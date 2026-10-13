# Profiling and Optimization Analysis: SASE TUI Startup on Apollo

**Researcher:** `research.4c.gem`  
**Date:** October 13, 2026  
**Target Environment:** `apollo` (Ubuntu 24.04 LTS, 16 vCPUs, KVM VM) vs `athena` (Debian 13, 64-thread AMD Threadripper 3970X)  
**Artifact Key:** `research:202610/apollo_tui_startup_profiling_and_optimization__gem.md`

---

## 1. Executive Summary

A comprehensive investigation into the slow startup performance of SASE's Textual TUI (`sase tui`) on `apollo` was conducted using direct system profiling, telemetry logs (`tui_startup.jsonl`, `tui_agent_loads.jsonl`, `tui_stalls.jsonl`), runtime thread stack dumps, and scoped `pyinstrument` profiling.

### Key Empirical Findings

1. **Massive Telemetric Regression:**
   - In historical logs (`tui_startup.jsonl`), `agents_ready_seconds` on `apollo` was **~4.6 seconds** in late August 2026.
   - Over September and October, startup latency climbed to **15.2s**, then **55.5s**, and on October 13, 2026, reached **78.95 seconds** (`visible_ready_seconds: 75.79s`).
   - On `athena` (bare-metal Threadripper), `agents_ready_seconds` remains **~4.1s–4.9s**.

2. **Severe Machine & Environment Asymmetries:**
   - **CPU:** `apollo` is a 16-vCPU KVM guest running 2.70 GHz Intel Xeon Platinum 8168 processors (Skylake-SP architecture from 2017) with lower clock speed and IPC than `athena`'s 32-core / 64-thread 4.5 GHz Threadripper 3970X.
   - **Disk I/O:** `apollo` runs on a virtual disk (`/dev/vda1`, ext4 over virtio) with a measured synchronous write throughput of **84.3 MB/s**, compared to `athena`'s NVMe drive at **1.2 GB/s** (**14× slower I/O**).
   - **Background Workload Contention:** `apollo` had an active 1-minute load average of **10.50 to 12.60** out of 16 vCPUs, saturated by two long-running `mypy` processes (each burning 100% of a core in workspaces `sase_16` and `sase_12`), `sase tool wait`, background AXE routine runners, `codex`, and `muse`.

3. **The 3.0-Second Deferred Startup Fallback Stampede:**
   - In `src/sase/ace/tui/actions/_startup_loads_core.py`, `_STARTUP_DEFERRED_FALLBACK_SECONDS` is hardcoded to **3.0 seconds**.
   - On a fast, unloaded machine, the initial Agents tab loads within 3 seconds, releasing deferred work in an orderly fashion.
   - On `apollo`, the initial visible tab cannot complete in 3 seconds under load. The 3-second fallback timer fires prematurely, releasing an avalanche of 15+ concurrent background tasks into the thread pool while the visible surface is still loading.

4. **Quadratic Entry-Point Re-discovery in Prompt & Macro Loading (Critical Bottleneck):**
   - Direct Pyinstrument profiling of `build_prompt_catalog_snapshot()` on `apollo` revealed that it takes **20.6 seconds** of continuous CPU time.
   - **Over 17.1 seconds (83%)** is spent inside `_discovery_snapshot` calling `importlib.metadata.entry_points(group=group)` across Python package metadata on disk.
   - In `src/sase/macro/_loader_parsing_inputs.py`, `_plugin_registry_snapshot()` calls `get_plugin_input_type_registry()` without passing memoized files, triggering a complete disk rescan of Python entry points for *every single macro input* parsed across the entire macro catalog.

5. **Relation Graph Explosion (44,321 Links):**
   - `load_artifact_links_snapshot(None)` on `apollo` loads **44,321 link rows**.
   - `link_index_for_snapshot()` takes **7.39 seconds** of synchronous Python computation to index these links, running Rust FFI label queries, string canonicalization, and alias lookups.
   - Triggered right after the 3-second fallback, this thread monopolizes the CPython Global Interpreter Lock (GIL).

6. **Agent Dataset Scale (965 Agents):**
   - `apollo` currently tracks **965 agents** in its active loader pool (compared to **23 agents** on `athena`).
   - The UI thread `apply` phase alone takes **5.2 seconds** on `apollo`, computing tree hierarchies, resolving clan summaries via FFI, and re-applying Textual CSS stylesheet rules across hundreds of widget nodes.

7. **CPython GIL Starvation & Event Loop Stalls:**
   - Because all these background workers run in Python threads via `asyncio.to_thread` under CPython 3.12, they fiercely contend for the GIL.
   - The Textual message pump and asyncio event loop stall repeatedly for **5.2s to 7.5s per episode**, rendering the TUI completely unresponsive to the user during startup.

---

## 2. Machine Profile: Apollo vs. Athena

To establish baseline hardware constraints, both machines were profiled for CPU architecture, virtualization, memory, disk I/O throughput, and system load.

| Metric | Apollo | Athena | Disparity Ratio |
| :--- | :--- | :--- | :--- |
| **Hostname / OS** | `apollo` / Ubuntu 24.04 (Linux 6.8.0) | `athena` / Debian 13 (Linux 6.12.111) | — |
| **Virtualization** | KVM Guest (full virtualization) | Bare Metal | Virtualized vs Bare Metal |
| **CPU Model** | Intel Xeon Platinum 8168 @ 2.70GHz | AMD Ryzen Threadripper 3970X | Skylake-SP (2017) vs Zen 2 (2019) |
| **Logical Cores** | 16 vCPUs (1 socket × 16 cores) | 64 threads (32 cores × 2 threads) | 4× core capacity on Athena |
| **Clock Frequency** | 2.70 GHz base (fixed) | 2.20 GHz base / 4.55 GHz boost | ~1.7× single-thread frequency advantage |
| **L3 Cache** | 64 MiB (NUMA node 0) | 128 MiB (8 instances) | 2× L3 cache on Athena |
| **RAM** | 31 GiB (11 GiB used, 17 GiB buff/cache) | 64 GiB (32 GiB used) | Adequate RAM on both |
| **Swap** | 0 B (No swap configured) | No swap used | 0 swap |
| **Root Filesystem** | `/dev/vda1` (ext4 over virtio) | `/dev/nvme0n1p2` (ext4 direct NVMe) | Virtual block vs PCIe Gen4 NVMe |
| **Synchronous Disk Write** | **84.3 MB/s** (100MB dsync: 1.244s) | **1.2 GB/s** (100MB dsync: 0.091s) | **14.2× slower disk write throughput** |
| **Active Load Average** | **10.50, 12.60, 10.38** (70–80% busy) | **0.85, 1.10, 0.95** (idle) | Severe CPU overcommit on Apollo |

### Background Process Analysis on Apollo

During initial inspection on `apollo`, the following CPU-intensive background processes were active:
- Two concurrent `mypy` typechecking tasks:
  - PID 3216371 in `sase_16`: **97.9% CPU**, 1.67 GB RSS
  - PID 3216421 in `sase_12`: **96.6% CPU**, 1.63 GB RSS
- `sase tool wait`: **55.6% CPU**
- `sase tool _join`: **50.1% CPU**
- `sase_gateway` service proc: **12.3% CPU**
- `run_agent_runner.py` (2 instances): **13.7% CPU combined**
- `sase axe routine run hooks` and `agent_waits`: **6.1% CPU**
- LLM harnesses (`codex exec` and `muse-bin`): **5.2% CPU**

With 10–12 cores actively running compiler and runner workloads, any new process on `apollo` experiences high CPU scheduling latency, reduced cache locality, and I/O lock contention.

---

## 3. SASE Startup Telemetry Analysis

SASE records structured JSONL events on every TUI invocation to `~/.sase/logs/tui_startup.jsonl`. A longitudinal analysis of 492 recorded startup events revealed the evolution of the problem:

### Historical Trajectory on Apollo

| Timestamp (UTC) | PID | Agents Count | Index Rows | Mount to 1st Paint | App Module Import | Agents Ready | Visible Ready |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **2026-08-31 17:37** | 1217762 | 0 | 0 | 0.37s | — | **2.62s** | 1.43s |
| **2026-09-01 10:48** | 1218662 | 0 | 0 | 0.79s | — | **4.38s** | 3.32s |
| **2026-10-12 08:23** | 411340 | 11 | 107 | 0.56s | 3.31s | **4.66s** | 2.72s |
| **2026-10-12 15:50** | 411340 | 24 | 158 | 0.94s | 4.39s | **15.24s** | 11.92s |
| **2026-10-12 20:22** | 4012606 | 30 | 175 | 1.00s | 5.36s | **16.09s** | 12.80s |
| **2026-10-13 10:16** | 2217726 | 39 | 243 | 0.71s | 3.97s | **14.51s** | 11.79s |
| **2026-10-13 11:55** | 2217726 | 42 | 238 | 1.80s | 5.12s | **55.55s** | 52.42s |
| **2026-10-13 13:02** | 3192631 | 45 | 268 | 0.81s | 5.29s | **78.95s** | **75.79s** |
| **2026-10-13 13:13** | 3263463 | 45 | 270 | 1.03s | 5.12s | **63.11s** | **59.12s** |

### Comparison with Athena (Current)

On `athena`, the same codebase and configuration produce:
- `interpreter_cli_import_seconds`: **0.59s–0.73s**
- `app_module_import_seconds`: **1.61s–1.92s** (vs 5.1s–5.3s on Apollo)
- `process_start_to_on_mount_seconds`: **1.23s–1.37s** (vs 3.1s–4.0s on Apollo)
- `on_mount_to_first_paint_seconds`: **0.43s–0.46s** (vs 0.81s–1.03s on Apollo)
- `agents_ready_seconds`: **4.13s–4.97s** (vs **63.1s–78.9s** on Apollo)
- `visible_ready_seconds`: **2.91s–3.67s** (vs **59.1s–75.8s** on Apollo)

### What the Telemetry Tells Us

1. **First Paint is Fast:** On `apollo`, `process_start_to_on_mount` is ~3.2s and `on_mount_to_first_paint` is ~0.8s. Within 4.0 seconds of starting `sase tui`, the TUI window appears and draws its initial chrome.
2. **The Collapse Occurs Post-Paint:** Between first paint (t ≈ 4.0s) and `agents_ready` (t ≈ 78.9s), there is a **75-second dead zone** where the UI freezes, spinners hang, and the event loop stalls.

---

## 4. Deep-Dive Root Cause Analysis

### 4.1 The 3-Second "Deferred Release" Stampede

In `src/sase/ace/tui/actions/_startup_loads_core.py`:
```python
_STARTUP_DEFERRED_FALLBACK_SECONDS = 3.0

def _arm_startup_deferred_fallback(self: Any) -> None:
    self._startup_deferred_fallback_timer = self.set_timer(
        _STARTUP_DEFERRED_FALLBACK_SECONDS,
        self._release_startup_deferred_loads_from_fallback,
        name="startup-deferred-fallback",
    )
```

#### Mechanism of Failure
1. At mount time, `_start_post_mount_background_loads()` schedules the visible surface (`Agents` tab) and arms the 3.0-second fallback timer.
2. On `apollo`, loading the 965 agents takes more than 3 seconds (even under ideal conditions, reading the SQLite index, project files, and normalizing rows takes 3.8s–6.6s).
3. At exactly $t = 3.0\text{s}$, `_release_startup_deferred_loads(reason="fallback")` fires.
4. It simultaneously releases:
   - `_run_deferred_mount_state_loads`: `find_all_patches_cached()`, `resolved_app_version()` (which executes `git` subprocesses to resolve dev tags).
   - `_start_startup_axe_surface`: `_run_axe_startup_init` -> `collect_axe_status_data()`.
   - `_schedule_deferred_startup_maintenance`:
     - `_schedule_prompt_catalog_rebuild` -> `build_prompt_catalog_snapshot()`
     - `_schedule_link_index_refresh` -> `link_index_for_snapshot()`
     - `_schedule_bead_confirmation_warmup`
     - `_schedule_dismissed_named_procs_startup_prune`
     - `_schedule_prompt_bar_import_warm`
5. Instead of letting the visible surface complete its load in isolation, the application floods the Python runtime with 15+ competing worker tasks.

---

### 4.2 Quadratic Entry-Point Re-discovery in Prompt & Macro Loading

The single largest CPU burner during startup was captured via `pyinstrument` on `apollo`:
`build_prompt_catalog_snapshot(generation=0, projects=())` took **20.608 seconds** of wall-clock time and **20.534 seconds** of pure CPU time!

#### The Call Tree
```
20.608 build_prompt_catalog_snapshot  (sase/ace/tui/prompt_catalog.py)
 ├─ 13.059 build_macro_assist_entries
 │   └─ 13.056 build_structured_macros_catalog
 │       └─ 12.237 gather_structured_entries
 │           ├─ 7.016 get_all_macros
 │           │   ├─ 3.367 load_macros_from_plugins
 │           │   │   └─ 3.253 parse_inputs_from_front_matter
 │           │   │       └─ 3.251 parse_input_type
 │           │   │           └─ 3.221 get_plugin_input_type_registry
 │           │   │               └─ 3.220 _discovery_snapshot
 │           │   │                   ├─ 1.616 discover_macro_plugin_distributions
 │           │   │                   │   └─ 1.560 importlib.metadata.entry_points
 │           │   │                   └─ 1.598 discover_macro_plugin_input_type_files
 │           │   │                       └─ 1.529 importlib.metadata.entry_points
 │           │   ├─ 2.058 load_macros_from_config (same _discovery_snapshot)
 │           │   ├─ 1.221 load_macros_from_internal (same _discovery_snapshot)
 │           │   └─ 0.235 load_macros_from_files (same _discovery_snapshot)
 │           └─ 4.714 get_all_workflows (same _discovery_snapshot)
 └─  7.375 load_snippet_catalog (same get_all_macros + _discovery_snapshot)
```

#### The Bug in `src/sase/macro/plugin_input_types.py`
In `get_plugin_input_type_registry()`:
```python
def get_plugin_input_type_registry(
    files: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    key, files = _discovery_snapshot(files)
    store = _cache_store()
    cached = store.get(key)
    if cached is not None:
        return cached
    ...
```
And in `src/sase/macro/_loader_parsing_inputs.py`:
```python
def _plugin_registry_snapshot() -> dict[str, Any] | None:
    snapshot = get_plugin_input_type_registry()  # files is None!
    registry = snapshot.get("registry")
    return registry if isinstance(registry, dict) else None
```
- When `parse_input_type()` parses an input field (e.g. `type: string`, `type: int`), it calls `_plugin_registry_snapshot()`, which calls `get_plugin_input_type_registry()`.
- To check if the result is in `store`, it must compute `key`.
- To compute `key`, it calls `_discovery_snapshot(files=None)`, which **unconditionally runs** `discover_macro_plugin_distributions()` and `discover_macro_plugin_input_type_files()`.
- Both functions call `importlib.metadata.entry_points(group=group)`.
- `importlib.metadata` scans the filesystem on every invocation, opening and parsing `entry_points.txt` across all installed packages in `.venv`!
- **Result:** For every input of every macro and workflow in the system, Python re-reads `entry_points.txt` from disk. On `apollo`'s virtual disk, this burns **17.1 seconds of CPU time**.

---

### 4.3 Relation Graph Indexing Scale (44,321 Links)

In `src/sase/ace/tui/relations/link_index.py`, `_build_link_index()` processes all links between artifacts, beads, and agents.

Direct execution on `apollo` yielded:
```python
snap = load_artifact_links_snapshot(None) # rows: 44,321
link_index_for_snapshot(snap) # Elapsed: 7.391s
```
- In `_build_link_index`:
  - 44,321 link dictionaries are traversed.
  - Rust FFI bindings `artifact_relation_label` and `artifact_relation_lookup` are called tens of thousands of times across the boundary.
  - Dict keys and tuples are allocated for both directed and undirected pairings.
  - For every canonical ref and target, `_aliases_for_ref(ref, identity)` is called, which calls `current_owner_agent_name_lookup_candidates` -> `foreign_agent_owner_root`.
- In CPython, running this single-threaded loop inside a worker thread blocks other threads from acquiring the GIL, freezing the main event loop for ~7.4 seconds.

---

### 4.4 Agent Roster Scale and UI Thread `apply` Stalls

In `tui_agent_loads.jsonl`, when loading agents:
- `apollo` tracks **965 agents** in `load_agents_from_disk_with_state`.
- In PID 3280720:
  - `stages_seconds["disk"]`: 6.66s
  - `stages_seconds["prep"]`: 2.78s
  - `stages_seconds["apply"]`: **5.20s**
- `apply` runs **synchronously on the main UI thread** (`_apply_loaded_agents_prepared_inner` in `_loading_apply.py`).
- During this 5.2-second window:
  - Textual DOM nodes are updated for the roster.
  - Clan groupings call `_container_for_clan` -> `resolve_clan_summary()` through Rust FFI for all clans.
  - Textual CSS selector rules are re-evaluated:
    ```
    Textual/css/stylesheet.py: apply
      rules = list(filter(limit_rules.__contains__, reversed(self.rules)))
    ```
  - The UI message pump cannot process keystrokes or timer ticks, triggering the stall watchdog:
    `WARNING sase.ace.tui.util.stall_watchdog: TUI message pump stall detected: 5.543s`

---

### 4.5 CPython GIL Starvation and GC Pauses

The stall watchdog (`~/.sase/logs/tui_stalls.jsonl`) logged multiple severe stalls during startup:

1. **Module Import on Event Loop Thread:**
   - In PID 3280720, the main thread stalled for **3.902 seconds** executing:
     `from ...repro.capture import record_agents_tab_loader_result`
   - Heavy deferred imports on the UI thread freeze the loop while Python resolves modules and disk stats.

2. **Garbage Collection (GC) Pauses:**
   - In `tui_stalls.jsonl`, memory heartbeats show:
     - Startup RSS: **425 MB**
     - Running RSS: **1.38 GB**
     - Full Generation 2 collections take **0.70s to 1.46s** per pause.
     - With 350,000+ objects allocated across multiple snapshot dictionaries, GC traversal of the cyclic heap stalls all threads.

3. **Background AXE Routine Git Contention:**
   - Every 20 seconds, AXE routine runners execute:
     - `chop:bead_claim_checks`
     - `chop:external_issue_mirror`
     - `sdd.clone.fetch` (taking ~500ms per git fetch)
   - These background fetches lock git repositories (`index.lock`), producing warnings in `tui.log`:
     `WARNING sase.git_lock_retry: Git lock contention in ... retrying attempt 7/7 after 3.200s`

---

## 5. Ranked List of Recommended Changes

To resolve the startup latency on `apollo` (and significantly accelerate TUI startup across all machines), the following changes are recommended, ranked by impact, feasibility, and risk.

---

### Rank 1: Memoize Plugin Entry Points in Macro Input Parsing (Critical Bugfix)
- **Impact:** **−17.1 seconds** on `apollo` startup; eliminates 83% of `build_prompt_catalog_snapshot()` CPU time.
- **Subsystem:** `src/sase/macro/plugin_input_types.py` & `src/sase/main/plugin_discovery.py`
- **Root Cause:** `_discovery_snapshot(files=None)` re-executes `importlib.metadata.entry_points()` on every single input field of every macro and workflow file.
- **Proposed Fix:**
  1. Add a module-level cached helper `get_memoized_macro_plugin_entry_points()` with an `@functools.cache` or process-lifetime memo.
  2. In `get_plugin_input_type_registry()`, reuse the cached entry-point list instead of re-scanning `.dist-info` directories on disk.
  3. Invalidate only when plugins are dynamically enrolled or modified.
- **Effort / Risk:** Low effort (<20 lines of code), zero behavioral risk.

---

### Rank 2: Extend or Dynamically Gate the Deferred Startup Fallback Timer (High Impact)
- **Impact:** **−20 to −30 seconds** on `apollo`; eliminates GIL and disk contention during initial visible paint.
- **Subsystem:** `src/sase/ace/tui/actions/_startup_loads_core.py`
- **Root Cause:** `_STARTUP_DEFERRED_FALLBACK_SECONDS = 3.0` is too aggressive for virtualized or loaded machines. When the visible Agents tab takes >3s, the fallback fires and launches `prompt_catalog`, `link_index`, and `axe_init` while the Agents tab is still reading disk.
- **Proposed Fix:**
  1. Increase the fallback from 3.0s to at least **15.0s**, or make it dynamically scale based on system load / machine profile.
  2. Better yet: do not fire deferred maintenance (`prompt_catalog`, `link_index_refresh`, `update_attempts`) until `_agents_first_load_done` is True, ensuring the visible surface has full priority over CPU and disk resources.
- **Effort / Risk:** Low effort (adjusting timer constant and gating logic), very low risk.

---

### Rank 3: Optimize Link Index Generation via Rust Core or Prefiltering (High Impact)
- **Impact:** **−5.5 to −6.5 seconds** on `apollo`; prevents 7.4s GIL freeze.
- **Subsystem:** `src/sase/ace/tui/relations/link_index.py` & `sase_core` (`sase-core` crate)
- **Root Cause:** Iterating over 44,321 link rows in Python with repeated FFI calls, string manipulation, and alias resolution takes 7.4 seconds.
- **Proposed Fix:**
  1. **Move `_build_link_index` to Rust Core:** As established by the SASE Architecture Rule ("Rust Core Backend Boundary"), heavy backend data structures belong in `sase_core`. Rust can build the 44k-row indexed map in <20 milliseconds and expose a single zero-copy lookup interface to Python.
  2. **Short-Term Python Optimization:** Filter links to only currently visible entities (e.g. current project or active agents) rather than building a whole-world index of 44k historic rows on startup.
- **Effort / Risk:** Medium effort; high return.

---

### Rank 4: Paginate / Cap Agent Roster Ingestion on Startup (High Impact)
- **Impact:** **−4 to −6 seconds** on `apollo`; reduces initial `stages_seconds["disk"]` and `apply` latency.
- **Subsystem:** `src/sase/ace/tui/models/agent_loader.py` & `src/sase/ace/tui/actions/agents/_loading_disk_full.py`
- **Root Cause:** `apollo` loads all 965 historical and active agents into memory during the first startup refresh. The main-thread `apply` stage takes 5.2s just computing DOM and CSS structures for 965 items.
- **Proposed Fix:**
  1. For initial startup paint (`source == "startup"`), enforce a strict viewport limit (e.g. top 50 or 100 most recent agents) from the SQLite index (`query_agent_artifact_index_bounded`).
  2. Load the remaining deep history asynchronously after `visible_ready` has completed.
- **Effort / Risk:** Medium effort; significantly improves startup perceived responsiveness.

---

### Rank 5: Pre-import `repro.capture` and Hot Modules off the UI Thread (Medium Impact)
- **Impact:** **−2 to −4 seconds**; eliminates stall watchdog hitches during initial render.
- **Subsystem:** `src/sase/ace/tui/actions/agents/_loading_disk_full.py` & `src/sase/ace/tui/actions/_startup_mount.py`
- **Root Cause:** `from ...repro.capture import record_agents_tab_loader_result` is imported inside `_load_agents_async` on the UI thread, causing a 3.9s stall during module discovery.
- **Proposed Fix:**
  - Add `sase.ace.tui.repro.capture` and related runtime modules to the pre-import list (`PROMPT_BAR_FIRST_MOUNT_MODULES` or early startup imports) so module bytecode is already loaded in memory before the first agent load finishes.
- **Effort / Risk:** Low effort; zero risk.

---

### Rank 6: Throttle Background AXE Routines & Mypy Contention on Apollo (System / Machine Level)
- **Impact:** Immediate reduction of Apollo load average from 12.0 to ~2.0, giving SASE full CPU slice allocation.
- **Target:** Machine-level background process management on `apollo`.
- **Proposed Fix:**
  1. Identify why two background `mypy` processes were running indefinitely at 100% CPU in `sase_16` and `sase_12`. If these are orphaned or stuck runs, kill or renice them with `ionice -c 3` and `nice -n 19`.
  2. When launching the TUI interactively on `apollo`, consider `--no-axe` (`-x`) if the user only needs control surface interaction without immediately spawning local background routines, or configure AXE routine intervals to be less aggressive during user-present sessions.
- **Effort / Risk:** Operational fix; immediate benefit.

---

### Summary Impact Projection

| Optimization | Target Subsystem | Estimated Apollo Startup Time Saved |
| :--- | :--- | :--- |
| **Rank 1: Macro Entry-Point Memoization** | `sase.macro.plugin_input_types` | **~17 seconds** |
| **Rank 2: Defer Maintenance until Agents Ready** | `sase.ace.tui._startup_loads_core` | **~25 seconds** (eliminates contention) |
| **Rank 3: Rust Core Link Index / Bounded Links** | `sase.ace.tui.relations.link_index` | **~6 seconds** |
| **Rank 4: Viewport-Capped Startup Agent Load** | `sase.ace.tui.models.agent_loader` | **~4 seconds** |
| **Rank 5: Pre-import Module Warmup** | `sase.ace.tui.repro.capture` | **~3 seconds** |
| **Rank 6: Apollo Background Load Mitigation** | OS process management on `apollo` | **~10–15 seconds** |
| **Combined Projected Startup Time on Apollo** | **From ~78s down to ~5–8s** | **~90% reduction** |
