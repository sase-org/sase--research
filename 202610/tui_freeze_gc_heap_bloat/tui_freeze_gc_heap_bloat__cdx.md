# TUI freeze budget: memory pressure and synchronous refresh forensics

Independent research by **cdx**, 2026-10-02. Scope: explain the approximately 10% freeze estimate in `prompt_space_and_project_cycle_latency.md`, use the available logs and profiles to identify useful fixes, and recommend a solution. This investigation used the shared input report, raw diagnostics, local source, and unrelated historical performance captures. No report or transcript from another researcher in this swarm was consulted.

## Findings

**The 10% estimate is reproducible, and the problem extends well beyond the prompt keys.** In an explicitly bounded recreation of the original window, 314 completed event-loop hitch episodes total 1,110.69 seconds over 11,160.73 seconds: **9.95%**. A later snapshot through 14:23:56 EDT contains 413 completed episodes totaling 1,590.26 seconds: **11.23%** by the original sum-of-durations method. Unioning inferred intervals reduces that slightly to **11.22%**.

That is an estimate of time inside recorded watchdog episodes, not an exact measurement of every instant during which the screen could not respond. Nevertheless, hundreds of multi-second episodes are real evidence of a serious responsiveness failure.

The most useful new findings are:

- The affected process had **5.67 GiB RSS plus 2.53 GiB swapped out**. Paging and memory retention must be considered alongside GC and GIL contention.
- **OS process uptime overstates the age of the current TUI instance.** SASE restarts using `os.execv`, preserving PID and process start time. There were 13 startup records for PID 872820. The instance that produced the approximately four-hour hitch window last started around **10:15 EDT**, not 26 hours earlier.
- There are concrete synchronous paths remaining on the event loop: runtime aggregation every second; fleet response normalization and reprojection; full detail-document hashing; and **22 hitch samples in `current_config_token()` waiting for a newly started thread**.
- A small controlled benchmark measured the complete Python-to-Rust runtime adapter at **10.17 ms median for 1,000 members**, not seconds. The multi-second samples at that binding do not establish that the Rust algorithm itself is the primary problem.
- Historical heap data already shows substantial retained JSON/link/index objects **after a cache-cap fix**. Count-bounded caches can still retain many large historical snapshots.
- GC is a credible amplifier, but existing data does not measure GC intervals. **Blindly adding `gc.freeze()` is not a defensible first production fix**, especially when memory retention and swap are already severe.

## Evidence and method

### Inputs

The shared report was consumed through the audited reference:

`research:202610/prompt_space_and_project_cycle_latency/prompt_space_and_project_cycle_latency.md`

Primary local evidence:

| Input | Purpose |
| --- | --- |
| `~/.sase/logs/tui_stalls.jsonl{,.1}` | Hitch/stall starts, recoveries, main-thread stacks, worker/task stacks on pump stalls |
| `~/.sase/logs/tui_startup.jsonl` | Distinguish TUI restarts from OS process uptime |
| `~/.sase/logs/tui_agent_loads.jsonl` | Real loaded-row counts and disk/prep/apply stage durations |
| `/proc/872820/{status,statm,environ}`, `ps`, CPU/memory pressure | Live resource state and probe availability |
| `~/.sase/perf/sase-zn.9.5-sustained-20260913T115503-tui_heap.jsonl` | Historical allocation growth and retained sites |
| `~/.sase/perf/sase-zn.9.5-sustained-20260913T115503.jsonl` | Historical RSS/swap, revision, workload, and capture metadata |
| `~/.sase/perf/athena-verify-sase-zn8-20260912T131736.raw` | Historical stack attribution, with known sampling limitations |
| `~/.sase/perf/sase-zn.9.5-sustained-20260913T115503-pyspy-start.raw` | Historical startup profile; not an October steady-state profile |

The current default `tui_trace.jsonl` was **stale for this investigation**: its last timestamp is 2026-10-01, and the live process had no `SASE_TUI_TRACE`, `SASE_TUI_PERF`, or `SASE_TUI_HEAP` environment variable set. The current `tui_jk.jsonl` lacks wall-clock/PID attribution, so it cannot establish October 2 key latency. I did not treat either file as a contemporaneous before/after measure.

Source inspected at:

- sase: `34079430e3bf2fd34bd3451631cbdbcd370514d2`.
- sase-core: `be86aa9fff063dd17b3c58849a2bb708fe00cd2c`, opened through `sase repo open`.
- Controlled adapter benchmark: CPython **3.14.7**, `sase-core-rs` **0.36.3**, GC thresholds `(2000, 10, 10)`.

These revisions identify inspected source, not the exact imported revision of the previously running TUI. An editable checkout advancing does not update already imported modules.

### Snapshot provenance

I read both retained stall segments into a private analysis snapshot before the subsequent live restart. All 972 parsed rows belonged to PID 872820. They covered **2026-10-02 10:27:57.519–14:23:56.501 EDT**, a 14,158.982-second window, with no unmatched start/recovery records.

| Segment | Bytes at read | SHA-256 |
| --- | --- | --- |
| `tui_stalls.jsonl.1` | 2,093,224 | `22acfa90a1b910dd3da7ed9724c56916c2a331cb1d8396143cdbe862db843774` |
| `tui_stalls.jsonl` | 1,587,944 | `c075a018ed7b4b18097567f0746d4cfacee5c6ff2ebc5ad0d9e6c46985d9acb8` |

These hashes describe that snapshot; live files keep appending and rotating. The measurements below preserve the useful aggregate evidence even after rotation.

I paired each event with its matching recovery, separately by PID and event type. I used `duration_seconds`, not `stall_seconds`, for episode duration. For union calculations I inferred each interval as `[recovery.ts - duration_seconds, recovery.ts]`, sorted intervals, and merged overlaps. Because recovery timestamps and monotonic duration capture are not perfectly simultaneous, this is an approximate union.

## What “10% frozen” actually means

| Window / measure | Episodes | Total seconds | Window share | Median / p90 / maximum duration |
| --- | ---: | ---: | ---: | --- |
| Recreation ending before 13:34:00 EDT, loop hitch duration sum | 314 | 1,110.690 | **9.95%** | 3.590 / 4.458 / 8.509 s |
| Full snapshot through 14:23:56, loop hitch duration sum | 413 | 1,590.255 | **11.23%** | 3.854 / 5.051 / 10.065 s |
| Full snapshot, union of loop hitch intervals | 413 | 1,587.999 | **11.22%** | Same episodes |
| Full snapshot, pump hitch duration sum | 61 | 247.814 | 1.75% | 4.005 / 5.091 / 8.513 s |
| Full snapshot, union of loop and pump hitch intervals | — | 1,613.989 | **11.40%** | Includes only about 25.99 s beyond the loop union |

The original report's 317 hitches versus this recreation's 314 reflect different cutoffs/snapshots. Its central approximately 10% claim is reproduced within rounding.

Important interpretation limits:

1. **Loop/pump and hitch/stall tiers overlap.** The 61 pump episodes and eight loop stall episodes are not independent additional freezes. Adding their totals would exaggerate the budget. The combined union is only slightly higher than the loop-only union.
2. **The watchdog counts beacon gaps plus recovery detection delay.** `_record_hitch()` anchors the episode at `now_mono - stall_seconds`; recovery is stamped on a subsequent watchdog poll. With the observed 0.5-second poll interval, durations include detection quantization and do not exactly equal a blocked callback's execution time.
3. **Rate limiting omits episodes.** The snapshot's loop hitch records report **35 suppressed episodes**; pump hitch records report zero. Their durations are unavailable. This undercounts some time while recovery polling can overcount some time. Consequently, neither the summed figure nor the union is a rigorous lower or upper bound on true input unavailability.
4. **Sub-1.5-second interruptions are invisible here.** This does not measure all key latency, nor the application's lifetime average.
5. **Last action is context, not causality.** An old `j`, `space`, or `ctrl+p` does not prove the action caused the freeze. The stack and phase timing are stronger evidence.
6. A “random keypress has a 1-in-10 chance” statement assumes keypress timing is independent of workload. Real users type and navigate in bursts, and may wait during stalls. Record actual input-to-paint latency instead of treating that probability as measured.

Implementation references: `src/sase/ace/tui/util/_stall_watchdog_monitor.py`, `_stall_watchdog_records.py`, `_stall_watchdog_config.py`; `docs/perf_runbook.md`, “Freeze and hitch capture.”

## Where hitch samples land

The following categories are **mutually exclusive initiating-stack classifications**. A category owns the whole episode duration for accounting only; a single threshold-time stack does not prove that function consumed every second of the episode. Classification priority was prompt key, countdown, detail debounce, fleet refresh, selector/self-pipe, Textual paint/layout, other.

| Sampled context | Episodes | Assigned episode seconds | Interpretation |
| --- | ---: | ---: | --- |
| Countdown/runtime tick | 87 | 327.574 | Repeated work on a one-second callback |
| Textual paint/layout | 86 | 340.724 | Rendering/allocation sites; GC or paging can amplify these |
| Fleet refresh | 56 | 204.000 | Pure projection and apply work still run synchronously after network awaits |
| Event-loop selector/self-pipe | 62 | 226.513 | Does not identify the worker, GC, or scheduling cause |
| Detail debounce | 40 | 160.386 | Debouncing changes when work runs, not its cost or execution thread |
| Prompt key | 3 | 17.069 | Real prompt-path problem, small share of the global recorded budget |
| Other | 79 | 313.989 | Refresh/watch callbacks, locks, config, and other paths |

This distribution is incompatible with treating the freeze problem as only the two prompt keymaps.

### Runtime tick: cache hits still perform data-scaled work

There were **49 loop hitch starts at `agent_runtime_facade.aggregate_clan_runtime`**, 48 of them under row runtime computation. The chain is:

`_on_countdown_tick → _patch_agent_runtime_rows → patch_active_runtime_rows → patch_runtime_suffix_row → build_runtime_suffix → runtime_interval → _aggregate_runtime → aggregate_clan_runtime`

The source has useful existing optimizations: navigation/typing gates, suffix-only row patches, and a 256-entry cache of now-independent member wires. However:

- `patch_active_runtime_rows()` iterates the widget's loaded rows, rather than explicitly restricting work to the terminal viewport.
- `_aggregate_runtime()` still collects descendants and fingerprints members before every cache lookup.
- The adapter runs `dataclasses.asdict()` for every member and reconstructs Python wire dictionaries on every invocation.
- Rust receives the members again, derives intervals, and aggregates them again for the new `now` value.
- The unchanged rendered-suffix check happens **after** that work.

The “cache hit” therefore does not mean O(1) tick work. Repetition across active containers remains an optimization opportunity.

**Controlled check:** two warmups followed by nine calls at each size, fixed timestamps and one resolved plan-wait interval per member. Timing covers the complete Python adapter, including wire conversion and Rust execution.

| Members per call | Median | Maximum |
| ---: | ---: | ---: |
| 1 | 0.018 ms | 0.024 ms |
| 10 | 0.137 ms | 0.139 ms |
| 100 | 1.830 ms | 1.904 ms |
| 1,000 | 10.175 ms | 13.030 ms |

This benchmark does not model the entire roster, a large dirty heap, paging, or a contended process. It does establish that one normal aggregate call need not take seconds. A watchdog stack inside this binding can reflect native computation, conversion, GC, or page faults; attribution requires more evidence.

The inspected Rust binding already releases the GIL around the core aggregation (`crates/sase_core_py/src/agent_scan/mod.rs:74`). Adding another worker alone will not fix synchronous calls from the UI, and adding GIL release to that core block would duplicate existing behavior.

References: `src/sase/ace/tui/models/_agent_time_aggregate.py:237`, `src/sase/core/agent_runtime_facade.py:14`, `src/sase/ace/tui/widgets/_agent_list_widget.py:325`, `_agent_list_build_patch_single.py:157`.

### Fleet refresh: off the pump still leaves synchronous loop work

The fleet refresh task fetches remote data asynchronously. After the awaits, `_run_agents_fleet_refresh()` calls `project_fleet_agents(...)` **synchronously**. Projection includes remote row construction, identity presentation, status overrides, and clan/session normalization. Applying the result can reproject and finalize the local list again.

One observed stack at **10:38:39 EDT** reaches:

`_run_agents_fleet_refresh → project_fleet_agents → rows_from_response → normalize_remote_host_nodes → apply_status_overrides → refresh_presented_agent_name → foreign_agent_owner_root`

Other fleet stacks enter clan-tribe resolution and list finalization. Moving network calls off-thread did not move these CPU/FFI transformations off the event loop. The existing navigation deferral happens after projection, so it does not protect the projection itself.

References: `src/sase/ace/tui/actions/agents/_fleet_refresh.py:160`, `_fleet_projection.py`, `_loading_finalize.py`; `src/sase/ace/tui/models/_fleet_agents_nodes.py`; `src/sase/core/agent_clan_tribe.py`.

### Detail documents: content hashing itself is on the hot path

The detail debouncer fires a synchronous callback. It can hydrate history, rebuild an agent/clan/tribe document, update the prompt panel, flatten its card tree, and calculate a content digest before deciding whether to apply the result.

At **14:18:02 EDT**, a **7.807-second** episode was sampled at:

`_fire_debounced_detail_update → _apply_agent_detail_update → AgentDetail.update_display → _update_main_source → PromptPanel.update → renderable_content_digest → _update_text_digest`

`renderable_content_digest()` walks the whole renderable tree; each `Text` encodes its plain content and visits its spans. This is O(document size), even when the newly constructed document is ultimately identical. That observation does not prove hashing alone took 7.8 seconds, but it identifies unnecessary allocation and traversal in a synchronous path.

References: `src/sase/ace/tui/actions/agents/_display_detail_render.py:231`, `src/sase/ace/tui/widgets/prompt_panel/__init__.py:164`, `src/sase/ace/tui/util/renderable_digest.py:20`.

### Config tokens: a background refresh still makes the caller wait for thread startup

**22 hitch starts** ended in:

`current_config_token → refresh_thread_to_start.start → threading.Thread.start → self._started.wait → waiter.acquire`

`current_config_token()` serves a stale token after its five-second deadline, but also creates and starts a new daemon thread from the calling thread. `Thread.start()` waits for the new thread to initialize. Under pressure or GIL contention, the supposedly cheap getter therefore still blocks the UI. One sample reached it during fleet finalization via `agent_tabs_view_config()`.

This is direct evidence of a remaining synchronization point, not a claim that normal thread initialization takes seconds on an unloaded host.

Reference: `src/sase/config/core.py:307–355`; specifically the five-second cadence at line 185 and thread startup at line 355.

### Info metrics: work occurs before the cached-result check

`_agent_info_metrics()` constructs a status fingerprint, rebuilds/deduplicates `bulk_ack_roster_universe`, builds a second identity/status fingerprint, and freezes the unread set **before** comparing its cache key. The metric result is cached, but much of the data traversal is not. Nineteen hitch samples included `_agent_info_metrics`; fourteen ended in the bulk-roster deduplication loop.

Use the existing roster/tribe generation mechanisms and an explicit unread-state generation to invalidate cached metrics. Do not simply remove the fingerprints without proving that every in-place mutation advances the relevant generation.

References: `src/sase/ace/tui/actions/agents/_display_detail_info.py:42`, `_unread_bulk_scope.py:51`, `_roster_generation.py`.

## Memory, GC, GIL, and paging

### Live memory pressure is material

Before the restart, `/proc/872820/status` showed:

| Field | Observed value |
| --- | ---: |
| VmRSS | 5,941,908 KiB ≈ **5.67 GiB** |
| RssAnon | 5,899,760 KiB |
| VmSwap | 2,647,808 KiB ≈ **2.53 GiB** |
| VmHWM | 6,791,292 KiB ≈ 6.48 GiB |
| Threads | 31 |

The host reported CPU load around `30.44 / 27.86 / 27.85` on 64 CPUs. CPU PSI was nearly zero at that instant, while memory PSI reported `some avg10=1.81` and `full avg10=1.54`. These are point observations, not a correlation with each historical hitch, but “only CPU overload” is not established and memory pressure is plainly relevant.

A large swapped heap can make otherwise small object walks expensive. RSS alone also misses the swapped portion, so it understates the memory involved.

At **14:24:47 EDT** a new startup record appeared for the same PID, the command acquired `--restart-service`, and subsequent status showed approximately **0.91 GiB RSS and zero swap**. This was an uncontrolled live restart, not an intervention tested by this researcher. It demonstrates that the previous heap state disappeared; it does not establish which code change fixed it or whether memory will grow again.

### The “26-hour-old TUI” inference is wrong for this evidence window

SASE's `_exec_ace_restart_if_requested()` uses `os.execv`. Linux preserves the PID and process-start accounting across exec. Startup telemetry is emitted once per app instance (`_startup_telemetry_recorded` guard), and PID 872820 has 13 startup records.

The last startup record before the measured hitch window was **10:15:09 EDT on October 2**. Thus the window describes an instance a little over four hours old by its end, even though `ps` reported roughly 27 hours of OS process age. A `sase_version` of `0.17.1` is also too coarse to identify the editable checkout revision.

Related telemetry defect: `startup_clock.py` derives interpreter startup from `/proc/self/stat` OS age, so exec restarts produce absurd `interpreter_cli_import_seconds`, including **96,984 seconds** in the 14:24 startup record. This should not be interpreted as a 27-hour import. Add an app-instance identifier and exec-aware clock anchor when improving performance telemetry.

References: `src/sase/main/ace_handler.py:101`, `src/sase/ace/tui/actions/_startup_telemetry.py:97`, `src/sase/ace/tui/util/startup_clock.py:32`.

### Historical retained heap gives a concrete starting point

The September 13–14 sustained capture has 176 heap snapshots over about 15.5 hours. Traced live allocations grow from **54.2 MiB to 1,373.5 MiB**. Its last top sites include:

| Allocation site | Retained bytes at last snapshot |
| --- | ---: |
| `json/decoder.py:361` | 938,561,397 ≈ 895.1 MiB |
| `relations/artifact_links.py:128` | 111,506,944 ≈ 106.3 MiB |
| `core/artifact_file_types.py:115` | 101,861,760 ≈ 97.1 MiB |

The last host sample also recorded **13,463,008 KiB RSS and 1,128,432 KiB swap** for that different process. Python traced bytes and RSS are not interchangeable; native allocations, allocator retention, and profiler overhead can contribute to the difference.

The capture metadata names commit **`e5f902ddd6`**, titled “bound six unbounded module-level caches driving residual heap growth.” Therefore this is evidence **after that cap fix**, not a reason to reapply an already-landed unbounded-cache fix.

Current `relations/artifact_links.py` and `relations/link_index.py` retain up to **64 different aggregate-signature snapshots/indexes**. A signature changes with mtime/size on each aggregate update, so many entries are historical full copies, not independent project scopes. A cap of 64 does not establish a useful byte budget. The artifact-ref completion loader also reads and caches all index rows before truncating the presented candidates.

The historical allocation sites are not proof of the October retaining owner. They justify measuring cache **rows, generations, and retained bytes**, then replacing historical-generation retention with current-per-scope snapshots and bounded pages.

### GC is plausible; it is not measured yet

Selector/self-pipe samples, Textual allocation sites, large heaps, and repetitive pauses are compatible with GC. They are also compatible with paging, CPU scheduling, native binding conversion, or worker interference. A Python watchdog needs execution time and the GIL to produce its record; an allocation-site snapshot can be captured after part of the pause has already elapsed.

The 14:21:00 pump-stall dump shows a worker in `PromptPredictionCorpus.compile`, while the main thread is in `selectors.select`. However, inspected Rust source releases the GIL during the expensive corpus compilation. The Python facade's JSON encoding and the binding's JSON decoding occur outside that released-GIL region. The worker's Python frame cannot distinguish those stages from the released-GIL core computation. This is a candidate for stage instrumentation, not proof of a GIL-holding Rust compiler.

Python provides `gc.callbacks` specifically for start/stop collection observations. Also, `gc.freeze()` moves tracked objects into a permanent generation ignored by future collections; `gc.unfreeze()` is the inverse. Freezing mutable application graphs can consequently retain cycles that later become unreachable. Repeating `freeze()` alone does not restore collection of previously frozen objects. Those are reasons to test a bounded policy rather than freezing the whole live TUI by default. [Python 3.14 GC documentation](https://docs.python.org/3.14/library/gc.html).

The live interpreter is 3.14.7. Python's documentation explicitly says the middle generation and threshold2 behavior were restored in **3.14.5**; advice based on initial 3.14's incremental behavior would be incorrect for this build. [Python 3.14 GC change notes](https://docs.python.org/3.14/library/gc.html).

## Limitations and verification needed

- No code fix was implemented, no live GC settings changed, and no controlled fresh-versus-aged TUI comparison was completed.
- A requested ten-second native `py-spy` capture fell far behind and temporarily stopped target threads during sampling. It was terminated, its execution fully reaped, and the target was confirmed running with `TracerPid: 0`. It produced no usable profile. The pre-restart analysis snapshot predates this attempt; subsequent live data should exclude this profiling interval.
- A simultaneous ten-second `pidstat` observation after the restart reported no major faults, but it overlapped the failed capture and therefore cannot exonerate paging in the earlier large-heap instance.
- Historical profiles have documented delayed sampling/read errors and belong to different revisions/workloads. Their frame counts are attribution hints, not October wall-clock percentages.
- Stack category episode totals are not function CPU totals. The retained logs do not contain enough data to apportion the 11% precisely among GC, paging, native work, and rendering.
- The raw logs are byte-rotated and independently updated. Future verification must retain an explicit run snapshot and run identity before the window rolls away.

## Recommended solution

**Prioritize bounded retained state and generation-based refresh preparation; make the UI consume cheap snapshots. Add GC/paging correlation in the same work, and reserve GC tuning for evidence that demonstrates it is needed.** This targets both demonstrated synchronous work and the large-heap amplification behind the global freezes.

1. **Make a small attribution and regression foundation first.** Add a unique TUI instance ID and imported source/core revision to watchdog, startup, load, and key-to-paint records. Make restart/import clocks exec-aware. Install a lightweight `gc.callbacks` recorder for every generation, recording monotonic start/stop, thread ID, duration, collected/uncollectable counts, and app-instance ID. Put events in a bounded buffer and flush outside the callback; do not dump stacks, serialize JSON, or scan all GC objects from the callback. Add periodic RSS/swap and major-fault deltas, plus spans/counters around runtime ticks, fleet normalization/apply, config refresh, document construction/digest, and prediction encode/decode/compile. This lets one capture distinguish allocation-triggered GC from data processing and paging.

2. **Reduce the retained working set before changing GC policy.** For artifact-link snapshots and indexes, retain the current generation per logical project/scope rather than up to 64 superseded full aggregates. Keep active widgets' snapshots valid through ordinary ownership, with a modest byte/row-budgeted LRU for genuinely distinct scopes. Page completion/index reads at the backend rather than loading every record and only slicing the displayed candidates. Measure the major JSON/link/index/cache owners and Rust prediction handles in a fresh run; do not assume the September owner is unchanged. Acceptance is a stable fixed-workload memory plateau and no growing swap over four hours, then a 24-hour soak. The fresh approximately 1 GiB instance supplies a comparison point, not a universal hard budget.

3. **Move preparation out of periodic UI callbacks and make cache hits cheap.**
   - Runtime: compute member inputs once per relevant roster/runtime generation, restrict tick painting to displayed rows, and cache settled aggregates completely. If live aggregate reevaluation remains material, add an immutable Rust-owned compiled interval handle or batch projection that preserves overlap and human-wait semantics; evaluate only the changing time component without rebuilding Python dictionaries. Do not replace interval-union policy with naïve `elapsed += 1`. New core APIs belong in sase-core, with bindings/tests and the sase revision pin updated.
   - Metrics/clan topology: key memoization on explicit roster, tribe, status, and unread generations. Reuse existing mutation hooks; add coverage for any missing in-place updates. Warm unchanged ticks should not deduplicate the bulk roster or resolve clan declarations again.
   - Fleet: perform response normalization/identity/status projection on a worker using captured immutable inputs. Prepare the list projection off-loop where possible; revalidate request generation, tab, and selected identity when results land. Apply only changed rows/panels. Retain one in-flight refresh and one pending request, and avoid rebuilding the whole tree for an unchanged response.
   - Config: make the UI token getter a pure cache peek. Schedule refresh through a long-lived/coalesced worker; never call `Thread.start()` from a render/query getter. Handle cold initialization on the worker as well.

4. **Stop allocating and hashing unchanged full detail documents.** Have the debouncer enqueue/coalesce generation-based preparation rather than synchronously rebuilding the document. Derive a content token from the selected row's meaningful inputs, source changes, fold state, theme, and hint mode; skip construction before hashing when that token is unchanged. Cache reusable section/card digests, bound large-document work, and restrict repaint to changed blocks. Use existing pump-free scheduling helpers for slow asynchronous preparation; an awaited `to_thread()` in a serial Textual callback still blocks its message pump. Perform widget mutation on the UI thread, with selection/generation checks. Extend typing deferral consistently to plain-agent detail refreshes, not just focused tribe documents.

5. **Run a matched before/after capture, then decide about GC.** Use identical terminal size, query/grouping, archive population, and normal agent/fleet load. Exercise idle ticks, sustained arrivals, j/k bursts, prompt typing, and large clan/tribe documents. Check loop and pump interval unions separately, preserve omitted-episode counts, and compare key-to-paint p95/max alongside phase spans, GC-overlap duration, RSS/swap, and fault rates. Start with a fresh instance, repeat after four hours, and run the 24-hour memory soak. Targets: no ≥1.5-second hitches in a normal 30-minute session, j/k highlight p95 below 16 ms, key-to-paint p95 below 33 ms, and unchanged-refresh work close to zero. If measured GC accounts for the residual pauses, test reduced allocations/retention first, then a carefully bounded freeze/threshold policy with mounted/unmounted widget lifecycle and memory-reclamation checks.

The best first implementation is **current-per-scope, byte-bounded snapshots plus cheap generation-based runtime/metrics/fleet refresh**, accompanied by GC and paging timestamps. Ship those measured changes before a global `gc.freeze()` policy. Restart can temporarily relieve the large heap, but the durable fix is to stop retaining and rebuilding historical state on an interactive event loop.
