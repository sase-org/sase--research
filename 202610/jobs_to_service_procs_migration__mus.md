# Jobs → service procs: should anything migrate? (with `wait_checks` as the test case)

**Verdict up front: migrate nothing.** No builtin job — including `wait_checks` —
meets the bar for becoming a service proc. The proposal is a category error that
trades a crash-consistent, observable batch reconciler for a stateful daemon in
exchange for a latency win (~seconds) on waits that last minutes to hours. The
cheaper fix, if wake latency ever proves painful, is a completion-side
write-through plus (optionally) a tighter waits-lane interval — not a new
supervised daemon. Details and the concrete recommendation are at the end.

## 1. What the two things actually are

These are different axes, not two sizes of the same thing.

**Jobs** (`src/sase/axe/`, scripts in `src/sase/scripts/sase_job_*`, configured
under `axe.routines` in `src/sase/default_config.yml`) are short-lived,
script-only batch units. The runner execs `<script> --context <context.json>`,
streams stdout/stderr to a per-run log, enforces `timeout`/`job_timeout`,
supports `trigger` (notably `fs` + `max_quiet`), `run_every` cadence
throttles, `for_each` fan-out, dry-run, structured results with validated
agent-launch proposals, per-run history, and maintenance-mode skip. A crash
kills one tick; the next tick retries cleanly. There is no in-memory state to
go stale.

**Service procs** (`src/sase/service/`, durable rows in `src/sase/procs/`,
configured under `service.procs`) are long-lived supervised daemons (or
transient oneshots for `!` commands). The service host reconciles roughly every
second and restarts crashed daemons under a `restart: on-failure` policy with
1s→60s backoff; three failures in 60s marks the proc `crash_loop` and raises a
notification per episode (see "Supervision and Recovery" in `docs/axe.md`).
Only two builtin service procs exist today — `scheduler` and `gateway`
(`src/sase/procs/service_meta.py`, `RESERVED_BUILTIN_SERVICE_PROCS`) — and that
scarcity is a signal: daemon status is reserved for things that must *hold*
something open (the scheduler orchestrator holding routine children; the
gateway holding an HTTP port), not for things that periodically *scan*.

**Routines** are the middle layer the proposal tends to skip over: each routine
owns an interval, and each job inside it adds its own `trigger`/`run_every`.
The waits lane runs every 10s; the hooks lane every 5s; usage every 60s;
comments every 60s; checks every 5min; external_mirror every 15min;
housekeeping every hour (`src/sase/default_config.yml`, `docs/axe.md`
"Default Routines"). Migrating a job to a service proc does not just move
code — it leaves this entire guardrail package behind (timeouts, fs-trigger
skip, cadence clocks, run history, launch-proposal runner, TUI Services-tab
integration, maintenance skip) and reimplements supervision from scratch.

## 2. How `wait_checks` works today (the thing we'd be replacing)

- The waiting runner (`src/sase/axe/run_agent_wait.py::wait_for_dependencies`)
  writes `waiting.json`, then polls for `ready.json` every **2s**, with a
  coarse **60s** direct-resolution fallback
  (`waiting_marker_dependencies_resolved`) so a job outage cannot strand a
  runner forever, plus a 10-minute bead-sync-hint backstop.
- The `wait_checks` job (`src/sase/scripts/_chop_wait_checks_run.py`,
  handler `@builtin_chop("wait_checks")`) runs in the **waits lane every
  10s**, guarded by an `fs` trigger watching `*/artifacts/ace-run/*` with
  `max_quiet: 120s`, so idle ticks cost a handful of `stat()` calls instead of
  a scan. On a fire it scans waiting markers, resolves named-agent / artifact /
  closed-bead dependencies via the shared `wait_dependency_resolution` library
  (preferring the persistent agent-artifact index,
  `src/sase/scripts/_chop_incremental_index.py`, failing open to a filesystem
  walk), confirms against a fresh membership view (races counted as
  `deferred_unconfirmed`, not errors), and writes `ready.json` only when every
  dependency is satisfied.
- End-to-end wake latency is therefore bounded by roughly
  **waits-interval (≤10s) + runner poll (≤2s)** in the normal case, 60s via the
  runner fallback when the job is down.

Two facts matter for the proposal. First, the 10s bound is already a
*policy choice*, not an architectural ceiling — the lane interval is one line
of config. Second, the writer side already touches the exact tree the fs
trigger watches, so a completion usually fires the trigger on the next tick
rather than waiting out `max_quiet`.

## 3. Critique: what a `wait_checks` service proc would actually buy and cost

**The buy is small.** Waiters park for the duration of whole agent runs —
minutes to hours. Shaving ~5–10s off a multi-minute wait is unobservable to
the human and irrelevant to throughput: the freed runner still needs a slot
under the global agent cap, and downstream launch itself goes through the same
batched lifecycle. Nobody has produced a wake-latency histogram showing p95
pain; without that measurement this is optimization on intuition.

**The cost is real and recurring:**

1. **Supervision downgrade.** Today a `wait_checks` crash is a `check_error`
   row and a retry in ≤10s. As a daemon, the same bug kills the watcher; the
   host backs off (1s doubling to 60s) and after three fast failures parks it
   in `crash_loop` behind a notification. Every waiter during that window
   falls back to the 60s runner path — the migration makes the common case
   marginally faster and the failure case strictly worse.
2. **State staleness.** The job is stateless per tick (plus the persistent
   artifact index it already shares). A daemon's reason to exist is held
   in-memory state (open inotify watches, cached index); that state can split
   from disk after a restart, a clock jump, or a missed event, and now needs
   its own resync protocol — duplicating what the 10s tick already *is*.
3. **Fan-out and FD cost.** One job pass scans all projects only when the
   trigger fires. A daemon needs a watch per project artifact tree (plus
   bead-store and sidecar inputs for bead waits), debouncing, and per-project
   backoff — per-machine FD and thread overhead that scales with project count
   even when nothing is waiting.
4. **Lost runner contract.** Structured results, launch proposals, dry-run,
   per-run logs, overrun accounting, `sase axe job run` manual replay, and the
   TUI Services-tab job rows all belong to the job runner. A service proc gets
   none of it; debugging "why is this agent still parked?" moves from a
   timestamped run log to tailing a daemon log.
5. **It cannot "wake" anyone anyway.** Parked runners block in
  `time.sleep(2)` polling `ready.json`. A daemon has no handle to
   signal them with; its only channel is the same `ready.json` write the job
   does today. "Wake up agents that are ready sooner" therefore reduces to
   "write `ready.json` sooner" — a scheduling question, answered equally well
   by a tighter interval or a write-through (Section 5), with no daemon
   required.

The same logic disposes of the general program ("some builtin routines and/or
jobs might be better as service procs"). Batch reconcilers with idempotent
passes, bounded per-pass budgets, and fail-open-to-next-tick semantics are
exactly what the job model is for. Daemon semantics pay off for servers that
hold connections or stream continuously. No builtin job does either.

## 4. Lane-by-lane triage: is there *any* job worth migrating?

Criterion applied uniformly: migrate only if the job (a) must hold a live
resource across ticks (socket, tail, lease), (b) has a measured sub-second
SLA the tick cannot meet, and (c) has an event source with no filesystem
proxy (so the fs trigger cannot express it). Result: **none qualify.**

| Lane / job(s) | Cadence | Why it stays a job |
|---|---|---|
| hooks: `hook_checks`, `mentor_checks`, `workflow_checks`, `pending_checks_poll`, `comment_zombie_checks`, `suffix_transforms`, `orphan_cleanup` | 5s + fs triggers | The hottest lane already wakes on ProjectSpec / checks-dir writes. A daemon saves milliseconds on second-scale lifecycle steps while inheriting all Section-3 costs. |
| hooks/waits/checks: `stale_running_cleanup` (fast lane + 5min backstop) | 5s / 5min | Explicitly keeps the `always` trigger because PID liveness has *no* fs proxy — the one case that looks daemon-shaped. But the fix is the dual placement (seconds in hooks, backstop in checks), which already covers a disabled fast lane. A daemon watching PIDs would just reimplement process polling with worse observability. |
| waits: `wait_checks`, `bead_claim_checks` | 10s + fs on `ace-run/*` | Closest call (see Section 3), still no: bounded by a config line, fails safe to the 60s runner fallback, and shares its resolution library with the runner. |
| waits: `epic_launch_flush`, `sidecar_auto_sync` | 10s lane, `run_every: 30s` | Self-throttling batch work with budgets and backoff; a daemon adds nothing. Note `sidecar_auto_sync` already hints bead-wait projects every tick — the event-driven fast path for bead waits exists *inside* the job model. |
| usage: `usage_refresh` | 60s, probes inline, creates no proc rows | Deliberately proc-less polling; daemonizing it creates the supervised process it was written to avoid. |
| comments/checks: `comment_checks` → `pending_checks_poll` → `pr_submitted_checks` | 1min / 5s / 5min | A launch/collect split across lanes with a 5-minute remote cache. A daemon does not reduce a single API call; it only moves the throttle. |
| external_mirror (issue/PR) | 15min, per-project fan-out, backoff, creation caps | Remote polling with cursors and repair scans — textbook batch job; daemon form would hold nothing and poll identically. |
| housekeeping: digests, compaction, reapers, sweeps, backfills, prunes | 1hr | Latency-insensitive maintenance with per-pass budgets and checkpoints (`artifact_link_backfill` resumes across ticks). Long-lived state is pure liability here. |

The two existing service procs confirm the rule: `scheduler` supervises
children and `gateway` serves HTTP. Neither scans-and-exits; neither could be
a job.

## 5. Adjustments to the requirements (called out as requested)

1. **Downgrade "migrate" to "measure first."** Before any migration, record
   waiter wake latency (done.json mtime → ready.json mtime → runner exit) for
   a week and require p95 pain attributable to the 10s tick. I expect it to
   show the tick is noise next to run durations; if it does not, the data
   picks the interval.
2. **Keep the polling path as a permanent backstop.** The runner's 60s
   fallback and the job's fail-open index handling assume a stateless
   reconciler always exists. Any fast path must be *additive*: never delete
   `wait_checks` the job, even if a notifier is added beside it.
3. **If latency must improve, prefer write-through over watchers.** The
   completing agent's finalization (which writes `done.json`) is the one place
   that knows *exactly* which dependency just resolved. A small, shared-library
   call there — resolve direct dependents via `wait_dependency_resolution` and
   write their `ready.json` inline — is a targeted O(dependents) write with no
   new supervised process, no watches, no debounce protocol. The periodic job
   stays as the reconciler for races the write-through misses (the membership
   confirmation in `_chop_wait_checks_run.py` already anticipates exactly this
   race).
4. **Treat interval tuning as the second lever, not migration.** 10s → 5s on
   the waits lane (or a narrower fs trigger) is a one-line change with the full
   existing observability story. Only if both write-through and interval
   tuning prove insufficient should anyone price a daemon — and that price
   must include the resync protocol, the FD/watch budget, and replacement
   run-history UX.

## 6. Recommended solution

1. **Migrate zero jobs to service procs.** Close the general program; record
   this note's criterion (Section 4) as the standing bar so the next proposal
   starts from measurement, not intuition.
2. **Leave `wait_checks` exactly where it is** — a 10s waits-lane job with its
   fs trigger, incremental index, membership confirmation, and runner-side
   60s fallback intact.
3. **If wake latency is felt rather than measured, do these in order and stop
   when the pain stops:** (a) add waiter wake-latency counters to the existing
   job summary; (b) implement completion-side `ready.json` write-through in the
   finalization path using the same resolution library (job remains the
   backstop); (c) only then consider tightening the waits interval.
4. **Do not add a `waiter`/`wait_watcher` service proc**, even as a
   complement: an additive notifier that shares nothing with the reconciler
   creates two writers for `ready.json` and a new class of "notifier said
   ready, reconciler disagrees" bugs, in exchange for seconds on hour-scale
   waits.

*Scope note: this is a code-and-docs analysis (default config, `docs/axe.md`,
`run_agent_wait*`, `_chop_wait_checks_*`, `_chop_incremental_index.py`,
`service/*`, `procs/service_meta.py`). I ran no latency benchmarks; the
"measure first" step above is load-bearing, not rhetorical.*
