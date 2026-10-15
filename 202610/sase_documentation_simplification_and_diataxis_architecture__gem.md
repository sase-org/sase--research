# SASE Documentation Simplification & Diátaxis Architecture
**Author:** researcher gem (`research.4l.gem`)  
**Date:** October 2026  
**Target Surface:** `sase.sh` public documentation and internal docs engineering process  
**Status:** Completed Research Report  

---

## Executive Summary

The proposal to drastically simplify SASE's public documentation on `sase.sh` while introducing structured documentation processes is not merely a good idea—it is an urgent strategic necessity.

Today, SASE possesses a sophisticated, world-class agentic coordination layer (spanning single-turn agent execution, git-native Beads, spec-driven development, the Textual ACE TUI, background daemon AXE, and a Rust core engine). However, its documentation on `sase.sh` suffers from severe **"Kitchen Sink Monolith Syndrome."** Over 4.1 MB of Markdown text is concentrated across approximately 50 files, with flagship pages running between 2,000 and nearly 10,000 lines (e.g., `ace.md` at 9,771 lines / 740 KB; `configuration.md` at 7,768 lines / 668 KB; `beads.md` at 3,047 lines / 201 KB). The site's current information architecture relies on arbitrary cognitive tiers—*"Getting Started"*, *"The Basics"*, *"Beyond the Basics"*, and *"The Nitty Gritty"*—which obscure the user's intent, mix incompatible modes of writing, and present new visitors with a paralyzing wall of 17 homepage cards and 50+ unsegmented sidebar items.

Adopting the **Diátaxis framework** (https://diataxis.fr) offers SASE the exact architectural rigor needed to disentangle this material into four purpose-built documentation quadrants:
1. **Tutorials (Learning-Oriented):** Safe, end-to-end learning journeys for newcomers acquiring competence.
2. **How-To Guides (Problem-Oriented):** Practical, goal-driven recipes for real-world production tasks.
3. **Reference (Information-Oriented):** Austere, authoritative, complete descriptions of APIs, CLI commands, configuration keys, and schemas.
4. **Explanation (Understanding-Oriented):** Illuminating discussions on architecture, design philosophy, single-turn execution, and coordination invariants.

### Key Conclusions & Strategic Adjustments

1. **Reject Dogmatic Fragmentation via "Topic Hubs":** Pure Diátaxis can disorient users if every feature is fragmented across four disjoint directories without connective tissue. We propose a **Hub-and-Spoke Model** with **Diátaxis Compass Cross-linking**, where major subsystems (e.g., *Beads*, *ACE TUI*, *Macros*, *AXE Daemon*) have unified entry portals that link cleanly to their respective quadrant artifacts.
2. **Eliminate Hand-Crafted Reference via Single Source of Truth (SSOT) Automation:** Hand-authoring CLI tables and configuration options in Markdown is a primary driver of documentation drift. We recommend extending SASE's existing code-generation pattern (exemplified by `tools/render_model_docs`) to auto-generate CLI flags, configuration schemas, and TUI keymaps directly from source code and `default_config.yml`.
3. **Overhaul sase.sh Information Architecture & UX:** Leverage MkDocs Material's `navigation.tabs` to establish top-level quadrant tabs (`Tutorials`, `How-To Guides`, `Reference`, `Architecture & Concepts`), replace the homepage's 17-card choice overload with three distinct persona-driven paths, and introduce visual quadrant chips and cheatsheet search tools.
4. **Enforce Governance through Budgets and CI Linters:** Introduce `just docs-lint` with a maximum line-budget rule (warning at 1,500 lines; error at 2,500 lines) and archetype templates (`templates/docs/`) to permanently prevent future monolithic regressions.
5. **Enable Agentic Documentation Maintenance as a Natural SASE Byproduct:** SASE agents thrive when assigned single-turn, well-bounded tasks. By giving each documentation page a single, unambiguous Diátaxis purpose, SASE agents can reliably write, verify, and update docs without prompt dilution or tone contamination.

---

## 1. Current State Audit: The "Kitchen Sink" Crisis on sase.sh

### 1.1 Quantitative Footprint

A forensic audit of the SASE `docs/` repository reveals an astonishing content density:
- **Total Markdown Text:** Over 4,176 KB across ~50 active files.
- **Top 5 Monoliths:**
  - `docs/ace.md`: **9,771 lines** (739,714 bytes / ~740 KB)
  - `docs/configuration.md`: **7,768 lines** (667,818 bytes / ~668 KB)
  - `docs/llms.md`: **3,582 lines** (237,286 bytes / ~237 KB)
  - `docs/macros.md`: **~3,400 lines** (243,904 bytes / ~244 KB)
  - `docs/beads.md`: **3,047 lines** (201,377 bytes / ~201 KB)
  - `docs/cli.md`: **1,026 lines** (210,626 bytes / ~211 KB)
  - `docs/notifications.md`: **~1,900 lines** (135,943 bytes / ~136 KB)
  - `docs/axe.md`: **~1,800 lines** (125,139 bytes / ~125 KB)

For context, standard technical documentation pages typically span between 150 and 800 lines. Having single documentation files approaching 10,000 lines is an extreme outlier that imposes significant performance, cognitive, and maintenance costs.

### 1.2 The Failure Modes of the Current Structure

```
+------------------------------------------------------------------------------------+
|                             CURRENT SITE ARCHITECTURE                              |
+------------------------------------------------------------------------------------+
|  Home  |  Getting Started  |  The Basics  |  Beyond the Basics  |  The Nitty Gritty|
+------------------------------------------------------------------------------------+
                                      |
                                      v
          +-------------------------------------------------------+
          |            ARBITRARY COGNITIVE TIERING                |
          | - What makes "Goals" Beyond the Basics, while         |
          |   "Memory" is in The Basics?                          |
          | - What makes "Commit Workflows" Nitty Gritty?         |
          | - Modality collision: Tutorial + How-To + Reference   |
          |   + Architecture crammed into single 10,000-line files|
          +-------------------------------------------------------+
```

#### Failure Mode 1: Arbitrary Cognitive Tiering
The current navigation relies on vague developmental phases:
- `Getting Started`
- `The Basics`
- `Beyond the Basics`
- `The Nitty Gritty`
- `Integrations`
- `Reference`

This taxonomy is author-centric rather than user-centric. When a developer visits `sase.sh`, they do not categorize their question as "Basic" or "Nitty Gritty." They ask:
- *"How do I configure SASE to work with GitHub pull requests?"* (A How-To Guide)
- *"What are the valid values for `autonomy_policy`?"* (A Reference lookup)
- *"How do I run my first agent?"* (A Tutorial)
- *"Why does SASE enforce single-turn execution instead of multi-turn chat loops?"* (An Explanation)

Under the current taxonomy, a user seeking to configure notifications finds `notifications.md` under "The Nitty Gritty", while configuring memory is under "The Basics", and configuring monitors is under "Beyond the Basics".

#### Failure Mode 2: Modality Contamination (The Kitchen Sink)
Consider `docs/ace.md` (9,771 lines). In this single document, the reader encounters:
1. An introduction to what the TUI is (Explanation).
2. Step-by-step instructions on launching `sase tui` (Tutorial).
3. How to split panes, pin agents, and filter tabs (How-To).
4. Exhaustive tables of every single leader-mode keybinding and vim-style navigation key (Reference).
5. Internal architecture of the Textual event loop, headless tmux driver, and snapshot engine (Explanation / Internal Reference).
6. Troubleshooting and revival runbooks for OOM crashes and bus errors (How-To / Troubleshooting).

When a user opens this page to look up a keybinding, their browser must parse 740 KB of HTML, and their search highlights dozens of irrelevant hits buried across thousands of lines.

#### Failure Mode 3: Search Degradation & Discoverability
In MkDocs Material, client-side search operates across document units. When documents are monolithic, search matches rank poorly because keywords appear dozens of times across multiple unrelated sections of the same file. The user is delivered to the top of a 9,000-line page rather than directly to the specific snippet they require.

#### Failure Mode 4: Homepage Choice Paralysis
The current `docs/index.md` presents:
- 4 primary CTA buttons in the hero header.
- 8 role-based cards under *"Pick the surface that matches your work"*.
- 9 additional cards under *"Move from overview to practice"*.
Totaling **17 distinct cards and 21 competing links** on the homepage alone. A developer evaluating SASE experiences immediate cognitive overload and cannot discern the critical golden path.

---

## 2. Diátaxis Framework: Deep Analysis & Fit for SASE

The Diátaxis framework, developed by Daniele Procida, is grounded in a simple but profound insight: **technical documentation serves four distinct human needs, requiring four distinct styles and structures.**

```
                      PRACTICAL STEPS (Action)
                                  ▲
                                  │
               TUTORIALS          │        HOW-TO GUIDES
           (Learning-oriented)    │     (Problem-oriented)
                                  │
    ACQUISITION                   │                     SERVING
    OF COMPETENCE ────────────────┼──────────────────── OUR WORK
    (Study/Education)             │                     (Production/Tasks)
                                  │
               EXPLANATION        │          REFERENCE
          (Understanding-oriented)│    (Information-oriented)
                                  │
                                  ▼
                    THEORETICAL KNOWLEDGE (Cognition)
```

### 2.1 The Four Quadrants Applied to SASE

| Quadrant | User Mindset | Goal in SASE | Tone & Style | What it MUST NOT contain |
| :--- | :--- | :--- | :--- | :--- |
| **Tutorials** | *"I am a beginner; teach me."* | Guide the user through installing SASE, launching their first agent safely in `home`, and inspecting the resulting patch in 15 minutes. | Welcoming, prescriptive, step-by-step, confidence-building. No options; one verified path. | No architectural justifications, no alternate configurations, no complete flag tables. |
| **How-To Guides** | *"I am working and need to solve a specific problem."* | Provide direct recipes: *"How to set up GitHub PR integration"*, *"How to configure Claude 3.5 Sonnet & Antigravity CLI"*, *"How to run remote dispatch over Tailscale"*, *"How to author a custom Macro"*. | Action-oriented, practical, assuming competence. Starts with prerequisites and ends with verification. | No beginner hand-holding, no conceptual treatises, no exhaustive parameter lists. |
| **Reference** | *"I need precise facts and specs right now."* | Authoritative, dry lookup: CLI flag definitions, `sase.yml` schema tables, `models.yml` tiers, TUI keymap tables, Macro `@`/`%` directive syntax. | Dry, austere, structured, comprehensive, exact, predictable. | No narrative prose, no tutorial walkthroughs, no opinion. |
| **Explanation** | *"I want to understand the design and concepts."* | Explain the core philosophy: *"The Single-Turn Agent Contract"*, *"Why Completion is Host-Owned"*, *"The SASE Goal Ledger vs Beads"*, *"Rust Core Backend Boundary"*, *"Memory Webs Architecture"*. | Discursive, illuminating, conceptual, architectural. Connects concepts and explains trade-offs. | No command-by-command instructions, no API parameter tables. |

### 2.2 SASE Monolith Decomposition Matrix

The table below demonstrates how SASE's current monolithic files naturally decompose into clean Diátaxis artifacts:

| Current Monolith (Path & Size) | Decomposed Target: Tutorials | Decomposed Target: How-To Guides | Decomposed Target: Reference | Decomposed Target: Explanation |
| :--- | :--- | :--- | :--- | :--- |
| **`docs/ace.md`**<br>(740 KB, 9,771 lines) | `tutorials/tui-walkthrough.md`<br>*(Touring the TUI in 5 mins)* | `how-to/tui/manage-agents.md`<br>`how-to/tui/capture-screenshots.md`<br>`how-to/tui/navigate-splits.md` | `reference/tui-keymaps.md`<br>`reference/tui-palette.md`<br>`reference/tui-views.md` | `explanation/tui-architecture.md`<br>`explanation/headless-tmux-driver.md` |
| **`docs/configuration.md`**<br>(668 KB, 7,768 lines) | Covered in Quickstart | `how-to/config/setup-project.md`<br>`how-to/config/configure-profiles.md` | `reference/config-schema.md`<br>`reference/env-vars.md`<br>`reference/feature-flags.md` | `explanation/configuration-hierarchy.md` |
| **`docs/beads.md`**<br>(201 KB, 3,047 lines) | `tutorials/first-epic.md`<br>*(Creating an epic & phase beads)* | `how-to/beads/track-followup-tasks.md`<br>`how-to/beads/sync-external-issues.md`<br>`how-to/beads/triage-discovered-work.md` | `reference/bead-types.md`<br>`reference/bead-status-lifecycle.md`<br>`reference/bead-cli.md` | `explanation/git-native-issue-tracking.md`<br>`explanation/event-log-storage.md` |
| **`docs/llms.md`**<br>(237 KB, 3,582 lines) | Covered in Quickstart | `how-to/providers/authenticate-claude.md`<br>`how-to/providers/setup-antigravity.md`<br>`how-to/providers/configure-custom-models.md` | `reference/models-catalog.md`<br>`reference/size-aliases.md`<br>`reference/provider-tiers.md` | `explanation/provider-abstraction.md`<br>`explanation/effort-ladder-routing.md` |
| **`docs/macros.md`**<br>(244 KB, ~3,400 lines) | `tutorials/first-macro.md` | `how-to/macros/author-workflow-macro.md`<br>`how-to/macros/pass-typed-json-inputs.md` | `reference/macro-directives.md`<br>`reference/macro-builtins.md` | `explanation/macro-compilation-pipeline.md`<br>`explanation/prompt-stash-semantics.md` |
| **`docs/axe.md`**<br>(125 KB, ~1,800 lines) | — | `how-to/daemon/start-service-host.md`<br>`how-to/daemon/schedule-maintenance.md` | `reference/service-cli.md`<br>`reference/daemon-units.md` | `explanation/axe-daemon-architecture.md`<br>`explanation/unsettled-goal-reconciliation.md` |

---

## 3. Plan Critique: Is This a Good Idea?

### 3.1 Unconditional Merits

The core intent—drastically simplifying the documentation and adopting Diátaxis—is **100% sound and overdue**. 

1. **Eliminates Cognitive Friction for Evaluators:** Potential users visiting `sase.sh` currently face a steep wall of text. Deconstructing this into a crisp 15-minute tutorial and focused how-to guides immediately broadens adoption.
2. **Restores Usability for Daily Practitioners:** Experienced SASE developers do not want to read an essay on why beads use event-log storage when looking up `sase bead create -t "..."` flags. Reference pages must be austere, fast, and searchable.
3. **Aligns Documentation with SASE's Engineering Ethos:** SASE is built around strict contracts (e.g., host-owned completion, spec-driven development, typed artifacts). Bringing the same contract-driven rigor to documentation creates structural integrity across code and prose.

### 3.2 Critical Failure Modes & Pitfalls (The Critique)

However, a naive or dogmatic execution of the plan carries serious risks that could leave SASE's documentation worse than before:

```
               POTENTIAL TRAP: DOGMATIC DIATAXIS FRAGMENTATION
               
               User wants to learn about "Beads":
               
               /tutorials/first-bead.md        <--- [Lost context]
               /how-to/beads/create.md         <--- [No theory]
               /reference/beads-cli.md         <--- [Dry table]
               /explanation/beads-storage.md   <--- [Abstract ideas]
               
               Result: "Folder Disorientation" and 4 disjoint tabs!
```

#### Pitfall A: The "Four-Door" Fragmentation Trap (Folder Disorientation)
If an engineer wants to understand and use a major subsystem like **Beads**, forcing them to navigate to four different corners of the site (`/tutorials/`, `/how-to/`, `/reference/`, `/explanation/`) without unified cohesion causes disorientation. When every feature is split into four microscopic files, users lose sight of the subsystem as an integrated whole.

#### Pitfall B: The Hand-Crafted Reference Burden
Writing reference pages by hand in Markdown is a maintenance nightmare. SASE's CLI has hundreds of flags; `default_config.yml` has hundreds of settings; models and size-aliases are updated constantly. If the restructuring merely redistributes hand-written tables into a `/reference/` folder, those tables will rapidly drift and rot.

#### Pitfall C: PDF Handbook Disruption
SASE actively builds and distributes a downloadable, bookmarked PDF handbook (`sase-handbook.pdf`) via `mkdocs-pdf.yml` and `mkdocs-exporter`. Diátaxis organizes content by user need, but an offline handbook requires a coherent, linear reading narrative (Introduction -> Getting Started -> Architectural Concepts -> Operational Guides -> Reference Appendices). If the web restructuring shuffles files without an explicit PDF compilation manifest, the generated PDF will become disjointed and unreadable.

#### Pitfall D: Big-Bang Migration Paralysis
Attempting to rewrite 4.1 MB of documentation all at once will either halt engineering progress or result in massive merge conflicts across active workspaces.

---

## 4. Justified Adjustments to Requirements

To avoid these pitfalls, we recommend four concrete adjustments to the plan:

```
+-----------------------------------------------------------------------------------------+
|                              FOUR JUSTIFIED ADJUSTMENTS                                 |
+-----------------------------------------------------------------------------------------+
| 1. Hub-and-Spoke Architecture: Subsystem Landing Portals with Diataxis Compass Navigation |
| 2. SSOT Code-Generated Reference: Programmatic generation of CLI, Config, and Keymaps   |
| 3. Dual-Manifest Publication: Web IA (Diataxis tabs) decoupled from PDF linear handbook |
| 4. Phased "Pillar-by-Pillar" Migration: Staged rollout preserving legacy redirects       |
+-----------------------------------------------------------------------------------------+
```

### Adjustment 1: The "Hub-and-Spoke / Compass" Navigation Model
Rather than scattering features into disconnected directories, implement **Subsystem Portals** linked by a **Diátaxis Compass**.
- Every major feature (e.g., Beads, Macros, TUI, LLM Providers, Daemon) has a concise landing summary that features a 4-quadrant "Compass Card":
  ```markdown
  ::: diataxis-compass
  - **Tutorial:** [Build your first Phase & Epic (10 min)](/tutorials/beads-first-epic/)
  - **How-To Guides:** [Manage Follow-up Tasks](/how-to/beads/tasks/) · [Sync Issues](/how-to/beads/sync/)
  - **Reference:** [CLI Syntax](/reference/bead-cli/) · [Status Lifecycle](/reference/bead-lifecycle/)
  - **Explanation:** [Git-Native Storage & Rust Core Reduction](/explanation/beads-architecture/)
  :::
  ```
This gives users the freedom to explore according to their current need without losing context of the subsystem.

### Adjustment 2: Automated Single Source of Truth (SSOT) Reference Generation
SASE already has a stellar working pattern in `tools/render_model_docs`, which reads `src/sase/llm_provider/models.yml` and generates the Markdown tables in `docs/llms.md` during `just fix` (`just fmt-docs`).
We must extend this pattern to all Reference documentation:
- `tools/render_cli_docs`: Introspects `sase`'s argparse/Rust CLI trees and emits authoritative CLI reference pages.
- `tools/render_config_docs`: Parses `src/sase/default_config.yml` schema and inline doc-comments to emit `reference/configuration.md`.
- `tools/render_keymap_docs`: Parses the default keymap dictionary to emit `reference/tui-keymaps.md`.
Human authors and agents should **never** manually edit reference tables.

### Adjustment 3: Decoupled PDF Linear Handbook Compilation
Maintain two distinct navigation manifests:
- `mkdocs.yml`: Optimized for web UX, organized by Diátaxis tabs (`Tutorials`, `How-To`, `Reference`, `Explanation`).
- `mkdocs-pdf.yml`: Optimized for linear reading:
  1. *Book 1: Foundations & Quickstart* (Tutorials + Core Explanation)
  2. *Book 2: Operator's Field Guide* (How-To Guides by subsystem)
  3. *Book 3: Architecture & Invariants* (Deep Explanations)
  4. *Book 4: Complete Technical Reference* (Auto-generated Reference appendices)

### Adjustment 4: Phased Pillar-by-Pillar Migration with Automated Redirects
Migrate one high-pain pillar per phase using `mkdocs-redirects`:
- *Pillar 1:* ACE TUI (`ace.md`)
- *Pillar 2:* Configuration & CLI (`configuration.md`, `cli.md`)
- *Pillar 3:* Planning & Beads (`beads.md`, `change_spec.md`, `goals.md`)
- *Pillar 4:* Providers & Macros (`llms.md`, `macros.md`, `agent_providers.md`)

---

## 5. Proposed Information Architecture & UX Redesign for sase.sh

### 5.1 Top-Level Navigation Structure (MkDocs Material Tabs)

By enabling `navigation.tabs` in `mkdocs.yml`, the top bar of `sase.sh` transforms into a clean, intuitive navigation surface:

```
==========================================================================================
 SASE   [Tutorials]   [How-To Guides]   [Reference]   [Explanation]   [Blog]     🔍 Search
==========================================================================================
```

When a user selects a tab, the left sidebar dynamically updates to show only the relevant hierarchy for that mode:

```
TUTORIALS TAB                   HOW-TO GUIDES TAB               REFERENCE TAB
├── Getting Started (15 min)    ├── Project Setup & Auth        ├── CLI Command Index
├── First Multi-Agent Swarm     ├── Daily TUI Driving           ├── Configuration Schema
├── First Spec & Plan           ├── Git & VCS Stitches          ├── Models & Tier Catalog
├── First Custom Macro          ├── Beads & Task Triage         ├── TUI Keybinding Matrix
└── Remote Machine Dispatch     ├── Daemon & Automation         ├── Macro Syntax Grammar
                                └── Troubleshooting Runbooks    └── Query Language Spec
```

### 5.2 Homepage (`sase.sh`) Redesign: The 3-Persona Triage

Replace the confusing 17-card grid on `docs/index.md` with a clean, focused triage interface:

```
+---------------------------------------------------------------------------------------+
|                                         SASE                                          |
|                     Structured Agentic Software Engineering                           |
|                                                                                       |
|   Coordinate coding agents through durable plans, reviewable handoffs, and            |
|   resumable runs across Claude Code, Codex, Antigravity, and local models.            |
|                                                                                       |
|         [ ⚡ Start 15-Minute Tutorial ]         [ 📖 Browse How-To Guides ]           |
+---------------------------------------------------------------------------------------+

       CHOOSE YOUR PATHWAY

   ┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
   │     🌱 New to SASE     │  │   🛠️ Daily Operator    │  │   📐 Systems Architect │
   │                        │  │                        │  │                        │
   │ Follow the hands-on    │  │ Step-by-step recipes   │  │ Deep dives into single-│
   │ tutorial to install    │  │ for git stitches, TUI  │  │ turn agent contracts,  │
   │ SASE and run a safe    │  │ driving, beads triage, │  │ host completion, and   │
   │ first agent in 15 min. │  │ and remote dispatch.   │  │ the Rust core engine.  │
   │                        │  │                        │  │                        │
   │ [Start Tutorial →]     │  │ [Browse Recipes →]     │  │ [Read Concepts →]      │
   └────────────────────────┘  └────────────────────────┘  └────────────────────────┘

+---------------------------------------------------------------------------------------+
|  QUICK SEARCH CHEATSHEETS:                                                           |
|  [ ⌨️ TUI Keymaps ]   [ ⚙️ Config Options ]   [ 💻 CLI Flags ]   [ 🤖 Model Catalog ]  |
+---------------------------------------------------------------------------------------+
```

### 5.3 Page-Level UX Enhancements

1. **Diátaxis Quadrant Badges:**  
   Every documentation page renders a subtle chip immediately beneath the title:
   - `🏷️ TUTORIAL` (Green)
   - `🏷️ HOW-TO GUIDE` (Blue)
   - `🏷️ REFERENCE` (Orange)
   - `🏷️ EXPLANATION` (Purple)  
   This immediately sets expectations for the reader regarding tone, scope, and purpose.

2. **Interactive TUI Keybinding Cheatsheet:**  
   Instead of a static 5,000-line Markdown table for ACE TUI keys, provide an interactive, filterable keymap table (using standard MkDocs JavaScript/CSS) allowing users to filter by modal context (Leader mode, Navigation mode, Agent Inspection mode).

3. **Tabbed Multi-Provider Code Snippets:**  
   Standardize all operational commands using MkDocs `pymdownx.superfences` tabbed blocks so users instantly view commands tailored to their installed CLI:
   === "Claude Code"
       ```bash
       sase run -m claude-3-5-sonnet "+home summarize repo"
       ```
   === "Codex CLI"
       ```bash
       sase run -m codex "+home summarize repo"
       ```
   === "Antigravity CLI"
       ```bash
       sase run -m agy "+home summarize repo"
       ```

---

## 6. Structuring the Documentation Process & Governance

To maintain documentation quality over time, SASE must transition from ad-hoc Markdown editing to a structured, enforceable documentation pipeline.

### 6.1 Archetype Page Templates

Under `docs/templates/` (or repository templates), establish strict structural schemas for each quadrant:

#### A. How-To Guide Template (`templates/docs/howto.md`)
```markdown
---
title: "How to <Accomplish Specific Goal>"
description: "Brief 1-sentence summary of the task."
type: howto
subsystem: <beads | tui | macros | providers | daemon>
---

# How to <Accomplish Specific Goal>

Brief context explaining what this guide achieves and when to use it.

## Prerequisites
- SASE installed and authenticated (`sase doctor` passes)
- Required plugins or permissions (e.g., `gh auth` or remote enrollment)

## Step 1: <First Direct Action>
Command and expected output.

## Step 2: <Second Direct Action>
Configuration snippet or command.

## Verification
How to verify the action succeeded (e.g., running `sase check` or inspecting status).

## Related
- Reference: [Link to relevant flag/schema spec]
- Explanation: [Link to background design concept]
```

#### B. Reference Template (`templates/docs/reference.md`)
```markdown
---
title: "<Subsystem> Reference"
description: "Authoritative specifications and options."
type: reference
subsystem: <subsystem>
generated: true # Set to true if emitted by SSOT tool
---

# <Subsystem> Reference

<!-- Dry, structured specification tables. No tutorial narrative. -->

## Options / Grammar / Flags
| Name | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| ...  | ...  | ...     | ...         |
```

### 6.2 CI Quality Gates (`just docs-lint` & `just docs-check`)

Incorporate documentation linting directly into `Justfile`:

```bash
# Add to Justfile:
docs-lint: _venv
    {{ venv_bin }}/python tools/lint_docs_diataxis
    {{ venv_bin }}/python tools/check_docs_links
```

The linter `tools/lint_docs_diataxis` enforces three invariants:
1. **Frontmatter Validation:** Every page in `docs/` must declare `type: tutorial | howto | reference | explanation | blog`.
2. **Line Budget Limits:**
   - Warning emitted if any document exceeds **1,500 lines**.
   - Build error if any document exceeds **2,500 lines** (exempting auto-generated reference tables).
   This permanently prevents the recurrence of 9,000-line monolithic files.
3. **SSOT Sync Check:** Verifies that all auto-generated reference pages (`cli.md`, `configuration.md`, `tui-keymaps.md`, `models-catalog.md`) match the current source code and YAML manifests.

---

## 7. Long-Term Agentic Documentation Management (SASE Agents)

While human-facing usability is the primary focus of this report, structuring documentation according to Diátaxis provides extraordinary leverage for **long-term agentic management** using SASE coding agents.

### 7.1 Why Diátaxis is Ideally Suited for LLM Coding Agents

1. **Context Window Efficiency & Focus:**  
   When an agent is tasked with adding a new feature or documenting a change, feeding it a 740 KB monolithic file causes severe prompt dilution, token waste, and hallucination. In contrast, feeding the agent a 200-line How-To guide or an isolated 150-line Explanation doc allows the model to concentrate fully on the specific edit.
2. **Unambiguous Authoring Contracts:**  
   LLMs naturally tend to mix explanations into reference tables or bloat tutorials with edge cases. By giving an agent a strict Diátaxis template:
   - *"You are writing a How-To guide. Do not explain the underlying storage engine. Only write prerequisites, action steps, and verification."*
   The resulting output is crisp, clean, and conformant.
3. **Clear Boundary: Agent Memory vs. Public Documentation:**  
   A critical confusion in SASE has been the overlap between `sase/memory/` and `docs/`:
   - `sase/memory/`: **Internal agent memory.** High-density, concise operational instructions and invariants for coding agents operating in ephemeral workspaces.
   - `docs/`: **Public developer documentation.** Polished, user-centric guides, tutorials, and references for human software engineers using SASE.
   SASE agents can read public docs when needed, but their primary durable instructions stay in `sase/memory/`. Agents can be tasked with auditing and updating public docs whenever code changes.

### 7.2 Proposed Agentic Documentation Skills

In the future, SASE can introduce dedicated macro skills for agentic docs maintenance:
- `/sase_doc_audit`: A research agent scans recently merged patches or PRs and flags any CLI flag, config key, or workflow change lacking documentation coverage.
- `/sase_doc_howto`: Scaffolds a new how-to guide conforming to `templates/docs/howto.md` based on an accepted plan or feature bead.

---

## 8. Recommended Solution & Phased Implementation Roadmap

### 8.1 Target Directory Structure

```
docs/
├── index.md                        # Redesigned 3-pathway triage landing page
├── tutorials/                      # [TUTORIALS TAB]
│   ├── index.md                    # Learning pathway overview
│   ├── getting-started.md          # 15-Minute Zero-to-One Quickstart
│   ├── parallel-swarms.md          # Running multi-agent parallel workflows
│   └── spec-driven-dev.md          # Working with Plans, Epics, and Beads
├── how-to/                         # [HOW-TO GUIDES TAB]
│   ├── index.md                    # Categorized recipe index
│   ├── setup/                      # Repo init, auth, plugins, environment
│   ├── tui/                        # Navigating ACE, panes, snapshots, revival
│   ├── planning/                   # Authoring plans, triage, follow-up tasks
│   ├── macros/                     # Writing workflows, typed JSON arguments
│   ├── providers/                  # Claude Code, Codex, Antigravity, local
│   ├── remote/                     # Tailscale dispatch, daemon service host
│   └── troubleshooting/            # OOM revival, runner slot waits, doctor
├── reference/                      # [REFERENCE TAB - SSOT Auto-Generated]
│   ├── index.md                    # Reference hub & cheatsheets
│   ├── cli.md                      # Auto-generated CLI command & flag index
│   ├── configuration.md            # Auto-generated schema from default_config.yml
│   ├── tui-keymaps.md              # Auto-generated keybinding matrix
│   ├── models-catalog.md           # Auto-generated from models.yml
│   ├── macro-directives.md         # @ and % grammar specification
│   └── query-language.md           # Agent Boolean query dialect
├── explanation/                    # [EXPLANATION TAB]
│   ├── index.md                    # Conceptual architecture index
│   ├── single-turn-agents.md       # Philosophy of single-turn vs chat loops
│   ├── host-owned-completion.md    # Host finalization & commit invariants
│   ├── git-native-beads.md         # Event-log issue storage & reduction
│   ├── goal-ledger.md              # Why Goals are distinct from Beads
│   ├── rust-backend-boundary.md    # SASE Core architecture & bindings
│   └── memory-webs.md              # Agent durable context & strand addressing
├── blog/                           # [BLOG TAB]
│   └── ...                         # Launch essays & release notes
└── overrides/                      # Material theme overrides
```

### 8.2 Four-Phase Migration Roadmap

```
  PHASE 1: Foundations & Tooling
  ├── Configure navigation.tabs & navigation.indexes in mkdocs.yml
  ├── Build SSOT reference generators (tools/render_config_docs, etc.)
  ├── Implement tools/lint_docs_diataxis with line budgets & frontmatter rules
  └── Redesign homepage (docs/index.md) to 3-persona triage layout
       │
       ▼
  PHASE 2: The Core Reference Extraction
  ├── Decompose docs/configuration.md into auto-generated reference + how-to
  ├── Decompose docs/cli.md into auto-generated command reference
  ├── Generate reference/tui-keymaps.md from src/sase/default_config.yml
  └── Set up mkdocs-redirects for legacy URLs
       │
       ▼
  PHASE 3: The Great Monolith Deconstruction
  ├── Deconstruct docs/ace.md (9,771 lines) into TUI Tutorial, How-Tos, Keymap Ref, & Architecture
  ├── Deconstruct docs/beads.md (3,047 lines) into First-Epic Tutorial, Triage How-Tos, & Event-Log Explanation
  ├── Deconstruct docs/macros.md and docs/axe.md
  └── Verify no document exceeds 1,500 lines
       │
       ▼
  PHASE 4: Verification, PDF Realignment & Polish
  ├── Update mkdocs-pdf.yml to compile linear 4-book handbook
  ├── Run full CI check (just docs-check && just docs-pdf-check)
  └── Audit external links, blog references, and search relevance
```

### 8.3 Summary Table of Strategic Recommendations

| Dimension | Current State | Proposed Diátaxis Solution | Strategic Benefit |
| :--- | :--- | :--- | :--- |
| **Information Architecture** | Arbitrary tiers (*"Basics"*, *"Nitty Gritty"*) | 4 Diátaxis Quadrants + Subsystem Hubs | Users immediately find what matches their cognitive need. |
| **Site Navigation** | Single 50-item left sidebar tree | MkDocs Material Top Tabs (`navigation.tabs`) | Eliminates sidebar clutter; scopes context dynamically. |
| **Page Granularity** | 9,000+ line kitchen sinks (`ace.md`) | Bounded pages (<1,500 lines) with single purpose | High search accuracy, fast page loads, readable. |
| **Reference Maintenance** | Hand-crafted Markdown tables | SSOT Code-generated from schemas & code | Zero maintenance drift; guaranteed correctness. |
| **Homepage UX** | 17 competing cards; choice paralysis | 3 clear persona pathways + Quick Cheatsheets | Clear golden path for new users and daily drivers. |
| **Agentic Governance** | Uncontrolled document bloat | Strict archetype templates + CI line budgets | LLM agents can maintain docs without drift or bloat. |

---

## Conclusion & Recommendation

The transition to a Diátaxis-inspired documentation architecture on `sase.sh` is an exceptional initiative that will immediately demystify SASE for newcomers and increase efficiency for veteran practitioners.

By avoiding the pitfall of pure, unguided fragmentation through **Subsystem Portals with Compass Cross-linking**, and by solving the reference maintenance burden through **SSOT code generation**, SASE can elevate its public documentation to match the stellar engineering quality of its underlying platform.

The recommended next step is for project leadership to approve the four justified adjustments and authorize **Phase 1 (Tooling & Navigation Infrastructure)** as a dedicated SASE planning bead.
