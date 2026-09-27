# ToolRun UX in sase's TUI

**Researcher:** cdx  
**Date:** 2026-09-27  
**SASE revision inspected:** `59f5eff1660acfb36c8eaa040c7e6a4fcd71ee59`  
**Scope:** the `sase tool` catalog, ToolRun ledger, Agents-tab decks and nodes,
Command Line, notifications, Projects, Procs, and Statistics surfaces

## Executive conclusion

Add a **Tool Runs** card to the existing **Tools** deck. Keep **LLM Calls** and
**Tool Runs** as explicitly separate cards: the former answers “what provider tool
calls did the model make?” and the latter answers “what durable project command did
SASE execute, with what outcome and evidence?” This is the best first integration
because ToolRuns already carry agent attribution and users investigate them in the
context of an agent.

Do **not** add a historical hammer-count badge to every agent node. It would be nearly
ubiquitous, would confuse activity with health, would double-count nested and
monitor-owned work, and the `⚒` glyph already denotes scheduler jobs in the TUI. The
Tools deck subtitle and card tab should disclose run counts. If later observation shows
that the tree needs a signal, add only an attention indicator for an active run or a
failure needing review—not a lifetime count.

Do not build a second command executor inside the card. `:` already provides a
project-aware, completion-rich command surface whose commands run as durable procs.
Use that pipeline for “run tool”, “follow”, and advanced CLI operations. Add a global
browser later as **Admin Center → Projects → Tools**, where the project-owned catalog
and machine-local run history naturally meet. Keep aggregate adoption, duration,
failure, and receipt metrics in Statistics as a later read-only view.

## What the product actually models

The most important design constraint is that “tool” currently names two different
things:

1. **LLM Calls** are provider events inside an agent run: reads, shell calls, edits,
   and other normalized model/tool interactions.
2. A **ToolRun** is a durable control-plane execution record created by `sase tool
   run`: catalog identity or ad-hoc argv, lifecycle, agent attribution, project,
   workspace, bead, execution owner, stages, output locators, fingerprints, samples,
   failure items, and a triage verdict.

The repository states this boundary directly in `docs/tool.md:3-9`. It is not a reason
to keep ToolRuns out of the Tools deck; it is a reason to preserve the two concepts as
separately named cards rather than merging their rows into one timeline.

ToolRuns have several independent relationship axes:

- `agent` is recorded from `SASE_AGENT_NAME` or the reserved monitor starter
  attribution (`src/sase/tool/executor_recording.py:38-61`).
- `owner_kind` / `owner_id` identifies a monitor or proc that owns execution and
  output; an inline run has no such owner.
- `parent_run_id` makes nested ToolRuns a hierarchy rather than independent flat
  activity.
- `project` is the catalog-owning repository identity, which can differ from the
  agent's host project for linked-repository commands (`docs/tool.md:37-56`).
- history is machine-local, and summary, detail, and logs have different retention
  horizons (`docs/tool.md:112-126`).

Consequently, a ToolRun is not simply another provider tool-call row, a Proc row, a
monitor row, or a file artifact. It may link to all of those without being any of them.

## Evidence from the present implementation

### The Agents detail architecture is the right contextual home

At the inspected revision, the deck registry already contains four decks—Main, Files,
Tools, and FINAL—in `src/sase/ace/tui/widgets/decks/model.py` and
`src/sase/ace/tui/widgets/decks/spec.py`. The Tools deck is still a special case that
hard-codes one `LLM Calls` card in
`src/sase/ace/tui/widgets/decks/panel_chrome.py:370-387`. Main and FINAL already prove
the general document/card/block model, sticky preferred cards, split panels, and
background loading.

This makes “another card in Tools” a good information architecture decision, although
it is not merely a one-widget patch: Tools needs to become a real multi-card deck.
Adding a fifth deck would enlarge an already four-item cycle and make users decide
between two adjacent concepts whose shared question is “what tools did this node use?”

### The TUI already has an execution surface

The Command Line (`:`) runs implicit-`sase` commands, is selection- and project-aware,
has ToolRun-ID completion, follows output, and runs ordinary commands as durable procs
(`docs/ace.md:3611-3658`). ToolRun candidates are already loaded through the Rust-backed
ledger and cache-invalidated from the ToolRun store
(`src/sase/completion/candidates/catalog_entities.py:48-88`).

This existing path matters. If a native Tools card launches `sase tool run check`, it
should submit it through the same durable proc machinery. It should **not** add `-H`:
the command-line proc is already the execution owner, and `-H` inside a live owner is
intentionally refused. Native shortcuts should be convenience affordances over this
path, not a second implementation of command execution.

### Raw badges would be high-volume and low-information

I sampled the newest 1,000 rows from the local machine ledger with
`sase tool runs -a -n 1000 -j` on 2026-09-27. This is a bounded, machine-specific
snapshot, not a population estimate, but it is enough to test the proposed badge's
signal quality:

| Measure | Observed |
| --- | ---: |
| Agent-attributed rows | 995 / 1,000 |
| Distinct attributed agent names | 575 |
| Agents with exactly one retained row | 368 |
| Agents with more than one retained row | 207 |
| Maximum retained rows for one name | 30 |
| Monitor-owned rows | 209 |
| Inline/unowned rows | 791 |
| Failed / signaled / lost rows | 721 / 111 / 10 |
| Succeeded / running rows | 155 / 3 |

Nearly every sampled ToolRun was agent-attributed. A badge meaning “this agent made a
ToolRun” would therefore decorate most relevant coding agents and cease to discriminate.
A number would not say whether the runs were nested, repeated attempts, monitor-owned,
successful, known-red verification, or new failures. The state mix also shows why a
red-on-any-nonzero-failure badge would overwhelm the node tree. Tool failure triage
exists specifically to distinguish NEW, KNOWN, FLAKY, and UNKNOWN items without
changing the command's exit code (`docs/tool.md:231-258`).

There is also a visual-language collision: `⚒` is already the scheduler job/Chop icon
(`src/sase/ace/tui/relations/link_subject.py:26-30`). Reusing it for ToolRuns would
make the same glyph mean two control planes.

### Existing external patterns favor contextual status plus dedicated detail

Two mature developer-tool patterns support the layered design:

- VS Code shows test status in context, provides a centralized explorer, and keeps
  detailed output in a separate Test Results panel rather than putting every execution
  detail into a badge. Its tree indicators communicate result state; count badges are
  configurable rather than the primary semantic. See the official
  [VS Code Testing documentation](https://code.visualstudio.com/docs/debugtest/testing).
- GitHub Actions presents a run summary, then jobs and steps, and automatically expands
  failed steps for diagnosis. This maps well to a ToolRun block whose compact header is
  state/tool/duration and whose expanded body emphasizes failed stages and triage. See
  the official
  [GitHub workflow-run log documentation](https://docs.github.com/en/actions/how-tos/monitor-workflows/use-workflow-run-logs).

The lesson is not to copy either interface literally. It is to preserve a progressive
disclosure ladder: glanceable state, bounded history, one selected execution's detail,
then full output/actions.

## Options considered

| Option | Strength | Main problem | Verdict |
| --- | --- | --- | --- |
| Tool Runs card in Tools deck | Correct node context; reuses cards, splits, sticky selection | Requires refactoring the currently single-card Tools deck | **Recommended first** |
| Separate ToolRuns deck | Clean implementation boundary and abundant space | Fifth deck; separates two answers to the same user question; extra cycling/picker load | Do not start here |
| `⚒N` on every agent node | Immediate discoverability | Ubiquitous, ambiguous, visually crowded, glyph collision | Reject |
| Conditional attention chip | Can reveal active or actionable failures | Needs a cheap, correct aggregate and careful semantics | Reconsider after the card ships |
| New top-level TUI tab | Full global console | ToolRuns do not justify a fourth everyday tab; weak node context | Reject |
| Artifacts pane | Durable-looking browse surface | Machine-local retention and no ToolRun ref/navigation contract today | Reject for now |
| Procs integration only | Good for proc-owned runs and lifecycle actions | Most sampled runs were inline; ToolRun and Proc are different identities | Link owners; do not merge |
| Projects → Tools sub-tab | Natural catalog provenance and project scope; global history | Larger second phase | **Recommended global surface** |
| Statistics → Tools view | Good for trends, failures, receipts, adoption | Poor run inspection/control surface | Later analytics only |

## Recommended interaction design

### 1. Make Tools a two-card deck

The Tools deck should contain, in this order:

1. **LLM Calls** — preserve the current default and behavior.
2. **Tool Runs** — a durable execution timeline for the selected node.

Preserving LLM Calls as the initial card avoids changing muscle memory. The panel's
existing preferred-card behavior means a user who selects Tool Runs keeps it while
moving through nodes. If a node has ToolRuns but no LLM Calls—such as an applicable
monitor or named proc—the deck can land on Tool Runs automatically.

The wide deck subtitle/picker should report both quantities, for example
`tools · 18 calls · 2 runs`; compact tiers can use unambiguous abbreviations such as
`18 calls · 2 runs`, not one combined number. This requires replacing the Tools deck's
single `count_noun=(call,calls)` assumption with structured per-card availability.

### 2. Model each ToolRun as a card block

Use one **Tool Runs** card with one block per run. This fits the existing
deck → card → block vocabulary and gives users the same `(` / `)` older/newer motion
used for session turns.

A collapsed block header should answer only:

```text
<state>  check  4m33s  · exit 1 · UNKNOWN 1 · monitor
```

The full block should show, in descending importance:

1. **Outcome:** lifecycle state, terminal cause, exit/signal, duration, started/settled
   time, and whether the command actually started.
2. **Stages:** compact timeline with failed/running stages expanded first; passed stages
   remain one-line.
3. **Triage:** verdict plus NEW/KNOWN/FLAKY/UNKNOWN item counts; selecting a failure
   reveals its bounded display, stage, paths, evidence, and possible owners.
4. **Context:** safe display argv, project, concrete agent turn, workspace, bead,
   launch mode, owner, and parent run.
5. **Evidence:** fingerprint completeness, mutation result, dirty-count transition,
   receipt coverage when applicable, and output-retention/truncation state.
6. **Actions:** open/follow output, copy run ID/command, open owner, stop when running,
   and rerun as a new execution.

Never display `private_argv`; use the recorded safe display argv. Never render pruned
detail or missing owner logs as empty success. Use explicit “summary retained; detail
pruned” / “owner log unavailable” states, matching the CLI's retention semantics.

Newest-first is appropriate, but selection must be stable: if the user is on the newest
block, follow new progress; if they moved to an older block, hold position and mark the
new arrival. This is the same follow-versus-reading behavior the current card-block UI
uses for session turns.

### 3. Resolve node scope explicitly

The card's query must be defined by node kind, not by string prefix guessing:

| Selected node | ToolRuns shown |
| --- | --- |
| Concrete agent turn | Exact `agent` attribution |
| Standalone agent node | Its exact concrete agent name |
| Sequential session | Union of its concrete agent-turn names, deduped by run ID |
| Monitor turn | Exact `owner_kind=monitor` + owner ID; annotate starter attribution |
| Named proc | Exact `owner_kind=proc` + owner ID |
| Workflow agent step | Its concrete agent attribution |
| Clan/whole tribe | No full history in v1; show an explanatory empty state or bounded summary only |
| Remote row | “ToolRun history is not included in this machine feed”, never zero |

For session aggregation, preserve the originating turn label on every block. A
monitor-owned run may be visible from both its attributed agent/session and its monitor
owner; this is intentional navigation through two relationships, but aggregate counts
must dedupe by run ID. Nested ToolRuns should be indented under their parent and should
not inflate a top-level “executions” count without disclosure.

### 4. Keep the agent-node tree quiet

Ship the card without a new agent-row badge. Discoverability comes from:

- the Tools deck's `runs` count;
- the Tool Runs card tab and empty state;
- a command-palette action, **Show Tool Runs**;
- settlement notifications deep-linking to the relevant card or global browser.

After usage data exists, consider one conditional attention chip only if it answers an
actionable question:

- active ToolRun owned/attributed here; or
- latest settled run has NEW or unreviewed UNKNOWN failures.

Do not show successful history, raw run totals, or every failed exit in the node row.
Do not use `⚒`. Any future glyph must be checked at narrow widths, with color removed,
and against existing status, provider, bead, monitor, gate, queue, owner, machine, and
runtime chrome.

### 5. Reuse Command Line and durable proc actions

Add **Run project tool…** to the command palette. It should show the current project's
catalog with description, LAST, and TYPICAL, then submit `tool run <name>` through the
existing Command Line/durable-proc execution path at the catalog project root. The
same picker can be opened from Projects → Tools later.

Within a ToolRun block:

- **Follow output** can initially open `tool show <id> -F` as a Command Line block; the
  viewer proc can be stopped without stopping the ToolRun.
- **Open retained output** can use the same owner-aware log resolution as `tool show
  <id> -l`.
- **Stop** must be cancel-first and submit the existing stop path off the event loop.
  If the owner is a monitor, the confirmation must say that stopping suppresses its
  recorded follow-up.
- **Rerun** must say it creates a new ToolRun and may repeat external side effects.

These operations should appear in the context-aware command palette before allocating
new single-key bindings. The Agents tab already has dense key semantics, and the
Command Line already offers expand, pager, kill, rerun, copy, and open-in-Procs actions.

### 6. Add a global surface under Projects, not a new top-level tab

The long-term global browser should be **Admin Center → Projects → Tools**, alongside
Projects, Repos, and Workspaces. Its project picker and current-project seed fit the
catalog's repository ownership better than Procs or Artifacts.

The sub-tab should have two linked regions:

- **Catalog:** named tool, description, LAST state/age, TYPICAL duration/sample count,
  and current receipt status. Enter runs the tool through a durable proc.
- **Recent runs:** bounded newest-first history with state/tool/agent/owner/duration;
  filters for project, tool, state, agent, and “needs review”; the detail pane reuses
  the ToolRun block renderer.

`Open owner` should navigate to the monitor Agent node or Admin Center Procs row. It
should not create a duplicate pseudo-proc. A run with no retained agent should still be
fully inspectable here.

The existing proc-owned handoff notification already records a run ID and `sase tool
show` command (`src/sase/tool/notify.py:46-105`). Change its action to deep-link to the
ToolRun detail. When agent attribution still resolves, prefer the Agents card; otherwise
open Projects → Tools.

### 7. Keep analytics separate

Later, Statistics can add a **Tools** view or Tooling section containing:

- executions, success, and triage-verdict rates by project/tool;
- duration and stage hot spots;
- failure-signature groups and NEW/UNKNOWN backlog;
- agent adoption of named versus raw heavy commands;
- receipt coverage and content-equivalent repeat opportunity.

These are time-range aggregates, not substitutes for recent-run inspection. They
should not block the contextual card.

## Backend and performance contract

The first implementation should start with the read model, not the widget.

1. Extend the Rust ToolRun query API with a bounded presentation summary that accepts
   a set of exact agent names and/or owner identities, returns runs deduped by ID, and
   includes lightweight stage progress plus triage-verdict/item counts. The current CLI
   list accepts only one exact agent filter (`src/sase/main/parser_tool.py:322-391`),
   while full triage is attached by per-run show; a TUI must not issue one show query
   per visible run.
2. Add a ledger generation/change token suitable for cache invalidation. Reuse the
   existing direct Rust binding; never shell out to `sase tool runs` and never query the
   SQLite schema directly from the TUI.
3. Define a pure `ToolRunTarget` projection for node → exact agent/owner/project sets.
   Keep this mapping unit-testable outside Textual.
4. Load off-thread, keyed by target + attempt + project + ledger token. Paint cached
   content immediately and coalesce refreshes. Only poll rapidly while a visible block
   is unsettled; otherwise use the normal auto-refresh token path.
5. Revalidate selection and focused deck after every await. Do not remount the agent
   tree when ToolRun data changes. A future attention chip should patch only affected
   rows after the lightweight aggregate is cached.
6. Treat remote ToolRun availability as three-state (`yes`, `no`, `unknown/unavailable`)
   until the fleet feed carries a compatible summary contract.

This respects the project's Rust-core boundary: selection-independent ToolRun query,
aggregation, dedupe, triage summary, and lifecycle semantics are shared backend
behavior; Textual owns only node targeting, layout, rendering, and interaction glue.

## Suggested delivery sequence

### Slice 1 — read-only contextual card

- Add the Rust scoped-summary query and thin Python adapter.
- Refactor Tools into a two-card deck with structured per-card availability.
- Add the Tool Runs card/block renderer for concrete agents, sessions, monitors, and
  named procs.
- Add explicit remote/pruned/unavailable states.
- Add **Show Tool Runs** to the command palette.
- Do not add row badges or lifecycle mutations.

This slice proves the information architecture with low behavioral risk.

### Slice 2 — actions and deep links

- Add **Run project tool…** using the durable proc/Command Line submission path.
- Add follow/log/copy/open-owner/stop/rerun actions to ToolRun context.
- Deep-link settlement notifications into ToolRun detail.
- Preserve owner-specific warnings and rerun side-effect disclosure.

### Slice 3 — project-wide browser

- Add Projects → Tools with Catalog and Recent Runs regions.
- Reuse the detail renderer and project picker.
- Add bounded filters and needs-review scope.

### Slice 4 — measured glance and analytics

- Measure card use, width pressure, query latency, and how often actionable ToolRuns
  exist off-screen.
- Add a conditional node attention chip only if the evidence supports it.
- Add Statistics aggregates for adoption, triage, duration, and receipts.

## Acceptance tests that matter

- A direct agent run appears under its exact turn and enclosing session once.
- A monitor-owned run appears from both the monitor and attributed session without
  double-counting session totals.
- Nested runs retain parent/child structure.
- Running → settled updates do not move an older selected block.
- NEW, KNOWN, FLAKY, UNKNOWN, unavailable triage, successful runs, signals, lost runs,
  pre-start stop, owner loss, pruned detail, missing logs, and truncated output each
  render distinctly.
- Safe display argv is used; private argv never reaches the UI/export.
- Remote absence is not displayed as zero.
- Stop confirmation accurately describes monitor follow-up suppression.
- A rerun creates a new ID and never implies replay/exactly-once semantics.
- Duplicate split panels share cached reads.
- Quiet auto-refresh opens no ToolRun files and does no SQLite work when the ledger
  token is unchanged; j/k paint latency remains within the existing p95 target.
- Visual snapshots cover narrow, normal, wide, split, zoomed, empty, running, failed,
  pruned, and remote states, with color-independent labels.

## Recommended solution

Implement a read-only **Tool Runs** card as the second card in the Agents tab's
existing **Tools** deck, backed by a new bounded Rust read model that scopes exact agent
turns and execution owners, dedupes nested/session relationships, and returns triage
summaries without N+1 reads. Keep LLM Calls as the default card, use ToolRun blocks for
newest-first outcome/stage/triage/evidence detail, and expose counts in the deck chrome
rather than on every agent row. Reuse `:` and its durable-proc machinery for running,
following, stopping, and rerunning tools; then add **Projects → Tools** as the global
catalog/history console and Statistics only for aggregate trends. Do not add `⚒N` node
badges; if later measurements justify a tree signal, make it conditional on active or
review-worthy ToolRuns and choose a glyph that does not collide with scheduler jobs.
