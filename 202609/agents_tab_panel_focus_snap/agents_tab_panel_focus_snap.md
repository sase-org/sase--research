# Agents-tab selection jump: the panel-focus snap steals the cursor

**Lead researcher:** C (consolidating A + B + own research) · **Date:** 2026-09-20
**Repo revision:** `e1ba4851c` · **Evidence:** static analysis + **live athena trace (1.8M events)**

## Bottom line

The Agents tab has two selection-like states — the selected agent (`current_idx`) and
the focused tribe panel (`_panel_group.focused_idx`) — and on **every background
refresh** it resolves disagreements between them in the wrong direction: it moves the
**cursor to the panel**, not the panel to the cursor. The user's selection is their
stated intent; panel focus is derived presentation state. The background path has that
dependency backwards, and that inversion is the jump.

Both prior reports reached this conclusion independently by static analysis. **I
confirmed it empirically against athena's own 515 MB trace file**, which neither
researcher knew existed:

- **76 of 76** non-adjacent cursor moves were immediately preceded by
  `agents.refresh_work` — typically within **1–130 ms**.
- **Zero** were preceded by a widget highlight echo.
- **61 of those 76 were never restored** — permanent, user-visible jumps.

That is the reported symptom, measured, with the mechanism identified. It also settles
the one substantive disagreement between the reports (§3).

**Recommended solution: §7.** The single fix that matters is inverting the dependency in
`_sync_panel_group`. But note **§6 first** — athena is in a degraded state that is
independently worth fixing and is the reason the bug is machine-specific.

---

## 1. Confirmed root cause (A's H1 = B's M1)

`_sync_panel_group()` runs on every list-changed Agents display refresh — both the
incremental fast path (`_display.py:466`) and the full rebuild (`_display.py:577`). Its
tail enforces "the cursor must live inside the focused panel"
(`_display_panel_collection.py:203-214`), verified verbatim in the current tree:

```python
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
```

`_snap_current_idx_to_focused_panel` sets `current_idx` to the **first agent of the
focused panel**, falling back to **row 0** (`_display_panel_collection.py:216-234`). It
never consults the identity the user had selected. That is a *maximal* jump — the cursor
lands at the top of a panel — which is why the symptom reads as "jumped to some other
node" rather than an off-by-one drift.

Three distinct ways the condition fires in the background (B's taxonomy, which is
sharper than A's flat list and which I adopt):

| | Trigger | Why it fires on athena |
| --- | --- | --- |
| **M1a** | The focused panel drops out of `_panel_group` while its widget stays mounted | Panel group is built from **occupancy only**; the widget layer is occupancy ∪ session-sticky. See §2 — this gap *widened* today. |
| **M1b** | The selected agent's panel key changes under it | Panel keys depend on workflow-parent inheritance and presentation anchors (`agent_panels.py:125-131`), so a child's key changes when its parent arrives in a later load window. |
| **M1c** | The selected agent leaves the focused panel's *rendered slice* | It became a folded child under a newly-formed clan/family container. Athena forms clans continuously. |

`AgentPanelGroup.from_panel_keys` silently resets focus to panel 0 when the previous
focus is gone (`agent_panels.py:243-259`) — so M1a produces a jump to the top of a
*different tribe*, and focus does not come back when the rows return.

### The snap is not gratuitous — a naive inversion would regress

Neither report noticed that the snap has a **deliberate purpose with a regression test**:
`test_sync_panel_group_snaps_selection_off_hidden_starting_row`
(`tests/ace/tui/test_agent_panel_index_integration.py:245`) parks the cursor on a hidden
`STARTING` row at index 0 and asserts the snap moves it to the rendered row 1. Any fix
must keep moving the cursor when the selected row is genuinely **unrenderable**.

I checked B's proposed patch (§7.1 of its report) against this test: it guards on
`panel_index.local_idx_for(selected_key, self.current_idx) >= 0`, so a hidden starting
row still falls through to the snap and the test still passes. **The recommended fix in
§7 is compatible with the existing test** — that compatibility is the reason to prefer
the guarded inversion over simply deleting the snap.

---

## 2. A recent fix half-closed M1a — and widened the underlying split

`8ae9ac1ea` ("retire Agents-tab tribe panels when their last node is dismissed", landed
on athena's checkout at 13:42 EDT today) made the session-sticky panel store
**identity-backed**, retiring a key only on explicit user removal. Its commit message is
explicit: *"A tribe's agents merely being absent from the roster never retires a key, so
an incomplete or bounded load still cannot unmount already-mounted tribe widgets."*

That protects the **widget** layer. It does **not** protect the **panel group**. In the
current code, `_sync_panel_group` computes `live_keys` (occupancy ∪ sticky) and then uses
it *only* for fold-intent retirement, passing bare `panel_keys` to
`AgentPanelGroup.from_panel_keys` (`_display_panel_collection.py:174-189`). So after
`8ae9ac1ea` the widget set is stickier than before while the group set is unchanged —
**the divergence M1a depends on is now wider, not narrower**. The codebase already
documents this exact split in a module added five commits earlier:

```python
# _paint_log.py:110-114
# The group alone drops an emptied sticky panel whose widget stays mounted
# as a collapsed strip, which would misreport that strip's collapse intent...
```

This matters for the recommendation: B's §7.2 is not a revert of `8ae9ac1ea` but its
natural completion — `live_keys` already honors identity-backed retirement, so feeding it
to the panel group inherits the new, correct retirement semantics.

---

## 3. Resolving the A/B disagreement: the highlight-echo hypothesis is dead

A ranked as its tertiary cause (H3) an unguarded `SelectionChanged` local→global
mistranslation, recommending adoption of `ProgrammaticSelectionGuard`. B explicitly ruled
this out: *"The jump is not a Textual `OptionHighlighted` echo — it is app state being
deliberately rewritten."*

**The trace settles it in B's favor.** Classifying every `selection.current_idx.set`
event by its immediately preceding event:

```
--- NON-ADJACENT jumps (n=76): preceding event ---
  76  agents.refresh_work
   0  widget.agent_list.watch_highlighted
```

Not one jump followed a widget highlight. `AgentList.watch_highlighted` is correctly
overridden to short-circuit synchronously during programmatic updates
(`widgets/agent_list.py:476-500`), and the trace shows it working: 1,064
`watch_highlighted.suppressed` events against 93 live ones in a 200k-line window.

**A's H3 should not be actioned.** The `ProgrammaticSelectionGuard` refactor is a
defensible hygiene item but it is not this bug, and spending the fix budget there would
leave the actual cause in place. This is the main correction the consolidation makes to
report A.

---

## 4. The empirical evidence (new — neither report had this)

Athena has `~/.sase/perf/tui_trace.jsonl`: **515 MB, 1,822,015 events**. `current_idx` has
a setter-level trace hook (`app.py:221-239`) recording every `old → new` transition,
which makes the jump directly observable.

**Method.** Extract `selection.current_idx.set`, `agents.refresh_work`,
`agents.paint_frame` and `widget.agent_list.watch_highlighted`; sort by timestamp; treat
`|new - old| > 1` as a jump (adjacent moves are j/k) and attribute each to its preceding
non-selection event.

**Results.**

- 221 selection sets; **76 non-adjacent jumps**; 145 adjacent moves.
- **76/76 jumps preceded by `agents.refresh_work`**, 66 of them within 1 second, most
  within 1–130 ms.
- **61/76 jumps were never restored** — the cursor stayed where the refresh put it.
- The characteristic signature of the snap-then-restore pair is visible in the raw log:

  ```
  ts=...742.913  4->0   prev=agents.refresh_work  dt=0.133s   <- snap to row 0
  ts=...742.929  0->4   prev=agents.refresh_work  dt=0.000s   <- identity restore wins
  ts=...750.192  4->0   prev=agents.refresh_work  dt=0.103s
  ts=...750.207  0->4   prev=agents.refresh_work  dt=0.000s
  ```

  When the restore wins the user sees a flicker; when the identity is missing — or the
  snap happens to land on a valid identity — the move is permanent. 61 of 76 were
  permanent.

**Which refresh drives it** (stage / display_cost / source of the preceding
`refresh_work`):

```
10  display / display_full_rebuild / fleet_refresh     <- largest single bucket
 8  display_patch / row_patch      / unknown
 7  data_loaded  / —               / auto_refresh
 7  data_loaded  / —               / watcher
 5  display / display_full_rebuild / filter
 5  display / display_full_rebuild / watcher
 4  display / display_full_rebuild / auto_refresh
```

Jumps occur at **both** `_sync_panel_group` call sites, with **fleet-refresh full
rebuilds the top trigger** — corroborating A's emphasis on staged fleet arrivals
(`_fleet_refresh.py:88-191`, where machine panels pop in and out as
`fleet_origin_alias`/family data fills in) and B's M1a/M1b.

---

## 5. Secondary mechanisms (real, verified, but not the headline)

Both reports independently found these; I verified both claims in the current tree.

**5.1 — The async apply re-applies a stale identity** (A's H2 = B's M3). Confirmed:
`selected_identity` is captured at `_loading_disk_full.py:275-279` with an explicit
comment about re-capturing after the await — and then **three more awaits** run before the
apply (lines 310, 320, 327). The drift detector hashes `selected_identity`, but that value
is *threaded through as an argument* to `_make_prepared_apply_snapshot`, so it is compared
against itself and can only ever be tripped by the row. The UI-thread recompute then calls
`restore_selection_by_identity(prior_identity=selected_identity, ...)` with the same stale
identity, which **beats the fresh row** in the helper's priority order. Net effect: a j/k
pressed during a slow refresh is silently undone.

The 250 ms `NavigationGate` does not cover this: it is consulted once, at the top of the
refresh coroutine (`_loading_refresh.py:199-202`), before the disk load. The fleet path
already solved exactly this by re-checking the gate at the *apply* seam
(`_fleet_refresh.py:203-223`) — that is the pattern the main refresh is missing.

**5.2 — The identity-restore fallback is a global-index clamp** (B's M2). Confirmed:
`_loading_apply.py:713` calls `_finalize_agent_list` positionally **without `prior_pos`**,
which defaults to `None` (`_loading_finalize.py:345`). So the good neighbor repair,
`_restore_focus_after_removal()` (`_navigation_order.py:263-303`), is **dead code on the
refresh path**, and the surviving fallback clamps to the same *global* offset into a
differently-shaped roster. B's observation that every other caller of this helper
(`logs_pane`, `machines_pane`, `project_list_controller`, …) is a flat list, where the
"nearest neighbor" docstring is actually true, is correct and is the clearest statement of
why the Agents tab is the odd one out.

**5.3 — `Agent.identity` is unstable for container rows.** The first three branches of
`models/agent.py:410-431` key on *render role* (`is_clan_container`,
`is_remote_family_container`, and `fleet_origin_alias` — fleet-resolution state). A row
that gains its first clan child changes identity without changing agent, which is what
makes 5.2 trigger at all on an otherwise healthy roster. Lowest priority; 7.1/7.2 make the
failure survivable regardless.

---

## 6. Why athena and not the MacBook — and an urgent unrelated finding

Both reports attributed the asymmetry to "athena is the busy fleet hub." That is correct
but understates it. I inspected the machine directly:

```
load average: 70.83, 64.20, 68.58     (64 cores — saturated)
Mem: 62 GB total, 51 GB used, 11 GB available
```

**Athena is running 39 duplicate copies of every SASE daemon:**

```
39  sase service run
39  sase scheduler run
39  sase axe routine run waits / housekeeping / hooks / external_mirror / comments / checks
```

38 of each are byte-identical command lines (`~/.local/bin/sase …`), all spawned within
roughly the last half hour — a **runaway respawn loop**, not legitimate per-project
daemons. That is ~270 redundant processes competing to write the same state.

This matters to the bug in two ways, and matters on its own terms more than the bug does:

1. **It is the amplifier.** Every mechanism above is a function of roster churn and apply
   latency. 39 schedulers writing agent state produce continuous roster churn (the
   `watcher` and `auto_refresh` refresh sources in §4), and a saturated 64-core box
   stretches the three-await window in §5.1 from milliseconds to seconds.
2. **It is an independent production problem.** Load 70 with 11 GB RAM left is a machine
   heading for trouble regardless of any TUI cursor behavior.

**Stale running code — checked and largely cleared.** `tui_perf.md` rule 15 warrants
ruling this out, and both reports flagged it as unverified. Athena installs `sase` as an
**editable** uv tool (`_editable_impl_sase.pth` → `/home/bryan/projects/github/sase-org/
sase/src/sase`), so the TUI imports the live checkout at process start. The TUI started
`Sun Sep 20 17:09:23` EDT, 21 seconds after the `ef9900990` fast-forward; the checkout has
since fast-forwarded three more times (17:54, 19:38, 20:35) to `98bf83a38`. So the running
TUI **does** include the `8ae9ac1ea` panel-retirement fix (merged 13:42 EDT) but is ~3.5
hours and 3 merges stale. A restart is cheap and worth doing, but — unlike what report A
suggested as step 1 — **it will not fix this**: the snap is present at `e1ba4851c`, and the
trace shows the jumps under code that already has today's fix.

---

## 7. Recommended solution

### 7.1 The fix that matters — invert the dependency in `_sync_panel_group`

The tab is internally inconsistent about which state is authoritative. In **explicit user
navigation**, focus follows the cursor (`_panel_navigation.py:122`, `_neighbors.py:414`,
`_unread_navigation.py:207,308`, `_folding_agent_groups.py:349`, `_revive_state.py:57` all
assign `focused_idx` *from* where the cursor went). In **every background rebuild**, the
cursor follows focus. Make the background path agree with the navigation path.

In `_display_panel_collection.py:203-214`:

```python
selected_key = (
    keys_per_agent[self.current_idx]
    if 0 <= self.current_idx < len(self._agents)
    else None
)
if selected_key is not None and panel_index.local_idx_for(selected_key, self.current_idx) >= 0:
    # The selection is still a rendered row somewhere: focus follows it.
    if selected_key != focused_key and selected_key in self._panel_group.panel_keys:
        self._panel_group.focused_idx = self._panel_group.panel_keys.index(selected_key)
    return
# Only when the selection is genuinely unrenderable do we snap.
self._snap_current_idx_to_focused_panel(keys_per_agent, focused_key)
```

Closes **M1b and M1c** outright and makes M1a survivable. Preserves the hidden-starting-row
test (§1). Reserves snap-to-panel for explicit user panel actions, where the focus move is
the user's own intent. It also restores the invariant already written down in
`util/selection.py:8-11`: *"the cursor lands on the same logical entry the user had
selected, or on the nearest valid neighbor if that entry is gone."*

### 7.2 Make the panel group agree with the painter about which panels exist

Pass the ordered `live_keys` — which `_sync_panel_group` **already computes and discards**
(`_display_panel_collection.py:176-183`) — to `AgentPanelGroup.from_panel_keys` instead of
bare `panel_keys`. A transiently-emptied tribe panel then keeps its focus slot, matching
the stickiness the widget layer already has. Post-`8ae9ac1ea` this inherits identity-backed
retirement for free (§2), so an explicitly dismissed tribe still retires correctly. Closes
**M1a**. Guard the reverse regression with the existing `agents.refresh_panel_widgets`
`panel_widget_ids` counter.

### 7.3 Re-read the live selection at the apply seam

Two small edits, closing **M3 / H2**:

1. `_loading_disk_full.py`: re-capture `selected_identity` and `on_agents_tab` immediately
   before `_apply_loaded_agents_prepared` (after line 327), not only after the disk await
   at 275. The comment at 275-276 already states the intent; apply it at the last seam too.
2. `_loading_apply.py:_select_finalize_plan`: stop passing the stale `selected_identity`
   into `_make_prepared_apply_snapshot` — read it live, the way `prior_visual_row` already
   is. Today the token compares the stale value against itself.

Optionally mirror the fleet path's apply-seam deferral (`_fleet_refresh.py:203-223`) in
`_run_agents_async_refresh`.

### 7.4 Give the Agents tab a real neighbor fallback

Thread `prior_pos` through from `_loading_apply.py:713` so the already-written, already-
tested `_restore_focus_after_removal()` actually runs on the refresh path — it resolves
against `_panel_navigation_stops()`, i.e. real visible rows including banners. Strictly
less new code than a bespoke per-panel clamp. Closes **M2's blast radius**.

### 7.5 Operational — do this first, independently of the code fix

Athena's 39 duplicate daemon sets (§6) should be investigated and reaped. This is the
larger operational problem, it is the reason the bug is machine-specific, and reducing it
will reduce jump frequency before a single line of TUI code changes. Restart the athena
TUI at the same time to pick up the last 3 merges — but do not expect the restart alone to
fix the jump.

### 7.6 Regression coverage

`tests/ace/tui/_epic_arrival_frames.py` is the right harness: it boots a real `AceApp` in
the host's own shape (`BY_STATUS`, split tribe panels, committed query, collapsed sibling),
parks a selection, and drives rosters through the real `_apply_loaded_agents_prepared`. Its
existing `selection_violations()` checker only proves the highlight is *internally
consistent* with `selected_identity`. Add three arrival windows asserting the **parked
identity is still selected**:

- the focused panel's rows transiently leave the roster, then return (M1a);
- the selected agent's `tribe` changes (M1b);
- the selected agent becomes a child under a newly-arrived clan container (M1c).

Also keep `test_sync_panel_group_snaps_selection_off_hidden_starting_row` green — it is the
guard against over-correcting §7.1.

### Priority

| # | Fix | Closes | Effort | Risk |
| - | --- | --- | --- | --- |
| 0 | §7.5 reap athena's duplicate daemons + restart TUI | amplifier | small | none |
| 1 | §7.1 focus follows selection in `_sync_panel_group` | M1b, M1c | small | low |
| 2 | §7.2 panel group uses sticky `live_keys` | M1a | small | low |
| 3 | §7.3 re-read selection at apply seam + live token | M3 / H2 | small | low |
| 4 | §7.4 thread `prior_pos` into refresh finalize | M2 radius | small | medium |
| 5 | §7.5(b) stable `Agent.selection_key` | M2 root | medium | medium |

Items 1 and 2 are both in `_display_panel_collection.py` and are, on the trace evidence,
**the** fix. **Do not action A's H3** (`ProgrammaticSelectionGuard` for `SelectionChanged`)
— §3 refutes it with data.

---

## 8. Limitations

- **The fix is not yet implemented or tested.** The trace analysis is observational: it
  proves the jumps are refresh-driven and not echo-driven, and that they land on
  panel-first rows, but it does not single-step `_sync_panel_group` itself. The final
  attribution among M1a/M1b/M1c rests on static analysis.
- **The trace predates the running TUI** (last written 16:57, TUI started 17:09), so it
  was produced by a slightly older revision — one that lacks `8ae9ac1ea`. The snap code
  itself is unchanged between the two, so the M1b/M1c evidence carries; the M1a *rate*
  may differ under the current binary. Re-running with `SASE_TUI_TRACE=1` after a restart
  would tighten this.
- **Neither prior report could execute the test suite** (B documented a stale
  `sase_core_rs` wheel); I did not attempt to either, so no proposed patch has been run
  against `tests/ace/tui/`.
- **Boundary note.** Per `rust_core_backend_boundary`, all of this is presentation-only
  Textual state (panel focus, cursor index, display refresh). Nothing here belongs in
  `sase-core`.
- **Not investigated:** the origin of the 39-way daemon duplication. It is reported here
  as a finding, not diagnosed.
