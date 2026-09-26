# Research Report: Nav Section Partitioning for Scheduled Routines in the Services Tab

- **Author:** Researcher gem (`research.e.gem`)
- **Swarm Context:** 5-Researcher Swarm (`gem`, `cdx`, `cld`, `grk`, `mus`)
- **Date:** 2026-09-26
- **Target File:** `/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_24/sase/repos/research/202609/scheduled_routines_nav_sections__gem.md`
- **Research Repo Relative Path:** `202609/scheduled_routines_nav_sections__gem.md`
- **Audience:** Lead Researcher, SASE System Architects, TUI & AXE Engine Developers

---

## 1. Executive Summary & Core Verdict

The user request proposes grouping scheduled routines into different **nav sections** on the Services tab, with an initial intuition that all **builtin routines** should be grouped together, while noting uncertainty about how to group "the other routines."

This research investigates the architectural, navigational, and cognitive ramifications of this proposal, critiques the underlying design assumptions, evaluates credible alternative models, and outlines concrete implementation blueprints.

### Key Conclusions:

1. **Strict Nav Sections (Stacked Bordered Panels) Are a Geometric & Usability Trap**:
   In SASE's canonical terminology, a **nav section** is a distinct, bordered panel in the left-side navigation column of a main TUI tab (e.g., `#service-procs-panel`, `#scheduled-routines-panel`, or individual `@tribe` panels on the Agents tab). Stacking three or more bordered panels inside the Services sidebar (`#bgcmd-list-container`) causes catastrophic vertical compression in standard terminal heights (24 to 35 lines). Fixed chrome overhead (borders, titles, separators, empty placeholders) consumes 8 to 12 rows, leaving each panel with 2 to 3 visible rows and spawning independent, fragmented scrollbars ("scrollbar soup").

2. **"Builtin vs. Other" Is a Flawed, Asymmetric Taxonomy**:
   SASE currently defines seven builtin routines (`hooks`, `waits`, `checks`, `usage`, `external_mirror`, `comments`, `housekeeping`) spanning over 30 jobs across wildly divergent operational domains (fast lifecycle progression vs. hourly database vacuuming). In contrast, most production environments have only zero, one, or two custom/plugin routines (e.g., `telegram`). Grouping by "builtin" vs. "other" yields extreme visual asymmetry (a massive list next to an empty or near-empty box), provides zero functional insight to the operator, and creates an ambiguous "other" dumping ground.

3. **Recommended Direction — Functional In-List Grouping**:
   Instead of physically splitting the sidebar into multiple separate bordered panels, the optimal solution is **In-List Grouping Sections (with category dividers or collapsible section banners)** inside the single existing `scheduled-routines-panel`. This achieves the user's organizational goal with **zero vertical chrome waste**, maintains frictionless `j`/`k` keyboard navigation, preserves existing focus/highlight mechanics, and adapts cleanly to any terminal geometry.

4. **Recommended Grouping Dimension — Functional Domains**:
   Routines should be grouped by **operational purpose** rather than code origin:
   - **`Lifecycle & Progression`** (fast Patch/CL advancement: `hooks`, `waits`)
   - **`Integrations & Connectors`** (external sync & notifications: `telegram`, `external_mirror`, `comments`)
   - **`System & Maintenance`** (resource health, quotas, disk cleanup: `housekeeping`, `checks`, `usage`)

---

## 2. Architectural Context & Canonical SASE Concepts

To ensure precise evaluation, we must ground the analysis in SASE's established memory, UI layout patterns, and AXE scheduling engine.

### 2.1 The Definition of "Nav Section" vs. "In-List Grouping"

Per SASE canonical reference memory (`sase memory read glossary:nav-section`):
> *"A nav section is one panel in the left-side navigation column of a main TUI tab; each of its selectable rows is a nav item. On the Agents tab, every agent tribe panel (`@default`, `@<tribe>`, or the merged `All agents` panel) is a nav section; on the Services tab, the Service Procs and Scheduled Routines panels are; on the Artifacts tab, each pane's entry list... is one... A nav section is a whole panel: grouping banners, in-list headers and dividers (Beads Tasks, the Services `── oneshots ──` divider), the Artifacts relation and Patch info panels, right-side detail panels, and Admin Center lists are not nav sections."*

This distinction is critical:
- **Nav Section**: An independent `OptionList` widget with its own border, dynamic title, Textual focus, selection index, and height allocation.
- **In-List Dividers / Headers**: Visual separators or banner rows rendered *inside* an existing `OptionList` widget (e.g., `_DIVIDER_LABEL = "── oneshots ──"` inside `BgCmdList`).

### 2.2 The Current Services Tab Architecture

The Services tab (`axe-view`) is composed in `src/sase/ace/tui/_app_layout.py`:

```python
with Horizontal(id="axe-view", classes=axe_classes):
    with Vertical(id="bgcmd-list-container"):
        yield BgCmdList(panel_key="service_procs", id="service-procs-panel")
        yield BgCmdList(
            panel_key="scheduled_routines", id="scheduled-routines-panel"
        )
    with Vertical(id="axe-container"):
        with AxeInfoRow(id="axe-info-row"):
            yield AxeInfoPanel(id="axe-info-panel")
            yield LaunchContextBar(id="launch-context-bar-axe")
        yield AxeDashboard(id="axe-dashboard")
```

The left navigation column (`#bgcmd-list-container`) statically stacks exactly two panels:
1. `#service-procs-panel` (`panel_key="service_procs"`): Supervisory daemons and oneshot commands.
2. `#scheduled-routines-panel` (`panel_key="scheduled_routines"`): Scheduled automation routines (lumberjacks) and their subordinate jobs (chops).

#### Subsystem Plumbing:
- **Panel Mapping (`src/sase/ace/tui/actions/axe_display/_panels.py`)**:
  Maintains a unified flat list of items (`_axe_items`) for row restoration and global jump-all modals, but slices it across panels via `ServicesPanelIndex`. `SERVICES_PANEL_ORDER` is currently hardcoded to `("service_procs", "scheduled_routines")`. Item classification is derived by type name:
  - `ServiceProcItem`, `BgCmdItem` $\to$ `service_procs`
  - `LumberjackItem`, `ChopItem` $\to$ `scheduled_routines`
- **Dynamic Height Allocation (`src/sase/ace/tui/util/panel_heights.py`)**:
  `allocate_panel_heights()` distributes the vertical pixel budget of `#bgcmd-list-container`. It accounts for border lines (`border_rows = 2`), inter-panel separators, and minimum readable heights (`border_rows + min(count, 2)`), assigning a `1fr` filler to spare space (`filler_idx=1`, which is the scheduled routines panel).
- **Border Titles & Stats (`src/sase/ace/tui/actions/axe_display/_panel_titles.py`)**:
  Builds rich status titles without disk I/O, computing running/error/idle counts and overrun warnings (`ScheduledRoutinesPanelStats`).
- **Fold Management (`src/sase/ace/tui/actions/axe_display/_loader_items.py`)**:
  Maintains fold state per lumberjack (`lumberjack:<name>`), dynamically appending or pruning `ChopItem` rows based on whether the parent routine is expanded.

### 2.3 The Live Routine Inventory

Inspecting the runtime configuration composed through the Rust core (`load_axe_config()`) reveals the current active routines:

| Routine | Interval | Jobs | Provenance Layer | Primary Responsibility |
| :--- | :--- | :--- | :--- | :--- |
| **`hooks`** | 5s | 8 | `default` | Fast Patch lifecycle, mentors, stale workflows, check polls |
| **`waits`** | 10s | 4 | `default` | Bead claim checks, epic launch flush, sidecar auto-sync, wait holds |
| **`checks`** | 300s | 4 | `default` | Bead task triage, plugin dependencies, PR submission checks |
| **`usage`** | 60s | 1 | `default` | LLM subscription usage window quota refresh |
| **`external_mirror`**| 900s | 4 | `default` | Bidirectional mirror for external GitHub issues/PRs (bob-cli, sase) |
| **`comments`** | 60s | 1 | `default` | Code review and critique comment polling |
| **`housekeeping`** | 3600s | 9 | `default` | Error digests, store compaction, temp reaping, artifact link backfill |
| **`telegram`** | 5s | 1 | `user` / `plugin` | Near-real-time outbound notification delivery to Telegram bot |

All routines except `telegram` originate from `default` (`src/sase/default_config.yml`). `telegram` originates from the user layer (`~/.config/sase/sase.yml`) via `sase-telegram`.

---

## 3. Comprehensive Critique of the Proposal

### 3.1 Critique 1: The Terminal Geometry Trap (Vertical Screen Real Estate)

The most severe flaw in introducing multiple independent nav sections (panels) to the Services sidebar is vertical space exhaustion.

#### The Mathematical Overhead of Stacking Panels
In Textual, each bordered panel (`BgCmdList`) requires:
- Top border: $1$ row
- Bottom border: $1$ row
- Minimum content view: $2$ rows (to show more than one item without immediate scroll-arrow clipping)
- Inter-panel separator: $1$ row

$$\text{Fixed Chrome Overhead for } N \text{ Panels} = 2N + (N - 1) = 3N - 1 \text{ rows}$$

Let us analyze available content rows across standard terminal viewport heights:

| Terminal Total Height | App Chrome (Tabs + Prompt + Footer) | Available Sidebar Height | 2 Panels (Current: Procs + Routines) | 3 Panels (Procs + Builtin + Other) | 4 Panels (Procs + Builtin + Plugins + User) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **24 rows** (Standard minimum) | 6 rows | 18 rows | 13 content rows (Procs: 4, Routines: 9) | **10 content rows** (Procs: 3, Builtin: 5, Other: 2) | **7 content rows** (Total collapse!) |
| **35 rows** (Laptop standard) | 6 rows | 29 rows | 24 content rows (Procs: 6, Routines: 18) | **21 content rows** (Procs: 5, Builtin: 13, Other: 3) | **18 content rows** (Heavy fragmentation) |
| **45 rows** (External monitor) | 6 rows | 39 rows | 34 content rows (Procs: 8, Routines: 26) | **31 content rows** (Procs: 7, Builtin: 20, Other: 4) | **28 content rows** (Manageable but cluttered) |

#### Consequences of the Space Crunch:
1. **Vertical Tree Collapse**: Scheduled routines are not flat single-line items; they are hierarchical trees. Expanding a single routine like `hooks` or `housekeeping` injects 8 to 9 subordinate chop rows. Inside a panel with only 5 to 7 visible rows, expanding even *one* routine forces the entire panel into aggressive scrolling.
2. **"Scrollbar Soup"**: Having three or four narrow, stacked boxes in a single 30-cell-wide column, each sporting its own independent scrollbar gutter and indicator, produces visual chaos and makes skimming impossible.
3. **Contrast with the Agents Tab**: The user may have drawn inspiration from the Agents tab's tribe panels (`@default`, `@epic`, `@job`, etc.). However, on the Agents tab:
   - Items are flat agent nodes (not expandable trees).
   - Tribes can be collapsed to single border lines (`collapsed=True`).
   - The user frequently works in one tribe at a time.
   In contrast, background services are an operational status dashboard where operators need simultaneous situational awareness across all active routines.

### 3.2 Critique 2: The Semantic Failure of "Builtin vs. Other"

The user's prompt notes: *"all builtin routines should be grouped together (I'm not sure how to group the other routines)."*

This intuition reveals a core semantic mismatch:

1. **Extreme Asymmetry**:
   In any realistic installation, "Builtin" contains 7 complex routines and 30+ jobs. "Other" contains 0, 1, or at most 2 routines. A layout where Panel A is massive and overflowing while Panel B has a single lonely row (`telegram`) looks unbalanced and unpolished.
2. **The "Empty Panel" Dilemma**:
   What happens when a developer runs SASE on a project without extra plugins or custom user routines?
   - If the "Other" panel is hidden dynamically, the layout jumps unexpectedly when a custom routine is introduced.
   - If the "Other" panel remains visible, it displays an empty placeholder (`"No routines configured"`), permanently wasting 4 valuable lines of vertical space on nothing.
3. **Packaging Origin vs. Operational Intent**:
   Operators do not monitor their systems according to where python wheels or YAML files were authored. When a developer switches to the Services tab, they ask:
   - *"Did my review mentor start?"* (Lifecycle)
   - *"Is external PR mirroring hanging?"* (Integration)
   - *"Are disk limits being breached?"* (Maintenance)
   Lumping `housekeeping` (hourly vacuum) with `hooks` (5s code review loop) simply because both ship with SASE, while banishing `telegram` to an "Other" category, contradicts user mental models.
4. **Configuration Provenance Ambiguity**:
   SASE's configuration system is multi-layered (`default` $\to$ `plugin` $\to$ `user` $\to$ `overlay` $\to$ `local`). If a user customizes `axe.routines.hooks.interval: 3` in `~/.config/sase/sase.yml`, the `hooks` routine now has contributions in both `default` and `user`. Is it "builtin" or "user"? If provenance determines the panel, overriding a single field threatens to relocate the routine or create bizarre boundary classifications.

### 3.3 Critique 3: Navigation and Interaction Friction

1. **Focus Hopping and j/k Boundary Traversal**:
   Currently, keyboard navigation in the Services tab allows seamless `j`/`k` movement across service procs, oneshots, and routines. However, traversing across panel boundaries in Textual triggers class updates (`-focused-panel`), border recoloring, and widget focus changes. Having three or four panels multiplies boundary crossings, introducing visual flicker and cognitive friction.
2. **Keyboard Shortcut Clashes**:
   Keys like `e` (edit configuration), `d` (toggle description banner), `E` (open error log), and `x` (toggle run) operate on the currently selected item. Splitting routines across multiple panels requires tracking focus across multiple instances of `BgCmdList` and ensuring action dispatchers resolve the correct widget context.
3. **Adaptive Jump Hints Fragmentation**:
   SASE uses adaptive jump hints (`_entry_jump_index_to_hint`) to let users jump directly to any item with a single keypress. Distributing jump letters across multiple separate bordered panels degrades visual scanability compared to a single structured list.

---

## 4. Alternative Approaches & Taxonomy Models

If physical multi-panel nav sections and "builtin vs. other" are both problematic, what are the superior alternatives?

### 4.1 Taxonomy Model: How to Group Routines

Instead of provenance, routines should be classified by one of the following rational dimensions:

#### Model A: Functional Domain (Strongly Recommended)
Group routines by their domain role within SASE:
- **`Lifecycle`** (`hooks`, `waits`): Latency-sensitive Patch lifecycle reconciliation, mentor triggers, CRS workflows, and wait condition resolution. Fast cadences (5s–10s).
- **`Integrations`** (`telegram`, `external_mirror`, `comments`): External boundary connectors, notification dispatchers, remote git/issue tracking. Medium cadences (5s–15m).
- **`Maintenance`** (`housekeeping`, `checks`, `usage`): System hygiene, disk quota monitoring, tmp cleanup, artifact pruning, periodic bead triage. Cadences from 1m to 1h.

*Why this works:* It creates balanced groupings (2 to 3 routines per group), makes intuitive sense to operators, and immediately tells the user what subsystem a custom routine belongs to.

#### Model B: Scheduling Cadence (Lane Speed)
Group routines by tick interval, matching AXE's internal queue architecture:
- **`Fast Lanes`** ($\le 10\text{s}$): `hooks`, `waits`, `telegram`
- **`Standard Polling`** ($1\text{m} - 5\text{m}$): `usage`, `comments`, `checks`
- **`Background Maintenance`** ($\ge 15\text{m}$): `external_mirror`, `housekeeping`

*Why this works:* Aligns directly with resource utilization and latency expectations.

---

### 4.2 Presentation Model: How to Render the Grouping

We evaluate four presentation architectures for rendering the grouped routines:

| Approach | Description | Screen Overhead | Navigation Flow | Complexity | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. In-List Dividers / Headers** | Single `BgCmdList` panel with styled section separator banners (e.g. `── Lifecycle ──`) | **0 extra border rows** (only 1 separator line per group) | Seamless `j`/`k` continuous scrolling | **Low** | **RECOMMENDED PRIMARY** |
| **2. In-List Collapsible Group Nodes** | 2-level hierarchy inside single panel: Category header expandable to Lumberjacks | **0 extra border rows** | Collapsible via Space/Enter; unified list | **Medium** | **EXCELLENT ENHANCEMENT** |
| **3. True Multi-Panel Nav Sections** | Dynamic `BgCmdList` panels stacked in `#bgcmd-list-container` (Agent Tribe style) | **Severe** ($3N-1$ chrome rows) | Tab/Shift-Tab across panels; border thrashing | **High** | **NOT RECOMMENDED** (Usability hazard) |
| **4. Quick View Filtering (Scope Bar)** | Single panel with a scope toggle key (e.g. `f` for `All` / `Lifecycle` / `Integrations`) | **0 extra rows** | Instant filter; no list growth | **Medium** | **GOOD COMPLEMENT** |

---

## 5. Adjustments to User Requirements

Based on the research findings, the following adjustments to the user's initial requirements are strongly recommended:

1. **Requirement Adjustment 1 (Taxonomy)**:
   *Original:* Group all builtin routines together; figure out how to group "other" routines.
   *Adjusted:* Replace the binary "builtin vs. other" dichotomy with **Functional Domain Categorization** (`lifecycle`, `integrations`, `maintenance`). Custom or plugin routines can declare their category (e.g. `category: integrations`), defaulting to a designated general or custom category if omitted.
2. **Requirement Adjustment 2 (Presentation Architecture)**:
   *Original:* Implement grouping as different "nav sections" (separate panels).
   *Adjusted:* Implement grouping as **In-List Category Sections with Dividers / Collapsible Headers** inside the existing Scheduled Routines nav section. This delivers 100% of the visual grouping benefits while avoiding terminal height collapse.
3. **Requirement Adjustment 3 (Adaptive Multi-Panel Fallback, if separate panels are mandated)**:
   *Adjusted:* If the user or product team strictly insists on multi-panel Nav Sections (separate `OptionList` widgets), the implementation MUST include:
   - **Empty-panel pruning**: Panels with 0 routines must be unmounted rather than displayed empty.
   - **Height-adaptive consolidation**: When terminal height falls below 35 lines, the UI must automatically collapse multi-panel mode into a single unified panel with in-list headers to prevent UI breakage.
4. **Requirement Adjustment 4 (Configuration Schema)**:
   *Adjusted:* Add an optional `category` (or `section`) attribute to `LumberjackConfig` in `sase.schema.json` and the Rust AXE configuration parser, backed by hardcoded default mappings for builtin routines so existing configs remain fully backwards-compatible.

---

## 6. Implementation Blueprints

Below are complete implementation blueprints for both the recommended approach (In-List Grouping) and the alternative multi-panel approach.

---

### 6.1 Blueprint A: In-List Functional Grouping (Recommended)

This design maintains a single `BgCmdList` widget for scheduled routines while introducing visual domain groupings.

#### 1. Configuration & Domain Mapping (`src/sase/axe/`)
In `src/sase/axe/_config_types.py`, extend `LumberjackConfig`:

```python
DEFAULT_ROUTINE_CATEGORIES: dict[str, str] = {
    "hooks": "lifecycle",
    "waits": "lifecycle",
    "telegram": "integrations",
    "external_mirror": "integrations",
    "comments": "integrations",
    "usage": "system",
    "checks": "system",
    "housekeeping": "system",
}

CATEGORY_METADATA: dict[str, dict[str, str]] = {
    "lifecycle": {"title": "LIFECYCLE & WORKFLOWS", "icon": "⚡", "color": "#00D7AF"},
    "integrations": {"title": "INTEGRATIONS & CONNECTORS", "icon": "⇄", "color": "#87D7FF"},
    "system": {"title": "SYSTEM & MAINTENANCE", "icon": "⚙", "color": "#FFAF5F"},
    "custom": {"title": "CUSTOM & EXTENSIONS", "icon": "◆", "color": "#D7AFDF"},
}
```

In `sase.schema.json`, allow an optional `category: { "type": "string" }` under `axe.lumberjacks.additionalProperties.properties`.

#### 2. Item Construction & Section Markers (`src/sase/ace/tui/actions/axe_display/_loader_items.py`)
In `_append_lumberjack_items(items)`:
Sort routines by category order (`lifecycle` $\to$ `integrations` $\to$ `system` $\to$ `custom`), then alphabetically.

```python
def _append_lumberjack_items(self, items: list[AxeItem]) -> None:
    # Group routine names by category
    categorized: dict[str, list[str]] = defaultdict(list)
    for name in self._axe_lumberjack_names:
        cat = self._get_routine_category(name)
        categorized[cat].append(name)

    # Append items with category divider flags
    for cat_key in ("lifecycle", "integrations", "system", "custom"):
        routine_names = categorized.get(cat_key, [])
        if not routine_names:
            continue
        is_first_in_cat = True
        for name in routine_names:
            items.append(
                LumberjackItem(
                    name=name,
                    category=cat_key,
                    show_category_divider=is_first_in_cat,
                )
            )
            is_first_in_cat = False
            # Append subordinate chops if lumberjack fold is expanded...
```

#### 3. Row Formatting (`src/sase/ace/tui/widgets/_bgcmd_list_rows.py`)
Extend `format_lumberjack_option`:

```python
def format_lumberjack_option(
    name: str,
    status: Any,
    is_selected: bool,
    category_header: str | None = None,
    hint_char: str | None = None,
    overrun_count: int = 0,
) -> Option:
    text = Text(no_wrap=True, overflow="ellipsis")
    if category_header:
        # Visual divider line styled like _DIVIDER_LABEL
        text.append(f"── {category_header} ──\n", style="dim #87D7FF")

    # Regular lumberjack rendering (▌ [*] name  ⚠1  C:12)
    ...
```

`last_line_cell_len()` already strips leading lines containing `\n`, ensuring that the category divider does not inflate the sidebar width calculation!

#### 4. Navigation & State Integrity
- **Index Stability**: Selection restoration (`restore_selection_by_identity`) continues working transparently because `LumberjackItem` keys (`("lumberjack", name)`) remain unchanged.
- **Heights**: `BgCmdList.rendered_line_count` naturally accounts for the extra divider lines in `allocate_panel_heights()`.

---

### 6.2 Blueprint B: Multi-Panel Nav Sections (The Full Tribe Architecture)

If independent bordered panels are strictly required, the following architectural overhaul is necessary.

```
                    ┌───────────────────────────────┐
                    │     #bgcmd-list-container     │
                    │                               │
                    │  ┌─────────────────────────┐  │
                    │  │  #service-procs-panel   │  │
                    │  └─────────────────────────┘  │
                    │  ┌─────────────────────────┐  │
                    │  │  #routines-lifecycle    │  │
                    │  └─────────────────────────┘  │
                    │  ┌─────────────────────────┐  │
                    │  │  #routines-integrations │  │
                    │  └─────────────────────────┘  │
                    │  ┌─────────────────────────┐  │
                    │  │  #routines-system       │  │
                    │  └─────────────────────────┘  │
                    └───────────────────────────────┘
```

#### 1. Dynamic Layout in `_app_layout.py`
Replace the static `scheduled-routines-panel` with a dynamic container or loop:

```python
with Horizontal(id="axe-view", classes=axe_classes):
    with Vertical(id="bgcmd-list-container"):
        yield BgCmdList(panel_key="service_procs", id="service-procs-panel")
        # Dynamic routine panels mounted per active category:
        for cat in ("lifecycle", "integrations", "system"):
            yield BgCmdList(
                panel_key=f"scheduled_routines_{cat}",
                id=f"scheduled-routines-{cat}-panel",
            )
```

#### 2. Dynamic Panel Partitioning in `_panels.py`
Refactor `_panels.py` to support dynamic panel keys instead of the static `Literal["service_procs", "scheduled_routines"]`:

```python
ServicesPanelKey = str  # "service_procs" | "scheduled_routines_<category>"

def _services_panel_key_for_item(item: object, routine_categories: dict[str, str]) -> ServicesPanelKey:
    match item:
        case ServiceProcItem() | BgCmdItem():
            return "service_procs"
        case LumberjackItem(name=name):
            cat = routine_categories.get(name, "system")
            return f"scheduled_routines_{cat}"
        case ChopItem(lumberjack_name=lj_name):
            cat = routine_categories.get(lj_name, "system")
            return f"scheduled_routines_{cat}"
```

`SERVICES_PANEL_ORDER` becomes dynamic: computed from `"service_procs"` followed by all non-empty routine category panel keys.

#### 3. Height Allocation with Multiple Fillers (`_render_panels.py`)
In `_apply_axe_panel_heights()`:
`allocate_panel_heights()` must be called with $N$ panels:

```python
ordered = [widgets[key] for key in active_panel_order]
collapsed_flags = [self._is_panel_collapsed(key) for key in active_panel_order]
heights = allocate_panel_heights(
    [int(getattr(w, "rendered_line_count", 0)) for w in ordered],
    collapsed_flags,
    container_height,
    filler_idx=1, # Primary routines panel absorbs leftover space
)
```

#### 4. Border Titles & Dynamic Header Stats
Each routine panel gets a dedicated border title formatted with its specific category stats:
- `#routines-lifecycle`: `⚡ Lifecycle · 2 [R:2] ●12`
- `#routines-integrations`: `⇄ Integrations · 3 [R:3] ●6`
- `#routines-system`: `⚙ System · 3 [R:2 I:1] ●14`

#### 5. Keyboard Navigation & Panel Cycling
- Update `Tab` and `Shift-Tab` bindings to cycle focus across all $N$ panels.
- Update `_axe_focused_panel_key()` to dynamically map the current global row index to its corresponding category panel.

---

## 7. Comparative Assessment Matrix

| Dimension | Option A: In-List Grouping Dividers | Option B: Multi-Panel Nav Sections | Option C: Status Quo (Flat List) |
| :--- | :--- | :--- | :--- |
| **Space Efficiency (24-line TUI)** | **Excellent** (0 extra chrome rows) | **Unusable** (11 rows lost to chrome) | **Good** (6 rows chrome) |
| **Space Efficiency (45-line TUI)** | **Optimal** (Clean vertical flow) | **Acceptable** (Readable, but partitioned) | **Spacious** (High density) |
| **Tree Expansion Flexibility** | **High** (Expanded chops expand naturally) | **Poor** (Chops easily clip viewport) | **High** |
| **Visual Scannability** | **High** (Clear domain separation) | **High** (Border-framed sections) | **Moderate** (Homogeneous list) |
| **Navigation Simplicity** | **Frictionless** (Continuous `j`/`k`) | **Moderate** (Frequent panel crossing) | **Frictionless** |
| **Implementation Risk** | **Very Low** (Pure widget/row formatting) | **High** (Dynamic mounting, resize math) | **Zero** |
| **Rust Core / Schema Impact** | **Optional** (Can be purely presentation) | **Required** (Schema & category types) | **None** |

---

## 8. Final Recommendation & Action Plan

### The Recommendation

1. **Reject "Builtin vs. Other"**: Do not classify routines by origin. Adopt **Functional Domain Grouping** (`lifecycle`, `integrations`, `maintenance`).
2. **Implement Blueprint A (In-List Grouping with Dividers)** as the primary solution:
   - It fulfills the user's desire to logically group scheduled routines.
   - It avoids destroying terminal usability on standard display resolutions.
   - It requires minimal, non-breaking modifications to TUI code.
3. **Add Routine Category Configuration**:
   - Provide built-in defaults for all core routines.
   - Allow optional `category:` declarations in `axe.routines` in `sase.yml` for custom routines or plugins.

### Action Plan:

- **Milestone 1 (Presentation Grouping)**:
  - Add `DEFAULT_ROUTINE_CATEGORIES` to `src/sase/axe/chop_inventory.py`.
  - Update `_append_lumberjack_items()` in `src/sase/ace/tui/actions/axe_display/_loader_items.py` to sort routines by category and flag category boundaries.
  - Update `_bgcmd_list_rows.py` to render section divider banners above the first routine of each category.
- **Milestone 2 (Config Extensibility)**:
  - Update `sase.schema.json` to allow `category` on routine definitions.
  - In `src/sase/axe/_config_types.py`, populate `LumberjackConfig.category`.
- **Milestone 3 (Optional Category Collapsing)**:
  - If operators desire the ability to hide entire functional groups, add category-level folding (`category:<name>`) to `_axe_fold_manager` so entire groups can be toggled with `Space`.
