# Should SASE retire lumberjacks in favor of independently scheduled chops?

Research snapshot: 2026-09-15  
Researcher: A  
Primary SASE revision: `688b2d4eac8f123b03303e37432ba9596c0aee79`  
Telegram plugin revision: `9c3a600327af53187418aa990f2a038fcdac6a36`

## Executive conclusion

There is no supported chop-order dependency inside any current lumberjack. The
runtime deliberately executes eligible sibling chops concurrently, passes the
latency-sensitive hook chops the same pre-tick snapshot, and aggregates results in
completion order. A test explicitly requires concurrency, and the change that
introduced it says the purpose was to stop a slow chop delaying its siblings. Any
chop whose correctness depends on YAML/list order is therefore already broken.

There *are* causal relationships among chops. The strongest are in `hooks` (hook
results enable mentors and workflows), `waits` (a sidecar sync may expose bead state
that unblocks a waiter), and the producer/consumer relationship between remote check
launchers and `pending_checks_poll`. Those relationships are implemented as durable,
eventually reconciled state transitions, not same-cycle sequencing. Today they may
cost an extra tick depending on which concurrent process observes which update first.

This means the idea is semantically feasible, but “remove lumberjacks” and “schedule
each chop independently” should not be treated as the same architectural decision.
The latter fixes a real problem: the current scheduler waits for *all* sibling futures
before the next lane tick, so one slow chop still creates head-of-line blocking. The
former throws away useful config inheritance, state namespacing, UI grouping, shared
snapshot construction, and a low resident-process count.

My recommendation is to pursue independent per-chop scheduling, but not a wholesale
one-resident-process-per-chop rewrite or immediate deletion of the lumberjack concept.
First remove the tick-wide completion barrier while preserving lane/group metadata and
stable `(lumberjack, chop)` identities. Measure that design before deciding whether the
remaining grouping deserves a less colorful name or full removal.

## Scope and method

I inspected:

- the effective live AXE configuration via `sase axe lumberjack list -v`,
  `sase axe chop list -a -j`, and `sase axe status --json`;
- the scheduler, supervisor, context, runner-deduplication, lifecycle, and state-path
  implementations at the SASE revision above;
- all built-in chop entry points and the deeper hook/workflow implementations where
  multiple chops touch the same state;
- the installed Telegram plugin's inbound/outbound chop implementations;
- the concurrency tests and the git commit that changed lumberjack execution from
  sequential to concurrent (`2c6464b1bf`, 2026-04-08).

The live configuration contained seven lumberjacks and 33 expanded chop instances:

| Lumberjack | Interval | Expanded chops | Notes |
| --- | ---: | ---: | --- |
| `hooks` | 5 s | 8 | Seven filesystem-triggered lifecycle chops plus always-on `stale_running_cleanup` |
| `waits` | 10 s | 4 | `epic_launch_flush` and `sidecar_auto_sync` are further limited by `run_every: 30s` |
| `checks` | 300 s | 5 | Includes a second, slower `stale_running_cleanup` schedule |
| `external_mirror` | 900 s | 4 | Two base chops expanded once for each of two enabled projects |
| `comments` | 60 s | 1 | Already effectively a single-chop lane |
| `housekeeping` | 3600 s | 9 | Maintenance, retention previews, gates, and cleanup |
| `telegram` | 5 s | 2 | User-configured inbound and outbound plugin chops |

On the sampled host, the orchestrator plus seven resident lumberjack Python processes
used about 154 MiB of summed RSS. That is only a point-in-time operational observation,
not a linear forecast, but it makes a jump from 7 to 33 resident scheduler children a
cost that should be measured rather than assumed away.

## Direct answer: does any lumberjack depend on chop order?

No—not as a supported or deterministic property.

The decisive evidence is in `src/sase/axe/lumberjack.py`:

1. A tick builds one Patch snapshot and serializes it before dispatch
   (`_run_tick`, lines 145-208).
2. It submits every eligible chop to a `ThreadPoolExecutor` (lines 212-233).
3. It consumes futures with `as_completed`, i.e. completion order, not config order
   (lines 234-235).
4. It does not return to the scheduler until all futures have completed; only then are
   timestamps, metrics, and status aggregated (lines 237-290).

`prepare_chop_run_context` also documents that scheduled chops share one read-only tick
context and receive private run-local copies only to prevent result-file races
(`src/sase/axe/chop_script_context.py`, lines 98-127). The explicit concurrency test
runs two one-second chops and requires the tick to finish in under 1.8 seconds
(`tests/test_axe_lumberjack_tick.py`, lines 409-445). The neighboring test requires a
failure in one chop not to prevent the others from running (lines 448-479).

The historical commit is unusually clear: `2c6464b1bf` changed sequential execution to
a thread pool so tick duration became the maximum chop duration rather than the sum.
All current shipped configurations have therefore lived under unordered sibling
execution, and many current chops were added or substantially revised after that
change.

Submission to the executor happens while iterating the configured list, but that is not
an execution-order contract. On this host the default executor has 12 workers, more
than the largest current lumberjack's nine chops, so all siblings can start without a
queue. Even on a smaller machine, relying on the executor's incidental dequeue order
would be invalid.

### Causal coupling by lumberjack

| Lumberjack | Order verdict | Real coupling |
| --- | --- | --- |
| `hooks` | No same-tick ordering; all eight scripts are concurrent and the Patch-consuming ones read the same pre-dispatch JSON snapshot. | `hook_checks` produces terminal hook states that later enable `mentor_checks` and `workflow_checks`. `pending_checks_poll` consumes results launched by the `checks` and `comments` lumberjacks, and those results can later enable workflows. `suffix_transforms`, zombie checks, and cleanup reconcile the same durable ProjectSpec/workspace domain. Visibility normally occurs on a later tick. |
| `waits` | No deterministic order. | `sidecar_auto_sync` can fetch a closed bead that `wait_checks` needs. If `wait_checks` reads first, it tries again on a later 10-second tick. `bead_claim_checks` and `wait_checks` both inspect agent artifacts but own distinct outcomes (claims versus `ready.json`). |
| `checks` | No in-lane dependency. | `pr_submitted_checks` is a producer for the hooks-lane `pending_checks_poll`. `stale_running_cleanup` is an intentional five-minute backstop for the same script already scheduled every five seconds in `hooks`; this is duplicate schedule-instance semantics, not ordering. The other gate/plugin/usage jobs are independent reconcilers. |
| `external_mirror` | No order. | Four target-expanded instances already run concurrently. Issue mirroring writes bead state and PR mirroring writes Patch state; per-project cursors, store locks, caps, and backoff provide isolation. Their shared concern is remote/API burst load, not sequencing. |
| `comments` | Trivially none. | It has one chop. Its outputs are collected asynchronously by `pending_checks_poll`. |
| `housekeeping` | No required order. | `disk_pressure` may invoke the same managed-temp and proc-runtime owners as the dedicated `managed_tmp_reap` and `proc_runtime_sweep` chops. Concurrent runs may duplicate scans or contend, but the owner-side rechecks/locks are the safety mechanism. `error_digest` may omit errors produced by concurrent housekeeping chops until the next digest; current unordered semantics already allow that. |
| `telegram` | No scheduler-order dependency. | Outbound delivery creates pending actions that inbound callbacks may later consume, but a callback cannot exist before Telegram has delivered the earlier outbound message. The two chops use separate delivery/update cursors, shared locked pending-action storage, and an explicit outbound singleton lock. This is external temporal causality, not a reason to sequence one five-second tick. |

The answer is therefore slightly more nuanced than “the chops are unrelated.” They
are mostly reconcilers in a distributed state machine. Several consume facts that
other chops eventually produce, but none is entitled to observe a sibling's writes in
the current tick.

## A concurrency caveat worth addressing independently

The lack of order dependencies does not prove every shared-state path is perfectly
race-safe. It means those paths already need to be race-safe.

For example, `comment_zombie_checks` and `workflow_checks` both run in `hooks` and can
update different comment entries in the same ProjectSpec concurrently. Both ultimately
call `set_comment_suffix` with the whole `patch.comments` collection from their shared,
pre-tick snapshot. `set_comment_suffix` constructs a replacement list outside the
ProjectSpec lock and `update_patch_comments_field` serializes that caller-provided list
under the lock. The lock prevents torn writes, but two disjoint updates based on the
same stale list can still be last-writer-wins. Eligibility makes a collision on the
*same* comment unlikely (zombie detection needs an old suffix; CRS launch needs no
suffix), but distinct entries can still expose the stale-whole-field pattern.

Other code is visibly hardened for concurrency: many hook mutations re-read under the
lock, fix-hook launch uses an atomic eligibility/claim operation, mentor writes merge
newer terminal states, the notification store has a shared lock, and cleanup owners
recheck state under their own locks. The stale-comments example should be tested and,
if reproduced, fixed regardless of the lumberjack decision. Splitting schedules does
not create the race; it may change overlap timing and make an existing assumption more
or less visible.

This suggests a prerequisite for any scheduler change: introduce order-randomized or
barrier-driven convergence tests for the state-sharing chop pairs. Do not preserve
incidental ordering to hide a lost-update bug.

## What lumberjacks actually provide today

The lumberjack is not just a loop wrapped around a list. It currently provides six
things:

1. **A cadence and fault-domain label.** The orchestrator supervises one child per
   lumberjack and restarts it with per-child backoff. A scheduler-level crash affects a
   cadence cohort but not the other cohorts.
2. **Config inheritance.** `interval`, `chop_timeout`, `wait_runners`, and `env` are
   declared once at lumberjack level and inherited by the chops. The Telegram lane, for
   example, supplies shared credentials/environment to both plugin chops.
3. **Amortized context creation.** Every lumberjack tick scans and filters Patches once,
   serializes two snapshots once, and shares them with all due chops. A naive
   one-`Lumberjack`-object-per-chop conversion would repeat that work for every chop,
   including chops that never inspect Patches. In the five-second `hooks` lane this can
   turn one scan/serialization into eight.
4. **A namespace and durable identity.** Run history, policy checkpoints, once-per
   state, and action linkage are addressed by `(lumberjack_name, chop_name)` and stored
   under `~/.sase/axe/lumberjacks/<lumberjack>/chops/<chop>/`
   (`src/sase/axe/_state_chops.py`, lines 83-128). The same base chop can therefore be
   scheduled twice, as `stale_running_cleanup` currently is.
5. **Lifecycle housekeeping and rollups.** Before dispatch, a tick finalizes launched
   chop actions for the whole configured chop set. It also publishes lane heartbeat,
   load, error, overrun, and telemetry rollups.
6. **Operator-facing organization.** The CLI and ACE tree use lumberjacks as meaningful
   groups—fast lifecycle, waits, checks, external mirroring, comments, housekeeping,
   and Telegram—not merely implementation detail.

The breadth of this contract makes wholesale removal a migration rather than a local
scheduler edit. A lexical inventory at the inspected revision found “lumberjack” in 89
source files, 100 test files, and 15 documentation files. Many are presentation or
tests, but state paths, environment variables, artifact/chop identities, manual-run
disambiguation (`-L`), config composition, status wire data, doctor checks, and TUI
selection keys are substantive compatibility surfaces.

## What the current grouping gets wrong

The main scheduling weakness survives the 2026 concurrency refactor. A scheduled job
is the *whole tick*, and the `ThreadPoolExecutor` context waits for every submitted chop
to finish. The next scheduled tick cannot run until `_run_tick` returns. Thus:

- a 90-second hooks chop can suspend all nominally five-second siblings for roughly 90
  seconds;
- a two-minute `sidecar_auto_sync` timeout can suspend the ten-second waits cohort;
- one slow target in `external_mirror` delays the next pass for all targets;
- a scheduler-level exception escaping `future.result()` restarts the whole
  lumberjack, shifting every sibling's phase.

Per-chop timeouts cap the damage, and a chop execution itself already runs in a separate
subprocess with live-run deduplication, streaming history, and failure isolation. In
other words, the actual work is already “on its own”; what remains coupled is due-time
calculation and the join barrier.

The grouping also creates synchronized bursts: siblings scan/launch together at daemon
startup and on every lane boundary. Independent schedules could reduce that burst if
they add stable staggering or jitter, but merely starting 33 independent workers at
once would preserve the startup burst and add process overhead.

## Critique of a literal one-process-per-chop design

### Advantages

- A slow or stuck chop cannot delay another chop's next due time.
- Restart/backoff and health become truly per chop rather than per cadence cohort.
- Every chop can declare its cadence directly; the `interval` plus `run_every`
  two-level model disappears.
- The runtime model matches the already-independent run history, trigger, timeout,
  target, checkpoint, and dedupe state.
- The system no longer needs arbitrary decisions about which cadence-themed
  lumberjack owns a new chop.

### Costs and traps

- **Resident overhead:** the live design has seven scheduler children; the effective
  config has 33 expanded instances. Thirty-three long-lived Python interpreters,
  telemetry flushers, heartbeat writers, and supervisor log streams are a substantial
  multiplier even before scripts run.
- **Repeated discovery and serialization:** instantiating today's lumberjack loop once
  per chop repeats the unconditional Patch scan/context write. That is particularly
  unattractive for frequent lanes and for Telegram/housekeeping jobs that ignore Patch
  context.
- **Identity migration:** flattening to chop name alone loses the two intentional
  `stale_running_cleanup` schedules and cannot safely represent the same script under
  different config. Target fan-out also distinguishes a base chop from expanded
  instances. The durable entity must be a *schedule instance*, not an executable name.
- **State/history compatibility:** changing the namespace risks orphaning history,
  once-per reservations, trigger checkpoints, launched-agent linkage, manual-run
  references, and artifact relations.
- **Config duplication:** deleting groups outright repeats timeouts, shared environment,
  and descriptions. Reintroducing a `defaults`, `profile`, or `group` layer would be a
  lumberjack stripped of process semantics—which may be exactly the useful endpoint,
  but it is not truly “no grouping.”
- **Loss of coherent snapshots:** some lifecycle chops intentionally consume a common
  pre-dispatch view. Independent scans are correct only if all mutations converge and
  lost-update paths are fixed. They may also waste I/O and produce harder-to-explain
  observations from slightly different moments.
- **Operational noise:** 33 top-level status rows are less readable than seven groups
  with child chops. The UI can keep logical groups even if the runtime does not, but
  that distinction should be designed deliberately.

## A safer architecture that captures the benefit

The narrow objective should be: **each expanded chop schedule has an independent due
time and in-flight slot; logical groups do not impose a join barrier.** That does not
require a resident process per chop.

A practical design would be:

1. Keep one orchestrator (or, as a smaller first step, the existing small set of lane
   processes) with a due-time table keyed by stable schedule-instance ID.
2. When an instance is due and not already in flight, dispatch it through the existing
   `run_configured_chop_once` service. Do not wait for unrelated futures before
   evaluating other due times.
3. Preserve `(lumberjack, chop)` as the compatibility ID during the first migration.
   It can later become an opaque `schedule_id` with an alias/migration table.
4. Retain logical `group`/`profile` metadata for inherited env/defaults and ACE
   presentation, but make it explicitly non-scheduling and non-ordering.
5. Cache or broker Patch snapshots so chops due in the same short window may share a
   scan without sharing completion. Chops that do not request Patch context should not
   pay for it.
6. Keep no-overlap dedupe, maintenance mode, per-chop timeout, trigger state,
   `run_every` migration, lifecycle finalization, and restart/backoff semantics explicit
   at the schedule-instance level.
7. Add stable staggering for expensive/remote jobs rather than letting daemon startup
   launch every due chop simultaneously.
8. Do not add implicit dependency edges. If a future chop truly requires another run's
   success, model that as an explicit durable dependency/DAG edge with failure policy;
   never make list order meaningful.

The single-chop `comments` lumberjack is a low-risk compatibility pilot for extracting
schedule-instance machinery. The `hooks` lane is the best test of the eventual benefit
but the worst first migration because it has the densest state-sharing and the most
latency-sensitive behavior.

## Suggested decision gates

Before deleting the abstraction, I would require:

- convergence tests that randomize start/completion order for `hooks`, `waits`, and
  overlapping cleanup owners;
- a regression test for disjoint concurrent comment-suffix updates;
- measurements of idle CPU, summed and proportional memory, filesystem scans/writes,
  subprocess spawn rate, and wakeup latency under both schedulers;
- a compatibility plan for state paths, chop refs, manual-run identity, target-expanded
  instances, and the two `stale_running_cleanup` schedules;
- an operator design that keeps useful grouping without implying ordering;
- a canary showing that a deliberately slow chop no longer delays a fast sibling.

## Recommendation

Do **not** pursue wholesale lumberjack removal as a 33-resident-worker rewrite right
now. There is no chop-order dependency blocking the idea, but the literal topology
would trade one real scheduling problem for process, I/O, compatibility, and UX costs.
Pursue the narrower and more valuable change: schedule every expanded chop instance
independently through the existing runner, preserve lumberjacks initially as
non-ordering config/identity/UI groups, fix any concurrency races the randomized tests
expose, and only retire the grouping after measurements show it no longer earns its
keep.
