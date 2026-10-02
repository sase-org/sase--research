# TUI frozen ~10% of wall time: stall-budget verification and prompt/space key latency — independent research (`__mus`)

Researcher: mus · date: 2026-10-02 · workspace sase_16 · sase master (checked files unchanged vs prompt in `prompt_space_and_project_cycle_latency.md`)

> Question: the `prompt_space_and_project_cycle_latency.md` input reports the live TUI spends ~10% of wall time frozen in ≥1.5 s event-loop hitches, and that `<space>` (open prompt) and `<ctrl+n/p>` (project cycling) are slow. Verify the 10% claim from available logs/profiling data, find what actually blocks those two keys, and recommend a fix.
>
> Independence note: I did not open any `__cdx/__cld/__grk/__gem/__final` swarm report nor the pre-existing `prompt_space_and_project_cycle_latency__mus.md`. I read only the shared input file `prompt_space_and_project_cycle_latency.md` (as shared material), the live code in this checkout, and `~/.sase/logs/tui_stalls*.jsonl` plus live `ps` state. Conclusions below are my own from those sources.

## 1. Bottom line

- **The "frozen 10%" claim reproduces.** Counting each hitch once (deduplicating `tui_hitch`/`tui_hitch_recovered` pairs) over the union of `tui_stalls.jsonl` + `tui_stalls.jsonl.1`: **481 hitches, 1,512 s of stall over a 14,087 s span = 10.7% of wall time**, median 3.18 s, max 6.4 s, all PID 872820. Counting both logs naively double-counts recovered rows (~24%); the deduplicated number is the correct one and it matches the reported ~10%.
- **The two keys have their own synchronous costs on top of that budget.** Both `<space>` and `<ctrl+n/p>` call the MRU validation loader **on the UI thread at keystroke time** (`_vcs_mru_cycling.py:404`, `_entry_custom.py:30/72`). That loader fans out per-entry into `is_launchable_project` → `list_project_records` + `detect_workflow_type` (plugin hook, can spawn subprocesses) and can *write* the MRU file when `prune=True`. That is policy + I/O + subprocess work inside a key handler.
- **First-visit `<ctrl+n/p>` has a second, independent spike source:** `_startup_prompt_catalog.py:379` calls `_restart_prompt_source_watcher()`, whose `stop()` does `thread.join(timeout=1.0)` (`fs_watcher.py:198-214`) while the worker parks in `select(..., idle_timeout=0.5)` (`fs_watcher.py:264-276`). Closing the fd does not reliably wake an already-blocked `select` on Linux, so teardown alone can cost ~0.5 s. The non-blocking `ensure_watches()` (`fs_watcher.py:216-235`, documented "safe to call from the UI thread") already exists and is the correct growth primitive.
- **The global stall budget is dominated by work unrelated to these keys** (Agents-detail debouncer, clan runtime/tribe resolution, Textual render allocation sites, main thread parked in `selectors.select`/`_read_from_self`), plus a 6 GB RSS footprint after ~27 h uptime. Fixing the keys alone cannot remove the "sometimes slow for seconds" tail — any keypress landing inside a 3 s hitch waits 3 s regardless of its own cost.
- **Recommended solution (my own):** (1) take both keys off I/O with an app-owned, worker-refreshed launchable-MRU snapshot that key handlers only peek at, `prune=False` on every key path; (2) make catalog getters pure and grow watcher coverage with `ensure_watches()` in a pump-free task, plus make `stop()` wakeable; (3) treat the 10% stall budget / RSS growth as a separate track (debouncer + clan aggregation off the pump, GC instrumentation, memory-leak hunt). Details in §5.

## 2. What I measured (independent stall-log analysis)

Method: parsed both `~/.sase/logs/tui_stalls.jsonl` (current) and `.1` (rotated) with Python `json`, grouped by `event`, deduplicated hitch/recovered pairs, computed span from min/max `ts`.

```
total rows (both files):            960
  tui_hitch / recovered:            408 / 408   (pairs — count once)
  tui_pump_hitch / recovered:        60 /  60   (pairs — count once)
  tui_stall / recovered:              8 /   8
  tui_pump_stall / recovered:         4 /   4
hitch-only rows:                    481
sum(stall_seconds):                 1,512 s
span (max ts − min ts):             14,087 s (3.91 h)
frozen fraction:                    10.73%
median / max hitch:                 3.18 s / 6.4 s
pid:                                all 872820
live ps at research time:           etime 1-02:55 (~27 h), RSS 6,048,212 kB (~5.8–6 GB), 31 threads, 42.5% CPU
MRU on this host:                   7 entries in ~/.sase/vcs_xprompt_mru.json (3 project refs + Patch/owner refs)
```

`last_action` distribution over hitch-only rows (top): `j` 192, `text_area_changed` 186, `u` 136, `k` 100, `underscore` 95, `ctrl+d` 72, `r` 38 — i.e. ordinary navigation/typing dominates, consistent with a global budget rather than one bad key. Directly prompt-related hitches in my window: `ctrl+p` 5 (3.2–4.2 s), `ctrl+n` 4 (2.3–5.5 s), `space` 1 (1.59 s). The small prompt-key hitch count is expected: the watchdog threshold is 1.5 s so the keys' own 20–700 ms costs rarely trip it; what trips it for these keys is landing *inside* a global hitch or hitting the multi-second MRU/watcher outliers.

Deepest-`sase` stack frames over hitch-only rows (my own signature: last `/sase/src/sase/` frame in `main_thread_stack`):

| hitches | deepest sase frame |
|---:|---|
| 176 | `ace_handler.py:131 _run_ace_app` only (no deeper sase frame — pump/timer/compositor level) |
| 56 | `_fire_debounced_detail_update` (Agents-detail debouncer) |
| 51 | `agent_runtime_facade.py:22 aggregate_clan_runtime` |
| 26 | `agent_clan_tribe.py:51 resolve_clan_tribe` |
| 23 | `config/core.py:355 current_config_token → refresh_thread_to_start.start()` |
| 15/13 | `renderable_digest.py` text/digest hashing |
| 14 | `_unread_bulk_scope.py:73 bulk_ack_roster_universe` |
| 13 | `_event_base.py:108 _prompt_input_active → bool(query(PromptInputBar))` |
| 8 | `artifact_files_cache.py:131 select_prompt_file → os.listdir` |
| 4 | `load_launchable`-family / `vcs_xprompt_mru` frames |
| 1 | `_restart_prompt_source_watcher` |

Cross-cutting signatures I counted by substring over hitch stacks:

- `selectors.select` parked: 74 rows; `_read_from_self`: 10 rows. The watchdog marks progress via `call_soon_threadsafe`, which wakes `select` immediately — a main thread stuck there for seconds implies it could not reacquire the GIL (worker holding it) or a stop-the-world pause. This is a real secondary signal, not just slow callbacks.
- Textual allocation sites (`cache.py __init__`, `strip.py __init__`, `compositor`, `model.__hash__`, `compile_query_profile` sha256): ~79 + 51 + 7 rows land inside render/allocation paths — the classic allocation-triggered-GC shape on a multi-GB heap.
- `gc`/`collect` literal matches are ~0/10 — expected, since CPython GC pauses do not leave Python frames; absence of the string proves nothing either way. GC remains a hypothesis requiring the `gc.callbacks` timing hook, not a verdict from stack text.

Caveats: one host, one long-lived process (27 h, ~6 GB RSS), threshold-censored at 1.5 s. Medians below the threshold (the keys' own 20–150 ms) are invisible here by construction.

## 3. Key-path mechanics I verified in code (this checkout)

### 3.1 Both keys validate the whole MRU synchronously

- `<ctrl+n/p>` → `PromptTextArea._on_key` → `_handle_vcs_mru_cycle_key` (`src/sase/ace/tui/widgets/_vcs_mru_cycling.py:385-423`). Line 404 calls `load_launchable_vcs_xprompt_mru()` with default `prune=True`, inline in the handler, before computing the pure-text edit.
- `<space>` → `action_start_agent_from_patch` (`actions/agent_workflow/_entry_custom.py:60-81`) → `_resolve_vcs_xprompt_mru_head()` (lines 14-42), which calls `load_launchable_vcs_xprompt_mru_pairs()` with default `prune=True` before mounting the bar.
- The loader (`src/sase/history/vcs_xprompt_mru.py:67-128`): reads one small JSON file (cheap), then per entry runs `_is_stale_known_project_prefix` (line 119) and `_vcs_prefix_provider_mismatched` (line 121).
  - `_is_stale_known_project_prefix` (lines 263-291) resolves alias → spec path → `is_launchable_project(project_name, projects_base)`.
  - `is_launchable_project` (`ace/tui/modals/project_discovery.py:64-`) calls `list_project_records(...)` **on every invocation** (full record enumeration + `resolve_project_alias_ref` + per-record spec check), and `_is_launchable_project_file` calls `detect_workflow_type(str(project_file))`, which dispatches through the `sase_workspace` pluggy registry to provider hooks including `ws_detect_workflow_type` — the GitHub hook shells `git config` in the project workspace. So one keypress = N × (record scan + spec stat + provider detect + up to 6 subprocess spawns), plus a possible MRU-file rewrite (`_save_vcs_xprompt_mru` when `prune=True` and anything filtered).
  - `_vcs_prefix_provider_mismatched` (lines 388-438) calls `detect_workflow_type` **again** for the same project.
- I attempted a direct wall-clock microbenchmark of the loader but the bare `python3` on PATH cannot import the checkout (`No module named 'sase.history'`); the tool-install interpreter owns the package and I did not want to perturb the live TUI process. I therefore report no new loader timing of my own and rely on the code-shape finding (synchronous I/O + subprocess + write inside a key handler), which is sufficient to condemn the pattern regardless of whether warm cost is 18 or 70 ms: it violates the keystroke-path rules (no subprocess/disk I/O, read-only, no writes) and has a multi-second cold/import tail plus a 1.2–2.1 s first-in-app call shape consistent with the input report's 8.5 s live `ctrl+p` row.

### 3.2 Watcher restart blocks first-visit cycling; the fix primitive already exists

- `_startup_prompt_catalog.py:379` calls `self._restart_prompt_source_watcher()` on first sight of a project (verified reference; `_startup_watchers.py:106` defines the restart).
- `ArtifactWatcher.stop()` (`ace/tui/util/fs_watcher.py:198-214`): sets stop event, closes fd, then `thread.join(timeout=1.0)`. The worker loop (`_loop`, lines 262-276) blocks in `select([fd], [], [], timeout)` with `idle_timeout = 0.5`. The comment on line 201 claims "Closing the fd unblocks the select()" — on Linux closing an fd does **not** wake a `select` already blocked on it (the fd number may even be recycled); the join then waits out up to the 0.5 s idle timeout, plus `start()` re-discovers watch paths afterwards. This is a synchronous 0.1–0.5 s+ tax on first-visit `ctrl+n/p`, exactly the shape of the 2.77 s live row that stacks `_replace_via_keyboard → highlight → catalog → _restart_prompt_source_watcher`.
- `ensure_watches()` (lines 216-235) is explicitly documented "Safe to call from the UI thread", adds only missing paths, no-ops on stopped watchers. `_live_watch_coverage.py:51-88` already uses it. The catalog path should use it instead of restart.

### 3.3 `<space>` rebuilds the bar every press; mount cost is structural

- `_show_prompt_input_bar_for_home` (`actions/agent_workflow/_prompt_bar_mount.py:403`) detaches the old bar synchronously (required to avoid `DuplicateIds` on `#prompt-input-bar`) and constructs/mounts a brand-new `PromptInputBar` per press. Compose + CSS + reflow/paint (~90 ms combined per input data) is therefore paid on every `<space>`, plus `on_mount` fan-out and post-open warmers that repaint Agents detail. No hitch in my window has `action_start_agent_from_patch`/bar-mount on its stack — consistent with the threshold argument: `<space>`'s own 0.1–0.75 s never trips a 1.5 s watchdog, so its "sometimes seconds" tail comes from the global budget, not its own frames.

I did not re-verify the Textual 8.2.8 `on_mount` MRO-double-dispatch count myself (installed Textual lives under the tool venv, readable but I prioritized the two blocking primitives above). I keep it as corroborated-but-not-independently-counted: the mount-per-press structure alone guarantees `<space>` cannot reach one frame without a reveal/hot-spare redesign.

### 3.4 The stall budget is a separate, larger problem

Top hitch sources have nothing to do with the prompt: Agents-detail debouncer (56), clan runtime aggregation (51, including a Rust `rust_aggregate` call — so at least that leg is already past the Python/Rust boundary), clan tribe/summary resolution (26+12+5), render digest hashing (15+13), `current_config_token` spawning a refresh thread (23), `_prompt_input_active()` DOM `query(PromptInputBar)` (13). Combined with 74 `select`-parked hitches and allocation-site hitches on a 6 GB heap, the picture is: heavy periodic aggregation + rendering + thread/GIL contention + probable GC pressure on a long-lived, never-compacted process. The `sase-v3` RSS note (2.3–2.5 GB flagged suspicious in August, now ~6 GB) supports treating memory growth as its own bug.

## 4. Options I considered

| Option | My verdict |
|---|---|
| `prune=False` on key paths only | Necessary but not sufficient — removes the write, leaves ~20+ ms validation + subprocesses + cold tail on the UI thread. Do it as step 0 of the snapshot fix. |
| Memoize `is_launchable_project` / `detect_workflow_type` with a global `lru_cache` | Reject as the primary fix. Stale-cache risk when remotes/workspaces change, and it changes behavior for every caller. Per-build memo inside the worker is fine. |
| Per-keypress `to_thread` / worker in the handler | Reject. Stampedes on held keys, breaks ordering against `_vcs_mru_index`, and `await` inside a Textual callback still serializes on the pump. |
| Snapshot once at startup, never invalidate | Reject — stale after launches / `set-current` / sibling TUIs. Needs generation + peek-token invalidation. |
| **App-owned launchable-MRU snapshot, worker-built, peeked by keys** | **Recommend (Phase 1 core).** Both keys become pure memory reads. |
| **Pure catalog getters + `ensure_watches()` + wakeable `stop()`** | **Recommend (Phase 1, ships with snapshot).** Removes first-visit spikes. |
| Coalesce highlight/arg-hint/Jinja work per edit | Recommend — small, independent, removes 10–20 ms per cycle press. |
| De-duplicate `on_mount` chaining; scope Agents-detail repaint while prompt active; stagger warmers | Recommend as Phase-1 hygiene — each is small and independently testable. |
| `gc.collect(); gc.freeze()` after startup + `gc.callbacks` pause logging | Recommend as instrumentation + cheap mitigation, not as proof of the GC hypothesis. Re-freeze policy needs a memory-cost note. |
| Hot-spare / reveal `<space>` instead of rebuild | Recommend as **Phase 2, conditional** on Phase-1 measurement still showing `<space>` p95 > ~60 ms. Prerequisite: explicit prompt-active state replacing `bool(query(PromptInputBar))` (13 hitch stacks already pay that DOM walk; a hidden spare would additionally suppress gated refreshes). |
| Port validation to Rust / persistent index daemon | Decline first — does not change *when* the work runs; scheduling (off keystroke path) dominates language. |
| Rebind `<space>`, drop markdown highlighting, tune debounces | Decline — no measured link to the blocking primitives. |

Rust-boundary check: no `sase-core` change is needed for my recommended fix. The snapshot is TUI-side scheduling/caching around the existing Python policy; provider detection stays a Python pluggy hook. A batch resolver would be the only thing that belongs in `sase_core` (with wire/binding/pin bump), and it is not required.

## 5. Recommended solution

### Phase 1 — both keys become memory operations; remove the spikes (one epic, small PRs; ship 1–2 first)

1. **App-owned `LaunchableMruSnapshot`.** Immutable `(canonical, display)` tuple + head-prefill metadata + generation + `ready/loading/error` (keep "empty" distinct from "cold"). Single-flight worker builds via the *existing* `load_launchable_vcs_xprompt_mru_pairs(prune=False)` (policy stays single-sourced); publish on the main thread with generation check. Triggers: warm after first paint beside existing catalog warm-ups; after `record_vcs_xprompt_usage` and `set-current`; tick-driven peek-token drift (MRU `mtime_ns+size`, project-spec signature, config token) — ticks revalidate, never recompute. Keys only peek; first `ctrl+n/p` per prompt session pins the ring copy (bursts never touch app state). Cold policy: `<space>` opens an empty bar immediately and applies prefill later only if session/cursor untouched; `ctrl+n/p` on cold shows a hint, never replays queued edits. Never write/prune from key paths; launch-time guards remain authoritative against one stale entry. Regression tests: four prune classes, alias display forms, empty stop, no-reorder/no-overwrite across generations. Structural test: with warm snapshot, zero `open/stat/subprocess.Popen/list_project_records/ArtifactWatcher.stop|start`/joins on both key paths. Expected: `ctrl+n/p` ~one frame, `<space>` ~100 ms, no multi-hundred-ms spikes.
2. **Pure catalog getters + non-blocking watcher growth.** Split "return warm entries / cold sentinel" from "request project"; requested projects go to a desired-set reconciled by a pump-free task (`spawn_pump_free_task` + `to_thread`) calling `ensure_watches(paths)`, then one reconcile. Make `stop()` wakeable (eventfd/self-pipe in the `select` set) so no teardown path ever blocks 0.5 s.
3. **Coalesce per-edit work** (one highlight-map rebuild per cycle edit; memoize assist-entries-to-wire per catalog object; move Jinja inspect off-pump).
4. **Mount hygiene:** de-duplicate mixin `on_mount`/`on_unmount`/`on_worker_state_changed` chaining; stagger non-essential prompt warmers one paint; hoist dispatch-line imports; gate prompt-driven Agents-detail repaint on selected-context actually changing and defer while a prompt is active.
5. **GC policy + proof:** `gc.collect(); gc.freeze()` after mount-state loads (optional idle re-freeze); register a `gc.callbacks` hook logging gen-2 pause durations into the perf/stall log — converts the GC hypothesis into data within a day.
6. **Instrumentation in the same epic:** extend `SASE_TUI_PERF` key-to-paint to `start_agent_from_patch` + cycle keys; add a `slow` bench for `<space>`, single `ctrl+p`, 6-key burst against ~30-entry MRU fixture.

### Phase 2 — conditional `<space>` reveal (only if Phase 1 leaves `<space>` p95 > ~60 ms)

1. Explicit `app._active_prompt_bar` state backing `_prompt_input_active()`; route the ~11 `"#prompt-input-bar"` lookups through one accessor (also removes a DOM walk from every binding check).
2. Idle-mounted fresh id-less hidden spare; on `<space>`: seed context/text → reveal → `activate()` (today's `on_mount` focus/cursor/title/warm-ups). Fresh instance per session preserves undo/completion/vim/search/frontmatter guarantees; mint new `session_id` on activate; keep cancelled-history save. Expected ~50–60 ms; overlay docking only after if sub-frame is required.

### Separate track — the 10% stall budget + RSS (own investigation, not part of the key epic)

- Profile/move off-pump: Agents-detail debouncer `_fire_debounced_detail_update`, clan runtime aggregation + tribe/summary resolution, render-digest hashing, `bulk_ack_roster_universe`, `select_prompt_file` listing.
- GIL/thread audit: `current_config_token` thread-spawn path, worker GIL hold during the 74 `select`-parked hitches, pump-free task discipline.
- Memory: hunt the 2.4 GB → 6 GB growth (reopen the `sase-v3` question with current numbers); GC-pause log from Phase 1 step 5 is the cheapest first evidence.
- Live acceptance: restart TUI (editable install needs restart to reload), then `SASE_TUI_PERF` samples + zero `tui_stalls.jsonl` rows with these handlers on-stack; track maxima/watchdog rows, not medians.

## 6. Risks and guardrails

- One stale snapshot entry for one press is the accepted contract (same as the current-project chip); launch revalidates, snapshot never allocates/resurrects or calls `resolve_ref`; bare-git `resolve_ref` creates projects so Patch entries stay on the offline Patch-name index.
- Watcher races: generation-own the desired set; never UI-join while a worker waits on `call_from_thread`; keep polling fallback.
- `gc.freeze()` pins future cyclic garbage until re-freeze — bounded, acceptable, note it.
- Measurement scope: single host, 7-entry MRU; snapshot design (not per-entry cost) is what scales.

## 7. Evidence provenance (mine)

- Stall numbers: `~/.sase/logs/tui_stalls.jsonl` + `.1` parsed 2026-10-02 (960 rows union → 481 hitch-only, 1,512 s / 14,087 s = 10.73%, median 3.18 s, max 6.4 s); `ps -p 872820` (etime 1-02:55, RSS ~6 GB, 31 threads); `~/.sase/vcs_xprompt_mru.json` (7 entries).
- Code: `_vcs_mru_cycling.py:385-423` (key handler loader call), `_entry_custom.py:14-42/60-81` (space loader call), `history/vcs_xprompt_mru.py:67-128/263-291/388-438` (loader + two detect paths), `modals/project_discovery.py:64-` (per-call record scan), `workspace_provider/_registry.py` + `bare_git_workspace.py:78` (pluggy detect dispatch), `util/fs_watcher.py:198-235/262-276` (join vs select vs ensure), `actions/_startup_prompt_catalog.py:379` + `_startup_watchers.py:106` (restart site), `_prompt_bar_mount.py:403` (rebuild-per-press), `_event_base.py:108` (DOM-walk active check).
- Not independently re-measured: warm/cold loader milliseconds and Textual `on_mount` MRO counts (tool-interpreter import boundary; deprioritized once the synchronous-I/O and join primitives were confirmed in source). Treat others' millisecond tables as corroboration, not as my data.
