# Should Builtin Scheduler Jobs Become Service Procs? `wait_checks`, Wake Latency, and Where the Job/Daemon Line Belongs

Researcher: `cld` (5-researcher swarm) · Written 2026-10-07 ~13:00–14:00 EDT · sase master
`38f48d7575` · Measurements taken live on athena (64 cores, load avg ~25)

## 0. Bottom Line

**Do not migrate any builtin job to a service proc yet. That includes `wait_checks`.**

Your instinct is right: waiting agents wake up slowly. But the cause is not that
`wait_checks` is a job. It is three defects in the `waits` lane, and each is cheap to fix
inside the job model:

1. **The lane's `fs` trigger cannot see agents finish.** It globs
   `projects/*/artifacts/ace-run/*`, which matches *month* shards (`202610`). Runs live
   two levels deeper (`YYYYMM/DD/<run>/done.json`). So `wait_checks` really runs on its
   120 s `max_quiet` backstop. Observed: about every 143 s.
2. **Each run spends about 30 s on dead runners.** 883 of the 912 `waiting.json` markers
   on disk belong to dead runner PIDs, and 880 of those are more than 7 days old.
3. **The `waits` tick is about 25 s, not 10 s.** A tick waits for its slowest job
   (`bead_claim_checks` 33 s, `wait_checks` 30 s, `sidecar_auto_sync` 15–25 s), and the
   `schedule` library sleeps the interval *after* each tick finishes. "Tick overrun" is
   logged nearly every cycle.

**What actually releases waiting agents today is the runner's own 60 s fallback.** In
October runner logs, 298 dependency waits were released by "runner fallback (ready.json
not observed)". Only about 70–95 were released through `ready.json`. So the designated
wake path, `wait_checks`, handles only about 1 in 5 releases.

That fallback is also expensive. Every parked runner rebuilds a full per-project index
(it reads every `agent_meta.json` and `done.json`) once a minute.

**Recommendation:** fix the lane (Phase 1, small), measure, then add *event-wake* to the
scheduler (Phase 2). Event-wake lets a job run within about a second of the file event
it watches, while keeping run history, timeouts, dry-run, maintenance-mode pause, and
automatic pickup of new code. A dedicated `waits` service proc is a conditional Phase 3,
only if measured latency still misses the target.

**Going forward, use one rule: daemons listen; jobs reconcile.** A service proc is the
right home for something that must hold a socket, long-poll, or subscription open (the
mobile gateway, the Telegram receiver). Batch reconcilers stay jobs, even when they need
to react quickly.

## 1. Method and Evidence Base

- I read the scheduler, service host, wait, and job code in this checkout, plus
  sase-core references found through `sase repo open`. Line references below are
  relative to the sase repo root.
- **Live state on athena:**
  - job run history under `~/.sase/axe/lumberjacks/*/chops/*/runs`;
  - routine `status.json` and `lumberjack-*.log`;
  - the newest `wait_checks` `.result.json`;
  - a liveness check of every `waiting.json`;
  - October runner logs in `~/.sase/workflows/202610/*.txt`, counting only the runner's
    structured wait lines.
- **Prior design material:**
  - the sase-11y service-host research (`research/202609/service_host_and_services_tab/`);
  - the plan `plans/202609/telegram_receiver_housekeeping.md`;
  - the sase-3e daemon revert (`5a65fa4fc1`, 2026-05-14);
  - bead `sase-14x`.
- Three read-only helper subagents swept the code. I re-verified every claim below that
  carries a number or a `file:line`.
- **Incidental exposure:** a broad grep over the runner logs printed two lines from other
  agents' transcripts that touch this topic. Their source is unknown; they may be peers
  or earlier research. I did not open those logs or use their content. All conclusions
  here come from my own measurements.

## 2. Adjusted Requirements (Called Out)

Your request was to recommend which jobs to migrate to service procs, and to critique the
plan. I am reframing it, because "service proc" is a means, and the end you named is
"wake up agents that are ready sooner".

| # | Adjustment | Why |
|---|---|---|
| R1 | **Goal becomes a latency target, not a migration.** Proposed: agent-dependency release p50 ≤ 5 s and p95 ≤ 15 s after the dependency's `done.json`. Bead-wait release ≤ 30 s after the close is pushed. | Without a target, "sooner" can't decide between a 1-line config fix and a new daemon. |
| R2 | **Measure first.** Record the release source (`ready_json` / `runner_fallback` / `startup`) and the latency (dependency `finished_at` → `wait_completed_at`) for each wait. | Today this is only recoverable by grepping runner logs and matching names. |
| R3 | **Keep job-grade observability for anything that writes durable state:** per-run history, per-run logs, RESULT card, manual run, `--dry-run`. | Service procs get one shared rolling log and a status line (§4.2). |
| R4 | **Every event-driven path keeps a polling backstop.** | The repo's existing stance (`max_quiet`, the runner fallback, the TUI watcher's polling fallback) is fail-open. Events get dropped. |
| R5 | **Hot upgrade.** After `sase update`, new code must run within one cycle. | Jobs get this free: each fire is a fresh interpreter. `sase update` restarts only the `scheduler` proc (`src/sase/main/update_restart.py:56-61`). |
| R6 | **Correct on macOS, fast on Linux.** | The existing inotify watcher is Linux-only (`src/sase/ace/tui/util/fs_watcher.py:94`). The tailnet includes a Mac. |
| R7 | **Bead waits are in scope.** | They are the slowest kind of wait, and they are limited by sidecar sync rather than `wait_checks`. |

## 3. How Waiting Works Today, and Where the Time Goes

### 3.1 The moving parts

- **Supervision chain:** service host → `scheduler` service proc (orchestrator) → one
  long-lived Python process per routine (43–104 MB RSS each on athena) → each job fire is
  a **fresh subprocess** (`src/sase/axe/chop_script_runner.py:198`).
- **Triggers are stat-polled inside the routine at tick time**
  (`src/sase/axe/chop_policy_snapshots.py:134-165`).
  - The token is `name:mtime:size:child_count` for each *shallow* glob match.
  - The fire decision is made in Rust (sase-core `axe_chop/decision.rs`).
  - A skip spawns nothing.
- **Tick barrier:** jobs in one tick run concurrently, but the tick waits for all of them
  (`src/sase/axe/lumberjack.py:227-235`). `schedule.every(interval)` (`:520`) sleeps the
  interval after the tick finishes, so the real period is interval + slowest job.
- **Parked runner** (`src/sase/axe/run_agent_wait.py`):
  - it writes `waiting.json`, then polls for `ready.json` every 2 s (`:97`, loop
    `:225-255`);
  - every 60 s it resolves dependencies itself (`:40`, `:233-248`). That resolution calls
    `build_wait_dependency_index` → `WaitDependencyIndex.build`, which reads every
    `agent_meta.json` and `done.json` in the project
    (`src/sase/core/wait_dependency_resolution/_index.py:114-150, 535-549`);
  - every 600 s it requests a beads sync (`:41`).
- **Completion signal:** `write_done_marker_and_update_index` writes `done.json`, updates
  the SQLite artifact index, and touches `projects/<p>/artifacts/.ace_refresh_pulse`
  (`src/sase/axe/run_agent_exec_markers.py:29-56`; `src/sase/turns/settlement.py:200-208`).
  The `waits` trigger does not watch that pulse file.

### 3.2 Defect 1: the trigger watches the wrong directory level

The default config is `trigger: {provider: fs, max_quiet: "120s", paths: [{path:
projects, glob: "*/artifacts/ace-run/*"}]}` for `wait_checks` and `bead_claim_checks`
(`src/sase/default_config.yml:1362-1376`, `:1326-1340`).

- **What the glob matches:** month shards, plus hidden lock files that sit directly in
  `ace-run/` (`.gate-shell-*`, `.gate-turn-*`, `.monitor-start-*`).
- **When a month shard changes:** its mtime moves only when a new *day* directory
  appears. On disk, `gh_sase-org__sase/artifacts/ace-run/202610` has mtime 00:13:32
  today, while its `07/` day directory has mtime 13:10:10.
- **Effect:** new runs, new `waiting.json` files, and `done.json` writes never change the
  token. The job fires only on `max_quiet` or on incidental lock-file churn.
- **Why the test didn't catch it:** `tests/test_axe_default_chop_triggers.py:148-162`
  creates the run directory directly under the month shard, with no day level.
  `docs/axe.md` (§ waits) still says the job re-scans "when a project gains a new agent
  artifact".

**Observed:** in the last 10 scheduled `wait_checks` entries, 8 were `skipped` ("watched
paths unchanged and within max_quiet"). The 2 real runs started at 13:13:35 and
13:15:58, 143 s apart.

### 3.3 Defect 2: `wait_checks` spends about 30 s on dead runners

Counters from the newest `wait_checks` result: `projects=37 artifacts=16857 waiting=912
already_ready=92 invalid=134 unresolved=686 ready_written=0`. The two real runs took
31.3 s and 27.9 s.

I checked liveness of every `waiting.json` against its `agent_meta.json` PID:

| Markers | Count |
|---|---:|
| Total `waiting.json` | 912 |
| Runner PID alive | 25 |
| Runner PID dead | 883 |
| No PID recorded | 4 |
| Older than 7 days | 880 |

About 97% of the work in each run is resolving dependencies for agents nobody will ever
resume. Nothing in the code filters dead waiters out.

### 3.4 Defect 3: head-of-line blocking stretches the `waits` tick to about 25 s

From the `waits` routine status: 172 cycles in 4,229 s, so the average cycle is **24.6 s**
against a configured 10 s. Last 10 runs of each job:

| Job | Fires | Median duration | Max duration |
|---|---|---:|---:|
| `bead_claim_checks` | 2 of 10 | 33.1 s | 33.5 s |
| `wait_checks` | 2 of 10 | 29.6 s | 31.3 s |
| `sidecar_auto_sync` | 10 of 10 | 16.7 s | 25.0 s |
| `epic_launch_flush` | 10 of 10 | 0.3 s | 0.4 s |

`lumberjack-waits.log` shows "Tick overrun: took 14–34 s but interval is 10s" almost
every cycle. The `hooks` lane, at 7.1 s per cycle against 5 s, is mildly affected too.

### 3.5 The result: the backstop became the primary path

October runner logs: 502 runner logs park on a real dependency (I excluded
duration-only and until-only waits). What came next:

| Next event after "Waiting for …" | Count |
|---|---:|
| `Dependencies satisfied by runner fallback (ready.json not observed)` | 298 |
| `All dependencies satisfied, proceeding with workflow` immediately (the `ready.json` path, from `wait_checks` or TUI run-now) | 68 |
| Killed while waiting | 54 |
| Interleaved output, or still parked | ~82 |

**About 76–81% of releases come from the runner fallback.** A helper matched 102 waits
by name against dependency finish times. Treat its numbers as approximate:

- fallback releases: median ~20 s, p90 ~50 s after the dependency's `done.json`;
- `ready.json` releases: median ~31 s, with a long tail.

That ordering is what you'd expect if `wait_checks` effectively fires every ~143 s and
then runs for ~30 s.

**The hidden cost:** each of the ~25 live parked runners rebuilds a full per-project
index every minute. A helper measured about 1 s of raw JSON reading per pass over the
15k run directories in the sase project. That is a steady background I/O and CPU load on
a host already at load ~25, and it scales as O(waiters × artifacts).

### 3.6 Bead waits

`%wait(bead=…)` reads the canonical *primary* beads clone, so a close only counts after
two things happen:

- the closing agent pushes;
- `sidecar_auto_sync` fetches and fast-forwards. It is `run_every: 30s`, which is about
  35 s in practice, and each run takes ~15 s.

Release then needs one more pass of the fallback or `wait_checks`. A realistic total is
45–90 s, and more than 10 minutes if a clone is in backoff. Bead closes never touch the
`waits` fs trigger at all.

### 3.7 Latency budget

These are estimates built from the measured parts. "Today" is measured.

| Component (agent-name wait) | Today | After Phase 1 | After Phase 2 | Dedicated daemon |
|---|---|---|---|---|
| Notice the completion | 0–143 s (`max_quiet` + tick alignment), or the 0–60 s runner fallback | 0–3 s (pulse-triggered, own 3 s lane) | ~0.25–1 s (inotify wake + debounce) | ~0.1–0.5 s |
| Spawn + import | ~1 s | ~1 s | ~1 s | 0 s |
| Resolve | ~30 s | ~1–3 s (live waiters only) | ~1–3 s | ~0.1 s (warm index) |
| Runner notices `ready.json` | 0–2 s | 0–2 s | 0–2 s | 0–2 s |
| **Typical end to end** | **~20–35 s; worst ~65–70 s (fallback) or ~3 min (`wait_checks` path)** | **~3–8 s** | **~2–5 s** | **~1–3 s** |

The daemon's remaining edge over Phase 2 is about 1–3 s per hop. Phase 1 alone delivers
most of the gain.

## 4. Critique: Is "Jobs → Service Procs" a Good Idea?

### 4.1 The plan conflates three different axes

| Axis | Options | What it controls |
|---|---|---|
| **Supervisor** | service host vs. scheduler orchestrator | Who restarts the process, and how it is enabled per machine |
| **Activation** | time tick vs. event wake | **Latency.** This is the axis your goal lives on. |
| **Process model** | fresh subprocess per run vs. long-lived state | Warm caches vs. isolation, hot upgrade, and per-run accounting |

The scheduler is *already* a service proc, and routines are *already* long-lived
processes. "Make `wait_checks` a service proc" really means "give one job its own
private loop, outside the scheduler". That fixes latency only because the new loop would
be event-driven or tight. Both properties can be given to the job where it is.

### 4.2 What a service proc would cost compared with a job

| Capability | Job today | Service proc today |
|---|---|---|
| Per-run record (status, duration, exit, result, proposals) | Yes (`ChopRunEntry`, newest 10) | No. Proc rows per *launch*, 20 kept. |
| Per-run log, context, and result files | Yes | One shared rolling `output.log` (2 MiB) |
| Run now / `--dry-run` / `--force` | Yes (`r`, `sase axe job run`) | Restart / start / stop only |
| Timeout per run | Yes (`timeout`, `job_timeout`) | No. A hung loop stays hung until a health probe or a human acts. |
| Triggers, guards, `once_per`, `for_each`, `axe.query` | Yes | Must be reimplemented |
| Maintenance-mode pause (`sase axe maintenance enter`) | Yes, checked every tick | Not honored unless reimplemented |
| New code after `sase update` | Next fire | Only on restart. `sase update` restarts only `scheduler`. |
| Failure semantics | A failed run is retried next tick, and the error lands in the error digest | Restart backoff 1→60 s, `crash_loop` after 3 failures in 60 s, give-up parking, one notification per episode |
| Adding a builtin | One `default_config.yml` entry | Rust allowlist `RESERVED_BUILTIN_SERVICE_PROCS` (sase-core `service/mod.rs:23`), schema enum, `service_meta.py`, `entry_launch` branch, docs. A plain `command:` entry avoids this. |
| Memory | Paid only while running | About 50–100 MB resident per Python daemon, permanently |

### 4.3 Precedents in this repo

- **sase-3e (reverted 2026-05-14, `5a65fa4fc1`).** A Rust daemon with event projections,
  a daemon scheduler, and file-watch ownership was built across 11 epics and then
  reverted wholesale. The no-daemon review written just before the revert found that its
  runtime wins sat dormant whenever the daemon was not running. That is a direct warning
  about building event infrastructure ahead of a demonstrated need.
- **`tg_inbound` → `telegram_receiver` (Sep 2026).** Long-polling moved from a job into a
  service proc. Afterwards, every tick-only duty silently stopped: command-menu
  registration, `/usage` refresh edits, gate-completion messages, media-group flushes,
  and keyboard cleanup. They stayed broken until a later plan found it
  (`plans/202609/telegram_receiver_housekeeping.md`). Moving a job into a daemon tends to
  drop the incidental duties the tick performed. `wait_checks` has some too: unknown-
  outcome counters and terminal-blocker notifications.
- **sase-11y research** deliberately deferred making routines direct children of the
  service host ("option D"), citing churn and blast radius for no current pain. The same
  reasoning applies one level down.

### 4.4 Where the instinct *is* right

Polling is a poor fit for dependency release. It is also a poor fit for Patch-pipeline
progression (hooks → mentors → workflows) and for bead-sync hints. Something should
react to events, and a long-lived process with warm state is the natural shape for that.
But **the routine process already is one**. What it lacks is:

- an event wake (inotify on the paths its triggers already declare, plus explicit nudge
  files);
- per-job scheduling that does not wait for the slowest sibling.

Add those to the scheduler once and every job benefits, with no loss of job semantics.

### 4.5 When a service proc *is* the right home

Use a service proc when **all** of these hold:

1. it holds something open — a listening socket, a long-poll or stream, a subscription,
   or a child it must supervise continuously;
2. it is a per-machine singleton consumer, so duplicate instances would misbehave;
3. its health is best described as "is it up", not "what did run N do";
4. its work is continuous, not periodic batches.

The `gateway` (an axum HTTP server) and `telegram_receiver` (`getUpdates` long-poll)
pass. **None of the 28 builtin jobs passes criterion 1.**

## 5. Job-by-Job Verdicts (All Builtin Jobs)

Verdict key:

- **Keep**: leave it a job unchanged.
- **Fix**: a trigger or code defect.
- **Lane**: move it to another routine.
- **Wake**: a Phase 2 event-wake candidate.

| Lane | Job | True input | Someone waiting on it? | Verdict |
|---|---|---|---|---|
| hooks (5 s) | `hook_checks` | Hook process exit; completion line written under `~/.sase/hooks/YYYYMM/` | Yes (Patch pipeline) | **Keep + Fix + Wake.** The trigger watches `*.sase`/`*.gp`, but the hook wrapper writes `===HOOK_COMPLETE===` into the hooks shard (`src/sase/ace/hooks/execution.py`). In theory completion waits for `max_quiet`. In practice spec churn fires it often; unmeasured. |
| hooks | `mentor_checks` | Hooks finishing; mentor marker | Yes | **Keep + Wake** (same nudge as hooks) |
| hooks | `workflow_checks` | Workflow markers in `~/.sase/workflows` plus PIDs | Yes | **Keep + Wake** |
| hooks | `pending_checks_poll` | `checks/*/*.txt` (watched correctly) | Moderate | **Keep + Wake** |
| hooks | `comment_zombie_checks` | Wall clock (7200 s age) | No | Keep |
| hooks | `suffix_transforms` | `.sase` contents | Low | Keep |
| hooks | `orphan_cleanup` | Reverted status + dead claim PID | Low | Keep |
| hooks / checks | `stale_running_cleanup` | PID death (a backstop by nature) | Moderate | Keep. It is the largest idle spawn source (~12/min). pidfd waits would be possible, but not worth a daemon. |
| waits (10 s) | `bead_claim_checks` | Pre-launch artifacts + owner PID death | Moderate | **Keep + Fix** (same trigger bug) **+ Lane** (its 33 s run must not block waits) |
| waits | `epic_launch_flush` | Wall clock + detached task alive | Low | Keep |
| waits | `sidecar_auto_sync` | Hint files sase writes, plus remote git | **Yes** (bead waits) | **Keep + Lane + Wake on hint writes.** The biggest lever for bead waits. |
| waits | `wait_checks` | `waiting.json` + dependency `done.json` + closed beads | **Yes** | **Keep + Fix + Lane + Wake.** Daemon only as a conditional Phase 3. |
| checks (300 s) | `bead_task_triage` | Bead store + deadlines | No (human triage) | Keep |
| checks | `plugins_required` | Config + installed dists | No | Keep |
| checks | `pr_submitted_checks` | Remote PR state | Low | Keep + **Fix**: `CheckCycleRunner._first_cycle` (`src/sase/axe/check_cycles.py:59,134,143`) is always true in a fresh subprocess, so every leaf bypasses the sync cache. Minor, but it is a casualty of the stateless model; fix it in code, not with a daemon. |
| usage (60 s) | `usage_refresh` | Wall clock + remote probes | Low | Keep |
| external_mirror (900 s) | `external_issue_mirror`, `external_pr_mirror` | Remote tracker | No | Keep. A future webhook *listener* would be the daemon, and it would nudge these jobs. |
| comments (60 s) | `comment_checks` | Remote reviewer comments | Moderate | Keep (same reasoning as the mirrors) |
| housekeeping (3600 s) | `error_digest`, `notification_store_compact`, `managed_tmp_reap`, `proc_runtime_sweep`, `disk_pressure`, `bead_stale_cleanup`, `gate_turn_reclaim`, `artifact_link_backfill`, `artifact_run_prune` | Wall clock, ages, backlogs | No | Keep, all nine. Bounded batch maintenance with timeouts is the archetypal job. `artifact_link_backfill` takes about 158 s per run, which is exactly why it needs run records and timeouts. |

**Totals:**

- builtin jobs to migrate to service procs: **0**;
- defects to fix: 3 (the waits trigger, the dead-waiter scan, the `_first_cycle`
  vestige), plus 1 to measure (hook-completion latency);
- lane splits: 1 (isolate `wait_checks`, and put `sidecar_auto_sync` and
  `bead_claim_checks` in separate routines);
- event-wake candidates: about 6.

**Outside the builtins (aside):** your user-config `telegram` routine runs `tg_outbound`
every 5 s, next to a `telegram_receiver` service proc that already holds the Telegram
session. Folding outbound delivery into the receiver is the only migration in the whole
system that passes §4.5. It is optional, it lives in the `sase-telegram` plugin, and it
must carry over every tick-only duty listed in §4.3.

## 6. Alternatives Considered

| Option | Latency | Cost and risk | Verdict |
|---|---|---|---|
| **A. `wait_checks` → `waits` service proc** (inotify + in-memory index, writes `ready.json`) | ~1–3 s | New daemon; loses §4.2 job capabilities; stale code after `sase update` unless update learns to restart it; needs a polling fallback on macOS; drops tick-only duties (§4.3) | Conditional Phase 3 only |
| **B. Completion-side write-through** (the `done.json` writer resolves its dependents and writes their `ready.json`) | ~2 s | Puts dependency resolution and the fresh-membership confirmation into every agent's finalization path, which is deliberately "must never fail settlement". Doesn't help bead waits. | Viable, but couples producer to consumers. Prefer a nudge (D). |
| **C. In-process builtin jobs** (routine calls the job function in a thread) | Saves ~1 s of spawn | Loses killable timeouts and isolation; reverses the script-only decision (`8e4002bb4d`, sase-6v.2) | Reject |
| **D. Event-wake jobs in the scheduler** | ~2–5 s | Moderate scheduler work; Linux-only acceleration; keeps every job capability | **Recommended (Phase 2)** |
| **E. Just shorten the `waits` interval** | None | Doesn't help: the trigger is blind and the tick is barrier-bound | Reject on its own; useful as part of Phase 1 |
| **F. Fix the three defects** | ~3–8 s | Small, mostly config and filtering | **Recommended (Phase 1)** |

## 7. Recommended Solution

### Phase 0 — Instrument (hours)

- Record `wait_release_source` (`ready_json` | `runner_fallback` | `startup` | `manual`)
  and `wait_release_latency_s` in `agent_meta.json` when `record_wait_completed_at`
  runs.
- Emit both as a metric.
- **Success measure:** the `runner_fallback` share drops below 10%, and the R1 targets
  are met.

### Phase 1 — Fix the waits lane (small; config plus Python in this repo)

1. **Trigger.**
   - Add `{path: projects, glob: "*/artifacts/.ace_refresh_pulse"}` to the
     `wait_checks` and `bead_claim_checks` triggers. Every `done.json` write already
     touches this file.
   - Make `write_waiting_marker` touch the same pulse, so new waiters are seen too.
   - Keep the `ace-run/*` entry for lock churn, or drop it.
   - Fix `tests/test_axe_default_chop_triggers.py` to use the real `YYYYMM/DD/<run>`
     layout, and correct `docs/axe.md`.
2. **Skip dead waiters.**
   - In `wait_checks`, resolve only markers whose runner is alive. Use PID plus start
     identity where available, to guard against PID reuse.
   - Enumerate waiters from the SQLite artifact index instead of stat-walking all 16.9k
     run directories.
   - Add an hourly housekeeping sweep that archives `waiting.json` for runners dead more
     than N hours.
   - **Verify first:** no resume or refresh path relies on a dead runner's `ready.json`.
     The runner's `wait_completed_at` fast path suggests none does.
3. **Split the lane.** Put `wait_checks` alone in a routine (e.g. `agent_waits`,
   `interval: 3`). Move `sidecar_auto_sync` into its own routine. Leave
   `bead_claim_checks` and `epic_launch_flush` in `waits`.
4. **Then demote the runner fallback** from 60 s to 300 s, once Phase 0 shows
   `wait_checks` releasing at least 90% of waits. This removes about 25 full project
   scans per minute.

**Expected:** agent waits ~3–8 s end to end; `wait_checks` ~1–3 s per run; the `waits`
lane stops overrunning.

### Phase 2 — Event-wake for jobs (medium; crosses into sase-core)

- **Config:** add an opt-in `wake: true` to `fs` triggers, plus optional named nudges
  (`~/.sase/axe/nudges/<name>`).
- **Linux:** the routine process puts inotify watches on the directories its trigger
  paths resolve to, and on the nudge files.
  - Events are debounced (~250 ms) and run that one job immediately, outside the tick
    barrier.
  - The per-job no-overlap lock still applies.
  - The run is recorded normally, with reason `wake: <path>`.
- **macOS, or watch failure:** today's polling plus `max_quiet`, unchanged.
- **Producers to nudge:**
  - `done.json` and `waiting.json` writes (the pulse already exists);
  - bead publish → the sidecar sync hint that already exists (`_sidecar_sync_hints.py`);
  - the hook wrapper's completion line → a `hooks` nudge;
  - check-output writes.
- **Boundary note:** trigger semantics and the config wire live in sase-core
  (`axe_chop/decision.rs`, schema). Per the Rust-core boundary rule, update the Rust
  wire, bindings, and tests there, then the Python routine and the
  `sase-core-revision.txt` pin here.
- **Expected:** agent waits ~2–5 s; bead waits ~push + 15–20 s; hook → mentor → workflow
  progression within seconds. Every job keeps history, timeouts, dry-run, and
  maintenance pause.

### Phase 3 — Conditional `waits` broker service proc

Build it only if, after Phase 2, p95 agent-wait release is above ~10 s, or profiling
shows parked-runner fallback I/O still matters. If you do build it:

- use a plain `command:` service proc, not a new reserved builtin;
- keep `wait_checks` as a 60 s backstop job, so an idempotent `ready.json` writer
  remains;
- make `sase update` restart it (a prerequisite, R5);
- carry over the job's diagnostics: unknown-outcome counters and terminal-blocker
  notifications;
- write status through `$SASE_SERVICE_PROC_STATUS`.

### Policy for later candidates

Apply §4.5. Event *sources* become daemons; the work they trigger stays in jobs, linked
by nudge files. Example: a future GitHub webhook listener behind the gateway that nudges
`comment_checks` and `pr_submitted_checks`.

## 8. Proposed Follow-Ups (not filed)

I did not file task beads. Four more researchers are investigating the same question,
and filing from each report would create duplicates. The lead can file these after
synthesis.

1. **Bug:** the `waits`-lane `fs` trigger is blind to completions and new runs (glob
   depth). The test fixture hides it, and the docs are wrong. (§3.2)
2. **Bug / perf:** `wait_checks` resolves 883 dead waiters per run, taking ~30 s. (§3.3)
3. **Perf:** chronic `waits` tick overrun caused by the tick barrier. Split the lane.
   (§3.4)
4. **Perf:** the runner fallback does a full project index build per parked runner per
   minute. (§3.5)
5. **Bug (minor):** `pr_submitted_checks` `_first_cycle` is always true in a fresh
   subprocess. (§5)
6. **Measure:** hook-completion → `hook_checks` latency, given the trigger watches only
   `*.sase`/`*.gp`. (§5)

## 9. Confidence and Open Questions

- **High confidence:** the trigger glob mismatch; the dead-marker counts; the tick
  overrun; that the fallback dominates releases. Each was directly observed and
  re-verified.
- **Medium confidence:** the per-wait latency distributions. They come from a helper's
  name-based matching of 102 waits and are directionally consistent with the cadence
  arithmetic.
- **Open:**
  - whether any resume path consumes a dead runner's `ready.json`;
  - real hook-completion latency in practice;
  - inotify watch budgets on very large `ace-run` trees (Phase 2 watches only
    directories the triggers name, not every run directory);
  - whether the `waits` routine will still need a 10 s interval once `wait_checks`
    leaves it.
