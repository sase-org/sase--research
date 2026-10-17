# Merge discipline for a green `master` and more frequent PyPI

**Researcher:** `research.1w.grk` (independent swarm report)
**Date:** 2026-10-17
**Query:** After `gastown_vs_sase_lessons_to_borrow.md`, SASE looks like it needs better merge discipline so `master` stays green and new versions can ship to PyPI more often. Is a PR-only / protected-`master` workflow required, or is there a better way? Critique the plan. Adjust requirements where justified. End with a recommended solution.

---

## Bottom line

The goal is right. The usual GitHub means are wrong for this repo.

**Keep `master` green, and ship from a proven SHA.** Do that with a **host-owned landing lane** that rebases, re-verifies, refuses regressions, pushes, and proves the remote tip. Add GitHub **fences** (who may push, no force-push, tag rules) around that lane. Do **not** switch this project to PR-only, and do **not** turn on GitHub's merge queue as the first control.

A PR-only protected branch would fight three things SASE already decided: host-owned completion (agents never open PRs), two-speed CI (Master Gate is the per-SHA signal; Full CI is scheduled), and the measured landing cadence (tens of direct `master` pushes per day). GitHub required status checks also do not compose with "commit locally, then push the new SHA": the SHA has no checks until it exists on GitHub.

Gas Town's valuable idea is **verify the integrated tip, then prove the merge**. Its default merge strategy is `direct`, not GitHub PRs. Batch-then-bisect is unwired. Copy the proof, not the PR theater.

PyPI is still **0.17.1** (uploaded 2026-08-29). Release PR **#299** (`chore(master): release 0.18.0`) has been open since 2026-08-30. That is a 49-day publish stall. Red `master` is the main reason. It is not the only one: Full CI is also red, and #299's `release-core-floor-smoke` is failing. "Green HEAD" and "we can ship" should be **two contracts**, not one.

---

## Recommended solution (read this first)

**Build a SASE landing lane, then fence it. Publish from last-known-green.**

1. **Landing lease (host, not GitHub).** Serialize `rebase onto origin/master → verify the rebased tree → push → prove `origin/master` contains the SHA`. The VCS plugin already rebases and retries the push (`_sync_with_origin_after_commit`, `_push_current_branch_with_rebase_retry`, 3 retries). It never re-runs tests after that rebase. That is the merge-discipline hole.
2. **Ratchet, then pass.** Refuse a landing whose verified failure set on the **rebased** tree is worse than the tip's baseline (latest Master Gate / Full CI fingerprints, plus a covering `just check` receipt). This works while `master` is red. Once HEAD is green, tighten to `pass` (quarantine list only for reviewed `xfail`s). Receipts stay **proof for host completion**, never a skip (`decisions:receipts-prove-before-they-skip`).
3. **Stop-the-line.** While the tip is red past a short threshold, accept only failure-reducing landings and reverts. `ci_watch` already sees the gate; it should arm the hold and launch one fix-or-revert, not only notify.
4. **GitHub fences, not PR-only.**
   - **Now:** tag ruleset so only the release workflow can create tags. Block force-push and branch deletion on `master`. Restrict who may push to the landing token (and admins). **Do not** require pull requests. **Do not** require status checks yet.
   - **After the lane exists:** optional required Master Gate checks only if the lane lands a SHA that already has those checks (temp ref → wait → fast-forward), or if the landing actor is an explicit bypass. Required checks on a brand-new SHA will freeze `create_commit`.
5. **Last-known-green for PyPI.** Advance `refs/sase/lkg` (or a `stable` ref) whenever Master Gate is green on that SHA **and** Full CI is fresh enough. Point `ci_watch` / publish at LKG, not at a red HEAD. Keep the two-speed split: land on Master Gate; release on Master Gate + fresh Full CI.
6. **New decision record** beside `ci-two-speed-split`: "master landings require a covering receipt on the rebased tree; GitHub's merge queue remains rejected at this cadence." Do not silently reopen the CI decision as "turn on GitHub MQ."

This is Gas Town R1, SASE-shaped, plus Aspect's LKG idea so publish is not held hostage by the next red hour.

---

## Critique of the plan

The plan in the prompt is: *better merge discipline so master stays green so we can publish to PyPI more often; maybe PR-only / protected master.*

### What is good

- **Green `master` is a real product constraint.** `ci_watch` will not release while the per-SHA fast gate is red (`decisions:ci-two-speed-split`). PyPI 0.17.1 and a 49-day 0.18.0 PR are the cost.
- **Merge discipline is the right layer.** The Oct 1 swarm (`research:202610/master_ci_red_why_and_how_to_stay_green`) and the Oct 16 Gastown comparison both found the same defect: nothing refuses a red landing. Master Gate is post-push telemetry. Local `just check` on a red base carries no information. Repairs get overtaken.
- **The Gastown lesson is correctly aimed.** Verify the *integrated* tree, prove the remote contains the SHA, resolve dependents only after land. That is merge discipline. It is not "use GitHub PRs."

### What is confused

- **PR-only is a GitHub UX, not a green-trunk mechanism.** Required pull requests force every change through a PR page. They do not test the combination of this change with everything else that lands in the same hour. Loose required checks (PR against a stale `master`) still produce semantic collisions. Strict "must be up to date" plus no queue serializes authors. A merge queue tests the future trunk, but it needs PRs, `merge_group` CI, and a serial or batched GitHub job.
- **Protected `master` is several independent knobs.** GitHub lets you restrict pushers, block force-push, require status checks, require PRs, and require a merge queue as separate settings. "Protect master" does not imply "PR-only." Treating them as one decision will either under-protect (status checks with no pusher restriction) or over-constrain (required PRs + required full PR CI).
- **Publishing more often is not the same as HEAD always green.** Uber, Google, and Aspect all keep a *releasable* line (speculation queue, auto-revert, or last-known-green). SASE currently ships HEAD or nothing. That is why one red afternoon blocks 0.18.0 for weeks.
- **Cadence math already rejected GitHub's merge queue.** `decisions:ci-two-speed-split` (2026-08-28) lists a GitHub merge queue among the alternatives that failed to produce an attributable per-SHA signal without saturating runners. At ~40–90 landings/day and ~13 minutes p50 Master Gate, a serial queue is on the order of 9–19 gate-hours per day. That is the reopen trigger of that decision, not a reason to ignore it.
- **This project's default land path is already trunk-based.** `docs/concepts/landing.md` and the `builtin@commit` finalizer rebase and **push straight to `master`**. The Gastown report measured ~42 commits/day since Oct 1 on that path. Switching the default to `#pr` would make every agent a PR author, against `decisions:host-owned-completion`.
- **Gas Town itself does not use PR-only for its factory.** `mol-refinery-patrol.formula.toml` defaults `merge_strategy = "direct"` (merge+push). `pr` is optional. Post-merge proof is `verifyMQPostMergeProof`: the target branch must contain `commit_sha`. Batch-then-bisect is unwired. The Gas Town *repo* lands its own PRs through GitHub, which is a different machine from the factory.

### Would I take a different approach?

Yes. I would **not** start with "require PRs on `master`." I would start with:

1. a refusal point on the existing `create_commit` path (receipt + ratchet on the rebased tree);
2. a landing lease so two finalizers cannot race;
3. fix-or-revert when Master Gate is newly red;
4. an LKG ref so PyPI can move while HEAD is being repaired;
5. GitHub rulesets that make the landing token the only pusher.

PR-only is a later option for *human-reviewed* changes and for other projects. It is a poor default for this factory.

---

## Requirement adjustments (explicit)

These change the prompt's implied requirements. Each is justified.

| # | Original implication | Adjusted requirement | Why |
|---|----------------------|----------------------|-----|
| A | `master` HEAD must be green before we can publish | **Ship last-known-green.** HEAD should *tend* green; publish is allowed from LKG when HEAD is red. | 0.18.0 has been blocked for 49 days by HEAD health. Aspect's `stable` / LKG ref exists exactly so CD does not wait for a perfect tip. |
| B | Maybe adopt PR-only / protected master | **Protect `master` without requiring PRs.** Restrict pushers, forbid force-push and deletion, protect tags. Keep `create_commit` as the default land path. | Required PRs fight host-owned completion and the current VCS plugin. GitHub documents pusher restrictions as independent of "require PRs." |
| C | Green means "CI is required before merge" | **Green means "no new failures on the integrated tree," proven locally, witnessed by Master Gate after push.** Full CI stays a *release* freshness check, not a land gate. | `ci-two-speed-split`. PR CI (`ci.yml`) is heavier (3.12/3.13/3.14, visual, docs) than Master Gate. Making it the land gate would collapse throughput. |
| D | Wait until master is green, then refuse red landings | **Ratchet immediately.** Refuse landings that add failures versus the tip's baseline *while red*. Tighten to `pass` once green. | The Oct 1 report's "wait for green" rule cannot start until someone wins a stop-the-line race. Gastown R1's ratchet is the version that works today. |
| E | Merge discipline = GitHub merge queue | **Merge discipline = rebase + re-verify + prove.** GitHub MQ remains rejected at this cadence. Reopen `ci-two-speed-split` only if the local lane fails and gate p50 still does not fit cadence. | Decision already recorded. April 2026 GitHub MQ squash/rebase incident silently reverted customer code (status incident `zsg1lk7w13cf`). |
| F | Publish more often once master is green | **Also fix the other publish blockers:** Full CI freshness, `release-core-floor-smoke` on #299, and the published `sase-core-rs` floor. | Live: #299's release-core-floor-smoke is **FAILURE** as of 2026-10-16 23:43Z. Green Master Gate alone would not merge that PR. |
| G | `no_new_failures` is an acceptable land verdict forever | **`no_new_failures` is a red-HEAD ratchet verdict.** On a green tip, land requires `pass`, with quarantines only from a reviewed expiry list. | Today's catalog (`sase/sase.yml` `receipt.accept: [pass, no_new_failures]`) plus `verdict_provenance: "unverified"` is how 1,100 red commits landed. |
| H | A GitHub required-status ruleset is the gate | **Do not require GitHub status checks until the landing SHA already has them.** Until then, the host is the gate. | Required checks on a SHA that does not yet exist on GitHub block direct push unless the actor bypasses, which makes the check decorative. |

---

## Current SASE state (live, 2026-10-17)

### GitHub has no merge discipline at all

```
GET /repos/sase-org/sase/branches/master/protection  →  404 Branch not protected
GET /repos/sase-org/sase/rulesets                    →  []
```

Anyone with write can push, force-push, and tag. Master Gate cannot refuse a push it has not seen.

### Master Gate is a witness, not a gate

`.github/workflows/master-gate.yml` runs on `push` to `master`, grouped by SHA, never cancelled. Jobs: docs, core-wheel, lint (byte-for-byte with PR lint), eight shards of `just test`. Timeouts 20 minutes.

`.github/workflows/ci.yml` runs on **pull_request** to `master` and as the Full CI callee: lint, docs-build, test on 3.12/3.13/3.14 (coverage on 3.12), visual-test, plus release-core-floor-smoke. Heavier, and `cancel-in-progress: true` per ref.

`.github/workflows/full.yml` is scheduled every two hours and calls `ci.yml`. That is the release freshness lane.

So today:

- Direct push to `master` → Master Gate after the fact.
- A PR → full PR CI, which is *not* what most landings use.
- Exhaustive signal → up to two hours later, on a SHA that may already be buried.

### How a landing actually happens

```
agent dirty tree
  → /sase_final declaration (receipt optional)
  → builtin@commit
  → sase stitch create / vcs_create_commit
  → git commit
  → fetch + rebase onto origin/master  (semantic conflict resolver may auto-continue)
  → git push origin <branch>           (up to 3 rebase retries)
  → Master Gate starts on the new SHA
```

Source: `src/sase/vcs_provider/plugins/_git_commit_dispatch.py` (`vcs_create_commit`, `_sync_with_origin_after_commit`, `_push_current_branch_with_rebase_retry`). `_PUSH_REBASE_RETRY_LIMIT = 3`.

There is **no test step between rebase and push.** Two agents can each pass `just check` on yesterday's tip, rebase over each other, and land a combination nobody ran. That is the textbook semantic-conflict / "in-flight collision" (Aspect, GitHub merge-queue docs, Uber SubmitQueue).

The finalizer records `verdict_provenance: "unverified"` when the declaration has no covering receipt (`src/sase/finalizers/declaration.py`). The `check` catalog accepts `[pass, no_new_failures]` (`sase/sase.yml`). Host-owned prepared completion *can* require a receipt (`accept: pass` or `no-new`); ordinary `sase final submit` does not.

### Green was reached and not held

Master Gate on `master`, last 200 completed/in-flight runs as of 2026-10-17 01:47Z:

| Day | Pass | Fail | Other | Total |
|-----|------|------|-------|-------|
| 2026-10-12 | 0 | 42 | 0 | 42 |
| 2026-10-13 | 14 | 30 | 0 | 44 |
| 2026-10-14 | 16 | 17 | 0 | 33 |
| 2026-10-15 | 8 | 5 | 0 | 13 |
| 2026-10-16 | 6 | 56 | 0 | 62 |
| 2026-10-17 (partial) | 0 | 4 | 2 in flight | 6 |

This matches the Gastown report's Oct 13–15 recovery and Oct 16 collapse (they counted 6 pass / 52 fail; a few more failures completed after that tally). Last green SHA in the 30-run sample: `7e3af4c8` (2026-10-16 19:58Z). HEAD at sampling: `134d3bcf` (2026-10-17 01:47Z), 21 first-parent commits later, gate red or still running.

Full CI: the last eight completed runs are all **failure**. One in progress on `fce4fdbb`.

The Oct 1 report's treadmill is still the operating mode: a repair epic can go green for a day, then product landings overtake it because nothing refuses them.

### PyPI is stuck on more than red HEAD

- **PyPI `sase`:** 0.17.1, upload time **2026-08-29T23:22:14Z**.
- **Release PR #299:** `chore(master): release 0.18.0`, opened **2026-08-30**, still **OPEN**, updated 2026-10-16 23:40Z.
- **#299 checks:** `release-core-floor-smoke` **FAILURE**; most other CI jobs **SKIPPED** (release-please branch is excluded from several PR jobs).
- **`publish.yml`:** release-please on a 3-hour cron, then build + install-smoke + Trusted Publisher upload. It does not itself ask "is master green?"; `ci_watch` is the human/automation brake on merging that PR / dispatching publish.
- **Two-speed release contract:** `gating_workflows` must be green on *this* commit; `heavy_max_age_hours` needs a recent green Full CI. Both are currently unsatisfied.

So "keep master green" is necessary for the *current* publish policy. It is not sufficient, and it is a poor *sole* publish policy.

`sase bead search` for "merge queue" and "landing refusal" still returns nothing. The green-master *repair* plan (`plan:202610/green_master_ci_repair.md`) explicitly left the landing contract out of scope. The repair can win a day; the machine will lose the next one.

---

## What Gas Town actually ships (verified in tree)

Opened `gh:gastownhall/gastown` at the checkout this host prepared. The mechanisms that matter:

**Post-merge proof (real code).** `internal/cmd/mq.go` `verifyMQPostMergeProof` refuses to close the MR or delete the branch unless `origin/<target>` contains the submitted `commit_sha`. That is the piece SASE should copy. SASE's stitch success is "git push exited 0," which is weaker (a later force-push or a failed follow-up rebase is invisible to bead close).

**Merged-result tests (LLM-triggered).** The Refinery patrol formula (`internal/formula/formulas/mol-refinery-patrol.formula.toml`, 1,285 lines) merges the target into a temp branch, runs setup/typecheck/lint/build/test on that tree, then classifies failure as branch-caused (`FIX_NEEDED`) or pre-existing (merge anyway). Default `merge_strategy` is **`direct`**. `judgment_enabled` defaults false. This is a host-side rehearsal, driven by an LLM patrol — Gas City and Yegge's "crons watch, models act" both moved that kind of loop out of the LLM.

**Batch-then-bisect: unwired.** Confirmed again by the consolidated Gastown report: `AssembleBatch` / `ProcessBatch` / `bisectBatch` have no non-test callers. Do not design SASE around a queue Gas Town never turned on.

**Caveat.** The merge *verdict* is an LLM judgment and can merge red by calling a failure pre-existing. SASE should keep the verdict in deterministic code (receipt fingerprints vs baseline), which it already has.

---

## Industry options, scored for *this* repo

### 1. Direct push to trunk, verify after (status quo)

Used by small XP teams and by SASE today. Trunk-based development's own docs say this is fine only when the author runs the **same** build the CI daemon will run, on a tree that is up to date with HEAD, *before* push, and when cadence is low enough that a red HEAD can be reverted before the next wave.

SASE fails every clause except "we have a CI daemon." Authors (agents) often land with unverified or inherited-red checks. 42% of pushes (Oct 1 measurement) landed before the previous gate finished. Post-push revert cannot keep up.

**Verdict:** insufficient. Keep the *shape* (direct trunk, short-lived work), add a pre-push refusal.

### 2. PR-only + required checks, no queue

GitHub "require pull request reviews" + "require status checks." This is the default of many public repos.

What it would do here:

- Every agent landing becomes a Patch + PR. Host-owned completion would have to grow a merge-bot, or humans would click Merge all day.
- PR CI is `ci.yml`, heavier than Master Gate. Either you slim PR CI down to Master Gate (then "PR-only" bought you a web UI, not a better test) or you wait for 3.12/3.13/3.14 + visual on every land.
- Loose checks: PRs go green against stale `master`, then collide. GitHub's own docs say checks "may fail after you merge."
- Strict "must be up to date": every land rebases and re-runs CI after the previous merge. At this cadence that *is* a merge queue, with worse UX.

**Verdict:** not recommended as the default land path. Keep `#pr` for human-reviewed or cross-fork work.

### 3. GitHub merge queue

GitHub tests a `merge_group` (base + this PR + everything ahead), then merges. Requires `on: merge_group` in Actions, branch protection or a ruleset with "Require merge queue," and PRs.

Why it is tempting: it is the textbook fix for in-flight collisions.

Why it is a bad first move here:

- `ci-two-speed-split` already rejected it on runner-capacity and per-SHA attribution grounds.
- Serial Master Gate at 40–90 lands/day is 9–19 hours of gate time unless you batch. Batching is the complexity Gas Town never wired and Uber built a research program around (SubmitQueue, ICSE 2019; follow-up arXiv:2501.03440, 2025).
- GitHub's queue is **PR-shaped**. SASE landings are **commit-shaped**.
- **April 23, 2026 incident** (`githubstatus.com/incidents/zsg1lk7w13cf`): squash/rebase merge-queue groups used the wrong merge base for ~4.5 hours. GitHub COO: 2,804 PRs affected. The failure mode was silent history rewrite, not a red X. A factory that lands tens of times a day should not make that code path load-bearing until it has a local proof of the landed tree anyway.
- You still need flake policy, hermeticity, and a build-cop. Aspect (Alex Eagle, 2024) argues queues do not address those, add a third CI trigger (~50% more compute), and delay teammates pulling HEAD.

**Verdict:** do not enable. Revisit only if a local lane is in production and still losing to collisions *and* you are willing to land through PRs.

### 4. Third-party merge queues (Trunk, Mergify, Bors)

Same shape as (3), sometimes with better batching and flake quarantine. Still PR-centric. Trunk's own docs assume branch protection and PR admission. Extra vendor on the land path of a product whose host already owns completion.

**Verdict:** not unless SASE's landing lane is later factored as a plugin others can replace. Do not take a dependency to fix a hole in `builtin@commit`.

### 5. Presubmit + serial commit queue (Google Piper / Uber SubmitQueue)

The high bar: a change is tested against a predicted future trunk, and only successful combinations land. Uber's SubmitQueue speculates a tree of pending changes and lands only green prefixes; Google TAP / presubmit plus automatic undo. This is what "never broken master at thousands of commits/day" actually is.

SASE's volume is two orders of magnitude smaller. A **single-slot landing lease** plus re-test of `tip + this change` is SubmitQueue with speculation width 1. That is the right scale. Do not build a probabilistic speculation graph.

**Verdict:** emulate width-1. That is the local landing lane.

### 6. Policy + LKG + build-cop, no queue (Aspect)

Eagle's alternative to queues:

- freshness policy on green statuses;
- test the prospective merge (rebase onto current HEAD);
- `stable` / last-known-green ref for developers and CD;
- on-call build-cop with revert-first authority;
- invest in hermetic tests so people do not "break glass."

This maps onto SASE unusually well: `just check` receipts are the freshness policy; the VCS plugin already rebases; `ci_watch` is the build-cop that currently only pages; publish already wants a green SHA.

**Verdict:** this plus width-1 verification is the recommended design.

### 7. GitHub rulesets as fences (recommended, limited)

Rulesets can: restrict who pushes, block force-push, block deletions, require linear history, protect tags, allow bypass actors. They can also require PRs and status checks — those two should stay **off** until the landing lane can present a SHA that already has checks.

A useful first ruleset for `sase-org/sase`:

- Target: `master`
- Block force pushes, block deletions
- Restrict pushes to the SASE landing GitHub App / `SASE_RELEASE_TOKEN` identity and a tiny admin bypass
- **Do not** require PRs
- **Do not** require status checks in v1
- Separate **tag** ruleset: only `publish.yml` / release identity may create `v*` tags (Gastown R12; Beads 1.2.1 unauthorized-release lesson)

This is "protected master" in the sense the prompt meant (unauthorized and sloppy pushes die) without "PR-only."

GitHub: after required status checks are enabled, a commit may be **pushed directly** or merged via PR once those checks exist on that SHA. Direct push of a *new* SHA still fails the check requirement. That is why v1 must not require checks.

---

## How this fits SASE decisions

| Decision | Implication for merge discipline |
|----------|----------------------------------|
| `host-owned-completion` | The host, not the agent, pushes. The refusal point belongs in the commit finalizer / stitch path, not in agent etiquette. Agents still must not open PRs. |
| `single-turn-agents` | A landing lease that runs rebase+check+push inside the finalizer is a host continuation, not an agent waiting on CI. |
| `receipts-prove-before-they-skip` | A covering `check` receipt authorizes completion. It must not skip the child `just check` on the **rebased** tree. After rebase the fingerprint moved; the old receipt is invalid. That is a feature. |
| `ci-two-speed-split` | Land against Master Gate's contents (lint + 8-shard fast suite), locally via `just check`. Do not run Full CI on every land. Do not put a GitHub merge queue on the push path. |
| `check-full-is-explicit` | The landing verify recipe is `just check` (which may escalate internally). `just check-full` stays the CI-repair case. |
| `triage-annotates-does-not-change-exit-codes` | Ratchet compares failure *sets*, not "the agent said KNOWN." Inherited reds are baseline; new signatures refuse. |
| `guarded-recipes` | Landing verification goes through `sase tool run check` so it is a ToolRun with a receipt. |
| `global-install-is-human-only` | Unrelated, except: do not let a lander `just install` its way to a green local that CI cannot reproduce. |

A new decision is warranted. Do not overload `ci-two-speed-split` with landing policy; that record is about which GitHub workflow runs on push vs schedule.

If the landing refusal is epic-scaffolded, put it behind a **beta** flag (`sase flag new`) so the Off branch remains "today's unverified push" until the ratchet is proven. Per `sase_flags.md`, that flag is epic scaffolding and should be removed before the epic lands, not left as a forever config.

---

## Design of the landing lane (concrete)

### Lease

One flock / lease per repo default branch. Concurrent finalizers wait or defer with a typed reason. Without this, two "green on origin/master at T0" agents rebase over each other and the second push's rebase is untested.

### Algorithm

```
with landing_lease(repo):
    fetch origin/master
    rebase this commit onto origin/master   # already implemented
    if rebase conflict and not auto-resolvable:
        conflict-repair turn (already implemented)
        return
    run `sase tool run check` on the rebased tree   # NEW, fingerprint includes rebased HEAD
    baseline = latest Master Gate (or Full CI) failure set for origin/master
    if origin/master Master Gate is green:
        require receipt verdict == pass
    else:
        require failure_set(check) ⊆ baseline     # ratchet; NEW failures refuse
        if stop_the_line and not (repair_tag or revert):
            refuse
    push
    prove: origin/master contains this SHA        # NEW, Gas Town mq proof
    only then: close beads / resolve waiters
```

### What "check" covers vs Master Gate

`just check` is whole-repo lint except `toobig`, plus diff-scoped tests with escalation to the full fast suite when the selector cannot trust the closure. Master Gate always runs the full fast suite in 8 shards.

Risk: a scoped `check` misses a test Master Gate will fail. Mitigations already in-tree: escalation on dangerous change-sets; `tests/test_github_actions_ci_workflow.py` forbids CI from using the scoped lane. Residual risk is acceptable if `ci_watch` reverts a SHA whose parent was green and whose own Master Gate is red within a bounded window (60 minutes was the Oct 1 proposal; keep it).

Do **not** wait for GitHub Master Gate before every push. That recreates the queue you are avoiding. Local check is the land gate; Master Gate is the attributable witness and the revert trigger.

### Stop-the-line vs hold-pull-fail-open

`decisions:hold-pull-fail-open`: a hold gates *admission* of new runs. In-flight agents still finish and, today, still push. A real freeze must be at **landing**, or in-flight work must drain first. Put stop-the-line in the landing lease, not only in LaunchApproval.

### Beads and dependents

Close assigned beads and resolve `%w(bead=…)` only after the prove step. That is Gas Town `merge-blocks` / `"Merged in "`. SASE currently treats stitch success as land.

---

## Publishing more often (the actual goal)

Once the lane exists, change the release contract:

1. **LKG ref.** When Master Gate is green for SHA S, fast-forward `refs/sase/lkg` to S (or a `stable` branch). Never move LKG to a red SHA. Optionally require Full CI green on S or on an ancestor within `heavy_max_age_hours`.
2. **`ci_watch` releases LKG, not HEAD.** If HEAD is red and LKG is 0.18.0-ready, merge/publish from LKG. The 49-day stall is what you get when HEAD is the only releasable name.
3. **Keep two-speed.** Do not wait for Full CI on every land. Do wait for a fresh Full CI on the *release SHA* (already the decision).
4. **Unblock #299's other failures in parallel.** `release-core-floor-smoke` is red on the release PR head. A green Master Gate on `master` will not make that job pass. Treat core-floor / published `sase-core-rs` as a sibling epic, not as "merge discipline."
5. **Stop-the-line the day you want 0.18.0 out.** The Oct 1 and Gastown reports both observed: repairs without a freeze are a treadmill. The landing lease is that freeze. A one-off hold on non-repair launches is still needed for the first green SHA, because in-flight agents will otherwise push through.

A reasonable publish cadence after this: **weekly**, or whenever LKG has moved and Full CI is fresh — not "every green hour," not "whenever HEAD happens to be green."

---

## Sequencing

**Now (hours, operator + one authorized repair agent)**

- Stop-the-line: hold non-repair launches; drain in-flight; land one repair commit; lift only when Master Gate is green on that SHA.
- Tag ruleset (release identity only).
- Confirm #299 `release-core-floor-smoke` independently of master color.

**This week (landing lane v0)**

- Lease + re-`check` after rebase + ratchet vs tip baseline + push proof.
- `ci_watch`: on "parent green, this SHA red," arm landing stop-the-line and launch one fix-or-revert.
- Decision record + beta flag if the refusal ships before it is proven.

**Next (fences + publish)**

- Restrict `master` pushers to the landing identity; block force-push.
- LKG ref; point publish / `ci_watch` at it.
- Hours-since-last-green and commits-ahead-of-LKG in ACE (Oct 1 report §5.E). The second number should stay 0 or 1.

**Later, only if measured**

- Width>1 batching if lease queue depth is the bottleneck.
- GitHub required Master Gate checks *on a pre-pushed landing SHA* (two-hop: `landing/sha` → wait → FF `master`).
- PR-only for a *different* project or for a human-review class of changes. Not as the sase factory default.

**Explicitly not in this program**

- GitHub merge queue.
- Required PRs on `master`.
- LLM-judged merge (Gas Town Refinery verdict).
- Bisecting batches.
- Making Full CI or `just check-full` the land gate.
- Trusting `no_new_failures` on a green tip.

---

## Success metrics

Use these, not "we turned on branch protection":

| Metric | Target |
|--------|--------|
| Master Gate green on HEAD | Stay green once recovered; red hours per week near zero |
| Commits ahead of last green | 0 or 1 (a red SHA is being reverted or fixed, not piled) |
| Landings without a covering rebased-tree receipt | 0 for `create_commit` to `master` |
| Time from newly-red SHA to revert or fix | < 60 minutes |
| PyPI releases | At least weekly from LKG once 0.18.0 is out; 0.18.0 itself within one stop-the-line window after core-floor is green |
| GitHub MQ / required-PR enabled | No |

---

## Is this a good idea?

**Yes, with the adjustments above.** SASE is already a trunk-based, host-owned, high-cadence factory. It is missing the one habit trunk-based development never made optional: **run the integration build on the tree you are about to make canonical, and do not make it canonical if that build is worse.** GitHub PRs are one way to host that habit. They are a bad way to host it here.

The failure mode to fear is not "we didn't enable branch protection." It is "we enabled PR-only, doubled CI, serialized the factory, still landed semantic collisions because checks were loose, and still could not ship 0.18.0 because Full CI and core-floor were red."

The failure mode of the recommended design is slower individual lands (one extra `just check` after rebase) and occasional refused landings that need a repair turn. That is the cost of a green trunk. It is the correct cost.

---

## Sources

### SASE (this checkout and live APIs, 2026-10-17)

- `.github/workflows/{master-gate,ci,full,publish}.yml`
- `src/sase/vcs_provider/plugins/_git_commit_dispatch.py` (rebase-then-push, no retest)
- `src/sase/finalizers/declaration.py` (`verdict_provenance: "unverified"`)
- `sase/sase.yml` (`receipt.accept: [pass, no_new_failures]`)
- `docs/concepts/landing.md`, `docs/contribute/commit-workflow-orchestrator.md`, `docs/contribute/tool-run-receipts.md`
- `sase/memory/decisions/{ci-two-speed-split,receipts-prove-before-they-skip,host-owned-completion,check-full-is-explicit}.md`
- `gh api repos/sase-org/sase/branches/master/protection` → 404; `.../rulesets` → `[]`
- `gh run list` Master Gate (200) and Full CI (8); `gh pr view 299`; PyPI JSON for 0.17.1
- `sase bead search` "merge queue" / "landing refusal" → none

### Prior SASE research (audited reads)

- `research:202610/gastown_vs_sase_lessons_to_borrow/gastown_vs_sase_lessons_to_borrow.md` (R1 landing lane; PR-only claim marked false)
- `research:202610/master_ci_red_why_and_how_to_stay_green/master_ci_red_why_and_how_to_stay_green.md`
- `plan:202610/green_master_ci_repair.md` (repair-only; landing contract out of scope)

### Gas Town (opened `gh:gastownhall/gastown`)

- `internal/cmd/mq.go` `verifyMQPostMergeProof`
- `internal/formula/formulas/mol-refinery-patrol.formula.toml` (`merge_strategy = "direct"`)

### Industry

- GitHub Docs: [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches); [Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue); [About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- GitHub incident 2026-04-23: [Incident with Pull Requests](https://www.githubstatus.com/incidents/zsg1lk7w13cf); Kyle Daigle (COO) on the 2,804 affected PRs
- Paul Hammant, [Trunk-Based Development — CI](https://trunkbaseddevelopment.com/continuous-integration/) and [Committing straight to the trunk](https://trunkbaseddevelopment.com/committing-straight-to-the-trunk/)
- Ananthanarayanan et al., "Keeping Master Green at Scale," ICSE-SEIP 2019 (Uber SubmitQueue)
- Juloori et al., "CI at Scale: Lean, Green, and Fast," arXiv:2501.03440 (SubmitQueue 2025)
- Alex Eagle, [Keeping main green in a monorepo](https://aspect.build/blog/keeping-main-green) (2024): queues vs LKG + build-cop
- Potvin & Levenberg, "Why Google Stores Billions of Lines of Code in a Single Repository," CACM 2016 (trunk + auto-undo)
- Cubic, [GitHub merge queue: how it works](https://www.cubic.dev/blog/github-merge-queue) (2026): loose vs strict vs queue
