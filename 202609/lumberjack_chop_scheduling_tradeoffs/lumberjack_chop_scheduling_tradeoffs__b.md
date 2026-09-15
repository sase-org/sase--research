# Retiring lumberjacks in favor of per-chop scheduling: a critique

_Researcher B · 2026-09-15 · sase `688b2d4eac`, sase-core `e6d08ad`, sase-telegram `9c3a600`_

## Question

Should AXE stop grouping chops into lumberjacks and instead schedule and run each chop
independently? In particular, does any current lumberjack contain chops that depend on
the order in which they run?

## Short answer

**No lumberjack runs its chops in order today, so no chop can depend on in-lane
ordering.** Since `2c6464b1bf` (2026-04-08), every eligible chop in a tick is submitted
to a `ThreadPoolExecutor` at once, and results are collected with `as_completed`
(`src/sase/axe/lumberjack.py:227-235`). The order of the `chops:` list in YAML affects
display only. The docs state the contract directly: "Scheduled script chops within one
lumberjack tick run concurrently" (`docs/axe.md:813`).

Several chops do have **producer → consumer** relationships on durable state, such as
hooks → mentors, background-check launchers → `pending_checks_poll`, and
`tg_outbound` → `tg_inbound`. These already tolerate running in either order and
converge on a later tick. Many of these pairs already span different lumberjacks. None
would break if the lumberjack wrapper went away.

The real hazard in the fast lanes is not ordering. It is **concurrent writers rewriting
Patch fields from the same stale tick snapshot**, together with an **agent-launch budget
that the config still describes but that no longer exists**. Lumberjacks do not protect
against either today, and removing them would neither cause nor cure them.

Ordering is therefore not what blocks the idea. What blocks it is that a lumberjack
does six other jobs, detailed below. The main benefit you would get from removing
lumberjacks is freedom from tick-bound head-of-line blocking, and that can be had much
more cheaply without removing the concept. My recommendation, at the end, is to
**decouple chop dispatch from the tick inside the existing lumberjack process first, and
not pursue full removal now.**

## Ordering audit: every lumberjack, every chop

### The mechanism rules out ordering dependencies

- `Lumberjack._run_tick` filters chops by `enabled` and `run_every`. It then submits
  **all** remaining chops to one `ThreadPoolExecutor()` and waits on `as_completed`
  (`lumberjack.py:212-235`). The default worker count is `min(32, cpu+4)`, and no
  lane has more than 9 chops, so every eligible chop starts at the same moment.
- Each chop runs as its own subprocess (`chop_runner_script.py:336-345`). Guards and
  triggers are evaluated independently per chop (`chop_policy_preflight.py:25-112`).
  No config field expresses "after chop X". Proposal `wait_on` exists, but it orders
  *agents launched by one chop* (`sase_chop_refresh_docs.py:115`), not chops.
- Chops ran sequentially only from 2026-02-21 (`21a8c2609b`, `65756c51b8`) to
  2026-04-08 (`2c6464b1bf`). Since then YAML list order has had no runtime effect.
- Before lumberjacks there was a single-process scheduler in which one
  `HookJobRunner` ran hook, mentor, and workflow checks back to back. The only
  ordering-era behavior that survives in documentation is the "shared agent-launch
  budget" (below). It stopped being shared when chops became subprocesses on
  2026-02-21.

Any chop that depended on order would already be flaky. What remains are data-flow
relationships.

### Relationships per lane

Legend:
- **Hard** means the result is wrong if the order flips.
- **Soft** means a producer/consumer pair that converges on a later tick.
- **Race** means concurrent writers with lost-update risk. This is independent of
  ordering.

**hooks (5s):** `hook_checks`, `mentor_checks`, `workflow_checks`,
`pending_checks_poll`, `comment_zombie_checks`, `suffix_transforms`,
`orphan_cleanup`, `stale_running_cleanup`

| Relationship | Kind | Evidence |
| --- | --- | --- |
| `hook_checks` → `mentor_checks`: mentors start only once the snapshot shows hooks finished | Soft (≈1 tick) | `ace/scheduler/mentor_checks.py:48-110` reads hook readiness from the snapshot. Any `.sase` write trips the fs trigger for all six Patch chops on the next tick. |
| `hook_checks` → `workflow_checks`: failed hooks lead to fix-hook workflows | Soft | `workflows_runner/starter.py` reads hooks from the snapshot. |
| `workflow_checks` → `mentor_checks`: a failed hook counts as "ready" once a fix or summarize suffix exists | Soft | `mentor_checks.py:90-103` |
| `pending_checks_poll` → `workflow_checks`: an applied `[critique]` comment leads to a CRS launch | Soft | `ace/scheduler/checks_runner.py:513-519` |
| `pending_checks_poll` moves a Patch to Submitted/Archived while its siblings still see the old status | Soft, with side effects | The siblings' terminal-status checks read the snapshot. At most one extra round of hook, mentor, or workflow work, later cleaned up by `suffix_transforms`. |
| `comment_zombie_checks`, `workflow_checks`, and `pending_checks_poll` all rewrite COMMENTS | **Race** | `set_comment_suffix` rebuilds the whole comment list from the caller's snapshot copy and writes it under the lock **without re-reading** (verified: `ace/comments/operations.py:167-191, 336-371`; `ace/scheduler/comments_handler.py:36-46`). A zombie sweep can erase a CRS `running_agent` suffix that `workflow_checks` just wrote. |
| `hook_checks` rewrites changed hook entries whole | **Race** | `merge_hook_updates` re-reads under the lock but replaces each changed hook with the snapshot-built entry (verified: `ace/hooks/persistence.py:191-212`). That can drop a `claiming-`/`running_agent` suffix that `workflow_checks` wrote. |
| `suffix_transforms` vs. everyone | Mostly safe | `84da4721c2` (2026-07-20) made its hook and comment edits re-read under the lock. This is the only race fix between chops in the history. |
| `mentor_checks` + `workflow_checks` share `max_agent_runners` | **Race** (budget) | See "the phantom per-tick budget" below. |
| `orphan_cleanup` / `stale_running_cleanup` vs. the claim writers | Race (low) | Releases happen under the lock, but the PID liveness check happens before the lock is taken. Unrelated finding: `orphan_cleanup` only reads claims for `all_patches[0].file_path`, so only the first project is checked (verified: `ace/scheduler/orphan_cleanup.py:31-39`). |
| Inside `stale_running_cleanup`: monitor reconcile, then claim release | **Hard, but inside one chop** | `axe/hook_jobs.py:375-435`. This is sequencing within a single script, not between chops. |

**waits (10s):** `bead_claim_checks`, `epic_launch_flush`, `sidecar_auto_sync`,
`wait_checks`

- `bead_claim_checks` and `wait_checks` touch disjoint data: CLAIMED beads and
  pre-launch claims versus closed beads, `done.json`, and `ready.json`. No relationship.
- `sidecar_auto_sync` → `wait_checks` is **soft**. The sync fast-forwards the beads
  clone that `wait_checks` reads for `%wait(bead=…)`. The waiting runner also polls
  every 2s and resolves dependencies itself every 60s, and it re-hints the sync on a
  ten-minute outage backstop (`docs/axe.md:254-265`).
- `epic_launch_flush` is independent.

**checks (300s):** `bead_task_triage`, `plugins_required`, `pr_submitted_checks`,
`stale_running_cleanup`, `usage_refresh`

- No relationships inside the lane.
- `pr_submitted_checks` → `pending_checks_poll` (hooks lane) is **soft and already
  crosses lumberjacks**.
- `stale_running_cleanup` is a second copy of the hooks-lane chop. The overlap guard is
  keyed per `(lumberjack, chop)`, so both copies can run concurrently every five
  minutes. Releases are idempotent under the lock.

**comments (60s):** `comment_checks`

- A single chop. `comment_checks` → `pending_checks_poll` (hooks lane) is soft and
  crosses lumberjacks. Its only duplicate guard is whether the pending-check file
  exists, so the worst case is a redundant remote check.

**external_mirror (900s):** `external_issue_mirror[<project>]`,
`external_pr_mirror[<project>]`

- The instances are independent. Cursor and backoff state live under
  `~/.sase/external_mirror/`, deliberately separate from any lane
  (`docs/axe.md:1110-1112`). PR adoption re-checks ownership under the ProjectSpec lock
  (`docs/axe.md:1142-1145`).
- Downstream, `bead_task_triage` (checks lane) picks up newly mirrored task beads on
  its next pass. That is soft and crosses lumberjacks.

**housekeeping (3600s):** `error_digest`, `notification_store_compact`,
`managed_tmp_reap`, `proc_runtime_sweep`, `disk_pressure`, `bead_stale_cleanup`,
`gate_shell_reclaim`, `artifact_link_backfill`, `artifact_run_prune`

- No ordering relationships.
- `disk_pressure` can run the managed-temp and proc-runtime cleanup passes early, in
  the same tick as `managed_tmp_reap` and `proc_runtime_sweep`. Its description says
  those owners "encode deletion policy". `proc_runtime_sweep` rechecks the proc store
  under its lock in Rust (`default_config.yml:1269-1288`). This is overlap, not order.
  I did not audit the temp reaper's own concurrency.
- `bead_stale_cleanup` and `bead_task_triage` (checks lane) partition ready task beads
  by the +1 bar, so they do not compete for the same bead.

**telegram (5s, user config in `~/.config/sase/sase.yml`, scripts from `sase-telegram`):**
`tg_inbound`, `tg_outbound`

- `tg_outbound` → `tg_inbound` is **soft**:
  - Outbound sends a message, records a pending callback action, and advances a
    high-water mark while holding its own exclusive `flock`
    (`sase_tg_outbound.py:366-384`, `outbound.py:152-177`).
  - Inbound later consumes the human's button press and removes the action through the
    shared host store (`pending_actions.py`, delegating to
    `sase.notifications.pending_actions`).
  - Human reaction time dominates, and neither order in a tick is wrong.
- The lane's description ("Keep Telegram transport chops in this lane… so bot network
  calls do not delay unrelated work") is another example of lanes being used to fence
  off head-of-line blocking.

### The phantom per-tick budget

`default_config.yml:969-971` says `workflow_checks` shares "max_agent_runners and the
current tick's agent-launch budget" with mentors.

In today's code that is not true:

- `HookJobRunner._agents_started_this_tick` is an instance field
  (`axe/hook_jobs.py:90-91, 155-206`).
- `BuiltinChopRuntime` builds a fresh `HookJobRunner` inside each chop subprocess
  (`chops/builtin.py:59-74`). The counter therefore only limits launches within one
  chop run.
- `RunnerPool` and `SharedRunnerPool` (`axe/runner_pool.py`) have no callers outside
  lazy exports in `axe/__init__.py`. `Lumberjack`'s docstring (`lumberjack.py:86-90`)
  and `docs/axe.md:1338-1345` still describe `SharedRunnerPool` as the coordination
  mechanism, so both are stale.
- The only limit that works across chops is `count_agent_runners_global()`, which
  counts `running_agent` suffixes already written to disk.

According to the subagent's reading, which I did not reproduce, mentor `STARTING` lines
and CRS/fix-hook suffixes are written only around or after launch. `mentor_checks` and
`workflow_checks` could then overshoot `max_agent_runners` (up to about 2×) when both
fire in the same tick.

**The implication for your idea:** the one "shared tick resource" a reader might expect
lumberjacks to provide is already gone. Scheduling chops independently would change how
often these two chops overlap, not whether the budget holds. A real fix needs a
cross-process reservation taken under a lock before launch, whatever the topology.

### Would removal make any of this worse?

Mostly no, with one nuance:

- **Stale snapshots.** Per-chop runs that build their own snapshot at dispatch time
  would read *fresher* data than a shared tick snapshot. That narrows the window for
  the COMMENTS and hook-entry lost updates without eliminating it.
- **Convergence latency.** Chains like hook → mentor currently converge in one 5s tick
  because an fs trigger fires every Patch chop together on the next tick. A per-chop
  scheduler has to keep at least that responsiveness. An fs trigger plus a short poll
  per chop does, and could even improve it, since a consumer would not wait for the
  producer's whole tick to finish.
- **Overlap patterns.** The racy hooks-lane writers currently fire together whenever
  any `.sase` file changes. That is already the worst case for overlap, so independent
  cadences would not increase it.

## What a lumberjack actually does today

Removing lumberjacks means replacing every one of these responsibilities, not just the
scheduling loop.

| # | Responsibility | Where it lives | Replacement needed if lumberjacks go away |
| - | --- | --- | --- |
| 1 | **Supervised process boundary.** The orchestrator runs one `sase axe lumberjack run <name>` child per lumberjack. It restarts children with exponential backoff and raises a single crash-loop alert per episode. `sase axe restart` verifies a fresh heartbeat for each lumberjack. | `orchestrator.py:100-134, 174-297`; `_process_restart.py:65-250` | Choose between one process per chop (33 effective chops on this host, counting `for_each` instances, against 7 processes today) and a single scheduler process, which gives up the fault isolation between lanes. |
| 2 | **Tick cadence.** A `schedule` job runs every `interval` seconds. | `lumberjack.py:520` | A timer per chop. `run_every` already exists, but it can only slow a chop below its lane's rate; it cannot make one run faster. |
| 3 | **Shared per-tick snapshot.** Once per tick, the lumberjack loads every Patch, applies the query filter, and serializes `all_changespecs.json`, `filtered_changespecs.json`, and `context.json` for all of its chops. | `lumberjack.py:177-208` | Either a snapshot per chop, which multiplies `find_all_patches` work on the 5-second lanes, or a shared snapshot cache with an explicit freshness rule. |
| 4 | **Shared defaults.** `chop_timeout`, `wait_runners`, and `env` are set once per lane and inherited by its chops. The user's `telegram` lane uses lane-level `env` for its bot username. | `_config_types.py:198-215`; `~/.config/sase/sase.yml` telegram lane | Per-chop repetition, or some other grouping construct such as a profile. |
| 5 | **State namespace and chop identity.** Everything is keyed by `(lumberjack, chop)`: run history, `checkpoint.json`/`seen.json`/`policy.lock` for triggers and `once_per`, `chop_timestamps.json`, and `agent_chops.json`. Several chops also keep durable "lane state" in `runtime.context.state_dir`: `bead_task_triage`, `plugins_required`, `bead_stale_cleanup`, `sidecar_auto_sync`, and `artifact_link_backfill`. | `_state_lumberjack.py:157-337`; `chop_policy_state.py:26-40`; `docs/axe.md:1481-1519`; scripts at `sase_chop_bead_task_triage.py:588`, `sase_chop_plugins_required.py:617`, and others | Migrating state paths. Precedent: moving the external mirrors out of `checks` in `fb33e3c1f9` required a dedicated `pr_mirror_state_dir()` plus a migration from the old checks-lane files. |
| 6 | **Operator and core surfaces.** These include `sase axe lumberjack list/run/status`, `chop run -L`, the Axe tab tree (lumberjack rows with chop children), maintenance pauses, per-lane spawn-rate and no-op metrics, overrun classification (measured against the lumberjack's interval), and Rust config composition and status wires keyed by lumberjack. | 116 files / 1,444 references in `src/sase`; 15 files / 371 references in `sase-core/crates` (`config/axe.rs`, `axe_status/wire.rs`, `axe_overrun/*`) | A cross-repo breaking change touching the Rust wire/API, Python bindings, the TUI, CLI, docs, user config, and the `sase-telegram` plugin's documented "telegram lumberjack" contract. |
| 7 | **Head-of-line coupling (a liability, not a feature).** The tick's `with ThreadPoolExecutor()` block waits for the slowest chop. `schedule` then sets the next run to *finish time + interval* (`schedule.Job.run` sets `last_run = now()` after the job and reschedules from there). | `lumberjack.py:229-235`; `schedule/__init__.py:674-693` | This is what removal would fix. |

### Evidence that responsibility 7 is the real pain

- The commit that introduced concurrent execution (`2c6464b1bf`) did so explicitly to
  change "tick duration from sum(all_chop_times) to max(all_chop_times), preventing
  slow chops from delaying others." It reduced head-of-line blocking without removing
  it.
- `fb33e3c1f9` (2026-08-12) created the dedicated `external_mirror` lane so that remote
  polling "never overruns its own tick or delays the checks lane's PR-submission and
  workspace-claim work" (`default_config.yml:1174-1180`). A lane was added to work
  around blocking inside a lane.
- A follow-up (`1f388edee0`) had to delete duplicate mirror entries that a concurrent
  branch had reintroduced under the old lane. Moving chops between lanes has a real
  merge and placement cost.
- The TUI's overrun indicator (`docs/axe.md:1296-1307`) exists to flag "a chop whose
  run blocked its lumberjack's tick for at least the lumberjack's `interval`."
- In the hooks lane, `chop_timeout: 90s` means one hung `hook_checks` can delay
  `pending_checks_poll`, `stale_running_cleanup`, and the rest of that 5-second lane by
  up to about 95 seconds.

The observed load on this host right now is modest. The durations below are the
median and maximum over the newest 10 runs of each chop:

| Lane (interval) | Slowest chop, median / max | Comment |
| --- | --- | --- |
| hooks (5s) | `stale_running_cleanup` 0.79s / 0.95s | All seven fs-triggered chops were `skipped` in about 10ms: the idle-CPU diet works. |
| waits (10s) | `wait_checks` 0.00s / 1.54s; `sidecar_auto_sync` 0.83s / 3.42s | Fine. |
| telegram (5s) | 0.04s / 0.07s | Fine. |
| comments (60s) | 2.95s / 3.83s | Fine. |
| checks (300s) | `pr_submitted_checks` 5.48s / 7.34s | Fine. |
| housekeeping (3600s) | `artifact_run_prune` 34.0s / 74.4s (2 of 10 failures) | Irrelevant at a one-hour cadence. |

So head-of-line blocking is a **tail risk** (a hung or slow chop in a fast lane), not a
steady-state problem. That matters when weighing a large migration.

### Subtleties worth knowing regardless of the decision

- **Chops already run as separate subprocesses.** Crash isolation for *chop code* is
  per chop today. The lumberjack process boundary only protects against failures in
  the scheduler loop itself: bad query parsing at construction, state-write errors,
  tick exceptions. Much of the fault-isolation argument for lumberjacks is therefore
  weaker than it looks.
- **Overlap prevention is already per chop.** `run_script_chop_once` refuses to start a
  chop while a live run of the same `(lumberjack, chop)` is recorded as `running`
  (`chop_runner_script.py:77-94`). Manual CLI and TUI runs rely on this today, so a
  per-chop dispatcher would not need a new dedupe mechanism.
- **Manual runs rebuild the shared tick snapshot.** `build_oneshot_context` writes the
  same `tick/all_changespecs.json` and `tick/filtered_changespecs.json` paths that the
  scheduled tick uses (`chop_runner_context.py:39-71`). Writes are atomic
  (`chop_script_context.py:47-62`), so readers never see torn JSON. However,
  `BuiltinChopRuntime` loads `all_patches` and `filtered_patches` lazily and separately
  (`chops/builtin.py:45-57`), so a chop *can* read the two files from different builds
  when a manual run lands mid-tick. This is harmless in practice. It does show that
  "one snapshot per tick" is a convention rather than an invariant, and a per-chop
  scheduler would make per-run snapshots the natural design.
- **The duplicated `stale_running_cleanup`** in `hooks` (5s) and `checks` (300s) exists
  only as a backstop in case the *hooks lumberjack process* is disabled, restarting, or
  crash-looping (`default_config.yml:1157-1165`). It is a direct product of the lane
  process model. Per-chop scheduling would either make it unnecessary or require
  multi-cadence identities.
- **Trigger preflight does not need the patch snapshot for `fs` triggers.** It needs it
  only for `patch` guards (`chop_policy_preflight.py:49-92`). The lumberjack
  nevertheless rebuilds and serializes the full snapshot every 5 seconds before
  checking any trigger (`lumberjack.py:177-208`), even when every hooks-lane chop will
  skip. That is a small but real idle cost that any redesign could eliminate by
  evaluating triggers first and building context lazily.

## Critique of the idea

### Strongest arguments for removing lumberjacks

1. **Cadence already belongs to chops.** Per-chop `run_every`, `timeout`, `fs` and
   `git.commits_since` triggers, `once_per`, `inhibit_if` guards, and `for_each`
   targets together decide when a chop really runs. The lane interval has become a
   polling floor plus a place where chops wait for each other.
2. **Lanes are a recurring workaround for head-of-line blocking.** The
   concurrent-execution commit, the `external_mirror` lane, the telegram lane's stated
   purpose, the overrun indicator, and the `stale_running_cleanup` backstop all exist
   because one chop can hold up its neighbors or its process. Scheduling per chop
   removes the problem instead of partitioning it.
3. **Placement is a source of bugs.** Moving a chop changes its state path, which
   needed a migration in `fb33e3c1f9`, and invited duplicate entries in `1f388edee0`.
4. **The mental model gets simpler.** There would be one unit (the chop), one cadence,
   and one overrun definition: a chop that exceeds its own cadence.
5. **No ordering dependency stands in the way.** This audit found none.

### Strongest arguments against removal

1. **The benefit is available without removal.** Head-of-line blocking comes from
   `_run_tick` waiting on the whole batch and from `schedule` rescheduling after the
   batch finishes. It does not come from grouping. A lane process could keep a due
   time per chop and dispatch each chop when due and not already running, without
   waiting for siblings. The pieces already exist: per-chop timestamps, overlap
   dedupe, run history, and preflight.
2. **Lumberjacks still carry real, non-scheduling value**: a restart and crash-loop
   boundary per lane, heartbeat-verified restarts, shared defaults (the telegram lane
   uses `env`), a state namespace that live lane state depends on, and the operator
   and TUI hierarchy. Every one of these would need a replacement or a migration.
3. **Blast radius is large and crosses repositories**: 116 Python files, 15 Rust files
   (config composition, status and overrun wires), user config in chezmoi, the
   `sase-telegram` plugin's documented contract, docs, and many tests. Under the Rust
   core boundary rule, the config and status reshaping must land in `sase-core` first.
4. **The measured pain is small.** On this host every fast lane finishes a tick in
   under about 1.5s at the tail. The risk is a hung chop, which is bounded by
   `chop_timeout`, not steady-state lag.
5. **Removal does not fix the actual correctness problems.** The stale-snapshot
   writers and the missing launch reservation are independent of topology, and they
   matter more.
6. **Per-chop processes cost more; a single scheduler couples more.** 33 small
   supervisors would add idle memory (lumberjack RSS is about 12–33 MB each today) and
   more status and heartbeat rows. One scheduler process for all chops would lose the
   property that a stuck or crash-looping hooks loop cannot stop housekeeping or
   telegram delivery.

### Options

| Option | What changes | Gain | Cost |
| --- | --- | --- | --- |
| **0. Status quo** | Nothing | None | Head-of-line tail risk remains; lanes keep multiplying as workarounds. |
| **1. Per-chop dispatch inside lumberjacks** | `_run_tick` becomes a dispatcher: each chop keeps its own next-due time (lane `interval` as the default) and is dispatched when due and idle, without waiting for its siblings. The snapshot is built lazily after preflight, only for chops that fire. | Removes head-of-line blocking and the idle snapshot rebuild. Keeps process, state, UX, and wires. | Moderate and mostly local to `lumberjack.py`, metrics, and overrun semantics. The Rust overrun classifier needs a per-chop cadence input. |
| **2. Demote lumberjacks to "process group + defaults"** | Option 1, plus an optional per-chop `interval`. Lanes remain only as a supervision boundary and a defaults bag. | Chops become the scheduling unit in practice. | Small schema addition in Rust config and the schema; docs. |
| **3. Full removal** | Remove `axe.lumberjacks`; chops become top-level with a per-chop cadence, run under one scheduler or one process each. | Simplest vocabulary. | Breaking config change, state-path migration (including gate generations in lane state), Rust config/status/overrun wires, TUI tree, CLI (`lumberjack list/run/status`, `-L`), restart heartbeat semantics, plugin docs, and a decision about fault isolation. |

One interaction with earlier research: the 2026-09-14 naming report
(`research:202609/scheduler_loop_naming_reassessment.md`) recommends renaming
lumberjacks to **scheduler loops**. Settle the removal question before spending on a
rename. Option 1 or 2 keeps the object and makes "loop" an even better name; option 3
makes the rename moot.

## Correctness follow-ups this research surfaced (independent of the decision)

These are candidate task beads, not filed. The lead should de-duplicate against
researcher A before filing.

1. **COMMENTS lost updates.** `set_comment_suffix` and `remove_comment_entry` should
   transform the list re-read under the lock, as `suffix_transforms` already does
   (`transform_patch_comments_field`), instead of writing back the caller's snapshot
   list.
2. **Hook-entry lost updates.** `merge_hook_updates` should merge suffix fields rather
   than replace whole `HookEntry` objects built from the snapshot.
3. **Phantom agent-launch budget.** Either implement a cross-process launch reservation
   for `mentor_checks` and `workflow_checks`, or correct `default_config.yml:969-971`.
   Delete or wire up the unused `RunnerPool`/`SharedRunnerPool`, and fix
   `docs/axe.md:1338-1345` and the `Lumberjack` docstring.
4. **`orphan_cleanup` scope.** It only inspects the first Patch's project file
   (`ace/scheduler/orphan_cleanup.py:37`).
5. **Pending-check orphan reaper.** Reported by the subagent, not verified by me: a
   remote check that is silent for more than 180s may have its output file reaped and
   be relaunched (`ace/scheduler/checks_runner.py:257-297`).

## Uncertainties

- I verified the COMMENTS and hook-merge write paths, the per-process launch counters,
  the unused runner pool, and the `orphan_cleanup` scope directly. I did **not**
  reproduce the claimed ~2× `max_agent_runners` overshoot, the non-convergence of the
  suffix loss in practice, or the 180s reaper behavior.
- I did not audit the internal locking of the proc, monitor, and managed-temp stores,
  or the Rust bead-claim release conditions.
- Timing data comes from one host (`kellys_mbp`), about 20 minutes after an AXE restart
  (the newest 10 runs per chop). Busier hosts such as athena and apollo may show more
  hooks-lane load.
- Researcher A's report was not consulted.

## Recommendation

**Do not pursue full lumberjack removal (option 3) now. Pursue option 1 instead:
per-chop dispatch inside the existing lumberjack process. Treat option 2 as its natural
follow-up.**

Your instinct is sound on the key technical point. No lumberjack contains chops that
depend on run order, and none has since April 2026, so chops are already independent
units in every sense except scheduling. The thing actually worth removing, though, is
the **tick barrier**: the way a slow chop holds up its siblings. The grouping itself is
not the problem. Option 1 removes that barrier at a small fraction of the migration
cost. It keeps the per-lane supervision boundary, lane state, shared defaults, and the
operator hierarchy that full removal would have to rebuild across `sase`, `sase-core`,
the telegram plugin, and user config. Separately, and with higher priority than any
topology change, fix the stale-snapshot COMMENTS and hook writers and the nonexistent
agent-launch budget. Lumberjacks neither cause nor prevent those bugs, and they affect
correctness today.

**Reconsider full removal if, after option 1 or 2 ships:**

- lanes carry nothing but an interval default and a display group; or
- the lifecycle journal shows lane crash loops are rare enough that per-lane process
  isolation is not worth its cost; or
- you want chops to run on non-AXE hosts or event sources where a lane process is
  unnatural.

Any of these would make lumberjacks vestigial, and removal would then be cleanup
rather than a redesign.
