# Three-pane splits for the Agents deck and the pager

Consolidated report · lead researcher · 2026-10-02 · sase master `c4b907e111` · Textual
8.0.1

Sources: five independent reports (`__cdx`, `__cld`, `__grk`, `__mus`, `__gem` in this
directory) plus my own checks. I re-read the split code on both surfaces. I re-ran the
flat-grid layout prototype and confirmed it never remounts a pane. I verified the kitty
and tmux key settings on athena and in the chezmoi dotfiles. I also found the original
deck-split rationale in `research:202609/agents_tab_decks_and_cards`.

---

## 1. Bottom line

**Build it.** Keep the `\` / `|` grammar you sketched. Implement it once, as a shared and
closed model with seven geometries, and add a few corrections. All five researchers
agree three panes are worth having, and so do I. On the Agents tab, Main + Files + Tools
side by side is the triage loop that `choose_new_panel()` already anticipates. In the
pager, three panes let you compare a document, a reference and a past version. Capping
the feature at three panes in two T-shaped families keeps every state enumerable and
testable. It keeps SASE from becoming a general window manager.

The design in one paragraph:

> `\` draws a horizontal divider (panes stacked) and `|` a vertical one (side by side).
> **If that divider already spans the whole area, the key erases it, and the side you are
> on grows to fill the space. Otherwise, with fewer than three panes, the key draws the
> divider through the focused pane. With three panes, the key turns the layout.**
> `Ctrl+F` / `Ctrl+B` move focus around a ring. `Ctrl+Shift+F` / `Ctrl+Shift+B` move the
> focused content around that ring. `Ctrl+Shift+D` closes the focused pane.

Four facts change how this should be built:

1. **A live bug blocks the work: sase-1er.** On master, closing a pager split (`q`,
   `Esc`, exhausted `Backspace`, or the same split key) leaves an empty body. Both close
   paths in `src/sase/pager/_screen_split.py` call
   `query_one("#pager-panes").remove_children()`, which removes the surviving pane too.
   Nothing remounts it. Two researchers reproduced this independently, and I confirmed it
   in the code. Every new close and collapse path would reuse this teardown, so fix it
   first.
2. **The requested `ctrl+shift` chords do not reach sase on your setup today.**
   - Kitty 0.41.1 keeps the default `kitty_mod = ctrl+shift`. Its default maps send
     `kitty_mod+f` and `kitty_mod+b` to `move_window_forward` and `move_window_backward`.
     I verified this in `/usr/lib/kitty/kitty/options/definition.py`. Your `kitty.conf`
     only remaps `cmd+f` and `ctrl+shift+y`.
   - tmux 3.5a reports `extended-keys off` and `extended-keys-format xterm`. Textual
     8.0.1 parses CSI-u (`ESC[100;6u` → `ctrl+shift+d`) but not tmux's xterm form
     (`ESC[27;6;100~` → no event; cdx tested this).
   - As a result, `ctrl+shift+d` arrives as plain `ctrl+d`: half-page scroll in the
     pager and `scroll_detail_down` on Agents. That is a silent misfire.
   - The project already has a precedent. `docs/ace.md` leaves `Ctrl+Shift+J/K` unbound
     for exactly this reason.
3. **Two keys are already taken.**
   - `ctrl+shift+d` is bound to the env-gated `debug_leak_snapshot`
     (`ace/tui/bindings.py:306`).
   - `ctrl+b` belongs to `scroll_prompt_up`. That action is disabled on Agents, so it
     needs a tab-disjoint registry pair, just as `ctrl+f` already has.
4. **Everything assumes two panes.** Both models compute the other pane as
   `1 - focused`. The deck's click-to-focus calls `toggle_focus`. `DeckArea.panel(i)`
   resolves panels by DOM query order. Persistence caps `MAX_PANELS = 2`. Pager
   `Ctrl+W` and the deck picker's capitals target "the other pane". This is more than
   adding two enum values.

---

## 2. What exists today

| | Agents deck (`ace/tui/widgets/decks/`) | Pager (`src/sase/pager/`) |
| --- | --- | --- |
| Layouts | `SINGLE`, `TOP_BOTTOM`, `LEFT_RIGHT` | `SINGLE`, `BELOW`, `BESIDE` |
| Open | `\` below, `\|` beside; new pane focused, 50/50 | same |
| Same key again | Unsplit to **panel 0**: `\` `\` returns to the original deck | Unsplit keeping the **focused** pane (vim `C-w o`) |
| Other key | Rotate; decks, focus and ratio kept | Rotate; views, focus and ratio kept |
| Focus | `Ctrl+F` toggle; docs say "`Ctrl+B` has no Agents behavior" | `Ctrl+F` toggle |
| Close focused | none | `q` / `Esc` / exhausted `Backspace` |
| Resize | `}` / `{` through 30/50/70 | `+` / `-` through 30/50/70 |
| New pane content | `choose_new_panel()`: next unshown deck with content (FINAL only on positive content) | Clone of the focused pane (`split_seed()`) |
| Widgets | Two precomposed `DeckPanel`s; ratio CSS keyed by panel ID | `PagerView`s mounted into a `Vertical`; inline `fr` sizes |
| Fit guard | none | `MIN_STACKED_PANE_HEIGHT = 7`, `MIN_BESIDE_PANE_WIDTH = 32` |
| Persistence | `~/.sase/ace_agents_deck_state.json`, schema 1, `MAX_PANELS = 2`; any other schema version rejects the whole file | none (session only) |
| Zoom | `Z` snapshots the state and shows the focused panel; chrome `◧ 1 of 2 · Z restore` | none |

sase-1eg, the pager split epic, deliberately mirrored the deck model without importing
it, and listed "more than two panes, or nested splits" as a non-goal. This request is
the sequel that lifts that non-goal. The two models have already drifted apart, so a
third copy of the algebra is not acceptable.

---

## 3. Critique of the request

### What is right

- **Cap at three panes and two families.** Recursive vim/tmux splitting would be a
  second product. Tiled 2×2 and three-equal-stripe layouts are pretty, but wrong for
  decks: a T-shape keeps one full-width or full-height reading region, which is the
  point. tmux calls these geometries `main-horizontal` / `main-vertical`, and kitty
  calls them Fat / Tall. That is good precedent for the shapes, though not for the keys.
- **No new layout keys.** Reaching for the other split key to get a third pane is the
  move a user will actually try. The grammar is complete with two keys.
- **`Ctrl+B` as the reverse of `Ctrl+F`.** With three panes, a ring is mandatory.
- **Swap with previous / next.** It completes the set. `Ctrl+F` moves *you*;
  `Ctrl+Shift+F` moves *the content*. It also makes it cheap to promote a pair pane
  into the big slot.
- **A close-focused key.** The deck has none today, and its same-key unsplit always
  keeps panel 0. With three panes that is the wrong survivor.

### What is wrong or missing

1. **"The larger pane" is the wrong identity.** At ratio 30, the full-width pane gets
   30% of the height while each pair pane gets 35% of the area, so it is smaller. Use a
   structural definition: the **main pane** is the one that spans the full width or
   height. All five reports agree.
2. **"Two new views" are really four geometries.** Splitting the focused pane means the
   T can open either way: main-top or main-bottom, main-left or main-right. Do not force
   a canonical picture. That would move content you did not touch.
3. **"Switch to the other 3-pane view" needs a definition.** Make it a **transpose**,
   a reflection across the main diagonal: main-top ↔ main-left and
   main-bottom ↔ main-right. The pair keeps its order, the top-left pane never moves, and
   pressing the key twice restores the exact state. That makes it the three-pane
   counterpart of today's two-pane rotate. cdx, cld and grk independently reached the
   same mapping.
4. **The literal rule can close the pane you are reading.** In a stacked 3-pane view
   with the main pane focused, "`\` closes the larger pane" destroys your focused pane.
   That breaks the pager's existing principle: the same split key keeps what you are on.
   See §5.2 and adjustment A2.
5. **Two-pane rotate disappears.** The opposite split key now nests a third pane
   instead. In the pager, that was the only way to change orientation without losing a
   pane's trail. The workaround (`|` nest, `\` erase) is not a rotation: it replaces the
   unfocused pane with a new clone or deck. This is a real regression. It needs either
   an explicit turn key (A6) or a release note that accepts it.
6. **"The other pane" is undefined with three panes.** This affects pager
   `Ctrl+W <label>`, doubled `Ctrl+W`, deck picker capitals (`p` then `M`/`F`/`T`/`N`)
   and `show_in_other_view`.
7. **One ratio cannot describe a T.** There is an outer split and an inner split.
8. **Unspecified:** where focus goes after a close, which divider grow/shrink moves, the
   minimum terminal size, and what zoom does with three panels.
9. **Key deliverability and collisions** (§1, facts 2 and 3).

---

## 4. Where the researchers disagreed, and how I resolved it

| Question | Positions | Resolution |
| --- | --- | --- |
| Adopt the requested grammar? | cdx, cld, grk: yes. mus: yes, but with "3-pane + same axis key → undo the nest". gem: no — keep 2-pane rotate, and press the same key again to go to 3 panes. | **Adopt it.** gem's variant contradicts the explicit requirement that the same key returns to a single pane. mus's variant breaks the one-rule grammar, and closing the new pane already undoes a nest (close∘split = identity, §6.4). |
| Same-key unsplit on the deck | cdx, grk, mus: unify on keep-focused. cld: keep panel 0 for the `\` `\` peek. | **Unify on keep-focused**, as a flagged behavior change (A3). The 2026-09 deck research (A17) specified keep-focused, and the implementation diverged. Keep-focused makes the same key ("only this") and close ("not this") exact complements on both surfaces. It also generalizes to three panes as "the side you're on survives". The peek becomes `\` … `ctrl+x`. |
| Erasing the main pane while it is focused | cdx, grk: close it anyway and move focus. cld: the main pane survives and the layout goes single. | **The focused side survives** (A2). This is the same rule as the 2-pane same-key unsplit, applied to the side of the divider you are on. The literal rule is a one-line fallback if you prefer layout determinism. |
| Turn semantics | cdx, cld, grk: transpose. grk called it "clockwise", but its mapping is the transpose. | **Transpose.** It is self-inverse and pins the top-left pane. |
| A nest that does not fit | grk: fall back to rotating the 2-pane. cdx, cld: refuse. | **Refuse with a toast naming what would fit.** A key should have one meaning per state, independent of terminal size. |
| "Other pane" target | cld, grk, gem: most recently focused (MRU). cdx, mus: next in the ring. | **MRU, with the target previewed while armed.** The pane you just left is almost always the one you are working against (vim `C-w p`). Previewing the target frame answers cdx's hidden-state objection. |
| Model shape | cdx: bounded split tree. cld: flat `PaneGrid` (axis, ratio, pair). grk: `kind` + `spine_side` + two ratios. gem, mus: enum values plus a second ratio. | **cld's flat `PaneGrid` with stable pane IDs.** It is isomorphic to cdx's depth-2 tree and grk's spine model, and it projects directly onto a CSS grid. A plain enum without pane IDs (gem) loses identity on swap. |
| Rendering | cld: flat CSS grid (prototyped). grk: dock the spine. cdx: custom `Layout.arrange`. gem: grid with a fixed master at index 0. | **Flat CSS grid.** I re-ran the prototype (§6.2): all shapes are exact, and there are zero mount/unmount events across six transitions. Dock works but needs two mechanisms. A custom `Layout` is more code than needed. gem's fixed-index CSS ignores which side the T opens on. |
| Persistence | cdx, grk: bump to schema v2. cld: additive v1. | **Additive v1.** The decoder rejects any other schema version wholesale, so v2 makes every older sase sharing `~/.sase` discard the whole layout. Additive v1 lets an old reader truncate to a valid 2-pane. |
| Shift-chord fallbacks | cld: `<` / `>` swap, `ctrl+x` close. cdx: `Ctrl+W Ctrl+…` prefix. gem: `ctrl+w` / leader. grk: none, just document. mus: needs some. | **cld's single-key aliases.** I verified they are free on the pager and tab-disjoint on Agents. A prefix is heavier, and Agents has no `ctrl+w` prefix today. Also fix the terminal chain (phase 0). |
| Minimum size | mus: about 100 columns (3 × 32). gem: "need 80×24". cdx, grk: about 64 × 14 of pane area. | **About 64 × 14 of pane area.** A T never has three panes along one axis, so mus's arithmetic applies only to stripes. Your current tmux window is 205×65. With the 60-column node list expanded, each Agents pair pane gets about 70 columns. |
| Delivery order | cld, mus: pager first. grk, gem: deck first. | **Model and keys on 2 panes first, then the pager, then Agents** (§8). The pager mounts dynamically and persists nothing, so it is the cheapest place to prove the adapter. |

---

## 5. Recommended design (UX contract)

### 5.1 Vocabulary and geometries

- In code, docs and help, say **stacked** (`\`) and **side by side** (`|`). vim and tmux
  use "horizontal" and "vertical" in opposite senses, so keep those words only as
  aliases.
- **main pane:** the pane that spans the full width or height.
- **pair:** the other two panes.
- **reading order:** the outer first region, then the second; within the pair, first
  then second.
- **turn:** transpose.
- The pager keeps the word "pane" and Agents keeps "panel".

```
 single     R2 stacked    C2 side by side
┌──────┐    ┌──────┐       ┌───┬───┐
│  A   │    │  A   │       │ A │ B │
│      │    ├──────┤       │   │   │
└──────┘    │  B   │       └───┴───┘
            └──────┘
 R3 main-top  R3 main-bottom  C3 main-left   C3 main-right
┌──────┐     ┌───┬───┐       ┌───┬───┐      ┌───┬───┐
│  A   │     │ B │ C │       │   │ B │      │ B │   │
├───┬──┤     ├───┴───┤       │ A ├───┤      ├───┤ A │
│ B │C │     │   A   │       │   │ C │      │ C │   │
└───┴──┘     └───────┘       └───┴───┘      └───┴───┘
```

### 5.2 Split-key transitions (both surfaces)

| From | `\` (stacked divider) | `\|` (side-by-side divider) |
| --- | --- | --- |
| single | **R2**: new pane below, focused, 50/50 | **C2**: new pane right, focused, 50/50 |
| R2 | **single**, keeping the focused pane | **R3**: the focused pane splits; the new pane opens to its right and takes focus; the unfocused pane becomes main and does not move or resize |
| C2 | **C3**: the focused pane splits; the new pane opens below it and takes focus; the unfocused pane becomes main | **single**, keeping the focused pane |
| R3 | Erase the full-width divider. Focus in the pair → **C2** of the pair, pair ratio kept. Focus on main → **single** (main). | **Turn → C3**: main-top ↔ main-left, main-bottom ↔ main-right; pair order, focus and both ratios kept |
| C3 | **Turn → R3** | Erase the full-height divider. Focus in the pair → **R2** of the pair. Focus on main → **single** (main). |

Examples: R2 with the top pane focused, then `|`, gives main-bottom. R2 with the bottom
pane focused, then `|`, gives main-top.

`|` / `\` never create a fourth pane. `Ctrl+W` and the deck picker never create a third
pane; only split keys do. From a single pane, `Ctrl+W` and the picker still open a
2-pane, as today.

### 5.3 Focus, swap, close, resize

- **Focus.**
  - `Ctrl+F` / `Ctrl+B` move to the next / previous pane in reading order, and wrap.
  - Both are inert on a single pane. With two panes they coincide.
  - A click focuses the clicked pane by ID. Today it calls `toggle_focus`.
  - Doubled `Ctrl+W` in the pager stays an alias of `Ctrl+F`.
  - Exactly one pane has logical focus, and Textual focus must agree with it.
- **Swap.**
  - `Ctrl+Shift+F` / `Ctrl+Shift+B` (aliases `>` / `<`) exchange the focused pane's
    whole session with the next / previous pane, and wrap. A session means document or
    deck, card, scroll anchor, search, folds, history and in-flight work.
  - Geometry and ratios belong to slots and do not change. Focus follows the content.
  - From any pair pane, one press puts that pane in the main slot.
  - With two panes, both directions coincide. Inert on a single pane.
- **Close.**
  - `Ctrl+Shift+D` (alias `ctrl+x`; in the pager `q` / `Esc` / exhausted `Backspace`
    when split) closes the focused pane. Active only with two or more panes.
  - A closed pair member's sibling takes over its space. The result is a 2-pane on the
    outer axis, with the outer ratio kept.
  - A closed main pane leaves the pair to fill the area. The result is a 2-pane on the
    inner axis, with the pair ratio kept.
  - In a 2-pane, close leaves a single pane.
  - Focus goes to the most recently focused survivor, falling back to the first in
    reading order.
  - Close is the exact inverse of split: positions, ratios and focus all return.
  - `Ctrl+Shift+D` never exits a single-pane pager; `q` still does.
- **Resize.**
  - Pager `+` / `-` and Agents `}` / `{` step the split that directly separates the
    focused pane from its sibling: the inner split for a pair pane, the outer split for
    the main pane. Steps stay 30/50/70.
  - A new inner split starts at 50.
- **"Other pane".** Pager `Ctrl+W <label>`, doubled-`Ctrl+W` arms and deck picker
  capitals target the **most recently focused other pane**, falling back to the next in
  reading order.
  - Capture the target's pane ID when the action is armed.
  - If a structural change removes the target before an async result lands, cancel with
    a short message instead of redirecting the result.
  - Push history only in the destination, preserving the sase-1eg fix that keeps the
    source's history generation untouched.
- **New-pane content.**
  - Pager: a clone of the focused pane, with independent history caches. Unchanged.
  - Agents: `choose_new_panel()` over every visible deck. With Main and Files shown,
    the third panel opens on Tools, or on FINAL when FINAL has positive content. The
    existing duplicate fallback stays.
- **Fit.**
  - Every new 3-pane geometry (nest or turn) must give each pane the surface minimum.
    For the pager that is 7 rows × 32 columns. For Agents, add new constants of about
    8 × 40, tuned on real screens.
  - Otherwise refuse with a toast that names what would fit. Example: "Not enough room
    for a third panel — `ctrl+s` collapses the node list".
  - Never collapse the node list automatically. Leave the Agents 2-pane path unguarded,
    as today.
  - Shrinking the terminal never closes a pane.
- **Zoom (Agents).**
  - `Z` snapshots the whole state.
  - The chip names the position: `◲ 3 of 3 · Z restore`.
  - Focus, swap, close and resize are disabled while zoomed.
  - A split key while zoomed **only restores** the layout. Today it drops the snapshot
    and splits the zoomed panel, which would silently discard two hidden sessions (A8).

### 5.4 Keys

| Action | Agents default (configurable in `default_config.yml`) | Pager (hard-coded) | Active |
| --- | --- | --- | --- |
| Split stacked / side by side | `backslash` / `vertical_line` | same | always (Agents tab) |
| Focus next / previous | `ctrl+f` / `ctrl+b` | same | 2+ panes |
| Swap with next / previous | `ctrl+shift+f,greater_than_sign` / `ctrl+shift+b,less_than_sign` | same | 2+ panes |
| Close focused | `ctrl+shift+d,ctrl+x` | same, plus existing `q` / `Esc` | 2+ panes |
| Turn (optional, A6) | `ctrl+t` | `ctrl+t` | 2+ panes |
| Grow / shrink | `}` / `{` | `+` / `-` | 2+ panes |

Plumbing that must land with the keys:

- **Agents keymaps:** keymap dataclass and metadata fields for the new actions.
- **Registry tab-disjoint pairs:**
  - `{toggle_deck_focus_reverse, scroll_prompt_up}`
  - `{swap_deck_panel_prev, start_ancestor_mode}` and
    `{swap_deck_panel_next, start_child_mode}` (`<` / `>` belong to the Artifacts tab)
  - `{turn_deck_layout, beads_toggle_note_audience}`
- **Availability:** add the new actions to `_DECK_LAYOUT_ACTIONS` and
  `_DECK_SPLIT_ONLY_ACTIONS`.
- **Discoverability:** palette rows, help modal and footer.
- **Pager:** add the keys to `BINDINGS` and to the `_screen_host.on_key` passthrough
  list. That list already lets `backslash`, `vertical_line`, `ctrl+f`, `plus` and
  `minus` win over an armed label prefix.
- **Collision:** move `debug_leak_snapshot` off `ctrl+shift+d`.

I checked that `<`, `>`, `ctrl+b`, `ctrl+t` and `ctrl+x` are all unbound in the pager.

### 5.5 Beauty spec

1. **Spatial stability is the aesthetic.**
   - A split subdivides only the focused pane.
   - A turn pins the top-left pane.
   - A close puts back exactly what was there.
   - Swap, turn, resize and focus never remount anything, so text does not jump.
2. **Exactly one full-strength frame.** Keep each surface's frame language: the pager's
   `round` section-accent frames and the deck's `solid` deck-accent frames, at 35% when
   unfocused.
   - Do not frame the pair as a group. Do not draw custom box T-junctions in v1; the
     doubled edge where frames meet already exists in 2-pane.
   - Only the focused pager pane paints link and time-band labels, as today.
3. **Name positions only when naming a target.** Extend the deck's zoom glyphs
   `◧ ◨ ⬒ ⬓` with `◰ ◱ ◲ ◳`. All eight are East-Asian-width N and one cell wide; I
   checked this with `rich.cells`.
   - Main-top reads `⬒ ◱ ◲`; main-bottom `◰ ◳ ⬓`; main-left `◧ ◳ ◲`; main-right
     `◰ ◱ ◨`.
   - Use them in the zoom chip, the picker hint ("show in the ◲ bottom-right panel") and
     the armed `^W…` footer. Keep steady-state titles quiet.
   - Caveat: `◰`–`◳` draw the quadrant as an outline rather than a fill, so they read
     lighter than `◧◨⬒⬓`. Judge this in a live render.
4. **Preview the target while `Ctrl+W` is armed.** The target pane's frame lifts to
   about 70% strength until the label lands or the arm is canceled.
5. **The footer does not grow.**
   - With three panes, `^F/^B pane` replaces `^F pane`. The pager keeps `q close pane`.
   - Swap, close and turn live in `?` help and the palette.
   - Help leads with the one-sentence grammar and the seven-geometry diagram.
6. **Narrow pair panes truncate gracefully.**
   - The deck or document name is kept; optional title detail goes first.
   - Each pane budgets its chrome from its own height.
7. **No animation.** Toasts appear only on refusal, never on success; the layout change
   is its own feedback.

---

## 6. Architecture

### 6.1 One shared, pure, presentation-only model

Put it in `src/sase/ace/tui/util/pane_grid.py`. The pager already imports
`sase.ace.tui.util` (`pump_tasks`, `trace`), so this adds no new dependency direction.
The module has no Textual imports and no deck or pager concepts. This is presentation
layout, which no other frontend has to match, so it stays out of `sase_core`. Rust-core
boundary litmus: all five reports agree.

```python
class Axis(StrEnum):
    ROWS = "rows"   # stacked, `\`
    COLS = "cols"   # side by side, `|`

@dataclass(frozen=True, slots=True)
class Pair:
    region: int       # outer region holding the pair: 0 = top/left, 1 = bottom/right
    ratio: int = 50   # first pair member's share

@dataclass(frozen=True, slots=True)
class PaneGrid:
    panes: tuple[int, ...] = (0,)   # stable surface-owned pane IDs, reading order, 1..3
    focused: int = 0                # pane ID
    axis: Axis | None = None        # outer split; None iff single
    ratio: int = 50                 # outer first region's share
    pair: Pair | None = None        # set iff 3 panes
    recent: tuple[int, ...] = ()    # MRU pane IDs

def press_split(g, axis, new_id) -> PaneGrid
def close_focused(g) -> PaneGrid
def cycle_focus(g, step) -> PaneGrid
def swap_focused(g, step) -> PaneGrid
def turn(g) -> PaneGrid
def step_ratio(g, direction) -> PaneGrid
def other_target(g) -> int | None
def fits(g, width, height, *, min_w, min_h) -> bool
def position_glyph(g, pane_id) -> str
def grid_spec(g) -> GridSpec   # columns, rows, fr tracks, spans, DOM order
```

Every transition is total: invalid input returns the state unchanged. `DeckAreaState`
and `PagerSplitState` become thin views over `PaneGrid`. Keep `DeckLayout` and
`PagerSplitLayout` as derived properties, so the existing comparisons across ACE
modules keep working while they migrate. The deck-only pieces stay local:
`choose_new_panel`, zoom and persistence. So do the pager-only pieces: clone seeding,
the `_split_in_flight` guard and the history generations.

If you reject A3, add one policy argument to `press_split`: `unsplit_keeps="first"` for
Agents in R2/C2. Every 3-pane rule stays shared.

### 6.2 Rendering: one flat CSS grid, no reparenting

Use one container with `layout: grid`, all panes as direct children, and
`grid-size` / `fr` tracks / `row-span` / `column-span` set from `grid_spec`. Use
`move_child` for order. I re-ran the prototype on Textual 8.0.1 at 100×40:

| Geometry | Regions `(x, y, w, h)` | DOM order |
| --- | --- | --- |
| R2, third pane `display:none` | A `(0,0,100,20)`, B `(0,20,100,20)` | A B (C) |
| main-top, outer 30 | A `(0,0,100,12)`, B `(0,12,50,28)`, C `(50,12,50,28)` | A B C |
| main-bottom, outer 70 | B `(0,0,50,28)`, C `(50,0,50,28)`, A `(0,28,100,12)` | B C A |
| main-left, outer 30 | A `(0,0,30,40)`, B `(30,0,70,20)`, C `(30,20,70,20)` | A B C |
| main-right, outer 70 | B `(0,0,70,20)`, A `(70,0,30,40)`, C `(0,20,70,20)` | **B A C** |

The widget objects were identical across all six transitions, with **zero**
mount/unmount events. This is the property that preserves scroll, workers, trails and
caches. Two consequences:

- **DOM order is not reading order.** Main-right needs `B A C` for row-major placement.
  Surfaces must hold explicit pane-ID → widget references.
  - Replace `DeckArea.panel(i)`, which uses query order.
  - Replace the deck's index-toggle click handler.
  - Never query repeated IDs from the host; the sase-1eg plan already warned about this.
- **The two ratios map onto the two track lists.** The outer ratio sets the rows of an
  R3, and the pair ratio sets its columns. The ID-keyed ratio CSS in
  `styles.tcss` (about lines 4020–4140) is replaced by inline grid styles.

Nested `Vertical` / `Horizontal` containers were rejected. R2 → R3 would require moving
pane B into a new container, which in Textual means `remove()` + `mount()`. That runs
`cancel_pump_free_tasks` for a `PagerView` and recomposes every deck for a `DeckPanel`.

### 6.3 Surface adapters

**Pager** (`_screen_split.py`, `_screen_host.py`, `_styles.py`):

- `#pager-panes` becomes the grid.
- `_apply_split_state()` computes `grid_spec`, applies the styles, reorders, and calls
  `set_pane_role` per pane.
- Close removes **only** the discarded view (the sase-1er fix).
- Mount the third view exactly as the second: clone seed, in-flight guard.
- Structural changes are transactions: validate fit, mount, revalidate after any await,
  then publish state. On failure, remove the orphan.
- Label arms, goto and search cancel per pane ID, never by index.

**Agents** (`decks/area.py`, `layout.py`, `picker.py`, `titles.py`,
`_agent_detail_deck_layout.py`):

- Add a third `DeckPanel`, either composed hidden or mounted lazily on first use.
  Decide by measuring startup under `SASE_TUI_TRACE=1`.
- `panel_index` becomes a lookup, not a constructor constant.
- Swap permutes `state.panels` plus `move_child`, so decks are not re-shown.
- **Only visible panels receive document updates.** This is TUI perf rule 6. With three
  panels visible, the debounced detail refresh does three times the work, so benchmark
  `j`/`k` p95 against the existing budget.
- Generalize these two-pane sites:
  - `other_panel_target` and `panel_position_label`
  - `_ZOOM_HALF_GLYPHS` → `position_glyph`
  - `visible_panels`
  - `_open_deck_split` (`area.panel(1)`)
  - `deck_picker_state`

### 6.4 Persistence: additive

- Keep `schema_version: 1` and raise `MAX_PANELS` to 3.
- Store `panels` in reading order, plus an optional `"pair": {"region": 0|1, "ratio": 50}`.
  `layout` keeps its existing values: `top-bottom` / `left-right` name the outer axis.
- An older reader ignores `pair` and truncates to two panels, which is still a valid
  R2/C2. A newer reader with no `pair` loads exactly as today.
- Validate pane uniqueness, focus membership and the ratio range. Recover to a smaller
  valid layout with a warning and never crash.
- Persist the edits made during zoom, not a stale snapshot.

---

## 7. Requirement adjustments (explicit)

| # | Your requirement | Adjustment | Kind | Why |
| --- | --- | --- | --- | --- |
| A1 | "closes the **larger** pane" | Close the structural **main pane** (spans full width or height) | clarification | Area-based "larger" is wrong at ratio 30. |
| A2 | `\` in stacked 3-pane / `\|` in side-by-side 3-pane always closes the larger pane | **When focus is in the pair**, the main pane closes, as requested. **When the main pane is focused**, it survives and the layout goes single. | change (main-focused case only) | A split key never closes the pane you're reading. "Erase the divider; your side grows" is the same rule as the 2-pane same-key unsplit. The literal rule is a one-line fallback. |
| A3 | (unspecified) which pane survives the 2-pane same-key unsplit | **Keep the focused pane on both surfaces.** This changes the Agents deck, which keeps panel 0 today. | change to existing behavior | It matches the approved 2026-09 deck design (A17) and the pager. It makes "only this" and "not this" exact complements. Cost: the deck's `\` `\` peek becomes `\` … `ctrl+x`. If you value the old peek, keep panel 0 for the deck's 2-pane case only (§6.1). |
| A4 | "split the currently focused pane" | The new pane opens right of / below the focused pane and takes focus. The unfocused pane becomes main and neither moves nor resizes. Four geometries, not two. | clarification | Matches the 2-pane rule and vim's `splitright` / `splitbelow`. |
| A5 | "switch to the other 3-pane view" | A **transpose**: pair order, focus and both ratios kept | clarification | Self-inverse; pins the top-left pane. |
| A6 | (implicit) the opposite key no longer rotates a 2-pane | **Add `ctrl+t` "turn"**, which transposes any split: R2 ↔ C2 and R3 ↔ C3. Optional; it can be deferred. | addition | Restores one-key rotation without discarding a pane's trail or deck. |
| A7 | `ctrl+shift+f/b`, `ctrl+shift+d` | Keep them as defaults, **plus `>` / `<` / `ctrl+x` aliases**, plus a phase-0 kitty/tmux fix. Move `debug_leak_snapshot` off `ctrl+shift+d`. | addition | The chords don't reach sase through your kitty → tmux chain. `ctrl+shift+d` misfires as `ctrl+d` scroll. |
| A8 | (unspecified) | Defines the following: MRU "other pane" with an armed-target preview; MRU focus after close; resize of the focused pane's parent split; per-split ratios; fit refusal for new 3-pane geometries; split keys while zoomed only restore | additions | Every rule the request left open, made explicit. |
| A9 | (implicit) | **Fix sase-1er before anything else.** | prerequisite | Every close path reuses the broken teardown. |

None of these adds more than three panes, synchronized scrolling, drag resizing, or
persisted pager layouts.

---

## 8. Rollout (epic shape)

0. **Terminal chain** (xsmall; dotfiles in chezmoi; needs your approval; can run in
   parallel).
   - kitty: unmap `kitty_mod+f` and `kitty_mod+b`. The documented pass-through form is
     `map kitty_mod+f` with no action. Optionally also `kitty_mod+o`, which kitty
     currently sends to `pass_selection_to_program`, so ACE's `Ctrl+Shift+O` is
     probably dead today too.
   - tmux: `set -s extended-keys on|always`, `set -s extended-keys-format csi-u`, and
     `set -as terminal-features 'xterm-kitty:extkeys'`.
   - Verify with `textual keys` inside tmux inside kitty, both locally and over SSH from
     the Mac. Nested layers need the same settings. This hop is the one thing nobody
     could test non-interactively.
1. **sase-1er** (small; bead is ready): remove only the discarded view. Add Pilot
   assertions that the survivor is still a child of `#pager-panes`, renders, and
   scrolls after `q`, `Esc`, exhausted `Backspace` and the same-key unsplit.
2. **Shared `PaneGrid` + grid rendering on both surfaces, still two panes**
   (medium).
   - Survivor unification (A3); `ctrl+b`; swap; close with aliases; move the debug
     chord.
   - This ships real value on its own: a reliable close and swap for decks.
   - Single-pane and 2-pane goldens stay byte-identical, apart from the intended
     survivor change.
3. **Pager three panes** (medium), behind a beta scaffolding flag. Follow the
   `sase_flags` memory, so `|` on a stacked split never means "rotate" on one surface
   and "nest" on the other at any master commit.
   - Nest, turn, erase, MRU `Ctrl+W` with preview, passthrough keys, help, goldens.
4. **Agents three panels** (medium–large, behind the same flag): third panel, fit
   guard, picker MRU, zoom chrome and restore-only split keys, additive persistence,
   palette/help/footer, perf benchmark.
5. **Land** (small): remove the flag. Update `docs/ace.md` (including the line
   "`Ctrl+B` has no Agents behavior"), `docs/pager.md`, the help sheets and
   `default_config.yml` comments. Update the `Deck Panel` glossary strand through
   `/sase_memory_write`. Write a release note for the changed opposite-key meaning and
   the deck survivor.

---

## 9. Acceptance bar

- **Exhaustive model table.** Seven geometries × focus position × every key, about 170
  transitions, pinned against a golden table that *is* the spec.
- **Hypothesis invariants** (`hypothesis` is already a dependency):
  - one to three unique panes, with focus in range
  - `turn∘turn = id`
  - `swap(+1)∘swap(−1) = id`
  - `close∘split = id`, ratios and focus included
  - focus cycling visits every pane
  - `grid_spec` regions tile the area with no gap or overlap
- **Pilot tests:**
  - After every close path, each survivor is mounted under the container, renders, and
    still scrolls, searches and follows links (the sase-1er regression).
  - Swap and turn keep widget identity and scroll.
  - Deleting each of the three panes; collapsing with main focused; rapid repeated keys
    during an async mount; click focus after a swap.
  - `Ctrl+W` targets MRU, and source and destination histories stay independent.
  - The ACE modal pager still never splits the Agents deck.
- **Persistence:** v1 files without `pair` load unchanged, 3-pane round-trips, and an
  old-reader simulation truncates to a valid 2-pane.
- **Goldens at 120×40:** the four T-shapes per surface with a pair pane focused. Single
  and 2-pane goldens stay byte-identical. Add no 3-pane goldens at 60 columns.
- **Live look pass** with real content (long replies, diffs, FINAL, time bands,
  streaming) at 80×24, 120×40 and your actual window size.
- Run `just check` through the guarded route. `check-full` only on explicit instruction.

---

## 10. Open decisions for you

1. **A3:** may the deck's same-key unsplit keep the focused panel (recommended), or must
   `\` `\` stay a peek that returns to panel 0?
2. **A2:** with the main pane focused, should erasing its divider keep main
   (recommended) or close it literally?
3. **A6:** ship the `ctrl+t` turn key in v1, or live with the lost 2-pane rotation
   first?
4. **Phase 0:** approve the kitty and tmux changes in chezmoi?

---

## 11. Recommended solution

Ship your `\` / `|` grammar, stated as one rule: **a split key erases its divider when
that divider spans the whole area, and your side grows. Otherwise it draws the divider
through the focused pane. With three panes it turns the layout.** That gives two
T-shaped families, four geometries, and never more than three panes.

- **Model:** one shared, pure `PaneGrid` (`sase/ace/tui/util/pane_grid.py`) with stable
  pane IDs, a structural main pane and pair, two ratios, and MRU focus. Pager and deck
  are thin adapters.
- **Rendering:** a flat Textual CSS grid. Panes are never reparented or remounted by a
  layout change; this is verified on 8.0.1.
- **Rules:**
  - The main pane is structural, not "larger".
  - The side you're on survives an erase.
  - A turn is a self-inverse transpose.
  - A swap moves whole sessions, and focus follows them.
  - Close promotes the sibling and is the exact inverse of split.
  - "Other pane" means most recently focused, previewed while armed.
  - Same-key unsplit keeps the focused pane on both surfaces.
- **Keys:** `ctrl+f` / `ctrl+b` focus; `ctrl+shift+f` / `ctrl+shift+b` (also `>` / `<`)
  swap; `ctrl+shift+d` (also `ctrl+x`) close; optional `ctrl+t` turn. Fix the kitty and
  tmux chain so the chords actually arrive, and move the debug leak chord.
- **Beauty:** exactly one full-strength frame; nothing you weren't touching moves;
  position glyphs only when naming a target; a target preview for `Ctrl+W`; the footer
  doesn't grow; toasts only on refusal.
- **Delivery:** fix sase-1er first. Land the model and keys on two panes, then the
  pager, then Agents behind one beta flag. Persist additively and test the transition
  table exhaustively.
