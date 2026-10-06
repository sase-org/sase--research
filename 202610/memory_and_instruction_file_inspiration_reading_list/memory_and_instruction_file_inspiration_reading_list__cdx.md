# Recent reading to improve SASE memory and agent instruction files

Researcher: **cdx**  
Research date: **2026-10-06**  
Publication window: **2025-10-06 through 2026-10-06**, inclusive by calendar date.

## Assessment

The most promising reading concerns the quality of the existing files: what deserves always-loaded context, how an agent discovers the right reference, how edits preserve useful knowledge, and how to measure whether a rule helps. SASE already has a substantial foundation: core/reference separation, keyword-addressed memory webs, authored links, audited reads, controlled writes, and immutable decision records. A new memory product or speculative retrieval layer is unlikely to be the most useful first inspiration.

My recommended starting trio is **Writing a good CLAUDE.md**, **Harness engineering**, and **Filesystem-Based Memory for LLM Agents**. Together they offer practical editing judgment, maintenance mechanisms, and evidence about the benefits and limits of organized Markdown memory. The final section ranks ten readings; the accompanying studies below explain why the ranking does not simply follow promotional claims.

This is an independent report. I did not consult any other researcher in this swarm or their reports, transcripts, or summaries. SASE-specific observations use the instructions supplied with the request and audited reads of `sase_artifacts.md`, `decisions:corpus-before-mechanism`, and `decisions:memory-links-are-authored`. This is a reading recommendation, not an implementation plan or an audit of the memory renderer's code.

## Selection method

I searched for recent work on `AGENTS.md`, `CLAUDE.md`, procedural skills, agent memory, and filesystem context. I prioritized original engineering articles and research papers, opened the primary sources, checked their publication dates, and inspected relevant methods and limitations. Long papers were reviewed through their abstracts and relevant sections rather than every appendix. Search-engine publication estimates were not treated as definitive dates.

Ranking weighs **direct relevance to SASE**, **likely new insight beyond its current design**, **concrete authoring or maintenance ideas**, and **strength of evidence**. Papers are included alongside articles and are identified as such. Vendor implementation reports are useful inspiration but do not establish universal causal effects. Reading times below are my estimates for the recommended sections.

## The ten strongest candidates

### A. Writing a good CLAUDE.md

**Kyle, HumanLayer — November 25, 2025. Practitioner article; approximately 10 minutes.**

The article recommends a small, broadly applicable entry file, task-specific Markdown references, pointers to authoritative material, and deterministic formatting tools. It explicitly extends its advice to `AGENTS.md`. Its case against accumulating a new permanent instruction after every annoyance is particularly useful. [Primary article](https://www.humanlayer.dev/blog/writing-a-good-claude-md).

**SASE inspiration:** Review each core paragraph for whether it changes a common decision or merely explains a rare situation. Compare overlapping home/project policy blocks and ask whether their duplication has a necessary scope. Preserve critical lifecycle and authorization rules while investigating redundant wording.

**Qualification:** This is experienced authoring advice. Its numerical instruction-count and line-count heuristics are not universal limits. Read the sections on applicability, progressive disclosure, and linting; take the editorial principles more seriously than a fixed size target.

### B. Harness engineering: leveraging Codex in an agent-first world

**Ryan Lopopolo, OpenAI — February 11, 2026. Engineering case study; approximately 15 minutes for the relevant sections.**

The team describes moving from a large instruction manual to a short entry file backed by versioned repository documentation. More distinctive are mechanical checks of documentation structure and cross-links, verification status, and recurring maintenance that finds obsolete material. [Primary article](https://openai.com/index/harness-engineering/).

**SASE inspiration:** The section “We made repository knowledge the system of record” is the most valuable. Ask what existing SASE checks establish about rendered descriptions, reachable references, scoped rules, and stale guidance. A navigable index needs continuing maintenance, not only a good initial design.

**Qualification:** This is one internal product team's experience, not a controlled study of instruction-file length. Its throughput estimates and permissive merge practices should not be generalized to SASE. The useful transfer is document maintenance and enforceable feedback, not the whole operating model.

### C. Filesystem-Based Memory for LLM Agents: Organization, Evolution, and Sustainability

**Sizhe Zhou and colleagues — July 29, 2026, arXiv v1. Research preprint; approximately 25–35 minutes for §§2 and 4 plus selected examples.**

This unusually close match to SASE examines agent-managed Markdown stores, growth, search tools, and procedural memory. Organized stores can substantially reduce retrieval cost on large material, but organization does not reliably improve answer quality. Most management agents' organizational discipline deteriorates as the store grows; tool interfaces also shape the resulting files. [Paper, v1](https://arxiv.org/html/2607.26637v1).

**SASE inspiration:** Evaluate the existing corpus longitudinally. Useful outcomes include bytes read, unnecessary reads, survival of older facts, correct handling of changed facts, and task performance. Good-looking folders are insufficient evidence of good memory.

**Qualification:** Its conversational and embodied-task settings differ from SASE development work. Do not infer a guaranteed twofold saving for SASE, or that agent reorganization is automatically beneficial. The strongest transfer is its experimental questions and preservation checks.

### D. Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?

**Thibaud Gloaguen and colleagues, ETH Zurich/LogicStar — February 12, 2026, v1 reviewed. Empirical research paper; approximately 20 minutes.**

The evaluation covers SWE-bench Lite and 138 tasks from 12 Python repositories with developer context files. Generated files usually add cost and can reduce task success; human-written files have more modest, mixed benefits. Instructions influence exploration and testing, which can create overhead. [Paper, v1](https://arxiv.org/html/2602.11988v1).

**SASE inspiration:** Treat each standing requirement as a behavioral intervention. Its benefit may be correct policy adherence rather than a higher issue-resolution score. Compare retained safeguards with alternative wording and scope, and measure unnecessary testing or exploration as well as successes.

**Qualification:** The study is heavily Python-focused and does not comprehensively measure security, maintainability, or SASE lifecycle correctness. It does not justify deleting required controls. Read §§4–5 rather than relying on the headline that context files hurt.

### E. Introducing Context Repositories: Git-based Memory for Coding Agents

**Letta — February 12, 2026. Implementation article; approximately 10 minutes.**

Letta describes Git-backed memory as a local filesystem, with a permanently visible tree, frontmatter descriptions, selected always-loaded files, and workflows for reflection and reorganization. It illustrates how paths and descriptions act as the interface for discovering memory. [Primary article](https://www.letta.com/blog/context-repositories/).

**SASE inspiration:** Compare the usefulness of SASE's reference descriptions and strand labels with this design. Do their names tell an agent where the answer is, or merely which subsystem a note concerns? SASE already possesses much of the underlying architecture; discoverability is the more interesting comparison.

**Qualification:** This is a product design description, not evidence of improved correctness. Its autonomous moves, edits, and Git commits need adaptation to SASE's write procedure, immutable decisions, and host-owned completion. Its stated file-count target is not a general standard.

### F. Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models

**Qizheng Zhang and colleagues — first posted October 6, 2025; v3 March 29, 2026 reviewed. Research paper, marked ICLR 2026; approximately 20–30 minutes.**

ACE separates experience generation, reflection, and curation. It uses localized, itemized updates instead of repeatedly rewriting an entire playbook, addressing a documented failure in which accumulated context collapses into an impoverished summary. Entries have identifiers and helpful/harmful feedback; refinement controls redundancy. [Paper, v3 and publication history](https://arxiv.org/abs/2510.04618); [method](https://arxiv.org/html/2510.04618v3).

**SASE inspiration:** Examine memory maintenance as a knowledge-preservation problem. A proposed edit should explain the specific lesson, its scope, supporting experience, and what it replaces. Localized changes fit SASE's existing strands better than whole-corpus rewriting.

**Qualification:** The original date sits exactly at this report's inclusive cutoff. Benchmark improvements in AppWorld and domain reasoning do not predict SASE gains. Useful reference playbooks can grow without expanding always-loaded policy. Self-reported usefulness is also weaker evidence than independently checked outcomes.

### G. Evaluating Memory in Production Agents

**Letta — July 28, 2026. Evaluation article; approximately 10 minutes.**

This article distinguishes memory usage—retrieval and adherence—from memory generation—generalization and hygiene. Scenarios based on production traces include messy and cleaned-up memory profiles. Examples contrast deriving a reusable rule with simply appending another dated correction, and repairing scattered contradictions with leaving them in place. [Primary article](https://www.letta.com/blog/evaluating-memory-in-production-agents/).

**SASE inspiration:** These four categories form a useful review rubric. Can an agent find the applicable strand, obey it, derive an appropriately scoped lesson, and revise mutable guidance without damaging existing knowledge? Keeping them separate helps diagnose a failed memory change.

**Qualification:** This is a private benchmark using synthetic scenarios, a simulated user, and an LLM judge. The category design and failure examples are more portable than the provider rankings. Coding competence alone should not be assumed to establish memory-editing competence.

### H. SkillsBench: Benchmarking How Well Agent Skills Work Across Diverse Tasks

**Xiangyi Li and colleagues — first posted February 13, 2026; v4 June 14, 2026 reviewed. Benchmark paper; approximately 20 minutes for §§5–6.**

The reviewed version evaluates 87 tasks under 18 model/harness configurations. Curated skills raise average pass rate from 33.9% to 50.5%, while 13 tasks have negative deltas. Focused guidance generally outperforms exhaustive bundles; harmful skills can impose unnecessarily heavy procedures or displace better defaults. [Paper, v4](https://arxiv.org/html/2602.12670v4); [version history](https://arxiv.org/abs/2602.12670).

**SASE inspiration:** Evaluate procedural instructions with and without the relevant skill. Inspect applicability boundaries and whether a routine task is being forced through an expensive workflow. Useful instructions should explain when their specialized procedure is warranted.

**Qualification:** This is skill packaging, not an experiment on SASE's core/reference format. Skills may contain executable resources. Self-generated-skill results have discovery and creator/solver interference confounds; they do not prove that learning from verified past experience is impossible. Avoid mixing older 86-task statistics with this version.

### I. How To Give Your Agent Memory

**Jake Broekhuizen, LangChain — June 24, 2026. Engineering tutorial; approximately 6–8 minutes.**

The article separates a trace as evidence from a durable lesson that changes later behavior. Its loop captures traces, diagnoses causes, and updates context; many observations belong in history, evaluations, or tool fixes instead of memory. It also stresses that subsequent runs must actually load the new context. [Primary article](https://www.langchain.com/blog/how-to-give-your-agent-memory).

**SASE inspiration:** Repeated corrections deserve diagnosis before they become permanent rules. A failure could mean poor wording, a conflicting instruction, a missed read, or a tool defect. Evidence about the cause determines which file, skill, or implementation should own the remedy.

**Qualification:** The concrete implementation promotes LangSmith products, and the article supplies no controlled performance result. SASE can use the diagnostic reasoning with its existing artifacts and audited reads. No new platform or storage dependency is implied.

### J. Equipping agents for the real world with Agent Skills

**Barry Zhang, Keith Lazuka, and Mahesh Murag, Anthropic — October 16, 2025; portability update December 18, 2025. Engineering article; approximately 10 minutes.**

The article explains three levels of disclosure: discovery metadata, the main instruction body, and additional references/resources. It recommends evaluating actual capability gaps, inspecting usage trajectories, and making descriptions useful for choosing the right skill. [Primary article](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills).

**SASE inspiration:** Review a skill or reference description as routing instructions, not a summary alone. The agent should be able to distinguish “this is relevant now” from “this belongs to a vaguely related domain.” Distinguish factual references from procedures that coordinate commands.

**Qualification:** SASE already uses this general pattern, so the likely benefit is authoring precision rather than architectural novelty. The article explains a design and recommends evaluation; it is not itself a controlled demonstration of improved performance.

## Important companion articles and contrary evidence

These qualify by date but fall below the final ten for direct inspiration or add a narrower companion perspective.

| Article and verified date | What it adds; why it is not higher |
| --- | --- |
| [On the Impact of AGENTS.md Files on the Efficiency of AI Coding Agents](https://arxiv.org/html/2601.20404v1), Jai Lal Lulla et al., **2026-01-28** | Across 124 PR tasks in 10 repositories using one Codex configuration, median runtime fell 28.64% and median output tokens fell 16.58%. Comprehensive correctness evaluation was explicitly outside scope; a 50-task manual sanity check is not equivalent. Essential companion to D, but less useful as a file-authoring guide. |
| [Do Context Files Help Coding Agents? A Two-Agent Ablation Study on Real Repositories](https://arxiv.org/abs/2607.27250), Prakhar Khatri, **2026-07-28** | Two agents, 17 tasks, three repositories, 288 runs: no measurable correctness gain from the tested context strategies. Its equivalence bounds still allow effects up to roughly 10–15 percentage points. A useful counterweight to broad claims; the small task sample limits universality. Assessment here is based on the abstract. |
| [How to write a great agents.md: Lessons from over 2,500 repositories](https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/), Matt Nigh, **2025-11-19**, updated **2025-11-25** | Concrete commands, clear boundaries, and examples make useful editorial prompts. However, the examples are specialist Copilot profiles under `.github/agents/`, not simply an always-loaded root `AGENTS.md`. The repository analysis does not establish a controlled performance effect. |
| [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents), Justin Young, **2025-11-26** | Shows how progress records and explicit acceptance checks support fresh sessions. Useful when studying continuation artifacts, but less directly about durable memory authoring. SASE's host-owned finalization and single-turn contract change the application of its agent-commit and session-loop examples. |
| [Bad Memory: Evaluating Prompt Injection Risks from Memory in Agentic Systems](https://arxiv.org/abs/2607.14611), Soham Gadgil et al., **2026-07-16** | Studies persistent malicious payloads in a synthetic workspace. A narrow companion when considering provenance and memory-update controls; it should not displace the broader authoring and evaluation readings. Assessment here is based on the abstract. |

The studies do **not** jointly establish that instruction files are always beneficial or always harmful. They use different task selections, agents, outcomes, and experimental conditions. Efficiency, task correctness, policy adherence, and memory preservation are separate dimensions. SASE needs evidence about its own workload, including the behavior that ordinary coding benchmarks omit.

## Questions these readings suggest for SASE

These are my synthesis and candidate evaluation questions, not findings that the articles measured on SASE.

1. **Which text earns permanent context?** The supplied home and project sections repeat portions of memory, repository, and finalization policy. Is that repetition reinforcing essential scoped behavior or consuming attention without changing decisions? Any comparison should retain the host lifecycle, authorization, and audited-read requirements. The promising comparison is current rendering versus equivalent, less redundant rendering.

2. **Can an agent choose the right reference before it knows the terminology?** SASE's short descriptions and strand catalog are its discovery interface. A useful probe gives the agent a normal task description and checks whether it finds the right audited read, including when the user does not name a note or glossary term. Merely demonstrating retrieval after supplying the exact selector tests a different ability.

3. **Does a lesson have an applicability boundary?** Consider whether a mutable guidance note makes clear the triggering situation, the action to take, why that action is necessary, and the evidence for it. A reusable lesson should be more than a transcript of one correction, while preserving exceptions that matter. This is especially important for instructions that trigger expensive verification or require another skill.

4. **What survives maintenance?** Memory quality includes handling superseded facts, preserving uncommon but useful exceptions, and keeping links to authoritative evidence. SASE's accepted decision records have immutable semantics; updating operational guidance must not rewrite the history of a decision. A shorter output alone is not a successful maintenance result.

5. **Where should a remedy live?** A code defect, unavailable capability, misleading command schema, and unclear instruction can produce similar agent failures. A new core rule is only one possible remedy. SASE's existing separation among skills, reference notes, decisions, and host mechanisms supplies several possible owners for the fix.

6. **Does a change improve behavior across the supported harnesses?** A reference may be discoverable in one provider and missed in another. Hold task and repository state fixed when comparing context versions; repeat borderline tasks rather than attributing one lucky run to wording. Measure required-policy adherence, outcome quality, unnecessary reads/tool calls, latency, and context cost. Memory-use and memory-editing performance should be scored separately.

A useful distinction throughout is **short entry context versus rich retained knowledge**. Concise initial instructions and detailed, selectively read playbooks can coexist. Preserving an existing corpus does not require injecting all of it into every turn. This matches SASE's current separation and its corpus-before-mechanism decision; the article ideas are most valuable as tests of that design's execution.

## Sources excluded by the date requirement

- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents), Anthropic, **September 29, 2025**: relevant, but seven days outside the window.
- [Advanced Context Engineering for Coding Agents](https://www.humanlayer.dev/blog/advanced-context-engineering), HumanLayer, **August 29, 2025**: a frequently recommended precursor, but outside the window. The date is also displayed in the adjacent-post link on article A.
- [Benchmarking AI Agent Memory: Is a Filesystem All You Need?](https://www.letta.com/research/), Letta, **August 2025** as listed on its research index: related to C and E, but outside the window.

Undated or continuously updated product documentation can support implementation later, but it was not promoted into this dated reading list. Generic industry trend pieces and derivative summaries were not prioritized over original sources.

## Ranked list of articles to consider reading

1. **[Writing a good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)** — **2025-11-25**. Best immediate editorial lens for core context, duplicated guidance, and reference pointers.
2. **[Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/)** — **2026-02-11**. Best practical inspiration for checking and maintaining an agent-readable knowledge base.
3. **[Filesystem-Based Memory for LLM Agents: Organization, Evolution, and Sustainability](https://arxiv.org/html/2607.26637v1)** — **2026-07-29**. Closest empirical match to SASE's Markdown corpus; particularly useful for evaluating growth and preservation.
4. **[Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?](https://arxiv.org/html/2602.11988v1)** — **2026-02-12**. Strong corrective to the assumption that adding requirements always helps; read with the efficiency companion above.
5. **[Introducing Context Repositories: Git-based Memory for Coding Agents](https://www.letta.com/blog/context-repositories/)** — **2026-02-12**. Most concrete comparison for names, descriptions, pinned context, and memory organization.
6. **[Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models](https://arxiv.org/html/2510.04618v3)** — **2025-10-06**, reviewed revision **2026-03-29**. Best inspiration for learning through localized, knowledge-preserving edits.
7. **[Evaluating Memory in Production Agents](https://www.letta.com/blog/evaluating-memory-in-production-agents/)** — **2026-07-28**. Best compact rubric separating retrieval, adherence, generalization, and hygiene.
8. **[SkillsBench: Benchmarking How Well Agent Skills Work Across Diverse Tasks](https://arxiv.org/html/2602.12670v4)** — **2026-02-13**, reviewed revision **2026-06-14**. Most useful evidence for focused procedural guidance and applicability boundaries.
9. **[How To Give Your Agent Memory](https://www.langchain.com/blog/how-to-give-your-agent-memory)** — **2026-06-24**. Clearest short account of turning diagnosed experience into durable behavioral improvement.
10. **[Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)** — **2025-10-16**. Useful authoring guidance for discovery descriptions and selective reference loading, although much of the architecture is already present in SASE.
