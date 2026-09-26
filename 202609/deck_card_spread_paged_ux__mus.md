# Deck / card spread-vs-paged UX: indicator + view-mode toggle

Research for: once card blocks are fully implemented (epic `sase-19x`, "Agent data
card blocks — per-shell blocks for the session Reply card"), (1) make it clear
whether the spread or paged view is enabled for a deck and/or card, and (2) add
keymap(s) to toggle through the 3 states: fully spread, paged deck + spread card,
paged deck + paged card.

## 1. Current state (as implemented by sase-19x phases 1–7)

### 1.1 The two independent auto decisions

There are two orthogonal spread/paged decisions, each with its own budget,
hysteresis, and config knob:

- **Deck level** (`DeckPanelSpreadMixin`, `src/sase/ace/tui/widgets/decks/panel_spread.py`,
  pure logic in `render_mode.py:decide_render_mode`): a multi-card Main deck renders
  SPREAD (every card on one scrollable page, separated by titled rules in
  `separators.py`) when measured rows fit within
  `ace.agent_decks.spread_max_screens` (default 1.5) viewport heights, else PAGED
  (one card at a time, `ctrl+j` / `ctrl+k` to cycle). Single-card decks always
  spread; `0` screens forces paged; ±10% hysteresis (`SPREAD_HYSTERESIS`)
  prevents flicker on resize/streaming.
- **Card/block level** (`DeckPanelBlocksMixin` in `panel_blocks.py`, pure logic in
  `block_model.py:decide_block_mode` — a thin wrapper over the same
  `decide_render_mode`): a Reply card shown alone in a *paged* deck renders its
  per-shell blocks SPREAD (all inline) or PAGED (one block per page,
  `[` / `]` to step, newest-landing, follow/keep-by-id cursors) against
  `ace.agent_decks.block_spread_max_screens` (default 1.5). Fewer than two blocks
  always spreads; `0` forces one-block-per-page.

In a **spread deck**, blocks always render inline (deck-spread path with
sticky-Reply chat-log landing, scroll-derived block cursor, anchor-motion
`[` / `]`); there is no "spread deck + paged card" combination. So the reachable
effective states are exactly the 3 the request names:

1. **Fully spread** — deck SPREAD, blocks inline.
2. **Paged deck + spread card** — one card visible, all its blocks inline.
3. **Paged deck + paged card** — one card visible, one block visible.

Both decisions are currently **fully automatic** (content size + viewport +
hysteresis). There is no manual override, no pinned mode, and no key to force a
state. Both config knobs are global (all panels, all decks); there is no
per-panel or per-deck override.

### 1.2 What the user can see today

| Surface | Shows | Gap |
|---|---|---|
| Border subtitle (`titles.py:deck_subtitle`) | dim `spread` tag when the deck is spread; nothing when paged | Paged is the *absence* of a tag (easy to miss); **no block-mode signal at all** — states 2 and 3 are visually indistinguishable in chrome |
| Border title (`titles.py:deck_title`) | card tabs + `i/n` position counter | Same rendering in states 2 and 3; position counter reads card position, not block position |
| Footer (`_keybinding_bindings_agents.py`) | `ctrl+j/ctrl+k cards` when >1 card; `[`/`]` `blocks` when `card_blocks_navigable` | `blocks` hint appears in *both* states 2 and 3? No — `card_blocks_navigable` is true only when the paged card actually pages (≥2 blocks + block-paged mode). In state 2 with ≥2 blocks the `[`/`]` keys still anchor-scroll within the spread card (phase 6 anchor-motion), so the footer can hide the only hint that blocks exist |
| Block rail (phase 8, in progress) | one-row timeline docked under the Main panel top border: roster numbers, active-block pill, arrival dots, click-to-select | Shows *position within blocks*, not the *mode*; only exists for the Reply card; collapsed/unfocused tiers may hide it |
| Help modal (`help_modal/agents_bindings.py`) | rows for card cycling and block stepping | No view-mode rows (nothing to document yet) |
| Toasts/notifies | none on mode change | Auto transitions (e.g. streaming past the budget flips block-spread → block-paged mid-read) happen **silently**, which is the most disorienting behavior |

The core finding: **state 1 is labeled (weakly), states 2 vs 3 are unlabeled, and
all transitions are silent and automatic.** Any fix must label all three states
explicitly (never by absence) and announce transitions the user didn't initiate.

### 1.3 Keymap landscape (constraints on a new binding)

`src/sase/default_config.yml` (§`app`, ~line 643+) is the single source of truth;
a new action needs entries in `AppKeymaps` (`keymaps/app_keymaps.py`), `bindings.py`,
`keymaps/metadata.py`, `keymaps/registry.py` (duplicate/collision sets),
`_app_action_availability.py` gating, footer, help, and palette metadata — the
phase-7 (`sase-19x.7`) checklist is the template. Bare single-letter keys on the
Agents tab are nearly exhausted (`v/V`, `s/S`, `d/D`, `o/O`, `r/R`, `z/Z`,
`=`/`-`, `.`, `;`, `:` all taken). Precedent for sharing a key across tabs via
tab-availability disambiguation exists (`[`/`]` shared with Artifacts subtab
cycling; `D` shared with Artifacts brief; `p` shared with Artifacts project
picker), so an Agents-only binding may reuse an Artifacts/Services-only key.
`B` (bare shift+b) appears unbound at app level, but this must be verified
against the registry's collision sets at implementation time; safe fallbacks are
a leader-prefix sequence or an explicitly-picked key via the normal keymap
review.

## 2. UX options considered

### A. Indicator only, no toggle (auto stays sovereign)

Cheapest; fixes "what am I looking at?" but not "I want the other view."
Rejected as insufficient — the request explicitly wants a toggle, and auto-mode
mis-guesses real cases (e.g. a 3-shell Reply just over budget forces paging on a
user who wants the whole answer inline, or vice versa).

### B. Two separate toggles (deck mode × card mode)

Two binary pins = 4 combinations, one of which (spread deck + paged card) does
not exist in the renderer and would have to be either forbidden (confusing) or
built (paging one card's blocks inside a free-scrolling spread deck — genuinely
weird UX: two nested scroll axes plus a pager). Two keys, a 2×2 matrix to
communicate, and an impossible corner. Rejected.

### C. One 3-state cycle key (+ optional reverse) over the reachable states, with an Auto home position (RECOMMENDED)

One action, `cycle_deck_view`, advancing one position per press through the three
*explicit* states; a fourth press returns to **Auto** (the current behavior).
Auto is the default and the home position, so the key is purely additive — users
who never touch it see zero behavior change.

Ordering (forward): `Auto → Spread → Paged+Spread → Paged+Paged → Auto…`
This order is deliberate: from Auto, one press gives the maximally-open view
(spread), matching the "show me everything" intent that most often motivates
overriding the auto-guess; subsequent presses narrow progressively.

### D. Cycle with no Auto return (toggle pins forever until config change)

Same as C but sticky without exit. Rejected: users who pin spread on a huge
session then open a 50-shell monster get a frozen-feeling multi-thousand-line
scroll with no obvious way back. Auto-as-home is the escape hatch and makes the
feature self-documenting via the toast ("view: auto").

### E. Config-only mode pins (no keymap)

Puts the choice in `ace.agent_decks` (e.g. `deck_view: auto|spread|paged`). No
discoverability, no per-moment control, Vim-users expect a keystroke for view
toggles. Rejected as the *only* mechanism; a config default for the *starting*
position is a fine optional extra (see §4).

## 3. Detailed design of the recommended solution (option C)

### 3.1 Semantics

- **Scope: per deck panel, Main deck only, runtime-ephemeral.** Each `DeckPanel`
  already keeps per-panel `_render_mode` / `_block_mode`; add a per-panel
  `_view_override: None | Literal["spread","paged_spread","paged_paged"]`
  (`None` = Auto). Operates on the *focused* panel, like the other deck actions.
  The Files deck is out of scope (its spread/paged stays fully auto).
- **Override beats measurement, nothing else changes.** When set, skip
  `_decide_main_mode` / `_decide_block_mode` for that panel's Main deck and use
  the pinned modes. Keep everything downstream untouched: newest-landing,
  follow/keep-by-id cursors, `[`/`]` stepping, hysteresis-free explicit render,
  `ReadingAnchor` transitions, rail, footer gating. This minimizes regression
  surface — the override is a ~10-line branch at the two decision call sites.
- **Persistence across subjects, cleared only by the user.** The pin survives
  subject changes and resizes within the session (predictability beats
  cleverness; auto-resuming on new subjects would make the key feel broken for
  the "always show me paged blocks" user). It is *not* persisted to disk in v1
  (matches zoom/isolate runtime-state precedent; persistence can come later via
  the existing `_deck_persistence` path if users ask).
- **Degenerate inputs stay sane:** 1-card deck + "paged deck" pin = trivially
  paged (harmless; indicator still honest); single-block card + "paged card" pin
  = renders spread (fewer than two blocks always spreads per `decide_block_mode`)
  with the indicator showing the *effective* mode, not the requested one (see
  §3.2 — this honesty rule is load-bearing).

### 3.2 Indicator (the "make it clear" half)

Rule: **every state is positively labeled; effective mode, not requested mode;
reuse the existing tier-drop system for narrow panels.**

1. **Subtitle tags (primary).** Extend `deck_subtitle`'s `spread: bool` param
   into a deck-mode + block-mode pair. Proposed vocabulary, dim-styled like the
   current `spread` tag:
   - state 1: `spread`
   - state 2: `paged · blocks spread` (deck paged; card's blocks inline)
   - state 3: `paged · block i/n` (deck paged; block pager with live position —
     position already tracked by the cursor, and duplicating the rail's pill
     here is *good*: the rail can be collapsed/hidden while the subtitle is
     always visible)
   - When the active card has <2 blocks, no block tag at all (nothing to page).
   - When a manual pin is active, prefix a marker, e.g. `spread ●` vs auto
     `spread` — or a `manual`/`auto` token. This answers "is this the auto-guess
     or did I pin this?" without a second lookup. Exact glyph subject to the
     font check noted in phase-8's pill-caps follow-up; fall back to ASCII
     (`[M]`/`[A]` or `manual`/`auto` words) if the pill/dot renders poorly.
   - Tier-drop order (widest first): full tags + switcher counts → drop block
     position → drop manual marker → drop tags (current behavior) → existing
     truncation. Narrow panels degrade to today's rendering, never worse.
2. **Toast on every change** (toggle press *and* silent auto transitions while
   in Auto? — no: toasts on auto-flip during streaming would spam; toast on
   toggle presses and on transitions *away* from a pinned mode only). Keep the
   streaming path quiet; the persistent subtitle tag is its indicator.
3. **Footer + help + palette.** Add the cycle binding to the Agents footer
   whenever a Main deck panel is focused (always-visible = discoverable, unlike
   the conditional `cards`/`blocks` rows), one help-modal row
   ("Cycle deck/card view: auto / spread / paged…"), and palette metadata
   following the phase-7 checklist. Consider also showing the current effective
   state *in* the footer label (footer labels already interpolate counts, e.g.
   `cleanup (3 done)`), e.g. `view: paged·2/5` — cheap and highly visible.
4. **Rail (phase 8) stays position, not mode.** Optionally dim the rail's
   non-active blocks further in paged mode — skip in v1; subtitle + footer carry
   the mode.

### 3.3 Keymap(s)

- **One new app action: `cycle_deck_view`** (forward), default key TBD at
  implementation from the collision audit; candidates in order: bare `B`
  (appears free; mnemonic: "view **B**oards"? weak — better mnemonic story:
  pair it in help text as "deck view"), else an Artifacts-disjoint shared key,
  else a leader sequence. **One reverse action `cycle_deck_view_reverse`,
  default `unbound`** (parity with `cycle_grouping_mode`/`O` precedent is nice,
  but a 3-cycle rarely needs reverse; leave it available for remapping).
- **Gating:** available when the Agents tab is active and the focused panel
  shows Main — no card-count or block-count precondition (pressing it on a
  single-block card still pins the deck dimension and toasts honestly).
- **Full pipeline per phase-7 checklist:** `AppKeymaps` field →
  `default_config.yml` entry + comment → JSON schema → `bindings.py` →
  `keymaps/metadata.py` → `registry.py` collision sets →
  `_app_action_availability.py` → footer row → help row → palette
  metadata/availability → deck-search exit keys if applicable → parity tests
  (`test_deck_card_block_keys.py` is the model) → user docs (phase 10 owns docs;
  coordinate).

### 3.4 What NOT to build (v1 non-goals)

- No Files-deck override; no spread-deck+paged-card combo; no persisted pins;
  no per-deck config knob; no auto-transition toasts; no rail redesign.

## 4. Implementation sketch (for the implementer)

1. `model.py`: add `ViewOverride` (`NONE/SPREAD/PAGED_SPREAD/PAGED_PAGED`) or a
   simple `Literal`; pure `resolve_view_modes(override, card)` helper returning
   `(RenderMode deck, RenderMode|None block)` — unit-testable with no Textual.
2. `panel_spread.py::_decide_main_mode` + `panel_blocks.py::_decide_block_mode`:
   early-return the pinned mode when `_view_override` is set (record key so
   redecision scheduling stays consistent).
3. Action `action_cycle_deck_view` on the Agents detail mixin (next to
   `action_next_card_block` in `_panel_detail.py`): advance override on the
   focused `DeckPanel`, call `show_main_document`-equivalent re-show preserving
   `ReadingAnchor`, `refresh_chrome()`, toast `view: <state> [(auto)]`.
4. `titles.py`: generalize `spread: bool` → view-state param; add tag builders +
   tier-drop entries; width-budget tests in the existing title test file.
5. Footer/help/palette/registry/schema/config entries per §3.3; keymap parity
   tests; golden screenshot(s) with the new tags (coordinate with phase 9's
   golden/screenshotting work).
6. Optional: `ace.agent_decks.deck_view_default: auto|spread|…` config for the
   starting position — trivial once the override field exists; include only if
   cheap.

## 5. Recommendation

**Implement option C: one forward-cycling `cycle_deck_view` key (Auto → Spread →
Paged+Spread → Paged+Paged → Auto), per-panel ephemeral pins that bypass only
the two auto decisions, with positively-labeled effective-mode tags in the
border subtitle (deck + block position + manual marker), the state echoed in the
footer label, a toast on toggle, and the full phase-7 keymap pipeline
(config → bindings → gating → footer → help → palette → tests → docs).**
It satisfies both halves of the request with the smallest behavior delta (one
branch at two call sites, additive-only for non-users), avoids the nonexistent
fourth combo that kills the two-toggle design, and reuses every existing UX
surface (subtitle tiers, footer interpolation, toast, rail) instead of inventing
new chrome. Estimated size: small–medium (one phase), ideally sequenced after
phase 8 (rail) and alongside phase 9 (goldens) so screenshots cover the new
tags.
