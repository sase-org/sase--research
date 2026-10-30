# TUI slowdown: memory pressure, repeated reconciliation, and a bounded snapshot design

Independent research by **cdx**, 2026-10-30. No other report or researcher findings from this swarm were consulted.

## Finding and scope

The strongest current evidence favors reducing the amount of data repeatedly loaded, copied, and converted inside the TUI process. The problem is already substantially larger than a slow highlight handler: the observed process grew by about **8.5 GB of resident memory in 135 minutes**, spent **10.1% of its heartbeat time in garbage collection**, and recorded **12.3% in loop-hitch time**. These measures overlap; they must not be added.

Keep Textual and the existing Rust backend. Build on the current indexed list projection, refresh coordinator, generation counters, and incremental row updates. Make background preparation proportional to changed data, and make UI work proportional to displayed changes. A framework rewrite, more worker threads, or another round of GC-threshold tuning would have a weaker evidence base and greater reliability risk.

This was a read-only investigation of application behavior, with short synthetic probes in separate processes. I did not restart the live TUI, attach a debugger, enable heap tracing or GC census, change configuration, or modify application code. Findings identify a direction and prioritized experiments, not a verified fix.

## 1. Evidence from the running TUI

### Provenance and measurement limits

The reviewed sase checkout was `feae9c8777948bf0984ccb26be63c1167998cfd6`. The newest startup record identified the running instance as:

| Field | Observed value |
| --- | --- |
| Instance | `f8c86c23` |
| PID | `2704211` |
| Startup record | 2026-10-30 18:32:16.578 UTC |
| Imported sase revision | `dab2d701fbac135ff3e828b2d0efd330c5a19b47` |
| Sase version | 0.18.1 |
| Python, from live heartbeat | 3.14.7 |
| Initial visible rows / index rows | 34 / 457 |
| Visible-ready time | 6.270 seconds after mount |

A source comparison between the live imported revision and the reviewed checkout showed only five TUI files changed, concerning deck/card navigation. In particular, the graph-copy classifier introduced by `3266724c91` was already present in the live revision. Recommending that already-landed optimization as the new fix would miss the current problem.

The opened Rust checkout was `0ec67fdcebccd0154a84168ad54e45e6c5793c1d`; sase's CI pin was `17e79c8cf5323d2ef4abcadef3bf95aa4e81c24b`. These are source-inspection identities, not proof of the live extension's build revision. The isolated workspace probes used Python 3.14.7 with the GIL enabled, sase-core-rs 0.43.2, Textual 8.0.1, and Rich 14.3.3. I did not independently establish the live process's Textual/Rich versions.

I read `tui_startup.jsonl`, `tui_stalls.jsonl` and its rotation, `tui_agent_loads.jsonl` and its rotation, and selected `/proc` fields. The first heartbeat extraction retained 28 records for this instance, ending at 20:47:52.681 UTC. Later rotation removed some early records, so the numerical evidence below records that first extraction explicitly. The source logs were live and were not captured as an atomic archive.

### Memory and pause behavior

| Measure | First extraction |
| --- | ---: |
| First heartbeat | 18:32:27.139 UTC |
| Last heartbeat | 20:47:52.681 UTC |
| Sum of recorded heartbeat windows | 8,141.849 seconds |
| RSS, first → last | 1,782,239,232 → 10,279,346,176 bytes |
| Swap, first → last | 0 → 4,235,898,880 bytes |
| Allocated Python blocks, first → last | 6,693,424 → 18,301,027 |
| Process major faults, first → last | 3,695,893 → 4,120,449 |
| GC time, all generations | 823.398 seconds; 10.11% |
| Loop-hitch heartbeat total | 1,004.613 seconds; 12.34% |
| Rate-suppressed loop-hitch subset | 35.356 seconds, already included above |

Generation 0 accounted for 265.268 seconds of GC, generation 1 for 295.815, and generation 2 for 262.315. **About 68% of GC time was in generations 0 and 1.** Focusing only on full collections would therefore leave most measured GC time untouched.

The freeze-report tool observed 74 idle-triggered full collections for this instance, with median 2.745 seconds, p95 4.991 seconds, and maximum 6.781 seconds. “Idle” describes when a collection was admitted; it does not guarantee that a user returning during the pause receives prompt service.

A direct process sample at 20:48:31 UTC showed roughly 8.37 GiB RSS and 5.05 GiB swap. The different RSS/swap balance seconds after the heartbeat illustrates an actively changing working set, not a stable plateau.

The host had 64 logical CPUs, load averages around 30/27/27, about 9.9 GiB available memory, and about 41.2 GiB used swap. A later pressure sample showed zero recent CPU pressure but measurable memory and I/O pressure. Load average alone does not establish CPU saturation. Paging and host activity can amplify application costs; neither justifies ignoring the TUI's own memory growth.

**Interpretation:** severe allocation/retention pressure and multi-second pauses are established. An unbounded leak in a particular cache is not established. Garbage awaiting cyclic collection, reachable old graphs, document/render caches, allocator retention, and native allocations need separate attribution.

### Refresh work is expensive even for small deltas

For the same instance, through 20:48 UTC, the retained slow-load log contained 262 records. This log is thresholded: the following distributions describe **slow loads only**, not all refreshes.

| Kind | Records | Median input rows | Disk median / p95 | Preparation median / p95 | Apply median / p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Broad path, logged as `full` | 157 | 443 | 25.490 / 43.902 s | 1.434 / 2.614 s | 0.517 / 0.826 s |
| Artifact delta | 103 | 5 | 0.640 / 1.993 s | 2.623 / 5.742 s | 0.537 / 1.219 s |
| Monitor reconciliation | 2 | — | Separate stage: median 3.984 s | — | — |

“Full” is the loader's broad-path label; it does not mean every one requested complete archive history. Sources included 68 auto-refreshes, 32 roster-completion retries, 24 quiet-time Tier-2 reconciliations, and 14 index revalidations among the broad-path slow records.

The worst recorded broad disk stage was a quiet-time Tier-2 load at 20:27:19 UTC: **76.524 seconds**, comprising 59.378 seconds in the index stage and 15.074 seconds in decoding, with 1,117 output agents. The worst delta apply stage was 2.894 seconds. These stage clocks include scheduling delays and contention and are not CPU profiles.

The important scaling mismatch is that a median five-row delta still incurred seconds of preparation. It warrants investigating the cached graph and global projections touched by that delta. The records do not by themselves prove that copying accounts for all preparation time.

### Attribution clues and missing evidence

A subsequent bounded extraction found 28 hitch-start stacks ending at `aggregate_clan_runtime`, 21 at the GC callback, and repeated occurrences of project-key conversion, token stat calls, and rendering. These are **watchdog snapshots**, not sampling-profile percentages. A late watchdog may observe the code running after a pause; a GC callback frame is not evidence that the callback itself caused the cost.

There were no key-to-paint samples for this instance in the current perf file. That file last changed on October 29; the trace file last changed on October 27 and was about 585 MB. I read its metadata only. There were no GC-census rows in the inspected stall logs. Thus this investigation cannot report current j/k p95, prompt-input latency, or a retained-type census. Historical trace files must not be presented as current evidence.

The freeze report's broad 16:00–20:48 invocation divided each instance's totals by the requested 17,280-second window. For this shorter-lived instance that produced misleadingly low percentages. The 10.11% and 12.34% above use the sum of this instance's heartbeat windows instead. They remain diagnostic figures, not a completed four-hour acceptance run.

## 2. What the code explains

### A. Safe mutable-graph isolation has an allocation cost

`models/_agent_graph.py` copies every reachable Agent once, preserving aliases through a memo. It recursively copies mutable containers and relinks row relationships. This is necessary because “frozen” snapshot wrappers still contain mutable Agent objects.

`actions/agents/_loading_graph.py` now classifies which cached roots need detaching. Authoritative replacement can skip discarded history, but a delta patch over cached history still needs the cached roster; capacity and fleet roots may also need detaching. This is exactly the path where the live slow records show small inputs and expensive preparation.

The existing `copy_agent_rows_relinked` is cheaper, but its contract permits only attribute reassignment and read-only use of nested leaves and out-of-batch rows. It is **not** a safe replacement for the general graph-copy boundary. The isolation tests deliberately pause workers while checking that live clan/session relationships remain intact.

A short synthetic probe used one root with N children and child-to-root back-pointers, one warmup and five measured copies, with application modules explicitly imported from this workspace:

| Children | Full reachable graph copy, median | Relinked roster copy, median |
| --- | ---: | ---: |
| 100 | 20.753 ms | 1.441 ms |
| 600 | 126.154 ms | 7.295 ms |
| 1,200 | 257.571 ms | 18.903 ms |

These operations have different safety contracts; the table is not a proposed drop-in speedup. It establishes that copying is data-scaled even in a minimal graph, before full preparation and rendering.

In a separate 600-row probe, weak references to two copied nodes remained alive after releasing the result and became dead after `gc.collect()`. That collection reclaimed 12,600 objects process-wide in 76.845 ms. It demonstrates a real cyclic-garbage mechanism, not that these nodes explain the live process's entire growth.

**Architectural consequence:** preserve isolation while reducing the need to copy. Immutable records with relationships expressed as IDs can share unchanged data safely. Shallowly copying today's mutable graph cannot provide that guarantee.

### B. Runtime-cache hits still walk the graph

`models/_agent_time_aggregate.py::_aggregate_runtime` collects descendants and builds a fingerprint for every member **before** consulting its wire/result caches. A same-bucket hit avoids wire rebuilding and Rust aggregation, but still pays traversal, tuple creation, hashing, and comparisons.

The synthetic probe's repeated same-time runtime query took median 0.256 ms at 100 children, 2.423 ms at 600, and 3.648 ms at 1,200. These are small single-container costs that can accumulate across nested containers and repeated rendering.

On cache misses, `core/agent_runtime_facade.py` converts member dataclasses with `asdict`. The Rust binding then parses Python objects, releases the GIL for core interval aggregation, and converts the result back. GIL release is already present. It does not make a synchronous call from the UI thread asynchronous, nor eliminate Python-side traversal and conversion.

`patch_active_runtime_rows` iterates the widget's `_agents` collection. Audit the actual visited and patched counts before assuming its “visible rows” description means terminal viewport-only work.

**Next improvement:** cache derived runtime state by a trustworthy runtime-input revision, compute interval-union summaries in Rust when inputs change, and let the UI update elapsed display from compact summaries. Preserve overlapping intervals, plan/question waits, monitor/gate semantics, terminal transitions, and descendant membership. Existing roster-generation hooks are useful infrastructure, but a global bump on unrelated changes is too coarse for the final cache design.

### C. Indexed loading and background work are already implemented

The current loader requests `record_shape="list"` and `agents_list_projection=True`. Rust already supports windowed cached queries. A proposal to “add an index” or “load only list data” without identifying the remaining wide stage would repeat existing work.

There is a real distinction between serving a snapshot and proving archive completeness. In `_agent_loader_artifacts.py`, full-history requests force revalidation. Rust's `agent_scan/index/query.rs` then discovers source directories and repairs stale rows before returning complete-history results. Removing that work while leaving `complete_history` true would silently hide new or deleted records.

The Python facade also uses an operation lock, with a bounded-read variant elsewhere. The large index-stage clock can include lock waiting, source reconciliation, database work, native-to-Python conversion, and scheduling. Its name is insufficient attribution.

Broad and delta refreshes already share the `_agents_loading` guard and pending-work machinery. The fix should improve the admission/freshness decisions within that coordinator, not introduce a competing scheduler.

**Next improvement:** keep serving the last usable indexed snapshot while one reconciliation establishes a new generation; reuse its completeness watermark until a relevant source change or repair condition invalidates it. Track why completion retries and Tier-2 repairs recur. Add finer timing around lock wait, reconciliation, selection, serialization, hydration, and graph preparation before choosing the backend optimization.

### D. Some supposedly cheap callbacks still do data-scaled work

The normal auto-refresh token probe already runs in `asyncio.to_thread`. However, the capacity-feed timer invokes its token probe synchronously. A stat-only call can still block, particularly under I/O pressure.

Watcher callbacks classify path batches on the UI thread. During prompt activity they can retain the path set and repeatedly classify it on a deferred timer. During navigation, the deferral path schedules timers carrying paths. This is a plausible amplification point during filesystem bursts, supported by one observed hitch stack in path classification, but queue growth was not measured.

Prefer one bounded accumulated change set, one pending notification, and worker-side classification where practical. On overflow, mark the affected surface uncertain and schedule authoritative reconciliation. Preserve notification deadlines and selected live-reply updates; delaying every event uniformly would break useful behavior.

Textual explicitly requires thread workers to marshal widget updates to the UI thread. SASE's additional pump-free-task rule addresses the separate problem of awaiting slow work inside its serial message callbacks. Both constraints must remain in force. [Textual worker guidance](https://textual.textualize.io/guide/workers/)

## 3. Design choices ranked by benefit and risk

| Option | Judgment |
| --- | --- |
| Improve existing refresh admission and reuse reconciliation evidence | First priority: targets repeatedly expensive work while retaining existing lifecycle and fallback paths. |
| Immutable, versioned Agent read model; deltas update affected relationships | Preferred structural change: reduces copying, Python object churn, and stale-result ambiguity. Stage it by projection rather than replacing every Agent consumer at once. |
| Runtime summaries invalidated by relevant field changes | High-value narrow change, supported by code and watchdog clues. Requires semantic parity tests. |
| Move remaining filesystem probes/classification out of callbacks | Useful focused hardening; keep UI installation bounded and generation-checked. |
| Bounded document/render caches and viewport work | Investigate with ownership/size counters; no evidence yet identifying one cache as the principal leak. Bound bytes as well as entry count. |
| Dedicated process for expensive read preparation | Contingency if Python heap/GIL interference persists after bounded work. Adds IPC, duplicate memory, versioning, crash recovery, and shutdown complexity. Reuse the service architecture if this becomes necessary. |
| More threads | Weak primary remedy. Existing threads share the interpreter heap and, on the tested build, the GIL. Conversion and cyclic collection remain. |
| GC disable, repeated freeze, or aggressive threshold changes | Reject as primary remediation. The model has cycles; these approaches trade pause timing for retention risk. |
| Textual/framework rewrite or free-threaded-Python migration | Reject for this investigation: broad compatibility risk with no evidence that either addresses the unnecessary work. |

PyO3's guidance supports releasing the GIL around Rust-only work; that is already done in the inspected bindings. The remaining boundary allocation and synchronous caller costs still need measurement. [PyO3 parallelism](https://pyo3.rs/v0.25.1/parallelism.html)

Python version details matter: 3.14.5 restored generation 1 and threshold-2 behavior, so the observed 3.14.7 process should not be diagnosed from early-3.14 incremental-GC assumptions. Freezing moves tracked objects out of future collections; it is not a leak fix. [Python GC documentation](https://docs.python.org/3.14/library/gc.html)

## 4. A staged, reliability-first implementation

### Stage 1: close the evidence gaps and eliminate redundant work

Capture one actual busy session with instance-attributed key-to-paint data, prompt activity, heartbeat windows, and bounded trace output. Preserve current and rotated logs before they expire. Include tab changes, typing, agent completion bursts, launches, dismissals, and file following. Compare under similar host memory/I/O pressure.

Add inexpensive counters to existing spans: requests coalesced, broad/delta decisions and reasons, input/output rows, graph nodes copied, runtime members visited, apply rows touched, stale results discarded, and live snapshots held. Log byte/count estimates for document caches and current/previous/preparing rosters. Avoid a full-heap walk on a frequent timer.

Trace one broad load and one five-row delta into the component stages identified above. Check whether a completion result is invalidated by a genuinely relevant mutation, an overly broad token, or a stale concurrent result. Keep the authoritative repair path; prevent avoidable repetition and preserve a last-known-good snapshot with explicit freshness.

Land the remaining callback-I/O and watcher-coalescing fixes as small changes with fault and overflow coverage.

### Stage 2: make runtime and row updates generation-aware

Compute runtime membership and interval summaries once per relevant input change. Reuse them during elapsed-time ticks; update only changed suffixes. Ensure the revision changes on every relevant status, timing, relationship, and question/plan transition.

Then introduce immutable compact records behind the existing preparation boundary. Separate domain facts from mutable presentation state: selection, folds, marks, scroll position, and widgets remain in the TUI. Relationship maps use stable IDs, allowing unchanged rows to be shared without cyclic Python object graphs.

A delta must identify affected parents/containers as well as changed leaves. Structural edits may require wider recomputation. Use the existing conservative whole-graph path until an incremental case proves equivalent; do not claim O(delta) for operations whose semantics genuinely affect the whole query result.

### Stage 3: keep expensive domain work in Rust and publish bounded results

Extend the existing Rust list projection and read model rather than creating a second authority. Rust owns shared status, relationship, interval, completeness, and reconciliation semantics; Python holds thin adapters and presentation state. Limit crossings to needed fields and bounded pages or changed records.

Version results by source generation and view/query request. Apply only a result still valid for current inputs, and recapture selection/tab after every await. Keep at most a bounded number of old/current/preparing snapshots; release superseded results promptly. Bound concurrent preparation across surfaces if measurements show their combined heap churn is the problem.

Any new binding requires the matching wire/API tests and an updated `sase-core-revision.txt` pin. Do not spread backend semantics back into Python to obtain a local speedup.

## 5. Correctness and acceptance

Preserve these behaviors explicitly:

- Worker preparation never mutates rows currently rendered by the UI.
- Older loads cannot resurrect a dismissed/deleted row or overwrite a newer mutation.
- Query incompleteness remains visible until authoritative reconciliation proves completeness.
- Selection, folds, marks, pane state, and scroll position survive background updates.
- Cancellation, teardown, exceptions, and stale results release loading flags and snapshots.
- Watcher loss/overflow and lock contention converge through the existing repair mechanism.
- Launch, cleanup, and other durable actions remain durable and correctly observed.

Reuse the graph-isolation barrier tests, incomplete-history merge tests, roster-generation guard tests, runtime semantics tests, incremental-display guards, and existing TUI navigation/trace harnesses. Extend them for failed/cancelled preparation, deleted parents, changed grouping membership, same-identity replacement, out-of-order results, and worker pause while the user navigates. Use a legacy result as a comparison oracle in tests, avoiding an always-on production double computation.

Measure scale while holding the active/visible set constant and increasing closed history; separately scale active rows and relationship fan-out. Otherwise a history-independence claim is confounded by more visible work. Record queue depth, allocated/copy counts and retained bytes alongside timing. Small repeatable probes identify mechanisms; they cannot replace a long-session check.

Use the project's existing acceptance targets: j/k p95 below 16 ms on each normally used tab, idle full-GC p95 at most 500 ms, GC below 3% of wall time, loop hitches below 0.5%, no automatic/backstop full collection within two seconds of input, less than 500 MB RSS growth over four contiguous measured hours, and zero sampled swap. Include prompt typing and a representative busy hour, and report missing evidence as incomplete. Propose an additional apply-work budget with measured margins; do not turn a noisy microbenchmark into an arbitrary CI gate.

No application tests were run for this research-only deliverable. The synthetic probes are attribution experiments, not acceptance results. A later implementation should run the repository-required checks and focused behavior/performance suites; `check-full` remains explicit-only.

## 6. Source map and reproduction notes

All code references below were read from the authorized local checkouts, not fetched from repository websites.

| Source | Relevant entry points |
| --- | --- |
| sase `src/sase/ace/tui/models/_agent_graph.py:56` | Full copy and restricted relinked copy contracts |
| sase `src/sase/ace/tui/actions/agents/_loading_graph.py:66` | Cached-root classifier and ownership boundary |
| sase `src/sase/ace/tui/actions/agents/_loading_compute.py:605` | Worker preparation boundary |
| sase `src/sase/ace/tui/models/_agent_time_aggregate.py:260` | Traversal and fingerprinting before cache lookup |
| sase `src/sase/core/agent_runtime_facade.py:14` | Member-to-dictionary conversion |
| sase `src/sase/ace/tui/widgets/_agent_list_widget.py:325` | Runtime-row tick loop |
| sase `src/sase/ace/tui/models/_agent_loader_artifacts.py` | Existing list projection and forced full-history revalidation |
| sase `src/sase/ace/tui/actions/agents/_loading_refresh*.py` | Shared refresh guards, delta fallback, completion/revalidation scheduling |
| sase `src/sase/ace/tui/actions/event_refresh/_watcher.py:19` | Navigation/prompt deferral and path classification |
| sase `src/sase/ace/tui/actions/event_refresh/_auto_refresh.py:67` | Synchronous capacity token probe |
| sase `src/sase/ace/tui/util/gc_policy.py`, `gc_telemetry.py` | Existing idle policy and heartbeat counters |
| sase-core `crates/sase_core/src/agent_scan/index/query.rs:254` | Cached serving versus source reconciliation |
| sase-core `crates/sase_core_py/src/agent_scan/mod.rs:77` and `:607` | Runtime/index bindings and GIL release |
| sase-core `crates/sase_core_py/src/json_bridge/mod.rs:232` | Direct serialization into Python objects |

The operational contract and targets came from audited reads of `tui.md`, `tui_perf.md`, and `ace.md`, plus `docs/contribute/perf-runbook.md`. The report registration procedure came from audited `sase_artifacts.md`.

The initial diagnostic invocation was:

```sh
tools/tui_freeze_report --since 2026-10-30T16:00:00Z --until 2026-10-30T20:48:00Z
```

For the percentages in this report, filter heartbeat rows to `app_instance_id == "f8c86c23"`, sum their `window_s`, then divide the sum of `gc_generations[*].total_s` and the sum of `loop_hitch_seconds` separately by that denominator. Do not add suppressed totals again. Filter the load log to the same instance and cutoff, partition by `load_kind`, and use the available stage fields. Percentile tables use sorted-index `round(0.95 * (n - 1))`. Logs may already have rotated past the captured evidence.

Synthetic probes ran as `PYTHONPATH=src .venv/bin/python` from the sase checkout. They constructed Agent rows in memory with unique identities, a root's `runtime_children`, and child `agent_session_container` back-pointers; compared `copy_agent_graph([root])` with `copy_agent_rows_relinked([root, *children])`; and timed repeated same-time `runtime_interval(root, now)` calls. They performed no artifact-store reads or TUI actions. Host contention and a small sample count limit their absolute timings.

## Recommended solution

**Keep the current TUI and evolve its existing Rust-backed loading path into a bounded, immutable, versioned read model.** First measure and stop unnecessary broad reconciliation and repeated preparation; then precompute runtime summaries and make proven delta cases update only affected records and relationships. Preserve the current graph isolation until immutable replacements make sharing safe, keep explicit completeness and stale-result checks, and retain conservative repair paths.

Judge success by a representative four-hour memory/responsiveness run and behavior parity, not by a single faster refresh. The evidence supports reducing workload and object churn first; it does not yet justify a framework rewrite, blanket concurrency increases, or disabling garbage collection.
