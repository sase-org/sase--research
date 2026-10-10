# Recent articles on agentic software engineering

**Researcher:** grk (research swarm member)
**Date:** 2026-10-10
**Question:** Which of the best articles on agentic software engineering from the last year (on or after 2025-10-10) should Bryan read next?
**Cutoff:** published, posted, or substantially revised on or after 2025-10-10.
**Library check:** Bob `ref/` only. Absence from the index is never proof a work was unread.

## Recommendation

Read in this order:

1. Finish Hassan et al. on Structured Agentic Software Engineering (already queued).
2. Read Lyu et al. on how practitioners actually build SE agents (unread).
3. Read Anthropic's June 2026 Claude Code usage study (unread).
4. Read AgentLens on "lucky pass" evaluation (unread).
5. Read the ASE 2026 plan-compliance study (unread).

Those five cover the discipline's self-definition, the process shift in teams that ship agents, field evidence at session scale, and the evaluation hole that pass@1 papers still paper over. Skip OpenAI's February 2026 harness-engineering post and Barbaste et al.'s July 2026 source-code anatomy: both are already finished in the library.

## Method

Sources were gathered independently from arXiv cs.SE / cs.AI, ICSE 2026, ASE 2026, MSR 2026, ESEM 2026, TOSEM, CACM, Anthropic and OpenAI research blogs, Bain, Thoughtworks, and METR. The window is one year back from 2026-10-10. First-version dates slightly before the cutoff were kept only when a later revision or venue version falls inside the window, and those cases are labeled.

Quality filter for the ranked list:

- Peer-reviewed or lab-grade empirical work, or a primary vendor write-up with original measurements.
- Directly about agentic *software engineering* (process, harness, evaluation, field practice, labor), not generic multi-agent surveys.
- Distinct from work already finished in Bob.

Every URL and title in the candidate set was passed through one `bob ref find` batch (plus a short follow-up batch). Finished items are dropped from the "read next" ranking. Queued or started items stay only when they still look like the highest-leverage unread work, and they are labeled.

## What the last year actually is

The field moved from "agents that patch GitHub issues" to "software engineering as delegated, supervised execution." Four facts frame the year.

**Benchmarks saturated, then cracked.** SWE-bench Verified scores that sat in the low single digits in late 2023 are now routinely reported in the 70–80% range on vendor harnesses. Scale AI's SWE-Bench Pro (arXiv 2509.16941, 2025-09-21, 19 days before the cutoff) was built as the harder successor: 1,865 long-horizon tasks, public / held-out / commercial splits, frontier resolve rates around 23% at launch. OpenAI later audited task quality on both Verified and Pro. Terminal-Bench 2.x became the other yardstick, scoring the model *plus* harness *plus* live shell. Meta's E2E-SWE (2026-09-29) asks a different question still: can an agent *build a working repository from an empty workspace*? Pass@1 across 13 frontier models spans 11.7% to 67.7%.

**The unit of work moved from the patch to the harness.** OpenAI's Codex team (Lopopolo, 2026-02-11) documented an internal product of ~1M lines and ~1,500 merged PRs written entirely by Codex, with humans steering. The durable lesson is mechanical: a short `AGENTS.md` as table of contents, a versioned `docs/` system of record, linters that encode architecture, agent-to-agent review, and observability made legible to the agent. Barbaste, Darrigol, Vu, and Wiltberger (arXiv 2609.00006, 2026-07-15) then dissected eleven production coding harnesses at source level and argued that in the first half of 2026 the coding harness completed a turn from tool to platform. You have finished both of those.

**Practice studies finally caught up with the demos.** Lyu, Williams, Shi, Sun, Peng, Yang, Sarro, and Lo (arXiv 2607.10856, 2026-07-12) interviewed 20 practitioners at 12 organizations and surveyed 80 more. Li, Zhang, and Hassan released AIDev (arXiv 2602.09185, MSR 2026): 932,791 agent-authored PRs from Codex, Devin, Copilot, Cursor, and Claude Code. Anthropic analyzed ~400,000 Claude Code sessions (Hitzig et al., 2026-06-16). Google deployed FlowAgent into pre-submit CI and applied 28,554 suggested fixes after 295,508 change suggestions (Ziftci et al., ASE 2026).

**The bottleneck is now review, evaluation, and expertise.** Bain's 2026 tech survey (293 senior technology leaders, published 2026-09-29) reports developers completing ~21% more tasks while review time rises ~91%, with 47% more concurrent workstreams. Anthropic finds people keep ~70% of planning decisions and hand Claude ~80% of execution decisions; domain expertise, not a software-engineering job title, predicts verified success. METR's early-2025 RCT (just outside the window) found a 19% slowdown with a 20% perceived speedup; their February 2026 follow-up sees point estimates of speedup that they treat as a lower bound because developers now refuse AI-disallowed tasks.

## Theme 1 — Naming the discipline

Hassan, Li, Lin, Adams, Chen, Kashiwa, and Qiu, *Agentic Software Engineering: Foundational Pillars and a Research Roadmap* (arXiv 2509.06216). First posted 2025-09-07 (33 days before the cutoff); current v3 2026-06-24. This is the paper that named Structured Agentic Software Engineering, split the field into SE-for-humans and SE-for-agents, and proposed the Agent Command Environment (ACE) and Agent Execution Environment (AEE), with Merge-Readiness Packs and Consultation Request Packs as the structured handoff artifacts. Briefing Engineering, Agentic Loop Engineering, and AI Teammate Lifecycle Engineering are the process names. **Already in the library as queued** (`ref/papers/agentic_software_engineering.md`, captured 2026-10-07, 2 annotations, blocked on the `sase` parent task). Finish this before anything else on the list. The June 2026 revision is the version to read.

Hoda, *Toward Agentic Software Engineering Beyond Code: Framing Vision, Values, and Vocabulary* (arXiv 2510.19692, 2025-10-22; ICSE 2026 Companion). A five-page values-and-vocabulary paper arguing that agentic SE has to be a whole-of-process shift, not a coding-acceleration story. **Already in the library as started** (legacy `collect_fleeting_notes` since 2025-11-15). Short, and it pairs with Hassan.

Alenezi, *From Determinism to Delegation: AI-Native Software Engineering and the Evolution of the Agentic Engineer* (arXiv 2606.28791, 2026-06-27). Position paper: the unit of work becomes the supervised agent workflow, correctness becomes statistical evaluation, accountability becomes outcome ownership. Useful as a compact "Agentic Engineer" job description. Unread.

Fuggetta, *Why Software Engineering Is Indispensable in the Age of Coding Agents* (arXiv 2610.10226, 2026-10-07; accepted at CACM). Five pages. Three LLM properties — probabilistic generation, agnosticism, semantic statelessness — create a vacuum that four reified knowledge levers have to fill: methodology, domain, design choices, process choices. The engineer is methodologist, mediator, and custodian. Unread, and the right short CACM piece to put next to Hassan.

Guo, Huang, Li, Huang, Chen, Zhang, Guo, Yu, Yiu, Lio, and Lam, *A Comprehensive Survey on Benchmarks and Solutions in Software Engineering of LLM-Empowered Agentic System* (arXiv 2510.09721, 2025-10-10). 150+ papers, 50+ benchmarks, living GitHub list. The best in-window map of the *solution × benchmark* grid. Unread. Liu et al.'s TOSEM survey (arXiv 2409.02977, TOSEM 2026) is older at the root (2024) and **already started** in the library; skip it unless you want the SE-task × agent-architecture taxonomy.

## Theme 2 — How teams actually build and run SE agents

Lyu et al., *How Do Practitioners Build SE Agents? Insights from a Mixed-Methods Study* (arXiv 2607.10856, v2 2026-07-25). This is the strongest unread empirical paper of the year for someone building an agent platform. Implementation got cheaper; bottlenecks moved to requirements, coordination, review, evaluation, and deployment. They describe a seven-stage loop and five process shifts, including evaluation-driven development and treating prompts, skills, context definitions, and scaffold behavior as first-class, versioned artifacts. Six challenges (unreliable eval signals, comprehension debt, provider-side model-update regressions) come with twelve practices. 91% of survey respondents agreed with the overall workflow. **Not in the library.**

Chatlatanagulchai, Li, Kashiwa, Reid, Thonglek, Leelaprute, Rungsawang, Manaskasemsak, Adams, Hassan, and Iida, *Agent READMEs: An Empirical Study of Context Files for Agentic Coding* (arXiv 2511.12884, 2025-11-17; v2 2026-08-09). 2,303 context files (`AGENTS.md`, `CLAUDE.md`, and kin) from 1,925 repositories. These files evolve like configuration code. Developers specify tests (75.9%), implementation details (70.8%), and architecture (68.1%); security (14.8%) and performance (14.5%) are rare. Directly relevant to memory-built instruction files. **Already queued** (legacy, added 2026-01-18). The August 2026 v2 is the version to read.

Horikawa, Li, Kashiwa, Adams, Iida, and Hassan, *Agentic Refactoring: An Empirical Study of AI Coding Agents* (arXiv 2511.04824, 2025-11-06; submitted to TOSEM). 15,451 refactoring instances in the AIDev Java slice. Agents explicitly target refactoring in 26.1% of commits, mostly low-level consistency edits (change variable type, rename parameter/variable), motivated by maintainability (52.5%) and readability (28.1%), with small structural gains. **Already queued** (legacy, added 2026-01-18).

Li, Zhang, and Hassan, *AIDev: Studying AI Coding Agents on GitHub* (arXiv 2602.09185, 2026-02-09; MSR 2026). The corpus behind the two papers above, later grown to millions of PRs. Required if you want to mine agent PRs yourself. Unread.

Peng, Calvo, Kalu, and Davis, *How Do Coding Agents Optimize Software and Report Performance Validation?* (arXiv 2610.03969, 2026-10-02). 1,130 agentic vs 1,130 human performance PRs through June 2026. Agentic PRs merge less often (54.4% vs 73.3%), use similar optimization strategies, and lean more on static reasoning than benchmarks (46.1% vs 57.2%), with that gap closing over the study period. Unread, narrower.

An exploratory ESEM 2026 paper on repository-preserved Agent Plans (LIPIcs ESEM 2026, 85 Markdown plan files from 10 of 36,710 screened repos) is a thin but on-point look at task-oriented plan artifacts sitting next to `AGENTS.md`. Unread.

## Theme 3 — Evaluation is the open problem

Sahoo, Mittal, Li, Ma, Steenhoek, Lin, and Hu, *AgentLens: Revealing The Lucky Pass Problem in SWE-Agent Evaluation* (arXiv 2605.12925, 2026-05-13; v4 2026-10-05). 2,614 OpenHands trajectories, eight model backends, 60 SWE-bench Verified tasks. Among 1,136 passing trajectories with process references, 10.7% are Lucky Passes: regression cycles, blind retries, missing verification, or disordered explore/implement/verify. 94.3% of lucky passes skip verification. Some models move five rank positions when ranked by process quality instead of pass rate. This is the paper that makes "SWE-bench went up" an incomplete sentence. **Not in the library.**

Liu, Dehghan, Ganhotra, Hirzel, and Jabbarvand, *From Plan to Action: How Well Do Agents Follow the Plan?* (arXiv 2604.12147, 2026-04-13; ASE 2026). 21,120 SWE-agent trajectories, four LLMs, SWE-bench Verified and Pro, eight plan variations. No plan → internalized, often incomplete workflows. A good standard plan helps. A bad plan is worse than none. Extra early-stage phases that fight the model's internal strategy hurt. Periodic plan reminders reduce violations. Directly relevant to SASE plans, stitches, and "explicit plan as artifact." **Not in the library.**

Ding, Bi, Zhu, Yang, Deitke, Yin, Wang, and Hou, *E2E-SWE: Benchmarking LLMs on Building Working Codebases from Scratch* (arXiv 2609.38335, 2026-09-29; Facebook/Meta). 186 whole-repo tasks, 11 languages, hidden tests, implementation-independent specs. Trajectories show long, front-loaded reasoning. Complements issue-resolution benches. Unread.

Luo, Wang, Li, Yin, Yan, Cheng, Wang, Liu, Zhang, Ye, Liu, and Yu, *Distilling Agentic Systems: A Roadmap across Models, Artifacts, and Harnesses* (arXiv 2609.36630, 2026-09-29). 57 pages. Agent Distillation as persistent transfer of task-solving knowledge, retained in the model, in artifacts, in the execution harness, or across substrates. This is the conceptual paper that matches SASE's bet that competence lives in the harness and in versioned artifacts. Unread.

## Theme 4 — Production systems and labor

Ziftci, Greene, Liu, Dalloro, and Dini, *Catching Developers in the Flow: Low-Latency Agentic Program Repair at Google Scale* (arXiv 2610.07289, 2026-10-05; ASE 2026). FlowAgent in Google's pre-submit outer loop (Critique/Cider). ReAct generate-and-validate plus abstention filters under latency constraints. 67.18% correct on a 195-failure manual sample; 28,554 applied fixes after Google-wide deployment. The industrial counterpart to "agents in the inner loop." Unread.

Hitzig, Massenkoff, Lyubich, Zhang, Heller, and McCrory, *Agentic coding and persistent returns to expertise* (Anthropic, 2026-06-16). ~400k Claude Code sessions, ~235k people, October 2025–April 2026. Users hold planning; Claude holds execution. Expert prompts trigger ~12 actions and ~3,200 words vs ~5 actions and ~600 words for novices. Verified success 15% (novice) vs 28–33% (intermediate and up). Debugging share fell from 33% to 19%; operating, analysis, and writing grew. Estimated session value +27%. Occupations other than software land within seven points of software engineers on coding-session verified success. Companion reports on autonomy and internal Anthropic usage are also unread. **Bob `find` on this URL returned only a weak slug match against Claude Code *docs*; treat as absent from `ref/`.**

Bain & Company, *The Missing Architecture for Agentic Software Development* (Technology Report 2026, 2026-09-29). Knowledge agents can consume, a harness that enforces quality deterministically, and treating the SDLC as a product. The review-time statistic is the one worth taking from it. Unread. (The live page is Cloudflare-gated; the abstract and "at a glance" block were retrieved from search snippets and should be verified on the PDF.)

Thoughtworks, *Engineering the harness: A practical pattern for reliable coding agents* (2026-09-29). Agent = model + harness. Guides (pre-action), sensors (post-action), selective human gates, a six-phase ANALYZE-through-delivery loop. Practitioner distillation of the OpenAI/Anthropic year. Unread.

METR, *We are Changing our Developer Productivity Experiment Design* (2026-02-24), plus the original RCT (arXiv 2507.09089, 2025-07-10, outside the strict window). The original result — 16 experienced OSS developers, 246 tasks, Cursor + Claude 3.5/3.7, 19% slower, 20% believed faster — is the cleanest causal study we have, and it is 15 months old. The in-window follow-up is the methodological story: developers now refuse the AI-off arm, so the late-2025 point estimates (−18% time for returning developers, −4% for new ones) are a lower bound. Unread, both.

OpenAI Developers, *Codex as a platform: build on the open agent harness* (2026-08-19). The public SDK/app-server follow-on to the finished harness-engineering post. Worth it only if you care about embedding Codex rather than reading another manifesto. Unread.

## What I am not ranking highly

- Bhati, *Agentic AI in the Software Development Lifecycle* (arXiv 2604.26275, 2026-04-29): a 9-page single-author survey that restates SWE-bench curves and vendor names. Use Guo or Hassan instead.
- Gorsky, *ASE-26: a curriculum for agentic software engineering as a discipline* (arXiv 2606.01152): curriculum deposit, derivative of Hassan/Hoda.
- Khan, Aljuaid, and Ning, *A critical assessment of the rise of agentic AI* (Discover Artificial Intelligence, 2026-10-05): nine-domain agentic-AI survey; software engineering is one chapter.
- Otoum and Elkhalili, IEEE Access 2026 SLR: generic methods-and-techniques review.
- FC-SWE, Agent4RE, Code Primitives, SWE-Journey: good specialized papers, lower priority than the process/eval/practice cluster.
- SWE-smith (NeurIPS 2025, arXiv 2504.21798) and the original METR RCT: important, outside the one-year window.

## Taste notes from the library

Recent finished reads in this neighborhood are Barbaste et al. (harness anatomy, finished 2026-10-10), OpenAI harness engineering (finished 2026-10-03), Nijkamp et al. on long-horizon agent architecture (arXiv 2609.19519, finished 2026-10-10), EA-Graph (arXiv 2608.04278), OpenAI Symphony, and filesystem-based agent memory. The unread list below is chosen to add *process evidence, field usage, and evaluation* on top of that harness/architecture cluster, rather than another source-level harness tour.

## Ranked list to consider reading

Rank combines (a) relevance to agentic SE as a discipline and to SASE-shaped work, (b) empirical or conceptual novelty in the last year, (c) density per page, (d) library status. Finished items are omitted.

| Rank | Article | Date | Why | Library |
| --- | --- | --- | --- | --- |
| 1 | Hassan et al., *Agentic Software Engineering: Foundational Pillars and a Research Roadmap*. [arXiv:2509.06216](https://arxiv.org/abs/2509.06216) (v3 2026-06-24) | 2025-09-07 / rev. 2026-06-24 | The SASE vision paper: ACE/AEE, briefing, loop engineering, teammate lifecycle. v1 is 33 days outside the window; read v3. | Already in your library (queued since 2026-10-07; legacy copy queued since 2025-11-28). Finish it. |
| 2 | Lyu, Williams, Shi, Sun, Peng, Yang, Sarro, Lo, *How Do Practitioners Build SE Agents?* [arXiv:2607.10856](https://arxiv.org/abs/2607.10856) | 2026-07-12 | Only mixed-methods study of how teams *build* SE agents. Specs, skills, and scaffolds as first-class artifacts; evaluation-driven development; comprehension debt. | not in `ref/` |
| 3 | Hitzig, Massenkoff, Lyubich, Zhang, Heller, McCrory, *Agentic coding and persistent returns to expertise*. [Anthropic](https://www.anthropic.com/research/claude-code-expertise) | 2026-06-16 | 400k-session picture of the actual division of labor: humans plan, the agent executes; expertise beats job title. | not in `ref/` (slug collision with Claude Code docs only) |
| 4 | Sahoo et al., *AgentLens: Revealing The Lucky Pass Problem in SWE-Agent Evaluation*. [arXiv:2605.12925](https://arxiv.org/abs/2605.12925) (v4 2026-10-05) | 2026-05-13 | Process-level scoring of SWE-agent traces. Pass@1 hides lucky, unverified, thrashing successes. | not in `ref/` |
| 5 | Liu, Dehghan, Ganhotra, Hirzel, Jabbarvand, *From Plan to Action: How Well Do Agents Follow the Plan?* [arXiv:2604.12147](https://arxiv.org/abs/2604.12147) (ASE 2026) | 2026-04-13 | 21k-trajectory study of plan compliance. Bad plans hurt more than no plan. Directly about making plans load-bearing. | not in `ref/` |
| 6 | Hoda, *Toward Agentic Software Engineering Beyond Code*. [arXiv:2510.19692](https://arxiv.org/abs/2510.19692) (ICSE 2026 Companion) | 2025-10-22 | Values, vocabulary, whole-of-process scope. Five pages. | Already in your library (started since 2025-11-15, legacy). |
| 7 | Ziftci, Greene, Liu, Dalloro, Dini, *Catching Developers in the Flow*. [arXiv:2610.07289](https://arxiv.org/abs/2610.07289) (ASE 2026) | 2026-10-05 | Google-scale pre-submit repair agent with abstention, latency, and applied-fix counts. | not in `ref/` |
| 8 | Luo et al., *Distilling Agentic Systems: A Roadmap across Models, Artifacts, and Harnesses*. [arXiv:2609.36630](https://arxiv.org/abs/2609.36630) | 2026-09-29 | Where agent competence lives once it is no longer "just the weights." | not in `ref/` |
| 9 | Chatlatanagulchai et al., *Agent READMEs*. [arXiv:2511.12884](https://arxiv.org/abs/2511.12884) (v2 2026-08-09) | 2025-11-17 | Large-scale study of `AGENTS.md` / `CLAUDE.md`. Functional context is common; security and performance guardrails are not. | Already in your library (queued since 2026-01-18, legacy). Prefer v2. |
| 10 | Fuggetta, *Why Software Engineering Is Indispensable in the Age of Coding Agents*. [arXiv:2610.10226](https://arxiv.org/abs/2610.10226) (CACM) | 2026-10-07 | Short argument that SE knowledge has to be reified as persistent artifacts. | not in `ref/` |
| 11 | Li, Zhang, Hassan, *AIDev: Studying AI Coding Agents on GitHub*. [arXiv:2602.09185](https://arxiv.org/abs/2602.09185) (MSR 2026) | 2026-02-09 | The field dataset (932k agentic PRs; later versions larger). | not in `ref/` |
| 12 | Ding et al., *E2E-SWE*. [arXiv:2609.38335](https://arxiv.org/abs/2609.38335) | 2026-09-29 | From-scratch repository construction, the next eval axis after issue resolution. | not in `ref/` |
| 13 | Doddapaneni, McLaughlin, Liu, Radzevych, *The Missing Architecture for Agentic Software Development*. [Bain](https://www.bain.com/insights/the-missing-architecture-for-agentic-software-development-technology-report-2026/) | 2026-09-29 | Industry architecture: knowledge, deterministic harness, SDLC-as-product; review as the constraint. | not in `ref/` |
| 14 | Guo et al., *A Comprehensive Survey on Benchmarks and Solutions…*. [arXiv:2510.09721](https://arxiv.org/abs/2510.09721) | 2025-10-10 | In-window literature map (150+ papers, 50+ benches). | not in `ref/` |
| 15 | Horikawa et al., *Agentic Refactoring*. [arXiv:2511.04824](https://arxiv.org/abs/2511.04824) | 2025-11-06 | What agents actually change when they "refactor." | Already in your library (queued since 2026-01-18, legacy). |
| 16 | Thoughtworks, *Engineering the harness*. [link](https://www.thoughtworks.com/insights/blog/architecture/engineering-the-harness-a-practical-pattern-for-reliable-coding-agents) | 2026-09-29 | Practitioner pattern language (guides, sensors, gates) after you have already read OpenAI's original. | not in `ref/` |
| 17 | METR, *We are Changing our Developer Productivity Experiment Design*. [link](https://metr.org/blog/2026-02-24-uplift-update/) | 2026-02-24 | How the causal-productivity measurement broke once developers would not work without agents. Pair with arXiv 2507.09089 (Jul 2025, outside the strict window). | not in `ref/` |
| 18 | Alenezi, *From Determinism to Delegation*. [arXiv:2606.28791](https://arxiv.org/abs/2606.28791) | 2026-06-27 | Compact "Agentic Engineer" role paper. | not in `ref/` |

If you only take three new captures: **Lyu et al. 2607.10856**, **Anthropic expertise**, **AgentLens 2605.12925**.

## Already finished (do not recapture)

- Barbaste et al., *Harness Engineering: Anatomy, Architecture, and Evolution of Coding Agents* (arXiv 2609.00006). Finished 2026-10-10.
- Lopopolo, *Harness engineering: leveraging Codex in an agent-first world* (OpenAI, 2026-02-11). Finished 2026-10-03.
- Nijkamp et al., *An Architecture for Long-Horizon Agents* (arXiv 2609.19519). Finished 2026-10-10. Taste signal, not an SE-process paper.
- EA-Graph (arXiv 2608.04278). Finished. Verification-memory paper, already in the SASE cluster.

Hugo Bowne-Anderson, *Harness engineering: why agent context…* ([Substack](https://hugobowne.substack.com/p/harness-engineering-why-agent-context)) is already queued (legacy, 2026-03-29). Low incremental value on top of the finished OpenAI post and Barbaste paper.

## Proposed captures

```bash
bob ref create https://arxiv.org/abs/2607.10856 -L
bob ref create https://www.anthropic.com/research/claude-code-expertise -L
bob ref create https://arxiv.org/abs/2605.12925 -L
bob ref create https://arxiv.org/abs/2604.12147 -L
bob ref create https://arxiv.org/abs/2610.07289 -L
bob ref create https://arxiv.org/abs/2609.36630 -L
bob ref create https://arxiv.org/abs/2610.10226 -L
bob ref create https://arxiv.org/abs/2602.09185 -L
bob ref create https://arxiv.org/abs/2609.38335 -L
bob ref create https://www.bain.com/insights/the-missing-architecture-for-agentic-software-development-technology-report-2026/ -L
bob ref create https://arxiv.org/abs/2510.09721 -L
bob ref create https://www.thoughtworks.com/insights/blog/architecture/engineering-the-harness-a-practical-pattern-for-reliable-coding-agents -L
bob ref create https://metr.org/blog/2026-02-24-uplift-update/ -L
bob ref create https://arxiv.org/abs/2606.28791 -L
```

Do not recapture Hassan, Hoda, Agent READMEs, or Agentic Refactoring; they are already in `ref/`.

## Limits

- Window is calendar-strict except where a later version is named.
- Bain's full report was not readable behind Cloudflare; ranking 13 uses the published abstract and "at a glance" statistics from indexed copies.
- `bob ref find` covers `ref/` only. Zorg-era records outside `ref/` are uncounted.
- Vendor blogs (Anthropic, OpenAI, Bain) are primary sources with an incentive to narrate success; the ranked list balances them with independent empirical papers.
- This swarm member did not read peer `__cdx` / `__cld` / `__mus` / `__gem` reports.

Library check: 8 of 37 URL candidates already in your library (2 finished). A follow-up batch of 9 related URLs added 2 more finished items used only as taste signals (Nijkamp; EA-Graph). Combined: 10 of 46 unique URLs in library (4 finished).
