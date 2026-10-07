# Recent literature to inspire SASE's current and future direction

_Independent swarm report from researcher `grk`, 2026-10-07. Built against
`research:202610/sase_related_reading_history.md` and the live Bob library. Peer swarm
reports from this round were not consulted._

## TL;DR

SASE's distinctive bets are already visible in 2026 literature: **host-owned mutation**,
**receipt-bound claims**, **single-turn ticks with durable state outside the context
window**, **isolated evidence gathering before synthesis**, and **instruction budget as a
first-class design object**. The field named the product "Structured Agentic Software
Engineering" a year ago; the last four months of papers are the first wave that
operationalizes those pillars instead of restating them.

**If you read only five:**

1. Hassan et al., *Agentic Software Engineering* v3 (the namesake paper; still queued unread).
2. Santos Filho, *ESAA* (agents emit intentions; a deterministic host mutates state and
   verifies replay).
3. Wang, Xu, Li, Peng, Adams, Hassan, Chen, *Ledger* (execution state as a runtime layer
   around an unmodified coding agent).
4. Krentsel, Agarwal, Cemri, Liu et al., *Reality Is the Final Verifier* (the two-gap
   account of why `just check` cannot be the last word).
5. Liu and Han, *What Does a Harness Buy? Tokens, Mostly* (the strongest published
   challenge to treating the harness as a SWE-bench lever).

Two independent annotations in the related-reading history already asked for **replay**.
Three of the five above are the replay/receipt/host-mutation cluster. That is the
clearest current-direction thread.

## How this list was built

| Step | What was done |
| --- | --- |
| Prior reading | Audited read of `research:202610/sase_related_reading_history.md` (79 finished SASE-related reads; 86 started). Finished 2026 work clusters on fleet orchestration (Gas Town, Symphony, Harness Engineering, Netclode, Muse fanout) and agent memory (Kinney, Zhou filesystem memory, EA-Graph, *The Log is the Agent*, Memory OS, Kerestecioglu). |
| Project bets | Mapped candidates onto SASE decisions already in core memory: single-turn agents, host-owned completion, goal ledger, receipts-before-skip, corpus-before-mechanism, adapters-normalize-harnesses, gates-never-block, rust-core-required, goals-host-binds. |
| Search | arXiv HTML/abstracts and a smaller set of 2026 practitioner pieces (Restate, Bain) from roughly 2025-09 through 2026-10-06, biased toward papers that name harness, receipt, ledger, swarm isolation, skill disclosure, or durable execution. |
| Dedup | Dropped anything the related-reading history marks **finished**. Kept queued/started library items only when they remain the highest-leverage unread item in their cluster. |
| Library | `bob ref find` on 45 unique URLs plus overlapping titles. |

This is a **direction** list, not a survey. SWE-bench incremental papers, generic
multi-agent surveys, and Claude Code tip lists were left out unless they change a SASE
design question.

## What SASE is already betting on

The ranking is relative to these bets, not to "agentic SE" in general.

| SASE bet | What a useful paper would do |
| --- | --- |
| Single-turn agents; continuation is mechanical | Treat the *tick* / turn as the unit of autonomy, with state that outlives the context window. |
| Host-owned completion | Separate cognitive intention from mutation; the agent proposes, the host commits. |
| Goal ledger; goals host binds | Keep an explicit, host-owned account of what is still open, who owns it, and when to stop. |
| Receipts prove before they skip | Bind claim, evidence, execution prefix, and artifact version so a pass cannot be transplanted. |
| Memory webs; corpus before mechanism | Prefer authored Markdown, typed events, and on-demand load over a retrieval layer. |
| Adapters normalize harnesses | Study production harnesses as platforms SASE wraps, including cost and instruction budget. |
| Research swarms | Isolate evidence gathering, then synthesize; treat human review as the scarce resource. |
| Two-speed verification | Distinguish the inner implementation–verification loop from an outer assurance loop. |

Replay is the annotation that keeps coming back (Gas Town molecules; *The Log is the
Agent*). Papers that make replay an executable contract outrank papers that only
describe long-horizon agents.

## Gaps the finished 2026 reading does not cover

The finished 2026 set is strong on **fleet control planes** and **token-level memory**.
It is thin on five things that 2026 papers now treat as first-class:

1. **Host-owned mutation as architecture**, not as a git policy. ESAA and Ledger make
   this a runtime, not a convention.
2. **Joint receipts.** EA-Graph anchors verification claims to artifact content. It does
   not bind the emitted claim to the ordered execution prefix and the source version
   together. *Actions with Receipts* does.
3. **The outer assurance loop.** Symphony names human attention as the bottleneck.
   Berkeley's two-gap paper says *why* more inner-loop tests cannot close it.
4. **Isolated search before consensus.** SASE research swarms already refuse peer reads
   during gathering. ArcticSwarm and GitSwarm are the first 2026 papers that measure
   that design.
5. **Harness as cost surface.** OpenAI's Harness Engineering essay (finished 2026-10-03)
   is a success story. *What Does a Harness Buy?* is the counter-measurement: same
   model, three production harnesses, cost differs by 3×, SWE-bench almost does not.

## Ranked list

Each entry says **what it is**, **why it belongs on a SASE desk now**, and **what to
steal or argue with**. Library state is labeled in the header.

### Rank 1 — Hassan et al., *Agentic Software Engineering: Foundational Pillars and a Research Roadmap* (v3)

- **Link.** <https://arxiv.org/abs/2509.06216> (v3, 24 Jun 2026; first posted 7 Sep 2025)
- **Authors.** Ahmed E. Hassan, Hao Li, Dayi Lin, Bram Adams, Tse-Hsun Chen, Yutaro
  Kashiwa, Dong Qiu (Queen's, Concordia, NAIST, Huawei Canada)
- **Library.** Already in your library (**queued** since 2025-11-28, legacy `unread`,
  `ref/ai/agent_ref/agent_swe.md`). This is the highest-leverage unread item in the
  related-reading history. If you have read it, the library entry is stale.

**What it is.** The paper that named Structured Agentic Software Engineering. SE 3.0 is
goal-oriented agent work, not code completion. It splits the field into SE-for-humans
and SE-for-agents, then rebuilds the four pillars (actors, processes, tools, artifacts)
for each. The two workbenches are the **Agent Command Environment (ACE)** — human
command center, inbox of Merge-Readiness Packs and Consultation Request Packs — and the
**Agent Execution Environment (AEE)**. Structured artifacts carry the dialogue:
BriefingScript, LoopScript, MentorScript from humans; CRP and MRP from agents; Version
Controlled Resolutions back. The speed-vs-trust numbers it cites (median agent PR
turnaround 13.2 minutes; 29.6% of plausible fixes introduce regressions; SWE-bench
solve rate collapsing under manual audit) are the empirical case for host-owned
completion.

**Why you should read it.** SASE-the-product already occupies the ACE slot this paper
sketches. Reading v3 is how you decide which of BriefingScript / MentorScript / MRP /
CRP / VCR are vocabulary to adopt, which you have already built under other names
(beads, gates, receipts, `sase final`, Mentor-like memory), and which remain open
research. The related-reading history called this out as the one queued item worth
reading next. That is still true, and v3 is nine months newer than the queued capture.

**Steal or argue.** Steal the MRP as an evidence bundle on a stitch, not as a PR
template: tests, hygiene, rationale, briefing hash, trajectory id. Argue with the
implication that ACE is a review inbox of packs; SASE's TUI is closer to a live fleet
console. The paper is a vision scaffold, not a system.

### Rank 2 — Santos Filho, *ESAA: Event Sourcing for Autonomous Agents in LLM-Based Software Engineering*

- **Link.** <https://arxiv.org/abs/2602.23193> (26 Feb 2026)
- **Authors.** Elzo Brito dos Santos Filho
- **Library.** Not in `ref/`.

**What it is.** Event Sourcing applied to coding agents. The LLM is a cognitive layer
that may emit only validated JSON intentions (`agent.result` or `issue.report`). A
deterministic orchestrator validates the schema, appends to `activity.jsonl`, applies
file effects, and projects `roadmap.json`. Boundary contracts live in
`AGENT_CONTRACT.yaml`. `esaa verify` hashes the log and checks that completed tasks are
immutable. Two case studies: 9 tasks / 49 events (single agent) and 50 tasks / 86 events
with four concurrent heterogeneous LLMs (Claude Sonnet 4.6, Codex GPT-5,
Antigravity/Gemini 3 Pro, Claude Opus 4.6). MIT reference implementation `esaa-core`.

**Why you should read it.** This is the architectural form of two things you already
annotated: "Support sase tool call replay?" and "Materialize steps in workflow to enable
replay starting at certain xprompt workflow steps." It is also the cleanest published
cousin of **host-owned completion**: agents do not write the tree; they propose
intentions; the host mutates. SASE currently lets the agent write in an ephemeral
workspace and then withholds git commit/PR from the agent. ESAA pushes the same
separation one layer down, to every file write. That is a live design fork, not a
metaphor.

**Steal or argue.** Steal the verify-on-hash replay and the "intention vs effect"
split for ToolRun records. Argue whether SASE should keep write-capable workspaces
(Muse fanout, `sase_<N>`) and only host-own the *land*, or host-own mutation the way
ESAA does. The case studies are small; the pattern is the value.

### Rank 3 — Wang, Xu, Li, Peng, Adams, Hassan, Chen, *Turning Interaction History into Execution State: A Runtime Layer for Long-Horizon Coding Agents*

- **Link.** <https://arxiv.org/abs/2608.00808> (1 Aug 2026)
- **Authors.** Zehao Wang, Yisen Xu, Chenglin Li, Chao Peng, Bram Adams, Ahmed E.
  Hassan, Tse-Hsun Chen (Concordia, Tencent, Queen's)
- **Library.** Not in `ref/`.

**What it is.** A deterministic **Ledger** around an unmodified coding agent. Trajectories
record what happened; they do not record which observations still describe the
repository. Ledger distills completed interactions into execution state (observed /
modified / attempted) and applies it at two boundaries of every step: **inform**
(compact runtime view appended to the prompt) and **govern** (reuse a still-valid
earlier result; flag redundant repetition). No extra model calls. On all 500 SWE-bench
Verified instances: Pass@1 56.2% → 64.2% (GPT-5 mini) and 75.8% → 81.0% (MiniMax M2.5),
with 28.9% and 31.8% lower cost. Attached to Codex: +3.4 points at 24.4% lower cost.
Ablation: govern drives resolution; inform drives efficiency.

**Why you should read it.** Same research group as Rank 1, one year later, with
numbers. This is the AEE-side companion to ACE: a runtime that keeps execution facts
out of the model's implicit reconstruction. It maps onto ToolRun (`record-before-admit`),
receipts, and the reason single-turn agents forget which files they already read. It
also gives a concrete alternative to LLM summarization of transcripts, which
Lindenbauer et al. (cited here) already found no better than masking old observations.

**Steal or argue.** Steal inform/govern as two paths over one execution ledger, and the
rule that the runtime maintains only mechanically derivable facts. Argue whether SASE
should attach this *inside* each provider adapter or *above* them in `sase_core`,
wrapping every harness the way Ledger wrapped mini-SWE-agent and Codex.

### Rank 4 — Krentsel, Agarwal, Cemri, Liu et al., *Reality Is the Final Verifier: On Two Key Gaps in Agentic Software Engineering*

- **Link.** <https://arxiv.org/abs/2609.12039> (10 Sep 2026)
- **Authors.** Alexander Krentsel, Shubham Agarwal, Mert Cemri, Shu Liu, Sidharth
  Sankhe, Ziming Mao, Matei Zaharia, Ion Stoica (UC Berkeley)
- **Library.** Not in `ref/`.

**What it is.** A two-gap framework. The inner loop revises implementation `P` until
evaluator `E` accepts it against requirements `R` under environment model `M`. Two gaps
sit outside that loop: the **requirement gap** (`R` vs stakeholder intent `I`) and the
**model gap** (`M` vs the real world `W`). Reward hacking exploits omissions in `R` or
`M`; hallucination widens them. Neither gap can generally be certified closed in an
open world, so the work is an outer **assurance–revision loop** that uses deployment
evidence to revise `R`, `M`, or `E`. Assurance is then a resource-allocation problem
over human judgment, agent capability, and compute. The two bottlenecks: accountable
human judgment (requirement gap) and faithful, costly evaluation (model gap).

**Why you should read it.** This is the theory under *Receipts Prove Before They Skip*,
*Triage Annotates*, two-speed CI, and host-owned completion. `just check` is an inner
loop. A green inner loop is a proxy. The paper says the quiet part: adding more
reviewing agents cannot close the gaps when they share the same incomplete artifacts.
Symphony already told you human attention is the bottleneck (3–5 interactive sessions).
This paper says what that attention is *for*.

**Steal or argue.** Steal the inner/outer loop split as vocabulary for ACE: inner =
agent + `just check`; outer = human settlement of a goal, CRP-like gates, and
deployment evidence. Argue how far SASE should go toward treating every land as a
provisional acceptance that an outer loop can reopen. The Next.js "propose / human
queue / reopen" pattern from the goals reading list sits here.

### Rank 5 — Hu, Hu, Guo, Wang et al., *Actions with Receipts: Jointly Binding Claims, Evidence, and Execution for Replayable Tool-Agent Auditing*

- **Link.** <https://arxiv.org/abs/2610.00327> (29 Sep 2026)
- **Authors.** Miaobo Hu, Shuhao Hu, Xiaobo Guo, Xin Wang, Bokun Wang, Yina Sa, Daren
  Zha, Jun Xiao (UCAS / IIE)
- **Library.** Not in `ref/`.

**What it is.** A claim-anchored execution contract. A valid citation and a valid trace
can both be well-formed while being transplanted across claims, actions, runs, or source
versions. The receipt jointly binds: the emitted claim, its exact source span, the
ordered execution prefix, and the source version/access state. Integrity is separated
from a pluggable support (entailment) plane. Seven independently testable properties,
including persisted-object replay and execution-rerun consistency. 1,275 / 1,280
cross-object substitution attacks detected (0.9961); dropping any one property collapses
detection of that attack family to 0.0156–0.0625.

**Why you should read it.** EA-Graph (finished 2026-10-03) anchors a verification claim
to artifact content and allows an **unprovable** verdict. This paper is the next
engineering step: the association itself is the auditable object, and replay is a
verifier, not a log viewer. That is the missing half of "Support sase tool call replay?"
It also matches *Receipts Prove Before They Skip* almost verbatim: a pass is not a skip
right unless the receipt reconstructs.

**Steal or argue.** Steal the integrity/support split (structural validity is not
entailment) and the seven properties as a checklist for ToolRun + artifact-link +
verdict receipts. Argue how much cryptography SASE needs versus content hashes and
ordered event logs you already have. The paper is security-flavored; the design is
portable.

### Rank 6 — Nijkamp, Koul, Pakhomov, Pang, *An Architecture for Long-Horizon Agents: Levels, Ticks and Cascaded Intelligence*

- **Link.** <https://arxiv.org/abs/2609.19519> (17 Sep 2026)
- **Authors.** Erik Nijkamp, Anurag Koul, Egor Pakhomov, Bo Pang (Salesforce AI Research)
- **Library.** Not in `ref/`.

**What it is.** A long-horizon agent must run continually without forgetting *before* it
can learn continually, and that ability lives in the harness. Seven bottlenecks follow
from `C, P, A, F ≪ H` at high autonomy (context, process, human attention, failure
interval all much shorter than the horizon). The answer is a hierarchy of **levels**
indexed by time scale, each with a bounded file summarizing the level below; a clocked
**tick** as the unit of autonomous action; and **cascaded intelligence** (escalate to a
stronger model only after failing review). Ten-day campaign: an agent reproduced a
published RL result with a human attending once a day, across every context reset, with
early operating knowledge changing later behavior without weight updates.

**Why you should read it.** This is the best 2026 statement of why SASE is a single-turn
system that still runs campaigns. A SASE turn is a tick. Mechanical continuation, AXE,
monitors, and the goal ledger are how a campaign outlives `C`, `P`, and `A`. Cascaded
intelligence is the size-alias effort ladder with a review gate. Bounded per-level
files are core / reference / strand memory with a hard line budget (they cap a level at
forty lines of any log). The "standing decisions" read at every wake are host-bound
goals.

**Steal or argue.** Steal ticks, standing decisions, resume-from-checkpoint-then-journal,
and escalate-only-after-failed-review. Argue with the implication of a continually
running driver; SASE's single-turn contract says the agent never promises to resume, and
the host manufactures the next tick. That disagreement is productive.

### Rank 7 — *ArcticSwarm: Deferring Early Consensus in Long-Horizon Multi-Agent Research*

- **Link.** <https://arxiv.org/abs/2609.01870> (1 Sep 2026)
- **Library.** Not in `ref/`.

**What it is.** Multi-parallel generate-and-verify works when a verifier exists (coding).
Open-ended research has no such verifier, and early consensus collapses search.
ArcticSwarm separates evidence gathering from integration. Subagents publish to a
shared bulletin board. **Gated isolation** lets selected search tasks keep their own
prior. Structured review at three commitment boundaries propagates only confident
candidates. BrowseComp-Plus: 82.6% with Qwen 3.5-27B vs 78.8% without gated isolation
and 74.5% with review also off. Live-web BrowseComp with GPT-5: 73.6% vs 54.9%
(provider system) and 63.4% (MiroFlow).

**Why you should read it.** This swarm's standing instruction is the same design:
independent researchers, no peer-report reads, a later lead synthesis. ArcticSwarm is
the first paper I found that *measures* isolation during gathering. It is the research
program for `#research_swarm`, including the risk that a shared bulletin board too
early is how swarms agree on a wrong story.

**Steal or argue.** Steal gated isolation and commitment boundaries as swarm-xprompt
policy, not as folklore. Argue whether SASE's "do not read the peer report" is enough,
or whether a typed bulletin board with review gates (artifact links, not free-form
chat) is the missing piece.

### Rank 8 — *GitSwarm: Decentralized Compounding Inference*

- **Link.** <https://arxiv.org/abs/2610.04862> (4 Oct 2026)
- **Library.** Not in `ref/`.

**What it is.** **Compounding inference:** organize inference-time compute so intermediate
work persists and later compute can inspect, extend, combine, or challenge it.
GitSwarm is an asynchronous system of homogeneous agents that decide how to advance a
task while collaborating through structured persistent memory in a shared, branch-able
Git repository. Atomic commits keep intermediates; explicit semantic dependencies
record how later work builds on earlier branches. IMOProofBench-Advanced: all 30
problems in one run with GPT-5.5. ProgramBench: 79.4% vs 65.1% strongest reported
baseline. On ProgramBench, 94.7% of contributions are subsequently built upon; the
selected solution's ancestry covers 82–93% of the contribution graph.

**Why you should read it.** SASE already compounds through git (ephemeral workspaces,
patches, stitches, hidden clones, pull-based auto-sync). GitSwarm names that as the
inference paradigm, not as VCS hygiene. The ancestry coverage numbers are a metric
SASE could put on research swarms and epic phases: did later work actually build, or
did it restart?

**Steal or argue.** Steal semantic dependencies across branches as a first-class
artifact-link relation (close to `derives-from` / `implements`). Argue that SASE's
host-owned land is the right place to compound, and that write-capable children in
worktrees are GitSwarm already — if the host records the ancestry.

### Rank 9 — Malo and Qiu, *PROJECTMEM: A Local-First, Event-Sourced Memory and Judgment Layer for AI Coding Agents*

- **Link.** <https://arxiv.org/abs/2606.12329> (v2, 30 Sep 2026)
- **Authors.** Ripon Chandra Malo, Tong Qiu (University of Utah)
- **Library.** Not in `ref/`.

**What it is.** Local-first, append-only plain-text log of typed events (issue, attempt,
fix, decision, note), deterministically projected into compact summaries and served
over MCP. **Memory-as-Governance:** a file-scoped advisory precheck, invoked before an
edit, returns recorded failures, open issues, and churn for that file. Six-month
self-study: 3,228 events, 27 projects; 86 of 427 issues closed by a recorded fix had
at least one prior failed attempt. Median analysis of a 1,500-event log: 42.0 s → 79.3
ms. They are careful: those histories are *candidates* for later warnings, not proof
that warnings prevented repeats. Code: `github.com/riponcm/projectmem`.

**Why you should read it.** Closest published system to SASE memory + beads + "do not
repeat a failed approach" as a host check. Zhou et al. (finished) studied filesystem
Markdown memory in general. PROJECTMEM is the coding-agent specialization with
event-sourcing and a governance gate. It also inherits Ink & Switch local-first
(already in the zorg-era finished set) without pretending a vector index is the
product. *Corpus before mechanism* lives here as an implementation.

**Steal or argue.** Steal typed events, deterministic projection, supersession of
decisions, and the pre-edit advisory. Argue that SASE should keep this in `sase_core`
(Rust, SQLite read models) rather than as an MCP sidecar, and that `/sase_new_task`'s
semantic-duplicate check is the bead-level version of the same gate.

### Rank 10 — Liu and Han, *What Does a Harness Buy? Tokens, Mostly*

- **Link.** <https://arxiv.org/abs/2610.04433> (3 Oct 2026)
- **Authors.** Yangze Liu, Zhongyi Han
- **Library.** Not in `ref/`.
- **Code.** <https://github.com/YangzeLiu/what-does-a-harness-buy>

**What it is.** Five models through three production harnesses (Claude Code,
mini-SWE-agent, OpenCode) on SWE-bench Verified, with reruns to measure noise. On 447
tasks, the heaviest and lightest harness are equivalent within five points. On a
45-task hard subset, swapping the harness flips as many tasks as rerunning the same
harness (13% both ways), and the tasks a harness wins do not repeat. The one clear
harness effect is a *loss* (OpenCode, output cap). What the harness decides is the
**bill**: up to 3× cost per task, set at the first call by the preamble of system
prompt and tool schemas, scaled by step count. Cached-input price scales the bill; it
does not reorder harnesses. 45 tasks catch a 13-point gap only half the time.

**Why you should read it.** You finished OpenAI's Harness Engineering essay three days
ago. That essay is a 0-handwritten-lines, 1,500-PR success story. This paper is the
measurement that says: on SWE-bench, the harness is mostly a token tax. SASE's product
bet is that the OS around models *is* the work — completion, goals, receipts, memory,
gates, ACE. If you evaluate SASE on SWE-bench deltas, this paper predicts you will
measure noise. If you evaluate SASE on cost, instruction budget, land quality, and
human attention, this paper is an ally.

**Steal or argue.** Steal "preamble × steps = bill" as the budgeted-router objective,
and their power analysis as a warning against harness A/B tests on small task sets.
Argue that SASE is not competing with Claude Code on SWE-bench; it is competing with
tmux-and-hope on campaigns. This paper is how you keep that argument honest.

### Rank 11 — Barbaste, Darrigol, Vu, Wiltberger, *Harness Engineering: Anatomy, Architecture, and Evolution of Coding Agents — A Source-Code Study of Eleven Systems*

- **Link.** <https://arxiv.org/abs/2609.00006> (15 Jul 2026; expanded edition of an April
  2026 study)
- **Library.** Not in `ref/`. 83 pages.

**What it is.** Source-level anatomy of Claude Code, Codex CLI, Gemini CLI, Mistral
Vibe, OpenHands, Aider, Mini-SWE-Agent, Hermes, Pi, OpenCode, OpenClaw, plus Omnigent
as a meta-harness. Seven canonical subsystems, 13 observations, 29 patterns. Across
~4M lines of Python/TypeScript/Rust: **no runtime imports a general-purpose agentic
framework**, and **none retrieves code with vector embeddings**. Skills lead MCP (9/11
vs 8/11). ACP ships in six systems with a new role: harness hosting. Longitudinal
diff of the original eight over one quarter: convergence becoming imitation; behavioral
policy migrating from prompt prose to configuration. Thesis: in H1 2026 the coding
harness turned from tool to **platform**. Closes with 18 design recommendations and a
90-line minimum-viable-harness scaffold.

**Why you should read it.** SASE wraps these CLIs. *Adapters Normalize Harnesses* needs
an empirical map of what is being normalized. Two findings land on existing
decisions: no vector retrieval (corpus before mechanism), and skills as the extension
surface (SASE skills / macros). ACP-as-host is the generic provider work. The
tool-to-platform turn is the strategic question behind a SASE rename (sasesh / sasos):
are you an orchestrator of CLIs, or the OS they run on?

**Steal or argue.** Steal the seven-subsystem map as the adapter checklist, and
"policy migrated from prompt prose to configuration" as a warning for core memory
bloat. Argue that SASE should remain the layer *above* these platforms (LaunchApproval,
goals, beads, finalizers) rather than becoming the twelfth harness.

### Rank 12 — Zhang, Hu, Upasani et al., *Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models*

- **Link.** <https://arxiv.org/abs/2510.04618> (v3, 29 Mar 2026; ICLR 2026)
- **Authors.** Qizheng Zhang, Changran Hu, Shubhangi Upasani, Boyuan Ma, Fenglu Hong,
  Vamsidhar Kamanuru, Jay Rainton, Chen Wu, Mengmeng Ji, Hanchen Li, Urmish Thakker,
  James Zou, Kunle Olukotun
- **Library.** Already in your library (**queued** since 2026-01-19, legacy `unread`,
  `ref/ai/agent_ref/agent_context_eng.md`).

**What it is.** Contexts as evolving **playbooks**. Generator / Reflector / Curator.
Incremental delta updates to avoid **brevity bias** (summaries drop domain insight) and
**context collapse** (iterative rewrite erodes detail). Works offline (system prompts)
and online (agent memory). +10.6% on agents, +8.6% on finance; matches a top AppWorld
agent with a smaller open-source model, using natural execution feedback rather than
labeled supervision.

**Why you should read it.** SASE memory-write routing, memory-built instruction files,
and the budgeted instruction router are this paper's setting. Kinney (finished, 29
highlights) already pushed you toward "flat until a retrieval need appears" and
token-level design. ACE is the strongest recent argument for *structured incremental
curation* of those tokens — which is what `/sase_memory_write` plus memory task beads
are for — without jumping to an embedding index.

**Steal or argue.** Steal generator/reflector/curator as roles for memory edits, and
"incremental deltas, not rewrite the playbook" as a constraint on instruction-file
migration. Argue that SASE should keep a human (or a gated agent) as Curator; the
filesystem-memory paper you finished says organization erodes unless the management
agent is strong.

### Rank 13 — Zhang, Zhao, Mudgal, Ammar, Cui, Chu, Blanken, *Report: Progressive Disclosure of Agent Skills*

- **Link.** <https://arxiv.org/abs/2609.35692> (28 Sep 2026)
- **Authors.** Guilin Zhang, Kai Zhao, Priyanka Mudgal, Waleed Ammar, Xiquan Cui, Xu
  Chu, Alet Blanken (Workday)
- **Library.** Not in `ref/`.
- **Pair with.** *Is Progressive Disclosure All You Need for Long-Context Agents?*
  <https://arxiv.org/abs/2607.17598> (20 Jul 2026) — one disclosure level is enough;
  a second routing level never helps and sometimes hurts.

**What it is.** Production measurement from Workday agents. Skills (named procedures)
in context grow cost with library size. Progressive disclosure (frontmatter of every
skill, full body on demand) improves skill-retrieval quality, slightly raises latency,
and prevents the N=100 eager-load crash. The companion paper finds the gain is
**context, not intelligence**: redundant when a strong harness already navigates; decisive
once the corpus is too large to read.

**Why you should read it.** This is the empirical brief for SASE skills, macros, and
the budgeted instruction router. Core memory is eager. Reference memory and strands are
disclosure level one. A second, learned router is the thing the companion paper says
not to add until the corpus forces it — which is *corpus before mechanism* with a
citation.

**Steal or argue.** Steal "frontmatter always, body on demand" as the skill/macro
loading rule, and the finding that recoverability of elided content is machinery
models rarely use (also in Rank 16's harness-design study). Argue against a clever
skill retriever until `sase memory read` and skill frontmatter fail in measured ways.

### Rank 14 — Gusev and Bernal Neira, *AI Agent Swarms as Researchers: Progress, Challenges, and Open Questions*

- **Link.** <https://arxiv.org/abs/2609.35719> (28 Sep 2026)
- **Authors.** Sergey Gusev, David E. Bernal Neira
- **Library.** Not in `ref/`.

**What it is.** Off-the-shelf coding-agent swarms given a scope, literature, compute,
and "make real, correct, useful progress, and do not stop" — no scientific ideas
supplied. Within weeks: research notes, paper-length drafts, and formal proofs in five
areas of optimization and physical science; proposed lab experiments in a sixth. They
do not claim all of it is correct or new; in what they checked, no major scientific
error, and several results are in a proof assistant. Production outran review: a full
review would take months. The questions are institutional: how to trust results when
review is scarce; what credit means when the human input is a prompt; how people learn
a field they cannot keep up with.

**Why you should read it.** SASE already runs research swarms and is building
`sase-listen` so commute time can absorb review. This paper is the cultural and
operational brief for that bet. Rank 7 (ArcticSwarm) is the isolation mechanism; this
is the *review bottleneck* once isolation works. Symphony's 3–5 interactive sessions
is the same bottleneck in product engineering.

**Steal or argue.** Steal "review, not production, is the scarce resource" as an ACE
design constraint (MRPs, listen editions, gates that never block the agent). Argue that
SASE's job is to make review cheaper and more honest (receipts, isolation, host-owned
synthesis), not to make the swarm louder.

### Rank 15 — Ewen, *Restate raises $20M Series A…* plus the durable-execution inner loop

- **Link.** <https://restate.dev/blog/announcing-series-a> (30 Sep 2026)
- **Author.** Stephan Ewen (Restate / Apache Flink)
- **Library.** Not in `ref/`.

**What it is.** Practitioner architecture, not a paper. Durable execution is being
pulled from coarse workflows into the **inner agent loop**. Replit moved Replit Agent
onto Restate; the new design uses **>10× more durable actions** than the previous
generation. That only works if a durable action is fast and cheap enough to wrap a
tool call or an inference call, not a whole job. Restate's pitch: single binary, log
append on the hot path, Virtual Objects for agent/session state, self-hostable.

**Why you should read it.** SASE's single-turn contract and ToolRun recording are a
*host-level* durability story. Restate/Temporal/DBOS are an *in-loop* durability story.
Replit's 10× action count is the existence proof that the inner loop can be journaled
without becoming a workflow engine. Your replay annotations want a journal of tool
calls. This is the industrial form of that journal, and a warning about latency/cost
if SASE puts a heavy orchestrator on every tool call.

**Steal or argue.** Steal "durability inside the loop, not around it" as the ToolRun
design center, and Virtual Objects as a relative of the goal ledger's live markers.
Argue that SASE should keep durability in `sase_core` (you already require a Rust
core, no Python fallback) rather than adopting Restate as a dependency — Restate is
itself a Rust-shaped single binary, which is a cousin, not a plugin.

## Honorable mentions (read after the fifteen)

These earned a place by mapping onto a live SASE surface. They are not the next five
nights of reading.

| Paper | Link | Why it is on the desk |
| --- | --- | --- |
| Xiao et al., *LLM Parkinsonism* / Global Executive Control | [2609.30662](https://arxiv.org/abs/2609.30662) | Agents keep acting after the objective is satisfied. GEC separates action generation from project-level stop. Directly relevant to **goals host binds** and to settling a goal instead of polishing forever. |
| *Do LLM Agents Execute the Plans They Declare?* | [2609.38108](https://arxiv.org/abs/2609.38108) | Plan+ReAct preserves declared structure only 22–45% of the time. Pattern-specific executors recover it. That is the case for **host-owned macro/xprompt execution** rather than hoping the model will follow the plan it wrote. Hierarchical mode wins on SWE-bench. |
| Zou et al., *AgentKernel: The Trust-Native Agentic Operating System* | [2609.29647](https://arxiv.org/abs/2609.29647) | Identity, perception, cognition, execution as mandatory OS pillars. Maps onto LaunchApproval, gates, sudo, memory-write routing. Useful when the sasos/sasesh rename debate needs an OS vocabulary that is not marketing. |
| *Distilling Agentic Systems: A Roadmap across Models, Artifacts, and Harnesses* | [2609.36630](https://arxiv.org/abs/2609.36630) | Agent competence lives in weights, artifacts, and harness. A 57-page map of where SASE should store what (memory vs skill vs adapter vs model choice). |
| Xu et al., *MemTrace* | [2610.04838](https://arxiv.org/abs/2610.04838) | Provenance-aware traces anchored to files/symbols/tests; validity checked against the current repo before reuse. Next step after EA-Graph for long-horizon coding memory. +21.2 DeepSWE pass@1 under Codex CLI. |
| Yu et al., *StateTape* | [2609.36319](https://arxiv.org/abs/2609.36319) | Rewrites context as the repository changes, using a symbol-level code graph so staleness is observed from writes, not inferred from text. Pair with MemTrace. |
| *An Empirical Study of Harness Design for Coding Agents* | [2609.20804](https://arxiv.org/abs/2609.20804) | 176 matched settings. Context management matters when the window is tight; rule-based elision before LLM summary wins; recoverable elision is unused; bash-only is enough for strong models and cheaper. Feeds the budgeted router. |
| Virk, Edds, Xia, Zhang, *SwarmResearch* | [2607.02807](https://arxiv.org/abs/2607.02807) | Shepherd + Search Agents, each on a git branch, local context. Companion to GitSwarm/ArcticSwarm with an orchestrator that adapts parallelism by search depth. |
| Gu, *From Model Scaling to System Scaling: Scaling the Harness in Agentic AI* | [2605.26112](https://arxiv.org/abs/2605.26112) | Harness-level bottlenecks: context governance, trustworthy memory, dynamic skill routing. Research agenda for trajectory quality, memory hygiene, verification cost. Framing paper; thinner than Ranks 10–13. |
| Assalaarachchi, Masood, Hoda, Grundy, *Toward Agentic Software Project Management* | [2601.16392](https://arxiv.org/abs/2601.16392) | Agentic PM as junior/intern with four autonomy modes. Relevant to AXE, epics, and "humans settle goals." ICSE AGENT 2026 workshop. |
| Hoda, *Toward Agentic Software Engineering Beyond Code* | [2510.19692](https://arxiv.org/abs/2510.19692) | **Already in library (started** 2025-11-15). Whole-of-process vision and CRAFT values. Finish it; do not recapture it. |
| Galster et al., *Harness Engineering for Agentic AI Coding Tools* (extended) | [2602.14690](https://arxiv.org/abs/2602.14690) | **Already in library (queued** 2026-02-20 as "Configuring Agentic AI Coding Tools"). 2,853 GitHub repos: Context Files dominate; `AGENTS.md` is the interoperable standard; Skills/Subagents are rare. Read with Rank 11. |
| *RoadmapBench* | [2605.15846](https://arxiv.org/abs/2605.15846) | 115 long-horizon version-upgrade tasks, median 3,700 lines / 51 files. Opus-4.7 at 39.1%. The benchmark SASE should care about more than SWE-bench if the product is campaigns. |
| *Thinking Before Thinking: Scaling Agentic Inference Through Meta-Reasoning* | [2609.38147](https://arxiv.org/abs/2609.38147) | Explicit controller: consolidate, explore options, score remaining budget, dispatch. Maps onto AXE, size aliases, and the budgeted router. |
| Chen et al., *Measure Before You Manage: Evaluating Agent Working Memory in Coding Agents* | [2608.31057](https://arxiv.org/abs/2608.31057) | Working memory is semantically heterogeneous; token budgets are the wrong metric. Pair with Rank 10. |
| Liu et al., *A Contract-Centered Architecture for Scalable and Manageable Agentic Runtimes* | [2608.27086](https://arxiv.org/abs/2608.27086) | Skill / Harness / Scaffold / data as responsibility contracts. Separability hypothesis is untested; useful vocabulary for the Rust-core boundary. |
| Bain, *The Missing Architecture for Agentic Software Development* | [link](https://www.bain.com/insights/the-missing-architecture-for-agentic-software-development-technology-report-2026/) | Survey (n=293, Apr 2026): +21% tasks, +91% review time, +47% concurrent workstreams. Practitioner confirmation of Rank 4's bottleneck. Read the Berkeley paper first. |
| Xu and Yan, *Agent Skills for LLMs* (survey) | [2602.12430](https://arxiv.org/abs/2602.12430) | Architecture, acquisition, security; 26.1% of community skills had vulnerabilities. Read if Rank 13 pushes you into the skills ecosystem. |
| *From Verification Failures to Reusable Guidance for Coding Agents* | [2609.39022](https://arxiv.org/abs/2609.39022) | Expert diagnosis of verification failures packaged as reusable kit (K framework). Niche, high-signal if you take MentorScript / memory-as-guidance seriously. |

## Cross-cutting implications (observations, not decisions)

These are patterns across the ranked set. They are not a proposal to change SASE.

1. **Replay is now a literature, not a comment.** ESAA, Actions-with-Receipts, Ledger
   govern, PROJECTMEM projections, and Restate's inner-loop journal all treat replay as
   an executable property. The two annotations in the related-reading history are
   pointing at a cluster that did not exist in that form when Gas Town was highlighted.

2. **The inner loop is getting solved; the outer loop is the product.** Ledger, ESAA,
   progressive disclosure, and harness anatomy improve the tick. Reality-is-the-Final-Verifier,
   ArcticSwarm, GitSwarm, and Gusev/Neira are about what happens *between* ticks:
   isolation, compounding, human settlement, review capacity. ACE (the SASE TUI) lives
   in that between.

3. **Do not score the OS on SWE-bench.** Rank 10's result, plus RoadmapBench's 39%
   ceiling on version upgrades, plus Berkeley's two gaps, all say the same thing:
   merge-readiness and campaign completion are different games from issue repair.

4. **Isolation before synthesis is becoming a measured design.** This swarm already
   practices it. ArcticSwarm and GitSwarm give you numbers and a vocabulary
   (commitment boundaries, compounding ancestry) to turn the practice into a
   `#research_swarm` invariant.

5. **Instruction budget is the harness's real degree of freedom.** Progressive
   disclosure, ACE playbooks, What-Does-a-Harness-Buy, and the empirical harness-design
   study all locate leverage in *what is sent on the first call and every step*, not in
   more tools. That is the budgeted instruction router, core-vs-reference memory, and
   skill frontmatter.

6. **Hassan's group is still the closest academic neighbor.** Rank 1 named SASE. Rank 3
   (Ledger) is the same labs shipping a runtime layer a year later. Reading them as a
   pair is how you keep SASE-the-product in dialogue with SASE-the-vision without
   treating the vision paper as a spec.

## Already-read items this list deliberately skipped

Finished in 2026 and therefore not re-recommended: Gas Town README, OpenAI Symphony,
OpenAI Harness Engineering, Netclode, Muse Code subagent fanout, Kinney on agent
memory, Zhou et al. filesystem memory, EA-Graph, *The Log is the Agent*, Memory OS,
Kerestecioglu human-inspired memory, charm VHS.

Started in the 2025 backlog and still worth finishing *instead of recapturing*:
Hoda (Rank honorable), SWE-agent, OpenHands, Cognition *Don't Build Multi-Agents*,
Anthropic *Building Effective Agents* / *Effective Context Engineering* / *Equipping
Agents with Agent Skills*, PDL, POML, LangGraph durability essays. Those remain in the
library as `started`. This report prefers 2026 papers that post-date them.

## Proposed library captures (not run)

```bash
bob ref create https://arxiv.org/abs/2509.06216   # already queued; mark read after you finish v3
bob ref create https://arxiv.org/abs/2602.23193   # ESAA
bob ref create https://arxiv.org/abs/2608.00808   # Ledger runtime
bob ref create https://arxiv.org/abs/2609.12039   # Reality Is the Final Verifier
bob ref create https://arxiv.org/abs/2610.00327   # Actions with Receipts
bob ref create https://arxiv.org/abs/2609.19519   # Levels, Ticks, Cascaded Intelligence
bob ref create https://arxiv.org/abs/2609.01870   # ArcticSwarm
bob ref create https://arxiv.org/abs/2610.04862   # GitSwarm
bob ref create https://arxiv.org/abs/2606.12329   # PROJECTMEM
bob ref create https://arxiv.org/abs/2610.04433   # What Does a Harness Buy?
bob ref create https://arxiv.org/abs/2609.00006   # Eleven-harness anatomy
bob ref create https://arxiv.org/abs/2609.35692   # Progressive disclosure of skills
bob ref create https://arxiv.org/abs/2609.35719   # Swarms as researchers
bob ref create https://restate.dev/blog/announcing-series-a
```

Add `-L` to also narrate. Do not run these unless you want them in `ref/`.

## Library check

Library check: **4 of 45 URL candidates already in your library (0 finished).** Of those
four: Hassan 2509.06216 **queued** (2025-11-28), ACE playbooks 2510.04618 **queued**
(2026-01-19), Galster/configuring-tools 2602.14690 **queued** (2026-02-20), Hoda
2510.19692 **started** (2025-11-15). Of the **15 ranked picks**, 2 are already queued
unread (Ranks 1 and 12) and 13 are absent from `ref/`. Absence from `ref/` is not proof
a paper was never read.

---

*Sources: arXiv HTML/abstracts for the cited ids, Restate Series A post (2026-09-30),
Bain Tech Report 2026, `research:202610/sase_related_reading_history.md`, and `bob ref
find` on 2026-10-07. No peer report from this swarm was opened.*
