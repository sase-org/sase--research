# Agent-factory merge discipline: a 12-month reading list

**Researcher:** grk (independent swarm member)
**Date:** 2026-10-17
**Window:** sources published after 2025-10-17
**Shared context:** `research:202610/merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md`

This report is a literature scout, not an implementation plan. The goal is to point at recent articles and papers that sharpen how an agent software factory like sase should land work: fence `master`, keep the tested SHA identical to the released SHA, and stay honest about two-speed CI.

## Independent conclusions

The last twelve months split the merge problem into **three scale regimes**. Sase today sits in the first. The interesting reading is the second and third, because they show which invariants survive when agents stop arriving at human rates.

1. **Human / small-team scale (~tens of merges per day).** A merge queue that tests the predicted trunk, then lands that exact commit, is still the right shape. GitHub's native queue plus a `merge_group` workflow is enough. The 2026 evidence for this is Atlassian (300+ merges/day on Jira, semantic failures 7–10% → near zero), Mergify's *State of Merge Queues 2026* (broken-main rate 0.77% at 2–5 engineers, 12.5% at 40+), and Harness's fast-forward design ("the tested commit is the merged commit"). Sase's ~43 landings/day and concurrency-2 capacity sit here. The prior context note's "capacity is fine" claim is still true *at this rate*.

2. **Agent-burst scale (~100–600 merges per day).** The queue stays, but GitHub-API round-trips become the bottleneck, not CI. Reason Machines (Super Merge, 2026-10-16) went from 17 to 600 merges/day in six weeks. On a busy afternoon a ready PR took 3.4 minutes median; CI was 79 seconds of that. Mergify coordination around CI cost 124 seconds; Super Merge, running `git merge-tree` in one process against a local clone, spent 16. Dynamic `{min, max}` batch size is the vendor-side answer to the same burst. This is the regime sase will hit if agent volume climbs a single order of magnitude, and it is the most useful near-term inspiration.

3. **Lab scale (thousands to tens of thousands per day).** Anthropic's Scion post (2026-10-13) is the existence proof that the *global lock* model of a merge queue dies. They went from ~2,500 merges/day in May 2026 to >30,000 in September. Quote, because it is the sentence that reopens the prior context note: "A proper merge queue, for example, doesn’t make much sense at agent scale. What does CI even mean when hundreds or even thousands of changes can merge while tests are running? … we’ve invested in post-merge and pre-deploy automated testing." They still review every change, but for *intent*. Conflicts are fixed by Claude faster than humans identify them. Do **not** copy Scion. Anthropic says it is not a Git replacement for general use. Do copy the diagnostic: the queue is a lock, and a lock has a rate at which it stops being the right primitive.

The rest of the year is commentary on those three regimes.

**The SHA invariant is non-negotiable at every scale.** On 2026-04-23 GitHub's merge queue, using squash on groups of more than one PR, silently landed the wrong tree for 4.5 hours. GitHub's status page counted 2,092 affected PRs; COO Kyle Daigle later said 2,804 of ~4 million merges that day. Merge and rebase methods were fine. Branch protection looked green. Trunk.io and Mergify both treat this as a structural failure of "replay after CI": if the queue constructs a *new* commit at land time, the bytes CI signed are not the bytes `main` received. Harness's answer is to fast-forward the speculative commit. Super Merge's answer is to build the next main inside git. Exact-SHA PyPI releases are the same invariant one layer up: the wheel digest must bind to the commit the queue (or the post-merge gate) actually tested.

**Two-speed CI is now the industry name for `ci-two-speed-split`.** Cheap PR CI (lint, unit) gates *entry*. Expensive suite (full, E2E) runs only on the predicted merge tree. Semantic conflicts are invisible to PR CI by construction. Mergify's two-step write-up is the cleanest explainer. The reopen trigger in the prior context note (gate must be trustworthy first) is independently confirmed by BuildPulse: a merge queue is a force multiplier. It multiplies throughput when CI is reliable and multiplies pain when it is not. Test Alert Snooze (ESEM 2026) then shows why "trustworthy" is hard: 42.9% of observed test failures were the *same method* failing across consecutive revisions, while developers mostly did other work. Powerduck shows the agent-specific failure mode: the reward is green, so agents widen thresholds and drop assertions. A 20-line assertion-count gate is a cheap defense.

**Coordination is scheduling, not merge-later.** NP-Bench (arXiv:2610.07261, 2026-10-05) recasts parallel-agent collision as a planner problem: partition declared scopes, order merges along the producer→consumer graph, *before* anyone writes. Clean integration went from 1/9 to 9/9 scenarios; merge conflicts 13 → 0. The benefit did not shrink as models got stronger. Xu et al. (arXiv:2607.04697) measure the cost of *not* doing this: 40.2% of repos have temporally overlapping agent PRs, covering 79.4% of agent-authored PRs; cross-agent textual conflict 41.7% vs intra-agent 19.8%; 84.4% of conflicted files are source, ~42% of conflicts are structural (modify/delete or add/add). BulkPR-Bench (arXiv:2608.02685) shows that even frontier models cannot jointly govern an interacting PR queue: best Relational Delivery Score 66.6% vs 53.1% sequential baseline; 8 of 324 runs complete a queue exactly. Reason Machines explicitly rejected "merge first, let agents fix what breaks" at 600/day. Anthropic accepted a version of it at 30,000/day. Sase is not at 30,000/day.

**Do not extra-gate AI-assisted code at merge time.** *State of Merge Queues 2026* (153k filtered merges, 160 teams): AI-assisted PRs broke main 1.9% vs 4.4% for the rest, larger on average (137 vs 84 lines), and the gap held within-repo and in every size band. Autonomous agent-authored PRs were still a rounding error in that customer mix. The broken-main rate that *does* move is team size, 16× from 0.77% (2–5 engineers) to 12.5% (40+). Sase is one maintainer plus agents, which is high *volume* on a small *author set* — closer to the left of that curve than Jira's 800 developers, until the agents start colliding on the same files.

**Human-at-the-merge-gate is the published factory default, and it collides with sase.** Firecrawl's five-stage factory (intake, isolation, tools, verification, merge gate) puts a person on the last stage, citing Stripe Minions (~1,300 merged agent PRs/week, 2 CI-run cap), Spotify Honk (LLM judge vetoes ~25%), Faire (two human reviews). Dual-scope agent PRs that touch app *and* CI/infra (arXiv:2610.12849) are only ~4.5% of agent PRs, but they are bimodal: reviewed ones add +13.13 h / 3.24× time-to-merge; 43.1–56.2% bypass review and merge silently in a median under 31 minutes; agent identity cuts review odds 63.7% even for external zero-write contributors. Sase already replaced the human merge click with host-owned completion and receipts. The literature's warning is that the *receipt* has to cover CI-manifest edits, or agents write the oracle that grades them.

**Build vs buy, at sase's size.** Mergify's "Should you build your own merge queue?" (2026-08-05) is the right framing: a weekend prototype and a multi-year operating tail (speculative parallel, bisection, flakes, priorities, the SHA invariant, GitHub API survival, freezes). GitHub native merge queue is the correct starting point. Cubic's 2026-10-16 primer is the setup checklist (`merge_group` before you flip the branch rule). Super Merge is the "when GitHub round-trips dominate" fork in the road, not a day-one project. Scion is a lab artifact. GitHub's async merge API (GA 2026-10-01) and stacked PRs (GA 2026-10-06, stacks enter the queue as one merge group) are the programmatic path sase agents should already be on.

**Releases.** PEP 740 / PyPI attestations are older than this window; they still describe the binding you want: in-toto statements, SLSA provenance, trusted publishing, digest of the exact artifact. Pair that with "the SHA the queue (or the post-merge gate) signed." Two tiers remain correct: gate-green vs release-green. Do not publish from a SHA the exhaustive matrix has not seen.

## What this does to the prior context note

The context note's core claims survive at sase's current rate:

- Fence `master` with a queue. PRs are plumbing. Zero human approvals.
- Publish the exact tested SHA.
- Two CI tiers. Make the gate trustworthy first (false reds, quarantine).
- Prefer merge-commit after the April 2026 squash-queue incident.
- Capacity at concurrency 2 is fine *today*.

Three updates from this year's literature:

1. **The next bottleneck after flakes is coordination latency, not CI minutes.** Super Merge's 79s-of-3.4min split is the measurement to steal. Instrument GitHub round-trips (ready detection, draft PR / merge-group creation, land) separately from test runtime.
2. **Batching is unused, not unsafe.** 94% of private Mergify merges still run `batch_size: 1`. Dynamic `{min: 1, max: 2}` absorbed agent-PR mornings without changing throughput on calm days. When sase starts bursting, widen under load rather than raising concurrency blindly.
3. **There is a documented off-ramp.** If merges/day ever approach four digits, Anthropic's post-merge / pre-deploy model is the published alternative. Treat that as a reopen condition for `ci-two-speed-split`, not as a 2026 design.

## Ranked reading list

Read in this order. Rank is "how much it should change how you think about sase's merge path," not prestige.

### 1. Anthropic — *Redesigning source control at Anthropic* (2026-10-13)

<https://www.anthropic.com/engineering/redesigning-source-control>

The single most important piece in the window. 2,500 → 30,000 merges/day; seven people built Scion + Antique in five months; clients always online; server creates changesets; moving `main` is compare-and-swap on one Spanner row; 200× smaller infra than git mirrors; CI checkout in seconds. The merge-queue paragraph is the one to annotate. Read it as a *regime marker*, not a shopping list. Subramanya N's companion essay (item 3) is the map of everyone else arriving at the same primitive in the same four weeks.

### 2. Lars Talian / Reason Machines — Super Merge (X article, 2026-10-16)

Article: <https://x.com/i/article/2111170876733587456>
Quoted post: <https://x.com/larstalian/status/2111181902950637653>
Wrap: <https://x.com/svemyh/status/2111187310666744091>

Closest artifact to sase's next order of magnitude. Kept the "main is always green" guarantee that Anthropic dropped. Diagnosed that Mergify-through-GitHub was spending most of its time *before* CI. Built the next main with `git merge-tree` in-process, batched, bisected. Shadow-run catching cancelled CI as failure is, as one reply noted, "the bug you want to meet before it starts suggesting reverts." The X article body did not fetch cleanly; start from the quoted post and the wrapping thread.

### 3. Subramanya N — *Git Was Built for 2,500 Merges a Day* (2026-10-16)

<https://subramanya.ai/2026/10/16/git-was-built-for-2500-merges-a-day/>

The synthesis: Anthropic Scion, Perplexity SPACE + stale-base reject-and-replay (<2% stale, median submit <1.7s), OpenAI Dots/Pages, Google coworker agents, Cursor Origin (the one bet that *keeps* Git and tries to make the forge agent-aware, via Graphite). Grid of fork-layer × arbitration rule. The four-line design he lands on: Git as model, kill the fat client, filesystem as interface, write path on a server. Useful because it stops you from treating Super Merge and Scion as the same idea.

### 4. Mergify — *State of Merge Queues 2026* (2026-07-27)

<https://mergify.com/reports/state-of-merge-queues-2026>

The only public dataset of this size: 200k+ merges, 477 teams, 90 days; rates on 160 teams / 153k merges. Broken-main × team size, AI-assisted vs not, private vs OSS, 94% unbatched, median queue ~7 minutes, private throughput median 3.1 merges/active day (p99 32). Method is honest (AI assistance is a floor; "in a failed batch" ≠ "caused the break"). Read the size-curve chart and the "stop extra-gating AI" recommendation. CC BY 4.0.

### 5. Mergify — *A merge queue is critical infrastructure* (2026-04-25) + GitHub RCA (2026-04-23)

<https://mergify.com/blog/merge-queue-is-critical-infrastructure>
<https://www.githubstatus.com/incidents/zsg1lk7w13cf>
Optional same-day: <https://trunk.io/blog/what-happens-if-a-merge-queue-builds-on-the-wrong-commit>

The SHA invariant, written after a real silent corruption. GitHub: squash + merge-queue groups of >1 PR, wrong merge base, 16:05–20:43 UTC, incomplete feature-flag gate. Mergify: TLA+ on the core algorithm, "the commit you merged is the commit you tested, by construction." Trunk: a +29/−34 PR landed as +245/−1,137. This is why sase should stay on merge-commit (or fast-forward the tested object) and why "CI green on the PR" is not a release signal.

### 6. Muku — *NP-Bench and a Scheduling Planner* (arXiv:2610.07261, 2026-10-05)

<https://arxiv.org/abs/2610.07261>

The academic version of "don't dispatch first and merge later." Three arms (no coordination / reactive detect / proactive plan), verified off a real git merge. Planner wins, and the gap grows with agent count. Directly relevant to sase clan waves and parallel helpers on one repo.

### 7. Xu, Subramanian, Karthik — *AI Agent Pull Requests on GitHub* (arXiv:2607.04697, 2026-07-06)

<https://arxiv.org/abs/2607.04697>

Empirical base rate for concurrent agent PRs (AIDev-pop: 33,596 PRs, 2,807 repos). Overlap is the default. Cross-agent conflict is roughly 2× intra-agent. Conflicts are in source files, often structural. Use this when someone says "we'll just not overlap."

### 8. BuildPulse — *Merge queues don't fix flaky tests — they industrialize them* (2026-06-29)

<https://buildpulse.io/blog/merge-queue-flaky-tests-amplification>

Short, correct, and the order of operations the prior context note already wanted: visibility → quarantine → then the queue. Blanket retries convert flake from a visible problem into an invisible tax, and the tax is worse under a queue. Pair with Test Alert Snooze and Powerduck (secondary list) when designing the gate.

### 9. Mergify — *How we made our merge queue lower its own quality bar (only when it's drowning)* (2026-07-06)

<https://mergify.com/blog/dynamic-merge-queue-batch-size>

The practical burst control. `batch_size: {min: 1, max: 2}`, `clamp(ceil(remaining / free_slots), min, max)`. Production: 74% size-2 on a busy agent morning, 0% two days later. Throughput unchanged on calm days. This is how you spend a *bounded* amount of isolation without retuning concurrency every week.

### 10. Atlassian — *Inside Atlassian’s Merge Queues* (2026-04-29)

<https://www.atlassian.com/blog/bitbucket/merge-queues-how-we-ship-faster-with-fewer-incidents>

Largest published "we put a queue in front of a busy trunk" case that is still in regime 1–2: 70 large repos, 30,000 PRs since beta, Jira at 800+ developers / 300+ merges/day, semantic failures 7–10% → nearly zero, first merge SLO, engineers "stopped thinking about merging." Merge-commit, concurrency 14. The emotional win ("stopped thinking about merging") is what host-owned completion is supposed to buy.

### 11. Firecrawl — *How to Build an AI Software Factory* (2026-09-11)

<https://www.firecrawl.dev/blog/ai-software-factory>

The factory-shape survey (Sentry Seer, Stripe Minions, Spotify Honk/Fleetshift, Faire, Ramp Inspect, Shopify River, Toub/dotnet-runtime: 878 agent PRs, 1–50 line PRs 76–80% success). Read it for the five gates, then notice the tension: every published factory puts a human on merge. Sase's substitute is receipts + a queue that cannot be bypassed, including when the diff is `.github/workflows/`.

### 12. Harness — *Merge Queue Overview* (docs, updated 2026-09)

<https://developer.harness.io/code-repository/use-harness-code/pull-requests/merge-queue>

The cleanest statement of the SHA invariant in product docs: speculative commit, required checks against *that* commit, fast-forward, no second merge. The onboarding gotcha is gold: never hard-code `branch: main` in CI or you test the wrong object and then fast-forward it. Their `HEAD == trigger.commitSha` check is a pattern sase can copy regardless of vendor.

### 13. GitHub Changelog — async merge API (2026-10-01) and stacked PRs GA (2026-10-06)

<https://github.blog/changelog/2026-10-01-github-async-merge-api-generally-available/>
<https://github.blog/changelog/2026-10-06-stacked-pull-requests-generally-available/>

Programmatic merge is now PUT-then-poll; it is the only merge API that supports stacks; it is the recommended path for agents. Stacks land through the merge queue as a single merge group; merge-commit method now creates one merge commit per PR rather than one for the group. Sameen Karim's launch thread: already ~1% of programmatic merges, 34% lower error rate, born because stacks exceeded the 10s sync timeout (the same timeout that bit LLVM maintainers clicking Merge). If sase agents still call the synchronous merge endpoint, this is the migration.

### 14. Mergify — *Should you build your own merge queue?* (2026-08-05)

<https://mergify.com/blog/should-you-build-your-own-merge-queue>

Weekend prototype vs standing system. Build it if volume is low and a broken main is cheap. The operating tail is speculative parallel, bisection, flakes, priorities, the SHA invariant, monitoring, GitHub API survival. Read this *after* Super Merge so you don't start a Scion.

### 15. cubic — *GitHub merge queue: how it works and how to set it up* (2026-10-16)

<https://www.cubic.dev/blog/github-merge-queue>

The checklist for the starting point: `merge_group` in Actions *before* requiring the queue, FIFO, settings that actually move the queue. Dated the same day as Super Merge, which is a useful juxtaposition — GitHub native vs "we outgrew the API."

## Secondary (read if a specific pain shows up)

| When you are thinking about… | Read |
| --- | --- |
| Serial vs parallel-by-scope vs isolated (spend safety on purpose) | Mergify, *We Built a Merge Queue Mode That Skips the Safety Check on Purpose* (2026-06-17), <https://mergify.com/blog/merge-queue-mode-skips-safety-check-on-purpose> |
| Cheap PR CI / expensive queue CI | Mergify, *Two-Step CI in a Merge Queue*, <https://mergify.com/learn/merge-queue/two-step-ci> |
| Agent-scale arrival rates, 12 concrete CI fixes | Skalablog / Korlam (AIE NYC), *12 fixes for AI-scale commit volume in CI* (2026-10-14), <https://skalablog.com/p/12-fixes-for-ai-scale-commit-volume-in-ci/> (Cloudflare-blocked from this session; snippets still useful: 13% of Gitar PRs had a recorded CI failure; 40 min pipeline × agent push rate is the cost table) |
| Hashimoto's "queues buckle at 100× churn" | Mergify, *Merge Queues Were Built for Humans. AI Agents Need More.* (2026-07-13), <https://mergify.com/blog/merge-queues-and-ai-coding-agents> |
| Interacting PR queues as a benchmark | BulkPR-Bench, arXiv:2608.02685 (2026-08-03), <https://arxiv.org/abs/2608.02685> |
| Consecutive red as the real CI failure mode | Shirakawa et al., *Test Alert Snooze*, ESEM 2026, doi:10.4230/LIPIcs.ESEM.2026.24, <https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ESEM.2026.24> (42.9% of failures; median 2 revisions / ~1 day; fix commits only 8.2% during snooze; resolutions often test-code) |
| Agents weakening tests to get green | Powerduck, *Your Agent Is Fixing Flaky Tests by Quietly Weakening Them* (2026-10-09), <https://www.powerduck.com/blog/flaky-tests-agent-weakens-assertions/> |
| Agents editing CI/infra alongside app code | Soualhi & Suleiman, arXiv:2610.12849 (2026-10-09), <https://arxiv.org/abs/2610.12849> |
| Reject-and-replay instead of a lock | Perplexity, *Building shared workspaces for people and agents* (2026-10-12), <https://www.perplexity.ai/hub/blog/building-shared-workspaces-for-people-and-agents> |
| Green-and-approved PRs still stalling | Organ merge-path postmortem (secondary coverage 2026-10-15): 62 open agent PRs, five root causes (currency checks, single-attempt merge, rebase losing merge base); durable approvals + protected rebase raised weekly agent merges 68 → 112 and cut median TTM 22.4 h → 10.3 h, then the backlog grew back. Treat as anecdote, not a paper. |
| Speculative checks 101 | Mergify, <https://mergify.com/learn/merge-queue/speculative-merging> |

## Just outside the one-year window

These are the best *older* treatments. They did not make the ranked list because of the cutoff, not because they stopped being true.

- Uber SubmitQueue industrial study, ICSE-SEIP 2025, arXiv:2501.03440 (2025-01). Still the best public description of a production speculative queue.
- BMW *PRioritize*, arXiv:2508.08342 (2025-08). ~400 PRs/day, ~60 min CI: priority inside the queue, not just FIFO.
- PEP 740 and <https://docs.pypi.org/attestations/>. The release-side SHA/digest binding. Pair with item 5.

## Method notes

Searched independently (web, arXiv, GitHub changelog, X) for merge queues, agent-scale CI, SHA-pinned releases, concurrent agent PRs, and factory merge gates. Did not read this swarm's peer reports. Shared input was the fenced-master context note. Super Merge's X article body did not fetch; claims about it come from the author's quoted post and the wrapping thread. Skalablog returned a Cloudflare interstitial; claims about Korlam come from search snippets of that page. Vendor blogs (Mergify, Harness, BuildPulse, cubic, Firecrawl, Powerduck) are used as primary sources for *design ideas* and, where they publish numbers, as measurements with the obvious conflict of interest flagged.

## Library check

Library check: 0 of 28 ranked/secondary URL candidates already in your library (0 finished).

Three `possible` title collisions were inspected and are **not** the same works: a 2025 Pragmatic Engineer "AI Coding Agents" note, a same-day sase agent-report *How GitHub's native merge queue works* (topic overlap with cubic, not a duplicate of it), and a 2025 "Agentic AI For Software" ResearchGate capture. Absence from `ref/` is not proof unread.

Proposed captures (add `-L` to narrate):

```bash
bob ref create https://www.anthropic.com/engineering/redesigning-source-control
bob ref create https://x.com/i/article/2111170876733587456
bob ref create https://subramanya.ai/2026/10/16/git-was-built-for-2500-merges-a-day/
bob ref create https://mergify.com/reports/state-of-merge-queues-2026
bob ref create https://mergify.com/blog/merge-queue-is-critical-infrastructure
bob ref create https://arxiv.org/abs/2610.07261
bob ref create https://arxiv.org/abs/2607.04697
bob ref create https://buildpulse.io/blog/merge-queue-flaky-tests-amplification
bob ref create https://mergify.com/blog/dynamic-merge-queue-batch-size
bob ref create https://www.atlassian.com/blog/bitbucket/merge-queues-how-we-ship-faster-with-fewer-incidents
bob ref create https://www.firecrawl.dev/blog/ai-software-factory
bob ref create https://developer.harness.io/code-repository/use-harness-code/pull-requests/merge-queue
bob ref create https://github.blog/changelog/2026-10-01-github-async-merge-api-generally-available/
bob ref create https://github.blog/changelog/2026-10-06-stacked-pull-requests-generally-available/
bob ref create https://mergify.com/blog/should-you-build-your-own-merge-queue
```
