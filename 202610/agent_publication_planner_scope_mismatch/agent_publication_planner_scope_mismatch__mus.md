# Agent-publication "did not materialize during commit drain" errors — research

Date: 2026-10-31. Scope: the recurring `agent_publication` error notifications
exemplified by `~/.sase/axe/error_digests/digest_20261031_100432.txt`:

- `[agent_publication] gh_sase-org__sase: published agent page for
  'bbugyi200.athena.sase-1pj.6' did not materialize during commit drain`
- `agent_publication: projects=4 hood_drained=0 link_drained=2
  referenced_by_drained=0 active_remaining=2 lock_busy=0 deferred_projects=0 errors=1`
- Exit code 0, structured result `check_error`, so the scheduler files an
  error digest (and a notification) on essentially every tick that hits it.

## What the error literally means

The message is emitted by exactly one place,
`src/sase/agents_sync/_commit_publication_transaction_steps.py`
(`acknowledge_completed`). After a hood is published to the agents sidecar,
the drain verifies each outbox row through `publication_request_fulfilled`
(`src/sase/agents_sync/publication_completion.py`), which delegates to the
Rust core `decide_publication_request_completion`
(`sase-core/.../agent_publication_recovery/complete.rs`). The decision is:

1. Compute the required page: `agents/<global>/README.md` for a run-kind
   publication, `sessions/<global>.md` for a session-kind publication.
2. If the page file does not exist in the sidecar checkout → unfulfilled
   ("required publication page is absent").
3. If the page exists, check the hood snapshot's run/container commit SHAs
   for the row's requested `primary_revision` (SHA-equivalent comparison).
   Page present + revision absent → unfulfilled with reason
   "required page exists without the requested primary revision".

"Did not materialize" is case 3: **the page rendered, but the snapshot does
not associate the requested revision with that agent's run.** The row is
charged one attempt (`increment_attempts=True`); after
`DEFAULT_PUBLICATION_MAX_ATTEMPTS = 3`
(`src/sase/agents_sync/publication_outbox_operations.py`) it quarantines,
which is why every digest series shows the same agent failing on 2–3
consecutive ticks (`active_remaining` 1 → 1 → 0) and then going quiet while
the *next* new agent starts failing. It is not one stuck row; it is a
systematic ack-gate refusal striking each new publication.

A sibling line often seen next to it,
`dropping projected edge with invalid ref: rule=stitch-bead
ref='bead:[sase-1g4.2.1.5]'`, is benign noise: a projected bead edge whose
target bead does not exist is skipped during planning. It is not the cause.

## How big the problem actually is

`sase agent sync -c -j` and `sase doctor` (observed 2026-10-31) show the
digest error is the tip of a large quarantined backlog:

- `state.agent_publication_outbox`: **5155 issues — 3817 quarantined,
  7 retired, 1331 stale requested revisions.**
- sase project (3544 quarantined rows): ~2912
  "agent-hood publication did not complete within 120s" (bounded-drain
  timeout), ~436 "agents sync lock is busy", ~36 "did not materialize",
  ~124 deferred-prompt-archive failures, plus a handful of sidecar-git
  failures (`pull --rebase` blocked by unstaged changes / index locks,
  payload-index reset failures).
- bob-cli project (278 quarantined rows): ~212 prompt-archive failures,
  ~63 "did not materialize", 3 retired.
- The 1331 stale requested revisions are exactly the ack-gate population:
  rows whose requested revision no longer appears in any published run's
  commits (see below).

Related throughput evidence: publication ticks overrun badly (log shows
"Tick overrun: took 300.3s but interval is 15s"), the sase sidecar
re-reduces ~2515 streams, and the housekeeping `artifact_link_backfill`
job itself timed out after 300s. Drains are slow; the 120s per-drain bound
(`_commit_publication_drain.py`, overridable via
`SASE_AGENTS_PUBLICATION_DRAIN_TIMEOUT`) converts slowness into quarantines.

## Root causes, ordered by weight

1. **Stale pre-commit revisions (the digest error).** The outbox row records
   the workspace HEAD at enqueue time (`_commit_publication_queue.py`).
   Commit `02cd3b39b6` ("name publications with the post-commit SHA",
   2026-10-24) acknowledged the pre/post-commit distinction, and commit
   `7b1b437558` ("report-first repair for stale publication revision
   rows") added a dedicated repair: rows enqueued before that fix can name
   a revision no published run carries. The ack gate then refuses them
   forever — retry alone can never succeed. Doctor explicitly reports these
   (1331) and points at the repair command. Short-lived agents (`.land`
   runs, research-swarm runs like `research.55.*`, which dominate the
   quarantine lists) are the most exposed: their workspaces move on or are
   cleaned, so nothing will ever re-associate the old SHA.
2. **Drain throughput vs. timeout (the bulk of quarantines).** ~80% of the
   sase backlog is bounded-drain timeouts, not correctness failures. A
   slow sidecar + 120s bound + 15s tick + lock contention is a recipe for
   mass quarantine. These rows are the most likely to succeed on a plain
   retry once the system is quiet.
3. **Lock contention.** `agent_publication`, `artifact_link_backfill`, and
   any manual `sase agent sync` all contend on `sase-agents-sync.lock`
   (436 quarantined "lock is busy"; even `-R` report mode failed with
   "agents sync lock is busy" during this investigation). Contention turns
   transient busyness into quarantines that then need manual release.
4. **Orphaned prompt archives.** ~336 rows quarantined with "prompt archive
   is unresolved and a missing local source does not prove there was no
   prompt obligation". The local prompt source (often an ephemeral numbered
   workspace) is gone, so the deferred-restore gate blocks acknowledgment
   and retry cannot fix it. These need a policy decision (re-run, record
   not-applicable, or retire), not more retries.
5. **Dirty sidecar clones.** A few rows fail on `git pull --rebase`
   (unstaged changes, index locks). Minor, but they poison every drain
   that touches that clone until cleaned.

## Recommended solution

Do these in order; each step is cheap and the sequence matters because
retrying before rekeying just burns the 3 attempts again.

1. **Rekey stale revisions first (fixes the digest error class):**
   `sase agent sync --repair-revisions -p gh_sase-org__sase --apply` and
   `sase agent sync --repair-revisions -p gh_bobs-org__bob-cli --apply`.
   Report mode first (without `--apply`) if you want to eyeball the
   rekey map; it writes nothing. Run when the scheduler is quiet — report
   mode itself failed with "lock busy" under load, so expect to retry.
   This directly addresses doctor's 1331 stale revisions and the "required
   page exists without the requested primary revision" verdicts.
2. **Release the quarantined backlog:**
   `sase agent sync --retry-quarantined` (per project; the sase project
   alone holds ~3544). Timeout and lock-busy rows should drain once the
   system is idle; rekeyed "did not materialize" rows should now fulfill.
   Watch the first few ticks: rows that fail 3 more times will
   re-quarantine with a fresh diagnostic telling you which class they
   belong to.
3. **Drop the unpublishable remainder:**
   `sase agent sync --drop-retired` clears the 7 retired rows ("hood has
   no publishable runs", digest mismatches) that can never publish.
4. **Triage the prompt-archive residue separately.** After steps 1–3,
   whatever remains quarantined with "prompt archive is unresolved" is
   missing its local source for good. Decide per batch: re-run the agent
   if the page matters, else leave quarantined (it is parked and silent)
   or retire it. Do not loop `--retry-quarantined` on these hoping for a
   different outcome.
5. **Stop the backlog from regrowing (throughput).** The underlying
   capacity problem is real: 300s ticks on a 15s interval, 2515-stream
   re-reductions, a 300s housekeeping timeout. Cheapest mitigations:
   run steps 1–3 during a quiet window (scheduler contention is visibly
   making everything worse); check whether the 120s drain bound
   (`SASE_AGENTS_PUBLICATION_DRAIN_TIMEOUT`) is still sized for the
   current sidecar; and treat the `artifact_link_backfill` 300s timeout
   as its own issue (it shares the lock and the tick budget). If
   timeouts persist after the backlog clears, that is a performance bug
   worth filing with the tick-overrun log lines as evidence — not an
   operator error.
6. **Expect notifications until `errors=0` is stable.** The digest is
   working as designed (exit 0 + `check_error` status → digest; cf. the
   "triage annotates, never changes exit codes" policy). The 10:12 tick
   in this window already showed `errors=0` once the active queue
   drained — the noise stops when the active queue stays empty, i.e.
   after steps 1–2, not by silencing the notifier.

Do **not** start with `--retry-quarantined` alone: un-rekeyed revision
rows will fail three more times and land back in quarantine, generating
three more digest notifications each. Rekey first, then retry.
