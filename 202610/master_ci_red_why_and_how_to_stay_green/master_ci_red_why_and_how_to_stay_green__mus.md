# Why Master Is Failing in CI — Research Report

**Date:** 2026-10-01 · **Scope:** `sase` repo, `master` branch, Master Gate workflow
**Investigated run (primary):** `36872281569` (`feat(sase-1dr.10)`, 2026-10-01T13:55:08Z)
**Corroborating runs:** `36865946503`, `36865947307`, `36860850910`, `36855942451`, `36851180356`, `36846361823` — all `failure`
**Local HEAD verified:** `781063e38e` — key failures reproduce locally

## TL;DR

Master is not failing for one reason. It is failing for **six independent, all-real
reasons at once**: one `lint` gate failure plus test failures in **7 of 8** Master Gate
shards (11 distinct `FAILED` tests + 1 collection `ERROR`). Every failure I sampled
reproduces on a clean local checkout, so this is genuine master breakage, not flake or
runner drift.

The common mechanism is **contract/audit drift**: recent feature commits changed a
CLI surface, a function signature, or a module layout without updating the
registry, completion table, help-text assertion, or re-export that pins that surface.
`just check` (the agent default) runs only **diff-scoped tests** (`just test-scoped`),
so authors get a green local signal while the whole-repo audit tests that CI runs stay
red. A burst of ~10 feature commits on 2026-09-30 → 2026-10-01 stacked the drift faster
than anyone repaired it, and each new master push re-reddens the per-SHA Master Gate.

> **Bottom line:** fix the six drift groups below (mostly one-line registry/test
> updates, one dead-code decision), then close the process hole that let red code
> land: make the audit/contract tests impossible to skip before merge.

---

## 1. What exactly is red

### 1.1 Gate-level picture (run `36872281569`)

| Job | Result | Detail |
|---|---|---|
| `core-wheel` | ✅ success | Rust wheel builds fine; the pin mechanism works |
| `lint` | ❌ failure | Symvision: 3 unused public symbols (see §2.1) |
| `test (shard 1)` | ✅ success | The only green shard |
| `test (shards 2–8)` | ❌ failure (7 shards) | 11 distinct `FAILED` + 1 `ERROR`, each shard 1–3 failures out of ~6,000 passing tests per shard |

The prior five master pushes show the same shape (lint + majority of shards red), so
this is a sustained broken-master window, not one bad commit. `Deploy Docs` stays green
throughout — docs build is unaffected.

### 1.2 The complete failure inventory

| # | Failing test / gate | Shard | Signature |
|---|---|---|---|
| 1 | Symvision lint (`just lint`) | lint | `HandoffSubmitResult`, `StarterResolution`, `owner_ref` reported unused; `Recipe _lint-symvision failed`, exit 1 |
| 2 | `test_force_reuse_launch_seam_rejection.py::test_plain_sase_run_without_request_sidecar_still_rejects_forced_reuse` | 8 | `Expected launch_agents_from_cwd(..., origin='typed')`, actual adds `history_text=None` |
| 3 | `...::test_sidecar_without_authorization_still_rejects_forced_reuse` | 8 | Same `history_text=None` mismatch |
| 4 | `test_bead/test_show_images.py::test_parser_help_covers_images_and_open` | 8 | `assert '-i, --images' in <help>` fails against current `sase bead show -h` text |
| 5 | `test_agent_header_panel.py` collection | 2, 4 | `ImportError: cannot import name 'test_hint_document_forces_expansion' from ...test_agent_header_panel_basic` |
| 6 | `test_contract_manifest.py::test_contract_manifest_matches_marker_selection` | 4 | Cascades from #5: `pytest -m contract --collect-only` exits 2 |
| 7 | `completion/test_kind_coverage.py::test_every_value_slot_is_kinded_choiced_or_hinted` | 6 | `uncaptioned completion value slots: memory/history:at` |
| 8 | `main/test_memory_log.py::test_memory_log_json_id_outputs_raw_event` | 7 | JSON payload dict mismatch (extra `blob_oid: None, included_blob_oids: []`-style keys) |
| 9 | `main/test_parser_command_help.py::test_memory_help_marks_primary_command_and_init_alias` | 7 | Expected `'{agent-docs,init,list,log,read,show,web}'` not in actual `sase memory -h` (actual has `history` subcommand) |
| 10 | `test_agent_artifact_directory_operation_audit.py::...sites_are_reviewed` | 7 | Reviewed-sites set mismatch |
| 11 | `test_partial_launch_cleanup.py::test_launch_query_rolls_back_partial_multi_prompt_launch` | 5 | `TypeError: fail_launch() got an unexpected keyword argument 'history_text'` |
| 12 | `test_axe_run_agent_runner_started_at.py::...cleanup_updates_artifact_index` | 5 | `assert 4 == 3` |
| 13 | `test_config_schema_repositories.py::...intrinsic_agents_sidecar_contract` | 3 | `assert '~/.sase/projects/<project_key>/repos/agents' in <description>` fails |

Shard wall-times in the failing run range from ~413 s (shard 6) to **~905 s (shard 3)**,
against the Master Gate's 20-minute (1,200 s) per-job ceiling — currently passing the
ceiling, but shard 3 has < 5 minutes of headroom left.

---

## 2. Root causes (grouped, with evidence)

### 2.1 Lint: dead public symbols left behind by the starter epic

`just lint` → `_lint-symvision` fails (verified locally — identical output):

```text
Unused public functions/classes:
  HandoffSubmitResult in src/sase/tool/handoff_launch.py
  StarterResolution in src/sase/tool/starter.py
  owner_ref in src/sase/tool/owner.py
```

`git log -S` traces the first two to `018061f6f2` (`feat(tool): implement starter
scoped tool runs`, 2026-09-30). The feature landed the types; nothing ever imported
them (or the use was later removed), and no epic-whitelist or privatization followed.
`owner_ref` is the same class of leftover. This is the cheapest failure on master and
the most telling: `just check` *does* include the symvision stage, so whoever landed
the red window either did not run `just check` to green or landed over it.

### 2.2 `history_text` signature drift (failures #2, #3, #11)

Commit `ce0f61846c` (`feat(history): record each submission's canonical text once`,
2026-09-30) threaded a new `history_text` kwarg through the launch path
(`src/sase/main/query_handler/_launch.py`, `src/sase/agent/launch_cwd*.py`). It updated
its own new tests (`tests/history/test_prompt_canonical_text.py`, `test_sase_run_history_ingress.py`)
but **not** the three pre-existing call-shape assertions:

- `tests/test_force_reuse_launch_seam_rejection.py` (2 tests assert
  `mock_launch.assert_called_once_with(prompt, origin="typed")`; code now passes
  `history_text=None`) — reproduced locally in 5.5 s;
- `tests/test_partial_launch_cleanup.py` (local `fail_launch()` stub lacks the new kwarg
  → `TypeError`).

Fix is mechanical (accept and assert the new kwarg), but the miss pattern matters: the
author updated tests colocated with the feature and missed behavior-adjacent tests owned
by a different concern (forced-reuse guards, partial-launch rollback).

### 2.3 Test-split re-export breakage (failures #5, #6)

`cf049c44aa` split `test_agent_header_panel.py` into `basic / preview / scroll`
modules with a thin facade re-exporting names. `c6b802a647` (`keep sticky header
collapsed in hint mode`, 2026-09-30) then renamed/removed
`test_hint_document_forces_expansion` in `test_agent_header_panel_basic.py` (current
file has `test_hint_mode_*` tests instead) but **never updated the facade's import list**
(`tests/ace/tui/widgets/test_agent_header_panel.py:19,71`). Result: every shard that
collects the facade errors, and shard 4's contract-manifest test — which shells out to
`pytest -m contract --collect-only` — fails as a cascade. Two shards (2 and 4) pay for
one stale import line.

### 2.4 Completion-kind registry drift (failure #7)

`92c6337de8` (`feat(sase-1dr.6): pager time axis and read view…`, 2026-10-01) added a
`--at` value slot to `memory history` without registering it in any of the three
places `test_every_value_slot_is_kinded_choiced_or_hinted` accepts
(`src/sase/completion/kinds.py` `NAME_TABLE`/`PATH_OVERRIDES`, `argparse choices=`, or
the `value_hint` table). The test's error message is literally the fix recipe. This is
the project's best-designed guardrail — it names the file and the three options — and
it is being landed over rather than satisfied.

### 2.5 Help-text / schema / audit drift (failures #4, #8, #9, #10, #13)

Five failures share one shape: **the CLI surface moved; the pinning test did not.**

- `sase memory -h` gained the `history` subcommand (memory-history feed epics
  `92c6337de8`, `7884ffe854`, `3819d254b3`, `429d6577de`) → the help assertion
  expecting exactly `{agent-docs,init,list,log,read,show,web}` fails.
- `sase bead show -h` changed its `-i/--images` rendering → images help test fails.
- `sase memory log --json --id` payload gained keys (e.g. `blob_oid`,
  `included_blob_oids`) → raw-event equality test fails.
- Config-schema description for sidecar repos was reworded; the
  `~/.sase/projects/<project_key>/repos/agents` substring assertion fails.
- The artifact-directory operation audit set is stale (new write sites from recent
  epics not added to the reviewed set).

Each is individually trivial; collectively they prove that **landing a CLI-visible
feature without running the audit tests is now the norm, not the exception.**

### 2.6 Runner bookkeeping drift (failure #12)

`test_home_mode_running_marker_cleanup_updates_artifact_index` asserts an artifact-index
count of 3; the code now produces 4. This smells like a neighboring epic adding a
marker/index write without bumping the count. Small, but it is the only failure in the
batch with no self-describing fix hint — it needs a human to decide whether 4 is
correct (likely yes) and update the expectation plus a comment naming the fourth entry.

---

## 3. Why did this merge? (process cause)

Three compounding factors, all visible in the repo — no speculation required:

1. **`just check` is scoped, CI is whole-repo.** `just check` ends with `just
   test-scoped` (diff-based selection) plus `print_scoped_summary`. An agent that runs
   only `just check` gets a green signal covering its own diff while the audit,
   contract, completion-kind, help-text, and cross-module tests that Master Gate runs
   stay red. The Justfile even documents the two-speed intent (`check-full is
   explicit-only` decision record). Two-speed verification only works if the fast lane
   reliably selects the audit tests affected by a diff — the failure list above shows
   several cases (help text, kinds, facade re-exports) where it evidently did not, or
   the author never ran even the scoped lane.
2. **Stacked merges without a green-master gate.** Six master pushes failed in
   sequence over ~4 hours while new features kept landing on top (1dr.6 → 1dr.8 →
   1dr.7 → 1dr.10 plus the `prompt_prediction_wire` split). Each push gets its own
   non-cancelling Master Gate run (grouped by SHA, deliberately), which is excellent
   for attribution — and it is attributing correctly: every SHA is independently red.
   But nothing in the observed flow *stopped the next landing*. Per-SHA attribution
   without a merge-blocking green-master rule is observability without control.
3. **Audit tests are numerous, exact-match, and scattered.** Help-text substring
   assertions, JSON-equality assertions, reviewed-sites sets, kind-coverage tables,
   schema-description substrings — each is cheap to satisfy and expensive to discover
   from a feature diff. A contributor adding `--at` cannot reasonably know to touch
   `kinds.py` unless the scoped lane selects `test_kind_coverage.py` or a checklist
   tells them. Today's answer to "how would I know?" is "CI tells you after merge,"
   which is too late.

Timeout pressure is a secondary risk, not a current cause: no shard hit the 20-minute
ceiling in the investigated run, but shard 3 at 905 s leaves little margin for suite
growth, and the `ci.yml` comment history already records repeated ceiling bumps
(90 → 120 min on the coverage leg). The next slowdown will convert slow shards into
timeout reds on top of the real reds.

---

## 4. What to do now (immediate fix checklist)

In priority order — each line is independently landable, smallest first:

- [ ] **Lint (5 min):** decide per symbol — privatize/delete `HandoffSubmitResult`,
      `StarterResolution`, `owner_ref`, or add a Symvision epic whitelist entry per
      `sase/memory/symvision.md`. Re-run `just lint` to green.
- [ ] **Facade import (5 min):** remove/rename `test_hint_document_forces_expansion`
      in `tests/ace/tui/widgets/test_agent_header_panel.py:19,71` to match the current
      `test_agent_header_panel_basic.py` names. Clears shards 2 + 4 (including the
      contract-manifest cascade).
- [ ] **`history_text` (15 min):** update the two `assert_called_once_with` expectations
      in `tests/test_force_reuse_launch_seam_rejection.py` and the `fail_launch()` stub
      signature in `tests/test_partial_launch_cleanup.py`. Clears shard 8 (×2) + shard 5 (×1).
- [ ] **Kind registry (10 min):** register `memory/history --at` in
      `src/sase/completion/kinds.py` (or add `choices=`/`value_hint`, per the test's own
      message). Clears shard 6.
- [ ] **Help/schema/audit (30–60 min):** update the five expectations in §2.5 to the
      intended new surfaces — but treat each diff as a review: confirm the new help text,
      JSON keys, schema wording, and write-site set are *intended* before blessing them.
      The `4 == 3` runner test needs an explicit correctness call, not a blind bump.
- [ ] **Confirm:** `just check` green locally, then watch one Master Gate run fully green
      before landing the next feature. Do not stack further features on a red master.

---

## 5. Prevention (so this stops recurring)

**Make the audit tests unskippable (highest leverage).**

- Promote the contract/audit set (`test_kind_coverage`, `test_contract_manifest`,
  help-text/schema/artifact-audit tests, facade collection) into the `test-scoped`
  selector's *always-run* set, or add a `just check` stage that runs exactly that
  named set. The scoped lane must be a superset of "tests that pin cross-cutting
  surfaces," not just "tests near the diff."
- Add a one-line feature checklist to `CONTRIBUTING.md` (or the plan template): *CLI
  surface changed? → run kinds + help + schema + audit tests. Signature changed? →
  grep all callers + stub signatures. Test file split? → update facades.*

**Block landing on red master.**

- Require a green Master Gate on `HEAD` before the next `master` push lands (merge
  queue, `stitch` gate, or human discipline with a `ci_watch`-style freshness check —
  the repo already has `ci_watch` vocabulary). Attribution without blocking has been
  measured and found insufficient: six red SHAs in a row.
- Keep the per-SHA non-cancelling Master Gate concurrency — it is the reason this
  report can attribute each failure to a commit range. Do not "fix" redness by
  cancelling older runs.

**Shrink the feedback loop.**

- The 905-second shard and the 90→120-minute coverage-leg history say the suite is
  growing into its ceilings. Refresh `tests/shard_timings.json` (the repo has
  `just refresh-shard-timings` + a ratchet workflow), and consider splitting the
  slowest shard before the 20-minute Master Gate ceiling starts producing timeout
  failures that mask real ones.
- Keep `Deploy Docs` as-is: it is the only consistently green signal and correctly
  scopes docs builds off the red path.

---

## 6. Recommended solution

**Do these three things, in this order:**

1. **Stop the line, then fix small-to-large.** Freeze feature landings until one Master
   Gate run is fully green. Land the checklist in §4 in the order given (lint →
   facade → `history_text` → kinds → audit set), each as its own minimal commit so the
   per-SHA gate confirms each fix independently. Expected cost: one focused session;
   no design work, no migration, no new infrastructure.
2. **Promote the audit set into the fast lane.** Make `just check` (or `test-scoped`)
   always run the half-dozen pinning tests in §2.4–§2.5 plus a facade-collection smoke,
   so the next `--at`-style change fails locally in seconds instead of on master in
   15 minutes. This single change would have prevented the majority of the current
   red window.
3. **Gate pushes on green master.** Adopt a merge queue or an explicit "no landing on
   red master" rule enforced by tooling, not etiquette. The Master Gate's per-SHA
   attribution is already built for this — it just needs a blocking consumer.

Master is red for ordinary, fixable reasons — six small drifts landing faster than
repairs. The suite caught every one of them; the process let them land anyway. Close
the process hole and the suite becomes a guardrail again instead of an obituary.

---

## Appendix — evidence & reproduction

- Master Gate runs (all `failure`, `master`, 2026-10-01): `36846361823`,
  `36851180356`, `36855942451`, `36860850910`, `36865946503`, `36865947307`,
  `36872281569` (`gh run list --branch master --limit 20`).
- Primary log: `gh run view 36872281569 --log-failed` — lint symvision block plus
  per-shard `short test summary info` lines quoted in §1.2 (shard counts: 3 + 1 + 3 +
  1 + 2 + 1 failed across shards 8/4/7/6/5/3; shard 1 green).
- Local reproduction at `781063e38e`: `pytest
  tests/test_force_reuse_launch_seam_rejection.py` (fails, `history_text=None`
  mismatch), `symvision src/sase …` (3 unused symbols), `pytest
  tests/completion/test_kind_coverage.py tests/main/test_memory_log.py
  tests/test_config_schema_repositories.py` (3 failures, same signatures as CI).
- Implicated commits: `018061f6f2` (starter types), `ce0f61846c` (`history_text`),
  `cf049c44aa` + `c6b802a647` (header-panel split + rename), `92c6337de8` (`--at` /
  memory-history surface), `60b2d3dfdb` lineage (bead show surface).
- Workflow definitions: `.github/workflows/master-gate.yml` (per-SHA, 8 shards,
  20-min ceilings), `.github/workflows/ci.yml` (PR/full lane), `.github/workflows/full.yml`
  (scheduled exhaustive lane). `Justfile:744` (`check` → `test-scoped`, not the full suite).
