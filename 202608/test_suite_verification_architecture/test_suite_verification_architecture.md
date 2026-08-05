---
create_time: 2026-08-05
updated_time: 2026-08-05
status: research
---

# Test Suite Verification Architecture at Agent Scale

**Research question:** The sase test suite has become very large and very slow, and the pain is worst when many agents
run their suites in parallel from their own numbered workspaces. What is actually costing the time, where does
parallelism break down, and what should change — including large architectural moves such as splitting the repo?

**Sources:** Consolidates two independent research reports ([`__a`](test_suite_verification_architecture__a.md),
[`__b`](test_suite_verification_architecture__b.md)) plus a third round of measurement run for this report on 2026-08-05
at commit `256da2887` on the development host (64 CPU, 62 GiB) under live contention from sibling workspaces. Where the
two reports disagreed, the disagreement is resolved below with a fresh measurement rather than by averaging.

## Bottom line

The suite is not slow because tests are slow. **It is slow because roughly 200–400 full-suite runs per day are admitted
against a host that can supply about 46,000 worker-minutes per day, and each run costs about 61 worker-minutes.** The
test suite is consuming somewhere between a quarter and a half of the machine's entire gated worker capacity,
continuously. Every other symptom — 45-minute gate waits, contention flakes, 66-minute CI legs — is downstream of that
one fact.

Three things follow:

1. **There is a confirmed one-line CI regression worth ~3×.** `_RESERVED_CPUS = 4` on a 4-vCPU GitHub runner yields a
   worker budget of exactly 1, so the entire CI matrix runs effectively serially. Verified in code and against measured
   job durations.
2. **The default local lane is stricter than CI in the wrong direction.** `just test` includes the visual PNG lane —
   27% of runtime for 1.6% of tests — even though `pyproject.toml`'s own default `addopts` excludes it and CI runs it as
   a separate job.
3. **The structural fix is diff-scoped selection as the default agent check, with the exhaustive suite reserved for
   integration and CI.** Measured this session: a real commit's scoped selection ran in **308 s on one core** versus
   ~385 s wall on 12 cores for the full suite — a **~15× reduction in host demand per check**, and it does not need the
   worker pool at all.

**Do not split the repo.** Both prior reports reached this independently and the fresh coupling measurements support it:
the `sase.ace.tui` seam is thin (27–34 reverse imports) but the wider `sase.ace` package has **128** non-`ace` importers,
and a split delivers a fixed ~2× for single-sided changes while adding permanent cross-repo pinning and leaving
aggregate host demand unchanged.

**Do not adopt Pants or Bazel yet.** Report `__a` makes a genuinely good case that a build system supplies the three
missing primitives (pre-collection partitioning, dependency-aware selection, cross-workspace result caching). But the
measurements below show the first two are worth less than they appear here, and the third can be approximated for a
fraction of the migration cost. Revisit only if the staged plan below plateaus.

## What both prior reports got right

These are settled; they are stated once and not re-argued.

- **Volume, not a slow tail.** Median test duration is 0 ms; p90 = 250 ms. The slowest 1,000 tests (3.9%) are 63% of
  runtime. Removing the worst offenders is worth a few percent, not a transformation.
- **The default lane is the whole suite.** Only **15** `pytest.mark.slow` usages exist across 2,699 test files. `slow`
  is not functioning as an execution class.
- **Three tests in `tests/test_dismissed_bundle_persistence.py` are 4.4% of the suite** (160.3 s). They are scale tests
  by name and behaviour and belong behind `slow`.
- **The suite-gate is greedy.** Floor 4, ceiling `budget - floor`, 45-minute acquisition timeout. The first run takes
  nearly everything; the second gets the floor; the third waits.
- **The gate always leases, even for a one-test run.** `tools/run_pytest:_parallel_worker_grant` acquires a lease
  unconditionally unless `SASE_TEST_GATE_DISABLED=1`. A scoped check today would still queue for 4 tokens for up to 45
  minutes — which would silently negate the entire benefit of scoping.
- **Growth is the real adversary.** Test LOC grew ~21× in six months (30k → 642k), with the test:source ratio steady at
  ~1.06:1. Both sides are growing at agent speed. Any fix that trims today's suite is a one-time win against a curve
  that doubles roughly every six weeks.
- **Continue the Rust-core migration** for architectural reasons, not as the answer to this question — it does not touch
  the 59% of runtime that is TUI presentation testing, which by the repo's own litmus test should stay in Python.

## Corrections and resolved disagreements

| Claim | `__a` | `__b` | Verified this session |
| --- | --- | --- | --- |
| CI runs on one worker | not found | budget = 1 on 4-vCPU runner | **`__b` confirmed.** `_RESERVED_CPUS = 4`; `cpu_limit = max(cpu_count - 4, 1)`; `.github/workflows/ci.yml` sets no `SASE_TEST_GATE_SLOTS`. This is the highest-ROI fix in either report and `__a` missed it entirely. |
| Visual lane in `just test` | "intentionally included" | 27% of runtime, should be excluded | **`__b` right.** `tools/run_pytest` sets `FAST_MARKER_EXPRESSION = "not slow"`, overriding `pyproject.toml`'s own `-m "not slow and not visual"`. CI already sets `SASE_PYTEST_EXCLUDE_VISUAL=true` and runs a dedicated `visual-test` job. The local default is *looser* than CI. |
| Non-`ace` importers of `sase.ace` | 74 | 128 | **128.** (`grep -rlE '^\s*(from\|import)\s+sase\.ace'` over `src/sase`, excluding `src/sase/ace/`.) `sase.ace.tui` specifically: 27 importers outside `sase.ace`, 34 counting string references — `__b`'s figure. |
| Cost of one full run | ~1,590 CPU-s | 3,648.7 "CPU-s" | **Both correct, different units.** `__a` measured true CPU time (187% utilisation × 849 s). `__b` summed per-test wall durations, which is *worker*-seconds and includes I/O, sleep, and lock waits. The suite is only ~47% CPU-busy per worker. `__b`'s number is the right one for capacity planning (a blocked worker still holds a slot) but must be read as worker-seconds, not CPU-seconds. |
| Most master CI runs are cancelled | — | "large majority" | **Overstated.** Last 40 master runs: 25 success, 11 cancelled (27.5%), 1 failure. Still notable — more than one in four master runs is discarded — but not a majority. |
| Affected selection still pays full collection | yes (objection to testmon) | implied no | **`__a`'s conclusion right, reasoning wrong** — see below. Path-scoped selection *does* limit collection to the given paths, but explicit file lists collect so inefficiently that scoping saves nothing. |
| xdist collection multiplier is "decisive" | decisive | folded into 21% overhead | **`__b`'s framing is better.** 21 workers × 16.1 s = 338 worker-s against ~3,650 worker-s total ≈ 9%. Real, but a secondary term, not the lever. |

## The measurement that changes the plan: scoping does not save collection

Report `__a` argued that affected selection is limited because "the roughly 15-second hot full collection remains," and
concluded that partitioning must happen *before* pytest starts — which is the core argument for Pants. Report `__b`
implicitly assumed path-scoped runs are nearly free to start. Both are wrong, in opposite directions:

| Selection | Files | Tests | Collection time |
| --- | ---: | ---: | ---: |
| Full suite via `testpaths` | 2,699 | 25,937 | **16.1 s** |
| 398 files (real commit's scoped set) | 398 | 4,966 | **20.8 s** |
| 800 files, explicit list | 800 | 9,765 | 61.9 s |
| `tests/ace/tui/widgets` as a **directory** | 228 | 3,018 | 2.1 s |
| the same 228 files listed **individually** | 228 | 3,018 | 4.9 s |

Collecting 19% of the tests costs **129%** of what collecting all of them costs. Passing an explicit file list is
roughly 2.3× more expensive per file than passing the enclosing directory, and pytest's per-argument conftest and
rootdir resolution makes the penalty superlinear. Coarsening to directories does not rescue it either: collapsing that
398-file selection to its 20 parent directories re-selects the entire 25,522-test suite.

**This does not defeat diff-scoped selection — it just means the win is entirely in execution, not collection.** A
scoped check should be budgeted at ~20 s of fixed collection cost plus scoped execution, and that is still
overwhelmingly worth it, because execution is ~3,650 worker-seconds. It does, however, remove the main technical
argument for a build-system migration: the collection term Pants would eliminate is worth ~16–21 s per run, not minutes.

## The measurement that sizes the problem: demand, not latency

Neither prior report measured how many checks the host is actually asked to run. That number reframes everything.

| Metric | Value |
| --- | --- |
| sase-project agent runs, July 2026 | **9,852** (~300–630/day) |
| Commits landed on master, last 14 days | **45–116/day** |
| Cost of one `just test` | ~3,650 worker-s = **60.8 worker-min** |
| Host gated capacity | 32 worker-slots × 1,440 min = **46,080 worker-min/day** |

Every agent that changes a file is required by `CLAUDE.md` to run `just check`, and in practice runs it more than once
(fix a lint failure, re-run). The run count is an estimate, not a direct measurement, and it is derived conservatively:
45–116 commits land per day, each from at least one agent that ran `just check` at least once, plus the substantial
fraction of the ~300–630 daily agent runs that change files without landing. **200–400 full-suite runs per day** is the
low end of that derivation. At 60.8 worker-minutes each — itself conservative, since it excludes the ~21% collection
and IPC overhead — the suite demands **12,000–24,000 worker-minutes per day against a 46,080 ceiling: 26% to 53% of the
entire machine, continuously.**

Report `__b` framed this as "16 workspaces × one check ≈ 973 worker-min." The real figure is an order of magnitude
larger and sustained. This is why the gate feels punitive: it is not misconfigured so much as it is rationing a resource
that is genuinely oversubscribed. **No amount of scheduler fairness fixes an oversubscribed resource. Only reducing
admitted work does.**

## Where the time goes

Per-area `call` time from a full `--durations=0` run (`__b`'s measurement, the best-instrumented in either report):

| Area | Time | Tests | ms/test |
| --- | ---: | ---: | ---: |
| `tests/ace/tui/visual` | **902.9 s** | 420 | **2,150** |
| `tests/*.py` (flat) | 821.6 s | 11,876 | 69 |
| `tests/ace/tui/*` (rest) | 770.8 s | 4,729 | 163 |
| `tests/ace/tui/widgets` | 331.4 s | 3,018 | 110 |
| `tests/test_bead` | 279.9 s | 1,357 | 206 |
| everything else | ~275 s | ~4,500 | — |

TUI-facing tests are **2,005 s = 59% of call time on 32% of the tests**. Bare Textual `run_test()` on a trivial app
costs 40 ms/iteration, which is the floor for the ~2,150 pilot-driven tests.

### `just check` is the test suite

A gap in both reports: `just check` runs thirteen gates, and it was never established that `just test` dominates.
Measured this session:

| Gate | Warm | Cold (fresh workspace) |
| --- | ---: | ---: |
| ruff check + format | 0.33 s | 0.40 s |
| **mypy** (2,749 files) | 0.55 s | **31.0 s** |
| symvision | 15.2 s | 15.2 s |
| prettier (markdown) | 5.7 s | 5.7 s |
| `sase validate` | 6.0 s | 6.0 s |
| pyscripts / committed-plans / changelog / core-ver / keep-sorted / toobig | ~7.7 s | ~7.7 s |
| **all non-test gates** | **~35 s** | **~66 s** |
| **`just test`** | **~385 s at 12 workers** | same |

So `just test` is >90% of a warm `just check` and >85% of a cold one. The focus of both reports is correct. The mypy
result is also a miniature of the whole problem: 31 s cold, 0.55 s warm, and every ephemeral workspace starts cold.

### The gate's constants are miscalibrated in two directions

```python
budget = min(cpu_count - 4, (MemAvailable - 8 GiB) // 1.2 GiB, 32)
```

- **The CPU reserve is a flat 4.** On the 64-core dev box that is noise; on a 4-vCPU CI runner it is the entire machine.
  One constant serving both hosts is the bug.
- **The memory reserve per worker is 1,229 MiB.** Measured worker RSS across live sibling workspaces this session:
  **0.74–0.85 GiB**. The gate over-reserves by ~45%, so the dev-box budget is roughly 30% smaller than it needs to be.
  Memory — not CPU — is the binding constraint here, and it is self-reinforcing: more concurrent runs → less free memory
  → smaller pool → longer runs → more overlap.

### Contention flakes are a compounding tax

Two consecutive full runs produced 6 and 7 failures with overlapping but non-identical sets. Of seven re-run serially,
**five reproduced as stale `sase_core_rs` binding skew** in a long-idle workspace, and two were genuine contention
flakes. The scoped 4,966-test run for this report also produced one unrelated error. The `test-visual-contention`
harness in the Justfile documents a pre-fix baseline of *116 failed / 246 passed* under 13× oversubscription — this
lane's contention sensitivity is already known and documented.

Every flake costs an agent a full re-run, which feeds straight back into the pool. Report `__a` makes the right
observation here: a full run is itself a stress test of filesystem timing, locks, event loops, and subprocess cleanup,
and running it concurrently in 15 workspaces manufactures noise.

## Options evaluated

| Option | Effect | Verdict |
| --- | --- | --- |
| Fix `_RESERVED_CPUS` / set CI gate slots | CI 44 → ~15 min, coverage leg 66 → ~22 min | **Do now.** One line. |
| Exclude visual from default `just test` | −27% suite cost; aligns local with CI and with `pyproject.toml` | **Do now.** One line. |
| Mark 3 scale tests `slow` | −4.4% | **Do now.** |
| Right-size `_MEMORY_KIB_PER_WORKER` | +~30% host budget | **Do now.** Backed by measured RSS. |
| Diff-scoped selection as default `just check` | measured 15× reduction in host demand per check | **The fix.** |
| Gate fair-share + no-lease for scoped runs | Redistributes a fixed pie; removes the 45-min queue for cheap checks | **Necessary companion** — without the no-lease path, scoped runs still queue. |
| Per-PR suite-runtime budget | Only lever that bends the 21×/6-month curve | **Do, ongoing.** |
| TUI harness cost reduction | ≈ −25% overall; large refactor across 1,157 files | Incremental, not the lead. |
| Push logic into `sase-core` | Directionally right; multi-quarter; misses the 59% TUI term | Continue for architecture, not speed. |
| pytest-testmon | Learns test→code deps via coverage; needs a per-workspace baseline DB keyed by interpreter, plugins, platform, and core SHA | **Superseded** — see below. |
| Pants | Supplies pre-collection partitioning, changed-target selection, fine-grained caching, REAPI remote cache | **Defer.** Its collection win is worth ~16–21 s/run; its caching win is approximable far cheaper; its hermetic sandbox would immediately break the tests that already read ambient config. |
| Bazel | Same primitives, more Python/pytest rule integration | Alternative only if Pants is ever revisited and fails. |
| Split the repo | Fixed ~2× for single-sided changes | **No.** See below. |
| Prune the suite | Trivial tests are nearly free to execute | The useful version is governance, not deletion. |

### Why coverage contexts beat testmon here

Report `__a` recommends testmon as a bridge and correctly identifies its three limits (in-pytest selection, per-workspace
baseline DB hazards, blindness to config discovery and Rust-side changes). Report `__b` proposes upgrading a static
import heuristic to a per-test coverage map. **`__b`'s path is strictly better and `__a`'s own objections explain why:**
both derive from the same Coverage.py data, but the coverage-context map is produced by the CI leg that *already* runs
`--cov=src/sase --cov-branch`, published as a read-only artifact, and consumed identically by every ephemeral workspace.
Adding `--cov-context=test` to that existing job is the entire cost. There is no writable `.testmondata` to shard, no
per-workspace baseline to key and invalidate, and no new concurrency hazard.

### Why not split the repo

The seam is real: `src/sase/ace/tui` is 257k LOC (42% of source, 1,122 files) with only 27–34 reverse imports, while the
TUI imports 50+ domain packages. But:

- It delivers a fixed ~2× and only for changes confined to one side — versus a measured ~15× for *all* changes from
  scoped selection.
- The TUI's 50+ domain imports guarantee cross-cutting changes are routine, each becoming two PRs with version pinning
  between them, doubled CI, doubled workspace provisioning, and a `sase repo open` hop.
- **It does not reduce aggregate host demand at all.** The same tests run, in two processes. Given that demand is the
  actual constraint, this is disqualifying.
- At the current growth rate each half returns to today's size in about six weeks.
- The wider `sase.ace` package — the boundary that would actually need to hold — has **128** non-`ace` importers,
  concentrated in `axe` (29), `main` (16), and `core` (13). Many of those expose presentation types in the wrong
  direction.

Revisit only if the TUI acquires an independent release cadence, on its own merits. Test speed is not sufficient reason.

## Recommended solution

### Tier 0 — this week, hours of work, no architectural risk

1. **Make the gate's CPU reserve proportional**: `reserved = max(1, cpu_count // 8)`, or set `SASE_TEST_GATE_SLOTS`
   explicitly in `.github/workflows/ci.yml`. Expected: `test` legs 44 → ~15 min, coverage leg 66 → ~22 min, and the
   latest-wins cancellation treadmill on master stops.
2. **Flip `FAST_MARKER_EXPRESSION` to `"not slow and not visual"`** in `tools/run_pytest`, matching `pyproject.toml` and
   CI. Keep `just test-visual` as the opt-in. −902.9 s (27%), and it removes the lane with the known contention-flake
   profile. Agents can get this benefit *today* with `SASE_PYTEST_EXCLUDE_VISUAL=true just test`.
3. **Mark the three scale tests in `tests/test_dismissed_bundle_persistence.py` `slow`.** −160.3 s (4.4%). Their setup
   populates the archive by calling the production save path thousands of times; direct fixture construction would
   preserve the assertion at a fraction of the cost.
4. **Set `_MEMORY_KIB_PER_WORKER` to ~950 MiB**, from measured 0.74–0.85 GiB worker RSS. +~30% host budget for free.

Combined: **~36% less suite cost, ~30% more host capacity, ~3× faster CI.**

### Tier 1 — next, 1–2 weeks: two-speed verification

Split the verification contract in two. This is the change that actually addresses "especially when parallel agents are
run," because it attacks admitted demand rather than per-run latency.

- **`just check` (the agent default)** = format/lint on changed files + diff-scoped tests + an always-run contract set,
  run **serially or with at most 2 workers, taking no gate lease**. The no-lease path is not optional: without it a
  scoped run still queues behind the 4-token floor for up to 45 minutes and the entire benefit evaporates.
- **`just check-full`** = today's exhaustive behaviour, run by the land/integration agent on the combined tree, and by
  CI on every PR.
- Update the `CLAUDE.md` policy accordingly: phase agents run `just check`; the land agent runs `just check-full`.

**Selection mechanism, phase 1** — static import-graph closure from changed `src/sase/**` modules to test files. No
state, fully deterministic. Budget ~20 s of collection plus scoped execution.

**Selection mechanism, phase 2** — add `--cov-context=test` to the CI coverage leg that already runs and publish the
contexts database as an artifact. This turns selection from a heuristic into ground truth, including the dynamic
dispatch an import graph misses.

**Conservative broadening (adopted from `__a`, whose treatment of this is the strongest content in either report).** Run
the full suite when any of these change: `pyproject.toml`, `uv.lock`, pytest config or plugins, any `conftest.py`,
shared test helpers, `src/sase/default_config.yml`, code generators, packaging metadata, the `sase_core_rs` wheel or
core commit SHA, or the selection code itself. Always include tests whose own files changed. Always run a small
contract/system safety set covering repository-wide audits — the tests that scan strings, paths, bindings, symbols,
command catalogs, schemas, and packaging metadata, which no dependency engine can select correctly.

**Shadow-validate before making it authoritative.** Run scoped selection for agents while CI continues to run
everything, and log every case where CI fails a test the selection did not choose. Make the fast path mandatory only
after the false-negative rate is zero across at least 30 varied changes. Emit a machine-readable selection manifest per
run (changed files, selected tests, broadening rules fired, baseline identity, duration, outcome) — selection health is
a production metric, not a one-time validation.

**Expected effect.** Measured this session on a real commit: 398 matched test files → 4,966 tests → **308 s wall on one
core**, versus ~385 s wall on 12 cores for the full suite. That is **~15× less host demand per check**. Be honest about
the range: a static one-hop heuristic matched 14.7%–26.7% of test files on three recent commits (`__b` reported a 9.3%
median with a differently-tuned heuristic), so expect **5–15×** from phase 1 and better from phase 2 — not the 20–200×
`__b`'s three favourable samples suggest. Even the low end takes daily suite demand from 26–53% of the host to roughly
3–6%.

### Tier 2 — ongoing: keep it from coming back

- **Gate fair-share.** `ceiling = max(floor, budget // max(1, active_leases))`, and let the pool re-derive capacity
  downward when holders change instead of pinning it to the first lease's computation.
- **Per-PR test-runtime budget.** Gate on measured suite delta, not test count: a change adding more than N seconds of
  suite time needs explicit justification. This is the only lever that bends a curve doubling every six weeks, and it is
  cheap on top of the `--durations` data the runner already emits.
- **A cross-workspace result cache — the cheap version.** `__a` is right that "an unchanged test with unchanged
  dependencies already passed" is the expensive fact nobody reuses. The cheap approximation is not Pants: it is a
  host-local, content-addressed record keyed by (git tree hash of `src/` + `tests/`, interpreter version, lockfile hash,
  `sase_core_rs` wheel hash) that lets an agent skip a check entirely when an identical tree was already verified. With
  15 clones of one repo on one host, hit rates should be meaningful.
- **Fail loudly on stale workspace bindings.** Five of seven observed failures were stale `sase_core_rs` in a long-idle
  workspace, presenting as confusing assertion errors. A staleness check in `_setup` would save a full diagnostic cycle
  each time.
- **Chip away at TUI harness cost** — 59% of runtime. A session-scoped app harness for the ~2,150 pilot tests, and a
  standing preference for direct widget assertions over `run_test()` pilots in new tests.
- **Continue the Rust-core migration** per the existing boundary rule, and use the resulting dependency graph to drive
  non-`ace` imports of `sase.ace` toward zero. If that ever reaches zero and ACE earns an independent release cadence,
  the repo split becomes a product decision rather than a performance one.

### Sequencing note

Tier 0 items 1–2 are one-line changes with immediate, independently verifiable effects; do them before anything else so
Tier 1 is measured against a sane baseline. Tier 1's no-lease scoped path must land in the same change as scoped
selection, or the result will look like no improvement at all.

## Appendix: measurement provenance

Figures in this report come from three independent measurement rounds and are attributed where they differ:

- **`__a`** (codex, commit `865281be4`): 4-worker non-visual benchmark, 14:09 wall, 25,487 passed / 7 failed; cold
  collection 45.65 s, hot 14.94 s; 187% aggregate CPU utilisation.
- **`__b`** (claude, commit `8065b58c4`): full `--durations=0` runs at 12 workers under sibling-workspace contention;
  3,648.7 worker-s total, 902.9 s visual; per-area and percentile breakdowns; exact monthly LOC via
  `git archive | tar -xO`; three sampled diff-scoped serial runs.
- **This report** (commit `256da2887`): gate constant verification; CI workflow and `gh run list` verification; reverse
  import counts; per-gate `just check` timings, cold and warm; collection-cost curve by selection shape; a 398-file /
  4,966-test scoped serial run; live worker RSS sampling; agent-run and commit-rate counts from `~/.sase/chats` and
  `git log`.

The three rounds ran at different commits, under different levels of host contention, and with different instrumentation
(true CPU time vs. summed test durations). Absolute wall times are therefore not directly comparable across rounds;
ratios and structural findings are.

**Unrelated finding:** `just _lint-symvision` fails on clean master (`progress_fingerprint` in
`src/sase/llm_provider/commit_finalizer_git.py`, used via a module alias that symvision cannot resolve). Already tracked
as `sase-fj`; independently corroborated rather than re-filed. It is worth noting here because it compounds the demand
problem: while master is red on a lint gate, every agent's `just check` fails before it reaches the test stage, and the
retry costs another full run.
