# Recent Articles/Papers Likely to Inspire SASE's Current and Future Direction

Researcher: mus (5-researcher swarm, independent report)
Date: 2026-10-07
Prior-reading baseline: `research:202610/sase_related_reading_history.md` (compiled 2026-10-07 from `bob ref` + zorg records; 79 finished related reads, 86 started-but-unfinished in `ref/`, 19 more started in zorg records)

## Method and scope

I read the full related-reading history first, then did independent web research
(swarm rule: I did not look for or open the `__cdx` / `__cld` / `__grk` / `__gem`
peer reports, their transcripts, or any summaries of them).

Selection rules I applied:

1. **No duplicates of finished reads.** Gas Town, OpenAI Symphony, OpenAI Harness
   Engineering (Lopopolo 2026-02-11), Netclode, Muse subagent fanout, Kinney's
   memory digest, Zhou et al. filesystem memory (2607.26637), EA-Graph (2608.04278),
   Nakajima *The Log is the Agent* (2605.21997), Memory OS (2506.06326), and the
   Kerestecioglu human-inspired memory paper (2605.08538) are already finished and
   therefore **not** re-recommended below — they are cited only as the baseline
   each new item builds on.
2. **Started-but-unfinished items are flagged, not re-ranked as discoveries.**
   Where a started item (e.g. Anthropic context engineering, Agent Skills docs,
   PDL papers, spec-driven pieces) is genuinely load-bearing, I say so and tell
   you to finish it rather than pretending it is new.
3. **Recency + SASE-leverage.** Everything below is 2025-06 or later, most of it
   2025-12 to 2026-09, and each entry names the concrete SASE subsystem it bears
   on (beads/epics, macros/xprompts, memory webs, skills, goals, AXE/scheduler,
   gates/monitors/receipts, `just check`/CI, dispatch/workspaces, TUI, Rust core
   boundary, provider adapters).
4. **Verifiability.** URLs are ones I actually fetched or whose search-record
   snippets I inspected this session. arXiv IDs are given where they exist so a
   stale blog summary is never the only handle.

## What the baseline tells me about where SASE is headed

Three threads dominate your finished 2026 reads, and your own annotations point
at the next step in each:

- **Fleets of coding agents** (Gas Town, Symphony, Harness Engineering, Netclode,
  subagent fanout). Open question: when does multi-agent help vs. hurt, and who
  owns the write path?
- **Agent memory as files** (Kinney digest + Zhou filesystem-memory + Memory OS +
  human-inspired consolidation). Open question: who curates, what is gated, and
  how does verification evidence stay anchored instead of rotting?
- **Replay** — your own words, twice: "Support sase tool call replay?" (on *The
  Log is the Agent*) and "Materialize steps in workflow to enable replay starting
  at certain xprompt workflow steps?" (on Gas Town molecules). The event log wants
  to become executable, not just auditable.

The ranked list below is ordered by expected leverage on those threads, not by
citation count.

---

## Ranked reading list (read in this order)

### 1. The multi-agent argument, both sides — read as a pair

- **Cognition, "Don't Build Multi-Agents" (June 2025)** —
  `https://cognition.com/blog/dont-build-multi-agents`
  (redirect target of the `cognition.ai` URL; fetch it at the `cognition.com` address).
- **Cognition follow-up, "Multi-Agents: What's Actually Working" (April 2026)** —
  `https://cognition.com/blog/multi-agents-working`
- **Anthropic, "How we built our multi-agent research system" (13 June 2025)** —
  Anthropic engineering blog (multi-agent research system; widely cited as the
  counterpoint).

**Why read it (rank 1):** this is the debate that governs *this very swarm's*
design and SASE's macro-swarm / research-swarm future. The two sides look
opposite and are actually a task-type split, which is exactly what SASE needs as
a documented rule:

- Anthropic reports multi-agent beating single-agent by ~90% **on research**
  (read-only, parallelizable breadth work) at ~15x token cost, while explicitly
  saying the same shape works poorly for coding, where tasks share one decision
  context and agents coordinate badly in real time.
- Cognition argues parallel subagents fracture context for **write-heavy coding**
  because every edit embeds implicit decisions (style, edge cases, naming) that
  conflict when made blind — then concedes in 2026 that read-only/review fanout
  is fine.

The 2026 synthesis converging across secondary sources: **keep writes
single-threaded; let extra agents contribute intelligence, not actions; share
full traces, not just messages.** That sentence belongs, nearly verbatim, in a
SASE decision note next to *Native Helpers Return; Only Roots Declare*,
*Goals Host Binds*, and the research-swarm architecture. It also predicts when
your swarm design (independent researchers + lead synthesizer, i.e. single-writer
synthesis) beats a "swarm that co-writes one document."

**Status vs. your library:** the history lists *Don't Build Multi-Agents*,
*Inside the Multi-Agent Debate*, and several single-vs-multi essays as
**started, not finished**. Finish this pair before anything else below.

### 2. Anthropic, "Equipping agents for the real world with Agent Skills" (16 Oct 2025) + the Agent Skills open standard (agentskills.io, 18 Dec 2025)

- Engineering post:
  `https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills`
  (I fetched this page this session; verified live.)
- Standard: `https://agentskills.io/` — SKILL.md with YAML frontmatter
  (`name` + `description`), progressive disclosure (metadata preloaded →
  full SKILL.md on relevance → bundled scripts/resources on demand).
- Context: adopted across Codex, Copilot, VS Code, Cursor, Antigravity; open
  standard announced Dec 2025 (VentureBeat, Dec 2025 coverage).

**Why read it:** SASE's skills (macro skills, generated skills under
`src/sase/macros/skills/`, the `generated_skills` reference memory) are the same
construct under a different name — procedural knowledge as files. Three things
transfer directly:

1. **Progressive disclosure as context engineering.** SASE's core/reference/strand
   tiers and the preloaded-memory-size work are solving the same finite-context
   problem; the Skills spec is the industry's converged answer and SASE should
   either conform its skill frontmatter to it or document the delta.
2. **Composability over bespoke agents.** "Onboarding guide for a new hire, not a
   fragmented custom agent per use case" is the anti-sprawl argument for SASE's
   skill catalog vs. proliferating macro variants.
3. **Standardization risk/opportunity.** If skills become portable across harnesses
   (which the `adapters-normalize-harnesses` decision already bets on), SASE's
   generated skills could run outside SASE — and outside skills could be
   imported. Read the spec, not just the blog post.

**Status vs. your library:** Agent Skills material sits in your **started**
bucket (Equipping Agents post, Claude Agent SDK, skills guides). This is the one
started thread most worth finishing, because it standardizes while you are still
generating skills.

### 3. The Agentic AI Foundation: MCP + AGENTS.md + goose under the Linux Foundation (announced 9 Dec 2025)

- Linux Foundation press release:
  `https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation`
  (I verified the title/anchor this session.)
- Good explainers: WorkOS blog "The Linux Foundation Launches the Agentic AI
  Foundation" (10 Dec 2025); Agnost AI blog on MCP + AGENTS.md finding a new home.
- What moved: Anthropic donated MCP, OpenAI donated AGENTS.md, Block donated
  goose; AAIF membership reportedly reached ~146 orgs by Feb 2026.

**Why read it:** two of the three donated projects are SASE's direct
environment:

- **AGENTS.md is the README-for-agents convention** (plain Markdown, no YAML
  head, read at session start; emerged across Codex/Amp/Jules/Cursor mid-2025).
  SASE's memory-built instruction files and `AGENTS.md` revisions (which you
  annotated 26 times) now live inside a vendor-neutral standard. Track it or
  drift from it.
- **MCP (97M monthly SDK downloads, 10k+ public servers as of Mar 2026 per
  secondary reporting) is the tool protocol under the provider layer** your
  2025 backlog already studied (MCP intro, Descope, MCP-as-plugin-system). The
  foundation move answers the governance question your backlog left open.
- **goose is the reference agent framework** to compare against SASE's own
  harness/ACE rather than against closed Codex/Claude behavior.

Read the press release + one explainer; file anything deeper under provider
adapters, not SASE core.

### 4. Spec-driven development goes mainstream: GitHub Spec Kit (1.0, 21 Aug 2026), AWS Kiro (GA Nov 2025), Tessl ("spec-as-source")

- GitHub Spec Kit repo + `https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/`
  (Sept 2025 post; kit crossed ~111k stars June 2026, ~132k+ after, 1.0 Aug 2026
  per 2026 roundups).
- AWS Kiro (spec-native IDE; preview July 2025, GA Nov 2025; "40-hour features in
  under 8 hours of human time when authored as specs first" per customer cases
  cited in 2026 guides).
- 2026 guides: TheBCMS "Spec-Driven Development: The Definitive 2026 Guide";
  devtoollab "Spec-Driven Development in 2026"; ThoughtWorks calling SDD "one of
  the most important practices to emerge in 2025"; Karpathy (Feb 2026) on
  spec-first succeeding vibe-coding.

**Why read it:** SASE's plan/epic/bead chain *is* a spec-driven pipeline
(requirements → design → tasks → agent implementation → human review), and the
industry just converged on the same thesis from the other direction ("the spec
is the prompt"). Concrete takeaways:

- Spec Kit's artifact layout (spec → plan → tasks) is the format other teams'
  agents already emit; SASE's `/sase_plan` skill and epic/phase-bead layout
  should interoperate or justify the divergence.
- Reported effects (order-of-magnitude fewer regenerate-from-scratch cycles;
  3–10x first-pass success on non-trivial tasks) are the metric SASE's own
  plan quality work should be measured against.
- The lineage your history already half-read (Fowler on SDD/Kiro/spec-kit/Tessl,
  ThoughtWorks 2025, Red Hat on SDD quality) is now finishable as a settled
  practice, not a prediction.

**Status vs. your library:** all three SDD rows in the history are **started**.
Read the GitHub SDD post + one 2026 guide; treat the rest as reference.

### 5. Daunis, "A Declarative Language for Building and Orchestrating LLM-Powered Agent Workflows" (arXiv:2512.19769, 22 Dec 2025)

- `https://arxiv.org/abs/2512.19769` (I fetched the abstract page this session;
  verified.) Subjects cs.SE/cs.AI/cs.PL.
- Claim: same pipeline definition executes across backend languages (Java,
  Python, Go) and deployments (cloud-native, on-prem); common patterns (RAG,
  filtering, API orchestration) as DSL, not imperative code; native A/B testing
  of agent strategies with metric collection; PayPal e-commerce eval at millions
  of daily interactions: 60% dev-time reduction, 3x deployment velocity,
  <50 lines DSL vs 500+ imperative, sub-100ms orchestration overhead.

**Why read it:** this is the macro/xprompt lineage's industrial cousin —
"agent development from application programming to configuration." Two SASE
questions it answers with production data:

1. Does a declarative workflow layer actually pay? (Their answer: yes, at
   PayPal scale, with numbers.)
2. Can workflow A/B testing be native to the orchestrator rather than bolted on?
   (Compare SASE's size-alias effort ladder, guarded recipes, and the replay
   annotations — materialized steps + A/B variants + replay-from-step is one
   combined design.)

Discount appropriately: single-company eval, and "enables non-engineers to
modify safely" is asserted more than shown. Still the best production-grounded
brief for the declarative-workflow bet SASE has already made.

### 6. Gong, "SPL: Orchestrating Workflows with Declarative Deterministic-Probabilistic Composition" (arXiv:2607.07727, 6 Jul 2026)

- `https://arxiv.org/abs/2607.07727` (fetched this session; verified. 24pp, under
  review at TMLR.)
- Claim: one `.spl` spec composes GENERATE/EVALUATE (probabilistic) with
  SOLVE/ASSERT (deterministic: SymPy/SageMath/Lean) sharing syntax, bindings,
  and routing; runs unchanged across Ollama/OpenRouter/Anthropic/distributed
  grids; 78-recipe cookbook + 1,200-run controlled experiment; solver arm
  82–93% machine-verified correctness vs. unverified LLM-only fluency.

**Why read it:** SASE keeps deterministic checks (`just check`, Symvision,
gates, verdict receipts) *beside* probabilistic generation (macros, agents).
SPL puts them *inside one specification language* — ASSERT next to GENERATE —
which is the precise shape of "verification as part of the workflow, not after
it." Even if you never adopt the language, the GENERATE/EVALUATE vs.
SOLVE/ASSERT split is a cleaner vocabulary than SASE's current
generate-then-gate phrasing, and the backend difficulty gradient (SymPy 78% vs.
Sage 54%; dominant failure = solver_error, not format errors) is a useful prior
for where SASE's own verified-step ambitions will actually fail.

### 7. Bai & Eisner, "Accelerating Language Model Workflows with Prompt Choreography" (arXiv:2512.23049; TACL preprint, 28 Dec 2025)

- `https://arxiv.org/abs/2512.23049` (fetched this session; verified.)
- Claim: dynamic global KV cache across LLM calls in a multi-agent workflow;
  each call attends to an arbitrary reordered subset of previously encoded
  messages; 2.0–6.2x faster time-to-first-token per message, >2.2x end-to-end on
  redundancy-dominated workflows; fine-tuning helps the cached path mimic
  re-encoding.

**Why read it:** the multi-agent tax in item 1 (~15x tokens) and this swarm's
own cost (5 researchers × full context) are the same problem: multi-agent
workflows redundantly re-encode shared context. Prompt Choreography is the first
principled systems answer I found — cache once, choreograph attention — rather
than "use a cheaper model" or "write shorter prompts." For SASE: research
swarms, macro swarms, and any future where AXE schedules overlapping agents over
one repo are exactly the redundancy-dominated workflows this accelerates. Read
for the mechanism (global reordered-subset cache + fine-tune-to-mimic), not the
headline speedup, which is workload-dependent.

### 8. Ke, "Quine: Realizing LLM Agents as Native POSIX Processes" (arXiv:2603.18030, 8 Mar 2026)

- `https://arxiv.org/abs/2603.18030v1` (verified via search record this session.)
- Claim: no new application-layer orchestrator; agents *are* POSIX processes
  (identity = PID, interface = stdio/exit status, state = memory + env +
  filesystem, lifecycle = fork/exec/exit); reference runtime + manuscript at
  `github.com/kehao95/quine`.

**Why read it:** SASE's runtime is currently application-layer: ephemeral
`sase_<N>` workspaces, named procs, oneshot/service procs, `%dispatch` to
remote machines, host-bound goals. Quine is the strongest contrarian brief that
the OS already *is* the orchestrator — isolation, scheduling, and
communication via POSIX rather than reimplemented per-harness. You will likely
reject the strong version (SASE needs beads, gates, and audit that PIDs don't
provide), but the paper forces the useful question: which half of SASE's
process machinery is load-bearing product (holds, receipts, ledger) and which
half is reimplemented `fork`/`exec`/scheduler that should defer to the OS?
Short paper, high conceptual yield for the dispatch/AXE/service-proc future.

### 9. Orlanski et al., "SlopCodeBench: Benchmarking How Coding Agents Degrade Over Long-Horizon Iterative Tasks" (arXiv:2603.24755, Mar 2026, rev. May 2026)

- `https://arxiv.org/abs/2603.24755` (+v2).
- Claim: 36 problems / 196 checkpoints where agents repeatedly extend their own
  solutions with evolving specs demanding architectural decisions; 15 coding
  agents; **no agent fully solves any problem end-to-end; best passes 14.8% of
  checkpoints**; agent code ~2.2x more verbose than human repos; structural
  erosion rises in ~80% of trajectories.

**Why read it:** this is the empirical shadow of Harness Engineering's
"entropy and garbage collection" chapter (which you finished) and the bead
problem in miniature: iterative agent work rots its own structure unless
something outside the agent prunes, consolidates, and re-architects. Connects
directly to Symvision lint, `sase memory read` gating, `/sase_new_task`
dedup, bead history/lossless archival, and the filesystem-memory finding that
organization erodes except under strong management agents. If SASE wants one
benchmark to adopt as its regression signal for long-horizon quality, start
here — and note its implication that functional pass-rate alone systematically
underestimates iterative risk.

### 10. "Verifiable Receipts for AI Agent Work: An Open Spec (v0.3)" (dev.to, 19 Sep 2026) + the Terminal-Bench harness-scaling result

- Spec post (v0.3, post-adversarial-verification):
  search "Verifiable Receipts for AI Agent Work" (rambozambo, dev.to, Sep 2026).
  Proposes per-claim receipts (relay URL + event id + timestamp) and a "3-check
  fix" for "my coding agent lied about completing the task."
- Benchmark signal: LangChain's harness-only optimization moving a frozen model
  from outside Terminal-Bench 2.0's top 30 to **5th place** without changing a
  weight (reported in Shane Wang's 2026 harness roundup), plus
  **LemonHarness** technical report (arXiv:2606.24311): 84.5–86.5% on
  Terminal-Bench 2.0 via unified runtime boundary + callable rules + time-aware
  execution.

**Why read them together:** SASE's *Receipts Prove Before They Skip*,
*Triage Annotates (KNOWN needs an independent witness)*, and EA-Graph's
artifact-anchored verification (already finished) all say the same thing these
say operationally: **claims must cite the artifact content that established
them, and the harness is now the benchmark.** Terminal-Bench is, per the
harness-optimization community, "the single best benchmark for harness
research" precisely because it publishes head-to-head harness variants with the
model held fixed. That is the measurement posture SASE's two-speed CI
(`just check` fast gate + scheduled exhaustive matrix) should copy: hold the
model fixed, vary the harness, keep baseline receipts.

### 11. Finish-your-started-read: Anthropic, "Effective Context Engineering for AI Agents" (29 Sep 2025)

- `https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents`
  (I fetched this page this session; verified live.)
- Core content: context rot / lost-in-the-middle, compaction (summarize-in-place
  over a sliding window, prune raw events), prompt layering, tool/MCP budget as
  finite curated resource; "what configuration of context produces the desired
  behavior" as the harness design question.

**Why finish it (not new, but highest-ROI unfinished):** your history shows it
as started, and everything in items 2, 7, and 9 assumes it. It is also the
missing citation behind SASE positions you already hold: core-vs-reference-vs-
strand tiers, preloaded-memory-size visibility, compaction vs. archival, and why
`just check` stays small. Read it once, then stop citing secondhand summaries
of it.

---

## What I deliberately left out

- **Anything already finished** (see selection rule 1) — including Zhou
  filesystem-memory, EA-Graph, *The Log is the Agent*, Memory OS, and Harness
  Engineering itself. The history's "already read" + "comparison report exists"
  (`202610/openai_harness_engineering_vs_sase`) means re-recommending them would
  waste your attention.
- **The 2025 zorg-era harness docs** (Claude Code tutorials, Gemini CLI docs,
  MCP intros, function-calling guides): superseded by items 2–3 above as the
  maintained standards.
- **LangGraph durability manuals, Awesome-Harness-Engineering lists, and
  practitioner workflow essays** (Osmani, Reed, Pragmatic Engineer): useful
  context, but they converge on "small tools, evals, guardrails before
  multi-agent" — which item 1 states with primary-source evidence.
- **Google-internal docs** counted but unnamed in the history: out of scope for a
  public-repo report.

## Gaps and confidence notes

- I verified the arXiv abstract pages for 2512.19769, 2607.07727, and 2512.23049
  by fetch this session, and the Anthropic context-engineering + Agent Skills
  pages likewise. Cognition URLs, Spec Kit star counts, AAIF membership figures,
  and SlopCodeBench/Terminal-Bench numbers come from search records and
  secondary reporting — treat the numbers as approximate and confirm against the
  primary source before citing them.
- I did not read full paper PDFs (abstracts + primary blog posts + launch
  records only); the ranking is by expected SASE leverage, not by methodological
  endorsement.
- Two history items deserve a library-hygiene note, not a reading slot: Hassan
  et al. 2509.06216 (the paper that named SASE/ACE) sits as **queued/unread** —
  if you have read it, the `bob ref` entry is stale; if not, it outranks
  everything above. And the 86 started + 19 zorg-started items are a
  finish-or-drop decision the history already stages for you.

## Bottom line

If you read only three: **the Cognition/Anthropic multi-agent pair (1)** to
settle SASE's single-writer rule, **the Agent Skills spec (2)** to keep SASE's
skill system standard-shaped, and **SlopCodeBench (9)** as the long-horizon
degradation benchmark that justifies SASE's gates, pruning, and receipts. The
rest convert adjacent bets SASE already made (specs, declarative workflows,
POSIX runtime, KV-cache choreography, AAIF standards, context engineering) from
intuition into cited, measured positions.
