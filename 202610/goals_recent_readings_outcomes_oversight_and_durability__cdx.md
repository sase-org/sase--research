# Ten recent readings for rethinking SASE Goals

Researcher: **cdx**  
Researched: **2026-10-05**  
Eligible publication window: **2025-10-05 through 2026-10-05, inclusive**

The most useful reading sequence is **1 → 2 → 3 → 4**: clarify the relationship between human intent and agent work, examine which orchestration machinery remains useful, distinguish completion evidence from completion claims, then consider how people actually supervise agents. The remaining articles broaden that foundation into continuing work, swarms, understandable systems, and durable execution.

This is a reading-selection report. Its conclusions concern which articles could improve your thinking; it does not propose a Goals implementation or revise your requirements.

**Context and selection method.** I read `~/tmp/incomplete_goals_prompt.md` and the historical shared [Goals epic roadmap](../202609/sase_goals_epic_roadmap/sase_goals_epic_roadmap.md), the latter through an audited artifact read. The draft raises lighter goal creation, a Goals-first interface, approval and verification queues, active-work heartbeats, permanent/service goals, goal hooks, clan launches, and cleanup of completed work. Its creation-origin list stops at “A”; I have not inferred the missing text. I used the roadmap to understand the subject, not to reassess the code or design. No report, transcript, summary, or finding from another researcher in this current swarm was consulted.

I searched primary engineering blogs, original research, and original usability reporting. For every final selection, I opened the publisher's article and checked its displayed publication date and relevant body sections. Search-engine “published” or “crawled” estimates were not used as the date authority. All ten articles are publicly readable, fall inside the window, and come from seven publishers. Ranking favors relevance to your particular uncertainties, strength of the underlying evidence, and additional perspective beyond the other selections; it is not a popularity or novelty ranking.

**What makes these readings useful together.** My interpretation is that your draft contains several different questions under the word “goals.” The articles help make those questions explicit before you commit to a particular answer:

| Thought in the draft | Question to bring to the reading | Most relevant ranked articles |
| --- | --- | --- |
| Lighter goal creation and universal goal assignment | How much intent needs to be explicit, and how much work structure can be discovered during execution? | 1, 2, 9 |
| “Needs Review,” plan approval, and verification | What judgment is being requested, and what evidence would make that judgment meaningful? | 3, 4, 5 |
| Heartbeats and active-work visibility | Which information helps a person redirect work, rather than merely observe activity? | 4, 7, 9 |
| Permanent/service goals and goal hooks | What changes when work originates from recurring events rather than a single prompt? | 5, 9, 10 |
| Clan launches as a unit | When does coordination improve outcomes, and when does it add overhead or propagate errors? | 2, 6 |
| Purging completed goals and dismissing agents | Which history remains useful after an execution instance or visible row goes away? | 7, 8, 10 |

There are two especially useful tensions to keep in mind. The first is **lighter orchestration versus stronger evidence**: the March harness case study simplifies work decomposition as model capabilities change, while the evaluation article makes success criteria more explicit. These can be read together without assuming that reducing workflow machinery means weakening the definition of success. This is my reading of [the harness experiments](https://www.anthropic.com/engineering/harness-design-long-running-apps) and [the evaluation guidance](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

The second is **fewer interruptions versus meaningful human control**. Observed experienced-user behavior favors monitoring and selective intervention; an event-driven implementation shows how questions, proposed actions, and results can be surfaced in a common work view. Neither establishes that every request should use the same approval semantics. That distinction is a useful reading question for [the autonomy study](https://www.anthropic.com/news/measuring-agent-autonomy) and [the ambient-agent walkthrough](https://aws.amazon.com/blogs/machine-learning/building-ambient-agents-with-amazon-bedrock-agentcore-from-event-driven-signals-to-human-in-the-loop-workflows/).

The biggest gap in the shortlist is direct evidence about your exact interface: none of these sources validates a first-tab position, the `<enter><enter>` gesture, SASE's particular clan syntax, or a purge interval. The material is strongest on conceptual distinctions, supervision, verification, and continuity. Application to those specific TUI choices would be an inference, not a reported finding.

**Why some attractive candidates did not make the ten.** Anthropic's [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) was published September 29, 2025, six days outside the window. Its [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) is from June 13, 2025 and is also ineligible. [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents), November 26, 2025, qualifies, but the March follow-up earns the slot by revisiting and removing parts of the earlier approach. NN/G's [Designing AI Agents: 4 Lessons from China's Qwen Agent](https://www.nngroup.com/articles/designing-ai-agents/), May 8, 2026, reports original usability work, but its six-participant consumer-transaction study has less direct transfer to your established coding-agent workflow than the selected systems and supervision articles. Undated living documentation, launch announcements with little analysis, and derivative roundups were not preferred.

**Ranked list of ten articles**

1. **[Humans and Agents in Software Engineering Loops](https://martinfowler.com/articles/exploring-gen-ai/humans-and-agents.html)**  
   **Kief Morris · MartinFowler.com / Thoughtworks · March 4, 2026.** Practitioner conceptual essay.

   **What it offers:** A distinction between the human loop that turns ideas into desired outcomes and the nested loops that produce specifications, code, and tests. It describes supervising and improving those loops as a different kind of involvement from inspecting each generated artifact.

   **Why it ranks first:** It supplies the clearest vocabulary for your underlying question: what relationship should a person's goal have to prompts, plans, agents, and verification? It is useful before discussing tab layout or goal-creation rules.

   **Read with this question:** Does the thing I am calling a goal express the outcome I care about, or an intermediate step in producing it?

   **Limit:** This is a reasoning framework, not an empirical validation of a particular goal-management product. Focus on the loop diagrams and the discussion of humans “on the loop.”

2. **[Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)**  
   **Prithvi Rajasekaran · Anthropic Engineering · March 24, 2026.** Firsthand engineering experiments.

   **What it offers:** Planner, generator, and evaluator experiments, including negotiated completion criteria. Crucially, the later version removes sprint decomposition and reduces evaluation frequency after a model upgrade; some previously helpful scaffolding becomes overhead.

   **Why it matters here:** This is the closest match to reconsidering a partially completed system while seeking lighter goal setup. It challenges the assumption that every currently useful orchestration step deserves to become a permanent product concept.

   **Read with this question:** Which structure expresses durable user intent, and which structure compensates for a particular model's current weaknesses?

   **Limit:** These are selected application-building examples, not controlled proof of a generally optimal workflow. The elaborate earlier harness was substantially more costly than the solo comparison. Prioritize the planner/evaluator rationale and the later simplification, rather than copying the original machinery.

3. **[Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)**  
   **Anthropic Engineering · January 9, 2026.** Evaluation methodology grounded in internal and customer practice.

   **What it offers:** Separates an agent's transcript from the resulting state of the world, and explains deterministic, model-based, and human grading. It also distinguishes finding one successful attempt from succeeding consistently across repeated attempts.

   **Why it matters here:** “Needs Review” becomes a more precise topic when you can ask what is being verified: the agent's account, an artifact, an environmental result, or a subjective quality judgment. The article covers research and conversational work as well as coding.

   **Read with this question:** What observation would establish that this outcome exists independently of the agent saying it does?

   **Limit:** Automated evaluation methodology does not settle a person's desired outcome or eliminate human judgment. Prioritize the definitions of transcript and outcome, research-agent grading, and the distinction between `pass@k` and `pass^k`.

4. **[Measuring AI agent autonomy in practice](https://www.anthropic.com/news/measuring-agent-autonomy)**  
   **Miles McCain and colleagues · Anthropic Societal Impacts · February 18, 2026.** Original observational research on millions of interactions.

   **What it offers:** More experienced Claude Code users both auto-approve more often and interrupt more often. The study also explains why runtime, task difficulty, and autonomy are different measurements.

   **Why it matters here:** It is unusually direct evidence for thinking about review queues, visible progress, and timely intervention. It challenges using approval frequency as the sole measure of whether a person remains in control.

   **Read with this question:** Would the proposed screen help me notice when to intervene, or mostly tell me that an agent is still running?

   **Limit:** Observational relationships are not causal proof. Account experience, product defaults, and task selection may influence the patterns. Focus on experienced-user supervision and the authors' recommendations for product developers.

5. **[Building ambient agents with Amazon Bedrock AgentCore: From event-driven signals to human-in-the-loop workflows](https://aws.amazon.com/blogs/machine-learning/building-ambient-agents-with-amazon-bedrock-agentcore-from-event-driven-signals-to-human-in-the-loop-workflows/)**  
   **Juan Albarran, Andy Widjaja, Kenton Blacutt, and Omar Hamden · AWS Artificial Intelligence Blog · October 1, 2026.** Concrete reference-implementation walkthrough.

   **What it offers:** Event-triggered work, scheduled work, review-before-execution and automatic-execution paths, and a common interaction mechanism for questions, proposed actions, results, and errors. Job state survives pauses for a human response.

   **Why it matters here:** The strongest direct analogue for permanent/service goals and replacing file-specific triggers with a broader source of work. Its unified Jobs view also connects continuing automation to a visible human-action queue.

   **Read with this question:** When work starts without a new prompt, what tells me why it started and what it needs from me?

   **Limit:** A fresh, AWS-specific sample rather than longitudinal evidence. It does not define a durable goal model, and its displayed “completed” status does not itself establish outcome verification. Read the conceptual and interaction sections before the deployment code.

6. **[Towards a science of scaling agent systems: When and why agent systems work](https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/)**  
   **Yubin Kim and Xin Liu · Google Research · January 28, 2026.** Accessible account of original controlled research.

   **What it offers:** Evaluates 180 configurations across single-agent and four multi-agent architectures. Coordination helps some parallelizable tasks but harms sequential planning tasks; architecture also changes error propagation.

   **Why it matters here:** A valuable counterweight to treating a clan as inherently the right execution unit for every goal. It gives you task properties to think about when deciding whether a group shares meaningful work or merely shares a label.

   **Read with this question:** Is the work actually decomposable, and where does the evidence get reconciled into one trustworthy outcome?

   **Limit:** Results depend on the study's benchmarks, models, budgets, and coordination protocols. The reported percentage gains and losses are not forecasts for SASE. Prioritize the alignment principle, sequential penalty, and error-amplification discussion.

7. **[The New Big Ball of Mud: Why Agentic AI Systems Turn Fragile](https://www.nngroup.com/articles/big-ball-of-mud-ai/)**  
   **Tanner Kohler · Nielsen Norman Group · October 2, 2026.** Qualitative research with advanced agent users.

   **What it offers:** Observations of personal agent systems growing through patches, context libraries, dashboards, and recurring automations until their owners struggle to understand or reconstruct them. It distinguishes global, local, and ambient context.

   **Why it matters here:** The best challenge to the temptation to continually enlarge a powerful personal orchestration system. One observed project evolves from a status widget into a much broader dashboard, making it particularly relevant to the proposed Goals surface.

   **Read with this question:** Would this addition make the system easier for me to understand and direct, or increase how much only the agent can explain?

   **Limit:** Qualitative observations, largely of nondeveloper builders, rather than a prevalence estimate or a diagnosis of SASE. Read it as a perspective on comprehensibility and the cost of perpetual extension.

8. **[Scaling Managed Agents: Decoupling the brain from the hands](https://www.anthropic.com/engineering/managed-agents)**  
   **Lance Martin, Gabe Cemaj, and Michael Cohen · Anthropic Engineering · April 8, 2026.** Firsthand infrastructure account.

   **What it offers:** Distinguishes durable session history, replaceable agent execution, and execution environments. It also explains why recoverable history is a different concern from the information currently present in a model's context window.

   **Why it matters here:** Particularly helpful for thinking about goals that outlive individual agents and about the meaning of dismissing or purging completed work. It encourages clearer language for what persists and what can be replaced.

   **Read with this question:** After a worker disappears, what information remains available to understand the outcome and continue related work?

   **Limit:** A hosted-service architecture at a different scale. Its abstractions are useful reading material; neither its deployment topology nor its retention choices are automatically appropriate for SASE. Prioritize the failure-recovery and session/context distinctions.

9. **[Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/)**  
   **Ryan Lopopolo · OpenAI Engineering · February 11, 2026.** Report from an internal product-building experiment.

   **What it offers:** Intent, executable feedback, agent-readable application behavior, versioned progress and decision records, and recurring maintenance tasks. The article distinguishes lightweight plans for small work from richer records for complex work.

   **Why it matters here:** It offers a concrete picture of lighter user input supported by a strong surrounding environment. Its ongoing cleanup work also makes permanent goals easier to imagine in terms of useful repeated outcomes rather than a single endless run.

   **Read with this question:** What information lets an agent prove progress while letting me spend less time restating context?

   **Limit:** A strongly supported internal environment, with no controlled productivity comparison or established multiyear results. The article explicitly cautions against assuming its autonomy generalizes. Focus on application legibility, plans as artifacts, and recurring maintenance.

10. **[Of course you can build dynamic AI agents with Temporal](https://temporal.io/blog/of-course-you-can-build-dynamic-ai-agents-with-temporal)**  
    **Mason Egger and Steve Androulakis · Temporal · November 12, 2025.** Explanatory engineering article with illustrative code.

    **What it offers:** A clear distinction between replayable orchestration and a predetermined plan. A durable record can preserve past model decisions while future decisions remain adaptive.

    **Why it matters here:** A useful antidote to assuming that lighter goal setting requires weaker execution guarantees, or that durable work requires specifying every step beforehand. It adds a recovery perspective to the discussion of long-lived and service-like work.

    **Read with this question:** What already-decided facts need to survive interruption, even if the next step is still open?

    **Limit:** Vendor advocacy and simplified examples. Replay alone is not proof that arbitrary external effects happen exactly once or that the user's outcome is satisfied. Read for the distinction between dynamic decisions and durable history, not as a recommendation to adopt Temporal.
