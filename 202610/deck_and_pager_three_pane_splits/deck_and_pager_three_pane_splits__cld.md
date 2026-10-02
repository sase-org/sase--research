# Three-pane splits for the Agents deck and the pager

Researcher: `cld` (research.3b swarm) · 2026-10-02 · sase master `47907502b6` · Textual
8.0.1

## TL;DR

- **Build it.** The request is a good idea, and the `\` / `|` grammar it describes is
  more coherent than it first looks. Its rule can be stated in one sentence: _a split key
  erases its own divider when that divider spans the whole area; otherwise it adds that
  divider inside the focused pane; and when three panes already exist, it turns the
  layout instead._ That is learnable, and it never needs a fifth layout key.
- **Implement it once.** Write one pure, Textual-free pane-grid model with exactly seven
  geometries. Both surfaces render it through a **flat CSS grid**: one container, panes
  as direct children, with `grid-size`, `fr` tracks, `row-span`/`column-span`, and
  `move_child` for order. I prototyped this in Textual 8.0.1. All four three-pane shapes
  and both two-pane shapes lay out correctly, and no pane is ever re-parented or
  re-mounted, so scroll, workers, trails and caches survive every transition.
- **Fix the existing close bug first.** On master, closing a pager split pane today
  (`q`, `Esc`, exhausted `Backspace`, or the same split key) detaches **both** panes and
  leaves an empty body. I reproduced this independently and it is tracked as **sase-1er**
  (I added a `+1`). Every new close/delete path goes through that same code.
- **The ctrl+shift keys don't reach sase today.** Your kitty uses the default
  `kitty_mod = ctrl+shift` and keeps kitty's own default maps for
  `ctrl+shift+f` / `ctrl+shift+b` (move window forward/backward). Your tmux 3.5a also
  runs with `extended-keys` off. Ship the requested chords, but add plain-ASCII aliases
  (`>` / `<` for swap, `ctrl+x` for close) and a small dotfiles change. Treat the
  deliverability check as phase 0.
- **Requirement adjustments, all called out in §7.** The most important ones:
  - "Larger pane" becomes the structural **main pane**.
  - A split key **never closes the pane you're focused on**.
  - "The other pane" means the **most recently focused** other pane.
  - Two-pane **rotate**, which the new grammar removes, is restored with a universal
    `ctrl+t` "turn" key (optional).

---

## 1. What exists today (verified in code)

### 1.1 Agents tab deck panels

| Concern | Where | Facts |
| --- | --- | --- |
| Pure model | `src/sase/ace/tui/widgets/decks/model.py`, `layout.py` | `DeckAreaState(panels, focused, layout ∈ {SINGLE, TOP_BOTTOM, LEFT_RIGHT}, ratio ∈ {30,50,70}, nodes_collapsed, zoom_snapshot)`. `toggle_split()` keeps **panel 0** on same-key unsplit; the other key rotates. `toggle_focus()` is `1 - focused`. |
| Widgets | `decks/area.py` | **Two pre-composed** `DeckPanel`s (`#agent-deck-panel-0/1`, panel 1 `hidden`). `apply_state()` syncs CSS classes only. `panel(i)` resolves by **DOM query order**. |
| CSS | `src/sase/ace/tui/styles.tcss:4020-4140` | Ratios are hard-coded per **panel ID** × layout × ratio (`#agent-deck-area.-top-bottom.-ratio-30 #agent-deck-panel-1 { height: 7fr }` …). Frames are `solid` in the deck accent, 35% alpha when unfocused, `heavy` when zoomed. |
| New-panel content | `layout.choose_new_panel()` | Walks the deck cycle for the first unshown deck with content; FINAL only on positive content. Otherwise duplicates the current deck on the next card. This already generalizes to a third panel. |
| "Other panel" | `decks/picker.py:other_panel_target()` | `1 - source_index`, labels `top/bottom/left/right`. |
| Zoom chrome | `decks/titles.py:_ZOOM_HALF_GLYPHS` | `◧ ◨ ⬒ ⬓` name the zoomed half (`◧ 1 of 2 · Z restore`). |
| Persistence | `models/agent_deck_persistence.py` | Schema v1, `MAX_PANELS = 2`, fail-open decode. A schema-version mismatch rejects the whole file. |
| Keys | `default_config.yml:744-748`, `ace/tui/bindings.py` | `\` / `\|` split, `ctrl+f` focus other, `}` / `{` grow/shrink, `ctrl+s` rail, `Z` zoom. |
| Availability | `ace/tui/_app_action_availability.py` | `_DECK_LAYOUT_ACTIONS` (Agents only), `_DECK_SPLIT_ONLY_ACTIONS` (split only). `scroll_prompt_down/up` (`ctrl+f` / `ctrl+b`) are **disabled on Agents** (line ~197). |
| Key-sharing registry | `ace/tui/keymaps/registry.py:~149` | Tab-disjoint pairs, e.g. `{"toggle_deck_focus", "scroll_prompt_down"}`. |

### 1.2 Pager split panes (epic sase-1eg, closed 2026-10-01)

| Concern | Where | Facts |
| --- | --- | --- |
| Pure model | `src/sase/pager/split.py` | `PagerSplitState(layout ∈ {SINGLE, BELOW, BESIDE}, focused, ratio)`. Same key keeps the **focused** pane. `split_fits()` uses `MIN_STACKED_PANE_HEIGHT = 7` and `MIN_BESIDE_PANE_WIDTH = 32`. The epic deliberately chose to "mirror, do not import" the deck model. |
| Host | `src/sase/pager/_screen_split.py` | Mounts clones dynamically (`split_seed()`), with an in-flight guard. `_apply_split_state()` sets inline `fr` sizes and `set_pane_role()`. |
| Layout | `src/sase/pager/_styles.py:19-33` | `#pager-panes` is a `Vertical`, switched to `layout: horizontal` for `-beside`. |
| Keys | `src/sase/pager/screen.py` (hard-coded) | `\`, `\|`, `ctrl+f`, `+` / `-`, `q`/`Esc` close focused pane, `ctrl+w <label>` opens a link in the other pane, `ctrl+w ctrl+w` focuses the other pane. `ctrl+b`, `ctrl+x`, `ctrl+t`, `<`, `>` are unbound. |
| Key routing | `_screen_host.py:on_key` | A hard-coded passthrough list (`backslash`, `vertical_line`, `ctrl+f`, `plus`, `minus`) wins over an armed label prefix. New pane keys must be added there. |
| Footer/help | `_chrome_footer.py`, `_trail_chrome_help.py:212-216` | The split footer adds `^F pane` and `q close pane`; the "Panes" help group. |

### 1.3 Live bug found while researching: sase-1er

`close_view()` and the same-layout branch of `_toggle_split()` both
`await self.query_one("#pager-panes").remove_children()`. That removes **every** pane,
the survivor included, and nothing re-mounts it. I reproduced it headless:

```
SasePager(long_document()), 80x20: body text visible before split → True
press | then |  → #pager-body widgets in DOM: 0, body text visible: False
120x40, \ then q (and \ then \): #pager-panes children 0, survivor in DOM False,
survivor.is_mounted still True
```

The existing tests only assert `len(screen.views)`, so they pass. The bug came in with
`dd32637d2c` (sase-1eg.3). Another swarm agent filed it as **sase-1er** a minute before I
got there, so I corroborated it with `+1` instead of opening a duplicate. **Every
three-pane close, delete and "close main" path depends on fixing this first.** The fix
is to remove only the discarded view (`await view.remove()`), and to add Pilot
assertions that the survivor is still a child of `#pager-panes` and still renders.

### 1.4 Deliberate differences between the two surfaces today

| | Agents deck | Pager |
| --- | --- | --- |
| New pane shows | A **different** deck (`choose_new_panel`) | A **clone** of the focused pane |
| Same split key keeps | Panel 0. This keeps the `\` `\` "peek" toggle non-destructive. | The focused pane (vim `ctrl-w o`) |
| Resize keys | `}` / `{` | `+` / `-` (`{`/`}` are history first/now) |
| Frame | `solid`, deck accent | `round`, section accent |
| Close this pane | none | `q` / `Esc` |

These differences are justified by content, and I keep them. Section 5 generalizes each
surface's own rule rather than forcing one rule onto both.

---

## 2. Reading the request precisely

**Terminology.** The request uses vim's naming, which the `Deck Panel` glossary entry
also uses: a **horizontal split** is `\` (one pane above the other) and a **vertical
split** is `|` (side by side). tmux uses the opposite words (`split-window -h` puts panes
side by side). Because of that, I name geometries by shape below, and I recommend the
code and docs never say "horizontal/vertical" again.

**The seven geometries.** "Split the currently focused pane" means the T-shape can open
on either side, so the request actually defines seven geometries:

```
 single     stacked (R2)   side-by-side (C2)
┌──────┐    ┌──────┐       ┌───┬───┐
│  A   │    │  A   │       │ A │ B │
│      │    ├──────┤       │   │   │
└──────┘    │  B   │       └───┴───┘
            └──────┘

 R3 · main-top   R3 · main-bottom   C3 · main-left   C3 · main-right
┌──────┐        ┌───┬───┐          ┌───┬───┐        ┌───┬───┐
│  A   │        │ B │ C │          │   │ B │        │ B │   │
├───┬──┤        ├───┴───┤          │ A ├───┤        ├───┤ A │
│ B │C │        │   A   │          │   │ C │        │ C │   │
└───┴──┘        └───────┘          └───┴───┘        └───┴───┘
```

The **main pane** (`A`) is the one that spans the full width (R3) or full height (C3).
The other two form the **pair**.

**The request as a state machine** (literal reading):

| From | `\` | `\|` |
| --- | --- | --- |
| single | → R2 (new pane below, focused) | → C2 (new pane beside, focused) |
| R2 | → single | → R3: split the **focused** pane side by side |
| C2 | → C3: split the **focused** pane stacked | → single |
| R3 | → C2: close the "larger" pane | → C3: "switch to the other 3-pane view" |
| C3 | → R3: "switch to the other 3-pane view" | → R2: close the "larger" pane |

`ctrl+b` cycles focus backward. `ctrl+shift+f` / `ctrl+shift+b` swap with the next or
previous pane. `ctrl+shift+d` deletes the focused pane and is only active with two or
more panes.

---

## 3. Critique

### 3.1 Is this a good idea?

**Yes, on both surfaces, with a capped and closed design.**

- **Agents tab:** this is where three panes pay off most. "Main + Files + Tools" for one
  agent is the triage loop that `choose_new_panel` already anticipates: it picks the next
  unshown deck, and that walk works unchanged for a third panel.
- **Pager:** the gain is smaller but real: a document plus two references, or a past
  version, the current version, and a source file.
- **Capping at three panes with a fixed geometry set is a feature, not a limitation.**
  The whole state space is 7 geometries × ≤3 focus positions. Every (state, key) pair,
  about 170 transitions, can be tested exhaustively instead of sampled. A general
  vim/tmux split tree cannot offer that. I recommend keeping the cap.

### 3.2 The grammar is good, but it needs to be stated as one rule

The user's table is consistent with this sentence:

> `\` and `|` draw dividers (`\` a horizontal one, `|` a vertical one). Pressing a key
> whose divider already spans the whole area **erases** it. Otherwise the key **adds**
> that divider inside the focused pane. With three panes, adding is impossible, so the
> key **turns** the layout.

Every row of §2 follows from it. Docs and the `?` help should lead with this sentence.

### 3.3 Problems and gaps I found

1. **"The larger pane" is ambiguous.** At ratio 30, main-top gives `A` 30% of the area
   while `B` and `C` get 35% each, so the main pane is *smaller*. The rule has to be
   structural: the pane that spans the full width or height (the **main pane**).
2. **Two-pane rotation disappears.** Today the other split key rotates R2 ↔ C2. Under the
   new grammar it creates a third pane instead. In the pager that is a real loss: rotating
   kept both panes' documents and trails, while the new detour (unsplit, then re-split)
   re-clones the focused pane and **discards the other pane's trail**. On Agents the
   re-split re-picks a deck. Without a fix, rotating a split takes three keystrokes
   (split into 3, turn, delete).
3. **"Which T?" and "what does the turn do?" are unspecified.** "Split the focused pane"
   gives four three-pane geometries, not two. The natural turn is a **transpose**
   (reflect across the main diagonal): main-top ↔ main-left and main-bottom ↔ main-right.
   The pair keeps its order, the top-left pane never moves, and pressing the key again
   returns exactly to the previous geometry. This is the three-pane analog of today's
   two-pane rotate, which is also its own inverse. A quarter-turn rotation would scramble
   reading order and is not self-inverse.
4. **A split key can close the pane you're reading.** Under the literal rule, if you
   focus the main pane in R3 and press `\`, the focused pane closes and focus jumps. That
   breaks the pager's existing principle ("the same split key keeps the focused pane").
   It is also strictly less expressive. "Keep only the main pane" would take two deletes,
   while "drop the main pane" already has `ctrl+shift+d`.
5. **"The other pane" becomes ambiguous with three panes.** This affects:
   - pager `ctrl+w <label>` (open a link in the other pane);
   - `ctrl+w ctrl+w`;
   - the Agents deck picker's capital letters (show a deck in the other panel);
   - the picker hint "show in the bottom panel".

   Today all of these hard-code `1 - index`.
6. **The ctrl+shift chords are not deliverable on your machine as configured.** This is
   the biggest reliability risk. Evidence:
   - Your kitty 0.41.1 keeps the default `kitty_mod ctrl+shift`. The user's `kitty.conf`
     only remaps `cmd+f` and `ctrl+shift+y`. Kitty's shipped defaults
     (`/usr/lib/kitty/kitty/options/definition.py`) map
     `kitty_mod+f → move_window_forward` and `kitty_mod+b → move_window_backward`.
     That is literally "swap with next/previous pane" at the terminal level, so the
     keystrokes never leave kitty. Kitty also maps `kitty_mod+o → pass_selection_to_program`,
     so ACE's existing `ctrl+shift+o` (jump forward) is probably dead for you today too.
     Pressing it is a quick test.
   - Your `tmux.conf` (tmux 3.5a) never sets `extended-keys`, so it is **off**. Even a
     `ctrl+shift+d` that kitty lets through reaches Textual as plain `ctrl+d`. That means
     half-page scroll in the pager, and `scroll_detail_down` on Agents.
   - Textual 8.0.1 asks for the kitty protocol (`\x1b[>1u`) and parses CSI-u
     (`_xterm_parser._re_extended_key`). It does **not** parse tmux's default xterm
     format `CSI 27;mod;key ~`. So tmux needs `extended-keys-format csi-u`, not just
     `extended-keys on`.
   - Failure is quiet rather than destructive: swaps fall back to focus cycling, and
     delete falls back to scrolling. That kind of silent failure is exactly what makes a
     feature feel unreliable.
7. **`ctrl+shift+d` is already bound** to the env-gated `debug_leak_snapshot`
   (`bindings.py:306`, when `SASE_ACE_DEBUG_LEAKS=1`).
8. **`ctrl+b` is free on Agents but needs registry work.** `scroll_prompt_up` owns it
   app-wide and is disabled only on Agents. It needs a tab-disjoint pair, just as
   `ctrl+f` has. Also note that `ctrl+b` is tmux's *default* prefix. You moved yours to
   `C-a`, but other sase users won't have.
9. **Unspecified rules:**
   - where focus goes after a close;
   - what `+`/`-` (pager) or `}`/`{` (Agents) resize when a pane sits inside two splits;
   - whether a three-pane layout must fit a minimum size.

   The Agents deck has no fit guard at all today, and the node column eats width: on a
   120-column terminal the pair panes would be about 30 columns.
10. **Agents panels are pre-composed, with ID-keyed CSS and DOM-order lookups.** A third
    panel needs a widget. Swapping must not re-render decks. `panel(i)` by query order
    breaks the moment the DOM order stops matching the slot order, which it must for one
    geometry (see §6.2).
11. **Persistence caps panels at 2 (`MAX_PANELS`).** Bumping the schema to 2 would make
    any older sase on the same `~/.sase` reject the whole file. That matters, because
    multiple sase versions do coexist on athena.
12. **Phased landing would make the same keys mean different things.** If the pager gets
    the new grammar before the Agents tab (or the reverse), `|` in a stacked split means
    "rotate" in one surface and "third pane" in the other until the epic lands.

---

## 4. Alternatives considered

| Option | Verdict |
| --- | --- |
| **A. Stay at two panes; add zoom/tabs.** | Rejected. Agents already has zoom (`Z`), and it doesn't give you three decks at once, which is the actual value. |
| **B. General vim/tmux split tree (N panes, arbitrary nesting).** | Rejected for now. The state space is unbounded, it needs directional focus (`h/j/k/l`), and "beautiful" falls apart below about 30 columns per pane. The recommended model is tree-*shaped*, so a 2×2 later is a bounded model change, not a rewrite. |
| **C. tmux-style presets cycled by one key** (`select-layout`, `next-layout`). | Rejected as the primary grammar. "Which pane did I just split?" is lost, and cycling through presets moves panes you didn't touch. tmux's `main-horizontal` / `main-vertical` are the same geometries as R3 / C3, which supports the layout set, and I borrow the term **main pane** from tmux. |
| **D. Dedicated key per layout.** | Rejected. That means five-plus keys to remember, and the two-key divider grammar is already complete. |
| **E. The requested grammar plus the refinements in §5.** | **Recommended.** |
| Implementation: nested `Vertical`/`Horizontal` containers | Rejected. R2 → R3 would have to move pane `B` into a new pair container. Textual cannot re-parent without `remove()` + `mount()`, which unmounts the pane. For `PagerView` that runs `cancel_pump_free_tasks`; for `DeckPanel` it re-composes every deck. |
| Implementation: **flat CSS grid** | **Recommended.** Prototyped in §6.2. |
| Model: two parallel models (as today) | Rejected. Duplicating the algebra was tolerable for two panes and is a reliability risk for seven geometries. |
| Model: move it into Rust `sase_core` | Not needed. This is presentation-only Textual layout; a web or editor frontend would not need to match it (the rust-core-boundary litmus test). |

---

## 5. Recommended design (the UX contract)

### 5.1 Vocabulary

Use these terms in code, docs and help:

- **stacked** (`\`, rows) and **side by side** (`|`, columns);
- **main pane** and **pair**;
- **reading order** (top-to-bottom, then left-to-right);
- **turn** (transpose).

The pager keeps the word "pane" and the Agents tab keeps "panel".

### 5.2 Keys

| Key (both surfaces) | Action | Active |
| --- | --- | --- |
| `\` / `\|` | Split key (table in §5.3) | always |
| `ctrl+f` / `ctrl+b` | Focus next / previous pane in reading order (wraps) | 2+ panes |
| `ctrl+shift+f` / `ctrl+shift+b`, **aliases `>` / `<`** | Swap the focused pane with the next / previous pane (wraps); focus moves with it | 2+ panes |
| `ctrl+shift+d`, **alias `ctrl+x`** | Close the focused pane | 2+ panes |
| `ctrl+t` (optional, §7 A6) | Turn: transpose any split (R2 ↔ C2, R3 ↔ C3) | 2+ panes |
| Pager `+` / `-`, Agents `}` / `{` | Grow / shrink the focused pane against its nearest sibling | 2+ panes |
| Pager `q` / `Esc` | Close the focused pane (pager when single); unchanged | always |

The aliases are plain ASCII, so they work under any terminal or tmux configuration. All
are verified free:

- **`<` / `>`**
  - Pager: unbound.
  - ACE: bound only by the Artifacts-tab `start_ancestor_mode` / `start_child_mode`, so
    they are tab-disjoint on Agents.
  - Mnemonic: "move this pane left/right in reading order"; tmux's swap-pane keys are the
    analog.
- **`ctrl+x`**
  - Pager: unbound.
  - ACE: no app-level binding; it is used only inside prompt and modal widgets.
  - Mnemonic: tmux's `prefix x` is kill-pane.

### 5.3 Split-key transitions

| From | `\` (stacked divider) | `\|` (side-by-side divider) |
| --- | --- | --- |
| single | **R2**: new pane below, focused, 50/50 | **C2**: new pane right, focused, 50/50 |
| R2 | **single**: pager keeps the focused pane; Agents keeps panel 0 (both unchanged) | **R3**: the focused pane splits side by side; the new pane goes right of it and takes focus; the other pane does not move or resize |
| C2 | **C3**: the focused pane splits stacked; the new pane goes below it and takes focus | **single** (as for R2) |
| R3 | Focus in pair → **C2** (main closes, pair keeps its ratio). Focus on main → **single** (main survives). | **Turn → C3** |
| C3 | **Turn → R3** | Focus in pair → **R2** (main closes). Focus on main → **single** (main survives). |

Close the focused pane (`ctrl+shift+d`, or `q` in the pager):

- **Closing a pair member** → its sibling takes the space, and the layout becomes R2/C2
  with the outer ratio kept.
- **Closing the main pane** → the pair fills the area, and the layout becomes C2/R2 with
  the pair's ratio.
- **Closing in a two-pane split** → single.

This makes **close the exact inverse of split**: the ratio, the positions and the focus
all return to the state before the split. That is a testable invariant.

### 5.4 Rules

- **New-pane content:**
  - Pager: a clone of the focused pane (`split_seed()`, unchanged).
  - Agents: `choose_new_panel()` from the focused panel (unchanged). With Main and Files
    shown, a third panel opens on Tools, or on FINAL when FINAL has content.
- **Focus after a close:** the most recently focused surviving pane, falling back to the
  first pane in reading order. The surface keeps a tiny MRU list of pane ids.
- **"The other pane"** (pager `ctrl+w <label>`, the Agents picker's capital letters):
  - It means the **most recently focused other pane** (vim's `ctrl-w p`), falling back to
    the next pane in reading order. With two panes this is exactly today's behavior.
  - It still never creates a third pane: only split keys do.
  - `ctrl+w ctrl+w` stays an alias of `ctrl+f` (vim's `ctrl-w w` cycles).
- **Swap:** trade places with the neighbor in reading order, wrapping at the ends. The
  geometry never changes; only contents move, and focus follows the moved pane (tmux
  `swap-pane -D/-U`). From any pair pane, one press puts it into the main slot.
- **Resize:** adjust the split that directly separates the focused pane from its nearest
  sibling. For a pair member that is the inner split; for the main pane it is the outer
  split. Steps stay at 30/50/70. Every split stays reachable with two keys and no new
  bindings.
- **Fit:**
  - Every new geometry (third pane, turn) must give each pane at least the surface
    minimum. Pager: 7 rows × 32 columns. Agents: new constants, about 8 × 40, to be tuned
    on real screens.
  - Otherwise, refuse with a toast that names what would fit, e.g. "Not enough room for
    a third panel — try `ctrl+s` for the node rail" or "…try `\` instead".
  - Keep the Agents tab's existing two-pane behavior unguarded, so nothing regresses.
  - As today, shrinking the terminal never closes a pane.
- **Zoom (Agents):** `Z` works unchanged on any geometry, because the snapshot is the
  whole state. Split keys while zoomed end the zoom, as today.

### 5.5 Beauty spec

1. **Spatial stability is the aesthetic.**
   - A split only subdivides the focused pane.
   - A turn pins the top-left pane.
   - A close puts back exactly what was there.
   - Nothing you weren't touching moves.
2. **Exactly one full-strength frame.** Keep each surface's frame language: the pager's
   `round` section-accent frames and the deck's `solid` deck-accent frames, at 35% when
   unfocused. With three panes, two dim frames and one bright frame make focus obvious
   without any new chrome.
3. **A position-glyph language** for talking about panes. Extend the deck's existing
   `◧ ◨ ⬒ ⬓` (all one cell wide, East-Asian-width N) with the quadrant squares
   `◰ ◱ ◲ ◳`:

   | Geometry | Glyphs (reading order) |
   | --- | --- |
   | main-top | `⬒ ◱ ◲` |
   | main-bottom | `◰ ◳ ⬓` |
   | main-left | `◧ ◳ ◲` |
   | main-right | `◰ ◱ ◨` |

   Use the glyphs only where a pane is being *named*. Keep steady-state titles quiet.
   - Agents zoom chip: `◲ 3 of 3 · Z restore`.
   - Picker other-panel hint: `show in the ◲ bottom-right panel`.
   - Pager armed-`ctrl+w` footer: `^W… ◲ pane`.
4. **Target preview while `ctrl+w` is armed** (pager, three panes): the target pane's
   frame lifts to about 70% strength until the label lands or the arm is cancelled. You
   see where the link will open before it opens.
5. **The footer doesn't grow.**
   - Pager: keeps `^F pane`.
   - Agents: shows `^F/^B panel` when three panels are visible, plus the existing
     `{/}` resize.
   - Swap, close and turn live in `?` help and the command palette. That follows the
     footer rule that only verbs which sometimes do nothing earn a slot.
6. **Help leads with the one-sentence grammar** (§3.2), then the rows.
   `docs/pager.md` and `docs/ace.md` get the seven-geometry diagram from §2.
7. **Toasts appear only on refusal**, never on success. The layout change is its own
   feedback.

---

## 6. Architecture

### 6.1 One shared pure model

Put it in `src/sase/ace/tui/util/pane_grid.py`, which the pager may import because it
already depends on `sase.ace.tui.util`. It has no Textual imports and no deck or pager
concepts.

```python
class Axis(StrEnum):
    ROWS = "rows"   # stacked  — `\`
    COLS = "cols"   # side by side — `|`

@dataclass(frozen=True, slots=True)
class Pair:
    region: int        # outer region holding the pair: 0 = top/left, 1 = bottom/right
    ratio: int = 50    # first pair member's share (RATIO_STEPS)

@dataclass(frozen=True, slots=True)
class PaneGrid:
    panes: tuple[int, ...] = (0,)   # surface-owned pane ids, reading order, len 1..3
    focused: int = 0                # index into panes
    axis: Axis | None = None        # outer split; None iff single
    ratio: int = 50                 # outer first region's share
    pair: Pair | None = None        # set iff 3 panes
    recent: tuple[int, ...] = ()    # MRU pane ids (focus history)

# Transitions (all total and pure; invalid input returns the state unchanged)
def press_split(g, axis, new_id, *, unsplit_keeps: Literal["focused", "first"]) -> PaneGrid
def close_focused(g) -> PaneGrid
def cycle_focus(g, step: int) -> PaneGrid
def swap_focused(g, step: int) -> PaneGrid
def turn(g) -> PaneGrid
def step_ratio(g, direction: int) -> PaneGrid
def other_target(g) -> int | None               # MRU other pane id
def regions(g, width, height) -> tuple[Rect, ...]   # reading order
def fits(g, width, height, *, min_w, min_h) -> bool
def position_glyph(g, index) -> str
def grid_spec(g) -> GridSpec   # cols, rows, col_fr, row_fr, spans, dom_order
```

`unsplit_keeps` is the only per-surface policy: `"focused"` for the pager and `"first"`
for Agents in R2/C2. Every R3/C3 rule is shared. `PagerSplitState` and the
`layout`/`ratio` fields of `DeckAreaState` become thin views over `PaneGrid`. Keep
`DeckLayout` as a derived property, so the roughly 36 `DeckLayout` comparisons across
13 ACE modules keep working while they migrate.

### 6.2 Flat-grid rendering (prototyped)

A throwaway probe script builds one `layout: grid` container with three direct
`Static` children. Its core is below. It sets `grid_size_*`, `grid_rows`/`grid_columns` as `fr`,
`row_span`/`column_span`, and reorders with `move_child`. Results on a 100×40 area:

| Geometry | Regions `(x, y, w, h)` | DOM order | Same widget objects |
| --- | --- | --- | --- |
| main-top (outer 30) | A `(0,0,100,12)`, B `(0,12,50,28)`, C `(50,12,50,28)` | A B C | ✓ |
| main-bottom (outer 70) | B `(0,0,50,28)`, C `(50,0,50,28)`, A `(0,28,100,12)` | B C A | ✓ |
| main-left (outer 30) | A `(0,0,30,40)`, B `(30,0,70,20)`, C `(30,20,70,20)` | A B C | ✓ |
| main-right (outer 70) | B `(0,0,70,20)`, A `(70,0,30,40)`, C `(0,20,70,20)` | **B A C** | ✓ |
| stacked, C `display:none` | A `(0,0,100,20)`, B `(0,20,100,20)` | A B (C skipped) | ✓ |

```python
def apply(grid, cols, rows, col_fr, row_fr, spans, dom_order):
    s = grid.styles
    s.grid_size_columns, s.grid_size_rows = cols, rows
    s.grid_columns, s.grid_rows = col_fr, row_fr          # e.g. "30fr 70fr"
    for w in grid.children:
        w.styles.column_span, w.styles.row_span = spans.get(w.id, (1, 1))
    for i, wid in enumerate(dom_order):                   # pure reorder, no remount
        w = grid.query_one(f"#{wid}")
        if grid.children.index(w) != i:
            grid.move_child(w, before=i)
```

What this establishes:

- Every transition is a style change, a `move_child` call (a pure reorder:
  `_nodes._remove/_insert` plus `refresh(layout=True)`), a mount of a new pane, or a
  removal of the discarded pane. **No pane is ever re-parented.**
- Hidden children drop out of grid placement (`_arrange` filters on `display`), so the
  Agents tab can keep a pre-composed hidden third panel inside the same grid.
- **DOM order is not always reading order.** In main-right, row-major auto-placement
  needs `[B, A, C]`. `grid_spec()` therefore returns `dom_order`, and surfaces must hold
  **explicit slot → widget references**. Do not use `query(DeckPanel)[i]` (`area.py`);
  the pager plan's "never re-query panes by ID" rule already points this way.

### 6.3 Pager adoption

- `#pager-panes` becomes a grid container. `_apply_split_state()` becomes "compute
  `grid_spec`, apply styles, reorder, `set_pane_role` per pane".
- Split, close, swap and turn all go through `PaneGrid`. Keep the async in-flight guard.
- Close removes only the discarded view (this is the sase-1er fix).
- Add `ctrl+b`, `ctrl+shift+f/b`, `<`, `>`, `ctrl+shift+d`, `ctrl+x`, and optionally
  `ctrl+t` to `BINDINGS` **and** to the `on_key` passthrough list.
- `show_in_other_view()` and `focus_other_view()` target `other_target()`. The armed
  `^W…` footer names the target with its glyph.
- Help gets updated "Panes" rows. Add PNG goldens for main-top/bottom/left/right at
  120×40, focused and unfocused.

### 6.4 Agents adoption

`DeckArea`:

- holds a `list[DeckPanel]` of slot references and a `PaneGrid`;
- keeps a third `DeckPanel`, either composed hidden at startup or mounted lazily on the
  first three-pane transition and then kept. Decide by measurement under
  `SASE_TUI_TRACE=1`; startup must not regress (tui_perf rule 9);
- replaces all ID-keyed ratio CSS (`styles.tcss:4028-4082`) with inline grid styles from
  `grid_spec`;
- swaps by permuting `state.panels` plus `move_child`, so decks are not re-shown and
  scroll is preserved. `panel_index` becomes a lookup, not a constructor constant.

The remaining two-pane assumptions to generalize:

- `picker.other_panel_target`, `panel_position_label`;
- `_ZOOM_HALF_GLYPHS` → `position_glyph`;
- `area.apply_state`/`visible_panels`/`on_deck_panel_focus_requested`;
- `_agent_detail_deck_layout._open_deck_split` (`area.panel(1)`);
- `_agent_detail_deck_show.deck_picker_state`.

Keymap plumbing:

- `default_config.yml` keymaps: keep `toggle_deck_focus`, and add
  `toggle_deck_focus_reverse: ctrl+b`,
  `swap_deck_panel_next: "ctrl+shift+f,greater_than_sign"`,
  `swap_deck_panel_prev: "ctrl+shift+b,less_than_sign"`,
  `close_deck_panel: "ctrl+shift+d,ctrl+x"`, and optionally `turn_deck_layout: ctrl+t`.
- `keymaps/app_keymaps.py` and `keymaps/metadata.py`: add the new fields.
- Registry tab-disjoint pairs: `{toggle_deck_focus_reverse, scroll_prompt_up}`,
  `{swap_deck_panel_prev, start_ancestor_mode}`,
  `{swap_deck_panel_next, start_child_mode}`, `{turn_deck_layout,
  beads_toggle_note_audience}`.
- `_DECK_LAYOUT_ACTIONS` and `_DECK_SPLIT_ONLY_ACTIONS`: add the new actions.
- Command palette (`commands/_app_metadata_nav.py`, `_availability_agents.py`), the help
  modal (`agents_bindings.py`), the footer (`_keybinding_bindings_agents.py:~498`), and
  `_deck_search_host.py`'s passthrough set.
- Move the env-gated `debug_leak_snapshot` off `ctrl+shift+d`.
- Update the `Deck Panel` glossary strand ("one deck panel, or two…") through
  `/sase_memory_write` when this lands.

### 6.5 Persistence: additive, so it degrades gracefully

Keep `schema_version: 1`. Raise `MAX_PANELS` to 3 and add an optional
`"pair": {"region": 0|1, "ratio": 50}`, with `panels` in reading order. An older reader
ignores `pair`, truncates to two panels and shows a valid R2/C2. A newer reader seeing
no `pair` loads exactly as today. A schema bump would instead make every older sase on
the machine discard the whole file.

### 6.6 Verification strategy

- **Exhaustive model table test:** every geometry × focus × key, about 170 transitions,
  pinned against a golden transition table. The state space is small enough to
  enumerate.
- **Hypothesis invariants** (`hypothesis` is already a dependency):
  - 1–3 unique panes, with focus in range;
  - `turn∘turn = id`;
  - `swap(+1)∘swap(−1) = id`;
  - close∘split = id, ratios included;
  - focus cycling visits every pane;
  - `regions()` tile the area exactly, with no overlap and no gap;
  - `grid_spec` placement equals `regions`.
- **Pilot:**
  - after every close path, the survivor is a child of the container and renders (the
    sase-1er regression);
  - swaps keep widget identity and scroll;
  - `ctrl+w` targets the MRU pane.
- **Goldens:** four three-pane PNGs per surface; existing single and two-pane goldens
  stay byte-identical.
- **Performance:** with three Agents panels visible, `bench_tui_jk.py` j/k p95 stays
  under 16 ms. The detail refresh is debounced, but three panels triple the debounced
  work.

---

## 7. Requirement adjustments (explicit)

| # | Your requirement | Adjustment | Why |
| --- | --- | --- | --- |
| A1 | "closes the **larger** pane" | Close the **main pane**: the one spanning the full width/height | Area-based "larger" is wrong at ratio 30 (§3.3-1). |
| A2 | `\` in R3 / `\|` in C3 always closes the main pane | Do this **when focus is in the pair**. When the **main pane is focused**, keep it and go to single. | A split key never closes the pane you're reading. This generalizes the pager's "same key keeps the focused pane", and makes "keep only main" one key. The literal rule is a fine fallback if you prefer layout determinism: it only changes the main-focused case. |
| A3 | "switch to the other 3-pane view" | Define it as a **transpose**: main-top ↔ main-left, main-bottom ↔ main-right, pair order and focus preserved | It is self-inverse and pins the top-left pane (§3.3-3). |
| A4 | "split the currently focused pane" (unspecified side) | The new pane goes right of / below the focused pane and takes focus; the unfocused pane neither moves nor resizes | It matches today's two-pane rule and vim's `splitright`/`splitbelow`. |
| A5 | `ctrl+shift+f/b`, `ctrl+shift+d` | Keep them, and **add `>`/`<` and `ctrl+x` aliases**, plus a dotfiles change (§8 phase 0). Move the debug binding off `ctrl+shift+d`. | They don't reach sase in your kitty → tmux stack today (§3.3-6). |
| A6 | (implicit) the other key no longer rotates a two-pane split | Add **`ctrl+t` turn** for every split (optional, deferrable) | Restores rotation without discarding the other pane's state (§3.3-2). |
| A7 | (unspecified) "the other pane" with three panes | **Most recently focused** other pane; its glyph is shown in hints, and the pager previews the target frame while `ctrl+w` is armed | Keeps `ctrl+w <label>` and picker capital letters meaningful. |
| A8 | (unspecified) focus after close, resize, fit | MRU focus; resize against the nearest sibling; fit guard only on new three-pane transitions | §5.4. |
| A9 | Agents `\`/`\|` in two-pane | **Unchanged**: keep panel 0 | Preserves the non-destructive `\` `\` peek toggle (the new panel shows a different deck). |

---

## 8. Rollout (epic shape)

0. **Key-deliverability spike** (xsmall/small; mostly dotfiles, in the chezmoi repo and
   with your approval). Example recipe, to be verified live with `cat -v` inside tmux
   inside kitty, both locally and over SSH from the Mac:
   - kitty: `map ctrl+shift+f no_op`, `map ctrl+shift+b no_op`. `no_op` passes the key
     through, the same pattern as your existing `map cmd+f no_op`. Add
     `send_text all \x1b[…;6u` maps if kitty doesn't encode them for tmux on its own.
   - tmux: `set -s extended-keys always`, `set -s extended-keys-format csi-u`,
     `set -as terminal-features 'xterm-kitty:extkeys'`. `always` is likely needed because
     Textual asks for the kitty protocol, not modifyOtherKeys.
   - Nested tmux over SSH needs the same settings at each layer.
   - If `ctrl+shift+o` (ACE forward jump) starts working, the chain works.
1. **sase-1er:** fix the survivor detach (small, already filed).
2. **`pane_grid` model:** pure model, `grid_spec`, exhaustive and Hypothesis tests. Add a
   **beta flag** (`sase flag new …`) as epic scaffolding so neither surface flips its
   `\`/`|` semantics alone.
3. **Pager** adopts the grid, the three-pane grammar, the new keys, MRU `ctrl+w`, help,
   docs and goldens. The pager comes first because panes mount dynamically there and
   nothing is persisted, so it proves the model and adapter at the lowest risk.
4. **Agents** adopts the grid: third panel, slot references, keymaps, availability,
   registry, picker, zoom glyphs, footer/help/palette, persistence, perf bench and
   goldens.
5. **Land:** remove the beta flag, update `docs/ace.md`, `docs/pager.md` and the
   `Deck Panel` glossary strand.

## 9. Risks and open questions

- **Terminal chain:** whether the kitty-on-Mac → SSH → tmux hop delivers CSI-u for
  ctrl+shift letters is the one thing I could not test from a non-interactive session.
  The aliases make the feature work regardless.
- **Agents third-panel cost:** pre-composing it hidden versus lazy mounting is a
  measurement, not an opinion. Measure startup and j/k with three panels visible.
- **Narrow terminals:** at 120 columns with the expanded node column, Agents pair panels
  are about 30 columns. The fit-refusal toast should steer users to `ctrl+s` (rail) or
  `Z`.
- **A2 is a judgment call.** It is worth confirming with the user that "main focused +
  same key → single" matches their intent.

## 10. Recommended solution

Adopt the requested `\` / `|` grammar and document it with the one-sentence divider rule.

**Model and rendering**

- Implement one shared, pure, closed `PaneGrid` model: seven geometries, reading-order
  pane ids, a structural main pane and pair, MRU focus, and a `grid_spec` projection.
- Render both surfaces through a single **flat Textual CSS grid**, so panes are never
  re-parented, re-mounted or re-rendered by a layout change.

**Rule refinements** (§7)

- Make the "larger" pane the structural main pane.
- Never let a split key close the focused pane.
- Make the three-pane turn a self-inverse transpose.
- Make "the other pane" the most recently focused one.
- Make close the exact inverse of split.
- Keep each surface's existing two-pane unsplit rule.

**Keys**

- Ship `ctrl+b` and the requested `ctrl+shift+f/b/d`.
- Add reliable `>` / `<` / `ctrl+x` aliases. Optionally add `ctrl+t` to bring back
  two-pane rotation.
- Fix kitty/tmux so the chords actually arrive.

**Chrome**

- Keep the existing frame languages, so exactly one frame is at full strength.
- Name positions with the `◧◨⬒⬓◰◱◲◳` glyph family only where a pane is being named.
- Preview the `ctrl+w` target.
- Keep footers the same size.

**Delivery**

- Fix sase-1er first.
- Land the pager, then Agents, behind a beta scaffolding flag.
- Persist additively, so older sase versions still read the file.
- Test the model exhaustively, not by sampling.
