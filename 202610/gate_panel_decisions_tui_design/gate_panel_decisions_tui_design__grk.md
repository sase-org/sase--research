# Gate-panel decisions: a wrapping inspector card

**Researcher:** grk · 2026-10-12
**Kind:** TUI UX research (layout, chrome, truncation, keys)
**Question:** How should Plan Decisions look and behave in ACE gate panels so they are beautiful, fully readable, and still “approve as shown”?
**Evidence:** live screenshot `~/tmp/screenshots/20261012_074036.png`; visual goldens `plan_gate_tale_decisions_{120x40,stacked_90x40,memory_120x40,unverified_120x40}.png` and `plan_gate_epic_decisions_120x40.png`; `src/sase/ace/tui/modals/plan_decision_rows.py`; `src/sase/ace/tui/styles.tcss`; the accepted cross-surface mock in `research:202610/plan_decisions_cross_surface_ux`; the User Question modal’s wrapping `SelectionList`.

---

## 1. Verdict

Ship a **one-line decision index plus a wrapping inspector card**. Stop putting the question, the choices, the why, and the default into a Textual `Button` label.

That single widget mistake is why the panel looks ragged and why the live screenshot cuts “Where should the relocated legacy tree (f” mid-word. The grammar already allows 120-character asks and 100-character labels. The rail is a fixed 50 cells. A multiline `Button` with `width: auto` paints a highlight only as wide as each line, then the parent clips the rest.

Keep **Approve as shown**, keep `Space` / `h` / `l` / `r` / `R`, keep callout follow in the plan pane. Change the chrome, the wrap policy, the height budget, and the rail’s willingness to grow on a wide terminal.

The aesthetic target is the accepted 2026-10 cross-surface mock (cyan gutter, full-width card, labels on a continuation line). The implementation never built that mock. This report is the repair.

---

## 2. What the screenshot actually shows

The 2026-10-12 Plan Review on a wide Athena window:

| Region | What is visible | What is lost |
| --- | --- | --- |
| Expanded `root` | `◉ root  db`, a clipped ask, three clipped choice lines, `default: db` | The rest of the ask; most of each choice label; the `why`; any sense of a card |
| Collapsed `dotfiles` / `conflicts` | id, value, a clipped ask | The rest of the ask; no ellipsis, so it reads as a bug |
| Fourth decision | Only in the verdict sentence (`old_tmp=nest`) | The whole row. The Decisions list is capped at 16 cells |
| Actions | `e ✏ Edit plan` plus a validate disclaimer | Fine, but it steals 4–5 cells from Decisions |
| Verdict | Tale / Reject / Feedback, summary with `root=db · …` | Fine, and docked, which is why Decisions is the thing that overflows |
| Document pane | The full plan, comfortably wrapped | Huge unused width while the rail clips |

The window is wide. The clip is independent of window width: `.gate-review-actions--decisions` is `width: 50` forever. Growing the terminal grows the plan, not the questions.

The same damage is already in the **short-copy goldens**, so this is not “a long plan, once”:

- `plan_gate_tale_decisions_120x40.png` — focused row is a ragged inverted blob; `By pane` sits in its own white chip; `★ pane keeps order` looks like a fourth option.
- `plan_gate_tale_decisions_stacked_90x40.png` — the focused grouping row loses every choice. `density` is gone. Verdict ate the dock.
- `plan_gate_tale_decisions_memory_120x40.png` — collapsed `tui_note` ask ends at `Record c`.
- `plan_gate_tale_decisions_unverified_120x40.png` — warning quote ends at `tui memor`.

Goldens used 30–40 character asks. The live plan used the full grammar. Both fail. The live plan fails louder.

---

## 3. Root causes, ranked

### 3.1 The expanded body is a `Button` label

`PlanDecisionRows.compose` yields a `Button` per decision and a `Static` detail sibling. `refresh_rows` writes **all** of `_expanded_row_text` into `button.label`, then hides the detail `Static` forever.

Textual’s `Button` default CSS is `width: auto`, `min-width: 16`, `line-pad: 1`, with a tall top/bottom border. A multiline label therefore:

1. Sizes each painted line to that line’s text.
2. Focus-reverses those uneven widths, which is the ragged white rectangle.
3. Overflows the 50-cell rail. The parent clips. There is no `text-wrap: wrap` and no `text-overflow: ellipsis` on `.plan-decision-row`.

The User Question modal already documented this class of bug and subclassed `SelectionList` to wrap (`user_question_modal.py`, `_WrappingSelectionList`). Plan Review did not reuse that lesson.

### 3.2 Choice key and label share one line

`_expanded_row_text` emits `  ◉ db ★  watches the existing $DB/…` as a single Rich span. Inner width is ~43–46 cells after border, padding, and `scrollbar-gutter: stable`. A 24-character key plus a 100-character label cannot fit. The accepted mock already stacked the label on the next indented line. The code did not.

### 3.3 Hard character truncation is the wrong tool, and it loses to the widget anyway

Collapsed asks cut at 80 characters (60 on memory rows) with `"..."`. The screenshot’s collapsed asks die at ~40–45 characters **without** an ellipsis. The `Button` clips first. Truncation is also width-blind: a 50-cell rail and a 90-column stacked rail get the same 80-character slice.

### 3.4 `max-height: 16` on `.plan-decision-rows`

Five decisions is the authored maximum. Two-line collapsed rows are 10 cells. An expanded choice with three options is ~8 more. Actions sits above; Verdict is docked below. Sixteen cells cannot hold that. The fourth decision in the screenshot is the overflow. On 90×40 the stacked dock is 48% of the body (~16 cells for the whole rail), so the cap and the dock fight each other and the focused choices disappear.

### 3.5 The rail does not grow

```
PlanApprovalModal .gate-review-body > .gate-review-actions           { width: 44; }
PlanApprovalModal .gate-review-body > .gate-review-actions--decisions { width: 50; }
.gate-review-document                                               { width: 1fr; }
```

A 200-column window still gives questions 50 cells. The grammar (`docs/sdd.md`): ask ≤ 120, label/`why` ≤ 100, 2–5 choices, ≤ 5 decisions. That budget was chosen for authoring, not for a 50-cell widget.

### 3.6 Chrome that the mock specified was never built

The 2026-10 mock had a cyan `▌` gutter, a full-width tinted card, `< value >` on the focused header, labels wrapping under keys, and `why` as a dim footnote. Shipping chrome is: inverted Button, `default: db` duplicating the `★`, `why` looking like another radio, header `Decisions  4 · 🧠 0` even when there is no memory decision.

The unused `#plan-decision-detail-{n}` widgets are the remnant of the split that should have happened.

---

## 4. Constraints that stay

These are load-bearing. A prettier panel that breaks them is a regression.

| Constraint | Why |
| --- | --- |
| **Approve as shown.** Enter, digits, Ctrl+S, and `c`→submit merge the sheet on display. | Cross-surface contract. Enter never edits a value. |
| `Space` cycles a choice / flips a toggle; `h`/`l` step; `r`/`R` reset. | Already in `ace.keymaps.gate` and the footer. Digit keys submit branches. |
| `j`/`k` walk Actions → Decisions → Verdict as one ring. | Shared gate-modal keys. |
| Decision Sheet and glyphs stay in sase-core / `_plan_display_decisions.py`. | TUI, Telegram, CLI, `%auto` receipt share `◉ ○ ☑️ ⬜ ★ ● 🧠`. |
| Focus follows the first callout (or id mention) in the plan pane. | ACE’s unique value vs Telegram/CLI. |
| Keypress path is a draft patch: no `validate_plan`, no re-lex, no span recache. | `tui_perf.md`; `test_draft_edit_avoids_revalidate_relex`. |
| Frozen definitions. Prose edits keep answers; `decisions:` edits are refused. | Gate protocol. |
| Presentation-only change. | Litmus test: Telegram/CLI already show the same sheet. Do not reopen the wire. |

---

## 5. Character budget (so wrap is a requirement)

Inner cells in the current 50-wide rail, after `border: solid`, `padding: 0 1`, and `scrollbar-gutter: stable`: **about 43–46**.

| Field | Max authored | Lines at 45 inner | Lines at 70 inner (36% of a 200-col window) |
| --- | --- | --- | --- |
| `ask` | 120 | 3 | 2 |
| choice label | 100 | 3 (indented) | 2 |
| `why` | 100 | 3 | 2 |
| 5 choices × (key line + wrapped label) | — | ~20 | ~12 |
| Worst inspector (5 choices, max copy) | — | ~25 | ~16 |

A 25-line inspector cannot live as an un-scrolling accordion body next to four other rows, Actions, and Verdict. The inspector **scrolls internally**. The index of ids does not.

---

## 6. Alternatives

### A. Surgical CSS on the existing Buttons

`width: 100%`, `text-wrap: wrap`, put labels on the next line, `max-height: 1fr`.

A one-hour patch. It would stop mid-word clipping on the 120×40 golden. It leaves Button borders, `line-pad`, and mixed-style wrap bugs. It does not give a cyan gutter or a uniform card. It does not save the 90×40 stacked layout. Treat as a possible hotfix, not the design.

### B. In-rail accordion, wrapping `Static` body (the 2026-10 mock, actually built)

Header stays a one-line control; body is a wrapping `Static` in a full-width card with a cyan gutter. Closest to the accepted mock. Still fights the 16-cell / 5-decision / max-copy budget unless the collapsed rows become one line and the card scrolls.

### C. One-line index + wrapping inspector card in the rail *(recommended)*

Every decision is always a one-line index row. The focused decision’s full ask, radios, why, and memory chips render in a wrapping card **below the index** (or between the focused row and the rest — see §7). The card scrolls. The index never disappears. The rail may grow with the window.

### D. Dock the inspector in the document pane

Index + Verdict stay in the rail. The wrapping card docks at the top of the plan pane, above the callout tint. Best width (the plan column). Bigger layout change; the plan and the inspector compete for height; focus-follow and the sticky card need a split inside `#plan-approval-scroll`. Keep as the fallback if C still clips on a 90×40 / 5-max-copy golden.

### E. Reuse the User Question two-pane

Left: question list. Right: wrapping options. Proven widgets (`OptionList` + `_WrappingSelectionList`). It replaces the plan-beside-decisions layout, which is ACE’s reason to exist for this gate. `j`/`k` would move inside the radio list and collide with the gate ring unless remapped (`n`/`p` in User Question). Reject as the Plan Review layout.

### F. Textual `RadioSet`

Real radio semantics, wrapping labels. `RadioSet` is a focusable `VerticalScroll`; Space/Enter toggle the radio, and `j`/`k` would move among radios. That fights “Space cycles the focused decision” and “Enter approves as shown”. Use the **look** of radios. Keep decision-level focus.

### G. Picker overlay on `i` or Enter

Conflicts with Enter = approve and with `i` = input panel. The focused card already is the picker.

---

## 7. Recommended UX

### 7.1 Product sentence

**Every decision id stays on screen. The focused decision’s full question wraps in a card. Enter still approves exactly the values on display.**

### 7.2 Layout

Wide (≥100 columns), decisions present:

```
┌ Plan Review  CLAUDE(opus) ──────────────────────────────────────────┐
│ ┌ Rail (min 50, 36%, max 76) ──┐ ┌ plan.md ───────────────────────┐ │
│ │ Actions                      │ │ decisions: 4 · answered in the │ │
│ │  e  Edit plan                │ │ Decisions panel                │ │
│ │                              │ │                                │ │
│ │ Decisions  4 · 1 changed     │ │ > [!decision] root = db  …     │ │
│ │ ┌ inspector ───────────────┐ │ │ > [!decision] root = legacy …  │ │
│ │ │▌ ◉  root            db ★ │ │ │                                │ │
│ │ │▌   Where should the      │ │ │ (callout of the focused        │ │
│ │ │▌   relocated legacy      │ │ │  decision is green+bold;       │ │
│ │ │▌   tree live?            │ │ │  the others stay dim)          │ │
│ │ │▌   ◉  db ★               │ │ │                                │ │
│ │ │▌      ~/db — watches     │ │ └────────────────────────────────┘ │
│ │ │▌      the existing $DB/  │ │                                    │
│ │ │▌   ○  legacy             │ │                                    │
│ │ │▌      ~/legacy — names   │ │                                    │
│ │ │▌      it as the previous │ │                                    │
│ │ │▌   ○  profile            │ │                                    │
│ │ │▌      ~/.profile already │ │                                    │
│ │ │▌      calls this root $DB│ │                                    │
│ │ │▌   ★  keep the tree the  │ │                                    │
│ │ │▌      profile already    │ │                                    │
│ │ │▌      points at          │ │                                    │
│ │ └──────────────────────────┘ │                                    │
│ │   ◉  dotfiles     repoint    │                                    │
│ │   ◉  conflicts    delete     │                                    │
│ │   ◉  old_tmp      nest       │                                    │
│ │                              │                                    │
│ │ Verdict                      │                                    │
│ │  ☑️ Launch coder  ☑️ Commit  │                                    │
│ │  1 ✅ Tale  2 ❌ Reject  3 💬 │                                    │
│ │  → coder + commit · root=db  │                                    │
│ │    · dotfiles=repoint · …    │                                    │
│ └──────────────────────────────┘                                    │
│ j/k  Space  h/l  r/R   Enter=Tale · defaults   Ctrl+S  …            │
└─────────────────────────────────────────────────────────────────────┘
```

Placement of the inspector: **directly under the Decisions header, above the unfocused index.** Opening the modal focuses decision 0, so the question is the first thing in the Decisions section (the existing “gentle nudge against rubber-stamping”). `j`/`k` move the highlight in the index; the inspector retargets. The index order stays author order.

Unfocused index row (exactly one line, width-aware ellipsis):

```
◉  root          db
◉  dotfiles      repoint ●          ← gold ● when changed
☑️ tui_note      yes
```

If leftover cells ≥ 12, append a dim ask preview after two spaces, ellipsized to the remaining width. If not, omit the preview. Never wrap an index row. Never drop an id.

### 7.3 Inspector card anatomy

```
▌ ◉  root                         db ★
▌    Where should the relocated legacy tree live?
▌
▌    ◉  db ★
▌       ~/db — watches the existing $DB/ tree in place
▌    ○  legacy
▌       ~/legacy — names it as the previous layout
▌    ○  profile
▌       ~/.profile already calls this root $DB
▌
▌    ★  keep the tree the profile already points at
```

Rules:

1. **Gutter.** One-cell `▌` in `$primary` (cyan in the current theme) on every inspector line. This is the mock’s focus cue. Reverse-video is reserved for the index row that is focused, or omitted entirely if the gutter + card background is enough. Pick one focus treatment and use it on the whole card, not per wrapped line.
2. **Header.** Glyph, id, current value, `★` if the value equals the default, gold `●` if it does not. Optional `< db >` chevrons around the value as a “Space will move this” affordance.
3. **Ask.** Full string, `text-wrap: wrap`. Three lines at 45 inner cells; two at 70. Sticky at the top of the card when the radios scroll.
4. **Radios.** Key on its own line with `◉`/`○` and `★` on the default key. Label starts on the next line, indented 6 cells, wrapped. Clicking a radio line sets that value (mouse parity with Space). Radios are **not** in the `j`/`k` ring.
5. **Toggles.** Same card: ask, then `☑️ yes ★` / `⬜ no` stacked the same way. Memory chips and the quote sit under the ask, wrapped. Unverified warning stays yellow and also wraps.
6. **Why.** Dim italic, prefixed with `★`, under the radios. It is a footnote for the default, not a fourth option. Drop the extra `default: db` line. The `★` on the default key plus the why line is enough.
7. **Overflow.** The card is `height: 1fr` inside the Decisions block and `overflow-y: auto`. The ask does not scroll away (dock it inside the card, or keep it in a non-scrolling header Static above a scrolling radio list).

### 7.4 Header

`Decisions  4` by itself. Append ` · 1 changed` when `changed_count > 0`. Append ` · 🧠 2` when `memory_count > 0`. A header that always reads `4 · 🧠 0` teaches the reviewer to ignore it.

### 7.5 Rail width

When the plan has decisions:

```
min-width: 50;
width: 36%;
max-width: 76;
```

Decision-free plans keep today’s 44. At 120 columns, 36% is 43 and the min-width holds 50 (status quo). At ~200 columns the rail becomes ~72, which is where a 120-character ask becomes two lines and a 100-character label becomes two. The plan pane stays the majority (`1fr`).

`.-gate-review-narrow` (below 100 columns) still docks the rail to 48% height. In that mode the inspector’s internal scroll is mandatory, and collapsed rows **must** be one line so all five ids remain reachable above Verdict.

### 7.6 Height budget

Replace `.plan-decision-rows { height: auto; max-height: 16; }` with:

```
.plan-decision-rows {
    height: 1fr;
    min-height: 8;
}
```

Decisions fill the space between Actions and the docked Verdict. The index is `height: auto`. The inspector is `height: 1fr`. Nothing in this block is hard-capped at 16.

### 7.7 Keys (unchanged)

| Key | Behavior |
| --- | --- |
| `j` / `k` | Move the index highlight; inspector retargets; plan scrolls to the callout |
| `Space` | Next choice, wrapping / flip toggle |
| `h` / `l` / arrows | Previous / next choice, or no / yes |
| `r` / `R` | Reset focused / all |
| `Enter` | Approve as shown |
| Click on an index row | Focus that decision |
| Click on a radio line | Set that value |

Do not add per-choice digit keys. Do not make Enter open a picker.

Optional later: when the inspector is focused and the last radio is highlighted for mouse users, that is paint-only. Keyboard focus stays on the decision.

### 7.8 Visual language (already canonical)

Keep `◉ ○ ☑️ ⬜ ★ ● 🧠`. Do not introduce `◆`, `⋔`, or a second radio alphabet. Changed values already use a gold `●` **and** the word “changed” in the header / Enter badge, so colour is not the only cue (`tui` / a11y).

Card background: `$surface-lighten-1` or a 20% `$primary` tint, full width of the rail’s content box. The highlight is the container, never the length of a Rich span.

### 7.9 Document pane

Keep fold, callout tint, and focus-follow. They already work (`test_first_frame_tint_keeps_syntax`, `cache_callout_spans`). Add a one-line dim caption under the plan filename when a decision is focused: `answering root`. Cheap, and it ties the two panes together when the callout is off-screen mid-scroll.

### 7.10 Actions and Verdict

Leave Verdict compact and docked. Leave Actions as a short list. If an action description would wrap past two lines, ellipsize it; it is secondary to Decisions. The validate disclaimer in the screenshot can be a tooltip or a one-line dim note, not a paragraph.

### 7.11 Motion and performance

On `Space` / `h` / `l` / `r`:

1. Mutate `PlanDecisionDraft` (already).
2. Patch **one** index row’s label and the inspector `Static`.
3. Re-tint the document from the cached spans (already).
4. Refresh the verdict sentence and the Enter badge (already).

Do not remount `PlanDecisionRows`. Do not rebuild every Button label (`refresh_rows` currently does). Do not call `validate_plan` or re-lex. `esc_drafts[request_id]` stays as today.

Swallowing all exceptions in `PlanDecisionRows` (`except Exception: pass` on query/mount/refresh) hid the dead detail widgets. New code should fail tests when a row cannot mount.

---

## 8. Widget tree

Replace the Button-per-row accordion with three pieces, all still under `#plan-decision-rows`:

```
PlanDecisionRows (Vertical)
  Static            #plan-decisions-header     (already a sibling today)
  Container         #plan-decision-inspector   classes=plan-decision-card
    Static          #plan-decision-gutter-ask  (header + wrapped ask, no scroll)
    VerticalScroll  #plan-decision-choices
      Static        one wrapping radio / toggle block
  OptionList        #plan-decision-index       one Option per decision, id=plan-decision-{n}
```

`OptionList` is the house widget for a one-line highlighted index (Models, command palette, User Question left pane). Guard programmatic `highlighted` assignments per `tui_perf.md` rule 12 so `j`/`k` from the gate ring do not echo.

If `OptionList` fights the gate focus ring, a one-line `Button` **per index row only** (never for the body) with `width: 100%; height: 1; border: none; text-wrap: nowrap; text-overflow: ellipsis` is acceptable. The inspector stays a `Container` of `Static`s.

Extract `_WrappingSelectionList`’s wrap/indent logic into a shared helper only if the inspector’s radio lines become a real `SelectionList`. They should not, because of the key contract. A wrapping `Static` with clickable regions (`on_click` + meta) is enough.

CSS sketch:

```css
PlanApprovalModal .gate-review-body > .gate-review-actions--decisions {
    min-width: 50;
    width: 36%;
    max-width: 76;
}
.plan-decision-rows {
    height: 1fr;
    min-height: 8;
}
.plan-decision-card {
    width: 100%;
    height: 1fr;
    min-height: 6;
    background: $primary 15%;
    border-left: heavy $primary;
    padding: 0 1;
    overflow-y: auto;
}
.plan-decision-card Static {
    width: 100%;
    height: auto;
    text-wrap: wrap;
    text-overflow: clip;
    text-align: left;
}
#plan-decision-index {
    height: auto;
    max-height: 7;          /* 5 decisions + chrome */
    text-wrap: nowrap;
    text-overflow: ellipsis;
}
```

Narrow dock (`.-gate-review-narrow`): keep `height: 48%` on the rail. The card still takes `1fr`. Index `max-height: 7` keeps five ids visible. Inspector scrolls.

---

## 9. What “looks good” means, line by line

Drawn from the accepted mock, from k9s/lazygit selection chrome (full-row highlight, not content-width highlight), and from nmtui-style radio groups (glyph + wrapping description under the name).

1. Focus is a **rectangle the width of the rail**, plus a left gutter. It is never a staircase of short inverted lines.
2. The selected radio is bold; unselected radios are dim. The label is readable in both states.
3. The default is a `★` on the default key. Changed is a gold `●` on the header value. Both can appear together (`mode ●` with `★` still on `pane`).
4. Wrapped continuation lines indent to the text column, so a glyph never dangles on a second line by itself (the same rule `_WrappingSelectionList.render_line` already implements).
5. Clipping with no ellipsis is a bug. Ellipsis is allowed only on the one-line index, and only with `text-overflow: ellipsis`.
6. The fourth and fifth decisions are always in the index. Discoverability does not depend on scrolling the inspector.
7. Memory warnings wrap. A 300-character quote is legal; it lives in the scrolling part of the card.

---

## 10. Implementation order

A single visual PR, three commits if it needs to land stacked:

1. **Stop the clip.** Inspector `Static` + one-line index; wrap asks and labels; drop `max-height: 16`; drop `default: db`; hide the dead detail widgets or finally use them as the card. Keys unchanged. Existing goldens will move; that is expected.
2. **Make it a card.** Cyan gutter, full-width tint, stacked key/label, header `N · K changed`, width-aware index ellipsis, selective patch on Space.
3. **Give wide terminals room.** `min-width: 50; width: 36%; max-width: 76`. Add max-copy goldens.

Hotfix-only (if a same-day repair is needed before the card): newline before labels, `.plan-decision-row { width: 100%; text-wrap: wrap; }`, `max-height: 1fr`. Then still do 1–3.

---

## 11. Verification

Current goldens never exercised the grammar’s max. Add fixtures, not only restyle the short ones.

| Golden | Size | Copy | Must show |
| --- | --- | --- | --- |
| `plan_gate_tale_decisions_120x40` | 120×40 | short (today) | Card, not a ragged Button; both ids visible |
| `plan_gate_tale_decisions_maxcopy_120x40` | 120×40 | 120-char ask, 100-char labels, 5 choices, 5 decisions | Full focused ask; every index id; no mid-word clip |
| `plan_gate_tale_decisions_stacked_90x40` | 90×40 | short | Focused radios still visible; second id visible |
| `plan_gate_tale_decisions_maxcopy_90x40` | 90×40 | max copy | All five ids; ask wrapped inside a scrolling card; Verdict still docked |
| memory verified / unverified | 120×40 | today’s quotes | Warning/quote wrap; `Record c` is gone |

Unit tests on the text builders:

- `_inspector_text` contains the full ask and each full label.
- `_index_label(width=46)` never exceeds 46 cells and uses an ellipsis when the ask is appended.
- Expanded choice labels are on a **different line** from the key.
- No `default: {value}` line.

Pilot test: at 120×40 and 90×40, `content_region` of the inspector contains the last character of a 120-char ask (or the inspector’s scrollbar is visible and `scroll_end` reveals it). The index region contains `plan-decision-4`.

Live check after landing: `sase screenshot` against a real four-decision plan like the 2026-10-12 Athena review. The golden lane is 120×40 / 90×40; the user’s window is wider, and the 36% rail is the thing that screenshot will prove.

Do not treat a single restyled short golden as done.

---

## 12. Out of scope

- Telegram keyboard and CLI `-D` card. They already wrap or paginate by nature. Glyphs and the summary sentence stay shared; this is ACE chrome.
- Question gates. User Question already wraps. Do not merge the two modals.
- Custom / sudo gate rails, except they should keep using `Static` / compact Buttons and never copy the decision-Button accordion.
- Raising or lowering the 120 / 100 / 5 authoring limits. Wrap to the limit; do not punish planners.
- Changing Enter, digits, or the Decision Sheet schema.

---

## 13. Why this is the best possible TUI design here

ACE is the only surface that can put the question next to the prose it selects. The 2026-10 research was right about that, right about Approve as shown, and right about the mock. It was wrong about the 50-cell accordion surviving 120-character asks inside a Textual `Button`.

The User Question modal, in this same TUI, already solved wrapping. k9s and lazygit already solved full-row selection. nmtui already solved “name on one line, description wrapped under it.” The repair is to use those three patterns inside the existing rail, grow the rail when the window has room, and never again hide a decision behind `max-height: 16`.

**Ship the index plus wrapping inspector card.** That is the design.
