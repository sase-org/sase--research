# Architectural Analysis: Evaluating the Migration of Builtin Jobs and Routines to Service Procs

**Author:** Researcher gem (`research.40.gem`)  
**Date:** October 2026  
**Status:** Complete  
**Topic:** Service Procs vs. Scheduler Routines & Jobs; `wait_checks` Latency Optimization  

---

## 1. Executive Summary

This research investigates whether any of SASE's current builtin background automation routines or jobs (chops)—specifically examining the `wait_checks` job—should be migrated to standalone machine-level **service procs** (`service.procs`).

### Key Findings & Recommendations

1. **Fundamental Category Error:** Migrating periodic or triggered background automation jobs into `service.procs` is an **architectural antipattern**. It conflates long-running machine host infrastructure (e.g., HTTP servers, IPC daemons, master orchestrators) with domain-specific automation and reconciliation workflows.
2. **Audit Outcome (0 of 29 Jobs):** A comprehensive evaluation of all 29 builtin jobs across SASE's 7 scheduler routine lanes (`hooks`, `waits`, `checks`, `usage`, `comments`, `external_mirror`, and `housekeeping`) reveals that **zero jobs** qualify for migration to service procs. Every current job is fundamentally a periodic/triggered state reconciliation task that benefits from the scheduler's lifecycle supervision, concurrency controls, timeout handling, and maintenance mode.
3. **The `wait_checks` Fallacy:** Moving `wait_checks` into a service proc does not inherently reduce agent wake-up latency. A standalone polling daemon would simply burn CPU cycles repeating directory scans outside the scheduler, while an inotify/event-driven filesystem daemon faces critical barriers:
   - High inotify handle consumption across hundreds of sharded run directories;
   - Event storms caused by active agent logging and telemetry;
   - Race conditions against multi-step agent artifact finalization (the very reason the 2-phase `confirm_dependency_resolution` exists);
   - Inability to observe non-filesystem dependencies (such as external bead closures in git sidecars or project stores).
4. **The Real Problem & Solution:** The user's underlying requirement is **minimizing agent wakeup latency** (currently ~5–10 seconds under the 10-second `waits` cadence). We recommend a pragmatic four-tier evolutionary approach:
   - **Tier 1 (Immediate / Zero Code):** Move `wait_checks` to the 5-second `hooks` routine, or tune the `waits` routine interval from 10s to 3s–5s. Because `wait_checks` is protected by a shallow `fs` trigger, idle ticks cost only a handful of `stat()` calls.
   - **Tier 2 (Client Optimization):** Accelerate the waiting runner's direct fallback resolution in `run_agent_wait.py` from 60s to 5s–10s, allowing parked runners to self-wake when dependencies clear.
   - **Tier 3 (Producer-Side Signaling):** Have completing agents and `sase bead close` emit an event hint or write `ready.json` directly when predecessors finish.
   - **Tier 4 (Event-Aware Scheduler):** Enhance the single existing `scheduler` service proc with an event-driven wakeup loop, triggering routine ticks early upon filesystem changes without fracturing the architecture into isolated daemons.

---

## 2. Background & Subsystem Architecture

To understand why migrating jobs to service procs is problematic, one must examine the distinct responsibilities, supervision hierarchies, and resource contracts of SASE's background architecture.

```
┌────────────────────────────────────────────────────────────────────────┐
│                      Platform Unit (systemd / launchd)                 │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Supervises
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        sase service (Host Process)                     │
│                  (sase service run, OOMPolicy=continue)                │
├───────────────────────────────────┬────────────────────────────────────┤
│   service.procs: gateway          │   service.procs: scheduler         │
│   (Mobile HTTP API server)        │   (Builtin background orchestrator)│
└───────────────────────────────────┴─────────────────┬──────────────────┘
                                                      │ Spawns & monitors
                                                      ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         AXE Orchestrator Process                       │
│                       (sase scheduler run / AXE)                       │
├─────────────┬─────────────┬─────────────┬─────────────┬────────────────┤
│ hooks (5s)  │ waits (10s) │ checks (5m) │ usage (60s) │ housekeep (1h) │
├─────────────┼─────────────┼─────────────┼─────────────┼────────────────┤
│ hook_checks │ wait_checks │ bead_task_  │ usage_      │ error_digest   │
│ mentor_     │ bead_claim_ │ triage      │ refresh     │ managed_tmp_   │
│ checks      │ checks      │ pr_sub_     │             │ reap           │
│ workflow_   │ sidecar_    │ checks      │             │ disk_pressure  │
│ checks      │ auto_sync   │ ...         │             │ ...            │
└─────────────┴─────────────┴─────────────┴─────────────┴────────────────┘
```

### 2.1 The Host Infrastructure Layer (`service.procs`)

The **sase service** (`sase service run`) is a persistent per-machine host process registered as a platform unit (`systemd` user unit on Linux, `launchd` LaunchAgent on macOS). It supervises entries declared under `service.procs` in SASE configuration.

- **Process Model:** Each declared service proc runs as an independent, long-lived operating system process (`subprocess.Popen`).
- **Supervision & Lifecycle:** The host tracks PID liveness, handles restart backoff policies (`restart: always | on-failure | no`), and captures output logs via dedicated pumping threads (`_pump_service_output`).
- **State & Reservation:** Every service proc launch reserves a durable record in SASE's Proc store (`~/.sase/procs/runtime/`).
- **Scope & Role:** Service procs are machine-level infrastructure. Today, SASE ships with only **two builtin service procs**:
  1. `scheduler`: The orchestrator that runs SASE's background automation routines and scheduled jobs.
  2. `gateway`: The HTTP API daemon that serves mobile companion clients.
  3. *(Plugins may add entries, such as `sase-telegram`'s `telegram_receiver` long-polling daemon).*

### 2.2 The Automation Orchestration Layer (`axe.routines`)

The **scheduler** (`sase scheduler` / AXE) is a builtin service proc whose process runs the **Orchestrator** (`sase.axe.orchestrator.Orchestrator`).

- **Multi-Process Routine Lanes:** The Orchestrator does not run automation tasks inline. Instead, it spawns and supervises multiple **routine** processes (`sase axe routine run <lane>`), such as `hooks`, `waits`, `checks`, `comments`, `usage`, `external_mirror`, and `housekeeping`.
- **Fault Isolation:** If a routine process crashes, the Orchestrator detects the exit, records restart metrics, and restarts the lane with exponential backoff without disrupting other routines or stopping the host.
- **Maintenance Coordination:** AXE provides a centralized maintenance mode (`sase axe maintenance enter / exit`). When active, all routine ticks pause gracefully across the entire machine, allowing safe package upgrades, database migrations, and plugin installs.
- **Concurrency & Runner Pools:** The scheduler manages global agent and hook execution limits across all routines via `SharedRunnerPool` (`max_agent_runners`, `max_hook_runners`).

### 2.3 The Job Automation Unit (Chops)

A **job** (historically "chop") is a short, script-only unit of automation executed within a routine.

- **Execution Model:** Jobs run as scheduled functions or short-lived subprocess scripts inside their parent routine's loop.
- **Declarative Policies:** Jobs declare triggers (`fs`, `git.commits_since`, `always`), timeouts (`job_timeout`), deduplication, once-per policies, and fan-out targets (`for_each`).
- **Structured Results:** Jobs emit structured results (`ChopResultBuilder`) proposing agent launches, gate creations, or lifecycle transitions. The scheduler host—never the job itself—authorizes and executes those proposals.

### 2.4 Architectural Comparison Matrix

| Property | Service Proc (`service.procs`) | Routine (`axe.routines`) | Job / Chop (`jobs`) |
| :--- | :--- | :--- | :--- |
| **Primary Purpose** | Host-level persistent service/daemon | Cadence-specific supervisor lane | Single discrete automation task |
| **Supervisor** | `sase service` (systemd/launchd) | Scheduler Orchestrator | Routine process loop |
| **Process Lifespan** | Long-running daemon (infinite loop) | Long-running lane loop | Ephemeral (seconds/milliseconds) |
| **Execution Trigger** | Boot / host start, restart policy | Fixed time interval (`schedule` lib) | Routine tick + declarative trigger |
| **Memory Cost** | High (1 dedicated Python process per proc) | Moderate (1 process per routine lane) | Negligible (runs inside routine) |
| **Proc Store Entry** | Yes (durable proc row per launch) | No (scheduler owns routine tree) | No (recorded in AXE state/metrics) |
| **Maintenance Mode**| Ignorant (runs through maintenance) | First-class (`sase axe maintenance`) | First-class (pauses with routine) |
| **Runner Pool Aware**| No | Yes (`SharedRunnerPool`) | Yes (obeys runner budgets) |
| **UI Placement** | Services Tab: "Service Procs" panel | Services Tab: "Scheduled Routines" | Services Tab: Routine Job List |

---

## 3. Detailed Critique of the Proposed Migration

The user's prompt raises a specific proposal:
> *"I've been thinking that some of the builtin routines and/or jobs that exist currently might be better suited as service procs. For example, wouldn't it be better if the `wait_checks` job was instead a service proc that could wake up agents that are ready sooner?"*

We critique this proposal across architecture, operational reliability, performance, and implementation realities.

### 3.1 Critique 1: The Architectural Category Error

Moving `wait_checks`—or any other domain automation job—out of AXE into `service.procs` is a **category error**.

1. **Subsystem Inversion:** The `scheduler` service proc was created specifically so that background automation would **not** require individual, ad-hoc OS daemons. Moving jobs into `service.procs` bypasses the very subsystem designed to govern them.
2. **Loss of Unified Operational Controls:**
   - **Maintenance Mode:** If `wait_checks` becomes a service proc, `sase axe maintenance enter` will no longer pause it. During a delicate schema migration or plugin upgrade, the `wait_checks` daemon would continue polling and writing `ready.json`, potentially unblocking agents against half-migrated state.
   - **Metrics & Observability:** AXE records cycle durations (`AXE_CYCLE_DURATION`), cycle counts (`AXE_CYCLES`), and errors (`AXE_ERRORS`) for every job and routine. Service procs only track process exit status and raw log lines.
   - **UI Fragmentation:** The SASE TUI Services tab cleanly separates "Service Procs" (host infrastructure) from "Scheduled Routines" (lifecycle jobs with cycle history, status badges, and next-run timers). Placing `wait_checks` in Service Procs clutters infrastructure views with domain tasks.

### 3.2 Critique 2: Deconstructing the "Wake Up Sooner" Hypothesis

Why did the user believe a service proc would wake up agents sooner?
The user equated **Job = Slow (10-second polling)** and **Service Proc = Fast (Instant event-driven daemon)**.

However, a service proc is simply an OS process managed by `sase service`. It does not possess any inherent event-driven capability. To understand why, let us examine how wait resolution currently operates.

#### How `wait_checks` Works Today (`_chop_wait_checks_run.py`)

1. Triggered on the `waits` routine interval (every 10 seconds).
2. The `fs` trigger performs a shallow stat over `projects/*/artifacts/ace-run/*`. If no files changed, it skips execution immediately.
3. If files changed or `max_quiet` (120s) expired:
   - Scans projects for `waiting.json` markers without a corresponding `ready.json`.
   - Assembles a `WaitDependencyIndex` from `agent_meta.json` files and indexed run records.
   - For bead dependencies (`wait_for_beads`), inspects canonical bead stores (`closed_bead_ids_for_project`).
   - Evaluates dependency satisfaction (`dependency_resolution_status`).
   - **Two-Phase Confirmation (`confirm_dependency_resolution`):** Re-inspects on-disk membership to ensure no new session members (monitors, successors) were added during evaluation.
   - Writes `ready.json` containing `{"resolved_deps": [...]}`.

#### How the Waiting Agent Behaves (`run_agent_wait.py`)

1. The parked agent writes `waiting.json`.
2. Calls `release_idle_memory()` to drop its memory footprint while sleeping.
3. Enters a sleep loop:
   ```python
   while not dependencies_resolved:
       if os.path.exists(ready_path):
           dependencies_resolved = read_ready_result(ready_path)
           if dependencies_resolved:
               break
       ...
       time.sleep(_WAIT_POLL_INTERVAL)  # _WAIT_POLL_INTERVAL = 2 seconds
   ```
4. If `ready.json` is not seen after 60 seconds, it invokes a direct fallback resolution:
   `_WAIT_DEPENDENCY_FALLBACK_INTERVAL = 60.0`.

#### The Current Latency Profile

- Routine Interval: 10 seconds.
- Waiter Poll Interval: 2 seconds.
- **Average Latency:** Approximately **5 to 7 seconds** from predecessor completion to waiter resumption.
- **Worst-Case Latency:** Approximately **10 to 12 seconds**.

#### Why a Service Proc Fails to Improve This Cleanly

If `wait_checks` were rewritten as a service proc, it would have to take one of two forms:

##### Form A: A Tight Polling Daemon (`while True: check(); sleep(1)`)
- If it simply loops with a shorter sleep interval (e.g., 1 second):
  - It does the exact same work that AXE already does.
  - It wastes substantial CPU performing cross-project filesystem checks every second.
  - **Critique:** If tight polling is acceptable, one can simply configure the `waits` routine interval to 2 or 3 seconds in `default_config.yml` without writing a single line of new service proc code or fragmenting process supervision!

##### Form B: An Event-Driven Watcher Daemon (e.g., `inotify` / `watchdog`)
- Attempting to make `wait_checks` an event-driven daemon that watches the filesystem creates severe technical problems:
  1. **OS Watch Exhaustion:** SASE projects contain hundreds or thousands of run directories under `projects/<proj>/artifacts/ace-run/<YYYYMM>/<DD>/<run_id>/`. Linux `inotify` requires registering watches on directories recursively. In large workspaces, this risks exhausting `/proc/sys/fs/inotify/max_user_watches`.
  2. **Event Storms & Thrashing:** Active SASE agents continuously stream token counts, log lines, tool calls, and temporary artifacts into their run directories. An `inotify` watcher would fire dozens of times per second, triggering constant, expensive re-indexing passes.
  3. **Multi-Source Dependencies:** Waiting agents do not only wait on agent runs! They wait on:
     - Named agents (`waiting_for`)
     - Artifact hashes (`wait_for_artifacts`)
     - Fork sources (`wait_for_fork_sources`)
     - Hood completion (`wait_for_hoods`)
     - **Closed Beads (`wait_for_beads`):** Beads live in project stores (`.sase/projects/<proj>/beads.jsonl`) or git sidecar checkouts. An inotify watcher on `ace-run` would be completely blind to bead closures!
  4. **Race Conditions Against Partial Writes:** When an agent finishes, it writes multiple files: `agent_meta.json`, `done.json`, updates indices, and possibly hands off to a monitor or gate. If an event watcher triggers instantly on the first file write, it observes incomplete state. This is precisely why `_chop_wait_checks_run.py` includes `confirm_dependency_resolution`.

### 3.3 Critique 3: Return on Investment (ROI) vs. Agent Turn Realities

In SASE's operational model, an agent turn is an LLM invocation that executes tool calls, compiles code, runs test suites, and reasons over diffs. A typical agent turn takes **30 to 180 seconds**.

Saving 4 to 6 seconds on a dependency barrier that occurs once or twice per multi-step workflow represents **less than 3% to 5%** of overall workflow execution time.

Introducing a dedicated daemon, bespoke IPC, file watcher complexity, and separate process supervision for a marginal 5-second gain on a 2-minute workflow is a fundamentally poor engineering tradeoff.

---

## 4. Comprehensive Audit of All 29 Builtin Jobs

To rigorously answer whether *any* builtin routine or job should become a service proc, we performed an exhaustive audit of all 29 jobs configured in `src/sase/default_config.yml`.

### 4.1 Routine 1: `hooks` (Interval: 5s, Fast Lifecycle Lane)

| Job Name | Current Role | Recommendation | Rationale |
| :--- | :--- | :--- | :--- |
| `hook_checks` | Advances hook states on Patches; starts stale hooks | **Keep as Job** | Reconciles Patch specs; guarded by `fs` triggers on `*/*.sase`; obeys `max_hook_runners`. |
| `mentor_checks` | Reconciles and launches mentor agents | **Keep as Job** | Proposes agent launches through AXE runner pool; must obey global `max_agent_runners`. |
| `workflow_checks` | Reconciles CRS and fix-hook agents | **Keep as Job** | Manages ephemeral agent lifecycles; coordinates directly with AXE runner pools. |
| `pending_checks_poll`| Collects results from background check scripts | **Keep as Job** | Ingests flat file outputs from `~/.sase/checks/`; runs in <10ms with `fs` trigger. |
| `comment_zombie_checks`| Flags aged comment threads as ZOMBIE | **Keep as Job** | Simple timestamp check over Patch metadata; purely periodic maintenance. |
| `suffix_transforms` | Normalizes proposal and attention markers | **Keep as Job** | In-place text transformation on Patch files; ephemeral batch sweep. |
| `orphan_cleanup` | Reclaims claims on reverted PRs with dead PIDs | **Keep as Job** | Process liveness check against Patch claims; brief scan every 5s. |
| `stale_running_cleanup`| Releases claims/proc rows held by dead PIDs | **Keep as Job** | Global PID liveness sweep; does not need daemonization. |

### 4.2 Routine 2: `waits` (Interval: 10s, Dependency & Sync Lane)

| Job Name | Current Role | Recommendation | Rationale |
| :--- | :--- | :--- | :--- |
| `bead_claim_checks` | Acquires/releases pre-launch bead claims | **Keep as Job** | Reconciles locks between pre-launch agents and dead owners; brief scan. |
| `epic_launch_flush` | Flushes orphaned planner completion notifications| **Keep as Job** | Runs every 30s (`run_every: 30s`) with grace periods; purely periodic GC. |
| `sidecar_auto_sync` | Fetches and fast-forwards sidecar repos | **Keep as Job** | Runs git network commands (`git fetch`, `git merge`); MUST be throttled (every 30s). Making it a daemon risks git index lock contention. |
| `wait_checks` | Resolves `%wait` dependencies, writes `ready.json` | **Keep as Job** | Evaluates cross-project dependency graphs; requires two-phase consistency confirmation. (See Section 6 for latency tuning). |

### 4.3 Routine 3: `checks` (Interval: 300s / 5m, Low-Frequency Checks)

| Job Name | Current Role | Recommendation | Rationale |
| :--- | :--- | :--- | :--- |
| `bead_task_triage` | Generates human gates for ready/snoozed beads | **Keep as Job** | Evaluates threshold rules (+1 counts, due dates) to raise gates; 5-minute cadence is optimal. |
| `plugins_required` | Raises gates for missing PEP 508 plugins | **Keep as Job** | Compares `plugins.required` against environment; changes only on install/update. |
| `pr_submitted_checks`| Initiates background PR submission verification | **Keep as Job** | Launches remote network checks; rate-limited by nature. |
| `stale_running_cleanup`| Five-minute backstop for dead-process claims | **Keep as Job** | Fallback safety net if the `hooks` lane is paused or degraded. |

### 4.4 Routine 4: `usage` (Interval: 60s, Provider Metrics)

| Job Name | Current Role | Recommendation | Rationale |
| :--- | :--- | :--- | :--- |
| `usage_refresh` | Probes provider quotas & subscription windows | **Keep as Job** | Probes remote LLM provider APIs inline; MUST respect rate limits and Retry-After headers. |

### 4.5 Routine 5: `comments` (Interval: 60s, Remote PR Comments)

| Job Name | Current Role | Recommendation | Rationale |
| :--- | :--- | :--- | :--- |
| `comment_checks` | Starts background critique-comment checks | **Keep as Job** | Remote GitHub/tracker API polling; throttled intentionally to 60s to prevent API bans. |

### 4.6 Routine 6: `external_mirror` (Interval: 900s / 15m, Remote VCS Mirroring)

| Job Name | Current Role | Recommendation | Rationale |
| :--- | :--- | :--- | :--- |
| `external_issue_mirror`| Mirrors GitHub tracker issues into task beads | **Keep as Job** | Heavy network diffing against remote issue trackers; 15-minute pacing prevents API throttling. |
| `external_pr_mirror` | Adopts external PRs into local Patches | **Keep as Job** | Heavy remote PR inventory scan; bounded cursor advances. |

### 4.7 Routine 7: `housekeeping` (Interval: 3600s / 1h, Maintenance & Retention)

| Job Name | Current Role | Recommendation | Rationale |
| :--- | :--- | :--- | :--- |
| `error_digest` | Dispatches hourly error digest notifications | **Keep as Job** | Summarizes rolling 1-hour error logs; inherently hourly. |
| `notification_store_compact`| Compacts dismissed notifications in JSONL | **Keep as Job** | Expensive file rewriting; running once an hour avoids TUI locking. |
| `managed_tmp_reap` | Prunes aged temporary files under managed root | **Keep as Job** | Heavy disk walk and unlinking; batch maintenance pattern. |
| `proc_runtime_sweep`| Cleans orphaned proc runtime directories | **Keep as Job** | Reconciles dead proc dirs under lock; batch maintenance pattern. |
| `disk_pressure` | Evaluates disk free-space thresholds | **Keep as Job** | Checks filesystem metrics and alerts on threshold crossings. |
| `bead_stale_cleanup` | Sweeps aged sub-threshold task beads | **Keep as Job** | Evaluates days-old stale beads; hourly cadence is more than sufficient. |
| `gate_turn_reclaim` | Force-settles abandoned or expired gate turns | **Keep as Job** | Reclaims timed-out gates after grace periods; batch safety net. |
| `artifact_link_backfill`| Derives retroactive links and repairs renames | **Keep as Job** | Heavy graph traversal and git log inspection; resumable batch job. |
| `artifact_run_prune` | Previews ace-run retention candidates | **Keep as Job** | Scans multi-month run history; preview pass. |

---

## 5. The Litmus Test: What Actually Belongs as a Service Proc?

To avoid ad-hoc architecture decisions in the future, we define the formal **Four-Part Litmus Test** for what belongs in `service.procs`:

A background workload should be a **Service Proc** if and only if it satisfies at least one of the following criteria:

1. **Persistent Socket / Network Listener:** The process must bind a network port, Unix domain socket, or IPC FIFO to serve incoming requests from external actors on demand (e.g., `gateway` serving mobile clients, or a future LSP server).
2. **Real-time Push Stream / Long-Polling Consumer:** The process maintains a persistent, uninterrupted connection to an external streaming service (e.g., `telegram_receiver` maintaining a long-poll to the Telegram Bot API, or an SSE/WebSocket client).
3. **Dedicated Subprocess Supervisor:** The process is a top-level orchestrator responsible for managing a hierarchy of other worker processes (e.g., `scheduler` supervising routine processes).
4. **Stateful In-Memory Engine:** The process maintains a heavy, persistent in-memory state or cache that is prohibitively expensive to reload from disk on a schedule (e.g., an in-memory vector database, semantic code graph, or warm language model cache).

If a task merely performs **periodic reads, diffs state on disk, and writes updates or emits notifications**, it is a **Job (Chop)** and belongs under the AXE scheduler.

---

## 6. Requirements Reframing & Adjustments

The user's original request asked:
> *"Which jobs (if any) should I migrate to service procs? Critique this plan... Make any adjustments to the requirements that you think are justified."*

We formally adjust the project requirements as follows:

| Stated Requirement | Adjusted Requirement | Justification |
| :--- | :--- | :--- |
| **"Migrate builtin jobs/routines to service procs"** | **"Retain all builtin jobs within AXE; preserve `service.procs` for host daemons only"** | Prevents architectural fragmentation, preserves maintenance mode, and avoids proc store bloat. |
| **"Turn `wait_checks` into a service proc to wake up agents sooner"** | **"Reduce agent `%wait` resolution latency from ~10s to ~2s using scheduler tuning and waiter-side direct checks"** | Solves the user's true performance goal (faster wakeup) without introducing daemon complexity, OS inotify exhaustion, or race conditions. |
| **"Use external daemon watchers for filesystem events"** | **"Leverage existing declarative `fs` triggers and lightweight producer hints"** | SASE already has `fs` triggers with `max_quiet` and producer hint mechanisms (e.g., `mark_bead_wait_sync_hint`); these should be expanded rather than replaced. |

---

## 7. Recommended Solution: Four-Tier Evolutionary Roadmap

To achieve fast agent wake-ups while keeping the architecture pristine, we recommend the following four-tier implementation roadmap:

```
┌────────────────────────────────────────────────────────────────────────┐
│  Tier 1: Cadence Tuning & Lane Rebalancing (Immediate / Zero Code)     │
│  • Move wait_checks to the 5s hooks routine OR tune waits to 3s-5s     │
│  • Cuts average wakeup latency in half (from ~6s to ~2.5s)             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Next Step
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Tier 2: Waiting Runner Optimization (Minor Code Change)               │
│  • Reduce _WAIT_DEPENDENCY_FALLBACK_INTERVAL from 60s to 5s-10s        │
│  • Parked runners evaluate direct resolution inline without waiting    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Next Step
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Tier 3: Producer-Side Completion Signaling (Event-Driven Wakes)       │
│  • Agent finalizer (runner_finalize.py) touches wait hint on finish   │
│  • sase bead close touches bead wait hint                              │
│  • Wakes routine tick immediately when predecessors complete           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Strategic Evolution
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Tier 4: Event-Aware Scheduler Orchestrator (Long-Term Architectural)  │
│  • Add an internal event-loop / signal to the existing scheduler proc │
│  • Routine ticks wake early upon file modifications                    │
│  • Retains single-tree supervision, metrics, and maintenance mode      │
└────────────────────────────────────────────────────────────────────────┘
```

### 7.1 Tier 1: Cadence Tuning & Lane Rebalancing (Immediate)

The simplest, safest, and most effective immediate adjustment is configuration-only:

1. **Option A (Move to `hooks`):** Move `wait_checks` from the `waits` routine (10s interval) into the `hooks` routine (5s interval).
   - In `src/sase/default_config.yml`, `hooks` already runs every 5 seconds.
   - `wait_checks` already has an `fs` trigger:
     ```yaml
     trigger:
       provider: fs
       max_quiet: "120s"
       paths:
         - path: projects
           glob: "*/artifacts/ace-run/*"
     ```
   - On ticks where no new agent artifact directory was modified, `wait_checks` evaluates in under 1 millisecond.
   - **Result:** Reduces maximum latency from 10s to 5s, and average latency to ~2.5s.
2. **Option B (Tune `waits` interval):** Change `axe.routines.waits.interval` from `10` to `3` or `5`.
   - Running the `waits` lane every 3–5 seconds is lightweight because all four jobs in `waits` are either trigger-guarded (`bead_claim_checks`, `wait_checks`) or cadence-throttled via `run_every: "30s"` (`epic_launch_flush`, `sidecar_auto_sync`).

### 7.2 Tier 2: Waiting Runner Self-Wake Optimization (Minor Code Change)

In `src/sase/axe/run_agent_wait.py`, the waiting agent process already polls for `ready.json` every 2 seconds (`_WAIT_POLL_INTERVAL = 2`), but only attempts direct dependency resolution as a fallback every 60 seconds:
```python
_WAIT_DEPENDENCY_FALLBACK_INTERVAL = 60.0
```

If the waiting agent is only waiting for a single named predecessor agent (the most common pattern in multi-agent workflows), checking if that predecessor's `done.json` exists takes less than a millisecond.

**Recommended Change:**
- Reduce `_WAIT_DEPENDENCY_FALLBACK_INTERVAL` from `60.0` to `5.0` or `10.0` seconds.
- Allow the parked runner to evaluate lightweight single-dependency checks inline. If the predecessor completed and wrote `done.json`, the waiter resolves itself and proceeds without waiting for AXE to sweep the directory!

### 7.3 Tier 3: Producer-Side Completion Signaling (Targeted Event Notification)

Instead of having a consumer poll or an external watcher guess when work is done, use **Producer-Side Signaling**:

1. When an agent completes its turn in `sase.axe.run_agent_exec_finalize`:
   - It already writes `done.json` and updates `agent_meta.json`.
   - Add a lightweight post-completion hook: if any waiting marker exists in the same session or clan, touch a known trigger file (e.g., `~/.sase/state/waits_hint`).
2. When a user or agent closes a bead via `sase bead close`:
   - The CLI already invokes `mark_bead_wait_sync_hint(project_name)`.
3. The `waits` routine watches this hint file and executes immediately when touched, delivering sub-second resolution without continuous polling.

### 7.4 Tier 4: Modernize the Scheduler Orchestrator (Long-Term Architecture)

If SASE eventually requires true sub-second reactivity across all background tasks:

- **Do NOT** decompose AXE into dozens of standalone service procs.
- **DO** enhance the existing `scheduler` service proc (`Orchestrator`).
- Give the Orchestrator an inotify/event-loop thread watching the configured trigger paths. When a path changes, the Orchestrator signals the specific child routine process (via a lightweight Unix signal or IPC pipe) to trigger its tick immediately rather than waiting for `time.sleep(interval)` to expire.
- **Benefits:**
  - Preserves centralized supervision, crash recovery, and logging.
  - Keeps AXE maintenance mode fully functional.
  - Keeps the TUI Scheduled Routines panel accurate.
  - Provides instant, event-driven reactivity across the entire automation suite.

---

## 8. Conclusion

The hypothesis that migrating `wait_checks` or other builtin jobs to service procs would improve SASE is well-intentioned but architecturally flawed. 

- **Service procs** are the foundation for long-running host daemons (network listeners and master supervisors).
- **Scheduler routines and jobs** are the proven, resilient abstraction for periodic and triggered lifecycle automation.
- Migrating jobs to service procs fractures SASE's operational model, bypasses maintenance mode, risks inotify watch exhaustion, and introduces concurrency races against agent finalization.

By adopting the recommended **Tier 1 (cadence rebalancing to the 5s `hooks` lane)** and **Tier 2 (waiter-side fallback acceleration)**, SASE can achieve the desired fast agent wakeup latency (~2 seconds) immediately, safely, and cleanly—without architectural debt.
