---
create_time: 2026-08-26
updated_time: 2026-08-26
status: research
---

# Making release-please automation live under continuous merge traffic

**Research question:** Why can the release-please PR remain unmerged for hours while
GitHub Actions continually cancels runs, and what release architecture will make forward
progress without consuming an unbounded runner queue or weakening release safety?

**Scope:** `sase` at `a3011392c`, `bbugyi200/bugyi-chops` at `0a7c2e1f`, the
latest 500 GitHub Actions runs visible at 2026-08-26T16:50:28Z, repository settings and
open release PR #284 observed on 2026-08-26, and current GitHub/release-please
documentation. This is research, not an implementation; no release or repository
setting was changed.

## Bottom line

The cancellations are an expected consequence of the configured bounded concurrency,
but they are not the real defect. The defect is a **liveness-incompatible release
predicate**: `ci_watch` requires the *current* `master` HEAD to have terminal green CI,
while new commits arrive about ten times faster than the full master workflow reaches a
terminal result.

In the measured 23.5-hour window, master CI never succeeded. One old run could execute
while every intermediate pending run was replaced; by the time that old run finished,
`master` had moved, and `ci_watch` deliberately rejected its result as stale. Preserving
all pending runs would turn cancellation into backlog without making current HEAD green.

The durable fix is to certify changes **before** they enter `master`, through GitHub's
merge queue, and have `ci_watch` place a fully generated release PR at the front of that
queue with expected-head race protection. The release candidate then gets a stable
queue position and a `merge_group` check against the latest base while later work waits
behind it. Post-merge master CI can remain useful for incident detection, but it should
not be the release transaction's liveness gate.

## 1. What the system does today

### 1.1 Master CI is bounded latest-pending, not an ordinary FIFO

The [current CI workflow](https://github.com/sase-org/sase/blob/a3011392c432bf3232f9cdb1e1337d5aa5222cc5/.github/workflows/ci.yml#L12-L21)
uses one concurrency group per ref and sets `cancel-in-progress` to false on `master`.
That protects the one *running* master workflow, but it does not preserve every pending
workflow. GitHub's default concurrency behavior permits one running and one pending run;
a newer arrival replaces the pending run. GitHub now offers `queue: max` to retain more
pending runs, but that is opt-in. See [Control the concurrency of workflows and
jobs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).

The workflow comments describe this accurately: one running plus one pending, with a
newer push replacing the pending slot. A spot check of four canceled master runs
(`32971100115`, `32980498606`, `32986438525`, and `32988549998`) found zero jobs in
each run. These were pending-slot replacements, not four expensive jobs killed halfway
through.

### 1.2 release-please and metadata sync move the release PR on every master push

The [Publish workflow](https://github.com/sase-org/sase/blob/a3011392c432bf3232f9cdb1e1337d5aa5222cc5/.github/workflows/publish.yml#L3-L18)
runs for every non-`sdd` push to `master`. release-please updates the pending PR, and the
workflow's [metadata reconciliation job](https://github.com/sase-org/sase/blob/a3011392c432bf3232f9cdb1e1337d5aa5222cc5/.github/workflows/publish.yml#L63-L123)
can add a second commit to its head after updating `uv.lock` and the published-core
floor. That behavior is consistent with release-please's model: it intentionally keeps
a release PR up to date as more work is merged, then tags a release when that PR is
merged. See the [release-please release-PR
lifecycle](https://github.com/googleapis/release-please/blob/05c6a4f71022304d4edad24ea90c1c16324503d5/README.md#L18-L33).

The project already gives that branch a small, specialized
[`release-core-floor-smoke`](https://github.com/sase-org/sase/blob/a3011392c432bf3232f9cdb1e1337d5aa5222cc5/.github/workflows/ci.yml#L402-L445)
instead of the full source matrix. This part normally converges quickly.

### 1.3 `ci_watch` requires two independent green certificates

The watcher requires both:

1. the current default branch to be green; and
2. the release PR to be clean, mergeable, generator-idle, and to have a non-empty,
   fully green check rollup.

The exact guard is documented in the [chop
README](https://github.com/bbugyi200/bugyi-chops/blob/0a7c2e1f13a425b12eab2e5f1a83c29f8d9fbe9f/README.md#L88-L99)
and implemented by
[`plan_release_merge`](https://github.com/bbugyi200/bugyi-chops/blob/0a7c2e1f13a425b12eab2e5f1a83c29f8d9fbe9f/src/bugyi_chops/ci_watch.py#L554-L588).
The default-branch classification is intentionally exact: a green settled SHA is green
only if it still matches current HEAD; otherwise it becomes `newer_head_unsettled`.
This is a sound fail-closed rule in isolation, but it cannot make progress when HEAD
moves faster than CI.

## 2. Measurements

The latest 500 runs returned by `gh run list` spanned
2026-08-25T17:19:20Z through 2026-08-26T16:50:28Z. The sample is a fixed latest-500
window, not a claim about runs before its start.

| Workflow/ref | Success | Failure | Canceled | In progress | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| CI / `master` | 0 | 12 | 56 | 2 | 70 |
| CI / release-please branch | 58 | 36 | 24 | 1 | 119 |
| Publish / `master` | 65 | 1 startup failure | 1 | 2 | 69 |
| Deploy Docs / `master` | 58 | 0 | 8 | 3 | 69 |
| PR Title / release-please branch | 173 | 0 | 0 | 0 | 173 |

Timing measurements within the same window:

| Measurement | Result |
| --- | ---: |
| Median interval between master CI arrivals | 638 s (10.6 min) |
| Median duration of terminal failed master CI runs | 6,556.5 s (109.3 min) |
| Median duration of successful release-PR CI runs | 71.5 s |
| Master CI service time / arrival interval | 10.3x |

The release-PR lane therefore does reach green frequently. Some of its short red runs
are intermediate heads: for example, run `32980768536` failed the floor smoke, and the
subsequent reconciled-head run `32980811498` succeeded about a minute later. The
watcher's generator-idle and final-head reread guards are appropriate for that two-step
update.

Master is different. The following cycle repeats:

```text
master A ── full CI(A) runs for roughly 109 minutes ───────────────┐
   B, C, D ... arrive every roughly 11 minutes                    │
   each new arrival replaces the one pending master run           │
                                                                  ▼
CI(A) ends, but HEAD is now K ── ci_watch rejects A as stale ── CI(K) starts
                                                                  │
                                      L, M, N ... repeat the cycle ┘
```

For the existing predicate to pass, a commit must be followed by a quiet period at
least as long as the full workflow, and that workflow must actually succeed. The sample
had no successful master workflow at all. A representative completed run
(`32976156802`) had genuine failures in coverage contexts, performance floors, visual
tests, and two Python test legs. Those failures are a separate correctness issue that
must not be relabeled as cancellation starvation.

## 3. Why the obvious fixes are insufficient

### Set `cancel-in-progress: false` on master

This is already the configuration. It preserves the running workflow, not the displaced
pending workflows.

### Add `queue: max`

This would make cancellation counts look better, but it would enqueue work about ten
times faster than the measured full-CI service rate. Current HEAD would sit at the back
of a growing FIFO, so the exact-HEAD release predicate would become slower rather than
live. A bounded queue of 100 eventually starts canceling again. This option is suitable
for scarce serial deployments whose arrival rate is below their service rate, not for
certifying every commit in this workload.

### Remove concurrency and run every master workflow

That trades a liveness failure for runner exhaustion. The workflow itself records that
unbounded org-wide contention previously stalled a core-wheel publish. It also spends
full-CI resources on commits already superseded for release purposes.

### Trigger release-please less frequently

Debouncing the Publish workflow would reduce the release branch's duplicate commits and
checks, so it is a useful efficiency follow-up. It does not fix the master predicate:
master still arrives every 10.6 minutes and requires roughly 109 minutes to certify.
It can also let release metadata lag code that would be included by a later merge unless
the release boundary is explicitly frozen.

### Wait for a quiet period

This preserves safety but makes release latency an accidental function of developer
activity. It is the behavior already being observed, not a control mechanism.

### Drop the default-branch guard and trust the release PR rollup

This would restore liveness today, but it is not yet a sufficient safety argument.
At observation time, GitHub's API reported no rulesets, no protection on `master`, and
`allow_auto_merge: false`. A green release metadata smoke does not prove that every
source change already entered `master` through enforced integration checks. The right
way to remove the post-merge guard is to make `master` green by construction first.

### Make full CI ten times faster

CI optimization is valuable, especially because current terminal runs exceed 100
minutes. Requiring performance alone to outrun an unbounded source of new commits is
fragile, however. It should reduce queue latency after the architecture is corrected,
not be the architecture's liveness proof.

## 4. The suitable GitHub primitive: a merge queue

GitHub describes merge queues specifically for busy branches. A queue tests a temporary
`merge_group` containing the pull request, the latest base, and entries ahead of it; it
merges only after required checks pass. Unlike strict "branch must be up to date"
protection, it does not require each PR author or bot to keep rebasing and restarting
checks. See [Managing a merge
queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue).

Two details matter for this project:

- Actions workflows that provide required checks must explicitly handle
  [`merge_group`](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#merge_group).
  The event's SHA is the merge-group SHA, which is the integration candidate that needs
  certification.
- GitHub's GraphQL `enqueuePullRequest` mutation accepts both `expectedHeadOid` and
  `jump: true`; the latter puts the PR at the front. See
  [`EnqueuePullRequestInput`](https://docs.github.com/en/graphql/reference/pulls#enqueuepullrequestinput).
  GitHub warns that jumping rebuilds affected in-progress queue entries, so it should be
  used once per deliberate release cut, not on every watcher tick.

That creates a deterministic release boundary:

1. release-please and metadata reconciliation finish for the current `master`;
2. the release PR's ordinary checks pass;
3. `ci_watch` atomically enqueues that exact head at the front;
4. the queue constructs and checks the release candidate against the latest base;
5. later changes wait behind the release entry, so they cannot continually invalidate
   the candidate;
6. GitHub merges it, and the existing Publish workflow tags and publishes the release.

This changes the gate from "eventually observe a quiet, green default branch" to
"establish a tested serialization point." That is the missing liveness guarantee.

## 5. Implementation shape and safeguards

The following is an architectural rollout outline, not a ready-to-run change list.

### 5.1 Make master green by construction

Add a repository ruleset for `master` that requires pull requests, a merge queue, and a
single stable required check such as `merge-gate`. Avoid broad bypass actors; a bypassed
direct push would invalidate the argument for removing the watcher’s post-merge guard.

Update CI to run on `merge_group` and make `merge-gate` an always-present aggregator.
It should fail unless the appropriate source checks and the release-floor smoke passed
for that merge-group SHA. Keep slow diagnostic, scheduled, coverage-artifact, or
post-merge jobs outside the required result unless their failure really must block every
merge. Required checks should express the smallest sufficient release certificate,
while `just check-full` and the existing broader lanes can continue to provide defense
in depth.

Configure the queue conservatively at first:

- require all queue entries to pass, rather than allowing a later green group head to
  mask an earlier failing entry;
- use a status-check timeout longer than measured gate duration;
- bound build concurrency to protect the organization runner pool;
- start with small merge groups, then tune group size and concurrency from measured
  throughput rather than enabling an unbounded Actions queue.

The current repository setting also reports `allow_squash_merge: false`, while
`ci_watch` currently invokes `gh pr merge --squash`. That is an independent direct-merge
failure waiting behind the current green guard. Re-enable squash if linear history is
the desired policy, or choose merge commits consistently. release-please supports both.
When a branch requires a merge queue, `gh pr merge` should not pass a merge strategy;
the queue owns it. See the [`gh pr merge`
manual](https://cli.github.com/manual/gh_pr_merge).

### 5.2 Make `ci_watch` an enqueuer and observer

For release submission, replace `default_branch_not_green` plus direct
`gh pr merge --squash` with a queue operation that preserves the existing fail-closed
guards:

- exactly one recognized release-please PR;
- non-draft, clean, and mergeable;
- non-empty green ordinary check rollup;
- release generator idle;
- final PR reread;
- expected release head OID;
- per-tick release cap and dependency order;
- explicit live mode.

Submit the GraphQL enqueue mutation with `jump: true` and `expectedHeadOid`, then record
an `enqueued` state rather than claiming `merged`. A later tick should confirm the PR's
actual merged state before writing the durable merge record and sending the release
notification. Default-branch CI health remains valuable for incident notifications; it
is only removed from the release-submission predicate.

Make the enqueue idempotent. If the exact head is already queued, do nothing. If the PR
head changes before enqueue, fail closed and retry a later tick. Once it is at the front,
master should remain stable until its merge-group check resolves; normal work can
continue to enter the queue behind it.

### 5.3 Roll out with evidence

Before enforcing the ruleset, fix or explicitly classify the currently genuine red
master jobs. Then run the new merge-group workflow as a non-required observation where
possible, enable the rule with a documented bypass/rollback procedure, and measure:

- time from release PR update to enqueue;
- time from enqueue to merge;
- number and cause of queue ejections/rebuilds;
- merge-gate duration and red rate;
- queue depth and developer wait time;
- runner-minutes per merged change;
- release boundary correctness (tag SHA, manifest version, changelog coverage, and
  package smoke).

Only after this works should Publish-workflow debouncing be considered. It is an
efficiency optimization, not part of the primary liveness fix.

## 6. Sources and reproducibility

Primary sources used:

- [GitHub Actions concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
- [GitHub merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)
- [GitHub `merge_group` event](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#merge_group)
- [GitHub required status checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging)
- [GitHub GraphQL merge-queue types](https://docs.github.com/en/graphql/reference/pulls#mergequeueentry)
- [GitHub CLI merge behavior](https://cli.github.com/manual/gh_pr_merge)
- [release-please release-PR lifecycle](https://github.com/googleapis/release-please/blob/05c6a4f71022304d4edad24ea90c1c16324503d5/README.md#L18-L33)
- [current SASE CI workflow](https://github.com/sase-org/sase/blob/a3011392c432bf3232f9cdb1e1337d5aa5222cc5/.github/workflows/ci.yml)
- [current SASE Publish workflow](https://github.com/sase-org/sase/blob/a3011392c432bf3232f9cdb1e1337d5aa5222cc5/.github/workflows/publish.yml)
- [current `ci_watch` implementation](https://github.com/bbugyi200/bugyi-chops/blob/0a7c2e1f13a425b12eab2e5f1a83c29f8d9fbe9f/src/bugyi_chops/ci_watch.py)

The run counts can be reproduced from the same repository with `gh run list --limit
500 --json workflowName,status,conclusion,headBranch,headSha,createdAt,updatedAt`. Because
the command is a rolling latest-500 window, later invocations need explicit timestamps
or archived JSON to reproduce this exact sample.

## Recommended solution

Adopt a protected `master` merge queue with a stable required `merge-gate` that runs on
`merge_group`, then change `ci_watch` from a direct merger into an idempotent,
expected-head queue enqueuer that moves a fully generated release PR to the front once
per release cut. Keep post-merge master CI as an incident signal, not a release gate;
fix genuine red jobs before enforcement; and treat `queue: max`, generator debouncing,
and CI speedups only as secondary optimizations. This is the only evaluated approach
that simultaneously creates a stable release boundary, preserves fail-closed testing,
bounds runner demand, and guarantees progress while development continues.
