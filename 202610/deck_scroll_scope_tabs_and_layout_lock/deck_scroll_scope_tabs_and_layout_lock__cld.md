# Can I scroll to see the whole deck? Making deck scroll scope obvious (cld)

**Question.** How should the Agents-tab deck panel show, without ambiguity, whether
scrolling the focused deck reaches all of its content (spread) or only the current card
or block (paged)? The proposals under review are: (1) show card sub-tabs only when the
deck is actually paged; (2) add bright, clearly visible view badges; (3) replace the
`auto` / `fixed` words with a lock icon. Is this the best UX?

**Researcher:** cld · **Date:** 2026-10-19 · **Code basis:** `master` at `a9046529ca`

---

## TL;DR

- **Your diagnosis is right, and "tabs only when paged" is the most valuable part of
  the plan.** The real defect is that the most prominent element in the deck title, the
  tab strip with its reverse-video active tab and `2/2` counter, signals "paged" in
  every mode. The only element that says "spread" is one muted word. In narrow panels a
  spread deck even renders `‹ 2/2 › Reply`, which is a carousel with a page counter
  (§1.3). The fix is mainly structural, not about brightness.
- **Adopt, generalized:** navigation chrome (tabs, `N/M`, `‹ ›`) appears **if and only
  if** content is off this scroll page. Apply this to every deck. FINAL and RECORD also
  switch between spread and paged automatically, and they have no badge today.
- **Adopt, adjusted:** a solid view **chip**, shown loud only on the focused panel. It
  must not look like the active tab, and it is not the main signal. Showing it bright
  in both states carries no information on its own.
- **Adopt, carefully:** a lock replaces `auto` / `fixed`, and no lock means automatic.
  But `🔒` already means *read-only* or *private* elsewhere in this TUI. Put the lock
  **inside the view chip** and rename "fixed" to "locked" everywhere (palette, toast,
  help, docs) so the icon and the words agree.
- **Add what the plan is missing:** a **continuation cue at the bottom border** of a
  paged deck (`+1 card · Ctrl+J`). That is where the eye is when the reader decides
  "I'm done". It reuses this TUI's existing `+9 lines · ▾ d more` idiom. A badge in the
  title is the Caps Lock LED problem: it sits away from the locus of attention.
- **Recommended solution (§6):** a four-part design: (A) structural rule for tabs;
  (B) chip with lock; (C) bottom `+N cards` / `+N blocks` cue; (D) copy and vocabulary
  cleanup. The work is presentation-only (no `sase_core` change) and mostly lands in
  `titles.py`, `view_badge.py`, and `panel_chrome.py`. It can ship in two small phases.

---

## 1. How it works today (verified in code)

### 1.1 Three layouts, one policy

A Main or Files deck panel has a **deck view** (`DeckView` in
`src/sase/ace/tui/widgets/decks/model.py`). Plan `plan:202609/deck_views.md` (epic
`sase-1b1`, closed) defines it:

| Layout        | What one scroll page holds | Other content reached by |
| ------------- | -------------------------- | ------------------------ |
| `spread`      | every card (blocks inline) | scrolling                |
| `page cards`  | one whole card             | `Ctrl+J` / `Ctrl+K`      |
| `page blocks` | one block of one card      | `(` / `)`, `Ctrl+J/K`    |

The **policy** is `AUTO` or one fixed layout. `AUTO` uses `decide_render_mode()` in
`render_mode.py`: spread when the cards fit within `spread_max_screens` (default
**1.5** viewport heights), with 10% hysteresis. `P` cycles the fixed layouts. Only the
palette's **Deck view: automatic** returns a panel to auto (`commands/catalog.py:294`).

Two corrections to the premise ("the user can only scroll the whole deck when cards are
not split out"):

- There is a **second level**. In `page blocks`, scrolling covers *one block*, not even
  the whole card. The same "can I scroll to everything?" question applies inside a card.
- Not every deck has a badge. **FINAL and RECORD** also auto-switch between spread and
  paged (`panel_navigation.py`, `panel_record.py`, `document_transitions_apply.py:84`),
  but `view_policy`/`titles._badge_variants` gives them no badge (Main and Files only).
  **Tools is paged-only.** The "currently focused deck" can therefore be a deck whose
  scroll scope is completely unlabeled today.

### 1.2 The title shows tabs in every mode

`DeckPanelChromeMixin.refresh_chrome()` (`panel_chrome.py`) builds the tab list
(`_main_tabs()`, `_files_tabs()`, `_final_tabs()`, …) **unconditionally** and passes it
to `deck_title()` (`titles.py`). In spread mode, `_on_main_scroll_y()`
(`panel_interaction.py`) moves the highlighted "active" tab as you scroll. That makes
the strip a **scroll-spy**, but it is styled exactly like real tabs: reverse-bold accent
pill plus `N/M`.

The badge (`view_badge.py`) is `{layout} · {status}`. Plan D5 makes it *deliberately
quiet*: the layout word is in accent (not bold), `auto` is muted (`#888888`), and only
`fixed` is bold. ("The badge is quiet by default and loud only when the user has changed
it.")

### 1.3 What the title actually renders

I called the real `deck_title()` on `master` with a Main deck of `Context` and `Reply`,
the active card set to Reply, and the panel focused:

| Effective view      | width 80 / 44                                  | width 30                      | width 18       |
| ------------------- | ---------------------------------------------- | ----------------------------- | -------------- |
| spread · auto       | `◆ MAIN spread · auto ┃ Context │ Reply  2/2`  | `◆ MAIN S·A ┃ ‹ 2/2 › Reply`  | `MAIN S·A 2/2` |
| spread · fixed      | `◆ MAIN spread · fixed ┃ Context │ Reply  2/2` | `◆ MAIN S·F ┃ ‹ 2/2 › Reply`  | `MAIN S·F 2/2` |
| page cards · auto   | `◆ MAIN page cards · auto ┃ Context │ Reply  2/2` / `◆ MAIN cards · auto ┃ …` | `◆ MAIN C·A ┃ ‹ 2/2 › Reply` | `MAIN C·A 2/2` |
| page blocks · fixed | `◆ MAIN page blocks · fixed ┃ Context │ Reply  2/2` | `◆ MAIN B·F ┃ ‹ 2/2 › Reply` | `MAIN B·F 2/2` |

At every width, spread and paged differ by **one muted word or letter**. Everything
else is identical. In the goldens (`agents_deck_view_fixed_spread_120x40.png` vs
`agents_deck_view_auto_page_blocks_120x40.png`), the `Reply` pill and `2/2` are the
brightest things in both titles. In `agents_deck_view_split_narrow_120x40.png`, the
title reads `MAIN C·F 2/2` and `MAIN B·A 2/2`, which only someone who has read the docs
can decode.

---

## 2. Why it is still unclear: diagnosis

1. **The signals contradict each other, and the loudest one is wrong.** Tab-strip
   styling (reverse pill plus `N/M` plus `‹ ›`) is a learned signifier for "other
   panels exist elsewhere". The WAI-ARIA tabs pattern defines tabs as layered panels
   with **one panel displayed at a time**. Practitioners warn that tab-styled navigation
   which actually scrolls or jumps is misleading (Adam Silver; Angular Components
   #23706). In spread mode the strip breaks that contract, and the muted badge cannot
   outvote it.
2. **The badge spends half its weight on secondary information.** `spread · auto` gives
   equal typographic weight to *what scrolling covers* (primary) and *who chose it*
   (secondary). The decoded tiny form `S·A` is two arbitrary letters.
3. **The cue is far from the locus of attention.** Raskin's classic example is the Caps
   Lock LED: users watch the document, not the indicator, so a correct indicator in
   the wrong place still produces mode errors. When the reader decides whether they have
   seen everything, they are looking at the **bottom** of the body, not the top border.
4. **The paged card's end creates an illusion of completeness.** Tognazzini's term, as
   popularized by NN/g: people stop scrolling when the screen looks finished, and solid
   horizontal lines read as "the end". A paged card ends at the panel border with
   nothing saying "1 more card". That is the costly failure, because content is missed.
   The opposite confusion (spread mistaken for paged) mostly costs extra `Ctrl+J`
   presses.
5. **Coverage gap.** FINAL and RECORD spread and page with no badge at all. Their tab
   strips show in both modes too.

---

## 3. Critique of the three proposals

### 3.1 "Only show card sub-tabs when actually paged": yes, and generalize it

**Why it is right.** It makes the strongest visual element *mean* the thing in
question. It also matches well-established precedent:

- Vim's default `showtabline=1` shows the tab line "only if there are at least two tab
  pages". WezTerm (`hide_tab_bar_if_only_one_tab`) and libadwaita's `AdwTabBar`
  (autohide by default) do the same.
- SASE already follows this rule: the Agent Tab strip "shows once two or more tabs
  exist" (glossary: Agent Tab). In spread there is effectively one page, so no strip.

**Generalize it.** Hide **all** pagination chrome in spread: tabs, the `N/M` counter,
and the compact rung's `‹ N/M ›` arrows. Apply the rule to **every deck** (Main, Files,
FINAL, RECORD). Tools is paged-only, so it always keeps its tabs. This gives one
sentence a user can learn: *"If you see tabs, other cards are off-page; if you don't,
scroll shows everything."*

**What you lose, and why it costs little:**

| Lost in spread                 | Why it is cheap / replacement                                                                                                                      |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Card inventory (names)         | Titled rules (`━━ ◆ Reply ━━━`, `separators.py`) mark every card in the body. Replace the strip with `all N cards`.                                |
| Scroll-spy ("you're in Reply") | Under AUTO a spread is at most **1.5 screens** by construction, so most of the deck and usually a separator are always visible. See below for fixed spread. |
| FINAL status strip             | FINAL instance tabs are `<id> <glyph>` (`final/document.py:56`), so the strip doubles as a status strip. The subtitle's `final <glyph>` segment and the cards in the body still show status. This loss is real but small (see §6.6). |
| Mouse targets                  | None. Title tabs are not clickable (`DeckPanel.on_click` only requests focus).                                                                    |

**Edge cases to design for:**

- **Fixed spread of long content** (for example Files 20 files × 2,000 lines, which
  plan D10 benchmarks). Here the scroll-spy matters. Optionally keep a single
  "you-are-here" label styled unlike a tab (`§ src/app.py`, no pill, no `N/M`), and
  only when the spread is taller than the viewport.
- **One-card decks** (`card_count <= 1` is always spread). Show the card name as plain
  text (`◆ MAIN · Summary`) with no chip, because nothing is off-page and there is no
  choice to make (`P` is unavailable).
- **Partial paints during `j`/`k`.** The badge is already held across partial Main
  paints (`_chrome_view`, `_held_chrome_views`). Tab visibility **must be derived from
  the same held view**, or the strip will flicker on and off while you navigate.
- **Auto flips while an agent streams** (spread → paged once content passes 1.65
  screens). With this rule the tabs *appear*. That structural change makes a good,
  silent notification, and no toast is needed.

### 3.2 "Bright, clearly visible badges": partially

- **You would be reversing an explicit design decision** (D5: "quiet by default, loud
  only when changed"). That is justified: D5 assumed the rest of the title was neutral,
  and §1.3 shows it was not. But note it as a deliberate reversal.
- **Brightness is not the signal.** If both spread and paged get equally bright badges,
  brightness tells the user nothing; only the word differs. Once tabs appear only when
  paged, the *structure* of the title answers the question pre-attentively. The chip
  then serves as (a) a stable place to look, (b) visible feedback for `P`, and (c) a
  place for the lock.
- **Make it a solid chip on the focused panel only.** Use uppercase bold dark text on
  the deck accent, the same visual family as the existing `ZOOM` chip
  (`ZOOM_CHIP_STYLE = "bold #1a1a1a on #FFD700"` in `titles.py`). Unfocused panels keep
  dim text with no fill, so focus stays legible in splits. Reverse/fill attributes
  survive monochrome captures, so meaning still does not depend on color alone.
- **The chip must not look like the active tab.** Today the active tab is
  `reverse bold {accent}`. A reverse-accent chip next to a reverse-accent tab pill
  would read as two selected tabs. Distinguish them by case (uppercase chip vs
  title-case tabs), by the `┃` separator, and optionally by half-block end caps on the
  chip.
- **Don't color-code paged as a warning** (amber). Paged is the *common* state for real
  agents, because Context + Reply usually exceed 1.5 screens. Permanent warning colour
  becomes banner noise, and it would compete with the deck accents.

### 3.3 "Lock icon instead of auto/fixed": yes, with care

**Why it's good.** The closest precedent is exact: iOS **rotation lock**, where no icon
means auto-rotate and a padlock-in-arrow means the orientation stays as chosen. Camera
"AE-L/AF-L" uses the same idea. *Absence means default*, so the common case shows
nothing and the badge loses 5–7 cells (`· auto` / `· fixed`).

**Caveats:**

1. **Semantic collision.** `🔒` already means **read-only** in this TUI
   (`_prompt_input_bar_title.py:145`, `existing_definition_finder_modal.py:41`) and
   **private** for bead attachments (`bead/attachment_presentation.py:23`). Next to
   `◆ MAIN`, a bare padlock can read as "this deck is read-only". **Mitigation:** draw
   the lock *inside* the view chip (`SPREAD 🔒`), so it attaches to the layout word, not
   the deck. `📌` is not a better choice: it already marks pinned stash rows
   (`prompt_stash_row.py:15`).
2. **Vocabulary must follow the icon.** If the icon is a lock, the words should be
   "locked" / "unlock", not "fixed" / "automatic". That affects the palette labels
   (`commands/catalog.py:294-297`), the teaching toast (`_panel_detail.py:224`), the
   help row (`agents_main_sections.py:77`), and the docs. Otherwise users meet three
   names for one state.
3. **Terminal rendering is safe for width but not for style.** U+1F512 has default
   emoji presentation and East Asian Width W, with no VS16 needed. That avoids the
   VS16 width bugs common in tmux and other terminals. Rich's `cell_len` returns 2,
   and the visual renderer bundles Noto Emoji. However, **colour emoji ignore foreground
   and usually ignore dim**, so an unfocused panel cannot dim its lock. That is
   acceptable, since a locked layout is sticky state worth seeing on every panel.
   Verify it in kitty and tmux.
4. **A visible lock invites "how do I unlock?"** Today only the palette unlocks. Make
   the first-lock toast name it (`Main view locked 🔒 · palette “Deck view: automatic”
   unlocks`, 60 cells). The prior plan already named the reopen condition for a
   dedicated reset key ("if resets prove frequent"). A visible lock makes that more
   likely, so track it.
5. **Keep the non-policy statuses as words.** `spreading…` and `spread unavailable` are
   not auto/fixed. They describe a pending or blocked request, so they stay text
   (muted, and warning tone for unavailable).

---

## 4. Adjustments to the requirements (called out explicitly)

| #  | Adjustment                                                                                                                                                                                                                                                         | Why                                                                                  |
| -- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| A1 | **Generalize the tab rule** to all pagination chrome (tabs, `N/M`, `‹ ›`) and to all decks (Main, Files, FINAL, RECORD). Tools stays tabbed because it is paged-only.                                                                                              | One learnable rule. FINAL/RECORD have the same ambiguity and no badge.               |
| A2 | **Add a bottom-border continuation cue** for paged decks: `+N cards · Ctrl+J`, plus `+N blocks · ( )` in page blocks. Optionally bold it when the reader is scrolled to the bottom.                                                                                 | Locus of attention / illusion of completeness. Reuses the `+9 lines · ▾ d more` idiom from `agent_header_panel.py`. |
| A3 | **Cover the block level**: the cue counts off-page blocks; keep the rail's `page N/M` / `all N` cue at more width tiers than today (widest tier only).                                                                                                           | The same question applies inside a card in page blocks.                              |
| A4 | **The chip is not the main signal.** Make it solid on the focused panel, distinct from the active-tab pill, and not color-coded by state.                                                                                                                           | Brightness in both states carries no information; structure does.                    |
| A5 | **Rename "fixed" to "locked"** everywhere the lock appears (palette, toast, help, docs).                                                                                                                                                                            | Icon and words must agree; 🔒 is otherwise ambiguous with read-only.                 |
| A6 | **Show the chip only where a choice exists** (Main and Files with 2+ distinct layouts). Other decks get the structural rule plus `all N cards` and the bottom cue, but no chip.                                                                                    | Keeps "chip = a view you control". Avoids a meaningless `PAGED` chip on Tools.       |
| A7 | **One-card decks show no chip and no tabs**; the card name is plain text.                                                                                                                                                                                          | Nothing is off-page and there is nothing to choose.                                  |

---

## 5. Alternatives considered

| Alternative                                                                                                                         | Verdict                                                                                                                                                                                                                                                                                   |
| ----------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Go modeless:** always render one continuous document; virtualize long cards; `Ctrl+J/K` only jump; folds (`za`) collapse cards.   | The ideal per Raskin, since the best mode indicator is no mode. Not now: paging exists for render cost (D10 budgets, 14k-line Replies) and focused reading, and the deck-views epic just landed. **Reopen** if Textual virtualization makes a 14k-line spread paint within the D10 budgets. |
| **Keep tabs in spread, restyle as a TOC** (no pill, `·` separators, caret for current).                                             | Too subtle. You asked for "much clearer", and a restyled strip still reads as tabs at a glance.                                                                                                                                                                                         |
| **Scope-worded chip** (`↕ ALL` / `↕ CARD` / `↕ BLOCK`) instead of layout names.                                                    | Answers the question more literally, but adds a second name for each layout (glossary, palette, persistence, docs all say spread / page cards / page blocks). Keep it as the fallback if user testing still shows confusion after §6.                                                     |
| **Semantic colours** (amber for paged, green for spread).                                                                           | Rejected: paged is the common state, so amber becomes noise and clashes with deck accents (§3.2).                                                                                                                                                                                       |
| **In-body end-of-card marker** (`── end of Context · Ctrl+J → Reply ──`).                                                          | The strongest cue for the illusion of completeness, but it changes the document. That affects measurement, search corpus, copy, reading anchors, and the bottom-pin follow behaviour. The border cue gets most of the benefit at near-zero risk. Revisit only if the border cue proves insufficient. |
| **Vim-style position readout** (`All` / `Top` / `42%` / `Bot`).                                                                    | Shows where you are *within the scroll region*, not what the region contains. The scrollbar already does that. Not needed.                                                                                                                                                              |
| **Toast on every auto spread↔paged flip.**                                                                                          | Rejected: noisy during `j`/`k`. The structural title change is the notification.                                                                                                                                                                                                         |

---

## 6. Recommended solution

### 6.1 The rule (put this sentence in the docs)

> **Tabs mean pages.** A deck panel shows card tabs, a `N/M` position, and a
> `+N cards` cue only when some of the deck is off this page. With no tabs, scrolling
> shows the whole deck.

### 6.2 Title grammar

Notation: `[SPREAD]` is the solid chip (uppercase, bold, dark text on the deck accent;
the brackets are not drawn). `«Reply»` is the active tab (reverse video, as today).
Widths were measured with Rich `cell_len`.

**Spread** (2+ cards). No tabs, no `N/M`, no arrows:

```text
◆ MAIN  [SPREAD]  all 2 cards                   27 cells
◆ MAIN  [SPREAD 🔒]  all 2 cards                30 cells   (locked)
◆ MAIN  [SPREAD]  all 2                         21 cells   (short)
MAIN [S]  /  MAIN [S🔒]                         8 / 10     (micro)
```

**Page cards / page blocks.** Tabs are present and mean pages:

```text
◆ MAIN  [PAGE CARDS]  ┃ Context │ «Reply»  2/2           42 cells
◆ MAIN  [PAGE BLOCKS 🔒]  ┃ Context │ «Reply»  2/2       46 cells (locked)
◆ MAIN  [CARDS]  ┃ ‹ 2/2 › Reply                         30 cells (compact)
MAIN [C] 2/2  /  MAIN [B🔒] 2/2                          12 / 14  (micro)
```

Compared with today (`◆ MAIN spread · auto ┃ Context │ Reply  2/2`, 43 cells), the
spread title is **shorter**, and the paged titles are the same width or narrower.
Removing `· auto` / `· fixed` pays for the chip padding, so the existing width ladder in
`deck_title()` keeps its shape. Only the spread branch gets its own rungs:
chip + `all N cards` → chip + `all N` → micro chip.

**Optional (fixed long spread only):** when the spread is taller than the viewport,
append a you-are-here label with no pill: `◆ FILES [SPREAD 🔒] all 20 · § src/app.py`.

### 6.3 Chip style

- Focused: `bold #1a1a1a on {accent}`, in the same family as `ZOOM`. Unfocused: `dim`,
  no fill.
- Tiers: `SPREAD` / `PAGE CARDS` / `PAGE BLOCKS` → `SPREAD` / `CARDS` / `BLOCKS` →
  `S` / `C` / `B`. These are today's short/tiny words, uppercased.
- Pending and blocked Files states stay worded after the chip: `[CARDS] spreading…` and
  `[CARDS 🔒] spread unavailable`. The lock means the *policy* is locked; the words
  explain why the picture differs.
- The D5 label rule is unchanged (a vacuous locked request shows the requested name).

### 6.4 Lock

- `🔒` inside the chip when `policy is not DeckView.AUTO`; nothing when auto.
- Copy changes: palette `Deck view: automatic (unlock)`, `Deck view: spread (locked)`,
  and so on. Toast: `Main view locked 🔒 · palette “Deck view: automatic” unlocks`
  (60 cells, under the 70 limit). Help row: `Lock deck view (palette unlocks)` (32
  cells, exactly the `CONTENT_WIDTH - 16 - 2` limit).

### 6.5 Bottom-border continuation cue (paged only)

Lead the subtitle with a status segment. `deck_subtitle()` already keeps `status` and
drops the switcher counts, then the switcher, when space is short:

```text
+1 card · Ctrl+J  main 2 · files 0 · tools · final 0 · record      (page cards)
+3 blocks ( ) · +1 card Ctrl+J  main 2 · …                          (page blocks)
+4 files · Ctrl+J  1-400 of 2000 lines · E editor                    (Files paged)
```

- Counts are *off-page* items: other cards (`len(cards) - 1`), and in page blocks the
  other blocks of the active card. Key names come from the keymap registry
  (`next_deck_card`, `next_card_block`), as `_deck_switch_hint()` already does.
- Muted by default. **Optionally bold accent when the paged scroll is at the bottom**
  (`scroll_y >= max_scroll_y`), so that at the "am I done?" moment the panel says "not
  yet". Refresh chrome only when that boolean flips, never per scroll tick (the
  `tui_perf.md` rules on event-loop work).
- Spread shows no cue. Its absence is part of the signal.

### 6.6 Other decks

- **FINAL / RECORD:** the tab rule and the `all N cards` text apply; no chip and no
  lock (they have no policy). FINAL keeps its status signal through the subtitle's
  `final <glyph>` segment. If losing per-instance glyphs in a spread FINAL title turns
  out to matter, show them as a plain glyph run with no names and no pill
  (`⊛ FINAL  all 4 cards ✓ ✓ ✗ ⋯`).
- **Tools:** unchanged (always paged, always tabbed), plus the bottom cue.

### 6.7 Docs and memory

- `docs/reference/tui/agent-statuses.md`: rewrite the "Agent data decks and cards"
  paragraph and **Deck Views → The badge / `P` / Palette** for chip, lock, tab rule,
  and bottom cue. `docs/reference/tui/agents-main-deck.md`: update the `Ctrl+J`/`Ctrl+K`
  paragraph. Read `docs_writing.md` first.
- The glossary strand `agent-data-card` describes spread vs paged. Add the "tabs mean
  pages" sentence through `/sase_memory_write`; do not hand-edit it.

### 6.8 Implementation map (all presentation-only; no `sase_core` change)

| File                                                   | Change                                                                                                                                                                                                                                                                         |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `widgets/decks/view_badge.py`                          | `badge_variants()` returns chip `Text` (long/short/tiny). Drop the `auto`/`fixed` words. Append `🔒` when `policy is not AUTO`. Keep the PENDING/BLOCKED words.                                                                                                                 |
| `widgets/decks/titles.py`                              | `deck_title(..., paged: bool)`. When not paged, use new spread rungs (chip + `all N cards`, no tabs, no `N/M`, no `‹ ›`). Paged rungs unchanged except for the chip. A one-card deck renders name + plain card title.                                                            |
| `widgets/decks/panel_chrome.py`                        | In `refresh_chrome()`, compute `paged` per deck: Main/Files from the **held** `ResolvedView.shown` (consistent with the chip during partial paints); FINAL/RECORD from `_render_mode`; Tools always `True`; `len(tabs) <= 1` → `False`. Build the continuation status and pass it to `deck_subtitle(status=…)`, joined with the Files line status. |
| `widgets/decks/panel_interaction.py`                   | In spread, keep updating `_main_active_card` (anchors and `P` use it), but skip `refresh_chrome()` unless the optional `§` label is shown. If you adopt the at-bottom emphasis, add a paged at-bottom watcher that refreshes chrome only when the value flips.                     |
| `commands/catalog.py`, `actions/agents/_panel_detail.py`, `modals/help_modal/agents_main_sections.py` | "locked" / "unlock" copy (§6.4).                                                                                                                                                                                                                         |
| `widgets/decks/block_rail.py` (A3, optional)           | Keep the `page N/M` / `all N` cue at the windowed tier too.                                                                                                                                                                                                                    |

### 6.9 Tests and goldens

- Unit: `tests/ace/tui/widgets/decks/test_deck_titles.py` (spread rungs have no `│`,
  no `N/M`, no `‹`; the lock appears only when locked; width ladder),
  `test_deck_chrome.py` (paged derivation, held view during partial paints, FINAL and
  RECORD), `test_deck_view_policy.py`, `test_final_deck_shell.py`, and the palette,
  help, and toast copy.
- Pilot: an auto flip from spread to paged makes tabs appear without flicker during
  `j`/`k` (`test_deck_view_main_pilot.py`).
- Visual: most `agents_deck_view_*` and `agents_decks_*` goldens re-baseline
  (`test_ace_png_snapshots_agents_deck_views.py`, `…_agents_decks.py`). Follow the
  `just fix-tui-screenshots` inspection contract in `tui_screenshot.md`. Add one golden
  for spread vs paged side by side in a split and one for the narrow micro tier.
- D5's acceptance test still applies, rephrased: *with the body covered, the title
  alone tells you whether scrolling reaches the whole deck.*

### 6.10 Phasing

1. **Phase 1 (small): structure, chip, lock.** A1, A4–A7, plus copy and docs. This
   alone fixes the contradictory-signal bug.
2. **Phase 2 (small): bottom continuation cue (A2)**, the optional at-bottom emphasis,
   and the rail cue tiers (A3).
3. **Deferred:** the `§` you-are-here label for long locked spreads; an in-body
   end-of-card marker; a dedicated unlock key (if palette unlocks prove frequent); the
   modeless continuous document (if virtualization meets the D10 budgets).

### 6.11 Risks

- **Title churn during `j`/`k`.** The title changes shape as you move between short and
  long agents. That is intended (it is the information), and the chip's fixed position
  right after the deck name gives the eye an anchor. Holding chip and tabs together
  across partial paints prevents flicker.
- **Emoji styling.** The lock cannot be dimmed in unfocused panels (§3.3). Check it in
  kitty and tmux. If it looks wrong, the fallback is the word `lock` inside the chip.
- **Lost scroll-spy in long locked spreads.** Covered by the optional `§` label.
- **Golden churn.** Large but mechanical.

### 6.12 Questions to settle before planning

1. Do you accept the **"fixed" → "locked"** rename across palette, toast, help, and
   docs? (Recommended; the icon implies it.)
2. Should the chip appear on **FINAL / RECORD** for consistency even without a policy?
   (Recommended: no, per A6.)
3. Do you want the **at-bottom emphasis** of the continuation cue in Phase 2, or is a
   static muted cue enough?

---

## Sources

- W3C WAI-ARIA Authoring Practices, [Tabs Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/): tabs show one panel at a time.
- Adam Silver, [Avoiding tab styles for navigation](https://adamsilver.io/blog/avoiding-tab-styles-for-navigation/), and [angular/components#23706](https://github.com/angular/components/issues/23706): tab-styled links that behave differently mislead.
- NN/g, [Why Didn't People Scroll? The Illusion of Completeness](https://www.nngroup.com/videos/illusion-completeness/); [Liferay: illusion of completeness](https://liferay.design/articles/best-practices/illusion-of-completeness); [St Andrews digital comms summary](https://digitalcommunications.wp.st-andrews.ac.uk/2020/09/21/scrolling-and-the-illusion-of-completeness/): solid lines read as "the end"; cut-off content invites scrolling.
- Raskin Center, [Modes are still harmful](https://www.raskincenter.org/ideas/modes-are-harmful/) (the Caps Lock LED and the locus of attention); NN/g, [UI Modes and Modals](https://www.nngroup.com/videos/ui-modes-modals/); Bill Buxton, [Mode errors](https://billbuxton.com/ModeErrors.html).
- Vim `showtabline` (default 1, tab line only with ≥2 tab pages), via [denops option docs](https://jsr.io/@denops/std/doc/option/~/showtabline); WezTerm [`hide_tab_bar_if_only_one_tab`](https://wezterm.org/config/lua/config/hide_tab_bar_if_only_one_tab.html); libadwaita [`TabBar:autohide`](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.3/property.TabBar.autohide.html).
- Vim `ruler` (`All` / `Top` / `Bot` / `%`), via [denops option docs](https://jsr.io/@denops/std@7.0.0/doc/option/~/ruler).
- iOS rotation lock: [BGR: the lock icon next to the battery](https://bgr.com/2204821/what-does-the-lock-icon-next-to-battery-mean-iphone/); [Apple Community thread](https://discussions-kr-prz.apple.com/thread/250947318).
- Terminal emoji width: [Darren Burns, Terminal support for emoji](https://darrenburns.net/posts/emoji-in-the-terminal/); [Jeff Quast, terminal character width](https://www.jeffquast.com/post/perfecting-terminal-character-width-using-correction-tables/); [ucs-detect tmux results](https://ucs-detect.readthedocs.io/_sources/sw_results/tmux.rst.txt).
- SASE internal: `plan:202609/deck_views.md` (D1–D10); `research:202609/deck_card_paging_ux/deck_card_paging_ux.md`; code under `src/sase/ace/tui/widgets/decks/` (`titles.py`, `view_badge.py`, `view_policy.py`, `panel_chrome.py`, `panel_interaction.py`, `render_mode.py`, `separators.py`); visual goldens `tests/ace/tui/visual/snapshots/png/agents_deck_view_*`.
