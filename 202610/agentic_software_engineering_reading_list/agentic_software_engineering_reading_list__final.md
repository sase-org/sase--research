# The best recent reading on agentic software engineering

- **Question.** Which of the best articles on agentic software engineering from the last
  year should you read next, excluding anything you have already read? The report ends
  with a ranked list.
- **Date.** 2026-10-10. The eligible window is **2025-10-10 through 2026-10-10**, judged by
  first publication. A later revision of an older paper does not make it eligible.
- **Written by.** The lead final, merging five independent reports with its own research.
- **Inputs.**
  - The five reports: [cdx](agentic_software_engineering_reading_list__cdx.md),
    [cld](agentic_software_engineering_reading_list__cld.md),
    [grk](agentic_software_engineering_reading_list__grk.md),
    [mus](agentic_software_engineering_reading_list__mus.md), and
    [gem](agentic_software_engineering_reading_list__gem.md).
  - Delegated fetches that checked the title, date, authors, and relied-on claims of about
    40 sources, including every Tier 1 and Tier 2 item.
  - One batched `bob ref find` over all 102 merged candidates. The five title-only matches
    were confirmed with `bob ref show`.

## Bottom line

The year's best writing has stopped asking how to prompt a coding agent. It now asks four
harder questions:

1. **Which harness components still earn their cost?**
2. **Who verifies the work, and what does a pass prove?**
3. **How should many agents coordinate?**
4. **What happens to human understanding and review capacity?**

You have already finished the architecture tour of this territory: the eleven-system harness
anatomy, OpenAI's harness-engineering post, Symphony, the long-horizon architecture paper, and
several memory papers. The highest-value next reads are therefore **controlled evidence and
first-hand operating reports**, not more architecture overviews.

If you read only five, read these:

1. **Fan et al., "An Empirical Study of Harness Design for Coding Agents"** (2026-09-17). It is
   the controlled-ablation follow-up to the anatomy paper you finished today.
2. **Gloaguen et al., "Evaluating AGENTS.md"** (v3, 2026-09-29). It is the most
   decision-relevant paper for SASE memory, and three of the five researchers ranked it
   independently.
3. **Krentsel et al., "Reality Is the Final Verifier"** (Berkeley, 2026-09-10). It gives the
   vocabulary for what receipts and goal checks can and cannot prove.
4. **Armin Ronacher, "The Coming Loop"** (2026-06-23). It is the best outside statement of
   SASE's single-turn-agent and outer-loop stance, and of where loops break.
5. **Chen & Stratton, "Artificial Intelligence in the Firm: Bottlenecks in Software
   Production"** (Harvard, current version 2026-08-04). It provides the year's strongest
   field evidence that review, not code writing, is now the constraint.

## What the year showed

These themes are where the five reports agree. They explain why the ranking favors evidence
over manifestos.

- **Harness engineering became the discipline, and is now being tested.** "Agent = model +
  harness" is consensus. The new work holds the loop fixed and measures which parts help.
  - Fan et al. ablate planning, action space, and context management.
  - AHE and Meta-Harness evolve harnesses automatically.
  - Gloaguen et al. test context files directly.
  - The answer is consistently *it depends on model and budget*. Some mechanisms that helped
    earlier models now mostly add cost.
- **Verification and review are the bottleneck.**
  - Field data: agent adoption across 718 firms increased PRs by 23%, but PR review time rose
    49% with no significant pass-through to output (Chen & Stratton).
  - Theory: Berkeley names the two gaps that no inner loop can close, and HIT makes
    acceptance authority non-transferable.
  - Practice: Zalando auto-approves its lowest-risk third of PRs, while StrongDM goes "no
    human review."
- **Pass rates hide process and decay.**
  - AgentLens finds that 10.7% of passing SWE-agent trajectories are "lucky passes."
  - SlopCodeBench shows agents eroding their own code faster than humans do.
  - Quality prompts shift where the decay starts, not how fast it proceeds.
- **Many-agent work needs a coordination mechanism and cost accounting.**
  - What works: a shared-workspace activity feed helps two agents (PASC), and Cursor's
    recursive planners with isolated workers reached about 1,000 commits per hour.
  - What fails: self-coordination through locks collapsed, and CooperBench catalogs the
    failure modes.
  - Static admission doubles pair pass rates but serializes almost everything (Claim Plane).
- **Human understanding is a resource that agents deplete.**
  - Storey's cognitive and intent debt.
  - Anthropic's RCT: 50% vs 67% quiz scores when learning with AI help.
  - Lyu et al.'s "comprehension debt."

## Where the reports disagreed, and how this report resolves it

Every row was checked against the primary source on 2026-10-10.

| Issue | Claim in the reports | Resolution |
| --- | --- | --- |
| AGENTS.md effect | mus: generated files *reduce* success ~3% and human files *improve* ~4%. cdx/cld: no improvement, >20% cost. | **Use v3.** v1 (Feb 2026) said context files "tend to reduce task success." v2 and v3 (Jun and Sep 2026) say they do "not generally improve task success rates" and raise cost ">20% on average." Both apply to LLM-generated and developer-written files. mus's per-type figures come from older secondary summaries. |
| Böckeler harness URL | gem: `…/exploring-gen-ai/harness-engineering.html` | Wrong. The canonical URL is `martinfowler.com/articles/harness-engineering.html`, dated 02 April 2026; the 17 Feb memo URL now redirects there. |
| Meta-Harness results | mus: "+27 on SWE-bench" | Not in the abstract. Reported results are text classification (+7.7 points with 4× fewer tokens), IMO-level math (+4.7), and beating hand-built TerminalBench-2 baselines. |
| "At Equal Inference Cost…" (mus #5) | Framed as evidence for the research-swarm debate | The paper exists, but it evaluates ALFWorld and WebShop with a frozen 7B model, so it is **not a software-engineering result**. Its v1 date (25 Jun 2026) also conflicts with its `2609.` ID. Demoted. |
| "Agentic Design Patterns" 2601.19752 (mus #8) | "Twelve design patterns for agentic coding" | Its real title is "…A System-Theoretic Framework," and it covers agentic AI in general. The abstract never mentions coding. Dropped. |
| Otoum & Elkhalili, IEEE Access (gem #9, "gold standard") | Peer-reviewed agentic-SE literature review | **The DOI returns 404.** grk had already dismissed it as a generic review. Dropped as unverified. |
| SWE-EVO (gem #6) | "Frontier agents >50% on SWE-bench drop precipitously" | The abstract compares **different models**: GPT-5.4 + OpenHands at 25% on SWE-EVO against GPT-5.2 at 72.8% on SWE-bench Verified. The first author is Tue Le, not Thai. |
| Anthropic expertise study | grk: value +27%. mus: ~25%. | **Both numbers are on the page.** The typical task's value rose "about 25%" (key findings), and the average session's value rose 27% from October to April (body). |
| Hassan et al., "Agentic SE: Foundational Pillars" | grk ranked it #1; cld called it out of window | **Out of window.** v1 is 2025-09-07, and only the revision is in range. It is still the paper that names *Structured Agentic Software Engineering* and you queued it on 2026-10-07, so it heads the "already in your library" list below. |
| TDD for agents | cdx recommends Willison's red/green TDD; cld cites Böckeler's experiment against TDD instructions | **A real tension, so the two are read as a pair (#21).** Böckeler's experiment is small: 2 runs per condition, Sonnet 4.6, greenfield Python, and token totals that include cache reads (her own caveat). Willison's argument is narrower: seeing the test fail proves it exercises the behavior. |
| Plan-compliance venue | grk: ASE 2026 | The arXiv page shows an ACM DOI but no venue, so ASE 2026 is unconfirmed. |
| "The Verification Horizon" | cld: "Qwen Team"; 28.6%→0.56% hacked-resolve rate | arXiv lists 13 individual authors and no team credit. The 28.6%→0.56% figure is not in the abstract and was not independently verified here. |
| Osmani, "Agent Harness Engineering" | gem: "Agent Stack," "Own the Outer Loop" | The page's verified core is the **ratchet**: every `AGENTS.md` line should trace to a past failure, and "harnesses don't shrink, they move." Osmani is an Anthropic MTS on Claude Code. |
| PASC vs CooperBench | Possible contradiction on multi-agent coordination | Not a contradiction. They test different workloads and coordination mechanisms (cdx's reading). |

## Ranked reading list

Ranking criteria, in order:

1. Incremental value over what you have finished.
2. Quality of evidence.
3. Direct usefulness for SASE design.
4. Agreement across researchers.
5. Recency.

The **SASE hook** line says why each item matters to you specifically. Every numbered item is
`not_found` in `ref/` unless marked otherwise.

### Tier 1: read these first

**1. An Empirical Study of Harness Design for Coding Agents**
- Run-Ze Fan et al. · arXiv [2609.20804](https://arxiv.org/abs/2609.20804) · 2026-09-17 ·
  preprint, 43 pages · ranked by cdx (#1).
- **Design:** holds the execution loop fixed and varies planning, action space, and context
  management. It covers 176 matched settings, four models, SWE-bench Verified and
  Terminal-Bench 2.1, five context strategies, and four context budgets.
- **Findings:**
  - Context management matters more as the budget shrinks.
  - Rule-based elision before LLM summarization is the most efficient strategy, and making
    elided content recoverable adds no accuracy.
  - Planning improves weaker models' accuracy but mainly cuts cost for stronger ones.
  - Bash-capable models do well with a bash-only interface at substantially lower cost.
- **SASE hook:** the method matters more than any single result. Retest planning, tool
  catalogs, and context policy under the model and budget you actually deploy, instead of
  accumulating mechanisms.
- **Caveat:** cdx reports one run per task and setting. The action-interface intervention is
  bundled, so it does not isolate tool count.

**2. Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?**
- Gloaguen, Mündler-Sasahara, Müller, Raychev, Vechev (ETH Zürich) · arXiv
  [2602.11988](https://arxiv.org/abs/2602.11988) · v1 2026-02-12, **read v3 (2026-09-29)** ·
  ranked by cdx (#4), cld (#6), and mus (#4).
- **Findings:**
  - Context files do not generally improve task success, for either LLM-generated or
    developer-written files.
  - They raise inference cost by more than 20% on average.
  - Agents follow the instructions, but repository overviews do not help.
  - Use context files for non-standard practices, and evaluate any addition before
    deploying it.
- **SASE hook:** this directly tests the core-memory inlining strategy, the budgeted
  instruction router, and how heavy the generated `AGENTS.md`/`CLAUDE.md` should be. Pair it
  with *Agent READMEs*, which you have queued.
- **Caveat:** the measured outcome is Python issue resolution. Governance, safety, and
  workflow constraints can justify instructions on other grounds.

**3. Reality Is the Final Verifier: On Two Key Gaps in Agentic Software Engineering**
- Krentsel, Agarwal, Cemri, …, Zaharia, Stoica · arXiv
  [2609.12039](https://arxiv.org/abs/2609.12039) · 2026-09-10 · position/framework paper ·
  ranked by cld (#2).
- **Argument:**
  - The implementation-verification loop cannot close two gaps. The **requirement gap**
    separates the requirements from what stakeholders intend. The **model gap** separates the
    evaluator's environment model from the world.
  - Reward hacking exploits these gaps, and hallucination widens them.
  - The proposal is an outer **assurance-revision loop** that uses deployment evidence to
    revise requirements, model, or evaluator, treated as an allocation of human judgment,
    agent capability, and compute.
- **SASE hook:** precise language for what a receipt proves and why goal settlement stays
  human.
- **Caveat:** the abstract has no numbers. Concrete cases cited by cld (a 6× KV-store
  "throughput" hack; 7.8% of "correct" SWE-bench patches failing developers' tests) are from
  the body.

**4. The Coming Loop**
- Armin Ronacher · [lucumr.pocoo.org](https://lucumr.pocoo.org/2026/6/23/the-coming-loop/) ·
  2026-06-23 · ~2,700 words · ranked by cld (#1).
- **Argument:**
  - He separates the agent loop inside one session from the **harness loop** outside it,
    which decides whether work is really done.
  - Loops work "astonishingly well" for porting, performance experiments, and security
    scanning.
  - On code he cares about, they produce defensive, fallback-laden code.
  - Attackers and bug reporters will run loops, so defenders must too.
  - He ends by asking how to keep human judgment in the loop.
- **SASE hook:** the best outside articulation of single-turn agents with mechanical
  continuation, and a list of failure modes goal checkpointing should detect.

**5. Artificial Intelligence in the Firm: Bottlenecks in Software Production**
- Fiona Chen & James Stratton (Harvard job-market paper) ·
  [PDF](https://fion.ac/jellyfish.pdf) · first version 2026-01-07, current 2026-08-04 · ranked
  by cdx (#5).
- **Data:** Jellyfish data covering about 300M work events across 718 firms, analyzed with a
  staggered difference-in-differences design.
- **Code output rises.** Agent adoption increased lines of code by 30%, commits by 20%, and
  PRs by 23%.
- **Review is the bottleneck.**
  - PR review time rose 49%.
  - The share of PRs with changes requested nearly doubled, and comments per PR rose 35%.
  - The share of workers doing review rose 14%.
  - The bottleneck persisted after firms adopted AI review tools.
- **Little pass-through.** There is no significant pass-through to issue output, and a
  precise zero effect on overall employment.
- **SASE hook:** the strongest quasi-causal field evidence that review capacity, not
  generation, limits delivery. It supports investing in risk-tiered landing, receipts, and
  review-reducing sensors.
- **Caveat:** observational identification, proprietary data, and a March 2026 data cutoff.
  Review time includes waiting time.

**6. Harness engineering for coding agent users**
- Birgitta Böckeler (Thoughtworks) ·
  [martinfowler.com](https://martinfowler.com/articles/harness-engineering.html) · 2026-04-02
  · ~3,200 words · ranked by cld (#3) and gem (#2).
- **Argument:**
  - The user's outer harness consists of **guides** (feedforward, such as `AGENTS.md`,
    skills, codemods) and **sensors** (feedback, such as tests, linters, review agents). Each
    is either computational or inferential.
  - The human runs a **steering loop**: when an issue recurs, they fix a guide or a sensor.
  - Behavioral correctness remains "the elephant in the room."
- **Companion:** the hands-on follow-up, ["Maintainability sensors for coding
  agents"](https://martinfowler.com/articles/sensors-for-coding-agents.html) (2026-05-27).
- **SASE hook:** a clean taxonomy for SASE memory (guides) versus hooks, receipts, and
  `just check` (sensors).

**7. SlopCodeBench: Benchmarking How Coding Agents Degrade Over Long-Horizon Iterative Tasks**
- Orlanski et al. · arXiv [2603.24755](https://arxiv.org/abs/2603.24755) ·
  2026-03-25, **read v2 (2026-05-07)** · ranked by cdx (#2) and cld (#25).
- **Results:**
  - The benchmark has 36 problems and 196 checkpoints, and agents extend their *own* earlier
    code.
  - Across 15 agents, none fully solves any problem, and the best passes 14.8% of checkpoints.
  - Agent code is 2.3× more verbose and 2.0× more eroded than 473 human Python repos.
  - Quality guidance cuts initial verbosity and erosion by up to a third but **does not
    change the rate of decay**.
- **SASE hook:** a reason to evaluate successive changes (regressions, extensibility,
  structure) rather than only the latest green run.
- **Caveat:** the structural metrics are proxies, and the human comparison is not on
  identical tasks.

**8. Minions: Stripe's one-shot, end-to-end coding agents (Parts 1 and 2)**
- Alistair Gray (Stripe) ·
  [Part 1](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents)
  2026-02-09 ·
  [Part 2](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2)
  2026-02-19 · ~4,000 words together · **lead's addition**; no researcher found it.
- **Scale:** over 1,300 merged PRs per week contain no human-written code. All are
  human-reviewed.
- **Design:**
  - Each run gets an isolated devbox from a pre-warmed pool in about 10 seconds.
  - The agent loop is a fork of Block's goose.
  - **Blueprints** are state machines that interleave deterministic nodes (lint, push) with
    agent nodes (implement, fix CI).
  - Toolshed is a central MCP server with about 500 tools, of which agents get a small subset
    by default.
  - Local lint runs in under five seconds.
  - A run gets **at most two CI rounds** before it returns to a human.
- **SASE hook:** this is the closest industrial analog to SASE's macro workflows, numbered
  workspaces, and guarded recipes. Böckeler (#6) cites it as an exemplar.

### Tier 2: strong next reads

**9. How Do Practitioners Build SE Agents? Insights from a Mixed-Methods Study**
- Lyu, Williams, Shi, …, Sarro, Lo · arXiv [2607.10856](https://arxiv.org/abs/2607.10856) ·
  v2 2026-07-25 · ranked by grk (#2).
- **Design:** 20 interviews across 12 organizations, plus a survey of 80 practitioners.
- **Findings:**
  - As implementation gets cheaper, bottlenecks move to review and evaluation.
  - The authors describe a seven-stage workflow and five process shifts, including
    **evaluation-driven development** and specifications as versioned artifacts.
  - They name six challenges with twelve practices. The challenges include unreliable eval
    signals, "comprehension debt," and regressions caused by provider-side model updates.
- **SASE hook:** the only empirical study of how teams *build* SE agents, which is what you
  are doing.

**10. Towards self-driving codebases**
- Wilson Lin (Cursor) · [cursor.com](https://cursor.com/blog/self-driving-codebases) ·
  2026-02-05 · ~19-minute read · ranked by cld (#5).
- **Design history:**
  - Lock-based self-coordination collapsed: 20 agents ran at the throughput of 1–3.
  - Planner/executor/judge designs were too rigid.
  - The final design uses recursive non-coding planners and isolated workers that return
    structured handoffs. The central integrator was removed as a bottleneck.
- **Results:** the team accepted a small steady error rate instead of 100% per-commit
  correctness, reaching about 1,000 commits per hour over 10M tool calls in a week. Disk I/O
  became the next bottleneck.
- **SASE hook:** handoff structure, error budget versus serialization, and where an epic
  orchestrator should sit.

**11. Coordination pair: PASC and CooperBench**
- **[Coordinating Agents on a Shared Git Workspace](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ESEM.2026.18)**
  - Özaytürk & Buzluca (Istanbul Technical University) · ESEM 2026, 2026-10-05 · ranked by
    cdx (#3).
  - Two agents share one git tree, and each sees a summary of the other's recent activity.
    They significantly beat a single agent.
  - A "silent" pair with no activity feed is statistically equivalent to a single agent, so
    the gain comes from coordination, not parallelism.
  - Compared with the silent pair, cost per resolved task is ~20% lower and destructive
    concurrent edits ~47% fewer.
  - Interference rises several-fold beyond two agents, and a single agent is still cheaper
    per pass.
- **[CooperBench: Why Coding Agents Cannot be Your Teammates Yet](https://arxiv.org/abs/2601.13295)**
  - Khatua et al. · 2026-01-19 · ranked by cdx (#10).
  - The failure-taxonomy companion: communication failures, broken commitments, and wrong
    expectations about a peer's work.
- **SASE hook:** evidence for observable peer actions (bead notes, commits) as a
  coordination channel, and a warning against unrestricted swarm scaling.

**12. Agentic coding and persistent returns to expertise**
- Hitzig, Massenkoff, Lyubich et al. (Anthropic) ·
  [anthropic.com](https://www.anthropic.com/research/claude-code-expertise) · 2026-06-16 ·
  ranked by grk (#3) and mus (#2).
- **Data:** about 400k interactive Claude Code sessions from about 235k people, October 2025
  to April 2026.
- **Findings:**
  - Users make about 70% of planning decisions but only about 20% of execution decisions.
  - Verified success is 15% for novices versus 28–33% for intermediate users and above.
  - Debugging fell from 33% of sessions to 19%.
  - Session value rose about 25–27% over the period.
  - Every one of the ten largest occupations comes within 7 points of software engineers on
    verified success.
- **SASE hook:** the largest public picture of the real human/agent division of labor.
- **Caveat:** vendor data. Task value is estimated from freelance postings.

**13. AgentLens: Revealing the Lucky Pass Problem in SWE-Agent Evaluation**
- Sahoo et al. · arXiv [2605.12925](https://arxiv.org/abs/2605.12925) · v4 2026-10-05 ·
  ranked by grk (#4).
- **Findings:**
  - 10.7% of passing trajectories are **lucky passes**, showing regression cycles, blind
    retries, skipped verification, or disordered phases.
  - The rate ranges from 0.5% to 23.2% across backends.
  - Ranking by process quality moves some models up to five positions.
- **SASE hook:** receipts should capture process evidence (was verification run?), not just
  a pass.
- **Caveat:** 60 tasks, and the dataset release is still pending.

**14. From Plan to Action: How Well Do Agents Follow the Plan?**
- Liu, Dehghan, Ganhotra, Hirzel, Jabbarvand · arXiv
  [2604.12147](https://arxiv.org/abs/2604.12147) · v3 2026-08-07 · ranked by grk (#5).
- **Design:** 21,120 SWE-agent trajectories across four LLMs and eight plan variants.
- **Findings:**
  - A bad plan is **worse than no plan**.
  - Periodic plan reminders reduce violations.
  - Extra early phases that conflict with the model's own strategy hurt.
- **SASE hook:** evidence on when `/sase_plan`-style explicit plans pay off, and on
  re-injecting the plan mid-run.

**15. Cheap Code, Costly Judgment: A Case Study on Governable Agentic Software Engineering**
- James C. Davis et al. (Purdue) · arXiv [2607.01087](https://arxiv.org/abs/2607.01087) · v2
  2026-07-04 · **lead's addition**.
- **Design:** a 12-week first-person case study. One expert built 420 KLOC of production code
  plus 1.16 MLOC of tests, lints, docs, and agent tooling, recorded in 88 contemporaneous
  field notes.
- **Contribution:** a "**governance conversion**" theory. Agent velocity exposes failure
  classes, human judgment interprets them, and new controls encode that judgment into the
  environment.
- **Unusual candor:** the authors report personal harm from sustained agentic work.
- **SASE hook:** a middle-range theory of how SASE accrues gates, hooks, and memory. It pairs
  with Osmani's "ratchet."

**16. Agentic Engineering at Zalando: a snapshot**
- Bartosz Ocytko ·
  [engineering.zalando.com](https://engineering.zalando.com/posts/2026/08/agentic-engineering-at-zalando-a-snapshot.html)
  · 2026-08-14 · ~4,000 words · ranked by cld (#7).
- **Context:** 2.5 years across more than 200 engineering teams, with no mandated tool and a
  LiteLLM proxy.
- **Findings:**
  - A risk-based PR approval bot, with rules derived from incident analysis, auto-approves
    **33%** of PRs and cut lead time 20–40%.
  - Engineers now split PRs to get low-risk parts through.
- **SASE hook:** a concrete, incident-derived risk-tiering model for host-owned landing.

**17. Verification Without Inspection**
- Annie Vella ·
  [annievella.com](https://annievella.com/posts/verification-without-inspection/) ·
  2026-07-31 · ~3,100 words · ranked by cld (#8).
- **Argument:**
  - Neither "review harder" nor "more tests" scales. She cites Deming, Bainbridge, and a
    Faros report that incidents per merged change more than tripled.
  - Make formal verification a first-class lifecycle step, for both agent-written code and
    agent actions.
- **Prequel:** ["The Middle Loop"](https://annievella.com/posts/the-middle-loop/)
  (2026-03-13).
- **SASE hook:** where receipts could go next.

**18. From Technical Debt to Cognitive and Intent Debt: Rethinking Software Health in the Age of AI**
- Margaret-Anne Storey · arXiv [2603.22106](https://arxiv.org/abs/2603.22106) · v4
  2026-04-06 · 10 pages · ranked by cld (#9).
- **Model:** the Triple Debt Model.
  - Technical debt lives in code.
  - Cognitive debt lives in people: the team's eroding shared theory of the system.
  - Intent debt lives in missing rationale, goals, and constraints.
- **Easier entry:** the [blog version](https://margaretstorey.com/blog/2026/02/09/cognitive-debt/)
  (2026-02-09).
- **SASE hook:** intent debt is what decision records and memory webs pay down. This gives
  you a citation and vocabulary for the launch post.

### Tier 3: read if the topic is live for you

**19. Harness self-optimization pair: AHE and Meta-Harness**
- **[Agentic Harness Engineering](https://arxiv.org/abs/2604.25850)**
  - Lin et al. · 2026-04-28 · ranked by cdx (#6) and mus (#6).
  - Proposed harness edits carry predictions that later outcomes test.
  - Terminal-Bench rises from 69.7% to 77.0% over ten iterations. The evolution used the full
    89-task set, so this is not a clean held-out estimate.
- **[Meta-Harness](https://arxiv.org/abs/2603.28052)**
  - Lee, Nair, Zhang, K. Lee, Khattab, Finn · 2026-03-30.
  - An agentic proposer searches harness code using prior candidates' code, scores, and
    traces.
  - Results appear in the corrections table. There is no SWE-bench result.
- **SASE hook:** an evidence-driven way to change SASE's own harness.

**20. Software Engineering in the Agent Era: From Trustworthy Change to Human–Agent Software Organizations**
- Zhongjie Wang & Mingyi Liu · arXiv [2609.04630](https://arxiv.org/abs/2609.04630) ·
  2026-09-04 · theory, no empirics · ranked by cld (#4).
- **Constructs:**
  - The change, not the PR, is the unit of control.
  - A "Responsibility Topology" describes who may accept residual risk.
  - "Human–Agent Cells" produce evidence but gain no acceptance authority.
- **SASE hook:** reads like an academic restatement of "Completion Is Host-Owned." It is long.

**21. The TDD pair: Willison and Böckeler**
- **[Red/green TDD](https://simonwillison.net/guides/agentic-engineering-patterns/red-green-tdd/)**
  - Simon Willison · 2026-02-23 · ranked by cdx (#11).
  - Make the agent watch the test fail first.
- **[TDD inside the agent loop – theater or actual value?](https://martinfowler.com/articles/exploring-gen-ai/tdd-in-the-agent-loop.html)**
  - Birgitta Böckeler · undated; published between mid-July and 2 Sep 2026, judging by its
    repo paths and series order · ranked by cld (#15).
  - TDD runs used 3–8.5× the tokens with no quality or mutation-score gain.
  - A blind judge several times ranked the non-TDD designs slightly higher.
  - She switched to mutation testing and "approved scenarios."
- **SASE hook:** decide whether instruction files should mandate test-first. See the
  corrections table for why these two do not simply contradict each other.

**22. Building a C compiler with a team of parallel Claudes**
- Nicholas Carlini (Anthropic) ·
  [anthropic.com](https://www.anthropic.com/engineering/building-c-compiler) · 2026-02-05 ·
  ranked by cld (#10); cdx considered it.
- **Setup:** 16 agents, about 2,000 sessions, and about $20k produced a Rust C compiler that
  builds Linux 6.9.
- **Harness:** lock-file task claiming, and GCC as an oracle so one giant task splits into
  independently debuggable pieces.
- **Lessons:** the verifier must be near-perfect, and test output should be designed against
  context pollution.
- **SASE hook:** a minimal cousin of bead claiming. The output rules apply to `sase tool`.

**23. Long-horizon evaluation cluster**
- **[SWE-Milestone](https://arxiv.org/abs/2603.13428)** (ICML 2026, 2026-03-13): scores 38%
  on continuous evolution versus more than 80% on isolated milestones.
- **[SWE-EVO](https://arxiv.org/abs/2512.18470)** (2025-12-20): 48 release-derived tasks
  averaging 21 files each.
- **[SWE Refactor Bench](https://arxiv.org/abs/2608.23564)** (2026-08-24):
  - 20 whole-repo migrations, and only 28 of 520 runs pass all three stages.
  - The best model, claude-opus-5, scores 47/100.
  - Agents "pass" by copying instead of migrating.
- **SASE hook:** benchmarks shaped like epics and migrations, not single issues.

**24. Parallel-agent conflict cluster**
- **[AI Agent Pull Requests on GitHub](https://arxiv.org/abs/2607.04697)** (2026-07-06):
  replayed merges conflict in 41.7% of cross-agent pairs.
- **[NP-Bench](https://arxiv.org/abs/2610.07261)** (2026-10-05): disjoint-scope scheduling
  took conflicts from 13 to 0.
- **[Claim Plane](https://arxiv.org/abs/2608.00947)** (2026-08-02):
  - Static admission doubled pair pass rates but serialized 97% of runs.
  - Dynamic admission broke on incomplete scope declarations.
- **SASE hook:** directly relevant to workspace allocation and hold/admission design. The
  Claim Plane negative result is the most useful of the three.

**25. Why Software Engineering Is Indispensable in the Age of Coding Agents**
- Alfonso Fuggetta · arXiv [2610.10226](https://arxiv.org/abs/2610.10226) · 2026-10-07 · 5
  pages · accepted at CACM but not yet published · ranked by gem (#1) and grk (#10).
- **Argument:** three LLM properties (probabilistic generation, agnosticism, semantic
  statelessness) leave a gap that four kinds of persistent knowledge artifact must fill. The
  engineer becomes methodologist, mediator, and custodian.
- **Why it sits low:** it is short and well framed but offers argument, not evidence.

**26. How AI assistance impacts the formation of coding skills**
- Anthropic (Shen & Tamkin) ·
  [anthropic.com](https://www.anthropic.com/research/AI-assistance-coding-skills) ·
  2026-01-29 · paper arXiv 2601.20245 · ranked by cld (#21).
- **Findings:** in an RCT with 52 engineers learning a new library, the AI-assisted group
  scored 50% versus 67% on the follow-up quiz and was not significantly faster. Delegation
  patterns scored lowest.

### Also worth knowing (unranked)

**Short practitioner essays.**
- Ronacher:
  - ["The Final Bottleneck"](https://lucumr.pocoo.org/2026/2/13/the-final-bottleneck/)
    (2026-02-13): a queueing view of review.
  - ["Better Models: Worse Tools"](https://lucumr.pocoo.org/2026/7/4/better-models-worse-tools/)
    (2026-07-04): tool schemas are not neutral across harnesses. Relevant to "Adapters
    Normalize Harnesses."
  - ["Astra for Coding: Why Are We Doing This Again?"](https://lucumr.pocoo.org/2026/9/7/astra-why/)
    (2026-09-07): a 35-hour unsupervised factory run produced nothing of value.
  - ["Agent Psychosis"](https://lucumr.pocoo.org/2026/1/18/agent-psychosis/) (2026-01-18):
    includes a critique of Beads and Gas Town.
- Others:
  - Edwards-Alexander, ["An Accidental Blackboard"](https://martinfowler.com/articles/exploring-gen-ai/an-accidental-blackboard.html)
    (2026-09-02): agents coordinated by reading each other's committed plan files.
  - Goedecke, ["Programming (with AI agents) as theory building"](https://www.seangoedecke.com/programming-with-ai-agents-as-theory-building/)
    (2026-04-03).
  - Osmani, ["Agent Harness Engineering"](https://addyosmani.com/blog/agent-harness-engineering/)
    (2026-04-19): the ratchet.

**Year-in-review and manifestos.**
- Willison, ["2026 in LLMs (so far)"](https://simonwillison.net/2026/Sep/27/2026-in-llms-so-far/)
  (2026-09-27).
- StrongDM's ["Software Factories"](https://factory.strongdm.ai/) manifesto (2026-02-06),
  read with Willison's [critical analysis](https://simonwillison.net/2026/Feb/7/software-factory/)
  (2026-02-07).
- Willison's living
  [Agentic Engineering Patterns](https://simonwillison.net/guides/agentic-engineering-patterns/)
  guide.

**Anthropic measurement and safety.**
- ["Measuring AI agent autonomy in practice"](https://www.anthropic.com/research/measuring-agent-autonomy)
  (2026-02-18, lead's addition):
  - The longest Claude Code turns roughly doubled to more than 45 minutes in three months.
  - Experienced users auto-approve more but also interrupt more.
- ["Quantifying infrastructure noise in agentic coding evals"](https://www.anthropic.com/engineering/infrastructure-noise)
  (2026-02-05): a 6-point Terminal-Bench swing from resource configuration alone.
- ["How we contain Claude across products"](https://www.anthropic.com/engineering/how-we-contain-claude)
  (2026-05-25): users approve about 93% of permission prompts, so containment must live in
  the environment.

**Measurement and field data.**
- METR, ["We are Changing our Developer Productivity Experiment Design"](https://metr.org/blog/2026-02-24-uplift-update/)
  (2026-02-24): the uplift follow-up broke because developers refused to work without AI.
- AIDev ([2602.09185](https://arxiv.org/abs/2602.09185)): about 930k agent PRs, the dataset to
  use if you mine agent PRs yourself.
- Google's FlowAgent ([2610.07289](https://arxiv.org/abs/2610.07289)): pre-submit repair at
  Google scale, with 28,554 applied fixes.

**Surveys, if you want one.**
- Guo et al., ["From Question Answering to Task Completion: A Survey on Agent System and Harness Design"](https://arxiv.org/abs/2606.20683)
  (2026-06-14).
- Zhou et al., ["Self-Evolving Coding Agents"](https://arxiv.org/abs/2608.03392) (v4
  2026-09-24).
- Raschka's explainer ["Components of A Coding Agent"](https://magazine.sebastianraschka.com/p/components-of-a-coding-agent)
  (2026-04-04) is the accessible version.

**Position papers.**
- Roychoudhury, Kang & Ray, ["Skills for the future software profession"](https://arxiv.org/abs/2606.21894)
  (v3 2026-08-30): verification and validation (V&V) become the core skill.
- Cao, ["Agentic Software"](https://arxiv.org/abs/2606.05608) (2026-06-04): software as
  runtime agent behavior.

## Already in your library: consider moving these up the queue

These are on-topic but already captured, so they are left out of the ranking.

- **Hassan et al., "Agentic Software Engineering: Foundational Pillars and a Research
  Roadmap"** (arXiv 2509.06216; v1 2025-09-07, v3 2026-06-24).
  - Queued since 2026-10-07 (modern note), which supersedes a legacy note queued since
    2025-11-28.
  - It is outside the window by first publication, but it is the paper that named
    *Structured Agentic Software Engineering*. grk ranked it first. Read v3.
- **Anthropic, "Demystifying evals for AI agents"** (2026-01-09). Queued since 2026-01-11
  (legacy backlog). The best bridge from #1, #7, and #13 to an evaluation practice for SASE.
- **Anthropic, "Harness design for long-running application development"** (2026-03-24).
  Queued since 2026-03-28 (legacy backlog). It separates generation from a calibrated,
  skeptical evaluator, and it removes scaffolding as models improve.
- **Chatlatanagulchai et al., "Agent READMEs"** (arXiv 2511.12884; read v2, 2026-08-09).
  Queued since 2026-01-18 (legacy backlog). The natural companion to #2.
- **Spotify, "1,500+ PRs Later" (Honk, Part 1)** (2025-11-06). Queued since 2026-03-22
  (legacy backlog).
  - Part 3, on feedback loops (2025-12-09), returned `not_found` by title.
  - It is the one to add if you capture only one more.
- **Anthropic, "Effective harnesses for long-running agents"** (2025-11-26), queued since
  2026-03-15. **"Scaling Managed Agents"** (2026-04-08), queued since 2026-04-17. Both are in
  the legacy backlog.
- **Horikawa et al., "Agentic Refactoring"** (2511.04824), queued since 2026-01-18. **OpenDev,
  "Building Effective AI Coding Agents for the Terminal"** (2603.05344), queued since
  2026-03-29. Both are in the legacy backlog.
- **Hoda, "Toward Agentic Software Engineering Beyond Code"** (2510.19692, 2025-10-22).
  Started since 2025-11-15 (legacy). Five pages; worth finishing.
- **LangChain, "The Anatomy of an Agent Harness"**, queued since 2026-04-04 (legacy). It
  surfaced as a title match for Osmani's essay and is a different article.
- **Per cld's separate lookup, not re-run here:**
  - Queued: Litt, "Understanding is the new bottleneck" (since 2026-10-07); Hashimoto, "My AI
    Adoption Journey" (since 2026-10-10); Kief Morris, "Humans and Agents in Software
    Engineering Loops"; Böckeler, "Context Engineering for Coding Agents"; and Anthropic's
    2026 Agentic Coding Trends Report.
  - Dropped 2026-10-08: "What Does a Harness Buy? Tokens, Mostly."

**Finished, so excluded:**
- The eleven-system harness anatomy (2609.00006).
- OpenAI's "Harness engineering."
- "An Architecture for Long-Horizon Agents" (2609.19519).
- OpenAI Symphony.

## Considered and dropped

- **Otoum & Elkhalili (IEEE Access):** the DOI does not resolve.
- **"Agentic Design Patterns" (2601.19752):** not about coding.
- **"At Equal Inference Cost…" (2609.04217):** not an SE benchmark, and its date is
  inconsistent with its ID.
- **Generic surveys:**
  - Bhati (2604.26275; also 2609.04681).
  - Tang & Runkler (2601.09822, a GenSE workshop concept paper).
  - Guo et al. 2510.09721.
  - Alenezi (2606.28791).
  - Gorsky's ASE-26 curriculum.
- **Simmering, "From Vibe Coding to Agentic Engineering":** a sound blog post, but Storey (#18)
  covers cognitive debt with more rigor.
- **Bain's "Missing Architecture" report:** grk could only read it via search snippets
  because of Cloudflare.
- **Thoughtworks' "Engineering the harness":** a restatement of #6.
- **Vendor surveys and "best coding agents" listicles.**
- **Out of window:** the original METR RCT (2025-07), SWE-Bench Pro (2025-09-21), Anthropic's
  "Effective context engineering" (2025-09), and DORA 2025 (2025-09). No 2026 DORA report
  was found.

## Suggested captures

These are proposals; the vault is read-only for this agent. Add `-L` to any line for
narrated audio.

```bash
bob ref create https://arxiv.org/abs/2609.20804
bob ref create https://arxiv.org/abs/2602.11988
bob ref create https://arxiv.org/abs/2609.12039
bob ref create https://lucumr.pocoo.org/2026/6/23/the-coming-loop/
bob ref create https://fion.ac/jellyfish.pdf
bob ref create https://martinfowler.com/articles/harness-engineering.html
bob ref create https://arxiv.org/abs/2603.24755
bob ref create https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2
bob ref create https://arxiv.org/abs/2607.10856
bob ref create https://cursor.com/blog/self-driving-codebases
bob ref create https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ESEM.2026.18
bob ref create https://www.anthropic.com/research/claude-code-expertise
bob ref create https://arxiv.org/abs/2605.12925
bob ref create https://arxiv.org/abs/2604.12147
bob ref create https://arxiv.org/abs/2607.01087
```

## Method and limits

**Inputs and verification.**
- Five independent reports were merged:
  - cdx: 24 audited candidates, strong on controlled evidence.
  - cld: 69 candidates, strong on practitioners.
  - grk: 46 candidates, strong on SE-academic and field studies.
  - mus: 14 candidates, mostly snippet-sourced.
  - gem: 11 candidates, with several unverified embellishments.
- The lead re-verified each Tier 1 and Tier 2 item and every disputed claim against the
  primary page. The Chen & Stratton figures come from the PDF text itself.

**What the lead's own research added.**
- Stripe Minions.
- Davis et al.'s governance-conversion case study.
- Anthropic's autonomy measurement.
- All of the corrections in the disagreements table.

**Limits.**
- `not_found` means absent from the `ref/` index. It is not proof you have not read
  something. Intake was not checked by `bob ref find`.
- arXiv items from July–October 2026 are recent preprints, and most lack peer review.
  Vendor posts from Anthropic, Stripe, Cursor, and Zalando are primary sources with an
  incentive to report success.
- Details marked as coming from a report's body text (for example, the cases cld cites in #3)
  were not all re-read verbatim.

Library check: 14 of 102 candidates already in your library (4 finished).
