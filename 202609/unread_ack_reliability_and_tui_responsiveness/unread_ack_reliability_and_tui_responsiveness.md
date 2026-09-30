# Unread acks that don't stick, a TUI that can't keep up, and why a proc isn't the fix

**Type:** consolidated research report (lead researcher)
**Date:** 2026-09-30
**Inputs:** five independent reports in this directory (`__cdx`, `__cld`, `__grk`, `__mus`,
`__gem`), plus the lead's own verification against the live logs, the notification store,
the proc store, the sase checkout, and the linked `sase-core` checkout.
**Question:** `,u` (mark all unread read) on the Agents tab "didn't seem to work"
(screenshot `~/tmp/screenshots/20260930_060248.png`). Unread indicators feel flaky and
always slow, including `,j` (jump to next unread). Should expensive work move into a
background proc? What should be built instead?

---

## Bottom line

1. **`,u` worked, and then the notification store itself was reverted.** The optimistic
   clear ran, the background write succeeded, and a durable revert followed. The most likely
   writer is the **remote-attention inbox reconciler**. About once a minute it reads the
   whole 19 MB store outside the lock and writes *every* row back through a merge where the
   caller's copy wins. Any dismissal committed in between is silently undone. Only one
   report (cld) found this. The other four blamed a TUI-side race, which is real but
   heals itself within seconds, so it cannot explain a revert that lasted 5 minutes (§1).
2. **Most of the slowness isn't unread code.** In the last 4.1 h the TUI's main loop was
   frozen for about **20 minutes**: 358 hitches, median 3.4 s, max 6.1 s. The top sources
   are the 1 Hz runtime-row repaint and the fleet-projection signature. Unread paths add real
   costs of their own on top of that: a synchronous full-store read after every ack, a
   per-row patch loop, a full-rebuild fallback for collapsed panels, and an undebounced
   detail render on `,j`. But a `,j` pressed behind a 3 s freeze is slow no matter what `,j`
   does (§2).
3. **A proc is the wrong tool for acks.** All five reports agree, and the lead's measurements
   back them up. The store write is *already* on a background thread. Procs cost at least
   about 1 s end-to-end, and they would **widen** the race windows that broke `,u`. The
   instinct itself is sound: nothing slow belongs on the UI thread. It also matches
   `tui_perf.md` rule 3. It just aims at the wrong work (§3).
4. **Recommendation:** fix correctness at the store first. That means small, mostly one-repo
   changes to the attention reconciler, then an atomic field-scoped upsert in `sase-core`.
   Next, add a sequence-fenced pending-ack overlay in the TUI, and make unread chrome
   updates O(changed visible rows) with no full rebuilds and no UI-thread store reads. Then
   take on the two periodic stall sources, which gives the biggest *felt* speedup. Push the
   unread/ack domain into `sase_core`, and shrink the store, only after that (§6).

---

## 1. What actually happened to `,u`

### 1.1 Timeline (UTC; local = UTC−4)

| Time | Evidence | Source |
|---|---|---|
| 10:02:14 | `Launching agent…` | `~/.sase/logs/tui_toasts.jsonl` |
| ~10:02:19.5 | `,u` pressed (watchdog `last_keypress_age_s` 1.77 at 10:02:21) | `tui_stalls.jsonl.1` |
| 10:02:21 | Toast **`Marked 27 completed agents read`**. No error or "restored unread" toast, so the write succeeded. | toasts |
| 10:02:21.5 → 22.6 | 2.52 s pump hitch in `_complete_unread_notification_dismissal` → `_refresh_notification_count` → **synchronous full snapshot read** | stalls |
| 10:02:48 | Screenshot: header `27 unread`, machine chip `athena 204 F5 U27`, `@epic U21`, `@job U6` | screenshot |
| ~10:04:09 | A notification poll ran `_reconcile_unread_from_completion_notifications` on a **fresh disk read** | stalls (recovery stack) |
| 10:07:05 | Second `,u`: **`Marked 27 completed agents read`**, the same 27 | toasts |
| 10:20:12 | `Marked 1 completed agents read`: the second press stuck | toasts |

The screenshot's own facts settle several disagreements between the reports:

- There are **204** agents. grk's "284" is a misread.
- `@epic` is **expanded**; its 21 unread are members hidden inside collapsed clan rows.
  `@job` is collapsed (U6). grk said `@epic` was collapsed.
- The inbox chip reads `?103` (a glyph plus 103), not "7103". The live store has 3,885 rows,
  1,040 of them active, totalling 19 MB.

### 1.2 Why the revert must have happened in the store

This is the deciding argument. It comes from the lead's code reading, which extends cld.

- `_reconcile_unread_from_completion_notifications`
  (`_notification_unread_projection.py:147-210`) **replaces** the unread set wholesale from
  the snapshot it is given (`unread_ids.clear(); unread_ids.update(next_unread)`).
- Every poll reads the store fresh: `_read_notification_snapshot_guarded` → `asyncio.to_thread`
  → Rust direct read, with no stat cache.
- A TUI-only race, where a stale snapshot re-adds rows, therefore heals on the next fresh
  poll. A fresh poll did reconcile at about 10:04:09. Yet at 10:07:05 the TUI still held
  exactly 27 unread.
- So at around 10:04 the store itself held those 27 completion notifications as
  `dismissed=false`.

Only two mechanisms can produce that state:

| Hypothesis | Verdict |
|---|---|
| **Lost update by a whole-store read-modify-write writer** (cld) | **Leading explanation.** See §1.3. |
| Rust dismiss matched 0 rows because of a key mismatch | Unlikely. The second press used the same key derivation and stuck. The completion callback also went down its "something changed" branch. |
| TUI pending-ack race: poll or finalize re-projects from a pre-dismissal snapshot (cdx, mus, grk, gem) | **Real, but secondary.** It causes seconds of flicker, not minutes, and must still be fixed (§1.4). |
| Collapsed-clan members excluded from `,u`; exact-match status predicate skips `FAILED (…)` (gem) | **Refuted.** The toast count (27) equals the header count (27), and both use the same predicate (`DISMISSABLE_STATUSES`). `FAILED (RETRIED)` rows count toward neither. |
| `,u` toggle/undo swallowed the press (gem) | **Not this incident**, since both presses *marked*. It is still a real UX trap when the UI lags (§4, R5). |

### 1.3 The lost-update writer (verified)

`src/sase/dispatch/attention_inbox.py:129-209`, `reconcile_remote_attention_inbox`:

```python
rows = load_notifications(include_dismissed=True)   # whole store, NOT under the store lock
output = list(rows)
...                                                 # edit remote-attention rows only
if outcome.changed:
    rewrite_notifications(output)                   # hands back EVERY row
```

`sase-core` `crates/sase_core/src/notifications/store.rs:1044-1067`:
`merge_and_rewrite_notifications_unlocked` treats the rewrite as a merge in which "caller's
rows win on id collision". Every completion row the reconciler read is in its input, so a
dismissal committed between its read and its write is overwritten with the stale
`dismissed=false`. The merge protects concurrent *appends*, not concurrent *state changes*.

Three findings from the lead turn this from "possible" into "expected":

- **It rewrites almost every minute.** `_coerce_pending_entry` stamps each entry with the
  poll's `observed_at_unix` (`attention_inbox.py:306`). That value lives inside `action_data`,
  so `_refresh_existing_notification(...) != existing` on nearly every poll. In the live
  store, **100 of 106 active remote-attention rows carry the most recent minute's
  `observed_at`**. The TUI therefore rewrites the full 19 MB store on roughly every 60 s
  network poll (`_remote_attention.py`, `asyncio.to_thread(reconcile_remote_attention_inbox)`).
- **Its window is wide.** It runs in a TUI thread and does substantial Python work (thousands
  of `Notification` objects and a list rebuild) while competing for the GIL with a main
  thread that is frozen about 8% of wall time. cld measured about 280 ms on an idle host;
  under this load the window is plausibly seconds per minute.
- **It is the only routine whole-store rewriter.** The only other caller of
  `rewrite_notifications` is the rare agent-name migration (`agent/names/_migration.py`).

Confidence: **high** that a store-level revert happened; **medium-high** that this writer
caused it. The store keeps no dismissal timestamps, so the exact interleaving can't be proven
after the fact. It also fits "flaky in general": an ack is lost only when it lands inside
the reconciler's window.

### 1.4 TUI-side flakiness (secondary, confirmed in code)

1. **No pending-ack fence.** Three paths re-project unread from a snapshot:
   - the poll (`_notification_polling.py:316`);
   - list finalize (`_loading_finalize.py` → `_sync_unread_completed_agents`);
   - `_reconcile_unread_from_cached_notifications`, which the ack completion calls itself.

   None of them consults in-flight acks. `_pending_bulk_read_agent_ids` is only an undo
   record, and a reconcile that re-adds rows *invalidates* the undo.
2. **Stale snapshots can overwrite fresher ones.** `_set_notification_snapshot_cache`
   (`_notification_provider.py:206`) stores whatever was read, with no ordering check.
3. **Chrome gaps.** The `,u` success branch skips `_refresh_current_tab()`
   (`_leader_mode.py:195-209`), and the patch path never refreshes the machine and tab strip
   (`_update_agents_header`). `athena … U27` can lag even when the state is correct.
4. **Latent key divergence** (cld). Python treats an empty `raw_suffix` as "no suffix"; the
   Rust matcher treats `""` literally. No live rows have this shape, but test helpers build it.

---

## 2. Why unread indicators feel slow

### 2.1 Layer 1: the main thread is saturated by periodic work (largest felt effect)

The lead re-measured `~/.sase/logs/tui_stalls.jsonl{,.1}` over the last 4.1 h (06:38–10:42Z):

- **358 loop hitches, 20.2 min frozen** (p50 3.44 s, max 6.08 s), plus 122 pump hitches
  totalling 6.2 min.
- By stack, the top sources are:
  - the **1 Hz countdown tick → `_patch_agent_runtime_rows` → `patch_row`**, which
    recomputes whole-roster wait-status maps (`collect_agent_wait_status_maps`, uncached) for
    every clan-container patch;
  - **fleet refresh → `_agents_projection_signature`**, a recursive deep-freeze of every field
    of every agent, run to decide whether to reproject.
- Unread-specific frames appear in only about 25 of 481 hitch rows (~5%).

**This changes the reading of the second `,u`.** cdx attributed a ~2.9 s stall to the
unread patch loop. In fact the 2.88 s pump hitch *started* at 10:07:03.95 inside the
fleet-projection signature and only *recovered* inside `_patch_unread_completed_agent_changes`.
The key press waited behind unrelated work first, then ran its own O(K·N) patch. Both costs
are real, and the first is larger.

### 2.2 Layer 2: costs in the unread paths themselves (all confirmed in code)

| Cost | Where | Effect |
|---|---|---|
| Synchronous full store read on the UI thread after every ack | `_unread_state.py:455` → `_refresh_notification_count` (`_notification_polling.py:335`) | 1.5–2.5 s live pump hitches. It always misses the cache because the worker just wrote the file. An async guarded variant already exists and isn't used here. |
| Collapsed panels have no rows, so a patch forces a **full Agents rebuild** | `render_collapsed()` sets `widget._agents = []`; `_try_patch_agent_row` returns False at `local_idx >= len(widget._agents)`; `_patch_unread_completed_agent_changes` then calls `_refresh_agents_display(list_changed=True)` | Any unread change in collapsed `@job` remounts every tribe panel just to change a title chip (grk). |
| Per-row patch loop | `_try_patch_agent_row`: `self._agents.index(agent)` (O(N)), `_agent_panel_title` with recursive lane counts, `_update_agents_info_panel` for *every* row | O(K·N) per bulk ack. The live stack at 10:07:05 sits here. |
| `,j` always runs an undebounced detail render | `_leader_mode.py:165-171` calls `_refresh_current_tab()` after the jump already refreshed with `defer_detail=True` | Detail render p95 is about 0.5 s, max 2.3 s (cld), on every `,j`. `,J` does the same. |
| Footer probe and candidate cache are O(N) even on a hit | `_has_unread_completed_agent` → `_unread_timed_jump_candidates`; the key tuples every agent's identity, status, and times plus `frozenset(unread_ids)` (`_unread_jump_candidates.py:57-98`) | Pressing `,` already pays. Each `,j` ack changes `unread_ids`, so the *next* `,j` always misses and rebuilds prospective clan trees. |
| Projection index rebuilt 4–6× per action, with an O(owned²) dedupe | `agent_node_projection_index` in toggle, reconcile, patch, finalize (`agent_nodes.py:195`) | A 2.3 s live freeze on a `,j`-into-collapsed-clan path (cld). |
| Reconcile runs on the UI thread | poll tail, finalize | 16 hitch rows with reconcile frames |

### 2.3 Layer 3: the store

- 19 MB and 3,885 rows. Every read is a full parse, and every dismiss rewrites the whole file
  under the exclusive lock. Both already run off-thread with the GIL released. The ack write
  uses the counts-only variant, so the *worker* is not the UI problem. The cost reaches the UI
  through synchronous reads, snapshot-to-Python conversion under the GIL, and longer
  lost-update windows.
- **Correction to gem:** running compaction now would free **0 bytes**. All 12.7 MB of
  dismissed rows are under the 14-day archive threshold. Of the 6.0 MB of active rows,
  **4.7 MB is `wait_checks`** (large `plus_ones` and `action_data`). Shrinking the store
  requires a retention-policy change and a payload diet, not a compaction run.

---

## 3. Critique of "use a proc for any expensive work"

**The goal is right and the mechanism is wrong.** All five reports reject procs for this.
The lead's evidence:

- **The expensive work isn't where a proc would go.** The store write already runs in a
  Textual thread worker (`run_worker(..., thread=True, name="agents-unread-ack")`, added by
  `sase-124.5`). What blocks the UI is:
  - UI-thread work *around* the write: the synchronous post-ack read, per-row patching, and
    rebuilds;
  - unrelated periodic freezes.

  A proc's result still has to be applied to widgets on the UI thread.
- **Latency floor.** The lead measured the proc store: the fastest successful procs take
  **~1.0 s end-to-end** (0.26 s just to start), and the one recorded
  `sase notify apply-state-many read` took **2.62 s**. Interactive feedback needs under
  16–100 ms.
- **It widens the races.** A 250 ms write becomes a 1–3 s write, which lengthens both the
  store lost-update window and the TUI's optimistic window. Today's failure *is* a race;
  slower writes lose races more often.
- **Operational mismatch.** Rapid `,j` would be rejected: the existing notification-state
  procs share one `("notification-state",)` concurrency key, which refuses overlapping
  submits. `_submit_durable_proc` defaults to `reload_on_complete=True`, which reloads Agents
  after every ack. The Procs tab would also fill with 50 ms bookkeeping rows.

**Where the idea is partly right** (additions not covered by most reports):

- `tui_perf.md` rule 3 *does* say: "Run slow user-initiated operations as durable procs
  (agent launches, kill/dismiss persistence, Patch actions)." The proposal follows documented
  project guidance. The distinction is that rule 3 is for operations that need durability,
  dedup, audit, and a count at quit. Unread acks are already in the shape rule 3 prescribes
  ("optimistic UI → sync worker → UI-thread on_complete"), just in-process, which is correct
  for a 250 ms idempotent write.
- **The GIL is a real limit on threads.** Background Python work still competes with the UI
  thread; cld measured about 45 ms of UI stall per background snapshot parse. The answer is to
  *not do heavy Python work on hot paths*: use caching, incremental updates, and Rust with
  the GIL released and lean return types. A cold subprocess per action is not the answer.
- **One legitimate background-process candidate:** the remote-attention inventory sync. It is
  periodic fleet maintenance that does a 19 MB read and rewrite every minute inside every TUI.
  Moving it to a service proc could be a sensible later cleanup, but **only after** its write
  becomes atomic (§6, Phase 0). Moving it first would keep the lost-update bug and hide it
  from the TUI's logs.

---

## 4. Requirement adjustments (explicit changes to the request)

> **R1 — Correctness before speed (new).** An acknowledgment (`,u`, `,j`, row-select) must
> never be reverted by another writer or by an older snapshot. Only a genuinely new
> completion may re-mark a node unread. No notification-store writer may read the whole store
> and write it back; state changes must be atomic and field-scoped under the store lock.
> *Why:* the screenshot failure is a lost update, and making things faster without this makes
> it more frequent.

> **R2 — Replace "run expensive work in a proc" with a placement rule.**
> - Nothing data-scaled runs on the UI thread or the Textual pump.
> - I/O and parsing go to in-process workers or `spawn_pump_free_task`, or to Rust with the
>   GIL released.
> - Paint, selection, and chrome stay synchronous and cheap.
> - Procs are only for durable, audit-worthy, or long-running operations.
>
> *Why:* §3. Also note that "background anything that causes a delay" would move hitches
> around rather than remove them: a worker must still marshal a rebuild back onto the pump.

> **R3 — Widen scope to the top main-thread stall sources.** Include the 1 Hz runtime-row
> patching (wait-status maps) and the fleet-projection signature. *Why:* about 20 minutes
> frozen per 4 hours. `,j` cannot feel fast while the loop is stuck for 3 s at a time.

> **R4 — Measure two moments, with budgets.**
> - **First paint** (key → optimistic paint): UI-thread work at most 16 ms p95 for `,u` and
>   for a `,j` to a visible row; at most 50 ms for a `,j` that must reveal a collapsed
>   panel or clan.
> - **Settlement** (persist and authoritative reconcile): asynchronous, no pump callback over
>   16 ms, typically under 1 s.
> - Zero synchronous store reads in any ack path, and no watchdog hitch with an unread frame.
>
> The reports proposed 16, 50–100, and 100 ms; the split above reconciles them against
> `tui_perf.md`'s 16 ms target.

> **R5 — Define `,u` precisely.**
> - "All" means every loaded unread terminal agent node across all Agents tabs, including
>   collapsed clans and tribes and off-tab query rows. It must equal the header count and
>   never expand a panel.
> - Keep undo, but make it explicit and time-bound, for example a toast reading "press `,u`
>   again within 10 s to undo".
>
> *Why:* the silent toggle turns a lag-induced double press into "restore all 27", which
> looks exactly like "it didn't work".

> **R6 — Store hygiene is in scope, but not as "run compaction".** Compaction frees nothing
> today (§2.3). Shorten live retention of dismissed rows, and put `wait_checks` payloads on a
> diet. *Why:* every full read and rewrite scales with file size, and so does the lost-update
> window.

> **R7 — No feature flag.** This is a correctness bug and a hitch fix on the default tab
> (grk).

---

## 5. Options considered

| Option | UI latency | Correctness | Cost | Verdict |
|---|---|---|---|---|
| Proc per ack or bulk ack (the proposal) | No change to UI-thread costs; ≥1 s writes; overlapping submits rejected | **Worse** (wider windows) | Medium | ✗ |
| Only make the post-ack refresh async | Removes one stall | Leaves both races | Small | Necessary, not sufficient |
| Attention reconciler writes only changed rows and ignores volatile fields | — | **Fixes the durable revert** for completion rows | Tiny | ✓ Phase 0 |
| Atomic field-scoped upsert in `sase-core` | Cheaper writes | Closes the lost-update class | Medium (cross-repo) | ✓ Phase 0 |
| Pending-ack overlay plus monotonic snapshot cache | — | Fixes the TUI flicker races | Small | ✓ Phase 0 |
| Batched chrome helper with no rebuilds, async completion, `,j` fixes | Large for unread paths | Neutral | Small–medium | ✓ Phase 1 |
| Periodic-work hot-spot fixes | **Largest felt win** | Neutral | Medium | ✓ Phase 2 |
| Lean ack and unread-index API in Rust with the GIL released | Removes 19 MB parses from hot paths | Good | Medium | ✓ Phase 3 |
| Warm helper daemon, SQLite store, free-threaded CPython | Potentially good | — | High; daemons were deleted twice before | ✗ Hold in reserve |

---

## 6. Recommended solution

Four phases, each useful on its own. No procs for acks.

### Phase 0 — make acks stick (days; highest priority)

1. **Attention reconciler quick fix (sase repo, tiny).** In
   `attention_inbox.reconcile_remote_attention_inbox`:
   - pass only the rows it **created or changed** to `rewrite_notifications`. The Rust merge
     keeps every row absent from the input, so completion rows can no longer be reverted;
   - exclude volatile fields (`observed_at_unix` inside the entry JSON) from change
     detection, so it stops rewriting 19 MB every minute.

   Residual risk: a user dismissal of a *remote-attention row that changed in the same
   poll* can still be clobbered. Step 2 closes that.
2. **Atomic upsert (`sase-core`).** Add a field-scoped upsert for the reconciler, for example
   `upsert_notifications_preserving_local_state(rows, owned_fields)`:
   - under the store lock, re-read each on-disk row;
   - apply only the reconciler-owned fields (icon, color, notes, tags, action, action_data,
     silent);
   - keep on-disk `read`/`dismissed` unless the auto-dismiss marker says otherwise, matching
     the documented intent of `_refresh_existing_notification`.

   Optionally make `rewrite` refuse `dismissed: true → false` flips unless the caller opts in.
   Bump `sase-core-revision.txt` per `docs/rust_backend.md`.
3. **TUI pending-ack overlay, fenced by read sequence (sase repo).** This lead design needs no
   cross-repo store token yet:
   - Keep a counter `_notif_read_seq`. Stamp each snapshot read with the value at the moment
     the read *started*.
   - Each ack records `pending[identity] = op_id`. When its worker finishes, it records
     `ack_done_seq = _notif_read_seq` at that moment.
   - Every reconcile path (poll, finalize, cached) treats pending identities as read.
   - A pending entry retires only after a snapshot whose `read_start_seq > ack_done_seq` has
     been applied, meaning a read that began after the write landed.
   - **Monotonic cache:** `_set_notification_snapshot_cache` ignores a snapshot whose
     `read_start_seq` is older than the cached one's.
   - On write failure, restore only the identities this operation still owns (the existing
     restore path, narrowed).
   - Stop invalidating undo when a reconcile merely re-confirms pending identities.

   With Phase 0.1–0.2 in place, a retired entry can no longer be resurrected by a reverted
   store. Without them, the overlay only hides the bug for one poll.
4. **One unread-chrome helper**, used by bulk mark, single ack, undo, rollback, and
   reconcile:
   - compute `changed = before ^ after`;
   - patch **visible** rows through an identity → (panel, local index) map, not `list.index`;
   - **skip rows in collapsed panels** and never fall back to `list_changed=True` for
     unread-only diffs. If a visible patch fails for a real reason such as width growth,
     rebuild *that panel only*;
   - refresh each affected panel title once, then the info chip, machine and tab strip, and
     tribe summary once each. Pass `refresh_info=False` through the per-row calls.
5. **Tests.**
   - A lost-update interleave: load, then dismiss, then reconciler rewrite, then assert the
     row is still dismissed. Cover this in the `sase-core` store tests and in a Python
     integration test.
   - A pending window, where a poll runs with the pre-write snapshot.
   - A stale snapshot landing after a fresh one.
   - `,u` scope across collapsed tribes, collapsed clans, and off-tab rows, with the header,
     machine chip, and titles all reaching 0 and no `display_full_rebuild`.
   - Empty-`raw_suffix` parity between Python and Rust.

### Phase 1 — make unread actions cheap (days)

1. **Ack completion never reads the store on the UI thread.** Delete the synchronous
   `_refresh_notification_count()` call and apply the outcome to the cached snapshot locally.
   Key cache removal by precomputed key set or id instead of the notifications × keys scan. If
   a resync is wanted, schedule the guarded `_refresh_notification_count_async`. Add a guard
   test that fails if `_read_notification_snapshot_from_provider` runs on the main thread
   during an ack.
2. **`,j` and `,J`:** remove the trailing `_refresh_current_tab()`; on a miss, only toast. The
   detail pane stays behind the 150 ms debounce (`tui_perf.md` rule 7). A jump that must
   expand a panel rebuilds only that panel.
3. **Footer probe:** `bool(_unread_completed_agent_ids)` plus a generation counter, with no
   candidate build.
4. **Candidate cache keyed by generation**, bumped on roster apply, fold change, tab switch,
   and query change, instead of an O(N) tuple. When `,j` acks its target, **remove that
   identity from the cached ordered list** rather than invalidating it, which removes the
   guaranteed miss on every step. A fully incremental `UnreadNavigationIndex` (cdx) is the
   follow-up only if traces still show cost.
5. **Coalescing ack writer:** one worker drains queued keys and makes one Rust call per batch,
   so five fast `,j` presses become one write. It returns changed ids through
   `call_from_thread`.
6. **Cache `agent_node_projection_index` per roster generation** and fix the O(owned²)
   dedupe.
7. **Instrument before and after:**
   - `tui_trace` spans for `leader.unread_bulk_ack`, `leader.unread_jump`,
     `unread.ack_complete`, and `agent_nodes.projection_index`, carrying workload dimensions
     (loaded agents, targets, collapsed or off-tab, store bytes);
   - `SASE_TUI_PERF` key-to-paint extended to leader keys;
   - `,u`/`,j` cases added to `tests/ace/tui/bench_tui_jk*.py` for four branches: visible,
     collapsed panel, collapsed clan, and other tab.

### Phase 2 — give the UI thread its time back (1–2 weeks; biggest felt improvement)

1. Cache `collect_agent_wait_status_maps` per roster generation. This is the #1 stall source
   through the runtime tick, and it also speeds up bulk `,u` repaints.
2. Change-only runtime-row patching and cached clan runtime aggregation.
3. Replace `_freeze_projection_value`'s deep freeze with a cheap signature: wire revisions or
   per-agent version counters.
4. Re-measure with the watchdog. Target: no hitches from the 1 Hz tick or fleet refresh at
   this roster size.

### Phase 3 — push the domain into `sase_core` and shrink the store (follow-on epic)

1. `ack_agent_completions(keys) → {dismissed_ids, generation}` and a lean
   `read_unread_completion_index()` returning only id, key, and read/dismissed, with the GIL
   released. By the Rust-core litmus test, any other frontend would need the same unread
   count, so the "which agent nodes are unread" projection plausibly belongs in Rust too.
   Store generations then replace the Phase 0 read-sequence fence.
2. Retention: shorter live retention for dismissed rows, and slimmer `wait_checks`
   `plus_ones` / `action_data`.
3. Only then reconsider a warm helper process, a SQLite store, or moving the attention sync
   into a service proc. None is expected to be necessary.

**Expected outcome:**

- Phase 0 makes `,u` durable and stops the "it came back" flakes.
- Phase 1 takes the `,j` and `,u` handlers from hundreds of milliseconds, plus a
  1.5–2.5 s post-ack freeze, down to a few milliseconds of UI work.
- Phase 2 removes most of the multi-second freezes that currently make *everything*,
  including unread navigation, feel slow.

---

## 7. Acceptance checks (use the screenshot's shape as the fixture)

| Action | Pass |
|---|---|
| `,u` with 21 unread inside collapsed clans of expanded `@epic` and 6 in collapsed `@job` | Header, machine chip, and tribe titles go from 27 to 0 on the same paint; no tribe expands; no full rebuild; UI work at most 16 ms p95 |
| Poll or finalize 50 ms later with a pre-write snapshot | Chrome stays cleared |
| Attention reconciler runs between an ack's write and the next poll | Rows stay dismissed in the store |
| Second `,u` within the undo window | Restores the same 27; the toast says so |
| `,j` to a visible unread row | Highlight and chips update immediately; detail waits for the debounce; no artifact-dir stat on that tick |
| `,j` into collapsed `@job` | Only `@job` rebuilds |
| Entering leader mode with 27 unread | No O(N) status signature built |
| Persist failure | Only this operation's identities restore, with an error toast |

---

## 8. Where the five reports disagreed, and how this report resolves it

| Topic | Reports | Resolution |
|---|---|---|
| Primary cause of the `,u` failure | cdx, mus, grk, gem: TUI stale-poll race. cld: store lost update | **cld.** Reconcile fully replaces the set from fresh reads, so a TUI race self-heals. A fresh poll reconcile at about 10:04:09 still left 27 unread at 10:07:05. The reconciler's rewrites are near-constant because of `observed_at` churn. |
| Screenshot facts | grk: 284 agents, `@epic` collapsed, "7103" inbox | 204 agents; `@epic` expanded with unread inside collapsed clans; `@job` collapsed; `?103` chip |
| `,u` targeting and status predicate | gem: members and `FAILED (…)` excluded | Refuted: toast 27 equals header 27, and both use the same predicate |
| Cause of the 10:07 stall | cdx: the unread patch loop | Mostly an unrelated fleet-signature freeze that the key press waited behind, then the patch loop |
| Compaction | gem: shrinks to under 500 KB | Frees 0 bytes under the 14-day policy; bloat is recent dismissals plus `wait_checks` |
| Latency budgets | 16 ms (cdx, grk), 50/100 ms (cld), 100 ms (mus) | Split into first-paint and settlement budgets (R4) |
| Where unread projection lives | mus: session-local, stays in Python. cld, cdx: Rust eventually | Presentation stays in Python. The ack API, lean index, and generation belong in `sase_core` (Phase 3), since other frontends need the same counts |
| `,j` candidate structure | cdx: incremental index. gem: sorted list. grk: generation key | Generation-keyed cache plus remove-on-ack first; full index only if traces demand it |

## 9. Not verified

- The exact interleaving of the 10:02 revert. No dismissal timestamps exist, so a
  reproduction test (Phase 0.5) should confirm the mechanism.
- Runtime traces of the collapsed-panel full-rebuild fallback. It is confirmed by code
  reading only (`render_collapsed` empties `widget._agents`; the patch bails out). Capture
  with `SASE_TUI_TRACE=1` in Phase 1.
- Dedicated leader-key latency. `tui_jk.jsonl` covers plain `j`/`k` only.

## Appendix — key references

- `src/sase/dispatch/attention_inbox.py:129-209` (whole-store read-modify-write), `:306`
  (per-poll `observed_at`); `src/sase/ace/tui/actions/agents/_remote_attention.py` (60 s
  thread cadence).
- `sase-core/crates/sase_core/src/notifications/store.rs:1044-1067` (merge rewrite, caller
  wins); `crates/sase_core_py/src/notifications/mod.rs` (GIL released; counts-only variant
  used for acks).
- `src/sase/ace/tui/actions/agents/`:
  - `_unread_state.py:145-215` (toggle and undo), `:378-455` (worker; synchronous refresh at
    455);
  - `_notification_unread_projection.py:35-137` (patch and rebuild fallback), `:147-210`
    (full-replace reconcile);
  - `_notification_polling.py:316` (poll reconcile), `:335` (synchronous count refresh);
  - `_notification_provider.py:206-265` (unordered snapshot cache);
  - `_display_panel_patches.py:363-520` (`list.index`, collapsed bail-out, per-row
    title/info);
  - `_unread_navigation.py:50-57` (footer probe); `_unread_jump_candidates.py:57-98` (O(N)
    cache key).
- `src/sase/ace/tui/actions/agent_workflow/_leader_mode.py:165-209` (`,j` always refreshes;
  `,u` success never does).
- `src/sase/ace/tui/widgets/_agent_list_widget.py:70` (`render_collapsed`).
- Evidence: `~/.sase/logs/tui_toasts.jsonl` (lines 86, 95, 100),
  `~/.sase/logs/tui_stalls.jsonl{,.1}`, `~/.sase/notifications/notifications.jsonl`
  (3,885 rows / 19 MB / 1,040 active), `~/.sase/procs/procs.jsonl` (proc latencies).
