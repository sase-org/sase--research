# Unifying Agent Memory and Documentation: Theory, Architecture, and Agentic Maintenance

**Author:** Researcher `gem` (4-Researcher Swarm)  
**Date:** October 2026  
**Artifact Target:** `research:202610/migrating_memory_to_documentation_and_agentic_maintenance__gem.md`

---

## Executive Summary

As autonomous coding agents transition from ephemeral conversational assistants to persistent software engineers, software projects face an acute epistemological challenge: **the Dual Knowledge Problem**. Modern agentic harnesses (including SASE) frequently maintain two parallel repositories of truth:
1. **Agent Memory (`sase/memory/`):** Explicitly curated context notes, instruction shims, and memory webs loaded into prompt context or fetched via specialized audited tooling.
2. **Project Documentation (`docs/`):** Human-facing reference manuals, architectural overviews, CLI specifications, and guides (typically rendered via static site generators like MkDocs).

When reference memories—such as `sase/memory/macros.md`—grow to capture extensive syntax rules, grammar tables, and operational workflows, they inevitably become **shadow documentation**. This creates severe synchronization drag, duplication of effort, and drift: changes landed in code require synchronized edits across `src/`, `docs/`, and `sase/memory/`.

The strategic solution is twofold:
1. **Elevate Project Documentation to First-Class Agent Memory:** Rather than treating `docs/` as a human-only artifact and `memory/` as an agent-only sandbox, the project documentation tree must be formalized as the system's **canonical external semantic memory**. The memory control plane (`sase memory read`, audited tracking, link closures) should operate seamlessly over `docs/`.
2. **Structure Documentation for Agentic Maintenance:** Unstructured or monolithic documentation files ("soup-to-nuts" pages) defeat agentic maintenance. By restructuring documentation along clear rhetorical axes—specifically adopting the **Diátaxis framework** (separating Reference, How-To, Explanation, and Tutorials) and anchoring technical reference directly to code artifacts (via AST dependency graphs and living documentation principles)—documentation becomes modular, predictable, and scriptable by agents.

This report provides the theoretical foundation, architectural blueprint, and a **curated, ranked reading list** of 10 seminal papers, treatises, and industry frameworks that provide direct inspiration for this transformation.

---

## 1. The Core Problem: Shadow Documentation and Knowledge Bifurcation

### 1.1 The Anatomy of Memory Bloat: The `sase/memory/macros.md` Case Study
In SASE, memory files under `sase/memory/` serve a crucial role: they provide durable agent context across ephemeral runs. SASE distinguishes between:
- **Core Memory (`type: core`):** Compact, always-loaded instructions inlined into `AGENTS.md` and provider shims (e.g., workspace rules, finalizer contracts).
- **Reference Memory (`type: reference`):** Detailed notes fetched on demand via audited `sase memory read` calls.
- **Memory Webs (`glossary`, `decisions`, `task_types`):** Keyword-keyed strands addressed via `web:keyword`.

However, examining `sase/memory/macros.md` (over 14 KB of densely packed syntax tables, directive specifications, and launch rules) reveals an immediate tension. Concurrently, `docs/macros.md` exists as a 240+ KB developer manual. 

Why did `macros.md` take up residence in `sase/memory/`?
Because agents generating or interpreting macro directives (`%queue`, `%hold`, `%final`, `#pr`) needed unambiguous, authoritative syntax rules. But because `sase/memory/` was isolated from the `docs/` publishing pipeline, `sase/memory/macros.md` became a second, distilled documentation manual. 

This pattern introduces three systemic failure modes:
1. **Triple-Update Tax:** Introducing a new directive or modifying argument syntax requires updating:
   - The implementation (`src/sase/macros/`).
   - The developer documentation (`docs/macros.md`).
   - The agent memory reference (`sase/memory/macros.md`).
2. **Subtle Semantic Drift:** When an edge case is clarified or updated in `docs/` but forgotten in `sase/memory/`, agents execute against obsolete constraints or hallucinate retired parameters.
3. **Context Window Contention:** Reference memory files authored as prose essays or mixed manuals burden agent context with extraneous background when only a strict syntax signature was required.

### 1.2 Cognitive Architecture: Documentation IS Semantic Memory
To resolve this split, we can turn to the cognitive science taxonomy formalized by Sumers et al. (Princeton) in **CoALA (Cognitive Architectures for Language Agents)**. CoALA structures agent memory into:
- **Working Memory:** The active prompt / context window of the current LLM call.
- **Episodic Memory:** Temporal sequences of past experiences, agent session histories, chat transcripts, and tool execution traces.
- **Procedural Memory:** Executable knowledge, skills, workflow scripts, and prompt macros (e.g., `#commit`, `%auto`).
- **Semantic Memory:** Factual domain knowledge, system models, architectural rules, API contracts, and language grammars.

Under this taxonomy, **software documentation is not merely text for humans; it is externalized semantic memory.** 
The bifurcation between "project documentation" and "agent memory" is an artificial historical accident. When documentation is structured and managed with the same rigor, metadata, and access controls as memory, it becomes the single authoritative source of semantic truth for humans and AI agents alike.

---

## 2. Elevating Documentation to a First-Class Memory Representation

What does it mean for project documentation in `docs/` to be a "first-class representation of memory"? It means documentation ceases to be passive text and adopts the capabilities, governance, and auditability of SASE's memory engine:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        UNIFIED SASE KNOWLEDGE ENGINE                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
┌───────────────────────┐                         ┌───────────────────────┐
│     sase/memory/      │                         │         docs/         │
│  (Instruction Layer)  │                         │   (Semantic Layer)    │
├───────────────────────┤                         ├───────────────────────┤
│ • Core Agent Rules    │                         │ • Technical Reference │
│ • Memory Webs         │                         │ • How-To Guides       │
│   - decisions: (ADRs) │                         │ • System Architecture │
│   - glossary: (Terms) │                         │ • User Tutorials      │
│ • Pointers & Indexes  │                         │ • CLI / API Manuals   │
└──────────┬────────────┘                         └───────────┬───────────┘
           │                                                  │
           └────────────────────────┬─────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       SHARED CONTROL PLANE                              │
├─────────────────────────────────────────────────────────────────────────┤
│ 1. Audited Reads: sase memory read docs:reference/macros -r "<why>"     │
│ 2. Canonical Linking: [[docs/reference/macros#queue]]                   │
│ 3. Automated Verification: AST & symbol checks, doctests via just check │
│ 4. Agentic Maintenance: Git-diff-driven sync loops (RepoAgent pattern)  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Uniform Addressing and Auditing
Currently, `sase memory read` supports flat notes (`sase memory read cli_rules.md`) and web strands (`sase memory read glossary:stitch`). 
If `docs/` is a first-class memory provider:
- Documentation can be queried through the same audited interface:
  ```bash
  sase memory read docs:reference/macros -r "Need exact syntax for %queue multiplier"
  ```
- Reads are logged to `.sase/state/audit/`, providing visibility into which documentation pages agents rely on and which sections correlate with task errors.

### 2.2 Authoritative Frontmatter and Link Closures
Just as SASE memory files declare YAML frontmatter (`type`, `parent`, `priority`, `link_reference`, `link_rendering`), documentation files in `docs/` can adopt lightweight metadata:
- **`audience`:** `agent`, `human`, or `hybrid`.
- **`symbols`:** Explicit code symbols (classes, functions, CLI flags) documented in this file, allowing static linters to verify cross-references.
- **`status`:** `active`, `deprecated`, or `draft`.
- **`closure`:** Support for inline `[[...]]` wiki-style transclusion and reference linking across the documentation graph.

### 2.3 The Division of Responsibility: Memory vs. Docs
Under a unified paradigm, what stays in `sase/memory/` and what moves to `docs/`?
- **Stays in `sase/memory/`:**
  - **Core Prompt Instructions:** The minimal, highly dense ~100-line bootstrap inlined into `AGENTS.md` and provider shims (workspace isolation rules, finalizer declaration protocols).
  - **Memory Webs (Historical / Episodic Records):** 
    - `decisions/`: Architecture Decision Records (ADRs). Immutable snapshots of why choices were made.
    - `glossary/`: High-frequency domain terminology and ontology.
    - `task_types/`: Bead classification rules.
- **Moves to `docs/`:**
  - **All Functional and Technical Reference:** `sase/memory/macros.md`, `sase/memory/cli_rules.md`, `sase/memory/tui_perf.md`, etc., migrate to `docs/reference/` or `docs/how-to/`.
  - In `sase/memory/`, these files are replaced by lightweight pointers or eliminated entirely in favor of direct `docs:` resolution.

---

## 3. Structuring Documentation for Agentic Maintenance

If documentation is to be maintained and scripted by agents, human prose alone is insufficient. Documentation must be structured so that agents can:
1. Locate exactly what needs updating without reading megabytes of unrelated text.
2. Edit targeted blocks without altering the rhetorical style or introducing hallucinations.
3. Validate their changes mechanically (via linters and tests) before submitting.

### 3.1 The Diátaxis Framework: Cognitive Separation of Concerns
The most critical architectural step is decomposing documentation using **Diátaxis** (created by Daniele Procida). Diátaxis separates documentation into four distinct quadrants based on two orthogonal axes:
- **Learning vs. Working**
- **Practical vs. Theoretical**

| Quadrant | Focus | Orientation | Agent Scriptability & Role |
| :--- | :--- | :--- | :--- |
| **Technical Reference** | Factual machinery, grammar, options, CLI flags | Information-oriented (Theoretical / Working) | **Highest Automation:** Deterministic, strictly structured, often generated or linted directly against AST / code schemas. Agents can update this with near-zero hallucination. |
| **How-To Guides** | Problem-oriented recipes, step-by-step procedures | Task-oriented (Practical / Working) | **High Automation:** Task recipes (e.g. "How to write a multi-step macro workflow"). Agents consume these to execute tasks and can generate new recipes based on verified execution traces. |
| **Explanation** | Architectural context, rationale, design trade-offs | Understanding-oriented (Theoretical / Learning) | **Low/Supervised Automation:** Explains "why". Linked to ADRs (`decisions/`). Agents consult these for conceptual boundaries; modifications require architectural review. |
| **Tutorials** | Learning journeys for beginners, exploratory lessons | Learning-oriented (Practical / Learning) | **Manual / Human-Centric:** Pedagogical, narrative flow. Agents rarely touch tutorials. |

#### Why Diátaxis Solves the Agent Maintenance Problem:
In monolithic documents (like current `macros.md`), reference syntax tables are intermingled with workflow examples, operational advice, and design rationale. When an agent is tasked with updating the syntax for `%queue`, it must parse and rewrite mixed rhetorical prose, frequently degrading explanations or mangling examples. 
Under Diátaxis:
- The syntax specification lives cleanly in `docs/reference/macros.md`. An agent updating `%queue` can update a single markdown table or grammar block with surgical precision.
- The workflow guide lives in `docs/how-to/authoring_macros.md`.
- The rationale lives in `docs/explanation/hold_and_queue_admission.md`.

### 3.2 Living Documentation: Grounding Docs in Code
Cyrille Martraire’s **Living Documentation** principles establish that documentation must be:
1. **Reliable:** Anchored to code so it cannot lie.
2. **Low-Effort:** Automated generation and extraction wherever a single source of truth exists.
3. **Insightful:** Focusing on intent and architecture rather than repeating trivial code statements.

For SASE, this means:
- **Schema-Driven Generation / Linting:** CLI options, macro directives, and config keys should have their reference tables either auto-generated from code definitions (e.g., `argparse` / `click` / dataclasses) or verified in CI.
- **Symvision Integration:** SASE already uses `symvision` to track unused symbols and prevent dead code. SASE should bridge documentation into this loop: if a public symbol or directive documented in `docs/reference/` is renamed or deleted in `src/`, CI should fail unless the documentation is updated.

### 3.3 The Topological Co-Evolution Pattern (RepoAgent / DocAgent)
Recent software engineering research (notably OpenBMB's **RepoAgent** and Yang et al.'s **DocAgent**) introduces a proven blueprint for keeping documentation in lockstep with code:
1. **AST & Dependency Mapping:** Build a dependency DAG of code objects (functions, classes, modules, CLI handlers) and their corresponding documentation sections.
2. **Git Diff Tracing:** On any commit or PR, analyze the `git diff`.
3. **Bottom-Up Topological Propagation:** Identify all documentation nodes affected by the changed code objects. Traverse the DAG in bottom-up topological order so child documentation updates precede parent overviews.
4. **Targeted Agent Prompts:** Dispatch focused agent turns with explicit instruction scopes: *"Update the parameter table in `docs/reference/macros.md` for `%queue` to reflect the new multiplier syntax in `src/sase/macros/queue.py`."*

### 3.4 Executable and Testable Documentation
To make documentation scriptable, documentation must be executable:
- **Doctests / Code Snippet Verification:** Every code snippet in `docs/` should be tested during `just check`. Tools like `pytest-examples` or `markdown-exec` run markdown code fences in CI.
- If an agent refactors an API and fails to update the snippet in `docs/how-to/macros.md`, `just check` fails immediately, catching drift at the pre-commit boundary.

---

## 4. Architectural Migration Blueprint for SASE

To transition SASE from shadow memory notes to first-class, agent-maintained documentation, the following three-phase roadmap is recommended:

### Phase 1: Carving Out `sase/memory/macros.md` via Diátaxis
1. **Create `docs/reference/macros.md`:** Migrate all formal syntax tables, directive grammars (`%queue`, `%hold`, `%final`), frontmatter input types, and CLI flags into a purely factual reference page.
2. **Create `docs/how-to/authoring_macros.md`:** Migrate practical workflow recipes, rollover macros (`#pr`, `#commit`), and fan-out examples into goal-oriented guides.
3. **Retire `sase/memory/macros.md`:** Replace the 14 KB reference note with a compact pointer in `sase/memory/README.md` or a lightweight core directive summary.

### Phase 2: First-Class `docs:` Memory Resolution
1. **Extend `sase memory read`:** Implement `docs:` selector resolution:
   ```bash
   sase memory read docs:reference/macros -r "Querying %hold directive arguments"
   ```
2. **Section Anchor Filtering:** Allow targeted reads using anchor fragments (e.g. `docs:reference/macros#queue-directive`), returning only the requested section to save context window tokens.
3. **Audit Log Integration:** Log all `docs:` reads to the project's memory audit ledger.

### Phase 3: Automated Doc-Sync Workflows and CI Verification
1. **Doc Linting in `just check`:**
   - Link checking (`markdown-link-check` or internal resolver).
   - Snippet execution: ensure all bash/python blocks in `docs/how-to/` run cleanly.
   - Symbol verification: verify that documented CLI flags and config keys match the runtime registry.
2. **Dedicated Documentation Maintenance Agent Skill / Macro:**
   - Introduce an automated workflow (e.g. `#doc-sync`) that inspects staged git diffs against the documentation map and updates `docs/` before final declaration.

---

## 5. Ranked Reading List for Inspiration

Below is a curated, prioritized reading list of 10 key papers, books, and frameworks. Each entry has been analyzed for its core contribution, theoretical relevance, and practical application to SASE's architecture.

```
                    TOP 10 READING LIST AT A GLANCE
 ─────────────────────────────────────────────────────────────────────────────
  #1  RepoAgent (Luo et al., 2024)           ─ Git diff + AST doc maintenance
  #2  CoALA (Sumers et al., 2023)             ─ Cognitive agent memory taxonomy
  #3  Diátaxis Framework (Procida, 2020)      ─ 4-quadrant doc structure
  #4  Living Documentation (Martraire, 2019)  ─ Single source of truth / DDD
  #5  ReadMe.LLM (Wijaya et al., 2025)        ─ LLM-oriented documentation specs
  #6  DocAgent (Yang et al., 2025)            ─ Multi-agent DAG doc generation
  #7  Documenting Arch. Decisions (Nygard)    ─ ADRs as immutable decision memory
  #8  CODESYNC (arXiv:2502.16645, 2025)       ─ Synchronizing LLMs with API drift
  #9  Docs Like Code (Gentle, 2017)           ─ CI/CD & version control for docs
  #10 Cascade (2026)                          ─ Test-driven doc-drift detection
 ─────────────────────────────────────────────────────────────────────────────
```

---

### Rank 1: RepoAgent: An LLM-Powered Open-Source Framework for Repository-level Code Documentation Generation
* **Authors:** Qinyu Luo, Yining Ye, Shihao Liang, Zhong Zhang, Yujia Qin, Yaxi Lu, Yesai Wu, Xin Cong, Yankai Lin, Zhiyuan Liu, Maosong Sun (Tsinghua University / OpenBMB)
* **Year & Source:** 2024 · [arXiv:2402.16667](https://arxiv.org/abs/2402.16667) · EMNLP / ASE 2024
* **Core Contribution:** RepoAgent is the first open-source, repository-level framework designed specifically to maintain and synchronize documentation with evolving code. It operates by parsing the repository into an Abstract Syntax Tree (AST), constructing an inter-object dependency Directed Acyclic Graph (DAG), and tracking code modifications via Git diffs. Documentation is generated and updated in **bottom-up topological order**, ensuring that when higher-level components are documented, their underlying dependencies are already fully documented.
* **Why You Should Read It:** It directly solves the "how to make maintenance scriptable via agents" question. Instead of asking an agent to re-read and re-write entire documentation files blindly, RepoAgent demonstrates how git diffs and AST dependency graphs isolate the exact documentation nodes that need regeneration.
* **Direct Application to SASE:** SASE can adopt RepoAgent's Git diff + DAG mapping to power an automated `#doc-sync` macro. When a SASE agent touches `src/sase/macros/directive.py`, the DAG maps the change to `docs/reference/macros.md#directives` and triggers a localized update.

---

### Rank 2: Cognitive Architectures for Language Agents (CoALA)
* **Authors:** Theodore R. Sumers, Shunyu Yao, Karthik Narasimhan, Thomas L. Griffiths (Princeton University)
* **Year & Source:** 2023 · [arXiv:2309.02427](https://arxiv.org/abs/2309.02427)
* **Core Contribution:** CoALA synthesizes decades of cognitive science (ACT-R, Soar) with modern LLM capabilities into a unified architectural blueprint for language agents. It provides a formal taxonomy of agent memory, dividing it into Working Memory (active context) and Long-Term Memory (Episodic, Procedural, and Semantic), while formalizing memory operations (Retrieval, Reasoning, Learning/Consolidation).
* **Why You Should Read It:** It gives you the rigorous conceptual foundation needed to treat project documentation as **externalized semantic memory**. It clarifies why confusing procedural memory (skills, macros) with semantic memory (documentation, manuals) degrades agent performance.
* **Direct Application to SASE:** Re-align SASE’s memory terminology and storage layout around CoALA’s pillars:
  - Working Memory: ephemeral prompt context and provider shims (`AGENTS.md`).
  - Procedural Memory: SASE skills (`src/sase/macros/skills/`) and macros (`sase/macros/`).
  - Semantic Memory: Project documentation (`docs/`).
  - Episodic Memory: SASE chat transcripts, agent runs, and stitch histories.

---

### Rank 3: Diátaxis: A Systematic Approach to Technical Documentation Authoring
* **Author:** Daniele Procida (Divio / Canonical)
* **Year & Source:** 2020–present · [diataxis.fr](https://diataxis.fr/)
* **Core Contribution:** Diátaxis is the gold-standard documentation architecture adopted by major open-source ecosystems (Python, Ubuntu, NumPy, Astro). It models documentation needs along two axes (theory vs. practice, learning vs. working), defining four distinct, non-overlapping quadrants: Tutorials, How-To Guides, Technical Reference, and Explanation.
* **Why You Should Read It:** Diátaxis is the missing structural link for agentic maintenance. Monolithic markdown files cause agents to hallucinate because the prompt context mixes pedagogical, factual, and architectural styles. Diátaxis enforces strict separation: Reference pages become factual tables that agents can verify and update with high fidelity, while Explanation and Tutorial pages are protected from unwanted edits.
* **Direct Application to SASE:** Reorganize `docs/` into `docs/reference/`, `docs/how-to/`, `docs/explanation/`, and `docs/tutorials/`. Migrate `sase/memory/macros.md` into `docs/reference/macros.md` (grammar tables) and `docs/how-to/authoring_macros.md` (practical examples).

---

### Rank 4: Living Documentation: Continuous Knowledge Sharing by Design
* **Author:** Cyrille Martraire
* **Year & Source:** 2019 · Addison-Wesley Professional (ISBN: 978-0134689326)
* **Core Contribution:** Martraire develops a comprehensive methodology for creating documentation that evolves synchronously with code under Domain-Driven Design (DDD). It articulates the four principles of living documentation: Reliable (tethered to code and tests), Low-effort (extracted from system artifacts), Collaborative (using ubiquitous domain language), and Insightful (focused on intent and architecture).
* **Why You Should Read It:** It shifts the mindset from "writing documentation" to "designing systems that document themselves." It provides concrete techniques for extracting documentation from code declarations, annotations, and test suites, eliminating duplicate manual writing.
* **Direct Application to SASE:** Leverage SASE's CLI definitions, macro schemas, and config models as the primary sources of truth. Write lightweight introspection utilities that generate or validate the reference markdown tables in `docs/reference/` during build time.

---

### Rank 5: ReadMe.LLM: A Framework to Help LLMs Understand Your Library
* **Authors:** Sandya Wijaya, Jacob Bolano, Alejandro Gomez Soteres, Shriyanshu Kode, Yue Huang, Anant Sahai (UC Berkeley)
* **Year & Source:** 2025 · [arXiv:2504.09798](https://arxiv.org/abs/2504.09798)
* **Core Contribution:** This paper introduces the concept of **"LLM-oriented documentation"**. The authors demonstrate that traditional documentation written for human eyes often fails when consumed by LLMs due to hidden assumptions, narrative verbosity, and ambiguous signatures. ReadMe.LLM provides a standardized specification and generation tool for creating concise, high-density codebase digests that boost LLM code-generation accuracy by up to 100%.
* **Why You Should Read It:** If documentation is to serve as first-class agent memory, it must be authored or structured in a way that maximizes LLM comprehension and minimizes token waste. This paper provides empirical guidance on how to format reference docs specifically for language models.
* **Direct Application to SASE:** Use ReadMe.LLM’s formatting principles for files in `docs/reference/` and for the summaries emitted by `sase memory read docs:...`. Strip decorative prose and focus on strict input/output contracts, parameter constraints, and failure modes.

---

### Rank 6: DocAgent: A Multi-Agent System for Automated Code Documentation Generation
* **Authors:** Dayu Yang, Antoine Simoulin, Xin Qian, Xiaoyi Liu, Yuwei Cao, Zhaopu Teng, Grey Yang
* **Year & Source:** 2025 · [arXiv:2504.08725](https://arxiv.org/abs/2504.08725)
* **Core Contribution:** DocAgent addresses the difficulty LLMs face when generating and updating documentation for large repositories with deep dependency graphs. It implements a multi-agent cooperative architecture comprising specialized roles (Reader, Searcher, Writer, Verifier, and Orchestrator) coordinated via a topological code dependency graph.
* **Why You Should Read It:** Demonstrates how multi-agent swarms can divide the labor of documentation maintenance: one agent inspects the code diff, another retrieves the dependent documentation nodes, a third drafts the update, and a dedicated verifier checks for correctness.
* **Direct Application to SASE:** Design a multi-agent documentation swarm macro (`#doc-team` or `#doc-sync`) for SASE epics. When landing complex multi-repository refactors, dispatch a verification agent to check that documentation changes accurately reflect the code diff.

---

### Rank 7: Documenting Architecture Decisions (Architecture Decision Records)
* **Author:** Michael Nygard
* **Year & Source:** 2011 · Cognitect Blog / IEEE Software (Zimmermann et al., 2020)
* **Core Contribution:** Nygard formalized the concept of Architecture Decision Records (ADRs): lightweight, immutable, version-controlled markdown records that capture a single architectural decision, its context, consequences, and alternatives. Crucially, ADRs are **chronological and immutable**; when a decision changes, a new ADR supersedes the old one rather than rewriting history.
* **Why You Should Read It:** It provides the conceptual boundary between **living documentation** (which describes what the system does today) and **decision memory** (which explains why the system was built that way). SASE’s `decisions/` memory web is already an implementation of ADRs.
* **Direct Application to SASE:** Keep `sase/memory/decisions/` strictly as immutable ADRs. When migrating functional explanations from `sase/memory/` to `docs/`, link the living documentation in `docs/explanation/` back to the corresponding ADR strands using `[[decisions:keyword]]`.

---

### Rank 8: CODESYNC: Synchronizing Large Language Models with Dynamic Code Evolution at Scale
* **Authors:** Research Consortium (Tsinghua, et al.)
* **Year & Source:** 2025 · [arXiv:2502.16645](https://arxiv.org/abs/2502.16645)
* **Core Contribution:** This paper studies the phenomenon of **code-documentation drift and API evolution**, introducing CODESYNC and the CODESYNCBENCH benchmark. It systematically evaluates how models fail when libraries evolve and establishes update-aware retrieval and instruction tuning methods to keep models synchronized with rapid code changes.
* **Why You Should Read It:** Provides rigorous data on why outdated documentation is more damaging to coding agents than missing documentation. Offers algorithmic techniques for detecting when documentation has drifted from implementation.
* **Direct Application to SASE:** Establish a documentation freshness metric in SASE. If an agent encounters a discrepancy between a code signature and a documentation page, empower the agent to log a `memory` or `bug` task bead immediately via `/sase_new_task`.

---

### Rank 9: Docs Like Code: Modern Approaches to Software Documentation
* **Author:** Anne Gentle
* **Year & Source:** 2017 (2nd Ed.) · Just Write Click (ISBN: 978-1365859731)
* **Core Contribution:** The foundational industry guide for integrating documentation directly into the software development lifecycle. It advocates storing documentation in the same repository as code, writing in plain text/Markdown, using version control, subjecting docs to code review, and automating quality checks through continuous integration (CI) pipelines.
* **Why You Should Read It:** It details the tooling, workflow, and culture required to make documentation maintainable by software engineers. It covers automated linting, style guide enforcement (Vale), dead-link verification, and automated build testing.
* **Direct Application to SASE:** Treat `docs/` with the exact same rigor as `src/`. Add markdown linting (`markdownlint`), prose checks, and link integrity verification directly into SASE's `just check` recipe so that pull requests cannot break documentation integrity.

---

### Rank 10: Cascade: Detecting Code-Documentation Inconsistencies via Automated Test Generation
* **Authors:** Academic Software Engineering Group
* **Year & Source:** 2026 / Pre-print · Software Engineering Research
* **Core Contribution:** Cascade introduces a method to automatically verify documentation claims by synthesizing automated unit and integration tests directly from documentation descriptions. If the synthesized test fails against the code, a concrete code-documentation inconsistency is proven and flagged.
* **Why You Should Read It:** Demonstrates the ultimate state of "executable documentation": using LLMs not just to write docs, but to generate automated tests that prove whether the documentation's assertions match the codebase reality.
* **Direct Application to SASE:** Explore automated test synthesis from `docs/how-to/` examples. By turning documented how-to examples into automated test runners within SASE's test suite, SASE guarantees that every documented workflow remains functioning.

---

## 6. Synthesis: Recommended Next Actions for SASE

To move forward with these insights, the following concrete actions are recommended:

1. **Adopt Diátaxis for `docs/`:**
   - Audit the current `docs/` directory and reorganize content into `docs/reference/`, `docs/how-to/`, `docs/explanation/`, and `docs/tutorials/`.
2. **Execute the `macros.md` Migration:**
   - Split `sase/memory/macros.md` into `docs/reference/macros.md` (syntax & grammars) and `docs/how-to/authoring_macros.md` (workflow recipes).
   - In `sase/memory/`, replace `macros.md` with a clean pointer or retire it.
3. **Elevate `docs/` to First-Class Memory in SASE Core:**
   - Add support in `sase memory read` for `docs:` targets (`sase memory read docs:reference/macros`).
   - Audit `docs:` reads through the SASE state store.
4. **Implement Doc-Verification in CI:**
   - Add a `just lint-docs` step to `just check` that checks markdown formatting, internal links, and symbol validity.
5. **Develop an Agentic Doc-Sync Workflow:**
   - Implement an agent macro (e.g., `#doc-sync`) inspired by RepoAgent that compares `git diff` against the documentation map and proposes updates when code contracts change.

---
*Report filed by researcher `gem`.*
