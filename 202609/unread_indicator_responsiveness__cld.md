# Unread Indicators: Why `,u` Didn't Stick, Why `,j` Is Slow, and Whether a Proc Is the Right Fix

Researcher: `cld` · Date: 2026-09-30 · Scope: Agents-tab unread markers (`,u`
mark-all-read, `,j` jump-to-next-unread, row-selection acks), the notification store behind
them, and the TUI main-thread budget they depend on.

---

## TL;DR

1. **`,u` did work. Then something undid it.** The TUI's own toast log shows
   `Marked 27 completed agents read` at 06:02:21 local. That is 27 seconds *before* the
   screenshot (06:02:48), and the same 27 rows were unread again when you pressed `,u` a
   second time at 06:07:05. The optimistic in-memory clear and the background store write
   both ran and succeeded (there was no error toast). The dismissals were later reverted **in
   the notification store itself**.
2. **The most likely culprit is a lost update, not latency.** The remote-attention inbox
   reconciler reads the *entire* notification store, edits a few `remote-attention` rows,
   then writes back the *entire* list via `rewrite_notifications`. The Rust `rewrite` is a
   merge where *the caller's rows win on id collision*. So any `dismissed=true` written
   between that read and that write gets silently reverted to `dismissed=false`. The
   reconciler runs on a TUI background thread on a 60 s cadence, concurrently with the
   `agents-unread-ack` worker. There are also two TUI-side races (no "pending ack"
   protection, and stale snapshot reads can overwrite a fresher cache) that cause
   short-lived flicker.
3. **Slowness is mostly *not* the unread code.** The unread path does have real costs:
   - a **synchronous, full 19 MB notification-store re-read on the UI thread after every
     ack** (~200–300 ms);
   - 4–6 redundant rebuilds of the agent-node projection index per keypress;
   - an extra undebounced detail render on `,j`.

   But the dominant effect is that the TUI main thread is **saturated by periodic work**.
   The stall watchdog logged **386 freezes of ≥1.5 s totalling ~22 minutes in the last
   ~3.8 hours** (median 3.5 s, max 6.1 s). The top sources are the 1 Hz runtime-row repaint
   and fleet-refresh projection signatures. A `,j` press that lands behind one of those
   freezes waits seconds no matter how fast `,j` itself is.
4. **A proc is the wrong tool here.** SASE procs are durable, supervised subprocesses with
   **~1–3 s end-to-end latency**:
   - a Python import alone is ~0.7 s;
   - the supervisor claim takes 0.25–1 s;
   - the observer polls every 0.5 s;
   - the existing `notify.state` proc key rejects overlapping submits.

   The expensive part of an ack is not the store write, which is already off-thread. It is
   UI-thread recomputation plus a starved UI thread. A proc would also **widen** the race
   window that is currently breaking `,u`.
5. **Recommendation (details in §8):** fix correctness at the store level (atomic,
   field-scoped writes and no whole-store read-modify-write), then add a
   generation-confirmed pending-ack overlay. Make acks never read the store on the UI
   thread, funnel acks through one coalescing in-process writer, and cut the main-thread
   hot spots. Longer term, move "ack these agent completions" and a lean "unread completion
   index" into `sase_core` with the GIL released, and shrink the store.

---

## 1. What actually happened in the screenshot

The screenshot shows `27 unread` in the header, `athena 204 F5 U27` on the machine chip,
`U21` on `@epic`, and U-badges on epic-tribe clan rows.

The TUI logs pin down the sequence (`~/.sase/logs/tui_toasts.jsonl`; times UTC, local =
UTC−4):

| UTC | Event |
|---|---|
| 10:02:14 | `Launching agent for gh_sase-org__sase...` |
| **10:02:21** | **`Marked 27 completed agents read`** (the `,u` optimistic path ran; the count matched the header, so targeting was complete) |
| 10:02:21 | Stall log: main thread inside `_complete_unread_notification_dismissal` → `_refresh_notification_count` → **synchronous store read**. The worker's store write had already returned OK; no restore toast was emitted. |
| 10:02:22 | `Started 1 agent(s)` |
| 10:02:48 | Screenshot: 27 unread again |
| **10:07:05** | **`Marked 27 completed agents read`**, i.e. the *same 27* were unread again |
| 10:20:12 | `Marked 1 completed agents read` (the second `,u` stuck: today every completion row from 09-29 onward is `dismissed=true` in the store) |

What this rules out:

- **Not a targeting bug.** `,u` targets `_agents_with_children` (the full, unfiltered
  roster), which includes clan members and other tabs and machines. The header, tab chips
  and clan badges all count subsets of that roster with the same status predicate
  (`DISMISSABLE_STATUSES`, which includes FAILED / EPIC CREATED / TALE DONE). A sub-agent
  cross-checked the identity sets and found them consistent. The toast count (27) equals
  the header count (27).
- **Not a failed write.** Failure would have produced
  `"Could not mark agent notification read; restored unread marker"` (`_unread_state.py:431`
  onward). No such toast exists.
- **Not a transient UI-only race.** TUI-side races self-heal on the next store read (seconds
  later). Here the unread state persisted for ≥27 s and was still there ~5 minutes later.
  That means the store itself held `dismissed=false` again: **a durable, store-level
  revert.**

### 1.1 The lost-update writer

`src/sase/dispatch/attention_inbox.py:129-209`, `reconcile_remote_attention_inbox`:

```python
rows = load_notifications(include_dismissed=True)      # read ENTIRE store (19 MB)
output = list(rows)
... edit a handful of sender == "remote-attention" rows ...
if outcome.changed:
    rewrite_notifications(output)                      # write back ENTIRE list
```

`sase-core` `crates/sase_core/src/notifications/store.rs:1044-1067`:

```rust
// Rewrite is a _merge_: caller's rows win on id collision; rows present on
// disk but absent from the input are preserved ...
let mut merged: Vec<NotificationWire> = input.to_vec();
for row in existing { if !input_ids.contains(row.id.as_str()) { merged.push(row); } }
```

Every row the reconciler read, including all agent-completion rows it never touched, is in
`input`. Any dismissal committed between its `load_notifications` and its `rewrite` is
overwritten with the stale `dismissed=false`. This is a classic read-modify-write lost
update. The merge protects concurrent *appends*, but not concurrent *state changes*.

Why this writer:

- It runs from the TUI on a background thread (`_remote_attention.py`, 60 s network
  refresh cadence, `FLEET_ATTENTION_INVENTORY_NETWORK_REFRESH_SECONDS = 60.0`).
- Its read is a full parse of the 19 MB store into Python objects, which takes ~280 ms on
  an idle host. The athena TUI was far from idle: agent loads were logging 5 s disk reads
  around 10:02. So the vulnerable window is hundreds of ms to seconds, once a minute.
- The 106 active `remote-attention` rows were refreshed recently (100 share one
  `observed_at` minute), so the reconciler is actively producing `changed` outcomes and
  rewriting.
- The only other whole-store rewriter, `agent/names/_migration.py`, is a rare migration.

**Confidence:**

- *High* that a store-level revert occurred.
- *Medium-high* that the attention reconciler was the writer. It is the only routine
  whole-store read-modify-write writer, and its timing and cadence fit. The store does not
  record dismissal timestamps, so I could not prove the exact interleaving.

The flakiness you've felt in general ("marked read, then it comes back") matches the same
bug: it only bites when an ack lands inside the reconciler's window.

### 1.2 Secondary (transient) flakiness sources in the TUI

These don't explain a 5-minute revert, but they do cause brief "it came back / it
flickered" moments, and they will matter more once acks are faster.

1. **No pending-ack protection.** `_mark_current_unread_done_agents_read` clears only the
   in-memory set (`_unread_state.py:170`). The cached notification snapshot keeps the
   notifications active until the worker finishes.

   Anything that recomputes unread state in that window puts them all back. There are three
   such recomputes:
   - the poll (`_notification_polling.py:316`);
   - agent-list finalize (`_loading_finalize.py:36-93` → `_reconcile_unread_from_completion_notifications`);
   - `_reconcile_unread_from_cached_notifications`.

   The recompute also cancels the undo snapshot (`_notification_unread_projection.py:208`).
   `_pending_bulk_read_agent_ids` is only an undo record; the reconcile never consults it.
   At 10:02 two agent-list loads were in flight (an auto-refresh started before `,u`, plus
   the launch reload).
2. **Stale snapshots can overwrite fresher ones.** `_read_notification_snapshot_guarded`
   stores whatever it read (`_notification_provider.py:257`,
   `self._set_notification_snapshot_cache(snapshot)`) with no generation or stat-token
   comparison.

   So a poll whose read started *before* the dismissal write can land *after* the
   completion callback's fresh read and resurrect the unread rows until the next tick.
3. **Machine-tab chip lag.** The `,u` success branch does not call `_refresh_current_tab()`
   (`_leader_mode.py:195-209`). The row-patch path refreshes panel titles, the info panel
   and the tribe summary, but not the machine tab strip (`_update_agents_header`). So
   `athena … U27` can lag even when state is correct.
4. **Latent key divergence.** Python treats `raw_suffix == ""` as "no suffix" and matches on
   `cl_name` alone. The Rust dismiss matcher treats `""` literally. Such a notification
   would be removed from the TUI cache but never dismissed in the store, so it reappears on
   the next read. No live rows have this shape today, but the unit-test helper builds
   exactly this shape.

Test coverage (`tests/…/test_agent_unread_toggle.py`) covers plain rows only. It has no
cases for concurrent reconcile, stale poll landing, attention-reconciler interleaving, clan
or tribe members, or other tabs.

---

## 2. Why the unread indicators feel slow

### 2.1 The whole UI thread is saturated (the biggest factor)

`~/.sase/logs/tui_stalls.jsonl` (+ `.1`) from 06:38Z to 10:26Z on the running TUI (pid
2832234, up 37 h):

- **386 hitches ≥1.5 s, 1,312 s (≈22 min) frozen in ≈3.8 h**, p50 3.5 s, max 6.1 s.
- Main-thread CPU time: **9 h 21 m over 37 h of uptime (≈25% duty cycle)**. Process RSS is
  3.9 GB, of which 520 MB is swapped out.

Top hitch sources, grouped by entry and call path:

| # hitches | Frozen total | Path |
|---:|---:|---|
| 87 | 343 s | 1 Hz countdown tick → `_patch_agent_runtime_rows` → `patch_row` |
| 49 | 140 s | fleet refresh → `_apply_fleet_projection` → `_agents_projection_signature` |
| 17 | 66 s | countdown tick → `_runtime_suffix_ticks` |
| 13 | 31 s | fleet refresh → `_update_agents_header` |
| 12 | 48 s | debounced detail → `update_display` |
| 11 | 26 s | fleet refresh → `_finalize_agent_list` |

Root causes I confirmed in code:

- **`patch_row` recomputes whole-roster wait-status maps for every clan-container patch.**
  `_agent_list_build_patching.py:259-261` calls
  `agent_wait_status_maps_for_build(widget, widget._agents)`, which reaches
  `agent_wait_status_maps_for_app` (`_agent_completion_wait.py:351-364`). That calls
  `collect_agent_wait_status_maps(app._agents_with_children)` with **no caching**.
  - The runtime tick patches every active row once a second.
  - With dozens of epic/tribe clan containers, that is O(clans × N) Python work per second.
  - Bulk `,u` repaints hit the same cost: O(K × N).
- **The fleet projection signature deep-freezes every field of every agent**
  (`_fleet_projection.py:32-64`). It recurses through mappings, sets and sequences, and calls
  `repr()` on nested dataclasses, on every fleet refresh, to decide whether to reproject.
  Innermost frames are `isinstance`/`is_dataclass` inside `_freeze_projection_value`.

**Implication:** keypresses queue behind these freezes. Even a perfectly optimized `,j`
handler feels "always slow" while the event loop is stuck for 2–6 s every few seconds.
Unread indicators suffer the most, because every step of them (jump, ack, repaint, count
refresh) triggers more main-thread work.

### 2.2 Unread-path-specific costs

These come from a static trace plus a headless benchmark (synthetic roster: 162 visible /
234 total / 111 unread, with the real notification file copied into a sandbox). The
synthetic numbers *understate* reality: no agent sessions, no artifact files, and an idle
host.

| Cost | Where | Measured |
|---|---|---|
| **Synchronous full notification-store read on the UI thread after every ack** | `_complete_unread_notification_dismissal` (`_unread_state.py:431-455`) → `_refresh_notification_count` → `_read_notification_snapshot_from_provider()` (`_notification_polling.py:335-346`) | 240–320 ms per call (19 MB, 3,879 rows, p99 row 70 KB, max 177 KB). Always a cache miss because the worker just wrote the file. Live stalls at 1.5 s and 2.15 s with exactly this stack. |
| Self-triggered re-poll | inotify watcher sees our own write → `_schedule_notification_poll` → another cold parse + reconcile | ~200 ms parse on a thread (still ~45 ms of GIL stall on the UI thread) + reconcile on the UI thread |
| `agent_node_projection_index` rebuilt from scratch 2× per keypress, plus 2–4× in the completion callback, finalize and polls | `_unread_state.py:85`, `_notification_unread_projection.py:59/173`, `_loading_finalize.py` | ~2 ms synthetic, but a **2.3 s live freeze** on a `,j`-into-collapsed-clan path inside `agent_node_projection_index` → `concrete_agent_session_member_rows`. It also has an O(owned²) dedupe (`agent_nodes.py:195`). |
| Undebounced, doubled detail render on `,j` | `_leader_mode.py:170` calls `_refresh_current_tab()` → `_refresh_agents_display()` with `defer_detail=False` (`_event_base.py:66-77`) after the jump already rendered | detail `update_display` p50 28 ms / p95 516 ms / max 2.3 s in the live trace. The prompt/transcript reads are synchronous. |
| `,u` bulk repaint is O(K·N) | per-row `patch_row` (see wait-maps above) + `_agents.index` + title recompute | 150–190 ms synthetic for 111 rows, before the 260–310 ms completion callback |
| `_remove_agent_completion_notifications_from_cache` scans notifications × keys on the UI thread | `_unread_state.py:258` | grows with batch size |
| `,j` into a collapsed clan or another tab does a full `_refilter_agents` + rebuild | `_unread_navigation.py:348`, `_jump_to_off_tab_timed_candidate` | 27–52 ms synthetic, much more on the live roster |

The actual store write (`dismiss_agent_completion_notifications_matching_agents`, ~240 ms
and a full-file rewrite under the lock) is **already off the UI thread** (`run_worker(...,
thread=True, name="agents-unread-ack")`, added in `980de1487a`). The problem is everything
around it.

---

## 3. Critique of "use a proc to run expensive work in the background"

The instinct is right: *nothing expensive should run on the UI thread.* The mechanism is
wrong for this problem.

### 3.1 What a SASE proc costs

- It is a durable, supervised subprocess recorded in `~/.sase/procs/procs.jsonl`
  (`src/sase/procs/spawn.py`).
  - It is launched through a Python bootstrap under `detach_scope`/systemd-run.
  - The caller waits for a start-ack marker, which is polled every 50 ms.
  - It then runs `sase <domain> …`, a fresh Python process that imports sase and
    `sase_core_rs` (~0.7 s import alone).
- Results come back through a durable result file. The TUI sees them only when the
  `ProcObserver` thread re-reads the proc store, every 0.5 s.
- **Measured from the live proc store:**
  - supervisor claim takes 0.25–1.0 s;
  - the cheapest commands take about 1 s end to end;
  - the one recorded `notify apply-state-many read` took **2.62 s**.
- The closest precedent, the notification modal's `notify.state` procs, uses a single
  global concurrency key (`"notification-state"`). A second submit while one runs is
  **rejected**, which would break rapid repeated `,j` presses.

### 3.2 Why it doesn't fit this problem

1. **Wrong bottleneck.** The write is already off-thread. What blocks the UI is:
   - the synchronous post-ack store read;
   - O(N) recomputation on every patch and keypress;
   - unrelated periodic work that freezes the loop for seconds.

   A proc moves none of that. Whatever the proc produces still has to be applied to
   widgets on the UI thread.
2. **It makes the correctness bug worse.** A proc stretches the write from ~250 ms to
   ~1–3 s. That widens both the store-level lost-update window and the TUI's
   optimistic-state window, during which polls and reloads resurrect unread rows. Today's
   `,u` failure is a race, and slower writes lose races more often.
3. **Latency floor.** Interactive feedback needs <50–100 ms. A proc's floor is ~1 s.
4. **Durability isn't needed here.** Procs earn their cost when work must survive TUI
   exit, needs an audit row, or runs for a long time. A 250 ms ack does not need a
   supervisor.
5. **Precedent points the other way.** Prior research concluded the same:
   - `202608/detached_proc_convergence` lists TUI proc types that "should stop being procs
     entirely".
   - `202609/bead_speedup_daemon_vs_direct_path` found the cost was imports and redundant
     reads, not a missing background process. Two earlier daemons were deleted.

### 3.3 Where the idea is partly right

- **The GIL.** Python work on a background *thread* still competes with the UI thread. The
  sandbox measured a ~45 ms UI stall per background store parse. A separate *process* is
  the only way around the GIL in CPython 3.14 (GIL build). But the answer is to *not do
  heavy Python work at all* on hot paths: use Rust with the GIL released, caching, or
  incremental updates. A cold subprocess per action is not the answer.
- **A warm helper process** (long-lived, pipe-connected, like a language server) would
  avoid both the GIL and spawn cost. But that is a daemon, and the project has deleted
  daemons twice for good reasons. Keep it in reserve only if Phase 2 profiling shows
  background-thread GIL contention still dominates after the fixes below.
- **Keep procs where they already fit:** the modal's `sase notify apply-state-many` bulk
  operations, where durability and audit matter and latency does not.

---

## 4. Requirement adjustments (explicit changes to what you asked for)

> **Adjusted R1 — Correctness before speed (new).** An acknowledgment (`,u`, `,j`, row
> selection) must be durable and must never be silently reverted by any other writer. No
> notification-store writer may do a whole-store read-modify-write; state changes must be
> atomic and field-scoped under the store lock. *Why:* the screenshot failure is a lost
> update, and making things faster without this makes it more frequent.

> **Adjusted R2 — Replace "run expensive work in a proc" with "no expensive work on the UI
> thread; background work stays in-process (worker thread or GIL-released Rust); procs only
> for durable, audit-worthy side effects."** *Why:* §3.

> **Adjusted R3 — Widen scope beyond the unread code path.** Include the top main-thread
> hitch sources (1 Hz runtime-row patching / wait-status maps, fleet projection signature).
> *Why:* they account for ~22 min of freezes in ~4 h, and `,j` can't feel fast while the
> loop is frozen behind them.

> **Adjusted R4 — Measurable budgets.** On a ~250-agent roster with the current 19 MB
> store:
> - `,j` key-to-paint ≤ 50 ms p95;
> - `,u` ≤ 100 ms p95 for 100 rows;
> - **zero** synchronous notification-store reads on the UI thread in any ack path;
> - no stall-log hitch whose stack contains an unread/ack frame.
>
> *Why:* "much more responsive" needs a regression gate, and the repo already has the
> harnesses (`bench_tui_jk_agents.py`, `SASE_TUI_PERF`, the stall watchdog).

> **Adjusted R5 — One source of truth with an explicit optimistic overlay.** Displayed
> unread = store-derived unread − pending acks + manual `U` marks. A pending ack clears
> only when a snapshot whose store token is at or after the ack's write token confirms it.
> *Why:* removes both TUI-side race classes (§1.2) in one mechanism.

> **Adjusted R6 — Store hygiene is in scope.** The live store is 19 MB with 3,879 rows,
> 1,037 of them active. p99 rows are 70 KB and the largest is 177 KB (`wait_checks`
> `plus_ones`, big `action_data`). Every full read costs 200–300 ms, and every write
> rewrites the whole file. *Why:* a lean read path and compaction shrink every cost above,
> including the lost-update window.

---

## 5. Options considered

| Option | Latency effect | Correctness effect | Cost | Verdict |
|---|---|---|---|---|
| **A. Proc per ack/bulk ack** (your proposal) | None on UI-thread costs; write takes ~1–3 s; overlapping submits rejected | **Worse**: widens race windows | Medium | ✗ Not for interactive acks |
| **B. Patch the in-process path** (async post-ack refresh, drop redundant refresh, cache projection index) | Large for unread path | Neutral unless paired with D/E | Small | ✓ Part of recommendation |
| **C. Single coalescing ack-writer** (one worker thread plus a queue; batches rapid `,j` acks into one store update; returns dismissed ids and store token) | Removes per-ack cold reads; fewer full-file rewrites | Good: serializes TUI writes, enables R5 | Small–medium | ✓ |
| **D. Pending-ack overlay with generation-confirmed reconcile, plus a monotonic snapshot cache** (reject older snapshots) | Neutral | **Fixes TUI-side flicker races** | Small | ✓ |
| **E. Atomic, field-scoped store writes in `sase_core`** (attention reconcile becomes a Rust upsert that owns only remote-derived fields and preserves on-disk `read`/`dismissed`; no whole-list rewrite) | Also cheaper writes | **Fixes the `,u` revert** | Medium (cross-repo) | ✓ Highest priority |
| **F. Lean unread index and ack API in `sase_core`** (`ack_agent_completions(keys) → {dismissed_ids, token}`; `read_unread_completion_index()` returns only id/key/read/dismissed; GIL released) | Big: removes 19 MB parses from hot paths | Good | Medium | ✓ Phase 3; matches the Rust-core boundary rule (a web UI would need identical unread semantics) |
| **G. Main-thread hot-spot fixes** (cache wait-status maps and projection index per roster generation; cheap fleet signature; patch only rows whose runtime text changed) | **Largest perceived win** | Neutral | Medium | ✓ Phase 2 |
| H. Notification daemon or warm helper process | Good | Neutral | High; daemons deleted twice | ✗ Hold in reserve |
| I. Replace the JSONL store with SQLite | Good (row updates, indexes) | Good | High migration | Later / only if E+F+R6 fall short |
| J. Free-threaded CPython (3.14t) | Potentially good | Neutral | High ecosystem risk (PyO3 build, Textual) | ✗ Not now |

---

## 6. Detailed design of the recommended pieces

### 6.1 Store correctness (sase-core + `attention_inbox.py`)

- **Quick fix (sase repo only).** Pass *only the rows the reconciler created or changed* to
  `rewrite_notifications`, not `output` (the whole list). Because the Rust rewrite
  preserves rows absent from the input, unrelated agent-completion rows can no longer be
  reverted. Residual risk: a user dismissal of a *changed remote-attention row* can still
  be clobbered.
- **Proper fix (sase-core).** Add an atomic upsert, e.g.
  `upsert_notifications_preserving_local_state(rows, owned_fields)`. Under the store lock it
  re-reads the on-disk row and applies only the reconciler-owned fields (icon, color, notes,
  tags, action, action_data, silent). It keeps on-disk `read`/`dismissed` unless the row
  carries the auto-dismiss marker. That matches the documented intent in
  `_refresh_existing_notification`. Then route the attention reconciler through it.
- **Make the reconciler avoid no-op rewrites.** Exclude volatile fields such as
  `observed_at_unix` from its change detection, so it doesn't rewrite the 19 MB file every
  minute.
- **Consider making `rewrite_notifications` refuse to flip `dismissed: true → false`**
  unless the caller opts in explicitly. This is a guard rail for future callers; a new API
  flag would keep migrations working.
- **Align the empty-`raw_suffix` matching semantics** between Python and Rust.

### 6.2 TUI optimistic state (sase repo)

- **`_pending_ack_keys: dict[AgentCompletionKey, int]`.** Record each ack's key and the
  write's resulting store token (returned by the writer).
  - `_reconcile_unread_from_completion_notifications` treats pending-acked identities as
    read.
  - A pending entry is dropped once a snapshot whose token is ≥ the write token has been
    applied, or on write failure, which restores the row as today.
- **Monotonic snapshot cache.** `_set_notification_snapshot_cache` ignores snapshots whose
  stat token (mtime_ns, size, inode) or generation is older than the cached one.
- **Refresh the machine-tab strip** in `_patch_unread_completed_agent_changes`.

### 6.3 Ack writer and no UI-thread reads (sase repo)

- **One long-lived ack worker** (thread + queue). `,j`/selection acks enqueue keys.
  - The worker drains everything queued and issues **one** Rust dismiss call per batch.
    Five fast `,j` presses become one write.
  - It returns `{dismissed_ids, store_token}` via `call_from_thread`.
- **In `_complete_unread_notification_dismissal`, delete the `_refresh_notification_count()`
  call.** Instead:
  - apply `dismissed_ids` to the cached snapshot (already done by
    `_remove_agent_completion_notifications_from_cache`; key it by id instead of scanning
    notifications × keys);
  - recompute indicator counts from the cache;
  - record `store_token` so the watcher-triggered poll for our own write is skipped.
  - If a full resync is wanted anyway, schedule the existing single-flight
    `_refresh_notification_count_async`, never the sync variant.
- **Add a guard test:** patch `_read_notification_snapshot_from_provider` to raise when it
  is called on the main thread during ack flows.

### 6.4 Unread-path UI work (sase repo)

- **`,j`:** remove the trailing `_refresh_current_tab()` in the leader handler (or pass
  `defer_detail=True`). The jump already repaints, and the detail pane should stay behind
  the 150 ms debounce.
- **Cache `agent_node_projection_index`** keyed on the roster generation (the
  `_agents_with_children` list identity plus load generation). Invalidate it on
  reload/refilter. Fix the O(owned²) dedupe.
- **Cache `collect_agent_wait_status_maps`** per roster generation (this also fixes the 1 Hz
  hot spot, §6.5).
- **`,u` above ~20 rows:** do one list rebuild instead of K patches, or make the patches
  O(1) with the caches above.
- **Instrument:** add `tui_trace` spans for `leader.unread_jump`, `leader.mark_all_read`,
  `unread.ack_complete` and `agent_nodes.projection_index`, and extend `SASE_TUI_PERF`
  key-to-paint to leader keys.
- **Add benchmarks:** extend `tests/ace/tui/bench_tui_jk_agents.py` with `,j` (four
  branches: visible, collapsed panel, collapsed clan, other tab) and `,u` (100 rows) cases
  against the R4 budgets.

### 6.5 Main-thread saturation (sase repo)

- **Wait-status maps:** see the §6.4 caching bullet. This is the #1 stall source through
  `_patch_agent_runtime_rows` → `patch_row` for clan containers.
- **Runtime tick:** compute per-row runtime text cheaply and patch only rows whose rendered
  suffix changed. Clan runtime aggregation (`aggregate_clan_runtime`) should be cached per
  clan and roster generation.
- **Fleet projection signature:** replace the recursive `_freeze_projection_value`
  deep-freeze with a cheap signature built from wire revisions or per-agent version
  counters. The fleet responses come from Rust and can carry a revision hash. At minimum,
  compute it off-thread and skip `repr()` of nested dataclasses.
- **Operational hygiene:** the process had been up 37 h at 3.9 GB RSS with 520 MB swapped.
  Swapped heap pages make GC traversals and cold paths slower. Worth measuring after the
  fixes, e.g. `gc.freeze()` after startup and a periodic memory report.

---

## 7. Test plan (gaps to close)

1. **Lost update:** interleave `load_notifications` → a dismissal via the ack API → the
   attention reconciler's rewrite, then assert that the completion row stays dismissed.
   This goes in the sase-core store tests and a Python integration test.
2. **Pending window:** after `,u`, run `_reconcile_unread_from_completion_notifications`
   with the pre-write snapshot, then assert the rows stay read and the undo stays armed.
3. **Stale snapshot landing:** start a guarded read, complete the ack, then deliver the
   older snapshot and assert the cache is not regressed.
4. **Scope:** `,u` with clan members, epic tribe members, rows on another agent tab, and
   rows on another machine tab. Assert that the header, machine chip and clan badges all
   reach 0.
5. **Empty `raw_suffix`:** Python and Rust matcher parity.
6. **Budgets:** the §6.4 benchmarks, plus a "no main-thread store read" guard.

---

## 8. Recommended solution

**Don't route unread work through procs.** Treat this as a correctness bug plus a
main-thread-budget problem, and ship in four phases. Each phase is independently useful.

**Phase 0 — make `,u` stick (days, highest priority)**

1. `attention_inbox.reconcile_remote_attention_inbox` rewrites only the rows it changed,
   and stops rewriting on volatile-field-only changes. *(The one-line core of the fix.)*
2. sase-core: add an atomic, field-scoped upsert for the attention reconciler that
   preserves on-disk `read`/`dismissed`. Guard `rewrite` against un-dismissing rows. Bump
   `sase-core-revision.txt`.
3. TUI: pending-ack overlay confirmed by store token, plus a monotonic snapshot cache.
4. Refresh the machine-tab strip after unread patches, and align empty-`raw_suffix`
   matching.
5. Tests from §7 (1–5).

**Phase 1 — make acks cheap (days)**

1. Remove the synchronous `_refresh_notification_count()` from the ack completion path.
   Apply the writer's `dismissed_ids` to the cache, and skip the self-triggered poll.
2. A single coalescing in-process ack writer (thread + queue).
3. Drop the redundant `_refresh_current_tab()` after `,j` so the detail pane stays
   debounced.
4. Cache `agent_node_projection_index` per roster generation, and do one rebuild for large
   `,u` batches.
5. Trace spans, and benchmarks with the R4 budgets.

**Phase 2 — give the UI thread its time back (1–2 weeks; biggest felt improvement)**

1. Cache wait-status maps per roster generation. This fixes the #1 stall source.
2. Change-only runtime-row patching and cached clan runtime aggregation.
3. A cheap fleet projection signature.
4. Re-measure with the stall watchdog. Target: no hitches from the 1 Hz tick or fleet
   refresh on a ~250-agent roster.

**Phase 3 — push the domain into `sase_core` and shrink the store (follow-on epic)**

1. `ack_agent_completions(keys) → {dismissed_ids, token}` and
   `read_unread_completion_index()` (a lean projection that skips large payloads), both
   releasing the GIL. Optionally, the unread projection itself ("which agent nodes are
   unread given these notifications") moves to Rust so every frontend agrees.
2. Store hygiene: archive dismissed rows more aggressively, and cap or externalize
   `wait_checks` `plus_ones` / large `action_data`.
3. Re-evaluate only then whether a warm helper process or a SQLite store is still
   warranted. Neither is expected to be.

**Expected outcome:**

- `,u` becomes durable (Phase 0).
- The `,j` handler itself drops from ~80–300+ ms plus a 250 ms post-ack freeze to well
  under 50 ms (Phase 1).
- The "always slow" feeling goes away once the loop stops freezing for 2–6 s every few
  seconds (Phase 2).

---

## Appendix A — Evidence commands (all read-only)

- Toasts: `grep -n "completed agents" ~/.sase/logs/tui_toasts.jsonl`, lines 86 and 95
  (10:02:21Z / 10:07:05Z, "Marked 27 …").
- Stalls: parse `~/.sase/logs/tui_stalls.jsonl{,.1}`. Group `tui_hitch` stacks by the first
  `ace/` frame and the next three frames; pair each with the following `*_recovered.duration_seconds`.
- Process: `ps -L -o tid,time,pcpu,comm -p <tui pid>`; `grep VmSwap /proc/<pid>/status`.
- Store: `~/.sase/notifications/notifications.jsonl` (19 MB, 3,879 rows; active by sender
  bead 179, wait_checks 158, axe 149, ci_watch 140, remote-attention 106, …) and
  `notifications-archive.jsonl` (47 MB).
- Rust merge semantics: `sase-core/crates/sase_core/src/notifications/store.rs:1044-1067`
  (opened with `sase repo open sase-core`).

## Appendix B — Key code references

- `src/sase/ace/tui/actions/agent_workflow/_leader_mode.py:165-209`: the `,j`/`,u`
  handlers.
- `src/sase/ace/tui/actions/agents/_unread_state.py`:
  - 145: toggle;
  - 170: optimistic mark;
  - 258: cache prune;
  - 378: worker schedule;
  - 431-455: completion, including the sync count refresh.
- `src/sase/ace/tui/actions/agents/_notification_polling.py:316` (poll reconcile) and
  `:335-346` (sync `_refresh_notification_count`).
- `src/sase/ace/tui/actions/agents/_notification_unread_projection.py:147-210`: the
  reconcile. It ignores pending acks and invalidates undo.
- `src/sase/ace/tui/actions/agents/_notification_provider.py:220-268`: the guarded read,
  which caches unconditionally.
- `src/sase/ace/tui/actions/agents/_loading_finalize.py:36-93`: reconcile on every list
  finalize.
- `src/sase/dispatch/attention_inbox.py:129-209`: the whole-store read-modify-write.
- `src/sase/ace/tui/widgets/_agent_list_build_patching.py:259-261` and
  `src/sase/ace/tui/_agent_completion_wait.py:351-364`: uncached wait maps per patch.
- `src/sase/ace/tui/actions/agents/_fleet_projection.py:32-64`: the deep-freeze signature.
- `src/sase/ace/tui/actions/_event_countdown.py:36-49`: the 1 Hz tick work.
