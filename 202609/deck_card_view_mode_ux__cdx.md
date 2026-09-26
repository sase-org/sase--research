# Deck and card view modes: UX research and recommendation

- **Researcher:** cdx
- **Date:** 2026-09-26
- **SASE source reviewed:** `ec25a1a3338edf683336138a6e6819f7a5906ffa`
- **Context:** epic `sase-19x`, its accepted card-block plan, the earlier consolidated
  card-block research, the implemented deck/card/block state and transitions, keymap
  registry, chrome, persistence, tests, docs, and representative PNG goldens
- **Scope:** presentation-only Agents-tab behavior. This belongs in the Python/Textual
  frontend, not `sase_core`.

## Executive conclusion

Model the feature as one ordered **paging depth**, not as independent deck and card
toggles:

| View mode | Deck | Block-bearing card | Short label |
|---|---|---|---|
| Fully spread | spread | spread | `S/S` |
| Page cards | paged | spread | `P/S` |
| Page blocks | paged | paged | `P/P` |

There are exactly three valid layouts because a spread deck intentionally forces all of
its cards' blocks inline. The fourth Boolean combination, deck spread plus card paged,
is invalid and should not be representable in state, keys, or UI.

Put a permanent, tiered mode chip in each deck panel's **top border title**, beside the
deck and card tabs. At wide widths spell it out (`DECK PAGED · CARD SPREAD`); at compact
widths use `D:P · C:S`; at the micro tier use `P/S`. Render both modes symmetrically,
including `PAGED`; do not rely on the block rail, the presence of tabs, or color. Keep
the existing bottom-border deck switcher for switching decks and remove its current
one-sided `spread` tag.

Add reversible cycling on **`(` and `)`**:

- `)` / `next_deck_view_mode`: fully spread → page cards → page blocks → fully spread
- `(` / `prev_deck_view_mode`: the reverse order

Parentheses complete the existing delimiter family (`[`/`]` navigate blocks,
`{`/`}` resize panels), are reliably delivered by terminals, and are available on the
Agents tab. They can be registered as contextual duplicates of the Artifacts-only
previous/next file-version actions that already own `(`/`)`.

Retain today's fit-based behavior as **Auto**, the default policy. A cycle key creates a
manual override for the focused panel and current deck; expose **Use automatic view**
as a command-palette action (configurable but unbound by default). The chip should say
`AUTO` or `FIXED` at its wide/compact tiers so a resize-driven automatic transition is
never confused with a user-locked layout. Persist the per-panel, per-deck policy, but
keep the existing block cursor ephemeral.

## 1. What exists now

### 1.1 The hierarchy and valid mode matrix are already settled

The accepted `sase-19x` design defines a strict hierarchy:

```text
deck panel → deck → card → optional card blocks
```

The current code has one `RenderMode` enum (`SPREAD`, `PAGED`) reused at both levels,
but the levels are not independent:

- A multi-card Main or Files deck is spread when its measured content fits
  `ace.agent_decks.spread_max_screens`; otherwise it is paged.
- Only a card shown alone in a paged deck gets a separate block-mode decision using
  `block_spread_max_screens`.
- A spread deck always renders every block inline.
- Cards with fewer than two blocks are trivially spread.
- Partial documents never decide a mode.
- Main-deck and block decisions share 10% hysteresis.
- Files decks containing image or video cards are forced paged because the spread
  renderer cannot represent those solo media cards.

That leaves three useful layouts, exactly the three in the request. Treating these as a
single ordered profile preserves the invariant by construction.

### 1.2 Current indication is asymmetric and low priority

`DeckPanelChromeMixin.refresh_chrome()` passes only one Boolean to `deck_subtitle()`:
whether the current deck is spread. `deck_subtitle()` then prepends the word `spread`
to the bottom-border switcher. Paged mode has no corresponding label.

This causes four concrete UX problems:

1. **Absence carries meaning.** A user must infer paged mode from the missing word
   `spread`, tabs, or visible content.
2. **Card mode is invisible.** In a paged Main deck, the block rail is shown for both
   block-spread and block-paged cards, so it cannot distinguish them.
3. **The status is the first thing discarded.** The subtitle's width tiers deliberately
   drop `spread` before dropping deck counts or the switcher. Narrow splits are exactly
   where mode changes are most likely, because viewport height and width participate in
   the decisions.
4. **It is spatially detached.** The mode belongs to the deck/card named in the top
   border, but the label appears among the deck switcher and line-count status in the
   bottom border.

Representative existing goldens confirm the ambiguity: a spread Files deck visibly says
`spread` at the bottom, while a paged Main deck says only `main 2 · files 0 · tools`.
There is no affirmative `paged` state.

### 1.3 The transition substrate is unusually ready for a manual control

The card-block work already added the hard part: `ReadingAnchor` captures card identity,
block identity, row offset, and bottom pin, then restores the most specific surviving
target across deck and block spread↔paged transitions. Manual view changes should go
through that same transition path. A second anchoring mechanism would be both redundant
and riskier.

Current panel state is already panel-local, and the focused-panel rule is consistent:
deck, card, block, scroll, search, fold, split ratio, and zoom actions all act on the
focused deck panel. A view-mode action should do the same.

## 2. UX goals

The design should satisfy these requirements:

1. **State is affirmative.** Both spread and paged must be named; paged must not be the
   absence of a label.
2. **Ownership is visible.** A user can tell whether the deck and the active card are
   spread or paged without deducing it from content.
3. **Invalid combinations are impossible.** Controls cannot request deck-spread plus
   card-paged.
4. **One action has one predictable scope.** It affects the focused panel, not both
   panels and not a hidden global configuration value.
5. **Manual intent is stable.** Streaming, resize, split rotation, header/jump-panel
   toggles, or a subject change must not immediately undo a user-selected layout.
6. **Automatic behavior remains the default.** The accepted fit-based heuristics and
   configuration remain valuable; the feature must not silently replace them.
7. **Narrow layouts remain legible.** A left-right split must still identify the mode.
8. **No keypress performs blocking work.** Main-deck toggling stays in-memory. Files
   spread preparation may use its existing asynchronous probe, but the action must
   return immediately.
9. **State is not encoded by color alone.** Text tokens survive themes, unfocused-panel
   dimming, monochrome capture, and users who cannot distinguish the accents.

## 3. Alternatives considered

### 3.1 Keep the existing automatic state and only improve the label

This is a worthwhile small fix but does not meet the control requirement. It also leaves
users unable to stabilize a layout while comparing agents or working in a split.

**Verdict:** necessary chrome work, insufficient solution.

### 3.2 Add independent “toggle deck mode” and “toggle card mode” actions

Two Booleans look flexible but create the invalid `S/P` combination. The implementation
then has to disable, rewrite, or defer the card toggle whenever the deck is spread. The
same keystroke sometimes changes a view, sometimes stores a latent preference, and
sometimes does nothing. The status UI also has to explain conflict resolution.

Separate keys would be useful only if all four combinations were meaningful. They are
not.

**Verdict:** reject.

### 3.3 One three-state ordered profile

An ordered profile exactly matches the valid matrix:

```text
SPREAD_ALL → PAGE_CARDS → PAGE_BLOCKS
```

It gives a compact status, a reversible cycle, one transition entry point, and no invalid
state. It also maps to the user's mental task: “show me more together” versus “isolate a
smaller unit.”

**Verdict:** recommend.

### 3.4 A modal or picker as the primary interaction

A picker could spell out all modes and Auto, but opening a modal for a three-item view
cycle is too much ceremony during triage. It is still useful in the command palette for
direct selection and for restoring Auto.

**Verdict:** secondary affordance, not the primary control.

### 3.5 Put another row of segmented controls inside every panel

This would be highly visible and easily clickable, but deck panels are often only
15–25 rows tall in a top-bottom split. Spending a permanent content row duplicates the
top-border title and competes with the new block rail.

**Verdict:** reject; use the border title.

## 4. Recommended interaction model

### 4.1 Separate policy from resolved layout

There are three **resolved layouts** but four **policies**:

```text
AUTO
SPREAD_ALL
PAGE_CARDS
PAGE_BLOCKS
```

This distinction is important. Auto is not a fourth visual layout; it resolves to one
of the three layouts using today's measurements, thresholds, hysteresis, and hard
capabilities. The explicit policies bypass fit measurement and stay stable until the
user changes or resets them.

Recommended semantics:

- New and migrated panel/deck state starts at `AUTO`.
- `)` while Auto is active selects the next explicit layout after the current resolved
  layout. `(` selects the previous one.
- Once explicit, `(`/`)` cycle the three explicit layouts and wrap.
- **Use automatic view** clears the override. Put it in the command palette and allow a
  user keymap, but leave it unbound by default to avoid adding a third rare shortcut to
  the footer.
- Direct palette commands—**Fully spread**, **Page cards**, **Page blocks**—are useful
  for discoverability and automation even though only previous/next need defaults.

The chip must expose whether the result is `AUTO` or `FIXED`. Otherwise a fixed layout
and an automatically chosen layout look identical until a resize behaves differently,
which is a classic hidden-mode error.

### 4.2 Scope and persistence

Store the policy **per visible panel and per deck**, not globally and not per subject or
per card:

- Panel 0 can be a stable “latest block” view while panel 1 is fully spread for context.
- A Files preference does not unexpectedly change the Main deck.
- Moving among agent rows preserves a chosen triage layout.
- Switching decks and returning restores that deck's preference.
- Per-card storage would create hidden state for every dynamic card id and make card
  navigation change the controlling preference.

Persist these policies beside each panel's deck and preferred card in
`ace_agents_deck_state.json`. Bump its schema and migrate v1 to Auto. Persistence matches
the existing treatment of layout, ratio, panel focus, deck selection, and preferred
card: these are durable workspace-view preferences. Do **not** persist the active block
or scroll anchor; `sase-19x` correctly made those ephemeral and subject-local.

### 4.3 Capability reduction

The profile is a preference, but the chip reports the **effective layout** for the
current content.

- Main deck with at least two cards and a block-bearing card: all three modes.
- Main deck with multiple cards but no card blocks: `SPREAD_ALL` and `PAGE_CARDS`;
  cycling skips the redundant block state.
- Main active card without blocks while another card has blocks: the deck can retain a
  `PAGE_BLOCKS` preference, but the chip shows `CARD —` on the non-block card. Switching
  to Reply makes `CARD PAGED` effective.
- Files: spread-all or page-cards. Page-blocks is structurally inapplicable and skipped.
- Files containing image/video: paged is a hard capability floor; do not force those
  cards through the text spread renderer. If a stored spread preference meets media,
  report the effective paged state and keep the preference for the next compatible
  subject.
- Tools and any one-card/no-block deck: no meaningful choice, so the cycle actions are
  unavailable and the chip shows the trivial effective state.
- Partial documents: retain the last full-document rendering and disable the action
  until the current subject's full document arrives.

Skipping duplicate effective states matters. A keypress that redraws the same content
with no explanation feels broken.

## 5. Mode chrome

### 5.1 Put the status in the top border title

The top border already names the deck and cards and highlights the active card. Add one
mode chip immediately after the deck name, with the card portion referring to the active
card:

```text
Wide, Auto and fully spread:
◆ MAIN  AUTO · DECK SPREAD · CARD SPREAD ┃ Context │ Reply

Wide, fixed card paging:
◆ MAIN  FIXED · DECK PAGED · CARD PAGED ┃ Context │ Reply  2/2

Compact:
◆ MAIN  A D:S C:S ┃ ‹ 2/2 › Reply
◆ MAIN  F D:P C:P ┃ ‹ 2/2 › Reply

Micro:
MAIN A S/S 2/2
MAIN F P/P 2/2
```

Use `CARD —` / `C:—` when the active card has no block mode. For a spread deck with a
block-bearing card, report `S/S`: the card's blocks are effectively spread by the
outside-in invariant even though no separate decision ran.

The labels should be text-first. Accent or reverse styling may distinguish the chip,
but `S`, `P`, `AUTO`, and `FIXED` carry the meaning. Unfocused panels dim the chip along
with the rest of their title.

### 5.2 Width priority

The title renderer already has full, compact, and micro tiers. Extend those tiers rather
than truncating a finished string. Recommended survival order:

1. deck name/glyph
2. effective mode chip
3. active card title
4. active position (`N/M`)
5. inactive card titles

This is a deliberate change from the current subtitle, where mode is discarded first.
The chip is most valuable in a narrow split, so it must survive there.

### 5.3 Keep navigation chrome separate

Remove the existing bottom-border `spread` tag after the top chip lands. The bottom
subtitle should remain the deck switcher plus Files line status. Duplicating the same
mode in both borders adds noise and preserves the old asymmetric code path.

The block rail remains a timeline/navigation control, not a mode indicator. It appears
in both block-spread and block-paged cards by design and should not change appearance to
carry mode state.

### 5.4 Feedback on a keypress

A mode key should synchronously update the chip, then recompose through the existing
transition machinery. If Files needs an asynchronous spread probe, show the requested
fixed policy in the chip with a restrained pending marker until the compatible result
is ready; never freeze the event loop.

A short toast is optional and useful only when a requested state is reduced by a hard
capability, for example: `Files view remains paged: media cards cannot spread.` Routine
cycles need no toast because the persistent chip is sufficient feedback.

## 6. Keymaps and discoverability

### 6.1 Default keys

Recommend:

| Action | Default | Meaning |
|---|---|---|
| `prev_deck_view_mode` | `left_parenthesis` (`(`) | Previous/shallower view profile |
| `next_deck_view_mode` | `right_parenthesis` (`)`) | Next/deeper view profile |
| `reset_deck_view_mode` | `unbound` | Return focused panel/current deck to Auto |

Why parentheses:

- They are an adjacent, reversible pair and arrive reliably through terminal/tmux.
- On Agents they complete a coherent delimiter family:
  - `[` / `]`: older/newer card block
  - `{` / `}`: shrink/grow focused split panel
  - `(` / `)`: previous/next view profile
- Their existing app owners, `files_prev_version` / `files_next_version`, are
  Artifacts-only, so the registry can allow the same tab-disjoint contextual duplicate
  pattern already used by the bracket and brace pairs.
- They avoid Ctrl+Shift chords, whose delivery failure was already proven during
  `sase-19x` research.

`(`/`)` should wrap, matching deck/card/block cycling elsewhere. The mode chip makes the
wrap visible. If later user testing finds wrap surprising, the pure cycle helper can be
changed to clamp without touching rendering or persistence.

### 6.2 Footer, help, and palette

- Footer: show `(/) view` only when at least two effective layouts exist for the focused
  deck. Do not add the Auto-reset action to the footer.
- Help: `(` / `)` — `Previous / next deck view mode`; add a one-line legend for
  `S/S`, `P/S`, and `P/P`.
- Palette: include cycle forward/reverse, the three direct modes, and **Use automatic
  view**. Keywords should include `view`, `layout`, `spread`, `paged`, `deck`, `card`,
  and `block`.
- Gating: Agents tab, prompt input does not own keys, focused visible panel, current
  deck has a full current-subject model, and at least two effective layouts exist.
- Search: treat both actions as structural deck-search exits, like card/block and deck
  navigation.

## 7. Transition behavior

Every mode change should capture one existing `ReadingAnchor` before recomposition and
restore it afterward:

1. same block plus row offset, if that block survives;
2. same card plus row offset;
3. card default;
4. document default.

Preserve a bottom pin. Do not change block `following` merely because the view profile
changed. Switching to page-blocks should show the scroll-derived active block, not
silently jump to the newest; switching back to a spread mode should top-align that block
with the established reserve/anchor behavior. This makes the new control a layout
change, not a navigation command.

For Main, explicit profiles should bypass both fit measurements:

- `SPREAD_ALL` ⇒ deck `SPREAD`; block mode implicit `SPREAD`
- `PAGE_CARDS` ⇒ deck `PAGED`; block mode forced `SPREAD`
- `PAGE_BLOCKS` ⇒ deck `PAGED`; block mode forced `PAGED` when the active card has at
  least two blocks
- `AUTO` ⇒ today's `_decide_main_mode()` plus `_decide_block_mode()`

For Files, explicit spread/paged should bypass the threshold decision, but spread may
still require the existing bounded asynchronous page probe. Hard solo-media paging wins
over policy.

## 8. Implementation shape

### 8.1 Pure model

Add a small pure module (or extend `model.py` if it remains focused) with:

- `ViewPolicy`: `AUTO`, `SPREAD_ALL`, `PAGE_CARDS`, `PAGE_BLOCKS`
- `ResolvedViewMode(deck_mode, card_mode, policy, constrained_reason=None)`
- forward/reverse profile cycling
- capability reduction for Main, Files, Tools, card count, block availability, and
  solo-media constraints
- full/compact/micro chip rendering inputs

Do not represent this as two optional `RenderMode` fields in persisted state; that would
permit the invalid `S/P` combination.

### 8.2 Panel and persistence

- Extend `DeckPanelState` with a per-deck policy map or a small fixed tuple for Main and
  Files. Tools can remain Auto/trivial.
- Bump the deck persistence schema; decode v1 as all-Auto and fail open per field.
- Add `DeckArea.set_view_policy(panel_index, deck, policy)` and focused-panel adapters.
- Route mode changes through `_apply_main_transition()` / `_apply_files_transition()`
  and the existing hierarchical anchor.
- Refresh chrome, block rail, footer availability, and persistence notification once
  after a successful change.
- Keep block cursors, arrivals, scroll positions, and following state where they are.

### 8.3 Chrome

Replace the `spread: bool` argument to `deck_subtitle()` with no mode responsibility.
Pass a resolved mode descriptor to `deck_title()` and make each title tier render its
own chip. This avoids coupling chrome to private panel dictionaries and makes width
behavior pure-testable.

### 8.4 Keymap pipeline

Follow the complete existing deck/card/block pipeline:

- `AppKeymaps`
- `default_config.yml`
- binding metadata and fallback bindings
- contextual duplicate allowlist for both parenthesis pairs
- app action availability and command context
- command palette metadata
- action handlers in the Agents panel-detail actions
- conditional footer, help, and deck-search exits

### 8.5 Performance

Manual Main modes should be cheaper than Auto because they skip measurement. A toggle
must not rebuild source data or touch files. It should reproject the already-built
document and rail. Reuse the same measurement caches when Auto is restored.

Forced fully spread can intentionally expose a very large Reply. That is a requested
override, not a reason to impose a silent size ceiling; preserve the lower-bound and
rendering safeguards and make the fixed status obvious. Solo media remains a hard
capability exception because there is no compatible spread renderer.

## 9. Verification matrix

### Pure tests

- the three valid layouts cycle in both directions and never produce `S/P`
- Auto resolves through existing threshold/hysteresis decisions unchanged
- capability reduction skips duplicate states
- single-card, no-block, one-block, multi-block, Files, Tools, and solo-media cases
- wide/compact/micro chip strings, including `CARD —`
- mode chip always fits its declared width; text, not color, distinguishes states

### Pilot tests

- each transition among `S/S`, `P/S`, and `P/P` preserves card/block/offset/pin
- toggling does not change block following or arrivals
- active Context under a retained `PAGE_BLOCKS` preference reports card N/A; Reply
  becomes block-paged
- partial paint cannot mutate policy or display stale subject state
- two split panels keep independent policies
- deck switching restores the selected deck's policy
- subject changes keep the panel/deck policy but reset block cursor as today
- Auto restoration resumes resize- and streaming-driven decisions
- Files media constrains spread without blocking or corrupting the stored preference
- prompt/search/key availability and contextual duplicate resolution
- persistence v1 migration, v2 round-trip, malformed-field fallback, zoom snapshot

### Visual tests

Capture and inspect at least:

- 120×40 single panel in all three layouts
- left-right split with one Auto and one Fixed panel
- narrow micro titles showing `S/S`, `P/S`, and `P/P`
- an active non-block Context card showing `C:—`
- Files spread, Files paged, and the media constraint
- focused/unfocused and dark/light theme variants

The visual acceptance criterion is simple: after covering the body text, a reviewer can
still identify the focused panel, current deck/card, effective deck/card modes, and
whether the choice is automatic or fixed.

## 10. Recommended solution

Implement a single ordered **view profile** with the three valid layouts:
`SPREAD_ALL (S/S)`, `PAGE_CARDS (P/S)`, and `PAGE_BLOCKS (P/P)`. Preserve fit-based
`AUTO` as the default policy, with explicit user choices acting as stable per-panel,
per-deck overrides and a palette action to return to Auto.

Show an always-present, width-tiered chip in the deck panel's top border title:
`AUTO/FIXED · DECK SPREAD/PAGED · CARD SPREAD/PAGED/—`, compacting to
`A/F D:S/P C:S/P/—` and finally `A/F S/S|P/S|P/P`. The chip must survive narrow splits;
remove the old bottom-border `spread` tag.

Bind `prev_deck_view_mode` to `(` and `next_deck_view_mode` to `)`, conditionally show
`(/) view` in the footer, and expose direct choices plus Auto in the palette. Use the
existing `ReadingAnchor` transition path so changing layout preserves the reader's
card, block, offset, pin, following state, and arrivals. Persist only the view policy;
keep block/navigation state ephemeral. This gives the feature a visible, coherent mental
model, makes invalid state impossible, and fits the existing SASE deck interaction
language with minimal new machinery.
