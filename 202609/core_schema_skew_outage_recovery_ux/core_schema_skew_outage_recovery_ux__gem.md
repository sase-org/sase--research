# Forensic Audit of Recent Systemic Agent Failures and TUI Recovery UX Architecture

**Author:** Researcher `gem` (5-Researcher Swarm)  
**Date:** 2026-09-25  
**Scope:** Root-cause audit of the multi-agent failure incident on 2026-09-25 (15:09–16:45 EDT), user rectification analysis, evaluation of TUI recovery UX alternatives, and architectural recommendation for SASE/ACE.

---

## 1. Executive Summary

Between approximately 15:09 and 16:15 EDT on 2026-09-25, a machine-wide cascading failure caused all active SASE agents and monitored tool procs across multiple ephemeral workspaces to fail. The incident halted ongoing epic implementation streams, corrupted multiple workspace git locks, and forced the user to conduct an emergency recovery involving manual lock removal, low-level Rust and Python contract repairs, and sequential manual agent restarts.

### Key Audit Findings
1. **Root Cause**: The outage was triggered by a cross-repository schema desynchronization between the Rust core backend (`sase-core`) and the Python client/TUI (`sase`). At 14:55 EDT, commit `2a0fc2ab` in `sase-core` landed breaking changes that bumped multiple wire schema versions (notably `scan_agent_artifacts` schema 9 $\to$ 10, work statistics schema 6 $\to$ 7, and launch wire schema 1 $\to$ 2). When the host environment ran updates and workspaces executed `just _setup`, ephemeral workspaces fast-forwarded their linked `sase-core` checkouts to `origin/master` and built/installed `sase_core_rs` 0.34.73. Because `sase` had not yet updated its Python schema mirrors, every monitored tool run failed during `_setup` validation (`validate_sase_core_rs`: *"scan_agent_artifacts probe returned stale schema: got 10, expected 9"*), causing active agents to abort.
2. **User Rectification**: The user identified the failure, pruned stale `.git/index.lock` files, purged a damaged workspace, attempted an initial batch of continuations at 15:57 (which failed due to the unrepaired schema mismatch), authored two backwards-compatibility commits in `sase-core` (`6cb3517`, `2457913`), and landed commit `d86bcc3ac` in `sase` (`fix(core)!: speak the agent-session core contract`) updating 45 files across the Python runtime and test suite. Following this fix, the user systematically relaunched or forked all failed agents between 16:12 and 16:45 EDT.
3. **UX Bottlenecks in the TUI (ACE)**: Recovery was excessively labor-intensive because the TUI provides **zero multi-agent recovery mechanisms**. While the TUI supports multi-selection via `_marked_agents` for killing, dismissing, waiting, and reverting, it does **not** support bulk retry or bulk fork/continuation. The user was forced to manually navigate to every failed agent row, trigger a single relaunch (`R` or `F`), review/submit the prompt bar, and repeat across more than a dozen agents. Furthermore, the absence of an **incident pre-flight health gate** allowed premature restarts (at 15:57) that immediately failed again, multiplying session fragmentation (`--1`, `--2`).

### Strategic Recommendation
We propose the **Incident-Aware Multi-Agent Recovery Architecture (IMARA)** for the SASE TUI, consisting of:
- **Tier 1 (Marked-Agent Bulk Operations)**: Extending `_marked_agents` with `R` (Bulk Retry) and `F` (Bulk Fork) accompanied by a unified multi-agent dispatch modal with rate-controlled slot queueing.
- **Tier 2 (Proactive Incident Triage & Pre-Flight Gating)**: An automated burst-failure detector that groups correlated agent crashes into a high-visibility Incident Banner, backed by an **Incident Recovery Wizard** that verifies system health (Rust-Python contract parity, git locks, daemon liveness) before allowing mass relaunch.
- **Tier 3 (Command Palette Batch Primitives)**: Direct colon commands (`:agent retry --failed`, `:agent fork --incident`) for keyboard-first operator recovery.

---

## 2. Forensic Audit: The Systemic Failure Incident

### 2.1 Chronological Incident Timeline (2026-09-25)

The incident unfolded over a 90-minute window on the primary host machine (`athena`):

```
14:55:11 EDT [sase-core] Commit 2a0fc2ab landed: "feat(core)!: canonicalize agent-session contracts"
                       Wire schemas bumped: scan (9->10), stats (6->7), launch (1->2).
       │
15:09:36 EDT [Host CLI] User ran: sase update -y && sase agent index gc && ace --restart-service
       │
15:10 - 15:40 [Workspaces] Agents dispatch monitored commands (sase tool run ...).
                       Each tool run invokes `just _setup`, which fast-forwards linked
                       sase-core checkouts to origin/master and rebuilds sase_core_rs.
       │
15:41 - 15:56 [Cascading Outage] validate_sase_core_rs fails across all workspaces:
                       "scan_agent_artifacts probe returned stale schema: got 10, expected 9"
                       Monitored commands fail with exit code 1; agents abort or crash.
                       Terminated processes leave stale .git/index.lock files in workspaces.
       │
15:41:20 EDT [Triage]  User removes stale index.lock in workspace sase_25.
15:37:52 EDT [Triage]  User cleans up broken workspace sase_14.
       │
15:57:40 EDT [Premature Recovery Attempt]
                       User attempts continuations/restarts for 0se--1, sase-17m.9--1, 0sf--1.
                       These immediately fail or hang because Python code is still unpatched.
       │
15:38 - 15:54 [sase-core Fixes]
                       Commit 6cb3517: fix(core): keep pre-contract artifact indexes readable
                       Commit 2457913: fix(core): accept pre-contract v2 agent relationship batches
       │
16:09:17 EDT [sase Fix Landed]
                       Commit d86bcc3ac: "fix(core)!: speak the agent-session core contract"
                       Updated Python mirrors (scan schema 10, etc.) across 45 files;
                       updated validate_sase_core_rs probes; pinned core revision to 2457913.
       │
16:12 - 16:45 EDT [Successful Recovery Waves]
                       Wave 1 (16:12-16:15): User restarts 0sd--1, sase-19i.2--1, sase-19o.3--1, sase-19p.2--1.
                       Wave 2 (16:27-16:44): User repairs failed pre-fix attempts: 0se--2, 0sf--2, sase-17m.9--2.
                       All agents resume successfully; bead phase work resumed via sbd work.
```

### 2.2 Deep Technical Root-Cause Analysis

The failure was a classic distributed contract desynchronization across the Rust/Python boundary.

#### 1. The Core Contract Flip
SASE delegates high-performance operations (agent artifact scanning, artifact indexing, runner slot capacity calculation, and directive parsing) to the `sase_core` Rust crate via `sase_core_rs` (PyO3 bindings).
In commit `2a0fc2ab` (`feat(core)!: canonicalize agent-session contracts`):
- Canonical `agent_session` keys were enforced over the legacy `session` alias.
- Wire schemas were incremented:
  - Agent artifact scan schema: `9` $\to$ `10`
  - Agent statistics / work schema: `6` $\to$ `7`
  - Agent launch wire schema: `1` $\to$ `2`
  - Agent cleanup plan schema: `5` $\to$ `6`

#### 2. The Auto-Upgrade Propagation Trap
When an agent or tool runs inside an ephemeral workspace (`sase_<N>`), its `Justfile` recipe `_setup` ensures linked repositories are up to date:
```bash
[setup] fast-forwarded /home/bryan/.../sase/repos/linked/sase-core to origin/master
[core-source] linked sase-core source changed since the extension was built; flagging an extension rebuild.
[setup] Rebuilding sase_core_rs: linked sase-core source changed since the extension was built.
```
As soon as the user initiated tool commands or agent runs following `sase update`, each workspace independently pulled `sase-core` `origin/master`, built or fetched the newly compiled wheel for `0.34.73`, and installed it into its virtual environment.

#### 3. The Validation Guardrail Tripping
The project has strict contract probes in `tools/validate_sase_core_rs`. Line 1122 of `validate_sase_core_rs` explicitly checked:
```python
if snapshot.get("schema_version") != 10:  # in old commit: != 9
    _error(
        "scan_agent_artifacts probe returned stale schema: "
        f"got {snapshot.get('schema_version')!r}, expected 9"
    )
    return False
```
Because the installed Rust binary produced payload `schema_version = 10`, but the workspace's validation script expected `9`, the probe immediately exited 1. 

Furthermore, running SASE processes (such as `sase tui` and `sase agent list`) encountered schema assertion errors when deserializing agent scans. Active monitored commands (`--mon`) aborted during `_setup`, resulting in:
```text
[validate_sase_core_rs] scan_agent_artifacts probe returned stale schema: got 10, expected 9
error: recipe `_setup` failed on line 141 with exit code 1
failed  exit=1  duration=590322ms
```

### 2.3 Comprehensive Audit of Affected Agents

An analysis of `~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/25/` and dismissed agent bundles revealed that over a dozen agents across 10+ workspaces collapsed simultaneously:

| Agent Identifier | Workspace | Parent / Role | Launch Time | Failure Mechanism / Error Signature |
| :--- | :--- | :--- | :--- | :--- |
| `0se--0` / `0se--mon` | `sase_25` | `claude_oauth_refresh_retry` | 15:41:42 | `scan_agent_artifacts` probe mismatch (got 10, expected 9); `_setup` failed exit 1. |
| `0sf--0` / `0sf--mon` | `sase_29` | `lease_index_lock_recovery` | 15:42:13 | `scan_agent_artifacts` probe mismatch (got 10, expected 9); `_setup` failed exit 1. |
| `sase-17m.9--mon` | `sase_12` | Epic Phase Bead `17m.9` | 15:41:43 | Agent statistics work-schema probe mismatch (got 7, expected 6); `_setup` exit 1. |
| `0sd--0` / `0sd--mon` | `sase_18` | `agent_header_preview_three_rows` | 15:38:37 | maturim rebuild $\to$ probe schema mismatch (got 10, expected 9); `_setup` exit 1. |
| `sase-19i.2--mon` | `sase_42` | Clan `sase-19i` Phase 2 | 15:45:17 | Monitored command failed during `_setup` tool validation. |
| `sase-19o.3--mon` | `sase_14` | Clan `sase-19o` Phase 3 | 15:48:20 | Workspace corrupted; lock failure; monitor terminated. |
| `sase-19p.2--mon` | `sase_44` | Clan `sase-19p` Phase 2 | 15:49:43 | Tool run failure on `validate_sase_core_rs`. |
| `sase-17x.13.10.6--mon`| `sase_24` | Clan `sase-17x` Phase 6 | 15:51:07 | Stalled during probe execution; lock contention. |
| `sase-17d.12.2--6` | `sase_0` | Clan `sase-17d` Phase 12 | 15:34:07 | Dismissed as FAILED in recent group `98ce6768a195`. |
| `0s8--0` | `sase_0` | Feature plan | 15:13:09 | Dismissed as FAILED in recent group `98ce6768a195`. |
| `0rv.w0.f0--2` | `sase_0` | Header layout refactor | 15:13:00 | Dismissed as FAILED in recent group `98ce6768a195`. |
| `sase-19i.2--1` | `sase_0` | Pre-continuation | 15:11:51 | Dismissed as FAILED in recent group `98ce6768a195`. |
| `0sa` / `0sa.r0--gate` | `sase_0` | Gate check | 15:22:36 | Dismissed as FAILED in recent group `b13e5b3f1982`. |

### 2.4 Audit of Actions Taken to Rectify the Situation

The user’s rectification procedure encompassed four distinct operational phases:

#### Phase 1: Lock and Workspace Cleanup (15:35 – 15:42)
Abrupt termination of git processes during `_setup` left lockfiles on disk. The user manually identified and cleared locks:
- Executed `rm -rf /home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_47/.git/index.lock`
- Executed `rm -rf /home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_12/.git/index.lock`
- Executed `rm -rf /home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_25/.git/index.lock`
- Purged corrupted workspace directory: `rm -rf sase_14 && q`
- Launched agent `0sc` to plan automated lock recovery (`lease_index_lock_recovery.md`).

#### Phase 2: Premature Relaunch Attempt (15:57)
Believing the issue might be transient or workspace-specific, the user initiated continuations/forks from the TUI for three agents:
- `0se--1` (15:57:40)
- `sase-17m.9--1` (15:57:48)
- `0sf--1` (15:57:57)
Because the Python codebase had not yet been updated, these new runs immediately hit the same schema assertions (`0se--mon-0`, `0sf--mon-0`, `sase-17m.9--mon-0`) and stalled or failed.

#### Phase 3: Synchronized Rust Core and Python Contract Fix (15:38 – 16:09)
The user executed a dual-repo fix:
1. **In `sase-core`**:
   - Commit `6cb3517` (15:38:20): `fix(core): keep pre-contract artifact indexes and saved groups readable` (ensured older disk formats did not crash the scanner).
   - Commit `2457913` (15:54:52): `fix(core): accept pre-contract v2 agent relationship batches`.
2. **In `sase`**:
   - Commit `d86bcc3ac` (16:09:17): `fix(core)!: speak the agent-session core contract`.
     - Bumped Python schema mirrors: scan (9 $\to$ 10), artifact index (32 $\to$ 33), cleanup (5 $\to$ 6), launch/launch-plan (1 $\to$ 2), gate follow-up (1 $\to$ 2), session-parent resolution (1 $\to$ 2), saved-group archive (2 $\to$ 3).
     - Standardized `agent_session` parameter across all dispatch facades.
     - Updated `tools/validate_sase_core_rs` probe expectations to schema 10.
     - Pinned `sase-core-revision.txt` to `2457913`.

#### Phase 4: Final Restart Wave (16:12 – 16:45)
Once commit `d86bcc3ac` was in place, the user methodically restarted or continued all affected work streams:
- `0sd--1` launched at 16:12:41 (succeeded).
- `sase-19i.2--1` launched at 16:12:50 (succeeded).
- `sase-19o.3--1` launched at 16:13:27 (succeeded).
- `sase-19p.2--1` launched at 16:15:32 (succeeded).
- Second-generation retries for the 15:57 failures:
  - `0se--2` launched at 16:27:24 (succeeded).
  - `0sf--2` launched at 16:32:13 (succeeded).
  - `sase-17m.9--2` launched at 16:39:28 (succeeded).
  - `sase-19p.2--2` launched at 16:44:13 (succeeded).
- Resumed dependent epic beads via CLI: `sbd work 18j 19i 19o 19p -Y` and `sbd work 17x.13.10 17d.12 -Y`.

---

## 3. TUI Failure Recovery UX: Gap Analysis

The recovery process exposed fundamental deficiencies in the TUI's user experience when handling multi-agent failures.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CURRENT TUI RECOVERY WORKFLOW                         │
└─────────────────────────────────────────────────────────────────────────────┘
  Incident Occurs (12+ Agents Fail)
         │
         ▼
  [Manual Hunt & Seek] ─────────► User must scan entire Agents table to find
                                  failed rows amidst active, waiting, and done rows.
         │
         ▼
  [Single-Row Navigation] ──────► Focus row 1  ──► Focus row 2  ──► ... ──► Focus row N
         │                             │                │                   │
         ▼                             ▼                ▼                   ▼
  [Manual Relaunch Loop] ───────► Press 'R'/'F'    Press 'R'/'F'       Press 'R'/'F'
                                       │                │                   │
                                  Edit/Enter       Edit/Enter          Edit/Enter
                                       │                │                   │
                                  Wait slot        Wait slot           Wait slot
         │
         ▼
  [Blind Dispatch Hazard] ──────► No pre-flight environment check exists.
                                  Premature launches fail again (e.g. 0se--1 -> 0se--2).
```

### Specific Friction Points

1. **Absence of Bulk Relaunch Primitives (`_marked_agents` Asymmetry)**:
   - SASE has a robust row-marking mechanism (`m` to mark/unmark, `*` to mark groups).
   - Marked agents support:
     - `s` $\to$ Save / Dismiss marked agents (`action_save_marked_agents`)
     - `k` / `,x` $\to$ Bulk Kill marked agents (`_bulk_kill_marked_agents`)
     - `w` $\to$ Bulk Wait for marked agents (`_bulk_wait_for_marked_agents`)
     - `y` $\to$ Bulk Revert commits (`_start_revert_marked_agents`)
   - **Critical Omission**: There is **no** `_bulk_retry_marked_agents` and **no** `_bulk_fork_marked_agents`. Pressing `R` or `F` while 10 agents are marked only acts on the single currently focused row, discarding or ignoring the mark set.

2. **No Incident Clustering or Failure Signature Grouping**:
   - In the TUI, failed agents are simply decorated with `FAILED` badges.
   - When 12 agents crash due to the *exact same* setup error (`validate_sase_core_rs`), they are rendered as isolated individual failures. The user cannot see that all 12 share a single root cause without opening each agent's detail panel or inspecting `live_reply.md`.

3. **Hazardous Blind Relaunching (No Pre-Flight Gating)**:
   - The TUI provides no feedback on system health before relaunching.
   - When the user retried `0se`, `0sf`, and `sase-17m.9` at 15:57, the TUI happily dispatched them despite the fact that `sase_core_rs` was completely out of sync with Python. A simple pre-flight check would have warned: *"System Environment Degraded: validate_sase_core_rs failing. Fix environment before relaunching."*

4. **Namespace and Suffix Bloat**:
   - Retries and forks create new names (`0se--1`, `0se--2`, `0se--mon-0`). Under repeated systemic failure, agent lineages become deeply nested and confusing to track.

5. **Terminology Disconnect**:
   - **Revive** (`w` via `AgentRevivalMixin`): Restores dismissed rows back into the Agents tab view; does *not* re-execute code.
   - **Retry** (`R` via `_retry_edit_agent`): Generates a new agent name (`allocate_retry_name`), populates prompt bar with raw prompt.
   - **Fork** (`F` via `action_fork_agent`): Populates prompt bar with `#fork:<target>` for versioned continuation.
   - **Restart** (CLI `sase agent restart`): In-place wipe and re-execution under the same name (not exposed cleanly on keypress in TUI).

---

## 4. UX Solution Space Exploration

We explore four distinct architectural solutions to address multi-agent recovery in the SASE TUI.

---

### Solution 1: Marked-Agents Bulk Operations (Bulk Retry & Bulk Fork)

#### Interaction Model
Leverage the user's existing muscle memory around marking (`m` to toggle mark, `M` or `*f` to mark all failed). When one or more agents are marked:
- Pressing **`R`** triggers `_bulk_retry_marked_agents()`
- Pressing **`F`** triggers `_bulk_fork_marked_agents()`

Instead of dumping raw prompts into the prompt input bar, the action opens a **Bulk Relaunch Modal**:

```
┌─────────────────────────── Bulk Agent Relaunch ───────────────────────────┐
│ Target Agents: 8 marked agents selected (6 FAILED, 2 STOPPED)             │
│                                                                           │
│ Mode:                                                                     │
│   (*) Fork Continuation (Recommended)   ( ) Fresh Relaunch (New Name)     │
│                                                                           │
│ Execution Settings:                                                       │
│   Queue Strategy: [ Staggered (2s delay) ▼ ]   Concurrency Limit: [ 4 ▼ ] │
│   Override Model: [ (keep original)       ▼ ]   Reasoning Effort: [ -- ▼ ] │
│                                                                           │
│ Selected Roster:                                                          │
│   [x] 0se--0             (codex / gpt-5.6-terra)   Exit: Setup Failure    │
│   [x] 0sf--0             (grok / grok-4.6)         Exit: Setup Failure    │
│   [x] sase-17m.9--mon    (grok / grok-4.6)         Exit: Setup Failure    │
│   [x] 0sd--0             (muse / spark-1.3)        Exit: Setup Failure    │
│   [x] sase-19i.2--plan   (codex / gpt-5.6-terra)   Exit: Setup Failure    │
│                                                                           │
│ [ Submit All (Enter) ]       [ Dry Run (Ctrl+D) ]       [ Cancel (Esc) ]  │
└───────────────────────────────────────────────────────────────────────────┘
```

#### Technical Evaluation
- **Pros**:
  - Seamlessly extends existing TUI marking infrastructure (`_marked_agents`).
  - High operator control: user can deselect specific agents in the modal.
  - Rate-limiting guardrails prevent overloading LLM providers or saturating runner capacity slots.
- **Cons**:
  - Still requires the operator to manually identify and mark the target agents.
  - Does not actively alert the user to the failure when it occurs.

---

### Solution 2: Incident Triage Banner & Recovery Wizard

#### Interaction Model
An intelligent background monitor tracks agent termination events. When a failure cluster is detected (e.g. $\ge 3$ agent failures within 10 minutes, or $\ge 2$ agents failing with identical system error signatures), a prominent, non-intrusive **Incident Recovery Banner** appears at the top of the Agents tab:

```
┌───────────────────────────────────────────────────────────────────────────┐
│ ⚠ INCIDENT DETECTED: 8 agents failed in the last 30m (Signature: Setup)   │
│   [R] Open Recovery Wizard      [D] Dismiss Incident Banner               │
└───────────────────────────────────────────────────────────────────────────┘
```

Pressing `R` (or clicking the banner) launches the **Incident Recovery Wizard**:

```
┌──────────────────────── Incident Recovery Wizard ────────────────────────┐
│ Incident ID: inc-260925-1541   Detected: 2026-09-25 15:41:43 (8 agents)   │
│ Primary Root Cause: Setup / Schema Mismatch (`validate_sase_core_rs`)     │
│                                                                           │
│ ── System Pre-Flight Diagnostics ──────────────────────────────────────── │
│   [✓] sase-core Git Revision Alignment: HEAD is 2457913                   │
│   [✓] sase_core_rs Validation Probe: Schema version 10 matches Python      │
│   [✓] Ephemeral Workspace Locks: Clean (no dangling index.lock detected)   │
│   [✓] LLM Provider Health: codex (OK), grok (OK), muse (OK)              │
│                                                                           │
│ ── Recovery Actions ───────────────────────────────────────────────────── │
│   [ Relaunch All Affected Agents ]   Creates continuation forks for 8     │
│                                      agents into runner slot queue.       │
│                                                                           │
│   [ Prune & Restart In-Place ]       Wipes failed run artifacts and       │
│                                      re-executes original prompts.        │
│                                                                           │
│   [ Export Diagnostic Bundle ]       Saves logs and environment details.  │
│                                                                           │
│                                                   [ Close Wizard (Esc) ]  │
└───────────────────────────────────────────────────────────────────────────┘
```

#### Pre-Flight Health Gate
The wizard executes live environment probes *before* enabling the "Relaunch" button:
1. `validate_sase_core_rs` execution check.
2. Scan for dangling `.git/index.lock` in active workspace directories.
3. Check for daemon/service host responsiveness.
If any check fails, the relaunch button is disabled with an actionable message:
> ⛔ *Relaunch Blocked: `validate_sase_core_rs` is failing with schema mismatch. Run `sase update` or apply core patches before restarting agents.*

#### Technical Evaluation
- **Pros**:
  - Eliminates the "Premature Relaunch Trap" that caused Bryan to waste cycles on `0se--1`, `0sf--1`, and `sase-17m.9--1`.
  - Zero hunt-and-seek: automatically aggregates all affected agents regardless of clan or scroll position.
  - Drastically lowers time-to-recovery (single keypress opens triage, single Enter relaunches).
- **Cons**:
  - Requires failure clustering logic and signature matching heuristics.

---

### Solution 3: Colon Command-Line Batch Recovery

#### Interaction Model
Power users who prefer keyboard-driven command execution can use SASE’s `:` command-line palette. We introduce the `:agent recover` family of commands:

```text
:agent recover --failed                      # Recovers all agents currently in FAILED state
:agent recover --since 45m                   # Recovers all agents failed in the last 45 minutes
:agent recover --signature "setup"           # Recovers agents matching the setup failure signature
:agent recover --marked                      # Recovers currently marked agents
:agent recover --dry-run                     # Previews the recovery roster without launching
```

#### Technical Evaluation
- **Pros**:
  - Fast, scriptable, and non-modal.
  - Easily invoked from any tab in ACE without changing view focus.
  - Familiar syntax consistent with `:sbd` and `:chop` commands.
- **Cons**:
  - Lower discoverability for visual users.
  - Does not provide rich interactive pre-flight feedback before dispatch.

---

### Solution 4: Clan/Deck Panel "Quarantine & Recovery" Card

#### Interaction Model
In SASE’s Deck Panel architecture, when focus rests on an agent that failed as part of a multi-agent cluster, the Context/Action deck dynamically injects a **Recovery Card Block**:

```
╭─ RECOVERY TRIAGE ─────────────────────────────────────────────────────────╮
│ Status: FAILED (System Outage Detected)                                  │
│ Sibling Failures: 5 other agents in clan 'sase-19i' failed at ~15:45     │
│ Diagnostic: Recipe `_setup` failed exit=1                                │
│                                                                           │
│ Quick Actions:                                                            │
│   [r] Restart This Agent Only                                             │
│   [R] Restart All 6 Failed Clan Schedulers                                │
│   [f] Fork Continuation on Last Clean Worktree                            │
╰───────────────────────────────────────────────────────────────────────────╯
```

#### Technical Evaluation
- **Pros**:
  - Contextual: appears right next to the agent details during normal inspection.
  - Scoped cleanly to the relevant clan or tribe.
- **Cons**:
  - Does not address cross-clan outages (e.g. `0se`, `sase-17m`, `0sd`, and `sase-19i` were in different clans/tribes).

---

## 5. Comparative Trade-Off Matrix

| Evaluation Criteria | Solution 1: Marked Bulk Ops | Solution 2: Incident Wizard | Solution 3: Colon Palette | Solution 4: Deck Card Block |
| :--- | :---: | :---: | :---: | :---: |
| **Speed to Recover (Keystrokes)** | Medium (Mark + R) | **Fastest (Banner R + Enter)**| Fast (Type command) | Medium (Navigate + R) |
| **Pre-Flight Safety Gating** | Optional Modal | **Built-in Diagnostic Gate** | Dry-run flag only | None |
| **Cross-Clan Outage Handling** | Excellent | **Excellent** | Excellent | Poor (Clan-scoped) |
| **UI Discoverability** | High (Keymap Hints) | **Highest (Toast/Banner)** | Low (Hidden behind `:`) | Medium |
| **Accidental Relaunch Prevention**| High (Modal Review) | **Highest (Hard Health Gate)**| Medium | High |
| **Throttled Queue Integration** | Native | **Native** | Native | Manual |
| **Implementation Complexity** | Low–Medium | Medium | Low | Low |

---

## 6. Recommended Architecture: The Incident-Aware Multi-Agent Recovery System

We recommend implementing a cohesive, three-tiered recovery framework:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 RECOMMENDED RECOVERY ARCHITECTURE (IMARA)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [ Tier 2: Incident Monitor & Pre-Flight Gate ] (Proactive Safety Layer)    │
│  • Detects failure clusters (>=3 failures in 15m or matching exit signature)│
│  • Displays top-level Incident Banner                                       │
│  • Runs Pre-Flight Diagnostics before allowing execution                    │
│                                                                             │
│  [ Tier 1: Marked-Agents Bulk Operations ] (Operator Precision Layer)       │
│  • Binds 'R' (Retry) and 'F' (Fork) when _marked_agents is active           │
│  • Opens Bulk Dispatch Modal with rate-limiting & model override            │
│                                                                             │
│  [ Tier 3: Command Palette Shortcuts ] (Power-User Fast Path)               │
│  • Exposes :agent recover --failed / --incident                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.1 Architectural Specification

#### 1. Failure Cluster Detector (`FailureClusterWatcher`)
A background service running inside `sase.ace.tui.app`:
- Hooks into `_on_agent_status_change` and `runs.jsonl` events.
- Maintains a sliding 20-minute ring buffer of terminal failure events.
- Evaluates clustering criteria:
  $$\text{Count}(\text{Failures}_{t - 20\text{m}}) \ge 3 \quad \text{OR} \quad \text{SignatureMatch}(\text{Failures}) \ge 2$$
- When triggered, posts an `IncidentDetectedEvent` to the TUI event bus.

#### 2. The Pre-Flight Diagnostic Engine (`RecoveryPreflightValidator`)
A lightweight, non-blocking check suite executed before any bulk relaunch:
- **Check 1: Core Wire Alignment**: Invokes `tools/validate_sase_core_rs` probe mode in memory. Verifies installed `sase_core_rs` matches Python expectations.
- **Check 2: Git Lock Health**: Inspects `.git/index.lock` across all active workspace paths registered in `~/.local/state/sase/workspaces/`.
- **Check 3: Service Host Responsiveness**: Pings `sase service` status.

#### 3. Marked Agents Action Expansion (`AgentMarkedRelaunchMixin`)
Add to `src/sase/ace/tui/actions/agents/_marking.py` and `_fork_actions.py`:
- Intercept `action_agents_retry` (`R`):
  ```python
  if getattr(self, "_marked_agents", None):
      self._show_bulk_retry_modal(self._marked_agents_in_mark_order())
      return
  self._retry_selected_agent()
  ```
- Intercept `action_fork_agent` (`F`):
  ```python
  if getattr(self, "_marked_agents", None):
      self._show_bulk_fork_modal(self._marked_agents_in_mark_order())
      return
  # single fork prompt input bar logic
  ```

#### 4. Throttled Runner Capacity Dispatch
Bulk relaunching 10+ agents simultaneously can trigger API rate limits (e.g. OpenAI/Anthropic/Grok 429s) or saturate local CPU cores during workspace initialization.
The recovery dispatcher submits jobs to the **Runner Slot Queue** (`%queue(weight=1)`) with a 1.5-second stagger interval:
```python
async def dispatch_recovery_batch(agents: list[Agent], mode: RecoveryMode):
    for idx, agent in enumerate(agents):
        await slot_queue.admit_staggered(agent, delay_seconds=idx * 1.5)
```

---

## 7. Implementation Roadmap & Next Steps

| Phase | Milestone | Deliverables |
| :--- | :--- | :--- |
| **Phase 1** | **Marked-Agent Bulk Primitives** | 1. Implement `_bulk_retry_marked_agents` and `_bulk_fork_marked_agents` in `src/sase/ace/tui/actions/agents/`.<br>2. Implement `BulkRelaunchModal` in `src/sase/ace/tui/modals/`.<br>3. Unit and TUI interaction tests in `tests/ace/tui/test_agent_bulk_relaunch.py`. |
| **Phase 2** | **Pre-Flight Health Validation** | 1. Create `sase.core.preflight` module implementing core schema, lock, and service checks.<br>2. Add pre-flight check execution to `BulkRelaunchModal` and CLI `sase agent restart`. |
| **Phase 3** | **Incident Banner & Wizard** | 1. Implement `FailureClusterWatcher` background monitor.<br>2. Build `IncidentRecoveryWizard` modal and notification toast integration.<br>3. Add `:agent recover` commands to the TUI command palette. |

---

## 8. Conclusion

The outage on 2026-09-25 was an acute demonstration of how cross-repository contract flips can trigger cascading multi-agent failures. While the user's forensic diagnosis and code fixes were swift and comprehensive, the physical recovery process in the TUI was severely throttled by manual, single-agent relaunch mechanics. Implementing the proposed **Incident-Aware Multi-Agent Recovery Architecture** will turn future catastrophic multi-agent failures into a 30-second, verified, single-click recovery event.
