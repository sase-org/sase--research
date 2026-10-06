---
create_time: 2026-10-06
updated_time: 2026-10-06
status: draft
tags:
  [
    research_swarm,
    agent-memory,
    agent-instruction-files,
    AGENTS.md,
    context-engineering,
    progressive-disclosure,
    sase-memory,
  ]
---

# Recent articles most likely to improve SASE memory files and agent instruction files

**Question.** Which papers and essays published in roughly the last year (after 2025-10-06)
are most likely to change how SASE authors memory notes and generates `AGENTS.md` /
provider instruction shims?

**Researcher.** grk (`research.3q.grk`). Independent report. I did not locate, open, or
read peer reports from this swarm (`__cdx`, `__cld`, `__mus`, `__gem`).

**Window.** Today's date is 2026-10-06. "Last year" means first public appearance on or
after 2025-10-06. A few slightly older pieces are listed as honorable mentions when a
2026 paper builds on them, or when they are still the best statement of a claim.

## Bottom line

Read in this order: **Gloaguen et al. on `AGENTS.md`**, **Anthropic's June 2026
steering guide**, **Shihipar's July 2026 Claude 5 context rules**, then **ACE**. Those
four together argue a single, SASE-shaped thesis:

1. Always-loaded instruction files are followed, so extra lines are not free — they
   raise cost and make tasks harder.
2. Facts belong in a small always-on file; procedures belong in on-demand skills;
   "never do this" belongs in deterministic hooks, not prose.
3. Newer models want *less* always-on text and more progressive disclosure.
4. When memory *does* grow, grow it by incremental bullets, never by rewriting the
   whole file.

SASE already has the right *shape* (core / reference / webs / generated skills /
authored `[[links]]` / immutable decisions). The literature's pressure is on *budget,
placement, and evolution*, not on adding a vector store.

Measured against that literature, today's generated `AGENTS.md` is already long: **290
lines**. Anthropic's 2026 CLAUDE.md heuristic is **under 200 lines**. The largest
always-on taxes after `sase.md` are the **decisions roster** (25 claims with
multi-line summaries) and the **glossary term dump**. The reopen condition in
`decisions:webs-render-in-their-own-section` ("enough webs that inlining every
descriptor is a token-budget problem") is the condition this reading list is about.

## How I ranked

I ranked for *inspiration to change SASE files*, not for general agent-memory
excellence. A paper that invents a new graph RAG is less useful here than a 12-page
measurement of what `AGENTS.md` actually does to coding agents.

Criteria, in order:

1. **File-shaped.** About markdown instruction files, skills, or git-native memory,
   not about embeddings as the primary store.
2. **Empirical or vendor-operational.** Measurements, or a lab that ships a harness
   and reports what they deleted.
3. **Maps onto SASE's existing split.** Core vs reference vs webs vs skills vs
   hooks vs artifacts.
4. **Would change an authoring decision.** What goes in `type: core`, how a web
   descriptor is written, whether a procedure should be a skill, whether a decision
   strand should ever be rewritten.

I read primary sources (arXiv HTML, Anthropic engineering posts, the Agent Skills
spec). I used SASE's live `AGENTS.md` and `sase/memory/` tree as the mapping target.
I did not use this swarm's other reports.

## What SASE already is (so the ranking is not generic)

SASE memory is git-native markdown:

| Layer | Mechanism | When it is paid |
| --- | --- | --- |
| Core notes | `type: core`, inlined into `AGENTS.md` and every provider shim | Every turn |
| Reference notes | `type: reference`; one-paragraph description inlined; body via `sase memory read` | Description always; body on demand |
| Memory webs | Descriptor always inlined in § Memory Webs; strand bodies never inlined | Descriptor always; strand on `web:keyword` |
| Authored links | `[[target]]` / `![[target]]` | At read time |
| Decisions | Immutable strands; supersession, never in-place rewrite | Roster always; body on demand |
| Skills | Generated `SKILL.md` from `src/sase/macros/skills/` | On skill use |
| Artifacts / beads / goals | Sidecar records, audited reads | On citation or read |

This is already closer to Anthropic's 2026 "progressive disclosure" stack than to
MemGPT-style paging. The interesting papers are the ones that say *this shape is
right and you are still overpaying*, or *this shape is right and you are not
evolving the right layer*.

Current generated `AGENTS.md` in this workspace: **290 lines**. Core note bodies
are small (`gotchas.md` is 10 lines; `rust_core_backend_boundary.md` is 21;
generated `sase.md` is 85). The bulk is web descriptors plus the reference-memory
index. That is the opposite of a "core notes are bloated" problem. It is a
"descriptor and index tax" problem.

## Cross-cutting findings

### 1. Instruction files are followed. That is why they hurt.

Gloaguen, Mündler, Müller, Raychev, and Vechev (ETH Zurich / LogicStar, ICLR 2026
workshop on memory for agentic systems; arXiv:2602.11988v3, 29 Sep 2026) is the
first large measurement of `AGENTS.md` / `CLAUDE.md` on real issue resolution.

Headline results, from the paper itself:

- Context files do **not** generally raise task success. LLM-generated files drop
  resolution ~0.5% on SWE-bench Lite and ~2% on their CTXbench (138 issues / 12
  niche repos with developer-committed context files).
- They **do** raise inference cost **>20%** (SWE-bench ~20%, CTXbench ~23%) and
  add ~2.5–3.9 steps per task.
- Developer-committed files beat LLM-generated files by **7%** on average
  (p=0.038) but still raise cost (up to 19%) and steps.
- Agents **follow** the files: mentioning `uv` takes use from <0.01 to 1.6 times
  per instance; mentioning a repo-specific tool takes use from <0.05 to 2.5.
- Repository **overviews do not help**. Time-to-first-touch of a file in the gold
  patch is not improved; extra exploration is.
- GPT-5.2 / GPT-5.1 mini spend **~22% more reasoning tokens** with LLM-generated
  files — the extra instructions make the task look harder.

Their prescription is the one SASE should steal: human-written context files
should state **non-standard practices that are not already in the README**, and
every addition should be evaluated. Auto-init (`/init`, LLM-generated
`AGENTS.md`) is currently a cost with no gain.

SASE generates `AGENTS.md` from *human-authored* memory, which is the better of
the two Gloaguen conditions. The remaining risk is the one they name in the
trace analysis: **followed-but-unnecessary requirements**. A 25-item always-on
decisions roster, a full glossary term dump, and a 10-item "you MUST read this
reference note when…" index are all followed. They are also paid on every TUI
paint, every research swarm member, every helper.

### 2. Facts, procedures, and guardrails are three different loading problems.

Anthropic's 18 Jun 2026 post *Steering Claude Code: when to use CLAUDE.md, skills,
hooks, and subagents* is the cleanest operational taxonomy of the year. Loading,
compaction, and context cost are first-class:

| Method | Load | Cost | Use for |
| --- | --- | --- | --- |
| Root CLAUDE.md | Session start, re-read after compaction | High, every line always | Build commands, layout, conventions, team norms |
| Nested CLAUDE.md | When that subdirectory is touched | Low | Directory-local conventions |
| Path-scoped rules | When matching files are touched | Medium unless scoped | Cross-cutting constraints |
| Skills | Name+description always; body on invoke | Low | Procedural workflows |
| Subagents | Isolated window; summary returns | Low in parent | Deep search, audits |
| Hooks | Lifecycle events; bypass compaction | Low | Deterministic "always/never" |

Two sentences from that post should sit next to `sase/memory/README.md`:

- "A 30-line procedure in CLAUDE.md" belongs in a skill.
- "'Never do this' in CLAUDE.md" belongs in a hook or permission, because
  prompted rules fail under pressure, long sessions, and prompt injection.

SASE already has the first split (core vs generated skills vs `sase memory
read`). It does **not** yet have path-scoped instruction loading, nested
per-directory instruction files, or a documented rule that "never" goes in a
hook. Several always-on core paragraphs are procedures: `/sase_final`,
`/sase_repo`, `/sase_memory_write`, artifact-read auditing. Those are closer to
skills than to "facts about the repo."

### 3. The frontier labs are deleting always-on text, not adding it.

Shihipar (Anthropic, 24 Jul 2026) reports that Claude Code **removed over 80% of
the system prompt** for Opus 5 / Fable 5 with no measurable loss on coding evals.
The replacements:

- Rules → judgement ("match surrounding comment density" instead of "never write
  multi-line comments").
- Examples → interfaces (enum statuses on tools instead of 9k-character
  when-to-use essays).
- Put it all upfront → progressive disclosure (verification moved into a skill;
  some tools are deferred until ToolSearch).
- Memory in CLAUDE.md → auto-memory.
- Simple specs → rich references (tests, HTML artifacts, rubrics, other
  codebases).

Direct CLAUDE.md advice: keep it lightweight; say what the repo is for; spend
tokens on **gotchas the filesystem will not reveal**; point at skills for
verification. "Avoid stating the obvious things Claude should know by looking at
your file system."

That last line is a critique of always-on architecture/project-structure
sections — which Mohsenimofidi et al. found are among the most common
`AGENTS.md` headings, and which Gloaguen found do not help.

### 4. Context is an attention budget. Always-on text has diminishing returns.

Anthropic's 29 Sep 2025 essay *Effective context engineering for AI agents* (seven
days before the strict window; still the canonical statement) treats context as a
finite attention budget with n² pairwise token relationships. "Good context
engineering means finding the smallest possible set of high-signal tokens that
maximize the likelihood of some desired outcome." System prompts should sit at
the right **altitude**: not brittle if-else prose, not vibes that assume shared
context.

The hybrid they describe is SASE's hybrid: drop a small CLAUDE.md up front, then
let the agent glob/grep/read just in time. Compaction, structured note-taking
outside the window, and subagent isolation are the long-horizon levers. SASE's
single-turn contract makes *intra-turn compaction* less central than in Claude
Code sessions, but the **per-turn always-on tax** is worse: every new agent pays
the full `AGENTS.md` again, with no session cache across SASE turns.

Chroma's July 2025 *Context Rot* report (slightly outside the window) is the
measurement behind that essay: 18 models degrade as input grows, even on simple
tasks. It is still the reason to treat core memory as scarce.

### 5. Evolving memory must grow by deltas. Full rewrites collapse.

Zhang, Hu, et al., *Agentic Context Engineering* (ACE; arXiv:2510.04618, 6 Oct
2025, ICLR 2026) is the year's best paper on *how instruction-shaped text should
change over time*.

Two failure modes of prompt/memory optimizers:

- **Brevity bias.** Optimizers collapse toward generic one-liners and drop domain
  tactics.
- **Context collapse.** Asking an LLM to rewrite the whole playbook can nuke it
  (their AppWorld case: 18,282 tokens / 66.7 accuracy → 122 tokens / 57.1, worse
  than the unadapted baseline).

ACE's answer: treat context as an **itemized playbook**. Generator runs the task,
Reflector extracts lessons, Curator emits small delta bullets (id + helpful/harmful
counters + content). Merge is deterministic. Grow-and-refine de-duplicates.
Reported: **+10.6%** on agents, **+8.6%** on finance, **~86.9%** lower adaptation
latency, and it works from execution feedback without labels. On AppWorld, ReAct+ACE
with DeepSeek-V3.1 matches IBM CUGA / GPT-4.1.

SASE's `decisions` web already refuses in-place rewrite — that is the right
anti-collapse stance for *constitutional* memory. ACE is about a *different*
layer: a living playbook of tactics (tool quirks, "this test is flaky if you
don't X") that should accumulate. Mixing those into immutable decision records
would be a category error. Mixing them into always-on `gotchas.md` would be a
budget error. The inspiring move is a **third, itemized, delta-updated playbook**
that is *not* core and *not* a decision.

Dynamic Cheatsheet (Suzgun et al., Apr 2025) is the predecessor ACE cites. It is
outside the year window; skip it unless you want the ACE genealogy.

### 6. Git-native files are winning as the memory substrate. The next step is
making memory *operations* tools.

Three 2025–2026 papers independently land on "the context is a file":

- **Git-Context-Controller** (Wu, Hu, Zhu, Pan, Liu, Xu, Jin; arXiv:2508.00031v2,
  1 Mar 2026). Context as a `.GCC/` workspace with `COMMIT`, `BRANCH`, `MERGE`,
  `CONTEXT`. Hierarchical retrieval: `main.md` roadmap, per-branch `commit.md`
  summaries, `log.md` OTA traces, `metadata.yaml`. Claude 4 Sonnet + GCC reaches
  **80.2%** on SWE-Bench Verified (+13.6% relative to their long-context
  baseline). The claim is that summarization makes agents "dumber"; versioned
  files keep fine grain recoverable.
- **CAT / Context as a Tool** (Liu, Yang, Jiang, Li, Guo, Liu, Dai;
  arXiv:2512.22087, 26 Dec 2025). Context maintenance is a *callable tool*, not a
  harness heuristic. Workspace = stable task semantics + condensed long-term
  memory + high-fidelity short-term interactions. SWE-Compressor: **57.6%**
  SWE-Bench-Verified under a bounded budget.
- **Coding Agent Memory Post-training** (Luo et al.; arXiv:2609.34422v2, 30 Sep
  2026). RL on a persistent filesystem plus ordinary shell, not a custom memory
  API. 4B and 9B policies trained this way compete with much larger Qwen3.5
  MoE models on SWE-bench Verified and MLE-bench Lite. The point: file create /
  edit / grep *is* the memory interface the base model already knows.

SASE already stores memory as versioned markdown. GCC/CAT/CAMG are not an
argument to introduce a vector DB. They are an argument to expose **structured
memory operations** (`commit` a lesson, `branch` an exploration, `context` at a
chosen resolution) as tools, instead of hoping the agent greps `sase/memory/`
well.

**Context Language Models** (Shao et al., UW + Meta Superintelligence Labs;
arXiv:2609.37725, 29 Sep 2026) take this further: the model edits its own
context file with unrestricted bash. Strong efficiency numbers, plus an explicit
safety warning that self-edited context can plant instructions. For SASE, that
is a reason to keep **human-authored core and decisions out of the model's
write set**, and to put any self-evolving playbook in a separate, reviewable
lane.

### 7. Progressive disclosure is now a standard, not a trick.

The Agent Skills spec (Anthropic origin, open standard late 2025, current
documentation at [agentskills.io](https://agentskills.io/home)) is the
industry-default packaging of on-demand procedures:

1. Discovery: name + description only (~100 tokens/skill).
2. Activation: `SKILL.md` body when the task matches.
3. Execution: scripts/references loaded or run as needed.

SASE already generates `SKILL.md` from templates and already has reference
memory whose *description* is always shown. The inspiring comparison is
**metadata quality**. Skill descriptions are written as trigger conditions
("use when the user wants to…"). Several SASE reference descriptions are
written as domain labels ("Read before macros…"). The skills literature says
the description *is* the retrieval index. Weak descriptions either never fire
or fire too often.

Huang et al.'s Aug 2026 survey *A Survey of Agent Memory in the Second Half*
(arXiv:2602.06052v4) then gives the map for everything else. Three axes:

- **Substrate:** internal (weights, KV) vs external (files, vectors, graphs).
- **Cognitive mechanism:** sensory / working / episodic / semantic / procedural.
- **Subject:** user-centric vs agent-centric.

SASE today, in that vocabulary:

| SASE object | Survey slot |
| --- | --- |
| Generated `AGENTS.md` / core | Working + procedural (always-on policy) |
| Reference notes + strands | Semantic, on-demand |
| Decisions web | Semantic, immutable, agent-centric |
| Beads / artifacts / chats | Episodic |
| Generated skills / macros | Procedural, portable |
| Goals | Agent-centric task state |

The survey's claim that 2025 produced hundreds of memory papers, and that
memory is now the substrate of *self-evolution*, is useful as a warning. SASE's
own `decisions:corpus-before-mechanism` already forbids building retrieval
ahead of a corpus. The 2026 literature does **not** reopen that decision. It
says: you already have a corpus (decisions, glossary, skills, artifacts);
improve *placement and evolution* of that corpus.

### 8. Real `AGENTS.md` files are still an experiment. Style is part of the experiment.

Mohsenimofidi, Galster, Treude, and Baltes (Heidelberg / Bamberg / SMU; MSR 2026;
arXiv:2510.21413v4, 5 Feb 2026) mined 10,000 engineered GitHub repos. **5%**
(466) had any AI context file by late 2025. `AGENTS.md` mean length **142
lines**, SD **231** — no settled size. Recurring H1/H2 categories: conventions
(50), contribution (48), architecture (47), build commands (40), goals (32),
test execution (32). Evolution, on the 10 most-edited files: mostly **add or
modify individual instructions**, not wholesale rewrites. Five writing styles
in Conventions sections: descriptive, prescriptive, prohibitive, explanatory,
conditional.

That last taxonomy is immediately usable as an authoring lint for SASE core
notes. "Never mention the workspace directory in a plan file" is prohibitive
and belongs in core (or a hook). "Memory webs are a descriptor plus a strand
directory" is descriptive and could be a pointer. Mixing all five styles in one
always-on paragraph is how files grow to 290 lines.

## Ranked reading list

Read these in order. The first four are the ones most likely to change a SASE
memory file this month. The rest deepen one axis. Each entry states the
publication date, why it ranks here, and the SASE move it suggests. "Move" is
inspiration, not a proposed patch.

### 1. Gloaguen et al., *Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?*

- **Where.** [arXiv:2602.11988](https://arxiv.org/abs/2602.11988) (v1 12 Feb
  2026, v3 29 Sep 2026). ICLR 2026 Workshop on Memory for LLM-Based Agentic
  Systems. Also the [ETH SRI page](https://www.sri.inf.ethz.ch/publications/gloaguen2026agentsmd).
- **Why it is #1.** It is the only paper this year that *measures* `AGENTS.md`
  / `CLAUDE.md` on issue resolution with both LLM-generated and
  developer-committed files, across Claude Code, Codex, and Qwen Code.
- **What to steal.** Do not auto-generate instruction content. Do not put
  repository overviews in always-on files. Put only non-standard practices.
  Evaluate every addition: followed instructions have a cost.
- **SASE implication.** Treat the 290-line generated `AGENTS.md` as a
  performance surface, not a documentation dump. The decisions roster and
  glossary term list are the first places a Gloaguen-style ablation would cut.
  Keep generating from human notes; never add an LLM `/init` path for core.

### 2. Segner, *Steering Claude Code: when to use CLAUDE.md, skills, hooks, and subagents*

- **Where.** [claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more](https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more)
  (18 Jun 2026).
- **Why #2.** Best operational table of 2026 for "where does this sentence
  live?" Directly translatable to SASE core / reference / skill / hook.
- **What to steal.** Root file < 200 lines, has an owner, reviewed like code.
  Procedures → skills. "Never" → hooks/permissions. Path-scoped rules beat
  unscoped always-on constraints. Nested per-directory files for local
  conventions.
- **SASE implication.** Walk every always-on paragraph and reclassify it. Final
  declaration, repo-open, memory-write, and artifact-read rules are
  *procedures*. Keymap gotchas and the rust-core litmus test are *facts*.
  "Do not mention the workspace path in a plan" is a *guardrail* and may want a
  hook, not a paragraph.

### 3. Shihipar, *The new rules of context engineering for Claude 5 generation models*

- **Where.** [claude.dev/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models](https://claude.dev/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)
  (24 Jul 2026).
- **Why #3.** A lab deleted 80% of its own always-on prompt and published the
  replacement rules. That is rarer and more useful than another memory
  architecture.
- **What to steal.** Judgement over rules. Interfaces over examples.
  Progressive disclosure over encyclopedias. Gotchas over filesystem tours.
  Rich references (tests, other code) over prose specs.
- **SASE implication.** Several core paragraphs still read like 2024 "do not
  ever X" rails. Rewrite at a higher altitude ("match surrounding
  conventions") and move the remaining rails into skills or hooks. Point
  `AGENTS.md` at reference notes and skills instead of inlining their
  contracts.

### 4. Zhang, Hu, et al., *Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models*

- **Where.** [arXiv:2510.04618](https://arxiv.org/abs/2510.04618) (v1 6 Oct
  2025, v3 29 Mar 2026). ICLR 2026. Code: [ace-agent/ace](https://github.com/ace-agent/ace).
- **Why #4.** Best account of how instruction-shaped text should *change*
  without collapsing. SASE already has immutability for decisions; it does not
  have a disciplined playbook layer.
- **What to steal.** Itemized bullets with helpful/harmful counters.
  Incremental deltas, never monolithic rewrite. Separate Generator / Reflector
  / Curator. Execution feedback is enough; labels are optional.
- **SASE implication.** Keep `decisions:` immutable. If SASE grows an
  agent-learned tactic store (flaky-test workarounds, provider-harness
  quirks), make it a new web or reference note that only accepts delta
  updates, with human curation on the merge. Do not let agents rewrite
  `AGENTS.md`.

### 5. Anthropic Applied AI, *Effective context engineering for AI agents*

- **Where.** [anthropic.com/engineering/effective-context-engineering-for-ai-agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  (29 Sep 2025).
- **Why #5.** Strictly one week outside the year window, but every 2026 piece
  above cites it. It is the vocabulary: attention budget, altitude, JIT
  retrieval, compaction, structured notes, subagents.
- **What to steal.** Smallest high-signal token set. Canonical examples, not
  exhaustive edge-case lists. Hybrid: small always-on file + tools that fetch.
- **SASE implication.** This is the design rationale for core vs
  `sase memory read`. Read it as the *why* behind papers 1–4, then apply it to
  the 290-line file.

### 6. Mohsenimofidi et al., *Context Engineering for AI Agents in Open-Source Software*

- **Where.** [arXiv:2510.21413](https://arxiv.org/abs/2510.21413) (v1 24 Oct
  2025, v4 5 Feb 2026). MSR 2026.
- **Why #6.** Empirical taxonomy of what people actually put in `AGENTS.md`,
  and how those files evolve. Complements Gloaguen (who measures effect) with
  "what is in the wild."
- **What to steal.** Heading categories, five writing styles, "add/modify
  instruction" as the dominant edit. Mean 142 lines as a prior.
- **SASE implication.** Audit core and web-descriptor prose against the five
  styles. Prefer explanatory ("do X because Y") for conventions, prohibitive
  for safety, and pointers instead of architecture tours.

### 7. Huang et al., *A Survey of Agent Memory in the Second Half*

- **Where.** [arXiv:2602.06052](https://arxiv.org/abs/2602.06052) (v4 4 Aug
  2026). Companion list: [AgentMemoryWorld/Awesome-Agent-Memory](https://github.com/AgentMemoryWorld/Awesome-Agent-Memory).
- **Why #7.** Best 2026 map of the field. Use it to name what SASE already
  covers and what it is deliberately not building.
- **What to steal.** Substrate / mechanism / subject taxonomy. The claim that
  memory is the self-evolution substrate. The reminder that working memory
  (always-on context) is a *gate*, not a warehouse.
- **SASE implication.** Do not reopen `corpus-before-mechanism`. Do use the
  taxonomy to keep semantic (decisions, glossary), procedural (skills), and
  episodic (artifacts, beads) in different loading classes.

### 8. Wu et al., *Git Context Controller: Manage the Context of Agents by Agentic Git*

- **Where.** [arXiv:2508.00031](https://arxiv.org/abs/2508.00031) (v2 1 Mar
  2026). First version is slightly before the window; the SWE-Bench numbers
  and the file-system design are in v2.
- **Why #8.** Closest published system to "SASE memory as an agent-facing
  git workspace." Strong SWE-Bench numbers without abandoning files.
- **What to steal.** Multi-resolution retrieval (`main.md` / `commit.md` /
  `log.md`). Explicit COMMIT/BRANCH/MERGE as tools. Summaries that still
  point at the fine-grain log.
- **SASE implication.** `sase memory read` is one resolution. A
  `CONTEXT --commit` analog for "what did we decide last time we touched
  beads?" would be GCC-shaped and still git-native. Branching reasoning into
  isolated worktrees is something SASE already does operationally; GCC is the
  memory version of that idea.

### 9. Liu et al., *Context as a Tool: Context Management for Long-Horizon SWE-Agents*

- **Where.** [arXiv:2512.22087](https://arxiv.org/abs/2512.22087) (26 Dec 2025).
- **Why #9.** Makes the philosophical move: context maintenance is an action
  the agent chooses, not a harness that fires at 60% of the window.
- **What to steal.** Three-part workspace (stable task semantics, condensed
  LTM, high-fidelity STM). Proactive compression at milestones.
- **SASE implication.** Single-turn SASE agents do not compact mid-turn the
  way Claude Code does, but *helpers* and research swarms already isolate
  STM. CAT is a reason to keep helper returns short and to treat "read this
  reference note" as a deliberate context action with a budget.

### 10. Agent Skills specification (and the SASE analog)

- **Where.** [agentskills.io](https://agentskills.io/home) and
  [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills).
  Open standard from late 2025; the 2026 client list is the evidence it
  stuck.
- **Why #10.** This is what "on-demand procedure" looks like when it is a
  portable format rather than a SASE-only skill. Compare it to
  `sase/memory/generated_skills.md` and to reference-note descriptions.
- **What to steal.** Three-stage disclosure. Descriptions written as
  triggers. `SKILL.md` under ~500 lines; further detail in `references/`.
- **SASE implication.** Rewrite reference `description:` fields as trigger
  conditions, not topic labels. That is a one-file-at-a-time improvement
  with no new mechanism.

### 11. Zhang et al., *Memory as Action: Autonomous Context Curation for Long-Horizon Agentic Tasks*

- **Where.** [arXiv:2510.12635](https://arxiv.org/abs/2510.12635) (v1 14 Oct
  2025, v3 7 May 2026).
- **Why #11.** Working-memory *editing* (delete/insert) as policy actions,
  trained end-to-end. 14B matches models 16× larger while cutting average
  context ~51%.
- **What to steal.** The idea that the agent should be allowed to *drop*
  always-on sections for a given turn, not only to fetch more.
- **SASE implication.** Today an agent can add context (`sase memory read`)
  but cannot subtract core. A future "context card" or per-turn core subset
  (for example, skip the decisions roster unless the task names a decision)
  is MemAct-shaped. That *would* be a new mechanism; `corpus-before-mechanism`
  says wait until the 290-line file is a measured problem. Gloaguen is that
  measurement for instruction files in general.

### 12. Luo et al., *Coding Agent Memory Post-training*

- **Where.** [arXiv:2609.34422](https://arxiv.org/abs/2609.34422) (v2 30 Sep
  2026). Project: [liruiluo.github.io/agentmemorygym](https://liruiluo.github.io/agentmemorygym/).
- **Why #12.** Fresh confirmation that **ordinary files plus shell** are a
  sufficient memory interface if you train (or prompt) for it. Closes the
  "maybe we need Mem0/Zep" door for SASE's coding agents.
- **What to steal.** Episode-persistent workspace; memory as create/revise/
  search/reuse of files; reward from the downstream task, not from a memory
  auxiliary loss.
- **SASE implication.** Double down on markdown-on-disk. Invest in making
  `sase/memory/` grep-friendly (short strands, good headings, authored
  links) rather than in a parallel retrieval engine.

## Read if you have time

These are in-window and good, but they change SASE less per hour than 1–12.

| Piece | Date | Why it is secondary for SASE |
| --- | --- | --- |
| Shao et al., *Context Language Models*, [arXiv:2609.37725](https://arxiv.org/abs/2609.37725) | 29 Sep 2026 | Model-edited context files; efficiency is real; **self-injection risk** is the SASE takeaway (keep core/decisions out of the model's write set). |
| Li, Ming, Chu, Shao, Jin, Xiong, *ACM: Agentic Context Management*, [arXiv:2607.23809](https://arxiv.org/abs/2607.23809) | 26 Jul 2026 | Lossless offload + on-demand query; +8% SWE-Bench-Verified on a 9B. Same family as CAT. |
| Xu et al., *A-MEM*, [arXiv:2502.12110](https://arxiv.org/abs/2502.12110) (NeurIPS 2025) | conference Dec 2025; arXiv Feb 2025 | Zettelkasten with *automatic* linking. SASE already chose **authored** `[[links]]` (`decisions:memory-links-are-authored`). Read as a contrast, not a migration plan. |
| AgentFold, [arXiv:2510.24699](https://arxiv.org/abs/2510.24699) | Oct 2025 | Proactive context folding for web agents. Relevant to compaction; less to durable memory files. |
| *enm-agent* (Obsidian-style markdown memory + RL, COLM 2026) | 2026 | Directly supports "markdown scaffold beats MemGPT/Mem0 for small models." Skim the memory-format section. |
| Corpus2Skill, [arXiv:2604.14572](https://arxiv.org/abs/2604.14572) | Apr 2026 | Distill a corpus into navigable skills. Interesting only after SASE's skill descriptions are trigger-shaped. |
| Anthropic, *Managing context on the Claude Developer Platform* | 29 Sep 2025 | Memory tool + context editing; 39% gain combining both on an internal search eval; 84% token cut on a 100-turn web search. Product analog of CAT. |

## Skip, or read last

- **Mem0 / Zep / Graphiti product reports.** Production user-memory. SASE's
  problem is *project constitution and procedures*, not chat personalization.
- **Generic "context engineering 2026 leader's guides"** (vendor blogs that
  restate Gloaguen + Anthropic without new measurements).
- **Dynamic Cheatsheet** (Apr 2025) unless you are reading ACE closely.
- **Chroma Context Rot** (Jul 2025) unless you want the original 18-model
  plots; Anthropic 2025 already digested it.
- **LLM-generated `AGENTS.md` how-tos.** Gloaguen is the rebuttal.

## A compact authoring checklist this literature supports

After reading 1–4, a SASE memory author can apply these without new machinery:

1. **Always-on is for non-standard facts and hard constraints the tree cannot
   reveal.** If grep would find it, do not inline it.
2. **Procedures are skills.** If a paragraph is a runbook, it is not core.
3. **"Never" wants a hook or a permission**, not only a sentence.
4. **Descriptions are retrieval indexes.** Write them as "read when…", the
   way `SKILL.md` descriptions are written.
5. **Do not rewrite a memory file from scratch.** Delta-update, or supersede
   with a new strand.
6. **Do not LLM-init core.** Human-authored, then generated into `AGENTS.md`.
7. **Measure.** Gloaguen's result is that "it feels helpful" is not a metric.
   Cost and success can move in opposite directions.
8. **Web descriptors are always-on.** Keep rosters to one line per strand;
   the body is what `sase memory read` is for. The decisions web's reopen
   condition is this checklist.

## Gaps

- No public ablation of SASE's own 290-line `AGENTS.md` (core-only vs
  core+webs vs full). Gloaguen is the closest external proxy.
- Almost no literature on **multi-provider identical shims** (SASE copies
  one `AGENTS.md` to every CLI). Shihipar is Claude-specific; Gloaguen did
  test Claude Code, Codex, and Qwen Code and saw the same cost pattern.
- Little on **single-turn hosts** that regenerate instruction context every
  agent. Most papers assume a long Claude Code / SWE-agent session.
- Self-evolving playbooks (ACE) vs human-constitutional memory (SASE
  decisions) is an open product question. The papers do not resolve who is
  allowed to write.

## Confidence

**High** that 1–4 are the right first reading and that SASE should not chase
vector-memory products this quarter.

**Medium** on any specific cut list for the 290-line file; that needs a
Gloaguen-style ablation on SASE tasks, not a vibe.

**Low** on importing ACE-style automatic curation into SASE without a human
curator — the CLM paper's self-injection warning, plus SASE's
host-owned-completion stance, argues against letting the model own core.

## Sources (primary)

1. Gloaguen, Mündler, Müller, Raychev, Vechev. *Evaluating AGENTS.md.* arXiv:2602.11988v3, 29 Sep 2026. https://arxiv.org/abs/2602.11988
2. Segner. *Steering Claude Code.* Anthropic, 18 Jun 2026. https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more
3. Shihipar. *The new rules of context engineering for Claude 5 generation models.* Anthropic, 24 Jul 2026. https://claude.dev/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models
4. Zhang, Hu, et al. *Agentic Context Engineering.* arXiv:2510.04618v3, 29 Mar 2026. https://arxiv.org/abs/2510.04618
5. Rajasekaran, Dixon, Ryan, Hadfield, et al. *Effective context engineering for AI agents.* Anthropic, 29 Sep 2025. https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
6. Mohsenimofidi, Galster, Treude, Baltes. *Context Engineering for AI Agents in Open-Source Software.* arXiv:2510.21413v4, 5 Feb 2026. https://arxiv.org/abs/2510.21413
7. Huang et al. *A Survey of Agent Memory in the Second Half.* arXiv:2602.06052v4, 4 Aug 2026. https://arxiv.org/abs/2602.06052
8. Wu, Hu, Zhu, Pan, Liu, Xu, Jin. *Git Context Controller.* arXiv:2508.00031v2, 1 Mar 2026. https://arxiv.org/abs/2508.00031
9. Liu, Yang, Jiang, Li, Guo, Liu, Dai. *Context as a Tool.* arXiv:2512.22087, 26 Dec 2025. https://arxiv.org/abs/2512.22087
10. Agent Skills specification. https://agentskills.io/home
11. Zhang, Shu, Ma, Lin, Wu, Sang. *Memory as Action.* arXiv:2510.12635v3, 7 May 2026. https://arxiv.org/abs/2510.12635
12. Luo et al. *Coding Agent Memory Post-training.* arXiv:2609.34422v2, 30 Sep 2026. https://arxiv.org/abs/2609.34422
13. Shao et al. *Context Language Models.* arXiv:2609.37725, 29 Sep 2026. https://arxiv.org/abs/2609.37725
14. Li, Ming, Chu, Shao, Jin, Xiong. *ACM: Agentic Context Management.* arXiv:2607.23809, 26 Jul 2026. https://arxiv.org/abs/2607.23809
15. Anthropic. *Managing context on the Claude Developer Platform.* 29 Sep 2025. https://claude.com/blog/context-management
16. Hong, Troynikov, Huber. *Context Rot.* Chroma Research, Jul 2025. https://research.trychroma.com/context-rot
17. Suzgun, Yuksekgonul, Bianchi, Jurafsky, Zou. *Dynamic Cheatsheet.* arXiv:2504.07952, 10 Apr 2025. https://arxiv.org/abs/2504.07952
18. Xu, Liang, Mei, Gao, Tan, Zhang. *A-MEM: Agentic Memory for LLM Agents.* arXiv:2502.12110 (NeurIPS 2025). https://arxiv.org/abs/2502.12110
