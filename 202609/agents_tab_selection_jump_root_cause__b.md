# Agents-Tab Selection Jumping to Another Node — Root-Cause Research

**Researcher:** B (`research.b`) · **Date:** 2026-09-20 · **Repo revision:** `e1ba4851c`

## Bottom line

The Agents tab has **no single authority over "which node is selected."** Three
independent subsystems write `current_idx` on every background refresh, and two of them
are allowed to overrule the user's actual selection:

1. **`_snap_current_idx_to_focused_panel()`** — on *every* list-changed display refresh,
   the tab enforces the invariant *"the cursor must live inside the focused tribe
   panel."* If that invariant breaks for any reason, it moves the cursor to
   `global_indices[0]` — **the first row of the focused panel** — and throws the user's
   selection away. This is the only mechanism that produces a *large, arbitrary* jump,
   and it is my primary suspect.
2. **`restore_selection_by_identity()`'s fallback** — when the selected agent's identity
   is not found in the rebuilt roster, the cursor is clamped to the prior **global
   index**, which on a multi-panel roster is not a visual neighbor at all.
3. **A stale `selected_identity` carried across three `await`s** in the async load —
   drift is *detected* but then *repaired using the same stale identity*, so a j/k move
   made during a slow refresh is silently undone.

All three are strongly load-dependent, which is exactly why athena reproduces and the
MacBook does not. My recommendation (§7) is to **invert the panel-focus/cursor
dependency**: the selected node is the user's stated intent and panel focus is derived
state that should follow it, not the reverse.

> **Verification caveat, stated up front:** I wrote a runtime reproduction against the
> repo's own frame harness (`tests/ace/tui/_epic_arrival_frames.py`) but **could not run
> it**. This workspace's installed `sase_core_rs` wheel is stale
> (`AttributeError: sase_core_rs is importable but does not expose binding
> 'artifact_relations_builtins'`) and `../sase-core` is not present here, so the entire
> `tests/ace/tui` lane fails at conftest import — independent of my probe. The findings
> below are therefore **static analysis plus the codebase's own admissions in comments**,
> not an executed repro. §6 gives the recipe to confirm on athena in minutes. I removed
> the probe file; the tree is clean.

---

## 1. How "the selected node" is actually represented

The selection is **a bare integer index into a flat list**, plus an optional banner key:

```python
# src/sase/ace/tui/actions/agents/_selection.py:23-33
class AgentSelectionMixin:
    _agents: list[Agent]
    current_idx: int
    current_attempt_number: int | None
    _current_group_key: tuple[str, ...] | None
```

```python
# src/sase/ace/tui/actions/agents/_selection.py:249-259
def _get_selected_agent(self) -> Agent | None:
    ...
    if self._agents and 0 <= self.current_idx < len(self._agents):
        agent = self._agents[self.current_idx]
```

Two properties of this model matter for the bug:

- **`self._agents` is the flat, global, post-fold, post-filter roster across *all* tribe
  panels.** `current_idx` is a global index, not a per-panel or per-screen row. An index
  that shifts by three can land you in a different tribe panel.
- **`self._agents` is replaced wholesale on every refresh** (`_display.py:149-150`
  documents this: *"``self._agents`` is replaced wholesale by the loading / refilter
  paths"*). So every refresh must re-derive the selection from scratch.

The stable key used for that re-derivation is `Agent.identity`:

```python
# src/sase/ace/tui/models/agent.py:410-431
@property
def identity(self) -> tuple["AgentType", str, str | None]:
    if self.is_clan_container and self.agent_clan:
        return (AgentType.RUNNING, f"clan:{self.agent_clan}", self.agent_clan_generation)
    if self.is_imported_family_container and self.agent_family:
        return (AgentType.RUNNING, f"imported-family:{self.agent_family}", self.raw_suffix)
    if self.is_remote_family_container and self.agent_family:
        origin = self.fleet_origin_alias or ""
        return (AgentType.RUNNING, f"remote-family:{origin}:{self.agent_family}", self.raw_suffix)
    return (self.agent_type, self.cl_name, self.raw_suffix)
```

For a plain agent row this is stable (`AgentType` is `RUNNING`/`WORKFLOW`/`PROC_SHELL` —
a *kind*, not a lifecycle status, per `src/sase/core/agent_types.py:8-16`). **But the
first three branches are not stable**: a row's identity changes the moment it starts or
stops being a clan / imported-family / remote-family container. That is a real identity
flip for a row the user may have selected. See §4.

---

## 2. Mechanism 1 (primary): the panel-focus snap

### 2.1 The code

`_sync_panel_group()` runs on **every list-changed Agents-display refresh** — both the
full-rebuild path and the incremental fast path:

- `src/sase/ace/tui/actions/agents/_display.py:466` (incremental)
- `src/sase/ace/tui/actions/agents/_display.py:577` (full)

Its tail unconditionally enforces "cursor inside focused panel":

```python
# src/sase/ace/tui/actions/agents/_display_panel_collection.py:203-234
keys_per_agent = self._panel_keys_per_agent()
focused_key = self._panel_group.focused_key
panel_index = self._agent_panel_index()
if 0 <= self.current_idx < len(self._agents):
    if (
        keys_per_agent[self.current_idx] != focused_key
        or panel_index.local_idx_for(focused_key, self.current_idx) < 0
    ):
        self._snap_current_idx_to_focused_panel(keys_per_agent, focused_key)
else:
    self._snap_current_idx_to_focused_panel(keys_per_agent, focused_key)

def _snap_current_idx_to_focused_panel(self, keys_per_agent, focused_key) -> None:
    """Set ``current_idx`` to the first agent in the focused panel."""
    global_indices, _panel_agents = rendered_panel_slice(self, focused_key)
    if global_indices:
        self.current_idx = global_indices[0]
        return
    ...
    self.current_idx = 0
```

Note what this does **not** do: it never consults the identity the user had selected. It
picks row 0 of a panel. That is a *maximal* jump — the cursor lands at the top of a
panel, which is exactly the "jumped to some other node" symptom rather than an off-by-one
drift.

There are **three distinct ways** this fires in the background.

### 2.2 (M1a) The focused panel drops out of the panel group while its widget stays mounted

`_sync_panel_group()` builds the panel group from **occupancy only**:

```python
# src/sase/ace/tui/actions/agents/_display_panel_collection.py:169-189
prev_focused = self._panel_group.focused_key
...
panel_keys = panel_keys_for(self._agents)          # <-- occupancy of the VISIBLE roster
live_keys = set(panel_keys)
agents_with_children = getattr(self, "_agents_with_children", self._agents)
for agent in agents_with_children:
    if agent_is_rendered_in_agents_panel(agent):
        live_keys.add(normalize_panel_key(agent.tribe))
live_keys.update(self._session_mounted_panel_key_set())
retire_panel_fold_intents(self, live_keys)          # live_keys is used ONLY here
retire_panel_fold_sweep_records(self, live_keys)
collapsed_keys = effective_panel_collapses(self, panel_keys)
self._panel_group = AgentPanelGroup.from_panel_keys(
    panel_keys, prev_focused, collapsed_panel_keys=collapsed_keys,
)
```

`panel_keys_for()` derives keys strictly from currently-rendered agents
(`models/agent_panels.py:113-125`). And `from_panel_keys` **silently resets focus to the
first panel** when the previous focus is gone:

```python
# src/sase/ace/tui/models/agent_panels.py:243-259
"""If ``focused_key`` is no longer present in the new panel set
(e.g. its tribe's last agent was dismissed), focus falls back to
the first available panel."""
...
try:
    idx = keys.index(focused_key)
except ValueError:
    idx = 0
return cls(panel_keys=keys, focused_idx=idx)
```

The codebase **already documents this exact divergence** — in the paint-log module added
five commits ago:

```python
# src/sase/ace/tui/actions/agents/_paint_log.py:110-114
# Observe the same mounted set the painter paints: occupancy plus
# session-sticky keys. The group alone drops an emptied sticky panel whose
# widget stays mounted as a collapsed strip, which would misreport that
# strip's collapse intent as not collapsed.
```

So: the *widget* list is occupancy ∪ session-sticky keys
(`_sorted_widget_panel_keys`), but the *panel group* is occupancy only. A tribe panel
whose rows transiently leave the visible roster keeps its widget on screen as a collapsed
strip **while vanishing from `_panel_group.panel_keys`.** If that was the focused panel:

> focus → panel index 0 → `_snap_current_idx_to_focused_panel` → cursor to the first row
> of a *different* tribe.

And the focus **does not come back** when the rows return, because `focused_key` now
names a panel that legitimately exists.

**What empties a panel's visible slice on a busy host:** a fold collapse, a live/committed
query flap, `hide_non_run_agents`, a dismissal, or a bounded-prefix load whose cache key
does not match (see §5 on what *is* already guarded here).

### 2.3 (M1b) The selected agent's panel key changes under it

`keys_per_agent[self.current_idx] != focused_key` also fires when the *agent* moves
panels rather than the panel disappearing. Panel keys are not a plain `agent.tribe` read
— they go through **workflow-parent inheritance and presentation anchors**:

```python
# src/sase/ace/tui/models/agent_panels.py:125-131
rendered_agents = [a for a in agents if agent_is_rendered_in_agents_panel(a)]
parent_lookup = _build_parent_lookup(agents)
anchors = presentation_anchor_lookup(agents, parent_lookup)
for a in rendered_agents:
    key = _panel_key_for_agent(a, parent_lookup, anchors)
```

So a row's panel key depends on **which other rows are currently loaded**. On a roster
where the loader returns a bounded window (§5), a child row can be present before its
parent/anchor row is. When the parent later arrives, the child inherits the parent's tribe
and its panel key changes — with no change to the child itself. If the user had that child
selected, the cursor snaps away.

### 2.4 (M1c) The selected agent leaves the focused panel's *rendered slice*

The second half of the condition — `panel_index.local_idx_for(focused_key,
self.current_idx) < 0` — fires even when the panel key is unchanged, whenever the
selected row is no longer a *rendered* row in that panel: it became a child under a newly
formed clan/family container, or a fold closed over it. On athena, agents spawn
clans/families continuously, so a running agent you selected can become a folded child of
a container that did not exist when you selected it.

---

## 3. Mechanism 2: the identity-restore fallback is a global-index clamp

Before the display refresh runs, the load pipeline re-derives `current_idx`:

```python
# src/sase/ace/tui/actions/agents/_loading_finalize.py:458-505
saved_idx = app.current_idx if on_agents_tab else app._agents_last_idx
restored_idx = restore_selection_by_identity(
    app._agents,
    prior_identity=selected_identity,
    prior_visual_row=saved_idx,
    identity_fn=lambda agent: agent.identity,
)
identity_restored = (...)
saved_idx = restored_idx
if (on_agents_tab and prior_pos is not None and selected_identity is not None
        and not identity_restored):
    app.current_idx = saved_idx
    app._restore_focus_after_removal(prior_pos)
else:
    new_idx = min(saved_idx, len(app._agents) - 1) if app._agents else 0
    if on_agents_tab:
        app.current_idx = new_idx
```

Two problems.

**(a) On the refresh path, the "nearest neighbor" repair is dead code.**
`_restore_focus_after_removal()` (`_navigation_order.py:263-303`) is the *good* repair —
it re-anchors to the visible navigation stop that slid into the removed row's position,
and correctly handles banner rows. But the refresh path never reaches it:
`_loading_apply.py:713` calls `_finalize_agent_list(...)` **without `prior_pos`**, which
defaults to `None` (`_loading_finalize.py:345`). So the `else` branch always wins.

**(b) The surviving fallback clamps to a *global list index*, not a visual row.**

```python
# src/sase/ace/tui/util/selection.py:74-...
"2. Else if ``prior_visual_row`` is in ``[0, len(new_items)-1]``, clamp
   to it (nearest-neighbor: the same visible row position now points at
   whichever entry slid into the previous selection's slot)."
```

The docstring's "nearest-neighbor" intuition holds for a **single flat list** — which is
true of every other caller of this helper (`logs_pane`, `machines_pane`,
`project_list_controller`, `config_pane_widget`, `feature_flags_pane`,
`memory_panel_state`). It is **not** true of the Agents tab, where the parameter is fed
`app.current_idx`, a global index across every tribe panel, with folds and filters applied.
When the identity is missing, the cursor lands at the same *global offset* into a
differently-shaped roster — which can be a different panel entirely.

**When is the identity missing?** Besides removal/dismissal, the identity-flip branches
in `Agent.identity` (§1): a selected row that becomes — or stops being — a clan container,
an imported-family container, or a remote-family container changes key entirely. The
remote-family branch even folds in `fleet_origin_alias`, which is fleet-resolution state.

---

## 4. Mechanism 3: a stale `selected_identity` survives three awaits

Rule 4 of `sase/memory/tui_perf.md` is explicit:

> **Re-capture UI state after every `await`.** Selection/tab captured before an await is
> stale when results land (pump-free tasks interleave); re-read the current tab and
> selected identity before applying, or j/k silently jumps.

The async loader applies this rule **once, and then stops applying it**:

```python
# src/sase/ace/tui/actions/agents/_loading_disk_full.py:272-278
# Capture current state AFTER the await; the user may have navigated
# (j/k) or switched tabs while disk I/O was in flight.
on_agents_tab = self.current_tab == "agents"
selected_identity = None
if on_agents_tab and self._agents and 0 <= self.current_idx < len(self._agents):
    selected_identity = self._agents[self.current_idx].identity
```

…and then, with that value held, three more awaits run before the apply:

```python
# _loading_disk_full.py:310, 320, 327
boundary      = await asyncio.to_thread(boundary_worker, ...)          # roster prep
content_index = await self._prepare_agent_content_search_index_async(...)
boundary      = await asyncio.to_thread(attach_finalize_plan_to_boundary, ...)
```

`prior_visual_row` is captured in the same stale window
(`_loading_apply.py:219-221`: `prior_visual_row = self.current_idx`).

There **is** a drift detector — but it does not fix the drift:

```python
# src/sase/ace/tui/actions/agents/_loading_apply.py:295-345
"""The plan is discarded — and the finalize pipeline recomputes the
query filter, status overrides, selection math, and group keys on
the UI thread — when ... any captured input (selection, fold snapshot, query,
status-override set, grouping mode, or hide flag) has drifted (``stale_token``)"""
current_snapshot = self._make_prepared_apply_snapshot(
    on_agents_tab=on_agents_tab,
    selected_identity=selected_identity,     # <-- the STALE value is passed back in
    load_state=...,
)
```

`make_finalize_stale_token` (`_loading_compute_finalize.py:290-320`) hashes both
`selected_identity` and `prior_visual_row`. Only `prior_visual_row` is re-read live
(inside `_make_prepared_apply_snapshot`); `selected_identity` is **threaded through as an
argument**, so it can never differ from itself. A j/k move therefore *does* invalidate the
token and discard the plan — and the UI-thread recompute at `_loading_finalize.py:467`
then calls `restore_selection_by_identity(prior_identity=selected_identity, ...)` with
**the same stale identity**, which wins over the fresh visual row (identity beats row in
the helper's priority order). Net effect: the cursor is dragged back to the node that was
selected before the refresh started.

**The nav gate does not cover this window.** `NavigationGate` is a 250 ms guard
(`util/nav_gate.py:5-12`) and it is consulted **once**, at the top of the refresh
coroutine, *before* the disk load:

```python
# src/sase/ace/tui/actions/agents/_loading_refresh.py:199-202
if self._nav_gate.is_navigating():
    delay = self._nav_gate.time_until_idle() + 0.05
    self.set_timer(delay, self._spawn_agents_refresh_task)
    return
```

Everything after that line — disk load, worker prep, content index, finalize plan, apply —
is unguarded. On a large roster that is seconds, not milliseconds.

**Notably, the fleet path already solved exactly this**, by re-checking the gate at the
*apply* seam and deferring:

```python
# src/sase/ace/tui/actions/agents/_fleet_refresh.py:203-223
def _defer_fleet_projection_apply_if_navigating(self, projection, *, ...) -> bool:
    nav_gate = getattr(self, "_nav_gate", None)
    if nav_gate is None or not nav_gate.is_navigating():
        return False
    delay = nav_gate.time_until_idle() + 0.05
    self.set_timer(delay, lambda: self._apply_deferred_fleet_projection(...))
    return True
```

That is the pattern the main refresh apply is missing.

---

## 5. Why athena and not the MacBook

Per `sase/memory/tailnet.md`, athena is the always-on Linux home server; `mac` is "offline
unless it is powered on with its lid open." Athena is where the agent fleet actually
lives. Every mechanism above is a function of roster size, roster churn, and refresh
duration — all of which are order-of-magnitude larger there.

Four concrete amplifiers:

1. **Refresh frequency.** Auto-refresh defaults to every 10 s (`app.py:297`,
   `_startup_mount.py:175-184`), *plus* artifact-delta refreshes from the in-flight
   transition poller (`_loading_refresh_polling.py`), *plus* fleet refreshes
   (`_fleet_refresh.py`). Every one of these ends in a list-changed display refresh, hence
   `_sync_panel_group()`, hence a snap opportunity. A host with no agent activity fires the
   cheap idle path and nothing moves.

2. **The loader window is a growing prefix anchored on the cursor.**

   ```python
   # src/sase/ace/tui/actions/agents/_loading_disk_viewport.py:30-57
   index_source = getattr(app, "current_idx", 0) if current_tab == "agents" else ...
   start_row = max(0, int(index_source))
   ...
   return AgentsViewport(start_row=start_row, visible_rows=visible_rows,
                         prefetch_rows=visible_rows * 2)
   ```

   On a small roster every load returns everything, the panel-key set is byte-identical
   every time, and nothing can snap. On a large roster the returned set is a *window*, so
   which tribes and which parent/anchor rows are present varies between refreshes — which
   is precisely the input to M1a and M1b.

3. **Clan/family formation.** Athena runs clans, tribes and families continuously. That
   drives M1c (selected row becomes a folded child) and the `Agent.identity` container
   flips behind M2.

4. **Apply latency.** The three-await window in §4 scales with roster size (roster prep,
   content-search index, finalize plan are all O(agents)). A window that is ~10 ms on the
   Mac can be hundreds of ms to seconds on a loaded athena, which is the difference between
   "never hits the race" and "hits it constantly." `athena_memory_pressure_and_agent_capacity`
   in this same research directory indicates athena is already memory-pressured, which
   lengthens these stages further.

**What is already guarded** (do not re-fix these):

- A **bounded-prefix load is patched over the cache**, not substituted for it, when the
  committed query matches — `_loading_compute_merge.py:312-333`: *"A bounded viewport
  prefix is never proof that a row vanished, whatever `has_more` says."* This closes the
  most obvious version of M1a. It does **not** close the fold/filter version, and it does
  not apply when `cache_query_matches` is false (a committed-query change, or the
  current-project query seed).
- A **same-query bounded zero** is ignored rather than applied
  (`_loading_apply.py:365-395`) — but note the early return `if load_state is None or
  load_state.returned_count != 0`, so a *partial* result is not covered by that guard.
- `AgentList.watch_highlighted` is correctly overridden to suppress programmatic echoes
  (`widgets/agent_list.py:471-500`), so rule 12 of `tui_perf.md` is satisfied. **The jump
  is not a Textual `OptionHighlighted` echo** — it is app state being deliberately
  rewritten.

---

## 6. How to confirm which mechanism it is, on athena, in ~10 minutes

Every piece of instrumentation needed already ships. `agents.paint_frame` records
`selected_identity` for the app **and** `highlighted_identity` per panel, per frame,
alongside the `source` of the refresh that produced it (`docs/perf_runbook.md:505-532`).

```bash
# On athena, run the TUI with tracing on, park the cursor on a node, do NOT touch
# the keyboard, and wait for a jump.
SASE_TUI_TRACE=1 sase tui

# Then: every frame where the selection moved, and what refresh caused it.
jq -c 'select(.event == "agents.paint_frame")
       | {seq, kind, source, display_cost, fallback_reason, selected_identity,
          panels: [.panels[] | [.widget_id, .option_count, .highlighted, .highlighted_identity]]}' \
   ~/.sase/perf/tui_trace.jsonl
```

Read it like this:

| Observation between two consecutive frames | Mechanism |
| --- | --- |
| `selected_identity` changes and the new value is the **first row of some panel**; the previously focused panel's `widget_id` is still present but its `option_count` dropped to 0 | **M1a** — emptied focused panel |
| `selected_identity` changes to a first row and the old node's `widget_id` changed panel | **M1b** — panel-key change |
| `selected_identity` changes to a first row while the old node simply stopped appearing in any panel's rows (folded under a container) | **M1c** — left the rendered slice |
| `selected_identity` changes to a node at an unrelated offset (not row 0 of anything) | **M2** — global-index clamp |
| `selected_identity` reverts to a node you had selected *a moment earlier*, right after a keypress | **M3** — stale identity |

Cross-check with the apply-side counters:

```bash
# finalize_plan discards tell you the drift detector is firing (M3 territory).
jq -r 'select(.event == "agents.apply_loaded_agents_prepared")
       | [.finalize_plan, .finalize_plan_discard_reason, .source] | @tsv' \
   ~/.sase/perf/tui_trace.jsonl | sort | uniq -c | sort -rn

# Panel presence over time: a tribe panel that blinks out of the group is M1a.
jq -r 'select(.event == "agents.refresh_panel_widgets") | .panel_widget_ids | @csv' \
   ~/.sase/perf/tui_trace.jsonl | uniq -c
```

`widget.agent_list.watch_highlighted` vs `...watch_highlighted.suppressed`
(`widgets/agent_list.py:481-500`) will further confirm the move came from app state
rather than a widget echo.

---

## 7. Recommended solution

### 7.1 The one fix that matters: invert the panel-focus ↔ cursor dependency

The tab is internally inconsistent about which of `current_idx` and
`_panel_group.focused_idx` is authoritative:

- In **explicit user navigation**, focus follows the cursor — `_panel_navigation.py:122`,
  `_neighbors.py:414`, `_unread_navigation.py:207,308`, `_folding_agent_groups.py:349`,
  `_revive_state.py:57` all assign `focused_idx` *from* where the cursor went.
- In **every background rebuild**, the cursor follows focus —
  `_display_panel_collection.py:207-234`.

The user's act is *selecting a node*. Panel focus is derived presentation state. The
background path has the dependency backwards, and that inversion is the jump.

**Change `_sync_panel_group()` so that, when the selected agent is still in the roster,
panel focus moves to the panel that contains it — instead of moving the cursor to the
focused panel.** Concretely, in `_display_panel_collection.py:203-214`:

```python
selected_key = keys_per_agent[self.current_idx] if 0 <= self.current_idx < len(self._agents) else None
if selected_key is not None and panel_index.local_idx_for(selected_key, self.current_idx) >= 0:
    # The selection is still a rendered row somewhere: focus follows it.
    if selected_key != focused_key and selected_key in self._panel_group.panel_keys:
        self._panel_group.focused_idx = self._panel_group.panel_keys.index(selected_key)
        return
# Only when the selection is genuinely unrenderable do we snap.
self._snap_current_idx_to_focused_panel(keys_per_agent, focused_key)
```

This single change kills **M1b and M1c outright** and makes M1a survivable (see 7.2).
It also matches the invariant already written down in `util/selection.py:8-11`:

> *"the cursor lands on the same logical entry the user had selected, or on the nearest
> valid neighbor if that entry is gone."*

### 7.2 Make the panel group agree with the painter about which panels exist

`_sync_panel_group()` should build the group from the same occupancy ∪ session-sticky key
set the widget layer already uses (`_sorted_widget_panel_keys` /
`_session_mounted_panel_key_set`), which it *already computes* as `live_keys` and then
throws away at `_display_panel_collection.py:176-183`. Passing `live_keys` (ordered) to
`AgentPanelGroup.from_panel_keys` instead of `panel_keys` means a transiently-emptied
tribe panel keeps its focus slot — the same stickiness the widget already has, and the
same invariant `_paint_log.py:110-114` documents. This closes **M1a**.

Guard against the reverse regression with the existing `agents.refresh_panel_widgets`
`panel_widget_ids` counter, which the perf runbook already advertises as the way to assert
"a tribe panel's continuous presence."

### 7.3 Make the async apply re-read the live selection

Two edits in the loader, both small:

1. In `_loading_disk_full.py`, **re-capture `selected_identity` and `on_agents_tab`
   immediately before `_apply_loaded_agents_prepared`** (after line 327), not only after
   the disk await at line 272. The existing comment at 272-273 states the intent; it just
   needs to be applied at the last seam too.
2. In `_loading_apply.py:_select_finalize_plan`, **stop passing the stale
   `selected_identity` into `_make_prepared_apply_snapshot`** — read it live, the way
   `prior_visual_row` already is. Today the token compares the stale value against itself,
   so `stale_token` can only ever be tripped by the row, and the recompute path re-applies
   the same stale identity anyway.

Optionally, mirror the fleet path's apply-seam deferral
(`_fleet_refresh.py:203-223`) in `_run_agents_async_refresh` so an apply that lands
mid-burst waits out the 250 ms nav window instead of fighting the user's keystrokes.
This closes **M3**.

### 7.4 Give the Agents tab a real neighbor fallback

`restore_selection_by_identity`'s row fallback is correct for flat lists and wrong for a
panelized, folded roster. Either:

- pass `prior_pos` through from `_loading_apply.py:713` so the already-written, already-
  correct `_restore_focus_after_removal()` (`_navigation_order.py:263-303`) actually runs
  on the refresh path — it resolves against `_panel_navigation_stops()`, i.e. real visible
  rows including banners; or
- give the Agents tab its own `identity_fn` fallback that clamps within the *selected
  agent's panel slice* rather than the global list.

The first is strictly less new code and reuses a tested helper. This closes **M2's blast
radius** (the cursor still moves when the node is genuinely gone, but to an actual
neighbor).

### 7.5 Cheap follow-up: stabilize `Agent.identity`

The container branches at `models/agent.py:410-431` make identity a function of *render
role* (`is_clan_container`, `is_remote_family_container`, `fleet_origin_alias`), which is
recomputed per load. A row that gains its first clan child changes identity without
changing agent. Consider keying container rows off the underlying run's stable
`(agent_type, cl_name, raw_suffix)` with the container-ness carried as a separate field,
or at minimum add an `Agent.selection_key` used only by the selection restore path. This
is the lowest-priority item — 7.1/7.2 make the failure survivable regardless — but it is
the reason M2 triggers at all on an otherwise healthy roster.

### 7.6 Regression coverage

`tests/ace/tui/_epic_arrival_frames.py` is already the right harness: it boots a real
`AceApp` under the host's own shape (`BY_STATUS`, split tribe panels, committed query,
collapsed sibling), parks a selection inside `@epic`, and drives rosters through the real
`_apply_loaded_agents_prepared`. It already has a `selection_violations()` checker
(`_epic_arrival_frames.py:495-506`) asserting `panel.highlighted_identity ==
frame.selected_identity`. Add three arrival windows to it:

- the focused panel's rows transiently leave the roster, then return (M1a);
- the selected agent's `tribe` changes (M1b);
- the selected agent becomes a child under a newly-arrived clan container (M1c);

and assert the *parked identity is still selected* after each — not merely that the
highlight is internally consistent with `selected_identity`, which is what the current
checker proves.

---

## 8. Priority

| # | Fix | Closes | Effort | Risk |
| - | --- | --- | --- | --- |
| 1 | §7.1 focus follows selection in `_sync_panel_group` | M1b, M1c | small | low |
| 2 | §7.2 panel group uses `live_keys` (sticky) | M1a | small | low |
| 3 | §7.3 re-read selection at the apply seam + live token | M3 | small | low |
| 4 | §7.4 thread `prior_pos` into the refresh finalize | M2 blast radius | small | medium (changes removal behavior) |
| 5 | §7.5 stable `selection_key` | M2 root | medium | medium |

Items 1 and 2 are both in `_display_panel_collection.py` and are, in my assessment, the
fix. Ship those first and re-run the §6 trace on athena before doing anything else.

---

## 9. Limitations and open questions

- **Not executed.** As stated at the top: the `tests/ace/tui` lane cannot run in this
  workspace (stale `sase_core_rs` wheel, no `../sase-core`), so this is static analysis
  corroborated by the codebase's own comments — not a demonstrated repro. The ranking in
  §8 should be re-checked against the §6 trace output from athena before implementation.
- **Boundary note.** Per `rust_core_backend_boundary` in CLAUDE.md, everything above is
  presentation-only Textual state (panel focus, cursor index, display refresh). I found no
  part of this that belongs in `sase-core`.
- **Not investigated.** Whether athena's TUI is running a stale imported snapshot of the
  code (`tui_perf.md` rule 15 — `stale_running_code.py`). Worth ruling out before
  attributing a jump to any landed-and-since-fixed path: if athena's TUI has been open a
  long time, it is executing whatever it imported at start.
- **Not investigated.** Whether athena has a different `refresh_interval`, grouping mode,
  or committed Agents query than the Mac. A committed query is directly upstream of
  `cache_query_matches` in §5's merge guard, so a differing query is itself a plausible
  amplifier worth checking with `sase config` on both hosts.
