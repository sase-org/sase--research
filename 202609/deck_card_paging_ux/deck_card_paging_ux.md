# Deck and card paging: a visible three-level view

**Research date:** 2026-09-26  
**Decision sought:** How should the Agents tab reveal and control deck/card spread and paging after `sase-19x` lands?

## Recommendation at a glance

Treat the display as **one ordered view depth**, with three effective layouts, rather than as two independent switches. Show the effective deck and active-card modes in a persistent, text-first badge in **each panel's top border title**. Bind **`P`** on the Agents tab to cycle the three layouts; offer the three direct choices and **Automatic view** in the command palette. Keep today's size-based Auto policy as the default. A manual selection should be a stable **per-panel, per-deck** preference, retained across agents and restarts; active card-block position remains ephemeral.

| Layout | Deck | Active card's blocks | What the reader gets |
| --- | --- | --- | --- |
| Fully spread | Spread | Inline | All cards and their blocks in one scrollable document |
| Page cards | Paged | Inline | One card, with its blocks in one scrollable document |
| Page blocks | Paged | Paged | One card and one block at a time |

`AUTO` is a **policy**, not a fourth layout: it resolves to one of these three through the existing thresholds and hysteresis. Deck spread plus block paging is prohibited by the accepted `sase-19x` decision D3. The user should never see that fourth Boolean combination, including while a mode is changing.

## What the evidence says

The accepted card-block plan, `plan:202609/agent_data_card_blocks.md`, specifies that only a card shown alone may page its blocks. The epic `sase-19x` currently has phases `.1`–`.8` closed and `.9` cutover / `.10` docs in progress. The recommendation here is for **after** that cutover, not for the flag-on intermediate state.

Today `deck_subtitle()` shows a dim `spread` only when the **deck** spreads. It shows no `paged` counterpart, says nothing about blocks, and its width candidates discard `spread` before the deck switcher. `deck_title()` has full, compact, and micro tiers but no mode. The one-row block rail appears in both block-spread and block-paged views and therefore cannot distinguish them. These are direct observations from `titles.py`, `panel_chrome.py`, and `block_rail.py`; all four reports corroborate them. In particular, a long newest block can look identical in the first viewport whether older blocks are inline below it or hidden on other pages. A visible label is more valuable than a transient animation or toast.

The existing transition machinery already captures `ReadingAnchor(card_id, block_id, offset_rows, pinned)` across automatic deck/block mode changes. Manual changes can use that path. The default thresholds are both `1.5` viewport heights; `0` requests paging, and the shared mode decision has 10% hysteresis. The original card-block sample reports 70 sessions, with 3/5/15 shells at p50/p90/max and 72/738/14,013 raw Reply lines. That makes both the middle layout and the risk of a very large forced spread real, though the sample is not a measured prevalence estimate for each layout.

Independent UX guidance supports a **persistent, contextual** indicator over routine toasts: [NN/g distinguishes nearby status indicators from notifications](https://www.nngroup.com/articles/indicators-validations-notifications/), and [Apple recommends showing selection state clearly when closely related views are offered](https://developer.apple.com/design/human-interface-guidelines/segmented-controls). Those are analogies, not validation of this particular TUI design. [WCAG's use-of-color guidance](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color) supports spelling out state rather than encoding Auto versus Fixed only by accent or dimming.

## A badge that answers both questions

Place the badge immediately after the deck name in the title and give it higher width priority than inactive card tabs. At full width, use explicit terms such as `AUTO · DECK PAGED · BLOCKS SPREAD` or `FIXED · DECK PAGED · BLOCKS PAGED`. In a compact split, shorten to `A D:P B:S` / `F D:P B:P`, with the legend in Help; the micro tier can use `A P/S` / `F P/P` if necessary. `A` and `F` are **text**, not just styles. Where the active card has fewer than two blocks, show `BLOCKS —` (or omit that field in a tiny title) rather than implying a block decision exists. On Files, show only the deck half; on Tools, where there is no useful choice, avoid a fictional block mode.

The top border is already where the panel names its deck and card. A bottom-border-only label would be lost in exactly the narrow split where a layout change is common. Remove the old subtitle `spread` tag once the badge exists; keep Files line counts and the deck switcher there. The rail may add a secondary cue—`all 5` for inline blocks, `page 3/5` for block paging—when width permits. The title remains the source of truth because the rail disappears in a spread deck and on cards without navigable blocks. Routine keypresses need no toast: the persistent badge changes in place. Use a concise message only when a requested layout is unavailable or pending.

The badge should report the **effective** layout, while `AUTO`/`FIXED` reports the policy. If a fixed `Page blocks` preference is viewed on Context, show `DECK PAGED · BLOCKS — · FIXED`; returning to Reply restores block paging. If Files contains media that the spread renderer cannot combine, keep the requested preference but show the effective paged result and its constraint. Never label an unrendered request as though it were on screen.

## Key and policy behavior

Bind one Agents-only app action, `cycle_deck_view`, to **`P`**. It is a printable terminal key, relates to `p` (pick deck), and is currently unused by Agents app actions. `P` does have bindings in other contexts, so the normal tab-availability/duplicate validation still applies. `v` is already `view_files` at app level and should not be taken. The suggested `B` / `Shift+B` forward/reverse pair does **not** give two terminal keys: uppercase `B` already is Shift+B. `(`/`)` could form a legitimate reverse pair with the existing delimiter family, but both are shifted punctuation and already have Artifacts-only file-version meanings. For three layouts, one cycle reaches any target within two presses; a reverse default is not necessary.

Use this explicit three-layout cycle, from least content isolated to most:

```text
Fully spread → Page cards → Page blocks → Fully spread
```

When the policy is Auto, the first `P` chooses the **next** distinct applicable layout after the current effective one and pins it; it must not merely pin the current picture. From a typical auto `Page blocks` Reply, that first press yields `Page cards`, which is the useful whole-Reply view without forcing the entire deck to spread. Subsequent presses cycle the explicit layouts. Direct palette actions—**Fully spread**, **Page cards**, **Page blocks**, **Use automatic view**—make every policy reachable, including a fixed copy of the current Auto layout. Help and the badge must explain the palette reset; Auto is deliberately a separate policy so the main key cycles exactly the three views requested. If user testing shows frequent Auto resets, add a dedicated reset shortcut rather than silently making the three-view cycle four steps long.

Apply changes to the **focused panel** and its selected deck. Retain the policy across `j`/`k`, deck switching, splits, zoom, and restart, matching other workspace-view preferences. Store a separate preference for Main and Files in each panel; do not attach it to a card ID or agent subject. A Reply's active block and scroll/following state stay per subject and are not persisted. A schema update to `ace_agents_deck_state.json` must decode version 1 as all-Auto; today's decoder rejects any version other than 1, so migration is required. A missing or unknown new field should fail open to Auto.

Skip layouts that are structurally equivalent or unsupported **for the active deck**: Files has no block-page layout; Tools has no meaningful cycle; one-card or one-block Main documents may have fewer distinct pictures. Preserve a fixed `Page blocks` preference when temporarily displaying a blockless card; do not silently erase it. If the current card has no blocks and two policies would render identically, the key may skip that duplicate while direct palette selection still permits it for future Reply cards. This keeps repeated presses visibly useful without making the preference card-local. Partial documents should not set policy or claim a new effective mode until the full current-subject document is available.

## Implementation and verification boundaries

This is presentation-only Textual state, keymaps, and chrome; no `sase_core` behavior is needed. Add one pure policy/resolution helper so title, footer, and action availability agree on the same effective state. Resolve explicit modes ahead of automatic measurement; keep hard renderer constraints, especially Files media. Route Main and Files changes through their existing transition paths so the card, block, row offset, and bottom pin survive. Do not turn a layout change into navigation or change `following` merely because a view was selected. Keep the keypress in memory and avoid rebuilding Main source data.

Forced fully spread is the main performance risk. Auto currently avoids very large spreads through a cheap row lower bound; an override removes that natural bound. Do not add an arbitrary three-screen refusal without evidence: it would break the promised **Fully spread** choice and complicate cycling. Benchmark a long, representative Reply (including the existing 5,000-line fixture and a pathological case); if it stalls the event loop, use a measured, explicit guard or deferred projection and explain the limit in the UI. Media incompatibility remains a hard constraint regardless of size.

Acceptance should include: each of the three layouts and Auto at wide and narrow widths; text legibility in monochrome; a blockless active card and a Files media page; focused versus unfocused split panels; version-1 persistence migration; first press from each Auto-resolved layout; hidden/disabled action on Tools or partial content; anchor and bottom-pin preservation; no unexpected change to following; and a long-Reply key-to-paint benchmark. The main visual test is simple: with body content covered, the title alone should tell a reader **which panel, which deck, whether the deck is spread or paged, whether the active card's blocks are inline or paged, and whether that choice is automatic or fixed**.

## How the four reports were reconciled

All four reports support the three-layout model and reject independent toggles. `cdx` and `grk` favor a top-title indicator; `mus` and `gem` favor the existing subtitle plus a rail cue. The current subtitle's drop order and the rail's absence in spread mode favor the **title as primary**, with a restrained rail cue. `cdx` and `grk` favor durable overrides, while `mus` favors subject-lifetime overrides; durable per-panel/per-deck state better matches saved layout and preferred card, provided `AUTO`/`FIXED` is visible and reset is easy to find. `grk` proposes `B`/`Shift+B`, `cdx` proposes `(`/`)`, `mus` proposes `v`, and `gem` proposes `P`; the key audit above favors a single `P`. `gem` recommends a toast on every change, while the persistent badge and contextual-indicator evidence make that unnecessary. `grk` proposes a fixed three-screen safety cap, whereas `cdx` would honor any explicit spread; the performance decision should follow measurement, not precede it.

The original reports are preserved beside this document: [cdx](deck_card_paging_ux__cdx.md), [grk](deck_card_paging_ux__grk.md), [mus](deck_card_paging_ux__mus.md), and [gem](deck_card_paging_ux__gem.md). Their audited immutable snapshots are respectively `file:explicit:ff294b170151c0f280efb93e`, `file:explicit:606bf1bfbdf58de14a5e4905`, `file:explicit:632208a0a03454b58985d958`, and `file:explicit:2912e8cf1d5e48e91006fc94`.

## Recommended solution

After `sase-19x` finishes, add a text-first **top-border mode badge** that always reports the effective deck and active-card layout plus `AUTO` or `FIXED`, with a small `all N`/`page N/M` cue on the block rail where it fits. Bind Agents-tab **`P`** to cycle **Fully spread → Page cards → Page blocks**, beginning from the next distinct layout when Auto is active, and provide direct choices plus **Use automatic view** in the palette. Persist a manual preference per panel and deck, preserve reading anchors through every transition, and verify large forced spreads before deciding whether they need a guard. This exposes the exact three valid states, makes automatic changes understandable, and gives one reliable, low-cost way to change the view.
