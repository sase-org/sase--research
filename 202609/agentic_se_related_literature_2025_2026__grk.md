# Ten recent reads in the wake of the SASE paper

**Question.** Hassan, Li, Lin, Adams, Chen, Kashiwa, and Qiu's *Agentic Software Engineering: Foundational Pillars and a Research Roadmap* ([arXiv:2509.06216](https://arxiv.org/abs/2509.06216), v3 24 June 2026) is the conceptual paper behind SASE's name, ACE/AEE split, and structured-artifact vocabulary. What is worth reading next, from work published in the last year, that a reader who loved that paper is likely to understand, appreciate, and learn from?

**Recommendation.** Read the ten items below, in the order given in [Reading order](#reading-order). They are the highest-value matches I found to the SASE paper's actual concerns — structured duality, durable artifacts, merge-readiness versus test-passing, harnesses as first-class tools, and human-agent collaboration — rather than the highest-scoring SWE-bench papers of the last twelve months.

**Scope.** Cutoff is 30 September 2025 through 30 September 2026. Quality was ranked above recency. Every recommended item was first posted, or last substantially revised, inside that window. Semantic Scholar listed 62 papers citing 2509.06216 as of this research; those citations, plus arXiv cs.SE, Anthropic Engineering, and METR, were the search surface. Other researchers in this swarm are writing independently; this report does not consult them.

## What the SASE paper actually asked for

The paper is a conceptual scaffold, not a method paper. The ideas a sequel has to answer are:

- **SE 3.0 / goal-agentic work.** Agents take technical goals, not token completions.
- **SE for Humans versus SE for Agents.** Two modalities, two workbenches: ACE (human command center) and AEE (agent execution environment).
- **Durable artifacts as the collaboration medium.** BriefingScript, LoopScript, MentorScript, Consultation Request Packs, Merge-Readiness Packs, Version Controlled Resolutions — not chat logs.
- **Speed versus trust.** Agent PRs are fast; merge-ready is rare; verification is the bottleneck.
- **The harness is part of the engineering object.** Agency versus autonomy, workflow agents versus autonomous agents, FMware coded in English.
- **Education and vocabulary.** The field needs shared language before it needs another agent loop.

Progress in the last year clustered around those same six points. The vision papers got companions. The empirical substrate (AIDev) landed at MSR. Harness design became a first-class research object in both academia and industry. Context files (`AGENTS.md`, `CLAUDE.md`) were measured at scale, then shown not to raise SWE-bench scores. Trustworthiness papers started talking about *evidence-centric inspection* rather than reading diffs.

## The ten

Each entry names the SASE pillar it continues, why it is likely to land with a reader of 2509.06216, and what to take away. Length is a hint, not a ranking.

### 1. Rashina Hoda — *Toward Agentic Software Engineering Beyond Code: Framing Vision, Values, and Vocabulary*

- **Kind.** Short vision paper (5 pages). ICSE Companion / AGENT@ICSE 2026.
- **When.** arXiv 22 October 2025; v2 17 February 2026.
- **Link.** [arXiv:2510.19692](https://arxiv.org/abs/2510.19692)
- **SASE pillar.** Vocabulary, process, "whole of SE" rather than agentic coding.

This is the cleanest direct conversation with Hassan et al. Hoda takes SASE's SE-for-Humans / SE-for-Agents duality as given, then argues that the emerging visions are still too code-centric. The contribution is a preliminary value set and a plea for shared vocabulary so "agentic SE" becomes a process-level paradigm rather than a coding accelerator. It is short enough to read in one sitting and sharp enough to change how you hear later empirical papers.

**Takeaway.** Keep SASE's structured vocabulary, and widen the object of study from code-producing agents to the socio-technical lifecycle those agents sit in.

### 2. Robert Feldt, Per Lenberg, Julian Frattini, Dhasarathy Parthasarathy — *The Semi-Executable Stack: Agentic Software Engineering and the Expanding Scope of SE*

- **Kind.** Conceptual keynote companion. Agentic Engineering 2026 workshop, Rio.
- **When.** 16 April 2026; v2 23 April 2026.
- **Link.** [arXiv:2604.15468](https://arxiv.org/abs/2604.15468)
- **SASE pillar.** Artifacts and tools, pushed outward from source code.

If Hoda is the values companion, Feldt is the *scope* companion. The claim is that SE is not shrinking because models write code; the engineered object is expanding into *semi-executable artifacts* — prompts, workflows, controls, operating logic — whose enactment depends on interpretation rather than deterministic execution. The six-ring stack (executable artifacts, instructional artifacts, orchestrated execution, controls, operating logic, societal/institutional fit) is the same kind of diagnostic vocabulary SASE offered for ACE/AEE. The preserve-versus-purify heuristic at the end is unusually useful for someone building an operating layer around agent CLIs.

**Takeaway.** Treat xprompts, MentorScripts, approval gates, and notification inboxes as engineered artifacts on a spectrum of executability, not as UI chrome around "the real work" of generated code.

### 3. Aldeida Aleti, Baishakhi Ray, Rashina Hoda, Simin Chen — *Trustworthy AI Software Engineers*

- **Kind.** Vision paper.
- **When.** 6 February 2026; v2 3 June 2026.
- **Link.** [arXiv:2602.06310](https://arxiv.org/abs/2602.06310)
- **SASE pillar.** Merge-Readiness Packs, trust, human-AI teams.

This paper asks what it would even mean for an AI agent to *be* a software engineer, then treats trustworthiness as a property of the system rather than a feeling in the reviewer. The operational move is *evidence-centric inspection*: evaluate selective signals and justifications, not raw diffs. That is MRP in all but name. Dimensions include technical quality, transparency and accountability, epistemic humility, and societal/ethical alignment.

**Takeaway.** SASE's MRP/CRP/VCR loop is the right shape. The missing research is which evidence a human coach should actually inspect, and how to keep that inspection cheaper than reading the patch.

### 4. Hao Li, Haoxiang Zhang, Ahmed E. Hassan — *AIDev: Studying AI Coding Agents on GitHub*

- **Kind.** Dataset / MSR 2026 mining-challenge paper.
- **When.** 9 February 2026. Dataset cutoff for this paper: 1 August 2025 (later Hugging Face revisions go further).
- **Link.** [arXiv:2602.09185](https://arxiv.org/abs/2602.09185) · [Hugging Face](https://huggingface.co/datasets/hao-li/AIDev)
- **SASE pillar.** Industrial relevance; the empirical world the vision paper gestured at.

Same lab as the SASE paper. AIDev is the large-scale view of agent-authored PRs that 2509.06216 could only cite in passing: 932,791 Agentic-PRs from Codex, Devin, Copilot, Cursor, and Claude Code across 116,211 repositories (paper version), plus a curated popular-repo slice with reviews, comments, commits, and issues. Later dataset tags are even larger. Almost every serious empirical paper on agent PRs in 2026 stands on this corpus.

**Takeaway.** Read this before the empirical papers below. It is the map, not the travelogue.

### 5. Worawalan Chatlatanagulchai, Hao Li, Yutaro Kashiwa, Brittany Reid, et al. — *Agent READMEs: An Empirical Study of Context Files for Agentic Coding*

- **Kind.** Large-scale empirical study. Cited *inside* the SASE paper.
- **When.** 17 November 2025; v2 9 August 2026.
- **Link.** [arXiv:2511.12884](https://arxiv.org/abs/2511.12884)
- **SASE pillar.** MentorScript / SE-for-Agents instructional artifacts.

2,303 context files (`AGENTS.md`, `CLAUDE.md`, `copilot-instructions.md`) from 1,925 repositories. They evolve like configuration code — frequent small additions, poor readability — and they overwhelmingly encode functional context (testing 75.9%, implementation 70.8%, architecture 68.1%) while starving security (14.8%) and performance (14.5%). That is the empirical picture of today's MentorScripts: enough to make the agent *run*, not enough to make it *trustworthy*.

**Takeaway.** Persistent instruction files are already a real artifact class. They are not yet the guardrail SASE needs, because the instructions that would constrain merge-readiness are the ones developers omit.

### 6. Thibaud Gloaguen, Niels Mündler-Sasahara, Mark Niklas Müller, Veselin Raychev, Martin Vechev — *Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?*

- **Kind.** Controlled evaluation. Latest revision 29 September 2026.
- **When.** 12 February 2026; v3 29 September 2026.
- **Link.** [arXiv:2602.11988](https://arxiv.org/abs/2602.11988)
- **SASE pillar.** MentorScript effectiveness; "do not trust folklore."

The necessary counterweight to item 5. Across SWE-bench tasks with generated context files *and* issues from repos that already commit `AGENTS.md`, providing the file does not generally raise task success, and it raises inference cost by more than 20% on average. Agents follow the instructions; repository overviews, which vendors recommend, do not help. Developer-committed files beat LLM-generated ones by about 7%.

**Takeaway.** SASE's instinct that durable artifacts matter is right. The instinct that more repository overview in the always-on context file will raise agent success is not, at least on today's issue-resolution benchmarks. Put the energy into non-standard local conventions and into evidence packs, not into another architecture summary.

### 7. Oussama Ben Sghaier, Hao Li, Bram Adams, Ahmed E. Hassan — *Don't Blame the Large Language Model: How Agent Harness Evolution Shapes Coding Agent Quality*

- **Kind.** Longitudinal / causal-isolation empirical study.
- **When.** 4 July 2026; v2 20 July 2026.
- **Link.** [arXiv:2607.03691](https://arxiv.org/abs/2607.03691)
- **SASE pillar.** AEE, tools, the agency/autonomy distinction.

This is the paper that makes the SASE claim "the workbench is a first-class pillar" falsifiable. The authors fix the model and vary only the harness across 35 sequential Qwen Code CLI releases, after first documenting release velocities above two per day across Codex, Qwen Code, Gemini, OpenCode, and OpenHands. Quality swings that practitioners blame on the LLM trace to harness PRs. Combined with item 8, this is the academic statement of what Anthropic has been writing in engineering posts: the scaffold is the product.

**Takeaway.** When a coding-agent CLI "gets worse," look at the harness release, not the model card. An operating layer that wraps those CLIs (ACE talking to many AEEs) inherits their harness regressions unless it versions and isolates them.

### 8. James C. Davis, Kelechi Kalu, Huiyun Peng, Parth V. Patil — *Model-Based Agentic Software Engineering* (MAGE)

- **Kind.** Framework + theory, refined on a longitudinal case and six industrial accounts.
- **When.** 25 August 2026.
- **Link.** [arXiv:2608.25174](https://arxiv.org/abs/2608.25174)
- **SASE pillar.** Artifacts, processes, authority; ACE as governed environment.

MAGE is the closest 2026 theory paper to SASE's "durable structure instead of reconstructed judgment." Coding agents make implementation abundant; the scarce work becomes choosing abstractions, producing evidence, and deciding which obligations govern acceptance. MAGE externalizes the smallest purposeful representation needed to answer an engineering question, then gives settled obligations proportionate authority through constraints, sensors, validators, and gates. Uncertain intent stays open. Recurring reconstruction becomes inherited structure.

**Takeaway.** BriefingScripts should not try to freeze the whole mission. Freeze the obligations that are settled; keep a channel (CRP) for the ones that are not.

### 9. Maria I. Gorinova, Macey Baker, Amy Heineike, Maksim Shaposhnikov, Rob Willoughby, Dru Knox — *Position: Coding Benchmarks Are Misaligned with Agentic Software Engineering*

- **Kind.** Position paper.
- **When.** 16 June 2026; v2 18 July 2026.
- **Link.** [arXiv:2606.17799](https://arxiv.org/abs/2606.17799)
- **SASE pillar.** The SWE-bench critique already in 2509.06216, sharpened.

The SASE paper's section 3.3 already said passing tests is not merge-ready. This position paper says the *benchmarks themselves* are the wrong instrument for agentic SE: they collapse model, harness, and environment into one end-to-end score against a single reference solution, with no component-level signal. A coding agent in practice is a system harness. Any one component can move the score by as much as a model generation.

**Takeaway.** Stop using SWE-bench Verified as a proxy for ACE/AEE quality. If you evaluate SASE-like systems, score the harness components, accept multiple valid patches, and measure merge-readiness evidence rather than identity with a hidden gold patch.

### 10. Anthropic Engineering — *Effective harnesses for long-running agents*

- **Kind.** Industry article, with a public quickstart.
- **When.** 26 November 2025.
- **Link.** [anthropic.com/engineering/effective-harnesses-for-long-running-agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- **SASE pillar.** AEE session bridging; LoopScript / progress artifacts; "clean state" as merge-readiness.

This is the practitioner document that independently rediscovers SASE's structured-artifact thesis. Long-horizon coding cannot live in one context window. Anthropic's answer is an initializer agent that writes `init.sh`, a feature-list JSON, and a progress file, plus a coding agent that does one feature, leaves a git commit and a progress note, and only marks a feature passing after end-to-end testing (browser automation in their web-app case). Failure modes — one-shotting the app, declaring victory early, leaving a dirty tree, marking features done without testing — are exactly the failure modes SASE designed MRPs to catch.

**Takeaway.** A progress file plus a failing-by-default feature list plus "leave the tree mergeable" is a field-tested LoopScript. Pair it with item 7 so you do not confuse harness skill with model skill. The March 2026 sequel, [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps), is the optional extra chapter (planner / generator / evaluator, multi-hour runs, cost versus quality).

## Reading order

Read for *shape* first, then *evidence*, then *practice*.

1. Hoda (item 1) — 30 minutes. Recalibrates the object of study.
2. Feldt (item 2) — an evening. Gives you a second vocabulary to hold next to ACE/AEE.
3. Aleti et al. (item 3) — 45 minutes. Connects trustworthiness to inspection of evidence.
4. AIDev (item 4) — skim the dataset paper; keep the Hugging Face card bookmarked.
5. Agent READMEs (item 5) then Evaluating AGENTS.md (item 6) — one sitting. Folklore, then the ablation.
6. Don't Blame the LLM (item 7) and MAGE (item 8) — the AEE / authority pair.
7. Gorinova et al. (item 9) — short; read before trusting any leaderboard.
8. Anthropic harness article (item 10) — last, because you will now see it as an instance of the theory rather than as a blog post.

## How the field moved in the last year

Relative to the September 2025 SASE draft, four shifts are real.

**The vision has company.** Hoda, Feldt, Aleti et al., Davis et al., and the Rio A2SE seminar (honorable mention) all treat agentic SE as a redefinition of SE's object, not as a better copilot. Shared vocabulary is still contested, which is what Hassan et al. asked the community to do.

**The empirical substrate exists.** AIDev made agent PRs measurable. Follow-on work (honorable mentions: Horikawa et al. on refactoring; Nakashima et al. on rejection reasons; Takerngsaksiri et al. on post-merge fixes) is already showing that merged is not measured, and that agent merges attract follow-up fixes at higher odds than human merges.

**The harness overtook the model as the interesting variable.** Ben Sghaier et al. isolated it. Gorinova et al. argued benchmarks hide it. Anthropic productized it. SASE's AEE was the right bet.

**Context files are real and overclaimed.** They exist at scale, they are maintained like config, they omit the NFRs merge-readiness needs, and they do not raise SWE-bench success. That is a more interesting situation than "just write a better CLAUDE.md."

## Honorable mentions

These are high quality and in-window. They missed the cut because they overlap a top-ten item, are narrower, or are thinner as *reads*.

| Item | Why it is close |
| --- | --- |
| Taibi, Muccini, Vaidhyanathan, Kalinowski, et al., *A Research Agenda on Agents and Software Engineering* ([arXiv:2605.11720](https://arxiv.org/abs/2605.11720), 12 May 2026) | Community roadmap from the Rio A2SE seminar (18 experts). Complements SASE's own roadmap. Drier than Feldt/Hoda as a read. |
| METR, *Time Horizon 1.1* ([metr.org, 29 January 2026](https://metr.org/blog/2026-1-29-time-horizon-1-1)) | Best public measure of long-horizon agent capability. Post-2023 doubling ~131 days on the updated suite. Essential for forecasting; less about structured SE. |
| Horikawa, Li, Kashiwa, Adams, Iida, Hassan, *Agentic Refactoring* ([arXiv:2511.04824](https://arxiv.org/abs/2511.04824), 6 November 2025) | 15k agent refactorings: localized consistency work, not architecture. Cited in the SASE paper. |
| Nakashima, Ishimoto, Kondo, McIntosh, Kamei, *Why Agentic-PRs Get Rejected* ([arXiv:2602.04226](https://arxiv.org/abs/2602.04226), 4 February 2026) | Seven rejection modes unique to agent PRs, including distrust of AI code; 67.9% of rejected PRs lack reviewer feedback. Direct MRP motivation. |
| Takerngsaksiri, Duong, Barnett, *Who Finishes the Job?* ([arXiv:2609.26847](https://arxiv.org/abs/2609.26847), 22 September 2026) | Merged agent PRs attract verified follow-up fixes at 1.62× the odds of human PRs; agents usually author those fixes themselves. Merge ≠ done. |
| Zhong, Noei, Zou, Adams, *Human-AI Synergy in Agentic Code Review* ([arXiv:2603.15911](https://arxiv.org/abs/2603.15911), 16 March 2026) | 278k review conversations. Humans still supply understanding, testing, and knowledge transfer; AI suggestions are adopted less and inflate complexity more. |
| Vasilopoulos, *Codified Context* ([arXiv:2602.20478](https://arxiv.org/abs/2602.20478), 24 February 2026) | Three-tier context (constitution / specialist agents / cold specs) over 283 sessions on a 108k-line system. Practitioner-shaped MentorScript design. |
| Koch, *From Agent Output to Authorized Transition* ([arXiv:2609.28216](https://arxiv.org/abs/2609.28216), 23 September 2026) | Assurance-spine / receipts at the merge-or-deploy boundary. Formal cousin of MRP, very new. |
| Anthropic, *Scaling Managed Agents: Decoupling the brain from the hands* ([8 April 2026](https://www.anthropic.com/engineering/managed-agents)) | Hosted long-horizon agents; harness outside the container; session log as the durable artifact. ACE/AEE topology in production language. |

## Explicitly out of scope

These would have been on a "best of agentic SE" list with a looser date cut, and they are not recommended here.

- Hassan et al., *Towards AI-Native Software Engineering (SE 3.0)* ([arXiv:2410.06107](https://arxiv.org/abs/2410.06107), 2024) — the prequel, more than a year old.
- He, Treude, and Lo, *LLM-Based Multi-Agent Systems for Software Engineering* (TOSEM; [arXiv:2404.04834](https://arxiv.org/abs/2404.04834) from 2024) — important survey, wrong date.
- Deng et al., *SWE-Bench Pro* ([arXiv:2509.16941](https://arxiv.org/abs/2509.16941), first posted ~19 September 2025) — first version sits just outside the one-year window. The ICML 2026 proceedings version is in-window if you want the evaluation paper; I still ranked conceptual and harness work higher for a SASE reader.
- Anthropic, *Effective context engineering for AI agents* (29 September 2025) — one day before the cutoff.

## Method

- Read 2509.06216 v3 (HTML) for the pillars, autonomy ladder, industrial section, and SWE-bench critique.
- Pulled Semantic Scholar citations of 2509.06216 (62 citing papers) and ranked by conceptual proximity, empirical weight, and readability.
- Searched arXiv cs.SE for 2025-10 through 2026-09 on agentic SE, ACE/AEE, coding-agent PRs, context files, harnesses, and merge-readiness.
- Cross-checked industry sources (Anthropic Engineering, METR) for articles that a SASE reader would actually enjoy, not product announcements.
- Verified first-version or substantial-revision dates against the 30 September 2025 cutoff.
- Did not read other swarm reports from this turn.

## Suggested next research (not done here)

If this list is useful, the highest-leverage follow-up is a short mapping from SASE's named artifacts (BriefingScript, LoopScript, MentorScript, CRP, MRP, VCR) onto the empirical findings in items 5–7 and 10: which of those artifacts already exist in the wild under other names, which are still missing, and which ones the Evaluating-AGENTS.md result says are unlikely to help in their current form.
