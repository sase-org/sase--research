# SASE Goals: Architecture, User Experience, Verification, and Lifecycle Design

**Author:** Researcher `gem` (5-Researcher Swarm)  
**Date:** September 2026  
**Status:** Research Report & Technical Design  
**Target:** SASE Core (`sase-core`), Runner (`sase`), and TUI (`ace`)  

---

## Executive Summary

The transition of SASE from **process-centric orchestration** (agent turns, stitches, subprocess lifecycles) to **outcome-centric software engineering** (goals, claims, evidence, and human verification) is one of the most consequential architectural evolutions in the project's history.

Currently, SASE agents operate at the level of commands, commits, and process runs. When an agent finishes its work, the system emits an unread notification and a `JumpToAgent` attention item. In simple single-turn interactions, this is acceptable. In modern SASE workflows—where an epic or tale plan may coordinate a planner, multiple phase implementations, retries, code reviews, and landing routines—this process-level noise becomes actively harmful. The user is pinged dozens of times for intermediate milestones that require no human action, diluting the signal until critical completion events are ignored.

This report conducts an independent, rigorous architectural and UX investigation into adding first-class **Goals** to SASE. We evaluate the core requirements, critique the initial user proposals (including the agent-side `SASE_PLAN` check and planner exemptions), resolve UX concerns around user prompting burden and agent autonomy, and formulate a complete, end-to-end technical design spanning the Rust core backend, launcher, finalizer pipeline, TUI presentation, and distributed sidecar storage.

### Key Conclusions & Design Highlights

1. **Host-Owned Launch Invariant, Not Agent-Side Skills:** The requirement that *"all SASE agents MUST have a goal defined"* cannot rely on the agent inspecting environment variables (`SASE_PLAN`) or calling skills (`/sase_new_goal`) on turn 1. In SASE, host invariants fail closed at the host boundary. The launcher binds every agent to a primary goal at spawn time before the model is invoked.
2. **Zero User Prompting Burden with Full Agent Agency:** Users do *not* need to explicitly specify `--goal "..."` on every invocation. For plan-backed runs, the plan's mandatory `goal` is inherited; for bead-backed runs, the bead intent is used; for ad-hoc prompts, the launcher derives the goal intent directly from the content-addressed `submitted_xprompt.md`. Once running, agents retain full agency: they can refine goal titles, decompose goals into sub-goals, or record structured acceptance criteria via a dedicated `/sase_goal` tool.
3. **No Planner Exemption:** Planners are goal-directed units of work (e.g., "Design architectural plan for auth refactor"). Exempting planners creates an untracked blind spot. When a plan is proposed and approved, the goal seamlessly transfers to the execution phase or is marked satisfied as a plan-delivery outcome.
4. **Outcome-Specific Evidence Hierarchy (`builtin@goal` Finalizer):** A goal cannot be closed on uncorroborated agent prose. Closing a goal requires a host-enforced finalizer submission ordered after `builtin@commit`, demanding concrete, durable evidence: host-verified stitch refs (`$CURRENT_COMMIT`) and test receipts for code, registered artifact refs for research/documentation, or validated plan refs for planning. Every close claim must also include a human verification hint executable in under 60 seconds.
5. **Attention Overhaul: Notify on Goal Claims, Not Process Exits:** Normal agent completion (`keep_open`) becomes silent in the user notification channel. Only when an agent submits a `close` claim does the goal transition to `needs_review` and emit a high-priority `JumpToGoal` notification.
6. **Dual-Surface TUI Design:** An intuitive and beautiful UX combines a project-wide **Goals Pane** in the Artifacts tab (`Artifacts > Goals`, shortcut `5` or `g`) featuring two visual lanes (**Needs Review** and **In Progress**), with contextual **Goal Chips** and `by goal` grouping on the **Agents Tab**, linked via the closed Artifact Link Graph (`pursues`, `evidences`, `defines`).
7. **Strict $O(n_{\text{unsettled}})$ Lightning-Fast Performance:** Goals are split in durable storage between hot active state (`goals/active/`) and cold historical archives (`goals/settled/YYYYMM/`). Foreground reads query a compact materialized projection (`active_goals.json`) or SQLite partial index, guaranteeing that performance scales with unsettled goals ($n \approx 5\text{--}50$), completely unaffected by thousands of historical settled records.

---

## 1. Critique of the Initial Plan & Core Architecture

### 1.1 Is "Goals" a Good Idea?

**Emphatically, yes.** Introducing first-class Goals addresses the single largest usability friction in multi-agent autonomous engineering: **notification fatigue and the loss of intent traceability.**

In the current SASE architecture:
- An agent is a temporary process execution turn.
- A stitch is a commit delta.
- A bead is an issue/task tracker item.
- A plan is a multi-phase implementation specification.

None of these represent the *intent* of the human operator across the entire lifecycle of an outcome. When a user asks SASE to "investigate and fix the intermittent timeout in test_auth", that intent may involve an exploratory agent, a bug bead, a tale plan, two code-writing turns, and a verification test. Today, each of these turns fires a completion event (`JumpToAgent`). The user must mentally stitch together whether the overall task succeeded, was abandoned, or is still waiting on another phase.

Goals provide the missing durable spine that unifies prompt provenance, contributing agents, produced artifacts, and human sign-off into an atomic, verifiable unit.

### 1.2 Critique of the Agent-Side `SASE_PLAN` & `/sase_new_goal` Proposal

The user prompt proposed:
> *"One idea for implementing this would be to require that every sase agent that is NOT tasked with creating a plan using the /sase_plan skill... check if the `SASE_PLAN` environment variable is set at the start of EVERY conversation. If not, it could invoke a new `/sase_new_goal` xprompt skill."*

While intuitive at first glance, this approach has several critical architectural failure modes:

| Failure Mode | Mechanism | Architectural Impact |
| :--- | :--- | :--- |
| **Violation of Host-Owned Invariants** | Relying on an LLM to read an env var and invoke a skill on turn 1 is probabilistic. LLMs frequently skip preamble instructions, prioritize user queries, or misread variables under context pressure. | Breaks the core invariant: *"All SASE agents MUST have a goal defined."* An invariant cannot depend on agent compliance. |
| **Swarm Concurrency & Race Conditions** | In a 5-researcher swarm (such as this one) launched from a single user prompt, 5 parallel agents start without a plan. If each runs `/sase_new_goal`, 5 duplicate goals will be created simultaneously for the same request. | Fragmented state, conflicting notification storms, and race conditions in sidecar Git commits. |
| **`SASE_PLAN` Hygiene & Scoping** | In `src/sase/agent/launch_spawn.py`, `_remove_inherited_sase_plan_env()` explicitly purges `SASE_PLAN` to prevent ambient plan pollution across workspace boundaries. `SASE_PLAN` was designed as a commit-tagging mechanism, not a runtime goal identifier. | Coupling goal tracking to `SASE_PLAN` leaks plan attribution and breaks environment hygiene. |
| **Loss of Prompt Provenance** | If the agent invents the goal body dynamically during its first turn, the immutable cryptographic link between the *exact user-submitted launch prompt* and the goal is degraded to an LLM hallucination of that prompt. | Breaches the requirement: *"Goals should be associated with the original prompts that were used to launch the sase agent."* |

**The Architectural Correction:**
The host launcher must own goal establishment at spawn time. Before the agent process is spawned or the model context is assembled, the host identifies or constructs the goal, records its provenance, and passes `SASE_GOAL_ID=<id>` as an immutable context binding.

### 1.3 Critique of the Planner Exemption

The proposal suggested exempting planner agents from having a goal. This is an anti-pattern:
1. **Planning is Work:** A user launching a planner has an explicit goal: *"Formulate an implementation plan for the migration."*
2. **Delivery & Verification:** Delivering a plan is an outcome. The plan artifact itself (`plan:YYYYMM/name.md`) is the evidence that satisfies the planning goal.
3. **Continuity:** When an approved plan is launched, the goal transitions seamlessly from *Planning* to *Execution*. Exempting planners would leave planning turns unmonitored and notification-silent, or force them back onto noisy legacy completion paths.

**Adjustment:** Planner agents are **not** exempt. They bind to the incoming request goal. When the planner completes, it submits its validated plan artifact as evidence to close the planning phase or transition the goal to active plan execution.

### 1.4 Addressing User Prompting Burden vs. Agent Autonomy

The user expressed a major concern:
> *"I'm worried that we are not letting agents set their own goals. I might be wrong about this, but doesn't that mean that users would always need to set the goal explicitly? That doesn't sound like a good design, if so, since it adds an extra burden on the user crafting the prompt."*

This is a perceptive concern, but it arises from a false dichotomy: *either the user must manually type `--goal` on every CLI call, or the agent must invent its own goal unconstrained.*

We solve this cleanly with **Tiered Launch Resolution and In-Turn Agent Refinement**:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Launch-Time Resolution                          │
│                                                                        │
│  1. Plan-Bound Run      ───► Inherit Plan's mandatory `goal` field     │
│  2. Bead-Bound Run      ───► Derive Goal from Bead title/intent        │
│  3. Follow-up / Swarm   ───► Inherit parent Goal (shared objective)    │
│  4. Ad-Hoc User Prompt  ───► Derive Goal from `submitted_xprompt.md`   │
│                              (Zero extra user keystrokes required)     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        In-Turn Agent Refinement                        │
│                                                                        │
│  Agent can invoke `/sase_goal` tool to:                                │
│  • Refine goal title or acceptance criteria                            │
│  • Decompose goal into sub-goals                                       │
│  • Link auxiliary active goals                                         │
└────────────────────────────────────────────────────────────────────────┘
```

- **Zero User Burden:** The user simply types `sase "fix the redis connection pool leak"` or `sase -m claude "explain the rust core binding"`. The host automatically establishes the goal from the launch prompt. No flags, no extra prompting syntax.
- **Full Agent Agency:** The agent is not locked into a rigid, unchangeable string. If the agent discovers during turn 1 that the problem is actually in connection timeouts rather than pool sizing, it can call `sase goal update --title "Fix Redis connection timeouts under load"` to sharpen the outcome statement.

---

## 2. Core Domain Model & Lifecycle

### 2.1 The Goal Wire Specification (`sase-core`)

In adherence to the **Rust Core Backend Boundary** (`rust_core_backend_boundary`), the core goal state machine, wire types, serialization, and validation must live in the `sase_core` crate (`crates/sase_core/src/goal/`).

```rust
// crates/sase_core/src/goal/wire.rs

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GoalStatusWire {
    Active,         // Work is underway by one or more agents
    NeedsReview,    // Agent claimed completion with evidence; awaits human verification
    Verified,       // Human verified the claim (Terminal Cold State)
    Waived,         // Human accepted outcome without full verification (Terminal Cold State)
    Rejected,       // Human rejected the claim; reopens to Active with feedback
    Canceled,       // Explicitly abandoned by human or orchestrator (Terminal Cold State)
    Superseded,     // Replaced by a successor goal (Terminal Cold State)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GoalOutcomeKindWire {
    CodeChange,     // Produces stitches, diffs, or operational changes
    ResearchDoc,    // Produces reports, analyses, or documentation
    PlanDelivery,   // Produces validated implementation plans
    AnswerOrReview, // Directly answers a user query or provides code review
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GoalEvidenceWire {
    pub kind: String,           // "stitch", "receipt", "plan", "research", "transcript"
    pub reference: String,       // e.g. "stitch:sase:a1b2c3d", "receipt:just-check-pass"
    pub digest: String,          // Cryptographic hash of the referenced artifact
    pub description: String,     // Brief explanation of why this supports the claim
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GoalWire {
    pub schema_version: u64,
    pub goal_id: String,                     // Canonical ID: "goal:<project>:<ulid_or_slug>"
    pub title: String,                       // Short descriptive title (< 120 chars)
    pub outcome_kind: GoalOutcomeKindWire,
    pub status: GoalStatusWire,
    pub project: String,
    
    // Provenance
    pub creator_agent_id: String,
    pub origin_prompt_digest: String,       // SHA-256 of the submitted unit prompt
    pub origin_prompt_relpath: String,      // Relpath to archived submitted_xprompt.md
    pub created_at: String,
    pub updated_at: String,
    
    // Associations
    pub plan_ref: Option<String>,           // Associated plan if applicable
    pub bead_id: Option<String>,            // Associated bead if applicable
    pub contributing_agent_ids: Vec<String>,
    
    // Lifecycle & Verification Claims
    pub claim: Option<String>,              // Agent's closure assertion
    pub verification_hint: Option<String>,  // Quick human check instructions (under 60s)
    pub evidence: Vec<GoalEvidenceWire>,
    pub human_feedback: Option<String>,     // Feedback provided upon Rejection or Waive
}
```

### 2.2 The Goal Lifecycle State Machine

The goal lifecycle cleanly decouples **Agent Claim** from **Human Verification**:

```text
                 ┌─────────────────────────────────────────────────┐
                 │                     Active                      │
                 │        (Agent(s) actively working)              │
                 └──────────────┬─────────────────────────▲────────┘
                                │                         │
                   builtin@goal │                         │ Reject claim
                     submission │                         │ (with feedback)
                      (action:  │                         │
                       "close") │                         │
                                ▼                         │
                 ┌────────────────────────────────────────┴────────┐
                 │                  Needs Review                   │
                 │       (Emits JumpToGoal notification to user)   │
                 └───────┬────────────────────────┬────────────────┘
                         │                        │
            Human clicks │           Human clicks │
             [v] Verify  │             [w] Waive  │
                         ▼                        ▼
                 ┌───────────────┐        ┌───────────────┐
                 │   Verified    │        │    Waived     │
                 │ (Cold Archive)│        │ (Cold Archive)│
                 └───────────────┘        └───────────────┘
```

1. **Active:** One or more agents are pursuing the goal. When agents finish with `keep_open`, the goal remains `Active`. No user notification is generated.
2. **Needs Review:** An agent executes `builtin@goal` with action `close` and attaches valid evidence. The host transitions the goal to `Needs Review` and emits **`JumpToGoal`**. The goal is *not* done; it is pending verification.
3. **Verified:** The user reviews the claim and evidence, checks the verification hint, and confirms the outcome (`sase goal verify <id>` or pressing `v` in the TUI). It enters the cold historical archive.
4. **Waived:** The user accepts the outcome without strict verification (`w` in TUI). Enters cold archive.
5. **Rejected:** The user reviews the claim, finds the test incomplete or the answer flawed, and presses `r` in the TUI (entering feedback). The goal immediately reverts to `Active`, ready for follow-up turns.

---

## 3. Launch Invariant & Prompt Provenance

### 3.1 Host-Owned Launch Binding Architecture

The launcher (`src/sase/agent/launch_spawn.py` and `src/sase/axe/run_agent_runner_setup_prompt.py`) establishes the goal binding deterministically across every launch surface:

```text
User Command / Swarm / API
           │
           ▼
┌────────────────────────────────────────────────────────┐
│            Host Launcher Admission Gate                │
│                                                        │
│  Check launch parameters:                              │
│  • Does --plan exist?     ──► Bind plan.goal_id        │
│  • Does --bead exist?     ──► Bind/create bead.goal_id │
│  • Is this a child/swarm? ──► Inherit parent goal_id   │
│  • Is this an ad-hoc run? ──► Create new goal from     │
│                               submitted_xprompt.md     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│             Durable Provenance & Env Injection         │
│                                                        │
│  1. Write submitted_xprompt.md (immutable SHA-256)     │
│  2. Record goal binding in active sidecar projection   │
│  3. Inject SASE_GOAL_ID into spawned agent env         │
│  4. Inject Goal Context block into system instructions │
└────────────────────────────────────────────────────────┘
```

### 3.2 Provenance of Original Prompts

A key requirement is:
> *"Goals should be associated with the original prompts that were used to launch the sase agent that created the goal."*

SASE already implements `write_submitted_xprompt_artifact()` in `run_agent_runner_setup_prompt.py`, which records the raw, unexpanded launch prompt into `submitted_xprompt.md` before alias expansion.

We extend this into a durable provenance contract:
1. **Content Addressing:** The goal stores `origin_prompt_digest = sha256(submitted_xprompt)`.
2. **Sidecar Archival:** In the `agents` sidecar repository, the prompt is stored at `prompts/YYYYMM/<digest>.md`.
3. **Swarm Provenance:** When a swarm of 5 researchers is spawned from a single prompt, the launcher assigns all 5 researchers the exact same `goal_id` and records the single root prompt as the origin. Each researcher's individual turn prompt is tracked as a contributing step, but the root goal's origin prompt remains the unified prompt that launched the swarm.

---

## 4. Closure Evidence & The `builtin@goal` Finalizer Contract

### 4.1 The Finalizer Pipeline Integration

SASE has a mature, host-adjudicated finalizer framework (`crates/sase_core/src/finalizer/` and `src/sase/finalizers/`).

We introduce `builtin@goal` as a mandatory, required finalizer configured in `src/sase/default_config.yml`:

```yaml
finalizers:
  defaults: [commit, goal]
  required: [goal]
  instances:
    commit:
      use: builtin@commit
      after: []
      max_attempts: 2
      refusal: defer
    goal:
      use: builtin@goal
      after: [commit]  # MUST execute after commit to resolve commit artifacts
      max_attempts: 1
      refusal: fail
```

Because `goal` executes **after** `commit`:
- If the agent created code changes, `builtin@commit` has already generated the host-verified `stitch` commit.
- The host provides the special token `$CURRENT_COMMIT` in the goal obligation context, which resolves directly to the new stitch SHA.

### 4.2 Finalizer Submission Envelope

On every turn completion, the agent's finalizer manifest must contain a `goal` payload:

```json
{
  "instance_id": "goal",
  "payload": {
    "action": "close",
    "goal_id": "goal:sase-org/sase:01j8x92m4b8v",
    "claim": "Added RS256 JWT signature verification and passed all test suites.",
    "verification_hint": "Run `cargo test -p sase_auth` and verify the test_jwt_validation passes.",
    "evidence": [
      {
        "kind": "stitch",
        "reference": "$CURRENT_COMMIT",
        "description": "Implementation of RS256 validation logic in auth crate"
      },
      {
        "kind": "receipt",
        "reference": "receipt:just-check-pass",
        "description": "Clean run of `just check` fast gate"
      }
    ]
  }
}
```

If the agent has only completed an intermediate step (e.g., Phase 2 of a 5-phase epic), it declares:

```json
{
  "instance_id": "goal",
  "payload": {
    "action": "keep_open",
    "goal_id": "goal:sase-org/sase:01j8x92m4b8v",
    "progress_summary": "Completed Phase 2: data models and migrations. Phase 3 (API endpoints) pending."
  }
}
```

### 4.3 Mandatory Evidence Hierarchy

The host strictly validates submitted evidence based on the goal's `outcome_kind`. Unsubstantiated prose is rejected by the host validator:

| Outcome Kind | Minimum Mandatory Evidence | Host Verification Rules |
| :--- | :--- | :--- |
| **Code Change** | Host-verified `stitch` reference + clean test/check `receipt` | The host confirms the stitch exists in the repository and verifies that the `just check` receipt matches the current worktree SHA. |
| **Research / Document** | Registered durable artifact reference (`research:...`, `@research:...`, `file:...`) | The host verifies that `sase artifact show <ref>` resolves and matches the agent's output digest. |
| **Plan Delivery** | Validated archived `plan:` reference | The host verifies that the plan passed `sase plan validate` and is stored in the `plans` sidecar. |
| **Answer / Question** | Audited transcript or response artifact | The host verifies that the response was captured and recorded in the turn's audited conversation transcript. |

### 4.4 The "Human Verification Hint" Standard

Every `close` action **must** include a `verification_hint`. This is a non-empty string explaining how the user can verify the claim in under 60 seconds.

**Examples of good verification hints:**
- *"Run `sase goal list` and confirm the table renders with no flickering."*
- *"Open `http://localhost:8080/api/health` and verify it returns HTTP 200 with status 'ok'."*
- *"Read section 3 of the generated report in `research:202609/auth_design__gem.md`."*

**Rejected verification hints:**
- *"I tested it and it works."* (Self-attestation, not a human instruction)
- *"Trust me."* (Trivial/invalid)

---

## 5. User Experience & TUI Architecture: Intuitive, Reliable, Beautiful

The user explicitly stated:
> *"I like that outcomes are embraced as a primary value-add for this functionality but am worried that we did not focus enough on user experience. For example, how do I figure out, for a particular sase project, which goals are currently active? Once I've found that goal, how do I then jump to any artifact (including a running agent) that is linked with that goal? ... I want you to lead the design on this one. Make sure you design this feature so it is intuitive, reliable, and (last but not least) beautiful!"*

To deliver on this, we present a comprehensive, dual-surface UX design.

### 5.1 Dual-Surface Experience

1. **Artifacts > Goals Pane (`Artifacts` Tab):** The project-wide control room, triage center, and verification inbox.
2. **Agents Tab Integration:** Contextual goal chips on every agent row, `by goal` grouping mode, and an Agent Goal Card in the inspector.

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │ SASE ACE  [Agents]  [Artifacts]  [Services]       🎯 2 to verify   09:41│
 ├────────────────────────────────────────────────────────────────────────┤
 │ [1 Agents] [2 Stitches] [3 Patches] [4 Beads] [5 Goals] [6 Plans]      │
 │                                                                        │
 │  ╭─ Needs Review (2 claims awaiting human verification) ─────────────╮ │
 │  │ STATUS   GOAL / CLAIM               CONTRIBUTORS  EVIDENCE   TIME │ │
 │  │ ◉ REVIEW Add RS256 JWT auth         3 agents      1 stitch   2m   │ │
 │  │          ↳ Claim: Passed cargo test; token validation functional  │ │
 │  │          ↳ Hint: Run `cargo test -p auth` (Press [v] to verify)   │ │
 │  │ ◉ REVIEW Research Goals TUI UX      5 agents (gem) 1 report  12m  │ │
 │  │          ↳ Hint: Inspect section 5 in research report             │ │
 │  ╰───────────────────────────────────────────────────────────────────╯ │
 │  ╭─ In Progress (3 active goals) ────────────────────────────────────╮ │
 │  │ STATUS   GOAL TITLE                 CONTRIBUTORS  PLAN/BEAD  TIME │ │
 │  │ ◈ ACTIVE Fix Redis timeout under load  1 agent    bead:142    8m  │ │
 │  │ ◈ ACTIVE Refactor tool control plane  2 agents    plan:09/tcp 45m │ │
 │  │ ◈ ACTIVE Implement Lumberjack chop    1 agent    —          1h12m │ │
 │  ╰───────────────────────────────────────────────────────────────────╯ │
 ├────────────────────────────────────────────────────────────────────────┤
 │ [v] Verify   [w] Waive   [r] Reject & Reopen   [Enter] Inspect Details │
 └────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Visual Hierarchy & Styling Rules

In accordance with SASE TUI standards:
- **Restrained, Semantic Accents:**
  - `Needs Review`: Warm Amber (`#FFAF00`) or Gold (`#FFD700`)—signals attention without emergency alarm.
  - `Active`: Calm Teal (`#00D7AF`) or Cyan—signals steady forward progress.
  - `Verified`: Subdued Emerald (`#5FAFAF`)—reassuring, low salience.
  - `Rejected`: Soft Coral (`#FF5F5F`)—clear indication of requested rework.
- **Never Color Alone:** Every state is accompanied by a distinct glyph and clear uppercase text (`◉ REVIEW`, `◈ ACTIVE`, `✓ VERIFIED`, `✕ REJECTED`).

### 5.3 Goal Detail View & Artifact Link Jumping

When the user selects a goal and presses `Enter`, the TUI opens the **Goal Detail Inspector**:

```text
╭─ Goal: Add RS256 JWT auth · goal:sase:01j8x92m4b8v ─────────────────────╮
│ Status: NEEDS REVIEW (Claimed 2m ago by agent:a4.w0.w2)                 │
│ Kind:   Code Change                                                     │
│                                                                         │
│ ╭─ Original Launch Prompt ────────────────────────────────────────────╮ │
│ │ "We need RS256 JWT validation for incoming authorization headers.   │ │
│ │ Make sure to handle clock skew of up to 60 seconds and reject       │ │
│ │ expired tokens immediately with 401."                               │ │
│ ╰─────────────────────────────────────────────────────────────────────╯ │
│                                                                         │
│ ╭─ Completion Claim & Evidence ───────────────────────────────────────╮ │
│ │ Claim: Implemented RS256 validation; added tests in auth_test.rs.   │ │
│ │ Hint:  Run `cargo test -p sase_auth` to verify rejection of skew.   │ │
│ │                                                                     │ │
│ │ Evidence Artifacts:                                                 │ │
│ │ • [Stitch] stitch:sase:9b8f2d "feat(auth): add RS256 JWT validation"│ │
│ │ • [Receipt] receipt:just-check-pass (All gates green)               │ │
│ │ • [Plan]    plan:202609/jwt_auth.md                                 │ │
│ ╰─────────────────────────────────────────────────────────────────────╯ │
│                                                                         │
│ ╭─ Contributing Agents (3) ───────────────────────────────────────────╮ │
│ │ • a4.w0.w0 (Planner)     ── Plan approved                           │ │
│ │ • a4.w0.w1 (Phase 1 Impl)── keep_open                               │ │
│ │ • a4.w0.w2 (Phase 2 Impl)── close (Claimed completion)              │ │
│ ╰─────────────────────────────────────────────────────────────────────╯ │
╰─────────────────────────────────────────────────────────────────────────╯
 [v] Verify   [w] Waive   [r] Reject   [Enter on Agent] Jump to Agent Tab
```

#### Seamless Jumping via the Closed Artifact Relation Graph

SASE's relation registry (`docs/artifact_links.md`) is extended with:
- `pursues` / `pursued-by`: Links an `agent` to its primary `goal`.
- `evidences` / `evidenced-by`: Links an `artifact` (stitch, report, plan) to the `goal`.
- `defines` / `defined-by`: Links a `plan` to the `goal`.

**How Jumping Works in Practice:**
1. **From Goals Pane to Agent:** Highlighting `a4.w0.w2` in the contributing agents list and pressing `Enter` performs a seamless cross-tab jump to the **Agents Tab**, focusing `a4.w0.w2`'s row and opening its chat transcript.
2. **From Goals Pane to Diff/Stitch:** Highlighting `stitch:sase:9b8f2d` and pressing `Enter` opens the TUI Diff Viewer for that exact commit.
3. **From Agents Tab to Goal:** On the Agents tab, every agent row displays a compact chip: `🎯 [jwt-auth]`. Pressing `g` while on that agent jumps directly to the Goals pane with that goal selected!
4. **Grouping by Goal on Agents Tab:** Pressing `Shift+G` on the Agents tab toggles the agent list grouping mode from `chronological` / `by clan` to `by goal`. All agents collaborating on the same outcome are grouped under a single visual goal banner.

---

## 6. Attention & Notification Redesign

### 6.1 The Noise Problem Solved

| Old Behavior (Process-Centric) | New Behavior (Outcome-Centric) |
| :--- | :--- |
| Agent 1 (Planner) exits -> **BEEP / Unread Dot** | Agent 1 exits -> Logged silently in agent history. Goal stays `Active`. |
| Agent 2 (Phase 1) exits -> **BEEP / Unread Dot** | Agent 2 exits with `keep_open` -> Logged silently. Goal stays `Active`. |
| Agent 3 (Phase 2) exits -> **BEEP / Unread Dot** | Agent 3 exits with `close` -> **`JumpToGoal` Notification!** |
| User overwhelmed by 3 pings for 1 task | User receives **exactly 1 alert** when verification is needed. |

### 6.2 Attention Notification Contract

1. **`JumpToGoal` Payload:**
   When an agent triggers `needs_review`, the host runner dispatches a high-priority attention item:
   ```json
   {
     "action": "JumpToGoal",
     "action_data": {
       "goal_id": "goal:sase:01j8x92m4b8v",
       "goal_title": "Add RS256 JWT auth",
       "claim": "Implemented RS256 validation; added tests in auth_test.rs.",
       "verification_hint": "Run `cargo test -p sase_auth` to verify rejection of skew.",
       "closing_agent": "a4.w0.w2"
     }
   }
   ```
2. **Top-Bar Attention Counter:**
   The TUI header bar displays `🎯 <N> to verify` whenever $N > 0$. Pressing `Ctrl+G` from anywhere in the TUI immediately jumps to the first pending claim in the Goals pane.
3. **Preserving Operational Alerts:**
   - Agent crashes, unhandled errors, and timeouts still immediately notify via `ViewErrorReport` / `JumpToAgent` (failed).
   - Interactive gates (`GateTurn`) and question prompts still notify immediately.
   - Only *successful intermediate execution turns* are silenced.

---

## 7. Distributed Storage & Lightning-Fast $O(n)$ Performance

The prompt mandates:
> *"The above requirements imply that sase agents need access to all active goals (really, any human/agent working on a sase project from any machine needs this access). This access needs to be lightning fast. More specifically, we should aim for `O(n)` performance, where `n` is the number of active goals (so done goals have no effect on performance)."*

### 7.1 The Storage Model: Active vs. Settled Partitioning

To guarantee that done goals have zero performance impact, we implement a **physical directory partitioning** in the shared `agents` sidecar repository:

```text
sase/repos/sidecars/agents/
├── goals/
│   ├── active/                             <── HOT SET (O(n_unsettled))
│   │   ├── goal_01j8x92m4b8v.json
│   │   └── goal_01j8x99k1z4m.json
│   ├── projection/
│   │   └── active_goals.json               <── Materialized Cache (O(1) read)
│   └── settled/                            <── COLD ARCHIVE (Never read in hot paths)
│       ├── 202607/
│       │   └── goal_01j4k...json
│       ├── 202608/
│       │   └── goal_01j6p...json
│       └── 202609/
│           └── goal_01j7q...json
```

1. **Hot Active Store (`goals/active/`):**
   Contains *only* unsettled goals: `status IN ('active', 'needs_review')`. In typical project operation, $n \approx 5\text{--}50$.
2. **Cold Historical Store (`goals/settled/YYYYMM/`):**
   When a goal is `verified`, `waived`, `canceled`, or `superseded`, the host atomically moves the JSON file from `active/` to `settled/YYYYMM/`.
3. **Materialized Hot Projection (`active_goals.json`):**
   A single, compact JSON file containing an array of all active goals with minimal summary fields (ID, title, status, last activity, contributor count).
   - Foreground reads (`sase goal list` or TUI header render) read **one file** from disk.
   - Time complexity: $O(n_{\text{unsettled}})$ to deserialize ~30 KB. Read time is under **1 millisecond**.
   - Even if the repository accumulates 50,000 completed goals over 3 years, foreground query latency remains completely flat.

### 7.2 Cross-Machine Synchronization Protocol

SASE operates across multiple machines (local desktop, laptop, remote servers, Apollo/Athena dispatch hosts). Shared state is synchronized via Git sidecar push/pull.

**The Publication Transaction:**
1. **Atomic Mutation:** Modifying a goal (e.g. `needs_review` or `verified`) is committed to the local `agents` sidecar checkout.
2. **Host Sidecar Auto-Sync:** In accordance with Decision `machine-link-writes-off-primary`, writes happen in the host-owned machine lane and push to the remote tracking branch.
3. **Optimistic Concurrency & Watermarking:**
   - Every goal has a monotonic `revision` integer and a `last_modified_machine` tag.
   - The TUI displays a subtle sync status in the Goals pane header: `Synced 12s ago · apollo`.
   - If two machines concurrently update the same goal (e.g. machine A claims close while machine B attaches a new contributor), Git merges the two event rows. If an irreconcilable conflict occurs, the goal defaults to `active` with a visible conflict banner.

---

## 8. CLI Specification

Every capability available in the TUI must have a fully functional CLI counterpart:

```bash
# 1. Listing Goals (Lightning fast, reads active projection)
sase goal list                       # Pretty table of Active & Needs Review goals
sase goal list --all                 # Includes cold settled goals (paged)
sase goal list --json                # Structured JSON output for scripts/agents

# 2. Inspecting a Goal
sase goal show <goal-id>             # Full detail: prompt, claim, evidence, contributors

# 3. Agent Goal Management (Used by agents or humans)
sase goal update <goal-id> --title "New Title" --criteria "Must pass benchmarks"
sase goal link <goal-id>             # Bind current agent/session to existing active goal

# 4. Human Verification Actions
sase goal verify <goal-id>           # Confirms verification; moves to cold archive
sase goal waive <goal-id> "Reason"   # Waives strict verification with explanation
sase goal reject <goal-id> "Reason"  # Reopens goal to Active with mandatory feedback
sase goal cancel <goal-id> "Reason"  # Explicitly cancels an abandoned goal
```

---

## 9. Phased Implementation Roadmap

To deliver this functionality with high reliability, we recommend a 5-phase implementation plan:

### Phase 1: Rust Core Domain Model & Wire Protocol (`sase-core`)
- Implement `crates/sase_core/src/goal/` containing `GoalWire`, `GoalStatusWire`, `GoalEvidenceWire`, and state transition logic.
- Implement serialized active goal projection builder and validation.
- Add PyO3 Python bindings in `sase_core_rs`.
- Ratchet `sase-core-revision.txt` in the main repo.

### Phase 2: Host Launch Binding & Provenance Integration
- Update `src/sase/agent/launch_spawn.py` and `src/sase/agent/launcher.py` to resolve and establish primary goals at spawn time.
- Update `src/sase/axe/run_agent_runner_setup_prompt.py` to link `submitted_xprompt.md` digest to the goal.
- Inject `SASE_GOAL_ID` into agent environments and add the Goal Context block into default agent instructions.
- Ensure swarms and fan-outs bind all worker agents to the single parent goal.

### Phase 3: The `builtin@goal` Finalizer
- Implement `src/sase/finalizers/goal.py` providing `builtin@goal`.
- Configure `goal` in `default_config.yml` as required, executing after `builtin@commit`.
- Implement evidence validation (resolving `$CURRENT_COMMIT` to stitch ref, checking receipts, verifying artifact references).
- Implement the transition to `needs_review` on valid `close` actions.

### Phase 4: Attention & Notification Cutover
- Update `src/sase/axe/run_agent_runner_finalize.py`:
  - Suppress default `JumpToAgent` on normal success turns when `keep_open` is selected.
  - Emit `JumpToGoal` whenever `builtin@goal` executes a `close` claim.
- Add top-bar unverified goal counter to ACE TUI.

### Phase 5: TUI Goals Pane & Agent Tab Integration
- Add `goals` pane to Artifacts tab registry (`src/sase/ace/tui/artifact_tabs.py`) with shortcut `5` / `g`.
- Build the two-lane view (`Needs Review` and `In Progress`) with action keys `[v]`, `[w]`, `[r]`.
- Add Goal chips to agent rows in the Agents tab and implement `Shift+G` grouping mode (`by goal`).
- Connect cross-tab jumps between Goals and Agents/Stitches/Plans via the Artifact Link Graph.

---

## 10. Conclusion & Recommended Solution

The addition of Goals transforms SASE from a low-level agent runner into a goal-directed autonomous engineering platform.

By replacing the fragile idea of agent-side `SASE_PLAN` checking with **host-owned launch binding**, we preserve 100% reliability with zero prompting burden on the user. By placing the completion decision inside a formal **`builtin@goal` finalizer**, we prevent hallucinated claims and mandate durable evidence. By transitioning notifications from process exits to **Goal completion claims**, we eliminate notification fatigue. And by pairing an **Artifacts Goals Pane** with **Agents tab goal context**, we give users an intuitive, reliable, and beautiful window into the active life of their software projects.
