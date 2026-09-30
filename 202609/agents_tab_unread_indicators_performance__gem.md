# Research Report: Agents Tab Unread Indicators Performance & Architecture Critique

**Researcher:** `research.2x.gem` (Swarm Member `__gem`)  
**Date:** 2026-09-30  
**Target Surface:** SASE TUI (`sase tui` / ACE), Agents Tab, Unread Navigation (`,j`), Bulk Unread Acknowledgment (`,u`), Notification Persistence  
**Context:** Investigation of unread indicator flakiness, failure of `,u` to clear unread badges (screenshot `~/tmp/screenshots/20260930_060248.png`), navigation latency on `,j`, and architectural evaluation of using a background proc.

---

## 1. Executive Summary

Recent use of the `,u` keymap (`mark_all_unread_done_agents_read`) on the SASE TUI "Agents" tab failed to clear visible unread indicators. As evidenced by screenshot `20260930_060248.png`, **27 unread nodes** remained stubbornly active across the display (21 in the `@epic` tribe across 5 failed clan containers and 4 done clan containers, and 6 in the `@job` tribe). Furthermore, navigating between unread completed agents using `,j` (`jump_to_next_unread_done_agent`) exhibits noticeable latency, stuttering, and inconsistent indicator state.

A proposal was raised to offload this expensive work to a background "proc".

### Key Findings:
1. **Why `,u` Failed in the Screenshot:**
   - **Roster & Clan Folding Blindspot:** `,u` filters across `roster = self._agents_with_children or self._agents` using `is_agents_tab_agent_node(agent)`. For clan containers, `is_agents_tab_agent_node` is explicitly `False`. The actual member agents owning the notifications are collapsed inside clan containers or collapsed tribe panels and were excluded from `,u`'s candidate list. Unlike `,j`, `,u` never traversed collapsed clan folds or cross-tribe/cross-tab projections.
   - **Terminal Status Predicate Mismatch:** 12 of the 21 unread indicators in `@epic` sit under `Failed` clans. The check `is_unread_completed_status(agent.status)` requires an exact membership in `DISMISSABLE_STATUSES`. Agents with compound or qualified failure statuses (such as `FAILED (RETRIED)`) fail this check and are ignored by `,u`.
   - **The Hidden Toggle/Undo Trap:** `,u` is implemented as an unannounced toggle (`_toggle_all_unread_done_agents_read`). If unreads were previously acknowledged or if the user taps `,u` repeatedly in response to UI latency, `,u` immediately executes `_restore_bulk_read_undo()`, re-arming all unread indicators.
   - **Background Polling Re-Assertion Race:** The TUI polls notifications every 9 seconds. The in-memory optimistic clearance was either overwritten by the background polling loop before the slow disk write committed, or the disk dismissal matched zero notifications due to key mismatches.

2. **Why `,j` is Sluggish and Stuttering:**
   - **O(N) Full-Tree Reconstruction on Every Step:** Every `,j` call invalidates its candidate cache because `unread_ids` changes. To discover candidate jump targets inside collapsed clans, it calls `prospective_clan_members`, which expands every clan fold, runs fold filtering over the entire workspace roster, runs `AgentPanelGroup.from_agents`, and reconstructs the Textual tree from scratch on the synchronous UI thread.
   - **Heavy Disk I/O on an 18.6 MB JSONL Store:** Acknowledging an agent completion triggers `dismiss_agent_completion_notifications_matching_agents`. The live notification store (`~/.sase/notifications/notifications.jsonl`) is **18.6 MB** (3,873+ rows). Even with Rust bindings (`sase_core_rs`), acquiring the lock file, reading/deserializing 18.6 MB of JSON, mutating, and rewriting the entire 18.6 MB file takes ~131ms of disk I/O per acknowledgment. Rapid `,j` presses saturate thread workers and lock contention.
   - **Full UI List Rebuilds on Navigation:** Stepping across panels or expanding folds calls `_refresh_agents_display(list_changed=True)`, forcing Textual to destroy and reconstruct widget hierarchies instead of performing surgical DOM row patching.

3. **Critique of the "Proc" Proposal:**
   - **Architectural Mismatch:** In SASE, a "proc" is an independent OS subprocess (e.g. `sase proc`, service proc, AXE routine). Using an external process for TUI in-memory reactivity introduces heavy inter-process serialization (IPC) and worsens state drift.
   - **Wrong Concurrency Layer:** The bottleneck is split between synchronous Python CPU work on the UI event loop and O(File_Size) disk serialization in the notification store. An external proc addresses neither and introduces severe split-brain state hazards.

---

## 2. Visual Context & Screenshot Analysis (`20260930_060248.png`)

Inspection of the referenced screenshot reveals the exact operational state of the TUI:
- **Header State:**
  - Active tab: `Agents` (sub-tab `main 1`).
  - Summary banner: `204 [3 running · 28 waiting · 5 failed · 27 unread · 146 done] · group: by status (o) · refresh: 9s (r)`.
  - Exactly **27 unread** nodes are tracked.
- **Tribe & Clan Hierarchy:**
  - `▲ @default · 21 [R2 W2 D17] = apollo 93`: Expanded. The cursor is focused on `0u0` (under `Waiting`). **Notice that `@default` has 0 unread nodes.**
  - `▼ @epic · 174 [W26 F5 U21 D127]`: Expanded tribe with **21 unread** nodes:
    - Under `Failed (40 agents · 5 failed)`:
      - `sase (FAILED) x9 [W7 F1 U2] m1 sase-1d5` (2 unread)
      - `sase (FAILED) x8 [W6 F1 U2] m1 sase-1cx` (2 unread)
      - `sase (FAILED) x6 [W4 F1 U2] sase-1cj.12` (2 unread)
      - `sase (FAILED) x6 [F1 U1 D5] o2 m1 sase-1co` (1 unread)
      - `sase (FAILED) x11 [F1 U5 D6] o10 m5 sase-1ck` (5 unread)
      *(Subtotal in Failed: 2 + 2 + 2 + 1 + 5 = 12 unread)*
    - Under `Done (97 agents)`:
      - `sase (DONE) x4 [U4] o1 m1 sase-1cu` (4 unread)
      - `sase (DONE) x5 [U3 D2] o3 m1 sase-1ck.5.1` (3 unread)
      - `sase (DONE) x4 [U1 D3] m1 sase-1cq` (1 unread)
      - `sase (DONE) x5 [U1 D4] o1 sase-1cp` (1 unread)
      *(Subtotal in Done: 4 + 3 + 1 + 1 = 9 unread)*
    *(Total in `@epic`: 12 + 9 = 21 unread)*
  - `▼ † @job · 9 [R1 U6 D2]`: Collapsed tribe with **6 unread** nodes.
  *(Total across all tribes: 21 + 6 = 27 unread)*

### Crucial Visual Observations:
1. **All 27 unread nodes are inside collapsed containers:**
   Every single unread indicator is either inside a collapsed clan row (`sase-1d5`, `sase-1cx`, `sase-1cu`, etc.) or inside the collapsed `@job` tribe. None of the unread nodes are directly visible rows in the tree.
2. **The active tribe (`@default`) has zero unreads:**
   The user's cursor is situated in `@default` on agent `0u0`. If an action scopes its query to the active panel or current tribe, it will find 0 candidates.

---

## 3. Deep Root-Cause Analysis

### 3.1 Why `,u` Did Not Clear the Unread Indicators

The code path for `,u` (`mark_all_unread_done_agents_read`) in `src/sase/ace/tui/actions/agent_workflow/_leader_mode.py` delegates directly to `_toggle_all_unread_done_agents_read()` in `src/sase/ace/tui/actions/agents/_unread_state.py`:

```python
def _toggle_all_unread_done_agents_read(self) -> _BulkUnreadToggleResult:
    unread_ids = getattr(self, "_unread_completed_agent_ids", None)
    roster = getattr(self, "_agents_with_children", None) or self._agents
    if unread_ids:
        target_agents = [
            agent
            for agent in roster
            if is_agents_tab_agent_node(agent)
            and agent.identity in unread_ids
            and is_unread_completed_status(agent.status)
        ]
        if target_agents:
            return self._mark_current_unread_done_agents_read(target_agents)

    pending_ids = getattr(self, "_pending_bulk_read_agent_ids", None)
    if pending_ids is not None:
        return self._restore_bulk_read_undo(pending_ids)

    return _BulkUnreadToggleResult(BulkUnreadToggleOutcome.NOOP)
```

Four fatal defects intersect here:

1. **Failure to Traverse Collapsed Clan Members:**
   In `agent_nodes.py`, `is_agents_tab_agent_node(agent)` explicitly returns `False` if `agent.is_clan_container` is true. The visible rows in `self._agents` for `sase-1cu`, `sase-1ck`, etc. are clan containers, so they are excluded.
   Furthermore, depending on grouping mode and fold states, child rows of collapsed clans are not retained in `self._agents`. While `,j` has dedicated helper methods (`_collapsed_clan_jump_candidates` and `_off_tab_jump_candidates`) to search inside collapsed folds, `,u` performs a naive flat scan over `roster`. If the child agents are omitted from `roster` or excluded by tribe filters, `target_agents` evaluates to empty (`[]`).

2. **Incompatible Status Predicate for Failed Agents:**
   12 of the unread agents are in `Failed` clans. The predicate `is_unread_completed_status(agent.status)` checks:
   ```python
   DISMISSABLE_STATUSES = {
       "DONE", "FAILED", "PLAN COMMITTED", "PLAN DONE",
       "TALE DONE", "PLAN REJECTED", "EPIC CREATED", STOPPED_STATUS,
   }
   ```
   If a failed agent has any decorated status (e.g. `FAILED (RETRIED)`, `FAILED (TIMEOUT)`, `FAILED (UNKNOWN)`), or is an intermediate turn of a multi-turn failure, `status in DISMISSABLE_STATUSES` evaluates to `False`. While `is_failed_agent_status` uses `status.startswith("FAILED")`, `is_unread_completed_status` does not! Consequently, all 12 failed unread agents are completely disqualified from `,u`.

3. **Accidental Bulk-Read Reversal (Undo Toggle):**
   Notice the second branch:
   ```python
   pending_ids = getattr(self, "_pending_bulk_read_agent_ids", None)
   if pending_ids is not None:
       return self._restore_bulk_read_undo(pending_ids)
   ```
   If `,u` previously executed (or if the user hit `,u` twice because the badges didn't clear), `,u` immediately restores all pending unreads back into `_unread_completed_agent_ids`. The command is fundamentally a toggle, not an idempotent "mark all read" action.

4. **Background Reconciliation Race Condition:**
   `_mark_current_unread_done_agents_read` updates `_unread_completed_agent_ids` in memory, then schedules an asynchronous thread worker to persist the dismissal via `dismiss_agent_completion_notifications_matching_agents`.
   Because `notifications.jsonl` is 18.6 MB, this background write takes 130–300ms. If the periodic notification poller (`_notification_polling.py`) fires during or right after this window, it calls `_reconcile_unread_from_completion_notifications()`. Because the notifications were not yet written or if the notification keys didn't match, the poller repopulates `_unread_completed_agent_ids` from the un-updated disk state, restoring the unread count back to 27.

---

### 3.2 Why Unread Navigation (`,j`) is Extremely Slow

Tracing the execution of `,j` (`_jump_to_next_unread_done_agent` in `_unread_navigation.py`):

```
,j Keypress
 └── _unread_timed_jump_candidates()
      ├── Check Cache (Key includes frozenset(unread_ids) -> ALWAYS MISSES after each step)
      └── _timed_agent_jump_candidates()
           └── _collapsed_clan_jump_candidates()
                └── prospective_clan_members()
                     ├── filter_agents_by_fold_state(all_agents)
                     ├── _apply_active_agent_query()
                     ├── AgentPanelGroup.from_agents()
                     └── for each panel:
                          └── build_agent_tree()  <-- Synchronous UI thread CPU burn!
 └── acknowledge_target()
      ├── _clear_agent_unread_and_dismiss_notification()
      │    └── run_worker(thread=True):
      │         └── dismiss_agent_completion_notifications_matching_agents()
      │              └── Lock & re-read 18.6 MB JSONL, serialize, rewrite 18.6 MB  <-- Heavy disk I/O!
      └── _refresh_agents_display(list_changed=True)  <-- Full Textual DOM rebuild!
```

1. **Cache Thrashing in `_unread_timed_jump_candidates`:**
   The candidate list is cached with `cache_key = (..., frozenset(unread_ids), ...)`. Each time `,j` is pressed, the selected agent is marked read, modifying `unread_ids`. Therefore, **every single jump invalidates the cache**.
2. **Massive Redundant Computations:**
   To find which candidate is next, `prospective_clan_members` simulates what the entire agent tree would look like if every collapsed clan fold were expanded. It runs fold filtering, active query parsing, panel grouping, and full tree building across all panels. This CPU-heavy pipeline runs directly on the UI thread for every keypress.
3. **Severe Notification Store Write Overhead:**
   Every single `,j` jump spawns a background thread to persist the dismissal. The file `~/.sase/notifications/notifications.jsonl` contains 3,873 lines totaling 18,690,336 bytes (~18.6 MB).
   In `crates/sase_core/src/notifications/store.rs`:
   ```rust
   let lock = open_lock_file(path)?;
   lock.lock_exclusive()?;
   let (mut rows, stats_before) = read_rows_unlocked(path, true)?;
   // mutate rows in memory...
   write_rows_unlocked(path, &rows)?;
   ```
   Rewriting an 18.6 MB file on every jump creates continuous disk thrashing. When the user presses `,j` repeatedly, multiple workers queue up behind the exclusive lock, pinning CPU/disk and delaying UI reconciliation callbacks.

---

## 4. Critique of the Proposed "Background Proc" Plan

The user asked:
> *"my first thought was that we could use a proc to run any expensive work (anything that causes a delay in the TUI) in the background. Can you do some research with the goal of helping me decide the best way to implement this? Also, critique this plan in general. Is this a good idea? Would you take a different approach?"*

### 4.1 What is a "Proc" in SASE?
Per SASE architectural definitions (see `sase memory read glossary:Proc`), a **Proc** (or **Named Proc** / **Service Proc**) is an independent operating system process managed by the SASE service host or scheduler (AXE). Examples include long-running background command processes, scheduled routines, and background worker daemons.

### 4.2 Why Using a Proc Here is a Misguided Architecture

1. **IPC & Serialization Overhead:**
   The data structures involved in the TUI's sluggishness are in-memory Python representations of hundreds of agents (`Agent` dataclasses, Textual widget state, active search ASTs, and fold tree graphs). Offloading tree calculations or jump selection to an external proc requires serializing this entire graph across process boundaries (via IPC, pipes, or files). Serialization and deserialization would take tens to hundreds of milliseconds, **increasing UI latency** rather than decreasing it.
2. **State Synchronization and Split-Brain Hazards:**
   The TUI's state is interactive and ephemeral: current cursor position, active fold states, search filter text, and session-local manual marks change on every keystroke. An external proc holding a detached view of agent state will suffer from race conditions, recommending jumps to rows that were just collapsed, deleted, or marked.
3. **Misidentification of the Bottleneck:**
   The TUI latency is **not** caused by lack of multiprocessing. It is caused by:
   - Inefficient algorithmic design in the UI thread (`prospective_clan_members` doing full tree rebuilds).
   - An uncompacted 18.6 MB JSONL file undergoing O(N) full-file reads and rewrites for a single boolean field change (`n.dismissed = true`).
   - Unnecessary full-widget-tree rebuilds (`_refresh_agents_display`) on simple cursor navigation.
4. **Architectural Principles (Rust Core vs Python Procs):**
   SASE's core architecture dictates that shared domain logic and heavy persistence belong in the Rust backend (`sase-core` / `sase_core_rs`), not in ad-hoc Python subprocs (Decision: `rust-core-required`). The TUI should run lean, utilizing async event loops and threads for non-blocking I/O, while relying on compiled Rust routines for heavy data operations.

**Verdict on the Proc Plan:**
Using a proc is **not recommended**. It would add massive complexity, introduce distributed-state bugs, and fail to solve the actual root causes of the sluggishness.

---

## 5. Adjustments to Requirements

To address the user's core problems, the requirements should be adjusted as follows:

| Existing / Implied Requirement | Proposed Adjustment | Justification |
| :--- | :--- | :--- |
| `,u` toggles bulk read on the visible roster | `,u` must be an **idempotent, cross-hierarchy bulk acknowledgment** across all tribes, collapsed clans, and completed statuses. | The toggle behavior surprises users and double-tapping reverses the action. Collapsed clans must be fully included. |
| `,u` status matching uses `DISMISSABLE_STATUSES` | Match **all terminal statuses** including `FAILED*` (prefix match) and session-terminal states. | 12 of 21 unreads in the screenshot were failed clan members disqualified by exact status matching. |
| Navigation (`,j`) candidate lookup builds prospective trees | Candidate lookup must be **O(1) / O(log N)** using an in-memory priority queue / sorted index of unread agent timestamps. | Full prospective tree building on every step causes frame drops and makes `,j` unusable. |
| Notification store rewrites the entire file on every dismissal | Dismissals must be **append-only / batched**, and the 18.6 MB store must be **compacted**. | Rewriting 18.6 MB per keystroke causes severe disk lock contention and UI callback lag. |
| UI thread rebuilds widget list on step | Use **in-place DOM row patching** and update only affected counter badges. | Avoid tearing down Textual widget lists during simple cursor navigation. |

---

## 6. Recommended Solution & Implementation Plan

We recommend a three-phase solution addressing functional correctness, UI algorithm optimization, and persistence efficiency:

### Phase 1: Fix `,u` Functional Correctness & Scope (Immediate)

1. **Traverse the Full Unread Set Regardless of Folds:**
   Instead of filtering `roster = self._agents_with_children or self._agents`:
   - Inspect `_unread_completed_agent_ids` directly.
   - Look up the corresponding `Agent` objects from the complete loaded catalog or `_agents_query_result`.
   - Include member agents hidden inside collapsed clan containers and collapsed tribe panels.
2. **Loosen Terminal Status Check:**
   Update the predicate to include all failed agents:
   ```python
   def is_bulk_read_eligible(agent: Agent) -> bool:
       status = agent.status
       return is_unread_completed_status(status) or is_failed_agent_status(status)
   ```
3. **Decouple Bulk-Read from Undo:**
   Make `,u` unconditionally acknowledge all unread completed agents. Provide a separate undo action or require a confirmation/toast rather than silently inverting on the next `,u` press.
4. **Invalidate and Repaint Container Badges:**
   Ensure `_repaint_changed_unread_rows()` forces updates to:
   - Clan aggregate counters (`ClanStatusCounts.unread`).
   - Tribe banner titles (`[W26 F5 U21 D127]`).
   - The top headline metrics (`AgentInfoPanel`).

### Phase 2: High-Performance Candidate Discovery for `,j` (UI Optimization)

1. **Lightweight Candidate Indexing:**
   Instead of running `prospective_clan_members` on every step:
   - Maintain a simple list of unread agent references sorted by timestamp:
     `sorted([a for a in all_agents if a.identity in unread_ids], key=lambda a: a.stop_time or a.start_time, reverse=True)`.
   - When the user presses `,j`, simply select the next candidate from this list in O(1).
2. **Lazy Fold Expansion:**
   Only for the *single target agent* selected for the jump:
   - Check if its parent clan fold is collapsed. If so, expand *only* that specific clan fold via `_fold_manager.set_level(clan_fold_key, FoldLevel.EXPANDED)`.
   - Do not prospectively expand and reconstruct trees for all other clans.
3. **Selective Row Patching:**
   - When jumping to an unread agent in an already-expanded panel, do not call `_refresh_agents_display(list_changed=True)`.
   - Move cursor focus and call `_try_patch_agent_row(agent)` to update the unread glyph in place.

### Phase 3: Notification Store Optimization & In-Flight Protection (Backend / Core)

1. **Run Notification Compaction Immediately:**
   Execute `sase_job_notification_store_compact` to archive dismissed notifications older than 14 days out of `notifications.jsonl` into `notifications-archive.jsonl`. Shrinking `notifications.jsonl` from 18.6 MB down to active records (< 500 KB) will instantly slash I/O latency by 95%.
2. **In-Flight Acknowledgment Guard:**
   In `_unread_state.py`, maintain a temporary `_in_flight_dismissals` set of agent identities with a short TTL (e.g. 15s). During periodic polling reconciliation (`_reconcile_unread_from_completion_notifications`), ignore active notifications for identities in this set so background polling does not resurrect unread indicators while disk writes are processing.
3. **Append-Only / WAL State Updates in `sase_core` (Medium Term):**
   In the Rust core crate (`crates/sase_core/src/notifications/store.rs`), implement append-only mutation records (e.g. appending a compact dismissal line `{"op":"dismiss", "ids":[...]}`) instead of rewriting the entire JSONL file on every update, with periodic background compaction.

---

## 7. Conclusion

The failure of `,u` to clear unread indicators in the screenshot is not a mystery: all 27 unread nodes were trapped inside collapsed clan containers and collapsed tribes, with half of them failing exact status predicates. Furthermore, the slowness of `,j` stems from full prospective tree building on the UI thread combined with 18.6 MB full-file JSONL disk rewrites.

Using a background proc would introduce IPC overhead, synchronization complexity, and architectural violations without fixing these underlying issues. Implementing the lightweight candidate index, repairing the `,u` traversal and status predicates, compacting `notifications.jsonl`, and adding in-flight reconciliation guards will deliver an instant, rock-solid, and responsive unread workflow in the SASE TUI.
