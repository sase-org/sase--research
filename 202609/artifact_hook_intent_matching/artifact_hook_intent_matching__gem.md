---
create_time: 2026-09-26
updated_time: 2026-09-26
status: draft
tags:
  - file-hooks
  - artifacts
  - research
  - xprompts
---

# Robust Artifact File Hook Matching: Analysis, Critique, and Architecture

**Researcher:** `research.gem` (Gemini 3.8 Flash High)  
**Scope:** `sase` workspace #22 (`sase-org/sase`), linked `sase-research-artifacts` plugin, and external tool integration (`bob highlights create`).  
**Topic:** Evaluating and designing a reliable, robust approach to matching artifact deliverables for file hook execution, comparing xprompt-set environment variables against first-class artifact metadata and structured hook filtering.

---

## 1. Executive Summary & Verdict

### 1.1 The Problem
Today, file hooks that target research reports and artifact deliverables rely on brittle heuristics. In `sase-research-artifacts`, the `research-highlights` file hook (which runs `bob highlights create --include-id`) must distinguish between unfinished intermediate researcher drafts and final consolidated reports. To prevent spawning unwanted Highlights PDFs for every swarm member's draft, the provider currently maintains a fragile web of negative vetoes:
- **Negative path globs:** `"!20*/*__*.md"`, `"!20*/*/*__*.md"`
- **Negative agent name globs:** `["!research.*.cdx", "!research.*.cld", "!research.*.grk", "!research.*.mus", "!research.*.gem"]`

Every time a new swarm provider is introduced (as recently seen in commit `f524532` when `grk`, `mus`, and `gem` were added), both the provider specification and documentation must be manually modified to enumerate new negative exclusions. Furthermore, this negative filtering conflates agent naming and directory depth with artifact intent.

### 1.2 Critique of the Proposed Plan (Environment Variable via `#research`)
The user's proposed plan suggests:
1. Having the `#research` xprompt set an environment variable by default (e.g., `SASE_FILE_HOOK_ENABLED=1`).
2. Supporting an override argument in `#research` (e.g., `#research(file_hooks=false)`) so swarm researcher agents running before the lead researcher can suppress the environment variable.
3. Matching file hooks based on this environment variable.

**Verdict: The underlying motivation is sound, but relying on ambient environment variables set by `#research` is architecturally problematic and fails to account for critical orchestration realities.**

Specifically:
1. **Host-Owned Commit Finalization Disconnect:** Commit-time file hooks (`producers: [commit, sdd, finalizer]`) are executed by host finalizers in the host process *after* the agent turn has exited. Ambient environment variables set within an agent process or during prompt expansion are not automatically replayed into the host commit finalizer unless explicitly stored in a turn declaration.
2. **`#research` XPrompt Format Constraint:** `#research` is currently a Markdown prompt part (`research.md`). Under SASE's core frontmatter schema, Markdown prompt parts do *not* support an `environment:` block; only `.yml` workflows support `environment:`.
3. **The `#research_swarm` Orchestration Blindspot:** In `#research_swarm`, the lead researcher (`research.{@1}.final`) **does not invoke `#research`**. Its prompt instructions are defined inline. If `#research` is the sole mechanism setting the environment variable, the lead researcher will never have the variable set.
4. **The Consolidated Report Artifact Creation Gap:** In `research_swarm.md`, the lead researcher only runs `sase artifact create` when `critique: true` (an opt-in flag defaulting to `false`). When `critique: false`, the lead researcher never registers the consolidated report with `sase artifact create` at all.
5. **Stored Path Hash Pollution:** When a file hook triggers via `producer: artifact`, `sase` passes the durable content-addressed copy (`stored_path`, e.g. `report-0123456789ab.md`) containing a 12-character SHA256 digest suffix. External tools like Bob derive note titles and marker IDs directly from this filename, polluting the Obsidian vault.

### 1.3 Recommended Solution (Three-Layer Architecture)
Rather than relying on ambient environment variables, SASE should adopt **first-class, declarative artifact intent**:
1. **Short-Term (Plugin & Swarm Fix):**
   - In `research_swarm.md`: Make the lead researcher *always* register the consolidated report via `sase artifact create` (not just when `critique` is enabled).
   - In `provider.py`: Invert the brittle negative filtering. Instead of enumerating negative agent names, use positive filtering (e.g., matching the lead role `*.final` or requiring the absence of `__` suffixes).
2. **Medium-Term (First-Class Artifact Metadata):**
   - Enhance `sase artifact create` with a `--tag <tag>` (or `--intent <intent>`) option (e.g., `sase artifact create -p <path> -l <label> --tag final-report`).
   - Add `tags` and `properties` to `FileHookFilters` in `src/sase/config/file_hooks.py`.
   - Update `dispatch_artifact_file_hook_event` in `src/sase/file_hooks/artifact.py` to pass the clean `source_path` (when `--move` was not requested) instead of forcing the hashed `stored_path`.
3. **Long-Term (If Environment Variables Are Kept as an Escape Hatch):**
   - Model the environment variable as an explicit `SASE_ARTIFACT_INTENT=report` variable injected via workflow definitions, paired with explicit turn-level propagation into finalizer metadata.

---

## 2. Deep Dive: Current Architecture & State Analysis

To understand why matching artifact files is challenging today, we must examine the intersection of three subsystems: file hook configuration, event dispatch/execution, and research artifact creation.

### 2.1 File Hook Configuration and Filtering (`src/sase/config/file_hooks.py`)
File hooks are configured in `sase.yml` or contributed by plugins via the `sase_file_hooks` entry point. Each hook specifies an event-matching filter via `FileHookFilters`:

```python
@dataclass(frozen=True)
class FileHookFilters:
    projects: tuple[str, ...] | None = None
    sidecars: tuple[str, ...] | None = None
    path_globs: tuple[str, ...] | None = None
    agent_name_globs: tuple[str, ...] | None = None
    ops: tuple[FileHookOp, ...] | None = None
    causes: tuple[str, ...] | None = None
    producers: tuple[FileHookProducer, ...] | None = None
```

The supported producers (`FileHookProducer`) are:
- `"commit"`: VCS commit events captured during workspace commits.
- `"sdd"`: Software Design Document / structured store commits.
- `"finalizer"`: Host-owned post-agent turn reconciliation commits.
- `"artifact"`: Explicit artifact creation via `sase artifact create`.
- `"dispatch"`: Manual or programmatic event replay.

Event matching is evaluated in `hook_matches_event()`:
```python
def hook_matches_event(
    hook: FileHookConfig,
    event: FileHookEvent,
    *,
    producer: FileHookProducer | None = None,
) -> bool:
    filters = hook.filters
    if filters.projects is not None and event.project not in filters.projects:
        return False
    if filters.sidecars is not None and event.sidecar_role not in filters.sidecars:
        return False
    if filters.ops is not None and event.op not in filters.ops:
        return False
    if filters.producers is not None and (
        producer is None or producer not in filters.producers
    ):
        return False
    if event.cause != "user" and event.cause not in (filters.causes or ()):
        return False
    if filters.path_globs:
        rel_path = event.rel_path.replace("\\", "/").removeprefix("./")
        if not _glob_matches(filters.path_globs, rel_path):
            return False
    return not filters.agent_name_globs or _glob_matches(
        filters.agent_name_globs,
        event.agent_name or "",
    )
```

Notice the critical limitations of `FileHookFilters` today:
1. **No metadata or tag matching:** There is no field for artifact kind, artifact label, tags, or frontmatter properties.
2. **No environment variable matching:** There is no mechanism to filter by the presence or value of an environment variable.
3. **Strict path and name orientation:** The only discriminators beyond repository kind and producer are `path_globs` and `agent_name_globs`.

### 2.2 The Two Producers: Commit vs. Artifact

#### 2.2.1 Producer `commit` (`src/sase/file_hooks/commit.py`)
- Emitted when changes are committed to a repository (primary or sidecar).
- The path passed to the hook command is the committed file path in the repository checkout:
  `abs_path = str(Path(repo_root) / rel_path)`
- Attribution (`agent_name`) is resolved from the agent identity running the commit finalizer.
- **Limitation:** Commits only occur at the end of the turn. If an agent creates intermediate files or artifacts that are untracked by Git, commit hooks never see them. Furthermore, in a swarm, each agent's finalizer creates a commit in the research sidecar.

#### 2.2.2 Producer `artifact` (`src/sase/file_hooks/artifact.py`)
- Emitted during an agent's turn when `sase artifact create` is executed.
- `capture_artifact_file_event(source_path)` captures the original `rel_path` and `sidecar_role`.
- `store_explicit_artifact_file()` copies the source file into durable storage:
  `~/.sase/artifacts/agents/<project>/<timestamp>/<stem>-<sha256[:12]>.<ext>`
- `dispatch_artifact_file_hook_event()` replaces `abs_path` with the stored content-addressed path:
  ```python
  event = CapturedFileEvent(
      abs_path=str(Path(stored_path).expanduser().resolve()),
      ...
  )
  ```
- **Limitation:** The command executed by the runner (`runner.py`) receives `run['abs_path']`, which is the stored path containing the content hash suffix.

### 2.3 The Case Study: `research-highlights`
In `sase-research-artifacts`, the `research-highlights` hook specification is configured as follows:

```python
# src/sase_research_artifacts/provider.py
RESEARCH_HIGHLIGHTS_HOOK_SPEC: Mapping[str, Any] = {
    "schema_version": 1,
    "provider": "research-highlights",
    "required": ["command"],
    "file_hook": {
        "description": (
            "Render new research reports into Highlights PDFs for the Obsidian "
            "reading queue."
        ),
        "filters": {
            "sidecars": ["research"],
            "producers": ["commit", "sdd", "finalizer"],
            "path_globs": [
                "20*/**/*.md",
                "!20*/*__*.md",
                "!20*/*/*__*.md",
                *_COMPANION_MARKDOWN_EXCLUDE_GLOBS,
            ],
            "agent_name_globs": [
                f"!research.*.{suffix}" for suffix in _SWARM_RESEARCHER_SUFFIXES
            ],
            "ops": ["ADD"],
        },
        "timeout": "120s",
    },
}
```

Notice why `producer: artifact` was excluded:
As documented in `sase-research-artifacts/docs/configuration.md` (lines 75–78):
> *"The producer restriction keeps committed-file routes and finalizer repair while skipping artifact-copy dispatch. Artifact dispatch executes against durable content-addressed copies whose basenames can carry digest suffixes, which would leak into Bob's derived PDF basename and marker id."*

Because `research-highlights` is forced to use commit-time hooks, it must deal with all commits landing in the `research` sidecar. In a research swarm, this includes:
1. Swarm researcher `cdx` commits `202609/topic__cdx.md`.
2. Swarm researcher `cld` commits `202609/topic__cld.md`.
3. Swarm researcher `grk` commits `202609/topic__grk.md`.
4. Swarm researcher `mus` commits `202609/topic__mus.md`.
5. Swarm researcher `gem` commits `202609/topic__gem.md`.
6. Lead researcher moves drafts into `202609/topic/` and commits `202609/topic/topic.md`.
7. Optional critique agent commits `202609/topic/topic__critique.md`.

To prevent generating 7 Highlights PDFs instead of 1, the hook author had to write both path vetoes (`!20*/*__*.md`, `!20*/*/*__*.md`) AND agent name vetoes (`!research.*.cdx`, `!research.*.cld`, etc.).

---

## 3. In-Depth Critique of the Proposed Plan

The user's concept is to introduce an environment variable set by `#research` by default, with an override argument to suppress it for preliminary swarm researchers.

Let us evaluate this proposal across technical, architectural, and operational dimensions.

### 3.1 Point 1: Lifecycle and Persistence Failure for Commit-Time Hooks
If the hook continues to use `producers: [commit, sdd, finalizer]`:
- An agent executes in its own process sandbox (or container/subshell).
- When the agent finishes its turn, it calls `/sase_final` and submits a declaration manifest (`sase final submit`).
- The agent process terminates.
- The host runner takes over and runs host finalizers (such as `builtin@commit`), which commits the working tree changes in the sidecar repo.
- The host runner calls `reconcile_commit_file_hooks()` in `src/sase/finalizers/commit_validation.py`.
- **The host finalizer does NOT retain arbitrary environment variables that were set inside the agent process or during prompt template expansion.**

Unless SASE is modified to capture, persist, and replay arbitrary environment variables across the agent-host boundary, **commit-time file hooks cannot inspect environment variables set by an xprompt.**

### 3.2 Point 2: XPrompt Type Mismatch (`.md` vs. `.yml`)
In SASE, xprompts come in two varieties:
1. **Markdown Prompt Parts (`.md`):** Simple text templates with YAML frontmatter. Frontmatter fields are defined in `src/sase/xprompt/prompt_frontmatter.py`:
   `_FIELD_ORDER = ("name", "description", "tags", "input", "xprompts", "skill", "snippet")`
   Markdown frontmatter does **not** support an `environment:` mapping. Unknown fields are parked in `extras` and ignored by the execution engine.
2. **Workflows (`.yml`):** Multi-step workflows defined in YAML. Workflows explicitly support an `environment:` mapping:
   ```yaml
   environment:
     SASE_COMMIT_METHOD: create_commit
   ```
   During prompt expansion in `src/sase/xprompt/workflow_executor_steps_embedded_expand.py`, `environment:` entries are rendered and injected into `os.environ`.

Currently, `#research` (`src/sase_research_artifacts/xprompts/research.md`) is a **Markdown prompt part**.
To allow `#research` to declare environment variables, one of the following must occur:
- `#research.md` must be rewritten as a `#research.yml` workflow.
- SASE core frontmatter schema (which lives in Rust in `sase-core`!) must be extended to parse and validate `environment:` in Markdown frontmatter, and `xprompt_to_workflow()` must map it.

### 3.3 Point 3: The `#research_swarm` Orchestration Blindspot
Let us examine `src/sase_research_artifacts/xprompts/research_swarm.md`.
The swarm is generated as a multi-prompt fan-out:
- Segment 1: `cdx` runs `{{ prompt }} #research(suffix=cdx)`
- Segment 2: `cld` runs `{{ prompt }} #research(suffix=cld)`
- Segment 3: `grk` runs `{{ prompt }} #research(suffix=grk)`
- Segment 4: `mus` runs `{{ prompt }} #research(suffix=mus)`
- Segment 5: `gem` runs `{{ prompt }} #research(suffix=gem)`
- Segment 6: `final` (Lead Researcher) runs:
  ```jinja
  %clan(research.{@1}, tribe=research, summary=...) %id:research.{@1}.final %m:{{ lead_model }}
  ...
  1. From the registered reports above, identify exactly one report per expected suffix...
  2. Research the request yourself...
  3. Pick a descriptive stem <name>... move each report inside it...
  4. Write the consolidated report to <name>/<name>.md...
  ```
- Segment 7: Optional `image` agent.
- Segment 8: Optional `critique` agent.

**Critical observation:** The lead researcher **does not invoke `#research`**!
If `#research` sets an environment variable, that environment variable will be set for a solo researcher running `sase run "topic" #research`. It could be suppressed for `cdx`/`cld` by passing an argument like `#research(suffix=cdx, file_hooks=false)`.
**However, the lead researcher will NOT have the environment variable set**, because the lead researcher never calls `#research`!
To make this work, `research_swarm.md` would have to duplicate the environment variable injection specifically in the lead researcher's segment definition.

### 3.4 Point 4: The Lead Researcher Artifact Creation Omission
In `research_swarm.md`, let us look at how the consolidated report is saved:
```jinja
4. Write the consolidated report to `<name>/<name>.md`: merge the strongest findings
   from every report above and your own research, resolve conflicts, cut duplication,
   and add missing critical context without unnecessary length.
{%- if critique %}

5. After the write succeeds, register the consolidated report as a durable snapshot so
   the critique agent, `research.{@1}.critique`, can find it:

   sase artifact create -p "<absolute-report-path>" -l "research:<repo-relative-report-path>"
{%- endif %}
```
If `critique` is `false` (the default!), **the lead researcher never runs `sase artifact create`!**
The lead researcher merely writes the file to the research sidecar checkout and finishes the turn. The file is only committed at the end of the turn by the host finalizer.
Therefore, if file hooks are switched to trigger on artifact creation (`producer: artifact`), **no file hook will ever trigger on the consolidated report in a standard research swarm!**

### 3.5 Point 5: Ambient Process State vs. Discrete Deliverables
Environment variables are ambient and process-wide. If an agent creates:
1. A scratch/debug Markdown file,
2. An infographic companion file,
3. A draft summary,
4. A final report,

all four operations execute in the same process environment. An environment variable like `SASE_FILE_HOOK_ENABLED=1` cannot distinguish between these deliverables.

Furthermore, in Jinja template expansion for YAML workflows:
```python
for key, value_template in p.workflow.environment.items():
    rendered = render_template(value_template, p.embedded_context)
    os.environ[key] = rendered
```
If an input sets `file_hooks=false`, setting `value_template: "{{ '1' if file_hooks else '' }}"` will result in `os.environ["VAR"] = ""`. The environment variable **remains present in the environment** with an empty string value. This frequently leads to bugs in shell scripts and child processes that check `if os.environ.get("VAR"):` vs `if "VAR" in os.environ:`.

---

## 4. Architectural Alternatives Comparison

To identify the best approach, let us compare four alternative architectures:

| Criteria | Approach 1: Env Var via XPrompt (User Proposal) | Approach 2: First-Class Artifact Tags / Intent | Approach 3: Clean Positive Path & Role Matching | Approach 4: Ref Provider / Sidecar Invariants |
| :--- | :--- | :--- | :--- | :--- |
| **Concept** | Ambient env var toggled by `#research` input | Explicit flag on `sase artifact create --tag <tag>` | Match positive role (`*.final`) and path structure | Provider spec defines what constitutes a report |
| **Trigger Point** | Unclear (Artifact vs Commit) | Artifact creation (`producer: artifact`) | Commit time (`producer: commit`) | Both / Either |
| **Granularity** | Process-wide (ambient) | Per-artifact (precise) | Per-commit / Per-file | Per-sidecar / Inventory |
| **Handles Swarm Drafts** | Requires manual override on every peer segment | Peer segments tag as `draft` or omit tag | Cleanly filters out `*.cdx` or `__*.md` | Inventory excludes drafts from report role |
| **Handles Lead Consolidator** | Fails unless lead segment is manually updated | Lead explicitly tags deliverable as `report` | Matches `*.final` or clean `<name>/<name>.md` | Matches canonical publication path |
| **Stored Path Hash Issue** | Unresolved for artifact producer | Resolved (hook passes source or clean path) | Resolved (commit hook passes repo path) | Resolved |
| **Implementation Complexity** | Medium (YAML conversion + env propagation) | Medium (CLI flag + filter expansion) | Low (regex / glob update in provider spec) | High (deep ref provider refactor) |
| **Architectural Hygiene** | Poor (leaky ambient state) | High (durable, explicit, auditable) | Medium (heuristic, but simpler than today) | High |

---

## 5. Detailed Analysis of Viable Solutions

### 5.1 Approach 2 (Recommended Long-Term): First-Class Artifact Tags

The most robust and extensible design treats artifact deliverables as first-class, tagged entities.

#### 5.1.1 CLI & Model Changes in `sase`
1. **Extend `sase artifact create`:**
   Add an optional `--tag` (or `--intent`) argument to `sase artifact create`:
   ```bash
   sase artifact create -p report.md -l "research:202609/topic/topic.md" --tag final-report
   ```
2. **Extend `CapturedFileEvent` & `FileHookEvent`:**
   Record the tags associated with the created artifact:
   ```python
   @dataclass(frozen=True)
   class CapturedFileEvent:
       ...
       tags: tuple[str, ...] = ()
   ```
3. **Extend `FileHookFilters`:**
   Allow hooks to filter on artifact tags:
   ```python
   @dataclass(frozen=True)
   class FileHookFilters:
       ...
       artifact_tags: tuple[str, ...] | None = None
   ```
4. **Fix `abs_path` in `dispatch_artifact_file_hook_event`:**
   When an artifact is created without `--move`, the source file in the repository checkout remains intact. Provide an option in the hook spec (e.g. `path_target: source | stored`, defaulting to `source` when available) so CLI tools like `bob highlights` receive the clean repository path without hash suffix pollution.

#### 5.1.2 Integration in `sase-research-artifacts`
- In `research.md` (solo research):
  ```bash
  sase artifact create -p "<absolute-report-path>" -l "research:<repo-relative-report-path>" --tag final-report
  ```
- In `research_swarm.md` (swarm researchers):
  Swarm researchers register their drafts as intermediate:
  ```bash
  sase artifact create -p "<absolute-report-path>" -l "research:<repo-relative-report-path>" --tag draft
  ```
- In `research_swarm.md` (lead researcher):
  Make the lead researcher **always** register the consolidated report:
  ```bash
  sase artifact create -p "<absolute-report-path>" -l "research:<repo-relative-report-path>" --tag final-report
  ```
- In `provider.py` (`RESEARCH_HIGHLIGHTS_HOOK_SPEC`):
  Switch the hook to:
  ```python
  "filters": {
      "sidecars": ["research"],
      "producers": ["artifact"],
      "artifact_tags": ["final-report"],
      "ops": ["ADD"],
  }
  ```
This eliminates **all** path globs and **all** agent name globs. It does not matter what the agent is named, what provider it runs on, or what subdirectory it uses—only the explicit declaration `--tag final-report` triggers Highlights PDF generation.

---

### 5.2 Approach 3 (Immediate / Low Risk): Positive Matching Inversion

If we want an immediate fix that requires **no modifications to SASE core CLI or execution engines**, we should fix the logic flaw in the current `research-highlights` provider filter.

#### Why Negative Globs Failed
The current filter attempts to list every case that should *not* run:
```python
"path_globs": ["20*/**/*.md", "!20*/*__*.md", "!20*/*/*__*.md", ...],
"agent_name_globs": ["!research.*.cdx", "!research.*.cld", "!research.*.grk", "!research.*.mus", "!research.*.gem"],
```
This is an antipattern. Every new swarm researcher breaks it.

#### Inverting to Positive Matching
In SASE, research artifacts follow strict structural invariants:
1. **Consolidated reports produced by a swarm** always have their filename matching their parent directory name (e.g., `202609/<topic>/<topic>.md`).
2. **Solo research reports** are placed at `202609/<topic>.md` and never contain a double underscore (`__`).
3. **Drafts and critiques** *always* contain a double underscore: `__cdx.md`, `__cld.md`, `__critique.md`.

Furthermore, in `#research_swarm`, the lead researcher is **always** named with the `.final` suffix:
`%id:research.{@1}.final`

By switching to positive rules:
```python
# Match either the lead researcher in a swarm, or any solo agent:
"agent_name_globs": ["*.final", "!research.*.*"],
# Match only clean report paths:
"path_globs": [
    "20*/*/*.md",        # Swarm consolidated reports: 202609/topic/topic.md
    "20*/*.md",          # Solo reports: 202609/topic.md
    "!20*/**/*__*.md",   # Exclude any draft or critique regardless of directory depth
    *_COMPANION_MARKDOWN_EXCLUDE_GLOBS,
]
```
Notice what this accomplishes:
- `!20*/**/*__*.md` uses a recursive globstar that excludes drafts at **any depth** (depth 1, depth 2, or depth 3), replacing both `!20*/*__*.md` and `!20*/*/*__*.md`.
- `agent_name_globs: ["*.final", "!research.*.*"]` explicitly matches `.final` (the lead researcher) while rejecting all swarm clan members (`research.<N>.<anything>`), and accepting solo agents (which have IDs like `bbugyi200.athena.solo` or auto-generated IDs that do not belong to the `research.*` clan).
- Adding a 6th or 7th swarm researcher (e.g., `llama`, `deepseek`) requires **zero code changes** to `provider.py`.

---

## 6. Adjustments to User Requirements

Based on this investigation, here are the concrete adjustments to the user's initial requirements:

1. **Do not use raw ambient environment variables for file hook matching.**
   - Environment variables are process-bound and are lost during host finalizer commit reconciliation.
   - If an environment variable is used, it should be paired with explicit turn declaration or artifact registration metadata.
2. **Update `#research_swarm` so the lead researcher always registers the artifact.**
   - In `research_swarm.md`, change step 5 from `{%- if critique %}` to an unconditional step. The lead researcher must always register the consolidated report via `sase artifact create`.
3. **Decouple artifact file hook execution from the content-addressed digest path.**
   - In `src/sase/file_hooks/artifact.py`, `dispatch_artifact_file_hook_event` must pass the source path (when not moved) or provide a mechanism for hooks to specify `target_path: source`. Without this, artifact file hooks remain unusable for tools like `bob highlights`.
4. **If `#research` input overrides are implemented, model them as report roles or tags.**
   - Instead of a generic boolean environment flag, add a typed input `role: enum [report, draft]` or `tags: string_list` to `#research`.
   - Default: `role: report`.
   - In `#research_swarm`: Pass `role=draft` for preliminary researcher segments (`cdx`, `cld`, etc.).

---

## 7. Recommended Solution & Step-by-Step Implementation Plan

### Step 1: Immediate Stabilization of `sase-research-artifacts`
1. **Fix `research_swarm.md`:**
   Make the lead researcher's registration unconditional:
   ```markdown
   5. After the write succeeds, register the consolidated report as a durable snapshot:

      sase artifact create -p "<absolute-report-path>" -l "research:<repo-relative-report-path>"
   ```
2. **Fix `provider.py` in `sase-research-artifacts`:**
   Replace the negative researcher enumeration with recursive glob vetoes and positive role matching:
   ```python
   "filters": {
       "sidecars": ["research"],
       "producers": ["commit", "sdd", "finalizer"],
       "path_globs": [
           "20*/**/*.md",
           "!20*/**/*__*.md",  # Recursive veto: excludes all drafts and critique at any depth
           *_COMPANION_MARKDOWN_EXCLUDE_GLOBS,
       ],
       "agent_name_globs": [
           "*.final",          # Swarm lead consolidator
           "!research.*.*",    # Exclude all other swarm clan members
       ],
       "ops": ["ADD"],
   }
   ```
3. **Update Tests:**
   Update `tests/test_filters.py` to prove that any new swarm researcher (e.g. `research.26.xyz`) is automatically rejected without touching `provider.py`.

### Step 2: Implement First-Class Artifact Tags in SASE Core (`sase`)
1. **Update `sase artifact create` CLI (`src/sase/artifact_cli/create.py`):**
   Add `--tag` (repeatable string):
   ```python
   parser.add_argument("-t", "--tag", action="append", default=[], help="Artifact tags for categorization and hook matching")
   ```
2. **Update `FileHookFilters` (`src/sase/config/file_hooks.py`):**
   Add `tags: tuple[str, ...] | None = None`.
3. **Update `dispatch_artifact_file_hook_event` (`src/sase/file_hooks/artifact.py`):**
   Support dispatching against `captured_source.abs_path` when the file was copied and exists at the original location.
4. **Cut over `research-highlights` to `producer: artifact`:**
   Once artifact tags exist, `research-highlights` can cleanly listen to:
   ```yaml
   filters:
     sidecars: [research]
     producers: [artifact]
     tags: [final-report]
   ```
   This guarantees that Highlights PDFs are generated immediately upon artifact creation, without waiting for commit finalization and without any dependence on path or agent naming conventions.

---

## 8. Conclusion

The user's intuition that matching artifact files is currently too fragile is completely accurate. The current reliance on negative agent name globs (`!research.*.cdx`, `!research.*.cld`, etc.) is an unsustainable maintenance burden.

However, resolving this by having `#research` set an ambient environment variable creates new failure modes due to the single-turn host-finalizer boundary, Markdown frontmatter limitations, and the structure of `#research_swarm`.

By inverting the glob matching immediately to use recursive negative path vetoes (`!20*/**/*__*.md`) and positive role matching (`*.final`), the system becomes instantly robust against swarm expansion. Subsequently, introducing first-class artifact tags (`sase artifact create --tag`) provides the permanent, declarative foundation for all future SASE artifact automations.
