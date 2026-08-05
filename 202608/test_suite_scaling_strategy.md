---
create_time: 2026-08-05
updated_time: 2026-08-05
status: research
---

# Scaling SASE's Test Suite Without Making Parallel Agents Fight

**Research question:** SASE's test suite is growing quickly and mandatory full-suite checks are increasingly expensive,
especially when several agents run them concurrently. What should change—in the test runner, agent workflow, CI, build
architecture, or repository boundaries—to restore fast feedback without hiding regressions?

**Scope:** Local inspection and measurement of the SASE checkout at commit `865281be4` on 2026-08-05, plus current
official documentation for pytest-xdist, pytest-testmon, Pants, and Bazel. The controlled full-suite benchmark used
Python 3.14.3, pytest 9.1.1, pytest-xdist 3.8.0, four workers, and excluded the visual and explicitly slow markers. That
makes it a useful lower-bound for the mandatory `just check`, which currently includes visual tests as well.

## Bottom line

This is primarily a **verification-scope and cache-reuse problem**, not a worker-count problem.

SASE currently asks every agent that changes a file to run essentially the same exhaustive check. Each run collects
25,500 default nonvisual tests; xdist repeats full collection in every worker; the host-global scheduler greedily gives
nearly all capacity to the first run; almost every test is in the nominally fast lane; and results are not reused across
ephemeral workspaces. The CI matrix then runs the same nonvisual universe on three Python versions.

The measured four-worker nonvisual run took **14:09 wall time** and still produced seven load/environment-sensitive
failures. A hot full collection alone takes about 15 seconds internally; a cold collection took 45.65 seconds. Tuning
xdist can improve fairness, but no worker setting removes the duplicated work.

The best path is a two-speed verification architecture:

1. Phase agents run changed/affected tests plus a small always-run safety set, normally with one or two processes.
2. A land/integration agent and CI retain exhaustive validation.
3. Test execution is partitioned before pytest starts and cached at test-file or small-batch granularity, so each pytest
   process collects only its assigned files and unchanged results are shared across workspaces.
4. Slow, visual, performance, and system tests become explicit lanes instead of living in the default fast selection.

I recommend a short pytest-testmon bridge while piloting Pants as the strategic test orchestrator. I do **not**
recommend splitting the repository yet: ACE is too coupled to the rest of the Python package, and a split would move
cost into cross-repository releases and integration checks without fixing duplicate execution.

## 1. Measured state

### 1.1 Suite size

| Metric                               |   Current value | Implication                                                                                 |
| ------------------------------------ | --------------: | ------------------------------------------------------------------------------------------- |
| Collected tests, all markers         |          25,915 | The suite is already in build-system territory, not small-project territory.                |
| Default nonvisual/non-slow selection |  25,500 (98.4%) | The default lane is effectively the whole suite.                                            |
| Tests marked `slow`                  |       8 (0.03%) | `slow` is not functioning as a useful execution class.                                      |
| Tests marked `visual`                |             407 | These are separately identifiable, but `just test`/`just check` intentionally include them. |
| Python test files                    |           2,697 | Collection/import overhead and test-file scheduling now matter materially.                  |
| Python test lines                    |         641,462 | Test code is larger than production Python by line count.                                   |
| Python source files / lines          | 2,749 / 605,972 | Source and test graphs are both large enough to benefit from dependency-aware execution.    |
| Tracked `tests/` size                |       69.59 MiB | Includes 406 tracked PNGs; the working directory was 157 MiB after generated caches.        |

The directory split is broad rather than dominated by one extractable component:

| Collected area               |  Tests | Test-bearing files |
| ---------------------------- | -----: | -----------------: |
| `tests/ace/tui/visual/` path |    420 |                108 |
| Other `tests/ace/tui/`       |  7,746 |                721 |
| `tests/test_bead/`           |  1,353 |                114 |
| `tests/main/`                |  1,171 |                120 |
| Everything else              | 15,225 |              1,338 |

ACE/TUI is large, but extracting it would still leave more than 17,000 tests in this repository. A repo split is not a
substitute for test selection and caching.

### 1.2 Growth rate

The growth is recent and steep. Counts below are static Python test definitions, so parametrization makes actual
collection larger.

| Snapshot   | Python test files | Test definitions | Tracked test size |
| ---------- | ----------------: | ---------------: | ----------------: |
| 2026-03-31 |               327 |            3,384 |          1.96 MiB |
| 2026-04-30 |               659 |            6,584 |          4.37 MiB |
| 2026-05-31 |             1,088 |            9,837 |         12.78 MiB |
| 2026-06-30 |             1,551 |           14,262 |         28.60 MiB |
| 2026-07-31 |             2,604 |           22,241 |         67.72 MiB |
| 2026-08-05 |             2,697 |           22,904 |         69.59 MiB |

In a little over four months, Python test files grew **8.2×**, test definitions **6.8×**, and tracked test bytes
**35.5×**. Any mitigation that only wins a fixed percentage will be overtaken quickly unless the verification model also
changes.

### 1.3 Collection and execution benchmark

Controlled measurements on the same checkout:

| Measurement                                         |                                                                 Result |
| --------------------------------------------------- | ---------------------------------------------------------------------: |
| Cold serial collection, default nonvisual selection |                                                           45.65 s wall |
| Hot serial collection, same selection               | 14.94 s reported by pytest; about 20 s wall through the shell pipeline |
| Four-worker nonvisual run                           |                                25,500 items; 14:07 pytest / 14:09 wall |
| Aggregate CPU utilization                           |                                     187% (about 1.87 cores on average) |
| Outcome                                             |                        25,487 passed, 7 failed, 7 skipped, 69 warnings |

The low average CPU utilization means the workload includes considerable filesystem, subprocess, event-loop, lock, and
teardown waiting. More processes can hide some waits, but oversubscription also makes timing-sensitive tests fail and
does not eliminate repeated collection.

The three slowest default-lane tests were:

| Test                                                            | Full-run call time |                                                    Focused serial call time |
| --------------------------------------------------------------- | -----------------: | --------------------------------------------------------------------------: |
| `test_save_dismissed_bundle_is_fast_with_many_existing_bundles` |            64.09 s |                                                                     52.33 s |
| `test_concurrent_bead_mutations_wait_past_the_old_lock_timeout` |    54.83 s, failed | Known to pass near 3–6 s alone in prior reports; reproduced here under load |
| `test_bundle_no_limit`                                          |            30.24 s |                                                                     27.92 s |

Three focused dismissed-bundle tests took 88.62 seconds serially. Their intent does not require populating the archive
by calling the production save path thousands of times; direct fixture construction could preserve the assertion while
removing most setup cost. Until optimized, these are performance/scale tests and should not be in the default fast lane.

### 1.4 Current concurrency policy is intentionally unfair

`tools/run_pytest` uses a host-global token pool, which is the right idea, but the automatic lease is greedy:

- default floor: 4 workers;
- default ceiling: up to 28;
- current computed host budget during this audit: 25;
- current automatic range: 4–21 workers;
- acquisition timeout: 45 minutes.

With an empty 25-token pool, the first full run takes 21 tokens, the second gets the remaining 4, and a third cannot
reach its floor and waits. This favors one workspace's latency over aggregate agent throughput. The exact budget changes
with available memory, but the structural behavior remains: the first run is allowed to consume `budget - floor`,
leaving room for only one minimum-size follower.

This explains why adding the gate prevented host collapse but did not make parallel-agent checks pleasant.

### 1.5 xdist amplifies collection

pytest-xdist's controller does not collect once and serialize tests. **Every worker performs a full collection**, sends
its IDs to the controller, and must agree on the resulting order. This is explicit in the
[xdist execution model](https://pytest-xdist.readthedocs.io/en/stable/how-it-works.html).

For this suite:

- 4 workers construct about 102,000 test items;
- the current 21-worker automatic grant constructs about 535,500;
- the configured 28-worker ceiling would construct about 714,000.

`worksteal` can improve execution balance, but it cannot change that collection multiplier. The decisive optimization is
to select or partition test files **before** pytest/xdist collection, then use modest concurrency inside each partition
only when beneficial.

### 1.6 CI repeats the same universe

The current GitHub Actions `test` matrix runs the full nonvisual suite on Python 3.12, 3.13, and 3.14. That is about
76,500 test executions per commit before the dedicated visual job and performance floors. The 3.12 leg additionally
collects coverage.

Testing all supported interpreters is valuable. The waste is that every unchanged test runs again rather than receiving
a content-addressed cache hit, and PRs do not distinguish affected code from unaffected code.

### 1.7 Baseline failures show non-hermetic behavior

The benchmark failures were not caused by a code edit:

- two xprompt-use tests deterministically included the ambient `research_swarm` xprompt despite patching their expected
  catalog;
- four hook-wrapper tests failed only in the full parallel run and passed immediately as a focused file (6/6);
- the bead mutation lock regression exhausted its 12-second deadline under four-worker load;
- warnings reported many tests changing the process CWD to a subsequently deleted directory, unawaited Textual timer
  coroutines, and multithreaded-process `fork()` usage.

These are not only correctness issues. A safe result cache needs declared inputs and isolated outputs. The failures show
which tests must initially remain in a non-cacheable system lane and what must be hermeticized before more aggressive
reuse.

## 2. Diagnosis

The current system has five multiplicative costs:

1. **Every agent owns exhaustive verification.** The project instruction requires `just check` after nearly any source
   change. In an epic with several phase agents, mostly disjoint changes trigger several full suites before the land
   agent runs another integrated suite.
2. **Almost all tests are one lane.** Only eight tests carry `slow`, while default tests include 30–60 second scale and
   lock-contention cases, TUI pilots, subprocess tests, repository-wide audits, and PNG rendering.
3. **xdist repeats full collection.** Increasing worker count attacks execution time while multiplying import and
   collection work.
4. **The token scheduler is greedy and static.** It cannot distinguish a ten-test check from a 25,500-test check and
   does not rebalance when additional agents arrive.
5. **No cross-workspace test-result cache exists.** Ephemeral clones share dependencies and a worker pool, but not the
   expensive fact that an unchanged test with unchanged dependencies already passed.

This also explains the flake history. A single full run is a stress test of filesystem timing, locks, event loops, and
subprocess cleanup. Repeating that stress test concurrently in multiple workspaces produces more noise, retries, and
task-triage work, which consumes the time gained by parallel agents.

## 3. What success should mean

A migration should be judged against explicit service levels rather than “pytest feels faster”:

| Workflow                                     | Target                                                                   |
| -------------------------------------------- | ------------------------------------------------------------------------ |
| Focused edit/test loop                       | under 30 s p50; under 90 s p95                                           |
| Phase-agent required check                   | under 3 min p95                                                          |
| Token admission for a scoped check           | under 10 s p95                                                           |
| Cold exhaustive nonvisual run on this host   | under 10 min with bounded resources                                      |
| Warm exhaustive run with no relevant changes | under 2 min, mostly cache hits                                           |
| Full-suite flake rate                        | below 0.5% of runs, then drive toward zero                               |
| Affected-test false negatives                | zero in a shadow-validation period before making selection authoritative |

The key metric is **time to trustworthy feedback per change**, not the wall time of one maximally parallel pytest
process.

## 4. Options evaluated

| Option                                      | Benefit                                                                                                                          | Limitation                                                                                                                              | Verdict                                                            |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Tune xdist and the token gate               | Fast to implement; improves fairness and host stability                                                                          | Still collects and executes the same suite; no reuse                                                                                    | Do immediately, but only as containment                            |
| Add real test lanes                         | Removes obvious 30–60 s scale/visual/system work from normal loops                                                               | Does not know which ordinary unit tests a change affects                                                                                | Required foundation                                                |
| pytest-testmon affected selection           | Small migration; learns test→executed-code dependencies using Coverage.py; supports xdist                                        | Needs a trustworthy baseline DB; still pays pytest collection; dynamic resources, subprocesses, and Rust-only changes need safety rules | Recommended bridge/pilot                                           |
| Pre-shard pytest by file and duration       | Avoids full collection in every worker; works with current tests                                                                 | A bespoke scheduler/cache tends to grow into a build system                                                                             | Useful fallback or transitional runner, not the strategic endpoint |
| Pants                                       | Python dependency inference, changed-target selection, fine-grained test caching, bounded process scheduling, local/remote cache | Substantial migration; hermetic sandboxes expose current ambient-input assumptions; per-file fixture startup needs batching             | Recommended strategic pilot                                        |
| Bazel                                       | Mature sharding, hermetic actions, remote cache/execution                                                                        | More BUILD/rule integration work for this Python/pytest-heavy repo; no advantage over Pants for the first migration                     | Keep as an alternative if Pants fails                              |
| Split the repository now                    | Smaller per-repo collections if boundaries are truly independent                                                                 | Current boundaries are not independent; cross-repo CI/versioning replaces local test cost                                               | Defer                                                              |
| Move appropriate logic/tests to `sase-core` | Aligns with the existing backend boundary and moves domain tests beside shared Rust behavior                                     | Does not by itself prevent every Python workspace from running every remaining Python test                                              | Continue for architectural reasons, not as the primary speed fix   |

### 4.1 Why testmon is a bridge, not the destination

[pytest-testmon](https://www.testmon.org/) records which executed code each test depends on and selects tests whose
dependencies changed. It is an excellent low-cost way to test the affected-selection hypothesis with this suite, and
current testmon supports pytest-xdist.

It has three important limits here:

1. Selection happens within pytest, so the roughly 15-second hot full collection remains.
2. Ephemeral workspaces need a baseline `.testmondata` copied from a known main commit and keyed by Python version,
   pytest/plugin versions, platform, and Rust-core revision. Blindly sharing one writable database would introduce a new
   concurrency hazard.
3. Coverage cannot safely infer changes hidden behind config discovery, repository-wide scans, shell subprocesses,
   generated assets, or a rebuilt Rust implementation behind an unchanged Python call site.

Use it for a shadow pilot: run selected tests for agents, then compare against scheduled exhaustive runs for at least 30
representative changes. Treat changes to `conftest.py`, pytest configuration, lockfiles, test helpers, default config,
the Rust wheel/core SHA, repository-audit code, or test-selection code as “run broad.” Always run a small
contract/system safety set.

### 4.2 Why Pants is a good strategic fit

Pants directly addresses the missing primitives:

- By default it models each Python test file as a target and can run only tests whose dependencies changed; unchanged
  test results remain cached. See the official
  [Pants pytest test goal](https://www.pantsbuild.org/stable/docs/python/goals/test).
- It parses Python imports for dependency inference and allows explicit dependencies where inference is insufficient.
  See [Python dependency inference](https://www.pantsbuild.org/stable/reference/subsystems/python-infer).
- It supports `--changed-since` plus transitive dependents, which maps naturally to a SASE workspace base commit. See
  [advanced target selection](https://www.pantsbuild.org/stable/docs/using-pants/advanced-target-selection).
- It has a shared local process cache and supports REAPI remote caching/execution for reuse between CI jobs and hosts.
  See [remote caching and execution](https://www.pantsbuild.org/stable/docs/using-pants/remote-caching-and-execution).
- It bounds total scheduled pytest concurrency and supports an execution-slot variable for tests that must name external
  resources uniquely. Its [pytest integration](https://www.pantsbuild.org/stable/docs/python/goals/test) also supports
  batching and xdist within a batch.
- Current Pants 2.32 knows Python 3.14 and permits a custom pytest tool resolve, so SASE is not forced to downgrade from
  pytest 9 solely to pilot it.

Pants's hermetic model is also the migration's main cost. SASE tests inspect repo files, launch git and shell commands,
depend on linked repos and a locally built Rust wheel, and sometimes observe ambient SASE configuration. These inputs
must be declared or those tests must remain explicitly non-cacheable/system-scoped. That work is desirable because the
benchmark proves the existing assumptions already cause false failures.

Do not begin by converting all 2,697 test files. Pilot 200–400 pure Python tests with no TUI, subprocess,
repository-wide scan, or ambient configuration dependency. Use small duration-balanced batches so fixture startup is
amortized without making one file invalidate hundreds of cached results. Keep `just test` authoritative during the
pilot.

### 4.3 Why not split the repo now

A good repository split follows a stable API and release boundary. The current code has the opposite shape:

- `src/sase/ace` contains 1,265 Python files and imports broadly from core, xprompt, agent, config, bead, axe,
  providers, workflows, history, and other subsystems;
- 74 non-ACE source files directly import `sase.ace`;
- many of those imports expose presentation/domain types in the wrong direction.

Extracting ACE today would require coordinated changes, compatibility releases, and cross-repository integration tests.
Agents touching a shared model would run suites in two repos rather than one. The split becomes attractive only after:

1. shared backend/domain behavior is moved behind the existing Rust-core or stable Python facade boundary;
2. non-ACE imports of `sase.ace` reach zero;
3. an ACE change rarely requires a core/CLI change in the same commit;
4. ACE can carry an independent release cadence and compatibility contract.

Pants gives most of the test-scaling benefit of a monorepo split without forcing a product/release split. Use its target
graph to expose and reduce coupling first; reconsider `sase-ace` afterward.

## 5. Proposed migration

### Phase 0: Stop the immediate waste (days)

1. Create explicit lanes:
   - `unit`: hermetic, deterministic, normally below 1 second per test;
   - `integration`: filesystem/git/subprocess or multi-module tests;
   - `system`: ambient services/config, process lifecycle, real terminal, and cross-repo behavior;
   - `visual`;
   - `performance`/`soak`.
2. Make `just test` mean unit + bounded integration. Keep `just test-full` or `just check-full` exhaustive. Preserve
   visual/system/performance coverage in dedicated commands and CI.
3. Rewrite archive-scale test setup to materialize existing fixture files directly. Mark any remaining 10+ second test
   `performance`/`slow`. Add a CI report, then a budget gate, for unit tests exceeding 2 seconds.
4. Change the token scheduler from greedy leases to job classes:
   - targeted/affected run: 1–2 tokens;
   - exhaustive local run: cap near 8 tokens on this host;
   - explicit contention/visual harness: dedicated opt-in class. Admit small jobs promptly and use FIFO fairness. Do not
     start xdist for a tiny path selection.
5. Record per-test-file durations and collection time as build artifacts. A scheduler cannot be improved rationally
   without stable timing data.

This phase does not reduce correctness coverage; it stops paying system/performance costs in every inner loop and lets
more than two agent checks make progress.

### Phase 1: Introduce an agent fast path (one to two weeks)

Add `just check-agent` with these semantics:

1. Resolve the workspace's base/integration commit.
2. Run formatting/lint checks appropriate to changed files.
3. Use a read-only copy of a mainline testmon baseline to select affected tests.
4. Add the always-run contract set and any tests directly changed by the agent.
5. Run selected tests serially or with at most two workers.
6. Emit a machine-readable selection manifest: changed files, selected tests, broadening rules, cache/baseline identity,
   duration, and outcome.

During shadow mode, phase agents may rely on `check-agent` for feedback, while the land agent/CI still runs the full
suite. Compare every later full failure against earlier selection. Make the fast path mandatory only after the false
negative rate is zero across at least 30 varied changes.

Then update the agent policy: phase agents run `just check-agent`; the land/integration agent runs `just check-full` on
the combined tree. This removes the largest duplication directly.

### Phase 2: Pilot Pants and shared result caching (two to six weeks)

1. Add Pants alongside the current uv/Justfile workflow; do not replace packaging or developer setup initially.
2. Generate targets for a pure-Python vertical slice and validate import inference with `pants dependencies`.
3. Configure the exact pytest/plugin versions through a custom tool resolve. Key the Rust extension input by wheel
   content and core commit SHA.
4. Model repo files, fixtures, and generated assets as explicit dependencies. Tag tests that cannot yet be hermetic as
   `system` and disable caching for them.
5. Tune small-batch compatibility using observed file durations. Avoid both extremes: 2,400 independent pytest startups
   on every cold run and one giant batch that invalidates the whole suite.
6. Point all workspace clones at the same host-local Pants cache. Add a CI REAPI cache only after local correctness and
   hit rates are demonstrated.
7. Compare:
   - cold full time;
   - no-change warm time;
   - one-leaf-change time;
   - one-shared-module-change time;
   - cache hit ratio;
   - selected target count;
   - failures missed by dependency inference.

Adoption gate: representative phase-agent checks should be below 3 minutes p95, warm unchanged tests should achieve at
least an 80% action-cache hit rate, and no shadow full run may find an unselected regression.

If Pants cannot accommodate the system-heavy tests without excessive declarations, retain it for unit/integration
targets and keep a legacy pytest system lane. If the pilot itself fails the value test, implement a much narrower
duration-balanced file-shard runner—but do not build a bespoke remote cache and dependency graph unless necessary.

### Phase 3: Change CI topology

Once affected selection/cache correctness is trusted:

1. On PRs, run all affected targets on Python 3.12, 3.13, and 3.14, plus one exhaustive primary-interpreter lane. With a
   shared action cache, `test ::` may remain the user-facing command while unchanged targets resolve as cache hits.
2. Run the full three-version matrix on master, nightly, and release boundaries. This preserves compatibility confidence
   without making every PR rediscover unchanged results.
3. Run visual tests on PRs when ACE/rendering/config/assets dependencies change; retain a scheduled/full-master visual
   sweep as a safety net.
4. Keep system, performance, soak, and terminal lanes separate with explicit timeouts and failure ownership.
5. Deduplicate identical CI requests by tree/config/core cache key, not merely by branch concurrency cancellation.

### Phase 4: Improve boundaries, then reconsider a repo split

Use the dependency graph to enforce architecture:

- non-ACE code must not import `sase.ace`;
- shared backend/domain behavior follows the existing Rust-core boundary;
- UI targets depend on stable facades, not internal orchestration modules;
- plugins and linked repos expose contract tests at their boundaries.

When those rules hold, measure how often changes cross the proposed `sase`/`sase-ace` line. Split only if independent
ownership/release cadence is valuable in its own right. Test speed alone is not enough reason.

## 6. Safety rules for affected selection and caching

Affected testing is safe only if broadening is conservative:

- Run broad when `pyproject.toml`, `uv.lock`, pytest configuration/plugins, `conftest.py`, shared test helpers, default
  config, code generators, package metadata, or the Rust extension/core revision changes.
- Always include tests whose files changed, even if the dependency engine does not select them.
- Maintain an explicit repository-audit/contract set for tests that scan strings, paths, bindings, symbols, command
  catalogs, schemas, or packaging metadata.
- Do not cache tests that read undeclared home configuration, external repos, the network, time, host process state, or
  shared directories until those inputs are isolated.
- Cache keys must include Python implementation/version, OS/architecture, dependency and tool lock content, pytest
  options/plugins, renderer/font stack for visual tests, relevant environment values, Rust wheel content/core SHA, test
  source, and transitive declared inputs.
- Sample exhaustive shadow runs even after rollout. Selection health is a production metric.
- A cache hit is valid evidence only when the action was hermetic; “passed once in some workspace” is not a cache key.

The current failures are useful migration tests: ambient `research_swarm` must not enter a hermetic xprompt test, hook
wrapper tests must not inherit a broken shared temp/output state, and lock tests must either own unique resources or be
scheduled as contention-sensitive system tests.

## 7. External evidence

- pytest-xdist documents that each worker performs full collection and that high-level fixtures execute once per worker,
  not once per overall controller run:
  [how xdist works](https://pytest-xdist.readthedocs.io/en/stable/how-it-works.html) and
  [xdist how-tos](https://pytest-xdist.readthedocs.io/en/stable/how-to.html).
- testmon selects tests by recorded executed-code dependencies and requires an initial full database-building run:
  [testmon overview](https://www.testmon.org/). Its own CI guidance cautions that central dependency/result management
  is more effective than casually sharing writable `.testmondata` files:
  [testmon in CI](https://www.testmon.org/blog/testmon-in-ci/).
- Pants documents per-test-file parallelism/fine-grained caching, changed-dependent selection, batching tradeoffs,
  Python import inference, and REAPI caching: [test](https://www.pantsbuild.org/stable/docs/python/goals/test),
  [advanced target selection](https://www.pantsbuild.org/stable/docs/using-pants/advanced-target-selection),
  [dependency inference](https://www.pantsbuild.org/stable/reference/subsystems/python-infer), and
  [remote caching](https://www.pantsbuild.org/stable/docs/using-pants/remote-caching-and-execution).
- Bazel demonstrates the same strategic primitives—hermetic test actions, runner-aware sharding, and cached action
  results—but would require more Python/pytest rule integration here:
  [Bazel test encyclopedia](https://bazel.build/reference/test-encyclopedia).

## Recommended solution

Adopt a **two-speed, dependency-aware verification system without splitting the repo now**.

Immediately create real test lanes, optimize or remove the three 30–60 second archive/lock tests from the default lane,
and replace the greedy 4–21 worker lease with fair job classes (1–2 workers for affected checks, roughly 8 for an
exhaustive run). Add `just check-agent` using a conservatively broadened testmon baseline, and change the project policy
so phase agents run that fast check while the land agent performs one exhaustive integrated check.

In parallel, run a bounded Pants pilot on a few hundred hermetic Python tests. If the pilot achieves zero shadow misses,
sub-three-minute phase checks, and at least 80% warm cache hits, expand it incrementally and add a shared CI cache. Keep
non-hermetic system/visual/performance tests in explicit legacy lanes until they are isolated. Use the resulting target
graph to remove non-ACE→ACE dependencies and continue moving shared backend behavior to `sase-core`; only then
reconsider an ACE repository split for product-boundary reasons.

This is the only evaluated approach that attacks all three dominant multipliers at once: **full-suite work repeated by
every agent, full collection repeated by every xdist worker, and unchanged results recomputed in every workspace**.
