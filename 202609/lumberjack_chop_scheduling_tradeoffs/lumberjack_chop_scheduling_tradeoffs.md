# Independent chop scheduling: should lumberjacks go away?

_Consolidated research · 2026-09-15_

## Executive assessment

**No current lumberjack has a supported requirement that its chops execute in a particular order.** Eligible siblings already run concurrently. Several chops consume state produced by other chops, but those relationships are reconciled over later runs, including across lumberjacks.

That makes independent scheduling feasible. It does **not** establish that every interleaving is safe: this investigation reproduced a stale-snapshot comment update that loses another writer's changes, and identified protections that need strengthening before overlapping successive scheduling rounds.

The strongest reason to pursue the idea is concrete: **one slow chop still delays every sibling's next run**, because the lumberjack waits for the whole batch. The best first change is to remove that completion barrier and give each configured chop instance its own due time. Keep existing process groups, identities, and configuration initially. Full lumberjack removal would add a broad migration before proving much additional benefit.

## Scope and provenance

This report combines three perspectives:

| Input | Dispatch identity | Preserved report | Registered immutable reference |
| --- | --- | --- | --- |
| A | `research.8.cdx` | [Researcher A](lumberjack_chop_scheduling_tradeoffs__a.md) | `file:explicit:ccbaa961fdf9a73961d663bb` |
| B | `research.8.cld` | [Researcher B](lumberjack_chop_scheduling_tradeoffs__b.md) | `file:explicit:2178057a59c5236253a8383b` |
| Lead | `research.8.final` | This report | Independent source inspection and isolated experiments |

A was identified by the canonical label `research:202609/lumberjack_removal_order_dependency_analysis__a.md`; B by `research:202609/lumberjack_removal_chop_ordering__b.md`. Both were read through `sase artifact read`. Their local copies were moved with their original suffixes and contents preserved; neither another researcher's checkout nor an immutable snapshot was modified.

The lead inspected SASE revision `21c18cc34bda871773519abfb14982dec2826e87`, Rust core `e6d08ad`, and Telegram plugin `9c3a600`. The scheduler, lifecycle writers, and default configuration inspected here were unchanged from the researchers' SASE revision `688b2d4eac`. Effective configuration was independently checked with `sase axe lumberjack list -v`. This is a local-host assessment, not a fleet-wide performance study.

## 1. What ordering exists today?

### Sibling order is not a contract

`Lumberjack._run_tick` prepares context, selects eligible chops, submits them to `ThreadPoolExecutor`, then collects results through `as_completed`. Thus configuration order is submission order, but neither completion order nor a producer-before-consumer guarantee. Worker availability can affect start timing; “concurrent” does not mean literally simultaneous. The concurrency behavior dates to commit `2c6464b1bf` on 2026-04-08. The existing `test_chops_run_concurrently` explicitly asserts parallel execution. [Scheduler source][scheduler] · [Concurrency test][tick-tests]

The lead also exercised the actual `_run_tick` with isolated, stubbed chop bodies and event barriers: the fast body completed while the slow body remained active, but the tick returned only after the slow body was released. This establishes both concurrency and the surviving completion barrier without running production chops.

### Audit of all configured lumberjacks

The effective host configuration contains **seven lumberjacks and 33 expanded schedule instances**, including project-specific mirror instances and two schedules for `stale_running_cleanup`.

| Lumberjack | Cadence / instances | Dependencies and verdict |
| --- | --- | --- |
| `hooks` | 5 seconds / 8 | Hook completion enables mentors; failed hooks enable fix workflows; fix-workflow suffixes can in turn satisfy mentor readiness; collected comment-check results enable CRS workflows. These consume persisted state or an earlier snapshot. No sibling ordering guarantee. Shared writers require concurrency safety. |
| `waits` | 10 seconds / 4 | `sidecar_auto_sync` can fetch a closed bead that unblocks `wait_checks`. If the waiter reads first, another pass can observe the change. `bead_claim_checks` and `epic_launch_flush` do not require list order. Sync and epic flush also have 30-second `run_every` limits. |
| `checks` | 300 seconds / 5 | No identified internal ordering dependency. `pr_submitted_checks` produces background results for `pending_checks_poll` in `hooks`. The second `stale_running_cleanup` is a backstop for the fast schedule's process being unavailable. |
| `external_mirror` | 900 seconds / 4 | Issue and PR mirror scripts expand for two projects. Their cursors and ownership checks provide isolation; shared API and disk load matter more than ordering. Mirrored tasks can later become input to task triage in `checks`. |
| `comments` | 60 seconds / 1 | Trivially no sibling dependency. `comment_checks` starts remote work that `pending_checks_poll` later collects. |
| `housekeeping` | 3600 seconds / 9 | No required list order identified. `disk_pressure` can invoke the same cleanup owners as `managed_tmp_reap` and `proc_runtime_sweep`; overlapping scans require owner-side safety. Digest visibility can lag concurrent error production. |
| `telegram` | 5 seconds / 2 | Outbound messages create actions that inbound callbacks later consume. This is a durable handoff, not a reason to order the two scripts within each tick. Separate cursors and the outbound singleton lock address other forms of overlap. |

The complete chop inventories remain in A and B. The default definitions and the readiness checks corroborate the relationships above. [Default configuration][defaults] · [Mentor readiness and admission][mentors] · [Workflow admission][workflows]

An actual hard sequence exists **inside** `stale_running_cleanup`: reconcile monitors before releasing affected claims. That stays inside one script when the script is scheduled independently. It does not justify ordering separate chops.

The precise answer is therefore **“no supported inter-chop ordering dependency found,” not “all chops are independent of shared state.”** A consumer still needs eventual producer execution, durable state, and another opportunity to run. A failed producer, inhibited consumer, or lost update can prevent convergence.

## 2. What the lead research changes or qualifies

### A confirmed comment update defect

Both researchers flagged stale `COMMENTS` writes. The lead reproduced the mechanism against a temporary ProjectSpec using the real parser and `set_comment_suffix`:

1. Read two copies of comments for Alice and Bob, initially without suffixes.
2. From copy A, set Alice's suffix to a running CRS agent.
3. From the unchanged copy B, set Bob's suffix to `ZOMBIE`.
4. Re-read: Bob is `ZOMBIE`, but Alice's running-agent suffix has disappeared.

Both writes succeeded. `set_comment_suffix` constructs a replacement list from the caller's snapshot; `update_patch_comments_field` locks the write but does not merge against a fresh read. Even serialized writes can therefore lose updates. Actual zombie and workflow callers supply snapshot comments. This is a demonstrated persistence defect, although the experiment did not launch real CRS agents or reproduce a production incident. [Comment mutation][comments] · [Zombie caller][zombie]

The analogous hook concern is narrower: `merge_hook_updates` does re-read under lock and preserves other commands, but replaces each changed command's whole hook entry. A concurrent suffix update on that same command can be vulnerable to a stale replacement. That path was inspected, not reproduced end to end. [Hook persistence][hooks]

### Existing overlap checks are not atomic reservations

Both reports describe the runner's live-run check as sufficient reusable deduplication. It is useful, but stronger claims are unwarranted. The runner checks `active_script_chop_run`, performs context and preflight work, and only later calls `start_chop_run`. No common lock covers that check-and-start sequence. The history writer also reads and replaces its index separately. Per-policy locks do not make this entire sequence atomic. [Runner admission][runner] · [History writes][history]

Two callers can both see no active run before either records one. The current serialized scheduler loop avoids competing scheduled admissions for the same instance, but manual calls already come from other processes. A replacement needs one in-flight slot per schedule instance **and** atomic cross-process admission for competing entry points. The source establishes the gap; duplicate real subprocess execution was not experimentally induced.

### A private context file does not make snapshots private

`prepare_chop_run_context` copies the context document and supplies a unique result path, but retains pointers to shared `tick/all_changespecs.json` and `tick/filtered_changespecs.json`. Built-in chops load those snapshots lazily and separately. Manual context creation already rewrites these same paths. [Context copying][context] · [One-shot context][oneshot] · [Lazy loads][builtin]

This qualifies A's description of a coherent shared snapshot and B's assertion that mixing versions is harmless. Atomic replacement prevents malformed JSON, but does not guarantee the two files represent the same generation. Removing the barrier while continuing to overwrite them would make this overlap routine. Use immutable snapshot generations retained until their consumers finish, or actual per-run snapshot files. Caching can still share discovery work without sharing mutable filenames.

### Launch capacity is not a shared tick budget

Each built-in chop creates its own `HookJobRunner`; its `_agents_started_this_tick` counter is process-local. Mentor and workflow admission read global persisted runner counts and add local starts. The configured claim of a shared tick budget is therefore misleading. These observations support an admission race concern, but do not establish B's suggested approximately twofold overshoot. No such magnitude was measured. [Built-in runtime][builtin] · [Mentor admission][mentors] · [Workflow admission][workflows]

A topology change should use atomic reservations for scarce launch capacity, or explicitly preserve and document weaker semantics. A lumberjack's grouping does not supply that reservation today.

### Removing the barrier changes overlap patterns

B argues that current simultaneous dispatch is already the worst case. That is too strong. Today there is an implicit relationship across **successive rounds**: every sibling's current run finishes before any sibling's next scheduled run begins. Independent scheduling removes it. A fast writer may now run repeatedly during one slow reader's lifetime. This can increase stale-state exposure, total work, and resource contention even without overlapping two runs of the same chop.

Likewise, hook-to-mentor progress often happens on a subsequent five-second opportunity, but five seconds is not a bound: slow scripts, triggers, guards, and failures can extend it. Telegram human reaction time is not a synchronization guarantee either. The outbound source explicitly documents an earlier callback-loss window and now persists pending actions immediately after sending. That is a handoff concern to test, not evidence of a required lumberjack order. [Telegram handoff][telegram]

## 3. Benefits and costs of the idea

### The benefit is independent progress

The scheduled unit is currently the whole tick. Normal recurring scheduling also calculates the next run after that job finishes. Consequently, a nominal five-second lane with a 90-second slow chop can approach **95 seconds between dispatch rounds**, before other overhead. Ordinary fast chop code already runs in its own subprocess; it is the next opportunity to run that remains coupled. [Scheduler source][scheduler]

Independent dispatch can improve tail latency, give expensive project targets separate timing, and avoid adding new lumberjacks just to protect unrelated work. Stable staggering could also reduce synchronized load. Merely starting more workers at once would not.

### Lumberjacks carry more than timing

| Existing responsibility | Consequence of outright removal |
| --- | --- |
| Supervised process and restart boundary | Choose a replacement fault domain. One central scheduler simplifies process count but shares scheduler failures; one resident worker per expanded instance increases resident processes from 7 to 33 on this host. |
| Shared `env`, timeouts, and defaults | Preserve profiles/groups or repeat configuration. Telegram uses inherited environment. |
| Snapshot discovery and serialization | Avoid multiplying scans for every chop, especially frequent chops that ignore Patch data. |
| `(lumberjack, chop)` identity | Preserve history, checkpoints, once-per state, action links, and manual-run disambiguation. Script name alone cannot represent duplicates or target expansion. |
| Script-owned state under `context.state_dir` | Migrate actual checkpoints, cursors, and gate generations, not just visible history files. |
| CLI, TUI, status, restart, and overrun contracts | Update Python callers and presentation alongside Rust config/status/overrun APIs and bindings. This is a cross-repository migration. |

A's roughly 154 MiB summed RSS measurement for the orchestrator plus seven lumberjacks is a useful warning about resident overhead, not a reliable extrapolation to 33 workers. B's newest-ten-run timing sample suggests modest load on this Mac, but it is not a percentile study or a fleet result. B's broad “every fast lane under 1.5 seconds” summary is also inconsistent with its own 3.42-second sidecar-sync maximum. The evidence demonstrates a structural tail-latency problem, not sustained fleet-wide distress.

## 4. Compare the realistic choices

| Choice | Benefit | Assessment |
| --- | --- | --- |
| Keep current scheduler | No migration | Reasonable if tail delay is acceptable; retains sibling coupling. |
| Independent due times inside existing lumberjack processes | Fast siblings can repeat while slow ones run; preserves identities and operations | **Best first step.** Moderate scheduler work plus admission, snapshots, and metric correctness. |
| One shared dispatcher, groups retained as metadata | Fewer scheduler processes and centralized dispatch | Worth comparing later; requires fairness, bounded capacity, and a deliberate shared failure domain. |
| One resident supervisor per chop instance; remove lumberjacks | Straightforward per-instance supervision | Feasible, but unproven memory/I/O benefit and substantial migration cost. |

“Each chop runs on its own” need not mean “each chop has a permanent Python scheduler process.” The current subprocess runner can remain the execution boundary under several scheduling designs.

## 5. Conditions for a useful first implementation

A focused implementation should demonstrate:

1. **Independent due times and bounded dispatch.** Define fixed-delay versus fixed-rate behavior, skip or coalesce missed runs, and avoid unlimited queued work. Test that slow siblings and slow project targets cannot monopolize available workers.
2. **Atomic admission and durable handoffs.** Prevent competing manual/scheduled starts of one instance; exercise launch-capacity races and crash recovery. Preserve action-level dedupe, triggers, checkpoint behavior, and maintenance pauses.
3. **Stable snapshots and convergent mutations.** Preserve one snapshot generation throughout a run and reproduce stale comment/hook interleavings. Test producer-before-consumer, consumer-before-producer, and repeated fast-consumer runs during a slow producer.
4. **Stable identity.** Initially retain `(lumberjack, expanded chop name)`, including both cleanup schedules. Removing a backstop needs a separate recovery justification; independent timing alone does not make it redundant.
5. **Responsive supervision and truthful metrics.** Finalize runs, update heartbeats, and handle shutdown without waiting for unrelated work. Move overrun meaning from “blocked the group” to lateness/duration against the instance's effective cadence.
6. **Measured benefit.** Compare idle CPU, RSS, snapshot scans/writes, spawn rate, and event-to-action latency under ordinary and deliberately slow runs. A single-chop lane can validate compatibility; a multi-chop canary is required to prove the benefit.

Shared scheduling policy, admission semantics, config, and status behavior belong in Rust core under the project's backend boundary. Python can retain process execution and thin adapters. This should not become a Python-only reimplementation of shared domain rules.

## 6. Evidence quality and remaining limits

- **Directly confirmed:** effective seven-group inventory; concurrent submission and completion barrier; finish-relative scheduling in the locally installed `schedule.Job.run`; unchanged relevant source since the researchers' revision; stale comment replacement; shared snapshot pointers; separate admission check and history write.
- **Experiments:** an event-controlled exercise of actual `_run_tick` with stubbed chop bodies confirmed fast completion plus slow-sibling blocking; a temporary-file exercise of real comment persistence confirmed lost updates. No live chop or external message was launched.
- **Test limitation:** the two selected existing scheduler tests did not pass in the local `.venv`: one setup error and one preflight-driven failure arose from missing Rust bindings, including `artifact_relations_builtins` and `evaluate_chop_decision`. The isolated barrier experiment stubbed unrelated host configuration/maintenance dependencies; it is not a replacement for the integration suite.
- **Not established:** production frequency of lost updates, exact launch-limit overshoot, safety of every cleanup interleaving, or performance on busier hosts. Unrelated unverified claims from B were excluded from the recommendation.

### Primary source index

Links below pin SASE code to the inspected revision. Rust and plugin sources were opened locally through `sase repo open` before inspection.

- [Scheduler and completion barrier][scheduler]; [existing concurrency/failure tests][tick-tests]; [default schedules][defaults].
- [Runner admission][runner]; [run history persistence][history]; [context copying][context]; [one-shot snapshots][oneshot]; [built-in lazy runtime][builtin].
- [Comment mutation][comments]; [zombie caller][zombie]; [hook merging][hooks]; [mentor admission][mentors]; [workflow admission][workflows].
- Rust core: `crates/sase_core/src/config/axe.rs`, `axe_status/wire.rs`, and Python adapter `src/sase/core/axe_chop_facade.py`; inspected revisions are recorded above.
- [Telegram pending-action persistence after delivery][telegram].

## Recommendation

**Pursue independent per-chop scheduling; do not pursue wholesale lumberjack removal yet.** No current inter-chop ordering contract blocks the idea. The valuable change is allowing each configured instance to make progress without waiting for its slowest sibling.

Start with independent dispatch inside the existing supervised groups, preserve durable identities, and make admission and snapshot handling safe before removing the barrier. Fix the reproduced comment lost update as correctness work independent of the topology decision.

Reconsider deleting lumberjacks after measurements show whether their remaining supervision, defaults, and operator grouping justify the abstraction. If they become only labels, removal can be a focused migration. At present, deleting them would spend much of the effort on replacing useful infrastructure rather than delivering the scheduling benefit.

[scheduler]: https://github.com/sase-org/sase/blob/21c18cc34bda871773519abfb14982dec2826e87/src/sase/axe/lumberjack.py#L145
[tick-tests]: https://github.com/sase-org/sase/blob/21c18cc34bda871773519abfb14982dec2826e87/tests/test_axe_lumberjack_tick.py#L409
[defaults]: https://github.com/sase-org/sase/blob/21c18cc34bda871773519abfb14982dec2826e87/src/sase/default_config.yml#L903
[runner]: https://github.com/sase-org/sase/blob/21c18cc34bda871773519abfb14982dec2826e87/src/sase/axe/chop_runner_script.py#L77
[history]: https://github.com/sase-org/sase/blob/21c18cc34bda871773519abfb14982dec2826e87/src/sase/axe/_state_chops.py#L221
[context]: https://github.com/sase-org/sase/blob/21c18cc34bda871773519abfb14982dec2826e87/src/sase/axe/chop_script_context.py#L98
[oneshot]: https://github.com/sase-org/sase/blob/21c18cc34bda871773519abfb14982dec2826e87/src/sase/axe/chop_runner_context.py#L24
[builtin]: https://github.com/sase-org/sase/blob/21c18cc34bda871773519abfb14982dec2826e87/src/sase/chops/builtin.py#L45
[comments]: https://github.com/sase-org/sase/blob/21c18cc34bda871773519abfb14982dec2826e87/src/sase/ace/comments/operations.py#L336
[zombie]: https://github.com/sase-org/sase/blob/21c18cc34bda871773519abfb14982dec2826e87/src/sase/ace/scheduler/comments_handler.py#L36
[hooks]: https://github.com/sase-org/sase/blob/21c18cc34bda871773519abfb14982dec2826e87/src/sase/ace/hooks/persistence.py#L167
[mentors]: https://github.com/sase-org/sase/blob/21c18cc34bda871773519abfb14982dec2826e87/src/sase/ace/scheduler/mentor_checks.py#L613
[workflows]: https://github.com/sase-org/sase/blob/21c18cc34bda871773519abfb14982dec2826e87/src/sase/ace/scheduler/workflows_runner/starter.py#L567
[telegram]: https://github.com/sase-org/sase-telegram/blob/9c3a600327af53187418aa990f2a038fcdac6a36/src/sase_telegram/scripts/sase_tg_outbound.py#L452
