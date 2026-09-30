# Agents-tab unread indicators: responsiveness, `,u` failure, and why a proc is the wrong first cut

- **Researcher:** grk (`research.2x.grk`)
- **Date:** 2026-09-30
- **Question:** Why did `,u` on the Agents tab fail to clear unread chrome (screenshot `~/tmp/screenshots/20260930_060248.png`), why are unread jumps (`,j`) and unread badges generally slow and flaky, and is “run expensive work in a proc” the right implementation?
- **Inspected:** live screenshot; `tui.md` / `tui_perf.md`; glossary `proc` / `oneshot`; Agents unread mixins (`_unread_state.py`, `_unread_navigation.py`, `_unread_jump_candidates.py`, `_notification_unread_projection.py`); leader dispatch (`_leader_mode.py`); collapsed-panel paint (`_agent_list_widget.py`, `_display_panel_widgets_paint.py`); row-patch fallback (`_display_panel_patches.py`); notification snapshot complete-path (`_notification_polling.py`, `_notification_provider.py`, `notifications/store.py`); durable-proc submission (`_proc_action_submission.py`); hitch-fix stitch `980de1487a` (`sase-124.5`). Independent of the other four swarm reports.

## Recommended solution

Keep unread chrome as an **optimistic, in-memory set** and make every user-facing unread action an **O(visible chrome) UI-thread patch**. Persist notification dismissals off-thread the way `sase-124.5` already does. Do **not** wrap this in a durable SASE Proc.

Ship this as one TUI epic with four mechanical rules:

1. **Badge-only unread changes never rebuild the Agents list.** Collapsed tribes have empty row lists (`render_collapsed()`). Today that makes the first collapsed unread patch fail and fall back to a full 284-row rebuild. For unread-only diffs, skip row patches on collapsed panels and repaint titles, the info chip, and the tab strip.
2. **In-flight acks are source of truth until persist fails.** Notification poll, 9s auto-refresh finalize, and the ack complete-handler all re-project unread from the snapshot. That clobbers the optimistic clear and is the flake. Hold a pending-ack identity set and ignore matching active notifications until the worker reports success or failure.
3. **`,j` must not call `_refresh_current_tab()`.** The jump already refreshes with `defer_detail=True`. The leader handler then applies the expensive detail pane immediately, including on-demand `hydrate_agent_attempt_history` disk work. Use the same two-phase path as `j`/`k`: highlight now, debounce detail.
4. **Leader “has unread?” is O(unread), not a candidate rebuild.** `_has_unread_completed_agent()` currently builds a cache key that tuples every loaded agent’s identity, status, and timestamps, then may walk collapsed-clan and off-tab query rows. Pressing `,` already hitchs before `u` or `j` runs.

Measure before and after with `SASE_TUI_PERF=1`, `SASE_TUI_TRACE=1`, and `~/.sase/logs/tui_stalls.jsonl`. Target: `,u` p95 < 16 ms of UI-thread work at this screenshot’s scale (284 agents, 27 unread, collapsed tribes, ~7k inbox); `,j` to an already-visible row matches ordinary `j`/`k`; `,j` that expands one collapsed tribe rebuilds **that tribe only**.

---

## Verdict

The user’s goal is right. The proposed mechanism is not.

Unread chrome is slow and flaky because the **UI thread does too much work to paint a badge**, and because **optimistic clears are not sticky** against the notification store. A durable Proc (the `~/.sase/procs/` object, Procs-tab row, argv worker) cannot paint, and would add store I/O, a subprocess, and — with the current `_submit_durable_proc(..., reload_on_complete=True)` default — a full Agents reload on every ack. That is the opposite of the 16 ms key-to-paint budget in `tui_perf.md`.

`sase-124.5` already moved the store write off-thread (`run_worker(..., thread=True, name="agents-unread-ack")`) with optimistic row state. The remaining hitch is everything around that worker: collapsed-panel patch fallback, a synchronous 7k-row snapshot re-read on complete, reconcile that restores unread, and a leader-mode full tab refresh on `,j`.

I would take the approach above. The adjustments below are where the request as written would otherwise make the TUI slower or more flaky.

---

## Requirement adjustments

These change the request. Each is load-bearing.

| ID | Adjustment | Why |
| --- | --- | --- |
| A1 | **Do not introduce a durable SASE Proc for unread ack, jump, or chrome refresh.** Persistence stays a Textual thread worker (or `spawn_pump_free_task` + `asyncio.to_thread`). | A Proc is a supervised argv with a `procs.jsonl` row. Unread ack is an in-process Rust notification-store write. `reload_on_complete=True` would rebuild Agents. The Procs tab would fill with 50 ms bookkeeping jobs. |
| A2 | **Do not background “anything that causes a delay.”** Only persistence, snapshot parses, and key projection may leave the UI thread. Paint, selection, and chrome stay synchronous and cheap. | Textual cannot patch widgets from a worker. Off-thread work that marshals a full rebuild back onto the pump is how hitches move around rather than disappear (`tui_perf.md` rules 1–2, 6–7). |
| A3 | **`,u` must clear unread chrome without expanding collapsed tribes and without rebuilding OptionLists.** Titles, the `27 unread` chip, and tab-strip `U#` badges update in place. | The screenshot’s 27 unread live entirely in collapsed `@epic` (U21) and `@job` (U6). Expanding `@epic` to paint 174 BY_STATUS rows is not “mark as read.” |
| A4 | **Treat in-flight bulk/single acks as dismissed for projection until the worker fails.** Poll, finalize (`_sync_unread_completed_agents`), and `_refresh_notification_count` must not put those identities back. | This is the flake. Optimistic UI plus “notification store is source of truth” without a pending-ack fence means `,u` works for one frame and then undoes itself. |
| A5 | **Ack complete must not re-read the full notification snapshot on the UI thread.** Keep the surgical cache edit already in `_remove_agent_completion_notifications_from_cache`. If the indicator needs counts, use the count-only API off-thread (`_read_notification_counts_from_provider` / `_refresh_notification_count_async`). | The screenshot header shows `inbox: 7103`. `_complete_unread_notification_dismissal` currently calls sync `_refresh_notification_count()`, which parses that snapshot on the UI thread via `call_from_thread` and then re-reconciles every agent row. |
| A6 | **`,j` / `,J` must not call `_refresh_current_tab()`.** After a successful jump, refresh highlight + unread chrome with `defer_detail=True`. On miss, toast only. | `_refresh_current_tab()` on Agents calls `_refresh_agents_display()` with **default `defer_detail=False`**, which runs `_apply_agent_detail_update` and `hydrate_agent_attempt_history` (artifact-dir stats) on the same keystroke the jump already deferred. |
| A7 | **A jump that must expand a collapsed tribe rebuilds that one panel, not the whole tab.** | `list_changed=True` currently remounts every tribe, including the already-correct expanded `@default`. |
| A8 | **`,u` marks the same set `,j` can jump to:** loaded agent-nodes in `_unread_completed_agent_ids` with terminal status, including collapsed-tribe members and off-tab query-result rows. | Today `,j` walks off-tab `_agents_query_result` and collapsed clans; `,u` only intersects the loaded roster. “Mark all unread nodes” as spoken does not match `mark_all_unread_done_agents_read` if a `U22` lives on `@athena` while `@default` is focused. |
| A9 | **Leader footer unread/stopped probes stay off the candidate builder.** `bool(_unread_completed_agent_ids)` plus a generation counter is enough to show `,u` / `,j` in the footer. Rebuild candidates only when jumping. | Entering leader mode already calls `_has_unread_completed_agent()` → `_unread_timed_jump_candidates()`, whose cache key includes a status tuple over the whole roster. |
| A10 | **Row-patch lookup is identity-indexed.** Stop using `self._agents.index(agent)` per changed row. | O(n) per unread identity, and object-identity `index` fails if the patched Agent is a different instance than the list slot. |
| A11 | **Profile first on a live session of this shape** (collapsed tribes, hundreds of agents, thousands of inbox rows). Do not add a new abstraction from a guessed bottleneck. | `tui_perf.md`: “Perceived causes are usually wrong.” The stall watchdog and `agents.refresh_display` / `agents.refresh_panel_highlights` spans will confirm the collapsed-patch fallback and the `,j` detail path. |
| A12 | **No feature flag.** This is a hitch and a correctness bug on the default Agents tab. | Occupancy and inbox size are already production-scale in the attached screenshot. |

A smaller adjustment I am *not* taking in v1: making unread a fully derived live query over the notification store with no in-memory set. The in-memory set is the right cache; the bug is letting the store projection win while an ack is in flight.

---

## 1. What the screenshot actually shows

The capture is `sase tui` `v0.17.1+1848.g28efa6f84`, Agents tab, grouping **by status**, auto-refresh **9s**.

Headline chrome:

- Info chip: **27 unread** (gold), on a roster of **284** agents (3 running, 28 waiting, 5 failed, 146 done).
- Inbox: **7103** notifications (`inbox: 7103 #22`).
- Load: 3/8 runners.

Where those 27 unread live:

| Surface | Unread |
| --- | --- |
| Expanded `@default` tribe (21 agents, focused) | none |
| Collapsed `@epic` tribe (174 agents) | **U21** |
| Collapsed `@job` tribe (9 agents) | **U6** |
| Sum | **27** |

The unread problem on this frame is not “the focused list is stale.” It is “almost every unread node is inside a **title-only collapsed tribe**.” `,u` that tries to patch those nodes as if they had rows will miss, rebuild, or both. `,j` that wants to select one of them must expand `@epic` or `@job` and paint that tribe.

The screenshot is consistent with `,u` having been pressed and the chrome not moving. It is also consistent with `,u` having cleared in-memory unread for one frame and notification reconcile putting it back before the PNG was taken. Both are predicted by the code paths below; a stall trace from that session would distinguish them. Either way the user-visible contract failed.

---

## 2. How unread is supposed to work today

Unread is not a stored agent field. It is a **session set** `_unread_completed_agent_ids` projected from active completion notifications, plus manual `U` guards (`_manual_unread_agent_ids`). `tui_perf.md` and `_loading_finalize._sync_unread_completed_agents` say the notification store is source of truth.

User-facing actions:

| Key | Action | Intended UI |
| --- | --- | --- |
| `U` | Toggle manual unread on the focused agent-node | Patch that row |
| `,j` | Jump to next unread terminal agent-node by recency, then ack it | Reveal + select + clear that marker |
| `,u` | Bulk-toggle: mark the current terminal unread batch read, or undo | Clear every matching marker; second press restores |

Ack path (`sase-124.5`):

1. Mutate `_unread_completed_agent_ids` on the UI thread.
2. `_repaint_changed_unread_rows` → `_patch_unread_completed_agent_changes`.
3. `_schedule_unread_notification_dismissal` → `run_worker(thread=True)`.
4. Worker calls `dismiss_agent_completion_notifications_matching_agents`.
5. `call_from_thread(_complete_unread_notification_dismissal)`.

That shape matches `tui_perf.md` rule 3 (optimistic UI → off-thread persist → UI-thread complete) **except** it uses a Textual worker, not a durable Proc — which is the correct choice for an in-process store write.

The contract already documents a limitation the screenshot trips over: `,u` only marks **currently loaded agent-nodes** (`is_agents_tab_agent_node` ∩ terminal status ∩ `_unread_completed_agent_ids`). Clan containers, monitors, gates, named procs, and session-member children are not countable agent-nodes. Collapsed-tribe **members** that are still in `_agents_with_children` should be marked. Their **rows** are not in any widget.

---

## 3. Critique of “put expensive work in a proc”

### 3.1 Which “proc”?

SASE uses that word for three different things:

| Thing | What it is | Right for unread? |
| --- | --- | --- |
| Durable SASE Proc | Argv supervised into `~/.sase/procs/procs.jsonl`, Procs tab, killable | No |
| TUI durable-op helper | `_submit_durable_proc` / `submit_agent_cleanup` / `submit_patch_operation` | No, for this |
| Textual worker / pump-free task | `run_worker(thread=True)` or `spawn_pump_free_task` | Yes, for persist and snapshot I/O |

The glossary Proc is the first one. `tui_perf.md` rule 3 names the second for **agent launch, kill/dismiss persistence, Patch actions** — operations that already have argv, dedup, and a result file. Unread ack is the third, and is already wired that way.

### 3.2 Why a durable Proc makes this worse

`_submit_durable_proc` always takes an argv, records a row, and defaults `reload_on_complete=True`. On complete it is built to refresh the surface from disk. Unread chrome does not need a subprocess, does not need a Procs-tab row, and must **not** reload Agents after a badge change.

Even a custom `reload_on_complete=False` Proc still pays:

- `procs.jsonl` append + observer tick
- concurrency-key / duplicate toast machinery
- an extra process vs a Rust FFI write that already has a counts-only API (`apply_notification_state_update_counts`)

That overhead is fine for “kill these 40 agents.” It is absurd for “the gold `U21` on a collapsed title should become `D127`.”

### 3.3 Why “background everything slow” misses the hitch

The expensive work on `,u` / `,j` is mostly **already on the UI thread after the state change**:

- `_try_patch_agent_row` → `self._agents.index(agent)` (object identity, O(n) per row)
- collapsed panel: `widget._agents == []` → patch returns False → **full list rebuild**
- `_refresh_agent_panel_titles` + `_update_agents_info_panel` + tribe summary
- `,j` leader handler: `_refresh_current_tab()` → undebounced detail
- complete-handler: full inbox snapshot parse + `_reconcile_unread_from_cached_notifications`

Moving the rebuild into a worker just means `call_from_thread` still runs the rebuild on the pump, plus you now race selection (`tui_perf.md` rule 4: re-capture UI state after every await). The 13 s config-glob freeze in `tui_perf.md` rule 8 is the cautionary tale: render-path work does not get faster by being scheduled; it gets faster by not running.

### 3.4 What *is* already correctly off-thread

Give `sase-124.5` credit. `_acknowledge_agent_unread` patches **before** the store write; tests assert `notification_dismiss` is not called until the worker body runs. Failure restores the marker and toasts. That is the right persist design. The remaining bugs are “the UI thread still does a rebuild and then lets poll overwrite the optimistic set.”

---

## 4. Why `,u` looks like a no-op on this frame

Three independently sufficient bugs; they stack.

### 4.1 Collapsed tribes have no rows, so bulk mark falls back to a full rebuild

`AgentList.render_collapsed()` does `self.clear_options(); self._agents = []`. A collapsed `@epic` / `@job` is a border title with urgency chips, not 174 Options.

`_try_patch_agent_row` then:

1. Finds the agent in the **app** roster (`self._agents.index(agent)`).
2. Resolves the panel widget.
3. Computes `local_idx`.
4. Hits `local_idx >= len(widget._agents)` because that list is empty.
5. Returns False with fallback reason `panel_membership_change`.

`_patch_unread_completed_agent_changes` treats any failed patch as “rebuild the whole Agents tab” (`_refresh_agents_display(list_changed=True)`). On this screenshot that means remounting `@default` (21 rows, BY_STATUS banners), `@epic` (collapsed), `@job` (collapsed), and every other tribe, just to change two title chips.

If that rebuild is slow enough, the screenshot is the pre-rebuild frame. If `_panel_content_is_unchanged` decides collapsed widgets need no paint because grouping mode matches, titles can even stay stale after the rebuild.

**Fix:** unread-only diffs call `_refresh_agent_panel_titles()` (already written for “transient numeric chips”), `_update_agents_info_panel()`, and `_update_agents_header()` / tab strip. They never call `_try_patch_agent_row` for identities whose panel is collapsed, and they never take the list-rebuild fallback for badge-only changes. Visible rows still `patch_agent_row`.

Note: BY_STATUS `_status_row_patch_is_safe` compares status bucket, name root/prefix, and launch anchor — **not** unread. An unread→read change on an expanded Done row is already a legal in-place patch. The fallback is not because grouping membership changed; it is because collapsed widgets have no rows.

### 4.2 Optimistic clear is not fenced against projection

`_reconcile_unread_from_completion_notifications` rebuilds `_unread_completed_agent_ids` from active completion keys in the snapshot. Any still-active matching notification puts the identity back. Callers:

- Notification poll (`_poll_agent_completions_once`) — does **not** consult `NavigationGate`
- Load finalize (`_sync_unread_completed_agents`) — every Agents refresh apply, including the 9s tick in the screenshot
- `_refresh_notification_count` → `_reconcile_unread_from_cached_notifications` — the ack complete-handler itself

Timeline that produces “I pressed `,u` and nothing happened”:

1. `,u` clears 27 identities, schedules one bulk dismiss worker, starts a full rebuild.
2. Poll or the 9s refresh reads the **pre-dismiss** snapshot (7103 rows; worker not done).
3. Reconcile restores all 27.
4. Worker finishes; complete-handler surgically drops cache rows, then **re-reads the whole snapshot on the UI thread** and reconciles again.

If dismiss keys match, step 4 should eventually clear chrome — after a hitch. If any completion notification uses a different `(cl_name, raw_suffix)` than `_notification_keys_for_agents` produced (clan/session projection vs member), those rows stay unread forever and `,u` looks like a no-op even after persist.

`_pending_bulk_read_agent_ids` is an undo snapshot, not an in-flight fence. Reconcile that *adds* unread even invalidates undo (`_invalidate_bulk_read_undo`). So a raced poll both restores the gold badges and steals the second `,u` (undo).

**Fix:** pending-ack set. Projection may add unread only for identities not in that set. Worker success removes them from pending; worker failure restores markers (already implemented) and drops them from pending.

### 4.3 Tab-strip chrome is missing from the patch path

`_patch_unread_completed_agent_changes` updates rows, panel titles, the info chip, and the focused tribe summary. It does **not** call `_update_agents_header()` / `_refresh_agent_tab_strip()`. Tab-strip `U#` is projected from `_unread_completed_agent_ids` plus `_agents_query_result` in `_agent_tabs_switch_strip.py`. After a successful in-place bulk mark, collapsed titles and the info chip can move while `@athena … U22` stays until some other refresh. The screenshot’s strip is part of the “didn’t work” read.

**Fix:** the unread chrome function is one helper: info chip, every panel title, tab strip, visible row patches. Call it from bulk mark, single ack, restore, and failed-persist rollback.

### 4.4 Leader NOOP refresh vs success non-refresh

On `MARKED_READ` / `RESTORED_UNREAD`, the leader handler toasts and returns **without** `_refresh_current_tab()`. That is correct *if* the patch path updates all chrome. On `NOOP` it toasts “No unread completed agents” and **does** refresh the tab. If the roster filter missed collapsed/off-tab identities while the info chip still showed 27, the user gets a lying toast plus a hitch. A1/A8 close that.

---

## 5. Why `,j` is “always very slow”

This is a different bug from `,u`, with a clearer smoking gun.

### 5.1 The leader handler undoes deferred detail

```165:171:src/sase/ace/tui/actions/agent_workflow/_leader_mode.py
        if key == leader_keys["jump_to_next_unread_done_agent"]:
            ...
                if not self._jump_to_next_unread_done_agent():
                    self.notify("No unread completed agents")
            self._refresh_current_tab()
            return True
```

`_jump_to_next_unread_done_agent` already:

- expands a collapsed panel or clan when needed
- acks the target
- calls `_refresh_agents_display(..., defer_detail=True)` on the heavy paths

Then `_refresh_current_tab()` → `_refresh_agents_display()` with **both defaults false**. That runs `_apply_agent_detail_update` on the same tick. `_apply_agent_detail_update` calls `hydrate_agent_attempt_history`, which list/stats `artifacts/attempts/<N>/` for the selected agent — work the normal `j`/`k` path deliberately deferred (`_refresh_agents_display_debounced`, `tui_perf.md` rule 7).

Ordinary `j`/`k` never do this. `,j` always does. That matches “always very slow” even when the unread row is already visible.

`,J` (next stopped) has the same trailing `_refresh_current_tab()`. Fix both.

### 5.2 Jumping into this screenshot expands a 174-agent tribe

With 21 unread in collapsed `@epic`, the first `,j` must `_expand_agent_panel("@epic")` (or the clan-fold path: expand + `_refilter_agents` + identity scan) and then `list_changed=True` for the whole tab.

Needed: rebuild **the expanded panel only** (`_refresh_affected_panel_widgets` / `_refresh_focused_agent_panel`). `@default` did not change membership.

### 5.3 Candidate discovery is too expensive for the footer

`_unread_timed_jump_candidates` cache key includes:

- `id(_agents)`, `id(_agents_with_children)`
- `frozenset(unread_ids)`
- every fold level
- grouping mode, search query, live-query facade ids
- **a tuple of (identity, status, start, stop, tree_parent) for every non-clan agent**

Building the key is already O(roster). A cache miss walks visible rows, `prospective_clan_members`, and off-tab `_agents_query_result`. `_has_unread_completed_agent()` (footer, every leader-mode entry) calls this. So `,` hitchs, then `j` hitchs again.

**Fix:** footer uses `bool(_unread_completed_agent_ids)` (and maybe a cheap “any terminal still loaded” flag updated when the set or roster changes). The candidate list is built once per jump, keyed by a generation counter bumped on unread mutation, fold change, tab switch, and roster apply — not by hashing every timestamp.

### 5.4 Ack-on-jump stacks persist hitches on a navigation key

Each `,j` also schedules `agents-unread-ack` and later runs the sync snapshot complete-handler (section 4.2). Rapid `,j` / `,j` / `,j` through 27 unread is 27 store writes and 27 UI-thread snapshot parses unless coalesced.

**Fix:** coalesce in-flight acks into one worker that dismisses a set of keys (bulk mark already sends one list). Jump adds the identity to the pending-ack set immediately; a single worker flushes the set.

---

## 6. Established TUI performance rules this work must reuse

Do not invent a fourth off-thread mechanism. The rules that already apply:

| Rule (`tui_perf.md`) | Application here |
| --- | --- |
| 1. Never block the event loop | Sync `_refresh_notification_count` in `call_from_thread` is a rule-1 break at inbox=7103 |
| 2. Off the loop ≠ off the pump | `asyncio.to_thread` inside a timer/poll callback still hitchs; persist already uses a thread worker |
| 3. Durable procs for launch/kill/Patch | Unread ack is not that class; keep the worker |
| 4. Re-capture UI state after await | Pending-ack set + identity-based chrome, not captured indices |
| 5. Cached data first, then background reload | Unread chrome from the in-memory set; store is backup |
| 6. Selective updates over full rebuilds | Collapsed-title unread is the poster child |
| 7. Debounce detail, never the highlight | Delete `_refresh_current_tab()` from `,j` |
| 8. Render paths never stat/glob | `hydrate_agent_attempt_history` must stay off the jump keystroke |
| 13. NavigationGate | Poll reconcile should defer while the user is in a `,j` / `,u` burst |
| Measure, don’t guess | Stall watchdog + `agents.refresh_display` spans + `SASE_TUI_PERF` |

`spawn_pump_free_task()` is the right wrapper if complete-side count refresh needs to be async without sitting on the Textual pump. It is not a Proc.

---

## 7. Recommended implementation (phased)

### Phase 0 — measure the live hitch (hours, not a design)

On a session like the screenshot (do not wait for a repro fixture first):

- `SASE_TUI_TRACE=1` and press `,` then `u`, then `,` then `j`.
- Read `~/.sase/logs/tui_stalls.jsonl` for `tui_hitch` / `tui_pump_hitch` stacks naming `_refresh_agents_display_impl`, `_apply_agent_detail_update`, `_read_notification_snapshot_from_provider`, `_unread_timed_jump_candidates`.
- `SASE_TUI_PERF=1` for key-to-paint on Agents.

This phase exists so Phase 1 is not another guessed off-thread wrapper. I expect the stacks to name the collapsed rebuild and the `,j` detail path. If they instead name the Rust snapshot parse, Phase 2 still holds; Phase 1’s rebuild fix remains necessary for collapsed chrome.

### Phase 1 — chrome correctness and `,u` (the screenshot)

One helper, e.g. `_apply_unread_chrome(before_ids)`, used by bulk mark, single ack, undo, and persist rollback:

1. Compute `changed = before ^ after`.
2. For each changed identity whose panel widget is **expanded**, `patch_agent_row` via an identity index (not `list.index`).
3. For changed identities on **collapsed** panels, do not patch rows.
4. Always: `_refresh_agent_panel_titles()`, `_update_agents_info_panel()`, `_update_agents_header()` (tab strip).
5. **Never** `_refresh_agents_display(list_changed=True)` for unread-only diffs. If a visible patch fails for a real reason (width growth), rebuild **that panel only**.

Fence:

- `_pending_unread_ack_ids: set[identity]`
- Reconcile skips those identities (treat as read).
- Bulk mark adds the batch before scheduling the worker.
- Worker success: drop from pending; surgical cache edit; update the notification indicator from the edited cache (no full snapshot).
- Worker failure: restore (existing), drop from pending, re-run chrome.

Tests to add (the current bulk-mark tests use a harness whose patch always succeeds and whose roster is fully visible):

- Bulk mark with two collapsed tribes totaling 27 unread updates titles + info chip, does not call `_refresh_agents_display(list_changed=True)`, does not expand panels.
- Reconcile during in-flight bulk ack does not restore those identities.
- Complete-handler does not call `_read_notification_snapshot_from_provider` on the UI thread.
- Tab strip `U#` drops on the same call as the info chip.
- Off-tab unread in `_agents_query_result` is included in `,u` (A8).

### Phase 2 — `,j` feels like `j`

1. Remove `_refresh_current_tab()` from the unread and stopped leader branches. Miss → toast. Hit → existing jump refresh with `defer_detail=True` (or the debounced helper).
2. Panel expand → `_refresh_affected_panel_widgets({that_key})`, not a tab-wide rebuild.
3. Footer `_has_unread_completed_agent` does not build jump candidates.
4. Coalesce ack workers so a `,j` burst is one dismiss of N keys.

Tests:

- Leader `,j` on a visible unread row does not call `_apply_agent_detail_update` / `hydrate_agent_attempt_history` on that tick.
- `,j` into a collapsed tribe rebuilds only that tribe’s widget.
- Repeated `_has_unread_completed_agent` does not allocate a status-signature tuple over the roster.

### Phase 3 — only if traces still show snapshot cost

If Phase 0/1 leave a hitch inside `read_notification_snapshot` at 7k inbox:

- Complete-handler stays cache-only (Phase 1).
- Poll already has `_read_notification_snapshot_guarded` + `asyncio.to_thread`; keep it, and make it honor `NavigationGate`.
- Consider a notification-store API that dismisses-by-agent-keys **and returns counts** so Python never materializes 7k `Notification` objects to update a badge. That belongs in sase-core if a web/CLI surface would need the same counts (rust-core boundary). The TUI must not grow a second Python JSONL parser.

Still no durable Proc.

---

## 8. What I would not do

- **A generic “TUI background proc” for every slow function.** It fights rules 1–2 and 6–7 and will get used on paint paths.
- **Making `,u` expand every collapsed tribe with unread.** That is a denial-of-service on the screenshot’s `@epic` panel.
- **Dropping optimistic UI and awaiting the store on the keystroke.** That is the pre-`sase-124.5` hitch.
- **Counting unread from the inbox indicator (`#22`) instead of agent-node projection.** Agent unread and notification-tab unread are related but not 1:1 (manual `U`, session containers, muted rows). Keep the agent-node set; fence it.
- **A new grouping bucket for unread.** BY_STATUS already treats unread as a chip on Done/Failed. A fourth banner would force membership rebuilds on every ack — the failure mode `_status_row_patch_is_safe` exists to avoid.

---

## 9. Suggested acceptance checks

Use the screenshot’s shape as the fixture, not a 3-row unit list:

| Action | Pass |
| --- | --- |
| `,u` with 21 unread in collapsed `@epic` and 6 in `@job` | Info chip 27→0; both titles drop `U#`; no tribe expands; no `display_full_rebuild` trace; UI-thread p95 < 16 ms |
| Notification poll 50 ms later | Chrome stays cleared |
| Second `,u` | Restores the same 27 (undo still works because reconcile did not steal the snapshot) |
| `,j` to a visible unread row | Highlight + chip/title update; detail waits for the 150 ms debounce; no attempt-dir stat on that tick |
| `,j` to unread inside collapsed `@epic` | Only `@epic` expands and rebuilds; `@default` widgets are not remounted |
| `,` (leader) with 27 unread | Footer shows `,j` / `,u` without building a 284-row status signature |
| Persist failure | Markers and chrome restore; error toast; no silent flake |

---

## 10. What to implement

The screenshot is a collapsed-tribe unread problem sitting on a 7k-row inbox, not a missing background-job type.

**Do this:** optimistic unread set + pending-ack fence + chrome-only patches + stop `,j` from applying undebounced detail.

**Do not do this:** durable Procs, “background any hitch,” or a full Agents rebuild to change a title chip.
