# Agents-tab selection jump: why the focused node moves on athena

**Researcher:** A · **Date:** 2026-09-21 · **Scope:** code research, no repro on athena hardware
**Question:** the selected/focused node on the Agents tab spontaneously jumps to some
other node; seen very often on athena, (as far as known) never on this machine.

## Executive summary

The Agents tab has **two** selection-like states that must agree: the selected agent
(`current_idx`, restored across refreshes by stable identity) and the focused tribe
panel (`_panel_group.focused_idx`). I found one mechanism that forcibly re-syncs them
in the wrong direction on **every background refresh**, plus two narrower races. All
three are data-churn-gated, which explains the athena-only symptom: athena is the
fleet/import hub (hundreds of foreign v1 rows, followed remote agents, staged fleet
catalog arrivals), so its roster and panel membership churn constantly while this
machine's list is quiet.

Ranked causes:

1. **Primary — `_sync_panel_group` snaps `current_idx` to the focused panel**
   (`src/sase/ace/tui/actions/agents/_display_panel_collection.py:204-234`). It runs
   inside every incremental display refresh
   (`src/sase/ace/tui/actions/agents/_display.py:466`). Whenever the selected agent's
   panel disagrees with the focused panel — after any reorder, fleet arrival,
   provisional-row swap, or container-identity flip moves the selected row across
   panels — the cursor is yanked to the **first row of the focused panel**. That reads
   exactly as "my node jumped to some other node."
2. **Secondary — async finalize snap-back to a stale identity**
   (`src/sase/ace/tui/actions/agents/_loading_finalize.py:456-512`). The non-plan
   recompute path uses a *fresh* row but a *stale* identity; when the stale identity
   still exists, `restore_selection_by_identity` prefers it and undoes the user's last
   navigation. The 250 ms nav gate (`src/sase/ace/tui/util/nav_gate.py:14`) is checked
   at refresh *start*, not at *apply*, so any j/k pressed mid-load is unprotected.
3. **Tertiary — unguarded `SelectionChanged` local→global mistranslation**
   (`src/sase/ace/tui/actions/_event_widgets.py:102-203`). The app handler resolves
   `event.index` against the *current* panel slice. A highlight message queued before a
   rebuild is translated against the *new* slice and writes a wrong `current_idx`.
   Other panes use `ProgrammaticSelectionGuard`
   (`src/sase/ace/tui/util/selection.py:32-71`); the Agents path relies only on a
   synchronous boolean flag (`src/sase/ace/tui/widgets/agent_list.py:455-500`).

**Recommended solution:** fix the sync direction in `_sync_panel_group` — when
selection and focused panel disagree after a data refresh, move the *panel focus* to
the selection (or leave both alone), never move the *selection* to the panel. As
defense in depth, re-check the nav gate (or re-capture identity) at apply time in the
async finalize path, and adopt `ProgrammaticSelectionGuard` for Agents
`SelectionChanged` handling. Before any code change, restart the athena TUI once: a
long-lived process may predate the row-0 phantom-echo fix and restarting rules out
stale-running-code in one step.

## Background: how Agents-tab selection survives refreshes

- `current_idx` is the selected agent's index into `self._agents`. Every rebuild
  restores it by **stable identity** `(AgentType, cl_name, raw_suffix)` with a
  clamped-row neighbor fallback (`src/sase/ace/tui/util/selection.py:74-113`).
  `AgentType` is a static kind (`run`/`workflow`/`proc-shell`), not status, so status
  flips alone do not break identity (`src/sase/core/agent_types.py:8-14`,
  `src/sase/ace/tui/models/agent.py:410-431`).
- Container rows (clan / imported-family / remote-family) key identity on family names
  plus generation/suffix — stable only while family reconstruction is deterministic.
- The list is split into tribe/machine panels (`_panel_group.focused_idx` = focused
  panel). j/k navigation keeps both in sync
  (`src/sase/ace/tui/actions/agents/_neighbors.py:377-431`).
- Refreshes are coalesced last-request-wins
  (`src/sase/ace/tui/actions/agents/_loading_refresh.py:97-140`) and run off-pump;
  display updates prefer in-place patching over rebuilds
  (`src/sase/ace/tui/actions/agents/_display.py:254-334`).
- A 250 ms `NavigationGate` defers refresh *start* and fleet-projection *apply* while
  the user is mid-burst on j/k — but nothing re-checks it at async-finalize apply
  time.

## H1 (primary): panel sync moves the selection, not the focus

`_sync_panel_group` recomputes panels from the new roster (preserving the old focused
key when it still exists), then does this
(`_display_panel_collection.py:204-214`):

```python
if 0 <= self.current_idx < len(self._agents):
    if (
        keys_per_agent[self.current_idx] != focused_key
        or panel_index.local_idx_for(focused_key, self.current_idx) < 0
    ):
        self._snap_current_idx_to_focused_panel(keys_per_agent, focused_key)
```

and `_snap_current_idx_to_focused_panel` sets `current_idx` to the **first agent of
the focused panel** (falling back to row 0). This runs on *every* incremental refresh,
i.e. on nearly every background tick that changes anything. The finalize step just
before it did the right thing (identity restore → cursor follows the agent); the snap
then undoes it whenever the agent now lives in a different panel than the focus.

Divergence sources (selection panel ≠ focused panel), all data-driven:

- **Fleet rows arrive in stages** (summary → followed → attention → paged catalog;
  `_fleet_refresh.py:88-191`). Machine panels pop in/out; a selected remote row hops
  panels as `fleet_origin_alias`/family data fills in.
- **Provisional dispatch rows are replaced by authoritative rows** with different
  identities (`_loading_apply.py:281-293`, `_fleet_projection.py:144-202`).
- **BY_MACHINE grouping** (natural on a fleet hub) makes every worker
  unavailability event a panel-membership change.
- **v1 import container rows on athena** (`imported-family:…` identities): prior
  research found family containers are not reconstructed consistently across loads,
  so a selected container row can vanish or re-key between refreshes — identity miss
  → neighbor fallback → snap.
- **Any re-sort** (status-bucket moves under BY_STATUS, clan regrouping) that carries
  the selected agent across a panel boundary.

Why athena only: this machine has no federation rows, no import churn, and few
concurrent agents, so selection and focus almost never diverge and the snap is a no-op.
Athena has all of the above plus constant refresh traffic (auto-refresh ticks,
notification/attention announcements, proc-projection generations), so the snap fires
"very often." Each firing lands on the focused panel's first row — characteristically
"some other node," often near the top.

## H2 (secondary): async finalize prefers the stale identity

`_load_agents_async` correctly re-captures selection *after* the disk await
(`_loading_disk_full.py:272-279`). But the worker-prep phase
(`prepare_loaded_agents_worker_boundary`) takes additional time, and the UI-thread
recompute path uses a **fresh row with the stale identity**
(`_loading_finalize.py:456-478`):

```python
saved_idx = app.current_idx ...          # fresh
restored_idx = restore_selection_by_identity(
    app._agents,
    prior_identity=selected_identity,     # stale (pre-worker value)
    prior_visual_row=saved_idx,           # fresh
    ...
)
```

`restore_selection_by_identity` returns the stale identity's index whenever it still
exists — i.e. a j/k pressed during the worker phase is silently reverted. The worker
plan's stale-token check (`_loading_compute_finalize.py:290-320`,
`_loading_apply.py:295-345`) discards the plan in exactly this case, but the fallback
recompute repeats the same staleness instead of re-capturing. The nav gate does not
cover this window: it is consulted at refresh start
(`_loading_refresh.py:199-202`) and fleet-apply time
(`_fleet_refresh.py:203-251`), never at finalize-apply time. Roster size stretches the
window — milliseconds locally, far longer on athena with hundreds of rows plus content
index and fleet widening — matching the machine asymmetry.

## H3 (tertiary): highlight echo translated against the wrong roster

`AgentList.on_option_list_option_highlighted` posts `SelectionChanged` for any
non-programmatic highlight (`agent_list.py:661-674`), and the app handler maps the
*local* row to a *global* index using the *current* panel slice
(`_event_widgets.py:131-147`). The programmatic guard is a synchronous boolean cleared
in `finally` (`agent_list.py:455-500`, `_agent_list_build_rebuild.py:63-172`,
`_agent_list_build_patching.py:120-129`); anything queued across a rebuild (Textual
pump ordering, hover-driven highlights, post-remove clamp messages) is translated
against the new roster and writes a wrong `current_idx`. Sibling panes solved this
class of bug with the identity-carrying `ProgrammaticSelectionGuard`; the Agents path
never adopted it. This predicts occasional single-row jumps correlated with
dismiss/kill completions (in-place row removal shifts) — worth checking against the
observed cadence, but less central than H1.

## Ruled out / minor

- **Status transitions** do not change identity (`AgentType` is static); they only
  matter via panel regrouping (feeds H1).
- **Full rebuilds** re-assert highlight from `current_idx` under guard
  (`_agent_list_build_rebuild.py:168-172`); the rebuild itself is not the jump.
- **Fleet projection apply** re-reads selection fresh at apply time
  (`_fleet_projection.py:166-178`) — clean.
- **Sync loads** capture on the UI thread with no await in between — clean.
- **Mouse hover** moves `highlighted` (hence selection) in Textual OptionLists; only
  relevant if athena's terminal has mouse reporting on — ask the user, don't assume.
- **Stale running code**: the in-code comment documents a prior row-0 phantom-echo
  bug fixed by the synchronous watch guard (`agent_list.py:476-487`, commit
  `b3ecd0772`). Per TUI perf rule 15, a long-running athena TUI predating that fix
  would show exactly this symptom with zero data dependence. Cheap to rule out (see
  verification).

## Verification (proposed, not yet run)

1. On athena: quit and restart the TUI. If jumps stop, it was stale running code —
   done, no patch needed. (`stale_running_code.py` detector + Update-panel notice
   tell you whether the process predates the fix.)
2. If jumps persist, run with `SASE_TUI_TRACE=1` and correlate jumps with
   `agents.refresh_display_incremental` + `display_fallback` reasons
   (`panel_membership_change`) and `refresh.auto_tick` — H1 predicts jumps land on the
   focused panel's first row immediately after membership-changing refreshes.
3. Confirm direction: log `current_idx` vs `focused_key` around `_sync_panel_group`
   (or add a `trace_event` when the snap arm fires). H1 predicts the snap arm fires on
   jump frames; H2 predicts jumps revert the *immediately preceding* j/k target.
4. Existing suites covering this area: `tests/ace/tui/` selection/panel tests plus the
   j/k bench (`pytest -s -m slow tests/ace/tui/bench_tui_jk.py`); any fix should add a
   regression test where a refresh moves the selected agent across panels and asserts
   `current_idx` still points at the same identity.

## Recommended solution

1. **Immediate (user, no code):** restart the TUI on athena; note process start time
   vs. fix history if it recurs.
2. **Primary fix:** in `_sync_panel_group`, when selection and focused panel
   disagree after a *data* refresh, move the focus to the selection
   (`focused_idx` → selected agent's panel) or do nothing — never rewrite
   `current_idx`. Reserve snap-to-panel for explicit user panel actions (Tab/panel
   jumps), where the focus move is the user's own intent. This single direction
   change removes the H1 jump while preserving all collapse/focus bookkeeping.
3. **Follow-ups:** (a) re-check `is_navigating()` (or re-capture `selected_identity`
   from `current_idx`) at finalize-apply time so H2's window closes; make the
   no-plan recompute prefer the fresh row when identity and row disagree;
   (b) adopt `ProgrammaticSelectionGuard` (with event-time slice or identity check)
   in `on_agent_list_selection_changed` to close H3.
4. **Athena-specific hygiene (optional):** prefer STANDARD grouping on the hub if
   BY_MACHINE churn dominates; keep fleet catalog pages bounded so membership
   flaps less often. These reduce trigger frequency but are not substitutes for the
   direction fix.
