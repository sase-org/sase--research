# `sase tool` as the control plane for expensive project commands

**Researcher:** A  
**Date:** 2026-09-14  
**Scope:** Independent review of the `sase-zm` epic and SASE's existing tool-call UI,
plus external research on command history, workload UX, observability, and runtime
prediction.

## Executive conclusion

The most valuable version of `sase tool` is not primarily a command wrapper. It is a
small, project-extensible control plane for expensive command executions. Wrapping a
command once should create one durable **tool run** with an identity, owner, lifecycle,
capacity reservation, live output, result, history, and forecast. The CLI, ACE, agents,
monitors, and future integrations should all be views over that same Rust-owned record.

This framing unlocks more than the current `run`/`status` proposal:

1. A searchable history of expensive work, including queue time, execution time,
   outcome, machine, profile version, and source-tree identity.
2. Useful, honest forecasts: estimated queue start and a range for remaining runtime,
   with sample size and confidence—not a falsely precise end timestamp.
3. Explanations for *why* something is waiting or slow, separating queue delay,
   setup/build work, child execution, finalization, and contention.
4. Performance-regression and flakiness detection by project/profile/stage/machine.
5. Durable verification receipts that agents, beads, Patches, and final responses can
   cite instead of saying only “tests passed.”
6. Safe single-flight joining or reuse of equivalent verification work when a profile
   can prove semantic equivalence.
7. Evidence-driven capacity prices, worker limits, and timeout suggestions.
8. Better agent decisions: run inline, hand off to a monitor, queue, or reuse an
   existing result based on predicted queue-plus-execution time.

I recommend retaining the exact-argv `sase tool run -- ...` entry point, but designing
the durable run model before implementing the UI. Add `plan`, `list`, `show`, `watch`,
`logs`, `cancel`, `retry`, `stats`, and `profile list/show`; make `status` the fleet's
live capacity/queue view. In ACE, create a top-level **Tools** tab for managed tool runs
and rename the existing per-agent **Tools** panel to **LLM Calls**. Link the provider
call to the managed run rather than rendering the same execution as two unrelated
things.

## What the current design already gets right

The current `sase-zm` plan (`plan:202609/command_capacity.md`) contains several strong
foundations worth preserving in the redesign:

- exact argv after a mandatory `--`, with no implicit shell;
- project-defined, versioned profiles instead of executable-name guessing;
- Rust ownership of policy, identity, numeric aggregation, and serializable
  projections;
- explicit capacity demand and fair admission, including the distinction between an
  inline agent's base weight and a monitor's standalone demand;
- atomic handoff to a monitor before releasing the provider's claim;
- structured outcomes that distinguish admission failure from a child exit with the
  same numeric code;
- durable supervision, process-tree-aware release, and no age-only lease expiry;
- a dry-run explanation of profile, setup, test selection, workers, demand, and
  predicted duration;
- prominent per-machine capacity/load display; and
- keeping queue cancellation and monitor continuation semantics tied to the existing
  monitor subsystem.

The epic's current `tool run/status` phase is therefore a good execution kernel. The
redesign opportunity is to treat its records as a first-class product surface rather
than an implementation detail of capacity admission.

### A terminology collision to resolve early

ACE already has a per-agent **Tools** panel. Its `tool_calls.jsonl` contains
provider-level calls such as reads, edits, Bash invocations, web fetches, and subagent
launches. The slow-call lane surfaces calls over a configurable threshold (currently 20
seconds). This data is best-effort, Python/TUI-owned glue and may have only bounded
summaries.

A managed `sase tool run -- just check-full` is a different object. The provider may
record the outer Bash call, but the managed command additionally has admission,
queueing, supervision, exact lifecycle transitions, capacity, stages, output ownership,
and a typed result. Standalone and monitor-origin runs may not have a provider tool call
at all.

The product vocabulary should therefore be:

- **LLM call**: one provider tool invocation from `tool_calls.jsonl`;
- **tool run**: one SASE-managed expensive command execution; and
- **attempt**: one execution attempt within a stable logical tool run, used by retry or
  resume.

The two can link to each other, but the provider log must not become the authoritative
tool-run store. Otherwise the CLI and non-agent callers inherit incomplete,
runtime-specific data and ACE double-counts the same work.

## Lessons from adjacent systems

No single comparison supplies the desired UX, but several mature systems demonstrate
the pieces.

### Runs should be structured events, not parsed terminal prose

Bazel's Build Event Protocol exists so IDEs and dashboards can consume build progress,
configuration, tests, artifacts, and results without parsing console output. Its event
graph also represents aborted or incomplete work explicitly. This is a close precedent
for project profiles emitting structured stage/progress events while preserving child
stdout and stderr for humans. [Bazel Build Event Protocol](https://bazel.build/remote/bep)

OpenTelemetry's stable tracing model describes one operation as a span with a stable
context, start/end timestamps, attributes, timestamped events, links, and status; child
spans represent meaningful sub-operations. It also recommends a general, statistically
useful operation name rather than a high-cardinality instance string. `ToolRun` need
not export OpenTelemetry on day one, but this is the right conceptual schema: a
low-cardinality profile is the operation name, the run ID is identity, stages are child
spans/events, and output is a linked log stream. [OpenTelemetry tracing
API](https://opentelemetry.io/docs/specs/otel/trace/api/)

### A compact live line and a detailed run object serve different needs

Ninja exposes counts, percent complete, elapsed time, current rate, and ETA through its
configurable `NINJA_STATUS` line. Its default stays deliberately compact. This argues
for a single updating stderr status line for foreground `sase tool run`, while detailed
history and output belong in `show`, `watch`, `logs`, and ACE. It also shows why stage
or unit progress is materially better than elapsed time alone when a tool can supply
it. [Ninja manual, `NINJA_STATUS`](https://ninja-build.org/manual.html#_environment_variables)

GitHub CLI's workflow-run group uses the unsurprising verbs `list`, `view`, `watch`,
`rerun`, and `cancel`; `view` can show all or only failed logs, and `watch` can return a
failing exit status. That division is more discoverable than a single overloaded
`status` command. `sase tool` should follow the same broad grammar while using SASE's
own `show`, `retry`, and `logs` conventions. [GitHub CLI `gh run`](https://cli.github.com/manual/gh_run),
[view](https://cli.github.com/manual/gh_run_view),
[watch](https://cli.github.com/manual/gh_run_watch)

### Queue-time estimates and execution-time estimates are different promises

Slurm's `squeue --start` reports expected start time and resources for pending jobs,
and its normal queue output includes a reason for waiting. The estimate is conditional
on a scheduler configuration that can actually calculate it. This is the correct UX
analogy: SASE should display **start estimate** for queued work and **finish estimate**
for running work separately, with “capacity,” “priority,” “dependency,” or “stale
profile” as an explicit wait reason. It should not combine both into one magic clock
without showing the components. [Slurm `squeue`](https://slurm.schedmd.com/squeue.html)

### Searchable context and privacy are both product features

Atuin makes command history useful by recording directory, duration, exit code,
machine, user, and session, then letting users filter by time, cwd, and exit. It also
documents command/cwd exclusion filters and applies secret patterns to captured output,
while warning that redaction is only a safety net. SASE has richer project and agent
identity available and should use it, but it needs similarly explicit opt-out and
redaction controls before accumulating command/output history. [Atuin search
reference](https://docs.atuin.sh/main/reference/search/), [Atuin configuration and
secret filtering](https://docs.atuin.sh/main/configuration/config/#secrets_filter)

### History becomes more valuable when it separates phases and distributions

Nextflow separates submission delay, real execution, and termination overhead in its
timeline and records task status, command, duration, CPU, memory, and I/O in its trace.
It warns that resource measurements are estimates and may be unavailable on some
platforms. This supports both a stage waterfall and a careful distinction between
SASE's reservation load and observed machine/process metrics. [Nextflow
reports](https://docs.seqera.io/nextflow/reports)

GitLab's CI analytics emphasizes median and 95th-percentile duration plus failure rate,
not only average duration. Those are useful first statistics for `sase tool stats` and
regression detection. [GitLab CI/CD
analytics](https://docs.gitlab.com/user/analytics/ci_cd_analytics/)

## Highest-value use cases

### 1. One answer to “what is consuming the machine?”

The live fleet view should join agents, monitors, and managed tool runs through their
authoritative reservation identities. A user should be able to see that athena is at
`23/32`, then drill into the holders and learn that 15 units belong to a `check-full`
run, 4 belong to agent baselines, and 4 belong to other commands. A queued row should
show demand, queue rank/age, protected status, and the exact reason it cannot start.

This turns the current capacity badge from a passive meter into a trustworthy
explanation surface. It is likely the first use case that repays the wrapper's cost.

### 2. Durable, searchable command history

Users and agents should be able to answer:

- When did `check-full` last pass on this source tree?
- Which machine ran it, with how many workers and which profile version?
- How much time was queueing versus execution?
- Which attempts failed, timed out, were canceled, or never started?
- What did the failed stage print?
- Did this invocation run inside an agent, a monitor, or standalone?

The default list should be project-scoped and recent, not a firehose across every
machine and project. Filters should cover state, profile, machine, agent/family,
origin, outcome, revision/fingerprint, time range, and minimum duration. JSON should
expose the same filters for agents and scripts.

### 3. ETA and expected start, with calibrated uncertainty

Yes, SASE can predict end time once enough comparable history exists. The word
“comparable” matters more than sheer sample count. A `check-full` on a warm athena
checkout with no Rust rebuild is not drawn from the same runtime distribution as one
that must compile `sase-core`; a 16-worker test selection is not comparable to a
4-worker run on `kellys_mbp`.

The forecast should decompose:

```text
queue start    ~2–5m       capacity + older protected request
run remaining  6–11m      80% interval, n=37 similar completed runs
likely finish  15:42–15:50 EDT
confidence     medium      warm/cold cache state is still unknown
```

The range is the product. A single `15:46` timestamp invites users and agents to treat
noise as certainty.

### 4. Performance regression and “why slow?” analysis

Once stages and context are recorded, SASE can compare a run with a suitable baseline:

- current p50/p95 versus the preceding profile version or time window;
- queue time versus execution time;
- setup/build/test/finalization stage deltas;
- machine and worker-count cohorts;
- cold versus warm caches;
- selected test count or input-size proxies; and
- failure/timeout/cancellation rate.

The UI can flag “1.8× slower than 20 comparable runs” and point to the stage that grew.
It should avoid causal language unless SASE has evidence; “correlated with high I/O
load” is defensible, while “caused by another agent” usually is not.

### 5. Verification receipts and provenance

Every terminal tool run should be addressable as an artifact-like identity such as
`tool:<run-id>`. A receipt can state:

- the recognized profile and version;
- exact source-tree/repository fingerprint and relevant dirty-state digest;
- selected stages/tests and their reasons;
- machine, worker allowance, capacity grant, and timestamps;
- child exit/signal and typed outcome;
- output/log artifact references and checksums; and
- invoker agent/monitor, bead, Patch, and stitch links when known.

This lets a final response cite a durable result and lets a later agent decide whether
that result applies to its current tree. It also makes “verified” auditable without
forcing full logs into every prompt. To avoid page explosion, treat tool runs as
resolvable virtual artifacts and materialize an artifact Markdown page only when a run
acquires a durable link.

### 6. Single-flight joining and safe result reuse

Two agents frequently request the same expensive verification on the same tree. A
managed profile can define a semantic fingerprint, allowing SASE to:

- **join** an identical run already queued or running, delivering its result to
  multiple interested callers without executing twice; or
- **reuse** a sufficiently recent successful receipt for the same semantic input.

This may save more capacity than better scheduling. It must be opt-in per profile.
Generic commands, mutation-producing commands, secret-dependent checks, or profiles
without complete fingerprints are never reusable. Joining needs multi-consumer result
delivery and must not let one consumer's cancellation kill work still required by
another.

### 7. Evidence-driven profiles and capacity prices

The original epic uses authored demand values, appropriately treating them as policy
rather than claims about physical cores. History can later show whether those values
produce good outcomes:

- Does increasing admitted workers reduce wall time or only raise contention?
- Which profiles' runtime rises sharply as concurrent reserved load rises?
- Are particular commands CPU-, I/O-, memory-, or setup-bound?
- Is a capacity price systematically conservative or associated with overload?
- Which timeout defaults sit below the observed tail?

The system should initially **recommend** profile/weight/worker changes. It should not
silently rewrite capacity policy from noisy observations.

### 8. Agent planning and handoff decisions

Machine-readable `plan` output lets an agent compare the cost of inline execution,
queue handoff, and a valid existing receipt before consuming provider time. It can also
budget a turn around “likely 4–7 minutes” rather than discovering the cost after spawn.
When queued work completes, the continuation can carry a compact typed result and the
tool-run reference rather than copying logs or asking the successor to rerun it.

### 9. Failure, flake, and infrastructure triage

Typed outcomes and stage identity allow useful groupings that raw exit codes cannot:

- admission refused / impossible demand;
- setup or spawn failure;
- command failure;
- test failure;
- timeout;
- explicit cancellation;
- supervisor interruption or reboot recovery; and
- output/telemetry collection degradation.

Repeated failure signatures can reveal likely flakes or shared infrastructure
incidents. This should begin as clustering and links to similar runs, not automatic task
creation or automatic “flake” declarations.

### 10. Critical-path and workflow optimization

For multi-stage checks, a waterfall exposes serial gaps, queue delays, overlong setup,
and underutilized parallel stages. Over time SASE can answer which profiles dominate
agent elapsed time and which changes would improve the developer loop most. This is a
better optimization target than “most frequently executed command” alone.

### 11. Notifications and attention routing

A durable run can publish completion once and let CLI, TUI, monitor continuation, or a
notification integration subscribe. Useful policies include “notify on terminal
failure,” “notify when queue wait exceeds p95,” and “notify when an ETA moves materially
later.” This avoids every wrapper inventing its own notification path.

### 12. Cross-machine advice, later

Once fleet snapshots and per-machine cohorts are trustworthy, preflight can say “athena
starts later but likely finishes sooner; apollo is free but this profile has low-confidence
history there.” That is valuable even without remote dispatch. Automatic migration or
execution on a different machine should remain a later, explicit feature because it
changes workspace, cache, trust, and output-location assumptions.

## ETA design: what is feasible and what would be misleading

### Separate three clocks

For every run, model these independently:

1. **Queue time:** request to admission. This depends on current holders, older queued
   work, fairness/protection, requested demand, and the remaining-time distributions of
   running holders.
2. **Execution time:** child start through process-tree exit. This depends mainly on
   profile/stages, machine, workers, cache/setup state, inputs, and contention.
3. **End-to-end time:** request through durable finalization/result delivery.

Queue forecasting compounds uncertainty from several running jobs, so its interval
will often be wider. Slurm only offers expected start when the configured scheduler can
derive it; SASE should likewise show `unknown` instead of fabricating a value when a
holder lacks a usable remaining-time distribution.

### Start with empirical cohorts, not machine learning

An effective first estimator is hierarchical and transparent:

1. Match completed, non-censored attempts on exact project, profile version, machine,
   stage plan, worker bucket, and known cache/setup class.
2. If the cohort is too small, progressively back off: compatible profile versions,
   nearby worker/load buckets, same machine class, then project-wide profile history.
3. Return p50 and a wider interval such as p10–p90, plus sample count, recency, and the
   fallback level used.
4. Weight recent samples more heavily and invalidate or down-rank history after known
   toolchain/profile discontinuities.

Prometheus's histogram guidance reinforces storing distributions from which different
quantiles can be computed and aggregated rather than only precomputed averages. SASE
should retain raw summary rows or mergeable histograms, not merely `mean_duration`.
[Prometheus histograms and
summaries](https://prometheus.io/docs/practices/histograms/)

Only after this baseline is measured should SASE consider quantile regression or
another conditional model. Recent HPC research finds long-tailed runtime distributions
and shows why point estimates optimized for mean error systematically hide uncertainty;
multi-quantile models provide a median and conservative bound that vary with job
features. The environment is different, but the design lesson is directly applicable:
show prediction intervals and job-specific confidence. [Choi and Oh, “UARP:
uncertainty-aware runtime prediction,” 2026](https://doi.org/10.1007/s11227-026-08422-8)

### Remaining time is conditional on survival so far

For a running command, do not calculate `historical median total - elapsed`. If the
command has already outlived many samples, those short samples are no longer possible.
Estimate the residual distribution conditional on total duration exceeding the current
elapsed time:

```text
P(remaining <= r | total > elapsed, cohort and live stage)
```

Stage transitions tighten the cohort. If `check-full` has finished setup and Rust build
and is now 40% through a structured test selection, estimates from comparable test-stage
progress are much better than estimates from command age alone. Generic commands with
no structured progress should show only time-conditioned historical ranges, never a
made-up percentage.

Timeouts, cancellations, supervisor loss, and still-running observations are
right-censored: SASE knows only that execution lasted at least some duration. Do not
treat them as completed at the censor time or discard them from every analysis. A later
survival-style estimator can use them without claiming a known finish time. The first
empirical implementation may exclude them from completion quantiles but should still
report censor/failure rates beside the estimate.

### “Machine load” needs two distinct fields

The `sase-zm` plan correctly defines capacity load as **reserved demand**, not CPU
utilization or physical cores. Reserved load is essential to queue prediction and a
useful contention proxy, but it is not enough to explain runtime. Prediction features
should distinguish:

- `reserved_load_at_request` and `reserved_load_at_start`;
- executing managed-demand composition by profile;
- configured/granted worker count;
- optional observed process-tree CPU time, peak RSS, I/O, and machine CPU/I/O/memory
  pressure summaries; and
- cache/setup/stage state.

Observed metrics should be labeled estimates and optional by platform, as Nextflow
does. A small sample of load at start plus bounded per-stage summaries is likely enough;
high-frequency telemetry is unnecessary for the initial UX.

### Prediction UX and quality gates

Every displayed forecast should carry:

- p50 remaining and an 80% or 90% interval;
- confidence (`high`, `medium`, `low`, or `insufficient data`);
- comparable sample count and history window;
- the top cohort/fallback facts;
- prediction creation/update time and model version; and
- queue and execution components.

Use progressive disclosure: list rows show `~6–11m · med`; `show` explains `n=37,
athena, profile v3, warm cache, load 9–16`; JSON exposes exact quantiles and features.

Before influencing admission or automatic placement, backtest chronologically and
measure interval coverage, absolute error, underprediction rate, and accuracy by
profile/machine/load cohort. Do not optimize only mean absolute error. A model whose
advertised 80% interval contains only 50% of outcomes should be degraded or hidden.

## Recommended CLI information architecture

### Core commands

```text
sase tool plan     Explain recognition, stages, capacity, reuse, and forecast; run nothing
sase tool run      Execute or explicitly queue a command
sase tool status   Show current fleet capacity, holders, and queue
sase tool list     List recent/current managed runs (`ls` alias)
sase tool show     Show one run/attempt, lifecycle, result, forecast, and links
sase tool watch    Refresh one run until terminal; optionally mirror its output
sase tool logs     Print/follow stdout and stderr from the authoritative capture
sase tool cancel   Cancel one queued/running run through its supervisor
sase tool retry    Create a new attempt linked to a terminal/refused run
sase tool stats    Summarize duration, queueing, outcomes, regressions, and utilization
sase tool profile  `list` and `show` the effective project profile catalog
```

`status` answers “what is happening now?”; `list` answers “what ran?”; `show` answers
“what happened to this run?”; `logs` answers “what did it print?” This separation is
worth the extra subcommands.

### Invocation examples

```sh
# Read-only preflight. Canonical replacement for an overloaded run --dry-run.
sase tool plan -- just check-full
sase tool plan -j -- just check-full

# Foreground: preserve child stdout/stderr and child exit status.
sase tool run -- just check

# Explicitly queue/handoff, or explicitly override only capacity admission.
sase tool run -q -- just check-full
sase tool run -f -- just check-full

# Unknown commands require authored demand; a shell is never inferred.
sase tool run -w 2.5 -- expensive-command --its-own-option
sase tool run -w 2.5 -- sh -c 'explicitly authored shell text'

# Live fleet and queue.
sase tool status
sase tool status -w

# History and drill-down.
sase tool ls --profile check-full --since 7d --outcome failed
sase tool show 4FX
sase tool watch 4FX --exit-status
sase tool logs 4FX -f
sase tool logs 4FX --failed
sase tool retry 4FX -q
sase tool cancel 4FX

# Performance/history.
sase tool stats check-full --since 30d --group-by machine
sase tool profile show check-full --machine athena
```

I prefer `plan` over making `run -n` the primary preflight because it describes the
operation's semantics and can later show reuse or placement options without pretending
to be an execution attempt. A compatibility `run --dry-run` alias would be harmless if
already shipped, but should not be the documented form in a redesign.

### Defaults and interaction rules

- Require `--` before child argv. All SASE options precede it; all child options follow
  it byte-for-byte as argv elements.
- Foreground `run` streams child stdout/stderr unchanged. SASE lifecycle/progress text
  goes to stderr and collapses to one line on a TTY.
- Do not offer normal foreground `run --json`; it corrupts the child's data plane.
  `plan`, `status`, `list`, `show`, `stats`, and detached/queued submission may expose
  versioned `--json`.
- `run` attempts admission once by default. It must not silently hand off an agent or
  silently force capacity. A refusal prints the executable `-q` and `-f` choices with a
  stable request ID, as the current plan proposes.
- `-q/--queue` and `-f/--force` stay mutually exclusive. `--force` bypasses admission
  only, never profile validation, ownership, supervision, or nested-run checks.
- `show`, `watch`, and `logs` without an ID select the sole active run owned by the
  current shell/agent in the current project. If ambiguous, a TTY offers a compact
  picker; noninteractive use errors and lists candidate IDs.
- The stable **run ID** survives refusal/resume and groups attempts; retry creates a new
  attempt ID. `show` defaults to the latest attempt and displays the attempt chain.
- `cancel` is a discoverable facade over the existing monitor/supervisor stop protocol,
  not a second cancellation implementation.
- Queue and execution timeouts remain separate and are visible in `plan` and `show`.
- Common filters should be shared across `list` and `stats`: `--project`, `--profile`,
  `--machine`, `--agent`, `--state`, `--outcome`, `--since`, `--until`, and `--limit`.
  Avoid inventing short flags for every advanced filter when the short namespace would
  become inconsistent.

### Example human output

```text
$ sase tool status
MACHINE       LOAD       RUNNING  QUEUED  OLDEST WAIT
athena        23/32           3       2   1m48s capacity
apollo         5/8            1       0   —
kellys_mbp     0/4            0       0   —

ID    STATE    PROFILE      OWNER        MACHINE  CAP   AGE/RUN   START/REMAINING
4FX   running  check-full   sase-zm.6    athena   15    7m12s     4–9m · med
4FY   queued   rust-build   kase.1       athena    8    1m48s     start ~3–8m · low
```

```text
$ sase tool show 4FX
4FX · check-full · RUNNING (attempt 1)
Owner       sase-zm.6 → monitor sase-zm--mon
Input       sase @ 8c0e… + dirty fingerprint 3e19…
Machine     athena · workers 16 · capacity 15 · start load 8/32
Timing      queued 0s · running 7m12s · likely 4–9m remaining (80%)
Forecast    medium · 37 comparable runs · profile v3/warm · updated 14s ago
Stage       tests 612/1043 · setup 8s ✓ · rust build 2m31s ✓
Outcome     pending
Output      tool-output:4FX/1 (redacted; 2.8 MiB)
Links       agent:sase-zm.6 · bead:sase-zm.6 · patch:...
```

## Recommended ACE/TUI UX

### 1. Add a top-level Tools tab

Managed tool runs need a fleet/project surface because standalone and queued monitor
runs cannot always be reached through an agent. The tab should use a responsive
list/detail layout:

- list columns: state, short ID, profile/label, owner, project, machine, demand, queue
  age or run elapsed, start/remaining range, and confidence;
- default filter: active plus recently terminal runs for the current project;
- quick filters: active/history, project, machine, profile, outcome, owner;
- stable textual state labels and symbols so color is never the only signal; and
- background refresh only while active rows exist or fleet change tokens fire.

Selecting a row shows:

1. lifecycle and attempt chain;
2. queue/admission explanation and reservation ownership;
3. a stage waterfall with queue, setup, execution stages, and finalization;
4. forecast range, confidence, cohort, and last update;
5. a lazily loaded tail of stdout/stderr with a jump to full logs;
6. source/profile/fingerprint and exact typed outcome; and
7. links to agent/family, monitor, project, bead, Patch/stitch, and receipt.

Actions should include follow output, cancel (through a normal confirmation gate),
retry, copy run ID/ref, jump to owner agent, and toggle similar-run statistics.

### 2. Rename the current Agents-tab Tools panel to LLM Calls

The existing panel remains valuable for reads, edits, web fetches, provider Bash calls,
and subagents. Calling it **LLM Calls** makes the boundary clear. When a provider call
launches a managed tool run, its row should show `→ tool:4FX` and inherit the managed
run's state/result summary. Expanding it can jump to the top-level Tools tab. Do not
render the managed child's full lifecycle as an unrelated second provider call.

### 3. Add compact tool-run context to agent rows/details

An active agent row can carry at most one small chip for its current managed run:

```text
▶ check-full 7m · 4–9m
⌛ check-full q2 · start ~3–8m
```

The agent detail should have a **TOOL RUNS** section listing current and recent linked
runs. Slow generic LLM calls remain in the existing slow-call lane; managed runs use
their richer source even if their elapsed time is below the slow-call threshold.

### 4. Make the fleet meters drillable

The planned per-machine badges/meters remain in the Agents header. Selecting a badge
filters the Tools tab to that machine and shows capacity source/freshness, holders,
queued demand, overload/uncertainty, and predicted releases. The meter itself should not
attempt to encode all of this.

### 5. Use ranges, not progress theater

For structured profiles, show real units/stages and a remaining-time range. For generic
commands, show elapsed plus the conditional historical range. Never turn elapsed/median
into a fake percent-complete bar. When confidence is insufficient, `ETA — · n=2` is a
better interface than a guess.

## Durable run contract

Shared CLI/TUI behavior belongs in `sase-core`. A versioned `ToolRunProjection` should
be reconstructible from append-only lifecycle events and should reference, rather than
duplicate, supervisor logs and monitor state.

### Identity and relationship fields

- run ID, attempt ID/ordinal, schema version;
- project/repository identity and profile/profile-version identity;
- semantic command fingerprint plus redacted display argv;
- protected exact argv reference needed for execution/resume;
- cwd/repository/source revision, dirty-input fingerprint, relevant input-size facts;
- invoker kind and stable agent/family/shell/monitor owner lineage;
- optional bead, Patch, stitch, and provider-call links;
- machine, boot, process birth, supervisor, and child identities; and
- parent/child tool-run relationship for verified nested stages.

### Lifecycle and timing fields

- requested, planned, enqueued, protected, admitted, starting, started, stage events,
  process-exited, finalizing, and terminal timestamps;
- explicit states such as `refused`, `queued`, `running`, `succeeded`, `failed`,
  `timed_out`, `canceled`, `interrupted`, and `uncertain/reconciling`;
- queue, setup, execution, finalization, and total durations;
- requested/granted demand, agent baseline, capacity source, force provenance,
  priority, queue rank/age, and wait reason; and
- worker limit plus load snapshots at request/admission/start and bounded stage
  summaries.

### Result, output, and forecast fields

- child-started boolean, exit code, signal, wrapper/admission outcome, failed stage,
  and normalized failure signature;
- stdout/stderr capture references, sizes, checksums, redacted previews, truncation and
  retention state;
- emitted artifacts/test counts/cache results where profiles support them;
- forecast snapshots with p50/p90 or interval bounds, confidence, cohort/fallback,
  sample count/window, feature summary, estimator version, and created-at time; and
- result consumers so one joined run can deliver to multiple callers safely.

Store full lifecycle history; derive mutable live projections and indices for fast
querying. Keep summary records longer than full output. Output should be loaded lazily
in ACE so a large history does not become a navigation or refresh regression.

## Privacy, correctness, and scope guardrails

### Command and output secrecy

Exact argv can contain secrets even without environment capture, and clean argv can
produce secret output. Therefore:

- never store an environment dump;
- separate protected execution argv from redacted/indexed display argv;
- let profiles identify secret-bearing arguments and non-recordable outputs;
- run built-in secret detection over both command and captured output, while stating
  clearly that it is not complete;
- provide project/profile exclusion rules and an explicit `--no-history` only where it
  does not undermine required supervision/auditing;
- do not use raw argv, cwd, or output as metric labels; and
- retain checksums and typed summaries when full logs expire.

### A successful process is not necessarily reusable verification

Exit zero alone does not prove applicability to a later tree. Reuse requires a profile
contract that fingerprints every semantically relevant input and toolchain/config
version. Dirty trees, generated files, external services, time-sensitive tests, and
untracked inputs all need explicit policy. The safest initial feature is joining an
already-running identical request; reuse of a historical success should ship later.

### Avoid automatic policy feedback loops initially

Forecasts may inform people and agents before they influence admission. Capacity
prices, timeouts, worker counts, placement, and profile grouping should remain authored
until the estimator is calibrated and drift handling is proven. Otherwise a temporary
slowdown can raise prices, reduce concurrency, change the observations, and reinforce a
bad model.

### Preserve one owner for each responsibility

- Rust core: run schema/state machine, identity, profile decisions, fingerprints,
  admission/fairness, aggregation, query filters, forecast inputs/results, and JSON
  projection.
- Host adapters: process supervision, exact argv execution, process-tree metrics,
  streaming/capture, durable writes, and platform probes.
- Project profiles: recognition, safe display/redaction, stage/event adapters,
  semantic fingerprint, expected outputs, and reuse eligibility.
- CLI/TUI: presentation and actions over the core API, never independent lifecycle or
  ETA logic.

## Suggested delivery sequence

### Phase A: define the product object before the command

Define and fixture the Rust-owned run/attempt state machine, profile identity,
timestamps, typed outcomes, log references, filters, and versioned JSON. Link provider
calls and monitor ownership without merging their stores. This is the compatibility
foundation for every UI.

### Phase B: execution plus live and historical UX

Ship `profile list/show`, `plan`, `run`, `status`, `list`, `show`, `watch`, `logs`,
`cancel`, and `retry`. Add the ACE Tools tab, rename the current panel to LLM Calls,
link runs into agent detail, and make fleet badges drillable. Record stage events for
one or two important SASE profiles, but accept generic runs without fake progress.

### Phase C: descriptive analytics and baseline ETA

Ship `stats` with p50/p95, outcome rate, queue/execution split, and stage breakdown.
Add a hierarchical empirical estimator with ranges, sample counts, recency, explicit
fallbacks, conditional remaining-time updates, and chronological calibration reports.
Do not use predictions for scheduling yet.

### Phase D: receipts, joining, and recommendations

Make terminal runs resolvable as `tool:<id>` receipts. Add opt-in single-flight joins
for strongly fingerprinted profiles. Surface regression, timeout, worker, capacity, and
placement recommendations. Add historical-success reuse only after invalidation and
multi-consumer semantics are tested.

### Phase E: optional prediction-assisted scheduling

Only after measured calibration should the scheduler use forecast distributions for
queue start estimates, conservative backfill, or placement advice. Keep an authored
fallback and explain every decision.

## Recommended solution / UX

Cancel and redesign `sase-zm` around a first-class, Rust-owned **ToolRun** contract,
then preserve its sound capacity/supervision pieces as consumers of that contract. The
recommended public shape is:

```text
sase tool profile list|show
sase tool plan -- <argv...>
sase tool run [--profile P|--weight N] [--queue|--force] -- <argv...>
sase tool status [--watch]
sase tool list|ls [filters]
sase tool show [run-id]
sase tool watch [run-id] [--exit-status]
sase tool logs [run-id] [--follow|--failed]
sase tool cancel [run-id]
sase tool retry [run-id] [--queue|--force]
sase tool stats [profile] [filters/grouping]
```

The CLI should use one stable run ID across refusal/resume and separate attempt IDs for
retry; preserve child streams and exit codes; put wrapper progress on stderr; require
`--`; keep queueing and force explicit; expose versioned JSON only on control-plane
views; and make `show` explain queue reason, stages, capacity, provenance, output, and
forecast confidence.

ACE should gain a top-level **Tools** tab for all managed runs, with active/history
filters, a stage waterfall, lazy output tail, links, and actions. Rename the current
per-agent **Tools** panel to **LLM Calls** and link/collapse its outer Bash invocation to
the managed run. Agent rows get only a compact current-run chip; fleet load meters
drill into the same Tools data.

For ETA, start with transparent hierarchical p50/range cohorts keyed by project,
profile version, machine, worker/load bucket, stage plan, and cache/setup state. Show
queue-start and execution-finish ranges separately, condition remaining time on elapsed
time and stage progress, include `n` and confidence, retain censored observations, and
ship no estimate when the data is insufficient. Advance to quantile/survival models
only after chronological calibration proves the displayed intervals.

After the foundation is trusted, prioritize durable `tool:<run-id>` verification
receipts and safe single-flight joining. Those two features turn `sase tool` from a
better progress display into infrastructure that prevents duplicate expensive work and
makes verification reusable, attributable, and auditable across the entire SASE
workflow.
