# How GitHub's native merge queue works

> Independent research for the fenced-`master` / exact-SHA release plan in
> `research:202610/merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md`.
> Researcher `grk` · 2026-10-17.

## Bottom line

GitHub's merge queue is a **server-side, FIFO admission lane for pull requests**.
When you enqueue a PR, GitHub builds a **temporary merge-group branch** that
contains `master` (or whatever the base is) plus every PR ahead of yours plus
yours. CI runs on **that** commit via the `merge_group` event. Only after those
required checks pass does GitHub land the group onto the base branch.

A required-PR rule by itself does not do this. PR CI tests each change against a
stale base. The queue is the piece that tests the **combination that will
actually land**.

Two facts matter for SASE's plan:

1. **The SHA CI tested is almost never the SHA that becomes `master`.** Native
   merge methods are merge / squash / rebase. GitHub does not offer a
   fast-forward of the tested merge-group commit. The *tree* should match. The
   *commit object* is new. Exact-SHA PyPI releases must publish the **landed**
   SHA (or prove tree equality), not the `gh-readonly-queue/…` SHA.
2. **`sase-org/sase` can use it today.** Merge queues are available on any
   public organization-owned repository. They are not a GitHub Team/Enterprise
   tax for a public org repo. Required reviews of 1+ would deadlock, because
   agents push as the maintainer and GitHub will not let you approve your own
   PR. Zero approvals is a supported setting.

## The problem it solves

Two PRs can each pass CI against today's `master` and still break `master`
together: they touch different lines, Git reports no conflict, and each was
green in isolation.

GitHub's older answer is **Require branches to be up to date before merging**.
That forces every author to rebase and re-run CI every time someone else lands.
On a busy branch that is a stampede: each merge invalidates every open PR.

The queue is the same guarantee without the stampede. Authors enqueue once.
GitHub rebases (conceptually) onto the predicted future `master` and tests that
prediction.

GitHub's own docs say this is "particularly useful on branches that have a
relatively high number of pull requests merging each day from many different
users." GitHub.com itself ships this way: merge queue is the single entry point
for their large monorepo (~2,500 PRs/month, groups of 30+).

## What happens, step by step

Imagine `master` at commit `M`, with PRs #101 then #102 then #103 enqueued.

```
Queue position   Temporary branch                         What CI tests
1. #101          gh-readonly-queue/master/pr-101-<sha>    M + #101
2. #102          gh-readonly-queue/master/pr-102-<sha>    M + #101 + #102
3. #103          gh-readonly-queue/master/pr-103-<sha>    M + #101 + #102 + #103
```

For each row GitHub:

1. Creates that read-only branch. You cannot push to it. While a PR is in the
   queue you also cannot push to the PR branch; dequeue first.
2. Fires `merge_group` with activity `checks_requested`. In Actions,
   `GITHUB_SHA` is the merge-group commit and `GITHUB_REF` is that temporary
   ref. Third-party CI must trigger on pushes to
   `gh-readonly-queue/{base_branch}/**`.
3. Waits for every **required** status check to report success on that SHA,
   or for the configured timeout.

If #101 and #102 both pass, GitHub merges the **#102 temporary branch** into
`master`. That lands both PRs, because the #102 branch already contains #101.

If #101 fails, GitHub **ejects #101**, rebuilds #102 as `M + #102` only, and
re-runs its checks. Everything behind a failure is invalidated. Jumping a PR to
the front of the queue does the same: it "introduces a break in the commit
graph" and rebuilds every in-flight group.

That rebuild cost is why flakes are expensive here. A false red does not just
bounce one PR; it burns the CI already running for everyone behind it.

## Three SHAs, not one

| SHA | What it is | Who tests it | Does it become `master`? |
| --- | --- | --- | --- |
| PR head | The agent's branch tip | `pull_request` workflows | No. Stale the moment anything else lands. |
| Merge-group head | Temporary commit on `gh-readonly-queue/…` | `merge_group` workflows. This is the admission test. | **No.** Different SHA from the PR. GitHub then *merges that branch into* the base using merge, squash, or rebase. |
| Landed `master` tip | The commit GitHub creates at land time | Whatever you run on `push` to `master` | Yes. This is the SHA a release job can pin. |

GitHub's docs are explicit: the temporary branches "contain a different `sha`
from the pull request," and on success "the temporary branch … will be merged
in to the target branch." Native merge methods are only `MERGE`, `SQUASH`, and
`REBASE`. There is no fast-forward-the-tested-commit option (Mergify and some
other queues do offer that; GitHub's native queue does not).

So:

- **Gate-green** is a property of the merge-group SHA.
- **Release-green** is a property of the landed SHA (or of a tree-equal
  artifact built from the merge-group).
- Assuming `master`'s SHA *is* the tested queue commit is the wrong mental
  model. The *contents* were tested. The *commit object* is new.

The 23 April 2026 incident is the existence proof that GitHub **recomputes**
the land rather than moving the tested ref. A bad merge-base calculation
produced squash commits whose trees did not match what CI had seen.

## Settings that actually change behavior

You turn the queue on with **Require merge queue**, either as a classic branch
protection setting (exact branch name, **no wildcards**) or as a **repository-
level** ruleset rule (not an organization-level ruleset).

| Setting | Ruleset name | What it does |
| --- | --- | --- |
| Merge method | same | `MERGE` / `SQUASH` / `REBASE`. Linear-history rules force squash or rebase. |
| Build concurrency | `max_entries_to_build` | How many `merge_group.checks_requested` events fire at once (1–100). This is CI parallelism, not how many PRs land together. `0` freezes the queue. |
| Only merge non-failing PRs | grouping strategy `ALLGREEN` vs `HEADGREEN` | **On (ALLGREEN):** every PR in the group must have passing checks. **Off (HEADGREEN):** only the head of the group (the combined tree) must pass. HEADGREEN is how you cut flake exposure from N draws to 1, at the cost of a failed head ejecting the whole group with no per-PR culprit. |
| Status check timeout | `check_response_timeout_minutes` | After this, missing checks are treated as failed and the PR is ejected. |
| Min / max PRs to merge | `min_entries_to_merge` / `max_entries_to_merge` | How many PRs GitHub **lands** in one go, once some merge-group has passed. Docs: "Merge limits do **not** combine `merge_group` builds." You still get one CI run per queued PR. Min+wait is for batching *deploys*, not for saving CI. |

Build concurrency 2 with max group size 1 is the "test speculatively, land one
at a time" shape. That matches a "every `master` SHA is attributable" goal
better than large land-groups, and it is also the shape that would have
avoided the April 2026 squash-group bug (which only hit groups of more than
one PR).

## CI wiring: the `merge_group` event

This is the setup step that actually breaks people.

```yaml
on:
  pull_request:
  merge_group:
    types: [checks_requested]
```

- `merge_group` is a **separate event** from `pull_request` and `push`. If a
  required check's workflow does not list it, the check never starts, the
  queue waits until timeout, and the PR is ejected. GitHub's docs use
  "must."
- Required checks are **coupled** across PR and queue: the same job *names*
  on the branch protection / ruleset list. A check must have reported in the
  last 7 days to show up in the picker.
- `actions/checkout` defaults to `GITHUB_SHA`, which is correct on
  `merge_group`. Any workflow that checks out
  `${{ github.event.pull_request.head.sha }}` is wrong in the queue (there is
  no `pull_request` payload).
- A job skipped by `if:` reports **Success**. A whole workflow skipped by a
  path filter stays **Pending**, and Pending holds the queue until timeout.
  The dangerous pattern is `if: github.event_name == 'pull_request'` on a
  *required* job: on `merge_group` it skips, counts as success, and the queue
  lands untested code.
- `push` workflows will also fire on `gh-readonly-queue/**` unless you
  `branches-ignore` them. Required queue checks should use `merge_group`, not
  piggyback on `push`.

A practical split: cheap PR jobs for authors, the same *job name* (or a
rollup job that `needs:` the real work) required for the queue. Matrixes need
an `if: always()` rollup; otherwise a skipped shard looks green.

## How a PR enters and leaves

**Enter** (write access, PR already satisfies branch rules, or auto-merge
waiting for them):

- PR UI: **Merge when ready** → **Confirm merge when ready**. You can click
  this before checks finish; GitHub enqueues when they do.
- `gh pr merge` on a queue-required branch: enqueues if checks have passed,
  otherwise enables auto-merge.
- GraphQL `enqueuePullRequest` (`pullRequestId`, optional `expectedHeadOid`,
  optional `jump: true`). `dequeuePullRequest` is the matching removal.
  `PullRequest.mergeQueueEntry` exposes `state`, `position`,
  `estimatedTimeToMerge`.

**Leave:**

- Required check failed on the merge group.
- Timeout.
- User / API dequeue. `gh` cannot dequeue or show the queue; the Branches
  page and the PR timeline can.
- Unresolvable branch-protection failure.

Admins with bypass can still **Merge without waiting for requirements** /
`gh pr merge --admin`. That skip is the hole a host landing lane would also
have. An empty bypass list is what "the queue is the only writer" actually
means, together with **Restrict updates** (rulesets) or "restrict who can
push" (classic protection).

**Require merge queue** governs *how PRs merge*. It is a different knob from
**Require a pull request before merging** and from **Restrict updates**. A
community report from May 2026 says GitHub started evaluating the merge-queue
rule on the initial ref-creation push as well, with no "do not require on
creation" toggle — so a ruleset that only has Require merge queue can block
`git push -u origin master` of a new branch. For an existing `master`, close
the direct-push hole with Restrict updates + Require a pull request (zero
approvals is enough) + empty bypass, then verify with a probe push. That
combination is what the fenced-`master` plan still needs to pilot.

## What the native queue does not do

These are product gaps, not misconfiguration:

- **No exact-SHA land.** No fast-forward of the tested merge-group commit.
- **No flake retry, no quarantine, no bisect.** A red check ejects. HEADGREEN
  is the only native "don't make every flake a serial killer" knob, and it
  sacrifices per-PR blame.
- **No merge freeze, no `Depends-On`, no scheduled merge.** Mergify/Trunk sell
  those on top.
- **No combining of CI.** One merge-group (so one CI run) per queued PR, even
  when several land together. GitHub's own stacked-PR team said in October
  2026 they are "working on another update so CI only runs for the head PR."
  That is not shipped as general merge-queue behavior.
- **No `gh` view or dequeue.** Automation should use GraphQL.
- **Jump-the-queue** rebuilds everyone. On GitHub Enterprise it is admin-only
  by default (custom role to grant). Treat it as a hotfix hatch, not a
  fairness tool.

## Availability and stacked PRs

- **Who:** public repos owned by an organization (any plan), or private repos
  on GitHub Enterprise Cloud. User-owned repos are not on the list. GHES has
  had it since 3.12.
- **Stacked PRs** became GA on 6 October 2026. A stack enters the queue as
  **one merge group**. Ejecting one PR ejects everything above it. The queue
  may exceed max group size by up to 50% to keep a stack together. With the
  merge-commit method, GitHub now creates **one merge commit per PR** (it used
  to create one for the whole group).

## The 23 April 2026 squash-group bug

Official status (`zsg1lk7w13cf`):

- Window: 16:05–20:43 UTC, 23 April 2026.
- Scope: merge-queue **squash** of a group with **more than one PR**. Merge
  and rebase groups, and any non-queue merge, were unaffected per the final
  RCA. An earlier status update also named rebase; the resolved text narrowed
  it to squash.
- What landed: squash commits computed from the wrong merge base, which
  **reverted earlier PRs and prior `master` commits**. CI had been green on
  a different tree. GitHub's monitoring did not catch it because availability
  was fine; customers reported it ~3.5 hours in.
- Blast radius GitHub published: 2,092 PRs (COO Kyle Daigle also tweeted
  2,804 / ~0.07% of that day's merges). They mailed recovery steps to
  affected admins.

The lesson for a fenced-`master` design is not "never use GitHub's queue." It
is: **treat land as a second, observable event**, compare trees, and prefer
the merge-commit method with max group size 1 until you have watched a pilot.
A release job that builds `github.sha` on `push` to `master` would have
published the *wrong contents* during that window if it trusted the queue
blindly — and would have been correct if it rebuilt from the landed SHA
*after* a tree check against the last green merge-group.

## Implications for the SASE plan

Mapped onto the fenced-`master` / exact-SHA brief, without re-litigating the
cadence or flake numbers:

1. **The queue is the right fence for landings**, and `sase-org/sase` is in
   the public-org availability set. PRs are plumbing. Set required approvals
   to **zero**. Required reviews of 1+ deadlock a maintainer-authored PR.
2. **Wire `merge_group` on Master Gate before flipping the switch.** Forgetting
   this is the classic "queue fills, nothing merges, then everything times
   out" failure. Drop any `if: event_name == pull_request` on required jobs.
3. **Close the direct-push hole with other rules**, not with the queue rule
   alone: Restrict updates, Require a pull request (no approvals), block
   force-push / deletion, empty bypass. Probe it.
4. **Do not treat the merge-group SHA as the release SHA.** Phase 0 of the
   brief (build the release commit, run the full matrix on that SHA, upload
   those files) is still required *after* the queue exists. The clean hook is
   `push` to `master` / `release-please` on the landed SHA. Optionally stash
   merge-group artifacts keyed by `git rev-parse HEAD^{tree}` and reuse them
   only when the landed tree matches.
5. **Start with merge commits, max group size 1, ALLGREEN, concurrency 2.**
   That is the conservative native configuration: one attributable land at a
   time, the method the April 2026 RCA left standing, two speculative builds
   in flight. HEADGREEN and larger land-groups are optimizations after the
   gate's false-red rate is low.
6. **Ejection is asynchronous.** "Agent finished" and "landed" are different
   states. A host that closes beads on stitch-create will lie once the queue
   owns the merge. Wait for `merged` (or a `push` to `master` containing the
   PR) before resolving `%w(bead=…)` waiters.
7. **A flaky required check is a random rebuild cannon.** The queue will not
   retry for you. The brief's "trustworthy gate first" ordering is load-
   bearing. Under 3% false reds is the difference between a queue and a
   lottery.

## Sources

**GitHub docs (canonical):**

- [Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue) — mechanism, settings, success/fail/jump walkthroughs, `merge_group` requirement, `gh-readonly-queue/` prefix, no-wildcard branch protection.
- [Merging a pull request with a merge queue](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/merging-a-pull-request-with-a-merge-queue) — availability, Merge when ready, `gh pr merge`, dequeue, ejection reasons.
- [Events that trigger workflows: `merge_group`](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#merge_group) — `GITHUB_SHA` / `GITHUB_REF`, `checks_requested` only.
- [Webhook events: `merge_group`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#merge_group) — "perform checks on the head SHA and report status back."
- [Available rules for rulesets (GHEC)](https://docs.github.com/en/enterprise-cloud@latest/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-merge-queue) — repo-level-only rule, concurrency `0` freeze, ALLGREEN vs HEADGREEN wording, min/max group size.
- [REST API: `merge_queue` rule parameters](https://docs.github.com/en/rest/repos/rules) — `grouping_strategy` (`ALLGREEN`/`HEADGREEN`), `merge_method` (`MERGE`/`SQUASH`/`REBASE`), `max_entries_to_build`, `min/max_entries_to_merge`, timeout.
- [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) — Require merge queue as a sibling of required checks / required PRs.
- [Require a pull request before merging](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging) — "doesn't necessarily have to be approved, but it must be opened."

**GitHub product / engineering:**

- [Pull request merge queue is now generally available](https://github.blog/changelog/2023-07-12-pull-request-merge-queue-is-now-generally-available/) (2023-07-12) — public org repos + GHEC; `merge_group` `destroyed`; jump-queue restricted to admins on Enterprise.
- [API support in public beta](https://github.blog/changelog/2023-04-19-pull-request-merge-queue-public-beta-api-support-and-recent-fixes/) — `enqueuePullRequest` / `dequeuePullRequest` / `mergeQueue` / `mergeQueueEntry`.
- [How GitHub uses merge queue](https://github.blog/engineering/engineering-principles/how-github-uses-merge-queue-to-ship-hundreds-of-changes-every-day/) (2024-03-06) — internal trains → queue; 30k+ PRs before GA.
- [Stacked pull requests generally available](https://github.blog/changelog/2026-10-06-stacked-pull-requests-generally-available/) (2026-10-06) — stack as one merge group; one merge commit per PR.
- GraphQL `EnqueuePullRequestInput`: `pullRequestId`, `expectedHeadOid`, `jump` (documented on GHES 3.16 schema; same mutation on github.com).

**Incident:**

- [GitHub status: Incident with Pull Requests, 2026-04-23](https://www.githubstatus.com/incidents/zsg1lk7w13cf) — squash multi-PR groups, wrong merge base, 2,092 PRs, customer-detected.
- [Kyle Daigle, 2026-04-24](https://x.com/kdaigle/status/2047803291988590609) — 2,804 PRs / 0.07%.
- [The Stack write-up](https://www.thestack.technology/github-bug-messed-up-customer-code-coo-plays-down-incident/) — COO "edge case" comment.

**Secondary (used to cross-check, not as authority over the docs):**

- [cubic, "GitHub merge queue: how it works and how to set it up"](https://www.cubic.dev/blog/github-merge-queue) (2026-10-16) — clear walkthrough of speculative groups and the "CI runs twice" FAQ.
- [Mergify, merge strategies](https://docs.mergify.com/merge-queue/merge-strategies/) — GitHub native has no fast-forward; Mergify does, and that is how you preserve the tested SHA.
- [GitHub community #193295](https://github.com/orgs/community/discussions/193295) — Require merge queue evaluated on direct/creation pushes (May 2026).
- [GitHub community #75568](https://github.com/orgs/community/discussions/75568) — skipped required jobs count as success; use an `if: always()` rollup.

**Context (this swarm):**

- `research:202610/merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md`
