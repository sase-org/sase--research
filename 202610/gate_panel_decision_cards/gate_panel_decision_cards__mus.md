# Gate Decisions Panels in the TUI: Beauty Pass and Cutoff Fix

> Researcher mus · 2026-10-12 · Independent TUI design research on the
> Decisions section of the Plan Review gate modal (and gate rails generally).
> Prompted by `~/tmp/screenshots/20261012_074036.png`, where decision rows in
> the left rail look cramped and decision text is cut off mid-word.

## Question

How should the TUI render reviewer decisions in gate panels so that every
row is legible at a glance, nothing is ever cut off mid-word, and the panel
looks deliberate rather than squeezed in — without changing decision
semantics, keybindings, or the verdict flow?

## Bottom line

**Keep the current information architecture; fix the container, not the
content.** The Decisions-above-Verdict rail introduced by the recent
Plan-Decisions work is the right structure. What is wrong is purely
presentational, and it has three compounding causes:

1. The rail is a fixed 50 cells wide, of which ~6 are chrome, leaving ~44
   for text — while collapsed rows assume ~62 columns of text.
2. Each decision row is a Textual `Button`, whose default chrome
   (border/padding, `min-width: 16`) eats further width and whose label
   rendering crops long lines instead of wrapping them.
3. Collapsed rows pre-truncate the question to 60/80 characters in Python,
   so even a wider panel would still show severed sentences.

The recommended fix is a **wrap-first row design**: responsive rail width,
borderless wrapping row widgets with real focus highlighting, word-boundary
two-line clamp for collapsed asks, full wrapped ask plus inline choices for
the focused row, and no character-count truncation anywhere. Details in
"Recommended solution and UX" below.

## What the screenshot shows

The capture is a Plan Review modal (`PlanApprovalModal`, `sase tui
v0.17.1+2434`) with four decisions (`root_db`, two more choice rows,
`conflicts_delete`-style rows) and a docked Verdict section:

- **Row 1** (`root db`): the question reads "Where should the relocated
  legacy tree (f…" — severed mid-word, running underneath the scrollbar.
  No ellipsis is visible; the text simply collides with the rail edge.
- **Rows 2–4** (`dotfiles repoint`, `conflicts delete`, …): same pattern —
  "Should the ~70 stow-style dotfile symlink…", "Should all ~400 Syncthing
  *.sync-conflict…" — each clipped at the rail edge.
- **Row chrome**: every row sits in its own grey block (default `Button`
  styling), which reads as visual noise next to the clean document pane.
  Only the focused row earns its grey; the rest should be quiet text.
- **Density imbalance**: the document pane (right, ~3/4 of the modal) is
  airy and beautifully syntax-tinted, while the rail compresses four
  decisions plus the full Verdict block into a ~50-cell strip. The panel
  that carries the actual decision work looks like an afterthought.

Notably, the cutoff is *not* the Python-side `"..."` truncation doing its
job — it is the widget cropping text the Python code already shortened.
Two truncation mechanisms stack, and neither respects word boundaries or
the real available width.

## Root causes (verified against the tree)

All paths relative to the sase checkout.

### 1. Fixed rail width vs. assumed text width

`src/sase/ace/tui/styles.tcss`:

- `.gate-review-body > .gate-review-actions` is `width: 42`
  (line 1766–1771); the decisions variant raises it to `width: 50`
  (line 1779–1781).
- The rail also carries `border: solid` (2 cells), `padding: 0 1`
  (2 cells), and `scrollbar-gutter: stable` (~2 cells) (line 1820–1824).
  Usable text width is therefore **~44 cells**, shrinking further when a
  decision row draws its own chrome inside.

`src/sase/ace/tui/modals/plan_decision_rows.py`, `_collapsed_row_text`
(line 69–119):

- Memory rows truncate the ask at **60 characters** plus a 2-space indent
  (line 110–113); non-memory rows at **80 characters** (line 115–118).
- 62 assumed columns into ~44 (or fewer) real columns guarantees the
  mid-word severing seen in the screenshot. The `"..."` the code appends
  is itself cropped off, so the user cannot even tell text is missing.

### 2. Rows are Buttons, and Buttons crop

`plan_decision_rows.py` `compose` (line 326–337) yields one `Button` per
decision; `refresh_rows` (line 348–364) rewrites each button label on
every focus change. But:

- Textual 8.0.1's `Button` defaults (verified in the installed package)
  include `width: auto; min-width: 16` plus default border/padding
  chrome. `.plan-decision-row` in `styles.tcss` (line 1788–1791) sets only
  `height: auto; text-align: left` — it never clears the button chrome,
  never sets `width: 1fr`, never enables wrapping.
- The widget therefore sizes itself, draws grey button blocks around
  every row, and *crops* overlong label lines at the rail edge instead of
  reflowing them. A `Static` would wrap; a `Button` does not. The
  screenshot's grey blocks and hard-clipped text are exactly this.
- Functionally the buttons are unnecessary: `PlanDecisionRows` already
  owns `focused_index`/`focused_id`, moves focus with `j/k`, and handles
  `Button.Pressed` only to *set focus* (line 369–377). Real widget focus
  buys nothing here — focus-by-index plus click-to-focus on a static row
  preserves every behavior.

### 3. Information hierarchy fights for one line

The collapsed first line packs `{glyph} {id}  {value}{●}` in bold, then
spends the second line on a provenance echo (`🧠 … · you asked`) that
repeats the decision id when no note names exist
(`f"🧠 {', '.join(names) if names else decision_id}"`, line 100). On a
44-cell rail, the provenance line and the ask compete; the ask — the one
line the reviewer must read to decide — loses.

Secondary issues worth fixing in the same pass:

- **Emoji cell widths**: `☑️`/`⬜` are 2-cell emoji with platform-variable
  shaping; mixed with 1-cell `◉`/`○`/`●`/`★` they make columns wobble.
  (Keep the vocabulary — see below — but stop relying on alignment.)
- **Verdict squeeze**: `#plan-verdict` is `dock: bottom` inside the same
  rail (`styles.tcss` line 1793–1796) with rows capped at `max-height: 16`
  (line 1783–1786). On short terminals the verdict block crushes the row
  area from below while the document pane scrolls freely.
- **Scrollbar collision**: `scrollbar-gutter: stable` reserves space, but
  cropped button labels render *under* the reserved gutter visually, which
  is why text appears to run beneath the orange scrollbar in the capture.
- **No snapshot coverage**: no test in `tests/` references
  `_collapsed_row_text`, `PlanDecisionRows`, or `plan-decision-row`, so
  this regression had no golden to catch it. (Absence verified by search;
  changing the truncation is therefore test-safe, but new goldens should
  be added with the fix.)

## Design principles

1. **The rail serves the decision, not the document.** Reviewers approve
   `approve+commit` essentially always; the cheapest correct action is a
   glance that confirms "these are all the defaults I expect" plus Enter.
   Every row must answer *what am I being asked, what is currently
   selected, and is it still the default* without scrolling or expanding.
2. **Never truncate characters; clamp lines.** The widget always knows
   its real width. Wrap to that width, clamp collapsed asks to two lines
   at a word boundary with a real ellipsis, and show the full ask on the
   focused row. Character counts in Python cannot know the terminal width
   and must go.
3. **Focus is a highlight, not a widget.** One focused row, fully
   expanded; all others quiet two-to-three-line summaries. No per-row
   button chrome, no competing borders — the rail has one border already.
4. **Don't churn the visual language.** The `◉ ○ ● ★ 🧠` vocabulary just
   shipped across TUI/CLI/Telegram and is covered by the cross-surface
   contract. The beauty pass keeps every glyph and meaning; it changes
   spacing, wrapping, and emphasis only.
5. **Narrow terminals degrade to stacked, not to clipped.** The existing
   `-gate-review-narrow` breakpoint (modal width < 100, actions docked
   bottom at 48% height) is the right mechanism; the fix must verify
   decisions read well there too, where width is plentiful but height is
   the constraint.

## Options considered

| Option | Shape | Verdict |
|---|---|---|
| A. Widen rail + smaller text | Bump fixed width 50 → 60, keep Buttons | Rejected: steals doc space on small terminals, keeps crop behavior, truncation stays wrong |
| B. Wrap-first rows (recommended) | Responsive width, borderless wrapping rows, line-clamp | Recommended: fixes cutoff at any width, removes chrome noise |
| C. Third column for Decisions | Verdict rail · Decisions column · document | Rejected: verdict and decisions are one flow; three columns starve the doc below ~180 cells |
| D. Decisions as overlay sheet | `h` opens full-width decision list | Rejected as primary: hides decisions behind a keystroke — the exact failure the Decisions section was built to end; fine as a future extra, not the fix |

## Recommended solution and UX

### Layout

- **Responsive rail width.** Replace the fixed `width: 50` for
  `.gate-review-actions--decisions` with a proportional width bounded on
  both sides, e.g. `width: 32%; min-width: 52; max-width: 72;`. Rationale:
  52 guarantees ~46 usable cells (enough for `id + value` plus a wrapped
  two-line ask at typical question lengths); 72 stops the rail from
  eating the document on ultrawide terminals; 32% keeps the doc-to-rail
  ratio stable in between. Keep the generic-gate 42 and decision-free 44
  widths untouched.
- **Keep the narrow breakpoint as is** (`HORIZONTAL_BREAKPOINTS` at 100
  in `plan_approval_modal.py`): below it the rail docks bottom at full
  width, where wrapped rows read beautifully. Verify the fix there; do
  not redesign it.
- **Verdict stays docked bottom**, but give rows a flex area that shrinks
  instead of the verdict overlapping: rows `height: 1fr` with internal
  scroll (keep `max-height` only as a fraction, e.g. remove the fixed
  `16` so short terminals still show two rows plus verdict).

### Row anatomy (collapsed, the common case)

Three quiet lines, no button block, no character truncation:

```
◉ root_db   db ●                   ← bold: glyph, id, current value, gold ● if changed
  Where should the relocated        ← dim, wrapped, max 2 lines…
  legacy tree live?…                ← …word-boundary ellipsis only if longer
  🧠 you asked · quote ✓            ← dim chips, only when informative
```

Rules:

- Line 1 never wraps: `{glyph} {id}  {shown}{ ●}`. If the value label is
  long, it — not the id — is the part allowed to ellipsize, since the id
  is the anchor for `←/→` cycling and the verdict sentence.
- The ask wraps to the real content width and clamps to **two lines** at
  a word boundary with `…`. Delete the 60/80-char Python truncation; the
  clamp helper must be a pure function of `(text, width, max_lines)` so
  it is unit-testable without a Textual pilot (matching the module's
  existing testability contract stated at the top of
  `plan_decision_rows.py`).
- The provenance line shows only when it adds information: memory chips
  (`🧠 notes · web · you asked`), the unverified warning (keep, yellow),
  or nothing. Never echo the bare decision id as a fake second line.
- Changed-from-default keeps the gold `●` **plus** a dim textual cue on
  the focused row (`was: <default>`); color is never the only signal
  (the module already follows this rule — keep it).

### Row anatomy (focused/expanded)

The focused row expands in place to the full decision:

```
◉ root_db   db ●
  Where should the relocated legacy tree live on this machine?
    ○ db ★       matches the existing $DB/ checkout
    ○ legacy     names it as the pre-… (labels wrap, never clip)
  ★ recommendation: db — …one-line why…
  default: db · was: db (dim when unchanged, highlighted when changed)
  🧠 you asked: "…" (dim, wrapped, full quote)
  ←/→ change · Space toggle · r reset            ← dim hint, first expansion only
```

- Choices render one per line as `◉/○ key ★?` + dim label, labels
  wrapped with hanging indent. Toggles keep `☑️ yes / ⬜ no` (familiar
  from the shipped design) but each on its own line so cell-width wobble
  cannot misalign anything.
- The key hint line appears only while the row is focused, so collapsed
  rows stay scannable.

### Focus, scrolling, and input (unchanged behavior, new rendering)

- `PlanDecisionRows` keeps owning `focused_index`; `j/k` + click move
  focus, `h/l`/`←/→` + Space cycle/flip, `r`/`R` reset. No keybinding
  changes.
- Replace per-row `Button` widgets with borderless `Static`-based rows
  (`padding: 0; border: none; width: 1fr;`) inside the existing
  `VerticalScroll`; move click-to-focus to a lightweight custom message.
  Focus indication becomes a full-width subtle background on the focused
  row plus a left `▍` marker — visible without being a box.
- Keep auto-scroll-into-view for the focused row and the existing
  document-pane scroll-sync (`scroll_target_for_decision`); the
  wrap-first change does not affect line math in the document pane.
- The verdict summary sentence (`→ Tale · …`) already wraps as a
  `Static`; leave it, but confirm it reflows after the rail widens.

### Scrollbar and chrome

- Set an explicit thin scrollbar (`scrollbar-size: 1 1;`) on the rail and
  a dimmer scrollbar color so the gutter reads as gutter, not as the
  orange/red bar dominating the capture. Text must never render beneath
  it — the wrap width must be measured *inside* the gutter.
- No nested borders anywhere in the rail: the rail's single `solid`
  border is the only box. Row separators, if needed, are a single dim
  horizontal rule or 1-line gap — not boxes.

### What explicitly does NOT change

Decision semantics, the frozen-per-review set, defaults/`%auto` behavior,
the `● ★ ◉ ○ 🧠` glyph vocabulary and their cross-surface meanings, all
keybindings, the verdict flow, and the document pane's tinting/folding.

### Implementation sketch (for the implementer)

1. `styles.tcss`: responsive decisions-rail width; `.plan-decision-row`
   → `width: 1fr; border: none; padding: 0 1;` + `.plan-decision-row--focused`
   highlight; thin dim scrollbar on `.gate-review-actions`; flex row area.
2. `plan_decision_rows.py`: add pure `clamp_lines(text, width,
   max_lines)`; collapsed builder wraps + clamps instead of `[:57]`; row
   widgets become focusable-by-index statics; `refresh_rows` updates text
   + focus class instead of button labels.
3. Tests: unit tests for `clamp_lines` (word boundary, CJK/emoji widths,
   `…` accounting); a pilot test that a 90-char ask renders fully
   (wrapped) at rail width 52 with no cropped line; targeted
   `just fix-tui-screenshots -- <decisions goldens>` plus one new golden
   with long asks and one narrow-terminal golden. No `just check-full`
   needed for the change itself.
4. Rollout: no flag — this is presentational, semantics-preserving, and
   every state (changed/unchanged, memory/non-memory, toggle/choice,
   narrow/wide) is snapshot-covered.

## Risks and open questions

- **Textual `Static` wrapping of Rich `Text` with mixed emoji widths** is
  generally correct but should be confirmed by the pilot test, not
  assumed — the installed Textual is 8.0.1 and the fixtures pin the font
  stack, so goldens are the real proof.
- **Minimum usable width**: at the 52-cell floor with a long decision id,
  line 1 could still crowd; the implementer should confirm the worst case
  (`id + value + ●`) against the longest ids in the wild and let the
  value ellipsize first per the rule above.
- A future full-width decisions overlay (option D) remains a reasonable
  *addition* for plans with 5+ long decisions, but it must never become
  required reading — the rail stays canonical.

## Sources consulted

- Screenshot `~/tmp/screenshots/20261012_074036.png` (the reported bad
  render; all observations above trace to it).
- `src/sase/ace/tui/styles.tcss` (gate rail widths, row/verdict/chrome
  rules, narrow breakpoint styles).
- `src/sase/ace/tui/modals/plan_decision_rows.py` (collapsed/expanded
  builders, Button-based rows, focus ownership).
- `src/sase/ace/tui/modals/plan_approval_modal_view.py` (rail compose:
  Decisions above docked-bottom Verdict).
- `src/sase/ace/tui/modals/plan_approval_modal.py` (horizontal
  breakpoints at 100 cells).
- `src/sase/sdd/_plan_display_decisions.py` (glyph vocabulary and
  provenance chips shared across surfaces).
- Textual 8.0.1 installed `Button.DEFAULT_CSS` (`width: auto;
  min-width: 16`, default chrome) from this checkout's `.venv`.
- My prior swarm report
  `202610/plan_decisions_cross_surface_ux/plan_decisions_cross_surface_ux__mus.md`
  (2026-10-07; the Decisions-above-Verdict structure this pass preserves).
- Reference memory `tui.md` + `lint_and_test.md` via `sase memory read`.
- Worked independently: no peer report from this swarm was located,
  opened, or consulted.
