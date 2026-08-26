---
create_time: 2026-08-26
updated_time: 2026-08-26
status: research
---

# Why the release gate never opens: CI latency against commit cadence

**Research question:** `sase-org/sase` uses release-please to maintain a release PR and
the `ci_watch` chop to merge it once every GitHub workflow is green. Master moves fast
enough that runs are continually cancelled by later ones, and releases have stopped.
What actually blocks the merge, and how should it be fixed?

**Scope:** `sase-org/sase` at `2cbe2f17d` (v0.16.0 shipped, release PR #284 pending),
`.github/workflows/{ci,publish,docs-deploy,pr-title}.yml`, `bbugyi200/bugyi-chops`
(`ci_watch`), `bbugyi200/actstat`, GitHub Actions run data and repository settings read
2026-08-26T17:05Z, and current GitHub documentation. Diagnosis only; nothing was
changed.

This report consolidates two independent research passes (`__a`, `__b` alongside it)
plus a third verification pass. Where the two disagreed, the disagreement is resolved
below against re-measured evidence.

## Bottom line

**Cancellation is a symptom, not the disease, and there is not one blocker but three.**
Each is independently sufficient to stop a release, so fixing any one alone changes
nothing.

1. **Liveness.** `ci_watch`'s first gate asks whether the *current tip of master* is
   both settled and green. Master CI takes ~107 minutes; commits land every ~11 minutes.
   GitHub keeps one running plus one pending run per concurrency group, so each push
   cancels the pending one and only ~13% of commits ever get a completed run. The tip is
   settled ~14% of wall-clock.
2. **Correctness.** Master CI has produced **zero green runs** in the measured window —
   166 cancelled, 33 failed, 0 succeeded. The failures are real, repeatable assertions.
   Even a perfectly live gate would find red.
3. **A latent merge failure.** `ci_watch` calls `gh pr merge --squash`
   (`ci_watch.py:869`), but the repository has `allow_squash_merge: false`. The first
   time gates 1 and 2 are ever satisfied, the merge still fails.

Blockers 1 and 2 feed each other: at 13% observation coverage a regression lands
unobserved, surfaces hours later in a run spanning ~7 commits with no attributable
author, and more commits land during the investigation. **The observation system runs at
roughly one eighth the rate of the thing it observes.**

The fix is not concurrency tuning. Runners are not the constraint — PR CI runs start in
~0 minutes, so the account is nowhere near its 20-job ceiling; the 26–74 minute master
waits are self-inflicted concurrency-group pending time. The fix is to apply the
project's own `decisions:two-speed-verification` to CI itself: a **fast per-SHA master
gate (≤ 8 min) that is the only thing the release gate reads**, plus the **heavy lane
moved off the default branch onto a cadence**. That is ~3% of the runner budget and
takes settled-tip from ~14% to ~68%.

## 1. Measurements

All figures below were re-measured independently for this report unless attributed.

### 1.1 The release train

| Fact | Value |
| --- | --- |
| Open release PR | #284, `chore(master): release 0.17.0` |
| Created | 2026-08-07T13:57Z (**19 days**) |
| State | `MERGEABLE`, `mergeStateStatus: CLEAN`, not draft, base `master` |
| Last shipped tag | `v0.16.0` |
| Commits since `v0.16.0` | ~1,589 |

The PR has been merge-ready in every structural sense for over two weeks.

### 1.2 Master CI outcomes

`gh run list --workflow=ci.yml --branch=master --limit 200`, spanning
2026-08-24T10:35Z → 2026-08-26T17:05Z:

| Conclusion | Count |
| --- | ---: |
| `cancelled` | **166** |
| `failure` | **33** |
| `success` | **0** |
| in progress | 1 |

Report `__a` sampled a narrower ~23.5 h window (56 cancelled / 12 failed / 0 success)
because a latest-500 query across *all* workflows truncates master CI. The two samples
agree in shape; `__b`'s wider window is the one carried forward, and this pass
reproduces it to within one run.

The two populations are structurally distinct. Cancellations have a ~6.5 min median
lifetime — the signature of runs killed *while pending*, before any job started; `__a`
spot-checked four (`32971100115`, `32980498606`, `32986438525`, `32988549998`) and found
**zero jobs** in each. Failures have a ~107 min median — runs that got the lane and ran
to completion. **No expensive work is being thrown away; signal is.**

### 1.3 Commit cadence

Last 400 master commits (126.7 h, 399 gaps): mean **19.1** min, **median 10.6**, p25
4.0, p75 19.9, p90 37.6 → **≈76 commits/day**. (`__b` reported 81.7/day over the same
nominal span; the difference is immaterial to every conclusion.)

### 1.4 Runners are free today

Queue wait (`created` → first job start) for the last 12 PR CI runs: **11 at 0.0 min,
1 at 0.1 min**. PR runs sit in per-ref groups and are almost always alone. Master CI's
measured 26.2 min median / 74.0 min max wait (`__b`) is therefore **entirely
concurrency-group pending time, not runner scarcity.**

### 1.5 The release PR side is not the bottleneck

Every source-based job is excluded for the release branch by
`github.event.pull_request.head.ref != 'release-please--branches--master'`, leaving one
job — `release-core-floor-smoke`, ~70 s, run complete in **73 seconds** (`__b`). The
`release_pr_empty_rollup` window is ~75 s out of every ~11 min, roughly **11% of ticks**.
Real, worth fixing, nowhere near a 19-day stall.

## 2. The gate `ci_watch` actually enforces

`plan_release_merge` requires all of these, in order (verified against source):

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

Condition 1 is the wall, and it is stricter than "master CI passed". `decide_repo`
requires the *settled* commit to still be the branch head:

```python
if base_state is RepoState.GREEN:
    if current:                       # head.sha.startswith(settled_sha)
        return RepoDecision(RepoState.GREEN, "green", head)
    return RepoDecision(RepoState.PENDING, "newer_head_unsettled", head)
```

`GREEN_CONCLUSIONS` is `{"success", "skipped", "neutral"}` — `cancelled` is not green,
and with no job-level red it is not `actionably_red` either, so `classify_repo` returns
`PENDING` → `default_branch_not_green`. Every tick, for 19 days.

The gate is fail-closed and, in isolation, correct. It simply cannot be satisfied when
HEAD moves ten times faster than CI settles.

## 3. The structural cause

Whether the gate can *ever* pass is governed by one ratio: CI wall time `L` against the
distribution of gaps `G` between pushes. Two derived quantities matter — **settled-tip
fraction** (share of wall-clock where the tip has a completed run, i.e. what a
5-minute-tick chop samples) and **undisturbed-push fraction** (share of commits whose
own run finishes before the next push, i.e. whether a failure is *attributable*).

| Gate wall time `L` | Tip settled | Pushes verified undisturbed |
| ---: | ---: | ---: |
| 5 min | 77.7% | 68.9% |
| **8 min** | **67.9%** | **57.9%** |
| 15 min | 50.2% | 38.1% |
| 30 min | 32.5% | 13.0% |
| **107 min (today)** | **13.7%** | **2.0%** |

Read the last row carefully. Settled-tip of ~14% is nominally enough for a 5-minute-tick
chop to catch, and it is propped up by long overnight gaps — so **latency alone does not
explain a 19-day stall**. The missing multiplier is `P(green)`, measured at **0/33**.

The undisturbed-push column is where the damage is done: **2.0%**. About one commit in
fifty gets a run that completes before the next push, and only ~13% get a completed run
at all. That is the mechanism that produced the red and sustains it.

## 4. Two aggravating factors

**The existing daily cron poisons the tip and steals the lane.** `ci.yml` carries
`schedule: cron '17 6 * * *'`, commented as a *"slow, intentionally contended flake
reproducer"*. Scheduled events run on the default branch, share the **same concurrency
group** `ci-refs/heads/master`, and attach to whatever tip SHA is current. Observed runs:

```
2026-08-26T07:10Z failure   152 min      2026-08-24T07:29Z failure  137 min
2026-08-25T07:10Z cancelled  74 min      2026-08-23T07:02Z failure   99 min
```

So once a day a workflow *designed to be flaky* occupies the single master lane for 1–2.5
hours and stamps `failure` on the tip that `ci_watch` reads. `__b` warned about this
hazard for a hypothetical future cron; it is already live.

**`sase-core` is checked out at unpinned HEAD.** `build-core` checks out
`sase-org/sase-core` at HEAD, so a push there can redden `sase` master with no `sase`
commit involved, and two runs of the same `sase` SHA are not reproducible. At 13%
observation coverage this is nearly undiagnosable.

## 5. The red itself — and it is narrowing

Failing jobs across the last 8 completed master CI failures:

```
2026-08-26T15:24Z  visual-test
2026-08-26T13:46Z  coverage-contexts, perf-floors, visual-test, test (3.13), test (3.12)
2026-08-26T11:10Z  visual-test, test (3.14), coverage-contexts, test (3.12)
2026-08-26T10:37Z  visual-test, coverage-contexts, test (3.14), test (3.12), test (3.13)
2026-08-26T07:10Z  visual-test, coverage-contexts, test (3.14), test (3.12), test (3.13)
2026-08-26T06:37Z  test (3.12), coverage-contexts, test (3.13), visual-test, test (3.14)
2026-08-26T02:31Z  perf-floors, visual-test, test (3.14), test (3.13), coverage-contexts
2026-08-26T01:40Z  visual-test, test (3.14), coverage-contexts, test (3.12)
```

This updates both source reports, which treated the red as a static set of four clusters.
The repair work is landing: the most recent run failed on **one** job where every prior
run failed on four to six. But **`visual-test` is present in 8/8** — it is the durable
blocker, and it is the one to fix first, not the four-cluster set.

Representative assertions (`__b`):

```
FAILED tests/test_models_panel_actions.py::test_panel_x_clears_active_override
  textual.widgets._option_list.OptionDoesNotExist: There is no option with an ID of 'small'
E  AssertionError: expect_state('artifacts_subtab', 'patches') timed out after 5.0s
     — last value was 'stitches'                       (visual-test, many occurrences)
error: Recipe `phase7-perf-check` failed                (perf-floors)
```

## 6. The capacity budget

Measured cost of one master CI run (`__b`, mean of three complete runs): **234
job-minutes** across 9 non-skipped jobs. `test (3.13)` alone is 72–91 min and
`coverage-contexts` 44–46 min — together over half the total.

Both repos are public, so GitHub-hosted standard-runner minutes are free. The binding
resource is the **20 concurrent jobs** allowed to a Free-plan *account*, shared across
all of `sase-org` — 28,800 job-minutes/day.

| Workload | job-min/day | % of budget |
| --- | ---: | ---: |
| Verifying **every** master commit at today's cost (76 × 234) | ~17,800 | **~62%** |
| PR CI (~85 runs/day) | ~17,000 | ~59% |
| Master CI **as actually executed** (11 completions/day) | ~2,600 | 9% |
| Proposed fast gate (76 × ~12) | ~910 | **~3.2%** |
| Proposed heavy lane (12 runs/day × ~220) | ~2,640 | ~9% |

This reconciles the apparent contradiction with §1.4: runners are free *today* precisely
because master is throttled to one run at a time. Deleting the concurrency block would
push demand past the account ceiling and reproduce the org-wide starvation that `ci.yml`'s
comment records as having stalled the `sase-core` v0.6.0 publish.

**You cannot afford to fully verify ~76 commits/day at 234 job-minutes each. You can very
comfortably afford to verify all of them at 12.**

*Worth knowing but not a fix:* a GitHub Team plan for `sase-org` raises the ceiling from
20 to 60 concurrent jobs for ~$4/user/month. That would make per-commit full CI
affordable — but it would **not** open the gate, because at `L`=107 min the tip is still
settled only ~14% of the time. This is a latency problem, and buying capacity does not
buy latency.

## 7. Resolving the two reports' central disagreement: the merge queue

Report `__a` recommends protecting `master` with a **GitHub merge queue** and changing
`ci_watch` to enqueue the release PR at the front via GraphQL `enqueuePullRequest`
(`expectedHeadOid` + `jump: true`). Report `__b` rejects merge queues outright. This is
the substantive conflict, and the evidence resolves it against `__a`.

**Finding: commits reach master by direct push, not through pull requests.** All 400 of
the last 400 master commits are single-parent, **zero** carry a `(#NNN)` squash-merge
subject, and all 200 most recent were committed by `Bryan Bugyi <bryanbugyi34@gmail.com>`
rather than GitHub's merge machinery. The repository confirms it: **0 rulesets**, master
returns `Branch not protected`, and `allow_auto_merge: false`. This matches the project's
own `decisions:host-owned-completion` — finalizers land commits directly.

A merge queue is enabled through a branch ruleset that *requires pull requests*. Adopting
it therefore means routing ~76 agent commits/day through PRs — a re-architecture of SASE's
landing model, not a CI configuration change. It also roughly doubles CI cost per commit
(PR CI *plus* a `merge_group` run) against a budget already ~59% consumed by PR CI alone.

**And `__a`'s own analysis refutes it.** `__a` correctly rejects `queue: max` on the
grounds that arrival rate (~11 min) far exceeds service rate (~107 min), so a FIFO merely
converts cancellation into unbounded backlog. That identical ratio governs a merge queue:
each entry must pass a `merge_group` check built from the same ~107-minute CI, giving a
ceiling near 13 merges/day against ~76 commits/day. **The queue becomes the new
bottleneck.** `__a` applies the ratio test to every alternative except its own
recommendation.

The kernel of `__a`'s idea is sound — the release cut needs a *stable serialization
point*. But that is obtainable without PR-ifying every commit, either by reducing `L` so
the tip settles often (§8, R1) or by cutting the release from the last known-good SHA
(§9, deferred option F). **Merge queue is the right long-term shape only if SASE ever
moves to PR-based landing; it is not the fix for now.**

### On `queue: max` — which directly answers the question as asked

`__a` is right and `__b` missed this: GitHub shipped a `queue` property in **May 2026**.
`queue: max` retains up to 100 pending runs per concurrency group, and requires
`cancel-in-progress: false`. So the literal complaint — *"every workflow gets cancelled
by a subsequent one"* — has a one-line configuration answer.

**It is still the wrong fix.** It would eliminate the cancellations while leaving the
release stalled, because at a 10× arrival-to-service ratio the tip would sit at the back
of a growing FIFO. Cancellation would become latency, and the exact-HEAD predicate would
get *slower*, not live. It is a good option for scarce serial deployments whose arrival
rate is below their service rate. That is not this workload — **until `L` comes down.**

## 8. Recommended solution

Extend the project's existing two-speed verification decision to CI. `just check`
(whole-repo lint gates + diff-scoped tests) versus `just check-full` (every gate + full
suite) is exactly this split, and CI currently runs only the `check-full` half on every
commit.

### R1 — Split `CI` into a fast master gate and a heavy lane *(the core fix)*

New `master-gate.yml`, `on: push: branches: [master]`, target **≤ 8 min wall / ~12
job-min**:

- `lint` (`just fmt-*-check`, `just lint`, `just validate`, `just build-check`) — ~4 min
- one scoped test leg on 3.12: `just test-scoped` against the merge-base — **not**
  `test-cov`, **not** `test-contexts` — ~4 min
- install `sase-core-rs` from PyPI at the declared floor; do **not** build the Rust core
  from source in the gate (8–10 serial minutes, and it belongs to the heavy lane)

Give it `concurrency: group: master-gate-${{ github.sha }}` — per-SHA, so **nothing is
ever cancelled** and every commit is attributable. Strip `ci.yml`'s `push: [master]`
trigger; leave `pull_request` unchanged.

### R2 — Move the heavy lane off the default branch

This turns on how `actstat` attributes runs, and the detail is decisive. Verified in
source: `fetch_default_branch_runs` requests
`/repos/{owner}/{repo}/actions/runs?branch=<default_branch>&per_page=100` — grouping by
SHA with **no event filter**. Two consequences:

1. A commit is "settled" based only on workflows that actually produced a run for it.
   Removing heavy jobs from the master push path does not leave commits unsettled — they
   settle *faster*.
2. A `schedule` or `workflow_dispatch` run still targets the default branch and **will**
   attach to the tip SHA. A heavy lane on a cron would re-poison the tip for ~90 minutes
   at a time — which is precisely what the existing flake-reproducer cron already does
   (§4).

Therefore run the heavy lane on a **non-default branch**: maintain `ci-full`, fast-forward
it to `master` every 2 hours from a small scheduled workflow or Axe chop, and trigger
`full.yml` on `push: branches: [ci-full]` with `cancel-in-progress: false`. It carries
`build-core`, `test (3.12/3.13/3.14)`, `visual-test`, `coverage-contexts`, `perf-floors`,
`ace-page-group-isolation`. Twelve runs/day, ~9% of budget, ≤2-hour blast radius, and
`actstat` never sees it.

**Move the existing `'17 6 * * *'` cron to `ci-full` in the same change.** It is a
deliberate flake reproducer whose failures currently land on the release gate's tip.

Accept deliberately: `ci_watch` reports incidents from default-branch sweeps only, so
heavy-lane failures will not page through the existing chop. Cover with GitHub's native
workflow-failure notifications, and file a bead to extend `ci_watch` with a watched-branch
list.

### R3 — Fix the `--squash` / `allow_squash_merge` mismatch *(one setting, do it now)*

`ci_watch.merge()` hard-codes `--squash` with `--match-head-commit`. The repository has
`allow_squash_merge: false`, `allow_rebase_merge: false`, `allow_merge_commit: true`.
The first time gates 1–8 ever pass, `gh pr merge --squash` fails. Either re-enable squash
merges (if linear history is the policy — release-please supports both) or change the
chop to match the repository. **Keep `--match-head-commit`; it is the race protection.**
This is cheap, independent of everything else, and otherwise guarantees the first
successful gate still produces no release.

### R4 — Fix `visual-test` first, then the rest

`visual-test` fails in 8/8 recent completed runs and is the last cluster standing (§5).
Work it to green on a pinned `sase-core` SHA, verified with a local `just check-full`
under `/sase_monitor`.

Land **R1 before R4**, deliberately: the fast gate gives the repair work per-commit
signal instead of the 1-in-8 signal that let the red accumulate. R1 is additive — it
removes no coverage until R2 lands.

### R5 — Throttle release-please to a schedule

Change `publish.yml`'s release-please step from `on: push` to `on: schedule` (every 2–4 h)
plus `workflow_dispatch`. The release branch head then moves 6–12×/day instead of ~76×,
which eliminates the `release_pr_empty_rollup` window (condition 6) and collapses
`release_generator_busy` (condition 8) from ~35–45% of ticks to a few percent. Keep the
*publish* half on push — or fire `workflow_dispatch` right after `ci_watch` merges — so a
merged release PR still tags and ships promptly.

### R6 — Pin `sase-core` in CI

Record a `sase-core` SHA in-repo; have `build-core` check out that SHA rather than HEAD,
with a separate ratchet job proposing bumps. This makes `sase` master CI reproducible and
stops `sase-core` pushes from silently reddening `sase`. (Overlaps the existing
`core_dependency_window_ratchet` research — coordinate rather than duplicate.)

### R7 — Attack `test (3.13)` and `coverage-contexts`

Even in the heavy lane these are 118–137 of the 234 job-minutes. `test (3.13)` runs
`just test-cost` at 72–91 min against `test (3.14)`'s 23–27 min for the same suite — a 3×
gap that is cost-attribution overhead, not coverage. Move cost attribution to a
nightly-only leg or find the overhead; same question for `test-contexts` at 44–46 min.

### Suggested order

**R3 → R1 → R4 → R5 → R2 → R6 → R7.**

R3 first because it is a single setting and it is otherwise a guaranteed failure at the
finish line. R1 next so the repair work gets per-commit signal. R2 is what reclaims the
budget, so it can follow the first green release.

### Expected end state

| Metric | Today | After R1–R2 |
| --- | ---: | ---: |
| Master gate wall time | ~107 min | ~6–8 min |
| Commits with an attributable completed run | ~13% | ~58% |
| Tip settled (% wall-clock) | 13.7% | ~68% |
| Master runs cancelled | 166 / 2.3 days | ~0 |
| Regression detection latency | 1–3 h, ~7 commits | ~8 min, 1 commit |
| Budget consumed by master CI | 9% (of a ~62% need) | ~12% (of a ~12% need) |
| Release merges possible per day | 0 | many windows/day |

## 9. Options rejected, with reasons

| Option | Verdict |
| --- | --- |
| **`queue: max`** on the master group | Eliminates cancellations, does not open the gate — converts cancellation into a growing backlog at a 10× arrival/service ratio. Revisit *after* `L` drops. |
| **Per-SHA concurrency on full `ci.yml`** | Fails twice: ~62% of budget on top of PR CI's ~59%, *and* at `L`=107 min the tip still settles ~14% of the time. |
| **Delete the master `concurrency:` block** | Same as above; reproduces the exact starvation the block was added to prevent. |
| **`cancel-in-progress: true` on master** | Already tried, recorded in `ci.yml`'s comment: no master run ever reaches a terminal conclusion. Strictly worse than today. |
| **GitHub merge queue** | Requires PR-ifying ~76 direct-push commits/day (§7), and its throughput ceiling is governed by the same ratio. Right long-term shape *only* if SASE moves to PR-based landing. |
| **Bigger plan / larger / self-hosted runners** | Buys capacity, not latency. The gate asks about the instantaneous tip. |
| **Verify every Nth commit** | `L` unchanged; attribution still spans N commits. Treats the symptom. |
| **Wait for a quiet period** | This *is* the current behavior, not a control mechanism — it makes release latency a function of developer activity. |
| **Slow the agents down** | The velocity is the point of the project. Design the verification system for the observed arrival rate. |
| **Drop the default-branch guard entirely** | Restores liveness but has no safety argument while master is unprotected and direct-pushable. Make master green by construction first. |

**Deferred — worth revisiting:** a **last-known-good release train**, changing `ci_watch`
to cut from the newest green commit rather than the tip. It removes the tip requirement
permanently and survives another doubling of velocity. At ~76 commits/day R1–R2 suffices;
at 160/day it probably does not.

## 10. Risks and safeguards

| Risk | Safeguard |
| --- | --- |
| Fast gate misses a regression the heavy lane would catch | Heavy lane still runs every 2 h; `just check-full` still gates epic landings; `just selection-health` already tracks whether scoped selection has ever been wrong — watch it. |
| Per-SHA gate concurrency reintroduces contention | Gate is ~12 job-min; a 10-commit burst is 120 job-min against 1,200/hour. Monitor PR CI queue wait (§1.4) as the canary — it should stay under 1 min. |
| `ci-full` drifts or the fast-forward job wedges | Fast-forward workflow fails loudly and alerts; the branch is disposable and re-derivable from master. |
| Heavy-lane failures unnoticed once off the default branch | Enable native workflow-failure notifications immediately; bead to extend `ci_watch` with a watched-branch list. |
| Throttled release-please delays a release up to 4 h | Acceptable against a 19-day stall; `workflow_dispatch` for manual cuts. |
| Green gate + red heavy lane ⇒ release ships a real regression | Add the most recent heavy-lane conclusion as an advisory condition in `ci_watch` before re-enabling unattended merges, or keep `merge_enabled` behind manual confirmation until the heavy lane has been green for a full day. |

## 11. Acceptance criteria

1. `gh run list --workflow=master-gate.yml --branch=master --limit 50` shows **zero**
   `cancelled` conclusions.
2. Median master gate wall time ≤ 8 minutes over 50 consecutive runs.
3. ≥ 90% of master commits in a 24-hour window have a completed gate run.
4. `actstat -f jsonl | jq -r 'select(.repo=="sase-org/sase") | .conclusion'` reports
   `success` for a majority of samples taken 10 minutes apart over an hour.
5. `ci_watch` reports `eligible` (or any reason other than `default_branch_not_green`)
   at least once per day.
6. A dry-run `gh pr merge` against the repository's *allowed* strategy succeeds (R3).
7. PR CI queue wait stays ≤ 1 minute median after R1 ships.
8. `v0.17.0` is tagged and published.

## 12. Open decisions for the owner

1. **Squash or merge commits?** R3 forces the choice. Squash keeps linear history and
   matches the chop as written; merge commits are what the repo currently allows.
2. **Which tests belong in the gate?** `just test-scoped` is the natural answer given the
   existing selector, but the gate runs on a *pushed* commit rather than a working tree —
   confirm `tools/select_tests` resolves a sensible baseline for `master~1..master`.
3. **`ci-full` branch versus a `gating_workflows` allowlist in `ci_watch`.** The branch
   needs no chop change; the allowlist is more principled ("the gate should name what it
   gates on") and would let the heavy lane stay on master. Branch is the faster path;
   allowlist is the better long-term shape.
4. **Is the last-known-good release train worth building now?** It permanently decouples
   release cadence from CI latency.

## Appendix: reproductions

```bash
# §1.2 — master CI outcome distribution
gh run list --repo sase-org/sase --workflow=ci.yml --branch=master --limit 200 \
  --json status,conclusion | jq -r '.[] | (.conclusion // .status)' | sort | uniq -c

# §1.3 — inter-push gap distribution
git log --format=%ct -400 | tac | awk 'NR>1{print ($1-p)/60} {p=$1}' | sort -n

# §1.4 — PR CI queue wait (runner slots, not group pending)
gh run list --repo sase-org/sase --workflow=ci.yml --event=pull_request --limit 12 \
  --json databaseId -q '.[].databaseId' | while read -r id; do
    gh run view "$id" --repo sase-org/sase --json createdAt,jobs \
      | jq -r '([.jobs[]|select(.startedAt)|.startedAt]|min) as $s
               | (($s|fromdate) - (.createdAt|fromdate))/60'
  done

# §4 — the daily cron competing for the master lane
gh run list --repo sase-org/sase --workflow=ci.yml --event=schedule --limit 5 \
  --json conclusion,createdAt,updatedAt,headSha

# §5 — failing jobs across recent completed failures
gh run list --repo sase-org/sase --workflow=ci.yml --branch=master --status=failure \
  --limit 8 --json databaseId -q '.[].databaseId' | while read -r id; do
    gh run view "$id" --repo sase-org/sase \
      --json jobs -q '[.jobs[]|select(.conclusion=="failure")|.name]|join(", ")'
  done

# §7 — direct-push landing model
git log --format='%H %P' -400 | awk '{print NF-1}' | sort | uniq -c   # -> 400x "1"
gh api repos/sase-org/sase --jq \
  '{allow_squash_merge,allow_merge_commit,allow_rebase_merge,allow_auto_merge}'
gh api repos/sase-org/sase/rulesets --jq 'length'                     # -> 0
```

## Sources

- [Control the concurrency of workflows and jobs — GitHub Docs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
- [GitHub Actions concurrency groups now allow larger queues — GitHub Changelog, May 2026](https://github.blog/changelog/2026-05-07-github-actions-concurrency-groups-now-allow-larger-queues/)
- [GitHub Actions limits — GitHub Docs](https://docs.github.com/en/actions/reference/limits)
- [Managing a merge queue — GitHub Docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)
- [`merge_group` event — GitHub Docs](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#merge_group)
- [`EnqueuePullRequestInput` — GitHub GraphQL](https://docs.github.com/en/graphql/reference/pulls#enqueuepullrequestinput)
- [`gh pr merge` manual](https://cli.github.com/manual/gh_pr_merge)
- [release-please — googleapis/release-please](https://github.com/googleapis/release-please)
- [GitHub Merge Queue Was Step One. Real CI Orchestration Comes Next. — Mergify](https://mergify.com/blog/github-merge-queue-was-step-one-real-ci-orchestration-comes-next)
- [The Merge Queue Is the New Bottleneck — TianPan.co](https://tianpan.co/blog/2026-07-02-the-merge-queue-is-the-new-bottleneck)
- [Merge Queues for Large Monorepos — Aviator](https://www.aviator.co/blog/merge-queues-for-large-monorepos/)
- Local sources: `sase-org/sase` `.github/workflows/{ci,publish}.yml`;
  `bbugyi200/bugyi-chops` `src/bugyi_chops/ci_watch.py`; `bbugyi200/actstat`
  `src/github.rs`.
