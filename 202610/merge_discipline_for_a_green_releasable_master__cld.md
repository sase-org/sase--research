# Merge discipline for sase: a green, releasable `master`

> **Research query:** After reading `gastown_vs_sase_lessons_to_borrow.md`, it seems like
> sase needs better merge discipline. We need a way to ensure that `master` stays green so
> we can publish new versions of sase to PyPI more often. Do we need a PR-only (protected
> `master`) workflow to achieve this, is that recommended anyway, or is there another way?
> Critique the plan, adjust the requirements where justified (calling the adjustments
> out), and end with a recommended solution.

**Researcher:** cld · **Date:** 2026-10-17 · **sase revision:** `134d3bcf5a` (`master`)

---

## Bottom line

1. **Yes, protect `master`. Agents should land through a GitHub merge queue, with no
   human-review requirement.** That is a different thing from a "PR-only" workflow for
   humans. Every sase landing is already mechanical: the host's `builtin@commit` finalizer
   rebases and pushes. Turning a push into "push a branch, open a PR, enqueue it" is a
   change to the finalizer's configuration. It is not a change to how anyone works. GitHub
   merge queue is free for public organization repos, and `sase-org/sase` is one.
2. **Merge discipline alone would not have shipped a single release in the last seven
   weeks.** PyPI has served `0.17.1` since 2026-08-29, and release PR #299 has been open
   for 48 days. A release currently needs all of the following at once, at the moving tip:
   - **Master Gate green at HEAD.** It passed 62 of its last 1,000 runs.
   - **A fresh green Full CI run.** It passed **1 of 271 runs since 2026-08-27**. Its
     `visual-test` job failed in every run I sampled.
   - **A published `sase-core-rs` that meets the floor.** The last watch ended
     `CORE_FLOOR_BLOCKED`.

   That joint state essentially never occurs.
3. **[Requirement adjustment] The real requirement is "a releasable commit always exists
   and gets published", not "HEAD is always green".** The fastest lever for releasing
   more often is to **release from the newest commit that passed the release gate (last
   known good), not from HEAD.** The August `release_gate_liveness` plan already lists
   this as deferred: "the owner … expects to build it soon". It is now overdue.
4. **A merge queue needs a trustworthy gate first.** On an otherwise healthy tree, about
   **30–40% of Master Gate runs fail on a single TUI timing flake** that passes on the
   next SHA. At that false-red rate, any refusal mechanism would bounce about a third of
   good changes, whether it runs on GitHub or locally. Flake policy is step 0: one bounded
   rerun, plus a quarantine where every entry expires.
5. **The August decision to reject a merge queue should be reopened.** It gave two
   reasons:
   - **"PR-ifying ~74 direct-push commits/day."** The host finalizer makes that a mechanical
     change.
   - **"The same arrival/service ratio."** The measured numbers fit:
     - Arrivals average about 45 a day.
     - A strictly serial queue of 15.5-minute gate runs can serve about 93 a day.
     - Bursts of up to 14 pushes an hour need build concurrency of 3–4, which the 20-job
       Free-plan cap cannot supply alongside Full CI.

   The decision's own reopen trigger, "gate p50 stops fitting the commit cadence", has
   also arrived: **44% of pushes land before the previous gate finishes.**
6. **Don't make the agent host the gate.** The Gas Town report's R1 proposed a local
   landing lane, and the 2026-10-01 report proposed a local receipt refusal. Both put the
   gate on the host. But the host is the scarce resource
   (`decisions:two-speed-verification`). Local `check` passed **10 of 405** recorded runs
   on this machine, and local results differ from CI on Python version and core binary.
   GitHub runners are free, clean, and a real fence. Keep `just check` as a pre-flight,
   not the gate.

---

## 1. What is actually happening (evidence, 2026-09-27 → 2026-10-17)

### 1.1 Headline numbers

- **Master Gate, last 1,000 push runs** (Sep 27 → Oct 17): **62 green (6.2%)**
  (`gh run list --workflow master-gate.yml`). Only Oct 1, 9, 11 and 13–16 had any greens
  at all.
- **Longest green streak** in those runs: **11 consecutive** (Oct 14 15:30Z). Every other
  streak was 1–5 runs long.
- **Full CI**, scheduled every 2 h: **1 green in 271 runs since Aug 27**, and that one was
  the Aug 29 run that shipped 0.17.x. `visual-test` was red in all 10 runs I sampled
  (Oct 13–16). The same golden, `test_renamed_generic_agent_session_root_png_snapshot`,
  fails repeatedly.
- **Full CI cost:** about 273 job-minutes and about 100 minutes of wall time per run;
  `test (3.12)` alone takes 96.6 min.
- **Gate duration:** p50 12.7 min, p90 26.2 min, mean 15.5 min.
- **Push cadence:**
  - Gap between pushes: p50 16.5 min (p25 7.4).
  - Peak: **14 pushes in a single hour**.
  - Volume: **720 first-parent commits since Oct 1** (about 45 a day). All 720 carry
    `SASE_TYPE=stitch`, and 719 carry a `SASE_AGENT` footer.
- **Overlap:** **44%** of pushes land before the previous push's gate finishes.
- **Local `check` (ToolRun ledger on this host, Sep 20 → Oct 16):** **10 passed out of
  405 runs (2.5%)**: 323 failed, 64 were killed by a signal, and 8 were lost. p50 10.8 min,
  p90 54 min.
- **PyPI:**
  - Latest is `0.17.1` (2026-08-29); 49 days with no release.
  - Before that, 28 releases between Jun 11 and Aug 29, about one every 2.9 days.
- **Release PR #299** (`release 0.18.0`) has been open since Aug 30. The last watch
  (`sase-1lh.7.4`, Oct 16) ended **`CORE_FLOOR_BLOCKED`**: `release_reason=gating_workflow_red`
  and the release PR's `release-core-floor-smoke` failed.
- **Branch protection and rulesets:** none (`…/branches/master/protection` returns 404;
  `…/rulesets` returns `[]`).
- **Repo and plan:** `sase-org/sase` is **public** and the org is on the **Free** plan
  (20 concurrent hosted jobs).
- **Reverts since Sep 1:** **5**, against 2,607 commits.

### 1.2 "Red" is two different problems

I pulled the failed jobs for all 112 red gate runs since Oct 13 and the failing test names
for 17 of the single-shard reds:

- **Flake-shaped reds: 30 runs.** Only one or two test shards fail, and the failure is
  usually a single node that passes on the next SHA. The sampled nodes were almost all
  Textual/TUI timing tests:
  - `test_prompt_next_word_*`
  - `test_new_project_create_flow::test_typing_starts_no_sync_probe_and_settles_once`
  - `test_new_project_source::test_filter_and_enter_…`
  - `test_agent_archive_remaining_proof::test_mounted_arrival_then_clear_name_keeps_selection`
    (now bead `sase-1ls`)
  - `test_epic_panel_arrival_frames`
  - `test_prompt_bar_hot_spare`

  A few were short deterministic breaks, such as the bare-git provider registry and the
  project-label audit (`sase-1lx`).
- **Deterministic reds: 82 runs.** These fail `lint`, `docs`, or three or more shards.
  Examples from the gate at `ea84bd8786` (HEAD~1 right now):
  - `fake_launch() got an unexpected keyword argument 'extra_env'`. This is the same
    class of break as item #3 in the 2026-10-01 report, whose fix was to make the launch
    fakes accept `**kwargs`.
  - Docs-lint rule E5 ("Hand-written Reference pages must not name epic or phase labels")
    on seven pages.
  - Two help-text pins.
  - The project-label audit.

Against 44 greens over the same window, the 30 flake-shaped reds mean **a gate run on a
healthy tree fails roughly 30–40% of the time**, which is about 6% per shard. That
matters for every option below:

- With a real gate, a 35% false-red rate means a third of good changes bounce.
- Without one, it trains everyone to treat red as noise, which is exactly what the
  2026-10-01 report found ("a red result carries no information").

### 1.3 The release gate asks for a state the tip never reaches

`tools/release_watch` (about 2,250 lines across `_release_watch_engine.py` and
`_release_watch_api.py`) waits for all of the following at the same time:

- a green Master Gate **at HEAD**;
- a green Full CI fresher than `heavy_max_age_hours`;
- a release-please PR head that is not stale;
- a published `sase-core-rs` that meets the floor.

**Every release-blocking check outside the merge path drifts red and stays red.** Nothing
stops a change from breaking Full CI's `visual-test` or the 3.13/3.14 legs. Those jobs
run only on a schedule, and nobody owns them while they are red. Much of the watcher's
state machine works around this: stale-head refresh, `awaiting_core`, the
`MASTER_GATE_RED` budget, and blind shard reruns.

### 1.4 Promises have not held; fences have not been built

- **At least eight epics or child epics** since late September have aimed at "green CI,
  then ship 0.18.0": `sase-1c1`, `sase-1i5.9.1.2`, `sase-1io.7.6`, `sase-1jz`, `sase-1kl`,
  `sase-1kx`, `sase-1lh` and `sase-1lh.7` / `.7.5`.
- **Each repair produced a short green window, then a deterministic break overtook it.**
  The latest cycle:
  1. Master was green on Oct 13–15.
  2. By about 01:49Z on Oct 16, lint and four or more shards were red.
  3. 56 of the 62 runs that day failed.
- **The 2026-10-01 plan explicitly scoped out the keep-green contract.** Its
  `plan:202610/green_master_ci_repair.md` lists "the green-or-revert landing contract"
  and "`.python-version` parity" as out of scope. As of today:
  - `src/sase/finalizers/declaration.py:_verdict_provenance` still records
    `"unverified"` instead of refusing.
  - There is still no `.python-version`.
  - `master-gate.yml` still has zero `if: always()` steps, so a red `just lint` still
    skips `validate` and `build-check`.
- **The Gas Town report's lesson 7 applies directly: "Fences beat promises."** It is no
  failure of effort that each repair decays within about 36 hours. With about 45 agent
  landings a day and no refusal point, decay is the expected outcome.

---

## 2. Critique of the plan, and requirement adjustments

The instinct is right: sase needs merge discipline, and the Gas Town comparison
correctly identifies landing as the most expensive gap. But the request as framed, "keep
`master` green so we can release more often", has three weaknesses. I'd adjust it as
follows. Each adjustment is labelled.

> **[Adjustment A] Make releasability the goal; green `master` is the means.** The goal
> is "**a commit that passed the full release gate always exists, is at most about a day
> old, and gets published automatically**". Green `master` is necessary for that. It is
> not sufficient: §1.3 shows that the release gate requires checks the merge path never
> runs, plus a cross-repo core publication. A perfectly green Master Gate would still
> have produced zero releases since Aug 29, because Full CI was never green.

> **[Adjustment B] Replace "always green" with service levels.** "Always green" is not
> achievable at a 35% flake rate, and it is the wrong success metric even after flakes
> are fixed. Use these targets instead:
>
> - false-red rate per gate build **< 3%**;
> - **zero** deterministic failures in merge-gate jobs on `master`;
> - landing latency p50 **< 30 min** and p95 **< 2 h**;
> - newest release no more than **7 days** behind the newest candidate, and the candidate
>   no more than **24 h** old;
> - **0** human interventions per day for routine landings.

> **[Adjustment C] Add an invariant: release gate ⊆ merge gate, or the check has an owner
> and a clock.** Any check that can block a release must either:
>
> 1. block merges, so it cannot regress; or
> 2. have a named owner and a hard response deadline, with automation that enforces it.
>
> `visual-test` is the proof. It is deterministic by design (exact pixel equality with
> pinned fonts, per `lint_and_test.md`), yet it has been red for weeks. Only Full CI
> runs it, and Full CI is not on the merge path.

> **[Adjustment D] "PR-only" means a machine merge queue, not human review.** Requiring
> approvals would cut a 45-a-day pipeline to the maintainer's attention span. The PR here
> is only an entry in the merge queue. The host opens it, GitHub tests the integrated
> result, and GitHub merges it with no human in the loop. Human review stays where it is
> today, in plan and epic approval and in `#pr` Patches for anything the owner wants to
> read.

> **[Adjustment E] Gate trustworthiness is a prerequisite, not a follow-up.** No refusal
> mechanism should be turned on for a job whose false-red rate exceeds a few percent.

> **[Adjustment F] Include sase-core in the definition of "releasable".** A sase commit is
> releasable only if its pinned `sase-core-revision.txt` is contained in a *published*
> `sase-core-rs`. The release selector should then pick an older commit rather than block
> with `CORE_FLOOR_BLOCKED`. Frequent sase releases therefore also need sase-core releases
> to be cheap and routine.

**Is it a good idea at all?** Yes. The current direct-push model works only if every agent
lands green voluntarily. Local `check` passes 2.5% of the time, so agents cannot tell
whether they are landing green. The result is predictable: a 6% green rate, eight repair
epics, and a seven-week release drought.

There is a second-order benefit. Once `master` is green and fenced, a red local `check`
once again means "you broke it". That makes the agents' own verification informative
again, and it removes most of the reason for the KNOWN/UNKNOWN triage machinery that
exists to cope with an always-red base.

---

## 3. Options compared

| # | Option | What it guarantees | Main cost / risk | Fit for sase | Verdict |
|---|--------|--------------------|------------------|--------------|---------|
| 1 | Status quo plus repair epics and etiquette | Nothing; green decays in about 36 h (§1.4) | Endless repair treadmill; no releases | Measured failure | **Reject** |
| 2 | Host-side refusal (Oct 1 recs A and B: covering `pass` receipt, red-HEAD rule, fix-or-revert) | Blocks agents whose local check failed | Local signal is 2.5% pass, Python/core skew vs CI; burns host capacity; while HEAD is red, the red-HEAD rule freezes everyone; not a fence (any other push path bypasses it) | Medium; consistent with `host-owned-completion` | **Pre-flight only**, not the gate |
| 3 | Local mechanical landing lane (Gas Town R1: lease → rebase → verify → push → prove, with a ratchet) | Verifies the integrated tree and proves the SHA | Serializes landings behind a host-bound check (p90 54 min); the same skew as 2; L-sized build inside sase-core | Good mechanisms, wrong venue | **Borrow the mechanisms** and run them on GitHub |
| 4 | Required status checks on PRs, "require up to date", no queue | Each PR is green on the latest base | At 44% overlap, PRs keep going stale ("one commit behind") and re-running; the [DEV postmortem](https://dev.to/itaisagi/ai-agent-pull-requests-stuck-in-merge-conflicts-what-broke-in-our-merge-path-and-what-we-changed-4ni9) hit this at 15 merges/day | Poor | **Reject** |
| 5 | Required checks on PRs, *not* up to date | Each PR is green on *some* base | Semantic merge skew: two green PRs can make a red `master` | Weak | **Reject** |
| 6 | **GitHub merge queue plus ruleset** | Tests each entry on base + everything ahead; merges only green; blocks direct pushes | Async landing to build into sase; 20-job concurrency on Free; flake sensitivity; GitHub dependency | Strong: free for public org repos, clean environment, real fence, off the host | **Adopt** (§5) |
| 7 | Third-party queue (Mergify, Trunk, Aviator, Graphite) | Same as 6 plus flake-aware retry, two-step CI, bisected batches, priorities | Cost; another dependency; overkill at about 45 PRs/day | OK | **Revisit** only if 6's limits bite |
| 8 | Post-merge auto-revert bot (Google-style culprit finding) | Bounds red time | Culprit attribution at 44% overlap with flakes needs flake-aware bisection ([Google: Flake Aware Culprit Finding](https://research.google/pubs/what-breaks-google/)); revert churn breaks dependents; Google pairs it with presubmit, it is not a substitute | Medium | **Optional backstop** for the heavy lane only |
| 9 | **Release from last known good** (Chromium's LKGR idea: a promoted ref or tag) | Releases flow even while HEAD is red | Needs per-SHA queryability (already present); version-from-tag change | Strong; already planned as "deferred" in Aug | **Adopt first** (§5.2) |

Options 6 and 9 complement each other:

- **Option 9** gets releases flowing within days, even before `master` holds green.
- **Option 6** stops the tip from regressing, so candidates appear continuously instead of
  once every few weeks.

---

## 4. Re-examining the August rejection of a merge queue

`plan:202608/release_gate_liveness.md` §8 lists the merge queue as rejected because it
"requires PR-ifying ~74 direct-push commits/day and its throughput ceiling is governed by
the same arrival/service ratio". That rejection was then carried into
`decisions:ci-two-speed-split`. Both reasons deserve a second look:

1. **PR-ifying is mechanical in sase.** No agent creates commits, branches or PRs; the host
   finalizer does (`decisions:host-owned-completion`). sase already has a `#pr` workflow
   that branches, commits, pushes and opens a PR (`docs/reference/vcs/commit-workflows.md`),
   and `sase-github` already wraps `gh pr merge`. A `queue` landing mode is a finalizer
   variant plus a watcher, not a change in how agents work.
2. **Arrival and service numbers fit, given enough build concurrency.** The figures below
   assume a GitHub merge queue with build concurrency *K*. Each entry is built on base +
   all entries ahead of it; [GitHub docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)
   state that "Merge limits do not combine `merge_group` builds". The mean gate time is
   15.5 min.

   | K | Capacity (PRs/day at 100%) | Utilisation at 45/day | Utilisation at 74/day (Aug peak) | Burst of 14 in 1 h | Concurrent jobs (about 10–11 per build) |
   |---|---|---|---|---|---|
   | 1 | ~93 | 0.48 | 0.80 | ~3.6 h to drain | ~11 (fits Free's 20 with Full CI moved to nightly) |
   | 2 | ~186 | 0.24 | 0.40 | ~1.8 h | ~22 (exceeds Free's 20) |
   | 4 | ~372 | 0.12 | 0.20 | ~0.9 h | ~44 (needs Team's 60) |

   - **Free plan:** a serial queue (K=1) handles the average load. Burst hours, such as an
     epic wave landing five phases at once, back up for an hour or more.
   - **Team plan:** 60 concurrent standard-runner jobs ([GitHub Actions limits](https://docs.github.com/en/actions/reference/limits))
     support K=3–4. It costs about $4 per user per month for a one-seat org; check the
     current price before buying. That is the cheapest throughput lever available.
   - **Job-minutes:** unchanged. There is still one gate build per landed commit, run on
     `merge_group` instead of `push`, plus rebuilds after an ejection. Free public-repo
     minutes are not the constraint; concurrency is.
3. **The decision's own reopen condition is met.** `ci-two-speed-split` reopens "when the
   fast gate's p50 wall time stops fitting the commit cadence". With 44% of pushes
   overlapping the previous gate, it no longer fits.

**Conclusion:** record a new decision that supersedes the merge-queue clause of
`ci-two-speed-split`. The rest of that decision still holds: a per-SHA fast gate, the
heavy lane off the push path, and attributable SHAs.

---

## 5. Recommended design

### 5.0 Step 0: make the gate trustworthy (prerequisite, S–M)

1. **Bounded rerun in CI test jobs only.**
   - **The rerun:** after the sharded `pytest` pass, re-run just the failed node IDs once,
     serially. Skip the rerun if more than about 3 nodes failed, because that is a real
     break.
   - **Pass on rerun:** the job passes but emits a `FLAKY:` annotation and a JSON artifact.
     The landing watcher (§5.3) files or `+1`s a `flake` task bead by failure signature.
   - **Decision record:** this is a CI policy distinct from local ToolRun triage
     (`decisions:triage-annotates-does-not-change-exit-codes` stays as is), and it needs
     its own record.
2. **Quarantine with expiry, not muting.**
   - **The list:** a committed list, for example `tests/quarantine.yml`, with node ID,
     bead, owner, date added and expiry (14 days at most).
   - **Still running:** quarantined nodes run in a separate *non-required* `quarantine`
     job, so the signal is kept.
   - **No rot:** an expired entry fails lint.
   - **Precedent:** this follows GitLab's quarantine process
     ([handbook](https://handbook.gitlab.com/handbook/engineering/testing/quarantine-process))
     and the "two signals" pattern: a trustworthy required gate, plus a lane that runs the
     quarantined tests.
   - **Why it is needed:** the August plan's "do not mute" rule produced today's 35%
     false-red rate. An expiring quarantine whose tests still run is not muting.
3. **Parity.**
   - Commit `.python-version` = `3.12`. This is still missing; it was the Oct 1 rec C.
   - Fail fast when the local core differs from `sase-core-revision.txt`.
   - Add `if: always()` to Master Gate's `validate`, `validate-committed-plans` and
     `build-check` steps (Oct 1 rec D).
4. **Get one commit fully green once.** That includes `visual-test` (one stale golden) and
   Full CI's three test legs and lint. `sase-1lh` already owns this work. It is a one-time
   cost; §5.2 and §5.4 keep the result from being lost again.

### 5.1 Step 1: protected `master` with a merge queue (L in total; can start in pilot within days)

**GitHub configuration** (ruleset on `master`):

- **Push protection:** block force pushes and deletions. Require linear history.
- **Require merge queue:**
  - **Merge method:** **rebase**. This keeps each agent commit's message and
    `SASE_TYPE` / `SASE_AGENT` footers verbatim, and keeps first-parent tooling
    (`commit_change_set`) valid.
  - **Build concurrency:** 1 on Free, 3–4 on Team.
  - **Group size:** minimum 1, maximum 5, with a short wait (0–1 min), so a lone PR never
    waits for company.
  - **"Only merge non-failing pull requests": ON**, to keep attribution.
  - **Status-check timeout:** about 45 min (gate p90 is 26 min).
- **Require status checks:** the merge-gate job names. Add them gradually; see the
  ratchet in §5.5.
- **Required approvals:** **0**.
- **Bypass list:** **empty**. Agents run with the maintainer's credentials, so any bypass
  granted to the maintainer is also granted to every agent. That would recreate the
  promise the fence exists to replace.
  - **Emergency path:** an admin temporarily disables the ruleset, a deliberate and
    audited human action.
  - **Later:** move landings to a dedicated bot identity (a GitHub App or machine user).
    The maintainer's personal account can then hold a bypass without agents inheriting
    it.
- **Repo settings:** enable auto-merge and "delete branch on merge".

**Workflow changes:**

- **`master-gate.yml`:**
  - Add `merge_group:`. That trigger is mandatory: "You **must** use the `merge_group`
    event … The merge will fail as the required status check will not be reported"
    (GitHub docs).
  - Add `pull_request:`. GitHub requires the required checks to pass on the PR head
    before enqueue: "Once a pull request has passed all required branch protection
    checks, a user … can add the pull request to the queue."
  - Gate each expensive job with `if: github.event_name != 'pull_request'`. GitHub reports
    a job skipped by a conditional as successful, so the PR-level run is nearly free and
    the real build happens once, on the merge group. **Verify this in the pilot.**
  - Keep `workflow_dispatch`.
- **Drop the `push` trigger** once the pilot confirms that the SHA landing on `master` is
  the tested merge-group head. In that case the merge-group run *is* the per-SHA gate for
  that SHA, and `ci_watch` can keep querying "gate at SHA X".
- **Remove or narrow `ci.yml`'s `pull_request` trigger.** Otherwise every agent PR would
  start the 234–273 job-minute heavy lane, costing about 11k job-minutes a day and
  saturating the runners. The heavy lane stays `schedule` plus `workflow_dispatch`
  (§5.4).
- **Fold `visual-test` (check mode) into the merge gate,** split into 3 shards of about
  9–10 min instead of one 27.6-minute job. This is Adjustment C in practice. Agents whose
  change alters TUI output already owe `just fix-tui-screenshots`; the gate now enforces
  that.

### 5.2 Step 2: release from last known good (M; do this first or in parallel; it unblocks PyPI soonest)

Release-please always tags the commit that merges its release PR, which is HEAD-shaped
by construction. I found no documented way to make it release an older SHA. I therefore
recommend replacing the release-PR model with **tag-on-green**:

1. **Candidate selector.** A scheduled nightly job, also runnable on demand, picks the
   newest `master` SHA **S** such that:
   - **(a)** every merge-gate check is green **on S exactly**;
   - **(b)** the heavy lane is green **on S exactly**: dispatch Full CI on an `rc/<sha>`
     ref pointing at S, and don't accept a merely "recent" run;
   - **(c)** S's pinned `sase-core-revision.txt` is contained in a published
     `sase-core-rs` release, so the floor smoke passes. If it is not, fall back to an
     older S rather than block (Adjustment F);
   - **(d)** S has at least one `feat`/`fix` since the last tag.
2. **Version from tags.** Switch hatchling to **hatch-vcs**, a drop-in for the current
   `hatchling` backend, so the version comes from the tag instead of a committed bump.
   Generate the changelog into the GitHub Release notes, for example with release-please
   in changelog-only mode or git-cliff. The tag is created on S; no commit is needed.
3. **Publish on tag.** `publish.yml` triggers on `v*` tags. It builds from the tag, runs the
   existing `install-smoke` and `install-smoke-core-floor` jobs, and publishes through
   trusted publishing, unchanged.
4. **Core window.** Move the `sase-core-rs` requirement ratchet out of release time. Make
   it a bot PR through the queue whenever sase-core publishes. That is the same pattern as
   `core-pin-ratchet.yml`.
5. **Cadence.** Nightly automatic releases when a new candidate exists, plus manual
   dispatch. A red HEAD no longer blocks a release; it only means tonight's candidate is
   an older SHA.
6. **Delete complexity.** Most of `tools/release_watch` goes away:
   - stale-head refresh;
   - `CORE_FLOOR_BLOCKED` choreography;
   - the HEAD red budget;
   - blind shard reruns.

   What remains is "find candidate, verify, tag, confirm installation". The Aug plan said
   nothing should foreclose this; the per-SHA gate it built is exactly what makes it
   possible.

This change would ship a release as soon as §5.0's single fully green commit exists, even
before the merge queue is turned on.

### 5.3 Step 3: sase integration, an async, host-owned landing (L; core)

This keeps `host-owned-completion` and `single-turn-agents` intact. Domain logic goes in
`sase_core`, per the Rust-core boundary. GitHub specifics go in the `sase-github` VCS
provider.

1. **`builtin@commit` gains a `queue` landing mode** alongside today's `push`, behind a
   feature flag:
   1. rebase onto `origin/master`;
   2. commit;
   3. push `sase/land/<agent-name>`;
   4. `gh pr create`, with title and body taken from the commit message;
   5. `gh pr merge --auto --rebase`. Against a queue-protected branch, the docs say this
      enqueues once checks pass, or enables auto-merge until then. The GraphQL
      `enqueuePullRequest` mutation also exists.

   The finalizer proves *queued* (PR exists and is enqueued or has auto-merge on). The
   turn ends there.
2. **A deterministic landing watcher**, an axe chop or service proc with no LLM, tracks a
   landing record (`queued → merged | ejected`) for each landing:
   - **Merged:** prove that `master` contains the landed SHA (Gas Town's post-merge
     proof). Only then:
     - close the bead;
     - resolve `%w(bead=…)` waiters and epic dependents, which is Gas Town's
       merged-only dependency resolution;
     - update the STITCHES entry.
   - **Ejected, classified from check conclusions and failure signatures:**
     - *Conflict:* reuse the existing conflict-repair turn on a fresh rebase, then
       re-enqueue.
     - *Flake* (a known flake signature or quarantine match): re-enqueue once,
       automatically.
     - *Deterministic failure:* launch one repair turn that `#fork`s the original agent
       with the failing log excerpt, limited to 1–2 attempts. After that, raise a
       `/sase_gate` for the human; the agent never waits (`gates-never-block`).
   - **Safety:** never close a bead without merged proof. Stranded or ageing landing
     records surface in a Problems or Attention view and in a daily digest.
3. **Epics.**
   - Phase *N+1* starts once phase *N* is *merged*. That adds roughly the queue latency
     (15–30 min) per wave, a deliberate trade for never building on unlanded code.
   - Speculative stacking on a queued head can come later if the latency bites.
4. **Pilot.**
   - Route low-risk traffic through `queue` mode first: `toobig` splits and docs-only
     agents.
   - Measure ejection classes and latency for a week.
   - Then flip the default.
   - Keep `push` mode as the flagged fallback for GitHub outages, together with the
     ruleset-disable emergency path. Mergify recorded a merge-queue disruption on
     2026-08-17 caused by degraded GitHub APIs
     ([status](https://status.mergify.com/incidents/1qm55bs3q91s)), so outages are not
     hypothetical.

### 5.4 Step 4: give the heavy lane an owner and a clock (S–M)

- **Run it less often:** move Full CI from every 2 h to **nightly plus every release
  candidate**. Twelve red runs a day carry no information and occupy up to about 10 runner
  slots for about 83% of the day, which blocks raising merge-queue concurrency on Free.
- **Keep only 3.13/3.14, perf floors, coverage and the slow lanes there.** Anything
  deterministic and affordable moves into the merge gate (visual first; see Adjustment C).
- **Owner.** A red heavy run on a candidate files or `+1`s a `ci` bead by signature and
  launches a build-cop repair turn. Optionally it auto-reverts the culprit when a
  one-night bisect finds it unambiguously. This is the Google pattern, used only as a
  backstop.
- **Clock.** If the heavy lane stays red for 48 h, raise a high-severity notification:
  releases are pinned to an aging candidate. Make a merge-queue "stop the line" check (only
  `ci`-labelled repairs may land) available as opt-in config. Don't make it the default:
  stop-the-line combined with a flaky lane is how freezes become permanent.

### 5.5 Bootstrap without a freeze: ratchet the required checks (S)

`master` does not need to be fully green before the fence goes up:

1. **Day 0:** create the ruleset with the merge queue required and **only the jobs that
   are green on HEAD today** as required checks. Near HEAD today those would be
   `core-wheel`, plus `docs`, `lint` and any shard on its first green day. From that
   moment, those jobs cannot regress.
2. **Ratchet up:** a small `tools/ratchet_required_checks` script, run on a schedule,
   adds every merge-gate job that has been green on the last *N* `master` SHAs to the
   required set. It only tightens, never relaxes, just like the core-pin and
   shard-timings ratchets the repo already has.
3. **Quarantine to speed up:** quarantine each currently failing node (with a bead and an
   expiry) so its shard turns green and becomes required sooner.

This approach reuses the "ratchet against the tip" idea from Gas Town R1 and needs no
freeze. Unlike the 2026-10-01 freeze proposal, it cannot be overtaken by in-flight
agents, because every landing passes through the queue.

### 5.6 Decision records to write (through `/sase_memory_write`; not done here)

1. **"Master lands only through the merge queue."** This record:
   - supersedes the merge-queue clause of `ci-two-speed-split`;
   - refines `host-owned-completion`: *queued* proof completes the turn, and *merged*
     proof completes the landing.
2. **"Releases are cut from the newest fully green commit."** This promotes the August
   "deferred" item.
3. **"CI retries a failed node once and quarantines flakes with expiry."** This record
   sits next to `triage-annotates-does-not-change-exit-codes`.

### 5.7 What to measure

Measure these from the landing records and the GitHub API, with a weekly digest:

- **Gate reliability:** false-red rate, i.e. nodes that pass on rerun, against the < 3%
  target.
- **Ejections:** rate by class (conflict, flake, deterministic).
- **Landing latency:** p50 and p95.
- **Throughput:** queue depth at peak hours, which tells you when to raise concurrency.
- **Release health:** candidate age and release lag.
- **Fence health:** master red-minutes per day on required jobs, which should be zero;
  anything above zero means a check is not truly required.
- **Human load:** human interventions per day.

---

## 6. What I would not do

- **Don't make a host-side check the gate.** That covers option 2 (a host refusal on
  local check results) and option 3 (a local landing lane). Use them as an agent
  pre-flight only.
  - **The resource:** the host is the measured bottleneck.
  - **The signal:** local pass rates are near zero, and local results differ from CI.
  - **The fence:** neither stops a push from any other path.

  Gas Town R1's mechanisms are right: verify the integrated tip, prove the SHA, resolve
  dependents only on merge, ratchet. GitHub runners are the right place to run them.
- **Don't add a human-approval requirement** to the ruleset.
- **Don't use "require branches to be up to date" without a queue.** At 44% overlap, PRs
  churn.
- **Don't adopt a third-party queue or batch-then-bisect now.** Native GitHub covers
  about 45 PRs a day. Bisecting queues were explicitly not recommended at this volume in
  the Gas Town synthesis.
- **Don't launch more repair epics without a fence.** Eight of them have shown that green
  without a fence lasts about a day and a half.
- **Don't keep Full CI every 2 h as a release gate for the tip.** It has passed once since
  August and only adds noise.

---

## Recommended solution

**Adopt a protected `master` with a GitHub merge queue that agents land through
automatically, and release from the newest fully green commit instead of from HEAD.**
Sequence the work so releases resume first:

1. **This week: Step 0 and Step 2.**
   - Add one bounded node rerun and an expiring quarantine to CI.
   - Commit `.python-version` = 3.12.
   - Add `if: always()` to the masked steps.
   - Get *one* commit fully green, including the stale `visual-test` golden.
   - Switch releases to **tag-on-green**: a nightly candidate selector that requires the
     merge gate, the heavy lane, and the core floor to pass on the exact SHA, plus
     hatch-vcs versioning and a tag-triggered `publish.yml`.

   PyPI starts receiving releases as soon as that one commit exists, even if HEAD goes
   red again the next hour.
2. **Next week: Step 1 in pilot.**
   - Create the `master` ruleset: merge queue, rebase, build concurrency 1 on Free,
     0 approvals, empty bypass list.
   - Make the required checks a **ratchet** that starts from the jobs green today.
   - Run Master Gate on `merge_group`, skip its expensive jobs on `pull_request`, and stop
     `ci.yml` from running on agent PRs.
   - Fold sharded `visual-test` into the gate.
   - Route `toobig` and docs agents through a flagged `queue` landing mode.
3. **Weeks 2–4: Step 3, then flip the default.**
   - Build the deterministic landing watcher (merged-proof bead closure; ejection
     classification; one flake re-enqueue; one or two repair turns; then a human gate).
   - Make `queue` the default landing mode for `sase-org/sase`, and keep `push` only as a
     flagged outage fallback.
   - Move Full CI to nightly plus per-candidate runs, with an owner and a 48-hour clock.
   - If burst-hour queue waits exceed about an hour, upgrade the org to Team for 60
     concurrent jobs and raise build concurrency to 3–4.
4. **Then:**
   - Write the three decision records in §5.6.
   - Shrink `tools/release_watch` to the candidate, tag and confirm-install path.
   - Consider the same queue for `sase-core` `main`.

**Expected outcome:** releases are again limited by the rate of user-facing changes, not by
the state of the tip. The fence ends the treadmill: a deterministic break can no longer
reach `master` through any path. With the base green, an agent's own `check` becomes a
meaningful signal again.

---

## Method and confidence

- **High confidence (measured directly, 2026-10-17):**
  - Master Gate outcomes and durations for 1,000 runs, failed jobs for all 112 red runs
    since Oct 13, and failing node names for 17 single-shard reds plus HEAD~1.
  - Full CI history for 271 runs, with job durations and failures for 10.
  - The PyPI release history (from the JSON API) and the release-please PR history.
  - Branch-protection and ruleset API responses, repo visibility, and org plan.
  - This host's 405-run `check` ToolRun ledger.
  - `git log` counts for commits and reverts.
  - Source reads: `master-gate.yml`, `publish.yml`, `ci.yml`, `full.yml`,
    `tools/_release_watch_engine.py`, `src/sase/finalizers/declaration.py` and the
    receipt policy in `sase/sase.yml`.
  - Bead reads: `sase-1lh`, `sase-1lh.7.4`, `sase-um`, plus a bead search.
  - Plan reads: `plan:202608/release_gate_liveness.md` and
    `plan:202610/green_master_ci_repair.md`.
  - Decision records: `ci-two-speed-split`, `check-full-is-explicit`,
    `host-owned-completion`, `receipts-prove-before-they-skip`, `guarded-recipes`,
    `triage-annotates-does-not-change-exit-codes`.
- **Medium confidence:**
  - The flake share (30–40%) uses a "≤ 2 shards, test-only" heuristic, and some of those
    reds were short deterministic breaks.
  - The queue capacity model assumes mean gate time and steady arrivals.
- **Verify in the pilot (from documentation and memory, not tested here):**
  - that a job skipped by a conditional satisfies a required check on `pull_request`;
  - that the SHA landing on `master` equals the tested merge-group head under rebase
    merging;
  - current Team-plan pricing.
- **Not done:** no ruleset, queue, or workflow was changed. No pilot was run.

## Sources

**Repository and live data (sase @ `134d3bcf5a`):**

- `.github/workflows/{master-gate,publish,ci,full}.yml`, `release-please-config.json`,
  `pyproject.toml`.
- `tools/_release_watch_engine.py`, `docs/contribute/rust-backend.md` (published version
  window, watching a release), `docs/reference/vcs/commit-workflows.md`.
- `src/sase/finalizers/declaration.py`, `sase/sase.yml`.
- `sase-github` (`src/sase_github/workspace/submit.py`).
- `gh run list`/`gh run view` (Master Gate, Full CI), `gh pr list`, `gh api` (branch
  protection, rulesets, repo, org), the PyPI JSON API, and `sase tool runs -t check`.

**Prior research (read through `sase artifact read`):**

- `research:202610/gastown_vs_sase_lessons_to_borrow/gastown_vs_sase_lessons_to_borrow.md`
- `research:202610/master_ci_red_why_and_how_to_stay_green/master_ci_red_why_and_how_to_stay_green.md`
- `plan:202608/release_gate_liveness.md`, `plan:202610/green_master_ci_repair.md`

**Web:**

- [GitHub Docs: Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)
  (settings, `merge_group` requirement, removal on failure, build concurrency 1–100)
- [GitHub Docs: Merging a pull request with a merge queue](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/merging-a-pull-request-with-a-merge-queue)
  (`gh pr merge` enqueues; eligibility: public org repos, or Enterprise Cloud for private)
- [GitHub Docs: About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
  and [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
  (bypass lists, admin behaviour)
- [GitHub Changelog: merge queue GA (2023-07-12)](https://github.blog/changelog/2023-07-12-pull-request-merge-queue-is-now-generally-available/)
- [GitHub Docs: Actions limits](https://docs.github.com/en/actions/reference/limits)
  (20 / 40 / 60 / 500 concurrent standard jobs for Free / Pro / Team / Enterprise)
- [GitHub GraphQL: `enqueuePullRequest`](https://docs.github.com/en/enterprise-server@3.17/graphql/reference/pulls)
- [Uber: SubmitQueue, "Keeping master green at scale" (EuroSys 2019)](https://www.uber.com/at/en/blog/slashing-ci-costs-at-uber/)
  and [Efficient CI at scale: lessons from Uber](https://devops.com/efficient-ci-at-scale-lessons-from-uber/)
- [Google: What Breaks Google? (flake-aware culprit finding, auto-revert evidence)](https://research.google/pubs/what-breaks-google/)
  and [Who broke the build?](https://research.google/pubs/who-broke-the-build-automatically-identifying-changes-that-induce-test-failures-in-continuous-integration-at-google-scale/)
- [Mergify: the origin story of merge queues (the "Not Rocket Science" rule, bors)](https://mergify.com/blog/the-origin-story-of-merge-queues)
- [GitLab handbook: Test quarantine process](https://handbook.gitlab.com/handbook/engineering/testing/quarantine-process)
  and [OneUptime: quarantining flaky tests without training the team to ignore red](https://oneuptime.com/blog/post/2026-07-28-quarantine-flaky-tests/view)
- [DEV: AI agent PRs stuck in merge conflicts (strict up-to-date churn at about 15 merges/day)](https://dev.to/itaisagi/ai-agent-pull-requests-stuck-in-merge-conflicts-what-broke-in-our-merge-path-and-what-we-changed-4ni9)
- [TianPan: The merge queue is the new bottleneck (2026)](https://tianpan.co/blog/2026-07-02-the-merge-queue-is-the-new-bottleneck)
- [Mergify status: merge-queue disruption from degraded GitHub APIs (2026-08-17)](https://status.mergify.com/incidents/1qm55bs3q91s)
- [release-please-action](https://github.com/GoogleCloudPlatform/release-please-action)
  (it tags the merge commit of its release PR; no documented release-at-SHA)
