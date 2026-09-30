# After the SASE paper: ten high-value recent reads on agentic software engineering

_Research date: 2026-09-30_

## Bottom line

The most important progress since the SASE paper is not simply that coding models score higher. The field is starting to treat the **whole engineering system**—model, harness, durable context, execution environment, feedback, human authority, and evolving repository—as the unit that must be designed and evaluated.

Five themes now have unusually strong evidence or practitioner agreement:

1. **The harness matters as much as the model.** Model-only comparisons hide large effects from context, tools, isolation, task decomposition, and feedback loops.
2. **Durable state beats conversational memory.** The strongest long-running systems externalize intent, progress, decisions, tests, and project knowledge into versioned artifacts that a fresh agent can inspect.
3. **Operational agency and governance authority are different.** Agents can initiate and execute work while humans retain responsibility for acceptance and merge.
4. **One-shot correctness is a poor proxy for software engineering.** Current agents struggle with multi-release evolution, and their code tends to bloat and structurally erode across repeated extensions even when checkpoints pass.
5. **Verification and security have to be designed into the runtime.** Tests alone miss architectural decay, and natural engineering inputs such as issues, comments, and attachments are now an attack surface.

That is a striking validation of the SASE paper's basic direction. The newer literature mainly sharpens the mechanisms, supplies empirical evidence for the gaps, and exposes failure modes that a disciplined coordination layer must address.

## Scope and selection method

I treated [*Agentic Software Engineering: Foundational Pillars and a Research Roadmap*](https://arxiv.org/abs/2509.06216) as the seed, not as one of the recommendations. I prioritized work connected to its core concerns: agent execution environments, human command and oversight, structured artifacts and handoffs, long-running work, trustworthy change, and meaningful evaluation.

The date window is **2025-09-30 through 2026-09-30**, inclusive. For arXiv papers I used the first-submission date, not a later revision date; for articles I used the displayed publication date. The seed paper's original arXiv submission was 2025-09-07, so it sits just outside this strict window.

The list is intentionally mixed:

- two unusually informative practitioner case studies;
- two position papers that clarify the field's unit of analysis and human-centered objectives;
- six empirical or systems papers covering context, coordination, long-horizon evolution, code quality, benchmark validity, and security.

“Recent” does not mean “settled.” Most research papers below are preprints, and the two vendor articles describe successful internal experiments rather than controlled neutral studies. I call out the main caveat for each item.

## The ten recommendations

### 1. [Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/)

**Ryan Lopopolo / OpenAI — 2026-02-11 — engineering article**

**Why start here:** This is the closest concrete implementation report I found to the SASE thesis. Three engineers report building an internal product of roughly one million lines and about 1,500 pull requests without manually written code. More important than the headline are the mechanisms: the repository becomes the system of record; a short `AGENTS.md` is a map rather than an encyclopedia; plans and decisions are versioned; documentation is checked and gardened; isolated worktrees expose logs, metrics, and traces to agents; architectural invariants are enforced mechanically; and recurring maintenance agents perform “garbage collection” on drift.

**What is genuinely useful:** The article explains why **agent legibility** is a first-class property of a codebase. Facts in chat, private documents, or a developer's head effectively do not exist for the running agent. Progressive disclosure plus executable constraints scales better than a giant prompt. Its inner lesson is that the human role shifts from typing implementation to designing a repository and feedback environment in which reliable implementation is the path of least resistance.

**SASE connection:** ACE/AEE separation becomes “humans steer, agents execute”; execution plans resemble durable BriefingScripts; repository-local evidence and automated checks resemble a continuously assembled merge-readiness surface.

**Caveat:** This is a first-party success report on a greenfield internal product. The claimed 10× speedup lacks a controlled counterfactual, and the setup received exceptional infrastructure investment. Read it for design patterns, not a general productivity estimate.

### 2. [Position: Coding Benchmarks Are Misaligned with Agentic Software Engineering](https://arxiv.org/abs/2606.17799)

**Maria I. Gorinova et al. — 2026-06-16 — position paper, SE 3.0 workshop**

**Why it matters:** This is the cleanest measurement-oriented continuation of the SASE paper. Its central claim is that a coding agent in practice is a **system harness**: models, agent harnesses, tasks, environment, context, and feedback over time. Current leaderboards usually collapse those components into one score and then attribute the result to the model. The paper shows that a fixed model can differ by 20 percentage points or more across harnesses on the same task distribution.

The authors separate feedback into useful time scales: fast inner-loop signals such as tests and types, middle-loop signals such as reviewer feedback and maintenance agents, and slow outer-loop outcomes such as reverts, incidents, and user response. They then identify three benchmark failures: model/harness conflation, anchoring evaluation to one reference implementation, and the absence of component-level diagnostic signal.

**What to take away:** “Did it pass?” is necessary but insufficient. A serious agent platform should record the model, harness, environment, context, and verifier versions; evaluate components as well as the integrated workflow; and prefer behavioral or invariant-based verification that admits multiple sound implementations.

**SASE connection:** The paper explicitly cites SASE's claim that passing tests is not merge readiness. It gives a rigorous vocabulary for why receipts, evidence packs, independent verifiers, and host-level orchestration should be evaluated separately.

**Caveat:** It is a position paper, not a new controlled benchmark study. Some evidence comes from the authors' own NS2 system and synthesized comparisons of prior results. Its remedies are persuasive but still need operational validation.

### 3. [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

**Anthropic Engineering — 2025-11-26 — engineering article**

**Why it matters:** This is the most compact practical account of making work survive context boundaries. Anthropic found that compaction alone did not prevent agents from attempting too much, leaving half-finished states, forgetting what happened, or declaring success prematurely. Their solution uses an initializer agent followed by incremental coding sessions, with a structured feature list, progress file, git history, reproducible startup script, and end-to-end tests as the handoff medium.

**What is genuinely useful:** A fresh session first reconstructs state, verifies that the baseline still works, selects one unfinished feature, and leaves a clean, documented state for its successor. The durable environment—not the model's conversational continuity—is the memory. The article also shows why explicit user-level testing tools matter: unit tests and `curl` can pass while the feature is visibly broken.

**SASE connection:** It is a small, legible demonstration of single-turn agents coordinated through durable artifacts and mechanical continuation. Its feature ledger and progress file are primitive versions of typed task state, evidence, and handoff artifacts.

**Caveat:** This is a vendor case study centered on one web-application build and one evolving model/harness family. It demonstrates feasibility and useful failure modes, not the optimal architecture for every repository.

### 4. [Humans are Missing from AI Coding Agent Research](https://arxiv.org/abs/2608.12355)

**Zora Z. Wang et al. — 2026-07-04 — position paper**

**Why it matters:** The paper argues that the bottleneck is moving from raw task completion toward whether people can communicate with, supervise, verify, and trust coding agents. It proposes four measurable interaction dimensions: **task alignment, steerability, verifiability, and adaptability**. This is a better target than maximum solo autonomy because it treats collaboration as a capability rather than a temporary concession to weak models.

The discussion of verifiability is particularly valuable. Even successful agent patches tend to be larger than the human reference patches, increasing review burden and making mistakes harder to detect. A system can therefore improve benchmark success while becoming less usable by its human verifier.

**SASE connection:** This supplies a human-centered research vocabulary for the Agent Coach and ACE side of SASE. Consultation, interruption, review surfaces, provenance, and bounded delegation are not UI polish; they determine system utility.

**Caveat:** The four dimensions are a research agenda and partial formalization, not a validated complete taxonomy. The paper is strongest as a corrective lens and source of testable questions.

### 5. [SlopCodeBench: Benchmarking How Coding Agents Degrade Over Long-Horizon Iterative Tasks](https://arxiv.org/abs/2603.24755)

**Gabriel Orlanski et al. — 2026-03-25 — empirical benchmark paper**

**Why it matters:** Most benchmarks reset after one issue. SlopCodeBench instead makes agents repeatedly extend their own earlier solutions under evolving requirements, allowing architectural decisions to compound. In the current revision, 15 agents face 36 problems and 196 checkpoints. No agent completes a whole problem; the best passes 14.8% of checkpoints. Structural erosion rises in 77% of trajectories and verbosity in 75.5%. Against 473 open-source Python repositories, agent code is reported as 2.3× more verbose and 2.0× more structurally eroded.

The most sobering result is that explicit quality guidance improves the initial code but does not stop the degradation rate. Better prompting is not enough; longitudinal maintenance and architectural feedback need to be part of the system.

**SASE connection:** This supplies evidence for continuous verification, scheduled cleanup, architecture-aware checks, and durable quality state. A merge-ready change can still make the next change harder, so evidence needs a time horizon longer than one patch.

**Caveat:** “Verbosity” and “structural erosion” are useful proxies, not a complete definition of maintainability. The benchmark's iterative tasks are more controlled than the social and operational evolution of a real production repository.

### 6. [Codified Context: Infrastructure for AI Agents in a Complex Codebase](https://arxiv.org/abs/2602.20478)

**Aristidis Vasilopoulos — 2026-02-24 — systems experience paper**

**Why it matters:** This paper turns “context engineering” into an explicit three-tier design: an always-loaded project constitution (“hot memory”), task-selected specialist agents, and on-demand subsystem specifications (“cold memory”). The author reports 283 sessions while constructing a 108,000-line C# distributed system, supported by 19 specialists and 34 specification documents. Retrieval hooks and file-based triggers route tasks to relevant knowledge, while a context-drift detector warns when source changes without corresponding specification updates.

**What is genuinely useful:** The distinction between a concise always-loaded constitution and deeper selectively loaded knowledge is practical and easy to reason about. The key reframing is that project documentation becomes **runtime infrastructure written for machine consumption**, with loading strategy, provenance, and maintenance cost—not just prose written after the code.

**SASE connection:** This closely parallels core versus reference memory, specialized skills, retrieval audits, and project-level orchestration. It is likely to provoke concrete comparisons about what should always be in context, what should be pulled on demand, and how drift should be detected.

**Caveat:** It is a single-author, single-project observational report in a documentation-heavy domain. There is no control group, and the author explicitly notes that team-scale and cross-project generalization remain untested.

### 7. [SWE-EVO: Benchmarking Coding Agents in Long-Horizon Software Evolution Scenarios](https://arxiv.org/abs/2512.18470)

**Tue Le et al. — 2025-12-20 — empirical benchmark paper**

**Why it matters:** SWE-EVO reconstructs version-level evolution work from release notes and histories of seven mature Python projects. Its 48 tasks span an average of 21 files and are checked by test suites averaging 874 tests. In the latest paper revision, GPT-5.4 with OpenHands resolves 25%, versus a reported 72.8% for GPT-5.2 on SWE-bench Verified. The precise model comparison will age; the durable finding is the large gap between isolated issue repair and coordinated software evolution.

The paper's **Fix Rate** is also worth studying. It credits partial progress only while preserving all previously passing regression tests, exposing work that a binary resolved/not-resolved score hides. Trajectory analysis shows an uncomfortable tradeoff: attempts that make more progress on new behavior can break more existing behavior.

**SASE connection:** It gives an evaluation shape for goals that span multiple patches, evolving specifications, dependency ordering, and partial but non-regressive progress. Those are closer to real plan/phase execution than a single issue benchmark.

**Caveat:** The benchmark has only 48 tasks, all in Python, and 26 come from one repository (DVC). Fix Rate still measures tests rather than maintainability or architectural fit.

### 8. [What Does an Agentic Software Engineering Benchmark Measure? Profiling Task Demands and Agent Behaviour Beyond What Category Labels Reveal](https://arxiv.org/abs/2609.01271)

**Radin Shayanfar, Keheliya Gallaba, and Ahmed E. Hassan — 2026-09-01 — empirical paper**

**Why it matters:** This is a direct update from one of the SASE paper's authors. The paper argues that labels such as “bug fix” and “feature implementation” conceal what work a benchmark actually demands. It proposes a **Spread–Novelty–Centrality (SNC)** profile: how dispersed the change is, how much new code it introduces, and how architecturally significant the touched code is.

Across five benchmarks and 14,922 trajectories, every benchmark pair differs on at least two SNC axes, including benchmarks with the same nominal label. Successful runs concentrate in low-SNC regions across model families, while successful behavior differs by family: Claude tends toward reference-patch scope parity as scale grows, whereas Qwen succeeds while overproducing. Task wording also materially shapes patch scope.

**What to take away:** Estimate task topology before delegation rather than relying on its ticket label. Spread and centrality can guide model choice, review intensity, conflict risk, and whether to decompose work. Per-model scope behavior should be configurable rather than hidden behind one universal prompt.

**SASE connection:** SNC suggests concrete metadata for task routing and risk-aware orchestration. It also reinforces that agent trajectories reveal demands that the gold patch alone cannot.

**Caveat:** All five evaluated benchmarks are Python-only and cover issue resolution or feature implementation. Language-aware analysis and broader task classes are needed before treating SNC as universal.

### 9. [Collaborator or Assistant? How AI Coding Agents Partition Work Across Pull Request Lifecycles](https://arxiv.org/abs/2605.08017)

**Young Jo(seph) Chung and Safwat Hassan — 2026-05-08 — AIware 2026 empirical paper**

**Why it matters:** This paper analyzes 29,585 pull-request lifecycles across five tool families and separates **who initiates the work** from **who authorizes completion**. Collaborator-style workflows are at least 96% agent-initiated, yet terminal merge authority remains overwhelmingly human. The paper's most useful conceptual result is that agency and governance decouple.

This is stronger than asking whether a tool is “autonomous.” It yields operational questions: Which work is agent-initiated? Where does review enter? Who endorses the result? Who merely executes the merge command? How much review capacity does the generated work consume?

**SASE connection:** It empirically supports distinct execution and acceptance layers. An agent may have broad operational initiative without inheriting the human or host's authority to declare a change acceptable.

**Caveat:** The data are concentrated in 2025 Q2–Q3, OpenAI accounts for 70.5% of the analytic sample, and GitHub events expose executors more reliably than decision-makers. The authors also cannot measure review depth from event occurrence alone.

### 10. [IssueTrojanBench: Benchmarking AI Coding Agents Against Malicious Issue Requests](https://arxiv.org/abs/2607.20759)

**Ankur Singh, Jinqiu Yang, and Tse-Hsun Chen — 2026-07-22 — security benchmark paper**

**Why it matters:** Agentic software systems ingest natural-language issues, comments, PDFs, and other artifacts while holding tools and local access. IssueTrojanBench treats those ordinary workflow inputs as attack vectors. It evaluates Cursor, Claude Code, and Codex Desktop across four attack categories and six delivery mechanisms; the authors report that 66.5% of malicious issues penetrate the tested model- and agent-level guardrails. Rejection came mainly from the underlying models, with little additional protection attributable to the agent frameworks.

**What to take away:** An issue is untrusted input, not merely a work order. Reliable agent execution needs least-privilege tools, sandboxing, explicit authority boundaries, provenance, approval gates for high-impact actions, and evaluation of the deployed model–harness pair. A prompt instruction to “be safe” is not a security architecture.

**SASE connection:** This provides a concrete threat model for gates, typed privileges, audited reads, isolated workspaces, and host-owned side effects. Structured artifacts improve coordination, but every artifact entering an execution environment also needs a trust classification.

**Caveat:** This is a new preprint with a constructed adversarial suite. The striking aggregate penetration rate should be independently replicated and interpreted per attack severity and deployment configuration, not as a universal compromise probability.

## Suggested reading order

If time is scarce, read **#1, #2, #4, and #5** first. Together they cover the working system, the evaluation problem, the human collaboration objective, and the longitudinal quality failure.

For an implementation-focused second pass, read **#3, #6, and #10**: durable handoffs, tiered project knowledge, and security boundaries.

For an evaluation and orchestration pass, read **#7, #8, and #9**: long-horizon progress, task topology, and the separation of operational initiative from merge authority.

## Synthesis: what changed over the year

The SASE paper proposed that agentic software engineering would require new actors, processes, tools, and artifacts. The last year did not produce a single settled architecture, but it did produce a much more concrete consensus about the substrate:

- **Actors:** The interesting actor is no longer an isolated model. It is a model–harness–environment system participating in a human-governed organization.
- **Processes:** Work increasingly looks like durable state transitions with incremental progress, independent checks, bounded authority, and explicit escalation—not a long chat session.
- **Tools:** Repositories, worktrees, CI, observability, issue trackers, sandboxes, and policy gates are becoming parts of the agent runtime rather than background developer tooling.
- **Artifacts:** Plans, progress ledgers, decision records, specifications, test evidence, trajectories, and provenance are executable coordination surfaces. Their freshness and trustworthiness matter as much as their existence.

The biggest unresolved problem is now easier to state: **how do we convert human intent and engineering taste into verifiable constraints without over-prescribing the implementation?** That question appears in different forms across nearly every recommendation—behavioral benchmarks, architectural invariants, reviewable patches, project constitutions, human-centered objectives, and security policies.

My strongest conclusion is that SASE's durable coordination layer is directionally ahead of much of the literature, but the newer work suggests three areas worth especially close attention:

1. longitudinal code-health signals that can detect compounding erosion, not merely patch correctness;
2. task-risk metadata based on spread, centrality, novelty, permissions, and trust provenance;
3. explicit measurement of human verification cost and authority, not just agent throughput.

Those three dimensions—future maintainability, task topology, and governance burden—are where “structured agentic software engineering” most clearly separates itself from simply running more coding agents.
