# SASE TUI Design & Architectural Report: Agent Tool Procs, Top-Bar Indicators, and Hierarchical Tool Visibility

**Author:** researcher gem (`research.43.gem`)  
**Date:** 2026-10-08  
**Topic:** Separating Agent `sase tool` Procs from TUI Background Procs, Redesigning Top-Bar Ambient Indicators (`bg:` and `tools:`), and Adding Tool Run Visibility across Tribe Panels and Clan Nodes.

---

## 1. Executive Summary & Verdict

### 1.1 The Bottom Line
The proposed redesign is **an exceptional and necessary architectural improvement** that resolves a deep conceptual conflation in SASE's Textual User Interface (TUI). 

Today, when an autonomous agent invokes `sase tool run` (e.g., executing test suites, build pipelines, or linter gates), the underlying execution spawns a supervisor-managed proc. Because the TUI proc observer classifies any non-service, non-monitor proc as a standard process, agent tool executions leak into the top-bar as blue gears (`procs: ⚙ N`). This gives users the false impression that the TUI itself is performing internal background operations (like index updates or git commits), obscures what the agent is actually waiting on, and breaks the design system rule established in epic `sase-1bt`: **"⚒ now means ToolRun everywhere."**

We strongly recommend implementing this feature, along with three crucial refinements:
1. **Top-Bar Bifurcation (`tools:` & `bg:`):** Demarcate agent tool execution (`tools: ⚒ N`) from internal TUI background operations (`bg: ⚙ N`). When counts are zero, both sections collapse to 0 cells, preserving top-bar horizontal real estate.
2. **Unified Hierarchical Iconography (`⚒` at every tier):** Carry the `⚒` glyph and `#87D7FF` accent consistently from the ambient macro level down to individual turns:
   - **Level 1 (Top Bar):** `tools: ⚒ N` (machine/workspace total live tools).
   - **Level 2 (Tribe Panels):** `⚒ N` in the panel border title and collapsed sidebar rail.
   - **Level 3 (Clan Nodes):** `⚒ N` on clan container rows (`agent.is_clan_container`), bridging the current blind spot where clan members' tools are invisible when collapsed.
   - **Level 4 (Agent Nodes):** `⚒ <label> <progress/elapsed>` live row chip on the active turn.
   - **Level 5 (Deck Sticky Footer):** `tools ⚒N M` on the selected agent's deck subtitle.
3. **Urgency-Aware Ambient Signaling:** Extend the silence detection (`⚠` silent past 60s) into both the `tools:` top-bar indicator and the tribe/clan summary chips (`tools: ⚒⚠ N` in `#FF5F5F`), instantly alerting developers to hung or zombie tool runs without requiring them to drill down into logs.

---

## 2. Analysis of the Existing Architecture & The Root Cause

### 2.1 How Agent `sase tool` Procs Are Spawned
When an autonomous SASE agent runs a command through `sase tool run` (such as `sase tool run check`, `sase tool run pytest`, or ad-hoc commands with `-- ARGV`), execution flows through `sase/tool/executor_entry.py`. 

Because the agent environment contains `SASE_AGENT`, `try_inline_escalation()` in `sase/tool/inline_escalation.py` intercepts the command and invokes `submit_handoff_run()` (`sase/tool/handoff_launch.py`). This creates a dual-state record:
1. **The ToolRun Ledger Record:** A durable row in `runs.sqlite` (managed via Rust core `sase_core::tool_run`), capturing run identity, tool configuration, duration predictions, stages, and execution state (`created`, `running`, `pass`, `failed`).
2. **The Supervisor Proc Request:** A detached supervisor process submitted via `sase.procs.submit_proc_request()`:
   ```python
   ProcSubmitRequest(
       argv=worker_argv(run_id),
       command=command,
       label=label,
       cwd=launch_root,
       origin="tool-run",
       proc_id=proc_id,
       project=project,
       workspace_num=workspace_num,
       session_id=session_id,
       tags=owner_tags(run_id, detached=detached),  # ["tool-run", f"tool-run:{run_id}"]
       env=worker_env_overlay(),
       request_fingerprint=owner_request_fingerprint(run_id),
       followup={"kind": "tool-run", "run_id": run_id},
   )
   ```

### 2.2 Why Tool Procs Leak into `procs: ⚙ N`
The TUI process runs a background daemon thread `ProcObserver` (`sase/ace/tui/proc_observer.py`) that monitors the supervisor proc store. When updating presentation state, `_proc_action_observer.py` executes:
```python
def _update_proc_indicator(self) -> None:
    projection = self._effective_proc_projection()
    lanes = proc_gear_lanes(projection)
    indicator = self.query_one("#proc-indicator", ProcIndicator)
    indicator.set_counts(lanes.procs, lanes.monitors)
```
In `sase/ace/tui/_proc_observer_models.py`, `proc_gear_lanes` iterates through active rows and assigns each to a lane via `proc_gear_lane()`:
```python
def proc_gear_lane(row: ObservedProc) -> GearLane | None:
    if is_monitor_turn_row(row):
        return "monitor"
    if is_service_row(row):
        return None
    if is_update_row(row):
        return "update"
    return "proc"
```
Because a `sase tool` proc has `origin == "tool-run"` and is neither a monitor turn (`origin == MONITOR_PROC_ORIGIN`) nor a service daemon (`origin in (SERVICE_HOST_ORIGIN, SERVICE_ONESHOT_ORIGIN)`), it falls through to `"proc"`. 

Consequently, `lanes.procs` increments for every active tool run, and `ProcIndicator` renders:
```python
text = gear_chip(proc_count, PROC_GEAR_HUE)  # Blue gear: bold #1a1a1a on #48CAE4
```
Thus, agent `sase tool` executions appear as blue gears under the `procs:` header.

### 2.3 The TUI Session Discrepancy & Restart Semantics
As noted in the prompt, agent tool procs are fundamentally detached from the TUI session lifecycle:
- **TUI Session Tasks:** In-process workers (`_session_workers`, prompt submission workers, local git operations, and interactive CLI commands) live inside the Textual process. In `sase/ace/tui/quit_impact.py`, `collect_tui_exit_impact()` warns the user if they attempt a TUI restart (`Ctrl+Q` -> `Restart TUI`) because terminating the process kills those threads.
- **Agent Tool Procs:** Agent tool runs are supervisor-detached. If the TUI restarts (`os.execv`), the tool run continues uninterrupted in the background supervisor. Yet, seeing `procs: ⚙ 3` at the top of the screen leads users to believe they cannot safely restart the TUI or that the TUI is busy processing internal commands.

---

## 3. Critical Evaluation & Architectural Critique

### 3.1 Is the Plan a Good Idea?
**Yes, unequivocally.** The current status indicator conflates two disparate categories of compute:
1. **Ambient Agent Tool Invocations:** Autonomous workload tasks triggered by LLM agents.
2. **TUI / Host Background Operations:** Human-driven or session-scoped background tasks.

Separating them provides immediate cognitive clarity:
- `tools: ⚒ 2` informs the user: *"My agents are actively running 2 tools (e.g., test suites or linters)."*
- `bg: ⚙ 1` informs the user: *"The TUI/host is executing 1 background process (e.g., a background command or git operation)."*

### 3.2 Evaluation of Specific Proposed Changes

#### A. Renaming `procs:` to `bg:`
- **Verdict:** Highly recommended.
- **Rationale:** 
  - The term `procs:` is overly generic. In Unix/Linux environments, "procs" implies OS-level process management (like `ps` or `top`). In SASE, this section does not display all OS processes.
  - `bg:` directly signals "Background Tasks" associated with the TUI session (such as `!` transient commands, durable submits, and session tasks).
  - **Width Advantage:** Top-bar space is constrained. `procs: ` occupies 7 cells; `bg: ` occupies 4 cells. Saving 3 horizontal cells reduces pressure on `choose_top_bar_density()`, preventing premature drops to compact density.
  - **Monitor Handling:** `bg:` should retain both the blue gear for TUI background processes and the orange gear for monitor turns (`sase monitor start`), as monitor turns are supervisor-managed background monitoring jobs. The tooltip should be updated from `"N running procs"` to `"N background processes"`.

#### B. Introducing `tools:` in the Second Row of Status Indicators
- **Verdict:** Highly recommended with key design requirements.
- **Zero-Count Policy:** `tools:` MUST be invisible when count is 0. Unlike tabs, top-bar indicators only claim screen space when actionable or active. When no tools are running, `tools:` consumes 0 cells.
- **Click Behavior:** Clicking `bg:` executes `open_tasks_panel` (navigating to Admin Center -> Procs tab). Clicking `tools:` MUST execute `open_tool_runs_panel` (navigating to Admin Center -> Tools tab, which already exists via `self._open_config_center("tools")`). This provides perfect semantic symmetry.
- **Dual-Source Authority:** 
  - There are two potential data sources: `ProcObserver` (which tracks supervisor proc store rows) and `ToolRunGlanceSnapshot` (which tracks `runs.sqlite` via `tool_run_live_glance()`).
  - *Critique:* An agent can theoretically invoke a tool run that does not spawn a supervisor proc (e.g., an ad-hoc inline tool run or a remote tool call). Furthermore, `ToolRunGlanceSnapshot` already tracks tool stages, typical durations, and silence detection.
  - *Recommendation:* The `tools:` indicator should be driven primarily by `ToolRunGlanceSnapshot.runs` (filtering for `state in {"created", "running"}`), while `ProcObserver` extracts tool procs out of `lanes.procs` so `bg:` remains clean.

#### C. Making Tool Runs Clearer in Tribe Panels and Nodes (Supporting Clan Nodes)
- **Verdict:** Essential. Today, there is a severe visibility disconnect:
  1. **Tribe Panels:** `agent_panel_border_title()` displays total lanes, agent statuses, `⚙<procs>`, `⊛<monitors>`, and `⌖<gates>`. It has **no** tool run indicator. A user looking at 3 tribe panels cannot tell which tribe is running a tool.
  2. **Agent Clan Nodes:** In `sase/ace/tui/tool_runs/attribution.py`, line 134 explicitly states:
     ```python
     if row.is_remote or row.is_clan:
         return ()  # Remote rows and clan containers never match.
     ```
     Because clan containers (`agent.is_clan_container`) are hard-filtered out of attribution, whenever a clan has members running tools, the clan header displays zero tool information. When the clan is collapsed, the user has no idea that tools are executing inside it!

---

## 4. Technical Design & Implementation Blueprint

```
+----------------------------------------------------------------------------------------------------+
|  TopBar: [TabBar: Agents | Artifacts | Services] ... [tools: ⚒ 2] · [bg: ⚙ 1 ⊛ 1] · [updates: ⟳]   |
+----------------------------------------------------------------------------------------------------+
|  Agent Tribe Panel: "❖ Core Team · 8 (4 running) ⚒ 2 ⊛ 1"                                          |
|  ├─ Clan Node: "▾ research-swarm (3 running) ⚒ 1"  <-- [Aggregated Clan Tool Count]                |
|  │  ├─ Agent Turn 1: "research.43.gem (RUNNING) ⚒ pytest 14/28" <-- [Detailed Live Chip]           |
|  │  └─ Agent Turn 2: "research.43.cdx (RUNNING)"                                                   |
|  └─ Agent Turn 3: "standalone-worker (RUNNING) ⚒ cargo check · 42s"                                |
+----------------------------------------------------------------------------------------------------+
|  Sticky Footer / Deck Subtitle: "tools ⚒2 18 calls"                                                |
+----------------------------------------------------------------------------------------------------+
```

### 4.1 Data Classification in Proc Observer
File: `src/sase/ace/tui/_proc_observer_models.py`

1. **Define Tool Proc Recognizer:**
   ```python
   def is_tool_run_proc(row: ObservedProc) -> bool:
       """Return whether an observed proc is an agent tool run."""
       if row.origin == "tool-run":
           return True
       return any(
           tag == "tool-run" or tag.startswith("tool-run:")
           for tag in row.tags
       )
   ```
2. **Update Gear Eligibility:**
   ```python
   def is_gear_eligible_row(row: ObservedProc) -> bool:
       """Return whether an active row counts toward the blue background gear.

       Tool runs, monitor turns, and service rows have their own surfaces;
       ownership is never inferred from session_id.
       """
       return (
           not is_monitor_turn_row(row)
           and not is_service_row(row)
           and not is_tool_run_proc(row)
       )
   ```
3. **Extend `GearLane` and `proc_gear_lane`:**
   ```python
   GearLane = Literal["proc", "update", "monitor", "tool"]

   def proc_gear_lane(row: ObservedProc) -> GearLane | None:
       if is_monitor_turn_row(row):
           return "monitor"
       if is_service_row(row):
           return None
       if is_update_row(row):
           return "update"
       if is_tool_run_proc(row):
           return "tool"
       return "proc"
   ```
4. **Update `ProcGearLanes`:**
   ```python
   @dataclass(frozen=True)
   class ProcGearLanes:
       procs: int = 0
       monitors: int = 0
       tools: int = 0
       update_rows: tuple[ObservedProc, ...] = ()
   ```

### 4.2 Top Bar Widgets: `BgIndicator` and `ToolsIndicator`

#### A. Renaming `ProcIndicator` to `BgIndicator`
Files: `src/sase/ace/tui/widgets/bg_indicator.py` (aliased or renamed from `proc_indicator.py`)
- Change `GROUP_LABEL = "bg"`.
- Update tooltip text:
  ```python
  @staticmethod
  def _build_tooltip(proc_count: int, monitor_count: int) -> str:
      parts: list[str] = []
      if proc_count > 0:
          noun = "background process" if proc_count == 1 else "background processes"
          parts.append(f"{proc_count} {noun}")
      if monitor_count > 0:
          noun = "monitor" if monitor_count == 1 else "monitors"
          parts.append(f"{monitor_count} running {noun}")
      if not parts:
          return "No background processes\nClick to open Background Tasks"
      return f"{', '.join(parts)}\nClick to open Background Tasks"
  ```

#### B. Creating `ToolsIndicator`
File: `src/sase/ace/tui/widgets/tools_indicator.py`
```python
"""Tools indicator widget for SASE's TUI top bar."""

from __future__ import annotations
from typing import Any
from rich.text import Text

from sase.tool.view_vocabulary import TOOL_RUN_ACCENT, TOOL_RUN_GLYPH
from .top_bar_group import TopBarGroup, icon_count_chip

_FAILURE_ACCENT = "#FF5F5F"

class ToolsIndicator(TopBarGroup):
    """Shows running agent tool executions in the top bar.

    Renders as ``tools: ⚒ N`` with the cyan Tools accent chip.
    If any live run has gone silent, renders as ``tools: ⚒⚠ N`` in red.
    Hidden when count is zero. Clicking opens the Admin Center Tools tab.
    """

    GROUP_LABEL = "tools"
    CLICK_ACTION = "open_tool_runs_panel"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._count = 0
        self._silent_count = 0
        self._set_body(self._build_content(0, 0))
        self.tooltip = self._build_tooltip(0, 0)

    def set_counts(self, tool_count: int, *, silent_count: int = 0) -> None:
        if self._count == tool_count and self._silent_count == silent_count:
            return
        self._count = tool_count
        self._silent_count = silent_count
        self._set_body(self._build_content(tool_count, silent_count))
        self.tooltip = self._build_tooltip(tool_count, silent_count)

    @staticmethod
    def _build_content(tool_count: int, silent_count: int) -> Text:
        if tool_count <= 0:
            return Text("")
        if silent_count > 0:
            return icon_count_chip(f"{TOOL_RUN_GLYPH}⚠", tool_count, _FAILURE_ACCENT)
        return icon_count_chip(TOOL_RUN_GLYPH, tool_count, TOOL_RUN_ACCENT)

    @staticmethod
    def _build_tooltip(tool_count: int, silent_count: int) -> str:
        if tool_count <= 0:
            return "No running tools\nClick to open the Tools tab"
        noun = "tool" if tool_count == 1 else "tools"
        text = f"{tool_count} running agent {noun}"
        if silent_count > 0:
            text += f" ({silent_count} silent/stalled ⚠)"
        return f"{text}\nClick to open the Tools tab"
```

#### C. Integrating in `TopBarIndicators`
File: `src/sase/ace/tui/widgets/top_bar.py`
```python
_TOP_BAR_GROUP_IDS: tuple[str, ...] = (
    "tools-indicator",
    "bg-indicator",
    "updates-indicator",
    "alias-overrides-indicator",
    "stashed-prompts-indicator",
    "notification-indicator",
)

def compose(self) -> ComposeResult:
    groups: tuple[TopBarGroup, ...] = (
        ToolsIndicator(id="tools-indicator"),
        BgIndicator(id="bg-indicator"),
        UpdatesAvailableIndicator(id="updates-indicator"),
        AliasOverridesIndicator(id="alias-overrides-indicator"),
        StashedPromptsIndicator(id="stashed-prompts-indicator"),
        NotificationIndicator(id="notification-indicator"),
    )
    for index, group in enumerate(groups):
        if index:
            yield Static(TOP_BAR_SEPARATOR, classes="top-bar-separator")
        yield group
```

### 4.3 Supporting Agent Clan Nodes
File: `src/sase/ace/tui/tool_runs/attribution.py`

1. **Extract Clan Member Names in `row_identity_from_agent`:**
   ```python
   def row_identity_from_agent(agent: object) -> _RowIdentity:
       ...
       is_clan = bool(_get("is_clan_container"))
       clan_member_names: list[str] = []
       if is_clan:
           # Gather child member names from runtime or followup children
           for child in list(_get("runtime_children") or ()) + list(_get("followup_agents") or ()):
               c_name = getattr(child, "agent_name", None)
               if c_name:
                   clan_member_names.append(str(c_name))
       ...
       return _RowIdentity(
           ...
           is_clan=is_clan,
           clan_member_names=tuple(clan_member_names),
       )
   ```
2. **Enable Clan Attribution in `select_live_runs`:**
   ```python
   def select_live_runs(
       runs: object,
       row: _RowIdentity,
   ) -> tuple[ToolRunGlance, ...]:
       candidates = tuple(runs) if isinstance(runs, (list, tuple)) else ()
       live = [run for run in candidates if _is_live(run)]
       if row.is_remote:
           return ()
       if row.is_clan:
           if not row.clan_member_names:
               return ()
           names = set(row.clan_member_names)
           selected = [
               run for run in live
               if _has_no_owner(run) and getattr(run, "agent", None) in names
           ]
           return tuple(_fold_children(selected))
   ```

3. **Render Clan Node Tool Indicator:**
   File: `src/sase/ace/tui/widgets/_agent_list_render_agent.py`
   In the container section alongside monitors and gates:
   ```python
   # On container rows (clans and sequential session containers),
   # append the tool run badge if any tools are actively running in the clan
   if is_container_row and selected_clan_tools:
       text.append(" ")
       text.append(f"{TOOL_RUN_GLYPH}{len(selected_clan_tools)}", style=f"bold {TOOL_RUN_ACCENT}")
   ```
   *Behavior:* When the clan is collapsed, ` ⚒1` shows right on the clan row. When expanded, the clan row shows ` ⚒1` and the specific child row shows its full progress chip (` ⚒ pytest 14/28`).

### 4.4 Supporting Agent Tribe Panels
File: `src/sase/ace/tui/actions/agents/_display_panel_titles.py`

1. **Add `running_tools` to `AgentPanelCounts`:**
   ```python
   @dataclass(frozen=True)
   class AgentPanelCounts:
       lane_count: int = 0
       asking: int = 0
       running: int = 0
       queued: int = 0
       waiting: int = 0
       failed: int = 0
       unread: int = 0
       read: int = 0
       running_monitors: int = 0
       settled_monitors: int = 0
       running_gates: int = 0
       settled_gates: int = 0
       failed_gates: int = 0
       named_procs: int = 0
       running_tools: int = 0  # NEW
   ```
2. **Compute `running_tools` in `agent_panel_counts()`:**
   Query `get_snapshot()` to count live runs attributed to any agent belonging to that tribe panel slice:
   ```python
   snapshot = get_snapshot()
   running_tools = 0
   if snapshot and snapshot.runs:
       panel_agent_names = {a.agent_name for a in agents if a.agent_name}
       running_tools = sum(
           1 for run in snapshot.runs
           if _is_live(run) and getattr(run, "agent", None) in panel_agent_names
       )
   ```
3. **Render in `agent_panel_border_title()`:**
   ```python
   _PANEL_TOOL_GLYPH = TOOL_RUN_GLYPH
   _PANEL_TOOL_STYLE = f"bold {TOOL_RUN_ACCENT}"

   if counts.running_tools:
       title.append(" ", style=_PANEL_COUNT_STYLE)
       title.append(
           f"{_PANEL_TOOL_GLYPH}{counts.running_tools}",
           style=_PANEL_TOOL_STYLE,
       )
   ```
4. **Sidebar Rail Support:**
   In `src/sase/ace/tui/widgets/_agent_list_render_rail.py`, include `⚒` in the collapsed tribe rail status summary when `counts.running_tools > 0`.

---

## 5. Visual Specifications & Styling Palette

To ensure the new components are intuitive, reliable, and aesthetically unified with SASE's design system, the visual tokens are defined as follows:

| Component | Element / State | Glyph | Style / Hex Code | Example Rendering |
| :--- | :--- | :--- | :--- | :--- |
| **Top Bar `tools:`** | Active Tools | `⚒` | `bold #1a1a1a on #87D7FF` | `tools: [ ⚒ 2 ]` |
| **Top Bar `tools:`** | Silent Tool Alert | `⚒⚠` | `bold #1a1a1a on #FF5F5F` | `tools: [ ⚒⚠ 1 ]` |
| **Top Bar `tools:`** | Zero / Inactive | None | None (0 cells) | *(hidden)* |
| **Top Bar `bg:`** | Active TUI Procs | `⚙` | `bold #1a1a1a on #48CAE4` | `bg: [ ⚙ 1 ]` |
| **Top Bar `bg:`** | Active Monitors | `⚙` | `bold #1a1a1a on #FF8700` | `bg: [ ⚙ 1 ⚙ 1 ]` |
| **Tribe Panel Header**| Running Tools | `⚒` | `bold #87D7FF` | `Core · 5 (2 running) ⚒1` |
| **Clan Container** | Clan Tool Count | `⚒` | `bold #87D7FF` | `▾ swarm (2 running) ⚒1` |
| **Agent Row Chip** | Live Tool Run | `⚒` | `bold #87D7FF` | `gem (RUNNING) ⚒ check 3/8` |
| **Agent Row Chip** | Silent Run | `⚒⚠` | `bold #FF5F5F` | `gem (RUNNING) ⚒⚠ check 2m` |
| **Deck Subtitle** | Sticky Footer | `⚒` | `bold #87D7FF` | `tools ⚒1 12 calls` |

---

## 6. Implementation Plan & Migration Safety

The work can be delivered safely in 4 modular stages:

1. **Stage 1: Proc Observer Demarcation & `bg:` Rename**
   - In `_proc_observer_models.py`, implement `is_tool_run_proc()` and update `proc_gear_lane()` so tool runs no longer evaluate to `"proc"`.
   - Update `ProcIndicator` to `BgIndicator` with `GROUP_LABEL = "bg"` and update tooltip strings.
   - Verify that running `sase tool run` no longer causes blue gears to appear in the top bar.

2. **Stage 2: `ToolsIndicator` in TopBar**
   - Create `ToolsIndicator` in `src/sase/ace/tui/widgets/tools_indicator.py`.
   - Mount it in `top_bar.py` under id `#tools-indicator` ahead of `#bg-indicator`.
   - Wire `set_counts()` to update on `ToolRunGlanceSnapshot` loads and `ProcObserver` events.
   - Bind click action to `action_open_tool_runs_panel`.

3. **Stage 3: Clan Node Tool Attribution**
   - In `attribution.py`, collect member names on clan rows in `row_identity_from_agent()` and allow `row.is_clan` to match member runs in `select_live_runs()`.
   - In `_agent_list_render_agent.py`, render `⚒N` on clan container rows.

4. **Stage 4: Tribe Panel Border Titles & Rail Mode**
   - Add `running_tools` to `AgentPanelCounts` in `_display_panel_titles.py`.
   - Add `_PANEL_TOOL_GLYPH` to `agent_panel_border_title()`.
   - Update `rail_panel_title()` in `_agent_list_render_rail.py` to reflect running tools in collapsed sidebar mode.
   - Run full unit test suite and snapshot verifications.

---

## 7. Conclusion

By separating agent `sase tool` executions from TUI background tasks, renaming `procs:` to `bg:`, introducing a dedicated `tools:` ambient indicator, and propagating `⚒` into tribe panel headers and clan containers, SASE will achieve a clean, elegant, and unified process hierarchy. Developers will instantly understand system activity at every level—from the top-bar glance down to the active agent turn.
