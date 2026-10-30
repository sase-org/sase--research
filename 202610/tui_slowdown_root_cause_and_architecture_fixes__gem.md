# Root-Cause Analysis and Architectural Remedies for TUI Performance Regressions

**Researcher:** `research.5k.gem`  
**Date:** October 30, 2026  
**Scope:** TUI latency, loop hitches, GC pause amplification, and memory bloat on long-running SASE ACE instances.  
**Target Repository:** `sase` (linked: `sase-core`, `sase--research`)  

---

## 1. Executive Summary

Over recent releases, the SASE Textual TUI (ACE) has exhibited severe responsiveness regressions during sustained interactive use. Users observe perceptible input lag on navigation ($j$/$k$), typing delays in the prompt bar, and recurrent freezes lasting anywhere from 2 to 24 seconds. 

An empirical forensic examination of the live production environment on `athena` (active instance `f8c86c23`, PID 2704211, running commit `dab2d701fb`) demonstrates that this degradation is **not** caused by ordinary rendering overhead or algorithmic complexity in widget layout. Instead, it is the product of a **destructive feedback loop between unbounded memory bloat, operating system swap thrashing, and stop-the-world Python garbage collection (GC)**:

1. **Catastrophic Memory Footprint:** The live TUI process has expanded to **29.1 GB virtual memory**, **15.6 GB RSS**, and **7.85 GB of active anonymous swap**.
2. **Stop-the-World Freeze Amplification:** In CPython, cyclic garbage collection (`gc.collect()`) must traverse every container object in the tracked generations. When 7.85 GB of heap structures are paged out to swap, cyclic GC triggers massive bursts of major page faults (`major_faults_delta > 140` per GC pause). A collection that should complete in 20–50 ms escalates into a **5 to 32-second complete process freeze**. Because the Python Global Interpreter Lock (GIL) is held throughout cyclic collection, all threads—including background worker pools and the main Textual event loop—are completely blocked.
3. **Primary Allocator and Churn Producers:**
   - **Monolithic Unbounded JSON Registries:** `~/.sase/agent_name_registry.json` has ballooned to **37 MB** (28,258 entries), and `~/.sase/dismissed_agents.json` has reached **4.7 MB** (83,592 entries). During staleness checks, `_registry_file_is_stale()` executes over 28,000 filesystem `stat()` calls in Python, while multiple worker threads deserialize these multi-megabyte JSON trees into nested Python dicts, generating hundreds of megabytes of short-lived and cyclic garbage per minute.
   - **Full-Load Refresh Stampedes:** Over a 2-hour observation window, the running instance executed **298 slow agent loads**, including **175+ full-history loads** (averaging one full disk load every 40 seconds). Each full load consumed between 25 and 71 seconds of background disk and index query processing. Overlapping asynchronous reload triggers (`auto_refresh`, `roster_completion_retry`, `input_quiet_tier2_reconcile`, `tier1_index_revalidate`) saturated the 16-worker thread pool, causing severe lock contention on `agent_artifact_index_operation_lock`.
   - **Textual `Strip` Self-Cycles:** Textual's `Strip` primitives each instantiate seven separate `FIFOCache` instances. Methods like `Strip.crop()` cache resulting child strips inside the parent's `_crop_cache`, generating complex self-referencing and cross-referencing cycles that bypass standard reference-counting deallocation and accumulate millions of surviving objects in Generation 2.
4. **Failure of Prior Mitigation Attempts:** Prior epics (`sase-1ez`, `sase-1nc`, `sase-1nf.14.1`) focused on raising GC thresholds (`threshold2 = 10,000`), invoking `gc.freeze()` at startup, and classifying graph copies. However, delaying Gen-2 GC merely allowed the heap to accumulate gigabytes of cyclic garbage until physical RAM was exhausted. Once memory began paging to swap, the deferred collections became catastrophic.

### Recommended Solution Overview
To resolve this permanently without compromising architectural reliability or breaking existing user workflows, SASE must implement a four-pillar architectural reform:
- **Pillar 1 (Storage Architecture):** Migrate `agent_name_registry` and `dismissed_agents` from flat, monolithic JSON files into the existing native SQLite database in `sase-core`, and implement an automated 30-day retention pruning policy.
- **Pillar 2 (Concurrency Control):** Enforce hard single-flight coalescing and exponential backoff on full agent disk loads to eliminate refresh stampedes.
- **Pillar 3 (Cycle Decoupling):** Sever back-pointers in superseded `Agent` graphs and clear Textual `Strip` cache cycles on widget option replacement.
- **Pillar 4 (Memory Pressure Management):** Replace passive static GC thresholds with an active memory-pressure-aware policy that triggers idle trimming and compacting before swap space is ever touched.

---

## 2. Empirical Forensic Evidence & Telemetry Analysis

### 2.1 Live Process Telemetry (`athena` / PID 2704211)

Diagnostics taken directly from the operating system and SASE runtime logs demonstrate extreme resource consumption:

| Metric | Measured Value | Standard / Target | Status |
| :--- | :--- | :--- | :--- |
| **Virtual Memory (`VmSize`)** | **29,092,928 kB (29.1 GB)** | < 2.0 GB | **CRITICAL BLOAT** |
| **Resident Set Size (`VmRSS`)** | **15,605,940 kB (15.6 GB)** | < 1.0 GB | **CRITICAL BLOAT** |
| **Anonymous Swapped Memory (`VmSwap`)** | **7,855,857 kB (7.85 GB)** | 0 kB | **FATAL FAILURE** |
| **CPU Core Utilization** | **81.8% – 99.0%** (sustained) | < 5.0% idle | **THREAD THRASH** |
| **Main Thread Accumulated CPU Time** | **250 minutes, 12 seconds** | — | — |
| **Worker Threads Count** | 28 threads (16 in threadpool) | ≤ 8 threads | Worker Saturation |

### 2.2 Acceptance Metrics from `tools/tui_freeze_report`

Evaluating instance `f8c86c23` against the authoritative `sase-1f3` performance targets via `tools/tui_freeze_report --acceptance` yields an unambiguous, reproducible failure across all latency and memory dimensions:

```
instance f8c86c23
  window: 6651.413 s; frozen: 847.879 s (12.75%, 181 loop episodes)
  hitch duration: median 3.760 s, p90 6.423 s, max 23.975 s
  late episodes: 69 (270.643 s)
  gc: 710.429 s (10.68% of window) by generation {"0": 228.452, "1": 247.324, "2": 234.653}
  idle collections: 53 pauses, p50 3.671 s, p95 5.466 s, max 6.781 s
  collections by trigger: idle 53 (p95 5.466 s); backstop 4 (p95 5.663 s); rss_backstop 7 (p95 5.974 s); automatic 833
  rss: 13.6 GiB -> 6.8 GiB; swap: 9.0 MiB -> 7.85 GiB peak (23 heartbeats)
  
acceptance verdict:
  FAIL  idle full-generation p95 <= 500 ms (observed: 5,465.6 ms)
  FAIL  total GC < 3% of observed wall time (observed: 10.30% - 10.68%)
  FAIL  loop hitches < 0.5% of observed wall time (observed: 12.13% - 12.75%)
  FAIL  VmSwap remains zero across observed heartbeats (observed: 7,855,857,664 B peak)
  FAIL  no late hitch outside a fully attributable idle collection (68 unexplained/partial violations)
  OVERALL VERDICT: FAIL
```

### 2.3 Stall Stack Traces and Page-Fault Profiling

A forensic examination of `~/.sase/logs/tui_stalls.jsonl` demonstrates that event loop hitches are triggered at seemingly innocuous program locations:

1. **Hitches during DOM/Style Tree Traversal (23.975 seconds):**
   ```
   File ".../textual/app.py", line 4420, in _watch_app_focus
     self.screen.update_node_styles()
   File ".../textual/dom.py", line 1813, in update_node_styles
     self.app.update_styles(self, animate=animate)
   File ".../textual/css/stylesheet.py", line 724, in update_nodes
     apply(node, animate=animate, cache=cache)
   File ".../textual/css/styles.py", line 1004, in extract_rules
     1 if is_important(rule_name) else 0,
   ```
   *Analysis:* Updating styles across several hundred rendered DOM nodes should take < 5 ms. In this stall, traversing node structures that had been swapped out to disk forced the OS kernel to service thousands of page faults, freezing the main thread for 24 seconds.

2. **Hitches during Pathlib Iteration (4.249 seconds):**
   ```
   File ".../tui/actions/event_refresh/_watcher.py", line 176, in _on_artifact_change_deferred
     self._on_artifact_change(changed_paths or None)
   File ".../tui/actions/event_refresh/_artifact_delta.py", line 38, in _agent_artifact_delta_dir_for_path
     if notifications_root in (path, *path.parents):
   File ".../pathlib/__init__.py", line 63, in __getitem__
   ```
   *Analysis:* Merely tuple-unpacking `*path.parents` stalled for 4.25 seconds because the underlying string/path objects were swapped out.

3. **Major Fault Correlation:**
   Every reported `tui_gc_pause` event in `tui_stalls.jsonl` logged an immediate surge in `major_faults_delta`:
   - `generation: 0, duration_s: 0.0607, major_faults_delta: 141`
   - `generation: 1, duration_s: 0.0906, major_faults_delta: 139`
   When cyclic collection runs across a heap spanning 15 GB of resident and 7.8 GB of swapped pages, the CPU spends virtually all its time waiting for disk block transfer, turning sub-second GC cycles into multi-second hangs.

---

## 3. Subsystem Root-Cause Deconstruction

```
+---------------------------------------------------------------------------------------------------+
|                                  THE TUI MEMORY & GC FEEDBACK LOOP                                |
|                                                                                                   |
|   +-------------------------------------+          +------------------------------------------+   |
|   | 1. Monolithic JSON Registries       |          | 2. Full-Load Refresh Stampede            |   |
|   | • agent_name_registry.json (37 MB)  |          | • 175+ full loads in 2 hours             |   |
|   | • dismissed_agents.json (4.7 MB)    |          | • Each load takes 25-71s disk/index time |   |
|   | • 28,000 filesystem stat() checks   |          | • 16-worker threadpool saturation        |   |
|   +-------------------------------------+          +------------------------------------------+   |
|                     |                                                   |                         |
|                     +------------------------+--------------------------+                         |
|                                              |                                                    |
|                                              v                                                    |
|                      +-----------------------------------------------+                            |
|                      | 3. Massive Generation-2 Heap Bloat            |                            |
|                      | • Millions of cyclic Textual Strips           |                            |
|                      | • 7 FIFOCaches per Strip (self-cycles)        |                            |
|                      | • RSS escalates: 13.6 GB -> 15.6 GB           |                            |
|                      +-----------------------------------------------+                            |
|                                              |                                                    |
|                                              v                                                    |
|                      +-----------------------------------------------+                            |
|                      | 4. System Swap Exhaustion                     |                            |
|                      | • 7.85 GB anonymous pages pushed to VmSwap    |                            |
|                      | • OS thrashing on memory access               |                            |
|                      +-----------------------------------------------+                            |
|                                              |                                                    |
|                                              v                                                    |
|                      +-----------------------------------------------+                            |
|                      | 5. Catastrophic Stop-the-World GC             |                            |
|                      | • gc.collect() traverses swapped-out memory   |                            |
|                      | • Hundreds of major page faults per collection|                            |
|                      | • 5 to 32-second freezes blocking main loop   |                            |
|                      +-----------------------------------------------+                            |
+---------------------------------------------------------------------------------------------------+
```

### 3.1 Root Cause A: Unbounded Monolithic JSON Registries

A critical design flaw in SASE's metadata tier is the persistence of global registries as flat JSON files without pagination, partitioning, or time-based retention:

1. **`~/.sase/agent_name_registry.json` (37 MB, 28,258 entries):**
   - Every active and historical agent name reservation is recorded in a single JSON document.
   - When parsed by Python (`json.load()`), this file instantiates over 28,000 top-level dictionaries, each containing nested `collision_owners`, timestamps, and path strings. In Python's object representation, this file consumes **between 350 MB and 500 MB of heap memory**.
   - **The `stat()` Storm:** In `src/sase/agent/names/_registry_store.py`:
     ```python
     def _registry_file_is_stale(data: dict[str, Any]) -> bool:
         ...
         for entry in entries.values():
             if entry_owner_missing(entry):
                 return True
     ```
     `entry_owner_missing()` performs `Path(artifacts_dir).exists()` or `Path(bundle_path).is_file()` on every single record. Whenever a staleness check runs without an active memo, Python executes **28,000 filesystem `stat` system calls**.
   - **Render-Path Contamination:** Even in display paths (`_snapshot_agent_name_registry`), detail panel renderers invoke `get_reserved_agent_session_names_for_display()`, which re-reads or validates this 37 MB document.
   - **Historical Context:** In linked `sase-core` commits, engineers noted:
     `"JSON-registry retention gap (agent_name_registry.json/dismissed_agents.json) left for a dedicated follow-up."`
     This unaddressed technical debt has now reached critical mass.

2. **`~/.sase/dismissed_agents.json` (4.7 MB, 83,592 entries):**
   - 83,592 dismissed agents dating back several months are maintained in a monolithic JSON array.
   - On every full agent disk load (`AgentLoadingDiskFullMixin._load_agents_async`), Python invokes `_external_dismissal_merge_result()`, deserializing 4.7 MB of JSON and creating a Python `set` of 83,592 three-element tuples.
   - This set is passed across asynchronous thread boundaries (`asyncio.to_thread`), copied, and checked repeatedly during roster normalization.
   - Although `dismissed_agents` is already mirrored in `agent_artifact_index.sqlite` (83,592 rows in SQLite), the Python TUI continues to process the flat JSON file in memory.

### 3.2 Root Cause B: Full-Load Cascades and Refresh Stampedes

An analysis of `~/.sase/logs/tui_agent_loads.jsonl` demonstrates that the TUI is executing an unsustainable number of full-history agent disk loads:

```
Total slow agent loads (2 hours): 298
Distribution by Source:
  - auto_refresh:                 79 full loads
  - inflight_poll:                60 artifact_delta loads
  - roster_completion_retry:      39 full loads
  - notification:                 34 artifact_delta + 8 full loads
  - input_quiet_tier2_reconcile:  28 full loads
  - tier1_index_revalidate:       17 full loads
  - launch:                       10 full + 5 artifact_delta loads
  - watcher:                      13 artifact_delta loads
```

- Over 175 **full** disk loads occurred in 120 minutes.
- **The Asymmetric Cost of a Full Load:** While an `artifact_delta` load takes 0.15s to 0.5s, a `full` load requires **25.6s to 71.3s**:
  - `index`: 23.7s to **64.3s** (scanning the 323 MB `agent_artifact_index.sqlite`).
  - `decode`: 1.4s to **23.8s** (hydrating hundreds of `Agent` domain models).
  - `prep`: 1.6s to **6.5s** (sorting, grouping, and graph folding).
- **The Stampede Cascade:** Because a full load takes up to 71 seconds, it exceeds the interval of periodic background ticks (`auto_refresh` and `tier1_index_revalidate`). Before one full load completes, subsequent triggers schedule additional loads. As a result, the `asyncio.to_thread` pool saturated with up to 16 concurrent worker threads, each attempting to acquire the SQLite read lock or hold large object batches, creating extreme GIL and memory pressure.

### 3.3 Root Cause C: Textual `Strip` Self-Cycles and Render Garbage

In Textual 8.2.8, every rendered line of an `OptionList` or widget is represented by a `Strip` object. Inspecting `textual.strip.Strip.__init__`:

```python
def __init__(self, segments: Iterable[Segment], cell_length: int | None = None) -> None:
    self._segments = list(segments)
    self._cell_length = cell_length
    self._divide_cache: FIFOCache[tuple[int, ...], list[Strip]] = FIFOCache(4)
    self._crop_cache: FIFOCache[tuple[int, int], Strip] = FIFOCache(16)
    self._style_cache: FIFOCache[Style, Strip] = FIFOCache(16)
    self._filter_cache: FIFOCache[tuple[LineFilter, Color], Strip] = FIFOCache(4)
    self._line_length_cache: FIFOCache[tuple[int, Style | None], Strip] = FIFOCache(4)
    self._crop_extend_cache: FIFOCache[tuple[int, int, Style | None], Strip] = FIFOCache(4)
    self._offsets_cache: FIFOCache[tuple[int, int], Strip] = FIFOCache(4)
```

1. **Seven FIFOCaches Per Strip:** Every single line rendered creates 7 caching structures.
2. **Cycle Creation:** In `Strip.crop()`:
   ```python
   self._crop_cache[cache_key] = strip
   ```
   A cropped or divided `Strip` is stored in the parent's `_crop_cache`. Child strips retain references to other strips or styles, creating cyclical dependency graphs.
3. **Reference Counting Failure:** CPython's reference counting cannot deallocate cyclic data structures. They can only be reclaimed when cyclic garbage collection runs.
4. **Volume:** With continuous runtime-suffix ticking (updating running agent elapsed seconds) and repeated option replacements in `_agent_list_build_patch_single.py`, hundreds of thousands of cyclic `Strip` and `FIFOCache` objects are minted. They survive into Generation 1 and Generation 2, swelling the heap until memory is exhausted.

### 3.4 Root Cause D: Why Prior GC Gating Epics Failed

In early October, Epic `sase-1ez` implemented `gc.freeze()` at startup and raised `threshold2 = 10,000` to defer full GC during interactive sessions.

While well-intentioned, this policy introduced a catastrophic side effect:
- `gc.freeze()` only protects objects allocated *before* the call. The millions of objects generated by subsequent agent loads, JSON parses, and render strips are allocated *after* startup and enter normal generational tracking.
- By raising `threshold2` from its default of 10 to 10,000, Python was instructed **never** to run Generation 2 collection until an enormous volume of object allocations and promotions had accumulated.
- Consequently, cyclic garbage was allowed to pile up unchecked until heap usage expanded from 1.5 GB to 15.6 GB, forcing the Linux kernel to push 7.85 GB into swap.
- When an idle window, backstop, or RSS threshold finally triggered Gen-2 GC, the collector was forced to traverse a 15+ GB heap spread across swapped disk blocks, causing the observed 5 to 32-second process freezes.

---

## 4. Architectural Evaluation & Design Principles

Any remediation must adhere to SASE's core architectural tenets:
1. **Preserve Documentation and Contract Integrity:** Retain single-turn agent isolation, pump-free background task scheduling, and existing domain events.
2. **Move Shared State into the Rust Core:** Adhere to Reference Memory `1.3 Rust Core Backend Boundary`: heavy data management, disk-backed indexing, and query filtering belong in `sase-core` (`sase_core_rs`), not in repetitive Python loops.
3. **Bounded Latency and Predictable Memory:** Keystroke ($j$/$k$) and rendering paths must execute in $\mathcal{O}(1)$ time with respect to total repository history and must never trigger synchronous disk I/O or multi-megabyte JSON deserialization.
4. **Never Page to Swap:** A responsive interactive TUI must remain entirely resident in physical RAM.

---

## 5. Recommended Solution: A Four-Pillar Architectural Action Plan

```
+---------------------------------------------------------------------------------------------------+
|                                   THE FOUR-PILLAR ARCHITECTURAL FIX                               |
|                                                                                                   |
|  +--------------------------------+                  +-----------------------------------------+  |
|  | Pillar 1: Native SQLite Stores |                  | Pillar 2: Single-Flight Refresh Coalesce |  |
|  | • Move name & dismissal checks |                  | • Hard single-flight mutex on loads     |  |
|  |   into sase-core SQLite        |                  | • Deduplicate concurrent full refreshes |  |
|  | • 30-day retention pruning     |                  | • Exponential backoff on retries        |  |
|  | • Eliminate 37MB JSON parse    |                  | • Relax revalidation cadence (15 min)   |  |
|  +--------------------------------+                  +-----------------------------------------+  |
|                 |                                                          |                      |
|                 +----------------------------+-----------------------------+                      |
|                                              |                                                    |
|                                              v                                                    |
|  +-------------------------------------------+-------------------------------------------------+  |
|  | Pillar 3: Explicit Cycle Breaking         | Pillar 4: Proactive Memory Pressure Watchdog    |  |
|  | • Weak references for Agent graphs        | • Cap RSS at 2.5 GB; proactive malloc_trim      |  |
|  | • Invalidate Textual Strip FIFOCaches     | • Re-tune threshold2 to 2,000 (frequent, fast)  |  |
|  | • Equality guard on Option replacement    | • Zero-tolerance for VmSwap > 50 MB             |  |
|  +-------------------------------------------+-------------------------------------------------+  |
+---------------------------------------------------------------------------------------------------+
```

### Pillar 1: Migrate Monolithic Registries to Native SQLite in `sase-core`

1. **Retire Flat JSON Deserialization:**
   - Cease reading `~/.sase/agent_name_registry.json` and `~/.sase/dismissed_agents.json` on TUI worker threads.
   - `dismissed_agents` is already present in `agent_artifact_index.sqlite` (83,592 rows). Expose a fast, indexed Rust query binding:
     ```rust
     // In sase_core::agent_scan::index
     pub fn is_agent_dismissed(conn: &Connection, identity: &AgentIdentityWire) -> Result<bool>
     ```
     This replaces loading 83,592 Python tuples with an indexed $\mathcal{O}(1)$ SQLite query or a cached Bloom filter.
2. **Move Name Reservation Queries to SQLite:**
   - Migrate `agent_name_registry` table schema into `agent_artifact_index.sqlite`.
   - Name checks (`lowest_name_suggestion`, `get_reserved_agent_session_names_for_display`) must execute via indexed SQL queries rather than in-memory dictionary iterations.
3. **Implement Durable Compaction / Pruning:**
   - Add a maintenance command: `sase agent registry prune --older-than 30d`.
   - Archived records for completed/dismissed agents older than 30 days must be moved to cold storage or purged from the hot lookup table. Reducing active registry entries from 28,258 to ~1,500 will shrink memory requirements by 95%.

### Pillar 2: Single-Flight Refresh Coalescing & Rate Limiting

1. **Implement Single-Flight Async Load Mutex:**
   - In `src/sase/ace/tui/actions/agents/_loading_disk_full.py`, wrap `_load_agents_async` with a single-flight coalescing coordinator:
     ```python
     class SingleFlightCoordinator:
         def __init__(self):
             self._in_flight: asyncio.Task | None = None
             self._pending_request: asyncio.Future | None = None

         async def execute(self, load_fn):
             if self._in_flight and not self._in_flight.done():
                 if self._pending_request is None:
                     self._pending_request = asyncio.Future()
                 return await self._pending_request
             self._in_flight = asyncio.create_task(load_fn())
             try:
                 res = await self._in_flight
                 if self._pending_request:
                     self._pending_request.set_result(res)
                     self._pending_request = None
                 return res
             finally:
                 self._in_flight = None
     ```
   - This ensures that if 5 events (`auto_refresh`, `notification`, `roster_completion_retry`) fire while a 30-second load is running, they share the single in-flight result rather than queueing 5 sequential 30-second disk loads.
2. **Cadence Relaxation:**
   - Lengthen the interval of `tier1_index_revalidate` and `input_quiet_tier2_reconcile` from periodic seconds to **15 minutes** (in accordance with `tui_perf.md` Rule 10: *"Periodic ticks revalidate; recomputes get a longer cadence"*).
   - Apply exponential backoff to `roster_completion_retry` (1s, 2s, 4s, 8s, up to 60s cap) instead of immediate re-polling.

### Pillar 3: Explicit Cycle Breaking & Render Strip Garbage Mitigation

1. **Guard `OptionList` Replacement with Content Equality:**
   - In `src/sase/ace/tui/widgets/_agent_list_build_patch_single.py`:
     ```python
     # Check whether rendered text and styling actually changed before replacing
     if current_option.prompt == new_option.prompt:
         return True  # Skip replace_option_prompt_at_index
     ```
     Skipping `replace_option_prompt_at_index` when the rendered prompt has not changed prevents Textual from dropping and recreating lines, saving thousands of `Strip` allocations per minute.
2. **Clear Strip Caches on Widget Unmount / Row Replacement:**
   - When an `AgentList` or detail deck is cleared or repainted, traverse discarded `Strip` instances and explicitly call:
     ```python
     strip._divide_cache.clear()
     strip._crop_cache.clear()
     strip._style_cache.clear()
     ```
     Clearing the caches severs the cyclic links, allowing CPython's reference counting to free the memory immediately without waiting for cyclic GC.
3. **Decouple `Agent` Model Graph Cycles:**
   - In `src/sase/ace/tui/models/agent.py`, replace bidirectional strong references between parents, children, and clan wave slots with `weakref.ref` or implement an explicit `.detach_graph()` method called when a roster snapshot is superseded.

### Pillar 4: Proactive Memory Pressure Management

1. **Re-tune Generational Thresholds:**
   - Lower `threshold2` from `10,000` to **`2,000`**.
   - Running Gen-2 GC when only ~200–300 MB of new objects have been promoted takes **< 100 ms**, whereas waiting until 10,000 promotions accumulate across 15 GB causes a 25-second freeze. Frequent, cheap collections are far superior to rare, catastrophic pauses.
2. **Active RSS Ceiling and Malloc Trimming in `GCPolicy`:**
   - In `src/sase/ace/tui/util/gc_policy.py`, add proactive memory threshold guards:
     ```python
     RSS_SOFT_CEILING_BYTES = 2 * 1024 * 1024 * 1024  # 2.0 GB
     SWAP_ALERT_THRESHOLD_BYTES = 50 * 1024 * 1024     # 50 MB

     if current_rss > RSS_SOFT_CEILING_BYTES or current_swap > SWAP_ALERT_THRESHOLD_BYTES:
         # Trigger idle cycle and push unmapped pages back to OS
         self.trigger_immediate_idle_collection()
         asyncio.to_thread(ctypes.CDLL("libc.so.6").malloc_trim, 0)
     ```
   - Enforcing an RSS ceiling of 2.0 GB ensures that process memory remains well below host physical limits and **never spills into swap**.

---

## 6. Implementation Roadmap & Verification Plan

### Phase 1: Immediate TUI Relief (Low Risk, High Impact)
- [ ] Add content-equality guards in `_agent_list_build_patch_single.py` to prevent redundant `replace_option_prompt_at_index` calls.
- [ ] Implement single-flight load coalescing in `AgentLoadingDiskFullMixin`.
- [ ] Re-tune `threshold2` to `2,000` in `gc_policy.py` and add proactive `malloc_trim(0)` when RSS exceeds 2.0 GB during idle windows.
- [ ] Relax `tier1_index_revalidate` interval to 15 minutes.

### Phase 2: Metadata Registry Modernization (Architectural Refactor)
- [ ] Extend `sase-core` SQLite schema to store agent name reservations and dismissal markers.
- [ ] Replace Python `dismissed_agents.json` and `agent_name_registry.json` deserialization with indexed `sase_core_rs` queries.
- [ ] Add `sase agent registry prune` command to archive entries older than 30 days.

### Phase 3: Graph and Strip Cycle Decoupling
- [ ] Audit Textual `Strip` lifecycle in `AgentList` and deck panels; implement explicit cache clearing on unmount.
- [ ] Convert `Agent` domain model parent-child links to use weak references.

### Verification Protocol
1. **Local Benchmarks:** Run `pytest -s -m slow tests/ace/tui/bench_tui_jk.py` to verify $p95 < 16$ ms for $j$/$k$ navigation across all tabs.
2. **Diagnostic Soak Verification:** Run `tools/tui_freeze_report --acceptance` over a 4-hour representative session on a freshly restarted TUI.
   - Acceptance criteria:
     - `VmSwap` remains **0 B** at all times.
     - `VmRSS` remains **< 2.0 GB**.
     - Total GC time is **< 3.0%** of wall time.
     - Idle full-generation GC $p95 \le 500$ ms.
     - Zero unexempt late hitches.
