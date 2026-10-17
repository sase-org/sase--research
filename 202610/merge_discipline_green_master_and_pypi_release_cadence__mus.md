# Merge discipline for SASE: keeping `master` green so PyPI releases can resume

> **Research query.** After reading `gastown_vs_sase_lessons_to_borrow.md`, SASE seems to need
> better merge discipline. The goal is a way to keep `master` green so SASE can publish to
> PyPI more often. Is a PR-only (protected `master`) workflow needed or even recommended, or
> is there another way? Critique the plan, adjust the requirements where justified (and call
> the adjustments out), and end with a recommended solution.

Researcher: **mus** · Date: 2026-10-17 · SASE `master` at `3e950ebdbd`

## Bottom line

1. **The intent is right and the framing is too narrow.** "Keep `master` green" is the wrong
   target for the PyPI goal. A release needs *one SHA that is proven releasable*, not a tip
   that is always green. Today the wheel is not even built from a proven SHA (see
   [finding 2](#2-the-published-artifact-is-not-the-sha-that-was-verified)).
2. **Master Gate green is necessary but nowhere near sufficient.** The release watcher also
   needs a recent green **Full CI**, and Full CI has passed **once in its last 271 runs**
   (last green 2026-08-29, the day 0.17.1 shipped). No landing discipline touches that.
3. **PR-only with branch protection is the wrong first move.** Required checks on a PR test
   the PR head against a stale base, which is the merge-skew class `sase-1cb` describes.
   Requiring "up to date" at 40–60 landings a day causes rebase and retest livelock. SASE's
   `ci.yml` also runs the whole 3-Python matrix on PRs (about 100+ minutes). What protects
   `master` is a **merge queue** (test the merged result, then land it). PR-only is merely
   the lock that makes a queue non-bypassable.
4. **A merge queue is the right end-state, but not the next step.** The data show two
   different red-makers, and a queue cures only one of them:
   - Short red blips (about 7% of red minutes) look like flakes.
   - A few long real breaks (about 93% of red minutes) have no owner and no deadline.
5. **Recommended.** Do four things first, in this order:
   1. Release from a **proven SHA** (a "last known good" ref).
   2. Make red **trustworthy** (quarantine recurring flakes, rerun failed shards once, fix
      Full CI).
   3. Stop the pile-on with a **red-HEAD freeze**, plus a cheap **combined-tree guard**
      after rebase.
   4. Add **fix-or-revert** within 60 minutes.

   Then decide on a **merge queue (PR + GitHub merge queue + ruleset)** from measured
   triggers, not from principle. [Details](#recommended-solution).

## Requirement adjustments (called out)

| #   | Original requirement                  | Adjusted requirement                                                                                                                           | Why                                                                                                                                                                           |
| --- | ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A1  | `master` stays green                  | **A releasable SHA less than 24 h old always exists** (release goal), plus **red minutes per day stay under a budget with bounded repair time** (tip goal) | PyPI needs a verified SHA, not a perpetually green tip. The two goals have different cures and costs                                                                          |
| A2  | "Green" is one thing                  | Two tiers: **gate-green** (Master Gate, per landing) and **release-green** (Master Gate + Full CI + core-floor smoke on the *same SHA*)         | Release already requires both signals (`decisions:ci-two-speed-split`), but nothing makes them agree on one SHA                                                               |
| A3  | PR-only / protected `master`          | Drop it as a requirement. Replace with **no unverified landing can reach `master`**, enforced server-side *if and when* a queue is adopted     | PR-only without a queue does not test the merged result and costs more than it buys here                                                                                       |
| A4  | (implicit)                            | **Add: publish the verified SHA, not whatever the tip is when Publish runs**                                                                    | `publish.yml`'s `build` job checks out the default branch with no `ref:`, so the wheel is the tip at publish time                                                             |
| A5  | (implicit)                            | **Add: a flake budget** (red onsets per day caused by flaky tests)                                                                              | A gate on a flaky suite is a random-rejection engine. About 12 of 15 recent red onsets were flake-shaped                                                                      |
| A6  | (implicit)                            | **Add: refusals are deferrals, not waits**                                                                                                      | `decisions:single-turn-agents` and `gates-never-block`: a landing refused during a freeze must park and drain mechanically, not block an agent                                |
| A7  | (implicit)                            | **Add: a release cadence policy** (scheduled release train)                                                                                    | A green `master` does not publish anything. Today release is an agent-driven epic (`sase-1lh`), not a boring scheduled job                                                    |

## What the evidence says

Tags: **[measured]** I ran the query today; **[code]** read in this checkout; **[external]**
vendor docs or papers; **[inferred]** my reasoning.

### 1. Release has stalled, and it was not always like this

- **[measured]** PyPI `sase`: 28 releases from 2026-06-11 to 2026-08-29 (about one per 2.8
  days). The last was **0.17.1 on 2026-08-29**. That is **49 days** with no release.
- **[measured]** Release PR #299 (0.18.0) has been open since 2026-08-30 and is `MERGEABLE`.
- **[measured]** Epic `sase-1lh` ("Green Master Gate and Full CI, then ship sase v0.18.0
  through ci_watch") is still in progress, with a child epic `sase-1lh.7` repairing the
  release watcher itself. Its notes record a misdiagnosed `CORE_FLOOR_BLOCKED` (a stale PR
  head, not a floor block) and "no Full CI run yet contains every fix".

### 2. The published artifact is not the SHA that was verified

- **[code]** `publish.yml` runs on a 3-hourly `schedule`. `build` does `actions/checkout@v4`
  with no `ref:`, then `uv build`. `publish` uses trusted publishing (`environment: pypi`).
- **[inferred]** The wheel is `master` at the moment Publish runs, plus whatever landed since
  the release PR was verified. With about 43 pushes a day, the tip moves every 30 minutes.
- **[code]** The watcher mitigates part of this. `evaluate()` requires the Master Gate at
  HEAD to be green (`_check_master_gate`), and `_is_stale_head` reasons about the PR's merge
  base. But the invariant it needs is "the artifact SHA was verified". Tip-green is a proxy
  for that.

### 3. Master Gate: red about half the time, but red *time* is concentrated

Window: 145 completed Master Gate runs from 2026-10-13 11:00Z to 2026-10-17 02:20Z
(87 hours). **[measured]**

| Metric                                                   | Value                                                |
| -------------------------------------------------------- | ---------------------------------------------------- |
| Time-weighted green fraction                             | **50%**                                              |
| Green→red onsets                                         | **15** of 145 runs (10.3%)                           |
| Red episodes                                             | 16                                                   |
| Episodes shorter than 60 min                             | 11, holding **7%** of red minutes                    |
| Episodes of 60 min or longer                             | 5 (189, 98, 605, 1135, 387 min), holding **93%** of red minutes |
| Gate wall time                                           | p50 12.6 min, p90 24.9 min (300 runs)                |
| Pushes per day (Oct 10–16)                               | 52, 37, 62, 44, 33, 13, 62 (about 43/day)            |
| Next push lands before the previous gate finishes        | **40%** (119 of 299), unchanged from the Oct 1 report's 42% |
| Current state                                            | Red from 2026-10-16 19:59Z; **green again at `08d9b66154` / `3e950ebdbd` at 02:26–02:29Z** (6.5 h red) |

**What the 15 onsets were.** I extracted the failing tests for each onset run
(`gh run view --log-failed`). **[measured]**, with the classification below **[inferred]**:

- About **12 of 15** failed only on timing-style TUI tests that recur across unrelated SHAs
  and have filed flake beads. Examples: `test_mounted_arrival_then_clear_name_keeps_selection`
  (5 onsets), `test_filter_and_enter_advance_the_modal_without_an_entry_point` (3),
  `test_next_word_peek` and the mid-word tests (2), `test_link_follow_seam` (2), plus
  `test_provider_drain_e2e` and a `30.87 < 5.0` bounded-drain timing assert.
- About **3 of 15** look like real regressions:
  - symvision lint (`73a61e6944`);
  - an `AttributeError` for a renamed `_instruction_boundary.notify_instruction_fallback`
    (`d69cd499dd`), which is classic merge skew;
  - `test_project_labels_never_derive_from_paths` (`a9701c36e6`).
- The classification is by signature and recurrence, **not by rerunning**. Treat the 12/3
  split as medium confidence.

**The two failure modes need different cures.**

- *Flake blips* are short and harmless to the tip, but poison any gate and any "release only
  when green" rule. Cure: statistical hygiene (quarantine, shard rerun, fixes).
- *Real breaks* are rare (about 2% of landings here, roughly 0.8 a day), but they last hours
  because nobody owns them and later landings pile on. Cure: freeze, fix-or-revert, and
  (optionally) a queue.

### 4. Full CI is the real release blocker

- **[measured]** `Full CI` (scheduled every 2 h, plus manual dispatches): **271 runs, 1
  success**, on 2026-08-29. It runs about 101 min p50 (114 min p90).
- **[measured]** On 2026-10-16 it ran 13 times and failed every time. The failing jobs were
  `test (3.12)`, `test (3.13)`, `test (3.14)`, `visual-test`, `lint` and `perf-floors`.
- **[measured]** The last two runs I inspected share a persistent real failure
  (`test_project_labels_never_derive_from_paths`) and add real regressions
  (`test_launch_approval*`, `test_root_help_renders_compact_help`,
  `tests/completion/test_snapshot.py` drift).
- **[inferred]** Master Gate (Python 3.12 only, non-visual) cannot see the 3.13/3.14, visual
  and perf lanes. A merge queue that runs the Master Gate would therefore **not** have made
  the 0.18.0 release possible. The release gate (`ci-two-speed-split`: fast gate plus a
  recent green Full CI) is stricter than anything a landing queue would enforce.

### 5. The landing path has no refusal point (confirmed, still true)

- **[code]** `vcs_create_commit` does `git commit` → `_sync_with_origin_after_commit`
  (`git rebase --autostash origin/<default>` plus automatic semantic-conflict resolution) →
  `_push_current_branch_with_rebase_retry`. No check runs on the combined tree that is
  pushed. This is the exact gap `sase-1cb` ("pushes auto-rebased commits without checking
  the combined tree") has tracked since 2026-09-28, with four prior instances (`sase-lg`,
  `sase-183`, `sase-1b7`, `9f67a91bce`) that were all ImportError or mypy-class breaks.
- **[measured]** Branch protection: `GET /branches/master/protection` returns 404 and
  `/rulesets` returns `[]`. Nothing server-side stops a direct push.
- **[measured]** Repo merge settings allow **only merge commits** (`allow_squash_merge` and
  `allow_rebase_merge` are false), so a queue needs a deliberate merge-method choice.
- **[code]** A PR landing path already exists (`#pr` commit method, `vcs_create_pull_request`
  in `_git_commit_dispatch.py`, the `PR Title` workflow, release-please reading conventional
  titles). Agents just do not use it for ordinary landings.

### 6. The local signal is weak, and slow

- **[measured]** `sase tool stats -t check -d 7` on this machine: 57 runs, **4 OK (7%)**, 48
  failed. p50 is **21m52s** and p90 **79m54s**; the scoped `test` stage is 46m p50. Master
  Gate is 12.6 min. So a local pre-push `check` is slower than the CI gate it is meant to
  predict, it runs on a contended host, and it has Python and Rust-core skew from CI.
- **[measured]** Debt: **145 open flake beads** and **88 `ci` beads** in `ready`.

### 7. Capacity

- **[measured]** `sase-org` is a **Free-plan organization** (`gh api orgs/sase-org`). The
  repo is public.
- **[external]** GitHub Free allows 20 concurrent jobs on standard hosted runners (Pro 40,
  Team 60, Enterprise 500), per GitHub's Actions limits docs.
- **[code]** Master Gate is 11 jobs (docs, core-wheel, lint, 8 test shards). Full CI is
  about 10 jobs for about 100 min and is scheduled every 2 h.
- **[inferred]** Full CI occupies half the slots nearly continuously, so the account
  realistically runs **one Master Gate at a time**. This is the likely root of
  `ci-two-speed-split` rejecting a merge queue. I did not measure job queue waits, so
  treat it as a hypothesis to test first.

## Critique of the plan

**What is good**

- It targets the right gap. The Gas Town report's central finding holds: "nothing on the
  landing path refuses a red change", and the Master Gate is post-land telemetry.
- It correctly separates *mechanical* enforcement from etiquette. Previous green-master
  repair epics (`sase-1lh`, `-1kx`, `-1kl`) keep working and then regressing, because
  nothing keeps them fixed.

**What I would change**

1. **Green-tip is a means, not the end.** The end is cheap, frequent, trustworthy releases.
   Two of the three things standing between SASE and a release are not about the tip:
   Full CI health, and building the wheel from the verified SHA. Optimizing the tip first
   spends the budget on the least binding constraint.
2. **PR-only is a mechanism, not a strategy.** Without a queue it moves the same post-push
   check to the PR head. It buys server-side enforcement and review UI, which a solo
   maintainer with agent committers mostly does not need yet.
3. **A queue on an untrusted signal makes things worse.** About 80% of recent red onsets
   look flake-shaped. A gate that rejects about 8–10% of candidates at random would burn a
   12-minute gate run for each false rejection, on a single effective runner slot.
4. **The cost side is under-counted.** A queue or any pre-land gate turns landing from a
   synchronous push into an asynchronous event. Epic phases chained on `%w(bead=…)` waiters
   gain 15–40 minutes per phase, and a rejected landing needs a repair agent. That is the
   "prove the push, then close beads" machinery (Gas Town R1 item 3), and it is the real
   engineering cost, not the GitHub setting.
5. **Gas Town's own evidence argues for caution.** Its Refinery's batch-then-bisect was
   unwired, its merge verdict was an LLM judgment that could merge red, and the project
   itself landed PRs through GitHub, not its Refinery. Rust's Homu was described as "quite
   buggy" and "hard to maintain" and is being rewritten. Home-grown queues are expensive to
   own.
6. **No success metric.** "Master stays green" has no number. I propose
   [these](#metrics-and-targets).

**Verdict.** Good instinct, wrong ordering. Fix the signal, decouple the release, bound the
red time, *then* buy the guarantee with a queue if the numbers say it is still worth it.

## Options considered

| Option                                                     | Prevents tip red?                         | Fixes PyPI cadence?                   | Cost / risk                                                                                                                                 | Verdict                      |
| ---------------------------------------------------------- | ----------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| **O1 Status quo + repair epics**                           | No                                        | No                                    | Has failed twice (Sept 18 → Oct 1, again Oct 16)                                                                                            | Reject                       |
| **O2 Branch protection only** (required checks, PR-only)   | Partly: tests the PR head, not the merge  | No                                    | `ci.yml` PR runs 100+ min; "up to date" livelocks at 40–60/day; agents must open PRs                                                         | Reject as a standalone step  |
| **O3 GitHub PR + merge queue + ruleset**                   | **Yes** (tests the merged result)         | Indirectly                            | Async landing; PR plumbing in the finalizer; 20-job Free cap; flaky gate rejects good PRs; merge-method choice; new decision record          | **End-state, gated** (see below) |
| **O4 Host-owned landing lane** (Gas Town R1: rebase → verify → push → prove) | Yes, if verification is trustworthy | Indirectly                            | Rebuilds a queue (locking, partial failure); local `check` is 22 min p50 with 3.12/3.14 skew; no server-side enforcement without a ruleset   | Fallback if O3 capacity fails |
| **O5 Green-or-revert** (freeze + fix-or-revert)            | Bounds it (modeled: about 11% red, from 50%) | Indirectly                         | Cheap; no async landing; reverts can conflict; must not revert on flakes (rerun-confirm first)                                              | **Do now**                   |
| **O6 Release from a proven SHA** (LKG ref, Full CI on candidates) | No (does not need to)              | **Yes, directly**                     | Needs a release-branch design spike; Full CI must become green at all                                                                       | **Do now, first**            |
| **O7 Flake control** (quarantine with expiry, shard rerun once) | Removes about 80% of onsets          | Yes (unblocks both gates)             | Needs an owner; quarantine must not become a graveyard                                                                                      | **Do now**                   |
| **O8 Fewer, bigger landings** (epic integration branches)  | Reduces landings from about 43/day to about 10/day | Indirectly                    | Long-lived branches; invasive to epic flow                                                                                                  | Later, if queue load demands |
| **O9 Buy capacity** (GitHub Team plan, 60 concurrent jobs) | No                                        | Indirectly (unblocks O3, faster Full CI) | Recurring cost, which I did not verify; at one maintainer it is likely small                                                              | Option, after measuring queue waits |

### How other systems solve it (for calibration)

- **Rust bors/Homu ("not rocket science rule")** **[external]**. Merge each approved change
  into a temp branch, run the full suite, and move `master` only on green. The goal was to
  stop merge skew, where two changes each pass alone but break together. Homu proved costly
  to maintain, and Rust moved to GitHub-native tooling.
- **Uber SubmitQueue** **[external]**. A speculation graph with a probabilistic model plus a
  conflict analyzer. It guarantees a green `master` at scale, but a 2025 follow-up reports
  premature build aborts and cut CI resource use by 53%. This is the scale-out answer and is
  overkill at 43 commits a day.
- **GitLab merge trains** **[external]**. Stacked merged-result pipelines. GitLab's docs warn
  that merged-results pipelines alone do not account for other merge requests that merge at
  the same time.
- **GitHub merge queue** **[external]**. A `merge_group` event runs required checks on a
  temporary branch. Settings: merge method, build concurrency (1–100), min/max group size,
  wait time, status-check timeout, and "only merge non-failing pull requests". Actions
  workflows **must** list `merge_group` or the required check never reports and the merge
  fails. Available to public repos owned by an organization (2023 changelog), so
  `sase-org/sase` qualifies. I did not enable it to confirm.
- **Chromium LKGR / Dart `lkgr` roller** **[external]**. A "last known good revision" is
  advanced only when a defined set of builders is green. This is the pattern behind O6.
- **Trunk-based release practice** **[external]**. High-cadence teams release straight from
  trunk, and others cut a release branch retroactively from an earlier known-good revision.

## The PR-only question, answered directly

- **Is a protected `master` required?** No. Protection is only the *lock*. The *rule* is
  "the merged result was tested". Without a queue or an equivalent tested-merge step,
  protection enforces only that someone opened a PR.
- **Is it recommended anyway?** Not as the next step. It is recommended as the final step of
  an adoption that includes a merge queue and a trustworthy gate. If adopted:
  - PR + **merge queue** + ruleset "require merge queue".
  - The bypass list holds only a break-glass admin, and the release bot (or the release PR
    goes through the queue too).
  - Merge-method decision: **squash**, so one conventional PR title becomes one release-please
    commit.
- **Do not use "require branches to be up to date" at this cadence.** Every landing
  invalidates every open PR, so agents would rebase and retest forever. A queue exists to
  remove exactly that.

## Recommended solution

The sequence is ordered by leverage on the PyPI goal, then by cost. Each step has an exit
criterion.

### Step 1. Release from a proven SHA (S–M, days)

*Targets A1, A2, A4.*

1. Define **release-green** = Master Gate green **and** Full CI green **and** core-floor
   smoke, all on the **same SHA**.
2. Change `full.yml` to test the **newest Master-Gate-green SHA** that has no Full CI result
   yet, instead of whatever tip is current at the cron tick. A tip that is Master-Gate-red
   cannot become release-green, so Full CI minutes spent on it are wasted. The 2-hour
   cadence stays.
3. Maintain a bot-owned `lkg` ref: the newest SHA with release-green. Resolution logic
   (which SHA is the newest green one) is shared backend behavior (ACE, CLI and `ci_watch`
   all need it), so per `rust_core_backend_boundary` it belongs in `sase_core`; the GitHub
   Actions glue stays in `tools/`.
4. Make Publish build **that** SHA. Two variants, both needing a short spike:
   - **Preferred.** Point release-please at a `release` branch fast-forwarded to `lkg`
     (`target-branch`), publish from that branch, and back-merge the version and changelog
     commit to `master`. I could not confirm release-please's non-default-branch behavior
     with the manifest config from official docs, so this needs a one-day spike.
   - **Fallback.** Keep release-please on `master`, but have `build` check out the release
     PR's verified SHA. This is smaller but loses the clean "tag equals verified SHA"
     property.

*Exit criterion:* a release can be cut while the tip is red, and the artifact SHA equals a
release-green SHA. *This is the step that directly unblocks 0.18.0 and every release after
it.*

### Step 2. Make red trustworthy (M, 1–2 weeks)

*Targets A5.*

1. **Quarantine** the recurring flake set with `xfail(strict=False, reason="sase-…")` on a
   reviewed list with an expiry. Start with the five tests that account for most onsets in
   the data above. These tests already have filed flake beads (`sase-1ls`, `sase-1l7`,
   `sase-1lr`, `sase-1k2`, …).
2. **Rerun failed test shards once** in Master Gate, using the same policy `release_watch`
   already applies (`_gate_test_shards_only` earns one blind rerun; lint and docs reds
   never do). This policy is unrelated to local-triage exit codes, so
   `triage-annotates-does-not-change-exit-codes` is not touched.
3. **Fix Full CI's persistent real failures**: the audit, completion-snapshot and
   launch-approval tests; visual-capture instability (`sase-1lh.7`); the 3.13/3.14 legs.
   Pin local Python to 3.12 (`.python-version`) to remove the skew the Oct 1 report found.
4. Triage the 145 flake and 88 `ci` beads against the same list. Anything unfixable gets a
   quarantine entry with an owner.

*Exit criterion:* flake-shaped red onsets under one per day, and at least one green Full CI
per day, held for 7 days.

### Step 3. Stop the pile-on (M, 1–2 weeks)

*Targets A1 (tip goal), A6. This is the "merge discipline" the user asked about, in its
cheapest effective form.*

1. **Red-HEAD freeze.** If the newest *completed* Master Gate on `origin/master` is red and
   survived the shard rerun, the commit finalizer **defers** every landing that is not a CI
   repair instead of pushing. A deferred landing stays committed in its workspace and a
   scheduler job drains it when HEAD is green. It does not block an agent and it does not
   fail the turn (`gates-never-block`, `single-turn-agents`).
   - Repair exemption: the assigned bead has `task_type` `ci` or `flake`, which is set at
     launch by the host and cannot be self-assigned mid-turn.
   - Evidence: 93% of red minutes sat in five long episodes where further landings piled on.
2. **Combined-tree guard** (`sase-1cb`, scoped small). After the final rebase, if the base
   moved, run the cheap checks that catch the import/type class (mypy about 1m48s, symvision
   about 1m46s, ruff, `pytest --collect-only`) before the push. This is a new bounded
   verification, **not** a receipt-based skip, so `receipts-prove-before-they-skip` is
   respected. It would have caught `sase-lg`, `sase-183`, `sase-1b7` and `9f67a91bce`. It
   would not catch every monkeypatch-string rename, which `d69cd499dd` appears to be.

*Exit criterion:* "commits ahead of last green" stays at 1 or lower at p90, and no episode
runs past 60 minutes without a freeze.

### Step 4. Fix-or-revert (M, 2–4 weeks)

*Targets A1 (tip goal).*

When a SHA is red, was green at its parent, and survived the shard rerun, `ci_watch` arms
the freeze and launches one fix agent with the SHA's diff and failing jobs. If HEAD is still
red after 60 minutes, it reverts the SHA. Modeled on this window (assuming reverts apply
cleanly): the five long episodes (2,414 red minutes) would be capped at about 75 minutes
each, so red time falls from about 50% to **about 11%** of the window, and to roughly
**7%** if Step 2 also removes the blips. That is enough for daily releases from `lkg`, but
it is not "never red".

*Exit criterion:* median time-to-green after a real break under 60 minutes, red minutes per
day under a stated budget (I suggest 10%).

### Step 5. Decision gate: PR + merge queue (L, only if triggered)

Adopt O3 **only if** after Steps 1–4 have run for about four weeks at least one of these
holds:

- Real-break onsets exceed about 1 per day (the freeze and revert are churning).
- Red minutes per day stay above budget even with the freeze and revert.
- The semantic-skew class (`sase-1cb`) recurs twice or more a month despite the combined-tree
  guard.
- Revert conflicts exceed about a third of reverts.
- Outside contributors start sending PRs (a PR flow becomes necessary anyway).

If triggered:

1. **Capacity first.** Measure job queue wait p90 with a Full CI run in flight. If it exceeds
   about 3 minutes, either upgrade the org plan (O9) or fall back to O4.
2. **Pilot as an opt-in lane**: epic-lander agents and the release bot land via PR → queue;
   everything else keeps pushing. The finalizer records "landing pending" and closes the bead
   and resolves `%w(bead=…)` waiters only after the SHA is proven on `master`. A rejected
   queue entry spawns one repair turn on the branch.
3. **Flip the ruleset** (require merge queue, no bypass except break-glass) once pilot
   metrics hold for a week.
4. **Queue settings (starting point):** squash; max group size 5, min 1; build concurrency 1;
   status-check timeout about 30 min; "only merge non-failing pull requests" on. One stable
   aggregate required check (a `gate` job) triggered on `merge_group`.
5. **Drop the push-triggered Master Gate** for queue-landed SHAs (or demote it), otherwise
   every landing is verified twice on a capacity-starved account. This also means the
   `lkg` logic must read `merge_group` results.
6. **Write the decision record**: it reopens `ci-two-speed-split` (its trigger, "the fast
   gate's p50 wall time stops fitting the commit cadence", is arguably already met: 40% of
   pushes outrun the previous gate). Land the lane behind a feature flag per `sase_flags.md`
   with the direct-push branch reachable.

I did not verify two behaviors and would test them in the pilot: that the SHA the queue
tests is the SHA that lands (it should be, for a fast-forwarded merge group), and how squash
interacts with release-please's expectation of one conventional commit per change.

## Metrics and targets

| Metric                                                          | Today (measured)             | Target after Steps 1–4                       |
| --------------------------------------------------------------- | ---------------------------- | -------------------------------------------- |
| Days since last PyPI release                                    | 49                           | ≤ 7 (release train)                          |
| Age of newest release-green SHA                                 | undefined; Full CI 1/271     | < 24 h                                       |
| Full CI green runs per day                                      | 0                            | ≥ 1                                          |
| Master Gate green fraction (time-weighted)                      | 50%                          | ≥ 90%                                        |
| Red episodes ≥ 60 min per week                                  | about 10 (5 in 3.6 days)     | ≤ 1                                          |
| Flake-shaped red onsets per day                                 | about 3                      | < 1                                          |
| Commits ahead of last green (p90)                               | dozens in a long episode     | ≤ 1                                          |
| Landings refused or deferred during a freeze                    | n/a                          | tracked; every one drains within one gate    |

## Risks and what would change my mind

- **Capacity may be fine.** If job queue waits are low even with Full CI running, the
  `ci-two-speed-split` capacity objection weakens and the queue (Step 5) moves earlier.
- **The flake share may be lower than 80%.** I classified by signature, not by rerun. If a
  rerun study shows most onsets are real, the case for a gate at landing strengthens and
  Step 3's combined-tree guard should grow into a fuller pre-push check.
- **Freeze deferral could create rebase pile-ups** in parked workspaces. If drain-time
  conflicts exceed a few percent, prefer refuse-and-relaunch for those landings.
- **The release-branch spike could fail.** If release-please cannot target `release` cleanly
  with the current manifest and `sync-release-metadata` job, take the fallback variant and
  accept looser artifact-SHA guarantees until Step 5.
- **Revert policy has a trust cost.** Auto-reverting an agent's work, especially an epic
  phase, can strand dependents. Restrict auto-revert to non-epic landings at first and
  escalate epic breaks through a gate.

## Method, confidence, and what I did not do

- **Read:** `gastown_vs_sase_lessons_to_borrow.md` (landing sections, R1, sequencing) and the
  prior `master_ci_red_why_and_how_to_stay_green.md` consolidated report, both through
  `sase artifact read`; decision records `ci-two-speed-split`, `host-owned-completion`,
  `receipts-prove-before-they-skip`, `check-full-is-explicit`; `publish.yml`, `ci.yml`,
  `master-gate.yml`, `full.yml`; `tools/_release_watch_engine.py` (`evaluate`,
  `_check_master_gate`, `_is_stale_head`); `_git_commit_dispatch.py`; beads `sase-1cb`,
  `sase-1lh`, `sase-1lh.7`.
- **Queried today (high confidence):** the last 300 Master Gate runs (outcomes, durations,
  push gaps, overlap, onsets, episodes), 271 Full CI runs, PyPI release history, branch
  protection and ruleset state, org plan, repo merge settings, `sase tool stats` for `check`,
  bead counts, failing-test names for 15 onset runs and 2 Full CI runs.
- **Medium confidence:** the flake versus real split (signature-based); the modeled revert
  benefit; the single-runner capacity hypothesis.
- **Not done:** I did not enable a ruleset or merge queue, rerun any failed SHA, measure job
  queue waits, prototype the release-branch publish, or read the other swarm researchers'
  reports.
- **External claims** come from web searches and one fetch of GitHub's merge-queue docs; the
  merge-queue plan availability for a Free-plan org's public repo rests on a 2023 GitHub
  changelog, so confirm it in Settings → Rules before depending on it.

## Sources

Local (SASE checkout and sidecars):

- `research:202610/gastown_vs_sase_lessons_to_borrow/gastown_vs_sase_lessons_to_borrow.md`
- `research:202610/master_ci_red_why_and_how_to_stay_green/master_ci_red_why_and_how_to_stay_green.md`
- `.github/workflows/{publish,ci,master-gate,full}.yml`, `release-please-config.json`
- `tools/_release_watch_engine.py`, `src/sase/vcs_provider/plugins/_git_commit_dispatch.py`
- Decision records: `ci-two-speed-split`, `host-owned-completion`,
  `receipts-prove-before-they-skip`, `check-full-is-explicit`
- Beads: `sase-1cb`, `sase-1lh`, `sase-1lh.7`

External:

- [Managing a merge queue (GitHub Docs)](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)
- [Pull request merge queue is generally available (GitHub changelog, 2023-07-12)](https://github.blog/changelog/2023-07-12-pull-request-merge-queue-is-now-generally-available/)
- [GitHub Actions limits and billing (GitHub Docs)](https://docs.github.com/en/actions/reference/usage-limits-billing-and-administration)
- [Keeping master green at scale (Uber, EuroSys 2019)](https://eng.uber.com/research/keeping-master-green-at-scale)
- [CI at Scale: Lean, Green, and Fast (arXiv 2501.03440)](https://arxiv.org/html/2501.03440v2)
- [Merge trains (GitLab docs)](https://docs.gitlab.com/ci/pipelines/merge_trains/)
- [The origin story of merge queues (Mergify)](https://mergify.com/blog/the-origin-story-of-merge-queues)
- [Release from trunk (trunkbaseddevelopment.com)](https://trunkbaseddevelopment.com/release-from-trunk)
- [release-please-action (googleapis)](https://github.com/googleapis/release-please-action)
- [Dart recipes `lkgr.proto`](https://dart.googlesource.com/recipes/+/e586b1f7adf5e9f09052c7c6a3a0c75bac6f99e8/recipes/roller/lkgr.proto)
