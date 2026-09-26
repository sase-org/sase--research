# Architectural Blueprint & Design: First-Class "Goals" in SASE

**Author:** researcher gem (`research.2m.gem`)  
**Date:** 2026-09-26  
**Status:** Research Proposal & Architectural Critique  
**Target Repository:** `sase` (linked: `sase-core`, sidecars: `goals`, `plans`, `beads`, `agents`)  

---

## 1. Executive Summary

This research investigates the addition of a first-class **Goals** capability to SASE. 

The user's core intent is twofold:
1. **Semantic Elevation:** Elevate agent work from fragmented, low-level execution turns into durable, outcome-oriented objectives associated directly with original user prompts and plans.
2. **Attention Hygiene (Notification Fatigue Reduction):** Replace noisy "agent completion" notifications—where every single intermediate agent turn, replan, or phase ping triggers an unread dot or chime—with **Goal Completion notifications**, notifying the human operator only when an actual high-level objective is declared done and supported by verifiable evidence.

### Strategic Verdict
The motivation is sound and addresses one of the most prominent friction points in modern agent swarms: **notification overload and lost high-level context**. 

However, the initial implementation proposal contains several architectural antipatterns that would introduce severe operational friction if implemented literally:
* **The Agent-Side Check Flaw:** Requiring every agent to inspect `$SASE_PLAN` at the start of *every* conversation and invoke a `/sase_new_goal` skill violates SASE's `single-turn-agents` and `host-owned-completion` invariants, burns tool-call tokens, introduces conversational latency, and risks LLM hallucinations. **Resolution:** Goal resolution must be **host-owned at launch time**.
* **The Store Traversal Bottleneck:** Querying goals across historical runs must never degrade as project history grows. Traditional single-file append-only issue trackers (like `issues.jsonl`) degrade to $O(N)$ where $N$ is total history. **Resolution:** A **two-bucket state partition** (`active/` vs `archive/`) guarantees strict $O(n)$ performance where $n$ is only the count of active goals, providing sub-millisecond reads across all machines and workspaces with zero git merge conflicts.
* **The Evidence Ambiguity:** Closing a goal requires an objective, tamper-proof **Evidence Triad**: (1) an automated execution witness (command exit code + execution ref), (2) produced artifact references, and (3) a human-readable satisfaction rationale.

This report critiques the original proposal, establishes rigorous architectural adjustments, details the data structures and storage mechanics, specifies the new `builtin@goal` finalizer, and presents an intuitive, reliable, and beautiful TUI design.

---

## 2. Critique of the Proposed Concept

### 2.1 The Underlying Problem: Why Agent Completion Fails as an Attention Unit

In SASE's current architecture:
* An agent run represents a single execution turn (`single-turn-agents`).
* An epic or complex task consists of multiple sequential or parallel agents (e.g. `sase-1ab.1`, `sase-1ab.2`, `sase-1ab.3--plan`, `sase-1ab.4`).
* SASE currently emits notifications (`notify_workflow_complete`) and lights up unread dots (`_unread_completed_agent_ids`) whenever *any* agent process terminates.

In practice, 80–90% of completed agents are intermediate workers: an exploratory researcher, an epic phase coder whose output is gated by a subsequent phase, a replanner recovering from a test failure, or a gate shell. The user does not want to—and should not—verify every intermediate agent. Alerting on each one causes alert blindness.

A **Goal**, by contrast, represents an *intended operational outcome* (e.g., "Implement RFC-104 endpoint and add integration tests", "Diagnose and fix SQLite connection leak under load", or "Answer architecture query regarding memory webs"). An agent turn is merely a transient mechanism to advance or fulfill that goal.

### 2.2 Critique of Proposed Requirements & Invariant Alignment

| Proposed Idea | Analysis & Architectural Critique | Recommended Adjustment |
|---|---|---|
| **"All agents MUST have a goal defined"** | Strong and necessary. Prevents "headless" or orphan agents whose purpose cannot be reasoned about or verified by the system. | **Adopt.** Every agent run record in `agent_meta.json` and every launch environment must carry `SASE_GOAL_ID`. |
| **"Reuse plan `goal` field whenever a plan is associated"** | Excellent synergy. SASE plans (`sdd/plans/`) already enforce a strict required `goal` field in their frontmatter schema validated by `sase-core`. | **Adopt.** When launching an approved plan or epic phase (`sase bead work`), the host automatically extracts `plan.goal` and binds the agent to that Goal. |
| **"Agents check `$SASE_PLAN` at conversation start and invoke `/sase_new_goal`"** | **High Risk / Anti-pattern.** Requiring an LLM agent to evaluate its environment on turn 1, execute search queries across active goals, and conditionally call a creation skill wastes 1–2 LLM roundtrips, burns prompt tokens, risks hallucination, and breaks single-turn idempotency. | **Reject Agent-Side Init. Adopt Host-Owned Launch Resolution.** The host launcher (`sase run`, `sase bead work`, TUI prompt bar) already possesses the prompt, bead, and plan *before* the agent starts. The host resolves or creates the goal deterministically prior to spawn. |
| **"Planner agents don't need to do this"** | Inconsistent taxonomy. Planners *do* have a goal: "Formulate an approved implementation plan for <prompt/bead>". If planners are exempt, the goal tracking system has a blind spot during the most critical exploratory and design phase. | **Adjust.** Planners are assigned a Goal too (e.g. `goal:g-...` with objective "Deliver approved implementation plan for <X>"). When the plan is proposed and approved, that planning goal completes, and the *implementation* goal is born from `plan.goal`. |
| **"Explicit finalizer deciding whether to close goal or leave it open"** | Perfect alignment with SASE's `host-owned-completion` and finalizer manifest system (`builtin@commit`). | **Adopt.** Introduce `builtin@goal` finalizer. Every agent must declare `action: "keep"` or `action: "close"` in its final manifest. |
| **"Closing requires evidence linked to the goal"** | Essential to prevent agents from declaring premature "mission accomplished" without proof. | **Adopt.** Define the structured **Evidence Triad** (Witness, Artifacts, Rationale) validated by the host prior to closing. |
| **"O(n) access where n = active goals across all machines"** | Mandatory for performance. SASE beads currently suffer from historical log bloat where queries must scan thousands of closed issues. | **Adopt.** Use **State Directory Partitioning** (`active/` vs `archive/`) in a synchronized sidecar or git store. Scanning active goals is strictly bounded by active file count $n$. |

---

## 3. Core Architecture & Conceptual Model

### 3.1 Taxonomy: Goals vs. Beads vs. Artifacts vs. Agents

To keep SASE clean and maintainable, we must strictly delineate what a Goal is relative to existing entities:

```
┌────────────────────────────────────────────────────────────────────────┐
│                                 GOAL                                   │
│  "The Desired Outcome / Purpose" (e.g. goal:g-260926-001)             │
│  - Objective description (from prompt or plan frontmatter)            │
│  - Originating Prompt ID (cites prompt:ph_a1b2c3)                     │
│  - Lifecycle: ACTIVE ──[finalizer: close + evidence]──► VERIFYING ──► CLOSED│
└──────────────────┬─────────────────────────────────┬───────────────────┘
                   │ implements                      │ achieved by
                   ▼                                 ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│                BEAD                  │  │            AGENT             │
│  "The Work Tracking & Dependency"    │  │   "The Execution Turn"       │
│  - Issue / Task / Epic structure     │  │  - Single-turn ephemeral run │
│  - Schedulable work unit             │  │  - Commits diffs via final   │
│  - Status: open, ready, in_prog...   │  │  - Submits goal keep/close   │
└──────────────────┬───────────────────┘  └──────────────┬───────────────┘
                   │                                     │
                   │ generates / links                   │ generates
                   ▼                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                              ARTIFACTS                                 │
│  "Durable Deliverables & Evidence"                                     │
│  - Plan (plan:202609/...)                                              │
│  - Git Commit / Stitch (stitch:14)                                     │
│  - Snapshot Files (file:explicit:..., research:202609/...)             │
│  - Execution Logs / ToolRuns (toolrun:...)                             │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Prompt (`prompt:ph_...`):** The exact immutable text submitted by the human or automated scheduler.
2. **Goal (`goal:<id>`):** The durable operational intent and verification contract. Represents "What condition must be true for the human to be satisfied?"
3. **Bead (`bead:<id>`):** The tracking and scheduling artifact (task, phase, epic) managing dependencies, size estimation, and triage.
4. **Agent (`agent:<name>`):** The ephemeral compute worker executing a provider turn.
5. **Artifact (`<kind>:<argument>`):** The immutable evidence and deliverables produced.

### 3.2 Goal Lifecycle State Machine

```
              ┌───────────────┐
              │    ACTIVE     │◄───────────────────┐
              └───────┬───────┘                    │
                      │                            │
      Agent submits   │                            │ User rejects verification
      finalizer close │                            │ (Reopen with feedback)
      + Evidence      ▼                            │
              ┌───────────────┐                    │
              │   VERIFYING   │ (Awaiting User)    │
              └───────┬───────┴────────────────────┘
                      │
                      │ User clicks [Verify & Accept]
                      │ or automated test passes
                      ▼
              ┌───────────────┐
              │    CLOSED     │ (Moved to archive/)
              └───────────────┘
```

* **ACTIVE:** Work is in progress. Intermediate agents complete with `goal_action: "keep"`. No user verification notifications are dispatched.
* **VERIFYING:** An agent has completed work and submitted `goal_action: "close"` with valid evidence. The Goal is flagged **Awaiting Verification**. A high-priority notification is dispatched to the user.
* **CLOSED:** The user reviews the evidence and clicks "Accept" (or runs `sase goal accept <id>`), or an automated gate accepts it. The goal moves to durable archive storage.

---

## 4. Lightning-Fast $O(n)$ Storage Architecture

### 4.1 The Scalability Trap of Monolithic Logs
Existing tracking systems in developer tools (including early bead prototypes and traditional git issue trackers) frequently store records in a single append-only log (e.g. `issues.jsonl`) or a flat directory containing all historical files. 

When a project accumulates 50,000 completed tasks over time:
* Listing active tasks requires reading and parsing all 50,000 records to filter for `status != "closed"`.
* Disk I/O becomes $O(N)$ where $N$ is all historical events.
* Memory pressure and startup latency in TUIs and agent prompts increase steadily.

### 4.2 The Solution: Two-Bucket State Directory Partitioning

To satisfy the user requirement:
> *"This access needs to be lightning fast. More specifically, we should aim for $O(n)$ performance, where $n$ is the number of active goals (so done goals have no effect on performance)."*

We partition storage into two distinct directories within the project's durable store (or dedicated sidecar repository `sase/repos/goals/`):

```
sase/repos/goals/ (or ~/.sase/projects/<project>/goals/)
├── active/
│   ├── g-260926-a1b2.json
│   ├── g-260926-c3d4.json
│   └── g-260926-e5f6.json
└── archive/
    ├── 202607/
    │   └── ...
    ├── 202608/
    │   └── ...
    └── 202609/
        ├── g-260925-9876.json
        └── g-260926-0012.json
```

#### Operational Mechanics:
1. **Goal Creation:**
   * An atomic write creates `active/<goal_id>.json`.
   * Cost: $O(1)$.
2. **Listing Active Goals:**
   * Read the directory entries of `active/`.
   * Because closed goals are *never* in `active/`, `readdir("active")` returns exactly $n$ entries.
   * In typical workflows, $n \in [1, 20]$.
   * Reading 10 small JSON files from the filesystem takes less than **1 millisecond**.
   * Cost: Strict $O(n)$ where $n$ is active goals. Total historical goals $N$ have **zero impact**.
3. **Goal Completion & Archival:**
   * When a goal transitions to `CLOSED`, the host finalizer executes:
     `git mv active/<goal_id>.json archive/<YYYYMM>/<goal_id>.json`
   * Atomic within the filesystem and clean in Git history.
4. **Zero-Merge-Conflict Multi-Machine Concurrency:**
   * Each active goal is an isolated file (`<goal_id>.json`).
   * If Machine A creates `g-101.json` on branch/checkout A, and Machine B creates `g-102.json` on branch/checkout B, Git merges the `active/` directory with zero conflicts!
   * No shared central JSON file or shared counter is touched.

### 4.3 Goal Schema Specification

Each goal file (`<goal_id>.json`) adheres to the strict schema below:

```json
{
  "schema_version": 1,
  "id": "goal:g-260926-a1b2",
  "goal_id": "g-260926-a1b2",
  "project": "sase",
  "title": "Add Goals functionality to SASE",
  "objective": "Design, implement, and verify first-class Goal tracking with TUI integration and O(n) performance.",
  "status": "verifying",
  "created_at": "2026-09-26T12:00:00Z",
  "updated_at": "2026-09-26T12:45:00Z",
  "completed_at": "2026-09-26T12:45:00Z",
  
  "origin": {
    "prompt_id": "ph_7f8a9b1c2d3e",
    "prompt_text": "I want to add a new 'Goals' functionality to sase...",
    "launcher_agent": "user",
    "initial_workspace": 44
  },
  
  "associations": {
    "plan_ref": "plan:202609/sase_goals_architecture.md",
    "epic_bead_id": "sase-goals-e1",
    "phase_bead_id": "sase-goals-e1.3",
    "agent_clan": "sase-goals"
  },
  
  "participating_agents": [
    {
      "name": "sase-goals.1",
      "turn_type": "research",
      "completed_at": "2026-09-26T12:15:00Z",
      "action": "keep"
    },
    {
      "name": "sase-goals.2",
      "turn_type": "implementation",
      "completed_at": "2026-09-26T12:45:00Z",
      "action": "close"
    }
  ],
  
  "closure_evidence": {
    "closed_by_agent": "sase-goals.2",
    "closed_at": "2026-09-26T12:45:00Z",
    "proof_type": "verification_witness",
    "rationale": "All core goal data models, active/archive storage partitioning, and finalizer hooks implemented. Full test suite passes with 100% assertion coverage.",
    "witness_command": "just check",
    "witness_exit_code": 0,
    "evidence_refs": [
      "stitch:42",
      "file:explicit:9b2c3d4e5f6a7b8c",
      "research:202609/sase_goals_architecture_and_design__gem.md"
    ]
  }
}
```

---

## 5. Host-Owned Goal Resolution at Launch Time

### 5.1 Why the Host Must Own Goal Resolution
The user's initial idea was:
> *"require that every sase agent that is NOT tasked with creating a plan... check if the SASE_PLAN environment variable is set at the start of EVERY conversation. If not, it could invoke a new /sase_new_goal xprompt skill."*

Let us examine why making the agent responsible for this at conversational runtime is fragile:
1. **Wasted Turn & Token Overhead:** The agent would need to spend its initial prompt context and first tool call executing `/sase_new_goal`, querying active goals, and matching text.
2. **Non-Determinism:** If the model phrases the goal slightly differently from what the user intended, or fails to notice an existing matching goal, duplicated or malformed goals proliferate.
3. **Single-Turn Violation:** In SASE, agents run single-turn headless routines. Injecting an interactive goal negotiation sequence complicates the runner and breaks simple automation pipelines (`sase run "query"`).

### 5.2 The Deterministic Host Resolution Matrix
When any agent is launched—whether via CLI (`sase run`), plan approval (`sase plan approve`), epic work (`sase bead work`), or the TUI prompt bar—the **SASE Host Launcher** resolves the goal before spawning the agent process:

```
                              AGENT LAUNCH TRIGGERED
                                        │
                                        ▼
                       Is SASE_PLAN set or Plan attached?
                                   /        \
                             YES  /          \  NO
                                 /            \
        Extract `goal:` from frontmatter       Is SASE_BEAD_ID set?
        Find or create Goal for Plan               /        \
                                            YES  /          \  NO
                                                /            \
                       Extract Bead Title/Desc       Is %goal(...) directive
                       Bind to Bead's Goal           passed in prompt?
                                                         /        \
                                                   YES  /          \  NO
                                                       /            \
                                             Use explicit      Synthesize Goal from
                                             Goal ID/text      Prompt Text (first line)
                                        │
                                        ▼
                         Assign SASE_GOAL_ID=<id>
                         Write goal metadata to agent_meta.json
                         Export SASE_GOAL_ID to agent process
```

#### Launch Environment Contract:
The agent receives:
* `SASE_GOAL_ID="g-260926-a1b2"`
* `SASE_GOAL_TITLE="Add Goals functionality to SASE"`
* `SASE_GOAL_OBJECTIVE="Design, implement, and verify first-class Goal tracking..."`

The agent is immediately informed in its system instructions:
> *"You are working toward Goal `g-260926-a1b2`: 'Add Goals functionality to SASE'. When your turn concludes, you must declare via your final manifest whether your work completes this goal or leaves it open."*

Zero tokens wasted on discovery. Zero roundtrips. 100% deterministic traceability.

---

## 6. The Goal Finalizer & Evidence Framework

### 6.1 The New Finalizer: `builtin@goal`
SASE already has a clean host-owned finalizer mechanism (`sase final list`, `sase final context`, `sase final submit`). Currently, `builtin@commit` enforces that all dirty repository trees are committed.

We introduce `builtin@goal`:
* Registered as a default host finalizer alongside `commit`.
* When `SASE_GOAL_ID` is present in the turn context, `builtin@goal` becomes an **active obligation**.

### 6.2 Finalizer Context & Manifest Submission
When the agent runs `sase final context -f json`, the returned context includes:

```json
{
  "obligations": [
    {
      "instance": "commit",
      "kind": "repository",
      "repo_id": "sase"
    },
    {
      "instance": "goal",
      "kind": "goal",
      "goal_id": "g-260926-a1b2",
      "goal_title": "Add Goals functionality to SASE",
      "assigned_objective": "Design, implement, and verify first-class Goal tracking..."
    }
  ],
  "manifest_template": {
    "payloads": {
      "commit": { ... },
      "goal": {
        "goal_id": "g-260926-a1b2",
        "action": "<keep|close>",
        "evidence": {
          "proof_type": "<verification_witness|artifact_produced|inspection>",
          "rationale": "<concrete explanation of how the goal was satisfied>",
          "witness_command": "<command that was executed, e.g. just check>",
          "evidence_refs": ["<artifact-refs>"]
        }
      }
    }
  }
}
```

### 6.3 The Evidence Triad: What Evidence Must Be Required?
The user prompt specifically requests:
> *"An agent that chooses to close a goal must provide evidence to the finalizer (that will then be linked to the goal somehow before closing it). Think hard about what we should require this evidence to be."*

Requiring free-form prose alone is inadequate: LLMs frequently generate platitudes like *"All requirements have been met."* 
Conversely, requiring only git commit SHAs is insufficient, because code changes alone do not prove correctness.

We establish the **SASE Evidence Triad**:

```
                              THE EVIDENCE TRIAD
                                      ▲
                                     / \
                                    /   \
                                   /     \
             1. EXECUTION WITNESS /───────\ 2. ARTIFACT LOCATORS
                                 / \     / \
                                /   \   /   \
                               /     \ /     \
                              └───────▼───────┘
                           3. SATISFACTION RATIONALE
```

1. **Execution Witness (Automated Verification):**
   * The agent must report a successful command execution proving correctness (e.g. `just check`, `pytest tests/test_goal.py`, or a custom reproduction script).
   * The host verifies against the agent's tool-call log (`tool_calls.jsonl` or `ToolRun`) that this command was actually run during this turn and exited with code `0`.
2. **Artifact Locators (Concrete Deliverables):**
   * At least one durable artifact reference produced or modified during the work (e.g., `stitch:<N>`, `file:explicit:<hash>`, `plan:202609/...`, or `research:202609/...`).
   * The host verifies that each referenced artifact actually exists in storage.
3. **Satisfaction Rationale (Human Verification Context):**
   * 1 to 3 sentences explaining specifically *what* was verified and *why* the user can trust that the objective is achieved.
   * Placeholders (e.g. "done", "fixed", "completed") are rejected by strict regex/length validation in `sase-core`.

#### Automated Artifact Linking Upon Submission:
When `sase final submit` succeeds with `goal_action: "close"`:
1. The host updates the goal record in `active/<goal_id>.json` to status `verifying` (or `closed`).
2. The host automatically calls the SASE artifact link store:
   ```bash
   sase artifact link add <evidence_ref> verifies goal:<goal_id> "<rationale>"
   ```
3. The evidence becomes permanently cross-linked in the project's knowledge graph and visible in the TUI Artifacts tab and Goal detail views.

---

## 7. Attention Architecture: Solving Notification Fatigue

### 7.1 The Two Notification Channels
SASE currently notifies the user on agent completion. We restructure notification routing based on the Goal abstraction:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AGENT FINISHES TURN                             │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                     Did agent submit `action: "close"`
                             on its Goal?
                                 /   \
                           NO   /     \   YES
                               /       \
                              ▼         ▼
     ┌────────────────────────────┐ ┌────────────────────────────────────┐
     │     INTERNAL LOGGING       │ │     HIGH-PRIORITY NOTIFICATION     │
     │ - Agent status -> COMPLETED│ │ - Goal status -> VERIFYING         │
     │ - Update Agent List in TUI │ │ - Emit Notification (sender: goal) │
     │ - NO audio chime           │ │ - Top bar indicator -> 🎯 1 Verify │
     │ - NO push notification     │ │ - Desktop / Telegram alert         │
     └────────────────────────────┘ └────────────────────────────────────┘
```

### 7.2 The Goal Verification Notification Payload
When a goal is closed by an agent, the host sends:
```json
{
  "sender": "goal",
  "action": "JumpToGoal",
  "notes": [
    "Goal 'Add Goals functionality to SASE' completed by agent sase-goals.2. Ready for verification."
  ],
  "action_data": {
    "goal_id": "g-260926-a1b2",
    "goal_title": "Add Goals functionality to SASE",
    "closed_by_agent": "sase-goals.2",
    "witness_command": "just check",
    "evidence_ref": "stitch:42"
  },
  "tags": ["goal", "verification-needed"]
}
```

### 7.3 TUI Unread Indicator Transformation
On the Agents tab and Top Bar:
* Instead of showing `● 14 unread` representing 14 intermediate agent turns that completed while the user was away, the Top Bar displays:
  `🎯 2 active · 1 to verify`
* Clicking the indicator immediately opens the Goal Verification view for the completed goal, showing the prompt, the diff, the test witness, and the agent's explanation.

---

## 8. User Experience & TUI Design: Intuitive, Reliable, Beautiful

The user requests:
> *"The TUI should have a new "Goals" panel somewhere that users can use to see all active goals for a project. We should use artifact links to make it very easy for users to jump from this panel to any artifact and/or sase agent on the "Agents" tab linked to that goal. Make sure you design this feature so it is intuitive, reliable, and (last but not least) beautiful!"*

### 8.1 TUI Placement: Dual Surface Architecture

To provide maximum ergonomics without cluttering the top bar, we implement Goals across two coordinated surfaces:

1. **The Primary Goals Surface: A Dedicated `Goals` Pane on the Artifacts Tab (`#artifacts-goals-pane`):**
   * Accessible via the top tab bar: `Artifacts` -> subtab `Goals` (shortcut `g` or digit shortcut `6`).
   * Color accent: Vibrant Emerald (`#00D787`) to signify purpose, clarity, and completion.
   * Icon: `🎯` (Target).
2. **The Operational Context Surface on the Agents Tab:**
   * In the **Agent Info Row** at the top of the Agents tab: A dynamic **Goal Chip** (`🎯 Add Goals functionality...`) displaying the active goal of the currently selected agent.
   * In the **Agent Detail Deck (Main Deck)**: A new **Goal Card** positioned directly alongside the Context and Reply cards, displaying the goal's objective, origin prompt, and remaining phase milestones.

### 8.2 Visual Layout of the Goals Pane (`Artifacts -> Goals`)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ AGENTS │ ARTIFACTS [Stitches | Patches | Beads | Plans | Research | > GOALS < | Files] │ SERVICES      │
├────────────────────────────────┬───────────────────────────────────────────────────────────────────────┤
│ ACTIVE GOALS (3 active)        │ GOAL DETAIL: g-260926-a1b2                                            │
├────────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
│ [A] 🎯 g-260926-a1b2           │ 🎯 Add Goals functionality to SASE                                    │
│     Add Goals functionality    │ Status: [VERIFYING - AWAITING OPERATOR]       Elapsed: 45m             │
│     Clan: sase-goals           │ Origin: prompt:ph_7f8a9b1c2d3e (Launch Workspace #44)                 │
│     ● VERIFYING (by agent .2)  ├───────────────────────────────────────────────────────────────────────┤
│                                │ OBJECTIVE:                                                            │
│ [B] 🎯 g-260926-c3d4           │ Design, implement, and verify first-class Goal tracking with TUI      │
│     Repair apollo mesh drops   │ integration and O(n) active performance.                              │
│     Clan: apollo-fix           ├───────────────────────────────────────────────────────────────────────┤
│     ○ ACTIVE (agent running)   │ ORIGINAL PROMPT (ph_7f8a9b1c2d3e):                                    │
│                                │ "I want to add a new 'Goals' functionality to sase. Goals should be   │
│ [C] 🎯 g-260925-e5f6           │  associated with original prompts... [click or Enter to view full]"   │
│     Refactor TUI node spine    ├───────────────────────────────────────────────────────────────────────┤
│     Clan: spine-refactor       │ ASSOCIATIONS & LINKS:                                                 │
│     ○ ACTIVE (waiting test)    │ Plan:    [P] plan:202609/sase_goals_architecture.md                    │
│                                │ Bead:    [B] bead:sase-goals-e1 (Epic: Goals Architecture)            │
│                                │ Clan:    [C] @sase-goals (Agents: sase-goals.1, sase-goals.2)         │
│                                ├───────────────────────────────────────────────────────────────────────┤
│                                │ COMPLETION EVIDENCE (Submitted by sase-goals.2):                      │
│                                │ • Rationale: Full test suite passes; active/archive partitioning      │
│                                │              benchmarked at <1ms.                                     │
│                                │ • Witness:   `just check` (Exit Code 0 ✓)                             │
│                                │ • Artifacts: [S] stitch:42 · [R] research:202609/sase_goals...__gem.md │
│                                ├───────────────────────────────────────────────────────────────────────┤
│                                │ ACTIONS:                                                              │
│                                │ [V] Accept & Close Goal   [R] Reject & Reopen   [J] Jump to Agent .2  │
└────────────────────────────────┴───────────────────────────────────────────────────────────────────────┘
```

### 8.3 Seamless Keyboard & Jump Hint Navigation
SASE users rely on rapid keyboard navigation (`_node_jump.py` / `jump_hints.py`). The Goals panel deeply integrates with this system:

* **Instant Jump to Agents:** Pressing `J` (or hint `[C]`) jumps directly to the agent in the **Agents tab** currently working on or responsible for closing that goal, automatically selecting its node in the Agent List.
* **Instant Jump to Artifacts:**
  * Pressing `P` opens the linked Plan in the SASE pager.
  * Pressing `B` jumps to the matching Bead on the Beads pane.
  * Pressing `S` jumps to the Stitch commit diff in the Stitches pane.
* **Verification Actions:**
  * Pressing `V` ("Verify & Accept") marks the goal `CLOSED`, moves the file to `archive/<YYYYMM>/`, and clears the notification.
  * Pressing `R` ("Reject / Request Follow-up") prompts the user for feedback and automatically launches a follow-up agent in that goal's clan with the feedback prompt.

---

## 9. Rust Core Backend Boundary

Per SASE Rule 1.3 (`rust_core_backend_boundary`) and Decision 18 (`rust-core-required`):
> *"Shared backend and domain behavior belongs in the `sase_core` crate of the linked `sase-core` repo... If a web app, CLI, editor integration, or another frontend would need the behavior to match the TUI, treat it as core backend logic."*

### 9.1 Boundary Division

| Layer / Repo | Responsibilities & Modules |
|---|---|
| **`sase-core` (Rust)** | • Core structs: `GoalRecord`, `GoalOrigin`, `ClosureEvidence`, `GoalStatus`.<br>• Store engine: `GoalStore` with atomic file persistence, `active/` and `archive/` partitioning, and strict $O(n)$ active goal directory streaming.<br>• Validation: Schema verification, evidence validation (witness check, non-empty rationale).<br>• Query API: `list_active_goals()`, `load_goal(id)`, `close_goal(id, evidence)`. |
| **`sase_core_py` (PyO3)** | • Python bindings exporting `GoalStore`, `GoalRecord`, and `GoalValidationResult`. |
| **`sase` (Python CLI & Workflow)** | • Host Launch Hooks: `launch_single_agent()`, `bead_work()`, and `plan_accept()` resolving and attaching `SASE_GOAL_ID`.<br>• Finalizer integration: `builtin@goal` finalizer validating declarations against `sase-core`.<br>• Notifications: `notify_workflow_complete` routing and attention suppression. |
| **`sase` (Textual TUI)** | • `ArtifactsGoalsPane` widget.<br>• TopBar Goal Indicator (`GoalIndicator`).<br>• Goal Card in Agent Detail Deck.<br>• Jump-hint keyboard bindings. |

### 9.2 Rust Core Implementation Sketch (`sase_core::goal`)

```rust
// crates/sase_core/src/goal/mod.rs

use std::fs;
use std::path::{Path, PathBuf};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum GoalStatus {
    Active,
    Verifying,
    Closed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClosureEvidence {
    pub closed_by_agent: String,
    pub closed_at: String,
    pub proof_type: String,
    pub rationale: String,
    pub witness_command: Option<String>,
    pub witness_exit_code: Option<i32>,
    pub evidence_refs: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GoalRecord {
    pub schema_version: u32,
    pub id: String,
    pub title: String,
    pub objective: String,
    pub status: GoalStatus,
    pub created_at: String,
    pub updated_at: String,
    pub completed_at: Option<String>,
    pub prompt_id: String,
    pub prompt_text: String,
    pub plan_ref: Option<String>,
    pub bead_id: Option<String>,
    pub closure_evidence: Option<ClosureEvidence>,
}

pub struct GoalStore {
    base_dir: PathBuf,
}

impl GoalStore {
    pub fn new(base_dir: impl Into<PathBuf>) -> Self {
        Self { base_dir: base_dir.into() }
    }

    pub fn active_dir(&self) -> PathBuf {
        self.base_dir.join("active")
    }

    pub fn archive_dir(&self, yyyymm: &str) -> PathBuf {
        self.base_dir.join("archive").join(yyyymm)
    }

    /// Strict O(n) scan across active goals only.
    pub fn list_active_goals(&self) -> Result<Vec<GoalRecord>, std::io::Error> {
        let active_path = self.active_dir();
        if !active_path.exists() {
            return Ok(Vec::new());
        }

        let mut goals = Vec::new();
        for entry in fs::read_dir(active_path)? {
            let entry = entry?;
            let path = entry.path();
            if path.extension().and_then(|s| s.to_str()) == Some("json") {
                let content = fs::read_to_string(&path)?;
                if let Ok(record) = serde_json::from_str::<GoalRecord>(&content) {
                    goals.push(record);
                }
            }
        }
        // Deterministic sort by created_at descending
        goals.sort_by(|a, b| b.created_at.cmp(&a.created_at));
        Ok(goals)
    }

    /// Atomically close a goal: validates evidence, updates status,
    /// and moves file from active/ to archive/YYYYMM/.
    pub fn close_goal(
        &self,
        goal_id: &str,
        evidence: ClosureEvidence,
        yyyymm: &str,
    ) -> Result<GoalRecord, String> {
        if evidence.rationale.trim().len() < 10 {
            return Err("Closure rationale must be at least 10 characters of concrete explanation".into());
        }

        let filename = format!("{}.json", goal_id);
        let src = self.active_dir().join(&filename);
        if !src.exists() {
            return Err(format!("Active goal {} not found", goal_id));
        }

        let content = fs::read_to_string(&src).map_err(|e| e.to_string())?;
        let mut record: GoalRecord = serde_json::from_str(&content).map_err(|e| e.to_string())?;

        record.status = GoalStatus::Closed;
        record.completed_at = Some(evidence.closed_at.clone());
        record.closure_evidence = Some(evidence);

        let dest_dir = self.archive_dir(yyyymm);
        fs::create_dir_all(&dest_dir).map_err(|e| e.to_string())?;
        let dest = dest_dir.join(&filename);

        let serialized = serde_json::to_string_pretty(&record).map_err(|e| e.to_string())?;
        fs::write(&dest, serialized).map_err(|e| e.to_string())?;
        fs::remove_file(&src).map_err(|e| e.to_string())?;

        Ok(record)
    }
}
```

---

## 10. Implementation Roadmap

### Phase 1: Core Domain & Storage Engine (`sase-core`)
1. Implement `crates/sase_core/src/goal/` with `GoalRecord`, `GoalStore`, and `ClosureEvidence`.
2. Implement two-bucket partitioning (`active/` vs `archive/`) with atomic file move operations.
3. Add comprehensive Rust unit tests validating $O(n)$ scanning and zero-conflict multi-machine semantics.
4. Expose PyO3 bindings in `crates/sase_core_py/`.

### Phase 2: Host Launch Integration & Environment Wiring (`sase`)
1. Update `launch_single_agent()` and `launch_planned_bead_work_agents()` to automatically resolve or instantiate a Goal record.
2. Bind plan frontmatter `goal` to `SASE_GOAL_ID`.
3. Export `SASE_GOAL_ID`, `SASE_GOAL_TITLE`, and `SASE_GOAL_OBJECTIVE` to agent environments and record in `agent_meta.json`.

### Phase 3: The `builtin@goal` Finalizer
1. Create `src/sase/finalizers/goal.py` implementing the `builtin@goal` finalizer provider.
2. Update `sase final context` to include Goal obligations when `SASE_GOAL_ID` is set.
3. Validate evidence in `sase final submit`: check witness commands in `tool_calls.jsonl`, verify artifact locators, and reject empty rationales.
4. Automatically stage typed artifact links (`verifies`) on goal closure.

### Phase 4: Notification Routing & Attention Overhaul
1. Modify `notify_workflow_complete`: suppress user-facing alerts/chimes for intermediate agents submitting `goal_action: "keep"`.
2. Emit `sender: "goal"` high-priority notifications when an agent submits `goal_action: "close"`.
3. Update top-bar unread counters from agent completion counts to pending Goal Verification counts.

### Phase 5: TUI Surface (`Artifacts -> Goals` & Agent Detail Integration)
1. Add `ArtifactsGoalsPane` to `src/sase/ace/tui/widgets/artifacts/`.
2. Implement split-pane navigation: active goals list with status badges on the left, rich markdown detail surface with prompt and evidence drawer on the right.
3. Wire keyboard jump hints (`J` to jump to Agent, `P` to jump to Plan, `S` to jump to Stitch).
4. Add Goal Context card to Agent Detail Main Deck.

---

## 11. Conclusion & Key Recommendations

1. **Adopt Goals as a First-Class Entity:** The feature provides immense value by bridging the gap between raw user prompts and low-level agent turns, eliminating notification fatigue.
2. **Reject Agent-Side Initialization:** Do not require agents to inspect `$SASE_PLAN` or run `/sase_new_goal` at conversation start. The host has all necessary context and must own goal initialization deterministically at launch time.
3. **Enforce Two-Bucket Storage Partitioning:** Partitioning active and archived goals into separate directories guarantees $O(n)$ active performance regardless of total project age and eliminates git merge conflicts across distributed machines.
4. **Mandate the Evidence Triad:** Enforce execution witness, artifact locators, and concrete satisfaction rationales via the new `builtin@goal` finalizer before permitting goal closure.
5. **Implement Beautiful Dual TUI Surfaces:** Provide an operational Goal Context card on the Agents tab and a dedicated, jump-navigable Goals management pane on the Artifacts tab.
