# Agent Data Card Blocks: Consolidated Design Research and Recommendation

- **Lead:** consolidated from four independent reports
  ([cdx](agent_data_card_blocks__cdx.md), [cld](agent_data_card_blocks__cld.md),
  [mus](agent_data_card_blocks__mus.md), [gem](agent_data_card_blocks__gem.md)), plus the
  lead's own verification against `sase` at `245dcb553`
- **Date:** 2026-09-25
- **Context:** epic `sase-17d` (agent data decks and cards; phases .1–.11 closed, child
  epic `sase-17d.12` in progress) and the shipped code under
  `src/sase/ace/tui/widgets/decks/`
- **Scope:** presentation-only Agents-tab behavior. No `sase-core` change and no
  `sase-core-revision.txt` bump. If a web or editor frontend ever needs the same
  "session timeline" (shell order, labels, statuses), move the roster adapter into
  `sase_core`, not the blocks.

## 0. Bottom line

**Build it.** All four researchers agree, and the lead's checks back them up. The Reply
card of a multi-shell agent session is the worst reading experience left in the deck
design. What you almost always want is the newest shell's output (the current state or
the final result), and today it is the most expensive thing to reach: a paged Reply opens
on the *oldest* shell, and the newest one sits one to twenty screens below. Card blocks
add a third level, **deck → card → block**, that fixes this. The sticky Reply card and
the deck model stay as they are.

The requirements need five adjustments, one of them mandatory:

| # | Your requirement | Adjustment | Strength |
|---|---|---|---|
| A1 | `Ctrl+Shift+J/K` cycle blocks | **`[` (older) / `]` (newer)** as defaults. `Ctrl+Shift+J/K` remains a user override for setups that verifiably deliver it. | **Mandatory.** On your tmux 3.5a chain, `Ctrl+Shift+J/K` arrives as `Ctrl+J/K`, even with `extended-keys always` + `csi-u`. Pressing it would **cycle cards, not blocks.** Two independent probes confirm this (§1.4). |
| A2 | Reverse the Reply's block order | **Keep blocks chronological, land on the newest block, and make `[` step back.** The first screen is the same, and the first keypress still reaches the second-to-last shell. The content is never reordered. | Strong recommendation. If you insist on reversal, reverse in *both* modes; never do it asymmetrically (§3.2). |
| A3 | Spread by default, paged past a configurable threshold | Keep it, plus one invariant: **a card pages its blocks only when it is shown alone.** A spread deck always spreads its blocks. The threshold is its own key, `ace.agent_decks.block_spread_max_screens` (default `1.5`, `0` = always one block per page). | Strong (§3.3, §3.4). |
| A4 | (unspecified) | **A one-row block rail**: a left-to-right timeline of the card's blocks, drawn in the JUMP roster's vocabulary and shown whenever blocks are navigable. | This is where most of the "beautiful" and "intuitive" comes from (§3.5). |
| A5 | "one block per `AGENT CHAT` sub-section" | **One block per concrete sase shell**, taken from the shell model (`concrete_agent_session_shell_rows()`), never parsed from headings. `AGENT CHAT` is the single-agent heading. A session Reply is `AGENT REPLY · N` plus one phase divider per shell. | Terminology and robustness fix (§1.2). |

There is also a cosmetic fix: **remove the vestigial "blank + dim 50-column rule + blank"
prefix** that opens every Reply card. It is a leftover from the single-document era. In
spread mode it doubles the new `━━ ◆ Reply ━━` separator, and in paged mode it wastes
three rows.

## 1. Evidence base

### 1.1 The substrate already exists

The sase-17d work landed nearly everything blocks need:

- `CardPart` (`card_part.py`) is a **transparent** Rich wrapper. Rendering it is
  identical to rendering its children, and walkers descend it through the
  `__sase_card_part__` marker. A `CardBlock` can follow the same pattern exactly.
- `decide_render_mode()` (`render_mode.py`) is pure, has 10% hysteresis, treats `0` as
  always-paged, and does not care how many items it is deciding over.
- `measure_main_rows()` computes a cheap lower bound with early exit, then an exact
  measurement cached by `(digest:card, width)`.
- Anchors: `Style(meta={"sase_deck_card": id})` publishes a `CARD` anchor through
  `SectionTrackingVisual`. Spread-mode `Ctrl+J/K` and the title's active-card pill both
  run on these anchors, so a `BLOCK` role is a one-enum-member extension.
- Each `DeckPanel` owns its own render mode, active card and scroll. `DeckAreaState`
  keeps the sticky preferred card. A spread deck on a new subject scrolls to the
  preferred card (`panel.py:372`), so a sticky Reply already lands on Reply.
- The keymap pipeline is explicit, and it already supports **tab-disjoint shared keys**
  (`_CONTEXTUAL_APP_DUPLICATES`, `keymaps/registry.py:101`).

### 1.2 How the Reply is built today

A session container is a root entry with at least one follow-up
(`Agent.is_agent_session_container_row`), so in practice it has two or more shells. Its
Main document comes from `_update_agent_session_display()`:

```text
context_card(header_text, prompt…)
reply_card(
    *traceback_parts,                      # card-level TRACEBACK
    reply_header,                          # "\n" + dim 50-col rule + "\n" + "AGENT REPLY · N"
    # one phase per shell from concrete_agent_session_shell_rows(), causal order:
    render_phase_divider("AGENT (plan)", t0), *timestamped chunks…,
    *build_gate_phase(gate),               # "─── ⋔ GATE ─── t1 ───" + fields + log
    *build_monitor_phase(mon),             # "─── ⚙ MONITOR ─── t2 ───" + fields + log
    render_phase_divider("AGENT (code)", t3), *chunks… | "No response content yet.",
)
```

Facts that shape the design:

- **The split points already exist.** They are the phase dividers, and they already look
  like block headers. No new separator style is needed.
- **The shell order is authoritative and non-trivial.** It is cycle-safe,
  identity-deduplicated, and places each monitor or gate right after the shell that
  started it. Blocks must call this projection, not sort by timestamp or parse rendered
  text.
- **`agent_session_roster_entries()` is built from the same shell list.** It supplies
  the JUMP roster's number, label, glyph and status bucket, so a block rail built from it
  matches the roster by construction.
- **Hint numbering is assigned during this chronological loop.** It uses a shared
  `hint_budget` and `hint_state.hint_counter`. This matters for the ordering decision
  (§3.2).
- **There are three assembly sites, not one.** They are (1) the session loop above, which
  serves both hint and non-hint modes; (2) the legacy `followup_agents` branch in
  `_agent_display_render.py:461-500`, used by non-session roots with follow-ups; and (3)
  that branch's hint twin in `_agent_display_hint_body.py:117-165`. The hint twin builds
  **one flat `Text`**, so it must be split per phase. It also has **no `is_gate`
  branch**, so in hint mode gates render as agent phases. That divergence already exists
  today.
- Single agents (`AGENT CHAT` plus per-turn timestamp dividers), proc shells, monitors,
  gates, workflow steps and clan/tribe Summary cards **do not get blocks in v1**. Turn
  timestamps are time-based rather than semantic, and would mint dozens of blocks.

### 1.3 How big session Replies get

cld scanned 1,308 `agent_meta.json` files (70 sessions, 2026-09-20 to 25). The figures
are lower bounds, because monitor logs and wrapping are excluded:

| Metric | p50 | p90 | max |
|---|--:|--:|--:|
| Shells per session | 3 | 5 | 15 |
| Raw reply lines per session | 72 | 738 | 14,013 |

The spread budget is 1.5 × viewport, about 60–90 rows in a single panel and 20–35 in a
split. So the **typical** session Reply is already at or past the threshold, and p90 is
10× over. Gates (58) and monitors (62) are as common as code shells (52), so they are
first-class block kinds. cdx's independent snapshot agrees: 12 of 16 sessions were
multi-shell, with block sizes of p50/p90 29/114 lines. **Both block modes will occur
routinely.**

### 1.4 Key delivery (the load-bearing finding)

The environment runs tmux 3.5a with `extended-keys off`, and the client is `xterm-kitty`
without the `extkeys` feature. The lead reran the probe on a private tmux server
(`-L cardprobe`), with a raw-mode reader in the pane:

| Key sent | `extended-keys off` | `extended-keys always` + `csi-u` |
|---|---|---|
| `C-j` / `C-S-j` | `\n` / **`\n`** | `\n` / **`\n`** |
| `C-k` / `C-S-k` | `\x0b` / **`\x0b`** | `\x0b` / **`\x0b`** |
| `C-o` / `C-S-o` | `\x0f` / **`\x0f`** | `\x0f` / **`\x0f`** |
| `M-j` / `M-k` | `\x1bj` / `\x1bk` | same |
| `[` / `]` | `[` / `]` | same |

cld's stronger test fed raw kitty-protocol bytes into a real tmux client pty with
`extkeys`. Shift+Enter and Ctrl+Enter passed through, but **Ctrl+Shift+J (`\x1b[106;6u`)
collapsed to `\n`**. No tmux configuration fixes this. kitty's defaults also bind
`kitty_mod+j/k` (that is, `ctrl+shift+j/k`) to scrolling. These pass through only off
the main screen.

Candidate keys compared:

- **`Ctrl+Shift+J/K`** fails as the *wrong action*: it cycles cards. That is the worst
  failure mode for a navigation key. mus cited `ctrl+shift+o` as precedent that it
  works, but that is a counterexample: `jump_to_entry_forward` arrives as `Ctrl+O` in
  tmux, so "forward" jumps backward (a side finding, §8).
- **`Alt+J/K`** (cdx's pick) reaches the app through tmux. tmux binds `M-j/M-k` only in
  the *prefix* table. It is fragile off-host, though: kitty on macOS types `∆`/`˚`
  unless `macos_option_as_alt` is enabled, and that is off by default.
- **`[` / `]`** are printable, so every terminal delivers them. They are free on the
  Agents tab, and the only app owners are the Artifacts-only `cycle_artifacts_subtab*`
  actions. They already mean "previous/next sub-thing" across the TUI: help tabs,
  notification tag tabs, gate-debug tabs, config and plugin sub-tabs, and the Statistics
  view. They also match an existing precedent exactly: **`{`/`}` are already
  Agents-deck-ratio vs Artifacts-split contextual duplicates.** A `[`/`]` pair for Agents
  card blocks versus Artifacts sub-tabs is the same shape.
- gem's leader `, b j/k` and `g j/k` fallbacks are rejected. They add key families, and
  `g` is already `scroll_to_top`.

### 1.5 Walker hazards

Walkers that don't know about `CardBlock` fail *silently*. The lead enumerated every
container walker in `src/`:

| Site | Today | If `CardBlock` is not taught |
|---|---|---|
| `render_mode._lower_bound_node` (`:72`) | `isinstance(node, (Group, CardPart))` | Each block counts as **1 row**. The lower-bound early exit is lost, so a 14,000-line session gets exact-rendered on every mode decision. **Perf regression.** |
| `renderable_digest._update_digest` (`:49`) | card marker branch | Falls back to `type name + repr()[:2048]`. Content changes past about 2 KB **don't change the digest**, so the digest skip hides streaming updates and ▶→✓ status changes. **Stale display.** |
| `_prepare_cached_hint_renderable` (`_agent_display_hints.py:70-100`) | wraps each card's children in one `CachedRenderable` | **Erases blocks in hint mode (`v`)**, so anchors and the rail vanish. It must cache the preamble and each block separately. |
| `_plain_renderable_content` (`_agent_display_hints.py:39`) | card marker branch | Falls back to `str(node)`. |
| `split_card_parts` / `flatten_card_document` (`card_part.py`) | card marker | `flatten` must descend blocks, and `split` must preserve them. |
| `_identity_header._find_carrier` (`:120`) | card marker | Low risk, because blocks live only in Reply, but it should use the shared helper. |

Remedy: one `is_card_container(node)` helper that returns true for either wrapper, used
by every walker. Five test files reference `CardPart`. sase-17d.2 already left `Text`/
`Group` isinstance failures behind once (epic notes #3 and #5), so grep the tests before
landing.

## 2. Is this a good idea?

**Yes.** There are four reasons:

1. **It fixes a frequent, real pain.** Section 1.3 shows both modes occurring routinely
   and the latest output buried.
2. **It composes into a triage loop.** A paged deck already keeps Reply sticky across
   `j/k`. If every node *also* lands on its newest block, `j/k` becomes one keypress per
   session to see each session's current or final shell output. This is the feature's
   best property and belongs in the docs.
3. **It is the right depth.** Paging inside a card is the deck idea one level down:
   spread when it fits, paged when it doesn't, and a key pair to step. Users learn
   nothing new.
4. **It makes `j/k` cheaper.** A block-paged Reply lays out one shell instead of a card
   of 738 to 14,000 lines.

The risks are real but manageable:

- Undeliverable keys (A1).
- A second ordering (A2).
- Incoherent nested modes (A3).
- Paging hiding context, because on block 5 you can't see that block 4 was a rejected
  gate (A4).
- Accidentally building a recursive UI with nested scroll containers.
- Scope creep ("like decks" invites Files, Tools and Summary now).
- A name collision: `command_line.block_*` already uses bare "block". Always say **card
  block**, `CardBlock`, and `next_card_block`.

### 2.1 Alternatives considered

| Alternative | Verdict |
|---|---|
| One card per shell (`Reply·plan`, `Reply·gate`, …) | **Reject.** Card ids become per-node, which breaks the sticky preferred card. It also floods the tab strip (an 8-shell session means 9 tabs) and ties deck mode to shell count. |
| A fourth "Conversation" deck | **Reject.** Context plus the latest output then needs a deck switch or a split, and it adds a deck for one use. |
| Anchors only: keep one Reply, land on the newest divider, and let `[`/`]` jump between dividers | **Good fallback / first slice.** It gives about 60–70% of the value in one small phase. It doesn't cut render cost or isolate huge outputs. It is literally the block-spread path, so no work is wasted. |
| Accordion (fold older shells) | **Reject; borrow its idea.** Folds are document-global state shared with `z…`, and 15 folded rows eat a screen. The rail *is* the folded accordion, in one row. |
| A `DeckPanel` mounted inside Reply (recursive panels) | **Reject.** Nested focus and scrolling conflict with search, pinning and resize. |
| General recursive "content nodes" | **Reject.** It builds mechanism ahead of need. Enforce exactly deck → card → optional blocks, and blocks never nest. |

## 3. Where the researchers disagreed, and the resolution

| Question | cdx | cld | mus | gem | **Resolution** |
|---|---|---|---|---|---|
| Default keys | `Alt+J/K` | `[` / `]` | `Ctrl+Shift` primary + fallback | `Ctrl+Shift` + `[`/`]` + leader + `g` | **`[` / `]`** only |
| Reply order | newest-first in both modes | chronological, land newest | chronological, land last | chronological spread, reversed paged | **chronological, land newest** |
| Nested modes | block mode first; deck measures the projection | deck spread ⇒ block spread | same as cld | same as cld | **invariant** |
| Block threshold | reuse deck knob | new key | reuse deck knob | new key | **new key, default 1.5** |
| Block chrome | in-content header + `Reply · 1/4` title suffix | docked one-row rail | subtitle `‹ i/n ›` | boxed navigator pill + title suffix | **rail** |
| Block state | ephemeral, per panel | ephemeral, per panel | `DeckPanelState.preferred_block` | `preferred_blocks` map | **ephemeral** |

### 3.1 Keys: `[` / `]`

The evidence is in §1.4. Direction: **`[` = older, `]` = newer**, and both wrap like card
cycling. On a left-to-right timeline rail, `[` literally points back in time. From the
landing (newest) block, the first `[` reaches the second-to-last shell, which is exactly
the behavior you asked for. Action ids are `prev_card_block` / `next_card_block`, in
document order. If you later run kitty outside tmux and want your original chord, bind
`prev_card_block: ctrl+shift+j` locally. Don't ship `Ctrl+Shift` in defaults or help
text, because it trains the hand to press a key that does the wrong thing inside tmux.

### 3.2 Order: chronological, land on the newest

What you want is: "I open Reply and see the latest output, and one keystroke reaches the
previous one." Chronological order plus a newest-block landing delivers exactly that, and
avoids every cost that reversal carries:

1. **One ordering everywhere.** The JUMP roster (`0 --plan`, `1 --gate`, `2 --code`), its
   digit jump keys, timestamps, `AGENT REPLY · N`, the search corpus, the `V` pager and
   `E` export are all oldest-first today.
2. **Hint numbers stay monotonic.** Hints are numbered in the chronological build loop.
   Reversing the document would either renumber them or show descending numbers.
3. **Streaming is stable.** In chronological spread, a new shell appends *below* the
   reader and nothing moves. In a reversed spread it prepends *above*, shifting the
   viewport unless extra scroll anchoring is added.
4. **Direction never flips.** gem's asymmetric model (chronological spread, reversed
   paged) makes the same key mean "newer" or "older" depending on a mode that streaming
   can change under you. cdx and cld both rejected it, and gem's own analysis flags the
   same problem.

cdx's case for newest-first in both modes was mode-stability plus "J goes visually down
to older". Chronological order is equally stable across modes, and with `[`/`]` plus a
horizontal rail there is no vertical metaphor to preserve. **What you give up:** the
spread document doesn't physically start with the final output. The landing rule makes
up for it by scrolling the newest header into view (§4.4). **If you still want literal
reversal,** apply it in both modes, add scroll anchoring for growth above the viewport,
label the card `AGENT REPLY · N · newest first`, and have the builder reverse exactly
once.

### 3.3 Nested modes: "shown alone" invariant

cdx proposed deciding each card's block mode first, projecting it (for example, Reply
becomes its newest block), and then deciding deck mode from the projection. The result
can be a spread deck showing Context plus only the newest Reply block. It is clever, but
the **deck's mode would then depend on which block is active.** A `[` from a 25-row
newest block to a 200-row gate log would flip the deck from spread to paged. The tab
strip would change and Context would vanish. `]` would flip it back. Navigation must not
change layout mode, and hysteresis can't absorb jumps that large. It would also need a
rail inside spread decks.

So adopt the rule cld, mus and gem converged on: **block mode is decided only for a card
shown alone** (a paged deck's active card, or a future single-card deck such as a
Summary with member blocks). A spread deck renders every block inline. With outside-in
decisions and a shared budget this mostly falls out naturally: a spread deck means Reply
fits, so its blocks fit. The explicit rule covers hysteresis edges and a block threshold
lower than the deck's. The genuinely useful part of cdx's idea, seeing Context and the
latest output together, is already available as a `Context | Reply` split, where each
panel keeps its own block cursor.

### 3.4 Threshold: a dedicated key

mus and cdx argued for one knob, on corpus-before-mechanism grounds. Under the invariant,
though, the block threshold answers a *different* question: "does a card shown alone
show all shells, or one at a time?" A standing preference of `0` (always one shell per
page) is legitimate, and the shared knob can only express it by also forcing every deck
to page. You asked for configurability, and the cost is small: an `AgentDecksSettings`
field with the same coercion, `default_config.yml`, the `sase.schema.json` entry (`ace`
has `additionalProperties: false`), `docs/configuration.md`, and parity tests. At the
default of `1.5` the golden matrix does not grow.

### 3.5 Chrome: the block rail

Each alternative fails somewhere:

- **Title suffix** (cdx, gem): the border title already carries the *card* position
  (`Reply  2/2`, `‹ 2/2 ›`, `MAIN 2/2` in `titles.py`), so a second fraction reads as
  ambiguous. It also disappears in compact and micro tiers exactly when you need it.
- **Subtitle** (mus): the border subtitle holds `spread · main 2 · files 1 · tools 109`.
- **Boxed pill** (gem): three or four rows of chrome, and a box inside a bordered panel
  is noise.
- **In-content header only** (cdx): it scrolls away inside a long block.

A **one-row rail docked under the panel's top border** answers "where am I, what's
around me, and how did each shell end" at all times. It reuses the roster's visual
language and is clickable. Specification in §4.6.

### 3.6 Block state: ephemeral

A block id is a shell identity. It is subject-specific, often short-lived, and
meaningless after switching nodes or restarting. The landing rule ("newest") would
override a persisted preference anyway, and persisting it would need a
`ace_agents_deck_state.json` schema change for nothing. The state lives on each
pre-composed `MainDeckView`, so it naturally survives deck switches, split rotation and
zoom. **Rejected:** sticking to a *role* across nodes (for example, staying on `--plan`
while pressing `j`). It is surprising and defeats the triage loop.

### 3.7 Data model: transparent wrapper plus validated accessors

gem's `CardPart(blocks=…)`, which also stores a flattened copy of the renderables, keeps
two sources of truth. mus's "every card has an implicit single block" makes the
predicate that matters (≥ 2 blocks) harder to see. cdx's explicit
`preamble`/`blocks`/`renderables` fields are clean, but they change `CardPart`'s shape
for every caller. Merge the strengths of both:

- `CardBlock` is a **transparent wrapper**, like `CardPart`. Phase 1 therefore renders
  identically and every walker simply descends.
- `CardPart` **computes** `preamble` and `blocks` at construction and validates the
  structure: blocks are trailing and contiguous, and ids are non-empty and unique. Logic
  never re-scans a mixed tuple.

## 4. Recommended design

### 4.1 Vocabulary and invariants

| Term | Meaning |
|---|---|
| **Agent data card block** ("card block") | One titled, stably identified unit inside a card. A session's Reply card has one per sase shell. |
| **Block rail** | The one-row timeline of a card's blocks, docked in a deck panel. |
| **Block-spread / block-paged** | How a card shown alone renders its blocks: all inline, or one at a time. |
| **Active block** | Block-paged: the block shown. Block-spread: the last block header at or above the viewport top. |
| **Following** | The panel is on the newest block, so a newly started shell becomes active automatically. |

Invariants:

- A card has zero blocks or at least one. Block controls need **two or more**.
- Blocks never nest.
- Block ids are data identity, taken from the shell's `Agent.identity`. They are never
  positions or role labels (`--mon`, `--mon-0`, and feedback rounds repeat).
- Block state is panel-local, and navigation acts on the **focused** panel's active
  card.
- There is **one `VerticalScroll`** per panel. Blocks are Rich structure plus anchors,
  never nested scroll widgets.

### 4.2 Which cards get blocks (v1)

| Selection | Card | Blocks |
|---|---|---|
| Agent session container | Reply | one per shell from `concrete_agent_session_shell_rows()`: `AGENT (role)`, `⚙ MONITOR`, `⋔ GATE` |
| Non-session root with legacy `followup_agents` | Reply | root phase plus one per follow-up, **if that path is still reachable**. Verify first. Its hint twin must be split per phase, and its missing gate branch fixed or confirmed dead. |
| Everything else | — | none; renders exactly as today |

Out of scope, but the model supports them later: clan/tribe Summary (one block per
member), Tools/LLM Calls (one per shell), attempt history (one per attempt).

### 4.3 Mode matrix (per deck panel)

| Deck mode | Shown | Block mode | Rail |
|---|---|---|---|
| spread | every card on one page | always inline | hidden; phase dividers suffice |
| paged, active card has ≥ 2 blocks | that card alone | spread if card rows ≤ `block_spread_max_screens × viewport`, else paged, with ±10% hysteresis for the same subject | **shown in both block modes**, so it never pops in or out when streaming crosses the band |
| paged, active card has < 2 blocks | that card alone | — | hidden |

Measurement reuses the deck-level lower bound: if it already exceeds the block budget ×
1.1, the card is block-paged at no extra cost. Otherwise, call `measure_main_rows` with
cache key `f"{digest}:{card_id}:{block_id}"`. **Partial documents never decide a
mode.**

### 4.4 Landing, navigation and live updates

Each panel keeps `{card_id: BlockCursor(block_id, following)}` for the current subject.

1. **New subject** (`j/k`, attempt toggle): select the newest block with `following =
   True`.
   - Block-paged: show its page from the top.
   - Block-spread: scroll to `min(header_row(newest), max_scroll_y)`. When the card fits,
     that lands at the bottom, like a chat log. There is no blank tail.
   - Deck-spread with a sticky Reply: the same clamp, so the newest header is on screen.
2. **Same subject, content update:** keep the block **by id** and keep the scroll offset.
   A bottom pin (`G`) persists.
3. **New shell while following:** advance to it (a paged view swaps the page; a spread
   view scrolls its header into view). Carry the bottom pin across.
4. **New shell while not following:** stay put. The new entry appears at the rail's right
   end with a restrained `● 1 newer ›` marker. **Never yank a reader out of history.**
5. **`[` / `]`:** move to the older or newer block, wrapping. `following` becomes `active
   == newest`.
   - Paged: swap the page and reset to its top.
   - Spread: an anchor motion that top-aligns the target header, the same as spread
     `Ctrl+J/K`. It uses the existing layout reserve and the bounded `call_after_refresh`
     retry in `_apply_spread_scroll`.
   - In a spread *deck*, `[`/`]` move between block headers when the scroll-active card
     has blocks, and are no-ops otherwise.
6. **Vanished block id:** fall back to the newest.
7. **Partial paint** (the header-only paint during `j/k`): it never touches block state.
   **Clear the rail on subject change,** and redraw it only from a full document of the
   current subject, so it can never show the previous node's shells.
8. **Mode transitions** (streaming crosses the band, resize, split, ratio, header or jump
   toggles): capture one hierarchical reading anchor, `(card_id, block_id, offset_rows,
   pinned)`, and restore the most specific identity that survives: same block + offset,
   then card top, then card default, then document default. This *replaces* ad hoc
   nested branches around `_apply_main_transition()`; it does not add another layer.
9. **Running newest block:** land at its top, which matches today's paged cards. `G`
   tails it (open question 4).

### 4.5 Keys and registration

| Key | Textual name | Action | Behavior | Contextual duplicate |
|---|---|---|---|---|
| `[` | `left_square_bracket` | `prev_card_block` | older block (wraps) | `cycle_artifacts_subtab_reverse` |
| `]` | `right_square_bracket` | `next_card_block` | newer block (wraps) | `cycle_artifacts_subtab` |

Registration follows the sase-17d checklist:

- `AppKeymaps` fields.
- **`src/sase/default_config.yml`** (the core gotcha).
- `_BINDING_META` and the fallback `bindings.py`.
- The `check_app_action` gate: Agents tab, the focused panel's active card has ≥ 2
  blocks, and `_prompt_input_owns_keys` respected.
- Palette metadata and availability.
- A help row, "Older / newer card block".
- A **conditional** footer entry, `[ ] blocks`, shown only when blocks exist.
- The `_CONTEXTUAL_APP_DUPLICATES` pairs.
- Deck-search structural exit keys (`_deck_search_host.py`).
- The four keymap parity tests.

**Mouse:** clicking a rail entry activates that block, using `@click` meta on the rail
segments.

### 4.6 Visual design

**Hierarchy.** It already exists, and blocks add no new separator style:

| Level | Marker |
|---|---|
| Deck | rounded border in the deck accent |
| Card | title tab pill (paged) or heavy `━━ ◆ Reply ━━` rule (spread) |
| Block | the existing phase divider `─── AGENT (code) ─── 07:23:10 ───` in the shell's accent (purple agent, amber `⚙` monitor, lifecycle-colored `⋔` gate), now carrying `sase_card_block` anchor meta |
| Turn | dim `─── 07:31:02 ───` |

**The rail.** One row, pre-composed in `DeckPanel.compose` and toggled by CSS class. It
is never remounted (a sase-17d rule).

- Entries are chronological, left to right, joined by `─` in separator gray `#444`.
- Each entry shows the roster number, glyph + label, and status glyph (✓ green, ▶
  yellow, ✗ red), all from `agent_session_roster_entries`.
- The active entry is a `reverse bold <deck accent>` pill, identical to the active card
  tab. Inactive entries are muted `#888`.
- An unfocused panel dims the whole rail, matching its dim title.
- At the widest tier only, the right edge shows `[ older · newer ]`. The hint's own
  brackets document the keys.
- Tiers come from a pure helper, and the widest one that fits wins (like `deck_title`):
  - full
  - windowed: active ± k neighbors, e.g. `‹9 older · 9 ⚙ --mon-3 ✓ ─ 10 --code ✗ ─ ▐11
    --code ▶▌ · 2 newer›`
  - compact: glyph-only neighbors
  - micro: `▐2 --code ▶▌ 2 older`

Landing on a session (deck paged on sticky Reply, block-paged, newest block):

```text
╭─ ◆ MAIN ┃ Context │ Reply  2/2 ────────────────────────────────────────────╮
│ 0 --plan ✓ ─ 1 ⋔ --gate ✓ ─ ▐2 --code ▶▌                 [ older · newer ] │
│ ─── AGENT (code) ─── 07:23:10 ─────────────────                            │
│ ─── 07:23:41 ──────────────────────────────────                            │
│ Reading the sticky-header code to see how the collapsed preview is built…  │
│ ─── 07:31:02 ──────────────────────────────────                            │
│ Implemented the XPROMPT card; running just check now.                      │
╰───────────────────────────────────────────── main 2 · files 1 · tools 109 ─╯
```

After one `[` (the second-to-last shell):

```text
╭─ ◆ MAIN ┃ Context │ Reply  2/2 ────────────────────────────────────────────╮
│ 0 --plan ✓ ─ ▐1 ⋔ --gate ✓▌ ─ 2 --code ▶                 [ older · newer ] │
│ ─── ⋔ GATE ─── 07:22:49 ───────────────────────                            │
│    Decision:  Tale ready for review: agent_header_xprompt_card.md          │
│    Kind:      plan                                                         │
│    Status:    TALE APPROVED                                                │
╰───────────────────────────────────────────── main 2 · files 1 · tools 109 ─╯
```

Reading history while a new shell starts (not following):

```text
│ 0 --plan ✓ ─ ▐1 ⋔ --gate ✓▌ ─ 2 --code ✓ ─ 3 --code ▶          ● 1 newer › │
```

Left/right split comparing two shells (compact tiers, independent cursors; the right
panel is unfocused and dimmed):

```text
╭─ ◆ MAIN ‹ 2/2 › Reply ─────────────╮ ╭─ MAIN 2/2 ─────────────────────────╮
│ ‹ 1 ⋔ ✓ ─ ▐2 --code ▶▌ ›           │ │ ‹ 0 ✓ ─ ▐1 ⋔ --gate ✓▌ ─ 2 ▶ ›     │
│ ─── AGENT (code) ─── 07:23:10 ──   │ │ ─── ⋔ GATE ─── 07:22:49 ────────   │
│ Implemented the XPROMPT card;      │ │    Decision:  Tale ready for…      │
│ running just check now.            │ │    Status:    TALE APPROVED        │
╰────────────────────────────────────╯ ╰────────────────────────────────────╯
```

A spread deck has no rail. The vestigial rule is gone, and the phase dividers are the
block anchors:

```text
╭─ ◆ MAIN ┃ Context │ Reply ─────────────────────────────────────────────────╮
│ AGENT PROMPT …                                                             │
│                                                                            │
│ ━━ ◆ Reply ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ AGENT REPLY · 2                                                            │
│ ─── AGENT (plan) ─── 07:12:12 ─────────────────                            │
│ …                                                                          │
│ ─── AGENT (code) ─── 07:23:10 ─────────────────                            │
│ …                                                                          │
╰────────────────────────────────────── spread · main 2 · files 1 · tools 3 ─╯
```

**Preamble.** In block-paged mode, drop the `AGENT REPLY · N` heading, because the rail
says it. Show a card-level `TRACEBACK` only above the **newest** block's page, which is
the landing page. Move it into a specific block later if it can be attributed to one
shell. Block-spread mode keeps the heading and puts the traceback first, as today.

### 4.7 Architecture

- **`widgets/decks/card_block.py`** (new):
  - `CardBlock(block_id, title, *renderables, meta: BlockMeta)`, a transparent wrapper
    marked `__sase_card_block__`. `BlockMeta` carries ordinal, label, glyph, accent and
    status bucket.
  - `is_card_container()`.
  - `CardPart.preamble` / `CardPart.blocks` accessors with validation.
- **Builders.** Extract session phase-to-block assembly into a new module, since
  `_agent_display_agent_session_render.py` is already at 432 lines.
  - Add a `block_id=` keyword to `render_phase_divider`, `build_monitor_phase` and
  `build_gate_phase`, so the divider line carries the anchor meta and a block never gets
  two headers.
  - One loop serves hint and non-hint modes.
  - **The builders reorder nothing.**
- **Walkers.** Teach every site in §1.5 through `is_card_container()`, and hash block
  id, title *and status* in the digest.
- **Anchors.** Add `DECK_BLOCK_META_KEY = "sase_card_block"`,
  `PromptPanelSectionRole.BLOCK`, and `block_anchor_rows(card_id, width)`. Card tracking
  and legacy section navigation ignore `BLOCK` anchors.
- **Pure model** (`block_model.py`):
  - `BlockCursor`
  - `resolve_active_block(ids, cursor, *, new_subject, partial)`
  - `cycle_item_id`, generalizing `cycle_card_id` and keeping it as a wrapper
  - `decide_block_mode`, a thin call to `decide_render_mode`
- **View.** `MainDeckView` (332 lines) gains block projection:
  - paged: `[traceback when on newest] + active block`, with digest
    `f"{digest}:{card}:{block}"`
  - spread: the whole card, then landing
- **Panel.** A new `DeckPanelBlocksMixin` in `panel_blocks.py`. `panel.py` is 735 lines
  and broke `toobig`'s 1000-line limit once during sase-17d (mus's "already at the
  limit" is stale), so it gains only the mixin include.
- **Rail.** `block_rail.py` holds the pure `block_rail_text(entries, active, *, width,
  accent, focused) -> Text` plus `BlockRail(Static)`, which subscribes to theme changes
  like the chrome does.
- **Wiring.**
  - `AgentDetail.cycle_focused_card_block(direction)` in `_agent_detail_decks.py`.
  - `action_next_card_block` / `action_prev_card_block` in
    `actions/agents/_panel_detail.py`.
- **Whole-card semantics are preserved.**
  - The search corpus indexes every block, including hidden ones, with sub-separators
    (`── Reply › 2 --code ──`).
  - `V`, `E` and clipboard stay card-wide. mus wanted `E` to follow the focused block;
    defer that to an explicit future "copy block" action instead.
  - Hint numbering stays computed over the full card, so it never renumbers while you
    cycle.

### 4.8 Performance

A block keypress must be a pure in-memory path: no file reads, stats, subprocesses, JSON
parsing or Main-source rebuild (`tui_perf` rules 1, 8 and 11).

- Exact block heights are cached per `(block digest, width)`.
- The rail is O(blocks), built from `BlockMeta`, with no render.
- There are no new workers, timers or refresh paths. Updates ride the existing Main
  fan-out and `DetailPanelDebouncer`, and scroll restores stay thin `call_after_refresh`
  callbacks.
- **Gate:** `SASE_TUI_PERF=1 pytest -s -m slow tests/ace/tui/bench_tui_jk.py`, in SINGLE
  and LEFT_RIGHT, before and after, with p95 < 16 ms. Add a 10-shell, 5,000-line sticky-
  Reply fixture and a block-cycle case. `j/k` should *improve*.

### 4.9 Reliability checklist

| Failure mode | Mitigation |
|---|---|
| `Ctrl+Shift+J` cycles cards | Printable `[`/`]` defaults |
| Rail shows the previous node's shells during partial paint | Clear on subject change; draw only from a full current-subject document |
| New shell shifts index-based ids | `block_id` = shell identity |
| View jumps while reading an old block | Follow only while on the newest; show a `1 newer` marker otherwise |
| Block keypress flips deck mode | "Shown alone" invariant (§3.3) |
| Streaming crosses the band | Hysteresis plus the hierarchical reading anchor |
| `[` pressed before anchors publish | Existing bounded retry |
| Digest skip hides growth or status | Teach the digest; hash block metadata |
| Lower-bound early exit lost | Teach `_lower_bound_node` |
| Hint mode erases blocks | Per-block `CachedRenderable` |
| Test helpers assume `Text`/`Group` | Update them to `flatten_card_document`; grep before landing |
| `toobig` | New modules only |

## 5. Delivery plan

No feature flag is needed. Phase 1 renders identically apart from the rule removal, and
phase 2 lands the whole visible behavior at once. If phase 2 must be split, scaffold it
with a `beta` flag (`sase flag new card_blocks`) that the epic removes before landing,
per the `sase_flags` rules.

| Phase | Size | Scope | Verification |
|---|---|---|---|
| **1. card-block-model** | medium | `CardBlock` plus accessors; `is_card_container` across every walker (including the three hazards); session builder wrapping (and legacy path if reachable); divider anchor meta; `BLOCK` role; vestigial rule removal | Partition tests for each node kind; plain-text equivalence (modulo the rule); digest changes on status and on content past 2 KB; lower-bound early exit still triggers; hint mode keeps blocks; anchors published; targeted `just fix-tui-screenshots` for the rule, inspected |
| **2. card-block-view** | large | Pure model and mode decision; config key; `MainDeckView` projection and landing; `DeckPanelBlocksMixin`; `BlockRail` plus tiers; `[`/`]` with full registration; footer, help and palette; search exits; rail click | Pure tests (following vs not, vanished id, partial, wrap, hysteresis); pilot tests (land newest, `[` goes to the second-to-last, follow and not-follow on a streaming new shell, subject reset, partial paint, split independence, spread↔paged anchoring, `[`/`]` through the public pilot path); PNG goldens (see below); live `sase screenshot` inspection; `j/k` bench |
| **3. card-block-docs** | small | `docs/ace.md` (hierarchy, newest landing, the triage-loop tip); `docs/configuration.md`; new glossary strand **Agent Data Card Block** plus an update to the Agent Data Card strand, both via `/sase_memory_write` | Describe only shipped behavior |

Goldens for phase 2:

- block-paged Reply on the newest block
- the same after `[`
- block-spread landing
- windowed, compact and micro rails in a LEFT_RIGHT split
- a spread deck with no rail
- the not-following `1 newer` marker

**Cheaper first slice, if you want value sooner:** ship phase 1 plus the anchor-only part
of phase 2. That means newest-block landing and `[`/`]` as header motions in a single
Reply document, with no paging and no rail. It is the block-spread path, so nothing is
thrown away.

## 6. Open questions for you

1. Do you accept **`[` / `]`** (A1)? The alternatives are `Alt+J/K`, which works in tmux
   but is fragile with macOS kitty, or your original chord as a personal override outside
   tmux.
2. Do you accept **chronological order with a newest-block landing** (A2) in place of
   literal reversal?
3. What should `block_spread_max_screens` default to? `1.5`, matching decks, is
   recommended. `1.0` pages by shell sooner. `0` always shows one shell per page.
4. When the newest block is still *running*, should landing tail it (bottom-pinned), or
   land at its top? Top is recommended, matching today's paged cards, with `G` to pin.
5. Should the legacy non-session `followup_agents` path get blocks in v1, or only
   session containers? Recommended: session containers first, and the legacy path only
   if it is still reachable.

## 7. Recommended solution

Add **agent data card blocks** as a strict third level: **deck → card → optional,
non-nesting blocks**. The first and only wired use is an agent session's **Reply** card,
with one block per concrete sase shell (`AGENT (role)`, `⚙ MONITOR`, `⋔ GATE`). The blocks
come from `concrete_agent_session_shell_rows()`, and each block id is the shell's
identity.

- **Order and landing.** Blocks stay chronological. Every node lands on its **newest
  block**, which makes sticky-Reply `j/k` a one-keypress-per-session triage loop. **`[`**
  steps to older blocks and **`]`** to newer ones, wrapping, so the first `[` reaches the
  second-to-last shell. Do not ship `Ctrl+Shift+J/K`: in your tmux it arrives as
  `Ctrl+J/K` and would cycle cards.
- **Modes.** A card shown on its own spreads its blocks inline when they fit
  `ace.agent_decks.block_spread_max_screens` (default `1.5`, `0` = always paged).
  Otherwise it pages them one shell at a time, with the decks' hysteresis. A spread deck
  always shows blocks inline, so block navigation never changes deck mode.
- **Chrome.** Whenever blocks are navigable, a **one-row block rail** shows the session
  timeline in the JUMP roster's language: numbers, labels, glyphs and status colors
  match, and the active block is the same accent pill as the active card tab. The
  existing phase dividers are the block headers. The vestigial rule at the top of Reply
  goes. The border title stays deck + card only.
- **Reliability.** Block state is ephemeral, per panel and per subject. Following applies
  only on the newest block, and a restrained `1 newer` marker appears otherwise. The rail
  is cleared on subject change and never drawn from partial documents. Mode transitions
  restore a hierarchical `(card, block, offset, pin)` anchor.
- **Build.** A transparent `CardBlock` wrapper with validated `CardPart` accessors,
  consumed through one `is_card_container()` helper by every walker. Pay particular
  attention to three silent hazards: the lower bound, the digest and the hint cache.
  Add a `BLOCK` anchor role, a `DeckPanelBlocksMixin`, and a tiered `BlockRail`, then
  register `prev_card_block`/`next_card_block` fully. It lands in two implementation
  phases plus docs, with no flag and no `sase-core` change, and should make `j/k`
  **faster** on large sessions.

## 8. Side findings (not part of this feature)

- **`jump_to_entry_forward` (`ctrl+shift+o`) is broken in tmux.** It arrives as `ctrl+o`,
  so "forward" jumps backward. Both cld's probe and the lead's confirm it. Tracked as
  task bead `sase-192` (filed by cld, corroborated by the lead).
- **The legacy `followup_agents` hint path** (`_agent_display_hint_body.py`) has no
  `is_gate` branch, so gates render as agent phases in hint mode, unlike the non-hint
  path.
