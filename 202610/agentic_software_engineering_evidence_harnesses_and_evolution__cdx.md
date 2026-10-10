# Agentic software engineering: recent evidence on harnesses, coordination, and sustained code quality

Researcher: cdx  
Research date: 2026-10-10  
Eligible first-publication window: 2025-10-10 through 2026-10-10, inclusive  
Deliverable: independent reading recommendations for Bryan; research papers and engineering essays

The most useful next reading concerns how to test the surrounding agent system, preserve code quality through successive changes, and coordinate concurrent work. Those subjects add more to your recent reading than another broad introduction to agents. The ranked list at the end prioritizes new empirical work, then practical essays that explain how to apply it.

## Scope and selection method

I searched for recent primary research and firsthand engineering accounts across arXiv, conference proceedings, Anthropic Engineering, Simon Willison's writing, METR, and researchers' own sites. Secondary coverage helped locate original papers but supplies none of the technical conclusions here. I verified publication dates on original sources; an updated page or a 2026 conference appearance alone does not make an older article eligible. Every ranked item was first published inside the window.

This is a curated search, not an exhaustive systematic review. Ranking is a judgment about incremental value for you, using relevance to SASE, quality of evidence and controls, actionable design implications, and recency. I read abstracts, methods/results, and relevant limitations for the leading papers, and the engineering essays; I did not independently reproduce experiments or exhaustively audit appendices. Recent preprints are identified as such. No peer report, peer transcript, or peer summary from this swarm was consulted.

Your finished external references show substantial existing coverage of harness architecture, long-horizon orchestration, and agent memory. Your annotations on the long-horizon architecture paper also emphasize delegation evidence and recovery checkpoints. I used those as preference signals, not as evidence that other articles have been read.

## Independent conclusions

**Evaluate components under the model and budget you actually deploy.** The September harness ablation study is especially valuable because it holds the execution loop fixed and varies components. My inference is that SASE should periodically retest planning, tools, and context policies rather than accumulate them indefinitely. It provides experiments worth adapting, rather than a universal architecture prescription. [Harness component study](https://arxiv.org/html/2609.20804v1).

**Make successive changes part of evaluation.** SlopCodeBench preserves agents' earlier implementations; SWE-Milestone reconstructs dependent development goals from repository histories. Together they expose failure modes hidden by repeatedly restarting from a clean, human-written base. My recommendation is to assess regressions, future extension difficulty, and code structure alongside current test results. This is a proposed local evaluation approach, not an experimentally proven remedy. [SlopCodeBench v2](https://arxiv.org/html/2603.24755v2), [SWE-Milestone v4](https://arxiv.org/html/2603.13428v4).

**Coordination is a mechanism that needs controls and accounting.** PASC offers evidence that observable peer actions can help; CooperBench shows that communication and cooperation can fail. These results concern different workloads and coordination systems, so they should not be treated as a contradiction or averaged into a general claim about swarms. Evaluate coordinated teams against both an uncoordinated team and a single agent, including total cost. [PASC](https://drops.dagstuhl.de/storage/00lipics/lipics-vol394-esem2026/LIPIcs.ESEM.2026.18/LIPIcs.ESEM.2026.18.pdf), [CooperBench](https://arxiv.org/html/2601.13295v2).

**A repository instruction file can enforce useful conventions without improving benchmark resolution.** The AGENTS.md study distinguishes following instructions from solving tasks. Its Python issue-resolution experiments do not measure all the governance, safety, or workflow reasons to have instructions. My inference is to retain necessary constraints and test additional explanatory material for incremental value. [Evaluating AGENTS.md v3](https://arxiv.org/html/2602.11988v3).

**Measure delivery and review effort, and separate environment failures from agent failures.** The firm-level production paper and infrastructure-noise essay address different measurement problems. Neither permits a universal estimate of agent productivity. They suggest tracking human review, accepted outcomes, and execution conditions as part of SASE's evaluation record. [Software production bottlenecks](https://fion.ac/jellyfish.pdf), [Infrastructure noise](https://www.anthropic.com/engineering/infrastructure-noise).

## Reading-library audit

I submitted all 24 article identities in one call to bob ref find, using URLs/arXiv IDs and titles: 48 lookup queries, not 48 distinct articles. I confirmed the seven possible title matches with bob ref show. Two were unrelated false positives: the harness-component study matched a different refactoring paper, and the routing paper matched a different Pragmatic Engineer article. They were not counted as duplicates. The routing paper has since changed title; its unchanged arXiv identity was checked.

Eight distinct candidates are already in the library: four finished and four queued. The other sixteen were not found by identity; that means absent from the indexed reference library, not proof that you have never read them. The lookup reported intake as not checked, so I cannot exclude unscanned captures. Bob was used read-only throughout.

### Finished candidates excluded from recommendations

| Article | Library evidence |
| --- | --- |
| [Harness Engineering: Anatomy, Architecture, and Evolution of Coding Agents — A Source-Code Study of Eleven Systems](https://arxiv.org/abs/2609.00006) | Finished; ref/papers/harness_engineering.md. |
| [Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/) | Finished; ref/blogs/harness_engineering.md. A superseded legacy queued duplicate does not override the finished capture. |
| [An Architecture for Long-Horizon Agents: Levels, Ticks and Cascaded Intelligence](https://arxiv.org/abs/2609.19519) | Finished; ref/papers/an_architecture_for_long_horizon_agents_levels.md. |
| [An open-source spec for Codex orchestration: Symphony](https://openai.com/index/open-source-codex-orchestration-symphony/) | Finished; ref/blogs/open_source_codex_orchestration_symphony.md. |

### Eligible candidates outside the final twelve

These eight, together with the four finished exclusions and twelve ranked items, account for all 24 checked article identities. Unqualified dates below are first publication dates.

| Candidate | Date and library status | Why it missed the final twelve |
| --- | --- | --- |
| [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | 2025-11-26; already in your library, queued since 2026-03-15, legacy backlog. | Useful initializer/incremental-worker design; the March follow-up offers more incremental value given your orchestration reading. |
| [Scaling Managed Agents: Decoupling the brain from the hands](https://www.anthropic.com/engineering/managed-agents) | 2026-04-08; already in your library, queued since 2026-04-17, legacy backlog. | Strong architecture account, but overlaps your recent durable-state and recovery interests more than the controlled experiments do. |
| [Building a C compiler with a team of parallel Claudes](https://www.anthropic.com/engineering/building-c-compiler) | 2026-02-05; not found. | Concrete agent-team case study; weaker comparative evidence than PASC and CooperBench. Read for testing and work partitioning, not a general productivity estimate. |
| [We are Changing our Developer Productivity Experiment Design](https://metr.org/blog/2026-02-24-uplift-update/) | 2026-02-24; not found. | Valuable measurement caution: participant/task selection and concurrent work impair the follow-up experiment. It does not establish a reliable current speedup percentage. |
| [Claim Plane: Reliability Gains and the Limits of Selective Concurrency for Parallel Coding Agents](https://arxiv.org/abs/2608.00947) | 2026-08-02; not found; preprint. | Relevant to deterministic admission. Reliability gains largely came from serialization; only 30 pairs, oracle-localized context, and physically sequential API calls. No demonstrated wall-clock parallel speedup. |
| [Harness Tokenomics: A Router for the Enterprise Agentic Control Plane](https://arxiv.org/abs/2609.28919) | 2026-09-24; revised 2026-09-26; not found; preprint. | Interesting cache-aware routing. Enterprise savings are simulated and tied to a dated price sheet; lower priority than correctness and maintenance. Former title: Control the Harness, Control the Cost. |
| [Methodological Harness in Agentic Software Engineering: An Empirical Study on Mining Software Repositories](https://arxiv.org/abs/2609.32014) | 2026-09-25; not found; preprint. | Broad artifact-adoption evidence, but observing mechanisms in repositories does not establish that they improve outcomes. |
| [How we built Claude Code auto mode: a safer way to skip permissions](https://www.anthropic.com/engineering/claude-code-auto-mode) | 2026-03-25; not found. | Practical authorization-classifier design with disclosed errors. A useful specialist read for gates; vendor-collected evaluation and residual misses limit security conclusions. |

Frequently cited introductions published in September 2025, including Effective context engineering for AI agents, fall outside the requested window and were filtered before the 24-candidate audit.

## Ranked articles to consider reading

1. **[An Empirical Study of Harness Design for Coding Agents](https://arxiv.org/abs/2609.20804)** — Run-Ze Fan et al.; **2026-09-17**, preprint. **Library: not found.**

   Best next read after the eleven-system architecture study you finished. Across four models and 176 settings, it tests planning, action interfaces, and context management. Elision before summarization is efficient; recoverable elision is rarely used; component benefits depend on capability and context budget. The main value is an experimental method for choosing SASE mechanisms.

   **Limit:** one run per task/setting, limited model families, and a bundled action-interface intervention; it does not isolate tool count alone. Read the component definitions and limitations before generalizing. [Full text](https://arxiv.org/html/2609.20804v1).

2. **[SlopCodeBench: Benchmarking How Coding Agents Degrade Over Long-Horizon Iterative Tasks](https://arxiv.org/abs/2603.24755)** — Gabriel Orlanski et al.; **2026-03-25**, revised **2026-05-07**, preprint. **Library: not found.**

   Strongest challenge to judging an agent only by its latest passing tests. Version 2 has 36 problems and 196 checkpoints, evaluates 15 agents, and reports a best checkpoint pass rate of 14.8%, with no complete problem solved. It also tracks redundant code and concentrated complexity as agents extend their own work.

   **Limit:** those structural measures are proxies, and comparisons with existing human repositories are not randomized comparisons on identical tasks. Older summaries report smaller datasets and different numbers; use v2. Focus on trajectory metrics and the quality-prompt intervention. [Full text](https://arxiv.org/html/2603.24755v2).

3. **[Coordinating Agents on a Shared Git Workspace: An Empirical Study of Action-Space Observation for Agentic Software Engineering](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ESEM.2026.18)** — Hasen Özaytürk and Feza Buzluca; **2026-10-05**, ESEM 2026 conference paper. **Library: not found.**

   Fresh, directly relevant evidence for coordination through commits, lifecycle changes, and test/error observations. PASC tests two homogeneous agents on 266 Python SWE-Bench Pro instances, with two models and three runs per configuration. Resolution improves over a single agent; cost per resolved task improves over a silent two-agent baseline.

   **Limit:** the single-agent baseline remains cheaper per pass. Larger-team observations show increased interference; this is not evidence for unrestricted swarm scaling. Read the cost table and validity discussion, not just the abstract's savings claim. [Paper](https://drops.dagstuhl.de/storage/00lipics/lipics-vol394-esem2026/LIPIcs.ESEM.2026.18/LIPIcs.ESEM.2026.18.pdf).

4. **[Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?](https://arxiv.org/abs/2602.11988)** — Thibaud Gloaguen et al.; **2026-02-12**, revised **2026-09-29**, preprint. **Library: not found.**

   An unusually relevant empirical check on persistent instructions. Its latest version compares generated and developer context with no-context conditions, including 138 CTXbench tasks. Context generally fails to improve resolution while increasing inference cost by over 20% on average; agents nevertheless follow the instructions.

   **Limit:** Python issue resolution is the evaluated outcome. Security, policy compliance, and unusual toolchains may justify instructions independently. Read v3's behavioral analysis and limitations; avoid the blanket conclusion that instruction files are useless. [Full text](https://arxiv.org/html/2602.11988v3).

5. **[Artificial Intelligence in the Firm: Bottlenecks in Software Production](https://fion.ac/jellyfish.pdf)** — Fiona Chen and James Stratton; first version **2026-01-07**, current PDF **2026-08-04**, working paper. **Library: not found.**

   Best addition if you want to connect agent execution to completed engineering work. The dataset covers 718 firms. A staggered difference-in-differences analysis estimates increases in code activity after agent adoption, a 49% longer submission-to-merge interval, and no statistically significant increase in tracked issue/epic resolutions.

   **Limit:** observational identification assumptions, proprietary data, and a March 2026 data cutoff constrain interpretation. Review duration includes waiting; it is not a direct measurement of hands-on reviewer effort. Non-significance is not proof of zero benefit. Read the empirical design and review-bottleneck sections.

6. **[Agentic Harness Engineering: Observability-Driven Automatic Evolution of Coding-Agent Harnesses](https://arxiv.org/abs/2604.25850)** — Jiahang Lin et al.; **2026-04-28**, revised **2026-05-18**, preprint. **Library: not found.**

   Particularly relevant to SASE's emphasis on recorded evidence. The system exposes editable components, organizes execution evidence, and makes proposed changes carry predictions that subsequent outcomes can test. Ten iterations improve Terminal-Bench performance from 69.7% to 77.0%; frozen-harness transfer provides additional evidence.

   **Limit:** evolution uses the full 89-task Terminal-Bench set, so that headline is not a clean unseen-task estimate. Model-specific timeout/budget choices complicate transfer. Read the change-attribution mechanism, component ablations, and transfer design. [Full text](https://arxiv.org/html/2604.25850v4).

7. **[SWE-Milestone: Evaluating AI Agents on Continuous Software Evolution](https://arxiv.org/abs/2603.13428)** — Gangda Deng et al.; **2026-03-13**, revised **2026-07-21**; published at ICML 2026. **Library: not found.**

   Complements SlopCodeBench through real repository histories and milestone dependency graphs. Across twelve models and four frameworks, the reported continuous-evolution Score reaches only 38.03%, versus over 80% on isolated milestones. Score measures partial progress; it is distinct from complete milestone resolution.

   **Limit:** test-rich repositories and dependency filtering shape the sample. Specification refinement uses strong-agent dry runs and human oversight, which matters when interpreting the isolated-task baseline. Read error propagation and the benchmark-construction limitations. [Full text](https://arxiv.org/html/2603.13428v4), [conference record](https://proceedings.mlr.press/v306/deng26d.html).

8. **[Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)** — Mikaela Grace et al., Anthropic; **2026-01-09**, engineering essay. **Library: already in your library, queued since 2026-01-11, legacy backlog.**

   Highest-priority queued essay. It connects tasks, repeated trials, traces, graders, and observable outcomes, and distinguishes finding one successful attempt from reliable repeated success. Useful for turning the preceding papers into an evaluation practice for SASE.

   **Limit:** a practitioner synthesis, not an independently replicated coding-agent experiment. Favor its evaluation vocabulary and grader calibration guidance over any assumption that one metric or framework fits every task.

9. **[Quantifying infrastructure noise in agentic coding evals](https://www.anthropic.com/engineering/infrastructure-noise)** — Gian Segato, Anthropic; **2026-02-05**, engineering essay. **Library: not found.**

   A compact, practical read before comparing agent or model scores. Holding the model, harness, and tasks fixed, Anthropic reports a six-percentage-point Terminal-Bench difference across resource configurations. It distinguishes transient environment failures from extra resources that permit different solution strategies.

   **Limit:** vendor experiments on one benchmark, not a universal correction factor. For SASE, the actionable question is whether identical CPU, memory, timeout, and enforcement conditions accompany a claimed performance improvement.

10. **[CooperBench: Why Coding Agents Cannot be Your Teammates Yet](https://arxiv.org/abs/2601.13295)** — Arpandeep Khatua et al.; **2026-01-19**, revised **2026-01-26**; also appeared at the ICLR 2026 MALGAI workshop. **Library: not found.**

    Read as the failure-analysis companion to PASC. Feature pairs across twelve libraries and four languages create integration conflicts despite locally implementable changes. It distinguishes communication failures, broken commitments, and inaccurate expectations about another agent's work.

    **Limit:** deliberately constructed collaborative tasks and tested agent settings do not characterize every parallel workflow. Do not equate its feature-pair setting with PASC's two-agent shared-task setting. Focus on failure taxonomy and matched solo/team baselines. [Full text](https://arxiv.org/html/2601.13295v2).

11. **[Red/green TDD](https://simonwillison.net/guides/agentic-engineering-patterns/red-green-tdd/)** — Simon Willison; **2026-02-23**, practitioner article. **Library: not found.**

    The shortest actionable item here. Write a behavioral test, observe it fail, then let the agent implement the change. The observed failing phase helps detect tests that never exercised the requested behavior.

    **Limit:** practitioner guidance rather than a controlled study, and passing self-authored tests does not settle architectural quality or independent acceptance. Apply it where the requested behavior needs a regression test. Publication date is confirmed by the author's [dated launch announcement](https://simonwillison.net/2026/Feb/23/agentic-engineering-patterns/), which names this among the first two chapters published that day.

12. **[Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)** — Prithvi Rajasekaran, Anthropic; **2026-03-24**, engineering essay. **Library: already in your library, queued since 2026-03-28, legacy backlog.**

    Best queued implementation narrative: separate generation from skeptical evaluation, calibrate the evaluator, and revisit scaffolding as model capability changes. Its move from Opus 4.5 to 4.6 illustrates why mechanisms that once helped can become unnecessary overhead.

    **Limit:** selected application demonstrations and provider-authored judgments, not a representative benchmark or proof that every independent evaluator improves quality. Read the evaluator design and the sections on removing sprint structure; assess the additional cost alongside the result.

Library check: 8 of 24 candidates already in your library (4 finished).
