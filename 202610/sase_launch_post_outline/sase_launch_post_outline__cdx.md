# Choosing an outline for the first SASE blog post

Researcher: cdx  
Research date: 2026-10-07  
Scope: editorial research and a recommended outline; no blog prose drafted.

This investigation began with Bryan's Obsidian notes and tasks, followed by primary-source research and checks against the current SASE checkout. No other report, chat, summary, or findings from this research swarm was consulted.

## Recommendation

Make the first post a personal engineering case study: why Bryan built SASE, what coordination problems appeared when he started supervising coding agents, and what he learned while building a working environment around them.

The strongest organizing principle is the reader's work: making prompts repeatable, supervising concurrent work, and preserving useful state. Introduce SASE's components inside that argument. The current feature-first outline gives considerable space to syntax and UI taxonomy before establishing why those details matter.

Suggested working title: **Why I Built SASE: A Working Environment for Coding Agents**.

Primary audience: developers who already use a coding-agent CLI and are beginning to run several tasks or sessions at once. The post should also make sense to a curious engineer with only one agent. It should answer why someone might want this layer, what it changes in everyday work, what it costs, and how to try it.

An editorial target of roughly 2,200–2,800 words is reasonable. This is a scope recommendation, not a research finding or a requirement. Use one recognizable work example across the technical sections, with a short demo near the beginning.

## What the vault actually says

The initial Dataview queries located related notes and tasks. Targeted notes were then read through Bob's read-only reference reader with the vault root as its search scope; its generated “reading state” for ordinary project notes was not treated as reading-history evidence. External references were checked separately in the normal reference library.

| Vault source | Evidence | Implication for the outline |
| --- | --- | --- |
| `sase_blog_0.md`, Requirements and Outline | Calls for a short transformation timeline, the Boris-method/`tmux_ai_window` origin, citations, humorous diagrams, screenshots, a “Why a TUI?” section, token choices, and prompt stashes. Its existing outline gives major sections to XPrompts, ACE, AXE, and later posts. | Preserve the personal origin and visible user experience; reorganize the material around reader problems. |
| `sase_blog_0.md`, active and blocked tasks | Work remains around architecture zettels, gathering references, and planning demos/infographics. The “high value, high untapped opportunity, and an associated lesson learned” task was canceled on October 6 because it duplicated the zettel task. | The underlying need for a lesson in each section remains useful, but the canceled task is not a separate launch dependency. |
| `why_sase.md` | Connects building SASE to pride in being a software engineer, uncertainty about the changing role, and wanting more control. Contains a reminder that activity metrics are not progress. | Bryan's viewpoint is a better opening than an exhaustive product inventory. Code volume and commit counts should not carry the argument. |
| `sase_blog.md` | Requests honest limitations, an explanation of AI slop, and “prompt debt”; gives examples of waits and retries; describes the ambition for the prompt input widget. | Include a compact lessons-and-limits section and practical reasons for waits/forks. Keep naming jokes and editor ambitions subordinate to the argument. |
| `ref/docs/sase_blog_260708.md` | Bryan's annotation asks for devil/angel bullets explaining why `%wait` and `#fork` are needed. The draft reference itself is marked dropped. | This is direct author feedback to explain the coordination problem before showing syntax. It is not a reason to revive the old draft as a reading assignment. |
| `sase_blog_0_legacy_notes.md` | Explicitly labels itself obsolete. Includes broad feature coverage and an assertion about a “fatal flaw” in Gas Town. | Treat it as idea history. Do not inherit its competitive assertion or its ten-part scope as current requirements. |
| `sase_blog_blockers.md` | The project was canceled in August; its listed tasks are completed or canceled. | Do not revive this old list as a set of release prerequisites. |
| `ref/papers/agentic_software_engineering.md` | Bryan's two comments connect consultation packs to gates and ask about recording “why” in plan frontmatter. | The connection between human intent, explicit decisions, and durable plans is a promising design lesson, without needing a paper-summary section. |

Two newer reminders in `sase_blog_0.md` are not yet sufficiently specified: “different types of tokens” and “AI broccoli.” Preserve space for them, but let Bryan supply the meaning and a concrete experience. This research did not equate AI broccoli with AI slop, infer a taxonomy of tokens, or invent a story for either.

The reference-gathering task points to `harness_for_rsi`, but its reference record is marked dropped on October 3. It should not be the default recommended reading.

## External research and what it changes

### Human attention is a credible opening problem

OpenAI's April 27, 2026 Symphony account describes engineers juggling several interactive sessions, losing track of work, and moving coordination toward deliverables and an issue tracker. It also discusses the tradeoffs of reduced mid-flight steering. This is strong corroboration for the attention problem in Bryan's notes. **Editorial inference:** introduce SASE as Bryan's particular answer to a familiar problem, and acknowledge that orchestration already has other implementations. The article's PR-throughput result is evidence about those teams, not a transferable SASE benefit. [OpenAI: Symphony](https://openai.com/index/open-source-codex-orchestration-symphony/)

### State between sessions deserves space in the introduction

Anthropic's November 26, 2025 harness article describes failures across context windows, premature completion, and incomplete handovers. Its approach uses incremental work, progress records, git history, and explicit verification. **Editorial inference:** durable plans and artifacts should be visible in post one even if their full mechanics belong in later posts. They explain what makes SASE more than a convenient launcher. This source is a particular harness experiment, not proof that every agent or project needs the same architecture. [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

### The author's engineering lessons can carry the post

OpenAI's February 11, 2026 harness article organizes its account around environmental legibility, repository knowledge, feedback loops, architectural rules, and recurring cleanup. It describes drift caused by agents copying existing patterns. **Editorial inference:** Bryan's ideas about prompt debt, duplicated functionality, and unused features can become a substantive engineering section rather than a generic disclaimer. The article is an experience report from a specific team; its speed estimates should not become a headline claim for SASE. [OpenAI: Harness engineering](https://openai.com/index/harness-engineering/)

### Explicit workflows and agent judgment are different ideas

Anthropic's December 19, 2024 article distinguishes predefined workflows from agents that choose their own steps, describes several parallelization patterns, and recommends adding complexity when justified. The current page itself warns that its tooling landscape has changed. **Editorial inference:** briefly explain the benefit of explicit ordering, fan-out, and checkpoints, then reserve full workflow syntax for a follow-up. A short reusable prompt should be sufficient as the entry point. [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)

### Attribute the SASE idea accurately

Hassan and colleagues' paper presents Structured Agentic Software Engineering as a vision for human and agent workbenches, with consultation and handover between them. The original submission was September 7, 2025; the current arXiv entry is version 3, dated June 24, 2026. **Editorial inference:** include a brief attribution where SASE is defined. Describe Bryan's project as an implementation influenced by the vision, without implying the paper validates this software or specifies every current design choice. [Agentic Software Engineering: Foundational Pillars and a Research Roadmap](https://arxiv.org/abs/2509.06216)

### Prompt composition has a relevant intellectual ancestor

Vaziri and colleagues' October 24, 2024 PDL paper argues for a declarative, prompt-centered language that keeps control of prompts while supporting calls to models and tools. SASE's own acknowledgements identifies it as an influence on workflows. **Editorial inference:** use it as a concise attribution in the prompt/control-flow section. Distinguish deterministic prompt expansion and explicit orchestration from the probabilistic output of a model. [PDL: A Declarative Prompt Programming Language](https://arxiv.org/abs/2410.19135)

### Parallel sessions are already available in agent CLIs

The current Claude Code common-workflows documentation describes isolated parallel sessions with worktrees, plan mode, session management, and scripting. **Editorial inference:** an opening should describe what became difficult in Bryan's own setup, without claiming all native CLIs lack persistence, parallelism, or useful controls. SASE's case should rest on the integration of reusable prompts, cross-provider work, durable project records, and human supervision. [Claude Code: Common workflows](https://code.claude.com/docs/en/common-workflows)

### Experience and speed need separate claims

METR's February 24, 2026 update explains why its newer productivity estimates are unreliable: participation and task-selection effects, plus difficulty measuring time when developers run agents concurrently. It considers greater current speedup plausible while emphasizing uncertainty. **Editorial inference:** Bryan's “optimal experience” preference can guide the post, but call it a design priority and personal experience. Avoid claiming optimality was demonstrated. Do not present the early-2025 slowdown result as a current universal verdict either. [METR: Developer productivity experiment update](https://metr.org/blog/2026-02-24-uplift-update/)

## Which structure to choose

| Candidate | Strength | Cost | Decision |
| --- | --- | --- | --- |
| A feature tour: prompts → TUI → scheduler → everything else | Easy to map to existing documentation and clips. | Reads like a manual; creates substantial scope and terminology load. | Use as a coverage checklist. |
| A broad manifesto about the future of software engineering | Fits the personal identity notes and research inspiration. | Requires defending industry-wide predictions; delays the tool's concrete value. | Keep the personal motivation and a brief conceptual timeline. |
| A personal engineering case study organized around work | Combines motivation, practical proof, reusable lessons, and a next step. | Requires selecting a few real examples and excluding interesting detail. | Recommended. |

The choice is an editorial judgment, not a measured preference study. No audience testing was performed.

## Boundaries and sequencing

**Establish a recognizable problem early.** Keep the origin sequence short: the shift in Bryan's own work, parallel CLI sessions, `tmux_ai_window`, and the coordination needs that followed. A timeline can be a small conceptual graphic. A chronology of every model or CLI release would consume the introduction and become stale.

**Give SASE a small mental model.** The current architecture guide describes prompt parsing and expansion, workspace allocation, provider execution, durable artifacts, notifications, and review/completion handling. Show that high-level flow once. Current decisions also make agent turns finite and completion host-owned; these are good optional design lessons if they explain a demonstrated handoff. Rust wire contracts, process internals, and finalizer protocol details can wait. Local evidence: `docs/architecture.md`; audited decisions `single-turn-agents` and `host-owned-completion`.

**Keep the main technical material in three connected groups.** Repeatable prompts and control flow; supervision and human decisions; durable work and background continuity. This keeps the author's original XPrompts/ACE/AXE interests visible while giving the reader a reason for each.

**Use one continuing example.** A modest task or investigation can connect composing a prompt, launching work, waiting for prerequisites, inspecting evidence, making a decision, and recovering useful context. A multi-model comparison is a useful fan-out demonstration. It should not be presented as a rigorous evaluation simply because the outputs differ.

**Keep durable work understandable.** Introduce plans, artifacts, and tracked changes through their use. The full bead hierarchy, Patch lifecycle, and agent-grouping vocabulary can be linked. Current Goals are person-owned outcome records, distinct from agent liveness; include this distinction only if the chosen example needs it.

**Keep background automation compact.** Current documentation describes the scheduler as running script jobs that can produce validated agent-launch proposals. A brief explanation shows how work continues outside the foreground interaction. Detailed cadence, routine configuration, maintenance behavior, and Telegram setup belong in follow-ups. Do not suggest that a continuously surviving LLM process owns all scheduling.

**Use current names.** The vault's XPrompts are now Macros; ChangeSpecs are Patches; AXE is a historical alias for the scheduler. The current entry point is `sase tui`. Older “families” correspond to agent sessions. These changes are documented in the glossary and current guides. Do not make readers learn both entire vocabularies. Local evidence: `docs/macros.md`, `docs/axe.md`, `README.md`, and the audited glossary.

**Finish with fit, limits, and one practical next step.** Keep alpha status, POSIX support, provider authentication, and the cost of configuring another layer concise and close to the invitation to try it. Link the existing Getting Started guide instead of reproducing installation, initialization, provider lists, and configuration blocks. Its read-only first run provides a useful starting point. Local evidence: `README.md` and `docs/getting_started.md`.

A practical allocation is about 30% for origin/problem/mental model, 45% for the three technical groups, 20% for lessons and limits, and 5% for next steps. These are editorial proportions.

## Visual and demonstration recommendations

Recommend assets here; this assignment does not create images, videos, or blog content.

| Placement | Recommended evidence | Existing material or constraint |
| --- | --- | --- |
| Opening | A short live view that makes the scale of concurrent work legible. | `docs/images/blog/sase_ace_multi_model_fanout.gif` demonstrates launch and kill controls. It does not, by itself, prove review quality or completed delivery. |
| Origin/problem | One humorous timeline or terminal-to-supervision illustration. | Aligns with the stick-figure and devil/halo preferences in `sase_blog_0.md`. Keep it specific to the coordination problem. |
| Prompt/control flow | One diagram of reuse, parallel work, an explicit dependency, and a checkpoint. | Reuse the continuing example; omit a full syntax chart. Native CLI capabilities should be represented fairly. |
| Supervision | One readable still plus a focused clip showing status and inspection. | `docs/images/blog/agents_observability_still.png` and the observability clip referenced by `README.md`. Verify that the selected frame reflects the current UI. |
| Durable work/lessons | One actual artifact or tracked-change view demonstrating a handover. | Bryan's vault records an agent reading four related plans. Use the example only after inspecting the actual evidence; this research did not verify those screenshots or the four reads. |

The three planned funny diagrams are an upper bound, not three additional research dependencies. Every visual should make a specific claim easier to assess. The asset filenames and captions above were checked in repository documentation; the recordings were not replayed or visually audited.

## What belongs in later posts

Reserve detailed Macro argument types, directive lists, multi-prompt versus YAML workflow syntax, LSP setup, keyboard references, agent group taxonomies, scheduler configuration, Telegram setup, bead/epic execution, Patch hooks/mentors/comments, memory architecture, plugin APIs, and eval design for separate posts.

The initial post should still acknowledge the existence of durable plans and current memory. The old outline's “future memory” label is outdated. Similarly, Telegram and other current integrations should not be casually presented as hypothetical future capabilities.

Competitive comparison can be a short positioning paragraph if needed. A Gas Town teardown adds a verification burden and distracts from Bryan's experience. The obsolete “fatal flaw” assertion was not independently substantiated here and should not be published from these notes.

The concrete author input still needed for a draft is one successful work example, one failure or maintenance lesson, the intended meaning of AI broccoli, and the token-related experience Bryan wants to discuss. Their absence does not prevent deciding this outline.

The checkout already contains `docs/blog/posts/structured-agentic-software-engineering.md`, dated July 8 and using publication wording, while the vault continues to track the first-post project as pending. This report treats the page as existing editorial material, not as proof of public launch status. Its provider/configuration/UI detail is a useful source to trim and verify rather than a requirement to reproduce.

## Reference-library check

These sources were checked together with `bob ref find`. Finished items are cited as background already read; the table is not a request to reread them. “Not found” means absent from the indexed reference library, not proof Bryan has never read the source.

| Source | Library state |
| --- | --- |
| Agentic Software Engineering paper | Queued since 2026-10-07; prefer the modern record over the superseded legacy capture. |
| PDL paper | Started; legacy backlog capture from 2026-01-30. |
| Building effective agents | Started; legacy backlog capture from 2025-10-27. |
| Effective harnesses for long-running agents | Queued since 2026-03-15; legacy backlog. |
| Harness engineering | Finished. |
| Symphony | Finished. |
| Claude Code common workflows | Started; legacy backlog capture from 2025-12-24. |
| METR February 2026 update | Not found in the indexed library. |

Library check: 7 of 8 candidates already in your library (2 finished).

## Recommended outline

# Why I Built SASE: A Working Environment for Coding Agents

## 1. Why I Started Building SASE

### A Short Timeline of My Changing Work
### Boris' Method and `tmux_ai_window`
### The Coordination Problems That Followed

## 2. What Needed Structure

### Prompts and Dependencies
### Human Attention and Decisions
### Context and Work Across Sessions

## 3. The SASE Working Environment

### The Research Vision Behind the Name
### Existing Agent CLIs and a Shared Coordination Layer
### From Intent to Work to Reviewable Evidence

## 4. Repeatable Prompts and Explicit Control Flow

### Macros: From Prompt Fragments to Reusable Work
### Fan-Out, Waits, and Forks
### Deterministic Steps and Agent Judgment
### Composing Prompts in the TUI and Editor

## 5. Supervising Work From One Screen

### Why a TUI?
### Status, Chats, Diffs, and Artifacts
### Notifications, Gates, and Human Judgment
### Prompt History, Stashes, and Resource Choices

## 6. Work That Survives the Chat

### Durable Plans, Artifacts, and Tracked Changes
### Handoffs and Recovering Context
### Background Scheduling and Remote Decisions

## 7. What Building SASE Taught Me

### Developer Experience and the Cost of More Agents
### AI Slop, Prompt Debt, and AI Broccoli
### Current Limits and Who SASE Fits

## 8. Try SASE and Shape What Comes Next

### The Getting Started Guide
### Questions for Readers
### Further Posts
