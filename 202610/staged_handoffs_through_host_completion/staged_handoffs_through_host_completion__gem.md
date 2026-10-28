# Architectural Assessment: Retiring Agent Kill Handoffs in Favor of Host Finalizers

**Author:** Researcher gem (`research.5f.gem`)  
**Date:** 2026-10-28  
**Topic:** Transitioning SASE gates, plans, and monitors from mid-turn SIGTERM kills to host-owned finalizer completion  
**Target Repository:** `research:202610/gate_monitor_finalizer_completion__gem.md`  

---

## 1. Executive Summary

This investigation evaluates the architectural proposal to stop having SASE gates, plan proposals, and monitors terminate their calling agents via mid-turn `SIGTERM` kills, requiring instead that all agent turns conclude through host-owned finalizers and submission declarations.

### Core Verdict
**The proposal to retire the mid-turn agent kill model is completely sound, urgent, and strongly recommended.** 

The current design—where `sase plan propose`, `sase monitor start`, and `sase gate create` invoke `kill_agent_runner_group()` to terminate the provider process group via `SIGTERM`—is a structural flaw. Evidence from live agent runs demonstrates that this kill model causes:
1. **Silent Loss of Work (Workspace Stranding):** Uncommitted file modifications made in the proposing turn (e.g., updating existing plan files to `status: done`, making baseline adjustments, or landing discovered bug fixes) are discarded because host completion finalizers are skipped. In epic `bob-cli-dw` (bead `bob-cli-e0`), five consecutive backlog batch lander agents lost their plan status updates because their turn ended with `sase plan propose`.
2. **Broken Turn Completion & Lost Reasoning:** Abruptly murdering the LLM provider process mid-execution destroys the agent's concluding remarks and reasoning, forcing the host runner to synthesize fake responses (`format_plan_as_response`) and swallow `SIGTERM` (exit code 143) errors.
3. **Contradictory Agent Contracts:** Instructions declare that host completion is universal (`decisions:host-owned-completion`), while simultaneously maintaining a confusing list of "mechanical exemptions" (`/sase_plan`, `/sase_monitor`, `/sase_gate`) that forbid using `/sase_final`.

### Critique and Recommended Refinement of the Implementation Approach
While the user's overarching goal is right, **"just using the existing commit finalizer" to execute gates and monitors should NOT be implemented by overloading `builtin@commit`.**

Overloading `builtin@commit` to manage gate shells, plan reviews, and monitor supervisors conflates two distinct concerns:
- **VCS Commit Reconciliation (`builtin@commit`):** Discovering repository dirt, validating commit messages, and running `sase stitch create`.
- **Turn Continuation & Lifecycle Handoff:** Transitioning the finished agent turn to an asynchronous supervisor (gate shell, child epic launcher, or monitor).

### Recommended Architecture: Staged Intent + Universal Finalizer + Post-Finalization Transition
Instead of stuffing gate/monitor execution into the commit finalizer:
1. **Staged Intent (No Kill):** Tools (`sase plan propose`, `sase monitor start`, `sase gate create`) validate their payloads, persist their records, stage a pending handoff intent marker in the agent's artifact directory, and return `0` cleanly to the agent.
2. **Universal Final Declaration:** Every root agent turn—without exception—concludes by invoking `/sase_final` to declare repository decisions.
3. **Host Finalizer Execution:** The host controller executes `run_finalizers()` (`builtin@commit`). If the workspace has dirty repositories (code, sidecars, or linked checkouts), they are committed. If the workspace is clean, the commit finalizer passes without requiring commit payloads.
4. **Host Post-Finalization Handoff:** Once finalizers verify and settle the turn's work, the host runner inspects the staged handoff intent and transitions the turn (launching the plan gate shell, starting the child workflow, or handing the lane to the monitor).

---

## 2. Context & Root Cause Analysis

### 2.1 The Current Kill-Based Architecture

Under the current implementation, any command that initiates an asynchronous wait or handoff calls `kill_agent_runner_group(artifacts_dir)`.

```
[Agent LLM Subprocess] ──> runs tool `sase plan propose` 
                               │
                               ├──> 1. Validates and archives plan
                               ├──> 2. Writes `.sase_plan_pending` marker
                               └──> 3. Calls `kill_agent_runner_group()`
                                        │
                                        └──> Sends SIGTERM to Runner PGID!
                                                 │
[Agent LLM Subprocess Dies (Exit 143)] <─────────┘
[Host Runner catches SIGTERM]
     ├──> Sees `was_killed() == True`
     ├──> Reads `.sase_plan_pending`
     ├──> Skips `run_finalizers()` via `should_skip_finalizers()`
     └──> Synthesizes fake response from plan file
```

Specific codebase evidence:
- In `src/sase/main/plan_propose_handler.py:479`: After archiving the plan and writing `.sase_plan_pending`, it invokes `kill_agent_runner_group(artifacts_dir)`.
- In `src/sase/monitor/handoff.py:64` and `src/sase/main/monitor/start.py:327`: After starting the monitor, `maybe_handoff_monitor_from_agent()` invokes `kill_agent_runner_group(artifacts_dir)`.
- In `src/sase/gate_turn/agent_handoff.py:64`: Creating a gate invokes `maybe_handoff_turn_from_agent()`, which writes `.sase_gate_pending` and invokes `kill_agent_runner_group(artifacts_dir)`.
- In `src/sase/finalizers/controller_context.py:47`:
  ```python
  def should_skip_finalizers(artifacts_dir: str | None) -> bool:
      if not artifacts_dir:
          return True
      if not os.environ.get("SASE_AGENT_TIMESTAMP"):
          return True
      return has_pending_handoff(artifacts_dir)
  ```
  `should_skip_finalizers()` explicitly checks `has_pending_handoff(artifacts_dir)` and bypasses all finalizer runs whenever a handoff marker is present!

### 2.2 Incident Evidence from Production Agents

The flaws of this model are not theoretical; they have repeatedly caused silent data loss and forced agent workarounds in production:

#### 1. The `bob-cli-dw.land` Landing and `bob-cli-e0` Defect
In epic `bob-cli-dw`, the lander agent (`bob-cli-dw.land`) verified five completed phases. During its audit, it discovered that the previous five epics (`bob-cli-d7`, `bob-cli-da`, `bob-cli-dd`, `bob-cli-df`, `bob-cli-dp`) had all been closed on beads, yet every single corresponding plan file in the `plans` sidecar still had frontmatter `status: wip`!

**Why did this happen?**
Each lander had followed the prompt instructions:
1. Mark the completed plan `status: done` in the local `sase/repos/plans/` sidecar checkout.
2. Run `sase plan propose` to propose the next backlog batch epic.
Because `sase plan propose` instantly murdered the runner with `SIGTERM`, no finalizer ever ran, and the modified `plans` sidecar was never committed. The approved child epic launched in a fresh workspace, leaving the uncommitted edits stranded in the old ephemeral workspace.

`bob-cli-dw.land` had made a test fix in `sase` and updated nine plan files. It explicitly noted in its transcript:
> *"I've landed and closed epic bob-cli-dw, but I didn't propose the next backlog epic (B7). Doing that would most likely have thrown away this turn's uncommitted work... This turn holds the sase test fix and nine plan-file edits, so I ended it normally to get them committed."*

The agent filed bug `bob-cli-e0` (`sase plan propose handoff never commits the proposer's dirty edits, so successor-rule landers lose plan status and landing fixes`).

#### 2. The `sase-1ou.land` Landing
In `sase-1ou.land`, the land agent fixed a difficult SQLite store contention bug in `sase-core` (`connection.rs`), added regression tests, and updated flake baselines. However, full CI exposed a surviving race condition on Python 3.12. The lander wrote child epic `files_spread_ci_landing.md` and proposed it with `sase plan propose`.

Proposing the plan immediately terminated the agent. Because the turn was killed, the lander could not conclude its turn cleanly or emit its comprehensive triage summary directly to the chat transcript; instead, the runner had to generate a synthetic plan preview response.

#### 3. The `bob-cli-dn` Monitor Defect
In bead `bob-cli-dn`, a predecessor agent opened an external repository (`sase repo open`), modified code, and started a monitor (`sase monitor start`). The kill handoff caused the continuation agent to lose track of the opened-repo commit obligation, stranding the uncommitted changes in the workspace.

---

## 3. Critique of the Proposed Plan

### 3.1 Why Retiring the Kill Model is the Right Decision
The user's intuition is entirely correct: having gates, plans, and monitors kill the agent was a design mistake.
- **Historic Motivation:** The kill model arose from `decisions:gates-never-block` and `decisions:single-turn-agents`. The goal was to prevent an agent from idling or polling while waiting for human review. However, terminating an agent's process group with `SIGTERM` in the middle of a tool call was a crude way to enforce non-blocking semantics.
- **Resolution:** A turn can be strictly single-turn without being violently killed in mid-sentence. The tool call should simply return control to the agent, allowing it to finish its thought, emit its user-facing conclusions, and submit its final declaration. Once the turn completes normally, the host executes finalizers and handles the transition.

### 3.2 Critique of "Just Using the Existing Commit Finalizer"
The user suggests:
> *"I'm thinking that the best way to do this is probably to just use the existing commit finalizer. This means that, after this change, all agent turns should be required to submit a final declaration... We will need to make sure that the commit finalizer knows that it is okay for agents that propose plans or run monitors do not specify that a commit should be made."*

We must evaluate two potential interpretations of this suggestion:

#### Interpretation A: Stuffing Gate/Monitor Execution into `builtin@commit`
If this means modifying the `builtin@commit` provider code to inspect `.sase_plan_pending` or `.sase_monitor_pending` and execute the handoff inside `execute_commit_finalizer()`:
- **Flaw 1 (Violates Separation of Concerns):** `builtin@commit` is an adapter for Git VCS stitches (`sase stitch create`). It should know nothing about gate shells, plan reviews, or monitor supervisors.
- **Flaw 2 (Brittle Fixed-Point Semantics):** SASE finalizers are designed to run to a fixed point (where mutating finalizers can reactivate verification finalizers). A handoff is an irreversible transition that terminates the agent lane or launches a child family. Triggering handoffs inside a finalizer iteration can cause catastrophic state corruption if subsequent finalizers fail.
- **Flaw 3 (Failure Atomicity):** If a git commit fails (e.g. merge conflict, dirty protected path, or invalid commit message), the turn must enter declaration/conflict recovery. If the handoff was already launched inside the commit finalizer, a child epic or gate shell would be running while the parent turn is in recovery!

#### Interpretation B: Running the Existing Commit Finalizer as Part of Universal Finalization
If this means that **every agent turn runs through host completion (which includes `builtin@commit`) before handing off**:
- **This is the correct architectural path!**
- The commit finalizer does what it does best: it audits the workspace, commits dirty repositories (including plans and sidecars), and verifies postconditions.
- Only *after* all finalizers have passed and the workspace is settled does the host runner execute the handoff.

### 3.3 Critique of "Do Not Specify That a Commit Should Be Made"
The user notes:
> *"We will need to make sure that the commit finalizer knows that it is okay for agents that propose plans or run monitors do not specify that a commit should be made."*

Let us examine the exact behavior of the commit finalizer today:
1. **When the Workspace is Clean:**
   - In `src/sase/finalizers/declaration_store.py:225`:
     ```python
     trigger = "dirty_repository" if repository_obligations else "not_triggered"
     requirements.append(
         FinalizerPayloadRequirementWire(
             instance_id=entry.instance_id,
             trigger=trigger,
             submission_required=bool(repository_obligations),
             ...
         )
     )
     ```
   - When no repositories are dirty, `repository_obligations` is empty (`[]`), `trigger` is `"not_triggered"`, and `submission_required` is `False`.
   - In `src/sase/finalizers/commit_execution.py:133`:
     ```python
     if state.dirty_state.is_clean and is_missing_declaration(exc):
         return BuiltinCommitExecution(..., result=success_result(...))
     ```
   - If an agent only proposed a plan (or started a monitor) and made no other file changes, the workspace is clean. The commit finalizer **already succeeds without requiring any commit decision**!
2. **When the Workspace is Dirty:**
   - If the agent *did* modify files (for example, editing an existing plan frontmatter to `status: done`, updating documentation, or fixing code), `repository_obligations` is non-empty.
   - **Crucial Rule:** In this case, the agent **MUST** specify a commit decision for those dirty repositories!
   - We must NOT allow an agent to leave dirty files uncommitted when proposing a plan.workspaces are ephemeral clones; any uncommitted change left behind when a plan hands off to a new child epic is permanently lost.
   - The only legal reason to leave dirty files uncommitted is a typed deferral (e.g. `foreign_work` or `protected_paths`).

---

## 4. Architectural Comparison of Alternatives

The table below contrasts the three potential architectures for handling gates, plans, and monitors:

| Dimension | Current Model (Mid-Turn SIGTERM Kill) | Overloaded Commit Finalizer | Recommended Model (Staged Intent + Universal Finalizer + Transition) |
| :--- | :--- | :--- | :--- |
| **Agent Termination** | Violent SIGTERM mid-tool call (Exit 143) | Normal exit after declaration | Normal exit after declaration |
| **Workspace Stranding** | Severe (uncommitted edits discarded) | Resolved | Resolved |
| **Dirty Repo Commits** | Never committed on handoff | Committed inside `builtin@commit` | Committed cleanly by `builtin@commit` before handoff |
| **Clean Repo Handling** | N/A (finalizers bypassed) | Custom exemption logic | Native (`submission_required: false`) |
| **Separation of Concerns** | Poor (tool kills runner) | Poor (`builtin@commit` manages gates) | Clean (VCS commits vs. lifecycle handoffs) |
| **Transcript Integrity** | Broken (synthetic responses fabricated) | Preserved | Preserved (real LLM response retained) |
| **Error / Recovery Path** | None (killed immediately) | Complex (handoff mixed with commit recovery) | Robust (commits settle first; if failed, recovery runs before handoff) |

```mermaid
flowchart TD
    subgraph Proposed_Architecture["Recommended Turn Completion Lifecycle"]
        A["Agent Turn Begins"] --> B["Agent executes tools\n(edits code, updates plan status)"]
        B --> C["Agent runs `sase plan propose` or `sase monitor start`"]
        C --> D["Tool validates & records record\nStages pending intent in artifacts\nReturns 0 (NO SIGTERM)"]
        D --> E["Agent finishes reasoning\nCalls `/sase_final`"]
        E --> F["Host runs `run_finalizers()`\n(`builtin@commit`)"]
        F --> G{"Are repos dirty?"}
        G -- "Yes" --> H["`builtin@commit` commits all dirty repos\nvia `sase stitch create`"]
        G -- "No" --> I["`builtin@commit` validates clean state"]
        H --> J{"Finalizers Succeeded?"}
        I --> J
        J -- "Yes" --> K{"Pending handoff intent staged?"}
        J -- "No" --> L["Enter Finalizer Recovery\n(Handoff blocked)"]
        K -- "Plan Proposed" --> M["Host executes plan gate shell\nLaunches child epic / review"]
        K -- "Monitor Started" --> N["Host transfers lane to monitor supervisor"]
        K -- "Gate Created" --> O["Host activates gate shell"]
        K -- "None (Normal)" --> P["Turn settles as completed"]
    end
```

---

## 5. Detailed Solution & Implementation Blueprint

### 5.1 Step 1: Remove `kill_agent_runner_group` from Handoff Tools

Modify the turn-ending tools so they register their intent but do not terminate the runner process:

1. **`sase plan propose` (`src/sase/main/plan_propose_handler.py`)**:
   - Keep validation, archiving, and `.sase_plan_pending` marker creation.
   - Remove `kill_agent_runner_group(artifacts_dir)`.
   - Return exit code `0` with informative stdout:
     ```text
     ✓ Plan validated and archived to ~/.sase/plans/202610/example.md
     ✓ Plan proposal staged for turn completion.
     Next action: Complete any remaining notes or status edits, then run `/sase_final` to declare commits and submit your turn.
     ```
2. **`sase monitor start` (`src/sase/monitor/handoff.py` & `src/sase/main/monitor/start.py`)**:
   - Keep monitor supervisor record creation and `.sase_monitor_pending` marker creation.
   - Remove `kill_agent_runner_group(artifacts_dir)` from `maybe_handoff_monitor_from_agent()`.
   - Return exit code `0` with confirmation that the monitor is running in the background and will take over the lane upon turn completion.
3. **`sase gate create` (`src/sase/gate_turn/agent_handoff.py`)**:
   - Remove `kill_agent_runner_group(artifacts_dir)`.
   - Return exit code `0`, staging `.sase_gate_pending`.
4. **`sase pipe` & `sase questions`**:
   - Update `pipe_handler.py` and `questions_command_handler.py` to stage their intents without invoking `kill_agent_runner_group`.

### 5.2 Step 2: Unblock Finalizers on Handoff Turns

In `src/sase/finalizers/controller_context.py`:
- Currently:
  ```python
  def should_skip_finalizers(artifacts_dir: str | None) -> bool:
      if not artifacts_dir:
          return True
      if not os.environ.get("SASE_AGENT_TIMESTAMP"):
          return True
      return has_pending_handoff(artifacts_dir)
  ```
- **Change:** Remove `has_pending_handoff(artifacts_dir)`. Handoff turns MUST execute finalizers so that all file changes made prior to the handoff are committed.
- In `src/sase/agent/pending_handoff_write.py`: Adjust `_refuse_finalizer_owned_handoff` to ensure that while finalizer-owned turns (e.g., commit recovery turns) cannot stage handoffs, an ordinary turn that staged a handoff is fully authorized to run finalizers.

### 5.3 Step 3: Wire Post-Finalization Handoff in the Runner

In `src/sase/axe/run_agent_exec.py` (and `run_agent_runner_launch.py`):
1. The execution loop runs `execute_workflow(...)`. The provider exits cleanly (exit code `0`).
2. `_invoke.py` proceeds to `run_finalizers(...)`.
3. The host executes `builtin@commit`:
   - If dirty repositories exist, the agent's submitted manifest commits them.
   - If no repositories are dirty, commit finalization passes cleanly.
4. **New Post-Finalization Hook:**
   - Check `pending_handoff_kind(artifacts_dir)`.
   - If a handoff is pending:
     - For `plan`: Call `handle_plan_marker(...)` to instantiate the plan gate turn or auto-approve and launch child epics.
     - For `monitor`: Call `handle_monitor_marker(...)` to hand the lane and workspace over to the monitor continuation.
     - For `gate`: Call `handle_gate_marker(...)` to activate the gate shell.
   - Note: Because the LLM provider was not killed, the real agent response is preserved in the chat history (`save_chat_history`), eliminating the need for synthetic transcript fallbacks.

### 5.4 Step 4: Update Declaration Manifest Rules & Tooling

In `src/sase/finalizers/declaration_store.py` and `declaration_manifest_commit.py`:
- Ensure that `sase final context -f json` clearly indicates requirements:
  - If `repository_obligations` is empty: `submission_required: false`. The agent can run `sase final submit` with an empty manifest or simply invoke `/sase_final` which auto-resolves clean state.
  - If `repository_obligations` is non-empty: `submission_required: true`. The agent provides commit messages for dirty repositories as normal.
- Update `sase_final` skill instructions:
  - Remove: *"Only a successfully executed plan, monitor, pipe, or questions handoff is exempt."*
  - Replace with: **"Every root SASE agent turn must conclude with `/sase_final`. If you staged a plan proposal, monitor, or gate during your turn, submitting your final declaration is what commits your work and triggers the handoff."**

---

## 6. Edge Cases & Special Considerations

### 6.1 Monitors Testing Uncommitted Workspace Diffs
**The Issue:** What if an agent starts a monitor specifically to run tests on uncommitted code before deciding whether to commit?
**The Solution:** SASE already has a first-class feature for this: **Prepared Host Completion** (`sase final prepare` + `sase monitor start -p verify -f <ref> -- just check`).
- In prepared completion, the agent prepares the commit manifest *without* committing. The monitor runs `just check` against the dirty tree.
- If the monitor passes, the host executes the commit postcondition without spawning another LLM turn.
- If the monitor fails, the continuation agent inherits the dirty tree to fix the failure.
- This existing mechanism remains unchanged and handles the "verify uncommitted diff" use case cleanly. Ordinary monitors (`sase monitor start` without `-f`) can safely commit any existing workspace work before starting.

### 6.2 Pre-existing Repository Dirt (Baselines)
If an agent starts in a workspace that already had dirty files from a predecessor (as in monitor continuations or dirty clones), `finalizer_baseline.json` tracks those pre-existing fingerprints. The commit finalizer already distinguishes between new dirt authored by this turn and pre-existing dirt. This protection ensures that an agent proposing a plan only commits files it actually touched.

### 6.3 Assigned Bead Closure vs. Plan Proposal
In lander prompts (such as `bob-cli-dw.land`), when a lander closes an epic, it runs `sase bead close <epic-bead>`. It may also propose a successor epic plan (`tier: epic`).
Under the new model:
- The lander closes the current bead.
- The lander edits any plan frontmatter in `plans/`.
- The lander proposes the successor plan with `sase plan propose`.
- The lander calls `/sase_final` to commit the plan edits and closeout evidence.
- The host commits the changes, verifies the bead closure, and transitions to the successor plan review. Everything happens cleanly in a single turn without work loss!

---

## 7. Migration & Memory Updates

To enact this change, the following durable memory notes and decision records should be updated:

1. **`decisions:gates-never-block`**:
   - Update the claim: Gates still never block an agent from waiting on human review. However, creating a gate shell no longer kills the agent with `SIGTERM` mid-tool call; rather, the agent stages the gate and concludes its turn through host finalization, which then transfers control to the gate shell.
2. **`decisions:host-owned-completion`**:
   - Update the claim: Remove the mechanical exemptions for `/sase_plan`, `/sase_monitor`, and `/sase_gate`. Completion is 100% host-owned across *all* root agent turns.
3. **`sase/memory/gotchas.md` & `sase/memory/lint_and_test.md`**:
   - Document that plan proposals and monitor starts do not terminate the process, and remind developers that turns staging handoffs must invoke `/sase_final`.
4. **Skills Updates**:
   - Deploy regenerated skills for `sase_plan`, `sase_monitor`, `sase_gate`, and `sase_final`.

---

## 8. Conclusion & Recommendation

The proposal to eliminate mid-turn agent kills for gates and monitors is an outstanding improvement that resolves persistent data loss bugs in SASE.

**Recommendation Summary:**
1. **Adopt the core change:** Stop killing agents in `sase plan propose`, `sase monitor start`, and `sase gate`.
2. **Do not overload `builtin@commit`:** Keep `builtin@commit` focused on git stitches.
3. **Implement the Staged Intent pattern:** Stage handoffs during the turn, run universal host finalizers upon turn exit, and trigger the handoff transition immediately after finalizers succeed.
4. **Require `/sase_final` universally:** Unify the agent completion contract so that every root turn declares its state and all dirty workspace changes are safely committed.
