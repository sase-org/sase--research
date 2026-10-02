# Making `<space>` (open prompt) and `<ctrl+n>/<ctrl+p>` (current-project cycling) instant

Researcher: `cld` · Date: 2026-10-02 · Code measured: sase `master` @ `45f165b6d5` (this workspace),
run under the user's installed tool interpreter (CPython 3.14.7, Textual 8.2.8, `sase_core_rs` 0.36.2,
`sase-github` 0.2.19).

## TL;DR

Both keys are slow for the same underlying reason: **they do synchronous, disk/subprocess-backed
validation and rebuild a large widget tree on the UI thread at keystroke time, and they trigger
follow-up work that blocks the Textual message pump right after the key lands.** Steady-state cost is
moderate; the "painfully slow / sometimes slow" experience comes from a handful of **100 ms – 2 s
spikes** that are each individually fixable.

Measured in the real `AceApp` (headless, sandboxed copy of the user's real `~/.sase` state, host load
average ≈ 35 on 64 cores):

| Key | Steady key→paint (p50) | First press after start | Spikes observed |
| --- | --- | --- | --- |
| `<space>` (open bar) | **142–154 ms** | 0.36–0.75 s (process busy 2.3–2.8 s) | +0.45–0.60 s full-GC pauses; +60–370 ms Agents-detail repaint right after the bar opens |
| `<ctrl+n>/<ctrl+p>` (cycle) | **42–44 ms** | 0.23–0.26 s | **0.31–0.47 s** on the first cycle onto each project (watcher restart joins a thread); bursts at human speed: per-key lag p90 0.53 s, max 1.29 s |

Root causes, ranked by user-visible impact:

1. **Every keypress re-validates the whole VCS MRU from disk.** It spawns six `git config` subprocesses and
   reads project records repeatedly (20–75 ms warm, 1.2–2.1 s cold) (`load_launchable_vcs_xprompt_mru_pairs`).
2. **The prompt-source inotify watcher is stopped and restarted on the keystroke path** the first time a
   prompt names a new project. `ArtifactWatcher.stop()` joins a thread blocked in a 0.5 s `select()`, so the
   UI thread blocks for 80–470 ms.
3. **The prompt bar is torn down and rebuilt from scratch on every `<space>`.** Each rebuild costs about
   45 ms of compose/CSS work and about 45 ms of reflow/paint. On top of that, an **O(n²) `on_mount` dispatch**
   runs 146 `on_mount` calls instead of 17, because mixins chain `super().on_mount()` *and* Textual calls
   every class's handler.
4. **Background warm-ups that complete after the bar opens repaint the Agents detail panel**
   (60–100 ms steady, 371 ms first) on the UI thread while the user is typing.
5. **Full (gen-2) GC pauses of 445–600 ms** with about 960k tracked objects. Widget-heavy `<space>` is a
   frequent trigger. A single `gc.freeze()` after startup cuts them to about 56 ms.
6. Smaller costs: the highlight map is rebuilt 2–3× per edit (10–20 ms per `ctrl+p`), and
   `_prompt_input_active()` walks the DOM on every key-binding check.

**Recommendation (details in §6).** Make both keys pure in-memory operations, in two phases.

Phase 1 is five small, independent fixes:

- (a) an app-owned **launchable-MRU snapshot**, refreshed off the pump, that both keys read;
- (b) watcher growth via the existing non-blocking `ArtifactWatcher.ensure_watches()` instead of
  stop/start;
- (c) de-duplicating the mixin `on_mount` chain;
- (d) scoping the "semantic surface" refresh so prompt-bar warm-ups never repaint the Agents detail;
- (e) `gc.freeze()` after startup loads.

Phase 1 removes essentially all of the multi-hundred-ms spikes. A prototype of (a)+(c)+(e) already
measured `ctrl+n/p` at **24 ms** and `<space>` at **109 ms** p50.

Phase 2 adds the structural fix for `<space>`: **a pre-built "hot spare" prompt bar composed during idle
time**, so the keypress only seeds text, reveals, and focuses. That targets roughly 50 ms (about one
layout+paint). The same phase coalesces highlight rebuilds, bringing `ctrl+n/p` to about one frame
(≤ 16 ms).

---

## 1. What the two keys actually execute

### 1.1 `<space>` — "Run Agent (Last VCS XPrompt)"

`src/sase/ace/tui/bindings.py:213` binds `space` → `start_agent_from_patch`.

1. Textual `_check_bindings` → `AceApp.check_action` → `check_app_action`
   (`src/sase/ace/tui/_app_action_availability.py:150`). This calls `_prompt_input_active()`
   (`src/sase/ace/tui/actions/_event_base.py:92`), which is `bool(self.query(PromptInputBar))`, a DOM walk.
2. `action_start_agent_from_patch` (`src/sase/ace/tui/actions/agent_workflow/_entry_custom.py:60`) →
   `_resolve_vcs_xprompt_mru_head()` → **`load_launchable_vcs_xprompt_mru_pairs()`** (line 30), which is
   synchronous (see §4.1).
3. `_show_prompt_input_bar_for_home` (`.../_prompt_bar_mount.py:403`) constructs a **brand-new**
   `PromptInputBar` and `mount()`s it.
4. Textual compose: four `Static`s, a `FrontmatterPanel`, a `Vertical`, and a `PromptTextArea`. The text area
   is a `TextArea` subclass with about 20 highlight/completion mixins, and its `TextArea.__init__` alone is
   about 13 ms. CSS is then applied to every new node.
5. `on_mount` storm: 146 handler invocations (§4.3), several `set_class` calls that each restyle the
   subtree, then the bar's own `on_mount` (`_prompt_input_bar_lifecycle.py:75`). That focuses the text area,
   sets the title, and schedules **nine warm-ups** (xprompt assist, artifact-ref kinds, VCS project
   catalog, model catalog, path inventory, history words, prediction cache, placeholders, dispatch
   targets).
6. Screen reflow: the bar docks at the bottom, the agents area shrinks, and the visible agent list is
   re-rendered. Then the first paint.
7. After paint, warm-up completions call `_refresh_visible_prompt_semantic_surfaces`
   (`src/sase/ace/tui/actions/_startup_prompt_catalog.py:347`). That rebuilds the bar's highlight map
   **and** schedules a full Agents-detail repaint (`_schedule_selected_agent_semantic_refresh`, line
   365) through the 150 ms detail debouncer.

### 1.2 `<ctrl+n>` / `<ctrl+p>` — cycle the "current project" stack

`PromptTextArea._on_key` (`src/sase/ace/tui/widgets/_prompt_text_area_key_handling.py:447/455`):

1. `_try_xprompt_arg_name_completion_cycle()` (normally a no-op), then
   `_handle_vcs_mru_cycle_key` (`src/sase/ace/tui/widgets/_vcs_mru_cycling.py:385`).
2. **`load_launchable_vcs_xprompt_mru()`** (line 404). This is the same synchronous validation as
   `<space>`, repeated on *every* press, plus `peek_project_tag_catalog()`.
3. `_replace_via_keyboard` → `TextArea.edit` → `_build_highlight_map` (xprompt-syntax layer). When the new
   project hasn't been seen this session, this goes through `get_warm_prompt_catalog_assist_entries_exact`
   → `_ensure_prompt_catalog_project` → **`_restart_prompt_source_watcher()`**
   (`_startup_prompt_catalog.py:373-379`) (§4.2).
4. `_on_prompt_completion_context_changed` updates the glossary and repo-mention contexts. Each update can
   trigger *another* `_build_highlight_map` and schedule warm-ups for the new project. Then
   `PromptInputBar.on_text_area_changed`, a Jinja-diagnostics timer (another highlight rebuild), and paint.
5. When the new project's warm-ups finish, the Agents detail is repainted again (as in step 7 of §1.1).

## 2. Method

- **The real app, headless.** `AceApp(query="!!!", refresh_interval=0, auto_start_axe=False,
  initial_tab="agents")` under `App.run_test(size=(220, 60))`, with a 10 s settle after
  `_mount_state_loads_done`. I didn't use `AcePage`, because its fast-startup policy patches out Patch
  discovery, which these paths depend on.
- **Real data, sandboxed.** `SASE_HOME` pointed at a 540 MB copy of the user's `~/.sase` state. The copy
  includes top-level state files, `agent_artifact_index.sqlite`, prompt history, notifications, clans, and
  every project's top-level files including all `*.sase` specs; it excludes workspaces. Config came from the
  real `~/.config/sase`. The MRU had 7 entries, and 4 of the 37 projects were launchable.
- **Key→paint.** I wrapped `textual.screen.Screen._compositor_refresh` and measured from key send to the
  first compositor refresh that completes after the handler finishes. For `<space>`, "after the handler"
  means after `PromptInputBar.on_mount`.
- **"Process busy".** `pilot.press()` only returns when the *whole process* (all threads) is idle; Textual's
  `wait_for_idle` compares process CPU time with wall time. I report that separately as the background
  "busy tail" that competes with the next keystroke.
- **Profiling.** pyinstrument (0.5 ms interval, full frames), `gc.callbacks` for pause timing, and
  call-counting wrappers.
- **Bursts.** `ctrl+p` sent straight to the driver every 50 ms (fast human or key-repeat cadence), without
  waiting for idle.
- **Caveats.** The numbers are a **lower bound** for the live TUI: headless mode skips terminal writes,
  auto-refresh ticks were off, and the sandbox has no live agent churn. The user's real stall watchdog
  (`~/.sase/logs/tui_stalls.jsonl`) recorded **3.2–4.7 s pump/loop hitches today** in unrelated
  Agents-tab work. Examples include a countdown tick in `_update_agents_info_panel` →
  `compile_query_profile` → `json.dumps`, and compositor renders. Any `<space>` or `ctrl+p` that lands
  during such a hitch waits behind it.

## 3. Measurements

### 3.1 Baseline key latency (real app, sandboxed real data)

| Metric | `<space>` | `<ctrl+n>/<ctrl+p>` |
| --- | --- | --- |
| key → handler start (steady p50) | 92 ms (compose/mount happen before the bar's `on_mount`) | 1.2 ms |
| handler (steady p50 / p90) | bar `on_mount` 9 / 10 ms | 37 / 47 ms |
| **key → paint, steady p50 / p90** | **142–154 / 149–166 ms** | **42–44 / 53 ms** |
| key → paint, first press after start | 360–745 ms | 226–262 ms |
| process busy after key (steady p50) | 377 ms | 146 ms |
| process busy after key (first) | 2.3–2.8 s | 0.71 s |

### 3.2 Bursts: walking the stack at human speed (6 × `ctrl+p` at 50 ms intervals, 6 rounds)

| Metric | p50 | p90 | max |
| --- | --- | --- | --- |
| per-key lag (send → its paint) | 44 ms | **530 ms** | **1293 ms** |
| last key → final paint | 40 ms | 45 ms | 534 ms |

The p90 and max come from the first visit to each project (§4.2 and §4.4), not from the median path.

### 3.3 Where the time goes

| Component | Cost | Evidence |
| --- | --- | --- |
| `load_launchable_vcs_xprompt_mru_pairs()` per press | 20–31 ms standalone, 30–73 ms in-app (GIL contention); **1.2–2.1 s** on the first in-app call; 9.9 s in a fresh process | 6 × `git config --get remote.origin.url` subprocesses + ≥3 `list_project_records` + Patch-cache stat/parse per call (counted) |
| `ArtifactWatcher.stop()` during watcher restart | **80–470 ms** (samples 451, 81, 211, 341, 471, 101 ms); 312 ms and 346 ms in-app | `thread.join(timeout=1.0)` on a thread in `select(..., 0.5)` |
| `PromptInputBar` compose + CSS apply | ~45 ms | `_on_compose`/`_register`/`stylesheet.apply` in the profile |
| `on_mount` storm + post-mount `set_class` restyles | ~40 ms (≈25–35 ms is duplication) | 146 invocations, counted (§4.3) |
| First layout/reflow + paint after mount | ~45 ms (OptionList `render_lines` ≈ 8 ms) | `_on_timer_update` → `_refresh_layout` |
| Agents-detail repaint triggered by prompt warm-ups | 58–97 ms each (371 ms first); 678–729 ms total per short run | debouncer instrumentation (§4.4) |
| `_build_highlight_map` per `ctrl+p` | 7–11 ms × 2–3 rebuilds | profile: `edit`, `_refresh_prompt_repo_mention_context`, `_refresh_prompt_glossary_context`, Jinja timer |
| `check_app_action` (incl. `_prompt_input_active` DOM walk) | ~10 ms on `<space>`; 13–50 ms per walk seen in watcher callbacks under contention | profile |
| Full (gen-2) GC pause | **445–600 ms** (959,512 tracked objects) | `gc.callbacks` |

### 3.4 Prototype what-ifs (monkeypatched in the harness, same data)

| Variant | `<space>` key→paint p50 / p90 | `ctrl+n/p` key→paint p50 / p90 |
| --- | --- | --- |
| Baseline | 142 / 149 ms | 44 / 53 ms |
| + MRU result memoized + `gc.freeze()` after startup | 130 / 180 ms | **19.7 / 30 ms** |
| + `on_mount` de-duplicated (each class's handler runs once) | **109 / 130 ms** (key→`on_mount` 92 → 60 ms) | 23.6 / 30 ms |
| GC only: full collections with vs. without `gc.freeze()` | 56 ms vs. 445–600 ms per gen-2 pause | (affects every key) |

The `<space>` that remains (~110 ms) is the compose + CSS (~45 ms) and reflow + paint (~45 ms) of a freshly
built bar. Only Phase 2's pre-built bar removes the compose half.

## 4. Root causes

### 4.1 Synchronous MRU validation on every keypress

`src/sase/history/vcs_xprompt_mru.py:67` `load_launchable_vcs_xprompt_mru_pairs()` (the function itself
claims to be "per-keystroke ``<ctrl+p>``"-aware) does the following each time it's called:

- reads and parses `~/.sase/vcs_xprompt_mru.json`;
- builds `_resolvable_vcs_ref_index()` (line 300): `get_known_project_workspaces()`, every Patch via
  `find_all_patches_cached()` (re-parses any spec file whose mtime changed; the 540 KB archive takes
  16–41 ms; agents rewrite the active spec constantly), and the project alias map;
- for each entry, runs `_is_stale_known_project_prefix` → `is_launchable_project` (which reads project
  records again) and `_vcs_prefix_provider_mismatched` → `detect_workflow_type()` → the sase-github plugin's
  `ws_detect_workflow_type`. That plugin **spawns `git config --get remote.origin.url`** in the project's
  workspace, twice per project entry: six subprocesses per keypress with this MRU;
- with `prune=True` (the default on both key paths) it **writes the MRU file** whenever something was
  pruned;
- humanizes each entry for display.

This breaks two rules in `tui_perf.md`: rule 1 ("no synchronous disk I/O, JSON parsing, subprocess calls in
action/message handlers") and rule 11 ("keystroke paths are read-only and prompt-free … never spawn
subprocesses"). It also scales with MRU size (capped at 100). The user has only 4 launchable projects, so
cost stays in the 20–40 ms band, but a cold first call in the live app cost 1.2–2.1 s.

### 4.2 Watcher restart with a blocking thread join on the keystroke path

Edit → `_build_highlight_map` → `_get_exact_warm_xprompt_arg_assist_entries`
(`_xprompt_arg_hints.py:198`) → `get_warm_prompt_catalog_assist_entries_exact`
(`_startup_prompt_catalog.py:123`) → `_ensure_prompt_catalog_project` (line 373). For any project not yet
in `_prompt_catalog_projects`, this calls `_restart_prompt_source_watcher()`
(`_startup_watchers.py:106`), which runs `ArtifactWatcher.stop()` (`util/fs_watcher.py:198`) and then
`start()`.

`stop()` closes the inotify fd and `thread.join(timeout=1.0)`. On Linux, closing an fd doesn't wake a
`select()` already sleeping on it, so the join waits out the loop's `idle_timeout = 0.5` (line 264), about
250 ms on average. Restarting also re-discovers every watch path (5–34 ms).

This happens on the **first `ctrl+p` onto each project per session**. The same path is reachable when you
type a `+project` tag, and every new Patch name that resolves as a "project" adds to the growing set.
`ArtifactWatcher.ensure_watches()` (line 216, documented "safe to call from the UI thread") already exists
and would avoid the stop/start entirely.

### 4.3 The bar is rebuilt per `<space>`, and its `on_mount` is O(n²)

Sixteen classes in `PromptTextArea`'s MRO define `on_mount`, and fifteen of them chain
`super().on_mount()`. Textual's `MessagePump._get_dispatch_methods`
(`textual/message_pump.py:743`) *also* invokes every class's `on_mount` along the MRO. Counted during one
steady-state `<space>`:

```
LineRenderingMixin 18x · FileCompletionDirectiveInventoryWorkerMixin 14x · JinjaHighlightMixin 13x ·
MisspellingHighlightMixin 12x · PromptRepoMentionMixin 11x · PromptGlossaryMixin 10x · … · ScrollView 22x
total: 146 invocations for 17 defining classes
```

Each `LineRenderingMixin.on_mount` runs `_sync_vim_cursor_class()` → `set_class`, and the first of those
triggers an 8 ms subtree restyle. `PromptGlossaryMixin.on_mount` re-schedules its context warm 10 times;
the work is idempotent but wasted. `on_unmount` and `on_worker_state_changed` show the same double-dispatch
pattern (two classes each).

Beyond that, because the bar is destroyed and rebuilt, every `<space>` pays the full cost again: compose,
CSS for every node, `TextArea.__init__`, post-mount class toggles, and re-running warm-ups whose "warmed"
flags live on the widget instance (for example `_vcs_project_catalog_warmed`,
`_file_completion_base.py:50`). The very first `<space>` also pays first-use import and CSS-rule costs.

### 4.4 Prompt warm-ups repaint the Agents detail panel

`_refresh_visible_prompt_semantic_surfaces` and `_refresh_visible_prompt_catalog_surfaces`
(`_startup_prompt_catalog.py:347` / `:526`) always end in `_schedule_selected_agent_semantic_refresh`
(line 365). That schedules `_fire_debounced_detail_update`, which costs 58–97 ms steady and 371 ms the
first time, mostly `lane_neighbor_projection_for` → `prospective_clan_projection` and footer updates.

The triggers are glossary, repo-mention, and catalog warm-ups for **the prompt bar's** project context: on
the first open, on every first cycle onto a new project, and after every prompt-source invalidation (any
xprompt, memory, or config edit in watched directories, which agents produce constantly). The selected
agent's detail context usually didn't change, and the user is typing in the bar, so the repaint is wasted
pump time that lands exactly while the user presses the next key. This conflicts with `tui_perf.md` rule 13
("defer non-urgent refresh work while … typing in the prompt input").

### 4.5 GC pauses

The settled app tracks about 960k container objects. Three full collections during 6 `<space>` + 36
`ctrl+n/p` presses took 445–600 ms each, while gen-0 and gen-1 collections stayed at 0.3–44 ms. Mounting a
widget tree allocates heavily, which makes `<space>` a frequent trigger, and the pause lands at random,
which matches "sometimes slow". Nothing in `src/sase/ace` tunes the collector (`gc.freeze`,
`set_threshold`). Calling `gc.collect(); gc.freeze()` once after startup cut full collections to 56 ms in
the same scenario.

### 4.6 Smaller per-edit costs

- **Triple highlight rebuild.** One `ctrl+p` rebuilds `_build_highlight_map` inside `TextArea.edit`, again
  in `_refresh_prompt_repo_mention_context`, again in `_refresh_prompt_glossary_context`, and once more from
  the Jinja-diagnostics timer. Each rebuild re-serializes the entire xprompt assist catalog to wire dicts
  (`_xprompt_arg_assist_entries_wire`, `_xprompt_syntax_highlight.py:177`, about 3.5 ms) and calls the Rust
  `xprompt_argument_spans` (about 4 ms).
- **`_prompt_input_active()` is a DOM walk.** It runs from `check_app_action` on app-level binding checks,
  from FS-watcher callbacks, and from detail-refresh guards.

## 5. Options considered

| # | Option | Gain | Risk / cost | Verdict |
| --- | --- | --- | --- | --- |
| A | **Launchable-MRU snapshot.** App-owned, computed off the pump at startup, after launches, on MRU-file/project/Patch change tokens, and on tick revalidation; both keys read it from memory. The bar also captures one ring per prompt session. | −20–75 ms on every press; removes 1–2 s cold spikes and all subprocesses from keystroke paths | Low. Keep the pruning rules single-sourced in `vcs_xprompt_mru.py`; the launch-time unresolved-ref guard still protects a briefly stale entry. | **Do (Phase 1)** |
| B | **Non-blocking watcher growth.** Compute the new project's watch paths off-thread and call `ensure_watches()`; make `stop()` non-blocking (self-pipe/eventfd in the `select` set, or no join for a daemon thread). | −80–470 ms first-visit spikes | Low | **Do (Phase 1)** |
| C | **De-duplicate `on_mount`.** Drop the `super().on_mount()` chaining in mixins (Textual already dispatches each class), or route through one `PromptTextArea.on_mount` that calls `_mount_<feature>()` hooks once. Same for `on_unmount` and `on_worker_state_changed`. | −25–35 ms per `<space>`; fewer redundant warm-up schedules | Low–medium (audit ordering assumptions) | **Do (Phase 1)** |
| D | **Scope semantic refresh.** Repaint the Agents detail only when the warmed context equals the selected agent's context, and defer it while a prompt is mounted. | −60–370 ms pump stalls right after open or cycle | Low | **Do (Phase 1)** |
| E | **GC policy.** `gc.collect(); gc.freeze()` after `_mount_state_loads_done`; optionally unfreeze/collect/re-freeze during long idle windows; optionally raise the gen-0 threshold. | Removes 0.45–0.6 s random pauses on *all* keys | Low (frozen objects that later become cyclic garbage are held until the next re-freeze) | **Do (Phase 1)** |
| F | **Hot-spare prompt bar.** Compose a fresh, hidden, id-less `PromptInputBar` during idle (after startup and after each dismissal). `<space>` seeds the text and prompt context, reveals, focuses, and runs an `activate()` that holds today's `on_mount` focus, cursor, title, and warm-up logic. | −45–60 ms more per `<space>`; also hides first-press import/CSS costs | Medium: lookups must go through an explicit accessor (see §6.2) | **Do (Phase 2)** |
| G | **Coalesce highlight rebuilds.** Mark dirty and rebuild once per edit or refresh; memoize wire-converted assist entries per catalog object. | −10–20 ms per `ctrl+p` | Low | **Do (Phase 2)** |
| H | **Explicit prompt-active state.** Replace `bool(query(PromptInputBar))` with a flag or reference maintained by mount, activate, and detach. | −a few to tens of ms per key, more under contention | Low; needed by F anyway | **Do (with F)** |
| I | Port MRU validation to the Rust core | Small: plugin hooks (`git config`) stay in Python; the problem is *when* it runs, not how fast | Medium | **Don't do first** (the snapshot is TUI-side caching of an existing function and sits fine on the presentation side of the boundary) |
| J | Make the bar an overlay layer so the Agents list doesn't reflow | Maybe −15–25 ms | UX change (covers rows) | Experiment only after F |
| K | Memoize sase-github's `ws_detect_workflow_type` by `(project_file, mtime)` or read `.git/config` directly | Makes even uncached validation ~6× cheaper | Lives in the linked `sase-github` repo | Optional; A makes it off-path anyway |

## 6. Recommended solution

### 6.1 Phase 1: kill the spikes (small, independent, low-risk changes)

1. **`LaunchableMruSnapshot`** (option A).
   - App state holds `tuple[(canonical, display), ...]` plus a validity token. The token is the MRU file's
     `(mtime_ns, size)` plus a cheap project/Patch change token: reuse the stat-only
     `ace_refresh_tokens` / `current_config_token()` style, and never stat or glob on a render path
     (`tui_perf.md` rule 8).
   - Rebuild it in a thread worker at startup idle, after `record_vcs_xprompt_usage` (launch), on project
     lifecycle changes, and when a periodic tick sees the token drift (rule 10: ticks revalidate, they don't
     recompute).
   - `_resolve_vcs_xprompt_mru_head()` and `_handle_vcs_mru_cycle_key` read the snapshot. On a cold miss
     (startup race), fall back to the stored MRU spellings with no validation and schedule a rebuild,
     matching how a cold `peek_project_tag_catalog()` already degrades.
   - **Bar-scoped ring:** the first `ctrl+n/p` in a prompt session copies the snapshot into the text area,
     so a burst never touches app state again.
   - Never `prune=True`-write from a keystroke path. Do the pruning write in the rebuild worker.
2. **Non-blocking watcher growth** (option B). In `_ensure_prompt_catalog_project`, add the project to the
   set and compute its new watch paths in a pump-free task (`spawn_pump_free_task`). Then call
   `self._prompt_source_watcher.ensure_watches(paths)` instead of `_restart_prompt_source_watcher()`.
   Separately, make `ArtifactWatcher.stop()` wake its loop (add a self-pipe or eventfd to the `select` set)
   so teardown never blocks for up to 0.5 s anywhere.
3. **De-duplicate `on_mount`** (option C) for `PromptTextArea`'s mixins, and also `on_unmount` and
   `on_worker_state_changed`. Add a regression test asserting each defining class's `on_mount` body runs
   exactly once per mount.
4. **Scope `_schedule_selected_agent_semantic_refresh`** (option D). Pass the refreshed context into the
   refresh path and skip the Agents repaint unless it matches the selected agent's glossary/repo-mention
   context. While `_prompt_input_active`, defer it to bar dismissal, which is the existing "defer while
   typing" activity gate.
5. **`gc.freeze()` after startup loads** (option E), right after `_mount_state_loads_done` flips. If
   memory growth is a concern, add an idle-window `gc.unfreeze(); gc.collect(); gc.freeze()` (for example
   after 2+ minutes with no input and no prompt mounted).

Expected after Phase 1 (from the §3.4 prototype plus the removed spikes): `ctrl+n/p` about 20–25 ms p50
with no first-visit or burst spikes from §4.2 or §4.4; `<space>` about 100–110 ms p50 with no GC or
watcher outliers.

### 6.2 Phase 2: make `<space>` a reveal, not a rebuild

1. **Hot-spare bar** (option F).
   - During idle (after startup and after each bar dismissal), mount a fresh `PromptInputBar` with **no
     id** and `display: none`. It is fully composed, styled, and mounted, with first-use imports and CSS
     paid off-keystroke.
   - On `<space>`: set `_prompt_context`, seed the initial text (reusing the existing in-place stack
     loaders such as `load_stack_from_xprompt_markdown` / history-load), flip `display`, and call a new
     `activate()`. `activate()` holds the focus, cursor, title, warm-ups, and classes logic that `on_mount`
     does today; `on_mount` keeps only construction-time work.
   - Textual details that shape the design: a node's `id` can be set once if it was `None`, but
     `query_one("#id")` uses the parent `NodeList`'s id index (`walk_breadth_search_id` →
     `_nodes._get_by_id`), which is filled at insertion. Setting the id at activation therefore won't make
     the spare findable. Route the ~11 `"#prompt-input-bar"` lookups (6 files) plus the 2 type queries
     through one accessor (`app._active_prompt_bar`) and back `_prompt_input_active()` with the same
     reference (option H).
   - Always build a *fresh* spare after dismissal rather than resetting a used bar. That keeps today's
     "new instance per prompt session" state guarantees: undo history, completion state, vim mode, search,
     frontmatter.
2. **Coalesce highlight rebuilds** (option G): one rebuild per edit or refresh cycle, plus a per-catalog
   memo of `xprompt_arg_assist_entries_to_wire`.

Expected after Phase 2: `<space>` about 50–60 ms (reveal + focus restyle + one reflow/paint) and
`ctrl+n/p` about 10–16 ms. Overlay-layer docking (option J) is the remaining lever if `<space>` must get
below one 60 Hz frame.

### 6.3 Guardrails, so this doesn't regress

- **Bench.** Add `tests/ace/tui/bench_prompt_bar_keys.py`, a `slow` bench in the style of
  `bench_admin_center_open.py`. It should report key→paint p50/p95 for `<space>`, single `ctrl+p`, and a
  6-key `ctrl+p` burst, against a fixture with ~30 MRU entries over several projects and Patches.
  - Targets: `<space>` p95 ≤ 60 ms; `ctrl+n/p` p95 ≤ 16 ms.
- **Structural tests**, cheap enough for `just check`:
  - no `subprocess.Popen` during `ctrl+n/p` or `<space>` (monkeypatch it to raise);
  - no `ArtifactWatcher.stop` on an edit path;
  - `on_mount` invocation count equals the number of defining classes.
- **Live verification.** Extend `SASE_TUI_PERF`'s key-to-paint JSONL (`src/sase/ace/tui/util/perf.py`,
  today j/k only) to cover `start_agent_from_patch` and the VCS-cycle keys, so the user can confirm the fix
  in the real TUI. Also check `~/.sase/logs/tui_stalls.jsonl` for any remaining hitches whose
  `last_action` is `space` or `ctrl+p`.

### 6.4 Note on the remaining "sometimes"

Even after both phases, a key that arrives while the pump is inside an unrelated multi-second callback
still waits; the stall log shows 3.2–4.7 s hitches today from Agents-tab countdown and render work. Those
need fixing on their own merits through the existing stall-watchdog workflow (`tui_perf.md` "Freeze
forensics first"). The changes above guarantee that these two keys never *cause* such a stall and never
schedule one right after themselves.

---

## Appendix A: reproduce

The harness scripts used for this report were throwaway files under `/tmp/cld/` and won't persist. The
core of the key→paint harness, in about 40 lines:

```python
os.environ["SASE_HOME"] = "<copy of ~/.sase without workspaces>"
from textual.screen import Screen
EV = []
def wrap(owner, name, kind):                      # timestamp start/end of a method
    fn = getattr(owner, name)
    def w(*a, **k):
        EV.append((perf_counter(), kind + ":start"))
        try: return fn(*a, **k)
        finally: EV.append((perf_counter(), kind + ":end"))
    setattr(owner, name, w)
wrap(Screen, "_compositor_refresh", "paint")
wrap(PromptInputBar, "on_mount", "bar_mount")
wrap(PromptTextArea, "_handle_vcs_mru_cycle_key", "cycle")
app = AceApp(query="!!!", refresh_interval=0, auto_start_axe=False, initial_tab="agents")
async with app.run_test(size=(220, 60)) as pilot:
    ... wait for app._mount_state_loads_done, then pause 10 s ...
    t0 = perf_counter(); await pilot.press("space"); await pilot.pause(); await asyncio.sleep(0.6)
    # key->paint = first "paint:end" after "bar_mount:end", minus t0
```

Run it with the user's tool interpreter so the Rust binding matches:
`PYTHONPATH=$PWD/src ~/.local/share/uv/tools/sase/bin/python harness.py`. This workspace's `.venv` has a
stale `sase_core_rs` that lacks `jinja_scope_variables`. Watch out: `du` is aliased to `sudo ncdu` in the
user's shell, so use `command du`.

## Appendix B: raw spot numbers

- Standalone MRU load (warm): 19.0–26.9 ms; the first call in a fresh process took 9.9 s (imports + Patch
  parse). Per call: 6 `git config` spawns and ≥3 `list_project_records`. Scaling test with 7/15/30 entries:
  20/37/32 ms (only 4 launchable projects, so pruning bounds it).
- In-app `load_launchable_vcs_xprompt_mru_pairs` max per run: 1462, 2068, 1211 ms (first call after
  startup).
- `ArtifactWatcher.stop()`: 451, 81, 211, 341, 471, 101 ms standalone; 312 and 346 ms in-app.
- GC with 959,512 tracked objects: gen-2 p50 519.5 ms, max 600.1 ms. Frozen: gen-2 56 ms.
- Debounced Agents-detail fire during measurement runs: 729 ms and 678 ms total; single fires 58–97 ms;
  first 371 ms.
- `<space>` steady profile (one press, 616 ms wall including idle polling): action 35 ms (MRU 31.6) +
  availability 9.5 ms; compose/register CSS ≈ 45 ms; `on_mount` chain ≈ 16 ms + 3 × 8 ms restyles;
  `_apply_active_classes` 8.5 ms; focus restyle 10.4 ms; layout/paint ≈ 43 + 7 ms.
- Steady `ctrl+p` handler (50 ms in profile): MRU 30.6 ms; `_replace_via_keyboard` 10.4 ms (highlight
  7 ms); context-changed chain 9.3 ms (two more highlight rebuilds).
