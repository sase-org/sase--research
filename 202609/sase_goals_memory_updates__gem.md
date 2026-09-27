# SASE Goals Post-Completion Memory Strategy: Analysis and Recommendations

_Researcher: `gem` · 2026-09-27 · swarm: 5-researcher independent investigation_  
_Target Program: SASE Goals (Epics G1–G6) · Context: `sase_goals_epic_roadmap.md`, `sase_goals_design.md`_

---

## Executive Summary

When all six SASE Goal epics (G1 through G6) complete, SASE will have transitioned from an agent execution model centered on noisy, turn-by-turn completion pings into a structured, intent-driven architecture governed by the foundational invariant: **"The host binds, agents claim, users settle."** 

This transition fundamentally touches agent lifecycle contracts, prompt directives, finalizer obligations, artifact models and relation graphs, human review gates, and TUI interaction models. Leaving memory unchanged after G6 would create severe context drift: agents would continue operating under obsolete assumptions (e.g., unaware of their finalizer claim obligations, unaware of draft naming/adoption rules, unaware of the `%goal` directive, or attempting to invoke human-only status verbs). Conversely, dumping every implementation detail into always-loaded core memory would bloat context windows and impose a permanent token tax on every agent turn.

This report provides a comprehensive, structured recommendation for the exact set of memory file additions, updates, and exclusions that should be in place once all SASE Goal epics have landed.

### Bottom-Line Recommendations

| Memory Tier / Target | Action | Key Updates / Purpose |
| :--- | :--- | :--- |
| **New Reference Note**<br>`sase/memory/sase_goals.md` | **Create** | The canonical reference guide for Goals: lifecycle (`draft` → `active` → `review` → `done`), host binding rules, agent draft naming/adoption via `/sase_goal`, finalizer obligations (`builtin@goal`), evidence requirements, and human-only status verb boundaries. |
| **Core Memory**<br>`sase/memory/sase.md` (§1.1.4) | **Update (Minimal)** | Add a single compact sentence to the `/sase_final` terminal action declaration indicating that the final declaration records the turn's goal action (`keep_open` or `claim`). Keep addition under 30 tokens. |
| **Reference Note**<br>`sase/memory/sase_artifacts.md` | **Update** | Register `goal:` as a first-class artifact kind (`goal:<id>`). Add the four new projection-sourced typed relations to the closed registry: `pursues`, `defines`, `evidences`, and `follows`. |
| **Reference Note**<br>`sase/memory/xprompts.md` | **Update** | Document `%goal:<id>` and `%goal:new` launch directives and generalized inheritance. Document `builtin@goal` as a required finalizer ordered after `commit`, and detail the final manifest goal payload. |
| **Reference Note**<br>`sase/memory/sase_beads.md` | **Update** | Formalize the separation of concerns: Beads track work units (plans, phases, tasks); Goals track intent and verification. Clarify phase worker `keep_open` vs land agent `claim`. Note that status verbs on both beads and goals are refused inside agent runs. |
| **Reference Note**<br>`sase/memory/generated_skills.md` | **Update** | Document the `/sase_goal` skill (`list`, `show`, `name`, `adopt`). Explicitly document that there is **no** `/sase_new_goal` skill. Note the `/sase_final` manifest expansion. |
| **Reference Note**<br>`sase/memory/cli_rules.md` | **Update** | Codify the system-wide safety invariant: commands with human-only status mutation verbs (`verify`, `reject`, `drop`, `merge`, `reopen`) must refuse execution when run inside agent environments. |
| **Reference Note**<br>`sase/memory/tui.md` & `tui_perf.md` | **Update** | Document the top-level `Goals` tab in `TAB_ORDER`, its keybindings (`v`, `r`, `x`, `l`, `e`, `m`, etc.), and strict performance budgets (projection refresh < 2 ms at $n=100$, highlight → paint $\le 16\text{ ms}$). |
| **Decision Web (`decisions`)** | **Add 3 Strands** | 1. `goals-host-binds-agents-claim-users-settle`<br>2. `goal-ledger-cohosted-in-beads`<br>3. `attention-cutover-claim-based-notifications` |
| **Glossary Web (`glossary`)** | **Add 8 Strands** | Add `goal`, `goal-claim`, `goal-draft`, `goal-verify-gate`, `goal-adoption`, `goal-ledger`, `answer-acknowledgement`, `idle-goal`. Update `artifact`, `gate-turn`, and `agent-turn`. |
| **Files Unchanged** | **No Change** | `sase_flags.md` (all beta scaffolding flags are removed by G6), `rust_core_backend_boundary.md` (architecture preserved), `task_types.md` (goals are not task beads), `lint_and_test.md`, `gotchas.md`. |

---

## 1. Context: What the Six SASE Goal Epics Deliver

As established in `sase_goals_epic_roadmap.md` and `sase_goals_design.md`, SASE Goals is partitioned into six verifiable sibling epics:

1. **G1 (Goal Ledger, CLI, `goal:` Artifact)**:
   - Immutable, conflict-free event ledger and `live/` marker hierarchy co-hosted in the beads sidecar repository (`goals` role), written via the hidden clone.
   - Machine-local `goals-hot.json` projection delivering sub-50ms reads across 100k+ settled goals.
   - Manual `sase goal` CLI commands (`new`, `list`, `show`, `edit`, `drop`, `reopen`, `merge`, `doctor`).
   - First-class `goal:` artifact catalog registration; `@goal:<id>` prompt citation syntax.

2. **G2 (Deterministic Binding)**:
   - Host resolves and binds an agent to a goal *before* provider spawn via `build_agent_meta`.
   - Generalizes `%tab` inheritance into shared directive inheritance across sessions, plans, clanned swarms, retries, dispatches, and monitors.
   - Introduction of `%goal:<id>` and `%goal:new` launch directives.
   - `sase plan propose` stamps `goal_id` and derives goal definitions from epic plans.
   - Bound prompt line: `SASE GOAL ⌖id — <title>`.
   - Artifact relations: `pursues` (agent → goal) and `defines` (plan → goal).

3. **G3 (Claims and Verification)**:
   - Required `builtin@goal` finalizer, ordered `after: [commit]`.
   - Every normal turn on a bound goal must submit a goal decision: `keep_open` (with a progress note) or `claim` (with evidence refs, 1–3 check-it steps, and known gaps).
   - Strict role derivation: epic phase agents cannot claim; only land agents or single-worker turns can claim.
   - A claim moves the goal to `review` and opens exactly one `GoalVerify` gate.
   - Refusal or failure falls open to `keep_open` plus diagnostic; a goal error never fails an agent turn.
   - Status verbs (`verify`, `reject`, `drop`, `reopen`, `merge`) are human-only and refused inside agent runs.
   - Artifact relation: `evidences` (artifact/commit/receipt → goal).

4. **G4 (Drafts, Naming, Adoption, Answer Acknowledgement)**:
   - Universal coverage: uncoordinated turns receive a machine-local draft goal.
   - Intake block: the agent's first act is to `name` its draft or `adopt` an active goal via the generated `/sase_goal` skill.
   - Swarms share one draft and produce one goal.
   - Naming publishes the creator's prompt.
   - Answer acknowledgement: opening an answer card settles the goal as `done · acknowledged`.
   - Artifact relation: `follows` (goal → goal for successor work).

5. **G5 (Goals Tab and Agents Integration)**:
   - Top-level `Goals` tab added to `TAB_ORDER` (Review, Running, Idle lanes, contributor pips, sync watermark).
   - Dedicated keybindings (`v`, `r`, `x`, `l`, `e`, `m`, `a`, `p`, `n`, `/`, `P`, `h`).
   - Agents tab integration: goal identity chip, FINAL-deck Goal card/enricher, *by goal* grouping in `o`/`O` ladder.
   - Jumps: `JumpToGoal` opens the Goals tab; goal card agent numbers jump directly to live agent rows (revealing collapsed rows).

6. **G6 (Attention Cutover)**:
   - Silences successful agent runs (`JumpToAgent(done)` goes quiet). Turn completion chimes are retired.
   - Chimes and push notifications are reserved for goal claims (`GoalVerify`), human decisions (gates), and unrecoverable errors.
   - Retires the ✅ success unread projection in the inbox.
   - Introduces quiet Idle goal hygiene notices.
   - Removes all temporary beta scaffolding flags.

---

## 2. Memory System Evaluation Framework

SASE memory is strictly divided into three tiers:
1. **Core Memory (`type: core`)**: Inlined directly into `AGENTS.md` and all 9 provider instruction shims (`CLAUDE.md`, `GEMINI.md`, etc.). It is paid for on *every single turn* by *every agent*.
2. **Reference Memory (`type: reference`)**: Listed as a one-line description in `AGENTS.md`. The body is read on-demand via audited `sase memory read` calls.
3. **Memory Webs (`web: true`)**: Keyed collections (`decisions`, `glossary`, `task_types`) whose descriptors are inlined into `AGENTS.md`, while individual strands are read on-demand via `sase memory read <web>:<keyword>`.

### Design Principles for Goal Memory Updates

To avoid degrading agent performance or inflating token expenditure, memory updates must adhere to four strict principles:

1. **Context Window Parsimony (The Token Budget Rule)**:  
   Do not bloat Core Memory. An agent writing a quick bash script does not need to know the internal data structures of the goal ledger or the keybindings of the Goals tab. Core memory must contain only the absolute minimum terminal contract needed by every agent turn.
2. **Audited On-Demand Recall**:  
   Domain-specific workflows (e.g., how an agent names a draft, how it structures claim evidence, or why it cannot call `sase goal verify`) belong in Reference Memory and Memory Webs, retrieved only when an agent is operating in those domains.
3. **Strict Symmetry with Existing Subsystems**:  
   Goals should follow the exact conventions already established by Beads (`sase_beads.md`) and Artifacts (`sase_artifacts.md`).
4. **Post-Landing Flag Cleanliness**:  
   Per `sase_flags.md`, feature flags are temporary scaffolding removed before or at landing. Once G6 lands, no goal flags remain. Memory files must document the permanent, unconditional reality, not temporary migration flags.

---

## 3. Recommended New Memory Files

### 3.1 New Reference Note: `sase/memory/sase_goals.md`

A new top-level reference memory note is required. Just as `sase_beads.md` governs work tracking and `sase_artifacts.md` governs artifact storage, `sase_goals.md` will govern intent, binding, draft management, claim obligations, and verification.

#### Frontmatter
```yaml
---
type: reference
parent: AGENTS.md
description: Read before creating, binding, claiming, adopting, or verifying SASE goals — goal lifecycle, draft naming and adoption rules, finalizer claim obligations, and human-only status verbs.
---
```

#### Proposed Structure and Key Content
- **1. The Core Model & Invariant**:
  - The invariant: *"The host binds, agents claim, users settle."*
  - Distinction from beads: Beads track tasks, bugs, and plans; Goals track user intent, execution grouping, and verified outcome delivery.
  - Canonical identifier: `goal:<id>`, referenced in prompts as `@goal:<id>`.
  - Lifecycle: `draft` → `active (running | idle)` → `review` → `done · acknowledged` | `done · verified` | `dropped`.
- **2. Binding & Inheritance**:
  - Pre-execution binding by the host: explicit `%goal:<id>`, session successors, plan `goal_id`, clan, parent, or bead.
  - Refusal to bind settled goals (`done` or `dropped`).
  - Generalized inheritance: child agents, retries, monitors, and dispatch inherit the parent's goal binding.
- **3. Drafts, Naming, and Adoption**:
  - Unbound runs receive a local draft.
  - Agent intake obligation: on its first turn, an agent on a draft must either `name` its draft or `adopt` an active goal using the `/sase_goal` skill.
  - Drafts are never published to the shared ledger until named.
  - Swarm single-goal invariant: swarms share a single root draft; individual members do not create separate goals.
- **4. Finalizer Obligations (`builtin@goal`)**:
  - Ordered strictly `after: [commit]` in the host completion chain.
  - On every bound turn, the agent must declare either `keep_open` (with a concise progress note) or `claim`.
  - Phase vs. land role restriction: epic phase agents can **never** claim; only land agents or single-worker turns can claim.
  - Claim payload requirements:
    1. 1–3 concrete check-it steps for human verification.
    2. Resolvable, provenance-checked evidence refs (symbolic `@commit`, created artifacts, plan ref, receipt snapshots, `@reply`).
    3. Known residual gaps or limitations.
  - Fail-open safety: a `builtin@goal` refusal or error falls open to `keep_open` with a diagnostic; it never fails the turn.
- **5. Verification, Settling, and Human-Only Verbs**:
  - A claim moves the goal to `review` and raises a `GoalVerify` gate (verify, reject with relaunch, drop).
  - **Human-only status verbs**: `verify`, `reject`, `drop`, `reopen`, and `merge` are strictly refused inside agent runs. Agents never settle goals directly.
  - Automatic answer acknowledgement: opening an answer card automatically settles answer-only goals (`done · acknowledged`).
- **6. CLI & Skill Interface**:
  - `sase goal` CLI overview. Bare `sase goal` defaults to `list`.
  - Agent-allowed CLI actions: `list`, `show`, `name`, `adopt`.
  - The `/sase_goal` skill.

---

### 3.2 New Decision Web Strands (`decisions/`)

Three new architectural decision records should be added to `sase/memory/decisions/`. In fact, as noted in `sase_goals_epic_roadmap.md` §9, the first record is a prerequisite move before G1 planning:

#### 1. `goals-host-binds-agents-claim-users-settle.md`
- **Slug**: `goals-host-binds-agents-claim-users-settle`
- **Aliases**: `host binds agents claim`, `goals core invariant`
- **Claim**: Every agent turn is bound by the host to exactly one goal before provider spawn; agents never create arbitrary goals from scratch but may name or adopt drafts; every turn terminates with an obligatory finalizer (`builtin@goal`) choosing between `keep_open` and `claim`; claims are settled exclusively by human decision (`GoalVerify` gate) or explicit acknowledgement, never by agent self-settlement or dismissing notification rows.
- **Why**: Eliminates "intake tax" where models burn reasoning budget deciding whether to create goals; avoids hallucinated or duplicate goal entities; prevents agents from self-approving their own work; guarantees that human review is focused on verified outcomes rather than monitoring endless turn completion pings.
- **Cost**: Protocol complexity in the runner and finalizer; requires evidence validation and provenance checks; requires gate handling infrastructure.
- **Reopens when**: Autonomous self-verification models prove reliable enough to completely replace human verification gates.

#### 2. `goal-ledger-cohosted-in-beads.md`
- **Slug**: `goal-ledger-cohosted-in-beads`
- **Aliases**: `goal ledger co-hosting`, `goals role in beads`
- **Claim**: The goal ledger is stored as an immutable, conflict-free event log with `live/` markers co-hosted in the beads sidecar repository under a dedicated `goals` role, written via the host-owned hidden clone, and projected into a machine-local fast cache (`goals-hot.json`).
- **Why**: Reuses existing multi-clone synchronization and hidden-clone write infrastructure without creating an additional sidecar repository; avoids git merge conflicts across multi-machine setups; keeps list latency under 50 ms even with 100k settled goals.
- **Cost**: Contention risk on the beads repository if push volume spikes (mitigated by a push-retry counter; triggers a dedicated repo split if contention is measured).
- **Reopens when**: Push contention or ledger size demonstrably degrades beads sidecar synchronization performance.

#### 3. `attention-cutover-claim-based-notifications.md`
- **Slug**: `attention-cutover-claim-based-notifications`
- **Aliases**: `silence success pings`, `claim-based attention`
- **Claim**: Completion notifications for successful agent runs (`JumpToAgent(done)`) are silenced; notification chimes and push alerts are reserved exclusively for goal claims (`GoalVerify`), human decisions (gates), and unrecoverable errors.
- **Why**: At scale (thousands of agent turns per week), raw completion pings create severe notification fatigue, causing users to miss critical failures. Goals aggregate multiple turns into cohesive outcomes, turning individual run completions into noise and goal claims into signal.
- **Cost**: Requires high claim precision (≥80%) and shadow coverage (≥90%) prior to cutover; users must adjust to reviewing goals rather than watching individual agent turn completions.
- **Reopens when**: Workflows emerge that require turn-level pulse monitoring that cannot be modeled through goal progress notes or dashboard views.

---

### 3.3 New Glossary Web Strands (`glossary/`)

Eight new glossary strands should be added to `sase/memory/glossary/` to define the new vocabulary:

1. **`goal.md`** (`Goal`, alias: `Sase Goal`): A durable unit of user-facing intent, execution grouping, and verified outcome across one or more agent turns, represented by a `goal:<id>` artifact.
2. **`goal-claim.md`** (`Goal Claim`, alias: `Claim`): A formal assertion submitted by an agent via the `builtin@goal` finalizer declaring that a goal's intended outcome is complete, accompanied by verifiable evidence refs, check-it steps, and known gaps.
3. **`goal-draft.md`** (`Goal Draft`, alias: `Draft Goal`): A machine-local, unbound goal placeholder assigned to an uncoordinated agent turn that the agent must either name or adopt into an active goal upon intake.
4. **`goal-verify-gate.md`** (`Goal Verify Gate`, alias: `GoalVerify`): A generic-form SASE gate opened upon a goal claim, allowing the user to verify the outcome, reject it with feedback and optional relaunch, or drop the goal.
5. **`goal-adoption.md`** (`Goal Adoption`, alias: `Adopt Goal`): The action of an agent merging its local draft into an existing active goal that shares the same intent, retracting any in-flight review claims on that goal.
6. **`goal-ledger.md`** (`Goal Ledger`, alias: `Goal Event Store`): The append-only, conflict-free event store and `live/` marker hierarchy co-hosted in the beads repository that records the immutable history of all goals.
7. **`answer-acknowledgement.md`** (`Answer Acknowledgement`, alias: `Answer Ack`): The automatic settlement of an answer-only goal (`done · acknowledged`) triggered when the user opens or views the answer card, bypassing manual verification.
8. **`idle-goal.md`** (`Idle Goal`, alias: `Stale Goal`): An active goal that has had no live agent contributors or progress notes for an extended duration, subject to aging and quiet nudge notices.

---

## 4. Recommended Updates to Existing Memory Files

### 4.1 Core Memory: `sase/memory/sase.md`

`sase.md` is inlined into every provider instruction shim on every turn. Its token footprint must remain strictly controlled.

- **Current Text (§1.1.4 SASE Final Declaration)**:
  > "Before any normal response that ends this SASE provider turn, use your `/sase_final` skill as the last action. This includes a final answer and an incomplete-status response; an unfinished turn still declares so its work is committed. Never end a turn to wait for a command or to resume later: nothing can wake you, so hand long commands to `/sase_monitor` before starting them. Only a successfully executed plan, monitor, pipe, or questions handoff is exempt, because those commands terminate the runner mechanically."

- **Recommended Update**:  
  Append one precise, compact sentence clarifying the finalizer goal action:
  > "That declaration commits your modified repositories and records your goal action (`keep_open` with progress note, or `claim` with verification evidence)."
- **Token Impact**: Adds ~20 tokens to core memory. High value for minimal cost.

---

### 4.2 Reference Memory: `sase/memory/sase_artifacts.md`

1. **Section "Model"**:
   - Register `goal:` as a first-class canonical artifact kind alongside plans, beads, patches, and stitches (`goal:<id>`).
   - Mention `@goal:<id>` as canonical prompt citation syntax.
2. **Section "Read And Resolve"**:
   - Document that `sase artifact read goal:<id> "<reason>"` renders the compiled goal card (*You asked → Outcome → Claim → Check it → Evidence → Gaps → Agents → Timeline*).
3. **Section "Links"**:
   - Add the four new typed relation pairs from the Goals closed registry to the relations list:
     - `pursues`: inverse `pursued-by`, directed yes, written by `projection` (agent → goal).
     - `defines`: inverse `defined-by`, directed yes, written by `projection` (plan → goal).
     - `evidences`: inverse `evidenced-by`, directed yes, written by `projection` (artifact/commit/receipt → goal).
     - `follows`: inverse `followed-by`, directed yes, written by `projection` (goal → goal).
4. **Linked References**:
   - Link `[[sase_goals.md]]`.

---

### 4.3 Reference Memory: `sase/memory/xprompts.md`

1. **Launch Directives Table**:
   - Add `%goal:<id>`: Binds execution to an existing active goal.
   - Add `%goal:new`: Forces creation of a new goal instead of inheriting an existing one.
   - Document shared directive inheritance: `%goal` inherits across child prompts, session successors, retries, monitors, and dispatch (generalizing `%tab` inheritance).
2. **Project-Task Launches & Finalizer Section**:
   - Document `builtin@goal`: A required finalizer instance ordered `after: [commit]`.
   - Explain `/sase_final` payload integration: Every normal turn manifest includes the goal decision (`keep_open` or `claim`).
   - Phase vs Land Rule: Phase agents can only select `keep_open`; only land agents or single-worker turns may submit a `claim`.
   - Fail-open contract: Errors in `builtin@goal` fall open to `keep_open` with diagnostics, never failing an agent turn.
3. **Linked References**:
   - Link `[[sase_goals.md]]`.

---

### 4.4 Reference Memory: `sase/memory/sase_beads.md`

1. **Section "Types, Tiers, And Launching"**:
   - Clarify the structural boundary between Beads and Goals:
     - Beads track units of work (epic plans, phases, typed tasks).
     - Goals track user-facing intent, agent contributor groupings, and verification outcomes.
     - Approving an epic plan defines a goal (`defines` relation). Phase beads *pursue* that goal (`pursues` relation).
2. **Section "Statuses" & "Closing"**:
   - Clarify phase vs land responsibilities:
     - Phase workers append `PROPOSED FOLLOW-UP:` notes to their phase bead and must declare `keep_open` on the bound goal.
     - Land agents close the epic bead and submit the goal `claim`, opening a `GoalVerify` gate.
     - Explicitly state: Closing an epic bead does **not** settle the goal; human verification (or auto-ack) settles the goal.
3. **Section "Status Verbs"**:
   - Note the symmetrical protection: Just as agents must never hand-edit bead statuses, agents are strictly refused from invoking human status verbs on goals (`sase goal verify`, `reject`, `drop`, `reopen`, `merge`).

---

### 4.5 Reference Memory: `sase/memory/generated_skills.md`

1. **New Skill: `/sase_goal`**:
   - Generated from `src/sase/xprompts/skills/sase_goal/`.
   - Teaches agents how to inspect goals (`list`, `show`), name their assigned draft (`name`), or adopt an existing active goal (`adopt`).
   - Emphasize: There is **no** `/sase_new_goal` skill because agents do not create goals from scratch (the host binds them or creates drafts).
   - Document that human status verbs (`verify`, `reject`, etc.) are omitted from the skill because they are human-only.
2. **Updated Skill: `/sase_final`**:
   - Document that `sase final submit` includes the goal action payload (`keep_open` or `claim`).

---

### 4.6 Reference Memory: `sase/memory/cli_rules.md`

- **Human-Only Status Mutation Convention**:
  - Add an explicit rule: Subcommands that mutate review, settlement, or triage state on behalf of human reviewers (`verify`, `reject`, `drop`, `merge`, `reopen`) must refuse execution when run inside agent execution environments.
  - This rule unifies the behavior across `sase bead update --status` and `sase goal verify|reject|drop|merge|reopen`.

---

### 4.7 Reference Memory: `sase/memory/tui.md` & `tui_perf.md`

1. **`sase/memory/tui.md`**:
   - Note the addition of the `Goals` tab to `TAB_ORDER` (Review, Running, Idle lanes).
   - Document Goals tab navigation and keybindings (`v` verify, `r` reject, `x` drop, `l` relaunch, `e` edit, `m` merge, `a` adopt, `p` prompt, `n` nudge/note, `/` filter, `P` project filter, `h` history).
2. **`sase/memory/tui_perf.md`**:
   - Document performance contracts for Goals:
     - Projection refresh < 2 ms at $n=100$.
     - Highlight-to-paint budget $\le 16\text{ ms}$.
     - Off-thread cache snapshot refreshes using change tokens.

---

### 4.8 Glossary Web Updates (Existing Strands)

Update the following existing strands in `sase/memory/glossary/`:
- **`artifact.md`**: Mention `goal:` as a first-class artifact kind alongside plans, beads, patches, and stitches.
- **`gate-turn.md`**: Add `GoalVerify` to the catalog of standard gates (`TaskTriage`, `PlanApproval`, etc.).
- **`agent-turn.md`**: Note that every normal LLM turn is host-bound to exactly one goal and must terminate with a goal action declaration (`keep_open` or `claim`).

---

## 5. Memory Files Evaluated and Intentionally Kept Unchanged

Rigorous memory management requires deciding what **not** to touch. The following files were evaluated and are recommended to remain unchanged:

1. **`sase/memory/sase_flags.md`**:
   - *Evaluation*: G1–G5 use temporary beta scaffolding flags. G6 removes the last flag.
   - *Verdict*: **No changes.** Per `sase_flags.md`, feature flags are temporary scaffolding that must be deleted upon landing. Once all Goals epics have landed, Goals is unconditional. Memory must not document retired flags.
2. **`sase/memory/rust_core_backend_boundary.md`**:
   - *Evaluation*: Goals places the ledger, reducer, wire types, and fast path in `sase-core`, and UI/glue in Python.
   - *Verdict*: **No changes.** Goals strictly follows the existing boundary. The existing note already defines the exact litmus test that Goals honors.
3. **`sase/memory/task_types.md` & `sase/memory/task_types/`**:
   - *Evaluation*: Do Goals introduce a new task type?
   - *Verdict*: **No changes.** Goals are not task beads; they are a distinct entity family (`goal:`, `sase goal`). Task bead types remain `bug`, `ci`, `feature`, `flake`, `memory`.
4. **`sase/memory/lint_and_test.md` & `symvision.md`**:
   - *Evaluation*: Verification and lint rules.
   - *Verdict*: **No changes.** Testing and linting rules (`just check` only, `symvision` handling) apply to Goals code identically to all other SASE code.
5. **`sase/memory/gotchas.md`**:
   - *Evaluation*: Keymap updates.
   - *Verdict*: **No changes.** The existing gotcha ("When changing keymaps... update `default_config.yml`") already covers the Goals tab keybindings.

---

## 6. Phasing: When Each Memory Update Should Land

Memory updates should not be dumped in a single massive PR at the very end of the program; nor should future features be documented before their code exists. Updates should be phased across the six epics:

```text
Pre-G1 ────────► G1 / G2 ────────► G3 / G4 ────────► G5 ────────► G6 (Landing)
ADR:             CLI & Artifacts   Finalizer &      TUI &          Full Reconciliation
Invariant        `sase_artifacts`  `xprompts.md`    Performance    `sase_goals.md`
Decision         `cli_rules.md`    `sase_beads.md`  `tui.md`       Core `sase.md`
Record           Glossary:         Skills:          `tui_perf.md`  Attention Cutover ADR
                 `goal`, `ledger`  `/sase_goal`                    `sase memory init`
```

### Stage 1: Pre-G1 (Before Planning Begins)
- **Land ADR**: `goals-host-binds-agents-claim-users-settle` in `sase/memory/decisions/`.
- *Rationale*: As noted in `sase_goals_epic_roadmap.md` §9, having this decision recorded upfront ensures all six epic plans cite it directly rather than re-arguing core invariants.

### Stage 2: During Epics G1 & G2
- **Update `sase_artifacts.md`**: Add `goal:` kind and `pursues` / `defines` relations.
- **Update `cli_rules.md`**: Document the human-only status mutation verb refusal rule.
- **Add Glossary strands**: `goal`, `goal-ledger`.

### Stage 3: During Epics G3 & G4
- **Update `xprompts.md`**: Document `%goal` directives, `builtin@goal`, and `/sase_final` manifest expansion.
- **Update `sase_beads.md`**: Clarify bead vs. goal roles, phase worker `keep_open`, and land agent `claim`.
- **Update `generated_skills.md`**: Add `/sase_goal` skill and `/sase_final` updates.
- **Add Glossary strands**: `goal-claim`, `goal-draft`, `goal-verify-gate`, `goal-adoption`, `answer-acknowledgement`.

### Stage 4: During Epic G5
- **Update `tui.md` & `tui_perf.md`**: Document Goals tab, keybindings, and performance budgets.

### Stage 5: During Epic G6 & Program Cutover
- **Create `sase/memory/sase_goals.md`**: Assemble the comprehensive canonical reference note.
- **Update Core Memory `sase/memory/sase.md`**: Append the `/sase_final` goal declaration sentence to §1.1.4.
- **Land ADRs**: `goal-ledger-cohosted-in-beads` and `attention-cutover-claim-based-notifications`.
- **Add Glossary strand**: `idle-goal`.
- **Run `sase memory init`**: Re-render `AGENTS.md` and sync all 9 provider instruction shims (`CLAUDE.md`, `GEMINI.md`, `QWEN.md`, `OPENCODE.md`, and home variants). Verify zero drift with `sase memory init --check`.

---

## 7. Context Token Impact Analysis

To ensure memory updates do not compromise agent efficiency, we analyze the net token impact on the agent instruction window:

| Component | Target Location | Estimated Tokens | Inlined on Every Turn? |
| :--- | :--- | :--- | :--- |
| Core Finalizer Sentence | `sase/memory/sase.md` (§1.1.4) | ~20 tokens | **Yes** (Paid on every turn) |
| Reference Description Entry | `AGENTS.md` (Reference catalog list) | ~25 tokens | **Yes** (1 line in reference list) |
| Web Descriptors Catalog | `AGENTS.md` (Strand lists in Web catalog) | ~35 tokens | **Yes** (3 decision titles + 8 glossary titles) |
| **Total Always-Loaded Increase** | — | **~80 tokens** | **Negligible (< 1.5% increase)** |
| Comprehensive Goals Reference | `sase/memory/sase_goals.md` | ~1,200 tokens | **No** (Audited read on-demand only) |
| Updated Reference Notes | `sase_artifacts`, `xprompts`, `beads`, etc. | ~800 tokens | **No** (Audited read on-demand only) |
| Decision & Glossary Strands | `decisions/`, `glossary/` | ~2,500 tokens | **No** (Audited read on-demand only) |

**Conclusion**: The proposed strategy is exceptionally token-efficient. Always-loaded context increases by only ~80 tokens (~0.05% of modern model context windows), while all detailed guidance is kept in on-demand reference memory and memory webs.

---

## 8. Summary Action Checklist for the User

Once all SASE Goal epics are complete, use this checklist to execute and verify the memory updates:

- [ ] **1. Create Reference Note**: Write `sase/memory/sase_goals.md` with YAML frontmatter parented to `AGENTS.md`.
- [ ] **2. Update Core Memory**: Append the `/sase_final` goal declaration sentence to `sase/memory/sase.md` (§1.1.4).
- [ ] **3. Update Reference Notes**:
  - [ ] `sase/memory/sase_artifacts.md` (add `goal:` kind, add `pursues`, `defines`, `evidences`, `follows` relations).
  - [ ] `sase/memory/xprompts.md` (add `%goal` directives, `builtin@goal` finalizer rules).
  - [ ] `sase/memory/sase_beads.md` (clarify bead vs goal boundaries, phase worker `keep_open`, land agent `claim`).
  - [ ] `sase/memory/generated_skills.md` (document `/sase_goal` skill and no `/sase_new_goal`).
  - [ ] `sase/memory/cli_rules.md` (document human-only status verb refusal rule).
  - [ ] `sase/memory/tui.md` & `tui_perf.md` (document Goals tab, keys, and performance budgets).
- [ ] **4. Add Decision Strands (`sase/memory/decisions/`)**:
  - [ ] `goals-host-binds-agents-claim-users-settle.md`
  - [ ] `goal-ledger-cohosted-in-beads.md`
  - [ ] `attention-cutover-claim-based-notifications.md`
- [ ] **5. Add & Update Glossary Strands (`sase/memory/glossary/`)**:
  - [ ] Add `goal.md`, `goal-claim.md`, `goal-draft.md`, `goal-verify-gate.md`, `goal-adoption.md`, `goal-ledger.md`, `answer-acknowledgement.md`, `idle-goal.md`.
  - [ ] Update `artifact.md`, `gate-turn.md`, `agent-turn.md`.
- [ ] **6. Regenerate and Synchronize Memory**:
  - [ ] Run `sase memory init` to re-render `AGENTS.md` and all 9 provider instruction shims.
  - [ ] Run `sase memory init --check` to confirm zero drift.
  - [ ] Run `just check` to ensure all memory lints, link integrity checks, and formatting pass.
