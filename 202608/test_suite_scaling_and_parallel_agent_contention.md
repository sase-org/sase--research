---
create_time: 2026-08-05
updated_time: 2026-08-05
status: research
---

# Test Suite Scaling and Parallel-Agent Contention

## Question

The sase test suite has become very large and very slow, and the pain is worst when many SASE agents run in parallel
from their own numbered workspaces. What is actually costing the time, where does parallelism break down, and what
should be changed — including large architectural moves such as splitting the repo, if that is genuinely the right
answer?

## Executive Summary

**The suite is not slow because individual tests are slow. It is slow because every agent runs all 25,900 of them, every
time, against a fixed host-wide worker pool.** One full `just test` costs **3,648.7 CPU-seconds (60.8 CPU-minutes)** of
measured test execution. The host-global worker-token gate caps the whole machine at 32 workers (observed 15–16 under
real memory pressure), so 16 workspaces each running `just check` once demand ~16 CPU-hours against a ~16–32
worker/minute ceiling. That is the whole problem in one sentence.

Four findings drive the recommendation:

1. **A confirmed CI regression is hiding in the gate.** `_calculate_default_token_budget` subtracts a flat
   `_RESERVED_CPUS = 4` from the CPU count. On a 4-vCPU GitHub-hosted runner that yields a budget of **1**, so CI runs
   the suite with `-n 1` — effectively serial. Measured CI legs: `test (3.13)` 44 min, `test (3.14)` 42 min,
   `test (3.12)` 66 min against a 90-minute timeout. The non-visual suite costs 2,478 CPU-s = 41.3 CPU-min, which
   matches a single worker almost exactly. This is a one-line fix worth roughly 3× on CI.
2. **27% of the suite's runtime is the visual PNG lane, which local runs execute redundantly.** `tests/ace/tui/visual`
   is **902.9 s across 420 tests (2,150 ms/test)** — 1.6% of the tests, 27% of the time. CI already runs it as a
   dedicated `visual-test` job (19 min) and explicitly excludes it from the test matrix, but `just test` includes it for
   every agent, on every check, and it is the lane most prone to contention flakes.
3. **Runtime is concentrated, but test *count* is not.** The median test takes **0 ms**; p75 = 30 ms; p90 = 250 ms. The
   slowest 1,000 tests (3.9%) are 63% of runtime and the slowest 2,500 (9.6%) are 86.5%. So most of the 25,900 tests are
   nearly free to execute — they are expensive only because they are *collected and scheduled* 16 times over.
4. **A median commit is textually related to 9.3% of test files, and running only those takes 18–167 seconds serially.**
   Three sampled commits scoped to their impacted test files ran in **18.3 s / 147.0 s / 166.5 s serial** versus ~61
   CPU-min for the full suite — a 20–200× reduction, achieved with a crude one-hop import heuristic and *no* worker pool
   at all.

**Recommendation: do not split the repo.** Splitting `ace/tui` out is technically feasible (it is 42% of source and only
34 non-TUI files import it) but it buys the same benefit as diff-scoped test selection while adding permanent
cross-repo version-pinning cost, and it does not reduce aggregate host demand at all. Instead: fix the CI gate budget
and pull visual out of the default lane this week (−36% suite CPU, CI 44 → ~15 min), then make **diff-scoped test
selection the default for `just check`** with the full suite reserved for CI (~30× reduction in aggregate host demand),
then add per-agent fair-share to the existing gate and a per-PR test-runtime budget to keep growth bounded.

## Evidence

All measurements taken 2026-08-05 on the development host (64 CPU, 62 GiB RAM) at commit `8065b58c4`, with 4–5 sibling
agent workspaces concurrently running their own suites — i.e. under realistic contention, not on an idle box.

### The suite in numbers

| Metric | Value |
| --- | --- |
| Source | 606,022 LOC / 2,749 files |
| Tests | 641,541 LOC / 2,697 files |
| Collected (default lane) | 25,920 tests |
| Measured test execution, full `just test` | **3,648.7 CPU-s (60.8 CPU-min)** |
| — of which `call` | 3,381.2 s |
| — of which `setup` | 230.2 s |
| — of which `teardown` | 37.2 s |
| Observed wall clock at 12 workers | 384.6 s and 357.0 s (two runs) |
| Non-execution overhead (12 × 384.6 − 3,648.7) | 966 worker-s = **21%** |

The 21% overhead is collection, interpreter/plugin import, xdist IPC and scheduling idle. It is real per-worker cost:
`import sase.ace.tui.app` alone is **1.4–2.1 s**, and single-process collection of the suite is **15.6 s**. Every worker
in every concurrent run pays both.

### Growth trajectory

Exact LOC by month (`git archive <ref> | tar -xO`):

| Month | Test files | Test LOC | Src files | Src LOC |
| --- | --- | --- | --- | --- |
| 2026-02 | 205 | 30,012 | 372 | 78,423 |
| 2026-03 | 327 | 61,024 | 497 | 109,241 |
| 2026-04 | 659 | 134,201 | 756 | 159,431 |
| 2026-05 | 1,088 | 233,989 | 1,200 | 245,074 |
| 2026-06 | 1,551 | 342,301 | 1,577 | 329,583 |
| 2026-07 | 2,604 | 619,504 | 2,621 | 583,326 |
| 2026-08 | 2,697 | 641,541 | 2,749 | 606,022 |

Test LOC grew **21× in six months**; July alone added 277k test LOC (+81%). The test:source ratio has held steady at
~1.06:1 throughout, so this is not test bloat relative to source — it is that *both* are growing at agent speed. Any
solution that only trims the current suite is a one-time win against a curve that doubles every ~6 weeks.

### Where the time actually goes

Per-area `call` time from a full run with `--durations=0`:

| Area | Time | Tests | ms/test |
| --- | --- | --- | --- |
| `tests/ace/tui/visual` | **902.9 s** | 420 | **2,150** |
| `tests/*.py` (flat) | 821.6 s | 11,876 | 69 |
| `tests/ace/tui/*` (rest) | 770.8 s | 4,729 | 163 |
| `tests/ace/tui/widgets` | 331.4 s | 3,018 | 110 |
| `tests/test_bead` | 279.9 s | 1,357 | 206 |
| `tests/main` | 68.0 s | 1,171 | 58 |
| `tests/agents_sync` | 56.7 s | 242 | 235 |
| everything else | ~150 s | ~3,100 | — |

TUI-facing tests (visual + `ace/tui` + widgets) are **2,005 s = 59% of call time on 32% of the tests**. Excluding the
visual lane alone leaves **2,478.3 CPU-s over 25,491 tests**.

Duration distribution across all 25,911 `call` phases:

```
mean=0.130s  p50=0.000s  p75=0.030s  p90=0.250s  p95=0.750s  p99=2.250s  max=85.75s

top    10 slowest:  241.8 s =  7.2%
top    50 slowest:  424.4 s = 12.6%
top   100 slowest:  587.3 s = 17.4%
top   500 slowest: 1461.5 s = 43.2%
top  1000 slowest: 2130.8 s = 63.0%
top  2500 slowest: 2923.1 s = 86.5%
```

Costliest single files:

| File | Time | Tests |
| --- | --- | --- |
| `tests/test_dismissed_bundle_persistence.py` | **160.3 s** | 19 |
| `tests/ace/tui/widgets/test_vim_normal_key_containment.py` | 67.6 s | 45 |
| `tests/ace/tui/visual/test_ace_png_snapshots_prompt_highlighting.py` | 51.0 s | 16 |
| `tests/ace/tui/test_agents_zoom_panel_files.py` | 36.3 s | 18 |
| `tests/test_plan_gates.py` | 34.6 s | 32 |

Three tests in `test_dismissed_bundle_persistence.py` account for 85.75 s + 61.17 s + ~13 s — **4.4% of the entire
suite in three assertions**. Their names (`test_save_dismissed_bundle_is_fast_with_many_existing_bundles`,
`test_bundle_no_limit`) identify them as scale/performance tests, which belong behind the `slow` marker.

### The parallel-agent bottleneck is the shared worker pool

`tests/_suite_gate.py` implements a host-global, crash-safe `flock` token pool. Its budget is:

```
budget = min(cpu_count - 4, (MemAvailable - 8 GiB) / 1.2 GiB, 32)
```

Each runner then takes `floor=4, ceiling=min(28, budget - 4)` tokens. Measured behaviour on this host:

| Host shape | Budget | Auto range |
| --- | --- | --- |
| 2 CPU / 7 GiB | **1** | (1, 1) |
| **4 CPU / 16 GiB (GitHub runner)** | **1** | **(1, 1)** |
| 8 CPU / 32 GiB | 4 | (4, 4) |
| 16 CPU / 64 GiB | 12 | (4, 8) |
| 64 CPU / 62 GiB available | 32 | (4, 28) |
| 64 CPU / 27 GiB available (observed) | 15 | (4, 11) |

Two consequences:

- **Memory, not CPU, is the binding constraint on the dev box.** Workers measured at 0.8–1.0 GiB RSS each; `sase ace`
  itself holds 3.08 GiB. With 27 GiB available the budget collapses from 32 to 15. This is self-reinforcing: more
  concurrent runs → less free memory → smaller pool → longer runs → more overlap. (The pool capacity is also pinned at
  whatever the *first* lease computed — observed capacity 23 while the live computation said 16 — so the pool does not
  shrink back until every holder exits.)
- **The host has a hard throughput ceiling of ~16–32 worker-minutes per wall-minute.** One suite is 60.8 CPU-minutes.
  Sixteen agents running `just check` once is ~973 CPU-minutes, or **30 min at full budget and 61 min at the observed
  budget of 16** — for a single check each. Agents typically run `just check` two to four times per task, so a round of
  16 agents represents 2–4 hours of contended wall clock. The gate is doing its job (it prevents thrash); the problem is
  the amount of work being admitted.

### Confirmed: CI runs the suite on one worker

`.github/workflows/ci.yml` sets no `SASE_TEST_GATE_SLOTS`, so `ubuntu-latest` (4 vCPU) computes
`cpu_limit = max(4 - 4, 1) = 1` and the whole matrix runs `-n 1`. Measured job durations from run `31026717636`:

| Job | Duration |
| --- | --- |
| `test (3.12)` (coverage leg) | **66 min** |
| `test (3.13)` | 44 min |
| `test (3.14)` | 42 min |
| `visual-test` | 19 min |
| Job timeout | 90 min |

The non-visual suite measures 2,478 CPU-s = **41.3 CPU-min**, which is within a couple of minutes of the observed 42–44
min legs. The 66-minute coverage leg is that plus coverage instrumentation overhead. The match is close enough to treat
the single-worker diagnosis as confirmed rather than inferred.

There is a second-order effect: of the last 40 CI runs on `master`, the large majority are `cancelled` by latest-wins
concurrency. Master is pushed faster than a 66-minute CI leg can finish, so the merge queue rarely produces a green
signal at all.

### Contention flakes and workspace skew are a real tax

Two consecutive full runs produced 6 and 7 failures with overlapping but non-identical sets. Re-running the seven
failures serially in isolation:

- **5 of 7 reproduced** — all version skew between the Python expectations and this workspace's installed
  `sase_core_rs` extension (e.g. `Error: issue not found: missing-edge` where the test expects
  `Dependency does not exist: …`). This is the documented "run `just install` first in a long-idle workspace" hazard,
  and it is itself a parallel-agent tax: 16 workspaces each carry an independently-staled binding.
- **2 of 7 passed in isolation** — genuine contention flakes, one of them in the visual lane
  (`test_ace_png_snapshots_agents_slow_tools`). The Justfile's own `test-visual-contention` notes record a pre-fix
  baseline of *116 failed / 246 passed* under 13× worker oversubscription, so this lane's sensitivity to contention is
  already known and documented.

Every contention flake costs an agent a re-run of the full suite, which feeds straight back into the pool.

### Test impact selection: measured, not hypothetical

For each of the last 40 first-parent commits, matching test files against the commit's changed `sase.*` modules (one-hop
textual match on the module and its parent package — deliberately over-inclusive):

```
median matched share:  9.3% of 2,697 test files
mean   matched share: 14.1%
```

Sampled commits, running only their matched test files, **serially with one worker**:

| Commit | Test files | Tests | Serial wall |
| --- | --- | --- | --- |
| `734d2e0c2` | 63 | 633 | **18.3 s** |
| `8065b58c4` | 233 | 2,557 | **147.0 s** |
| `e99f5017d` | 344 | 3,635 | **166.5 s** |
| — full suite — | 2,697 | 25,900 | ~3,650 s |

A crude heuristic already gives a **20–200× reduction**, and — critically — these runs are fast enough *serially* that
they do not need the shared worker pool at all. Sixteen agents running scoped serial checks would consume ~16 CPUs
instead of saturating a 32-token pool.

### Repo-split seam analysis

If a split were the answer, the seam is clear:

| Unit | Src LOC | Src files | Test LOC | Test files |
| --- | --- | --- | --- | --- |
| `src/sase/ace/tui` | **257,247 (42%)** | 1,122 | ~291,547 (45%) | 1,157 (43%) |
| everything else | 348,775 | 1,627 | ~349,994 | 1,540 |

Coupling is genuinely thin in one direction: only **34 non-TUI source files** import `sase.ace.tui`, versus the TUI
importing 50+ domain packages (`sase.core` 445 references, `sase.xprompt` 236, `sase.agent` 112, …). So `ace/tui` is
close to a leaf consumer and *could* be extracted. The wider `sase.ace` package is not a candidate — 128 non-`ace`
source files import it.

## Alternatives Considered

### A. Split the repo (extract `ace/tui`)

**Effect:** two repos with suites of ~35 and ~25 CPU-min. A change confined to one side runs half the tests.

**Against it:** this is a strictly worse version of test impact selection. It delivers a fixed 2× only for
single-sided changes, while impact selection delivers a measured 20–200× for *all* changes. It adds permanent cost:
version pinning between two repos, two PRs for any cross-cutting change (the TUI's 50+ domain imports guarantee these
are common), doubled CI, doubled workspace provisioning, and a `sase repo open` hop for every agent that touches both.
It does not reduce aggregate host demand at all — the same tests run, just in two processes. And it does nothing about
the growth curve: at the current rate each half returns to today's size within ~6 weeks. **Recommend against as the
primary fix.** It remains a reasonable *later* move if the TUI acquires an independent release cadence, for reasons
other than test time.

### B. Push more logic into the Rust core (`sase-core`)

Already the stated architecture in `CLAUDE.md`, and directionally right — Rust tests are one to two orders of magnitude
cheaper per assertion. But it is a multi-quarter migration, and it does not touch the 59% of runtime that is TUI
presentation testing, which by the repo's own litmus test *should* stay in Python. Continue, but not as the answer to
this question.

### C. Reduce per-test fixed cost in the TUI harness

Bare Textual `run_test()` on a trivial app measures **40 ms/iteration**; that is the floor for the 2,153 pilot-driven
tests, and `ace/tui` tests average 110–163 ms. A shared session-scoped app harness, or converting pilot tests to direct
widget-render assertions, could plausibly halve the 2,005 s of TUI time. Real but bounded (≈ −25% overall), and it is a
large refactor across 1,157 files. Worth doing incrementally; not the lead.

### D. Distributed / remote test execution

The host genuinely is the constraint, so shipping suite runs to a build farm is a legitimate option. It adds
infrastructure, network latency, and result-plumbing complexity. Only worth it *after* the common case is cheap —
otherwise it scales the wrong workload.

### E. Prune the suite

641k test LOC in six months, with a p50 test duration of 0 ms, strongly suggests redundancy. But the trivial tests are
nearly free to *execute*; they cost collection and scheduling, not runtime. Mass deletion is risky, hard to automate,
and attacks the smallest term. The useful version of this idea is governance (see step 3 below), not deletion.

### F. Tighter admission control in the existing gate

The gate throttles workers but has no per-agent fairness: one runner can take up to 28 of 32 tokens while others sit at
the 4-token floor for up to 45 minutes. A fair-share cap (`ceiling = max(floor, budget / active_leases)`) is cheap and
improves latency variance, but it redistributes a fixed pie rather than shrinking the work. Good companion, not a fix.

## Recommended Solution

A three-step plan, ordered by effort-to-payoff. Steps 1 and 2 are independent and can land in either order.

### Step 1 — This week: reclaim 36% of suite CPU and 3× of CI (hours of work)

1. **Make the gate's CPU reserve proportional.** Replace the flat `_RESERVED_CPUS = 4` with something like
   `reserved = max(1, cpu_count // 8)`, or set `SASE_TEST_GATE_SLOTS` explicitly in `.github/workflows/ci.yml`. Today a
   4-vCPU runner gets a budget of 1. Expected: CI test legs **44 min → ~15 min**, coverage leg **66 min → ~22 min**,
   which also stops the latest-wins cancellation treadmill on `master`.
2. **Remove the visual lane from the default `just test`.** Flip `FAST_MARKER_EXPRESSION` to
   `"not slow and not visual"` and keep `just test-visual` / `SASE_PYTEST_EXCLUDE_VISUAL` as the opt-in, matching what
   CI already does with its dedicated `visual-test` job. Saves **902.9 CPU-s (27%)** and removes the lane with the known
   contention-flake profile. Agents can get this benefit *today*, before any code change, with
   `SASE_PYTEST_EXCLUDE_VISUAL=true just test`.
3. **Mark the three scale tests in `tests/test_dismissed_bundle_persistence.py` as `slow`.** 160.3 s / 4.4% of the suite
   in three tests that are explicitly measuring performance at scale.

Combined: 3,648.7 → ~2,320 CPU-s, a **36% cut**, for a few hours of work and no architectural risk.

### Step 2 — Next: diff-scoped test selection as the default for `just check` (1–2 weeks)

Make `just check` run only the tests reachable from the working diff. Keep the full suite as the CI gate and behind an
explicit `just test-full`.

- **Selection mechanism, phase 1:** static import-graph closure from changed `src/sase/**` modules to test files. No
  artifacts, no state, fully deterministic, and the crude version already measured 18–167 s per commit. Always include
  `tests/conftest.py`-adjacent and marker-driven suites, and fall back to the full suite when a "hub" file changes
  (`conftest.py`, `pyproject.toml`, `src/sase/core/**`, anything matching >40% of test files).
- **Selection mechanism, phase 2:** upgrade to a per-test coverage map. The CI coverage leg already runs
  `--cov=src/sase`; adding `--cov-context=test` and publishing the contexts database as an artifact turns selection from
  a heuristic into ground truth, including dynamic dispatch the import graph misses.
- **Safety net:** CI keeps running everything on every PR, so a selection miss delays discovery to CI rather than
  shipping a regression. Add a nightly/pre-release full local run.

Expected: median agent check drops from ~61 CPU-min to ~2–6 CPU-min. Aggregate host demand for a round of 16 agents
drops from ~973 CPU-min to ~30–90 CPU-min — a **10–30× reduction** — and most scoped runs become fast enough to skip the
worker pool entirely, which removes the queueing that currently dominates perceived latency.

This is the step that specifically fixes "especially when parallel agents are run," because it attacks aggregate demand
rather than per-run latency.

### Step 3 — Then: keep it from coming back (ongoing)

- **Per-agent fair-share in the gate.** `ceiling = max(floor, budget // max(1, active_leases))`, so the eleventh agent
  is not starved at the 4-token floor while the first holds 28. Also let the pool re-derive capacity downward when
  holders change, instead of pinning it to the first lease's computation.
- **Per-PR test-runtime budget.** Gate on measured suite delta, not on test count: a PR that adds more than N seconds of
  suite time needs an explicit justification. This is the only lever that bends the 21×-in-six-months curve, and it is
  cheap to implement on top of the `--durations` data the runner already emits.
- **Chip away at TUI harness cost.** A session-scoped app harness for the 2,153 pilot tests, and a standing preference
  for direct widget assertions over `run_test()` pilots in new tests.
- **Continue the Rust core migration** for domain logic, per the existing boundary rule.
- **Fix workspace binding skew.** Five of seven observed failures were stale `sase_core_rs` in a long-idle workspace.
  A cheap staleness check in `_setup` that fails loudly (rather than producing seven confusing assertion errors) would
  save agents a full diagnostic cycle each time.

### Explicitly not recommended now

**Do not split the repo.** The seam is real and the extraction of `src/sase/ace/tui` (42% of source, 34 reverse imports)
would work, but it delivers a fixed ~2× only for single-sided changes, at the cost of permanent cross-repo version
pinning and two-PR workflows for the cross-cutting changes the TUI's 50+ domain imports make routine — and it leaves
aggregate host demand unchanged. Diff-scoped selection delivers a measured 20–200× for every change, with no
coordination cost. Revisit the split only if the TUI needs an independent release cadence, on its own merits.
