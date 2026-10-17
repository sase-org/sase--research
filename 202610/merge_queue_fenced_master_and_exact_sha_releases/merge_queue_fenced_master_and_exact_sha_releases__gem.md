# SASE Merge Discipline, Protected Branches, and Master Health: Architecture and Trade-off Analysis

**Author:** researcher gem (`research.1w.gem`)  
**Date:** 2026-10-17  
**Scope:** Investigation of merge discipline, branch protection, CI capacity, release automation, and master branch stability for SASE.

---

## Executive Summary & Bottom Line

1. **Direct Answer on PR-Only / Protected Master Branch:**
   Adopting a traditional GitHub PR-only workflow with mandatory branch protection is **not recommended** for SASE in its current architecture. While intuitively appealing from conventional human-centric software engineering practices, imposing a mandatory PR gate on every change would introduce severe operational dysfunction:
   - **CI Queue Saturation:** At SASE's current commit cadence of 40–90 commits per day, running the 12.7-minute (p50) / 31.5-minute (p90) Master Gate serially across PRs would consume between **19.0 and 47.3 hours of single-threaded CI runner capacity per calendar day**, mathematically guaranteeing unbounded queue backlog.
   - **Quadratic Rebase Churn:** Serial PR queues force subsequent PRs to continually rebase against newly landed heads, invalidating previous CI runs and triggering cascading re-runs.
   - **Impedance Mismatch with Single-Turn Autonomous Agents:** SASE's core architecture relies on host-owned completion (`decisions:host-owned-completion`) and single-turn agents (`decisions:single-turn-agents`). Interposing a human-in-the-loop review queue throttles agent velocity by an order of magnitude; interposing an automated bot-driven GitHub merge queue creates high landing latency (30–60 minutes per turn), blocking dependent execution waves (`sase bead work` Kahn waves).

2. **The Real Problem on Master:**
   The user's diagnosis that SASE has a fatal lack of merge discipline is 100% correct. Master is chronically broken (e.g., 198 of 198 runs failed leading into October; 52 failures out of 58 runs on Oct 16; live regressions failing today). However, the root cause is **not** the lack of GitHub pull requests; it is that **the current host commit finalizer (`builtin@commit` via `_git_commit_dispatch.py`) rebases onto `origin/master` and pushes immediately without ever verifying the integrated rebased tree**. Master Gate runs strictly *post-push*, and 42% of commits land before the prior commit's CI has even finished. Furthermore, unverified landings are accepted by default (`verdict_provenance: unverified`), and red test runs are routinely ignored under the assumption that failures are inherited.

3. **Adjusting the Requirements (Decoupling PyPI from Master Tip):**
   The prompt links two goals:
   - *Goal A:* Keep master green.
   - *Goal B:* Publish new versions of SASE to PyPI more frequently (PR #299 for v0.18.0 has languished unmerged since August 30 because `ci_watch` and `_release_watch_engine.py` refuse to merge release PRs on a red master).
   
   **Critical Requirement Adjustment:** In an autonomous agentic factory, development trunk velocity must be decoupled from release safety. Expecting trunk (`master`) to be green 100% of the time under high-throughput autonomous iteration is unrealistic. SASE should **not** gate releases on the instantaneous state of `master HEAD`. Instead, SASE should establish a **Proven-Green Release Train** (`stable` branch or release pointer tag) that automatically fast-forwards only to commits that have verified green on both `Master Gate` and `Full CI`. Releases to PyPI can then flow continuously and safely from this proven pointer, completely insulated from in-flight development breakage on `master`.

4. **The Recommended Architecture (Four-Layer Landing Discipline):**
   - **Layer 1: Host-Owned Pre-Push Landing Lane (Local Ratchet on Rebased Tree):** Implement Recommendation R1 from the 2026-10-16 Gas Town analysis. Before `_git_commit_dispatch.py` pushes to `origin/master`, it must acquire a local landing lease, rebase onto the latest remote tip, run fast local verification (`just check` with receipts), and enforce a **regression ratchet** (refusing any landing that introduces failures beyond the baseline).
   - **Layer 2: Environment & Boundary Parity:** Eliminate local vs. CI drift by pinning local Python strictly to 3.12 (via `.python-version` and `just install`), validating linked `sase-core` revisions against `sase-core-revision.txt`, and addressing collection-phase blind spots in test selection.
   - **Layer 3: Red-Tip Refusal & Stop-The-Line Mode:** When `origin/master` HEAD is red on CI, the commit finalizer must refuse all non-repair landings. Only commits with `ci` or `flake` task beads or explicit bypass may land until HEAD is green.
   - **Layer 4: Decoupled `stable` Release Train:** Fast-forward a `stable` branch only to fully green SHAs. Point `release-please` and PyPI publication at `stable`, enabling frequent, unblocked, risk-free PyPI releases.

---

## 1. The Present Reality: Anatomy of a Broken Trunk

### 1.1 Empirical Health of `master`
Historical and live data confirm that SASE's `master` branch is trapped in an ongoing reliability crisis:
- **October 1 Audit:** `master` remained continuously red for 13 days and approximately 1,110 consecutive commits. In September 2026, only 60 out of 1,907 Master Gate runs passed (a 3.1% pass rate).
- **October 16 Audit:** Following the `sase-1lh` repair epic, master turned green briefly, then immediately relapsed: on October 16, Master Gate logged **6 passes and 52 failures**.
- **Live Check (October 17):** Of the most recent Master Gate runs on `master`, all completed runs are failing (e.g., run `38990563833` failed on `tests/test_launch_approval_tui.py::test_tui_launch_approval_approve_dispatches_stored_request` and `test_tui_launch_approval_dispatch_failure_records_failed_response`). Commits continue to push directly to `master` on top of these failures.

### 1.2 Impact on PyPI Releases
The chronic breakage on `master` has completely paralyzed the release pipeline:
- The public PyPI package `sase` remains frozen at **0.17.1**, published on **2026-08-29**.
- Release PR #299 (for v0.18.0) was generated on 2026-08-30 and has remained open and unmerged for over six weeks.
- The release engine (`tools/_release_watch_engine.py`) enforces strict pre-merge safety:
  ```python
  if pr.merge_base_gate not in GOOD_CONCLUSIONS:
      return False  # Blocks release PR merging when merge-base gate is red
  ```
- Because Master Gate is almost always red, `ci_watch` refuses to authorize the merge of the release-please PR. PyPI publishing is hard-gated on master health, meaning the external world cannot receive any of the hundreds of features, fixes, or performance enhancements committed over the past two months.

---

## 2. Deep Dive: How the Current Landing Path Works (and Fails)

To understand why merge discipline is absent, one must trace the exact execution path of a commit in the SASE codebase:

```
[Agent Turn Completes]
         │
         ▼
[Agent submits Final Declaration] (`sase final submit`)
         │
         ▼
[Host Finalizer Engine] (`src/sase/finalizers/commit_execution.py`)
         │
         ▼
[Stitch Invocation] (`sase stitch create`)
         │
         ▼
[Git Provider Dispatch] (`src/sase/vcs_provider/plugins/_git_commit_dispatch.py`)
         ├─ 1. Stage files & bead store (`git add`)
         ├─ 2. Create local commit (`git commit -m ...`)
         ├─ 3. Rebase onto origin (`_sync_with_origin_after_commit` -> `git rebase origin/master`)
         └─ 4. Push to origin (`_push_current_branch_with_rebase_retry` -> `git push origin master`)
                  │
                  ▼
         [Pushed to Remote Master]
                  │
                  ▼ (Asynchronous)
         [GitHub Actions: Master Gate triggered POST-PUSH]
```

### The Three Critical Failure Modes:
1. **Zero Pre-Push Verification of the Rebased Tree:**
   In `_git_commit_dispatch.py` (lines 491–504), the code commits locally, rebases onto `origin/master`, and immediately pushes. At no point between the rebase and the push does `_git_commit_dispatch` run `just check`, test the rebased tree, or check for semantic conflicts. If the base had changes that conflict semantically with the agent's changes, the broken tree is pushed instantly to `origin/master`.
2. **Post-Push Telemetry vs. Pre-Push Gating:**
   `Master Gate` (`.github/workflows/master-gate.yml`) triggers on `push: branches: [master]`. It is an audit after the fact, not a gatekeeper. By the time Master Gate marks a run red (12–30 minutes later), subsequent agents have already pulled the broken commit into their workspace clones.
3. **The Inherited Failure Illusion:**
   Because master is red 90%+ of the time, almost every agent running `just check` sees failures. Agents (and automated triage tools) dismiss these failures as "inherited, not mine." Agents then submit declarations with `verdict_provenance: unverified`. The finalizer accepts this and pushes, piling fresh breaks onto existing breaks.

---

## 3. Critique of the Proposed Plan: "PR-Only / Protected Master Branch"

The user asks: *"I'm not sure if we need to adopt a PR-only (i.e. protected master branch) workflow to achieve this (or if that's recommended anyway) or if there is some other way... Is this a good idea?"*

### 3.1 Why PR-Only is the Standard Human Reflex
In human engineering teams, branch protection rules (`Require pull request before merging`, `Require status checks to pass before merging`) are standard industry practice:
- Prevents direct pushes to `main`/`master`.
- Enforces code review.
- Ensures CI passes on the PR branch before integration.

### 3.2 Why PR-Only Breaks Down in SASE
When applied to SASE's autonomous multi-agent software factory, a rigid PR-only workflow causes catastrophic friction:

#### A. The Mathematical Queue Saturation Problem
Let us examine the numbers from the October audits and live measurements:
- **Fast Gate Wall-Clock Time:** Master Gate duration is **12.7 minutes (p50)** and **31.5 minutes (p90)**.
- **Commit Cadence:** SASE generates **40 to 90 commits per day** (an average of one commit every 15–30 minutes during active work).
- **Serial PR Gate Cost:**
  $$\text{Daily CI time needed} = 90 \text{ commits} \times 12.7 \text{ min} = 1,143 \text{ min} \approx 19.05 \text{ hours}$$
  At p90 (31.5 min), it requires **47.25 hours of CI runner time per calendar day**.
- A strictly serialized merge queue (where PR $N+1$ waits for PR $N$ to merge and then tests against the new tip) exceeds the physical capacity of a 24-hour day. The queue will experience unbounded latency growth.
- This was precisely evaluated in **`decisions:ci-two-speed-split`**:
  > *"The measured alternatives all either failed to produce an attributable per-SHA signal or consumed the account's capacity without reliably settling the tip: queue: max on the master group, per-SHA concurrency on the full ci.yml, deleting the master concurrency block, cancel-in-progress: true, a GitHub merge queue, larger or self-hosted runners..."*

#### B. The Rebase Storm & Invalidation Cascade
If GitHub branch protection requires *"Require branches to be up to date before merging"*:
- When PR 1 merges into `master`, PRs 2, 3, 4, 5, and 6 are immediately marked "out of date."
- Each PR must be rebased onto `master`.
- Each rebase restarts the 13–30 minute CI run.
- With $N$ concurrent PRs, the number of CI runs scales quadratically ($O(N^2)$), consuming massive GitHub Actions concurrency and resulting in landing delays of hours for trivial fixes.

#### C. Human Review Bottleneck vs. Single-Turn Agent Autonomy
- If the PR-only workflow requires human approval (`Require approvals > 0`), the entire autonomous agent system stops. A human cannot review 90 PRs a day. Autonomous swarms, overnight epics, and background task processing become impossible.
- If the PR workflow does *not* require human approval (auto-merging bot once CI passes), then the PR abstraction is simply a slow, fragile, API-heavy merge queue that provides no human review benefits while paying all the latency and queue overhead.

#### D. Disruption of SASE Work-Unit Waves (`sase bead work`)
- SASE tasks and epics execute in topological waves (Kahn waves). For example, Phase 1 creates a shared data structure, and Phase 2 spawns three parallel worker agents to build against that data structure.
- In SASE's transaction model (`decisions:single-turn-agents`), Phase 1 finishes, commits to `master`, and Phase 2 workers immediately clone/pull `master` to begin work.
- In a PR-only queue, Phase 1 waits 30–60 minutes in a GitHub PR queue. Phase 2 either idles (halting the factory) or branches off an unmerged PR branch (creating complex multi-branch reconciliation nightmares if Phase 1 needs minor re-rolls).

---

## 4. Lessons from Gas Town, Bors, and Industry Practice

The prompt references `gastown_vs_sase_lessons_to_borrow.md`. What did Gas Town do, what worked, and what failed?

### 4.1 What Gas Town Attempted (The Refinery)
Gas Town implemented a merge queue called the **Refinery**:
- When a worker finished, it ran `gt done`, creating a Merge Request (MR) bead.
- The Refinery ran a 1,285-line patrol formula (`mol-refinery-patrol.formula.toml`).
- It merged the target branch into a temporary branch, ran tests on the **merged result**, and proved the target branch contained the commit SHA (`verifyMQPostMergeProof`) before closing the bead.
- Blocked beads waited on `merge-blocks` dependencies that only resolved when the predecessor had `"Merged in <sha>"`.

### 4.2 What Failed in Gas Town
- **Batch-then-bisect was vaporware:** Gas Town's README advertised sophisticated batch-and-bisect merging, but code analysis revealed it was completely unwired in production. The Refinery processed MRs strictly one at a time.
- **LLM-Judged Merging:** The Refinery used an LLM prompt to judge whether a failure was "pre-existing" or "introduced by the branch." The LLM often misjudged, merging red changes anyway.
- **Abandoned by its own creators:** The Gas Town project itself stopped using the Refinery for its own repository, choosing instead to merge through GitHub PRs. Gas Town's creator (Steve Yegge) noted that the system "fell apart at the seams with Opus 4.7" because models kept fiddling with the harness itself.
- **The Gas City Pivot:** In Gas Town's successor, Gas City, all LLM patrol supervisors were discarded in favor of deterministic orchestrator code ("crons watch, models act").

### 4.3 The Bors / Graydon Hoare Principle
The fundamental insight of Bors (Graydon Hoare's "Not Rocket Science Rule") is:
> *"automatically test merge candidates before they land."*

In web-scale cloud repositories (e.g. Rust, Chromium), this is handled by massive distributed merge queues with speculative batching. But SASE does not have a 1,000-node CI cluster. **SASE's key advantage is that agents run locally on powerful host machines with full workspace checkouts and pooled git object alternates.**
Therefore, the verification does not need to happen in a slow cloud merge queue—it can happen **locally on the host machine before the commit is pushed**.

---

## 5. Adjusting the Requirements: Velocity vs. Release Decoupling

The prompt states:
> *"Namely, we need a way to ensure that master stays green so we can start publishing new versions of sase to PyPI more often."*

This conflates two distinct engineering requirements:
1. **Trunk Hygiene:** Keeping `master` healthy enough so that agents and developers can branch, build, and test without being blinded by noise and false alarms.
2. **Release Reliability:** Ensuring that packages published to PyPI are guaranteed to be 100% green, fully tested, and functional.

### The Decoupling Insight
In high-velocity software engineering, **coupling release publishing directly to the instantaneous tip of `master` is an anti-pattern**. 
Even in high-discipline engineering environments (e.g., Google Piper trunk, Linux kernel, Chromium), trunk is occasionally broken for brief intervals by subtle integration bugs, compiler quirks, or timing flakes.
If PyPI releases require `master HEAD` to be green at the exact hour the release job runs:
- A single test flake or an in-progress repair stops all PyPI releases.
- A backlog builds up (e.g., 6 weeks without a release).
- When a release finally does get attempted, it contains hundreds of accumulated commits, making regression attribution exceedingly difficult.

### The Adjusted Requirement:
- **Requirement 1 (Trunk Quality):** Implement mechanical pre-push landing discipline so `master` remains green >95% of the time, and any regression halts subsequent non-repair landings immediately.
- **Requirement 2 (Release Train):** Establish an automated, asynchronous **`stable` release pointer** (branch or tag) that advances only across SHAs that have passed both `Master Gate` and `Full CI`. PyPI releases publish from `stable`, completely immunizing the public release pipeline from transient development breakages on `master`.

---

## 6. Comprehensive Trade-off Matrix of Alternative Approaches

| Approach | CI Runner Cost | Landing Latency | Blast Radius of Breaks | Compatibility with SASE Multi-Agent Model | Implementation Effort | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Option 1: GitHub PR-Only + Required Checks** | **Extreme** (19–47 h/day; queue saturation) | **Very High** (30–90 min per turn) | Zero on master | **Very Poor** (destroys wave dependencies; requires human bottleneck or bot) | Medium | **Rejected:** Mathematically saturates CI capacity; throttles agent throughput. |
| **Option 2: GitHub Merge Queue (Speculative Batching)** | **High** (re-runs batches on failure) | **High** (15–45 min per turn) | Zero on master | **Poor** (batch evictions cause latency spikes for agents) | Medium | **Rejected:** Re-evaluating `decisions:ci-two-speed-split` shows cloud queue overhead is unnecessary. |
| **Option 3: Post-Push Auto-Revert Bot** | **Low** (runs on existing CI) | **Zero** (immediate push) | High (master is red until reverted) | **Medium** (creates rebase churn and revert commit noise) | Low | **Insufficient:** Does not stop 42% race where newer commits land before gate finishes. |
| **Option 4: Host-Owned Pre-Push Landing Lane (Local Rebase & Ratchet)** | **Zero GitHub CI cost** (runs locally on agent host) | **Low** (2–4 min local check) | Minimal (catches 95%+ of breaks before push) | **Excellent** (fits `host-owned-completion` & `receipts-prove-before-they-skip`) | Medium | **Recommended:** Solves trunk health at the source without cloud bottlenecks. |
| **Option 5: Decoupled `stable` Release Train** | **Zero additional cost** (reuses scheduled Full CI) | **N/A** (background release sync) | Zero for external PyPI users | **Flawless** (development never blocks releases; releases never block agents) | Low | **Recommended:** Instantly unblocks frequent PyPI releases. |

---

## 7. The Recommended Architecture: Four-Layer Merge Discipline

Rather than adding a heavyweight GitHub PR workflow, SASE should implement a cohesive, deterministic, host-owned landing architecture.

```
                  [Agent Completes Turn]
                            │
                            ▼
           [Layer 1: Host-Owned Pre-Push Landing Lane]
         ┌──────────────────────────────────────────────┐
         │ 1. Acquire per-repo host landing lease       │
         │ 2. Fetch and rebase onto origin/master       │
         │ 3. Run fast local verification (just check)  │
         │ 4. Evaluate Ratchet:                         │
         │    - New failures? -> REFUSE PUSH            │
         │    - Clean pass? -> PROCEED                  │
         │ 5. Push to origin/master                     │
         │ 6. Verify remote SHA (push proof)            │
         └──────────────────────────────────────────────┘
                            │
                            ▼ (Pushed to master)
         ┌──────────────────────────────────────────────┐
         │ [Layer 2: Environment Parity Enforced]       │
         │ - Python 3.12 pinned locally & in CI         │
         │ - Linked sase-core checked against pin       │
         └──────────────────────────────────────────────┘
                            │
                            ▼
         ┌──────────────────────────────────────────────┐
         │ [Layer 3: Stop-The-Line Enforcement]         │
         │ If CI Master Gate fails on HEAD:             │
         │ - Commit finalizer refuses non-repair pushes │
         │ - Only 'ci'/'flake' task beads can land      │
         └──────────────────────────────────────────────┘
                            │
                            ▼
         ┌──────────────────────────────────────────────┐
         │ [Layer 4: Decoupled Stable Release Train]    │
         │ - Master Gate + Full CI passes on SHA X      │
         │ - Fast-forward 'stable' branch to SHA X      │
         │ - release-please & publish.yml cut PyPI from │
         │   'stable' continuously                      │
         └──────────────────────────────────────────────┘
```

### Layer 1: Host-Owned Pre-Push Landing Lane (`builtin@commit` Ratchet)
This directly implements Recommendation R1 from the 2026-10-16 Gas Town research within SASE's architectural boundaries:
1. **Per-Repo Landing Lease:**
   In `src/sase/finalizers/commit_execution.py`, when a turn declares a repository commit, the host finalizer acquires a per-repository file lock (`.sase/locks/landing_<repo>.lock`). This serializes concurrent agent landings on the same host, preventing two agents from racing past each other's rebase.
2. **Rebase First:**
   Fetch `origin/master` and rebase the agent's commit on top.
3. **Verify the Rebased Tree:**
   In `src/sase/vcs_provider/plugins/_git_commit_dispatch.py`, before invoking `git push`, invoke local verification on the rebased tree:
   ```python
   # Pseudocode in _sync_with_origin_after_commit / _push_current_branch:
   ok, err = self._rebase_onto_origin_default(cwd, default_branch)
   if not ok:
       return (False, f"Rebase conflict: {err}")
   
   # Run verification on the integrated tree
   verdict = run_local_landing_verification(cwd)
   if not verdict.is_acceptable(baseline):
       return (False, f"Landing refused: regression detected on rebased tree: {verdict.failures}")
   ```
4. **Enforce the Regression Ratchet:**
   - If the baseline was green, the rebased tree must pass 100% (`verdict == PASS`). Any failure is a regression caused by this commit or its semantic interaction with master. The push is **refused**.
   - If the baseline on master is currently red (during recovery periods), the commit must **not introduce any new failure signatures** not already in the baseline (`verdict == NO_NEW_FAILURES`).
   - This adheres strictly to `decisions:receipts-prove-before-they-skip`: receipts serve as proof for host completion, never as an unverified skip.
5. **Prove the Push:**
   Following Gas Town's `verifyMQPostMergeProof`, verify that `origin/master` actually contains the pushed SHA before marking bead dependencies resolved. Dependent beads (`%w(bead=...)`) unblock only on confirmed remote inclusion.

### Layer 2: Strict Environment and Tooling Parity
Pre-push verification is only as good as the parity between the local agent environment and GitHub Actions:
1. **Pin Local Python to 3.12:**
   - Commit `.python-version` with content `3.12`.
   - Update `just install` and `just install-dev` to enforce Python 3.12. This eliminates insidious syntax and stdlib drift (such as Python 3.12 vs 3.14 `argparse` rendering differences that caused invisible CI breakages).
2. **Strict Core Revision Checking:**
   - When running local verification, `just check` must ensure the installed `sase-core-rs` matches the SHA pinned in `sase-core-revision.txt`. If the linked checkout is ahead or behind, fail fast.
3. **Facade and Test Collection Edges:**
   - Enhance `tools/select_tests` to track inter-test imports (e.g., facade files importing basic test modules) and always run a fast `pytest --collect-only` pass so import breaks cannot escape scoped testing.

### Layer 3: Stop-The-Line Mode on Red HEADs
To eliminate the 1,110-commit pileups where broken commits accumulate for weeks:
1. **Red-HEAD Landing Guard:**
   Before pushing, `_git_commit_dispatch.py` queries the cached state of `origin/master`'s latest Master Gate run (via `ci_watch` or GitHub status API).
2. **Refuse Feature Landings on Broken Trunk:**
   If HEAD is red, any commit whose commit message or task bead does not match `fix:`, `ci:`, `flake:`, or an explicit repair tag is **refused**.
3. **Autonomous Repair Acceleration:**
   When HEAD turns red, the host scheduler dispatches a targeted CI repair task bead with the failing job logs injected, prioritizing repairs above all backlog feature work.

### Layer 4: Decoupled `stable` Release Train for Frequent PyPI Publishing
To satisfy the user's primary business requirement—publishing new versions of SASE to PyPI frequently without being blocked by trunk fluctuations:
1. **Introduce the `stable` Branch:**
   Create a dedicated branch: `stable` (or `release`).
2. **Automated Promotion Engine:**
   Enhance `ci_watch` (which already runs on a schedule) to advance `stable`:
   ```bash
   # When Master Gate and Full CI both succeed on commit X on master:
   git push origin X:refs/heads/stable
   ```
3. **Configure `release-please` and PyPI Publishing on `stable`:**
   - Update `release-please-config.json` to track `default-branch: "stable"`.
   - Update `.github/workflows/publish.yml` to trigger on `stable`.
4. **Benefits:**
   - If master has an active regression being fixed, `stable` simply remains at the previous green commit.
   - When master goes green, `stable` immediately advances.
   - Release PRs merge cleanly and reliably.
   - PyPI can be updated daily or on every green release train advance, completely decoupling public publishing velocity from private development churn.

---

## 8. Implementation Roadmap and Next Steps

### Phase 1: Stop-the-Line Trunk Recovery & Immediate PyPI Release (Today)
1. **Arm Landing Hold:** Temporarily pause non-essential feature launches.
2. **One Authorized Build-Cop Pass:** Resolve the currently failing tests on master (`test_launch_approval_tui.py`, etc.) and ensure Master Gate and Full CI pass cleanly.
3. **Unblock 0.18.0:** Merge Release PR #299 and publish SASE 0.18.0 to PyPI.
4. **Commit `.python-version`:** Set to `3.12`.

### Phase 2: Host Landing Pre-Push Check (Week 1)
1. **Modify `_git_commit_dispatch.py`:** Add a pre-push hook in `vcs_create_commit` that executes `just check` on the rebased tree before calling `git push`.
2. **Refusal Contract:** Wire refusal into the commit finalizer so unverified or failing trees fail closed.
3. **Feature Flag:** Ship behind `feature_flags.pre_push_landing_verification` per `sase/memory/sase_flags.md`.

### Phase 3: The `stable` Release Train (Week 2)
1. **Create `stable` branch** in GitHub repository.
2. **Add Promotion Step to `ci_watch`:** Automatically fast-forward `stable` to master SHAs that satisfy `gating_workflows` and `heavy_max_age_hours`.
3. **Retarget `release-please` to `stable`:** Update `publish.yml` and release configuration.

### Phase 4: Core Landing Lease & Ratchet in `sase_core` (Month 1)
1. Migrate the host landing lease and regression ratchet logic into `sase_core` (Rust backend) under `decisions:rust-core-required`.
2. Author new decision record: `decisions:host-landing-lane-and-stable-release`.

---

## 9. Conclusion

Adopting a PR-only, protected master branch workflow is the wrong solution to a real problem. It attempts to enforce quality by outsourcing gating to an already saturated cloud CI pipeline, which would paralyze SASE's high-speed autonomous agent workflow.

The right solution is **distributed, host-owned merge discipline**:
1. **Test before pushing:** Rebase and verify locally on the host machine before code ever reaches remote `master`.
2. **Enforce the ratchet:** Refuse any change that introduces new test failures.
3. **Stop the line:** Refuse feature pushes while `master` HEAD is red.
4. **Decouple releases:** Advance a `stable` branch only on proven-green commits, enabling continuous, reliable, hands-free PyPI publishing.
