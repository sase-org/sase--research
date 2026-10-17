**GitHub native merge queues: how they work and what SASE must handle**

*Independent cdx research · 2026-10-17 · GitHub.com*

**Recommendation:** GitHub’s queue fits the proposed protected `master`: it automates testing changes together before admitting them. SASE still needs reliable checks, an asynchronous landing watcher, and separate release qualification. This report uses the [supplied proposal](merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md) as context; its measurements were not re-audited.

**What happens when changes enter the queue**

Suppose `master` is at M and PRs A, B, C enter in that order. GitHub creates temporary candidates:

| Candidate | Contents tested |
| --- | --- |
| A | M + A |
| B | M + A + B |
| C | M + A + B + C |

With sufficient build concurrency, these candidates can be tested simultaneously. GitHub lands passing changes in queue order. If A fails, GitHub removes A and rebuilds the affected candidates without it. B passing with A does not prove B passes without A. Conflicts and missing-check timeouts can also eject entries; moving an entry to the front rebuilds work behind it. The PR timeline explains removals. [Queue mechanics](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)

This solves the “two individually green changes break together” problem. Ordinary PR checks can test a merged result, but that result can become stale. Strict up-to-date protection also addresses this problem, at the cost of repeatedly updating PR branches. The queue manages those combinations automatically. [Branch protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

**CI must test the temporary candidate**

The essential Actions triggers are:

```yaml
on:
  pull_request:
    branches: [master]
  merge_group:
    types: [checks_requested]
    branches: [master]
```

For `merge_group`, `github.sha` identifies the candidate and `github.ref` identifies its temporary ref. Check out that candidate; explicitly checking out `master` or the PR head tests the wrong combination. A workflow listening only for PRs or pushes does not provide the required queue-event wiring. [Actions events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#merge_group)

Required check names are shared between PR admission and queue validation. GitHub does not expose independent required-check lists for these two stages. Merge limits also do **not** combine their CI builds: allowing five PRs to land together does not promise one build for five PRs. [Queue configuration](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)

**Correction to the proposal:** its cheap PR admission needs an event-aware `integration-ready` job. On PR events, validate the intended admission conditions; on queue events, require every integration dependency to have actually succeeded. An unconditional “all dependencies succeeded” rule rejects intentionally skipped PR jobs. Conversely, accepting skipped dependencies indiscriminately can admit an untested queue candidate. Use `always()` so dependency failures cannot skip the aggregate. Workflow-level path filters can leave required checks pending; conditional job skips are treated differently. [Check behavior](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks)

**The settings that matter**

| Setting | Meaning and suggested starting point |
| --- | --- |
| Build concurrency | Candidates requesting CI simultaneously. Start at **2**, as proposed; each candidate may fan out into many runner jobs. |
| Minimum / maximum merge size | How many PRs land together. Start **1 / 1** for easier diagnosis; consider **1 / 5** after the pilot. |
| Minimum-size wait | Delay while waiting to fill a group. With minimum 1, there is no batching wait to fill. |
| Require every queue entry to pass | Keep **enabled**. Disabling allows a passing cumulative head to cover earlier failing entries. |
| Check timeout | Time allowed for results. **60 minutes** is a pilot hypothesis from the supplied context; include runner waiting time. |
| Merge method | Use **merge**, consistent with the proposal. |

These are recommendations, not GitHub defaults. The [ruleset documentation](https://docs.github.com/en/enterprise-cloud@latest/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-merge-queue) defines the controls. Merge commits preserve the original commits; squash/rebase rewrite history, so proof based on the agent’s original SHA needs a different approach. [Merge methods](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-methods-on-github)

**What SASE must track after submission**

`gh pr merge` can succeed by enabling auto-merge while admission checks are pending, or by enqueueing an eligible PR. Neither proves it landed. Thus SASE needs to distinguish “awaiting admission,” “queued,” and “merged.” `--match-head-commit` checks the expected PR head at submission; `--admin` can bypass the queue where permitted. [CLI contract](https://cli.github.com/manual/gh_pr_merge)

My recommendation is to reconcile persisted PR records using actual merge evidence, including `mergedAt` and `mergeCommit`, before resolving dependent work. Those fields are available through [`gh pr view`](https://cli.github.com/manual/gh_pr_view). Compare a candidate with its recorded landing commit or group endpoint: comparing against the **current** `master` tip can falsely fail after subsequent merges. Neither a queue-removal event nor a destroyed group alone proves failure; successful merges also produce those events. [GitHub event semantics](https://github.blog/changelog/2023-07-12-pull-request-merge-queue-is-now-generally-available/)

**Queue-green and release-ready remain separate**

Track the PR head, tested candidate, landed commit, and release SHA separately. The documentation reviewed does not establish a universal identity guarantee between candidate and landed SHAs across merge methods. Verify that relationship in the pilot; equal file trees alone do not prove identical commit identity or build inputs.

Even perfect queue validation proves only the configured checks. Keep the proposal’s exact-SHA release qualification: select the actual release commit, qualify it, and publish the same built files. A newer green `master`, or a green PR head, cannot substitute for that evidence.

**A small pilot is justified**

The feature is available to public organization repositories, including Free organizations; private organization repositories need Enterprise Cloud. [Availability](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/merging-a-pull-request-with-a-merge-queue)

Use a repository ruleset requiring PRs with zero approvals, the queue, and the aggregate check; keep routine writers off its bypass list. Requiring PRs does not itself require human review. [Rulesets](https://docs.github.com/en/enterprise-cloud@latest/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)

Before enforcement, demonstrate conflicting changes, failed checks, direct-push rejection, restart recovery, and candidate-to-landed SHA tracking. Measure wasted builds and false ejections. The supplied latency estimates are simulation results, not a GitHub service guarantee. These operational behaviors were researched from documentation, not exercised against a live queue.
