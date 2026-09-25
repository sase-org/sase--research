# Finalizer observability on the Agents tab

**Researcher:** cdx  
**Date:** 2026-09-25  
**Scope:** UX and implementation architecture for visualizing and troubleshooting SASE finalizers on the Agents tab

## Executive conclusion

Finalizers should become a first-class, terminal chapter of an agent's lifecycle without becoming a second kind of agent or a permanently noisy dashboard feature.

I recommend a layered design:

1. Show `FINALIZING` as a real live phase in the agent row, plus a compact finalizer warning chip only when attention is useful.
2. Add a **Finalizers** card to the existing **Main** deck, after Context and Reply/Output. The card is the routine inspection surface: aggregate state, ordered finalizer instances, dependencies, attempts, durations, evidence, and concise diagnostics.
3. On an agent-session container, use future **card blocks to represent concrete shells**, exactly as proposed for the Reply card. Each block contains that shell's finalizer story. Do not use blocks for individual finalizers or attempts.
4. Put raw and provider-specific details in a read-only **Finalizer Inspector** modal: instances, attempts, output channels, structured artifacts, and live tailing. The card should explain; the inspector should excavate.
5. Back all three surfaces with one bounded, deterministic projection in `sase_core`, fed by the sealed plan, final context/result, an append-only progress journal, and an explicit output-artifact catalog. Do not derive execution state from filenames or subprocess output.

This preserves the strengths of the earlier finalizer-panel proposal while adapting it to the deck/card architecture that landed afterward. It also remains generic when SASE has many finalizer providers, dependency chains, fixed-point cycles, and output shapes unlike the built-in `commit` finalizer.

## Research basis

I reviewed the two requested research artifacts:

- `research:202609/agents_tab_finalizer_panel/agents_tab_finalizer_panel.md`
- `research:202609/agent_data_card_blocks/agent_data_card_blocks.md`

I then traced the current finalizer runtime, artifact wires, agent scanner, Agents-tab deck/card code, modal patterns, and bounded subprocess runner in the current `sase` checkout, plus the corresponding finalizer and agent-scan wires in `sase_core`. I also sampled the retained local finalizer corpus under the SASE project store. This was an independent investigation; no other report from the current research swarm was consulted.

Relevant current implementation areas include:

- `src/sase/llm_provider/_invoke.py`
- `src/sase/finalizers/controller.py`
- `src/sase/finalizers/wire.py`
- `src/sase/finalizers/bounded_subprocess.py`
- `src/sase/tui/agent_data.py`
- `src/sase/tui/agent_data_decks.py`
- `src/sase/tui/agent_data_cards.py`
- `src/sase/tui/models.py`
- `crates/sase_core/src/finalizer/wire.rs` in `sase_core`
- `crates/sase_core/src/agent_scan/wire.rs` in `sase_core`

The old finalizer-panel report remains strong on state vocabulary, progressive disclosure, bounded parsing, and live observability. Its proposed placement as a foldable detail section predates the Main/Files/Tools deck architecture, however. The card-block report supplies the missing composition rule: a deck contains cards; a card may be divided into non-nesting blocks representing a stable repeated dimension.

## What exists today

### The runtime is generic even though the retained corpus is not

Before provider execution, `_invoke.py` resolves and persists a sealed finalizer plan and stores a small projection in `agent_meta.json`. After a normal provider return, the finalizer controller executes the selected instances. It supports:

- provider-neutral instance IDs and provider references;
- `after` dependencies and ordered execution;
- refusal policies and typed deferrals;
- bounded retries;
- up to eight fixed-point cycles;
- commit reactivation after another finalizer changes repository state;
- evidence and diagnostics per attempt;
- a terminal aggregate result.

Monitor-driven host completion enters the same controller. A useful design therefore cannot assume that every run is a conventional LLM agent, that every provider is `commit`, or that one finalizer maps to one subprocess.

The retained corpus at the time of research contained 503 sealed plans and 259 terminal results. Every selected instance was `commit`; 247 results succeeded and 12 failed. Of the successful and failed instances, 26 recorded no execution attempt, 232 recorded one, and one recorded two. Every retained result used one controller cycle. This is useful evidence about today's common path, but it is exactly the dataset that could cause a design to overfit the built-in finalizer.

The files already demonstrate why that would be a mistake. Generic command providers commonly write `attempt-N.stdout`, `attempt-N.stderr`, and diagnostics. The commit provider can instead produce target-qualified files such as `attempt-1.main.stdout`, `attempt-1.research.outcome.json`, conflict-repair prompts and responses, and other per-repository records. Plugin-worker stdout is also a JSON protocol channel, not necessarily human-readable log text. A UI that discovers `attempt-N.stdout` by globbing has already encoded the wrong abstraction.

### There is a blind interval

The controller has the most useful live facts only in memory: current cycle, active instance, active attempt, provider, start time, accumulated evidence, and diagnostics. The aggregate result is written only when execution finishes or fails. Long-running finalizers therefore look like a provider that has stopped producing visible progress.

The current `agent_meta.json` finalizer projection contains the plan digest, selected IDs, and raw operations, but not a lifecycle phase or active execution. More importantly, both the Python and Rust agent-scan wires enumerate fields explicitly and currently discard `finalizers` and `finalizers_drift`. The data is written, but the Agents tab cannot receive it through the normal scan model.

### Absence of a result is ambiguous

`should_skip_finalizers()` intentionally skips execution when:

- no artifacts require finalization;
- the run does not have a SASE agent timestamp; or
- a plan, questions, monitor, gate, or pipe handoff is pending.

The local sample included 244 plans without a terminal result. Some had a completed or failed `done.json`; many had neither. Pending handoff markers are ephemeral and may have been cleaned by the time a user inspects history. Therefore:

> A sealed plan without a result is not evidence of interruption.

It may mean a legitimate handoff, a non-triggering context, a historical run from before richer telemetry, or a genuinely interrupted controller. The UI must distinguish these only from positive observations. It must never manufacture a red failure from missing files.

### The current Agents tab has a better home than a new pane

The Main deck now tells the lifecycle story with Context and Reply/Output cards. Files and Tools are separate decks for genuinely different content families. Deck panels can compare two cards, and chosen cards can remain sticky while the user navigates agents. This changes the placement decision from the earlier report.

A new Finalizers deck would add another global cycle stop even when most successful agents have little worth inspecting. It would separate the end of an agent's lifecycle from its beginning and response, and it would make Reply-versus-finalizer diagnosis require cross-deck navigation. A permanent standalone pane has similar space and noise costs.

Finalization is part of Main.

## Proposed experience

### 1. Agent row: communicate phase and attention

While the host owns finalization, render the live status as `FINALIZING`, while retaining the broader Running bucket for filtering and state machinery. This matters because the provider has returned but the agent is not complete.

Use a small glyph-plus-text signal, never color alone:

| Situation | Row treatment |
|---|---|
| Actively finalizing | `⛭ active` and `FINALIZING` |
| Terminal success or not triggered | no persistent chip |
| Failed/refused | `⛭ failed` |
| Deferred/handed off | `⛭ deferred` or `⛭ handed off` |
| Interrupted/unavailable telemetry | `⛭ interrupted` or `⛭ unavailable` |

Success should become visually quiet after completion. The row's job is triage, not history. The Main card retains the durable story.

### 2. Main deck: a Finalizers card

For runs with a nonempty sealed plan or any finalizer observation, Main becomes:

```text
Main
  Context
  Reply / Output
  Finalizers
```

Do not add the card to true legacy runs with no plan and no observation. Do not automatically move focus to it when finalization starts or fails: changing the user's selected card during navigation would be disruptive. If the user selects Finalizers, normal sticky-card behavior should make it easy to walk a series of agents and compare the same lifecycle phase. A split deck panel can show Reply and Finalizers together.

The normal card should answer four questions in one glance:

1. Did finalization run?
2. What is running or what failed?
3. What happened before and after it?
4. Where do I go for proof?

One possible rendering:

```text
FINALIZERS  failed · 1/3 succeeded · 14m 08s
plan 8a92d1f0 · cycle 1 · updated 10s ago

✓ snapshot     plugin:snapshot     attempt 1/1   1.2s
✗ publish      command:publish     attempt 2/2   14m 06s
  after: snapshot
  exit 1 · stderr: authentication expired
— notify       plugin:notify       blocked by publish

[Enter] inspect attempts and output
```

The exact typography should follow the existing card visual language. The information hierarchy is more important:

- A preamble gives aggregate phase/status, succeeded/total count, elapsed time, current cycle, short plan identity, and drift warning.
- Instance rows follow resolved plan order, not filename or completion order.
- Each row shows state, stable instance ID, provider reference, attempt gauge, duration, salient evidence, and dependency when relevant.
- Only the active or most important non-success row expands by default.
- Full fold levels expose attempt history, scoped diagnostics, evidence, typed deferral, affected paths, and a small bounded output tail.
- Successful rows collapse to one line.

This is the card equivalent of the earlier report's foldable `FINALIZERS` section, but it composes naturally with current navigation and split comparison.

### 3. Card blocks: use the shell dimension, not the attempt dimension

Card blocks should play a meaningful but deliberately limited role.

On a concrete agent shell, the Finalizers card needs no visible block wrapper. On an agent-session container that aggregates several concrete shells, use one block per concrete shell in the same chronological order and with the same shell identity as the Reply card:

```text
Finalizers card for session
  block: shell 1  -> that shell's finalizer pipeline
  block: shell 2  -> that shell's finalizer pipeline
  block: shell 3  -> that shell's finalizer pipeline
```

Land on the newest shell; use the future block navigation to inspect older shells. When rendered in a spread, blocks remain inline as the card-block proposal specifies.

Do **not** use one block per finalizer instance or per attempt. Blocks do not nest, so choosing instances consumes the only repeated structural dimension and conflicts with session history. It would also make the same Finalizers card mean one thing on a shell and another on a session. Finalizer instances are a dependency-ordered pipeline and belong as rows/sections inside the shell's block. Attempts are subordinate details and belong under the instance or in the inspector.

This rule scales cleanly:

```text
deck -> card -> shell block -> finalizer instance row -> attempt detail
```

The card can ship before block-view support by rendering the same per-shell chunks contiguously. Later wrapping them in transparent CardBlock objects should not change the content model.

### 4. Finalizer Inspector: the diagnostic long tail

The Main card should not become a log browser. Add a dedicated, read-only modal reachable from the focused Finalizers card, a command-palette action, and a registered contextual key such as `,F` if that chord remains free when implemented.

Use the existing split-list/detail modal language, but make a distinct component rather than overloading patch run history:

```text
┌ Finalizer Inspector ─────────────────────────────────────┐
│ pipeline / attempts        │ selected detail            │
│ ✓ snapshot                 │ attempt 2 · 14m 06s        │
│ ✗ publish                  │ stderr                     │
│   ├ attempt 1              │ ... bounded, sanitized ... │
│   └ attempt 2              │                            │
│     ├ stdout               │                            │
│     ├ stderr               │                            │
│     ├ inputs               │                            │
│     └ outcome              │                            │
│ — notify                   │                            │
└────────────────────────────┴────────────────────────────┘
```

Default selection should be the current instance while running, otherwise the latest failed/refused/deferred instance, otherwise the last instance. The right pane can render text, JSON, evidence, diagnostics, inputs, or provider-described artifacts. It should follow a live stream until the user scrolls upward, then pause following in the familiar log-viewer manner.

Version one should not offer cancel, retry, or rerun. Those are control-plane operations with nonce, idempotency, repository-state, and dependency semantics; observability should not imply that a finalizer is just a restartable job.

## State model and source precedence

The UI needs explicit states rather than deriving meaning from color or file presence:

- `selected`
- `pending`
- `running`
- `retrying`
- `success`
- `not triggered`
- `handed off`
- `blocked / not run`
- `deferred`
- `refused`
- `failed`
- `interrupted`
- `unavailable`

`handed off` is important because SASE agents are single-turn and completion is host-owned. A plan/questions/monitor/gate/pipe transition is normal lifecycle behavior, not failure.

Reconciliation should use strict precedence:

1. The authenticated sealed plan owns selection, resolved order, dependencies, policy, provider references, and plan identity.
2. A valid terminal result matching the run identity and plan digest owns terminal verdicts.
3. A matching progress journal can describe live state and explicit skip/handoff outcomes before a terminal result exists.
4. Final context explains trigger decisions such as `not triggered`.
5. Output artifacts are evidence only. They never determine state.
6. A plan with no later positive observation is `unavailable` for historical purposes, not automatically `interrupted`.
7. `interrupted` requires positive evidence that finalization started plus evidence that its owning runner is dead without a terminal record.

When a dependency fails, later planned instances should be shown as `blocked / not run`, including the blocking predecessor when known. When a provider succeeds without needing an attempt, render `not triggered`, not a mysterious zero-attempt success.

## Data contract

### Compact summary for rows

Extend the existing `agent_meta.finalizers` projection with a compact observation summary, for example:

```json
{
  "plan_digest": "...",
  "selected": ["snapshot", "publish", "notify"],
  "phase": "running",
  "aggregate_status": "running",
  "active_instance_id": "publish",
  "active_attempt": 2,
  "updated_at": "2026-09-25T12:34:56Z"
}
```

Carry that bounded object through the Rust and Python agent-scan wires and into `AgentState`. Because the artifact index's list projection already retains ordinary agent-meta fields, this gives the row enough information without opening per-run artifacts during rendering. Updating `agent_meta.json` also uses an already-watched surface rather than inventing a polling path.

### Append-only semantic progress journal

Add a bounded `finalizers/progress.jsonl` journal written best-effort by the host controller. Suggested events:

- `phase_started`
- `phase_skipped` with a typed reason such as `handoff`, `no_artifacts`, or `missing_agent_identity`
- `cycle_started`
- `instance_started` / `instance_finished`
- `attempt_started` / `attempt_finished`
- `phase_finished`

Each event should carry the run/agent/nonce identity, plan digest, monotonically increasing sequence, instance/provider identifiers when applicable, wall-clock timestamp, and writer-computed duration where applicable. A telemetry-write failure must not change the finalizer verdict.

This journal solves both live progress and historical ambiguity. It should be treated as a semantic event source, not a log file to print directly.

### Explicit output-artifact catalog

Providers should register observable files through a host-owned catalog rather than requiring the UI to infer meaning from filenames. Each entry should describe at least:

- instance ID and provider reference;
- cycle or execution ordinal;
- attempt number;
- operation/target label;
- content kind and media type;
- relative path;
- live versus immutable/terminal status;
- byte size and truncation status;
- safe display hint (`text`, `json`, `diagnostics`, `input`, `outcome`, or `protocol`).

The host validates that paths remain inside the finalizer artifact root and do not escape through symlinks. This catalog accommodates command stdout/stderr, multi-repository commit artifacts, plugin protocol records, future API traces, and finalizers that produce no textual log at all.

For live subprocess output, extend the existing bounded reader with optional host-owned sinks. Keep the current bounded in-memory capture and immutable terminal attempt artifacts as the execution contract. The live sink can write separately bounded per-stream files or chunks registered in the catalog. A slow or failed sink must never block the child reader or alter timeout/deadlock behavior.

### One shared projection in `sase_core`

Add a new read-model wire such as `FinalizerRunViewWire`; do not mutate the execution wire merely to fit one frontend. It should reconcile:

- sealed plan;
- final context;
- terminal result;
- progress events;
- runner liveness/handoff observation;
- artifact descriptors.

The projection returns bounded aggregate and per-instance states, attempts, durations, scoped diagnostics/evidence, and described outputs. Shared precedence and state semantics belong in Rust so the TUI, CLI, web UI, and editor integrations do not disagree. Python should perform bounded filesystem reads off the UI thread and pass parsed inputs through the binding. Landing such a change requires the normal `sase-core-revision.txt` pin update after the core commit.

## Performance, resilience, and safety

The Agents tab's navigation path must remain filesystem-free. Finalizer support should follow these constraints:

- Row state comes from the normal indexed/scanned `AgentState`, not per-row artifact reads.
- Full detail loads only for the selected agent, in a worker, after the normal detail-panel debounce.
- Cache the projection by bounded file signatures and reject stale worker results after selection changes.
- A quiet refresh tick performs no finalizer reads and causes no redraw.
- Live-output updates refresh only the focused card/inspector, not the agent list.
- Impose byte, line, event, attempt, and diagnostic caps before parsing or rendering.
- Deduplicate repeated diagnostics and scope them to the relevant attempt. The controller currently makes repeated accumulation possible even though today's retained results are small.
- Sanitize ANSI/OSC sequences and render output as inert text, never Rich/Textual markup.
- Tail large streams and fetch older chunks only on explicit demand.
- Delay noisy live-tail presentation for a few seconds so fast finalizers do not flicker.

The retained result set was modest during this research (about 224 KB total, with a largest result around 7.4 KB), but an earlier corpus analysis found a multi-megabyte pathological result caused by repeated diagnostics. The implementation should defend the structural boundary, not tune itself to the currently retained happy path.

## Delivery sequence

### Phase 1: truthful lifecycle and terminal card

- Define the shared core read model and reconciliation fixtures.
- Record explicit start/skip/finish progress events.
- Carry a compact finalizer summary through agent scanning.
- Render `FINALIZING`, attention chips, and the Main-deck Finalizers card from bounded terminal/live data.
- Treat plan-only history as unavailable unless stronger evidence exists.

This phase immediately eliminates the invisible-finalizer gap without needing raw live logs.

### Phase 2: session composition and inspector

- Integrate shell-identity blocks when the CardBlock substrate is ready.
- Add the output-artifact catalog to generic provider helpers and built-ins.
- Add the read-only Finalizer Inspector for terminal attempts and artifacts.
- Cover non-command artifacts, structured protocol channels, and multi-target outputs.

### Phase 3: live output and polish

- Add non-blocking live sinks to bounded subprocess execution.
- Tail active output selectively in the card and inspector.
- Add paused-follow behavior, copy/export affordances, width/theme snapshots, and accessibility polish.

This order avoids coupling the basic UI to the hardest live-streaming work and avoids shipping logs before state semantics are trustworthy.

## Verification priorities

The test matrix should intentionally defeat commit-only assumptions:

- multi-instance dependency success and failure;
- a command provider with retries;
- a plugin provider whose stdout is protocol data;
- a provider with structured artifacts but no log;
- a multi-repository commit run;
- fixed-point reactivation across cycles;
- not-triggered, handed-off, refused, deferred, failed, blocked, interrupted, and unavailable states;
- digest/identity mismatch and truncated/corrupt progress tails;
- very large/repeated diagnostics and oversized output;
- session cards with multiple shell blocks and a single-shell transparent case;
- sticky Finalizers navigation and Reply/Finalizers split comparison;
- no focus jump when finalization starts or ends;
- unchanged p95 list navigation and zero finalizer I/O on quiet ticks;
- live-sink failures that do not alter child-process behavior or finalizer verdicts.

## Alternatives considered

### A dedicated Finalizers deck

This offers conceptual isolation but is too expensive in routine navigation. It creates an often-empty global deck, fragments one lifecycle across decks, and makes direct Reply/finalizer comparison awkward. Reconsider only if future finalizers develop several independent card families rather than a single pipeline story.

### A permanent foldable section in the general detail document

This was sensible before cards. Today it bypasses sticky card navigation and split comparison, and it lets finalizer detail compete vertically with Context and Reply. The useful folding behavior should live inside the Finalizers card instead.

### One card block per finalizer or attempt

This looks attractive for many future finalizers but spends the sole non-nesting block dimension on an internal pipeline detail. It fails to compose with multi-shell sessions and obscures dependencies. Rows and folds are the correct representation for instances; the inspector is correct for attempts.

### Modal-only support

A modal can diagnose, but it cannot communicate that an apparently finished provider is still finalizing or allow rapid cross-agent triage. It is a necessary third layer, not the primary surface.

## Recommended solution

Implement finalizer support as **row signal + Main-deck Finalizers card + shell-oriented card blocks + read-only inspector**, all driven by a shared `sase_core` observation projection.

Specifically: add `FINALIZING` and quiet attention chips to agent rows; add Finalizers after Reply/Output in Main; use one block per concrete shell only when a session aggregates shells; represent finalizer instances as ordered rows and attempts as subordinate detail; and expose provider-described artifacts in a dedicated inspector. Back this with explicit progress events, a compact agent-meta summary, and a generic artifact catalog, with strict precedence that treats handoffs and not-triggered runs as normal and never guesses failure from a missing result.

Do not add a top-level Finalizers deck, do not use blocks for attempts, and do not infer state or output semantics from commit-specific filenames. That combination provides excellent routine visibility today and a stable architecture for the several new finalizers expected next.
