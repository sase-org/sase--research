# Which scheduled jobs should become service procs?

Independent research by **cdx**, 2026-10-07. No other report or researcher findings from this swarm were consulted. This is a research recommendation, not an implementation or a change to running automation.

**Recommendation:** migrate `wait_checks` into one persistent, wakeable `wait_resolver` service proc. Keep remote syncing out of its execution loop and retain periodic reconciliation and the runner fallback. Do not convert every job or promote entire routines merely to change their supervisor. Consider bead claim reconciliation as a later responsibility of the same service; retain the other jobs unless a specific latency or ownership requirement justifies migration.

## Evidence and scope

I inspected the primary checkout at `38f48d7575e4cddb49334a54a42ebfd257125d1f` and an audited `sase-core` checkout at `f8d05efc58310eca985f2112afc89379ff7a6636`. I read the relevant glossary, artifact instructions, and architectural decisions through `sase memory read`; inspected the effective job inventory and routine configuration without changing them; and ran isolated temporary-directory experiments against the primary checkout's Python helpers. I also checked primary documentation for scheduling and filesystem event delivery.

The shipped configuration has **seven routines, 29 job placements, and 28 distinct jobs**; `stale_running_cleanup` appears in two routines. Effective configuration on this machine also contains builtin `refresh_docs` plus plugin/user work (`ci_watch`, `tg_outbound`, `toobig_split`). The complete migration assessment below covers the shipped jobs and `refresh_docs`. I observed the additional names but did not inspect their implementations, so I do not issue implementation-level verdicts on them. The effective builtin routine intervals match the defaults. [Default configuration][S1]

Confidence is high about control flow and the reproduced trigger/publication behavior. There is no before/after service prototype or representative latency benchmark. Performance gains below are architectural expectations, not measured results. A runtime snapshot showed the `waits` routine's cumulative no-op ratio at approximately 0.63, but that is a mixed-routine counter, not a `wait_checks` benchmark and not evidence that a daemon will use less memory.

## What migration would actually change

The current hierarchy is:

```text
platform unit, or detached host
  sase service
    scheduler service proc
      routine process, one per configured routine
        short job subprocesses, concurrent within a tick
    gateway service proc, disabled by default
```

Thus these jobs already run under a service proc indirectly. Routines are already persistent and independently restarted. Moving a routine under the service host can improve independent control and remove one supervision layer, but does not automatically change its cadence, blocking behavior, scanning cost, or subprocess launches. [Orchestrator][S2], [routine loop][S3], [service host spawning][S4]

A service proc provides lifecycle supervision, enablement, logs, and durable process records. It supplies neither dependency notifications nor a scheduled-job execution engine. Configured entries are daemons; oneshots are transient runtime submissions. The existing `sase_job_wait_checks` command performs one pass, requires job context, and exits. Configuring that command as a daemon does not implement waiting: `on-failure` parks a cleanly exited proc, while `always` creates repeated process restarts rather than a useful event loop. A migration needs an actual persistent entry point. Currently packaged `builtin:` launchers are limited to `scheduler` and `gateway`; a new command entry point is possible, or a new builtin requires the Rust configuration contract and Python launcher to change together. [Builtin job runtime][S5], [service configuration][S6], [launcher resolution][S7]

The useful change is therefore **from cadence-driven subprocess reconciliation to persistent reconciliation that can wake on relevant changes**, with a clear domain owner. Service ownership is the appropriate container for that change, not its mechanism.

## Why `wait_checks` is the strongest candidate

### There are several independent sources of delay

`waits.interval` is ten seconds. `wait_checks` has an `fs` trigger with a two-minute `max_quiet`. The runner checks `ready.json` every two seconds and, for project-backed dependency waits, performs its own dependency resolution roughly every sixty seconds. It also tries direct resolution before parking. [Defaults][S1], [runner wait barrier][S8], [runner resolver][S9]

With a trigger-visible change and short ticks, the routine contributes approximately zero to ten seconds of observation delay, followed by up to roughly two seconds for the runner to notice readiness. This is an estimate under those conditions, not a service-level guarantee. A ten-second interval is not the actual universal bound:

- Each routine submits its jobs concurrently but waits for **all** results before returning from the tick. `sidecar_auto_sync` shares `waits`, runs every thirty seconds, has a two-minute timeout, and spends up to a nominal ninety-second work budget on target processing and maintenance. A fast `wait_checks` result can be consumed during that tick; a dependency that changes after its pass may wait while unrelated syncing holds up the next tick. The ninety-second budget is not a guaranteed bound on every pre-pass or in-flight operation. [Routine tick][S3], [sidecar syncing][S10]
- The scheduler invokes the whole tick synchronously. The `schedule` documentation explains that execution time affects scheduling, and missed runs are not replayed. Consequently an interval cannot be treated as an end-to-end deadline. [Schedule documentation](https://schedule.readthedocs.io/en/stable/), [reference](https://schedule.readthedocs.io/en/stable/reference.html)
- The filesystem trigger can miss relevant state changes, independently of tick speed.

### The current filesystem trigger misses changes in existing date shards

The default watch glob is `*/artifacts/ace-run/*`. `_fs_watch_token` records metadata and immediate child count for each matched entry; it does not recursively summarize their contents. Canonical agent runs are stored at `ace-run/YYYYMM/DD/YYYYMMDDHHMMSS`. The glob therefore watches month directories rather than the actual run files. [Snapshot helper][S11], [canonical Rust layout][S12]

Using the actual helper in an isolated temporary tree produced:

| Mutation inside an existing month/day shard | Did the trigger token change? |
| --- | --- |
| Create `done.json` in an existing run | No |
| Rewrite that `done.json` | No |
| Create `waiting.json` in that run | No |
| Create another run under the same day | No |
| Create `done.json` in a legacy, unsharded run | Yes |
| Rewrite the legacy run's existing `done.json` | No |

These results demonstrate token blindness, not a measured production stall. The Rust trigger skips an unchanged token until `max_quiet` elapses. For eligible project-backed waits, the sixty-second direct-resolution fallback may release the runner sooner than the job's two-minute quiet backstop. Other state changes can also cause an earlier job fire. The important conclusion is that the advertised ten-second routine is not a dependable ten-second wake mechanism. [Rust trigger decision][S13], [runner fallback][S8]

Merely replacing the shallow glob with a much larger recursive glob increases scan cost and still leaves tick scheduling. Prefer bounded mutation signals and correctly scoped watches; use a filesystem reconciliation pass to recover omissions.

### Readiness publication also needs tightening

The job writes `ready.json` by opening the final path and dumping JSON into it. The runner first checks existence, then `read_ready_result` returns **True** on JSON decoding or file read errors. A reader that catches the writer between file creation and complete publication can therefore cross the barrier. In separate temporary-file experiments, both an empty file and a file containing only `{` returned True. [Ready writer][S14], [ready reader][S9]

This is a reproducible behavior and a race opportunity, not proof of a production premature launch. It should be corrected as part of the readiness path: publish atomically, reject malformed/unreadable readiness, and bind any new readiness record to the current waiting generation. A faster concurrent observer makes publication discipline more important.

### The resolver's semantics are substantially richer than “process ended”

Named waits, exact artifact waits, sessions, clans/hoods, fork sources, planner handoffs, bead dependencies, and retries do not all have the same completion rule. The code confirms fresh session membership after reading completion evidence so a newly created monitor or gate member cannot be omitted by a stale index. One failing waiter stays parked while healthy siblings progress. Failed dependencies do not become successful merely because a process exited. [Wait handler][S14], [membership confirmation][S15], [behavior documentation][S16]

A new service must preserve that shared behavior and its existing fixtures. It must not reinterpret every terminal proc as an agent success, or hold a run-scoped metadata cache forever. The existing resolver is spread across Python adapters/helpers and Rust reductions; it is not currently one completely Rust-owned wait service. New shared dependency and ownership policy belongs in `sase_core`, exposed through `sase_core_rs`, rather than in a competing service-only Python implementation.

Finally, `wait_checks` normally releases a **pre-provider runner barrier**. It does not resume an LLM turn that has already ended. The runner then applies time conditions, refreshes code as needed, and acquires capacity through the existing admission path. Agent continuation after monitor/gate completion remains mechanically host-owned. [Runner control flow][S17], [slot admission][S18]

## Complete candidate assessment

“Keep” means the scheduled job model remains suitable; it does not mean its current trigger or interval can never be improved.

| Job or closely related group | Current placement | Recommendation and reason |
| --- | --- | --- |
| `wait_checks` | `waits`, 10s, shallow fs trigger | **Migrate first.** Local dependency progress is latency-sensitive; persistent state and mutation wakeups are useful. |
| `bead_claim_checks` | `waits`, 10s, same fs trigger | **Later candidate for the same wait service.** Related pre-launch ownership, but includes store locks, commits/publication, and dead-owner reconciliation. Keep its slow I/O off the readiness loop and retain liveness checks. |
| `sidecar_auto_sync` | `waits`, every 30s, 2m timeout | **Separate from fast waits immediately; service migration optional.** A separate scheduled routine solves interference. A later sync service can consume durable hints and own retries if remote bead convergence latency justifies it. |
| `epic_launch_flush` | `waits`, every 30s | **Keep as recovery work.** It flushes orphaned notifications after a 90s grace and reaps old settle markers. Improve normal settlement at its producer; a permanent orphan-repair daemon has little initial value. |
| `hook_checks`, `mentor_checks`, `workflow_checks` | `hooks`, 5s, fs triggers | **Keep initially.** They share Patch lifecycle context and runner budgets. If five-second progression or startup cost proves limiting, use one coherent Patch reconciler, not three daemons. |
| `pending_checks_poll` | `hooks`, 5s, result-file trigger | **Keep initially; event-driven invocation is plausible.** This is a bounded result collector. Direct completion notification or scheduling on output changes can avoid a dedicated daemon. |
| `comment_zombie_checks`, `suffix_transforms`, `orphan_cleanup` | `hooks`, 5s, Patch triggers | **Keep.** State normalization, deadline checking, and conservative repair fit jobs; review cadence separately. |
| `stale_running_cleanup` | `hooks`, 5s, plus `checks`, 300s | **Keep the periodic backstop.** It checks dead supervisors/PIDs, repairs proc rows and monitor state, and releases claims. Add exit notifications for owned children if useful; external death still needs reconciliation. Do not move all orphan cleanup into the central service host. |
| `bead_task_triage`, `plugins_required` | `checks`, 300s | **Keep.** Bounded gate reconciliation with generation/deduplication. Human decision workflows do not justify resident processes per job. |
| `pr_submitted_checks` | `checks`, 300s | **Keep.** Starts remote checks; changing its supervisor cannot make upstream state arrive earlier. |
| `usage_refresh` | `usage`, 60s, 90s timeout | **Keep.** Already machine-wide, due-aware, coalesced, cooldown/Retry-After constrained, and run inline without submitting a proc for each scheduled probe. A persistent provider collector is conditional on a demonstrated timing or connection requirement. |
| `external_issue_mirror`, `external_pr_mirror` | `external_mirror`, 900s, per-project | **Keep.** Deliberately paced remote polling, bounded inventories, checkpoints and backoff. A future webhook ingestion service could wake these same bounded reconciliation operations. |
| `comment_checks` | `comments`, 60s | **Keep.** Remote polling throttle and local result collection are deliberately separate. An upstream push integration, not daemon ownership, is the route to materially earlier feedback. |
| `error_digest`, `notification_store_compact` | `housekeeping`, hourly | **Keep.** Batching and store maintenance; permanent residency offers little latency benefit. |
| `managed_tmp_reap`, `proc_runtime_sweep`, `disk_pressure` | `housekeeping`, hourly | **Keep.** Bounded owner-safe cleanup. If hourly disk-pressure detection is too slow, give the existing check a shorter independent cadence; a service is unnecessary without continuous telemetry needs. |
| `bead_stale_cleanup`, `artifact_link_backfill`, `artifact_run_prune` | `housekeeping`, hourly | **Keep.** Slow backlog repair, bounded migration/outbox work, and retention previews. Preserve checkpoints, budgets, and deletion/preview policy. |
| `gate_turn_reclaim` | `housekeeping`, hourly, 2m timeout | **Keep as recovery; revisit deadline handling separately.** Normal gate answers already settle through the gate path. Hourly observation can delay deadline expiry and recovery; a deadline timer or faster bounded lane is a better first fix than a service per gate-repair job. |
| `refresh_docs` | Builtin, currently configured separately at 60s | **Keep.** A proposal job selected by commit-count policy and action-success checkpoints. Preserve the scheduler's admission/deduplication rather than replacing it with a daemon that launches agents itself. |

Placement and job contracts come from [defaults][S1]. Additional implementation evidence: [bead claim reconciliation][S19], [usage job][S20], [gate reclaim][S21], [stale process cleanup][S22], [documentation refresh][S23]. These are capability assessments, not an endorsement of every existing default cadence.

## Critique of a broader migration

The idea is good where it creates a distinct persistent owner for latency-sensitive local progress. It is weak as a blanket “service procs are better jobs” strategy.

1. **A service per job adds persistent memory, watch registrations, config, shutdown paths, and upgrade obligations.** Some routines would remain for their other jobs, so the first migration adds a resident process rather than simply replacing one. Idle fs-triggered jobs already avoid many subprocess launches. Measure total cost before claiming savings.
2. **Existing supervision is already substantial.** Routines are restarted today, and individual jobs have execution records, structured summaries, guards, cadence, timeouts, deduplication, and proposal admission. A daemon needs operation-level equivalents where applicable. PID liveness alone does not prove its dependency work is progressing. [Routine supervision][S2], [job runner][S24]
3. **A daemon loses per-invocation memory reset and kill boundaries.** A leaked cache or hung store operation can stall all waiters. Keep per-waiter faults isolated, bound reconciliation, and put network or uninterruptible work in cancellable workers with deadlines.
4. **Pure events are insufficient.** New directories require watch registration; rename/atomic replace can invalidate a file watch; event queues can overflow. Linux inotify is not recursive, and network filesystems may deliver no events. Use notifications to request a fresh authoritative read and repair on startup, overflow, and a periodic timer. [Linux inotify](https://man7.org/linux/man-pages/man7/inotify.7.html), [notify crate documentation](https://docs.rs/notify/latest/notify/)
5. **Local observation is not remote freshness.** A bead closed elsewhere is unavailable to a local wait resolver until the owning store converges. Turning `wait_checks` into a daemon does not remove fetch latency or remote failures. Keep one conservative sync policy and emit a local wake after successful convergence.
6. **Lifecycle independence changes operator expectations.** Stopping `scheduler` currently pauses its whole routine tree. A separately hosted wait service would continue operating. `sase update` and feature-flag changes currently restart the scheduler; a new resident service can retain old code or settings unless those restart/reload paths are extended. `after` is start ordering, not dependency readiness. [Service config][S6], [update restart][S25]

## Explicit adjustments to the requirements

I would change the proposed requirements as follows:

- **Optimize committed local state to readiness latency, not the number of jobs converted.** Start with a proposed target of p95 under one second to publish local dependency readiness and p95 under three seconds for the existing two-second-poll runner to observe it, on an otherwise idle healthy host. These are acceptance targets to validate, not predictions. Resource admission, deliberate time waits, and remote sync are separately measured.
- **Migrate a responsibility rather than an entire routine.** `waits` mixes fast dependency coordination with remote syncing and orphan recovery. One wait resolver is justified; moving all four jobs into one synchronous daemon preserves their interference.
- **Retain convergence and degraded operation.** Keep startup/periodic authoritative reconciliation and the runner's sixty-second fallback. No event bus or comprehensive durable change journal is required for the first version.
- **Strengthen readiness publication.** Atomic writes, malformed-record rejection, waiting-generation validation for new records, and a single readiness writer are required. Faster but prematurely released waits would be a regression.
- **Make stop/update semantics explicit.** Separate service control should allow waits to keep progressing while scheduled maintenance is paused. Document that deliberate change, and provide an aggregate pause through existing control surfaces if all automation must stop. Keep the central host focused on supervision rather than executing wait or bead domain logic itself.
- **Preserve current workflow semantics.** No premature capacity allocation, no changing post-dependency durations to pre-dependency timers, no treating failure as success, and no provider-turn resurrection. New policy must be shared across CLI, TUI, and service through the Rust core boundary.

## A concrete architecture and rollout

Create one `wait_resolver` service proc with a genuine daemon entry point, bounded output, graceful shutdown, and explicit restart behavior. An always-restart policy is reasonable for an essential resident resolver; intentional host stops must still remain stopped. Do not depend on `after: [scheduler]` for correctness: local readiness should work independently of the scheduler's current PID.

The service wakes on **wait registration/removal, relevant agent/session/hood membership or terminal changes, bead-store convergence, and a repair timer**. A first implementation can coalesce project changes and reconcile that project's pending waits; a dependency-to-waiter map is useful later if profiling establishes the need. Cross-project dependencies must wake the consuming projects as well. Observe only relevant metadata/markers, not streamed output or every retained artifact.

Reuse the existing architectural seams. Agent completion already touches a project `.ace_refresh_pulse`; waiting-marker publication already updates the artifact index; sidecar publishers already leave durable per-project role hints; capacity admission already has a `runner_slots.token`. These are useful integration points, but none currently provides a complete durable wait notification protocol. Extend producer coverage and reconcile omitted signals; do not declare the best-effort artifact index or a pulse to be the source of truth. [Completion marker][S26], [refresh pulse][S27], [wait marker][S28], [sync hints][S29], [index mutation][S30]

A wake schedules a fresh read of canonical state, bounded dependency evaluation, fresh membership confirmation, and atomic readiness publication. A local socket or directory watch can notify runners; the two-second polling path can remain initially. Recheck readiness after subscribing and immediately before sleeping so a change between observation and wait registration cannot be lost. Add overflow and watcher-failure handling and a conservative repair interval, initially around thirty seconds. A dropped notification may delay reconciliation but must not authorize readiness.

Keep all Git fetching and sidecar publication out of that loop. Initially move `sidecar_auto_sync` into an independent routine, preserving its state directory/checkpoints or explicitly migrating them. If remote convergence remains the dominant delay, then introduce a dedicated `sidecar_sync` service consuming existing hints, retaining backoff and bounded work, and issuing completion wakeups. A local hint identifies desired work; it does not imply a remote fetch succeeded. Avoid a separate fast-beads sync algorithm.

Retain a run-once reconciliation operation behind the current manual `wait_checks` surface. Both manual execution and the daemon must honor the same ownership/lock and readiness generation contract. Select the active writer explicitly during rollout; a service crash must not cause a second writer to race it. Runner fallback may continue to resolve its own barrier through the same predicate. Initially compare the service's proposed releases with the existing operation in a read-only shadow mode before enabling publication.

Put new shared readiness, ownership, generation, and invalidation policy in `sase_core`; expose it through bindings and update `sase-core-revision.txt` when Python calls the new API. Keep process/watcher plumbing and plugin side effects in thin Python adapters. Preserve existing dependency fixtures while moving or adapting the behavior; do not fork a second resolver.

After adoption, consider folding **local** bead claim reconciliation into the same service, with independent bounded workers and periodic dead-owner checks. Leave `epic_launch_flush` and gate repair scheduled. Revisit a combined Patch lifecycle service only if its five-second delay or job-process cost is material in measured use. A wakeable scheduler dispatching the existing job runner is a credible alternative when several domains need early execution; it preserves job policy and history but is a larger scheduler change than this focused first migration.

## Verification that should decide adoption

Use the current tests as behavioral fixtures, then test the new owner across process boundaries:

- Preserve terminal outcome classification, exact versus named dependencies, bead conjunctions, missing/unreadable stores, session/monitor/gate successors, hood membership, fork sources, and one bad waiter's isolation.
- Reproduce the existing same-day shard blind spot, then show a newly created waiter and completed dependency wake without waiting for the periodic repair interval.
- Crash before and after readiness publication, restart the service with already-complete dependencies, drop notifications, overflow/disable watchers, and add a directory before watch registration. Require eventual progress without an early release.
- Show empty/partial readiness remains parked, stale waiting generations cannot release a new barrier, and repeated/manual reconciliation cannot create duplicate admission or publication.
- Run a slow or failing sidecar fetch concurrently with healthy local waits. Measure remote-store convergence separately, and prove one blocked project or lock does not stall unrelated waiters.
- Verify mixed dependency/duration and absolute-time behavior, capacity priorities/holds, cancellation, scheduler stop, host restart, service disable, and CLI update reload/restart behavior.
- Compare dependency-to-ready and ready-to-runner p50/p95/p99, idle CPU, total RSS, subprocess counts, filesystem reads, watch count, pending waiters, oldest unresolved age, errors, and last successful reconciliation. Include many waiters and long retained histories, not just a single empty project.

The most relevant existing fixtures include `test_axe_chop_wait_checks_terminal_outcomes.py`, `test_axe_chop_wait_checks_beads.py`, `test_axe_chop_wait_checks_fault_isolation.py`, and `test_axe_chop_wait_checks_plan_agent_sessions_handoffs.py`. I inspected these but did not run the test suite; the experiments above exercised actual helpers with temporary input and left application state unchanged.

## Source index

The numbered references link to the inspected revisions, so later changes need not silently change the evidence. The effective inventory/runtime counters were read-only observations of this machine on 2026-10-07; they are not a durable benchmark dataset.

[S1]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/default_config.yml#L1184
[S2]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/axe/orchestrator.py
[S3]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/axe/lumberjack.py#L160
[S4]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/service/host_spawn.py#L61
[S5]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/chops/builtin.py#L152
[S6]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/docs/configuration.md#L4351
[S7]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/service/host_support.py#L28
[S8]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/axe/run_agent_wait.py#L209
[S9]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/axe/run_agent_wait_deps.py#L126
[S10]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/scripts/sase_chop_sidecar_auto_sync.py#L453
[S11]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/axe/chop_policy_snapshots.py#L134
[S12]: https://github.com/sase-org/sase-core/blob/f8d05efc58310eca985f2112afc89379ff7a6636/crates/sase_core/src/agent_scan/layout.rs#L49
[S13]: https://github.com/sase-org/sase-core/blob/f8d05efc58310eca985f2112afc89379ff7a6636/crates/sase_core/src/axe_chop/decision.rs#L271
[S14]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/scripts/_chop_wait_checks_run.py#L45
[S15]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/core/wait_dependency_resolution/_confirmation.py#L23
[S16]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/docs/axe.md#L249
[S17]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/axe/run_agent_runner.py#L195
[S18]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/axe/run_agent_wait_slots.py
[S19]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/scripts/sase_chop_bead_claim_checks.py#L79
[S20]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/scripts/sase_chop_usage_refresh.py#L57
[S21]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/scripts/sase_chop_gate_turn_reclaim.py#L32
[S22]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/axe/hook_jobs.py#L375
[S23]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/scripts/sase_chop_refresh_docs.py#L77
[S24]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/axe/chop_runner_script.py#L67
[S25]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/main/update_restart.py#L56
[S26]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/axe/run_agent_exec_markers.py#L29
[S27]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/turns/settlement.py#L200
[S28]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/axe/run_agent_wait_markers.py#L74
[S29]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/_sidecar_sync_hints.py#L29
[S30]: https://github.com/sase-org/sase/blob/38f48d7575e4cddb49334a54a42ebfd257125d1f/src/sase/core/agent_artifact_index_lifecycle_mutations.py#L162

## Recommended solution

**Adopt one focused `wait_resolver` service proc for `wait_checks`, using coalesced mutation wakeups plus bounded periodic reconciliation and the existing runner fallback. Fix readiness publication and the sharded trigger gap as part of that work. Move sidecar syncing into an independent execution lane now; consider a hint-driven sync service only if measured remote convergence requires it. Add bead claim repair to the wait service later if its blocking work can be isolated. Keep the remaining jobs scheduled, preserve their safety/admission contracts, and make independent stop/update behavior part of the rollout.**

This captures the useful part of the proposal—earlier, reliable local progress—without replacing a functioning scheduler with a collection of timer daemons.
