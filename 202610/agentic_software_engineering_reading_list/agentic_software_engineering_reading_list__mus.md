# Recent Agentic Software Engineering: Research Reading List

Researcher: mus (swarm researcher, independent report)
Date: 2026-10-10
Scope: best recent (published within the last year, i.e. after 2025-10-10) articles
related to agentic software engineering. Candidates were checked against Bryan's
Bob reference library via `bob ref find` before ranking; items already finished
were excluded from the recommendations.

## Method

1. Web-searched for 2026 papers, surveys, benchmarks, and practitioner pieces on
   coding agents, harness engineering, context engineering, multi-agent SE, and
   empirical studies of agentic coding.
2. Assembled 14 candidates and ran them through `bob ref find` in a single
   batched lookup.
3. Result: 3 of 14 already in the library (2 finished, 1 queued from the legacy
   backlog); 1 title-similarity-only hit that is a different document (docs page,
   not the research paper); 10 absent from `ref/`.
4. Verified the top-ranked survey and the multi-agent skeptical result against
   their arXiv abstract pages for authors, dates, and claims.

## Already in your library (excluded from recommendations)

- **Harness Engineering: Anatomy, Architecture, and Evolution of Coding Agents —
  A Source-Code Study of Eleven Systems** (Barbaste et al., arXiv:2609.00006) —
  finished 2026-10-10. The empirical anchor for this whole area; no need to
  re-recommend.
- **An Architecture for Long-Horizon Agents: Levels, Ticks and Cascaded
  Intelligence** (Nijkamp et al., arXiv:2609.19519) — finished 2026-10-10.
- **Building Effective AI Coding Agents for the Terminal** (OpenDev,
  arXiv:2603.05344) — already in your library (queued since 2026-03-29, legacy
  backlog). Still worth reading given the SASE terminal/TUI overlap; included
  below as a labeled carry-over, not a fresh recommendation.

## Ranked recommendations

### 1. From Question Answering to Task Completion: A Survey on Agent System and Harness Design
Guo et al., arXiv:2606.20683 (14 Jun 2026). Companion list:
`github.com/ggjy/Awesome-Agent-Engineering`.
The single best start. First survey to treat harness design as its own subject:
model-plus-harness lens, four paradigms of agent engineering, six coupled
runtime responsibilities (observation, context, control, action, state,
verification), and open problems in value-aware evaluation, safety, harness
generalization, and model-harness co-evolution. Maps directly onto SASE's
harness-vs-model questions. Not in library.

### 2. Agentic coding and persistent returns to expertise (Anthropic research)
Anthropic, June 2026: `https://www.anthropic.com/research/claude-code-expertise`.
Analysis of ~400,000 Claude Code sessions from ~235,000 users (Oct 2025–Apr
2026). Core findings: humans keep planning authority ("what to do") while the
agent handles execution ("how to do it"); domain expertise predicts success
better than a software-engineering background; average task value rose ~25%
over seven months while debugging time nearly halved. The largest public
empirical dataset on agentic coding behavior. Library lookup returned only
title-similar docs pages, not this paper — treated as not in library.

### 3. Components of a Coding Agent (Sebastian Raschka)
Magazine piece, ~April 2026:
`https://magazine.sebastianraschka.com/p/components-of-a-coding-agent`.
Practitioner anatomy in six components: agent harness, tool calling, context
management, memory, planning, execution environment — framed as a three-layer
model/agent-loop/runtime architecture. Thesis: what looks like a smarter model
is usually a better harness. Short, concrete, and the natural companion to
rank 1. Not in library.

### 4. Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?
Gloaguen et al., arXiv:2602.11988 (Feb 2026), with AGENTBENCH (real-world
GitHub issues from repos with developer-written context files).
Counterintuitive result: auto-generated repo context files *reduced*
coding-agent success ~3% and raised inference cost 20%+, while human-written
files improved success ~4%. Directly relevant to SASE's instruction-file and
default-config delivery work. Not in library.

### 5. At Equal Inference Cost, Multi-Agent Structure Does Not Beat a Single Frozen Agent
Dylan et al., arXiv:2609.04217 (submitted 25 Jun 2026). MA-Evolve optimizes
Planner–Executor–Critic role prompts by coordinate ascent over a frozen 7B
backbone at fixed total LM-call budget: full team 0.769 vs single executor
0.754 (p = 0.80) despite 1.8x more eval calls; planner and critic evolve to
near-empty prompts. Sobering evidence for the research-swarm and macro-swarm
architecture debates: multi-agent gains may be compute gains in disguise. Not
in library.

### 6. Agentic Harness Engineering: Observability-Driven Automatic Evolution of Coding-Agent Harnesses
Lin et al., arXiv:2604.25850 (2026). Evolves a coding-agent harness from
observability signals; reported Terminal-Bench 2 lift 69.7 → 77.0. The most
actionable "harness that improves itself" result for SASE's own harness work.
Not in library.

### 7. Meta-Harness: End-to-End Optimization of Model Harnesses
arXiv:2603.28052 (2026). Outer-loop harness optimization reporting +27 on
SWE-bench. Pairs with rank 6: two independent 2026 lines of evidence that the
harness, not the model swap, is where benchmark points come from. Not in
library.

### 8. Agentic Design Patterns
arXiv:2601.19752 (2026). Twelve formal design patterns for agentic coding
systems. Pattern-catalog form makes it easy to map SASE mechanisms (holds,
gates, monitors, swarms) onto named industry patterns and spot gaps. Not in
library.

### 9. Self-Evolving Coding Agents (survey)
arXiv:2608.03392 (v1 4 Aug 2026). Surveys coding agents that adapt memory,
skills, tools, frameworks, or collaboration structure from prior coding
interactions, organized around executable feedback, repo context,
trajectories, reliability, safety, maintainability, cost, and
generalization. The forward-looking complement to rank 1. Not in library.

### 10. LLM-Based Agentic Systems for Software Engineering: Challenges and Opportunities
Tang & Runkler, arXiv:2601.09822 (Jan 2026). Systematic review of multi-agent
LLM systems across the full SDLC (generation, testing, debugging) plus
benchmarks and frameworks. Broadest SDLC coverage of the list; best if only
one systematic-review slot is available alongside the harness-focused rank 1.
Not in library.

### 11. SWE Refactor Bench: Can Coding Agents Complete a Long-Horizon, Whole-Repository Stack Migration?
2026 (HuggingFace papers page `2608.23564`). Whole-repo stack-migration
benchmark — long-horizon, full-repo tasks rather than single-issue fixes.
Closest benchmark to SASE-scale autonomous work (epics, migrations). Related
alternatives worth knowing: DeepSWE, RepoRescue, ChainSWE. Not in library.

### 12 (carry-over, already queued). Building Effective AI Coding Agents for the Terminal
OpenDev, arXiv:2603.05344 — already in your library (queued since 2026-03-29,
legacy backlog). Seven-subsystem harness model plus context-engineering layer
and lessons learned. Recommend promoting it from the backlog queue rather
than re-adding.

## Suggested capture lines (for Bryan, optional)

```bash
bob ref create https://arxiv.org/abs/2606.20683
bob ref create https://www.anthropic.com/research/claude-code-expertise
bob ref create https://magazine.sebastianraschka.com/p/components-of-a-coding-agent
bob ref create https://arxiv.org/abs/2602.11988
bob ref create https://arxiv.org/abs/2609.04217
bob ref create https://arxiv.org/abs/2604.25850
bob ref create https://arxiv.org/abs/2603.28052
bob ref create https://arxiv.org/abs/2601.19752
bob ref create https://arxiv.org/abs/2608.03392
bob ref create https://arxiv.org/abs/2601.09822
```

## Caveats

- All dates, author lists, and finding summaries above come from web search
  snippets and two arXiv abstract verifications (ranks 1 and 5); I did not
  read the full papers. Treat quoted numbers (e.g. Terminal-Bench 69.7 →
  77.0, +27 SWE-bench) as reported claims, not verified results.
- `bob ref find` covers notes under `ref/` only; absence there is not proof an
  item was never read (per the skill's coverage note), and the legacy backlog
  may hold related material under different keys.

Library check: 3 of 14 candidates already in your library (2 finished).
