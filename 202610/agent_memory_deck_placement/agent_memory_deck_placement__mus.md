# Memory Deck for the Instruction Bundle: Research & Recommendation

## Summary

Moving the selected agent's instruction bundle out of the Files deck and into a
dedicated memory deck is a good idea, with one adjustment: **do not make it a
bundle-only deck**. The bundle is one of several already-existing,
already-audited "what did this agent know and read" surfaces that are currently
split across three places (Files deck tail, Main deck `SASE CONTEXT` lanes,
header-panel `AGENT MACRO`). A memory deck that unifies exactly those surfaces
— bundle, audited reads, launch row, macros/skills — is coherent, discoverable,
and removes a real category error (the bundle is not a file the agent
"touched"). The record deck is the wrong home for these cards: it answers "what
*is* this run" (lifecycle/provenance/relations/links), not "what did it know".
Recommended deck: `❖ MEMORY` with four cards — `Bundle`, `Reads`, `Macro &
Skills`, `Workspaces` — reusing the existing lane loaders, with the Files-deck
bundle pages removed (not duplicated) and the Main-deck `SASE CONTEXT` lanes
kept as compact summaries that link into the new deck.

## 1. Current state (verified against the tree)

### 1.1 The five agent data decks

`src/sase/ace/tui/widgets/decks/spec.py` registers exactly five decks, cycled
by `Ctrl+N`/`Ctrl+P` and jumped to via the `p` picker (`m`/`f`/`t`/`n`/`r`):

| Deck | Cards | Content |
|------|-------|---------|
| Main (`◆ MAIN`) | `Context`, `Reply` (or single `Summary` for clans/tribes) | Details, prompt, reply, `SASE CONTEXT` lanes |
| Files (`▤ FILES`) | one card per file page | commit diffs, live diff, linked-repo diffs, extra files, **instruction-bundle pages last** |
| Tools (`λ TOOLS`) | `⚒ Runs`, `LLM Calls` | tool runs + tool-call timeline |
| Final (`⊛ FINAL`) | `Overview` + per-finalizer cards | how turns landed |
| Record (`≡ RECORD`) | `Lifecycle`, `Provenance`, `Relations`, `Links` | recorded facts about the run |

Documented in `docs/reference/tui/agent-statuses.md` ("Agent Data Decks and
Cards"). Tools/FINAL/RECORD have no deck views (always automatic); Main and
Files support spread/paged/block views.

### 1.2 Where the instruction bundle lives today

`src/sase/ace/tui/widgets/file_panel/_instruction_bundles.py` +
`_file_list.py::desired_file_pages`: bundle paths come from
`sase.instructions.manifests.run_bundle_paths(artifacts_dir)` (root-then-helper
records under `<artifacts>/instructions/`), are cached off the event loop, and
are **appended last** after commit slots, live diff, linked slots, and
`extra_files`. `source_label_for_slot` tags them `bundle` when the path
contains `/instructions/` and ends in `.md`.

Consequences of this placement:

- The bundle competes for position with diffs, which are the Files deck's
  stated purpose ("Diffs and files the agent touched", `spec.py` blurb). The
  deck subtitle counts it as just another file.
- Default-page logic (`pages[0]`) never prefers the bundle; it is reachable
  only by paging to the tail.
- Helper bundles (native-helper second records) are pages with no visible
  root/helper distinction in the Files deck chrome.
- Availability probing (`availability.py::probe_files_deck`) conflates
  bundle-only agents with diff-bearing agents: a bundle-only agent reports
  Files content, which overstates "this agent changed files".

This is the category error the proposal correctly identifies: the bundle is
*input context*, not *output artifact*.

### 1.3 What "memory the agent used" already consists of

There is more audited memory state than just the bundle, and it is currently
split across two more surfaces:

**Main-deck `SASE CONTEXT` lanes** (`_agent_context.py`, `CONTEXT_LANE_ORDER =
PLAN, BEAD, ARTIFACTS, MEMORY, GLOSSARY, SKILLS, WORKSPACES`):

- `MEMORY` lane (`_agent_memory_reads.py`): audited `sase memory read` events
  from `sase.ace.tui.memory_reads` (newest 5 + overflow footer, per-event
  `reason:`, hint-numbered report/file targets, version chips/pins). Crucially
  it already renders a **launch row first** (`MemoryLaunchRow`,
  `_agent_memory_versions.py::resolve_launch_row`): "Instructions as launched"
  (explicit bundle, with delivery channel + byte size + `bytes match` /
  `MISMATCH` chip) or "AGENTS.md as launched" (native/fallback/pre-E3
  snapshot rows, git-blob-pinned or `workspace_head`). So the "what did it
  launch with" question is *already answered in miniature* in Main.
- `GLOSSARY` lane: retired `sase glossary read` log only; current
  `sase memory read glossary:<kw>` reads surface in `MEMORY`. The lane is
  legacy and explicitly documented as such in `agents-main-deck.md`.
- `SKILLS` lane (`_agent_skill_uses.py`): audited skill uses
  (`sase.ace.tui.skill_uses`, newest 5 + overflow, with reasons). This is the
  closest thing to "macros the agent used" that is audited at runtime.
- `WORKSPACES` lane (`_agent_opened_workspaces.py`): opened-workspace events.
- `PLAN`/`BEAD`/`ARTIFACTS` lanes: intent, work items, and artifact
  interactions — *not* memory, and should stay where they are.

**Header-panel `AGENT MACRO`** (`agent-sessions.md`, `agents-main-deck.md`,
`pager.md`): the *launch-time* macro/input text (the raw prompt the run was
fanned out from), rendered in the sticky header, not the scrolling body. It is
the invocation input, not a record of macros consumed mid-run. There is **no
audited per-macro-use log** comparable to memory-reads/skill-uses; macro
consumption mid-run surfaces indirectly (prompt text, skill log for
skill-backed macros, tool calls).

**CLI counterparts** (all read-only, all reusable as deck data sources):
`sase instructions show AGENT` (bundle bytes + digest check, `-l`/`-n`/`-H`
for helper selection), `sase instructions verify`, `sase instructions readout`
(handoff-aware misses + memory reads), `sase skill log`, and the memory-read
report generator (`memory_read_report_path`).

## 2. What cards/blocks a memory deck should contain

Working from the litmus test "what did this agent know, and what did it read",
the deck has four natural cards. Each reuses an existing loader; none needs a
new audit pipeline.

### Card 1 — `Bundle` (the proposal's core)

- Blocks: one block per recorded invocation bundle, root first then helper
  (the order `run_bundle_paths` already returns), each headed by its manifest
  facts: sequence `NN`, provider, actor (`sase_root`/`native_helper`),
  delivery channel/status, byte size, digest check (`bytes match`/`MISMATCH`).
  This fixes today's missing root/helper distinction.
- Body: the recorded bundle bytes (as `sase instructions show` prints), with
  the existing section-table view (`-s`: id, layer, status, bytes,
  `tokens_est`, source) as a collapsed/first-block summary. Section-level
  blocks are the honest "card block" granularity: bundles are long, and the
  existing deck block machinery (`(`/`)` older/newer block, block rail) fits
  section navigation exactly.
- Fallback block: when no `instructions/` dir exists (native/fallback/pre-E3
  runs), show the launch-row equivalent — workspace `AGENTS.md` snapshot state
  or `workspace_head` — with an explicit "no recorded bundle; native delivery"
  label rather than an empty state. The `resolve_launch_row` logic already
  computes this; reuse it.
- Integrity failures (`MISMATCH`, missing bytes) get a visible warning block,
  matching the FINAL deck's honest-failure tone.

### Card 2 — `Reads` (audited memory + glossary reads)

- The full (uncapped) `MEMORY` lane event list: every audited
  `sase memory read` with timestamp, selector/canonical path, reason, and
  hint/report targets — i.e. the lane's newest-5 view without the cap, plus
  the version chips. Blocks: one per read event (or per distinct file, newest
  event first) so `(`/`)` walks the read history.
- Fold the legacy `GLOSSARY` lane in as a trailing `Glossary (retired log)`
  section of this card rather than its own card: it is read-only history with
  no new writes, and a whole card would over-promise its importance. This also
  retires a lane from `SASE CONTEXT` display pressure over time.
- Do **not** include artifact `Reads` here: audited `sase artifact read`
  events live in the `ARTIFACTS` lane, are about output/input artifacts, and
  moving them would split the ARTIFACTS lane's Beads/Reads/Commits/Deltas/
  Files grouping that `agents-main-deck.md` documents as a unit.

### Card 3 — `Macro & Skills` ("macros?" in the proposal)

- Top block: the launch macro (`AGENT MACRO` bytes — the invocation input),
  attributed as launch input, not as something the agent "used". This resolves
  the proposal's "maybe macros?" by giving the only always-available macro
  content a precise, non-misleading label.
- Remaining blocks: audited skill uses (full `SKILLS` lane list, uncapped),
  each with skill name, timestamp, reason, and producing member label on
  sessions. Skill-backed macros are thus covered by evidence, not by guessing.
- Explicitly do **not** invent a "macros consumed" list: no audit source
  exists, and prompt-text grep would be unreliable. If macro-use auditing is
  wanted later, it is a new collector (`sase macro` invocation log analogous
  to `tool_calls.jsonl`/skill log), not deck design. Say so in the deck's
  empty state ("mid-run macro expansion is not audited; see prompt text").

### Card 4 — `Workspaces` (small, possibly foldable into Reads)

- Full opened-workspaces event list (uncapped lane). This is the weakest card:
  it answers "where did it look" rather than "what did it know". Keep it only
  if the deck needs symmetry with `SASE CONTEXT`; otherwise merge as a
  trailing section of `Reads`. My recommendation: ship it as its own card only
  if the lane has content for the selection, else omit (the clan/session
  pattern of omitting known-empty sections already establishes this
  convention). A four-card deck with one routinely-empty card is worse than a
  three-card deck with an occasional fourth.

### Blocks, not cards, for sessions

Session rows already aggregate member lanes with role labels (`plan`,
`coder`, …). The memory deck should follow the Reply card's block precedent:
one block per producing turn/member inside `Reads` and `Macro & Skills`,
newest-block landing, `(`/`)` navigation, arrival dots. Do not create
per-member cards; the card count must stay stable across selections or the
`Ctrl+J`/`Ctrl+K` muscle memory and the persisted preferred-card logic break.

## 3. Where these cards do NOT belong

- **Not in RECORD.** RECORD's four cards (Lifecycle, Provenance, Relations,
  Links) answer "what is this run and where does it sit in the graph". They
  are fixed-card, always-available, identity-grade facts — `probe_record_deck`
  returns `True` unconditionally. Memory content is variable-length,
  content-grade, and often absent (agents with no reads). Mixing them would
  (a) break RECORD's "always four cards" contract and its bare-`record`
  switcher, (b) overload the deck whose picker blurb users already understand,
  and (c) put 500-line bundle bodies next to one-line capability flags. The
  proposal's instinct to ask about RECORD is right to check, but the answer is
  no: keep RECORD as the identity deck. The one legitimate RECORD-adjacent
  item — the bundle's *existence*/digest as a provenance fact — is already
  covered by keeping a compact launch row visible in Main (see §4).
- **Not left in Files.** §1.2's category error stands: diffs are outputs, the
  bundle is input. Bundle pages should move, not duplicate — duplication would
  fork preferred-card state, availability counts, and the `p`-picker file
  counts across two decks for one backing store.
- **Not merged into Tools.** The Tools deck is a timeline of *actions* (runs,
  calls). Memory is *context*. The existing cross-links (LLM-call rows linking
  to run blocks) show the right pattern for relating the two — link, don't
  merge. One link worth adding: skill-use rows → the `⚒ Runs`/LLM-call rows
  they caused, if attributable; otherwise skip.

## 4. Critique of the plan and adjustments

**Is it a good idea? Yes**, for three reasons: (1) it fixes a real miscategorization
(bundle-as-output-file); (2) it collects four currently-scattered
know/read surfaces into one navigable place; (3) all data sources already
exist, so this is presentation work with no new collectors, no schema, and no
Rust-boundary crossing (presentation-only Textual state stays in this repo per
the `rust_core_backend_boundary` memory).

**Adjustments (called out as requested):**

1. **Scope up from "bundle deck" to "memory deck" — but only to audited
   content.** The proposal's "other types of memory (and maybe macros?)" is
   directionally right; constrain it to the four cards in §2. In particular,
   do not pull `PLAN`/`BEAD`/`ARTIFACTS` lanes in — they are intent/work/output,
   and `SASE CONTEXT` would be gutted if they left.
2. **Keep compact `SASE CONTEXT` lanes in Main; link, don't remove.** Main's
   lanes are the triage view (counts + newest 5 + launch row). The memory deck
   is the diagnosis view (full bodies). Deleting the lanes would punish the
   common case (glance) to serve the rare case (audit). Add per-lane affordances
   (`p m`-style jump or a `MEMORY`-lane suffix like the slow-tools lane's `p t`
   pointer) instead. This mirrors the established slow-tools → LLM-Calls and
   verdict-suffix → Runs link patterns.
3. **Move, don't copy, the bundle pages.** Remove `instruction_bundle_pages`
   from `desired_file_pages` when the memory deck ships, and re-point
   availability: bundle-only agents should report Files-empty. Otherwise every
   count, picker row, and preferred-card default double-reports.
4. **Do not add a "macros used" card without an audit source.** Ship launch
   macro + skill uses (§2, card 3) and file the collector as follow-up work if
   wanted. A grep-derived macro list would be the deck's one dishonest card.
5. **New-deck cost is real but bounded — name it.** A sixth deck touches the
   deck registry (`spec.py`), cycle order, picker letters (free letters are
   scarce: `m`/`f`/`t`/`n`/`r` are taken — `y`/`e`/`o` are candidates, or a
   two-key `p m` reuse with disambiguation), persisted deck state
   (`ace_agents_deck_state.json`), availability probes, spread/paged policy
   (memory bodies are long: default paged, like Tools), and the
   deck-switcher/picker docs. It also slightly lengthens `Ctrl+N`/`Ctrl+P`
   cycles for everyone. The alternative — three new RECORD cards — is cheaper
   but wrong (§3); the other alternative — expanding Main's lanes in place —
   preserves Main's triage role poorly (Main is already the longest document).
   The sixth deck is worth it, but the plan should budget the chrome work,
   not just the cards.
6. **Archive/clan/session/tribe behavior must be specified.** Archived runs
   must hydrate the memory deck from retained bundles (the Archive already
   promises "full prompt, reply, diffs, tool calls, and Record cards" —
   extend that list); clan containers and tribe panels have no single bundle
   and should show the deck as unavailable rather than aggregated (bundles do
   not aggregate meaningfully, unlike tool-call timelines); session containers
   aggregate with role labels like the lanes do today.

## 5. Recommended solution

Ship a sixth agent data deck, `❖ MEMORY` ("What this agent knew and read"),
with cards `Bundle` · `Reads` · `Macro & Skills` · (`Workspaces` when
non-empty), per §2, built exclusively on existing loaders (`run_bundle_paths`
/ `launch_root_bundle`, memory/glossary/skill/workspace lane loaders,
`resolve_launch_row`, `sase instructions show` projections). Move bundle pages
out of the Files deck; keep capped `SASE CONTEXT` lanes in Main as triage with
jump affordances into the new deck; leave RECORD untouched. Default the deck
to paged (long bodies), block-navigate sections/reads with the existing
`(`/`)` + block-rail machinery, and specify Archive hydration plus
clan/tribe-unavailable semantics before build. File one follow-up (not in
scope): an audited macro-expansion log if "macros consumed" ever needs to be
more than launch-macro + skill uses.

## Sources inspected

- `src/sase/ace/tui/widgets/decks/spec.py`, `availability.py`, `panel_record.py`
  (deck registry, probes, RECORD handling)
- `src/sase/ace/tui/widgets/file_panel/_file_list.py`,
  `file_panel/_instruction_bundles.py` (bundle-as-Files-tail)
- `src/sase/ace/tui/widgets/prompt_panel/_agent_context.py`,
  `_agent_memory_reads.py`, `_agent_skill_uses.py`, `_agent_memory_versions.py`
  (SASE CONTEXT lanes, launch row, skill uses)
- `src/sase/instructions/manifests.py` (`run_bundle_paths`,
  `launch_root_bundle`), `docs/reference/memory/instruction-bundles.md`
- `docs/reference/tui/agent-statuses.md`, `agents-main-deck.md`,
  `agents-deck-panels.md`, `files-and-preview.md`,
  `docs/reference/agents/agent-sessions.md` (deck/card contracts, header
  `AGENT MACRO`, Archive hydration promise)
