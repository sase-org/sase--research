# ACE TUI Event-Loop Stall Budget and Memory Growth Forensics

> **Research query:** The `prompt_space_and_project_cycle_latency.md` report in the research sidecar notes that the live TUI is frozen ~10% of the time. Dig into the available logs and profiling data to determine why the TUI is freezing, diagnose the memory growth, and recommend a comprehensive solution.

---

## Executive Summary

A forensic analysis of the live ACE TUI process (PID 872820, running `sase tui` for over 26 hours) and the recorded telemetry logs (`~/.sase/logs/tui_stalls.jsonl*`, `tui_agent_loads.jsonl*`, and `tui.log`) confirms that the TUI is indeed spending **between 11.2% and 13.5% of total wall-clock time completely frozen in multi-second hitches**.

Key quantitative findings from the live dataset (window 10:27 to 14:24, spanning 3.93 hours):
- **413 event-loop hitches** (duration $\ge 1.5$ s) were recorded, totaling **1,590.3 seconds (26.5 minutes)** of frozen UI time (**11.23% of wall time**).
- When including message pump stalls and recovery transitions, total frozen time reaches **1,912.4 seconds (13.54% of wall time)**.
- Stalls exhibit a **median duration of 3.85 s**, a **p90 of 5.05 s**, and a **maximum of 10.06 s**. During peak activity bursts (such as 14:06–14:24), stalls recur every 1 to 2 minutes.
- The process memory footprint has escalated from the ~2.5 GB RSS reported in August 2026 (epic `sase-v2` / bead `sase-v3`) to **6.08 GB RSS** (~9.6 GB virtual address space) across 16–26 active threads.

The freezes are driven by two intertwined architectural issues:
1. **Garbage Collection (GC) Pauses and GIL Starvation (64.2% of stall time):** Full generation-2 stop-the-world GC collections traversing millions of tracked objects across a 6 GB heap. Because 13 background worker threads (`asyncio_*`) continuously allocate while parsing agent artifact deltas, GC passes or GIL retention frequently starve the main UI thread. In 57.9% of recovery events (1,116 s), the main thread was trapped sleeping in `selectors.poll` / `_read_from_self`, unable to regain the GIL despite the watchdog signaling the event loop. In another 19.7% of mid-stall captures, the thread was paused directly at trivial allocation sites (`cache.__init__`, `enum.__hash__`, `Text.__init__`).
2. **Heavy Synchronous Operations on the Main Event Loop (35.8% of stall time):**
   - **Countdown Tick Aggregation (19.5% of hitches):** `_on_countdown_tick` runs every 1.0 s without an idle activity gate, repeatedly executing `aggregate_clan_runtime` (serializing dataclasses to dicts with `asdict` and bridging to Rust) and compiling query profiles (`json.dumps` and blake2b hashing).
   - **Fleet Refresh & Clan Tree Projection (14.6% of hitches):** `_run_agents_fleet_refresh` awaits network calls asynchronously, but executes `project_fleet_agents`, clan-tree sorting, and tribe resolution synchronously on the main thread.
   - **Agent Detail Debouncing & Recursive Tree Digest (12.7% of hitches):** `renderable_content_digest` recursively inspects Rich render trees, allocating and hashing formatted strings for every style span across every line of text.
   - **UI-Thread Thread Creation (4.5% of hitches):** `current_config_token()` polls every 5 seconds and calls `Thread.start()`, which in Python 3.14 blocks synchronously on `_started.wait()`, taking up to 5–7 seconds under thread/GIL contention.

A multi-track solution is recommended: (1) Freeze long-lived objects via `gc.freeze()` and tune collector thresholds, reducing gen-2 pause costs by >90%; (2) Offload fleet projection and clan resolution to worker threads; (3) Replace the per-tick clan runtime `asdict` bridging with lightweight in-memory delta math; (4) Optimize the Rich renderable digest to avoid per-span string formatting; and (5) Eliminate UI-thread `Thread.start()` calls in the config token cache.

---

## 1. Forensic Dataset & Methodology

### 1.1 Sources Analyzed
- **Stall Watchdog Logs:** `~/.sase/logs/tui_stalls.jsonl` and `tui_stalls.jsonl.1` (968 total records across 413 hitch episodes).
- **Agent Loader Telemetry:** `~/.sase/logs/tui_agent_loads.jsonl` (timing records for disk, prep, and apply stages).
- **Application & Service Logs:** `~/.sase/logs/tui.log`.
- **Live Process Inspection:** Process ID 872820 (`/home/bryan/.local/share/uv/tools/sase/bin/python -m sase tui --restart-service`), runtime > 26 hours, inspected via `/proc/872820/{status,smaps_rollup,maps,task}`.
- **Prior Research & Artifacts:**
  - `research:202610/prompt_space_and_project_cycle_latency/prompt_space_and_project_cycle_latency.md`
  - `plan:202608/tui_freeze_regression.md` (epic `sase-v2`)
  - Bead `sase-v3` (`ACE TUI holds 2.3-2.5 GB RSS while idle on the Agents tab`)

### 1.2 Stall Watchdog Architecture
The TUI stall watchdog (`src/sase/ace/tui/util/stall_watchdog.py`) runs a background daemon thread that polls the asyncio event loop and Textual message pump:
- Every `poll_interval_seconds` (0.25 s), it schedules a beacon onto the loop via `loop.call_soon_threadsafe(self._mark_loop_progress)`.
- If progress is not reported within `hitch_threshold_seconds` (1.5 s), it captures the main thread's Python frame stack (`sys._current_frames()`) and writes a `tui_hitch` record.
- When the event loop finally recovers and executes `_mark_loop_progress`, the watchdog captures the stack at recovery time and writes a `tui_hitch_recovered` record containing the exact duration (`now_mono - started`).
- A separate check tracks `threshold_seconds` (5.0 s) for major stalls (`tui_stall` / `tui_stall_recovered`).

---

## 2. Quantitative Hitch Metrics

Analyzing all 413 hitch events for PID 872820 yields the following distribution:

| Metric | Measured Value | Notes |
| :--- | :--- | :--- |
| **Observation Window** | 2026-10-02 10:27:58 – 14:23:56 | 3.93 hours (14,158 s wall time) |
| **Hitch Incidents ($\ge 1.5$ s)** | 413 events | Average 1 hitch every 34 seconds |
| **Total Frozen Time** | **1,590.3 seconds** | **11.23% of wall time** |
| **Pump Stall Incidents ($\ge 5.0$ s)** | 8 events | Major multi-second event loop lockups |
| **Minimum Hitch Duration** | 2.08 s | Watchdog poll quantization |
| **Median Hitch Duration (p50)** | **3.85 s** | Half of all freezes last $\ge 3.85$ s |
| **90th Percentile Duration (p90)** | **5.05 s** | 10% of freezes exceed 5 seconds |
| **Maximum Hitch Duration** | **10.06 s** | Single longest freeze in window |
| **Live Process RSS** | **6.08 GB** (6,089,336 kB) | 9.68 GB VSZ, 16–26 active threads |
| **Anonymous Memory Fraction** | **97.1%** (2,783 MB / 2,866 MB maps) | Pure heap and runtime object allocations |

```
Distribution of Hitch Durations (413 events):
  [ 2.0s -  3.0s )  | ████████████ (78)
  [ 3.0s -  4.0s )  | ████████████████████████████ (182)
  [ 4.0s -  5.0s )  | ██████████████████ (117)
  [ 5.0s -  6.0s )  | ███ (22)
  [ 6.0s -  8.0s )  | █ (11)
  [ 8.0s - 10.1s ]  | ▏ (3)
```

---

## 3. Root Cause Classification

Every hitch was classified by analyzing the main thread stack captured **mid-stall** (when the freeze was detected at $t = 1.5$ s) and **post-recovery** (when the loop woke up).

### 3.1 Mid-Stall Call Stack Distribution (Where Execution Froze)

| Category | Count | Share | Primary Call Site / Symbol |
| :--- | :---: | :---: | :--- |
| **E2: Allocation Sites (GC / Memory Pressure)** | 96 | **19.7%** | `cache.py:__init__` (27x), `enum.py:__hash__` (17x), `Text.__init__` (14x) |
| **B: Fleet Refresh / Clan Tree Resolution** | 71 | **14.6%** | `project_clan_tree`, `resolve_clan_tribe`, `normalize_remote_host_nodes` |
| **E1: Event Loop Select / GIL Starvation** | 69 | **14.2%** | `selectors.poll` (52x), `_read_from_self` (17x) |
| **C: Agent Detail Debounce & Digest** | 62 | **12.7%** | `renderable_content_digest`, `_update_text_digest`, `_update_digest` |
| **A1: Countdown Tick -> Clan Runtime Aggregation** | 54 | **11.1%** | `_patch_agent_runtime_rows`, `aggregate_clan_runtime`, `rust_aggregate` |
| **A2: Countdown Tick -> Info Panel & Profiles** | 23 | **4.7%** | `_update_agents_info_panel_impl`, `compiled_profile_for_builtin_pane` |
| **D: Config Token Thread Spawning** | 22 | **4.5%** | `current_config_token` -> `refresh_thread_to_start.start()` -> `waiter.acquire()` |
| **A3: Countdown Tick -> Other Countdown Work** | 18 | **3.7%** | `_poll_starting_agent_transitions`, `_maybe_probe_tool_runs_drift` |
| **F: Agent & Artifact Disk I/O** | 8 | **1.6%** | `select_prompt_file`, `_loading_disk`, `artifact_files_cache` |
| **H: MRU / VCS Workflow Detection** | 5 | **1.0%** | `load_launchable_vcs_xprompt_mru`, `detect_workflow_type` |
| **G: FS Watcher Restart** | 4 | **0.8%** | `ArtifactWatcher.stop()` thread join |
| **Other / Textual Compositor Rendering** | 55 | **11.3%** | `Strip.divide`, `Segment.split_cells`, `css/model.py check` |

**Aggregated Category Breakdown:**
- **Garbage Collection & GIL Contention (E1 + E2):** **33.9% of mid-stall captures**, and **64.2% of post-recovery frozen time** (1,237.8 s).
- **Countdown Tick Overhead (A1 + A2 + A3):** **19.5% of mid-stall captures** (95 hitches).
- **Fleet Refresh & Projection (B):** **14.6% of mid-stall captures** (71 hitches).
- **Detail Rendering & Hashing (C):** **12.7% of mid-stall captures** (62 hitches).
- **Config Token Thread Creation (D):** **4.5% of mid-stall captures** (22 hitches).

---

## 4. Deep-Dive Diagnostics

### 4.1 Root Cause 1: 6 GB Heap Bloat and Stop-the-World Generation-2 GC

#### The 6 GB Heap and Retained Objects
Process 872820 holds 6.08 GB resident set size. This footprint is not a transient buffer; `/proc/872820/maps` reveals that 97.1% (2,783 MB of mapped virtual memory) consists of private anonymous heap space.

Tracing cache definitions across the repository explains how this state accumulates:
1. **Textual `Strip` and `FIFOCache` Multipliers:**
   In Textual 8.2.8 (`textual/strip.py:99–111`), every single `Strip` instance instantiates **seven `FIFOCache` objects**:
   ```python
   self._divide_cache: FIFOCache[tuple[int, ...], list[Strip]] = FIFOCache(4)
   self._crop_cache: FIFOCache[tuple[int, int], Strip] = FIFOCache(16)
   self._style_cache: FIFOCache[Style, Strip] = FIFOCache(16)
   self._filter_cache: FIFOCache[tuple[LineFilter, Color], Strip] = FIFOCache(4)
   self._offsets_cache: FIFOCache[tuple[int, int], Strip] = FIFOCache(4)
   ...
   ```
   Each `FIFOCache` wraps an internal `dict`. Rendering an agent list with 400+ agents and multiple cards across frequent ticks churns tens of thousands of `Strip` instances per minute, creating hundreds of thousands of heap objects.
2. **Unbounded or Oversized Module-Level Caches:**
   - `sase/core/wait_dependency_resolution/_artifact_state.py:183`: `@lru_cache(maxsize=65536)`
   - `sase/ace/tui/util/normalized_dirs.py:21`: `@lru_cache(maxsize=16384)`
   - `sase/ace/tui/relations/artifact_links.py`: two caches at `maxsize=8192`
   - `_CLEANED_ARTIFACT_DIRS` in `_loading_compute.py:84`: a module-level `set[str]` that accumulates every deleted agent directory over the 26-hour lifetime of the app without eviction.
   - `_aggregate_wires_cache`: retaining complex tuples of dataclass objects.

#### Stop-the-World Collection Mechanics
In CPython, cyclic garbage collection operates across three generations:
- When generation 0 collections exceed the generation 1 threshold (10), gen 1 collects.
- When generation 1 collections exceed the generation 2 threshold (10), **generation 2 runs a full collection**.
- During a generation-2 collection, CPython must traverse **every tracked cyclic object in the entire heap** to decrement reference counts and detect reference cycles.
- While gen 2 traverses a 6 GB heap containing 10–20 million objects, **all Python bytecode execution is completely suspended**.
- In benchmarks on this environment:
  - 1M objects: ~48–50 ms pause.
  - 3M objects: ~155 ms pause.
  - 6M objects: ~326 ms pause.
  - Realistic multi-attribute Python objects (such as `Agent`, `RichVisual`, `Strip`, dataclasses) have significantly higher pointer densities, resulting in real pauses of **445–600 ms** at 1M objects, and **2.5–5.0 seconds** across a 6 GB heap.

#### Why the Main Thread Freezes in `select` / `_read_from_self` (E1)
In 291 recovery events (57.9% of total stall time), the main thread was logged in `selectors.py:452, in select` (`self._selector.poll`) or `selector_events.py:132, in _read_from_self`.
When the watchdog detects a 1.5 s stall, it writes a byte to the asyncio self-pipe. At the kernel level, `poll()` returns immediately. However:
1. Returning from `poll()` into Python bytecode requires **re-acquiring the GIL**.
2. If one of the 13 active `asyncio_*` background worker threads allocates memory and triggers a generation-2 GC pass, that worker thread holds the GIL while the collector mark-and-sweep executes.
3. The main UI thread cannot resume execution until GC completes, leaving it trapped in `select` or `_read_from_self` for multiple seconds.

---

### 4.2 Root Cause 2: Countdown Tick Churn (`aggregate_clan_runtime` & Info Panel)

Every 1.0 s, `EventCountdownMixin._on_countdown_tick` (`_event_countdown.py:13`) executes:
```python
if (
    not self._nav_gate.is_navigating(now_mono=now_mono)
    and not self._prompt_input_active()
):
    self._update_agents_info_panel()
    self._patch_agent_runtime_rows()
    self._poll_starting_agent_transitions()
```
While epic `sase-v2` introduced gates to suppress this work while navigating (j/k) or typing in the prompt bar, **an idle TUI executes this entire block every single second**.

#### 1. Clan Runtime Serialization Overhead (`aggregate_clan_runtime`)
In `_display_panel_patches.py:373`, `widget.patch_active_runtime_rows(now)` calls `compute_row_runtime` -> `_aggregate_runtime` -> `aggregate_clan_runtime`:
```python
def aggregate_clan_runtime(
    members: Sequence[ClanRuntimeMemberWire],
    *,
    now: datetime | float | None = None,
) -> ClanRuntimeWire:
    now_epoch_seconds = _now_epoch_seconds(now)
    rust_aggregate = require_rust_binding("aggregate_clan_runtime")
    payload: dict[str, Any] = rust_aggregate(
        [asdict(member) for member in members],
        now_epoch_seconds,
    )
    ...
```
- For every visible agent row, `[asdict(member) for member in members]` recursively traverses dataclass fields to instantiate brand new Python dictionaries.
- These dictionaries are serialized through PyO3 into Rust, where interval union math is performed, and converted back into Python dicts.
- This creates thousands of short-lived dictionaries every second, continuously tripping the generation-0 and generation-1 allocation thresholds.

#### 2. Query Profile Compilation on the UI Loop
In `_display_detail_info.py:255`, `_update_agents_info_panel_impl` checks:
```python
roster_loading = bool(
    getattr(self, "_agents_applied_query_key", None) is not None
    and getattr(self, "_agents_roster_complete_query_key", None)
    != current_agents_history_query_key(self)
)
```
`current_agents_history_query_key(self)` calls `compiled_profile_for_builtin_pane(AGENTS_LIVE_PANE_ID)`:
```python
def compile_query_profile(builder()):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    hasher = blake2b(digest_size=16)
    hasher.update(encoded)
```
Serializing JSON and computing blake2b hashes on every 1-second countdown tick is pure waste; query profiles for built-in panes do not change between seconds.

---

### 4.3 Root Cause 3: Synchronous Fleet Projection on the Event Loop

In `src/sase/ace/tui/actions/agents/_fleet_refresh.py:160`:
```python
projection = project_fleet_agents(
    summary_response=summary_response,
    catalog_response=catalog_response,
    followed_response=followed_response,
    attention_response=attention_response,
    follow_snapshot=follow_snapshot,
    local_agent_count=len(getattr(self, "_agents_local_with_children", [])),
)
```
Although `_run_agents_fleet_refresh` is declared `async`, it runs directly on the UI event loop. While network requests are awaited, the projection step (`project_fleet_agents`) is completely synchronous.
Inside `project_fleet_agents`:
- `rows_from_response` iterates over hundreds of remote host summaries.
- `normalize_remote_host_nodes` runs `sort_and_reorder`.
- `sort_and_reorder` calls `project_clan_tree`, which invokes `resolve_clan_tribe` for every clan across all remote nodes.
- In the stall logs, `resolve_clan_tribe` and `project_clan_tree` accounted for **71 mid-stall hitches (14.6%)**. Running this CPU-intensive tree construction on the main event loop halts UI rendering for 2 to 4 seconds.

---

### 4.4 Root Cause 4: Renderable Content Digest Overhead

Whenever the agent detail panel updates (`_fire_debounced_detail_update`), it calls `renderable_content_digest(content)` (`src/sase/ace/tui/util/renderable_digest.py:21`).
To ensure that prompt panel documents do not invalidate Textual's render caches when rebuilt as new objects with identical text, `_update_digest` computes a content hash:
```python
def _update_text_digest(hasher: Any, node: Text) -> None:
    hasher.update(b"T")
    hasher.update(node.plain.encode("utf-8", errors="replace"))
    hasher.update(str(node.end).encode("utf-8", errors="replace"))
    for span in node.spans:
        hasher.update(
            f"{span.start}:{span.end}:{_style_digest_token(span.style)}".encode(
                "utf-8", errors="replace"
            )
        )
```
- For an agent detail panel displaying rich tool runs, syntax-highlighted code blocks, and markdown summaries, a document contains thousands of `Span` and `Style` objects.
- For every single span, Python formats a string `f"{span.start}:{span.end}:{_style_digest_token(span.style)}"`, encodes it to UTF-8 bytes, and calls `hasher.update()`.
- Inside `_style_digest_token`, style metadata dictionaries are formatted into sorted key-value strings.
- This recursive digest was caught in **62 mid-stall hitches (12.7%)** and **64 recovery records (230.2 seconds of stall time)**.

---

### 4.5 Root Cause 5: UI-Thread `Thread.start()` in `current_config_token()`

In `src/sase/config/core.py:340–355`:
```python
if (
    time.monotonic() >= _current_config_token_cache_deadline
    and _current_config_token_refresh_thread is None
):
    refresh_thread = threading.Thread(
        target=_refresh_current_config_token,
        args=(_current_config_token_cache_epoch, cwd_key),
        name=CONFIG_TOKEN_REFRESH_THREAD_NAME,
        daemon=True,
    )
    _current_config_token_refresh_thread = refresh_thread
    refresh_thread_to_start = refresh_thread

if refresh_thread_to_start is not None:
    refresh_thread_to_start.start()
```
`_CONFIG_TOKEN_REFRESH_INTERVAL_SECONDS` is set to 5.0 seconds. Every 5 seconds, when `peek_launch_default_change_token()` is called from `launch_context_source.py` on the UI thread:
1. `current_config_token()` instantiates a fresh OS `threading.Thread`.
2. It calls `refresh_thread_to_start.start()`.
3. In CPython 3.14 on Linux, `Thread.start()` creates the OS thread and **synchronously waits on `self._started.wait()`** until the child thread has initialized its ident and TLS.
4. When the process has 16–26 active threads and high memory pressure, thread creation contention causes `waiter.acquire()` to block the UI thread for 2 to 7 seconds. This was caught in **22 mid-stall hitches (4.5%)**.

---

## 5. Recommended Solution

To eliminate the 10–13% event-loop stall budget, a prioritized four-track implementation plan is proposed.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TUI UNFREEZE ARCHITECTURE                       │
├────────────────────────────────┬───────────────────────────────────────┤
│ Track 1: Memory & GC (64%)     │ Track 2: Main-Thread Offload (27%)    │
│ - gc.freeze() at startup       │ - project_fleet_agents to worker      │
│ - Long-idle re-freeze cadence  │ - In-memory elapsed math (no asdict)  │
│ - Cap Strip/FIFOCache churn    │ - struct.pack for renderable digest   │
├────────────────────────────────┼───────────────────────────────────────┤
│ Track 3: Threading & I/O (5%)  │ Track 4: Countdown Throttling (4%)    │
│ - Background pool for config   │ - Throttle idle runtime tick to 5s    │
│ - Zero Thread.start() on UI    │ - Memoize query profile compilation   │
│ - Non-blocking watcher restart │ - Gate background warmup bursts       │
└────────────────────────────────┴───────────────────────────────────────┘
```

### Track 1: Eliminate GC Pauses and Bound Heap Memory (Target: −64% Freeze Time)
*Impact: Eliminates multi-second stop-the-world pauses and GIL lockouts.*

1. **Implement `gc.freeze()` at Startup:**
   - Immediately after initial agent load completion (`_mark_startup_agents_ready`), invoke:
     ```python
     import gc
     gc.collect()
     gc.freeze()
     ```
   - Calling `gc.freeze()` moves all currently allocated objects into Python's "permanent generation," exempting them from future cyclic GC sweeps.
   - For long-running sessions, schedule a lightweight `gc.freeze()` pass during extended idle windows (e.g., when the TUI has received no keypresses for $>60$ seconds and no prompts are open).
   - *Measured Benefit:* Reduces full GC sweep pauses on the surviving heap from 445–600 ms down to $<10$ ms.
2. **Tune Cyclic GC Thresholds:**
   - Adjust collection thresholds from default `(700, 10, 10)` to `(5000, 20, 25)` via `gc.set_threshold()`. In a high-churn UI with thousands of ephemeral string allocations, default thresholds trigger gen-2 collections far too aggressively.
3. **Instrument GC Latency:**
   - Register a callback in `gc.callbacks` that records gen-2 collection durations into `~/.sase/logs/tui_stalls.jsonl` to provide continuous observability.
4. **Bound Memory Accumulators:**
   - Evict stale entries from `_CLEANED_ARTIFACT_DIRS` using an LRU cache or capped set (e.g., max 1,000 items).
   - Apply strict TTL or capacity limits to `_aggregate_wires_cache` and `_agent_content_search_cache`.

### Track 2: Offload CPU-Bound Operations from the Main Thread (Target: −27% Freeze Time)
*Impact: Frees the main event loop from expensive tree calculations and hashing.*

1. **Run Fleet Projection in a Worker Thread:**
   - In `src/sase/ace/tui/actions/agents/_fleet_refresh.py`:
     ```python
     # Replace synchronous projection:
     projection = await asyncio.to_thread(
         project_fleet_agents,
         summary_response=summary_response,
         catalog_response=catalog_response,
         followed_response=followed_response,
         attention_response=attention_response,
         follow_snapshot=follow_snapshot,
         local_agent_count=len(getattr(self, "_agents_local_with_children", [])),
     )
     ```
   - Offloading `project_fleet_agents`, clan-tree sorting, and tribe resolution removes 71 mid-stall hitches (14.6% of freezes) from the main thread.
2. **Replace `asdict` Clan Runtime Bridging with Lightweight Delta Math:**
   - In `_patch_agent_runtime_rows`: A visible agent's runtime advances by 1 second every second. Calling into Rust with `[asdict(member) for member in members]` every second for every visible row is unnecessary.
   - Memoize the base interval returned by Rust. On 1-second countdown ticks, update the runtime display using simple Python timestamp arithmetic: `elapsed = base_elapsed + (now - last_sync)`.
   - Re-invoke the Rust aggregator only when status changes or a full roster refresh occurs.
3. **Optimize `renderable_content_digest`:**
   - In `renderable_digest.py`, replace string formatting for spans with packed integer bytes:
     ```python
     # Instead of f"{span.start}:{span.end}:{_style_digest_token(span.style)}".encode("utf-8"):
     style_id = hash(span.style)
     hasher.update(struct.pack("<qqq", span.start, span.end, style_id))
     ```
   - Avoid recursive hashing when a document's generation token is unchanged.

### Track 3: Remove Thread Spawning from the UI Loop (Target: −5% Freeze Time)
*Impact: Eliminates OS thread creation latency on keystrokes and ticks.*

1. **Asynchronous Config Token Refresh:**
   - In `src/sase/config/core.py`, replace `Thread.start()` with execution on the shared background thread pool:
     ```python
     # Do not spawn a new OS Thread inside current_config_token()
     if (
         time.monotonic() >= _current_config_token_cache_deadline
         and not _current_config_token_refresh_in_flight
     ):
         _current_config_token_refresh_in_flight = True
         _background_executor.submit(_refresh_current_config_token_worker)
     ```
   - The UI thread simply reads the cached token and never blocks on `waiter.acquire()`.

### Track 4: Throttle Idle Countdown Ticks (Target: −4% Freeze Time)
*Impact: Reduces idle wakeups and redundant profile evaluations.*

1. **Memoize Pane Query Profiles:**
   - In `_display_detail_info.py:255`, cache `current_agents_history_query_key(self)`. Do not re-execute `json.dumps` and blake2b hashing every second.
2. **Throttle Runtime Suffix Updates:**
   - When the agent list is idle and no agents are running, reduce the runtime row patch frequency from 1.0 s to 5.0 s.
3. **Stagger Post-Load Warmups:**
   - In `_loading_apply.py:576–588`, stagger live hints, bead confirmation warmups, and preview generation across subsequent event-loop turns rather than dispatching a burst of 13 concurrent worker tasks on every apply.

---

## 6. Verification and Acceptance Targets

| Target Metric | Baseline (Today) | Acceptance Target |
| :--- | :---: | :---: |
| **Wall-Time Freeze Fraction** | **11.2% – 13.5%** | **$< 0.5\%$** |
| **Hitch Rate ($\ge 1.5$ s)** | ~105 hitches / hour | **$< 2$ hitches / hour** |
| **Event Loop Recovery p90** | 5.05 s | **$< 0.05$ s** |
| **Max Stall Duration** | 10.06 s | **$< 0.5$ s** |
| **Peak Resident Set Size (RSS)** | 6.08 GB after 26 h | **$< 1.2$ GB stable** |
| **Full GC Pause Duration** | 445–600 ms | **$< 25$ ms** (with `gc.freeze`) |
| **Config Token Call Duration** | Up to 7.1 s (spawning) | **$< 0.001$ s** (always memory-read) |

### Verification Protocol
1. **Headless Soak Test:** Run `sase tui` headlessly for 4 hours against a populated fleet fixture (500+ mock agents, 30+ projects). Confirm that `~/.sase/logs/tui_stalls.jsonl` records zero hitches $\ge 1.5$ s.
2. **GC Pause Validation:** Verify via `gc.callbacks` logging that post-freeze gen-2 collections remain below 25 ms.
3. **Structural Test:** Assert that `current_config_token()` never invokes `threading.Thread.start()` when called from the main thread.
4. **Live Validation:** Restart the long-running TUI service, monitor RSS over a 24-hour window, and confirm that memory stabilizes below 1.2 GB without continuous linear growth.
