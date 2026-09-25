# Agent Data Card Blocks: Design Research and Recommendation

- **Researcher:** cdx
- **Date:** 2026-09-25
- **Primary repository state:** `sase` at `8fd6a054fd`
- **Context:** epic `sase-17d`, its accepted deck/card plan, the current implementation,
  tests, visual goldens, and a bounded snapshot of recent agent sessions
- **Scope:** presentation-only Agents-tab behavior; no `sase-core` change is warranted

## 0. Verdict

Build card blocks, but constrain them to **one structural level inside a card**. This is
the right abstraction for a session Reply: making every shell a top-level card would
overload the Main deck, while leaving the Reply as an undifferentiated transcript makes
the final result unnecessarily hard to reach.

The strongest design is:

1. A card may own an ordered tuple of typed blocks. V1 uses this only for an agent
   session's Reply card, with one block per row returned by
   `concrete_agent_session_shell_rows()`.
2. Reply blocks are presented **newest first in both modes**. The current/final shell is
   block 1; “next block” moves to the second-newest shell. Keeping one order in both
   modes avoids reversing the meaning of navigation when a resize changes modes.
3. Blocks use the same spread/paged policy and the existing
   `ace.agent_decks.spread_max_screens` setting. Do not add a second threshold until
   users demonstrate a need to tune the two levels independently.
4. Resolve block mode first, project each card to what it will actually show, and then
   resolve deck mode. This permits the most useful composition: Context plus the latest
   Reply block can remain visible as a deck spread even when the full Reply history is
   large.
5. Keep a **single `VerticalScroll`**. Blocks are Rich document structure plus anchors,
   not nested Textual scroll widgets and not miniature DeckPanels.
6. Do not persist a shell/block identity across application restarts or across node
   changes. Preserve it for the same subject, panel, and card; otherwise default to the
   newest block.
7. **Adjust the requested default keys.** Use `Alt+J` / `Alt+K` for next/previous block.
   On the current client chain, `Ctrl+Shift+J/K` cannot be distinguished reliably from
   `Ctrl+J/K`; pressing the requested shortcut can invoke card navigation instead.
   Keep the action configurable so a user with end-to-end enhanced-key support may bind
   `Ctrl+Shift+J/K` explicitly.

The idea is good. Its main danger is not the extra model type; it is accidental creation
of a recursive UI with nested scrolling, duplicated mode logic, and unstable live
selection. The design below avoids that.

## 1. What the current implementation already gives us

The deck epic has landed most of the necessary substrate:

- `widgets/decks/card_part.py` defines transparent, ordered `CardPart` wrappers.
- `MainDeckDocument` carries cards, subject identity, partial/full state, and a digest.
- `DeckPanel` and `MainDeckView` implement per-panel active cards, spread/paged mode,
  scroll-derived active-card tracking, transition anchoring, and bottom pinning.
- `_CardSeparator` places hidden `sase_deck_card=<id>` metadata into Rich segments.
  `SectionTrackingVisual` turns those markers into cached row anchors.
- `decide_render_mode()` already provides viewport-relative thresholds, a 10%
  hysteresis band, unknown-size behavior, and a `0` means always-paged policy.
- `measure_main_rows()` uses a cheap lower bound before exact Rich measurement and
  caches exact heights by digest and width.
- Each pre-composed panel has independent widget and scroll state, which is exactly what
  side-by-side comparison of different Reply blocks needs.
- The keymap pipeline is explicit: config, typed `AppKeymaps`, binding metadata,
  fallback bindings, availability, command palette, help, contextual duplicates, and
  tests.

This is a strong fit. Card blocks should extend these seams, not create a second panel
system.

### 1.1 The Reply is already structurally assembled per shell

`_agent_display_agent_session_render.py` gets the causal shell sequence from
`agent_session_shell_rows()` and appends one phase at a time:

- agent shells receive an `AGENT (<role>)` divider and their reply content;
- monitor shells use `build_monitor_phase()`;
- gate shells use `build_gate_phase()`;
- empty/running shells still receive a visible placeholder.

The source sequence is not a trivial timestamp sort. In
`models/agent_session_members.py`, `concrete_agent_session_shell_rows()` is cycle-safe,
identity-deduplicated, and inserts monitor/gate shells immediately after their causal
starter. That is the authoritative order. The block implementation should call it once
and reverse the resulting tuple; it should not reconstruct ancestry, sort timestamps,
or parse rendered `AGENT CHAT` headings.

One terminology correction is important: a session container currently has one
`AGENT REPLY · N` heading and per-shell `AGENT (...)`, `MONITOR`, or `GATE` phase
dividers. A selected completed shell may say `AGENT CHAT`, but the aggregate does not
literally contain one `AGENT CHAT` heading per shell. The requirement should therefore
be implemented semantically as **one block per concrete sase shell**, not by searching
for a literal heading string.

### 1.2 The use case is common enough to justify a real abstraction

A bounded `sase agent list -a -j` snapshot on 2026-09-25 contained 16 visible sessions
and 38 session rows. The command caps recent completed history, so this is directional,
not a population estimate:

| Shells visible per session | Sessions |
|---:|---:|
| 1 | 4 |
| 2 | 7 |
| 3 | 4 |
| 8 | 1 |

Twelve of sixteen sessions were multi-shell. Counting the larger of `live_reply.md`
and `response.md` for each row as a conservative source-line lower bound, non-empty
blocks had p50/p75/p90 sizes of 29/47/114 lines (maximum 756). Across the twelve
multi-shell sessions, merged lower bounds ranged from 6 to 678 lines, with median 58
and p75 122. Wrapping, dividers, monitor/gate fields, and card preamble make rendered
heights larger.

Both modes will therefore occur in routine use. This is not a feature where a static
“show every section” implementation will be sufficient.

### 1.3 Existing visuals argue against putting a third tab strip in the border

The current wide single-panel golden has enough room for `MAIN | Context | Reply 1/2`.
In a left/right split the title already degrades to a micro `MAIN 1/2` form. Adding all
block labels to the border would either crowd out the card identity or disappear at the
exact widths where navigation context matters most.

Blocks should therefore have an **in-content rail/header**, while the existing card tab
may add only a compact position suffix such as `Reply · 1/4` when space allows.

## 2. Critique of the proposed requirements

### 2.1 What is right

- A Reply is a meaningful unit, but a multi-shell Reply has meaningful internal
  boundaries. Card blocks express both truths.
- Spread for short content and paging for long content is already familiar in this UI.
- Latest-first access matches the dominant question after a session finishes: “what was
  the outcome?”
- A separate navigation chord preserves the established hierarchy:
  deck (`Ctrl+N/P`) → card (`Ctrl+J/K`) → block (new keys).
- The abstraction can later support other genuinely segmented cards without changing
  the deck model.

### 2.2 Where I would adjust it

| Proposed requirement | Recommended adjustment | Reason |
|---|---|---|
| New `Ctrl+Shift+J/K` defaults | Default to `Alt+J/K`; leave `Ctrl+Shift+J/K` configurable for enhanced-key environments | The current tmux chain collapses the requested chords into the existing `Ctrl+J/K` card actions. Wrong navigation is worse than an unavailable shortcut. |
| Final block first when paged | Make Reply blocks newest-first in **both** spread and paged modes | Otherwise resize can invert visual order and the meaning of “next.” With newest first, next naturally moves down/older. |
| A configurable block threshold | Reuse `ace.agent_decks.spread_max_screens` in v1 | One mental model and no speculative knob. The existing value is already cached, typed, documented, schema-checked, and supports `0`. |
| Blocks “work like decks” | Reuse pure sequence/mode/anchor primitives, but do **not** recursively mount a deck or scroll container | Recursive panels would create focus, scrolling, search, pinning, and resize conflicts. |
| Split the Reply's `AGENT CHAT` subsections | Split from the shell model before rendering, using `concrete_agent_session_shell_rows()` | Literal headings differ by shell kind and aggregate path. Parsing Rich output would be brittle and lose durable identity. |
| Reverse card blocks | Reverse only Reply's producer order; keep the generic block model order-neutral | Newest-first is a Reply policy, not a universal rule for every future blocked card. |

### 2.3 Key feasibility is a load-bearing issue

The current environment reports:

```text
TERM=tmux-256color
TERM_PROGRAM=tmux
tmux extended-keys: off
tmux client: xterm-kitty (no extkeys feature)
```

Legacy terminal encoding cannot reliably distinguish `Ctrl+Shift+letter` from
`Ctrl+letter`. The [kitty keyboard protocol](https://sw.kovidgoyal.net/kitty/keyboard-protocol/)
exists specifically to disambiguate modifier combinations; Textual supports that
protocol, but every link in the terminal/tmux chain must preserve it. In the present
chain, `Ctrl+Shift+J` can arrive as `Ctrl+J`, selecting the next **card**, and
`Ctrl+Shift+K` can arrive as `Ctrl+K`.

`Alt+J/K` is currently unused in SASE and has a legacy representation (`ESC` plus the
letter) that tmux and Textual can distinguish. The new actions should still be named
`next_card_block` / `prev_card_block`, with ordinary user-configurable bindings. If the
owner later enables and verifies extended keys end to end, the desired chords can be a
local override. I would not make application correctness depend on that host setting.

### 2.4 Alternatives considered

| Alternative | Assessment |
|---|---|
| Make each shell output a Main-deck card | Reject. Context plus an 8-shell session becomes nine card tabs; sticky Reply semantics disappear and narrow titles become opaque. |
| Add a Conversation deck with one card per shell | Plausible, but worse for the first use case. It adds a fourth deck and makes Context + latest output require a split or deck switch. |
| Keep one Reply and add phase-header jumps only | Too small. It improves navigation but cannot page large merged replies or keep the final output isolated. |
| Mount a DeckPanel inside Reply | Reject. Nested focus and nested scrolling will be confusing and fragile. |
| General recursive “content nodes” of unlimited depth | Reject. This is mechanism ahead of need. Enforce exactly deck → card → optional block. |

## 3. Recommended UX contract

### 3.1 Definitions and invariants

- A **card block** is one titled, stably identified content unit inside an agent data
  card.
- A card has either no explicit blocks or one ordered block sequence. Blocks never own
  child blocks.
- Block ids are unique within their card and are data identity, not display labels.
- A single-block card is structurally valid but has trivial spread behavior; cycling is
  a no-op.
- Card-wide preamble may appear before the sequence. For Reply this includes the
  `AGENT REPLY · N` heading and any card-level traceback treatment.
- Block navigation acts on the **focused deck panel's active card**. If that card has
  fewer than two blocks, it does nothing.
- Block state is panel-local. Two Main panels may intentionally show different shell
  outputs from the same session.

### 3.2 Reply order and initial selection

The session projection remains causally ordered internally, then the Reply builder
reverses it exactly once:

```text
source shell order:  plan → monitor → code → finalizer
Reply block order:   finalizer → code → monitor → plan
navigation:          1/4      → 2/4  → 3/4    → 4/4
```

For an active session, label the first block **current**, not final. Once terminal, it
may be labeled **final**. `next_card_block` moves toward older work; previous moves
toward newer work. Both wrap, matching card navigation.

This order should apply to spread too. A newest-first transcript is less conventional
than a chat log, but it is the only order that simultaneously satisfies “final first,”
keeps `J` visually downward, and remains stable across mode changes.

### 3.3 Spread and paged behavior

Use the current `decide_render_mode()` semantics (including 10% hysteresis), generalized
from “card sequence” to “item sequence”:

- 0 or 1 block: trivial spread.
- More than one block and threshold `0`: paged.
- Unknown size on a new subject: paged until known.
- Otherwise compare merged block rows with
  `spread_max_screens × viewport_rows`.
- On same-subject changes, retain the previous mode inside the hysteresis band.

In **block spread**:

- render every block newest-first in the card;
- show a visible header for every block, including the first;
- derive the active block from the last block anchor at or above `scroll_y`;
- next/previous scroll that block header to the top;
- use the existing trailing layout reserve so the oldest/final visible anchor can reach
  the top.

In **block paged**:

- render the card preamble plus only the active block;
- default to the newest block;
- next/previous swaps the block body and resets to its top;
- preserve bottom pin only when it belonged to the active block.

### 3.4 Resolve nested modes from the inside out

This is the most important interaction rule:

```text
full CardPart
  └─ decide each card's block mode from all of that card's blocks
       └─ project the card (all blocks, or its active block)
            └─ decide deck mode from the projected cards
                 └─ paint one flat document in one VerticalScroll
```

Do **not** make the outer deck measure hidden paged blocks. If a session has 600 lines
across six blocks but its latest block is 25 lines, the Reply can page internally while
the Main deck still spreads Context plus that 25-line result. This is the useful form of
progressive disclosure; forcing the outer deck to page because of invisible history
would create unnecessary double pagination.

There is no circular dependency: both levels use the same panel viewport, block mode is
decided first, and only its projection affects deck measurement.

### 3.5 Visual design

Keep the existing border hierarchy clean:

```text
╭─ ◆ MAIN ┃ Context │ Reply · 1/4 ─────────────────────────╮
│ AGENT REPLY · 4                         newest first      │
│ ━━ ◆ 1/4 · final · AGENT (code) · 14:23:45 ━━━━━━━━━━━━ │
│                                                          │
│ Final response content…                                  │
╰─ spread  main 2 · files 1 · tools 1 ─────────────────────╯
```

Guidelines:

- The border continues to identify deck and card. It never lists all block labels.
- A block header is a full-width rule derived from today's phase divider. It carries
  position, current/final state, shell kind/role, and time.
- Use the shell-kind glyph/accent already established for monitor and gate phases; use
  the Main accent for agent shells. Do not add another boxed panel.
- The first block gets a real header and hidden anchor; unlike first cards, it should
  not rely on an implicit row-zero anchor because Reply has preamble.
- Add `· 1/4` to the active Reply tab only when it fits. Compact/micro border tiers may
  omit it because the in-content header remains authoritative.
- The footer shows `Alt+J/Alt+K blocks` only when the focused active card has multiple
  blocks. Help and the command palette always document the action.
- If the reader stays on an older block while a new shell arrives, show a restrained
  `1 newer` marker rather than moving them.

### 3.6 Live-update selection rules

Track a small per-panel, per-card cursor with both identity and intent:

```python
@dataclass(frozen=True, slots=True)
class BlockCursor:
    block_id: str | None
    follow_newest: bool = True
```

Rules:

1. New subject or card with no cursor: select the first block (newest) and follow it.
2. Same subject, content update in the active block: preserve block and scroll offset;
   if bottom-pinned, remain pinned.
3. A new shell appears while following newest: select the new first block.
4. A new shell appears while reading an older block: preserve that stable block id and
   show `1 newer`.
5. Explicitly navigating to the newest block re-enables follow-newest; navigating away
   disables it.
6. If the chosen block disappears, fall back to newest.
7. A partial/cheap document never settles a new block mode and never clears a
   same-subject cursor merely because a block is temporarily missing.

This avoids the two worst streaming failures: yanking a reader out of history, and
leaving a user on what used to be “index 0” after a new latest block is prepended.

### 3.7 Transition anchoring

The current deck transition stores a card and row offset. Blocks require one explicit
hierarchical reading anchor:

```python
@dataclass(frozen=True, slots=True)
class MainReadingAnchor:
    card_id: str | None
    block_id: str | None
    offset_rows: int
    pinned_to_bottom: bool
```

Capture it before block-mode, deck-mode, geometry, hint-mode, or theme recomposition;
restore after paint. The most specific surviving identity wins:

1. same block + offset;
2. same card + top;
3. card default;
4. document default.

This should replace ad hoc nested transition branches rather than adding another layer
of callbacks around `_apply_main_transition()`.

## 4. Recommended data and rendering architecture

### 4.1 Data model

Add a transparent `CardBlock` beside `CardPart`, but make blocks explicit fields rather
than indistinguishable children:

```python
@dataclass(frozen=True, slots=True)
class CardBlock:
    block_id: str
    title: str
    renderables: tuple[RenderableType, ...]

@dataclass(frozen=True, slots=True)
class CardPart:
    card_id: str
    title: str
    preamble: tuple[RenderableType, ...] = ()
    blocks: tuple[CardBlock, ...] = ()
    renderables: tuple[RenderableType, ...] = ()  # unblocked-card body
```

The exact constructor can preserve today's positional API, but the invariant should be
clear: an unblocked card has `renderables`; a blocked card has `preamble + blocks`.
Avoid a loose mixed tuple that callers must scan and validate on every render.

Required invariants:

- no empty `block_id`;
- no duplicate block ids within a card;
- deterministic order;
- digest includes card id/title, block id/title/order, preamble, and bodies;
- transparent full-document rendering remains segment-equivalent where no block mode
  projection is active.

The generic model does not contain “newest.” The session Reply producer passes reversed
blocks. Other cards may later use chronological or domain-specific order.

### 4.2 Build blocks at the phase assembly seam

Refactor `_update_agent_session_display()` so each loop iteration returns one block:

```python
def build_session_reply_block(phase: Agent, ...) -> CardBlock:
    # agent / monitor / gate body, plus a standardized marked phase divider
```

Use a stable id derived from the full `Agent.identity` tuple, not the role label or
position. Labels are not unique (multiple monitors and feedback rounds are common), and
positions change when a new shell arrives.

Keep these semantics inside the block:

- timestamped chunks remain within their shell block;
- monitor fields and captured output stay together;
- gate decision fields and execution output stay together;
- “No response content yet” is a real block body;
- attempt substructure stays inside its shell block; do not introduce block nesting.

The card-level traceback and `AGENT REPLY · N` preamble remain outside the sequence.
If later evidence shows a traceback belongs unambiguously to one shell, it can move into
that block without changing the block API.

`_agent_display_agent_session_render.py` is already 432 lines, near the project's
500-line target. Put block/phase assembly in a new cohesive module rather than growing
it. Likewise, `widgets/decks/panel.py` is 735 lines; block behavior belongs in a
`panel_blocks.py` mixin or in `MainDeckView`, not in that file.

### 4.3 Generalize primitives, not widgets

Extract or add these pure helpers:

- `cycle_item_id(ids, active, direction, default_id)`; keep `cycle_card_id()` as a
  compatibility wrapper if useful;
- `decide_sequence_render_mode(item_count, ...)`; cards and blocks call the same pure
  policy;
- exact/lower-bound sequence measurement with a caller-supplied digest namespace;
- `resolve_active_block()` with partial-document behavior;
- block projection into a renderable card plan.

Do not make `DeckPanel` recursive. `MainDeckView` remains the only Static inside the
Main scroll and paints a flat Rich `Group` from a pure render plan.

### 4.4 Add a distinct anchor role

Extend the existing section tracker with:

```text
metadata key: sase_card_block
anchor role:  BLOCK
identity:     block:<card-id>:<block-id>
```

Add `block_anchor_rows(card_id, width)` alongside `card_anchor_rows()`. Card active
tracking ignores block anchors; legacy section navigation ignores both card and block
anchors; layout reserve considers block anchors so the final target can top-align.

The block header should own the marker. Do not attach it to arbitrary reply text: the
header is always present, and measuring it gives an exact stable boundary.

### 4.5 Render-plan state belongs in the view, not persisted layout

Keep `DeckAreaState.preferred_card`; do not add a raw shell id to
`ace_agents_deck_state.json`. A shell identity is subject-specific, often short-lived,
and meaningless after switching nodes or restarting days later. Persisting it would
require a schema migration and would usually fall back immediately.

Instead, each pre-composed `MainDeckView` owns ephemeral state for its current subject:

- active block per blocked card;
- follow-newest flag;
- previous block render mode per card;
- pending spread target;
- hierarchical reading anchor.

This state naturally survives deck switches, split rotation, and zoom because the
widgets stay mounted. It resets on a subject/attempt change.

### 4.6 Preserve whole-card semantics outside navigation

Blocks are a presentation/navigation layer, not data loss:

- search corpus includes every block title and body, including paged-hidden blocks;
- `V`/pager export of Reply remains the whole Reply card in its defined newest-first
  order;
- file-hint numbering remains computed over the full card document so it does not
  renumber while cycling;
- digest and availability count the full card;
- clipboard/editor actions keep their current card-wide meaning unless a future
  explicit “copy block” command is added.

The current hint cache wraps each card's entire children in one `CachedRenderable`,
which would erase block structure. Update `_prepare_cached_hint_renderable()` to retain
`CardBlock` wrappers and cache preamble and each block body separately. Also update:

- `renderable_content_digest()`;
- lower-bound measurement traversal;
- `flatten_card_document()` and other transparent tree walkers;
- search-corpus rendering;
- test renderable walkers and metadata helpers.

### 4.7 Performance contract

Block navigation must be a pure in-memory keystroke path:

- no file reads, stats, globs, subprocesses, or JSON parsing;
- no Main-source rebuild merely to select another block;
- large merged replies exit measurement through the cheap lower bound;
- exact block height is cached by `(block digest, width)`;
- active block derivation uses the already-published anchor cache;
- geometry/stream refreshes reuse the existing coalescing path;
- UI mutations and scroll restores remain thin `call_after_refresh` callbacks.

Measure `Alt+J/K` alongside the existing j/k benchmark. The same p95 < 16 ms target is
appropriate.

## 5. Implementation surfaces

### 5.1 Core deck/render files

Likely changes:

- `widgets/decks/card_part.py` — block model, validation, flattening helpers.
- `widgets/decks/main_document.py` — block-aware accessors/render plan inputs.
- `widgets/decks/render_mode.py` — generic sequence policy and block measurement.
- `widgets/decks/main_view.py` — projection, active block, anchors, and scroll target.
- new `widgets/decks/panel_blocks.py` — per-panel block mode/cursor orchestration.
- `widgets/decks/panel_spread.py` — call the projected-card measurement path.
- `widgets/decks/panel_chrome.py` and `titles.py` — compact `Reply · n/N` state.
- `widgets/decks/separators.py` — marked block header/rule.
- `widgets/prompt_panel/_section_navigation.py` and `_section_view.py` — BLOCK role.
- `util/renderable_digest.py`, search corpus, hint caches, and transparent tree walkers.

Keep `DeckPanel`'s public API stable where possible and delegate to the new mixin.

### 5.2 Reply producer files

- Factor session phase/block assembly out of
  `_agent_display_agent_session_render.py`.
- Reuse `concrete_agent_session_shell_rows()`; reverse only at Reply construction.
- Let monitor/gate builders return bodies or accept a standardized marked divider so a
  block never gets two headers.
- Update hint-mode assembly through the same structural helper. Do not maintain a flat
  hint-only Reply path with independently inferred boundaries.

V1 should not retrofit blocks onto regular one-shell Reply/Output cards unless doing so
falls out for free. The abstraction should support them, but the UI only needs block
controls for the session Reply use case.

### 5.3 Keymap and command plumbing

Add `next_card_block` and `prev_card_block` everywhere the deck actions already appear:

- `src/sase/default_config.yml` (**required core gotcha**), defaults `alt+j` / `alt+k`;
- `AppKeymaps`;
- `_BINDING_META`;
- fallback `bindings.py`;
- app action availability and prompt-input ownership;
- command metadata/availability;
- Agents help row;
- conditional footer entry;
- committed-search structural exit keys;
- keymap/catalog/default/fallback-parity tests.

No contextual-duplicate entries are currently needed for `Alt+J/K`, because repository
search found no existing owners. Recheck at implementation time.

### 5.4 Config and documentation

Reuse `ace.agent_decks.spread_max_screens`; document that it controls both deck-card
and card-block sequences. Its existing `0` behavior applies to both.

Add/update:

- the Agent Data Card glossary strand to define optional blocks;
- a new Agent Data Card Block glossary strand;
- `docs/ace.md` hierarchy, newest-first Reply policy, modes, and keys;
- `docs/configuration.md` action ids and the expanded threshold meaning;
- help and command-palette descriptions.

No feature flag is necessary if the work lands behind complete tests in one coherent
epic, but staged commits should preserve a usable UI throughout.

## 6. Required behavior and edge cases

The implementation contract should explicitly cover:

1. **Zero blocks:** render card preamble/body normally; block keys no-op.
2. **One block:** trivial spread; no footer hint or distracting `1/1` unless the shell
   header already benefits from it.
3. **Many blocks:** unique ids, newest-first order, wrapping navigation.
4. **Empty current shell:** newest block still appears with its running/waiting state.
5. **Monitor/gate blocks:** structured fields and output remain in one block.
6. **Duplicate roles:** ids remain unique when labels repeat (`--mon`, `--mon-0`, etc.).
7. **Streaming newest block:** content updates do not reset scroll unless bottom-pinned.
8. **New shell arrival:** follow-newest versus preserve-older behavior from §3.6.
9. **Partial document:** does not collapse selection or decide a new mode.
10. **Resize/split/ratio/header/jump toggles:** preserve card, block, and offset.
11. **Deck spread + block paged:** Context and active Reply block can coexist.
12. **Deck paged + block spread:** Reply shows all short blocks when the projected Reply
    itself is the active deck page.
13. **Two Main panels:** independent block cursors and scroll positions.
14. **Search/hints/pager:** see the complete card, not only the visible page.
15. **Tiny width:** block header truncates safely; position survives even when title is
    omitted.
16. **Prompt input/search overlay:** owns keys exactly as today; block bindings do not
    leak through.
17. **Unsupported enhanced keys:** default navigation still works via `Alt+J/K`.

## 7. Verification plan

### 7.1 Pure tests

- `CardBlock` construction, uniqueness, flattening, and segment equivalence.
- Digest changes for block identity, title, body, and order.
- Generic mode boundaries, hysteresis, threshold `0`, unknown total, and partial state.
- Newest-first cycle and wrap behavior.
- Follow-newest reconciliation when a block is prepended.
- Projected-card measurement: hidden paged blocks must not force outer deck paging.
- BLOCK anchor extraction; card/section resolvers must ignore it where appropriate.
- Layout reserve includes the final block anchor.

### 7.2 Builder tests

- A plan → monitor → code → gate session yields gate/code/monitor/plan blocks.
- Every block preserves the exact content previously rendered by its phase.
- Repeated monitors/gates get unique stable ids.
- Empty and running phases stay visible.
- Traceback and `AGENT REPLY · N` remain in card preamble.
- Hint-mode output has identical block boundaries and continuous stable hint numbering.

### 7.3 Pilot/integration tests

- Start on latest paged block; next goes to second-latest; previous returns.
- Spread navigation scrolls the requested block header to the top.
- Manual scroll updates active block and compact `n/N` chrome.
- New shell auto-follows only when `follow_newest` is true.
- A reader on an older block is not moved when a shell or output update lands.
- Block and deck mode transitions preserve hierarchical offsets.
- Split panels compare different blocks without cross-talk.
- Card/deck/block keys target only the focused panel.
- Search overlay structural keys close/route consistently.
- `Alt+J/K` is exercised through the public Textual pilot path.

### 7.4 Visual coverage

Add and inspect at least:

- paged Reply on latest/final block;
- paged Reply after moving to the second-latest block;
- spread Reply with three shell kinds newest-first;
- Context + internally paged Reply in an outer Main spread;
- two Main panels showing different Reply blocks;
- narrow left/right micro chrome;
- live session with `current` and `1 newer` states.

### 7.5 Performance

- Benchmark block cycling on a session with many small blocks and one with very large
  outputs.
- Record p50/p95/max and keep p95 under 16 ms.
- Confirm no disk reads occur on a block-cycle keypress.
- Verify large merged replies exit through lower-bound measurement rather than exact
  rendering of every block.

## 8. Suggested delivery sequence

1. **Structure:** add `CardBlock`, block-aware digest/flatten/cache/search helpers, and
   session Reply construction. Preserve the current full flattened appearance.
2. **Projection:** add block render planning, mode decision, anchors, and hierarchical
   transition state without keys.
3. **Interaction:** add `Alt+J/K`, active chrome, footer/help/palette, panel-local state,
   and live follow-newest behavior.
4. **Polish and proof:** visual goldens, live screenshots, performance benchmark, docs,
   and glossary.

This sequence keeps every step reviewable and avoids combining builder correctness with
keymap and visual debugging.

## 9. Recommended solution

Implement **one-level, presentation-only CardBlocks** inside `CardPart`. Build the agent
session Reply as one card-level preamble plus one block per concrete sase shell, using
the existing causal shell projection and reversing it once so the current/final shell is
first. Render blocks newest-first in both modes. Decide block spread/paged mode with the
existing 1.5-screen configuration and hysteresis, project the card, then decide the
outer deck mode from that projection. Paint everything in the existing single scroll
with a new BLOCK anchor role; never nest a DeckPanel or scroll container.

Keep block selection ephemeral and panel-local, preserve it by stable shell identity for
same-subject updates, and explicitly distinguish “follow newest” from “reading older.”
Use an in-content phase-style block rail, a compact `Reply · n/N` suffix when space
permits, and conditional footer help.

Finally, change the requested default shortcut to **`Alt+J/K`**. The requested
`Ctrl+Shift+J/K` is a good conceptual chord but is unsafe on the owner's current tmux
chain because it aliases the already-bound card keys. Expose normal configurable action
ids so it can be rebound after enhanced-key support is enabled and verified end to end.

With those adjustments, card blocks are an intuitive extension of the deck/card model,
solve a frequent real navigation problem, preserve the TUI's performance constraints,
and create a clean reusable primitive without turning the Agents detail area into a
recursive UI framework.
