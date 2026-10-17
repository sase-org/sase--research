# How GitHub's native merge queue works

> **Research query:** Help me understand how GitHub's native merge queues work. Context:
> [the merge-queue-fenced `master` report](merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md),
> which recommends landing every sase change through one.

## Bottom line

- **A merge queue is a line in front of `master`.** A PR doesn't merge when you click
  merge. It joins the line, and GitHub builds a temporary commit: the current `master`,
  plus every PR ahead of it, plus this PR. CI runs on that commit. If it passes, `master`
  moves to it. If it fails, the PR is removed and nothing lands.
- **`master` becomes exactly the commit that was tested.** I checked this on two public
  repos. On Homebrew/brew, all 16 recent `main` commits were tested queue commits. On
  bevy, 18 of 19 were, and the one exception most likely started testing just before my
  sample window. So "the landed SHA equals the tested SHA" holds in practice. GitHub's
  docs don't say this in so many words.
- **Each PR gets its own build, stacked on the ones ahead.** With build concurrency 2,
  PR B's build starts on top of PR A's untested commit. If A fails, GitHub rebuilds B
  directly on `master`. Batching settings only change how many passed PRs *land* at once.
  They never combine builds.
- **Your CI must listen to a new event, `merge_group`.** Every required check has to
  report on the queue commit. A required check that runs only on `pull_request` never
  reports there, so the queue waits until the timeout and then ejects the PR.
- **"Merged" happens later, and asynchronously.** `gh pr merge` exits 0 once the PR is
  *queued* or set to auto-merge. Automation has to watch for the actual merge.
- **sase can use it.** It is available on all public repos owned by an organization, and
  sase is one.

## The mental model

```text
 master:  M ─────────────────────────────────────────────▶ (fast-forwards to A, then B)
           \
 queue:     A'  = M + PR A               ← build 1 (gh-readonly-queue/master/pr-A-<M>)
              \
               B' = M + PR A + PR B      ← build 2 (gh-readonly-queue/master/pr-B-<A'>)

 A' passes → master = A'      B' passes → master = B'
 A' fails  → A ejected; B rebuilt as M + PR B, on top of master
```

The queue never lets `master` point at a commit that hasn't passed the required checks.
It also never asks an author to rebase or "update branch". The queue does that
integration itself.

## A PR's trip through the queue

1. **The PR's own required checks pass.** The rule is: "Once a pull request has passed
   all required branch protection checks, a user with write access to the repository
   can add the pull request to the queue."
2. **Someone enqueues it.** Options:
   - the **Merge when ready** button;
   - `gh pr merge`, which enqueues if checks have passed and otherwise turns on
     auto-merge, which enqueues later;
   - the GraphQL `enqueuePullRequest` mutation.
3. **GitHub builds a merge group.** It creates a branch named
   `gh-readonly-queue/<base>/pr-<number>-<parent-sha>` containing one new commit, and
   fires a `merge_group` event of type `checks_requested`. The parent is the newest
   commit ahead of this PR: either `master` or the previous PR's group commit.
4. **CI runs on that commit and reports its checks.** The queue waits for every required
   check, up to the status-check timeout.
5. **If it passes, `master` advances to that commit,** possibly together with other
   passed PRs, depending on the merge limits. The PR shows as merged, and the temporary
   branch is deleted (a `merge_group` event with action `destroyed`).
6. **If it fails, the PR leaves the queue.** GitHub records why on the PR timeline and
   fires `pull_request.dequeued`. The documented removal reasons are:
   - a failing required check;
   - a timeout waiting for CI;
   - a manual or API removal;
   - a branch-protection failure it cannot resolve;
   - a conflict with the base found while grouping.

## What a merge group is

- **Contents.** The latest base plus the changes of the PRs ahead of it, plus this PR.
  GitHub's example says the group for PR #2 "contains code changes from the target
  branch, pull request #1, and pull request #2".
- **A new SHA.** The group commit is not the PR head. The docs say these branches
  "contain a different `sha` from the pull request".
- **Which commit is built depends on the merge method.**
  - **Merge:** the queue makes a real merge commit, titled "Merge pull request #N from
    …", whose second parent is the PR head. The PR's own commits and SHAs survive.
  - **Squash:** one new commit holding the whole PR.
  - **Rebase:** one new commit, with a new SHA, for each PR commit.
- **What stacking looks like in practice (Homebrew/brew, Oct 17, merge method):**
  - At 12:36 the group for `pr-24193` was built on `987637f2c3`. That was PR 24281's
    group commit, which only reached `main` at 12:43.
  - `main` then became `3264f71d24`, which was exactly 24193's group commit.
  - The next five PRs follow the same pattern. Each branch name ends in the SHA of the
    commit it was stacked on.

## When a build fails

GitHub's documented rule: when a group fails, its PR is removed, and every group behind
it is rebuilt without it.

Here it is happening on bevy on Oct 5, reading the `CI` workflow's queue runs:

1. At 20:42, PR 25985 was built on `main` (`85cf…`), producing `44fe…`.
2. At 20:47, PR 25995 was built on `44fe…` and PR 26026 on top of that. The two builds
   started one second apart, so they ran concurrently.
3. PR 25985 failed. At 20:57, 25995 was rebuilt directly on `85cf…`, and 26026 was
   rebuilt on top of the new commit.

Rebuilds are the main cost of a queue. One failure near the front restarts every build
behind it. That is why the context report's simulation is so sensitive to the false-red
rate.

**Jumping to the front.** An entry can be moved to the head of the queue: the **jump**
button, or `enqueuePullRequest(jump: true)`. On Enterprise, only admins can jump by
default. Jumping rebuilds *every* in-progress group, because the reorder "introduces a
break in the commit graph".

## The settings

These live on the `merge_queue` rule of a ruleset, or under "Require merge queue" in a
classic branch-protection rule. Ranges come from GitHub's docs and API schema. I found no
documented defaults, so set every value explicitly.

- **Merge method** (`MERGE`, `SQUASH` or `REBASE`)
  - Sets how each PR becomes a commit in its group, and therefore on `master`.
- **Build concurrency** (`max_entries_to_build`, 1–100)
  - How many groups are building at once: how far ahead of the queue head GitHub
    speculatively stacks. This is the throughput knob, and it costs runners.
- **Group size**
  - `max_entries_to_merge`: how many *passed* entries can land together, 1–100.
  - `min_entries_to_merge`, plus `min_entries_to_merge_wait_minutes`: wait for a batch,
    but give up after the wait time.
  - "Merge limits do not combine `merge_group` builds." These limits change how often
    `master` moves, not how many builds run.
- **Only merge non-failing PRs** (`grouping_strategy`)
  - `ALLGREEN` (on): "the merge commit created by merge queue for each PR in the group
    must pass all required checks."
  - `HEADGREEN` (off): only the commit at the head of the group must pass. An earlier
    PR whose own build failed can still land if a later build that includes it passes.
  - The docs pitch `HEADGREEN` for "intermittent test failures". It tolerates flakes, at
    the cost of `master` holding commits whose own build failed.
- **Status check timeout** (`check_response_timeout_minutes`, 1–360)
  - Checks still silent at the deadline "will be assumed to have failed".

**Two live configurations, read from GitHub's rules API:**

- **Homebrew/brew** (a high-volume open-source project):
  - `MERGE`, `HEADGREEN`;
  - build concurrency 100, merge up to 100, minimum 1, wait 0;
  - timeout 60 min;
  - 36 required checks, and 1 approving review.
- **github/docs** (run by GitHub itself):
  - `SQUASH`, `ALLGREEN`;
  - build concurrency **2**, merge 1 at a time, minimum 1, wait 5 min;
  - timeout 60 min.

  The context report's proposed settings (merge, concurrency 2, `ALLGREEN`, 60 min) are
  close to this one.

## Wiring CI to the queue

- **Trigger on `merge_group`.** If you don't, "status checks will not be triggered…
  The merge will fail as the required status check will not be reported."
  - In the run, `GITHUB_SHA` is the group SHA and `GITHUB_REF` is the
    `gh-readonly-queue/…` ref.
  - Third-party CI has to build pushes to `gh-readonly-queue/<base>` instead.
- **Required checks are evaluated twice:** once on the PR head, as the ticket to enter,
  and again on the group commit, as the gate to land. The same check names must turn
  green both times. A common pattern is to make the PR-side run cheap with job-level
  `if:` and put the real work on `merge_group`. A job skipped by `if:` reports Success.
- **Don't let required workflows skip themselves.** A workflow skipped by a `paths`
  filter leaves its checks Pending, and a required Pending check blocks the merge.
- **Every required check must exist on both events.** A check that only makes sense on
  a PR, such as a PR-title lint, should either not be required or get a trivial
  `merge_group` job with the same name.
- **Use one aggregate required check.** A final job with `needs:` on everything and
  `if: always()` keeps the required list stable as jobs change. Job names must be unique
  across workflows, or a required check can resolve to the wrong job.
- **Watch `push` triggers.** GitHub emits a `push` event when it creates a queue branch,
  so a workflow with `on: push` and no branch filter also runs on every queue branch.
  Homebrew's push-triggered `release.yml` and four updater workflows run on its
  `gh-readonly-queue/…` branches. sase's push triggers are already filtered to
  `branches: [master]`, so they are safe.
- **Mind `concurrency:` keys.** Each group has its own ref and SHA, so keys built from
  `github.ref` or `github.sha` don't collide. A fixed key with `cancel-in-progress: true`
  would cancel queue builds. (This is my inference from how concurrency groups work, not
  something the docs state.)
- **Results attach to the group SHA, and that SHA becomes `master`.** After landing,
  `master`'s commit already carries its passing checks, so look up gate results by SHA.
  Look-ups by branch find nothing, because queue runs are on `gh-readonly-queue/…` refs.

## Driving it from automation

- **`gh pr merge`**, quoting its help text: "When targeting a branch that requires a
  merge queue, no merge strategy is required. If required checks have not yet passed,
  auto-merge will be enabled. If required checks have passed, the pull request will be
  added to the merge queue."
  - `--match-head-commit <sha>` refuses to enqueue if the PR head has moved.
  - `--admin` bypasses the queue, for actors who are allowed to.
  - Exit 0 means *queued or armed*, never *merged*.
- **GraphQL:**
  - `enqueuePullRequest(pullRequestId, jump, expectedHeadOid)`;
  - `dequeuePullRequest(id)`, the only programmatic way to remove an entry, since the
    CLI can't;
  - `repository.mergeQueue(branch:)` lists entries with their position and state:
    `QUEUED`, `AWAITING_CHECKS`, `MERGEABLE`, `UNMERGEABLE` or `LOCKED`.
- **Events a landing watcher can use:**
  - `pull_request`: `enqueued`, `dequeued`, `auto_merge_enabled`, `auto_merge_disabled`;
  - `merge_group`: `checks_requested`, `destroyed`;
  - then the PR's `merged` state.

  `dequeued` with no merge means ejected. Read the timeline for the reason.
- **Who can enqueue:** anyone with write access.

## Who can use it, and what it blocks

- **Availability:** "all public repos owned by organizations", plus private and public
  repos on Enterprise Cloud. User-owned repos are not listed. `sase-org/sase` is a public
  org repo, so it qualifies.
- **Classic branch protection** cannot use a merge queue with a wildcard (`*`) branch
  pattern. Rulesets are the modern home for it.
- **Direct pushes.** No GitHub page I read says outright that a merge-queue rule alone
  rejects direct pushes. What the docs do give you:
  - a "require a pull request" rule blocks them for anyone not on the bypass list;
  - "restrict updates" limits pushes to bypass actors;
  - required checks reject a new SHA that has no statuses.

  So pair the queue with the PR rule, and treat "queue alone blocks pushes" as unverified.
- **Bypass** applies to actors listed on the ruleset (roles, teams or apps), and `gh pr
  merge --admin` uses it. In sase, agents push as the maintainer, so any bypass the
  maintainer holds, agents hold too.

## Risks worth knowing

- **It is GitHub's code in your landing path.** On 2026-04-23, from 16:05 to 20:43 UTC,
  a regression made queues built with squash or rebase put commits on the wrong base,
  so earlier PRs in the same group appeared reverted. Reported counts differ: 2,092 PRs
  in 658 repos, or 2,804 PRs. Merge-method queues were not named as affected.
- **Flakes become ejections.** Under `ALLGREEN`, a flaky failure ejects a good PR and
  rebuilds everything behind it. The options are to fix the flakes, retry inside the
  job, or accept `HEADGREEN`'s weaker guarantee.
- **No bisecting.** The native queue builds one group per PR and has no
  "batch, then bisect on failure" mode. Throughput comes from build concurrency, which
  costs runners.
- **Queue state lives only on GitHub.** If the host restarts, it has to rediscover what
  it queued. Use the API, the timeline, and `--match-head-commit` to avoid enqueuing
  twice.

## What this means for the sase plan

The context report lists four behaviours to rehearse on a scratch repo. This research
settles some of them:

1. **"`master`'s new SHA equals the tested queue commit."** It does, in practice. 34 of
   35 landings on two repos were a tested queue commit, and the 35th most likely
   predates my sample window. Homebrew, which accounts for 16 of the 34, uses the merge
   method, the one the plan chose. Keep the tree-equality proof as cheap insurance, but
   expect it to be trivially true.
2. **"Does 'require merge queue' alone block direct pushes?"** Not documented. The plan
   already pairs the queue with a required-PR rule (0 approvals) and an empty bypass
   list, which blocks direct pushes on its own terms. Still confirm it in the rehearsal.
3. **"Does a check skipped by `if:` satisfy the requirement?"** Yes, it reports Success.
   A workflow skipped by a path filter does not.
4. **"How do PRs made with the maintainer's credentials trigger workflows?"** Normally.
   The no-new-runs rule applies only to events caused by `GITHUB_TOKEN`. The docs are
   silent on `merge_group` events when the enqueuer *is* `GITHUB_TOKEN`, so keep
   enqueuing as the maintainer or as a GitHub App.

**Two sase-specific gotchas found in today's workflows:**

- **`pr-title.yml` runs only on `pull_request`.** If it is ever made a required check,
  it would never report on merge groups, and every PR would time out in the queue.
- **`master-gate.yml` is keyed per SHA with `concurrency: master-gate-${{ github.sha }}`.**
  That stays safe under `merge_group`. But because `master` fast-forwards to the tested
  SHA, keeping the push-triggered gate during the pilot re-tests the identical commit,
  which is about 43 extra builds a day.
  - Treat it as a short-lived flake detector, not an independent audit.
  - Drop it once by-SHA look-ups work.

## Method and confidence

- **High confidence (documented by GitHub):**
  - entry and removal rules;
  - the `merge_group` trigger;
  - setting names, meanings and ranges, from the docs and from live GraphQL introspection
    of `MergeQueueParameters`, `EnqueuePullRequestInput`, `DequeuePullRequestInput`
    and `MergeQueueEntryState`;
  - `gh pr merge` semantics, from the local `gh` 2.96.0 help text;
  - availability.
- **High confidence (measured on live public data, read-only):**
  - queue branch naming, stacking, rebuild-on-failure, fast-forward to the tested SHA,
    and `push` runs on queue branches, from the Actions runs API on Homebrew/brew and
    bevyengine/bevy;
  - the two queue configurations, from `GET /repos/{repo}/rules/branches/main`.
- **Unverified:**
  - whether the queue rule *by itself* blocks direct pushes;
  - documented defaults for each setting;
  - how `merge_group` behaves when the enqueuer is `GITHUB_TOKEN`;
  - github/docs' rule also carries an undocumented `actor_controlled_merging: false`
    parameter.
- **Not done:** no repo, ruleset or workflow was created or changed.

## Sources

- GitHub Docs:
  - [Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)
  - [Merging a pull request with a merge queue](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/merging-a-pull-request-with-a-merge-queue)
  - [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
  - [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
  - [REST: repository rules](https://docs.github.com/en/rest/repos/rules)
  - [Events that trigger workflows: `merge_group`](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
  - [Triggering a workflow (the `GITHUB_TOKEN` rule)](https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/triggering-a-workflow)
  - [About pull request merges](https://docs.github.com/en/pull-requests/reference/pull-request-merges)
- GitHub blog:
  - [Merge queue GA changelog (2023-07-12)](https://github.blog/changelog/2023-07-12-pull-request-merge-queue-is-now-generally-available/)
  - [How GitHub uses merge queue to ship hundreds of changes every day](https://github.blog/engineering/engineering-principles/how-github-uses-merge-queue-to-ship-hundreds-of-changes-every-day/)
- The April 2026 incident:
  - [GitHub status: the incident](https://www.githubstatus.com/incidents/zsg1lk7w13cf)
  - [The Stack: coverage](https://www.thestack.technology/github-bug-messed-up-customer-code-coo-plays-down-incident/)
- Live API reads (2026-10-17):
  - Actions runs for `merge_group` and `push` events on Homebrew/brew and
    bevyengine/bevy;
  - `rules/branches/main` for Homebrew/brew and github/docs;
  - GraphQL introspection of the merge-queue types.
- sase checkout: `.github/workflows/{master-gate,ci,pr-title,docs-deploy}.yml`.
