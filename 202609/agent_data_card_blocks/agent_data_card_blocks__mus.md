# Agent data card blocks ("card blocks"): design research

Research report (mus). Independent assessment of the proposal to add sub-card
"agent data card blocks" to the Agents-tab deck system (sase-17d epic context):
spread-by-default / paged-past-threshold blocks inside a card, `ctrl+shift+j/k`
block cycling, and splitting the Main deck's Reply card into one block per
sase-shell `AGENT CHAT` sub-section with the last block shown first.

## Verdict

Good idea, worth building, with four adjustments (all called out in §2). The
Reply card is the right first use-case: it is the longest card, the one users
page through most, and its content already has a visible per-shell structure
(phase dividers) that blocks would merely reify. The deck machinery built by
sase-17d — spread/paged decision, cycling, separators, title chrome, search
indexing — applies almost unchanged one level down, so this is a generalization
exercise, not a new subsystem. The main risks are keymap deliverability
(`ctrl+shift` in terminals), a third navigation dimension, and the proposed
block-order reversal, each addressed below.

This is presentation-only Textual state, so under the Rust core boundary it
stays in this repo; no `sase-core` change and no `sase-core-revision.txt` bump
is needed.

## 1. What exists today (grounding)

- Cards are `CardPart(card_id, title, *renderables)` with ids `context`,
  `reply` (titled "Reply" or "Output"), `summary`
  ([card_part.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_43/src/sase/ace/tui/widgets/decks/card_part.py:27)).
  A Main document is a `MainDeckDocument` holding an ordered tuple of cards
  ([main_document.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_43/src/sase/ace/tui/widgets/decks/main_document.py:11)).
- Spread-vs-paged is decided purely by measured rows against
  `spread_max_screens` (default 1.5) viewport heights, with 10% hysteresis
  ([render_mode.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_43/src/sase/ace/tui/widgets/decks/render_mode.py:27),
  [agent_decks_settings.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_43/src/sase/ace/tui/agent_decks_settings.py:8)).
- Card cycling is `ctrl+j/k` (`next_deck_card` / `prev_deck_card`), decks are
  `ctrl+n/p`, both wraparound via pure helpers `cycle_card_id` / `cycle_deck_id`
  ([bindings.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_43/src/sase/ace/tui/bindings.py:265),
  [model.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_43/src/sase/ace/tui/widgets/decks/model.py:47)).
  Spread-mode cycling scrolls to the card anchor; paged-mode cycling swaps the
  single shown card ([panel.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_43/src/sase/ace/tui/widgets/decks/panel.py:280)).
- The Reply card's `reply_parts` are assembled in
  [_agent_display_render.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_43/src/sase/ace/tui/widgets/prompt_panel/_agent_display_render.py:497)
  in three shapes: (a) follow-up consolidation — main-agent reply then one
  phase per follow-up (`build_monitor_phase`, `build_gate_phase`, or
  `render_phase_divider` + `render_agent_reply_content`); (b) DONE/FAILED single
  agent — `AGENT CHAT` header plus timestamped reply chunks (each with a
  `render_timestamp_divider`) or a single response; (c) running agent —
  `AGENT REPLY` header plus live reply. Phase dividers (`--- LABEL --- HH:MM:SS
  ---`, [content.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_43/src/sase/ace/tui/widgets/prompt_panel/_agent_display_content.py:166))
  already delimit one sub-section per shell, so the proposed split points exist
  visually today.
- Spread separators carry the card id in `Style` meta under `DECK_CARD_META_KEY`
  for scroll-derived active-card detection and section navigation
  ([separators.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_43/src/sase/ace/tui/widgets/decks/separators.py:60),
  [_section_navigation.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_43/src/sase/ace/tui/widgets/prompt_panel/_section_navigation.py:27)).
- There is precedent for a `ctrl+shift+` binding in this codebase
  (`ctrl+shift+o` → `jump_to_entry_forward`,
  [bindings.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_43/src/sase/ace/tui/bindings.py:23)).

## 2. Critique and adjustments

### 2.1 Good idea, and the Reply card is the right first cut

The Reply card concentrates the deck's worst case: multi-follow-up agents
concatenate several full shell outputs into one scroll, which is exactly the
content that trips the paged threshold and then forces card-level paging to
show an undifferentiated wall. Splitting at phase boundaries turns an
incidental visual structure into a navigable one, and per-phase labels already
exist (`AGENT (code)`, `MONITOR`, `GATE`, … via `get_phase_label`), so block
titles are free. No objection to the use-case.

### 2.2 ADJUSTMENT 1 — Do not truly reverse block order; keep chronological order and default the selection to the last block

The request asks for reversed block order so the newest output shows first.
True reversal is a mistake, for three reasons:

1. Spread mode reads top-to-bottom. If the stored order is reversed, the spread
   rendering shows newest-first while every other log-like surface in the
   product (monitor/gate output, timestamped chunks, attempt history) reads
   oldest-first. Chronological spread with "start at the bottom" matches how
   chat UIs and `tail` behave; reversed spread matches nothing else here.
2. Direction stability. With chronological storage, `j` always means
   newer/forward and `k` older/back at every level (cards and blocks alike).
   With reversal, `ctrl+shift+j` means "older" inside Reply but "next" for
   cards — a needless inversion to document and remember.
3. Index stability as follow-ups append. Chronological append keeps existing
   block ids and positions stable; a reversed store re-indexes on every new
   follow-up, which complicates the pinned-selection logic (§4).

What the request really wants — "I open Reply and see the latest output, one
keystroke reaches the previous one" — is fully satisfied by chronological
order plus initial-selection-equals-last when the Reply card becomes block-paged.
That is also exactly the `resolve_active_card` pattern with a different default
([model.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_43/src/sase/ace/tui/widgets/decks/model.py:120)),
so it reuses tested logic instead of inventing reversed-order logic.
Spread mode is unaffected (it shows everything anyway).

### 2.3 ADJUSTMENT 2 — Verify `ctrl+shift+j/k` reaches the app in supported terminals, and ship a fallback binding

`ctrl+j` is LF (`0x0A`); in legacy terminal modes `ctrl+shift+j` typically
arrives as the identical byte, making the two bindings indistinguishable no
matter what Textual declares. Distinct delivery needs kitty-keyboard /
modifyOtherKeys / CSI-u sequences, which depend on terminal + terminfo + the
Textual xterm parser cooperating. The `ctrl+shift+o` precedent suggests this
can work in the maintainer's setup, but it must be verified per targeted
terminal (at minimum the ones in the TUI screenshot automation), not assumed.
If any supported terminal coalesces the keys, the block feature becomes an
unreachable modal state there — the same "Reply card is unreachable" failure
mode sase-17d.2 already hit once (sase-17d note #1).

Recommendation: keep `ctrl+shift+j/k` as primary, but also bind block cycling
to a pair that survives plain terminals (e.g. `alt+j/k`, or `]`/`[` if free —
check against the Agents-tab keymap in
[default_config.yml](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_43/src/sase/default_config.yml:642)),
make both pairs user-overridable config entries following the existing
`next_deck_card` pattern, and surface both in the help modal's deck section
([agents_bindings.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_43/src/sase/ace/tui/modals/help_modal/agents_bindings.py:84)).
Test the fallback, not just the primary.

### 2.4 ADJUSTMENT 3 — One threshold knob, not two

The proposal says "a configurable threshold" for blocks. Do not add
`block_spread_max_screens`; reuse `ace.agent_decks.spread_max_screens`. The
decision function is already row-budget-based
([render_mode.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_43/src/sase/ace/tui/widgets/decks/render_mode.py:27)),
so feeding it block rows Just Works, one knob keeps spread/paged behavior
consistent across levels, and a second knob doubles the golden-screenshot
matrix (§6) for no user-visible benefit. If per-level tuning ever proves
necessary, split the knob then — corpus before mechanism.

### 2.5 ADJUSTMENT 4 — Blocks for Reply only in v1; keep them out of the card chrome's tab strip

Do not generalize blocks to Context/Summary yet, and do not render block tabs
in the deck title strip next to card tabs. Two tab strips (cards × blocks)
plus a deck switcher is the "beautiful" requirement's biggest enemy. Instead:
the title strip keeps showing cards; when the active card is block-paged
Reply, the subtitle/status line shows the block position (`‹ 3/5 › MONITOR …
--- HH:MM:SS` reuse of the phase label) — one line, existing chrome
([titles.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_43/src/sase/ace/tui/widgets/decks/titles.py:1)).
The nested-mode rule that keeps this comprehensible: block paging applies only
when the Reply card is itself the paged focus (deck paged + Reply active).
In deck-spread mode the Reply card always renders its blocks spread with
titled separators, exactly like cards today. Four theoretical mode
combinations collapse to two user-visible ones, and there is never paging
inside paging.

### 2.6 Alternatives considered and rejected

- **More cards instead of blocks** (emit one `CardPart` per phase, cycle with
  existing `ctrl+j/k`). Rejected: it pollutes the card tab strip with a
  variable number of phase tabs, changes what `ctrl+j/k` means per agent, and
  breaks the stable three-card mental model (`context`/`reply`/`summary`) that
  persistence, search, and the glossary strands assume.
- **Section-jump instead of paging** (pager-style `ctrl+n/p`-to-header within
  the card). Cheaper, but it leaves the wall-of-text problem unsolved for the
  longest outputs and adds a fourth keybinding family. Blocks subsume it:
  block-paged cycling *is* section jumping with focus.
- **Foldable phase sections.** More code (fold state per phase, fold chrome),
  conflicts with the spread aesthetic sase-17d chose, and folds hide content
  by default where blocks page it by necessity. Revisit only if block paging
  tests poorly with real sessions.

## 3. Terminology

"Card block" is fine and composes with the existing glossary
(`agent-data-card`, `agent-data-deck`, `deck-panel` strands). Note the existing
unrelated use of "card" in `binary_card_document` (pager link targets,
[landings.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_43/src/sase/pager/landings.py:122))
— do not rename either, but the new glossary strand should scope "card block"
to agent data cards explicitly so pager "cards" don't collide. Block ids
should be stable strings (`reply/0`, `reply/1`, … or phase-slug ids), never
bare indices, so selection pinning survives follow-up appends.

## 4. Recommended design

**Data.** Add a `BlockPart(block_id, label, *renderables)` mirroring
`CardPart`, and give `CardPart` an optional `blocks: tuple[BlockPart, ...]`
(defaulting to a single implicit block so every existing call site and test
keeps working). A card with ≤1 block behaves exactly as today — zero
behavioral change for Context/Summary and for single-phase Reply.

**Split point.** Split at build time, not by parsing rendered `Text`. The
follow-up loop in `_agent_display_render.py` already knows the phase structure:
emit one block per phase (leading main-agent reply = block 0 labeled with its
phase label; each monitor/gate/followup phase = one block labeled
`get_phase_label`). For the single-agent DONE/FAILED path, emit one block for
the whole `AGENT CHAT` section in v1 — *not* one block per timestamped chunk
(chunk boundaries are time-based, not semantic, and long sessions would mint
dozens of blocks). Running-agent and no-content paths emit the single implicit
block. Unstructured/special displays (clan, tribe, workflow, attempt-pinned,
hint mode) degrade to one block automatically.

**Cycling.** Mirror `cycle_card_id` with `cycle_block_id` (same wraparound
semantics, same unknown-anchor rule) in `model.py`; mirror
`cycle_focused_deck_card` → `cycle_focused_deck_block(direction)` through
`AgentDetail` → `DeckPanel` → `MainDeckView`, with new `next_deck_block` /
`prev_deck_block` actions. Block preference pins by `block_id` (extend
`DeckPanelState` with `preferred_block`, mirroring `preferred_card`) so live
follow-up appends and split/zoom/restore don't yank the view, and so
`choose_new_panel`'s duplicate-Main case can carry the block after the card.

**Rendering.** Reuse `decide_render_mode` on summed block rows with the same
`spread_max_screens` knob (Adjustment 3); reuse `main_separator_for` with the
block label for spread separators, carrying a distinct meta key
(e.g. `sase_deck_block`) alongside — not instead of — the card meta so
scroll-derived active-block detection and existing section navigation coexist;
reuse `measure_main_rows` per block (phase counts are small, so the existing
measure cache pattern holds; extend the bench in `bench_tui_jk.py` with a
block-cycling case and keep p95 < 16 ms). Paged block view swaps the single
shown block exactly like `show_card` does for cards; initial selection is the
last block for Reply, first (only) otherwise (Adjustment 1).

**Chrome.** No title-strip change. When Reply is block-paged, the subtitle
shows `‹ i/n › <phase label>`; when block-spread, separators delimit phases
(the page already looks like this — blocks just make it navigable). Help modal
+ `default_config.yml` gain the two documented, overridable bindings
(Adjustment 2).

**Cross-cutting.** Index block labels/bodies in `search_corpus.py`; make
E/clipboard and detail actions follow the focused block (they already retarget
to the focused deck panel — extend the target to include the block); keep the
`toobig` lint green by putting all new code in new modules (`blocks.py`,
`panel_blocks.py` mixin) — `panel.py` is already at the 1000-line limit per
the sase-17d close-out notes, so zero new lines there beyond a mixin include.

## 5. Reliability notes

- **Live updates.** Follow-ups arrive while Reply is open; appending a block
  must not move the user's current block (pin by id, as with cards) and must
  not flip spread→paged under them more aggressively than the existing
  hysteresis already allows for cards.
- **Empty/degenerate blocks.** `card_document` drops empty parts today; blocks
  need the same rule (a phase with no renderable output must not mint an empty
  page), applied at build time.
- **Stale tests.** sase-17d left prompt-panel tests asserting `Text`/`Group`
  where `CardPart` now flows (sase-17d notes #3, #5); block work must update
  those expectations to unwrap blocks too, not add a second layer of
  isinstance failures.
- **Terminal matrix.** The `ctrl+shift` deliverability check (§2.3) is a
  release gate, not a nice-to-have: an undeliverable primary binding strands
  users on the last block with no way back.

## 6. Verification plan (for the implementing epic)

1. Unit tests: block splitting at phase boundaries (follow-up / single /
   running / empty-traceback shapes), `cycle_block_id` wraparound + unknown
   anchor, `decide_render_mode` reuse on block rows, chronological order with
   last-block default selection.
2. `just check` green including `toobig` (new modules, not `panel.py`
   growth) and symvision.
3. Three PNG goldens mirroring the sase-17d.8 spread trio: block-spread Reply,
   block-paged Reply on the last block, and a mid-cycle block — generated with
   `just fix-tui-screenshots` and visually inspected.
4. Live `sase screenshot` captures of a multi-follow-up agent: spread Reply,
   paged Reply (last block first), one `ctrl+shift+j` step; inspect separator
   styling and the subtitle block indicator.
5. `SASE_TUI_PERF=1` bench for block cycling in SINGLE and split layouts,
   before/after p95 recorded.
6. Key-delivery matrix: confirm `ctrl+shift+j/k` arrives distinctly (and the
   fallback works) in every supported terminal before close.

## 7. Recommended solution (summary)

Build card blocks as a strict one-level-down generalization of the deck
system, Reply-card-only, with: `BlockPart` + optional `CardPart.blocks`
(single implicit block = today's behavior); build-time phase-boundary
splitting (one block per shell phase; single-agent `AGENT CHAT` stays one
block); chronological storage with last-block initial selection instead of
reversal; the shared `spread_max_screens` threshold and shared
spread/paged/cycling/separator machinery; `ctrl+shift+j/k` primary bindings
with a plain-terminal fallback, both overridable and help-documented; block
position shown in the subtitle line, never as a second tab strip; block
preference pinned by stable id in `DeckPanelState`; and all new code in new
modules to respect the `panel.py` size limit. Verify with unit tests, PNG
goldens, live screenshots, perf bench, and a terminal key-delivery matrix.
