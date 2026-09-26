# Spread vs paged view: indicator and toggle after card blocks

- **Researcher:** grk (`research.f.grk`)
- **Date:** 2026-09-26
- **Question:** After card blocks land, how should the Agents-tab deck panel make spread vs paged obvious at both the deck and the card, and how should a keymap walk the three legal combinations?
- **Depends on:** epic `sase-19x` (card blocks; phases .8–.10 still in progress) finishing first. This is follow-up UX, not a new phase of `sase-19x`.

## Recommended solution

Keep the automatic 1.5-screen thresholds. Add a **per-panel pin** that selects among the three legal views, a **two-level subtitle indicator** that names deck mode and card/block mode in established words, and **one first-class key, `P`**, that cycles those three views (plus auto, so the pin can be released).

| View | What fills the panel | Deck mode | Card/block mode | Rail (after `sase-19x.8`) |
| --- | --- | --- | --- | --- |
| **spread** | Every card, blocks inline | spread | spread (forced by D3) | hidden |
| **card** | One card, all of its blocks | paged | spread | shown when the card has ≥ 2 blocks |
| **block** | One card, one card block | paged | paged | shown when the card has ≥ 2 blocks |
| **auto** | Whichever of the three the thresholds pick | decided | decided | follows the effective view |

Default pin is **auto**. `P` walks `spread → card → block → auto → spread`, skipping a stop the current deck cannot honor (Files has no blocks; Tools is a single card). The existing `decide_render_mode` / `decide_block_mode` path stays in charge; the pin only substitutes the two `*_max_screens` values it already reads. `ReadingAnchor` already restores the current card, block, and offset across those flips.

Do this as a new epic after `sase-19x` closes. Presentation-only, no `sase-core` change.

---

## 1. What is already true

### 1.1 Two independent auto-decisions, three legal combinations

Epic `sase-17d.8` (`plan:202609/deck_spread_mode.md`) made a multi-card deck **spread** when its cards fit `ace.agent_decks.spread_max_screens` (default 1.5 viewport heights, `0` = always paged) and **paged** otherwise, with ±10% hysteresis. Epic `sase-19x` (`plan:202609/agent_data_card_blocks.md`) copied that pattern one level down: a card shown *alone* spreads its card blocks when they fit `ace.agent_decks.block_spread_max_screens` (also 1.5 / `0`).

Binding decision **D3**, accepted with the card-blocks research, is load-bearing:

> Only a card shown alone pages its blocks. A spread deck always spreads its blocks.

That is why the user listed **three** states, not four. Spread-deck + paged-card is illegal: block navigation must never flip the deck's mode, and a spread Main deck with a paged Reply inside it would mix two scroll metaphors on one `VerticalScroll`.

The matrix already in `sase-19x` §3.3:

| Deck mode | Card with ≥ 2 blocks | Block mode | Rail |
| --- | --- | --- | --- |
| spread | every card on one page | always inline | hidden (phase dividers suffice) |
| paged | that card alone | spread or paged by `block_spread_max_screens` | shown in **both** block modes |
| paged | < 2 blocks | n/a | hidden |

Code: `RenderMode` in `widgets/decks/model.py`, `decide_render_mode` in `render_mode.py`, `decide_block_mode` in `block_model.py` (thin wrapper), per-panel `_render_mode` in `panel_spread.py`, per-panel `_block_mode` in `panel_blocks.py`. Partial documents never decide a mode. Image/video file pages still force the Files deck paged (`has_solo_card`).

### 1.2 The current “you are in spread” cue is weak, and card/block mode has none

`deck_subtitle()` (`widgets/decks/titles.py`) paints a dim `spread` word between the Files line-count status and the `main · files · tools` switcher. Tests in `test_deck_titles.py` / `test_deck_spread_pure.py` lock in the drop order: **the spread tag is the first thing thrown away when the subtitle is tight**. Paged is unmarked. Block-spread vs block-paged is not named anywhere.

Chrome today:

- **Title strip** (`deck_title`): `◆ MAIN ┃ Context │ Reply  2/2`. The reverse-bold tab and `N/M` tell you *which card is active*. In a paged deck that is a decent “you are looking at one card” cue. In spread the same strip still exists (the tab follows scroll); the extra cue is the `━━ ◆ Reply ━━` separators in the body.
- **Subtitle**: dim `spread` or nothing.
- **Block rail** (`sase-19x.8`, still in progress): shown for a paged Main deck on a navigable card, in **both** block modes, by design (D4: the rail must not pop in and out as streaming crosses the band). The rail names the active *block*. It does not name the *mode*.
- **Footer**: `Ctrl+J/K` “cards” when `deck_card_count > 1`; `[/]` “blocks” when `card_blocks_navigable`. Conditional, which is correct (`src/sase/ace/CLAUDE.md`). Neither entry says spread vs paged.

So a reader can confuse:

1. A paged two-card Main that opened on Context with “this agent has no Reply”.
2. A block-paged Reply (one phase divider, rail present) with a block-spread Reply (every shell, rail present). The rail is the same object in both.
3. Auto paging because the session is huge with “this is just how decks look”.
4. Two split panels on different modes with no reason spelled out.

The original decks research (`research:202609/agents_tab_decks_and_cards/agents_tab_decks_and_cards.md` §1.2) explicitly deferred a manual override: *“Config `0` means always paged. No per-deck override until someone asks (`corpus-before-mechanism`).”* This request is that ask, now at two levels.

### 1.3 Transitions and perf are already solved if the toggle reuses them

`panel_transitions.py` captures a hierarchical `ReadingAnchor(card_id, block_id, offset_rows, pinned)` and restores the most specific target that survives. Spread ↔ paged at either level already keeps the reader’s place. A user toggle that only changes the two screen budgets, then calls the same refresh, inherits that for free.

j/k must stay under 16 ms p95 (`tui_perf.md`, `sase-19x` cutover). Block-paging exists because p90 session Replies are ~738 raw lines and the max in the card-blocks corpus was ~14,013. A pin that *forces* fully-spread on those sessions would undo the epic. The pin therefore has to keep a safety ceiling (below).

Keystroke path: in-memory, no I/O, same as `[`/`]` (`sase-19x` §3.6).

### 1.4 The Agents keymap is dense; `P` is free; `S` is Patch-only

Every lowercase letter on the Agents tab is taken. `+` / `-` / `_` / `=` are custom-agent, fold collapse, and isolate-panels. `Z` is **panel zoom** (maximize the focused deck in place). `z` is fold-mode. `[`/`]` are card blocks vs Artifacts sub-tabs. `{`/`}` grow the deck panel. `Ctrl+J/K` are cards. `Ctrl+N/P` are decks. `p` is the deck picker.

Two capitals are unused as Agents app actions:

- **`P`** — no Agents owner. `p` is already `pick_deck`.
- **`S`** — bound to `bulk_change_status`, which `_app_action_availability.py` rejects unless the tab is Artifacts / Patches. Pressing `S` on Agents today is a no-op.

`Ctrl+Shift+…` still collapses to `Ctrl+…` on the user’s tmux 3.5a + kitty chain (card-blocks research §1.4; D1). Do not put this feature on a shifted-ctrl chord.

---

## 2. What the three states are for

They are a **zoom of what one panel is about**, not two independent checkboxes.

```
spread  →  the whole deck
card    →  one card (Context, or the full Reply with every shell)
block   →  one card block (one sase shell)
```

That matches how people already move: `Ctrl+N/P` choose a deck, `Ctrl+J/K` choose a card, `[`/`]` choose a block. The new control chooses **how many of those levels share the viewport**.

Typical jobs:

| Job | Wanted view |
| --- | --- |
| Triage sessions with sticky Reply (`j`/`k` lands on the newest shell) | **block**, even when the Reply would have spread |
| Read one Reply as a chat log (newest at the bottom, every shell visible) | **card** |
| See Context beside Reply, or several small file pages at once | **spread** |
| Let the panel decide as content and split geometry change | **auto** |

Auto remains the right default. Median sessions sit on the 1.5-screen band (card-blocks research §1.3); hysteresis exists specifically so streaming does not flip the layout under the reader. Replacing auto with a purely manual control would make short sessions require a keypress to see everything and long sessions unusably spread. The toggle is for when auto is *wrong for the current intent*.

---

## 3. Indicator

### 3.1 Put it in the subtitle, in established words, and stop dropping it first

The subtitle already owns “how this panel is behaving” (the dim `spread` tag, the deck switcher, Files line counts). The title owns identity (which deck, which card). The rail owns the session timeline. Keep those jobs apart.

**Wide tier** — two bits, nouns included:

```
deck spread                         main 2 · files 1 · tools 109
deck paged · card spread            main 2 · files 1 · tools 109
deck paged · card paged             main 2 · files 1 · tools 109
```

When the deck is spread, omit the card bit: D3 makes `card spread` redundant, and printing it would suggest a fourth state.

When the active card has no blocks (Context, clan Summary, Files pages, Tools), omit the card bit even in a paged deck: `deck paged` is the whole story.

When the pin is **not** auto, mark it so the reader can tell a choice from a threshold:

```
deck paged · card paged *           main 2 · files 1 · tools 109
```

`*` is a pin, not a new word. Same cell budget as today.

**Mid tier** — short names of the effective view, still always present:

```
spread    main · files · tools
card      main · files · tools
block     main · files · tools
card*     main · files · tools      ← pinned
```

**Tight tier** — the short name only (`spread` / `card` / `block`, with `*` if pinned). Drop the switcher before dropping the view word.

This **inverts** today’s drop order (`titles.py` currently prefers the switcher over the spread tag). If the point of the work is “make the mode obvious”, the mode word is the last status to go.

Style: inactive bits dim (`#888888`, same as inactive card tabs); the effective view in the focused panel uses the deck accent; unfocused panels dim the whole subtitle as they already dim the title. No new separator glyph. No extra widget row.

### 3.2 Why not a 3-cell segmented control, a title badge, or a second rail

A `spread │ card │ block` pill strip (reverse-bold on the active cell, matching card tabs) is attractive and maps 1:1 onto the cycle. It is a legend the user has to learn: `card` means “paged deck, spread card”. The two-bit form answers the question in the words the user used. Use the short names only when width forces it.

A title-strip badge (`◆ MAIN spread ┃ …`) fights the card tabs and the `N/M` counter. Title is already the densest chrome on the panel.

A dedicated widget row is clickable (the block rail is the precedent) and costs **one row in every mode**, including fully spread, where the rail is hidden on purpose. Height is already spoken for by the header, the jump panel, and the coming rail. Border `border_subtitle` is not a widget, so clicks there are not a reliable affordance in Textual. **Do not add a row for this.** Key + palette cover input; the subtitle covers output.

Do not overload the block rail with mode text. The rail is a timeline. It is hidden in spread, which is exactly when a mode cue is still needed.

### 3.3 Content already helps; the subtitle names the *policy*

Paged vs spread is also visible in the body (one card vs separators; one phase divider vs many). The subtitle’s job is to name **why**. After a pin, that distinction matters: `deck paged *` means “I asked for this”, `deck paged` means “the Reply is tall”. The rail’s presence already means “this paged card has blocks”; the new `card spread` / `card paged` bit is what the rail cannot say.

---

## 4. Keymaps

### 4.1 One cycle key, default `P`

**Action:** `cycle_deck_view`
**Default:** `"P"`
**Help (≤ 32 chars):** `Cycle spread / card / block`
**Footer (conditional):** `P` `view` — only when the focused panel has at least two legal stops (same rule as `Ctrl+J/K` “cards” and `[/]` “blocks”).
**Palette:** the cycle, plus four direct commands (`Spread all cards`, `One card (blocks spread)`, `One block`, `Auto spread/paged`) so a reader can jump without walking past a state. Search tokens: `spread`, `paged`, `card`, `block`, `view`, `deck`.

Why `P`:

- Free on Agents. No `_CONTEXTUAL_APP_DUPLICATES` pair required.
- Families with `p` (pick *which* deck) the way `o`/`O` family grouping. `P` picks *how* the current deck is shown.
- Printable, so tmux delivers it. Shift of `p` is a real distinct key, unlike `Ctrl+Shift+J`.
- `S` (mnemonic “spread”) is the runner-up: it is a no-op on Agents today because `bulk_change_status` is Patches-only, and sharing it would match the `[`/`]` / `{`/`}` pattern. `S` names only one of the three stops, and it is already a Patch verb. Prefer `P`. Offer `S` in the plan as an allowed remap, not the default.

**Second action:** `reset_deck_view` (palette; default **unbound**). Needed so a user who remaps `P` off the 4-stop cycle can still return to auto. Fold-mode `zP` is a reasonable optional default if a two-key alias is wanted; `z` already means “how this panel is shown” (folds, and `Z` is panel zoom). Do not steal `z1`/`z2`/`z3` — those are session/clan/tribe fold levels.

Do not add a picker. The old Agents `p` view picker was removed on purpose during `sase-17d`. Three views plus auto are a cycle, not a modal.

### 4.2 Cycle semantics

Order, coarsest to finest, then auto:

```
spread → card → block → auto → spread
```

Skip a stop the panel cannot honor:

- **Main, Reply has ≥ 2 blocks, two+ cards:** all four stops.
- **Main, two cards, no blocks:** skip `block` (`spread → card → auto`).
- **Files, two+ pages:** skip `block` (a file page has no card blocks). `card` means one file page.
- **Tools / single Summary card:** `cycle_deck_view` unavailable. Footer hides `P`. Palette entries disabled via the same `deck_view_cyclable` cache that `[`/`]` uses (`card_blocks_navigable` is the template: O(1), recomputed when document / deck / mode / pin changes, then `_refresh_agent_footer_bindings_only`).

From **auto**, the first `P` pins the *next* stop after the current *effective* view (wrap from `block` to `spread`). That makes the common “auto gave me card, I want one shell” case a single keypress.

Each stop **pins**. Auto **clears** the pin and restores the configured `spread_max_screens` / `block_spread_max_screens`.

Do not ship a reverse cycle by default. Four stops means any view is at most three presses away. `cycle_deck_view_reverse` can exist unbound for people who want it.

Gating (copy the card-block pipeline: `app_keymaps.py`, `default_config.yml`, `metadata.py`, `bindings.py`, `_app_action_availability.py`, palette, help, footer, `deck_structural_exit_keys`):

- Tab is Agents
- Prompt input does not own keys
- Focused panel’s `deck_view_cyclable` is true
- Non-priority binding, so text inputs keep `P`

### 4.3 Two independent toggles are the wrong shape

A `toggle_deck_spread` plus `toggle_card_spread` pair maps onto the two config keys, and onto the user’s “and/or” wording. It also creates a fourth combination the product has already banned, and it needs a policy for “I toggled card-paged while the deck is spread.” Either the card toggle is dead until the deck is paged (hidden mode), or it secretly pages the deck first (the key does two things). A single cycle of the *legal* views matches the request (“toggle through the 3 states”) and needs one key in a full keymap.

Zoom-in / zoom-out (`zr`/`zm`, Photos pinch, Lightroom grid ↔ loupe) is the better *metaphor* and a worse *binding*: `+`/`-` are taken, and two new letters are not available. The 4-stop cycle is the zoom metaphor folded onto one key.

---

## 5. Pin mechanics

### 5.1 The pin only rewrites the two budgets the deciders already take

Keep `decide_render_mode` and `decide_block_mode`. Do not add a third renderer. A pin is a pair of substitute floats:

| Pin | `spread_max_screens` | `block_spread_max_screens` |
| --- | --- | --- |
| auto | config (1.5) | config (1.5) |
| spread | `FORCE_SPREAD_SCREENS` (internal, 8.0) | same (D3: if the deck spreads, blocks are inline) |
| card | `0` (deck always paged) | `FORCE_SPREAD_SCREENS` |
| block | `0` | `0` (card always paged) |

`FORCE_SPREAD_SCREENS = 8.0` is a safety ceiling, same kind of internal constant as `SPREAD_HYSTERESIS = 0.10`. Solo image/video pages still force Files paged. A 14k-line Reply under a spread pin still pages once it exceeds eight screens; the subtitle keeps the pin mark and shows the *effective* bits (`deck paged · card paged *` while pin is `spread`). Toast once when a pin cannot be honored: `Reply is too large to spread`. Do not add a third user-facing config key in v1.

Hysteresis stays. Streaming under **auto** still does not flicker. Streaming under a pin stays in the pinned budgets (a `block` pin will not suddenly spread when a shell is short).

After substituting the budgets, call the existing `_refresh_main_mode_for_shown` / Files probe path. `ReadingAnchor` keeps the current card, block, and offset. Cycling to `block` does not jump to the newest shell; cycling to `spread` does not jump to Context. Following/arrival-dot rules are unchanged.

### 5.2 Scope, lifetime, persistence

- **Per focused deck panel**, like `_render_mode` and `_block_mode`. Split panels can disagree (one spread Main, one block Main). That is already true under auto when the panels have different heights; the indicator makes it readable.
- **Survives `j`/`k`, attempt toggle, and deck switch** inside that panel. The triage loop is the feature’s best trick (`sase-19x` docs phase: sticky Reply + newest block = one keypress per session). A `block` pin that reset on every node would be useless for that loop. A `spread` pin that reset on every node would be safer for perf; the 8-screen ceiling makes a sticky spread pin acceptable.
- **Files vs Main:** store **one pin per panel**, not per deck. Switching Main → Files maps `block → card` (finest available). Switching back restores `block` if the Main card still has blocks, else the finest available. This is cheaper than two pins and matches “how zoomed is this panel”.
- **Persist** in `ace_agents_deck_state.json` next to `preferred_card`. That file is already the home of “how I left the deck area.” Schema v1 is `{layout, ratio, focused, nodes_collapsed, panels: [{deck, preferred_card}]}` (`agent_deck_persistence.py`). Bump to v2 with optional `view: auto|spread|card|block` per panel; missing / unknown → `auto` (fail open, same as unknown decks). Block *cursor* stays ephemeral (`sase-19x` §3.1); the view pin is a reader preference, like the sticky card.
- **Not per node, not in config.** Config keeps the auto thresholds. The pin is TUI state.

### 5.3 What `Z` and folds continue to mean

| Key | Job |
| --- | --- |
| `Z` | Panel zoom: this deck occupies the detail column |
| `z`… | Fold depth *inside* a card’s sections |
| `P` | How many hierarchy levels share the viewport |
| `[`/`]` | Which card block, given the current view |
| `Ctrl+J/K` | Which card |

Do not name this feature “zoom”. `Z` already owns that word in help and the glossary (`glossary:deck-panel`). Help copy should say **cycle spread / card / block**.

---

## 6. Alternatives considered

**Manual-only (drop auto).** Short sessions and split geometry would always start paged or always start spread, both wrong. Auto is why the thresholds and hysteresis exist. Keep it as the default pin.

**Two keys, two bits.** See §4.3. Creates the illegal fourth state or a dead key.

**`S` as the default.** Workable via a tab-disjoint duplicate with `bulk_change_status`. Weaker mnemonic for a 3-stop control, and `S` already means bulk status on Patches. Document as a supported remap.

**Fold-mode `zs` only.** Zero occupancy cost, poor discovery. Fold mode’s help section is “Metadata Fold Mode”. Fine as an *alias*, not as the only binding. Card-blocks put `[`/`]` in `ace.keymaps.app` because they are a first-class navigation verb; this is the same class, used less often than `[` but about as often as `Z`.

**Include only the three views, unpin via click.** Border subtitles are not widgets, so click-to-unpin would need a new row. A 4-stop cycle makes auto first-class on the same key the user already learns.

**Force-spread with no ceiling.** Fights `sase-19x`’s reason to exist and the j/k budget. The 8-screen internal ceiling is the compromise: “prefer spread” rather than “always render 14k lines”.

**Persist nothing.** Then a `block` pin for triage dies on restart, while the sticky Reply card survives. Inconsistent. Persist with the rest of deck state.

**Show `paged` as the unmarked default.** That is today’s bug. Always name the effective deck mode; name the card mode when it can differ.

**A new config `ace.agent_decks.default_view`.** Unnecessary in v1. Auto + a persisted pin already covers “I always want block for triage” without another YAML knob. Revisit if people remap `P` to a no-op and still want a boot default.

---

## 7. Implementation sketch (for the later epic)

Presentation-only. No `sase-core-revision.txt` bump. Wait for `sase-19x.8` (rail), `.9` (flag cutover), `.10` (docs) so the subtitle, footer, and `docs/ace.md` land against the shipped rail and the unflagged block path.

Suggested phases (medium epic):

1. **Pure view pin + subtitle.** `DeckViewPin` enum (`auto/spread/card/block`), `screens_for_pin(pin, settings) -> (spread, block)`, `effective_view(deck_mode, block_mode, has_blocks) -> spread|card|block`. Extend `deck_subtitle(..., view=, pinned=)` with the tiers in §3.1. Invert drop order. Unit tests for skip rules and the 8-screen ceiling. Still auto-only in the panel; this phase is already a UX win if it ships alone, but do not cut over without the key.

2. **Pin + `P` + palette + footer + help.** Per-panel `_view_pin` on `DeckPanel`, substituted into `_decide` in `panel_spread.py` / `panel_blocks.py`. `AgentDetail.cycle_focused_deck_view()`. Full keymap pipeline cloned from `sase-19x.7`. `deck_view_cyclable` cache. Pilot: cycle honors ReadingAnchor; split panels independent; Files skips `block`; Tools gated; streaming under `block` pin does not spread; oversize spread pin degrades and toasts.

3. **Persist + goldens + docs.** Schema v2 `view` field. PNG goldens for the three views and the pinned vs auto subtitle (120×40, plus a tight width that uses the short name). `docs/ace.md` hierarchy section, key table, and the triage tip (`P` then `j`/`k`). `docs/configuration.md` only if a remap/`P` sharing note is needed. Glossary: extend `glossary:agent-data-card` / `glossary:agent-data-deck` with the three views and the pin; do not mint a new jargon term. Memory edits go with the epic lander, matching the `sase-19x` note that the lander applies proposed memory text directly.

Module map (keep `panel.py` / `titles.py` under the toobig cap):

| Module | Change |
| --- | --- |
| `widgets/decks/model.py` | `DeckViewPin` |
| `widgets/decks/view_pin.py` (new, pure) | `screens_for_pin`, `effective_view`, `next_view`, skip rules |
| `widgets/decks/titles.py` | subtitle tiers; drop order |
| `widgets/decks/panel_spread.py` / `panel_blocks.py` | read pin budgets |
| `widgets/decks/panel_chrome.py` | pass `view=` / `pinned=` |
| `models/agent_deck_persistence.py` | schema v2 |
| keymap / footer / help / palette | clone `sase-19x.7` |

`FORCE_SPREAD_SCREENS` lives next to `SPREAD_HYSTERESIS`. Do not thread it through `AgentDecksSettings` until someone needs it user-visible.

---

## 8. Risks

- **`P` vs `p`.** Adjacent keys, different jobs. Help and footer must always spell `P` as “view” and `p` as “pick deck”. The deck picker already reserves `p` internally (`DECK_PICKER_RESERVED_KEYS`); keep `P` out of that picker.
- **Pin vs hysteresis.** A `spread` pin with an 8-screen budget still uses the ±10% band. Document that auto-near-threshold flicker is an auto-only phenomenon; pins are sticky by construction.
- **Goldens.** Subtitle text will churn every Agents-deck PNG that shows a border. Budget a targeted `just fix-tui-screenshots` pass and inspect, same as D8 / block-keys.
- **Rail timing.** If this ships before `sase-19x.8`, the “rail present in both block modes” gap is still the main confusion. Wait.
- **Naming in copy.** Say **card block** in help if the 32-char budget allows; the short subtitle word is `block` because width is tight and the glossary already accepts “block” as the aka of card block in UI chrome (the rail, `[`/`]` footer “blocks”). Do not say “zoom”.
- **command_line.block_\*.** Unrelated. Keep action ids `cycle_deck_view`, never `cycle_block_view`.

---

## Recommended solution

Ship a **view pin** on each deck panel, default **auto**, with one key **`P`** that cycles **spread → card → block → auto**, skipping impossible stops, and a **subtitle that always names the effective deck mode** (`deck spread` / `deck paged`) **and the card mode when it can differ** (`card spread` / `card paged`), with `*` when pinned.

Implementation is a budget substitution in front of the deciders that already exist, plus chrome and the `sase-19x.7` keymap pipeline. Persist the pin beside `preferred_card`. Cap forced spread at eight screens so j/k stays fast. Wait until card blocks (including the rail and the flag cutover) are done, then do this as its own epic.

That is the smallest change that makes the mode obvious, gives a one-key walk through exactly the three states the product allows, and leaves the automatic thresholds in charge until the reader asks otherwise.
