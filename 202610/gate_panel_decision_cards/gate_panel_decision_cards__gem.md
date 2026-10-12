# TUI Gate Panel Decisions Redesign: Layout, Typography, and Interaction

**Author:** Researcher `gem` (research.4a.gem)  
**Date:** 2026-10-12  
**Target Surface:** SASE TUI Plan Review Gate Modal (`PlanApprovalModal` / `gate-review-shell`)  
**Scope:** Forensic analysis of current gate decision rendering, root causes of text clipping, layout alternatives, and a comprehensive UX/architectural recommendation.

---

## 1. Executive Summary

Plan Decisions allow authors to embed reviewer choices directly within plans, enabling reviewers to steer implementation parameters (such as directory targets, cleanup policies, and architectural trade-offs) at gate approval time without stalling the workflow.

However, an inspection of live gate approval captures (specifically `~/tmp/screenshots/20261012_074036.png`) reveals that the current presentation of Plan Decisions in the SASE TUI is severely compromised:

1. **Catastrophic Horizontal Clipping:** Crucial prompt questions (`ask`), option descriptions, rationales (`why`), and memory citations are violently truncated mid-word (e.g., `"Where should the relocated legacy tree (f"`, `"  ◉ db * ~/db: matches the existing $DB/"`, `"Should the ~70 stow-style dotfile symlink"`).
2. **Invisible Decisions (Vertical Starvation):** The decision list is constrained to an arbitrary maximum height (`max-height: 16`). In the screenshot, with 4 declared decisions, the 4th decision (`old_tmp`) is completely invisible and pushed below the viewport without a clear scroll affordance.
3. **Severe Modal Real-Estate Imbalance:** In a standard modern terminal (~200 columns wide), the left action/decision rail is hardcoded to a fixed 50-cell width (~25% of the screen), while the right plan document pane consumes ~145 cells (~75% of the screen). Because standard Markdown plan text wraps at 80–100 characters, the right pane wastes ~60–70 columns of dead black space, while the critical decision interface starves in 46 usable columns.
4. **Widget Misuse:** Decision rows are implemented as monolithic Textual `Button` widgets displaying dense, unformatted `Rich.Text` strings. Textual buttons default to `overflow: hidden; text-overflow: clip`, preventing multi-line text wrapping and muddling semantic styling.

This report conducts a forensic analysis of the current implementation, evaluates four architectural design directions, and delivers a recommended solution and UX specification: **a responsive, proportional two-pane layout with dedicated multi-line `PlanDecisionCard` widgets, compact accordion states, and clear typographic hierarchy.**

---

## 2. Forensic Analysis of Current Implementation

### 2.1 Visual Evidence: Screenshot `20261012_074036.png`

The screenshot displays the SASE TUI running on `bas athena` inside `PlanApprovalModal` titled `Plan Review  CLAUDE(opus)`.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ sase tui (v0.17.1+...)                                                       Plan Review  CLAUDE(opus)                 │
├─────────────────────────────────────────────────┬──────────────────────────────────────────────────────────────────────┤
│ Actions                                         │ plan.md                                                              │
│   e ✏️ Edit plan                                │ **one** batched `/sase_sudo` request (Step 10)...                    │
│   Accepted only when 'sase plan validate' pass  │ Throughout this plan `<root>` means `~/db`...                        │
│ ─────────────────────────────────────────────── │                                                                      │
│ Decisions 4 · 🧠 0                              │ ## Non-goals                                                         │
│ ┌─────────────────────────────────────────────┐ │ - Dissolving the legacy tree into chezmoi...                         │
│ │ ◉ root  db                                  │ │ - Committing or pushing inside the legacy checkouts...               │
│ │ Where should the relocated legacy tree (f   │ │                                                                      │
│ │   ◉ db * ~/db: matches the existing $DB/    │ │                                                                      │
│ │   ○ legacy ~/legacy: names it as the pre    │ │                                                                      │
│ │   * ~/.profile already calls this root $D   │ │                                      [~65 columns of unused          │
│ │   default: db                               │ │                                       blank space on right]          │
│ │ ◉ dotfiles  repoint                         │ │                                                                      │
│ │ Should the ~70 stow-style dotfile symlink   │ │                                                                      │
│ │ ◉ conflicts  delete                         │ │                                                                      │
│ │ Should all ~400 Syncthing *.sync-conflict   │ │                                                                      │
│ └─────────────────────────────────────────────┘ │                                                                      │
│ Verdict                                         │                                                                      │
│   ☑ 1 Launch coder  ☑ 2 Reject  ☐ 3 Feedback   │                                                                      │
│   1 Tale  2 Reject  3 Feedback                 │                                                                      │
│   → coder + commit · root=db · dotfiles=repoi.. │                                                                      │
├─────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────┤
│ j/k=Navigate Space=Toggle Enter=Tale · defaults Ctrl+S=Submit l/right=Next choice h/left=Prev choice r=Reset ...       │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Observable Defects:
1. **Truncation of Prompt Question:** The question for the selected decision `root` reads: `"Where should the relocated legacy tree (f"`. The user cannot even read the full question!
2. **Truncation of Option Consequence Labels:** Option `db` cuts off at `"...existing $DB/"`. Option `legacy` cuts off at `"...names it as the pre"`. The reviewer cannot understand the trade-offs of the options.
3. **Truncation of Rationale:** The rationale for the default (`why`) cuts off at `"* ~/.profile already calls this root $D"`.
4. **Truncation of Collapsed Prompts:** Decision 2 (`dotfiles`) cuts off at `"Should the ~70 stow-style dotfile symlink"`. Decision 3 (`conflicts`) cuts off at `"Should all ~400 Syncthing *.sync-conflict"`.
5. **Missing Decision 4:** The header clearly states `"Decisions 4 · 🧠 0"`, but only 3 decisions are visible in the box. The fourth decision, `old_tmp`, is completely hidden. The only clue that `old_tmp` exists is in the fine-print summary at the very bottom: `old_tmp=nest`.
6. **Vast Dead Space on Right:** The document pane displays standard Markdown prose (~80 characters wide). In a full-screen terminal, more than 40% of the modal width is completely empty black space.

---

### 2.2 Code-Level Root Cause Analysis

Tracing the TUI implementation across `src/sase/ace/tui/` reveals the exact technical mechanisms causing these failures:

#### 1. Hardcoded Rail Width in TCSS
In `src/sase/ace/tui/styles.tcss`:
```css
PlanApprovalModal .gate-review-body > .gate-review-actions {
    width: 44;
}

PlanApprovalModal .gate-review-body > .gate-review-actions--decisions {
    width: 50;
}
```
The rail is granted exactly 50 columns. With outer container borders (`border: solid $secondary;`, 2 cells) and padding (`padding: 0 1;`, 2 cells), the inner printable width is **46 columns**. 

#### 2. Arbitrary Hardcoded Truncation Thresholds
In `src/sase/ace/tui/modals/plan_decision_rows.py` (lines 110–118):
```python
if isinstance(memory, dict):
    ...
    if ask.strip():
        truncated = ask.strip()
        if len(truncated) > 60:
            truncated = truncated[:57] + "..."
        text.append(f"  {truncated}", style="dim")
else:
    truncated = ask.strip()
    if len(truncated) > 80:
        truncated = truncated[:77] + "..."
    text.append(truncated, style="dim")
```
The python builder truncates strings at **80 characters** (or 60 characters for memory rows), while the enclosing container is only **46 characters wide**! Consequently, string truncation never even triggers as intended; instead, Textual clips the text mid-word at column 42–44.

#### 3. Misuse of Textual `Button` for Complex Card Content
In `src/sase/ace/tui/modals/plan_decision_rows.py` (lines 328–338):
```python
def compose(self):
    for index, row in enumerate(self._rows):
        yield Button(
            self._row_label(index, row),
            id=f"plan-decision-{index}",
            classes="plan-decision-row",
        )
        yield Static("", id=f"plan-decision-detail-{index}", classes="plan-decision-detail")
```
A Textual `Button` is designed for short trigger labels ("Submit", "Cancel"). In Textual, a `Button`'s label does not support standard wrapping; text overflows are clipped (`overflow: hidden`). When an entire 7-line Rich `Text` block containing question, choices, radio glyphs, and rationales is stuffed into a `Button.label`, any line longer than 44 characters is clipped without wrapping.

Furthermore, focusing a `Button` applies Textual's default button focus styling across the entire multi-line block, creating an awkward, heavy block highlight.

#### 4. Height Choking by `max-height: 16`
In `src/sase/ace/tui/styles.tcss`:
```css
.plan-decision-rows {
    height: auto;
    max-height: 16;
}
```
An expanded decision takes 6–8 lines. Each collapsed decision takes 2–3 lines. With 4 decisions, the required height is `(1 * 7) + (3 * 2.5) + margins = 16–18` lines. The container hits `max-height: 16` immediately, cutting off the 4th decision. Because Textual does not render prominent scrollbar tracks inside tightly bounded sub-widgets, the reviewer is left unaware that further decisions exist below the fold.

---

## 3. Design Goals and Guiding Principles

To make decisions in gate panels look clean, legible, and professional, any new design must adhere to five principles:

1. **Zero Text Clipping (Guaranteed Legibility):** Every prompt question (`ask`), choice label, consequence explanation, rationale (`why`), and memory citation must wrap naturally and remain fully readable.
2. **Clear Information Hierarchy:** Reviewers must immediately perceive:
   - What the decision is about (question).
   - What options exist and what each option does (consequences).
   - Which option is currently selected.
   - What the default is and why the author chose it.
   - Any memory provenance or citations involved.
3. **Balanced Screen Real-Estate:** Terminals running SASE are typically 140–220 columns wide. The layout must intelligently allocate space: generous room for decision cards (~70–76 columns) while leaving ample room for Markdown plan reading (~80–110 columns).
4. **Preserved Keyboard Flow & Muscle Memory:** The existing vim-style navigation (`j`/`k` for decisions, `h`/`l` or arrow keys for cycling choices, `Space` for toggling, `r`/`R` for reset, `Enter` for approval) must remain instant, fluid, and intact.
5. **Synchronized Plan Context:** SASE's mechanism of scrolling `plan.md` to the matching `> [!decision] <id> = <key>` callout when a decision is focused is a powerful feature; the visual presentation should highlight and reinforce this connection.

---

## 4. Evaluation of Design Alternatives

We evaluate four structural approaches for presenting decisions in gate modals:

| Design Dimension | Approach A: Proportional Two-Pane with Decision Cards (Recommended) | Approach B: Three-Pane Split (Sidebar + Inspector + Plan) | Approach C: Top-Drawer Carousel / Header Grid | Approach D: Inline Document Interactive Decisions |
| :--- | :--- | :--- | :--- | :--- |
| **Layout Structure** | Left Rail (72–76 cols) + Right Document (1fr) | Left Nav (26 cols) + Center Inspector (58 cols) + Right Plan (1fr) | Top Decision Drawer (30% height) + Bottom Plan (70% height) | Left Nav (35 cols) + Embedded interactive widgets in Right Document |
| **Horizontal Space for Decisions** | **70–74 usable columns** (Standard text measure) | **54–56 usable columns** | Full modal width (~180 cols) | Full document width (~120 cols) |
| **Vertical Space for Plan** | **100% of body height** (~45–50 lines) | **100% of body height** (~45–50 lines) | **60–70% of body height** (Plan is squeezed vertically) | **100% of body height** |
| **Terminal Width Requirement** | Graceful from 110 to 220+ cols | Requires >= 160 cols; cramped below 140 cols | Works on narrow terminals, but wastes horizontal width | Works on any width |
| **Complexity & Implementation Risk** | **Low to Medium:** Refactors `PlanDecisionRows` & TCSS within existing modal architecture | **High:** Requires complete rewrite of `PlanApprovalModalViewMixin` layout and focus management | **Medium:** Changes vertical modal flow and interferes with verdict docking | **Very High:** Requires interactive form controls embedded inside Markdown syntax stream |
| **Cognitive Load on Reviewer** | **Low:** Clean visual hierarchy; familiar left-to-right review flow | **Medium:** Three vertical panes can feel visually busy | **High:** Vertical splits reduce readable plan context | **High:** Forces reviewer to hunt through 500 lines of plan to find decisions |

### Analysis of Trade-Offs:

- **Why Not Approach C (Top-Drawer)?** Terminal heights are scarce (often 40–55 lines). Dedicating 15–20 vertical lines to a top decision drawer leaves only 20–25 lines for `plan.md`. Constant vertical scrolling through the plan destroys readability.
- **Why Not Approach D (Inline Document)?** Plan Decisions must be reviewed and resolved *as a cohesive unit* alongside the final verdict. Scattering decision controls across a 600-line Markdown document forces the reviewer to hunt through headings. Furthermore, it complicates draft state serialization and keyboard navigation.
- **Why Approach A Over Approach B?** Approach B (Three-Pane) is tempting on an ultra-wide screen, but in terminals between 110 and 150 columns (common on laptops or split tmux panes), three vertical panes crowd out the plan document. Approach A provides 72–76 columns for the left rail—the exact typographical golden ratio for reading English prose (65–75 characters per line)—while leaving 100+ columns for the plan document.

---

## 5. Recommended Solution and UX Specification

### 5.1 Responsive Layout & Geometry

#### TCSS Rules:
Replace the fixed `width: 50;` rule with responsive, proportional styling:

```css
/* Responsive gate review rail */
PlanApprovalModal .gate-review-body > .gate-review-actions {
    width: 44;
}

/* Decisions rail: expand to 74 columns on standard/wide displays */
PlanApprovalModal.-gate-review-wide .gate-review-body > .gate-review-actions--decisions {
    width: 74;
    max-width: 42%;
}

/* Responsive fallback for medium displays (100-130 cols) */
PlanApprovalModal .gate-review-body > .gate-review-actions--decisions {
    width: 62;
}

/* Narrow displays (<100 cols): existing bottom dock remains */
PlanApprovalModal.-gate-review-narrow .gate-review-body > .gate-review-actions {
    dock: bottom;
    width: 100%;
    height: 48%;
}

/* Decision list container: remove max-height choke */
.plan-decision-rows {
    height: auto;
    max-height: 28; /* Increased to accommodate expanded card + collapsed pills */
    scrollbar-gutter: stable;
    padding: 0;
}
```

#### Why 74 Columns?
- Outer rail width: `74 cells`
- Rail border (`solid $secondary`): `2 cells`
- Rail padding (`0 1`): `2 cells`
- Inner usable width: **`70 cells`**
- In a 70-cell space:
  - Indented option lines have **64 characters** of text wrapping room.
  - Option descriptions wrap cleanly across 2 lines instead of clipping.
  - The plan document on the right retains **~110–130 cells** on standard 180–200 column terminals, preserving comfortable plan reading.

---

### 5.2 Widget Architecture: From `Button` to `PlanDecisionCard`

Replace the monolithic `Button` implementation in `plan_decision_rows.py` with a dedicated Textual component: `PlanDecisionCard` inside `PlanDecisionAccordion`.

```
PlanDecisionAccordion (VerticalScroll)
 ├── PlanDecisionCard [0] (Focused / Expanded)
 │    ├── CardHeader (ID pill, status badge, value pill)
 │    ├── QuestionText (Static, text-wrap: wrap)
 │    ├── OptionsGroup (Radio list with wrapped consequence text)
 │    ├── RationaleBox (Static, subtle border: why default)
 │    └── MemoryCitationBox (Static: note link, provenance, quote)
 ├── PlanDecisionPill [1] (Collapsed)
 ├── PlanDecisionPill [2] (Collapsed)
 └── PlanDecisionPill [3] (Collapsed)
```

Each card is a Textual `Container` (or `Static` with Rich renderables) capable of proper multi-line layout and semantic focus handling, rather than a single flattened button label.

---

### 5.3 Visual Design & Typographic Mockups

#### A. Expanded Active Decision Card (Focused)

```
┌─ [1/4] root ────────────────────────────────────── ● MODIFIED ─┐
│                                                                 │
│ Where should the relocated legacy tree (formerly ~/Sync) go?    │
│                                                                 │
│   ◉ db           ★ default                                      │
│     matches the existing $DB/projects/* checkout structure      │
│                                                                 │
│   ○ legacy                                                      │
│     names it as the preferred legacy path ~/legacy              │
│                                                                 │
│ ┌─ ★ Author's Rationale ──────────────────────────────────────┐ │
│ │ ~/.profile already calls this root $DB; matches existing    │ │
│ │ shell aliases and crontabs without path re-exports.         │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

#### Key Visual Improvements:
1. **Clear Header Frame:** Shows card index (`[1/4]`), identifier (`root`), and state pill (`● MODIFIED` in gold `#FFD700` if changed from default, or `★ DEFAULT` in dim cyan).
2. **Prominent, Uncut Question:** Styled in bold white/bright text, wrapping naturally across lines.
3. **Structured Choice Items:**
   - Active radio glyph `◉` in green/cyan.
   - Choice key (`db`) in bold.
   - `★ default` marker explicitly labeled.
   - Consequence label indented on the next line with `text-wrap: wrap`, dimmed for contrast.
4. **Dedicated Rationale Callout Box:** Rendered in a subtle bordered box (`border: round $surface-light`), making the rationale stand out without competing with the options.

---

#### B. Memory Decision Card with Citation & Provenance

When a decision originates from or affects memory:

```
┌─ [4/4] sync_policy ────────────────────────────── 🧠 MEMORY ────┐
│                                                                 │
│ Should Syncthing sync-conflict files be deleted automatically?  │
│                                                                 │
│   ☑️ yes          ★ default                                      │
│     purges ~400 stale conflict copies across ~/Sync             │
│                                                                 │
│   ⬜ no                                                         │
│     leaves conflicts intact for manual reconciliation           │
│                                                                 │
│ ┌─ 🧠 Memory Citation ────────────────────────────────────────┐ │
│ │ Note: [[gotchas.md]] · web · you asked                      │ │
│ │ "Clean up old conflict files left by Syncthing daemon"       │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

If memory provenance is unverified (e.g. `quote_not_found` or `claim_not_found`):
```
│ ┌─ ⚠ Memory Warning ──────────────────────────────────────────┐ │
│ │ ⚠ Quote not verified in note · Disabled until enabled by you│ │
│ └─────────────────────────────────────────────────────────────┘ │
```
The warning appears in high-visibility amber/yellow (`#FFAF00`), preventing accidental automated changes to unverified memory states.

---

#### C. Ultra-Compact Collapsed Decision Pills

When a decision is not focused, it should collapse into an ultra-compact **1-line or 2-line summary pill**. This ensures that even with 5 decisions, all collapsed items fit cleanly into the viewport!

```
○ 2. dotfiles      repoint ★  Should ~70 stow-style dotfile symlinks...
○ 3. conflicts     delete  ★  Should all ~400 Syncthing conflict files...
○ 4. old_tmp       nest    ★  Where should old_tmp temporary scratch go...
```

- Left marker: `○` (unfocused radio)
- Index & ID: `2. dotfiles`
- Current Value: `repoint` (highlighted)
- Status: `★` (default) or `●` (modified)
- Short prompt summary: Truncated to fit the remaining width with an ellipsis.
- Total height per collapsed item: **1 line**!

#### Vertical Math with 5 Decisions:
- 1 Expanded Card: ~12–14 lines
- 4 Collapsed Pills: 4 lines
- Header & Margins: 3 lines
- **Total Height Required:** ~20 lines!
This fits effortlessly into the 28-line viewport without hiding any decision!

---

### 5.4 Full Gate Review Modal Layout Mockup

Here is how the complete `PlanApprovalModal` looks with the proposed design on a standard 180-column terminal:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ sase tui (v0.17.1+2434)                                                    Plan Review  CLAUDE(opus)             │
├────────────────────────────────────────────────────────────────────────┬─────────────────────────────────────────┤
│ Actions                                                                │ plan.md                                 │
│   e ✏️ Edit plan  (Accepted only when 'sase plan validate' passes)      │                                         │
│ ────────────────────────────────────────────────────────────────────── │ > [!decision] root = db                 │
│ Decisions 4 · 🧠 1                                                     │ Throughout this plan `<root>` means     │
│ ┌─ [1/4] root ────────────────────────────────────── ★ DEFAULT ──────┐ │ `~/db` (`/home/bryan/db`), or `~/legacy`│
│ │ Where should relocated legacy tree (formerly ~/Sync) go?           │ │ if decision `root = legacy`. Both are   │
│ │                                                                    │ │ direct children of `~`, so retargeting  │
│ │   ◉ db           ★ default                                         │ │ a link means replacing its single       │
│ │     matches existing $DB/projects/* checkout structure             │ │ `Sync` path component with the root's   │
│ │                                                                    │ │ basename.                             │
│ │   ○ legacy                                                         │ │                                         │
│ │     names it as preferred legacy path ~/legacy                     │ │ ## Non-goals                            │
│ │                                                                    │ │ - Dissolving the legacy tree into       │
│ │ ┌─ ★ Rationale ──────────────────────────────────────────────────┐ │ │   chezmoi, or pruning dead X11-era      │
│ │ │ ~/.profile already calls this root $DB; matches existing       │ │ │   configs (xmonad, bspwm, termite).     │
│ │ │ shell aliases without path re-exports.                         │ │ │ - Committing or pushing inside legacy   │
│ │ └────────────────────────────────────────────────────────────────┘ │ │   checkouts under `<root>`.             │
│ └────────────────────────────────────────────────────────────────────┘ │                                         │
│   ○ 2. dotfiles   repoint ★  Should ~70 stow-style dotfile links...  │ ## Steps                                │
│   ○ 3. conflicts  delete  ★  Should all ~400 Syncthing conflict fi...│ ### 0. Capture state (read-only)        │
│   ○ 4. old_tmp    nest    ★  Where should old_tmp temporary scra...  │ 1. `mkdir -p ~/tmp/sync-removal`         │
│ ────────────────────────────────────────────────────────────────────── │ 2. Confirm `~/Sync` contains only       │
│ Verdict                                                                │    `old_syncthing_dir/` and logs...     │
│   ☑ 1 Launch coder   ☑ 2 Reject   ☐ 3 Feedback                        │                                         │
│   [ 1 Tale · defaults ]   [ 2 Reject ]   [ 3 Feedback ]                │                                         │
│   → coder + commit · root=db · dotfiles=repoint · conflicts=delete ... │                                         │
├────────────────────────────────────────────────────────────────────────┴─────────────────────────────────────────┤
│ j/k=Navigate  Space=Toggle  h/l=Choice  r=Reset  R=Reset all  Enter=Tale · defaults  Ctrl+S=Submit  e=Edit  q=Cancel    │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Notice the stark contrast with the current screenshot:
- **Left Rail Width:** Expanded to 74 columns. Every word of the question, options, descriptions, and rationales is legible.
- **Plan Document Pane:** Still has 106 columns of width—ideal for 80-column Markdown reading.
- **All Decisions Visible:** Decisions 1, 2, 3, and 4 are all visible at once.
- **Synchronized Highlighting:** When Decision 1 (`root`) is selected, the right pane scrolls to `> [!decision] root = db` and tints it green!

---

### 5.5 Interaction and Keyboard UX Specification

Reviewers spend significant time in gate review modals; interaction must be rapid, predictable, and ergonomically sound.

#### Keybindings & Shortcuts:

| Key Binding | Target | Action | Behavioral Details |
| :--- | :--- | :--- | :--- |
| `j` / `Down` | Accordion | **Next Decision** | Expands next decision card, collapses previous card, sync-scrolls plan document to matching callout. |
| `k` / `Up` | Accordion | **Prev Decision** | Expands previous decision card, collapses next card, sync-scrolls plan document. |
| `l` / `Right` | Active Card | **Next Choice** | Cycles to the next available option in the active card. Re-tints plan callout immediately. |
| `h` / `Left` | Active Card | **Prev Choice** | Cycles to previous option in the active card. Re-tints plan callout immediately. |
| `Space` | Active Card | **Toggle / Step** | For toggle decisions: flips `yes`/`no`. For choice decisions: advances to next choice. |
| `1` – `9` | Active Card | **Direct Select** | Direct shortcut to select choice 1, 2, 3... of the active decision without cycling. |
| `r` | Active Card | **Reset Decision** | Resets the active decision to author's default value (`default`). |
| `R` | Modal | **Reset All** | Resets all decisions in the modal back to default values. |
| `Enter` | Modal | **Submit Primary** | Submits primary verdict (e.g. `Tale · defaults`) with all current decision selections. |
| `Ctrl+S` | Modal | **Submit Active** | Submits the currently selected branch. |
| `e` | Modal | **Edit Plan** | Suspends modal to open `$EDITOR` on plan file. |
| `Ctrl+D` / `Ctrl+U` | Document | **Scroll Plan** | Scrolls the right plan document down/up by half a page. |
| `g` / `G` | Document | **Plan Top/Bottom**| Scrolls plan document to top / bottom. |
| `q` / `Esc` | Modal | **Cancel** | Dismisses modal without submitting (preserves draft state in `esc_drafts`). |

#### Mouse Affordances:
- Clicking any option in an expanded card selects it immediately.
- Clicking any collapsed decision pill expands it and focuses that decision.
- Clicking `[★ Reset]` on a modified decision restores its default.

---

## 6. Implementation Architecture & Migration Roadmap

To deliver this design cleanly into SASE with minimal disruption and zero regressions, we outline a four-step implementation plan.

### Step 1: TCSS & Rail Geometry Expansion
**File:** `src/sase/ace/tui/styles.tcss`
1. Update `PlanApprovalModal .gate-review-body > .gate-review-actions--decisions` width from `50` to `74` when `-gate-review-wide` is active.
2. Set responsive fallback to `62` when terminal width is between 100 and 130 columns.
3. Remove `max-height: 16` on `.plan-decision-rows`, replacing it with `max-height: 28; height: auto;`.
4. Ensure `.gate-review-document` maintains `width: 1fr; min-width: 70;`.

### Step 2: Refactoring `plan_decision_rows.py` to Card Architecture
**File:** `src/sase/ace/tui/modals/plan_decision_rows.py`
1. Deprecate `Button` widgets as row containers.
2. Implement `PlanDecisionCard` (a custom Textual container or compound `Static` with Rich formatting) that renders:
   - Header with ID, index, and status chip.
   - Wrapped question text with `text-wrap: wrap`.
   - Option lines with proper indenting and wrapped consequence descriptions.
   - Distinct rationale box (`border: round $surface-light`).
   - Memory citation block.
3. Implement `_collapsed_pill_text()`: single-line compact representation for inactive rows.
4. Remove arbitrary string truncation limits (`len > 80`, `len > 60`); rely on proper terminal text wrapping.

### Step 3: Keyboard and Focus Integration
**File:** `src/sase/ace/tui/modals/plan_approval_modal_controls.py`
1. Update `_gate_control_ids()` to bind focus to the new card widgets.
2. Add direct numeric choice selection (`1`..`9`) when focused on a choice decision.
3. Preserve existing `_apply_draft_edit()` hooks and draft caching in `esc_drafts`.
4. Verify synchronized scrolling (`_scroll_to_focused_decision()`) remains smooth.

### Step 4: Verification & Golden Screenshots
1. Test across terminal geometries:
   - 80x24 (narrow fallback: bottom dock)
   - 120x40 (medium width: 62-col rail)
   - 200x55 (wide screen: 74-col rail)
2. Verify with plans containing:
   - 1 single boolean toggle decision
   - 4–5 multi-choice decisions with long descriptions (e.g. reproducing `20261012_074036.png`)
   - Decisions with memory provenance and warnings (`quote_not_found`)
3. Update any affected visual golden screenshots with Conventional Commit trailer `UNRELATED_SCREENSHOT_UPDATES` if applicable.

---

## 7. Conclusion and Summary of Recommendations

The current defects in SASE TUI gate decision panels—ugly layout, mid-word text clipping, and missing decisions—are not fundamental limitations of terminal user interfaces. They are the direct consequence of:
1. Squeezing dense interactive choices into an arbitrary 50-cell column while 70 columns of terminal space sit empty on the right.
2. Forcing rich multi-line card content into single-line clipping `Button` widgets.
3. Artificially capping the decision list container at `max-height: 16`.

By widening the decision rail to **74 columns**, replacing `Button` with a proper **multi-line `PlanDecisionCard`**, adopting **compact 1-line collapsed pills**, and structuring the layout with **clear typographic hierarchy and wrapped text**, the gate review modal will transform from a cramped, frustrating bottleneck into a polished, executive-grade review surface that makes plan approval fast, clear, and confidence-inspiring.
