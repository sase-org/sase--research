# Making `ctrl+n/p` project-stack cycling and `space` prompt activation fast

Researcher: mus (independent swarm report, `__mus` suffix).
Date: 2026-10-02. Codebase: sase checkout at `sase_47` (Python TUI under `src/sase/ace/`).

## What the two slow operations actually are

Both keymaps funnel through one shared synchronous loader, the VCS-xprompt MRU
("current project" stack) store in `src/sase/history/vcs_xprompt_mru.py`:

- **`ctrl+n` / `ctrl+p` in the prompt input widget** do not move a widget focus.
  In `PromptTextArea._on_key`
  (`src/sase/ace/tui/widgets/_prompt_text_area_key_handling.py:447-461`) they call
  `_handle_vcs_mru_cycle_key()`
  (`src/sase/ace/tui/widgets/_vcs_mru_cycling.py:385`), which cycles the prompt's
  leading workspace target (`+<project>` tag or `#` ref) through a ring built
  from `load_launchable_vcs_xprompt_mru()`. `ctrl+p` steps toward older entries,
  `ctrl+n` toward newer ones, with a terminal empty stop that deletes the target.
- **`space` activating the prompt widget** is `action_start_agent_from_patch`
  (`src/sase/ace/tui/actions/agent_workflow/_entry_custom.py:60`), which calls
  `_resolve_vcs_xprompt_mru_head()` → `load_launchable_vcs_xprompt_mru_pairs()`,
  then mounts a fresh `PromptInputBar` via `_show_prompt_input_bar_for_home()`
  (`src/sase/ace/tui/actions/agent_workflow/_prompt_bar_mount.py:403`).

So "make both fast" is mostly one problem: **the per-keypress/per-activation
`load_launchable_vcs_xprompt_mru*()` call is synchronous, uncached, and does
 disk I/O plus a pruning write on the UI thread.**

## Measured cost (this machine, 3 projects, 309 patches, 7 MRU entries)

Timed with the repo's own `.venv` Python against the real functions:

| Call | Cold (first use in process) | Warm (second call) |
|---|---|---|
| `load_launchable_vcs_xprompt_mru_pairs()` | **0.47 s – 5.34 s** (run-to-run variance; import + scan dominated) | **~24 ms** |
| `get_known_project_workspaces()` | 2 ms | 2 ms |
| `find_all_patches_cached()` | ~150 ms | fast (mtime-keyed) |
| Raw MRU JSON read | 0.1 ms | 0.1 ms |

Two observations matter more than the exact numbers:

1. **Cold cost is an import avalanche.** `-X importtime` on a first
   `load_launchable_vcs_xprompt_mru_pairs()` shows ~290 ms for the
   `sase.xprompt.loader` chain (directives → processor → workflow executor →
   llm_provider → launch_selection) and ~60 ms for `sase.ace.patch.cache`,
   pulled in lazily by `_resolvable_vcs_ref_index()`, plus the
   `project_discovery` (TUI modal) import inside the per-entry stale check and
   the `project_aliases`/`project_display_names` imports inside dedupe. The
   first `ctrl+n/p` (or first `space`) after TUI start pays all of it **on the
   event loop**, inside an async `_on_key`/action handler with no `await` —
   i.e. a straight UI freeze. The 5.3 s outlier is what the user feels when
   filesystem caches are cold; ~0.5 s is the floor.
2. **Warm cost (~24 ms) already exceeds the project's key-to-paint budget.**
   `sase/memory/tui_perf.md` targets p95 < 16 ms (`SASE_TUI_PERF=1`), and that
   24 ms was measured with only 3 projects and 7 MRU entries — it scales with
   project count, patch count, and MRU length (see below), and it excludes the
   rest of key handling, re-render, and completion-context refresh that runs
   after it in the same handler.

## Why every keypress is expensive: the work inventory

Each `ctrl+n/p` press (and each `space` activation) synchronously performs all
of this, with **no cache anywhere on the path** (verified: no memoization of
the launchable MRU exists):

1. JSON read of `~/​.sase/vcs_xprompt_mru.json` (cheap — the only cheap step).
2. `_resolvable_vcs_ref_index()`: `get_known_project_workspaces()` re-enumerates
   **all project records via the Rust binding on every call (no cache)**,
   `find_all_patches_cached()` re-lists all patch project files (mtime-keyed
   per file, but the directory walk + record iteration is per call), and
   `load_project_alias_map()` rebuilds the alias map.
3. Per-entry pruning over up to 100 MRU entries: `_is_stale_known_project_prefix`
   stats a spec path and calls `is_launchable_project()` per entry;
   `_vcs_prefix_provider_mismatched` reads the project spec file and runs
   `detect_workflow_type()` per entry.
4. **A possible disk write on the keystroke path**: when pruning drops an entry,
   `load_launchable_vcs_xprompt_mru_pairs()` calls `_save_vcs_xprompt_mru()`.
   A function named `load_*` mutating disk inside a key handler violates the
   project's own "keystroke paths are read-only" rule (`tui_perf.md` rule 11).
5. `_dedupe_mru_pairs()` runs `humanize_vcs_refs_in_text()` per entry.
6. `_cycle_vcs_mru_text()` re-normalizes and re-display-forms **all** entries per
   keypress (`_next_vcs_mru_index` + `_mru_entry_display_form`), i.e. O(n)
   catalog work per step while the user holds `ctrl+p` to walk the stack.

The `space` path then mounts the bar. Mount-time work was audited too and is
largely already correct: all eight completion-catalog warms
(`_warm_current_xprompt_assist_entries`,
`_warm_current_artifact_ref_completion_catalog`,
`_warm_vcs_project_completion_catalog`, model catalog, path inventory, history
words, prediction cache, placeholder cache) plus `_warm_dispatch_target_catalog`
are dispatched to background workers, and `_setup_home_prompt_context` is just
a timestamp plus a context object. So for `space`, the MRU-head resolution is
the fixable synchronous chunk; no mount redesign is indicated. (The "sometimes"
in "sometimes slow" fits this diagnosis: `space` is fast when the MRU snapshot
inputs are warm and no prune-write fires, slow on cold imports, large scans, or
a prune-triggered rewrite.)

This diagnosis also matches the project's standing rules rather than inventing
new ones: `tui_perf.md` rules 1 (never block the event loop), 8 (cache disk
reads keyed by mtime; never re-read per keypress), and 11 (keystroke paths are
read-only and prompt-free) each independently flag this call chain. The
`_file_completion_base._warm_vcs_project_completion_catalog` docstring even
names the same catalog-disk-touch hazard and the approved remedy (build once in
a background thread into a module-level cache).

## Options considered

1. **Cache the launchable-MRU snapshot keyed by change tokens; keystroke path
   reads cache only.** Keep `load_launchable_vcs_xprompt_mru_pairs()` semantics
   (including pruning rules) but compute the snapshot in a background worker and
   serve keypresses from the last snapshot. Invalidation key: mtime/size of the
   MRU JSON file plus the projects-dir change token the codebase already uses
   for refresh gating (`ace_refresh_tokens` / stat-only tokens, rule 13/14).
   Pruning writes move to the refresh path (or to launch/record time), keeping
   the keystroke path side-effect-free per rule 11. Repeated `ctrl+p` walks then
   cost O(1) ring arithmetic against a memoized normalized ring instead of O(n)
   re-normalization per step.
2. **Hoist/warm the lazy imports.** The cold ~0.5–5 s is dominated by first-use
   imports (`xprompt.loader` chain, `ace.patch.cache`, `project_discovery`,
   alias/display modules). Warm them once at TUI startup or on first prompt-bar
   mount in a worker (the codebase already has this pattern for the tag catalog
   via `ensure_project_tag_catalog`), so the first keypress never pays it.
   Alone this fixes the worst freeze but leaves the ~24 ms+ per-press steady
   state, so it complements option 1 rather than replacing it.
3. **Serve `space` from the same cache; mount first, fill prefill after.**
   `_resolve_vcs_xprompt_mru_head()` reads the cached snapshot (microseconds).
   If the snapshot is cold/absent, mount the home-mode bar immediately with the
   empty default and apply the MRU prefill when the worker lands (the codebase's
   rule-5 "show cached data instantly, then background reload" shape). This also
   removes the "sometimes" variance.
4. **Run the load in a worker per keypress.** Rejected: rapid `ctrl+p` repeats
   need strict ordering against the evolving `_vcs_mru_index` cursor; a cache
   (option 1) gives ordering for free, while per-press workers add
   queue/ordering machinery for no benefit.

## Recommended solution

**Do options 1 + 2 together, with 3 as the `space`-path consequence of 1:**

- Add a small module-level snapshot cache for the launchable MRU
  (entries + normalized display ring), invalidated by (MRU file mtime/size,
  projects-dir token). Both `_handle_vcs_mru_cycle_key()` and
  `_resolve_vcs_xprompt_mru_head()` read it synchronously — never disk.
- Refresh the snapshot in a background worker: on TUI startup / first prompt
  mount, on MRU record (the write path already knows when data changed), and on
  projects-dir token drift. Prune-and-save happens only on the refresh path,
  never inside a key handler.
- Warm the refresh path's import closure (`xprompt.loader`,
  `ace.patch.cache`, `project_discovery`, alias/display helpers) with the
  existing worker-warm pattern so neither the first `ctrl+n/p` nor the first
  `space` pays the import avalanche.
- Memoize the per-snapshot normalized ring so holding `ctrl+p` is O(1) per step.

Expected effect: per-keypress MRU work drops from ~24 ms warm / 0.5–5 s cold
to sub-millisecond cache reads, bringing both keymaps inside the 16 ms
key-to-paint budget even as project/patch counts grow; `space` additionally
loses its cold-start and prune-write stalls. Behavior contract (ring order,
forward/backward directions, terminal clear stop, the four prune classes,
tag display forms) is unchanged — the relevant suites are
`tests/ace/tui/widgets/test_prompt_vcs_mru_cycling.py`,
`tests/ace/tui/widgets/test_vcs_mru_cycling_logic.py`,
`tests/test_vcs_xprompt_mru_pruning.py`, and
`tests/ace/tui/test_entry_points_vcs_prefix_mru.py`.

Verification for the implementer: profile before/after with
`sase tui --profile`, `SASE_TUI_PERF=1` key-to-paint JSONL, and the stall
watchdog (`~/.sase/logs/tui_stalls.jsonl`); recipe and benches are in
`docs/perf_runbook.md`, `tests/perf/README.md`,
`tests/ace/tui/bench_tui_jk.py`. A regression test should fail a keystroke path
that touches disk (e.g. assert no file read/write during
`_handle_vcs_mru_cycle_key` with a warm snapshot, and assert the prune-write
fires only on the refresh path).
