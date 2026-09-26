# Deck + card view-mode UX: making spread/paged visible and toggleable

Research report — how to show whether the spread or paged view is enabled for a
deck and/or card, and what keymap(s) should cycle the three view states
(fully spread · paged deck + spread card · paged deck + paged card).

## 1. Context and constraints

Card blocks (epic `sase-19x`, now fully implemented behind phases `.1`–`.8`)
add a third level to Agents-tab deck panels: deck → card → block. The mode
matrix from the epic plan (`plan:202609/agent_data_card_blocks.md`, §3.3) is:

| Deck mode | What is shown | Block mode | Rail |
|---|---|---|---|
| spread | every card on one page | always inline | hidden |
| paged, active card ≥ 2 blocks | that card alone | block-spread or block-paged via `block_spread_max_screens` (±10% hysteresis) | shown in **both** block modes |
| paged, active card < 2 blocks | that card alone | — | hidden |

Two structural facts shape everything below:

1. **There are 3 states, not 4.** A spread deck always spreads its blocks
   (plan decision D3: "only a card shown alone pages its blocks", because
   "block navigation must never flip the deck's mode"). So deck-spread +
   block-paged is not a reachable combination, and a two-independent-toggles
   design would have an invalid corner to explain away.
2. **View state is ephemeral and panel-local by design.** Block cursors live
   on each panel's pre-composed `MainDeckView`, scoped to the current subject,
   never persisted (no change to `ace_agents_deck_state.json`). Deck render
   mode uses same-subject hysteresis (`decide_render_mode` in
   `src/sase/ace/tui/widgets/decks/render_mode.py`, shared by
   `decide_block_mode` in `block_model.py`). Any toggle should follow the
   same philosophy: a temporary override, with the two
   `ace.agent_decks.{spread,block_spread}_max_screens` thresholds remaining
   the durable preference (including `0` = always paged).

## 2. What the user can see today (gap analysis)

I traced the current indicators through the chrome code:

- **Border subtitle** (`deck_subtitle()` in
  `src/sase/ace/tui/widgets/decks/titles.py`, wired by
  `DeckPanelChromeMixin.refresh_chrome()` in `panel_chrome.py`): shows a dim
  `spread` tag **only when the deck is spread**. Paged is the *absence* of a
  tag. Tier degradation drops the spread tag first when narrow.
- **Border title tab strip** (`deck_title()`): in a multi-card paged deck it
  shows the active tab highlighted plus a `2/5` position counter; in spread
  the strip lists tabs without a paged position. So deck spread-vs-paged is
  *inferable* but never *stated*.
- **Block rail** (`block_rail.py` tiered `block_rail_text` + `BlockRail`
  widget, docked under the Main panel border): shows the timeline pill in
  both block modes — deliberately, so it never pops in/out across the
  hysteresis band. But it says nothing about *which* block mode is active.
- **Footer** (`_display_detail_footer.py` + `_keybinding_bindings_agents.py`):
  conditional `cards` (`Ctrl+J/K`) and `blocks` (`[`/`]`) entries. No
  view-mode entry.
- **Help / palette**: deck section documents card cycling, block stepping,
  splits, zoom — no view-mode concept.

Net: **block-spread vs block-paged has no indicator at all**, and **paged is
communicated only by omission**. A user asking "which of the 3 states am I
in?" cannot answer it from the chrome today. That is the core defect to fix;
the toggle key is secondary.

## 3. Keymap landscape

Deck/card navigation today (app-level, `src/sase/default_config.yml` ≈
lines 655–669): `Ctrl+J/K` cycle cards, `[`/`]` step blocks, `Ctrl+N/P`
cycle decks, `p` deck picker, `\`/`|` splits, `Ctrl+F` panel focus,
`{`/`}` resize, `Ctrl+S` node panel. Phase `sase-19x.7` established the full
pipeline for adding a keymap: `keymaps/app_keymaps.py` field →
`default_config.yml` entry → `bindings.py` `Binding` →
`keymaps/metadata.py` + `keymaps/registry.py` (contextual duplicates) →
`_app_action_availability.py` gating set → `actions/agents/_panel_detail.py`
`action_*` → footer entry → `help_modal/agents_bindings.py` row → command
palette metadata (`commands/_app_metadata_nav.py`,
`commands/_availability_agents.py`) → deck-search exit keys
(`_deck_search_host.py`) → parity tests.

Candidate defaults for a view-mode key, checked against
`default_config.yml`:

- **`v` (app-level, Agents tab): free.** Lowercase `v` appears only as
  `command_line.block_pager` (a focused-command-line context, inactive
  elsewhere) and in Artifacts/Admin contexts. No Agents app-level or
  Agents focused-pane binding uses it. Mnemonic: *view*.
- **`V`: taken** (`show_agent_run_log` / `view_agent_metadata` on Agents).
  Do not default-bind reverse to `V`; panel-focus gating could theoretically
  disambiguate, but it overloads a destructive-adjacent inspection key.
- **`s`/`S`: taken in row context** (`save_marked_agents` /
  `bulk_change_status`). Same gating caveat, weaker mnemonic.
- `w`: free on Agents but mnemonic-poor.

So there is exactly one clean single-letter default: `v`.

## 4. Options considered

### A. One cycling key (`v`: view) through the 3 forced states — RECOMMENDED

One action, e.g. `cycle_deck_card_view`, wraps
fully-spread → paged-deck/spread-card → paged-deck/paged-card → back.
With 3 states, wrapping forward reaches any state in ≤ 2 presses, so no
reverse key is needed (a reverse saves at most one press in one case —
not worth a second default in a crowded map). Register the action in the
palette; leave any reverse unbound and user-configurable.

Mechanics: a panel-local ephemeral override holding a forced
`(deck_mode, block_mode)` pair that bypasses `decide_render_mode` /
`decide_block_mode` while set. Cleared on subject change (return to
threshold-derived auto), surviving deck switches, split rotation, and zoom
— mirroring block-cursor lifetime. Transitions reuse the hierarchical
`ReadingAnchor` capture/restore from `panel_transitions.py` (phase
`sase-19x.6` built exactly this for spread↔paged flips), so the toggle
preserves the reader's anchor instead of jumping to top/newest. No
persistence-schema change.

Edge semantics to pin: forcing fully-spread on a huge deck could render
thousands of rows — but that is already what the thresholds do when content
fits, and `measure_main_rows` short-circuits huge cards; the override only
skips the *decision*, not measurement. Forcing paged on a 1-card deck is a
no-op at deck level (single card always spreads per `decide_render_mode`)
and only affects the block dimension — fine. Forcing block-paged on a card
with < 2 blocks is a no-op — fine; the indicator (§5) still shows the deck
half honestly.

### B. Two separate toggles (deck spread/paged + card spread/paged)

Matches the two-threshold mental model and allows direct jumps. Rejected as
the default: it implies 4 combinations while only 3 are valid, so the
deck-spread + block-paged corner needs a collapse rule ("deck wins",
silently degrading one toggle's promise) that must then be explained in the
indicator anyway. Two keys also cost twice the map space for a 3-state
space. Could be offered later as unbound granular actions for power users,
but not the primary UX.

### C. Direct-select (picker modal or three keys)

Most explicit, most discoverable in modal form (mirrors the `p` deck
picker), but heaviest: a modal for a 3-way toggle is disproportionate, and
three keys is unjustifiable map spend. A view-mode picker could be a later
follow-up if telemetry/feedback shows users lost in the cycle — not the
first step.

### D. Config-only (document `spread_max_screens: 0`)

Already exists and stays the durable-preference story, but it is not
interactive and cannot express "temporarily force spread to orient, then go
back to auto". Complements the key; does not replace it.

## 5. Indicator design (the more important half)

Principle: **the mode must always be stated, never implied by omission**,
and the block half needs an indicator where none exists.

1. **Subtitle tag becomes 3-valued and always-on.** Extend `deck_subtitle()`:
   deck-spread keeps `spread`; deck-paged shows `paged`, plus the card half
   when the active card has ≥ 2 blocks — e.g. `paged · blocks spread` vs
   `paged · block 2/5`. Keep the existing widest-first tier degradation
   (drop block tag → drop counts → drop switcher), so narrow panels degrade
   gracefully and the deck tag is the last thing to go.
2. **Block rail gains the block-mode word.** The rail already renders in both
   block modes; append the mode (or the `v view` key hint, which fits the
   existing "key hint at the widest tier" convention) so spread-vs-paged is
   visible exactly where block navigation happens.
3. **Footer gets one conditional entry** (`v view`), shown when the focused
   panel has > 1 card or navigable blocks — same conditional pattern as the
   existing `cards`/`blocks` entries.
4. **Help + palette rows** follow the `sase-19x.7` pipeline (help deck
   section, palette metadata/availability, deck-search exits, parity tests).

Deliberately *not* recommended: coloring the border or title by mode (fights
the focus-accent system), and putting the indicator only in the footer
(footers are far from the content and already crowded).

## 6. Recommended solution

- **Ship one bound keymap**: `cycle_deck_card_view` on **`v`** (Agents tab,
  app-level, tab + panel-focus gated exactly like `[`/`]`), wrapping the 3
  forced states in the order fully-spread → paged deck + spread card →
  paged deck + paged card. Panel-local ephemeral override, cleared on
  subject change; transitions via `ReadingAnchor`; no persistence change.
  Full `sase-19x.7` pipeline (keymaps dataclass, defaults, bindings,
  metadata/registry, `check_app_action` gating, footer, help, palette,
  deck-search exits, parity tests) plus a `default_config.yml` comment
  update per the keymap gotcha.
- **Ship the always-on 3-valued subtitle tag + rail mode word** (§5.1–5.2)
  in the same change: the toggle without the indicator leaves the user
  pressing `v` with no confirmation of effect.
- **Leave reverse/direct-select unbound** (palette-available action only);
  revisit a picker only on evidence of confusion. Keep the two thresholds
  as the durable preference story and document the
  thresholds-vs-override relationship (`0` = always paged permanently;
  `v` = temporary force until subject change) in `docs/ace.md`.
- **Tests**: pure override-cycle unit tests (order, wrap, no-op corners from
  §4A), subtitle/rail tier goldens for all three states, and a keymap
  parity test mirroring `test_deck_card_block_keys.py`.

Why this shape: it matches the actual state space (3, not 4), costs one
clean key (`v` is the only free mnemonic), reuses the two hardest existing
mechanisms (anchor-preserving transitions, tiered chrome degradation), and
fixes the real defect — mode invisibility — rather than just adding motion.
