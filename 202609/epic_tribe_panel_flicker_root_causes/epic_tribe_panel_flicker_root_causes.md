# Agents-tab `@epic` tribe panel flicker: consolidated root-cause analysis

Consolidated from two independent research reports
([A](epic_tribe_panel_flicker_root_causes__a.md): apply-boundary atomicity;
[B](epic_tribe_panel_flicker_root_causes__b.md): widget identity and merge-guard
holes) plus lead verification of every load-bearing code claim against the current
master tree (2026-09-19).

## 1. Executive summary

The flicker is real, still reproducing after sase-127, sase-12p, `17c465c`
(tribe latch), and `3962d8819` (row-graph isolation), and it is **not one bug**.
Three verified defects compound:

1. **The apply pipeline publishes twice per disk apply.** A disk-derived roster is
   finalized and rendered first; only afterwards does
   `_sync_proc_shell_agents_from_projection()` merge the proc-observer projection
   and finalize again. When the first roster lacks the rows sustaining `@epic`,
   the panel unmounts and remounts milliseconds later.
2. **The incomplete-load merge guard still lets small/empty bounded loads replace
   a larger cache.** A bounded load with `has_more=False` (which every zero-row
   bounded result reports) is treated as authoritative whenever the
   complete-history latch is unset — and any incomplete apply with a mismatched
   `history_query_key` *clears* that latch.
3. **Tribe panels are not stable widgets.** `AgentList` widgets are keyed by slot
   index (`agent-list-panel`, `agent-list-panel-1`, …), every full rebuild
   `clear_options()`s every panel, and the row-remove incremental path bails on
   *any* nonempty query — which on this host is permanent
   (`NOT machine:apollo`). Even a legitimate one-frame occupancy change in a
   *sibling* tribe repaints or blanks the `@epic` widget.

Traces from 2026-09-18/19 show repeated `2 panels / 17 agents → 1 panel /
0 agents → 2 panels / 17 agents` sequences lasting ~25–55 ms — long enough for
multiple terminal frames — on a process confirmed to be running the prior fixes.

**Recommended solution (three phases, in this order):** (1) make roster
publication atomic — merge the generation-stamped proc projection *before* the
one and only finalize; (2) make tribe panels identity-stable widgets keyed by
tribe, sticky for configured tribes, with no `clear_options` on untouched
panels; (3) separate pagination completeness from removal authority in the merge
guard and, as follow-up, in the Rust core. Details in [§6](#6-recommended-solution).

## 2. Verified runtime evidence

From `~/.sase/perf/tui_trace.jsonl` and `~/.sase/logs/tui_agent_loads.jsonl` on
athena (grouping `by_status`, committed query `NOT machine:apollo`, split tribe
panels):

- **Three zero-to-restored publications in eleven minutes** on 2026-09-18
  (16:16:47, 16:16:50, 16:27:24), each with the same shape: bounded disk load
  returns `returned_count=0, bounded_prefix=true, has_more=false`; the
  incomplete-load merge declines to preserve a nonempty cache (56–149 rows);
  the UI finalizes and renders `agents=0, panels=1`; proc-shell sync immediately
  publishes `agents=17, panels=2`. The empty state persists ~25–55 ms — a real
  state transition exposed to the renderer, not a paint artifact.
- **The fixes were installed and running.** Commit `571039e11` (containing both
  `7058f16ce` bounded-load convergence and `3962d8819` row-graph isolation) was
  installed at 16:14:36; the TUI restarted at 16:15:50; the first recurrence
  followed about a minute later. Stale process code does not explain this
  evidence — though report B correctly notes stale-TUI checks (sase-12p.2) must
  precede any future live-repro triage, since a second PID (1880150) was
  applying 0-row full auto-refreshes all morning on 2026-09-19.
- **The zero result is not the steady-state truth.** Re-running the production
  tiered loader with the persisted query and the traced limit (97) returns 97
  rows including two `epic` rows. The traced zeros were transient anomalies (or
  query-transition artifacts the trace cannot distinguish, since it does not
  record the canonical query key).
- **Load sizes are still unstable on some paths.** On the main TUI PID,
  `auto_refresh` has converged (~230 rows) but `tier1_index_revalidate` swings
  41–696 rows — the same class of oscillation sase-127 closed for auto-refresh,
  still alive on the revalidate path.
- **Fallback mix.** In the trace tail, `display_full_rebuild` dominates
  incremental spans 231 to 18; dominant fallback reasons are
  `panel_membership_change` and `unsupported_grouping`.

## 3. Verified causal mechanisms

All file/line claims below were re-verified against the current tree.

### 3.1 Dual publication per disk apply (report A's root cause)

`_apply_loaded_agents_prepared()` (`src/sase/ace/tui/actions/agents/_loading_apply.py`)
assigns the prepared roster and calls `_finalize_agent_list()` — driving
panel-key calculation and rendering — and only *then* calls
`_sync_proc_shell_agents_from_projection()`, which reads
`_effective_proc_projection()`, merges proc-shell agents into the roster, and
calls `_finalize_agent_list()` **again**
(`src/sase/ace/tui/actions/_proc_action_completion.py:154–198`).

`PreparedApplySnapshot` carries only `cached_agents_with_children` (proc rows
already materialized in the roster, per `6eb51ac49`); it does not capture the
live proc projection or a projection generation. A proc row present only in the
newer projection is therefore absent from the first publication by construction.
The traced `0 → 17` sequences are the exact observable consequence.

### 3.2 The merge guard's removal-authority hole (both reports)

`merge_incomplete_load_after_complete_history`
(`_loading_compute_merge.py:308–330`) patches over the cache only when the
complete-history latch is set, the load is an `artifact_delta`, or the load is
`bounded_prefix AND has_more`. Otherwise it returns the incoming prep unchanged
— replacement. Two consequences:

- A **zero-row bounded result necessarily reports `has_more=false`** (in the
  Rust core, `has_more` means "matching completed candidates exceeded the
  budget" — a pagination fact, not an authoritativeness fact), so a bounded
  zero always bypasses the patch path.
- The latch is fragile: `_loading_apply.py:446–448` clears
  `_agents_seen_complete_history` on **any** incomplete apply whose
  `history_query_key` does not match. One mismatched-key load disarms the guard
  for everything that follows.

The `7058f16ce` tests cover `bounded_prefix=true, has_more=true`; they do not
cover a same-query bounded zero, nor the revalidate path whose 41–696 swings
remain live.

### 3.3 Panels are index-addressed slots, not tribe widgets (report B's root cause)

- `panel_keys_for` builds the panel set from *rendered* rows only
  (`status != "STARTING"` excluded); zero members ⇒ no key ⇒ widget removed. An
  empty tab is special-cased to a single `@default` panel, so a 0-row apply
  unmounts every named tribe.
- `panel_widget_id(panel_idx)` (`_display_helpers.py`) keys widgets by **slot
  index**. Any tribe appearing/disappearing *before* `epic` in sort order
  changes `@epic`'s index; `_refresh_panel_widgets` then paints a different
  tribe into the widget the user was watching.
- `build_list` starts with `widget.clear_options()`
  (`_agent_list_build_rebuild.py:122`), so even a full rebuild with unchanged
  keys blanks each panel for a frame.
- `_try_refresh_agents_display_incremental` requires
  `next_panel_keys == old_panel_keys`; any membership change falls back to a
  full rebuild (`panel_membership_change`). There is no single-panel
  insert/remove path.
- The row-remove patch bails whenever `_agent_search_query` is nonempty
  (`_display_panel_patches.py:125`) — sase-127.2 fixed the blanket
  `active_search` display fallback but not this helper. With the standing
  `NOT machine:apollo` query, **every identity removal** forces a full rebuild
  that `clear_options()`s `@epic`.
- Unmounting retires fold intents, so a remount re-applies
  `initially_expanded` — the fold-reset the user perceives alongside the
  disappearance.

Transient occupancy churn is routine: pre-metadata rows (`tribe is None`)
create a momentary `@default`; an epic fan-out whose visible members are all
`STARTING` empties `@epic` until they turn `RUNNING`.

### 3.4 Why the prior fixes and soaks missed this

| Fix / check | What it closed | What it left |
| --- | --- | --- |
| sase-127 (`7058f16ce` et al.) | 171↔484 auto-refresh oscillation; `has_more=true` bounded patching; stable-query display fallback | Bounded zero / `has_more=false`; revalidate path; row-remove bail; widget identity |
| sase-12p (`1fa7e5fc3`) | BY_STATUS admitted to incremental path; stale-TUI detector | BY_DATE rebuilds; index-keyed widgets; latch clearing |
| `17c465c` tribe latch | Pre-metadata rows *staying* in `@default` | They still exist for one apply and shift slots |
| `3962d8819` graph isolation | Node-content flicker (icons/links) from in-place mutation | Different symptom; does not keep the panel mounted |
| 30-min soaks | `"epic" in panel_keys_for` under exercised loads | 50 ms unmounts; widget object identity; `clear_options` blanks; the untested apply holes |

Soak occupancy is not widget stability, and human observation cannot catch a
50 ms unmount. The repro invariant `post_complete_incomplete_shrink` is also
disabled until a complete-history snapshot is observed, so the traced
nonempty→empty transitions were never rejected.

## 4. Resolved disagreements

- **Which is "the" root cause?** Report A names the dual publication; report B
  names widget identity plus the merge guard. Both are verified and both are
  required: the atomic apply (A) eliminates the traced `0→17` double-publish,
  but without tribe-stable widgets (B) a *legitimate* one-frame occupancy or
  sort-order change still blanks `@epic`; conversely, sticky widgets without
  the atomic apply leave selection/roster state transiently wrong and the
  merge hole still collapses the universe. B's report attributed the ~50 ms
  restore to "two consecutive UI applies" without identifying the second; A's
  proc-sync ordering is that mechanism — they corroborate rather than conflict.
- **Is the Rust core at fault?** B says no (presentation state); A says not
  proven but hardening-worthy. Consolidated position: the index rebuild is
  transactional and is not the demonstrated producer of the zeros, so the fix
  is TUI-side first — but the cached bounded query runs multiple SELECTs
  without one read transaction, and the cache validates on file mtimes rather
  than a logical generation, so an anomalous zero remains possible and
  currently undiagnosable. Core hardening is justified follow-up, not the fix.
- **Ordering of phases.** B lands widget stability first; A lands the atomic
  apply first. Recommendation below puts the atomic apply first because it is
  the mechanism behind every *traced* occurrence and fixes state (selection,
  folds), not just paint; widget stability lands immediately after (or in
  parallel) because it is the only fix for sibling-tribe slot remapping, which
  no merge or apply change can address.

## 5. What not to do

- Do not slow refreshes, add debounce delays, or paint a spinner — the empty
  frame is a published apply, not a slow paint.
- Do not force Tier 2 / unwindowed history on every refresh; that reverts
  sase-127's CPU win (~54% → ~0.25 cores).
- Do not only debounce `initially_expanded` (hides the fold reset, leaves the
  unmount) or collapse to merged mode (avoids the slot bug, ignores the 0-row
  apply).
- Do not treat `has_more=false` as proof a bounded snapshot may delete by
  omission — anywhere.

## 6. Recommended solution

### Phase 1 — Atomic roster publication (fixes the traced flicker)

Refactor the disk-apply path so composition happens before the single
publication:

1. Capture the effective proc projection **and a monotonically increasing proc
   generation** when preparing the apply boundary.
2. Merge proc-shell agents with the disk/cached/fleet roster *before* fold
   filtering, query filtering, selection planning, and panel-key calculation.
3. At the UI-thread commit point, compare the proc generation; if it moved,
   rebase on the latest projection before publishing.
4. Assign app state and call `_finalize_agent_list()` **exactly once**; remove
   the post-finalize `_sync_proc_shell_agents_from_projection()` call from the
   disk-apply path (observer events outside an apply keep the event-facing
   wrapper, but an in-flight apply coalesces with them).

### Phase 2 — Tribe-stable panel widgets (fixes sibling-churn and blank-frame flicker)

1. Key `AgentList` widgets by panel key (`agent-list-panel-epic`, …), not slot
   index; keep a slot-0 compatibility alias. Reorder children on sort changes
   instead of repainting.
2. Add single-panel insert/remove to the incremental path; drop the
   `next_panel_keys != old_panel_keys ⇒ full rebuild` shortcut.
3. Keep configured tribes (`ace.tribes`, including `epic`) mounted at 0 rendered
   rows — render the collapsed title strip instead of unmounting; do not retire
   their fold intents; apply `initially_expanded` only on first mount per
   session.
4. Never `clear_options()`/`update_list` a widget whose row identities and
   grouping signatures are unchanged.
5. Delete the `if self._agent_search_query: return False` bail in
   `_try_remove_agent_rows` (finish sase-127.2): row-remove operates on
   post-filter visible lists, exactly like the display diff.

### Phase 3 — Removal authority and core hardening (prevents recurrence)

1. Widen the merge guard: an incomplete load may replace the cache only when
   `complete_history` is true or it is an artifact delta with explicit
   tombstones. `bounded_prefix` loads always patch by identity regardless of
   `has_more`; in particular, a same-query bounded zero over a nonempty cache
   keeps the cache, logs `empty_incomplete_apply_ignored`, and schedules one
   revalidated load. (A query *change* may legitimately empty the tab.)
2. Clear the complete-history latch only on an actual committed-query change,
   never on an incomplete apply with a missing/mismatched `history_query_key`.
3. Converge `tier1_index_revalidate` with the auto-refresh patching semantics
   so its 41–696 swings cannot change panel keys.
4. Rust core follow-up: run candidate selection, machine-tree expansion, and
   hydration in one SQLite read transaction; return a logical index generation
   the Python cache validates against, and consider an explicit
   `snapshot_authoritative` wire flag so removal authority is stated, not
   inferred.

### Regression tests and trace invariants

- Proc row present only in the projection (not the cached roster) + empty disk
  load ⇒ the first and only finalize contains `@epic`.
- Proc generation moves between worker prep and UI commit ⇒ latest projection
  published.
- Same-query bounded zero over nonempty cache ⇒ cache retained; changed-query
  zero ⇒ allowed.
- Sibling `chop` row added/removed while an `epic` row stays ⇒ epic widget
  object identity unchanged, no `update_list`, option count never 0.
- Standing nonempty query + identity removal ⇒ stays incremental, no
  `active_search` fallback.
- Revalidate 41-over-696 ⇒ applied identity set unchanged.
- Trace-level invariant: one logical apply must not emit `N → 0 → N` visible
  rows or lose and regain a panel key; trace `history_query_key`, proc
  generation, published panel keys, snapshot authority, and removal evidence
  on the apply span.

### Verification on the live host

Before measuring, confirm the interactive TUI's PID and imported SHA (the
sase-12p stale-code check — two PIDs were writing load logs on 2026-09-19).
Then soak with the real persisted state (`by_status`, `NOT machine:apollo`,
live churn) asserting on traces, not observation: no `2 → 1 (agents=0) → 2`
panel sequences, zero `active_search` fallbacks in steady state, zero full
rebuilds on unchanged panel keys, and `@epic`'s widget id continuously present
in `refresh_panel_widgets` spans.

## 7. Sources

- Report A: apply-boundary atomicity analysis (trace forensics, apply-path code
  walk, Rust index review, production query probe).
- Report B: widget-identity and merge-guard analysis (panel model, display
  fallback census, prior-epic postmortem, live load-log statistics).
- Lead verification (2026-09-19, master): `_loading_apply.py` finalize-then-sync
  ordering and latch clearing; `_proc_action_completion.py:198` second
  finalize; `_loading_compute_merge.py` guard conditions; `_display_helpers.py`
  index-keyed ids; `_agent_list_build_rebuild.py:122` `clear_options`;
  `_display_panel_patches.py:125` `active_search` bail.
- Prior work: sase-127, sase-12p, commits `7058f16ce`, `155aeee2e`,
  `5b7c4553c`, `1fa7e5fc3`, `3962d8819`, `17c465c`, `6eb51ac49`.
