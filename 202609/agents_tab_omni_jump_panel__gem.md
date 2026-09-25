# Architectural Research & Design: Agents Tab Omni-Node Jump Panel (`"`)

**Author:** researcher gem (`research.8.gem`)  
**Date:** September 2026  
**Status:** Completed Research & Design Specification  
**Target Subsystem:** SASE TUI (`src/sase/ace/tui/`) — Agents Tab Navigation  

---

## 1. Executive Summary

This report presents an architectural investigation, design critique, and concrete technical blueprint for adding a new `"` (`quotation_mark`) keymap to the SASE TUI "Agents" tab. The feature introduces a dedicated, high-performance **Omni-Node Jump Panel** designed to navigate instantly to any agent node in the loaded workspace roster—including nodes currently collapsed under clans, nested sessions, groups, or hidden by active tab filters—while explicitly excluding non-agent workflow execution steps (Bash and Python steps).

### Primary Conclusions & Verdict
1. **Strong Endorsement:** The proposed panel addresses a critical ergonomic bottleneck in modern SASE swarm, tribe, and multi-agent workflows. As swarms routinely spawn 10–50+ agents organized across hierarchical clans and session containers, manually drilling into nested folds or relying on screen-bound jump hints (`'`) creates significant navigation friction.
2. **Keymap Cohesion:** Binding this to `"` (`quotation_mark` / `Shift+'`) is conceptually brilliant: `'` (apostrophe) represents local, screen-visible hint jumping, while `"` (double quote) elevates the exact same mental model to global, omni-node navigation.
3. **Dual-Mode Keyboard Interaction:** The user's requirement for a dual-mode interaction—defaulting to hint-jumping mode with `<tab>` toggling focus into a query input bar—is viable and powerful. We refine this interaction model with vim-inspired `/` entry, dual `<enter>` / hint dispatch, and non-colliding list navigation (`<ctrl+n>` / `<ctrl+p>`).
4. **Fast, Beautiful Preview:** By separating preview rendering into an instantaneous synchronous metadata card (0 ms) and a debounced background-worker content renderer (150 ms), the panel achieves high visual beauty without violating SASE TUI event-loop performance rules (`tui_perf.md`).
5. **Robust Reveal Contract:** The panel integrates directly with `_agent_reveal.py`'s `prepare_agent_navigation_target` and `reveal_agent_navigation_target` pipeline, resolving folded clan containers, folded sessions, and collapsed panels. Crucially, we identify and solve the `TARGET_FILTERED` edge case where an active main-tab filter would otherwise prevent jumping to a valid target.

---

## 2. Context & Current Navigation Architecture

### 2.1 The Agents Tab Hierarchy
The SASE Agents tab visualizes a multi-layered agent topology:
- **Tribes & Panels:** Top-level visual partitions (e.g. Standard, By Status, By Machine, or custom Tribes).
- **Groups & Banners:** Visual groupings (e.g. by status `RUNNING`, `DONE`, `FAILED`, or project).
- **Clan Containers:** Synthetic parent rows representing an agent clan (e.g. `research`, `review`, `worker`).
- **Clan Members:** Individual agent runs associated with a clan. When a clan container is collapsed, its members are hidden from the rendered list (`_agents`).
- **Sequential Agent Sessions:** Agent sessions containing iterative prompt/response turns.
- **Session Member Shells:** Individual follower runs within a session (`child_linkage == AGENT_SESSION_MEMBER`). When the session is collapsed, members are hidden.
- **Workflow Step Children:** Workflows expand into child steps. These steps can be:
  - Agent steps (`step_type == "agent"`): LLM agent instances with tool-call artifacts.
  - Command steps (`step_type in {"bash", "python"}`): Shell scripts or Python hooks.

### 2.2 Existing Jump Mechanisms & Their Limitations

| Feature | Keymap | Scope | Traverses Folds? | Search Filter? | Node Preview? | Limitation |
| :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **Local Entry Jump** (`jump_to_entry`) | `'` | Current tab left pane | ❌ No | ❌ No | ❌ No | Only annotates rows currently rendered and visible on screen. Cannot jump to hidden/collapsed clan members or session shells. |
| **Fast Jump** (`jump_to_entry_fast`) | `ctrl+o` | Current tab | N/A | N/A | N/A | Reverses through jump history stack (`_entry_jump_agents_anchor_stack`). |
| **Cross-Tab Jump** (`jump_to_all_entries`) | `` ` `` | Artifacts, Agents, Services | ❌ No | ❌ No | ❌ No | Shows top 50 entries across all tabs via `JumpAllModal`. Truncates long lists, lacks filtering, lacks previews, and only indexes top-level visible rows (`self._agents`). |
| **Member Roster Digits** (`_member_jump`) | `0`–`9` | Selected clan/session | ⚠️ Within selected | ❌ No | ❌ (Side panel) | Only active when a container is already selected; only addresses up to 10 members in that specific container. |

**The Gap:** There is currently no way to quickly locate and jump to an arbitrary agent across the workspace without knowing its exact fold location and manually navigating/expanding through Tribe -> Panel -> Group -> Clan -> Member.

### 2.3 Internal Data Structures: `_agents` vs `_agents_with_children`
In `src/sase/ace/tui/`:
- `self._agents`: The currently filtered, rendered, and visible list of agents in the main view. Folded children are absent. Rows filtered out by the active query are absent.
- `self._agents_with_children`: The complete, authoritative in-memory roster of all loaded agents, including collapsed clan members, session member shells, workflow children, monitors, and proc shells.
- `src/sase/ace/tui/actions/navigation/_agent_reveal.py`: Contains `prepare_agent_navigation_target` and `reveal_agent_navigation_target`. This machinery can validate an `AgentIdentity` against `_agents_with_children`, identify the necessary ancestor fold expansions (clan folds, session folds, group banners, panel collapses), expand them via `_fold_manager.expand()`, refilter the view, and locate the resulting index in `self._agents`.

---

## 3. Plan Critique & Design Tradeoffs

### 3.1 Is This a Good Idea?
**Verdict: Yes, exceptional.**
As agent systems scale from single-turn assistants to swarms, pipelines, and autonomous tribes, user cognitive load shifts from "what did this one agent do" to "where is agent X in the fleet?". A fast, fuzzy, searchable omni-jump modal mirrors modern developer tooling standards (e.g. VS Code Quick Open `Ctrl+P`, Neovim Telescope `find_files` / `live_grep`, macOS Raycast / Spotlight). Combining that fuzzy search with Vimium-style direct hint keys gives both keyboard-driven power users (instant keystroke jump) and exploratory users (interactive search filter) optimal ergonomics.

### 3.2 Critique of Specific Requirements & Refinements

#### Point 1: Keymap Selection (`"`)
- **User Request:** Add a new `"` keymap to the "Agents" tab.
- **Analysis:**
  - In `src/sase/default_config.yml`, `'` is `jump_to_entry` and `` ` `` is `jump_to_all_entries`.
  - On standard ANSI keyboards, `"` is `Shift+'`. This creates an exceptionally intuitive pairing:
    - `'` (single quote): Jump among *visible* entries on screen.
    - `"` (double quote): Jump among *all* nodes across the entire agent workspace.
  - **Implementation Detail:** In Textual, pressing `"` generates `event.key == "quotation_mark"` (or `character == '"'`). In `src/sase/ace/tui/keymaps/key_validation.py`, `quotation_mark` is currently missing from `_KEY_DISPLAY`. It must be registered as `"quotation_mark": '"'`.
  - **Terminal Compatibility:** While `"` requires `Shift` on US layouts, it is a single printable character and widely accessible across terminal emulators.

#### Point 2: Dual Mode (Hint Jump vs Query Input vs Tab Toggling)
- **User Request:**
  > "By default, the query input bar should not be selected (so the user can press hint keys). The `<tab>` keymap should be able to be used to focus the query input bar and then unfocus it again to press hint keys."
  > "The user should also be able to use the `<enter>` keymap to select (and jump to) the currently selected node."
  > "The user should be able to cycle through the nodes listed in the panel using the `<ctrl+n/p>` keymaps."
- **Critique & Deep Analysis:**
  There is an inherent UX tension between **Hint Key Navigation** and **Text Search Filtering**:
  - In Hint Mode, pressing any letter (e.g. `a`, `b`, `c`, `s`) immediately executes a jump or registers a hint prefix.
  - In Search Mode, pressing any letter types into the search query.
  If the search bar were focused by default, hint keys could not work without a modifier. If hint keys worked by default without an easy way to search, users with 50+ nodes would have to read two-letter hints across pages.
  **The User's `<tab>` Toggle is the Correct Foundation, but Needs These Ergonomic Polish Points:**
  1. **Dual Entry to Search:**
     - In Hint Mode, both `<tab>` AND `/` (the universal vim search key) should immediately focus the query input bar.
     - When focusing the query bar, visually change the search bar border to an active accent (e.g. cyan `#00D7AF`) and display a subtle badge: `[SEARCH MODE]`.
  2. **Exiting Search Mode:**
     - Pressing `<tab>` returns focus to the list (re-entering `[HINT MODE]`), keeping the currently typed query filter intact!
     - Pressing `<escape>` while in Search Mode should first unfocus the query bar (or clear the search if already empty) and return to Hint Mode. A second `<escape>` dismisses the modal.
  3. **Immediate Action from Search Mode:**
     - Power users who type a query (e.g. `gem`) will often narrow the list down to 1–2 items. They should **not** be forced to press `<tab>` then `a` just to finish.
     - Pressing `<enter>` while in the search bar should **immediately jump** to the currently highlighted item in the filtered list!
     - Pressing `<ctrl+n>` / `<ctrl+p>` (and `up` / `down`) while the search bar is focused must navigate the list selection without losing input focus.
  4. **Dynamic Re-Allocation of Hints:**
     - Whenever the query input changes, the visible list is filtered.
     - As the list shrinks, **hints must be dynamically re-allocated** to the remaining filtered nodes using `build_jump_hint_maps()`!
     - For example, if 40 nodes exist, hints might be two-character (`aa`, `ab`...). If the user filters down to 4 nodes, hints become single-character (`0`, `1`, `2`, `3` or `a`, `b`, `c`, `d`). If the user hits `<tab>`, they can jump with a single keystroke!

#### Point 3: Scope of "Any Node" & Exclusion of Bash/Python Steps
- **User Request:**
  > "navigate to any node, regardless of whether or not it is show. We should be able to jump to hidden agent session shells and hidden agent clan members, for example. Don't include agent shell Bash/Python steps."
- **Node Classification in the SASE Model:**
  Let us strictly define which entities from `self._agents_with_children` are included and excluded:

  | Entity Type | Inclusion | Classification Logic | Rationale |
  | :--- | :---: | :--- | :--- |
  | **Standalone Root Agent** | ✅ Included | `not agent.is_child_row and not agent.is_clan_container` | Primary autonomous agents. |
  | **Sequential Session Container** | ✅ Included | `is_sequential_agent_session_container(agent)` | Root of an interactive multi-turn session. |
  | **Clan Container** | ✅ Included | `agent.is_clan_container` | Synthetic parent representing an entire clan group. |
  | **Clan Member** (Shown or Hidden) | ✅ Included | `bool(agent.agent_clan) and not agent.is_clan_container` | Concrete workers within a clan. |
  | **Session Member Shell** (Shown or Hidden) | ✅ Included | `agent.is_agent_session_member_child` | Sequential turn shells within a session. |
  | **Workflow Agent Step** | ✅ Included | `agent.is_workflow_step_child and agent.step_type == "agent"` | Agent step executing an LLM persona within a workflow. |
  | **Workflow Bash / Python Step** | ❌ **EXCLUDED** | `agent.is_workflow_step_child and agent.step_type in {"bash", "python"}` | **Explicitly excluded by user prompt.** These are non-agent utility scripts. |
  | **Monitors** | ⚠️ Excluded by default | `agent.is_monitor` | Background verification procs, not agent nodes. |
  | **Gates** | ⚠️ Excluded by default | `agent.is_gate` | Approval barriers, not agent nodes. |
  | **Durable Proc Shells** | ❌ Excluded | `agent.is_proc_shell` | Command-line executions tracked in Procs tab. |

#### Point 4: The Hidden Node Jump Contract & The `TARGET_FILTERED` Pitfall
- **The Core Problem:**
  When jumping to a node that is currently hidden:
  - If the node is hidden because its ancestor clan or session container is collapsed, `reveal_agent_navigation_target(self, plan)` successfully expands the container folds (`fold_manager.expand(key)`).
  - **However**, what if the node is hidden because the user has an active filter query in the main Agents tab (e.g. the main tab filter was set to `status:running`, but the target agent is `DONE`)?
  - In `_agent_reveal.py`:
    ```python
    target_idx = _target_index(owner, plan.target_identity)
    if target_idx is None:
        return _AgentRevealOutcome(failure=AgentRevealFailure.TARGET_FILTERED)
    ```
    If the target was excluded by the main tab's filter query, `_target_index` returns `None` and reveal fails with `TARGET_FILTERED`!
- **The Solution / Adjustment:**
  When jumping from the Omni-Jump panel:
  1. Attempt `reveal_agent_navigation_target`.
  2. If the outcome fails with `AgentRevealFailure.TARGET_FILTERED`:
     - Clear the main Agents tab filter (set `self.canonical_query_string = ""` and run `self._refilter_agents()`).
     - Re-attempt `reveal_agent_navigation_target`.
     - Notify the user with a brief toast: `"Cleared Agents tab filter to reveal <agent_name>"`.
  3. Push pre-jump position to `_entry_jump_agents_anchor_stack` so the user can immediately hit `ctrl+o` to return to where they were before the jump!

#### Point 5: Preview Performance & Architecture
- **User Request:**
  > "This panel should be large so we can show a good (but fast) preview of the currently selected node"
- **SASE TUI Performance Requirements (`tui_perf.md`):**
  - *Rule 1: Never block the event loop.* No synchronous disk I/O or heavy parsing on keypress.
  - *Rule 7: Debounce detail panels, never the highlight.* Selection moving (`ctrl+n/p`) must paint in under 16 ms. Detail updates must be debounced (150 ms).
  - *Rule 8: Cache disk reads keyed by mtime.*
- **Two-Tier Fast Preview Architecture:**
  - **Tier 1 — Instant Metadata (0 ms, synchronous):**
    All key identity fields are already present in memory on the `Agent` object:
    - Formatted title, raw suffix, agent ID.
    - Status badge with color (RUNNING, DONE, FAILED, KILLED, WAITING).
    - Clan / Session affiliation, parent linkage.
    - Model name/alias, elapsed runtime or duration.
    - Attached Bead ID, unread status.
    - Hierarchy path (e.g. `Tribe: Default ▸ Clan: research ▸ Member: gem`).
    This header renders instantaneously as the user cycles through rows with `<ctrl+n>` / `<ctrl+p>`.
  - **Tier 2 — Content Snippet (150 ms debounced worker):**
    - The prompt body, live reply tail, or response summary.
    - Checked first against an in-memory preview cache (`agent_session_preview_cache` or a local LRU cache).
    - If uncached, read asynchronously via `asyncio.to_thread` from the agent's artifacts directory (`agent.get_raw_xprompt_content()` or `agent.get_response_content()`).
    - Formatted using `fit_xprompt_preview` (`src/sase/ace/tui/widgets/agent_header_preview.py`) with clean quote bar `▎` and soft Markdown reflow.

---

## 4. Visual & Interaction Design

### 4.1 Aesthetic Concept: The SASE Omni-Jump HUD
The panel is designed as a focused, floating command center (Heads-Up Display) spanning **84% of terminal width** and **82% of terminal height** (minimum 80 cols × 26 rows).

```
╭────────────────────────────── ✦ Agents Omni-Jump ✦ ──────────────────────────────╮
│  🔍 Search: [ research_gem                               ]  [1/48]  [SEARCH MODE] │
├───────────────────────────────────────┬──────────────────────────────────────────┤
│ HINT  NODE / CLAN HIERARCHY   STATUS  │ PREVIEW: research_gem [RUNNING]          │
├───────────────────────────────────────┼──────────────────────────────────────────┤
│ [ a ] ▾ clan: research        2 run   │ Agent ID:    sase-0814-gem               │
│ [ b ]   ├─ researcher.8.cdx   DONE    │ Clan:        research (generation 1)     │
│ [ c ]   ├─ researcher.8.cld   DONE    │ Role:        Swarm Specialist (gem)      │
│ [ d ]   ├─ researcher.8.mus   DONE    │ Model:       gemini-3.8-flash (xhigh)    │
│ [ e ]   └─ researcher.8.gem  ►RUNNING │ Elapsed:     1m 42s                      │
│                               (hidden)│ Bead:        #2841 (Research node jump)  │
│ [ f ]   standalone_task_worker DONE   │ Path:        sase_18/sase/repos/research │
│ [ g ] ▾ session: refactor_tui 3 shells├──────────────────────────────────────────┤
│ [ h ]   ├─ #1: inspect_css    DONE    │ PROMPT PREVIEW                           │
│ [ i ]   └─ #2: apply_styles   WAITING │ ▎ You are researcher gem in a 4-agent   │
│                                       │ ▎ swarm. Conduct research independently  │
│                                       │ ▎ on adding a new '"' keymap to the      │
│                                       │ ▎ Agents tab...                          │
│                                       │ ▎ ¶ Target: Agents tab Omni-Jump panel   │
╰───────────────────────────────────────┴──────────────────────────────────────────╯
│ [Tab] Toggle Search · [^N/^P] Next/Prev · [Enter] Jump · [a-z] Direct · [Esc] Close│
╰──────────────────────────────────────────────────────────────────────────────────╯
```

### 4.2 Visual Styling & Palette Alignment

1. **Header & Badges:**
   - Title: `─── ✦ Agents Omni-Jump ✦ ───` in bold white with `#FFD700` (gold) star glyphs.
   - Mode Badges:
     - `[HINT MODE]`: Badge in `bold #FFFF00 on #333300` when input is unfocused.
     - `[SEARCH MODE]`: Badge in `bold #00D7AF on #003322` when input is focused.
   - Match Counter: `[12 / 48 nodes]` in `dim cyan`.

2. **Search Input Bar:**
   - When unfocused: Thin dim border (`dim #555555`), placeholder text `"Press [Tab] or [/] to filter..."`.
   - When focused: Vibrant accent border (`#00D7AF`), cursor active, instant reactivity.

3. **Node List (Left Pane, ~45% width):**
   - Hint Badges: `[ a ]` or `[ 1 ]` in `bold #FFFF00` (high-contrast yellow) on dark surface.
   - Tree Structure: Subdued tree lines (`├─`, `└─`, `▾`) in `dim #87D7FF`.
   - Hidden Indicator: If a node is currently collapsed/hidden in the main view, a subtle `(folded)` or `(hidden)` tag appears in `dim italic #FF87D7`, signaling to the user that jumping here will unfold the tree.
   - Status Dots:
     - `● RUNNING`: `#00D7AF` (emerald)
     - `● DONE`: `dim #87D7FF` (soft blue)
     - `● FAILED`: `#FF5F5F` (coral red)
     - `● WAITING` / `WORKFLOW`: `#AF87FF` (purple)
     - `● KILLED` / `STOPPED`: `#FF8C00` (orange)
   - Highlight Cursor: Crisp background highlight with a left indicator mark `►`.

4. **Preview Pane (Right Pane, ~55% width):**
   - Left vertical dividing border: `dim #555555`.
   - Identity Header: Two-column key-value layout with dim labels and colored values.
   - Divider: Thin horizontal rule with section tag `── PROMPT PREVIEW ──`.
   - Content: Rich Text with styled quote gutter (`▎ ` in `#AF87FF`) and soft word wrapping.

5. **Footer:**
   - Uncluttered command ribbon with key pills:
     `[Tab] Search` · `[^N/^P] Move` · `[Enter] Jump` · `[a-z] Direct Jump` · `[Esc] Close`

---

## 5. Implementation Blueprint

### 5.1 Architecture & Component Breakdown

```
src/sase/ace/tui/
├── actions/
│   └── navigation/
│       ├── _agent_node_jump.py        <-- Mixin for action_jump_to_agent_node
│       └── _agent_reveal.py           <-- Existing reveal engine (enhanced with TARGET_FILTERED recovery)
├── modals/
│   ├── agent_node_jump_modal.py       <-- Main ModalScreen implementation
│   ├── agent_node_jump_input.py       <-- Dual-mode FilterInput subclass
│   ├── agent_node_jump_list.py        <-- Custom OptionList / list container with hint badges
│   └── agent_node_jump_preview.py     <-- Fast two-tier preview widget
├── keymaps/
│   ├── app_keymaps.py                 <-- Add jump_to_agent_node: str
│   └── key_validation.py              <-- Register "quotation_mark": '"'
└── default_config.yml                 <-- Bind jump_to_agent_node: "quotation_mark"
```

### 5.2 Key Classes and Data Contracts

#### 1. Data Model (`_NodeEntry`)
```python
@dataclass(frozen=True, slots=True)
class NodeJumpEntry:
    """Internal representation of a candidate agent node."""
    agent: Agent
    identity: AgentIdentity
    display_name: str
    hierarchy_label: str       # e.g. "clan: research / researcher.8.gem"
    status: str
    status_style: str
    is_hidden: bool            # True if folded/collapsed or filtered in main view
    indent_level: int          # Visual nesting depth (0 for root/clan, 1 for member)
    search_haystack: str       # Lowercase token string for fast filtering
```

#### 2. Candidate Collector (`_collect_agent_nodes`)
```python
def collect_jump_candidate_nodes(
    agents_with_children: Iterable[Agent],
    visible_identities: set[AgentIdentity],
) -> list[NodeJumpEntry]:
    """Collect all valid agent nodes, strictly excluding Bash/Python steps."""
    entries: list[NodeJumpEntry] = []
    
    for agent in agents_with_children:
        # 1. Strictly exclude Bash and Python workflow steps
        if agent.is_workflow_step_child and agent.step_type in {"bash", "python"}:
            continue
            
        # 2. Exclude non-agent procs/monitors/gates unless desired
        if agent.is_monitor or agent.is_gate or agent.is_proc_shell:
            continue
            
        # 3. Determine display name and hierarchy
        indent = 0
        if agent.is_clan_container:
            name = f"▾ clan: {agent.agent_clan}"
            hierarchy = f"clan:{agent.agent_clan}"
        elif agent.agent_clan:
            name = f"  ├─ {agent.display_name or agent.agent_name}"
            hierarchy = f"{agent.agent_clan} / {agent.display_name or agent.agent_name}"
            indent = 1
        elif agent.is_agent_session_member_child:
            name = f"  └─ {agent.display_name or agent.agent_name}"
            hierarchy = f"session / {agent.display_name or agent.agent_name}"
            indent = 1
        else:
            name = agent.display_name or agent.agent_name or humanize_cl_name(agent.cl_name)
            hierarchy = name
            
        is_hidden = agent.identity not in visible_identities
        
        # Build search haystack: name, clan, id, role, model, task_type
        tokens = [
            agent.agent_name or "",
            agent.display_name or "",
            agent.agent_clan or "",
            agent.cl_name or "",
            agent.raw_suffix or "",
            agent.model or "",
            getattr(agent, "task_type", "") or "",
        ]
        haystack = " ".join(t.lower() for t in tokens if t)
        
        entries.append(
            NodeJumpEntry(
                agent=agent,
                identity=agent.identity,
                display_name=name,
                hierarchy_label=hierarchy,
                status=agent.status,
                status_style=_AGENT_STATUS_STYLES.get(agent.status, ""),
                is_hidden=is_hidden,
                indent_level=indent,
                search_haystack=haystack,
            )
        )
    return entries
```

#### 3. Modal Screen Structure (`AgentNodeJumpModal`)
```python
class AgentNodeJumpModal(ModalScreen[AgentIdentity | None]):
    """Omni-Node jump modal with dual-mode hint keys, live search, and preview."""

    BINDINGS = [
        ("escape", "handle_escape", "Cancel / Unfocus"),
        ("tab", "toggle_input_focus", "Toggle Search"),
        ("ctrl+n", "cursor_down", "Next Node"),
        ("ctrl+p", "cursor_up", "Previous Node"),
        ("enter", "select_highlighted", "Jump to Selected"),
    ]
```

#### 4. Dual-Mode Key Handling & Hint Dispatch
```python
def on_key(self, event: Key) -> None:
    # If the search input currently owns focus:
    if self._input_focused:
        if event.key == "tab":
            event.prevent_default()
            event.stop()
            self._unfocus_input()
            return
        if event.key == "escape":
            event.prevent_default()
            event.stop()
            if self._filter_input.value:
                self._filter_input.value = ""
            else:
                self._unfocus_input()
            return
        if event.key in ("ctrl+n", "down"):
            event.prevent_default()
            event.stop()
            self._move_selection(1)
            return
        if event.key in ("ctrl+p", "up"):
            event.prevent_default()
            event.stop()
            self._move_selection(-1)
            return
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            self._select_current_node()
            return
        # Other typing events flow normally into FilterInput
        return

    # If in Hint Mode (input unfocused):
    if event.key in ("tab", "slash"):
        event.prevent_default()
        event.stop()
        self._focus_input()
        return

    if event.key in ("ctrl+n", "down"):
        event.prevent_default()
        event.stop()
        self._move_selection(1)
        return

    if event.key in ("ctrl+p", "up"):
        event.prevent_default()
        event.stop()
        self._move_selection(-1)
        return

    if event.key == "enter":
        event.prevent_default()
        event.stop()
        self._select_current_node()
        return

    if event.key == "escape":
        event.prevent_default()
        event.stop()
        self.dismiss(None)
        return

    # Check hint key match
    key = normalize_jump_key(event.key, event.character)
    match = match_jump_hint(self._hint_to_entry, self._pending_hint_prefix, key)
    if match.outcome is JumpHintMatchOutcome.PENDING:
        event.prevent_default()
        event.stop()
        self._pending_hint_prefix = match.prefix
        return
    if match.outcome is JumpHintMatchOutcome.COMPLETE and match.target is not None:
        event.prevent_default()
        event.stop()
        self.dismiss(match.target.identity)
        return
```

#### 5. Reveal & Jump Execution with Filter Recovery
```python
def action_jump_to_agent_node(self) -> None:
    """Triggered by '"' keymap on the Agents tab."""
    if self.current_tab != "agents":
        return

    complete = list(getattr(self, "_agents_with_children", None) or self._agents)
    visible_ids = {a.identity for a in self._agents}

    def _on_node_selected(target_identity: AgentIdentity | None) -> None:
        if target_identity is None:
            return

        # 1. Save current jump anchor for ctrl+o back-jump
        save_anchor = getattr(self, "_save_agents_jump_anchor", None)
        if callable(save_anchor):
            save_anchor()

        # 2. Prepare reveal plan
        plan, failure = prepare_agent_navigation_target(self, target_identity, require_current=False)
        if plan is None:
            self.notify(f"Cannot jump to node: {failure.value}", severity="warning")
            return

        # 3. Execute reveal
        outcome = reveal_agent_navigation_target(self, plan)
        
        # 4. Handle TARGET_FILTERED recovery: if hidden by main-tab query, clear it!
        if outcome.failure is AgentRevealFailure.TARGET_FILTERED:
            clear_filter = getattr(self, "action_clear_filter", None)
            if callable(clear_filter):
                clear_filter()
            # Retry reveal on the unfiltered roster
            outcome = reveal_agent_navigation_target(self, plan)

        reveal = outcome.result
        if reveal is None:
            self.notify(f"Could not reveal node: {outcome.failure}", severity="error")
            return

        # 5. Focus panel and select target index
        panel_group = getattr(self, "_panel_group", None)
        if panel_group is not None:
            panel_group.focused_idx = reveal.panel_idx
        self._expanded_panel_focus = False
        self._current_group_key = None
        self.current_idx = reveal.target_idx

        # 6. Acknowledge unread and refresh display
        ack = getattr(self, "_acknowledge_agent_unread", None)
        if callable(ack):
            ack(reveal.target_agent)
            
        self._refresh_agents_display(list_changed=True, defer_detail=False)

    self.push_screen(
        AgentNodeJumpModal(
            agents=complete,
            visible_identities=visible_ids,
        ),
        _on_node_selected,
    )
```

---

## 6. Alternative Approaches Evaluated

### Alternative A: Extend `JumpAllModal` (the Backtick Modal)
- **Concept:** Modify `JumpAllModal` to include filtering and previews, and add hidden agent nodes to its entries.
- **Why Rejected:**
  - `JumpAllModal` is intentionally a lightweight, cross-tab fast switcher spanning Artifacts, Agents, and Services.
  - Adding a search bar, dual-mode focus state, and heavy preview cards would bloat a fast cross-tab modal used for quick switching.
  - Cross-tab clutter: Searching for "gem" in a cross-tab modal would return patches, services, and agents mixed together.
  - The Agents tab has specific domain concepts (clans, sessions, unread status, prompt previews) that do not belong in a generic cross-tab switcher.

### Alternative B: In-Place Filter Expansion on the Agents Tab
- **Concept:** Instead of a modal, pressing `"` focuses the main Agents tab search bar and automatically unfolds all clans and sessions to show all matching nodes inline.
- **Why Rejected:**
  - Highly disruptive to user workspace state: unfolding every clan and group destroys the user's carefully curated fold view.
  - When the user cancels or clears the search, restoring the exact previous multi-level fold state across 50 nodes is error-prone and slow.
  - A modal provides a sandboxed, ephemeral exploration space: you search, inspect previews, jump to the winner, and only the winner's ancestry is expanded, leaving unrelated folds tidy.

### Alternative C: Fuzzy Finder Without Direct Hint Keys (Telescope-Only)
- **Concept:** A standard filter input where all alphanumeric keys type into the search bar, with no hint keys.
- **Why Rejected:**
  - Sacrifices one of SASE's greatest ergonomic strengths: single-letter hint jumping.
  - In a list of 10–20 nodes, typing "research" (8 keystrokes) + Enter is vastly slower than pressing `d` (1 keystroke).
  - The hybrid dual-mode design gives the speed of hint keys when targets are in view, plus the power of fuzzy search when they are not.

---

## 7. Recommended Roadmap & Test Plan

### 7.1 Phased Implementation Stages

1. **Stage 1: Keymap Registration & Core Infrastructure**
   - Register `"quotation_mark": '"'` in `src/sase/ace/tui/keymaps/key_validation.py`.
   - Add `jump_to_agent_node: "quotation_mark"` to `src/sase/default_config.yml` under `agents`.
   - Add `Binding("quotation_mark", "jump_to_agent_node", "Jump to Node", show=False)` in `bindings.py`.
   - Add `action_jump_to_agent_node` stub in navigation actions.

2. **Stage 2: Candidate Collection & Filtering Logic**
   - Implement `collect_jump_candidate_nodes()`, verifying strict exclusion of `step_type in {"bash", "python"}`.
   - Verify inclusion of folded clan members, session shells, and workflow agent steps.
   - Wire substring / fuzzy query matching.

3. **Stage 3: Modal UI & Dual-Mode Controller**
   - Implement `AgentNodeJumpModal` with `FilterInput`, `OptionList`, and `Static` preview container.
   - Implement the `<tab>` / `/` focus toggle and mode badges (`[HINT MODE]` vs `[SEARCH MODE]`).
   - Connect dynamic hint allocation via `build_jump_hint_maps()`.
   - Wire `<ctrl+n>` / `<ctrl+p>` navigation across both modes.

4. **Stage 4: Two-Tier Preview & Detail Panel Debouncer**
   - Implement synchronous tier-1 metadata card.
   - Implement asynchronous tier-2 debounced text reflow using `fit_xprompt_preview()`.
   - Benchmark with `tests/ace/tui/bench_tui_jk.py` to ensure p95 highlight latency remains < 16 ms.

5. **Stage 5: Reveal Pipeline & Filter Reset Integration**
   - Wire modal dismissal to `_reveal_agent_row()`.
   - Implement the `TARGET_FILTERED` recovery loop to automatically clear the main tab filter when jumping to an out-of-filter node.
   - Verify jump anchor recording and `ctrl+o` return navigation.

### 7.2 Verification & Test Strategy
- **Unit Tests:**
  - `tests/ace/tui/test_agent_node_jump_collection.py`: Assert that Bash/Python steps are never returned; assert that folded clan members and session shells are always returned.
  - `tests/ace/tui/test_agent_node_jump_dual_mode.py`: Test key routing in both Hint Mode and Search Mode; test `<tab>` toggle, `/` entry, and `<escape>` un-focusing.
- **Integration Tests:**
  - Open modal in a fixture with 3 folded clans and 2 folded sessions.
  - Select a hidden clan member via hint key; verify modal dismisses, parent clan expands, target row is selected and highlighted, and anchor is recorded.
  - Set active filter `status:running` on main tab. Jump to a `DONE` agent via Omni-Jump. Verify main tab filter is cleared, node is revealed and selected.
- **Performance Benchmarks:**
  - Run `bench_tui_jk.py` with the modal open; assert selection cycling (<16 ms) without event-loop stalling.

---

## 8. Summary & Final Recommendation

The proposed `"` Agents Omni-Node Jump Panel is an outstanding addition to SASE's TUI. It completes the navigation hierarchy by connecting local visible jumping (`'`), cross-tab switching (`` ` ``), and global agent-tree exploration (`"`).

By adopting the refined dual-mode interaction model, the strict node eligibility filter (filtering out Bash/Python steps), the two-tier debounced preview architecture, and the `TARGET_FILTERED` recovery contract, this feature will be **intuitive**, **reliable**, and **exceptionally fast**.

Implementation should proceed according to the phased blueprint detailed in Section 5 and Section 7.
