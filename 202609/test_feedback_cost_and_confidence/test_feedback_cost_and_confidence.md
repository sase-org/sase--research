# Faster SASE Test Feedback With Trustworthy Verification

Research consolidated on 2026-09-12. Lead inspection: SASE revision
`072d657ab75d67d4b613393933474176a86d3a29`; both independent reports examined
`e1a2f7839502dd228fc4ab29687c4256f3cf055c`. The relevant detector, selector, and CI
implementations are unchanged between those revisions.

**The best investment is to remove repeated verification work while preserving the
existing correctness gates.** Start with green, reproducible CI and direct measurement
of the global-state leak detector. Then reduce expensive test setup, imports, and
synchronization. Repair selection inputs and calibration, and benchmark file-based
execution before considering a runner replacement. Larger machines or a build-system
migration are secondary choices.

This conclusion combines
[researcher A's executor and harness investigation](test_feedback_cost_and_confidence__a.md),
[researcher B's detector profiling and selection investigation](test_feedback_cost_and_confidence__b.md),
and the lead's independent inspection of code, raw timing records, and current CI logs.
The lead did not run another exhaustive suite: the existing recording and targeted
source checks establish priorities, while a controlled full-suite experiment remains
necessary to establish the achievable speedup.

**What is already in place.** SASE already has scoped local tests, a bounded worker
pool, historical timings, eight outer CI shards, xdist, cost budgets, coverage contexts,
and specialist visual, isolation, and contention lanes. `just check` runs whole-repo
lint and scoped tests. `just check-full` runs lint and `test-cost`, including blocking
leak detection. Scoped escalation instead enters the **fast** full-inventory lane; it
does not automatically incur the cost lane's detector overhead. Master Gate also runs
the fast inventory, not leak detection. Scheduled Full CI covers the broader matrix.
These distinctions matter: a remedy for slow landing verification will not necessarily
accelerate a slow scoped check or Master Gate.

The accepted `two-speed-verification` and `ci-two-speed-split` decisions already
recognize shared-host capacity as the constraint. The useful next question is which work
to eliminate, rather than whether to introduce a fast lane.

**The strongest measurements.** The lead independently read the retained cost record
`20260906T041026Z-3088222.json` through the project's telemetry modules. It identifies
host `apollo`, cost mode, and seven workers. It contains no directly usable source SHA,
so it is historical evidence rather than a benchmark of today's checkout.

| Observation                                                                                        | Evidence                                                        | What it means                                                                                  |
| -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| 38,700 nodes in 3,516 attributed files                                                             | September 6 recording; independently verified                   | A large inventory, but size alone does not explain the runtime.                                |
| 94.5 minutes controller wall time                                                                  | 5,670.7 seconds in that recording                               | This is a cost-lane measurement, not the duration of every full test command.                  |
| 37,864.7 aggregate process CPU seconds, versus 4,681.4 attributed to tests and 326.0 to collection | Same record; aggregate includes a small controller contribution | About 32,857 seconds, or 86.8%, sit outside those two measured buckets.                        |
| 710 AcePage entries; 3,684 Textual app entries                                                     | Same record                                                     | Repeated application lifecycle work is a substantial target.                                   |
| 328.1 aggregate collection seconds                                                                 | Same record, about 47 seconds per worker                        | Repeated collection matters, but is under 1% of this recording's aggregate CPU.                |
| About 547 MiB median and 1.51 GiB peak process RSS                                                 | Same record                                                     | Raising worker counts has a meaningful memory cost.                                            |
| 47 escalations out of 85 scoped records; 38 un-escalated records have a 19.6-minute median         | Lead's fresh read; A/B previously saw 46 of 84                  | The local fast path is often neither small nor fast. The duration median excludes escalations. |
| Median selection: 638 test **files**; 42 baseline-missing events                                   | Lead's fresh read                                               | A's description of selected “nodes” is incorrect. Coverage-context availability is a real gap. |

B's small experiment increased a 112-test file from 7.7 to 27.3 seconds with leak
detection. B also measured roughly 0.24 seconds per snapshot after loading about 4,350
SASE modules. These are useful researcher measurements, not independently repeated
whole-suite results. Both reports' broader timing comparisons span different dates, host
conditions, and instrumentation; they should guide ranking, not promises.

**The detector is the first performance hypothesis to test.** In
`tests/_global_state_leak_detector.py`, `pytest_runtest_protocol` is a `tryfirst`
hookwrapper. It snapshots all loaded SASE module globals before and after every test,
then compares fingerprints. The cost recorder's wrapper lacks `tryfirst`, so the
snapshot and comparison work surrounds its timer. This matches pytest's documented
[hook-wrapper ordering](https://docs.pytest.org/en/stable/how-to/writing_hook_functions.html#hook-function-ordering-call-example).
The implementation therefore explains why tests can look relatively cheap while the
processes remain CPU-bound.

The lead confirms the mechanism, not the claim that all unexplained CPU belongs to that
detector. Other hooks, reporting, instrumentation, and garbage collection may
contribute. Dividing 6,407 attributed seconds by seven yields about 15.3 minutes of
idealized test work; collection, imbalance, startup, shutdown, and remaining hooks must
still be added. B's proposed 95-to-20-minute improvement is a plausible hypothesis, not
an established outcome.

A direct experiment should distinguish four configurations: ordinary fast execution,
cost recording alone, leak detection alone, and both. Keep the SHA, installed Rust
wheel, node inventory, worker width, ordering, and host class fixed. Measure controller
wall time, aggregate CPU, peak simultaneous memory, and explicit snapshot/diff time;
include child-process resource use where possible. Start with representative files, then
run repeated full-inventory comparisons under the existing capacity gate. Merely
comparing `test` with `test-cost` conflates two plugins and their interaction: the cost
plugin itself imports modules that the detector subsequently scans.

**Several attractive claims need correction before they become implementation work.**

| Claim in the independent reports                                                       | Consolidated finding                                                                                                                                                                                                                     |
| -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TUI lifecycle accounts for exactly 68.5% of test time; halving it saves 30–35% overall | The cause timers overlap: AcePage entry contains app entry and settling, and settling contains pauses. A explicitly warned against adding them. Keep the hotspot ranking; discard the additive percentage and derived saving.            |
| The 13,751 recorded numeric pauses are fixed sleeps                                    | `_pause_cause` labels every non-`None` delay, including zero, as `pilot_pause_delay`. `settle_pilot` already uses two zero-delay drains and a rendered-frame barrier. The 532 seconds cannot be treated as removable sleep time.         |
| Reinstalling the same Rust wheel unnecessarily changes its identity                    | `tools/validate_test_environment` already content-hashes the extension. The broadening rule compares several environment buckets. Inspect the changed buckets; do not replace existing digest logic or suppress real dependency changes. |
| Failed coverage jobs cannot publish a baseline                                         | `coverage-contexts` already uploads with `if: always()`. The current run attempted upload but found no `.coverage` file. Repair both execution and the producer/output path.                                                             |
| Replace `test-cost` with cheap timings and keep existing cost budgets unchanged        | Those budgets consume cost recordings, including cause counts and CPU/RSS fields. The checker otherwise defaults to the latest retained recording. Cheap timings alone cannot establish that today's tree meets those budgets.           |
| Two modules have adopted shared AcePage fixtures                                       | The migration manifest contains one consumer module. Additional helper references are not additional migrated coverage.                                                                                                                  |

These corrections favor a focused optimization program over optimistic headline
speedups. They also expose a measurement gap: current CPU budgets emphasize test-item
and collection CPU, so a large outer-hook regression can escape the main cost metrics.
Add fresh, revision-bound whole-process and detector-specific measurements before
ratcheting a new baseline.

**Restore a usable correctness signal first.** The lead rechecked Master Gate run
[34716393016](https://github.com/sase-org/sase/actions/runs/34716393016), attached to
the inspected SHA. It failed after about seven minutes with `Author identity unknown` in
artifact-link tests. The latest ten completed Master Gates sampled all failed. The
latest five completed scheduled Full CI runs also failed.

In [Full CI run 34711185377](https://github.com/sase-org/sase/actions/runs/34711185377),
the lead confirmed missing `provider_pool_eligibility_mask` bindings, a failed coverage
job after roughly 56 minutes, a cost job cancelled near 90 minutes, and the missing
`.coverage` upload. This corroborates A/B's diagnosis without assuming their earlier
failure counts remain current.

Give temporary Git repositories deterministic, test-owned configuration and identities,
with explicit overrides for identity-sensitive tests. Validate the installed Python/Rust
binding contract before expensive jobs start. A binding check already exists in lint;
repairing a broken pin and ensuring consumers fail early is more useful than proposing
the same check again. Verify coverage database production, artifact upload, and local
installation end to end. A passing check on an unrelated or stale tree is insufficient.

**Preserving coverage is different from preserving detection guarantees.** B's fastest
proposal moves leak detection entirely from landing checks to scheduled CI. That keeps
the detector's code but allows state-poisoning regressions to land before it runs. The
existing two-speed decision does not automatically authorize every further demotion. The
default recommendation retains the current required detector until a cheaper
implementation has demonstrated equivalent findings.

If delayed detection becomes an acceptable product decision, a scheduled-only detector
is an alternative with potentially large savings. State its cost explicitly: detection
lag includes scheduling, queues, execution, and outages. A two-hour cron is not a
two-hour detection guarantee; the sampled Full CI itself takes about 101 minutes. GitHub
also documents that
[scheduled runs can be delayed](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
A release gate based on recent success is also different from proving each landing's
exact tree. Require freshness enforcement and a recovery owner before making that trade.

**The practical sequence is bounded and measurable.**

1. **Establish green baselines and separate feedback milestones.** Record time to first
   actionable failure, completion of selected tests, full fast-inventory completion,
   completion of required landing checks, and total resource demand. Show available
   results promptly while verification continues; avoid launching a duplicate full suite
   solely to obtain an earlier status. Preserve the existing agent-default `just check`
   policy. Any required long verification continues through the project's monitor flow.

2. **Measure and reduce detector and startup overhead.** Use the four-way experiment
   above, then optimize the dominant snapshot/fingerprint operations with the existing
   detector as a comparison oracle. Preserve per-test poisoning detection, environment,
   path, cache, and thread coverage. A cache keyed only by a module or dictionary's
   identity is unsafe: an in-place mutation leaves that identity unchanged. Per-file
   snapshots also miss leaks a later test cleans up. Require mutation cases and
   comparison runs before accepting either shortcut. Independently remove the autouse
   fixture's unconditional import of `models_panel`, which loads TUI code for unrelated
   tests. B's snapshot-report startup finding merits profiling, while preserving
   snapshot verification and reports when used.

3. **Reduce measured harness work by file rank.** Extend `AcePageGroup` only to
   compatible high-cost modules, with an explicit reset contract and module-scoped event
   loop. Preserve cold-start tests and compare shared versus fresh-page execution for
   every migrated module, including order and contention checks. Replace redundant waits
   with bounded waits for the actual state or rendered frame; retain deliberate timing
   tests. Replace repeated full-repository scans inside tool unit tests with small
   fixtures while retaining one real-repository validation. Remove nested whole-suite
   collection where outer collection already provides the needed inventory. Keep
   subprocess tests wherever process isolation, environment, signals, or CLI behavior is
   the assertion.

4. **Repair selection before pruning further.** Supply usable coverage contexts, retain
   their union with static dependencies, and calibrate runtime estimates against recent
   full **fast** runs on the same host class and worker width. The current 232-second
   threshold originated on athena at 28 workers and is also used for serial escalation;
   it is a poor counterfactual for apollo. Include queue/admission costs without
   increasing host-wide worker demand. A/B report 19 selection-health false-negative
   records; the correlation allows an ancestor selection and later full-run superset, so
   replay them on matched revisions before calling all 19 proven causal misses. Add
   regression cases for confirmed failures. Retain conservative mappings for Rust
   bindings, data assets, subprocesses, and dynamic imports, which Python coverage alone
   cannot prove safe.

5. **Benchmark executor changes after attribution.** A's balanced plain-pytest process
   proposal is worth a prototype. First compare xdist's `loadfile` against current
   scheduling for app-sharing modules; it guarantees file affinity without replacing
   orchestration. Then compare disjoint file lists executed by a bounded number of
   `pytest -n0` processes.
   [Xdist collects separately in each worker](https://pytest-xdist.readthedocs.io/en/stable/how-it-works.html),
   and
   [its distribution modes](https://pytest-xdist.readthedocs.io/en/stable/distribution.html)
   trade load balance against fixture affinity. Smaller import universes may also reduce
   detector cost, but that effect is unmeasured. Include any authoritative collection
   pass in benchmark cost. Preserve exact node-ID multiset, outcomes, skip/xfail
   behavior, failure propagation, isolated output paths, and report merging. Retain
   order-diverse checks: identical node IDs alone do not prove equivalent isolation or
   plugin behavior.

The first two steps should be investigated before commissioning a broad executor
rewrite; the later steps can be accepted in small batches. Presentation and test-harness
changes belong here. If implementation changes shared backend/domain behavior, follow
the existing Rust-core boundary rather than creating Python-only behavior for tests.

**Decision criteria.** Use the same representative workloads before and after each
change. Compare medians and tails under controlled capacity, then verify performance
under normal contention. Record versions and the installed native extension digest.
Treat these as initial acceptance targets, not forecasts:

| Dimension          | Suggested criterion                                                                                                                               |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Correctness        | Required checks green for the tested tree; no unexplained lost nodes or detector findings; migrated TUI modules pass fresh-page and order checks. |
| Inner loop         | At least 50% lower median scoped feedback, followed by a sub-five-minute target for ordinary changes; report p90 and escalation separately.       |
| Resource use       | At least 30% lower measured CPU demand for representative full verification, without higher peak aggregate memory or more worker tokens.          |
| Executor promotion | At least 20% lower full-run wall time or a material measured resource reduction; retain reproducible results and existing capacity control.       |
| Selector health    | Fresh usable contexts in over 95% of eligible runs; zero unexplained misses across a representative matched-revision comparison window.           |
| Regression control | Fresh records bound to code, environment, mode, and worker width; explicit budgets for whole-run overhead as well as test bodies.                 |

More hardware can help remaining queue pressure after these changes; it does not remove
repeated scanning, imports, or lifecycle work. Bazel/Pants or result caching would
require well-defined inputs across Python, Rust, filesystem state, subprocesses, and
plugins. They are substantial alternatives if reproducibility and dependency boundaries
become an independent problem, rather than the first response to this profile.
Repository splitting would introduce integration boundaries without addressing the
measured tax. Likewise, A's suggestion to revisit CI admission merits later measurement:
per-SHA service time exceeding inter-arrival time alone does not prove overload when
jobs run concurrently. Measure arrival rate, runner-minutes per revision, and available
capacity before changing the accepted per-SHA policy.

For audit and reproduction, the original inputs were consumed with `sase artifact read`:
A is `research.1.cdx`, originally
`research:202609/sase_test_feedback_acceleration__a.md`, immutable snapshot
`file:explicit:f4acb6d70afe4e3b0e4a269e`; B is `research.1.cld`, originally
`research:202609/test_feedback_loop_speed_and_reliability__b.md`, immutable snapshot
`file:explicit:0d4135789f6576c6f14bf606`. Their local copies were moved into this
directory with suffixes and bytes preserved. No predecessor chat transcripts were used.
Primary local evidence additionally includes `Justfile`, `tools/run_pytest`,
`tools/validate_test_environment`, `tools/check_test_cost_budgets`,
`tests/_test_cost_plugin*.py`, `tests/_global_state_leak_detector.py`,
`tests/_global_state_leaks/fingerprints.py`, `tests/_test_selection*.py`,
`tests/_conftest_runtime.py`, `src/sase/ace/testing/settle.py`, the AcePageGroup
manifest, and the inspected GitHub workflow files. The cited decision records were read
through SASE memory's audited interface.

**Recommended solution:** keep SASE's two-speed verification architecture and fund a
focused cost-reduction effort: restore green CI and working context artifacts, measure
and optimize the leak detector without weakening its required checks, then eliminate
expensive repeated imports, app setup, scans, and waits. Recalibrate scoped selection
and promote file-based execution only when comparative evidence supports it. This
combines B's strongest diagnosis with A's strongest harness ideas while preserving
correctness evidence. Treat a fivefold improvement as a hypothesis to test, and
scheduled-only leak detection as an explicit alternative with delayed detection—not as a
prerequisite for faster feedback.
