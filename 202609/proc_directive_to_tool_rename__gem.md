# Research & Architecture Critique: Renaming the `%proc` Directive to `%tool` and Supporting `sase tool`

**Author:** Researcher `gem` (Swarm Member)  
**Date:** 2026-09-25  
**Target Repository:** `sase` / `sase-core`  
**Sidecar Reference:** `research:202609/proc_directive_to_tool_rename__gem.md`  
**Context:** `research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md`, `sase-s6` (`plan:202608/typed_launch_units.md`), `sase tool` control plane (Epics E1–E8)

---

## 1. Executive Summary

The prompt proposes renaming the `%proc` directive to `%tool` and adding features to it to better support the newly introduced `sase tool` command. 

Following a comprehensive architectural investigation across the `sase` Python codebase, the `sase-core` Rust crate, and the 8-epic roadmap for `sase tool` (`sase_tool_epic_roadmap.md`), this report reaches a definitive conclusion:

> **Core Recommendation:** **Do NOT rename `%proc` to `%tool` in-place.**  
> Renaming `%proc` to `%tool` is a **conceptual category error** that conflates the *execution substrate* (an operating system process shell) with a *domain entity* (a project-governed named tool). 
>
> Instead, adopt an **Orthogonal Two-Tier Directive Model**:
> 1. **Retain `%proc`** as the low-level, generic process execution primitive for arbitrary Bash and Python scripts (`%proc:: \n ```bash ... ``` `), preserving the clean symmetry established in `sase-s6` (`LaunchUnit::ProcUnit` vs `LaunchUnit::AgentUnit`).
> 2. **Introduce a dedicated, first-class `%tool` directive** (`%tool(check)`, `%tool(test, args=["..."])`, `%tool(check, keep_going=true)`) that directly targets the `sase tool` catalog, compiles to a new `LaunchUnit::ToolUnit`, validates tool existence statically at plan expansion time against `sase/sase.yml`, and dispatches directly into the `ToolRun` recording engine.

This approach gives users a clean, high-ergonomics `%tool` directive that natively leverages all 8 tool epics (fingerprinting, stage protocols, E2 hand-off, E3 failure triage, E4 verification receipts, and E7 local capacity admission) without breaking existing launch units, polluting the 180-day `ToolRun` ledger with ad-hoc glue scripts, or creating vocabulary confusion with LLM provider tool calls.

If project leadership nevertheless insists on a single unified directive, this report also provides a complete **Migration and Guardrail Blueprint** to execute the rename safely while mitigating the semantic traps.

---

## 2. Current Architecture & Verified Subsystem State

To understand why an in-place rename creates friction, we must examine what `%proc` and `sase tool` actually represent in the codebase today.

### 2.1 The Current `%proc` Subsystem (`sase-s6` / `typed_launch_units`)

Introduced under epic `sase-s6` (`plan:202608/typed_launch_units.md`) and gated by the `typed_launch_units` beta flag (currently **enabled** in default config), `%proc` defines a stand-alone process unit in an xprompt launch request.

#### Key Characteristics of `%proc`:
1. **Execution Substrate:**
   - It represents a **process shell** (`proc-shell`, lifecycle `proc-shell`, origin `xprompt-proc`), as opposed to an **agent runner** (`agent-session`).
   - A launch plan freezes a tagged union: `LaunchUnitPayloadWire::Agent(AgentUnitWire)` or `LaunchUnitPayloadWire::Proc(ProcUnitWire)`.
2. **Script-Centric Syntax:**
   - Positional command: `%proc("just check")`
   - Inline script: `%proc(python="print('ready')", timeout="20m", label="Preflight")`
   - Fenced block:
     ````markdown
     %proc(timeout="20m", idle_timeout="5m", cwd="docs", workspace="true")::

     ```bash
     just docs-check
     ```
     ````
3. **Execution Pipeline:**
   - Admission coordinator runs prerequisites (`%wait(...)`, `%if::`, `%hold(...)`, and `%queue(...)` capacity check).
   - Once eligible, `sase.agent.launch_proc_runtime.dispatch_proc_unit` reserves a `proc-shell` record in `~/.sase/procs/`.
   - The detached supervisor acquires an operational workspace lease (`workspace=true`), materializes the source code into a private `0600` script, and executes `/bin/bash --noprofile --norc <script>` or python.
   - It records logs in `~/.sase/procs/<proc-id>/output.log` and renders in the TUI Agents tab with a `▣` glyph and in the Procs tab.
   - **Crucially: `%proc` knows nothing about named tools, stages, or `ToolRun` ledgers.** It runs arbitrary code.

### 2.2 The `sase tool` Subsystem (Epics E1–E8)

Epic E1 has already landed the core `sase tool` infrastructure (`src/sase/tool/`, `src/sase/config/tools.py`), and the roadmap establishes an 8-epic trajectory:

```
E1 (Ledger & Foreground) ──> E2 (Durable Hand-off -H) ──┬──> E3 (Failure Triage NEW/KNOWN)
                                                         ├──> E4 (Verification Receipts)
                                                         └──> E5 (TUI Surfaces & LLM Calls)
                                                                 │
                                                                 v
                                         E6 (Forecasts) ──> E7 (Capacity Admission) ──> E8 (Fleet Rollout)
```

#### Key Characteristics of `sase tool`:
1. **Repository-Owned Catalog:**
   - Tools are defined in the project's `sase/sase.yml` under `tools:` (e.g. `check`, `check-full`, `test`, `install`).
   - Definitions are immutable per git tree: they specify exact argv, stages (`run_silent`), tracked input files (for dirty fingerprinting), environment passthrough, toolchain fingerprint commands, and argument policies (`args: deny` or `args: allow`).
2. **Machine-Local `ToolRun` Entity Store:**
   - SQLite ledger with ~180-day retention for run summaries, tracking exact attempt chains, per-stage timings, load averages, PSI metrics, and exit codes.
3. **Roadmap Invariant 3: "Zero New Supervisors":**
   - As documented in `sase_tool_epic_roadmap.md` §2.3: *"A ToolRun is a semantic record delegating execution to one of three existing executors: inline child, monitor (in-agent), durable proc (standalone)."*
   - Notice: **`proc` is the executor that `sase tool` delegates to during hand-off (`-H`)!**

---

## 3. In-Depth Critique of the In-Place Rename Plan (`%proc` -> `%tool`)

Renaming `%proc` to `%tool` seems intuitive at first glance ("developers think about running tools, not processes"). However, when analyzed against the system's architecture, several severe flaws emerge:

### 3.1 The Category Error: Execution Mechanism vs. Operational Entity

In systems architecture, clean boundaries rely on keeping mechanisms separate from policies:
- **`proc` is a Mechanism:** It answers *"HOW does this run?"* (As an isolated, supervised OS process with a private script, PID tracking, and log file).
- **`tool` is a Domain Entity:** It answers *"WHAT business operation is being performed?"* (A project-defined verification or build recipe registered in `sase.yml` with stages and fingerprints).

If `%proc` is renamed to `%tool`:
- What is `%tool:: \n ```bash\npython scripts/adhoc_clean.py\n``` `?
  - Is an arbitrary five-line bash cleanup script a "tool"?
  - Does it create an entry in the SQLite `ToolRun` ledger?
    - If **YES**: It pollutes the 180-day `ToolRun` database with throwaway, non-repeatable ad-hoc runs that lack a catalog definition, dirty-input tracking, or stage contracts.
    - If **NO**: Why is the directive named `%tool` if it doesn't run a tool or record a `ToolRun`? This creates an irreconcilable disconnect between the `%tool` directive and the `sase tool` command!

### 3.2 The "Triple Tool" Vocabulary Collision

SASE has already spent significant design effort resolving the word "tool":
1. **Provider Tool Calls:** Agents calling functions (`view_file`, `run_command`, `read_url_content`). To free the word "tool" for `sase tool`, Epic E1 specifically renamed the TUI tools pane to **LLM Calls** (`src/sase/ace/tui/llm_calls/`).
2. **`sase tool` CLI:** The repository command runner and ledger (`sase tool run check`).

Introducing `%tool` as an in-place rename of `%proc` introduces a third, conflicting meaning:
- In an xprompt template containing agent instructions, `%tool(...)` appears alongside prompt text.
- To an LLM reading its prompt context, `%tool` looks like an instruction regarding provider tool calling or an available LLM tool.
- In the TUI, stand-alone procs appear in the **Procs pane** (`sase proc`, `~/.sase/procs/`). If the directive is `%tool`, users will look for it in `sase tool runs`, but find it under `sase proc`. The mental mapping is fractured.

### 3.3 Loss of Static Catalog Validation

One of the greatest weaknesses of `%proc` today is that it is untyped procedural code:
```text
%proc("just chekc")   <-- Typo only caught at runtime after workspace lease!
```

If we simply rename `%proc` to `%tool` and allow it to accept arbitrary bash strings or fences, we perpetuate this weakness. 

Conversely, if `%tool` is designed as a *domain-specific directive* targeting named tools:
```text
%tool(check)
```
The Rust core parser can **statically validate** `check` against `sase.yml` during prompt expansion, *before approval and before any workspace lease is claimed*. If the tool does not exist, the plan fails validation immediately. An in-place rename of a generic script directive loses this opportunity.

### 3.4 Python vs. Tool Semantics

`%proc` supports Python scripts:
```text
%proc(python="import sys; sys.exit(0)")
```
`sase tool` has no concept of arbitrary Python script execution; named tools are argv lists defined in `sase.yml`. Renaming `%proc` to `%tool` means `%tool(python="...")` would either be an invalid tool or an awkward second-class construct that confuses what `sase tool` does.

### 3.5 Migration Blast Radius and In-Flight Friction

`sase-s6` has four open discovered issues (`#14`, `#15`, `#16`, `#17`) regarding coordinator PID tracking, rescan polling, and `%wait(time=...)` elapsing. 
Renaming `%proc` to `%tool` would touch:
- `sase-core`: `plan_resolution.rs`, `wires.rs`, `editor/wire.rs`, `argument_syntax_edit.rs`, unit tests.
- `sase`: `_directive_collect.py`, `_directive_extract.py`, `code_value.py`, `launch_proc_runtime.py`, `agent_launch_facade.py`.
- Documentation: `docs/xprompt.md`, `docs/ace.md`, `docs/axe.md`, `docs/architecture.md`.

Refactoring working code across the Rust-Python boundary for a purely cosmetic rename while the underlying coordinator issues are being stabilized introduces high risk for zero functional gain.

---

## 4. Evaluation of Architectural Alternatives

| Evaluation Dimension | Option 1: In-Place Rename (`%proc` -> `%tool`) | Option 2: Orthogonal Two-Tier (`%proc` + `%tool`) (Recommended) | Option 3: Unified Directive with Sub-Modes |
| :--- | :--- | :--- | :--- |
| **Separation of Concerns** | **Poor.** Conflates OS process with project tool. | **Excellent.** Generic proc vs governed tool. | **Fair.** Mixed within one syntax. |
| **ToolRun Ledger Integrity** | **Poor.** Either pollutes ledger with ad-hoc scripts or breaks naming symmetry. | **Pristine.** Only `%tool` writes to `ToolRun` ledger; `%proc` uses proc store. | **Moderate.** Ad-hoc vs named must be tagged. |
| **Static Catalog Validation** | **No.** Accepts arbitrary strings. | **Yes.** Validates against `sase.yml` at plan expansion. | **Conditional.** Only if `name=` mode used. |
| **LSP Autocomplete & DX** | **Weak.** Generic string completion. | **Outstanding.** Autocompletes valid project tools (`check`, `test`). | **Complex.** Depends on parsed mode. |
| **Backward Compatibility** | **Breaking.** Breaks existing xprompts/docs. | **100% Non-breaking.** `%proc` unchanged. | **Partial.** Deprecation period needed. |
| **Support for E1–E8 Features** | **Awkward.** Adding tool flags to script block. | **Native.** Designed specifically for tool flags. | **Moderate.** Options apply conditionally. |
| **Implementation Complexity** | High churn (Rust wire, Python, docs). | Low-to-Medium (additive, zero breaking changes). | High (complex branching in parser). |

---

## 5. Recommended Solution: The Two-Tier Architecture

Rather than destroying `%proc`, **elevate the system by introducing a dedicated `%tool` directive while keeping `%proc` as the underlying process substrate.**

```
XPrompt Directives
       │
       ├─────────────────────────────────────────┐
       ▼                                         ▼
   %proc Directive                           %tool Directive
   (Generic OS Process Unit)                 (Governed Project Tool Unit)
       │                                         │
   Arbitrary Bash/Python scripts             Project named tool from sase.yml
   Private 0600 script materialization       Static catalog validation in Rust
   Tracked in ~/.sase/procs/                 Tracked in ToolRun SQLite Ledger
   Rendered as ▣ (Proc Shell)               Rendered as ⚙ (Tool Run)
       │                                         │
       └────────────────────┬────────────────────┘
                            ▼
              Durable Admission Coordinator
```

### 5.1 Syntax and Ergonomics of `%tool`

The new `%tool` directive is designed specifically to interface with the `sase tool` command and its roadmap epics:

#### 1. Bare Named Tool
```text
%tool(check)
```
or with quotes:
```text
%tool("check")
```
- Validates that `check` is defined in `sase.yml`.
- Automatically inherits the tool's defined `argv`, `stages`, and `inputs`.

#### 2. Named Tool with Extra Arguments (when permitted by tool definition)
```text
%tool(test, args=["tests/test_tool_handler.py", "-k", "test_runs"])
```
- Compiles to `sase tool run test -- tests/test_tool_handler.py -k test_runs`.
- Statically rejected if `sase.yml` specifies `args: deny` for that tool!

#### 3. Execution Control (Epics E1 & E2)
```text
%tool(check, timeout="15m", keep_going=true, handoff=true)
```
- `handoff=true`: Automatically delegates to `sase tool run -H` (E2 hand-off), ensuring execution survives agent completion or shell exit.
- `keep_going=true` (`-k`) or `fail_fast=true` (`-x`): Directly configures stage progression.

#### 4. Verification Receipts and Caching (Epic E4)
```text
%tool(check, reuse=true)
```
- When `reuse=true`, the tool run checks for an existing green verification receipt on an unchanged tree. If valid, the unit settles instantly with status `cached` without running the underlying commands!

#### 5. Capacity and Queuing (Epic E7)
```text
%q(priority=10, weight=0.5)
%tool(check-full)
```
- Seamlessly participates in `runner_capacity` tool queue admission alongside agent launches.

---

## 6. Technical Implementation Blueprint

### 6.1 Rust Core (`sase-core`) Modifications

Located in the linked `sase-core` checkout (`crates/sase_core/`):

#### 1. Wire Types (`crates/sase_core/src/agent_launch/wires.rs`)
Add a distinct `ToolUnitWire` to the launch unit payload:
```rust
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum LaunchUnitPayloadWire {
    Agent(AgentUnitWire),
    Proc(ProcUnitWire),
    Tool(ToolUnitWire),
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ToolUnitWire {
    pub tool_name: String,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub extra_args: Vec<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub timeout: Option<String>,
    pub keep_going: bool,
    pub fail_fast: bool,
    pub handoff: bool,
    pub reuse_receipt: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub queue_capacity: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub queue_weight: Option<f64>,
}
```

#### 2. Static Plan Resolution & Catalog Validation (`plan_resolution.rs`)
During expansion, resolve the tool catalog from `sase.yml`:
```rust
pub fn validate_tool_unit(
    unit: &ToolUnitWire,
    catalog: &ToolCatalog,
    logical_id: &str,
    diagnostics: &mut Vec<LaunchPlanDiagnosticWire>,
) {
    if let Some(entry) = catalog.get(&unit.tool_name) {
        if !unit.extra_args.is_empty() && entry.args_policy == ArgsPolicy::Deny {
            diagnostics.push(typed_unit_diagnostic(
                "tool-args-denied",
                &format!("Tool '{}' does not allow extra arguments.", unit.tool_name),
                logical_id,
                None,
            ));
        }
    } else {
        diagnostics.push(typed_unit_diagnostic(
            "unknown-tool",
            &format!("Named tool '{}' is not defined in sase/sase.yml.", unit.tool_name),
            logical_id,
            None,
        ));
    }
}
```

#### 3. Editor LSP Completion (`editor/wire.rs`)
Provide dynamic completions for `%tool(`:
- Completes with the exact list of configured tools from `sase.yml` (`check`, `check-full`, `test`, `install`).
- Snippet: `%tool(${1|check,check-full,test,install|})$0`.

---

### 6.2 Python Runtime (`sase`) Modifications

#### 1. Directive Extraction (`src/sase/xprompt/_directive_collect.py` & `_directive_extract.py`)
Add support for `%tool(...)`:
- Extracts `tool_name` (positional or named `name=`).
- Extracts options: `args`, `timeout`, `keep_going`, `fail_fast`, `handoff`, `reuse`.
- Rejects code fences or `python=` bodies on `%tool` with an explicit diagnostic: *"`%tool` runs named tools from `sase.yml`; for arbitrary scripts, use `%proc::`"*.

#### 2. Admission Coordinator Dispatch (`src/sase/agent/launch_admission_runtime.py`)
When a `ToolUnit` is admitted:
- If `handoff=true`: Invoke `sase.tool.handoff_launch.execute_handoff`.
- If foreground: Invoke `sase.tool.executor.execute_tool_run`.
- Capture the generated `run_id` and record it in the launch receipt as `tool_run_id`.
- Emit artifact link edge: `launch:<request-id>` -> `tool:<run-id>`.

#### 3. TUI Visualization (`src/sase/ace/tui/`)
- Display the tool unit in the Agents tab with a distinct glyph: `⚙ <tool_name>` (e.g. `⚙ check`).
- Status chip reflects tool run stages (e.g., `stage: test-fast 3/5`).
- Clicking the row jumps directly to the ToolRun details view.

---

## 7. Fallback Plan: If In-Place Rename (`%proc` -> `%tool`) Is Mandatory

If project leadership decides that `%proc` must be renamed to `%tool` regardless of the architectural distinction, execute the migration following these strict guardrails to prevent regressions:

### 7.1 Two-Phase Deprecation & Aliasing
1. **Phase 1 (Additive Alias):**
   - Introduce `%tool` as an alias for `%proc`.
   - Both `%proc` and `%tool` parse into the existing `ProcUnitWire`.
   - Update `sase-core` LSP to recommend `%tool` and mark `%proc` as deprecated in hover documentation.
   - Support an optional `tool="<name>"` argument on `%tool(...)`:
     ```text
     %tool(name="check")   # Automatically delegates to sase tool run check
     %tool("just check")   # Legacy raw script execution
     ```
2. **Phase 2 (Deprecation Warning & Schema Bump):**
   - Bump `LAUNCH_PLAN_WIRE_SCHEMA_VERSION`.
   - Issue a warning diagnostic when `%proc` is authored.
   - When `%tool` is given raw bash/python scripts, emit a warning that ad-hoc scripts will not be recorded in the `ToolRun` ledger.
3. **Phase 3 (Removal):**
   - Remove `%proc` keyword support after one release cycle.

### 7.2 Handling Ad-Hoc Scripts in the `ToolRun` Ledger
If `%tool` executes arbitrary scripts, do NOT record them as standard named tools. Instead:
- Record them with `tool_name: "adhoc"`, `adhoc: true`.
- Enforce a 7-day retention limit instead of the standard 180-day summary retention, preventing database bloat from throwaway pipeline scripts.

---

## 8. Summary of Recommendations & Next Steps

1. **Reject the pure in-place rename:** Do not destroy `%proc`. Keep `%proc` as the underlying mechanism for running arbitrary OS processes (`ProcUnit`).
2. **Adopt the Two-Tier Model:** Implement `%tool` as a first-class directive dedicated to `sase tool` and `ToolRun` integration.
3. **Sequence with Epic E2:** Schedule the `%tool` directive implementation as part of or immediately following **Epic E2 (Durable Hand-Off Execution)**. E2 provides the exact durable execution semantics that `%tool(..., handoff=true)` needs.
4. **Leverage Static Validation:** Use the Rust core to validate `%tool(<name>)` against `sase.yml` at plan creation time, eliminating runtime errors before approval.

