# PyPI Release Reliability: Architecture, Synthesis, and Delivery Plan

**Author:** Researcher gem (Swarm 22)  
**Date:** 2026-10-18  
**Scope:** Review and synthesis of tagged research files, converged architecture, and four-epic delivery breakdown for reliable SASE PyPI releases.

---

## 1. Executive Summary & Bottom Line

SASE's PyPI release process stalled for over seven weeks (49 days) following the release of v0.17.1 on 2026-08-29. Worse, the shipped v0.17.1 release became completely un-installable on PyPI due to aggressive, uncoordinated retention deletion in the linked `sase-core` repository (`sase-16p`), causing `pip install sase` and `uv tool install sase` to fall back to ancient v0.1.0 or fail outright. Meanwhile, release PR #299 for v0.18.0 sat unmerged because the release watchdog required Full CI to be green within six hours—a condition that passed only 1 time in 271 runs.

Reviewing the 12 tagged research reports in the research sidecar reveals a complete, coherent diagnosis and a robust path forward. By converging the strongest insights across the initial merge queue proposal, the four-epic reassessment, the deep-dive GitHub queue primer, the Google release engineering comparison, and cross-project studies (Gas Town, Gas City, and agent literature), we arrive at a unified, battle-tested solution.

### Core Architectural Decisions

1. **Protect `master` via GitHub's Native Merge Queue with Zero Approvals:**
   Direct pushes to `master` must stop. Green windows on an unfenced branch decay within ~36 hours under 43 pushes/day from multi-host agents (apollo and athena). The native merge queue tests the actual combined state (`master` + all queued PRs ahead + candidate PR) on `gh-readonly-queue/master/...`. PRs serve strictly as host-created admission tickets, requiring **0 approvals** because agents execute under the maintainer's identity (where GitHub self-approval rules would deadlock).
2. **Linear History via Rebase (One Commit Per PR):**
   Reversing the original proposal's merge-commit stance, real SASE history demonstrates that merge commits duplicated and dropped changelog entries in release-please (e.g., June 0.1.x history). SASE's history is strictly linear (294 consecutive single-parent commits). We adopt **rebase** as the primary merge method, with squash as a documented fallback.
3. **Build-Once, Exact-SHA Publishing with Hardened Provenance:**
   `publish.yml` must never build whatever floating commit happens to sit at `master`'s HEAD. It must build the exact release candidate commit once, package the wheel and sdist, record their sha256 digests, qualify those exact artifacts across Python 3.12–3.14, and publish those identical bytes. Trusted Publishing attestations must be keyed to the release candidate SHA, not the scheduled trigger commit.
4. **Three-Class Check Inventory (N1):**
   - **Admission Checks (Merge-blocking):** Fast Master Gate suite (p50 ~12.5 min) triggered on `merge_group` via an event-aware aggregate check (`integration-ready`).
   - **Release-blocking Checks:** Packaging validation, wheel/sdist install smokes, core floor verification, and `test (3.13)` / `test (3.14)`.
   - **Advisory Checks:** Visual snapshots, perf-floors, and tutorial tests run continuously on candidates, filing tracked `ci` beads with an SLO, but never blocking merge or release by default.
5. **Flake-Aware Qualification & Google-Style Post-Submit Discipline:**
   Qualification of ~56k test nodes cannot remain an all-or-nothing coin flip. Release-blocking qualification jobs inherit Epic B's bounded 1-shot in-job rerun (for $\le 3$ failing nodes). Post-submit breakage triggers deterministic culprit finding and an **auto-revert-first** protocol (`ace/revert_agent_transaction.py`) to restore green head within a 6-hour SLO.
6. **Pre-Publish Behavioral Exercise on Linux and macOS:**
   Before uploading to PyPI, the candidate wheel and sdist must be smoke-tested in clean virtual environments using dependencies resolved from public PyPI on both `ubuntu-latest` and `macos-latest`, executing real CLI workflows, `sase core health`, and headless TUI rendering.
7. **Core Dependency Invariant & Retention Guard:**
   `sase-core` retention scripts must enforce an automated safety invariant: never delete any `sase-core-rs` version required by the last $N \ge 2$ published `sase` releases. Master's release train automatically detects core pin lag (`CORE_LAG`) and requests/cuts the required core release before publishing SASE.
8. **Preserving Developer Velocity:**
   The merge queue introduces an asynchronous gap between agent completion and commit landing (~13 min p50, ~28 min p95). We bridge this gap by adding explicit landing status tracking (`armed`, `queued`, `landed`, `ejected`), landed notifications, and a `sase preview` command executing from an isolated worktree at the PR head.

### Delivery Structure

The work is split into **Step 0** (human admin ruleset today), **Track 0** (immediate release relief via existing beads), and **Four Decoupled Epics**:
- **Step 0 (Today):** Human admin creates a GitHub branch ruleset blocking branch deletion and non-fast-forward pushes on `master`.
- **Track 0 (Immediate, Parallel):** Restore PyPI installability (`sase-16p`, `sase-10d`). Cut `sase-core-rs` release with pinned commit `916d5e3a`, ratchet PR #299, and publish v0.18.0.
- **Epic A (Parallel Start):** Exact-Candidate Releases, Install Guards, and Core Invariants (Build-once, flake-aware qualification, multi-OS exercise, retention invariant, daily public install canary).
- **Epic B (Parallel Start):** Trustworthy Merge Gate & Drift Protection (Bounded rerun, non-blocking quarantine with hygiene escalation, environment parity, +30-day shifted-clock drift canary).
- **Epic C (Parallel Start):** Queue-Aware Landing Protocol & Developer Experience (sase-core landing state machine, sase-github rebase adapter, developer preview & landed notifications, proven on a throwaway sandbox repo).
- **Epic D (Sequenced Cutover):** Production Cutover, Post-Submit Discipline, and Release Train (Requires Epic B mechanisms live and Epic C sandbox suite passing; low-risk pilot, 7-day soak with $<3\%$ false reds, culprit auto-revert, and full enforcement).

---

## 2. Review and Synthesis of the 12 Tagged Research Reports

The 12 research reports tagged with `pypi-release-reliability` establish the historical, architectural, and operational context. Here is their critical synthesis:

### 2.1 The Crisis and Immediate Context
1. **`sase_v0_18_0_pypi_release_status.md`**:
   - *Core Finding:* Details the exact failure mechanism of PR #299 (v0.18.0). `ci_watch` refused to merge because Full CI had failed for 49 consecutive days. The run failures were dominated by visual snapshot timeouts (shifter/deck races) and python 3.12/3.13/3.14 test flakes.
   - *Takeaway Adopted:* Confirmed the critical separation between Master Gate and Full CI, and proved why Full CI must never be a blind, synchronous prerequisite for merging release PRs.
2. **`master_ruleset_step0_setup_steps.md`**:
   - *Core Finding:* Step-by-step instructions for Step 0: creating the `master-integrity` branch ruleset on `sase-org/sase` with `deletion` and `non_fast_forward` enabled and empty bypass.
   - *Takeaway Adopted:* Must remain an administrative action for today, completely outside the epics. Never test destructively against production `master`.

### 2.2 The Foundation Proposals and Reassessments
3. **`merge_queue_fenced_master_and_exact_sha_releases.md`**:
   - *Core Finding:* The original proposal establishing the need for a merge queue. Crucially, its queue simulation (replaying 200 real arrival times at 43 pushes/day) proved that runner capacity is *not* the bottleneck: at concurrency $K=2$, landing latency is ~13 min p50 and ~28 min p95. The true bottleneck is test flakiness. It also decisively rejected host-side landing lanes (local `check` passes only 3.6% of the time, takes up to an hour, and cannot coordinate between apollo and athena).
   - *Modifications Required:* The original recommended merge commits, assumed 0.18.0 was in scope, folded visual-test into the gate, and relied on a feature flag rather than project configuration.
4. **`merge_queue_fence_reassessment_and_epic_split.md`**:
   - *Core Finding:* The landmark reassessment consolidating four reviewer perspectives into 6 major requirement modifications (A–J revised) and 13 new requirements (N1–N13). It reversed the merge commit decision to **rebase** after discovering changelog corruption in sase's June history, extracted 0.18.0 to Track 0, established the N1 check inventory, and defined the 4-epic delivery roadmap.
   - *Takeaway Adopted:* Forms the baseline structural skeleton of our architecture.
5. **`merge_queue_fence_reassessment_explained.md`**:
   - *Core Finding:* Plain-language translation and rationale for the four-epic delivery split, explaining why merging C and D into 3 epics would compromise sandbox safety and leave cutover unowned.

### 2.3 Technical Deep-Dives and External Models
6. **`github_native_merge_queue_primer.md`**:
   - *Core Finding:* Detailed GitHub merge queue mechanics. Proved that `master` advances to the exact temporary commit SHA tested on `gh-readonly-queue/master/...`. Clarified that `gh pr merge` exits 0 on *armed/queued*, not merged, requiring asynchronous landing watchers. Identified that skipping required jobs via `if:` on `merge_group` causes untested code to land, necessitating an event-aware aggregate job (`integration-ready`).
   - *Takeaway Adopted:* Informs the exact GitHub workflow triggers, aggregate check structure, and landing state reconciliation.
7. **`google_release_engineering_vs_sase_release_plan.md`**:
   - *Core Finding:* Evaluated the plan against Google release engineering (Piper, TAP, Rapid, MPM, BAB, Build Cops). Identified that the plan was strong pre-merge but critically weak post-merge. Provided 11 ranked enhancements, notably:
     - *Flake-aware qualification:* 3 of 6 runs on unchanged commit `ae9f044bb3` failed due to 1-2 flakes out of ~56k tests.
     - *Post-submit discipline:* 2-hour continuous Full CI, deterministic culprit finding, and auto-revert-first.
     - *Pre-publish exercise:* Real CLI workflows on Linux and macOS before uploading.
     - *Quarantine time-bomb fix:* Expired quarantine entries must escalate hygiene/bead priority, never fail the admission gate.
     - *Provenance fix:* Attestations must certify candidate SHA, not master tip.
   - *Takeaway Adopted:* We incorporate all top-tier Google recommendations into Epics A, B, and D.
8. **`merge_queue_impact_on_testing_agent_fixes.md`**:
   - *Core Finding:* Analyzed the impact on the maintainer's edit-test loop (editable install of primary checkout + fast-forward pull). Identified two major user-facing gaps: "agent done" no longer means "ready to test", and there is no way to test changes before queue landing without dirtying the checkout.
   - *Takeaway Adopted:* Mandates the addition of landing state notifications and the `sase preview` worktree command into Epic C.
9. **`agent_factory_merge_discipline_reading_list.md`**:
   - *Core Finding:* Literature review of 2025–2026 industrial and academic findings (Anthropic, Uber SubmitQueue/Stovepipe, Mergify, Snyk LiteLLM poisoned scanner). Emphasized that high-frequency agent PRs create denial-of-service queue storms if retry loops are unchecked, and proved that zero approvals remains safe only when backed by post-merge automated verification.

### 2.4 Ecosystem Comparisons and User-Facing Alignment
10. **`gastown_vs_sase_lessons_to_borrow.md`**:
    - *Core Finding:* Compared Steve Yegge's Gas Town to SASE. Established the central maxim that "fences beat promises". Borrowed the concepts of push proof, dependency resolution only on merge, and durable preservation.
11. **`gascity_advantages_over_sase_and_what_to_borrow.md`**:
    - *Core Finding:* Deep dive into Gas City's architecture. Disproved several myths (e.g., confirmed that full git alternates avoid workspace disk bloat) and reinforced that release safeguards must be enforced mechanically by the control plane.
12. **`sase_sh_docs_redesign.md`**:
    - *Core Finding:* Documentation redesign emphasizing that "Step 1 must be true": the documented first-run install (`uv tool install sase`) must install a working product. A broken PyPI package poisons the entire user journey.
    - *Takeaway Adopted:* Establishes clean-install smoke checks as a non-negotiable release gate.

---

## 3. Converged Architectural Specification

```
                             [Agent Finishes Turn]
                                       │
                         Armed PR Created (0 approvals)
                                       │
                      ┌────────────────┴────────────────┐
                      ▼                                 ▼
             [PR Entry Checks]                [Developer Preview]
            (Fast lint / syntax)             (sase preview worktree)
                      │
            PR Enqueued in Merge Queue
            (Build concurrency K=2)
                      │
         [gh-readonly-queue/master/...]
           integration-ready Aggregate
             (Full Master Gate suite)
                      │
             ┌────────┴────────┐
             ▼                 ▼
          [Passed]          [Failed]
             │                 │
      Rebase Onto master    Ejected from Queue
      (Landed Notification)    │
             │           Witness Check on Base
             │                 │
             │        ┌────────┴────────┐
             │        ▼                 ▼
             │   [PR Bug]          [Base Drift]
             │   Fork Repair       3 Strikes -> Circuit Breaker
             │                     Queue-Jump Repair Turn
             │
     [Every 2 Hours: Continuous Release-Blocking Lane]
           (test 3.13, test 3.14, core-floor smoke)
             │
     ┌───────┴───────┐
     ▼               ▼
  [Green]         [Broken]
     │               │
     │       Culprit Finder -> Auto-Revert PR (Queue Jump)
     │
[Nightly Release Train: Candidate Evaluation]
     │
  1. release-please draft release (tag forced, draft=true)
  2. Build wheel & sdist once -> sha256 digests recorded
  3. Flake-aware qualification (bounded 1-shot rerun for <= 3 nodes)
  4. Behavioral exercise on clean Ubuntu & macOS (CLI, health, headless TUI)
  5. Core-lag check -> auto-cut core release if needed
  6. Provenance attestation bound to candidate SHA
  7. Publish to PyPI -> Un-draft release
  8. Daily Public Install Canary (uv tool install sase == latest PyPI)
```

### 3.1 Admission Control and Queue Configuration

- **GitHub Repository Ruleset:**
  - Target: `refs/heads/master`.
  - Rules: `deletion`, `non_fast_forward`, `pull_request` (with required approvals = 0), and `merge_queue`.
  - Queue parameters:
    - `merge_method`: `REBASE` (one commit per PR; commit message formatted as PR title and description).
    - `max_entries_to_build` (concurrency): `2`.
    - `min_entries_to_merge` / `max_entries_to_merge`: `1` / `1` for pilot and early enforcement; scalable after observation.
    - `grouping_strategy`: `ALLGREEN` (every PR's speculative commit must pass).
    - `check_response_timeout_minutes`: `60`.
  - Bypass list: strictly empty. Admin overrides require disabling the ruleset, creating an immutable audit log entry.
- **Workflow Triggers and Event-Aware Aggregate:**
  - `master-gate.yml` listens on `pull_request: branches: [master]` and `merge_group: types: [checks_requested]`.
  - The aggregate job `integration-ready` runs with `if: always()` and evaluates dependencies:
    - On `pull_request`: accepts intentionally skipped heavy jobs; validates formatting, lints, and syntax.
    - On `merge_group`: asserts that every required gate job completed with `conclusion == 'success'`.
- **Drift Handling and Base-Red Resilience:**
  - *Witness Check:* When an ejection occurs, the reconciler checks if the failed test node also fails on the base commit. If witnessed on base, the failure is classified as base drift rather than a defect in the PR.
  - *Circuit Breaker:* If 3 consecutive ejections share the same failure signature, admission is paused via a durable hold (modeled on `hold-pull-fail-open`). A high-priority build-cop turn is dispatched; agents are never blocked waiting.
  - *Queue Jump:* Build-cop repair PRs and emergency reverts use the `jump` attribute in GraphQL `enqueuePullRequest` to move to the front of the queue.
  - *Shifted-Clock Canary:* Nightly gate run against master tip with system clock shifted +30 days, detecting date-dependent test time-bombs before they detonate in production.

### 3.2 Exact-Candidate Release Qualification and Publishing

- **Draft Versioning & Provenance Integrity:**
  - `release-please` runs with `draft: true` and `force-tag-creation: true`. Release PRs claim version bumps, but GitHub Releases remain drafts until PyPI confirmation.
  - GitHub Actions Trusted Publishing attestations are explicitly configured to bind to the candidate commit SHA, eliminating the defect where attestations certify floating master tip commits.
- **Build-Once Candidate Record:**
  - A candidate record tuple `(version, tag, commit_sha, tree_sha, core_pin, digests)` is created during the build step.
  - Wheel and sdist are built once. Subsequent qualification and publishing steps consume these identical binary artifacts.
- **Flake-Aware Qualification (Addressing the 50% Coin Flip):**
  - Qualification runs the release-blocking set on the candidate commit.
  - Release-blocking jobs in `ci.yml` (`test (3.13)`, `test (3.14)`, packaging smokes) incorporate a bounded in-job rerun: if $\le 3$ test nodes fail, they are rerun once serially. A pass on rerun records `FLAKY:` and marks the node as recovered, preventing spurious candidate rejections while preserving failure evidence.
- **Multi-OS Behavioral Exercise:**
  - Prior to PyPI upload, the built wheel and sdist are installed into clean virtual environments on both `ubuntu-latest` and `macos-latest`.
  - The exercise executes: (1) package import, (2) `sase --version`, (3) `sase core health`, (4) headless TUI frame rendering, and (5) a real CLI project workflow.
- **Post-Publish Canary & Recovery:**
  - A scheduled daily canary runs `uv tool install sase` in a clean environment, asserts that the installed version matches PyPI's latest release, and verifies `sase core health`.
  - If a bad release reaches PyPI, `sase release yank` automates PEP 592 yanking, while hotfixes are prepared on a dedicated release branch via cherry-pick.

### 3.3 Core Invariant & Retention Guard

- **Retention Invariant (`sase-core`):**
  - `.github/scripts/pypi_retention.py` in `sase-core` is patched with an inviolable constraint: it inspects published SASE releases on PyPI and refuses to delete any `sase-core-rs` version satisfying the core range of the last $N \ge 2$ SASE releases.
  - If PyPI metadata cannot be fetched, retention fails closed (deletes nothing).
- **Automated Core Release Ordering:**
  - The nightly release train compares master's `sase-core-revision.txt` against published `sase-core-rs` versions on PyPI.
  - If an unreleased core commit is pinned, the train logs `CORE_LAG`, initiates an automated `sase-core` release dispatch, and pauses SASE release promotion until the core wheel is live.

### 3.4 Developer Experience & Feedback Loop

- **Landing State Tracking & Notifications:**
  - Agents finish their turn upon reaching the durable **armed** state (`gh pr merge --auto` executed and confirmed).
  - A host-side reconciler tracks the transition: `armed` $\to$ `queued` $\to$ `landed` (or `ejected`).
  - Upon merge, a system notification fires to alert the developer that the change is live on `origin/master`.
- **Pre-Landing Testing (`sase preview`):**
  - Developers can test an agent's changes immediately without waiting 15–30 minutes for the queue.
  - `sase preview <pr-number|agent>` sets up an ephemeral git worktree at the PR head commit and launches an editable subshell or runs commands against it, avoiding checkout divergence on the primary repository.

---

## 4. Delivery Plan & Epic Breakdown

```
[Today]  Step 0: Human Admin Ruleset (Force-push & deletion protection on master)
[Now]    Track 0: Restore PyPI Installability (sase-16p / sase-10d / PR #299 / v0.18.0)

               ┌──────────────────────────────────────────────┐
               │         Parallel Engineering Phase            │
               ├──────────────────────┬───────────────────────┤
               ▼                      ▼                       ▼
      [Epic A: Releases]      [Epic B: Gate]          [Epic C: Queue]
      - Build-once SHA        - Bounded rerun         - Landing state machine
      - Flake-aware qual      - Expiring quarantine   - Rebase adapter
      - Linux/macOS exercise  - Parity (.python-ver)  - Preview & notify
      - Retention invariant   - Shifted-clock canary  - Sandbox verification
      - Install canary        - False-red digest      
               │                      │                       │
               │                      ▼                       ▼
               │              [Mechanisms Live]       [Sandbox Suite Passed]
               │                      │                       │
               └──────────────────────┼───────────────────────┘
                                      ▼
                        [Epic D: Production Cutover]
                        - Production merge_group & integration-ready
                        - Low-risk pilot (docs, toobig, ratchets)
                        - Culprit finder & auto-revert
                        - 7-day soak (<3% false reds)
                        - Enforce queue default (bypass empty)
                        - Nightly release train active
```

### 4.1 Step 0: Human Administrative Action (Today)
- **Goal:** Place basic fences on `sase/master` immediately without affecting current agent push workflows.
- **Actions:**
  - Human maintainer executes GitHub CLI command or uses web UI to create `master-integrity` ruleset on `sase-org/sase`.
  - Target: `refs/heads/master`.
  - Rules enabled: Restrict deletions (`deletion`), Block force pushes (`non_fast_forward`).
  - Bypass list: Empty.
- **Verification:**
  - Read back via API: `gh api repos/sase-org/sase/rules/branches/master --jq '.[].type'` confirms exactly `deletion` and `non_fast_forward`.
  - Normal agent pushes continue uninhibited (fast-forward commits are unaffected).

### 4.2 Track 0: Emergency Release Relief (Parallel)
- **Goal:** Restore a functioning `pip install sase` on PyPI immediately.
- **Actions:**
  - Cut `sase-core-rs` release containing commit `916d5e3a`.
  - Update `pyproject.toml` floor in PR #299 to match the published core version.
  - Ensure Master Gate is green; merge PR #299 manually.
  - Trigger `publish.yml` to publish v0.18.0.
- **Verification:**
  - In a clean environment: `uv tool install sase==0.18.0` succeeds and `sase core health` passes.

### 4.3 Epic A: Exact-Candidate Releases, Install Guards, and Core Invariants
- **Scope:** `sase` release workflows, `sase-core` retention scripts, and release tooling.
- **Phases:**
  - **A1. Build-Once & Candidate Identity:** Export exact SHA, tag, and version from release-please; checkout exact SHA in `build`; generate sha256 digests; write candidate manifest. Configure `release-please` with `draft: true`.
  - **A2. Flake-Aware Qualification & Multi-OS Exercise:** Add `ref` input to `ci.yml`; implement bounded 1-shot rerun for $\le 3$ failed nodes; add clean-environment install exercise on `ubuntu-latest` and `macos-latest` testing CLI workflows and headless TUI.
  - **A3. Candidate Publishing & Attestation Hardening:** Key Trusted Publishing attestations to candidate SHA; require digest verification before upload; implement candidate-based upload resumption.
  - **A4. Honest Watcher & State Machine:** Upgrade `release_watch` to track candidate states (prepared, qualifying, published, confirmed); replace pre-merge Full CI requirement with candidate qualification.
  - **A5. Core Dependency Synchronization & Retention Invariant:** Implement `pypi_retention.py` protection preserving core versions for last $N \ge 2$ SASE releases; implement `CORE_LAG` detector in release train.
  - **A6. Daily Public Install Canary:** Automated scheduled action testing `uv tool install sase` in clean environment against public PyPI.
  - **A7. Decision Record:** Author decision record: "PyPI publishes exactly the qualified release SHA."
- **Independent Verification:**
  - *V-A1 (Moving Tip):* Advance `master` tip while candidate qualifies; verify that published wheel and attestation match candidate SHA, not tip.
  - *V-A2 (Flake Recovery):* Planted transient flake in qualification recovers via rerun, records `FLAKY:`, and allows release.
  - *V-A3 (Deterministic Failure):* Planted deterministic bug in 3.14 tests blocks candidate publication.
  - *V-A4 (Multi-OS Failure):* Planted macOS-specific startup crash blocks publication.
  - *V-A5 (Retention Safety):* Dry-run retention run in `sase-core` refuses to prune versions needed by published SASE versions.

### 4.4 Epic B: Trustworthy Gate & Drift Protection
- **Scope:** `sase` test harnesses, Master Gate workflows, and CI policies.
- **Phases:**
  - **B1. Master Gate Bounded Rerun:** Implement 1-shot serial rerun for $\le 3$ failed nodes in Master Gate test shards; emit `FLAKY:` annotations; file/increment `flake` beads.
  - **B2. Expiring Quarantine with Non-Gating Escalation:** Implement quarantine registry with max 14-day expiry. Expired entries fail hygiene check and escalate bead priority, but explicitly DO NOT fail the required gate.
  - **B3. Test Environment Parity:** Commit `.python-version` (3.12); enforce fail-fast check between local core and `sase-core-revision.txt`; ensure `if: always()` preserves reporting steps.
  - **B4. Drift Canaries:** Implement nightly tip gate run and +30-day shifted-clock gate run to detect time bombs.
  - **B5. False-Red Digest & SLO Tracking:** Publish weekly false-red rate digest; measure progress toward $<3\%$ false-red threshold.
  - **B6. Visual Lane Sharding Study:** Measure visual-test stability; determine preconditions for potential future promotion into gate.
  - **B7. Decision Record:** Author decision record: "CI reruns a failed node once and quarantines flakes with non-gating expiry."
- **Independent Verification:**
  - *V-B1 (Rerun Pass):* Transient flake passes on rerun, emits `FLAKY:`, and Master Gate concludes green.
  - *V-B2 (Quarantine Non-Blocking):* Expired quarantine entry flags hygiene violation but allows merge gate to pass.
  - *V-B3 (Clock Shift):* Planted future expiration date fails shifted-clock canary while keeping current gate green.
  - *V-B4 (Threshold):* Measured false-red rate over 7 consecutive days remains $<3\%$.

### 4.5 Epic C: Queue-Aware Landing Protocol & Developer Experience
- **Scope:** `sase-core` landing state machine, `sase-github` provider, `sase` CLI commands; verified on a dedicated throwaway sandbox repo.
- **Phases:**
  - **C1. Landing State Machine in `sase_core`:** Model states: `prepared`, `armed`, `queued`, `merged`, `ejected`, `superseded`. Ensure turn ends at `armed`.
  - **C2. GitHub Adapter Implementation:** Implement rebase merge queuing via `gh pr merge --auto --rebase` in `sase-github`; map PR head SHA to landed SHA.
  - **C3. Reconciler & Watcher:** Host-side daemon monitoring landing status; proves merge via tree equality and ancestor checks; updates beads upon confirmed landing.
  - **C4. Drift Handling & Witness Checks:** Implement base witness check on ejection; implement 3-strike circuit breaker and durable hold.
  - **C5. Developer Testing Tools:** Implement `sase preview` (isolated worktree at PR head) and landed desktop/terminal notifications.
  - **C6. Sandbox Infrastructure & Suite:** Create public scratch repo `sase-org/sase-sandbox`; configure merge queue ruleset.
  - **C7. Sandbox Verification Suite:** Run full battery of synthetic landings, concurrent PRs, conflicts, ejections, host restarts, and circuit breaker activations.
- **Independent Verification:**
  - *V-C1 (Single PR Landing):* PR queues, passes checks, lands via rebase; landed commit matches tested tree.
  - *V-C2 (Stacked Landing):* Multiple PRs queue concurrently; speculative builds rebase correctly; all land with linear history.
  - *V-C3 (Ejection & Rebuild):* Front PR fails; queue ejects front PR and automatically rebuilds rear PR; rear PR lands safely.
  - *V-C4 (Developer Preview):* `sase preview` successfully runs commands against unmerged PR code in an isolated worktree.
  - *V-C5 (Host Restart):* Host killed during queued state reconciles idempotently upon reboot without duplicating PRs.

### 4.6 Epic D: Production Cutover, Post-Submit Discipline, and Release Train
- **Scope:** `sase` production repository settings, `ci_watch`, and operational monitoring.
- **Entry Criteria:** Epic B mechanisms live and false-red rate $<3\%$; Epic C sandbox test suite completely green.
- **Phases:**
  - **D1. Production Workflow Integration:** Add `merge_group` trigger to `master-gate.yml`; wire event-aware `integration-ready` aggregate; drop heavy `ci.yml` triggers from PRs.
  - **D2. Ruleset Setup & Controlled Pilot:** Enable merge queue on `sase-org/sase` with maintainer bypass; route allowlisted agent traffic (docs, toobig, ratchets) through queue.
  - **D3. Post-Submit Discipline & Culprit Auto-Revert:** Implement 2-hour continuous release-blocking check; build deterministic culprit finder; integrate auto-revert protocol via queue-jump PR.
  - **D4. Pilot Soak & Latency Measurement:** Monitor real traffic for 7 days; verify landing p50 $<30$ min, p95 $<60$ min, runner waits $<5$ min.
  - **D5. Full Enforcement Cutover:** Set `landing.mode: queue` as project default; empty ruleset bypass list; remove direct push permissions.
  - **D6. Nightly Release Train Activation:** Enable automated nightly release qualification and publishing; enforce public install canary.
  - **D7. Decision Record:** Author decision record: "`master` lands only through the merge queue."
- **Independent Verification:**
  - *V-D1 (Production Rebase):* Allowlisted pilot PR lands through production queue; verify linear git history on `master`.
  - *V-D2 (Direct Push Refusal):* Direct push attempt to `master` is rejected by GitHub server ruleset.
  - *V-D3 (Auto-Revert):* Planted bug in post-submit release lane is isolated by culprit finder, automatically reverted via queue-jump PR, restoring green head within SLO.
  - *V-D4 (Full Release Cycle):* Nightly train automatically qualifies candidate, executes multi-OS exercise, publishes to PyPI, confirms public install, and marks release un-drafted without human intervention.

---

## 5. Architectural Comparison Matrix

| Dimension | Initial Proposal (Oct 11) | 4-Epic Reassessment (Oct 17) | Converged Architecture (Gem) |
|---|---|---|---|
| **Merge Method** | Merge commits | Rebase | **Rebase (one commit per PR)**; squash fallback |
| **PR Role** | Admission ticket | Admission ticket | **Admission ticket; 0 approvals** |
| **Turn Boundary** | End at "queued" | End at "armed" | **End at "armed"** (`gh pr merge --auto`) |
| **Check Inventory** | Fold visual into gate | N1: Admission, Release, Advisory | **N1 Three-Tier Inventory** |
| **Qualification Mode** | All-or-nothing Full CI | Release-blocking subset | **Flake-aware qualification** (bounded 1-shot rerun) |
| **Pre-Publish Smoke** | 1-OS import check | Wheel & sdist smoke | **Multi-OS exercise** (Ubuntu + macOS: CLI, health, TUI) |
| **Release Versioning** | Release-please tags tip | Release-please candidate SHA | **Release-please draft releases**; un-draft on PyPI pass |
| **Post-Submit Lane** | Scheduled Full CI (2h) | Full CI (2h or nightly) | **2h continuous lane + culprit auto-revert** |
| **Quarantine Expiry** | Fails lint/gate | Fails lint/gate | **Hygiene check & bead escalation** (never blocks gate) |
| **Core Retention** | Not addressed | Last $N \ge 2$ SASE versions | **Invariant enforced in core + fail-closed** |
| **Developer Testing** | Not addressed | Gaps identified | **`sase preview` worktree + landed notifications** |
| **Delivery Split** | 3 Phases (single flow) | 4 Epics + Step 0 / Track 0 | **4 Epics + Step 0 / Track 0** |

---

## 6. Risks, Fallbacks, and Open Questions

1. **Rebase Interaction in Speculative Queue Groups:**
   - *Risk:* If speculative merge groups rebase multiple PRs unpredictably, commit footers or signatures could mutate.
   - *Mitigation:* Epic C sandbox suite explicitly validates multi-PR rebase groups. If rebase exhibits defects under queue concurrency, fallback to `SQUASH` (with PR body formatted as commit body).
2. **Post-Submit Flake vs. Real Culprit Disambiguation:**
   - *Risk:* Automatic rollback could revert a good commit if post-submit tests flake.
   - *Mitigation:* Culprit finder enforces a strict $k$-of-$k$ confidence rule (e.g., failed 2 consecutive runs on candidate, passed 2 consecutive runs on parent) before opening a revert PR.
3. **Queue Wait Times During Agent Bursts:**
   - *Risk:* Multiple agent waves finishing simultaneously could queue 10+ PRs, increasing landing latency beyond 60 minutes.
   - *Mitigation:* Concurrency $K=2$ handles typical arrival bursts. If p95 exceeds 60 minutes, GitHub organization upgrade to Team plan increases concurrent runner allocation.
4. **macOS Runner Capacity in Public CI:**
   - *Risk:* Free macOS runners in GitHub Actions can experience queue wait delays.
   - *Mitigation:* Pre-publish exercise runs only on candidate releases (once nightly or on release dispatch), never on ordinary PR merge gates.

---

## 7. Conclusion

By synthesizing the 12 tagged research reports, we resolve the tensions that previously divided researchers. The converged architecture protects `master` with mechanical fences, guarantees exact-SHA release integrity, eliminates the false-red coin flip during qualification, exercises artifacts across operating systems before publishing, guards core dependency retention, and preserves developer velocity with preview tooling. 

Executing Step 0 today and Track 0 in parallel will restore immediate installability, while Epics A, B, and C progress in parallel toward a reliable, automated, and permanent production cutover in Epic D.
