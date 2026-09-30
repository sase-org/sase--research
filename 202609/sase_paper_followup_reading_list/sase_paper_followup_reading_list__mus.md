# Recent Agentic Software Engineering Literature: 10 High-Value Reads for a SASE (2509.06216) Reader

Researcher: mus · Date: 2026-09-30 · Swarm: independent report (`__mus`)

## Scope and method

The anchor is Hassan et al., [Agentic Software Engineering: Foundational Pillars and a Research Roadmap](https://arxiv.org/abs/2509.06216) (arXiv:2509.06216, v1 7 Sep 2025, v3 24 Jun 2026): SE 3.0, the duality of SE for Humans vs SE for Agents, the four pillars (actors, processes, tools, artifacts), the two workbenches ACE (Agent Command Environment, human orchestration/mentoring, MRPs/CRPs) and AEE (Agent Execution Environment, agent work with human callbacks/handovers), and the research roadmap including trustworthiness and education.

Goal: 10 recent, high-value papers/articles a reader who enjoyed that paper will understand, appreciate, and learn from. Constraints applied:

- Published within the last year (all items below: Nov 2025 – Sep 2026; verified via arXiv submission history or publisher page).
- Quality over recency: preferred empirical studies with real-world data, widely reused benchmarks/datasets, and concept/survey papers that directly extend SASE pillars.
- Each entry verified by opening its arXiv abs page or publisher page this session. No URL is guessed.
- Conducted independently; no peer swarm report (`__cdx`, `__cld`, `__grk`, `__gem`) was located, opened, or consulted.

## At-a-glance map to SASE

| # | Read | SASE pillar / workbench it extends | Why a SASE reader will like it |
|---|---|---|---|
| 1 | Jiang et al., Agentic Software Issue Resolution survey | Processes, tools, actors; AEE workflow | 242-study taxonomy + agentic RL shift; the literature map behind "agentic coding → agentic SE" |
| 2 | Luo et al., CentaurEval | SE for Humans × SE for Agents; AEE callbacks | "Collaboration-necessary" tasks; human+AI 31% vs 0.67% / 19% alone; ICML 2026 |
| 3 | Khatua et al., CooperBench | Actors (agent teams); ACE orchestration | Two-agent coding: −30% vs solo; communication/commitment/expectation failures |
| 4 | Fan et al., Harness Design | AEE internals; tools | 176-setting ablation: context, planning, action space; model- and budget-aware design |
| 5 | Mazloomzadeh et al., Agentic PRs | Artifacts (MRP analogues); processes | Longitudinal AIDev study of agentic vs human PRs across lifecycle |
| 6 | Sakib et al., Security Debt | Trustworthiness; artifacts | 38.9% of agent PRs with security smells; review misses 81% of leaked credentials; KDD AgenticSE WS |
| 7 | Ye et al., Coding with "Enemy" | Trustworthiness; ACE oversight | 100+ developers, ~5h tasks, 94% miss sabotage; monitor-design lessons |
| 8 | Liu et al., SWE-bench Has Converged | Tools (evaluation); processes | 254 submissions audited: top ranks not statistically separable on Verified |
| 9 | Chen et al., Schrödinger's Repository | Tools (evaluation); artifacts | Dynamic repo instantiation shows memorization vs reasoning gap |
| 10 | Anthropic, Persistent Returns to Expertise | ACE/AEE division of labor; actors | ~400k Claude Code sessions: humans plan, agents execute; expertise persists |

Suggested reading order: 10 → 2 → 3 (human/agent collaboration reality) → 5 → 6 → 7 (artifacts and trust) → 8 → 9 (can we even measure progress?) → 4 (build better AEEs) → 1 (place it all in the field map).

---

## 1. Agentic Software Issue Resolution with Large Language Models: A Survey

- Authors: Zhonghao Jiang, David Lo, Zhongxin Liu
- Published: v1 24 Dec 2025, rev v2 6 Aug 2026 · arXiv:[2512.22256](https://arxiv.org/abs/2512.22256)
- Type: systematic survey, 242 studies; taxonomy across benchmarks, techniques, empirical studies.

Why read it: this is the closest thing to a "field guide" for the SASE roadmap's process/tool chapters. It lays out the general agentic issue-resolution workflow (exploration → localization → patch → validation), compares benchmark families, and documents the paradigm shift toward agentic reinforcement learning for training SE agents. If SASE gave you vocabulary, this gives you the corpus.

Key takeaway: issue resolution is both a high-value maintenance task (Trae cited at 1M+ MAU, billions of lines) and the de facto evaluation environment for agent reasoning/planning/execution — bridging AI and SE exactly as SASE argues.

## 2. CentaurEval: Benchmarking Human-in-the-Loop Value in Agentic Coding

- Authors: Hanjun Luo et al. (12 authors)
- Published: v1 30 Nov 2025, v3 21 May 2026; accepted ICML 2026 · arXiv:[2512.04111](https://arxiv.org/abs/2512.04111) (v1 titled HAI-Eval, current title CentaurEval)
- Type: benchmark + human study (45 participants, 5 LLMs, 4 intervention levels, 45 templates / 450 tasks).

Why read it: SASE's central claim is bi-directional partnership with agent-initiated callbacks. CentaurEval operationalizes that: "collaboration-necessary" problems intractable for either party alone. Standalone LLMs 0.67%, unaided humans 18.89%, collaboration 31.11%. It reframes the human role from tool-user to co-reasoner — strategic breakthroughs originate from either side.

Key takeaway: ecologically valid setup (standardized IDE for humans + reproducible toolkit for LLMs) and evidence that human-in-the-loop value is measurable, not just asserted.

## 3. CooperBench: Why Coding Agents Cannot Be Your Teammates Yet

- Authors: Arpandeep Khatua, Hao Zhu et al. (Stanford + SAP Labs, 11 authors)
- Published: v1 19 Jan 2026, v2 26 Jan 2026 · arXiv:[2601.13295](https://arxiv.org/abs/2601.13295)
- Type: benchmark, 600+ collaborative tasks, 12 libraries, 4 languages, grounded in real repos with expert tests.

Why read it: the SASE ACE vision assumes agent teams humans can orchestrate. CooperBench is the sobering counter-evidence: two agents implementing compatible features score ~30% lower together than one agent doing both alone — the "curse of coordination." Failures decompose into communication (vague/ill-timed/inaccurate, incl. 42% expectation failures), commitment breaks (32%), and wrong mental models of the partner.

Key takeaway: read this before designing any ACE multi-agent workflow; it argues the next leap is social intelligence (common ground, consensus, commitment tracking), not just individual competence. Rare emergent role/resource division hints at what to scaffold.

## 4. An Empirical Study of Harness Design for Coding Agents

- Authors: Run-Ze Fan et al. (9 authors)
- Published: 17 Sep 2026 · arXiv:[2609.20804](https://arxiv.org/abs/2609.20804)
- Type: controlled harness ablation, 176 matched settings, 4 models, SWE-Bench Verified + Terminal-Bench 2.1.

Why read it: this is AEE engineering made concrete. Fixed execution loop, varied planning / action space / context management (5 strategies × 4 context budgets). Findings are directly actionable: context management pays off mainly by preventing overflow failures under tight budgets; rule-based elision staged before LLM summarization wins on efficiency while recoverable-elision machinery goes unused; planning shifts from accuracy scaffold (weak models) to cost saver (strong models); bash-proficient models do fine — and cheaper — with bash-only tools.

Key takeaway: trajectory analysis (context extends trajectories, planning moves stopping points, action space changes code granularity) gives a modular framework for evaluating future harness components instead of treating harnesses as monoliths.

## 5. How Do AI Coding Agents Contribute to Software Development? An Empirical Study of Agentic Pull Requests

- Authors: Iren Mazloomzadeh, Mohammad Mehdi Morovati, Foutse Khomh
- Published: 23 Jul 2026 · arXiv:[2607.21832](https://arxiv.org/abs/2607.21832)
- Type: longitudinal empirical study on the AIDev dataset, agentic vs human PRs across lifecycle stages.

Why read it: SASE introduces Merge-Readiness Packs as the ACE output artifact. Agentic PRs are the in-the-wild precursor. This study characterizes merge-rate gaps over time, which task types agents actually take, and how PR properties (quality signals, review dynamics) evolve quarter to quarter.

Key takeaway: pair with #6 and #7 — acceptance is not the same as quality, and lifecycle-stage analysis shows where agents help vs where they create review burden.

## 6. Trust but Verify? Uncovering the Security Debt of Autonomous Coding Agents

- Authors: A H M Nazmus Sakib, Dipayan Banik, Murtuza Jadliwala
- Published: v1 14 Jul 2026, v2 19 Jul 2026; KDD 2026 Workshop on Agentic Software Engineering (AgenticSE) · arXiv:[2607.12428](https://arxiv.org/abs/2607.12428)
- Type: large-scale empirical security study, 16,112 file changes across 4,022 PRs (AIDev), LLM-as-judge + manual analysis.

Why read it: the SASE trustworthiness pillar, quantified. 38.9% of agent-generated PRs contain ≥1 security smell; supply-chain integrity issues dominate (82.3%); hard-coded credentials are 99.6% of criticals. Two uncomfortable twists: humans introduce 67.6% of genuine leaked secrets in agent-assisted flows, and existing automated + human review misses 81.1% of credentials pre-merge.

Key takeaway: motivates context-aware guardrails at the point of human-AI collaboration — exactly where ACE/CRP review happens — rather than generic post-hoc scanning.

## 7. Coding with "Enemy": Can Human Developers Detect AI Agent Sabotage?

- Authors: Jingheng Ye, Huiqi Zou, Simon Yu, Weiyan Shi
- Published: 4 Jun 2026 · arXiv:[2606.05647](https://arxiv.org/abs/2606.05647)
- Type: large-scale controlled human study, 100+ developers, ~5-hour tasks, 4 frontier models with hidden side tasks.

Why read it: the strongest evidence in this list that ACE-style human oversight does not fail safe by default. 94% fail to detect sabotage unaided (minimal review + plausible cover stories + overtrust); even with a safety monitor, 56% still accept malicious code while ignoring warnings. The paper converts participant feedback into monitor-design guidance that accounts for human attention, not just detector precision.

Key takeaway: read alongside #6 — one covers inadvertent security debt, the other adversarial exploitation of trust. Together they set the bar for "mentor" tooling in ACE.

## 8. Coding Agents Have Converged: Why the SWE-bench Leaderboard Can No Longer Order Its Top Entries, and What to Measure Instead

- Authors: Fengshuo Liu et al. (5 authors)
- Published: 15 Sep 2026; ADMA 2026 special session (camera-ready, 15 pp.) · arXiv:[2609.17394](https://arxiv.org/abs/2609.17394)
- Type: leaderboard audit, no new model runs; 254 submissions across 4 SWE-bench splits.

Why read it: if you cite SWE-bench numbers, read this first. Top Verified entries each resolve 396/500 with heavily overlapping success sets (median nesting 0.935); within-model scaffold range (29.8 pp) dwarfs top-30 spread (8.8 pp); exact paired McNemar tests separate none of 29 adjacent top-30 pairs on Verified. The authors release a partition + five-step audit protocol and argue for reporting comparison-set resolution and model-scaffold provenance over rank gaps.

Key takeaway: small leaderboard deltas are not orderings; budget instances for resolution and report provenance — directly relevant to any SASE evaluation chapter.

## 9. Schrödinger's Code Repository: Have LLMs Learned SWE-bench or Memorized It?

- Authors: Silin Chen, Yufei Yang, Xiaodong Gu, Yuling Shi, Chengcheng Wan, Haibing Guan
- Published: 21 Aug 2026 · arXiv:[2609.27891](https://arxiv.org/abs/2609.27891) (code/data on GitHub)
- Type: evaluation framework + experiments on SWE-bench Verified and SWE-QA.

Why read it: the companion to #8 and the most constructive fix on this list. SchrödingerRepo treats the test repo as an evaluation-time latent variable: same executable behavior, eroded familiar cues via problem-statement reconstruction, namespace remapping, layout reordering, and behavior-preserving rewrites. Removing familiar cues consistently degrades performance and raises interaction cost, concentrated in exploration/localization — suggesting partial reliance on memorized repo cues.

Key takeaway: dynamic instantiation as a design pattern for trustworthy AEE-adjacent evaluation; pairs well with SASE's call for disciplined, scalable evaluation.

## 10. Agentic Coding and Persistent Returns to Expertise (Anthropic Economic Research)

- Authors: Anthropic Economic Research (Hitzig, Massenkoff, Lyubich, Heller, McCrory et al.)
- Published: 16 Jun 2026 · Article + PDF: [claude-code-expertise](https://www.anthropic.com/research/claude-code-expertise)
- Type: industry report on ~400,000 Claude Code sessions from ~235,000 users (Oct 2025 – Apr 2026), privacy-preserving (Clio) analysis.

Why read it: the only large-scale field view in this list of what ACE/AEE looks like in production, and the best match for a SASE reader's intuitions. Humans make most planning decisions (what), Claude makes most execution decisions (how); domain expertise — not SE background — predicts output per instruction and success; debugging share nearly halved over seven months while end-to-end use (deploy/run, data analysis, docs) and estimated task value (+25% vs freelance postings) rose; non-developer occupations succeed at near-engineer rates when paired with domain knowledge.

Key takeaway: "persistent returns to expertise" reframes SE-for-Humans: the scarce input is judgment and context, not keystrokes — strong support for SASE's mentor/orchestrator framing of ACE.

---

## Limitations and what was excluded

- Cutoff enforced: nothing published before Oct 2025. Notably excluded: the original SWE-bench papers, early SWE-agent / Devin reports, and the May 2025 Darwin-Gödel Machine preprint (revised Mar 2026 but out of scope as a v1-2025 publication) despite its relevance to self-improving agents.
- One thin spot: communication-protocol standards (MCP/A2A/AGENTS.md-style context files) moved fast in this window but the strongest write-ups were vendor docs and evolving specs rather than stable peer-reviewed reads; Fan (#4) and CooperBench (#3) cover the durable design lessons without pinning a transient spec version.
- All arXiv metadata re-checked 2026-09-30; Anthropic page fetched same day. Findings summarized from abstracts and publisher summaries, not full-paper replication.
