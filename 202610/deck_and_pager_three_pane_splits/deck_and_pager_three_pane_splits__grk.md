# Three-pane splits for the Agents deck and the pager

Researcher: `grk` (independent). This note is a design recommendation, not an
implementation plan.

**Verdict:** The feature is a good idea and the right next step after
[sase-1eg](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1eg/README.md).
Do not grow a general tiling window manager. Ship a closed family of five
layouts (single, stacked 2, side 2, stacked-main 3, side-main 3) driven by the
existing `\` / `|` keys, with `Ctrl+B` / `Ctrl+F` as a real focus ring,
`Ctrl+Shift+B` / `Ctrl+Shift+F` to swap along that ring, and `Ctrl+Shift+D` to
close the focused pane.

The user's cyclic key table is learnable and beautiful once the unsplit pane is
named the **spine** (not "the larger pane") and a few ambiguities below are
closed. I would take this approach, with the requirement adjustments in
§4.

---

## 1. What exists today

Both surfaces already share a two-pane peer model. The pager
(`src/sase/pager/split.py`, `_screen_split.py`) was written to *mirror* the
Agents deck (`src/sase/ace/tui/widgets/decks/layout.py`, `area.py`) without
importing it. That duplication is now a liability: a three-pane state machine
is easy to get wrong twice.

| | Agents deck | Pager |
|---|---|---|
| Layouts | `SINGLE`, `TOP_BOTTOM`, `LEFT_RIGHT` | `SINGLE`, `BELOW`, `BESIDE` |
| Open | `\` below, `\|` beside; new panel focused at 50/50 | same |
| Same key again | Unsplit **to panel 0** (not the focused panel) | Unsplit **keeping the focused pane** (vim `C-w o`) |
| Other key | Rotate, keep decks/focus/ratio | Rotate, keep views/focus/ratio |
| Focus | `Ctrl+F` toggles; docs say `Ctrl+B` has no Agents behavior | `Ctrl+F` toggles; no reverse |
| Ratio | `{` / `}` through `(30, 50, 70)` | `+` / `-` through the same steps |
| Close focused | none (same-key unsplits to panel 0) | `q` / `Esc` / exhausted Backspace |
| Other-target | `p` then `M`/`F`/`T`/`N`; `other_panel_target` is `1 - source` | `Ctrl+W` `<label>`; "the other pane" |
| Widgets | Two pre-composed `DeckPanel`s; panel 1 starts `.hidden` | `PagerView`s mounted dynamically |
| Persistence | `~/.sase/ace_agents_deck_state.json` schema v1, `MAX_PANELS = 2` | per-session only (sase-1eg non-goal) |
| Zoom | `Z` snapshots layout, shows focused as `SINGLE` | none (uppercase letters are link labels) |
| Small windows | no fit guard | `MIN_STACKED_PANE_HEIGHT = 7`, `MIN_BESIDE_PANE_WIDTH = 32` |
| Chrome | per-deck accent border, 35% unfocused | per-section accent round frame, subject in title/subtitle |

sase-1eg's contract (just landed) is explicit: two panes, rotate on the other
key, same key keeps the focused pane, pixel-identical single-pane goldens,
`Ctrl+W` never creates more than two panes. Its non-goals list "More than two
panes, or nested splits." This research is the sequel that lifts that non-goal.

The Agents tab has four decks (Main, Files, Tools, FINAL). Three visible
panels is the natural fit: a 3-pane view shows three of the four, and
`Ctrl+N`/`Ctrl+P` still reach the fourth. The pager's use is comparison
reading (bead / plan / source, or now / past / diff).

---

## 2. Critique of the requested plan

### What is right

- **Cap at three.** Recursive vim/tmux splits look powerful and become a
  second product. Five layouts, two of them three-pane T-junctions, is the
  whole feature. tmux already named these `main-horizontal` and
  `main-vertical`; we should steal the geometry, not the `next-layout` cycle.
- **`\` and `|` stay the only split keys.** A third chord for "now make three"
  would be forgotten. Nesting on the *other* axis key is the move a user
  reaching for a third pane will actually try.
- **`Ctrl+B` as reverse `Ctrl+F`.** With two panes, toggle was enough and the
  docs already reserved `Ctrl+B` on Agents (`Ctrl+B has no Agents behavior`).
  With three, a ring is mandatory. `Ctrl+F` / `Ctrl+B` is emacs/less paging
  inverted into pane order, and it is already tab-disjoint from
  `scroll_prompt_down` / `scroll_prompt_up` (`ctrl+f` / `ctrl+b` on the
  prompt).
- **A close-focused chord.** Pager `q` already means "not this pane". The deck
  has no equivalent: same-key unsplits to panel 0, which is the wrong survivor
  once you have been working in the bottom/right panel. `Ctrl+Shift+D` is the
  deck's `q`, and on the pager it aliases `q` while split.
- **Swap along the ring.** Complementary to focus-move: `Ctrl+F` moves you,
  `Ctrl+Shift+F` moves the content.

### What is wrong or underspecified

1. **"Larger pane" is the wrong name.** After `{` / `}` (or `+` / `-`) the
   spine can be the *smaller* region. The pane that was not subdivided is the
   **spine**: it spans the full outer axis. Close-spine must close that pane
   even when it is visually smaller.
2. **Two 3-pane "views" are really four geometries.** Nesting the focused pane
   makes the spine's side depend on focus:
   - stacked 2, focus top, `|` → spine **bottom**
   - stacked 2, focus bottom, `|` → spine **top**
   - side 2, focus left, `\` → spine **right**
   - side 2, focus right, `\` → spine **left**
   Treat these as one family per outer axis, plus a `spine_side`, not as two
   anonymous views.
3. **2-pane rotate disappears.** sase-1eg taught `|` on a stacked split to
   *rotate*. The new table uses that keystroke to *nest*. That is the right
   long-term binding (nest is what `|` *looks like* it should do), but it is a
   regression for anyone who learned rotate yesterday. Recover it as a
   two-keystroke path (nest, then close-spine) and, when the nest cannot fit,
   **fall back to rotate** so small terminals keep the old one-keystroke
   behavior.
4. **Agents and pager disagree on same-key unsplit.** Deck keeps panel 0;
   pager keeps focused. Three-pane plus `Ctrl+Shift+D` makes "keep panel 0"
   indefensible. Unify on the pager/vim rule.
5. **"The other pane" does not survive a third pane.** `other_panel_target`,
   `Ctrl+W`, doubled `Ctrl+W`, and capital deck letters all assume `1 - i`.
6. **One ratio is not enough.** A T-junction has an outer split (spine vs
   nested pair) and an inner split (the pair). Grow/shrink must act on the
   split that contains the focused pane.
7. **`Ctrl+Shift+D` collides with the leak-snapshot debug binding**
   (`SASE_ACE_DEBUG_LEAKS=1` → `action_debug_leak_snapshot`). Rebind the
   debug chord.
8. **No shared model.** Copying the 2-pane toggle into two files was
   tolerable. Copying this table is not.

### Would I do something else?

I would not:

- Build an arbitrary binary split tree (vim `C-w s/v` unbounded).
- Add even-3 columns / even-3 rows / tiled (tmux `next-layout`). Those are
  pretty and wrong for decks: the spine is the point.
- Add a new split key, a leader sequence, or a double-tap.
- Persist pager splits (still a session gesture).
- Let `Ctrl+W` or the deck picker open a third pane. Three panes are a
  deliberate `\ `|` gesture.

I would do exactly the cyclic table the user sketched, with the adjustments
in §4.

---

## 3. Recommended state machine

Five kinds. `spine_side` is `START` (top/left) or `END` (bottom/right) and is
ignored on 1- and 2-pane layouts.

```
SINGLE          one pane
STACKED         2, top / bottom          (`\` from single)
SIDE            2, left / right          (`|` from single)
MAIN_STACKED    3, spine full width      (`|` from STACKED)
MAIN_SIDE       3, spine full height     (`\` from SIDE)
```

Axis mnemonic, matching the glossary (vim names: `\` is a horizontal split,
`|` a vertical split):

> `\` talks about the stacked axis. `|` talks about the side-by-side axis.
> If that axis is absent, split it (nest when a split already exists on the
> other axis). If that axis is the inner split of a 3-pane, rotate the figure.
> If that axis is the outer/spine split, drop the spine. If that axis is the
> only split, keep the focused pane and go single.

### Transitions (`\` / `|`)

```
SINGLE --\--> STACKED          new pane is bottom, focused
SINGLE --|--> SIDE             new pane is right, focused

STACKED --\--> SINGLE          keep focused (vim C-w o)
STACKED --|--> MAIN_STACKED    split focused side-by-side;
                               unfocused original becomes the spine
                               (focus top  → spine END / bottom)
                               (focus bottom → spine START / top)
                               if the nest does not fit: rotate to SIDE instead

SIDE --|--> SINGLE             keep focused
SIDE --\--> MAIN_SIDE          split focused stacked;
                               unfocused original becomes the spine
                               (focus left  → spine END / right)
                               (focus right → spine START / left)
                               if the nest does not fit: rotate to STACKED instead

MAIN_STACKED --|--> MAIN_SIDE  rotate; spine stays spine, nested pair stays nested
                               clockwise: spine END (bottom) → spine END (right)
                                          spine START (top)  → spine START (left)
MAIN_STACKED --\--> SIDE       close spine; nested pair remains, now side-by-side

MAIN_SIDE --\--> MAIN_STACKED  rotate (inverse of the clockwise map above)
MAIN_SIDE --|--> STACKED       close spine; nested pair remains, now stacked
```

From STACKED, `|` then `\` is the two-keystroke 2-pane rotate (via a 3-pane
that immediately collapses if you did not want it). From SIDE, `\` then `|`.
On a window too narrow/short to nest, the first keystroke is the old rotate,
so sase-1eg muscle memory still works on small terminals.

Same-key on 2-pane still returns to single. That requirement stays.

### ASCII

Stacked 2, focus top, press `|`:

```
╭─────╮         ╭───╮╭───╮
│  A* │   -->   │ A ││ C*│     MAIN_STACKED, spine END
╰─────╯         ╰───╯╰───╯
╭─────╮         ╭────────╮
│  B  │         │   B    │
╰─────╯         ╰────────╯
```

Stacked 2, focus bottom, press `|`:

```
╭─────╮         ╭────────╮
│  A  │   -->   │   A    │     MAIN_STACKED, spine START
╰─────╯         ╰────────╯
╭─────╮         ╭───╮╭───╮
│  B* │         │ B ││ C*│
╰─────╯         ╰───╯╰───╯
```

Rotate MAIN_STACKED spine-END with `|`:

```
╭───╮╭───╮      ╭───╮╭────╮
│ A ││ C │  --> │ A ││    │    MAIN_SIDE, spine END (right)
╰───╯╰───╯      ╰───╯│ B  │
╭────────╮      ╭───╮│    │
│   B    │      │ C ││    │
╰────────╯      ╰───╯╰────╯
```

Close-spine from the left figure with `\`:

```
╭───╮╭───╮
│ A ││ C │     SIDE, focus kept if it was A or C;
╰───╯╰───╯     if focus was the spine, it lands on the last nested pane
```

### New pane contents

- **Pager:** clone of the focused pane (document, reading anchor, trail,
  independent history). Same as sase-1eg. The third pane is another clone,
  not a blank.
- **Decks:** `choose_new_panel` over decks not already shown that have
  content (FINAL only on positive content). A third pane is why there are
  four decks. Duplicate the focused deck only when nothing else qualifies,
  with the existing Main-card / Files-file offset so the two copies are not
  identical.

`Ctrl+W` and the deck picker's capital letters **do not** create a third
pane. From single they still open a 2-pane; from 2- or 3-pane they fill an
existing other pane (see §4.5).

---

## 4. Requirement adjustments (explicit)

These change or complete the user's list. Each is justified.

### 4.1 Name the unsplit pane the spine

**Adjust:** whenever the request says "the larger horizontal/vertical pane",
read **spine**. Close-spine ignores ratio.

### 4.2 Spine side follows the focused pane at nest time

**Adjust:** the two additional "views" are families. `MAIN_STACKED` and
`MAIN_SIDE` each have `spine_side ∈ {START, END}`. Do not canonicalize to
spine-bottom / spine-right; that would ignore which pane the user split.

### 4.3 When a nest does not fit, rotate

**Adjust:** `|` on STACKED that cannot give both nested panes
`MIN_BESIDE_PANE_WIDTH` (32) and the spine `MIN_STACKED_PANE_HEIGHT` (7)
rotates to SIDE (sase-1eg behavior) and toasts why. Symmetric for `\` on
SIDE. A 3-pane layout is a progressive enhancement of a wide enough
terminal, not a hard fail.

3-pane minimum is the same for both families: about **64×14** (two 32-col
nested panes, or two 7-row nested panes, plus a spine). Existing 2-pane
beside goldens already skip 60 columns; 3-pane goldens should be 120×40
only.

### 4.4 Unify same-key unsplit on "keep focused"

**Adjust:** Agents currently unsplits to panel 0. Change it to match the
pager: same-key on a 2-pane keeps the focused panel, like vim `C-w o`.
`Ctrl+Shift+D` (and pager `q`) is the converse: close focused, keep the
other. This is a visible Agents behavior change and must be documented.

### 4.5 "Other pane" becomes last-focused, else next in reading order

**Adjust:** with three panes, `1 - i` is undefined.

- Remember `last_focused` (the pane `Ctrl+F` / `Ctrl+B` / click just left).
- `Ctrl+W` `<label>`, doubled `Ctrl+W`, and `p` then `M`/`F`/`T`/`N` target
  that pane when it still exists and is not the source; otherwise the next
  pane in reading order.
- They never open a third pane.

Reading order is spatial, left-to-right then top-to-bottom:

| Layout | Order |
|---|---|
| STACKED | top, bottom |
| SIDE | left, right |
| MAIN_STACKED spine END | nested-left, nested-right, spine |
| MAIN_STACKED spine START | spine, nested-left, nested-right |
| MAIN_SIDE spine END | nested-top, nested-bottom, spine |
| MAIN_SIDE spine START | spine, nested-top, nested-bottom |

`Ctrl+F` walks this order forward and wraps. `Ctrl+B` walks it backward.
Click still focuses the pane under the pointer. `toggle_focus` (boolean
flip) is deleted; both surfaces call `cycle_focus(delta)`.

### 4.6 Two ratios

**Adjust:** `ratio` is the outer split (first region vs rest, same 30/50/70
steps). `inner_ratio` is the nested pair, default 50. Grow/shrink:

- focused pane is nested → step `inner_ratio` (the focused nested pane grows)
- focused pane is the spine → step `ratio` (the spine grows)

Clamp against the same minima. A 2-pane ignores `inner_ratio`. Persistence
writes both.

### 4.7 Swap moves content; focus follows the content

**Adjust:** `Ctrl+Shift+F` / `Ctrl+Shift+B` swap the focused pane with the
next/prev pane in reading order. The user keeps looking at the same
document/deck in its new slot (focus follows content). With two panes both
chords swap the pair. With one pane they are inactive.

This pairs with `Ctrl+F` / `Ctrl+B`: those move the caret, these move the
window.

### 4.8 `Ctrl+Shift+D` closes the focused pane, and is split-only

**Adjust (clarifying):** active only when two or more panes are visible, as
requested. Effects:

| From | Focused | Result |
|---|---|---|
| 2-pane | either | SINGLE, the other pane survives |
| 3-pane | a nested pane | 2-pane along the **outer** axis (spine + remaining nested) |
| 3-pane | the spine | 2-pane along the **inner** axis (same as close-spine) |

Pager `q` / `Esc` / exhausted Backspace keep this meaning (they already close
focused). On SINGLE they still dismiss the pager. The deck has no `q`;
`Ctrl+Shift+D` is its only close-focused.

Same-key 2-pane unsplit (`\` on STACKED, `|` on SIDE) is unchanged and still
the way back to one pane without `Ctrl+Shift+D`.

### 4.9 Rebind the debug leak snapshot

**Adjust:** `Binding("ctrl+shift+d", "debug_leak_snapshot")` under
`SASE_ACE_DEBUG_LEAKS=1` must move (command palette or a different chord).
Production `Ctrl+Shift+D` is close-pane.

### 4.10 Do not open a fourth pane

**Adjust (clarifying):** `|` / `\` on a 3-pane only rotate or close-spine.
There is no tiled 2×2, no even-3, no "split this nested pane again".

### 4.11 Extract one pure split model

**Adjust (architecture, not UX):** put the table in one module both surfaces
import. sase-1eg's "mirror without importing" rule is revoked for this
feature. Content policy (clone vs next deck), zoom, persistence, and chrome
stay local.

---

## 5. Keys

### Agents tab (configurable, `default_config.yml`)

| Action | Default | Gated |
|---|---|---|
| `toggle_deck_split_below` | `backslash` | Agents tab |
| `toggle_deck_split_right` | `vertical_line` | Agents tab |
| `toggle_deck_focus` | `ctrl+f` | 2+ panes (cycle +1, not toggle) |
| `cycle_deck_focus_prev` (new) | `ctrl+b` | 2+ panes |
| `swap_deck_panel_next` (new) | `ctrl+shift+f` | 2+ panes |
| `swap_deck_panel_prev` (new) | `ctrl+shift+b` | 2+ panes |
| `close_deck_panel` (new) | `ctrl+shift+d` | 2+ panes |
| `grow_deck_panel` / `shrink_deck_panel` | `}` / `{` | 2+ panes; inner vs outer per §4.6 |

`ctrl+b` is already tab-disjoint: `scroll_prompt_up` is hidden on Agents
(`test_scroll_prompt_hidden_on_agents_while_decks_on`). Add
`{cycle_deck_focus_prev, scroll_prompt_up}` to the keymap registry's
disjoint set next to the existing
`{toggle_deck_focus, scroll_prompt_down}` pair.

`Ctrl+Shift+O` already ships on Agents, so shift-chords are in the product's
vocabulary. `Ctrl+Shift+J/K` are documented as often collapsing to
`Ctrl+J/K` under tmux+kitty; the same caveat belongs on the new chords. Do
not add a surviving-tmux fallback in v1; the existing close/focus keys
(`\`, `|`, `Ctrl+F`, `Ctrl+B`) cover users whose terminal eats shift.

### Pager (hard-coded, like the rest of pager keys)

Same chords. Add them to the `_screen_host.py` passthrough that already
exempts `backslash`, `vertical_line`, `ctrl+f`, `plus`, `minus` from label
swallowing:

```
backslash, vertical_line, ctrl+f, ctrl+b,
ctrl+shift+f, ctrl+shift+b, ctrl+shift+d,
plus, minus
```

Footer, split mode: `^F/^B pane` before `/ search`; `q close pane` as
today. `Ctrl+Shift+D` can stay in `?` only (it aliases `q`). Swap stays in
`?` only.

`Ctrl+W` `Ctrl+W` becomes "next pane" (alias of `Ctrl+F`), not a boolean
toggle.

---

## 6. Beauty

The look spec from sase-1eg still holds: single-pane goldens stay
byte-identical; split panes are independently framed; focus is full-strength
accent, unfocused is ~35%; only the focused pane paints jump labels.

Three-pane beauty is the T-junction, not new chrome.

**Layout mechanism (recommended): dock the spine.** Textual 8.0.1 supports
`dock: top|bottom|left|right`. A docked child leaves the flow; the remaining
children layout in the leftover region. That is exactly a T-junction without
reparenting:

| Kind | Parent layout | Spine | Nested pair in the leftover |
|---|---|---|---|
| MAIN_STACKED, spine END | horizontal | `dock: bottom` | side by side |
| MAIN_STACKED, spine START | horizontal | `dock: top` | side by side |
| MAIN_SIDE, spine END | vertical | `dock: right` | stacked |
| MAIN_SIDE, spine START | vertical | `dock: left` | stacked |
| STACKED / SIDE / SINGLE | as today | panel 2 `.hidden`, no dock | — |

Each `DeckPanel` / `PagerView` keeps a stable identity (the pane you opened
second is still widget 1). Role classes (`-spine`, `-nested-a`, `-nested-b`)
move between widgets as the table requires. Content does not hop widgets on
nest/rotate, so a Files diff worker is not restarted because the spine
changed sides.

Textual also has `layout: grid` with `column-span` / `row-span`. Grid fill
order fights spine-START (the spanning cell wants to be first in child
order). Dock avoids that. Use grid only if docked percentage heights
misbehave in a prototype; both are available in 8.0.1.

**Frames.** Keep per-pane `round` / `solid` borders. The T will show a
double line where three frames meet — the same double line 2-pane already
has between neighbors. Do not invent a custom box-drawing T in v1. A later
polish pass can switch inner edges to single-cell rules; it is not this
epic.

**Zoom.** `ZoomChrome` already carries `panel_count`. For 3-pane drop the
2-pane half glyphs (`◀`/`▶`/`◰`/`◱` in `_ZOOM_HALF_GLYPHS`) and show
`n of 3`. Snapshot the full 3-pane state; `Z` restore is exact, picker
capital letters still use `exit_zoom_keeping_panels`.

**Footer / help.** Prefer compact verbs (`^F/^B pane`, `^⇧D close`) over
layout names. The help sheet's Panes group lists the cyclic table with the
ASCII figures above. Glossary strand `Deck Panel` must learn three panels
and the spine; pager docs get a matching "Split panes" rewrite.

---

## 7. Implementation shape

### Shared pure module

New `src/sase/split_layout.py` (no Textual, no ACE, no pager imports):

```python
class SplitKind(StrEnum):
    SINGLE = "single"
    STACKED = "stacked"
    SIDE = "side"
    MAIN_STACKED = "main-stacked"
    MAIN_SIDE = "main-side"

class SpineSide(StrEnum):
    START = "start"  # top / left
    END = "end"      # bottom / right

@dataclass(frozen=True, slots=True)
class SplitState:
    kind: SplitKind = SplitKind.SINGLE
    focused: int = 0          # identity index into panes
    panes: tuple[int, ...] = (0,)  # identity ids, spatial meaning via roles()
    ratio: int = 50           # outer
    inner_ratio: int = 50
    spine_side: SpineSide = SpineSide.END
    last_focused: int | None = None
```

Functions (all total, all tested without Textual):

- `toggle_axis(state, axis, *, fits_nest: bool) -> SplitState`
- `cycle_focus(state, delta) -> SplitState`
- `swap_focus(state, delta) -> SplitState`  # permute identities, focus follows
- `close_focused(state) -> SplitState`
- `close_spine(state) -> SplitState`
- `roles(state) -> {id: SPINE|NESTED_A|NESTED_B|ONLY}`
- `reading_order(state) -> tuple[int, ...]`
- `other_target(state, source_id) -> int`
- `step_ratio(state, grow: bool) -> SplitState`  # inner vs outer per focus
- `fits(kind, spine_side, ratio, inner_ratio, width, height) -> bool`

`decks/layout.py` and `pager/split.py` become thin wrappers: decks add zoom,
`choose_new_panel`, and persistence; pager adds clone-seed and
`_split_in_flight` teardown. Existing names (`DeckLayout.TOP_BOTTOM`,
`PagerSplitLayout.BELOW`) can remain as aliases of `STACKED` during the
migration so not every test file moves at once — but the transition table
must have a single implementation.

### Agents widgets

- `DeckArea.compose` grows a third `DeckPanel` (`#agent-deck-panel-2`,
  `.hidden`). Same pattern as panel 1 today.
- `apply_state` learns four new area classes (`-main-stacked-start/end`,
  `-main-side-start/end`) plus `-inner-30/50/70`, and sets per-panel role
  classes. Hidden unused panel(s) stay `display: none`.
- `visible_panels()`, `focused_panel()`, click-to-focus, and
  `_reload_duplicate_deck_from_cache` iterate whatever is visible (1–3).
- **Only visible panels receive document updates.** A hidden third panel
  must not load Files/Tools on every agent switch (TUI perf rule 6:
  selective updates; three Main/Files/Tools/FINAL widget trees are
  expensive). Lazy-load on first show.
- `MAX_PANELS = 3`. Bump `SCHEMA_VERSION` to **2**. Unknown v2 layouts fail
  open the way unknown v1 layouts already do. v1 files still load (2-pane).
  An old TUI that cannot read v2 already fails open to empty; do not let it
  save a truncated 2-panel overwrite — the version bump is what prevents
  that.
- `choose_new_panel`'s `shown` set becomes the visible decks, so a third
  pick walks to the remaining contentful deck.
- `panel_position_label` grows `top-left` / `top-right` / `bottom` / …
  for picker copy.

### Pager host

- `_views` is a list of identities in any order; spatial placement is CSS
  roles, not list order. Mount the third `PagerView` the same way the second
  is mounted today (clone seed, `_split_in_flight` guard, async-safe
  remove).
- `show_in_other_view` uses `other_target`. From SINGLE it still opens
  STACKED if it fits else SIDE — never MAIN_*.
- `is_split` becomes `kind is not SINGLE` (already roughly this).
- `#pager-panes` CSS grows the four 3-pane classes; inline `fr` widths on
  2-pane stay as they are.

### Availability / footer / help

- `_DECK_SPLIT_ONLY_ACTIONS` gains the four new actions.
- Footer `other panel` becomes `pane` (it is no longer binary).
- Palette / command catalog rows for the new actions, Agents-tab gated.

---

## 8. Risks

| Risk | Mitigation |
|---|---|
| 3× deck widgets on every Agents view | Pre-compose hidden, **lazy-load** on first visible; `visible_panels()` is the only refresh set |
| Agent j/k p95 regresses | Existing `SASE_TUI_PERF=1` budget; do not refresh hidden panels; keep DetailPanelDebouncer |
| Nest-replaces-rotate muscle memory | Fallback rotate when nest does not fit; docs/changelog callout; two-keystroke recover (`\|` then `\`) |
| `Ctrl+Shift-*` eaten by tmux | Document; `Ctrl+F`/`B` and `\``\|`/`q` still complete the job |
| Dock percentage vs `fr` quirks | Spike dock in a 20-line Textual toy before the epic; grid+span is the fallback |
| Persistence clobber (sase-1bk) | Schema v2; fail open; never write 3-pane through the v1 encoder |
| `query_one("#id")` cache across panes | sase-1eg already warned: pane-local queries, never host-level `#pager-body-scroll` |
| History / time-band bugs from sase-1eg landing | 3-pane `Ctrl+W` tests must register a history provider (the gap sase-1ef.land found) |
| Zoom vs 3-pane (sase-19e) | Snapshot the full `SplitState`; picker uses `exit_zoom_keeping_panels` |
| Golden drift on 60×30 | Do not add 3-pane goldens at 60 columns; 120×40 only |

---

## 9. Tests and docs (the acceptance bar)

Pure model (no Textual), one table-driven file that *is* the spec:

- Every cell of the §3 transition table, including spine-side from focus.
- Fit fallback: nest refused → rotate, not toast-and-no-op, when the other
  2-pane fits.
- `cycle_focus` wrap, `swap_focus` follows content, `close_focused` vs
  `close_spine`.
- Ratio stepping inner vs outer; clamp.
- `other_target` prefers `last_focused`.

Pilot:

- Deck: `\` `\|` nest/rotate/close-spine; third panel shows the next
  contentful deck; `Ctrl+F`/`B`; swap; `Ctrl+Shift+D`; zoom snapshot
  round-trip; picker capital letter fills last-focused; persistence
  round-trip of a 3-pane state.
- Pager: same keys; clone seed on the third pane; `q` closes focused;
  `Ctrl+W` into last-focused; labels only on the focused pane; small-window
  nest fallback; ACE modal still does not split the Agents deck
  (`test_view_files_pager_split_keys.py`).
- Existing 2-pane tests keep passing with aliases.

Visual goldens (120×40, dark is enough unless a frame bug is
theme-specific):

- MAIN_STACKED spine END, a nested pane focused (labels visible only there)
- MAIN_STACKED spine START
- MAIN_SIDE spine END
- MAIN_SIDE spine START
- 2-pane goldens unchanged
- Single-pane goldens byte-identical (sase-1eg invariant)

Docs:

- `docs/ace.md` Agents keys + deck split section
- `docs/pager.md` Split panes
- glossary `Deck Panel` (and the still-open `sase-1bg` Deck View strand,
  adjacent, not a duplicate)
- help sheet Panes group
- `default_config.yml` comments

---

## 10. Suggested epic shape (for whoever plans this)

Not this research's job to file, but the cuts are obvious and serial where
the model must exist first:

1. **shared-model** (medium) — `split_layout.py` + table tests; wrappers
   keep today's 2-pane behavior so this phase is user-invisible.
2. **deck-three** (medium) — third panel, dock CSS, persistence v2, zoom,
   picker, lazy-load.
3. **deck-keys** (small) — nest/rotate/close-spine, `Ctrl+B`, swap, close,
   footer, availability, glossary.
4. **pager-three** (medium) — third view, same table, `Ctrl+W` /
   last-focused, host passthrough, history tests.
5. **polish** (small) — 3-pane goldens, look pass, docs.

Phases 2 and 3 can merge. 4 can overlap 2 once phase 1 is on master.
Single-pane pixel identity is an invariant of every phase.

---

## 11. Recommended solution (summary)

Ship a **closed 5-layout T-junction model**, not a tiler.

- `\` / `|` keep their glyphs and gain an axis mnemonic: split that axis,
  or nest into it, or rotate when it is already the inner split, or drop
  the spine when it is the outer split, or return to one pane when it is
  the only split.
- The unsplit pane is the **spine**. Its side is the pane you did not split.
- `Ctrl+F` / `Ctrl+B` walk a spatial ring. `Ctrl+Shift+F` / `Ctrl+Shift+B`
  swap along that ring (focus follows content). `Ctrl+Shift+D` closes the
  focused pane and is inert on single.
- One shared pure `SplitState`. Decks and pager wrap it. Dock the spine for
  the T. Lazy-load the third deck panel. Persist schema v2. Do not let
  `Ctrl+W` or the picker create a third pane.
- When a 3-pane nest cannot fit, **rotate**, which preserves sase-1eg on
  small windows.
- Unify Agents same-key unsplit onto **keep focused**.
- Single-pane rendering stays pixel-identical. 3-pane goldens live at
  120×40.

That is the design I would implement.
