# Research Report: Visual Representation of Waves in SASE Agent Clans

**Researcher:** `research.4j.gem`  
**Date:** October 15, 2026  
**Artifact:** `research:202610/agent_clan_wave_visual_representation__gem.md`  
**Topic:** Designing intuitive, reliable, and aesthetically compelling wave visualizations for epic and generic agent clans in the SASE TUI.

---

## Executive Summary

Agent clans in SASE represent groups of cooperative, rootless agents executing concurrently toward a shared objective. In epic workflows, work is structured around a dependency Directed Acyclic Graph (DAG) partitioned into Kahn-style topological layers called **waves**, concluding with a consolidation "land" agent. 

However, as demonstrated by live telemetry and visual inspection of current TUI captures (e.g., `~/tmp/screenshots/20261015_124557.png`), the SASE TUI today provides **zero visual representation of waves** during live execution:
1. **Left-Pane Roster Fragmentation:** Clan members in the left-hand navigation pane are sorted strictly by status priority (`RUNNING` → `TESTING` → `WAITING` → `DONE`). This shatters the chronological and logical pipeline narrative: completed Wave 1 phases sink to the bottom, active Wave 1 phases float at the top, and pending phases from Waves 2 through 5 and the final landing agent are scrambled in the middle in arbitrary order.
2. **Right-Pane Card Disconnect:** The clan summary card announces `Counts: 7 phases · 5 waves`, but immediately regresses to a flat, unpartitioned 1-to-7 list of phases.
3. **Jump-Bar Blindness:** The footer JUMP legend (`0 .1 ✓ | 1 .2 ▶ | 2 .3 ▶ | 3 .4 ⏳ ...`) numbers agents chronologically but offers no visual boundaries between dependency layers.
4. **General Clan Omission:** Outside of epics, non-epic clans (research swarms, multi-prompt pipelines, custom automation clans) have no wave concept at all, even when their members declare clear multi-stage `%w` wait dependencies.

### Key Conclusions & Strategic Recommendations

- **Critique of the Proposal:** The plan to visually represent waves is **fundamentally sound and overdue** for epics, but extending wave chrome unconditionally to *every* agent clan requires crucial qualification. Embarrassingly parallel swarms (e.g., standard 4-agent research swarms with no intra-clan dependencies) have a wave depth of 1; plastering "Wave 1" across flat swarms creates visual noise without conveying structural information. 
- **Adaptive Wave Model:** Wave presentation should be **adaptive**: activated automatically whenever a clan exhibits a dependency depth $\ge 2$ (or possesses explicit epic plan metadata), while gracefully collapsing to the existing clean flat view for single-wave parallel swarms.
- **Unified DAG-Derived Waves:** Rather than introducing fragile manual `%wave` configuration, general clans should derive waves dynamically from the **intra-clan `%w` wait DAG**. This unifies epics, multi-prompt scripts, and custom workflows under a single mathematical model computed in the Rust backend (`sase_core`).
- **Cohesive 4-Surface TUI Design:**
  - **Left Pane:** Adopt **Wave-First Sorting** within clans paired with compact **Inline Wave Badges** (`W1`, `W2`, ..., `⚑L`) and a clan container progress pill (`[W1/5]`). This preserves 1-line vertical density without bloating the tree with collapsible sub-banners.
  - **Right Pane Summary:** Restructure the epic/clan summary card into distinct, stylized **Wave Sections** with per-wave status rollups (`── Wave 1 of 5 · 2 running, 1 done ──`).
  - **JUMP Legend:** Introduce subtle wave demarcators (`┆` or bracketed groups) and active-wave color accenting in the bottom navigation bar.
  - **Dedicated Pipeline View:** Introduce an optional Unicode/ASCII stage diagram on the Clan deck (`MAIN spread | Summary | Waves`) illustrating inter-wave progression.

---

## 1. Current State Architecture & Baseline Analysis

### 1.1 The Baseline: Deconstructing `20261015_124557.png`

Analyzing the screenshot of clan `bob-cli-7v` reveals the exact pain points experienced by users today:

```
Left Pane (Agent List):
@epic · 8 [R2 W5 D1] ⌖1
▼ Running · 8 agents · 2 running
  ▼ bob-cli (RUNNING) [R2 W5 D1] ⌖1 bob-cli-7v        12m54s / 13m36s
    └ ⚡ bob-cli (RUNNING) x4 ◆ bob-cli-7v.3                     12m54s
    └ ⚡ bob-cli (TESTING) x6 o1 ◆ bob-cli-7v.2          🏃 22s / 13m36s
    └ ⚡ bob-cli (WAITING 2 o6 4 1 o1) ◆ bob-cli-7v.land
    └ ⚡ bob-cli (WAITING 1 o1) ◆ bob-cli-7v.7
    └ ⚡ bob-cli (WAITING 1 o1) ◆ bob-cli-7v.6
    └ ⚡ bob-cli (WAITING 1 o2 1) ◆ bob-cli-7v.5
    └ ⚡ bob-cli (WAITING 1 o1 1 o1) ◆ bob-cli-7v.4
    └ ⚡ bob-cli (DONE) x5 ◆ bob-cli-7v.1              12:40:51 · 8m10s ✏
```

#### Observations from the Active Run:
- **Clan Structure:** `bob-cli-7v` is an epic clan with 7 authored phases plus 1 land agent (`bob-cli-7v.land`).
- **Dependency Reality:**
  - **Wave 1:** Phases 1 (`dedupe`), 2 (`naming`), and 3 (`adapter`) have no intra-epic dependencies. They launch concurrently.
  - **Wave 2:** Phase 4 (`gate`) waits on Phases 1 and 2.
  - **Wave 3:** Phase 5 (`route`) waits on Phases 3 and 4.
  - **Wave 4:** Phase 6 (`listen`) waits on Phase 5.
  - **Wave 5:** Phase 7 (`docs`) waits on Phase 6.
  - **Land:** `bob-cli-7v.land` waits on all phases.
- **Visual Breakdown in the TUI:**
  - **Phase 1** has completed (`DONE`). Because `DONE` has lowest priority in `_CLAN_MEMBER_STATUS_PRIORITIES` (priority 5), it is sent to the very bottom of the list.
  - **Phases 2 & 3** are actively executing (`TESTING`, `RUNNING`). They have priority 2, so they sit at the top.
  - **Phases 4, 5, 6, 7, and land** are all `WAITING` (priority 4). Because their status priority is identical, their order is determined by insertion order from roster hydration. Consequently, `.land` appears *above* `.7`, `.6`, `.5`, and `.4`.
  - **The Mental Tax:** To understand what is happening, a developer must cross-reference the tiny dependency count glyphs (`2 o6 4 1 o1`) against the Summary card on the right, manually reconstructing the DAG in their head to realize that Phase 4 is waiting for Phase 2 to finish, while Phase 5 cannot start until Phase 4 and Phase 3 finish.

### 1.2 Code Inspection: How Clans and Waves Work Today

1. **Epic Work Plan Generation (`sase_core::bead::work` & `sase.bead.work_plan`):**
   - In `sase_core::bead::work::build_epic_work_plan_from_issues`, open phases are layered Kahn-style:
     ```rust
     while !remaining.is_empty() {
         let ready: Vec<&str> = remaining
             .iter()
             .copied()
             .filter(|pid| deps.get(pid).is_some_and(|blockers| blockers.is_subset(&placed)))
             .collect();
         ...
         placed.extend(ready.iter().copied());
         waves.push(ready);
     }
     ```
   - Each phase is assigned a 0-based `wave` index.
   - However, when `render_multi_prompt` in `src/sase/bead/work_prompt.py` emits the launch prompt, the wave number is **discarded**. Only `%w(<agent_dependencies>)` and `%w(bead=<bead_dependencies>)` directives are materialized into agent instructions.
2. **Clan Tree Projection (`src/sase/ace/tui/models/_agent_tree_clan.py`):**
   - The TUI synthesizes clan containers via `project_clan_tree`.
   - Direct clan members are sorted via `_sort_clan_member_units`:
     ```python
     units.sort(
         key=lambda unit: clan_member_status_priority(
             unit[0].status,
             unit[0].retried_as_timestamp,
         )
     )
     ```
   - No wave attribute exists on `Agent` or `AgentStateSessionFields`. Sorting is 100% status-driven.
3. **Member Roster Plumbing (`src/sase/ace/tui/widgets/prompt_panel/_member_roster.py`):**
   - Remarkably, `MemberRosterEntry` already defines `group_label: str | None = None`.
   - In `append_member_roster`:
     ```python
     if entry.group_label is not None and entry.group_label != previous_group_label:
         text.append(f"  {entry.group_label}\n", style="dim italic #8787AF")
     previous_group_label = entry.group_label
     ```
   - However, `clan_roster_entries` in `_agent_display_clan_roster.py` leaves `group_label` as `None`. The capability to display group dividers in the right pane roster has existed in the codebase, completely unused for clan members!

---

## 2. Critique of the Proposed Plan & Requirement Adjustments

The user's prompt outlines the following intent:
> *"I want to fix that by showing the waves that exist in every agent clan (even research clans and custom, user-defined clans) in some visually appealing way in the TUI."*

### 2.1 Critique 1: Should Waves Exist for "Every" Agent Clan?

**Assessment: Desirable in theory, but harmful if applied naively.**

1. **The Parallel Swarm Problem:**
   - Consider a typical research swarm, such as the 4-researcher swarm investigating this request (`research.4j.cdx`, `.cld`, `.grk`, `.gem`). All four researchers execute simultaneously with zero inter-agent dependencies.
   - If we treat every clan as having waves, this research clan has exactly **one wave** ($W=1$).
   - If the UI unconditionally renders `Wave 1` headers, `[W1/1]` badges, and wave section dividers, we add visual noise that communicates nothing: every agent is in Wave 1.
2. **The Pipeline Swarm Opportunity:**
   - Conversely, consider a research workflow that dispatches 4 exploratory researchers in parallel, followed by a lead researcher that synthesizes their findings (`research.4j.lead` with `%w(research.4j.*)`).
   - That workflow has **two waves** ($W=2$): Wave 1 (exploration) and Wave 2 (synthesis).
   - In that scenario, showing waves is deeply informative and visually gratifying!
3. **Recommended Adjustment (Adaptive Threshold):**
   - **Rule:** A clan displays wave representations **if and only if** $\text{wave\_count} \ge 2$, or if it is an epic clan with explicit plan metadata.
   - Single-wave clans ($\text{wave\_count} = 1$) suppress wave chrome and render as standard parallel containers. This preserves minimalism where waves do not matter, while highlighting structure where they do.

### 2.2 Critique 2: How Should Waves Be Defined for Non-Epic Clans?

**Assessment: Waves must be derived from the intra-clan `%w` DAG, NOT manually authored.**

1. **Why Manual `%wave` Directives are an Anti-Pattern:**
   - If we required users or macros to declare `%wave:1`, `%wave:2`, we introduce a dangerous dual source of truth.
   - In SASE, execution is strictly governed by the scheduler (AXE) and `%w` wait directives. If an agent declares `%wave:2` but lacks a `%w` dependency on Wave 1, the scheduler will start it immediately in parallel if queue capacity permits!
   - A visual indicator that claims an agent is in "Wave 2" while it is actively running in parallel with "Wave 1" destroys trust and creates cognitive dissonance.
2. **The Correct Solution (DAG Topological Rank):**
   - In any clan, every member's wait list `waiting_for` can be filtered to intra-clan peers:
     $$E_{\text{intra}} = \{ (u, v) \mid u, v \in \text{Clan}(C) \land v \text{ waits on } u \}$$
   - Applying Kahn's algorithm or longest-path DAG layering on $G = (V_C, E_{\text{intra}})$ computes the exact topological layer for every member:
     - $\text{Wave}(v) = 1 + \max_{(u, v) \in E} \text{Wave}(u)$ (with $\text{Wave}(u) = 1$ for root nodes).
   - This approach is 100% automatic, requires zero changes to user prompt syntax, works for custom multi-prompts, and is guaranteed to mirror the scheduler's actual execution constraints.

### 2.3 Critique 3: Static Waves vs. Dynamic Asynchronous Execution

**Assessment: Waves represent topological tiers, not rigid wall-clock barriers.**

- In DAG execution, if Phase 4 depends only on Phase 1, and Phase 1 finishes in 2 minutes while Phase 2 and 3 take 30 minutes, Phase 4 can start running immediately!
- Under Kahn layering, Phase 4 might be categorized as Wave 2. If Phase 4 starts running while Phase 2 (Wave 1) is still running, both Wave 1 and Wave 2 are simultaneously active.
- **Design Implication:** The UI must not treat waves as rigid sequential "pages" where Wave 2 is locked until Wave 1 is 100% empty. The UI must elegantly support **multiple active waves** (e.g., "Wave 1 & 2 active"), reflecting real asynchronous execution.

---

## 3. Comprehensive Visual Design: Intuitive, Reliable, Beautiful

To achieve the user's goal of making the feature intuitive, reliable, and beautiful, we propose changes across the four key surfaces of the SASE TUI.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ AGENTS TAB OVERVIEW WITH WAVE INTEGRATION                                                                              │
├─────────────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────┤
│ LEFT PANE: AGENT ROSTER                 │ RIGHT PANE: CLAN DECK & SUMMARY                                              │
│                                         │                                                                              │
│ @epic · 8 [R2 W5 D1] ⌖1                 │ CLAN                                                                         │
│ ▼ Running · 8 agents                    │ bob-cli-7v RUNNING [R2 W5 D1]                                                │
│   ▼ bob-cli (RUNNING) [W1/5] bob-cli-7v │ bob-cli · @epic · 9 agents · 5 waves (Wave 1 active) · 13m34s · 1/3          │
│     ├ ⚡ W1 (TESTING) bob-cli-7v.2 🏃 22s│ ──────────────────────────────────────────────────────────────────────────── │
│     ├ ⚡ W1 (RUNNING) bob-cli-7v.3  12m │ MAIN spread · auto | Summary | Waves                                         │
│     ├ ⚡ W1 (DONE)    bob-cli-7v.1   8m │                                                                              │
│     ├ ⚡ W2 (WAITING) bob-cli-7v.4      │ ── Wave 1 of 5 · 2 running, 1 done ───────────────────────────────────────── │
│     ├ ⚡ W3 (WAITING) bob-cli-7v.5      │ 1 Dedupe import ... [small]  ✓ done (8m10s)                                  │
│     ├ ⚡ W4 (WAITING) bob-cli-7v.6      │ 2 Pure naming ...   [medium] 🏃 testing (22s)                                │
│     ├ ⚡ W5 (WAITING) bob-cli-7v.7      │ 3 Adapter render... [medium] ▶ running (12m54s)                              │
│     └ ⚡ ⚑L (WAITING) bob-cli-7v.land   │                                                                              │
│                                         │ ── Wave 2 of 5 · 1 waiting ───────────────────────────────────────────────── │
│                                         │ 4 Variadic TARGET.. [medium] ⏳ waiting (after dedupe, naming)                │
│                                         │                                                                              │
│                                         │ [Waves 3-5 & Land collapsed/scrollable...]                                   │
├─────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────┤
│ FOOTER JUMP BAR:                                                                                                       │
│ JUMP CLAN MEMBERS 0-7 · 5 WAVES                                                                                        │
│ W1 [ 0 .1 ✓ | 1 .2 🏃 | 2 .3 ▶ ] ┆ W2 [ 3 .4 ⏳ ] ┆ W3 [ 4 .5 ⏳ ] ┆ W4 [ 5 .6 ⏳ ] ┆ W5 [ 6 .7 ⏳ ] ┆ L [ 7 .land ⏳ ]  │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Surface 1: Left Pane (The Agent List Roster)

The left pane is the most critical navigation element. Screen real estate is precious; vertical bloat pushes other clans off screen.

#### Design Decision: Wave-First Sorting + Inline Badges (Rejecting Subtree Banners)
- **Why Reject Subtree Banners?**
  Adding `▼ Wave 1`, `▼ Wave 2`, ..., `▼ Wave 5`, `▼ Land` headers under the clan container adds 6 extra rows to an 8-member clan. This almost doubles the height of the clan from 9 rows to 15 rows. In terminals with 35-40 lines, a single clan would monopolize half the visible screen.
- **The Winner: Inline Badges with Logical Wave-First Sorting:**
  1. **Clan Container Header Badge:**
     On the clan container row, display the active wave progression:
     ```
     bob-cli (RUNNING) [R2 W5 D1] [W1/5] ⌖1 bob-cli-7v
     ```
     - Style: `[W1/5]` styled in bold cyan (`bold #00D7D7`) or bright magenta (`bold #D75FFF`), signaling that the clan is currently on Wave 1 of 5.
     - When all waves are done and land is running: `[W:Land]` or `[W:⚑]`.
  2. **Member Rows: Inline Wave Chips:**
     Each child row displays a concise wave tag between the tree glyph and the status parenthetical:
     ```
     ├ ⚡ W1 bob-cli (TESTING) x6 o1 ◆ bob-cli-7v.2          🏃 22s / 13m36s
     ├ ⚡ W1 bob-cli (RUNNING) x4 ◆ bob-cli-7v.3                     12m54s
     ├ ⚡ W1 bob-cli (DONE) x5 ◆ bob-cli-7v.1              12:40:51 · 8m10s ✏
     ├ ⚡ W2 bob-cli (WAITING 1 o1 1 o1) ◆ bob-cli-7v.4
     ├ ⚡ W3 bob-cli (WAITING 1 o2 1) ◆ bob-cli-7v.5
     ├ ⚡ W4 bob-cli (WAITING 1 o1) ◆ bob-cli-7v.6
     ├ ⚡ W5 bob-cli (WAITING 1 o1) ◆ bob-cli-7v.7
     └ ⚡ ⚑L bob-cli (WAITING 2 o6 4 1 o1) ◆ bob-cli-7v.land
     ```
  3. **Wave-First Sorting Hierarchy:**
     Instead of sorting purely by status across the entire clan, sort by:
     $$\text{SortKey} = (\text{WaveIndex}, \text{StatusPriority}, \text{StartTime})$$
     - **Effect:** Wave 1 members always appear first! Within Wave 1, active members (`RUNNING`, `TESTING`) sort above `DONE`.
     - Then Wave 2 members appear next, followed by Wave 3, Wave 4, Wave 5, and finally Land.
     - **Tree branch rendering:** Use `├ ` for all items and `└ ` strictly for the terminal member (`.land`).
     - **Result:** The list reads as a clear, top-to-bottom pipeline that reflects the real execution sequence, while still floating active work to the top of the active wave!

### 3.2 Surface 2: Right Pane - Clan Summary Card

The Summary Card (generated by `sase_clan_summary_epic.py` and `_agent_clan_summary_text.py`) is where users read the details of the epic.

#### Design Transformation:
Transform the flat numeric phase list into **Structured Wave Sections**:
- Each wave gets a titled section rule:
  `── Wave 1 of 5 · 2 running, 1 done ─────────────────────────────`
- Active waves are highlighted with a vibrant accent (e.g., `#87D7FF` or `#D75FFF`); pending waves are muted (`dim #8787AF`); completed waves use green tinting (`#5FD787`).
- Each phase within the wave shows its live status chip:
  - `✓ done` (Phase 1)
  - `🏃 testing` (Phase 2)
  - `▶ running` (Phase 3)
  - `⏳ waiting` (Phases 4-7, Land)
- Dependencies are clearly annotated (`after dedupe, naming`).
- Land phase is given its own concluding banner:
  `── Land Phase · 1 waiting ──────────────────────────────────────`

### 3.3 Surface 3: Bottom JUMP Legend Bar

The bottom bar (`_agent_jump_legend.py`) is used for rapid keyboard jumping (keys `0`–`9` and `'` jump mode).

#### Current State:
`JUMP CLAN MEMBERS 0-7`  
`0 .1 ✓ | 1 .2 ▶ | 2 .3 ▶ | 3 .4 ⏳ | 4 .5 ⏳ | 5 .6 ⏳ | 6 .7 ⏳ | 7 .land ⏳`

#### Enhanced Design with Wave Grouping:
1. **Title Enrichment:**
   `JUMP CLAN MEMBERS 0-7 · 5 WAVES (W1 ACTIVE)`
2. **Subtle Wave Partitioning:**
   Use dotted vertical bars (`┆`) to divide waves, with wave tags:
   `W1 [0 .1 ✓  1 .2 🏃  2 .3 ▶] ┆ W2 [3 .4 ⏳] ┆ W3 [4 .5 ⏳] ┆ W4 [5 .6 ⏳] ┆ W5 [6 .7 ⏳] ┆ ⚑L [7 .land ⏳]`
3. **Visual Responsiveness:**
   On narrow viewports where space is tight:
   `0 .1 ✓ 1 .2 🏃 2 .3 ▶ ┆ 3 .4 ⏳ ┆ 4 .5 ⏳ ┆ 5 .6 ⏳ ┆ 6 .7 ⏳ ┆ 7 .land ⏳`
   The subtle `┆` character costs only 1 cell between wave boundaries, preserving high density while clearly demarcating stages.

### 3.4 Surface 4: Dedicated Pipeline / DAG Visualization Deck Card

In addition to Summary and Spread, add a **Pipeline / Waves** card view to the Main Deck for clans with $\ge 2$ waves:

```
┌────────────────────────────────────────────────────────────────────────┐
│ PIPELINE: bob-cli-7v (Wave 1 active · 1/5 waves complete)              │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  [ WAVE 1 ] ──▶  [ WAVE 2 ] ──▶  [ WAVE 3 ] ──▶  [ WAVE 4 ] ──▶ [W5]   │
│  ● 1 done        ○ 1 wait        ○ 1 wait        ○ 1 wait       ○ 1 wt │
│  ▶ 2 running                                                           │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ .1  ✓ 8m │    │ .4  ⏳    │    │ .5  ⏳    │    │ .6  ⏳    │   ...    │
│  │ .2  🏃22s│    └──────────┘    └──────────┘    └──────────┘          │
│  │ .3  ▶12m │                                                          │
│  └──────────┘                                                          │
│       │               ▲               ▲                                │
│       └───────────────┴───────────────┘                                │
│                                                                        │
│  [ LAND AGENT ]                                                        │
│  └─ .land ⏳ waiting on all phases                                      │
└────────────────────────────────────────────────────────────────────────┘
```
This diagram is rendered using standard Rich boxes and ASCII/Unicode arrows, requiring no external graphical dependencies and rendering instantly off-thread.

---

## 4. Technical Architecture & Implementation Blueprint

Following SASE's core architectural guidelines (including the Rust Core Backend Boundary in Rule 1.3), backend scheduling and domain calculations belong in `sase_core`, while Textual presentation remains in Python.

### 4.1 Rust Core (`sase_core`): Generic Clan Wave Derivation

Introduce a pure DAG layering utility in `sase_core::agent::clan_waves`:

```rust
// In crates/sase_core/src/agent/clan_waves.rs

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClanMemberDepWire {
    pub name: String,
    pub waits_on: Vec<String>,
    pub status: String,
    pub is_land: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClanWaveAssignmentWire {
    pub name: String,
    pub wave_index: usize, // 1-based
    pub is_land: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClanWaveScheduleWire {
    pub wave_count: usize,
    pub active_wave: usize,
    pub assignments: Vec<ClanWaveAssignmentWire>,
    pub has_cycle: bool,
}

pub fn derive_clan_waves(members: &[ClanMemberDepWire]) -> ClanWaveScheduleWire {
    // 1. Filter waits_on to intra-clan members only.
    // 2. Identify land agent (either explicit or waiting on all other members).
    // 3. Run Kahn's topological sort on remaining members.
    // 4. Assign wave_index = layer + 1.
    // 5. Determine active_wave (the lowest wave containing non-terminal members).
    ...
}
```

**Benefits:**
- Hermetic, fast (sub-millisecond execution for up to 1,000 members).
- Guaranteed cycle detection.
- Shared between Python TUI, CLI (`sase clan show`), and future web or API endpoints.

### 4.2 Python Data Model Layer

Update `AgentStateSessionFields` and `Agent`:
- `clan_wave: int | None = None`: The 1-based wave index of this member.
- `is_clan_land_member: bool = False`: Flag indicating if this is the final land agent.
- `clan_wave_count: int | None = None`: On the clan container row, total waves.
- `clan_active_wave: int | None = None`: On the clan container row, currently active wave.

### 4.3 Python Presentation & Widget Wiring

1. **`src/sase/ace/tui/models/_agent_tree_clan.py`:**
   - In `project_clan_tree`, invoke wave derivation for each clan container:
     - For epic clans, populate wave assignments from the already-loaded `EpicWorkPlan` (or via `bead_build_epic_work_plan`).
     - For general clans, populate wave assignments via `derive_clan_waves` over `member.waiting_for`.
   - Update `_sort_clan_member_units`:
     ```python
     def _clan_member_sort_key(unit: list[Agent]) -> tuple:
         anchor = unit[0]
         # Land agent always sorts last
         if anchor.is_clan_land_member:
             return (9999, anchor.status)
         wave = anchor.clan_wave or 1
         priority = clan_member_status_priority(anchor.status, anchor.retried_as_timestamp)
         return (wave, priority)

     units.sort(key=_clan_member_sort_key)
     ```
2. **`src/sase/ace/tui/widgets/_agent_list_render_agent.py`:**
   - On the clan container row: render the `[W{active}/{total}]` pill in cyan next to the status chip `[R2 W5 D1]`.
   - On member rows: in `_agent_list_render_agent_prefix.py`, render `W1`, `W2`, ..., `⚑L` right before the status parenthetical.
3. **`src/sase/ace/tui/widgets/prompt_panel/_agent_display_clan_roster.py`:**
   - In `clan_roster_entries`, populate `entry.group_label`:
     ```python
     wave_label = (
         "Land Phase" if member.is_clan_land_member 
         else f"Wave {member.clan_wave} of {clan.clan_wave_count}"
     )
     entries.append(
         MemberRosterEntry(
             ...,
             group_label=wave_label if clan.clan_wave_count > 1 else None,
         )
     )
     ```
   - This immediately activates wave subheadings in the right pane roster with zero new widget code!
4. **`src/sase/scripts/sase_clan_summary_epic.py`:**
   - Update `_render_plan_summary` to group phases under wave subheaders rather than emitting an unpartitioned list.

---

## 5. Edge Cases, Failure Modes, and Gotchas

### 5.1 Cycle Detection in User-Defined Clans
- **Risk:** A user authors a custom multi-prompt with cyclical waits:
  `A waits on B; B waits on A`.
- **Handling:** When Kahn's algorithm detects a cycle, `derive_clan_waves` flags `has_cycle = true`. The TUI must not crash or hang. Instead:
  - Fall back gracefully to `wave = None` (flat list).
  - Decorate the clan container with a warning pill: `[⚠️ Cycle]`.
  - The unresolvable agents already render unresolvable wait indicators (`WAIT_UNKNOWN_GLYPH`).

### 5.2 External Waits vs. Intra-Clan Waves
- **Risk:** An agent in Wave 1 of clan `myclan` waits on an external bead `bead-999` from another project.
- **Handling:** External dependencies must **not** increment intra-clan wave numbers. Waves measure the internal stage structure of the clan. The external wait remains visible via the bead glyph (`o1`), but the member remains logically in Wave 1 of this clan.

### 5.3 Dynamic Member Addition Mid-Flight
- **Risk:** A clan member launches follow-up subagents or child sessions during execution.
- **Handling:** Subagents with a `parent_timestamp` or session children belong to their parent member's unit (hierarchically nested). They inherit their parent's wave index and render indented under their parent.

### 5.4 Screen Width & Terminal Constraints
- **Risk:** In narrow terminal windows (e.g. 80 columns), adding `[W1/5]` or `W1` badges might cause row clipping.
- **Handling:**
  - In `_agent_list_render_layout.py`, calculate cell budget. If width is severely constrained, compress `[W1/5]` to `1/5` or suppress inline member badges while keeping wave-first ordering.

---

## 6. Comparison of Approaches

| Criteria | Option A: Subtree Banners in Left Pane | Option B: Inline Badges + Wave-First Sort (Recommended) | Option C: Right-Pane Only (Status Quo in Left) |
| :--- | :--- | :--- | :--- |
| **Left-Pane Density** | Poor (adds 5-8 lines per clan) | **Excellent (0 extra lines)** | Excellent (0 extra lines) |
| **Visual Elegance** | Cluttered, excessive lines | **Crisp, modern, high signal** | Low (jumbled status order persists) |
| **Mental Model Alignment** | High | **High (pipeline reads top-to-bottom)** | Poor (scrambled phases) |
| **Implementation Effort** | High (nested tree fold state) | **Moderate (clean model & sort update)** | Low (right-pane changes only) |
| **Screen Real Estate Impact** | Severe (monopolizes viewport) | **Negligible** | None |
| **General Clan Support** | Complex | **Seamless (DAG-derived)** | None |

---

## 7. Recommended Action Plan & Next Steps

1. **Step 1: Core Rust Binding (`sase-core`):**
   - Implement `sase_core::agent::clan_waves::derive_clan_waves`.
   - Expose via PyO3 as `derive_clan_waves`.
   - Add unit tests covering linear pipelines, diamond DAGs, cycles, and single-wave swarms.
2. **Step 2: Python Data Model Integration:**
   - Update `AgentStateSessionFields` with `clan_wave`, `clan_wave_count`, `clan_active_wave`, and `is_clan_land_member`.
   - Wire `project_clan_tree` to populate these fields during roster hydration.
3. **Step 3: Right Pane Roster & Summary Wave Grouping (Immediate Win):**
   - Pass `group_label` in `clan_roster_entries` for multi-wave clans.
   - Update `sase_clan_summary_epic.py` to render wave subheaders.
4. **Step 4: Left Pane Inline Badges & Wave-First Sorting:**
   - Update `_sort_clan_member_units` to sort by `(wave, status_priority)`.
   - Render `[W{active}/{total}]` on clan container and `W{N}` on child rows.
5. **Step 5: Bottom JUMP Legend Wave Partitioning:**
   - Add wave demarcation (`┆`) to `_agent_jump_legend.py`.
6. **Step 6: Dedicated Pipeline Visualizer Card:**
   - Add the `Waves` card view to the Clan deck area for rich ASCII pipeline visualization.

---

*Report prepared independently by researcher `gem`.*
