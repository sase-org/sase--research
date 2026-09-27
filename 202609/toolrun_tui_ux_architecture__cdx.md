# ToolRun UX in the SASE TUI

**Researcher:** cdx  
**Date:** 2026-09-27  
**SASE revision inspected:** `21d4e12c8c43c56ebeaa24ff245e7eafbd13c9b5`  
**sase-core revision inspected:** `f1ddeb5395c9ff2bf097607f6c18ea49d0751b83`

## Executive conclusion

The best Agents-tab integration is a second **Tool Runs** card inside the existing
**Tools** deck, beside **LLM Calls**. It should not replace or merge with LLM Calls:
provider calls answer “what did the model invoke?”, while ToolRuns answer “what durable
SASE-managed execution happened, how did it settle, and what evidence did it leave?”
They are adjacent concepts at different abstraction levels.

The proposed hammer-and-total-count badge is not a good default. A total is
retention-bounded, local-machine-only, hard to aggregate correctly for sessions and
monitors, and mostly repeats activity rather than conveying urgency. Ship no Agent-row
ToolRun badge initially. If the card proves too easy to miss, add a later
**attention-only** marker using the Tools deck's existing `λ` identity: for example
`λ!2` for two retained runs with new failures, `λ?1` for an unknown failure, or `λ▶1`
for an active run. Never show a success count on every node.

The contextual card alone cannot serve project-wide history, unattributed/human runs,
catalog discovery, failure grouping, or launching. The complementary global surface
should be an eighth, last-position **Tools** pane in the SASE Admin Center, with
**Runs**, **Catalog**, and **Failures** views and a master/detail run inspector. Putting
it last preserves every existing numeric Admin Center shortcut. It should cross-link
to Agents and Procs rather than duplicating those surfaces.

Implementation should start below the widgets: add a compact, batch, read-only ToolRun
browse projection in `sase_core`, expose it through `sase_core_rs`, and then build the
Agents card. The current API is too heavyweight and too narrow for responsive TUI use.

## What `sase tool` actually represents

The CLI is several related products under one command group:

- a project-owned named-tool **catalog** (`list`);
- an **execution launcher** for named and ad-hoc commands (`run`, including handoff);
- a durable machine-local **run ledger** (`runs`, `show`);
- **lifecycle control** (`show -F`, `wait`, `stop`);
- a **failure intelligence** view (`failures` and per-run triage);
- **receipt/proof** queries and repeat-opportunity analytics (`receipt`, `receipts`).

Trying to represent all of this with one card or one badge would produce an overloaded
surface. The TUI should distribute the capabilities by user intent rather than mirror
CLI subcommands one-for-one:

| User intent | Best TUI home |
| --- | --- |
| What did this selected agent execute? | Agents → Tools → Tool Runs |
| What provider calls did this agent make? | Agents → Tools → LLM Calls |
| What is running or failing on this machine/project? | Admin Center → Tools → Runs |
| What named commands are available, and how have they behaved? | Admin Center → Tools → Catalog |
| Which failure signatures are current? | Admin Center → Tools → Failures |
| Who owns the output process? | Cross-link to Admin Center → Procs |
| What did a selected run emit? | ToolRun detail/output, loaded on demand |
| Is current verification evidence covered? | Catalog/detail receipt chip; Statistics for aggregate opportunities |

This separation also respects SASE's own vocabulary. `docs/tool.md`, the ToolRun
glossary strand, and the LLM Calls glossary strand explicitly distinguish a ToolRun
execution record from the provider-call artifact shown by the current Tools deck.

## Findings from the current implementation

### The Tools deck is the right local container

The Agents detail area already has the correct information architecture:
deck → card → optional card block. `src/sase/ace/tui/widgets/decks/spec.py` declares
the Tools deck, while `panel_chrome.py` currently hard-codes its single `LLM Calls`
card. `DeckPanelState.preferred_cards` already persists a preferred card per deck.
Therefore adding a card is consistent with the model and less disruptive than adding
another deck.

This matters because the live code now cycles four decks—Main, Files, Tools, and
FINAL—even though some documentation still describes three. A fifth top-level deck
would lengthen a frequently used cycle and force the user to choose between two
tool-related decks. A second Tools card uses the existing `Ctrl+J` / `Ctrl+K` card
navigation and preserves the conceptual grouping.

The Tools deck currently uses a bespoke `LLMCallsPanel`, not the generic card-document
view used by Main and FINAL. The new card will therefore require either:

1. refactoring Tools into a two-card document host, or
2. teaching a Tools-specific host to switch two child views.

The first option is architecturally better. FINAL already demonstrates one card block
per durable run in `widgets/decks/final/`. Reusing/generalizing that machinery gives a
Tool Runs card stable run blocks, newest-block following, arrival dots, and `(`/`)`
older/newer stepping without inventing another navigation language.

### ToolRun attribution is useful but not equivalent to an Agent node

`src/sase/tool/executor_recording.py` records `agent`, `workspace`, `bead`,
`owner_kind`, `owner_id`, `parent_run_id`, and `project`. That is enough for a valuable
first integration, but it creates non-obvious matching rules:

- A single-turn Agent node can match an exact `agent` name.
- A session container must aggregate all concrete turn names, not prefix-match names.
- A monitor row should match `owner_kind=monitor` plus its monitor id, even when LLM
  Calls is unavailable on that row.
- A session container should also include the ToolRun owned by its monitor turn.
- A selected agent may have runs from the primary repo and linked repos. ToolRuns are
  deliberately recorded under the catalog-owning repo identity, so the contextual
  agent query must span projects and show a project chip rather than silently applying
  the current-project filter.
- Parent/child ToolRuns should render as a hierarchy using `parent_run_id`; flattening
  them makes a nested wrapper look like unrelated duplicate activity.
- The ledger is machine-local. Remote Fleet agent rows cannot truthfully show zero; the
  state is “not available from this machine” unless Fleet later transports a summary.
- A count is only a retained-history count. `summary_days`, `detail_days`, and
  `log_days` have different horizons, so the UI must say “retained runs” and clearly
  mark pruned stages or output.

These rules are a strong reason not to bolt a count onto `AgentState` during the normal
Agents load.

### The existing query API is not a good TUI read model

The Rust `ToolRunListRequestWire` supports only one exact tool, state, agent, and
project plus cursor/limit. `list_runs` selects IDs and then materializes complete
`ToolRunWire` values, including fingerprints and log metadata, one run at a time. It
does not return a per-run triage verdict or class counts. The schema also lacks an
`(agent, created_ts)` index and an `(owner_kind, owner_id, created_ts)` index.

Using this API directly from the Agents tab would lead to one or more of the following:

- N queries for the N concrete turns in a session;
- a ledger scan on every selection;
- loading large fingerprint JSON that a timeline row does not need;
- a second database open per run to obtain triage;
- SQLite reads or JSON processing on a latency-sensitive path;
- incorrect current-project scoping for linked-repo work.

The TUI performance memory explicitly requires cached instant paint, background
revalidation, selective patching, and no synchronous I/O in render or input handlers.
The proper fix is a core-owned read projection, not a Python-side SQLite reader.

### State and verdict must remain visibly separate

A failed ToolRun can have the triage verdict `no_new_failures`. SASE intentionally does
not turn that into a successful exit. The UI should render both, for example:

```text
✗ check   4m 12s   exit 1
  NO NEW FAILURES · 7 KNOWN · 1 FLAKY
```

It must not recolor the whole row green, call it “passed”, or hide its exit code.
Likewise, `stop requested` is not the same state as stopped, missing evidence is not
zero, and a lost wrapper is not a failed command.

### External UX patterns support layered disclosure

Two established interfaces reinforce this design:

- GitHub Actions starts with run history, drills into a run summary, then jobs/steps,
  and expands failed steps for diagnosis rather than putting full logs in the list.
  See [Using workflow run logs](https://docs.github.com/en/actions/how-tos/monitor-workflows/use-workflow-run-logs).
- VS Code separates contextual status decorations from a centralized Test Explorer and
  a detailed Test Results panel; it also lets users filter by status. See
  [Testing in VS Code](https://code.visualstudio.com/docs/debugtest/testing).

The useful transferable pattern is not their visual styling. It is the layered model:
small contextual signal → centralized inventory → selected-run evidence, with failures
receiving more visual priority than routine successes.

## Evaluation of the candidate integrations

| Candidate | Verdict | Reason |
| --- | --- | --- |
| Add **Tool Runs** as a second Tools-deck card | **Do** | Correct selected-agent scope; reuses card navigation; keeps provider calls distinct but adjacent. |
| Add a new **ToolRuns deck** | **Do not** | Splits one concept across two decks and lengthens an already four-deck cycle. |
| Replace **LLM Calls** with ToolRuns | **Do not** | Loses provider-level file/web/subagent activity and conflates observation with execution. |
| Merge both into one chronological timeline | **Not yet** | There is no durable correlation id; timestamp/argv matching would invent relationships and duplicate semantics. |
| Add hammer + total count to every Agent node | **Do not initially** | Clutter, ambiguous retention scope, remote unknowns, session aggregation cost, and low actionability. |
| Add an attention-only row marker later | **Potentially** | Useful if it means active/new/unknown rather than merely “some runs exist.” |
| Put all ToolRuns in Procs | **Do not** | Foreground runs may have no proc, and Proc lifecycle/output omits stages, fingerprints, triage, receipts, and nested ToolRuns. |
| Put ToolRuns in Artifacts | **Do not** | ToolRuns are not currently artifact-reference/document entities; the ledger is operational and machine-local. |
| Add a fourth top-level TUI tab | **Do not** | Too prominent for a supporting operational surface; expands the primary three-tab loop. |
| Add **Tools** to the Admin Center | **Do** | Natural home for machine-local inspection and control; consistent with Procs, Logs, Statistics, and Projects. |

## Proposed Agents-tab experience

### Deck and cards

Keep the deck named **TOOLS** and retain its `λ` glyph. Change its description from
“LLM tool-call timeline” to “Provider calls and durable tool runs.” Give it two cards:

1. **LLM Calls** — the existing provider-call timeline, behavior unchanged.
2. **Tool Runs** — durable runs attributable to the selected node.

Preserve LLM Calls as the first/default card for compatibility. If it is empty and
Tool Runs has content, select Tool Runs. Persist the user's preferred Tools card just
as the deck state already does for other decks.

The deck chrome should not reduce two unlike quantities to one number. The card tabs
should carry their own counts:

```text
λ TOOLS ┃ LLM Calls 18 · TOOL RUNS 3
```

The deck picker can say `2 cards`; the active card labels provide the meaningful call
and run counts. “3 runs” means three retained rows loaded for this node, and truncation
must be explicit (`50+ retained runs` or `50 shown`).

### Tool Runs card

Use one stable card block per run, ordered oldest → newest so the existing newest-block
landing and following behavior remain intuitive. Cap the contextual load (for example,
50 newest runs) and link to the global browser for the rest.

Compact block example:

```text
── 14:32  ✗ check  · 4m 12s · sase ─────────────────────
exit 1 · no new failures · 7 known · 1 flaky
stages 11/11 · input unchanged · monitor acme--mon
```

Expanded detail should add exact argv, run id, start/settle timestamps, stage timeline,
terminal cause, owner, parent run, dirty-count change, evidence completeness, and
diagnostics. Full detail adds triage items and bounded output tail. Full retained logs
remain on-demand in the global inspector/editor; they should not be read for normal
card paint.

Interaction should reuse deck conventions:

- `Ctrl+J` / `Ctrl+K`: LLM Calls ↔ Tool Runs card.
- `(` / `)`: older/newer ToolRun block; newest follows arrivals until the user steps
  backward.
- `h` / `l`, `H` / `L`: compact/expanded/full for the active Tools card, preserving
  existing LLM Calls behavior.
- `Enter` or a numbered hint on a run: open Admin Center → Tools → Runs focused on the
  exact id.
- `E`: export the currently rendered card text, as Tools already does; a separate
  “open retained output” command handles full logs.

### Empty and partial states

The empty state must explain the distinction:

- `No ToolRuns attributed to this node` when the local query is authoritative.
- `ToolRun history is local to <machine>; this is a remote agent` for Fleet rows.
- `No retained ToolRuns` when rows may have aged out.
- `Run detail was pruned; summary retained` and `Output log expired` in a block rather
  than silently omitting sections.
- `ToolRun ledger unavailable: <bounded diagnostic>` on store/core errors. The rest of
  the Agents tab remains usable.

### Do not heuristically merge LLM calls and ToolRuns

An LLM `bash` call containing `sase tool run check` and its durable ToolRun describe
the same causal episode at different layers, but there is currently no stable join key.
Keep them in separate cards. A future `origin_tool_call_id` or equivalent may enable a
“related provider call” link. Do not correlate by timestamps or command text.

## Agent-row signal

Do not ship a total-count hammer in the first version. Agent rows are already dense,
and the count would imply more certainty than the local retained ledger provides.

If usage testing shows that failures are missed unless the Tools deck is open, add one
highest-severity marker, not several counters:

| Marker | Meaning |
| --- | --- |
| `λ!N` red | N retained ToolRuns with `new_failures` |
| `λ?N` amber | N retained failed runs with unknown/unavailable triage |
| `λ▶N` cyan | N created/running runs, only when there is no higher-severity marker |
| no marker | Successes, known/flaky-only failures, no runs, remote-unavailable, or not yet loaded |

The marker reuses the Tools deck identity, avoids emoji-width problems, and encodes
meaning with punctuation as well as color. Its help text must call the number
“retained actionable runs.” Populate it with one batched background query for visible
exact agent names, carry it stale-while-revalidate, and patch only changed rows. Never
perform a ToolRun query per rendered node.

## Proposed Admin Center Tools pane

Add **Tools** as tab 8, after Updates, so `1`–`7` keep their current meanings. Open it
from the command palette (`Open tools panel`) and from exact ToolRun links in Agents or
Procs. Its header should state the machine because the ledger is local.

### Runs (default)

Use the same master/detail grammar as Procs:

- left: paginated retained runs, newest first;
- right: selected run summary and evidence;
- live selected run refreshes while `created`/`running`;
- filters for free text, project, agent, tool, state, verdict/class, owner, bead,
  duration, and time range;
- current project is the initial scope when one exists, with an explicit All Projects
  toggle;
- nested runs are indented beneath a loaded parent;
- detail sections are Summary, Stages, Triage, Changes/Evidence, and Output.

Failure state should determine the primary icon; triage is a secondary chip. Failed
stages should expand by default, following the useful GitHub Actions pattern. Output is
loaded only for the selected run and tail-followed only while visible.

### Catalog

Show project-owned named tools with description, exact argv, argument policy, LAST,
TYPICAL, stage mode, and receipt policy/coverage. A receipt should read as proof—such as
`receipt: pass · expires in 37m`—never as “up to date,” and it must never disable the
Run action because SASE receipts intentionally do not skip execution.

Launching from the TUI should initially support named tools only. Show a confirmation
containing project root, exact argv, appended arguments, and execution mode. Always use
the durable handoff path; never run a named tool synchronously on the Textual event
loop. Move focus to the created Run detail once the durable id exists. Ad-hoc launch
can remain a CLI/Command Line workflow until it has a reviewed argument-entry design.

### Failures

Render the existing signature groups with class, tool/stage, display, run count, agent
count, first/last timestamps, and possible owner. Selecting a group should show its
newest occurrences; Enter opens the exact latest run. Default ordering should remain
severity/recency oriented, with NEW and UNKNOWN visually ahead of KNOWN and FLAKY.

### Lifecycle actions

- **Follow** is implicit while the selected run is active; there is no TUI equivalent
  of blocking `wait`.
- **Stop** calls the same owner-aware control path as `sase tool stop`. Render “stop
  requested” immediately but do not claim stopped until settlement arrives.
- **Rerun** is not part of the first slice. When added, it creates a new standalone run
  and must not attribute it to whichever Agent row happened to lead the user there.
- Keep Procs as the process-owner surface. An owner chip jumps to Procs; the Procs row
  gains a ToolRun link/chip back to this inspector.

## Core read model and implementation boundary

Shared browse/filter/aggregation behavior belongs in `sase_core`, consistent with the
project's Rust backend boundary. The Python TUI should receive normalized wire records
and only render them.

### Add compact browse APIs

A useful design would expose two new bindings rather than stretch the execution wire:

1. `tool_run_browse(request) -> ToolRunBrowseResultWire`
   - compact row fields only;
   - multi-value `agents`, `projects`, `states`, and owner selectors;
   - time range, tool, bead, verdict/class, cursor, limit;
   - triage verdict and NEW/UNKNOWN/KNOWN/FLAKY counts joined in one query;
   - stage completed/total/failed counts;
   - total/truncated metadata;
   - no full fingerprints, samples, or log bytes.
2. `tool_run_detail(request) -> ToolRunDetailResultWire`
   - the existing show data plus attached timeline, triage, retention facts, and a
     normalized before/after change summary;
   - exact run-id lookup;
   - still no log contents unless explicitly requested through a bounded tail reader.

Add indexes for agent/time and owner/time access. Do not teach Textual to query the
SQLite schema directly, and do not issue one `tool_run_show` plus one triage query for
every visible row.

A separate batch glance call can be added only if the row marker is approved later. It
should return counts per exact agent name; the TUI can aggregate those exact identities
into current session containers using the same membership resolver that builds the
Agent tree.

### Refresh behavior

- Paint cached card/list data immediately, then load off-thread.
- Debounce selection-driven detail loads and re-check selected node/run after each
  await.
- Include the SQLite database and WAL in the change token; ToolRuns use SQLite WAL.
- Poll/revalidate active selected runs more often than settled history.
- Run liveness reconciliation on a bounded slow cadence or explicit refresh, not on
  every render/keypress.
- Patch deck availability/counts and Agent markers selectively; do not rebuild the
  Agent list when only ToolRun status changes.
- Keep first paint independent of ledger size and use cursor pagination in the global
  browser.

### Attribution improvements worth considering

The existing exact agent name is workable, but a future wire version should consider a
stable local agent-turn identity or artifacts-dir identity. That would eliminate name
reuse ambiguity and make session aggregation durable outside the currently loaded
Agent tree. This is not required to ship the first card and should not block it.

## Suggested delivery sequence

### Phase 1 — read model and contextual card

1. Add compact browse/detail wires, queries, indexes, PyO3 bindings, and Python facade
   in `sase-core`/sase; advance `sase-core-revision.txt` past the core commit.
2. Refactor Tools into a real two-card host while preserving every LLM Calls behavior,
   search corpus, editor export, detail level, and persisted preferred card.
3. Implement Tool Runs blocks for a single agent, session aggregate, and monitor owner.
4. Handle cross-project attribution, nested runs, remote unknowns, retention, and
   bounded failure states.
5. Ship without Agent-row badges and without launch/stop actions.

This is the smallest slice that tests whether the information is useful in the place
users first asked for it.

### Phase 2 — global inspector and cross-links

1. Add Admin Center Tools tab 8, default Runs master/detail, filters, paging, and live
   selected-run follow.
2. Link exact runs from the Agents card and owner Procs; link back to Agent when the
   local row can be resolved.
3. Add Catalog and Failures views using the same core projections.

### Phase 3 — control and proof

1. Add reviewed named-tool launch through durable handoff.
2. Add owner-aware stop with requested-versus-settled states.
3. Add receipt coverage to Catalog/run detail and repeat-opportunity analytics to
   Statistics if the data is useful there.
4. Measure discoverability. Only then decide whether an attention-only Agent marker is
   justified.

## Acceptance criteria

- LLM Calls and Tool Runs remain distinct, accurately labeled cards.
- Selecting a session shows all and only its concrete turns' retained ToolRuns,
  including its monitor-owned run, with no prefix-collision matches.
- Linked-repo runs appear in the contextual card with project identity.
- Remote nodes never render a misleading zero.
- Failure exit state and triage verdict are simultaneously visible.
- Nested runs render as parent/child, not duplicate siblings.
- Missing/pruned details and logs are explicit.
- A quiet TUI performs no ToolRun store reads on every idle tick; all SQLite/JSON work
  stays off the event loop and serial message pump.
- Moving rapidly between Agents never lets a stale ToolRun result paint the new
  selection.
- The card works without the Admin Center pane, and the pane works for unattributed
  human/ad-hoc runs without an Agent.
- Named-tool launch yields a durable run id before the UI treats the action as started.
- Receipt presentation never implies execution was or will be skipped.

## Recommended solution

Build a layered ToolRun experience. First add a compact batch ToolRun read model in
`sase_core`; then add **Tool Runs** as the second card of the Agents tab's existing
**Tools** deck, modeled as one stable block per retained run and kept separate from
**LLM Calls**. Do **not** add a raw hammer/count badge to Agent nodes. Add a later
attention-only `λ` marker only if measured usage shows that new, unknown, or active runs
need a glance signal. Complete the experience with an eighth **Tools** Admin Center pane
for global Runs/Catalog/Failures browsing, exact run detail, durable named-tool launch,
and owner-aware stop, with links to Agents and Procs. This gives the selected-agent
workflow a lightweight contextual view while preserving a truthful, scalable home for
the full `sase tool` control plane.
