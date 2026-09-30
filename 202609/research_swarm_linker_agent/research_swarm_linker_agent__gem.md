---
create_time: 2026-09-30
updated_time: 2026-09-30
status: research
tags: [research_swarm, xprompts, file_hooks, linker_agent, infographics]
---

# Research Swarm Linker Agent Design and Integration Analysis

**Researcher:** `research.2z.gem` (Antigravity)  
**Topic:** Adding a `linker` agent to `#research_swarm`, removing the `critique` agent, embedding infographics, adding `image_model`, and auditing file-hook suffix filtering.  
**Target Codebases:** `sase-research-artifacts` linked repository and `sase` host engine.

---

## Executive Summary & Verdict

The proposal to introduce a `linker` agent to the `#research_swarm` xprompt workflow, automatically triggered whenever `linker=true` OR `image=true`, while eliminating the unused `critique` agent and exposing an explicit `image_model` parameter, is **fundamentally sound and highly valuable**. 

It directly solves the long-standing "orphaned infographic" problem across the research corpus: previously, infographics were generated after the lead consolidator finished, leaving the consolidated markdown report devoid of visual media and causing the `research-highlights` file hook to generate Obsidian Highlights PDFs without the infographic. Furthermore, having a dedicated refinement pass standardizes research reports into unnumbered markdown sections and adds local anchor links without authoring an unwanted Table of Contents (TOC).

However, **the proposal contains one critical technical misconception regarding file-hook suffix filtering that would introduce a severe regression if implemented as described**:
- The prompt suggests adding `__final` to the "list of suffices the corresponding file hook uses to ignore certain research files."
- In `sase_research_artifacts.provider`, the file hook does **not** maintain a list of filename suffixes. Instead, its `path_globs` filter uses the blanket negative patterns `!20*/*__*.md` and `!20*/*/*__*.md`. Therefore, any file named `<name>__final.md` is **already automatically ignored** by the file hook.
- Meanwhile, the only suffix list in the provider is `_SWARM_RESEARCHER_SUFFIXES = ("cdx", "cld", "grk", "mus", "gem")`, which generates the `agent_name_globs` filter (`!research.*.<suffix>`). If `final` were added to that list, the hook would veto any file added by `research.*.final`. This would catastrophically break all default swarm runs (`linker=false` and `image=false`), because when the linker does not run, `research.*.final` is the sole author of the final `<name>.md` publication report.

With this misconception corrected and five other necessary adjustments incorporated (including introducing a `linker_model` parameter, preventing infographic filename pollution like `<name>__final_infographic.png`, and establishing strict anti-summarization guardrails), the plan is strongly recommended for implementation.

---

## Current Architecture & Problem Statement

### 1. The Existing `#research_swarm` Workflow
The `#research_swarm` xprompt in `sase-research-artifacts` orchestrates a multi-agent pipeline:
1. **Parallel Researchers:** Depending on provider flags, up to five independent agents (`cdx`, `cld`, `grk`, `mus`, `gem`) run simultaneously. Each writes a self-named draft at the month root: `$(sase repo path research --ensure)/$(date +%Y%m)/<topic>__<suffix>.md`.
2. **Consolidating Lead (`.final`):** Waits on all researchers. It moves each draft into `<month-dir>/<name>/<name>__<suffix>.md`, researches gaps, and writes the consolidated report to `<name>/<name>.md`.
3. **Optional Infographic Agent (`.image`):** Runs if `image=true`. It forks the lead's conversation (`#fork:research.{@1}.final #research/image`) and uses the hardcoded model alias `@image` to generate `<source-stem>_infographic.png`.
4. **Optional Critique Agent (`.critique`):** Runs if `critique=true` with model `critique_model` (default `@xlarge`). It evaluates `<name>.md` and writes `<name>__critique.md`.

```text
[Current Flow]
cdx ──┐
cld ──┼─> final (<name>.md) ─┬─> [File Hook Triggers Highlights PDF]
grk ──┤                     ├─> image (<name>_infographic.png) [Orphaned!]
mus ──┤                     └─> critique (<name>__critique.md)
gem ──┘
```

### 2. The Orphaned Infographic Problem
An inspection of the durable research corpus in `sase/repos/research/202609/` reveals over 45 generated infographics. However, essentially none of the corresponding consolidated markdown reports embed their infographic. Because the image agent runs after the lead consolidator has completed its turn:
- The lead agent has already finalized and committed `<name>/<name>.md`.
- No downstream agent updates `<name>/<name>.md` to reference `![Infographic](<name>_infographic.png)`.
- The `research-highlights` file hook executes immediately upon the commit of `<name>.md`, converting the markdown into an Obsidian Highlights PDF before the infographic exists and without any image embedding.
- As a result, the reading queue in Obsidian receives a purely text-based PDF, while the high-value visual infographic remains a detached, unreferenced asset.

### 3. Critique Agent Redundancy
The `critique` agent is rarely if ever invoked in practice. When enabled, it consumes substantial tokens and execution slots to write `<name>__critique.md`, an artifact that is almost never consulted during downstream implementation planning. Removing it simplifies the swarm structure and frees queue capacity.

---

## Critique of the Proposed Plan

### Strengths
1. **Solves the Image Orphan Pipeline:** By triggering the `linker` agent whenever `image=true`, the pipeline guarantees that any generated infographic is physically inserted into the markdown document prior to publication.
2. **Standardizes Publication Format:** Lead researchers frequently produce varied formatting (e.g., numbered headers like `1.1 Background`, inconsistent callouts). A dedicated linker agent unifies the report into clean, unnumbered markdown headings (`## Section`, `### Subsection`).
3. **Local Navigation Without TOC Clutter:** Complex reports often exceed 3,000 words. Injecting in-text contextual jump links (`[see Findings](#findings)`) without generating an intrusive Table of Contents improves reading ergonomics in Obsidian and GitHub.
4. **Exposing `image_model`:** Replaces hardcoded `%model:@image` with an explicit configurable parameter, allowing users to override the model or use faster/cheaper vision models.

### Vulnerabilities & Technical Gotchas

#### 1. The File Hook Suffix Trap
The proposal states:
> *"When the linker agent will be run, the lead agent should be instructed to use the `__final` research markdown filename suffix. This suffix should be added to the list of suffices the corresponding file hook uses to ignore certain research files."*

Let us trace how `RESEARCH_HIGHLIGHTS_HOOK_SPEC` in `src/sase_research_artifacts/provider.py` evaluates events:
```python
"filters": {
    "sidecars": ["research"],
    "producers": ["commit", "sdd", "finalizer"],
    "path_globs": [
        "20*/**/*.md",
        "!20*/*__*.md",      # Excludes depth-1 drafts
        "!20*/*/*__*.md",    # Excludes depth-2 drafts and critique
        *_COMPANION_MARKDOWN_EXCLUDE_GLOBS,
    ],
    "agent_name_globs": [
        f"!research.*.{suffix}" for suffix in _SWARM_RESEARCHER_SUFFIXES
    ],
    "ops": ["ADD"],
}
```
Two critical observations emerge:
1. **`path_globs` uses a wildcard pattern, not a suffix list:** The pattern `!20*/*/*__*.md` excludes **any** file in a topic directory that contains `__`. When the lead researcher writes `<name>/<name>__final.md`, it matches `*/*__*.md` and is **automatically filtered out**. No file hook modification is required for path filtering.
2. **`_SWARM_RESEARCHER_SUFFIXES` is for agent names, not file paths:** `_SWARM_RESEARCHER_SUFFIXES = ("cdx", "cld", "grk", "mus", "gem")` defines agent name vetoes (`!research.*.cdx`, etc.). If `final` is appended to `_SWARM_RESEARCHER_SUFFIXES`:
   - `agent_name_globs` will contain `!research.*.final`.
   - When a user runs `#research_swarm` with `linker=false` and `image=false`, `research.*.final` writes `<name>/<name>.md`.
   - The file hook will check `agent_name_globs` against `event.agent_name == "research.<clan>.final"`.
   - Because `!research.*.final` matches, **the file hook will reject the event**.
   - **Result:** Default swarm runs will silently stop generating Highlights PDFs altogether.

#### 2. Image Agent Fork Stem Pollution
The `#research/image` xprompt reads:
```markdown
Generate an infographic that illustrates the main points made in this research markdown
file. Write the image to `<source-stem>_infographic.png` in the same directory.
```
In `research_swarm.md`, the image segment forks the lead: `#fork:research.{@1}.final #research/image`.
If the lead's output file is `<name>/<name>__final.md`, its source stem is `<name>__final`.
Without explicit instructions, `#research/image` will derive the filename `<name>__final_infographic.png`.
This breaks established repo conventions where infographics are named `<name>_infographic.png` (matching the parent folder `<name>/`). The prompt must explicitly instruct the image agent to strip the `__final` suffix when determining the image target name.

#### 3. Critical Path Latency & Queue Budget
Previously, `image` and `critique` ran in parallel after `final`.
Under the new design, when `image=true`, the execution becomes strictly sequential:
$$\text{Researchers} \longrightarrow \text{Lead (.final)} \longrightarrow \text{Image (.image)} \longrightarrow \text{Linker (.linker)}$$
This adds a third sequential stage to the critical path. If an image generation takes 45 seconds and the linker takes 60 seconds, total swarm turnaround time increases by ~100–120 seconds. This is an acceptable tradeoff for correct document assembly, but users should be aware that `image=true` or `linker=true` extends runtime.

#### 4. Semantic Drift and Information Loss Risk
The linker agent is instructed:
> *"The new file should duplicate the meaning and intent of the lead's document. The linker agent should NOT attempt to do its own research."*

In LLM-based refactoring agents, "refining structure" is the #1 vector for accidental summarization. LLMs frequently collapse detailed tables, omit nuanced qualifications, drop code blocks, or smooth over technical tensions found by the lead. The linker agent prompt requires strict negative constraints forbidding summarization.

---

## Justified Adjustments to Requirements

Based on the technical critique, the following 6 adjustments are incorporated:

| # | Proposed Requirement | Identified Issue | Justified Adjustment |
|---|---|---|---|
| 1 | Add `__final` to file hook suffix list | Hook uses `path_globs` wildcard (`!*/*__*.md`); suffix list is for agent vetoes. Adding `final` breaks default runs. | **Do NOT modify `_SWARM_RESEARCHER_SUFFIXES` in `provider.py`.** Rely on the existing `!20*/*/*__*.md` glob which already ignores `<name>__final.md`. |
| 2 | Expose `image_model` only | Misses model configurability for the new `linker` agent. | **Add `linker_model` parameter** (defaulting to `@xlarge` to ensure high-fidelity text preservation). |
| 3 | Image agent runs after lead | Image agent deriving stem from `<name>__final.md` produces `<name>__final_infographic.png`. | **Add explicit image naming instruction** in the image segment: author `<name>_infographic.png`, omitting `__final`. |
| 4 | Linker discovers lead file | If lead does not register `<name>__final.md`, `wait.artifacts` will not contain it. | **Instruct lead agent to run `sase artifact create` on `<name>__final.md`** whenever `run_linker` is true. |
| 5 | Linker refines document | Risk of aggressive LLM summarization and loss of technical substance. | **Include strict anti-summarization guardrails** in the linker prompt: forbid shortening, preserve all data/tables/quotes. |
| 6 | Add local jump links | Fragile markdown anchors; risk of agent hallucinating a TOC. | **Specify GitHub/Obsidian slug conventions** (`#section-name`) and provide an explicit negative constraint: **NO TOC / outline**. |

---

## Detailed Implementation Specification

### 1. Changes to `sase-research-artifacts`

#### A. Frontmatter Inputs (`src/sase_research_artifacts/xprompts/research_swarm.md`)
Remove `critique` and `critique_model`. Add `linker`, `linker_model`, and `image_model`:

```yaml
  - name: image
    type: bool
    default: false
    description: Generate an infographic after the lead researcher finishes.
  - name: image_model
    type: word
    default: "@image"
    description:
      Model alias or provider model for the optional `<clan>.image` infographic agent.
  - name: linker
    type: bool
    default: false
    description:
      Run a linker agent to refine the report's structure, embed the infographic,
      and validate/add cross-links. Always runs when `linker=true` or `image=true`.
  - name: linker_model
    type: word
    default: "@xlarge"
    description:
      Model alias or provider model for the `<clan>.linker` agent.
```

#### B. Template Layout Logic
Define `run_linker` and update the layout visualization:
```jinja2
{%- set run_linker = linker or image -%}
{%- set ns = namespace(layout_lines=["<month-dir>/<name>/"]) -%}
{%- for r in researchers -%}
{%- set _ = ns.layout_lines.append("├── <name>__" ~ r.short ~ ".md") -%}
{%- endfor -%}
{%- if run_linker -%}
{%- set _ = ns.layout_lines.append("├── <name>__final.md") -%}
{%- if image -%}
{%- set _ = ns.layout_lines.append("├── <name>_infographic.png") -%}
{%- endif -%}
{%- set _ = ns.layout_lines.append("└── <name>.md") -%}
{%- else -%}
{%- set _ = ns.layout_lines.append("└── <name>.md") -%}
{%- endif -%}
{%- set layout_body = ns.layout_lines | join("\n") -%}
```

#### C. Lead Researcher Step Instructions
In the lead researcher segment (`research.{@1}.final`):
```jinja2
{%- if run_linker %}
4. Write the consolidated report to `<name>/<name>__final.md`: merge the strongest findings
   from every report above and your own research, resolve conflicts, cut duplication,
   and add missing critical context without unnecessary length. Do NOT write `<name>/<name>.md`;
   the downstream linker agent will produce the final `<name>/<name>.md` file.

5. After the write succeeds, register the consolidated report as a durable snapshot so
   the downstream linker agent, `research.{@1}.linker`, can find it in `wait.artifacts`:

   sase artifact create -p "<absolute-report-path>" -l "research:<repo-relative-report-path>"

   Use the report's actual absolute path and its path relative to the research repo root,
   for example `research:202609/<name>/<name>__final.md`. Do not pass `--move`.
   If registration fails, report that failure; do not report the task as fully complete.
{%- else %}
4. Write the consolidated report to `<name>/<name>.md`: merge the strongest findings
   from every report above and your own research, resolve conflicts, cut duplication,
   and add missing critical context without unnecessary length.
{%- endif %}
```

#### D. Image Agent Segment
Update the image segment to use `image_model` and enforce the canonical image target:
```jinja2
%if(should_run={{ image }}) %id(image, clan=research.{@1}) %m:{{ image_model }}
%wait:research.{@1}.final %q({% if runners is not none %}{{ runners }}{% else %}1.5x{% endif %}, w=0.25{% if priority is not none %}, priority={{ priority }}{% endif %}) #fork:research.{@1}.final #research/image

When saving the infographic, write the image to `<name>_infographic.png` in the report's parent directory, omitting any `__final` suffix from the image filename.
```

#### E. Linker Agent Segment (Replacing Critique)
Author the new `linker` segment:
```jinja2
%if(should_run={{ run_linker }}) %id(linker, clan=research.{@1}) %m:{{ linker_model }}
%wait:research.{@1}.final {% if image %}%wait:research.{@1}.image {% endif %}%q({% if runners is not none %}{{ runners }}{% else %}1.5x{% endif %}, w=0.25{% if priority is not none %}, priority={{ priority }}{% endif %})

You are the linker and refinement agent for a research swarm. The lead researcher,
`research.{@1}.final`, has synthesized the swarm's findings into a consolidated report ending
in `__final.md`. Your job is to transform this draft into the final published research report
`<name>/<name>.md`.

Sase derives your plan's links from the artifacts you read this turn; use `sase artifact read`
for context you actually use.

The lead researcher's registered reports:

{% raw %}{% for a in wait.artifacts if a.kind == "markdown" and a.label and a.label.startswith("research:") %}
- wait_name={{ a.wait_name }} label={{ a.label }} source_path={{ a.source_path }} path={{ a.path }} ref={{ a.ref }}
{% endfor %}{% endraw %}

Steps:

1. Identify the lead's consolidated report: exactly one entry with `wait_name`
   `research.{@1}.final` whose label has the form `research:<YYYYMM>/<name>/<name>__final.md`.
   Open the research repo with `/sase_repo`, then read the report through its canonical
   research reference using `sase artifact read`. Do not read predecessor chat transcripts.
2. Review the lead's report. Your goal is structural refinement and polish:
   - Duplicate the meaning, technical substance, arguments, evidence, and conclusions of the
     lead document with complete fidelity. Do NOT attempt to conduct your own research.
   - Do NOT summarize or condense the content. Preserve all data, tables, code snippets,
     citations, caveats, and detailed discussions.
   - Structure the document using clean, hierarchical, UNNUMBERED markdown headings
     (`# Title`, `## Heading`, `### Subheading`). Strip section numbers (e.g. change
     `## 1. Executive Summary` to `## Executive Summary`).
   - Do NOT generate a Table of Contents (TOC), bulleted outline of sections, or document index.
{%- if image %}
3. An infographic was generated for this research. Check for `<name>_infographic.png` (or
   `<name>__final_infographic.png`) in the report directory. Embed the image near the top of the
   report (directly after the introductory summary/verdict or in an Overview section) using
   standard markdown: `![Infographic](<image-filename>)`. If no image exists, do not insert a broken link.
{%- endif %}
4. Validate and enrich document links:
   - Ensure all existing external URLs and SASE references in the lead's document are well-formed.
   - Add local cross-reference jump links where sections naturally reference one another (e.g.,
     `[see Recommendation](#recommendation)`). Ensure anchor slugs match standard GitHub/Obsidian
     slugification (lowercase, hyphens for spaces, punctuation stripped).
5. Write the final published report to `<name>/<name>.md` in the same directory as the lead's
   report. Mirror the frontmatter conventions (`create_time`, `updated_time`, `status`, `tags`).
   Create it without overwrite: if the file already exists, stop and report the collision visibly.
6. After the write succeeds, register the report as a durable snapshot so the file hook and SASE
   indexing pick it up:

   sase artifact create -p "<absolute-report-path>" -l "research:<repo-relative-report-path>"

   Use the report's actual absolute path and its path relative to the research repo root,
   for example `research:202609/<name>/<name>.md`. Do not pass `--move`.
```

---

## File Hook Verification & Test Strategy

### Why `provider.py` Requires No Code Changes
In `tests/test_filters.py`, verify the glob behavior:
- `path_globs` has:
  ```python
  "!20*/*__*.md",
  "!20*/*/*__*.md",
  ```
- Any file matching `202609/topic/topic__final.md` matches `!20*/*/*__*.md` and is filtered out.
- The file hook triggers on `ADD` of `202609/topic/topic.md`.
- Because `research.*.linker` is NOT in `agent_name_globs`, the commit by the linker agent will successfully pass the filter and trigger `research-highlights`.
- When `linker=false` and `image=false`, `research.*.final` commits `202609/topic/topic.md`. Since `research.*.final` is NOT in `agent_name_globs`, it also triggers `research-highlights`.

### Test Suite Updates (`tests/test_xprompt_loading.py`)
1. **Remove Critique Tests:** Remove assertions verifying `critique` in segments and `test_research_swarm_image_plus_critique_run_in_parallel`.
2. **Add Linker Tests:**
   - `test_research_swarm_defaults_omit_linker()`: Verify 3 segments (`cdx`, `cld`, `final`).
   - `test_research_swarm_linker_true_adds_linker_segment()`: Verify 4 segments (`cdx`, `cld`, `final`, `linker`).
   - `test_research_swarm_image_true_triggers_linker()`: Verify 5 segments (`cdx`, `cld`, `final`, `image`, `linker`).
   - `test_research_swarm_image_model_override()`: Verify `%m:codex/gpt-5.6-sol` in the image segment when `image_model="codex/gpt-5.6-sol"`.
   - `test_research_swarm_wait_chain()`: Verify `linker` waits on `image` when `image=true`, and waits on `final` when `image=false`.
3. **Filter Test (`tests/test_filters.py`):**
   Add `"202608/widgets/widgets__final.md"` to `_DEPTH_2_DRAFTS` to guarantee regression prevention.

---

## Summary Comparison Matrix

| Dimension | Existing System | Bryan's Proposed Plan | Recommended Solution |
|:---|:---|:---|:---|
| **Infographic Embedding** | Orphaned (never referenced in markdown) | Embedded by `linker` | Embedded by `linker`, canonical `<name>_infographic.png` enforced |
| **Critique Agent** | Present (rarely used, dead weight) | Removed | Removed |
| **Image Model** | Hardcoded `@image` | Configurable `image_model` | Configurable `image_model` (default `@image`) |
| **Linker Model** | N/A | Not specified | Configurable `linker_model` (default `@xlarge`) |
| **Trigger Logic** | N/A | `linker=true` OR `image=true` | `linker or image` |
| **Lead Output** | `<name>.md` | `<name>__final.md` when linker runs | `<name>__final.md` registered via `sase artifact create` |
| **File Hook Suffixes** | Excludes `*__*.md` via globs | Add `final` to suffix list | **Leave `provider.py` suffix list untouched**; rely on existing globs |
| **Formatting Rules** | Unstructured | Unnumbered sections, no TOC | Unnumbered sections, no TOC, strict anti-summarization directive |

---

## Conclusion & Next Steps
The proposed feature represents a marked improvement in the quality, visual appeal, and navigability of SASE research artifacts. By avoiding the file-hook suffix trap, specifying `linker_model`, enforcing proper artifact registration for discovery, and ensuring that image naming remains clean and unpolluted, the implementation will be robust, backward-compatible, and immediately beneficial.
