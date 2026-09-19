# Agents `@epic` Panel Flicker: Apply-Boundary Atomicity and Bounded-Snapshot Semantics

## Executive summary

The recurring `@epic` panel flicker is best explained by a **non-atomic Agents-tab
apply pipeline**, not by Textual painting alone. A broad Tier-1 disk refresh can publish
one roster and rebuild the panels; only afterward does the code merge the current
proc-observer projection and finalize the roster a second time. When the first roster
does not contain the proc-shell rows that sustain `@epic`, the panel is removed and then
remounted a few milliseconds later.

The live trace contains three instances of exactly this shape within eleven minutes on
2026-09-18:

1. the bounded artifact-index load returned zero rows;
2. the incomplete-load merge declined to preserve a nonempty cache;
3. the UI finalized and rendered `agents=0, panels=1`;
4. proc-shell synchronization immediately produced `agents=17, panels=2` and rendered
   again.

This happened after the previously relevant fixes had been installed. Those fixes
addressed mutable row-graph races, bounded prefixes with `has_more=true`, and cached
proc-shell carryover, but they do not make the union of disk rows and the latest
proc-observer projection a single publication.

The recommended solution is to make roster publication transactional: compose the
latest disk result, cached rows allowed by snapshot semantics, proc projection, fleet
projection, folds, and query filtering before the first and only finalize/render. Add a
proc-projection generation token so a projection that changes during background compute
is rebased at the UI-thread commit boundary. Separately, stop treating `has_more=false`
as proof that a bounded snapshot has authoritative removal information.

## Scope and evidence

This investigation used:

- the current Python TUI loading, merge, proc-observer, and panel-rendering code;
- the linked Rust artifact-index implementation;
- git history for earlier attempted fixes;
- the local TUI trace and startup/update logs;
- a read-only production-query probe against the current artifact index.

The decisive runtime evidence is in `/home/bryan/.sase/perf/tui_trace.jsonl`. The trace
ends on 2026-09-18, so it proves the mechanism and historical recurrence but does not
claim continuous tracing through 2026-09-19.

## Direct runtime evidence

### Three zero-to-restored publications

The following events are from one Agents-tab session. Times are America/New_York.

| Time | Refresh source | Load result | Cached rows at merge | First panel publication | Second panel publication |
|---|---|---:|---:|---|---|
| 16:16:47 | `filter` | `returned_count=0`, `bounded_prefix=true`, `has_more=false` | 149 | `agents=0, panels=1` at 16:16:47.314 | `agents=17, panels=2` at 16:16:47.368 |
| 16:16:50 | `dismissed_index_sync` | `returned_count=0`, `bounded_prefix=true`, `has_more=false` | 56 | `agents=0, panels=1` at 16:16:51.061 | `agents=17, panels=2` at 16:16:51.116 |
| 16:27:24 | `notification` | `returned_count=0`, `bounded_prefix=true`, `has_more=false` | 100 | `agents=0, panels=1` at 16:27:24.957 | `agents=17, panels=2` at 16:27:24.982 |

For the 16:27 occurrence, the detailed sequence is:

```text
16:27:24.749  agents.load_from_disk
                source=notification, returned_count=0,
                bounded_prefix=true, requested_limit=97, has_more=false
16:27:24.915  agents.incomplete_load_merge
                incoming=0, cached=100, duration=0.0046ms
16:27:24.938  agents.finalize_plan visible=0
16:27:24.954  display fallback: panel_membership_change
16:27:24.957  agents.refresh_panel_widgets agents=0 panels=1
16:27:24.962  agents.fold_filtering count=49
16:27:24.968  second full display, agents=17
16:27:24.982  agents.refresh_panel_widgets agents=17 panels=2
```

The first display completed at 16:27:24.960 and the restored display completed at
16:27:25.012. That is enough time for multiple terminal frames. This is therefore a
real state transition exposed to the renderer, not merely a title-paint artifact.

The same trace also records `fallback_reason="panel_membership_change"`. The panel
renderer removes `AgentList` widgets whose IDs are no longer in the new panel set
(`src/sase/ace/tui/actions/agents/_display_panel_widgets.py:70-80`) and later mounts the
missing widgets again. A temporary panel-set contraction is thus visible by design.

### The issue survived the prior fixes

The dev-update log shows that commit `571039e11` was installed at 16:14:36, and the TUI
startup log records a new startup at 16:15:50. That revision contains both:

- `7058f16ce` — `fix(agents): stabilize bounded load convergence`;
- `3962d8819` — `fix(tui): isolate agent row graphs during background refresh`.

The first traced recurrence followed about a minute later. Stale process code therefore
does not explain this evidence.

### The zero result is not the current steady-state query result

The persisted current query is `NOT machine:apollo`. Running the production tiered
loader quietly with that query and the traced limit of 97 returned:

```text
agents=97
bounded_prefix=True
returned_count=97
has_more=True
record_count=256
tribes={None: 91, chop: 3, epic: 2, research: 1}
```

Thus the trace's zero-row result is not a durable truth about the current index/query;
the same query currently includes two `epic` rows. The old trace does not record the
canonical query key, so it cannot prove whether every zero was a provider anomaly or a
legitimate disk-only result for the exact query at that instant. That uncertainty does
not weaken the UI root cause: even a legitimate empty disk component must be unioned
with the proc projection before publication.

## Causal path in the current code

### 1. The apply boundary knows only about cached proc rows

`prepare_loaded_agents_apply_boundary()` preserves proc-shell rows found in
`snapshot.cached_agents_with_children`
(`src/sase/ace/tui/actions/agents/_loading_compute.py:203-219`). This was added by
`6eb51ac49` (`fix(ace): preserve proc shell selection on refresh`) and is useful, but it
only carries rows already materialized in the roster.

`PreparedApplySnapshot` does not contain the current proc-observer projection or a proc
generation (`_loading_compute_types.py:76-105`). The snapshot constructor similarly
captures `_agents_with_children` but not `_effective_proc_projection()`
(`_loading_apply.py:171-232`). A newer observer projection can therefore be absent from
the prepared boundary even when it is available by commit time.

### 2. The disk-derived roster is finalized and rendered

`_apply_loaded_agents_prepared()` assigns the prepared lists and calls
`_finalize_agent_list()` at `_loading_apply.py:518-555`. Finalization drives panel-key
calculation and display refresh. If the prepared list lacks the rows that own `@epic`,
the incremental display path rejects the panel-key change and falls back to a full
rebuild (`_display.py:277-296`).

### 3. Only after rendering does proc synchronization happen

The same method calls `_sync_proc_shell_agents_from_projection()` after finalization and
after recording the app projection (`_loading_apply.py:570-582`). That sync:

- reads the effective proc projection;
- merges proc-shell agents into `_agents_with_children`;
- invokes `_finalize_agent_list()` again
  (`src/sase/ace/tui/actions/_proc_action_completion.py:154-205`).

The trace's zero-to-17 sequence is the exact observable consequence of this ordering.
The UI is publishing two internally coherent component snapshots rather than one
coherent aggregate snapshot.

## Why earlier fixes were incomplete

### Bounded-load convergence covers only `has_more=true`

The current merge defines a bounded load as partial only when both
`bounded_prefix` and `has_more` are true
(`_loading_compute_merge.py:312-329`). A zero-row bounded result necessarily reports
`has_more=false`, so without a same-query complete-history watermark the function
returns immediately and omission becomes deletion. The 0.003-0.007 ms merge spans in
the trace are consistent with this early return.

`has_more` is a pagination fact, not an authoritativeness fact. In the Rust core it is
computed as “matching completed candidates exceeded the budget”
(`crates/sase_core/src/agent_scan/index.rs:4859-4909`). It says nothing about whether
the snapshot is allowed to delete rows previously visible from another component or a
prior index generation.

The `7058f16ce` tests cover a bounded prefix with `has_more=true`, including panel-key
preservation. They do not cover a same-query bounded zero with no explicit deletion
evidence.

### Proc-shell preservation tests cover the cached-roster case

The existing regression test seeds both the current roster and the observer projection
with the proc shell, then asserts it is present at the first finalize
(`tests/ace/tui/test_proc_shell_selection_survives_refresh.py:155-190`). It does not
exercise the important race: the effective observer projection contains a row that is
not in the apply snapshot's cached roster. It also does not assert that an entire apply
performs only one visible finalization.

### Row-graph isolation fixes a different race

`3962d8819` prevents background normalization from mutating the displayed `Agent` graph.
That removes transient field/relationship corruption but cannot prevent two deliberate
list publications.

### The repro invariant starts too late

`post_complete_incomplete_shrink` is disabled until a complete-history snapshot has
been observed (`src/sase/ace/tui/repro/invariants.py:112-137`). The traced loads had no
complete-history watermark for the relevant query, so a nonempty-to-empty bounded
transition was not rejected. There is also no invariant for “panel keys must not shrink
and regrow during one logical apply.”

## Artifact-index findings

The Rust index is not proven to be the primary cause of the flicker.
`rebuild_agent_artifact_index()` performs its delete and reinserts in one SQLite
transaction, so a normal rebuild should not expose its empty intermediate table.

There are nevertheless two correctness-hardening opportunities:

1. A cached bounded query is a sequence of SELECTs—active candidates, completed
   candidates, optional machine-tree expansion, and record hydration—without an
   explicit connection-wide read transaction
   (`agent_scan/index.rs:4806-4902`). Concurrent commits can therefore make those
   phases observe different SQLite snapshots.
2. The Python snapshot cache is guarded by database/WAL mtime and size before and after
   the query (`_agent_loader_artifacts.py:321-445`), but it has no logical index
   generation or authoritativeness token. A stable zero can be cached, and a bounded
   result exposes no independent statement that removal-by-omission is safe.

These are plausible contributors to an anomalous zero and deserve tests, but the
available evidence does not identify the exact producer of the old zero snapshot. The
atomic UI fix is required regardless.

## Recommended solution

### 1. Make aggregate roster publication atomic

Refactor proc synchronization into a pure composition step and a separate event-facing
wrapper. During a disk apply:

1. capture the effective proc projection and its monotonically increasing generation;
2. build proc-shell agents from that projection;
3. merge them with the disk/cached/fleet roster **before** fold filtering, query
   filtering, selection planning, panel-key calculation, and finalization;
4. at the UI-thread commit point, compare the proc generation with the captured one;
5. if it changed, rebase the prepared data on the latest proc projection (or recompute
   the cheap final boundary);
6. assign app state and call `_finalize_agent_list()` exactly once.

Remove the ordinary post-finalize `_sync_proc_shell_agents_from_projection()` call from
the disk-apply path. Observer events outside a disk apply can still use the wrapper, but
an in-flight disk apply must coalesce with them rather than publish an intermediate
proc-less roster.

This is the root fix. Merely retaining the old panel widget, adding a delay, or making
the rebuild faster would hide only some frames while leaving selection and roster state
temporarily wrong.

### 2. Separate pagination completeness from removal authority

Extend `AgentLoadState`/the Rust wire with an explicit concept such as
`removals_complete` or `snapshot_authoritative`, ideally paired with an index generation.
For an unchanged query:

- bounded cached loads should patch by identity and must not delete by omission;
- exact artifact deltas may remove only rows named by tombstones/dismissals;
- a source-reconciled full-history snapshot may replace the roster authoritatively;
- `has_more=false` alone must not authorize deletion.

As an immediate safety patch, if a same-query bounded cached load falls from a nonempty
roster to zero without tombstones or explicit dismissal evidence, retain the last good
disk roster and schedule one revalidated load. Do not apply this guard across a query
change, where an empty result may be intentional.

### 3. Give the core query one logical snapshot

Run candidate selection, machine-tree expansion, and hydration within one explicit
SQLite read transaction and return a logical index generation with the result. The
Python cache should key/validate against that generation rather than only file metadata.
This will make any future zero result diagnosable and prevent mixed-generation reads.

### 4. Add regression tests and trace invariants

Add these deterministic cases:

- current roster lacks a proc shell, current proc projection contains an `epic` proc
  shell, disk load is empty: the first and only finalize still contains `@epic`;
- proc generation changes between worker preparation and UI commit: the latest
  projection is rebased before publication;
- same-query bounded zero with no deletion evidence preserves the prior disk roster;
- changed-query bounded zero is allowed;
- cached index read concurrent with index maintenance remains generation-consistent;
- a logical apply may not emit `N -> 0 -> N` visible rows or lose and regain a panel key.

Trace `history_query_key`, proc projection generation/count, pre-commit and published
panel keys, snapshot authority, index generation, cache hit/miss, and explicit removal
evidence. That will distinguish a valid query transition from an index anomaly in one
event rather than requiring inference from surrounding logs.

## Final recommendation

Implement the **single-publication aggregate boundary** first: merge the latest
generation-stamped proc projection before folds/finalization and render once. In the same
change, add the regression where `@epic` exists only in the newer proc projection. Then
land the same-query bounded-zero guard, followed by explicit snapshot-authority and
index-generation semantics in the Rust core.

That ordering directly eliminates the observed flicker even if a disk query legitimately
returns zero, while the follow-up semantics prevent transient or stale bounded snapshots
from erasing valid disk rows.
