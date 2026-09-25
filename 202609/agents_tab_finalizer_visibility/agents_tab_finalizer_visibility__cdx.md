# Finalizer observability in the Agents tab

**Researcher:** `research.a.cdx`  
**Date:** 2026-09-25  
**Scope:** Product and implementation research for making SASE finalizers visible,
understandable, and diagnosable from the Agents tab.

## Executive finding

Finalizers should become a first-class **Finalizers deck** in the Agents tab, not a
fold inside Main, a kind of tool call, or a new tree node. The deck should have an
Overview card followed by one stable card per selected finalizer instance. When the
upcoming card-block abstraction is available, a finalizer-instance card should use one
block per concrete execution scope (normally one agent shell; several blocks when a
session aggregates several shells). Attempts belong inside that block as a compact
timeline and must not become another nesting level.

That hierarchy matches the three identities a user needs to reason about:

```text
selected agent/session
  └── stable finalizer instance (card)
        └── concrete execution in one shell/run (card block)
              └── attempts, output, evidence, and diagnostics (card content/modal)
```

The UI also needs a small row-level signal because a hidden deck cannot explain why an
otherwise-finished agent is still running. Render `FINALIZING` as a display phase while
retaining the agent's underlying Running lifecycle bucket, and show a sparse finalizer
chip only while finalization is active or ended non-successfully. Successful finalizers
should not permanently clutter the list.

The durable data needed for this cannot be reconstructed reliably from today's files.
Add a small semantic progress journal and bounded live-attempt log, then reconcile the
plan, context, progress, result, output files, and runner liveness in `sase_core` into a
single read model. This should be a new artifact-projection API, not a change to the
strict finalizer execution protocol. The Python TUI should only load capped bytes off
the event loop and render the Rust projection.

## Inputs and method

I reviewed the requested prior research:

- `202609/agents_tab_finalizer_panel/agents_tab_finalizer_panel.md`
- `202609/agent_data_card_blocks/agent_data_card_blocks.md`

I then independently inspected the current Python controller, finalizer artifact
writers, agent scanner, deck system, detail-refresh path, prepared-monitor completion,
and the linked Rust core wire/scanner definitions. I also compared the interaction to
workflow/run-log products whose users face a similar summary-to-failure-to-log
progression. No report produced by another researcher in this swarm was consulted.

The most useful external precedents were GitHub Actions' run → job → step drill-down,
including automatic expansion of failed steps and searchable/downloadable logs
([workflow run logs](https://docs.github.com/en/actions/how-tos/monitor-workflows/use-workflow-run-logs)),
and Grafana's live-tail behavior, where scrolling pauses following so new output does
not steal the reader's position
([logs integration](https://grafana.com/docs/grafana/latest/visualizations/explore/logs-integration/)).
These are interaction precedents, not data-model templates.

## What exists today

Finalization is already a rich host lifecycle, but its durable records and its Agents
presentation are disconnected.

### Lifecycle and artifacts

Before invoking a provider, `src/sase/llm_provider/_invoke.py` resolves and persists the
finalizer plan and writes a compact selection into `agent_meta.json`. After the provider
turn returns, the same invocation runs finalizers inline before ordinary response
post-processing. Consequently, an agent can look merely `RUNNING` for minutes after its
model turn has effectively ended.

The current durable records are:

- `finalizer_plan.json`: an envelope with raw operations, the resolved plan, and
  diagnostics. An authority copy additionally contains the sealed configuration
  snapshot.
- `final_context.json`: the issued declaration/context, selected instances, trigger and
  policy facts, submission requirement, and manifest template.
- `finalizers/<instance>/...`: immutable output, input, and diagnostic files emitted by
  commit, command, and plugin providers.
- `finalizer_result.json`: a schema-v1 run-artifact envelope containing aggregate
  status, controller cycles, instance results, and diagnostics.
- `agent_meta.json["finalizers_drift"]`: a best-effort drift diagnostic written at the
  end of controller execution.

There is no durable active-instance state, attempt-start record, progress journal, or
general live finalizer log. For command providers, `.stdout`, `.stderr`, and
`.diagnostics.json` appear only after the subprocess exits. Plugin execution similarly
persists protocol output at operation boundaries, and its raw stdout is not necessarily
a human-readable log. During a long attempt, the TUI therefore has no principled way to
say which instance is running, how long it has run, or whether another attempt has
started.

The controller may execute as many as eight fixed-point cycles. Commit may reactivate
when new work appears; non-commit instances execute once. Dependencies, trigger
eligibility, declaration recovery, retries, refusal policy, deferral, and verification
all make the lifecycle more expressive than a single `commit` spinner.

### A protocol boundary that matters

The persisted `finalizer_result.json` is not the Rust/Python strict
`FinalizerAggregateResultWire` serialized directly. It is a schema-v1 artifact wrapper
that includes controller-cycle information around embedded instance results. The
execution protocol is separately versioned at v2 and intentionally rejects unknown
fields.

That distinction argues against adding UI-only fields such as `running`, display
labels, or live-log locations to the execution wire. The UI needs a separate
artifact-to-view projection which can understand legacy run artifacts as well as new
progress records. Execution inputs and outputs should remain strict and provider-facing.

### Current Agents architecture

The shipped deck system currently has Main, Files, and Tools:

- Main answers “what did this agent receive and reply?”
- Files answers “what changed?”
- Tools answers “what model tool calls occurred?”

Deck selection, card selection, two-panel spread, sticky preferred cards, picker
metadata, search, editor/export behavior, and persisted layout already form a coherent
navigation system. Decks are therefore the natural extension point. Adding a deck is
not zero-cost—the enum/cycle, title metadata, picker, panel composition, persistence,
search/editor/export, tests, and snapshots all contain three-deck assumptions—but it is
less conceptual complexity than inventing a parallel finalizer navigator.

The prepared-monitor path already exposes a coarse host completion state. It records
`finalizing`, scans that summary into the agent model, and presents “Host final:
Finalizing” in Main. It still lacks per-instance detail. Ordinary and prepared-monitor
completion eventually call the same finalizer controller, so separate UI models would
be needless divergence.

## The questions a useful UI must answer

A finalizer surface is valuable only if it lets a user move quickly from overview to
cause. In priority order, it should answer:

1. **Is this agent done, or is host-owned completion still working?**
2. **Which finalizers were selected, and why were others absent or not triggered?**
3. **Which instance is active, what is it doing, and how long has it been there?**
4. **What depends on what, and which upstream outcome blocked later work?**
5. **Was the outcome success, skip, refusal, deferral, failure, interruption, or simply
   never reached?**
6. **Across retries and controller cycles, what changed?**
7. **What diagnostic, evidence, or bounded output explains the outcome?**
8. **For a multi-shell session, which concrete run produced the outcome?**
9. **Can the user inspect the underlying artifact without the UI loading an unbounded
   file or executing untrusted presentation code?**

These questions are generic across future finalizers. A commit-centric design centered
on SHA, branch, and push state could answer today's common case while becoming the wrong
abstraction as soon as validation, publication, notification, indexing, deployment, or
policy finalizers are added.

## Placement alternatives

| Placement | Strength | Fundamental problem | Verdict |
|---|---|---|---|
| Main card/fold | Immediately visible and cheap for a tiny summary | Pollutes conversational context; scales poorly with instances, retries, logs, and session history | Keep only a one-line host-completion summary when useful |
| Tools deck | Already handles chronological operations | Finalizers are host-owned completion, not model tool calls; conflation damages audit semantics | Reject |
| Agent tree child/shell | Gives each item a row | A finalizer is not an agent session and has no independent prompt/reply lifecycle | Reject |
| Modal only | Good for dense logs | Undiscoverable and provides no at-a-glance lifecycle | Use only as drill-down |
| New top-level tab | Plenty of room | Separates evidence from the selected agent and duplicates filtering/navigation | Reject |
| **Finalizers deck** | Matches existing detail grammar, card navigation, spread, search, and sticky selection | Requires completing the deck plumbing and a new data source | **Choose** |

The older research reasonably proposed a foldable section in Main because it analyzed
the pre-deck detail layout. With decks now shipped, preserving that placement would
underuse the current information architecture. Main should summarize finalization, not
become the full finalizer workbench.

## Recommended information architecture

### Agent-list signal

The list is for triage, not forensic detail. Add two independent concepts:

- **Lifecycle bucket:** the existing canonical state used for actions, filters,
  capacity, and ordering. While finalizers run, this remains Running.
- **Display phase:** a narrow projection which can render `FINALIZING` for the row and
  status line without inventing a new terminal lifecycle state.

Beside the phase, show a compact chip only when attention is warranted:

```text
● research.a.cdx     FINALIZING       ⛭ check 1/2
✗ publish.a.cdx      FAILED           ⛭ publish ✗
✓ analysis.a.cdx     DONE
```

Success is deliberately silent in the row after completion. The Finalizers deck remains
available for audit, but persistent green chips across every completed agent would hide
the exceptional states. For a session row, aggregate with severity first and include a
count, such as `⛭ 1 failed / 5 runs`.

### Finalizers deck

Add `DeckId.FINALIZERS` and expose it wherever decks are exposed: cycle, picker,
single/two-panel layouts, persisted preferences, search, copy/export, and editor-open.
The count noun should be **instances**, not cards or operations. The deck is available
when the selected concrete agent has a plan/result, or when a selected session contains
at least one concrete shell with finalizer data.

The first card is always Overview. Remaining cards use stable identity
`instance:<instance_id>` and follow resolved plan/dependency order. Stable identities
let sticky card preference do something useful: a user investigating `publish` can move
between agents and land on `publish` whenever it exists.

#### Overview card

Overview is the fast answer to “what is happening?” It should contain:

- aggregate phase and elapsed duration;
- selected, complete, active, and attention-needed counts;
- the sealed plan digest in shortened form, with an invalid/drift warning if needed;
- declaration/submission state;
- a dependency-aware instance list with status, attempt, duration, and blocker;
- controller cycle only when greater than one or otherwise diagnostically relevant;
- a concise diagnostic summary, deduplicated by code/message/scope.

Example:

```text
 FINALIZING · 3 selected · cycle 1 · 00:42
 declaration accepted · plan 84a91c2d

 ✓ commit       success       1 attempt       00:02
 ● check        running       attempt 1/2     00:40   after commit
 ◌ publish      blocked                         —      after check

 Diagnostics
 ! check output has been quiet for 30 seconds
```

For a true DAG, render an indented ordered list with explicit `after …` labels rather
than an attractive but misleading linear pipeline. Wide layouts may add connectors;
narrow layouts must remain truthful without them.

#### Finalizer-instance cards

Each selected instance receives a generic card. Its fixed summary fields are:

- instance id and provider reference;
- current/terminal status and elapsed/total duration;
- trigger, dependency, submission, retry, and refusal policy;
- controller cycle and attempt summary;
- diagnostics, refusal/deferral reason, and typed evidence;
- bounded current or last output;
- paths/actions for underlying artifacts.

The card title should lead with instance id; the provider ref is secondary. Provider
specifics belong in typed evidence rows, not bespoke hard-coded panels. Commit may show
repository/SHA evidence because its result supplies those facts; a future deployment
finalizer may show environment/URL evidence through the same mechanism. If richer
provider presentation becomes necessary, extend the protocol with small sanitized
display hints interpreted by core code—do not allow plugins to inject Rich markup or
Python render callbacks.

Attempts are a compact timeline inside the card/block:

```text
 Attempts
  1  failed     exit 1       00:08   command-exit-nonzero
  2  running                 00:34   output updated 2s ago
```

The initial viewport should expand the active attempt or first failing/refused/deferred
item automatically, like mature workflow-log UIs. Successful historical attempts stay
collapsed. `Enter` opens a full-screen read-only modal focused on the selected attempt,
with Output, Diagnostics, Evidence, and Inputs views as available. The modal supports
find, copy, editor-open, and explicit tail-follow; it does not add retry/cancel buttons
in the first version.

### The precise role of card blocks

Card blocks are useful here, but only at one semantic boundary:

> **Card = stable finalizer instance. Block = execution of that instance in one
> concrete agent shell/run. Attempts remain rows inside the block.**

This is preferable to the tempting “one block per attempt” model for four reasons:

1. A block is the lowest navigable composition layer and cannot nest. Making attempts
   blocks leaves nowhere principled for multi-shell/session history.
2. Most instances have zero or one attempt; permanent block chrome would add noise for
   the common case.
3. Retries are evidence about one execution, while a different concrete shell has a
   genuinely different plan, context, artifact root, and liveness boundary.
4. Stable instance cards preserve cross-agent sticky selection; card-per-shell or
   card-per-attempt would make identity volatile.

For a concrete agent shell, each instance card has one block and therefore shows no
block rail. For a session container, collect executions with the same instance id into
chronological blocks keyed by concrete agent identity plus run/plan identity. Land on
the newest block and reuse the generic card-block rail and older/newer navigation. Show
the shell label, start time, plan digest, and outcome in the block header. A prepared
monitor finalization is simply another execution scope with a `monitor` provenance
label, not a different species of UI.

If an instance was not selected in a shell, do not fabricate an empty instance block.
The session Overview can still say that a shell had no matching instance. This keeps
instance cards meaningful while preserving the ability to troubleshoot selection.

The first implementation should not wait for generic card blocks. Render the selected
concrete run as ordinary card content and, for session rows, a simple run selector or
stacked run sections. Once card blocks ship, wrap those already-defined run view models
as blocks without changing the finalizer projection.

## State model and truth precedence

The presentation vocabulary should distinguish configuration, eligibility, activity,
and outcome. “Enabled” is too ambiguous. A practical normalized set is:

- `selected`: present in the sealed plan, execution not yet eligible;
- `not_triggered`: selected but its trigger condition did not occur;
- `waiting_for_declaration`: submission/declaration recovery is active;
- `ready`: dependencies and trigger are satisfied;
- `running`: an operation/attempt is active;
- `retrying`: an earlier attempt failed and another is scheduled/running;
- `success`;
- `skipped`;
- `refused`;
- `deferred`;
- `failed`;
- `blocked`: not run because a dependency or policy stopped the path;
- `not_run`: selected but controller termination prevented execution;
- `interrupted`: durable progress began, the runner is dead, and no terminal result
  closes it;
- `unavailable`: artifacts are invalid, mismatched, too large, or unreadable.

These are **read-model states**, not all new provider protocol outcomes. In particular,
`running`, `retrying`, `blocked`, `interrupted`, and `unavailable` are inferred from
artifacts and liveness.

Reconciliation should use explicit precedence:

1. Validate plan identity/digest and scope. A mismatch becomes `unavailable`, never a
   best-effort success.
2. A matching terminal `finalizer_result.json` is authoritative for outcomes.
3. Before terminal result, matching semantic progress plus live runner identity is
   authoritative for active phase/instance/attempt.
4. `final_context.json` supplies trigger, declaration, and submission facts.
5. Output-file existence supplies content availability only; it never proves success.
6. `agent_meta.json` supplies a cheap list-row hint, not detail truth.
7. Begun but unclosed progress with a dead/mismatched runner becomes `interrupted`.
8. Planned instances never reached after another terminal failure become `blocked` or
   `not_run`, not success and not an infinite spinner.

This precedence also makes legacy behavior honest. A historical run with plan and
result can be reconstructed completely enough for audit. A historical plan with no
result and no progress should say `not_run`/`unavailable`, not guess what happened.

## Minimal new observability contract

### 1. Semantic progress journal

Write `finalizers/progress.jsonl` using one versioned record per semantic transition,
not per output chunk. Useful events are:

- `phase_started` / `phase_finished`;
- `declaration_recovery_started` / `declaration_recovery_finished`;
- `instance_ready` / `instance_started` / `instance_finished`;
- `attempt_started` / `attempt_finished`;
- optional provider-operation boundaries such as `validate_started` and
  `verify_finished` when they explain a long plugin finalizer.

Each record should include schema version, monotonically increasing sequence, UTC wall
time, elapsed monotonic duration where meaningful, run identity, plan digest, cycle,
instance id, provider ref, operation, attempt, status, and diagnostic code. Write start
events before work and finish events after durable attempt artifacts are closed.

The event count is structurally small because controller cycles and provider attempts
are bounded. Keep the journal append-only for the run, with a conservative hard byte
ceiling and a final `observability_truncated` diagnostic rather than rotating away the
beginning. Failure to append observability must never change a finalizer verdict.

### 2. Bounded live attempt output

For subprocess-backed operations, add an optional chunk observer to the existing
bounded subprocess plumbing and mirror human-readable chunks to a bounded
`attempt-N.live.log` plus at most one rotated predecessor. Keep immutable terminal
stdout/stderr/protocol files as evidence of record. The live file is explicitly a
convenience view: cross-stream ordering may be approximate, and plugin protocol stdout
should not be displayed as a human log unless the provider marks it suitable.

Use the existing bounded-log/rotation utilities and output renderer. Sink failures are
swallowed after recording a diagnostic. Never let disk pressure in an optional live
tail fail the finalizer itself.

### 3. Cheap row summary in agent metadata

Extend the existing `agent_meta.json["finalizers"]` projection with a small runtime
summary updated only at semantic boundaries:

```json
{
  "plan_digest": "…",
  "selected": ["commit", "check"],
  "raw_operations": ["commit", "check"],
  "runtime": {
    "phase": "running",
    "active_instance_id": "check",
    "attempt": 1,
    "selected_count": 2,
    "attention_count": 0,
    "started_at": "…",
    "updated_at": "…"
  }
}
```

On terminal write, publish the aggregate summary to metadata before the ordinary done
marker. This gives the scanner a tiny stable input and avoids parsing finalizer trees
for every list refresh. Because Rust's `AgentMetaWire` and scanner schema are fixed and
currently omit finalizers, this is a real scan-schema evolution (with the corresponding
Python mirror, fixtures, and revision pin), not a free untyped dictionary addition.

### 4. Shared core projection

Add a separate Rust artifact-read model, conceptually:

```text
FinalizerRunProjectionInput
  plan artifact bytes
  context artifact bytes?
  progress records?
  result artifact bytes?
  bounded output inventory
  runner identity/liveness

        ↓ deterministic reconciliation

FinalizerRunSnapshot
  aggregate summary
  ordered instance snapshots
  execution scopes
  attempts
  diagnostics/evidence/output references
  provenance and degraded-state reasons
```

Python should perform capped filesystem reads in a worker and pass the byte/content
inputs to `sase_core_rs`; Rust should own validation, precedence, normalization, DAG
ordering, diagnostic deduplication, and interruption inference. This keeps CLI, future
web UI, and TUI behavior aligned while respecting the established core boundary. Do
not add these presentation states to finalizer execution wire v2.

Result loading must accommodate real legacy artifacts. The old corpus found a 3.32 MB
result caused by repeated diagnostics, so a 1 MB UI cap would reject known evidence.
Load off-thread with an explicit cap comfortably above that legacy case (for example 8
MiB), then cap/deduplicate the projected diagnostics and render a clear “artifact too
large” fallback beyond the limit. The writer should also prevent repeat amplification
going forward.

## TUI loading and interaction

The TUI must never stat, parse JSON, or tail logs in `compose()`/`render()`. Add a
selected-agent finalizer snapshot cache keyed by concrete artifact identities plus
file `(mtime_ns, size)` signatures. Follow the existing pattern:

1. render the last immutable cached deck immediately;
2. debounce selected-agent detail work;
3. read capped artifacts and call core projection in a worker;
4. reject stale generations when selection/layout changes;
5. mount a precomposed deck view on the event loop.

List refresh should observe only the compact metadata projection. Detail invalidation
should recognize plan/context/progress/result and selected live-log changes, but a log
chunk must not trigger a global Agents rescan. Poll/tail more frequently only while the
Finalizers deck (or modal) is visible and the selected run is active. Short successful
finalizers should pass without a flashing log pane; reveal live output after a small
delay or immediately on failure/user drill-down.

Tail following should occur only when the viewport is already at the bottom. Scrolling
up pauses follow and shows a “new output” affordance; jumping to latest resumes it.
This prevents the classic live-log failure mode where incoming text repeatedly yanks a
user away from the line being inspected.

Search should index overview labels, instance/provider ids, statuses, diagnostic codes
and messages, evidence labels/values, attempt summaries, and visible bounded output.
Search results switch to the Finalizers deck and focus the appropriate card/block. The
editor action opens the exact durable artifact, while export/copy clearly labels live
output as non-authoritative.

## Security and correctness constraints

- The UI is read-only initially. Retrying, bypassing, or cancelling finalizers changes
  host-owned completion and has idempotency/authorization consequences that deserve a
  separate command design.
- Never render provider-supplied Rich markup. Treat output, evidence, and diagnostics
  as untrusted text and apply existing ANSI/control sanitization.
- Never expose the authority plan's sealed secrets/config snapshot. The visible plan,
  normalized context/result, and allowlisted evidence are sufficient.
- Cap bytes, records, lines, and projected diagnostics before mounting widgets.
- Preserve full instance ids in the detail/modal even if compact list labels truncate.
- Make stale, partial, mismatched, or corrupt data visually explicit. Observability
  should fail degraded, while finalizer execution continues independently.
- Prepared-monitor and ordinary provider completion must emit the same progress
  contract. Keep the monitor's existing one-line Main summary as a link/summary, not a
  second detail implementation.

## Delivery sequence

### Slice 1: durable truth and core projection

- Add semantic events and live-log observers to the controller/providers.
- Add the small metadata runtime summary.
- Add Rust artifact parsing/reconciliation, bindings, legacy fixtures, and corrupt/
  oversized/dead-runner tests.
- Make ordinary and prepared-monitor finalization use the same observer.
- Optionally expose a narrow diagnostic CLI view so the read model can be tested
  independently of Textual.

This slice is invisible or minimally visible but removes the inference gap before UI
work begins.

### Slice 2: deck and row UX

- Add the Finalizers deck, Overview and instance cards, deck picker/cycle/persistence,
  row display phase/chip, search, editor/export, and read-only attempt modal.
- Implement off-thread cache/loading and selected-detail invalidation.
- Cover narrow/wide, one/two-panel, active/success/failure/refusal/deferred/interrupted,
  corrupt, and historical snapshots.

### Slice 3: card blocks and session aggregation

- Adapt instance cards to generic card blocks once that feature lands.
- Group concrete shell executions by stable instance id for session selections.
- Reuse the common rail/older-newer behavior and preserve card preference.
- Add prepared-monitor provenance and multi-cycle histories as ordinary block metadata.

This ordering deliberately avoids coupling finalizer visibility to the card-block
delivery date while preserving a clean migration.

## Verification targets

The most important tests are not pixel snapshots alone:

- artifact reconciliation matrices for terminal-result precedence, partial progress,
  dead runner, digest mismatch, dependency failure, retry, reactivation, refusal,
  deferral, and legacy plan/result-only runs;
- golden projections shared by Rust and Python bindings;
- scanner schema compatibility and metadata-summary behavior;
- no-I/O render/compose assertions and quiet-tick cache tests;
- rapid selection/deck/layout changes with stale worker completion;
- bounded/corrupt/oversized JSON and live logs containing ANSI/control sequences;
- session grouping where the same instance exists in several shells, only some shells,
  or with different plan digests;
- sticky instance-card selection across agents and newest-block landing within a
  session;
- list semantics proving `FINALIZING` does not accidentally change lifecycle filters,
  actions, capacity, or cleanup.

## Recommended solution

Implement a **read-only Finalizers deck** with an Overview card and one stable card per
finalizer instance. Give the Agents list a sparse `FINALIZING` display phase and
attention chip, while keeping lifecycle semantics unchanged. Model a future card block
as one concrete shell/run execution of that instance; keep attempts as rows within the
block and use a modal for full bounded output, diagnostics, evidence, and inputs.

Before exposing the deck, add three generic observability primitives: a versioned
semantic progress journal, bounded human-readable live attempt logs, and a compact
runtime summary in agent metadata. Reconcile those with the existing plan, context,
terminal result, artifact inventory, and runner liveness through a new deterministic
`sase_core` projection. Do not change the strict finalizer execution protocol merely
for UI state, do not treat finalizers as tool calls or child agents, and do not build
the layout around commit-specific fields.

Ship the projection and observer first, the concrete-agent deck second, and card-block
session history third. This yields immediate, honest troubleshooting for today's
commit finalizer while giving every future finalizer the same scalable navigation,
state semantics, safety boundary, and audit trail.
