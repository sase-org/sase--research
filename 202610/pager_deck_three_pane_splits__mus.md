# Pager + Agents-deck 3-pane splits: research, critique, and recommended design

Researcher: mus (independent swarm report; no peer reports consulted).
Scope: the proposal to add two 3-pane views plus `ctrl+b` / `ctrl+shift+b,f` /
`ctrl+shift+d` keymaps to the Agents-tab deck panel and the sase pager split view.
Sources: pager split implementation (`src/sase/pager/split.py`,
`_screen_split.py`, `screen.py`, `_screen_host.py`), deck layout implementation
(`ace/tui/widgets/decks/model.py`, `layout.py`, `area.py`,
`_agent_detail_deck_layout.py`), app bindings (`ace/tui/bindings.py`), deck/pager
tests, and `docs/pager.md` ("Split panes"). Bead sase-1eg (pager split epic,
closed) read for context.

## 1. Verdict up front

The goal is sound but the proposed keymap state machine is not shippable as
written: it overloads `\` / `|` with five jobs each (open, nest-to-3, rotate-3,
close-other, unsplit-to-1), defines close-target as "the larger pane" (which the
user cannot reliably identify), and proposes three keymaps that collide with
existing bindings or with terminal delivery limits. I recommend building the
3-pane feature with **fixed 3-pane templates** (not a nesting tree), an explicit
documented state diagram, close-focused semantics everywhere, and additive
keymaps with non-shift fallbacks. Details and the full build order are in
section 9. Every deviation I propose from the request is listed in section 10.

## 2. How the two implementations work today

Both surfaces share a shape but are independent implementations (pager's
`split.py` header says it mirrors `decks/layout.py` without importing it).

**Pager** (`src/sase/pager/split.py`, `_screen_split.py`):

- Pure model `PagerSplitState(layout, focused, ratio)` with
  `layout ∈ {SINGLE, BELOW, BESIDE}`, `focused ∈ {0,1}`, ratio steps
  `(30, 50, 70)`. Pure transitions: `toggle_split`, `close_focused_pane`,
  `toggle_focus`, `step_ratio`, plus `split_fits` guards
  (`MIN_STACKED_PANE_HEIGHT = 7`, `MIN_BESIDE_PANE_WIDTH = 32`).
- Semantics: from single, `\`/`|` opens the target at 50/50 with the *new* pane
  focused. Same key again unsplits keeping only the *focused* pane (vim `ctrl-w o`
  style). The other key *rotates* keeping focus and ratio. `q`/`Esc`/exhausted
  backspace closes the focused pane. `ctrl+f` focuses the other pane, `+`/`-`
  steps the ratio, click focuses, `ctrl+w <label>` opens a link in the other
  pane (opening a split when single). Only the focused pane paints link-label
  badges. One shared footer; split mode shows `^F pane` / `q close pane`.
- The screen mixin hard-codes "two": `self._views` has length 1 or 2,
  `other_index = 1 - index`, `len(views) == 2` branches in `_apply_split_state`,
  and `show_in_other_view` iterates "the pane that is not source".

**Agents deck** (`decks/model.py`, `decks/layout.py`, `area.py`,
`_agent_detail_deck_layout.py`):

- `DeckAreaState(panels, focused, layout, ratio, nodes_collapsed, zoom_snapshot)`
  with `layout ∈ {SINGLE, TOP_BOTTOM, LEFT_RIGHT}`. Same open/rotate/unsplit
  shape, one deliberate difference: same-key unsplit keeps **panel 0**, not the
  focused panel (pager keeps the focused pane — an inconsistency to resolve when
  touching this code).
- Extra deck-only concerns: `choose_new_panel` (new panel shows the next
  unseen deck with content; duplicate-Main takes the next card; empty FINAL is
  never auto-picked), zoom snapshots, node-rail/collapse, persisted deck state,
  and a duplicate-FILES `next_file()` nudge. `DeckArea` composes exactly two
  `DeckPanel` widgets (`agent-deck-panel-0/1`); `visible_panels()` returns at
  most two.
- Bindings (`ace/tui/bindings.py`): `\` → `toggle_deck_split_below`,
  `|` → `toggle_deck_split_right`, `ctrl+f` → `toggle_deck_focus`,
  `{`/`}` → shrink/grow (pager uses `-`/`+` for the same job).

## 3. Critique of the proposal, point by point

1. **The `\`/`|` state machine is ambiguous and undiscoverable.** Each key is
   asked to mean: open-2-pane, nest-focused-into-3, rotate-between-3-pane-forms,
   close-a-pane-to-2, *and* unsplit-to-1. That is five transitions on one key,
   distinguished only by invisible layout state. Users will not be able to
   predict what `|` does, and the help/footer cannot explain it in one line
   (today's one-liners — "same key keeps only the focused pane, other key
   rotates" — already saturate the explainability budget). The two 3-pane
   bullets are also near-mirror text that is hard to tell apart; whichever
   design ships needs a named state diagram, not prose.
2. **"Closes the larger pane" should be rejected.** Size is a bad identity:
   at 50/50 there is no larger pane, after ratio steps the larger pane may not
   be the one the user wants to drop, and nothing in the chrome marks which
   pane is "larger". Both surfaces already have close-focused semantics (`q`,
   `close_focused_pane`); the third pane should follow them. Keep "larger"
   out of the model entirely.
3. **`ctrl+b` collides in the deck context.** `bindings.py` already binds
   `ctrl+b` → `scroll_prompt_up` (paired with `ctrl+f` → `scroll_prompt_down`).
   `ctrl+f` itself is double-bound today (`scroll_prompt_down` *and*
   `toggle_deck_focus`), disambiguated by focus/context. A bare `ctrl+b` =
   "reverse focus" is only safe if it is scoped exactly the way `ctrl+f`'s
   focus arm is (pager screen and deck-focus contexts), and the prompt-scroll
   meaning must keep working when the prompt has focus. This is solvable but it
   is real work, not a one-line binding: audit every `ctrl+f`/`ctrl+b`
   consumer (modals, `vim_text_area`, `hint_input_bar`, command-line input all
   use `ctrl+b` = cursor-left today).
4. **`ctrl+shift+b/f` may not arrive from real terminals.** Many terminals
   report `ctrl+shift+<letter>` identically to `ctrl+<letter>`, so the swap
   binding can silently no-op outside GUI terminals. Precedent cuts both ways:
   the app already binds `ctrl+shift+o` and `ctrl+shift+d`, so Textual accepts
   the spelling — but acceptance is not delivery. Ship these as the primary
   with a guaranteed shift-free fallback each (see section 6), and verify with
   a Pilot test *plus* a manual matrix note, since Pilot bypasses terminal
   encoding.
5. **`ctrl+shift+d` is already taken: `debug_leak_snapshot`.** Either the leak
   snapshot moves to a new key or the delete-pane binding picks a free chord.
   Do not stack two actions on one chord by context if it can be avoided; both
   are global-ish app actions and someone will bleed through.
6. **Swap semantics are undefined.** With two panes "swap with previous/next"
   reduces to one operation, but the request names previous *and* next, which
   only differ with ≥3 panes. Does swap exchange pane *contents* (documents,
   trails, history state) keeping focus, or move *focus*? Does it wrap? What
   does it do with 2 panes or 1 pane (no-op? toast?)? Keep-focused + exchange
   contents + wrap-around is the least surprising (tmux `{`/`}`-style), and
   with 2 panes both directions coincide — say so explicitly.
7. **`ctrl+w` ("other pane") is undefined with 3 panes.** Today "other" ==
   "the one pane that is not source". With three panes the follow-into-other,
   doubled-`ctrl+w`-focus-other, and `show_in_other_view` paths need a new
   definition. The natural one: "other" = next pane in focus order
   (`(focused + 1) % n`), focus never moves. This must be a conscious decision,
   not an emergent `views[1 - index]` bug.
8. **Minimum-size math gets strict.** Current guards need 2×7 rows stacked and
   2×32 columns beside. Three panes need 3×7 rows / 3×32 columns plus frames —
   roughly ≥100 columns for a 3-beside and ≥24 rows for a 3-stacked layout,
   before ratio steps. On an 80×24 terminal most 3-pane requests must be
   refused with the "try the other orientation" toast. The feature will read
   as broken on small windows unless refusal messaging is designed alongside
   it. Also decide whether ratio stepping still offers only (30,50,70): a
   3-pane needs *two* ratios (or one ratio + equal-split remainder) — the
   current single-`ratio` field cannot express it.
9. **"Two views × two panes" vs "nested split of the focused pane" are two
   different architectures; the proposal mixes them.** "Splitting the
   currently focused pane vertically" describes a *tree* (tmux-style nested
   splits: the outer stays horizontal, the focused pane subdivides). "Two
   additional views that each use three panes" describes *templates* (fixed
   3-pane arrangements you switch between). A tree is strictly more general
   but costs much more: recursive layout application, per-node ratios,
   recursive fit checks, N-pane chrome/label/focus/history logic, and goldens
   for every reachable tree. Templates cap the state space at ~6 layouts and
   keep every existing 2-pane code path a special case of the template logic.
   For a reading pager and a deck panel, templates win on reliability per unit
   of complexity. Cap at 3 panes; do not build a general N-pane tree.
10. **Deck/pager parity is assumed but the two models already disagree.**
    Unsplit keeps focused (pager) vs panel 0 (deck); grow/shrink keys differ
    (`+`/`-` vs `{`/`}`); footer/help rows differ; only the pager has
    `split_seed` clone semantics and per-pane history generations, only the
    deck has zoom/choose-panel/nodes-collapse. A shared "do both at once"
    diff will sprawl across both subsystems plus persistence, goldens, and
    docs. Sequence it: pure-model + pager first, deck second, shared keymap
    polish last (section 9).

## 4. Alternatives considered

- **A. Nested binary tree (tmux-like).** Most expressive; highest cost in
  layout code, fit checks, focus cycling, `ctrl+w` routing, and visual tests.
  Rejected for this milestone: nothing in the reading/deck use cases needs
  depth-2 nesting that templates cannot show.
- **B. Fixed 3-pane templates (recommended).** Add exactly two layouts per
  surface. Pager: `BELOW_THEN_BESIDE` (stacked pair on top? — no; pick the two
  useful tilings below) — concretely I propose the two tilings that match the
  request's nesting description without a tree:
  - `H3`: outer side-by-side pair where the *second column is itself split
    horizontally* — i.e. what you get by splitting the focused pane of a
    BELOW layout the other way. Hmm, naming aside, the two tilings are: (1) a
    horizontal 2-split whose focused half is vertically subdivided (one wide
    pane + two stacked panes), and (2) a vertical 2-split whose focused half
    is horizontally subdivided (one tall pane + two side-by-side panes).
  - Represent each as `(outer: Layout, inner_index: 0|1, inner: Layout)` with
    the constraint `inner ⟂ outer`. That is 2 outer × 2 inner positions = 4
    states, but the request only needs the focused-half variants; still,
    storing `inner_index` is nearly free and removes the "which half split?"
    ambiguity the proposal leaves open. If thrift is preferred, fix
    `inner_index = focused at nest time` and drop the field — but then focus
    movement after nesting must be specified (focus stays in the pane the user
    was in; it becomes one of the two inner panes deterministically).
- **C. Simple 1×3 / 3×1 strips only.** Cheapest (one ratio list of two splits,
  trivial CSS), but it cannot express the L-shaped tilings the request
  actually describes, and a 3-beside strip almost never fits at 80 columns.
  Rejected as the *only* 3-pane form; acceptable as a fallback if fit checks
  force it — no, keep the two L-tilings and let the fit guard refuse.
- **D. Improve 2-pane instead of adding 3-pane.** Worth naming: most of the
  user value (compare two versions, keep context visible) is already served by
  2-pane + `ctrl+w` + zoom (deck) / reading anchor (pager). If 3-pane proves
  too cramped in practice, the fallback is: ship focus-reverse + swap + delete
  on the 2-pane model and defer the third pane. I do not recommend leading
  with D — the request is explicit — but sequence the work so D is a shippable
  intermediate (keymaps land on 2-pane first, 3-pane templates second).

## 5. Data-model design (both surfaces)

- Pager `PagerSplitState`: add the two template layouts to `PagerSplitLayout`
  (e.g. `BELOW_SPLIT_SECOND` / `BESIDE_SPLIT_SECOND`, or the
  `(outer, inner_index, inner)` triple form), keep `focused ∈ {0,1,2}`, and
  replace single `ratio` with a pair (e.g. `ratio_outer`, `ratio_inner`, each
  drawn from `RATIO_STEPS`). All existing pure functions keep their names and
  gain 3-pane branches; `toggle_focus` becomes cycle-forward `(focused+1) % n`.
  `split_fits` checks outer then inner extents against the same minima.
- Deck `DeckAreaState`/`DeckLayout`: same treatment; `panels` becomes length
  ≤3; `choose_new_panel` runs a second time against the two shown decks for
  the third panel (duplicate-Main takes the next-next card; duplicate-FILES
  nudge generalizes from "panel 1" to "the new panel"); zoom snapshot already
  stores full state so it generalizes if `apply_state`/chrome loops stop
  assuming indices {0,1}.
- Audit every `1 - index` / `len(...) == 2` site when generalizing:
  pager `_screen_split.py` (`close_view`, `_toggle_split`, `_apply_split_state`,
  `focus_other_view`, `show_in_other_view`), deck `area.py`
  (`apply_state`, `visible_panels`, `focused_panel`), and
  `_agent_detail_deck_layout.py` (`toggle_deck_split`, `_open_deck_split`
  indices). `focused` must always satisfy `0 ≤ focused < len(panels)`.

## 6. Keymap design (proposed, conflicts resolved)

State diagram (both surfaces; deck names in parentheses):

| From | Key | To |
|---|---|---|
| SINGLE | `\` (`below`) | 2-BELOW, focus=new |
| SINGLE | `\|` (`beside`) | 2-BESIDE, focus=new |
| 2-BELOW | `\|` | 3-pane template H (focused half subdivided), focus stays in subdivided pane |
| 2-BESIDE | `\` | 3-pane template V (focused half subdivided), focus stays |
| 3-pane H | `\` | back to 2-BELOW (drop the inner subdivision; focused pane survives) |
| 3-pane V | `\|` | back to 2-BESIDE |
| 3-pane H | `\|` | rotate to 3-pane V (keep all three documents, focus, ratios) |
| 3-pane V | `\` | rotate to 3-pane H |
| 2-BELOW | `\` | SINGLE (keep focused — pager rule; adopt in deck too) |
| 2-BESIDE | `\|` | SINGLE (keep focused) |

Focus/swap/delete:

- `ctrl+f` cycles focus forward, `ctrl+b` cycles *backward* — scoped to the
  pager screen and to deck-focus contexts only, leaving the existing
  prompt-scroll / cursor-left `ctrl+b` meanings intact where the prompt or an
  input has focus. With 2 panes backward == forward; document that.
- Swap: `ctrl+shift+f` / `ctrl+shift+b` exchange the focused pane's content
  with the next/previous pane's content, focus follows the content (i.e. the
  user's pane moves with them), wrap-around, no-op when single. Add shift-free
  fallbacks (pager: reuse `{`/`}`? no — those are history-first/now. Propose
  pager `ctrl+w {` / `ctrl+w }`-style or explicit `alt+[` / `alt+]`; deck: keep
  `ctrl+shift` primary + palette/command entries as fallback). No-op (not
  toast) when fewer than 2 panes.
- Delete: needs a new home since `ctrl+shift+d` is `debug_leak_snapshot`.
  Options: (a) move leak snapshot to a clearly-debug chord and take
  `ctrl+shift+d`; (b) use `ctrl+w x`-style or `alt+x` for delete-pane. Either
  way the guard is "enabled iff ≥2 panes visible" and the semantics are
  close-focused (== `q` in pager). Unsplit-to-single stays on the same-key
  path in the table above; delete-pane is the explicit alternative that also
  works from 3-pane (3→2, dropping the focused pane and keeping the other
  two with focus on the next survivor).

## 7. Reliability notes

- Third-pane seeding: pager clones via `split_seed`/`apply_split_seed` (same
  document, reading position, trail) and each pane then steps independent
  history — the third pane must get its own history generation and
  `SectionTimeState`/cache copies (the sase-1eg land-note bug class: source
  generation bumps, band-hint clearing, `_pending_action` routing). Deck third
  panel goes through `choose_new_panel`, not cloning.
- The `_split_in_flight` guard, async mount/remove workers, and
  small-window refusal toasts must cover the 3-pane transitions; fit-check
  *both* orientations before nesting (a nest that fits the outer but not the
  inner must refuse with the naming-the-other toast, not half-mount).
- Transient per-pane state (label prefix, `y`/`E`/`ctrl+w` arms, goto/search)
  already cancels on focus loss — with 3 panes the "losing pane" is
  whichever had the arm, not "the other one"; keep the cancel logic
  pane-keyed, not index-keyed.
- Persistence (deck layout save) and footer/help/`docs/pager.md` key tables
  must version or extend for the new layouts; old saved states (layout strings)
  must still load.

## 8. Beauty notes (last but not least, as requested)

- Chrome: keep today's rule — full-strength accent frame on the focused pane,
  dimmed frames elsewhere; the two sub-panes of a subdivision share the dim
  style so the eye reads "2 groups, 3 panes". Subject-as-border-title /
  position-as-subtitle already works per-pane; verify the narrower inner panes
  truncate titles gracefully (ellipsis, no wrap) at ~32 columns.
- Ratios: 50/50 outer with a 50/50 inner reads best at ≥120 columns; below
  that the fit guard will refuse most 3-panes, which is correct — a refused
  split with a helpful toast is more beautiful than three unreadable slivers.
  Consider whether ratio steps for inner splits should offer only (50,) at
  small widths; simplest is to keep (30,50,70) for both and let `split_fits`
  veto.
- Footer/help: the one-shared-footer pattern holds; extend the split verbs
  (`^F/^B pane`, swap/delete verbs) without overflowing — likely requires
  shortening or context-gating (show swap/delete only when split). Every new
  key needs a help row (`_trail_chrome_help.py`, deck bindings help) and a
  `docs/pager.md` + Agents-help entry; add PNG goldens for both 3-pane
  templates (the sase-1eg.5 pattern: 4 split goldens + docs rows).
- Motion: no animated transitions; state changes apply atomically with focus
  already on the surviving pane so screen-reader/compositor order is stable.

## 9. Recommended solution (build order)

1. **Pure models + property tests.** Extend pager `split.py` and deck
   `layout.py`/`model.py` with the two template layouts, 3-way focus cycling,
   paired ratios, and `split_fits` for three panes. Port every `1 - index`
   assumption. Unit-test the full table in section 6 as pure transitions.
2. **Pager 3-pane.** Generalize `_screen_split.py` to N≤3 views (mount, remove,
   `_apply_split_state` CSS for the two templates, click-to-focus, per-pane
   label scoping, `ctrl+w`-means-next, third-pane seed/history independence).
   Add `test_app_split3`-style Pilot tests + goldens.
3. **Deck 3-pane.** Third `DeckPanel` in `DeckArea.compose`, generalized
   `apply_state`/`visible_panels`/zoom chrome, `choose_new_panel` second
   pass, persisted-state migration, deck Pilot tests.
4. **Keymaps last:** `ctrl+b` reverse-focus (context-scoped, prompt-scroll
   preserved), swap pair with shift-free fallbacks, delete-pane on a
   non-`debug_leak_snapshot` chord with the ≥2-pane guard. Update footers,
   help, `docs/pager.md`, Agents bindings help.
5. **Polish gate:** goldens for both templates on both surfaces, small-window
   refusal toasts, docs key tables, `just check` + visual suite.

## 10. Adjustments to the request (explicit)

1. Rejected "closes the larger pane" → close-focused everywhere (section 3.2).
2. Replaced prose toggle rules with the explicit table in section 6 (single
   extra keypress reaches the other 3-pane form via rotate; same-key from a
   3-pane steps back to its parent 2-pane, not to single).
3. Unsplit keeps the *focused* pane on both surfaces (pager rule wins; deck
   changes from keep-panel-0) — one rule to learn (section 2, 6).
4. `ctrl+b` scoped, not global (section 3.3); `ctrl+shift+d` relocated or
   replaced due to `debug_leak_snapshot` (section 3.5); swap pair gains
   shift-free fallbacks due to terminal delivery limits (section 3.4).
5. Defined with-3-panes semantics the request leaves open: `ctrl+w` target =
   next pane in focus order; swap = exchange contents, focus follows content,
   wrap-around, no-op when single (sections 3.6–3.7).
6. Capped at exactly 3 panes via fixed templates — no general nesting tree —
   with fit-guard refusal as a designed outcome (sections 3.8–3.9).
7. Sequenced deck and pager separately with a shippable 2-pane+keymaps
   intermediate (sections 3.10, 9) rather than one combined diff.
