# Research: Deck and Card Spread vs Paged View UX & 3-State Toggle Keymaps

**Author:** Researcher gem (Swarm: `research.f.*`)  
**Date:** 2026-09-26  
**Context:** Epic `sase-19x` (Agent data card blocks - per-shell blocks for session Reply cards)  
**Target Bead:** Follow-up UX refinement for Agent Decks and Card Blocks  

---

## Executive Summary

Epic `sase-19x` introduced a strict three-tier presentation hierarchy to SASE Agents-tab deck panels: **Deck &rarr; Card &rarr; Block**. In this architecture, a deck (Main, Files, Tools) contains cards (e.g., Context, Reply), and an agent session's Reply card contains one card block per concrete sase shell (`0 --plan`, `1 ⋔ --gate`, `2 --code`, etc.).

Currently, presentation modes are chosen purely automatically by viewport measurement against configuration thresholds (`spread_max_screens` and `block_spread_max_screens`). While this adaptive sizing prevents runaway rendering performance hits on large sessions, it creates two major UX deficiencies:

1. **State Invisibility & Ambiguity:** Users cannot reliably discern which view state is active. In particular, a spread deck misleadingly highlights a single card tab as active in the top border; more critically, **State 2 (Paged Deck + Spread Card Blocks)** and **State 3 (Paged Deck + Paged Card Blocks)** look visually identical in the panel chrome and block rail, despite having fundamentally different scrolling and key-navigation semantics.
2. **Lack of User Agency:** Users have no mechanism to override the automatic sizing decisions. An incoming stream of shell output or a minor terminal resize can abruptly flip a card from spread to paged mode while the user is actively reading.

This research investigates the design of clear visual indicators and an ergonomic keymap for navigating the **3 valid operational states**:
- **State 1: Fully Spread** (Deck Spread & Card Blocks Spread)
- **State 2: Paged Deck, Spread Card** (Deck Paged & Card Blocks Spread)
- **State 3: Fully Paged** (Deck Paged & Card Blocks Paged)

### Recommended Solution Summary
- **Visual Clarity:**
  - **Deck Title (Top Border):** In State 1 (Spread Deck), replace the misleading single-tab highlight `Context │ ▐Reply 2/2▌` with a dedicated spread indicator `◆ MAIN [spread] ┃ Context ── Reply (all 2)`.
  - **Block Rail (Row 2):** In State 2 and State 3, explicitly communicate the block mode via a badge and contextual key hint:
    - State 2: `[spread] [ older · newer (scroll) ]` &mdash; clarifying that all blocks are in the scrollback.
    - State 3: `[paged 3/3] [ older · newer (page) ]` &mdash; clarifying that discrete pages are mounted.
  - **Deck Subtitle (Bottom Border):** Expand the bottom border tag from a bare `spread` to explicit state labels: `spread deck`, `spread card`, or `paged card` (dim), with a lock indicator (`🔒`) when manually overridden.
- **Keymap:** Bind **`P`** (`Shift+P`, action `toggle_deck_view_mode`) as a top-level, single-key action on the Agents tab.
  - `P` is 100% collision-free in `default_config.yml` (every lowercase letter `a-z` is occupied, but `P` is free).
  - It pairs mnemonically with `p` (`pick_deck`): `p` picks the deck, `P` toggles the deck/card projection.
  - Forward-cycles `State 1 &rarr; State 2 &rarr; State 3 &rarr; State 1`.
  - Gracefully collapses to a 2-state toggle (`State 1 &harr; State 2/3`) on cards without block navigation (Context card, single-shell agents) and on the Files deck.
  - Operates as an **ephemeral per-subject override**, persisting through content streaming and resizes, while seamlessly preserving cursor and scroll positions via SASE's existing `ReadingAnchor` engine.

---

## 1. Architectural Foundation & State Matrix

### 1.1 The Deck &rarr; Card &rarr; Block Hierarchy

In SASE's Agents tab, data presentation is structured into three layers:
1. **Deck:** Represents a major domain of agent inspection (`Main`, `Files`, `Tools`).
2. **Card:** Represents a distinct semantic document within a deck. For `Main`, cards include `Context` and `Reply`.
3. **Card Block:** Represents a titled, contiguous, stably identified sub-unit within a card. For `Reply`, each concrete sase shell (`plan`, `code`, `monitor`, `gate`) is encapsulated in a `CardBlock` carrying roster metadata (`BlockMeta`).

### 1.2 The Three Valid Visual States

Because of binding architectural decision **D3** established in `agent_data_card_blocks.md` ("*Only a card shown alone pages its blocks. A spread deck always spreads its blocks*"), the theoretical 2x2 matrix of `{Deck Spread, Deck Paged} &times; {Card Spread, Card Paged}` reduces strictly to **three valid states**:

```
+-------------------------------------------------------------------------+
|                                DECK LEVEL                               |
|                                                                         |
|   +--------------------------+           +--------------------------+   |
|   |       DECK SPREAD        |           |        DECK PAGED        |   |
|   | (All cards shown inline) |           | (Only active card shown) |   |
|   +------------+-------------+           +------------+-------------+   |
+----------------|--------------------------------------|-----------------+
                 |                                      |
                 v                                      |
       +--------------------+                           |
       |  CARD BLOCK LEVEL  |                           |
       |                    |                           |
       |  (Always Spread)   |                           |
       +---------+----------+                           |
                 |                                      |
                 v                                      v
       +====================+        +--------------------+--------------------+
       |      STATE 1       |        |                 CARD BLOCK              |
       |    FULLY SPREAD    |        |                                         |
       |                    |        |   +----------------+  +---------------+ |
       | - Deck: Spread     |        |   |  BLOCK SPREAD  |  |  BLOCK PAGED  | |
       | - Cards: All shown |        |   | (All inline)   |  | (1 page/shell)| |
       | - Blocks: Inline   |        |   +-------+--------+  +-------+-------+ |
       +====================+        +-----------|-------------------|---------+
                                                 |                   |
                                                 v                   v
                                       +===================+ +=================+
                                       |      STATE 2      | |     STATE 3     |
                                       | PAGED DECK,       | |   FULLY PAGED   |
                                       | SPREAD CARD       | |                 |
                                       | - Deck: Paged     | | - Deck: Paged   |
                                       | - Card: Active    | | - Card: Active  |
                                       | - Blocks: Inline  | | - Blocks: 1/page|
                                       +===================+ +=================+
```

#### Why State 4 ("Spread Deck + Paged Card") is Prohibited
If a deck is spread, cards are stacked vertically on a single continuous scroll canvas separated by heavy rules (`━━ ◆ Reply ━━`). Paging blocks inside one middle section of a continuous document would break scroll tracking, create jarring layout pops, and destroy the mental model of a continuous timeline. Thus, invariant D3 holds: **A spread deck always spreads its blocks.**

### 1.3 State Comparison Matrix

| Property | State 1: Fully Spread | State 2: Paged Deck, Spread Card | State 3: Fully Paged |
| :--- | :--- | :--- | :--- |
| **Deck RenderMode** | `RenderMode.SPREAD` | `RenderMode.PAGED` | `RenderMode.PAGED` |
| **Card Block Mode** | `RenderMode.SPREAD` (forced) | `RenderMode.SPREAD` | `RenderMode.PAGED` |
| **What is Rendered** | All cards (`Context`, `Reply`, etc.) inline | Only active card (`Reply`), all shell blocks inline | Only active card (`Reply`), single shell block on page |
| **Block Rail** | Hidden (phase dividers suffice) | **Visible** (scroll-derived active pill) | **Visible** (mounted page active pill) |
| **`Ctrl+J / Ctrl+K`** | Scroll anchor to next/prev card | Switch active card (page swap) | Switch active card (page swap) |
| **`[ / ]` (Prev/Next Block)** | Scroll anchor to block header | Scroll anchor to block header | Swap block page (reset to top) |
| **Scrollback Contents** | Entire deck history | Entire card history (all shells) | Isolated single shell output |
| **Typical Target Use Case** | Quick overview of short/medium sessions | Deep reading across full session timeline | Focusing on newest/single shell in large sessions |

---

## 2. Analysis of Current UX Friction Points

Investigation of the live implementation reveals three major sources of user confusion:

### 2.1 The Deceptive Active Tab in Spread Decks (State 1)
When `MainDeckView` renders in `RenderMode.SPREAD`, `panel_chrome.py` nevertheless invokes `deck_title()` with `active_index`:
```text
┌─ ◆ MAIN ┃ Context │ ▐Reply▌  2/2 ─────────────────────────────────────────────┐
```
Because the deck has landed on the "sticky Reply" card, `Reply` is rendered as an exclusive selection pill (`reverse bold <accent>`) with count `2/2`. 
- **The Confusion:** The top border explicitly signals to the user: *"You are viewing card 2 of 2 (Reply)."* However, in reality, `Context` is sitting right above `Reply` on the exact same canvas. A user who scrolls up is surprised to see `Context` appear.
- **The Bottom Tag:** The only visual hint that the deck is spread is a dim `spread` tag appended to the bottom border subtitle:
  `└──────────────────────────────────────────── spread  main 2 · files 1 · tools 109 ───┘`
  On narrower panes or when status messages appear, this dim tag is the first element dropped by the width fitter.

### 2.2 The Complete Indistinguishability of State 2 and State 3
This is the most critical usability flaw. Consider what the user sees in State 2 vs State 3:

**State 2 (Paged Deck + Spread Card):**
```text
┌─ ◆ MAIN ┃ Context │ ▐Reply▌  2/2 ─────────────────────────────────────────────┐
│  0 --plan ✓ ─ 1 ⋔ --gate ✓ ─ ▐2 --code ▶▌                [ older · newer ]  │
│  ─── AGENT (code) ─── 07:23:10 ─────────────────────────────────────────────  │
```

**State 3 (Paged Deck + Paged Card):**
```text
┌─ ◆ MAIN ┃ Context │ ▐Reply▌  2/2 ─────────────────────────────────────────────┐
│  0 --plan ✓ ─ 1 ⋔ --gate ✓ ─ ▐2 --code ▶▌                [ older · newer ]  │
│  ─── AGENT (code) ─── 07:23:10 ─────────────────────────────────────────────  │
```

Both states display:
1. The exact same border title: `◆ MAIN ┃ Context │ ▐Reply▌  2/2`
2. The exact same border subtitle: `main 2 · files 1 · tools 109` (neither has `spread`, because the *deck* is paged)
3. The exact same block rail: `0 --plan ✓ ─ 1 ⋔ --gate ✓ ─ ▐2 --code ▶▌  [ older · newer ]`
4. The exact same initial viewport content (the newest block).

**The Breakdown in User Mental Model:**
- In **State 2**, if the user scrolls up (`k` / `Ctrl+U`), the previous shells (`0 --plan`, `1 ⋔ --gate`) are in the scroll buffer above. Pressing `[` smoothly scrolls the window up to the header of shell 1.
- In **State 3**, if the user scrolls up, there is nothing above! To see shell 1, the user *must* press `[`, which triggers a discrete page swap.
- Without an indicator, the user cannot know whether they can scroll to see context or whether they must press page-stepping keys.

### 2.3 Unwanted Automatic Mode Transitions
Because mode decisions are automatic based on row thresholds:
- When a shell is actively streaming output, crossing the 1.5 screen threshold will abruptly flip the card from block-spread to block-paged.
- Splitting the deck (`\` or `|`) halves the viewport height, which can immediately flip both deck and card modes.
- Users have no way to say: *"I don't care how long this is, keep it spread"* or *"I want to focus on this single block, keep it paged"*.

---

## 3. Visual Design Solutions: Making View Modes Evident

To make view modes immediately legible at a glance, indicators must be integrated into the natural visual hierarchy:

```
┌─ [DECK BORDER TITLE] : Indicates DECK Mode (Spread vs Paged) ───────────────┐
│  [BLOCK RAIL]        : Indicates CARD BLOCK Mode (Spread vs Paged)          │
│                                                                             │
│  ... Card Content ...                                                       │
│                                                                             │
└─ [DECK SUBTITLE]     : Unifies Overall Mode & Override State ───────────────┘
```

### 3.1 Deck Title Bar (Top Border): Clarifying Deck Spread

#### State 1: Deck is Spread
When the deck is spread, we must dismantle the misleading illusion that only one card is active:
1. **Deck Badge:** Append a distinct `[spread]` badge directly next to the deck identifier:
   `◆ MAIN [spread]`
2. **Tab Grouping:** Connect card titles with inline connectors (`──` or `·`) instead of discrete column separators (`│`), and omit the exclusive `reverse bold` highlight:
   `Context ── Reply  (all 2)`
   *(Optional scroll anchor indicator)*: The card currently in the viewport can be denoted subtly with an underline or accent text without the heavy pill:
   `Context ── `**`Reply`**`  (all 2)`

```text
State 1 Title Mockup (Focused):
┌─ ◆ MAIN [spread] ┃ Context ── Reply  (all 2) ───────────────────────────────┐
```

#### State 2 & 3: Deck is Paged
When the deck is paged, the traditional tab strip is retained because only the active card is rendered:
```text
State 2 & 3 Title Mockup (Focused):
┌─ ◆ MAIN ┃ Context │ ▐Reply▌  2/2 ─────────────────────────────────────────────┐
```

### 3.2 Block Rail (Row 2): Clarifying Card Block Mode

The block rail is docked directly under the top border whenever the active card has &ge; 2 blocks. Because it sits directly above the card content, it is the primary focal point when reading shells.

#### Proposed Block Rail Enhancements

1. **Explicit Mode Badge (Left or Center-Left):**
   - **State 2 (Card Spread):** Display `[spread]` (or `[all inline]`) in muted accent style.
   - **State 3 (Card Paged):** Display `[paged]` (or `[page M/N]`).
2. **Contextual Key Hint (Right Edge):**
   The right edge of the rail currently shows `[ older · newer ]`. Expanding this hint communicates the mechanical effect of pressing `[` or `]`:
   - **State 2 (Card Spread):** `[ older · newer (scroll) ]` or `[spread]  [ older · newer ]`
   - **State 3 (Card Paged):** `[ older · newer (page) ]` or `[page 3/3]  [ older · newer ]`
3. **Active Pill Styling:**
   - In State 3 (Paged), the active pill `▐2 --code ▶▌` is a solid reverse block, symbolizing that the view is locked to that page.
   - In State 2 (Spread), where all blocks are inline and the active block is merely derived from the viewport's vertical scroll position, the pill can use an open/hollow bracket or distinct border: `▸ 2 --code ▶ ◂` or `▐2 --code ▶▌ (scroll)`.

```text
Rail Visual Mockups:

State 2 (Paged Deck + Spread Card):
│  [spread]  0 --plan ✓ ─ 1 ⋔ --gate ✓ ─ ▐2 --code ▶▌        [ older · newer ]  │

State 3 (Paged Deck + Paged Card):
│  [paged 3/3]  0 --plan ✓ ─ 1 ⋔ --gate ✓ ─ ▐2 --code ▶▌     [ older · newer ]  │
```

### 3.3 Deck Subtitle (Bottom Border): Unifying State & Lock Status

The bottom border subtitle currently houses `deck_subtitle()`. Expanding its tag parameter allows it to act as a definitive, unambiguous status summary:

- **State 1:** `spread deck  main 2 · files 1 · tools 109`
- **State 2:** `spread card  main 2 · files 1 · tools 109`
- **State 3:** `paged card  main 2 · files 1 · tools 109`

If the user has applied a manual toggle override, prefix with a lock indicator:
- `🔒 spread card  main 2 · files 1 · tools 109`

### 3.4 Comprehensive Visual State Mockups

#### Mockup: State 1 (Fully Spread)
*All cards shown inline; all blocks inline; rail hidden; title indicates spread.*
```text
┌─ ◆ MAIN [spread] ┃ Context ── Reply  (all 2) ───────────────────────────────┐
│                                                                             │
│  === Context =============================================================  │
│  Initial prompt: Investigate UX for card blocks spread/paged toggle...      │
│                                                                             │
│  ━━ ◆ Reply ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  ─── AGENT (plan) ─── 07:20:00 ───────────────────────────────────────────  │
│  Outlining implementation plan...                                           │
│                                                                             │
│  ─── AGENT (code) ─── 07:23:10 ───────────────────────────────────────────  │
│  Implementing widgets/decks/card_block.py...                                │
│                                                                             │
└───────────────────────────────────── spread deck  main 2 · files 1 · tools ─┘
```

#### Mockup: State 2 (Paged Deck, Spread Card)
*Only Reply card shown; all shells inline in scrollback; rail displays `[spread]` badge.*
```text
┌─ ◆ MAIN ┃ Context │ ▐Reply▌  2/2 ─────────────────────────────────────────────┐
│  [spread]  0 --plan ✓ ─ 1 ⋔ --gate ✓ ─ ▐2 --code ▶▌        [ older · newer ]  │
│                                                                             │
│  ─── AGENT (plan) ─── 07:20:00 ───────────────────────────────────────────  │
│  Outlining implementation plan...                                           │
│                                                                             │
│  ─── AGENT (code) ─── 07:23:10 ───────────────────────────────────────────  │
│  Implementing widgets/decks/card_block.py...                                │
│                                                                             │
└───────────────────────────────────── spread card  main 2 · files 1 · tools ─┘
```

#### Mockup: State 3 (Fully Paged)
*Only Reply card shown; only active shell shown; rail displays `[paged 3/3]` badge.*
```text
┌─ ◆ MAIN ┃ Context │ ▐Reply▌  2/2 ─────────────────────────────────────────────┐
│  [paged 3/3]  0 --plan ✓ ─ 1 ⋔ --gate ✓ ─ ▐2 --code ▶▌     [ older · newer ]  │
│                                                                             │
│  ─── AGENT (code) ─── 07:23:10 ───────────────────────────────────────────  │
│  Implementing widgets/decks/card_block.py...                                │
│  All tests pass. Ready for review.                                          │
│                                                                             │
└────────────────────────────────────── paged card  main 2 · files 1 · tools ─┘
```

---

## 4. Keymap Design & State Transitions

The user prompt specifies:
> *"I also want to add one or more new keymaps that allow the user to toggle through the 3 states (fully spread, paged deck and spread card, paged deck and paged card)."*

### 4.1 Key Selection Analysis & Collision Audit

An exhaustive audit of `src/sase/default_config.yml` across `ace.keymaps.app` and modal namespaces yields the following key availability facts:

1. **Lowercase Letters `a`&ndash;`z`:**
   - **Zero free keys.** Every single lowercase ASCII letter from `a` to `z` is already bound to an application or tab action on the Agents tab.
2. **Uppercase Letters `A`&ndash;`Z`:**
   - Almost all uppercase letters are bound (`A`, `C`, `D`, `E`, `F`, `G`, `H`, `I`, `J`, `K`, `L`, `M`, `N`, `O`, `Q`, `R`, `S`, `T`, `U`, `V`, `W`, `X`, `Y`, `Z`).
   - Exactly **two** uppercase letters are completely unbound in `app`: **`B`** and **`P`**.
3. **Symbols & Control Keys:**
   - `[` / `]`: Card block navigation (`prev_card_block` / `next_card_block`).
   - `{` / `}`: Deck panel resizing (`shrink_deck_panel` / `grow_deck_panel`).
   - `\` / `|`: Deck panel splitting (`toggle_deck_split_below` / `toggle_deck_split_right`).
   - `Ctrl+J` / `Ctrl+K`: Card cycling (`next_deck_card` / `prev_deck_card`).
   - `Ctrl+N` / `Ctrl+P`: Deck cycling (`next_deck` / `prev_deck`).

#### Evaluation of Key Candidates

| Candidate | Mnemonic | Pros | Cons | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **`P`** (`Shift+P`) | **P**rojection / **P**aged&harr;Spread / **P**anel view | Pairs naturally with `p` (`pick_deck`); completely unbound in `app`; 100% reliable terminal delivery; single keypress. | Uppercase requires shift. | **Recommended Winner** |
| **`s` / `S`** | **S**pread | High mnemonic value for "spread". | `s` is already bound to `save_marked_agents`; `S` is bound to `bulk_change_status`. Rebinding would break workflow. | Rejected (Collision) |
| **`z s` / `z p`** (Fold mode) | **z**-mode **s**pread | Uses existing modal namespace `fold_mode`. | Requires two sequential keystrokes (`z` then `s`), making rapid toggling cumbersome. | Acceptable fallback, but inferior ergonomics |
| **`, p`** (Leader mode) | Leader **p**rojection | Safe namespace; no top-level collision. | Two keystrokes; leader mode is reserved for administrative/rare tasks; layout toggle is an active browsing tool. | Rejected (Wrong semantic tier) |
| **`Ctrl+Shift+P`** | Control-Shift-Projection | Follows editor convention. | Susceptible to terminal/tmux swallowing (per Binding Decision D1). | Rejected (Terminal hazard) |

### 4.2 The Winning Choice: `P` (`Shift+P`)

`P` is the ideal key:
- **Pairing:** `p` opens the deck picker (`pick_deck`), while `P` cycles the deck/card view modes (`toggle_deck_view_mode`).
- **Cleanliness:** Zero conflicts in `app:` keymaps.
- **Reliability:** Standard printable ASCII (0x50), delivered identically across tmux, Kitty, Alacritty, WezTerm, iTerm2, and Windows Terminal.

### 4.3 State Transition Mechanics

When the user presses `P`, the focused deck panel advances to the next state in the 3-state cycle:

```
                  +----------------------------------+
                  |                                  |
                  v                                  |
            [ STATE 1 ]                              |
            Fully Spread                             |
           (Deck Spread)                             |
                  |                                  |
                  | Press 'P'                        |
                  v                                  |
            [ STATE 2 ]                              |
         Paged Deck, Spread Card                     |
        (Deck Paged, Block Spread)                   |
                  |                                  |
                  | Press 'P'                        |
                  v                                  |
            [ STATE 3 ]                              |
            Fully Paged                              |
         (Deck Paged, Block Paged)                   |
                  |                                  |
                  +------------- Press 'P' ----------+
```

#### Directionality: Do We Need a Reverse Key?
Because there are only 3 states:
- Moving from State 1 to State 3 takes only 2 presses of `P`.
- Moving from State 3 to State 1 takes 1 press of `P`.
A single cyclic key (`P`) is lightweight, fast, and sufficient. However, for maximum accessibility, SASE can provide:
- `toggle_deck_view_mode: "P"` (cycles forward)
- Direct commands exposed in the Command Palette (`;`):
  - `deck:view:fully-spread`
  - `deck:view:paged-spread`
  - `deck:view:fully-paged`
  - `deck:view:cycle`

### 4.4 Contextual Collapsing for Cards Without Blocks

Not all cards have card blocks! For example:
- The `Context` card has no blocks.
- The `Prompt` card has no blocks.
- A single-phase agent session has only 1 shell (`has_block_navigation` is False).

**The Problem:** On a card without blocks, State 2 (Paged Deck + Spread Card) and State 3 (Paged Deck + Paged Card) are visually and functionally identical (both render the lone card).
**The Rule:** If the active card has `< 2` blocks, the transition cycle **automatically skips State 3**, collapsing cleanly into a 2-state toggle:
$$\text{State 1 (Fully Spread)} \iff \text{State 2 (Paged Deck)}$$
This prevents redundant "dead keystrokes" that would otherwise do nothing.

### 4.5 Behavior on Other Decks (Files & Tools)

The deck view toggle should not be exclusive to `Main`:
- **Files Deck:** `Files` supports Spread (all diffs/files inline) and Paged (one file at a time), but does not have shell blocks. On the Files deck, `P` cleanly toggles between **Files Spread** and **Files Paged**.
- **Tools Deck:** Toggles between inline tool stream and paged tool details.

---

## 5. Technical Implementation Architecture

The feature can be implemented cleanly by leveraging the data models and anchor restoration mechanisms already built in epic `sase-19x`.

### 5.1 Data Model Additions (`widgets/decks/model.py`)

Define the pure state enum:

```python
class DeckViewState(StrEnum):
    """Hierarchical view state for a deck panel."""
    FULLY_SPREAD = "fully_spread"          # Deck spread, card blocks spread
    PAGED_DECK_SPREAD_CARD = "paged_spread" # Deck paged, card blocks spread
    FULLY_PAGED = "fully_paged"            # Deck paged, card blocks paged
```

### 5.2 Transition Logic (`widgets/decks/block_model.py`)

Add a pure transition helper:

```python
def cycle_deck_view_state(
    current: DeckViewState,
    *,
    has_blocks: bool,
    direction: int = 1,
) -> DeckViewState:
    """Return the next view state for the deck panel.
    
    If has_blocks is False, skips PAGED_DECK_SPREAD_CARD and collapses
    to a 2-state toggle between FULLY_SPREAD and FULLY_PAGED.
    """
    if not has_blocks:
        return (
            DeckViewState.FULLY_PAGED
            if current is DeckViewState.FULLY_SPREAD
            else DeckViewState.FULLY_SPREAD
        )
    
    cycle = (
        DeckViewState.FULLY_SPREAD,
        DeckViewState.PAGED_DECK_SPREAD_CARD,
        DeckViewState.FULLY_PAGED,
    )
    idx = cycle.index(current)
    return cycle[(idx + direction) % len(cycle)]
```

### 5.3 Panel Integration & Anchor Preservation (`widgets/decks/panel.py`)

The `DeckPanel` widget maintains an ephemeral override:
`_view_state_override: DeckViewState | None = None`

When `action_toggle_deck_view_mode` fires:
1. **Determine Current State:** Inspect `self.is_spread(self._deck)` and `self.main_view.block_mode_for_active_card()`.
2. **Calculate Next State:** Call `cycle_deck_view_state(current, has_blocks=card.has_block_navigation)`.
3. **Capture Reading Anchor:**
   ```python
   anchor = self._capture_reading_anchor(document, old_mode=old_deck_mode)
   ```
4. **Apply New Modes:**
   - If next is `FULLY_SPREAD`: set deck render mode to `SPREAD`.
   - If next is `PAGED_DECK_SPREAD_CARD`: set deck to `PAGED`, force active card block mode to `SPREAD`.
   - If next is `FULLY_PAGED`: set deck to `PAGED`, force active card block mode to `PAGED`.
5. **Render & Restore Anchor:**
   ```python
   self.main_view.show_document(document, preferred_card=active, mode=new_deck_mode, block_mode=new_block_mode)
   self._restore_block_transition(anchor, active)
   self.refresh_chrome()
   ```

Because SASE's `panel_transitions.py` already implements hierarchical `ReadingAnchor(card_id, block_id, offset_rows, pinned)` restoration, toggling modes preserves the user's scroll location and active block cursor without visual jumpiness.

### 5.4 Override Lifetime & Reset Semantics

How long does a manual override last?
- **Current Subject (Sticky):** While viewing the current agent session, the manual override remains locked. Incoming shell output or window resizes will not kick the user out of their chosen state.
- **Subject Change (`j`/`k`):** When navigating to a new agent in the tree, the override resets to `None` (returning to automatic measurement).
  - *Rationale:* A 1-shell session and a 20-shell session have vastly different display requirements. Forcing a 20-shell session to open in Fully Spread because the user toggled a small session earlier would cause performance lags.
- **Config Option:** For users who desire strict permanence, introduce a configuration setting:
  ```yaml
  ace:
    agent_decks:
      manual_view_mode_sticky: false  # When true, 'P' choice persists across j/k
  ```

---

## 6. Implementation Checklist & Phase Plan

To deliver this UX improvement smoothly following the close of `sase-19x`, the work should be executed across three tightly scoped phases:

### Phase 1: Pure State Model, Keymap Registration & Gating
- [ ] Add `DeckViewState` and `cycle_deck_view_state` to `widgets/decks/block_model.py`.
- [ ] Register `toggle_deck_view_mode: "P"` in `src/sase/default_config.yml` under `ace.keymaps.app`.
- [ ] Update `app_keymaps.py`, `keymaps/metadata.py`, and `bindings.py`.
- [ ] Add gating in `_app_action_availability.py` (active on Agents tab when focused on deck panels).
- [ ] Add parity unit tests verifying cycle behavior for cards with and without blocks.

### Phase 2: Panel Chrome & Block Rail Visual Indicators
- [ ] Update `titles.py` (`deck_title`): In `RenderMode.SPREAD`, format tabs with `[spread]` badge and linked connectors `──`, removing the deceptive single-card `reverse bold` highlight.
- [ ] Update `titles.py` (`deck_subtitle`): Support explicit mode strings (`spread deck`, `spread card`, `paged card`).
- [ ] Update `block_rail.py`: Add `[spread]` vs `[paged]` indicator badge and contextual key hints (`[ older · newer (scroll) ]` vs `[ older · newer (page) ]`).
- [ ] Add golden tests for title and rail renderings across all 3 states.

### Phase 3: Action Execution, Transitions & User Documentation
- [ ] Implement `action_toggle_deck_view_mode` on `AgentDetail` and `DeckPanel`.
- [ ] Hook into `ReadingAnchor` capture and restoration in `panel_transitions.py`.
- [ ] Handle Files deck 2-state toggle (`Files Spread` &harr; `Files Paged`).
- [ ] Add help modal entries in `agents_bindings.py` under the "Navigation" section.
- [ ] Document `P` key and view states in `docs/ace.md` and `docs/configuration.md`.

---

## Conclusion & Recommended Next Step

The tension between automatic sizing and user intent is resolved by providing **explicit visual feedback** and **direct user control**. 
1. **Visually**, labeling State 1 with `[spread]` in the title and labeling States 2 and 3 with `[spread]` vs `[paged]` in the Block Rail completely dispels state ambiguity.
2. **Interactively**, binding **`P`** delivers a zero-collision, ergonomic, single-keystroke controller to cycle smoothly between all three valid states.

Following the landing of epic `sase-19x`, this specification should be formalized as an executable follow-up plan bead (`bd/new_epic` or task bead) to deliver these UX polish items.
