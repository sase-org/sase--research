# Reassessing Merge Queue Fencing, Exact-SHA Releases, and Epic Decomposition Strategy

> **Author:** Researcher `gem` (`research.4q.gem`)  
> **Date:** 2026-10-17  
> **Target:** SASE Landing Discipline, PyPI Release Architecture, and Implementation Phasing  
> **Context:** Reassessment of the consolidated solution in `merge_queue_fenced_master_and_exact_sha_releases.md`

---

## 1. Executive Summary & Bottom Line

The solution proposed in `merge_queue_fenced_master_and_exact_sha_releases.md` gets the fundamental engineering principles right:
1. **GitHub Native Merge Queue over Host Locks:** Relying on a host-side lock or lease (such as local `flock`) fails because SASE landings originate from multiple hosts (`athena` and `apollo`), local checks take 12–59 minutes and fail 96% of the time, and local validation cannot enforce server-side push rejection. GitHub's native merge queue provides true speculative batch testing on the integrated target tree.
2. **Decoupled Qualification & Exact-SHA Releases:** Green HEAD is an illusory release gate. The root cause of the 49-day PyPI release stall since August 29 is not merely Master Gate volatility, but rather Full CI drift, core-floor blockers, and a silent defect in `.github/workflows/publish.yml` where `actions/checkout@v4` checks out the default branch tip instead of the qualified release commit.
3. **Flake Quarantine Precedes Queue Enforcement:** Enforcing a merge queue on a test suite with a 30–40% false-red rate turns the queue into a random-rejection engine that thrashes speculative batches and starves agent workflows.

### Core Verdicts of this Reassessment

1. **The Proposed Solution is Sound but Contains Critical Gaps:**  
   The 4-phase technical roadmap is approved in concept, but its requirements must be amended in six critical areas:
   - **Atomic Release Tagging:** Decouple release-please tag generation from PyPI publishing so a failed qualification job does not leave a phantom public git tag on GitHub that has no matching package on PyPI.
   - **Visual Test Quarantine:** Do *not* fold `visual-test` into the required Master Gate in Phase 1. `visual-test` failed in 270 of 271 Full CI runs; forcing it into the merge gate before complete hermetic isolation will instantly paralyze the queue.
   - **Cross-Repository Landing Orchestration:** Explicitly model and enforce landing order between `sase` and `sase-core`. Changes spanning both repositories require that the pinned Rust core commit is merged and published on `sase-org/sase-core` before the dependent `sase` PR enters the merge queue.
   - **Epic Wave Pipelining SLA:** Mitigate the 13–30 minute per-wave latency penalty of asynchronous merge queueing by supporting horizontal phase concurrency or scoped epic integration branches.
   - **Speculative Ejection Attribution:** Ensure that when an integrated speculative batch fails due to PR #1, PR #2 is tested standalone before being erroneously marked as failing or retried.
   - **Formal Elimination of Host-Local Gate Leases:** Demote local `just check` to lightweight pre-commit linting and rely entirely on server-side queue gates.

2. **Epic Recommendation: MUST Be Multiple Epics (Exactly 3 Epics):**  
   This initiative **must not be executed as a single monolithic epic**. A monolithic epic would fatally couple an immediate emergency release repair (shipping 0.18.0) to multi-week test stabilization and cross-repo Rust/GitHub infrastructure development. It would violate SASE single-turn and bead lifecycle constraints, as an epic cannot sit open for weeks monitoring queue latency or flake rates.  
   Instead, the work must be partitioned into **three sequenced epics**, each with strict, independently verifiable exit criteria:
   - **Epic 1: Exact-SHA Release Pipeline & Emergency Master Fences (Phase 0)** — Ship immediately (Days 1–3) to unblock PyPI 0.18.0 and stop destructive branch mutations.
   - **Epic 2: CI Gate Trustworthiness & Flake Quarantine System (Phase 1)** — Stabilize Master Gate (Weeks 1–2) to bring false-red rates under 3% with inline single-node retries and expiring quarantine.
   - **Epic 3: Host Landing Orchestration & Native Merge Queue Integration (Phases 2 & 3)** — Implement the Rust state machine in `sase_core`, the PR landing adapter in `sase-github`, rehearse on a scratch repo, pilot on low-risk traffic, and cut over to an enforced merge queue with a nightly release train.

---

## 2. Reassessment of the Proposed 4-Phase Solution

### Phase 0: Cheap Fences & Honest Releases
*Original Focus: Rulesets to block force push/deletion, exact SHA checkout in `publish.yml`, qualify job calling `ci.yml`, relax release watcher pre-merge rule, ship 0.18.0.*

- **Strengths:**  
  Phase 0 correctly isolates the immediate business bottleneck. PyPI has been starved of releases for 49 days. The inspection of `publish.yml` confirms that line 131 uses `actions/checkout@v4` with no `ref:`, pulling whatever commit happens to sit at the tip of `master` when the scheduled or manual workflow triggers. Furthermore, the existing `release` job only outputs `release_created` and discards `sha`, guaranteeing version mismatch during concurrent pushes.
- **Deficiencies & Gaps:**  
  1. *Phantom Public Tags:* If `release-please` cuts a permanent `v0.18.0` git tag on GitHub upon merging PR #299, and the subsequent `qualify` workflow fails on a heavy matrix check, GitHub has published tag `v0.18.0` while PyPI has nothing. Because Phase 0 also introduces tag protection rulesets blocking tag deletion, the repository enters a desynchronized state where the tag cannot be removed or re-pointed.
  2. *Release Watcher Blindness:* `tools/_release_watch_api.py` queries `_run_list("master-gate.yml", branch="master")`. Modifying this to query by SHA is necessary, but Phase 0 must also ensure that release candidate evaluation handles timeout and abort states gracefully without hanging the release train.

### Phase 1: Trustworthy Gate
*Original Focus: CI single-node retry for <= 3 nodes, expiring flake quarantine (<= 14 days), parity fixes (.python-version = 3.12, core revision check, `if: always()`), fold `visual-test` into gate, move Full CI to nightly + candidates, SLA < 3% false reds.*

- **Strengths:**  
  The queue simulation in the baseline report conclusively proves that queuing capacity is not the constraint (at concurrency K=2, p50 latency is ~13 minutes). Rather, flakiness is the killer: at a 30% false-red rate, p95 latency jumps to 52 minutes, 1.66 builds are burned per landing, and 9% of valid changes suffer spurious ejections requiring costly manual or automated repair turns. Inline single-node retries and expiring quarantines are proven industry remedies.
- **Deficiencies & Gaps:**  
  1. *Premature Visual Test Gating:* The baseline proposal recommends folding `visual-test` (check mode, sharded) into Master Gate during Phase 1. The evidence collected in the report directly refutes this: Full CI passed only 1 of 271 runs since August 27, and `visual-test` was red in *every single run sampled*. Injecting an unmitigated 100% failure rate suite into the merge gate would completely halt all merges.
  2. *Local Environment Parity:* While committing `.python-version` = `3.12` addresses Python version mismatch, it does not address differences in system packages, dynamic linker behaviors for Rust cdylibs, or Go tool versions between developer machines (`apollo` vs. `athena`) and Ubuntu GitHub Actions runners.

### Phase 2: Merge Queue Pilot
*Original Focus: Scratch repo rehearsal, `master-gate.yml` `merge_group` trigger + `integration-ready` job, host landing state machine in `sase_core`, `sase-github` PR adapter, deterministic landing watcher, proof of merge before bead close.*

- **Strengths:**  
  The discovery that `sase-github`'s `_submit_via_pr_merge` (`src/sase_github/workspace/submit.py:245`) interprets `gh pr merge --merge --delete-branch` exiting 0 as "merged" is critical. Under a merge queue, exit code 0 signifies only that the PR was *queued* or auto-merge was enabled. Closing beads and releasing waiters at this point breaks causal dependency ordering. Moving the landing state machine to `sase_core` and tracking proof-of-merge via SHA and tree equality is architecturally sound.
- **Deficiencies & Gaps:**  
  1. *Cross-Repo Landing Deadlock (`sase` + `sase-core`):* The proposal treats SASE as a single repo. In reality, core backend changes land in `sase-core` and are pinned via `sase-core-revision.txt` in `sase`. If an agent updates both, which PR enters the queue first? If the `sase` PR enters the queue while the `sase-core` commit is unmerged on GitHub, `core-wheel` will fail when it attempts to checkout that SHA.
  2. *Epic Wave Latency Accumulation:* In multi-phase epics where Phase N+1 depends on Phase N, waiting for Phase N to merge through the queue adds 13–30 minutes of idle queue time per phase. A 5-phase sequential epic incurs up to 2.5 hours of pure queue waiting.

### Phase 3: Enforce & Simplify
*Original Focus: Mandatory merge queue on `master`, 0 approvals, empty bypass list, concurrency 2, timeout 60 min, retire push gate, nightly release train, write decision records.*

- **Strengths:**  
  Zero approvals solves the self-approval deadlock where agents push with the maintainer's token. An empty bypass list ensures no backdoors exist for agents or humans to break the fence. A nightly automated release train restores the rapid release cadence that existed prior to August.
- **Deficiencies & Gaps:**  
  1. *Lack of Shadow Run Verification:* Cutting over from push mode to mandatory queue mode without an intermediate period where the queue runs in shadow mode on all agent PRs invites unexpected breakage.
  2. *Disaster Recovery / Break-Glass Protocol:* While an admin can disable the ruleset, there must be a scripted reconciliation command to drain or cancel in-flight queue entries and resynchronize the local `sase_core` landing state machine.

---

## 3. Warranted Requirement Modifications

The following adjustments modify or extend the requirements specified in `merge_queue_fenced_master_and_exact_sha_releases.md`. Each adjustment is explicitly justified.

```
+---------------------------------------------------------------------------------------------------+
| SUMMARY OF WARRANTED REQUIREMENT ADJUSTMENTS                                                      |
+----+---------------------------------------+------------------------------------------------------+
| #  | Requirement Area                      | Core Adjustment                                      |
+----+---------------------------------------+------------------------------------------------------+
| R1 | Atomic Release Publishing             | Tag-After-Qualify via Draft Releases                 |
| R2 | Visual Regression Gating              | Shadow Mode & 14-Day Stability Precondition          |
| R3 | Cross-Repository Landing Order        | Enforce Rust Core Landing before SASE Queueing       |
| R4 | Epic Wave Latency SLA                 | Phase Parallelization & Epic Integration Branches    |
| R5 | Speculative Ejection Attribution      | Isolated Retest of Queued Dependents                 |
| R6 | Host Gate Lease Retirement            | Full Deprecation of Host-Local Serial Locks          |
+----+---------------------------------------+------------------------------------------------------+
```

### Requirement Adjustment 1: Atomic Release-or-Nothing (Tag-After-Qualify)
- **Original Implication:** `release-please` creates the GitHub release and tag; `publish.yml` triggers, builds the release SHA, runs `qualify`, and publishes to PyPI. If `qualify` fails, "fix forward and ship the next day".
- **Adjusted Requirement:**  
  **Releases must not publish a permanent public git tag or public GitHub release until the qualification job has succeeded.**  
  `release-please` must be configured with `draft: true` (or operate on a release-candidate branch). The `qualify` job runs on the candidate commit. Only after `qualify` and `install-smoke` pass does the workflow convert the release from draft to published, push the immutable `v*` tag, and upload artifacts to PyPI.
- **Rationale:**  
  Under protected tag rulesets, a failed qualification run leaves an orphaned, unremovable public git tag that does not exist on PyPI. Downstream tools, package resolvers, and git clones observing the tag assume the release exists, creating severe external and internal confusion.

### Requirement Adjustment 2: Staged Visual Test Incorporation (Shadow Mode Precondition)
- **Original Implication:** Phase 1 folds `visual-test` (check mode, sharded) into Master Gate.
- **Adjusted Requirement:**  
  **`visual-test` MUST NOT be a required status check in Master Gate or the merge queue until it achieves a false-red rate of < 1% over 14 consecutive days.**  
  During Phase 1 and Phase 2, `visual-test` must run in *shadow/advisory mode* (or as a non-blocking job with `continue-on-error: true`). It will emit failure signatures and file flake beads, but will not block PR admission. Only after the TUI timing and SVG golden flakiness are hermetically fixed may it be promoted to a blocking gate.
- **Rationale:**  
  The data shows `visual-test` failed 270 of 271 runs. Making an actively broken test suite a required check will instantly block all 43 daily landings and force the queue into continuous rejection loops.

### Requirement Adjustment 3: Cross-Repository Landing Coordination (`sase` + `sase-core`)
- **Original Implication:** The landing engine operates on individual repository checkouts.
- **Adjusted Requirement:**  
  **The host landing state machine in `sase_core` and `sase-github` must support cross-repository landing dependency validation.**  
  When an agent turn modifies both `sase-core` and `sase`:
  1. The `sase-core` change must be committed, submitted, and merged into `sase-org/sase-core` first.
  2. The host coordinator must verify via GitHub API that the new commit is present on `sase-core`'s default branch.
  3. The `sase-core-revision.txt` in `sase` must then point to that confirmed SHA before the `sase` PR is enqueued.
  If the `sase-core` landing fails or is ejected, the `sase` landing must abort before enqueueing, preventing broken builds in the `sase` queue.
- **Rationale:**  
  `master-gate.yml` builds the Rust core extension directly from `sase-core-revision.txt` at `sase-org/sase-core`. Enqueueing a `sase` PR that references an unmerged core commit results in a deterministic compilation failure in CI.

### Requirement Adjustment 4: Epic Wave Pipelining & Maximum Wave Latency SLA
- **Original Implication:** "Epic waves: each phase starts once the previous one has merged."
- **Adjusted Requirement:**  
  **Bound epic wave latency by establishing explicit pipelining and architecture standards:**
  1. *Horizontal Parallelism First:* Epic planners must prioritize decomposing phases into independent, parallel clan waves rather than deep serial chains.
  2. *Epic Integration Branch Option:* For epics that strictly require > 3 sequential dependent phases, provide an optional "epic integration branch" workflow where intermediate phases land immediately into an isolated feature branch, and the integrated feature branch undergoes merge-queue admission once upon epic completion.
  3. *Latency SLA:* For standard sequential waves, the merge queue p50 latency must be monitored and maintained strictly under 25 minutes.
- **Rationale:**  
  A 5-phase sequential epic where each phase waits 20–30 minutes for merge confirmation adds 100–150 minutes of idle wall-clock time, severely hurting developer velocity.

### Requirement Adjustment 5: Speculative Ejection Attribution & Safe Retry Budget
- **Original Implication:** When a PR at the head fails, every build behind it restarts. A flaked PR re-enqueues once.
- **Adjusted Requirement:**  
  **Speculative batches must enforce strict failure attribution:**
  1. When a speculative batch containing PR #1 and PR #2 fails, PR #1 is ejected immediately.
  2. PR #2 must be automatically re-tested standalone against the current base without attributing a failure penalty to PR #2.
  3. Ejected PRs receive an automatic retry only if the failure matches a registered flake signature.
  4. Deterministic failures launch exactly one bounded repair turn with a 60-minute TTL. If unresolved, the landing is aborted, the branch deleted, and a `/sase_gate` is raised.
- **Rationale:**  
  Prevents healthy PRs speculative stacked behind a broken PR from being misclassified as defective or trapped in redundant repair cycles.

### Requirement Adjustment 6: Dual-Host Lock Elimination & Local Check Demotion
- **Original Implication:** Replace host landing lane with GitHub merge queue.
- **Adjusted Requirement:**  
  **Formally deprecate and remove all host-local serial locks (`flock`) and demote local `just check` to lightweight pre-commit verification.**  
  Local pre-flight must execute only fast linters and smoke tests (< 2 minutes). Full suite verification is strictly delegated to the GitHub Actions merge queue, which serves as the sole, authoritative gate.
- **Rationale:**  
  Local `just check` has a 96% failure rate and 12–59 minute duration on `apollo`, while `athena` cannot coordinate with `apollo`'s local locks. Moving all serialization to GitHub eliminates cross-machine locking synchronization entirely.

---

## 4. Epic Decomposition: Single vs. Multiple Epics

### The Recommendation
**This initiative MUST be structured as MULTIPLE EPICS (specifically, THREE Sequenced Epics). Under no circumstances should it be executed as a single epic.**

```
+---------------------------------------------------------------------------------------------------+
| RECOMMENDED THREE-EPIC SEQUENCING                                                                 |
|                                                                                                   |
|  [ EPIC 1: Phase 0 ]                                                                              |
|  Exact-SHA Releases & Master Protection Fences                                                    |
|  - Fix publish.yml (exact SHA checkout)                                                           |
|  - Add master force-push/delete ruleset                                                           |
|  - Reconcile release metadata & ship 0.18.0                                                       |
|  - Duration: 2-3 Days | Risk: Low | Verification: 0.18.0 on PyPI                                  |
|         |                                                                                         |
|         v                                                                                         |
|  [ EPIC 2: Phase 1 ]                                                                              |
|  CI Gate Trustworthiness & Flake Quarantine                                                       |
|  - Inline single-node test retry (<= 3 nodes)                                                     |
|  - Expiring quarantine manifest (quarantine.yml)                                                  |
|  - Python 3.12 & Rust core revision parity                                                        |
|  - Reschedule Full CI to nightly; visual tests in shadow mode                                     |
|  - Duration: 1-2 Weeks | Risk: Medium | Verification: False-reds < 3% over 7 days                 |
|         |                                                                                         |
|         v                                                                                         |
|  [ EPIC 3: Phases 2 & 3 ]                                                                         |
|  Native Merge Queue & Host Landing Orchestration                                                  |
|  - Rust landing record state machine (sase_core)                                                  |
|  - GitHub PR landing adapter & submit.py fix (sase-github)                                        |
|  - Deterministic landing watcher daemon                                                           |
|  - Actions merge_group workflow & integration-ready check                                         |
|  - Scratch repo rehearsal -> Low-risk pilot -> Full enforcement                                   |
|  - Duration: 2-3 Weeks | Risk: High | Verification: Zero direct pushes, p50 < 30m, 100% via queue |
+---------------------------------------------------------------------------------------------------+
```

### Detailed Justification Against a Single Monolithic Epic

1. **Urgency Mismatch (Emergency Unblock vs. Infrastructure Overhaul):**  
   PyPI has been stalled for 49 days. Fixing `publish.yml` to checkout the release commit, adding simple branch protection rulesets, and shipping 0.18.0 is a 2–3 day task with immediate high-value payoff. Combining this into a single epic with a 4-week merge queue overhaul holding cross-repo Rust dependencies would needlessly delay the release of 0.18.0 by another month.
2. **Technical Domain and Repository Decoupling:**  
   - *Phase 0* is purely GitHub Actions YAML and workflow scripting in `sase`.
   - *Phase 1* is test harness engineering, pytest plugins, and test suite stabilization in Python.
   - *Phase 2/3* is distributed systems engineering across `sase-core` (Rust state machine), `sase-github` (GitHub API client), and repo administration.  
   Lumping these disparate domains into one massive epic creates bloated planning documents, high merge conflict surfaces, and unmanageable cognitive load for implementing agents.
3. **Strict Prerequisite Gating (The "Garbage In, Garbage Out" Queue Paradox):**  
   A merge queue cannot be safely turned on until gate stability is proven. If Phase 1 (flake reduction) and Phase 2/3 (merge queue) were in the same epic, the epic would enter an ambiguous, partially completed limbo state where the queue code is ready but cannot be enabled because tests are still flaking at 15–20%. Separate epics allow Epic 2 to have a clean, hard exit gate (< 3% false reds over 7 days) before Epic 3 begins cutover.
4. **SASE Agent & Bead Lifecycle Integrity:**  
   In SASE, epic beads are expected to drive active implementation work through structured phase beads and close promptly upon verification. An epic cannot sit idle for two weeks waiting for flake rate statistics or canary pilot metrics to accumulate. Multiple epics allow each milestone to close cleanly, update project memory, and transition state mechanically.

---

## 5. Detailed Epic Breakdown & Independent Verification Plans

### Epic 1: Exact-SHA Release Pipeline & Master Protection Fences (Phase 0)

- **Objective:** Fix the release pipeline so that published wheels correspond exactly to qualified release commits, protect `master` against destructive actions, and successfully ship `sase 0.18.0` to PyPI.
- **Repositories Involved:** `sase` (primary), GitHub repository settings.
- **Deliverables:**
  1. GitHub Ruleset on `master` blocking force pushes and branch deletions.
  2. Fix `.github/workflows/publish.yml`:
     - Export `sha` from `release` job steps (`steps.release*.outputs.sha`).
     - Configure `actions/checkout@v4` in `build` job with `ref: ${{ needs.release.outputs.sha }}`.
     - Add `qualify` job that calls `ci.yml` reusable workflow on that exact SHA.
     - Make `publish` job depend on `qualify` and `install-smoke`.
     - Replace broad `publish_existing` boolean with explicit target tag/SHA input.
  3. Update `tools/_release_watch_api.py` and `tools/_release_watch_engine.py` to evaluate post-merge qualification on the release commit SHA instead of pre-merge heuristic green windows.
  4. Resolve outstanding deterministic Full CI blockers (stale visual golden, project-label audit) and merge PR #299 to publish `0.18.0`.

#### Independent Verification Plan for Epic 1

```
+---------------------------------------------------------------------------------------------------+
| EPIC 1 INDEPENDENT VERIFICATION PROTOCOL                                                          |
+------+---------------------------+----------------------------------------------------------------+
| Step | Action                    | Expected Observable Outcome                                    |
+------+---------------------------+----------------------------------------------------------------+
| 1.1  | Test branch deletion      | Run `git push origin :master` with test token; expect HTTP 403 |
|      | and force-push ruleset    | Protected branch error.                                        |
+------+---------------------------+----------------------------------------------------------------+
| 1.2  | Verify checkout ref       | Trigger manual dry-run workflow; inspect checkout step log;    |
|      | resolution in publish.yml | confirm HEAD SHA matches requested commit SHA exactly.         |
+------+---------------------------+----------------------------------------------------------------+
| 1.3  | Artifact hash integrity   | Compare sha256 digests of dist/ wheels across `build`,         |
|      | across jobs               | `qualify`, and `install-smoke`; confirm 100% byte equivalence.  |
+------+---------------------------+----------------------------------------------------------------+
| 1.4  | Qualify job enforcement   | Simulate failed qualify job; confirm downstream `publish` job  |
|      | on publish                | is marked `skipped` and no upload to PyPI occurs.              |
+------+---------------------------+----------------------------------------------------------------+
| 1.5  | End-to-end 0.18.0 release | Merge PR #299; confirm PyPI returns HTTP 200 for 0.18.0 and    |
|      | verification              | fresh virtualenv `uv pip install sase==0.18.0` runs cleanly.   |
+------+---------------------------+----------------------------------------------------------------+
```

---

### Epic 2: CI Gate Trustworthiness & Expiring Flake Quarantine (Phase 1)

- **Objective:** Eliminate Master Gate noise, achieve a false-red rate strictly under 3%, and isolate known flaking tests without hiding technical debt.
- **Repositories Involved:** `sase` (primary).
- **Deliverables:**
  1. In-job automatic retry mechanism in `.github/workflows/master-gate.yml`:
     - If <= 3 test nodes fail in a shard, rerun those exact nodes serially once.
     - If the retry passes, annotate the run with `FLAKY: <node_id>` and exit 0.
     - If > 3 nodes fail, bypass retry and fail fast.
  2. Expiring Quarantine System:
     - Create `tests/quarantine.yml` mapping quarantined node IDs to tracking bead IDs, owners, and explicit expiry dates (<= 14 days).
     - Quarantined tests run in an isolated non-blocking matrix lane.
     - Add linter rule in `just lint` failing if any quarantine entry has expired.
  3. Parity Fixes:
     - Commit root `.python-version` with value `3.12`.
     - Add pre-check failing fast if local core binary differs from `sase-core-revision.txt`.
     - Add `if: always()` to critical artifact verification steps in Master Gate.
  4. Workflow Scheduling Optimization:
     - Move heavy Full CI (`full.yml`) from every 2 hours to a nightly schedule plus release candidate runs, freeing up ~10 concurrent runner slots.
     - Run `visual-test` in shadow mode (non-blocking).

#### Independent Verification Plan for Epic 2

```
+---------------------------------------------------------------------------------------------------+
| EPIC 2 INDEPENDENT VERIFICATION PROTOCOL                                                          |
+------+---------------------------+----------------------------------------------------------------+
| Step | Action                    | Expected Observable Outcome                                    |
+------+---------------------------+----------------------------------------------------------------+
| 2.1  | Synthetic flake retry     | Commit test that fails on attempt 1 and passes on attempt 2;   |
|      | verification              | verify job exits 0 with `FLAKY:` annotation in summary.        |
+------+---------------------------+----------------------------------------------------------------+
| 2.2  | Multi-failure fast-fail   | Commit 4 failing tests; verify retry logic is bypassed and job |
|      | boundary test             | terminates without burning rerun cycles.                       |
+------+---------------------------+----------------------------------------------------------------+
| 2.3  | Quarantine execution and  | Add test to `quarantine.yml`; verify it does not run in gate   |
|      | isolation                 | shards, runs in quarantine lane, and does not fail gate build. |
+------+---------------------------+----------------------------------------------------------------+
| 2.4  | Quarantine expiration     | Add entry with yesterday's date to `quarantine.yml`; verify    |
|      | linter gate               | `just lint` fails with explicit expiration message.            |
+------+---------------------------+----------------------------------------------------------------+
| 2.5  | 7-Day Gate Stability SLA  | Query GitHub Actions API across all Master Gate runs for 7     |
|      | audit                     | consecutive days; verify false-red rate is strictly < 3%.      |
+------+---------------------------+----------------------------------------------------------------+
```

---

### Epic 3: Native Merge Queue & Host Landing Orchestration (Phases 2 & 3)

- **Objective:** Deploy GitHub native merge queue on `master`, integrate the host landing engine in `sase_core` and `sase-github`, prove the system via rehearsal and low-risk pilots, enforce mandatory queue admission, and automate the nightly release train.
- **Repositories Involved:** `sase` (primary), `sase-core` (linked), `sase-github` (linked).
- **Deliverables:**
  1. Rust Landing State Machine (`sase-core`):
     - Implement landing lifecycle: `Created` -> `Queued` -> `Merged` | `Ejected` | `Superseded`.
     - Enforce cross-repo prerequisite validation (`sase-core` merged before `sase` queued).
  2. GitHub Adapter & Fixes (`sase-github`):
     - Update `_submit_via_pr_merge`: recognize that exit 0 from `gh pr merge --auto` indicates *queued*, not *merged*.
     - Ensure agent completion returns `queued` state without closing beads prematurely.
  3. Deterministic Landing Watcher Daemon (`sase`):
     - Background service/chop monitoring queued PRs by commit SHA.
     - On merge: verify that `master` contains the agent's SHA and that trees match; only then close the bead and notify waiters.
     - On ejection: classify failure (conflict, flake, deterministic) and dispatch bounded repair turns.
  4. Workflow & Ruleset Integration:
     - Update `master-gate.yml` with `merge_group: types: [checks_requested]` and aggregate `integration-ready` job.
     - Configure GitHub ruleset requiring merge queue: merge commit method, concurrency 2, 0 approvals, empty bypass list.
     - Deprecate push trigger on `master-gate.yml`.
  5. Decision Records:
     - Write decision records replacing `ci-two-speed-split` merge-queue clause and updating `host-owned-completion`.

#### Independent Verification Plan for Epic 3

```
+---------------------------------------------------------------------------------------------------+
| EPIC 3 INDEPENDENT VERIFICATION PROTOCOL                                                          |
+------+---------------------------+----------------------------------------------------------------+
| Step | Action                    | Expected Observable Outcome                                    |
+------+---------------------------+----------------------------------------------------------------+
| 3.1  | Scratch repo rehearsal    | Execute full queued PR workflow on scratch repository; confirm |
|      |                           | `merge_group` executes and auto-merges successfully.           |
+------+---------------------------+----------------------------------------------------------------+
| 3.2  | Proof-of-merge bead state | Complete agent turn; verify bead remains `claimed`/`in_progress|
|      | integrity                 | while queued, and closes ONLY after watcher proves merge.      |
+------+---------------------------+----------------------------------------------------------------+
| 3.3  | Mutual incompatibility    | Submit PR A and PR B that pass independently but break when    |
|      | rejection test            | combined; verify merge queue admits A and cleanly ejects B.    |
+------+---------------------------+----------------------------------------------------------------+
| 3.4  | Direct push server-side   | Attempt direct git push to `master` as maintainer and agent;   |
|      | rejection                 | verify GitHub server rejects push with ruleset error.          |
+------+---------------------------+----------------------------------------------------------------+
| 3.5  | Nightly release train     | Verify unattended nightly release-please execution enqueues    |
|      | automation                | release PR, qualifies candidate, and publishes without manual  |
|      |                           | human intervention.                                            |
+------+---------------------------+----------------------------------------------------------------+
```

---

## 6. Risk Analysis & Contingency Plans

| Risk Scenario | Impact | Mitigation / Contingency Path |
| :--- | :--- | :--- |
| **Flake rate remains > 5% after Epic 2** | Merge queue will suffer high ejection rate, slowing down landing latency. | Do not proceed with Epic 3 cutover. Temporarily disable "only merge non-failing PRs" in the merge queue settings to tolerate non-blocking flakes while triage continues. |
| **Runner queue wait spikes at K=2** | PRs wait in queue longer than 30 minutes, exceeding latency SLA. | Throttle Full CI runs further, or upgrade GitHub organization to GitHub Team plan ($4/user/mo) to expand hosted runner concurrency from 20 to 60 jobs. |
| **GitHub Merge Queue outage / incident** | Landings blocked; inability to merge critical emergency fixes. | Maintain an audited break-glass procedure: an authorized admin temporarily disables the ruleset, lands the fix via direct push, and re-enables the ruleset. |
| **Exact-candidate qualification fails repeatedly** | Releases stall despite green merge queue due to heavy lane differences. | Fall back to "tag-on-green" strategy (`hatch-vcs`): script release tooling to identify the newest historical commit that passed both Master Gate and Full CI, tagging that commit directly. |
| **Cross-repo race condition between core and sase** | Rust bindings mismatch in merge queue build. | Enforce atomic dependency sequencing in `sase_core`: landing watcher holds `sase` PR until `sase-core` GitHub release/commit is live on the remote index. |

---

## 7. Conclusion & Execution Sequence

The proposed merge-queue-fenced `master` and exact-SHA release architecture is the right technical solution for SASE, but it must be executed with discipline:
1. **Adopt Requirement Adjustments R1 through R6**: Ensure releases are atomic (Tag-After-Qualify), keep unhardened visual tests off the blocking gate, enforce cross-repo landing order, bound wave latency, and formally retire host-local gate locks.
2. **Execute as Three Strictly Sequenced Epics**:
   - **Week 1:** Execute **Epic 1** to fix `publish.yml` and ship `0.18.0`.
   - **Weeks 2–3:** Execute **Epic 2** to implement inline test retries, expiring quarantine, and bring false reds below 3%.
   - **Weeks 3–5:** Execute **Epic 3** to build the host landing engine in `sase_core`/`sase-github`, rehearse on a scratch repo, pilot on low-risk traffic, and fully enforce the merge queue on `master`.

This sequenced roadmap addresses immediate business pain within days while building a robust, automated foundation that guarantees `master` remains green and PyPI releases flow on a predictable 1–3 day cadence.
