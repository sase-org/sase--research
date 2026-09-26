# Research Report: Deck and Card Spread vs. Paged View UX & Keymap Design

**Researcher**: `gem` (Swarm ID: `research.2l.gem`)  
**Context**: Epic `sase-19x` (Agent data card blocks), SASE ACE TUI  
**Date**: September 2026  
**Target Path**: `sase/repos/research/202609/deck_and_card_spread_paged_toggle_ux__gem.md`  

---

## 1. Executive Summary & Core Recommendations

In SASE's ACE TUI (Agents tab), the display architecture is organized in a three-tier hierarchy: **Deck → Card → Block**. With the introduction of card blocks for session Reply cards (epic `sase-19x`), cards no longer represent the atomic unit of content. Instead, large cards (specifically agent session Replies) are partitioned into shell-level card blocks (`AGENT`, `MONITOR`, `GATE`).

This introduces two distinct layout axes:
1. **Deck Presentation Axis**: Whether all cards in the deck are rendered concatenated on a single scrollable canvas (**Deck Spread**) or isolated to a single active card (**Deck Paged**).
2. **Card Block Presentation Axis**: When a card is shown alone in a paged deck, whether all of its card blocks are rendered inline on one scrollable canvas (**Block Spread**) or partitioned into single-shell pages (**Block Paged**).

Currently, both axes are decided automatically via viewport height heuristics (`spread_max_screens` and `block_spread_max_screens`, both defaulting to 1.5). However, users lack two critical capabilities:
- **Visual Transparency**: It is difficult or impossible to tell at a glance whether the current view is spread or paged at the deck or card level, and the one-row block rail looks visually identical regardless of whether `[` / `]` flips pages or scrolls to headers.
- **Direct Control**: Users cannot manually toggle between viewing density states to inspect full histories or isolate specific execution phases.

### Summary of Recommendations

1. **The 3-State Model**:
   Formalize the three coherent display states as a linear **Information Density Ladder**:
   - **State 1: Fully Spread** (`DECK_SPREAD`): All cards concatenated inline; all card blocks inline; block rail hidden.
   - **State 2: Paged Deck, Spread Card** (`CARD_SPREAD`): Active card shown alone; all blocks within that card rendered inline; block rail visible as a scroll/anchor timeline.
   - **State 3: Paged Deck, Paged Card** (`CARD_PAGED`): Active card shown alone; only the active block rendered; block rail visible as a page-flip timeline.
   *(Note: The theoretical fourth permutation—Deck Spread with Paged Card—is architecturally and visually invalid in a unified document scroll container and is rejected.)*

2. **Visual Clarity Improvements (Multi-Surface Clarity)**:
   - **Deck Subtitle (Bottom Border)**: Replace the current binary `spread` tag with an explicit, tiered view-mode badge: `spread` (State 1), `card-spread` (State 2), and `paged` (State 3).
   - **Deck Title (Top Border)**: When in State 1 (Fully Spread), replace the misleading active tab counter (e.g., `3/3`) with an explicit `all 3` or `spread` chip, making it immediately obvious that cards are concatenated.
   - **Block Rail (Timeline)**: In the right-hand hint area (and compact badges), explicitly distinguish navigation modes: show `[ / ] page` in Block-Paged mode versus `[ / ] scroll` in Block-Spread mode, accompanied by subtle mode glyphs (`⧉` for paged, `≡` for spread).
   - **Transient Feedback**: Fire a brief, low-overhead TUI toast notification (`self.notify("Deck view: Paged deck, spread card")`) whenever the state is toggled.

3. **Keymap Ergonomics**:
   - **Primary Action**: Add `cycle_deck_card_view` bound by default to **`P`** (`Shift+p`).
     - **Rationale**: In `default_config.yml`, `P` is completely unbound at the app level. It forms a natural conceptual pair with `p` (`pick_deck`): lowercase `p` picks *which* deck to show; uppercase `P` toggles *how* the deck and cards are presented. It is 100% terminal/tmux safe (standard ASCII 80).
   - **Reverse Cycle**: Add `cycle_deck_card_view_reverse` bound to **`g P`** or available via custom remapping.
   - **Leader Mode Shortcut**: Add `,s` (or `,v`) under `ace.keymaps.leader_mode.keys.view_mode` for users who prefer two-key mnemonic sequences.
   - **Deck Picker Modal Integration**: Add a direct toggle hint/key (e.g., `Tab` or `s`) inside the `p` (`pick_deck`) modal so deck selection and layout mode can be adjusted in one place.

---

## 2. Background and Technical Context (`sase-19x`)

### 2.1 The ACE Deck and Card Hierarchy

The ACE TUI detail pane hosts three deck panels:
- **`MAIN`**: Contains the primary agent session context, prompt, and replies.
- **`FILES`**: Displays modified files, unified diffs, and touched artifacts.
- **`TOOLS`**: Displays the timeline of tool calls and command invocations.

Within the `MAIN` deck, content is partitioned into **Cards**:
- `Context`: Task specifications, agent specs, environment data.
- `Prompt`: User prompt and injected xprompt content.
- `Reply`: Agent execution transcripts, tool outputs, thinking phases, and final answers.

### 2.2 The Introduction of Card Blocks (`sase-19x`)

Prior to `sase-19x`, the `Reply` card was rendered as one monolithic vertical document. In long multi-turn agent sessions or sessions involving subagents, monitors, and gates, this card could extend thousands of lines.

Epic `sase-19x` divides the `Reply` card into **Card Blocks**:
- Each concrete sase shell (`AGENT (code)`, `⚙ MONITOR`, `⋔ GATE`) becomes a distinct `CardBlock` carrying metadata (`BlockMeta`: sequence index, role label, status bucket, accent color, and shell identity).
- Navigation between blocks is enabled via `[` (`prev_card_block`) and `]` (`next_card_block`).
- A dedicated **Block Rail** widget (`BlockRail`) is composed directly below the panel's top border to display a horizontal timeline of shells with an active pill indicator, status glyphs, and arrival dots for streaming updates.

### 2.3 Current Automatic Decision Logic

Layout rendering currently relies on two pure decision functions:
1. `decide_render_mode` (`render_mode.py`):
   - Computes total rendered height across all cards in the deck.
   - If `total_rows <= spread_max_screens * viewport_rows`, the deck renders as `RenderMode.SPREAD`.
   - Otherwise, the deck renders as `RenderMode.PAGED`.
   - Includes a 10% hysteresis buffer (`SPREAD_HYSTERESIS = 0.10`) to prevent oscillation during content streaming.
2. `decide_block_mode` (`block_model.py` / `panel_blocks.py`):
   - Applied only when a card with $\ge 2$ blocks is **shown alone** in a paged deck.
   - If `card_rows <= block_spread_max_screens * viewport_rows`, the card renders as `RenderMode.SPREAD` (block-spread).
   - Otherwise, it renders as `RenderMode.PAGED` (block-paged).
   - If a card has $< 2$ blocks, it unconditionally spreads.

---

## 3. Analysis of the 3 States: The Information Density Ladder

When considering both axes, there are mathematically $2 \times 2 = 4$ permutations. However, user experience and document layout constraints reduce these to **3 valid states**.

```
[Level 1: Deck Overview]      State 1: Fully Spread (Deck Spread)
        │                     - Continuous canvas of Context, Prompt, Reply
        │                     - All blocks rendered inline
        ▼
[Level 2: Card Isolation]     State 2: Paged Deck, Spread Card
        │                     - Only one card shown (e.g., Reply alone)
        │                     - All blocks rendered inline
        ▼
[Level 3: Block Isolation]    State 3: Paged Deck, Paged Card
                              - Only one card shown
                              - Only one block/shell rendered per page
```

### 3.1 State Breakdown

| State | Deck Mode | Card Block Mode | What the Viewport Renders | Block Rail Status |
| :--- | :--- | :--- | :--- | :--- |
| **1. Fully Spread** | `SPREAD` | `SPREAD` (inline) | Every card (`Context`, `Prompt`, `Reply`) separated by heavy `━━ ◆ Reply ━━` rules. All shells inline. | **Hidden** (phase dividers `─── AGENT ───` suffice). |
| **2. Paged Deck, Spread Card** | `PAGED` | `SPREAD` (inline) | Only the active card. All blocks in that card are laid out continuously. | **Shown** (acts as a scroll/anchor timeline). |
| **3. Paged Deck, Paged Card** | `PAGED` | `PAGED` | Only the active card, and only the active block within that card. | **Shown** (acts as a page-flip timeline). |

### 3.2 Why the Fourth Permutation ("Deck Spread, Card Paged") Is Invalid

Could a deck be spread while a card inside it is block-paged?
- **Layout Inconsistency**: In `MainDeckView`, a spread deck is compiled into a single unified Rich `Group` composed of all cards, wrapped in one `VerticalScroll`. If one card in the middle of this document were "paged", scrolling past it would either display an arbitrary slice of the card or require intra-document paging widgets inside a continuous scroll canvas.
- **Scroll Invariants**: Spread mode relies on stable row offsets (`card_anchor_rows`). Flipping a block page inside an inline card would cause the entire document below it to jump unpredictably.
- **Mental Model Collision**: "Spread" at the deck level means *"show me everything concatenated"*. Paging a card's inner content contradicts that contract.

Therefore, the system operates on a coherent 3-state ladder. Cycling through these states represents zooming in or zooming out along an information density continuum.

---

## 4. UX Improvement 1: Making Spread vs. Paged View Clear

### 4.1 Current Deficiencies in Visual Feedback

1. **Asymmetric Subtitle Tag**:
   - `titles.py` sets `spread_tag = Text("spread", style="dim") if spread else None`.
   - When the deck is spread, the dim word `spread` appears in the bottom subtitle.
   - When the deck is paged, **nothing** appears. The user cannot tell whether paging is active or whether the deck simply has only one card.
2. **Narrow Viewport Fragility**:
   - In `deck_subtitle`, candidate tiers drop `spread_tag` before dropping the deck switcher. On split panels (`|` or `\`), the word `spread` is frequently dropped due to width budgeting.
3. **Total Block-Mode Invisibility**:
   - Neither the top border title nor the bottom border subtitle provides any indication of whether a card is block-spread or block-paged.
   - The Block Rail displays identical pills (`▐ 0 --plan ✓ ▌ ─ 1 --mon-0 ▶`) in both modes.
   - The user has no way of knowing whether pressing `[` / `]` will jump the scroll position down a long page (block-spread) or swap the visible page instantly (block-paged) until they actually press the key.

### 4.2 Comparative Evaluation of Indicator Placement

We evaluated five potential TUI surfaces for communicating view state:

| Surface | Pros | Cons | Verdict |
| :--- | :--- | :--- | :--- |
| **A. Deck Subtitle (Bottom Border)** | Established location for `spread`; plenty of horizontal space in single-panel layouts. | Hidden or truncated in narrow splits; bottom border is peripheral to user focus. | **Essential for Deck Mode**: Upgrade to explicit tri-state labels. |
| **B. Deck Title (Top Border)** | Primary focal point; rendered in panel accent; immediately visible on entry. | Card tab strip is horizontally constrained when multiple cards exist. | **Targeted Indicator**: Clarify spread decks by showing `all 3` instead of `3/3`. |
| **C. Block Rail (Timeline)** | Located directly where block navigation occurs; visible only when blocks exist. | Rail is hidden in State 1 (Fully Spread). | **Essential for Card Mode**: Add `page` vs `scroll` hint and glyphs (`⧉` vs `≡`). |
| **D. App Footer** | Global visibility; shows current key bindings. | Disjoint from the specific deck panel (especially in dual-panel splits). | **Secondary**: Include `P view` hint when Agents tab is active. |
| **E. Notification Toasts** | Immediate, unambiguous feedback right when the user acts. | Transient (disappears after 2-3 seconds). | **Essential Action Feedback**: Fire on every keymap toggle. |

### 4.3 Proposed Visual Design Specification

#### 1. Deck Subtitle (Bottom Border)
Update `deck_subtitle()` in `src/sase/ace/tui/widgets/decks/titles.py` to accept the comprehensive view mode:
- **State 1 (Fully Spread)**: `Text("spread", style="dim")` (or `deck-spread`)
- **State 2 (Paged Deck, Spread Card)**: `Text("card-spread", style="dim")`
- **State 3 (Paged Deck, Paged Card)**: `Text("paged", style="dim")` (or `card-paged`)
- **Cards without blocks (Context, Prompt)** in paged deck: `Text("paged", style="dim")`

When width allows, render as:
`◆ MAIN  ·  spread  ·  main · files · tools`
`◆ MAIN  ·  card-spread  ·  main · files · tools`
`◆ MAIN  ·  paged  ·  main · files · tools`

#### 2. Deck Title Strip (Top Border)
In `deck_title()` (`titles.py`), when the deck is in **State 1 (Fully Spread)**:
- Currently, `_build_full()` appends `active_index + 1 / len(tabs)` (e.g. `3/3`). This falsely implies that only card 3 is active.
- Instead, render: `all 3` or `spread 3`:
  `◆ MAIN ┃ [Context] │ [Prompt] │ [Reply]  all 3`
- In States 2 and 3 (Deck Paged), keep the traditional active counter:
  `◆ MAIN ┃ Context │ Prompt │ [Reply]  3/3`

#### 3. Block Rail Mode Indicators
In `src/sase/ace/tui/widgets/decks/block_rail.py`, enhance the right-hand key hint and compact tiers:
- **In State 3 (Block-Paged)**:
  - At the `full-hint` tier: render `[ / ] page` (or `⧉ [ / ]`) at the right edge in `#888888`.
  - In `compact` and `windowed` tiers: render a small badge `⧉` (paged icon) next to the active pill.
- **In State 2 (Block-Spread)**:
  - At the `full-hint` tier: render `[ / ] scroll` (or `≡ [ / ]`) at the right edge.
  - In `compact` and `windowed` tiers: render a small badge `≡` (spread/flow icon) next to the active pill.

This gives the user an instantaneous visual anchor: they know before pressing `[` or `]` whether the screen will page or scroll.

---

## 5. UX Improvement 2: Keymap Design and Ergonomics

### 5.1 Analysis of Candidate Keybindings

The user requested: *"one or more new keymaps that allow the user to toggle through the 3 states (fully spread, paged deck and spread card, paged deck and paged card)"*.

We audited the entire keymap namespace in `src/sase/default_config.yml` and `registry.py` across all tabs and scopes.

#### Key Availability Audit

| Candidate Key | Current Bindings in `app:` | Current Bindings in Agents Tab | Evaluation / Safety |
| :---: | :--- | :--- | :--- |
| **`P`** (`Shift+p`) | **Unbound** | **Unbound** | **Outstanding**. Pairs with `p` (`pick_deck`). 100% terminal/tmux safe. Zero collision risk. |
| **`z`** | `start_fold_mode` (Agents), `beads_snooze`, `files_cycle_kind` | Bound to fold mode on Agents tab | **Collision**. Using `z` would break fold mode or require nested modal chords. |
| **`Z`** (`Shift+z`) | `zoom_panel`, `files_open_viewer` | Bound to panel zoom on Agents tab | **Collision**. Already performs panel zoom/unzoom. |
| **`s`** / **`S`** | `save_marked_agents` (`s`), `bulk_change_status` (`S`) | Heavily bound on Agents tab | **Collision**. Core agent selection/status actions. |
| **`v`** / **`V`** | `view_files` (`v`), `view_agent_metadata` (`V`) | Bound on Agents tab | **Collision**. Opens file viewer or metadata pager. |
| **`ctrl+e`** | **Unbound** | **Unbound** | **Viable Chord**. Mnemonic for "Expand/Expose". However, ctrl chords are slower than single keystrokes. |
| **`\`** / **`\|`** | `toggle_deck_split_below` (`\`), `toggle_deck_split_right` (`\|`) | Bound to deck panel splitting | **Keep Intact**. Belongs to panel layout rather than content density. |
| **`,s`** | **Unbound** in `leader_mode` | **Unbound** | **Ideal Secondary**. High discoverability; two-key mnemonic (`leader` + `spread`). |

### 5.2 Keymap Structural Patterns: Single Cycle vs. Separate Toggles

We evaluated three interaction patterns for the keymap:

#### Pattern A: Single Tri-State Cycle Key (`P`) [RECOMMENDED]
Pressing `P` advances cyclically through the ladder:
$$\text{Fully Spread (1)} \xrightarrow{\mathbf{P}} \text{Paged Deck, Spread Card (2)} \xrightarrow{\mathbf{P}} \text{Paged Deck, Paged Card (3)} \xrightarrow{\mathbf{P}} \text{Fully Spread (1)}$$
- **Pros**:
  - Requires only one key binding (`P`).
  - Perfect conceptual model: progressively zooms in from macroscopic overview to isolated execution unit, then wraps.
  - Matches user workflow: users typically switch between "read the whole transcript" (Spread) and "focus on the current shell" (Paged).
- **Cons**: Stepping backwards from State 3 to State 2 requires two presses unless a reverse key is provided.

#### Pattern B: Bidirectional Stepping (`P` / `Shift+P` or `[` / `]`)
- Forward cycle with `P` (1 → 2 → 3), reverse cycle with another key (e.g. `g P` or `Alt+P`).
- Since `P` is already shifted, reverse could be bound to `cycle_deck_card_view_reverse` in configuration.

#### Pattern C: Two Independent Toggles (`toggle_deck_spread` & `toggle_card_spread`)
- Key 1 toggles Deck Spread ↔ Paged.
- Key 2 toggles Card Block Spread ↔ Paged.
- **Why this fails**:
  - Violates state independence. If the deck is in Deck Spread mode, toggling Card Block mode to Paged is illegal. The key would either be a silent no-op (confusing) or force the deck into Paged mode (surprising side effect).
  - Consumes two separate key bindings in an already constrained namespace.

### 5.3 Recommendation: Primary Key `P` + Leader Shortcut `,s`

1. **Default App Keymap**:
   ```yaml
   ace:
     keymaps:
       app:
         cycle_deck_card_view: "P"
   ```
2. **Leader Mode Shortcut**:
   ```yaml
   ace:
     keymaps:
       leader_mode:
         keys:
           view_mode: "s"  # Activated via `,s`
   ```
3. **Behavior on Trigger**:
   - Computes next state in the 3-state cycle.
   - Applies the mode transition using `panel_transitions.py` reading anchors.
   - Emits a Textual notification toast:
     - State 1: `self.notify("Deck view: Fully spread")`
     - State 2: `self.notify("Deck view: Paged deck, spread card")`
     - State 3: `self.notify("Deck view: Paged deck, paged card")`
   - Refreshes panel chrome and block rail.

---

## 6. State Lifecycle, Edge Cases, and Auto-Hysteresis

### 6.1 Ephemeral vs. Persistent State

How should manual view-mode choices persist?
1. **Panel-Local Stickiness**:
   - In ACE, `DeckPanelState` already retains `preferred_card` across agent switches (`j`/`k`).
   - The user's manual view mode override should attach to the focused `DeckPanel` instance (e.g., `_view_mode_override: DeckCardViewMode`).
   - If a user sets Panel 0 to "Fully Spread" and Panel 1 to "Paged Card" in a split, each panel retains its setting independently as the user navigates agents.
2. **Interaction with Automatic Sizing (The "Auto" State)**:
   - By default, upon launching ACE, the view mode starts in `AUTO` (driven by `spread_max_screens` and `block_spread_max_screens`).
   - When the user presses `P`:
     - The current effective mode is resolved (e.g., if auto resolved to Fully Spread).
     - The manual override steps to the *next* state (State 2: Paged Deck, Spread Card).
     - The panel is now in a manual override state, immune to automatic screen budget recalculations during window resizing or streaming.
   - **Resetting to Auto**:
     - Users can reset to `AUTO` via leader mode (`,S` or `,a`) or a command palette action (`deck-view:reset-auto`).
     - Alternatively, config option `ace.agent_decks.default_view_mode` can allow users to set a preferred fixed default (`auto`, `fully_spread`, `card_spread`, `card_paged`).

### 6.2 Handling Cards Without Blocks

What happens when the focused card has $< 2$ blocks (e.g., `Context` or `Prompt` cards, or a single-turn agent reply)?
- **Card-level Reality**: For a card without blocks, State 2 (Paged Deck, Spread Card) and State 3 (Paged Deck, Paged Card) render the exact same content: the full card.
- **UX Dilemma**: Should pressing `P` on the `Context` card cycle 1 → 2 → 3 → 1, or should it skip State 3?
- **Recommended Handling**:
  - **Do NOT skip State 3**. The view mode is a **panel-level presentation contract**, not a temporary card property.
  - If the user is on the `Context` card and presses `P` to set `card_paged`, the subtitle displays `paged`. When the user subsequent cycles to `Reply` (`Ctrl+J`), the `Reply` card immediately honors the `card_paged` setting without requiring another toggle.
  - The toast notification on `Context` can indicate: `Deck view: Paged deck (card has no blocks)` to prevent confusion.

### 6.3 Dual-Panel Splits and Unfocused Panels

When two deck panels are visible (e.g., `LEFT_RIGHT` split via `|`):
- Navigation and toggle actions apply strictly to the **focused panel** (`area.focused_panel()`).
- The unfocused panel dims its subtitle and rail pill, consistent with SASE TUI standards.
- Both panels can independently display different view modes for different decks (e.g., Panel 0 showing `MAIN` Fully Spread; Panel 1 showing `FILES` Paged).

### 6.4 Seamless Scroll and Anchor Preservation

Switching between spread and paged modes must never cause the reader to lose their place.
Epic `sase-19x` introduced `panel_transitions.py` and the `ReadingAnchor` model:
```python
@dataclass(frozen=True)
class ReadingAnchor:
    card_id: str | None
    block_id: str | None
    offset_rows: int
    pinned: bool
```
Because `ReadingAnchor` captures the specific `block_id` and line offset before recomposition, toggling between State 1, State 2, and State 3 preserves the exact shell and row position the user was reading. No new transition plumbing is needed; the toggle simply hooks into `_apply_main_transition()`.

---

## 7. Concrete Implementation Architecture & Blueprint

### 7.1 Data Model Additions (`src/sase/ace/tui/widgets/decks/model.py`)

Define the explicit view mode enum:
```python
class DeckCardViewMode(StrEnum):
    """Deck and card presentation state."""
    AUTO = "auto"
    FULLY_SPREAD = "fully_spread"       # State 1: Deck spread, cards inline, blocks inline
    CARD_SPREAD = "card_spread"         # State 2: Deck paged, active card alone, blocks inline
    CARD_PAGED = "card_paged"           # State 3: Deck paged, active card alone, blocks paged

DECK_CARD_VIEW_CYCLE: tuple[DeckCardViewMode, ...] = (
    DeckCardViewMode.FULLY_SPREAD,
    DeckCardViewMode.CARD_SPREAD,
    DeckCardViewMode.CARD_PAGED,
)

def next_deck_card_view_mode(current: DeckCardViewMode, direction: int = 1) -> DeckCardViewMode:
    """Return the next view mode in the 3-state cycle."""
    if current is DeckCardViewMode.AUTO:
        # Step from fully spread as the baseline
        return DeckCardViewMode.CARD_SPREAD if direction > 0 else DeckCardViewMode.CARD_PAGED
    idx = DECK_CARD_VIEW_CYCLE.index(current)
    return DECK_CARD_VIEW_CYCLE[(idx + direction) % len(DECK_CARD_VIEW_CYCLE)]
```

### 7.2 Chrome and Title Helpers (`src/sase/ace/tui/widgets/decks/titles.py`)

Enhance `deck_subtitle` to render the view mode badge:
```python
def deck_subtitle(
    active: DeckId,
    availability: Mapping[DeckId, object],
    *,
    status: Text | None,
    width: int,
    accent_for: Mapping[DeckId, str],
    view_mode: DeckCardViewMode = DeckCardViewMode.AUTO,
    is_spread: bool = False,
) -> Text:
    # Map view mode to concise display tag
    mode_text = None
    if view_mode is DeckCardViewMode.FULLY_SPREAD or (view_mode is DeckCardViewMode.AUTO and is_spread):
        mode_text = Text("spread", style="dim")
    elif view_mode is DeckCardViewMode.CARD_SPREAD:
        mode_text = Text("card-spread", style="dim")
    elif view_mode is DeckCardViewMode.CARD_PAGED or (view_mode is DeckCardViewMode.AUTO and not is_spread):
        mode_text = Text("paged", style="dim")

    # Include mode_text in candidate tier combinations
    ...
```

Enhance `deck_title` to render `all N` in spread mode:
```python
if is_spread and active_index is not None and len(tabs) > 1:
    text.append(f"  all {len(tabs)}", style=_MUTED)
elif active_index is not None and len(tabs) > 1:
    text.append(f"  {active_index + 1}/{len(tabs)}", style=_MUTED)
```

### 7.3 Block Rail Mode Hint (`src/sase/ace/tui/widgets/decks/block_rail.py`)

Update the key hint in `_build_full_hint`:
```python
def _build_full_hint(
    ...,
    block_mode: RenderMode = RenderMode.PAGED,
) -> Text:
    mode_label = "page" if block_mode is RenderMode.PAGED else "scroll"
    hint = f" {prev_key}/{next_key} {mode_label} "
    ...
```

### 7.4 Action Handler (`src/sase/ace/tui/actions/agents/_panel_detail.py`)

Add the action handler to `AgentPanelDetailMixin`:
```python
def action_cycle_deck_card_view(self) -> None:
    """Cycle the focused deck panel through the 3 view states (wraps)."""
    if self.current_tab != "agents":
        return
    agent_detail = self.query_one("#agent-detail-panel", AgentDetail)
    new_mode = agent_detail.cycle_focused_deck_view_mode(direction=1)
    
    # Toast descriptions
    labels = {
        DeckCardViewMode.FULLY_SPREAD: "Fully spread (all cards & blocks inline)",
        DeckCardViewMode.CARD_SPREAD: "Paged deck, spread card (card alone, blocks inline)",
        DeckCardViewMode.CARD_PAGED: "Paged deck, paged card (card alone, single block)",
    }
    self.notify(f"Deck view: {labels.get(new_mode, new_mode)}")
    self._refresh_agents_display()
```

### 7.5 Configuration Defaults (`src/sase/default_config.yml`)

1. Register the keymap under `ace.keymaps.app`:
   ```yaml
   ace:
     keymaps:
       app:
         # Deck presentation mode (spread deck -> spread card -> paged card)
         cycle_deck_card_view: "P"
   ```
2. Register the leader mode key under `ace.keymaps.leader_mode.keys`:
   ```yaml
   ace:
     keymaps:
       leader_mode:
         keys:
           view_mode: "s"
   ```
3. Add configuration setting under `ace.agent_decks`:
   ```yaml
   ace:
     agent_decks:
       # Default presentation mode for agent decks: auto, fully_spread, card_spread, or card_paged
       default_view_mode: "auto"
   ```

---

## 8. Summary Comparison of Solutions

| Dimension | Minimal Viable Approach | Recommended Solution | Complex Multi-Key Approach |
| :--- | :--- | :--- | :--- |
| **State Model** | Binary spread/paged toggle at deck level only. | **3-State Ladder**: Fully Spread → Card Spread → Card Paged. | 4-state matrix with independent toggles. |
| **Visual Indicators** | Keep existing `spread` tag in subtitle. | **Multi-surface**: Subtitle badge (`card-spread`/`paged`), Title `all N`, Rail `page`/`scroll` hint, and Toast. | Modals, heavy status banners, floating badges. |
| **Keymaps** | Leader mode only (`,s`). | **Single shifted key `P`** + Leader `,s` + toast notification. | Separate keys for deck spread, card spread, and reset (`ctrl+e`, `ctrl+w`, `ctrl+r`). |
| **Ergonomics** | 2 keystrokes; no conflicts. | **1 keystroke (`P`)**; perfectly paired with `p` (`pick_deck`). | High cognitive load; risk of invalid state collisions. |
| **Architecture** | Reuses existing `decide_render_mode`. | Reuses `panel_transitions.py` reading anchors and pure decision helpers. | Requires rewriting `MainDeckView` scroll architecture. |

---

## 9. Conclusion

Implementing the **3-State Information Density Ladder** with **`P`** as the primary cycle key and clear multi-surface indicators solves both visibility and control deficits in ACE's deck UX:

1. **Clarity**: Users are never left guessing whether a view is spread or paged. The subtitle labels the state (`spread`, `card-spread`, `paged`), the title disambiguates concatenated cards (`all 3`), and the block rail communicates whether `[` / `]` will jump scroll anchors or flip pages (`[ / ] page` vs `[ / ] scroll`).
2. **Control**: The single-key shortcut **`P`** provides frictionless, terminal-safe cycling between high-level overview and phase-isolated reading without polluting the keymap namespace or colliding with existing navigation.
3. **Robustness**: Anchored in `ReadingAnchor` from epic `sase-19x`, state transitions are instantaneous, smooth, and preserve the reader's exact scroll position across every mode switch.
