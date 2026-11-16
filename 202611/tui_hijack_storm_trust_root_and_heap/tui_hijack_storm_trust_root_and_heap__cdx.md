# SASE TUI performance: fix config ownership first, then bound retained work

Independent research by **cdx**, 2026-11-16. No other report, transcript, summary, or findings from this research swarm were consulted. This investigation used the local source tree, existing machine telemetry, small isolated Python profiling experiments, and primary documentation. It made no production source changes and did not restart or modify the running TUI.

The strongest immediate opportunity is a specific startup regression in **canonical config ownership and repeated trust-resolution work**. Fix that shared cause first. Then reduce the large live object graphs and repeated roster preparation behind sustained-session stalls. Retain Textual, the existing incremental refresh architecture, and Rust as the shared domain backend. There is enough instrumentation to start implementing the first fix now.

**Evidence and scope.** The inspected SASE revision was `73718c77e1` and the opened Rust core revision/pin was `e9b1cf04158d1168e43fb150dc6d7a62c14a959c`. Recent real startup rows identified imported revision `8254254e2f`; the older session used for the four-hour stall analysis identified `082f2bc705`. These are distinct evidence cohorts, not an assertion that every measurement came from an identical checkout.

The installed interpreter reported Python **3.14.7**, Textual **8.2.8**, and `sase-core-rs` **0.44.2**. The workspace virtualenv instead had Textual **8.0.1** and a same-version core wheel missing `project_local_commands`. I discarded that environment as an authoritative performance comparison and repeated the constructor profile with the installed interpreter, importing this workspace's source through `PYTHONPATH`. Version strings alone are insufficient to establish binding compatibility. No package installation was performed.

Measurements below distinguish observed costs, experimentally isolated causes, and remaining hypotheses. Historical observations are not a controlled before/after benchmark: host load, data, query, and versions varied. Slow-loader logs are threshold-selected and must not be read as distributions of all loads. A constructor-only experiment does not establish terminal first-paint or navigation performance.

**The startup regression is concentrated in construction.** Existing `~/.sase/logs/tui_startup.jsonl` contained these Agents-startup cohorts, grouped by UTC date:

| UTC date | Startup rows | Median app construction | Median app-module import | Median `agents_ready_seconds` |
|---|---:|---:|---:|---:|
| 2026-10-25 | 4 | 0.715 s | 2.407 s | 6.342 s |
| 2026-11-01 | 9 | 0.803 s | 2.859 s | 7.819 s |
| 2026-11-08 | 7 | 0.902 s | 2.098 s | 9.530 s |
| 2026-11-14 | 5 | 5.016 s | 1.676 s | 11.340 s |
| 2026-11-15 | 8 | 5.445 s | 2.077 s | 11.146 s |
| 2026-11-16, captured by this investigation | 3 | 5.252 s | 2.246 s | 11.617 s |

The sharp transition is visible on November 12: revision `671ff5bde0` recorded construction of 1.034 s at 10:05:40 UTC, while `ea4121387b` recorded 6.205 s at 10:33:18 UTC. Host load1 was similar, 19.46 versus 18.64. That revision interval introduced local-command trust adapters and enforcement, including `021cd73021` and `ea4121387b`. This temporal correlation directed the profiling; the experiments below provide stronger attribution.

Read these fields with their actual anchors. Despite its name, `process_start_to_on_mount_seconds` starts at the app's legacy initialization stamp; it excludes earlier interpreter/CLI and app-module imports. `agents_ready_seconds` uses that same legacy anchor. `visible_ready_seconds` starts at `on_mount`. `app_construct_seconds` overlaps the legacy pre-mount interval. Do not add all these values together or present `agents_ready_seconds` as complete launch-to-interactive time. The implementation in [startup_clock.py](https://github.com/sase-org/sase/blob/73718c77e1/src/sase/ace/tui/util/startup_clock.py) and [startup telemetry](https://github.com/sase-org/sase/blob/73718c77e1/src/sase/ace/tui/actions/_startup_telemetry.py) is authoritative; some earlier prose in the runbook describes superseded stopwatch behavior.

The latest sampled startup already used the Tier 1 artifact index, with 300 index rows, zero pre-ready Patch relation-index builds, zero pre-release auto-refresh ticks, and release reason `visible_ready`. Its mount-to-first-paint interval was 0.224 s. Thus this evidence does not support blaming initial layout, an archive-wide startup scan, or premature sanity refreshes for the new construction cliff.

**A verified call chain explains most of that cliff.** Profiling `AceApp(auto_start_axe=False)` with `cProfile`, after disabling local config as the actual CLI does, produced:

| Installed-runtime constructor profile | Observed result |
|---|---:|
| Constructor wall time | 5.973 s |
| `build_app_bindings` cumulative time | 5.263 s |
| `resolve_artifacts_subtabs` cumulative time | 5.248 s |
| Project provider loads | 10 |
| `merge_config_sources` calls | 121 |
| `_project_identity` cumulative time | 3.288 s |
| Rust `axe_config_compose` cumulative time | 2.544 s over 121 calls |

Cumulative times overlap and must not be summed. The expensive route is:

```text
AceApp.__init__
  → init_late_startup_state
  → build_app_bindings
  → resolve_artifacts_subtabs (cold cache)
  → load_project_provider_records
  → per-project merged config / trust evaluation
  → project identity fallback
  → per-project config merges again
```

[Keybinding construction](https://github.com/sase-org/sase/blob/73718c77e1/src/sase/ace/tui/keymaps/bindings.py) eagerly discovers provider tabs to generate numbered shortcuts. [The tab registry](https://github.com/sase-org/sase/blob/73718c77e1/src/sase/ace/tui/artifact_tabs.py) has a useful stale-while-revalidate path, but its first miss is synchronous. [Provider discovery](https://github.com/sase-org/sase/blob/73718c77e1/src/sase/ace/tui/_artifact_tab_discovery.py) resolves every project's configuration. Turning off the TUI's own local config does not eliminate these explicit project-local config resolutions.

There is a concrete ownership defect in that route. For a canonical `checkout/sase/sase.yml`, [`_checkout_root_for_local_path`](https://github.com/sase-org/sase/blob/73718c77e1/src/sase/config/local_trust_enforcement.py) starts discovery at `checkout/sase`. [`discover_project_root`](https://github.com/sase-org/sase/blob/73718c77e1/src/sase/content_layout.py) accepts a directory containing `sase.yml` as a project root. It therefore returns the content directory itself. The canonical-layout fallback in `_checkout_root_for_local_path` never gets a chance to use the grandparent.

A read-only reproduction against this checkout returned:

```text
config_relative: sase/sase.yml
 detected_root_relative: sase
 checkout_root_matches: False
```

[`_project_identity`](https://github.com/sase-org/sase/blob/73718c77e1/src/sase/config/local_trust_management.py) cannot match that directory against the registered primary checkout. It falls back to inspecting workspace registries across projects, building their merged configs along the way. The nested evaluation guard prevents infinite trust recursion, but does not prevent the repeated merge/normalization work. With ten provider projects, the observed call count has a roughly quadratic component.

I ran two in-memory experiments, without editing source or trust records:

| Experiment | Result | What it establishes |
|---|---|---|
| Replace only numbered Artifacts binding generation with an empty list | Constructor 0.403 s, unprofiled | That constructor dependency contains most of the work; this is not a functional proposed patch |
| For canonical config files whose grandparent has `.git`, return that grandparent from the ownership helper; retain normal trust evaluation | Profiled constructor 1.902 s; 21 merges instead of 121; ten corrected paths | Correct ownership avoids most repeated work without disabling trust evaluation |

The second experiment reduced the profiled construction sample by about **68%**, roughly **4.1 seconds**. These are single-sample component experiments under changing host load, not a promised end-to-end speedup. The narrow predicate used for experimentation is not a production-ready identity resolver.

There are two important implementation traps:

1. Deferring just the numbered keybindings moves the work to [`ArtifactsView.__init__`](https://github.com/sase-org/sase/blob/73718c77e1/src/sase/ace/tui/widgets/artifacts/view.py), which also calls `resolve_artifacts_subtabs` during composition, including when the view is hidden.
2. Moving all provider work out of composition can still shift the cost to the first Agents load. A fresh-process bounded-loader profile returned 100 agents from 143 index records in 6.762 s. Index time was only 0.174 s, decoding 0.987 s, but normalization/provider time was 5.493 s. The latter went through `AgentIdentitySnapshot.current → _configured_agents_sidecar_paths → resolve_sync_targets → collect_repo_inventory →` the same project config/trust path. [Owner discovery](https://github.com/sase-org/sase/blob/73718c77e1/src/sase/core/agent_identity_facade.py) and provider discovery need a shared efficient answer.

After the ownership experiment's constructor had warmed that process, a subsequent bounded load took 1.727 s: index 0.420 s, decode 0.530 s, provider 0.772 s. Because it was warm and unprofiled, that is not a clean speedup comparison with the separate cold loader profile. It does demonstrate why the complete startup sequence, including shared-cache warming, must be measured.

The safest first change is to resolve config ownership consistently for the trust CLI and enforcement, preserve the distinction between canonical and legacy layouts, and use one validated project/workspace inventory per operation. The CLI's `_requested_checkout` also uses `discover_project_root`; correcting only enforcement risks binding acknowledgments and runtime evaluation to different identities. Cover primary and numbered workspaces, unregistered checkouts, symlinked paths, a repository actually named `sase`, canonical/legacy ambiguity, and config-path versus checkout-path invocation. Reuse trust decisions only when identity, logical config path, policy version, command-bearing content, lower-layer inputs, and acknowledgment state still match. A changed identity must not silently inherit the old acknowledgment.

Shared identity/config behavior belongs in `sase_core` with thin Python adapters. Update bindings and SASE's core revision pin if a new core API is introduced. A small correctness repair plus operation-scoped inventory reuse is safer than broad persistent caching of trust results or disabling the trust feature.

**Steady-state sluggishness has a separate, substantial memory and allocation component.** I ran the existing freeze report against a fixed four-hour window of the older long-running session:

```bash
python tools/tui_freeze_report \
  --since '2026-11-16T06:45:00Z' \
  --until '2026-11-16T10:45:00Z' \
  --instance 8c4f728d
```

Its output included:

| Signal | Four-hour result |
|---|---:|
| Watchdog loop-frozen time | 566.732 s, **3.94%** of the window |
| Loop episodes | 143 |
| Median / p90 / maximum episode duration | 3.960 / 4.394 / 4.845 s |
| Idle full-GC pauses | 136 |
| Idle full-GC p50 / p95 / maximum | 3.090 / 3.646 / 3.918 s |
| RSS | Approximately 4.0 → 4.2 GiB |
| Swap | Approximately 600 → 484 MiB |
| Slow full-loader records | 156, or 39 per hour |
| Index stage in those records | 148 below 1 s; 7 between 1 and 5 s; 1 missing |

This is elapsed-session exposure, including idle periods; it is not a measured fraction of the user's keystrokes delayed. Watchdog lateness can also reflect GC, GIL contention, scheduling, or paging, so the captured Python stack is not by itself proof that its last frame caused the full pause. The recent GC duty-cycle fix (`bdf8ae1590`, November 12) predates this session: its presence did not remove multi-second pauses.

Across the retained slow-loader logs from November 14 onward for PID 88182, 836 full-load records with stages had these medians/p95s: disk 2.565/6.496 s, decode 1.758/5.209 s, preparation 0.966/3.155 s, UI apply 0.244/0.467 s. For 231 staged artifact-delta records, disk was 0.275/2.381 s, preparation 2.425/5.524 s, apply 0.325/0.958 s. These are **slow-path samples only**. They show that a small disk delta does not guarantee cheap preparation or application.

The loader's stage named `decode` is broader than JSON parsing: [`_load_agents_from_all_sources`](https://github.com/sase-org/sase/blob/73718c77e1/src/sase/ace/tui/models/agent_loader.py) combines project claims, artifact records, Patch fields, and enrichment. For example, completed-agent construction resolves instruction-bundle files and commit metadata through [`_done_common.py`](https://github.com/sase-org/sase/blob/73718c77e1/src/sase/ace/tui/models/_loaders/_done_common.py). Profile this stage before attributing it to SQLite or PyO3 serialization.

A newer session, `9976747c` / PID 2180945, supplied a more severe memory observation: its heartbeat around 323 s uptime reported **35.14 GB RSS**, and around 624 s reported **34.83 GB RSS plus 12.38 GB swap**, with a 50.63 s full collection. The process had `SASE_TUI_PERF=1` and `SASE_TUI_GC_CENSUS=1`; no `SASE_TUI_HEAP` flag was present in the inspected environment. This cohort is separate from the four-hour baseline and the active census changes its performance characteristics.

The existing census at `ts=1794827160.6152658` counted 8,125,371 tracked survivors, including 3,961,252 lists, 2,362,039 dicts, **207,837 `AgentArtifactRecordWire` objects**, 207,522 `AgentMetaWire` objects, and 402,220 paths. The census itself lasted 11.45 s. That is evidence of a large surviving Python object graph at that instant. It does not prove a leak, identify the retaining owner, or establish that those records all belong to the visible Agents roster. They may include simultaneous background scans, catalogs, caches, and temporary in-flight results. The census does not account for every allocation or frozen object.

My inference is that **avoiding large hydration and reconstruction is a higher-value durable approach than further GC tuning alone**. A fixed-count cache can still hold enormous snapshots. The existing artifact snapshot cache caps itself at eight entries, runtime aggregation caches already have entry caps, and retry/attempt caches use different retention rules. Audit retained bytes/rows and lifetimes, rather than adding another generic cache. Keep history in the persistent core index; keep compact active/query-window row projections in the TUI; hydrate selected details on demand; discard superseded generations; and bound concurrent full-history work. Preserve query completeness and history availability explicitly instead of pretending a bounded result is complete.

Useful first ownership suspects are full-history reconciliation, raw artifact snapshots retained through pending workers, provider/sidecar catalog warming, and duplicate roster/detail representations. The current evidence does not justify selecting one of these as the proven owner of all 207,837 records. This is the one remaining diagnostic gap that should precede an invasive memory redesign.

**Concurrency changes must reduce work as well as move it.** Much of the correct architecture already exists: pump-free task spawning, navigation/typing activity gates, deferred hidden startup work, bounded Tier 1 reads, exact artifact deltas, prepared worker results, stale-selection checks, incremental row patches, and 150 ms detail debouncing. Preserve those mechanisms.

A coroutine scheduled as a Textual timer or callback can still occupy the app's serial message pump while awaiting a worker. Use the established [`spawn_pump_free_task`](https://github.com/sase-org/sase/blob/73718c77e1/src/sase/ace/tui/util/pump_tasks.py) lifecycle and existing refresh coalescing. Keep widget mutation on the UI thread and reject stale results after awaits. Textual's [worker documentation](https://textual.textualize.io/guide/workers/#thread-workers) specifically requires thread-to-main-thread handoff for most UI changes and notes that thread cancellation differs from coroutine cancellation.

Adding threads will not eliminate Python CPU and GC costs. Python's [asyncio documentation](https://docs.python.org/3.14/library/asyncio-task.html#asyncio.to_thread) explains the GIL limitation of `to_thread`. SASE's Rust [artifact-query and runtime-aggregation bindings](https://github.com/sase-org/sase-core/blob/e9b1cf04158d1168e43fb150dc6d7a62c14a959c/crates/sase_core_py/src/agent_scan/mod.rs) already release the GIL during core computation, then marshal results to Python. Large Python result graphs remain relevant. A wholesale rewrite in Rust is unnecessary; compact and batched core APIs are a targeted option when profiles justify them.

Another measured lead is runtime display aggregation: 28 retained hitch-start stacks from the older session ended at the Python-to-Rust runtime aggregate call. The current [`_agent_time_aggregate.py`](https://github.com/sase-org/sase/blob/73718c77e1/src/sase/ace/tui/models/_agent_time_aggregate.py) already caches input wires, result buckets, and fast identity hits. The remaining call still does Python `asdict` per member before Rust aggregation. Check invalidation frequency and membership size, then compute only changed/visible displayed durations or batch shared domain calculations. Do not replace the existing interval-union semantics with naive sums. Stack frequency is a prioritization lead, not a measured CPU percentage.

The countdown already respects typing/navigation gates. Similarly, detail debouncing already exists, yet a recorded pump hitch passed through prompt rendering and `renderable_content_digest`. Longer debounce is unlikely to be the fundamental answer. Skip unchanged detail content using stable content identity before building and hashing a large renderable, and only pursue that change if a fresh profile confirms its contribution after memory pressure is reduced.

**Existing instrumentation is sufficient for the first repair.** Reuse these tools:

| Question | Existing evidence/tool | Constraint |
|---|---|---|
| Where did startup time go? | `tui_startup.jsonl`, `sase tui --profile`, `capture_tui_startup.py`, `-X importtime` | Preserve timing anchors; capture imported SHA and environment |
| What blocked responsiveness? | `tui_stalls.jsonl`, `tools/tui_freeze_report` | Analyze one app instance and explicit time window |
| Is navigation fast? | `SASE_TUI_PERF=1`, `tui_jk.jsonl`, existing j/k and prompt benchmarks | Get enough fresh samples; check dropped samples and distinguish handler-to-paint from physical input arrival |
| Is unchanged polling cheap? | Short `SASE_TUI_TRACE=1` capture, `refresh.auto_tick`, loader spans | Inspect reload counts and causes; do not leave tracing enabled indefinitely |
| What drives memory growth? | Heartbeats, existing GC census, opt-in heap sampler | Heavy probes perturb the workload; isolate them from latency acceptance |

The default trace file was approximately **585 MB** and last modified November 15. Its presence is not evidence that the current process is tracing. I did not delete it or start a new long trace. The older baseline session had no fresh attributable navigation sample set sufficient for a p95 claim; three samples from the newer process are also insufficient. No navigation target is claimed achieved.

Use a brief allocation investigation only if the existing census plus worker/cache ownership inspection cannot identify the large snapshot owners. The existing `SASE_TUI_HEAP` sampler can compare allocation sites in a controlled reproduction; reduce traceback depth from the default 25 frames to keep overhead bounded. If it still cannot distinguish owners, add narrowly scoped counters to the existing telemetry for snapshot records retained by cache/task generation and full-history jobs in flight. Allocation sites and retaining owners answer different questions. There is no need for a new tracing framework, pervasive spans, or permanent `gc.get_objects()` scans.

Disable optional census/heap probes for final latency acceptance. The census uses `DEBUG_SAVEALL`, two collections, and a survivor traversal; its own source documents the longer pause. Python's [GC documentation](https://docs.python.org/3.14/library/gc.html) confirms that `DEBUG_SAVEALL` retains collected objects for inspection. Do not disable GC globally or repeatedly freeze newly created objects to hide allocation churn. The existing policy already moves collections to quiet periods and bounds their duty cycle; a user can still resume input during a long collection.

**A staged implementation makes the risk reviewable.** The following order is preferable:

| Order | Change | Expected benefit | Main acceptance risk |
|---|---|---|---|
| 1 | Correct canonical config ownership consistently; reuse validated project/workspace facts within an operation | Recover a large part of the observed 4–5 s construction regression and avoid moving it into owner discovery | Trust identity and acknowledgment semantics |
| 2 | Make cold provider descriptor discovery asynchronous across all callers, after the shared cause is repaired | Keep hidden provider inventory off first paint and protect against future project-count growth | Dynamic shortcut ordering, pending navigation, initial Artifacts startup |
| 3 | Bound retained snapshot/roster data and repeated preparation; apply exact deltas without reconstructing unchanged history | Reduce allocation rate, memory pressure, GC duration, and sustained refresh cost | Completeness, status/relationship parity, dismissal and selection stability |
| 4 | Optimize measured remaining runtime-tick/detail-render costs | Improve tail navigation latency | Stale elapsed displays or skipped real detail changes |

Stage 2 needs one coherent descriptor snapshot used by keymaps, Artifacts composition, help, command catalog, and navigation. Fixed panes can appear immediately; provider discovery may publish a complete generation later with a loading/error state and stable identifiers. An early provider shortcut should queue or resolve against the same generation, not silently point at a different pane. Avoid creating an empty cache entry that consumers mistake for authoritative discovery. This is broader and riskier than the first ownership fix, so it should not be bundled into its initial patch.

For stage 3, do not simply decrease refresh frequency or cap away active agents. Preserve active rows, omitted-history indicators, fallback behavior for unsupported queries, bounded lock waits, deleted/dismissed records, and optimistic action state. Reuse the existing prepared-apply and incremental-render routes. Move shared query/filter/projection semantics to Rust if they need changing; keep presentation state in Textual.

Validate each stage independently. For the first repair, add canonical-versus-legacy ownership and trust identity tests plus a project-count operation-count regression test. Assert near-linear config/inventory work at increasing project counts instead of a flaky tight time limit. Test changed acknowledgments/config/policy, ambiguous roots, and multi-project isolation. Then repeat real terminal startup captures at a fixed query/viewport with at least five runs per revision, recording load, versions, binding availability, initial tab, and imported SHA.

A reasonable provisional startup acceptance is to recover at least half the newly added construction cost, approach the previous roughly one-second construction regime on a comparable host, and verify an actual launch-to-interactive improvement. The prototype's 1.90 s profiled constructor makes a several-second recovery plausible, but not guaranteed. Report first frame, visible readiness, and all-surfaces readiness separately; a faster skeleton with delayed useful content is not success.

For sustained performance, run the existing representative Agents, Artifacts, Services, prompt-input, grouping, and large-history scenarios, including navigation during refresh and tab/query changes during worker completion. Keep the project's **p95 key-to-paint <16 ms** goal, but supplement it with watchdog tail stalls and enough real interaction samples. A keypress timer that starts after input dispatch cannot alone prove absence of earlier queueing. Run a real busy-session soak through repeated refresh and detail-navigation cycles; retained row counts and memory should settle, with no continuing growth toward the tens-of-GB condition. Set a concrete memory ceiling after identifying which surfaces legitimately retain data rather than inventing a universal RSS limit.

Run the required `just check` through SASE's approved tool workflow when implementing. A performance patch should also run its relevant slow benchmark explicitly; general correctness tests do not establish latency improvement. Match the tested Textual/core environment to the actual TUI. The installed/core binding mismatch found here must be resolved in the implementation environment before trusting test outcomes, without a global reinstall as part of this research.

**Recommended solution:** start with the verified config-ownership/trust-resolution repair and operation-scoped inventory reuse, preserving the trust contract. Then make provider discovery consistently lazy, and use the existing memory evidence to eliminate oversized retained snapshots and repeated whole-roster preparation. Finish with measured tick/render optimizations. This sequence offers a demonstrated several-second startup opportunity, attacks the sustained-session memory/GC problem at its source, and limits each change to a testable boundary. Add only narrow ownership diagnostics if the existing tools cannot identify who retains the large artifact graphs; do not begin with a new instrumentation system, global GC tuning, or a TUI rewrite.
