# Remote Machine TUI Driver Architecture & Implementation Plan

**Author:** Researcher gem (`research.46.gem`)  
**Date:** October 2026  
**Scope:** Transforming a low-resource MacBook into the primary SASE TUI driver via remote dispatch, operation parity on the Agents tab, and resource-conscious synchronization.

---

## 1. Executive Summary

The user wishes to make a resource-constrained MacBook the primary driver of SASE's Textual TUI (`sase tui`) by completing the implementation for remote machine support. The stated requirements include:
1. Manually specifying remote execution via `%dispatch:<target>`, with an ergonomic shorthand `%d:<target>`.
2. Achieving reliable operation parity on the **Agents** tab for remote agents identical to local agents (lifecycle, inspection, decks, attention, terminal, and VCS actions).
3. Accommodating slow or purely manual synchronization (via a dedicated keymap for the selected remote machine) to prevent the MacBook from exhausting CPU, memory, and network resources.

### Core Architectural Findings

1. **The Resource Paradox of the "Local TUI Controller" Premise:**
   Running SASE's TUI locally on macOS is non-trivially resource-intensive. Textual's async Python runtime, Rich terminal cell layout, background file watchers (`watchdog`/FSEvents), local Git workspace scans, SQLite index updates, and the background Rust federation daemon (`sase_federation_worker`) already consume significant memory and CPU cycles. Ironically, running `sase tui` inside `tmux` directly on the powerful remote Linux devbox and connecting via an SSH terminal emulator (e.g., Ghostty or Alacritty) consumes orders of magnitude fewer resources on the MacBook (~20 MB RAM, 0.1% CPU, zero background polling, zero fan noise).
2. **The "Full Sync" Antipattern:**
   Attempting to synchronize "all agent data" (full conversation transcripts, raw tool run logs, intermediate scratch files, Git worktrees) to the MacBook directly contradicts the low-resource constraint. A single multi-turn agent can produce 10–50 MB of transcripts and tool outputs; a fleet of 20 agents would quickly saturate local disk and network bandwidth. Parity must be achieved through **on-demand bounded streaming** and **SSH transport handoffs**, *not* bulk replication.
3. **Current State of Remote Dispatch in SASE:**
   SASE already possesses a well-designed, asymmetric federation layer (`sase_gateway` in `sase-core`, `sase_federation_worker`, and `RemoteContentClient`). Remote rows already render in the Agents list, and basic remote stop (`x`), retry (`R`), fork (`F`), and attention/questions (`Enter`) already work over journaled HTTP endpoints. However, severe gaps remain:
   - `%d` is not recognized by the directive parser.
   - The Main Deck forces remote chat content into an isolated modal (`RemoteContentModal`) rather than native deck panels.
   - Files/Diff, Tools/Runs, and Metadata Pagers are explicitly gated off for remote rows.
   - Terminal handoff (`open_tmux` / `t`) is hardcoded to fail on remote rows.
   - Remote revive and complex interactive gate approvals are unimplemented.
   - Background federation polling cannot be completely disabled in favor of manual-only synchronization.

### Recommended Strategy
Adopt a **Hybrid On-Demand Architecture**:
- Implement `%d` as an immediate ergonomic shorthand.
- Expose an optional default target (`dispatch.default_target`) to avoid manual directive typing entirely.
- Transition deck rendering from modal popups to native, on-demand streaming via existing `/api/fleet/v1/content` handles.
- Route terminal and tmux operations through SSH transport handoffs (`ssh_target`).
- Provide an explicit `sync_selected_remote_machine` keymap and a `manual_sync_only` configuration flag to strictly cap resource utilization.

---

## 2. Critique of the Overall Plan

### 2.1 Is This a Good Idea?

The desire to use a lightweight laptop as a "glass pane" while delegating heavy compute (compilation, Docker containers, multi-agent LLM harnesses, test suites) to a powerful remote machine is an industry-standard workflow. However, the proposed mechanism—running the full SASE TUI controller locally while dispatching agents remotely and synchronizing all data—introduces architectural friction that must be honestly critiqued.

#### 1. The Resource Reality on macOS
Textual TUIs are not lightweight shell scripts. In SASE:
- **Python / Textual Runtime:** Maintains reactive DOM trees, CSS styling engines, Rich text segmentations, and high-frequency event loops.
- **Background Processes:** Supervises `sase_federation_worker` (a local Rust daemon communicating via Unix domain sockets), file system monitors (`FSEvents`), and periodic timers for model quotas, heap GC, and notifications.
- **Git Operations:** The SASE controller regularly checks local repository statuses, branches, and worktrees.
When running on an older or lower-spec MacBook (e.g., dual-core Intel or baseline 8 GB Apple Silicon), running the TUI locally can cause noticeable battery drain and memory pressure, even if the agent LLM calls themselves execute remotely.

#### 2. The Semantic Mismatch of "Full Synchronization"
SASE agents operate inside **ephemeral Git workspaces** (`sase_<N>`). An agent turn is deeply coupled to its local filesystem environment:
- It creates branches and commits.
- It executes tools via bash/python procs in scratch directories.
- It writes large `transcript.jsonl` and `transcript_full.jsonl` logs.
- It indexes files via Symvision AST analysis.

If "all data is able to be synced locally" means pulling the agent's full workspace, git trees, and logs onto the MacBook, the MacBook becomes a heavy mirror of the remote machine. This requires high network bandwidth, heavy disk write cycles, and local storage overhead—defeating the purpose of keeping the MacBook lightweight.

### 2.2 Would We Take a Different Approach?

Before committing engineering effort to building out complex remote virtualization protocols, the user should consider the two primary architectural alternatives.

```
+-------------------------------------------------------------------------------+
|                       ARCHITECTURAL APPROACHES                                |
+-------------------------------------------------------------------------------+

Approach A: Pure Remote TUI (The Thin Terminal)
[ MacBook: Ghostty / Alacritty ]  <=== SSH ===>  [ Remote Box: tmux + sase tui ]
  - MacBook CPU/RAM: ~0% / 20MB                     - 100% feature parity out of the box
  - Battery impact: Negligible                      - Zero sync latency; zero code changes

Approach B: The Refined Hybrid Controller (Recommended for Fleet / Multi-target)
[ MacBook: sase tui (Controller) ]  <== HTTP/SSH ==>  [ Remote Box: sase_gateway ]
  - Runs local TUI controller                       - Agents execute remotely in ephemeral workspaces
  - On-demand streaming (no bulk sync)              - SSH handoffs for tmux; RPC for lifecycle/attention
  - Manual sync toggle for low resources

Approach C: Naive Bidirectional Mirroring (The Anti-Pattern)
[ MacBook: Heavy Mirror ]  <=== Bulk File Sync ===>  [ Remote Box: Workspaces ]
  - Syncs gigabytes of transcripts/repos/logs       - Slashes battery; thrashes SSD
  - High risk of sync conflicts & network lag      - High maintenance overhead
```

#### Comparison Matrix

| Dimension | Approach A: Remote TUI (SSH + tmux) | Approach B: Refined Hybrid Controller | Approach C: Naive Mirroring |
| :--- | :--- | :--- | :--- |
| **MacBook Resource Use** | **Minimal** (Terminal only, ~20MB RAM, 0% CPU) | **Moderate** (~200MB RAM, 1–5% CPU) | **Severe** (High disk I/O, network churn) |
| **Parity with Local** | **100% Native** (Everything works out of the box) | **Near-100%** (Via streaming + RPC + SSH) | **Partial & Fragile** (Sync race conditions) |
| **Engineering Effort** | **Zero days** (Ready today) | **Moderate** (1–2 developer weeks) | **High** (Complex file synchronization) |
| **Multi-Machine Fleet** | Limited (Bound to that one machine) | **Excellent** (Can orchestrate N machines) | Poor (N-way sync overhead) |
| **Mac Notification / UI**| Terminal OSC notifications only | Native macOS notifications & clipboard | Native macOS notifications & clipboard |
| **Offline Viewing** | None | Bounded cached view of past turns | Local copy of past turns |

### 2.3 Verdict on Approach
- If the user's setup consists of **one primary remote development machine**, **Approach A (SSH + tmux)** is strictly superior in stability, performance, battery life, and zero implementation cost.
- However, if the user specifically desires the MacBook to act as a **Controller hub** (e.g., dispatching between local and remote, orchestrating multiple remote machines, or leveraging native macOS desktop integration), **Approach B (The Refined Hybrid Controller)** is architecturally sound—**provided that the requirements are adjusted to avoid full bulk disk synchronization.**

---

## 3. Review & Adjustments to Requirements

### Requirement 1: `%dispatch` Manual Specification & `%d` Shorthand
- **User Request:** Add `%d` as shorthand for `%dispatch`.
- **Critique:** Excellent and necessary ergonomic enhancement. Currently, typing `%dispatch:apollo` or using the `gD` picker is verbose.
- **Justified Adjustments:**
  1. **Add `%d` Shorthand:** Register `"d": "dispatch"` in `_DIRECTIVE_ALIASES` and support `%d:<alias>` and `%d(alias)` in directive scanning.
  2. **Add `dispatch.default_target` Configuration:** Allow configuring a default machine alias (e.g. `dispatch.default_target: apollo`) in `~/.config/sase/config.yml`. When set, normal launches from that machine automatically assume the remote target unless explicitly overridden with `%d:local`. This eliminates the need to type `%d` on every single prompt.

### Requirement 2: Reliable Operation Parity on the Agents Tab
- **User Request:** "Reliably perform EVERY agent operation that I can currently perform from the 'Agents' tab on local agents on remote agents as well."
- **Critique:** While the sentiment is understandable, taking this literally leads to architectural anti-patterns (such as attempting to run local git commands against remote workspace directories).
- **Justified Adjustments (The Operation Parity Taxonomy):**
  We must categorize all Agents tab operations into four concrete architectural tiers:

  | Operation Tier | Operations | Implementation Strategy |
  | :--- | :--- | :--- |
  | **Tier 1: Direct Fleet RPC** | Stop (`x`), Retry (`R`), Fork (`F`), Revive (`agents_revive`) | Handled via journaled HTTP mutations to `sase_gateway` (`/api/fleet/v1/mutate`). |
  | **Tier 2: Attention & HITL** | Answering questions (`Enter`), Approving plan gates | Handled via the notification inbox and `/api/fleet/v1/attention/resolve`. Complex plan edits pull a temporary buffer into `$EDITOR`. |
  | **Tier 3: On-Demand Streaming** | Main Deck (Chat/Transcript), Files Deck (Diff), Tools Deck (Runs), Metadata Pager | Fetch bounded content chunks on-demand via `RemoteContentClient` (`/api/fleet/v1/content`). Render inside native Textual decks without modals. |
  | **Tier 4: SSH Transport Handoff** | Terminal attach (`open_tmux` / `t`), Running interactive shell | Resolve `ssh_target` and spawn an interactive SSH session attached to the remote workspace/tmux window. |

### Requirement 3: Synchronization Strategy & Resource Conservation
- **User Request:** "Slow to sync locally, or exclusively manual via a new keymap that syncs the currently selected remote machine's data..."
- **Critique:** The user correctly identifies the risk of resource exhaustion from background polling.
- **Justified Adjustments:**
  1. **Strict Decoupling of Catalog vs. Payload Data:**
     - **Catalog Data (Metadata):** Agent name, session, status, model, cost, tokens, prompt text, and capability flags. This is lightweight JSON (tens of kilobytes) and can be polled periodically or refreshed manually.
     - **Payload Data (Heavy):** Full chat history, tool run logs, diffs, and artifact files. **Never eagerly sync payload data in the background.** Fetch payload data *strictly on-demand* when the user focuses on or expands a deck panel.
  2. **Configurable Sync Modes:**
     - `periodic` (default): Polling on tab switch / interval.
     - `manual`: Completely suspends background HTTP/federation polling.
  3. **Targeted Manual Sync Keymap:**
     - Add `sync_selected_remote_machine` (e.g., bound to `gs` or `Ctrl+S`), which triggers an explicit cache invalidation and re-fetch for only the currently selected machine or remote agent.

---

## 4. Current Codebase Architecture & Gap Analysis

To implement these requirements, we must examine what SASE already provides and identify the exact code gaps.

### 4.1 Existing Remote Dispatch Infrastructure

SASE already possesses a mature foundation for remote orchestration:
1. **Enrollment & Gateway:**
   - Targets run `sase_gateway` (Axum/Tokio Rust server in `sase-core`) supervised by the service host.
   - Controllers enroll targets using one-time bootstrap bundles (`sase machine init -B <bundle>`).
   - Private network connectivity is established over Tailscale HTTPS endpoints.
2. **Federation Worker Daemon:**
   - On the controller, `FederationWorkerSupervisor` manages `sase_federation_worker` (Rust entry point).
   - Python code talks to the supervisor via Unix domain socket IPC using `FederationFacade`.
   - The worker queries remote gateways and maintains an in-memory cache.
3. **Agents Tab Integration:**
   - `AgentFleetRefreshMixin` (`_fleet_refresh.py`) queries the facade and converts responses into `FleetRowsProjection`.
   - Remote agents appear as `Agent` models in the mixed agent list with host chips (e.g., `apollo`).
   - Grouping by machine (`o` -> "by machine") renders remote aliases under their own banners.
4. **Lifecycle & Attention Support:**
   - `AgentRemoteLifecycleMixin` (`_remote_lifecycle.py`) journals stop, retry, and fork operations via `submit_machine_agent_action`.
   - `AgentRemoteAttentionMixin` (`_remote_attention.py`) routes pending questions and gates into the notification inbox.
   - `RemoteContentClient` (`sase.dispatch.content`) validates digest-checked content chunks from `/api/fleet/v1/content`.

### 4.2 Comprehensive Gap Analysis

Despite the foundation, remote agents currently feel like "second-class citizens" in the TUI due to specific implementation barriers.

```
+---------------------------------------------------------------------------------------------------+
|                                  AGENTS TAB CAPABILITY GAP MATRIX                                 |
+---------------------------------------------------------------------------------------------------+
| Operation / Feature          | Local Agent Support      | Remote Agent Support    | Gap Severity  |
+------------------------------+--------------------------+-------------------------+---------------+
| Directive: %d shorthand      | N/A                      | Not parsed / rejected   | Low (Easy)    |
| Stop agent (x)               | Yes (SIGTERM / cancel)   | Yes (via Gateway RPC)   | None          |
| Retry agent (R)              | Yes (Rerun turn)         | Yes (via Gateway RPC)   | None          |
| Fork agent (F)               | Yes (Prefills prompt)    | Yes (Fork prompt bar)   | None          |
| Revive agent (agents_revive) | Yes (Rewinds workspace)  | Completely Disabled     | High          |
| Answer Question (Enter)      | Yes (Modal flow)         | Yes (Attention modal)   | None          |
| Approve Gate (Enter)         | Yes (Plan edit / verify) | Basic approve only      | Moderate      |
| Main Deck (Chat/Transcript)  | Native in-panel render   | Unbound modal popup     | High (UX)     |
| Files Deck (Diff/Changes)    | Native tree & diff view  | Disabled (returns None) | High          |
| Tools Deck (LLM Calls/Runs)  | Native cards & metrics   | Disabled (hardcoded off)| Moderate      |
| Metadata Pager (P / K)       | Full document pager      | Disabled (returns False)| Low           |
| Tmux Attach (open_tmux / t)  | Native local attach      | Disabled (returns False)| High          |
| Jump to Patch (J / Enter)    | Jumps to Patches tab     | Disabled (returns False)| Moderate      |
| Tags / Tribe / Unread        | Modifies local metadata  | Disabled (returns False)| Low           |
| Sync Control                 | Automatic + 'r' refresh  | Polled with local apply | Moderate      |
+---------------------------------------------------------------------------------------------------+
```

#### Detailed Examination of Gaps

1. **Directive Parsing (`src/sase/macro/_directive_types.py` & `_directive_scan.py`):**
   - In `_directive_types.py`, `_DIRECTIVE_ALIASES` maps short letters to directives (`a -> auto`, `m -> model`, `w -> wait`). `"d"` is currently absent.
   - In `_directive_scan.py:94`, `scan_dispatch_directive` fast-paths:
     ```python
     if "%dispatch" not in prompt:
         return None
     ```
     This causes `%d:target` to be completely ignored unless `%dispatch` is literally present.
2. **Main Deck Isolation (`src/sase/ace/tui/actions/agents/_panel_detail.py`):**
   - For local agents, selecting an agent immediately streams the prompt and response into `DeckId.MAIN`.
   - For remote agents, lines 70–72 redirect `edit_spec` (`_open_agent_chat`) to `action_view_remote_agent_content()`, which pops up a modal window (`RemoteContentModal`) rather than rendering into the deck. If the user navigates rows with `j`/`k`, the main deck remains empty.
3. **Files & Tools Deck Gating (`src/sase/ace/tui/widgets/decks/availability.py`):**
   - `probe_files_deck(agent)` line 48:
     ```python
     if agent.workspace_num is not None and not agent.fleet_origin_alias:
         return DeckAvailability(None, None)
     return DeckAvailability(False, 0)
     ```
     Remote agents (`agent.fleet_origin_alias` is set) evaluate to `DeckAvailability(False, 0)`, completely suppressing the Files deck.
   - `probe_tools_deck(agent)` line 59:
     ```python
     # Pinned attempts, clans, tribes, and remote rows stay without Runs.
     ```
     Tool runs are hardcoded off for remote rows.
4. **Action Availability Guardrails (`src/sase/ace/tui/_app_action_availability_agents.py`):**
   - Lines 277–291 block almost all standard row actions on remote agents:
     ```python
     if selected_agent_remote and action in _LOCAL_AGENT_ROW_ACTIONS:
         return False
     ```
     This single check disables `open_tmux`, `start_tmux_mode`, `jump_to_agent_patch`, `view_agent_metadata`, `rename_cl`, `add_tag`, `edit_agent_tribe`, and `toggle_agent_unread`.
5. **Terminal / Tmux Handoff (`src/sase/ace/tui/actions/agents/_panel_tmux.py`):**
   - `_open_agent_tmux_window` assumes the agent has a local workspace directory (`workspace_num`). For a remote agent, this directory does not exist on the MacBook.
   - However, `sase` already has `RemoteSshTarget` and `resolve_remote_ssh_target(machine)` in `src/sase/dispatch/ssh_target.py` (populated via `sase machine add -S/--ssh-target`), but it is not connected to `open_tmux`.
6. **Remote Revive Flow:**
   - Reviving rewinds an agent to a previous commit and relaunches it. Currently, `_revive_execution.py` performs local git resets and branch checks. Remote execution requires a new mutation endpoint on `sase_gateway`.

---

## 5. Detailed Technical Design & Implementation Plan

To fulfill the user's requirements cleanly while preserving stability and performance, the implementation should be organized into five targeted components.

```
+------------------------------------------------------------------------------------------+
|                               IMPLEMENTATION ARCHITECTURE                                |
+------------------------------------------------------------------------------------------+

1. Directives & Launch
   Prompt Input  --->  [_directive_scan.py]  --->  Recognizes %d:<alias> & %dispatch:<alias>
                       (Resolves default target from config if omitted)

2. Native Deck Presentation (On-Demand Streaming)
   AgentDetail   --->  DeckArea (MAIN / FILES)
                            |
                            v
                       RemoteContentClient (Digest-validated chunk streaming)
                            |
                            v
                       sase_gateway [/api/fleet/v1/content] (Fetch on-demand; zero bulk sync)

3. Terminal Handoff
   Keypress 't'  --->  resolve_remote_ssh_target(machine)  --->  Terminal window:
                                                                 ssh -t <target> "tmux attach ..."

4. Remote Mutations
   Revive / Gate --->  sase machine agent mutate  --->  sase_gateway [/api/fleet/v1/mutate]

5. Throttled Sync Control
   Keypress 'gs' --->  _schedule_agents_fleet_refresh(target_machine=selected, force=True)
   Config: dispatch.federation.manual_sync_only: true (Suspends background polling)
+------------------------------------------------------------------------------------------+
```

### 5.1 Component 1: `%d` Shorthand and Launch Target Ergonomics

#### Changes in `src/sase/macro/_directive_types.py`
Add `"d"` to `_DIRECTIVE_ALIASES`:
```python
_DIRECTIVE_ALIASES: dict[str, str] = {
    "a": "auto",
    "c": "clan",
    "d": "dispatch",  # <-- Added shorthand
    "e": "effort",
    "h": "hide",
    "i": "id",
    "m": "model",
    "n": "name",
    "q": "queue",
    "r": "repeat",
    "t": "tribe",
    "w": "wait",
}
```

#### Changes in `src/sase/macro/_directive_scan.py`
Update `scan_dispatch_directive` to ensure the fast-path check does not discard `%d`:
```python
def scan_dispatch_directive(prompt: str) -> DispatchDirectiveScan | None:
    # Check for both canonical %dispatch and shorthand %d
    if "%dispatch" not in prompt and not re.search(r"(?:^|\s)%(?:d[:(]|d\b)", prompt):
        return None
    # Remainder of regex parsing canonicalizes %d to %dispatch via _DIRECTIVE_ALIASES
```

#### Supporting Default Target Configuration
In `src/sase/dispatch/launch_preview.py`, when resolving the target:
```python
if target is None:
    config = load_dispatch_config()
    default_target = config.default_target  # e.g., configured in config.yml
    if default_target and default_target in config.machines:
        target = default_target
```
This allows the user to simply run `sase run "prompt"` on their MacBook and have it automatically dispatch to their Linux box without even typing `%d`.

---

### 5.2 Component 2: Native Deck Presentation (Eliminating the Modal)

Instead of popping up `RemoteContentModal`, remote chat, transcript, and diff content should stream directly into SASE's deck panels.

#### 1. Main Deck (`DeckId.MAIN`) Integration
- When a remote agent is selected, `AgentDetail` should read the content handle advertised in `agent.fleet_content`.
- The Main Deck document loader should invoke `RemoteContentClient.open_handle()` asynchronously via a background task.
- Chunks are decoded and appended to the `MainDeckDocument` as Markdown/Rich text.
- If the agent is currently running (`agent.status in ACTIVE_STATUSES`), arm a lightweight growth poll via `RemoteContentClient.continue_tail()`.

#### 2. Files / Diff Deck (`DeckId.FILES`) Integration
- Remote agents running in SASE produce git diff content handles. The gateway already publishes these under `content_handles` with `kind: "diff"`.
- Update `probe_files_deck()` in `src/sase/ace/tui/widgets/decks/availability.py`:
  ```python
  if agent.fleet_origin_alias:
      content = getattr(agent, "fleet_content", {})
      handles = content.get("content_handles") or content.get("handles") or []
      has_diff = any(h.get("kind") in ("diff", "patch", "files") for h in handles)
      return DeckAvailability(has_diff, len(handles) if has_diff else 0)
  ```
- Update `load_deck_file_view()` in `_agent_detail_files.py` to fetch the diff handle over `RemoteContentClient` and render the syntax-highlighted diff directly into `FileView`.

#### 3. In-Memory Chunk LRU Cache
To guarantee low memory usage on the MacBook, `RemoteContentClient` should bound its internal cache with an LRU policy (maximum 50 chunks or 30 MB). Evicted chunks can be re-fetched on demand over the tailnet if the user scrolls back.

---

### 5.3 Component 3: SSH Terminal & Tmux Handoff

One of the most essential operations on local agents is pressing `t` (`action_start_tmux_mode`) or `action_open_tmux` to jump into the agent's workspace.

#### Implementation in `src/sase/ace/tui/actions/agents/_panel_tmux.py`
1. Inspect the selected agent:
   ```python
   alias = getattr(agent, "fleet_origin_alias", None)
   if alias:
       self._open_remote_agent_tmux_window(agent, alias)
       return
   ```
2. Resolve the SSH target using `sase.dispatch.ssh_target.resolve_remote_ssh_target(alias)`.
3. Construct the remote tmux session/window command:
   ```python
   # The remote exact locator or session name identifies the tmux session
   session_name = agent.exact_key or agent.agent_session_name or "sase"
   ssh_target = resolve_remote_ssh_target(alias).host
   cmd = [
       "ssh", "-t", ssh_target,
       f"tmux attach -t '{session_name}' 2>/dev/null || tmux new-session -s '{session_name}'"
   ]
   ```
4. Spawn this in the user's configured terminal launcher (or a new tmux window locally that executes the ssh command).
5. Update `_app_action_availability_agents.py` to return `True` for `open_tmux` and `start_tmux_mode` on remote agents when an SSH target is configured.

---

### 5.4 Component 4: Remote Revive & Interactive Gates

#### 1. Remote Revive Mutation
- In `sase-core` (`crates/sase_gateway/src/fleet_mutations.rs`), extend `FleetMutationKindWire` to include `Revive`.
- The gateway handler resolves the agent turn, verifies its workspace status, rewinds the Git head, and re-invokes the SASE runner.
- On the controller TUI, update `_revive.py` / `_remote_lifecycle.py`:
  When `action_agents_revive` is triggered on a remote agent, invoke `_submit_remote_lifecycle([agent], kind="revive")`.

#### 2. Interactive Plan Gates
- Currently, remote gates support boolean approve/deny.
- For plan review gates where the user wants to edit the plan in `$EDITOR`:
  1. Fetch the plan file via `RemoteContentClient`.
  2. Write to a local temporary buffer (`/tmp/sase_plan_<id>.md`).
  3. Open `$EDITOR` locally on the MacBook.
  4. On editor save and exit, submit the updated plan text in the attention resolve payload:
     `POST /api/fleet/v1/attention/resolve { "request_id": id, "action": "approve_with_plan", "edited_plan": text }`.

---

### 5.5 Component 5: Throttled Sync Architecture & Manual Sync Keymap

To ensure the MacBook never runs hot or drains battery due to background fleet requests:

#### 1. Configuration Setting: `manual_sync_only`
In `~/.config/sase/config.yml` (under `dispatch.federation`):
```yaml
dispatch:
  federation:
    sync_mode: manual  # Options: periodic (default), manual
    request_timeout_seconds: 5.0
```

#### 2. Respecting `sync_mode` in `_fleet_refresh.py`
In `_schedule_agents_fleet_refresh()`:
```python
if config.sync_mode == "manual" and not force:
    # Ignore automatic tab_switch, file watcher applies, or timers.
    # Only run when explicitly triggered by the user (force=True).
    return
```

#### 3. Dedicated Keymap Action: `sync_selected_machine`
- Define action `action_sync_selected_remote_machine()` in `_fleet_refresh.py`.
- Register in `src/sase/ace/tui/keymaps/app_keymaps.py` and `src/sase/default_config.yml` (e.g. bound to `gs` or `Ctrl+S`).
- When pressed:
  1. Determine the machine alias under the cursor (or from the active filter).
  2. If none selected, sync all enrolled machines.
  3. Invoke `_schedule_agents_fleet_refresh(source="manual_keymap", force=True)`.
  4. Display a brief toast: `"Syncing apollo fleet data..."`.

---

## 6. Phased Implementation Roadmap

```
+---------------------------------------------------------------------------------------------------+
|                                     RECOMMENDED ROADMAP                                           |
+---------------------------------------------------------------------------------------------------+

PHASE 1: Launch Ergonomics (Quick Wins)
  - Add %d shorthand in _directive_types.py and _directive_scan.py.
  - Add prompt completions and syntax highlighting for %d.
  - Implement dispatch.default_target in config.yml.
  - Timeline: 1-2 days.

PHASE 2: Native Deck Presentation & Streaming
  - Connect RemoteContentClient to DeckId.MAIN (embed chat directly in panel).
  - Connect RemoteContentClient to DeckId.FILES (stream remote git diffs).
  - Remove modal popup barrier; enable metadata pager for remote rows.
  - Implement bounded LRU memory cache for content chunks.
  - Timeline: 3-5 days.

PHASE 3: Terminal & Workspace Operations
  - Connect open_tmux ('t') to SSH transport handoff via resolve_remote_ssh_target.
  - Enable Jump-to-Patch for upstream published branches.
  - Unlock tagging and unread tracking in local follow_store.
  - Timeline: 2-3 days.

PHASE 4: Mutations, Interactive Gates & Manual Sync Control
  - Add dispatch.federation.sync_mode: manual setting.
  - Add sync_selected_remote_machine keymap action (gs / Ctrl+S).
  - Add remote revive mutation in sase_gateway and TUI lifecycle bridge.
  - Implement round-trip plan buffer editing for remote gates.
  - Timeline: 4-6 days.
+---------------------------------------------------------------------------------------------------+
```

---

## 7. Recommended Solution & Final Guidance

### 7.1 Immediate Advice for Today
If your immediate goal is to work from your MacBook today without suffering resource constraints, **do not wait for full remote controller virtualization**:
1. Open your terminal on your MacBook (Ghostty / Alacritty / iTerm2).
2. SSH into your powerful machine inside `tmux`:
   ```bash
   ssh -t my-devbox "tmux new-session -A -s sase-work"
   ```
3. Run `sase tui` inside that remote tmux session.
4. **Outcome:** You get 100% operation parity immediately, native speed, zero battery drain on your Mac, and full persistence across laptop lid closes.

### 7.2 The Strategic Development Path
If you want to build this feature so that your MacBook acts as a genuine multi-machine orchestrator:
1. **Accept the Refined Architecture:** Abandon the idea of bulk-syncing "all agent data" to the MacBook. Adopt **on-demand streaming** for decks and **SSH handoffs** for terminal sessions.
2. **Execute Phase 1 Immediately:** Adding `%d` and `dispatch.default_target` takes less than 50 lines of code and provides immediate quality-of-life benefits.
3. **Execute Phase 2 (Native Decks):** Bring remote content out of the isolated modal and into the native Main and Files deck panels.
4. **Implement the Manual Sync Keymap:** Add the `sync_mode: manual` setting and `gs` keymap so that your MacBook only touches the network when you explicitly ask it to.

This hybrid approach respects the physical limits of your MacBook while unlocking the full, elegant power of SASE's distributed architecture.
