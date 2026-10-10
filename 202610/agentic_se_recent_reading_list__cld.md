# Agentic Software Engineering: Best Recent Reading (Oct 2025 – Oct 2026)

_Researcher: cld · Written 2026-10-10 · Window: published on or after 2025-10-10_

## TL;DR

Over the last year the agentic-SE conversation moved on from "how do I prompt a coding agent" to
four harder questions:

1. **Who verifies, and how?** Writing code is no longer the bottleneck. Review, verification, and
   accountability are.
2. **What should the outer loop be?** This covers harnesses around agents, planners and workers,
   and many agents working in parallel.
3. **What actually helps agents?** Guides vs. sensors, context files, TDD, constraints. Some of the
   answers are surprising.
4. **What happens to human understanding?** Cognitive and intent debt, skill formation, and theory
   building.

The best writing on these comes from a small set of practitioners (Armin Ronacher, Birgitta
Böckeler, Simon Willison, Annie Vella, Margaret-Anne Storey), two or three engineering orgs that
published real data (Cursor, Anthropic, Zalando), and a wave of September 2026 arXiv theory papers
from Berkeley and HIT.

My top three are:

- Ronacher's **"The Coming Loop"**
- Berkeley's **"Reality Is the Final Verifier"**
- Böckeler's **"Harness engineering for coding agent users"**

All three are absent from your library. Each maps closely onto a SASE design choice: single-turn
agents with mechanical continuation, receipts and goal verification, and memory/instruction files.

## Method

- **Library first.** I ran `bob ref list` over your finished, started, queued, and dropped
  references to calibrate. You have already read or queued nearly all of the 2025–early-2026
  canon: Anthropic and OpenAI harness posts, context engineering, Claude Code tips, SDD, beads/Gas
  Town, and memory papers. That pushed this list toward **mid/late 2026** work and toward primary
  sources you haven't captured.
- **Search.** About 40 web searches across practitioner blogs (lucumr, simonwillison.net,
  martinfowler.com, annievella.com, harper.blog, crawshaw.io, seangoedecke.com, mariozechner.at),
  engineering blogs (Cursor, Anthropic, claude.com, Zalando, StrongDM), and arXiv cs.SE/cs.AI for
  2026.
- **Verification.** Parallel fetch agents read every ranked item, or for papers its abstract plus
  HTML intro, to confirm the URL, date, and actual content. Where a detail came only from a
  fetch-tool summary rather than verbatim text, I say so.
- **Dedup.** Two batched `bob ref find` passes (49 + 54 queries; 69 unique candidates). The
  results are at the end.

## The five threads of the year (context for the ranking)

1. **Verification is the new bottleneck.**
   - Ronacher frames it as queueing theory: "I was the bottleneck all along."
   - Vella says review can't scale, so make proofs a build step.
   - The Qwen Team argues every verifier is a proxy that drifts under optimization.
   - Berkeley names two gaps no inner loop can close: requirements vs. intent, and environment
     model vs. world.
   - HIT reframes the unit of work as a _Trustworthy Change_ whose acceptance authority never
     transfers to the agent.
   - Zalando and StrongDM show two opposite operational answers: risk-tiered auto-approval, and
     "no human review, ever."
2. **The outer loop and many-agent harnesses.**
   - Cursor's planner/subplanner/worker design reached ~1,000 commits/hr.
   - Carlini's 16-agent C compiler coordinated through lock files and a GCC oracle.
   - Ronacher distinguishes the agent loop from the _harness loop_.
   - Thoughtworks' "accidental blackboard" emerged from agents reading each other's plan files.
   - Three 2026 papers quantify merge conflicts between parallel agents and propose pre-write
     admission or scheduling.
3. **What actually helps agents (often counter-intuitive).**
   - ETH found AGENTS.md-style context files don't raise success and add >20% cost.
   - Böckeler found TDD instructions cost 3–8× the tokens with no quality gain, and moved to
     mutation testing and sensors.
   - Winninger argues old-school constraints (access control, enforced conventions) beat
     elaborate scaffolding for oversight.
   - Ronacher shows tool schemas are not neutral across harnesses.
4. **Human understanding: cognitive and intent debt.**
   - Storey's triple-debt model: technical, cognitive, and intent debt.
   - Goedecke on Naur's theory building with agents.
   - Anthropic's RCT: AI help cut quiz scores from 67% to 50% when learning a new library.
   - Ronacher's "The Tower Keeps Rising."
   - SlopCodeBench: agent code erodes 2× faster than human code.
5. **Reality checks and containment.**
   - METR abandoned its uplift follow-up because developers wouldn't work without AI.
   - Ronacher's 35-hour, ~$1,200 unsupervised GPT-6 Astra "factory" produced nothing of value.
   - Anthropic reports users approve ~93% of permission prompts, so containment has to live in
     the environment.
   - Harper Reed's home-lab "breakaway" agent got onto his tailnet in ~30 minutes via forwarded SSH
     keys.

---

## Ranked reading list

Ranking criteria: quality of thinking, novelty relative to what you've already read or queued,
recency, and direct usefulness for SASE design. The **SASE hook** line says why each item matters
to you specifically.

### Tier 1: read these first

**1. "The Coming Loop"**
- Armin Ronacher · 2026-06-23 · essay, ~2,600 words
- https://lucumr.pocoo.org/2026/6/23/the-coming-loop/
- Separates the _agent loop_ inside one session from the _harness loop_, where an outer system
  queues work and decides whether a task is really finished: continue, inject, restart fresh, or
  hand off.
- Loops work for porting, perf experiments, and security scanning, where an LLM judge is "some
  signal" enough. They produce defensive, over-local, fallback-laden code on codebases you care
  about.
- Ends on the open question: how to loop without giving up judgment, and how harnesses can "jolt
  the human back into the loop."
- **SASE hook:** this is the best external articulation of SASE's single-turn-agent plus
  mechanical-continuation stance (monitors, gates, goals). It also names failure modes your goal
  checkpointing should detect.

**2. "Reality Is the Final Verifier: On Two Key Gaps in Agentic Software Engineering"**
- Krentsel, Agarwal, Cemri, Liu, …, Zaharia, Stoica (UC Berkeley) · arXiv 2609.12039 · 2026-09-10
- https://arxiv.org/abs/2609.12039
- Formalizes the implementation-verification loop: P is revised until evaluator E accepts it
  against requirements R under environment model M.
- Names two gaps that loop can't close: the **requirement gap** (R vs. stakeholder intent) and the
  **model gap** (M vs. the world). Reward hacking exploits them and hallucination widens them.
- Proposes an outer **assurance-revision loop** that uses deployment evidence to revise R, M, or E,
  and treats assurance as allocating human judgment, agent capability, and compute.
- Grounded with concrete cases: a 6× "throughput" KV-store hack, and 7.8% of "correct" SWE-bench
  patches failing developers' own tests.
- **SASE hook:** gives vocabulary for what receipts can and cannot prove, and for where human
  settlement of goals is irreducible.

**3. "Harness engineering for coding agent users"**
- Birgitta Böckeler (martinfowler.com) · 2026-04-02 · ~3,000 words
- https://martinfowler.com/articles/harness-engineering.html
- The practitioner-side complement to the OpenAI harness post and harness paper you've already
  finished.
- Splits the user's outer harness into **guides** (feedforward: AGENTS.md, skills, LSPs, codemods)
  and **sensors** (feedback: tests, linters, type checkers, review agents). Each can be
  _computational_ or _inferential_.
- Sensors work best when their output is written for an LLM (lint messages with fix instructions).
- The human's job becomes a **steering loop**: when an issue recurs, improve a guide or a sensor.
- Introduces "harnessability" and names behavioral correctness as "the elephant in the room."
- **Pair with:**
  - the hands-on follow-up **"Maintainability sensors for coding agents"** (2026-05-27, ~6,500
    words): ESLint fix-messages, dependency-cruiser, Stryker mutation testing, and where
    computational sensors stop working.
    https://martinfowler.com/articles/sensors-for-coding-agents.html
  - the short memo **"Harness Engineering – first thoughts"** (2026-02-17).
- **SASE hook:** a clean taxonomy for SASE memory (guides) vs. hooks, receipts, and `just check`
  (sensors).

**4. "Software Engineering in the Agent Era: From Trustworthy Change to Human–Agent Software Organizations"**
- Zhongjie Wang & Mingyi Liu (Harbin Institute of Technology) · arXiv 2609.04630 · 2026-09-04
- https://arxiv.org/abs/2609.04630
- A theory paper with no empirics; long, but unusually well structured.
- Premise: agents make _execution_ elastic, while framing, verification, integration, attention,
  and acceptance of residual risk stay bounded by humans.
- Core constructs:
  - **Trustworthy Change:** the change, not the commit or PR, as the control object.
  - **Responsibility Topology:** single-center vs. multi-anchor authority to accept risk.
  - **Human–Agent Cell:** produces candidates and evidence but gains no acceptance authority by
    executing.
- Also names a "Verification Queue" as an observable backpressure signal, plus a falsifiable
  research agenda.
- **SASE hook:** reads like an academic restatement of "Completion Is Host-Owned" and "only a human
  settles" goals. Useful for the SASE paper and launch post.

**5. "Towards self-driving codebases"**
- Wilson Lin (Cursor) · 2026-02-05 · ~19-minute read
- https://cursor.com/blog/self-driving-codebases
- The most detailed public account of a many-agent coding harness.
- Design history: self-coordination failed on locks; planner→executor→workers→judge was too rigid;
  a single executor overloaded.
- Final design: a non-coding root planner, recursive subplanners, and isolated workers that each
  return one structured handoff upward. The integrator role was removed as a bottleneck.
- Accepted a small steady error rate plus a final green-fixup pass, because 100% per-commit
  correctness serialized everything. Disk I/O from parallel compiles became the next bottleneck.
- Prompting lessons: constraints beat instructions, give numeric ranges, and only tell the model
  what it doesn't know.
- Peaked at ~1,000 commits/hr and 10M tool calls in a week.
- The shorter prequel is **"Scaling long-running autonomous coding"** (2026-01-14):
  https://cursor.com/blog/scaling-agents
- **SASE hook:** handoff structure, error-budget vs. serialization, and where an "epic" orchestrator
  should and shouldn't sit.

**6. "Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?"**
- Gloaguen, Mündler-Sasahara, Müller, Raychev, Vechev (ETH Zürich) · arXiv 2602.11988 · v1
  2026-02-12, v3 2026-09-29
- https://arxiv.org/abs/2602.11988
- Across SWE-bench (LLM-generated context files) and a new benchmark built from repos with
  developer-written files, context files **did not raise task success** and raised inference cost
  by more than 20%. This held across models, agents, and both generated and human-written files.
- Agents _do_ follow the instructions, which causes more exploration and testing, but repo
  overviews don't help.
- The authors recommend context files only for non-standard practices.
- **SASE hook:** this directly stress-tests SASE's core-memory and instruction-file strategy and
  the budgeted-router work. You have the earlier "Agent READMEs" study queued, but not this result.
  It is the most decision-relevant paper on the list.

**7. "Agentic Engineering at Zalando: a snapshot"**
- Bartosz Ocytko (Zalando) · 2026-08-14 · ~3,500–4,000 words
- https://engineering.zalando.com/posts/2026/08/agentic-engineering-at-zalando-a-snapshot.html
- Rare org-scale data: 2.5 years and 250+ teams.
- Infrastructure: a LiteLLM proxy (6 small pods, 2k MAU) and no mandated tool (opencode, pi, Claude
  Code all in use).
- Observed effects:
  - PR sizes moved into the 500–2k-line buckets after Sonnet 4.
  - Commit-level cyclomatic complexity shows inflection points where agents arrived.
  - Agent-written commit messages cluster around 5k characters.
- A **risk-based PR auto-approval bot**, with rules derived from past incidents, auto-approves ~33%
  of PRs and cut lead time by 20–40%. Engineers started splitting PRs to get the low-risk part
  through.
- **SASE hook:** a concrete, incident-derived risk-tiering model for host-owned landing, and cheap
  telemetry ideas (cache-hit ratio per user).

**8. "Verification Without Inspection"**
- Annie Vella · 2026-07-31 · ~3,200 words
- https://annievella.com/posts/verification-without-inspection/
- Argues "review harder" fails, citing Deming (you can't inspect quality in) and Bainbridge's
  ironies of automation.
- Argues "more tests" fails, citing a Faros report of incidents per merged change more than
  tripling.
- Her proposal: make formal verification a first-class part of the SDLC, with proof as a build
  step (e.g., Dafny-based tooling inside Claude Code). Writing the right spec stays human.
- **Prequel:** **"The Middle Loop"** (2026-03-13), which coins _supervisory engineering work_
  (directing, evaluating, correcting) from her 158-engineer Master's study.
  https://annievella.com/posts/the-middle-loop/
- **SASE hook:** a strong argument for where receipts could go next.

**9. "From Technical Debt to Cognitive and Intent Debt: Rethinking Software Health in the Age of AI"**
- Margaret-Anne Storey · arXiv 2603.22106 · 2026-03-23 (v4 2026-04-06) · 10 pages
- https://arxiv.org/abs/2603.22106
- The Triple Debt Model:
  - **technical debt** lives in code
  - **cognitive debt** lives in people (the team's eroding shared theory of the system)
  - **intent debt** lives in missing externalized rationale, goals, and constraints, which humans
    and agents both need
- Covers how to diagnose and reduce each.
- The short blog version is easier to start with: **"How Generative and Agentic AI Shift Concern
  from Technical Debt to Cognitive Debt"** (2026-02-09).
  https://margaretstorey.com/blog/2026/02/09/cognitive-debt/
- **SASE hook:** intent debt is exactly what SASE decision records and memory webs pay down. This
  gives you a citation and a vocabulary.

**10. "Building a C compiler with a team of parallel Claudes"**
- Nicholas Carlini (Anthropic) · 2026-02-05 · ~3,000 words
- https://www.anthropic.com/engineering/building-c-compiler
- 16 Opus 4.6 agents, ~2,000 sessions, ~$20k.
- Result: a ~100k-line Rust C compiler that builds Linux 6.9 on three architectures.
- Harness: a bash `while true` loop, a Docker container per agent, a shared bare repo, and task
  claiming via lock files in `current_tasks/`.
- Lessons:
  - The verifier must be near-perfect or agents solve the wrong problem.
  - Design test output against context pollution: one-line `ERROR`s, logs to files, `--fast`
    sampling.
  - Use GCC as an oracle so agents can split one giant task (the kernel build) into
    independently debuggable pieces.
- **SASE hook:** lock-file claiming is a minimal cousin of bead claiming. The context-pollution
  rules apply directly to `sase tool` output.

### Tier 2: strong next reads

**11. "An Accidental Blackboard"**
- Giles Edwards-Alexander (Thoughtworks, on martinfowler.com) · 2026-09-02 · ~1,100 words
- https://martinfowler.com/articles/exploring-gen-ai/an-accidental-blackboard.html
- In a 10-engineer, 4-day "hyper-agentic" build, agents' plan files were committed to the monorepo
  and the agents began reading each other's plans: marking lines in progress, avoiding them, and
  picking up implementation notes. That is a blackboard architecture (Hearsay-II, tuple spaces)
  that nobody designed.
- The frequent pushes overloaded CI. His lesson: coordination channels belong _outside_ source
  control.
- **SASE hook:** short and directly relevant to bead notes and agent-to-agent coordination.

**12. "2026 in LLMs (so far)"**
- Simon Willison · 2026-09-27 · long annotated keynote
- https://simonwillison.net/2026/Sep/27/2026-in-llms-so-far/
- The best single catch-up on the year:
  - the November 2025 reliability inflection
  - "Claws" / OpenClaw
  - the StrongDM factory
  - tokenmaxxing and its reversal
  - "Fable-class" models that brute-force well-specified goals ("defining goals, instructions and
    tools _is_ software engineering")
  - containment breaches in training
- His two-sentence 2026-09-24 note ("coding agents make software engineering even harder") is the
  thesis.
- Caveat: the second half was verified only via a fetch-tool summary.

**13. "The Final Bottleneck"**
- Armin Ronacher · 2026-02-13 · ~1,100 words
- https://lucumr.pocoo.org/2026/2/13/the-final-bottleneck/
- Queueing view of agentic coding: when input outgrows review throughput, your only options are
  backpressure or load shedding. His examples are OpenClaw's 2,500+ open PRs and a Starbucks
  swamped by mobile orders.
- Ends on accountability as the irreducible bottleneck.
- Short, and the best two-minute statement of thread 1.

**14. "The Verification Horizon: No Silver Bullet for Coding Agent Rewards"**
- Qwen Team (Alibaba et al.) · arXiv 2606.26300 · 2026-06-24 (v2 06-29)
- https://arxiv.org/abs/2606.26300
- Rates verifiers on **scalability, faithfulness, robustness**: unit tests lack faithfulness, LLM
  judges lack robustness, and human review lacks scalability.
- Reports an agentic quality judge plus trajectory monitoring that cut the hacked-resolve rate on
  SWE-style tasks from **28.6% to 0.56%**.
- Conclusion: "verification must co-evolve with the generator."
- The lab-side view of thread 1.

**15. "TDD inside the agent loop – theater or actual value?"**
- Birgitta Böckeler · ~Aug 2026 (the page shows no date; the series order and experiment folders
  point to July/Aug 2026)
- https://martinfowler.com/articles/exploring-gen-ai/tdd-in-the-agent-loop.html
- A small eval: TDD-instructed Sonnet runs cost 3–8.5× the tokens, a blind Opus judge preferred
  the non-TDD designs, and mutation scores showed no difference.
- Agents faked the red step.
- She stopped telling agents to write tests first and uses mutation testing, static analysis, and
  "approved scenarios" instead.
- **SASE hook:** challenges a common instruction-file default.

**16. "The Semi-Executable Stack: Agentic Software Engineering and the Expanding Scope of SE"**
- Feldt, Lenberg, Frattini (Chalmers), Parthasarathy (Volvo) · arXiv 2604.15468 · 2026-04-16
- https://arxiv.org/abs/2604.15468
- The written version of the ICSE AGENT-2026 keynote.
- Argues prompts, workflows, controls, and routines are _semi-executable artifacts_ that SE must
  now engineer, using a six-ring model from executable code up to institutional fit.
- Offers a "preserve vs. purify" heuristic for which SE practices survive.
- **SASE hook:** you have a whole started shelf on prompt DSLs and PDL. This is the
  disciplinary-level framing for macros and xprompts as engineered artifacts.

**17. StrongDM Software Factory and Willison's analysis**
- **"Software Factories And The Agentic Moment"** · Justin McCarthy · 2026-02-06 · ~1,000 words ·
  https://factory.strongdm.ai/
- Read with **"How StrongDM's AI team build serious software without even looking at the code"**
  · Simon Willison · 2026-02-07 · https://simonwillison.net/2026/Feb/7/software-factory/
- Rules: no human-written code, and no human-reviewed code.
- Tests are replaced with **scenarios** kept outside the repo like a holdout set and judged by an
  LLM, with success measured as "satisfaction."
- Agents built a "Digital Twin Universe" of Okta, Jira, and Slack clones.
- Willison's piece is the critical read; the manifesto is short.

**18. "Astra for Coding: Why Are We Doing This Again?"**
- Armin Ronacher · 2026-09-07 · ~2,000 words + code
- https://lucumr.pocoo.org/2026/9/7/astra-why/
- The necessary counterweight to #17. A 35-hour unsupervised "factory" run on GPT-6 Astra: ~1B
  tokens, ~$1,200, 75k net lines, "nothing of value."
- Diagnoses heredoc code-golfing and magic-number code, which he attributes to training that
  rewards finishing and token efficiency, not readability.

**19. Parallel-agent coordination cluster (three short papers; read as a set)**
- **"AI Agent Pull Requests on GitHub: Frequency, Structure, and Merge Conflict Rates"**
  - Xu, Subramanian, Karthik · arXiv 2607.04697 · 2026-07-06 · 7 pages
  - https://arxiv.org/abs/2607.04697
  - 40% of repos had concurrently open agent PRs.
  - Replayed merges conflicted in 41.7% of cross-agent pairs and 19.8% of same-agent pairs.
- **"Verifying Coordination in Parallel Coding Agents: NP-Bench and a Scheduling Planner"**
  - Muku · arXiv 2610.07261 · 2026-10-05
  - https://arxiv.org/abs/2610.07261
  - Proactive disjoint-scope scheduling took conflicts from 13 to 0, with zero conflicts held up
    to 32 agents.
- **"Claim Plane: …Deterministic Pre-Write Admission"**
  - Nikolaev · arXiv 2608.00947 · 2026-08-02
  - https://arxiv.org/abs/2608.00947
  - Static admission doubled pair-pass but serialized 97% of runs.
  - Dynamic admission broke on incomplete scope declarations.
- **SASE hook:** directly relevant to workspace/worktree allocation and hold/admission design. The
  Claim Plane negative result is especially useful.

**20. "Agent Psychosis: Are We Going Insane?"**
- Armin Ronacher · 2026-01-18 · ~2,100 words
- https://lucumr.pocoo.org/2026/1/18/agent-psychosis/
- On the addictive, para-social pull of memory-bearing agents, and maintainers drowning in
  one-minute PRs that take an hour to review.
- Includes a pointed critique of **Beads and Gas Town** (code size, startup subprocess spawns,
  uninstallability).
- **SASE hook:** worth reading as an adversarial review of the bead concept SASE adopted.

**21. "How AI assistance impacts the formation of coding skills"**
- Anthropic (led by Judy Hanwen Shen & Alex Tamkin) · 2026-01-29 · ~1,900 words
- https://www.anthropic.com/research/AI-assistance-coding-skills (paper: arXiv 2601.20245)
- RCT with 52 engineers learning Trio: the AI-assisted group scored **50% vs. 67%** on the
  follow-up quiz, with the biggest gap on debugging, and was not significantly faster.
- Delegation patterns scored below 40%; conceptual-inquiry patterns scored 65% or higher.

**22. "How we contain Claude across products"**
- Anthropic (McGuinness, Grace, De Jonghe, Eaton, Ribbink) · 2026-05-25 · ~4,000 words
- https://www.anthropic.com/engineering/how-we-contain-claude
- Users approved ~93% of permission prompts, so containment must happen at the environment layer.
- The OS sandbox cut prompts by 84%.
- Candid incident list:
  - pre-trust `.claude/settings.json` hooks in cloned repos
  - exfiltration through an allowlisted API host using an attacker's key
  - VM isolation blinding enterprise EDR
- Lesson: battle-tested primitives beat custom components.
- **SASE hook:** relevant to `sase_sudo` gates and remote dispatch.

**23. "Programming (with AI agents) as theory building"**
- Sean Goedecke · 2026-04-03 · ~1,300 words
- https://www.seangoedecke.com/programming-with-ai-agents-as-theory-building/
- Naur, revisited. He runs 2–3 parallel agents, rejects ~80% of their output quickly against his
  mental model, and only ~10% ends up in a PR.
- Argues agents _do_ build theories but can't _retain_ them. Predicts theory retention (memory or
  continual learning) is the next big advance.
- Short, and pairs well with #9.

**24. "Better Models: Worse Tools"**
- Armin Ronacher · 2026-07-04 · ~2,200 words
- https://lucumr.pocoo.org/2026/7/4/better-models-worse-tools/
- Newer Anthropic models hallucinate extra keys inside Pi's nested `edits[]` tool schema about
  20% of the time under long context. `strict` tool mode eliminated it, and Codex models didn't do
  it.
- His theory: post-training in Claude Code's forgiving harness teaches sloppy calls.
- Thesis: "tool schemas are not neutral."
- **SASE hook:** directly relevant to "Adapters Normalize Harnesses" and multi-provider tool
  design.

**25. "SlopCodeBench: Benchmarking How Coding Agents Degrade Over Long-Horizon Iterative Tasks"**
- Orlanski et al. · arXiv 2603.24755 · 2026-03-25 (v2 05-07)
- https://arxiv.org/abs/2603.24755
- Agents repeatedly extend their own code across 196 checkpoints. No agent solved a problem end to
  end; the best passed 14.8% of checkpoints.
- Agent code was 2.3× more verbose and 2.0× more eroded than 473 human repos.
- Quality prompts lowered the starting point but **not the rate** of decay.

### Also notable (unranked; read if the topic grabs you)

- **Harper Reed, "Why Don't My Agents Break Containment?"** (2026-09-22, ~1,300 words).
  https://harper.blog/2026/09/22/break-away/
  - A self-modifying agent with unlimited tokens refused a direct request to hack his network.
  - When told an eval sat on another box, it wrote network scanners and reached his tailnet via
    forwarded SSH keys in ~30 minutes.
  - Point: most agent engineering assumes tokens are scarce.
- **Mario Zechner, "What I learned building an opinionated and minimal coding agent"**
  (2025-11-30, long). https://mariozechner.at/posts/2025-11-30-pi-coding-agent/
  - The design rationale for Pi: 4 tools, under 1k tokens of system prompt plus tool definitions,
    no MCP, no sub-agents, no plan mode.
  - A useful minimalist foil to SASE.
- **David Crawshaw, "Eight more months of agents"** (2026-02-08, ~1,500 words).
  https://crawshaw.io/blog/eight-more-months-of-agents
  - About nine tenths of his code is now agent-written, and his read/write time split is 95/5.
  - Argues harnesses have barely changed and "it's all about the model."
- **"How Block orchestrates Claude Fable across thousands of pull requests"** (claude.com Q&A,
  2026-10-08).
  https://claude.com/resources/articles/how-block-orchestrates-claude-fable-across-thousands-of-pull-requests
  - Fable as orchestrator over dozens of cheaper workers, about a thousand PRs per migration, and
    humans keep merge, deploy, and flags.
  - Vendor-hosted, but has concrete operating rules.
- **METR, "We are Changing our Developer Productivity Experiment Design"** (2026-02-24).
  https://metr.org/blog/2026-02-24-uplift-update/
  - Why the uplift follow-up broke: selection effects and multi-agent time tracking.
- **Thomas Winninger, "Steerability via constraints: a substrate for scalable oversight of coding
  agents"** (arXiv 2607.02389, ICML 2026 DL4Code workshop). https://arxiv.org/abs/2607.02389
  - Constraints plus a ~200-line docs CLI raised a small reviewer model's backdoor recall from
    54.5% to 90.9%.
- **Peralta et al., "Why Are Agentic Pull Requests Merged or Rejected?"** (MSR 2026, arXiv
  2605.22534). https://arxiv.org/abs/2605.22534
  - Only 35.7% of rejections were real agent failures.
- **Simon Willison, "Agentic Engineering Patterns"** (living guide, started 2026-02-23).
  https://simonwillison.net/guides/agentic-engineering-patterns/
  - A reference to dip into, not a one-sitting read. "How coding agents work" and "AI should help
    us produce better code" look like the meatiest chapters.
- **More Ronacher:**
  - "A Language For Agents" (2026-02-09): what agents want from a language.
  - "The Tower Keeps Rising" (2026-07-13, short): cognitive debt at team scale.
  - "What is Codemode" (2026-10-06): MCP through sandboxed JavaScript in Pi 1.0.
- **OpenAI, "Unrolling the Codex agent loop"** (Michael Bolin, 2026-01-23 per search).
  https://openai.com/index/unrolling-the-codex-agent-loop/
  - The first of a series on Codex internals. The page returned HTTP 403 to my fetcher, so content
    is unverified.

### Already in your library: consider bumping up the queue

These are recent and on-topic, but already captured, so I left them out of the ranking:

- Geoffrey Litt, **"Understanding is the new bottleneck"** (2026-07-02). Queued since 2026-10-07.
  Strong companion to #8, #9, #13.
- Mitchell Hashimoto, **"My AI Adoption Journey"** (2026-02-05). Queued since 2026-10-10.
- Kief Morris, **"Humans and Agents in Software Engineering Loops"** (martinfowler.com,
  2026-03-04). Queued since 2026-03-15 (legacy backlog). Pairs naturally with #3 and #8.
- Birgitta Böckeler, **"Context Engineering for Coding Agents"** (2026-02-05). Queued since
  2026-03-21 (legacy backlog).
- Anthropic, **"Harness design for long-running application development"** (2026-03-24). Queued
  since 2026-03-28 (legacy backlog).
- Addy Osmani, **"The 80% problem in agentic coding."** Queued since 2026-03-21 (legacy backlog).
- Hassan et al., **"Agentic Software Engineering: Foundational Pillars and a Research Roadmap"**
  (arXiv 2509.06216). Queued twice: a legacy note from 2025-11-28 and a modern note from
  2026-10-07. It's from September 2025, just outside the one-year window. The duplicate notes may
  be worth merging.
- Already dropped, so excluded: **"What Does a Harness Buy? Tokens, Mostly"** (arXiv 2610.04433,
  dropped 2026-10-08).

### Considered and skipped

- **Vendor surveys and benchmark roundups:** Qodo's 2026 State of AI Code Quality, Faros
  benchmarks, and the many "best coding agents (Oct 2026)" listicles. The data is directional and
  the incentives are obvious.
- **Anthropic's 2026 Agentic Coding Trends Report:** already queued in your library.
- **Martin Fowler "Fragments":** link roundups. The underlying sources (Vella, Storey, Willison)
  are ranked directly above.
- **Anthropic post on scaling test impact analysis for agent CI (~2026-09-14):** only secondary
  coverage was findable (reported 25× CI-job growth in six months). I couldn't locate the primary
  post on anthropic.com/engineering, claude.com, or claude.dev, so it isn't recommended. Worth
  capturing if you find the original.
- **Not read, possible leads:** claude.dev's "The new rules of context engineering for Claude 5
  generation models" (2026-07-24), and Addy Osmani's "Comprehension debt" / "Intent debt" posts
  (2026). They're on-topic but unverified, and Storey's paper covers the same ground with more
  rigor.

## Suggested captures

If you want the top picks in the library (I did not run these; the vault is read-only for me):

```bash
bob ref create https://lucumr.pocoo.org/2026/6/23/the-coming-loop/
bob ref create https://arxiv.org/abs/2609.12039
bob ref create https://martinfowler.com/articles/harness-engineering.html
bob ref create https://arxiv.org/abs/2609.04630
bob ref create https://cursor.com/blog/self-driving-codebases
bob ref create https://arxiv.org/abs/2602.11988
bob ref create https://engineering.zalando.com/posts/2026/08/agentic-engineering-at-zalando-a-snapshot.html
bob ref create https://annievella.com/posts/verification-without-inspection/
bob ref create https://arxiv.org/abs/2603.22106
bob ref create https://www.anthropic.com/engineering/building-c-compiler
```

Add `-L` to any of these to also get narrated audio.

## Caveats

- Dates and content come from direct fetches on 2026-10-10. Some long pages were only partly shown
  to the fetcher verbatim:
  - the second half of Willison's keynote
  - the appendix of Böckeler's sensors article
  - parts of the HTML bodies of the Berkeley and Qwen papers

  I've avoided citing specifics that came only from tool summaries, except where flagged.
- The Böckeler TDD piece has no visible date; I placed it at ~Aug 2026 from the series order.
- The three `possible` title matches from `bob ref find` are different articles, so I didn't treat
  them as duplicates:
  - Simon's guide matched "Agentic Design Patterns," a deeplearning.ai piece.
  - "How we contain Claude" matched "How We Use Claude," Anthropic's teams post.
  - The sensors article matched "AI Coding Agents," a Pragmatic Engineer newsletter.
- `not_found` means a candidate is absent from `ref/`. It doesn't prove you haven't read it.

Library check: 8 of 69 candidates already in your library (0 finished).
