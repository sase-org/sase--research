---
title: "Architectural Foundations and Strategic Improvements for SASE Research Swarms"
create_time: 2026-10-01T12:15:00-04:00
updated_time: 2026-10-01T12:15:00-04:00
status: draft
tags:
  - research-swarm
  - multi-agent-architecture
  - sase-core
  - xprompts
  - artifact-lineage
---

# Architectural Foundations and Strategic Improvements for SASE Research Swarms

## Executive Summary

Autonomous research in complex software engineering repositories is not solved by simply broadcasting a prompt across $N$ frontier LLM providers and having a lead agent summarize their outputs. When multi-agent swarms lack structured role specialization, adversarial testing, and grounded empirical feedback, they exhibit well-documented pathologies: **consensus homogenization** (different models repeating identical conventional wisdom), **synthesis degradation** (leads producing vague compromise summaries that erase nuanced findings and contradictions), and **epistemic drift** (asserting unverified pre-trained beliefs rather than investigating the live codebase).

This report investigates the architecture of the `#research_swarm` xprompt in the SASE ecosystem (`sase` core and the `sase-research-artifacts` plugin). We analyze foundational multi-agent research principles, identify critical architectural bugs and limitations discovered during live swarm execution, evaluate underutilized SASE platform capabilities, propose justified new SASE features, and conclude with a ranked, prioritized roadmap for improvement.

### Core Discoveries & Bottom Line

1. **Critical Parser Bug in Embedded Swarms**: If `#research_swarm` is invoked without explicit `(prompt=...)` or `::` argument binding (for example `#research_swarm\n<prompt>` or `#research_swarm: <options>\n<prompt>`), Jinja evaluates `prompt` as blank across the template. Because embedded swarms place the first segment (`cdx`) at the call site and append subsequent segments (`cld`, `grk`, `mus`, `gem`, `final`), the unparsed prompt text trailing the directive attaches *only* to the first researcher, leaving all other researchers and the lead running with an empty prompt.
2. **Stale Lineage Derivation in Core**: In `sase/artifact_links/derive/_research_lineage.py`, `_SWARM_SUFFIXES` is hardcoded to `("__a", "__b")`. SASE's core link derivation has never been updated to reflect the multi-provider suffixes (`__cdx`, `__cld`, `__grk`, `__mus`, `__gem`), breaking automated `derives-from` artifact lineage graph generation.
3. **Artifact Metadata & Schema Mismatch**: The `sase-research-artifacts` plugin specifies rich frontmatter properties (`status`, `tags`, `create_time`, `updated_time`) for the SASE TUI Artifacts Pane, but `#research` and `#research_swarm` prompts provide no frontmatter scaffolding, rendering reports without status badges, timestamps, or facets.
4. **Cognitive Homogeneity vs. Differentiated Roles**: `#research_swarm` currently provisions 5 models with identical prompts. Transitioning from homogeneous provider-based broadcasting to **differentiated cognitive roles** (e.g., Architectural Invariants, Adversarial Red-Team / Failure Modes, Empirical Codebase Auditing, and Ecosystem Standards) produces significantly broader and deeper findings.
5. **Synthesis Architecture**: Replacing single-pass consolidation with a structured **Disagreement & Consensus Ledger** prevents synthesis collapse and surfaces critical technical tensions.

---

## What Makes a High-Performing Research Agent Swarm?

Building an effective research swarm requires understanding the epistemic failure modes of large language models operating in multi-agent configurations.

```
                    ┌──────────────────────────────────────────────┐
                    │            USER RESEARCH REQUEST             │
                    └──────────────────────┬───────────────────────┘
                                           │
               ┌───────────────────────────┴───────────────────────────┐
               ▼                                                       ▼
   [CURRENT: Homogeneous Broadcast]                         [PROPOSED: Role-Differentiated]
  ┌─────────────────────────────────┐                    ┌─────────────────────────────────┐
  │ cdx: Generic Prompt             │                    │ Arch: Invariants & Boundaries   │
  │ cld: Generic Prompt             │                    │ RedTeam: Failure Modes & Risks  │
  │ grk: Generic Prompt             │                    │ Codebase: Empirical Git/Tests   │
  │ mus: Generic Prompt             │                    │ Ecosystem: Precedents & RFCs    │
  │ gem: Generic Prompt             │                    └────────────────┬────────────────┘
  └────────────────┬────────────────┘                                     │
                   │                                                      ▼
                   ▼                                     ┌─────────────────────────────────┐
  ┌─────────────────────────────────┐                    │ Stage 2: Cross-Critique/Delphi  │
  │ Lead: Single-pass consolidation │                    └────────────────┬────────────────┘
  │ (Compromise soup, lost nuance)  │                                     │
  └────────────────┬────────────────┘                                     ▼
                   │                                     ┌─────────────────────────────────┐
                   ▼                                     │ Lead: Consensus & Dispute Matrix│
  ┌─────────────────────────────────┐                    └────────────────┬────────────────┘
  │ Final Output                    │                                     │
  └─────────────────────────────────┘                                     ▼
                                                         ┌─────────────────────────────────┐
                                                         │ Linker: Canonical Publication   │
                                                         └─────────────────────────────────┘
```

### 1. Cognitive Diversity over Model Diversity

Running five different LLM providers (OpenAI, Anthropic, xAI, Muse, Google) provides hardware and training data diversity, but because frontier models are trained on overlapping corpora of internet text and academic papers, their initial response to an open-ended prompt tends to converge on mainstream conventional wisdom.

True cognitive diversity requires **role differentiation**:
- **The Structural/Architectural Analyst**: Examines system invariants, interface boundaries, coupling, and modularity. Asks: *"How does this proposal fit into the broader system architecture and existing contracts?"*
- **The Adversarial Red-Teamer (Contrarian / Devil's Advocate)**: Specifically tasked with finding reasons why the proposed idea will fail, exploring failure modes, edge cases, race conditions, scaling bottlenecks, security vulnerabilities, and developer ergonomics friction. Asks: *"Under what conditions does this break? What are the hidden maintenance costs?"*
- **The Empirical Codebase Auditor**: Grounded strictly in the live repository. Examines existing implementations, runs static analysis, audits commit history, checks existing test coverage, and evaluates concrete integration points. Asks: *"What does the actual code do today, and where does reality diverge from documentation?"*
- **The Ecosystem & Precedent Surveyor**: Explores external industry solutions, standard specifications, adjacent open-source projects, and academic literature. Asks: *"How have mature systems solved this problem, and what lessons were learned?"*

When agents investigate from orthogonal vantage points, the swarm captures complementary dimensions of the problem rather than five slightly reworded versions of the same overview.

### 2. Epistemic Hygiene and Verification

Unassisted LLMs exhibit high confidence when generating plausible-sounding but inaccurate technical claims (parametric hallucination). In a research swarm, agents must adhere to strict epistemic standards:
- **Fact vs. Inference vs. Speculation**: Reports must explicitly label verified facts (backed by code citations or documentation), logical deductions, and unverified hypotheses.
- **Disconfirmation Testing**: A research report is incomplete without addressing what evidence would falsify its thesis.
- **Auditable Grounding**: Claims must cite concrete file paths, symbol names, line numbers, or external URLs rather than vague assertions.

### 3. Preventing Synthesis Collapse (The Consolidation Bottleneck)

The most vulnerable point in a research swarm is the consolidation step (`research.<clan>.final`). When a single lead model is tasked with merging multiple lengthy reports, three degenerative failure modes occur:
1. **Compromise Soup**: The lead resolves sharp disagreements by writing generic, bland compromises that dilute actionable recommendations.
2. **Detail Attrition**: Concrete data, specific code locations, and edge-case caveats present in individual reports are discarded to fit token budgets.
3. **Contradiction Erasure**: Instead of surfacing technical disputes, the lead quietly picks one perspective or ignores the conflict entirely.

To prevent synthesis collapse, the lead's consolidation process must be structured around a **Formal Disagreement and Consensus Ledger**:
- **Consensus Items**: High-confidence findings corroborated across multiple independent perspectives.
- **Dialectic Disagreements**: Direct contradictions between researchers, explicitly presenting the competing arguments, evaluating the evidence for each, and explaining why one was chosen (or framing it as an open decision).
- **Novel Insights**: Discoveries surfaced by only a single researcher that warrant elevation.
- **Unresolved Open Questions**: Gaps in current evidence requiring human input or live prototyping.

---

## Current Architecture and Vulnerability Analysis of `#research_swarm`

The `#research_swarm` xprompt is defined in `sase-research-artifacts` at `src/sase_research_artifacts/xprompts/research_swarm.md`. 

### Pipeline Mechanics
1. **Parallel Fan-out**: Authoring up to 5 researcher segments (`cdx`, `cld`, `grk`, `mus`, `gem`) separated by markdown `---` dividers. Each segment is configured with `%q(1.5x, w=0.25)` and gated by `%if(should_run=...)` based on provider flags and `provider_enabled("hard")`.
2. **Draft Output**: Each researcher invokes `#research(suffix=<short>)`, writing an independent report to `$(sase repo path research --ensure)/$(date +%Y%m)/<stem>__<short>.md` and registering it via `sase artifact create -p ... -l "research:..."`.
3. **Consolidation**: The lead agent `research.<clan>.final` waits on all researchers (`%wait:research.{@1}.<short>`), queries `wait.artifacts` to identify the registered reports, moves each report into a newly created `<month-dir>/<name>/` directory, and writes `<name>/<name>__final.md` (or `<name>.md`).
4. **Companion Production & Publication**: When `image=true` or `linker=true`, the image agent generates `<name>_infographic.png`, and the linker agent publishes the final clean `<name>.md` with verified links and embedded graphics.

### Detailed Audit of Discovered Flaws

#### 1. Embedded Swarm Macro Expansion Bug
During our execution, an urgent usability bug was uncovered in how SASE processes embedded xprompt swarms. SASE defines embedded swarms such that the first segment is rendered at the call site, while subsequent segments are appended.
When a user launches a swarm as:
```text
#research_swarm
Can you investigate ...
```
The xprompt invocation `#research_swarm` has no explicit `prompt=` argument. SASE initializes Jinja variables with default `prompt=None` or empty string. Therefore:
- The first segment (`cdx`) expands at the call site, and the user's trailing prompt text is appended to `cdx`'s prompt block.
- Segments 2 through 5 (`cld`, `grk`, `mus`, `gem`) and the lead (`final`) expand with `{{ prompt }}` evaluated as blank.
- As observed in this turn's artifacts, researchers `cld`, `grk`, `mus`, `gem`, and `final` received an empty prompt (`: `), while only `cdx` received the full user question.

#### 2. Stale Lineage Derivation in Core SASE
In `src/sase/artifact_links/derive/_research_lineage.py`, the function `derive_research_swarm_lineage` detects parent-child relationships between consolidated research reports and their constituent drafts:
```python
_RESEARCH_KIND = "research"
_SWARM_SUFFIXES = ("__a", "__b")
```
When research swarms originally supported only two generic agents (`__a` and `__b`), this derivation worked. However, when the swarm was upgraded to per-provider suffixes (`__cdx`, `__cld`, `__grk`, `__mus`, `__gem`), the core derivation logic was never updated. As a result:
- `sase artifact link suggest` fails to detect lineage for modern research swarms.
- The SASE artifact graph lacks bidirectional edges connecting the published report to its source drafts.

#### 3. Missing Frontmatter Scaffolding
In `src/sase_research_artifacts/provider.py`, `RESEARCH_REF_PROVIDER_SPEC` specifies:
```python
"properties": {
    "create_time": {"type": "datetime", "source": "markdown_frontmatter"},
    "updated_time": {"type": "datetime", "source": "markdown_frontmatter"},
    "status": {
        "type": "enum",
        "values": ["draft", "review", "final", "archived"],
        "source": "markdown_frontmatter",
    },
    "tags": {"type": "string_list", "source": "markdown_frontmatter"},
}
```
However, neither `#research.md` nor `#research_swarm.md` instructs researchers or leads to generate YAML frontmatter. Consequently, all created research reports omit frontmatter, preventing the SASE TUI Artifacts Pane from displaying status badges, grouping by status, or indexing tags.

#### 4. Destructive In-Place Reorganization
The lead researcher is instructed to move files on disk (`mv <month-dir>/<name>__<suffix>.md <month-dir>/<name>/<name>__<suffix>.md`).
- Because agents run in ephemeral numbered workspaces (`sase_<N>`), performing file renames in the lead's private workspace changes paths that were previously indexed under durable artifact references (`research:<relpath>`).
- If another agent or user queries the original registered reference, the path on disk in other workspaces is unaligned until synchronizations occur.
- It is significantly cleaner for researchers to write directly into the topic directory or for the lead to register updated artifact references declaratively.

---

## Taking Better Advantage of Existing SASE Features

The SASE platform contains rich primitives that `#research_swarm` can immediately leverage without needing new platform-level code:

### 1. SASE Goals Integration (`sase goal`)
SASE has a dedicated, Rust-backed Goal Ledger (Decisions 10 and 11). Every goal has an ID, title, target outcome, and status. Research is almost always conducted to inform an engineering goal.
- **Capability**: `#research_swarm` should accept an optional `goal=<id>` parameter.
- **Implementation**: The xprompt can inspect `sase goal show <id>`, injecting the goal's title and desired outcome into the prompt context.
- **Completion**: Upon finishing, the lead or linker can execute `sase artifact link -s "research:<path>" -t "goal:<id>" -r "informs"` to bind the research directly to the project's active goal ledger.

### 2. SASE Beads Integration (`sase bead`)
Research often uncovers defects, architectural debt, or necessary follow-up work.
- SASE core rules already emphasize filing discovered work via `/sase_new_task` or recording proposed follow-ups.
- `#research_swarm` should explicitly instruct researchers:
  *"If your investigation uncovers bugs or unhandled edge cases in the existing codebase, file them as SASE task beads (`task_type=bug` or `task_type=feature`) and cite the created bead IDs in your report."*
- This transforms research from a passive document into an active driver of the project's backlog.

### 3. Agent Tribes and Clans (`%clan`, `%tribe`)
Currently, only the lead agent has `%clan(research.{@1}, tribe=research, summary=...)`. Individual researchers have `%id(<short>, clan=research.{@1})` with no summary.
- The TUI and Pager group agents by clan and tribe.
- By assigning distinctive descriptive summaries to each researcher (e.g. `%clan(research.{@1}, tribe=research, summary=[[bold]RESEARCH (Red Team):[/bold] {{ prompt }}])`), the ACE TUI, Deck panels, and Pager timelines immediately convey which role is currently thinking or executing.

### 4. SASE Model Aliases and Effort Ladder
Decision 21 defines the SASE size alias effort ladder: `@xlarge`, `@large`, `@medium`, `@small`, `@fast`.
- Currently, `#research_swarm` hardcodes specific model strings (`codex/gpt-6.1-sol@xhigh`, `claude/opus@xhigh`, etc.).
- When provider APIs experience downtime, rate limits, or version deprecations, hardcoded strings fail closed.
- SASE size aliases provide multi-provider fallback chains. Swarms should allow users to specify tier presets (e.g. `tier=xlarge` or `tier=fast`) rather than requiring manual provider-by-provider configuration.

### 5. Verified Link Checking and Tool Runs (`sase tool run`)
The linker agent already runs `curl` checks on URLs. This pattern can be expanded to the research phase:
- Empirical researchers can be instructed to run test suites or verification commands via `sase tool run` to empirically validate whether claimed bugs or behaviors exist in the repository.

---

## Justified New SASE Platform Features

While much can be accomplished within existing primitives, several targeted platform enhancements would fundamentally elevate SASE research swarms:

### 1. Swarm-Level Prompt Broadcast Semantics
**Problem**: As proven in this run, embedded swarms currently lack automatic remainder broadcasting. If arguments are omitted from the directive tag, subsequent text in the prompt buffer is given only to the first segment.
**Feature**: The SASE xprompt preprocessor (`src/sase/xprompt/processor.py`) should support a `@broadcast` modifier or automatically assign any unconsumed top-level body text to a designated default input (such as `prompt`) across all swarm segments.

### 2. Native Multi-Stage Swarm Directive (`%stage` or `%round`)
**Problem**: Expressing a multi-round Delphi or debate workflow (e.g. 5 researchers -> cross-critique -> synthesis) currently requires writing dozens of lines of repetitive Jinja templates with complicated `%wait` naming schemes.
**Feature**: Introduce a native directive or workflow primitive that can fan-in and fan-out across rounds:
```text
%swarm:research(clan=research.{@1})
  %round:1(roles=[arch, redteam, empirical, ecosystem])
  %round:2(critique=cross)
  %round:3(synthesize=lead)
```

### 3. Extensible Plugin Lineage Providers
**Problem**: `_SWARM_SUFFIXES` in `sase` core cannot anticipate suffixes introduced by third-party or plugin xprompts without modifying core code.
**Feature**: Allow `sase_artifact_refs` hook implementations (in `sase-research-artifacts`) to register their own lineage derivation rules (`artifact_lineage_provider_specs`), keeping core clean and plugins autonomous.

### 4. Research Linter & Evaluation Metric (`sase research lint`)
**Problem**: There is no automated verification that a research report meets quality standards before it is committed or converted to PDF.
**Feature**: Add a `sase research lint <path>` command that verifies:
- YAML frontmatter matches `RESEARCH_REF_PROVIDER_SPEC`.
- Heading structure complies with Pandoc PDF rules (no double numbering, no redundant TOC).
- All relative file links and in-document anchor links resolve.
- Citations to repository files point to valid paths and commits.

---

## Ranked List of Recommended Improvements

Below is the prioritized roadmap of actionable improvements, ranked by impact, urgency, and implementation feasibility:

| Rank | Improvement | Target Component | Complexity | Impact |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Fix Swarm Prompt Binding / Validation**<br>Ensure prompt text is properly validated and distributed to all swarm members; fail fast if `prompt` is empty rather than launching silent blank agents. | `sase-research-artifacts` / `sase` xprompt parser | Low | **Critical** |
| **2** | **Update Core Lineage Derivation**<br>Update `_SWARM_SUFFIXES` in `_research_lineage.py` to include `("__cdx", "__cld", "__grk", "__mus", "__gem")` so artifact link suggestion works. | `sase` core (`src/sase/artifact_links/`) | Trivial | **High** |
| **3** | **Enforce Standard Markdown Frontmatter**<br>Prompt all researchers and leads to output valid YAML frontmatter (`title`, `status`, `tags`, `create_time`, `updated_time`) matching `RESEARCH_REF_PROVIDER_SPEC`. | `sase-research-artifacts` (`research.md`, `research_swarm.md`) | Low | **High** |
| **4** | **Transition from Homogeneous to Role-Differentiated Prompts**<br>Assign explicit complementary mandates (Architectural Invariants, Adversarial Red-Team, Empirical Code Auditor, Ecosystem Surveyor) instead of identical generic prompts. | `sase-research-artifacts` (`research_swarm.md`) | Medium | **High** |
| **5** | **Structured Disagreement & Consensus Synthesis**<br>Require the lead agent to output a structured Consensus Matrix, Disagreement Ledger, and Novel Findings section to prevent synthesis degradation. | `sase-research-artifacts` (`research_swarm.md`) | Low | **High** |
| **6** | **First-Class SASE Goal & Bead Integration**<br>Accept `goal=<id>` and `bead=<id>` inputs in `#research_swarm`, inject their context, and automatically link generated artifacts to goals/beads. | `sase-research-artifacts` (`research_swarm.md`) | Medium | **Medium-High** |
| **7** | **Tiered Swarm Presets & Alias Fallbacks**<br>Provide preset profiles (`preset=quick`, `preset=balanced`, `preset=deep`) and utilize SASE size aliases (`@xlarge`, `@large`) to prevent hardcoded model breakage. | `sase-research-artifacts` (`research_swarm.md`, `default_config.yml`) | Medium | **Medium** |
| **8** | **Extensible Plugin Lineage Hookspec**<br>Add an `artifact_lineage_provider_specs` hook so plugins can declare custom lineage patterns without modifying host core code. | `sase` core & `sase-research-artifacts` | High | **Medium** |
| **9** | **Automated Research Quality Linter**<br>Implement `sase research lint` to validate frontmatter, link health, heading cleanliness, and citation integrity before publishing. | `sase-research-artifacts` / `sase` CLI | Medium | **Medium** |
| **10** | **Multi-Round Debate / Delphi Swarm Topology**<br>Implement native two-phase research swarms where researchers review and challenge peer findings before final synthesis. | `sase` core / `sase-research-artifacts` | High | **Future Expansion** |

---

## Conclusion

The `#research_swarm` xprompt is one of the most powerful collaborative capabilities in SASE. However, its current implementation operates primarily as a parallel model ensemble with flat synthesis and several subtle integration flaws. 

By repairing the prompt propagation and lineage derivation bugs, introducing cognitive role differentiation (especially an adversarial red-team), mandating structured consensus/disagreement ledgers, and linking directly with SASE's Goals and Beads systems, `#research_swarm` can evolve from an interesting multi-model experiment into an enterprise-grade automated research engine.
