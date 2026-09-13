# Deciding the Test-Feedback Speedup: Fresh Evidence and a Recommendation

Research performed 2026-09-13 at SASE revision `f3a39fa835` on host apollo (workspace
`sase_12`). This report derives from the consolidated
[test_feedback_cost_and_confidence](test_feedback_cost_and_confidence/test_feedback_cost_and_confidence.md)
report of 2026-09-12; it verifies that report's claims against today's tree, adds new
measurements that were hypotheses yesterday, and converts the combined evidence into a
single recommended course of action.

**Recommendation in one sentence: do not change the verification architecture — repair
the two broken inputs that are silently defeating it (hermetic CI and coverage-context
baselines), then cut the leak detector's per-test cost in place, and only then consider
harness and executor work.**

## 1. What Changed Since Yesterday's Report: Nothing Structural

Twenty-three commits landed between the prior report's inspected revision
(`e1a2f78395`) and today's HEAD. None of them touch the selector, the leak detector,
the cost plugin, `tools/run_pytest`, or the CI workflows; they are feature commits that
*added* roughly 1,800 lines of new tests in one day. Two consequences:

- Every structural claim in the prior report still holds at HEAD (verified by reading
  the detector, selection-rule, and Justfile sources directly).
- The suite is compounding: the selection universe is now 3,805 non-visual test files
  (3,516 attributed files / 38,700 nodes in the September 6 cost recording). Any
  do-nothing option gets worse on a measurable slope.

One landed commit is relevant to a known escalation cause: `edaf35bd95` ("fix(rust):
keep dev builds in managed targets") should reduce spurious Rust-extension identity
churn. Whether it actually lowers the `core-identity-changed` escalation count (32 of
the last 91 scoped runs) is now observable in `just selection-health` and should be
watched, not assumed.

## 2. Fresh Evidence A: CI Is Still Red, and the Cost Is No Longer Hypothetical

The prior report's first priority — restore a green baseline — has not happened, and
today's data shows what that costs.

**Master Gate.** Every completed Master Gate run today failed (seven consecutive
sampled, e.g. runs 34752937763, 34752859969, 34752328752). Each fails in 6–9 minutes
across several of the eight shards. The dominant failure class is exactly the one the
prior report diagnosed: `Author identity unknown` from git commits inside
`tests/sdd/test_artifact_link_*` (temporary repositories inheriting the runner's absent
git identity — a host-hermeticity bug, since developer machines mask it via
`~/.gitconfig`). Two additional failures ride along in the sampled run:
`tests/main/test_var_integration.py` (`assert '27' == '28'`) and
`tests/test_bead/test_cli_work_epic_dry_run.py` (`assert 0 == 1`), both consistent with
newly landed features whose tests never saw a green gate to regress from.

**Full CI.** The latest five scheduled Full CI runs all failed (~100 minutes each). In
run 34738952402: `test (3.13)` failed at 1h30m, `contention-test` failed at 36m, and
`coverage-contexts` failed at its "Record per-test coverage contexts" step after 42m —
the upload step runs (`if: always()`) but has nothing usable to ship.

The compounding effect matters more than any single failure: a red gate cannot tell
anyone about a *new* regression, `ci_watch` freshness can never be satisfied, and — the
new finding below — the broken `coverage-contexts` job is directly inflating every
agent's inner loop.

## 3. Fresh Evidence B: The Scoped Lane Is Starved, and the Causal Chain Is Now Visible

`tools/selection_health --json` over the durable host-local store (91 scoped runs, 57
full runs):

| Metric                              | Value                | Reading                                                          |
| ----------------------------------- | -------------------- | ---------------------------------------------------------------- |
| Escalation rate                     | 53/91 = **58.2%**    | Worse than the 55% in yesterday's report; the "fast" lane is a coin flip. |
| Median scoped duration              | **19.6 min** (p90 36.8, max 43) | The agent-default inner loop, before lint gates.                 |
| Coverage contexts consulted         | 42 runs              | `context_missing_runs: 42`, `context_stale_runs: 0`              |
| Selections contributed by contexts  | **0, ever**          | The dynamic half of the selector has never fired on this host.   |
| `no-baseline-depth-boost` fired     | 42 runs              | Missing baseline → compensating depth boost → bigger selections. |
| `serial-budget-exceeded` fired      | 31 runs              | Inflated selections then blow the 232 s serial budget.           |
| `core-identity-changed` fired       | 32 runs              | Environment-identity churn forces escalation.                    |
| Median selection size               | 638 files (16.8% of universe) | Large for a typical diff; consistent with depth-boost inflation. |
| Worker-seconds saved by selection   | 44,305               | Selection *works* when it runs — the mechanism is worth rescuing. |
| False negatives on record           | 19                   | Unchanged; still needs matched-revision replay before being called causal. |

This is the report's central new synthesis. The chain is:

**red Full CI → coverage-contexts job never publishes a baseline → every scoped run
fires `context-baseline-missing` + `no-baseline-depth-boost` → selections inflate
toward 638+ files → `serial-budget-exceeded` (a 232 s budget calibrated on athena at 28
workers, not apollo) → 58% of "fast" runs escalate into the full fast lane → the
agent-default `just check` has a ~20-minute median and consumes full-suite capacity it
was designed to avoid.**

Each link is individually confirmed in the rule sources
(`tests/_test_selection_rules.py`, `tests/_test_selection_contexts.py` — a fresh
baseline is what `no-baseline-depth-boost` explicitly compensates for) and in the
health store's rule histogram. The slow feedback loop agents feel locally is, to first
order, a *plumbing* failure — not an architecture failure and not raw suite size.

## 4. Fresh Evidence C: The Detector Multiplier, Measured on Today's Tree

Yesterday's report treated the leak detector's cost as the first hypothesis to test,
with B's single-file measurement (7.7 s → 27.3 s) as suggestive. I ran the four-way
experiment it prescribed, at small scale, on today's HEAD: 74 tests across two
representative files (`tests/test_command_catalog.py`,
`tests/ace/tui/test_leader_keymap_dispatch.py`), serial, same interpreter and wheel,
plugins injected exactly as `tools/run_pytest cost` does:

| Configuration                | Wall (s) | pytest test phase (s) |
| ---------------------------- | -------- | --------------------- |
| Plain (run 1 / run 2)        | 8.2 / 9.2 | 3.3 / 3.9            |
| Cost plugin only             | 7.8      | 3.1                   |
| Leak detector only           | 21.7     | 16.9                  |
| Cost + leak (the cost lane)  | 21.6     | 16.5                  |

Three conclusions, now measured rather than inferred:

1. **The leak detector is the cost-lane multiplier**: ~5x on the test phase, ~2.6x on
   wall time even for this import-light batch. Detector cost scales with loaded SASE
   modules (full-suite workers load ~4,350), so the full-suite multiplier is at least
   this large. This is fully consistent with the 86.8% unattributed CPU in the
   September 6 recording (~32,857 CPU-seconds outside test and collection buckets).
2. **The cost plugin is essentially free.** Proposals to replace `test-cost` with cheap
   timings attack the wrong plugin.
3. **The two plugins do not meaningfully interact** at this scale — "both" equals
   "leak-only" — so detector optimization can proceed without redesigning cost
   recording.

The prior report's suite-scale four-way experiment (fixed SHA, wheel digest, worker
width, host class; run through the monitor flow under the capacity gate) is still worth
doing before ratcheting budgets, but the ranking question it was designed to answer is
no longer open.

## 5. The Decision Space

Candidates, judged against the two-speed decisions' actual constraint (shared host
capacity, ~46,000 gated worker-minutes/day, ~61 worker-minutes per full run):

| Option | Inner-loop effect | Landing-lane effect | Reliability risk | Cost | Verdict |
| --- | --- | --- | --- | --- | --- |
| **A. Hermeticity repair + green CI** (test-owned git identity/config; triage the two feature-test failures; fail-early binding check) | Indirect but large (prerequisite for B; ends escalation-by-noise) | Restores the only correctness signal | None — strictly adds determinism | Days | **Do first** |
| **B. Coverage-baseline restoration + selection recalibration** (fix the `coverage-contexts` producer; fetch via existing `refresh-contexts-baseline`; recalibrate the 232 s budget for apollo widths; replay the 19 false negatives on matched revisions) | Direct: removes the depth-boost/serial-budget chain behind most of the 58% escalation | Modest | Low — union of contexts with static closure stays conservative; false-negative replay guards recall | Days, after A | **Do second** |
| **C. Detector cost reduction in place** (Rust-core fingerprint walk per the core boundary; dirty-module tracking with the existing detector as comparison oracle; keep per-test blocking semantics) | Small | Large: the measured ~5x test-phase multiplier bounds the prize on the ~95-minute cost lane | Medium — identity-keyed caches are unsafe (in-place mutation), per-file snapshots miss cleaned-up leaks; both need mutation tests + oracle runs | 1–2 weeks | **Do third** |
| D. Harness reductions (AcePageGroup extension by file rank, settle-wait tightening, fixture-scan fixes, drop the autouse `models_panel` import) | Moderate, incremental | Moderate | Low if fresh-page/order checks are kept per migrated module | Ongoing batches | Steady-state work after A–C |
| E. Executor changes (xdist `loadfile` comparison, then bounded `pytest -n0` file pools) | — | Unknown until benchmarked | Medium (equivalence must be proven: node multiset, outcomes, isolation) | Weeks | Benchmark-gated, not now |
| F. Scheduled-only leak detection | — | Large | **High** — state-poisoning lands before detection; a 2-hour cron is not a 2-hour guarantee (Full CI itself takes ~100 min and is currently red) | Small | Rejected as default, per prior report |
| G. Bazel/Pants, repo split, more hardware | — | — | — | Months / $ | Still rejected; see reopen conditions |

Industry practice supports this ordering rather than the glamorous options. Predictive
and coverage-based test selection (Meta's predictive selection, Google's presubmit/
postsubmit split — the same two-speed shape SASE already adopted) all depend on
trustworthy ground truth from a green postsubmit lane; SASE built that pipeline and
then let its input rot. Bazel-style caching and selection require hermetic test inputs
— the `Author identity unknown` class is precisely the non-hermeticity that would
poison such a migration, so option G cannot be a way to *skip* option A. And
testmon-style per-test coverage selection is what `coverage-contexts` already
implements, with the conservative static-closure union the pure-coverage tools lack
(Rust bindings, data assets, subprocesses, dynamic imports). Nothing external offers a
shortcut past fixing what exists.

## 6. Recommended Solution

**Adopt a three-step repair program, in strict order, and defer everything else behind
its measurements.**

**Step 1 — Hermeticity sprint (days).** Give every test-created git repository a
deterministic, test-owned identity and config (exported `GIT_CONFIG_GLOBAL` /
`GIT_CONFIG_SYSTEM` pointing at a fixture-owned file, plus author/committer env
defaults, with explicit overrides for identity-sensitive tests), and add a guard test
that runs a representative repo-creating test with `HOME` redirected so the class can
never silently return. Triage the `test_var_integration` and epic-dry-run failures.
Exit criterion: Master Gate green on consecutive pushes and one green Full CI,
including `coverage-contexts` producing and uploading a `.coverage` database.

**Step 2 — Feed the selector (days, immediately after).** Restore baseline fetch on
agent hosts, then recalibrate: re-derive the serial-runtime budget from recent full
fast runs on apollo at the widths agents actually get (the 232 s athena-derived
constant is both the escalation trigger and a poor counterfactual), and replay the 19
recorded false negatives on matched revisions before treating selector recall as a
blocker. Exit criteria: `context_selected_total > 0` and climbing,
`no-baseline-depth-boost` at ~0 fires, escalation rate well under 30%, median `just
check` under 10 minutes on ordinary diffs (the prior report's 50%-reduction criterion),
with p90 and escalations reported separately.

**Step 3 — Detector program (1–2 weeks, parallelizable with step 2 once CI is green).**
Run the suite-scale four-way experiment through the monitor flow to fix the baseline,
then optimize the snapshot/fingerprint path in place — a Rust-core fingerprint walk
(this is shared backend behavior; it belongs behind the `sase-core` boundary, not in a
Python fast path) and/or dirty-module tracking validated against the existing detector
as a comparison oracle on mutation cases. Per-test blocking detection semantics are
non-negotiable; scheduled-only detection (option F) stays rejected unless the user
explicitly accepts delayed poisoning detection as a product decision. Exit criterion:
cost-lane wall time reduced by the detector's measured share without a single lost
finding across oracle comparison runs.

Afterward, options D and E proceed as small evidence-gated batches under the prior
report's acceptance criteria, which remain sound. Hardware, build-system migration, and
repo splitting stay closed with explicit reopen conditions: revisit only if, *after*
steps 1–3 land, the fast gate's p50 no longer fits the commit cadence or selection
health shows the heuristic materially wrong in practice.

**Why this is the best answer to "faster feedback without less reliability":** it is
the only option set whose speedups come from *removing defects and waste* — a
non-hermetic test class, a dead data pipeline, an unoptimized 5x hook — rather than
from trading away detection guarantees (F), rebuilding orchestration on unproven
equivalence (E), or buying capacity that repeated scanning would immediately consume
(G). Every step has a measurable exit criterion, and every deferred option has a
recorded condition that would reopen it.

## 7. Provenance

Evidence gathered this session: `git log --stat e1a2f78395..HEAD` (infra-file scope);
`gh run list`/`gh run view --log-failed` for Master Gate runs 34752937763 et al. and
Full CI runs 34738952402 et al.; `tools/selection_health --json` on the durable
host-local store; direct reads of `Justfile`, `tools/run_pytest`,
`tests/_global_state_leak_detector.py`, `tests/_test_selection.py`,
`tests/_test_selection_rules.py`, `pyproject.toml`; and the four-way timing runs
described in §4 (74 tests, serial, apollo, `.venv` interpreter, plugins injected as
`tools/run_pytest cost` does). The prior consolidated report was consumed via `sase
artifact read
research:202609/test_feedback_cost_and_confidence/test_feedback_cost_and_confidence.md`;
the `two-speed-verification` and `ci-two-speed-split` decision records and
`lint_and_test.md` were read through SASE memory's audited interface.
