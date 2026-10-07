# Recent SASE task beads: independent impact audit (cdx)

Researcher: **cdx**, working independently in the research.3y swarm. No peer report, peer transcript, peer summary, or peer findings were consulted. Evidence came from the shared task-bead records, this workspace's source and history, the explicitly opened linked `sase-core` checkout, and independent probes.

**Finding:** the highest-impact work protects the agent launch path, makes new core functionality deliverable through published packages, and prevents display-only operations from crossing into initialization or commits. Deterministic verification failures also have substantial project-wide cost. Two especially valuable performance fixes have already landed while their task beads remain `ready`.

## Scope and exact eligibility

The fixed, inclusive 48-hour window is **2026-10-05 16:25:27 UTC through 2026-10-07 16:25:27 UTC** (October 5–7, 12:25:27 EDT). This endpoint was recorded before acquiring the bead inventory; it is not a rolling cutoff that changes while researching.

I enumerated every currently existing task bead with:

```bash
sase bead list --type task --status all --limit 0 --format json
```

The resulting snapshot contained **1,111 task beads**. For each record, eligibility was `created_at` within the window **OR** at least one `plus_one_evidence[].timestamp` within the window. I did not substitute `updated_at`, note timestamps, cumulative +1 count, or the reporter's earlier `observed_since` for the time a +1 was recorded.

**23 distinct tasks qualified:** 11 newly created, 13 recently corroborated, with one task in both groups. There were 17 +1 entries in the window. All statuses were included: the selected set happened to contain 20 `ready` tasks and three `open` flags, with no selected closed, claimed, snoozed, or in-progress tasks. The types were nine bugs, four CI failures, seven flakes, and three flags. I then read all 23 through one audited `sase bead read ... --format json --no-links -r ...` call, including task-type fields, notes, +1 evidence, close history, and dependencies. Sparse description bodies were not treated as empty tasks: several contain their substantive evidence in `task_type_fields`.

The inventory and eligibility timestamps are fixed; source checks and detailed reads occurred afterward. The primary source revision was `38f48d7575e4cddb49334a54a42ebfd257125d1f`; its core pin was `26ec2d61d9c60eede1596ae7d8c897e74dfb8141`. The opened core checkout was `f8d05efc58310eca985f2112afc89379ff7a6636` for tag/history diagnosis. An inspected current source implementation is not the same as proof that every installed process has adopted it.

## How I judged impact

This is a ranking of the **impact of the work associated with each task**, not a vote count, severity label, or a queue of ten still-unimplemented fixes. I weighed:

1. **Consequence:** inability to launch, unsafe/unexpected writes, broken package compatibility, recurring interaction cost, or verification noise.
2. **Reach and recurrence:** many agents/frontends/releases versus one rarely exercised test or UI path; recurring costs outrank one-off cleanup.
3. **Evidence:** independent runtime checks and measured behavior outrank a plausible mechanism or a title alone. A reproduced test failure does not establish a production failure.
4. **Recovery and marginal benefit:** a workaround reduces urgency; a delivered fix retains its impact but should not be implemented again. Small fixes with broad benefit are attractive, without pretending bead size is a measured effort estimate.

+1s are evidence entries, not independent votes. In particular, `sase-1fy` has reports from a phase and its land agent about overlapping runs; those cannot be counted as separate incidents. I kept related TUI flakes from occupying several top-ten slots merely because they produce multiple failing nodes. Flag-retirement beads were judged on retirement work itself, rather than inheriting all the value of the larger instruction-delivery program.

## Complete eligible inventory

All timestamps below are UTC. **C** means created in the window, **+** means corroborated in the window. The +1 column is **entries in this window / cumulative entries**. The table is ordered by original creation time, not impact.

| Bead | Type / status / size | Created | Qualifies | Latest +1 in window | +1 recent / total | Impact judgment |
| --- | --- | --- | --- | --- | --- | --- |
| [sase-10d](https://github.com/sase-org/sase--beads/blob/main/pages/sase-10d/README.md) | bug / ready / small | 2026-09-13 21:59:11 | + | 2026-10-06 12:33:50 | 1 / 6 | **Top 2.** Release prerequisite; 100 missing floor capabilities independently confirmed. Old commit-specific title is stale. |
| [sase-13p](https://github.com/sase-org/sase--beads/blob/main/pages/sase-13p/README.md) | ci / ready / large | 2026-09-20 12:03:33 | + | 2026-10-07 13:25:22 | 1 / 13 | **Top 10.** Deterministic boundary failure independently reproduced; startup and verification regression guard. |
| [sase-14o](https://github.com/sase-org/sase--beads/blob/main/pages/sase-14o/README.md) | ci / ready / small | 2026-09-20 22:08:33 | + | 2026-10-06 22:08:52 | 1 / 15 | First reserve: reproducible host-store leakage spoils full-lane tests; no demonstrated product failure. |
| [sase-15h](https://github.com/sase-org/sase--beads/blob/main/pages/sase-15h/README.md) | flake / ready / medium | 2026-09-21 16:58:10 | + | 2026-10-06 00:19:33 | 1 / 2 | Core gate flake; repeated ETXTBSY fixture-exec evidence, mechanism still a hypothesis. |
| [sase-17r](https://github.com/sase-org/sase--beads/blob/main/pages/sase-17r/README.md) | bug / ready / medium | 2026-09-24 13:11:54 | + | 2026-10-06 21:40:05 | 1 / 2 | **Top 6.** Broad agent-start latency; hidden-clone GC implementation already landed, operational benefit still to verify. |
| [sase-18v](https://github.com/sase-org/sase--beads/blob/main/pages/sase-18v/README.md) | ci / ready / small | 2026-09-25 04:36:43 | + | 2026-10-06 12:32:07 | 1 / 2 | Narrow CLI assertion/render-width problem; newest +1 is source corroboration, not a new runtime reproduction. |
| [sase-1br](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1br/README.md) | flake / ready / large | 2026-09-27 22:29:48 | + | 2026-10-06 00:19:02 | 1 / 2 | Scroll-settle test flake, including isolated failures; related symptoms may share a larger TUI fixture cause. |
| [sase-1em](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1em/README.md) | flake / ready / large | 2026-10-02 00:54:26 | + | 2026-10-06 22:08:42 | 1 / 1 | Registry test flake under loaded runs; real pending-claim failure in production is unproven. |
| [sase-1f0](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1f0/README.md) | flake / ready / large | 2026-10-03 02:32:33 | + | 2026-10-05 17:43:32 | 1 / 5 | Strong reserve: repeated RSS sampling flake, potentially relevant to demand telemetry; admission impact unproven. |
| [sase-1fy](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1fy/README.md) | flake / ready / large | 2026-10-04 13:29:15 | + | 2026-10-06 00:19:12 | 3 / 6 | **Top 9.** Repeated five-failure/five-error TUI cascades; serial failures also reported, cause unresolved. |
| [sase-1gp](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1gp/README.md) | flake / ready / large | 2026-10-05 14:10:58 | + | 2026-10-06 00:19:23 | 1 / 1 | Session-state test flake; overlaps focus/isolation incidents, actual cross-app production leak unproven. |
| [sase-1gs](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1gs/README.md) | bug / ready / large | 2026-10-05 14:14:53 | + | 2026-10-06 00:20:58 | 3 / 4 | **Top 8.** Broad historical read/link-write failure; two linked default reads succeeded in this audit, current failure not established. |
| [sase-1gv](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1gv/README.md) | flag / open / small | 2026-10-05 19:57:02 | C | — | 0 / 0 | Conditional sunset of Grok rules channel; retirement criteria matter, no current defect or January deadline urgency. |
| [sase-1gw](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1gw/README.md) | flag / open / small | 2026-10-05 19:58:29 | C | — | 0 / 0 | Conditional sunset of Claude helper channel; do not credit retirement with the whole instruction-delivery rollout. |
| [sase-1gx](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1gx/README.md) | bug / ready / medium | 2026-10-05 22:17:13 | C | — | 0 / 0 | **Top 3.** Read resolution reaches initialization/commit-capable code; existing read-only guards limit some paths. |
| [sase-1gy](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1gy/README.md) | bug / ready / medium | 2026-10-05 22:17:25 | C | — | 0 / 0 | Gitignored legacy perf output regrows sdd/; checkout hygiene issue, less impact than commit-capable reads. |
| [sase-1gz](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1gz/README.md) | flake / ready / large | 2026-10-06 00:19:48 | C | — | 0 / 0 | Single recorded socket/symlink-test flake; exact assertion absent, no evidence of a production security failure. |
| [sase-1h0](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1h0/README.md) | bug / ready / small | 2026-10-06 00:20:30 | C | — | 0 / 0 | Unused modal maintenance burden; no user reaches these modals, so direct product benefit is small. |
| [sase-1h1](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1h1/README.md) | bug / ready / large | 2026-10-06 00:22:02 | C | — | 0 / 0 | **Top 7.** Quoted comma/paren completion failure independently reproduced; runtime/TUI argument disagreement. |
| [sase-1h2](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1h2/README.md) | bug / ready / small | 2026-10-06 15:11:20 | C | — | 0 / 0 | **Top 1.** Cold-import failure independently reproduced; approved launches can never start. |
| [sase-1h4](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1h4/README.md) | flag / open / small | 2026-10-06 19:45:11 | C | — | 0 / 0 | Conditional retirement of shadow-render rollout flag, following cutover or seven-day observations. |
| [sase-1h5](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1h5/README.md) | bug / ready / small | 2026-10-06 21:38:33 | C | — | 0 / 0 | **Top 5.** Recurring UI/store cost and poor scaling; one-pass grouping and non-forced auto-refresh already landed. |
| [sase-1h6](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1h6/README.md) | ci / ready / small | 2026-10-06 22:07:14 | C+ | 2026-10-06 23:39:36 | 1 / 1 | **Top 4.** Deterministic lint barrier with broad fan-out; current private module import pattern remains present. |

## Independent checks and corrections to the record

**Launch path (`sase-1h2`): confirmed current runtime failure.** In two fresh `.venv/bin/python` subprocesses, importing `sase.history.prompt_store_mutations` first exited 1 with `ImportError: cannot import name 'add_or_update_prompt' from partially initialized module ...`; importing `sase.history.prompt_store` before the mutations module exited 0. The source still contains the eager facade import at `prompt_store_mutations.py:9` and the trailing re-export at `prompt_store.py:477`. Both `launch_cwd_agents.py` and `launch_cwd_bead_work.py` lazily import `effective_prompt_origin` from the mutations module. The bead records an approved LaunchApproval with `dispatch_status=failed` and no agents launched. I did not submit an actual launch to reproduce it: the fresh-process import and current call sites establish the failure mechanism without creating more agents.

**Published binding floor (`sase-10d`): the problem persists, but its original recipe is outdated.** The current dependency declaration remains `sase-core-rs>=0.35.0,<0.36.0`. I ran:

```bash
.venv/bin/python tools/probe_core_floor --json --advisory   --sase-core-dir sase/repos/linked/sase-core
```

It returned a cached wheel-probe verdict of `blocked_unpublished`, declared floor `0.35.0`, **100 missing capabilities**, and diagnostic `exit_code: 4`. Because `--advisory` was supplied, the process exited 0; that is not a passing compatibility result. Four capabilities had no containing release tag in the opened history: `bead_probe_target_owner`, `instruction_manifest_wire_schema_version`, `normalize_instruction_manifest`, and `wait_epic_follow_reduce`. The recent +1's 95-capability count is already obsolete. Its claim that `load_macro_input_type_registry` has no containing tag is also obsolete: the opened checkout now has `v0.37.0` containing that capability. Merely updating the task's original September commit number would miss the current cohort.

There is a material protection here: `docs/rust_backend.md` ("Who owns the published version window") assigns dependency-window reconciliation to `publish.yml`'s release-branch job, and `ci.yml` has `release-core-floor-smoke`. The declared source-checkout window lag is intentional during development. This is **release-enabling work and a release prerequisite**, not proof that the currently published SASE package is broken or an instruction for feature agents to edit the floor on master. The floor probe alone does not validate all intermediate wheels in an allowed version window.

**Read-only behavior (`sase-1gx`): confirmed source path, not a destructive runtime experiment.** `get_read_view()` still returns `get_project()` outside its explicit read-only-location branch. `get_project()` can materialize a store and invoke `init_beads()`. For `BEADS_DIRNAME`, that initialization calls `ensure_bare_git_sdd_initialized(..., commit=True, push=False)`. This makes the architectural read/write separation incomplete. Existing `_refuse_read_only_bead_store` checks protect some plain-checkout cases, so it would be wrong to claim every read commits into every unrelated repository. I did not exercise the missing-store path against a real checkout. The remaining scope is to make display-only resolution unavailable or truly read-only, while preserving explicitly authorized initialization.

**Performance (`sase-1h5`, `sase-17r`): valuable work already present in source.** Commit `7615e253d8` (2026-10-07 02:35:28 UTC) groups phases by parent in one pass and changes automatic `BeadsPane.on_refresh()` to `force=False`, retaining explicit user refresh as `force=True`. `beads_data_sources.load_project_beads()` also prefers the Rust board snapshot that returns issues, ready IDs, and blocked IDs together, with a legacy path when the binding is absent. Commit `69ecdace02` (2026-10-06 23:41:20 UTC) adds hidden-clone GC and calls it from the sidecar auto-sync path, addressing the clone omitted by the older primary-clone maintenance. Both commits predate the fixed endpoint.

The bead's historical timings remain useful evidence of potential impact: approximately 2.8 seconds per visible-pane refresh, and 22.2-second median fresh bead-sidecar clone latency across 41 operations. **I did not remeasure either workload after these commits.** The 48-second pane cost at a fourfold synthetic store is a scaling experiment reported in the bead, not today's measured latency. These two tasks require verification/adoption and tracker reconciliation before anyone commissions duplicate implementation.

**Quoted macro arguments (`sase-1h1`): confirmed current runtime mismatch.** I constructed a macro entry with `note: line`, `env: enum`, and `flag: bool`, and invoked the current `detect_macro_arg_completion_at_cursor` at the end of each string:

```text
#m:x,          -> macro_arg_value for env   (correct)
#m:"a,b",      -> macro_arg_value for flag  (wrong input)
#m("a)b",s     -> None                     (missing menu)
```

Current source still uses `value.count(",")`, `body.split(",")`, and raw `")" in body` tests to select inputs. Rust spans are already used for some value boundaries; that partial integration has not fixed input selection. Reusing core structural context matters because the same prompt must mean the same thing to the TUI, runtime binder, and editor.

**Import budget (`sase-13p`): confirmed current deterministic boundary failure.** A fresh interpreter running the measurement used by `test_app_import_budget.py` loaded **3,570 modules**, with approximately **2.449 CPU seconds**. The current cap is 3,570 and the comparison is strict `<`, so the count check fails while the five-second CPU budget passes. The original title's 3,292/3,290 numbers no longer describe the defect. Close history shows the task reopened on October 7 after the October 1 close; this is not merely a stale pre-close observation. No claim that startup currently exceeds five seconds is warranted.

**Artifact links (`sase-1gs`): repeated recent failures, but not reproduced on my current read paths.** The record includes three new +1 entries and examples of valid link additions and link-expanded bead reads failing before completion. However, my current full JSON reads of `sase-1h2` and the historically affected epic `sase-1g4` exited 0 with three and eight link rows respectively. I did not attempt `artifact link add`, because that would change the graph during a read-only audit. The underlying lexical validator still exists, but its existence is not proof that it is receiving a bad ID today. This bead merits bounded reproduction and identification of the offending stored/ref value before a repair; broadening ID grammar without that evidence would be speculative.

**Symvision (`sase-1h6`): current source agrees with the recorded deterministic blocker.** Cross-file imports of `sase.instructions._runs` remain in instruction verification/coverage, doctor checks, and the main instruction handler; two unrelated files still define local functions named `_runs`. The latest +1 reproduces the same findings on another unchanged-base check, and the original report explains the module/function name collision. I inspected these sites rather than rerunning the project-wide gate. A `KNOWN` classification preserves the nonzero result; it does not make the check green.

## Tradeoffs, reserves, and what the ranking does not imply

The strongest first reserve is **`sase-14o`**. It has 15 cumulative +1 entries and a fresh report of completion failures against live stores. I verified that the relevant tests still leave resolver inputs under-isolated. Its repair improves confidence in the full test lane, but the evidence establishes a test-environment fault rather than broken production completion or doctor behavior. The large cumulative count is not by itself enough to outrank launch failure, write safety, or published compatibility.

**`sase-1f0`** is the next reserve: five cumulative corroborations and a reported one failure in ten serial runs make the zero-RSS sample meaningful. Nevertheless, there is no demonstrated production admission or capacity-allocation error, and the proposed short-lived-process sampling race is unconfirmed. It should first establish whether the contract promises a nonzero peak for a process that exits before sampling.

The remaining flakes (`sase-15h`, `sase-1gz`, `sase-1gp`, `sase-1em`, `sase-1br`) cause real rerun cost. The socket/symlink test name does **not** establish an IPC security vulnerability, and the session/registry test names do **not** establish production identity leakage. The exact federation assertion is missing. Core and TUI test-fixture fixes may be worthwhile, but giving several related symptoms separate top-ten slots would overstate the evidence.

`sase-1h0` and `sase-1gy` are maintenance work with limited direct user consequences: unused modals and ignored legacy perf files. The flags `sase-1gv`, `sase-1gw`, and `sase-1h4` have January 2027 or release-0.19.0 retirement criteria plus observation/cutover conditions; none has recorded recent corroboration of a current defect. Retirement must follow those conditions, especially where disabling a flag would remove an instruction or helper-delivery channel.

If the practical goal is **what to launch next**, the delivered performance work needs verification rather than new implementation, and `sase-1gs` needs a current bounded reproduction. That would move `sase-14o` and `sase-1f0` upward in an outstanding-work queue. I retain performance tasks in the requested ranking because the user asked which corresponding work is most impactful, not only which patches remain unwritten. No task status, +1, dependency, or note was changed by this audit.

## Ranked list: the 10 most impactful eligible task beads

1. **[sase-1h2](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1h2/README.md) — Make cold imports safe so approved agents can launch.**

   **Highest immediate impact; independently reproduced; small size.** A human can approve a LaunchApproval and still get no agents because dispatch enters a circular import in a fresh process. This blocks the system's primary purpose and wastes approval/recovery effort; bead-work launch callers share the vulnerable path. Fixing import-order dependence restores useful work across launch workflows. The warm-import success explains why routine tests can miss it. Verify with fresh-interpreter import and launch-path regression coverage; do not rely on a process that happened to preload the facade.

2. **[sase-10d](https://github.com/sase-org/sase--beads/blob/main/pages/sase-10d/README.md) — Publish the required Rust cohort and reconcile the release dependency floor.**

   **Largest release reach; current compatibility gap confirmed; small recorded size.** The 0.35.0 floor lacks 100 required capabilities, including unreleased instruction and wait behavior. Resolving this enables published-wheel users to receive a broad set of already-landed work and restores source/wheel parity. Release guards reduce the danger of silently shipping an incompatible package, but they also make the missing cohort a release prerequisite. Follow the current release-owned reconciliation workflow and required cohort, rather than blindly applying the task's old September commit recipe or raising master metadata.

3. **[sase-1gx](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1gx/README.md) — Keep display-only bead operations out of initialization and commits.**

   **High integrity impact; source path confirmed; medium size.** A read abstraction still delegates to materialization and commit-capable initialization when an existing usable store is not found. Unexpected scaffolding or commits can pollute checkout history and turn an inspection into a repair problem. Separating read resolution from initialization protects doctor, attachment, and other bead consumers together. Some explicit read-only guards already protect plain checkouts; the fix should close the remaining path, not remove legitimate initialization. I did not create a real stray commit to test it.

4. **[sase-1h6](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1h6/README.md) — Remove the private instruction-module import pattern that poisons lint.**

   **Broad, recurring verification cost; small size; current trigger remains present.** A deterministic Symvision failure stops the lint stage across unrelated agents and appears in multiple clean-base runs. Repairing the cross-file private module naming/import pattern restores a trustworthy shared gate and avoids recurring false attribution to unrelated `_runs()` helpers. This is a compact change with unusually broad benefit. The evidence points to the instruction module, so renaming unrelated local helpers or adding suppressions would miss the cause. Current source inspection supports the recorded failure; I did not rerun Symvision.

5. **[sase-1h5](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1h5/README.md) — Make the Beads pane scale and avoid unnecessary periodic reloads.**

   **High recurring interaction and resource impact; small size; implementation already landed.** The recorded 2.8-second refresh cost recurs while the pane is visible, and the nested epic-by-issue scan becomes far worse as history grows. One-pass phase grouping, unchanged-store reuse, and a single board snapshot improve the usefulness of the project's central task view rather than just one test. Source now contains those changes from `7615e253d8`. The high ranking credits the delivered work; next verify post-change latency and actual binding adoption, then reconcile the still-ready task. The synthetic fourfold-store measurement is not a current production timing.

6. **[sase-17r](https://github.com/sase-org/sase--beads/blob/main/pages/sase-17r/README.md) — Keep hidden bead clones packed so fresh agents do not pay repack latency.**

   **Broad agent throughput impact; medium size; follow-up implementation already landed.** Recorded fresh clones cost 22.2 seconds median and up to 47.3 seconds, with 41 operations in 13 hours; the work affects each new workspace's first bead operation. Local packed-reference experiments reduced clone cost to about two seconds, giving a concrete benefit rather than a speculative optimization. The new +1 identified the hidden clone omitted by earlier maintenance, and `69ecdace02` now adds that path. Verify hidden-clone compaction and fresh-clone tail latency before treating the operational problem as closed. Removing all historical data or redesigning storage is unnecessary to capture this immediate benefit.

7. **[sase-1h1](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1h1/README.md) — Use structural argument parsing for quoted-value completion.**

   **Confirmed user-facing correctness problem; large size.** A comma inside a quoted argument shifts the selected input from `env` to `flag`; a quoted parenthesis suppresses the menu entirely. This makes enum, boolean, and model assistance unreliable for otherwise valid prompts, and makes the TUI disagree with the binder/editor. Taking cursor/input context from shared core parsing fixes a whole class of punctuation errors and avoids another frontend-specific parser. Both recorded examples reproduce in this checkout. Its reach is narrower than launch/store infrastructure, which limits its position despite strong certainty.

8. **[sase-1gs](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1gs/README.md) — Restore reliable artifact-link writes and link-expanded bead reads.**

   **Potentially broad workflow impact; large size; current failure confidence reduced.** Recent evidence records failed typed links and failed audited reads, forcing agents to use prose relationships and `--no-links`. Repair would preserve discoverability, duplicate-task context, and normal inspection across the artifact graph. Those are central workflows, so the historical consequence belongs in the top ten. However, two current full linked reads succeeded in my audit, and I did not mutate the graph to test writes. First isolate the current failing row/value and determine whether a repair has already taken effect; do not claim that all reads still fail today.

9. **[sase-1fy](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1fy/README.md) — Stop the prompt focus and mount/teardown failure cascade.**

   **Most costly eligible TUI flake cluster; large size; production cause unproven.** Multiple recent checks show five failing tests plus five teardown errors, with missing-widget, duplicate-ID, timeout, and isolation signatures. This creates noisy failure cascades and expensive reruns across unrelated changes. Some serial failures are recorded too, so blaming xdist alone is unsupported. Fixing the lifecycle/fixture issue can recover a meaningful part of verification reliability; choose one representative root-cause investigation instead of separately counting each sibling flake as equal impact. A real user-facing focus defect remains possible, not established.

10. **[sase-13p](https://github.com/sase-org/sase--beads/blob/main/pages/sase-13p/README.md) — Restore a passing import-budget guard with real startup headroom.**

   **Deterministic, currently reproduced verification failure; large recorded size.** The task was reopened after its previous close, and the current count is exactly 3,570 against a strict `< 3570` limit. Resolving this restores a shared regression guard and encourages sustainable lazy-import boundaries as the TUI grows. Its import-graph benefit reaches every cold TUI start, though the measured 2.449 CPU seconds already satisfies the timing budget. This ranks below user-visible correctness and broad integrity work: it is evidence of a count-boundary failure, not proof of an unusably slow application. Avoid declaring success at equality or automatically ratcheting the cap again without a justified budget policy.
