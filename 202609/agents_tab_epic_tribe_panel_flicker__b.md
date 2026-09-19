# Agents-tab `@epic` tribe panel flicker: remaining causes and recommended fix

Independent analysis of why the `@epic` Agents-tab tribe panel still
disappears and reappears after several landed fixes.

- **Date:** 2026-09-19
- **Host evidence:** athena, live `sase tui` processes and
  `~/.sase/logs/tui_agent_loads.jsonl` / `~/.sase/perf/tui_trace.jsonl`
- **Persisted Agents UI state on this host:** grouping `by_status`
  (`~/.sase/grouping_mode.txt`), committed query
  `NOT machine:apollo` (`~/.sase/ace_agents_last_query.json`)

## 1. Answer

The panel is not a stable widget. It is a **slot in an index-addressed
list** whose occupancy is recomputed from the *currently visible* agent
rows. `@epic` unmounts whenever that visible set has zero rendered
members in tribe `epic`, and it also *looks* like it vanished whenever
a neighboring tribe appears or disappears, because the widgets are
keyed as `agent-list-panel`, `agent-list-panel-1`, … rather than as
`epic` / `chop` / `default`.

Two closed epics already targeted this symptom (sase-127 on 2026-09-17,
sase-12p on 2026-09-18). They stopped the original load-tier 171↔484
oscillation and the BY_STATUS “rebuild every refresh” path. They did
**not** make the widget identity tribe-stable, did **not** finish the
active-query incremental path (row-remove still bails on any nonempty
search query), and did **not** prevent empty incomplete applies from
briefly publishing a 0-row Agents tab.

Live traces on this host still show the collection flipping `2 → 1 → 2`
panels, including `17 agents / 2 panels → 0 agents / 1 panel → 17
agents / 2 panels` in ~50 ms. That is the visual flicker: every tribe
panel, `@epic` included, is torn down for a frame and then remounted,
which also re-applies `ace.tribes.epic.initially_expanded`.

**Recommended fix:** keep tribe panels as stable widgets (id-by-tribe,
sticky configured tribes, no `clear_options` on untouched panels), and
close the two remaining apply/display holes that still publish an empty
or rebuilt collection under the user’s standing `NOT machine:apollo`
query. Details in [§8](#8-recommended-solution).

## 2. How a tribe panel is allowed to vanish

### 2.1 Panels exist only while at least one rendered row maps there

`panel_keys_for` (`src/sase/ace/tui/models/agent_panels.py`) builds the
split-panel collection from **rendered** agents (`status != "STARTING"`)
and each row’s presentation-anchor tribe. No members ⇒ no key ⇒ no
widget.

The empty Agents tab is special-cased to `[None]` (the reserved
`@default` slot). A 0-row apply therefore does not keep `@epic`
mounted; it replaces the whole collection with a single empty default
panel.

Whole-panel fold intent is retired when a key stops being live
(`retire_panel_fold_intents` in
`src/sase/ace/tui/actions/agents/_panel_fold_intent.py`). Config
documents the consequence: when the panel later returns,
`initially_expanded` is applied again
(`docs/configuration.md`, `ace.tribes.initially_expanded`).

### 2.2 Widgets are addressed by slot index, not by tribe

```python
# src/sase/ace/tui/actions/agents/_display_helpers.py
def panel_widget_id(panel_idx: int) -> str:
    if panel_idx == 0:
        return "agent-list-panel"
    return f"agent-list-panel-{panel_idx}"
```

`_refresh_panel_widgets` mounts missing *indices*, removes extra
indices, then calls `update_list` on every remaining `AgentList`.
`build_list` starts with `widget.clear_options()`.

Consequences:

| What actually changed | What the user sees |
| --- | --- |
| `@epic` membership hits zero | The `@epic` widget is removed (or the slot is reused for another tribe) |
| A tribe *before* `epic` alphabetically appears or disappears (`@default`, `@chop`, …) | The same DOM node that was showing `@epic` is `clear_options()`’d and filled with a different tribe. `@epic` “jumps” or “vanishes” from its old slot |
| Full rebuild with *unchanged* keys | `@epic` stays in the same slot but blanks for a frame (`clear_options`) |
| Brief 0-row apply | All named tribes unmount; one empty `@default` remains; then they remount and re-expand |

This is why the symptom is reported as “the `@epic` panel flickers”
even when `@epic` membership itself is stable.

### 2.3 Incremental refresh refuses to run once the key set moves

`_try_refresh_agents_display_incremental`
(`src/sase/ace/tui/actions/agents/_display.py`) requires
`next_panel_keys == old_panel_keys`. Any tribe appearing or emptying
records `panel_membership_change` and falls back to the full rebuild
above. There is no “insert/remove one panel, leave the others
untouched” path.

## 3. What was already tried (and what it actually closed)

| When | Work | What it fixed | What it left |
| --- | --- | --- | --- |
| 2026-07 | `agents_tab_left_panel_flicker` / left-TUI flicker | Off-tab / footer / CL refresh flicker | Not tribe-panel occupancy |
| 2026-08 | `agent_row_tribe_panel_latch` (17c465c) | Pre-metadata rows latching into `@default` because `_tier1_merge_key` changed when `parent_timestamp` appeared | Still possible for `tribe is None` rows to *create* `@default` and shift later slots |
| 2026-09-17 | **sase-127** “Fix Agents-tab flicker and disappearing tribe panels” (7058f16ce, 155aeee2e, 5b7c4553c, 677ed7d8e) | Bounded incomplete loads patch over cache instead of replacing; stable search query no longer forces `active_search` *display* fallback; no-op fleet reprojection skips `_finalize_agent_list`. Soak: `@epic` mounted 30 min, apply counts ~606–625, no 171↔484 swing | Index-addressed widgets; row-remove still `active_search`; BY_STATUS still full-rebuilded; 0-row incomplete applies not guarded |
| 2026-09-18 | **sase-12p** “Keep tribe panels mounted under BY_STATUS…” (1fa7e5fc3, plus stale-TUI detector) | BY_STATUS admitted to the incremental path; explained why the sase-127 soak did not match the running TUI (process imported on 2026-09-16, fixes landed 2026-09-17, Update panel reported “current”) | BY_DATE still `unsupported_grouping`; widget ids still index-based; row-remove still refuses any nonempty query |
| 2026-09-18 | `agent_node_refresh_isolation` / 3962d8819 | Worker copies of `Agent` graphs so provider icons / family links do not clear on the live objects mid-refresh | Different symptom (node contents, not panel unmount). Does not keep `@epic` mounted |

sase-127.land and sase-12p.land both recorded 30-minute athena soaks
with `@epic` continuously mounted. The user seeing the panel again
today is not a contradiction of those soaks: the soaks measured
*membership of `epic` in `panel_keys_for` under the loads they
exercised*. They did not make the widget identity tribe-stable, and
they did not run against the remaining apply holes below, which still
show up in today’s traces.

## 4. Remaining causes, ranked

### Cause A (highest confidence): empty incomplete applies still reach the display

`~/.sase/perf/tui_trace.jsonl` (tail of the 514 MB live file) contains
repeated `agents.refresh_panel_widgets` sequences:

```
2 panels / 17 agents  →  1 panel / 0 agents  →  2 panels / 17 agents
```

with the empty state lasting on the order of **50 ms**. `panel_keys_for([])`
returns `[None]`, so `@epic` is unmounted, then remounted, then
`initially_expanded` is applied again.

That pattern is too fast to be a disk round-trip. It is two consecutive
UI applies: one publishing an empty visible list, one restoring the
previous universe.

`merge_incomplete_load_after_complete_history`
(`src/sase/ace/tui/actions/agents/_loading_compute_merge.py`) *should*
prevent a partial load from replacing a cached universe, but only when
one of these is true:

- `snapshot.agents_seen_complete_history` (the complete-history **query
  latch**), or
- `artifact_source == "artifact_delta"`, or
- `bounded_prefix and has_more`

Otherwise it returns the incoming prep unchanged. A 0-row (or
tiny-row) load then becomes the published roster.

The latch is cleared on any apply whose `history_query_key` does not
match:

```python
# src/sase/ace/tui/actions/agents/_loading_apply.py
elif not history_complete_for_query:
    self._agents_complete_history_query_key = None
    self._agents_seen_complete_history = False
```

And `has_more` is a weak signal: a windowed index read that returns
fewer rows than `requested_limit` reports `has_more=False` even when
the archive is large. Combined with a cleared latch, that load is a
**replacement**, not a patch.

Today’s `tui_agent_loads.jsonl` (2026-09-19 07:34–11:40 UTC) on the
main TUI PID **1598377**:

| Source | Incoming `agents` |
| --- | --- |
| `auto_refresh` | 210–238 (stable bounded prefix) |
| `tier1_index_revalidate` | **41–696** (still swinging) |
| `startup_prefix_completion` | 467 |
| `input_quiet_tier2_reconcile` | 909 |
| `filter` | 0 (once) |

Incoming counts are pre-merge. The 41-vs-696 revalidate swing is the
same *class* of bug sase-127 closed for auto-refresh, still alive on
the revalidate path. A 41-row revalidate with `has_more=False` and a
cleared latch publishes 41 rows (or, in the trace, 0) and drops every
tribe that is not in that slice.

A second TUI PID **1880150** has been applying `auto_refresh full
agents=0` on a ~20–40 s cadence all morning (83/83 auto-refresh slow
records are zeros). If that process is a visible Agents tab, it will
flicker continuously. Even if it is a capture/helper TUI, it shows
that 0-row full applies are a live production path, not a test
fixture.

### Cause B (highest confidence, always-on for this user): active-query row-remove still forces a full rebuild

sase-127.2 removed the blanket `active_search` fallback from
`_try_refresh_agents_display_incremental` when the query *text* is
unchanged. The row-remove helper was not updated:

```python
# src/sase/ace/tui/actions/agents/_display_panel_patches.py
if getattr(self, "_agent_search_query", ""):
    self._record_display_patch_trace(
        display_cost="row_remove",
        fallback_reason="active_search",
        ...
    )
    return False
```

This host’s committed query is never empty (`NOT machine:apollo`).
`machine` is a pushdown-safe field, so the query stays active in
steady state.

Any identity leaving the visible set (status change that the query
drops, inflight poll, watcher delta, dismiss, STARTING exclusion)
therefore:

1. Enters the incremental path (query unchanged, BY_STATUS admitted).
2. Hits `_try_remove_agent_rows`, which refuses because a query is
   active.
3. Returns False from the incremental impl.
4. `_refresh_agents_display(list_changed=True)` runs
   `_refresh_panel_widgets`, which `clear_options()`s **every** panel
   including `@epic`.

If the removal also empties some tribe, the key set changes first
(`panel_membership_change`) and the same full rebuild remaps slots.

This is why the flicker is intermittent rather than constant: it fires
on membership churn, which on athena is frequent but not every tick
(row-patch of in-place badge updates can still succeed).

### Cause C (high confidence): sibling-tribe occupancy churn remaps `@epic`’s widget

Even with `@epic` membership rock-solid, `panel_keys_for` is the set
of *all* occupied tribes, sorted alphabetically, `@default` first.

Anything that briefly creates or destroys a key that sorts before
`epic` (`None` / `@default`, `chop`, …) changes `@epic`’s index.
`_refresh_panel_widgets` then paints a different tribe into the widget
the user was looking at.

Known producers of a transient `@default`:

- Rows with `tribe is None` (pre-metadata RUNNING claims,
  `agent_meta.json` not yet written). The August latch fix stops those
  rows from *staying* wrong; it does not stop them from existing for
  one apply.
- `STARTING` rows are excluded from rendering
  (`agent_is_rendered_in_agents_panel`). An `@epic` family whose last
  visible members are all `STARTING` (epic launch fan-out, revive,
  retry) unmounts the panel until they become `RUNNING`.

`tribe` is in `KNOWN_FALLBACK_FIELDS`
(`src/sase/ace/tui/models/agent_live_query_pushdown.py`): a
`tribe:…` query is not window-safe. The user’s actual query is
`NOT machine:apollo`, which *is* pushable. The standing query does not
need to mention `epic` for `@epic` to unmount; it only needs the
visible set to lack epic-anchored rows.

### Cause D (medium): remaining full-rebuild fallbacks besides B

From the same trace tail, `agents.refresh_work` fallbacks:

| Reason | Typical source | Notes |
| --- | --- | --- |
| `unsupported_grouping` | `fleet_refresh`, `auto_refresh` | Incremental admits STANDARD / BY_STATUS / BY_MACHINE only. **BY_DATE** still rebuilds every time. This host currently persists `by_status`, so this should be idle *if* the running process imported sase-12p. If the process is stale, this is the sase-12p.2 story again |
| `panel_membership_change` | fleet / auto_refresh / inflight_poll / notification | Cause A/C |
| `stale_grouping_mode` | mixed | Widgets’ `_grouping_mode` disagrees with the app (grouping picker / remount) |
| `status_membership_change` | local mutation | Genuine BY_STATUS bucket move; rebuild is correct, but still `clear_options`s sibling tribes |
| `search_query_changed` | filter | Expected on an actual query edit |

`widget.agent_list.update_list` still appears often in the trace (203
events in the 12 MB tail). Each one blanks an `OptionList`.

### Cause E (operational, still real): the running TUI may not be running the landed code

sase-12p.2 exists specifically because this host’s long-lived
editable-install TUI kept executing the 2026-09-16 import while
sase-127 sat on disk. `tui_perf.md` rule 15 is the same invariant.

Today there are two PIDs writing `tui_agent_loads.jsonl`. A soak
against HEAD does not describe a process that started before HEAD.
The Update-panel stale-code row must be checked before treating a
live flicker as a new logic bug; it can also *coexist* with A–D.

### Cause F (related, not this symptom): in-place graph mutation

3962d8819 copies cached `Agent` graphs before worker
`_normalize_relationships_after_merge`. That stopped provider icons
and clan child links from going empty on the *already mounted* panel
(the 2026-09-18 “nodes flicker” report). It does not prevent the
panel widget from being unmounted. Treat icon flicker and panel
unmount as separate bugs if both are still visible.

## 5. Live evidence (2026-09-19)

### 5.1 Panel-count flaps in `tui_trace.jsonl`

`agents.refresh_panel_widgets` in the recent tail:

- 97 spans with `panels=2`
- 8 spans with `panels=1`
- 7 transitions `2→1` and 7 `1→2`

Representative empty flashes (monotonic `ts` from the trace file):

| From | To | Restore |
| --- | --- | --- |
| 2 panels / 17 agents | 1 panel / 0 agents | 2 panels / 17 agents in ~54 ms |
| 2 panels / 17 agents | 1 panel / 0 agents | 2 panels / 17 agents in ~55 ms |
| 2 panels / 26 agents | 1 panel / 0 agents | 2 panels / 17 agents in ~25 ms |

A 0-row visible list is sufficient to unmount `@epic`. The restore
remounts it. That matches the user report exactly.

Dominant display fallbacks in that tail: `panel_membership_change`
and `unsupported_grouping`. Incremental spans are rare relative to
`display_full_rebuild` (18 vs 231 in the 8 MB slice).

### 5.2 Incoming load sizes in `tui_agent_loads.jsonl`

Main interactive TUI (PID 1598377): bounded auto-refresh has
converged (~230). **Revalidate has not** (41–696). One
`input_quiet_tier2_reconcile` reached 909. One `filter` load logged
0 agents.

Helper/other TUI (PID 1880150): every logged auto-refresh is a 0-row
full load.

These numbers are loader `all_agents` lengths, recorded before merge.
They are the *inputs* that Cause A’s merge guard is supposed to
absorb. The 0-row display flashes in §5.1 show that at least some of
those inputs are still being published.

### 5.3 Why `@epic` specifically

Bundled tribes include `epic` with an icon and
`initially_expanded: true`. This host’s Agents tab is split by tribe
(not merged), grouping `by_status`, query `NOT machine:apollo`.
`@epic` is usually one of two visible panels, so it is the panel the
user is watching; the mechanism is not epic-specific. Any named tribe
with intermittent occupancy, or any tribe whose slot index moves,
would flicker the same way.

## 6. Why previous soaks could pass and the bug still show

1. **Soak occupancy ≠ widget stability.** Asserting `panel_keys_for`
   still contains `"epic"` for 30 minutes does not assert that
   `id=agent-list-panel-1` continued to *be* the epic widget, nor that
   `clear_options` was not called on it.
2. **0-row flashes are tens of milliseconds.** A human soak note
   “continuously mounted” can miss a 50 ms unmount; a trace query on
   `panels` does not.
3. **The standing query keeps row-remove off the incremental path.**
   A soak with no identity churn (or with an empty query) never hits
   Cause B.
4. **Stale imported code.** sase-12p.2 is the documented reason the
   2026-09-17 soak and the 2026-09-18 user report disagreed.

## 7. What not to do

- Do not “fix” this by slowing refreshes, coalescing more, or
  painting a spinner over the Agents list. The empty frame is a
  published apply, not a slow paint.
- Do not force Tier 2 / unwindowed history on every auto-refresh.
  sase-124 is the freshness/cost epic; broadening loads will bring
  back the CPU that sase-127 just removed (~54% → ~0.25 cores).
- Do not treat this as a `sase-core` bug. Panel identity, merge
  guards, and display fallbacks are TUI presentation state.
- Do not only debounce `initially_expanded`. That hides remount
  fold-reset and leaves the unmount itself in place.
- Do not collapse split tribes into merged mode as the fix. Merged
  mode avoids the slot-index bug by having one widget; it does not
  explain or fix the 0-row apply.

## 8. Recommended solution

Do these as one epic with two phases that can land independently.
Phase 1 stops the *visual* flicker even when occupancy legitimately
changes for a frame. Phase 2 stops the *false* 0-row / shrink
publishes so occupancy itself stops oscillating.

### Phase 1 — Make tribe panels stable widgets (this is the actual UI bug)

1. **Key `AgentList` widgets by panel key, not by index.**
   Replace `panel_widget_id(idx)` with a tribe-stable id
   (`agent-list-panel-default`, `agent-list-panel-epic`, …). Keep a
   compatibility alias for slot 0 if tests/callers hardcode
   `#agent-list-panel`. Reorder container children when the sort
   order changes; do not `update_list` a widget whose tribe did not
   change.
2. **Insert/remove one panel without rebuilding siblings.**
   When `panel_keys` grows or shrinks, mount or `remove()` only the
   affected `AgentList`. Drop the
   `next_panel_keys != old_panel_keys ⇒ display_full_rebuild`
   shortcut in `_try_refresh_agents_display_incremental`. Record a
   new display cost such as `display_panel_insert` /
   `display_panel_remove`.
3. **Sticky configured tribes.**
   For every tribe in `ace.tribes` (at least the bundled `epic` /
   `job` / `review` / `pinned` / `default`), keep the widget mounted
   while the TUI session runs, even at 0 rendered rows. Render the
   existing collapsed title strip (or an empty expanded panel)
   instead of unmounting. Do **not** call `retire_panel_fold_intents`
   for configured keys. Do **not** re-apply `initially_expanded`
   except on first mount of the session.
4. **Stop `clear_options` on untouched panels.**
   Full `_refresh_panel_widgets` must not call `update_list` on a
   widget whose row identities and grouping signatures are unchanged.
   `clear_options` is the frame of blank the user reads as
   “disappeared.”

Acceptance for phase 1: a test that adds and removes a `chop` row
while an `epic` row stays put asserts the epic widget object identity
is unchanged, `update_list` is not called on it, and its option count
does not go to 0. A 0-row incomplete apply must leave the epic widget
mounted.

### Phase 2 — Stop publishing a smaller universe than the cache already has

1. **Patch, don’t replace, any incomplete load once a larger cache
   exists.** Widen
   `merge_incomplete_load_after_complete_history` so the skip
   condition is only `load_state.complete_history` (authoritative
   full snapshot) or an artifact-delta with explicit tombstones.
   `has_more=False` on a bounded/windowed read must not mean
   “this is the whole universe.”
2. **Never clear the complete-history latch on an incomplete apply.**
   Clear it only when the committed query key actually changed
   (`search_query_changed` / stale-query discard). Incomplete loads
   with a missing or mismatched `history_query_key` must not reset
   `_agents_seen_complete_history`.
3. **Hard-stop empty incomplete applies.** If incoming
   `filtered_agents` is empty, `complete_history` is false, and the
   cache is nonempty, keep the cache. Log/trace it
   (`empty_incomplete_apply_ignored`). This is the 50 ms 0-row flash
   in §5.1.
4. **Finish sase-127.2.** Delete the
   `if self._agent_search_query: return False` guard in
   `_try_remove_agent_rows` (and any sibling `active_search` bails
   that are not “the query *text* changed”). The display-diff path
   already operates on post-filter visible lists; row-remove must
   match. Add a guard test: standing query `NOT machine:apollo`,
   BY_STATUS, one identity removed, `update_list_calls == 0` on the
   epic widget, no `active_search` fallback.
5. **Converge revalidate with auto-refresh.**
   `tier1_index_revalidate` still arrives as 41–696 rows on PID
   1598377. After (1)–(3), a 41-row revalidate must not change
   `panel_keys`. Add the sase-127.1 panel-key stability test for
   *revalidate* loads, not only `bounded_prefix=True, has_more=True`.

Acceptance for phase 2: replay a recorded 0-row notification/auto
apply against a 17-row two-tribe cache and assert panel keys stay
`[..., "epic"]`, widget identities stay put, and
`_agents_seen_complete_history` stays true. Revalidate 41-over-696
must keep 696 identities.

### Phase 3 — Prove it on the running host (short)

1. Restart the interactive TUI onto the landed tree (sase-12p.2
   stale-code row). Confirm PID and imported SHA before measuring.
2. Soak on athena with the real persisted state (`by_status` +
   `NOT machine:apollo` + live churn) and `SASE_TUI_TRACE=1`.
3. Trace assertions, not vibes:
   - `agents.refresh_panel_widgets` never reports `panels` dropping
     `@epic`’s widget id (once ids are tribe-stable, log `panel_keys`
     on that span).
   - No `2 → 1 (agents=0) → 2` sequences.
   - `fallback_reason=active_search` is zero in steady state.
   - `display_full_rebuild` on unchanged `panel_keys` is zero.
   - Incoming revalidate size may still vary; *applied* identity set
     and epic widget identity may not.
4. Extend `tests/perf/test_agents_display_rebuild_guard.py` with:
   - sibling-tribe insert/remove does not rebuild epic
   - nonempty standing query + row remove stays incremental
   - empty incomplete apply does not unmount a configured tribe

### Suggested sequencing

Land **phase 1 first**. It makes the remaining apply holes much less
visible and is the only change that fixes sibling-tribe remapping,
which no merge-guard can fix. Land phase 2 immediately after so the
0-row publish cannot still collapse height/layout or reset folds on
sticky empty panels. Phase 3 is the same instruments sase-127.4 /
sase-12p.3 already used; add `panel_keys` / widget ids to those
spans so the next report does not have to infer occupancy from
`panels=1`.

BY_DATE incremental support is optional follow-up. It is the
remaining `unsupported_grouping` source. This host is on `by_status`;
do not block the `@epic` fix on BY_DATE.

## 9. Code map

| Path | Role |
| --- | --- |
| `src/sase/ace/tui/models/agent_panels.py` | `panel_keys_for`, STARTING exclusion, `@default` empty state |
| `src/sase/ace/tui/actions/agents/_display_helpers.py` | Index-based `panel_widget_id` |
| `src/sase/ace/tui/actions/agents/_display_panel_widgets.py` | Mount/unmount by index; `update_list` / `clear_options` |
| `src/sase/ace/tui/actions/agents/_display.py` | Incremental vs full rebuild; `panel_membership_change` |
| `src/sase/ace/tui/actions/agents/_display_panel_patches.py` | `active_search` row-remove bail |
| `src/sase/ace/tui/actions/agents/_loading_compute_merge.py` | Incomplete-load patch vs replace |
| `src/sase/ace/tui/actions/agents/_loading_apply.py` | Complete-history latch set/clear; UI apply |
| `src/sase/ace/tui/actions/agents/_panel_fold_intent.py` | Fold-intent retirement on unmount |
| `src/sase/ace/tui/widgets/_agent_list_build_rebuild.py` | `clear_options()` at the start of every `update_list` |
| `src/sase/ace/tui/models/agent_live_query_pushdown.py` | `machine` pushable; `tribe` / `status` fallback fields |
| `tests/perf/test_agents_display_rebuild_guard.py` | Existing “don’t remount `@epic`” guards to extend |
| `docs/configuration.md` | `initially_expanded` re-applied on remount |

## 10. Sources

- Plan `202609/agents_tab_flicker.md` (sase-127, status done)
- Plan `202609/by_status_panels_and_stale_tui.md` (sase-12p, status done)
- Plan `202609/agent_node_refresh_isolation.md` (graph copy / node flicker)
- Plan `202608/agent_row_tribe_panel_latch.md` (pre-metadata tribe latch)
- Memory `tui_perf.md` rules 5, 6, 15
- Beads sase-127, sase-12p (closed land notes and soak claims)
- Commits 7058f16ce, 155aeee2e, 5b7c4553c, 1fa7e5fc3, 3962d8819
- `~/.sase/logs/tui_agent_loads.jsonl` (2026-09-19, PIDs 1598377 and 1880150)
- `~/.sase/perf/tui_trace.jsonl` (panel-count flaps and fallback reasons)
- Persisted `~/.sase/grouping_mode.txt` = `by_status`
- Persisted `~/.sase/ace_agents_last_query.json` = `NOT machine:apollo`
