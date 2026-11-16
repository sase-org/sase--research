# Research Report: Root Causes and Safe Optimization Plan for `sase` TUI Slowdowns

**Scope:** Diagnosis of recent and compounding slowdowns in `sase tui` (`AceApp`) across startup, background refresh, memory/GC behavior, and interactive responsiveness (`j`/`k`, `,j`, prompt bar, footer updates), using live telemetry logs (`~/.sase/logs/`, `~/.sase/perf/`), cProfile/importtime measurements, heap object accounting, and code inspection at commit `8254254e2f` / `73718c77e1`.

---

## Executive Summary

"The TUI has slowed down quite a bit lately (including startup)" is **not a single bottleneck**—telemetry reveals **two distinct recent regressions** stacked on top of **three structural scale bottlenecks** as `~/.sase` history has grown (`358 MiB` `agent_artifact_index.sqlite`, `45 MiB` `artifacts/index.jsonl` with `46,930` rows, `65,875` `dismissed_bundles/*.json`, `22 MiB` `artifact-links.json`, `20 MiB` `memory_reads.jsonl`, `14 MiB` `artifact_reads.jsonl`, `13 MiB` `agent_bead_touches.json`, `8,555` issues in `gh_sase-org__sase`):

1. **Critical Live Memory, Thread & CPU Catastrophe (Regression on 2026-11-16, commit `d26b581253`):**
   Adding per-selection hijack decision resolution (`_display_detail_footer.py` -> `_schedule_hijack_decision`) invokes `facts.resolve_and_decide` on a background thread pool whenever footer/selection state updates. When a row lacks `artifacts_dir`, `resolve_hijack_subject()` calls `find_named_agent()`, which executes an **unindexed full-tree `scan_agent_artifacts()`** (`15.38s`, `23,107` `AgentArtifactRecordWire`, `2.16 GiB` RSS, `797,212` GC objects per call) and falls back to `dismissed_bundles.rglob("*.json")` across **`65,875` files**. Even when `artifacts_dir` is present, it calls `find_agent_session_by_member_artifact_dir()` / `find_agent_session()`, which walk every `ace-run` directory in pure Python. With multiple concurrent worker threads (`asyncio_0`..`asyncio_30`), live `tui_gc_census` captured **`207,837` `AgentArtifactRecordWire`** (`9 × ~23.1k`), driving RSS to **`5.2–5.4 GiB` within `16–20s`** of startup and **`20.9–35.1 GiB` RSS (`49.0 GiB` virtual / `30.3 GiB` swap)** within **5–20 minutes**, leaving **14 live `asyncio_*` worker threads** stuck at exit.
2. **Startup Regression `+4.3s` in `AceApp.__init__` (Regression on 2026-11-12, commit `ea4121387b`):**
   `tui_startup.jsonl` shows an exact step jump between `671ff5bd` (`app_construct_seconds = 1.034s`) and `ea412138` (`6.205s`, staying at `5.236s` median in the latest 20 runs vs `0.728s` on Nov 1–6 and `0.903s` on Nov 7–12). `init_late_startup_state` -> `build_app_bindings()` -> `resolve_artifacts_subtabs()` synchronously loads configs for all 10 enabled projects. In `src/sase/config/local_trust_enforcement.py:92-94`, `_checkout_root_for_local_path()` passes `local_path.parent` (`.../proj/sase`) to `discover_project_root()`, which returns `.../proj/sase` instead of the primary checkout `.../proj`, failing the fast match in `local_trust_management.py:165` (`str(primary) == root_key`) and falling into an **$O(N^2)$ scan** across every registered project (`120` merged-config loads, `121` `axe_config_compose` calls, `100` `WorkspaceStore` initializations in `cProfile`). The exact same $O(N^2)$ storm repeats in cold `AgentIdentitySnapshot.current()` (`agents.load_from_disk.provider`).
3. **Eager Import Overhead (`app_module_import_seconds = 2.077s` median):**
   `python -X importtime` measures `2,123.7 ms` to import `AceApp`, **`65.5%` (`1,391.7 ms`)** inside `sase.ace.tui.actions.agents._core` eagerly pulling in `gate_turn`, `notification_gates`, `macro.models`, and `agent_detail` before Textual (`114.3 ms`) mounts. Total process start to Agents ready now has a median of **`11.97s`** (up to `53.9s`) and AXE ready **`13.20s`** (up to `54.0s`).
4. **Full-History Log Materialization in UI Detail Header & Caches (`3.1–5.6 GiB` pre-hijack steady RSS):**
   Even before `d26b581253`, long-lived TUI sessions (`8c4f728d` at `082f2bc7`) hovered at `3.06–5.57 GiB` RSS. Rendering one agent's detail header (`build_detail_header_summary`, `p50 = 1.25s`, `max = 18.62s`, `sum = 150.8s` in `tui_trace.jsonl`, measured `3.394s` on a single cold row) triggers full-project parses and permanent in-memory caches for `artifacts/index.jsonl` (`46,930` `ArtifactFile`, doubled to `93,824` in live census), `artifact_reads.jsonl` (`27,005–27,011` `ArtifactReadEvent`), `memory_reads.jsonl` (`23,037–23,051` `MemoryReadEvent`), and `agent_bead_touches.json` (`16,005` `BeadTouch`), alongside `3.4s` link-index builds (`22 MiB + 19 MiB`) and `gc.freeze()` (`513k–1,002k` frozen objects).
5. **Background Contention, Whole-Graph Delta Copies, & UI-Thread Stalls:**
   - `agents.bead_confirmation_warmup` hit **`p50 = 141.1s, max = 161.1s`** under contention (`load_stranded_report("gh_sase-org__sase")` reads `8,555` issues and runs 3 batched full-history index queries across `253` keys).
   - `artifact_delta` refreshes (`inflight_poll` / `watcher`, only `2–8` changed agents) copy and re-project the entire cached agent graph (`copy_agent_graph`), taking **`2.7s` median (`max = 12.8s`)** under scale/GIL contention.
   - Interactive latencies show `,j` (`p50 = 588.5 ms`, `p95 = 1,548.4 ms`), `prompt_space` (`p95 = 667.2 ms`), `j`/`k` (`p95 = 386.7 / 368.2 ms`), UI-thread `aggregate_clan_runtime` FFI calls on timer ticks (`33` hitches), UI-thread `.stat()` / file locks (`launch_context_source`, `_launchable_mru`), and Textual `FIFOCache` (`63,108` objects) / stylesheet stalls (`48.45s` under swap).

---

## 1. Evidence & Historical Timeline

### 1.1 Startup Latency Trajectory (`~/.sase/logs/tui_startup.jsonl`, `n = 2,255`)

Observed medians across the 3 epochs (`2026-11-01` through `2026-11-16`):

| Metric | Pre-Nov07 (`n=40`, Nov 1–6) | Pre-`ea412138` (`n=40`, Nov 7–12) | Latest (`n=20`, Nov 13–16) | Latest Max |
| :--- | ---: | ---: | ---: | ---: |
| `interpreter_cli_import_seconds` | `0.849s` | `0.839s` | `0.461s` | `1.060s` |
| `app_module_import_seconds` | `2.144s` | `2.046s` | `2.077s` | `3.382s` |
| **`app_construct_seconds`** | **`0.728s`** | **`0.903s`** | **`5.236s`** | **`7.566s`** |
| **`process_start_to_on_mount_seconds`** | **`1.588s`** | **`1.979s`** | **`6.086s`** | **`8.553s`** |
| `compose_seconds` | `0.013s` | `0.012s` | `0.012s` | `0.021s` |
| `on_mount_to_first_paint_seconds` | `0.489s` | `0.266s` | `0.455s` | `0.642s` |
| `visible_ready_seconds` (from `on_mount`) | `6.948s` | `7.693s` | `5.572s` | `46.934s` |
| **`agents_ready_seconds`** (total wall) | `8.491s` | `9.726s` | **`11.969s`** | **`53.934s`** |
| **`axe_ready_seconds`** (total wall) | `9.117s` | `10.296s` | **`13.196s`** | **`54.007s`** |

Exact startup change-point in `tui_startup.jsonl`:
- Row `2227` (`2026-11-12T10:05:40Z`, rev `671ff5bd`): `app_construct_seconds = 1.034s`.
- Row `2228` (`2026-11-12T10:33:18Z`, rev `ea412138`): `app_construct_seconds = 6.205s`.

*(Note: `agents_ready_seconds = process_start_to_on_mount_seconds + visible_ready_seconds`, verified directly on `9976747c`: `6.2539s + 5.3632s = 11.6172s`.)*

### 1.2 Memory & Swap Regression (`~/.sase/logs/tui_stalls.jsonl`)

Comparing pre-`d26b5812` vs post-`d26b5812` instances in `tui_stalls.jsonl`:
- **Pre-`d26b5812` long-lived instance `8c4f728d`** (`rev 082f2bc7`, started `2026-11-15T21:54:19Z`, `app_construct = 5.164s`): after `7.5–13h` uptime (`66` heartbeats), oscillated between **`3.06 GiB` and `5.57 GiB` RSS** (`0.50–0.76 GiB` swap), with `gc_freeze_count = 512,926–579,390`.
- **Post-`d26b5812` instances (`rev 8254254e`, 2026-11-16):**
  - `8542b466`: **`5.43 GiB` RSS at `19.6s`** -> **`20.85 GiB` RSS + `14.66 GiB` swap (`35.51 GiB`) at `319.7s`** (`16` active threads in stall dump, `14` surviving `asyncio_*` threads at exit in `tui.log`).
  - `4da97138`: **`5.27 GiB` RSS at `16.4s`**.
  - `9976747c`: **`5.19 GiB` RSS (`20,900,671` blocks, `gc_freeze_count = 1,001,673`) at `15.9s`** -> **`35.14 GiB` RSS (`133.8M` blocks) at `322.7s`** -> **`18.74 GiB` RSS + `30.25 GiB` swap (`48.99 GiB`, `370,071` major faults) at `1,226.4s`** (`gc_count = [12, 7, 797]`, `~74s` GC + `96–140s` hitch totals per 5m window).

Live opt-in GC survivor census on `9976747c` at `~111s` uptime (`2026-11-16T11:06:00Z`, `census_duration_s = 11.45s`, **`8,125,371` non-frozen survivors**, `garbage_count = 0`):

| Surviving Object Type | Count in `9976747c` | Primary Source Verified |
| :--- | ---: | :--- |
| `builtins.list` / `builtins.dict` | `3,961,252` / `2,362,039` | Wire records + nested markers + UI caches |
| `pathlib.PosixPath` | `402,220` | Artifact / scan / glob / cache paths |
| `AgentArtifactRecordWire` / `AgentMetaWire` | **`207,837`** / **`207,522`** | **`9 × ~23.1k`** full-tree `scan_agent_artifacts` in concurrent hijack workers |
| `ArtifactFile` | **`93,824`** | **`2 × ~46.9k`** rows parsed from `~/.sase/artifacts/index.jsonl` |
| `AgentSessionTurnWire` / `MonitorWire` / `GateWire` | `87,111` / `60,642` / `26,469` | Nested inside `207,837` `AgentArtifactRecordWire` |
| `FinalizerStatus{Summary,Instance,Runner}Wire` | `67,915` / `61,747` / `45,576` | Nested inside `207,837` `AgentArtifactRecordWire` |
| `WorkflowStateWire` / `DoneMarkerWire` / `PlanPathMarkerWire` | `35,640` / `33,435` / `26,298` | Nested inside `207,837` `AgentArtifactRecordWire` |
| `textual.cache.FIFOCache` (`Segment`, `Strip`) | **`63,108`** (`31,931`, `9,013`) | Rich/Textual per-option/line render caches |
| `ArtifactReadEvent` / `MemoryReadEvent` | `27,005` / `23,037` | Project-wide JSONL snapshot caches (`artifact_reads.py`, `memory_reads.py`) |
| `BeadNote` / `BeadTouch` / `BeadLink` / `Issue` / `BeadNotePreview` | `17,178` / `16,005` / `9,916` / `8,555` / `7,948` | Unfiltered project bead/touch caches (`8,555` issues in `sase`) |
| `NotificationPlusOne` / `Notification` | `14,544` / `4,261` | Direct notification provider (`1,917` rows reloaded 5× at startup) |
| `ArtifactRef{Document,File,Agent}Candidate` | `6,672` / `5,000` / `3,686` | `ArtifactRef` completion/highlight catalogs |

---

## 2. Detailed Bottleneck Analysis

### Bottleneck #1 (P0 Critical): Footer-Triggered Hijack Decision Storm Causes `207k` Wire Objects, `35 GiB` RSS, `65k`-File Rglobs, and Hung Worker Threads
- **Files:**
  - Trigger: `src/sase/ace/tui/actions/agents/_display_detail_footer.py:173-175, 213` and `src/sase/ace/tui/actions/agent_workflow/_leader_mode.py:562`
  - Unbounded pool cache: `src/sase/ace/tui/actions/agents/_hijack_decision_cache.py:89-141`
  - Subject resolver: `src/sase/agent/hijack/facts.py:70-134`
  - Name/session scanners: `src/sase/agent/names/_lookup_named.py:86-246` and `src/sase/agent/names/_lookup_groups.py:126-180`
- **Mechanism:**
  1. Every time `_apply_agent_footer_update()` runs (cursor move, display refresh, selection change), it calls `self._schedule_hijack_decision(current_agent)`, spawning an `asyncio.to_thread` task via `spawn_pump_free_task` with **no concurrency cap (`max_workers=1` absent)** and keyed by `(identity, roster_generation)` (so any background refresh invalidates the cache key).
  2. `_compute_hijack_decision_sync` calls `facts.resolve_and_decide` -> `resolve_hijack_subject()`.
  3. Whenever `row` lacks `artifacts_dir` (e.g., session container, claim row, named proc, or epic/workflow row), `facts.py:100` calls `find_named_agent(requested_name, include_dead=True)` -> `_lookup_named.py:102`:
     ```python
     snapshot = scan_agent_artifacts(projects_dir, ace_run_scan_options())
     ```
     This bypasses `agent_artifact_index.sqlite` and walks the entire filesystem! Measured standalone: **`15.378s`**, returning **`23,107` `AgentArtifactRecordWire`** (`2,164.4 MiB` RSS, `797,212` GC objects) per call. Multiply by 9 concurrent threads in-flight = **`207,963`** (`207,837` in live census!). If no live/on-disk artifact matches, `_lookup_named.py:214` falls back to `bundles_dir.rglob("*.json")` and parses **all `65,875` JSON files** in `~/.sase/dismissed_bundles` (`tui_stalls.jsonl` caught `asyncio_0..30` stuck in `_find_named_dismissed_bundle`).
  4. Even when `artifacts_dir` **is** present (`facts.py:104-124`), it still calls `find_agent_session_by_member_artifact_dir(artifacts_dir)` and (on `None`) `find_agent_session(requested_name)` -> `_lookup_groups.py:131`, which calls `iter_ace_run_artifact_dirs()` and parses `agent_meta.json` across all `23,000+` artifact dirs in pure Python!
- **Impact:** Severe GIL contention, `5.2 -> 35.1 GiB` RSS + `30 GiB` swap thrashing, `10–50s` stalls, and `14` worker threads blocking clean exit.

### Bottleneck #2 (P0 High): `$O(N^2)` Trust / Config Discovery Bug Adds `+4.3–5.2s` to Startup & `+6s` to Cold Provider Load
- **Files:**
  - Constructor call chain: `src/sase/ace/tui/actions/_state_init_late.py:373` (`build_app_bindings`) -> `src/sase/ace/tui/keymaps/bindings.py:49` (`resolve_artifacts_subtabs`) -> `src/sase/ace/tui/_artifact_tab_discovery.py:42-110` (`load_project_provider_records` -> `load_merged_config_for_local_path`).
  - Root-resolution bug: `src/sase/config/local_trust_enforcement.py:86-109` (`_checkout_root_for_local_path`) and `src/sase/config/local_trust_management.py:141-205` (`_project_identity`).
- **Mechanism:**
  1. `ace_handler.py:225` calls `set_include_local_config(False)`, which skips local config only for global reads—explicit `load_merged_config_for_local_path(config_path)` calls during provider tab discovery across all 10 enabled projects still execute local trust enforcement.
  2. When `local_path` is `.../proj/sase/sase.yml`, `_checkout_root_for_local_path` (`local_trust_enforcement.py:92-94`) sets `probe = local_path.parent` (`.../proj/sase`) and calls `discover_project_root(probe)`. Because `.../proj/sase` is a valid content dir, `discover_project_root` returns **`.../proj/sase`** instead of the checkout root **`.../proj`**. (Lines `103-105` already unwrap `.parent.parent` for `sase/sase.yml`, but only in the unreachable `found is None` fallback!)
  3. Consequently, in `local_trust_management.py:165`, `if str(primary) == root_key` (`".../proj" == ".../proj/sase"`) **fails for every canonical project**, falling into lines `173-205` where it loops over **every registered project**, calling `load_merged_config_for_local_path(primary_config)` (`120` calls, `121` Rust `axe_config_compose` calls) and `WorkspaceStore(str(primary), ...)` (`100` subprocess `git remote` probes), turning `O(N)` into `O(N^2)` (`+5.4s` measured inside `cProfile`).
  4. The exact same `collect_repo_inventory` $O(N^2)$ loop runs synchronously in `AgentIdentitySnapshot.current()` during cold `agents.load_from_disk.provider` (`6.35s` until `@lru_cache` warms `_discover_known_owner_roots`).

### Bottleneck #3 (P1 High): Full-Log Parses & Unbounded In-Memory Caches in Detail Header + Link Index + GC Freeze
- **Files:**
  - `src/sase/ace/tui/widgets/prompt_panel/_agent_display_header_summary.py:244-340` (`build_detail_header_summary`)
  - `src/sase/core/artifact_file_explicit.py:44-53, 207-255` (`read_artifact_file_index`, `_artifact_file_index_cache`)
  - `src/sase/ace/tui/artifact_reads.py:73-288` & `src/sase/ace/tui/memory_reads.py:65-280`
  - `src/sase/ace/tui/bead_touches.py` / `agent_bead_touches.json` (`13 MiB`)
  - `src/sase/ace/tui/relations/_native_link_index.py:296` (`links.index_build`)
  - `src/sase/ace/tui/util/gc_policy.py:392-400` (`gc.freeze()`)
- **Mechanism:**
  - Selecting an agent triggers `build_detail_header_summary` (`p50 = 1.25s`, `max = 18.62s`, `sum = 150.8s` in `tui_trace.jsonl`; `3.394s` on first row in clean probe). It parses entire append-only project logs into Python dataclass tuples and retains them in module-level caches:
    - `artifacts/index.jsonl` (`45 MiB`, `46,930` lines) -> `read_artifact_file_index` caches `tuple[ArtifactFile, ...]` and `list_indexed_artifact_files` does an $O(M)$ Python scan over all `46,930` rows (`2×` = `93,824` alive in census when refreshed concurrently or alongside `files_data.query_artifact_files`). Note `query_artifact_files` in `artifact_file_query_facade.py` already delegates filtering to Rust!
    - `artifact_reads.jsonl` (`14 MiB`) -> `27,011` `ArtifactReadEvent` cached in `_artifact_reads_snapshot_cache`.
    - `memory_reads.jsonl` (`20 MiB`) -> `23,051` `MemoryReadEvent` cached in `_memory_reads_snapshot_cache`.
    - `agent_bead_touches.json` (`13 MiB`) -> `16,005` `BeadTouch` cached.
  - `links.index_build` takes **`3.42s` (`max = 3.63s`)** ingesting `22 MiB` `artifact-links.json` + `19 MiB` `artifact-link-projection.json`.
  - Meanwhile, `gc_policy.py:396` runs `gc.freeze()` after initial startup loads settle—by which time `513k–1,002k` objects are alive—permanently pinning those startup caches/widgets into Python's immortal generation even after eviction/refresh.
  - Additionally, `agent_name_registry.json` (`41 MiB`), `dismissed_agents.json` (`5.1 MiB`, `85k+` entries), and `notifications.jsonl` (`1,917` rows reloaded **5×** during startup in `tui_trace.jsonl`) add steady CPU and RSS pressure.

### Bottleneck #4 (P1 High): Eager Module Imports (`2.08s`), AXE Startup (`4.1s`), and Deferred `bead_confirmation_warmup` (`141–161s`)
- **Import closure (`app_module_import_seconds = 2.08s` median):**
  `-X importtime` shows `sase.ace.tui.app` takes **`2,123.7 ms`**, of which **`1,391.7 ms` (`65.5%`)** is `sase.ace.tui.actions.agents._core` importing modal/action/gate/macro graphs (`_agent_enter_action` `597ms`, `_metadata_search` `454ms` -> `sase.gate_turn` `431ms` -> `sase.notification_gates` `424ms` -> `sase.macro.models` `260ms`, `agent_detail` `358ms`), while `textual.app` is only `114.3 ms`.
- **Background `agents.bead_confirmation_warmup` (`src/sase/ace/tui/actions/agents/_loading_bead_warmup.py:107-276`, `src/sase/bead/stranded_facts.py:67-239`):**
  Observed at **`p50 = 141.1s, max = 161.1s`** in `tui_trace.jsonl` (`n = 7`, `sum = 630s`). Calling `warm_stranded_work_reports` runs `load_stranded_report` per project (`gh_sase-org__sase` has `8,555` issues, `253` stranded candidates -> 3 batched `query_agent_artifact_index(include_full_history=True, include_hidden=True)` calls across 100-key OR-filters; `2.41s` standalone, `141–161s` when contending with disk/lock/swap/GIL activity).
- **AXE startup & refresh (`src/sase/ace/tui/actions/axe_display/_data.py:340-520`):**
  `axe.load_status` / `axe.collect` takes **`4.10s` median (`5.08s` max)** in `tui_trace.jsonl` (`1.24s` even clean offline) because `include_full_snapshots=True` eagerly runs `collect_chop_snapshot` across all `63` chops (`698` JSON reads + `651` 500-line log tails = `1,349` file reads) plus `axe_config.load_axe_config()` (`0.33s`) before the AXE tab is even visited.

### Bottleneck #5 (P1/P2 Medium-High): `load_agents` Decode/Revalidate, Whole-Graph Delta `prep`, and Interactive UI-Thread Work
- **`artifact_delta` `prep` (`src/sase/ace/tui/actions/agents/_loading_disk_delta.py:121-138`, `_loading_compute.py:605-650`, `_loading_graph.py:108-148`):**
  Every minor delta (`2–8` changed agents from `inflight_poll` or `fs_watcher`) calls `own_required_apply_snapshot` -> `copy_agent_graph` on the **entire** cached `Agent` list (`860k` calls / `408k` `isinstance` checks = `0.288s` at `166` rows, scaling linearly to **`~2s+` at `1,100–1,200` rows** and **`2.5–12.8s`** under GIL/swap contention).
- **`decode` & `tier1_index_revalidate` (`src/sase/ace/tui/models/_loaders/_meta_enrichment_wire.py`, `sase-core/crates/sase_core/src/agent_scan/index/selection.rs:84-118`):**
  In standalone `cProfile` before trust/retention warmups, `enrich_agent_from_meta_wire` ran `~1,000` times for `311` index records (`~3×` per agent), triggering `load_agent_workspace_retention()` (`1,027` calls) and `get_artifacts_dir()` -> `_filtered_project_records()`. When index marker signatures drift, `revalidate` rescans stale dirs (`11.17s` repairing `7,731/7,789` rows on a non-projected scan; `tier1_index_revalidate` median `disk = 3.52s` in `tui_agent_loads.jsonl`).
- **Interactive UI-Thread Stalls & Input Latency (`tui_jk.jsonl`, `tui_stalls.jsonl`):**
  - `,j` (`p50 = 588.5 ms`, `p95 = 1,548.4 ms`, `paint_ms = 625–770 ms`, `model_ms = 260–285 ms` in `tui_jk.jsonl`): `_unread_navigation.py` synchronously dismisses notification state and calls `_refresh_agents_display(list_changed=..., defer_detail=...)`, plus falls back via `_jump_to_next_stranded_agent`.
  - Timer-tick & focus hitches on the UI thread (`tui_stalls.jsonl`):
    - `gc_policy.tick_safe` (`35` hitches; `_run_idle_census` took `11.45s`!).
    - `agent_runtime_facade.aggregate_clan_runtime` called synchronously inside `patch_runtime_suffix_row` (`33` hitches across actions; `27` attributed to `h`).
    - `launch_context_source._tick` / `_broadcast` (`app.query(LaunchContextBar)`) and `_launchable_mru_tick` doing `.stat()` / lock opens (`temporary_override_state.py:100`) on the UI loop.
    - Textual `stylesheet.py:606` (`48.45s` stall in `9976747c`) + **`63,108` `FIFOCache`** objects during DOM updates / swap thrashing.

---

## 3. Do We Need Extra Instrumentation?

**No new instrumentation is required before starting fixes.** Existing TUI telemetry (`tui_startup.jsonl`, `tui_stalls.jsonl` + watchdog stacks, `tui_agent_loads.jsonl`, `SASE_TUI_PERF=1`, `SASE_TUI_TRACE=1`, `SASE_TUI_HEAP=1`, `SASE_TUI_GC_CENSUS=1`, `tools/tui_freeze_report`) already pinpointed **100% of the regressions and hotspots** above with microsecond/line-level attribution.

**Only after landing Phase 1–2**, two lightweight, low-overhead additions are recommended *only if verification shows residual noise*:
1. **Emit `worker_pool_active` / bounded queue depth** in `tui_memory_heartbeat` (`gc_telemetry.py`) to confirm background executor saturation stays near zero after fixing hijack lookups.
2. **Trace-only (`SASE_TUI_TRACE=1`) substage spans** inside `prepare_loaded_agents_worker_boundary` (`own_snapshot`, `incomplete_merge`, `runner_slots`, `fold`, `finalize_plan`) and `load_agents_from_disk.decode` (`meta_enrichment`, `retention`, `project_lookup`) if `prep` or `decode` still exceeds `200ms` after fixing hijack/delta ownership.

---

## 4. Safe, Phased Optimization Roadmap (With Risk Analysis)

All changes below are ordered by **impact ÷ risk** so the critical catastrophe is stopped immediately while complex refactors stay isolated and testable.

### Phase 1: Stop the Bleeding Immediately (Critical Fixes — Low/Medium Risk, Huge Win)

1. **Fix Hijack Decision Resolution & Unindexed Scans (`d26b5812` + `_lookup_named` / `_lookup_groups`):**
   - **Never call `scan_agent_artifacts()` or `rglob("*.json")` from a UI hover/footer background worker.**
   - In `src/sase/ace/tui/actions/agents/_display_detail_footer.py` and `_hijack_decision_cache.py`:
     - Only schedule `_schedule_hijack_decision` on `150–250ms` cursor-idle debounce (or lazily when `,` leader mode opens / `x` kill modal opens), **not** on every `j`/`k` cursor tick or footer redraw.
     - Bound `_hijack_decision_tasks` to a single latest-wins serial worker (`max_concurrency = 1`) and pass a `threading.Event` / cancellation token so superseded footer lookups abort before starting.
     - Key `_hijack_decision_cache` on a lightweight **row-local hijack fingerprint** (`(identity, status, pid, artifacts_dir, agent_session)`) rather than global `roster_generation`, preventing cache wipes on unrelated delta refreshes.
   - In `src/sase/agent/hijack/facts.py` and `src/sase/agent/names/_lookup_named.py` / `_lookup_groups.py`:
     - When `row` is an in-memory TUI `Agent` whose `status` is already terminal or row-local (`cheap_hijack_ingress_available` / already hydrated `agent_session`, `artifacts_dir`, `workspace_num`, `pid`), pass the TUI's already-loaded session/member rows (`deps`) instead of rescanning disk!
     - Back `find_named_agent()` and `_iter_agent_session_members()` with **indexed SQLite queries** (`query_agent_artifact_index` using `idx_agent_artifacts_agent_name_nocase` / `idx_agent_artifacts_agent_session_nocase` / `candidate_filter`) instead of `scan_agent_artifacts()` (`23k` rows / `2.16 GiB`) or `iter_ace_run_artifact_dirs()` (`23k` JSON reads). Add an index or `dismissed_agents` SQLite table lookup instead of `bundles_dir.rglob("*.json")` across `65,875` files (or cache/index `dismissed_bundles` incrementally).
   - **Expected impact:** Eliminates **`207k` `AgentArtifactRecordWire` (`~15–30 GiB` RSS + swap)**, `15s` scans, and the `14` hung worker threads on exit.

2. **Fix the `$O(N^2)` Checkout-Root Bug in `local_trust_enforcement.py` (`ea412138` Startup Regression):**
   - **Root fix (`src/sase/config/local_trust_enforcement.py:86-109`):** When `local_path.name in {"sase.yml", "sase.yaml"}` and `local_path.parent.name == "sase"` (or `discover_project_root(local_path.parent)` resolves to the `sase` config subdir inside `<checkout>/sase/sase.yml`), normalize/unwrap to the parent checkout directory *before* calling `local_trust_management._project_identity()`, AND/OR add an in-process `(config_token, projects_mtime)` memoized lookup map `{checkout_dir -> project_identity}` inside `local_trust_management.py` (`_project_identity`).
   - Also defer or make `resolve_artifacts_subtabs()` lazy: register artifact subtab keymaps lazily or cache resolved project provider records per config token off the synchronous `AceApp.__init__` critical path so startup does not block `app_construct_seconds` on 10 project configs.
   - **Expected impact:** Drops `app_construct_seconds` from **`5.24s` back to `<0.6–0.9s`** (`-4.3s` to `-4.6s` startup!), and cuts cold `AgentIdentitySnapshot.current()` (`provider` substage) from **`6.35s` down to `<0.3s`**.

3. **Defer AXE Full Snapshots Until Tab Activation (`axe.load_status`):**
   - In `src/sase/ace/tui/actions/axe_display/_data.py` and startup AXE loader: on startup when `initial_tab != "axe"` / `"services"`, pass `include_full_snapshots=False` (only check host/service status and counts for top bar chrome), deferring the `63`-chop / `635`-run / `1,349`-file tail scan until the Services/AXE tab is opened or explicitly refreshed.
   - **Expected impact:** Shaves **`~3–4s`** off `axe_ready_seconds` (`13.2s -> ~9s` combined with Phase 1 #2 -> `~4s`!) and cuts `1,349` startup file opens.

---

### Phase 2: Replace Full-Log Memory Caches & Rust-Offload Queries (Medium Risk, Major Steady-State & `j/k` Win)

1. **Stop Parsing Whole `45 MiB` / `20 MiB` / `14 MiB` / `13 MiB` Logs into Python RAM (`build_detail_header_summary` + `artifact_file_explicit`):**
   - Replace `read_artifact_file_index()` -> `_artifact_file_index_cache` (`46,930–93,824` `ArtifactFile` dataclasses cached in Python RAM) in `list_indexed_artifact_files()` / `list_artifact_files()` with targeted indexed queries (via `sase_core` `artifact_files_query(agent=..., raw_timestamp=...)` / a SQLite or offset index inside `sase-core`, avoiding loading all `46,930` rows to render 1 agent's header!).
   - Move `artifact_reads.jsonl` (`14 MiB`, `27k` events), `memory_reads.jsonl` (`20 MiB`, `23k` events), and `agent_bead_touches.json` (`13 MiB`, `16k` events) filtering to **bounded streaming / Rust index or per-project tail/SQLite lookup** (matching only the target agent's timestamp/name/session without keeping `66k+` Python objects pinned in `_artifact_reads_snapshot_cache` / `_memory_reads_snapshot_cache`).
   - Also keep `load_prompt_prediction_caches(include_archive=True)` disabled or Rust/SQLite-backed instead of `477 MiB` Python archive in memory, and fix the `5×` duplicate startup load of `notifications.jsonl` (`1,917` rows loaded repeatedly at startup).
   - **Expected impact:** Slashes baseline TUI RSS from **`3–5.6 GiB` down to `<300–500 MiB`** and brings `build_detail_header_summary` from **`1.25–18.6s` down to `<30–100 ms`**.

2. **Speed Up Imports (`AceApp` Lazy Action/Modal Imports):**
   - Break the monolithic eager import chain in `src/sase/ace/tui/actions/agents/_core.py` (`1,392 ms` of `2,124 ms`): defer heavy modal/action imports (`_agent_enter_action`, `_metadata_search` -> `sase.gate_turn` / `notification_gates` / `sase.macro.models`, `_marking_kill`) to action invocation or `on_mount` background pre-import *after* first paint (`call_later`), keeping only minimal keybinding signatures/panel scaffolds at class definition time.
   - **Expected impact:** Cuts `app_module_import_seconds` from **`~2.08s` to `<0.5–0.8s`** (`-1.3s+` cold startup).

3. **Bound / Index `bead_confirmation_warmup` & `stranded_facts`:**
   - In `src/sase/bead/stranded_facts.py` and `sase/core/bead_read`: maintain/use SQLite or cached open/in-progress bead index (do not re-parse `8,555` `issues.jsonl` lines + `17k` `BeadNote`s repeatedly on `bead_confirmation_warmup` and `_BEAD_CACHE`).
   - In `_loading_bead_warmup.py`: warm only currently **visible viewport + `WAITING`/unread rows** rather than all project-wide stranded sweeps on every `apply`, and run stranded sweep at lower priority / longer TTL unless the user opens Stranded modal or hits `,j` fallback.
   - **Expected impact:** Eliminates `141–161s` warmup storms and removes `Issue`/`BeadNote`/`BeadLink` memory bloat.

---

### Phase 3: Eliminate Whole-Graph Copying, UI-Thread FFI, & GC Freeze Pathology (Medium-High Effort)

1. **Incremental In-Place / Persistent Structural Patching for `artifact_delta` (`prep` `2.7s -> <50 ms`):**
   - Instead of calling `copy_agent_graph` across `1,100–1,200` `Agent` objects (`860k–6M` calls) on every `6`-agent `artifact_delta`, use copy-on-write / identity-scoped replacement for only the `6` changed `Agent` rows + their direct clan/parent container, reusing immutable sub-records without recursive `_value_contains_agent` reflection.
2. **Cache/Coalesce Enrichments During `decode` & Skip Stale Revalidate Churn:**
   - Deduplicate `enrich_agent_from_meta_wire` to once per unique `Agent` (`~300` calls instead of `~1,000`), memoize `load_agent_workspace_retention` + `get_artifacts_dir` per refresh batch.
   - Add an mtime/change-journal or coarse directory-mtime guard in `sase-core` (`selection.rs`) before stat'ing `200+` completed agent dirs on every `tier1_index_revalidate`.
3. **Remove Synchronous UI-Thread Work & Rethink `gc.freeze()`:**
   - Move `aggregate_clan_runtime` (in `patch_runtime_suffix_row`, `33` hitches) and `.stat()`/`FileLock` checks (`launch_context_source`, `_launchable_mru`) off the UI event loop into background workers with precomputed snapshots.
   - In `,j` (`_unread_navigation.py`): update notification state asynchronously after optimistic UI cursor/highlight movement and patch only the affected row/panel instead of full `_refresh_agents_display(list_changed=True)` (`625–770ms` paint).
   - **Fix `gc.freeze()` (`gc_policy.py:396`):** Only call `gc.freeze()` *before* loading mutable/evictable project caches (immediately after imports/`AceApp.__init__`, not after `15.9s` when `500k–1M` rows of transient agent/cache data are frozen permanently in RAM), or remove `gc.freeze()` once live object count drops below `<150k` objects (where full gen-2 GC takes `<20 ms`, making `11.45s` `tui_gc_census` / `24–74s` GC pauses vanish!).

---

## 5. Recommended Solution

**Take a focused, 3-step surgical path starting immediately on `sase` (with follow-up SQLite/query support in `sase-core`):**

1. **Immediate Hotfix (Today, Safe & Minimal Scope):**
   - **Fix the hijack worker storm (`d26b5812` follow-up):** Debounce & serialize `_schedule_hijack_decision` (`max_concurrency=1`), use a row-local cache key (not global `roster_generation`), pass already-loaded TUI session rows/artifacts into `facts.resolve_and_decide`, and **forbid `scan_agent_artifacts()` and `bundles_dir.rglob("*.json")` from `facts.py` / interactive TUI paths**—route `find_named_agent` and `find_agent_session*` through bounded `query_agent_artifact_index` (`candidate_filter` on `agent_name`/`agent_session`).
   - **Fix the `ea412138` trust root bug (`local_trust_enforcement.py:92`):** Unwrap `.../proj/sase/sase.yml` to `.../proj` *before* `discover_project_root` / `_project_identity` lookup (plus memoize `_project_identity` per config token), and defer `axe.collect(include_full_snapshots=True)` until the Services/AXE tab opens.
   - **Expected Immediate Gain:** RSS drops from **`5.2–35.1 GiB` back below `<1–3 GiB`**, `14` hung threads disappear, startup `process_start_to_on_mount` drops from **`~6.1s` to `~1.7s`**, and `axe_ready` drops **`~3–4s`**.

2. **Short-Term Architecture Fix (This Week — `sase-core` + `sase`):**
   - Eliminate full-file Python caches for `artifacts/index.jsonl` (`46.9k` `ArtifactFile`), `artifact_reads.jsonl` (`27k`), `memory_reads.jsonl` (`23k`), `agent_bead_touches.json` (`16k`), and `issues.jsonl` (`8.5k`) by pushing per-agent / per-bead filtered lookups into `sase-core` (Rust SQLite / indexed readers) so only the ~10–50 rows needed for display enter Python RAM, and switch `link_index_build` / `bead_confirmation_warmup` to lazy/on-demand incremental updates.
   - Lazy-load heavy action modules out of `sase.ace.tui.actions.agents._core` (`-1.3s` import) and move `gc.freeze()` right after imports (or remove it once Python heap object count shrinks from `8.1M` -> `<200k`).

3. **Follow-Up Responsiveness Pass (Next):**
   - Replace whole-roster `copy_agent_graph` in `artifact_delta` `prep` with targeted per-row copy-on-write updates (`prep` `2.7s -> <50 ms`), offload timer-tick `aggregate_clan_runtime` and `,j` disk/panel work off the UI thread, and verify gains directly against existing `tui_startup.jsonl`, `tui_stalls.jsonl`, `tui_agent_loads.jsonl`, `SASE_TUI_PERF=1`, and `SASE_TUI_GC_CENSUS=1` without needing new heavy instrumentation upfront.
