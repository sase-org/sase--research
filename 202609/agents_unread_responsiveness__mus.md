# Agents-tab unread indicators: why `,u` flaked, why `,j` is slow, and what to do instead of a proc

**Author:** mus (independent swarm researcher)
**Date:** 2026-09-30
**Context:** `,u` (mark all unread done agents read) on the Agents tab appeared to do
nothing (screenshot `~/tmp/screenshots/20260930_060248.png`: header still shows
`27 unread` over 204 agents); unread markers are "flakey in general and always very
slow", including `,j` (jump to next unread done agent). Proposal under review: run
expensive unread work in the background behind a **proc**.

## TL;DR

- A service **proc is the wrong tool** for this job. In SASE a proc is a durable,
  supervised subprocess (proc-store row, logs, service host, lifecycle management).
  The unread paths are millisecond-scale in-memory set operations plus one small
  notification-store write — and that write **already runs off-thread** via Textual's
  `run_worker(thread=True)`. Wrapping it in a proc would add IPC, serialization,
  ordering, and failure-mode complexity to fix a problem that is not a compute problem.
- The `,u` "didn't work" is most plausibly a **correctness race, not missing
  backgrounding**: the bulk toggle clears unread state optimistically on the UI thread,
  but the periodic completion poll re-projects unread markers from the notification
  store **before the async dismissal write lands**, resurrecting the markers. The
  screenshot (stale `27 unread` count) is consistent with either this resurrection or
  with the indicator repaint lagging the optimistic clear.
- The `,j` slowness is most plausibly **redundant synchronous refresh work per
  keypress** (jump-time acknowledge + full display refresh + an unconditional
  `_refresh_current_tab` from the leader handler), not any single expensive kernel that
  needs a background thread.
- **Recommended solution:** keep the existing Textual thread-worker pattern, and (1) fix
  the optimistic-clear vs poll-reconcile race, (2) cut the duplicate refreshes on the
  `,u`/`,j` paths, (3) move the one synchronous disk read off the UI thread (an async
  variant already exists), (4) set a keypress-to-paint SLO and measure with the existing
  `tui_trace` instrumentation before parallelizing anything else.

## What the code actually does today

All paths below were read in the current checkout (repo root `sase_47`, TUI under
`src/sase/ace/tui/`). No peer swarm reports were consulted.

### `,u` — `mark_all_unread_done_agents_read`

- Leader binding: `,u` is `mark_all_unread_done_agents_read`
  (`src/sase/ace/tui/keymaps/mode_keymaps.py`), dispatched in
  `src/sase/ace/tui/actions/agent_workflow/_leader_mode.py` to
  `_toggle_all_unread_done_agents_read()`
  (`src/sase/ace/tui/actions/agents/_unread_state.py`).
- The toggle itself is **already cheap and synchronous**: set differences over
  `_unread_completed_agent_ids` for currently loaded terminal rows, then
  `_repaint_changed_unread_rows()` (selective row patching via
  `_patch_unread_completed_agent_changes`, with full-rebuild fallback).
- The durable side effect — dismissing the matching completion notifications in the
  notification store — is **already backgrounded**: `_schedule_unread_notification_dismissal`
  uses Textual `run_worker(work, thread=True, name="agents-unread-ack", group="agents")`
  and marshals the completion back with `call_from_thread`. This is exactly the
  "expensive work in the background" pattern the proposal asks for; it already exists.
- Two observations relevant to "didn't seem to work":
  1. On the `MARKED_READ` / `RESTORED_UNREAD` outcomes the leader handler notifies and
     returns **without** calling `_refresh_current_tab()` (only the `NOOP` branch
     refreshes). Repaint therefore depends entirely on the selective-patch path
     succeeding. If any patch misses (row not found, panel membership changed, widget
     tree unavailable), that row keeps its stale marker until the next 9 s auto-refresh
     tick — matching the screenshot's stale `27 unread` header.
  2. The notification **indicator** (top-right inbox counts) is refreshed only in
     `_complete_unread_notification_dismissal`, i.e. after the off-thread store write
     lands. Any poll or render between the optimistic clear and that completion shows
     stale counts — "flakey".

### `,j` — `jump_to_next_unread_done_agent`

- Dispatch: `,j` → `_jump_to_next_unread_done_agent()`
  (`src/sase/ace/tui/actions/agents/_unread_navigation.py`): cached candidate discovery
  (`_unread_timed_jump_candidates`), time-ordered jump with fold expansion /
  refilter / tab switch, per-target acknowledge (`_clear_agent_unread_and_dismiss_notification`
  + repaint or `_refresh_agents_display`), and then the leader handler **unconditionally**
  calls `_refresh_current_tab()` on top.
- `_refresh_current_tab()` on the Agents tab routes through `_schedule_agents_async_refresh`
  plus a forced fleet refresh (`_refresh_panel.py`, `_event_base.py`). So a single `,j`
  can perform: acknowledge + display refresh inside the jump **and** a scheduled async
  reload + fleet refresh afterwards. That stacking, repeated per keypress while stepping
  through 27 unread rows, is the obvious slowness suspect — compounded by per-ack work
  that rebuilds the agent-node projection index over roughly twice the roster
  (`_notification_keys_for_agents` indexes `[*requested, *loaded]`) on every jump.
- The candidate cache itself rebuilds its key from a `status_signature` tuple over **all**
  non-container agents plus a fold snapshot on every call — O(n) key construction per
  keypress even on a cache hit. Cheap at 204 rows, but it scales the wrong way and
  defeats the purpose of the cache under rapid `,j` repeats.

### The flakiness race (primary suspect for both symptoms)

The completion-poll tick (`_notification_polling.py`) unconditionally calls:

```python
self._reconcile_unread_from_completion_notifications(notifications)
```

and `_reconcile_unread_from_completion_notifications`
(`_notification_unread_projection.py`) **rebuilds unread state strictly from the active
notifications it is handed**, clearing manual guards first. The snapshot-cache prune
(`_remove_agent_completion_notifications_from_cache`) only happens in `_complete…`,
i.e. after the off-thread dismissal write finishes.

Window: `,u` clears 27 rows optimistically → poll tick reads the store **before** the
worker write lands → reconcile re-adds all 27 markers → worker write lands → markers
clear again (or the next tick re-clears them). To the user this looks exactly like
"`,u` didn't work" followed by markers mysteriously fixing themselves — "flakey in
general". The same race applies to single-row `,j` acknowledges. The 9 s auto-refresh
visible in the screenshot sets the timescale on which users observe the flicker.

A second, smaller staleness source: `_refresh_notification_count()` re-reads the
notification store **from disk synchronously on the UI thread** and is invoked from the
dismissal completion path. An async variant (`_refresh_notification_count_async`,
guarded single-flight snapshot loader) already exists — the sync one is the one wired
into the ack path.

## Critique of the proc proposal

**A proc is the wrong granularity and the wrong failure model for this work.**

1. **What a SASE proc is.** A background command / service proc is a durable proc-store
   row with logs, runtime directories, and supervision by the service host
   (`docs/ace.md`, `docs/architecture.md`: "`~/.sase/procs/` … Rust-owned proc rows,
   logs, and runtime directories for `%proc` named procs, gate answers, and other
   supervised background commands"). It is designed for durable, observable,
   restartable units of work — agents, monitors, gates — not sub-second UI mutations.
2. **The expensive half is already backgrounded.** The only true I/O on these paths
   (the notification-store dismissal) already runs on a Textual worker thread with
   `call_from_thread` completion. There is no remaining blocking kernel that a proc
   would remove from the event loop; a proc would just move the same write across a
   process boundary with serialization and ordering hazards.
3. **A proc makes the race worse, not better.** The core bug is an ordering problem
   (optimistic clear vs reconcile-from-stale-store). A proc lengthens the write path
   and adds a second completion channel, widening the resurrection window. Ordering
   guarantees are easier with the in-process worker + generation token than with proc
   lifecycle callbacks.
4. **Python-thread workers are sufficient here** because the background work is I/O
   (store read/write), not CPU-bound Python. The codebase already uses both
   `run_worker(thread=True)` and `asyncio.to_thread` for the heavy Agents loading
   pipeline (`_loading_filter.py`, `_loading_compute_finalize.py` with
   `PreparedFinalizePlan` stale-token discard). Follow that precedent; do not invent a
   new execution lane.
5. **The Rust-boundary note is out of scope for this fix.** Shared backend behavior
   belongs in `sase-core` (`AGENTS.md` §1.3), but unread marker state is session-local
   TUI presentation state (ephemeral sets on the app object), not shared backend
   behavior — no frontend would need to match it. Keep this fix in this repo.

## Requirements adjustments (proposed)

1. **Add a responsiveness SLO before changing execution strategy.** E.g.:
   keypress-to-visible-paint p95 < 100 ms for `,u` and `,j` at 500 loaded agents,
   measured with the existing `tui_trace("agents.refresh_display")` /
   `record_agents_refresh_trace` instrumentation. Do not background anything else until
   a trace shows what actually exceeds budget. (Justification: the current theory —
   duplicate refreshes + race — predicts the trace will show redundant full rebuilds,
   not one slow kernel.)
2. **Treat the resurrection race as a correctness bug, not a perf task.** Requirement:
   after `,u` reports "Marked N read", no poll tick may restore those markers unless a
   genuinely new completion notification arrives. (Justification: users cannot
   distinguish "slow" from "reverted"; fixing the race may resolve the whole report.)
3. **Downgrade "use a proc" to "use the existing worker pattern where tracing demands
   it".** Requirement: any new backgrounding uses `run_worker(thread=True)` /
   `asyncio.to_thread` with `call_from_thread` completion and a stale-plan discard,
   per the `PreparedFinalizePlan` precedent — no proc-store rows for UI state writes.
   (Justification: least new machinery, same-thread completion ordering, existing tests
   cover the pattern.)
4. **Scope the fix to loaded-row paths first; off-tab/collapsed rows second.**
   `_toggle_all_unread_done_agents_read` already iterates the full
   `_agents_with_children` roster, but verify collapsed-clan and off-tab unread rows
   clear and stay clear — the jump-candidate machinery treats those as separate cases
   and the repaint path is ancestor-aware for a reason.

## Recommended solution

In order; stop when the SLO in (1) above is met:

1. **Close the race (correctness first).**
   - Prune the acknowledged keys from `_notification_snapshot_cache` **optimistically**
     at `,u`/ack time (reuse `_remove_agent_completion_notifications_from_cache`),
     so an intervening poll reconcile cannot resurrect them; keep the existing restore
     path (`_restore_unread_notification_dismissal`) for genuine write failures.
   - And/or attach a generation token to the dismissal and have the poll reconcile skip
     keys with an in-flight dismissal, reconciling them only on the completion callback.
   - Regression test: simulate optimistic `,u` → poll with pre-dismissal snapshot →
     assert markers stay cleared (mirrors existing helpers in
     `tests/ace/tui/_agent_unread_helpers.py`, `test_agent_unread_toggle.py`).
2. **Remove the duplicate refresh on `,j` (and audit `,u`).**
   - The jump already refreshes appropriately per branch (`list_changed` vs highlight);
     make the leader handler's trailing `_refresh_current_tab()` conditional (e.g. skip
     when the jump reported success and already refreshed), or debounce it into the
     existing `_refresh_agents_display_debounced` two-phase path used for j/k
     navigation (highlight now, expensive detail after the burst settles).
   - Ensure the `,u` success path repaints the header count chip / tab strip even when
     selective patching reports fallback, rather than relying solely on row patches.
3. **Move the remaining sync disk read off the UI thread.** Route the ack completion
   through the existing `_refresh_notification_count_async` (guarded single-flight
   loader) instead of the synchronous `_refresh_notification_count`.
4. **Cheap per-keypress wins (only if tracing still shows pressure):** hoist the
   projection-index build out of per-row `_notification_keys_for_agents` on the bulk
   path (build once for 27 rows, not 27 times); replace the O(n) cache-key tuple in
   `_unread_timed_jump_candidates` with a roster-version counter.
5. **Verify with traces + existing suites**, not new machinery:
   `tests/ace/tui/test_agent_unread_*.py`, `test_agents_tab_refresh_paths.py`, and the
   `tui_trace` refresh/patch counters (assert no `display_full_rebuild` on `,j`-repeat
   and no marker resurrection across a poll tick).

## What I did not verify

- Exact millisecond breakdowns: I read the refresh/patch/reconcile code paths but did
  not run the TUI under `tui_trace` against a 200-agent roster, so the "duplicate
  refresh dominates" claim is code-reading inference, ranked first because the path
  structure (up to three refreshes per `,j`) makes it the highest-expected-value
  suspect. Step 0 of implementation should be capturing those traces.
- Whether the screenshot's stale `27 unread` came specifically from resurrection vs
  patch-fallback staleness; both mechanisms exist in the code and both produce the
  observed symptom. The recommended fix addresses both.

## Key sources (all in-checkout, independently readable)

- `src/sase/ace/tui/actions/agents/_unread_state.py` — toggle, optimistic clear,
  `run_worker(thread=True)` dismissal, restore-on-failure
- `src/sase/ace/tui/actions/agents/_unread_navigation.py`,
  `_unread_jump_candidates.py` — `,j` jump, candidate cache
- `src/sase/ace/tui/actions/agents/_notification_unread_projection.py` — reconcile
  strictly from active notifications (race site)
- `src/sase/ace/tui/actions/agents/_notification_polling.py` — poll tick reconcile +
  sync `_refresh_notification_count` vs existing `_refresh_notification_count_async`
- `src/sase/ace/tui/actions/agent_workflow/_leader_mode.py` — `,u` skips refresh on
  success; `,j` always refreshes on top of the jump's own refresh
- `src/sase/ace/tui/actions/agents/_display.py`, `_display_panel_widgets_refresh.py`,
  `_loading_filter.py`, `_loading_compute_finalize.py` — refresh costs and the
  existing `asyncio.to_thread` + stale-plan-discard precedent
- `src/sase/ace/tui/keymaps/mode_keymaps.py`, `src/sase/default_config.yml` — `,j` /
  `,u` bindings
- `docs/ace.md`, `docs/architecture.md` — service proc / background-command model
