# Accelerating SASE Test Feedback Without Weakening Reliability

**Research date:** 2026-09-12  
**Repository revision examined:** `e1a2f7839502dd228fc4ab29687c4256f3cf055c`  
**Scope:** pytest execution, Textual/Ace test harnesses, selection telemetry, and GitHub Actions topology

## Executive summary

SASE does not primarily have a “pytest needs more parallelism” problem. It already uses pytest-xdist, deterministic outer CI shards, a worker-token gate, historical file timings, scoped test selection, coverage contexts, cost attribution, and separate fast versus exhaustive workflows. The current bottleneck is repeated work inside that architecture:

- thousands of expensive Textual app boots and unconditional settling pauses;
- repository-wide validation and nested pytest collection launched again from individual tests;
- every xdist worker independently collecting the selected test universe;
- high-scope fixtures being repeated once per worker;
- costly instrumentation being placed on critical CI paths even when it does not add functional coverage;
- a scoped lane whose selection evidence is frequently unavailable and whose median response is already measured in tens of minutes.

The strongest strategy is therefore **cost removal plus execution-boundary redesign**, not additional hardware and not a more aggressive test selector. Keep every assertion and retain a required exhaustive gate, but make the same tests cheaper: amortize application lifecycle at the module/file boundary, replace broad “wait until idle” calls with observable readiness conditions, remove redundant nested whole-repository work, and prototype timing-balanced file shards executed by plain single-process pytest instances. The last change preserves parallel execution while avoiding xdist’s repeated full collection and aligns naturally with module-scoped application reuse.

The suite is currently red in CI for at least one deterministic environment defect, so the first operational step must be restoring a reproducible green baseline. Optimization measurements taken against an already-red suite cannot safely distinguish performance changes from correctness regressions.

## What exists today

The repository already has a mature two-speed test system:

- `just test` runs the default fast inventory in parallel through `tools/run_pytest`.
- `just test-scoped` maps a diff to a subset of tests and can use a limited “middle gear.”
- `just test-cost` executes the fast suite with detailed timing and attribution.
- `just check` combines whole-repository static checks with scoped tests.
- `just check-full` combines static checks with the fully attributed fast suite and flake checks.
- The master gate uses eight deterministic, timing-balanced file shards. Each shard then invokes the normal parallel test runner.
- The exhaustive workflow covers multiple Python versions, coverage contexts, visual tests, page-group isolation, contention, performance floors, and other specialist lanes.

Two accepted design decisions are particularly relevant. The project intentionally chose a never-cancelled per-SHA fast master gate plus a scheduled exhaustive matrix, and intentionally chose scoped local verification plus a full landing gate. Those are sensible reliability boundaries. Both decision records also state conditions under which the choices should be revisited: the fast gate no longer fitting commit cadence, or selection health being materially wrong. Current telemetry indicates that both reopening conditions deserve review, but it does not justify simply discarding either reliability boundary.

The implementation is also more sophisticated than a typical pytest repository. `tools/run_pytest` supports work-stealing and file-based distribution, enforces a shared worker-token budget, records durations and resources, and uses a historical timing table for deterministic shards. That means a wholesale replacement with another fashionable test runner would throw away useful machinery before the dominant sources of waste have been addressed.

## Measured state

### Repository scale and growth

At the examined revision, the repository contains 3,952 `test_*.py` files. The newest cost record, captured on 2026-09-06 with seven workers, reports:

| Metric | Current record |
|---|---:|
| Collected test nodes | 38,700 |
| Attributed test files | 3,516 |
| Sum of file wall time | 6,406.7 s |
| Sum of file CPU time | 4,681.4 s |
| Attributed idle time | 1,725.3 s |
| Aggregate collection time | 328.1 s |
| Median worker RSS | about 547 MiB |
| Peak worker RSS | about 1.51 GiB |

The aggregate collection number is roughly 46.9 seconds per worker. That matters because pytest-xdist’s controller does not collect once and distribute the result; each worker performs collection itself and the controller verifies that collections match. This is documented behavior, not an incidental implementation bug ([pytest-xdist: how it works](https://pytest-xdist.readthedocs.io/en/stable/how-it-works.html)). High-scope fixtures similarly execute once per worker unless the project implements additional cross-process coordination ([pytest-xdist: making session fixtures execute only once](https://pytest-xdist.readthedocs.io/en/stable/how-to.html)).

Compared directionally with the August baseline research, the suite has grown rapidly:

| Metric | August baseline | Current record | Change |
|---|---:|---:|---:|
| Test nodes | 27,988 | 38,700 | +38% |
| Attributed files | 2,470 | 3,516 | +42% |
| Sum of file wall time | 3,719 s | 6,407 s | +72% |
| Textual app starts | 2,148 | 3,684 | +71% |
| Ace page entries | 506 | 710 | +40% |

The comparison is not perfectly apples-to-apples because the current run has cost instrumentation, but the direction and scale are unambiguous: test growth is outrunning earlier optimizations.

### Where time is going

The current cost attribution names these dominant operations:

| Operation | Calls | Inclusive attributed time |
|---|---:|---:|
| Ace page entry | 710 | 1,597.8 s |
| Textual `run_test` entry | 3,684 | 1,359.0 s |
| Ace pilot settling | 6,841 | 593.9 s |
| `subprocess.run` | 41,056 | 574.1 s |
| Pilot pause delay | 13,751 | 532.2 s |
| Parser creation | 1,861 | 92.3 s |
| YAML loading | 56,006 | 57.8 s |

These timers can be nested and therefore must not be summed as independent savings. They nevertheless locate the highest-leverage paths. Static searches reinforce the result: the tests contain about 2,330 `.run_test(...)` calls, 3,305 `pilot.pause(...)` calls, and hundreds of explicit subprocess call sites.

Textual’s testing API creates an application and returns a `Pilot` from `run_test`; `Pilot.pause()` without a delay waits for pending messages to be processed ([Textual testing guide](https://textual.textualize.io/guide/testing/), [Pilot API](https://textual.textualize.io/api/pilot/)). This is correct but broad synchronization. Repeating it after actions whose completion can be observed through a narrower state transition turns scheduling and unrelated background work into test latency.

The slow-file distribution is concentrated enough to support targeted work. Of the retained historical durations, the top 100 files account for about 55.6% of retained time. After accounting for unmeasured files with the timing table’s default estimate, those top 100 still represent about 47.8% of predicted work. Halving their cost would therefore reduce predicted total work by roughly 24%, before touching thousands of small tests.

Representative hotspots show distinct, actionable causes:

- `tests/ace/tui/widgets/test_vim_normal_key_containment.py` takes about 136 seconds for 45 nodes. It is currently the only actual module listed in the Ace page-group manifest. Shared app boot appears to be working there—only one page entry is recorded—but pilot settling, pauses, and repeated YAML loads remain substantial. This shows both that boot amortization works and that waits become the next bottleneck once boot is shared.
- `tests/test_check_feature_flags_tool_run.py` takes about 86 seconds for seven nodes and invokes full repository static validation twice. That work overlaps checks already performed by the lint lane and scales with the size of the repository rather than the behavior under test.
- `tests/test_contract_manifest.py` takes about 46 seconds, almost all idle/subprocess time, because it invokes another pytest collection operation. Collection is already happening in the outer pytest session.
- `tests/test_procs_service.py` takes about 52 seconds, with about 51 seconds attributed as idle time, indicating a synchronization or timeout-oriented target rather than useful computation.

An earlier app-boot amortization plan introduced the Ace page-group helper and intended to migrate multiple high-cost files. The current manifest contains only one test module. The mechanism is promising, but its highest-value rollout remains incomplete.

### Sharding and parallelism

The existing timing table is useful but partially stale. It retains measurements for about 808 currently existing files, while the discovered suite has 3,952 files. The remaining files receive a default duration. Even so, the current eight-way plan is remarkably even: each outer shard contains roughly 491–496 files and is estimated at about 1,030 seconds of serial file time.

The CI architecture then starts pytest-xdist inside each of those outer shards. This creates two layers of scheduling and causes each xdist worker within a shard to collect that shard’s entire test set. More workers can reduce wall time while increasing total collection, memory, process startup, shared-service contention, and fixture duplication. It also works against app reuse unless all tests sharing an app instance stay within the same worker. Xdist’s `loadfile` and `loadscope` modes provide useful affinity guarantees, while work stealing is designed for unequal durations and can improve fixture reuse ([pytest-xdist distribution modes](https://pytest-xdist.readthedocs.io/en/stable/distribution.html)). Neither mode removes per-worker collection.

The clean architectural alternative is to promote the already-existing outer file scheduler into the primary parallelism boundary: partition the full file list into *W* historical-time-balanced sets and run *W* plain `pytest -n0` processes. Each process collects only its own explicit files, and all tests from one file stay together. This is not necessarily faster in every suite, so it should be prototyped and measured. SASE’s unusually high collection memory and file-scoped TUI setup make it a particularly strong candidate.

### Scoped selection is not yet a safe speed foundation

The selection-health record contains 84 scoped runs and 50 full comparisons. Its results are mixed:

| Metric | Result |
|---|---:|
| Median selected nodes | 638 of 3,799 (16.8%) |
| Median scoped duration | 1,175 s (19.6 min) |
| 90th-percentile scoped duration | 2,207 s (36.8 min) |
| Escalation rate | 54.8% |
| Observed false negatives | 19 |
| Runs consulting coverage contexts | 42 |
| Runs with a usable context baseline | 0 |

The selector demonstrably saves worker-seconds, but it is neither consistently fast nor currently strong enough to be authoritative. All 42 runs that consulted coverage context lacked a baseline, and the false negatives cluster around a few integration-heavy areas. A tool that returns the first result quickly can be valuable even when it is not trusted to approve a merge; a tool with observed false negatives should not replace the exhaustive anchor.

Coverage contexts are still worth repairing. They answer which tests executed particular lines, which is exactly the evidence a change-based selector needs ([coverage.py measurement contexts](https://coverage.readthedocs.io/en/7.12.0/contexts.html)). They should be treated as a reliability prerequisite for future selection, not as the first performance project. Adding context edges can initially widen selections, so the immediate benefit is safety and diagnosis rather than guaranteed speed.

### CI feedback and signal quality

Recent GitHub Actions history was sampled on 2026-09-12:

- The last 99 completed master-gate runs all failed. Their median duration was about 7.3 minutes and the 90th percentile about 11.2 minutes.
- The last 50 completed scheduled full workflows all failed. Their median duration was about 99.4 minutes.
- In one recent full workflow, coverage and Python 3.12 test lanes each ran for about 54–56 minutes; the cost lane was cancelled near 90 minutes; the Python 3.14 fast lane ran about 23 minutes; and the overall workflow lasted about 101 minutes.
- A recent master gate with a Rust-core cache hit completed in about seven minutes, with individual test shards around five to seven minutes. A recent cache miss stretched the gate to about 22 minutes because the core build took over 13 minutes.

The latest sampled master failures include a deterministic environment problem: tests that create temporary Git repositories cannot commit because Git author identity is unset. This is a signal-integrity issue, not a performance result. Restoring a green baseline is a prerequisite to deciding whether any optimization preserves correctness.

Pushes in the sample also arrive in bursts only a few minutes apart, while the never-cancelled gate has a 7.3-minute median and can take much longer on a cache miss. That satisfies the spirit of the accepted decision’s explicit reopening condition: the fast gate no longer reliably fits commit cadence. It supports a deliberate review of batching or merge-queue admission after the suite is green. It does not by itself support cancelling older runs, because the current design intentionally values per-SHA evidence.

GitHub Actions can limit matrix concurrency with `max-parallel`, and dependency caching can avoid repeated downloads and rebuilds on clean runners ([workflow matrix syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax), [dependency caching](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)). SASE already has a host-capacity constraint, however. Increasing matrix concurrency or runner size would shift resource cost rather than remove work and could worsen the suite’s known contention sensitivity.

## Options considered

### 1. Add more workers or larger runners

This is the lowest-effort way to reduce an isolated run’s wall time, but the evidence argues against it as the main strategy. Collection, memory, fixtures, subprocesses, and shared-service pressure are duplicated with worker count. The project already regulates worker tokens because contention changes behavior. More hardware also does nothing for the total compute consumed by the scheduled matrix.

**Verdict:** useful only as a temporary capacity measure, not the architectural answer.

### 2. Make scoped selection more aggressive

The potential payoff is large because a median selected set is only 16.8% of the inventory. The current selection-health record nevertheless contains 19 false negatives, no usable context baseline in 42 context-dependent runs, and a 19.6-minute median. More aggressive pruning now would exchange correctness for apparent speed.

**Verdict:** keep it as an advisory/first-result lane while rebuilding its evidence; do not make it the merge authority yet.

### 3. Split more CI lanes or cancel superseded work

Splitting improves visibility and can reduce critical-path time when capacity is plentiful, but it can increase duplicate setup and queue contention. Cancelling superseded runs reduces spend but conflicts with the accepted per-SHA evidence policy. The decision’s reopening condition appears met, so batching or merge-queue admission is worth a separate review once signal is green.

**Verdict:** secondary scheduling work, after test cost and signal quality.

### 4. Adopt Bazel or another hermetic build/test system

Hermetic actions enable safe caching and parallelism when inputs and outputs are fully declared ([Bazel hermeticity](https://bazel.build/concepts/hermeticity)). SASE’s tests exercise temporary Git repositories, processes, filesystem state, terminals, Textual event loops, and global configuration. Converting enough of that surface to hermetic targets would be a major migration, and most of the measured hot operations would remain expensive inside those targets.

**Verdict:** disproportionate migration cost for the current bottlenecks. Reconsider only if cross-language build reproducibility independently demands it.

### 5. Remove repeated work and change the process boundary

This option attacks CPU, idle time, memory, and wall time simultaneously without selecting fewer tests. It extends mechanisms the repository already has: cost attribution, historical file timings, Ace page groups, explicit isolation checks, and worker-token control.

**Verdict:** best risk-adjusted path.

## Proposed implementation sequence

### Phase 0: restore a trustworthy baseline

1. Fix the Git identity/environment defect in temporary-repository tests and any other deterministic failures.
2. Capture several green baselines at a fixed worker budget on the same host class. Record end-to-end wall time, aggregate CPU, peak RSS, collection time, top-file timings, and flake outcomes.
3. Separate correctness timing from diagnostic timing. The expensive cost profiler should run in a dedicated or scheduled lane unless a change touches the runner or budgets; the same Python-version test inventory can still execute in fast mode on every required gate.

This phase is intentionally first. A red baseline makes equivalence claims weak and performance distributions noisy.

### Phase 1: reduce the dominant test and harness costs

1. **Complete app-lifecycle amortization by cost rank.** Migrate the highest-cost compatible TUI modules into the Ace page-group mechanism, not a broad undifferentiated batch. Preserve clean state with an explicit reset contract between tests. Run shared mode by default and retain an isolated-equivalence lane; changes to the grouping helper or lifecycle code should trigger full isolation coverage.
2. **Replace broad waits with condition-based synchronization.** For the top 100 files, classify each `pilot.pause()` or settle call by the state it protects. Add helpers that wait for the relevant message, widget state, task completion, or model generation, with a bounded timeout and a useful failure diagnostic. Keep broad settling only when the behavior under test is the event loop becoming quiescent.
3. **Stop launching whole-repository checks inside ordinary tests.** Refactor `test_check_feature_flags_tool_run` into small synthetic-fixture tests for tool behavior, while retaining one outer validation lane that checks the real repository. This preserves both semantics without scanning the same tree repeatedly.
4. **Eliminate nested pytest collection.** Move contract-manifest validation into the outer session’s collection plugin or compare against the already-collected item set. Retain one focused integration test for the standalone command if that command is a public contract.
5. **Use in-process calls where the process boundary is irrelevant.** Keep subprocess tests when isolation, CLI parsing, signals, environment inheritance, or exit behavior is the assertion. Otherwise call the underlying API with isolated state. This distinction preserves architectural coverage while removing thousands of process starts.
6. **Cache immutable parse products within an appropriate scope.** Parser construction and repeated YAML reads are smaller than app lifecycle costs but occur frequently. Module/session fixtures are a standard pytest mechanism for sharing expensive setup ([pytest fixture scopes](https://docs.pytest.org/en/stable/how-to/fixtures.html)). Only cache objects proven immutable or clone/reset them explicitly.

Work should be ordered by measured file contribution. Because the top 100 files account for about half of predicted work, this produces feedback sooner and gives a clear stop condition.

### Phase 2: prototype file-process sharding as the primary local executor

Build an experimental runner that:

1. performs one authoritative collection to enumerate node IDs and map them to files;
2. uses the existing historical-duration table to assign files to *W* balanced bins with longest-processing-time-first scheduling;
3. launches *W* isolated `pytest -n0 <explicit file list>` processes under the existing shared worker-token gate;
4. provides each process an isolated temp directory, home/config surface, coverage data file, JUnit path, and cost-record path;
5. merges results and proves that the union of executed node IDs exactly equals the authoritative collection, with no duplicates;
6. preserves deterministic reproduction by printing the exact file assignment and random/ordering inputs.

Compare this against xdist at the same worker-token budget. Promote it only if repeated green runs show a material gain—suggested thresholds are at least 20% lower wall time or 30% lower collection/RSS—without new flakes or changed node coverage. A lower-risk stepping stone is `--dist loadfile` for TUI-heavy subsets, but it retains xdist’s repeated collection and should not be mistaken for the final optimization.

### Phase 3: shorten the human feedback path without weakening the landing gate

1. Keep scoped selection as a quick, non-authoritative first result. Supply fresh coverage contexts automatically, expose why every test was selected, and treat missing context as a visible health failure rather than silent normal behavior.
2. Triage the existing 19 false negatives by subsystem and add selector regression fixtures. Do not promote selection to merge authority until meaningful comparisons show zero unexplained false negatives and context availability is consistently high.
3. Preserve one exhaustive fast-suite anchor before merge/landing. Move orthogonal dimensions—extra Python versions, coverage attribution, visual tests, contention, and heavy performance profiling—to scheduled or change-triggered lanes only where historical evidence proves that triggering is safe.
4. After the gate is green and cheaper, re-evaluate per-SHA scheduling using measured arrival rate and gate service time. Consider merge-queue batching or an explicitly approved newest-SHA policy, but record the reliability tradeoff because it changes the existing completion evidence model.

## Guardrails and success criteria

Performance work on a test system needs stronger correctness checks than ordinary refactoring. The following should gate rollout:

- The collected node-ID set is identical before and after each executor change.
- No tests, assertions, or meaningful environments are deleted, skipped, or reclassified merely to improve timing.
- Shared app groups pass their isolated-equivalence lane, including under contention.
- New synchronization helpers have bounded timeouts and diagnose the unmet condition.
- No statistically meaningful increase in flakes across repeated normal and contention runs.
- The required exhaustive path remains green.
- Selector context availability exceeds 95%, and unexplained false negatives are zero over a representative comparison window before it gains authority.
- Timing is evaluated at fixed worker tokens on the same host class, using median and 90th percentile rather than a single best run.

Useful initial targets are:

- halve the aggregate cost of the current top 100 files;
- reduce total attributed file wall time by at least 35%;
- reduce collection to at most 20 seconds per worker-equivalent;
- keep peak worker/process RSS below 700 MiB under the standard budget;
- deliver a local first-result lane with a 60-second median and three-minute 90th percentile for ordinary changes;
- restore a consistently green master gate whose median service time fits the observed commit cadence.

Absolute thresholds should be complemented by relative regression budgets because host contention is real. The cost system should distinguish functional failure, performance regression, and infrastructure contention so that a slow environment does not turn the correctness signal red without explanation.

## Recommended solution

Adopt a **measure-first cost-removal program with timing-balanced file-process sharding**, while retaining one exhaustive required gate. First restore green CI and capture a fixed-budget baseline. Then finish Ace/Textual lifecycle sharing in the costliest compatible modules, replace broad pilot settling with observable condition barriers, and remove nested whole-repository subprocess and collection work. In parallel, prototype *W* balanced plain pytest processes over disjoint file lists and require exact node-set equivalence before replacing xdist; this directly attacks repeated collection, memory, and fixture duplication without running fewer tests. Keep scoped selection advisory until coverage contexts are reliable and its false negatives are eliminated, and move non-functional cost instrumentation off the critical PR path. This combination offers the largest credible reduction in both developer latency and total resource use without weakening the architecture’s correctness guarantees.
