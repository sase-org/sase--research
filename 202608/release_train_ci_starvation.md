---
create_time: 2026-08-26
updated_time: 2026-08-26
status: research
---

# Why the SASE Release Train Stalled: CI Latency Against Commit Velocity

**Research question:** `sase-org/sase` uses release-please to maintain a release PR and
the `ci_watch` chop to squash-merge it once every GitHub workflow is green. Master moves
fast enough that runs are constantly cancelled by later ones, and releases have stopped.
What is actually blocking the merge, and how should it be fixed?

**Scope:** `sase-org/sase` at `a3011392c` (version 0.16.0, release PR #284 pending),
`.github/workflows/{ci,publish,docs-deploy,pr-title}.yml`, the `ci_watch` chop in
`bbugyi200/bugyi-chops`, and `bbugyi200/actstat`. All GitHub Actions measurements were
taken on 2026-08-26 over the preceding 19.5 hours to 3 days; commit-cadence measurements
cover the last 400 master commits (126.8 hours). Nothing was changed — this is diagnosis
plus a recommended design.

## Bottom line

**The release train is not stalled by cancellations. It is stalled because master CI is
genuinely red, and it stays red because cancellations hide the failures from you.**

Two diseases are running at once, and they feed each other:

1. **Master CI has produced zero green runs in three days** — 165 cancelled, 33 failed,
   0 succeeded. The 33 that completed all failed on real, deterministic assertions.
   `ci_watch`'s very first gate is "is the default branch green," so the merge never even
   reaches the release-PR checks.
2. **Only ~13% of master commits ever get a completed CI run.** Master CI takes ~107
   minutes; commits land every ~11 minutes. GitHub keeps one running plus one pending run
   per concurrency group, so each new push cancels the pending one. Six or seven commits
   are skipped for every one that is verified.

Disease 2 causes disease 1. A regression that lands is not observed for hours, and when
it finally is, the failing run covers seven commits at once and names a SHA that is
already stale — so nobody can attribute it, and the next agent pushes on top of it.

The fix is not concurrency tuning. **Runners are not the constraint** — PR CI runs start
in 0.1 minutes, so the org is nowhere near its 20-slot ceiling; the 26–74 minute waits on
master are self-inflicted concurrency-group pending time. The fix is to apply the
project's own two-speed verification decision (`decisions:two-speed-verification`) to CI
itself: a **fast master gate (≤ 8 minutes) that runs on every commit and is the only
thing the release gate looks at**, plus a **heavy lane moved off the default branch onto
a cadence**. That takes
per-commit observation coverage from 13% to ~58% and the settled-tip fraction from ~14%
to ~68% of wall-clock, at 3% of the org's runner budget.

Then fix the red. Nothing releases until that is done.

## 1. What is actually happening

### 1.1 The release train has been stopped for 19 days

| Fact | Value |
| --- | --- |
| Open release PR | #284, `chore(master): release 0.17.0` |
| Created | 2026-08-07T13:57Z |
| Last shipped tag | `v0.16.0`, 2026-08-07 01:52 |
| Commits accumulated since `v0.16.0` | **1,589** |
| Elapsed | **19.5 days** |
| Commit rate | **81.7/day** (one every ~17.6 min mean, ~10.7 min median) |

The PR itself is healthy: `MERGEABLE`, `mergeStateStatus: CLEAN`, not a draft, correct
base. It has been merge-ready in every structural sense for over two weeks.

### 1.2 Master CI has produced zero green runs in three days

Every `CI` run on `master` from 2026-08-24T09:44Z to 2026-08-26T16:50Z:

| Conclusion | Count | Median lifetime |
| --- | --- | --- |
| `cancelled` | **165** | 6.5 min |
| `failure` | **33** | 106.8 min |
| `success` | **0** | — |

Per day: Aug 24 — 49 cancelled / 10 failed. Aug 25 — 95 / 15. Aug 26 (partial) — 21 / 8.

The two populations are structurally different. The 6.5-minute median for cancellations
is the signature of runs killed **while pending**, before a single job started. The
107-minute median for failures is the signature of runs that got the slot and ran to
completion.

### 1.3 The cancellations are concurrency-group churn, not runner starvation

`ci.yml` sets:

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/master' }}
```

The exemption for master is correct as far as it goes — the in-comment history records
that cancelling in-flight master runs meant no master run ever reached a terminal
conclusion. But **`cancel-in-progress: false` does not make the queue deep.** GitHub
allows exactly one running and one pending run per concurrency group regardless of the
setting; a newly queued run *replaces* the pending one, and the displaced run is marked
`cancelled` ([GitHub Docs][gh-concurrency]).

So with one master lane:

- A run occupies the lane for ~107 minutes.
- Commits arrive every ~11 minutes (median).
- Roughly ten commits arrive during one run; nine of them take turns in the single
  pending slot and are cancelled in sequence; the tenth inherits the lane.

Measured queue wait (`created` → first job start) for master CI runs that did start:
median **26.2 min**, max **74.0 min**.

The decisive control: the same measurement for PR CI runs, which sit in per-ref groups
and are therefore almost always alone:

```
PR CI queue wait (min), n=19: [0.0, 0.1, 0.1, ... , 0.2]   median=0.1   >5min: 0/19
```

**Runner slots are free.** The 26–74 minute master waits are entirely concurrency-group
pending time. This matters enormously for the fix: the current serialization is not
paying for a capacity shortage that exists today.

### 1.4 The release PR side is *not* the bottleneck

It is tempting to blame release-please regenerating the branch on every master push. It
does — the branch head moves every ~11 minutes — and `gh pr checks 284` intermittently
reports *no checks reported*, because the rollup is keyed to a head SHA that was just
force-pushed.

But the release branch's CI is nearly free and settles almost immediately. Every
source-based job is excluded by
`github.event.pull_request.head.ref != 'release-please--branches--master'`, leaving one
job:

```
run created 16:57:41Z → release-core-floor-smoke success (70s) → run complete 16:58:55Z
(build-core, lint, test, visual-test, coverage-contexts, perf-floors,
 ace-page-group-isolation, docs-build, contention-test: all skipped)
```

**73 seconds.** The empty-rollup window is roughly 75 seconds out of every 11 minutes —
about 11% of ticks. Real, worth fixing, but nowhere near a 19-day stall.

## 2. The gate `ci_watch` actually enforces

`plan_release_merge` in `bugyi_chops/ci_watch.py` requires **all** of these, in order:

| # | Condition | Failure reason | Status today |
| --- | --- | --- | --- |
| 1 | default branch state is `GREEN` | `default_branch_not_green` | **fails ~always** |
| 2 | exactly one release PR | `no_release_pr` / `ambiguous_release_prs` | passes |
| 3 | branch prefix, not draft, correct base | `not_release_pr` / … | passes |
| 4 | `mergeable == MERGEABLE` | `release_pr_not_mergeable` | passes |
| 5 | `mergeStateStatus == CLEAN` | `release_pr_not_clean` | passes |
| 6 | rollup non-empty | `release_pr_empty_rollup` | fails ~11% of ticks |
| 7 | every check `COMPLETED` and green | `release_pr_checks_not_green` | usually passes |
| 8 | no in-flight `Publish`/release-please run | `release_generator_busy` | fails ~35–45% |

Condition 1 is the wall. And it is stricter than "master CI passed" — `decide_repo`
requires the *settled* commit to still be the branch head:

```python
if base_state is RepoState.GREEN:
    if current:                       # head.sha.startswith(settled_sha)
        return RepoDecision(RepoState.GREEN, "green", head)
    return RepoDecision(RepoState.PENDING, "newer_head_unsettled", head)
```

So the gate asks a question about *right now*: **is the tip of master both settled and
green at this instant?** Not "did some recent commit pass."

Live evidence from an `actstat -f jsonl` sweep taken during this research:

```
sase-org/sase  e6eccc5  conclusion=failure
  Deploy Docs  success   (456s)
  Publish      success   (496s)
  CI           cancelled (1124s)   ← queued 16:28:31, displaced 16:47:15
```

`cancelled` is not in `GREEN_CONCLUSIONS`, and with no job-level red it is not
`actionably_red` either, so `classify_repo` returns `PENDING` → `default_branch_not_green`
→ no merge. Every tick, for 19 days.

## 3. The structural cause: latency against inter-push interval

The probability that the gate can *ever* pass is governed by one ratio: CI wall time `L`
against the distribution of gaps `G` between master pushes. Over the last 400 commits
(126.8 h, 399 gaps): mean 19.1 min, median **10.7 min**, p25 4.0, p75 20.0, p90 38.2.

Two derived quantities matter. **Settled-tip fraction** — the share of wall-clock during
which the tip has a completed run — is what a chop ticking every 5 minutes samples.
**Undisturbed-push fraction** — the share of commits whose own run finishes before the
next push — is what determines whether a failure can be *attributed to its author
commit*.

| Gate wall time `L` | Tip settled (% wall-clock) | Pushes verified undisturbed |
| ---: | ---: | ---: |
| 3 min | 85.6% | 81.7% |
| 5 min | 77.7% | 68.9% |
| **8 min** | **67.9%** | **57.9%** |
| 12 min | 57.0% | 46.1% |
| 15 min | 50.2% | 38.1% |
| 20 min | 41.7% | 25.1% |
| 30 min | 32.5% | 13.0% |
| 60 min | 20.4% | 4.0% |
| **107 min (today)** | **13.7%** | **2.0%** |

Read the last row carefully, because it is the crux and it is easy to get wrong.

At today's `L`, the tip is nominally settled ~14% of wall-clock — enough, in principle,
for a 5-minute-tick chop to catch. The settled-tip number is propped up by long overnight
gaps. So **scheduling alone is not a sufficient explanation for a 19-day stall**; the
missing multiplier is `P(green)`, which is measured at **0/33**.

The undisturbed-push column is where the damage is done: **2.0%**. Only about one master
commit in fifty gets a run that completes before the next push, and only ~13% get a
completed run at all (11 completions/day against 82 commits/day). That is the mechanism
that produced and sustains the red:

- A regression lands and is not observed for one to three hours.
- The run that eventually completes spans ~7 commits, so the failure has no author.
- `ci_watch` correctly reports it, but against a SHA that is already ~7 commits stale —
  the chop even has a dedicated `head_unsettled` state for exactly this.
- Seven more commits land during the investigation.

**Cancellation is not the disease; it is the symptom of an observation system running at
1/8 the rate of the thing it observes.** Fix the observation rate and the red becomes
attributable, fixable, and preventable.

## 4. The capacity budget

Measured cost of one master CI run (mean of three complete runs: `32976156802`,
`32961969407`, `32938975814`): **234 job-minutes**, 9 non-skipped jobs, 81–166 min wall.

| Job | Duration (min, observed range) |
| --- | --- |
| `test (3.13)` (`just test-cost`) | **72.7 – 90.6** |
| `coverage-contexts` (`just test-contexts`) | **44.1 – 46.4** |
| `test (3.12)` (`just test-cov`) | 37.1 – 45.0 |
| `test (3.14)` (`just test`) | 22.9 – 26.9 |
| `visual-test` | 13.2 – 18.9 |
| `build-core` (Rust, cached) | 8.1 – 10.3 |
| `perf-floors` | 5.0 – 6.2 |
| `lint` | 3.7 – 4.5 |
| `ace-page-group-isolation` | 1.3 – 1.6 |

Both repos are **public**, so GitHub-hosted standard-runner minutes are free. The binding
resource is the **20 concurrent jobs** allowed to a Free-plan *account*, shared across all
of `sase-org` ([GitHub Docs][gh-limits]). That is 28,800 job-minutes/day.

| Workload | job-min/day | % of org budget |
| --- | ---: | ---: |
| Verifying **every** master commit at today's cost (81.7 × 234) | 19,118 | **66%** |
| PR CI (~85 runs/day, similar shape) | ~17,000 | ~59% |
| Master CI **as actually executed** (11 completions/day) | 2,574 | 9% |
| Proposed fast gate (81.7 × ~12) | ~980 | **3.4%** |
| Proposed heavy lane (12 runs/day × ~220) | ~2,640 | 9% |

This reconciles the apparent contradiction in §1.3. Runners are free *today* precisely
because master is throttled to one-run-at-a-time. Simply deleting the concurrency block
would push demand to ~125% of the account ceiling and reproduce the org-wide starvation
that the `ci.yml` comment records as having stalled the `sase-core` v0.6.0 publish.

**You cannot afford to fully verify 82 commits/day at 234 job-minutes each. You can very
comfortably afford to verify all 82 at 12 job-minutes each.**

## 5. The red itself

The 33 completed runs fail on real, repeatable assertions — not flakes, not
infrastructure:

```
FAILED tests/test_models_panel_actions.py::test_panel_x_clears_active_override
  textual.widgets._option_list.OptionDoesNotExist: There is no option with an ID of 'small'
FAILED tests/test_models_panel_edit_outcomes.py::test_on_alias_edited_offers_commit_when_in_repo
  textual.css.query.NoMatches: No nodes match '#confirm-btn' on ConfirmActionModal
E  AssertionError: expect_state('artifacts_subtab', 'patches') timed out after 5.0s
     — last value was 'stitches'                       (visual-test, many occurrences)
error: Recipe `phase7-perf-check` failed                (perf-floors)
```

The same clusters recur across `test (3.12/3.13/3.14)`, `visual-test`, and
`coverage-contexts` in run after run. `179508566 fix: repair the three deterministic
master CI failure clusters` (2026-08-26 09:45) was an attempt at exactly this; the run at
13:46 still failed.

One aggravating factor worth separating out: `build-core` checks out `sase-org/sase-core`
at **unpinned HEAD**. A push to `sase-core` can turn `sase` master red with no `sase`
commit involved, and two runs of the same `sase` SHA are not reproducible. At 13%
observation coverage this is nearly impossible to diagnose.

## 6. Solution space

| Option | Effect on gate | Cost | Verdict |
| --- | --- | --- | --- |
| **A.** Per-SHA concurrency (`ci-${{ github.sha }}`) | every commit verified | 66% of account budget + PRs ⇒ ~125% | **Rejected** — recreates the starvation incident |
| **B.** GitHub merge queue | serialize + batch merges | requires all 82 commits/day to become PRs | **Rejected** — agents push directly; and the queue's own throughput ceiling is the same ratio problem ([Mergify][mergify], [TianPan][tianpan]) |
| **C.** Batch: verify every Nth commit | fewer runs | still ~107 min `L`; attribution still spans N commits | **Rejected** — treats symptom |
| **D.** Two-speed CI: fast blocking gate + heavy cadence lane | `L` 107 → ~6–8 min | ~3.4% + ~9% of budget | **Recommended** |
| **E.** Throttle release-please to a schedule | closes conditions 6 and 8 | negative (fewer runs) | **Recommended** (secondary) |
| **F.** Last-known-good release train: change `ci_watch` to cut from the newest green commit rather than the tip | removes the tip requirement entirely | chop + release-please target-branch changes | **Defer** — right answer if velocity doubles again |

Option D wins because it is the same decision the project already made for local
verification. `just check` (whole-repo lint gates + diff-scoped tests) versus
`just check-full` (every gate + full suite) is exactly this split, and CI currently runs
only the `check-full` half on every commit. **Extending two-speed verification to CI is
the smallest change consistent with the project's existing architecture.**

## 7. Recommended solution

### R0 — Fix the red first (prerequisite, blocks everything)

Nothing below produces a release while `test`, `visual-test`, `coverage-contexts` and
`perf-floors` fail deterministically. Work the four clusters in §5 to green on a pinned
`sase-core` SHA, verified with a local `just check-full` under `/sase_monitor`.

Do this first, but note it is *not* durable on its own — at 13% observation coverage the
next regression lands within hours and is again unattributable.

### R1 — Split `CI` into a fast master gate and a heavy lane *(the core fix)*

New workflow `master-gate.yml`, `on: push: branches: [master]`, target **≤ 8 minutes
wall, ~12 job-minutes**:

- `lint` (`just fmt-*-check`, `just lint`, `just validate`, `just build-check`) — ~4 min
- one scoped test leg on 3.12: `just test-scoped` against the merge-base, **not**
  `test-cov`, **not** `test-contexts` — ~4 min
- **Install `sase-core-rs` from PyPI at the declared floor.** Do not build the Rust core
  from source in the gate; that is 8–10 serial minutes and it belongs to the heavy lane.

Give it `concurrency: group: master-gate-${{ github.sha }}` — per-SHA, so nothing is ever
cancelled and every commit is attributable. At 3.4% of the account budget this is
affordable with a wide margin.

Strip `ci.yml`'s `push: [master]` trigger. It keeps `pull_request` unchanged.

### R2 — Move the heavy lane off the default branch

This is the subtle part, and it turns on how `actstat` attributes runs. From its README:

> **Settled:** for each repository, workflow runs from its **default branch** are grouped
> by commit SHA. […] every workflow run retained for that commit has completed. It does
> not mean that every workflow defined in the repository ran.

Two consequences:

1. A commit is "settled" based only on the workflows that **actually produced a run** for
   it. Removing heavy jobs from the master push path does not leave the commit unsettled
   — it settles faster.
2. There is **no event filter**. A `schedule` or `workflow_dispatch` run still targets the
   default branch and *will* attach to the tip SHA. So a heavy lane on a cron would
   re-poison the tip for ~90 minutes at a time.

Therefore: run the heavy lane on a **non-default branch**. Maintain `ci-full`; have a
small scheduled workflow (or an Axe chop) fast-forward `ci-full` to `master` every 2
hours; trigger `full.yml` on `push: branches: [ci-full]` with `cancel-in-progress: false`.
It carries `build-core` (source-built Rust), `test (3.12/3.13/3.14)`, `visual-test`,
`coverage-contexts`, `perf-floors`, `ace-page-group-isolation`. Twelve runs/day, ~9% of
budget, ≤ 2-hour blast radius, and `actstat` never sees it.

Trade-off to accept deliberately: `ci_watch` reports incidents from default-branch sweeps
only, so heavy-lane failures will not page you through the existing chop. Cover that with
GitHub's native workflow-failure notifications initially; a `ci_watch` extension that also
watches a named non-default branch is a good follow-up bead.

### R3 — Attack `test (3.13)` and `coverage-contexts` directly

Even in the heavy lane these two are 118–137 of the 234 job-minutes. `test (3.13)` runs
`just test-cost` at 72–91 min against `test (3.14)`'s 23–27 min for the same suite — a
3× gap that is cost-attribution overhead, not test coverage. Either move cost attribution
to a nightly-only leg or find the overhead. Same question for `test-contexts` at 44–46
min; `coverage_contexts.toml` already documents that this measurement was tuned once, so
the ratchet is worth re-running.

### R4 — Throttle release-please to a schedule

Change `publish.yml`'s release-please step from `on: push` to
`on: schedule` (every 2–4 h) `+ workflow_dispatch`. The release branch head then moves
6–12×/day instead of ~82×, which:

- eliminates the `release_pr_empty_rollup` window (condition 6);
- collapses `release_generator_busy` (condition 8) from ~35–45% of ticks to a few percent;
- lets the 73-second `release-core-floor-smoke` settle with hours to spare.

Keep the *publish* half on push (or fire `workflow_dispatch` immediately after `ci_watch`
merges) so a merged release PR still tags and ships promptly.

### R5 — Pin `sase-core` in CI

Record a `sase-core` SHA in-repo and have `build-core` check out that SHA rather than
HEAD, with a separate ratchet job that proposes bumps. This makes `sase` master CI
reproducible and stops `sase-core` pushes from silently reddening `sase`. (This overlaps
the existing `core_dependency_window_ratchet` research — coordinate rather than duplicate.)

### Suggested order

`R1` → `R0` → `R4` → `R2` → `R5` → `R3`.

R1 before R0 deliberately: land the fast gate *first* so that the repair work in R0 gets
per-commit signal instead of the 1-in-8 signal that let the red accumulate. R1 is
additive — it does not remove any existing coverage until R2 lands, and R2 is what
reclaims the budget.

### Expected end state

| Metric | Today | After R1–R2 |
| --- | ---: | ---: |
| Master gate wall time | ~107 min | ~6–8 min |
| Commits with an attributable completed run | 13% | ~58% |
| Tip settled (% wall-clock) | 13.7% | ~68% |
| Master runs cancelled | 165 / 3 days | ~0 |
| Regression detection latency | 1–3 h, ~7 commits | ~8 min, 1 commit |
| Account budget consumed by master | 9% (of a 66% need) | ~12.4% (of a 12.4% need) |
| Release merges possible per day | 0 | many windows/day |

## 8. Options rejected, with reasons

- **Delete the master `concurrency:` block.** Immediately correct-looking and wrong: §4
  shows demand goes to ~125% of the 20-slot account ceiling, which is the exact failure
  the block was added to prevent.
- **Set `cancel-in-progress: true` on master.** Already tried and recorded in `ci.yml`'s
  comment: no master run ever reaches a terminal conclusion, so CI produces no signal at
  all. Strictly worse than today.
- **Larger/self-hosted runners.** Buys wall-clock but not the ratio; the gate would still
  ask a question about the instantaneous tip. And it costs money to fix a scheduling
  problem that a 12-job-minute gate fixes for free.
- **GitHub merge queue.** Requires routing 82 commits/day through PRs. Even then the
  queue's throughput ceiling is governed by the same `L` versus arrival-rate ratio;
  batching helps only after `L` is reduced.
- **Slow the agents down.** The velocity is the point of the project. Design the
  verification system for the observed arrival rate instead.

## 9. Failure modes and safeguards

| Risk | Safeguard |
| --- | --- |
| Fast gate misses a regression the heavy lane would catch | Heavy lane still runs every 2 h; `just check-full` still gates epic landings. `just selection-health` already tracks whether scoped selection has ever been wrong — watch it. |
| Per-SHA gate concurrency reintroduces contention | Gate is ~12 job-min; even a 10-commit burst is 120 job-min against 1,200/hour. Monitor PR CI queue wait (§1.3) as the canary — it should stay under 1 min. |
| `ci-full` branch drifts or the fast-forward job wedges | Have the fast-forward workflow fail loudly and alert; the branch is disposable and re-derivable from master. |
| Heavy-lane failures go unnoticed once off the default branch | Enable native workflow-failure notifications immediately; file a bead to extend `ci_watch` with a watched-branch list. |
| Throttled release-please delays a release by up to 4 h | Acceptable against a 19-day stall; add `workflow_dispatch` for manual cuts. |
| Green gate + red heavy lane ⇒ a release ships with a real regression | Add the most recent heavy-lane conclusion as an advisory condition in `ci_watch` before enabling unattended merges again, or keep `merge_enabled` gated behind a manual confirmation until the heavy lane has been green for a full day. |

## 10. Acceptance criteria

1. `gh run list --workflow=master-gate.yml --branch=master --limit 50` shows **zero**
   `cancelled` conclusions.
2. Median master gate wall time ≤ 8 minutes over 50 consecutive runs.
3. ≥ 90% of master commits in a 24-hour window have a completed gate run
   (`gh api repos/sase-org/sase/actions/runs?head_sha=<sha>` non-empty and terminal).
4. `actstat -f jsonl | jq -r 'select(.repo=="sase-org/sase") | .conclusion'` reports
   `success` for a majority of samples taken 10 minutes apart over an hour.
5. `ci_watch`'s report shows `eligible` (or a reason other than `default_branch_not_green`)
   for `sase-org/sase` at least once per day.
6. PR CI queue wait stays ≤ 1 minute median after R1 ships.
7. `v0.17.0` is tagged and published.

## 11. Open decisions for the owner

1. **Which tests belong in the gate?** `just test-scoped` is the natural answer given the
   existing selector, but the gate runs on a *pushed* commit rather than a working tree —
   confirm `tools/select_tests` resolves a sensible baseline for `master~1..master`.
2. **`ci-full` branch versus extending `ci_watch` with a workflow allowlist.** The branch
   requires no chop change; a `gating_workflows` var in `ci_watch` is more principled
   ("the gate should name what it gates on") and would let the heavy lane stay on master.
   The branch is recommended as the faster path; the allowlist is the better long-term
   shape.
3. **Should R4's throttle be 2 h or 4 h?** Longer is cheaper and settles harder; shorter
   keeps the changelog closer to reality.
4. **Is option F (last-known-good release train) worth building now?** It permanently
   decouples release cadence from CI latency, so it survives another doubling of velocity.
   At 82 commits/day R1–R2 is sufficient; at 160/day it probably is not.

## Appendix: reproductions

```bash
# §1.2 — master CI outcome distribution
gh run list --workflow=ci.yml --branch=master --limit 200 \
  --json status,conclusion,createdAt,updatedAt \
  | jq -r '.[] | .conclusion // .status' | sort | uniq -c

# §1.3 — queue wait, master (concurrency-group pending) vs PR (runner slots)
gh run list --workflow=ci.yml --branch=master --limit 25 --json databaseId -q '.[].databaseId' \
  | while read -r id; do
      gh run view "$id" --json createdAt,jobs \
        -q '[( .jobs[] | select(.conclusion!="skipped") | .startedAt )] | min as $s
             | "\($s)  created=\(.createdAt)"'
    done
gh run list --workflow=ci.yml --event=pull_request --limit 20 --json databaseId -q '.[].databaseId' \
  | while read -r id; do gh run view "$id" --json createdAt,jobs; done   # → all ~0.1 min

# §1.4 — the release PR's real check cost
gh run list --branch release-please--branches--master --workflow=ci.yml --limit 1 \
  --json databaseId -q '.[0].databaseId' \
  | xargs -I{} gh run view {} --json createdAt,updatedAt,jobs

# §2 — what the chop sees right now
actstat -f jsonl | grep '"repo":"sase-org/sase"'

# §3 — inter-push gap distribution
git log --format=%ct -400 | tac | awk 'NR>1{print ($1-p)/60} {p=$1}' | sort -n

# §4 — job-minute cost of one master CI run
gh run view 32976156802 --json jobs \
  -q '[.jobs[] | select(.conclusion!="skipped")
       | ((.completedAt|fromdate) - (.startedAt|fromdate))/60] | add'

# §5 — the deterministic failures
gh run view 32976156802 --log-failed | grep -E '^\S+\s+.*(FAILED |^E  |error: Recipe)'
```

## Sources

- [Control the concurrency of workflows and jobs — GitHub Docs][gh-concurrency]
- [Actions limits — GitHub Docs][gh-limits]
- [GitHub Merge Queue Was Step One. Real CI Orchestration Comes Next. — Mergify][mergify]
- [The Merge Queue Is the New Bottleneck — TianPan.co][tianpan]
- [Merge Queues for Large Monorepos — Aviator][aviator]
- [release-please — googleapis/release-please][release-please]

[gh-concurrency]: https://docs.github.com/actions/writing-workflows/choosing-what-your-workflow-does/control-the-concurrency-of-workflows-and-jobs
[gh-limits]: https://docs.github.com/en/actions/reference/limits
[mergify]: https://mergify.com/blog/github-merge-queue-was-step-one-real-ci-orchestration-comes-next
[tianpan]: https://tianpan.co/blog/2026-07-02-the-merge-queue-is-the-new-bottleneck
[aviator]: https://www.aviator.co/blog/merge-queues-for-large-monorepos/
[release-please]: https://github.com/googleapis/release-please
