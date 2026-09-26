# Deck and Card Paging Modes: UX and Implementation Recommendation

- **Researcher:** cdx
- **Date:** 2026-09-26
- **Scope:** follow-on UX after `sase-19x` (agent data card blocks)
- **Code reviewed:** `sase` at `6a6ae5d10`, including the landed `sase-19x.1`–`.7`
  work and the accepted epic plan for the remaining rail, docs, and visual work

## Bottom line

Treat the three layouts as one ordered **paging-depth** choice, not as two independent
deck/card booleans:

| Paging depth | Deck rendering | Card-block rendering | User-facing short name |
| --- | --- | --- | --- |
| none | spread | spread | **spread all** |
| card | paged | spread | **page cards** |
| block | paged | paged | **page blocks** |

This model encodes the `sase-19x` invariant that a spread deck always spreads its card
blocks. It therefore cannot express the invalid fourth combination, “spread deck,
paged card.”

Keep today's size-based behavior as **adaptive** mode. Add a panel-local **fixed**
override that cycles through the three paging depths. Show a persistent badge in the
deck-panel border subtitle, for example:

```text
adaptive · spread all
fixed · page cards
fixed · page blocks
```

At wider widths the badge can expand to the fully explicit forms `deck spread · card
spread`, `deck paged · card spread`, and `deck paged · card paged`. The badge must have
higher width priority than deck availability counts; unlike today's `spread` tag, it
must not be the first thing discarded on a narrow panel.

Bind uppercase `P` to cycle the focused panel forward through the applicable depths and
`,P` to clear the override and return to adaptive behavior. Add direct command-palette
actions for adaptive, spread all, page cards, and page blocks. This gives the common
operation one keystroke, retains an obvious escape from a fixed override, and avoids
another terminal-sensitive modifier chord.

## 1. What exists after `sase-19x`

The underlying interaction has three nested levels:

```text
deck panel -> deck -> card -> optional card blocks
```

The accepted `sase-19x` behavior is deliberately asymmetric:

- A multi-card deck is spread when it fits `spread_max_screens`, otherwise paged.
- A card shown alone is block-spread when it fits
  `block_spread_max_screens`, otherwise block-paged.
- A spread deck always spreads every card's blocks. Block navigation must never cause
  the deck itself to change mode.
- `Ctrl+J` / `Ctrl+K` navigate cards in either deck mode.
- `[` / `]` navigate older/newer card blocks in every mode where blocks are navigable.
- The block rail is shown for a navigable card in both block-spread and block-paged
  modes. The rail intentionally does not distinguish those modes.
- Mode changes caused by sizing already preserve a hierarchical `ReadingAnchor`
  containing card, block, offset, and bottom-pin state.

That last point is important: the expensive transition semantics already exist. A
manual selector should feed those same transitions instead of creating a second render
path.

The code currently represents each layer with the same binary `RenderMode` enum and
derives it automatically:

- `panel_spread.py` decides the deck mode.
- `panel_blocks.py` decides the block mode when one card is shown alone.
- `panel_transitions.py` captures/restores the reading anchor.
- `panel_chrome.py` passes a single `spread: bool` to `deck_subtitle()`.
- `titles.py` renders the word `spread` only for the positive case.

No Rust-core work is warranted. This remains presentation-only, panel-local TUI state.

## 2. The current status indication is insufficient

Today's deck-panel subtitle shows `spread` when the active deck is spread and shows
nothing when it is paged. That has four problems:

1. **Paged is represented by absence.** A reader has to know that a missing word is a
   state, not a width fallback or a rendering delay.
2. **The tag is low priority.** `deck_subtitle()` explicitly tries a candidate without
   the spread tag before it drops the counted deck switcher. The state indicator can
   therefore disappear precisely in narrow split panels, where the mode is most likely
   to change.
3. **It has no lower-level state.** The new rail appears in both block-spread and
   block-paged modes, so neither rail presence nor the block cursor tells the reader
   whether all blocks or one block are rendered.
4. **It does not explain why the mode may move.** An automatically selected layout can
   flip after a resize, split, header expansion, or streamed content crossing the
   hysteresis band. A fixed user override should not look identical to that adaptive
   result.

The existing visual hierarchy also rules out several tempting locations:

- The border title is already deck + card: `◆ MAIN | Context | Reply 2/2`.
- The block rail is the session timeline and has a dense width-degradation strategy of
  its own.
- In-content labels scroll away and would be duplicated for every card in a spread
  deck.
- A transient toast confirms a keypress but cannot answer “what mode am I in now?”
  later.

The border subtitle is therefore still the right home; its content and width priority
need to change.

This aligns with the basic status-visibility principle: current state should remain
visible so a user can predict the next action, not merely flash after the action
([Nielsen Norman Group](https://www.nngroup.com/articles/visibility-system-status/)).
The three layouts are closely related choices affecting the same view, which is also
the use case that segmented/content-switcher guidance assigns to a single-select
control rather than unrelated toggles
([Apple HIG](https://developer.apple.com/design/human-interface-guidelines/segmented-controls),
[Carbon Design System](https://carbondesignsystem.com/components/content-switcher/usage/)).

## 3. Model one paging depth, not two switches

Two independent commands such as “toggle deck paging” and “toggle card paging” expose
four bit combinations even though only three layouts are legal. The invalid combination
then has to be rejected, silently normalized, or made to perform two changes. Each
choice makes the mental model harder:

```text
deck spread + card spread   valid
deck spread + card paged    invalid by sase-19x invariant
deck paged  + card spread   valid
deck paged  + card paged    valid
```

Instead, introduce a composite presentation enum distinct from the existing layer-local
`RenderMode`:

```python
class PagingDepth(StrEnum):
    NONE = "none"    # spread all
    CARD = "card"    # page cards; spread the active card's blocks
    BLOCK = "block"  # page cards and the active card's blocks
```

The name describes where paging begins in the hierarchy. It also extends cleanly to a
card without blocks: `BLOCK` is simply unavailable there, so cycling skips it. Do not
call the enum `RenderMode`; that name already means spread/paged at one layer.

### Effective state versus policy

There are two concepts and the UI should not conflate them:

- **Policy:** adaptive, or a fixed paging depth selected by the user.
- **Effective state:** the layout currently rendered after considering which levels
  actually exist.

Adaptive policy runs the existing thresholds and maps their results to a paging depth.
Fixed policy bypasses the relevant threshold decisions. The badge shows both the policy
source (`adaptive` or `fixed`) and the effective depth.

For a card/deck shape where a depth is meaningless, cycling should visit only distinct
effective layouts:

| Focused content | Applicable cycle |
| --- | --- |
| Main deck, active/preferred block card, multiple cards | spread all -> page cards -> page blocks |
| Multi-card Main with a non-block card active | spread all -> page cards |
| Multi-file Files deck | spread all -> page cards |
| Single-item deck / Tools | no action; omit the badge unless useful as passive status |

When the user moves from Context to Reply, the block depth becomes applicable. A fixed
block preference may be retained internally for Reply, but the badge must describe the
effective current layout, not claim that a blockless Context card is “block-paged.”

## 4. Adaptive default plus an explicit fixed override

Removing adaptive sizing would discard one of the deck design's strengths: small
documents are easy to scan as one page, while large documents avoid massive rendering
and navigation costs. A manual command should supplement this behavior, not replace it.

The interaction should be:

1. A panel starts in **adaptive** policy, using the two existing thresholds and
   hysteresis.
2. On the first cycle keypress, take the current effective depth as the anchor, advance
   to the next applicable depth, and install that as a **fixed** override. This ensures
   every keypress visibly changes the layout; it does not first “fix” the same layout.
3. Further presses cycle the fixed applicable depths with wrapping.
4. A separate reset action clears the override and immediately recomputes adaptive
   mode.

A separate reset is better than adding `adaptive` as a fourth stop in the main cycle.
The user asked for three visual states, and an adaptive stop can resolve to the same
visual state as the preceding fixed stop. The only apparent change would be a tiny
badge word, making the cycle feel as if it ignored a keypress. A direct reset is also a
clear exit from a choice, consistent with general user-control guidance
([Nielsen Norman Group](https://www.nngroup.com/articles/ten-usability-heuristics/)).

### Override lifetime and scope

Use a **panel-local, per-deck, session-local** override:

- It affects only the focused deck panel, matching card, block, search, scroll, split,
  and zoom actions.
- Two split panels may intentionally use different depths.
- It survives node changes, deck switches, split rotation, zoom, resize, and streaming
  for the life of the TUI process.
- It resets to adaptive on application restart and is not added to
  `ace_agents_deck_state.json` in the first implementation.

This is the best balance between stability and surprise. Resetting on every selected
node would make a triage workflow fight the view. Persisting a fixed override across
application restarts would silently defeat the configured adaptive thresholds long
after the user forgot pressing the key. The configuration keys remain the durable way
to request an always-paged bias; the key is a working-session override.

Do not implement the key by rewriting `spread_max_screens` or
`block_spread_max_screens`. Those settings are user configuration, shared by panels,
and thresholds rather than exact three-state policy.

## 5. Persistent mode badge

Replace the asymmetric `spread` tag with a width-tiered badge. Recommended tiers:

| Width tier | Adaptive example | Fixed example |
| --- | --- | --- |
| wide | `adaptive · deck paged · card spread` | `fixed · deck paged · card paged` |
| normal | `adaptive · page cards` | `fixed · page blocks` |
| compact | `A · cards` | `F · blocks` |

For the first state use `spread all`, not `page none`; it matches the established SASE
term and describes what the reader sees. In help and docs define the three short names
once:

- **spread all** = deck spread, card blocks spread
- **page cards** = deck paged, active card's blocks spread
- **page blocks** = deck paged, one block at a time

The candidate ordering in `deck_subtitle()` should prioritize information as follows:

1. critical deck status such as Files line/cap status;
2. the mode badge;
3. the deck switcher;
4. deck counts.

At minimum, drop counts and then the switcher before dropping the mode badge. The title
already names the active deck, while no other persistent surface names its render mode.
Use the deck accent for the selected fixed state and dim styling for `adaptive`; do not
rely on color alone because the words carry the distinction.

After a keypress, also show a short confirmation toast such as:

```text
View fixed: page blocks  ·  ,P returns to adaptive
```

The toast is feedback; the badge remains the source of truth.

## 6. Keys and discoverability

### Recommended defaults

| Key | Action | Behavior |
| --- | --- | --- |
| `P` | `cycle_deck_paging_depth` | Cycle the focused panel through distinct applicable depths, wrapping |
| `,P` | `reset_deck_paging_depth` | Clear the focused panel/deck override and return to adaptive |

Why `P`:

- It is a printable key that survives the user's kitty/tmux path.
- It is currently unbound in the Agents app context.
- It is mnemonic for **paging** and pairs with lowercase `p`, the existing deck picker,
  without colliding with that action.
- Three stops do not need a forward/reverse pair; the desired state is at most two
  presses away.
- It avoids consuming another structural punctuation pair. `[`/`]` already navigate
  blocks, `{`/`}` resize split panels, `\\`/`|` control splits, and `(`/`)` already
  select artifact file versions in another context.

The key should be non-priority so inputs retain text entry. Gate it to the Agents tab,
no prompt-input ownership, a focused deck panel, and at least two distinct effective
layouts. Add `P view` to the contextual footer only when available.

The command palette should also offer four deterministic commands:

- `Deck view: Adaptive`
- `Deck view: Spread all`
- `Deck view: Page cards`
- `Deck view: Page blocks` (available only when a block-capable card exists)

Direct palette commands matter even with a cycle key: they make the vocabulary
discoverable, let a user select a known state without counting presses, and provide a
mouse-accessible route through the existing palette.

### Alternatives considered

**Separate deck and card toggles:** reject. They expose an impossible fourth state and
make the card command's behavior conditional on the deck command.

**`(`/`)` as previous/next mode:** viable but weaker. They match the punctuation-pair
family, but require shifted digit keys, have no mnemonic, and still need a reset to
adaptive.

**A leader-only cycle:** reject as the primary route. This is a lightweight visual
operation likely to be used while comparing layouts; two keys add friction. A leader
reset is appropriate because reset is less frequent.

**Put adaptive into the main cycle:** reject. It creates four policy stops for three
visual states and can yield a no-visible-change press.

**Only show a toast:** reject. It fails the original requirement to make the current
state clear after the toast expires.

**Put the mode in the block rail:** reject. The rail intentionally appears in both
block modes, is absent for other cards/decks, and already spends its width budget on
block identity, status, arrivals, and navigation hints.

## 7. Transition behavior and edge cases

Manual mode changes should be first-class inputs to the existing transition machinery.
They should not directly swap CSS classes or call view rendering without an anchor.

Required behavior:

- Capture the existing `ReadingAnchor(card_id, block_id, offset_rows, pinned)` before a
  fixed-depth transition and restore it with the current specificity fallback.
- Preserve the preferred card. Cycling from spread while scrolled inside Reply should
  page Reply, not jump to Context.
- Preserve the active block by id when going between page cards and page blocks.
- Preserve a bottom pin. Otherwise retain the block-relative offset where meaningful
  and clamp to the block/card top when a projection removes preceding content.
- A fixed override must not change because of resize, split ratio, header/jump-panel
  toggles, streaming growth, or hysteresis. Only content applicability can collapse an
  unavailable depth.
- Adaptive mode continues to use the current thresholds, hysteresis, partial-document
  guard, and deferred measurement.
- Partial documents never change either the adaptive decision or the manual override.
- A spread deck continues to force all blocks inline regardless of a retained lower
  preference.
- Search corpus, `E` export, `V` pager, fold state, clipboard behavior, and block cursor
  order remain document-wide and unchanged.
- Files supports the two applicable depths (spread all/page cards); Tools and any
  single-item deck do not advertise a no-op cycle.

If a fixed depth becomes temporarily unavailable after selecting another subject, keep
the preference panel-locally but badge the **effective** depth. When a compatible Reply
card returns, the fixed lower depth applies again. A one-time toast is unnecessary for
normal node navigation; the `fixed` badge is sufficient explanation.

## 8. Suggested implementation shape

1. **Pure model.** Add `PagingDepth`, a cycle helper that filters to applicable depths,
   and mapping helpers between a depth and `(deck_mode, block_mode)`. Unit-test this
   without Textual.
2. **Panel-local policy.** Add an override store to each pre-composed `DeckPanel`, keyed
   by deck (and, where needed, stable card id). Keep it out of `DeckAreaState` and the
   persisted snapshot for v1.
3. **One resolver.** Create a helper returning policy source, requested depth, effective
   depth, deck `RenderMode`, and optional block `RenderMode`. Both chrome and rendering
   should consume this result so the label cannot disagree with the view.
4. **Decision integration.** Let `_decide_main_mode`, `_decide_files_mode`, and
   `_block_mode_for_card` consult the resolver. Adaptive uses the existing measurement;
   fixed values bypass it.
5. **Transitions.** Route a cycle/reset through `_apply_main_transition` and the
   existing block-aware anchor restoration. For Files, reuse `_apply_files_transition`.
6. **Chrome.** Replace `spread: bool` in `deck_subtitle()` with a small mode-badge model
   and revise candidate priority. Do not infer the label from one Boolean.
7. **Commands and keys.** Add availability, action methods, command catalog entries,
   footer/help rows, default keymaps, keymap schema/model fields, and command-palette
   direct actions. Update `src/sase/default_config.yml` as required by project
   convention.
8. **Documentation.** Document the three names, adaptive versus fixed, scope, reset,
   keys, and the two threshold settings. Avoid calling this a “toggle” in prose when it
   is a three-way cycle.

Do not add a feature flag unless the implementation lands before `sase-19x` removes
`card_blocks`; this is chrome/control layered on an already accepted behavior and has a
clean test boundary.

## 9. Verification matrix

### Pure tests

- The only full-depth states are `(spread, spread)`, `(paged, spread)`, and
  `(paged, paged)`.
- Cycling forward wraps and skips unavailable depths.
- First manual cycle advances from the adaptive **effective** depth.
- Reset removes the override and re-runs adaptive mapping.
- Badge text and width tiers cover all three depths and both policy sources.

### Widget/action tests

- `P` acts on the focused split panel only.
- Main Reply visits all three states without losing the active card/block/offset.
- Context and Files visit only their two distinct states; Tools is unavailable.
- `,P` returns to adaptive and can legitimately keep the same visual depth while
  changing the badge source.
- A fixed depth survives resize, streaming, deck switching, node switching, split
  rotation, and zoom.
- Adaptive mode still crosses both thresholds with the existing 10% hysteresis.
- Partial paints do not change policy or mode.
- Prompt input retains `P`.
- Footer, help, palette, and remapped keys all use the live keymap.

### Visual tests

Capture at least:

- all three Main/Reply depths at 120x40;
- adaptive and fixed badges at the same effective depth;
- a narrow left/right split proving the badge survives before deck counts;
- Files spread/paged badges;
- block rail in both page-cards and page-blocks states, proving rail presence is stable;
- focused versus unfocused panels with different fixed depths.

Inspect live after goldens. The most likely visual failure is not the mode transition;
it is the subtitle competing with the deck switcher, Files status, and narrow border
label truncation.

## Recommended solution

Implement a composite `PagingDepth` with three legal values—`NONE` (**spread all**),
`CARD` (**page cards**), and `BLOCK` (**page blocks**)—while retaining the current
threshold logic as the default **adaptive** policy. Add a session-local fixed override
per focused panel/deck; it survives normal navigation and geometry changes but is not
persisted across TUI restarts.

Replace the current optional `spread` subtitle tag with a persistent, width-tiered badge
that shows both policy and effective state: wide panels spell out `deck spread/paged ·
card spread/paged`, normal panels use `adaptive/fixed · spread all/page cards/page
blocks`, and narrow panels retain a compact badge before sacrificing it to deck counts.

Bind `P` to cycle forward from the current effective state through the applicable fixed
depths, and bind `,P` to return to adaptive. Add direct palette actions for all three
depths plus adaptive, a contextual `P view` footer hint, and normal help/docs entries.
Drive every change through the existing block-aware `ReadingAnchor` transition path so
the active card, active block, reading offset, and bottom pin survive. This gives the
user one coherent three-state control, makes automatic versus manual behavior visible,
and preserves the strongest property of the existing design: adaptive layout when the
user has not expressed a preference.
