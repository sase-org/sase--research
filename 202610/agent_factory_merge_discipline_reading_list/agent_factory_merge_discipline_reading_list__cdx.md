**Merging in an agent software factory: recent evidence for integration protocols, reliable gates, and immutable releases**

Independent research by **cdx**, 2026-10-17. Reading window: **2025-10-18 through 2026-10-17**. All ten ranked readings below fall within it. Paper dates refer to initial arXiv submission unless stated otherwise; revisions and manuscript dates are distinguished. Research was conducted independently: no other report, transcript, or findings from this swarm were consulted.

The shared input was [Merge discipline for SASE: a merge-queue-fenced master and exact-SHA PyPI releases](merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md), read through the audited artifact reader. Its operational measurements are treated as supplied context, not independently reproduced in this investigation. This is a reading-led architectural analysis, not a fresh audit of SASE's implementation or GitHub settings.

My recommendation is to retain the proposal's native GitHub queue as the initial integration service, while putting more design attention into the contract between agent completion, verified landing, and release publication. The best recent material concerns that contract and its failure modes. It does not establish that SASE needs a bespoke merge scheduler, an LLM making admission decisions, or a different vendor immediately.

If you read only three pieces, choose the **CAID paper**, **Mergify's TLA+ case study**, and **the critique of code-based flaky-test detection**: numbers 1, 2, and 3 in the final ranking.

**Separate the responsibilities before choosing the mechanism.** The important distinction is between planning work, repairing code, ordering integration, and publishing packages. They can share a UI without sharing a decision-maker.

| Responsibility | Recommended SASE owner | Evidence it should produce |
| --- | --- | --- |
| Decompose work and recognize dependencies | Planner, informed by repository structure | Explicit dependency edges and task boundaries |
| Implement and repair conflicts | Authoring agent, or a bounded repair successor | A new candidate revision and its verification results |
| Admit integrated changes | Deterministic queue and server-enforced policy | Candidate identity, tested integration identity, required checks |
| Recognize durable landing | Recoverable host service | Proof connecting the candidate, landed commit, and target history |
| Qualify and publish a version | Release workflow | Exact source revision, package digests, qualification evidence, publication receipt |

This division is my synthesis. CAID supports explicit isolation and integration; Cursor's experience supplies a useful warning against making every merge wait for a separate integration agent. Neither source is a direct evaluation of GitHub's native queue against a SASE-style host service. [CAID](https://arxiv.org/html/2603.21489v2), [Cursor](https://cursor.com/blog/scaling-agents).

**The landing watcher deserves the rigor of a small distributed protocol.** Mergify's formal-methods article reports failures around freeze transitions and speculative promotion. Its webhook incident shows how stale fields in a valid event can undo previously correct state. Both apply even if GitHub owns the queue: SASE still owns the interpretation of remote outcomes and the release of dependent work. [Formal verification case study](https://mergify.com/blog/how-we-formally-verified-our-merge-queue-with-tla-plus), [webhook incident](https://mergify.com/blog/when-github-webhooks-lie-how-an-empty-array-broke-our-merge-queue).

My proposed invariants for that host layer are:

- A candidate is identified by repository, PR, head SHA, and an attempt or generation identifier. An old success cannot authorize a replacement head.
- Every accepted submission remains accounted for until a durable terminal outcome. A restart neither loses it nor creates another PR for it.
- Reprocessing a remote observation cannot duplicate task completion, dependent-agent launch, or publication.
- Failed, cancelled, expired, and missing checks are distinct from success. Any accepted skip has an explicit policy reason.
- A repair creates a new candidate generation and invalidates authorization tied to its predecessor.
- Receiving a webhook triggers reconciliation; it does not by itself prove that the currently requested revision landed.

A small bounded model should include crashes, duplicate observations, reordered observations, timeouts, and head replacement. Tests should deliberately break each invariant and demonstrate a failure. This is a focused application to the host-owned state machine, not a proposal to reimplement the provider's queue.

There is a subtle correction to the shared proposal's tree-equality check. Compare the tested integration tree with the **immutable landed integration commit for that merge group**, not the current moving tip of `master`. By the time a watcher polls, another valid landing may have advanced the branch. Separately verify that the recorded landed commit remains an ancestor of the current target. Preserve a group-to-candidate mapping when several PRs land together. This is a protocol deduction, not a guarantee of undocumented provider behavior; the pilot must establish the actual SHA mapping.

Tree equality also has limits: equal tracked files do not prove equal builds when version generation, commit metadata, tags, dependencies, or environment differ. The release path should retain the stricter exact-source-and-package contract.

**Treat flaky outcomes as execution evidence, not an exemption inferred from source code.** Recent work finds serious generalization limits in code-only flaky-test detectors. A separate Python study shows that known flaky tests often fail to reproduce on different hardware. Those findings argue for retaining runner, dependency, test-order, and execution evidence when deciding whether a failure can be retried or quarantined. [Detection limits](https://arxiv.org/abs/2607.09345), [Python Shaker evaluation](https://arxiv.org/abs/2609.25528).

One mathematical assumption in the supplied queue model needs explicit qualification. A 30% first-attempt failure probability does **not** establish a 9% two-attempt failure probability. In general:

`P(two failures) = P(first failure) × P(second failure | first failure)`

The 9% calculation additionally assumes the relevant retry probability remains 30%. Persistent runner trouble, test ordering, and environmental conditions can correlate failures. Measure that conditional rate on unchanged candidates, and model different retry environments separately. A serial rerun of one failed node changes the execution conditions; its pass is useful evidence, but does not establish that the original failure was harmless.

For SASE, I would preserve first-attempt outcomes, bound automatic retries, keep quarantined tests observable, and measure both escaped regressions and false rejections. An intermittent product race can produce flaky test outcomes while still deserving to block release. The target should be confidence in the gate's decision, not merely a high final green percentage.

**Optimize burst handling after observing it.** The shared proposal's roughly 43 daily arrivals do not alone determine whether batching is needed. Agent waves can produce concentrated arrivals even when average utilization is modest. Mergify's July report is unusually relevant: its own before/after daily merge counts were around SASE's scale, while adaptive batching addressed bursts. It explicitly did not demonstrate improved daily throughput. [Dynamic batching experience](https://mergify.com/blog/dynamic-merge-queue-batch-size).

I would therefore keep the simple initial queue, but add measurements of burst size, oldest-candidate age, retry amplification, runner occupancy, and recovery effort per failed batch. Consider batching only when those observations show a problem. A batching experiment should preserve required-check policy while making the reduced attribution and rollback granularity explicit. Do not interpret “lowering the quality bar” as permission to ignore failed checks.

Also distinguish three controls: concurrent speculative builds, combining changes into one CI execution, and landing several already-validated PRs together. GitHub documents that its merge limits do not combine `merge_group` builds. Increasing the merge-group landing limit is therefore not equivalent to Mergify's adaptive CI batching. [GitHub merge-queue documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue).

**Reduce conflicts before the landing stage.** The July agent-PR study distinguishes source-level structural conflicts from ordinary overlapping edits. It is a useful prompt to measure rename/delete/add contention and stale branch age, rather than focusing only on lockfiles. Its observed conflict rates are not forecasts for SASE. [Agent PR concurrency study](https://arxiv.org/html/2607.04697v1).

My practical inference is to assign ownership of shared interfaces during a task wave, group tightly coupled edits, and give repair agents both changes' intent. A clean textual merge proves little about whether independently changed interfaces still agree. Small coherent changes help, but splitting a coupled change into many independently admitted pieces can introduce intermediate broken states. Explicit dependencies or an atomic integration unit may be appropriate; the right unit is determined by validity, not a universal lines-per-PR target.

**Make the release object stronger than a source SHA.** The recent artifact-promotion case study offers a useful distinction between drawing a promotion boundary and actually enforcing its checks. Its implementation openly lacks several controls, which makes it a useful design review exercise rather than a template to copy. [Artifact Promotion Control Model](https://arxiv.org/html/2609.35891v1).

For SASE, I would define a release record containing the version, immutable source SHA, built wheel and sdist digests, qualification run identities, build configuration identity, and the resolved `sase-core-rs` dependency used in qualification. Install smokes should consume the built packages. Upload should consume the same files, followed by confirmation of the published digests. The sdist needs its own build/install validation; downstream builds from it cannot be promised to be byte-identical to a tested wheel.

This extends rather than replaces the supplied build-once recommendation. It also separates two questions: whether the release workflow produced a file, and whether that file passed the required tests. PyPI supports provenance attestations, but provenance alone does not assert functional correctness. Current [PyPI attestation documentation](https://docs.pypi.org/attestations/) is implementation reference material, not a dated entry in the reading ranking.

**Keep the guarantee precise.** A queue can prevent admission when its required checks fail. It cannot promise that no deterministic defect reaches `master`; untested behavior can still be wrong. GitHub's April incident also demonstrates that the integration service itself can construct an incorrect result. Retain independent landing evidence and a deliberate recovery procedure even when a hosted queue owns scheduling. [GitHub's incident account](https://github.blog/news-insights/company-news/an-update-on-github-availability/).

Two current developments qualify the source proposal without overturning its initial choice. Rust's January 13 report says its replacement Bors was already merging compiler PRs: describing that rewrite as merely ongoing is stale. Trunk's July 30 announcement describes atomic testing and landing of GitHub PR stacks. These make maintained custom systems and stack-oriented services concrete alternatives, but neither demonstrates a present need for SASE to adopt one. [Rust infrastructure report](https://blog.rust-lang.org/inside-rust/2026/01/13/infrastructure-team-q4-2025-recap-and-q1-2026-plan/), [Trunk stack support](https://www.trunk.io/blog/trunk-merge-queue-now-supports-github-stacked-pull-requests).

**How I selected the readings.** I prioritized primary research, operators describing their own failures, explicit experimental methods, and lessons that change a SASE design decision. The ranking balances relevance, evidential strength, and reading effort. The papers are preprints unless their entries say otherwise; arXiv hosting is not evidence of peer review. Vendor accounts are useful operational testimony, not independent product comparisons. I inspected relevant full-text methods and limitations for the ranked papers, and the first-party articles for the operational accounts.

Six additional recent candidates were screened but not ranked: the Rust and Trunk updates above; [AgenticFlict](https://arxiv.org/abs/2604.03551), which is useful dataset context but overlaps the conflict topic; [Understanding and Detecting Flaky Builds in GitHub Actions](https://arxiv.org/abs/2602.02307), an observational Java-project study; [Merge Queues Were Built for Humans. AI Agents Need More.](https://mergify.com/blog/merge-queues-and-ai-coding-agents), which adds less concrete evidence than the selected Mergify accounts; and [PyPI in 2025](https://blog.pypi.org/posts/2025-12-31-pypi-2025-in-review/), which is broader than the release question. AgenticFlict's PR-versus-base conflicts and the July paper's PR-versus-PR conflicts have different denominators and should not be combined.

The targeted queue-prioritization paper [Improving Merge Pipeline Throughput in Continuous Integration via Pull Request Prioritization](https://arxiv.org/abs/2508.08342) was first submitted August 11, 2025, outside the requested window. I excluded it rather than presenting an older paper as recent. Undated product documentation is likewise kept outside the ranking.

The Bob check queried all 16 recent article/paper candidates in one batch. Fifteen were absent from the reference index; one possible title match was inspected and proved to be a different Pragmatic Engineer article. Absence means “not found in the indexed library,” not “you have not read it.”

**Ranked articles and papers to consider reading**

1. **[Effective Strategies for Asynchronous Software Engineering Agents](https://arxiv.org/html/2603.21489v2)** — Jiayi Geng and Graham Neubig. **March 23, 2026; revised July 8.** Research preprint. Suggested reading: §§2–4 and limitations; about 25–35 minutes.

   The closest match to SASE's architectural question. CAID combines dependency-aware delegation, isolated worktrees, explicit integration, and author-owned conflict repair. Table 2 is more informative than the headline: on Commit0-Lite, Sonnet 4.5 rises from 53.1 to 59.1, but reported runtime rises from 692.6 to 1,583.2 seconds and cost from 1.9 to 8.1. The larger headline gains concern another model. PaperBench uses the Code-Dev protocol with an LLM judge, not full scientific reproduction.

   **Read for:** how dependency readiness and integration fit together. **Limit:** different aggregate execution budgets and higher cost; this does not establish a throughput improvement or prove a hosted queue design. My takeaway is to preserve the isolation/integration contract while measuring its coordination overhead.

2. **[How We Formally Verified Our Merge Queue with TLA+ (and Found Bugs That Tests Missed)](https://mergify.com/blog/how-we-formally-verified-our-merge-queue-with-tla-plus)** — Julien Danjou. **April 13, 2026.** First-party engineering account; 8 minutes.

   Reports bounded exploration of 468,000 states and two bugs, involving freeze handling and promotion of insufficiently prepared speculative entries. The most valuable warning is that some invariants initially passed vacuously because they referred to an unreachable state.

   **Read for:** a concrete way to review SASE's landing and completion transitions. **Limit:** this is a vendor's account of a bounded model; GitHub/git I/O and parallel queues were outside its model, and the author acknowledges specification drift. I did not independently inspect the implementation or reproduce TLC. Borrow the modeling discipline, including deliberate counterexamples, without treating the article as a proof of the complete service.

3. **[How Far Are We from Detecting Flaky Tests? On the Limits of Code-Based Detection](https://arxiv.org/html/2607.09345v1)** — Ömer Oktay Gültekin and colleagues. **July 10, 2026.** Research preprint, marked under review; about 25 minutes.

   Audits benchmark shortcuts and evaluations that mix projects. Code-based detectors that looked effective under published protocols fare much worse with project separation. In its 86-test E2E corpus, source plus logs supported a cause for only 42%; the remainder required additional execution evidence.

   **Read for:** deciding what evidence authorizes a flaky classification. **Limit:** the findings concern particular detectors and datasets, not every possible model-assisted diagnostic system. For SASE, use an agent to propose a diagnosis and reproduction strategy; let observed execution evidence and explicit policy determine admission.

4. **[Scaling long-running autonomous coding](https://cursor.com/blog/scaling-agents)** — Wilson Lin. **January 14, 2026.** First-party experimental account; 7 minutes.

   Describes failures of shared-file coordination and locks, then a planner/worker structure. Cursor also removed a dedicated integrator after it became a bottleneck, leaving workers responsible for conflicts.

   **Read for:** the strongest counterweight to adding another agent role whenever integration becomes painful. **Limit:** exploratory workloads, vendor reporting, and large code-volume anecdotes do not establish release correctness. Its shared-branch experiments are not evidence that SASE should remove its server fence. Keep the queue deterministic and dispatch reasoning-intensive repair only when needed.

5. **[When GitHub Webhooks Lie: How an Empty Array Broke Our Merge Queue](https://mergify.com/blog/when-github-webhooks-lie-how-an-empty-array-broke-our-merge-queue)** — Mehdi Abaakouk. **March 25, 2026.** Production incident account; 8 minutes.

   A reviewer-related webhook overwrote labels with an empty array, causing a queued PR to be ejected. The article explains action-aware updates and protection against superseded head-SHA observations.

   **Read for:** the implementation hazards behind “just watch the PR until it merges.” **Limit:** restricting updates by action is not a complete ordering or delivery guarantee. My extension for SASE is periodic authoritative reconciliation, durable candidate generations, and idempotent completion. Exercise event reordering and restarts before making dependent work trust the watcher.

6. **[How we made our merge queue lower its own quality bar (only when it's drowning)](https://mergify.com/blog/dynamic-merge-queue-batch-size)** — Julian Maurin. **July 6, 2026.** Operational experiment; 7 minutes.

   Uses batch sizes from one to two as backlog competes for five speculative-check slots. On one busy day, 74% of checks paired changes; a subsequent quiet day paired none. Crucially, weekday merges averaged 48.4 before and 45.3 after: the author does not claim higher daily throughput.

   **Read for:** a bounded response to bursty agent arrivals at a surprisingly relevant daily volume. **Limit:** a short observational window, no demonstrated reduction in escaped defects, and weaker per-change attribution. Adapt only if measured SASE bursts justify it; avoid adopting a vendor's tradeoff slogan as a general mathematical theorem.

7. **[The Artifact Promotion Control Model: An Implementation Case Study](https://arxiv.org/html/2609.35891v1)** — Vasili Gavrilov and Enkli Ylli. **ArXiv September 27, 2026; manuscript states first version June 3 and revision September 7.** Case-study preprint. Read §§11.7, 13, and 15 first; 15–25 minutes.

   Frames a release around the built object and enumerates which controls one AWS deployment system actually implements. Its explicit missing controls—such as no integrity verification at deployment and no signature/provenance check—are more valuable than its deployment-speed numbers.

   **Read for:** turning “publish the tested SHA” into a verifiable package handoff. **Limit:** one anonymized application, operator-authored evidence, and no measured build-on-target comparison. It is lower-confidence empirical evidence and not a security blueprint. The control table is the reusable idea.

8. **[AI Agent Pull Requests on GitHub: Frequency, Structure, and Merge Conflict Rates](https://arxiv.org/html/2607.04697v1)** — **July 6, 2026.** Empirical preprint; about 20 minutes.

   Studies 33,596 agent PRs and replays 716 evaluable co-active pairs. It reports textual conflicts in 119/601 same-platform pairs and 48/115 cross-platform pairs. Source files account for 84.4% of conflicted files; modify/delete and add/add together account for about 42% of conflict reports.

   **Read for:** designing conflict categories and task-boundary measurements. **Limit:** observational sampling, platform/repository confounding, and replayed branch heads rather than a controlled multi-agent deployment. The paper is recent, but its underlying PR corpus covers December 2024–July 2025. It measures textual conflicts, not semantic correctness or CI cost. Do not infer that choosing one model vendor halves SASE's conflict rate.

9. **[Evaluating Shaker for Flaky Test Detection in Python Projects](https://arxiv.org/html/2609.25528v1)** — Gabriela Leal, Denini Silva, and Leopoldo Teixeira. **September 22, 2026.** Empirical preprint; about 15 minutes.

   Tests 137 known flaky Python tests with a budget of 100 executions per technique; some runs truncate. Resource-contention injection detects 37.2%, versus 35.8% for ordinary reruns; the reported difference is not statistically significant. Many inherited flaky cases do not reproduce on the evaluation hardware.

   **Read for:** questioning whether local and hosted-CI flaky evidence transfers. **Limit:** non-order-dependent tests and a stress configuration inherited from another ecosystem; the result does not establish that targeted stress testing is useless. Preserve environmental provenance when comparing SASE's host and CI outcomes.

10. **[An update on GitHub availability](https://github.blog/news-insights/company-news/an-update-on-github-availability/)** — Vlad Fedorov. **April 28, 2026.** First-party incident and reliability account; 6 minutes.

    GitHub reports that April 23 multi-PR squash merge groups produced incorrect results that reverted earlier changes, affecting 658 repositories and 2,092 PRs. This account says merge and rebase methods were unaffected. It is an incident-specific statement, not an enduring safety guarantee for either method.

    **Read for:** grounding the proposal's provider-risk discussion in primary evidence. **Limit:** a summary rather than a full reproducible fault analysis, and already partly covered by the shared input, so its marginal reading value is lower. Keep a record of what was tested and what landed, and rehearse recovery without assuming a provider's green status proves correct integration.

Library check: 0 of 16 candidates already in your library (0 finished).
