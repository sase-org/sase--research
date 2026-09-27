# Integrating `sase tool` into the Agents tab (and beyond): UX design research

Research report (mus). Independent assessment of how best to surface the
`sase tool` command — named project tools plus the machine-local ToolRun
ledger — inside the SASE TUI, with focus on the Agents tab. Evaluates the two
proposed integrations (a new card in the Tools deck; a hammer icon with a
count on agent nodes) against the data model, the existing deck system, and
TUI data-fetch patterns, and ends with a recommended solution.

## Summary

Both proposed integrations point in the right direction but each has a real
flaw, and they share one root problem: **the existing Tools deck is not about
`sase tool` at all**. The Tools deck (λ, picker `t`) renders the *LLM
tool-call timeline* — transcript-derived provider calls (Read/Edit/Bash
inside the agent's conversation) sourced from agent artifact dirs
([spec.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_48/src/sase/ace/tui/widgets/decks/spec.py:44)).
A ToolRun is something else entirely: a *guarded process execution* recorded
in a machine-local ledger with its own lifecycle (created → running →
succeeded/failed/interrupted/lost/signaled), duration, exit code, stage
timeline, and verdict receipt. Conflating the two inside one deck would teach
users that "tool calls" and "tool runs" are the same thing. They are not, and
the distinction matters most exactly when debugging (`sase tool failures`
groups by failure *signature across agents* — a cross-agent concept that fits
no single transcript timeline).

Recommendation in one paragraph: **add a fifth deck, RUNS, scoped to the
selected node's attributed ToolRuns, following the FINAL-deck precedent; add
a compact run-count chip with failure coloring to agent rows as the ambient
signal (the hammer idea, restyled to fit row chrome); keep the Tools deck
untouched.** Phase it so the cheap data-path validation (cached per-agent
counts) lands before the deck UI. Details and rationale below.

This is presentation-only Textual state (deck registry, probes, views, row
chrome) plus read calls through the existing `sase_core_rs` binding, so under
the Rust core boundary it stays in this repo with no `sase-core` change and
no `sase-core-revision.txt` bump — unless a new server-side aggregation is
wanted (flagged as an open question in §5).

## 1. What `sase tool` actually offers the TUI

Five CLI surfaces exist today
([query.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_48/src/sase/tool/query.py:1),
[receipt_report.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_48/src/sase/tool/receipt_report.py:1),
[failures.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_48/src/sase/tool/failures.py:1)):

| Surface | Content | TUI value |
|---|---|---|
| `list` | Named project tools with LAST result + TYPICAL (median) duration | Inventory; low Agents-tab value |
| `runs` | ToolRun ledger, newest first: ID / TOOL / STATE / DURATION / ARGV; filters `-A agent`, `-t tool`, `-s state` | **Core**: per-agent run timeline |
| `show` (`-l`/`-F`/`-j`) | One run: full envelope, retained-log replay, follow-until-settle streaming | Drill-down from a run card |
| `failures` | Grouped failure signatures with RUNS / AGENTS / FIRST / LAST / OWNER columns | Triage; cross-agent, not per-node |
| `receipt(s)` | Verdict receipts + content-equivalent repeat opportunities | "Can I skip re-running this?" |

Three facts about the data model drive the whole design:

1. **Agent attribution already exists.** Every run records `agent` from
   `SASE_AGENT_NAME`/`SASE_TOOL_RUN_AGENT`
   ([executor_recording.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_48/src/sase/tool/executor_recording.py:38)),
   and `runs -A <agent>` filters on it. The agent-node → runs join key is
   free; no recording change is needed.
2. **Reads are TUI-cheap.** The Python adapter is a thin pass-through over
   the `sase_core_rs` binding with a 250 ms busy timeout
   ([tool_run.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_48/src/sase/core/tool_run.py:269)).
   A `tool_run_summary` aggregate binding also already exists alongside
   `tool_run_list`/`tool_run_show` (same file) — plausibly a one-call source
   for per-agent counts, though its payload shape needs verification (§5).
3. **Runs outlive and out-scope transcripts.** The ledger also records
   `owner_kind`/`owner_id` (proc/monitor owners), `parent_run_id` (nested
   runs), `project`, `workspace`, and `bead`
   ([executor_recording.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_48/src/sase/tool/executor_recording.py:38)).
   ToolRuns therefore exist for rows that have *no* transcript tool calls at
   all — monitors, procs, clan containers — and for runs whose agent is long
   settled. Any surface gated on transcript availability will systematically
   hide them.

And the current TUI integration state is exactly zero: no file under
`src/sase/ace/` references `tool_run`, `ToolRun`, or "tool run". This is
greenfield, which means the naming decision made now sticks.

## 2. What the Agents tab offers today (the integration surface)

- **Left: node/tribe list.** Rows carry dense leading chrome (gutter, marks,
  type/provider badges) owned by
  [_agent_list_render_agent_prefix.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_48/src/sase/ace/tui/widgets/_agent_list_render_agent_prefix.py:1)
  plus a status parenthetical
  ([_agent_list_render_agent_status.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_48/src/sase/ace/tui/widgets/_agent_list_render_agent_status.py:1)).
  Precedents for count chips exist: the monitor `⚙N` lane counts and
  `agent_count_chip.py`. Row space is genuinely scarce (list column clamped
  ~60–130 cells, per prior decks research), so anything added must earn its
  cells.
- **Right: deck panels.** One panel type, four registered decks
  (MAIN ◆ / FILES ▤ / TOOLS λ / FINAL ⊛) with picker keys `m`/`f`/`t`/`n`,
  count nouns, and accent classes
  ([spec.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_48/src/sase/ace/tui/widgets/decks/spec.py:23)).
  Each deck has a no-I/O availability probe driving subtitles and empty
  states
  ([availability.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_48/src/sase/ace/tui/widgets/decks/availability.py:1));
  the Tools probe returns content keyed on the *transcript tool-call cache*
  (`cached_tool_call_count`) and goes empty for clan containers, named procs,
  and pinned attempts.
- **FINAL is the precedent to copy.** It was added later as a full deck with
  its own directory (`decks/final/`: document, enrichers, instance cards,
  live view, loader, overview card, run blocks, view) — i.e., node → owned
  records → per-record cards is an established pattern, and "node → its tool
  runs" is structurally identical to "node → its finalizer instances".

## 3. Evaluating the two proposed integrations

### 3.1 A new card in the Tools deck — not recommended as framed

Problems:

1. **Semantic collision.** The Tools deck's contract is "LLM tool-call
   timeline" (its blurb, its count noun `call/calls`, its λ glyph, its
   transcript sources). A ToolRun card would sit beside transcript calls with
   a different grain (one guarded `check` run may *contain* hundreds of
   transcript calls, or zero — e.g. a monitor-owned run with no agent
   transcript at all), a different time base, and a different lifecycle. Users
   would reasonably but wrongly infer that the numbers reconcile.
2. **Wrong availability gate.** The Tools probe goes empty exactly where
   ToolRuns are most interesting: non-entry rows (clans, procs, monitors own
   runs via `owner_kind`), pinned attempts, and agents whose transcript cache
   is cold. A ToolRun card inside this deck inherits a gate designed for a
   different data source.
3. **Count-noun and picker confusion.** The deck subtitle counts "calls";
   mixing "runs" into the same count corrupts the subtitle's meaning, and
   there is no per-card filtering story once both record types share one
   panel.

Verdict: the instinct (runs belong in the detail area, next to calls) is
right; the container is wrong.

### 3.2 Hammer icon + count on agent nodes — recommended with restyling

This is the better of the two ideas because it answers the ambient question
("which nodes actually *did* anything expensive?") that no deck can answer —
decks only speak for the selected node. Assessment:

- **Feasibility: yes.** Row chrome already hosts glyphs + counts (⚙ gear for
  monitors with settled styling, gate glyphs, provider emoji badges), and the
  status parenthetical has room for one compact chip. Precedent for
  settled-vs-live styling (grey vs colored gear,
  [_agent_list_render_agent_prefix.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_48/src/sase/ace/tui/widgets/_agent_list_render_agent_prefix.py:64))
  maps directly onto run states (live: running/created/signaled;
  failed: red; settled-ok: dim).
- **Two refinements.** First, prefer a text-glyph chip over the 🔨 emoji:
  rows use text glyphs everywhere except provider badges, and emoji width
  varies by terminal. A `⛏`-style glyph or a short `T3`/`run:3` chip in the
  existing count-chip style fits better; keep the hammer metaphor in the deck
  glyph instead (see §4), where one larger icon is affordable. Second, the
  count must come from a **cached aggregate** (one `tool_run_summary`-shaped
  call, TTL'd like the tool-call cache), never one `tool_run_list` per row —
  the list can hold dozens of nodes and per-row queries would be an N+1
  against a SQLite store with a 250 ms busy timeout each.
- **Triage value is the justification.** A red failure-tinted count on a
  FAILED agent row links "this agent failed" to "and its `check` run failed
  with signature X" at a glance — the `failures` table's AGENTS column shows
  this join is already the triage path in CLI form.

## 4. Recommended solution

**A fifth deck (RUNS) + a row run-chip, phased. Tools deck untouched.**

### Phase 0 — data path + row chip (cheap, validates everything else)

1. Add a cached per-agent run-count query (prefer the existing
   `tool_run_summary` binding if its shape serves; else one `tool_run_list`
   per *selected* agent plus a bounded summary query for visible rows —
   verify before building).
2. Render one compact chip on agent rows with content, styled by worst state:
   live (running/created/signaled) > failed > settled. No chip when the
   agent has no attributed runs. Reuse the settled/live styling convention
   from the monitor gear.
3. Success criterion: counts match `sase tool runs -A <name>` for spot
   checks; no measurable frame cost (cache-hit path only on the event loop,
   fetch off-loop exactly like `build_slow_tool_sources`).

### Phase 1 — RUNS deck (the main integration)

- Register `DeckId.RUNS` in the deck model + `DeckSpec` (name `RUNS`,
  count noun `run/runs`, blurb "guarded tool runs attributed to this node",
  distinct glyph — hammer-equivalent text glyph — and accent). Note: picker
  keys `m`/`f`/`t`/`n` are taken (prior decks research flagged keymap churn
  as the riskiest part of deck work); pick `r` if free, else a `g`-prefixed
  binding, and treat the keymap as an explicit decision, not an afterthought.
- Availability probe: content = attributed-run count from the Phase-0 cache;
  unlike the Tools probe, it must work for *every* row type (entries, clans,
  monitors, procs, pinned attempts) since attribution is by name/owner, not
  transcript.
- Cards: one card per run (newest first, mirroring `runs` ordering) —
  header line `TOOL · STATE · DURATION · EXIT`, subline truncated argv;
  expanded card adds the stage timeline (`attach_timeline`/
  `format_stage_progress` already exist in CLI form), exit code, receipt
  pointer when present, and log tail. Follow the FINAL deck's
  document/loader/view split (`decks/final/` as the template).
- Deliberately read-only in Phase 1. Actions (`stop`, follow `-F`, full log
  replay `-l`) reuse existing bindings and come in Phase 2 once the read
  path proves its caching story.

### Explicit non-goals / later

- **Do not merge into the Tools deck**, and do not rename it yet. If the
  TOOLS-vs-RUNS confusion materializes in practice, the cheap fix is
  renaming the Tools deck's display name to CALLS (keeping `DeckId.TOOLS`
  and picker `t` stable); that is a product decision to revisit with usage
  evidence, not now.
- **`list` (named-tool inventory), `failures`, and `receipts` do not belong
  in the Agents tab.** They are project-level, not node-level. Their natural
  home is a future project-scoped surface (or the existing CLI), not a deck.
- Monitor/proc-owned runs (via `owner_kind`) will appear under their owner
  rows' RUNS decks automatically once the probe keys on attribution rather
  than row type — no special casing needed.

## 5. Open questions (verify during implementation, not before)

1. `tool_run_summary` payload shape — does one call yield per-agent
   counts/states for all visible rows, or is a new core aggregation needed?
   (If the latter, that is the *only* piece crossing the Rust boundary, and
   it needs the `sase-core` checkout + revision-bump procedure.)
2. Agent-name stability as a join key: renames, session turns sharing a
   name, and clan children — confirm `runs -A` semantics match the row
   identity the TUI holds (`Agent.identity` vs display name).
3. Live-update cadence for running runs (the `-F` follow path implies a
   streaming read; the deck needs a poll/refresh story consistent with the
   existing stale-threshold refresh, not a new timer).
4. The RUNS picker key and whether a fifth deck forces the deck-cycle order
   (`active_deck_cycle`) or panel-layout defaults to change.

## 6. Bottom line

Rank-ordered options:

1. **RUNS deck + row run-chip (recommended).** Clean semantics, follows the
   FINAL precedent, ambient + drill-down coverage, read path needs no core
   change.
2. **Row chip only.** Half the value (no drill-down), but a fine Phase-0
   stopping point if deck budget is tight.
3. **New card in the Tools deck (not recommended).** Cheapest to build,
   but teaches users a false equivalence between transcript calls and
   guarded runs, and inherits an availability gate that hides exactly the
   runs worth seeing.
