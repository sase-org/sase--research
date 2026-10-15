# Docs as Memory: Architecture Critique, Knowledge Tiering, and Agent-Scriptable Documentation Structure

**Date:** 2026-10-15  
**sase checkout:** `c2c2ffd4df`  
**Researcher:** `research.1f.gem` (Swarm Member)  
**Topic:** Evaluating the migration of SASE memory notes to `docs/`, treating project documentation as a first-class memory representation, and restructuring documentation for agent maintenance and scriptability.

---

## 1. Executive Summary & Bottom Line

### 1.1 The Core Questions
The proposal under evaluation puts forward three interrelated ideas:
1. **Migrating memories to `docs/`:** Moving existing SASE memory notes (such as `sase/memory/macros.md`) into documentation files under `docs/` to eliminate dual maintenance.
2. **Docs as first-class memory:** Treating project documentation as a first-class representation of memory, managed with similar governance, auditability, and lifecycle tooling.
3. **Agent-scriptable documentation:** Restructuring `docs/` so that its maintenance by autonomous coding agents is intuitive, robust, and programmatic.

### 1.2 Bottom-Line Assessment
- **Is migrating memories into `docs/` a good idea?**  
  **No, if executed as a literal merger or replacement.** The instinct to eliminate duplicate maintenance between `sase/memory/macros.md` and `docs/macros.md` is valid, but merging them into the same file conflates two fundamentally different audiences with opposing constraints:
  - *Human documentation* (`docs/`) is pedagogical, discursive, illustrated, and narrative. `docs/macros.md` spans **4,082 lines (243.8 KB, ~60,000 tokens)**.
  - *Agent reference memory* (`sase/memory/`) is an operational constraint layer: dense, imperative, telegraphic, and strictly token-budgeted. `sase/memory/macros.md` spans **167 lines (14.7 KB, ~3,700 tokens)**.  
  Directly pointing agents to `docs/macros.md` would inflict severe context bloat (a 16x token explosion per read), dilute prompt attention, and trigger agent hallucinations. Conversely, stripping `docs/macros.md` down to a telegraphic cheat-sheet destroys the user-facing documentation on `https://sase.sh/`.
- **Is making project documentation a first-class representation of memory a good idea?**  
  **Yes, but as a parallel knowledge tier with shared governance, not as prompt-inlined memory.** Documentation should adopt SASE Memory's best properties—YAML frontmatter schemas, audited reads (`sase doc read -r "<why>"`), git blob OID tracking, and cross-reference validation—without dumping 90 documentation files (4.4 MB, ~1.1M tokens) into the prompt compilation pipeline or `sase memory list`.
- **Is structuring documentation for agent scriptability a good idea?**  
  **Yes, this is the highest-leverage and most urgently needed reform.** The primary obstacle to agent-maintained documentation in SASE today is the prevalence of **monolithic giant files**:
  - `docs/ace.md`: 739.7 KB (~185,000 tokens)
  - `docs/configuration.md`: 667.8 KB (~167,000 tokens)
  - `docs/macros.md`: 243.8 KB (~61,000 tokens)
  - `docs/llms.md`: 237.3 KB (~59,000 tokens)
  - `docs/cli.md`: 210.6 KB (~53,000 tokens)
  - `docs/beads.md`: 201.4 KB (~50,000 tokens)  
  Editing a 740 KB file with agent tools (`replace_file_content`, line patching) is fragile, token-expensive, and prone to whitespace drift and context truncation. De-monolithizing these documents into modular topic subtrees (<400 lines per file) following the Diátaxis framework, combined with **code-driven single-source generation** (extending the proven `tools/render_model_docs` pattern to CLI options, configuration schemas, and macro directives), completely solves the maintenance burden and prevents drift.

---

## 2. Current State: Two Disjoint Knowledge Systems

A quantitative and architectural comparison of the repository's two knowledge systems reveals the stark divergence between their purposes and characteristics:

| Metric / Attribute | SASE Memory (`sase/memory/`) | SASE Documentation (`docs/`) |
| :--- | :--- | :--- |
| **Primary Audience** | Autonomous LLM Agents | Human Developers, Operators, Users |
| **Total Markdown Files** | 122 files (including webs & strands) | 90 files |
| **Total Lines** | 4,225 lines | 65,178 lines |
| **Total Raw Bytes** | 213,390 bytes (~0.20 MB) | 4,435,748 bytes (~4.23 MB) |
| **Estimated Token Volume** | ~53,000 tokens (entire corpus) | ~1,100,000 tokens |
| **Preloaded Context Size** | 381 lines (~5,750 tokens) inlined | 0 tokens (never inlined) |
| **Average File Size** | ~35 lines (~1.7 KB) | ~724 lines (~49.3 KB) |
| **Maximum File Size** | 167 lines / 14.8 KB (`macros.md`) | 20,000+ lines / 739.7 KB (`ace.md`) |
| **Governance & Validation** | Strict YAML frontmatter, 11-rule validator, `sase doctor`, `sase memory init` | MkDocs strict build (syntax/links only); no frontmatter schema |
| **Access Tracking** | Audited via `sase memory read` with agent ID, reason, cwd, git blob OIDs | Unaudited; raw filesystem reads (`view_file`, `cat`) |
| **UI Integration** | ACE TUI Memory panel, pager time band, history diffs (`sase memory history`) | Rendered static HTML site (`mkdocs.yml`, Material for MkDocs) |

### 2.1 The Case Study of `macros.md`
The prompt specifically highlights `sase/memory/macros.md`. Examining both files shows why the user feels tension:

```
sase/memory/macros.md :  167 lines  |   14,776 bytes |  ~3,700 tokens
docs/macros.md        : 4,082 lines |  243,807 bytes | ~61,000 tokens
```

- **What `sase/memory/macros.md` contains:**
  1. *Invoke syntax*: Shorthands (`#name:arg`, `#name:: text`), quoting rules, delimiter semantics, memory inclusion rules (`#memory/<stem>`).
  2. *Directives table*: A compact 17-row reference table summarizing `%model`, `%effort`, `%id`, `%clan`, `%wait`, `%queue`, `%hold`, `%proc`, `%dispatch`, `%tab`, `%final`, `%repeat`, `%auto`, `%hide`, and `%{a|b}`.
  3. *Definition syntax*: Frontmatter fields for `.md` and `.yml` workflows; first-wins discovery order.
  4. *Project-task launch contracts*: `#gh:`, `#git:`, `#commit`, `#propose`, `#pr:`, and the non-negotiable rule: *"Agents never create git commits, branches, or PRs directly. Host-owned finalizers run after the model returns. Finish with `/sase_final`..."*
- **What `docs/macros.md` contains:**
  1. A multi-page conceptual guide explaining why macros exist, why xprompts were renamed, an ASCII resolution diagram, and an infographic prompt.
  2. Exhaustive CLI subcommands (`sase macro expand`, `explain`, `list`, `show`, `graph`) with sample inputs, full terminal outputs, and error handling.
  3. Multi-page prose sections for *every single directive*, detailing parameter types, admission gate semantics, queue multiplier mathematics, hold scopes, and execution diagrams.
  4. Complete YAML workflow schemas, step-by-step authoring tutorials, and advanced pattern catalogs.

Both documents discuss identical syntax and directives, but their **density, tone, and operational focus** are completely different.

---

## 3. Critique of the Proposed Direction

### 3.1 Critique 1: Migrating Memories Directly to `docs/`
The desire to delete `sase/memory/macros.md` and tell agents to "just read `docs/macros.md`" encounters several fatal failure modes:

1. **The Token Budget Disaster (Context Window Saturation)**  
   SASE agent execution is built around single-turn economics and strict token budgeting (`docs/instruction_bundles.md`, `decisions:instructions-per-invocation`). Preloaded core memory is intentionally capped at ~5,750 tokens across the entire project. When an agent running a task needs to look up macro directive syntax, reading `sase/memory/macros.md` costs **3,700 tokens**. Reading `docs/macros.md` costs **61,000 tokens**—consuming 30% to 60% of an agent's effective working context window before any codebase files are read.
2. **Context Dilution and Attention Degradation**  
   LLMs suffer performance degradation ("lost in the middle") when relevant operational constraints are buried in tens of thousands of tokens of explanatory narrative, troubleshooting notes, and historical context. When an agent only needs to know the exact regex syntax of `#name:arg` or whether `%hold` accepts `@tribe`, skimming 4,000 lines of prose dramatically increases hallucination rates.
3. **Loss of Agent Imperatives and Invariant Guardrails**  
   `sase/memory/macros.md` ends with a critical, unambiguous imperative:
   > *"Rule: Agents never create git commits, branches, or PRs directly. Host-owned finalizers run after the model returns. Finish with `/sase_final`..."*  
   In a human-facing documentation manual, this operational constraint is out of place or softened into descriptive architecture. If agents read user documentation instead of memory, critical behavioral guardrails are lost.
4. **Violation of Architectural Decision: `decisions:corpus-before-mechanism`**  
   SASE's architectural record explicitly documents that speculative retrieval mechanisms (such as keyword-triggered dynamic memory and episode-recall layers) were built and subsequently deleted because adding complex machinery ahead of concrete need introduced maintenance drag. Replacing compact memory files with an ad-hoc doc retrieval layer would repeat this exact mistake.

### 3.2 Critique 2: Making Project Documentation a "First-Class Representation of Memory"
The viability of this idea depends entirely on how "first class" is defined:

- **The Flawed Interpretation (Flattening Docs into Memory):**  
  Treating `docs/*.md` as memory notes subject to `sase memory list` or prompt inlining would be catastrophic. Loading 90 files and 1.1 million tokens into memory management would render `sase memory list` unusable, swamp the ACE TUI Memory panel, and obscure the critical distinction between prompt context and reference materials.
- **The Sound Interpretation (Extending Memory Governance to Docs):**  
  Where documentation *should* become first-class is in its **tooling, auditability, and validation**:
  - *Audited Reads*: Currently, agents read docs via unmonitored filesystem tools (`view_file`, `cat`). Adding an audited command (`sase doc read <topic> [--section <name>] -r "<why>"`) ensures documentation access is tracked in the agent's audit log, attributing reads to tasks and measuring doc relevance.
  - *Metadata & Schema Validation*: Enforcing lightweight YAML frontmatter in docs (defining title, domain, doc type, and associated code paths) enables automated verification.
  - *Drift Detection*: Adding CI checks that verify documentation matches the underlying code (CLI parsers, config schemas, and macro directives).

### 3.3 Critique 3: Structuring Documentation for Agent Scriptability
The user's observation that documentation maintenance is currently not intuitive or scriptable via agents is completely accurate. The root causes in SASE's current tree are:

1. **Monolithic File Architecture**  
   As documented in Section 2, files like `docs/ace.md` (740 KB) and `docs/configuration.md` (668 KB) are too large for standard agent tool calls. In Antigravity and Claude CLI harnesses, tool output limits (typically 30–50 KB per call) require agents to paginate through files using byte offsets. Making surgical edits using string replacement tools (`replace_file_content`) on a 20,000-line file frequently fails due to non-unique matches, minor whitespace differences, or line-number drifting.
2. **Lack of Machine-Readable Topic Boundaries**  
   Sections within `docs/macros.md` or `docs/cli.md` transition between high-level concepts, detailed parameter tables, and troubleshooting without consistent structural delimiters or semantic anchors.
3. **Manual Synchronization Overhead**  
   When a developer or agent adds a feature (such as a new flag, macro directive, or config key), there is no programmatic contract connecting the implementation file (e.g., `src/sase/macro/_directive_types.py`) to the documentation (`docs/macros.md`) or the memory note (`sase/memory/macros.md`). Maintenance relies entirely on human memory.

---

## 4. Architectural Alternatives & Evaluation

To evaluate how best to resolve these tensions, four alternative architectures were analyzed:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                ARCHITECTURAL OPTIONS                                   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Option A: Naive Unification                                                            │
│   Delete sase/memory/macros.md -> Agents read docs/macros.md directly                  │
│   ❌ Context bloat (60k tokens)  ❌ Diluted rules  ❌ High failure rate                │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Option B: Tag-Filtered Extraction (Dual-Audience Single-Source)                        │
│   Author docs with <agent-only> or <summary> tags -> compiler extracts memory         │
│   ⚠️ Awkward prose compromise  ⚠️ Fragile custom parser  ⚠️ High authoring friction   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Option C: Code-Driven Single-Source Generation (The `render_model_docs` Pattern)       │
│   Code/Manifests define data -> Tools generate both docs blocks and memory tables      │
│   ✅ 100% drift-free  ✅ Fast CI verification  ✅ Proven pattern in SASE tree         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Option D: Tiered Knowledge Architecture with Shared Governance (RECOMMENDED)           │
│   Tier 1: Core Memory (Inlined) | Tier 2: Agent Ref Memory | Tier 3: Modular Docs       │
│   ✅ Optimal token budgets  ✅ Modular files (<400 lines)  ✅ Audited sase doc read    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Option A: Naive Unification (Direct File Merger)
- **Mechanism:** Delete `sase/memory/macros.md`. Add `docs/macros.md` to `## Reference Memory` in `AGENTS.md`. Agents call `sase memory read docs/macros.md`.
- **Verdict:** **Rejected.** Fatal token explosion (60,000 tokens vs 3,700 tokens), context pollution, and loss of tight operational constraints.

### Option B: Tag-Filtered Extraction (Dual-Audience Single-Source)
- **Mechanism:** Keep documentation in `docs/macros.md`, but annotate specific blocks with custom markers (e.g., `<!-- BEGIN AGENT REFERENCE -->` or `<div class="agent-memory">`). `sase memory init` extracts these blocks into `sase/memory/macros.md`.
- **Verdict:** **Rejected.** While it achieves a single file on disk, authoring human-friendly documentation that cleanly doubles as an agent operational cheat-sheet creates unnatural, contorted writing. MkDocs rendering of agent directives can be awkward, and custom extraction parsers add brittle document-layer machinery.

### Option C: Code-Driven Single-Source Generation
- **Mechanism:** Treat code definitions and structured manifests as the single source of truth. SASE already demonstrates this successfully in `tools/render_model_docs`:
  - `src/sase/llm_provider/models.yml` is the canonical manifest.
  - `tools/render_model_docs` renders `<!-- BEGIN GENERATED -->` blocks in `docs/llms.md`.
  - `just fmt-docs-check` verifies zero drift in CI.
  This model can be extended to macro directives, CLI commands, and configuration keys:
  - Macro directives are defined in a structured Python/YAML registry (e.g., `src/sase/macro/registry.py` or dataclasses in `_directive_types.py`).
  - A generator script renders both:
    1. The detailed directive tables and documentation in `docs/macros/directives/`.
    2. The compact, high-density reference table in `sase/memory/macros.md`.
- **Verdict:** **Adopt as a Core Mechanism.** Eliminates manual synchronization without compromising document structure.

### Option D: Tiered Knowledge Architecture with Shared Governance (The Comprehensive Solution)
- **Mechanism:** Formalize a three-tiered knowledge hierarchy that distinguishes Core Memory, Reference Memory, and Project Documentation, while unifying their governance, auditability, and modularity.
- **Verdict:** **Recommended Solution.** Addresses all three parts of the user request cleanly, sustainably, and safely.

---

## 5. Recommended Architecture: The Tiered Knowledge System

### 5.1 The Three-Tier Knowledge Hierarchy

```
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 1: CORE PROMPT MEMORY (`sase/memory/*.md`, type: core)                           │
│ - Audience: Root agents during prompt assembly                                        │
│ - Scope: Workspace invariants, linked repos, /sase_final contract, key gotchas        │
│ - Delivery: Inlined into AGENTS.md and explicit provider bundles                      │
│ - Budget: Hard cap <6,000 tokens total (Current: ~5,750 tokens)                       │
├───────────────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: AGENT REFERENCE MEMORY (`sase/memory/*.md`, type: reference & webs)          │
│ - Audience: Active agents executing specialized tasks                                 │
│ - Scope: Dense operational cheat-sheets, task schemas, ADRs, glossary strands         │
│ - Delivery: On-demand, audited via `sase memory read <selector> -r "<why>"`           │
│ - Budget: 500 – 3,500 tokens per note/strand (Current: ~3,700 tokens for macros.md)   │
├───────────────────────────────────────────────────────────────────────────────────────┤
│ TIER 3: MODULAR PROJECT DOCUMENTATION (`docs/**/*.md`)                                │
│ - Audience: Humans (reading sase.sh) & Agents (performing deep research/refactors)    │
│ - Scope: Conceptual guides, tutorials, architectural runbooks, full API references    │
│ - Delivery: Human web browsing & Audited agent access via `sase doc read`             │
│ - Budget: Unconstrained globally; section-capped (<2,500 tokens) per agent read       │
│ - Structure: De-monolithized into modular topic trees (<400 lines per file)           │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Adjusted Requirements
To make project documentation a first-class citizen and ensure it is easily scriptable and maintainable by agents, the following adjustments to the user's initial requirements are recommended:

1. **Do not delete `sase/memory/macros.md`; automate its synchronization.**  
   Preserve `sase/memory/macros.md` as Tier 2 Reference Memory. Use code-driven generation or CI drift checking to guarantee that it never diverges from `docs/macros/` or `src/sase/macro/`.
2. **De-monolithize `docs/` into topic-oriented directories (<400 lines per file).**  
   Decompose monolithic markdown files (`docs/macros.md`, `docs/configuration.md`, `docs/cli.md`, `docs/ace.md`) into modular directory trees. Small files allow agents to view and edit individual pages cleanly with single tool invocations.
3. **Standardize frontmatter across `docs/`.**  
   Require structured YAML frontmatter on all documentation files, establishing metadata that agents can inspect before reading full text.
4. **Introduce the `sase doc` CLI for audited, section-aware agent documentation reads.**  
   Give agents a dedicated tool to query and read documentation with attribution and bounded token usage.
5. **Establish Single-Source Code Generation for Reference Data.**  
   Auto-generate CLI reference tables, configuration reference tables, and macro directive references from code/schema definitions.

---

## 6. Implementation Blueprint

### 6.1 Documentation Modularization (The Diátaxis Layout)
Break down the massive monolithic files in `docs/` into structured directories:

#### Case Study: Restructuring `docs/macros.md` (4,082 lines -> Modular Tree)
Replace the single 244 KB file with a clean directory `docs/macros/`:
```text
docs/macros/
├── index.md                 # Overview, mental model, infographic (~250 lines)
├── syntax.md                # Invocation rules, shorthands, quoting, delimiters (~300 lines)
├── directives/              # Granular cards for each directive (~100-250 lines each)
│   ├── model.md             # %model and %effort
│   ├── queue.md             # %queue, capacity multipliers, priority, weight
│   ├── hold.md              # %hold admission barrier, selectors, TTL
│   ├── wait.md              # %wait dependencies and time floors
│   ├── proc.md              # %proc stand-alone process units
│   ├── final.md             # %final finalizer operations
│   └── dispatch.md          # %dispatch remote execution
├── workflows.md             # YAML workflow step specifications (~350 lines)
├── swarms.md                # Fan-out swarms (---) and segmenting (~200 lines)
├── vcs.md                   # Project tags, patch refs, rollover macros (#commit, #pr) (~300 lines)
└── cli.md                   # CLI tools (expand, explain, list, show, graph) (~350 lines)
```

#### Case Study: Restructuring `docs/configuration.md` (668 KB) and `docs/cli.md` (211 KB)
- `docs/configuration/`
  - `index.md`: Discovery hierarchy, configuration files, precedence.
  - `keys/`: Grouped by domain (`agents.md`, `beads.md`, `memory.md`, `providers.md`, `vcs.md`).
- `docs/cli/`
  - `index.md`: Global flags, output formats (`--format json|rich|table`), exit codes.
  - `commands/`: Individual subcommand groups (`agent.md`, `artifact.md`, `bead.md`, `memory.md`, `tool.md`).

*MkDocs Impact:* Using MkDocs Material's `navigation.indexes` feature, each folder's `index.md` seamlessly acts as the section landing page. MkDocs redirects (`mkdocs-redirects`) preserve URL backwards compatibility for existing links (e.g., `docs/macros.md` redirects to `docs/macros/index.md`).

### 6.2 Standardized Documentation Frontmatter Schema
Require all documentation files under `docs/` to declare structured metadata:

```yaml
---
title: Prompt Directives: %queue and Admission Gates
description: Configuring agent runner capacity, multipliers, priority, and weight with %queue.
doc_type: reference          # tutorial | howto | reference | explanation
domain: macro
related_code:
  - src/sase/macro/_directive_types.py
  - src/sase/macro/_directive_extract.py
related_memory:
  - macros.md
status: active               # active | experimental | deprecated
---
```

**Benefits for Agent Scriptability:**
- When an agent is tasked with modifying a feature, it can scan frontmatter `related_code` to immediately locate all documentation files covering that code.
- Linters can assert that every `.py` file in a critical subsystem has at least one associated `doc_type: reference` document.

### 6.3 First-Class Tooling: The `sase doc` CLI
Introduce a dedicated CLI tool and skill for documentation management:

```bash
# List documentation topics with metadata and sizes
sase doc list [--domain macro] [--type reference]

# Audited read of a documentation topic (records agent, reason, and git blob OID)
sase doc read macros/directives/queue -r "Need %queue multiplier syntax for runner admission"

# Audited read of a specific heading/section (caps returned tokens)
sase doc read macros/syntax --section "Line Shorthands" -r "Checking double colon syntax"

# Validate documentation frontmatter, cross-links, and generated block parity
sase doc check
```

**Implementation Details:**
- **Audit Logging:** Reuses `sase.memory.read_log` models (`_read_log_models.py`). Document reads are logged alongside memory reads in `agent_meta.json` and project state, with blob OIDs capturing the exact version read.
- **Token Protection:** Enforces a default cap (e.g., 2,500 tokens) per read. If a requested section exceeds the cap, it returns a section outline and requires the agent to specify a sub-heading.
- **Skill Definition:** A thin skill `sase_doc_read` is generated for agent environments, giving agents explicit, audited access to Tier 3 documentation.

### 6.4 Single-Source Codegen for Directives, CLI, and Config
To eliminate drift without forcing human docs and agent memory to share prose:

1. **Centralize Macro Directives Registry:**
   Move directive definitions into a structured registry (extending `src/sase/macro/_directive_types.py` with parameter schemas and short summaries).
2. **Implement `tools/render_macro_docs`:**
   A script that parses the registry and generates:
   - `docs/macros/directives/*.md` reference tables.
   - The markdown table in `sase/memory/macros.md` between `<!-- BEGIN GENERATED: DIRECTIVES -->` and `<!-- END GENERATED: DIRECTIVES -->` markers.
3. **Continuous Enforcement via `just check`:**
   Add `just fmt-docs-check` rules that fail if generated blocks in `docs/` or `sase/memory/` are out of sync with code definitions.

---

## 7. Migration Roadmap

The implementation can be executed across four distinct, low-risk phases:

### Phase 1: Documentation Decomposition & Frontmatter Standard (Non-Breaking)
1. Split `docs/macros.md` into `docs/macros/` directory (preserving existing URLs via `mkdocs-redirects`).
2. Add YAML frontmatter schema to all files in `docs/macros/`.
3. Split `docs/configuration.md` and `docs/cli.md` into modular subdirectories.
4. Verify `mkdocs build --strict` passes in CI.

### Phase 2: Single-Source Reference Codegen (Drift Elimination)
1. Standardize the directive definitions registry in `src/sase/macro/_directive_types.py`.
2. Implement `tools/render_macro_docs` to update `docs/macros/` and `sase/memory/macros.md`.
3. Add `tools/render_cli_docs` to generate CLI tables from `argparse` parsers.
4. Integrate `fmt-docs-check` into the standard `just check` pipeline.

### Phase 3: First-Class `sase doc` Tooling & Agent Skill
1. Implement `sase doc list` and `sase doc read` CLI commands in `src/sase/doc/`.
2. Connect `sase doc read` to the existing audited read-log infrastructure (`sase.memory.read_log`).
3. Generate the `sase_doc_read` skill and deploy to managed agent environments.

### Phase 4: Cross-Linking & Memory Review
1. Author bidirectional links between `sase/memory/` and `docs/` using `[[doc:<path>]]` syntax.
2. Review remaining reference memory notes (`cli_rules.md`, `dispatch.md`, `sase_artifacts.md`, `sase_beads.md`) to ensure they serve purely as high-density agent operational guides, linking to their companion docs under `docs/`.

---

## 8. Summary of Recommendations for Bryan

1. **Reject the literal migration of `sase/memory/macros.md` into `docs/macros.md`.**  
   Keep `sase/memory/macros.md` as a concise (~3.7k token) agent operational cheat-sheet. Dumping 60k tokens of documentation into the agent context will hurt latency, token costs, and instruction adherence.
2. **Solve the duplicate maintenance problem at the source via codegen.**  
   Generate the directives reference tables in both `docs/macros/` and `sase/memory/macros.md` from a single code registry in `src/sase/macro/`. Let CI enforce that neither ever drifts.
3. **De-monolithize `docs/` immediately.**  
   Break files larger than 1,000 lines (`ace.md`, `configuration.md`, `macros.md`, `llms.md`, `cli.md`, `beads.md`) into modular topic folders (<400 lines per file). This single change will make agent-driven documentation updates dramatically faster, cheaper, and more reliable.
4. **Make documentation "first-class" through audited tooling (`sase doc read`), not prompt inlining.**  
   Give agents the ability to read targeted, audited sections of documentation without polluting the core instruction bundle or the TUI memory panel.
