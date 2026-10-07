---
audio:
  edition: brief
  duration_s: 269.6
  chapter_count: 3
  episode_id: waking-waiting-agents-sooner-b2b0f6
---

# Should Builtin Jobs Become Service Procs? Waking Waiting Agents Sooner

> **Research query:** Would some of SASE's builtin routines or jobs be better suited as
> service procs, for example a `wait_checks` service proc that wakes ready agents sooner?
> Recommend which jobs (if any) to migrate, critique the plan in general (is it a good
> idea, and would a different approach be better?), clearly call out any justified
> adjustments to the requirements, and end with a recommended solution.

<div class="listen">

♫ **Brief audio edition** · 4 min · 3 chapters · [Narration
script](wait_wakeup_jobs_vs_service_procs_narration.md)

</div>

![Infographic: zero builtin jobs to migrate now, so wait_checks stays a job and the wait path gets repaired first. Waiting is slow because 82% of classified releases use the 60 s fallback, only 19 of 906 waiting markers have live runners, and the nominal 10 s routine averages 24.4 s. Release takes a 21–33 s median and admission adds 45–50 s more. The plan is to measure, repair the job, optionally add event wake, and build a service proc only if targets still fail: daemons listen, jobs reconcile](wait_wakeup_jobs_vs_service_procs_infographic.png)

## Bottom line

**Do not migrate any builtin job to a service proc now. That includes `wait_checks`.** Your
instinct that waiting agents wake too slowly is correct, and the effect is larger than you
might expect. But the cause is not that `wait_checks` is a job. Three defects in the
`waits` lane mean `wait_checks` almost never does the waking. The runner's 60-second
fallback releases about 82% of dependency waits instead (see
[what I re-verified](#what-i-re-verified)).

The defects are cheap to fix inside the job model
([Phase 1](#phase-1-fix-the-lane)):

1. **The `wait_checks` trigger is blind to completions.** Its `fs` glob watches
   month-shard directories, two levels above the run directories where `done.json` and
   `waiting.json` are written. The job therefore runs mostly on its 120 s `max_quiet`
   backstop, or when an unrelated lock file changes.
2. **Each run spends about 29 s resolving dead waiters.** Of 906 `waiting.json` markers on
   disk, only 19 belong to live runners. 883 runners are dead, and 884 markers are more
   than 7 days old.
3. **The `waits` routine is a convoy.** One tick waits for all of its jobs. With
   `wait_checks` (~29 s), `bead_claim_checks` (~33 s, per cld) and `sidecar_auto_sync`
   (~15–25 s) in the same tick, the "10 s" lane averages **24.4 s** per cycle.

There is also a fourth finding that none of the
[five researchers](#how-the-five-reports-line-up) measured. **After a wait is released, a
median of about 45–50 s passes before the agent actually starts.** Much of that is the
runner-slot admission scan, which took **~11 s per pass** when I measured it. A faster
resolver cannot shorten that phase, so it caps how much a "wake sooner" project can gain
(see [where the time actually goes](#where-the-time-actually-goes)).

**[Recommended solution](#recommended-solution):**

- **[Phase 0](#phase-0-instrument):** instrument release source and latency.
- **[Phase 1](#phase-1-fix-the-lane):** fix the lane. Make `ready.json` publication
  atomic, point the trigger at the existing completion pulse, resolve live waiters only,
  isolate `wait_checks` in its own fast routine, and later demote the runner fallback.
- **[Phase 2](#phase-2-event-wake-for-jobs) (optional):** add a general event-wake to the
  scheduler.
- **[Phase 3](#phase-3-resolver-service-proc) (conditional):** build cdx's
  `wait_resolver` daemon only if measured targets are still missed.
- **[Parallel track](#parallel-track-for-admission-latency):** cut the admission-scan
  cost.

**Standing rule for future candidates: daemons listen; jobs reconcile.** None of the 28
builtin jobs passes [that bar](#litmus-for-future-candidates) today.

## Where the time actually goes

The latency budget is for a named-agent wait on athena today. The "after" columns are
estimates built from the measured parts.

| Segment | Today (measured) | After Phase 1 | After Phase 2 | With a dedicated daemon |
|---|---|---|---|---|
| Dependency done → resolver notices | 0–143 s on the `wait_checks` path (`max_quiet` plus convoy), or the 0–60 s fallback | 0–2 s (pulse trigger, own 2 s lane) | ~0.3–1 s (inotify plus debounce) | ~0.1–0.5 s |
| Resolve | ~29 s (all waiters, all history) | ~1–3 s (live waiters only, index-backed) | ~1–3 s | ~0.1–1 s (warm state) |
| Runner sees `ready.json` | 0–2 s | 0–0.5 s (if the poll is shortened) | same | same |
| **Release latency** | **p50 ~21–33 s, p90 ~58 s** | **~2–6 s** | **~1.5–4 s** | **~0.5–2 s** |
| Release → agent starts (admission) | **p50 ~45–50 s, p90 ~75–95 s** | unchanged | unchanged | unchanged |

**The daemon's remaining edge over Phase 1 is about 1–4 s.** The admission phase is
untouched by every option in this table, and it is now the larger share of end-to-end
"dependency done → agent working" time. If the real goal is "the downstream agent starts
working sooner", the admission scan is at least as important as `wait_checks` (see the
[parallel track](#parallel-track-for-admission-latency)).

## What I re-verified

These are the facts the recommendation rests on.

| Claim | Verification (2026-10-07) |
|---|---|
| Trigger watches the wrong level | `wait_checks` and `bead_claim_checks` use `glob: "*/artifacts/ace-run/*"` (`default_config.yml:1326-1376`). The token is a shallow `name:mtime:size:child_count` per match (`chop_policy_snapshots.py:_fs_watch_token`). For the sase project, the `ace-run/202610` mtime was **00:13:32** while `ace-run/202610/07` was **13:37:33**. `done.json` and `waiting.json` writes never change the token. |
| What the glob actually matches | **2,365 entries** across projects. At least **2,334** of them are hidden `..monitor-start-*`, `..gate-shell-*` and `..gate-turn-*` lock files that accumulate in `ace-run/`. So the trigger fires *incidentally*, whenever a gate or monitor lock is created. Each idle tick also stats about 2.4k entries per job. |
| `wait_checks` mostly skips | Of its 11 newest runs (13:33–13:37), 8 were `skipped: watched paths unchanged and within max_quiet`. Real fires came at 13:33:49, 13:34:52 and 13:37:14. |
| Each run is slow and mostly wasted | The 13:34:52 run took **29.2 s**: `artifacts=16858 waiting=907 already_ready=92 invalid=134 unresolved=680 ready_written=1`. The job walks every artifact directory and has no liveness filter (`_chop_wait_checks_run.py:88-135`). |
| Dead waiters dominate | 906 `waiting.json`: **19 live** runner PIDs, **883 dead**, 4 with no PID, **884 older than 7 days**. |
| Tick convoy | `ThreadPoolExecutor` plus `as_completed` waits for every job in the tick (`lumberjack.py:227-235`). `waits` averages **24.4 s** per cycle against 10 s; `hooks` averages **7.0 s** against 5 s. The log shows "Tick overrun" nearly every cycle. |
| Fallback does the real work | In October runner logs I classified 502 logs that park on a real dependency: **304 released by "runner fallback (ready.json not observed)"**, **68 by `ready.json`** (or another fast path), and 130 killed, still parked or interleaved. That is about **82%** fallback. Matches cld (298 vs 68). |
| Release latency | I matched waiters to session-aware dependency finish times (`<name>` plus `<name>--gate/--code/--mon/--plan`), keeping only non-gated, successful dependencies. **Fallback releases: n=21, p50 33 s, p90 58 s. `ready.json` releases: n=5, p50 21 s, max 37 s.** These samples are small but consistent with cld's ~20 s median and ~50 s p90. mus and gem's 5–12 s estimates are refuted. |
| **Post-release admission gap (new)** | From `wait_completed_at` to `run_started_at`, for runs that never logged "Waiting for a runner slot": **n=45, p50 49 s, p90 94 s**. A broader n=149 pass gave p50 44 s, p90 73 s. In this window the runner does deferred macro expansion, then `wait_for_runner_slot` (`run_agent_runner.py:182-214`). |
| Admission scan cost | `_collect_runner_slot_records()` (capacity-only scan, 12,421 records) took **11.8 s and 10.9 s** on two passes. It runs under the host-wide `runner_slots.lock`. This is the "host resource diet" hot path. The capacity-only mode has landed, but it is still O(history). |
| Fallback cost | `build_wait_dependency_index("gh_sase-org__sase")` took **4.7–5.0 s** per pass. Every live parked runner does this once a minute: ~19 × 5 s ≈ 95 s of index building per minute. |
| `ready.json` race (cdx) | The writer does `open(path, "w")` then `json.dump` (`_chop_wait_checks_run.py:287`). The reader returns **True on `JSONDecodeError` or `OSError`** (`run_agent_wait_deps.py:126-143`). A runner that catches a half-written file crosses the barrier. |
| Maintenance nuance | Routine ticks honor `sase axe maintenance` (`lumberjack.py:161-167`), but nothing in `run_agent_*.py` checks maintenance. **The runner fallback already releases waiters during maintenance.** gem and grk overstate the "a daemon would bypass maintenance" objection. It applies to a new daemon only as much as it already applies to the runners. |
| Hot upgrade | `sase update` restarts only the `scheduler` service proc (`update_restart.py:56-61`). A separate daemon would keep running old code unless update learns to restart it. |
| Completion pulse exists | `write_done_marker_and_update_index` already touches `projects/<p>/artifacts/.ace_refresh_pulse` (`run_agent_exec_markers.py:29-57`). `write_waiting_marker` updates the artifact index but does not touch the pulse. |
| Precedents | `5a65fa4fc1` (2026-05-14) reverted the sase-3e daemon rollout. `8e4002bb4d` (sase-6v.2) made jobs script-only. Bead **sase-14x** records athena running 39 duplicate scheduler and routine copies at load 70, a reminder that every resident process needs airtight single-instance and single-writer guarantees. |

## Critique of the plan in general

### Three independent axes

**The proposal conflates three independent axes (cld):**

| Axis | Options | What it actually controls |
|---|---|---|
| Supervisor | service host vs. scheduler orchestrator | Who restarts it, per-machine enablement, Services-tab placement |
| Activation | time tick vs. event wake | **Latency.** Your goal lives on this axis. |
| Process model | fresh subprocess per run vs. long-lived state | Warm caches vs. isolation, hot upgrade, per-run accounting |

The scheduler is already a service proc, and each routine is already a long-lived
process. "Make `wait_checks` a service proc" changes the supervisor axis. It helps only if
it *also* changes activation, and activation can be changed without changing the
supervisor.

### What a job keeps that a service proc loses

- per-run history and result cards;
- `sase axe job run`, `--dry-run` and `--force`;
- per-run timeouts;
- triggers, guards, `run_every` and `for_each`;
- the maintenance pause;
- the error digest;
- new code on the next fire after `sase update`.

A service proc gets restart backoff, `crash_loop` parking, one rolling log and a status
line. A hung daemon loop stays hung, whereas a hung job is killed at its timeout.

### Incidental duties

**Moving work into a daemon tends to drop the tick's incidental duties.** The
`tg_inbound` → `telegram_receiver` move silently lost command-menu registration,
`/usage` edits, gate-completion messages and more, until a later plan restored them
(cld). `wait_checks` has its own incidental duties: unknown-outcome counters and
terminal-blocker notifications.

### Where the instinct is right

- Polling is a poor fit for dependency release, and probably for Patch-lifecycle
  progression and bead-sync hints too.
- Something should react to events. But the reacting thing can be the existing routine
  (event-wake), with a producer-side signal. It does not need to be a new supervised
  process per job.

### Litmus for future candidates

The rule is "daemons listen; jobs reconcile". Promote work to a service proc only when
all of these hold:

1. It holds something open: a listening socket, a long-poll or stream, a subscription, or
   continuously supervised children.
2. It is a per-machine singleton consumer, so duplicates would misbehave.
3. Its health is "is it up?", not "what did run N do?".
4. Its work is continuous, not periodic batches.

The current service procs pass this test: `scheduler`, `gateway` and `telegram_receiver`.
**None of the 28 builtin jobs passes criterion 1.**

gem adds a fifth, "stateful in-memory engine whose state is too expensive to reload".
That is the only criterion a wait resolver could ever meet. It does not meet it today,
because the persistent SQLite artifact index already provides warm state without a
daemon.

### Plugin aside

cld and grk both note that `tg_outbound` (a 5 s job beside the `telegram_receiver` daemon
that already holds the Telegram session) is the only workload in the system where folding
into a daemon is defensible. It is optional, it lives in `sase-telegram`, and it must
carry over every tick-only duty.

## How the five reports line up

| Researcher | Verdict on `wait_checks` | Proposed mechanism | Strongest unique contribution | Errors found in verification |
|---|---|---|---|---|
| **cdx** | **Migrate** to one `wait_resolver` service proc | Coalesced mutation wakeups, repair timer, shadow mode, single writer | Reproduced the trigger blindness in a temp tree. Found the **non-atomic `ready.json` race**. Most rigorous daemon design and test plan. | None material. The daemon is well designed but premature given the evidence below. |
| **cld** | Keep it a job. Daemon only as a conditional Phase 3. | Fix the lane (pulse trigger, dead-waiter filter, lane split), then event-wake in the scheduler | **Live measurements**: release sources, dead-waiter counts, tick overrun. Precedents (sase-3e revert, Telegram receiver lost duties). The "three axes" framing. | None found. Every number I re-measured matched. |
| **grk** | Keep it a job | Completion-side "poke" (write-through) plus a faster runner poll | Clear trigger-event table. Litmus test using the Telegram receiver as the existence proof. Bead-close hook. | Write-through that runs full resolution inside settlement is riskier than it looks ([see below](#grk-and-mus-settlement-write-through)). |
| **mus** | Keep it a job | Measure first, write-through, interval tuning | Concise cost list: supervision downgrade, staleness, two writers for `ready.json`. | Claimed that completions "usually fire the trigger on the next tick" and that latency is bounded by roughly 10 s + 2 s. **Both are false.** |
| **gem** | Keep it a job | Tier 1: move to `hooks` / shorten interval. Tier 2: fallback 60 s → 5–10 s. Tiers 3–4: producer hints, event-aware scheduler. | Comparison matrix and "stateful in-memory engine" litmus criterion. | Its 5–7 s latency estimate is wrong. **Tiers 1 and 2 would actively hurt** ([see below](#gem-tier-1-faster-lanes)). It also says jobs "run inside the routine" with negligible memory, but each job fire is a subprocess. |

**Consensus (5 of 5):**

- Do not migrate wholesale.
- Restate the goal as a latency target.
- Keep a polling backstop.
- Keep the fresh-membership confirmation fail-closed.
- Keep shared resolution policy in `sase_core`.
- A service proc has no channel to "wake" a parked runner anyway. Runners poll for
  `ready.json` every 2 s.

**The real split** is about mechanism: cdx's dedicated daemon, grk and mus's settlement
write-through, or cld's fix-the-lane approach followed by scheduler event-wake. The
measurements [above](#what-i-re-verified) settle it in favour of cld's sequencing. cdx's
correctness fixes and grk's bead-close hook are folded in.

## Resolving the disagreements

### cdx daemon versus fixing the lane

- cdx's diagnosis is right: blind trigger, publication race, rich resolution semantics,
  and local versus remote freshness.
- Its design is the right shape *if* a daemon is ever built: wakeups as hints, a periodic
  repair timer, shadow mode, a single writer, `sase_core` ownership, and explicit
  stop/update semantics.
- But every measured delay has a job-model fix that gets most of the gain:
  - the trigger is pointed at the wrong files;
  - the resolver wastes 97% of its work on dead waiters;
  - the lane convoys behind syncing.
- The daemon would add a permanently resident process and a second lifecycle. It would
  also need an `update` restart path, a maintenance policy, and single-instance
  guarantees (see sase-14x).
- It buys ~1–4 s more. Keep cdx's design as the
  [Phase 3](#phase-3-resolver-service-proc) specification.

### grk and mus settlement write-through

- The idea is attractive because settlement knows exactly which agent just finished.
- But full resolution in the finalizer means:
  - a ~5 s index build;
  - session-terminal semantics: a member finishing does not mean the session is done;
  - the fresh-membership confirmation;
  - cross-project waiters.
- All of that would run inside a path whose contract is "must never fail settlement". It
  would also run concurrently across simultaneous completions, which creates the
  two-writer problem mus itself warns about.
- **Resolution: keep the poke, make it a signal rather than a resolution.** The pulse
  already exists. Have the resolver (the job) watch it. grk's bead-close hook survives in
  the same form: bead publish or sync touches a pulse that wakes the resolver.

### gem Tier 1 faster lanes

gem's Tier 1 is to move `wait_checks` to the 5 s `hooks` lane, or shorten the `waits`
interval.

- Rejected. A shorter interval does not help a blind trigger. Fires stay gated by
  `max_quiet`.
- Moving a 29 s job into `hooks` would make every Patch-lifecycle tick (hooks → mentors →
  workflows) wait behind it. That lane already overruns at 7.0 s per 5 s cycle.
- Interval tuning becomes useful only *after* the trigger and the dead-waiter scan are
  fixed. That is why [Phase 1](#phase-1-fix-the-lane) gives `wait_checks` its own fast
  lane.

### gem Tier 2 faster fallback

gem's Tier 2 is to cut the runner fallback from 60 s to 5–10 s.

- Rejected as harmful. Each fallback pass is a ~5 s full project index build.
- At 19–25 live waiters, a 5 s cadence means roughly 19–25 builds running continuously:
  tens of cores' worth of JSON reading on a host already at load ~20.
- The correct direction is the opposite. Once `ready.json` is reliable, **lengthen** the
  fallback (cld).

### Maintenance-mode objection

This objection was raised by gem and grk.

- Weaker than stated, because parked runners already ignore maintenance via the fallback.
- It remains a real design obligation for any new resident process: decide explicitly
  whether waits should progress during maintenance.

### Job count

There are 29 job placements and 28 distinct jobs, because
`stale_running_cleanup` sits in both `hooks` and `checks`. cdx is right; gem's "29 jobs"
counts placements.

## Adjusted requirements

These are deliberate changes to what you asked for.

| # | Adjustment | Why |
|---|---|---|
| **R1** | **The goal becomes a latency target, not a migration count.** Proposed target for named-agent waits: dependency session terminal → `wait_completed_at` **p50 ≤ 5 s, p95 ≤ 15 s** after Phase 1, tightening to p95 ≤ 5 s only if Phase 2 is built. Bead waits: **≤ 30 s after the close is pushed.** | "Sooner" cannot choose between a config fix and a daemon without a number. |
| **R2** | **Split "wake sooner" into three measured segments:** release latency, `ready.json` observation, and release → `run_started_at` admission. Treat admission as a sibling track, in scope for the goal but not for `wait_checks`. | Admission is now the larger segment (p50 ~45–50 s), and no resolver design touches it. |
| **R3** | **Measure first.** Record `wait_release_source` (`ready_json` / `runner_fallback` / `startup` / `manual`) and the release latency in `agent_meta.json`. | Today this can only be recovered by grepping runner logs and fuzzy-matching names. |
| **R4** | **Readiness correctness is a requirement, not a nice-to-have.** Publish `ready.json` atomically, treat malformed or unreadable files as not ready, and keep a single writer per waiting generation. | A faster but premature release is a regression. A faster observer widens today's race window. |
| **R5** | **Every event path is additive. The polling backstop is permanent.** | Events get dropped: inotify is not recursive, can overflow, and is Linux-only. The tailnet includes a Mac. |
| **R6** | **Bead waits are in scope.** | Bead closes never touch an `ace-run` trigger. They are gated by sidecar sync. |
| **R7** | **Any resident process must reach parity on lifecycle.** It must restart on `sase update`, have an explicit maintenance policy, be guaranteed single-instance, and preserve job-grade diagnostics. | `sase update` restarts only `scheduler`. sase-14x shows what duplicate resident processes do to athena. |
| **R8** | **Shared readiness and ownership policy goes in `sase_core`.** Trigger-wire changes go through sase-core, the bindings and the `sase-core-revision.txt` pin. | This follows the Rust-core boundary. The trigger decision already lives in `axe_chop/decision.rs`. |

## Recommended solution

### Phase 0 Instrument

*Effort: hours.*

- Stamp `wait_release_source` and `wait_release_latency_s` when `record_wait_completed_at`
  runs.
- Add `admission_latency_s` (`run_started_at − wait_completed_at`).
- Surface the 883-dead-waiter backlog as a counter in the `wait_checks` summary.
- **Exit criteria for Phase 1:** a `runner_fallback` share below 10%, and the
  [R1 targets](#adjusted-requirements).

### Phase 1 Fix the lane

*Effort: small; mostly this repo plus config.*

1. **Correctness first.**
   - Write `ready.json` via temp file plus `os.replace`. The TUI run-now writer
     (`_directive_persistence._write_json_file`) already does this, so reuse that pattern.
   - Make `read_ready_result` return *not ready* on decode or read errors, so the runner
     retries on the next poll.
   - This step stands alone and should ship regardless of the rest.
2. **Point the trigger at the signal that already exists.**
   - Add `{path: projects, glob: "*/artifacts/.ace_refresh_pulse"}` to the `wait_checks`
     and `bead_claim_checks` triggers.
   - Make `write_waiting_marker` touch the same pulse.
   - Drop the `ace-run/*` entry, or narrow it so it stops matching 2.3k lock files.
   - Keep `max_quiet` as the repair backstop.
   - Fix `tests/test_axe_default_chop_triggers.py` to use the real `YYYYMM/DD/<run>`
     layout, and correct the `docs/axe.md` sentence that promises a re-scan "when a project
     gains a new agent artifact".
   - Separately, the accumulation of leaked lock files in `ace-run/` deserves its own
     cleanup.
3. **Resolve live waiters only.**
   - Enumerate waiters from the artifact index, which `waiting.json` publication already
     updates, instead of walking 16.9k directories.
   - Skip markers whose runner is dead, using PID plus start identity to guard against PID
     reuse.
   - Add an hourly housekeeping sweep that archives `waiting.json` for runners dead longer
     than N hours.
   - *Verify* that a revived runner re-resolves on startup before parking (the
     `initial_dependencies_resolved` path suggests it does) and records its PID before it
     can be filtered.
4. **Break the convoy.**
   - Give `wait_checks` its own routine (for example `agent_waits`, interval 2 s). With a
     pulse trigger, an idle tick costs ~37 stats, so a short interval is cheap.
   - Move `sidecar_auto_sync` into its own routine.
   - Investigate `bead_claim_checks`'s 33 s runs (likely the same full-history walk), then
     leave it and `epic_launch_flush` in `waits`.
5. **Runner side.**
   - Optionally shorten the `ready.json` existence poll from 2 s to 0.5 s. It is a single
     `stat`, unlike the fallback.
   - Once Phase 0 shows at least 90% of releases via `ready.json`, **lengthen**
     `_WAIT_DEPENDENCY_FALLBACK_INTERVAL` from 60 s to 180–300 s. That removes about
     95 s/min of index building on athena today.
6. **Bead waits.** After `sidecar_auto_sync` fast-forwards a beads clone, touch the
   affected project's pulse so `wait_checks` runs immediately. Keep the existing per-tick
   bead hint for live bead waiters.

**Expected result:** named-agent release ~2–6 s, down from p50 ~21–33 s. `wait_checks`
runs take seconds instead of ~29 s, the `waits` lane stops overrunning, and parked-runner
background I/O drops.

### Phase 2 Event-wake for jobs

*Optional, medium; crosses into sase-core.*

Add an opt-in `wake: true` for `fs` triggers that watch explicit *files* (pulse and nudge
files), not trees:

- On Linux, the routine places inotify watches on them, debounces (~250 ms), and runs
  that single job immediately, outside the tick barrier.
- The per-job no-overlap lock still applies, and the run is recorded normally with reason
  `wake: <path>`.
- Elsewhere, or when a watch fails, it falls back to today's polling plus `max_quiet`.

Build this only when more than one domain needs it. The likeliest second user is
Patch-lifecycle progression: the hook wrapper's completion line and check-output writes
could become nudges. For `wait_checks` alone, Phase 1's 2 s pulse lane captures most of
the benefit.

### Phase 3 Resolver service proc

*A `wait_resolver` service proc; conditional.*

Build it only if, after Phases 1–2, p95 release latency is still above ~10 s, or if
resolution cost still matters at scale. If you build it, use cdx's design:

- a plain `command:` service proc, not a new reserved builtin;
- wakeups as hints plus a ~30 s repair timer;
- shadow mode before publishing;
- a single explicit writer;
- `sase update` restart ([R7](#adjusted-requirements));
- carried-over diagnostics;
- `wait_checks` kept as a backstop job.

### Parallel track for admission latency

*This is not a migration.*

The ~11 s capacity-only slot scan under a host-wide lock is now the dominant "ready but
not running" cost. It also scales with history, like everything above.

Revisit the host-resource-diet work. An index-backed capacity query, or a shared scan
with event invalidation, would cut release → start time far more than any resolver
change. Fold this into the existing epic or follow-up rather than this one.

### Leave everything else as jobs

| Lane | Jobs | Verdict |
|---|---|---|
| hooks (5 s) | `hook_checks`, `mentor_checks`, `workflow_checks`, `pending_checks_poll` | Keep. These are Phase 2 wake candidates. Measure hook-completion → `hook_checks` latency first, since its trigger watches `*.sase` and `*.gp`, not the hooks shard. |
| hooks | `comment_zombie_checks`, `suffix_transforms`, `orphan_cleanup`, `stale_running_cleanup` (+ `checks` backstop) | Keep. PID death has no filesystem proxy, and the dual placement is the reliability pattern. |
| waits (10 s) | `wait_checks` | **Keep + Fix + own lane** (Phase 1). Daemon only in Phase 3. |
| waits | `bead_claim_checks` | Keep + fix the trigger + investigate its 33 s runtime. |
| waits | `sidecar_auto_sync` | Keep + own lane + post-sync pulse. It is the biggest lever for bead waits. |
| waits | `epic_launch_flush` | Keep (recovery work). |
| checks (5 m) | `bead_task_triage`, `plugins_required`, `pr_submitted_checks` | Keep. cld notes a minor bug: `CheckCycleRunner._first_cycle` is always true in a fresh subprocess. Fix it in code. |
| usage (60 s) | `usage_refresh` | Keep. It is deliberately proc-less and already due-aware. |
| comments (60 s), external_mirror (15 m) | `comment_checks`, `external_issue_mirror`, `external_pr_mirror` | Keep. A future webhook *listener* would be the daemon, and it would nudge these jobs. |
| housekeeping (1 h) | `error_digest`, `notification_store_compact`, `managed_tmp_reap`, `proc_runtime_sweep`, `disk_pressure`, `bead_stale_cleanup`, `gate_turn_reclaim`, `artifact_link_backfill`, `artifact_run_prune` | Keep. Bounded batch maintenance is the archetypal job. `gate_turn_reclaim` deadline handling could use a faster lane, but not a daemon. |
| (separately configured) | `refresh_docs` | Keep. Scheduler admission and deduplication matter more than latency here. |

**Totals:** 0 migrations. Confirmed defects: the blind trigger, the dead-waiter scan, the
tick convoy, and the `ready.json` race. Also one admission-latency track, about six
event-wake candidates, and one optional plugin consolidation (`tg_outbound`).

Consider recording "daemons listen; jobs reconcile" as a decision record so the next
proposal starts from the litmus and a measurement, not from taxonomy.

## Confidence and open questions

- **High confidence:**
  - the trigger mismatch;
  - the dead-waiter counts;
  - the tick convoy;
  - the share of releases handled by the fallback;
  - the `ready.json` read/write race;
  - the scan and index-build timings at today's load.

  I re-measured each one directly.
- **Medium confidence:** the latency distributions. The samples are small (n=21 and n=5
  for release; n=45 for admission), and name matching is heuristic. The admission gap may
  include some `%q` capacity queueing that never logged "Waiting for a runner slot".
- **Open questions:**
  - Does any resume or revive path depend on a dead runner's `ready.json` or
    `waiting.json`?
  - Is `bead_claim_checks` slow for the same reason as `wait_checks`?
  - What is the real hook-completion latency?
  - How much of the admission gap is the scan itself and how much is lock convoying?
  - Once `wait_checks` leaves, does `waits` still need a 10 s interval?

## Scope and inputs

Consolidated report by the lead researcher, 2026-10-07. It merges five independent reports
(`cdx`, `cld`, `grk`, `mus`, `gem`) with my own re-verification against sase master
`aebe28de84` and live state on athena (measured 13:30–13:45 EDT, load average 16–21).

## Sources

**Researcher reports** (now in this directory):

- `wait_wakeup_jobs_vs_service_procs__cdx.md`
- `wait_wakeup_jobs_vs_service_procs__cld.md`
- `wait_wakeup_jobs_vs_service_procs__grk.md`
- `wait_wakeup_jobs_vs_service_procs__mus.md`
- `wait_wakeup_jobs_vs_service_procs__gem.md`

**Code verified at sase `aebe28de84`:**

- `src/sase/default_config.yml` (waits routine)
- `src/sase/axe/chop_policy_snapshots.py`
- `src/sase/axe/lumberjack.py`
- `src/sase/axe/run_agent_wait.py`
- `src/sase/axe/run_agent_wait_deps.py`
- `src/sase/axe/run_agent_wait_slots.py`
- `src/sase/axe/run_agent_runner.py`
- `src/sase/axe/run_agent_runner_refresh.py`
- `src/sase/axe/run_agent_exec_markers.py`
- `src/sase/axe/run_agent_wait_markers.py`
- `src/sase/scripts/_chop_wait_checks_run.py`
- `src/sase/turns/settlement.py`
- `src/sase/main/update_restart.py`
- `src/sase/core/wait_dependency_resolution/_index.py`

**Live state on athena:**

- `~/.sase/axe/lumberjacks/{waits,hooks}/status.json`
- `~/.sase/axe/lumberjacks/waits/chops/wait_checks/runs/`
- `~/.sase/axe/lumberjacks/waits/logs/output.log`
- `waiting.json` and `agent_meta.json` liveness across `~/.sase/projects/*/artifacts/ace-run/`
- October runner logs in `~/.sase/workflows/202610/`
- Timed calls to `_collect_runner_slot_records()` and `build_wait_dependency_index()`

**Commits and beads:**

- `5a65fa4fc1` (sase-3e daemon revert)
- `8e4002bb4d` (script-only jobs)
- bead `sase-14x` (duplicate scheduler copies on athena)
