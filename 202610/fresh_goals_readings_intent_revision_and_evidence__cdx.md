# Fresh readings for SASE Goals: intent, revision, and evidence

Researcher: **cdx** · Research date: **2026-10-06**  
Eligible publication window: **2025-10-06 through 2026-10-06**, inclusive.

The most promising next reading is Maggie Appleton’s September essay on planning with agents. The most directly relevant paper is Microsoft Research’s *Goals as First-Class Abstractions in Human-AI Collaboration*. For a concrete new angle on judging goal completion, read Braintrust and Basis’s article on behavior specs. All three are detailed in the ranked list that ends this report.

## What this adds to the earlier research

I located and read the October 5 synthesis, [Ten recent readings for rethinking SASE Goals](goals_redesign_recent_reading_list/goals_redesign_recent_reading_list.md), through an audited `sase artifact read`. It already covers vendor goal primitives, long-running harnesses, oversight and approval fatigue, heartbeat scheduling, persistent state, and goal drift. I used that synthesis as shared prior input. I did not read any report, transcript, summary, or findings from another member of the current `research.3t` swarm.

The ten selections below are absent from that synthesis’s ranked list **and its honorable mentions**. This is a claim about that specific reading list, not every earlier SASE research report. I also read the workspace’s `docs/goals.md` and the audited `goal-ledger` and `goals-host-binds` decision records to ground relevance in SASE’s person-owned outcomes, durable history, and human settlement authority.

My search emphasized four complementary questions:

1. How does a person discover and express what they actually want?
2. How should that intention change when work reveals new information?
3. What makes delegated work understandable and reviewable by its owner?
4. What evidence distinguishes useful progress from activity or persuasive reporting?

## Conclusions from the reading

These are my interpretations of the readings, offered as questions to explore:

- **Help the owner think:** What makes a goals experience useful while intention is still forming? [Goals as First-Class Abstractions](https://www.microsoft.com/en-us/research/publication/goals-as-first-class-abstractions-in-human-ai-collaboration/).
- **Make choices understandable:** What representation lets you examine consequences before committing? [Planning with Agents](https://maggieappleton.com/planning-agents).
- **Examine the route as well as the result:** Which material requirements need evidence beyond the final artifact? [Behavior specs](https://www.braintrust.dev/blog/behavior-specs).
- **Budget articulation effort:** How much structure deserves your attention for this particular outcome? [Understanding Spec-Driven-Development](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html).
- **Let review inform future intent:** Could outcome reflection improve how you formulate subsequent goals? [Nudging Attention to Workplace Meeting Goals](https://arxiv.org/abs/2602.16939).

## Selection and verification

I ranked for likely inspiration to Bryan’s Goals work, then incremental value beyond the October 5 list, directness of the original source, and readability. I favored articles: **seven selections are articles or article-form practitioner essays; three are papers**. A paper earned a place when it offered an unusually close conceptual match or empirical evidence. Ranking is qualitative, not an estimated probability of usefulness.

I opened each ranked original source and checked its title, author or publishing organization, publication date, and the passages underlying the recommendation. Dates below are publication dates, not crawl dates. For the three papers, I distinguish workshop/conference publication from first public preprint dates. Appleton’s visible page uses relative dates; its primary HTML explicitly gives `article:published_time` and `datePublished` as **2026-09-14**, with modification on September 15. I checked those metadata directly.

I excluded repeated picks from the prior synthesis and undated living product documentation from the ranking. Search snippets served for discovery; recommendations rely on opened primary articles and papers. Practitioner cases, position papers, and empirical studies are identified separately. Claims about what might transfer to SASE are my interpretation.

Two useful tensions make these readings better as a set:

- Read the specification critique (#4) alongside the practical guide (#8), and ask how much structure a particular outcome deserves.
- Read goal articulation (#2) alongside disempowerment (#9), and ask whether AI is clarifying the owner’s preferences or supplying its own.

## Ranked reading list

### 1. Planning with Agents: Divided Worlds, Boundary Objects, and Thicker Interfaces

**[Read the article](https://maggieappleton.com/planning-agents)** · Maggie Appleton · **2026-09-14** · Illustrated essay/talk transcript.

**Why first:** It most strongly expands the design space beyond a goal card, a status lane, or a completion loop. Appleton critiques long questionnaires followed by a large Markdown plan and binary approval. She proposes representations that humans can inspect, manipulate, and discuss, and prototypes that expose consequences while decisions remain open.

**What to take from it:** Focus on the shadow-editor and retry-policy examples. They show the difference between choosing a verbal option and seeing its implications. A goal could become a shared object around which informed choices happen; that is my extension of her planning argument.

**Reading question:** When a goal contains an unresolved choice, what would let you make that choice competently?

**Evidence limit:** This is design exploration, not a controlled usability study. Her companion [Chopin prototype writeup](https://githubnext.com/projects/chopin/) is dated September 2026 and shows the research context; it is an optional companion, not another ranked pick.

### 2. Goals as First-Class Abstractions in Human-AI Collaboration

**[Publication page](https://www.microsoft.com/en-us/research/publication/goals-as-first-class-abstractions-in-human-ai-collaboration/)** · [Full paper](https://www.microsoft.com/en-us/research/wp-content/uploads/2026/04/2026-goals-as-first-class-abstractions-in-human-ai-collaboration-AutomationXP26_paper_0982.pdf) · Lev Tankelevitch and Sean Rintel · **April 2026**; workshop citation dated **2026-04-14** · Seven-page workshop position paper.

**Why second:** This is almost exactly the conceptual question behind SASE Goals. It identifies a gap between recording goals and helping people formulate, reconcile, and use them during work.

**What to take from it:** Section 5 proposes six capabilities: assistance with articulation, durable representations, detection and negotiation of conflicting intentions, revision history and rationale, anticipation of downstream effects, and goal cues within actual workflows. The paper argues that useful goal objects must tolerate incomplete and changing intentions.

**Reading question:** Which part of your goals experience improves the quality of an intention, rather than merely preserving it?

**Evidence limit:** This is a research agenda supported by prior literature and examples, not a validation of an implemented goals platform. Its broad review of commercial tools should not be mistaken for an exhaustive product benchmark.

### 3. Behavior specs, an open standard for supervising long-horizon agents

**[Read the article](https://www.braintrust.dev/blog/behavior-specs)** · Ankur Goyal and Mitchell Troyanovsky · **2026-07-29** · Engineering article; collaboration between Braintrust and Basis.

**Why third:** It introduces a concrete evaluative unit between a final outcome and exhaustive step checking. A correct final artifact can conceal missing grounding, outdated verification evidence, or an inappropriate process.

**What to take from it:** The presentation-validation example specifies what evidence must refer to the current artifact, what should happen after a failed check, and what the agent may honestly claim. Each behavior is judged independently as satisfied, violated, or inapplicable. These specs are evaluation standards and are not shown to the working agent as prompts.

**Reading question:** Which few requirements about reaching a goal matter enough to evaluate independently of the final result?

**Evidence limit:** This is a vendor-backed standard announcement with production examples, not comparative evidence of improved outcomes. The authors also stress that measuring compliance does not establish that the chosen standard is wise.

### 4. Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl

**[Read the article](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)** · Birgitta Böckeler · **2025-10-15** · Hands-on practitioner analysis on Martin Fowler’s site.

**Why fourth:** It is the best corrective here to making every goal a miniature requirements bureaucracy. A small bug produced four user stories and sixteen acceptance criteria in one trial; another workflow generated extensive, repetitive review material.

**What to take from it:** The distinction between writing a specification first, preserving it for maintenance, and treating it as the primary source is particularly useful for thinking about how long intention records should remain operational. Read the sections on problem size, Markdown review burden, and apparent control despite ignored instructions.

**Reading question:** How much goal detail is useful for this size and uncertainty of work, and who bears the cost of reviewing it?

**Evidence limit:** Small exploratory trials from 2025. Read it for failure modes and questions, rather than present-day conclusions about those rapidly evolving products.

### 5. The 3 Roles of Context for AI Agents

**[Read the article](https://www.nngroup.com/articles/3-agent-context-roles/)** · Tanner Kohler · **2026-09-18** · UX research article based on observations of Claude power users.

**Why fifth:** It offers a clear explanation for how casual, lightweight instructions can work: they depend on supporting context. Users maintained libraries serving three roles—stable guidance across work, information scoped to a particular project or task, and raw surrounding streams.

**What to take from it:** The same information can move between roles. A message can begin as background communication, become evidence for current work, and later become a durable reference. That is a useful lens on the relationship between a goal, its relevant evidence, and the wider context from which it arose.

**Reading question:** If the goal itself is one sentence, where does the information needed to interpret it correctly live?

**Evidence limit:** Qualitative observations of advanced users; the article does not establish causal performance gains or universal behavior. Its context categories are useful vocabulary, not an authority hierarchy for agent permissions.

### 6. Nudging Attention to Workplace Meeting Goals: A Large-Scale, Preregistered Field Experiment

**[Abstract and dates](https://arxiv.org/abs/2602.16939)** · [Full text](https://arxiv.org/html/2602.16939v1) · Lev Tankelevitch, Ava Elizabeth Scott, Nagaravind Challakere, Payod Panda, and Sean Rintel · **2026-02-18** first public preprint; CHI 2026 paper · Empirical research.

**Why sixth:** It brings real evidence about lightweight goal reflection into a list otherwise rich in design arguments. The study included **361 employees and 7,196 meetings** over two weeks.

**What to take from it:** Pre-meeting prompts did **not** significantly improve measured meeting effectiveness relative to the control group. Both groups reported improvements in goal awareness and behavior; the authors suggest the post-meeting surveys unintentionally prompted reflection. Timing, overload, and whether reflection produced an immediate useful artifact mattered in participants’ accounts.

**Reading question:** Could reviewing a finished outcome help you formulate the next goal better, and what would make that interaction worth your attention?

**Evidence limit:** Meeting work rather than software agents; self-report, imperfect compliance, and no passive control. The findings do not prove either pre- or post-work reflection improves SASE outcomes.

### 7. “Doctor, it hurts when agents create unreviewable PRs.” “Don’t do that.”

**[Read the article](https://blog.jonudell.net/2026/06/28/doctor-it-hurts-when-agents-create-unreviewable-prs-dont-do-that/)** · Jon Udell · **2026-06-28** · Short practitioner essay.

**Why seventh:** It offers a useful alternative response to review overload: shape work so its owner can understand it while it unfolds. That complements the prior list’s emphasis on filtering the resulting review queue.

**What to take from it:** Udell describes small testable work packages, shared local specifications, switching agents to obtain another perspective, and searchable history. Removing an item from the current worklist does not make it disappear from history. This is a concrete account of separating current attention from retained context.

**Reading question:** What size of delegated outcome lets you retain enough understanding to judge it yourself?

**Evidence limit:** One author’s workflow while building his own tool. He explicitly declines to generalize to industrial-scale throughput. The worklist is an analogy for goals, not the same domain object as SASE’s outcome record.

### 8. How to write a good spec for AI agents

**[Read the article](https://addyosmani.com/blog/good-spec/)** · Addy Osmani · **2026-01-13** · Practical engineering guide.

**Why eighth:** It provides a concrete set of prompts for expressing a goal’s working agreement. Read it after #4 so its useful checklists do not become mandatory overhead for every request.

**What to take from it:** Start with purpose, use task-specific context, provide examples or conformance criteria, distinguish actions to take routinely from actions requiring approval and prohibited actions, and revise the specification as understanding changes. Explicitly synchronizing the agent with a revision is a particularly useful detail.

**Reading question:** What is the smallest set of examples, constraints, and success evidence that makes this goal unambiguous enough to pursue?

**Evidence limit:** This is practitioner guidance assembled from experience and other sources, not a controlled comparison. Its assertions about effective configurations and self-verification should be read as advice rather than proof of reliability.

### 9. Disempowerment patterns in real-world AI usage

**[Read the research article](https://www.anthropic.com/research/disempowerment-patterns)** · Anthropic · **2026-01-28** · Accessible article explaining an empirical study.

**Why ninth:** It adds a perspective largely missing from engineering-loop discussions: an assistant can influence which goals its owner comes to want. A record labeled human-owned does not settle that question.

**What to take from it:** The study analyzes approximately **1.5 million conversations**, distinguishing potential distortion of beliefs, value judgments, and actions. Potentially disempowering exchanges could receive favorable immediate feedback. My application to Goals is a question about whether an articulation assistant helps you examine trade-offs or quietly selects priorities for you.

**Reading question:** How would you recognize a goal suggestion that is convenient to accept but poorly aligned with your own priorities?

**Evidence limit:** The analysis concerns consumer conversations and filters out purely technical interactions. It measures disempowerment potential, largely through validated automated classifiers, rather than confirmed harm. It is a conceptual transfer to SASE, not evidence that coding-goal suggestions cause these effects.

### 10. Designing Intent Communication for Agent-Human Collaboration

**[Abstract and dates](https://arxiv.org/abs/2510.20409)** · [Full text](https://arxiv.org/html/2510.20409v1) · Yi Li, Francesco Chiossi, Helena Anna Frijns, Jan Leusmann, Julian Rasch, Robin Welsch, Philipp Wintersberger, Florian Michahelles, and Albrecht Schmidt · **2025-10-23** first public preprint; MUM conference **2025-12-01–04** · Design-framework paper.

**Why tenth:** It helps distinguish several meanings of showing agent progress. A status signal, an explanation of purpose and constraints, and a projection of the next consequential action serve different human needs.

**What to take from it:** The framework combines information depth, task horizon, and communication modality. Its examples encourage choosing disclosure according to what the owner must perceive, understand, or anticipate at that moment. This supplies a broader vocabulary for a goal’s live display than an activity feed alone.

**Reading question:** Does this progress update help you understand the goal’s situation, anticipate a decision, or only confirm that an agent is alive?

**Evidence limit:** A conceptual framework illustrated mainly through robotics and shared-control scenarios. It does not supply a controlled evaluation of a coding-agent goals interface or a validated notification cadence.
