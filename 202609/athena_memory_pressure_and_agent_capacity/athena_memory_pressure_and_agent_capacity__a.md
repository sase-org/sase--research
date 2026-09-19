# Athena SASE memory investigation and 1,000-node scaling

Date: 2026-09-19  
Researcher: A  
Scope: live read-only inspection of Athena, current SASE source, and short-lived isolated loader/render measurements. No Athena services, agents, or existing TUI processes were stopped or modified.

## Executive conclusion

The suspicion is substantially correct: SASE is the largest controllable consumer of Athena's memory. However, the number of rows in the Agents tab is not, by itself, the main cause.

There are three distinct effects:

1. **Parked agent runners dominate SASE memory.** Athena had 64 active/recent-live agents, including 50 Waiting and 3 Queued agents. The Waiting processes alone held about 16.7 GiB RSS; Waiting plus Queued held about 18.5 GiB. SASE currently represents each parked agent with a heavyweight Python `run_agent_runner.py` process, so pre-run agents scale at roughly hundreds of MiB per node even though they are sleeping.
2. **Two long-lived, stale TUI processes held another 6-7 GiB RSS.** They started on September 15 and September 18 and had not loaded the current checkout's later loader/import improvements. Their anonymous heaps are far larger than a fresh TUI data/render workload, indicating long-lived heap retention or allocator high-water behavior rather than an intrinsically large node model.
3. **Concurrent SASE test jobs were a large transient contributor.** Depending on the sample, pytest parents/workers held roughly 9-21 GiB RSS. Prometheus held another roughly 3.6 GiB and is not a SASE cause.

The strongest denial of the original narrow hypothesis is a controlled measurement on Athena's real data: current code loaded 932 agent rows, built 999 tree options, and peaked at about 195 MiB RSS. Twenty full loader-plus-render replacements of roughly 537 rows peaked at about 250 MiB. Therefore, 1,000 displayed nodes do not inherently require gigabytes. The present machine pressure comes mainly from process-per-waiter execution architecture, plus stale long-lived TUI heaps and concurrent test workloads.

## Live Athena measurements

All measurements were taken on 2026-09-19 in America/New_York. The machine has 62 GiB RAM and 63 GiB swap.

At the first sample:

| Metric | Observation |
|---|---:|
| RAM used / available | 53 GiB / 9.3 GiB |
| Free RAM | 2.3 GiB |
| Swap used | 25 GiB |
| Reclaimable slab | 4.0 GiB |

Later, after several test jobs ended, RAM use fell to 47 GiB and swap use to 18 GiB. This confirms a large transient test component, but it does not remove the persistent SASE issue: the agent runners and TUIs remained very large. `vmstat` still showed swap-in activity during the later sample, and five-minute memory PSI had recently registered full stalls.

### Process attribution

An initial RSS grouping produced:

| Process group | Approximate RSS |
|---|---:|
| 63 `run_agent_runner.py` processes | 19.7 GiB |
| Two SASE TUI processes | 6.3 GiB |
| Concurrent pytest parents/workers | 20.6 GiB |
| SASE service/gateway/axe processes | 1.1 GiB |
| Prometheus and Pushgateway | 3.6 GiB |
| Other processes | 3.2 GiB |

The workload changed during inspection. A later proportional-set-size walk found 60 `run_agent_runner.py` processes at **19.7 GiB PSS** plus **2.8 GiB swap PSS**. Because most of this memory is private anonymous memory, RSS is not merely double-counting shared libraries.

Joining the current `sase agent list -j` status to each live PID made the parked-agent cost explicit:

| Status | Live PIDs | Aggregate RSS | Average RSS |
|---|---:|---:|---:|
| Waiting | 50 | 16.7 GiB | 342 MiB |
| Queued | 3 | 1.8 GiB | 616 MiB |
| Running | 7 | 3.0 GiB | 436 MiB |
| Starting | 1 | 0.9 GiB | 901 MiB |

The configured/effective runner limit reported by the agent listing was 8. That limit constrains admitted execution, not resident pre-run processes: 53 Waiting/Queued agents remained in memory outside the eight-runner execution budget.

Most parked runners were sleeping in `hrtimer_nanosleep`; several were days old. Of 60 runners in one sample, 53 had 250-500 MiB RSS, three exceeded 500 MiB, and three were older than 24 hours. This is idle retained memory, not useful working data.

### TUI processes

The two live TUI processes were:

| PID | Started | Command | Later RSS |
|---:|---|---|---:|
| 1598377 | 2026-09-18 14:03:07 | `python -m sase tui --restart-service` | 4.0 GiB |
| 1880150 | 2026-09-15 14:25:32 | legacy `sase ace -t agents` | 2.8 GiB |

At an earlier point their combined PSS was about 6.24 GiB and their combined swap PSS was about 2.11 GiB. The newer process grew by roughly another 0.5 GiB during this investigation.

`pmap` showed that the newer TUI had 209 anonymous mappings totaling about 4.0 GiB resident, including 37 mappings individually at least 60 MiB resident. The older TUI had 202 anonymous mappings totaling about 2.8 GiB resident, including 23 mappings at least 60 MiB. This shape is consistent with a retained Python/native heap or allocator arenas, not mapped artifact files.

The TUI heap sampler was not enabled in either process, so the exact retained allocation sites cannot be proven from these already-running processes. `py-spy` showed both apps idle and all background worker threads waiting; it did not show active work accounting for their heaps.

## Node-count experiment

I ran isolated processes using the current installed SASE code and Athena's real 197 MiB artifact index.

| Workload | Result | Peak RSS |
|---|---:|---:|
| Bounded loader | 120 rows | 169 MiB |
| Full-history loader | 921 rows | 182 MiB |
| Full loader + tree construction | 932 rows, 999 tree entries | 176 MiB |
| Full loader + real `AgentList` option construction | 932 rows, 999 options | 191 MiB |
| 20 cached loader + option-list replacements | 537 rows / 556 options on final pass | 250 MiB |

The 999 tree entries comprised 932 agent/shell/step rows plus 67 grouping rows. By the stricter project glossary definition, 292 of the 932 rows were top-level Agent Nodes; the rest were other SASE nodes such as family-shell or workflow-step rows. For memory sizing, the rendered 999-option tree is the relevant number.

A further 200-update run over the same 932-row list remained near 183 MiB RSS with a 192 MiB high-water mark while running and then exited normally. This does not replace an hours-long endurance test, but it rules out a simple per-`AgentList.update_list` linear leak in current code.

**Conclusion:** the current node representation and option rendering are compatible with approximately 1,000 nodes on Athena. The live multi-gigabyte TUIs are not evidence that 1,000 nodes inherently cost that much.

## Why the live TUIs do not represent current-code baseline behavior

The newer TUI began at 14:03:07 on September 18. The checkout then landed several relevant changes after it had already imported its code:

- `3962d8819` at 14:09:27: isolate agent row graphs during background refresh.
- `264eedc6c` at 15:53:05: trim the TUI startup import graph.
- `13a8efbb4` at 18:06:08: project compact Agents-list index rows before JSON hydration.

SASE's own TUI guidance notes that editable-install processes keep executing the snapshot imported at startup. The September 15 TUI is older still. A restart is therefore a justified immediate mitigation and a necessary prerequisite for measuring current behavior.

The live newer TUI's slow-load log also shows high churn: 369 slow events over the inspected log window, including 198 full loads and 161 artifact-delta loads. Its largest full-history reconciliation produced 909 rows and took about 49 seconds (45 seconds in disk work); repeated Tier-1 revalidations grew from about 586 to 697 loaded rows. Churn over stale code is a plausible source of heap high-water behavior, but the exact retained sites need `SASE_TUI_HEAP=1` on a newly started process to distinguish live Python objects from native allocator retention.

## Runner architecture is the primary scaling failure

`src/sase/axe/run_agent_runner.py` imports the full runner execution stack before it performs dependency and runner-slot admission. A process then remains alive through dependency, time, hold, bead, hood, and capacity waits. That gives every waiting node a complete Python interpreter and a large imported/runtime heap.

The code already recognizes this issue. Commit `38ac15b07` added `gc.collect()` plus glibc `malloc_trim(0)` at the start of waits and every 60 seconds. Its commit message records an earlier Athena incident in which 63 of 71 agents were Waiting/Queued and retained 31 GiB. The current observation is better but still unacceptable: 50 Waiting agents retain 16.7 GiB despite that mitigation.

The existing tests mock `malloc_trim`; they prove control-flow invocation but do not impose a real RSS bound after a representative bootstrap on the Python 3.14 runtime used by Athena. The runtime reports both pymalloc and mimalloc support. Memory may remain reachable through bootstrap state, or allocator layers may prevent glibc trimming from returning most pages. Regardless of the precise allocator split, the live result proves that trimming a heavyweight parked process is not a sufficient 1,000-node design.

At the observed 342 MiB average, 1,000 Waiting agents would imply roughly 334 GiB RSS. Even an excellent 90% trim would still leave roughly 33 GiB. A process-per-waiter model cannot meet the requested scale robustly.

## Other contributing factors and risks

### Concurrent test fan-out

Multiple `pytest -n 4` and `pytest -n 6` jobs were running from separate SASE workspaces. Their workers were frequently 0.7-1.4 GiB each. They accounted for 20.6 GiB at the first sample and about 9.4 GiB later. This is SASE-associated workload rather than Agents-tab storage, and admission should consider host memory when launching concurrent verification monitors.

### Cache and virtualization limits

Current code has useful bounds: a 512-entry agent render cache, a 128-entry banner cache, an eight-entry artifact-snapshot cache, list-shaped index projection, and a growing viewport prefix. However, the prefix eventually retains and renders all traversed rows; it is not true view virtualization. The per-process `AgentSnapshotCache` also accumulates attempt/retry entries by artifact path without an explicit size bound. Neither caused the isolated 1,000-option process to exceed 200 MiB, but both should be covered by an endurance memory budget.

### Existing benchmark gap

`tests/perf/bench_tui_trace.py` advertises a 1,000-Agent fixture, but the main scenario starts on the Artifacts tab. It only assigns the fixture list directly to `app._agents` in the large-reply branch and does not clearly exercise a full 1,000-row AgentList rebuild through the production loader/apply path. It tests latency, not an RSS ceiling. The isolated measurement above drove `AgentList` directly, but the repository still needs a production-path memory acceptance test.

## Immediate mitigation

These steps can recover memory without changing the data model:

1. Restart both long-lived TUI sessions so they run the current checkout. This should reclaim their existing 6-7 GiB immediately and activate the post-start loader/import fixes. Start one replacement with `SASE_TUI_HEAP=1` and a 60-second sampling interval for attribution.
2. Review and stop/dismiss Waiting and Queued agents that are no longer wanted using SASE lifecycle commands, not raw process kills. Every ten average Waiting runners released should return roughly 3.3 GiB at the observed footprint.
3. Avoid overlapping several full pytest shards on this host while it is already swapping. Verification admission should use a memory budget in addition to a runner-count budget.
4. Treat `max_running_agents` as an execution limit only; it is not currently a memory cap. Until the architecture changes, add an operational cap on total resident pre-run runners or refuse new fan-out when available memory/PSI crosses a threshold.

These are pressure-relief measures, not the final 1,000-node solution.

## Verification required for a durable fix

A regression suite should measure both object retention and process RSS/PSS:

- Build and render at least 1,000 mixed nodes through the production load/apply path, including families, shells, workflows, waits, clans, and grouping banners.
- Run at least 500 full/delta/viewport refresh cycles, force collection, and assert a post-warmup growth ceiling. A reasonable first Athena target is TUI RSS below 500 MiB and less than 50 MiB growth after warmup; current short-lived results suggest this is conservative.
- Record `tracemalloc` live/peak bytes alongside `/proc/self/smaps_rollup`. Rising traced bytes identify retained Python objects; flat traced bytes with rising RSS identifies allocator fragmentation/high-water retention.
- Add a real Linux integration test for `release_idle_memory()` after a representative runner bootstrap. Assert actual RSS reduction; do not only mock `malloc_trim`.
- Test 1,000 durable Waiting/Queued intents with no more than O(1) scheduler processes and no heavyweight runner process before admission.
- Assert that the number of heavyweight runner/provider processes is bounded by the configured admitted capacity, not by the number of visible Waiting nodes.
- Track host `MemAvailable`, swap-in rate, and memory PSI in admission. Fail closed or defer launches before the host enters sustained reclaim.

## Recommended solution

Replace the process-per-waiter design with a **durable, processless admission queue owned by the Rust core/service scheduler**:

1. Launch writes a compact, idempotent launch intent and the visible waiting metadata, then exits. The Agent Node's liveness is derived from durable state, not a sleeping PID.
2. One scheduler watches dependency, time, bead, hood, hold, and runner-capacity transitions for all queued intents. This work belongs in the shared Rust core because CLI, TUI, mobile, and other frontends must agree on it.
3. Only after an intent is eligible and has claimed capacity does the scheduler spawn/exec the heavyweight Python runner or provider process. Recovery after scheduler restart replays durable intents without duplicating launches.
4. As an intermediate step, split `run_agent_runner.py` into a minimal pre-admission launcher with deferred imports, and re-read prompt/runtime state after admission instead of retaining the full bootstrap heap. Validate any `PYTHONMALLOC`/`malloc_trim` tuning empirically, but do not treat allocator tuning as the final design.
5. Keep the current compact index projection and bounded viewport, then move to true row virtualization if catalogs grow substantially beyond 1,000. Add the RSS/endurance gates above before declaring the Agents tab scale target complete.

This design makes 1,000 historical or Waiting Agent Nodes a disk/index problem rather than 1,000 Python processes, while bounding expensive execution to the configured runner capacity. It directly removes Athena's dominant SASE memory cost and is the recommended path to reliable 1,000+ node operation.
