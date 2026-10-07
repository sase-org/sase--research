---
title: "First SASE Blog Post: Architectural Analysis and Recommended Outline"
create_time: 2026-10-07T21:26:00-04:00
updated_time: 2026-10-07T21:26:00-04:00
status: research
tags:
  - blog
  - launch-strategy
  - sase-blog-0
  - technical-writing
  - obsidian-vault-audit
---

# First SASE Blog Post: Architectural Analysis and Recommended Outline

## Executive Summary

This research report investigates the architectural decisions, historical iterations, and recommended structure for the inaugural SASE blog post (Post 0 of the public technical series). Over the five months between May and October 2026, SASE's introductory blog post underwent multiple rewrites, one public publication and retraction, two independent consolidated research audits, and a stalled directed-Zettelkasten attempt. 

By auditing the notes, project files, and task archives in Bryan's Obsidian vault (`~/bob`), this report diagnoses why prior drafts stalled, identifies the essential personal material and critical technical requirements dropped by past agent-generated revisions, and evaluates how the mid-to-late 2026 developer ecosystem (e.g., OpenAI Codex app, Anthropic Claude Code, Databricks Omnigent) impacts SASE's external positioning.

The primary finding is that **the post's structural impasse is an ownership gap, not an outline deficiency**. Bryan's original outline from July 2026 was structurally sound, but previous automated attempts to flesh it out relied on documentation excerpts, creating an impersonal "product tour" that lacked the practitioner scars, empirical metrics, and candid admissions found across Bryan's private vault notes. Furthermore, embedding low-level installation mechanics into the conceptual launch essay interrupted narrative momentum and violated Diataxis documentation separation principles.

This analysis culminates in a **recommended section-by-section and subsection-by-subsection outline** that reconciles the proven conceptual spine with Bryan's unharvested vault insights—specifically integrating the "three-question grid" (High Value, Untapped Opportunity, Lesson Learned), the four categories of internal "AI Slop" and prompt debt, and hard empirical data from SASE's 11,000-commit ledger—while strictly deferring tutorial installation mechanics to the companion quickstart.

---

## 1. Vault Archaeological Audit: What Bryan Wrote, Committed, and Dropped

### 1.1 The Five-Month Iteration Cycle (May – October 2026)

A longitudinal review of Bryan's Obsidian vault (`~/bob/sase_blog.md`, `~/bob/sase_blog_0.md`, `~/bob/sase_blog_0_legacy_notes.md`, `~/bob/why_sase.md`, and task logs) reveals a recurring pattern:

| Date Window | Event / Artifact | Observed Dynamics |
| :--- | :--- | :--- |
| **May 2026** | Initial `[00]` Draft (`why-coding-agents-need-orchestration.md`) | A 5,400-word, 20-section monolith. Detailed and accurate, but suffered from reference-table density, visible `[00]` serialization numbering, early install instructions, and zero visual assets. Published briefly on 2026-05-09. |
| **June 2026** | Series Reassessment & First Research Consolidation | Consolidated audits (`blog00_launch_post_review_consolidated.md`, `sase_blog_series_structure_consolidated.md`) recommended pruning the 10-part series into a 6-post hub-and-spoke cluster, removing `[00]` numbering, and separating conceptual explanation from hands-on tutorial. |
| **Early July 2026** | July Draft (`structured-agentic-software-engineering.md`) | Bryan spent 19 days deciding on a refined outline (`sase_blog_0.md#^outline`), then used Fable to generate a 2,762-word draft on 2026-07-08. The `[00]` post was retracted (`draft: true`). |
| **Late July 2026** | The Authorship Gap Diagnosis (`first_post_authorship_gap.md`) | Proofreading stalled for 20 days with only one marginal annotation. Research diagnosed that every task where agents wrote text completed immediately, while every task requiring personal voice, judgment, or scar tissue stalled. |
| **August 2026** | Directed Zettelkasten Pilot (`directed_zettelkasten_first_post.md`) | Prescribed harvesting ~18 existing quotes from `~/bob` into atomic notes under `~/bob/zk/blog0/` to eliminate blank-page paralysis. Stalled because the method became another task container rather than a writing release. |
| **October 2026** | Present Day (`gkeep_inbox.md`, `20261007.md`) | Bryan captured new Google Keep tasks to launch research swarms to finalize the outline and draft the opening paragraph, alongside bookmarks of Databricks' Omnigent meta-harness and the original SASE research paper. |

### 1.2 The Root Cause: The "Replace-Don't-Own" Mechanism

The historical stalling was driven by what prior research accurately termed the **replace-don't-own cycle**. When proofreading a draft that felt overly synthetic, the natural reaction was to generate a replacement or embark on preparatory meta-work (creating new projects, restructuring notes, designing note-taking methodologies) rather than editing the draft in place.

Automated drafts extracted text primarily from product documentation (`docs/`). As a consequence:
1. Documentation describes intended mechanics, not failure modes, frustrations, or trade-offs.
2. The writing stripped out the very elements that make engineering essays compelling: personal voice, design regrets, humor, and operating data.
3. Every sentence became a stylistic judgment without clear criteria, turning proofreading into an exhausting editorial burden.

### 1.3 Unharvested Assets and Dropped Vault Requirements

A systematic comparison between the requirements documented in `~/bob/sase_blog.md` / `~/bob/sase_blog_0.md` and the existing draft text reveals vital technical and narrative elements that were never incorporated:

#### The Three-Question Section Grid
Under Bryan's completed outline task (`sase_blog_0.md#^outline`), an essential subtask remained uncompleted:
> *"Flesh out 'high value, high untapped opportunity, and an associated lesson learned' for each section."*

This grid was Bryan's explicit formula for injecting authentic engineering judgment into each technical section. Without it, sections read like feature catalogs rather than lived experiences.

#### The AI Slop Confession
In `sase_blog.md` (lines 50–54), Bryan defined four concrete categories of AI slop that actively manifest in SASE's own 900k-line codebase:
1. **Unnecessary backward compatibility** (defensive shims for discarded early patterns).
2. **Features never used or no longer used** (speculative complexity built by eager agents).
3. **Duplication of functionality and logic** (agents reimplementing utilities across subpackages).
4. **Prompt debt** (accumulated degradation in model alignment due to prompt drift and superficial code reviews).

This formulation is arguably the most original and impactful conceptual contribution in Bryan's vault. In an industry increasingly skeptical of AI-generated code, a technical founder candidly cataloging prompt debt in their own codebase is disarming, authoritative, and unfakable.

#### Dropped Admissions and One-Liners
Bryan's notes contain sharp, candid reflections that were systematically pruned by documentation generators:
- *"I'm bad at naming things but I worry that indicates a deeper problem with the design."*
- *"The Agents tab is the buggiest part of the TUI."*
- *"SASE does not claim optimal performance, but optimal experience."*
- *"Alternations allow for 'vibe evals'."*
- *"Plan mode is the canonical or best example of some deeper primitive. I know it. Interrupts?"*
- *"Motion isn't progress."* (quoting the Codex podcast against runaway commit counts).
- *"The scrollback buffer is the database. Close the window, lose the run."*
- The Gas Town comparison: Gas Town's fatal flaw of failing to interweave agent execution with deterministic local shell/Python logic.

#### The Empirical Ledger
As verified in `first_post_authorship_gap.md`, SASE is backed by massive, verifiable operational scale:
- **11,000+ Git commits** in ~5.5 months.
- **~895,000 lines of Python** (430k source, 465k test), reflecting a **1.08:1 test-to-source ratio**.
- **5,000+ recorded agent runs** (averaging ~226 runs/day, peaking near 500/day).
- **2,230 Beads and 6,000+ Plan documents**.

This ledger provides empirical grounding that few other engineering teams possess.

---

## 2. Late-2026 Ecosystem Context & Strategic Positioning

### 2.1 The Commoditization of Parallel Worktrees

In early 2026, running multiple agents in parallel Git worktrees was considered novel. By October 2026, it is standard practice:
- **OpenAI Codex app**: Native support for worktrees, automations, background threads, and IDE syncing.
- **Anthropic Claude Code**: Documented parallel worktree workflows, agent teams, and dedicated Agent SDK monthly budgets.
- **Databricks Omnigent (Matei Zaharia, June 2026)**: A meta-harness designed to combine, control, and share multi-agent workloads.
- **Hassan et al. (ArXiv:2509.06216)**: Formalized "Agentic Software Engineering," highlighting Consultation Request Packs (analogous to SASE gates) and multi-agent coordination frameworks.

**Strategic Consequence**: The blog post must **not** pitch "parallel agents in worktrees" or "a terminal split into windows" as SASE's primary innovation. Leading with parallelism invites immediate dismissal as a DIY rehash of Codex or Omnigent.

### 2.2 SASE's Distinct Wedge

SASE's true differentiation lies in being a **local, provider-neutral, Git-native operating layer that wraps agent CLIs rather than raw model APIs**:
1. **CLI Wrapper vs. Model API**: SASE does not attempt to build a custom code-editing harness or replace frontier vendor tools. It orchestrates the developer's existing, authenticated CLIs (`claude`, `codex`, `agy`, `qwen`, `opencode`, `muse`), inheriting vendor sandboxes, account tiers, and low-level optimizations while imposing structure around them.
2. **Durable Work Units vs. Transient Chats**: Chat transcripts and tmux buffers are ephemeral. SASE introduces structured units of engineering progress: ChangeSpecs, Beads (Git-native dependency tracking), and durable plan/artifact records.
3. **Deterministic Control Flow (Macros)**: Moving prompt engineering from volatile shell history into versioned, testable, parameterized prompt programs with directives (`%model`, `%wait`, `%id`, `%auto`).
4. **Supervised Autonomy (Interrupt Gates)**: Plan approval modals, feedback loops, and launch gates prevent agents from cascading into unmonitored rabbit holes.

---

## 3. Structural Evaluation: Why Previous Outlines Stumbled

### 3.1 Failure of the 20-Section `[00]` Outline
The May `[00]` draft attempted to serve simultaneously as a manifesto, install guide, directive specification, CLI cheat sheet, and competitor teardown. Readers faced reference tables and shell commands before understanding the conceptual premise, resulting in high cognitive drop-off.

### 3.2 Friction in the July 6-Section Outline
The July draft (`structured-agentic-software-engineering.md`) tightened the structure to six core areas:
1. Introduction (`tmux_ai_window`, Boris Cherny method, 😈/😇 bullets)
2. SASE Wraps Agent CLIs, Not Models
3. Macros (formerly XPrompts)
4. The Agents Tab in SASE's TUI
5. Install, Configure, Initialize
6. What's Next

While this outline had strong narrative momentum, two key flaws persisted:
- **The Mid-Post Tutorial Trap**: Section 5 ("Install, Configure, Initialize") inserted low-level shell setup (`uv tool install`, `sase doctor`, YAML configuration snippets) directly between the TUI showcase and the conclusion. According to Diataxis principles, an architectural essay (Explanation) should not be interrupted by a step-by-step setup guide (Tutorial). Installation belongs in the companion quickstart (`[01] Hello, SASE — Your First 15 Minutes`).
- **The Voice Vacuum**: Sections 2, 3, and 4 read like sterile rephrasings of the documentation site, omitting Bryan's three-question grid, technical regrets, and the AI slop confession.

---

## 4. Design Invariants for the Recommended Outline

1. **Adhere to the Proven Conceptual Spine**: Retain the core journey from the chaotic "window farm" to CLI encapsulation, prompt programs (Macros), and cockpit observability (TUI). Do not discard the structure that required 19 days to establish.
2. **Excise the Inline Tutorial**: Replace Section 5's detailed install/config block with a sharp, candid **"Confessions from the Ledger: AI Slop, Limitations, and Reality at Scale"** section. Reduce installation mechanics to a prominent link pointing directly to `[01] Getting Started`.
3. **Embed the Three-Question Grid**: Every technical core section must balance feature explanation with practitioner truth:
   - *High Value*: What concrete operational leverage does this provide?
   - *Untapped Opportunity*: What is still missing or unrefined?
   - *Lesson Learned / Scar*: What broke first when running 200 agents a day?
4. **Lead with Radical Technical Honesty**: Explicitly define prompt debt and the four categories of AI slop. An author auditing their own tool's imperfections immediately establishes credibility on Hacker News and technical forums.
5. **Clear Separation of Concerns Across the Blog Series**: Post 0 establishes the operating philosophy and the architecture. Subsequent posts handle detailed deep-dives (ChangeSpecs in Post 2, Beads/SDD in Post 3, AXE/Background execution in Post 4).

---

## 5. Recommended Outline for the First SASE Blog Post

### Proposed Metadata & Titles
- **Primary Title**: *SASE: The Missing Operating Layer for Coding Agents*
- **Alternative / Hacker News Title**: *Why Coding Agents Need an Operating Layer (Lessons from 11,000 Commits)*
- **Subtitle**: *From a tmux farm of CLI agents to a durable engineering control plane: five months of running 200 agent sessions a day.*
- **Canonical Slug**: `why-coding-agents-need-orchestration` (preserving established redirect routes)

---

### Outline Structure

#### 1. The Window Farm: Why Raw Coding Agents Hit a Wall
- **1.1 The Boris Cherny Method at Scale**
  - The developer status quo: running multiple CLI agents across terminal panes or tmux windows (`tmux_ai_window`).
  - The illusion of linear scaling: why juggling five terminal windows feels productive until real engineering coordination begins.
- **1.2 The Failure Modes of Unstructured Agent Work (The 😈 List)**
  - *The scrollback buffer as database*: Close the terminal window, lose the entire execution history.
  - *Context drift and prompt amnesia*: Retyping prompts from memory or digging through shell history.
  - *Unsupervised runaway execution*: The anxiety of an agent launching unauthorized child processes while the developer steps away.
  - *Handoff chaos*: "What did Agent 4 change, who reviewed the diff, and why did it break the test suite?"
- **1.3 The Thesis: Coding Agents Can Patch; Engineering Work Needs an Operating Layer**
  - Distinguishing code generation from software engineering.
  - The SASE paradigm: durable state, reusable prompt assets, supervision gates, and centralized observability (The 😇 List).
  - *Visual Asset*: `window_farm_vs_control_tower` diagram (tmux terminal sprawl vs. structured control tower).

#### 2. The Core Boundary: Wrapping Agent CLIs, Not Model APIs
- **2.1 Why SASE Does Not Call Raw Model APIs**
  - The temptation of building a custom LLM agent vs. the reality of frontier CLI velocity.
  - Respecting vendor runtimes: why wrapping `claude`, `codex`, `agy`, `qwen`, `opencode`, and `muse` preserves native tool ecosystems, sandboxes, and authentication models.
- **2.2 Preserving Runtimes While Inverting Control**
  - How SASE wraps the execution boundary: preprocessing prompt directives, managing workspace isolation, capturing raw transcripts, and handling structured exit finalization.
- **2.3 The Vendor Reality: Quota Economics and Model Routing**
  - Scarcity in agent budgets: managing Anthropic Agent SDK credits, Codex subscription limits, and fallback worker tiers.
  - Provider neutrality: decoupling engineering workflows from single-vendor lock-in.
- **2.4 Practitioner Reality (The Grid)**
  - *High Value*: Instant zero-maintenance adoption of vendor upgrades without modifying orchestration logic.
  - *High Untapped Opportunity*: Deeper provider-level token telemetry and unified cost auditing across heterogenous CLIs.
  - *Lesson Learned*: Subprocess streaming across five distinct CLI harnesses is fragile; vendor CLI updates can alter exit codes without warning.
  - *Visual Asset*: `one_prompt_provider_clis` diagram (single SASE orchestration layer routing across diverse agent runtimes).

#### 3. Prompts as Code: Deterministic Workflows with Macros
- **3.1 Moving Prompts Out of Shell History**
  - The Markdown Macro specification: version-controlled prompt templates with YAML frontmatter interfaces and Jinja2 templating.
- **3.2 Control Flow in Text: Directives**
  - Declaring execution parameters inline: model selection (`%model`), agent identity (`%id`), execution dependencies (`%wait`), and reasoning effort (`%effort`).
- **3.3 Fan-Out, Multi-Agent Workflows, and Vibe Evals**
  - Cartesian fan-out and alternations (`%{#review | #test}`): evaluating multi-model responses across identical tasks ("vibe evals").
  - Chained workflows: multi-segment execution with explicit barrier synchronization (`---` separators and `%wait` directives).
- **3.4 The Authoring Surface: Prompt Input Widget (PIW) vs. Editor LSP**
  - Why terminal prompt entry requires first-class ergonomics: vim normal mode, completion (`Ctrl+T`), history (`Ctrl+K`), and stashing (`Ctrl+S`).
  - Bridging the editor gap: `sase-nvim` and LSP support.
- **3.5 Practitioner Reality (The Grid)**
  - *High Value*: Turning disposable prompts into durable, team-shareable engineering tools.
  - *High Untapped Opportunity*: Strict type validation and static linting for nested YAML workflows.
  - *Lesson Learned*: Silent authoring failures—unrecognized macro names passing through verbatim to the model, and prompt debt accumulating from unvetted template edits.
  - *Visual Asset*: `sase_ace_prompt_input.gif` (interactive prompt input with completion and workspace expansion).

#### 4. The Cockpit: Terminal Observability and Human Supervision
- **4.1 Centralized Observability Over Multi-Agent Sprawl**
  - Moving beyond window-hopping: the SASE TUI Agents tab.
  - Hierarchical agent taxonomy: grouping runs by projects, plan sessions (`--plan`, `--code`), clans, and hoods.
  - Status glyphs and provider badges: reading system-wide execution status at a glance.
- **4.2 Gates as Interrupt Primitives: Human-in-the-Loop Steering**
  - Why unconstrained agents drift: the necessity of structured interrupt gates.
  - Plan review and approval workflows: approving, rejecting, editing, or converting plans into epics before files are touched.
- **4.3 Supervised Fan-Out: The Launch Approval Gate**
  - Preventing agent explosion: catching recursive agent spawn requests before tokens burn.
- **4.4 Practitioner Reality (The Grid)**
  - *High Value*: Reclaiming developer focus; transforming chaotic terminal multitasking into a calm review-and-dispatch loop.
  - *High Untapped Opportunity*: Integrated diff review and inline syntax highlighting directly inside the TUI dashboard.
  - *Lesson Learned*: "The Agents tab is the buggiest part of the TUI"—managing complex Textual widget hierarchies, asynchronous state updates, and terminal resize edge cases.
  - *Visual Assets*: `sase_ace_agents_observability.gif` / `agents_observability_still.png` (live TUI observability tree).

#### 5. Confessions from the Ledger: AI Slop, Limitations, and Scale
- **5.1 The Empirical Ledger: Five Months of High-Velocity Agent Runs**
  - Verified operational figures: 11,000+ Git commits, 895,000 lines of Python, 1.08:1 test-to-source ratio, and 5,000+ agent executions.
  - Deconstructing the numbers: What happens when a solo engineer averages 226 agent runs a day?
- **5.2 Cataloging AI Slop in SASE's Own Codebase**
  - *Unnecessary backward compatibility*: Zombie code paths retained to support deprecated prototype syntax.
  - *Ghost features*: Overengineered capabilities built by autonomous agents that no human ever invoked.
  - *Duplicated logic*: Subtle parallel implementations of common utility functions across decoupled packages.
  - *Prompt Debt*: The compounding decay of system alignment when agents build atop prior agent-generated code under drifting prompts.
- **5.3 What SASE Is Not (Candid Limitations)**
  - Not an autonomous self-driving developer; SASE optimizes developer experience, not unsupervised autonomy.
  - Not a hosted enterprise SaaS; local-first, POSIX-centric terminal software.
  - The open design scars: naming regrets ("I'm bad at naming things..."), unhandled Textual crash screens, and rapid CLI API churn.

#### 6. The Road Ahead: From Workspaces to an Agentic Ecosystem
- **6.1 The SASE Public Series Roadmap**
  - Brief roadmap of upcoming focused deep-dives:
    - *Post 1: Hello, SASE — Your First 15 Minutes* (Link to practical installation and first run).
    - *Post 2: ChangeSpecs — The Durable Unit of Agent Work* (Review records, commit flow, and PR integration).
    - *Post 3: Planning Work That Lands — Beads, SDD, and Dependency Graphs*.
    - *Post 4: The Engine Room — AXE Background Automation, Hooks, and Mobile Control*.
- **6.2 SASE in the Late-2026 Landscape**
  - Situating SASE alongside OpenAI Codex app, Databricks Omnigent, and the Hassan et al. research paper.
  - Why local, open, hackable orchestration remains critical for software engineers.
- **6.3 Conclusion: "No Weasels; Just Work"**
  - Summary of the core ethos: disciplined structure around creative agents.
  - Call to action: GitHub repository link, docs at [sase.sh](https://sase.sh), and quickstart link.

---

## 6. Implementation Notes for the Author

1. **Keep Post 0 Conceptual**: Do not reintroduce terminal install commands (`uv tool install sase`) or configuration YAML into Section 1 or Section 5. Defer all setup mechanics to the Post 1 / Getting Started link.
2. **Execute the Three-Question Grid Directly**: The subsections labeled *Practitioner Reality (The Grid)* represent the primary vehicle for Bryan's voice. They should be written directly from personal experience rather than delegated to documentation extractors.
3. **Render the Scaffolding Briefs**: Prioritize rendering the three existing diagram briefs (`window_farm_vs_control_tower.prompt.md`, `one_prompt_provider_clis.prompt.md`, and `prompt_burrito.prompt.md`) into final graphical assets.
4. **Publish the Prompt Debt Definition**: Highlight the concept of "Prompt Debt" in Section 5; it serves as a powerful intellectual anchor that resonates with experienced practitioners navigating generative software development.
