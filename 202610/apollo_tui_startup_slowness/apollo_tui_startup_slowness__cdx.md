# Apollo SASE TUI startup: measured graph work, plugin discovery, and host pressure

Independent research by **cdx**, 2026-10-13. Measurements were taken over SSH to Apollo between approximately 13:06 and 13:20 UTC (09:06–09:20 EDT). No other researcher's report, chat, summary, or findings were consulted.

## Findings

Apollo's startup problem is real, but the available evidence does not support treating it primarily as a shortage of RAM or CPU count. Existing telemetry records **52.42 and 75.79 seconds from mount to Agents readiness** on October 13. The latter startup reports a 72.05-second “disk” stage. However, the same machine can complete the standalone Agents provider load in **3.87 seconds**, including an indexed query and conversion in **0.48 seconds**. “Disk” is a broad application-stage label, not a measurement of time waiting for physical storage.

I found two concrete sources of unnecessary work:

- Hidden Patch relation construction walks **44,321 artifact-link rows**. It runs on the UI thread during deferred startup, and another refresh path builds the same kind of index in a worker. A process-local experiment that skipped Patch relation construction reduced mount-to-Agents-ready time from **18.68 to 10.90 seconds** in one control pair.
- Prompt-catalog construction repeatedly discovers installed plugin metadata while parsing individual macro inputs. One profiled catalog build made **636 calls to `importlib.metadata.entry_points()`** and took **20.78 seconds**. Reusing one plugin input-type registry snapshot reduced the same profiled operation to **2.63 seconds**, with the same **100 assist entries**. This was an isolated catalog experiment, not an end-to-end TUI benchmark.

Both are actionable without increasing the VM size. Host contention is an amplifier: CPU and I/O pressure varied substantially during this investigation, so these single-run effects are candidates for engineering work, not promised p95 improvements. The exact cause of the exceptional 75.79-second run was not captured contemporaneously; the controlled measurements identify reproducible waste, rather than fully accounting for every second of that historical outlier.

## Machine profile

| Signal | Apollo observation | Interpretation |
| --- | --- | --- |
| CPU | 16 online vCPUs; Intel Xeon Platinum 8168 at 2.70 GHz; KVM | Many logical CPUs, but Python execution and UI work can still bottleneck within one process. |
| OS / Python | Ubuntu kernel 6.8.0-146-generic; Python 3.12.3 | Measurements used the installed SASE interpreter, not the system Python for SASE imports. |
| RAM | 31 GiB total; about 11 GiB used; about 20 GiB available; no swap | No observed memory shortage; memory PSI stayed effectively zero. |
| Disk | `/dev/vda1`, ext4; 193 GiB total, 142 GiB used, 51 GiB free; 74% full | `~/.sase` is a real directory on this local filesystem, not an observed network mount or symlink. |
| Load average, first snapshot | 16.49 / 13.82 / 10.55 | High enough to investigate, but not sufficient evidence of saturated CPUs. |
| Seven one-second `vmstat` intervals | 5–9 runnable tasks; CPU idle 48–63%; I/O wait 2–3%; steal rounded to 0 | Substantial spare CPU capacity during this particular window. Excludes `vmstat`'s first, since-boot row. |
| Four one-second `iostat` intervals | CPU idle 57.9–63.6%; steal 0–0.06%; vda utilization 37–42%; write await 0.67–4.02 ms | No sustained device saturation in this window. Roughly 603–858 writes/s and 353–445 flushes/s indicate material background write activity. Device utilization alone is not a complete storage-capacity diagnosis. |
| Initial PSI | CPU `some avg10=1.23`, `avg60=7.72`; memory approximately 0; I/O `some avg10=3.74`, `full avg10=3.19` | Some resource stalls, rather than a uniformly quiet host. |
| Later PSI, 13:19 UTC | CPU `some avg10=14.36`; I/O `some avg10=22.96`, `full avg10=14.84`; memory approximately 0 | Pressure increased later. Do not generalize the earlier idle-CPU observation to all startups. |
| TUI cgroup and ancestors | `cpu.max=max 100000`; `nr_throttled=0`; `throttled_usec=0` | No observed cgroup CPU quota throttling of the user's TUI. |
| Existing TUI PID 3192631 | About 1.2 GiB RSS, zero swap, 30 threads | A large process, but not evidence of current RAM exhaustion. |
| Four-second thread CPU sample | TUI averaged 98.5% of one CPU; main thread 13.2%; two worker threads accounted for most of the remainder | Background work matters. Profiling just the event-loop thread misses much of the process's CPU use. |

Other active processes included `rustc`, two `mypy` processes near a core each, a job-wait process near a core, and SASE/Python workers. I did not pause or kill any of those processes, change scheduling policy, install packages, clear caches, or change Apollo's production configuration.

PSI measures time during which tasks are stalled on a resource; its `some` and `full` fields distinguish partial from broader stalls. It is more directly useful for this diagnosis than inferring latency from load average alone. See the [Linux kernel PSI documentation](https://docs.kernel.org/accounting/psi.html).

Apollo reported installed versions: **sase 0.17.1**, **sase-core-rs 0.39.0**, **Textual 8.2.8**, **Rich 15.0.0**, and **pyinstrument 5.1.3**. SASE and its Rust package reported editable source locations through runtime metadata. I attempted the audited remote repository-open workflow; it failed because Apollo's project record has no `WORKSPACE_DIR`, including with an explicit workspace selector. I did not bypass it to directly read that remote checkout or its git history. Code inspection used the authorized local SASE checkout at `010185b0c47e1c9c70fd90e4b21149a4fb445753` and the opened sase-core checkout at `2fc3d7754a3585180d0d2d7bd7ca1e034de31cdc`. Runtime profiles independently identify the relevant Apollo functions and line numbers. Matching release strings do not establish identical source revisions.

## Existing startup evidence

Before launching my controlled captures, Apollo had 492 startup records. The latest five October 13 records were:

| Record timestamp, UTC | Visible ready after mount | All surfaces ready after mount | App module import | Visible rows | Index records |
| --- | ---: | ---: | ---: | ---: | ---: |
| 08:12:04 | 8.20 s | 9.38 s | 4.08 s | 36 | 235 |
| 08:21:42 | 8.82 s | 9.82 s | 4.61 s | 36 | 236 |
| 10:16:03 | 11.79 s | 11.79 s | 3.97 s | 39 | 243 |
| 11:55:50 | 52.42 s | 52.42 s | 5.12 s | 42 | 238 |
| 13:02:12 | 75.79 s | 75.79 s | 5.29 s | 45 | 268 |

These timestamps are record emission times, not command invocation times. The October 13 median visible-ready time was 11.79 seconds across these five records. The much worse last two are real tail latency, not representative of every launch. For context, the October 10–12 daily medians were 10.80, 4.35, and 10.26 seconds, across 12, 7, and 7 records respectively; October 10 already had an 89.22-second outlier.

For PID 3192631, app instance `6caf1c57`, the 13:02 startup's matching loader row was:

```text
source=startup, load_kind=full, raw agents=955
stages_seconds: disk=72.047145, prep=0.707073, apply=0.640655
```

It subsequently recorded a 69.04-second revalidation and a 54.42-second delta load. Thus the issue extends beyond initial screen composition. In contrast, first paint for that startup arrived 0.812 seconds after mount, and the Services surface settled earlier than Agents. A drawn loading screen is not the same as an interactive Agents roster.

The telemetry anchor needs care. `process_start_to_on_mount_seconds` and `agents_ready_seconds` are based on an App-initialization timestamp, despite their names. CLI and app-import splits use separate clocks. Repeated app instances in one long-lived PID also produced an implausible historical `interpreter_cli_import_seconds` value of 237,028 seconds. I excluded that number from conclusions. Do not sum medians, overlap construction/mount stages, or read the historical “process start” field as the complete shell-command-to-ready time.

Source references: [startup telemetry](https://github.com/sase-org/sase/blob/010185b0c47e1c9c70fd90e4b21149a4fb445753/src/sase/ace/tui/actions/_startup_telemetry.py), [startup clocks](https://github.com/sase-org/sase/blob/010185b0c47e1c9c70fd90e4b21149a4fb445753/src/sase/ace/tui/util/startup_clock.py), and [runtime-state initialization](https://github.com/sase-org/sase/blob/010185b0c47e1c9c70fd90e4b21149a4fb445753/src/sase/ace/tui/actions/_state_init_runtime.py).

## Controlled profiling

### The indexed provider is much faster in isolation

Using `/home/bryan/.local/share/uv/tools/sase/bin/python`, with local repository config disabled as it is for the TUI, I profiled both the tiered loader and the actual provider wrapper:

| Operation | Wall time | Detail |
| --- | ---: | --- |
| `load_tiered_agents(index_freshness='cached')` | 3.374 s | Separate module import took 1.844 s. |
| `load_agents_from_disk_with_state(load_dismissed_agents(), source='startup')` | 3.873 s | 962 raw agents, 270 index records, Tier 1, artifact index, no index error or repair recommendation. |
| Indexed query plus Python conversion in the latter profile | 0.480 s cumulative | Native Rust query itself approximately 0.172 s. |
| Status normalization | 1.090 s cumulative | Includes status overrides and identity lookup. |
| First identity snapshot | 0.727 s cumulative | Approximately 0.543 s in repository inventory discovery. |

These are instrumented, fresh-process observations against the live archive, not a hermetic benchmark. They show that the entire path is capable of completing in seconds and that the existing index is usable. They do not prove that an index lock or storage stall never occurs.

The remembered Agents query was empty, with a valid `agents-live` snapshot; there was no persisted active agent sub-tab. A complex saved-query fallback is therefore not the demonstrated explanation for these captures.

### External all-thread startup sampling

I launched disposable TUIs in a 120×40 pseudoterminal using `sase tui -x -r 0`. `-x` suppressed service-host autostart; `-r 0` disabled periodic auto-refresh in the experimental TUI, while watchers and startup work remained active. Each experiment had a unique temporary directory and its own trace, startup, loader, and watchdog paths. Supervisors drained terminal output, sent `q`, waited, and terminated only their own process group when needed.

An initial run combined `py-spy` with `--profile`. That was a poor timing baseline: 298 of 2,053 weighted active-thread samples included pyinstrument frames, and its stack sampler appeared in watchdog stacks. I retained it for method diagnostics, then repeated without pyinstrument. Neither sampler capture reached startup completion within its bounded observation window. Their absence of a completed startup row is censored evidence, not a precise startup duration.

The py-spy-only capture collected 2,533 weighted active-thread samples. Inclusive sample counts overlapped and are not wall-clock percentages:

| Attribution | Samples or completed trace |
| --- | --- |
| Imports | 690 inclusive samples |
| Patch relation construction | 436 inclusive samples; 7.131- and 7.757-second completed relation spans |
| CSS processing | 272 inclusive samples |
| Agents provider load | 222 inclusive samples |
| Repository inventory | 150 inclusive samples |
| Agents index query | 21 inclusive samples; 0.577-second completed index span |
| Agents decode | 7.518-second completed span; 1,249 decoded rows including workflow steps |

Watchdog stacks caught the main thread in `artifact_link_edges`, `_target_for_ref`, and Rust lookup-key bindings during hidden Patch work. Loader-thread stacks caught identity discovery traversing the full repository inventory and repeatedly canonicalizing workspace paths. Prompt-catalog stacks caught plugin input-type discovery. These observations explain how an apparently background “disk” stage can stretch while unrelated work contends for execution.

Python 3.12 threads share the GIL, so moving Python-heavy catalog and graph loops to threads does not provide unconstrained parallel execution. Actual disk waits, executor queue delays, GIL contention, and UI scheduling delays can coexist. The profiles establish the work being performed; they do not isolate the exact proportion of each wait. See [Python's threading documentation](https://docs.python.org/3.12/library/threading.html).

An attempted read-only attachment to the existing user TUI with `py-spy dump` was denied by ptrace permissions. I did not elevate privileges or relax host security; child-process sampling succeeded.

### Patch graph experiment

A standalone profiled build found **44,321 link rows**, across the global snapshot, for **284 Patches**. It took **5.359 seconds** including snapshot loading and patch discovery. The relation projection itself consumed about 4.407 cumulative seconds. It made:

```text
88,642 endpoint target-resolution calls
43,151 artifact_row_ref_lookup_keys Rust binding calls
43,085 artifact_link_ref_parts Rust binding calls
```

The graph cache stores aggregate input rows, but it does not eliminate their repeated endpoint projection for a pane. Most input rows describe unrelated agents, outputs, and other artifacts. Python converts lookup inputs and outputs and resolves Rust bindings repeatedly for each endpoint before checking whether the edge touches a known Patch.

The startup deferred-state path calls `_apply_patches` on the UI thread; `_apply_patches` immediately builds this relation index. The regular asynchronous Patch reload already has a prepared worker result carrying a relation index. The sampled session exhibited both paths. The fix should route startup through prepared results and defer unnecessary hidden-pane graph work, preserving the graph for when the user opens it.

I then ran two instrumented TUIs without either sampling profiler. Both used the same App pre-import, terminal size, settings, trace paths, and readiness markers. One used the real graph builder; in the other, only that builder returned `None` for the lifetime of that disposable process.

| Metric | Control, real graph | Graph skipped |
| --- | ---: | ---: |
| App import marker | 5.173 s | 4.833 s |
| First paint from wrapper start | 9.500 s | 9.280 s |
| Agents ready from wrapper start | 27.331 s | 19.309 s |
| Visible ready after mount | 18.679 s | 10.899 s |
| Loader disk stage | 8.152 s | 3.274 s |
| Preparation | 1.630 s | 1.418 s |
| Display apply | 3.088 s | 4.602 s |
| Index records / visible rows | 273 / 45 | 273 / 45 |
| Raw loaded agents | 969 | 969 |

The control's main-thread graph call took 3.322 seconds; its concurrent initial identity discovery took 3.903 seconds. With graph work skipped, identity discovery took 0.459 seconds. That pattern is consistent with interference extending more than the graph's own duration. The measured post-mount reduction was **7.780 seconds, or 41.7%**, with equivalent row counts.

This is one unrandomized pair on a changing shared host. It is stronger evidence than a hot stack alone, but cannot justify promising an eight-second saving on every launch or claiming it explains the historical 75-second outlier. Graph skipping was an experimental ablation, not a production feature removal.

Source references: [deferred startup state load](https://github.com/sase-org/sase/blob/010185b0c47e1c9c70fd90e4b21149a4fb445753/src/sase/ace/tui/actions/_startup_loads_index.py), [Patch preparation and apply paths](https://github.com/sase-org/sase/blob/010185b0c47e1c9c70fd90e4b21149a4fb445753/src/sase/ace/tui/actions/patch/_loading.py), [link-edge projection](https://github.com/sase-org/sase/blob/010185b0c47e1c9c70fd90e4b21149a4fb445753/src/sase/ace/tui/relations/artifact_links.py), and [row-resolution adapter](https://github.com/sase-org/sase/blob/010185b0c47e1c9c70fd90e4b21149a4fb445753/src/sase/core/artifact_row_resolution_facade.py).

### Plugin registry experiment

`get_plugin_input_type_registry()` does cache the decoded registry. However, it computes its discovery snapshot **before checking that cache**. Every parsed input therefore rediscovers manifest files and known plugin distributions. Each discovery enumerates both the canonical and legacy entry-point groups. Catalog construction also loads macros for snippets and again for assist entries.

With cProfile enabled for both catalog builds:

| Metric | Existing registry behavior | One reused registry snapshot |
| --- | ---: | ---: |
| Catalog wall time | 20.783 s | 2.630 s |
| Python function calls | 17.70 million | 2.12 million |
| `entry_points()` calls | 636 | 34 |
| Cumulative time in `entry_points()` | 18.175 s | 0.953 s |
| Assist entries produced | 100 | 100 |

Obtaining the reused registry snapshot took an additional **0.156 seconds**, before the second timed catalog build. Including that cost, the experiment still reduced this instrumented work by approximately 86.6%. It retained the original registry data; no plugin was disabled. Remaining enumeration comes from other macro-discovery operations and should also be shared within a catalog generation.

This demonstrates a repeated-discovery problem, not an estimate of 18 seconds of end-to-end startup savings. cProfile adds overhead, particularly to Python-heavy code, and a production cache must preserve invalidation when manifest contents, installed plugins, or disable settings change. Equal entry counts are a useful sanity check, not a complete content-equivalence test. See the [Python 3.12 profiling documentation](https://docs.python.org/3.12/library/profile.html).

Source references: [registry cache](https://github.com/sase-org/sase/blob/010185b0c47e1c9c70fd90e4b21149a4fb445753/src/sase/macro/plugin_input_types.py), [entry-point discovery](https://github.com/sase-org/sase/blob/010185b0c47e1c9c70fd90e4b21149a4fb445753/src/sase/main/plugin_discovery.py), [per-input resolution](https://github.com/sase-org/sase/blob/010185b0c47e1c9c70fd90e4b21149a4fb445753/src/sase/macro/_loader_parsing_inputs.py), and [prompt catalog](https://github.com/sase-org/sase/blob/010185b0c47e1c9c70fd90e4b21149a4fb445753/src/sase/ace/tui/prompt_catalog.py).

### Imports and startup scheduling

A fresh `python -X importtime -c 'from sase.ace.tui import AceApp'` took **7.056 seconds** under the host's then-current load. The largest measured cumulative import subtree was `actions.agents._core` at **4.096 seconds**, with `_agent_enter_action` at 2.141 seconds and `_metadata_search` at 1.315 seconds. Those chains pulled in gate/notification models and metadata/pager-related functionality before the user requested those actions. These nested cumulative times must not be added together.

Separately, normal startup telemetry shows roughly 4–5 seconds importing the App module, while construction itself is around 0.4–0.7 seconds and the measured `compose()` generator is around 0.02–0.03 seconds. The Textual mount/style/layout interval is still several seconds. A small `compose_seconds` does not mean constructing and styling the whole screen is free.

The code prioritizes the visible surface initially, but after **three seconds** the fallback releases hidden surfaces and maintenance even if Agents is not ready. That launches Patch loading, prompt-catalog warming, and other work into the same startup interval. It is a plausible mechanism for amplification on a slow host. Deferral should have an execution budget and a dependency boundary, not merely a short timer before releasing every expensive job.

Source references: [startup release orchestration](https://github.com/sase-org/sase/blob/010185b0c47e1c9c70fd90e4b21149a4fb445753/src/sase/ace/tui/actions/_startup_loads_core.py), [deferred maintenance](https://github.com/sase-org/sase/blob/010185b0c47e1c9c70fd90e4b21149a4fb445753/src/sase/ace/tui/actions/_startup_loads_maintenance.py), and [Agents disk-stage boundaries](https://github.com/sase-org/sase/blob/010185b0c47e1c9c70fd90e4b21149a4fb445753/src/sase/ace/tui/actions/agents/_loading_disk_full.py). The [Python command-line documentation](https://docs.python.org/3.12/using/cmdline.html#cmdoption-X) describes `-X importtime` and its self/cumulative fields.

## Reproduction and validation

The raw controlled captures remain on Apollo in these uniquely created temporary directories; they may eventually be cleaned up. The decisive results above are embedded in this durable report:

```text
/tmp/sase-startup-cdx-vm931_ux             # py-spy + pyinstrument, overhead diagnostic
/tmp/sase-startup-cdx-plain-nijma620       # py-spy-only startup, trace and watchdog
/tmp/sase-startup-cdx-ablation-ge_dukcj    # process-local graph skip, markers and telemetry
/tmp/sase-startup-cdx-control-f7rfx80b     # real graph control, markers and telemetry
```

The files contain only my captures. No peer report or peer-generated profile was opened. Production source/configuration was not edited. The disposable TUIs can perform their ordinary startup and quit bookkeeping; these were observations against the real SASE state, not fully hermetic tests. My experiment process groups were cleaned up.

Useful short host measurements:

```bash
ssh apollo 'vmstat 1 8'
ssh apollo 'iostat -xz 1 5'
ssh apollo 'cat /proc/pressure/cpu /proc/pressure/memory /proc/pressure/io'
ssh apollo 'pidstat -u -t -p <tui-pid> 1 4'
```

For code-side attribution, use the installed interpreter and profile the exact provider wrapper, not only the lower-level scanner:

```python
from sase.config.core import set_include_local_config
set_include_local_config(False)
from sase.ace.dismissed_agents import load_dismissed_agents
from sase.ace.tui.actions.agents._loading_helpers import load_agents_from_disk_with_state
# Surround this call with perf_counter and, separately, cProfile:
result = load_agents_from_disk_with_state(load_dismissed_agents(), source="startup")
```

For a traced terminal launch, give every process separate output paths:

```bash
SASE_TUI_TRACE=1 SASE_TUI_TRACE_PATH=<unique-dir>/trace.jsonl \
SASE_TUI_STARTUP_PATH=<unique-dir>/startup.jsonl \
SASE_TUI_AGENT_LOADS_PATH=<unique-dir>/loads.jsonl \
SASE_TUI_LOADER_LOG_THRESHOLD_SECONDS=0.05 \
/home/bryan/.local/bin/sase tui -x -r 0
```

Record from shell command start to first paint and first interactive roster, then repeat with ordinary service and refresh settings. Use a child launched by py-spy when attaching is denied. Avoid pyinstrument in the baseline timing run; if used for attribution, pair it with an unprofiled measurement. The repository also supplies `tests/perf/capture_tui_startup.py`, but its default suite and “quiet” load threshold should not be treated as capacity-normalized comparisons across machines.

Before accepting any implementation, obtain several quiet and busy runs on the same installed revision, terminal geometry, saved query, and archive. Compare distributions of first paint, visible-ready, and all-surfaces-ready independently. Record CPU/I/O PSI and executor submit/start/finish timestamps alongside them. Validate plugin content and invalidation, graph edges after opening Artifacts, the visible roster, and input responsiveness. Shared graph/domain optimizations belong in **sase-core**, with Python/TUI scheduling and thin adapters here; update the Rust binding and SASE's core revision pin together when needed.

## Ranked changes to consider

1. **Defer hidden Patch relation construction and remove its UI-thread startup build.** This has the strongest directly measured TUI benefit: 18.68 → 10.90 seconds after mount in one control pair. Route startup through prepared worker results, retain the result for reuse, and build graph data when its pane becomes visible or after Agents readiness. Batch endpoint resolution/filtering in sase-core rather than making tens of thousands of per-endpoint Python/Rust calls. Preserve relations when the user opens the pane. Verify both startup latency and graph correctness.

2. **Discover plugin metadata once per catalog generation, before resolving individual macro inputs.** The existing registry cache pays discovery cost before every cache lookup. Sharing the registry snapshot cut 636 entry-point scans to 34 and an instrumented catalog build from 20.78 to 2.63 seconds, plus 0.16 seconds to obtain the snapshot. Share canonical/legacy enumeration and macro inventories too. Keep manifest/config/plugin invalidation explicit; do not permanently disable plugins or freeze stale data. This likely helps the CLI and other macro consumers as well as the TUI.

3. **Give startup maintenance a budget and prioritize the visible roster until it is ready.** The three-second fallback currently releases expensive hidden loading and catalog warming into a slow Agents startup. Defer nonurgent work until visible-ready or an idle window; serialize/coalesce heavy warmups and make tab-switch demand override deferral. A fallback can maintain a usable loading surface without scheduling every corpus build at once. Measure executor waits and input latency, and ensure hidden surfaces eventually load.

4. **Use a lightweight identity/sidecar discovery path instead of the full repository clone inventory.** `AgentIdentitySnapshot.current()` reaches `resolve_sync_targets()` and constructs the repository/workspace clone matrix just to identify agents-sidecar roots. This cost was about 0.73 seconds alone and 3.90 seconds during the real-graph control. Resolve only the required machine-level roots, reuse an immutable snapshot across the load, coalesce concurrent cold misses, and invalidate on relevant identity/project changes. Retain explicit owner semantics; do not guess identities or skip configured namespaces.

5. **Reduce eager imports and mount only the widgets needed for the initial view.** The App import commonly costs 4–5 seconds, and one fresh import measured 7.06 seconds. Move action-only imports such as enter/pager/gate handling to their invocation paths, keep public facades thin, and delay hidden-pane/widget construction. Distinguish the cheap `compose()` generator from the more expensive Textual mount/style/layout interval. After the prior fixes, investigate CSS updates, deck application, clan/runtime projection, and detail rendering, which also appeared in stalls; preserve immediate highlight updates.

6. **Make startup measurements reflect command-to-interactive time and identify worker waits.** Correct misleading historical clock names/anchors, emit visible-ready even if a hidden surface never settles, attach actual code revision to captures, and split executor queue time, provider/index time, normalization, and UI apply time. This does not itself save seconds, but prevents optimizing storage for a Python scheduling problem and makes regressions actionable. Keep expensive revision lookup and log writes off the startup path.

7. **Reduce competing batch work on Apollo using measured CPU and I/O pressure.** Profile and bound build/test concurrency and persistent high-CPU wait/poll workers before tuning globally. Prefer pressure-aware admission and batch scheduling that reserves responsiveness for the interactive TUI. The later I/O PSI spike warrants observing the owning writers during a slow launch. Initial memory availability, negligible steal, and unthrottled TUI cgroups do not support adding swap, clearing page caches, or changing CPU quota as the first remedy. Avoid killing useful work just because load average is high.

8. **Consider faster hardware or different placement only after comparable software and quiet-host measurements.** If command-to-interactive latency remains unacceptable with repeated discovery and hidden graph work removed, compare single-thread CPU performance and local storage latency on an existing alternative host using the same revision/data. Extra vCPUs alone cannot fix Python serialization or an O(global-links) loop on the UI thread. Current observations do not establish a need for more RAM; a purchasing decision needs a controlled before/after benchmark rather than this session's load average.
