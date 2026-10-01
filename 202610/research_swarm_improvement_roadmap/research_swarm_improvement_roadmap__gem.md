---
create_time: 2026-10-01
updated_time: 2026-10-01
status: research
tags: [research_swarm, multi_agent_swarms, sase_integration, output_variables, artifact_lineage, research_methodology]
---

# Advancing the Research Swarm: Cognitive Specialization, Synthesis Architecture, and SASE Engine Integration

**Researcher:** `research.37.gem` (Gemini / Antigravity)  
**Topic:** Comprehensive research into improving the `#research_swarm` xprompt swarm: multi-agent research methodologies, deeper integration with SASE platform features, proposed SASE engine capabilities, and a ranked improvement roadmap.  
**Target Repositories:** `sase-research-artifacts` linked repository, `sase` core engine, and `research` sidecar repository.

---

## Executive Summary & Bottom Line

The `#research_swarm` xprompt workflow is one of SASE's most sophisticated agent orchestration workflows. In its current design, it fans out up to five independent LLM researchers (`cdx`, `cld`, `grk`, `mus`, `gem`) in parallel, waits on all surviving researchers, invokes a lead consolidator (`final`) to synthesize their drafts into a unified document, and optionally launches an infographic designer (`image`) and an editorial publisher (`linker`).

However, an in-depth systems audit of `#research_swarm`, the underlying SASE engine, and current state-of-the-art multi-agent research architectures (e.g., Stanford STORM, The AI Scientist, adversarial debate architectures) reveals **four fundamental architectural limitations** in the current design:

1. **The Homogeneous Redundancy Trap (Cognitive Blindness):** All 5 researchers currently receive the *exact identical prompt and instructions* (`{{ prompt }} #research(suffix=...)`). Without role or perspective differentiation, independent models execute overlapping web searches, cite identical top-ranking search results, and produce drafts that have 70–80% semantic overlap. The swarm pays 5× the compute cost for marginal informational breadth.
2. **The Lead's Synthesis Bottleneck & "Lost-in-the-Middle":** The lead consolidator receives up to five lengthy markdown files (15,000–30,000 words total) in a single turn. LLMs digesting this volume suffer from synthesis fatigue and attention dilution: they summarize consensus points, smooth over genuine contradictions, and miss subtle technical disagreements.
3. **Severe Under-Utilization of Existing SASE Platform Primitives:**
   - **Output Variables (`sase var`):** SASE already possesses a full-featured cross-agent output variable system (`SASE_AGENT_VAR_UPSTREAMS_JSON`, `WaitRuntimeNamespace`, `agents.<agent_key>.<var>`), but `#research_swarm` uses none of it. Downstream agents are forced to parse unstructured markdown files rather than consuming machine-readable claim matrices.
   - **Artifact Lineage Bug (`sase-15r`):** SASE's built-in artifact lineage deriver (`src/sase/artifact_links/derive/_research_lineage.py`) is hardcoded to obsolete suffixes `_SWARM_SUFFIXES = ("__a", "__b")`. Consequently, `sase artifact link suggest` completely fails to detect or record `derives-from` relationships between consolidated reports and modern drafts (`__cdx`, `__cld`, `__grk`, `__mus`, `__gem`, `__final`).
   - **Actionability Disconnect:** Research reports live in isolation. Discovered follow-up tasks are not scaffolded into SASE task beads (`sase bead`), research is not bound to strategic goals (`sase goal`), and architectural decisions are not codified into SASE memory strands (`sase memory/decisions/`).
4. **Fragility in the Image-to-Linker Handoff:** Because SASE's `%wait` directive enforces hard-blocking semantics (releasing only on successful agent completion), an error, quota exhaustion, or rate limit in `<clan>.image` permanently parks `<clan>.linker` with an unresolvable dependency, preventing the canonical `<name>.md` report from ever publishing.

### Top Recommendation
Transform `#research_swarm` from a **naive parallel copy swarm** into a **faceted, multi-lens research collective with structured variable interchange and fail-safe publishing**:
- Assign explicit, orthogonal research lenses to parallel researchers (e.g., Empirical/Code Feasibility, Adversarial/Red Team, Theoretical/SoTA, Ecosystem/Precedents).
- Instrument each researcher to emit structured findings, key claims, and confidence scores via `sase var set`.
- Render a pre-compiled Cross-Researcher Comparison Matrix in the lead's Jinja prompt to eliminate synthesis fatigue.
- Decouple the linker from image hard-waits to eliminate workflow deadlocks.
- Fix bug `sase-15r` in SASE core so artifact link derivation tracks modern swarm drafts.

---

## 1. Deconstructing What Makes a Great Research Agent Swarm

To understand why `#research_swarm` needs improvement, we must examine the epistemic foundations of collaborative research and contrast naive multi-agent systems with high-rigor research architectures.

### 1.1 The Pitfalls of Naive Multi-Agent Parallelism

In classical distributed systems, running $N$ identical workers on a partitioned dataset provides linear scaling. In generative AI research, however, running $N$ models on the *same unpartitioned open-ended prompt* suffers from rapidly diminishing returns:

```
Naive Swarm:
User Prompt ──┬──> [Codex]  ──> Queries Google ──> Cites Source A, B ──> Draft 1 ──┐
              ├──> [Claude] ──> Queries Google ──> Cites Source A, C ──> Draft 2 ──┼──> [Lead Consolidator]
              ├──> [Grok]   ──> Queries Google ──> Cites Source A, D ──> Draft 3 ──┤    (Overwhelmed by 5x
              ├──> [Muse]   ──> Queries Google ──> Cites Source B, C ──> Draft 4 ──┤     overlapping drafts)
              └──> [Gemini] ──> Queries Google ──> Cites Source A, B ──> Draft 5 ──┘
```

When all models receive `{{ prompt }} #research(suffix=...)`:
1. **Search Query Convergence:** Most LLMs formulate similar search queries when presented with identical instructions. They hit the same top-ranking documentation, blog posts, and GitHub repositories.
2. **Superficial Breadth over Deep Inquiry:** Every researcher attempts to provide an exhaustive, holistic answer in a single turn. As a result, each researcher spends its limited context and token budget skimming the surface rather than conducting deep primary-source code audits, tracing edge cases, or verifying empirical data.
3. **Groupthink via Public Search Algorithms:** Even though the agents are strictly isolated from one another ("Conduct your research independently and do not read peer reports"), their information supply is not independent—it is correlated by search engine indexing and popular consensus.

### 1.2 The Principles of High-Rigor Research Swarms

State-of-the-art research frameworks (such as Stanford's STORM for topic-oriented synthesis, Sakana AI's The AI Scientist, and multi-perspective adversarial debates) succeed because they enforce four structural properties:

| Property | Naive Swarm (Current) | Rigorous Research Swarm (Proposed) |
| :--- | :--- | :--- |
| **Cognitive Diversity** | Identical prompt sent to different model weights | Specialized research lenses / personas with divergent inquiry goals |
| **Information Partitioning** | All agents search the same broad problem space | Agents explore distinct sub-questions or specialized evidentiary angles |
| **Epistemic Stress-Testing** | Passive synthesis; lead assumes drafts are truthful | Explicit adversarial / red-team challenges to test fragile assumptions |
| **Synthesis Architecture** | Massive unstructured text dumps to lead LLM | Structured claim matrices and confidence scores via machine-readable variables |
| **Auditability & Grounding** | Linker tests HTTP 200 via `curl` | Claims tied to primary artifacts, code references, and audited reads |

---

## 2. Deep Dive: Architectural and Methodological Swarm Improvements

### 2.1 Orthogonal Cognitive Lenses (Faceted Research)

Rather than having five generalists write five competing essays on the exact same topic, the swarm should assign distinct **research lenses** to its members. Each lens focuses the agent's attention on a specific dimension of rigorous research:

1. **The Empirical & Systems Architecture Lens (Assigned to Codex / `cdx`):**
   - *Focus:* Concrete implementation details, codebase inspections, schema models, performance benchmarks, API contracts, edge cases, and mechanical failure modes.
   - *Directive:* "Focus on physical feasibility, codebase realities, and implementation mechanics. Inspect existing code, test configurations, and measure concrete bottlenecks. Reject theoretical claims that lack implementation paths."
2. **The Theoretical & State-of-the-Art Lens (Assigned to Claude / `cld`):**
   - *Focus:* Conceptual taxonomies, formal definitions, industry standards, architectural patterns, academic literature, and long-term design elegance.
   - *Directive:* "Focus on structural abstractions, conceptual clarity, taxonomy, and principled design tradeoffs. Identify the core theoretical problem and frame the solution space against established computer science paradigms."
3. **The Adversarial Red Team & Failure Mode Lens (Assigned to Grok / `grk` or Gemini / `gem`):**
   - *Focus:* Devil's advocacy, stress-testing assumptions, spotting hidden risks, operational fragility, backward-compatibility breaks, and questioning prevailing consensus.
   - *Directive:* "Act as the adversarial skeptic. Your primary mission is to identify what could go wrong, where the proposed direction makes unverified assumptions, what operational traps exist, and why alternatives might be superior."
4. **The Prior Art & Ecosystem Lens (Assigned to Muse / `mus` or Gemini / `gem`):**
   - *Focus:* How other ecosystems, prior SASE epics, open-source libraries, and competitor tooling solved this problem. Historical precedents, deprecated attempts, and lessons learned.
   - *Directive:* "Investigate prior art, related projects, historical plans in the repository, and broader ecosystem conventions. Focus on precedent: who has tried this before, what succeeded, and what failed?"

#### Execution Matrix with Lenses:
By allowing an optional `lenses=true` parameter (or defaulting to lens-oriented prompts when multiple researchers run), each researcher produces a deeply specialized report:
- `cdx`: The technical specification and code mechanics.
- `cld`: The conceptual framing and architectural tradeoffs.
- `grk`: The adversarial critique and risk analysis.
- `gem`: The broad ecosystem survey and multi-modal integration.
- `final`: A master synthesis that resolves the dialectic between the proponent and the skeptic!

### 2.2 Solving the Synthesis Bottleneck: Structured Claim Extraction

In the current `#research_swarm`, the lead researcher receives:
```markdown
The researchers' registered reports:
- wait_name=research.37.cdx label=research:202610/topic/topic__cdx.md ...
- wait_name=research.37.cld label=research:202610/topic/topic__cld.md ...
...
```
The lead is instructed: "Read each report... research the request yourself, prioritizing gaps, weak evidence, and disagreements... merge the strongest findings."

When an LLM reads 25,000 words across 5 reports in a single turn, the attention mechanism suffers from **information saturation**. Subtle disagreements are ignored, and the model defaults to producing a generic summary of the consensus.

**The Solution: Standardized Claim Emission via SASE Output Variables (`sase var`).**
If every researcher is instructed to structure its output both as prose and as a compact JSON payload stored via `sase var set`, the lead can instantly inspect an aggregated comparison matrix:

```bash
sase var set 'findings={
  "verdict": "RECOMMEND_WITH_CAVEATS",
  "confidence": 0.85,
  "top_claims": [
    "Lineage derivation is hardcoded to __a/__b in _research_lineage.py",
    "Linker parks permanently if image generation times out"
  ],
  "identified_risks": [
    "Backward compatibility breaks if file hooks reject __final.md"
  ],
  "disagreements_with_consensus": [
    "Linker should not be renamed to publisher because docs already cite linker"
  ]
}' --json
```

Because SASE automatically populates `agents.<wait_name>.<var_name>` in the lead's Jinja environment when `build_agent_output_variable_context` runs, the lead's prompt can render a machine-generated **Consensus & Conflict Dashboard**:

| Agent | Verdict | Confidence | Key Innovation / Finding | Primary Concern |
| :--- | :--- | :--- | :--- | :--- |
| `cdx` | RECOMMEND | 0.90 | Implementation in `provider.py` | Suffix regex performance |
| `cld` | CAUTION | 0.75 | Taxonomy of failure modes | In-document anchor drift |
| `grk` | SKEPTICAL | 0.60 | Over-engineering risk | Unnecessary extra token cost |
| `gem` | RECOMMEND | 0.85 | SASE var integration | Wait dependency deadlocks |

The lead can immediately see where consensus exists (instant agreement) and where conflict exists (requiring deep investigation and adjudicated rulings).

---

## 3. Taking Better Advantage of Existing SASE Features

SASE is an extraordinarily capable environment with extensive toolchains, sidecars, and state management engines. `#research_swarm` currently uses only a tiny fraction of SASE's built-in power.

### 3.1 Unlocking SASE Output Variables (`sase var` / `agents.*`)

As verified in `src/sase/agent/output_variable_context.py` and `src/sase/axe/run_agent_exec.py`:
- Any agent that runs `sase var set "<key>=<value>"` or `sase var set '<key>=<json>' --json` attaches structured metadata to its run artifacts.
- When a successor agent declares `%wait:<upstream_name>`, SASE's runner automatically executes `build_agent_output_variable_context`, collecting the upstream variables and exposing them as the reserved Jinja variable `agents`.
- In `#research_swarm`, the lead already declares `%wait` on every researcher:
  `{% for r in researchers %}%wait:research.{@1}.{{ r.short }} {% endfor %}`.

**Concrete Enhancement:**
1. Update `#research` (the sub-prompt executed by each researcher) to mandate:
   ```bash
   sase var set "summary=<one-sentence-bottom-line>"
   sase var set "verdict=<RECOMMEND|CAUTION|REJECT|EXPLORATORY>"
   sase var set 'claims=[{"claim": "...", "confidence": "high|med|low"}]' --json
   ```
2. Update the lead segment in `research_swarm.md` to render these variables:
   ```jinja
   {% if agents %}
   ### Structured Researcher Summaries
   {% for r in researchers %}
   {% set a = agents["research." ~ "@1" ~ "." ~ r.short] %}
   - **{{ r.short }}** ({{ r.provider }}): Verdict: `{{ a.verdict }}` | Summary: {{ a.summary }}
   {% endfor %}
   {% endif %}
   ```
This requires **zero core SASE changes**—the infrastructure is already 100% operational in SASE today!

---

### 3.2 Fixing and Extending SASE Artifact Lineage (`sase-15r`)

A core design principle of SASE is durable provenance: tracking which artifacts were derived from which parent artifacts.

In `src/sase/artifact_links/derive/_research_lineage.py`:
```python
_RESEARCH_KIND = "research"
_SWARM_SUFFIXES = ("__a", "__b")  # <-- BUG: Hardcoded to obsolete v1 suffixes!

def derive_research_swarm_lineage(document: DerivableDocument) -> tuple[DerivedLinkCandidate, ...]:
    ...
    stem = document.path.stem
    if stem.endswith(_SWARM_SUFFIXES):
        return ()

    candidates: list[DerivedLinkCandidate] = []
    for suffix in _SWARM_SUFFIXES:
        sibling_path = document.path.with_name(f"{stem}{suffix}{document.path.suffix}")
        if not sibling_path.is_file():
            continue
        ...
```

Because of this bug (tracked in task bead `sase-15r`), `sase artifact link suggest` and SASE's automated link graph derivations produce **zero** lineage links for modern swarms (`__cdx`, `__cld`, `__grk`, `__mus`, `__gem`).

**The Solution:**
1. In `src/sase/artifact_links/derive/_research_lineage.py`, replace `_SWARM_SUFFIXES = ("__a", "__b")` with a dynamic regex matching all `<stem>__<suffix>.md` files in the directory, while explicitly ignoring:
   - `<stem>__final.md` (which is the direct ancestor of `<stem>.md`, not a sibling draft).
   - Companion files like `*_infographic.md` or `*_infographic.png`.
   - Critique files like `<stem>__critique.md`.
2. Model the lineage chain accurately:
   - For swarms without a linker: `<name>.md` `derives-from` `<name>__<suffix>.md`.
   - For swarms with a linker: `<name>.md` `derives-from` `<name>__final.md`, and `<name>__final.md` `derives-from` `<name>__<suffix>.md`!
3. Furthermore, the linker or lead should explicitly emit durable links at creation time:
   ```bash
   sase artifact link add "research:<month>/<name>/<name>.md" derives-from "research:<month>/<name>/<name>__final.md" "published canonical report derived from lead final draft"
   ```

---

### 3.3 Eliminating the Image-to-Linker Hard-Lock Deadlock

In `research_swarm.md`:
```jinja
%if(should_run={{ run_linker }}) %id(linker, clan=research.{@1}) %m:{{ linker_model }}
%wait:research.{@1}.final {% if image %}%wait:research.{@1}.image {% endif %}
```

#### The Problem:
`%wait:research.{@1}.image` requires that `research.{@1}.image` finish with status `completed`. If the image agent fails (e.g., OpenAI/Gemini image generation API rate limit, safety filter refusal on technical diagrams, timeout, or machine crash), SASE's AXE scheduler marks the wait as unresolvable.
The linker is permanently parked. `<name>.md` is never generated. The entire research run stalls at the 95% mark, requiring manual operator intervention or tmux triage.

#### The Solution:
1. **Architectural Decoupling in XPrompt:** The linker should **only wait on `.final`**:
   `%wait:research.{@1}.final`
   To ensure the image has time to generate, either:
   - The image agent runs concurrently with or directly after the lead.
   - Or, the linker checks for the presence of `<name>_infographic.png` via filesystem check or artifact query.
2. **Fail-Soft Linker Logic:** The linker prompt already states:
   > "If the image agent completed without producing one, publish without it and say so in the final response."
   However, this prompt instruction is currently unreachable because the runner blocks at the `%wait` boundary before the linker can ever boot! Decoupling the hard wait allows the linker's existing fallback logic to execute gracefully.

---

### 3.4 Automated Downstream Actionability via SASE Beads (`/sase_new_task` / `sase bead`)

Research is useless if it stays trapped in static markdown files. The true value of agentic research in an engineering system is discovering actionable work:
- Bugs discovered in existing code.
- Missing feature abstractions.
- Technical debt or refactoring opportunities.
- Flaky tests or documentation gaps.

**Enhancement:**
Instruct the lead consolidator (`.final`) to review the synthesized report and automatically create SASE task beads for all concrete recommendations:
- The lead uses the `/sase_new_task` skill to file task beads with appropriate task types (`feature`, `bug`, `ci`, `memory`).
- The lead associates the newly created beads with the research report by recording:
  ```bash
  sase artifact link add "research:<month>/<name>/<name>.md" related "bead:<bead_id>" "actionable follow-up task discovered during research"
  ```
- This bridges the gap between *investigation* and *execution*.

---

### 3.5 Codifying Architectural Conclusions into SASE Memory Strands (`sase memory`)

When a research swarm is dispatched to resolve an architectural debate (e.g., choice of database, IPC mechanism, concurrency model, or API design), the desired outcome is often a permanent **SASE Decision Record** in `sase/memory/decisions/`.

SASE Decision Records follow a strict, immutable contract:
- Context and Claim.
- Why chosen over credible alternatives.
- Costs and drawbacks accepted.
- Concrete conditions that would reopen the decision.

**Enhancement: `#research_swarm(decision=true, ...)`**
Add an optional boolean argument `decision: bool = false` to `#research_swarm`. When `decision=true`:
- The lead researcher is instructed to draft an accompanying decision record strand under `sase/memory/decisions/<slug>.md`.
- Uses `/sase_memory_write` to propose the new decision record to the user.
- Creates an enduring architectural asset directly in the project's core memory.

---

### 3.6 Deterministic Verification Tooling vs. Fragile Ad-Hoc Bash

In the current linker prompt, the agent is instructed to validate external URLs and markdown anchors via ad-hoc bash commands:
```bash
curl -fsSL -o /dev/null --max-time 20 <url>
pandoc <file> -t html
```
Having an LLM execute a loop of 30 ad-hoc `curl` calls via `run_command` in a bash shell has several disadvantages:
- High latency and excessive provider turn overhead.
- Inconsistent error handling when encountering redirects, rate limits, or transient 403s.
- Token waste from verbose command outputs.

**Enhancement: Dedicated SASE Named Tool (`tools/verify_research_report`)**
Add a lightweight, hermetic Python verification script to `sase-research-artifacts` and register it as a SASE tool (`sase tool run research-verify <file>`):
- Deterministically parses markdown headers to verify there are no hand-numbered sections (`1.1`, `2.0`), which break Pandoc PDF numbering.
- Validates in-document anchors against GitHub-flavored markdown and pandoc rules.
- Asynchronously checks external URLs with connection pooling and a strict 5-second timeout.
- Validates that all images referenced in markdown actually exist on disk.
- Emits a clean JSON verdict that the linker or lead consumes in a single tool call.

---

## 4. Proposed New SASE Engine Features (Truly Justified)

While many improvements can be made within existing prompt and plugin boundaries, our research identified three platform-level capabilities that would significantly elevate SASE's orchestration engine.

### 4.1 Feature 1: Fail-Soft & Optional Dependency Directives (`%wait:optional(...)`)

**Problem:** SASE's `%wait` directive is currently all-or-nothing. If an upstream agent fails, cancels, or encounters an infrastructure error, all downstream agents waiting on it are irrevocably stuck. This makes complex multi-stage pipelines brittle to single-agent failures.

**Proposed Syntax:**
```
%wait:research.{@1}.final
%wait:optional(research.{@1}.image, timeout=180s)
```
or
```
%wait(research.{@1}.image, required=false)
```

**Engine Behavior:**
- When an optional dependency fails or times out, SASE's AXE scheduler does not mark the waiting agent as permanently blocked.
- Instead, it unblocks the waiting agent, injects a failure marker into the runtime environment (`wait.failures = [{"agent": "research.12.image", "error": "timeout"}]`), and permits execution to continue.
- This would benefit not only `#research_swarm`, but all fan-out/fan-in workflows across SASE (e.g. testing swarms, multi-provider code reviews).

---

### 4.2 Feature 2: Native Staged Query Decomposition (`%stage`)

**Problem:** In complex research topics, a human user often cannot know in advance how best to decompose the research request into sub-problems. Currently, all researchers receive the raw user prompt.

**Proposed Capability:**
Introduce a two-stage research swarm architecture:
1. **Stage 1 (Decomposition / Scoper):** A fast reasoning agent (`@large`) analyzes the prompt and emits a structured decomposition JSON:
   - Sub-topic 1: "Low-level Linux kernel IPC benchmarks"
   - Sub-topic 2: "Rust memory safety guarantees in shared memory"
   - Sub-topic 3: "Real-world production case studies at scale"
2. **Stage 2 (Specialist Fan-Out):** The parallel researchers are dynamically dispatched, each receiving its specific sub-topic plus the overarching context.
3. **Stage 3 (Consolidation):** The lead integrates the sub-topic answers into a cohesive master report.

**XPrompt Syntax Implementation:**
Using SASE's existing output variable binding (`agents.<decomposer>.subtopics`), Stage 2 prompts can directly index:
```jinja
{{ agents['research.{@1}.scoper'].subtopics[loop.index0] }}
```
Adding first-class `%stage` syntax would make this pattern native and declarative across SASE.

---

### 4.3 Feature 3: TUI Research Provenance Heatmap & Consensus Scoring

**Problem:** In the SASE TUI (`sase tui`), the Artifacts pane displays research markdown files as monolithic text documents. Readers cannot easily tell:
- Which parts of the report were written by Codex vs. Claude vs. Gemini.
- What claims were unanimously agreed upon vs. what claims were contentious.

**Proposed Capability:**
- **Consensus Score:** During consolidation, compute a consensus score for major claims based on the cross-researcher output variables (e.g. "80% multi-model consensus").
- **Visual Provenance Badges:** In the TUI and rendered Highlights PDF, display small marginal badges or colored indicators indicating model provenance (e.g., `[∴ cdx]` for implementation details, `[∴ cld]` for theoretical framing).
- This builds immense trust for human decision-makers reviewing research reports in Obsidian or the SASE TUI.

---

## 5. Comprehensive Ranked Improvement Roadmap

Below is the prioritized, ranked roadmap of recommendations for improving `#research_swarm`. Each item is evaluated by **Impact**, **Implementation Effort**, and **Dependencies**.

### Tier 1: Immediate High-Impact Improvements (Zero or Low Engine Work)

#### Rank 1: Introduce Orthogonal Research Lenses (`lenses=true`)
- **Impact:** **Very High**. Completely eliminates the "echo chamber" redundancy trap where 5 models write the same generic summary. Vastly increases research depth, technical precision, and adversarial risk detection.
- **Effort:** **Low**. Pure prompt engineering in `src/sase_research_artifacts/xprompts/research_swarm.md`.
- **Implementation:** Add optional `lenses: bool = true` input. When enabled, inject specialized inquiry directives (Empirical/Code, Theoretical/Pattern, Adversarial/Risk, Prior Art/Precedent) into `cdx`, `cld`, `grk`, `gem`, and `mus`.

#### Rank 2: Implement Structured Output Variable Exchange (`sase var`)
- **Impact:** **Very High**. Solves the lead consolidator's synthesis bottleneck and "lost-in-the-middle" attention fatigue. Enables automated cross-researcher comparison tables.
- **Effort:** **Low-Medium**. Uses SASE's existing, fully operational `sase var` and `agents.*` Jinja namespace.
- **Implementation:** Update `#research` to instruct models to emit `summary`, `verdict`, `claims`, and `confidence` via `sase var set`. Update the lead's segment in `research_swarm.md` to render a Markdown comparison table at the top of its prompt.

#### Rank 3: Fix Stale Artifact Lineage Deriver (`sase-15r`)
- **Impact:** **High**. Restores broken artifact link generation across the entire research corpus. Allows `sase artifact link suggest` to accurately map consolidated reports to their source drafts.
- **Effort:** **Low**. Small code edit in `src/sase/artifact_links/derive/_research_lineage.py` and unit test update in `tests/artifact_links/test_research_lineage.py`.
- **Implementation:** Replace `_SWARM_SUFFIXES = ("__a", "__b")` with dynamic suffix matching (`__cdx`, `__cld`, `__grk`, `__mus`, `__gem`), treat `__final` as parent of `<name>.md`, and ignore companion/critique files.

#### Rank 4: Un-park the Linker from Image Generation Failures
- **Impact:** **High**. Prevents whole-swarm stalls when the image generation provider rate-limits or errors.
- **Effort:** **Low**. Modify the linker's dependency in `research_swarm.md` so it does not hard-block on `.image`, or implement an asynchronous file-check fallback.
- **Implementation:** Change the linker segment's wait directive to `%wait:research.{@1}.final` (or add a bounded wait), enabling the linker's existing fallback logic ("publish without image if missing") to actually run.

#### Rank 5: Actionable Follow-Up Scaffolding via Task Beads (`sase bead`)
- **Impact:** **Medium-High**. Turns research recommendations into trackable engineering work.
- **Effort:** **Low**. Instruct the lead consolidator to invoke `/sase_new_task` for concrete action items and link them with `sase artifact link add`.
- **Implementation:** Add a post-synthesis step in the lead prompt instructing it to scaffold up to 3 high-priority follow-up task beads.

---

### Tier 2: Plugin & Tooling Enhancements (Moderate Investment)

#### Rank 6: Deterministic Report Verification Tool (`sase tool run research-verify`)
- **Impact:** **Medium-High**. Replaces slow, error-prone ad-hoc LLM `curl` and `pandoc` bash loops with a fast, deterministic checker.
- **Effort:** **Medium**. Create a Python script in `sase-research-artifacts/tools/` that checks Pandoc header levels, validates local anchors, and pools HTTP requests for URL checking.
- **Implementation:** Linker runs `sase tool run research-verify <file>` and receives an actionable diagnostic report.

#### Rank 7: Optional SASE Decision Record Drafting (`decision=true`)
- **Impact:** **Medium**. Seamlessly connects exploratory research to durable architectural memory in `sase/memory/decisions/`.
- **Effort:** **Low-Medium**. Add `decision: bool = false` to `#research_swarm`. When true, lead drafts `<slug>.md` under `sase/memory/decisions/` and submits it via `/sase_memory_write`.

#### Rank 8: Explicit Bidirectional Artifact Link Registration
- **Impact:** **Medium**. Ensures that every published report explicitly records its `derives-from` edges immediately at publish time without waiting for external link suggestion scans.
- **Effort:** **Low**. Add `sase artifact link add "research:..." derives-from "research:..."` to the linker's final steps.

---

### Tier 3: Core Platform Features (Engine Evolution)

#### Rank 9: Fail-Soft Dependency Semantics in SASE AXE Scheduler (`%wait:optional(...)`)
- **Impact:** **High**. General platform capability that prevents cascaded workflow deadlocks across all SASE swarm types.
- **Effort:** **High**. Requires changes to `sase.axe.run_agent_wait`, `run_agent_wait_deps.py`, and directive parsing in `src/sase/xprompt/`.

#### Rank 10: Dynamic Staged Query Decomposition (`%stage`)
- **Impact:** **High**. Enables automated sub-topic decomposition for highly complex, multi-faceted research prompts.
- **Effort:** **High**. Requires runner support for dynamic intermediate prompt synthesis before launching parallel worker segments.

#### Rank 11: TUI Multi-Model Consensus & Provenance Visualizer
- **Impact:** **Medium**. Visual and UX polish for human operators reviewing research in the SASE TUI Artifacts pane.
- **Effort:** **Medium-High**. Requires Textual UI extensions and metadata tagging in the artifact index.

---

## 6. Conclusion

The current `#research_swarm` xprompt is an impressive prototype that demonstrated the feasibility of multi-provider research swarms in SASE. However, its current operational model—running 5 identical prompts in parallel and dumping 25,000 words of unstructured text onto a single lead consolidator—wastes compute, encourages cognitive redundancy, and causes synthesis fatigue.

By introducing **orthogonal research lenses**, harnessing SASE's existing **`sase var` output variable architecture**, fixing the **`sase-15r` lineage deriver**, and **decoupling the linker from image deadlocks**, `#research_swarm` can be transformed into an enterprise-grade research engine that produces deeper, more rigorous, and directly actionable engineering intelligence.
