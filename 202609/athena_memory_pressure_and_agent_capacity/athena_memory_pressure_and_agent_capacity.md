# Athena memory pressure and reliable capacity for 1,000+ agent nodes

**Date:** September 19, 2026. Measurements are in EDT (UTC−04:00); memory units are binary GiB/MiB.  
**Scope:** Consolidation of two independent reports plus fresh lead-researcher measurements and code review. No existing Athena agents, services, or TUI sessions were stopped, restarted, or reconfigured.

## Findings

**SASE is the dominant contributor to Athena's memory pressure. The number of displayed agent nodes is not the dominant demonstrated cause.** Three separate costs explain most of the problem:

1. **Parked agent processes:** 50 Waiting runners retained approximately **16.5–16.7 GiB RSS**, despite an execution limit of eight. Each waiting node has a heavyweight Python process before admission.
2. **Concurrent verification:** agent-launched pytest workloads consumed approximately **9–21 GiB RSS** across the researchers' changing samples.
3. **Long-lived TUI sessions:** two sessions retained approximately **7 GiB resident memory**, plus roughly **1.8–2.1 GiB swapped out**. Both started before relevant September 18 optimizations.

The lead researcher's fresh, mounted `AgentList` experiment displayed **1,000 actual agent nodes** at **161–169 MiB RSS** across 20 rebuilds. Researcher A also measured Athena's real approximately 1,000-option roster below 200 MiB in an isolated process. These results reject the claim that 1,000 rows inherently require several gigabytes. They do **not** establish that the full application remains bounded over days.

The recommended direction is a **durable admission queue with no heavyweight process per waiting agent**, combined with host-wide memory admission for expensive jobs and a measured TUI endurance budget. A wholesale list-widget rewrite is not the first justified intervention.

## Where Athena's memory is going

### Host pressure is real, but this was not a confirmed OOM event

Athena exposes **62.7 GiB usable RAM** and approximately **64 GiB swap**. At 08:01, the lead researcher observed **52.1 GiB used**, **10.5 GiB available**, and **19.7 GiB swap occupied**. Earlier researchers observed roughly 25 GiB swap occupied. Workload turnover explains some variation.

There was current contention, beyond merely having old pages in swap: memory PSI reported `some avg60=1.11` and `full avg60=1.02`, while two one-second `vmstat` intervals showed swap-in of 104 and 3,228 KiB/s. PSI measures time stalled on a resource; these observations support intermittent memory stalls, not a claim of continuous thrashing or a demonstrated OOM kill. [Linux PSI documentation](https://docs.kernel.org/accounting/psi.html)

Low `MemFree` alone is insufficient diagnosis. `MemAvailable` estimates memory available for new workloads without swapping; PSS apportions shared pages across processes and is better than summed RSS for attributing physical memory. SwapPss is reported separately below and is not additional resident RAM. [Linux `/proc` documentation](https://docs.kernel.org/filesystems/proc.html)

### Fresh process attribution

The lead researcher's 08:02 `/proc/*/smaps_rollup` walk produced:

| Process class | Processes | Resident PSS | SwapPss | Interpretation |
| --- | ---: | ---: | ---: | --- |
| `run_agent_runner.py` | 59 | **18.23 GiB** | **2.20 GiB** | Largest persistent SASE class |
| pytest/xdist and test launchers | 24 | **12.66 GiB** | **1.05 GiB** | Transient verification fan-out |
| SASE TUI | 2 | **6.93 GiB** | **1.80 GiB** | Two large, old application heaps |
| Other SASE helpers | 29 | **1.40 GiB** | **1.11 GiB** | Broad command-based classification |

These SASE-associated classes account for about **39.2 GiB resident PSS**. Test memory is agent workload, not Agents-tab storage. A preceding RSS sample put Prometheus-related processes at approximately **4.0 GiB**; their PSS was inaccessible to the SSH user. Process exits and launches make this an approximate, non-atomic attribution, not an exact reconciliation to kernel totals.

Joining a separate 08:01 `sase agent list -j` sample to runner PIDs found **50 Waiting runners at 16.49 GiB RSS**, averaging **338 MiB each**, plus four Queued runners at 1.68 GiB and three Running runners at 1.11 GiB. Two classified runner PIDs did not match that listing. Both independent researchers found essentially the same 50-waiter population and approximately 343 MiB per waiter earlier.

Runner RSS/PSS describes the runner itself; it does not automatically include separate provider subprocesses. Queued runners can be expensive before provider execution. The population above should not be described as 59 concurrently executing providers.

## Why waiting agents are the primary scaling failure

Current `src/sase/axe/run_agent_runner.py` imports execution/finalization modules at module load, then performs `bootstrap_agent_run()` before dependency admission. Prompt expansion also precedes runner-slot admission. Dependency and capacity waits keep that interpreter and its retained state alive.

The configured runner limit of eight therefore bounds admitted execution, **not all resident runner processes**. Adding waiting work grows memory even when useful concurrency is unchanged.

This is already a recognized problem: commit `38ac15b07` added `release_idle_memory()`, which runs garbage collection and attempts glibc `malloc_trim(0)` on wait entry and periodically. Its tests verify invocation through mocks. They do not prove a real post-bootstrap RSS budget on Athena's Python 3.14 runtime. The observed population remains far too expensive; existing data does not isolate how much is live state, Python allocator retention, or native allocation.

At the measured footprint, **1,000 similarly parked runners would extrapolate to approximately 330 GiB RSS**. This is a sizing extrapolation, not a load test. Even reducing each waiter to 20 MiB leaves roughly 19.5 GiB for 1,000 waiters. A small waiting-process stub can provide interim relief; durable waiting records serviced by a bounded scheduler are the scalable design.

Historical nodes need no process. An agent family can also contain many shell and step rows. Capacity requirements must distinguish **1,000 retained agent nodes**, **1,000 pending launch intents**, and **eight admitted executions**.

## What the TUI evidence proves

### Three complementary measurements

| Evidence | Workload | Memory result | Limit of inference |
| --- | --- | --- | --- |
| Existing Athena sessions | PIDs 1598377 and 1880150 | About 4.08 and 2.90 GiB RSS at 08:02 | Confirms large retained heaps; no allocation-site attribution |
| Researcher A, fresh current-code process | Real loader data: 932 agent/shell/step rows and 999 options, including banners | About 191 MiB peak RSS; 20 loader/render replacements reached about 250 MiB | Real data, but a short isolated path; only 292 top-level agent nodes in the 932-row sample |
| Lead researcher, 08:03 | Headless mounted Textual app containing the production `AgentList`; 1,000 independent agent nodes, 1,002 options; fresh row objects on each of 20 passes | RSS 160.9 MiB after pass 1, 168.3 after pass 5, 168.7 after pass 20; final PSS 142.4 MiB | Actual widget layout/rendering, but synthetic rows and no complete `AceApp` loader/detail/refresh lifecycle |

The lead experiment ran for approximately nine seconds on Athena using CPython **3.14.7**, SASE **0.17.1**, `sase-core-rs` **0.34.59**, and Textual **8.2.8**. It recreated mixed Done/Failed/Waiting/Running rows, changed selection, allowed the message pump to settle, and collected garbage before measurement. `is_agents_tab_agent_node()` confirmed all 1,000 entries were agent nodes. No real agents were launched.

The render-only test does not substitute for a full-app soak. It does demonstrate that B's prediction of unavoidable multi-gigabyte memory from 1,000 `OptionList` rows is unsupported. Conversely, A's approximately 1,000 options cannot by itself certify 1,000 family nodes with expanded descendants.

### The live sessions predate relevant fixes

The newer TUI started September 18 at **14:03:07**; the other started September 15. Relevant commits landed after the newer process started:

| Commit | September 18 time | Change |
| --- | --- | --- |
| `3962d8819` | 14:09 | Isolate agent row graphs during background refresh |
| `264eedc6c` | 15:53 | Trim TUI startup imports |
| `13a8efbb4` | 18:06 | Project compact index rows before JSON hydration |

Long-running editable-install processes retain already-imported code until restart. These old sessions are poor evidence for current-code baseline memory. Restarting is justified, but there is no evidence yet that these commits eliminate all long-term growth.

Anonymous private memory establishes a heap-like allocation footprint, not specifically live Python objects. Neither session had the heap sampler enabled. A's idle stack samples and B's process CPU averages cover different time windows; neither identifies which allocations remain reachable.

The older runbook's dramatic September 11 before/after reduction also involved **different TUI PIDs and a restart**, in addition to scratch cleanup. It does not prove that deleting scratch shrank an unchanged TUI heap.

### Corrected cache attribution and remaining risks

B identified plausible retainers, but one central claim does not survive current-source call-site review:

- `AgentSnapshotCache.dismissed_bundles()` can load every dismissed bundle, but **no production call site was found in current source**. `_revive_archive.py` uses `load_dismissed_bundles_page()`. The existence of 34,328 bundle files is not evidence that all their `Agent` objects occupied either live heap. Historical execution and heap contents remain unverified.
- The attempt-history/retry dictionaries and tool-call cache do have production uses without an explicit overall size bound. They are valid endurance risks, not measured explanations for all seven GiB.
- Revival pagination still accumulates merged rows and prior page snapshots while browsing. Pagination is not automatically a bounded resident window; exercise this interaction in the soak.
- Multiple roster lists can share references. Counting lists or the model's 200+ fields does not establish a per-node retained size. Large detail payloads and reachable graph contents matter more.
- The viewport grows a loaded prefix and the widget retains options for its supplied rows. True data virtualization remains useful at larger scales, but the measured 1,000-node widget does not establish it as the urgent RAM fix.

## Mitigations in priority order

### Immediate operational relief

1. **Retire the abandoned TUI and restart the needed session on current code**, using the normal lifecycle after checking session ownership and attached work. Exiting both old processes releases their approximately seven GiB resident footprint; net savings depend on the replacement session. Run only the sessions actually needed.
2. **Review unnecessary Waiting/Queued work and cancel it through SASE lifecycle commands.** Ten average waiting runners represent approximately 3.3 GiB RSS. Hiding or dismissing display rows alone must not be assumed to stop their processes.
3. **Avoid overlapping large verification suites while pressure persists.** Schedule test jobs and their worker counts against one host memory budget. The observed one-GiB-class pytest workers make CPU-count-only admission insufficient.
4. **Restrict further pending-runner fan-out until waiters are cheap.** Lowering the admitted execution limit alone does not remove parked processes. Use available memory and sustained PSI with hysteresis to defer new memory-heavy work; calibrate thresholds from Athena measurements.

These are recommendations; this research did not carry them out. More swap or deleting durable agent history does not address the demonstrated process cost.

### Targeted TUI investigation

Start a replacement diagnostic session with `SASE_TUI_HEAP=1` and `SASE_TUI_HEAP_INTERVAL_SECONDS=60`, and collect matching PID-level RSS/PSS/SwapPss, row counts, and cache counts. The implementation is documented in `docs/perf_runbook.md` and `src/sase/ace/tui/util/heap.py`.

For startup allocation coverage, begin tracing at interpreter startup with `PYTHONTRACEMALLOC`; the SASE sampler normally starts during application initialization, after some imports. Compare an instrumented diagnostic run with an uninstrumented budget run because tracing has overhead. Rising traced bytes can locate Python retention; flat traced bytes with rising RSS can also reflect native allocations, fragmentation, or allocations made before tracing began. [Python tracemalloc documentation](https://docs.python.org/3/library/tracemalloc.html)

Use the results to cap caches by entries **and bytes**, evict departed identities, bound archive-page retention, and avoid retaining large detail payloads in list state. If the full application still exceeds its budget after these fixes, implement a compact indexed roster with viewport/detail hydration and a genuinely bounded rendering window.

## Acceptance criteria for 1,000+ nodes

These are **proposed engineering budgets**, not already-passed guarantees:

| Area | Required test and initial target |
| --- | --- |
| Full Agents tab | At least 1,000 real agent nodes through production load/apply/render paths, with mixed families, expanded shells/steps, clans, filters, fleet rows, and large details; record total rendered rows separately |
| TUI memory | Uninstrumented RSS below **500 MiB after one hour**, below **600 MiB after 24 hours**, and less than **50 MiB post-warmup growth** across at least 500 mixed refresh/interaction cycles; explain and adjust budgets only with measured evidence |
| Retention | Visit many distinct agents, open tool details, dismiss/revive multiple pages, change queries, replace graphs, and repeatedly expand/collapse families; verify cache sizes and retained objects stabilize |
| Pending work | **1,000 durable Waiting/Queued intents**, no heavyweight runner/provider process before admission, a bounded number of scheduler processes, and a proposed **256 MiB incremental scheduler budget** |
| Execution | Configured capacity bounds admitted execution groups; account for provider subprocesses, job children, and separate resource budgets rather than counting visible rows |
| Recovery | Scheduler restart, cancellation-versus-admission races, dependency changes, and expired claims preserve queue state without duplicate execution |
| Host | Test the combined workload with eight admitted executions and representative verification; maintain calibrated headroom and avoid sustained memory PSI/swap churn |

Swap occupancy need not immediately fall below a fixed number for recovery to be successful. Observe current stall and swapping rates alongside available memory.

The existing 1,000-agent performance fixture is insufficient as a memory acceptance test: `tests/perf/tui_trace/scenarios.py` primarily starts on the Patches tab and injects agents in a large-reply branch; it does not establish a production-path 1,000-node memory ceiling. Add the full-app workload above, plus a real Linux RSS test for any interim runner trimming/import change.

## Evidence and provenance

- [Researcher A report](athena_memory_pressure_and_agent_capacity__a.md): dependency **`research.9.cdx`**, original canonical reference `research:202609/athena_sase_memory_and_1000_node_scaling__a.md`, immutable snapshot `file:explicit:f34b7bab6e76c72c2b661def`.
- [Researcher B report](athena_memory_pressure_and_agent_capacity__b.md): dependency **`research.9.cld`**, original canonical reference `research:202609/athena_sase_memory_pressure__b.md`, immutable snapshot `file:explicit:dfc6ea8b1ee456185af74abf`.
- Both reports were consumed through `sase artifact read`. Their local research-checkout copies were moved with their A/B identities intact; SHA-256 checks confirmed unchanged contents. Other checkouts and immutable snapshots were untouched. No predecessor chat transcripts were consulted.
- Lead evidence: read-only SSH samples at **08:01–08:02 EDT** using `free`, `/proc/pressure/memory`, `vmstat 1 3`, process command classification, `/proc/<pid>/smaps_rollup`, and `sase agent list -j`; mounted-widget experiment at **08:03 EDT** using the installed runtime. PSS could not be read for three Prometheus processes; five processes disappeared during enumeration.
- Local source review at **`8989d0a72`**: runner bootstrap/admission and `runner_idle_memory.py`; TUI `_snapshot_cache.py`, `_revive_archive.py`, `_dismiss_memory.py`, `llm_calls/cache.py`, `AgentList`, and `_agent_list_build_rebuild.py`; performance scenarios, heap sampler, and `docs/perf_runbook.md`. Installed package versions above identify the separate Athena experiment, not a verified identical remote source revision.

## Recommended solution

**Implement centralized, durable admission so waiting agents occupy records, not heavyweight Python processes.** Store an idempotent launch intent and its visible state, evaluate dependencies/time/hold/capacity centrally, and launch the runner only after an atomic claim. Include leases, cancellation, restart recovery, and reconciliation of already-spawned children so crashes do not duplicate work. Shared eligibility and lifecycle rules belong in **`sase-core`**; the service/Python adapter should perform process and filesystem side effects.

Use deferred heavyweight imports or a minimal pre-admission launcher only as an interim improvement, backed by actual RSS measurements. Add host-wide memory reservations for verification and other expensive child jobs so the queue fix does not simply shift the pressure to pytest.

In parallel, restart and profile the TUI, fix demonstrated retention, and enforce the full-app 1,000-node endurance budget. Keep compact index projection and introduce true data virtualization if those measurements require it. This order removes the largest proven cost first, preserves 1,000+ useful agent nodes, and ties further UI changes to evidence rather than attributing old multi-gigabyte heaps to row count alone.
