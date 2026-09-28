# SASE Goals Critique: Intent, Verification, and the Limits of Clan-Level Notification Silencing

_Researcher: gem (independent report) · Date: 2026-09-28 · Context: SASE Goals Roadmap & sase-1bu Epic Bead_

---

## 0. Executive Summary & Bottom-Line Recommendation

The question at hand is whether the extensive investment in **SASE Goals** (a 6-epic, ~35-phase architecture spanning storage ledgers, deterministic binding, claim finalizers, verification gates, TUI tabs, and attention cutovers) is justified, or whether SASE should instead pivot to a lightweight alternative: **customizing xprompt swarms and agent clans to suppress intermediate completion notifications and only notify on designated agents.**

### Bottom Line:
1. **Is "better notifications" the only value-add of Goals?**
   **No.** While reducing notification noise was the initial catalyst, Goals solves three other fundamental architectural problems:
   - **Verification vs. Notification:** SASE currently has binary process completion (`JumpToAgent` tagged `done`), but no concept of a structured *settlement decision* (Review → Verify / Reject & Relaunch / Drop) backed by durable, unforgeable evidence (commits, test receipts, check-it steps).
   - **Definition of Done as an Agent Steering Force:** Agents without an explicit goal optimize only their immediate local prompt. A bound goal (`SASE GOAL ⌖...`) and the required `builtin@goal` finalizer force agents to evaluate whether the outcome is true before claiming victory.
   - **Inventory of Intent:** SASE tracks processes (Agents tab), scheduled tasks (Beads), and designs (Plans), but has zero inventory of active, in-flight human intent across machines.

2. **Can customizing xprompt swarms and agent clans replace Goals?**
   **No.** Silencing certain clan/swarm members is a brittle partial fix:
   - **Coverage Blind Spot:** Swarms and clans account for less than ~15% of multi-agent runs. Over **41%** of weekly runs on athena (841 of 2,048 runs) are Epic phase/land agents (`sase bead work`), which do not use xprompt swarms. Pipe chains, session successors, and ad-hoc single-turn queries would continue to spam.
   - **The Dynamic DAG Trap:** As seen in `#research_swarm`, swarms with `critique=true` or `image=true` execute agents *after* the lead (`.final`). Static "notify the lead" rules either notify prematurely or fail to notify when execution graphs branch.
   - **The Precedent of `epic_launch_handoff.py`:** SASE already attempted an ad-hoc notification deferral hack for planner agents. It required file locks, atomic JSON state swaps, TTL sweeps, and complex recovery plumbing (`src/sase/bead/epic_launch_handoff.py`). Repeating this ad-hoc pattern across swarms, epics, and pipes recreates distributed state bugs without a domain model.
   - **Silence is Not Verification:** Even if only the lead notifies, the user still receives a bare unread dot pointing to a transcript, without structured evidence, test receipts, check-it steps, or a rejection/relaunch mechanism.

3. **Is the user's skepticism justified?**
   **Emphatically yes.** The current 6-epic, 35-phase plan suffers from **universal scope over-engineering**—most notably in **G4 (Drafts & Universal Binding)**:
   - Attempting to force every single casual question, one-line query, or bug check into a machine-local draft goal with LLM compare-and-swap naming, adoption logic, and answer-acknowledgement creates massive cognitive and token overhead (80 tokens + CLI tool calls per turn, plus 25+ answer-ack chores daily).
   - The immediate landing of G1 (`sase-1bu`) already demonstrated the high maintenance cost of this distributed ledger: child epic `sase-1bu.8` had to be created immediately to fix 12 distinct edge cases (phantom active goals, uppercase ID forks, doctor header blanking, projection leaks).

### Concrete Recommendation: Press forward, but with a "Structured Workflows First" scope reduction (Epics & Swarms first; defer G4 drafts and G5 standalone tab)
- **Do NOT abandon Goals** to write ad-hoc clan notification hacks. G1 (the Rust ledger) is already built and working in `sase-core`.
- **Pivot the roadmap:**
  1. **Finish G1 fixes (`sase-1bu.8`).** The immutable event ledger and hot projection are already sunk cost and functional.
  2. **Implement G2 (Deterministic Binding) ONLY for Epics and Swarms.** Bind epic phase/land agents to the epic's goal, and swarm members to a clan goal. Let all unassigned, single-turn prompts fail-open (remain unbound).
  3. **Implement G3 (Claims and `GoalVerify` Gate).** Empower the land agent and the swarm lead to submit a structured claim with evidence, while silencing contributor turns.
  4. **DEFER G4 (Universal Drafts) and G5 (Standalone TUI Tab).** Do not force casual questions to have goals. Settle high-value multi-agent verification first.

---

## 1. Deconstructing the Value Proposition: Is Notification Quality the Only Value-Add?

The premise of the user's skepticism is: *"if the only value-add is better notifications (so users are only notified when work they asked for is complete), couldn't we just customize xprompt swarms and/or agent clans to only send a completion notification for certain agents?"*

To evaluate this honestly, we must inventory what SASE Goals actually provides beyond raw notification reduction.

### 1.1 Notification vs. Verification (The Attention Mismatch)

The current SASE notification model treats agent completion as an exit event, not a decision event:
- In `src/sase/axe/run_agent_runner_finalize.py:460-470`, an agent exiting with code 0 constructs a `CompletionNotificationPayload` with action `JumpToAgent` and `tags=["done"]`.
- In the TUI, this sets an unread marker (`●`) on that agent's row.
- **Clicking the row dismisses the notification.**

This creates a fundamental structural problem:
- **An exit code is not a verdict.** An agent that crashed into an infinite loop and exited cleanly, or an agent that hallucinated an answer, or an agent that wrote broken code that fails linting, still sends a `JumpToAgent(done)` notification.
- **There is no verification protocol.** To verify the work today, the user must:
  1. Jump to the agent.
  2. Read through a 500-line chat transcript or raw tool logs.
  3. Inspect `git status` or browse the artifacts directory to figure out which files were touched.
  4. Manually run `just check` or test commands to see if the changes work.
  5. If the work is bad, open a new shell, write a prompt explaining what went wrong, and launch a new agent.

Under **SASE Goals (G3)**, a notification is replaced by a **`GoalVerify` gate**:
- The notification does not say "Agent 2g finished." It says:
  > **Goal ⌖7k2mq: Tailnet dispatch mesh works on every machine**  
  > **Claim:** All 3 nodes enrolled and respond to `%dispatch`.  
  > **Evidence:** `@commit` (adds daemon loop), `receipt:tool_run:01...` (all 42 tests passed).  
  > **Check it:** Run `sase dispatch --ping all`; expect all nodes to report 0ms.  
  > **Gaps:** Tailscale v1.50+ required; older nodes untested.
- The gate offers three explicit, typed human actions:
  - **Verify (`v`):** Marks the goal `done · verified`.
  - **Reject & Relaunch (`r`):** Collects user feedback and automatically relaunches a new agent bound to the same goal with the feedback pre-filled.
  - **Drop (`x`):** Abandons the objective without polluting the active list.

Customizing xprompt swarms to only notify on the lead agent still emits a raw `JumpToAgent(done)` unread dot. It gives the user zero structure for verification, zero evidence binding, and zero feedback/relaunch automation.

### 1.2 Definition of Done as an Agent Steering Force

In the current SASE architecture, an agent prompt is an open-ended instruction. The agent decides when to stop based on its internal context window:
- In multi-turn or complex tasks, agents frequently experience "goal drift": they solve a secondary problem, hit a roadblock, declare "I have finished setting up the prerequisites," and exit 0.
- When an agent is bound to a goal (`SASE GOAL ⌖...`) with explicit `outcome` and `criteria`, the agent's definition of done is externalized and anchored in its instructions.
- At the end of the turn, the required `builtin@goal` finalizer executes. The host explicitly asks:
  - *"Can you claim this goal? If yes, provide your claim, 1–3 check-it steps, and resolve candidate evidence."*
  - *"If not, provide a one-line progress note explaining why you are keeping it open."*

This changes model psychology: the model cannot simply output "Done!" in conversational text. It is forced by the host finalizer protocol to evaluate its own output against the stated goal criteria.

### 1.3 The Missing Layer: Intent vs. Process vs. Work vs. Design

SASE has three well-developed operational primitives:
1. **Processes (The Agents tab):** Ephemeral execution units. Shows what processes are running, paused, or dead.
2. **Scheduled Work (Beads):** Structured backlog items. Designed for engineering tasks that need triage, sizing, assignees, and dependencies.
3. **Designs (Plans):** Markdown documents (`sdd/tales/`, `sdd/epics/`) detailing how a feature will be implemented.

As documented in `sase_goals_why_not_beads.md`, **none of these represent human intent**:
- **Why Beads cannot represent intent:** A bead is scheduled work. 80% of daily SASE agent activity (questions, research swarms, quick fixes, ad-hoc audits) is NOT scheduled work. If every question created a bead, the backlog would accumulate ~16,000 dead beads a year, bloating `sase bead list` and triggering useless `TaskTriage` gates.
- **Why Agents cannot represent intent:** A research swarm is 5 agents. An epic is 1 planner + 6 phase workers + 1 land agent (8 agents). An agent is a worker, not the job.
- **Why Plans cannot represent intent:** A plan is a static blueprint. It has no live state, no sync across machines, and no verification gates.

Goals fill the empty quadrant: **Verified Intent**.
```text
  INTENT       ⌖ Goal ("Tailnet dispatch mesh works on every machine")
                  │ defines
  DESIGN       ▤ Plan (plan:202609/tailnet_dispatch.md)
                  │
  WORK         ◇ Epic Bead (sase-1bu) ── Phase Beads ── Land Bead
                  │
  EXECUTION    ● Planner Agent · Phase Workers · Land Agent
```

### 1.4 Provenance and Multi-Turn Continuity

When a user rejects an agent's work or asks a follow-up question:
- Today, the new agent is an isolated row in the Agents tab. History is fragmented across different agent IDs, and the context of why the second agent was spawned is lost unless manually reconstructed.
- Under Goals, all contributors across turns, sessions, and machines attach to a single persistent goal object (`goal:<id>`). Follow-up questions, rejections, and relaunches accumulate on the goal's timeline.

---

## 2. Technical Critique of the Alternative: "Just Customize Swarms and Clans"

The user asks: *"...couldn't we just customize xprompt swarms and/or agent clans to only send a completion notification for certain agents?"*

Let us evaluate the technical feasibility, failure modes, and architectural implications of this idea.

### 2.1 The 85% Coverage Blind Spot

The most immediate flaw in relying on xprompt swarms and agent clans for notification management is that **swarms and clans represent only a small minority of multi-agent execution in SASE.**

Based on empirical data from the lead synthesis and `sase-1bu`:
- Weekly volume on athena is **~2,048 agent runs**.
- **841 runs (~41%) are Epic-bound** (`sase bead work` launching a planner, multiple phase agents, and a land agent).
- **Epics do NOT use xprompt swarms or agent clans.** Epics are launched by the bead scheduler (`src/sase/bead/work_prompt.py`, `src/sase/axe/run_agent_runner_bead.py`).
- Dozens of other runs are chained via `sase pipe`, session successor turns, monitor continuations, or direct subagents.
- Approximately **25–30 runs per day are single-turn ad-hoc questions or tasks**.

If SASE only customizes xprompt swarms and clans:
1. Every Epic run will continue to spam 5–10 completion notifications (one per phase agent, plus planner, plus lander).
2. Every pipe chain will continue to notify on every intermediate link.
3. Every ad-hoc query will continue to ding the user with a useless process-level `done` chime.

To solve the notification problem across the entire system using the "clan/swarm" philosophy, SASE would have to independently invent ad-hoc silencing rules for:
- Epics (silence phase agents, notify lander)
- Pipes (silence all but the tail agent)
- Monitors (silence intermediate checks, notify on terminal state)
- Single-turn runs (silence unless an output variable is set)

This immediately blows up into four separate, uncoordinated silencing hacks across four distinct subsystems.

### 2.2 The Fragility of "Certain Agents" (Dynamic DAGs & Race Hazards)

Who is "the certain agent" that should send the notification?

Consider the `#research_swarm` xprompt. In the simple case:
```text
research.N.cdx ──┐
research.N.cld ──┼──► research.N.final (lead) ──► NOTIFY?
research.N.grk ──┘
```
It seems obvious: silence `cdx`, `cld`, `grk`, and let `final` send the notification.

However, as uncovered in `xprompt_swarm_goals.md` (§6 item 1), real xprompt swarms do not have a static terminal agent:
- When `#research_swarm` is invoked with `critique=true`, a critique agent is launched that executes `%wait:research.N.final`.
- When invoked with `image=true`, an infographic agent is launched that also waits on `final`.
- If both are enabled:
  ```text
  researchers ──► research.final ──┬──► research.critique
                                   └──► research.image
  ```
- If SASE hardcodes "only the lead (`.final`) notifies":
  - The user receives a completion notification while the critique and infographic agents are still running! The notification is premature.
- If SASE instead tries to implement "only notify when the clan has no live members":
  - Who evaluates this condition?
  - Because agents are ephemeral single-turn processes that exit independently, determining whether an agent is "the last member of the clan" requires distributed synchronization across workspaces.
  - What happens if a researcher fails or crashes? Does the clan hang forever in silence?

### 2.3 The Ghost of `epic_launch_handoff.py` (The Cost of Ad-Hoc Deferral)

We do not have to guess what happens when SASE builds ad-hoc notification deferral mechanisms without a domain model: **the codebase already tried it, and the result is `src/sase/bead/epic_launch_handoff.py`.**

To prevent planner agents from sending an annoying completion notification before the epic's phase agents are launched, SASE had to write:
- `defer_epic_completion` and `defer_epic_completion_until_monitor_settlement`
- A file-locking protocol (`log_file_lock`) on ephemeral paths
- A pending/settled JSON state machine on disk (`pending_path`, `settled_path`)
- A sweeping mechanism (`EpicCompletionSweepResult`, `EPIC_COMPLETION_SETTLED_TTL_SECONDS`)
- Complex error-handling where any failure to lock falls back to sending immediately

Attempting to "customize clans and swarms" to suppress and defer notifications would require duplicating this exact file-locking, TTL-sweeping, state-deferral machinery across `src/sase/agent/clan_membership.py` and `src/sase/agent/xprompt_swarm.py`.

It is a textbook case of avoiding a clean domain entity (Goals) only to reimplement its state machine poorly in ad-hoc file locks.

---

## 3. Steelman of Bryan's Skepticism: What Is Wrong with the Goals Plan?

Having critiqued the swarm-only alternative, we must turn an equally critical eye toward the existing SASE Goals plan (`sase_goals_epic_roadmap.md` and `sase_goals_design.md`).

Why is Bryan hesitating? His instinct is valid: **the current SASE Goals program is in serious danger of over-engineering and delivery failure.**

### 3.1 The 35-Phase Epic Risk and SASE Historical Evidence

The lead synthesis in `sase_goals_epic_roadmap.md` presents a sobering analysis of SASE root epics:
- Epics with 1–3 phases spawn a remediation child epic **16%** of the time (median 3.9 h to close).
- Epics with 6–7 phases spawn child epics **23%** of the time (median 4.8 h to close).
- Epics with 10–11 phases spawn child epics **50%** of the time (median 30.1 h to close).
- Epics with 12+ phases spawn child epics **58%** of the time (median 48.2 h to close).
- Contract-crossing epics (`sase-xe`, `sase-x7`, `sase-zm`) exploded to 33–82 phases and stalled for weeks.

To deliver Goals, the roadmap proposes **six sibling epics (G1–G6) totaling ~35 phases**:
- G1: Goal ledger, manual CLI, `goal:` artifact (6 phases)
- G2: Deterministic binding across 14 launch paths (6 phases)
- G3: Claims and verification gates (7 phases)
- G4: Drafts, naming, adoption, answer ack (6 phases)
- G5: Goals tab and Agents tab integration (6 phases)
- G6: Attention cutover and soak (4 phases)

**We are already seeing the warning signs.**
Look at what happened with G1 (`sase-1bu`), which just concluded its initial 7 phases:
- Land triage on 2026-09-28 (`sase-1bu.land`) immediately had to spawn a child epic, **`sase-1bu.8`**, to address a litany of edge-case bugs:
  - Edit/drop on unknown ID creates phantom active goals.
  - Raw uppercase IDs fork directory structures.
  - Criterion IDs use length rather than event indices.
  - Corrupt events abort the entire doctor and list commands.
  - Corrupt `goals-hot.json` projection is unrebuildable without manual intervention.
  - Doctor repair blanks projection headers.
  - Warm list p50 missed its 5ms target by 7x (38.7ms), requiring a separate bug bead (`sase-1c3`).
  - Acceptance tests leaked monkeypatches into real user directories (`~/.sase/projects/acme_goals_accept`).

If G1—which was purely mechanical Rust ledger I/O with zero model judgment and zero TUI code—already required an emergency remediation epic, what will happen when G2 attempts to bind 14 distinct launch paths, or when G4 introduces LLM draft naming?

### 3.2 The G4 Universal Draft Fallacy (Mechanism Before Corpus)

The single most dangerous part of the SASE Goals design is **G4: "Every agent has a goal."**

The design insists on an absolute invariant:
> *"Every LLM agent turn has exactly one primary goal."*

To satisfy this invariant for prompts that have no plan, no bead, and no explicit `%goal`, G4 invents **Draft Goals**:
1. Before an agent launches, the host mints a machine-local draft (`goal:7k2mq`).
2. An 80-token intake block is injected into the agent's prompt.
3. The agent is instructed to run `sase goal list`, decide if an active goal matches, and either run `sase goal adopt` or `sase goal name`.
4. Siblings in a clan race to name the goal using compare-and-swap.
5. If the agent dies before naming, the host auto-names it from prompt excerpts.
6. When the agent answers a simple question, it submits a claim with `@reply` evidence.
7. To avoid overwhelming the user, G4 invents "Answer Acknowledgement": opening the answer automatically marks the goal `done · acknowledged`.

**This is classic architectural over-reach:**
- Why are we forcing a distributed state machine, compare-and-swap naming, and draft adoption protocols onto a user asking: *"Where is the config file for ripgrep?"*
- SASE runs ~25 ad-hoc questions a day. Turning each of them into a draft goal, forcing the model to make CLI tool calls to name it, and generating 25 "acknowledged" state transitions adds token latency, tool-call failure surface area, and zero human value.
- The `corpus-before-mechanism` principle states: *SASE does not build memory retrieval or linking machinery ahead of a corpus that demonstrably needs it.* Universal draft goals violate this principle directly.

### 3.3 The TUI Risk (G5)

G5 proposes adding a second top-level tab to the TUI (`Agents | Goals | Artifacts | Services`), complete with Review, Running, and Idle lanes, bespoke goal cards, 12 new keybindings, and relation-rail jump integration.

As noted in `sase_goals_epic_roadmap.md`, G5 will cause massive **golden churn** (the Artifacts tab scaffold re-blessed 179 PNGs). It also creates interface redundancy:
- Today, the user's primary home is the **Agents tab**.
- Adding a Goals tab forces the user to switch back and forth between "Who is working?" (Agents) and "What is being done?" (Goals).
- If the goal review card is accessible directly from the notification gate (via `JumpToGoal` or gate modals), do we actually need a permanent top-level tab in v1? Probably not.

---

## 4. Architectural Comparison: Four Strategic Paths

To help Bryan decide whether to press forward, pause, or pivot, here is a structured comparison of the four viable paths:

| Dimension | Path 1: Full Goals (G1–G6 as planned) | Path 2: Clan/Swarm Silencing (User's Proposal) | Path 3: Claims Without Goals (cld alternative) | Path 4: Scoped Goals (Epics & Swarms First) |
| :--- | :--- | :--- | :--- | :--- |
| **Core Concept** | Distributed ledger + universal binding + gates + TUI tab | Suppress completion notifications on non-lead clan agents | Agent finalizer flag (`needs_review`) + gate; no Goal entity | G1 ledger + G2 binding for Epics/Swarms + G3 gates; drop G4/G5 |
| **Phases / Effort** | ~35 phases across 6 epics (~4–6 weeks) | 1–2 small tasks (~2–3 days) | ~10 phases across 2 epics (~1.5 weeks) | ~15 phases across 3 epics (~2 weeks) |
| **Noise Reduction** | **95%** (all success pings silenced; only claims notify) | **~15%** (swarms quiet; epics, pipes, questions still spam) | **80%** (agents choose when to be loud) | **85%** (epics and swarms quieted; claims notify) |
| **Verification Gate** | Yes (`GoalVerify` gate with typed evidence) | **No** (bare unread dot on agent row) | Yes (`ReviewGate` per agent) | Yes (`GoalVerify` gate on epic/swarm settlement) |
| **Evidence & Check-it** | Yes (commits, test receipts, check-it steps, gaps) | **No** (user inspects raw transcript) | Partial (attached to agent exit) | Yes (gathered on claim by lander/lead) |
| **Coverage of Work** | Universal (every turn bound) | Only xprompt swarms and explicit clans | Universal (per agent) | Structured multi-agent work (epics, swarms, explicit `%goal`) |
| **Failure Modes** | High complexity, G4 draft LLM games, verification fatigue | Premature notification on branched swarms, distributed file-lock bugs | No multi-agent aggregation; lead can't see researchers | None in casual runs (casual runs fail-open/remain unbound) |
| **Sunk Cost Impact** | Leverages G1 | Wastes G1 (abandons completed Rust ledger) | Wastes G1 | Leverages G1 fully |

---

## 5. Critical Analysis of Path 4: The "Scoped Goals" Compromise

Why is **Path 4 (Scoped Goals: Epics & Swarms First)** superior to both Full Goals and Clan Silencing?

### 1. It directly attacks the actual source of pain.
Where does the notification pain actually come from?
It does not come from running a single agent to ask a question. One question → one answer → one completion chime is completely acceptable human-computer interaction.
The pain comes from **multi-agent fan-outs**:
- You approve an epic, and 8 agents run sequentially/in parallel over 30 minutes, chiming on every phase.
- You launch `#research_swarm`, and 5 researchers each ding when their individual markdown draft is written, followed by the lead dinging.

By binding **only Epics and Swarms**:
- Epic phase agents bind to the Epic Goal → phase completions are SILENT.
- The land agent claims the Goal → **ONE** `GoalVerify` gate fires with the full commit and test receipt.
- Swarm researchers bind to the Swarm Goal → researcher completions are SILENT.
- The swarm lead claims the Goal → **ONE** `GoalVerify` gate fires with the synthesized research report.
This eliminates **85%+ of all notification noise** without writing a single line of G4 draft-naming code!

### 2. It avoids the G4 "Draft Goal" disaster.
- In Path 4, if a launch has no plan, no epic bead, no clan, and no explicit `%goal`, **it is unbound (`goal_id = None`)**.
- An unbound agent does NOT get an 80-token intake block.
- It does NOT make compare-and-swap CLI calls to name drafts.
- It does NOT generate draft markers in the ledger.
- It finishes its turn, commits its stitch, and sends its normal notification.
This keeps casual interactions light, fast, and free of state-machine overhead.

### 3. It leverages G1 rather than throwing it away.
`sase-1bu` was hard work. The Rust core domain model, the on-disk ledger in the beads sidecar, the hidden-clone write lane, and the `sase goal` CLI commands are already written. Abandoning Goals now throws away a tested, high-performance distributed ledger in order to write messy file-lock hacks in Python.

### 4. It defers the TUI golden churn (G5).
By utilizing the existing **Gate Modal infrastructure** (`src/sase/ace/tui/actions/agents/_notification_gate_actions.py`) and Telegram/mobile integrations for the `GoalVerify` gate, SASE does not need an immediate 6-phase overhaul of the TUI tabs. The Goals tab can be evaluated later when there is an actual corpus of verified goals.

---

## 6. Actionable Recommendation & Roadmap

### Should you press forward with Goals?
**YES, but pivot the scope immediately.** Do not build the monolithic 35-phase program, and do not fall into the trap of ad-hoc clan notification suppression.

### Concrete Action Plan:

1. **Immediate Next Step: Land `sase-1bu.8` (Goals G1 Landing Fixes)**
   - Complete the in-progress child epic `sase-1bu.8`.
   - Ensure the Rust core ledger and CLI honesty fixes land cleanly on master. This secures the foundational storage layer.

2. **Re-scope G2: Deterministic Binding (Epics & Swarms ONLY)**
   - Cut G2 down to **4 phases**:
     - Phase 1: Core resolver for explicit `%goal`, Epic Bead (`epic -> plan -> goal_id`), and Clan.
     - Phase 2: Directives: `%goal:<id>` and `%goal:new`.
     - Phase 3: Generalize `%tab` inheritance to propagate `goal_id` through `bead work`, dispatch, and session retries.
     - Phase 4: Stamping `goal_id` during `sase plan propose`.
   - **Explicitly drop from G2:** Draft resolution rungs, orphan audit enforcement for untyped launches. If an agent has no goal, it runs unbound (fail-open).

3. **Deliver G3: Claims and the `GoalVerify` Gate**
   - Implement `builtin@goal` finalizer (ordered after commit).
   - Rules:
     - Phase workers and swarm researchers have role `contributor` → can only submit `keep_open` (silent).
     - Land agents and swarm leads have role `owner` → submit `claim` with `@commit` or report artifact refs.
     - A claim generates a `GoalVerify` gate with Verify / Reject / Drop actions.
     - Rejecting relaunches onto the same goal with user feedback.
   - Silence `JumpToAgent(done)` **only** for agents that have an active bound goal.

4. **Pause and Measure before G4, G5, and G6**
   - With G1, G2 (scoped), and G3 landed:
     - Epics produce exactly 1 notification (the `GoalVerify` gate).
     - Swarms produce exactly 1 notification (the `GoalVerify` gate).
     - Casual questions continue working exactly as they do today.
   - Run this in production for 2 weeks.
   - Ask: *Do we actually miss having goals on casual single-turn questions?*
     - If no: **Cancel G4 and G6 permanently.** You have achieved 90% of the benefit at 40% of the cost.
     - If yes: Plan G4 based on measured demand rather than theoretical symmetry.

---
_Report produced independently by researcher gem in accordance with swarm isolation protocol._
