# Reassessing the merge-queue-fenced `master` plan: revised requirements and a four-epic split

> **Research query:** Reassess the solution proposed by
> `202610/merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md`
> (call it "the report"). Make whatever changes to its requirements are warranted, and
> call each change out clearly. Then recommend whether the work should be one epic or
> several. If several, justify the split and give each epic its own independent
> verification steps.

**Researcher:** cld · **Date:** 2026-10-17 · **sase `master`:** `60718e5b1b`. The report
was written at `4cb33feae9`, 19 commits earlier the same day.

## Bottom line

1. **The report's core design holds. Keep it.** That means a server-enforced native merge
   queue with zero approvals, exact-SHA releases, and a gate made trustworthy before it
   is enforced. I independently agree with its reasons for rejecting a host-side landing
   lane, required PRs without a queue, and human approvals.
2. **Five corrections change what gets built.** Each is backed by evidence the report did
   not have.
   - **[`pip install sase` is broken today.](#c1-the-newest-release-is-not-installable)**
     It installs **sase 0.1.0**. sase 0.17.1, the only current release, needs
     `sase-core-rs>=0.32.16,<0.33.0`, and PyPI retention deleted every 0.32.x around
     Sep 20. The report never mentions this. It makes "can users install the latest
     sase" the first requirement, ahead of "is `master` green".
   - **[The merge-commit method would corrupt the changelog.](#c2-merge-commits-would-corrupt-release-please-changelogs)**
     With merge commits, release-please writes each change into the changelog 2–3 times,
     and it can silently miss a change's commit. A simulation against release-please
     17.11.2 confirmed this. The repo's merge-commit message is *already* set to PR
     title plus body. Merge commits would also hide attribution from every tool that
     reads only first parents, and they would double commit counts.
     **Use rebase with one commit per PR.** This reverses the report.
   - **[A queue blocks bad landings, not drift.](#c3-the-queue-fences-landings-not-drift)**
     In the 17 hours since the report was written, `master` went red **20 of 20 times**.
     Four kinds of failure turned up in one day:
     - a flake;
     - a time bomb, where a test fixture used wall-clock timestamps;
     - a deterministic regression introduced by a landing;
     - a landing that calls a core binding no published `sase-core-rs` has.

     The queue stops only the third kind. Worse, a drifted (red) base fails every merge
     group. Under the report's ejection rules, that becomes a storm of repair turns. The
     design needs four protections: a base-red witness, a circuit breaker, a way for the
     base fix to jump the queue, and a canary that runs the gate under a shifted clock.
   - **[The release path needs a core-release step.](#c4-releasability-needs-a-core-step-and-a-retention-invariant)**
     "The core floor must be published" is right as a requirement, but the report gives
     no way to make it happen. Releases need a step that cuts a `sase-core` release on
     demand. PyPI retention needs an invariant: never delete core versions that a
     published sase still needs.
   - **[Landing mode is a product feature.](#c6-landing-mode-is-a-per-project-product-setting-not-a-flag)**
     The queue landing mode should be per-project configuration in the workspace
     provider. A feature flag kept for an outage fallback is not allowed: under SASE's
     flag rules, a choice users keep forever is a config field. And "beads close only on
     proof of merge" conflicts with three prompt templates that tell agents to close
     their own beads. Keep bead closing as it is, and make the *waits* landing-aware.
3. **[Smaller corrections](#c5-smaller-design-defects):**
   - the aggregate required check contradicts itself on `pull_request`;
   - rulesets cannot require `release-core-floor-smoke` only for the release PR;
   - the list of writers to `master` is incomplete;
   - `ci_watch` lives in an external repo, `bugyi-chops`;
   - "ship 0.18.0" duplicates the active `sase-1lh` chain.
4. **[Split the work into four epics](#recommendation-four-epics-not-one), plus two items
   outside them.** The two outside items:
   - **Step 0:** a few minutes of human admin work today;
   - **Track 0:** restore installability now, owned by the existing release work.

   The four epics:
   - **A. Honest, installable, exact-SHA releases.**
   - **B. A trustworthy gate.**
   - **C. Queue-aware landing in SASE**, a product feature verified on a sandbox repo.
   - **D. Cut `sase/master` over to the queue.**

   A, B and C can run in parallel. D starts only when B's soak criterion and C's sandbox
   verification are met. One epic would hold releases hostage to the largest piece of
   work. It would also span a week-long soak and two human-gated GitHub admin changes,
   and leave a beta flag in place for a month.

## What changed since the report was written

All figures below were measured at about 19:30–20:10 UTC on 2026-10-17, unless they cite
a bead.

- **The latest release cannot be installed.**
  - `uv pip compile` of `sase==0.17.1` on Python 3.12 fails: *"only
    sase-core-rs>=0.34.23 is available and sase>=0.17.1 depends on
    sase-core-rs>=0.32.16,<0.33.0"*.
  - An unpinned `sase` resolves to **`sase==0.1.0`**.
  - PyPI holds 51 `sase-core-rs` versions, from 0.34.23 to 0.41.0. There is no 0.32.x or
    0.33.x.
  - Cause: epic `sase-13t` ("Restore sase-core PyPI publishing and bound its storage
    growth", closed 2026-09-20) reclaimed space under the 10 GB PyPI limit and deleted
    the window every published sase pins. Bead `sase-10d` records the consequence, with
    6 corroborations, and is still `ready`. Bead `sase-1m4` records the user-visible
    symptom.
- **Master Gate has gone red 20 times in a row** since `4cb33feae9` (02:48Z) through
  `60718e5b1b` (19:31Z). Only **9 of the newest 100 runs** were green; the report
  counted 27.
- **Four kinds of failure appeared in that one day:**
  1. **A flake.** On `4cb33feae9`: `test_new_project_configure_review…`, the case the
     report analysed. Run `39062840842` also hit flake `sase-1lr`.
  2. **A time bomb.**
     - `test_agent_auto_restart_sweep_safety.py::test_disabled_path_resurfaces_silenced_once_and_ignores_others`
       failed in gate runs on `315092afeb`, `623574727b` and `a4465e18db`, and on all
       three Pythons in Full CI.
     - The fix, `f2a7b802f9`, is titled *"derive healer fixture timestamps from test
       clock"* (`sase-1ma`). The fixture had aged out. No landing caused it.
  3. **A deterministic regression introduced by a landing.**
     `test_deferred_wait_gates_before_claim_and_prepares_claimed_workspace` is "now
     failing in CI, not just locally". Source: the `sase-1lh.7.5.4.3.3.3` note citing
     runs `39061530695` and `39062840842`.
  4. **An unpublished core dependency.**
     - Since `667a5a83c0` (this morning), sase calls `mobile_pairing_issue`.
     - No published core passes `tools/check_sase_core_rs_bindings` against HEAD:
       0.41.0 and 0.40.1 lack `mobile_pairing_issue`, and 0.40.0 also lacks
       `project_clan_waves`.
     - `pyproject.toml` still declares `sase-core-rs>=0.35.0,<0.36.0`.
     - Source: the same bead note.
- **Full CI has improved.** In the latest failing run (`39046170656`), `visual-test`,
  `perf-floors` and `ace-page-group-isolation` passed. Only `test (3.12/3.13/3.14)` and
  `tutorial-tests` failed, mostly on the same tests the gate fails. The report said
  "`visual-test` was red in every run sampled", which is no longer true; the `sase-1lh`
  repairs landed.
- **The repair loop is still running.** About 40 plan files from September and October
  have names about releases, green CI, 0.18.0 or core floors: 18 in `plans/202609`, 23
  in `plans/202610`. Bead IDs now nest six levels deep
  (`sase-1lh.7.5.4.3.3.1`). This is the "promises, not fences" pattern the report
  describes, still going.

## Assessment

### What the report gets right (kept)

- **It diagnoses the real problem.** Nothing refuses a red landing. Master Gate only
  reports breakage after the fact. Repair epics decay.
- **It rejects the right alternatives.** A host-side landing lane runs on a slow and
  untrustworthy local signal, from two hosts, and fences nothing. Required PRs without a
  queue test against a stale base. Requiring "up to date" churns at 40% overlap. Human
  approvals deadlock on self-authored PRs.
- **It sets the right order.** Release honesty and gate trustworthiness come before
  enforcement, and "trustworthy before enforced" is the governing constraint.
- **Its capacity analysis is sound.** The queue simulation and the runner-wait
  measurements show flakiness is the binding constraint, not runner capacity. One
  caveat is in [C5](#c5-smaller-design-defects).
- **It reads `ci-two-speed-split` correctly.** A queue produces a per-SHA signal, and the
  record's own condition for reopening has been met.

### C1. The newest release is not installable

**What the report missed.** It treats releases as stalled. In fact they are *broken for
users*, a stronger condition. Since about Sep 20, anyone following the published install
instructions gets sase 0.1.0.

**Three consequences:**

1. **Requirement A is aimed at the wrong target.** "A release-qualified SHA under 24 h
   old" is the steady-state goal. The first goal is that the newest release resolves
   and installs.
2. **A release cadence alone does not prevent this class of failure.** Retention on
   another package (`sase-core-rs`) broke an already-published sase. Two things are
   needed:
   - a retention invariant;
   - a canary that installs from PyPI.

   Neither depends on landing discipline.
3. **Restoring installability cannot wait** for a gate soak or a queue pilot. It belongs
   in a track that ships the next release from whatever SHA qualifies (Track 0 below).

### C2. Merge commits would corrupt release-please changelogs

The report chose **merge commits** for three reasons:

- the April 2026 incident spared merge groups;
- merge commits preserve the agent's commit SHA;
- merge commits are the only method the repo allows today.

It did not check how release-please, which drives versioning and the changelog, handles
merge commits. I had a helper read release-please at `45e6e20` (v17.11.2) and run its
published modules on simulated history:

- **How it collects commits.** It walks the full history reachable from `master`, not
  just first parents (`src/github.ts:241-305`). It attaches both the merge commit and
  the agent commit to the same PR (`:357-385`). Nothing removes duplicates by PR.
- **How it splits messages.** `splitMessages` (`src/commit.ts:424-438`) starts a new
  entry wherever a message body contains a conventional header after a blank line.
- **Measured entries per change:**
  - **3** with the report's setting: PR title plus a description containing the full
    agent message;
  - **2** with title only;
  - **2** even with GitHub's default `Merge pull request #N…` subject, because the
    default body is the PR title.
- **The repo already uses the report's setting.** `gh api repos/sase-org/sase` returns
  `merge_commit_title: PR_TITLE` and `merge_commit_message: PR_BODY`. Under a
  merge-method queue, duplicates are guaranteed, not hypothetical.
- **It can also miss commits.**
  - Its stop condition (`src/manifest.ts:661-672`) assumes everything walked before the
    last release SHA is newer than that release.
  - Suppose an agent commit was authored before the release PR merged, and then merged
    through the queue after it. The walk can reach the release merge commit first and
    stop, never collecting the agent commit.
  - With merge commits, the conventional merge-commit title is then the only reliable
    carrier of that change, so whether duplicates appear depends on timing.
  - This leans on GraphQL history matching `git log` date order. That holds locally;
    GitHub does not document it.

**Merge commits would also break SASE's own history tools** (from the code map):

- **Tools that read only first parents lose attribution.** A merge commit carries no
  `SASE_AGENT`/`SASE_BEAD` footers. Affected:
  - `sase-core memory_history/query.rs:327-345`;
  - `file_history/index.rs:339`;
  - `src/sase/tool/triage_inputs.py:87` (`rev-list --first-parent`).
- **Commit-count thresholds double.** Examples: `axe/chop_policy_snapshots.py:96` (the
  `git.commits_since` threshold of 100), `updates/incoming_commits.py`, and
  `version/_git.py`.

**Revised choice: the rebase method, with exactly one commit per PR.**

- **Why it fits SASE:**
  - History stays linear.
  - The agent's full commit message, footers included, lands verbatim.
  - Every existing history tool keeps working.
  - It is what the finalizer already does today (`git rebase --autostash origin/master`
    at `_git_commit_dispatch.py:184-199`). The difference is that the result is now
    tested before it lands.
- **Cost: the landed SHA differs from the agent's local SHA.**
  - The landing record must map original SHA → landed SHA, and the host must republish
    stitch and agent-page references on merge.
  - The proof of merge becomes: the PR is `MERGED`, *and* its landed commit is on
    `master`, *and* that commit's tree equals the tree the merge group tested. A simple
    "`master` contains SHA X" no longer works.
- **Repair turns amend and force-push.** The PR stays one commit, and the repair
  re-enqueues with the new expected head. That keeps every `master` commit bisectable.
- **Fallback: squash.** It is release-please's recommended mode, and `pr-title.yml`
  already says "Validate squash-merge title". The PR body must then *exclude* the
  subject line, or `splitMessages` duplicates the change inside the squash commit.
  Squash also handles PRs with more than one commit.
- **The April 2026 incident does not decide this.** It was a fixed bug lasting hours. The
  status page names rebase among the affected methods and the blog does not. The
  tree-equality proof and the push-triggered audit gate guard against any method's
  regressions. A permanent changelog defect is the larger risk.
- **Enforce the choice.** Add the ruleset rule *"Require linear history"*.

### C3. The queue fences landings, not drift

A merge group's tree is the base plus the PR. If the base itself has turned red because
of something no landing did, every group fails. That includes:

- a time-bomb test (as today);
- a new release of an upstream dependency;
- a change to the runner image;
- a lapsed external credential.

Under the report's ejection rules, a "deterministic failure" gets one or two repair
turns, *for every PR in the queue*. At about 43 landings a day, one drifted test would
start dozens of repair agents chasing a failure none of them caused. The report's
"known flake signature re-enqueues once" rule does not catch it, because the drift is
deterministic.

**Required additions:**

1. **A base-red witness before any repair turn.**
   - Before classifying an ejection as the PR's fault, the landing watcher checks whether
     the failing node also fails on the base. Two sources: the base's latest gate run,
     or one scheduled run against the bare base.
   - This reuses the independent-witness rule from
     `triage-annotates-does-not-change-exit-codes`. KNOWN requires an independent
     witness.
2. **A circuit breaker.**
   - Trigger: N ejections in a row (start at 3) share a failure signature.
   - Response: pause admission of queue landings, using the existing hold machinery
     (`hold-pull-fail-open`). Raise **one** build-cop turn and one high-severity
     notification.
   - Agents still end their turns at "queued", and nothing blocks
     (`gates-never-block`).
3. **The base fix jumps the queue.** The GraphQL `enqueuePullRequest` input has a `jump`
   flag that puts a PR at the front of the queue. It may need admin rights; confirm in
   the sandbox. Without it, the fix for a red base waits behind PRs that are all doomed
   to fail.
4. **A drift canary on a schedule.**
   - Keep a scheduled gate run on the `master` tip; once the queue exists, the push
     trigger goes away. Run it at least nightly. Add one run under a clock shifted
     about +30 days, for example with `faketime` or a SASE test-clock variable.
   - The shifted run would have flagged today's `sase-1ma` fixture before it went off.
   - This goes in Epic B; it is cheap and pays off without a queue.

### C4. Releasability needs a core step and a retention invariant

Adjustment I in the report says "the `sase-core-rs` range a SHA needs must already be
published". The only mechanism it offers is keeping `release-core-floor-smoke` required
on the release PR, and that only *detects* the problem. Today, HEAD needs a binding no
published core has. The sase-core side caps releases at one cut a day
(`sase-13t.5`). This blocker recurs (`sase-10d`, `sase-n4.5.4.1`, `sase-rt.2`,
`sase-so.5.1`, and the 0.18.0 watch's `CORE_FLOOR_BLOCKED` exits).

**Required additions:**

1. **A core step in the release train.**
   - If the candidate's pinned `sase-core-revision.txt` is not contained in a published
     `sase-core-rs` within the declared range:
     1. dispatch the sase-core release (release-plz, respecting the daily cut);
     2. wait for PyPI;
     3. ratchet the floor on the release branch. `sync-release-metadata` already calls
        `tools/ratchet_core_window`.
   - Report a `CORE_LAG` reading on the release dashboard.
2. **A retention invariant in sase-core's PyPI retention tooling.** Never delete a
   `sase-core-rs` version inside the declared range of any of the last N published sase
   releases, with N ≥ 2. That is the bug class that broke installs on Sep 20.
3. **An install canary.**
   - Daily, in a clean environment, run `uv tool install sase`. Assert the installed
     version equals the newest PyPI release, then run `sase core health`.
   - On failure, file a bead or add a `+1`.
   - It would have caught the Sep 20 break within a day. It fails today, which is a good
     first check of the canary itself.

I considered a stronger rule and rejected it as the default: "the gate refuses any
landing whose pinned core is unpublished." It would make `master` always releasable
with respect to core. But every cross-repo change would wait for a core release, at
most one a day. Reconsider it if the automated core step proves unreliable.

### C5. Smaller design defects

- **The `integration-ready` aggregate contradicts itself.**
  - The report says to skip expensive gate jobs on `pull_request` and to make the
    aggregate "fail unless every dependency actually succeeded".
  - But the `gh pr merge` manual says that when the base requires a merge queue and
    "required checks have not yet passed, auto-merge will be enabled". So the PR must
    pass its required checks before it can be added to the queue.
  - With every dependency skipped on `pull_request`, the aggregate as specified would
    fail, and no PR could ever be enqueued.
  - **Fix:** make the aggregate depend on the event. On `pull_request`, pass when the
    cheap checks pass and the expensive jobs are *skipped*. On `merge_group`, require
    every dependency to be `success`.
- **Rulesets cannot require a check only for the release PR.**
  - Required checks apply to every PR into `master`. "Keep `release-core-floor-smoke` as
    an explicit part of the release PR's required checks" cannot be configured that way.
  - The release-branch conditions in `ci.yml` and `build-core.yml` read
    `github.event.pull_request.head.ref`, which does not exist on `merge_group`.
  - **Fix:** run the floor smoke and the install smokes in Epic A's post-merge `qualify`
    job, on the exact release SHA, as publish blockers. The pre-merge run on the release
    PR stays on `pull_request` only as an early warning.
  - Once the queue exists, the aggregate can detect that a group contains the release PR
    from its `pr-<N>` head ref and add packaging checks before merge. Then a version
    number is never burned on a failed qualification.
- **The list of writers to `master` is incomplete.** Adjustment J ("cover every writer")
  is right, but the host plan covers only the commit finalizer. Other code also pushes
  to the project branch:
  - `ace/revert_agent_transaction.py:121` (`git push origin <branch>`);
  - `post_write_operations.py:66-74` (`git pull --rebase` + `git push`, used by the TUI
    save-macro action and the stitch handler);
  - humans running `sase stitch create`.

  With an empty bypass list, every one of these is refused at enforcement. Each must
  honor the landing mode.
- **`ci_watch` is outside sase.**
  - The release PR is merged by `ci_watch`, at `bugyi-chops`
    `src/bugyi_chops/ci_watch.py:1293-1304`:
    `gh pr merge <N> --merge --match-head-commit <oid>`. Its configuration lives in
    chezmoi (`sase_athena.yml`).
  - It also looks up heavy checks by branch. `tools/release_watch` never merges; it only
    dispatches and reruns.
  - These changes belong in Epic D and touch an external repo plus the dotfiles.
- **"Ship 0.18.0" duplicates live work.**
  - Phase 0's step 5 overlaps the active `sase-1lh` chain, whose current watch is
    `sase-1lh.7.5.4.3.3.3`.
  - It also depends on things outside this program: a core release, and a green window
    at HEAD.
  - Drop it from the program. Track 0 owns "the next installable release", whatever its
    version.
- **The qualification set contradicts itself.**
  - Phase 0 says to qualify on "the full matrix: visual, 3.13 and 3.14, perf floors" and
    to make `publish` depend on it.
  - The next paragraph says that if the commit fails only on a lane the gate doesn't
    run, you should "fix forward and ship 0.18.1".
  - **Fix:** release-blocking checks are limited to the gate's checks plus packaging-only
    checks. Packaging-only means install smokes on 3.12 and 3.14, and the core-floor
    smoke. Checks that run only in the heavy lane run during qualification as advisory:
    they file beads and get an owner, but they do not block. They become blocking only
    once promoted into the gate. This is the report's own Adjustment F, applied
    consistently.
- **Capacity has a caveat.**
  - Master Gate is 11 jobs: `docs`, `core-wheel`, `lint` and 8 test shards. At build
    concurrency K=2, the peak demand is 22 jobs against the Free plan's 20-job cap.
  - That cap is shared with the rest of the `sase-org` organization, including
    sase-core's CI.
  - The report's 149 s p90 wait was measured at about 40% overlap. A busy queue at K=2
    overlaps nearly all the time.
  - This does not block the plan. Measure it in the pilot, and keep the report's
    fallbacks: K=1 or the Team plan.

### C6. Landing mode is a per-project product setting, not a flag

- **The report's plan:** "A queue landing mode for the commit finalizer, behind a feature
  flag", then "keep push mode behind the flag as an outage fallback".
- **The rule it breaks.** Under SASE's flag rules (`sase_flags.md`), a flag users are
  meant to keep choosing forever "was never a feature flag; add a normal config field".
  An agent creates a beta flag only as epic scaffolding, and that same epic removes the
  flag before it lands.
- **Why it must be configuration.** SASE is a product. Many projects will never have a
  merge queue: bare git, GitHub repos without rulesets, other users' repos. So
  `landing.mode: push | queue` is per-project configuration owned by the workspace
  provider. It defaults to `push`, sase-github implements `queue`, and the sase project
  is the first adopter.
- **This also fits the code.**
  - A PR path already exists: the `#pr` macro sets
    `SASE_COMMIT_METHOD=create_pull_request`, which reaches `vcs_create_pull_request`
    and `gh pr create`.
  - A merged-PR poller already exists: sase-github's `ws_generate_submitted_check_script`,
    consumed by `ace/scheduler/checks_runner.py`.
  - Queue mode should extend these, not build alongside them.
- **Keep beads closing as they do; make waits landing-aware.**
  - The report says "beads close and `%w(bead=…)` waiters resolve only on proof of
    merge". But agents close their own beads during their turn. Three templates instruct
    it: `bd/work_phase_bead` (`default_config.yml:2290-2291`), `bd/land_epic` and
    `bd/work_task`.
  - The finalizer also closes a bead after commit (`workflow.py:645-661`). Even in PR
    mode, that happens when the PR is created.
  - Moving closure to a watcher would rewrite the bead lifecycle and four agent-facing
    instructions, and would merge two separate facts: "the work is done" and "the code
    has landed".
  - **Better:** a bead still closes when the work is done. A `%w(bead=X)` wait, and
    epic-segment sequencing, resolve only when X is closed **and** X has no unresolved
    landing record (`queued` or `ejected`).
  - Agent waits (`%w(<agent>)`) key on `done.json`, which is written after the
    finalizers. They need the same landing predicate when used for epic sequencing
    (`bead/work_prompt.py:207-213`).
  - The landing record state machine lives in `sase_core`, as the report says; see
    `rust_core_backend_boundary`.

## Requirement changes

The report's requirements are labeled A–J; my changes are labeled R1–R15. Each entry
says whether it keeps, modifies or adds to a report requirement, and why.

**Kept as stated**

- **R1 (keeps D):** one admission path that the server enforces and that tests the
  integrated result. That means a native merge queue, with PRs as plumbing and zero
  approvals.
- **R2 (keeps E):** publish exactly what was qualified. Build once from the release SHA,
  record digests, and upload those exact files.
- **R3 (keeps G):** the gate must be trustworthy before it is enforced. Entry thresholds
  are in Epic D: false reds per build ≤10% for the pilot and <3% for enforcement.

**Modified**

- **R4 (modifies A).**
  - *Report:* "A release-qualified SHA under 24 h old exists and gets published on a
    cadence."
  - *Revised:* two tiers.
    1. **The newest PyPI release installs.** `uv tool install sase` resolves to the
       latest version in a clean environment, checked daily.
    2. Then the cadence: release lag of 7 days or less at first, then 1–3 days.
  - *Why:* installs have been broken since about Sep 20 ([C1](#c1-the-newest-release-is-not-installable)).
- **R5 (modifies B and F).**
  - *Report:* release-green is "the full matrix plus core-floor plus install smokes, all
    on the same SHA".
  - *Revised:* **release-blocking = the gate's checks ∪ packaging-only checks, on the
    exact SHA.** Packaging-only means the install smokes and the core floor. Checks that
    run only in the heavy lane are *advisory* for releases: they run, file beads, and
    get an owner and a deadline. They become blocking only once promoted into the gate.
  - *Why:* this removes the contradiction between "the full matrix blocks publishing"
    and "fix forward" ([C5](#c5-smaller-design-defects)). It also stops an untrusted
    heavy lane from blocking releases forever.
- **R6 (modifies H).**
  - *Report:* "beads close and waiters resolve only on proof of merge".
  - *Revised:* **"landed" is a separate, host-owned record.** A bead closes when its work
    is done, as today. Waits and epic sequencing additionally require that the bead's
    landing records are `merged`.
  - *Why:* it avoids rewriting the bead lifecycle and four agent instructions
    ([C6](#c6-landing-mode-is-a-per-project-product-setting-not-a-flag)).
- **R7 (modifies I).**
  - *Report:* the core range must already be published, checked by smoke tests.
  - *Revised:* the release train **creates** the core release when one is needed, and
    PyPI retention **never** deletes core versions inside the range of the last N (N ≥ 2)
    published sase releases.
  - *Why:* detection without a remedy recurs. Retention already broke installs once
    ([C4](#c4-releasability-needs-a-core-step-and-a-retention-invariant)).
- **R8 (modifies J).**
  - *Report:* admission control covers every writer.
  - *Revised:* the same requirement, made concrete. These must honor the landing mode:
    - the commit finalizer;
    - `revert_agent_transaction`;
    - `post_write_operations` (TUI saves);
    - humans running `sase stitch create`.

    During the pilot, the bypass list holds only the maintainer identity, and it is
    emptied at enforcement.
  - *Why:* several code paths push to the project branch today
    ([C5](#c5-smaller-design-defects)).
- **R9 (modifies C).**
  - *Report:* service levels for false reds, latency and release lag.
  - *Revised:* the same, plus two new service levels:
    - **days with install broken = 0**, from the install canary;
    - **days with the core lagging what HEAD needs**, reported but not a gate.
  - *Why:* these are the two failures that actually stopped users.

**New**

- **R10 (new; reverses the report's merge-method decision).**
  - *Requirement:* land with **rebase and one commit per PR**, enforced by "Require
    linear history". Squash is the fallback. Merge commits are rejected.
  - *Why:* release-please duplicates or drops changes under merge commits, history tools
    that read only first parents lose attribution, and commit counts double
    ([C2](#c2-merge-commits-would-corrupt-release-please-changelogs)).
- **R11 (new).**
  - *Requirement:* **handle drift.** Before any repair turn, check for a base-red
    witness. Trip a circuit breaker after N ejections in a row with the same signature,
    which holds admission and starts one build-cop turn. Let the base fix jump the queue.
    Run a nightly tip canary plus one run under a shifted clock.
  - *Why:* a red base fails every merge group, and the result is a storm of repair turns
    ([C3](#c3-the-queue-fences-landings-not-drift)).
- **R12 (new).**
  - *Requirement:* **landing mode is per-project configuration**, `landing.mode: push |
    queue`, owned by the workspace provider. It defaults to `push`, and sase-github
    implements `queue`. It is not a feature flag.
  - *Why:* SASE's flag rules, and the fact that SASE is a product
    ([C6](#c6-landing-mode-is-a-per-project-product-setting-not-a-flag)).
- **R13 (new).**
  - *Requirement:* **GitHub admin changes are human-gated decisions at epic
    boundaries:** rulesets, enabling the queue, removing bypasses. Agents propose them
    through `/sase_gate` and never apply them unasked.
  - *Why:* they face outward, are disruptive and are hard to reverse, so they need
    confirmation.
- **R14 (new).**
  - *Requirement:* **the aggregate required check depends on the event.** On
    `pull_request` it passes with expensive jobs skipped. On `merge_group` it requires
    every dependency to be `success`.
  - *Why:* a PR must pass its required checks before it can be enqueued
    ([C5](#c5-smaller-design-defects)).
- **R15 (new).**
  - *Requirement:* **one owner per goal.** "Ship 0.18.0" leaves this program. Track 0,
    meaning the existing `sase-1lh` chain or its successor, owns the next installable
    release.
  - *Why:* avoids duplicate epics, and the program's success no longer depends on factors
    it does not control.

**Dropped**

- Setting the merge-commit message to "PR title and description". It is already set, and
  it is harmful under merge commits.
- Keeping `release-core-floor-smoke` as a release-PR-only required check. Rulesets cannot
  express that; the check moves into `qualify`.
- Keeping push mode "behind the flag" as an outage fallback. Configuration replaces the
  flag.

## Revised solution in one paragraph

**Today, by a human:** a ruleset that blocks force pushes and deletion on `master`.

**Now:** Track 0 restores installability by shipping the next release from any qualified
SHA. The required core release and floor ratchet come first.

**Then three epics in parallel:**

- **A** makes publishing honest: exact SHA, digests, the gate's checks plus packaging
  checks as blockers, a core release on demand, a retention invariant and an install
  canary.
- **B** makes the gate trustworthy: one bounded rerun, an expiring quarantine, a canary
  under a shifted clock, parity fixes, and folding `visual-test` into the gate.
- **C** builds queue-aware landing as a per-project product feature, verified end to end
  on a sandbox repo. It includes landing records in core, the sase-github adapter,
  landing-aware waits, and drift-safe ejection handling.

**Finally, D** cuts `sase/master` over: a pilot first, then human-gated enforcement with
rebase, linear history, K=2 and an empty bypass list. After that, D drops the
push-triggered gate, moves the watchers to SHA lookups, and runs the nightly release
train.

## Recommendation: four epics, not one

### Why not a single epic

1. **Releases would be held hostage.** The release work (A) delivers user value within
   days, and is urgent because of [C1](#c1-the-newest-release-is-not-installable).
   Bundled with the queue work, the largest and riskiest piece, publishing fixes could
   not be called done until the queue cutover was.
2. **Soak periods and human gates belong at epic boundaries.** Enforcement needs 7 days
   of measured false reds below 3%, plus two human-gated admin changes. SASE agents are
   single-turn, and a land agent cannot verify a week of metrics within its turn. A
   single epic would sit open for 4–6 weeks with phases that are waits.
3. **Flag hygiene requires it.** Any beta scaffolding in the landing work has to be
   removed before the epic that added it lands. In one epic that spans the pilot and
   cutover, the scaffolding lives for weeks across unrelated phases.
4. **Each part has its own way to be proven.** A is proven on TestPyPI and with dry runs
   on a past SHA. B is proven with planted flakes and time bombs. C is proven end to end
   on a sandbox repo. D is proven only on the real repo. Separate epics let each part
   pass or fail on its own, and a failure in C (say, GitHub behaving differently in the
   sandbox) leaves A and B landed and useful.
5. **The parts touch different repos and owners.**
   - A: sase, plus sase-core retention and release.
   - B: sase tests and CI only.
   - C: sase-core, sase-github and sase.
   - D: sase workflows, GitHub settings, `bugyi-chops` (`ci_watch`) and the chezmoi
     configuration.
6. **The landing feature outlives this program.** C is useful to every SASE project that
   wants a queue, even if `sase/master` never enforced one.

### Why not more than four

- **Splitting C by repo would leave pieces nothing can verify.** A core landing record
  with no adapter, or an adapter with no landing-aware waits, can't be checked end to
  end. Cross-repo ordering within C is handled by its phases.
- **Merging A and B was considered and rejected.** Both are "signal" work. But A has to
  ship this week no matter what, while B's value is measured over weeks, and B's
  rerun-and-quarantine policy needs its own decision record.

### Epic map and dependencies

```
Step 0 (human, today)   ── ruleset: block force pushes and deletion on master
Track 0 (existing work) ── restore installability; next release from any qualified SHA
                                                     │ (independent)
Epic A  Honest installable releases  ────────────────┼──────────────┐
Epic B  Trustworthy gate             ─── soak met ───┤              │
Epic C  Queue-aware landing          ─── sandbox ok ─┴─► Epic D ◄───┘ (train needs A)
                                                         Cut over sase/master
A, B and C run in parallel. D's entry needs B's soak criterion and C's sandbox
verification. D's release-train phase needs A.
```

**Who owns which files**, to avoid merge conflicts between the parallel epics:

- **A:** `publish.yml`, plus `ci.yml`'s `workflow_call` inputs (the new `ref`), and
  `tools/release_watch*`.
- **B:** test infrastructure, `master-gate.yml` test-job steps, quarantine files, and
  `full.yml`'s schedule. It folds `visual-test` in *after* A2 lands, because both touch
  `ci.yml`.
- **C:** finalizer, waits, sase-core landing, sase-github, and the sandbox repo's
  workflows.
- **D:** `master-gate.yml` triggers and aggregate, `ci.yml`'s `pull_request` trigger,
  GitHub settings, and `ci_watch`.

### Step 0: human admin, today (not an epic)

- **Ruleset on `master`:** block force pushes and branch deletion. It does not affect
  today's workflow.
- **Tag ruleset for `v*`:** hold it. It helps only once the release identity differs
  from the credentials agents push with. I agree with the report here.
- Agents may propose both through `/sase_gate`.

### Track 0: restore installability (not an epic of this program)

- **Owner:** the existing `sase-1lh` chain, or a focused successor that absorbs
  `sase-10d`.
- **Goal:** a new sase release installs from PyPI. 0.18.0 or any later version will do.
- **Critical path:**
  1. Cut a `sase-core-rs` release that exposes `mobile_pairing_issue` and
     `project_clan_waves`.
  2. Ratchet the floor in the release PR.
  3. Fix the deterministic gate red
     (`test_deferred_wait_gates_before_claim_and_prepares_claimed_workspace`).
  4. Merge the release PR while HEAD is gate-green, or tag the release from a
     gate-green SHA.
- **Exit check:** in a clean environment, `uv tool install sase` reports the new
  version, and `sase core health --json` passes.
- **Watch out:** this track is the eighth-plus iteration of the repair loop. Box it to
  the critical path above, and send everything else to Epics A and B.

### Epic A: honest, installable, exact-SHA releases

*Repos: sase (plus sase-core for retention and release dispatch). Size: medium–large, 6
phases. Can start immediately. Decision record: "PyPI publishes exactly the qualified
release SHA".*

**Phases:**

1. **Build exactly the release SHA.**
   - `publish.yml` `build` uses `ref: ${{ needs.release.outputs.sha }}`. The
     release-please action exposes `sha` as "SHA that a GitHub release was tagged at".
     It is the release PR's `mergeCommit.oid` (`src/github-api.ts:700-714`;
     `src/strategies/base.ts:602,729`).
   - Assert that tag = SHA = `pyproject` version = `__version__`.
   - Build once, record sha256 digests, and pass the files between jobs.
2. **Qualify on the exact SHA.**
   - `ci.yml` `workflow_call` gains a `ref` input, threaded through every checkout.
   - The `qualify` job runs the R5 set as blockers: gate lint, docs and 8 shards; install
     smokes on 3.12 and 3.14; core floor.
   - Heavy-lane-only jobs run as advisory and file beads on failure.
   - `publish` needs `qualify`.
3. **Publish by tag.**
   - Replace `publish_existing` with an explicit tag input. It resolves the tag to its
     SHA and checks the digests before any partial re-upload.
   - Make the "tagged, not yet on PyPI" state explicit in `release_watch`, and evaluate
     release-please's `draft` option.
   - Relax the release watcher's pre-merge rule from "fresh green Full CI on *some* SHA"
     to "qualification of the exact release SHA after the merge".
4. **Core release on demand.** In the release train, check bindings against the newest
   published core (`tools/check_sase_core_rs_bindings`). If they are missing, dispatch
   sase-core release-plz, respecting the daily cut, wait for PyPI, then ratchet. Emit
   `CORE_LAG`.
5. **Retention invariant and install canary.**
   - **Retention:** sase-core's PyPI retention keeps every `sase-core-rs` version inside
     the declared range of the last N ≥ 2 published sase releases. It fails closed when
     it cannot compute that set.
   - **Canary:** a daily scheduled job runs `uv tool install sase` in a clean
     environment, then checks that the installed version equals the latest PyPI version
     and that `sase core health` passes. It files a bead or adds a `+1` on failure.
6. **Write the decision record and update the docs.**

**Independent verification.** None of these need a queue or a trustworthy gate.

- **V-A1 Exact SHA under a moving tip.**
  - Dispatch the new publish path in a dry-run or TestPyPI mode for a tag whose SHA is
    behind `master`.
  - The logged checkout SHA, the SHA stamped in the wheel's metadata, and the tag SHA
    must be identical.
  - The digests recorded by `qualify` must equal the digests uploaded to TestPyPI.
- **V-A2 Qualification blocks publishing.** On a scratch tag with a deliberately failing
  gate test, `publish` is skipped, and the release watcher reports "tagged, not
  published".
- **V-A3 Heavy-lane-only failures are advisory.** On a scratch tag where only an
  advisory job fails, `publish` proceeds, and a bead is filed or gets a `+1`.
- **V-A4 Core lag is detected.** Running the train step against today's HEAD reports
  `CORE_LAG` naming `mobile_pairing_issue`, and in sase-core's dry-run mode it would
  dispatch a release.
- **V-A5 Retention invariant.** In a dry run of the retention planner, any version in the
  declared range of the last two sase releases is marked keep. A planted plan that tries
  to delete one fails.
- **V-A6 Install canary.** Run once now, it **fails** (it resolves 0.1.0), which proves
  it detects the outage. After the first release through the new path it passes.
- **Exit:** the first real release published through the new path has PyPI file digests
  equal to the `qualify` digests and a tag SHA equal to the qualified SHA, and V-A6
  passes.

### Epic B: a trustworthy gate

*Repo: sase. Size: medium, 6 phases. Can start immediately. Decision record: "CI reruns
a failed node once and quarantines flakes with an expiry", alongside
`triage-annotates-does-not-change-exit-codes`.*

**Phases:**

1. **One bounded rerun inside the job.**
   - After the sharded run, rerun only the failed node IDs, once and serially. Skip the
     rerun when more than 3 nodes failed.
   - A pass on rerun emits a `FLAKY:` annotation and files a `flake` bead by failure
     signature, or `+1`s an existing one.
2. **An expiring quarantine.**
   - Each entry names a node, a bead, an owner and an expiry of at most 14 days.
     Quarantined tests still run, in a job that is not required. An expired entry fails
     lint.
   - Seed it with the repeat offenders:
     - `sase-1ls`;
     - `sase-1lr`;
     - `test_link_follow_seam`;
     - `test_review_back_restores_draft_…`;
     - the mid-word prompt tests.
3. **Parity fixes.**
   - Commit `.python-version` with 3.12.
   - Fail fast locally when the core differs from `sase-core-revision.txt`.
   - Add `if: always()` to the gate's lint steps.
4. **Drift canaries.**
   - A nightly gate run on the `master` tip.
   - One nightly run under a clock shifted about +30 days, flagging failures that occur
     only under the shift as time bombs.
5. **Bring heavy checks onto the merge path.** Fold `visual-test` (check mode) into the
   gate; it now passes in Full CI. Move Full CI from every 2 h to nightly plus release
   candidates. This runs after A2.
6. **A false-red digest.** A weekly report built from the annotations:
   - false reds per gate build;
   - red minutes per day;
   - time bombs caught.

**Independent verification:**

- **V-B1 A planted flake is absorbed.** A scratch-branch test that fails on its first
  attempt (via a marker file) and passes on rerun leaves the job green, emits a `FLAKY:`
  annotation, and files or `+1`s a flake bead.
- **V-B2 A planted deterministic failure is not masked.** It is still red after the
  rerun. With more than 3 failures, no rerun happens at all.
- **V-B3 Quarantine.** An expired entry fails lint, and a quarantined failing test still
  runs and reports in the non-required job.
- **V-B4 Time-bomb canary.** Re-introduce the pre-`f2a7b802f9` fixture on a scratch
  branch. The normal gate passes, and the run under the shifted clock fails and is
  flagged as a time bomb.
- **V-B5 Parity.** A local run with a mismatched core revision fails fast, naming both
  revisions.
- **Exit:** the mechanisms are proven and the digest is live with a baseline. The 7-day
  false-red soak (below 10% for the pilot, below 3% for enforcement) is **not** B's exit
  criterion. It is D's entry criterion, because it depends on the whole project's
  traffic, not just on B's code.

### Epic C: queue-aware landing in SASE, a product feature

*Repos: sase-core, sase-github and sase, plus a scratch public repo in `sase-org`. Size:
xlarge; it should be planned as an epic with 6–7 phases. Can start immediately. Decision
record: "Landed is a host-owned state distinct from turn completion", refining
`host-owned-completion`.*

**Phases:**

1. **Core landing records.** In `sase_core`, add the landing record and its state machine
   (`queued → merged | ejected | superseded | abandoned`). It holds:
   - the original SHA, landed SHA, tested group SHA and tree;
   - the PR number;
   - the ejection class.

   Add the wire format, API and bindings, and move the `sase-core-revision.txt` pin.
2. **The sase-github queue adapter.**
   - Push `sase/land/<agent>` and run `gh pr create`. The title is the commit subject;
     the body is the message *body*, without the subject line.
   - Enqueue with the expected head, using `gh pr merge --auto --match-head-commit` or
     GraphQL `enqueuePullRequest(expectedHeadOid)`, with `jump` for base repairs.
   - Extend the existing merged-PR poller to detect merges and ejections.
   - Fix `_submit_via_pr_merge` (`submit.py:219-276`): an exit status of 0 means queued,
     not merged.
3. **Landing mode in sase.**
   - Add the per-project `landing.mode` setting, defaulting to `push`.
   - Under `queue`, the finalizer creates the PR on the existing `create_pull_request`
     path, enforces one commit per PR, and ends the turn once the PR is queued.
   - `revert_agent_transaction`, `post_write_operations` and `sase stitch create` honor
     the mode.
4. **A landing watcher with no LLM**, run as an axe chop.
   - **Proof of merge:** the PR is `MERGED`, *and* its landed commit is on the base
     branch, *and* the landed tree equals the tested group's tree.
   - **On merge:** map the original SHA to the landed SHA and republish stitch and
     agent-page references.
   - **Waits:** make `%w(bead=…)` and epic-segment waits landing-aware (R6).
5. **Drift-safe ejection handling.** Classify each ejection as a conflict, a flake, a
   deterministic failure, or a red base (the latter only with an independent witness).
   - **Conflicts** go to the existing conflict-repair turn.
   - **Flakes** re-enqueue once.
   - **Deterministic failures** get at most 2 repair turns, forked from the original with
     the failing log excerpt. Repairs amend and force-push the PR.
   - **A red base** starts no repairs at all.
   - **Circuit breaker:** N ejections in a row with the same signature → a hold on
     admission, one build-cop turn, and a notification. Anything left unresolved goes to
     the human through `/sase_gate`.
6. **The sandbox repo.**
   - A scratch public repo with:
     - a ruleset requiring the merge queue, using rebase, linear history and K=2;
     - a toy gate with controllable pass, fail, flaky and time-bomb tests;
     - an event-aware `integration-ready` aggregate (R14).
   - Plus a scripted end-to-end harness.

**Independent verification**, all on the sandbox and none touching `sase/master`:

- **V-C1 Happy path.** A queued change lands.
  - The new `master` SHA equals the SHA the merge group tested.
  - The bead is closed, but a dependent `%w(bead=…)` resolves only after the merge.
  - Stitch and agent pages show the landed SHA.
- **V-C2 A deterministic failure is repaired.** The change is ejected, exactly one repair
  turn starts with the log excerpt, and the change re-enqueues and lands. The PR stays a
  single commit.
- **V-C3 Two changes conflict only in combination.** Each passes alone and they fail
  together. The second is ejected and classified deterministic, and the first lands.
- **V-C4 A drifted base is contained.** Detonate the sandbox's time bomb.
  - The first ejection is classified as a red base, and **no** repair turn starts.
  - After N ejections the circuit breaker holds admission and raises one gate.
  - A base-fix PR that jumps the queue lands first, and admission resumes.
- **V-C5 Crash recovery.** Kill the host while a PR is queued. On restart, records
  reconcile, no duplicate PR appears, and the landing completes.
- **V-C6 Push mode is unchanged.** The existing finalizer suite passes unchanged, and a
  sandbox project in `push` mode lands exactly as today.
- **V-C7 The questions the report left open.** Settle these on the sandbox:
  - Does "require merge queue" alone refuse a direct push?
  - Does a bypass actor still get through?
  - Does a job skipped by `if:` satisfy the requirement on `pull_request`?
  - Does `mergeCommit.oid` under rebase equal the landed head?
  - Does `jump` need admin rights?
- **Exit:** V-C1 through V-C7 pass in a scripted run that can be repeated.

### Epic D: cut `sase/master` over to the queue

*Repos: sase, `bugyi-chops` (`ci_watch`), chezmoi (configuration), and GitHub settings.
Size: medium, 6 phases, two of them human-gated and one a monitored soak.*

**Entry criteria:**

- **Epic B:** its mechanisms are live, and false reds per build have stayed at or below
  10% for 7 days.
- **Epic C:** it has passed its exit criterion.

**Phases:**

1. **Workflows on `sase`.**
   - Add the `merge_group` trigger and the event-aware `integration-ready` aggregate to
     `master-gate.yml`, with the cheap path on `pull_request`.
   - Drop `ci.yml`'s `pull_request` trigger; keep `workflow_call`.
   - Keep the push-triggered gate as an audit.
   - None of this changes behavior before the queue exists, because `merge_group` never
     fires.
2. **Enable the queue — human-gated.**
   - Allow auto-merge and rebase merges, and delete branches on merge.
   - Ruleset: merge queue required with the rebase method, K=2, groups of at most 5, only
     non-failing PRs merged, and a 60-minute timeout. Also require linear history and
     the `integration-ready` check.
   - **The bypass list holds the maintainer identity** for the pilot, so agents in push
     mode keep working.
3. **Pilot for one week.** Route low-risk agents (`toobig` splits, docs) through
   `landing.mode=queue` overrides. Measure:
   - ejection classes;
   - landing p50 and p95;
   - runner waits at K=2 against the 20-job cap.
4. **Enforce — human-gated.** The entry bar is now false reds **below 3%** over 7 days.
   - Empty the bypass list.
   - Set the sase project's `landing.mode` to `queue`.
   - Drop the push-triggered gate once lookups by SHA work.
   - **Watchers:**
     - `ci_watch` enqueues the release PR instead of merging it;
     - `ci_watch` heavy-check lookups and `release_watch` `_run_list` move from branch to
       SHA.
5. **Release train.**
   - Nightly, if there are `feat`/`fix` commits: run the core step (A4), then enqueue the
     release PR.
   - Packaging checks run in the merge group for the release PR, then `qualify` and
     `publish` (Epic A).
   - The heavy lane gets a build-cop turn, plus a high-severity notification if it stays
     red for 48 h.
6. **Decision records.**
   - "`master` lands only through the merge queue" supersedes the merge-queue clause of
     `ci-two-speed-split`. The record also lists the rebase rationale.
   - Update `host-owned-completion` with a reference to C's record.

**Independent verification**, on the real repo:

- **V-D1 The contract holds.**
  - A direct `git push origin HEAD:master` with agent credentials is refused.
  - A canary PR with a failing test does not move `master`.
  - Two canary PRs that fail only in combination: the second is ejected.
- **V-D2 Every commit was tested.** For every `master` commit after cutover, a script
  over `gh api` finds a successful `merge_group` run of `integration-ready` whose
  `head_sha` equals that commit. Zero exceptions.
- **V-D3 Service levels over 7 days.**
  - Landing p50 under 30 min and p95 under 60 min.
  - False reds per build under 3%.
  - Runner-wait p90 under 5 min.
  - Zero waits that resolved before their landing merged, per the landing records.
- **V-D4 The release train runs unattended.** At least one release is published by the
  nightly train with no human action. Days since the last release stays at 3 or fewer.
  The install canary stays green.
- **V-D5 The fallback works.** Disable the ruleset, set `landing.mode=push`, and land one
  change. Then restore both, with an audit log entry for each step.

## Risks and what would change this recommendation

- **The sandbox shows "require merge queue" cannot coexist with direct pushes, even for
  bypass actors.** Then D2 and D4 collapse into one hard cutover, and the pilot moves
  entirely to the sandbox (C). The epic split is otherwise unchanged.
- **Rebase merges in the queue behave unexpectedly.** For example, `mergeCommit.oid`
  might not be the landed head, or the landed SHA might differ from the group SHA. Then
  switch to squash, with a PR body that excludes the subject line. Do not switch to
  merge commits unless release-please moves to `changelog-type: github` and the tools
  that read only first parents are fixed.
- **False reds stay above 10% after B.** Delay D. B keeps paying off without a queue, and
  so do A and C.
- **The automated core step proves unreliable** (sase-core's own `master` red, the daily
  cut). Then adopt the stronger rule from C4: the gate refuses landings whose core pin is
  unpublished. Also consider the same fence for sase-core, whose `master` is unprotected
  too (`sase-core` `release-plz.yml:598-605`).
- **Track 0 keeps slipping.** If no installable release exists by the time A lands, use
  A's publish-by-tag path from the newest SHA that qualifies under R5, with a release
  branch carrying the version bump and floor ratchet. Do not wait for HEAD.

## Method, confidence, and limits

**How I read things:**

- the report, through `sase artifact read`;
- the research repo, through `sase repo open`;
- `sase-github`, `sase-core`, `googleapis/release-please` and
  `googleapis/release-please-action`, opened as linked or external repos by two helpers;
- memory, through `sase memory read`: the decisions `ci-two-speed-split`,
  `host-owned-completion`, `check-full-is-explicit`, `guarded-recipes`,
  `triage-annotates-does-not-change-exit-codes`, `single-turn-agents`,
  `gates-never-block` and `helpers-return-roots-declare`, and the notes
  `sase_beads.md`, `sase_flags.md` and `sase_sizes.md`;
- beads, through `sase bead read/search`.

**Measured directly (high confidence):**

- installability of `sase==0.17.1` and of unpinned `sase` (`uv pip compile`), and the
  `sase-core-rs` versions on PyPI;
- Master Gate conclusions for the last 100 runs and the failing jobs in 8 recent runs;
- failing jobs and tests in Full CI run `39046170656`;
- the state of release PR #299, the publish runs, and the GitHub releases;
- the repo's merge settings (`gh api repos/sase-org/sase`);
- `publish.yml`, `master-gate.yml`, `ci.yml`, `build-core.yml`, `full.yml` and
  `pr-title.yml` at `60718e5b1b`;
- line references I spot-checked: `default_config.yml:1947-1956,2288-2292`,
  `bead/work_prompt.py:207-213`, `tools/_release_watch_api.py:854-860`,
  `tool/triage_inputs.py:85-89`.

**From helpers (high to medium confidence):**

- **release-please's merge-commit behavior:** source reading plus a simulation run on
  the published 17.11.2 modules. The "missed commit" case assumes GraphQL history
  follows `git log` date order.
- **The SASE code map:** finalizer, PR path, bead-close sites, wait resolution, the
  history tools, writers, and `ci_watch`. File:line references come from the helper,
  apart from those I spot-checked.

**From bead notes (medium confidence):**

- the deterministic regression in `test_deferred_wait_gates_…`;
- the missing core bindings at HEAD;
- the cause of the retention damage (`sase-13t`, `sase-10d`).

**Inferred and not verified:**

- GitHub merge-queue behaviors listed under V-C7;
- whether `jump` needs admin rights;
- K=2 capacity under a busy queue.

**Not done:**

- no rulesets, workflows, memory files, or beads were changed;
- no follow-up beads were filed. The installability outage is already tracked by
  `sase-10d`/`sase-1m4`, and the proposed epics are for the lead to plan.

## Sources

**SASE, at `60718e5b1b` and the live APIs:**

- Workflows: `.github/workflows/{publish,master-gate,ci,build-core,full,pr-title}.yml`
- `release-please-config.json`, `pyproject.toml`
- `src/sase/default_config.yml`, `src/sase/bead/work_prompt.py`,
  `src/sase/vcs_provider/plugins/_git_commit_dispatch.py`,
  `src/sase/workflows/commit/workflow.py`, `src/sase/post_write_operations.py`,
  `src/sase/ace/revert_agent_transaction.py`, `src/sase/tool/triage_inputs.py`,
  `tools/_release_watch_api.py`
- `sase-github` `src/sase_github/workspace/{submit,workspace_plugin}.py`
- `bugyi-chops` `src/bugyi_chops/ci_watch.py`, via the helper
- `gh run list` and `gh api …/actions/runs/{id}/jobs` (Master Gate, Full CI, Publish),
  `gh pr list` (#299 and earlier), `gh release list`, PyPI JSON for `sase` and
  `sase-core-rs`
- Beads `sase-1lh.7.5.4.3.3.3`, `sase-10d`, `sase-13t`, `sase-1m4`
- Plan names under `plans/202609` and `plans/202610`

**Prior research:**

- `research:202610/merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md`
  (the report under review)

**External:**

- `googleapis/release-please` at `45e6e20` (v17.11.2): `src/github.ts:241-305,357-385`,
  `src/commit.ts:424-438,491-503`, `src/manifest.ts:637-679,1818-1826`,
  `src/strategies/base.ts:602,729`, `src/github-api.ts:700-714`
- `googleapis/release-please-action` at `0b6b3fc`: `src/index.ts:186-216`, README `sha`
  output
- [opendefensecloud/dev-kit#22](https://github.com/opendefensecloud/dev-kit/pull/22):
  the same release-please duplication under merge commits, fixed by switching to squash
- [GitHub Docs: Managing a merge queue](https://docs.github.com/en/enterprise-server@3.20/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue):
  `merge_group` is required, and failing checks remove the PR
- [GitHub GraphQL reference: `enqueuePullRequest`](https://docs.github.com/en/enterprise-server@3.17/graphql/reference/pulls)
  (`jump`, `expectedHeadOid`)
- `gh pr merge` manual: under a required merge queue, a PR whose required checks have not
  passed gets auto-merge enabled; once they pass, it is added to the queue
