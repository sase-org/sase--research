# What You've Already Read That Bears on SASE

_Reading-history report from the Bob reference library (`bob ref`) plus zorg-era reading
records, compiled 2026-10-07._

## TL;DR

- **79 finished reads relate to SASE.** 50 are indexed in `ref/` (12 from the modern 2026
  library, 38 from the 2025 zorg backlog). The other 29 are zorg-era records outside
  `ref/` that `bob ref` does not index. A further **86 related references are started
  but not finished.**
- **Your 2026 reading has two themes, both finished in the last four months:**
  1. **Running fleets of coding agents:** Gas Town, OpenAI's Symphony and Harness
     Engineering, Netclode, and Muse Code's subagent fanout.
  2. **Agent memory:** six items, from Steve Kinney's survey digest to four 2025–2026
     arXiv papers.
- **The items you engaged with most:** Steve Kinney on agent memory (29 highlights),
  the Gas Town README (13 highlights, 4 comments), and *The Log is the Agent*
  (6 highlights). You also annotated three revisions of SASE's own `AGENTS.md` (26
  comments in total).
- **Two of your annotations independently asked for replay:**
  - On *The Log is the Agent*: "Support sase tool call replay?"
  - On Gas Town's molecules: "Materialize steps in workflow to enable replay starting at
    certain xprompt workflow steps? @sase"

  Replay is the clearest design idea your reading keeps returning to.
- **A notable gap:** Hassan et al., *Agentic Software Engineering: Foundational Pillars
  and a Research Roadmap* (arXiv 2509.06216). This is the paper that introduced the name
  "Structured Agentic Software Engineering (SASE)" and the Agent Command Environment
  (ACE). The library has it as **queued** (legacy status `unread`, added 2025-11-28). If
  you have read it, the library entry is stale.

## How This List Was Built

| Source | What was checked | Result |
| --- | --- | --- |
| `bob ref list -o external -R finished -g` | Every finished external reference in `ref/` | 60 notes; 50 related, 5 are SASE's own docs, 5 tangential |
| `bob ref list -o external -R started` | Every started external reference in `ref/` | 92 notes, all legacy `collect_fleeting_notes`; 86 related, plus 5 LLM chat transcripts and 1 personal `GEMINI.md` |
| `bob ref show … -f json` | Highlights, comments, and own notes for all 152 | 8 notes carry annotations (listed below) |
| `bob query` (Dataview) | The ~424 zorg-era reading records that `bob ref doctor` reports outside `ref/` | 29 finished related reads, 19 started; none already indexed (confirmed with `bob ref find`) |

I counted a zorg-era record the same way `bob ref` does:

- **Finished:** status `READ`, `REVIEW_FLEETING_NOTES`, or `REVIEW_LIT_NOTES`.
- **Started:** status `COLLECT_FLEETING_NOTES`.

The following were left out:

- The 272 finished agent reports in `ref/chat`. They are SASE research reports, so they
  show what topics interest you, not what you read.
- 145 queued and 8 dropped external references.

**Google-internal material is counted but not named.** This report lives in a public
repository. Each tier gives a count of `go/` documents and a one-line description of
their subject.

## 1. Finished: The 2026 Core Set (Modern Library)

### 1.1 Orchestrating Fleets of Coding Agents

| Reference | Finished | Your engagement | Why it bears on SASE |
| --- | --- | --- | --- |
| **Gas Town README** (gastownhall/gastown, multi-agent workspace manager) | 2026-06-15 | 13 highlights, 4 comments | The closest public analogue to SASE (detail below the table). |
| **An open-source spec for Codex orchestration: Symphony** (Kotliarskyi, Zhu, Brock; OpenAI, 2026-04-27) | 2026-10-03 | none | Turns a Linear board into a control plane: every open task gets an agent and humans review results. It names the real bottleneck as human attention (3–5 interactive sessions per engineer). This is the bet behind SASE's beads + AXE scheduler + ACE. Its "organize around deliverables, not sessions" stance matches the *Goals Host Binds* decision. |
| **Harness engineering: leveraging Codex in an agent-first world** (Ryan Lopopolo; OpenAI, 2026-02-11) | 2026-10-03 | none | A product built with 0 hand-written lines: ~1M LOC and ~1,500 merged PRs from 3–7 engineers, under "humans steer, agents execute." Its parts map onto SASE's: `AGENTS.md` as a map ≈ memory-built instruction files; the investment in guardrails and feedback loops ≈ `just check`, Symvision, and the two-speed CI. This repo already has a comparison report (`202610/openai_harness_engineering_vs_sase`). |
| **Building a self-hosted cloud coding agent: Netclode** (Stan's blog, 2026-02) | 2026-10-03 | none | A self-hosted remote coding agent: k3s plus microVM sandboxes, several agent SDKs, a native iOS app, and Tailscale access. It parallels SASE's `%dispatch` to apollo over the tailnet, the *agents across machines* work, and `sase-telegram` as a mobile front door. |
| **Muse Code: Subagent fanout** (dev docs) | 2026-10-06 | none | One parent fans out write-capable children, each in its own git worktree. Concurrency is about cores − 2, clamped to 4–8. A session event log records every spawn and control action. This is the same shape as SASE's ephemeral `sase_<N>` workspaces, *native helpers return; only roots declare*, and the Muse provider work. |

**Gas Town in detail:**

| Gas Town | SASE counterpart |
| --- | --- |
| Beads and Convoys | Beads and epics (same vocabulary) |
| Molecules/Formulas (TOML workflow templates with materialized steps) | Macro workflows |
| Refinery (Bors-style bisecting merge queue with verification gates) | Host-owned completion and land agents |
| Scheduler (capacity governor) | AXE and hold admission |
| Escalation (tracked beads) | Gates and notifications |

Your comments on the README:

- "Materialize steps in workflow to enable replay starting at certain xprompt workflow
  steps? @sase"
- "It looks like all agent launches run through the Mayor agent?" SASE takes a
  different approach with LaunchApproval and host binding.

### 1.2 Agent Memory (SASE's Memory System)

| Reference | Finished | Your engagement | Why it bears on SASE |
| --- | --- | --- | --- |
| **Agent memory systems** (Steve Kinney; digest of Hu et al.'s 107-page *Memory in the Age of AI Agents* survey) | 2026-06-11 | **29 highlights**, 2 comments; you linked the token-level passage to `[[sase_memory]]` | Most of the ideas you highlighted map onto SASE (detail below the table). |
| **Filesystem-Based Memory for LLM Agents: Organization, Evolution, and Sustainability** (Zhou et al., arXiv 2607.26637) | 2026-10-03 | none | Studies exactly SASE's medium: memory kept as a directory of Markdown files (detail below the table). |
| **EA-Graph: Artifact-Anchored Verification Memory for Coding Agents under Upstream Drift** (Hsu, Chi, Everett; arXiv 2608.04278) | 2026-10-03 | none | Anchors each verification claim to the exact artifact content that established it. It keeps evidence strength separate from freshness and allows an explicit **unprovable** verdict. This mirrors *Receipts Prove Before They Skip*, *Triage Annotates* (KNOWN needs an independent witness), and the risk that stale memory silently outlives the code it describes. |
| **The Log is the Agent: Event-Sourced Reactive Graphs** (Yohei Nakajima, arXiv 2605.21997) | 2026-10-03 | 6 highlights, 1 comment: **"Support sase tool call replay?"** | The append-only event log *is* the agent. It gives deterministic replay through a content-addressed cache of model and tool responses, cheap forks, and goal-to-model-call lineage. SASE already leans this way: the event-sourced *Goal Ledger*, *record-before-admit* ToolRun records, persisted artifact-link events, and agent transcripts. Your comment proposes the next step. |
| **Memory OS of AI Agent** (Kang et al., arXiv 2506.06326) | 2026-10-03 | none | Hierarchical short-, mid-, and long-term memory with heat-based promotion. Compare SASE's core (always loaded) / reference (on demand) / strand (by keyword) tiers and the *preloaded memory size* work. |
| **Human-Inspired Memory Architecture for LLM Agents** (Kerestecioglu et al., Microsoft, arXiv 2605.08538) | 2026-10-03 | none | Adds consolidation, interference-based forgetting, and reconsolidation. On 13K VSCode issues, dedup-based consolidation kept 97.2% retention precision while shrinking the store 58%. That is the bead problem in miniature: compare `/sase_new_task`'s semantic-duplicate check and the bead history and lossless archival research. |

**Kinney's digest, mapped to SASE:**

| What you highlighted | SASE counterpart |
| --- | --- |
| Forms / Functions / Dynamics framing; "your entire memory design space is token-level" when using hosted models | SASE memory is token-level Markdown |
| Flat → planar → hierarchical topologies | Memory webs are the planar step |
| Experiential memory: case → strategy → skill | Skills are skill-based experiential memory |
| "Flat is probably right… add structured construction only when you see specific retrieval needs" | Nearly verbatim the *No Retrieval Mechanism Before Its Corpus* decision |

**The filesystem-memory paper, in brief:**

- Organized stores roughly halve retrieval cost on large material.
- Organization erodes as memories accumulate, except under the strongest management
  agents.
- Changing the tool set alone reshapes the store as much as swapping the model.

For SASE, this supports gating writes (the `/sase_memory_write` routing and `memory`
task beads) and investing in tools like `sase memory read`, rather than trusting agents
to keep the store tidy.

### 1.3 Tooling SASE Uses

| Reference | Finished | Why it bears on SASE |
| --- | --- | --- |
| **charm VHS README** (scripted terminal recordings) | 2026-07-08 | The basis of the ACE demo-video tooling and the VHS caption-overlay research. |

## 2. Finished: The 2025 Backlog (Zorg Era, Migrated Into `ref/`)

These carry legacy statuses (`read`, `review_fleeting_notes`, `review_lit_notes`), so the
library has no finish date. The date shown is when each was added.

### 2.1 Framing Agentic Software Engineering

| Reference | Added | Why it bears on SASE |
| --- | --- | --- |
| **The Agentic Transformation of Software Engineering** (Daniel Bentes, Medium) | 2025-11-17 | SASE's thesis in essay form. |
| **Agentic Design Patterns / How agents can improve LLM performance** (Andrew Ng, *The Batch*) | 2025-05-12 | Reflection, tool use, planning, and multi-agent collaboration: the vocabulary SASE's macros and agent families build on. |
| **One Year of Agentic AI: Six Lessons from the People Doing the Work** (McKinsey QuantumBlack) | 2025-10-17 | Organizational lessons about workflows, evaluation, and humans in the loop. |
| **Vibe coding is dead: agentic swarm coding is the new enterprise moat** (VentureBeat) | 2025-10-17 | Argues for swarms over solo agents, i.e. the macro-swarm / research-swarm direction. |
| **I have seen the compounding teams** (Sam Schillace, *Sunday Letters*) | 2025-10-13 | Teams whose agent tooling compounds; the motivation for durable memory and skills. |
| **How I made a useful AI assistant with one SQLite table and a handful of cron jobs** (Geoffrey Litt) | 2025-04-14 | One small durable store plus scheduled jobs. Compare AXE scheduler chops and routines, and the SQLite bead read model. |
| **How Anthropic teams use Claude Code** (Anthropic) | 2025-08-20 | Real usage patterns for a harness SASE drives. |
| **My AI Skeptic Friends Are All Nuts** (Thomas Ptacek, fly.io) | 2025-06-04 | The practitioner case for coding agents. |

### 2.2 Agent Harnesses SASE Drives

| Reference | Added | Why it bears on SASE |
| --- | --- | --- |
| **Claude Code overview** and **Claude Code tutorials** (Anthropic docs) | 2025-04-08 | Provider capabilities behind the Claude adapter. |
| **Gemini CLI cheatsheet** (Phil Schmid) | 2025-08-20 | Gemini adapter. |
| **Gemini CLI commands** and **Gemini CLI configuration** docs (google-gemini/gemini-cli) | 2025-08-08 | Gemini adapter configuration and command surface. |
| **Gemini CLI MCP server** docs | 2025-09-27 | MCP wiring for the Gemini provider. |
| _9 Google-internal docs and slide decks on Gemini CLI usage, tips, agent training, and production use_ | 2025-06 – 2025-08 | Same subject. *Adapters Normalize Harnesses* depends on knowing each CLI's config, hooks, and tools. |

### 2.3 Tool Protocols and Function Calling

| Reference | Added | Why it bears on SASE |
| --- | --- | --- |
| **Introducing the Model Context Protocol** (Anthropic) | 2025-04-11 | Tool protocol under the provider layer. |
| **What is MCP** (Descope) | 2025-04-14 | Same. |
| **Say That 10 Times Real Fast: Model Context Protocol** (C. Abernathy) | 2025-04-14 | Same. |
| **MCP: An (Accidentally) Universal Plugin System** (worksonmymachine) | 2025-06-29 | Plugins as protocol; compare SASE's plugin repos and the generic ACP provider research. |
| **FastAPI-MCP** docs | 2025-05-13 | Exposing services as MCP tools. |
| **Function calling guide** (OpenAI) | 2025-06-02 | Tool-call contracts. |
| **Function calling** (Prompting Guide) | 2025-06-15 | Same. |
| _3 Google-internal MCP guides_ | 2025-08 | Same subject. |

### 2.4 AI-Assisted Development (Google-Internal)

_5 internal slide decks and docs on AI-assisted development and vibe coding (2025-08)._

## 3. Finished: Zorg-Era Records Outside `ref/` (Not Indexed by `bob ref`)

`bob ref doctor` warns that ~424 reading records live outside `ref/`. `bob query` found
these finished, SASE-related ones. `bob ref find` confirmed that none is in the library.

| Reference | Vault note · status | Why it bears on SASE |
| --- | --- | --- |
| **Claude Squad README** (smtg-ai/claude-squad) | `dev_ref` · READ (2025-08) | Manages many Claude Code / Codex / Aider sessions in tmux with git worktrees. It is the earliest visible ancestor of SASE's workspace-per-agent model and ACE's agent list. |
| **Conventional Commits 1.0.0** | `dev_ref` · READ | SASE's commit subjects follow it (`feat(bead): …`, `test(dispatch): …`). |
| **release-please** (googleapis) | `dev_ref` · REVIEW_FLEETING_NOTES | Automated semver releases; compare the automated semver releases research. |
| **Local-first software** (Ink & Switch) | `dev_ref` · REVIEW_FLEETING_NOTES | SASE keeps its state local: files, SQLite read models, git-backed sidecars, pull-based auto-sync. |
| **Clean Architecture** (Robert C. Martin, book) | `clean_arch` · all 36 chapter records READ or in review | The dependency rule and "UI and frameworks are plugins" are the reasoning behind the *Rust Core Backend Boundary*: behavior every frontend must share belongs in `sase_core`. |
| **avante.nvim README** and its Hacker News thread | `nvim_ref` · READ / REVIEW_FLEETING_NOTES | Editor-embedded agents; context for `sase-nvim`. |
| **CodeCompanion.nvim**: intro, configuration, usage | `nvim_ref` · READ | Multi-provider chat and agent plugin. |
| **CodeCompanion: Extending adapters** | `nvim_ref` · REVIEW_LIT_NOTES | Its adapter layer is a small-scale *Adapters Normalize Harnesses*. |
| **CodeCompanion** workflow-strategy code search, plus your prompts & workflows notes | `nvim_ref` · READ | Its workflow strategy is a cousin of macro workflows. |
| **mcphub.nvim README** | `nvim_ref` · REVIEW_FLEETING_NOTES | MCP servers managed from the editor. |
| **Managing MCP servers in Neovim** (apidog) | `nvim_ref` · READ | Same. |
| **VectorCode** (Davidyz) | `nvim_ref` · REVIEW_FLEETING_NOTES | Repo-indexed retrieval for coding agents; relevant to *corpus before mechanism*. |
| _13 Google-internal docs (`work_ref`)_ | READ / REVIEW_* (2025) | Vibe-coding levels and manifesto, an LLM agent guide, SWE responsibilities in the AI era, AI development outlook, function calling, prompt tooling, a docs agent, an editor agent, bug-triage tooling, small changes, code review, and decision frameworks. |

## 4. Started but Not Finished (86 in `ref/`, 19 More in Zorg Records)

These are legacy `collect_fleeting_notes` records: you started them in the 2025 backlog
and they were never marked done. They're listed so you can see what's half-read, not
claimed as read.

**Agentic-SE research papers:**

- *SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering* (arXiv
  2405.15793)
- *OpenHands: An Open Platform for AI Software Developers as Generalist Agents* (arXiv
  2407.16741)
- *Large Language Model-Based Agents for Software Engineering: A Survey* (arXiv
  2409.02977)
- *Mixture-of-Agents* (arXiv 2406.04692)
- *Lost in Code Generation: Reimagining the Role of Software Models in AI-driven SE*
  (arXiv 2511.02475)
- *Toward Agentic Software Engineering* (arXiv 2510.19692)
- *Agentic AI for Software: Thoughts from the SE Community* (ResearchGate)
- *A Survey on Agent Workflow* (arXiv 2508.01186)

**Single- vs multi-agent debate:**

- Cognition, *Don't Build Multi-Agents*
- *Inside the Multi-Agent Debate* (Cognition vs Anthropic)
- Phil Schmid, *Single vs Multi-Agents*
- *Agentic AI: Single vs Multi-Agent Systems* (Medium)
- *How LLMs and Multi-Agent Systems Work Together*
- *LLMs for Multi-Agent RL* (Xue Guang)

**Anthropic and OpenAI agent engineering:**

- *Building Effective Agents*
- *Writing Effective Tools for Agents*
- *Effective Context Engineering for AI Agents*
- *Building Agents with the Claude Agent SDK*
- *Equipping Agents for the Real World with Agent Skills*
- *Claude Code: Best Practices for Agentic Coding*
- Claude 4 prompting best practices
- Claude Code docs: subagents, hooks guide, plugins, common workflows
- OpenAI, *A Practical Guide to Building Agents*

**Prompt and workflow languages (the macro/xprompt lineage):**

- *PDL: A Declarative Prompt Programming Language* (arXiv 2410.19135), plus the PDL
  overview and tutorial
- *Declarative Prompt DSLs* (Emergent Mind)
- *Prompt Orchestration Markup Language* (arXiv 2508.13948)
- *From Prompts to Templates* (arXiv 2504.02052)
- *Prompts as Software Engineering Artifacts* (arXiv 2509.17548)
- *A Roadmap for Tamed Interactions with LLMs* (arXiv 2510.24819)
- *A Declarative Language for Building and Orchestrating LLM-Powered Agent Workflows*
  (arXiv 2512.19769)
- *Plang*
- Markform
- *Avoiding Multi-Agent Complexity with YAML*
- BAML intro

**Spec-driven development (the plan/epic lineage):**

- Martin Fowler site, *SDD: Kiro, spec-kit, Tessl*
- Thoughtworks, *Spec-Driven Development in 2025*
- Red Hat, *How Spec-Driven Development Improves AI Coding Quality*

**Claude Code practice:**

- HumanLayer, *Writing a Good CLAUDE.md*
- Three hooks guides (suiteinsider, eesel, A. Rezvani)
- Shrivu Shankar, *How I Use Every Claude Code Feature*
- Builder.io, *How I Use Claude Code* and *Codex vs Claude Code*
- *32 Claude Code Tips*
- Jesse Vincent, *Superpowers* and *How I'm Using Coding Agents in September 2025*
- SuperClaude docs
- Siddharth Bharath, Claude Skills and complete-guide posts
- *The Claude Code Playbook*, *My Claude Code Workflow*, *7 Best Practices*
- Claude Code 2.0 and Agent SDK best-practice posts
- *Claude Code 2025* timeline and *The Evolution of Claude Code*
- Rafael Quintanilha, *Using Codex as a Task Inbox*

**Durable agent runtimes:**

- LangGraph 1.0, *Building LangGraph*, *LangGraph Multi-Agent Workflows*, LangGraph
  overview, *LangGraph Explained*
- *Scalable Agent Systems with LangGraph: Memory, Streaming, Durability*
- LangChain, *Why Agent Infrastructure Matters*
- Galileo, *LangGraph vs AutoGen vs Crew*
- Hugging Face, agent memory post (Kseniase)

**Practitioner workflow essays:**

- Addy Osmani, *My LLM Coding Workflow*
- Seven Peaks, *Practical Guide to Agentic Software Development*
- QuantumBlack, *Agentic Workflows for Software Development*
- Pragmatic Engineer, *AI Coding Agents*
- Harper Reed, *An LLM Codegen Hero's Journey*
- Sanity, *First Attempt Will Be 95% Garbage*
- *Agentic AI Has Changed My Career*
- Repo Prompt docs

**Gemini CLI:**

- Headless mode docs
- 4 Google-internal decks and docs

**Zorg records outside `ref/` (started):**

- awesome-claude-code
- *My Remote-First Workflow* (rrmistry)
- claude-code.nvim
- contextfiles.nvim
- *Cursor vs CodeCompanion*
- CodeCompanion adapter configuration, plus your memory and chat-buffer notes
- avante.nvim wiki
- mcphub.nvim wiki
- *Managing MCP Servers with mcphub.nvim* (Medium)
- 8 Google-internal docs on AI-assisted development and evals

## 5. Tangential Reads (Finished, Weak Link)

- **Obsidian docs** (finished 2026-06-04). SASE memory links adopted Obsidian's
  `[[target]]` / `![[target]]` syntax (*Memory Links Are Authored*).
- **The Zettelkasten cluster** (roughly two dozen zorg-era reads across `zorg_ref`,
  `bobdoto_ref`, and `zettlr_ref`) and Karpathy's **The Append-and-Review Note**. Atomic,
  densely linked notes are the intellectual ancestor of memory webs and strands.
- **Editor and market pieces:** *My New Favorite IDE: Cursor*, *Introducing Zed AI*,
  *The Fastest AI Code Editor* (Zed), *Google Is Winning on Every AI Front*.
- **Release and tooling side-reads:** vhyrro's *Just Use Semver*, overseer.nvim.

## 6. SASE's Own Documents You Read and Annotated

These are not papers, but they are the most heavily annotated items in the library:

| Document | Finished | Comments | Gist of your comments |
| --- | --- | --- | --- |
| `sase AGENTS` (v1) | 2026-10-06 | 9 | Fold memory-edit permission text into the memory section; drop core notes that duplicate reference memory (artifact relations, feature flags); move test-monitor guidance into `/sase_monitor`. |
| `sase AGENTS v2` | 2026-10-06 | 14 | Memory-web text should name `sase memory read <web>:<slug>`; push finalizer and new-task procedure into their skills; drop Python-specific and xprompt-specific details from core memory. |
| `sase AGENTS v3` | 2026-08-29 | 3 | Replace the IMPORTANT memory paragraph with a pointer to `/sase_memory_write`; require `sase artifact read` for sidecar artifacts. |
| `sase_memory_write` skill | 2026-08-29 | 3 | Treat a bead that describes memory changes as authorization; drop the routing table; delete the obsolete `sase memory write/review` commands. |
| `sase INSTALL` | 2026-07-02 | 2 | Question whether `sase core health` is needed; make one step configurable. |

Several of these comments visibly landed: today's generated instructions route memory
edits through `/sase_memory_write` and require `sase artifact read` for sidecar artifacts,
in nearly your v3 wording.

## 7. Suggested Follow-Ups

1. **Decide on replay.** Two independent annotations, one on *The Log is the Agent* and
   one on Gas Town, ask for replay of tool calls or workflow steps. *EA-Graph*'s
   content-anchoring is the matching verification half. I did not check whether a bead
   already tracks this.
2. **Fix the SASE-paper entry.** Arguably the most relevant paper in the library is still
   `queued`/`unread` (`ref/ai/agent_ref/agent_swe.md`). Mark it read if you've read it.
   Otherwise it is the one item on this list worth reading next.
3. **Optionally migrate key zorg-era reads into `ref/`** so future `bob ref` lookups see
   them. Proposed commands (not run):
   - `bob ref create https://github.com/smtg-ai/claude-squad`
   - `bob ref create https://www.inkandswitch.com/essay/local-first`

Library check: 50 of 79 finished SASE-related reads are already in your library (all 50
finished). The other 29 live only in zorg-era records outside `ref/`. A further 86
related references are in your library as started (plus 19 started zorg-era records).
