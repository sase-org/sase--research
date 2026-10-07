# Research Report: Embedding Gate Options in SASE Plan Frontmatter

**Author:** Researcher `gem` (5-Researcher Swarm)  
**Date:** October 2026  
**Target:** SASE Architecture & Planning Subsystem  
**Scope:** Tales, Epics, Notification Gates, Memory Authorization, and TUI/CLI Review Workflows  
**Repo-Relative Path:** `202610/plan_frontmatter_embedded_gate_options__gem.md`

---

## Executive Summary

This research investigates the design, viability, and architecture for embedding **gate options** directly within SASE plan frontmatter (for both tales and epics).

### The Core Problem
Under SASE's current single-turn architecture, a planning agent faces a sharp dilemma whenever a fork in requirements or a sensitive action arises:
1. **Interactive Questions (`/sase_questions`)**: If an agent needs user clarification before writing a plan—or proposes changing project memory when not explicitly commanded to do so—it must call `/sase_questions`. This immediately terminates the agent via SIGTERM, generates a question gate turn, blocks progress on human input, and upon resolution spawns a brand new planning agent from scratch. This creates a high-latency, multi-turn round trip for questions that the planner could easily have accommodated within a single plan document.
2. **All-or-Nothing Plan Review (`sase plan propose`)**: When a plan is submitted, the human reviewer's choices in the plan approval gate are largely binary at the implementation level: approve or reject (with optional feedback or unchecking coder launch / plan commit). The reviewer cannot toggle optional plan features, select between planned alternatives, or granularly authorize sensitive side-effects (such as updating memory files under `sase/memory/`).

### Verdict: Is This a Good Idea?
**Yes, with sharp architectural boundaries.** Embedding declarative gate options into plan frontmatter solves two real problems:
- **It eliminates artificial planning turn interruptions**, collapsing the question-and-plan workflow into a single, cohesive human review step.
- **It introduces a reliable, auditable human-in-the-loop (HITL) authorization gate for SASE memory modifications**, turning memory changes into explicit opt-in checkboxes that default to OFF unless the user explicitly commanded them.

However, this feature must **not** be allowed to degrade into a "choose-your-own-adventure" engine for indeterminate or unresearched plans. Plans must remain cohesive specifications. Gate options should be restricted to **scoped feature toggles, design forks with bounded alternatives, and explicit policy authorizations**.

### Key Recommendations
1. **Frontmatter Schema**: Introduce a clean, declarative `gate_options:` list in plan frontmatter (validated strictly by `sase-core` in Rust), supporting typed boolean toggles (`type: boolean`, default) and constrained discrete choices (`type: choice`).
2. **First-Class Memory Protection**: Provide a specialized `kind: memory` option type that connects directly to SASE's memory authorization rules. If a plan proposes modifying files under `sase/memory/`, it **must** declare a memory gate option. It defaults to `true` if and only if the user's turn prompt explicitly requested memory changes; otherwise, it defaults strictly to `false`.
3. **Seamless TUI/Gate Integration**: Leverage SASE's existing `GateBranchControls` and `GateOption` AND-group toggle infrastructure (`☑️` / `⬜`). Boolean options become checkboxes directly in the plan approval modal alongside `Launch coder` and `Commit plan`, requiring zero redesign of Textual widget trees.
4. **Durable Resolution Stamping**: When the plan is approved, the reviewer's resolved selections are stamped into the committed sidecar plan frontmatter (`gate_selections:`) to ensure permanent provenance, and injected into the successor coder prompt (or epic phase workers) so downstream agents have an unambiguous mandate.
5. **Phase DAG Integrity for Epics**: In Phase 1, embedded gate options in epics must pass context and configuration to phase workers, but must **not** dynamically delete nodes or mutate the dependency graph of `phases:` to prevent orphan beads and broken DAG invariants.

---

## 1. System Architecture & Context

To design this capability correctly, we must analyze how plans, gates, and agent sessions currently interact in SASE.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CURRENT PLAN LIFECYCLE                           │
└─────────────────────────────────────────────────────────────────────────────┘

 [Planner Agent]
       │
       │ writes `sase_plan_<name>.md`
       ▼
 [sase plan propose] ───> Rust `validate_plan` (sase-core)
       │                  Moves file to `~/.sase/plans/<name>.md`
       │                  Writes `.sase_plan_pending` marker
       ▼
  [Agent Killed] (SIGTERM handoff per `single-turn-agents`)
       │
       ▼
 [Host Supervisor] ─────> `build_plan_approval_gate_spec`
       │                  Creates `~/.sase/interaction_requests/plan/<id>/`
       │                  Query: `(approve AND commit) OR reject OR feedback`
       ▼
 [PlanApprovalModal] (TUI / Telegram / CLI)
       │
       │ Human approves (checks `approve`, `commit`)
       ▼
 [Gate Response Translation] ───> `translate_plan_gate_response`
       │
       ▼
 [Successor Launch]
       ├─ Tale: `prepare_accepted_plan_successor` -> Spawns coder agent
       └─ Epic: `create_and_launch_epic_from_plan` -> Creates beads & phases
```

### 1.1 The SASE Plan Hierarchy: Tales vs. Epics
SASE plans are strictly typed Markdown documents with structured YAML frontmatter:
- **Tale (`tier: tale`)**: A single-agent implementation unit (scoped to `xsmall`, `small`, or `medium`). When approved, it spawns a single successor coder agent with a fresh context window receiving `@<plan_ref>` and the instruction: `"The above plan has been reviewed and approved. Implement it now."`
- **Epic (`tier: epic`)**: A multi-phase project orchestrated as a directed acyclic graph (DAG) of phase beads (`phases: [{id, title, depends_on, size, description}]`). When approved, the host creates an epic bead, creates individual phase beads with dependencies, and initiates `sase bead work`.

All frontmatter validation is centralized in the Rust backend crate `sase_core::plan::validate`. Any unrecognized frontmatter key triggers an immediate `unknown-key` diagnostic error.

### 1.2 Gates and Gate Turns
Per decision record `decisions/gates-never-block`:
> *"A gate an agent creates becomes a gate shell: a named, non-LLM member of that agent's family that publishes the decision, outlives its creator, runs the commands the reviewer selects, and hands their typed outcome to the next family member. Continuation is always the gate shell's recorded follow-up, never the creator waiting, polling, or blocking on a response."*

A gate request bundle lives under `~/.sase/interaction_requests/<kind>/<request-id>/`. It defines:
- A boolean expression query, e.g. `(approve AND commit) OR reject OR feedback`.
- Mutually exclusive branches derived from the query.
- Options (`GateOption`) with identifiers, presentation labels, icons, default selection states, and executable commands.
- Groups (`GateGroup`) defining how AND-connected options are displayed and submitted together.

In the Textual TUI (`PlanApprovalModal` and `GateBranchControls`), AND branches are already rendered with interactive toggle checkboxes:
```
☑️ 🚀 Launch coder agent
☑️ 💾 Commit plan file to the plans sidecar
[ 1 ✅ Tale ]
```
Reviewers can toggle individual options on or off before submitting the branch.

### 1.3 Memory Authorization Rules (`sase_memory_write`)
Project memory under `sase/memory/` (which generates `AGENTS.md` and provider instructions) is treated with strict reverence:
> *"Memory is context every future agent pays for. Remember that every token in context either helps or hurts us..."*

An agent is authorized to write to memory **only** if:
1. The user's prompt for that turn explicitly asks for the change.
2. An approved plan being implemented explicitly names the change in its steps.
3. A bead being worked explicitly describes the change.

Crucially, `sase_memory_write` currently dictates:
> *"Authoring a plan whose steps change memory, when the user did not ask for it? Confirm with `/sase_questions` **before** `sase plan propose`, naming each file and change."*

This requirement is the chief source of friction: planners that realize memory notes should be updated must grind to a halt, prompt the user with `/sase_questions`, and abandon their planning context rather than simply presenting the plan with a toggle.

---

## 2. Critique: Is Embedding Gate Options in Plans a Good Idea?

### 2.1 The Value Proposition
1. **Contextual Decision Making**: Evaluating whether to update a memory note, generate a backward-compatibility shim, or choose Database A vs. Database B is significantly easier when reading the full plan that details the pros, cons, and implementation steps. Asking these questions in a vacuum via `/sase_questions` strips the user of the architectural context.
2. **Turn Efficiency & Latency Reduction**: Eliminates the "ask question -> die -> human answers -> respawn -> write plan -> die -> human reviews" two-gate, two-turn sequence. Collapses the flow into a single agent turn and a single review modal.
3. **Auditability and Exact Provenance**: When options are embedded in the plan, the reviewer's decisions are permanently stamped into the plan record committed to git in the `plans` sidecar. Future readers can inspect `@plan:202610/...md` and see not just what was planned, but exactly which options were accepted by the human.

### 2.2 Potential Risks and Architectural Pitfalls

#### Pitfall 1: "Choose-Your-Own-Adventure" Plan Dilution
*The Risk*: If agents can embed arbitrary options, lazy planners might generate ambiguous, uncommitted plans with 10 toggles instead of doing rigorous analysis and recommending a clear path.
*Mitigation*: The `/sase_plan` skill must prescribe clear guidelines:
- A plan must have a primary, recommended architectural path.
- Gate options must only be used for:
  - Policy authorizations (e.g., memory updates).
  - Explicit scope boundaries (e.g., optional CLI flag vs. core only).
  - Discrete, well-bounded forks where the agent has fully detailed both branches.
- If the agent is fundamentally unsure of the user's intent or architecture, it must still use `/sase_questions` *before* planning.

#### Pitfall 2: The Epic DAG Invalidation Hazard
*The Risk*: If an epic plan defines 4 phases (`phases: [A, B, C, D]` where `D depends_on C`), and frontmatter declares an option `include_feature_c: false`. If the user unchecks it, what happens? If Phase C is excluded, Phase D's dependency on C fails or produces an orphan bead.
*Mitigation*: **Do not permit gate options to dynamically prune epic phases in Phase 1.** Phase DAG structure must remain static. Gate options in an epic are passed as configuration context to the phase workers. If Phase C is conditional, Phase C's worker runs, checks the gate selection, and either no-ops or adapts its implementation cleanly.

#### Pitfall 3: The "Memory Default Gaming" Vulnerability
*The Risk*: An LLM agent, eager to be helpful, might decide that updating memory is obviously desirable and set `default: true` on a memory gate option, circumventing the principle that memory changes must be explicitly requested.
*Mitigation*: Mechanical enforcement. SASE must define a dedicated option kind (`kind: memory`). When `sase plan propose` validates the plan:
- If `kind: memory` has `default: true`, the host checks whether the turn's prompt or bead description explicitly authorized memory changes.
- If not, validation either errors or automatically coerces the default to `false`.
- In `%auto` mode, memory gates are **always** resolved to `false` unless explicitly overridden.

---

## 3. Recommended Design: `gate_options`

We propose introducing a first-class `gate_options` section in plan frontmatter.

### 3.1 Frontmatter Specification

```yaml
---
tier: tale
title: Add --fast path verification recipe
goal: Add a fast check recipe and document it in SASE CLI reference memory.
size: medium
gate_options:
  - id: update_memory
    label: "Update SASE memory (sase/memory/cli_rules.md)"
    kind: memory
    default: false
    files:
      - sase/memory/cli_rules.md

  - id: hook_integration
    label: "Install git pre-push hook for fast checks"
    description: "Configures .git/hooks/pre-push to run check-fast automatically."
    type: boolean
    default: true
---
```

#### Field Definitions
| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `string` | Yes | Unique identifier matching `^[a-z0-9_]{2,32}$`. |
| `label` | `string` | Yes | Human-facing label rendered on the toggle button (max 80 chars). |
| `description` | `string` | No | Explanatory note displayed below the label or as a tooltip in the TUI. |
| `type` | `enum` | No | Option control type: `boolean` (default) or `choice`. |
| `default` | `bool \| str`| Yes | Default state: `bool` for `boolean`; choice ID for `choice`. |
| `kind` | `enum` | No | Semantic category: `general` (default) or `memory`. |
| `files` | `list[str]` | Cond. | Required when `kind: memory`; lists the specific memory files to be modified. |
| `choices` | `list[obj]` | Cond. | Required when `type: choice`; list of `{id: str, label: str}` options. |

### 3.2 Choice Selectors (Radios / Enums)
For questions where the agent has a fork between alternatives:
```yaml
gate_options:
  - id: cache_backend
    label: "Artifact cache backend"
    type: choice
    choices:
      - id: sqlite
        label: "SQLite database (recommended)"
      - id: flat_files
        label: "Flat JSON directory"
    default: sqlite
```

In the TUI, boolean options render as inline checkboxes (`☑️` / `⬜`). Choice options render as a selectable radio group or picker that sets the value before submitting the branch.

---

## 4. End-to-End Implementation Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       REFINED PLAN & GATE ARCHITECTURE                      │
└─────────────────────────────────────────────────────────────────────────────┘

 [Authoring]
   Planner agent writes `gate_options` in plan frontmatter.
   If memory files are touched in plan steps, a `kind: memory` option is required.
       │
       ▼
 [Validation Boundary] (sase-core in Rust)
   `validate_plan` checks syntax, unique IDs, types, and memory defaults.
   Emits `un-gated-memory-change` diagnostic if memory touched without gate.
       │
       ▼
 [Gate Specification] (sase.plan_gate)
   `build_plan_approval_gate_spec` synthesizes `GateOption` for each embedded item.
   Tale Query: `(approve AND commit AND opt_1 AND opt_2) OR reject OR feedback`
   Epic Query: `(approve AND opt_1 AND opt_2) OR reject OR feedback`
   Primary branch includes embedded options with their authored defaults.
       │
       ▼
 [Review Presentation] (Textual TUI / PlanApprovalModal)
   Renders standard actions (`Launch coder`, `Commit`) + embedded options.
   Human toggles checkboxes with Space / Click.
       │
       ▼
 [Response Resolution] (sase._plan_gate_envelope)
   `translate_plan_gate_response` extracts `selected_option_ids`.
   Separates core protocol (`approve`, `commit`) from embedded selections.
   Derives map: `gate_selections = {"update_memory": False, "hook_integration": True}`.
       │
       ▼
 [Persistence & Stamping]
   Plan file frontmatter is updated with `gate_selections:` before being committed
   to the `plans` sidecar (`sase/repos/plans/YYYYMM/<plan_name>.md`).
       │
       ▼
 [Downstream Execution]
   ├─ Tale: `prepare_accepted_plan_successor` injects `### Gate Selections` into
   │        the coder prompt. If `kind: memory` is false, memory writes are blocked.
   └─ Epic: `create_and_launch_epic_from_plan` records `gate_selections` on the epic
            bead; phase workers read the stamped plan and respect selections.
```

### 4.1 Gate Query and Grouping Mechanics
SASE's notification gate query engine already evaluates boolean expressions:
- **Tale Branch**:
  $$\text{Query} = (\text{approve} \land \text{commit} \land \text{opt}_1 \land \text{opt}_2 \dots) \lor \text{reject} \lor \text{feedback}$$
  Group: `TALE_PLAN_SUBMIT_GROUP` contains `("approve", "commit", "opt_1", "opt_2")`.
- **Epic Branch**:
  $$\text{Query} = (\text{approve} \land \text{opt}_1 \land \text{opt}_2 \dots) \lor \text{reject} \lor \text{feedback}$$
  Group: `EPIC_PLAN_SUBMIT_GROUP` contains `("approve", "opt_1", "opt_2")`.

Because SASE's `GateBranchControls` evaluates any non-empty subset of a branch as valid:
- Reviewer can keep `approve` and `commit` checked, check `opt_2`, and uncheck `opt_1`.
- Reviewer clicks `[ 1 ✅ Tale ]`.
- `selected_option_ids` becomes `("approve", "commit", "opt_2")`.

### 4.2 TUI Aesthetics & Visual Layout

In `PlanApprovalModal`, the right-hand column houses the decision tree. With embedded gate options, the layout is organized into distinct logical zones separated by clean horizontal lines:

```
┌─ Decision ────────────────────────────────────────────────────────┐
│                                                                   │
│ ┌ Tale: Add --fast verification recipe ─────────────────────────┐ │
│ │                                                               │ │
│ │  Host Actions:                                                │ │
│ │  ☑️ 🚀 Launch coder agent                                      │ │
│ │  ☑️ 💾 Commit plan file to plans sidecar                      │ │
│ │                                                               │ │
│ │  ───────────────────────────────────────────────────────────  │ │
│ │                                                               │ │
│ │  Plan Options:                                                │ │
│ │  ⬜ 📝 Update SASE memory (sase/memory/cli_rules.md)          │ │
│ │     [dim]Authorizes modifying project memory notes[/dim]      │ │
│ │                                                               │ │
│ │  ☑️ ⚙️ Install git pre-push hook for fast checks               │ │
│ │     [dim]Configures .git/hooks/pre-push automatically[/dim]   │ │
│ │                                                               │ │
│ │  [ 1 ✅ Tale (Submit) ]                                       │ │
│ └───────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ [ 2 ❌ Reject ]                                                   │
│ [ 3 💬 Send Feedback ]                                           │
│                                                                   │
│ [e] Edit plan in $EDITOR  [c] Coder options                       │
└───────────────────────────────────────────────────────────────────┘
```

#### Visual Highlights:
- **Badge/Icon Semantics**: Standard emoji icons distinguish actions:
  - `🚀` Launch agent / `💾` Commit plan (Host actions)
  - `📝` Memory authorization (Policy gate)
  - `⚙️` Technical / workflow option
  - `💡` Conceptual / design choice
- **Checkbox Glyphs**: Uses Textual's standard Unicode `☑️` (checked) and `⬜` (unchecked).
- **Subtitles**: Subtle `[dim]` explanations appear below option labels without cluttering the primary line.
- **Keyboard Navigation**: Pressing `1` submits the active selection; `j`/`k` navigates options; `Space` toggles the focused option.

---

## 5. Memory Protection Integration

The user specifically requested:
> *"start requiring that all memory file changes be planned in plan files with explicit human gates (that should default to on iff the user explicitly requested those memory changes)."*

Here is the exact authorization protocol that enforces this invariant:

### 5.1 The Memory Invariant Triad
1. **Authoring Rule**: An agent writing a plan that touches `sase/memory/` MUST declare a `kind: memory` gate option in frontmatter.
2. **Default Determination**:
   - When the agent generates `sase_plan_<name>.md`, it inspects its initiating user prompt.
   - If the user explicitly requested memory updates (e.g. `"update memory"`, `"document this in cli_rules.md"`), it sets `default: true`.
   - If memory changes are incidental or agent-initiated, it MUST set `default: false`.
3. **Mechanical Guard in `validate_plan`**:
   - `sase plan propose` verifies that if any file in `sase/memory/` is targeted for edits in the plan body, a corresponding `kind: memory` option exists.
   - If not found, validation rejects the proposal with:
     `error [un-gated-memory-change]: Plan proposes changes to sase/memory/cli_rules.md but lacks an explicit memory gate option in frontmatter.`
4. **Execution Enforcement**:
   - Upon plan approval, `gate_selections` records whether the memory option was selected.
   - If `update_memory: false`, the coder agent prompt is injected with:
     `"Memory updates were NOT authorized by the reviewer. You MUST NOT edit any files under sase/memory/."`
   - Any attempt by the downstream coder to run `sase memory init` or edit files under `sase/memory/` will be rejected by the tool execution guard or pre-commit hook.

---

## 6. Downstream Agent Handoff Protocols

### 6.1 Tale Handoff (Coder Agent Successor)
In `sase.axe.run_agent_exec_plan_accept::prepare_accepted_plan_successor`:

Currently, the successor prompt is formatted as:
```python
successor_prompt = (
    f"{model_prefix}{vcs_prefix}"
    f"@{coder_plan_ref}\n\n"
    "The above plan has been reviewed and approved. "
    f"Implement it now.{coder_extra}\n{embedded_refs}"
)
```

With gate options, we inject the resolved decisions directly into the preamble:
```python
options_block = "\n".join(
    f"- [{'x' if val else ' '}] `{opt_id}`: {'Approved / Enabled' if val else 'Rejected / Skipped'}"
    for opt_id, val in gate_selections.items()
)

successor_prompt = (
    f"{model_prefix}{vcs_prefix}"
    f"@{coder_plan_ref}\n\n"
    "The above plan has been reviewed and approved with the following reviewer gate selections:\n"
    f"{options_block}\n\n"
    f"Implement the plan strictly according to these selections.{coder_extra}\n{embedded_refs}"
)
```

Additionally:
- `gate_selections` is serialized into `agent_meta.json` under `"plan_gate_selections"`.
- `SASE_GATE_SELECTIONS` is exported as an environment variable for CLI tools.

### 6.2 Epic Handoff (Bead & Phase Generation)
In `sase.bead.epic_from_plan::create_and_launch_epic_from_plan`:
1. The validated plan content is stamped with `gate_selections:` in its frontmatter before committing to the plans sidecar.
2. The created epic bead stores `gate_selections` in its metadata.
3. When phase workers are spawned by `sase bead work`, each phase worker's instructions reference the stamped plan (`@plan:...`) where the resolved selections are permanently legible.

---

## 7. Codebase Modification Plan

Implementing this feature cleanly spans the linked `sase-core` crate (Rust) and the `sase` repository (Python/Textual).

### 7.1 Component Matrix

| Subsystem | File | Nature of Change |
|---|---|---|
| **sase-core** | `crates/sase_core/src/plan/validate.rs` | Add `gate_options` to `COMMON_FIELDS`. Implement strict parsing for `gate_options` (id, label, default, kind, type, choices). Emit diagnostics for missing memory gates. |
| **sase-core** | `crates/sase_core/src/plan/wire.rs` | Add `ValidatedGateOption` struct to the wire binding returned to Python. |
| **sase** | `src/sase/sdd/plan_validate.py` | Expose `gate_options` on the Python `PlanValidationResult` dataclass. |
| **sase** | `src/sase/plan_gate.py` | In `build_plan_approval_gate_spec`, read `gate_options` from the validation result and construct dynamic `GateOption` instances and updated branch queries. |
| **sase** | `src/sase/_plan_gate_shared.py` | Add `EPIC_PLAN_SUBMIT_GROUP` and dynamic group builder helpers. |
| **sase** | `src/sase/_plan_gate_envelope.py` | In `translate_plan_gate_response`, parse embedded options out of `selected_option_ids` and populate `gate_selections`. |
| **sase** | `src/sase/plan_approval_choices.py` | Update `plan_approval_protocol_for_selection` to accept extra embedded option IDs alongside `approve` and `commit`. |
| **sase** | `src/sase/axe/run_agent_exec_plan_accept.py` | In `prepare_accepted_plan_successor`, stamp `gate_selections` into plan frontmatter, inject summary into coder prompt, and enforce memory write prohibition. |
| **sase** | `src/sase/bead/epic_from_plan.py` | In `create_and_launch_epic_from_plan`, stamp `gate_selections` into the archived epic plan before committing. |
| **sase** | `src/sase/macros/skills/sase_plan.md` | Document `gate_options` syntax and authoring guidance for planning agents. |
| **sase** | `src/sase/macros/skills/sase_memory_write.md` | Update routing rule: authorize memory changes through plan `gate_options` instead of requiring pre-plan `/sase_questions`. |

---

## 8. Summary of Adjustments to Requirements

In response to the prompt's invitation to critique and adjust requirements:

1. **Adjust Requirement: Do Not Allow Arbitrary Free-Form Input Inside Plan Gates**  
   *Adjustment*: Restrict embedded frontmatter gate options to **discrete types** (`boolean` toggles and `choice` enums). Free-form string input is already handled by `c` (coder options) and feedback modals. Embedding free-form text input fields in frontmatter adds excessive cognitive overhead to plan review.
2. **Adjust Requirement: Epic Phases Must Remain Statically Typed**  
   *Adjustment*: Embedded gate options in epics must not attempt to prune or re-wire phase dependency trees (`phases:`) dynamically at review time. All phase nodes are created; phase workers adapt their execution based on the stamped selections.
3. **Formalize Memory Gating Policy**:  
   *Adjustment*: Rather than relying solely on agent prompt compliance, make `kind: memory` a first-class validator concept in `sase-core`. If a plan describes editing memory files, `sase plan propose` strictly enforces that a corresponding `kind: memory` gate option is present and defaults to `false` unless explicit user authorization was recorded.

---

## 9. Conclusion

Embedding gate options in SASE plan frontmatter is a natural, elegant evolution of SASE's planning and gate architecture. It bridges the gap between static plan documents and interactive decision-making, eliminates cumbersome preliminary question cycles, and provides an airtight, auditable human gate for memory modifications.

By leveraging SASE's existing AND-group toggle mechanics in `GateBranchControls`, the user experience in the Textual TUI will be immediate, beautiful, and intuitive: reviewers can review the plan text on the left, flip relevant options and memory permissions on the right with single keystrokes, and approve execution in one unified action.
