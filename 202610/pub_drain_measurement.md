# Publication drain measurement (pub-measure, sase-1nf.9)

**Date:** 2026-10-20. **Hosts:** athena (this machine), apollo (read-only over SSH).
**Code:** sase master at `d958a168fc` plus the pub-measure instrumentation
(stage-timing JSONL, sync-lock holder record, richer outbox doctor output).

## Bottom line

Every commit-triggered publication drain on athena rebuilds the whole world and
is therefore doomed by the 120 s alarm before it publishes anything. A
representative drain of the `sase` project (`gh_sase-org__sase`, 3,368
quarantined requests) spends **~210 s in the inventory build alone**, then
~14 s per planned hood, for a ~224 s floor against a 120 s bound. The
per-drain cost is dominated by two whole-project operations that do not scale
with the request being published:

1. `build_project_hood_inventory`: 19,517 runs in 12,474 hoods, **9,903 git
   subprocesses** (4,886 `commit_record` + 4,859 `resolve_sha`), 22 MB of
   prompt bytes + 452 MB of chat bytes read — for every drain.
2. `plan_hoods`: ~14 s and **~60 MB / ~24,000 files of payload for a
   one-run hood**, identical (within 4%) to a 67-run hood. Planning cost is
   independent of hood size: the whole payload is rebuilt per drain.

`pub-fix` (sase-1nf.10) must scope the inventory and the payload to the hoods
being published (or cache them) before anything else. No timeout, retry, or
accounting fix can help while one drain costs ~2x the bound.

## What was instrumented (permanent)

- One structured JSONL line per commit-triggered drain at
  `~/.sase/logs/agent_publication_drains.jsonl` (bounded, rotated past 1 MiB,
  following the existing `~/.sase/logs` conventions): project, active-request
  and distinct-hood counts, outcome, error class, alarm flag and stage, lock
  wait, per-stage durations (`payload_clean`, `pull_rebase`,
  `inventory_build`, `prepare` / `hood_publish:<hood>` /
  `prompt_archive_prepare` / `manifest_verify`, `commit`, `push`, `verify`,
  `cleanup`, `retry_*`), inventory counters (runs scanned,
  `commit_record` calls, prompt/chat bytes), and per-op git subprocess
  counts. See `src/sase/agents_sync/publication_timing.py`.
- A sync-lock holder record (`{pid, operation, agent, started_at}`) written
  beside the flock file on every `bounded_agents_lock` acquisition and
  removed on release; a stale pid is ignored. A lock-busy drain error now
  names the holder and its age. See `git_sync_ops.py`.
- `sase doctor -C state.agent_publication_outbox -j` now reports a
  `last_error_histogram` (stable failure classes shared with the JSONL
  `error_class`), the oldest active request's age, and per-project hidden
  clone state: commits ahead of/behind upstream, rebase in progress,
  untracked `files/objects`, dirty `prompts/`/`artifacts/`.
- Profiling harness: `tools/agents_publication_profile --project <key>`
  runs the inventory build and `plan_hoods` for the largest and smallest
  hoods. Both functions write nothing.

## Athena measurement (sase project, 2026-10-20)

Harness output (`tools/agents_publication_profile --project
gh_sase-org__sase`), read-only:

- inventory build: **209.84 s**; 19,517 runs in 12,474 hoods.
- git subprocesses during inventory: **9,903** — 4,886
  `agents_sync.commit_record`, 4,859 `agents_sync.resolve_sha`, 156
  `agents_sync.primary_root`.
- bytes read per drain: prompt 22,126,005 (~22 MB), chat 452,201,332
  (~452 MB).
- `plan_hoods` largest hood (`sase-um.5.1.3`, 67 runs): 14.66 s, 24,164
  files, 59,997,051 bytes. Smallest hood (`sase-ao.land`, 1 run): 14.03 s,
  23,868 files, 59,707,903 bytes. Cost is hood-size independent.
- Top hoods by runs: `sase-um.5.1.3` (67), `0zf` (46), `sase-126.4` (31).

Outbox state (`sase doctor -C state.agent_publication_outbox -j`):

- `gh_sase-org__sase`: 3,369 requests, **3,368 quarantined**, 1 active.
- Error classes: **timeout 2,905**, lock_busy 434, index_lock 19,
  unstaged_changes 5, manifest_mismatch 2, other 4, rebase_conflict 1.
- Oldest active request age: ~65 days.
- Hidden clone (`.../gh_sase-org__sase/repos/agents`): ahead 0, behind 0,
  no rebase, no untracked objects, clean prompts/artifacts. The clone is
  healthy; the backlog is purely a drain-cost problem.

Representative error samples (all read-only, from
`agents-publication-outbox.json`):

- timeout: `agent-hood publication did not complete within 120s` (2,905 rows).
  Root cause: measured ~224 s minimum drain (above). The SIGALRM unwinds the
  drain stack and the error is charged to every active request's attempt
  budget (`_record_failure(logical_keys=None)`), which contradicts
  `docs/reference/agents/hood-sync.md:330-333`. Unique content at risk: every
  quarantined request's unpublished hood pages.
- lock_busy (434): `agents sync lock is busy`. No holder was recorded at
  measurement time (the record is new); the JSONL line and the holder suffix
  will attribute the next occurrences to a pid/operation/age. Likely
  contributors: overlapping drains and the wedged apollo replay (below)
  holding clones across retries.
- index_lock (19), e.g. hood `sase-12w`: `could not stage agents sidecar
  payload: ... .git/index.lock ... File exists. Another git process seems to
  be running`. Root cause: a previous drain died while holding the index
  lock — consistent with the alarm orphaning streaming `git push` children
  (the timeout is swallowed inside per-hood publish, so cleanup never
  runs). These rows need an `index.lock` reaper or stale-lock removal before
  they can publish; the payload itself is intact.
- unstaged_changes (5): `git pull --rebase failed: ... Your index contains
  uncommitted changes` / `Your local changes ... would be overwritten by
  merge`. The timed-out drain leaves `prompts/` dirty (cleanup only restores
  the payload paths), so the next drain's pull fails. Recovery must clean
  `prompts/`/`artifacts/` the way full sync does — currently only the
  payload paths are restored.
- manifest_mismatch (2), e.g. hood `sase-18j`: `manifest file set mismatch
  for 'bbugyi200.apollo.03'`. Same class as apollo's retired rows (below);
  needs the manifest-repair procedure, not retries.
- rebase_conflict (1 on athena; see apollo for the bulk class).

## Apollo inspection (read-only, 2026-10-20)

- Outbox totals: **458 quarantined, 284 retired, 5 active** (747 requests).
- bob-cli (`gh_bobs-org__bob-cli`, 355 requests, 351 quarantined): **all 351
  quarantined rows fail replaying one stale local commit `2abeff3f9`
  ("chore(agents): sync from bbugyi200.apollo")** onto upstream. The replay
  touches shared derived files across the whole `bob-cli-7c` hood family
  (dozens of `agents/.../README.md` plus `chat.md` blobs, e.g. a 6,907-line
  `chat.md`). The clone sits at 1 ahead / 545 behind with **no rebase
  marker on disk** — each drain retries the pull, fails, aborts, and
  re-charges all 351 rows' attempt budgets. Unique content at risk: the
  `bob-cli-7c` session pages that exist only in `2abeff3f9` plus any
  untracked `files/objects` (currently zero).
- sase (`gh_sase-org__sase`, 392 requests): **283 retired with
  `manifest file set mismatch for 'bbugyi200.apollo.03'`** across ~40 hoods
  (largest: `research` with 110 rows), 15 quarantined manifest rows, 49
  quarantined timeouts, 41 quarantined lock_busy, 1 active timeout. The
  retired rows are unpublishable without the manifest-repair procedure;
  `pub-fix` must resolve the stale local state without losing the unique
  unpublished content, then `pub-recover` retries only the classes whose
  cause was removed.
- No wedged rebase in progress on either apollo clone right now; both
  clones are otherwise clean (no untracked objects, no dirty
  prompts/artifacts).

## What pub-fix must cover (from this report)

1. Scope the inventory build and `plan_hoods` payload to the hoods being
   published (or cache them): a representative, previously failing request
   must publish inside the existing 120 s bound.
2. Stop charging repo-wide failures (lock busy, timeout outside per-hood
   work, clone/pull/push/cleanup) to every active request's attempt budget.
3. Let `_PublicationDrainTimedOut` escape per-hood handling, terminate the
   timed-out streaming push/fetch with its process group, and extend drain
   cleanup to `prompts/` and `artifacts/`.
4. Resolve apollo's stale local commit `2abeff3f9` and the
   `bbugyi200.apollo.03` manifest mismatches without losing the unique
   unpublished `bob-cli-7c` pages; add a bounded retry selector with an
   error-class filter.
5. Reap or tolerate stale `index.lock` files left by timed-out drains.

## Reproducing

- `sase doctor -C state.agent_publication_outbox -j` (needs this phase's
  code installed for the histogram and `sidecar_states`).
- `.venv/bin/python tools/agents_publication_profile --project
  gh_sase-org__sase [--large-hood research]` (read-only; ~4 minutes on
  athena at current scale).
- `sase bead read sase-1nf.9 -r "<why>"` for the phase scope.
