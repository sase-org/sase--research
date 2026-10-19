# Deck scrollability vs. card tabs: view badges, tab visibility, and the auto/fixed lock

Research report — researcher `mus` (independent swarm report, suffix `__mus`).
Scope: the currently focused sase agent deck in the Agents tab — can the user
scroll to see its entirety, or must they page through card sub-tabs with
`<ctrl+j/k>`? How should the chrome communicate that, and what should happen to
the `auto` / `fixed` badge language?

## TL;DR recommendation

Yes, this is a good idea, with three adjustments. Do not hide the tab strip in
spread mode; do not replace words with an icon alone; do not make badges
uniformly "bright". Instead:

1. Keep the tab strip always, but give it two visually distinct modes: in
   `SPREAD` render tabs as in-page anchors (no exclusive highlight pill, no
   `n/N` counter emphasis, scroll-derived active tab follows the scroll); in
   `PAGED` keep today's exclusive-selector tabs (`reverse bold` active pill +
   `n/N` + `<ctrl+j/k> cards` footer). The distinction, not the removal, teaches
   scrollability while preserving orientation.
2. Split today's single `{layout} · {status}` badge into two separately styled
   pieces: a high-salience layout pill (`SCROLL` / `CARDS` / `BLOCKS`) and a
   low-salience pin (`auto` → nothing/unlocked, `fixed` → `🔒`/`PIN`). The layout
   answers "can I scroll?"; the pin answers "will it stay that way?".
3. Keep the words, add the icon. `auto`/`fixed` as bare words are the problem,
   but an icon alone is worse (undiscoverable, ambiguous, width-fragile). Use
   `SCROLL` / `CARDS n/N` / `BLOCKS` plus `🔒` only on pinned views.

Details and rationale below. All file paths are relative to the sase repo root.

## 1. How the system works today

### 1.1 Three layouts, two render modes, two policies

- `src/sase/ace/tui/widgets/decks/model.py`: `DeckView` (`AUTO`, `SPREAD`,
  `PAGE_CARDS`, `PAGE_BLOCKS`), `RenderMode` (`SPREAD`, `PAGED`),
  `DeckViewPolicies` (per-panel `main`/`files`; Tools/FINAL/RECORD permanently
  `AUTO` with no badge), `cycle_card_id()`, `resolve_active_card()`,
  `with_panel_view()`, `DeckPanelState`, `DeckAreaState`.
- `src/sase/ace/tui/widgets/decks/view_policy.py`: `ViewContent`
  (`card_count`, `active_block_count`, `spread_blocked`), `ResolvedView`
  (`policy`, `shown`, `status`), `ViewStatus` (`OK`, `PENDING`, `BLOCKED`),
  `_layout_signature()` mapping each `DeckView` to
  `(RenderMode, _BlockState)`, `_distinct_layouts()`, `next_view()`,
  `forced_deck_mode()`, `forced_block_mode()`, `resolve_view()` (the "D5 label
  rule": pending/blocked show effective layout; vacuous fixed requests show the
  requested name so the badge stays stable).
- `src/sase/ace/tui/widgets/decks/render_mode.py`: `decide_render_mode()` with
  `SPREAD_HYSTERESIS = 0.10`, `spread_budget_rows()`, `measure_card_rows()`
  (cheap lower-bound then exact `console.render_lines`, 64-entry cache).
- `src/sase/ace/tui/widgets/decks/panel_spread.py`: `is_spread()`,
  `_decide_document_mode()`, `_decide_main_mode()`, `_decide_files_mode()`,
  `_cycle_document_spread()`, `_cycle_main_spread()`, `_cycle_files_spread()`,
  `_main_spread_active()`, `spread_active_for()`.
- `src/sase/ace/tui/widgets/decks/panel_view_queries.py`:
  `DeckPanelViewQueriesMixin.view_content()`, `effective_layout()`,
  `next_view()`, `resolved_view()`, `deck_view_cycle_available`,
  `_compute_view_cycle_available()`, `_sync_view_cycle_available()`.
- `src/sase/ace/tui/agent_decks_settings.py` + `src/sase/default_config.yml`
  (`ace.agent_decks`): `spread_max_screens: 1.5`,
  `block_spread_max_screens: 1.5`, `final_tail_delay_seconds: 5.0`. A
  multi-card deck spreads when its measured rows fit in 1.5 viewport heights;
  `0` means always paged. One-card decks always spread (`forced_deck_mode()`).
- `src/sase/ace/tui/models/agent_deck_persistence.py`: persists per-panel Main /
  Files policies; Files `PAGE_BLOCKS` is rejected/decoded to `AUTO`.

So `AUTO` is a policy ("decide for me from measured height + hysteresis +
same-subject stickiness"), while `SPREAD` / `PAGE_CARDS` / `PAGE_BLOCKS` are both
policies (when pinned) and on-screen layouts (the `shown` field). The badge
conflates the two axes into one string, which is the root of the confusion.

### 1.2 What the user actually sees

- `src/sase/ace/tui/widgets/decks/view_badge.py`: `badge_variants()` returns
  long/short/tiny `rich.text.Text` for a `ResolvedView`. Long/short join as
  `{layout} · {status}`; tiny joins as `{layout}·{status}`. Layout words:
  `spread` / `page cards` / `page blocks` (short: `spread` / `cards` /
  `blocks`; tiny: `S` / `C` / `B`). Status words: `auto` / `fixed` (tiny `A` /
  `F`), plus `spreading…` / `spread unavailable` for Files pending/blocked.
  Styling (`_status_style()`): unfocused everything `dim`; focused AUTO status
  is muted `#888888`; focused fixed status is `bold {accent}`; BLOCKED is
  `#D7AF5F`.
- `src/sase/ace/tui/widgets/decks/titles.py`: `deck_title()` (tier ladder:
  full-long → full-short → compact-long → compact-short → compact-tiny →
  micro-tiny → micro-alone; Files/FINAL with >4 tabs skip full rungs via
  `_skips_full_tier()`), `_build_full()` (all tab titles + `reverse bold`
  active pill + `n/N`), `_build_compact()` (`‹ n/N ›` + active title),
  `_build_micro()` (deck name + `n/N`), `_badge_variants()` (badge only for
  MAIN/FILES; Tools/FINAL/RECORD keep tab-only rungs), `ZOOM_CHIP_TEXT/STYLE`
  (reverse-gold `ZOOM` precedent for a bright chip), `deck_subtitle()` (deck
  switcher; the old `spread` tag is gone by design).
- `src/sase/ace/tui/widgets/decks/panel_chrome.py`: `DeckPanelChromeMixin`
  (`_main_tabs()`, `_files_tabs()`, `_tools_tabs()`, `_final_tabs()`,
  `_record_tabs()`, `_active_tab_index()`, `_chrome_view()` with held views
  across partial paints, `_main_chrome_view()`, `_files_chrome_view()`,
  `refresh_chrome()`). Tabs are built unconditionally — spread mode still draws
  the full tab strip today.
- `src/sase/ace/tui/widgets/decks/panel_navigation.py`:
  `DeckPanelNavigationMixin.cycle_card()` — in spread, `<ctrl+j/k>` calls
  `_cycle_main_spread()` / `_cycle_files_spread()` / `_cycle_document_spread()`
  (scroll-to-card via `scroll_to_card()` / anchor rows); in paged mode it calls
  `show_card()` / `next_file()` / `prev_file()`. Same keys, different mechanics.
- `src/sase/ace/tui/bindings.py`: `ctrl+j` `next_deck_card`, `ctrl+k`
  `prev_deck_card`, `P` `cycle_deck_view`, `p` `pick_deck`;
  `src/sase/ace/tui/actions/agents/_panel_detail.py`: `action_next_deck_card()`,
  `action_prev_deck_card()`, `action_cycle_deck_view()` (one step wider
  `page blocks → page cards → spread → wrap` via `policy_next_view()`; first fix
  from AUTO fires a teaching toast: "`Main view fixed · palette `Deck view:
  automatic` undoes`"), `action_set_deck_view_at()`.
- `src/sase/ace/tui/widgets/_agent_detail_deck_view.py`:
  `AgentDetailDeckViewMixin.cycle_focused_deck_view()` /
  `set_focused_deck_view()`.
- `src/sase/ace/tui/widgets/_keybinding_bindings_agents.py` (footer):
  `deck_card_count > 1` → `ctrl+j/ctrl+k cards` (shown in both spread and paged
  — the label does not distinguish scroll-jump from page-turn);
  `card_blocks_navigable` → `(/) blocks`; `deck_view_cycle_available` → `P
  view` (only when `next_view()` is non-None, i.e. ≥2 distinct layouts).
  Scroll keys (`ctrl+d`/`ctrl+u` `scroll_detail_down/up`, `G`/`g`
  `scroll_to_bottom/top`) are not footer-advertised on the Agents tab; the only
  scroll affordances are the `VerticalScroll` scrollbar and the help modal.
- `src/sase/ace/tui/modals/help_modal/agents_main_sections.py`: `ctrl+j /
  ctrl+k Cycle deck card`, `P Cycle deck view (auto: palette)`, `(/) Older /
  newer card block`, scroll rows.
- Tests: `tests/ace/tui/widgets/decks/test_deck_view_policy.py` (signature
  table, `_distinct_layouts`, widening order, `resolve_view`, the D5 badge
  table `spread · auto` / `S·A` etc.), `tests/ace/tui/widgets/decks/test_deck_titles.py`
  (badge follows deck name, badge ladder, micro-tiny, Tools tab-only, Files
  crowded compact, fixed-requested-name, zoom chip), `test_deck_chrome.py`,
  `test_deck_view_keys.py`, `test_deck_view_main_pilot.py`,
  `test_deck_view_files_pilot.py`, `test_deck_model.py`,
  `tests/ace/tui/visual/test_ace_png_snapshots_agents_deck_views.py`.

### 1.3 The two-level scrollability subtlety

Deck-level paging is not the whole story. There are two independent axes:

1. Deck level: one card per page (`PAGE_CARDS`) vs. all cards on one scroll
   (`SPREAD`).
2. Block level inside the active card: one block per page (`PAGE_BLOCKS`) vs.
   all blocks inline (`PAGE_CARDS` deck + block-spread, or `SPREAD` deck).

`effective_layout()` in `panel_view_queries.py` reports the combination
(`block_mode_for_active_card() is PAGED` → `PAGE_BLOCKS`). A user in
`PAGE_CARDS` with a 40-block Reply still cannot "see the entirety" by deck
scroll alone — `(/)` block paging applies. Any badge or tab treatment must not
promise full scrollability when only the deck axis spreads. Today's
`page cards · auto` vs. `page blocks · auto` distinction is precisely this, and
it is the strongest argument for keeping three layout words rather than
collapsing to two.

## 2. Critique of the proposed plan

### 2.1 "Only show card sub-tabs when split out (paged)" — directionally right, literally wrong

The instinct is correct: the always-on tab strip teaches "there are other
pages, use `<ctrl+j/k>`" even when everything is already on screen, which is
exactly backwards. But removing the strip in spread mode has three costs:

1. Loss of orientation. In spread, the strip is the only at-a-glance deck
   inventory (how many cards, which one am I over). The scroll-derived active
   tab (`spread_active_card()`, `_files_spread_active_index()`) already follows
   the scroll position — deleting the strip deletes a working "you are here"
   map. Users with 5-card MAIN spreads would lose the cheapest way to know the
   deck got long.
2. Loss of continuity. AUTO flips between spread and paged as content streams
   (hysteresis damps but does not eliminate it). A strip that appears/disappears
   on each flip is a layout jolt in the most space-constrained chrome row, and
   it fights the held-view anti-flicker design (`_held_views()`).
3. Spread `<ctrl+j/k>` still exists. It scroll-jumps between cards
   (`scroll_to_card()`, anchor rows). If tabs vanish in spread, the footer
   `ctrl+j/ctrl+k cards` hint (shown whenever `deck_card_count > 1`) points at
   invisible targets, and keyboard users lose the visible confirmation that the
   jump landed on the intended card.

Adjustment: keep the strip in both modes but make mode unmistakable at a
glance (Section 4.1). Paged tabs = exclusive selector (today's pill + `n/N`).
Spread tabs = anchor map (no exclusive pill, or a hollow/underline active
marker; de-emphasize `n/N`; the active tab tracks scroll). This preserves
orientation while fixing the false "must page" signal.

One legitimate exception: single-card decks. With `card_count <= 1` everything
collapses to one signature (`test_signature_single_card_collapses_all`), the
`P` cycle is unavailable, and the tab strip is a single self-named tab. There
the strip and the badge both add noise for zero information. Suppressing the
badge (and optionally the `1/1`-less single tab) for single-card decks is safe
and I recommend it.

### 2.2 "Bright and clearly visible badges" — yes, but only the layout half

Today's badge is low-salience by construction: muted `#888888` for AUTO (the
common case), small text tucked after `◆ MAIN`, competing with tabs, subtitle
switcher, and the gold `ZOOM` chip. Users do not read it because nothing tells
them to. A brighter layout signal is warranted — it is the primary mode
indicator.

But brightening the whole `{layout} · {status}` string brightens the wrong
thing half the time. `auto` vs. `fixed` is provenance, not state; making
`auto` bright trains users to watch the half that matters least. Files
`spreading…` / `spread unavailable` are transient/negative states that deserve
their own treatments (spinner-ish muted + warning gold already do this well).
Recommendation: one bright pill for layout, one quiet pin for policy. Bright
does not mean large: a short uppercase pill (`SCROLL` / `CARDS` / `BLOCKS`) in
accent or green/blue reads at a glance and survives the title width ladder
better than today's `page blocks · fixed` sentence.

Accessibility constraint: never color-only. Pair the pill with a shape/word
difference (different words already do this), keep the `n/N` counter for paged,
and keep everything legible when unfocused (today unfocused is all-`dim`, which
would erase a color-only distinction — the word difference must carry it).

### 2.3 "Replace auto/fixed with a lock icon" — yes as an addition, no as a replacement

`auto`/`fixed` are jargon: they name the mechanism (policy) from the system's
point of view, not the user's ("will this view change under me?"). A lock maps
better to the user's mental model: unlocked = "follows content size",
locked = "stays where I put it". The proposal's instinct is good.

Three objections to icon-only:

1. Discoverability. Nothing about `🔒` says what is locked (the layout? the
   card? the scroll?) or how to unlock (palette `Deck view: automatic`? `P`?
   `P` does not cycle back to AUTO today — it only walks fixed layouts wider,
   so unlock is palette-only). Icon-only makes a hidden affordance hider.
2. Ambiguity. A lock next to `SCROLL` could read as "scroll locked" (the
   opposite of the truth — pinned-spread still scrolls freely; what is locked
   is the layout choice). Text `auto` at least names the right noun (the view
   decision), even if dully.
3. Width ladder fragility. The tiny tier (`S·A`, `C·F`) already compresses to
   near-meaninglessness; a lone glyph at micro widths is worse. And terminal
   font coverage for `🔒`/`🔓` is less universal than ASCII — fall back to
   `PIN`/`AUTO` text or a widely covered glyph (`⚿`/`🔓` vary), and always keep
   a text equivalent in help/palette.

Adjustment: icon + short word, with the word carrying meaning and the icon
carrying glanceability. Concretely: pinned views append `🔒` (or `▪PIN`) to the
layout pill; auto views show no pin at all (absence is the signal — today's
`· auto` text is pure noise in the common case and its removal funds the
brighter pill within the same width budget). The footer/help then teach
"`P` pins & widens · palette Deck view: automatic unpins".

### 2.4 What the plan misses

- Block-level paging (Section 1.3). Collapsing the badge to "scroll vs. tabs"
  erases `CARDS` vs. `BLOCKS`, and users will report "SCROLL but I still can't
  see it all" when a 40-block card pages internally. Keep three layout states.
- The `P` one-way ratchet. `P` pins on first press and never unpins (by
  design, per `cycle_focused_deck_view()` + toast). If pins become more
  prominent (lock icon), expect more users to pin accidentally and more "stuck
  in fixed" complaints. Either make `P` long-cycle back to AUTO (wrap
  fixed→…→AUTO) or add an explicit unpin key; at minimum, surface "palette to
  unpin" in the footer when pinned (there is room: `P view` only shows when
  cycling is available — extend the label to `P view · auto:palette` or similar
  when pinned).
- Footer dishonesty in spread. `ctrl+j/ctrl+k cards` means page-turn in paged
  but scroll-jump in spread. If tabs change meaning by mode, the footer must
  too (`cards` → `jump` in spread, or `cards` stays with a scroll qualifier).
- Width-budget reality. The title row is the scarcest row in the UI (deck name
  + badge + tabs + `n/N` + `ZOOM` chip vs. `size.width - 4`). Every added
  brightness/pill must be priced against the existing ladder
  (`test_badge_ladder_prefers_long_then_short_then_tiny`,
  `test_files_crowded_tabs_skip_full_rungs_with_badge`). Short uppercase pills
  are cheaper than today's long words — this funds the change — but the exact
  ladder needs re-derivation, not just a color swap.
- Unfocused panels. Four-plus deck panels can be visible (splits, zoom
  snapshot). Dimming everything unfocused is correct, but the layout word must
  still differ textually there (it does today; preserve that).

## 3. Alternatives considered

| Option | Upside | Why not (sole solution) |
|---|---|---|
| Scrollbar-only affordance | Zero chrome cost | Thin `VerticalScroll` bar is invisible at a glance; paged views also scroll within a card, so presence of a bar does not answer the question |
| `…more below` / fade hint in body | Answers scrollability at point of use | Content-area widget, fights card separators and block projection; transient; does not survive narrow heights |
| Status-bar line (`scrollable` flag) | Cheap | No such bar exists; subtitle switcher row is for deck switching, overloading it confuses two navigations |
| Auto-hide tabs in spread (literal proposal) | Strongest spread signal | Section 2.1: loses orientation, jolts on AUTO flips, orphans spread `ctrl+j/k` |
| Icon-only lock, no words | Minimal width | Section 2.3: undiscoverable, ambiguous, font-fragile |
| Merge CARDS+BLOCKS into one `PAGED` | Simpler badge | Section 1.3: lies about block paging; breaks `next_view()` widening order users already learned via `P` |

## 4. Recommended solution

### 4.1 Tab strip: same strip, two modes

- PAGED (deck): today's treatment unchanged — all titles, `reverse bold` active
  pill, `n/N` counter. Meaning: "exactly one is visible; `<ctrl+j/k>` turns
  the page."
- SPREAD (deck): anchor-map treatment — all titles in muted style, active tab
  follows scroll (`spread_active_for()` already computes it) rendered as an
  underline or hollow marker rather than the exclusive reverse pill, `n/N`
  de-emphasized or dropped (position is continuous, not indexed). Meaning:
  "all below; `<ctrl+j/k>` jump-scrolls; plain scroll works."
- Single-card deck: suppress the view badge entirely (nothing to decide); keep
  or drop the lone tab per width (dropping is fine — the card title is visible
  in-body via separators).
- Tools/FINAL/RECORD: unchanged (tab-only, no badge) — out of scope, but audit
  FINAL's always-spread document (`final/document.py` returns `SPREAD`) so its
  tab strip does not accidentally inherit the new paged styling.

### 4.2 Badge: bright layout pill + quiet pin

Replace `{layout} · {status}` with `{PILL}[ 🔒]`:

- `SCROLL` — deck spreads; plain scroll (`ctrl+d/u`, mouse, scrollbar) shows
  everything. Styled as the bright element (bold accent-backed pill; exact
  token TBD with theme — accent background already has precedent in the active
  tab pill and `ZOOM` chip).
- `CARDS n/N` — deck pages one card at a time; `<ctrl+j/k>` required for other
  cards. `n/N` stays inside the pill so the count survives tier drops.
- `BLOCKS` — active card pages one block at a time; `(/)` required within the
  card even though the deck axis shows one card. Keeps today's valuable
  CARDS/BLOCKS split.
- Pin: AUTO shows no pin (absence = follows content); pinned appends `🔒`
  (fallback `PIN` where glyph coverage is doubted). Pending/blocked keep
  today's muted `…` / gold `!` treatments on the layout pill rather than as
  separate status words (`SCROLL…` while probing, gold `NO SCROLL` when media
  blocks spread — same semantics as `spreading…` / `spread unavailable`, new
  clothing).
- Width ladder (to re-derive in `titles.py` / `view_badge.py`): pill-first —
  drop `n/N` from pill before dropping pill words; tiny tier becomes single
  letters *with* the pin preserved (`S` / `C` / `B` + `🔒`), because policy
  matters most exactly when space is scarcest (pinned-narrow is the "stuck"
  complaint shape). Micro tier keeps pill, drops tabs before pill.
- Unfocused: keep all-`dim` but preserve word differences (no color-only
  signaling).

### 4.3 Footer, help, and toast: teach the two axes

- Footer (`_keybinding_bindings_agents.py`, both agent + archive paths in
  `_display_detail_footer.py`): split today's `ctrl+j/ctrl+k cards` into
  `ctrl+j/k page` (paged deck) vs. `ctrl+j/k jump` (spread deck). When pinned,
  extend `P view` with the unlock path (`P view · auto:palette` or a second
  `unpin` entry if a key is added). Keep `(/) blocks` as-is.
- Help (`agents_main_sections.py`): `Cycle deck card` → two rows (`Page deck
  card (paged)` / `Jump to card (spread)`); `Cycle deck view (auto: palette)`
  → `Pin & widen deck view (palette: automatic unpins)`.
- Toast (`action_cycle_deck_view()` in `_panel_detail.py`): keep the first-fix
  toast — it is the only in-flow unlock teaching — but shorten to fit 70 cols
  with the new vocabulary (`Main pinned · palette Deck view: automatic
  unpins`).
- Palette labels (`Deck view: automatic/spread/cards/blocks` via
  `action_set_deck_view_at()` / `DECK_VIEW_CHOICES`): rename to match pills
  (`Scroll all`, `Page cards`, `Page blocks`, `Automatic`) or keep enum values
  and change display strings only — persistence (`agent_deck_persistence.py`)
  stays on the enum.

### 4.4 `P` behavior: fix the ratchet while touching this

Minimal fix (recommended): after the last fixed layout, one more `P` returns to
`AUTO` (wrap the widening walk through AUTO). `next_view()` in
`view_policy.py` currently returns `None` when fewer than two distinct layouts
exist and otherwise walks fixed layouts; extending the walk to include AUTO as
a rest stop preserves `deck_view_cycle_available` gating (still `None` for
single-card/Tools/blocked-Files) while making pin reversible from the
keyboard. Update `_compute_view_cycle_available()`,
`cycle_focused_deck_view()` (no more `first_fix`-only toast — toast on
unpin instead), and the `P view` footer visibility accordingly. If the team
prefers not to change `P` traversal, the fallback is a dedicated unpin key —
but that spends a binding to preserve a wart.

## 5. Implementation sketch

- `view_badge.py`: replace `_status_texts()` / `_layout_texts()` vocabulary
  with pill + pin variants; keep the `(long, short, tiny)` triple and
  `_status_style()` split (bright style for layout segment, muted/bold-accent
  for pin). Update the D5 table test (`test_badge_variants_d5_table`) —
  expect churn in `test_deck_view_policy.py` and every `titles.py` badge test
  (`test_badge_follows_deck_name_before_tabs`,
  `test_badge_ladder_prefers_long_then_short_then_tiny`,
  `test_resolved_fixed_badge_shows_requested_name`, Files crowded test).
- `titles.py`: add spread-vs-paged tab builders (or a mode flag into
  `_build_full()` / `_build_compact()`), re-derive the candidate ladder with
  pill widths, keep `_skips_full_tier()` behavior, keep `ZOOM` chip precedence
  (chip leads, pill follows — two bright elements need an order; zoom wins as
  the rarer state).
- `panel_chrome.py`: pass `is_spread` into `deck_title()`; suppress badge for
  single-card decks in `_chrome_view()` (Main: `len(cards) <= 1`; Files:
  `len(file_list) <= 1`); held-view logic unchanged.
- Footer/help/toast/palette strings as in 4.3 (touches
  `_keybinding_bindings_agents.py`, `_display_detail_footer.py`,
  `agents_main_sections.py`, `_panel_detail.py`, command catalog availability
  in `commands/_availability_agents.py` if labels move there).
- `view_policy.py` only if 4.4 is accepted (`next_view()` walk + `resolve_view()`
  shown-name rule for the AUTO rest stop).
- Visual goldens: `test_ace_png_snapshots_agents_deck_views.py` + `just
  fix-tui-screenshots` per `tui_screenshot.md`; perf: no new per-keypress work
  (badge/tab computation stays in `refresh_chrome()` fast path — see
  `tui_perf.md` rules 5/6; spread measurement caching in `render_mode.py`
  untouched).
- Docs: keymap/help text changes may need `docs/` touch-ups per
  `docs_writing.md` conventions; `default_config.yml` comments for
  `spread_max_screens` should gain one line naming the new pills.

## 6. Verification done for this report

- Read `model.py`, `view_policy.py`, `view_badge.py`, `render_mode.py`,
  `spec.py`, `titles.py`, `panel_chrome.py` (both halves),
  `panel_view_queries.py`, `panel_navigation.py`, `panel_spread.py` (spread
  decisions + spread cycling + anchor math), `document_view.py`
  (`show_card()` vs. `scroll_to_card()`), `_agent_detail_deck_view.py`,
  `_panel_detail.py` (`action_cycle_deck_view` + toast + palette set),
  `_keybinding_bindings_agents.py` + `_display_detail_footer.py` (footer
  conditions), `agents_main_sections.py` (help rows), `agent_decks_settings.py`
  + `default_config.yml` (1.5 screens, `P`, `ctrl+j/k`), badge/policy/title
  tests, and the `tui.md` → `tui_perf.md` / `tui_screenshot.md` memory chain
  (audited reads). No screenshots or live TUI runs were needed for a
  research-only turn; the visual recommendations above should be validated with
  `sase screenshot` and the deck-views PNG goldens before landing.
- Deliberately did not seek out sibling-swarm reports (`__cdx`/`__cld`/`__grk`/`__gem`).

## 7. Open questions for the lead

1. Should Files `spread unavailable` (media-blocked) keep the gold warning, or
   does the new `NO SCROLL` pill cover it? (Lean: keep gold — it is a content
   limitation, not a layout choice.)
2. Is `P`-wraps-to-AUTO acceptable, or is pin deliberately hard to exit to
   prevent accidental unpins during demos? The footer/toast wording depends on
   this.
3. Glyph coverage: is `🔒` safe in the team's terminals, or should the pin be
   ASCII (`PIN` / `*`)? Recommend shipping text-first with the glyph as
   progressive enhancement.
