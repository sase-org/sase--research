# Decomposing `sase tool` into independently valuable epics

**Independent researcher A report**  
**Date:** 2026-09-17  
**Code snapshots reviewed:** SASE `14403c1594b63deac2d9dceec2adbb6c3d7eb79a`;
`sase-core` `b4f7de3aee7ece9c9b4fa61c1776aa72f30f9de0`  
**Primary input:** `research:202609/sase_tool_control_plane/sase_tool_control_plane.md`

## Executive decision

This work is not merely large enough for multiple epics; it is too large and too
cross-cutting to be safe as one epic. The existing `sase-zm` plan demonstrates the
problem: fourteen medium phases span a Rust state machine, host supervision, monitor
handoff, CLI design, test/build adapters, initialization, fleet publication, Textual
rendering, memory/skill changes, and a three-machine rollout. It also mixes at least
four separately valuable products:

1. a durable record of what expensive commands ran;
2. a better way to execute and hand off those commands;
3. intelligence derived from the record (forecasts, reuse, failure classification);
4. capacity admission and fleet presentation.

Those products have different evidence prerequisites and different failure modes.
Recording can be useful before predictions are calibrated. Predictions can be useful
before they control execution. Receipts can save work without a queue. Admission is
safest only after real demand and duration data exist.

I recommend replacing `sase-zm` with a legend of **seven user-verifiable epics**:

1. **Named tools and the ToolRun ledger**
2. **Durable tool execution and live run UX**
3. **Forecasts and automatic inline-versus-handoff routing**
4. **Safe receipts and staged verification**
5. **Failure intelligence and structured continuations**
6. **Local tool capacity admission**
7. **Fleet capacity surfaces and coordinated rollout**

The first five are valuable even if admission is never built. Epics 6 and 7 deliberately
split `sase-zm`'s local scheduling work from its fleet wire/UI/deployment work.

The most important architecture decision is this:

> A ToolRun is a semantic execution record linked to an execution owner. It is not a
> new Proc kind, and it is not a second scheduler.

An inline foreground run may have no Proc. A detached standalone run should link to a
transient oneshot service Proc after `sase-11y` lands. An in-agent handoff should link
to the existing monitor Proc because that is what owns the workspace and continuation.
The ToolRun supplies tool identity, stage facts, fingerprints, predictions, receipts,
diagnostics, and provenance. The Proc supplies durable OS-process supervision,
stop/settlement, and bounded log ownership. One can point to the other without
duplicating either lifecycle.

## Research scope and evidence

I first read the requested consolidated control-plane report through the audited
artifact interface. I then independently inspected:

- the current SASE and `sase-core` trees at the revisions above;
- the active bead graph, especially `sase-zm`, `sase-11y`, `sase-124`,
  `sase-117`, `sase-11l`, `sase-z4`, `sase-zl`, `sase-zn`, and the fleet and
  retention epic chains;
- the active plans for command capacity and the service host;
- the current Proc wire/store, monitor-result and continuation paths, service state,
  runner-capacity policy, telemetry store, CLI parser registry, configuration layers,
  and ACE slow-tool-call panel;
- the CLI and TUI-performance project rules.

I did not inspect the other researcher in this swarm, its chat, or its `__b.md` report.

The requested report's measurements remain the best empirical reason to do this work:
slow calls dominate agent command wall time, failed/timed-out verification dominates
`check-full` wall time, agents repeat unchanged work, and agents frequently choose the
wrong inline-versus-monitor path. I treat those measurements as cited input, not as
measurements I independently reproduced in this planning-oriented investigation.

## What exists now

### Procs and monitors already own durable background execution

The current Rust Proc wire is schema version 3
(`crates/sase_core/src/procs/wire.rs`). It already carries:

- exact argv/cwd and project/workspace/session attribution;
- PID/PGID and supervisor identity;
- request fingerprints and idempotent reservation;
- pending/running/settling/terminal lifecycle;
- stop intent, timeouts, exit code, a typed result payload, and a log locator;
- an additive service block.

The Rust store atomically reserves a proc-shell, claims one supervisor, records
settlement, and publishes one terminal result
(`crates/sase_core/src/procs/store.rs`). Monitor code projects this shared Proc into
agent-family semantics rather than maintaining a separate process supervisor
(`src/sase/monitor/proc_adapter.py`).

Monitor continuations are also already a rich product. `sase-zl` is closed and its
current result wire records command, cwd, outcome, elapsed time, timeout kind, retained
log metadata, diagnostic references, workspace identity, and exact-once delivery
(`src/sase/monitor/result_projection.py` and the Rust continuation bindings). A
`sase tool` plan must reuse this result graph rather than create another follow-up
mechanism.

### `sase-11y` is building the missing machine service substrate

At the inspected revision, `sase-11y` has already landed:

- Proc service metadata and per-service retention;
- project-excluding `service.procs` configuration composition;
- a locked, boot-aware service state store;
- restart decision/state facades;
- detached-cgroup escape;
- a shared child-supervision library.

Its active work adds the status snapshot, service host/CLI, platform units, Services
tab, and transient oneshot service Procs. In particular, `sase-11y.8` intends to move
background commands onto transient oneshot service Procs with recorded exit codes and
durable rerun.

This is complementary infrastructure, not a competing definition of ToolRun. Service
procs answer “which process does the machine host own?” Tool runs answer “which
catalogued operation was requested, what inputs did it cover, what stages happened,
what did it predict, and may its result be reused?”

### Proc retention is intentionally too small for a prediction corpus

Generic terminal Proc history defaults to 100 rows; named service procs keep the newest
20 terminal rows per service. That is appropriate for operational process history, but
not for duration distributions, failure baselines, change-point analysis, or long-lived
receipt evidence. Treating every ToolRun as only a Proc would either lose the corpus or
force the Proc store to become an analytics database.

The current telemetry store is also not a substitute for ToolRun identity. It is a
Rust-owned SQLite time-series store with raw/5-minute/1-hour retention and
counter/gauge/histogram queries. It is ideal for aggregate metrics such as duration,
outcome count, load, and prediction calibration. It does not retain the entity graph
needed for `sase tool show RUN`, attempts, stages, fingerprints, receipts, diagnostic
signatures, or execution-owner links.

Therefore:

- the **ToolRun store** is canonical for versioned run entities and summaries;
- the **Proc store** is canonical for background process lifecycle and bounded logs;
- the **telemetry store** receives low-cardinality aggregate metrics;
- tool logs have one owner (the linked Proc when background, the tool runtime when
  foreground), never two copied logs.

### Existing “Tools” UI means provider calls, not managed tool runs

`src/sase/ace/tui/tools/` reads provider `tool_calls.jsonl` and derives slow LLM tool
calls. It is useful evidence for adoption and historical import, but those entries are
not the proposed managed ToolRuns. The eventual UI should call the existing panel “LLM
Calls” and link a Bash call that invokes `sase tool run` to the richer ToolRun. It should
not merge their identities or render the same work twice.

### Capacity and queue primitives already exist

`sase-z4` is closed. Rust `runner_capacity` schema version 5 already owns weighted
claims, serial-lineage reuse, parallel addition, zero-weight records, waiters,
diagnostics, holds, numeric validation, and fail-closed snapshots. `sase-zp` carries
capacity through epic launches; `sase-10h` protects gate approval from blocking;
`sase-11l` holds un-dispatched agents and Procs while leaving running work alone.

A tool scheduler must extend this authority. Creating a tool-local token pool, a Python
queue, or a separate hold implementation would recreate bugs those epics have already
paid to fix.

## The boundary to freeze before planning phases

The following model should be a shared contract for all seven epics.

### Tool definition

A named tool is project data in the repository's `sase/sase.yml`, because its argv,
stages, input declarations, and receipt semantics belong to the project. This differs
from `service.procs`, which deliberately ignores project-local config because services
are machine policy.

The catalog should use argv arrays and no implicit shell. Suggested minimum shape:

```yaml
tools:
  check:
    argv: [just, check]
    stages: run_silent
    handoff: auto
    receipt:
      scope: tree
      inputs: [uv.lock, pyproject.toml, sase-core-revision.txt]
      ttl: 24h
```

Operational machine/user overlays may tune allowed local fields such as timeout or
authored demand, but they must not silently replace project command identity. The
composer should retain field provenance, and project-local tool identity must win or
conflict explicitly. Ad-hoc `run -- ARGV...` remains supported with byte-exact argv,
mandatory `--`, and no implicit shell, but it does not earn a receipt or a catalog
profile.

### ToolRun

The Rust-owned versioned record should include at least:

- run id and attempt-chain id;
- project, tool name/version, repository/workspace/tree identity;
- protected execution argv and separately redacted display argv;
- caller/agent/bead/epic/Patch attribution;
- requested mode and actual execution owner
  (`foreground`, `proc:<id>`, or `monitor:<id>`);
- lifecycle and typed outcome;
- stage timeline and progress;
- start/load/resource samples or references to them;
- prediction snapshot and basis as it was known at decision time;
- command/input/toolchain fingerprint;
- receipt produced/reused and validity explanation;
- normalized failure signatures and diagnostic references;
- log owner/locator, never a second copied log;
- force/bypass and policy-decision provenance.

Foreground and background execution paths must converge on the same record states. A
background Proc may settle first and then atomically project its terminal result into
the ToolRun; reconciliation must recover either side after a crash.

### Public CLI

The desired mature command group can still resemble the prior report, with one
adjustment: ship only the verbs whose owning epic is present.

- Bare `sase tool` delegates to `list` through the central convention.
- Epic 1 ships `list`, `run`, `runs`, and `show`.
- Epic 2 adds `stop` and `show --follow`.
- Epic 3 adds `stats` and `run -E/--explain`, then automatic routing.
- Epic 4 adds `receipt`.
- Epic 5 adds `failures` and `rerun`.
- Epic 6 adds queue/force/local-capacity fields to `run` and `status`.
- Epic 7 extends `status` to the fleet and adds machine drill-down in ACE.

Every public long option needs a short alias; options stay optional. An ad-hoc command
that later needs authored demand should receive a typed refusal containing an executable
retry, rather than making an argparse option formally required.

## Why seven epics rather than one or four

A good epic split has five properties:

1. a normal user can demonstrate a new result without reading internals;
2. rollback of that epic does not corrupt another product's durable state;
3. its acceptance can be expressed without assuming a later epic exists;
4. its data/evidence prerequisites exist when implementation starts;
5. one landing agent can review the complete behavioral surface.

The four broad phases in the requested source (“record, predict, reuse/triage, admit”)
are directionally right, but two of them still contain multiple independent risk
domains:

- “record” combines the canonical ledger with Proc/monitor handoff and Textual live
  behavior, exactly where `sase-11y` and `sase-124` are changing contracts;
- “reuse and triage” combines proof-validity/fingerprinting with diagnostic
  normalization/baseline classification;
- “admit” combines a local scheduler and nested grants with fleet protocol, UI,
  initialization, and multi-machine operational cutover.

Splitting those three pairs produces seven coherent products with clear acceptance.

## Recommended epic set

### Epic 1 — Named tools and the ToolRun ledger

**User result:** A user can declare `check`, run `sase tool run check`, preserve the
child's stdout/stderr and exit behavior, and immediately inspect the durable result with
`sase tool runs` and `sase tool show RUN`.

**Scope**

- Freeze the Rust ToolDefinition/ToolRun/state-machine/store contracts and PyO3
  bindings.
- Add the provenance-aware project tool catalog and schema/default examples.
- Implement foreground execution, crash reconciliation, bounded log ownership,
  redacted display argv, and recording-fails-open behavior.
- Ship `list`, `run TOOL | -- ARGV...`, `runs`, and `show` with versioned JSON for
  control-plane views.
- Emit compact agent-facing output and full human TTY streaming.
- Import historical provider Bash/monitor rows as `source: imported` summaries, without
  pretending they have fingerprints or load samples.
- Emit low-cardinality duration/outcome telemetry and adoption/bypass metrics.
- Integrate the ToolRun owner with disk inventory/retention from the start.

**Explicitly out**

No monitor handoff, ETA, auto routing, receipts, failure classification, admission,
fleet meters, or new TUI top-level surface.

**Normal-user acceptance**

On a clean test project, run a passing, failing, signaled, and interrupted named tool
plus one ad-hoc argv. All five get distinct durable records; child output and exit
semantics are correct; `show` explains terminal state; secret-marked argv is redacted;
restart reconciliation produces no phantom success; an unavailable recording store
warns but does not suppress the child command.

**Why it is an epic**

This crosses the Rust/PyO3 boundary, config composition, a durable store, process
execution, CLI, retention, import, and packaging. It is already larger than a normal
phase, yet its user proof does not depend on any later intelligence.

### Epic 2 — Durable tool execution and live run UX

**User result:** A user can hand a long named tool off, leave the initiating process or
agent turn, follow it live, stop it, and see the same run identity in CLI and ACE.

**Dependencies**

- Epic 1.
- `sase-zl` (already closed) for structured result/continuation delivery.
- `sase-11y.4` and `sase-11y.8`, or the accepted equivalent service-host/oneshot
  contracts, before the standalone detached adapter lands.
- `sase-124`'s cheap refresh/change-token path before the live ACE surface lands.

**Scope**

- Add the execution-owner adapter:
  - foreground: ToolRun owns the child/log;
  - in-agent handoff: existing monitor Proc owns child/log/workspace/continuation;
  - standalone detached: transient oneshot service Proc owns child/log.
- Add explicit `-H/--hand-off`; do not auto-route yet.
- Make `show --follow` and `stop` facades over the authoritative execution owner.
- Reconcile ToolRun/Proc settlement after either side crashes.
- Put a fixed-width live tool chip on the owning agent row and a ToolRun card in agent
  detail, reading cached snapshots only.
- Rename the existing provider-call panel to “LLM Calls” and link wrapped Bash calls.
- Publish one settlement notification through the `sase-117` targeting path.

**Explicitly out**

No predictor, automatic handoff, receipt reuse, capacity queue, or fleet surface.

**Normal-user acceptance**

Start the same slow test tool from a human shell, from inside an agent with `-H`, and as
a standalone detached request. Each produces exactly one ToolRun; background cases link
exactly one Proc; stop and timeout settle both sides consistently; the in-agent case
delivers one continuation result; ACE updates without a full archive reload; restarting
the TUI or service host does not lose the run.

### Epic 3 — Forecasts and automatic inline-versus-handoff routing

**User result:** Before running, `sase tool run -E check` explains the expected duration
range and whether SASE would reuse, run inline, or hand off. Normal `run` then makes that
decision and explains it in one line.

**Dependency/readiness gate**

Epic 1 must have a real corpus. Imported history can seed coarse priors, but automatic
decisions stay disabled until chronological backtesting meets an explicit calibration
threshold for the relevant cohort. Epic 2 supplies the handoff action.

**Scope**

- Record load/pressure and stage/resource samples for every managed run.
- Implement Rust-owned empirical quantiles with transparent fallback by project, tool
  version, machine, load bucket, and relevant tool covariates.
- Treat timeouts/cancellations/running rows as censored observations.
- Ship `stats`, prediction basis/sample counts, and `run -E/--explain`.
- Add conditional remaining-time estimates, overdue/stalled states, and calibrated
  `timeout: auto`.
- Add provider-budget-aware automatic inline/handoff routing.
- Notify for overdue/stalled or human-started completion through existing notification
  infrastructure.

**Explicitly out**

No ML model, no admission influence, no automatic weight rewrite, no remote dispatch.

**Normal-user acceptance**

Backtest held-out runs and show the configured interval covers approximately its stated
share. A short tool stays inline; a long tool hands off; low-sample tools show
`unknown` or a labeled fallback; a run past p90 says “overdue” rather than inventing a
countdown; the explanation names every input to the decision.

### Epic 4 — Safe receipts and staged verification

**User result:** Re-running `check` on an identical covered tree returns a cited pass
receipt without repeating the work; changing a declared input invalidates it. Cheap
lint stages can fail before heavy tests start.

**Dependency**

Epic 1, including a stable fingerprint algebra. It may be developed in parallel with
Epic 3 after that contract freezes.

**Scope**

- Define tree- and workspace-scoped fingerprints, dirty-diff identity, toolchain and
  allow-listed environment inputs, profile version, TTL, and invalidation reasons.
- Allow only explicitly receipt-capable named tools to mint reusable pass receipts.
- Ship `receipt TOOL` and reuse/force-rerun behavior.
- Represent declared stages and stage receipts; run cheap stages first and reuse their
  pass in the later full run.
- Integrate verification and install examples; let host-completion policy, not an
  agent, decide whether a receipt satisfies a landing gate.
- Report hours avoided and false-reuse safety tests.

**Explicitly out**

Failures do not become reusable receipts. No concurrent single-flight joining, remote
cache, or automatic hermeticity claim.

**Normal-user acceptance**

Two identical `check` invocations execute once; a source edit, dirty-diff change,
lockfile/toolchain change, TTL expiry, or missing declared input forces execution with a
specific reason. A lint failure prevents the expensive test stage. A non-hermetic tool
without explicit receipt policy never reuses.

### Epic 5 — Failure intelligence and structured continuations

**User result:** `sase tool failures` groups stable signatures as NEW, KNOWN, or FLAKY,
and a follow-up agent receives that structured evidence without a hand-written
1,000-character baseline-diff instruction.

**Dependencies**

Epic 1 and the existing `sase-zl` result/evidence graph. Epic 4's stage model is useful
but should be an additive dependency only if failure extraction relies on it.

**Scope**

- Normalize diagnostics into stable signatures without workspace-number/path noise.
- Separate verification failures from infrastructure failures.
- Compare against merge-base/master evidence and the existing flake/task corpus using
  explicit provenance and observation windows.
- Ship `failures` and `rerun RUN` attempt chains.
- Feed bounded signature/evidence objects into monitor continuations.
- Add the Admin Center Tools pane's failure/history views only after the CLI contract is
  accepted.
- Suggest existing/new bead actions; never auto-create beads.

**Explicitly out**

No automatic source changes, automatic task creation, or claim that an unknown failure
is caused by the current diff.

**Normal-user acceptance**

Run fixtures containing one current-diff failure, one master failure, one known flake,
and one infrastructure failure. CLI, JSON, continuation, and ACE agree on identities
and labels; repeated signatures group; evidence stays bounded; ambiguous cases remain
UNKNOWN rather than being mislabeled.

### Epic 6 — Local tool capacity admission

**User result:** On one machine, expensive tools and agents share one authoritative
capacity budget. A request that does not fit is safely refused or queued, never starts
early, never leaks demand, and explains an executable next action.

**Dependencies/readiness gate**

- Epics 1 and 2 for run identity and durable waiting execution.
- Existing `sase-z4`, `sase-zp`, `sase-10h`, and `sase-11l` contracts.
- Epic 3 must have enough data to recommend initial prices; authored prices remain
  policy until calibration is proven.

**Scope**

- Extend the Rust runner-capacity owner with temporary ToolRun demand and legal
  transitions; do not add a scheduler.
- Link reservations to authoritative claim lineage and Proc/ToolRun process-birth
  identity.
- Add one fair queue, finite wait policy, impossible-request handling, bounded
  deference, cancellation, and crash/reboot recovery.
- Preserve zero-weight gate/epic-launch behavior and hold only undispatched work.
- Validate nested grants; put supported recipe setup/build/pytest paths behind the
  grant and enforce worker ceilings.
- Add queue/force/resume controls and local capacity detail to `run`/`status`.
- Keep admission fail-closed with a recorded break-glass; recording itself stays
  fail-open.

**Explicitly out**

No remote placement, fleet meter, cross-machine cache, preemption, or automatic capacity
rewrite.

**Normal-user acceptance**

On an isolated managed host with a small capacity, saturate the budget, submit a heavy
tool and a light agent, exercise queue aging, cancel one waiter, kill one supervisor,
restart the coordinator, and run nested pytest. At every point the Rust snapshot,
`sase tool status`, Proc state, and actual children agree; capacity is never
oversubscribed except by an explicit recorded force; gate approval remains prompt.

### Epic 7 — Fleet capacity surfaces and coordinated rollout

**User result:** ACE and CLI show trustworthy local and remote machine capacity,
holders, freshness, and expected starts; the new ledger can be activated and rolled
back machine by machine without double admission.

**Dependencies**

Epic 6 plus the accepted unified-fleet and `sase-124` refresh contracts. This is the only
epic that edits fleet wire/presentation and machine initialization for tool capacity.

**Scope**

- Publish a versioned capacity snapshot per machine through the existing Rust fleet
  path and change-token invalidation.
- Extend `sase tool status` and machine detail with fresh/stale/unknown semantics,
  holders, queued target, pressure, and expected start.
- Add compact accessible machine meters without a new poll loop or render-path I/O.
- Require explicit per-machine persistent capacity through existing init/doctor
  workflows.
- Stage the compatible release, drain old owners, activate the new ledger, verify
  athena/apollo/Mac, and prove rollback.
- Measure TUI p95 and idle-refresh costs before and after.

**Explicitly out**

No remote execution dispatch, machine migration, combined fleet denominator, or
automatic capacity based on physical cores.

**Normal-user acceptance**

With one current peer, one old peer, and one offline peer, CLI and ACE show fresh,
unknown-capability, and stale states honestly. Local load is identical to admission's
snapshot. A controlled drain/cutover proves no old and new budgets coexist. Rollback
waits for new holders to drain. The TUI meets the existing p95 and quiet-tick targets.

## Dependency shape

Strict dependencies and evidence gates are:

```text
Active foundations:
  sase-11y service/proc work ───────┐
  sase-zl monitor results (done) ───┤
  sase-124 refresh work ────────────┤
                                    v
Epic 1: ledger ──> Epic 2: durable execution ──> Epic 3: forecast/routing
       │                 │                         │
       ├────> Epic 4: receipts/stages              │
       └────> Epic 5: failure intelligence         │
                         │                         │
                         └──────────┬──────────────┘
                                    v
                         Epic 6: local admission
                                    │
                                    v
                         Epic 7: fleet + rollout
```

Epics 4 and 5 can run in parallel with the corpus-collection period for Epic 3 once the
Epic 1 wire/fingerprint boundaries are stable. They are sequencing prerequisites for a
coherent product roadmap, not hard technical prerequisites for every line of Epic 6.

## Interaction with active and recent epics

| Work | Complement to reuse | Conflict to avoid | Recommended dependency/ownership |
| --- | --- | --- | --- |
| `sase-11y` service host | shared supervision; service Proc block/status; transient oneshots; Services UI | new Proc kind, second service host, duplicate logs, editing the same parser/config/TUI seams concurrently | Epic 1 can build isolated ledger modules; Epic 2 waits for service-host/oneshot contracts |
| `sase-z4` / `sase-zp` weighted capacity | Rust claim lineage, decimal accounting, queue metadata | Python/tool-local token bucket or mutable launch weights | Epic 6 extends Rust policy |
| `sase-10h` gate admission | non-blocking approval and explicit zero-weight monitor | a tool queue that makes gates consume/wait on tool capacity | Epic 6 carries explicit zero semantics in acceptance |
| `sase-11l` holds | undispatched Proc/agent eligibility barrier | stopping a running tool or a second hold store | Tool waiters participate only at the existing eligibility boundary |
| `sase-kp` / `sase-zl` monitors | workspace handoff, result graph, retained diagnostics, exact-once continuation | second continuation graph, copied log, shell-string success inference | Epic 2 links monitor as execution owner; Epic 5 enriches its result |
| `sase-117` settlement notifications | exact targeted refresh and settlement events | broad TUI refresh or bespoke notification polling | Epics 2/3 publish through the existing channel |
| `sase-xe...` fleet work | authenticated machine identity, versioned fleet snapshot, stale/old-peer handling | new fleet transport or locally inferred remote load | Epic 7 extends the existing wire |
| `sase-124` / `sase-zn` TUI performance | cheap load token, cached first paint, bounded reloads, pump-free work | filesystem scans, a new polling loop, render-time stats | Epic 2/7 wait for or consume these paths |
| `sase-zw` retention | disk owners, pressure/inventory, safe pruning | an unregistered `~/.sase/tools` corpus/log tree or copied Proc logs | Epic 1 registers ownership and retention immediately |
| `sase-11e` terminology | established Routine/Job vocabulary | calling ToolRuns “jobs” and confusing Scheduler jobs with commands | Use ToolRun/run consistently |
| `sase-x7.5.1` shared formats | coordinated versioned wire release practice | an unversioned cross-repo ToolRun format during a shared-format cutover | Version the wire from day one and coordinate release floors |

### Specific answer about `sase-11y`

Do not wait to design the ToolRun contract, but do not implement a competing background
runtime while `sase-11y` is active.

Safe work now:

- the ToolRun/catalog/store model in new modules;
- foreground-only `run` and history CLI;
- import/adoption measurements;
- aggregate telemetry and retention registration.

Work that should follow `sase-11y`'s accepted contracts:

- standalone detached tool execution via transient oneshot service Procs;
- Services/Tools navigation decisions;
- service status/change-token integration;
- any refactor of Proc submission, supervisor bootstraps, or process stop semantics.

This produces useful progress without asking two epics to edit
`src/sase/procs`, `src/sase/service`, parser registration, default config, and the same
TUI tree simultaneously.

## Disposition of `sase-zm`

`sase-zm` should be superseded/canceled before these epics launch, not left as a
parallel owner.

Current evidence:

- all fourteen phases are still marked in progress;
- the baseline phase has been closed and reopened twice;
- current master contains no `tests/fixtures/command_capacity` baseline files and no
  discoverable `sase-zm` implementation commit;
- the current source still has no `sase tool` command or ToolRun core type;
- useful contracts exist in the plan and bead notes, but there is no landed feature
  whose ownership must remain with the old epic.

Nothing should be discarded conceptually. Map its work forward:

| `sase-zm` phases | New owner |
| --- | --- |
| baseline fixtures and adoption evidence | Epic 1 |
| command reservation/lease/fair queue | Epic 6 |
| monitor integration | Epic 2 for execution ownership; Epic 6 for queued capacity transfer |
| CLI | each new epic owns the verbs/options it makes real |
| machine capacity initialization | Epic 7 |
| profiles and selection facts | Epic 1 catalog, Epic 3 prediction, Epic 6 authored demand |
| pytest/recipe admission | Epic 6 |
| fleet snapshot/meters | Epic 7 |
| guidance and coordinated rollout | the epic whose behavior is being activated, chiefly Epics 6–7 |

The old plan remains valuable research material, but keeping its phases assigned while
new epics modify the same seams would make ownership ambiguous and invite duplicate
stores/queues.

## Cross-epic acceptance rules

Every epic should preserve these invariants:

1. **One semantic run, one ToolRun id.** Retries form an explicit attempt chain.
2. **One process owner.** Foreground runtime, Proc, or monitor owns the child; never
   two.
3. **One log owner.** ToolRun points to the authoritative retained log.
4. **One continuation graph.** Monitor result delivery remains `sase-zl`'s.
5. **One capacity authority.** Rust runner-capacity policy remains authoritative.
6. **One fleet transport.** Existing fleet snapshots carry additive capacity data.
7. **Versioned JSON from the first release.** CLI, PyO3, TUI, and gateway consumers do
   not reverse-engineer text.
8. **No policy feedback before calibration.** Predictions advise before they schedule;
   suggested weights do not silently rewrite configuration.
9. **No unbounded storage.** Summary and log retention, disk inventory, and pressure
   behavior land with the first writer.
10. **No fake precision.** Unknown ETA/load/receipt applicability stays unknown.

## Decisions to make in the first planning session

The first epic plan should explicitly settle these questions; later epics should not
reopen them casually:

1. **ToolRun store shape.** A dedicated Rust-owned SQLite entity store is the strongest
   fit for indexed history and atomic state, while telemetry remains aggregate-only.
   If an event log is chosen instead, prove bounded replay/query cost and migrations.
2. **Config provenance.** Define exactly which named-tool fields are repository-owned
   and which machine/user layers may tune.
3. **Log ownership.** Specify foreground log paths, background Proc locators, and
   retention without copying.
4. **Recording failure semantics.** Warn and run when initial recording fails; define
   how a lost terminal update reconciles.
5. **Redaction.** Store protected execution argv separately from display argv and never
   persist an environment dump.
6. **Artifact identity.** Reserve a `tool:<run-id>` reference only if the artifact
   provider can resolve it without turning every run into an explicit copied file.

Decisions that should wait for evidence:

- exact admission weights;
- automatic timeouts;
- single-flight joining;
- fleet placement hints;
- any ML predictor;
- cross-machine receipt reuse.

## Recommended solution

Create one legend with the seven epics above. Plan Epic 1 now. Make Epic 2 explicitly
dependent on the accepted `sase-11y` service-host/oneshot and `sase-124` refresh
contracts where it touches them. Allow Epics 4 and 5 to proceed after Epic 1 while Epic
3 accumulates and validates its corpus. Do not begin admission until the record and
duration evidence exist. Split local admission (Epic 6) from fleet protocol/UI/cutover
(Epic 7).

Before launching that legend:

1. decide and record that ToolRun is a semantic record linked to, not embedded in, a
   Proc;
2. supersede/cancel `sase-zm` and preserve its plan as input;
3. add explicit dependencies on the active proc/service/TUI work instead of relying on
   “rebase later” prose;
4. assign each CLI verb and each durable store to exactly one epic;
5. make every epic's acceptance a runnable user story like the ones above.

That sequence yields useful software after every landing, minimizes conflict with the
current service-host work, and reserves the riskiest scheduling and fleet changes for
the point at which SASE has actual ToolRun evidence rather than a hand-authored price
table.
