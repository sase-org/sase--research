# sase-1pt vs sase-1pu.5.1: do the epics conflict?

- **Date:** 2026-10-29
- **Beads:** `sase-1pt` (epic, in progress), `sase-1pu.5.1` (epic, in progress)
- **Sources:** bead records (`sase bead read`); plan artifacts
  `plan:202610/commit_stage_async_publication.md` and
  `plan:202610/published_run_state_convergence.md` (`sase artifact read`); the sase
  checkout at `9394107ac2`, the HEAD when this session started.

## Answer

There is no logical conflict. The two epics are scoped against each other on purpose,
and neither declares a bead dependency. They do edit the same publication pipeline at
the same time, though, and that can cause two real problems: a queued retry can regress
a terminal state, and a change to the shared transaction's default behavior can quietly
break queued prompt archives. Worry about those two. The rest is merge friction. Nothing
needs to stop now, but one ordering constraint should be enforced (see Recommendations).

## What each epic covers

| | `sase-1pt` | `sase-1pu.5.1` |
| --- | --- | --- |
| Goal | Commit stage ends at a durable enqueue. A host-owned background publisher drains hood, prompt-archive, and link rows. | Published runs converge to verified terminal state without regressing newer snapshots. |
| Status | In progress. Phases 1-4 closed; 5-8 open. | In progress. 5.1.1 closed; 5.1.2-5.1.4 open. |
| Parent | Top-level | `sase-1pu.5` -> `sase-1pu` (seed `sase-1cc`) |

`sase bead dep list` shows no dependencies for `sase-1pt`, `sase-1pu.5.1`, or `sase-1pu.5`.

## The scope boundary is explicit

The `sase-1pt` plan lists "Republishing hoods whose runs became terminal after
publication (the rest of `sase-1cc`)" as out of scope. That work belongs to
`sase-1pu.5.1`, so the split was deliberate.

## One diagnosis, two fixes

Both epics start from the same bug: the hood is published before `done.json` exists.

- `sase-1pu.5.1` cites `workflows/commit/workflow_publication.py` calling
  `publish_committed_agent_hood` before the finalizer writes `done.json`, and
  `write_done_marker_and_update_index` not refreshing published state.
- `sase-1pt` (phase enqueue-only) moves the hood drain after `done.json`. The doorbell
  rings after `write_done_marker_and_update_index`, on the stated premise that "the hood
  captures terminal run state."

`sase-1pt` fixes the order. It does not by itself fix the state:

- `_artifact_state` in `src/sase/agents_sync/inventory_sources.py:400-410` returns
  `waiting` whenever `record.waiting` or `pending_question` is set, before it looks at
  `done`. A run with `done.json` plus leftover waiting metadata therefore publishes as
  waiting, including on the after-done path. I confirmed this by reading the function.
- The `sase-1pt` backstop publishes a request whose `done.json` is still missing after
  10 minutes, so crashed runs get a non-terminal hood by design.
- The inline fallback (`commit.publication.mode = inline`, or scheduler not live) runs
  "today's inline code unchanged," which still publishes before `done.json`.

So `sase-1pu.5.1` is needed on the normal path as well as for the backlog, and
`sase-1pt`'s backstop depends on it. The `sase-1pu.5.1` plan cites 8,659 of 15,457
published runs still active or waiting in a September measurement. `sase-1pt` does not
touch that backlog.

## Where they can collide

### R1 (highest): a queued retry can regress a terminal state

- The queue drain reaches `publish_agent_hood` through an injected argument:
  `src/sase/agents_sync/_commit_publication_locked.py:142` (`publish_hood=publish_agent_hood`).
  `drain_agent_publications` (`src/sase/agents_sync/_commit_publication_drain.py:112`) is
  called from `_commit_publication_queue.py:66,83`. The new background publisher will
  therefore write hoods through the function that `sase-1pu.5.1.2` changes.
- `sase-1pt.7` makes `background` the default. Queued rows are retried after a lock-busy
  or push failure, which is exactly when a row is oldest and its inventory is stalest.
- `sase-1pu.5.1.2` requires that a terminal outcome survive stale observations and that
  a retry re-read upstream before it builds a payload. That rule is absent today:
  `src/sase/agents_sync/publication_snapshot.py:_merge_richer_run_files` (line 420) has
  no state-precedence logic.
- **Open check:** confirm that a queued retry rebuilds the hood from the request's stored
  inputs (`commit_cwd`, `artifacts_dir`, `run_id`) and does not reuse a payload captured
  at enqueue time. The `sase-1pt` design suggests it rebuilds, but I did not read the
  drain code to confirm.

### R2: the shared transaction and protection code

- `git_sync_transaction.py`: `sase-1pu.5.1.3` says the repair path must not publish
  unrelated pending prompt objects, so it wants a narrow entry point or an explicit mode.
  The `sase-1pt` deferred path regenerates queued prompt archives inside the hood
  transaction, and that transaction publishes pending objects. If the default behavior of
  the shared transaction changes, queued archives break without an obvious failure.
  Required: default behavior unchanged, with a test that proves it.
- `publication_protection.py`: `sase-1pt.6` edits `_scan_file` and `scan_publication_bytes`
  to re-raise `PublicationDrainTimedOut` and to audit the other broad handlers in the hood
  transaction. `sase-1pu.5.1.2` routes its new state bytes through the same scan-and-withhold
  path. Two epics editing the same broad-exception handlers is the most likely source of a
  silent protection gap. Recent commits to these files (`c687d8b6eb`, `cecfbbab2f`,
  `0f76e05de4`) show active churn in this area.

### R3: mechanical merge friction (expect conflicts, low risk)

- Both epics register builtin jobs in the same four places: the `pyproject.toml` script
  entries, `src/sase/default_config.yml`, `src/sase/footprint/catalog.jsonl`, and the
  automation docs. `sase-1pt` adds `artifact_retention` and `agent_publication`;
  `sase-1pu.5.1.4` adds `agent_state_refresh`.
- Both epics edit `docs/reference/agents/hood-sync.md`.
- Both epics bump `sase-core-revision.txt`. This is mitigated: the `sase-1pt.4` pin
  resolver is present at `src/sase/sdd/_revision_pin_conflict_resolver.py`, so pin-only
  rebase conflicts now resolve mechanically.

### R4: two periodic writers on one sidecar (low)

`agent_publication` (`sase-1pt.6`, every 15 s, 240 s budget) and `agent_state_refresh`
(`sase-1pu.5.1.4`, every 5 min, 90 s budget) both take the agents lock. Both plans define
lock-busy handling, so they are compatible. Their integration tests should run with both
jobs active.

## What is compatible (checked against the plans)

- **Acknowledgment:** `sase-1pt` acks only after push and manifest verification. The
  `sase-1pu.5.1` plan says not to change commit-outbox ack semantics. These agree.
- **No network in marker writers:** the `sase-1pu.5.1` plan forbids network publication in
  marker writers. The `sase-1pt` doorbell ring is a local touch in `finalize_loop`, after
  the marker write. Keep it local.
- **Locking and push recovery:** both use the existing agents `flock` and bounded push
  recovery.

## State at check time (in the tree)

| Item | State |
| --- | --- |
| `sase-1pt.1` refby-events | Landed (commit `5f675c311f`; bead closed) |
| `sase-1pt.4` pin resolver | Present |
| `sase-1pt.6` publisher (`publication_doorbell.py`, `sase_chop_agent_publication.py`) | Absent |
| `sase-1pt.7` `commit.publication.mode` | Absent from `default_config.yml` |
| `sase-1pu.5.1.2` state precedence | Absent (no precedence logic in `publication_snapshot.py`; `_artifact_state` unchanged) |
| `sase-1pu.5.1.3` `--repair-states` | Absent |
| `sase-1pu.5.1.4` `agent_state_refresh` | Absent |

The overlap is still prospective. None of the colliding `sase-1pu.5.1` changes exist yet,
and I did not confirm the `sase-1pt` changes to the shared files (I did not check
`sase-1pt.5` or `sase-1pt.8` in code).

## Recommendations

1. **Enforce an ordering.** Land the `sase-1pu.5.1.2` precedence rule and its tests before
   `sase-1pt.7` flips the default to `background`. If that can't happen, `sase-1pt.7`
   must carry a test that a queued retry after a terminal publish does not regress state.
2. **Keep the transaction change additive.** Land the `sase-1pu.5.1.3` transaction change
   as a separate, additive change with the default path unchanged, plus a test that the
   default transaction still publishes pending prompt objects.
3. **Plan for the second lander to rebase.** Whichever epic lands second rebases and
   regenerates config and docs with `just fix`. Expect textual conflicts in the four
   job-registration files.
4. **Cross-link the beads.** Add a bead note on each epic (a note, not a `dep` edge) that
   records the convergence dependency: `sase-1pt`'s backstop and inline fallback depend on
   `sase-1pu.5.1` for terminal state. I did not change any beads.

## Method and limits

- Bead records were read with `sase bead read`. Plans were read with `sase artifact read`.
- Code checks were presence checks by grep and `test -f`, plus one read of
  `inventory_sources.py:400-410`. I did not read the diffs of in-progress phases and did
  not run tests.
- The open check in R1 (whether queued retries rebuild payloads) is unresolved.
- Phase-level detail for `sase-1pt.5`-`.8` and `sase-1pu.5.1.2`-`.4` comes from the plan
  artifacts, not from each phase bead.
