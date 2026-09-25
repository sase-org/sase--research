# Agent Data Card Blocks — Research, Critique and Recommendation (cld)

Researcher: `cld` (4-researcher swarm). Date: 2026-09-25. Context: epic `sase-17d` (agent
data decks and cards), its plan `plan:202609/agents_tab_decks_and_cards.md`, and the
shipped code under `src/sase/ace/tui/widgets/decks/`.

## 0. Summary

**Verdict: build it.** The Reply card of a multi-shell agent session is the worst reading
experience left in the deck design. The newest shell's output, which is what you nearly
always want, sits at the bottom of a long paged card that opens at the oldest shell.
Card blocks are the right abstraction: a third level, deck → card → block. They keep the
sticky Reply card and the deck model intact.

I recommend four adjustments to the requirements. Each is argued in §4:

1. **Keys: use `[` / `]`, not `Ctrl+Shift+J/K`.** I verified that `Ctrl+Shift+J` reaches
   sase as `Ctrl+J` on your terminal chain (kitty → ssh → tmux 3.5a). It still does even
   with tmux `extended-keys always` and `csi-u` fully enabled. So the proposed key would
   silently **cycle cards instead of blocks**.
2. **Don't reverse the block order.** Keep blocks chronological, **land on the newest
   block**, and make `[` step back to the next-older block. You still see the final
   shell's output first, and one keypress still reaches the second-to-last shell. The
   spread view, the JUMP roster, shell numbers, timestamps, hint numbering, search and the
   `V`/`E` exports all stay in the one order they already share.
3. **Nested modes need an invariant:** a card pages its blocks only when it is shown on its
   own (its deck is paged). Deck-spread implies block-spread. The block threshold is a new
   key, `ace.agent_decks.block_spread_max_screens` (default `1.5`).
4. **Add a one-row block rail** above the card body. It is a left-to-right timeline of the
   session's shells, drawn in the JUMP roster's vocabulary (`0 --plan ✓ ─ 1 ⋔ --gate ✓ ─
   ▐2 --code ▶▌`). It is what makes paging understandable and it is what makes it look
   good.

Plus several reliability rules:

- block ids are shell identities, not indices
- "follow latest" stickiness
- the rail never shows a previous subject's shells
- hint mode must not flatten the blocks away (a concrete hazard in
  `_prepare_cached_hint_renderable`)
- remove a vestigial rule that currently opens every Reply card

**Shape:** two implementation phases plus docs and glossary. No feature flag is needed
because phase 1 is render-identical. No `sase-core` change.

## 1. What I examined

- **Epic, plan and prior research.**
  - The `sase-17d` bead and its notes.
  - The full epic plan (§3.1 card table, §3.7 spread/paged algorithm, §3.8 visual
    language, §3.4 key-registration checklist).
  - The prior decks research (a different, earlier swarm), grepped only for key-delivery
    and Reply findings.
- **Code.**
  - `widgets/decks/`: `card_part.py`, `model.py`, `main_document.py`, `main_view.py`,
    `panel.py` (735 lines), `panel_spread.py`, `panel_chrome.py`, `render_mode.py`,
    `titles.py`, `separators.py`, `search_corpus.py`.
  - The Reply builders: `prompt_panel/_agent_display_agent_session_render.py` and
    `_agent_display_render.py:423-620`.
  - The phase helpers: `_agent_display_content.py`, `_agent_monitor_section.py:321`,
    `_agent_gate_section.py:300`.
  - The roster: `_agent_display_agent_session.py`.
  - Anchors: `_section_navigation.py` and `_section_view.py:209`.
  - Walkers: `util/renderable_digest.py:49`, `_identity_header.py:120`,
    `_agent_display_hints.py:39-100`.
  - Keymaps: `default_config.yml:636-680`, `_app_action_availability.py:348`,
    `keymaps/registry.py:137`.
  - Settings: `agent_decks_settings.py`.
- **Live TUI.** I captured `sase screenshot` PNGs of session `0rv.w0` (3 shells: `--plan`,
  `--gate`, `--code`), zoomed with `Z`, on Context and on Reply, before and after
  scrolling. The observations are in §2.3.
- **Terminal chain.** I ran key-delivery probes with private tmux servers (`-L`), so the
  user's server was never touched. The transcripts are in Appendix A.
- **Data.** I measured shells per session and reply size across 1,308 `agent_meta.json`
  files from 2026-09-20..25 (Appendix B).

## 2. How the Reply card works today

### 2.1 Structure

An agent-session container's Main document is built in
`_update_agent_session_display()`:

```
context_card(header_text, prompt…)
reply_card(
    *traceback_parts,               # TRACEBACK (moved here by sase-17d.2)
    reply_header,                   # "\n" + dim 50-col rule + "\n" + "AGENT REPLY · N"
    # one phase per sase shell, in session chain order:
    render_phase_divider("AGENT (plan)", t0), *chunks…,   # agent shell
    *build_gate_phase(gate),        # "─── ⋔ GATE ─── t1 ───" + fields + log
    *build_monitor_phase(mon),      # "─── ⚙ MONITOR ─── t2 ───" + fields + log
    render_phase_divider("AGENT (code)", t3), *chunks…,
)
```

The legacy `followup_agents` branch (`_agent_display_render.py:461-500`) has the same
shape.

**Terminology note.** `AGENT CHAT` is the heading of a *single* finished agent
(`_agent_display_render.py:508`). Its sub-dividers are per-turn timestamps
(`─── 07:13:20 ───`), not shells. The "one block per sase shell" you describe is **one
block per phase under `AGENT REPLY · N`**. Monitor and gate shells are included. Turn
timestamps are not blocks.

### 2.2 Deck machinery you can reuse

- **`CardPart`** is a *transparent* Rich wrapper: rendering it is byte-identical to
  rendering its children. Walkers descend it through the `__sase_card_part__` marker. A
  `CardBlock` can follow exactly this pattern.
- **`decide_render_mode()`** is a pure function with 10% hysteresis. It is card-count
  agnostic, so it works unchanged with `card_count=len(blocks)`.
- **`measure_main_rows()`** takes a cheap lower bound with early exit, then renders
  exactly only near the band. Results are cached by `(digest:card, width)`.
- **Anchors.** A `Style(meta={"sase_deck_card": id})` on a rendered line publishes a
  `CARD` anchor through `SectionTrackingVisual`. Spread-mode `Ctrl+J/K` and the
  scroll-derived title pill run on these anchors. A `BLOCK` role is a one-enum-member
  extension.
- **Per-panel state.** Each `DeckPanel` owns its render mode, active card and scroll. The
  sticky preferred card lives in `DeckAreaState`.

### 2.3 What the live screenshots show (session `0rv.w0`, Main zoomed, Reply paged)

1. **A vestigial rule opens the card.** Paged Reply begins with two blank lines, a dim
   50-column rule and another blank line. It is the old Context/Reply separator from the
   single-document era. In deck-spread mode it stacks under the new `━━ ◆ Reply ━━`
   separator, giving two rules in a row. The rows are wasted and it looks like a rendering
   glitch.
2. **The newest output is buried.** The card opens on `AGENT REPLY · 3` →
   `─── AGENT (plan) ─── 07:12:12 ───` → the plan agent's turn-by-turn notes. The gate
   phase is about two screens down and the running `--code` shell's output is below that.
3. **A timeline already exists at the bottom of the detail area.** The JUMP panel shows
   `SESSION SHELLS 0-2: 0 --plan ✓  1 --gate ✓  2 --code ▶`: numbered, labelled by suffix,
   status-glyphed, oldest first. Blocks should reuse this vocabulary (§5.6).
4. **The phase dividers already look like block headers.** The purple `AGENT (plan)` and
   cyan `⋔ GATE` dividers, each with a start time, read as section heads. No new separator
   style is needed.

### 2.4 How big session Reply cards get

Data is from 2026-09-20..25. Details are in Appendix B.

| Metric (70 agent sessions) | p50 | p90 | max |
| --------------------------- | --: | --: | -----: |
| Shells per session | 3 | 5 | 15 |
| Raw reply lines per session | 72 | 738 | 14,013 |

The budget is `1.5 × viewport`: about 60–90 rows in a single panel and about 20–35 in a
split. So a typical session Reply is already at or past the threshold, and p90 is 10×
over it. Monitor logs are not counted, so these figures are lower bounds. Role mix:
root 93, monitor 62, gate 58, code 52. Gates and monitors are first-class block kinds,
not edge cases.

## 3. Critique — is this a good idea?

**Yes.** Four reasons:

- **It fixes a real, frequent pain.** Most of the time you want "what is the session
  doing now, or what did it end with?" Today that is the most expensive thing to reach.
- **It composes with the sticky Reply.** A paged deck already keeps Reply as you press
  j/k. If each node also lands on its **newest block**, j/k becomes a fast triage loop:
  you see every session's latest shell output, one keypress per session. I think this is
  the feature's best property. It is worth naming in the docs.
- **It is the right depth.** Decks already page *cards*. Paging *within* a card is the
  same idea one level down, so the user learns nothing new: spread when it fits, paged
  when it doesn't, a key pair to step.
- **It improves performance.** A paged block renders one shell's output instead of
  the whole 738- to 14,000-line card.

**Problems with the plan as written.** Each is addressed in §4:

- **P1. `Ctrl+Shift+J/K` cannot be delivered** on your terminal chain. It would fire
  `Ctrl+J/K` (card cycling). It fails as the *wrong action*, not as a no-op, which is the
  worst failure mode for a navigation key. The existing `Ctrl+Shift+O` (forward jump) has
  the same defect today: it arrives as `Ctrl+O` and jumps *backward*.
- **P2. Reversing the order creates a second ordering.** The spread view, JUMP roster,
  `0-9` shell jump keys, `AGENT REPLY · N`, timestamps, hint numbering, search corpus, `V`
  pager and `E` export are all chronological. If you reverse only the paged view, the key
  direction flips when a streaming card crosses the threshold. If you reverse both views,
  a live shell grows at the *top* of a spread card, which shifts the viewport under you
  while you read older blocks, and the transcript reads backwards.
- **P3. The nested spread/paged state is under-specified.** Two independent thresholds
  allow incoherent states. For example, a deck spread showing Context plus one paged
  Reply block, with the other blocks hidden mid-scroll.
- **P4. Paging hides context.** On block 5 you can no longer see that block 4 was a
  rejected gate. Without a visible timeline, paged blocks feel like a maze. The rail
  (A4) is not decoration; it is what makes paging safe.
- **P5. The "block" name collides.** `command_line.block_next`/`block_kill`/… already use
  bare "block" for command-line transcript blocks. Use the qualified term **card block**
  everywhere: action ids `next_card_block`/`prev_card_block`, class `CardBlock`.
- **P6. Scope creep risk.** "Like decks" invites generalizing to Files, Tools and Summary
  now. Build the model generically, but only wire the Reply card.

## 4. Requirement adjustments (clearly called out)

| #  | Your requirement | Adjustment | Why |
| -- | ---------------- | ---------- | --- |
| A1 | `Ctrl+Shift+J/K` cycle blocks | **`]` next (newer) / `[` previous (older)**, both wrapping. `Ctrl+Shift+J/K` stays available as a user override for people who run outside tmux. | P1. Verified (Appendix A). Brackets are printable, so every terminal delivers them. `[`/`]` already mean "previous/next sub-thing" all over the TUI: Artifacts sub-tabs, help and notification tabs, the Statistics view, the gate debug modal. vim's `[[`/`]]` are section motions. Both keys are free on the Agents tab (`cycle_artifacts_subtab` is Artifacts-only). |
| A2 | Reverse the Reply's block order; the final block is shown first when paged; Ctrl+Shift+J goes to the second-to-last block | **Keep blocks chronological. Land on the newest block. `[` goes to the second-to-last.** | P2. You get the same first screen and the same first-keypress result, but one ordering everywhere and no content reordering in the builders. On a left-to-right timeline, `[` points back in time. |
| A3 | Spread by default, paged past a configurable threshold | **Keep, with the invariant "blocks page only when their card is shown alone".** Add `ace.agent_decks.block_spread_max_screens: 1.5` (`0` = always paged). | P3. Deck spread implies the card fits, which implies its blocks spread. The block decision reuses `decide_render_mode` and its hysteresis. |
| A4 | (unspecified) | **Add a one-row block rail** whenever a paged deck's active card has 2 or more blocks, in both block-spread and block-paged mode. | P4. It is the "where am I" for blocks and it mirrors the JUMP roster. Showing it in both block modes means it never pops in or out when content crosses the threshold, so there is no layout jump. |
| A5 | (unspecified) | **Stickiness:** block ids are shell identities; a new subject resets to the newest block; "follow latest" applies only while you are on the newest block. | Reliability while sessions stream new shells (§5.4). |
| A6 | "AGENT CHAT sub-sections" | **Blocks are the shell phases under `AGENT REPLY · N`.** Single agents, turn timestamps and attempt dividers are not blocks. | This is the actual structure (§2.1). Sessions always have ≥ 2 shells (glossary), so the rail appears for every session container and never for plain agents. |
| A7 | (cosmetic) | **Drop the vestigial "blank + rule + blank" prefix** of the Reply card, in both modes. | §2.3 item 1. The card separator and title now do its job. This changes goldens. |

**If you insist on A2 as literally written** (reverse order), apply it to *both* modes
and add scroll anchoring for content growth above the viewport. Build this and
`AGENT REPLY · N · newest first`. I still recommend against it for the reasons in P2.

## 5. Proposed design

### 5.1 Vocabulary

| Term | Meaning |
| ---- | ------- |
| **Agent data card block** ("card block") | One titled unit *inside* a card. The Reply card of an agent session has one block per sase shell. |
| **Block rail** | The one-row timeline of a card's blocks, shown above the card body in a paged deck. |
| **Block-spread / block-paged** | How a card shown on its own renders its blocks: all inline, or one at a time. |
| **Active block** | Block-paged: the block shown. Block-spread: the block whose header is at or above the viewport top. |
| **Newest block** | The last block in chronological order: the default landing. |
| **Following** | The panel is on the newest block, so a newly started shell becomes active automatically. |

### 5.2 Which cards get blocks

| Selection | Card | Blocks |
| --------- | ---- | ------ |
| Agent session container | Reply | one per shell phase: agent (`AGENT (role)`), `⚙ MONITOR`, `⋔ GATE` |
| Agent with legacy `followup_agents` | Reply | root phase + one per follow-up |
| Everything else (single agent, shell node, proc, monitor, gate, workflow step, attempt view `D`, clan/tribe Summary) | — | none; renders exactly as today |

Future candidates, not in scope: clan/tribe Summary with one block per member; Tools/LLM
Calls with one block per shell; attempt history with one block per attempt.

### 5.3 Mode matrix (per deck panel)

| Deck mode | What is shown | Block mode | Rail |
| --------- | ------------- | ---------- | ---- |
| spread | every card on one page | always inline (spread) | hidden; the phase dividers suffice |
| paged, active card has ≥ 2 blocks | that card alone | **spread** if the card's rows ≤ `block_spread_max_screens × viewport`, else **paged** (±10% hysteresis, same subject) | **shown** |
| paged, active card has < 2 blocks | that card alone | — | hidden |

The rule is stated as "decided only when the card is shown alone" rather than "when the
deck is paged". That way a future single-card deck (for example a Summary card with
member blocks, where the deck is trivially spread) still pages its blocks.

**Measurement.** The deck-level lower bound already visited the Reply renderables, so
reuse it. If that lower bound already exceeds the block budget × 1.1, the card is
block-paged with no extra work. Otherwise call `measure_main_rows(blocks, …)` with cache
key `f"{digest}:{card_id}:{block_id}"`. Partial documents never decide the mode (same as
17d).

### 5.4 Landing, navigation and stickiness

- **New subject** (j/k to another node, attempt-pin toggle):
  - Block-paged: show the **newest block's page** from its top. `following = True`.
  - Block-spread: scroll to `y = min(header_row(newest), max_scroll_y)`. This shows as
    much of the newest block as fits, starting from its header. When the whole card fits
    it simply lands at the bottom, which is the chat-app convention. No layout reserve
    and no blank tail.
- **Same subject, content refresh** (streaming, status changes): keep the active block by
  **id** (the shell identity) and keep the scroll.
  - If `following` and a new shell appears: advance to the new block. Paged: switch the
    page; spread: scroll its header into view. Carry the bottom pin across if it was on.
  - If not following: stay. The new shell simply appears at the right end of the rail.
- **`]` / `[`:** move to the next/previous block in chronological order, wrapping.
  - Paged: swap the page and scroll to its top.
  - Spread: scroll that block's header to the top, using the existing bounded
    `call_after_refresh` retry pattern from `_apply_spread_scroll`.
  - `following` is recomputed as `active == newest`.
- **`Ctrl+J/K` away and back:** switching to Context and back to Reply keeps the block.
  Block state is per panel, per subject.
- **Mode transitions** (streaming crosses the band, resize, split, ratio): anchor on the
  active block, exactly as 17d §3.7 anchors on the active card. Spread → paged activates
  the block at the viewport top and keeps the offset within it. Paged → spread scrolls
  that block's header to where it was.
- **Partial paint** (the immediate header-only paint during j/k): never touch block state.
  **Clear the rail on subject change** so it can never show the previous node's shells.
  Draw it again only from a full document of the current subject.
- **Splits:** each panel has its own block cursor, so a `Context | Reply` split or two
  Reply panels on different blocks (compare the gate with the code shell after it) just
  work.
- **Not persisted.** Block choice is subject-specific and ephemeral. `DeckPanelState` and
  `~/.sase/ace_agents_deck_state.json` do not change.
- **Rejected: sticking to a role across nodes** (for example staying on `--plan` as you
  press j). It is surprising and it defeats the triage loop. Newest-first landing is the
  better default.

### 5.5 Keys

| Key | Textual name | Action id | Behavior | Shared with (contextual duplicate) |
| --- | ------------ | --------- | -------- | ---------------------------------- |
| `]` | `right_square_bracket` | `next_card_block` | Newer block in the focused panel's active card (wraps) | `cycle_artifacts_subtab` (Artifacts) |
| `[` | `left_square_bracket` | `prev_card_block` | Older block (wraps); the first press from landing goes to the second-to-last shell | `cycle_artifacts_subtab_reverse` (Artifacts) |

Registration follows the 17d §3.4 checklist:

- `AppKeymaps` fields
- `default_config.yml` defaults (the core gotcha)
- `_BINDING_META` rows
- fallback `bindings.py` rows
- `check_app_action` gate (Agents tab, focused panel's active card has ≥ 2 blocks,
  `_prompt_input_owns_keys` respected)
- palette metadata and availability
- a help-modal row ("Older / newer card block", ≤ 32 chars)
- a *conditional* footer entry, `[/] blocks`, shown only when blocks exist
- `_CONTEXTUAL_APP_DUPLICATES` pairs
- deck-search structural exit keys (`_deck_search_host.py:35`)

The enforcement tests are the same four as in 17d.

**Mouse.** Clicking a rail entry activates that block (Textual `@click` meta on the rail
segments).

### 5.6 Visual design

**Typographic hierarchy.** It already exists; keep it.

| Level | Marker |
| ----- | ------ |
| Deck | rounded border in the deck accent |
| Card | heavy full-width `━━ ◆ Reply ━━` (spread) or the title tab pill (paged) |
| Block | light `─── AGENT (code) ─── 07:23:10 ───` in the shell's accent (purple agent, amber `⚙` monitor, lifecycle-colored `⋔` gate) |
| Turn | dim `─── 07:31:02 ───` |

Blocks add no new separator style. The phase divider *is* the block header. It carries
the new `sase_card_block` anchor meta.

**Block rail.** One row, docked between the panel's top border and its scroll.

- It uses the JUMP roster's vocabulary: number, then glyph and suffix label, then status
  glyph, all drawn from `agent_session_roster_entries`. That is the same source as the
  roster, so numbers, labels and colors match by construction.
- Entries are chronological, left to right, joined by `─` in the separator gray `#444`.
- The active entry is a `reverse bold <deck accent>` pill, identical to the active card
  tab in `titles.py`.
- Inactive entries are muted `#888`. Status glyphs keep their roster bucket colors: ✓
  green, ▶ yellow, ✗ red.
- An unfocused panel dims the whole rail, matching its dim title.
- The right edge carries a dim live-keymap hint at the widest tier only.

Single panel, deck paged on Reply, first landing (block-paged, newest):

```
╭─ ◆ MAIN ┃ Context │ Reply  2/2 ────────────────────────────────────────────╮
│ 0 --plan ✓ ─ 1 ⋔ --gate ✓ ─ ▐2 --code ▶▌                    [ older  ] newer │
│ ─── AGENT (code) ─── 07:23:10 ────────────                                   │
│ ─── 07:23:41 ─────────────────────────────                                   │
│ Reading the sticky-header code to see how the collapsed preview is built…    │
│ ─── 07:31:02 ─────────────────────────────                                   │
│ Implemented the XPROMPT card; running just check now.                        │
╰────────────────────────────────────────────── main 2 · files 1 · tools 109 ─╯
```

After one `[` (the second-to-last shell):

```
│ 0 --plan ✓ ─ ▐1 ⋔ --gate ✓▌ ─ 2 --code ▶                    [ older  ] newer │
│ ─── ⋔ GATE ─── 07:22:49 ──────────────────                                   │
│    Decision:  Tale ready for review: agent_header_xprompt_card.md            │
│    Kind:      plan                                                           │
│    Status:    TALE APPROVED                                                  │
```

Rail tiers (pure helper, widest fitting tier wins, like `deck_title`):

| Tier | Example | When |
| ---- | ------- | ---- |
| full | `0 --plan ✓ ─ 1 ⋔ --gate ✓ ─ ▐2 --code ▶▌   [ older  ] newer` | everything fits |
| windowed | `‹9 older · 9 ⚙ --mon-3 ✓ ─ 10 --code ✗ ─ 11 ⋔ --gate ✓ ─ ▐12 --code ▶▌ · 2 newer›` | many shells: active ± k neighbors plus counts |
| compact | `‹ 1 ⋔ ✓ ─ ▐2 --code ▶▌ ›` | narrow split: glyph-only neighbors |
| micro | `▐2 --code ▶▌ 2 older` | tiny width |

**Block-spread** (the Reply fits on its own): the same rail, with the active entry
derived from scroll. The content is today's chronological transcript without the
vestigial rule, opened so the newest block's header is as high as it can go.

**Deck-spread** (Context and Reply both fit): no rail. `[`/`]` scroll between block
dividers when the scroll-derived active card is Reply, and do nothing on Context.

```
│ AGENT PROMPT …                                                  │
│                                                                 │
│ ━━ ◆ Reply ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ AGENT REPLY · 2                                                 │
│ ─── AGENT (plan) ─── 07:12:12 ───────────                       │
│ …                                                               │
│ ─── AGENT (code) ─── 07:23:10 ───────────                       │
╰────────────────────────────── spread · main 2 · files · tools ─╯
```

**Heading.** In block-paged mode, drop `AGENT REPLY · N` (the rail says it) and show
`TRACEBACK`, when present, at the top of the **newest** block's page, which is the
landing page. In block-spread mode keep the heading and put the traceback first, as
today.

### 5.7 Architecture

All of this is presentation-only Textual state. No `sase-core` change is needed. The shell
list comes from the existing Python `concrete_agent_session_shell_rows`. If a web Agents
view ever needs the same "session timeline" (labels, status, order), that roster adapter
is the piece to move into `sase_core`, not the blocks.

1. **`widgets/decks/card_block.py`** (new):
   - `CardBlock(block_id, title, *renderables, meta: BlockMeta)`, where `BlockMeta` holds
     ordinal, label, glyph, accent and status bucket. It is a transparent wrapper like
     `CardPart`, marked `__sase_card_block__`.
   - Helpers `card_blocks(card)`, `card_preamble(card)` and
     `is_card_container(node)`. That last one returns true for either wrapper. Walkers
     call it instead of checking `__sase_card_part__`, so the next nesting level costs
     nothing.
2. **Builders.**
   - Wrap each phase in `_update_agent_session_display` (one loop serves both hint and
     non-hint) and in the `followup_agents` branch.
   - Add a `block_id=` keyword to `render_phase_divider`, `build_monitor_phase` and
     `build_gate_phase`. It stamps `Style(meta={"sase_card_block": id})` on the divider
     line.
   - Take block metadata from `agent_session_roster_entries`.
   - Drop the vestigial rule (A7).
   - **Document order stays chronological, so builders reorder nothing.**
3. **Walkers:**
   - `renderable_digest.py`: hash block id, title *and status*, so ▶→✓ invalidates the
     digest skip.
   - `_identity_header._find_carrier` and `_agent_display_hints._plain_renderable_content`.
   - `flatten_card_document`: flatten blocks too.
   - `split_card_parts`: preserve blocks.
   - **Hazard:** `_prepare_cached_hint_renderable` (`_agent_display_hints.py:70-100`)
     collapses each card's children into one `CachedRenderable`. That would erase the
     blocks in hint mode (`v`), and the rail would vanish. Cache the preamble and each
     block separately instead.
4. **Anchors.** Add `DECK_BLOCK_META_KEY = "sase_card_block"` and
   `PromptPanelSectionRole.BLOCK` in `_section_navigation.py`, plus
   `block_anchor_rows(width)` in `_section_view.py`.
5. **Pure model** (`widgets/decks/model.py` or `block_model.py`):
   - `BlockCursor(block_id, following)`
   - `resolve_active_block(block_ids, cursor, *, new_subject, partial)`
   - `cycle_block_id` (reuse `cycle_card_id`)
   - `decide_block_mode(...)`, a thin call to `decide_render_mode`

   Unit-test these exhaustively: new shell while following or not following, vanished
   block id, partial documents, wrap.
6. **View.** `MainDeckView` gains block-aware composition. Paged shows `[preamble when on
   newest] + active block`, with digest `f"{digest}:{card}:{block}"`. Spread shows the
   whole card, then lands.
7. **Panel.** Add a new mixin `DeckPanelBlocksMixin` in `widgets/decks/panel_blocks.py`.
   `panel.py` is 735 lines and already broke `toobig`'s 1000-line hard limit once during
   17d, so do not grow it. The panel keeps `{card_id: BlockCursor}` per subject and
   re-decides the block mode on `show_main_document`, resize and card switch.
8. **Rail.** `widgets/decks/block_rail.py` holds the pure `block_rail_text(entries,
   active, *, width, accent, focused) -> Text` with tiers, and `BlockRail(Static)`. It is
   pre-composed in `DeckPanel.compose` and toggled by CSS class, with no remounts (17d
   rule). It subscribes to theme changes like the chrome does.
9. **Wiring:**
   - `AgentDetail.cycle_focused_card_block(direction)` in `_agent_detail_decks.py`.
   - `action_next_card_block` / `action_prev_card_block` in
     `actions/agents/_panel_detail.py`.
10. **Search and `E`.** The search corpus adds block titles as sub-separators
    (`── Reply › 2 --code ──`). `E` exports the whole card; it is unchanged.
11. **Config.**
    - `AgentDecksSettings.block_spread_max_screens`, with the same coercion as
      `spread_max_screens`.
    - `default_config.yml` next to `spread_max_screens`, with a comment.
    - A `sase.schema.json` entry (`ace` has `additionalProperties: false`).
    - `docs/configuration.md`.
    - Parity tests.

### 5.8 Performance

- **j/k gets cheaper.** A block-paged Reply lays out one shell, not the whole card. With
  the sticky Reply this is the common case during triage.
- **The mode decision reuses the deck's lower bound.** Exact measurement only happens near
  the band and is cached per block and width. The rail is O(blocks), built from metadata
  already carried on each `CardBlock`, with no I/O or render.
- **No new workers, timers or refresh paths.** Block updates ride the existing Main
  document fan-out and `DetailPanelDebouncer`.
- **Gate.** `SASE_TUI_PERF=1 pytest -s -m slow tests/ace/tui/bench_tui_jk.py` in SINGLE
  and LEFT_RIGHT, before and after, with p95 < 16 ms. Add a bench fixture of a 10-shell,
  5,000-line session with Reply sticky. It should *improve*.

### 5.9 Reliability checklist

| Failure mode | Mitigation |
| ------------ | ---------- |
| The rail shows the previous node's shells during the j/k partial paint | Clear on subject change; draw only from a full document of the current subject |
| Index-based ids shift when a new shell starts | `block_id` = shell identity |
| The view jumps to a new shell while you read an old one | Follow only while on the newest block |
| Streaming crosses the block band | Hysteresis plus active-block anchoring |
| `]` pressed before anchors are published | Existing bounded `call_after_refresh` retry |
| Digest skip hides a status change | Digest includes block metadata |
| Hint mode loses the blocks | Per-block `CachedRenderable` |
| Test helpers assume `Text`/`Group` children (17d.2 left 9 such failures on master) | The wrapper stays transparent. Update helpers to `flatten_card_document`. Grep tests for `CardPart` assumptions before landing, and run the prompt-panel suites named in `sase-17d` notes #3 and #5 |
| Terminal mangles the key | Printable `[`/`]` |
| `toobig` | New modules; `panel.py` does not grow |

## 6. Alternatives considered

1. **One card per shell** (`Reply·plan`, `Reply·gate`, …). This breaks the sticky
   preferred card, because card ids become per-node. It floods the title tab strip and
   couples the deck's spread decision to the shell count. **Rejected.**
2. **Anchors only, no paging** ("minimal"). Keep Reply as one document, open it scrolled
   to the newest phase divider, and let `[`/`]` jump between dividers. This is about one
   small phase for roughly 60–70% of the value. It does not reduce render cost for huge
   sessions, and the newest block still ends at the bottom of a very long page. It is a
   **good fallback** if you want a quick win first. It is also literally phase 2's
   block-spread path, so none of the work is wasted.
3. **Accordion.** Fold older shells to one-line summaries with the newest one expanded.
   This is attractive, but folds are document-global state shared with `z…`, and 15
   collapsed rows eat a screen. The rail *is* the collapsed accordion, in one row.
   **Rejected; its idea is borrowed.**
4. **Literal reversal.** See P2 and A2. Viable only if applied to both modes and paired
   with scroll anchoring for growth above the viewport. **Not recommended.**
5. **`Ctrl+Shift+J/K` plus terminal reconfiguration.** It is not fixable inside tmux 3.5a:
   I verified that even `extended-keys always` + `csi-u` + `extkeys` collapses it
   (Appendix A). kitty's defaults also bind `kitty_mod+j/k` to scroll; those pass through
   in the alternate screen, per the kitty 0.41 source. `Alt+J/K` does reach tmux, but
   macOS kitty needs `macos_option_as_alt` (default off), so it is fragile.
   **Rejected as defaults; fine as user overrides.**
6. **Block position in the border title instead of a rail.** This saves a row, but the
   title already carries the card tab strip. Border labels are not per-segment clickable
   and there is no room for statuses. **Rejected.** The rail's micro tier covers tiny
   panels.

## 7. Implementation plan

No feature flag. Phase 1 is render-identical apart from the vestigial-rule removal, and
phase 2 lands the whole visible behavior at once, so no half-feature ever reaches users
(`sase_flags` rule). If phase 2 must be split, scaffold it with a `beta` flag
`card_blocks` that the epic removes.

| Phase | Size | Scope | Verification |
| ----- | ---- | ----- | ------------ |
| **1. `card-block-model`** | medium | `CardBlock` + helpers; builder wrapping (session + follow-ups); divider block meta; the `BLOCK` anchor role; every walker, including the hint-cache hazard; digest; A7 vestigial-rule removal | Partition tests per node kind; plain-text equivalence (modulo A7); digest changes on status; hint mode keeps blocks; anchors published; targeted `just fix-tui-screenshots` for the rule removal, inspected |
| **2. `card-block-view`** | large | Pure model and mode decision; config key; `MainDeckView` block composition and landing; `DeckPanelBlocksMixin`; `BlockRail` and its tiers; `[`/`]` with full registration; footer, help and palette; search exits; rail click | Pure-function tests; pilot tests (landing on newest, `[` → second-to-last, wrap, follow-latest with a streaming new shell, not-following stays, subject reset, partial paint, independent split panels, spread↔paged anchoring); PNG goldens (block-paged newest, after `[`, block-spread landing, windowed/compact/micro rails in a LEFT_RIGHT split, deck-spread with no rail); live `sase screenshot` inspection; j/k bench |
| **3. `card-block-docs`** | small | `docs/ace.md` ("Agent data decks and cards" gains card blocks and the triage-loop tip); `docs/configuration.md`; new glossary strand **Agent Data Card Block** (aka card block) plus an Agent Data Card strand update, both through `/sase_memory_write` | `sase memory init`; describe only shipped behavior |

**Independent bug** (discovered, separate from this feature): `jump_to_entry_forward`
(`ctrl+shift+o`) arrives as `Ctrl+O` under tmux, so "forward" jumps backward. Rebind it,
or accept that it is a kitty-outside-tmux-only key.

## 8. Open questions for you

1. Do you accept **`[` / `]`** (A1)? The alternative is `alt+[`-style chords or your
   original keys as personal overrides outside tmux.
2. Do you accept **chronological order with newest-first landing** (A2) instead of a
   reversed order?
3. Should `block_spread_max_screens` default to `1.5` like decks, or lower (for example
   `1.0`) so sessions page by shell sooner?
4. Should landing on a *running* newest block pin to its bottom (tail the live shell)?
   The alternative is its top, which matches today's paged-card behavior. My recommended
   default is the top, with `G` to pin.

## 9. Recommended solution

**Add agent data card blocks as a third level (deck → card → block). The first and only
wired use is an agent session's Reply card, with one block per sase shell phase
(`AGENT (role)`, `⚙ MONITOR`, `⋔ GATE`).**

- **Order and landing.** Blocks stay chronological. Every node lands on its **newest
  block**, and together with the sticky Reply card this makes j/k a one-keypress-per-
  session triage loop. `[` steps to older blocks and `]` to newer ones, wrapping. The
  first `[` reaches the second-to-last shell, which is exactly what you asked for,
  without reversing any content. Do not use `Ctrl+Shift+J/K`: on your tmux chain it
  arrives as `Ctrl+J/K` and would cycle cards.
- **Modes.** A card shown on its own (paged deck) spreads its blocks inline when they fit
  within `ace.agent_decks.block_spread_max_screens` (default `1.5`). Otherwise it pages
  them one shell at a time, with the same hysteresis as decks. A spread deck always shows
  its blocks inline. Block-spread lands with the newest block's header as high as it can
  go. Block-paged lands on the newest block's page.
- **Chrome.** Whenever blocks are navigable, a **one-row block rail** shows the session
  timeline in the JUMP roster's language. Numbers, suffixes, glyphs and status colors
  match the roster, and the active block is the same accent pill as the active card tab.
  The phase dividers stay the block headers. The vestigial rule at the top of Reply goes.
- **Reliability.** Block ids are shell identities. Following applies only on the newest
  block. The rail is cleared on subject change and never drawn from partial documents.
  Mode transitions anchor on the active block. The digest covers block status. Hint mode
  caches per block.
- **Build.** `CardBlock` is a transparent wrapper, like `CardPart`, consumed by a shared
  `is_card_container` walker helper. It needs a new `BLOCK` anchor role, a
  `DeckPanelBlocksMixin`, a `BlockRail` widget with tiered rendering, and the
  `next_card_block`/`prev_card_block` actions with full registration. It lands in two
  phases plus docs, with no flag and no `sase-core` change. It should make j/k *faster*
  on large sessions.

## Appendix A — Key-delivery probes (all on private tmux sockets)

Environment: the live TUIs run in tmux 3.5a panes (`sase:5`, `sase_ace_agents:1-2`).
`tmux show -s extended-keys` reports `off`. The client is `xterm-kitty` (kitty 0.47.0)
over sshd, with client features `bpaste,ccolour,clipboard,cstyle,focus,title` (no
`extkeys`).

1. **Textual 8.2.8 key events, tmux defaults, `send-keys`:**
   - `C-j` → `ctrl+j`; `C-S-j` → **`ctrl+j`**
   - `C-S-o` → **`ctrl+o`**; `C-o` → `ctrl+o`
2. **Same, with `extended-keys on` + `terminal-features xterm*:extkeys`:** unchanged
   (`C-S-j` → `ctrl+j`, `C-S-k` → `ctrl+k`).
3. **Same, with `extended-keys always`, both `xterm` and `csi-u` formats:** unchanged.
4. **Raw bytes into a real tmux client pty** (`TERM=xterm-kitty`, `extended-keys
   always`, `extended-keys-format csi-u`, `extkeys`), captured in the pane's raw-mode
   reader:
   - Shift+Enter `\x1b[13;2u` → `\x1b[13;2u` ✔ passes
   - Ctrl+Enter `\x1b[13;5u` → `\x1b[13;5u` ✔ passes
   - Ctrl+; `\x1b[59;5u` → `\x1b[59;5u` ✔ passes
   - **Ctrl+Shift+J `\x1b[106;6u` → `\n`** ✘ collapsed
   - **Ctrl+Shift+J `\x1b[27;6;106~` → `\n`** ✘ collapsed

   Conclusion: tmux 3.5a normalizes Ctrl+Shift+*letter* to Ctrl+*letter* even with
   extended keys fully enabled. No tmux config fixes `Ctrl+Shift+J/K`.
5. **kitty 0.41.1 defaults** (`/usr/lib/kitty/kitty/options/definition.py:3583,3686,3704`):
   `kitty_mod = ctrl+shift`; `kitty_mod+k` → `scroll_line_up`; `kitty_mod+j` →
   `scroll_line_down`. `window.py:1990-2001` makes both return `True` (pass through) off
   the main screen. The deployed `~/.config/kitty/kitty.conf` (7 lines) does not remap
   them.

## Appendix B — Session size method

The script scanned `~/.sase/projects/*/artifacts/ace-run/202609/2[0-5]/*/agent_meta.json`
(1,308 files). It grouped them by `agent_session`, which is set on 70 sessions. For each
shell it counted lines of `live_reply.md` / `response.md` and took the maximum of the
two. Monitor proc logs are excluded, so the reply-size figures are lower bounds. A
spot-check of `sase-17x.13.9` (8 shells) totalled 679 reply lines.
