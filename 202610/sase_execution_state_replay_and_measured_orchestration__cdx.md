# SASE’s next readings: execution state, replay, and measured orchestration

Independent research by **cdx**, 2026-10-07. Sources were checked against the versions available on that date. This report was researched independently; no other researcher’s report or findings from this swarm were consulted.

**My recommendation is to make explicit execution state and evaluation the next research priorities.** SASE already has durable records, isolated workspaces, multiple providers, audited artifacts, and host-owned completion. Its next opportunity is to use those records to show agents which observations remain current, make recovery boundaries explicit, and measure whether context and orchestration improve completed work. The ranked readings below provide both promising mechanisms and evidence that some common agent practices fail to deliver their expected benefits.

The three readings I would start with are Ledger, VibeMemBench, and the September revision of Evaluating AGENTS.md. Together they ask a useful sequence of questions: what does the agent know about its current execution; does persistent experience improve executable work; and does the instruction context help enough to justify its cost? The later selections connect these questions to replay, authority, model routing, and multi-agent coordination. These priorities are my inference for SASE, not conclusions established about SASE by the papers.

I used the supplied [SASE reading history](sase_related_reading_history.md), accessed through the audited reference research:202610/sase_related_reading_history.md, and checked the current Bob reference library. The history suggests that replay deserves particular attention: your annotations on The Log is the Agent and Gas Town independently asked about replaying tool calls and restarting materialized workflow steps. You have already finished Symphony, Harness Engineering, the filesystem-memory study, EA-Graph, MemoryOS, and Human-Inspired Memory Architecture. I treat those as background rather than recommend them again.

The library lookup covered **18 candidates in one batch**. Three are already queued: Managed Agents, Harness design for long-running application development, and Demystifying evals for AI agents. None of the 18 is marked finished. The other fifteen are absent from the ref/ index; that does **not** establish that you have never read them, particularly given the older reading records outside that index. Two queued items remain in the main ranking because their architectural relevance is unusually strong.

For project context I inspected this checkout’s README and documentation on ToolRuns, monitors, goals, model routing, and architecture, plus the audited decisions on single-turn agents, host-owned completion, corpus before mechanism, and receipts before reuse. Relevant public documentation includes [ToolRuns](https://sase.sh/tool/), [monitors](https://sase.sh/monitors/), and [provider configuration](https://sase.sh/llms/). This is a reading and design assessment, not an implementation or benchmark reproduction.

**The most useful distinction for the replay direction is between four different operations.**

| Operation | What it accomplishes | Implication for SASE |
| --- | --- | --- |
| Inspect recorded output | Displays evidence from a completed execution | ToolRun output playback already provides this; it does not execute the command again. |
| Reconstruct control state | Restores ownership, settled outcomes, checkpoints, and continuation lineage | SASE’s monitor continuation and parent-history mechanisms already address parts of this. |
| Replay observations in isolation | Supplies recorded model/tool responses to reproduce an earlier path | Requires a defined capture boundary and explicit handling of filesystem, process, and external state. |
| Resume or selectively recompute work | Performs new work from a selected step or changed artifact | Requires dependency invalidation, fresh admission, and side-effect policy; a prior transcript alone is insufficient. |

This distinction prevents an attractive replay feature from silently acquiring verification-cache or duplicate-effect semantics. SASE’s receipt decision explicitly keeps every tool invocation executing its child. It reopens reuse only after measured opportunity and a hermeticity proof. Ledger’s governing mechanism includes suppression of repeated commands, so its design cannot be imported wholesale under that contract. Its execution-state presentation is a useful experiment that can be studied separately.

Likewise, SASE already retains evidence when reducing continuation context. Managed Agents offers a related architectural model: preserve the durable session independently of the particular context slice a harness presents. The new research question is how to make the *current implications* of that evidence visible across turns without claiming that a summary is authoritative or complete. [Managed Agents architecture](https://www.anthropic.com/engineering/managed-agents)

I would investigate the following bounded experiments before undertaking a larger architecture change. These are proposed measurements, not filed tasks or claims that the features are currently missing:

| Experiment | Comparison and outcome | Decision it could inform |
| --- | --- | --- |
| Execution-state view | Keep execution unchanged; add a compact view of observed file coverage, intervening changes, attempted commands, and explicit uncertainty. Measure stale reads, repeated work, resolved tasks, and total cost. | Whether mechanically derived state belongs in successor context. |
| Context and memory ablation | Hold host enforcement constant. Compare current context, a smaller set of necessary instructions with audited references, and curated relevant experience. Use repeated, held-out tasks and check both task success and workflow compliance. | Which information deserves always-loaded placement; whether memory construction or delivery is the bottleneck. |
| Recovery fault matrix | Interrupt before launch acknowledgement, after a side effect but before its receipt, during checkpoint publication, and while a recovery is itself interrupted. Check preserved evidence, duplicate effects, ownership, and typed uncertainty. | What each recovery boundary actually guarantees. |
| Small artifact-lineage pilot | Use one already-existing multi-step workflow. Change an intermediate artifact and identify the dependent work, leaving unrelated outputs intact. Begin with isolated, non-effectful computation. | Whether materialized steps and dependency identities justify selective recomputation. |
| Routing and swarm economics | Compare task-level routes and independent versus coordinated agent configurations under matched budgets and host resources. Include cache behavior, review time, correction chains, and final accepted outcomes. | When another model or agent pays for itself. |

A practical starting corpus could be a small collection of actual SASE failures and manually checked workflows, with reference outcomes and repeated trials. The eval guidance already queued in your library recommends starting from real failures and separating one successful attempt from consistent success across attempts. That is a useful companion to SASE’s existing deterministic checks: it evaluates the behavior of the agent-plus-host system rather than just the code it produced. [Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)

There are several evidence limits that affect the ranking. Ledger uses one run per SWE-bench instance per configuration. VibeMemBench deliberately selects cases where useful experience exists, and its reported transfer-gain confidence intervals include zero. The execution-lineage study has only two controlled memo-update tasks. Routing savings come from an emulation and repricing, with strong assumptions about model capability and session shape. These are reasons to borrow experimental methods and challenge mechanisms locally, rather than project their percentage gains onto SASE.

I also checked the current revisions instead of relying on search snippets. **Evaluating AGENTS.md v3, dated September 29, says that context files do not generally improve success; it does not establish that all instruction files are harmful.** **Harness Tokenomics v2, dated September 26, has a different title from the original indexed version, Control the Harness, Control the Cost.** The ranking uses the current titles and results. arXiv items are treated as preprint evidence unless a venue is explicitly identified; vendor articles are primary engineering accounts, not independent comparative trials.

Six other checked candidates did not make the main twelve:

| Candidate | Why it remains secondary |
| --- | --- |
| [Do Context Files Help Coding Agents?](https://arxiv.org/abs/2607.27250), Prakhar Khatri, July 28, 2026 | A valuable companion to rank 3: 288 runs, but only 17 tasks from three repositories. Its 10–15 percentage-point equivalence bounds leave smaller effects unresolved. |
| [Configuration Smells in AGENTS.md Files](https://arxiv.org/abs/2606.15828v5), dos Santos et al., revised July 30, 2026; SCAM 2026 listed | Useful for reviewing generated instructions, but prevalence of configuration smells is not evidence of their causal effect on coding success. |
| [Harness Engineering for Predictable Agentic Systems](https://arxiv.org/abs/2608.26197), Saransh Dhage, August 25, 2026 | Structured-plan validation is interesting, and first-pass constraints sometimes worsened reproducibility. Two synthetic finance/legal tasks limit direct coding applicability. |
| [Deterministic Replay for AI Agent Systems](https://arxiv.org/abs/2607.16200), Rasheed Mudasiru | agrepl provides network record/replay, but its limitations explicitly exclude filesystem mutations and database writes. Those omissions matter greatly for coding-agent replay. Its displayed April submission date also differs from the July identifier/indexing metadata; I would verify bibliographic details before formal citation. |
| [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), Anthropic, January 9, 2026 | Already in your library, queued since January 11, legacy backlog. Excellent practical preparation for the experiments above, but less novel than the targeted papers. |
| [Building a C compiler with a team of parallel Claudes](https://www.anthropic.com/engineering/building-c-compiler), Nicholas Carlini, February 5, 2026 | Worth a targeted skim for test-oracle design: many agents duplicated work when all encountered one blocking bug, and a differential compiler oracle enabled decomposition. A compelling case study, but the main list emphasizes transferable mechanisms and controlled comparisons. |

**Ranked reading list.** The ordering combines immediate SASE relevance, additional value beyond your completed reading, empirical strength, and likely payoff per reading effort. “Absent from index” below means no match in the checked Bob ref/ library, not proven unread.

1. **[Turning Interaction History into Execution State: A Runtime Layer for Long-Horizon Coding Agents](https://arxiv.org/abs/2608.00808)** — Zehao Wang et al.; August 1, 2026; arXiv preprint. **Absent from index.**

   **Why read it:** Ledger directly addresses the gap between a durable transcript and a usable account of current execution. It separates an inform path that presents runtime state from a govern path that mediates repeated work, with no additional model calls. Across 500 SWE-bench Verified tasks, reported Pass@1 rises from 56.2% to 64.2% for GPT-5 mini and from 75.8% to 81.0% for MiniMax M2.5; a Codex transfer test also improves.

   **SASE payoff:** Study the observation/change/command representation as a possible foundation for cross-turn state views and better checkpoints. Keep command suppression separate from receipt semantics.

   **Read critically:** The estimates use single runs per instance; the main domain is Python issue repair. Tracked repository changes are not a complete model of external state. Start with the state representation, inform/govern ablations, and limitations. [Full text](https://arxiv.org/html/2608.00808v1)

2. **[VibeMemBench: Evaluating Memory Systems for Coding Agents on Real Repository Coding Tasks](https://arxiv.org/abs/2609.23570)** — Liyang Fan et al.; September 20, 2026; arXiv preprint. **Absent from index.**

   **Why read it:** It tests whether memory improves executable repository work, rather than recall alone. On 111 targets from 90 repositories, four memory systems fail to beat the matched memory-off baseline in eleven of twelve model/system pairings. Directly supplied verified experience shows small directional gains on four of five transfer solvers, but all five transfer confidence intervals cross zero.

   **SASE payoff:** This is the strongest methodological follow-up to your completed MemoryOS and filesystem-memory reading. It separates whether useful historical experience exists from whether a memory system delivers it effectively.

   **Read critically:** Targets were selected for demonstrated memory usefulness in a reference setting; retrieval is performed before the coding trajectory, and resource reporting excludes memory-side token costs. Start with the intervention contract, results, and record-form failure analysis. [Full text](https://arxiv.org/html/2609.23570v1)

3. **[Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?](https://arxiv.org/abs/2602.11988v3)** — Thibaud Gloaguen et al.; February 12, revised **September 29, 2026**; arXiv preprint. **Absent from index.**

   **Why read it:** This challenges one of SASE’s most consequential interfaces. The latest version finds no general task-success improvement from context files and over 20% higher inference cost on average. Agents follow instructions and explore/test more, but repository overviews are ineffective. Developer-written files outperform generated files without establishing a significant advantage over no file.

   **SASE payoff:** Use its ablations to evaluate generated core context and on-demand references. Preserve unusual workflow requirements and host boundaries while measuring whether explanatory material deserves prompt space.

   **Read critically:** CTXbench is Python-focused; task resolution does not measure all security, maintainability, or policy-compliance benefits. The paper does not support deleting SASE’s single-turn or completion requirements. Read v3’s behavioral analysis and limitations rather than the older negative headline. [Full text](https://arxiv.org/html/2602.11988v3)

4. **[From Agent Loops to Deterministic Graphs: Execution Lineage for Reproducible AI-Native Work](https://arxiv.org/abs/2605.06365)** — Josh Rosen and Seth Rosen; May 7, 2026; arXiv preprint. **Absent from index.**

   **Why read it:** It develops the closest conceptual continuation of your Gas Town annotation about materialized workflow steps. Artifact-producing computations have explicit dependencies and identities; an update can propagate through affected work while preserving unrelated artifacts.

   **SASE payoff:** It supplies a vocabulary and evaluation criteria for restart-from-step and partial recomputation: dependency isolation, preservation of unaffected work, and cross-artifact consistency. SASE’s artifact references provide a starting point, but artifact identity alone is not a complete execution identity.

   **Read critically:** This is a mechanism study with two policy-memo tasks, three repeats, and one model family. Correct graph specification is assumed; coding performance and multi-round drift are not established. Read execution identity, invalidation, and the maintained-state metrics first. [Full text](https://arxiv.org/html/2605.06365v1)

5. **[Mnemosyne: Agentic Transaction Processing for Validating and Repairing AI-generated Workflows](https://arxiv.org/abs/2607.00269v3)** — Edward Y. Chang and Longling Geng; June 30, revised August 31, 2026; arXiv preprint. **Absent from index.**

   **Why read it:** Its central architecture closely matches host-owned completion: generated actions remain proposals until deterministic admission checks them against effective state and executable constraints. Repairs must re-enter admission, preserve evidence, and respect dependencies.

   **SASE payoff:** Use it to scrutinize the boundaries between continuation, finalizer declaration, admission, and committed state. It is especially relevant to stale recovery and failures that arrive during another recovery.

   **Read critically:** Guarantees are relative to the declared constraints and deployment assumptions. Bounded safety experiments do not establish general production correctness; complete physical-effect and temporal-exception paths remain partly specified rather than tested. At 60 pages, prioritize the admission model, interruption stress tests, and evidence-status qualifications. [Full text](https://arxiv.org/html/2607.00269v3)

6. **[Harness Tokenomics: A Router for the Enterprise Agentic Control Plane](https://arxiv.org/abs/2609.28919v2)** — Ted Kwartler, Alan Aqrawi, and Arian Abbasi; September 24, revised September 26, 2026; arXiv preprint. **Absent from index.**

   **Why read it:** It treats routing as a multi-request, cache-sensitive decision. It favors session starts, independent lanes, and subagent launches as routing boundaries; a cheaper token rate can lose its advantage when switching rebuilds context or causes correction work.

   **SASE payoff:** SASE already routes among models and records usage. The useful next measurement is completed-work cost, including cache reads/writes, retries, and review, rather than a model’s advertised price alone. Subscription capacity should also be accounted for separately from API dollars.

   **Read critically:** The claimed 13–21% savings come from an enterprise emulation, not a live quality-controlled deployment. Model-quality and token-use assumptions, dated prices, and session distributions substantially affect the result. Read cache payback and limitations; borrow the method rather than the dollar projections. [Full text](https://arxiv.org/html/2609.28919v2)

7. **[Beyond Single-Use Tokens: Durable Authorization State for Replay-Resistant LLM Agent Actions](https://arxiv.org/abs/2608.01710)** — Jinghan Xu et al.; August 3, 2026; arXiv preprint. **Absent from index.**

   **Why read it:** A new token can still repeat the same authorized action after replanning, delegation, concurrency, or a crash. CapLease binds consumption to the authorization instance and canonical action, with durable Issue–Prepare–Commit state.

   **SASE payoff:** This is the necessary companion to replay and automatic recovery. It provides concrete questions for launch approvals and finalizers: what action was approved, how much execution remains authorized, and which identity survives an uncertain retry?

   **Read critically:** A comparably stateful server ledger achieves the same protection; the essential contribution is durable consumption state, not a special token format. Exactly-once external effects also require an idempotent destination, and canonicalization/trusted-contract errors remain relevant. Read the crash case and non-idempotent-destination negative control. [Full text](https://arxiv.org/html/2608.01710v1)

8. **[Scaling Managed Agents: Decoupling the brain from the hands](https://www.anthropic.com/engineering/managed-agents)** — Lance Martin, Gabe Cemaj, and Michael Cohen; April 8, 2026; Anthropic engineering article. **Already in your library, queued since April 17, legacy backlog.**

   **Why read it:** It separates durable session events, the replaceable model harness, and execution environments. The log survives a harness crash; context transformation is distinct from retained history; execution resources can be provisioned independently.

   **SASE payoff:** It is a strong architectural comparison for provider adapters, mechanical successors, remote execution, and retained continuation evidence. Stable interfaces can survive improvements in models and changes in harness behavior.

   **Read critically:** This is a hosted production account, not a comparative benchmark or evidence that SASE should adopt the service. Some reset machinery became unnecessary as models improved, but SASE’s single-turn contract also serves ownership and lifecycle requirements. Read the session/context distinction and independently replaceable components first.

9. **[Understanding Agent Scaling in LLM-Based Multi-Agent Systems via Diversity](https://arxiv.org/abs/2602.03794)** — Yingxuan Yang et al.; February 3, 2026; arXiv preprint. **Absent from index.**

   **Why read it:** It explains diminishing returns from correlated agents and tests model/prompt diversity under matched agent-call budgets. In its experiments, two diverse agents can match or outperform sixteen homogeneous agents.

   **SASE payoff:** It gives a research basis for evaluating SASE’s multi-provider swarms. Measure distinct useful evidence and error correlation, not just the number of reports. Independent investigation, as used in this swarm, can preserve diversity for later synthesis.

   **Read critically:** The core tests are reasoning/knowledge tasks with small open-weight models, with additional API-model checks; they do not establish results for repository editing. Its embedding-based effective-channel metric measures semantic variation, which need not mean correctness. Read matched-budget comparisons and the distinction between correct and incorrect path diversity. [Full text](https://arxiv.org/html/2602.03794v1)

10. **[Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)** — Prithvi Rajasekaran; March 24, 2026; Anthropic engineering article. **Already in your library, queued since March 28, legacy backlog.**

    **Why read it:** Planner, generator, and evaluator agents agree on sprint criteria before implementation; the evaluator exercises the running application. This is a practical account of making completion criteria observable and improving feedback beyond an agent’s self-assessment.

    **SASE payoff:** It could inspire artifact-based acceptance contracts for larger work and evaluation of actual product behavior alongside code checks. The distinction between product scope and detailed implementation prescriptions is especially useful for plan workflows.

    **Read critically:** The comparison also changes time, spend, and scope: one highlighted full-harness run costs $200 over six hours versus $9 over twenty minutes for a solo run. It is not an isolated causal test of three-agent superiority, and evaluators required calibration. Read contracts, evaluator failures, and harness simplification.

11. **[Scaling LLM-Driven Multi-Agent Systems: Design Principles and Architectural Scalability Analysis](https://arxiv.org/abs/2607.27942)** — Linus Sander et al.; July 30, 2026; arXiv preprint. **Absent from index.**

    **Why read it:** It compares increasingly complex terminal-task workflows and reports a capability threshold: scaling helps the stronger baseline but not the weakest one, while the largest configuration loses ground through timeouts. Repeated runs also expose inconsistent task success.

    **SASE payoff:** This complements rank 9 with tool-using engineering tasks. Evaluate role structure, feedback loops, and execution budgets together; agent count is an incomplete design variable.

    **Read critically:** The main scaling sweep is within one model family, with a frontier reference configuration; broader provider generalization remains open. The architecture is largely sequential, so its results do not directly predict SASE’s concurrent independent workers. Read actual topology, timeout accounting, consistency, and cost tables. [Full text](https://arxiv.org/html/2607.27942v1)

12. **[Quantifying infrastructure noise in agentic coding evals](https://www.anthropic.com/engineering/infrastructure-noise)** — Gian Segato; February 5, 2026; Anthropic engineering article. **Absent from index.**

    **Why read it:** Controlled Terminal-Bench experiments show a six-percentage-point spread between the least- and most-resourced environments. Resources can both prevent infrastructure failures and enable different solving strategies.

    **SASE payoff:** This is essential reading before judging routing or swarm changes on a shared server. Pin resource allocations, headroom, time limits, and concurrency; retain infrastructure outcomes separately from agent reasoning failures.

    **Read critically:** The measurements come from Anthropic’s environment and do not prove the same effect size on SASE. Avoid importing a universal headroom multiplier. Read the distinction between reserved resources and kill thresholds, then the proposed empirical calibration procedure.

Library check: 3 of 18 candidates already in your library (0 finished).
