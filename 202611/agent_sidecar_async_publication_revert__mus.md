# Agent sidecar async publication: should it be reverted?

**Swarm report (`__mus`) — research for the lead synthesizer. Question: we made agent
sidecar publication asynchronous to speed up commits and have seen publication errors
since. Should we revert? Is "sidecar page live before its commit" the right invariant?
Can commits be fast while guaranteeing it with 100% certainty?**

**Short answer:** your invariant is the right goal, but a full code revert is more than
you need, and 100% certainty is unachievable on the current commit ordering no matter
which mode you pick. Flip `commit.publication.mode` back to `inline` (one config
default, not a revert), keep the background publisher as the recovery drain it already
is, measure the real inline cost with the existing drain-timing log before optimizing,
and only then decide whether to invest in the one design that actually delivers the
guarantee: publishing the sidecar *before* the primary is pushed.

## 1. What the async change actually does

Two October 30 commits introduced the current behavior (both landed as `sase-1pt`
stitches):

- `4356cffaa1` ("add background publication job") built the host-owned `publication`
  scheduler routine: a 15-second fs-triggered job (doorbell files under
  `~/.sase/projects/<key>/agent_publication/`) plus a 5-minute backstop, a 4-minute
  per-pass budget, and a liveness heartbeat at
  `~/.sase/agent_publication/heartbeat.json`. See
  [src/sase/agents_sync/publication_job.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_13/src/sase/agents_sync/publication_job.py)
  and the `publication` block in
  [src/sase/default_config.yml](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_13/src/sase/default_config.yml).
- `e69360f49d` ("enqueue agent publication in background") made it the **default**:
  `commit.publication.mode: background`. When axe is running *and* the heartbeat is
  fresher than 15 minutes, the commit path persists a durable outbox row plus a hint
  file and returns — the prompt archive and hood are written later by the publisher
  (after `done.json` exists, or after a 10-minute grace; `_DONE_MARKER_GRACE_SECONDS`
  in `publication_job.py`). Bead pages, plan-header refresh, and artifact-link release
  evidence stay synchronous. Otherwise the commit falls back to the inline drain.

The selection logic is `_background_publication_selected()` in
[src/sase/workflows/commit/workflow_publication.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_13/src/sase/workflows/commit/workflow_publication.py:318),
and the user-facing contract is documented in
[docs/reference/vcs/commit-workflows.md](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_13/docs/reference/vcs/commit-workflows.md)
("Agent-sidecar publication" section) and
[docs/reference/agents/hood-sync.md](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_13/docs/reference/agents/hood-sync.md).

This is the *second* time this trade was made. On August 5, `de78052789` ("publish
sidecar work inline on the commit path") did the reverse: it deleted
`enqueue_committed_agent_publication`, restored `publish_committed_agent_hood`
(enqueue **plus** drain), and re-established the loud-failure contract — explicitly
because commits carry `SASE_AGENT=` provenance tags and the sidecar work should finish
before the command returns. The October change re-added the enqueue-only path alongside
the inline one rather than replacing it.

## 2. Your invariant is correct — and background violates it by construction

Agent-backed commits and PRs carry `SASE_AGENT=` (and usually `SASE_MODEL=`) trailers,
and commit footers link the agent session page
([commit-workflows.md](docs/reference/vcs/commit-workflows.md) "Agent-backed commits"
paragraph;
[internals](docs/contribute/agents-sidecar-sync.md) "footers identify a sase agent").
A reader who follows that reference in the window between the primary push and the
publisher drain finds nothing — exactly the failure you describe. Background mode
*guarantees* such a window on every agent commit taken on the fast path: 15-second
scheduler cadence at best, plus the 10-minute `done.json` grace for still-running
agents, plus the 4-minute work budget, lock contention, and any quarantine/retry
delays. Follow-up fixes since the async landing (`6d615680b8` stale-retry rework,
`3e6c19ee37` index-lock contention bound, `0547d23ce3`/`a0b00da79b` repair bounding,
`5dfd28c74b` gate-turn claim loss on publication failure) confirm the error surface
grew exactly where async queues grow it: stale rows, lock races, and repair runbooks
(`--repair-revisions`, `--repair-planner-scopes`, `--retry-quarantined`).

So on the core question — *should the page be live before the commit is readable?* —
I agree with you. The commit message is a published pointer; a pointer that routinely
dangles is a defect, not a speedup.

## 3. Why "revert" overshoots — and what to do instead

You do not need to revert `4356cffaa1`/`e69360f49d`. The async machinery is also the
recovery machinery: the same publisher, doorbell, heartbeat, and `sase agent sync`
drain are what rescue legitimately deferred work (lock busy, push failure, process
death) under *either* mode, and the inline path already depends on them ("every drain
and full sync rebuilds the archives owed by the requests it is about to acknowledge").
Ripping them out would remove your safety net while the inline path still needs one
(see §4).

The minimal change that restores your invariant as the default is a one-line default
flip:

```yaml
commit:
  publication:
    mode: inline   # today: background
```

in `src/sase/default_config.yml` (plus regenerating the config reference docs). That
restores the pre-October-30 behavior for every user without deleting the background
job, which keeps running as the backstop drain. Per-machine override
(`commit.publication.mode`) already exists for anyone who wants the fast path back.
Recommend gating the flip exactly the way the feature was gated: one stitch, default
flip + docs, no code deletion. If the errors stop, the diagnosis (async caused them)
is confirmed cheaply and reversibly.

## 4. The uncomfortable finding: even `inline` does not give you 100%

Two facts in the current code mean the invariant cannot hold with certainty today,
regardless of mode:

1. **The primary is pushed before publication starts.** Dispatch (commit + push)
   completes, the first result marker is written, and *then* the tracking phase runs
   the publication step
   ([workflow.py](src/sase/workflows/commit/workflow.py) dispatch/push section;
   [_workflow_tracking.py](src/sase/workflows/commit/_workflow_tracking.py)
   `_run_tracking_steps` → `_run_agent_publication_step`). Any reader of the primary
   remote sees the commit while the sidecar drain is still running. Inline shrinks the
   dangling window to one drain duration; background stretches it to publisher latency.
   Neither closes it.
2. **The outbox is keyed by the post-commit SHA.** Requests are keyed
   `(global_agent, primary_revision)` where `primary_revision` is the commit the agent
   created — publication *names* a commit that must already exist. You therefore
   cannot publish-first without a different identity scheme (provisional key + rekey on
   commit; the `--repair-revisions` rekey machinery proves rekeying is feasible but it
   is a repair path, not the main path). And inline itself degrades: when the drain
   cannot finish now, the commit still returns `OK` with a "deferred, will retry"
   warning (`_run_agent_publication_inner`: `if outcome.queued: ... warning ...` then
   `return True`). Only the never-even-queued case fails loudly with a `--resume`
   hint.

A true 100% guarantee ("no readable commit ever points at an unpublished page")
requires reordering, not tuning — one of:

- **(a) Hold the primary push until the sidecar acknowledges.** Smallest change to the
  ordering: push primary, attempt sidecar drain, and if the drain defers, either hold
  the primary push (so remote readers never see the commit first) or fail the commit
  loudly. Cost: commits inherit sidecar flakiness (lock contention, credential
  outages) as hard failures; needs the `--resume` path to be rock-solid since it
  becomes the normal recovery route, not the exception.
- **(b) Sidecar-first with provisional keys.** Publish the agent page under a
  pre-commit identity, commit, then rekey/confirm. Biggest change (outbox keying,
  revision repair, planner rows all assume post-commit SHAs), but it is the only order
  in which a failed primary leaves a harmless orphan page rather than a dangling
  pointer. Orphans are acceptable; dangling pointers are not.
- **(c) Stop pointing at unpublished pages.** Keep background, but remove the
  `SASE_AGENT=` page link from the commit message until publication confirms (deferred
  tagging, or a "publishing" placeholder page). This is the standard async pattern
  (like CI status on a PR), but it concedes your invariant rather than meeting it.

My recommendation: do **not** pursue (b) or (c) now. Take the default-flip from §3,
which gets you from "dangles on every commit" to "dangles only when the inline drain
defers" — likely a 10–100x reduction in dangling windows — and evaluate whether the
residual (case (a)-without-holding) is actually painful before paying for reordering.

## 5. Speeding up commits without breaking the (restored) guarantee

Measure first: every commit-triggered drain already appends one structured timing line
to `~/.sase/logs/agent_publication_drains.jsonl` (lock wait, per-stage durations,
inventory counters, git op counts; see
[src/sase/agents_sync/publication_timing.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_13/src/sase/agents_sync/publication_timing.py)),
and `tools/agents_publication_profile --project <key>` profiles a representative drain
read-only. The `sase-1nf.10` ("pub-fix") plan was explicitly scoped from these
records. Do not optimize on intuition; pull ~50 recent drain lines and rank stages
before changing anything.

With that data, the levers that preserve the guarantee (roughly in cost/benefit
order) are:

1. **Scope the inline drain to the committing hood first.** Today the inline path
   "immediately drains every active request for the project under the bounded agents
   lock" — one stale or slow neighbor row taxes your commit. Draining the committing
   hood synchronously and leaving the rest to the background publisher preserves your
   invariant for the pointer your commit actually contains while recovering most of
   the async speedup.
2. **Keep already-moved work off the path.** The codebase has been converging here:
   completed link drains release their hint with leftovers going to the hourly
   `artifact_link_backfill` (`6d615680b8`); protection-scan reuse (`30e012baaa`),
   slim owner-manifest `files` lists, and the quadratic-scan fix (`54779b62f5`) all
   cut inline seconds. Continue that direction: anything that is retryable-by-design
   (artifact links, Referenced By, backfill) should never block the hood ack.
3. **Cut lock contention, not corners.** The drain log's `lock_wait_seconds` plus the
   lock-holder attribution (`{pid, operation, agent, started_at}` beside the flock
   file) tells you whether commits queue behind each other or behind the 15-second
   publisher tick. If the publisher routinely holds the agents lock when commits
   arrive, deschedule or jitter the tick rather than widening the async window.
4. **Warm clones and idempotence.** Hidden machine clones that are already fetched and
   payloads that are "already current" (byte-identical rebuild → no-op ack) make the
   common inline drain cheap. These are pure wins with no semantic cost.
5. **Bounded fast-fail with loud resume — not silent defer.** Where a bound must
   exist (lock timeout, transaction budget), prefer failing the publication step with
   the existing `sase stitch create --resume` hint over warning-and-continuing. A
   failed commit that retries is honest; an `OK` commit with a dangling pointer is
   the bug you are trying to kill. Note this trades commit latency variance for
   correctness — the right trade while the invariant matters more than the speedup.

What I would explicitly **not** do: reintroduce blanket background-by-default, add a
second queue, or "fix" the errors with more repair flags while keeping the ordering.
Each repair flag (`--repair-revisions`, `--repair-planner-scopes`,
`--retry-quarantined/--retry-retired`) is evidence of async's carrying cost: operator
attention per dangling row. The August revert (`de78052789`) already ran this
experiment and chose inline; the October reintroduction re-created the exact failure
class it removed.

## 6. Recommended decision

1. **Agree with the invariant.** A commit message that names an agent page should name
   a live page. This is a correctness property of the commit workflow, not a
   performance preference.
2. **Don't revert code; flip the default.** Set `commit.publication.mode: inline` as
   the default, keep the publisher/doorbell/heartbeat/`sase agent sync` machinery as
   the recovery path, and confirm the error rate drops. One stitch, fully reversible.
3. **Instrument before further surgery.** Rank real drain costs from
   `agent_publication_drains.jsonl` + the profile tool; apply §5 levers in order,
   starting with hood-scoped inline drain.
4. **Treat 100% as a separate project.** If residual deferred-inline windows still
   hurt after (1)–(3), the fix is primary-push-holding (a) or sidecar-first rekeying
   (b) — an explicit design decision with its own bead, not a side effect of the
   revert discussion. Until then, report the guarantee honestly as "page live before
   return except when the drain defers, in which case the commit says so and names
   its recovery command."

## Sources inspected (all in this checkout)

- `src/sase/workflows/commit/workflow_publication.py` — background selection
  (`_background_publication_selected`), enqueue-only vs inline branches,
  queued-with-warning returns.
- `src/sase/workflows/commit/workflow.py`, `src/sase/workflows/commit/_workflow_tracking.py`
  — dispatch/push precede tracking-phase publication.
- `src/sase/agents_sync/publication_job.py` — publisher drain, 10-minute
  `done.json` grace, 4-minute budget, heartbeat writes.
- `src/sase/agents_sync/publication_doorbell.py` — doorbell/hints,
  `publisher_is_live`.
- `src/sase/axe/run_agent_exec_finalize.py` — doorbell rung after `done.json`.
- `src/sase/agents_sync/publication_timing.py` — drain-timing JSONL schema.
- `src/sase/default_config.yml` (`commit.publication.mode`, `publication` routine),
  `docs/reference/vcs/commit-workflows.md`, `docs/reference/agents/hood-sync.md`,
  `docs/contribute/agents-sidecar-sync.md`.
- History: `de78052789` (Aug: back to inline), `4356cffaa1` + `e69360f49d` (Oct:
  background job + background-by-default), `4f1a5e0760` (timing), `6d615680b8`
  (stale-retry rework), `3e6c19ee37`, `0547d23ce3`, `a0b00da79b`, `5dfd28c74b`.
- Tests: `tests/test_commit_workflow_publication_step.py` (mode/axe/liveness gating),
  `tests/agents_sync/test_publication_job.py`, `tests/test_commit_publication_inline.py`.
