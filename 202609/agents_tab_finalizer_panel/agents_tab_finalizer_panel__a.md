# Agent finalizer observability in the Agents tab

**Researcher:** A  
**Date:** 2026-09-10  
**Scope:** Read-only presentation of the finalizers selected for an agent run, their live progress, and their terminal outcomes in ACE's Agents tab.

## Executive summary

The best experience is a first-class, foldable **FINALIZERS** section in the selected agent's existing metadata document—not a permanent new pane, a modal-only view, child rows in the agent tree, or an extension of the Tools timeline.

The section should be present as soon as the run's sealed finalizer plan exists. In its default form it shows one line per selected instance, in execution order, with an unambiguous word-and-glyph state, attempt count, and elapsed time. Expanding a running or failed row reveals its current operation, structured diagnostic, and a small bounded log tail. Full output remains one explicit action away. This answers the common questions at a glance without making every agent detail view look like a terminal multiplexer.

That UI should not be built by inferring progress from today's files. The repository currently has authoritative inputs and terminal outputs, but almost no durable state during execution:

- `finalizer_plan.json` reliably records the sealed, ordered selection.
- `finalizer_result.json` is written atomically only at controller termination.
- command, provider, and stitch stdout/stderr are accumulated in memory and written only after the subprocess returns.
- the controller's active instance, attempt, and timing are local variables.
- writes under `finalizers/<instance>/` are not Agents-tab refresh markers.

Consequently, a renderer-only implementation would be attractive but unreliable: it could show what was selected and what eventually happened, but it could not truthfully distinguish queued, running, retrying, stuck, or interrupted work.

I recommend adding a small versioned observation protocol alongside the existing execution protocol:

1. Keep the sealed plan as the authority for what was selected.
2. Add an atomically replaced `finalizer_state.json` for the cheap current snapshot and an append-only `finalizer_events.jsonl` for a durable transition timeline.
3. Tee bounded subprocess streams into explicit live files, then atomically promote them to the existing terminal artifact names.
4. Extend the terminal result projection so every selected instance receives a terminal disposition and useful human summary/output references.
5. Parse and reconcile these records in the Rust core, expose one frontend-neutral `FinalizerObservation`, and let the TUI render it through a new asynchronously loaded metadata lane.

This separates three concerns that should not be conflated: execution status, user-facing summary, and raw output. It also creates an observability contract that a future CLI, web app, or remote fleet view can reuse.

## Research questions and terminology

The requested questions are deceptively different:

1. **What finalizers are enabled?** For an individual historical run, the useful and truthful term is **selected for this run**. The globally configured instance registry may have changed since launch and includes instances irrelevant to this agent. The sealed plan should therefore drive the view. Badges can explain whether an instance came from defaults, an explicit selector, or a required policy.
2. **Which are running?** This requires authoritative runtime state. Process existence or the presence of a partly written file is not enough.
3. **What happened?** A terminal verdict, a concise summary, structured diagnostics/evidence, and raw stdout/stderr are four different levels of information. The default UI should show them in that order.

I use **finalizer** for a selected instance such as `commit` or `lint`; **operation** for provider phases such as describe/validate/execute/verify; and **substep** for implementation-specific work such as stitching one repository. A user should not have to know those distinctions, but the data model needs them to avoid a vague spinner that says only “commit is running” for several minutes.

## What exists today

### The durable contract is strong before and after execution

The configuration model already has the right identity and ordering concepts. `docs/configuration.md` documents defaults, required instances, explicit selectors, `after` dependencies, retry limits, refusal behavior, and named instances. `src/sase/finalizers/plan.py` seals an ordered plan with a `plan_digest`, stable instance IDs, provider references, dependency order, policy, and provenance. This is the correct source for the run-specific answer to “what is enabled?”

At the other end, `src/sase/finalizers/controller_results.py` publishes an atomic aggregate `finalizer_result.json`. Its instance wires contain terminal status, attempts, deferral/refusal information, evidence, and diagnostics. `src/sase/axe/runner_reporting.py` already trusts this artifact for completion error reporting. These records should remain the authority for the terminal verdict.

The finalizer system has also recently accumulated substantial integrity and fixed-point behavior (`b1c6bb105`, `78550c993`, `980bedfea`, and `2f9c4ae29`). That history argues for a typed projection rather than a TUI that reverse-engineers operational files and silently diverges as the controller evolves.

### Execution is currently a black box

The missing middle is visible in several implementation paths:

- `src/sase/finalizers/controller.py` keeps `active_instance_id`, `active_provider_ref`, start time, ledgers, and the set of completed non-commit instances in memory. The controller can revisit commit over as many as eight fixed-point cycles, but only publishes the aggregate result when it exits or fails.
- `src/sase/finalizers/bounded_subprocess.py` correctly avoids pipe deadlocks, caps each stream at 1 MiB, enforces a hard timeout, and terminates the process group. Its reader threads append to in-memory buffers; there is no observer callback or live sink.
- `src/sase/finalizers/executor_command.py` writes `attempt-N.stdout`, `attempt-N.stderr`, and diagnostics only after a command attempt finishes.
- `src/sase/finalizers/executor_plugin.py` similarly writes describe/validate/execute/verify output after each provider operation. Provider stdout is protocol JSON, not necessarily a human log stream.
- `src/sase/finalizers/commit_repair.py` writes per-repository stitch output after the stitch subprocess returns. A single commit finalizer may encompass multiple repositories and conflict-repair passes.
- `src/sase/finalizers/ledger.py` knows attempts, evidence, diagnostics, and retry budget, but only in the controller process.

There is also a terminal completeness issue. `src/sase/finalizers/controller_results.py` writes the instance results accumulated so far. On an early failure, later selected instances can be absent rather than explicitly marked “not run because dependency X failed.” A UI must not translate absence into either success or eternal pending.

### The Agents tab has a natural home for this information

`src/sase/ace/tui/widgets/agent_detail.py` presents a composite selected-agent view. The right side is a metadata document with section navigation, folding, zoom, and existing modes for prompt/file/tools. A dedicated permanent pane would compete with those modes and spend scarce width even for runs with no interesting finalizer activity.

The closest interaction precedent is the **SLOW TOOL CALLS** section implemented by `src/sase/ace/tui/widgets/prompt_panel/_agent_slow_tools.py`: it has compact/detail/full fold levels, bounded rows, status glyphs, and an escape hatch to a richer timeline. `src/sase/ace/tui/widgets/prompt_panel/_agent_display_header.py` and `_agent_display_state.py` compose these lanes into one navigable document. Finalizers fit this grammar well, while remaining semantically separate from model-issued tools: finalizers are host-owned completion work and may continue after the provider turn has ended.

The loading architecture is also suitable. `_agent_display_header_summary.py` maintains per-lane caches, mtime signatures, and refresh intervals; `_agent_display_async_agent.py` performs file work off the UI thread and rejects stale results with a selection generation. `src/sase/agent/artifact_files_cache.py` already includes an append-aware tail cache. The finalizer view can reuse those patterns.

Two current gaps matter:

- `src/sase/ace/tui/actions/event_refresh/_constants.py` does not treat finalizer state/result files as agent refresh markers.
- `_artifact_paths.py`, `_auto_refresh.py`, and `agents/_live_watch_coverage.py` are optimized around known top-level markers and selected live-file refreshes. Rebuilding the agent list for every log chunk would violate that design and create avoidable churn.

Finally, these artifacts already have an appropriate lifetime. `src/sase/core/managed_tmp_reaper.py` gives `workflow-artifacts/` a 14-day run-artifact horizon specifically because the Agents tab reads those directories after completion. The new records should live inside the same run directory and be covered by retention and archive tests.

## UX goals

The view should satisfy six properties:

1. **Immediate:** after selecting an agent, cached information paints synchronously; enrichment arrives without freezing navigation.
2. **Truthful:** “running,” “failed,” and “not run” come from durable facts with explicit precedence, never directory guesses.
3. **Quiet by default:** progress is visible, but output does not push the prompt and metadata off-screen.
4. **Inspectable:** one expansion reveals why something is slow or failed, and one further action opens the complete artifact.
5. **Stable under updates:** new output never steals focus, changes the user's fold choice, or yanks a scrolled viewport back to the bottom.
6. **Consistent across time and place:** live, terminal, archived, family, and eventually remote views use the same vocabulary and reconciliation rules.

## Alternatives considered

| Placement | Strengths | Problems | Verdict |
|---|---|---|---|
| Foldable metadata section | Visible with identity/context; uses existing navigation, folding, zoom, and responsive layout | Needs a new summary lane and careful refresh path | **Recommended** |
| New permanent side pane | Maximum simultaneous detail | Consumes width, creates empty chrome, complicates narrow layouts | Reject |
| New `]`-cycled detail mode | Plenty of room for logs | Hides the basic selected/status answers behind a mode switch | Use only as an optional future deep view |
| Modal/pager only | Simple, excellent for full logs | Poor discoverability; no at-a-glance live state | Keep as the full-output escape hatch |
| Reuse Tools timeline | Existing live activity UI | Wrong ownership and lifecycle; provider protocol output is not a model tool call | Reject |
| Child rows in agent tree | Highly visible | Finalizers are not agents, clutters families, harms scanability | Reject |

The metadata section wins because the common case is a small structured summary, while the exceptional case is a deep log. Progressive disclosure lets both coexist.

## Proposed interaction design

### Placement and default view

Add `FINALIZERS` as a peer to the existing metadata sections, above the prompt/context bulk. Show it whenever a valid sealed plan exists, even before finalization starts. Omit it for legacy runs that have no plan; if a plan exists but cannot be authenticated or parsed, show a visible “unavailable” warning instead of pretending that zero finalizers were selected.

The section heading should summarize the current phase:

- `FINALIZERS · 3 selected · starts after agent response`
- `FINALIZERS · 1 running · 1 passed · 1 queued`
- `FINALIZERS · passed · 3 in 18.4s`
- `FINALIZERS · failed · 1 of 3`

The normal fold level shows all selected instances when the set is small. Each row includes a glyph, an explicit state word, instance ID, human provider label, attempt/budget when relevant, and duration. Dependency or policy information appears only when it explains waiting or non-execution.

```text
▼ FINALIZERS · 1 running · 1 passed · 1 queued
  ✓ commit   passed · 2.4s
  ◐ lint     running · attempt 1/2 · 8s
  ○ notify   queued · after lint
```

Provider references such as `builtin@command` are useful provenance but visually secondary. Instance IDs are the stable primary labels because users configure and recognize them. A `required` badge should appear only where it adds information; provenance such as “default” or “explicit” belongs in the full fold.

### Expanded running and failed rows

The full fold reveals structured progress and, for only the active or selected instance, a small live tail:

```text
▼ FINALIZERS · 1 running · 1 passed · 1 queued
  ✓ commit   builtin@commit · passed · 2.4s
  ◐ lint     builtin@command · attempt 1/2 · 8s
    execute · tests/ace/tui
    │ 218 passed, 3 skipped
    │ collecting visual snapshots…
    └ ↓ 14 new lines · @ open full log
  ○ notify   queued · waiting for lint
```

A terminal failure gets exception-first treatment:

```text
▼ FINALIZERS · failed · 2 passed · 1 failed
  ✓ commit   passed · 2.4s
  ✗ lint     failed · 12.8s · command_failed
    tests/ace/tui/test_agent_detail.py::test_compact FAILED
    @ open stderr · % copy artifact path
  – notify   not run · blocked by lint
```

This follows a useful precedent from GitHub Actions: failed steps are expanded automatically and precise/full logs remain available separately ([workflow run logs](https://docs.github.com/en/actions/how-tos/monitor-workflows/use-workflow-run-logs)). Apply that behavior only as the initial logical fold state. Never override an explicit user fold choice or move the scroll position when a result changes.

### Live-follow behavior

Raw live output should never stream into the default metadata document. It appears only when the relevant row is expanded or the section is zoomed.

When the viewport is already at the bottom, new lines may auto-follow. The instant the user scrolls upward, switches focus, folds the section, or enters a hint session, freeze the viewport and increment a quiet `↓ N new lines` indicator. Returning to the bottom or invoking a resume action reenables follow. Grafana's live-tail behavior uses the same core rule—scrolling pauses the tail, with explicit pause/resume controls—which prevents the application from fighting the reader ([Grafana Logs integration](https://grafana.com/docs/grafana/latest/visualizations/explore/logs-integration/)).

Render at most roughly 3–8 preview lines and retain a bounded in-widget tail, independent of the persisted output cap. The existing `Log` and `RichLog` widgets support real-time append, `max_lines`, and `auto_scroll` ([Textual Log](https://textual.textualize.io/widgets/log/), [Textual RichLog](https://textual.textualize.io/widgets/rich_log/)); either is suitable for a zoomed log, but the normal metadata section should remain a stable Rich renderable rather than embedding a scrolling widget inside every row.

### State vocabulary

Use glyph, word, and color together so status is readable without color and searchable in screenshots:

| UI state | Meaning |
|---|---|
| selected | In the sealed plan; controller has not started |
| queued | Controller is active, but dependencies/order block this instance |
| running | An operation or substep has started |
| retrying | A prior attempt failed and budget remains |
| passed | Terminal success |
| failed | Terminal failure |
| deferred | Deliberately left unresolved under policy; show the reason |
| refused | Finalizer refused and policy made that terminal |
| not run | Controller ended before this selected instance could run; show why |
| interrupted | Host/runner ended without a terminal finalizer result |
| unavailable | Records are corrupt, incompatible, or fail authentication |

Do not use “pending” in the UI for all of selected, queued, and retrying; it obscures the distinction users need. Likewise, retain the agent's underlying active lifecycle bucket but add a visible display phase such as `FINALIZING · lint` once the provider turn has returned. That avoids the false impression that the model is still generating without introducing a new query/status taxonomy in the first iteration.

### Families, attempts, and remote agents

Finalizers belong to concrete runs. When the selected row represents a family, group observations by member first and summarize the family heading (`5 runs · 1 active · 4 passed`). Do not merge same-named finalizers from different members into one synthetic execution. A pinned historical attempt must read only that attempt's artifacts; it must not silently borrow the latest family member's result.

For remote agents, transmit the bounded structured observation (plan identity, states, timestamps, summaries) with the normal projection. Fetch raw log ranges only after an explicit user action. The first release can label live remote logs unavailable if there is no bounded content capability; inventing polling over entire files is worse than a clear limitation.

## Observation and artifact contract

### Source precedence

The frontend should receive one reconciled projection with these precedence rules:

1. The authenticated sealed plan is authoritative for selected instances, order, provider identity, dependencies, provenance, and policy.
2. A valid terminal `finalizer_result.json` is authoritative for controller and instance outcomes.
3. A live snapshot is authoritative only for runtime phase and only when its run identity and `plan_digest` match the sealed plan.
4. Attempt output files supply content, never status.
5. If the runner is no longer live and no terminal result exists, the observation is `interrupted`/`incomplete`, not `failed` or `running`.

A terminal result always dominates a leftover live snapshot. Missing files have explicit meanings: no plan is legacy/unavailable; plan plus no controller-start is selected; controller-start plus no terminal result is active only while the runner is demonstrably live.

### New current-state snapshot

Add an atomically replaced, schema-versioned `finalizer_state.json`. It should be updated only at semantic transitions, not on every output chunk. A representative shape is:

```json
{
  "schema_version": 1,
  "run_id": "…",
  "agent_id": "…",
  "plan_digest": "…",
  "sequence": 17,
  "controller": {
    "state": "running",
    "cycle": 2,
    "started_at": "…",
    "updated_at": "…"
  },
  "instances": [
    {
      "instance_id": "commit",
      "state": "running",
      "attempt": 2,
      "max_attempts": 2,
      "operation": "execute",
      "substep": "stitch",
      "subject": "research",
      "started_at": "…",
      "output_refs": {
        "stdout": "finalizers/commit/attempt-2.research.stdout.live",
        "stderr": "finalizers/commit/attempt-2.research.stderr.live"
      }
    }
  ]
}
```

Timestamps should be wall-clock values for persistence, with durations computed from monotonic time by the writer when closing a phase. The TUI may compute a display elapsed time while the runner is live, but must not turn clock skew into an execution verdict.

### Append-only transition journal

Also add `finalizer_events.jsonl`, with a strictly increasing sequence within the controller. Events should cover controller start/finish, instance queue/start/finish, operation start/finish, attempt start/finish, retry scheduled, repository/substep start/finish, and structured diagnostic publication.

The snapshot makes selected-agent refresh cheap; the journal preserves the sequence necessary for a trustworthy expanded timeline and postmortem. This is analogous to a trace model in which a span carries start/end/status while ordered events annotate meaningful progress ([OpenTelemetry Trace API](https://opentelemetry.io/docs/specs/otel/trace/api/)). The reader should tolerate a truncated final JSONL line after a crash and never let observability-file damage alter finalizer execution semantics.

The snapshot and journal should be emitted by a single small controller observer API, not handwritten at every call site. Event publication is best-effort and self-diagnosing: an observation write failure should be captured as a diagnostic when possible, but must not convert an otherwise successful commit into failure. Execution artifacts and the terminal result remain safety-critical authorities.

### Live output files

Extend `bounded_subprocess` with an optional byte-chunk observer used by command, provider, and stitch executors. Preserve all existing caps, timeout, process-group termination, and returned buffers. The reader threads append each stream to a distinct `*.stdout.live` or `*.stderr.live` file opened before spawn; on completion the writer closes and atomically promotes it to the existing canonical name.

Important constraints:

- Keep stdout and stderr separate. Concurrent reader threads cannot promise exact cross-stream ordering, so the UI must not fabricate it.
- Record truncation explicitly when the existing 1 MiB stream cap is reached.
- Normalize invalid UTF-8 and strip ANSI/OSC/control sequences before Rich rendering. Never allow subprocess output to create hyperlinks, markup, or terminal control effects.
- Provider stdout is the JSON protocol transport. By default show the provider's structured message/diagnostics and treat raw protocol output as developer detail. If providers need true logs, add an advertised log-stream/output-reference capability instead of heuristically parsing protocol stdout.
- Never include provider configuration or environment values in the presentation projection.

The tail cache should key by path plus inode/size and read only appended bytes. Promotion from `.live` to the canonical path is an explicit source transition, not a request to reread unrelated artifacts.

### Complete terminal projection

Evolve the terminal result schema so it includes every selected instance, even after an early failure. Add a disposition such as `not_run` with a reason (`blocked_by`, controller error, or no trigger), plus:

- `started_at`, `finished_at`, and `duration_ms`;
- a short structured `summary` suitable for one UI line;
- stable output references by kind and phase;
- all attempt results, including retries across controller cycles;
- operation/substep context for the most useful failure;
- existing evidence, diagnostics, deferral, and refusal fields.

“Final output” can then be presented consistently as:

1. summary;
2. diagnostic and evidence;
3. selected output tail;
4. complete raw artifact.

This hierarchy is more useful than dumping the final 20 lines and hoping they contain the reason.

## Frontend architecture and performance

Shared reconciliation belongs in the Rust core. The plan/state/result combination is backend/domain behavior that future frontends must interpret identically. Define a versioned `FinalizerObservation` projection with controller phase, ordered instance observations, output metadata, data freshness, and explicit compatibility/integrity errors. Python should call the binding or a thin adapter; renderers should never individually reconcile files.

In ACE:

1. Add a `finalizers` lane to `DetailHeaderSummary` and the metadata context-lane union.
2. Load it through the existing off-thread header worker. Immediately paint a cached observation, then publish the refreshed lane only if agent selection/generation still matches.
3. Cache plan/state/result by mtime signature. Do no filesystem work in render, key handlers, or the `j`/`k` immediate-header path.
4. Add the top-level state and result filenames to exact artifact refresh classification. State transitions can dirty the selected detail lane; they do not require a full agent-list rebuild.
5. While—and only while—the selected agent has a visible expanded live tail, run a lightweight roughly one-second tail revalidation. Stop it on collapse, selection change, tab loss, terminal result, or application inactivity. No periodic tick should read file contents; it only schedules bounded off-thread work when the signature changed.
6. Keep the existing 150 ms detail debounce and stale-generation rejection. A late tail read from agent A must never render after the user selects agent B.
7. Let `done.json` trigger the normal terminal refresh; reconcile the terminal result before rendering the completed state.

Textual explicitly distinguishes async workers from thread workers for blocking APIs and requires UI mutation from worker threads to pass through `call_from_thread` or message posting ([Textual workers](https://textual.textualize.io/guide/workers/)). The existing Agents-tab architecture already follows this pattern and should remain the only route for artifact reads.

The agent list needs at most a tiny phase suffix/badge for the selected or finalizing row. Do not animate every row or include changing log counts in the list. A single subtle active glyph at a one-second cadence is sufficient; semantic transition events should do most of the work.

## Reliability and degraded states

The UI should make incomplete telemetry legible instead of optimistic:

- **Plan authentication/digest mismatch:** show `unavailable · plan integrity check failed`; do not display unauthenticated config as fact.
- **Unknown schema:** show `unsupported finalizer record vN`; preserve access to raw artifacts.
- **Truncated event journal:** use the last complete event and snapshot, flag the timeline as incomplete.
- **Runner died mid-finalizer:** mark the active instance `interrupted`; later instances become `not run`. Preserve the partial log.
- **Snapshot write failed:** continue using the last good snapshot and show its age. The terminal result supersedes it if present.
- **Terminal result omitted an instance:** the core projection may show `unknown/not reported` for compatibility, but the new writer should explicitly materialize every selected instance.
- **Controller revisits commit:** represent another attempt/cycle; do not overwrite the earlier success or make total duration appear continuous.
- **Long silence:** derive elapsed time from start and display the current operation. Do not call it “stuck” merely because no output arrived; many valid subprocesses are quiet.
- **Artifact reaping/archive:** once raw output is unavailable, keep the terminal structured summary and say `log expired` rather than presenting a broken action.

All update files should use the repository's existing atomic-write and lock conventions. Append-only records should have one writer and a monotonic sequence. Parsing should be bounded by file size/record count, and path references must be confined to the agent artifact root.

## Accessibility and visual polish

The beauty of this feature should come from hierarchy and restraint:

- align instance labels and state columns when width allows, but switch to wrapped two-line rows rather than horizontal clipping on narrow terminals;
- use the existing ACE color language and dim provenance/details;
- pair every color with a stable glyph and word;
- reserve motion for the single active row;
- keep time precision human-scaled (`8s`, `2m 14s`; decimals only below ten seconds when useful);
- truncate long IDs in the middle only when the full value is available through a hint/copy action;
- never flash, auto-open, steal focus, or move the document because a log line arrived;
- auto-promote a newly failed section only if there is no persisted user fold override.

The result should feel like a compact build-status card embedded in the agent record, not like another dashboard bolted onto the TUI.

## Security and privacy

Finalizer output can contain source, paths, tokens accidentally echoed by a command, or third-party provider material. Although current artifacts already retain stdout/stderr, making them visible increases accidental exposure risk.

The implementation should:

- show no raw output in the collapsed/default view;
- sanitize all terminal control and Rich markup;
- avoid copying tails into application logs, telemetry, notifications, or the shared projection;
- fetch remote raw content only through an explicit bounded action;
- display structured summaries authored by trusted built-ins/providers, while still escaping them as text;
- preserve existing artifact permissions and retention rather than creating a second global log cache.

## Implementation sequence

### Phase 1: terminal read-only value

- Add the core projection for sealed plan plus terminal result.
- Render the foldable section with selected, passed, failed, deferred, refusal, attempts, evidence, and existing output-artifact actions.
- Explicitly label pre-controller instances `selected`, not `running`.
- Add visual and projection fixtures before introducing live mutation.

This phase answers two of the three user questions from authoritative existing data and establishes the information architecture.

### Phase 2: runtime lifecycle

- Add the observer API, atomic state snapshot, and append-only transition journal.
- Instrument controller, provider operations, command attempts, commit repository/substeps, retries, and terminal reconciliation.
- Surface `FINALIZING · <instance>` in the selected agent row/header without changing lifecycle query semantics.
- Add exact refresh markers and selected-lane invalidation.

### Phase 3: live output

- Add the bounded subprocess chunk observer and `.live` promotion.
- Implement append-only tail reads, output sanitization, follow/pause/new-line behavior, and full-log actions.
- Advertise structured provider logging rather than treating protocol stdout as a terminal.

### Phase 4: breadth and polish

- Add family aggregation, pinned-attempt behavior, bounded remote projection/log retrieval, archive/retention handling, and final visual tuning.
- Consider a dedicated finalizer timeline mode only after actual usage shows that the expanded metadata view is insufficient.

## Verification strategy

The feature crosses controller correctness, persistence, asynchronous loading, and visual behavior. It needs tests at each boundary.

**Core projection fixtures**

- selected but not started;
- dependency ordering and required/default/explicit provenance;
- running operation and repository substep;
- retry with remaining and exhausted budget;
- commit reactivation across fixed-point cycles;
- success, failure, refusal, and deferral;
- early failure with later instances explicitly not run;
- plan-digest mismatch, unknown schema, corrupt snapshot, and truncated journal;
- runner death with no terminal result;
- terminal result overriding stale running state.

**Writer/executor tests**

- atomic snapshot replacement and monotonically sequenced events;
- partial-line crash recovery;
- slow subprocess emitting alternating chunks;
- stream cap, timeout, cancellation, and process-group behavior unchanged by the tee;
- live-to-canonical promotion on success and failure;
- separate stdout/stderr and explicit truncation;
- provider protocol output never rendered as an implicit human log;
- observer I/O failure cannot change a finalizer verdict.

**TUI behavior and snapshots**

- widths around 120, 80, and 60 columns and short terminal heights;
- collapsed, normal, full, running, retrying, terminal-success, and terminal-failure views;
- long instance/provider IDs and long diagnostics;
- family aggregation and attempt-pinned history;
- scrolling pauses follow and increments `new lines`; returning to bottom resumes;
- output never changes focus, fold override, or scroll position;
- selection generation prevents cross-agent stale data;
- no full agent-list refresh for log chunks;
- terminal transition is picked up through state/result/done markers;
- light/dark themes and no-color legibility.

**Performance budgets**

- `j`/`k` navigation performs no artifact I/O and remains within the existing p95 target;
- inactive/hidden/collapsed views generate no tail reads;
- a live selected tail reads only appended bytes;
- opening Agents remains independent of total archived-run count;
- a burst of log chunks coalesces into bounded refresh work rather than an unbounded message queue.

An end-to-end fake finalizer should emit lines slowly, retry once, then either pass or fail; another case should kill the runner mid-attempt. These expose the race conditions that static terminal fixtures cannot.

## Open decisions

Three choices should be made explicitly during design review:

1. **Controls:** keep the first release observational. Cancel/retry actions have authorization and fixed-point semantics that are outside this request; do not smuggle them into a display feature.
2. **Provider summary contract:** add an optional, bounded presentation summary and explicit log capability. Preserve provider diagnostics as structured data and never infer a summary from arbitrary stdout.
3. **Journal retention:** retain lifecycle records with the normal run artifact. If future storage measurements show pressure, compact the terminal journal into the terminal result while preserving raw attempt artifacts under the existing horizon.

## Sources and repository evidence

External interaction precedents and framework guidance:

- [GitHub Actions: workflow run logs](https://docs.github.com/en/actions/how-tos/monitor-workflows/use-workflow-run-logs) — failed-step expansion, search behavior, line links, and downloadable full logs.
- [GitHub CLI `gh run view`](https://cli.github.com/manual/gh_run_view) — summary, step detail, failed-only output, attempt selection, and full-log layers.
- [Grafana Logs integration](https://grafana.com/docs/grafana/latest/visualizations/explore/logs-integration/) — live tail, scroll-to-pause, and explicit resume behavior.
- [Textual workers](https://textual.textualize.io/guide/workers/) — lifecycle-bound workers, thread workers for blocking work, and thread-safe UI handoff.
- [Textual `Log`](https://textual.textualize.io/widgets/log/) and [Textual `RichLog`](https://textual.textualize.io/widgets/rich_log/) — bounded real-time append and auto-scroll primitives.
- [OpenTelemetry Trace API](https://opentelemetry.io/docs/specs/otel/trace/api/) — separation of start/end/status from ordered events.

Primary repository evidence reviewed:

- finalizer configuration and lifecycle: `docs/configuration.md`;
- sealed selection: `src/sase/finalizers/plan.py`;
- controller/fixed-point execution: `src/sase/finalizers/controller.py`, `controller_context.py`, `controller_results.py`, and `ledger.py`;
- subprocess/output paths: `bounded_subprocess.py`, `executor_command.py`, `executor_plugin.py`, `executor_protocol.py`, `commit_dispatch.py`, and `commit_repair.py`;
- terminal reporting: `src/sase/axe/runner_reporting.py`, `run_agent_exec_finalize.py`, and `run_agent_runner_finalize.py`;
- selected-agent UI and async caching: `src/sase/ace/tui/widgets/agent_detail.py` and the `prompt_panel/_agent_display_*` modules;
- live refresh classification: `src/sase/ace/tui/actions/event_refresh/` and `actions/agents/_live_watch_coverage.py`;
- artifact tailing and retention: `src/sase/agent/artifact_files_cache.py` and `src/sase/core/managed_tmp_reaper.py`.

## Recommended solution

Build a foldable **FINALIZERS** metadata section whose default state is a calm ordered status card and whose expanded state reveals structured progress plus a bounded, user-controlled tail. Show it from the moment the sealed plan exists, call the instances “selected for this run,” distinguish the agent's `FINALIZING` display phase from model generation, auto-highlight failures without overriding user state, and keep complete output behind one explicit action.

Before claiming live support, add the missing runtime contract: an atomic `finalizer_state.json`, an append-only transition journal, bounded live stream artifacts, and a complete terminal result for every selected instance. Reconcile them in a shared Rust `FinalizerObservation` projection with strict source precedence and degraded-state semantics; keep Python/TUI code to asynchronous loading, caching, refresh routing, and presentation. Refresh semantic transitions through exact artifact markers, tail only the visible selected instance, pause follow on scroll, and never perform artifact I/O in the render or navigation path.

Ship this in three user-visible increments—terminal summary, live lifecycle, then live output—while designing the schema for families and remote observers from the start. This produces the most intuitive surface now, preserves the controller's reliability guarantees, avoids overwhelming the TUI, and gives every future frontend one trustworthy answer to what was selected, what is happening, and what ultimately happened.
