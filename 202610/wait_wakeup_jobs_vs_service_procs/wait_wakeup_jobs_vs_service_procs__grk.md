---
create_time: 2026-10-07
updated_time: 2026-10-07
status: draft
tags:
  [
    research_swarm,
    jobs,
    service-procs,
    scheduler,
    wait_checks,
    routines,
  ]
---

# Should builtin jobs become service procs?

**Question.** Some builtin routines and jobs might be better as service procs.
`wait_checks` is the motivating example: a service proc could wake agents that
are ready sooner. Recommend which jobs, if any, to migrate. Critique the plan.
Propose a different approach if it is better. Adjust requirements that would
make the migration unreliable, and call those adjustments out.

**Researcher.** grk. Independent report. I did not locate, open, read, or
otherwise consult peer reports from this swarm.

## Bottom line

**Do not migrate builtin jobs to service procs.** The motivating need — wake a
parked waiter as soon as its dependency is actually done — is real, and
`wait_checks` is currently slower than its 10-second lane advertises. The
wrong remedy is a new daemon.

`wait_checks` is already a short script inside a long-lived routine process
inside the `scheduler` service proc. Promoting it to a peer of the scheduler
does not wake anyone. Parked runners poll `ready.json` every two seconds. A
new service proc that still writes `ready.json` still waits on that poll, and
it loses job history, `sase axe job run`, structured results, maintenance
mode, and crash isolation that the waits routine already provides.

The latency bug is more specific than "jobs poll." After day-sharding of
`ace-run`, the shipped `fs` trigger watches month directories
(`projects/*/artifacts/ace-run/*`). Writing `done.json` inside
`ace-run/YYYYMM/DD/<timestamp>/` does not change that token. The trigger then
relies on `max_quiet: "120s"`. The parked runner's own fallback already
re-resolves every 60 seconds, so `wait_checks` is often not even the fast
path.

**Recommended solution:** keep every shipped job as a job. Add a
completion-side poke on the existing `done.json` / bead-close write paths so
satisfied waiters get `ready.json` in milliseconds. Keep `wait_checks` as the
periodic backstop, confirmation pass, and terminal-blocker notifier. Optionally
cut the remaining two-second runner poll with inotify on `ready.json`. Treat
event-driven *job triggers* inside the scheduler as a later general facility,
not a catalog of new service procs.

The one completed analog of "this job became a service proc" is Telegram's
inbound receiver: a long-lived exclusive `getUpdates` consumer. That is the
litmus. None of the remaining builtins match it.

## Verdict on the idea

The instinct is right about *latency* and wrong about *process type*.

SASE already has three long-lived layers:

| Layer | What it is | Lifetime |
| --- | --- | --- |
| Service host | One per machine (`sase service run`) | Platform unit |
| Service proc | Named daemon the host owns | Until stop / crash-loop / disable |
| Routine | Scheduler child that ticks jobs | Until scheduler stop; restarted on crash |

Jobs are the finite work those routines run. The glossary is blunt: a job is
"one short, script-only unit of scheduler automation"; a service proc is a
named proc the sase service owns, `daemon` or `oneshot`. Config entries are
daemons. Oneshots are transient `sase service proc run` / TUI `!` commands.

`wait_checks` as a service proc would mean: a second machine-level daemon,
with its own restart policy, Services-tab row, crash-loop notification, and
`after:` ordering, whose job is still "scan markers and write `ready.json`."
That is a category error. The waits *routine* is already the long-lived
process. If the work needs an event loop, give that loop to the routine or to
the writer of `done.json`. Do not mint a new supervisor object.

The product has already used service procs for the right cases:

- `scheduler` — the automation daemon (builtin, enabled).
- `gateway` — HTTP server for mobile (builtin, disabled by default).
- `telegram_receiver` — exclusive Telegram long-poll (`sase_job_tg_inbound --receiver`, plugin, disabled by default).

Those hold a socket or an exclusive remote consumer. `wait_checks` holds
neither.

## What actually unblocks a waiter today

A `%wait` launch parks a runner process. The barrier is in
`src/sase/axe/run_agent_wait.py`:

1. **Immediate resolve.** `initial_dependencies_resolved` runs before parking.
   If the dependency is already done, the agent never waits.
2. **Park and poll.** The runner writes `waiting.json`, then sleeps 2 seconds
   at a time watching for `ready.json`.
3. **`wait_checks`.** The waits routine (interval 10s) runs the job, which
   scans waiting markers and writes `ready.json` when every named-agent,
   artifact, hood, and closed-bead dependency is satisfied *and* a
   post-resolution membership confirmation still holds.
4. **Coarse fallback.** Every 60 seconds the parked runner re-resolves the
   same dependency set itself, so a job outage cannot strand it forever.
   Bead-sidecar hints from the runner are coarser still (10 minutes).

`wait_checks` also emits the "never self-resolve" notification for terminal
blockers. That is observer work, not wakeup work.

So "wake agents sooner" has two clocks, not one:

- How soon `ready.json` appears after the dependency lands.
- How soon the parked runner notices `ready.json` (up to 2 seconds, plus a
  60-second fallback if `ready.json` never appears).

A service proc that only replaces step 3 addresses the first clock, and only
if it is actually event-driven. Replacing a 10-second job with a daemon that
still polls is theatre.

## The fs trigger does not see `done.json`

This is the load-bearing finding.

Shipped config (`src/sase/default_config.yml`):

```yaml
wait_checks:
  trigger:
    provider: fs
    max_quiet: "120s"
    paths:
      - path: projects
        glob: "*/artifacts/ace-run/*"
```

`docs/axe.md` describes that glob as "an idle tick only re-scans when a
project gains a new agent artifact." That sentence was true of the legacy
layout `ace-run/<timestamp>/`. It is not true of the current layout.

sase-core `agent_scan/layout.rs`:

```text
projects/<project>/artifacts/ace-run/YYYYMM/DD/<timestamp>/
```

The fs token (`_fs_watch_token` in `chop_policy_snapshots.py`) shallow-globs
from `~/.sase/projects` and, for each match, records name, mtime, size, and
immediate child count. `*/artifacts/ace-run/*` matches **month shards**, not
agent directories.

Writing `done.json` creates a file inside the timestamp directory:

- timestamp-dir mtime changes
- day-dir mtime does not (no directory entry added there)
- month-dir mtime and child count do not

The trigger therefore does **not** fire on the event `wait_checks` exists to
observe. The same glob is on `bead_claim_checks`.

The shipped test `test_artifact_glob_chops_skip_idle_and_fire_on_new_agent_artifact`
creates `ace-run/202601/20260101_120500_agent-name` as a *direct child of the
month shard*. That is not the canonical day-sharded path. The test proves the
trigger fires when a new directory appears under `YYYYMM`. In production that
is a new **day**, not a new agent, and not a `done.json`.

What actually fires `wait_checks` today:

| Event | Fires fs trigger? |
| --- | --- |
| First agent of a new month | Yes (new glob match) |
| First agent of a new day | Yes (month child count) |
| New agent later the same day | No |
| `done.json` / `waiting.json` write | No |
| Bead close in the beads sidecar | No |
| `max_quiet` 120s | Yes, unconditionally |

The waits routine still wakes every 10 seconds and *evaluates* the trigger.
The job itself is skipped. Worst case before `max_quiet` is two minutes.
The runner fallback at 60 seconds is then the real wakeup path.

`hook_checks` does not have this bug: it globs `projects/*/*.sase`, which are
the files hooks actually mutate, so a ProjectSpec write changes the token on
the next 5-second tick. `pending_checks_poll` globs the check result files
themselves. `wait_checks` is the mismatch.

## Litmus: when a job should become a service proc

Migrate a job to a service proc only when **all** of these hold:

1. The work is a long-lived loop or listener, not a finite scan.
2. The process must own an exclusive resource (socket, `getUpdates` offset,
   single-writer connection) that two overlapping job ticks would corrupt.
3. Its lifecycle should be enable/disable/restart **independent** of the
   scheduler (a machine that stops automation should still serve mobile, or
   still receive Telegram).
4. Losing job features is acceptable: `run_every`, `trigger`, `inhibit_if`,
   `for_each`, structured launch proposals, run history under
   `~/.sase/axe/lumberjacks/…`, `sase axe job run`, maintenance-mode pause.

Telegram inbound is the existence proof. The plugin ships
`sase_job_tg_inbound` in two modes: `--once` (legacy job tick) and
`--receiver` (daemon). `service.procs.telegram_receiver` runs the latter.
Telegram allows one `getUpdates` consumer. Two overlapping ticks would steal
updates. The receiver does not inherit AXE routine `env:`; it has its own.
Outbound (`sase_job_tg_outbound`) stayed a job: it is a finite "send unsent
notifications" pass.

The service-host epic (`202609/service_host_sunset.md`) exists to guarantee
**one supervisor per child**. Adding a `wait_checks` daemon next to the
scheduler re-opens "who restarts this, and does `sase axe maintenance`
pause it?" for a scan that the waits routine already supervises.

A later plan (`202609/unread_ack_reliability_and_tui_responsiveness.md`)
explicitly deferred moving remote-attention sync into a service proc until
measurements showed the current path still cost UI time. That is the right
bar: measure, then maybe a daemon. Not taxonomy.

`usage_refresh` already considered and rejected procs: it "probes inline in
the job process instead of submitting a proc, so periodic collection creates
no proc rows."

## Builtin catalog

Shipped jobs, grouped by whether they could plausibly be daemons.

### Do not migrate — finite reconciliation on a cadence

These are the whole default catalog except as noted below.

**hooks (5s).** `hook_checks`, `mentor_checks`, `workflow_checks`,
`pending_checks_poll`, `comment_zombie_checks`, `suffix_transforms`,
`orphan_cleanup`, `stale_running_cleanup`. Latency-sensitive Patch
lifecycle. The ProjectSpec `fs` trigger already fires on the files they
mutate. `stale_running_cleanup` is `always` because a dead PID has no
filesystem proxy; a 5-second always-on scan is the point of the fast lane,
with a 5-minute copy in `checks` as backstop. A daemon watching `/proc`
would be more code for the same "seconds, not minutes" SLA.

**waits (10s).** `wait_checks`, `bead_claim_checks`, `epic_launch_flush`
(`run_every: 30s`), `sidecar_auto_sync` (`run_every: 30s`). See the
wakeup design below. `sidecar_auto_sync` is git fetch/fast-forward with a
bounded budget and backoff. That is a job. Hinting beads for live waiters
every 30 seconds is already the "wake sooner" valve for sidecar lag.

**checks (5m).** `bead_task_triage`, `plugins_required`,
`pr_submitted_checks`, `stale_running_cleanup`. Human gates and remote PR
probes. Five minutes is the product cadence. A daemon would poll the same
stores more often and raise more duplicate-gate risk.

**usage (60s).** `usage_refresh`. Provider HTTP probes with cooldown and
Retry-After. Explicitly not a proc.

**external_mirror (15m).** `external_issue_mirror`, `external_pr_mirror`.
Remote tracker pagination with per-project `for_each`, checkpoints, and
backoff. Job features (`for_each`, independent instance cadence) are load
bearing. A service proc would have to reimplement fan-out.

**comments (60s).** `comment_checks`. Starts background critique fetches;
`pending_checks_poll` consumes results. Splitting launch from consume across
lanes is a job-scheduler pattern, not a daemon pattern.

**housekeeping (1h).** `error_digest`, `notification_store_compact`,
`managed_tmp_reap`, `proc_runtime_sweep`, `disk_pressure`,
`bead_stale_cleanup`, `gate_turn_reclaim`, `artifact_link_backfill`,
`artifact_run_prune`. Bounded maintenance. Hourly on purpose. `artifact_run_prune`
is preview-only. None of these should occupy a Services-tab daemon.

`refresh_docs` is a discoverable script with `git.commits_since` and
`for_each` in the docs example. It is not a default routine job. Leave it.

`stale_running_cleanup` appears in two lanes (hooks + checks). That
duplication is a reliability pattern (fast path plus backstop). Two service
procs, or one daemon plus a job, would be worse.

### Already a service proc — do not fold back into jobs

| Proc | Why it is a daemon |
| --- | --- |
| `scheduler` | Owns the routine tree |
| `gateway` | HTTP listener |
| `telegram_receiver` | Exclusive long-poll |

### Plugin jobs that stay jobs

`tg_outbound` remains a finite notification drain. If outbound latency ever
matters at sub-second scale, tail `notifications.jsonl` from the existing
receiver process (it already runs inbound housekeeping under a lock) rather
than adding `telegram_sender` as a fourth machine daemon.

`tg_inbound` without `--receiver` remains the `--once` cleanup tick and the
legacy re-arm path. Do not delete it in order to "fully migrate."

### Nothing else is a candidate

I would not migrate `wait_checks`, `bead_claim_checks`, `hook_checks`,
`sidecar_auto_sync`, `usage_refresh`, or any housekeeping job. If a future
component needs a persistent watch (for example a dedicated artifact-index
writer), that is a **new** service proc with a new contract, not a renamed
job.

## Critique of "make wait_checks a service proc"

### What you would lose

- `sase axe job run wait_checks` and the Services-tab job run-now path.
- Per-run history under the lumberjack chops directory.
- Structured summaries (`ready_written`, `deferred_unconfirmed`,
  `waiter_errors`, `unknown_outcome`).
- Maintenance mode. Today `sase axe maintenance enter` pauses scheduled
  ticks. A service proc keeps running unless the host is taught a second
  pause switch.
- Confirmation and terminal-blocker behavior staying on one code path with
  one timeout (`job_timeout`).
- Crash isolation at the *routine* grain. A wedged wait daemon takes a
  Services-tab crash-loop; a wedged waits routine is restarted by the
  scheduler without parking the gateway or Telegram.

### What you would not gain

- Instant agent start. The runner still polls `ready.json` every 2 seconds
  unless that poll changes too.
- Independence from the scheduler. If the host is down, waiters are the
  least of it. If the scheduler is stopped on purpose, waiters should stay
  parked; a separate daemon would keep releasing them during maintenance.
- Simpler ops. Builtin launchers are reserved (`scheduler`, `gateway`). A
  third builtin needs a packaged launcher, doctor checks, and overlay
  enablement. A `command:` wrapper around `sase_job_wait_checks` in a loop
  is a homegrown routine with none of the job policy engine.

### What would actually have to be built anyway

An honest "wakeup daemon" is not `while true; do wait_checks; sleep 1`. It
is inotify/fanotify on artifact trees and bead stores, debounce, the same
confirmation pass (`confirm_dependency_resolution` after a fresh membership
view — sessions grow monitors and gates between the resolving read and the
write), and a way to notify the parked PID. That is an event-driven
*implementation of the job*, which can live in the waits routine or in the
completion path. The service-proc wrapper does not do that work.

## A better approach

Three layers, in order of payoff.

### 1. Completion-side poke (do this)

`write_done_marker_and_update_index` already runs at settlement. It writes
`done.json`, updates the artifact index, reconciles agent holds, and pulses
the TUI. It is the moment the world knows an agent finished.

After a known successful outcome (`completed`, `noop`, `epic_approved`,
`plan_committed` — same set `wait_checks` already uses), run the existing
wait-resolution helper against live `waiting.json` markers and write
`ready.json` for waiters that confirm cleanly. Failed/killed/rejected
outcomes still must not release named waits.

Do the same from the bead-close path for `wait_for_beads`. Bead waits cannot
see `done.json` at all; a `wait_checks` daemon watching only agent artifacts
would still miss them.

Keep the confirmation pass. `docs/axe.md` is explicit: if a session grew a
member between the resolving view and the write, defer. A poke that skips
confirmation will launch a waiter onto a workflow that just started a
monitor or gate.

Keep `wait_checks` as a 10-second (or quieter) backstop for:

- missed pokes
- bead-sidecar lag after `sidecar_auto_sync`
- terminal-blocker notifications
- waiters that appeared after the dependency settled (the immediate resolve
  at waiter start already covers the common case)

This is push-from-writer, which is how the rest of settlement already works
(index, holds, TUI pulse). It does not add a process.

### 2. Make the parked runner notice `ready.json` without a 2s sleep (cheap)

Even an instant `ready.json` waits up to two seconds. Watch the waiter’s own
`ready.json` with inotify, or `sleep` in 200ms slices, or eventfd. Do not
signal PIDs from `waiting.json`; PID reuse is how you unpark the wrong
process. The 60-second full fallback stays as the outage path.

### 3. Event-driven job triggers inside the scheduler (later, general)

If several jobs want "run me when this tree changes, and also every N
seconds," add an `fs` trigger mode that is actually a watch, evaluated
between ticks, still invoking the job runner. That would help `wait_checks`
*and* `hook_checks` without a service proc per job.

Do **not** deepen the current glob to `*/artifacts/ace-run/*/*/*` as the
main fix. That would stat every historical timestamp directory on every
10-second tick, which is the cost the shallow glob was invented to avoid.

A smaller config-only mitigation, if poke is delayed: have settlement touch
a single pulse file (`~/.sase/wait_wake` or similar) and point the existing
`fs` trigger at that file. Next 10-second tick runs the job. Latency falls
from ~60–120s to ~0–12s without a daemon. Still worse than a poke.

### What not to do

- Do not lower the waits interval to 1s as a substitute. The job is skipped
  by the trigger; a faster skip loop wastes a little CPU and changes
  nothing until `max_quiet`.
- Do not delete the fs trigger without a replacement. Idle ticks that spawn
  `wait_checks` across every project are the expense the trigger was
  paying for. Fix what it observes, or poke, or both.
- Do not have the poke launch agents. Admission, holds, runner slots, and
  `%queue` stay with the parked runner. The protocol is still `ready.json`.
- Do not put wakeup policy in the TUI. Writers of `done.json` include
  non-TUI runners.

## Requirement adjustments

Call these out as deliberate deltas from the prompt.

### R1. The goal is waiter wakeup latency, not a job→daemon migration

**Adjustment.** Treat "migrate jobs to service procs" as a hypothesis to
falsify, not as the work. Success is: a waiter whose dependency just
produced a successful `done.json` (or whose bead just closed) crosses the
barrier in well under a second plus runner-slot admission, without a new
Services-tab row.

### R2. Zero builtin jobs migrate in this round

**Adjustment.** The prompt asks "which jobs (if any)." The answer is none
of the shipped builtins. The Telegram receiver already migrated, and for a
reason that does not apply here.

### R3. Keep `wait_checks` as a job even if wakeup becomes push

**Adjustment.** A poke is an accelerator. The job remains the
reconciler, the notifier, and the outage backstop. Removing it would
strand waiters when a writer crashes after `done.json` and before the poke,
and would drop terminal-blocker notifications.

### R4. Bead waits are in scope for wakeup, not only named-agent waits

**Adjustment.** The example is `wait_checks` waking agents. Many parked
runners are waiting on `wait_for_beads`. A design that only watches
`ace-run` leaves those on the 30-second sidecar hint plus 10-second job
(or 120-second quiet). The poke must have a bead-close hook.

### R5. Confirmation stays fail-closed

**Adjustment.** Faster wakeup is not allowed to defeat
`confirm_dependency_resolution`. A session that grew a member after the
resolving read stays parked. That is ordinary `deferred_unconfirmed`, not
an error, and it is why a naive inotify "any file changed → unpark" daemon
would be unsafe.

### R6. No new builtin service-proc launcher

**Adjustment.** `RESERVED_BUILTIN_SERVICE_PROCS` is `gateway` and
`scheduler`. Do not add `wait_checks`. If a later index-writer daemon is
justified by measurement, it gets its own name and contract.

### R7. Scheduler maintenance continues to pause scheduled wakeup

**Adjustment.** A completion-side poke from an agent that is already
finishing may still write `ready.json` during maintenance; that is a
settlement side effect, like writing `done.json`. A *scanner* must honor
maintenance. A wait_checks service proc would need extra code to do what
the routine already does.

### R8. Rust-core boundary for shared resolution

**Adjustment.** Wait resolution is already shared
(`sase.core.wait_dependency_resolution`, used by the job and the runner).
A poke should call that, not a third copy. If a web app or another frontend
must match TUI wait semantics, the resolver belongs in sase-core; do not
grow a Python-only daemon.

## Recommended solution

**Ship a poke, not a daemon.**

1. **Keep the catalog.** No builtin job becomes a service proc. Keep
   `telegram_receiver` / `gateway` / `scheduler` as the daemon set.
2. **Fix `wait_checks` latency at the writer.** From
   `write_done_marker_and_update_index` (success outcomes only) and from
   bead close, attempt the existing resolution+confirmation path and write
   `ready.json`. Best-effort: a poke failure leaves the waiter for the job.
3. **Keep `wait_checks` in the waits routine.** Optionally retarget its `fs`
   trigger at a pulse file the poke touches, or drop the broken month-shard
   glob in favor of `always` plus a cheaper index-only scan (the job already
   prefers the artifact index). Do not deepen the glob.
4. **Tighten the runner poll** on `ready.json` (inotify or shorter sleep).
   Keep the 60-second full fallback.
5. **Revisit event-driven job triggers** only after the poke is measured. If
   idle `hook_checks` ticks or remaining wait lag still show up in traces,
   add watches to the scheduler, still invoking jobs.

Expected latency after (2)+(4), busy host, dependency just completed:

- `ready.json` written in the same process that settled the dependency
- waiter notices in well under a second
- `wait_checks` continues to catch anything the poke missed within one
  quiet period, and still owns notifications

That is the behavior the service-proc idea was reaching for, without a
fourth long-lived process or a layering violation.

## Sources

Primary, in this checkout:

- Glossary strands: Job, Routine, Service Proc, Oneshot Service Proc, Sase
  Scheduler, Sase Service, Named Proc.
- `src/sase/default_config.yml` — `service.procs`, `axe.routines`.
- `docs/axe.md` — scheduler architecture, default routines, fs trigger
  contract, wait confirmation.
- `docs/configuration.md` — service proc fields; `wait_checks` description.
- `src/sase/axe/run_agent_wait.py` — 2s poll, 60s fallback, 600s bead hint.
- `src/sase/axe/run_agent_wait_deps.py` — runner-side resolve without
  `ready.json`.
- `src/sase/axe/chop_policy_snapshots.py` — shallow fs tokens.
- `src/sase/scripts/_chop_wait_checks_run.py` — scan, confirm, write
  `ready.json`.
- `src/sase/axe/run_agent_exec_markers.py` — `done.json` + index + holds +
  TUI pulse.
- `tests/test_axe_default_chop_triggers.py` — month-shard glob test.
- sase-core `crates/sase_core/src/agent_scan/layout.rs` — day-sharded
  `ace-run/YYYYMM/DD/<timestamp>`.
- sase-core `crates/sase_core/src/service/mod.rs` — reserved builtins.
- sase-telegram `src/sase_telegram/default_config.yml` and `receiver.py` —
  job vs `--receiver` daemon.
- Plan `202609/service_host_sunset.md` — one supervisor per child.
- Plan `202609/unread_ack_reliability_and_tui_responsiveness.md` — deferred
  service-proc move until measured.
