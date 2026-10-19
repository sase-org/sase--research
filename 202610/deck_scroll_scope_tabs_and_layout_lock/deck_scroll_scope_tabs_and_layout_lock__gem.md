# Deck Scroll Clarity, Sub-Tab Affordances, and View Badges UX Architecture

> **Author**: researcher gem (`research.52.gem`)  
> **Date**: October 2026  
> **Status**: Independent Research Report  
> **Topic**: SASE ACE TUI Agent Data Decks — Scroll Clarity, Card Sub-Tab Affordances, and View Badges

---

## 1. Executive Summary

In the SASE ACE TUI, the **Agent Data Decks** (Main, Files, Tools, FINAL, RECORD) represent the core reading and inspection surface for agent state, prompts, replies, and file changes. A longstanding point of user friction is the cognitive ambiguity surrounding **deck scrollability**:

> *Can I scroll down to see the entire deck, or is content cut off / isolated into separate sub-tabs that require `<Ctrl+J>` / `<Ctrl+K>` to navigate?*

Currently, whether a multi-card deck renders **spread** (every card vertically concatenated in a single continuous scroll container) or **paged** (one card at a time, hiding sibling cards), the top border title renders virtually identical horizontal tab strips:
```text
Spread: ◆ MAIN  spread · auto  ┃  Prompt │ Context │ Reply  1/3
Paged:  ◆ MAIN  cards · auto   ┃ [Prompt]│ Context │ Reply  1/3
```

This presentation violates foundational interface design principles:
1. **False Affordance**: Horizontal tabs universally signify mutually exclusive views. Displaying tabs over a continuous, scrollable document misleads users into believing they cannot scroll past the active card.
2. **Low-Salience Badging**: The current badge (`spread · auto` vs `cards · auto`) uses subtle foreground text (`#888888` / accent) on transparent backgrounds with zero visual pop.
3. **Misleading Vocabulary**: The term `cards` (from `page cards`) fails as a layout descriptor because decks consist of cards in *both* modes. Calling policies `auto` and `fixed` exposes internal engine mechanics rather than immediate user navigation affordances.

### Verdict on the Proposed Direction

The user's plan proposes three core changes:
1. **Show card sub-tabs only when actually paged** (i.e. when `<Ctrl+J/K>` is required to switch cards).
2. **Introduce bright, clearly visible badges** to indicate the view.
3. **Replace "auto" and "fixed" with a lock icon (`🔒`)**.

**Assessment**: The plan is **fundamentally sound, highly intuitive, and solves the primary user pain point**. However, a naive implementation would introduce subtle new UX hazards (specifically: off-screen card discoverability in spread mode, footer hint dissonance, and cross-deck inconsistency on Final and Record). 

This report critiques each proposal, resolves the edge cases, and provides a concrete architectural specification for implementation in `src/sase/ace/tui/widgets/decks/`.

---

## 2. Technical Context & Mental Model Analysis

### 2.1 The Two Fundamental Render Modes

In `src/sase/ace/tui/widgets/decks/`, card documents are rendered through `CardDocumentView` inside a Textual `VerticalScroll` container. There are two primary rendering modes:

```
+-------------------------------------------------------------------------+
| SPREAD MODE (Continuous Document)                                       |
| VerticalScroll                                                          |
| +---------------------------------------------------------------------+ |
| | [Card 1: Prompt]                                                    | |
| | Prompt text...                                                      | |
| | ━━ ◆ Context ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ | |
| | [Card 2: Context]                                                   | |
| | Context text...                                                     | |
| | ━━ ◆ Reply ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ | |
| | [Card 3: Reply]                                                     | |
| | Reply text...                                                       | |
| +---------------------------------------------------------------------+ |
| All cards live in one scroll stream. Normal scroll keys move through.   |
| <Ctrl+J/K> performs an anchor jump to card separators.                 |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
| PAGED MODE (Segmented Cards)                                            |
| VerticalScroll                                                          |
| +---------------------------------------------------------------------+ |
| | [Card 1: Prompt]                                                    | |
| | Prompt text...                                                      | |
| | (End of Card 1 — Bottom of scrollable container)                    | |
| +---------------------------------------------------------------------+ |
| Only ONE card is mounted. Scrolling down terminates at Card 1's end.   |
| <Ctrl+J/K> is REQUIRED to flip to Card 2 or Card 3.                     |
+-------------------------------------------------------------------------+
```

1. **Spread Mode (`RenderMode.SPREAD`)**:
   - Every card in the document is rendered in vertical sequence.
   - Consecutive cards are delineated by titled rules (`_CardSeparator`: `━━ ◆ Context ━━━━`).
   - The scrollbar spans the entire multi-card document.
   - `<Ctrl+J>` / `<Ctrl+K>` (`next_deck_card` / `prev_deck_card`) does not swap pages; it scrolls the next/previous card separator to the top of the viewport (`_cycle_main_spread`).

2. **Paged Mode (`RenderMode.PAGED` / `DeckView.PAGE_CARDS`)**:
   - Only the active card is mounted into the scroll container.
   - Scrolling is strictly bounded within the active card.
   - `<Ctrl+J>` / `<Ctrl+K>` swaps the mounted card document.

3. **Block Paged Mode (`DeckView.PAGE_BLOCKS`)**:
   - A sub-mode of paged mode (Main deck only) where both cards *and* multi-part blocks within the card (e.g. streaming assistant reply chunks) are paged individually.

### 2.2 How Policies Work Today (`model.py`, `view_policy.py`)

- **Policy**: Each panel tracks a `DeckView` policy for Main and Files: `AUTO`, `SPREAD`, `PAGE_CARDS`, `PAGE_BLOCKS`.
- **Automatic Resolution**: Under `AUTO`, `render_mode.py:decide_render_mode()` measures the rendered row height of all cards against `ace.agent_decks.spread_max_screens` (default: 1.5 viewport heights). If total rows fit within 1.5 screens (with 10% hysteresis), it renders spread. If content overflows 1.5 screens, it automatically flips to paged.
- **Fixed Policy**: Pressing `P` (`cycle_deck_view`) cycles between the fixed views (`page blocks` → `page cards` → `spread`), locking the layout so automatic resizing never reverts it. The command palette offers `Deck view: automatic` to unlock.

### 2.3 The Root UX Failure Mode

The user's confusion stems directly from `src/sase/ace/tui/widgets/decks/titles.py`:

In `deck_title()`:
- Regardless of whether `is_spread` is True or False, `tabs = tuple(tabs)` is rendered into the title bar via `_build_full()` or `_build_compact()`.
- In Spread mode, `active_index` tracks the *reading position anchor* (derived from `scroll_y`). As the user scrolls past card separators, the highlight on the tab strip shifts from `Prompt` to `Context` to `Reply`.
- To the author, this was conceived as a "table of contents scrollspy".
- **To the user, this looks 100% like browser or editor tabs**. When users see `[Prompt] │ Context │ Reply`, their universal mental model is: *"I am on tab 1. To see tab 2, I must click or switch tabs. Scrolling will not take me there."*

Compounding the problem, the badge that is supposed to disambiguate this:
```python
# view_badge.py lines 78-86
if focused:
    text.append(layout_word, style=accent)
    text.append(joiner, style=_SEPARATOR)
    text.append(status_word, style=status_style)
```
- Is rendered with transparent background and muted grey joiners.
- Says `cards · auto` in paged mode. "Cards" is not an action or a layout; it's a noun.
- When the panel is unfocused, the entire badge collapses into `dim` monochrome text.
- For Tools, FINAL, and RECORD decks, **no badge appears at all** (they are permanently auto), yet FINAL and RECORD can still spread or page based on height!

---

## 3. Critical Critique of Proposed Changes

### Proposal 1: Only Show Card Sub-Tabs When Actually Paged

> *"only showing card sub-tabs when we actually have split out sub-tabs (i.e. when the user has to use the `<ctrl+j/k>` keymaps to view other cards in the current deck)."*

#### Why this is a great idea
- **Direct Affordance Alignment**: Tabs exist if and only if pagination exists. If you see tabs, you must page. If you do not see tabs, you can scroll.
- **Cognitive Relief**: The user does not need to parse badge text or memorize SASE layout terminology to know how to navigate.
- **Horizontal Chrome Reclaim**: Removing tabs in spread mode frees up 30–60 terminal columns in the top border title. On split screens (2-pane or 3-pane splits where panels are 40–50 columns wide), this completely eliminates ugly tab truncation and ellipsis (`…`).

#### Potential Hazards & Refinements
1. **The "Below-the-Fold" Discovery Hazard**:
   - *Problem*: In spread mode, if an agent has a 30-line Prompt card, and the viewport is only 22 lines high, the user only sees the top part of Prompt. The separator `━━ ◆ Context ━━━━` is below the fold.
   - If sub-tabs are completely stripped from the title bar, does the user know that Context and Reply exist below?
   - *Critique*: A completely empty title bar (`◆ MAIN  [SPREAD]`) fails to communicate that multiple cards exist. The subtitle at the bottom says `main (3)`, but users look at the top title for orientation.
   - *Refinement*: In spread mode, instead of *interactive tabs* (`[Prompt] │ Context │ Reply`), display a **Reading Anchor / Card Overview** (e.g. `(3 cards · scroll ↕)` or `§ Prompt (1/3)`). This provides orientation without looking like switchable tabs.

2. **Footer Keybinding Mismatch**:
   - Currently, `_keybinding_bindings_agents.py` hardcodes:
     ```python
     if deck_card_count > 1:
         bindings.append((f"{next}/{prev}", "cards"))
     ```
   - In spread mode, `<Ctrl+J/K>` still functions as an anchor jump (scrolling to the next card header).
   - If the title bar has no tabs, but the footer says `^J/^K cards`, users wonder what "cards" refers to.
   - *Refinement*: Contextualize the footer binding: in paged mode, display `^J/^K cards` (or `^J/^K tab`); in spread mode, display `^J/^K jump` (or `^J/^K section`).

---

### Proposal 2: Bright and Clearly Visible View Badges

> *"start showing a bright and clearly visible set of badges that indicate the view."*

#### Why this is a great idea
- Instant glanceability: Users should not have to lean in to read low-contrast grey text to determine the viewport mode.
- In terminal interfaces, high-contrast pills (text on colored background) provide immediate visual anchoring. SASE already uses this successfully with the reverse-gold `ZOOM` chip (`bold #1a1a1a on #FFD700`).

#### Potential Hazards & Refinements
1. **Visual Noise & Hierarchy**:
   - If the badge is excessively bright (e.g. bright yellow or flashing colors), it competes with the actual agent content (diffs, code syntax, markdown headings).
   - *Refinement*: Use **inverted theme pills** rather than arbitrary neon colors. For example:
     - `SPREAD`: Inverse Accent / Secondary (e.g. `bold #1a1a1a on #87D7AF` or theme secondary background). Clean, calm, indicates continuous document flow.
     - `PAGED`: Inverse Warning / Amber (e.g. `bold #1a1a1a on #D7AF5F`). Amber signals that content is partitioned/segmented.
     - `BLOCKS`: Inverse Purple / Violet (e.g. `bold #1a1a1a on #AF87D7`).
   - When unfocused, reduce opacity/saturation (e.g. `dim on #333333` or subtle bordered pill) so only the active panel draws primary focus.

2. **Terminology Overhaul**:
   - The current terms are confusing:
     - `spread`: Acceptable, but technical.
     - `cards`: Confusing. Both spread and paged modes contain cards.
     - `blocks`: Slightly obscure without context.
   - *Refinement*:
     - Long forms: `[ SPREAD ]`, `[ PAGED ]`, `[ BLOCKS ]`.
     - Short forms: `[ SPREAD ]`, `[ PAGED ]`, `[ BLOCKS ]`.
     - Tiny forms (for tight splits): `[ S ]`, `[ P ]`, `[ B ]`.
   - Never use the bare word "cards" to mean "paged". "PAGED" immediately communicates that content is broken into pages.

---

### Proposal 3: Replace "Auto" and "Fixed" with a Lock Icon (`🔒`)

> *"stop showing "auto" and "fixed" and start representing this state using a little lock icon instead?"*

#### Why this is a great idea
- **Saves 5 to 8 Columns**: " · auto" is 7 characters; " · fixed" is 8 characters. In split viewports where total width is 45 characters, spending 8 characters on policy metadata is wasteful.
- **Universal Affordance**: In consumer and developer UX (smartphones, IDE toolbars, graphics software), a lock icon is the universal symbol for "this parameter has been pinned / locked and will not auto-adjust".
- **Clean Default**: Automatic is the expected default state. Showing the word "auto" on every single panel is visual clutter.

#### Potential Hazards & Refinements
1. **What to show when "Auto"?**:
   - *Crucial Decision*: Do **NOT** display an unlocked lock (`🔓`) when auto.
   - An open lock conveys insecurity or a broken state, and displaying `🔓` across 4 panels adds needless noise.
   - **Recommended Pattern: Quiet Default, Explicit Override**:
     - When `AUTO`: Show just the badge (e.g. `[ SPREAD ]` or `[ PAGED ]`). No icon.
     - When `FIXED`: Append the lock icon (e.g. `[ SPREAD ] 🔒` or `[ PAGED ] 🔒`).
     - The presence of `🔒` immediately tells the user: *"You pinned this view with `P`."*

2. **Terminal Glyph Safety**:
   - `🔒` (U+1F512) is a 2-cell wide Unicode emoji.
   - SASE already uses `🔒` in multiple core surfaces:
     - `src/sase/ace/tui/widgets/_prompt_input_bar_title.py:171` (`🔒 read-only`)
     - `src/sase/bead/attachment_presentation.py:23` (`PRIVATE_BADGE = "🔒"`)
     - `src/sase/ace/tui/modals/bead_note_modal.py:348`
   - Rich and Textual calculate cell widths using `cell_len()`, where `cell_len("🔒") == 2`.
   - In tight spaces where 2 cells matter, the badge ladder can degrade to `[S]🔒` or `[S*]`.

3. **What about `PENDING` and `BLOCKED` statuses?**:
   - Files deck can be `PENDING` (measuring large diffs in the background) or `BLOCKED` (media files cannot spread).
   - These are content states, not policy locks:
     - `PENDING`: `[ SPREAD… ]` (pulsing or trailing ellipsis).
     - `BLOCKED`: `[ PAGED ] ⚠` or `[ NO SPREAD ]` with warning yellow.
     - A blocked view should never show a lock icon unless the user *also* fixed the policy.

---

## 4. Proposed UX Architecture & Design Specification

### 4.1 Title Bar State Matrix

The table below defines the exact title bar rendering across all combinations of deck mode, policy, and card counts:

| Render Mode | Policy | Content State | Title Bar Layout (Wide / Full) | Title Bar Layout (Narrow / Split) |
| :--- | :--- | :--- | :--- | :--- |
| **Spread** | Auto | Multi-card | `◆ MAIN  [ SPREAD ] ┃ (3 cards · scroll ↕)` | `◆ MAIN [S] ┃ (3)` |
| **Spread** | Fixed | Multi-card | `◆ MAIN  [ SPREAD ] 🔒 ┃ (3 cards · scroll ↕)` | `◆ MAIN [S]🔒 ┃ (3)` |
| **Spread** | Auto | Single-card | `◆ MAIN  [ SPREAD ]` | `◆ MAIN [S]` |
| **Paged** | Auto | Multi-card | `◆ MAIN  [ PAGED ] ┃ [Prompt] │ Context │ Reply  1/3` | `◆ MAIN [P] ┃ ‹ 1/3 › Prompt` |
| **Paged** | Fixed | Multi-card | `◆ MAIN  [ PAGED ] 🔒 ┃ [Prompt] │ Context │ Reply  1/3` | `◆ MAIN [P]🔒 ┃ ‹ 1/3 › Prompt` |
| **Blocks** | Fixed | Multi-block | `◆ MAIN  [ BLOCKS ] 🔒 ┃ [Reply] 3/3 ┃ Block 2/5` | `◆ MAIN [B]🔒 ┃ Blk 2/5` |
| **Files** | Blocked | Media diff | `◆ FILES [ PAGED ] ⚠ ┃ file 1 │ [file 2]  2/2` | `▤ FILES [P]⚠ ┃ 2/2` |
| **Files** | Pending | Measuring | `◆ FILES [ SPREAD… ] ┃ file 1 │ [file 2]  2/2` | `▤ FILES […] ┃ 2/2` |

### 4.2 Visual Anatomy Mockups

#### Mockup 1: Multi-Card Spread Mode (Continuous Scroll)
```text
┌─ ◆ MAIN  [ SPREAD ] ┃ 3 cards · scroll ↕ ───────────────────────────────┐
│ System Prompt:                                                          │
│ You are an expert engineer working on SASE.                             │
│                                                                         │
│ User Request:                                                           │
│ Please fix the race condition in update_attempts.py.                    │
│                                                                         │
│ ━━ ◆ Context ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ Active workspace: sase-org/sase/sase_17                                 │
│ Open files: src/sase/ace/update_attempts.py                             │
│                                                                         │
│ ━━ ◆ Reply ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ I have investigated the race condition and applied a locked file guard. │
└─ main (3) · files (1) · tools (4) · final · record ─────────────────────┘
```
*Visual cue*: There are NO tabs in the top border. The user instantly understands this is a single, continuous document. The pill `[ SPREAD ]` confirms continuous layout. The text `3 cards · scroll ↕` confirms that Context and Reply are waiting below.

#### Mockup 2: Multi-Card Paged Mode (Sub-Tabs Present)
```text
┌─ ◆ MAIN  [ PAGED ] 🔒 ┃ [Prompt] │ Context │ Reply  1/3 ────────────────┐
│ System Prompt:                                                          │
│ You are an expert engineer working on SASE.                             │
│                                                                         │
│ User Request:                                                           │
│ Please fix the race condition in update_attempts.py.                    │
│                                                                         │
│ (End of Prompt card)                                                    │
└─ main (3) · files (1) · tools (4) · final · record ─────────────────────┘
```
*Visual cue*: Clear, distinct tabs are rendered. The active tab `[Prompt]` is highlighted. The badge `[ PAGED ] 🔒` tells the user: (1) content is paged, and (2) this mode is pinned by user preference. The user immediately knows to press `<Ctrl+J>` to see Context.

#### Mockup 3: Narrow 3-Pane Split (Graceful Degradation)
```text
┌─ ◆ MAIN  [P]🔒 ┃ ‹ 1/3 › Prompt ────────┐
│ System Prompt:                          │
│ You are an expert engineer...           │
└─ main (3) ──────────────────────────────┘
```
*Visual cue*: On a 40-column panel, the badge shrinks to `[P]🔒` (5 cells total), and the tab strip gracefully degrades to compact ordinal `‹ 1/3 › Prompt`. No information is lost, and nothing overflows.

---

## 5. Technical Implementation Blueprint

To implement this design cleanly within the existing SASE codebase without regressing persistence or test suites, the following components should be modified:

### 5.1 Badge Construction (`src/sase/ace/tui/widgets/decks/view_badge.py`)

1. **Pill Style Definitions**:
   Replace plain foreground text with inverted high-contrast pills:
   ```python
   # High-contrast badge styles
   _BADGE_STYLE_SPREAD = "bold #1a1a1a on #87D7AF"   # Muted teal/cyan pill
   _BADGE_STYLE_PAGED  = "bold #1a1a1a on #D7AF5F"   # Amber/gold pill
   _BADGE_STYLE_BLOCKS = "bold #1a1a1a on #AF87D7"   # Purple pill
   _BADGE_STYLE_DIM    = "bold #888888 on #262626"   # Unfocused pill
   _LOCK_ICON          = "🔒"
   ```

2. **Lock Icon Integration**:
   Instead of appending `· auto` or `· fixed`, append `🔒` only when `resolved.policy is not DeckView.AUTO`:
   ```python
   def _status_icon(resolved: ResolvedView) -> str:
       if resolved.status is ViewStatus.PENDING:
           return "…"
       if resolved.status is ViewStatus.BLOCKED:
           return "⚠"
       if resolved.policy is not DeckView.AUTO:
           return " 🔒"
       return ""
   ```

3. **Badge Text Variants**:
   - `SPREAD`: Long = `" SPREAD "`, Short = `" SPREAD "`, Tiny = `" S "`
   - `PAGE_CARDS`: Long = `" PAGED "`, Short = `" PAGED "`, Tiny = `" P "`
   - `PAGE_BLOCKS`: Long = `" BLOCKS "`, Short = `" BLOCKS "`, Tiny = `" B "`

### 5.2 Chrome Title Assembly (`src/sase/ace/tui/widgets/decks/titles.py`)

Modify `deck_title()` and `_build_full()` to accept an explicit `is_spread: bool` flag:

1. **Conditional Sub-Tab Rendering**:
   ```python
   if is_spread:
       # SPREAD MODE: Suppress sub-tabs.
       # Render reading anchor overview instead of tabs.
       if len(tabs) > 1:
           card_info = f"({len(tabs)} cards · scroll ↕)"
           # Build: glyph NAME [SPREAD][🔒] ┃ (N cards · scroll ↕)
   else:
       # PAGED MODE: Render real sub-tabs.
       # Build: glyph NAME [PAGED][🔒] ┃ [Card 1] │ Card 2  1/2
   ```

2. **Reading Anchor Dynamic Tracking**:
   When in spread mode, as the user scrolls, `active_index` tracks the current visible section. If width permits, render:
   ```text
   ◆ MAIN  [ SPREAD ] ┃ (3 cards · § Context 2/3)
   ```
   This gives the user continuous reading orientation without looking like clickable tabs.

### 5.3 Panel Chrome Mixin (`src/sase/ace/tui/widgets/decks/panel_chrome.py`)

In `DeckPanelChromeMixin.refresh_chrome()`:
Pass `is_spread=self._is_spread_active_for(deck)` into `deck_title()`.
Ensure this applies uniformly across `MAIN`, `FILES`, and where applicable, `FINAL` and `RECORD`.

### 5.4 Footer Keybinding Alignment (`src/sase/ace/tui/widgets/_keybinding_bindings_agents.py`)

Update the keybinding label dynamically based on the focused panel's render mode:
```python
is_spread = focused_panel.is_spread(focused_panel.deck)
label = "jump" if is_spread else "cards"
bindings.append((f"{self._kd('next_deck_card')}/{self._kd('prev_deck_card')}", label))
```
This ensures the footer reinforces the visual mental model:
- Paged: `^J/^K cards` (or `^J/^K tabs`)
- Spread: `^J/^K jump` (jump between card sections)

---

## 6. Trade-off Matrix & Alternatives Analysis

| Approach | Scroll Clarity | Off-Screen Card Discoverability | Split Pane Friendliness | Implementation Complexity | Overall UX Rating |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Status Quo** | ❌ Poor (Tabs look identical in both modes) | ⚠️ Moderate (Tabs visible, but misleads scrollability) | ❌ Poor (Tabs truncate heavily on splits) | N/A (Existing) | 3/10 |
| **Approach 1: Strict User Proposal** (Hide tabs in spread, bright badge, lock icon, empty title in spread) | 🟢 Excellent (No tabs = scroll) | ❌ Poor (User doesn't know cards exist below fold) | 🟢 Excellent (Saves massive width) | Low | 7/10 |
| **Approach 2: Recommended Solution** (Hide tabs in spread + Spread Reading Anchor + Inverted Badges + Lock Icon + Footer Sync) | 🟢 Excellent (Tabs = page, Anchor = scroll) | 🟢 Excellent (`(3 cards · scroll ↕)` informs user) | 🟢 Excellent (Graceful ladder down to `[S]🔒`) | Low–Medium | **9.5/10** |
| **Approach 3: Floating Scroll Overlay** (Keep tabs in both, add a floating `↓ More Cards` toast at bottom) | ⚠️ Fair (Distracting floating element in TUI) | 🟢 Good | ❌ Bad (Overlays agent text in small terminals) | High | 5/10 |

---

## 7. Actionable Implementation Recommendation

### Recommended Action Plan

We recommend executing this feature in **three discrete, low-risk phases**:

1. **Phase 1: Vocabulary & Lock Icon Cutover** (`view_badge.py`):
   - Replace `cards` with `PAGED`, `spread` with `SPREAD`, `blocks` with `BLOCKS`.
   - Replace `· auto` and `· fixed` with a conditional `🔒` icon when fixed.
   - Upgrade badge styling to high-contrast inverted pill styling (`_BADGE_STYLE_SPREAD`, `_BADGE_STYLE_PAGED`).
   - Update `test_deck_view_policy.py` to assert new badge variants.

2. **Phase 2: Spread Tab Suppression & Reading Anchor** (`titles.py`, `panel_chrome.py`):
   - In `panel_chrome.py`, pass `is_spread` to `deck_title()`.
   - In `titles.py`, when `is_spread` is True, omit the `CardTab` tabstrip delimiters (`│`) and active-tab reverse highlight.
   - In place of tabs, display the Reading Anchor: `(N cards · scroll ↕)` when multiple cards exist.
   - Update `test_deck_titles.py` and `test_deck_chrome.py`.

3. **Phase 3: Contextual Footer Hint Alignment** (`_keybinding_bindings_agents.py`):
   - Update `<Ctrl+J/K>` footer hint to display `jump` when focused on a spread deck, and `cards` (or `tabs`) when paged.
   - Re-verify TUI visual snapshots via VHS/pilot tests.

### Summary Verdict

The user's intuition is right on target: **showing sub-tabs on a spread deck is the root cause of the confusion**. By restricting sub-tabs strictly to paged decks, introducing high-contrast view badges, replacing "auto/fixed" with `🔒`, and adding a lightweight reading anchor in spread mode, the SASE ACE TUI achieves crystal-clear visual affordance without cluttering the screen.
