# Deck and card view depth: indicator and 3-state cycle

- **Researcher:** grk (independent swarm report)
- **Date:** 2026-09-26
- **Context:** epic `sase-19x` (agent data card blocks; phases `.1`–`.8` closed,
  `.9` cutover and `.10` docs still in progress) on top of shipped epic `sase-17d`
  (agent data decks and cards)
- **Scope:** presentation-only Agents-tab behavior after card blocks are fully
  landed. No `sase-core` change. No change to
  `ace.agent_decks.spread_max_screens` / `block_spread_max_screens` defaults.

## 0. Recommended solution

Treat spread versus paged as one **view-depth ladder** with three legal rungs,
plus the existing auto-fit policy as a way to leave the ladder.

| Rung | User's name | Deck | Card blocks | When it is distinct |
| --- | --- | --- | --- | --- |
| `spread` | fully spread | every card on one page | always inline (invariant D3) | two or more cards |
| `cards` | paged deck and spread card | one card | all blocks inline | the active card has two or more blocks |
| `blocks` | paged deck and paged card | one card | one block per page | the active card has two or more blocks |
| `fit` | (today's default) | auto from `spread_max_screens` | auto from `block_spread_max_screens` | always |

Ship two things together, in this order of user-visible value:

1. **A mode chip that cannot disappear**, in the deck panel **border title**,
   naming the effective rung. Auto-fit renders the word muted; a user pin
   renders it as an accent pill, the same language as the active card tab and
   the active rail entry. On the block rail, say `page 3/5` in `blocks` and
   `all 5` in `cards`. Remove the current subtitle `spread` tag so there is
   one source of truth.
2. **One cycle keymap** `cycle_deck_view` on **`B`**, with `cycle_deck_view_reverse`
   on **`Shift+B`**. `B` opens the document (more on one page):
   `blocks → cards → spread → fit → blocks`. The first press starts from the
   **effective** rung, so a typical large Reply (auto `blocks`) goes to `cards`
   on the first `B`. Direct palette commands exist for each rung. The pin is
   per focused deck panel, sticky across `j`/`k`, and persisted with the rest
   of `ace_agents_deck_state.json`.

Do not add a second independent "toggle card paging" key. The fourth combo
(spread deck + paged card) is forbidden by the accepted card-blocks invariant:
a spread deck always spreads its blocks. A cycle of the three legal rungs
cannot produce it. Two independent toggles can appear to do nothing.

## 1. Question

Once card blocks are fully implemented, two follow-ups:

- Make it clear whether spread or paged view is enabled **for the deck and for
  the card**.
- Add one or more keymaps that toggle through the three states the user named:
  fully spread; paged deck and spread card; paged deck and paged card.

This report decides the UX, the keymap, how auto-fit interacts with a pin, and
a concrete implementation shape against the code that exists today.

## 2. What the product does today

### 2.1 Two independent auto decisions

A deck panel already has two hysteresis decisions that share
`decide_render_mode()` (`src/sase/ace/tui/widgets/decks/render_mode.py`,
`SPREAD_HYSTERESIS = 0.10`):

- **Deck.** A multi-card Main or Files deck spreads when its cards fit
  `ace.agent_decks.spread_max_screens` viewport heights (default `1.5`; `0`
  means always paged). One-card decks (`card_count <= 1`) always report
  `RenderMode.SPREAD`, and spread versus paged then look the same. Files can
  force paged when a probe marks a page `has_solo` (images, video).
- **Card.** A card shown **alone** spreads its blocks when they fit
  `ace.agent_decks.block_spread_max_screens` (default `1.5`; `0` means always
  one block per page). Binding decision D3 of `sase-19x`: block paging is
  legal only for a card shown alone. A spread deck always inlines blocks.
  Block navigation (`[` / `]`) is specified never to flip deck mode.

Those two booleans produce four combinations on paper and **three** on screen:

```
                  card spread          card paged
deck spread       SPREAD               (illegal; coerced to SPREAD)
deck paged        CARDS                BLOCKS
```

This is why a 3-state cycle matches the product. A 2×2 control panel does not.

### 2.2 Chrome that already tries to speak, and fails

**Border title** (`titles.deck_title`): where am I. Glyph, deck name, card
tabs, `N/M` position. Full / compact / micro tiers. No mode.

**Border subtitle** (`titles.deck_subtitle`): what else. Optional Files line
status, a dim word `spread` when the **deck** is spread, then the
`main · files · tools` switcher. The documented drop order is:

1. status + `spread` + counted switcher
2. status + counted switcher
3. status + `spread` + bare switcher
4. status + bare switcher

`test_deck_spread_pure.py` asserts the tag is **dropped first** when width is
tight. Paged is the unmarked default: there is no `paged` word at all.
Block-spread versus block-paged is not mentioned.

**Block rail** (`block_rail.py`): one row under the Main top border, shown
whenever blocks are navigable **in a paged deck** (D4). Shown in **both**
`cards` and `blocks`. Hidden in a spread deck. The active entry is an accent
pill; the widest tier adds `[ older · newer ]`. The rail tells you blocks
exist and which one is active. It does not tell you whether the card is
showing one block or all of them.

**Footer:** `Ctrl+J/K` → `cards` when `deck_card_count > 1`; `[` / `]` →
`blocks` when `card_blocks_navigable`. Those advertise **motion**, not **mode**.

**Help / palette:** card and block motion keys are registered; there is no
view-depth action (`cycle_deck_view` does not exist).

### 2.3 Persistence and keys already spoken for

`~/.sase/ace_agents_deck_state.json` schema v1 stores `{layout, ratio, focused,
nodes_collapsed, panels: [{deck, preferred_card}]}`. Block cursors are
deliberately ephemeral and panel-local (`sase-19x` §3.1). Render mode is
recomputed from content, viewport, and hysteresis; it is not stored.

On the Agents tab, printable `B` is free at app level. Copy-mode `%B` is
`capture_agents_repro` and does not consume a bare `B`. `P` is also free
(`p` is the deck picker). Fold-mode `z` already owns section-fold levels
`z1`–`z4` / `zz` / `zZ`; mixing page-depth into fold-mode would collide two
different "how much is open" concepts on the same prefix.

`[` / `]` are taken by `prev_card_block` / `next_card_block`. `Ctrl+J` / `K`
cycle cards. `Ctrl+N` / `P` cycle decks. `Z` zooms the focused panel. The
card-blocks research already proved `Ctrl+Shift+J/K` arrives as `Ctrl+J/K`
in this tmux 3.5a + kitty chain and must not be reused.

### 2.4 Size facts that make the middle rung real

The accepted card-blocks research (`research:202609/agent_data_card_blocks/agent_data_card_blocks.md`)
measured 70 sessions: p50/p90/max shells 3/5/15, raw reply lines 72/738/14,013.
A 1.5-screen budget is about 60–90 rows in a single panel and 20–35 in a
split. Typical Replies already miss the spread band, so auto `blocks` is
common, auto `cards` (paged deck, still-inline shells) is common in splits
and on medium Replies, and auto `spread` is common on small Main documents
and on Files with a handful of diffs. All three rungs will be lived in.
Both block modes occur routinely.

## 3. The load-bearing UX gap

The two paged-deck rungs can **paint identically** on first landing.

Landing is the newest block, from its top (`sase-19x` D6). If that newest
shell is taller than the viewport — p90 Replies are hundreds of lines, and a
single code shell often is — then:

- `cards` (all blocks inline, scrolled to the newest header)
- `blocks` (only that block's page)

both show the same header, the same first viewport of text, and the same
rail pill. The reader finds out which world they are in only by scrolling
past the end of the shell (next shell versus end of card) or by pressing
`[` (anchor-scroll versus page swap).

That is the defect the indicator has to fix. The dim subtitle `spread` tag
does not touch it: it is absent in both of those rungs, and it is the first
thing dropped even when the deck *is* spread (narrow splits, Files status
lines, goldens that already pin a 160-column terminal so the tag will fit).

A secondary gap: auto-fit can flip under the reader when streaming crosses
the hysteresis band. `ReadingAnchor` keeps the place; the **mode** still
changes with no announcement. A pin is how a reader says "stay here."

## 4. UX principles

These follow from how this TUI already teaches state, and from the analog
that actually matches the 3-rung ladder.

1. **Name the legal rung, not two independent bits.** "Deck paged · card
   spread" teaches a 2×2 whose fourth cell cannot happen. One word
   (`spread` / `cards` / `blocks`) is the state. Help text spells out the
   long form the user used.
2. **Where-am-I lives in the title.** `sase-17d` §3.8 already assigned the
   title that job and the subtitle "what else." Mode is where-am-I. The
   subtitle keeps the deck switcher and Files line counts.
3. **Same pill language as tabs and the rail.** Auto-fit is muted text, like
   an inactive tab. A user pin is `▐cards▌` in the deck accent, like the
   active card and the active block. The reader can see at a glance whether
   the layout will still move on them.
4. **The rail distinguishes the two paged rungs.** Title chip names the
   rung; the rail says how to read it: `page 3/5` means the rail is a pager,
   `all 5` means the rail is a minimap over one scrolling card.
5. **One press changes the picture, or is gated.** Skipping a rung that
   would paint the same (Tools, one-card Main, a card with fewer than two
   blocks) keeps `B` honest. A no-op still needs a reason in the footer
   (the binding is hidden when there is only one meaningful rung).
6. **Printable keys only for new defaults.** Card-blocks already paid for
   this lesson. `B` is delivered through tmux and through kitty's main
   screen.
7. **Transitions reuse `ReadingAnchor`.** `sase-19x` §3.4.9 already restores
   `(card_id, block_id, offset_rows, pinned)` across spread↔paged at both
   levels. The cycle key is one more caller of that path, not a new
   scrolling story.
8. **Keystroke paths stay cheap.** `tui_perf` forbids heavy work on the
   pump. Auto-spread is already bounded by 1.5 screens. A forced `spread`
   of a 14,013-line Reply is the new hazard; see §8.

The closest analog is vim `foldlevel` / macOS Preview's Continuous Scroll
versus Single Page, and PDF page `3/12` appearing only in single-page mode.
Finder's icon/list/column cycle (`Cmd+1/2/3`) is the interaction analog:
one key (or a small family) walks a totally ordered set of views.

## 5. Indicator design

### 5.1 Title chip (source of truth)

Extend `deck_title` with a `view_depth` argument and a `pinned` flag.
Place the chip after the card tabs / `N/M`, still inside the title budget
so compact/micro can keep it.

Full, auto-fit on a two-card Main that auto-paged to blocks:

```
╭─ ◆ MAIN ┃ Context │ Reply  2/2  blocks ─────────────────────────────╮
│  0 --plan ✓ ─ 1 ⋔ --gate ✓ ─ ▐2 --code ▶▌  page 3/5  [ older · newer ] │
│  ─── AGENT (code) ─── 07:23:10 ───                                     │
╰──────────────────────────────────────────── main 2 · files 1 · tools ─╯
```

Full, user-pinned `cards` (paged deck, whole Reply as a chat log):

```
╭─ ◆ MAIN ┃ Context │ Reply  2/2 ▐cards▌ ─────────────────────────────╮
│  0 --plan ✓ ─ 1 ⋔ --gate ✓ ─ ▐2 --code ▶▌  all 5     [ older · newer ] │
│  ─── AGENT (plan) ─── …                                                │
```

Full, user-pinned `spread`:

```
╭─ ◆ MAIN ┃ Context │ Reply  2/2 ▐spread▌ ────────────────────────────╮
│  SASE CONTEXT …                                                        │
│  ━━ ◆ Reply ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
```

Compact keeps the chip (`◆ MAIN ┃ ‹ 2/2 › Reply · blocks`). Micro keeps a
one-letter fallback `S` / `C` / `B` after the deck name (`MAIN 2/2 B`) so
the mode survives a 40-cell split column. The chip is in every tier that
the tabs are; it is dropped only after the title has already fallen to
micro and still does not fit, which is narrower than any layout this TUI
ships goldens for.

Muted versus pill is the auto-versus-pin signal. Do not add a second word
`auto` / `pin` in the title; the style carries it. Help and the palette
can say "fit" explicitly.

### 5.2 Rail suffix

At the widest and full tiers, before the key hint:

| Rung | Suffix |
| --- | --- |
| `blocks` | `page {active}/{count}` in the deck accent |
| `cards` | `all {count}` muted |
| `spread` | rail hidden (phase dividers + title chip suffice) |

Windowed / compact / micro rails already fight for cells; keep `page N/M`
as long as it fits, then rely on the title chip alone. Do not invent a
second pill style for `cards` versus `blocks` — the suffix is enough, and
the pill already means "active block."

### 5.3 Subtitle

Delete the `spread=` argument from `deck_subtitle` and the dim `spread`
tag. The drop-order tests that prefer dropping mode before the switcher
go away with it. Files line status stays.

### 5.4 Footer, help, palette

Footer, conditional on "this panel has two or more distinct rungs":

```
B/⇧B view
```

Help row, Navigation section, next to the card/block motion rows:

```
B / Shift+B    Cycle view (blocks · cards · spread · fit)
```

Palette commands (all Agents-tab, prompt-input gated like the other deck
keys):

| Command | Action |
| --- | --- |
| Cycle deck view | `cycle_deck_view` |
| Cycle deck view reverse | `cycle_deck_view_reverse` |
| Spread view | `set_deck_view` (`spread`) |
| Cards view | `set_deck_view` (`cards`) |
| Blocks view | `set_deck_view` (`blocks`) |
| Fit view | `reset_deck_view` (`fit`) |

No toast. Zoom, header toggle, and jump-panel toggle already rely on
chrome. A toast would fire on every `B` and fight the chip. If a press is
refused (forced spread too large, §8), *that* is a toast.

## 6. Keymap

### 6.1 Defaults

| Action | Default | Why |
| --- | --- | --- |
| `cycle_deck_view` | `B` | Printable; free on Agents; mnemonic for view **b**readth / **b**locks-depth; copy-mode `%B` is unrelated |
| `cycle_deck_view_reverse` | `shift+b` | Same family, both directions, so a 4-slot ring is not a trap |
| `set_deck_view` / `reset_deck_view` | unbound | Palette and help; users who want a dedicated `fit` key bind it |

`P` is the runner-up (`p` already picks a deck, so `P` reads as "page").
Keep it unbound so a later "other-panel" picker letter stays available,
matching capital `M` / `F` / `T`.

Do not bind this inside fold-mode. `z` already means section folds inside
a card. View depth is which card/block **pages** exist. Putting `zs` /
`zp` next to `z1`–`z4` would make two ladders share a prefix.

Do not reuse `[` / `]` with a modifier. `Ctrl+[` is Escape in terminals.

### 6.2 Cycle order

`B` **opens** (less paging, more on one page):

```
blocks  →  cards  →  spread  →  fit  →  blocks
```

`Shift+B` **closes**.

The cursor starts at the **effective** rung, including when policy is
`fit`. Consequences that match real sessions:

- Large session Reply, auto `blocks` (the common case). First `B` goes to
  `cards`: the whole Reply becomes a chat log, Context leaves the page,
  the rail switches from `page 3/5` to `all 5`. That is the middle state
  the user asked for, and it is the most useful first override.
- Second `B` goes to `spread`: Context and Reply share the page.
- Third `B` goes to `fit`: release the pin, hysteresis takes over again,
  chip goes from pill to muted.
- Small two-card Main, auto `spread`. First `B` wraps to `blocks` if the
  Reply has two or more shells, or to `fit` if `blocks` and `cards` would
  paint the same. Wrapping from `spread` onto `fit` is how auto remains
  reachable without a hidden gesture.

`fit` belongs on the ring. Once a pin persists across TUI restarts (§7),
there has to be a one-key way back to auto sitting next to the way in.
Burying `fit` in the palette only would strand a persisted `blocks` pin.

### 6.3 Skipping

The cycle enumerates **distinct paintings** for the focused panel's
current deck and active card:

| Situation | Distinct rungs |
| --- | --- |
| Main, two cards, active card has ≥ 2 blocks | `blocks`, `cards`, `spread`, `fit` |
| Main, two cards, active card has 0–1 blocks | `cards` and `blocks` collapse; ring is `cards`/`spread`/`fit` (label the collapsed rung `cards`) |
| Main, one card (clan Summary, Tools-like) | `spread` and `cards` collapse; if that card has ≥ 2 blocks the ring is `blocks`/`cards`/`fit` |
| Files, two or more text pages, no solo media | `cards`/`spread`/`fit` (`blocks` does not exist) |
| Files with `has_solo` (image/video) | stay paged; `spread` is refused for that subject |
| Tools | binding unavailable |

A pin of `blocks` on Reply survives `Ctrl+K` onto Context by **degrading**
the painting to `cards` while **keeping** the pin. Returning to Reply
restores one-block pages. This is the same stickiness as the preferred
card.

Gating matches card-block keys: Agents tab, prompt input does not own
keys, focused panel has two or more distinct rungs. The press is
in-memory: no file I/O, no Main-source rebuild. It calls the existing
mode-transition path.

### 6.4 Two keys versus one cycle

A pair `toggle_deck_paging` + `toggle_card_paging` looks like it maps onto
"deck and/or card." Costs:

- The card toggle is a silent no-op in `spread` (D3). Silent no-ops on a
  dedicated key fail principle 5.
- Users have to reconstruct the three named states from two bits.
- Two new default keys on an Agents map that is already dense.

The user asked to toggle **through** three states. One cycle plus reverse
plus palette setters is that request. The title chip still shows a single
word that is unambiguously about both levels, because each word encodes
both bits.

## 7. Pin policy, scope, persistence

**Policy versus painting.** `fit` is a policy (run `decide_render_mode` /
`decide_block_mode`). `spread` / `cards` / `blocks` are pins that skip
those functions and feed `RenderMode` in directly. The chip always shows
the **painting**. The pill versus muted style shows the **policy**.

**Grain: per panel.** Split layouts already give each `DeckPanel` its own
render mode, preferred card, and block cursor. A left Main in `blocks`
(triage the Reply) next to a right Files in `spread` (skim diffs) is the
point of splits. A global pin would fight `Ctrl+F`.

**Lifetime: sticky across subjects, persisted across restarts.** A view
depth is a reading posture, like the preferred card and the split ratio.
Store it on each panel snapshot:

```json
{
  "schema_version": 2,
  "panels": [
    {"deck": "main", "preferred_card": "reply", "view_depth": "blocks"}
  ]
}
```

Unknown / missing `view_depth` loads as `fit` (fail open, same as unknown
decks today). Schema v1 files keep working. `fit` is stored as `"fit"` or
omitted; omitting is enough.

Do not persist into `default_config.yml`. The thresholds remain the
auto-fit policy; `B` is a session layout override, next to zoom and
splits.

Do not persist per card. Per-card pins would change deck mode when
`Ctrl+J` moved from Context to Reply, which is the surprise D3 spent
complexity to avoid for `[` / `]`.

Block **cursors** stay ephemeral. A `blocks` pin says "page by shell";
which shell is still the per-subject cursor that lands on newest.

## 8. Performance and forced spread

Auto-spread only renders when the cheap lower bound (and then the exact
measure) says the document fits ~1.5 screens. Forced `spread` on a p90
Reply is a new path: one `VerticalScroll` holding hundreds to thousands
of rows.

Rules from `tui_perf.md` that apply:

- The `B` handler must stay thin and synchronous on the pump. Any
  re-measure that cannot use the existing `(digest, width)` LRU belongs
  in the same `call_after_refresh` / `ReadingAnchor` restore the spread
  transition already uses.
- Do not add a worker, timer, or refresh path. Ride Main fan-out.
- `j`/`k` must not get slower. A pin is not on the row-motion path.

**Safety cap.** If a pin to `spread` would exceed
`max(spread_max_screens, 3.0)` screens by the existing lower bound,
refuse it, stay on `cards`, and toast `too large to spread · B for fit`.
The middle rung still gives the whole Reply without dragging Context and
without laying out 14k lines in one paint. Users who truly want the
unbounded dump have `V` (metadata pager) and `E` (editor).

Add a `B`-cycle case to the sticky-Reply bench fixture `sase-19x` already
required (10 shells, 5,000 lines). Gate: p95 key-to-paint for `B` on a
fitting document stays comparable to `Ctrl+J`; refused huge spreads stay
comparable to a no-op.

## 9. Alternatives considered

### A. Indicator only, no keymap

Cheapest. Fixes the identical-paint bug with the title chip and the rail
suffix. Leaves the reader stuck in auto-fit. Rejected as the *whole*
solution because the request includes the cycle; kept as **phase 1** of
the implementation because the chip is valuable on its own and unblocks
golden inspection.

### B. Subtitle always shows `spread` / `paged` / `paged+blocks`

Smallest diff: stop dropping the tag, add words for the other rungs.
The subtitle is already the overflow dump (Files `1-120 of 693 lines · E
editor`, switcher counts). Mode lost that fight once by design. Moving
it to the title is the actual fix.

### C. Two independent toggles (deck, card)

Maps onto the request's "and/or" wording. Produces a silent no-op on the
card toggle inside a spread deck, spends two default keys, and makes the
user assemble the three named states themselves. See §6.4.

### D. Three dedicated keys, one per rung

Honest, and a poor Agents-tab citizen. Palette setters already give
direct jumps. Defaults should be the cycle pair.

### E. 3-slot ring with no `fit`

Matches the request's list exactly. After persistence, the only way back
to hysteresis is a buried palette command. Once someone pins `blocks` for
a week of triage they cannot recover auto without reading help. The 4th
slot is the release valve.

### F. First press pins in place, second press advances

Avoids a surprising first motion. Also makes the first `B` look dead
unless the muted-to-pill change is unmistakable, and it adds a phantom
press to every change. Starting from the effective rung and moving on
the first press is simpler. The chip still flips muted → pill on that
same press.

### G. Fold-mode `zs` / `zp` / `z1`–`z3`

Reuses an existing "how open is this" prefix. Section folds and page
depth would share `z` and fight for `z1`–`z4`. Category error.

### H. Config knobs only (`spread_max_screens: 0` etc.)

Already exists and already fails as UX: it is global, requires editing
config, and cannot express the middle rung without also forcing every
Files deck to page.

## 10. Implementation sketch

Presentation-only, after `sase-19x.9` removes `card_blocks`. New logic
goes in new modules so `panel.py` / `main_view.py` stay mixin-thin.

| Piece | Where |
| --- | --- |
| `ViewDepth` enum (`fit`, `spread`, `cards`, `blocks`) plus `effective_view_depth(...)` and `cycle_view_depth(current, direction, legal)` | `widgets/decks/view_depth.py` (pure, next to `block_model.py`) |
| Legal-rung helper from document + active card + deck id | same module; table-driven tests |
| Pin on `DeckPanelState.view_depth` | `widgets/decks/model.py`; persist in `agent_deck_persistence.py` schema v2 |
| Apply pin ahead of `_decide_*_mode` | `panel_spread.py` / `panel_blocks.py` |
| Title chip + subtitle tag removal | `titles.py`, `panel_chrome.py` |
| Rail suffix | `block_rail.py` |
| Actions | `actions/agents/_panel_detail.py` next to `action_next_card_block`; host method on `AgentDetail` |
| Keymap | `default_config.yml` `app.cycle_deck_view` / `cycle_deck_view_reverse`; `keymaps/app_keymaps.py`; `metadata.py`; help `agents_bindings.py`; footer `_keybinding_bindings_agents.py`; palette `_app_metadata_nav.py` + `_availability_agents.py`; `bindings.py` fallbacks |
| Docs | `docs/ace.md` next to the spread paragraph; `docs/configuration.md` only if a cap is configured (prefer a constant) |
| Glossary | land-agent follow-up: extend the Agent Data Card strand with the three rung names; do not edit memory from this research |

`effective_view_depth` is the one function every chrome site calls. Paint
from the effective rung; style from `pin != fit`.

Verification:

- Pure tables for `cycle_view_depth` (wrap, skip collapsed rungs, degrade
  `blocks` on a blockless card, Files, Tools).
- Pilot: pin survives `j`/`k`; split panels pin independently; `ReadingAnchor`
  keeps the shell across `blocks ↔ cards ↔ spread`; first `B` on an auto
  `blocks` Reply shows the whole card; `Shift+B` returns; fourth `B` from
  `spread` returns to `fit` and hysteresis can page again.
- PNG goldens: auto `blocks` (muted chip + `page N/M`), pinned `cards`
  (pill + `all N`), pinned `spread` (pill, no rail), compact title in a
  left-right split, Files `spread` chip, Tools with no chip.
- Live `sase screenshot` inspection of a 5-shell session in all four ring
  slots.
- `just check`, plus the `B` bench case in §8.

## 11. Risks

- **Forced spread of huge Replies** — refused by the cap in §8; `V`/`E`
  remain the unbounded readers.
- **Title width in splits** — compact/micro keep a chip or a letter;
  goldens must include a 80×24 left-right split, not only 160-col.
- **Persisted pin surprises on small nodes** — a `blocks` pin on a clan
  Summary degrades; chip still reads `cards` or `spread` according to
  paint. Revisit if users report the pill "lying."
- **`B` muscle memory** — unused on Agents today; copy-mode `%B` is
  documented in help under copy, not Navigation.
- **Flag timing** — do not land against `card_blocks` Off. Wait for
  `sase-19x.9`. The chip can go in as soon as both modes exist without a
  flag; the key can share that change or follow by a day.
- **Golden churn** — every Agents-tab deck PNG that shows a title will
  pick up the chip, including auto-fit muted `spread`/`blocks`. Budget
  that into the same work as the feature, like `sase-19x.9`'s goldens.

## 12. Open questions for the user

1. **Cycle order.** Opening (`blocks → cards → spread → fit`) is the
   recommendation, because the common auto state is `blocks` and the
   first `B` then yields the whole Reply. Closing-first
   (`spread → cards → blocks → fit`) would make the first press on a
   large Reply force a full-document spread (or hit the cap).
2. **Safety cap.** Refuse `spread` above 3 screens, versus always
   honoring the pin and accepting a hitch. Recommendation: refuse.
3. **Persist the pin.** Recommendation: yes, schema v2, fail open to
   `fit`. Session-only is simpler and loses the triage posture on
   restart.
4. **Default key `B` versus `P`.** `B` recommended; `P` is the
   alternative if `B` is wanted for something else.

If those four are accepted as stated, the implementation in §10 is
ready to become a small epic (indicator + key + persistence, one phase
each, or one medium phase if cutover is already green).

## 13. Sources

- Epic `sase-19x` and plan `plan:202609/agent_data_card_blocks.md`
  (binding decisions D1–D8, mode matrix §3.3, visual design §3.7, rail
  mocks).
- Epic `sase-17d` plan `plan:202609/agents_tab_decks_and_cards.md` §3.7
  (algorithm), §3.8 (visual language: title = where am I, subtitle =
  what else, dim `spread` tag).
- Shipped code: `widgets/decks/titles.py`, `panel_chrome.py`,
  `render_mode.py`, `block_model.py`, `block_rail.py`, `panel_blocks.py`,
  `panel_spread.py`, `agent_decks_settings.py`,
  `models/agent_deck_persistence.py`,
  `widgets/_keybinding_bindings_agents.py`,
  `default_config.yml` keymap, `docs/ace.md` decks section.
- Prior research `research:202609/agent_data_card_blocks/agent_data_card_blocks.md`
  (key delivery, session size distribution, D3 invariant).
- `sase/memory/tui_perf.md` (keystroke path, pump, no new refresh).
- Glossary strands Agent Data Card, Agent Data Deck, Deck Panel.
- Tests that encode today's indicator policy:
  `tests/ace/tui/widgets/decks/test_deck_spread_pure.py` (spread tag
  dropped first),
  `tests/ace/tui/widgets/decks/test_deck_block_rail.py` (rail hidden in
  spread decks, shown in both block modes),
  `tests/ace/tui/visual/test_ace_png_snapshots_agents_decks.py` (wide
  terminal so the subtitle tag will fit).
