---
create_time: 2026-08-08
updated_time: 2026-08-08
status: research
---

# Measured Triage of the Parallel-Suite Flake Class (sase-ct / sase-h8.3)

**Research question:** which node IDs the durable selection-health store and the
`just test-contention` reproducer actually implicate in sase's parallel-suite flake
class, what mechanism each one fails by, and which remediation phase of epic `sase-h8`
owns it.

**Scope:** the `sase` repo at master `47b9f0017` on 2026-08-08, the durable
selection-health store at `~/.sase/test-selection/gh_sase-org__sase/` as read at
2026-08-08T01:27:46Z, and two contention soaks run on the 64-core `athena` development
host. This note is the deliverable of phase `triage` of
`plans:202608/parallel_suite_flake_class.md` (bead `sase-h8.3`). It replaces the epic
plan's *hypothesised* family membership, which was assembled from bead anecdotes, with
measured assignments. Where measurement contradicts the plan, this note wins and says so.

## Bottom line

The class is real but **substantially smaller than the store reports**, and the two
largest signals in both the store and the reproducer are not flakes at all.

1. **Six nodes are a live regression at HEAD, not flakes.** The four
   `tests/test_gate_cli_show.py` nodes and the two
   `tests/gate_conformance/test_gate_conformance.py[*-legacy_shared_input]` nodes fail
   deterministically at `47b9f0017`, serially, unpinned, with `-p no:randomly`. They are
   collateral from `ff0b765a4`. They are out of scope for this epic and need their own
   fix.
2. **The contention harness contaminates its own measurement.** `just test-contention`
   exports `SASE_TEST_SELECTION_HEALTH_DISABLED=1` into every repeat, and three nodes
   fail deterministically under that variable with no contention at all — after which
   `test_contract_set_serial_runtime_stays_within_budget` fails as a *cascade*, because
   it shells out a nested pytest that inherits the variable and asserts the child exited
   zero. This means the `sase-h8.1` baseline's headline result
   ("`test_contract_set_serial_runtime_stays_within_budget` 4/4, F2 wall-clock ceiling")
   is **misattributed**: under the harness that node is not measuring wall clock at all.
   Until this is fixed the harness can neither confirm nor falsify a fix to that node,
   and the epic's exit criterion of a zero-failure tally is unreachable for reasons
   unrelated to flakes.
3. **A third of the store's "reproducible flake" set is an artifact of three
   catastrophic runs.** Excluding the three full runs with ≥20 failures (950, 185, and
   32 failures) drops the store's set from 42 nodes to 31. Eleven nodes are called
   reproducible flakes purely because one catastrophic run supplied the second disjoint
   change set that `reproducible_flake_nodeids` requires.
4. **The `tests/test_bead/` clusters are a since-fixed genuine break, not F4 leakage.**
   The plan flagged this hypothesis and it is confirmed: the six snooze nodes fail as an
   all-or-nothing block in the same run across five heads and three workspaces over one
   4.5-hour window, the three `close_history` nodes likewise, and every one of them
   passes at HEAD. They are not per-node timing races.
5. **After those removals, the genuinely contention-reproducible class is small — seven
   nodes.** Across a 6-repeat 23-file soak and an 8-repeat 9-file soak: three F3
   `test_agent_metadata_search` nodes, two F2 `test_stall_watchdog` nodes, one F1
   `test_artifact_files_modal_copy` node, and one `tests/fakey` node. Two of the seven
   are node IDs no bead had enumerated before, and the `fakey` node — the second-strongest
   reproducer in the whole class at 5/8 — fails by a real-wall-clock deadline (F2), not
   by the broken pipe (F5) the plan assigned it.

## Method

Two soaks, both at `47b9f0017`, both with the `sase-h8.1` default pinning: 26 xdist
workers pinned to CPUs 0,1 (13x oversubscription).

```bash
# Soak A -- the 23 files owning every node in the store's reproducible-flake set.
SASE_CONTENTION_REPEAT=6 just test-contention -- <23 files>
# 758.0s, 6/6 red repeats, 14 distinct nodes.

# Soak B -- the ACE and tooling files whose store-frequent nodes did not reproduce in
# soak A, concentrated so each node gets more contention per repeat.
SASE_CONTENTION_REPEAT=8 just test-contention -- <9 files>
# 546.6s, 5/8 red repeats, 2 distinct nodes.
```

The store side was computed with `reproducible_flake_nodeids`
(`tests/_test_selection_health.py:156`) over the full-run records, and cross-checked
against `just selection-health`'s flake-suppressed section. The store was read, never
mutated or pruned.

## Measurement A: the durable health store

Read 2026-08-08T01:27:46Z.

| Measurement                                            |          Value |
| ------------------------------------------------------ | -------------: |
| Full-run records                                       |            275 |
| Selection records                                      |            271 |
| Full runs with at least one failure                    |            124 |
| Red rate                                               |          45.1% |
| `reproducible_flake_nodeids` over the store            |             42 |
| ... with the 3 catastrophic runs (≥20 failures) excluded |             31 |
| `just selection-health` flake-suppressed section       | 20 (84 scoped run/failure matches) |
| Union of the store set and both soak tallies           |             45 |

The two sets differ legitimately: the report's set is additionally restricted to nodes a
scoped run matched, so it is a subset. Both are recorded here as the plan requires.

The store is a shared, host-local, 30-day-retention artifact that every workspace writes,
so these counts drift while agents run: the same store read ~40 minutes earlier in this
session reported 273 full runs and a 40-node set. The timestamped read above is the one
the table below is built from.

The catastrophic runs are:

| Recorded at              | Head        | Workspace | Failures |
| ------------------------ | ----------- | --------- | -------: |
| 2026-08-07T14:24:35Z     | `57a045cfc` | sase_16   |      950 |
| 2026-08-07T18:46:55Z     | `b473a10d0` | sase_11   |      185 |
| 2026-08-07T15:35:37Z     | `34928a454` | sase_17   |       32 |

A run of that shape is a broken environment, not 950 flakes, but every node in it
contributes a change set to `reproducible_flake_nodeids`, so any node that also failed
once elsewhere is promoted to "reproducible flake". This is a real weakness in the
metric and it matters to phase `gate`: **the flake gate should discount full runs above
a failure-count threshold**, or the baseline will absorb whole broken runs.

## Measurement B: soak A (23 files, 6 repeats, 758s)

```
contention tally: 14 node(s) failed across 6 repeat(s) in 758.0s; red repeats: 1,2,3,4,5,6
  6/6  tests/gate_conformance/test_gate_conformance.py::test_gate_conformance[ace-legacy_shared_input]
  6/6  tests/gate_conformance/test_gate_conformance.py::test_gate_conformance[cli-legacy_shared_input]
  6/6  tests/test_contract_manifest.py::test_contract_set_serial_runtime_stays_within_budget
  6/6  tests/test_gate_cli_show.py::test_show_json_reports_declared_inputs_branches_and_actions
  6/6  tests/test_gate_cli_show.py::test_show_prints_a_readable_summary_of_the_decision_surface
  6/6  tests/test_gate_cli_show.py::test_show_reports_a_cancelled_gate
  6/6  tests/test_gate_cli_show.py::test_show_reports_the_terminal_status_of_an_answered_gate
  6/6  tests/test_run_pytest_scoped.py::test_scoped_escalation_runs_the_governed_fast_lane
  3/6  tests/ace/tui/test_agent_metadata_search.py::test_inline_metadata_search_commit_repeat_q_and_passthrough
  2/6  tests/ace/tui/test_agent_metadata_search.py::test_inline_metadata_search_reverse_key_override
  1/6  tests/ace/tui/modals/test_artifact_files_modal_copy.py::test_artifact_file_modal_Y_anchors_path_recovered_from_agent_meta_json
  1/6  tests/ace/tui/test_agent_metadata_search.py::test_inline_metadata_search_yank_and_frozen_refresh
  1/6  tests/ace/tui/util/test_stall_watchdog.py::test_watchdog_records_one_stall_with_stack_and_context
  1/6  tests/ace/tui/util/test_stall_watchdog.py::test_watchdog_writes_loop_recovery_record
```

Every 6/6 node in that tally is deterministic rather than load-sensitive. Only the six
nodes at 3/6 and below are the flake class.

## Measurement C: soak B (9 files, 8 repeats, 547s)

Soak A ran 23 files at once, so each individual node competed with 300 others for two
CPUs. Soak B concentrates the nine files whose store-frequent nodes did not reproduce,
giving each node materially more contention per repeat.

```
contention tally: 2 node(s) failed across 8 repeat(s) in 546.6s; red repeats: 1,2,3,4,8
  5/8  tests/fakey/test_retry_pipeline_e2e.py::test_retryable_failure_then_success_records_lifecycle_and_nudge
  1/8  tests/ace/tui/util/test_stall_watchdog.py::test_watchdog_writes_loop_recovery_record
```

Two results matter:

- **`test_retryable_failure_then_success_records_lifecycle_and_nudge` is the class's
  second-strongest reproducer at 5/8**, and its mechanism is **not** the broken pipe the
  plan assigned it. Every failure is
  `TimeoutError: timed out waiting for retry state 'retrying'`, raised by
  `FakeyHarness.wait_for_retry_state`'s fixed 5-second real-wall-clock ceiling
  (`tests/fakey/harness.py:440`) while a background thread and its subprocess make
  progress too slowly under 13x oversubscription. That is F2, not F5.
- **Nothing else reproduced in 8 concentrated repeats**, including
  `test_tracked_executor_reports_terminal_and_extra_commands_live` (0/8 on top of 0/6),
  all four store-known `test_stall_watchdog` nodes other than the one above, both
  `test_prompt_bar_xprompt_selector_requests` nodes, `test_at_prefix_directory_drilldown`,
  `test_bulk_waiting_agents_mount_forced_artifact_prompts`, and
  `test_installing_prunes_the_cache_to_the_keep_limit`.

Incidentally, `tests/fakey/harness.py:492` holds a **fifth** private `_wait_until` copy
beyond the four that phase `waits` (`sase-h8.2`) was scoped to retire. The lint check in
phase `gate` must catch it.

## Correction 1: the six gate nodes are a regression at HEAD

Reproduced outside any harness:

```bash
.venv/bin/python -m pytest -q -p no:randomly \
  tests/test_gate_cli_show.py tests/gate_conformance/test_gate_conformance.py
# 6 failed at 47b9f0017, serial, unpinned, no CPU restriction.
```

All six fail with the same shape:

```
GateError: option 'audit' cannot be answered: no surface can submit a value its
input_schema accepts ('reason' is a required property). Declare 'reason' under this
option's 'inputs' so every surface collects it, or drop it from 'required'.
```

`ff0b765a4` ("feat(notification-gates)!: fail closed at creation for unanswerable
gates", 2026-08-07T23:24:06Z) introduced `_validate_option_answerability`
(`src/sase/notification_gates/kind_validation/custom.py:44`). The store's first recorded
failure of these six is 2026-08-08T00:12:36Z at `7bbd82a47`, the commit seven minutes
after it. The fixtures in these two suites declare an option whose `input_schema`
requires a property that is not declared under the option's `inputs`, which the new
validator now rejects at creation. The tests, not the validator, are stale.

They landed in the store's reproducible-flake set only because four different
workspaces hit them with different working-tree change sets, which is exactly the
disjoint-change-set signature `reproducible_flake_nodeids` reads as a flake. **This is a
generalisable false positive: a deterministic break on master looks identical to a flake
to that heuristic**, and phase `gate` must account for it.

**Out of scope for `sase-h8`.** Filed as a follow-up on `sase-h8.3`.

## Correction 2: the harness contaminates its own measurement

`tools/run_pytest`'s `_contention_environment` sets `SASE_TEST_SELECTION_HEALTH_DISABLED=1`
for every repeat (`tools/run_pytest:846`), deliberately, so a starved diagnostic run does
not pollute the durable store. Three nodes fail deterministically under that variable
with no contention whatsoever:

```bash
SASE_TEST_SELECTION_HEALTH_DISABLED=1 .venv/bin/python -m pytest -q -p no:randomly \
  tests/test_run_pytest_scoped.py
# 1 failed, 10 passed -- test_scoped_escalation_runs_the_governed_fast_lane
#   AssertionError: Right contains 2 more items, first extra item: '-p'
# (the expected command hardcodes the health plugin the env var suppresses)
```

The full set is `test_run_pytest_scoped.py::test_scoped_escalation_runs_the_governed_fast_lane`
plus `test_run_pytest_health.py::test_scoped_run_lands_in_the_durable_health_store` and
`::test_escalated_scoped_run_is_recorded_before_the_handoff`.

`test_contract_set_serial_runtime_stays_within_budget` then fails as a **cascade**, not
on its budget. It runs `tests/contract_manifest.txt` in a nested pytest through
`tools/refresh_contract_manifest._nested_pytest_env`, which copies `os.environ` and so
inherits the variable; `tests/test_run_pytest_scoped.py` is line 18 of that manifest; and
the test asserts `proc.returncode == 0` before it ever looks at elapsed time:

```bash
SASE_TEST_SELECTION_HEALTH_DISABLED=1 .venv/bin/python -m pytest -q -p no:randomly \
  tests/test_contract_manifest.py::test_contract_set_serial_runtime_stays_within_budget
# AssertionError: ... 3 failed, 348 passed in 22.43s / assert 1 == 0
```

Consequences:

- The `sase-h8.1` baseline note's "4/4 F2 wall-clock ceiling" for this node is wrong.
  The node has a genuine F2 problem in the store (19 occurrences in **full** lanes, where
  health recording is on and this cascade cannot occur), but the harness has never
  measured it.
- Phase `clock` cannot falsify a fix to that node under the harness until the cascade is
  removed, and phase `land`'s zero-failure exit criterion is unreachable until then.

**Fix shape** (assigned to phase `tooling`, `sase-h8.7`, and it should go first): make
these three tests pin `SASE_TEST_SELECTION_HEALTH_DISABLED` explicitly via monkeypatch
rather than inheriting whatever the ambient environment says, so their expected command
and their recording assertions are hermetic. Do **not** fix it by stopping the harness
from setting the variable — that would restore store pollution, which the harness
deliberately prevents.

## Correction 3: the `tests/test_bead/` clusters are a since-fixed break

The plan asked triage to test the "genuine break, not a flake" hypothesis for the snooze
cluster before assigning it to F4. Confirmed. Every run that charges any snooze node
charges the whole block:

| Recorded at          | Head        | Workspace | Run failures | Cluster nodes |
| -------------------- | ----------- | --------- | -----------: | ------------: |
| 2026-08-07T15:47:38Z | `34928a454` | sase_16   |            6 |             6 |
| 2026-08-07T16:31:33Z | `3b5c76da4` | sase_11   |            6 |             6 |
| 2026-08-07T16:36:23Z | `d364936e2` | sase_11   |            6 |             6 |
| 2026-08-07T18:53:00Z | `b473a10d0` | sase      |            7 |             6 |
| 2026-08-07T20:01:12Z | `43250ffb6` | sase      |            8 |             6 |

Five heads, three workspaces, one 4.5-hour window, always all six together, never a
subset — the signature of a broken shared behaviour at those commits, not of six
independent timing races. `tests/test_bead/test_close_history_*` behaves identically (3
of 3 together, twice at `e0acf8097`), as does `test_db_migrations.py` (2 of 2 together,
twice at `b5872ca3a`).

All of them pass at HEAD:

```bash
.venv/bin/python -m pytest -q -p no:randomly tests/test_bead/test_cli_snooze.py \
  tests/test_bead/test_snooze_gate.py tests/test_bead/test_snooze_lifecycle.py \
  tests/test_bead/test_close_history_cli_integration.py \
  tests/test_bead/test_close_history_end_to_end.py tests/test_bead/test_db_migrations.py \
  tests/test_bead/test_cli_golden.py
# 131 passed in 6.09s
```

None reproduced in soak A (0/6). They are **confirm-only** for phase `tooling`: record
the evidence, do not re-derive a race that was never there.

## Correction 4: only one node has ever failed on a head containing its own fix

For every node the epic plan credits to a named prior fix, the store was checked with
`git merge-base --is-ancestor <fix> <failing head>`:

| Node                                                             | Named fix   | Last store failure   | Head contains fix? |
| ---------------------------------------------------------------- | ----------- | -------------------- | ------------------ |
| `test_watchdog_keeps_hitch_and_stall_state_machines_independent` | `156cac833` | 2026-08-07T21:33:22Z | **yes**            |
| `test_bulk_waiting_agents_mount_forced_artifact_prompts`         | `bde727ecc` | 2026-08-06T20:10:27Z | no                 |
| `test_contract_set_serial_runtime_stays_within_budget`           | `08d0e0476` | 2026-08-07T20:01:12Z | no                 |
| `test_tracked_executor_reports_terminal_and_extra_commands_live` | `aaa8245df` | 2026-08-07T21:08:05Z | no                 |
| `test_installing_prunes_the_cache_to_the_keep_limit`             | `aec67f31c` | 2026-08-07T14:20:04Z | no                 |
| `test_malformed_header_block_leaves_authored_metadata_visible`   | `5a039ef14` | 2026-08-06T14:37:12Z | no                 |

So the plan's central cautionary example holds — `156cac833` demonstrably did not hold —
but the other five fixes are simply **unfalsified**: the store contains no run that
exercised them. That is what the harness is for, and soak A/B is the first time any of
them has been exercised under reproducible contention.

## The triage table

Families are the plan's F1–F5, plus three this phase added on evidence:

- **F6 — environment-conditional determinism.** Fails deterministically given an
  environment the store does not record. Not load-sensitive.
- **X1 — genuine regression at HEAD.** Out of scope for `sase-h8`.
- **X2 — genuine break at an earlier head, since fixed.** Confirm-only.

`soak` is failures out of 6 repeats in soak A and, where the file was in soak B's
selection, out of 8 repeats in soak B (`—` = file not in that soak's selection); `store`
is total occurrences in full-run records.

| Node                                                                                                   | store | soak | Family | Observed symptom | Fix shape | Phase |
| ------------------------------------------------------------------------------------------------------ | ----: | ---: | ------ | ---------------- | --------- | ----- |
| `test_gate_cli_show.py::test_show_json_reports_declared_inputs_branches_and_actions`                    |    11 |  6/6 | X1     | `GateError: option 'audit' cannot be answered` | update fixture to declare the required input under `inputs` | out of scope |
| `test_gate_cli_show.py::test_show_prints_a_readable_summary_of_the_decision_surface`                    |    11 |  6/6 | X1     | same | same | out of scope |
| `test_gate_cli_show.py::test_show_reports_a_cancelled_gate`                                             |    11 |  6/6 | X1     | same | same | out of scope |
| `test_gate_cli_show.py::test_show_reports_the_terminal_status_of_an_answered_gate`                      |    11 |  6/6 | X1     | same | same | out of scope |
| `gate_conformance/test_gate_conformance.py::test_gate_conformance[cli-legacy_shared_input]`             |    11 |  6/6 | X1     | `GateError: option 'apply' cannot be answered` | same | out of scope |
| `gate_conformance/test_gate_conformance.py::test_gate_conformance[ace-legacy_shared_input]`             |    11 |  6/6 | X1     | same | same | out of scope |
| `test_run_pytest_scoped.py::test_scoped_escalation_runs_the_governed_fast_lane`                         |     2 |  6/6 | F6     | expected command hardcodes the health plugin the ambient env suppresses | monkeypatch `SASE_TEST_SELECTION_HEALTH_DISABLED` to a known value | `tooling` |
| `test_run_pytest_health.py::test_scoped_run_lands_in_the_durable_health_store`                          |     0 |    — | F6     | recording asserted while ambient env disables it | same | `tooling` |
| `test_run_pytest_health.py::test_escalated_scoped_run_is_recorded_before_the_handoff`                   |     0 |    — | F6     | same | same | `tooling` |
| `test_contract_manifest.py::test_contract_set_serial_runtime_stays_within_budget`                       |    19 |  6/6 | F2 + F6 | store: wall-clock budget miss under load. harness: `assert 1 == 0` cascade from the F6 nodes in its nested run | fix the F6 nodes first, then move the guard off wall clock (two normalization attempts have already failed) | `clock` (after `tooling`) |
| `test_agent_metadata_search.py::test_inline_metadata_search_commit_repeat_q_and_passthrough`            |     2 |  3/6 | F3     | `assert None is not None` — `VimSearchController.current_selection` is `None` | make `_set_prompt_text` settle-verified, or quiesce the debounced `AgentDetail.update_display` repaint instead of racing it | `fixture` |
| `test_agent_metadata_search.py::test_inline_metadata_search_reverse_key_override`                       |     2 |  2/6 | F3     | same | same | `fixture` |
| `test_agent_metadata_search.py::test_inline_metadata_search_yank_and_frozen_refresh`                    |     2 |  1/6 | F3     | `assert 'needle' in ''` — `#agent-search-panel` content empty | same | `fixture` |
| `test_stall_watchdog.py::test_watchdog_records_one_stall_with_stack_and_context`                        |     0 | 1/6 · 0/8 | F2     | `assert 3 == 1` — three `tui_stall` records where one was asserted | injectable time source / explicitly advanced clock | `clock` |
| `test_stall_watchdog.py::test_watchdog_writes_loop_recovery_record`                                     |     2 | 1/6 · 1/8 | F2     | `Left contains one more item: 'tui_stall'` — spurious extra stall before `stall_recovered` | same | `clock` |
| `test_stall_watchdog.py::test_watchdog_keeps_hitch_and_stall_state_machines_independent`                |    11 | 0/6 · 0/8 | F2     | spurious hitch cycle during the file's own `asyncio.sleep(0.03)` settle; recurred **after** `156cac833` | same; do not widen tolerances a third time | `clock` |
| `test_stall_watchdog.py::test_watchdog_records_compact_loop_hitch_and_recovery`                         |     3 | 0/6 · 0/8 | F2     | unbalanced hitch/recovery pairs | same | `clock` |
| `test_stall_watchdog.py::test_watchdog_records_compact_pump_hitch_and_recovery`                         |     3 | 0/6 · 0/8 | F2     | same | same | `clock` |
| `modals/test_artifact_files_modal_copy.py::test_artifact_file_modal_Y_anchors_path_recovered_from_agent_meta_json` | 1 | 1/6 | F1 | `assert [] == ['~/workspace/sdd/plans/202605/plan.md']` — clipboard empty at assert time | bounded wait on clipboard delivery, not `pause()` | `pump` |
| `modals/test_artifact_files_modal_copy.py::test_artifact_file_modal_copy_anchors_pdf_markdown_source_path` |   3 |  0/6 | F1     | same file, same clipboard boundary | same | `pump` |
| `test_prompt_bar_xprompt_selector_requests.py::test_vcs_tag_offers_project_local_xprompts_by_canonical_name` | 3 | — · 0/8 | F1 | selector contents asserted before the off-pump request resolves | bounded wait on the resolved selector state | `pump` |
| `test_prompt_bar_xprompt_selector_requests.py::test_vcs_tag_directory_key_spelling_also_resolves`        |     3 | — · 0/8 | F1     | same | same | `pump` |
| `widgets/test_prompt_at_prefix_completion.py::TestAtPrefixIntegration::test_at_prefix_directory_drilldown` | 3 | 0/6 · 0/8 | F1 | drilldown asserted before the directory listing task completes | bounded wait on the listing | `pump` |
| `test_agent_bulk_kill_edit.py::test_bulk_waiting_agents_mount_forced_artifact_prompts`                   |     3 | 0/6 · 0/8 | F1     | already fixed by `bde727ecc`; reference shape for the family | confirm under the harness, do not re-fix | `pump` |
| `test_notification_custom_gate.py::test_tracked_executor_reports_terminal_and_extra_commands_live`       |    13 | 0/6 · 0/8 | F5     | `[Errno 32] Broken pipe` on streaming stdin close | `aaa8245df` is the candidate fix and is now exercised; confirm or account for the separate `assert False is True` symptom | `tooling` |
| `fakey/test_retry_pipeline_e2e.py::test_retryable_failure_then_success_records_lifecycle_and_nudge`      |     3 | 0/6 · **5/8** | F2 (not F5) | `TimeoutError: timed out waiting for retry state 'retrying'` — `wait_for_retry_state`'s fixed 5 s ceiling (`tests/fakey/harness.py:440`) expires while the background thread and its subprocess are still progressing | the ceiling is a diagnostic bound, not a speed assertion: raise it substantially and/or wait on the harness barrier the pipeline already exposes, rather than on elapsed seconds | `tooling` |
| `fakey/test_retry_pipeline_e2e.py::test_kill_during_retry_wait_stops_before_another_subprocess`          |     2 | 0/6 · 0/8 | F2 (not F5) | same file, same fixed-ceiling waits | same | `tooling` |
| `test_install_coverage_contexts_tool.py::test_installing_prunes_the_cache_to_the_keep_limit`             |     6 | 0/6 · 0/8 | F4     | mtime tie-break; fixed by `aec67f31c` 14 minutes after the last recorded failure | confirm under the harness | `tooling` |
| `test_plan_display.py::test_malformed_header_block_leaves_authored_metadata_visible`                     |     5 |  0/6 | F4     | out-of-date `sase_core_rs` binding, identical across 4 workspaces; `5a039ef14` now fails loudly instead | confirm; no code change expected | `tooling` |
| `test_contract_manifest.py::test_contract_manifest_matches_marker_selection`                             |     5 |  0/6 | F4     | manifest vs live marker collection disagreeing across concurrent workspaces | confirm; check for a shared cache | `tooling` |
| `test_plan_approval_actions.py::test_headless_epic_approval_submits_while_inflight_launch_holds_anchor`   |     2 |  0/6 | F4     | in-flight-launch anchor race | confirm under a longer soak | `tooling` |
| `test_run_pytest_scoped.py::test_scoped_mode_runs_the_selection_serially_and_never_acquires`             |     2 |  0/6 | F4     | promoted by a catastrophic run only | confirm; likely not a flake | `tooling` |
| `test_bead/test_cli_snooze.py` ×4, `test_snooze_gate.py` ×1, `test_snooze_lifecycle.py` ×1               |   5–6 |  0/6 | X2     | all-or-nothing block failure across 5 heads / 3 workspaces; green at HEAD | confirm-only; record the evidence | `tooling` |
| `test_bead/test_close_history_cli_integration.py` ×2, `test_close_history_end_to_end.py` ×1              |     3 |  0/6 | X2     | same block signature at `e0acf8097` | confirm-only | `tooling` |
| `test_bead/test_db_migrations.py` ×2                                                                     |     3 |  0/6 | X2     | same block signature at `b5872ca3a` | confirm-only | `tooling` |
| `test_bead/test_cli_golden.py::test_bead_cli_golden_contract[list_json]`                                 |     2 |  0/6 | X2     | promoted by a catastrophic run only | confirm-only | `tooling` |
| `test_bead/test_cli_work_from_plan_concurrency.py` ×2                                                    |     2 |  0/6 | F4     | promoted by a catastrophic run only; genuine concurrency tests | confirm under a longer soak | `tooling` |

## Explicitly out of scope

- **`tests/test_bead/test_cli_work_contention_regressions.py::test_concurrent_bead_mutations_wait_past_the_old_lock_timeout`.**
  20 store occurrences, the single most frequent node, 0/6 in soak A. Tracked under
  `sase-e2` alone, as the 2026-08-05 triage and the epic plan both require. Not absorbed
  here.
- **The six X1 gate nodes.** A live regression at HEAD from `ff0b765a4`, not a flake.
  Filed as a follow-up on `sase-h8.3` for the epic's `land` agent to triage into its own
  task bead.
- **PNG visual-lane nodes.** None surfaced; the soaks ran the non-visual lane only.

## What each remediation phase should do first

- **`pump` (`sase-h8.4`)** — the only node that reproduced is
  `test_artifact_file_modal_Y_anchors_path_recovered_from_agent_meta_json` (1/6), and it
  is a *different* node in the same file than the one the plan named. The clipboard
  delivery boundary is the shared cause for both `test_artifact_files_modal_copy` nodes.
  The other F1 members are store-only; use an injected delay at the named boundary to
  falsify, as the plan's acceptance clause allows.
- **`clock` (`sase-h8.5`)** — two `test_stall_watchdog` nodes reproduced, one of which
  (`test_watchdog_records_one_stall_with_stack_and_context`) no bead had enumerated.
  That is five nodes in one file failing by one shared mechanism, which is the strongest
  argument in this triage for the structural change the plan asks for rather than another
  tolerance widening. `test_contract_set_serial_runtime_stays_within_budget` is blocked
  behind `tooling`'s F6 fix; do not attempt to falsify it under the harness first.
- **`fixture` (`sase-h8.6`)** — all three `test_agent_metadata_search` nodes reproduced
  (3/6, 2/6, 1/6) and are the highest-yield target in the whole class. `_set_prompt_text`
  (`tests/ace/tui/test_agent_metadata_search.py:24`) waits for the debouncer to be
  not-pending, updates the panel, and then does one bare `pause()` — the queued
  `AgentDetail.update_display → AgentPromptPanel.update_display` repaint lands during that
  pause and drops the injected corpus. `test_rapid_navigation_loads_only_the_final_detail`
  is **not** in the store's flake set and did not reproduce; the plan's expected
  membership overstates it.
- **`tooling` (`sase-h8.7`)** — do the F6 fix first; it unblocks the harness for every
  other phase. The one node in this phase that actually reproduces is
  `tests/fakey/test_retry_pipeline_e2e.py::test_retryable_failure_then_success_records_lifecycle_and_nudge`
  at 5/8, and it is a fixed 5-second ceiling, not a pipe race — F5 is the wrong starting
  hypothesis for it. Everything else in the phase is confirm-with-evidence rather than
  re-fix: the bead-store clusters (X2),
  `test_installing_prunes_the_cache_to_the_keep_limit`,
  `test_malformed_header_block_leaves_authored_metadata_visible`, and
  `test_tracked_executor_reports_terminal_and_extra_commands_live` all have a named
  candidate fix and zero reproductions across 14 combined repeats.
- **`gate` (`sase-h8.8`)** — two findings change the gate's design. It must discount
  full runs above a failure-count threshold (three catastrophic runs promoted 11 nodes),
  and it must not read a deterministic break on master as a flake (the six X1 nodes are
  indistinguishable from flakes to `reproducible_flake_nodeids` today).
