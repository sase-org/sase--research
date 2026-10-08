# Tools vs TUI-background status: design research

Author: grk (independent swarm researcher)
Date: 2026-10-08
Scope: ACE top-bar activity chips, Procs tab header, Agents-tab row/header/tribe/clan surfaces for `sase tool` work

## Verdict

The request is a good idea and should land. Mixing `sase tool` hand-off procs into the blue `procs:` gear is a real category error: those procs are durable, machine-local ToolRun owners (`origin="tool-run"`), they do not block TUI restarts, and they already speak a different glyph (`⚒`, U+2692) everywhere else.

Take the user's split, then tighten three requirements:

1. Count **live ToolRuns** in `tools:`, not only the procs those runs sometimes own.
2. Put `tools:` in the **existing top-bar indicator cluster** (sibling of today's `procs:`), not on the Agents `load: / model: / project:` row.
3. Reverse D15 for **local clan nodes and tribe panels**. Keep D15 for remote rows.

Keep the orange monitor gear in the renamed `bg:` group. Do not invent a third `mon:` group in this change.

---

## 1. Critique of the proposed plan

The plan as stated:

- Procs created by agents via `sase tool` are a different kind of proc than TUI-triggered work.
- They do not block TUI restarts.
- Reuse the existing `sase tool` icon (the one in the sticky chrome above the decks).
- New `tools:` section with that icon and a count, in the 2nd row of status indicators.
- Stop showing those procs as blue gears in `procs:`.
- Rename `procs:` → `bg:` for the remaining blue gears (TUI-associated background).
- Make tribe panels and nodes (including clan nodes) show when a sase tool is running there.

### What is already true

This is not a greenfield visual language. Epic sase-1bt already decided `⚒` means ToolRun everywhere: Agents-tab live row chip, identity-header chip, Tools-deck subtitle `tools ⚒N M`, `⚒ Runs` card, Procs-tab row marker, Admin Center Tools pane, notifications. The chop/Services trail moved to `⏲` so the two never collide (`docs/ace.md` "Agents Tab Tool Runs"; `src/sase/tool/view_vocabulary.py`).

Restart policy already matches the user's instinct. `collect_restart_blockers` treats independent durable commands, tool runs, monitors, oneshots, and service daemons as non-blockers. Tests in `tests/ace/tui/_update_restart_blockers.py` pin `origin="tool-run"` rows as non-blocking even when `session_id` is this TUI.

Classification already has an authoritative wire: hand-off / detach submit with `origin="tool-run"` and tags `tool-run` + `tool-run:<id>` (`src/sase/tool/handoff_launch.py`, `src/sase/tool/handoff.py`). The TUI already decodes that tag in the Procs pane (`tool_run_id_for_task`).

The miss is presentation: `proc_gear_lane` still buckets those rows as `"proc"`, so they inflate the blue gear.

### Where the plan is incomplete

**Most `sase tool` invocations do not create a proc.** Inside an agent the common paths are:

| Path | Owner | Top-bar today |
| --- | --- | --- |
| Foreground `sase tool run` (inline) | none; the agent is blocked | nothing in `procs:`; live `⚒` on the agent row |
| Soft-ceiling escalation / `sase monitor start` | monitor (`origin` = monitor) | orange `⚙` in `procs:` |
| `sase tool run -d` (agent-only detach) | proc `origin="tool-run"` | **blue `⚙` (wrong)** |
| `sase tool run -H` (outside agents, or TUI "Run project tool…") | proc `origin="tool-run"` | **blue `⚙` (wrong)** |

If `tools:` counts only origin=`tool-run` procs, the top bar stays silent for the usual case: an agent running `check` inline. That is the opposite of "make it clearer when a sase tool is running."

**Clan and tribe surfaces already refuse the chip.** `select_live_runs` and `selector_for_agent` return empty for `is_clan` and remotes (D15). `header_chip_for_node` hard-returns `None` for clan containers. Tribe panel titles already show amber/grey `⚙N` for monitors and `⚙N` for named procs, and **no `⚒`**. Session containers already aggregate member chips. Clans do not. That is the gap the user is pointing at.

**`bg:` collides with an existing word.** The TUI already calls `!` oneshots "background commands" (`BgCmdList`, `bgcmd`). Those oneshots are correctly excluded from the gear (service/oneshot origin). A `bg:` label is still the right length and the right metaphor for TUI-session work, but the tooltip must say "TUI background tasks" so it is not read as the Services-tab `!` list.

**The Procs tab header is the same count source.** `Procs · this session   ⚙ 2  ⚙ 1` is documented to match the top-bar blue/orange pair. Splitting the top bar and leaving the pane header counting tool-run rows as blue would make the two surfaces lie about each other.

### Is this a good idea?

Yes. The current blue gear answers three different questions at once (TUI work, monitors, and named-tool owners). The first two already have distinct chips inside one group. The third has a finished glyph that the group ignores. Users restart ACE, glance at `procs:`, and cannot tell whether a blue `⚙ 3` is "mail is running" or "four agents are in `just check`."

A different approach I considered and rejected: keep one `procs:` group and restyle tool-run rows as a third chip inside it (`⚙ 2  ⚒ 1  ⚙ 1`). That is cheaper and still an improvement, but it keeps the label `procs:` meaning "everything durable," which is what the user is trying to stop teaching. A labeled `tools:` group also gives a correct click target (Admin Center Tools, not Procs).

---

## 2. Requirement adjustments (explicit)

These change the request. Each is justified.

### A. `tools:` counts live ToolRuns, not tool-run procs

**Adjustment.** The `tools:` chip's number is the count of machine-local live ToolRuns (`state` in `{created, running}`), after folding a live child into its live parent (same rule as the row chip). Origin=`tool-run` procs are **excluded from `bg:`** even when the glance is empty.

**Why.** `⚒` already means ToolRun, not "proc that happens to own a run." Inline runs and monitor-owned runs are the work the user wants to see. Counting procs would make `tools:` a rare-path badge for `-H`/`-d` only.

**What stays from the request.** Those procs leave the blue gear. They keep the `⚒` marker on the Procs tab.

### B. Place `tools:` in the top-bar cluster, not the per-tab status row

**Adjustment.** Read "2nd row of status indicators at the top" as the TopBar indicator cluster (the row with `Agents | Artifacts | Services` plus `procs: · updates: · … · inbox:`). Do not put `tools:` on the Agents `load: · model: · project:` row.

**Why.** `procs:` already lives in that cluster. Activity (procs, updates) sits there; launch context (model, project) and runner load sit on the per-tab status row. A tool-run count is machine activity, not launch context. Putting it next to `load:` would mix "how full is the runner" with "is a named tool running," and it would vanish conceptually on Artifacts/Services even though the work is still on the machine.

Chrome layout today (`src/sase/ace/tui/_app_layout.py`):

1. `UsageHeader` — title + provider usage
2. `TopBar` — tabs + indicator cluster (`procs`, `updates`, `overrides`, `stash`, `inbox`)
3. Per-tab status row — Agents: info + `load:` + `model:` + `project:`

### C. Reverse D15 for local clans and tribes; keep it for remotes

**Adjustment.** Local clan nodes get a live `⚒` chip (and a header chip / Runs selector). Tribe panel titles and the tribe identity header get a live `⚒N` badge. Remote rows (`fleet_origin_alias`) still never show a chip: the ledger is machine-local, and absence must not read as "no runs."

**Why.** D15 lumped clans with remotes. The remote reason is sound. The clan reason is not: a local clan is a container of local members, and session containers already aggregate. The user asked for clan support by name.

### D. Keep orange monitors inside `bg:`

**Adjustment.** Do not move monitor turns into `tools:`, and do not add a `mon:` group.

**Why.** A monitor is a detached supervisor. It may own a ToolRun, or it may be `just sleep 30`. The orange `⚙` already answers "how many supervisors." `tools:` answers "how many named tools." A monitor wrapping `check` appears in both, which is honest. Splitting monitors now adds width and a third collapsing group for a question the orange chip already answers.

### E. No feature flag

**Adjustment.** Ship as one visual-language change. Do not hide it behind a beta flag.

**Why.** The Off branch is the bug (tool-run procs in the blue gear, clans without chips). Users are not meant to choose the old mix forever. A sunset flag is for deprecation of a supported branch; this is a replacement of a mislabeled count.

### F. Accept `bg:` as the label, with a precise tooltip

**Adjustment.** Use `bg:` as requested. Tooltip: "TUI background tasks" / "N TUI background tasks." Do not use `tui:` or keep `procs:` for the blue chip.

**Why.** `bg:` matches the surrounding micro-labels (`load:`, `stash:`, `inbox:`). The remaining blue gears really are TUI-associated work (sync, mail, accept, notification gates, session workers). The collision with `!` bgcmds is tooltip-and-docs work, not a reason to fight the requested label.

**Caveat to document.** Clicking `bg:` still opens the Admin Center **Procs** tab, which continues to list tool-run rows (with `⚒`). The tab is the inventory; the chip is a filtered live count. Clicking `tools:` opens the **Tools** tab.

---

## 3. Current architecture (evidence)

### 3.1 Two records, one execution

A ToolRun is the durable ledger row `sase tool run` writes. A Proc is a durable supervised process. Glossary: a ToolRun "is not a monitor or a proc (those may own the run)."

Hand-off creates both: reserve a `created` run, then `submit_proc_request(..., origin="tool-run", tags=owner_tags(run_id), followup={"kind": "tool-run", "run_id": run_id})`.

Inline execution creates only the ToolRun. The agent row is the UI owner.

### 3.2 Gear lanes today

`proc_gear_lane` (`src/sase/ace/tui/_proc_observer_models.py`):

- monitor origin → `"monitor"` (orange)
- service / oneshot → `None` (Services tab)
- update types/scopes → `"update"` (green, in `updates:`)
- everything else active and gear-eligible → `"proc"` (blue)

`origin="tool-run"` falls through to `"proc"`. That is the bug.

`ProcIndicator` renders `procs: ⚙ N` (blue) plus orange `⚙ N` for monitors. Hidden only when both are zero. Click → `open_tasks_panel` (Procs tab).

The Procs pane title uses the same classifier and **shows a dim `⚙ 0` for an empty blue/orange lane** so a missing chip cannot mean "unknown." The top bar hides at zero (ambient badge). Keep that distinction.

### 3.3 The icon the user wants

`TOOL_RUN_GLYPH = "⚒"` and `TOOL_RUN_ACCENT = "#87D7FF"` (`src/sase/tool/view_vocabulary.py`). Comment: "Single-cell ToolRun glyph (plan D1)."

Surfaces that already use it:

- Agents-tab live row chip (`_append_tool_run_chip`) — live only; minute-quantized
- Sticky identity header above the decks (`_tool_runs_chip` in `_identity_header_compact.py`) — this is the "sticky footer shown above deck panels": the header panel's compact second row, physically above the deck column
- Deck switcher subtitle `tools ⚒N M` (bold accent while live, red while silent)
- `⚒ Runs` card
- Procs list: `⚒ <label>` on hand-off owner rows

Reuse this glyph. Do not introduce a new one.

### 3.4 Attribution rules already written

`select_live_runs` (plan §3.3):

1. Remote or clan → no chip
2. Monitor row → owner_kind=monitor and owner_id match
3. Named-proc row → owner_kind=proc and owner_id match
4. Session container → owner-less runs whose `agent` is a member name
5. Concrete agent turn → owner-less runs whose `agent` equals the row

Consequence: a `-H`/`-d` run with `owner_kind=proc` chips the proc row. Tool-run procs are **not** projected as Agents-tab named-proc nodes (`_is_standalone_macro_row` requires `PROC_LIFECYCLE_NAMED_PROC` plus a prompt-proc origin). So proc-owned runs currently have **no Agents-tab row chip at all**. They only show in Procs and in the starter's history field as `→ proc <id>`.

Clan/tribe aggregation must therefore union the subtree (members, their monitors, their named procs) and also credit `run.agent` when it names a member, so a proc-owned run still lights the clan that started it.

### 3.5 Glance snapshot is already the right feed

`ToolRunGlanceLoaderMixin` loads `tool_run_live_glance` off the event loop (`asyncio.to_thread` + `spawn_pump_free_task`), publishes an immutable snapshot, and patches rows whose chip token changed. Render paths read the snapshot plus `now`. No SQLite on keystroke or paint.

The top-bar `tools:` count must be a pure function of that snapshot. Do not add a poll.

### 3.6 Clan status already has the beauty rule to copy

A clan with exactly one running member (`STARTING` included) shows that member's status word, styling, and overlays (`FINALIZING`, etc.). A member that needs the user outranks it. Session/clan containers already show `⚙N` monitor badges on the collapsed row.

Tool chips on clans should follow the same one-vs-many instinct.

---

## 4. Recommended visual language

One sentence: **`⚙` is process supervision. `⚒` is a named tool.** Color is a modifier, never the only signal.

### 4.1 Top bar (full density)

```
bg:  ⚙ 2  ⚙ 1  · tools:  ⚒ 3  · updates: ⬆ 1  · stash:  ≡ 2  · inbox: …
      blue  orange           sky                 moss
```

Compact density drops the labels together, as today. `⚒` vs `⚙` still identifies the group.

**`bg:` body**

- Blue filled `⚙ N` — TUI-associated background (session overlay, this-session durable work, unattributed non-tool procs). Same hue `#48CAE4`.
- Orange filled `⚙ N` — running monitor turns. Unchanged.
- Hide a lane at zero; hide the whole group only when both are zero (top-bar ambient rule).

**`tools:` body**

- Filled `⚒ N` in Tools accent `#87D7FF` on dark ink, via `icon_count_chip` (same chip grammar as gears and stash).
- If any counted run is silent: filled chip in `#FF5F5F`, glyph `⚒⚠` if width allows, else `⚒` plus a red fill. Tooltip must include the word `silent`.
- Hide at zero.
- Click → `action_open_tool_runs_panel` (Admin Center Tools).
- Tooltip example: `3 running tools: check, test, lint` / `1 silent tool: check (4m)` then `Click to open the Tools tab`.

**Left-to-right order.** Keep `bg` in the current `procs` slot (first activity group), insert `tools` immediately after it, then `updates`. Smallest jump for people who look at "the first chip."

**Width.** Full `tools:  ⚒ 3 ` is ~11 cells; compact ` ⚒ 3 ` is ~5. The cluster already collapses labels when the tab strip wins. No new density tier.

**Scope.** `bg:` stays "this ACE session plus unattributed," matching today. `tools:` is **machine-local** (every live glance row). ToolRuns are not TUI-session-bound; counting only this session would hide another TUI's `-H` and every agent inline run.

### 4.2 Procs tab header (must move in lockstep)

```
Procs · this session   ⚙ 2  ⚒ 1  ⚙ 1   [4 running · 5 done]
                       blue  tools orange
```

Empty blue/orange lanes still render dim `⚙ 0`. The tools chip **hides at zero** here too, or shows dim `⚒ 0` if we want the same "unknown vs none" guarantee. Recommendation: dim `⚒ 0` on the Procs header only, because that header is an inventory legend; the top bar is an ambient badge.

Update the invariant: blue + tools + orange + green = running count (service rows remain excluded from this tab's default list).

### 4.3 Agent nodes (concrete turns, monitors, named procs)

Keep the existing live row chip (`⚒ check 7/11`, `⚒ check 2m`, `⚒⚠ check silent 4m`, `+N`). Do not add a second count badge on the same row.

**New:** when the only live run for a visible agent is proc-owned and there is no named-proc row, still show the chip on the **starter agent** (treat `owner_kind=proc` as "owned, but the owner is not a node" and fall back to `run.agent`). That closes the `-H`/`-d` invisibility hole without projecting those procs as Agents-tab nodes.

Do not add tool-run procs as named-proc nodes. The Agents tab would fill with anonymous `sase tool _adopt` rows. The Tools deck and Procs tab already diagnose them.

### 4.4 Clan nodes

Local clans only.

**Zero live tools.** No `⚒`.

**Exactly one live tool** (after child-fold) in the clan subtree. Show that tool's full row chip (`⚒ check 7/11`), mirroring "exactly one running member shows that member's status."

**Two or more.** Show a count badge `⚒N` in Tools accent after the clan status chip and before monitor `⚙N`. If any are silent, `⚒⚠N` in red, or a red `⚒N` plus tooltip.

Subtree = direct clan members, each member's session turns (monitors, gates), and any named-proc children. Union `select_live_runs` over those identities, plus owner-less or proc-owned runs whose `agent` is a member name.

Header chip and `Tool runs` field: same selector. Runs card: allowed. Empty copy for a local clan with no runs stays `No tool runs or LLM calls for this node`. Remote copy unchanged (`ToolRun history lives on <machine>`).

### 4.5 Tribe panels

Panel border title, after the metric chip (or after named-proc `⚙N` if present), before running-monitor `⚙N`:

```
@build · 16 [R4 D12] ⚒2 ⚙3 ⚙1
```

`⚒N` omitted at zero. Silent: red, same as the top bar. Collapse-independent, like monitor badges: a fully collapsed tribe still reports live tools.

Tribe identity header (sticky panel above the decks): add the same `⚒` / `⚒N` chip that agent compact headers already show. `build_tribe_compact_lines` currently has status, counts, fold — no tools.

### 4.6 What not to do

- Do not recolor `bg:` blue gears. They already mean TUI work.
- Do not use ⚙ for tools "because it is a process." The whole point is the glyph split.
- Do not tick the top-bar tools chip every second. Minute-quantize elapsed the way row chips do; live `k/n` progress can update on glance refresh (~1 s store-token probe, already coalesced).
- Do not block the event loop. Glance is in memory; panel counts are a walk of that tuple.

---

## 5. Data model

### 5.1 Exclude tool-run procs from the blue lane

Extend `GearLane` with `"tool"`.

```python
TOOL_RUN_ORIGIN = "tool-run"  # matches handoff_launch.submit

def is_tool_run_row(row: ObservedProc) -> bool:
    if row.origin == TOOL_RUN_ORIGIN:
        return True
    return any(
        isinstance(tag, str)
        and (tag == "tool-run" or tag.startswith("tool-run:"))
        for tag in (row.tags or ())
    )
```

`proc_gear_lane`: after monitor, before service, if `is_tool_run_row` → `"tool"`. Service and monitor still win if a row were both (it should not be).

Origin is authoritative (same pattern as `MONITOR_PROC_ORIGIN` and the service-origin fallback). Tags cover older rows.

`ProcGearLanes` does **not** need to feed the top-bar tools count. It only needs to stop putting those rows in `procs`. Optionally expose `tools_procs` for the Procs header's `⚒` inventory chip.

### 5.2 Top-bar tools count from the glance snapshot

Pure helper next to `row_chip.py`:

```python
def live_tool_run_count(runs, *, silent_after_s, now_ts) -> tuple[int, int, tuple[str, ...]]:
    """Return (live_count, silent_count, labels) after child-fold."""
```

Drive `ToolsIndicator.set_counts` from the same place that applies a glance snapshot (`ToolRunGlanceLoaderMixin` apply path) and once on mount. Do not recompute from the proc observer.

If `tool_runs_disabled_reason()` is set, hide `tools:` and still exclude origin=`tool-run` from `bg:`.

### 5.3 Clan / tribe selectors

Extend `_RowIdentity` with:

- `is_tribe_panel: bool` (panel titles are not nodes; they use a side path)
- `member_identities: tuple[_RowIdentity, ...]` for clans

`selector_for_agent` for a local clan:

```text
key = "clan:<clan-name>"
agents = sorted member agent names
owners = [("monitor", id) | ("proc", id) for members]
```

Core already accepts multi-agent + multi-owner selectors (`ToolRunSelector.to_request`). No `sase-core` API change.

`select_live_runs` for a clan: union of the member rules, then `_fold_children`. Do not name-prefix guess (`clan.` prefix matching is forbidden; attribution stays by node kind and recorded `agent` / owner ids).

Tribe panel: union over the panel's visible top-level agents (including nested clan containers, which now recurse). Same snapshot, no extra IO.

### 5.4 Rust core boundary

Lane coloring, chip chrome, and tribe title layout are TUI presentation. The ledger and glance already live in `sase-core` (`tool_run_live_glance`). Do not reimplement glance in Python. Do not add a Python fallback. Do not put `GROUP_LABEL = "bg"` in core.

---

## 6. Implementation map (for the eventual epic)

Suggested phases, each shippable and screenshot-backed:

1. **Classifier + top bar + Procs header.** `is_tool_run_row`, `GROUP_LABEL = "bg"`, new `ToolsIndicator`, wire glance count, click to Tools tab, docs for Top-Bar Indicators / Proc Indicator / Procs Tab. Tests: `test_proc_gear_lanes`, `test_proc_indicator`, `test_top_bar_indicators`, `test_procs_pane_header_counts`.
2. **Starter fallback for proc-owned runs** on concrete agent rows (the `-H`/`-d` hole). Tests in `test_tool_runs_attribution` (new or extend).
3. **Local clans.** Reverse D15 in attribution, summaries, header chip, deck empty-state only for remotes. Clan row chip + header chip. Tests that currently pin "clan has no chip" invert for local clans and stay for remotes (`test_tool_runs_header_chip.py::test_remote_and_clan_have_no_chip_or_field`).
4. **Tribe panel titles + tribe compact header.** `AgentPanelCounts.live_tools` / `silent_tools`. Visual snapshots for a collapsed tribe with a live check.
5. **Goldens.** `just fix-tui-screenshots` for top-bar, procs header, clan row, tribe title. Inspect the report; do not treat generation as approval.

Keep the change inside the TUI + docs + tests. No CLI flag, no config field, no keymap change (`p` stays Procs; Tools already has `action_open_tool_runs_panel`).

### Files that will move (expected)

- `src/sase/ace/tui/_proc_observer_models.py`
- `src/sase/ace/tui/widgets/proc_indicator.py`
- `src/sase/ace/tui/widgets/tool_runs_indicator.py` (new)
- `src/sase/ace/tui/widgets/top_bar.py`
- `src/sase/ace/tui/actions/_proc_action_observer.py`
- `src/sase/ace/tui/tool_runs/attribution.py`
- `src/sase/ace/tui/tool_runs/summaries.py`
- `src/sase/ace/tui/tool_runs/header_chip.py`
- `src/sase/ace/tui/tool_runs/row_chip.py` (count helper)
- `src/sase/ace/tui/tool_runs/loader.py` (publish count with snapshot)
- `src/sase/ace/tui/actions/agents/_display_panel_titles.py`
- `src/sase/ace/tui/widgets/_agent_list_render_agent.py`
- `src/sase/ace/tui/widgets/_agent_list_render_cache.py` (clan chip token)
- `src/sase/ace/tui/widgets/prompt_panel/_identity_header_compact.py`
- `src/sase/ace/tui/modals/procs_pane_selection.py`
- `docs/ace.md` (Top-Bar Indicators, Proc Indicator, Agents Tab Tool Runs, glyph table, Procs Tab)
- matching tests and PNG goldens

`src/sase/default_config.yml` only if a keymap comment names `procs:`; the indicator labels are not config.

### Performance

Follow `tui_perf.md`: snapshot apply is already pump-free; `set_counts` is a signature no-op when unchanged (copy `ProcIndicator`). Clan title math is O(live runs × visible nodes) on data already in RAM. Do not stat the ToolRun store from a render path.

### Tests that will fail on purpose until updated

- `test_busy_cluster_renders_all_labels_wide` asserts `"procs:"` and `"procs:  ⚙ 2  ⚙ 1 "`
- `test_remote_and_clan_have_no_chip_or_field` (split remotes vs local clans)
- `test_procs_pane_header_counts` blue-chip == top-bar gear count
- `test_lane_totals_preserved` (`lanes.procs + lanes.updates == eligible`)
- PNG snapshots under `tests/ace/tui/visual/snapshots/png/` for top bar and updates/proc fixtures

---

## 7. Beauty notes (so the epic does not ship a correct-but-ugly chip)

- Same chip grammar as gears: padded ` {glyph} {n} `, bold dark ink on a filled hue, identity glyph inside the fill so compact mode still reads.
- `⚒` is already documented as single-cell. Do not wrap it in extra spaces that gears do not get.
- Sky `#87D7FF` vs TUI cyan `#48CAE4` is close. The glyph is the discriminator; if a screenshot review finds the two chips blob together, darken the tools fill one step (`#5FA8D3`) rather than inventing a new hue family. Prefer keeping `#87D7FF` first so Tools-deck, row chip, and top bar stay one color.
- Silent is red **and** the word/⚠, never color alone (existing ToolRun vocabulary).
- Tribe title order: metrics, named-proc count, **live tools**, running monitors, settled monitors, gates. Tools sit with "what is happening," not with "how many named procs exist."
- Do not pluralize labels (`tools:` / `bg:`), matching `procs:` / `stash:` / `inbox:`.

---

## 8. Risks

- **Double-count anxiety.** A monitor-owned `check` is orange `⚙` and `⚒`. Teach it in the tooltip: monitors are supervisors; tools are named catalog runs. This is the same as a row that is both `TESTING` and `⚒ check 7/11`.
- **Glance truncated.** Snapshot can set `truncated=True`. If live rows were dropped, the count is a lower bound. Show the count we have; do not paint a `+` that looks like extra tools. Optional follow-up: tooltip "count may be incomplete."
- **Name reuse.** `run.agent` plus `since_ts` already guards reused agent names on node summaries. Clan aggregation should pass the same `since_ts` window (clan container start minus 60 s, or union of member starts).
- **Visual golden churn.** Top bar is on many snapshots. Budget a screenshot pass; inspect groups, do not batch-accept.
- **`bg:` vs `!` vocabulary.** Docs and tooltip must say "TUI background tasks." A later rename to `tui:` is available if users confuse the two in practice; do not pre-split the epic for it.

---

## 9. Recommended solution

Ship one visual-language change:

1. **`bg:`** — today's `procs:` group, blue gears only for TUI-associated background, orange gears still monitors. Exclude `origin="tool-run"` (and `tool-run:` tags) from blue.
2. **`tools:`** — new top-bar group immediately after `bg:`, filled `⚒ N` in Tools accent, count = folded live ToolRuns from the existing glance snapshot, red when any are silent, click opens Admin Center Tools, hide at zero.
3. **Procs header** — add a `⚒` lane so it cannot disagree with the top bar.
4. **Agents tab** — keep per-node live chips; fall back proc-owned runs onto the starter row; give **local clans** the same live chip (full chip if one, `⚒N` if many); give **tribe panel titles and the tribe sticky header** a collapse-independent `⚒N`.
5. **Remotes stay chip-less** (D15's real reason).

That is intuitive (one glyph, one meaning), reliable (origin + glance, no render-path IO, restart policy already correct), and beautiful (existing chip grammar, existing Tools accent, clan one-vs-many copied from clan status).

Do not count only hand-off procs. Do not put `tools:` on the `load: / model: / project:` row. Do not add a `mon:` group. Do not feature-flag it.
