**Reading toward a SASE essay about durable goals, human understanding, and trustworthy completion**

Independent research by cdx · 2026-10-24  
Reading-history window: 2026-04-24 through 2026-10-24.

The most promising direction for your blog is to explain how SASE helps a person retain coherent control of engineering work as execution becomes increasingly automated. Your recent annotations already contain that argument. In your Gas Town notes, you object to treating every completed agent as an urgent demand on your attention: “You need to check on goals, not individual agents!” The best next readings develop that instinct into a design vocabulary: shared goals, recoverable context, understandable changes, and evidence that an outcome actually happened.

My recommendation is to start with **Ten Challenges for Making Automation a “Team Player”**, **Understanding is the new bottleneck**, and **Reality Is the Final Verifier**. The first is absent from your reference index; the latter two are already queued. If you want an entirely new-to-the-index starter set, read **Ten Challenges**, **Why Do Multi-Agent LLM Systems Fail?**, and **Programming as Theory Building**. “Absent” here means absent from the indexed library, not proof you have never read something.

I researched independently. I did not consult the other researchers’ reports, transcripts, summaries, or findings.

I reviewed the requested directories through `bob ref` and read-only `bob query`, using completion state rather than file modification time or publication date. The bounded history query was:

```sh
bob ref list -o external -R finished -t blogs,papers -S 2026-04-24 -g -n 150 -f json
```

It returned **25 completed records**, without truncation: 13 blogs and 12 papers. Four “papers” were versions of your own CV; excluding these leaves **21 relevant external readings**. Seventeen completion dates came from reading tasks, including those four CVs. Eight came from Git history, all dated October 3; these are approximate historical evidence, not eight confidently known reading sessions on that day. The earliest explicit completion in the selected records is June 11. This does not establish that you read nothing in April or May.

The broader type-filtered query also returned 66 undated legacy records under `ref/zorg/`. I checked the exact `ref/blogs/` and `ref/papers/` directories with Dataview and excluded those legacy records from the requested six-month cohort. Unmigrated records outside `ref/` and unscreened intake are outside the index’s coverage. I did not modify the vault. Annotations are the latest scanned snapshots, not live PDF state.

This is the complete relevant cohort, with short local note names so you can reproduce a lookup using `bob ref show <path> -c -f markdown`. “Git” denotes the inferred completion date.

| Completion | Reading | Note under ~/bob/ref/ |
| --- | --- | --- |
| Oct 23 | Agentic coding is straining CI. Here’s how we scaled test impact analysis at Anthropic | `blogs/agentic_coding_is_straining_ci_heres_how_we_scaled_test_impact_analysis_at.md` |
| Oct 23 | How the Claude Code team does code review | `blogs/solving_code_review_at_anthropic.md` |
| Oct 21 | Redesigning source control at Anthropic | `blogs/redesigning_source_control.md` |
| Oct 19 | Gas Town Emergency User Manual | `blogs/gas_town_emergency_user_manual.md` |
| Oct 16 | Diátaxis compass and how-to | `blogs/diataxis_fr_compass_and_howto.md` |
| Oct 16 | Karpathy’s llm-wiki.md | `blogs/karpathy_llm_wiki.md` |
| Oct 16 | The Coming Loop | `blogs/the_coming_loop.md` |
| Oct 13 | Goals as First-Class Abstractions in Human-AI Collaboration | `papers/2026_goals_as_first_class_abstractions_in_human_ai_collaboration_automationxp26.md` |
| Oct 11 | The natural home for AI agents is your Reminders app | `blogs/reminders.md` |
| Oct 10 | An Architecture for Long-Horizon Agents: Levels, Ticks and Cascaded Intelligence | `papers/an_architecture_for_long_horizon_agents_levels.md` |
| Oct 10 | Harness Engineering: Anatomy, Architecture, and Evolution of Coding Agents | `papers/harness_engineering.md` |
| Oct 10 | The Dot and the Swarm | `blogs/the_dot_and_the_swarm.md` |
| Oct 3, Git | An open-source spec for Codex orchestration: Symphony | `blogs/open_source_codex_orchestration_symphony.md` |
| Oct 3, Git | EA-Graph: Artifact-Anchored Verification Memory for Coding Agents under Upstream Drift | `papers/ea_graph.md` |
| Oct 3, Git | Filesystem-Based Memory for LLM Agents: Organization, Evolution, and Sustainability | `papers/filesystem_memory.md` |
| Oct 3, Git | Harness engineering: leveraging Codex in an agent-first world | `blogs/harness_engineering.md` |
| Oct 3, Git | Human-Inspired Memory Architecture for LLM Agents | `papers/human_mem_arch.md` |
| Oct 3, Git | Memory OS of AI Agent | `papers/memory_os.md` |
| Oct 3, Git | netclode | `blogs/netclode.md` |
| Oct 3, Git | The Log is the Agent | `papers/log_is_the_agent.md` |
| Jun 11 | Steve Kinney’s agent memory systems article | `blogs/steve_kinney_agent_memory.md` |

The four excluded completed CV records are `BryanBugyi_CV_extended.md`, `_v3.md`, `_v4.md`, and `_v5.md`, completed October 12–13. The v2 record was queued, so it was never part of the 25.

Your comments provide stronger evidence of direction than the titles alone. I read the commented annotations for Gas Town, goals, source control, code review, CI, long-horizon architecture, The Log is the Agent, and Kinney’s memory article. I also checked the library record for your own SASE essay and the three queued recommendations below.

| Your annotation or reaction | What I infer from it | Reading that develops or challenges it |
| --- | --- | --- |
| Gas Town: supervise goals instead of every agent completion | You want attention to follow outcomes and decisions | Ten Challenges; Ironies of Generative AI |
| Goals paper: link goals to originating prompts, evaluate alignment, preserve why goals changed | Provenance and revisable intent matter beyond task completion | Reality Is the Final Verifier; Ten Challenges |
| Code-review article: noisy agent findings resemble your mentor-loop problem | Reviewer output has downstream cost; more review can produce more work | MAST; Minions Part 2 |
| The Log is the Agent: interest in tool-call replay | Reconstructing execution and proving success are separate concerns | End-to-End Arguments |
| Long-horizon architecture: periodic progress checkpoints for unfinished goals | Continuity should survive individual runs | Ten Challenges; Programming as Theory Building |
| Source-control article: interest in changesets, read tracking, and component monitoring | You are connecting execution with durable evidence | End-to-End Arguments; Minions Part 2 |

These are my interpretations of your notes, not a claim that you have endorsed the proposed designs. Some highlighted material consists of images with no textual comment; I did not invent opinions from those images.

I also read the local launch essay, `docs/blog/posts/structured-agentic-software-engineering.md`, and portions of the orchestration and planning drafts. The launch essay has a good concrete opening: the tmux window farm stops being sufficient. It then spends much of its space on providers, syntax, interface navigation, and installation. Those details explain how to use SASE, but they leave room for a stronger explanation of **why this particular structure should exist**.

A possible central claim, in your own eventual wording, is: *As coding becomes easier to delegate, the engineering system must preserve the connection between a person’s intent, the work being attempted, and the evidence used to judge the result.* That is an editorial synthesis, not an established research result.

SASE already has relevant architectural commitments. I checked the audited project memories for the goal ledger, single-turn agents, host-owned completion, and verification receipts. Goals are person-owned outcome records distinct from agent liveness. Continuation outlives a provider turn through host mechanisms. Completion requires host-selected finalizers and verified postconditions. Receipts concern an exact verification fingerprint and do not skip execution. These are useful concrete examples for the essay, although the project’s own design records are not independent validation that the system improves productivity.

The readings suggest three productive tensions to explore.

First, **durability has to preserve meaning as well as bytes**. Naur’s theory-building argument challenges the assumption that collecting code, prompts, and documentation is enough to retain the understanding needed to change a system. Litt supplies practical ways to help people build that understanding. My application to SASE is to make an important completion artifact explain the purpose of a change, its governing assumptions, and how to explore it—not merely preserve the transcript. This is a research-inspired suggestion, not a claim about an existing feature. [Naur’s original essay, readable transcription](https://pablo.rauzy.name/dev/naur1985programming.pdf), [Litt’s article](https://www.geoffreylitt.com/2026/07/02/understanding-is-the-new-bottleneck).

Second, **goal supervision still needs an intelligible route down to evidence**. A top-level green status can hide uncertainty just as effectively as a wall of terminal windows. A useful blog demonstration would follow one real task through a changed assumption, an interrupted run, a successor’s recovery, and the final human judgment. Show how someone answers “what changed, what remains uncertain, and what decision is mine?” without rereading every conversation. The coordination literature motivates these questions; whether SASE answers them well needs a demonstration or measurement. [Klein et al., Ten Challenges](https://doi.org/10.1109/MIS.2004.74).

Third, **completed execution, verified implementation, and satisfactory outcome require different evidence**. A finished process does not establish that a change satisfies the person’s intent. An effective test suite still approximates the deployed environment and the desired behavior. The end-to-end argument helps explain where a guarantee must be checked; the two-gap paper explains why even that check remains revisable in an open world. This makes a persuasive account of host-owned completion possible without suggesting it proves all software correct. [Saltzer, Reed, and Clark](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf), [Krentsel et al.](https://arxiv.org/html/2609.12039v1).

For the blog, I would emphasize one completed engineering story and one failure story. Explain which responsibility sits with the provider CLI, which sits with the SASE host, and which remains a human judgment. Let the feature details support those stories. A useful later evaluation would compare how long it takes you to reconstruct a paused task, identify a changed assumption, or decide what to do next. Other candidate measures are human minutes per accepted outcome, review rounds per accepted change, and the fraction of notifications that lead to a useful decision. These are proposed measures, not results I collected.

I would also resist turning these readings into an immediate infrastructure expansion. You have already read extensively about memory systems and harnesses. The higher-value next step for the essay is a clearer account of responsibility and evidence. New agent roles, memory machinery, and dashboards should have to earn their place against that account.

I selected the final list for immediate usefulness to the blog, conceptual distance from your recent reading, practical applicability to SASE, and strength of evidence. Older work ranks highly when it supplies a missing concept. The list includes conceptual arguments, empirical studies, and engineering reports; their evidential limits are different.

The library audit batched all eleven works, using titles plus URL/arXiv/DOI identities. A second complete batch added the renamed journal version of the scaling paper and the skill-formation article’s alternate title and URL. It contained 26 queries representing eleven works. The three “possible” title matches were confirmed with `bob ref show` and exact URL matches. All were queued, none finished or dropped. No legacy queued item appears in this shortlist. Intake was reported as not checked.

Source access was sufficient for the recommendations, with two qualifications. The author-site copy of Ten Challenges returned an error; I read the original paper from a coauthor’s ResearchGate PDF. The Naur scan was poorly text-extractable through the browser; I retrieved and extracted the readable PDF transcription directly. The Nature version of the scaling paper was available as indexed publisher text, while direct open hit its access redirect; I also inspected arXiv v3. I used MAST v3 rather than its older search-result abstract. I did not reproduce numerical claims from obsolete versions.

The ranked reading list follows. Reading times are my rough estimates for a focused first pass.

1. **[Ten Challenges for Making Automation a “Team Player” in Joint Human-Agent Activity](https://doi.org/10.1109/MIS.2004.74)** — Gary Klein, David D. Woods, Jeffrey M. Bradshaw, Robert R. Hoffman, and Paul J. Feltovich. *IEEE Intelligent Systems*, November–December 2004, pp. 91–95. **Absent from your reference index.** About 20 minutes. [Free coauthor-hosted PDF](https://www.researchgate.net/profile/David-Woods-19/publication/3454232_Ten_Challenges_for_Making_Automation_a_Team_Player_in_Joint_Human-Agent_Activity/links/0c96052164a74da6ab000000/Ten-Challenges-for-Making-Automation-a-Team-Player-in-Joint-Human-Agent-Activity.pdf).

   This is the strongest new conceptual addition. The paper treats joint activity as requiring shared commitments, predictability, directability, and maintained common ground. Its challenges include visible intentions, goal negotiation, and attention management. Read the whole short paper, particularly challenges 5, 7, 9, and 10.

   **For SASE and the essay:** use it to ask whether the human can understand and redirect the work without monitoring every action. Your goal-centered reaction to Gas Town becomes a concrete design question. A compelling example would show an agent communicating a newly discovered obstacle and the host retaining that obligation across a restart.

   **Limit:** this is a conceptual human-factors framework from before LLMs. It supplies design criteria, not evidence that SASE or a particular coordination architecture satisfies them.

2. **[Understanding is the new bottleneck](https://www.geoffreylitt.com/2026/07/02/understanding-is-the-new-bottleneck)** — Geoffrey Litt, July 2026. **Already in your library, queued since 2026-10-07**; scheduled for October 25 when checked. About 15–20 minutes.

   Litt argues for understanding as a condition of creative participation. He demonstrates explanations organized around concepts, quizzes, and interactive micro-worlds. Read the “Why understand?” discussion and the examples; they are more useful here than merely copying his skill.

   **For SASE and the essay:** this gives your artifacts a human purpose. A person should leave an agent-assisted change better able to propose the next change. Consider illustrating one explanation that helped you learn a subsystem, and describing what you could do afterward.

   **Limit:** this is a practitioner account, not a controlled comparison. Quizzes can also create friction or reward superficial recall. Treat the particular techniques as experiments, not universal approval requirements.

3. **[Reality Is the Final Verifier: On Two Key Gaps in Agentic Software Engineering](https://arxiv.org/abs/2609.12039)** — Alexander Krentsel and colleagues, September 10, 2026, arXiv preprint. **Already in your library, queued since 2026-10-10**; scheduled for November 7 when checked. About 30 minutes. [Full text](https://arxiv.org/html/2609.12039v1).

   The paper distinguishes the gap between requirements and stakeholder intent from the gap between a modeled environment and deployment reality. It proposes revising requirements, models, and evaluators using observed outcomes. Prioritize sections 2, 5, and 6.2–6.4.

   **For SASE and the essay:** use this to explain why an accepted plan and passing tests do not settle every question. My application is to tell a story in which deployment evidence or a human objection changes the goal’s interpretation, and show how that history remains available.

   **Limit:** this is a conceptual research agenda. It does not demonstrate that a goal ledger closes either gap. Its value is making the limits of automation explicit enough to design around.

4. **[Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657)** — Mert Cemri and colleagues, 2025; inspected arXiv v3, October 26, 2025. **Absent from your reference index.** About 25–35 minutes for the main argument and taxonomy. [Full text](https://arxiv.org/html/2503.13657v3).

   MAST organizes fourteen failure modes into system design issues, inter-agent misalignment, and task verification. The current version describes more than 1,600 annotated traces across seven frameworks. Read Figure 1, section 4, and the intervention case studies.

   **For SASE and the essay:** this is a disciplined alternative to explaining every failure as a weak model. Map one actual SASE incident to a lost handoff, misread instruction, repeated step, or premature termination. Then explain the specific structural change that would prevent recurrence. Your noisy-review-loop observation is a natural starting point.

   **Limit:** trace labels and LLM-based annotation are imperfect, and the tested systems and model generations differ from current SASE. The paper’s failure percentages are not estimates of SASE’s reliability.

5. **[Programming as Theory Building](https://pages.cs.wisc.edu/~remzi/Naur.pdf)** — Peter Naur, *Microprocessing and Microprogramming*, 1985. **Absent from your reference index.** About 25 minutes. [Readable transcription used for this report](https://pablo.rauzy.name/dev/naur1985programming.pdf).

   Naur argues that programming includes developing the understanding that lets people explain a system, relate it to the world, and modify it coherently. Program text and documentation alone do not convey all of that understanding. Focus on “The Theory To Be Built by the Programmer” and “Program Life, Death, and Revival.”

   **For SASE and the essay:** this is a useful challenge to your interest in durable memory. Saving all the artifacts is valuable; you still need to explain how someone acquires the understanding needed to act on them. A strong blog example would involve a successor recovering the reason behind a design decision.

   **Limit:** this is a philosophical account with historical examples. It does not establish an empirical ceiling on modern AI, and should not be cited as proving that machines cannot understand programs.

6. **[Minions: Stripe’s one-shot, end-to-end coding agents—Part 2](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2)** — Alistair Gray, February 19, 2026. **Already in your library, queued since 2026-10-11.** About 15 minutes. Your reading task depends on Part 1, which is also queued.

   Stripe describes blueprints that interleave deterministic operations with agent loops, isolated developer environments, fast local feedback, and bounded CI repair. Its standard flow returns a branch for human scrutiny after the second push and CI run. Focus on “Blueprints” and “… and iterate.”

   **For SASE and the essay:** this provides an engineering comparison for deciding what the host should own. It also makes bounded review and repair easier to explain in light of your mentor-loop concern. Describe the responsibility split and its costs, rather than copying Stripe’s scale claims.

   **Limit:** this is a company-authored operational report, not a controlled benchmark. Stripe’s existing developer infrastructure is a major precondition; its throughput does not predict the benefit of a local installation.

7. **[Ironies of Generative AI: Understanding and mitigating productivity loss in human-AI interactions](https://arxiv.org/abs/2402.11364)** — Auste Simkute, Lev Tankelevitch, and colleagues, February 17, 2024, preprint. **Absent from your reference index.** About 25 minutes. [Full text](https://arxiv.org/html/2402.11364v1).

   This synthesis connects generative AI to earlier human-factors research. It examines the shift from producing work to evaluating it, workflow disruption, interruption costs, and changes in task difficulty. Sections 3.3–3.5 discuss interface design, interruption timing, and clear task allocation.

   **For SASE and the essay:** use it to evaluate the notifications promise. A notification is useful when it helps you make or resume a decision. More visibility can still impose more attention costs. One interesting comparison would be a stream of individual completions versus a concise account of what changed for one goal.

   **Limit:** much of the underlying evidence concerns earlier assistants and adjacent domains. It motivates hypotheses about SASE’s interface, not a proven optimal notification policy.

8. **[How AI Impacts Skill Formation](https://arxiv.org/abs/2601.20245)** — Judy Hanwen Shen and Alex Tamkin, 2026; inspected v2. **Absent from your reference index**, including the companion article’s alternate title. About 15 minutes for the [authors’ research summary](https://www.anthropic.com/research/AI-assistance-coding-skills), or 30 minutes for the [paper](https://arxiv.org/html/2601.20245v2).

   A randomized study of developers learning an unfamiliar asynchronous-programming library found weaker subsequent learning with AI assistance and no statistically significant overall completion-time improvement. Interaction patterns involving conceptual engagement were associated with stronger learning than wholesale delegation.

   **For SASE and the essay:** pair this with Litt. Completion speed and retained competence are separate outcomes. You could describe how you use agents differently when learning an unfamiliar subsystem versus carrying out work you already understand.

   **Limit:** the short task and immediate quiz do not measure months of professional development or SASE usage. The interaction-pattern analysis is exploratory, not a randomized demonstration that a particular explanation feature fixes the problem.

9. **[End-to-End Arguments in System Design](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf)** — Jerome H. Saltzer, David P. Reed, and David D. Clark; 1981 conference paper, expanded in *ACM Transactions on Computer Systems*, 1984. **Absent from your reference index.** About 20–30 minutes.

   The paper examines functions whose complete correctness depends on knowledge at the application endpoints. Lower layers can help, but their guarantees may not establish the application’s intended result. Read the careful file-transfer example and the discussion of acknowledgments.

   **For SASE and the essay:** this is a precise analogy for host-owned completion. A successful tool call, an agent’s final message, and an accepted engineering result represent different boundaries. Explain which postconditions the host can check and what still needs a person’s judgment. Likewise, replaying a tool result reconstructs evidence; it does not automatically establish that a fresh external action is safe.

   **Limit:** this is an application of a systems-design argument to SASE, not a theorem about agent architecture. The original paper discusses tradeoffs rather than a universal rule to move everything upward.

10. **[Capable language models can outgrow the benefits of collaboration](https://www.nature.com/articles/s42256-026-01268-y)** — Yubin Kim and colleagues, *Nature Machine Intelligence*, July 24, 2026. Preprint title: **[Towards a Science of Scaling Agent Systems](https://arxiv.org/abs/2512.08296)**. **Absent from your reference index under both titles and identities.** About 30–40 minutes; prioritize the results and limitations. [Accessible preprint full text, v3](https://arxiv.org/html/2512.08296v3).

    The study compares coordination architectures under matched resource constraints and finds that collaboration’s benefit depends on task structure and the single-agent baseline. The journal version explicitly frames its empirical threshold as a practical selection rule, not a universal scaling law.

    **For SASE and the essay:** fan-out is a capability whose value should be demonstrated on a suitable task. Independent research, separable implementation, and tightly coupled sequential debugging need not use the same coordination structure. This supports explaining your routing choices instead of equating larger swarms with progress.

    **Limit:** benchmark results and fitted thresholds should not become hard-coded defaults. Within-domain architecture selection is better supported than predicting absolute performance in new domains; the findings do not directly evaluate SASE’s heterogeneous workflows.

11. **[Ironies of Automation](https://gwern.net/doc/sociology/technology/1983-bainbridge.pdf)** — Lisanne Bainbridge, *Automatica* 19(6), 775–779, 1983. **Absent from your reference index.** About 15–20 minutes.

    Bainbridge examines the problems created when automation leaves people responsible for unusual failures while reducing their routine practice and awareness. Her discussion of monitoring, takeover, and training remains a useful lens for supervisory software.

    **For SASE and the essay:** ask what a user can do when the ordinary automatic path breaks. A recovery story should show what information survives, how the person regains context, and which actions remain available. This makes the human role concrete.

    **Limit and reason for ranking:** industrial-process and aviation examples do not transfer mechanically to coding. It also overlaps with number 7 and the skill-formation paper, so it is a short historical deepening after the more directly applicable readings.

Library check: 3 of 11 candidates already in your library (0 finished).
