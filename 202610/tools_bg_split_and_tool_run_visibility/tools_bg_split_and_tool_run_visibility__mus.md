# Tool-run procs: `tools:` indicator, `procs:` → `bg:` rename, and per-node running indicators

Research report (mus). Goal: decide the best way to stop counting agent-launched
` sase tool` procs as blue gears in the top-bar `procs:` indicator and instead show
them under a new `tools:` section with the ⚒ icon, rename `procs:` to `bg:`, and make
running tool state clearer on agent tribe panels/nodes including clan nodes.

## Summary of recommendation

The plan is a good idea and should be built, with three adjustments (all flagged
**ADJUSTMENT** below):

1. Put the new `tools:` group in the **same top-bar cluster as `bg:`** (row 1),
   not in the Agents status row (row 2). Same data source, same update path, global
   scope, no per-tab duplication.
2. Rename only the **indicator label** `procs:` → `bg:`; keep the Procs tab/pane
   name, widget id, and JSON shapes unchanged for now.
3. Treat `origin == "tool-run"` as the classifier (tags as fallback), because the
   submit path *does* set `session_id` when resolvable — "not session-linked" is
   about lifetime, not attribution, so the lane split must key on origin, not on
   session attribution.

## Current state (verified in tree)

### What a `sase tool` hand-off proc is

- `submit_handoff_run` (`src/sase/tool/handoff_launch.py`) reserves a ToolRun
  (`owner_kind="proc"`, `owner_id=<new proc_id>`) and submits an adopting proc with:
  - `origin="tool-run"`,
  - label `tool:<name>` (or `tool:ad-hoc`) via `describe_handoff_command`,
  - tags `["tool-run", f"tool-run:{run_id}"]` plus `tool-run-detached` when detached
    (`src/sase/tool/handoff.py: owner_tags`),
  - `request_fingerprint = f"tool-run:{run_id}"`, followup `{"kind": "tool-run"}`.
- **Nuance for the "not linked with the TUI session" claim:** the submit path calls
  `resolve_session_ref(None)` and `infer_proc_attribution`, so `session_id` is set
  whenever a session is resolvable. The proc is unlinked in the *lifetime* sense
  (does not block TUI restarts, survives them), not necessarily in the attribution
  sense. Any classifier keyed on `session_id is None` will misclassify these rows.
  Key on `origin` first, `tool-run:<id>` tag second.

### The icon language already exists

- `src/sase/tool/view_vocabulary.py`: `TOOL_RUN_GLYPH = "⚒"`, running accent
  `TOOL_RUN_ACCENT = "#87D7FF"`, silent marker `SILENT_GLYPH = "⚠"` (rendered
  `⚒⚠`), plus a `⚒<count>` count form. Settled buckets reuse the finalizer
  palette. This is the single vocabulary the Agents-tab chips, Runs card, and
  Tools pane already share — the new indicator must reuse it, not invent a hue.
- Blue gear `⚙` (`MONITOR_GLYPH`, `PROC_GEAR_HUE = "#48CAE4"`) = session proc lane;
  orange `⚙` = monitors; green `⚙` = updates. Three lanes already share one glyph
  distinguished only by hue. A fourth `⚙` hue for tools would be unreadable, which
  is the strongest visual argument for the ⚒ split: it is the only lane with a
  distinct glyph.

### Where tool procs leak into `procs:` today

- `proc_gear_lane()` (`src/sase/ace/tui/_proc_observer_models.py`) returns
  `"monitor"` / `None` (service) / `"update"` / `"proc"` — a hand-off row is none
  of the first three, so it lands in `"proc"` and inflates the blue-gear count via
  `proc_gear_lanes()` → `ProcIndicator.set_counts(procs, monitors)`
  (`src/sase/ace/tui/widgets/proc_indicator.py`, `GROUP_LABEL = "procs"`).
- The Procs pane already partially knows: `_append_tool_run_marker` renders
  `⚒ <label>` from the `tool-run:<id>` tag (`src/sase/ace/tui/modals/procs_pane_render.py`).
  So the pane marks them but the top bar counts them as generic procs — the exact
  inconsistency the request targets.
- Agents status row (`AgentInfoPanel`) has a separate `⚙N` named-proc badge for
  `NAMED_PROC`-lifecycle rows; hand-off procs are not named-proc-lifecycle rows,
  so that badge is almost certainly unaffected — verify with one test, do not
  change it.

### Per-node running state already exists (except clans)

- Agent list rows: live-only ⚒ chip via `select_live_runs` + `row_chip_for_runs`
  (`_agent_list_render_agent_status.py`, `tool_runs/row_chip.py`, minute-quantized).
  Attribution is owner-first → exact agent-name → session-container aggregation.
- `select_live_runs` explicitly returns `()` for `is_remote` and `is_clan`
  (`tool_runs/attribution.py`), and `selector_for_agent` returns `None` for both
  (`tool_runs/summaries.py`), so clan containers get **no** row chip, **no** header
  chip, and **no** Tool-runs field today. Session containers already aggregate over
  member names — clans need the mirror image of that logic.
- Compact header chip + `Tool runs` field + `⚒ Runs` deck card + `tools ⚒N M`
  deck-chrome subtitle (`panel_navigation.py`) cover the selected node. The gap is
  precisely: clan container rows, and clan selection headers.

## Critique: is this a good idea?

Yes. Three reasons:

1. **It fixes a category error, not just a label.** Tool-run owner procs are
   execution substrate for ledger entries that already have their own live
   affordances (row chips, header chip, Runs card). Counting them as generic
   background procs double-reports one underlying activity and implies the wrong
   management actions (a user "cleaning up procs" should not be nudged to kill a
   proc that is really a running tool with its own stop path, `action_stop_live_tool_run`).
2. **Glyph distinctness scales; hue distinctness does not.** See above: three `⚙`
   hues is already the limit. ⚒ is pre-established, user-visible in deck chrome,
   and self-explanatory next to `bg:`.
3. **`bg:` is the honest name.** After the split, the blue-gear lane contains only
   TUI-associated background work, so `bg:` describes it. Keeping the word "procs"
   for that lane would now *under*-claim (tool procs are also procs).

Risks and costs, honestly stated:

- **Churn surface of the rename.** `GROUP_LABEL = "procs"` feeds full/compact cell
  math, separator sync, tooltip text ("No running procs / Click to open the Procs
  tab"), and an unknown number of golden tests/screenshots plus docs/help text that
  say "procs:". (I did not exhaustively enumerate test references; the implementer
  must grep `procs:` across `tests/` and `docs/`.) This is why ADJUSTMENT 2 keeps
  the tab name and widget id (`#proc-indicator`, queried in
  `_proc_action_observer.py`) stable.
- **Count-conservation confusion.** `bg: + tools:` will no longer equal the old
  `procs:` number users memorized, because monitors were never in `procs:` (own
  orange chip) and services never counted. The tooltip and the Procs-tab header
  must make the four-lane accounting (`bg / monitors / tools / updates`) explicit
  or users will file "my proc disappeared" bugs.
- **Clan aggregation cost.** A clan fans out to N member names; the node-summary
  LRU is keyed per node and capped at 64 with 20 runs per node. A naive clan
  OR-query multiplies store reads. Bound it (member cap, reuse per-member entries)
  or put clan headers behind the same debounced enrichment worker as today.

## ADJUSTMENT 1 — `tools:` placement: top-bar cluster, not the status row

The request asks for `tools:` "in the 2nd row of status indicators." Read
literally, that is the per-tab status row (Agents: `AgentInfoPanel` +
`AgentLoadIndicator` + `LaunchContextBar`; Services: `AxeInfoRow`). I recommend
against that placement:

- The count is **global** (all tool-run owner procs, all sessions in scope), but
  the status row is **per-tab** — it would need duplicating on Agents, Services,
  and Artifacts rows, tripling width pressure on the most crowded row in the UI.
- It is computed by the **same** `proc_gear_lanes()` pass on the **same**
  observer snapshot that feeds `bg:`; splitting the two lanes across two rows,
  two widgets, and two update paths invites skew (one repaints, the other lags).
- The status row already shows *local* tool state (per-row ⚒ chips, header chip).
  A global `tools:` there duplicates information at a different granularity in
  the same visual field.

**Recommended:** `tools:` as a new `TopBarGroup` in `TopBarIndicators`
(`src/sase/ace/tui/widgets/top_bar.py`), ordered immediately after the renamed
`bg:` group, same `CLICK_ACTION` target family (open the Procs tab; ideally
pre-filtered to tool rows — see below). It hides at zero exactly like the gear
chips (`hide_at_zero=True` semantics via `icon_count_chip("⚒", n, "#87D7FF")`),
so narrow terminals and the full↔compact density math behave identically. If the
requester insists on status-row presence, the fallback is a compact `⚒N` segment
inside the deck-chrome subtitle area (which already speaks ⚒), not the
`AgentInfoPanel` strip.

## ADJUSTMENT 2 — rename the label, not the world

- `ProcIndicator.GROUP_LABEL`: `"procs"` → `"bg"`. Tooltip: `"N running
  background procs"` / `"No running background procs\nClick to open the Procs tab"`.
  Keep the tab title "Procs", the widget id `#proc-indicator`, and the
  `ProcGearLanes` field names (`procs` + new `tools`) to minimize churn. A full
  tab rename ("Background") is a fine follow-up, not part of this change.
- Procs-tab header (`procs_pane_selection.py`, currently `gear_chip(proc, …,
  hide_at_zero=False)` + monitor + update): add the ⚒ chip with
  `hide_at_zero=False` so the lane always reads "none" rather than "unknown",
  consistent with the existing comment on that call site. Order: `bg`, `tools`,
  monitors, updates — matching the top bar left-to-right.

## ADJUSTMENT 3 — classify by origin, fall back to tag

In `proc_gear_lane()`, add before the generic `"proc"` return:

```python
if row.origin == "tool-run" or tool_run_id_for_task(row) is not None:
    return "tools"
```

Precedence notes: monitor check first is harmless (origins are disjoint:
`MONITOR_PROC_ORIGIN` vs `"tool-run"`); the tool check must come before the
update check only if a tool proc could ever carry update scopes — it cannot
today, but place the tool branch first anyway so the lane owns its rows
unconditionally. `tool_run_id_for_task` (tag `tool-run:<id>`, pure, already in
`procs_pane_render.py` — hoist it to a shared helper rather than duplicating)
covers rows submitted before any origin backfill. Detached tool rows
(`tool-run-detached`) stay in `tools:` — detachment is a lifetime flag, not a
different kind. `ProcGearLanes` gains `tools: int = 0`; `proc_gear_lanes()`
counts it in the same single pass; `_proc_action_observer.py` passes the third
count through.

Click behavior: `tools:` opens the Procs tab. Stretch goal, worth speccing now:
open it with a tool-run filter applied (the pane already decodes the tag per
row, so a `tool:`/lane filter is a small addition to `procs_filter_bar.py`).
Without that, the count and its rows are one click apart but visually
disconnected; with it, the loop closes.

## Per-node clarity, including clans

1. **Keep the existing row chip exactly as is** for agent/monitor/proc/session
   rows (live-only, silent-aware, minute-quantized). Do not add proc-row ⚒
   duplication beyond today's `_append_tool_run_marker` — the owner proc row
   already shows `⚒ <label>`, and the owned run's chip lives on the owner via
   `select_live_runs` owner-first matching. That two-sided rendering is correct.
2. **Clan containers: aggregate, mirroring session containers.** Extend
   `_RowIdentity` with member agent names for clan containers (the session path
   already harvests `followup_agents`/`runtime_children` + container name; reuse
   the harvester). Matching rule: ownerless live runs whose `agent` is a member,
   plus proc-owned runs whose `owner_id` is a member's proc row — the latter is
   new and matters because clan members launch hand-off procs. Render the
   existing count form (`⚒N`, silent-aggregates to `⚒⚠` when any member run is
   silent, worst-severity ordering reused from `_order_live_runs`). Clicking the
   clan chip expands the clan or opens the Runs card for the worst member —
   pick one, document it in the tooltip.
3. **Clan selection header:** build a clan OR-selector over member names so the
   compact header chip and expanded `Tool runs` field work for clan selection.
   Bound the fan-out (cap members, cap runs at the existing per-node limit,
   LRU-keyed by clan key) and load it on the existing debounced enrichment
   worker — never on the render path, which stays pure/in-memory per the
   module contracts (`header_chip.py`, `summaries.py`).
4. **Do not lift the remote exclusion.** `selector_for_agent` excludes remotes
   because the ledger is machine-local and absence must not read as "no runs"
   (D15). That reasoning is locality, not aggregation, and still holds. Clans
   are local; remotes are not. Keep them separate.

## Beauty guidance (the "last but not least" part)

- One accent only: `#87D7FF` for every live-tool affordance (top-bar chip,
  tab-header chip, row chip, deck subtitle). Silent is the only second color and
  already defined (`⚒⚠`). Never tint ⚒ blue-gear `#48CAE4` — that re-merges the
  lanes you just split.
- Compact density already preserves identity (glyph inside the fill,
  `icon_count_chip`). Verify `tools:` collapses to `⚒ 2` with no label at narrow
  widths and that separator logic (`separator_visibility`) treats the new group
  like the others — it does automatically once registered in
  `_TOP_BAR_GROUP_IDS`, but add the golden test.
- Microcopy: `bg:` (not `background:` — the cluster uses terse labels),
  `tools:` (not `tool:` — it is a count of running tools, parallel to the
  plural `procs:` it replaces). Tooltip should teach the accounting in one line:
  e.g. `"2 running tools (sase tool runs)\nClick to open the Procs tab"`.
- The empty Procs-tab tools lane should read as an explicit zero chip, matching
  the existing "reads none rather than unknown" policy — a missing lane and a
  zero lane must never look the same.

## Verification plan for the implementer

- Unit: `proc_gear_lane` returns `"tools"` for `origin="tool-run"`, for
  tag-only legacy rows, and for detached variants; never `"proc"`. Lanes count
  conservation: `bg + tools == old procs` on a fixture mixing hand-off,
  plain, monitor, service, and update rows.
- Unit: indicator bodies — `bg:`/`tools:` render, hide-at-zero, tooltip text,
  full/compact cell math, separator flags with the new group present and absent.
- Unit: `select_live_runs` clan aggregation (member agent match, member proc-owner
  match, silent folding, count-chip form, remote still excluded).
- TUI goldens/screenshots for the top-bar cluster (full + compact) and the
  Procs-tab header with all four lanes; grep-update every `procs:` expectation,
  doc, and help string.
- Live check: `sase tool run -H -- <slow tool>` while the TUI watches — `tools:
  ⚒ 1` appears, blue `bg:` does not move, owner proc row shows `⚒ <label>`,
  owning node shows the row chip, clan ancestor (if any) aggregates. Kill via the
  tool stop path and watch all three clear together (no orphaned count — the
  classic skew bug this split could introduce if the lanes read different
  snapshots; they must not).

## Open questions

1. Confirm the intended "2nd row" — this report assumes the per-tab status row
   and recommends the top-bar cluster instead (ADJUSTMENT 1). If the requester
   meant something else by "2nd row," the placement advice changes but the lane
   split does not.
2. Should `tools:` count *all* hand-off procs or only ones owning a *live* run?
   Recommend: active proc rows (same `active_rows` scoping as today), which is
   usually identical to live runs but survives ledger hiccups. A proc in
   `settling` with a settled run is the edge — pick active-status-gating and
   document it.
3. Tab rename (`Procs` → `Background`)? Recommend deferring; label-only now.
4. Feature flag? The lane split changes a memorized number; if the project wants
   a gradual rollout, the flags system exists (`sase/memory/sase_flags.md`), but
   my read is this is safe to ship unflagged with tooltip copy doing the teaching.

## Files touched (recommended)

- `src/sase/ace/tui/_proc_observer_models.py` — `GearLane` + `"tools"`,
  `proc_gear_lane`, `ProcGearLanes.tools`, `proc_gear_lanes`.
- `src/sase/ace/tui/widgets/proc_indicator.py` — label `bg:`, tooltip, third count
  (or split a new `ToolIndicator(TopBarGroup)`; prefer a new widget over a
  three-purpose `ProcIndicator` — cleaner ownership, same 10-line shape).
- `src/sase/ace/tui/widgets/top_bar.py` — register group + id ordering.
- `src/sase/ace/tui/actions/_proc_action_observer.py` — pass `lanes.tools`.
- `src/sase/ace/tui/modals/procs_pane_selection.py` — fourth header chip.
- `src/sase/ace/tui/modals/procs_pane_render.py` — hoist `tool_run_id_for_task`
  for reuse by the lane classifier.
- `src/sase/ace/tui/modals/procs_filter_bar.py` — optional `tool:` lane filter
  (click-through target for `tools:`).
- `src/sase/ace/tui/tool_runs/attribution.py`, `summaries.py`, `row_chip.py`,
  `_agent_list_render_agent_status.py`, `_agent_list_render_cache.py`,
  `models/_agent_clan.py` — clan member harvesting, aggregation matching,
  header selector, cache signatures.
- `tests/` + `docs/` — every `procs:` expectation and help string.
