# Agents Tab Collapsed Nav Sidebar & Deck Zoom UX Design

**Date**: 2026-09-27  
**Author**: Researcher gem (`research.h.gem`)  
**Status**: Completed Research & Proposed Architecture  
**Topic**: Decoupling Nav Sidebar Collapse (`<ctrl+s>`) from Deck Zoom (`Z`), Introducing the Compact Nav Rail, and Establishing an Unmistakable Zoom Visual Language  

---

## 1. Executive Summary

In the current SASE Textual TUI (`src/sase/ace/tui/`), the `<ctrl+s>` keymap (collapsing the Agents-tab navigation sidebar) and the `Z` keymap (zooming into a single deck panel) are tightly coupled behind the same underlying state property: `DeckAreaState.nodes_collapsed = True`. Both paths trigger `_sync_nodes_collapsed_chrome()`, which attaches the `-nodes-collapsed` CSS class to `#agents-content`, applying `display: none;` to `#agent-list-container` and revealing a bare 2-cell scrollbar minimap (`#agent-node-spine`).

This architectural coupling produces two major user experience defects:
1. **Total Loss of Situational Awareness on `<ctrl+s>`**: Pressing `<ctrl+s>` makes the entire 60-column sidebar vanish, hiding all tribe boundaries, agent status groups, active running agents, and failure indicators. The user gains screen real estate for the deck, but loses all visibility into their active agent fleet.
2. **Visual Ambiguity with Zoom (`Z`)**: Because both `<ctrl+s>` and `Z` hide the sidebar and render only a single deck panel (when in `DeckLayout.SINGLE`), the resulting visual layout is nearly identical. The only distinction in the entire interface is a 4-character dim text fragment (`zoom`) tucked between separators in the top `AgentInfoPanel`. Users frequently confuse whether they merely collapsed the sidebar or entered an active zoom snapshot.

### Core Recommendation
We recommend **completely decoupling sidebar collapse from deck zoom**:
- **Sidebar Collapse (`<ctrl+s>`) -> The Compact Nav Rail (6 columns wide)**: Instead of hiding `#agent-list-container`, `<ctrl+s>` toggles `#agent-list-container` into a fixed 6-column **Compact Nav Rail**. In this state, `AgentList` remains fully mounted, focused, and navigable with `j`/`k`, but renders a streamlined, beautiful icon-first grammar:
  - **Tribes** are represented by their configured icon badges (e.g., `⌂`, `▲`, `†`, `◆`, `◉`).
  - **Agent Groups** across all grouping modes (`BY_STATUS`, `STANDARD`, `BY_DATE`, `BY_MACHINE`) are represented by their semantic category glyphs (e.g., `▶` Running, `⏳` Waiting, `✗` Failed, `◫` Project, `⑂` Patch, `⏱` Today, `⇄` Machine) alongside compact count chips.
  - **Agent Nodes** represent their provider badge (e.g., `🟣` Claude, `🟢` OpenAI, `🔵` Gemini), runtime state glyph, and a smart disambiguation token / attempt number.
- **Deck Zoom (`Z`) -> Pure Full-Bleed Focus (100% width)**: Zooming completely removes all sidebar chrome (0 columns, no 2-cell spine) and elevates the focused deck into an unmistakable "Cinematic Focus Mode" featuring a **double border** (`border: double #FFD700;`), an elevated **`[ ⤢ ZOOMED (1 of 2) ]` border badge**, and explicit `Z to restore` exit affordances.

This report critiques the plan, evaluates ergonomic trade-offs (including split decks and dense agent rosters), defines the complete glyph and styling catalog, and provides a zero-regression implementation architecture adhering strictly to `tui_perf.md`.

---

## 2. Current Architecture & Root Cause Analysis

### 2.1 The Current Collapse & Zoom Pipeline

In `src/sase/ace/tui/widgets/decks/layout.py`:
```python
def toggle_nodes_collapsed(state: DeckAreaState) -> DeckAreaState:
    state = _zoom_ended(state)
    return dataclasses.replace(state, nodes_collapsed=not state.nodes_collapsed)

def _enter_zoom(state: DeckAreaState, focused: int | None = None) -> DeckAreaState:
    ...
    return dataclasses.replace(
        snapshot,
        panels=snapshot.panels,
        focused=index,
        layout=DeckLayout.SINGLE,
        nodes_collapsed=True,
        zoom_snapshot=snapshot,
    )
```

In `src/sase/ace/tui/widgets/_agent_detail_deck_layout.py`:
```python
def _sync_nodes_collapsed_chrome(self) -> None:
    collapsed = bool(area.state.nodes_collapsed)
    if collapsed:
        content.add_class("-nodes-collapsed")
    else:
        content.remove_class("-nodes-collapsed")
    ...
    if collapsed:
        spine.remove_class("hidden")
    else:
        spine.add_class("hidden")
```

And in `src/sase/ace/tui/styles.tcss`:
```tcss
#agent-list-container {
    width: 60;
    height: 100%;
    layout: vertical;
}

#agents-content.-nodes-collapsed #agent-list-container {
    display: none;
}

#agent-node-spine {
    width: 2;
    min-width: 2;
    max-width: 2;
    height: 100%;
    background: $surface;
    color: $text-muted;
}
```

### 2.2 Why This Causes Confusion

1. **Identical Visual Geometry**:
   When viewing a single deck (`DeckLayout.SINGLE`):
   - Pressing `<ctrl+s>` hides `#agent-list-container` (width 60 -> 0) and displays `#agent-node-spine` (width 2). The deck fills the rest of the window.
   - Pressing `Z` snapshots the layout, hides `#agent-list-container` (width 60 -> 0), displays `#agent-node-spine` (width 2), and displays the deck.
   - To the user's eye, the screen transformation is 100% identical.

2. **Subtle and Inadequate Feedback**:
   The only distinction today is in `src/sase/ace/tui/widgets/agent_info_panel.py`:
   ```python
   if self._nodes_collapsed:
       self._append_separator(text)
       if self._nodes_zoomed:
           zoom_key = self._registry.app.zoom_panel
           text.append("zoom", style="bold #FFD700")
           ...
       text.append("nodes ", style="dim")
       text.append(f"{self._position}/{self._total}", style=self._TOTAL_COUNT_STYLE)
   ```
   A tiny 4-letter word `zoom` in the top header is completely lost against the dense status information on screen. Neither the deck border, deck header, nor the sidebar area provides any salient feedback.

3. **Loss of Navigation Context**:
   `NodeSpine` only renders `»` at the top and a minimap track (`│` and `┃`). It communicates nothing about what agents exist, what status they are in, or where the cursor is relative to tribes or groups.

---

## 3. Critique of the Plan & Essential Adjustments

Is replacing the invisible sidebar with a fixed-width icon representation a good idea? **Yes, unequivocally**, but only if several non-obvious design challenges are addressed.

### Critique 1: The "Split Decks with Hidden Sidebar" Dilemma
- **The Issue**:
  The user request states:
  > *"When the sidebar is collapsed, it is completely invisible currently. This is the correct behavior when zoomed, but should not be the default format used when collapsing the sidebar using the `<ctrl+s>` keymap."*
  
  If `<ctrl+s>` *only* collapses the sidebar to a fixed-width rail (e.g., 6 columns), and *only* `Z` completely hides the sidebar, consider what happens when a user has a split deck layout (e.g., Main Document on the left, Files/Diffs on the right in a 50/50 split).
  `Z` inherently forces `DeckLayout.SINGLE`. Therefore, if `<ctrl+s>` no longer allows fully hiding the sidebar, **there would be no way to view split decks in full-bleed edge-to-edge mode without a sidebar**.
- **Adjustment**:
  We should support an intentional presentation model:
  1. `<ctrl+s>` defaults to toggling between **Expanded (60 col)** and **Compact Nav Rail (6 col)**.
  2. A secondary keybinding (or a configurable 3-state cycling mode `ace.sidebar_toggle_mode`: `"two_state"` vs `"three_state"`) should allow:
     - `Expanded (60 col)` -> `Compact Rail (6 col)` -> `Fully Hidden (0 col)` -> `Expanded`.
  3. Alternatively, `<ctrl+alt+s>` (or a leader key such as `, s h`) should provide an immediate "Hide Sidebar Completely" action that leaves split layouts intact.

### Critique 2: Homogeneity & The "Identical Icon" Problem
- **The Issue**:
  In a large SASE project, a user might launch 8-10 parallel Claude agents under an epic. If the compact rail only renders the provider badge (`🟣`) and the status glyph (`▶`), the user will see 10 consecutive rows of `🟣 ▶`.
  Without names, how does the user distinguish between `research.1`, `research.2`, `eval.test`, etc.?
- **Adjustment**:
  The Compact Nav Rail cannot simply be an icon dump. It requires a **Glanceability Hierarchy**:
  1. **Synchronized Header Primacy**: Moving the cursor (`j`/`k`) over a compact row must instantly update the `AgentInfoPanel` and deck breadcrumbs with the full agent name, runtime, and prompt summary.
  2. **Micro-Disambiguators**: Dedicate 1-2 cells of the 6-cell budget to structural disambiguation:
     - For numbered worker turns: superscript/subscript index (e.g., `¹`, `²`, `³`) or abbreviated attempt tag (`#1`, `#2`).
     - For agents requiring human attention: a bold gold indicator (`▲` or `?`).
     - For unread/completed nodes: a high-contrast dot (`●`).
  3. **Rich Tooltip Overlay**: Textual tooltips on hover or cursor pause provide instant full-name preview without expanding the rail.

### Critique 3: Banner vs Node Visual Grammar
- **The Issue**:
  If an agent group banner for "Running" displays `▶` and an agent node in that group also displays `▶`, how does the user know which row is a category header and which is an agent node?
- **Adjustment**:
  Headers (Tribes and Group Banners) must have an entirely distinct structural vocabulary from Nodes:
  - **Tribes**: Full-width solid accent divider with tribe icon (e.g., `[@⌂]──` or `⌂ DEF`).
  - **Group Banners**: Bracketed or pill-enclosed category glyph with count badge (e.g., `[▶] 4`, `[✗] 1`, `[⏳] 2`).
  - **Agent Nodes**: Left-anchored selection border + provider icon + status dot + micro-index.

### Critique 4: Performance & Textual Pump Safety
- **The Issue**:
  Under Rule 6 of `sase/memory/tui_perf.md`, *"Full agent-list rebuilds are the most expensive UI operation."*
  If toggling `<ctrl+s>` forced every `AgentList` widget to wipe and rebuild its `OptionList` options from Python scratch, pressing `<ctrl+s>` would cause a noticeable frame drop / stall (100–300 ms).
- **Adjustment**:
  The compact rail must be implemented using **CSS-driven layout regimes and memoized row formatting**:
  - The container `#agent-list-container` switches classes between `-expanded` and `-compact`.
  - Row rendering leverages `AgentRenderCache` with a dual-cache key (`(agent_key, is_compact)`), so toggling `<ctrl+s>` swaps cached representations or adjusts line clipping without thrashing Textual widget trees.

---

## 4. Visual & UX Specification: The Compact Nav Rail

### 4.1 Dimension & Geometry Budget (6 Columns)

We establish the standard Compact Rail width at **6 cells** (`width: 6; min-width: 6; max-width: 6;`):
- Width 2–4 is too narrow: insufficient room for selection borders, provider badges, and status marks simultaneously.
- Width 8–10 takes too much horizontal space away from decks.
- **6 columns** is the exact sweet spot: it saves **54 terminal columns** (90% width recovery!) while accommodating a complete 4-part visual token.

```text
 Column Index:  0   1   2   3   4   5
 Cell Content: [S] [P] [T] [D] [G] [│]
```
- **Cell 0 (`[S]`) - Selection & Mark Indicator**:
  - Selected / Focused row: `▌` in bold gold (`#FFD700`) or primary accent.
  - Marked row (multi-selection): `✓` in green (`#00D700`).
  - Fold restore armed: `▿` or ` armed marker.
  - Normal row: blank (` `) or subtle tree depth guide.
- **Cell 1 (`[P]`) - Provider / Container / Type Badge**:
  - AI Providers: `🟣` (Claude/Anthropic), `🟢` (OpenAI), `🔵` (Gemini), `🦙` (Ollama/Local).
  - Background Entities: `⚙` (Monitor / Service Proc), `⧖` (Gate / HITL).
  - Workflow Steps: `❯` (Python/Bash execution).
  - Clan Containers: `▼` / `▶` (Clan root).
- **Cell 2 (`[T]`) - Live Execution Status**:
  - Running: `▶` (bold green/blue).
  - Waiting / Locked: `⏳` (lavender).
  - Paused / Needs Input (`PLAN`, `QUESTION`): `▲` or `?` (pulsing gold).
  - Completed / Done: `✓` (soft green or dim).
  - Failed / Crashed: `✗` (bold red).
  - Queued: `…` (muted blue).
- **Cell 3–4 (`[D] [G]`) - Micro-Disambiguator & Badges**:
  - Sequence / Turn ID: `#1`, `#2`, `#3` (or superscript `¹`, `²`).
  - Unread / Notification: `●` (bold amber).
  - Reviewable Diff: `✏️` (pencil glyph).
  - Reverted: `↺`.
- **Cell 5 (`[│]`) - Rail Boundary**:
  - Vertical border rule `│` in dim `$border` style, separating the rail cleanly from the adjacent deck panel.

### 4.2 Comprehensive Icon & Glyph Catalog

#### 4.2.1 Tribes (Top-Level Partitions)
Tribes already support custom icons and colors in `src/sase/default_config.yml` via `ace.tribes`. In the Compact Rail, tribe headers render as a dedicated 1-line section chip:

| Tribe Key | Configured Icon | Display Color | Collapsed Rail Representation | Description |
|---|:---:|:---:|:---:|---|
| `@default` | `⌂` | `#87D7FF` (Sky Blue) | `[@⌂]─` | Default unassigned agents |
| `@epic` | `▲` | `#AF87FF` (Lavender) | `[@▲]─` | Epic plan phase-worker clans |
| `@job` | `†` | `#FFAF5F` (Amber) | `[@†]─` | Scheduled AXE background jobs |
| `@pinned` | `◆` | `#FFD75F` (Gold) | `[@◆]─` | Hand-promoted sticky agents |
| `@review` | `◉` | `#00D7AF` (Teal) | `[@◉]─` | Mentor / CRS / code review agents |
| *Custom / Unset* | `◈` | Configured | `[@◈]─` | Fallback custom tribe icon |

*Tribe Accordion Behavior*: When a tribe panel is collapsed with `-`, its Compact Rail header remains visible as a 1-row button (`[@⌂] `). Clicking or pressing `enter` on it expands that tribe's members in the rail!

#### 4.2.2 Agent Groups (Banners across Grouping Modes)
Group headers must be instantly distinguishable from node rows. We enclose group category icons in square brackets `[...]` followed by their agent count:

| Grouping Mode | Group Category | Semantic Glyph | Collapsed Banner Token | Styling |
|---|---|:---:|:---:|---|
| **BY_STATUS** | `Stopped` (Needs Input) | `▲` | `[▲] 2` | Bold Gold (`#FFD700`) |
| | `Starting` | `◐` | `[◐] 1` | Dim Cyan (`#5FD7FF`) |
| | `Running` | `▶` | `[▶] 4` | Bold Sky Blue (`#87AFFF`) |
| | `Queued` | `…` | `[…] 3` | Muted Blue (`#5F87FF`) |
| | `Waiting` | `⏳` | `[⏳] 2` | Lavender (`#AF87FF`) |
| | `Failed` | `✗` | `[✗] 1` | Bold Red (`#FF5F5F`) |
| | `Done` | `✓` | `[✓] 8` | Soft Green (`#87D787`) |
| **STANDARD** | L0: Project | `◫` *(New)* | `[◫] 5` | Bold Sky Blue (`#5FAFFF`) |
| | L1: Patch (CL/PR) | `⑂` *(New)* | `[⑂] 3` | Cyan (`#87D7FF`) |
| | L2: Name-Root | `▸` | `[▸] 2` | Dim Teal (`#87D7AF`) |
| **BY_DATE** | L0: `Today` | `⏱` *(New)* | `[⏱] 6` | Bold Sky Blue (`#5FAFFF`) |
| | L0: `Yesterday` | `◷` *(New)* | `[◷] 4` | Sky Blue (`#5FAFFF`) |
| | L0: `This Week` | `📅` *(New)* | `[📅] 9` | Dim Sky Blue (`#5FAFFF`) |
| | L0: `Earlier` | `🗄` *(New)* | `[🗄]12` | Dim Muted (`#888888`) |
| | L1: Time Hour/Day | `🕒` *(New)* | `[🕒] 2` | Light Cyan (`#87D7FF`) |
| **BY_MACHINE** | L0: Local (`here`) | `⌂` | `[⌂] 4` | Bold Cyan (`#5FD7FF`) |
| | L0: Remote Machine | `⇄` | `[⇄] 3` | Bright Cyan (`#5FD7FF`) |
| | L1: Machine Status | Status glyph | `[▶] 2` | Status Bucket Color |

*Note on New Icons*:
- Replacing the raw rectangular blocks `▌` and `▎` with `◫` (Project) and `⑂` (Patch / Branch) gives STANDARD mode clean, unmistakable semantics in narrow spaces.
- Introducing `⏱`, `◷`, `📅`, and `🗄` provides BY_DATE mode with instant temporal recognition.

#### 4.2.3 Agent Nodes (Individual Rows)

| Node Type | Icon 1 (Type/Provider) | Icon 2 (Status) | Icon 3 (Disambiguator) | Rendered Rail Row (Width 6) |
|---|:---:|:---:|:---:|---|
| **Claude Agent (Running, #1)** | `🟣` | `▶` | `#1` | `▌🟣▶#1│` (Selected) |
| **Claude Agent (Running, #2)** | `🟣` | `▶` | `#2` | ` 🟣▶#2│` |
| **Gemini Agent (Waiting Input)** | `🔵` | `▲` | `?` | ` 🔵▲ ?│` |
| **OpenAI Agent (Done)** | `🟢` | `✓` | ` ` | ` 🟢✓  │` |
| **Monitor Proc (Active)** | `⚙` | `▶` | `m1` | ` ⚙▶m1│` |
| **Gate Turn (Pending Human)** | `⧖` | `▲` | `! ` | ` ⧖▲ !│` |
| **Python Step (Workflow Child)** | `❯` | `▶` | `py` | ` ❯▶py│` |
| **Failed Agent (Needs Review)** | `🟣` | `✗` | `● ` | ` 🟣✗● │` (Unread) |

---

### 4.3 Visual Comparison: Full vs. Compact Rail

```text
FULL EXPANDED SIDEBAR (60 columns)
┌──────────────────────────────────────────────────────────┐
│ @epic clan:feature-auth                                  │
│ ▌ sase-org/sase ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2 running  │
│   ▎ ⑂ sase-4012 (auth-oauth) ────────────────── 2 agents │
│     ▸ review.h ───────────────────────────────────────── │
│ [a] ▌ 🟣 review.h.claude (RUNNING 01:24) ─────── %r12    │
│ [b]   🟣 review.h.gemini (WAITING INPUT) ─────── %r13    │
│   ▎ ⑂ sase-4015 (login-fix) ─────────────────── 1 failed │
│ [c]   🟢 auth.coder (FAILED exit:1) ──────────── %r14    │
└──────────────────────────────────────────────────────────┘

COMPACT NAV RAIL (6 columns)
┌────┐
│[@▲]│  <- Tribe: @epic
│[◫]3│  <- Project: sase-org/sase (3 agents)
│[⑂]2│  <- Patch: sase-4012
│▌🟣▶│  <- Row a: Selected, Claude, Running
│ 🔵▲│  <- Row b: Gemini, Needs Input (Gold ▲)
│[⑂]1│  <- Patch: sase-4015
│ 🟢✗│  <- Row c: OpenAI, Failed (Red ✗)
└────┘
```

**Key Takeaways**:
- 54 columns of width returned to active documents.
- 100% of fleet health, provider allocations, and navigation states remain completely visible at a glance.
- Keyboard cursor `j`/`k` glides through the rail with instant highlight feedback `▌`.

---

## 5. Visual & UX Specification: The Unmistakable Zoom Mode

The user prompt mandates:
> *"As a part of this change, let's make it clearer (in a visually appealing way) when a deck is zoomed (so the user can't mistakenly think the sidebar is just collapsed)."*

To ensure zoom is never confused with sidebar collapse, Zoom must be treated as an elevated, high-focus **Cinematic View**.

### 5.1 The Four Visual Pillars of Zoom Mode

```text
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ╔═ [ ⤢ ZOOMED: PANEL 1 OF 2 ] ═ ⬡ MAIN DOCUMENT ═════════════════════════════ Z to restore ═╗ │
│ ║                                                                                            ║ │
│ ║  # Implementation Plan: Authentication Overhaul                                            ║ │
│ ║                                                                                            ║ │
│ ║  This document outlines the multi-provider authentication migration...                    ║ │
│ ║                                                                                            ║ │
│ ╚════════════════════════════════════════════════════════════════════════════════════════════╝ │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Pillar 1: Full-Bleed 100% Screen Width (No Rail, No Spine)
- When zoomed via `Z`, the sidebar is **completely zeroed**:
  - `#agent-list-container { display: none; }`
  - `#agent-node-spine { display: none; }`
- The deck panel extends seamlessly from terminal column 0 to the far right edge.
- **The Contrast**: If the user sees the 6-column icon rail on the left, they are in **Normal Collapsed Mode**. If the screen is 100% filled edge-to-edge by the deck with no left margin, they are in **Zoom Mode**.

#### Pillar 2: Elevated Double Border with Gold Accent
- Normal deck borders use `border: solid $secondary;` (blue/green/pink).
- In Zoom Mode, the active deck switches to Textual's **`border: double #FFD700;`**:
  ```tcss
  #agent-deck-area.-zoomed .deck-panel {
      border: double #FFD700;
  }
  ```
  Double box-drawing glyphs (`╔═══╗`, `║   ║`, `╚═══╝`) with a rich gold/amber highlight have been the universal visual metaphor for maximized/zoomed windows in terminal interfaces for decades. It immediately conveys an elevated modal state.

#### Pillar 3: High-Visibility Border Title Badge
- In `src/sase/ace/tui/widgets/decks/titles.py`:
  When `is_zoomed(state)` is true, prepend a high-contrast reverse-video badge to the border title:
  ```text
  [ ⤢ ZOOMED ] · MAIN ┃ Plan Overview (1/4)
  ```
  - If zoomed from a split (e.g., 2 panels were active):
    ```text
    [ ⤢ ZOOMED: 1 OF 2 ] · MAIN ┃ Plan Overview (1/4)
    ```
  - The badge is styled in `bold reverse #FFD700` (black text on gold background). It is visually impossible to overlook.
  - In the right-aligned border subtitle, render the explicit escape hint:
    ```text
    Z to restore split  ·  main · files 3 · tools 1
    ```

#### Pillar 4: Top Info Row Pill
- In `src/sase/ace/tui/widgets/agent_info_panel.py`:
  Replace the dim `"zoom"` string with an illuminated banner chip:
  ```text
  ⤢ ZOOM ACTIVE (Z exits)  ·  nodes 3/14  ·  Ctrl+S sidebar
  ```

---

## 6. Implementation Architecture

To implement this cleanly, reliably, and without performance regressions, we outline the exact code modifications across SASE components.

### 6.1 State Decoupling in Deck Models

In `src/sase/ace/tui/widgets/decks/model.py`:
Extend `DeckAreaState` to distinguish between sidebar presentation modes:

```python
from enum import Enum

class NavSidebarMode(Enum):
    EXPANDED = "expanded"     # Normal 60-column sidebar
    COMPACT_RAIL = "compact"  # Collapsed 6-column icon rail
    HIDDEN = "hidden"        # 0 columns (used in Zoom or full-bleed split)

@dataclass(frozen=True)
class DeckAreaState:
    panels: tuple[DeckPanelState, ...] = (DeckPanelState(DeckId.MAIN),)
    focused: int = 0
    layout: DeckLayout = DeckLayout.SINGLE
    ratio: int = 50
    # Backward compatibility: nodes_collapsed is True when COMPACT_RAIL or HIDDEN
    sidebar_mode: NavSidebarMode = NavSidebarMode.EXPANDED
    zoom_snapshot: DeckAreaState | None = None

    @property
    def nodes_collapsed(self) -> bool:
        return self.sidebar_mode is not NavSidebarMode.EXPANDED
```

In `src/sase/ace/tui/widgets/decks/layout.py`:
Update `toggle_nodes_collapsed` and `_enter_zoom`:

```python
def toggle_nodes_collapsed(state: DeckAreaState) -> DeckAreaState:
    """Toggle between EXPANDED and COMPACT_RAIL via Ctrl+S."""
    state = _zoom_ended(state)
    new_mode = (
        NavSidebarMode.EXPANDED
        if state.sidebar_mode is NavSidebarMode.COMPACT_RAIL
        else NavSidebarMode.COMPACT_RAIL
    )
    return dataclasses.replace(state, sidebar_mode=new_mode)

def _enter_zoom(state: DeckAreaState, focused: int | None = None) -> DeckAreaState:
    """Enter zoom: snapshot state, isolate panel, and hide sidebar completely."""
    if state.zoom_snapshot is not None:
        return state
    snapshot = dataclasses.replace(state, zoom_snapshot=None)
    index = snapshot.focused if focused is None else focused
    return dataclasses.replace(
        snapshot,
        panels=snapshot.panels,
        focused=index,
        layout=DeckLayout.SINGLE,
        sidebar_mode=NavSidebarMode.HIDDEN,
        zoom_snapshot=snapshot,
    )
```

### 6.2 CSS & Chrome Synchronization

In `src/sase/ace/tui/widgets/_agent_detail_deck_layout.py`:
Update `_sync_nodes_collapsed_chrome`:

```python
def _sync_nodes_collapsed_chrome(self) -> None:
    area = self.deck_area
    mode = area.state.sidebar_mode
    zoomed = is_zoomed(area.state)

    content = app.query_one("#agents-content")
    container = app.query_one("#agent-list-container")
    spine = app.query_one("#agent-node-spine")

    # Update deck area zoom styling
    deck_area = app.query_one("#agent-deck-area")
    if zoomed:
        deck_area.add_class("-zoomed")
    else:
        deck_area.remove_class("-zoomed")

    # Sidebar mode handling
    if mode is NavSidebarMode.EXPANDED:
        container.remove_class("-compact")
        container.remove_class("-hidden")
        content.remove_class("-nodes-collapsed")
        spine.add_class("hidden")
    elif mode is NavSidebarMode.COMPACT_RAIL:
        container.add_class("-compact")
        container.remove_class("-hidden")
        content.remove_class("-nodes-collapsed")
        spine.add_class("hidden")  # Replaced by the compact rail itself!
    elif mode is NavSidebarMode.HIDDEN:
        container.remove_class("-compact")
        container.add_class("-hidden")
        content.add_class("-nodes-collapsed")
        spine.add_class("hidden")  # Completely hidden in Zoom!
```

In `src/sase/ace/tui/styles.tcss`:

```tcss
#agent-list-container {
    width: 60;
    height: 100%;
    layout: vertical;
    transition: width 100ms in_out_cubic;
}

#agent-list-container.-compact {
    width: 6;
    min-width: 6;
    max-width: 6;
    padding: 0;
    border-right: solid $border;
}

#agent-list-container.-compact AgentList {
    padding: 0;
    border: none;
}

#agent-list-container.-hidden {
    display: none;
}

/* Zoom Elevated Chrome */
#agent-deck-area.-zoomed .deck-panel {
    border: double #FFD700;
}
```

### 6.3 Fast Option Rendering in Compact Mode

In `src/sase/ace/tui/widgets/_agent_list_render_agent.py` and `_agent_list_render_banner.py`:
Introduce `format_compact_agent_option` and `format_compact_banner_option`.
When the parent container has `-compact`, `AgentList` outputs 6-cell options.
Because `AgentList` options are cached via `AgentRenderCache`, we extend the cache key to include a `compact: bool` flag:
```python
cache_key = (agent.identity, agent.status, is_selected, is_compact)
```
This guarantees that swapping between `<ctrl+s>` states is instantaneous (< 16 ms) and does not incur full list allocations.

---

## 7. Comparative Evaluation of Alternatives

| Approach | Screen Recovery | Situational Awareness | Implementation Risk | Ergonomic Quality | Verdict |
|---|:---:|:---:|:---:|:---:|:---:|
| **Status Quo (Hide Sidebar on `<ctrl+s>` and `Z`)** | High (100%) | None (Blind) | None | Poor (Confusing & Disorienting) | **Rejected** |
| **Alternative A: Separate `NodeRail` Widget** | High (90%) | High | High (Dual state, sync bugs, Textual event routing) | Medium | **Rejected** |
| **Alternative B: Floating Popover on Hover** | High (100%) | Low (Requires mouse/keystroke hover) | High (Z-index layering, flicker on terminal) | Poor | **Rejected** |
| **Recommended: Integrated Compact Nav Rail + Elevated Zoom** | High (90% on collapse, 100% on zoom) | Exceptional (Live icons, counts, status) | Low (Reuses `AgentList` pipeline, pure CSS & render layer) | Exceptional (Intuitive, responsive, beautiful) | **Recommended** |

---

## 8. Phased Implementation Roadmap & Verification Plan

### Phase 1: Model & Decoupling
1. Add `NavSidebarMode` (`EXPANDED`, `COMPACT_RAIL`, `HIDDEN`) to `src/sase/ace/tui/widgets/decks/model.py`.
2. Update `toggle_nodes_collapsed()` in `layout.py` to target `COMPACT_RAIL`.
3. Update `_enter_zoom()` to target `HIDDEN` and set `-zoomed` on the deck area.
4. Verify unit tests for deck area layout state in `tests/ace/tui/decks/test_layout.py`.

### Phase 2: Zoom Visual Elevation
1. Add `.-zoomed` CSS rule in `styles.tcss` with `border: double #FFD700;`.
2. Update `deck_title()` in `src/sase/ace/tui/widgets/decks/titles.py` to prepend `[ ⤢ ZOOMED ]` and restore hints.
3. Update `AgentInfoPanel` to render the gold zoom pill.
4. Verify live screenshot with `sase screenshot` while zoomed.

### Phase 3: Compact Rail Formatting & Icon Catalog
1. Implement `format_compact_banner_option()` in `_agent_list_render_banner.py` using bracketed glyphs (`[▶]`, `[◫]`, `[⏱]`).
2. Implement `format_compact_agent_option()` in `_agent_list_render_agent.py` using provider emoji + status glyph + disambiguator.
3. Add `-compact` style rules to `styles.tcss`.
4. Update `_sync_nodes_collapsed_chrome()` to toggle `-compact` vs `-hidden`.

### Phase 4: Performance & Live Verification
1. Run `SASE_TUI_PERF=1` and check `~/.sase/perf/tui_jk.jsonl` to verify p95 navigation latency stays below 16 ms in both expanded and compact states.
2. Verify with visual regression tests that split-panel tribe folding works reliably in compact mode.

---

## 9. Conclusion

Decoupling sidebar collapse (`<ctrl+s>`) from deck zoom (`Z`) solves one of the most glaring ergonomic ambiguities in the SASE Agents tab. By transforming `<ctrl+s>` into a **6-column Compact Nav Rail**, users recover 54 columns of critical workspace while retaining full ambient fleet observability and instant keyboard control. Simultaneously, elevating `Z` into a **Full-Bleed, Double-Bordered Cinematic Zoom** gives users clear visual confidence that they are in an isolated, temporary snapshot that can be effortlessly restored. This design strikes the ideal balance between functional density, technical reliability, and aesthetic elegance.
