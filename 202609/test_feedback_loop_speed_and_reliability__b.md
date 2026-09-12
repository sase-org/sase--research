# Speeding Up SASE's Test Feedback Loop Without Weakening Reliability (Researcher B)

**Research question:** The sase test suite is very slow and resource-hungry. Some of that
is the unavoidable cost of a large codebase. What is the best way to shorten the feedback
loop without making the architecture less reliable?

**Scope and method:** sase `master` at `e1a2f7839` (2026-09-12), measured on `apollo`
(16 vCPU Xeon Platinum 8168, 31 GiB, shared with sibling agent workspaces). Evidence
comes from:

- Code and config: the `Justfile`, `tools/run_pytest`, the suite gate, test selection,
  test-cost modules, the root conftest, and the GitHub workflows.
- Durable local data: the selection-health store and the newest full cost recording
  (`timings/cost/20260906T041026Z-3088222.json`, 7 workers).
- Earlier project research and decision records: the `two-speed-verification` and
  `ci-two-speed-split` decisions, plus `202604/test_suite_speedup.md`,
  `202605/just_check_speed_research.md` and
  `202609/temporary_high_capacity_test_machine.md`.
- GitHub Actions run history.
- Small experiments I ran myself: cProfile, `-X importtime`, and A/B runs.

Every number below is either copied from a recording (source named) or measured by me
(marked **measured**). The host was not idle, so treat the single-run timings as good to
within about ±20%.

---

## Executive Summary

The problem is not mainly that the suite is large. Three independent defects have piled
up, and each makes the others worse:

1. **The exhaustive lane pays a hidden 5–6× tax.**
   - `just check-full` runs `just test-cost`. Since `6385a8ebb` (2026-08-10), that lane
     also loads the global-state leak detector (`tests._global_state_leak_detector`).
   - The detector is a `tryfirst` hookwrapper. Before and after *every* test it walks the
     globals of every loaded `sase.*` module.
   - With all ~4,350 sase modules imported, one snapshot takes **0.24 s** (measured).
     That is about 0.5 s per test, times 38,700 tests.
   - In the last full cost recording on apollo, the 7 workers burned **37,865 CPU-s**, but
     only **4,681 CPU-s** happened inside test items and **326 CPU-s** in collection. About
     **87% of worker CPU was spent outside the tests.**
   - The run took **94.5 minutes of wall clock**. The same tests' item time (6,407 s)
     spread over the same 7 workers would take about **16–17 minutes**.
   - An A/B run on a 112-test file went from 7.7 s to 27.3 s with the detector loaded
     (measured).
2. **The safety net has holes, so the fast path cannot be trusted and agents fall back to
   the slow path.**
   - Master Gate has passed only 19 times in its last 399 runs (380 failures); the last
     green run was 2026-09-08. Full CI has not been green since 2026-08-29.
   - The current Master Gate reds are deterministic, not flaky: SDD artifact-link tests run
     `git commit` without a configured identity ("Author identity unknown"). They pass on
     dev hosts only because those hosts have a global git identity. Nothing in the root
     conftest isolates `GIT_CONFIG_GLOBAL` or author/committer identity.
   - Full CI's `coverage-contexts` job fails on a stale pinned-core binding. As a result,
     **zero** `sase-coverage-contexts-*` artifacts exist.
3. **The diff-scoped lane is running blind and is often slower than the lane it is meant
   to replace** (from `just selection-health` on apollo):
   - It was without its coverage-contexts baseline in **42 of 42** runs that consulted
     it.
   - **55%** of scoped runs escalated to the full lane.
   - Median scoped duration is **1,175 s**, and p90 is **2,207 s**. 34 of 84 scoped runs
     were slower than the "full lane" constant they are compared against.
   - That constant (232 s) was measured on athena with 28 workers. apollo grants only 7
     workers per run by default.
   - **19 false negatives** are recorded.

Inside the tests themselves, the dominant real cost is the **Textual app lifecycle**. App
startup, AcePage enter/exit, settle barriers and fixed-delay pilot pauses add up to
**4,388 s of the 6,407 s** attributed item wall (**68.5%**). About 2.25 s goes into each
`AcePage` enter.

**Recommendation (details in the last section):**

- Do not buy hardware first, and do not add more selection cleverness first.
- Run a four-step "make the governed lane cheap and the backstop real" program, in this
  order:
  1. Restore a green, hermetic CI signal.
  2. Take the leak detector off the per-change path and cut per-process fixed costs.
  3. Amortize the Textual lifecycle cost that dominates real test time.
  4. Only then repair and recalibrate the scoped lane, so it is a genuine accelerator
     rather than a gamble.
- Steps 1–2 are days of work, not weeks. On apollo they should turn `check-full` from
  about 95 minutes into about 20 minutes, with no loss of coverage.

---

## 1. The Workload, Measured

### 1.1 Size

| Metric                                   | Value                                         |
| ---------------------------------------- | --------------------------------------------- |
| Test files (`test_*.py`)                 | 3,952                                         |
| Test functions (`def test_`)             | 36,227                                        |
| Collected nodes in the cost lane         | 38,700 (3,516 files)                          |
| Test Python LOC vs `src/` Python LOC     | 1.08 M vs 0.97 M                              |
| Files using Textual `run_test` / `Pilot` | 326                                           |
| Test files calling `subprocess.*`        | 295 (86 files create git repos)               |
| `tests/ace/` share of shard-timing time  | 57% (`tests/ace/tui` alone: 4,255 s of 7,413 s) |
| Top 100 files' share of shard time       | 55.6% (top 500: 91.4%)                        |
| Reproducible-flake baseline              | 53 nodes (`tests/reproducible_flake_baseline.txt`) |

The time is concentrated. A few hundred TUI-heavy files carry most of the suite's cost,
which means targeted work on them pays off disproportionately.

### 1.2 Where a full run's CPU actually goes (apollo, cost lane, 7 workers)

From `20260906T041026Z-3088222.json`:

| Bucket                                           | Seconds  | Share of worker CPU |
| ------------------------------------------------ | -------- | ------------------- |
| Worker CPU, total (7 workers)                    | 37,865   | 100%                |
| CPU inside test items (setup+call+teardown)      | 4,681    | 12.4%               |
| Collection CPU (about 47 s per worker)           | 326      | 0.9%                |
| **Unattributed, outside items**                  | **~32,858** | **~86.8%**       |
| Controller wall clock                            | 5,671 (94.5 min) | —           |

Every worker ran at 92–98% CPU for the entire 94 minutes, yet each spent only 339–1,514 s
of wall time inside test items. The cost plugin's `pytest_runtest_protocol` wrapper has
no `tryfirst`, so any `tryfirst` wrapper runs *outside* its timer. Two such wrappers are
registered:

- **`tests._global_state_leak_detector`**: loaded only in the cost lane (enforced by
  `tests/test_run_pytest_command.py::test_global_state_leak_detector_args_are_cost_lane_only`).
  It calls `_snapshot()` before and after every test, and `_snapshot()` iterates
  `vars(module)` for every loaded `sase.*` module, fingerprinting private globals and
  caches.
- **`tests._config_reader_probe`**: loaded in every lane. Per test it only enumerates
  threads, which is cheap.

Detector cost, **measured**:

| Experiment                                                        | Result          |
| ----------------------------------------------------------------- | --------------- |
| `_snapshot()` with ~350 modules loaded                            | 0.002 s         |
| `_snapshot()` after importing all 4,354 `sase.*` modules          | **0.24 s** (3 runs) |
| `tests/test_pluggy_hookspec_forwarding.py` (112 tests), plain     | 7.7 s (9.5 s wall) |
| Same file with `-p tests._global_state_leak_detector --sase-detect-global-leaks` | **27.3 s** (28.9 s wall) |

An xdist worker that has collected the whole suite has imported essentially all of
`sase`. Two snapshots per test at 0.24 s each give a *lower bound* of about
**18,600 CPU-s** (0.48 s × 38,700), before counting the diff step and the extra GC
pressure from holding two large fingerprint maps. That lower bound alone explains more
than half of the unattributed CPU. The overall shape — flat 95% CPU with low item time —
matches a per-test cost that grows with the number of loaded modules.

**Caveat:** this attribution is an inference from recorded data plus micro-benchmarks,
not a controlled whole-suite A/B. Step 2 of the recommendation starts by running that
A/B: the same SHA with `just test-cost`, then with `just test`, on an otherwise idle
host.

### 1.3 Where real test time goes (inside items)

Cause attribution from the same recording (6,407 s item wall in total):

| Cause                          | Count  | Wall s | Mean       |
| ------------------------------ | ------ | ------ | ---------- |
| `ace_page_enter`               | 710    | 1,598  | 2.25 s     |
| `textual_app_run_test_enter`   | 3,684  | 1,359  | 0.37 s     |
| `ace_settle_pilot`             | 6,841  | 594    | 0.087 s    |
| `subprocess_run`               | 41,056 | 574    | 0.014 s (only 50 CPU-s: mostly waiting on git and other children) |
| `pilot_pause_delay` (numeric pauses) | 13,751 | 532 | 0.039 s |
| `textual_app_run_test_exit` + `ace_page_exit` | 4,392 | 252 | — |
| `parser_create`                | 1,861  | 92     | 0.05 s     |
| `yaml_load`                    | 56,006 | 58     | ~1 ms      |

The Textual lifecycle — app startup, page enter/exit, settle, pauses — totals
**4,388 s, or 68.5%** of attributed item time. The profile of one AcePage-based test
(`tests/ace/tui/test_help_modal_filter.py`, **measured**) points to these internals:

- `AcePage.__aenter__` takes about 2.0 s per enter.
- Importing `sase.ace.testing._startup` costs 5.6 s once per process.
- Textual CSS parsing makes about 3,000 `parse` calls, about 2 s in total, even with
  `sase/ace/testing/_stylesheet_cache.py` in place.

**Caveat:** that test itself failed on this workspace's stale local `sase_core_rs` wheel
(a missing binding), so its timings show the shape of the costs, not exact values.

The amortization layer already exists: `AcePageGroup` hands out isolated checkouts of one
running page, and a forced-isolation lane (`just test-ace-page-group-isolated`) keeps it
honest. Only **2 test modules** use it so far.

Grep counts show 128 numeric `pilot.pause(<delay>)` call sites in 23 files and 44
`asyncio.sleep(<n>)` sites in tests. Each numeric pause is wall time that a settle
barrier could replace.

### 1.4 Fixed per-process overhead (hurts serial scoped runs and inner-loop reruns)

Profiling `tests/core/test_agent_alias_history_wire.py` (4 trivial tests, **measured**):
the session takes about 10–11 s, while every test phase is under 5 ms. The overhead is
spent on:

- **3.3 s: an autouse fixture imports the TUI.**
  `tests/_conftest_runtime.py::_isolate_runner_limit_override` monkeypatches a dotted
  path inside `sase.ace.tui.modals.models_panel`. Resolving that string imports the
  models panel, the model picker modal and the Textual stack — for *every* test process,
  even non-TUI ones.
- **3.4 s: inline-snapshot's session report.** `inline_snapshot` `pytest_sessionfinish`
  → `show_report` runs even when no snapshot was touched.
- About 1 s of pytest, hypothesis and inline-snapshot plugin import, plus collection.

A worker in an xdist run pays these once, so they matter little for the full lane. They
matter a lot for the serial scoped lane and for "rerun this one file" loops, where
about 7 of 10 seconds is avoidable.

### 1.5 Host capacity

On apollo the suite gate computes `min(16 − 2, (MemAvailable − 8 GiB) / 700 MiB, 32)`,
which is about **14 tokens**. The automatic per-run ceiling is half of that: **7
workers**. Two concurrent full runs therefore saturate the host.

The `two-speed-verification` measurements (61 worker-minutes per run, 232 s full-lane
wall) came from athena's 64-core configuration, and `FULL_LANE_WALL_SECONDS = 232.0`
still encodes that athena crossover (`tests/_test_selection_health.py`). On apollo the
same crossover is off by an order of magnitude. That is why "serial-budget-exceeded"
fired in 31 of 84 scoped runs, and why so many scoped runs "lost" to a full lane that
does not really finish in 232 s here.

---

## 2. The Safety Net, Measured

The two-speed design is only sound if CI is a trustworthy backstop. The lint-and-test
note says selection "is a heuristic backstopped by CI". Right now it is not.

### 2.1 Master Gate (per-SHA, 8 shards)

- **19 successes against 380 failures** in the last 399 runs. Last green: 2026-09-08.
  Wall-clock p50 is 7.3 min, which is fine.
- The 6 most recent runs failed on the *same* nodes in shards 5 and 6:
  `tests/sdd/test_artifact_link_publication_retry.py`,
  `tests/sdd/test_artifact_link_machine_store.py` and
  `tests/sdd/test_artifact_link_hidden_clone_e2e.py`. Each fails with
  `git commit ... exit 128: Author identity unknown`. One shard-3 Textual `NoMatches`
  failure showed up once.
- Root cause: the tests are not hermetic. Dev hosts have `git config --global user.name`
  set (verified on apollo), but CI runners do not. The root conftest sets none of
  `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_NOSYSTEM`, `GIT_AUTHOR_*` or `GIT_COMMITTER_*`.
  Instead, 95 test files configure identity themselves, and each new git-using test must
  remember to do the same.

### 2.2 Full CI (scheduled every 2 h, exhaustive)

- Last green run: **2026-08-29**. p50 wall is 100 min.
- The latest run failed in `lint`, `coverage-contexts`, `visual-test`, `contention-test`,
  and the `test (3.12)` and `test (3.14)` legs.
- `coverage-contexts` dies on
  `sase_core_rs ... does not expose binding 'provider_pool_eligibility_mask'`: the pinned
  core revision lags the Python callers. Because the job never succeeds, **no coverage
  contexts artifact exists** (`gh api .../actions/artifacts` → 0 matches).

### 2.3 The diff-scoped lane (`just check`)

From `just selection-health` (84 scoped runs, 50 full runs, 30-day retention):

| Metric | Value |
| --- | --- |
| Escalated to full | 46 / 84 (54.8%) |
| Coverage-contexts baseline present | **0 / 42** consulted runs |
| Rules fired | `context-baseline-missing` 42, `no-baseline-depth-boost` 42, `serial-budget-exceeded` 31, `core-identity-changed` 29, `src-data-asset` 17 |
| Median / p75 / p90 duration | 1,175 s / 1,785 s / 2,207 s |
| Median selected | 638 files (16.8%) |
| Recorded false negatives | 19 (lumberjack history/tick/streaming, proc inventory, prompt-panel navigation) |
| Claimed worker-seconds avoided | 44,305 |

Without a contexts baseline, the selector adds `no-baseline-depth-boost` and widens the
static import closure, so selections balloon. It then runs them serially, or at the
middle gear's 4 workers, and takes 20–40 minutes. Meanwhile `core-identity-changed` fires
in 35% of runs, because ephemeral workspaces keep reinstalling a moving `sase_core_rs`
wheel (three core-pin commits landed on 2026-09-11/12 alone). This workspace's own venv
was stale against the source during this research.

**This is the feedback loop the user is feeling.** An agent's "fast" check takes 20–40
minutes, escalates about half the time, and the "slow" check takes about 95 minutes on
apollo. CI, meanwhile, is red for reasons unrelated to the change, so nobody learns
anything from it.

---

## 3. Options Considered

Each option is rated on three things: speed gain, effect on reliability, and cost.

| # | Option | Speed gain | Reliability effect | Cost / risk |
| --- | --- | --- | --- | --- |
| A | **Hermetic CI + stop-the-line on red Master Gate** (git identity and config isolation in the root conftest, a core-pin consistency gate) | Indirect but large: restores the backstop that makes every scoped shortcut safe; unblocks coverage contexts | **Strongly positive** | Days; small blast radius |
| B | **Move the leak detector off the per-change path** (run it in scheduled Full CI and/or sample it; `check-full` runs the fast lane plus timing and cost budgets) | `check-full` about 95 → ~17–20 min on apollo (5×); frees ~50–85% of full-run CPU host-wide | Neutral if the detector still runs, and still fails, on a schedule; poisoning is caught ≤2 h later instead of per landing | Hours to days |
| B′ | Make the detector cheap instead: snapshot only modules touched since the last check (module `__dict__` identity or version tags), per-file rather than per-test, or diff lazily | Similar to B, and keeps per-landing detection | Positive (keeps detection on every landing) | 1–2 weeks; detector correctness must be re-proven |
| C | **Cut per-process fixed costs** (lazy runner-limit patch that doesn't import the TUI; skip the inline-snapshot report unless snapshots were used; lazy `sase.ace.testing._startup`) | About 7 s off every serial or small run; large for scoped lanes and inner-loop reruns | Neutral | Days |
| D | **Amortize the Textual lifecycle** (migrate high-node-count TUI modules to `AcePageGroup`; extend stylesheet caching to `run_test` apps; replace the 128 numeric pauses with settle barriers; ratchet with existing cost budgets) | Attacks the 68.5% of item time; a realistic target is 30–50% of total item wall | Neutral to positive if the isolation lane and the budgets stay mandatory; pause→barrier also removes a timing-flake source | 2–6 weeks, incremental, parallelizable across agents |
| E | **Repair and recalibrate the scoped lane** (actually produce the contexts baseline; per-host crossover from the host's own full-lane records instead of athena's 232 s; stop `core-identity-changed` from escalating when the core wheel digest is unchanged; lease the host's fair share instead of 1–4 workers) | Scoped median 20 min → a few minutes, once contexts exist; escalation rate should fall sharply | Must be watched: 19 false negatives exist today; needs A as backstop | 1–3 weeks; builds on existing tooling |
| F | Adopt pytest-testmon (coverage-based, local DB, xdist support since v1.4) | Good inner-loop selection | Heuristic similar to E, but coverage-driven; overlaps the existing selector; adds a DB per workspace | Medium; duplicates sunk investment |
| G | Pants/Bazel-style result caching keyed by dependency closure | Large for unchanged areas | Soundness equals the static closure (misses dynamic imports, data files, subprocesses); already rejected in `two-speed-verification` | High; architecture-wide |
| H | More hardware (resize apollo, route full lanes to athena, rent a 48-vCPU droplet) | Linear in cores; about 3× on a 48-vCPU box | Neutral | Recurring cost; **multiplies waste** unless B–D land first |
| I | Demote TUI e2e tests to unit-level or delete "redundant" tests | Potentially large | **Negative**: TUI behavior is exactly what regresses; rejected | — |
| J | Split the repo to shrink each suite | Smaller suites | Adds cross-repo integration gaps; already rejected in the decision record | High |

---

## 4. Recommended Solution

**Adopt a sequenced "cheap governed lane, real backstop" program: A → B + C → D → E.**
Revisit hardware (H) only after measuring the result. Keep every existing safety lane
(leak detector, AcePageGroup isolation lane, contention harness, visual suite). What
changes is *where* they run and *what they cost*, not *whether* they run.

### Step 1 — Restore the backstop (days)

1. Add hermetic git isolation to the root conftest's environment fixture. It should set
   `GIT_CONFIG_GLOBAL` to an empty temp file, `GIT_CONFIG_NOSYSTEM=1`, and fixed
   `GIT_AUTHOR_NAME/EMAIL` and `GIT_COMMITTER_NAME/EMAIL`. Tests that need a specific
   identity can still override per test. This fixes the current Master Gate reds at the
   root, and stops the 96th git-using test file from repeating the bug.
2. Guard against pin drift: fail `lint` fast (it already runs
   `check_sase_core_rs_bindings`) and, crucially, get `coverage-contexts` green so an
   artifact exists.
3. Treat a red Master Gate as stop-the-line for landing epics. If the gate is ignored,
   the scoped lane has no backstop, and the only safe agent behavior becomes "always run
   the full suite". That is exactly the capacity drain the two-speed decision exists to
   prevent.

**Success metric:** Master Gate green rate ≥ 90% over 7 days; at least one
`sase-coverage-contexts-<sha>` artifact per day.

### Step 2 — Take the tax off the governed lane (days)

1. First, run the A/B on an idle host: `just test-cost` against `just test` at the same
   SHA and worker width. This confirms the detector attribution in §1.2.
2. Change `check-full` to run the fast lane with the cheap timing recorder and the
   committed cost budgets. Move `--sase-detect-global-leaks --sase-fail-on-global-leaks`
   into a Full CI job, which already runs every 2 hours and already gates release through
   `ci_watch` freshness. This follows the same rule `ci-two-speed-split` already accepted:
   an exhaustive signal may lag by ≤2 h in exchange for keeping it off the push path.
3. Optionally follow with B′ (an incremental snapshot) so detection can come back on
   every landing at negligible cost.
4. Do the fixed-overhead fixes from §1.4 (option C):
   - Patch the runner-limit override at its source module only, or behind a lazy check.
   - Disable the inline-snapshot report unless snapshots were used.
   - Enforce this with a small test asserting that a trivial non-TUI test process does
     not import `textual`. The existing `test_chop_import_budget.py` shows the pattern.

**Expected result on apollo:** `check-full` test stage about 95 min → ~17–20 min at
7 workers, and about 9–10 min at 14. Trivial single-file runs ~10 s → ~3 s. Host-wide,
each full run frees roughly 30,000 CPU-s, which is capacity sibling agents get back.
**Reliability change:** leak detection moves from "every landing" to "every 2 h, still
release-gating". Nothing is removed.

### Step 3 — Amortize the Textual lifecycle (2–6 weeks, incremental)

Drive the work from the cost recorder's existing per-file cause data. The top 100 files
carry 55.6% of shard time, and they are overwhelmingly `tests/ace/tui/*`:

- **Migrate high-node-count AcePage modules to `AcePageGroup`.** Keep the forced-isolation
  lane as a mandatory Full CI job; it already exists. Each migrated module turns N × 2.25 s
  of page enters into roughly one enter plus cheap checkouts.
- **Reuse parsed stylesheets for plain `App.run_test` widget tests** (3,684 enters at
  0.37 s), not just the AcePage fast policy.
- **Replace numeric `pilot.pause(delay)` and `asyncio.sleep(n)` in tests with the
  event-driven settle barrier.** Extend the `_lint-test-waits` gate to reject new
  numeric pauses. This removes wall time and a known source of timing flakes at once.
- **Ratchet `tests/perf/baselines` budgets downward** after each batch, so gains cannot
  silently regress.

**Target:** cut Textual-attributed time (4,388 s) by half. That is about 30–35% of total
item wall, and it compounds with step 2.

### Step 4 — Make the scoped lane a real accelerator (1–3 weeks)

This work only makes sense once steps 1–2 are done: the contexts baseline exists, and the
full lane is cheap enough to be an honest crossover.

- **Per-host crossover.** Replace the athena constant `FULL_LANE_WALL_SECONDS = 232` with
  a crossover computed from the host's own recent full-lane records and granted width.
  Keep the constant as a fallback.
- **Stop needless `core-identity-changed` escalations.** Escalate only when the installed
  `sase_core_rs` *digest* differs from the baseline's, not when a workspace merely
  reinstalled the same wheel.
- **Keep contexts fresh host-locally.** Either `just refresh-contexts-baseline` as part of
  workspace provisioning, or a low-priority host job running `just test-contexts` when
  the token pool is idle, so a CI outage no longer blinds selection.
- **Drive the false-negative count to zero.** Every recorded miss becomes a selection
  rule or a data-asset mapping, starting with the lumberjack cluster, which suggests a
  subprocess/script dependency the import graph cannot see.

**Success metrics:** escalation rate < 25%; median scoped wall < 5 min; zero new false
negatives per week; `selection-health` "slower than full lane" < 5% of runs.

### What I would *not* do

- **Buy capacity first.** A 48-vCPU box would turn a 95-minute wasteful run into roughly
  a 30-minute wasteful run, at recurring cost. After steps 2–3, apollo alone should be
  adequate for the agent loop. Routing Full CI-grade local lanes to athena remains a
  cheap option if still needed.
- **Adopt Pants/Bazel or testmon now.** Both duplicate a selector that already exists and
  already has health tooling. Its current failure is missing inputs (no contexts baseline,
  athena-calibrated constants, red CI), not a missing mechanism.
- **Drop the leak detector, the isolation lane or TUI e2e tests to "save time".** They
  protect exactly the shared-state and TUI regressions this codebase is prone to. The
  goal is to move them, not delete them.

### Why this is the best trade-off

- It attacks measured waste before necessary work: the detector tax, fixed per-process
  imports, fixed-delay pauses, and repeated app startup.
- It restores the one precondition (a green, hermetic CI) that makes every
  speed-over-exhaustiveness shortcut in the existing architecture safe.
- It reuses the project's own instruments (`test-cost` causes, cost budgets,
  `selection-health`, the AcePageGroup isolation lane) as ratchets, so the gains are
  measurable and cannot silently regress.
- It stays inside accepted decisions: `two-speed-verification`, `ci-two-speed-split`, and
  `rust-core-required`. No decision needs reopening.

---

## 5. Risks and Validation Items

1. **Detector attribution** (§1.2) is inferred from recording data plus micro-benchmarks.
   Validate it with the step-2 whole-suite A/B before changing `check-full`.
2. **Host noise.** Every timing here came from a shared, busy apollo. Repeat key
   measurements while the suite gate pool is idle.
3. **Moving detection to a 2 h lane** means a poisoning regression can land and be caught
   later. Mitigate by making the scheduled job page through `ci_watch` like other
   release-gating signals, or by landing B′.
4. **AcePageGroup migration** can mask order dependence. The forced-isolation lane must
   stay required in Full CI, and migrated modules should be spot-run under
   `test-contention`.
5. **The CI identity fix** could expose tests that silently relied on the host's global
   git config for other settings (for example `init.defaultBranch` or signing). Expect a
   short triage pass — this is the correct direction for hermeticity.

---

## Sources

- Repo files: `Justfile` (`check`, `check-full`, `test-*` recipes), `tools/run_pytest`,
  `tests/_suite_gate_budget.py`, `tests/_test_selection*.py`, `tests/_test_cost_plugin.py`,
  `tests/_global_state_leak_detector.py`, `tests/_global_state_leaks/fingerprints.py`,
  `tests/_config_reader_probe.py`, `tests/_conftest_runtime.py`, `tests/conftest.py`,
  `src/sase/ace/testing/ace_page_group.py`, `tests/shard_timings.json`,
  `tests/perf/baselines/test_cost_baseline.json`,
  `.github/workflows/{master-gate,ci,full}.yml`.
- Commits: `6385a8ebb` (detector gates the cost lane), `b5b5ded84` / `ee9603d31` (cost
  lane and budgets), `5d8872f4d` / `840dd3eb4` (Master Gate / Full CI split).
- Local data: `just selection-health` / `tools/selection_health --json`; cost recording
  `20260906T041026Z-3088222.json`; GitHub Actions run history via `gh run list/view`
  (Master Gate and Full CI conclusions, job-level failure logs).
- SASE memory: `lint_and_test.md`, `decisions:two-speed-verification`,
  `decisions:ci-two-speed-split`, `decisions:rust-core-required`, `tailnet.md`.
- Prior research: `202604/test_suite_speedup.md`, `202605/just_check_speed_research.md`,
  `202609/temporary_high_capacity_test_machine.md`.
- External: [pytest-testmon](https://github.com/tarpas/pytest-testmon) and
  [testmon v1.4 xdist support](https://www.testmon.org/blog/v14-with-xdist-support-is-out/);
  [Pants dependency inference and caching](https://www.pantsbuild.org/blog/2020/10/29/dependency-inference);
  [pytest-xdist docs](https://pytest-xdist.readthedocs.io/en/latest/).
