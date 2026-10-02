# Making `<space>` (open prompt) and `<ctrl+n/p>` (project cycling) fast

Consolidated report · lead researcher · 2026-10-02 · sase master `8d1ac50c51` (none of the
key-path files changed since `45f165b6d5`, the revision the researchers measured) · live
TUI interpreter: CPython 3.14.7, Textual 8.2.8

Sources: five independent reports in this directory (`__cdx`, `__cld`, `__grk`, `__mus`,
`__gem`) plus my own checks:

- I re-read the key paths, the watcher, and the provider-detection code in `sase-github`
  and `sase-core`.
- I confirmed Textual's `on_mount` dispatch semantics against the installed 8.2.8 source.
- I mined today's live stall log (`~/.sase/logs/tui_stalls.jsonl{,.1}`: 726 rows from
  10:28 to 13:34, one TUI process).
- I inspected the live process, ran a GC-pause scaling benchmark, and read the prior
  prompt-lag epic `sase-v2` and its memory follow-up, `sase-v3`.

---

## 1. Bottom line

The two keys are slow for **three separable reasons**. Only the first one is shared, and
all five reports agree on it:

1. **Every press re-validates the whole "current project" MRU on the UI thread.**
   `<ctrl+n/p>` and `<space>` both call `load_launchable_vcs_xprompt_mru*()`. That call
   lists project records about 9 times and spawns **6 `git config` subprocesses** through
   the GitHub provider's `ws_detect_workflow_type`. It can also *write* the MRU file
   (`prune=True`).
   - Warm cost: about 18–26 ms standalone and 30–73 ms in-app.
   - Cold cost: 0.45–2 s.
   - The live stall log has an 8.5 s `ctrl+p` freeze inside this function.
2. **`<ctrl+n/p>` onto a project not yet seen this session restarts an inotify watcher
   synchronously.** A *render getter* calls this restart, and `ArtifactWatcher.stop()`
   joins a thread parked in a 0.5 s `select()`.
   - Cost: 80–470 ms per first visit; one live incident lasted 2.8 s.
   - Only cdx and cld found this. A fix that only caches the MRU leaves it in place.
3. **`<space>` rebuilds the whole prompt widget tree on every press.** Several costs are
   built into that rebuild:
   - The `on_mount` chain is O(n²): 146 handler calls for 17 defining classes.
   - Warm-ups that finish after the bar opens repaint the Agents detail panel.
   - Steady key-to-paint is about 145 ms; the first press after startup takes 0.4–0.75 s.

There is a fourth, cross-cutting factor behind "sometimes". **The live TUI spent 10% of
the last 3 hours frozen in ≥1.5 s event-loop hitches** (317 hitches, median 3.6 s). The
process sits at 5.9 GB RSS after 26 h. Any keypress that lands in one of those freezes
waits, whatever its own code costs. Full-GC pauses (445–600 ms measured by cld) are part
of this, and so is unrelated Agents-tab work.

**Recommendation (details in §6).**

- **Phase 1** makes both keys pure in-memory operations:
  - an app-owned, worker-refreshed **launchable-MRU snapshot** that both keys read;
  - pure catalog getters plus **non-blocking watcher growth**;
  - coalesced per-edit highlight work;
  - de-duplicated `on_mount`;
  - no Agents-detail repaints triggered by the prompt;
  - `gc.freeze()` after startup;
  - perf instrumentation for these keys.

  Phase 1 should bring `<ctrl+n/p>` to about one frame and `<space>` to about 100 ms with
  no multi-hundred-ms spikes.
- **Phase 2**, which you need if `<space>` must feel instant (≤ 60 ms), makes `<space>` a
  *reveal* of a pre-built hidden bar instead of a rebuild. It has a hard prerequisite:
  replace the DOM-query `_prompt_input_active()` with explicit state.
- **Separately**, treat the 10% stall budget and the RSS growth as their own track.
  Without that track, the keys will still sometimes be slow no matter what Phase 1–2 do.

---

## 2. What the keys actually do

- **"Current project stack" is the VCS-xprompt MRU** (`~/.sase/vcs_xprompt_mru.json`,
  most-recent first, capped at 100). The current project is the first entry that maps to
  an enabled project. On this host the MRU has 7 entries: 3 launchable projects plus Patch
  and owner/repo refs.
- **`<ctrl+n>` / `<ctrl+p>`** are handled by `PromptTextArea._on_key`
  (`_prompt_text_area_key_handling.py:447–461`).
  - An xprompt arg-name completion cycle gets first claim on the keys. Otherwise they go
    to `_handle_vcs_mru_cycle_key` (`_vcs_mru_cycling.py:385`).
  - That handler loads the MRU, computes a pure edit (`_cycle_vcs_mru_text`) that swaps
    the leading `+project` / `#gh:ref`, and applies it with `_replace_via_keyboard`.
  - It then refreshes the arg hints and fires `_on_prompt_completion_context_changed()`.
  - `ctrl+p` moves to older entries and `ctrl+n` to newer ones. The ring includes one
    empty stop.
  - Cycling edits text only; it doesn't promote anything in the MRU. Keep it that way.
- **`<space>`** is bound to `start_agent_from_patch` (`bindings.py:213`,
  `default_config.yml:893`).
  - `_entry_custom.py:60` resolves the MRU head with the same loader.
  - `_show_prompt_input_bar_for_home` (`_prompt_bar_mount.py:403`) synchronously detaches
    any old bar and saves its cancelled text. It then constructs and mounts a brand-new
    `PromptInputBar`.
  - The detach has to be synchronous to avoid `DuplicateIds` on `#prompt-input-bar`.
  - The action is disabled while a bar is already active.

## 3. Where the time goes

### 3.1 Consolidated measurements

| What | Value | Source |
| --- | --- | --- |
| MRU loader, warm standalone | 18.1 ms median (cdx, n=12); 20–26 ms (grk, mus, gem); 19–27 ms (cld) | all five |
| MRU loader, in the running app | 30–73 ms (GIL contention); first in-app call 1.2–2.1 s | cld |
| MRU loader, fresh process | 0.45–0.63 s (grk, gem); 0.47–5.3 s (mus); 7.9–9.9 s, import-dominated (cdx, cld) | — |
| Work per call | ~9 `list_project_records`, 6 `git config` spawns, ~107 Python `stat`s; raw JSON read 0.05 ms | cdx, grk, cld |
| `ctrl+p` handler, real loader vs preloaded list | **27.7 ms → 2.4 ms** (11.5×) | cdx |
| `<space>` pre-mount work, real vs preloaded | 21 ms → 0.01 ms | cdx |
| `ctrl+n/p` key→paint, real app, steady p50 / p90 | 42–44 / 53 ms | cld |
| `ctrl+n/p` first visit to a project (watcher restart) | 0.31–0.47 s; `stop()` alone took 81–471 ms | cld |
| `ctrl+p` bursts at 50 ms cadence | per-key lag p90 530 ms, max 1.29 s | cld |
| `<space>` key→paint, steady p50 / p90 | 142–154 / 149–166 ms | cld |
| `<space>` first press after startup | 0.36–0.75 s (process busy for 2.3–2.8 s afterwards) | cld |
| `<space>` composition | compose + CSS ≈ 45 ms; `on_mount` storm ≈ 40 ms; reflow + paint ≈ 45 ms | cld |
| Prototype: memoized MRU + `gc.freeze` + de-duplicated `on_mount` | `ctrl+n/p` 20–24 ms p50; `<space>` 109 ms p50 | cld |
| Full (gen-2) GC pause, 960k tracked objects | 445–600 ms; 56 ms after `gc.freeze()` | cld |

cld measured headless with a sandboxed copy of the real `~/.sase`, so its numbers are a
**lower bound** for the live terminal.

### 3.2 Live incidents (stall watchdog, today)

- **12:38:05–12:38:08 — `ctrl+p` → MRU loader.** The samples show provider-metadata
  reads, ProjectSpec existence checks, repeated Rust project enumeration, and
  `subprocess.run`/`_fork_exec` in GitHub provider detection. The loop recovered after
  **8.51 s**. (cdx; I re-confirmed the rows.)
- **12:37:48 — `ctrl+p` → `_replace_via_keyboard` → `_build_highlight_map` →
  `get_warm_prompt_catalog_assist_entries_exact` → `_ensure_prompt_catalog_project` →
  `_restart_prompt_source_watcher`.** Recovered after 2.77 s. The `last_action` field
  says `space`, pressed 6.9 s earlier. That is the realistic workflow: open with `<space>`,
  then `ctrl+p` to the project you want, and the first `ctrl+p` pays both costs back to
  back.
- **No hitch in today's log has `action_start_agent_from_patch` or prompt-bar mount on
  its stack.** The watchdog threshold is 1.5 s, so `<space>`'s own 0.1–0.75 s costs never
  show up there. `<space>`'s multi-second "sometimes" therefore comes from §3.4, not from
  its own code.

### 3.3 Verified root-cause mechanics

- **MRU validation is policy work done at keystroke time.**
  - `_is_stale_known_project_prefix` calls `is_launchable_project`, which lists *all*
    project records on every call, parses the spec, and calls `detect_workflow_type`.
  - `_vcs_prefix_provider_mismatched` calls `detect_workflow_type` *again*.
  - The `sase-github` hook (`workspace_plugin.py:64`) runs
    `git config --get remote.origin.url` in the project workspace.
  - This breaks two `tui_perf.md` rules: rule 1 (no subprocess or disk I/O in handlers)
    and rule 11 (keystroke paths are read-only and never spawn subprocesses).
  - Cost scales with the number of distinct *known-project* entries, not raw MRU length.
    cld's scaling run gave 20/37/32 ms for 7/15/30 entries, so gem's ~350 ms projection
    for 50 entries is too pessimistic. Even so, the cost never fits the budget.
- **Watcher restart from a getter.** `_ensure_prompt_catalog_project`
  (`_startup_prompt_catalog.py:373`) calls `_restart_prompt_source_watcher` the first time
  it sees a project. That calls `stop()` and then `start()`.
  - `stop()` closes the fd and then runs `thread.join(timeout=1.0)`
    (`util/fs_watcher.py:198–214`).
  - On Linux, closing an fd doesn't wake a `select()` that is already blocked on it, so
    the join waits out the loop's `idle_timeout = 0.5`.
  - `start()` then re-discovers every watch path (5–34 ms), which includes project
    namespace scans.
  - `ArtifactWatcher.ensure_watches()` (line 216) already exists and is documented as
    "safe to call from the UI thread". It adds watches without a restart.
- **O(n²) `on_mount`, confirmed.**
  - Textual 8.2.8's `MessagePump._get_dispatch_methods` yields every class's `on_mount`
    along the MRO.
  - Fifteen `PromptTextArea` mixins *also* chain through
    `getattr(super(), "on_mount")()` (for example `_line_rendering.py:38`,
    `_yank_highlight.py:46`). I counted 18 `on_mount`/`_on_mount` definitions in the
    78-class MRO.
  - Each `LineRenderingMixin.on_mount` toggles CSS classes, which restyles the subtree.
- **Post-edit amplification.** One `ctrl+p` rebuilds `_build_highlight_map` two or three
  times at 7–11 ms each: once inside `edit`, then from the repo-mention and glossary
  context refreshes, plus a Jinja timer on the pump.
- **Post-open amplification.** Prompt warm-ups call
  `_refresh_visible_prompt_semantic_surfaces`, which always ends in
  `_schedule_selected_agent_semantic_refresh`. That is an Agents-detail repaint costing
  58–97 ms steady and 371 ms the first time. The selected agent's context usually didn't
  change, and the user is typing.
- **Prior art is already in the repo.**
  - The current-project chip already uses the right pattern. `peek_current_project_change_token`
    stats the MRU and reads the config token (time-gated), and the resolve runs on a
    worker.
  - The VCS `+` completion catalog already calls the loader with `prune=False`, behind a
    signature-keyed module cache, warmed by a thread worker.
  - The keymaps are the paths that never adopted either pattern.

### 3.4 Cross-cutting: the stall budget and GC (my additions)

The live TUI is PID 872820. It runs `sase tui` from the editable checkout, has been up
26 h, and shows 5.9 GB RSS, 41.5% average CPU, and 26 threads. Its stall log from
10:28 to 13:34 today shows:

- **317 loop hitches ≥1.5 s in 3.12 h: 1,123 s frozen, or 10.0% of wall time.** The
  median hitch was 3.6 s, p90 4.5 s, and max 8.5 s, spread evenly across the hours. A
  keypress at a random moment has roughly a 1-in-10 chance of waiting seconds.
- The top stack sources are unrelated to the prompt:
  - the Agents-detail debouncer `_fire_debounced_detail_update`: 76 rows;
  - clan runtime aggregation: 43 rows;
  - clan-tree resolution: 25 rows;
  - Textual strip/compositor rendering.
- **57 hitches had the main thread parked in `selectors.select` /
  `_read_from_self`.** The watchdog marks progress with `call_soon_threadsafe`, which
  wakes `select` at once. A main thread stuck there for seconds therefore couldn't get
  the GIL back. A worker holding the GIL, or a GC pass running on a worker, would do
  that. About 30 more hitches landed at allocation sites inside Textual rendering, such as
  `cache.py:__init__`, `Strip.__init__`, and `model.__hash__`. That is the signature of
  allocation-triggered GC.
- **GC scaling.** In my synthetic benchmark on the TUI's interpreter, a full collection
  cost about 50 ms per million simple tracked objects (1M → 48 ms, 6M → 326 ms), and
  `gc.freeze()` cut it to about 0 ms. cld measured 445–600 ms with 960k *real* objects,
  which have denser graphs. A 5.9 GB heap after 26 h makes multi-second gen-2 pauses
  plausible.
  - This is **consistent with the evidence, not proven**. Nothing in `src/sase` tunes or
    instruments the collector today.
  - RSS was 2.3–2.5 GB in August, and `sase-v3` flagged that as suspicious. `sase-v3` was
    later swept as stale, and RSS has since more than doubled.

So the keymaps' own code is the part this research can make fast. The "sometimes slow"
tail for `<space>` also depends on the app's global stall budget.

## 4. Disagreements and how I resolved them

| Question | Positions | Resolution |
| --- | --- | --- |
| Cache key for the snapshot | gem: MRU file `(mtime, size)` only. Others: MRU stat plus a project/Patch/config token | **MRU stat alone is not enough.** Disabling, renaming, or archiving a project changes validity without touching the MRU file, and the stale result would last the whole session. Key on the MRU stat plus the existing project-spec signature (`vcs_project_catalog_signature`) plus `current_config_token()`. Revalidate Patch state on a tick. Launch-time guards still protect against one stale entry. |
| How to make validation cheap | grk: rewrite the filter on Rust `record.launchable` / `record.vcs_kind`. gem: global `@lru_cache` on `detect_workflow_type`. cdx/cld/mus: keep the policy single-sourced and run it off-thread | **Move the existing function off the keystroke path first; don't change its semantics.** I verified the Rust and plugin semantics differ. Rust sets `vcs_kind="gh"` only from a `gh_<owner>__<repo>` directory name, and `"git"` only from `BARE_REPO_DIR`. The plugin reports `gh` for any non-bare `.git` workspace with a non-local remote. So `vcs_kind=None` can't prove a mismatch. A process-global `lru_cache` keyed by path goes stale when a remote or workspace changes, and it changes behavior for every caller (`ws_get_change_label` and others). Efficiency inside the worker (one record pass, per-build provider memo) is a follow-up. |
| Does `<space>` need a mount redesign? | mus: no. gem: high risk, not recommended. cdx: only after measuring. grk: keep-alive/reset. cld: Phase 2 fresh hot spare | **Measure after Phase 1, then do it if `<space>` must be ≤ 60 ms.** cld measured 92 ms from key to bar `on_mount` and about 110 ms remaining after the Phase 1 prototype. Compose + CSS and reflow + paint make up most of that, and only a pre-built bar removes the compose half. Prefer cld's *fresh hidden spare* over grk's reset-in-place: a new instance per session keeps today's undo, completion, vim, search, and frontmatter state guarantees. |
| Per-key worker or `to_thread` in the handler | Rejected unanimously | Agreed. A per-key worker stampedes on held keys and breaks ordering against `_vcs_mru_index`. An `await` inside a Textual callback still blocks the serial pump (`tui_perf.md` rule 2). |
| Is the watcher restart part of the problem? | Only cdx and cld found it | **Yes.** There is live stack evidence (12:37:48) plus cld's in-app timings. It must ship with the snapshot, or first-visit cycling stays slow. |
| GC, `on_mount`, Agents-detail repaint | Only cld | Verified (§3.3, §3.4). Each is a small, independent fix. |
| Mount-time worker storm (8–9 thread workers) and a ~27 ms first-mount import in `_refresh_dispatch_context_line` | Only gem | Plausible, and cheap to fix: stagger the non-essential warmers and hoist the imports. This is secondary hygiene, not a primary cause. |
| Does this cross the Rust core boundary? | grk/cld: no sase-core change needed. cdx: a batch resolver would belong in `sase_core` | **No sase-core change is needed for the fix.** The snapshot is TUI-side scheduling and caching around an existing Python policy function, and provider detection is a Python plugin hook. Move code into `sase_core` only if someone *re-implements* the validation policy as a batch resolver, and then add the wire, binding, and pin bump. |

## 5. Options considered (merged)

| Option | Effect | Verdict |
| --- | --- | --- |
| `prune=False` on key paths only | Removes the write; validation (about 20 ms) stays | Necessary, not sufficient |
| Memoize `is_launchable_project` or `detect_workflow_type` only | Cuts repeated work; `git` still runs on cache misses inside the key | Insufficient alone |
| Per-key worker / `asyncio.to_thread` in the handler | Ordering, stampede, and pump-blocking problems | Reject |
| Snapshot once at startup, never invalidate | Fast but stale after launches, `set-current`, or other TUIs | Reject |
| **App-owned snapshot, peek tokens, coalesced single-flight worker, ring pinned per prompt session** | Both keys use memory only; removes the subprocesses and 1–8 s cold spikes | **Do (Phase 1)** |
| **Pure catalog getters + `ensure_watches()` + wakeable `stop()`** | Removes 0.1–2.8 s first-visit spikes | **Do (Phase 1)** |
| **Coalesce highlight/context refresh per edit** | −10–20 ms per `ctrl+n/p` | **Do (Phase 1)** |
| **De-duplicate mixin `on_mount`** (also `on_unmount` and `on_worker_state_changed`) | −25–35 ms per `<space>` | **Do (Phase 1)** |
| **Skip or defer Agents-detail repaint driven by prompt warm-ups** | Removes 60–370 ms pump stalls right after open or cycle | **Do (Phase 1)** |
| **`gc.collect(); gc.freeze()` after startup loads, plus GC-pause logging** | Shrinks full-GC pauses (cld: 0.5 s → 56 ms) on *every* key | **Do (Phase 1)** |
| Stagger mount warm-ups; hoist the dispatch-line imports | A few ms to tens of ms on first open | Do (cheap hygiene) |
| **Explicit prompt-active state + fresh hidden spare bar** | `<space>` becomes a reveal (about 50–60 ms) | **Do (Phase 2), if measured `<space>` is still above target** |
| Overlay-docked bar (no reflow of the Agents list) | Maybe −15–25 ms more | Experiment only after Phase 2; it changes the UX |
| Drop markdown highlighting, rebind `<space>`, tune debounces | Little or no effect on the measured causes | Don't |
| Port MRU validation to Rust; a persistent index daemon | Doesn't change *when* the work runs | Don't do first |

## 6. Recommended solution

### 6.1 Phase 1: both keys become memory operations, and the spikes go away

Ship as one epic made of small, independent PRs. Do 1–2 first because both keys depend
on them.

1. **`LaunchableMruSnapshot`, app-owned, used by both keys.**
   - **Contents.** An immutable tuple of `(canonical, display)` pairs plus head-prefill
     metadata, a generation number, and an explicit `ready` / `loading` / `error` state.
     Keep "MRU is empty" distinct from "snapshot is cold".
   - **Build.** Use a single-flight thread worker (one build in flight, one pending,
     last-request-wins). It initially calls the *existing*
     `load_launchable_vcs_xprompt_mru_pairs(prune=False)` so the policy stays
     single-sourced in `vcs_xprompt_mru.py`. Publish to app state on the main thread with
     a generation check.
   - **Triggers.**
     - warm after first paint, next to the existing catalog warm-ups;
     - after `record_vcs_xprompt_usage` (launch) and `sase project set-current`;
     - when a tick sees the peek token drift (MRU `(mtime_ns, size)`, project-spec
       signature, config token).

     Follow `tui_perf.md` rule 10: ticks revalidate, they don't recompute.
   - **Keys.**
     - `_handle_vcs_mru_cycle_key` and `_resolve_vcs_xprompt_mru_head` only *peek*. They
       never read, stat, or spawn anything.
     - The first `ctrl+n/p` in a prompt session copies the snapshot ring into the text
       area. A burst then never touches app state again, and the next session picks up
       the new generation.
     - Add a regression test proving that the four prune classes, alias display forms,
       and the empty stop all still behave the same.
   - **Cold policy.** Startup warming makes this rare.
     - `<space>` opens and focuses an empty bar immediately. It applies the prefill later
       only if the same session is still mounted and its text and cursor are untouched.
     - `ctrl+n/p` with a cold snapshot shows a brief loading hint and leaves the text
       alone. It never queues edits to replay later.
   - **Pruning.** Never write from a key path. If the persisted prune is still wanted, do
     it in an explicit maintenance path that is concurrency-safe against a concurrent
     `record_vcs_xprompt_usage`, not in the snapshot worker.
   - **Authority.** Launch keeps revalidating the target through the existing guards. A
     stale snapshot must never allocate a project or resurrect one, and it must never
     call `resolve_ref`.
   - **Efficiency follow-up**, inside the worker only: one `list_project_records` pass per
     build, and provider detection memoized per build, keyed by project file.
2. **Pure catalog getters and non-blocking watcher growth.**
   - Split "return warm entries" from "request this project".
     `get_warm_prompt_catalog_assist_entries_exact` and the highlight getters return
     entries or a cold sentinel, and never start, stop, or join anything.
   - When a project is requested, add it to the desired set. Then compute its watch paths
     in a pump-free task (`spawn_pump_free_task` + `to_thread`) and call
     `ArtifactWatcher.ensure_watches(paths)` instead of `_restart_prompt_source_watcher()`.
     Reconcile the catalog once after the watches are installed, to catch changes made in
     between.
   - Make `ArtifactWatcher.stop()` wake its loop: add an eventfd or self-pipe to the
     `select` set, so teardown never blocks for 0.5 s anywhere.
3. **Coalesce per-edit work in the cycle handler.** Rebuild the highlight map once per
   edit or refresh cycle. Memoize `xprompt_arg_assist_entries_to_wire` per catalog
   object. A leading-tag swap doesn't need an immediate arg-hint refresh, and it doesn't
   need the Jinja diagnostics to run on the pump. Route that inspect through
   `spawn_pump_free_task`.
4. **De-duplicate `on_mount`** in `PromptTextArea`'s mixins. Remove the
   `getattr(super(), "on_mount")()` chaining, since Textual already dispatches each class.
   Do the same for `on_unmount` and `on_worker_state_changed`. Test that each defining
   class's body runs exactly once per mount.
5. **Scope prompt-driven semantic refresh.** `_schedule_selected_agent_semantic_refresh`
   should repaint the Agents detail only when the warmed context matches the selected
   agent's context. While a prompt is active, it should defer the repaint to dismissal.
   This is the `tui_perf.md` rule 13 "defer while typing" gate.
6. **GC policy.** Run `gc.collect(); gc.freeze()` once after `_mount_state_loads_done`.
   Optionally re-freeze during long idle windows when no prompt is mounted.
   - Register a `gc.callbacks` hook that adds gen-2 pause durations to the stall/perf log.
     That turns the §3.4 hypothesis into data in one day of use.
7. **Mount hygiene.** Stagger the non-essential prompt warmers by one paint, and hoist the
   imports in `_refresh_dispatch_context_line`.
8. **Instrumentation, in the same epic.** Extend `SASE_TUI_PERF` key-to-paint recording
   (today j/k only, `util/perf.py`) to `start_agent_from_patch` and the cycle keys. Add a
   `slow` bench (`bench_prompt_bar_keys.py`) for `<space>`, a single `ctrl+p`, and a
   6-key burst, against a fixture with about 30 MRU entries across projects and Patches.

**Expected after Phase 1**, from cld's prototype plus the removed spikes:

- `ctrl+n/p`: about 10–20 ms p50, with no first-visit or burst spikes from these paths.
- `<space>`: about 100 ms p50, with no 0.4–2 s cold or watcher outliers.

### 6.2 Phase 2: `<space>` becomes a reveal, not a rebuild

Do this if the Phase 1 measurement still shows `<space>` p95 above about 60 ms. That is
likely: compose, CSS, and reflow alone cost about 90 ms.

1. **Prerequisite: explicit prompt-active state.** Today `_prompt_input_active()` is
   `bool(self.query(PromptInputBar))`.
   - `sase-v2.2` gates the countdown tick on it, and so do auto-refresh, the FS-watcher
     callbacks, and detail-refresh guards. A hidden bar that stays mounted would therefore
     **permanently suppress those refreshes**.
   - Back the function with an `app._active_prompt_bar` reference that mount, activate,
     and detach maintain. Route the roughly 11 `"#prompt-input-bar"` lookups through one
     accessor. This also removes a DOM walk from every app-binding check.
2. **Hot-spare bar.**
   - During idle (after startup and after each dismissal), mount a *fresh* id-less
     `PromptInputBar` with `display: none`. Setting an id later doesn't index it for
     `query_one("#…")`, hence the accessor.
   - On `<space>`:
     1. seed the prompt context and text using the existing stack loaders;
     2. reveal the bar;
     3. call a new `activate()`, which takes over today's `on_mount` focus, cursor,
        title, and warm-up logic.
   - Dismissal keeps today's cancelled-history save. Other prompt modes (feedback,
     approve, markdown editor) keep their explicit remounts.

   Expected result: `<space>` at about 50–60 ms, made up of the reveal, a focus restyle,
   and one reflow/paint. If it must drop below one frame, the remaining lever is docking
   the bar as an overlay.

### 6.3 Separate track: the stall budget behind "sometimes"

Phases 1–2 guarantee that these keys never *cause* a stall and never schedule one right
after themselves. They can't stop a key from landing inside the 10% of wall time the
live TUI currently spends frozen in other work. Open a separate investigation covering:

- the Agents-detail debouncer and clan runtime aggregation, the top stack sources;
- GIL starvation by workers;
- RSS growth to 5.9 GB.

`sase-v3`, the RSS bug, was swept as stale even though the number has since more than
doubled. Phase 1 step 6 (GC logging) is the cheapest first piece of evidence for that
track.

## 7. Acceptance targets and guardrails

- **Targets**, against a normally loaded host:
  - warm `ctrl+n/p` key→paint p95 ≤ 16 ms, with the synchronous handler ≤ 5 ms;
  - `<space>` p95 ≤ 110 ms after Phase 1 and ≤ 60 ms after Phase 2;
  - the first `<space>` after startup is never blocked by a cold snapshot.

  Track maxima and watchdog rows, not just medians.
- **Structural tests**, cheap enough for `just check`. With a warm snapshot, the
  `ctrl+n/p` and `<space>` paths must perform **zero** of each of these:
  - MRU reads or writes;
  - `list_project_records` calls;
  - `subprocess.Popen`;
  - `ArtifactWatcher.stop`/`start` or thread joins.

  Also test:
  - the `on_mount` count equals the number of defining classes;
  - delayed or older snapshot generations can't overwrite text or reorder an in-flight
    cycle;
  - a cold `<space>` followed by typing is never clobbered by a late prefill.
- **Live check.** After deploying, restart the TUI (an editable install doesn't reload
  modules that are already imported). Then confirm the `SASE_TUI_PERF` samples and that
  no `tui_stalls.jsonl` hitches have these handlers on the stack.

## 8. Risks

- **One stale entry for one key press.** Serving the last snapshot means a project that
  was just disabled can appear in the ring briefly. That is the same contract as the
  current-project chip, and launch revalidates.
- **Patch entries** must keep using the offline Patch-name index. They should never be
  turned into `is_launchable_project` or `resolve_ref` calls; bare-git `resolve_ref`
  *creates* projects.
- **Watcher races.** Generation-own the desired watch set, and never let the UI thread
  wait on a join while the watcher thread waits on `call_from_thread`. Keep the polling
  fallback while watch coverage is incomplete.
- **`gc.freeze()`** keeps frozen objects that later become cyclic garbage alive until the
  next re-freeze. That costs a bounded amount of memory, which is acceptable.
- **The hot spare** must hook session identity correctly: mint a new `session_id` on
  activate, and keep the cancelled-history save for the outgoing session. This is the
  fiddly part, and it's why Phase 2 waits on Phase 1 measurements.
- **Measurement scope.** The data comes from one host with a 7-entry MRU and 3–4
  launchable projects. Today's cost grows with the number of known-project entries; the
  snapshot design does not.

## Appendix: evidence provenance

| Claim | Evidence |
| --- | --- |
| Live `ctrl+p` stalls (8.51 s MRU, 2.77 s watcher) | `tui_stalls.jsonl` rows at 12:37:48 and 12:38:05–08 (cdx; re-confirmed by lead) |
| 10% of wall time in hitches; select-parked and allocation-site hitches | Lead analysis of 726 rows, 10:28–13:34, PID 872820; `ps` showed etime 26 h, RSS 5.9 GB |
| Textual MRO dispatch plus mixin `super()` chaining | Installed Textual 8.2.8 `MessagePump._get_dispatch_methods`; `_line_rendering.py:38`, `_yank_highlight.py:46`, and 13 sibling mixins |
| `stop()` join versus `ensure_watches()` | `src/sase/ace/tui/util/fs_watcher.py:198–234, 264–276` |
| Rust `launchable` / `vcs_kind` semantics | `sase-core` `crates/sase_core/src/project_spec.rs:534–619` |
| GitHub provider runs `git config` | `sase-github` `src/sase_github/workspace_plugin.py:64–91` |
| GC scaling | Lead synthetic benchmark (1M/3M/6M objects → 48/155/326 ms; frozen → ~0 ms); cld's in-app 445–600 ms |
| Prior work | `sase-v2` (prompt-lag epic, landed 2026-08-28; `.2` gates the countdown on `_prompt_input_active()`); `sase-v3` (2.3–2.5 GB RSS bug, canceled as stale) |
| Measured app timings and prototypes | `__cld` §3 (headless real `AceApp`, sandboxed real state) |
| Handler with preloaded list (11.5×) | `__cdx` controlled measurements |
