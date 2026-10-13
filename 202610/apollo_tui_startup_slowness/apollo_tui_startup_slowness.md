# Why `sase tui` starts slowly on apollo, and what to change

> **Research query:** Why does sase's TUI take so long to start up on the apollo machine?
> Profile that machine and sase's startup, and end with a ranked list of changes to
> consider for improving the TUI's startup on apollo (or in general).

![Infographic: sase's TUI paints about 5 s after launch on apollo but the Agents roster waits; a 3-second fallback timer starts heavy jobs together, and Python GIL contention starves the Agents loader (1.5–3.9 s alone vs 72 s in the app); combined experimental fixes cut Agents-ready from 42.2 s to 12.0 s; ranked changes start with building Patch relations only when needed, waiting for Agents before heavy jobs, fixing the plugin-discovery cache, and reserving CPU headroom on apollo](apollo_tui_startup_slowness_infographic.png)

## Bottom line

First paint is not the problem: the TUI draws about 1 s after mount, roughly 5 s after
you press enter. The dead time comes after that, while you wait for a usable Agents
roster. On apollo that wait used to be about 6 s (all-time p50). This week its p90 is
55 s, and your sessions today took 52–79 s (see
[what the telemetry says](#what-the-telemetry-says)).

1. **The Agents loader is not slow, it is starved.** Run alone on apollo, the loader
   finishes in 1.5–3.9 s. Inside your 13:02 TUI it took 72 s. In the lead's traces, one
   7,313-row SQLite read takes 0.06 s on its own and 0.28 s in a quick TUI startup, but
   **47.2 s** in a slow one. The cause is CPython's GIL. Python drops the GIL around every
   SQLite row step and every `stat`, and has to win it back each time. When CPU-bound
   Python threads in the same process are running, each win-back can wait up to the 5 ms
   switch interval. cld reproduced this on apollo at exactly 5 ms per row (see
   [the GIL convoy](#the-gil-convoy-turns-contention-into-minutes)).
2. **The TUI starts the starving threads itself.** 3 s after mount, a
   [fallback timer](#the-3-s-fallback-releases-everything-at-once) releases every
   hidden-surface and maintenance task, whether or not Agents is ready. Measured on
   apollo without a profiler, single-threaded, at load ≈22 (details in
   [the competing work](#the-competing-work-measured-without-a-profiler)):
   - **App-wide link index:** 7.5–8.5 s of CPU to walk 44,737 artifact-link rows.
   - **Prompt/macro catalog:** 8.3 s of CPU. Of that, 7.1–7.3 s is 624
     `importlib.metadata.entry_points()` rescans, caused by a cache that computes its key
     by re-running plugin discovery.
   - **Patch relation index:** 2.2–2.4 s of CPU per build. The file watcher rebuilds it on
     every artifact change even though its pane is hidden, which means 7–10 builds before
     Agents is ready in the slowest runs.
   - **Auto-refresh ticks:** each one runs `axe.collect`, which takes 2–29 s under
     contention. The slower the startup, the more ticks fire.

   This is a feedback loop: a slower startup gets more watcher rebuilds and refresh ticks,
   which slow it down further. That loop is the difference between a ~20 s startup and
   the 50–90 s cliffs.
3. **Apollo makes all of this worse.** It is a 16-vCPU KVM droplet on a 2017 Xeon 8168,
   2.2–2.9× slower per thread than athena. It runs system Python 3.12.3, at load 13–31,
   mostly from agents' pytest-xdist runs. The test gate's default budget leaves only 2 of
   the 16 vCPUs for everything else (see the [machine profile](#machine-profile)).

   The cause is not memory, CPU steal, disk saturation, the artifact-index tier, or the
   gateway (healthy today); see [what was ruled out](#what-was-ruled-out).
4. **The combined software fix saves about 30 s at today's load.** The lead ran 4+4
   interleaved startups at load 21–29
   ([lead experiment](#lead-experiment-with-the-combined-fixes)):
   - **Unmodified:** mean **42.2 s** to Agents-ready (range 27.2–60.8 s).
   - **With fixes:** mean **12.0 s** (range 11.2–13.8 s), and the variance disappears.
     The fixes were: (a) memoized plugin discovery, (b) no hidden Patch relation index,
     (c) deferred work held until Agents is ready.

The ranked list of changes is in
[Ranked changes to consider](#ranked-changes-to-consider). The top three are
small-to-medium code changes in this repo. #4 is a no-code apollo setting.

## What the telemetry says

**Field semantics** (grk, cdx). These matter before comparing any numbers:

- `agents_ready_seconds` is measured from `AceApp` init, not process start. Add 4–6 s of
  CLI start and import to get wall-clock time.
- `visible_ready` and `all_surfaces_ready` are measured from `on_mount`.
- The footer stopwatch stops at `all_surfaces_ready`, which waits for both Agents and
  Services. Its all-time p50 is 8.0 s, against 3.2 s for `visible_ready`.
- `interpreter_cli_import_seconds` is broken after in-process restarts (one value was
  237,028 s). Ignore it.
- The loader's `disk` stage covers the dismissed snapshot, index query, decode, status
  and identity normalization, and projections. It does **not** mean waiting on physical
  disk.

**Trend** for apollo `agents_ready_seconds` by week (cld):

| Week of | p50 | p90 | max |
| --- | --- | --- | --- |
| 09-21 | 4.9 s | 18.2 s | 38 s |
| 09-28 | 5.5 s | 18.4 s | 65 s |
| 10-05 | 6.0 s | 32.6 s | 92 s |
| 10-12 | 13.4 s | **55.5 s** | 79 s |

Athena's p90 over the same weeks was 12–19 s, and its all-time p50 is 4.55 s.

**Your sessions today**, as `agents_ready`:

- Morning: 11.0, 11.3, and 14.5 s.
- **55.5 s** at 11:55.
- **79.0 s** at 13:02: `disk` 72.05 s, `prep` 0.71 s, `apply` 0.64 s.
- 35.7 s at 13:54, an in-process restart of the same TUI.

The 13:02 session went on to a 69 s revalidate and a 54 s notification delta load, so the
TUI does not go quiet after startup either. Every startup over 37 s in the log puts its
time in the loader's `disk` stage. During the 79 s startup the stall watchdog recorded
only 1.5–2 s event-loop hitches. The time went to worker threads waiting, not to the UI
thread blocking.

## Mechanism

### The loader in isolation

| Step (apollo, under load) | Time |
| --- | --- |
| Cached artifact-index query (273 records) | 0.39 s warm |
| Tier-1 cached snapshot | 0.35 s |
| Decode (457 agents + 807 workflow steps) | 0.86 s |
| `load_tiered_agents(...)` | 1.54 s |
| Full provider wrapper `load_agents_from_disk_with_state` (962 raw agents) | 3.87 s, of which identity snapshot 0.73 s and status normalization 1.09 s |

### The 3 s fallback releases everything at once

`_STARTUP_DEFERRED_FALLBACK_SECONDS = 3.0` (`src/sase/ace/tui/actions/_startup_loads_core.py`)
fires `_release_startup_deferred_loads`. That function starts all of the following
together:

- Deferred mount-state loads. These read Patches and then call `_apply_patches`, which
  builds the relation index **on the event loop** (`_startup_loads_index.py`).
- The Services/axe surface.
- `_schedule_deferred_startup_maintenance`: prompt-catalog rebuild, update-toast check,
  update attempts, usage-refresh fallback, **app-wide link-index refresh**, prompt-bar
  import warm, and the dismissed named-proc prune.
- Deferred post-roster work and monitor reconcile.

On athena, Agents is usually ready before the 3 s mark, so this release is orderly. On
apollo it almost never is, so the fallback fires in the middle of the load.

### The competing work measured without a profiler

| Work | Lead measurement on apollo (load ≈22, single thread, no profiler) | Figures in the reports | Notes |
| --- | --- | --- | --- |
| Prompt/macro catalog build | 8.3–8.5 s wall, 8.2–8.4 s thread CPU. 624 `entry_points()` calls cost 7.1–7.3 s. With discovery memoized: **1.28–1.31 s**, 40 calls, same 250 snippets | 20.8 s (cdx, cProfile); 20.6 s (gem, pyinstrument) | The profilers inflated the time about 2.5×. The work is CPU: each call parses 94 dist-infos (12–17 ms per call). |
| App-wide `LinkIndex` (`link_index_for_snapshot` → `_build_link_index`) | **7.5–8.5 s CPU** over 44,737 rows | 7.39 s (gem) | Cached by aggregate mtime/size signature, but that signature changes whenever any agent writes links |
| Patch relation index (`_build_patch_relation_index`) | **2.2–2.4 s CPU per build**; repeat builds cost the same (no memoization) | 2.34–2.39 s (cld); 5.36 s including snapshot load under cProfile (cdx) | The first build runs on the event loop at startup. After that the file watcher reruns it back-to-back for every artifact change. |
| Auto-refresh tick (`axe.collect`: 766–768 file opens, 361 run-JSON parses) | 2–29 s per tick in cliff runs | 5–15 s (cld) | Ticks fire about every 10 s whatever the startup state |
| Update check, bead/plan-preview warmups, diff badges | 2–10 s each under contention (cld) | | |

**Why the plugin cache doesn't help.** `get_plugin_input_type_registry()`
(`src/sase/macro/plugin_input_types.py`) builds its cache key by calling
`_discovery_snapshot(files)` *before* it checks the cache. With `files=None`, that runs
`discover_macro_plugin_input_type_files()` and `discover_macro_plugin_distributions()`,
and each of those scans two entry-point groups. `_plugin_registry_snapshot()` in
`_loader_parsing_inputs.py` calls this once for every macro input it parses. The cache
therefore never skips the expensive part. The bug also slows any CLI command that loads
macros, not just the TUI.

**Why the reports disagree on relation-index cost (2.4 s, 5.4 s, 7.4 s).** They measured
two different walks over the same 44 k rows: the Patch relation projection and the
app-wide link index. Both run at startup.

### The GIL convoy turns contention into minutes

cld's reproduction used apollo's real dismissed-bundle index (7,313 rows, read-only), with
the default 5 ms switch interval:

| Competing CPU-bound Python threads | Query time |
| --- | --- |
| 0 | **0.059 s** |
| 1 | **36.4 s** |
| 3 | **71.8 s** |

Athena on CPython 3.14 shows the same effect (0.022 s alone, 31.8 s with one spinner), so
this is a CPython property, not an apollo bug. Lowering `sys.setswitchinterval` on its own
did not help in cld's A/B.

The lead's traces show where the convoy landed in real startups. Numbers are seconds of
each span that overlap the window before Agents was ready:

| Span | Base run 4 (60.8 s) | Base run 8 (27.2 s) | Fix run 6 (11.2 s) |
| --- | --- | --- | --- |
| `agents.load_from_disk` (the loader's `disk` stage) | 51.3 | 14.5 | 3.5 |
| ↳ `dismissed_snapshot` | **47.2** | < 0.9 | 0.28 |
| ↳ `provider` (identity and normalization) | 3.6 | **13.4** | 2.9 |
| `relations.index.patches` | 37.1 (×8) | 3.8 (×1) | 0 |
| `refresh.auto_tick` / `axe.collect` | 41.2 (×4) / 39.4 (×5) | — / 12.2 (×2) | — / 0.3 |

The victim changes from run to run. Sometimes it is the dismissed-identities `fetchall`,
sometimes the `realpath` storm in `AgentIdentitySnapshot.current()` (0.5 s alone, up to
7.6 s in the TUI). It is always a loop on the loader's critical path that releases the GIL
on every row or syscall. Two more such loops sit on that path:

- The dismissed index is opened with `create=True`, so **every read runs `BEGIN
  IMMEDIATE`, a schema upsert, and a commit**, including an fsync on this fsync-bound disk
  (confirmed in `dismissed_bundle_index/_schema.py`).
- Each decoded record makes its own probes: `Path.resolve`, marker `is_file` checks, and
  commit-metadata JSON reads.

### The ToolRun glance refresh piles up during slow startups

**New finding.** `_run_tool_runs_refresh` (`src/sase/ace/tui/tool_runs/loader.py`) works
like this:

1. It clears `state.scheduled`.
2. While `_agents_loading` is true, it re-arms itself on a 50 ms timer and returns.
3. The next `_schedule_tool_runs_refresh` call, from the countdown drift probe at most
   every 2 s, sees the refresh as neither running nor scheduled, so it starts **another**
   timer chain.

Every chain spawns a pump-free task 20 times a second until Agents finishes loading. Then
they all run `load_glance_blocking` at the same time.

In base run 4 (60.8 s), 20 chains built up, and 20 × 2.3 s glance loads all started within
0.1 s of the roster appearing. Only 1 of the 4 base runs showed this. It needs the ToolRun
store to change during a long load, which the `sase tool wait` pollers' constant
reconcile writes make likely. The cost is extra event-loop churn during startup, plus
about 45 s of thread work right as the roster appears. The fix is small: keep `scheduled`
set while deferring, or re-check `running`/`scheduled` on the deferred path.

### The quiet floor of imports and event-loop work

- **Import is about 3× slower than athena.** `import AceApp` takes 5.5–6.6 s on apollo
  against 1.9 s on athena, and `sase.*` modules account for about 4.8 s of that.
- **The heaviest import subtrees** on apollo (cld) are `actions.agents._core` (3.9 s),
  `_agent_enter_action` (1.9 s), `_metadata_search` (1.3 s), `gate_turn` and
  `notification_gates` (1.15 s), `agent_detail` (1.1 s), and `prompt_panel` (0.9 s).
  Nested cumulative times overlap, so don't add them.
- **Dataclass creation is about half the import on 3.12.** 2,012 dataclasses are created
  at import time, making 11,164 `exec` calls. The import-budget test caps the import at
  5.0 s of process time, and apollo's hardware already exceeds that.
- **`repro.capture` is imported on the event loop for every load.**
  `from ...repro.capture import record_agents_tab_loader_result`
  (`agents/_loading_disk_full.py:117`, `:271`) runs on every Agents load and pulls in
  +293 modules. It costs 0.56 s alone and 2.5–3.9 s in the TUI, yet the call is a no-op
  unless repro capture is enabled.
- **Python 3.14 is a small win.** It is about 15–20% faster on pure-Python loops but only
  about 8% faster at creating dataclasses, so it shortens import a little and does not
  fix the convoy.

## Machine profile

| | apollo | athena (control) |
| --- | --- | --- |
| Hardware | DigitalOcean KVM droplet, 16 vCPU Xeon Platinum 8168 @ 2.7 GHz (Skylake-SP, 2017), 1 thread/core | Threadripper 3970X, 32C/64T, boost to 4.55 GHz |
| Per-thread Python speed | 2.2–2.9× slower on `fib`, dict inserts, and sort, same interpreter on both hosts (cld) | baseline |
| RAM / swap | 31 GiB / **none** | 62 GiB |
| Disk | virtio ext4 `/dev/vda1`, 74% full (51 GiB free) | local NVMe |
| sase interpreter | uv tool venv symlinked to **system `/usr/bin/python3.12` (3.12.3)**; uv has no 3.14 installed (only 3.10) | uv-managed CPython 3.14.7 |
| sase revision | 0.17.1 editable at `010185b0c4`, sase-core-rs 0.39.0 | same |
| `from sase.ace.tui import AceApp` | **5.5–6.6 s**, 3,493 modules | 1.85–1.95 s |
| Load during research | 9–31 (lead: 21–29) | ~5–8 on 64 threads |
| PSI | CPU `some` avg60 8–23%; I/O `full` 3–8% (D-state tasks waiting on `jbd2` journal commits); memory ≈0 | — |

### Who uses the CPU on apollo

cld's 10 s census found about 11.2 cores busy:

- Agent pytest-xdist runs: 8.1–9.6 cores.
- axe: 0.6–1.8 cores.
- Each `sase tool wait` poller: 0.2–0.5 cores.
- Your idle TUI: 0.3 cores.

At 14:10 the lead saw a similar picture:

- Two xdist runs (apollo workspaces `sase_10` and `sase_16`), with 6–7 workers each at
  40–90% CPU and 1.1–1.4 GB RSS apiece.
- rustc, the LLM usage workers, and one `sase tool wait`.
- MemAvailable had fallen to 8 GiB (it was ~20 GiB earlier in the day).

### Why there are so many test workers

`tools/run_pytest`'s suite gate (helpers in `tests/_suite_gate_budget.py`) sizes a
host-wide token pool. The pool is the smallest of:

- CPUs minus max(1, CPUs/8);
- (MemAvailable − 8 GiB) / 700 MiB;
- 32.

Each run gets a fair share of half the pool. On apollo that means a pool of 14 and 7
workers per run, so **two concurrent agent test runs take 14 of the 16 vCPUs**.
`SASE_TEST_GATE_SLOTS` overrides the pool size. The gate also assumes 700 MiB per worker,
but workers were observed at 1.1–1.4 GB, which matters on a host with no swap.

### What was ruled out

Ruled out by consensus and rechecked by the lead:

- Memory pressure (PSI ≈0).
- CPU steal (≈0) and cgroup throttling (none).
- Missing bytecode.
- A Tier-2 source-scan fallback: every slow startup since 10-03 was `tier1`/`artifact_index`.
- A bad SQLite plan: the queries are indexed and take 55 ms.
- Disk saturation: iowait was 0.5–3%, and every lead probe had thread CPU ≈ wall time.
- The gateway: healthy at 13:14 and at 14:13, with 17 threads, 11 fds, 114 MB RSS, and no
  WAL backlog.

## Lead experiment with the combined fixes

**Setup.** In the lead's A/B on apollo, a wrapper pre-imported the same modules in both
arms. The **fix** arm applied three process-local monkeypatches:

- (a) memoized `_discovery_snapshot(None)`;
- (b) `_build_patch_relation_index` → `None`;
- (c) `_STARTUP_DEFERRED_FALLBACK_SECONDS = 120`, so hidden work is released at
  visible-ready instead of at 3 s.

Each run used `sase tui -x -t agents` in a private 160×48 tmux session, with startup,
loader, and trace telemetry redirected to scratch files. The arms were interleaved B F F
B B F F B.

| Run | Arm | load1 | `agents_ready` | `visible_ready` | Relation-index builds |
| --- | --- | --- | --- | --- | --- |
| 1 | base | 21.1 | 48.6 s | 45.1 s | 7 |
| 2 | fix | 21.3 | 11.2 s | 7.6 s | 0 |
| 3 | fix | 23.4 | 13.8 s | 10.0 s | 0 |
| 4 | base | 28.9 | 60.8 s | 56.9 s | 8 |
| 5 | base | 27.1 | 32.2 s | 28.5 s | 3 |
| 6 | fix | 27.1 | 11.7 s | 7.8 s | 0 |
| 7 | fix | 29.5 | 11.2 s | 7.4 s | 0 |
| 8 | base | 27.3 | 27.2 s | 23.7 s | 1 |

- **Base:** mean 42.2 s, median 40.4 s.
- **Fix:** mean 12.0 s, median 11.5 s.

In the base arm, the number of relation-index builds tracks the startup time. This agrees
with the single-change ablations: cld's (34.0 → 26.3 s mean, n = 17) and cdx's
(18.7 → 10.9 s after mount, one pair). Combining all three changes removes most of the
remaining contention.

**Caveats:**

- Each arm has only n = 4.
- (b) stands in for "build it when the pane is visible"; it is not a shippable change.
- (c) cancels the fallback instead of implementing a proper readiness gate.
- The fix arm still costs about 15–18 s of wall time at load ≈25 (11–14 s plus 3–4 s of
  import), so apollo stays 2–3× slower than athena until the deeper items in the
  [ranked changes](#ranked-changes-to-consider) land.

## Disagreements resolved

| Claim (source) | Verdict |
| --- | --- |
| "The prompt catalog costs ~20 s" (cdx, gem) vs "the `entry_points` scans are convoy victims holding only ~1.3 s of GIL" (cld) | **Both are partly right.** Run alone without a profiler, the build takes 8.3 s, nearly all of it CPU, so it is a real hog; the profilers inflated it about 2.5×. Inside the TUI it also waits on the GIL. Memoization cut it 6.5×. |
| The relation index costs 2.4 s, 5.4 s, or 7.4 s | **Two different walks.** The Patch relation index costs 2.2–2.4 s; the app-wide link index costs 7.5–8.5 s. cdx's figure included snapshot load and cProfile overhead. |
| "14× slower disk drives startup" (gem) | **No.** Synchronous write throughput is not on the startup path; iowait was 0.5–3% and the probes were CPU-bound. I/O pressure (`jbd2` commit waits) is a secondary tax, fed partly by `sase tool wait` reconcile writes and the dismissed-index write on every read. |
| "965 agents vs 23 on athena; cap the roster at 50" (gem) | **Not the difference.** Athena loads 822 agents (grk). `apply` took 0.8–1.0 s in the lead's runs. A bounded first window (grk, mus) is polish, not the fix. |
| "The gateway stampede is the top issue" (mus, measured on athena only) | **Not active today.** The gateway was healthy at both checks. It is a separate tail risk from the Oct 9 incident, so it stays on the list but not at the top. |
| "Projected 78 s → 5–8 s" (gem) | **Overstated.** Adding up per-item savings double-counts shared contention. Measured combined effect: ~42 → ~12 s from init (~15–18 s wall) at load ≈25. |
| Apollo's Python version | **System 3.12.3** (cld is right). uv has no 3.14 installed on apollo. |
| Lowering `sys.setswitchinterval` | **No help on its own** (cld A/B). Revisit only after the CPU hogs are gone. |

## Scope and evidence base

**Consolidated report.** This merges five independent researcher reports (`__cdx`, `__cld`,
`__grk`, `__mus`, `__gem` in this directory) with the lead researcher's own checks and A/B
runs on apollo, made 2026-10-13 between 14:10 and 14:35 UTC. All times are UTC (Bryan's
local time is EDT, UTC−4). No sase code, config, or installed environment was changed on
apollo. The lead's experiments used process-local monkeypatches inside disposable
`sase tui -x` instances, with their telemetry redirected to scratch files.

| Researcher | Where | Main method | Distinctive contribution |
| --- | --- | --- | --- |
| cdx | apollo | py-spy (child process), cProfile, graph-skip ablation pair, registry-reuse experiment | 636 `entry_points()` calls per catalog; skipping the graph took visible-ready 18.7 → 10.9 s after mount; identity discovery walks the full repo inventory |
| cld | apollo + athena | `py-spy --gil`, 17-run interleaved A/B, GIL-convoy reproduction | Relation-index treadmill: mean 34.0 → 26.3 s, SD 15 → 0.6 s. 5 ms/row convoy. Dismissed-index write transaction on every read. `repro.capture` import on the event loop. Dataclass import cost |
| grk | apollo + athena | Telemetry statistics (493 + 1,944 records), isolated loader probes | Loader 1.5 s isolated vs 72 s in the TUI. Telemetry field semantics. Stopwatch gated on Services. inotify cap. Slow loads continue after startup |
| mus | athena only | Perf runbook, telemetry, import timing | Profiling playbook; gateway-stampede history; per-row prep cost; source-scan cliff paths |
| gem | apollo + athena | pyinstrument, stall log | The 3 s fallback stampede; the app-wide `link_index_for_snapshot` cost; `repro.capture` stall; GC pauses |
| lead | apollo | Unprofiled probes; 8-run interleaved A/B with all three fixes combined; trace-span attribution before ready | Separates real costs from profiler-inflated ones; measures the combined effect; finds the ToolRun glance coalescing bug and the pytest gate budget |

## How to re-measure

- **Host first:**
  - `uptime`, `cat /proc/pressure/{cpu,io,memory}`, and
    `ps -eo pcpu,rss,args --sort=-pcpu | head`.
  - Count the agent xdist workers before trusting any TUI number.
- **Isolated costs** (installed interpreter `~/.local/share/uv/tools/sase/bin/python3`):
  - Time `build_prompt_catalog_snapshot(generation=0, projects=())`,
    `_build_link_index(load_artifact_links_snapshot(None))`, and
    `_build_patch_relation_index(find_all_patches_cached())` with `perf_counter` and
    `thread_time`, not under a profiler.
- **A traced launch with redirected telemetry:**
  - Set `SASE_TUI_TRACE=1` and give `SASE_TUI_TRACE_PATH`, `SASE_TUI_STARTUP_PATH`, and
    `SASE_TUI_AGENT_LOADS_PATH` their own scratch paths.
  - Sum the spans that overlap the window before the first
    `agents.apply_loaded_agents_prepared`.
  - `py-spy` has to be the **parent** process (apollo has `ptrace_scope=1`). Use
    profilers to attribute time, never to measure it.
- **Clean up the shared log:** filter researcher runs out of apollo's
  `~/.sase/logs/tui_startup.jsonl`. cld lists its 20 `app_instance_id`s in its report; cdx
  and the lead redirected their telemetry.
- **Lead scratch files:** scripts and 8 run directories are in
  `/tmp/sase-lead-probe-vwkeva/` on apollo, safe to delete.

## Ranked changes to consider

Ranked by expected effect on apollo's startup, weighted by evidence strength and effort.
Most of them also help athena.

1. **Stop the Patch relation-index treadmill.** *(Code, this repo; small–medium;
   strongest single-change evidence.)*
   - In `event_refresh/_watcher.py`, mark Patches dirty instead of reloading them when the
     Artifacts/Patches pane isn't visible, and reload on tab entry. Respect the startup
     window and `NavigationGate`.
   - Debounce visible-pane reloads adaptively, by at least the duration of the last
     reload.
   - Take the startup `_apply_patches()` build off the event loop: reuse the worker's
     prepared result, or build lazily on first relation-rail use.
   - Memoize on (link-aggregate signature, Patch-set signature).
   - Evidence: the cliffs and variance disappear (cld n = 17; cdx pair;
     [lead A/B](#lead-experiment-with-the-combined-fixes) arm b).
2. **Gate hidden startup work on Agents readiness, not a 3 s timer.** *(Code, small.)*
   - Replace the [3 s release](#the-3-s-fallback-releases-everything-at-once) with
     "release at visible-ready", keeping a generous safety timeout (30–60 s) and the
     existing tab-switch fast path.
   - Release the heavy jobs one after another instead of all at once: prompt catalog,
     app-wide link index (7.5–8.5 s), update check, and warmups.
   - Suppress auto-refresh ticks (`axe.collect`) and watcher-driven hidden reloads until
     startup completes.
   - This breaks the slow-startup → more-ticks → slower-startup loop.
3. **Fix the plugin-discovery rescans.** *(Code, ~20 lines; do this first, it is the
   cheapest.)*
   - Compute the discovery snapshot once per catalog generation and pass it down, or
     memoize it per process. Invalidate on manifest mtime, the installed plugin set, and
     the disable-plugin env vars.
   - Share `_discover_macro_plugin_entry_points` within a generation to remove the
     remaining 40 calls.
   - Measured: 8.3 → 1.3 s of CPU, with identical output. It also speeds up every CLI
     command that loads macros.
4. **Give interactive work headroom on apollo.** *(Ops, no code, immediate.)*
   - Set `SASE_TEST_GATE_SLOTS` in apollo's agent environment to about 6–8. Today
     [two agent `just check` runs](#why-there-are-so-many-test-workers) can take 14 of
     the 16 vCPUs.
   - Run agent tests and release-mode `rustc` builds under `nice`/`ionice`.
   - `%dispatch` heavy agents to athena, which idles at load 5–8 on 64 threads.
   - Every number in this report scales with contention, and the convoy penalty grows
     with the number of busy threads.
   - Separately, the gate's 700 MiB-per-worker estimate is low against the observed
     1.1–1.4 GB, which is an OOM risk on a host with no swap.
5. **Make the 44.7 k-row link walks cheap.** *(sase-core plus thin adapters; medium.)*
   - Move both the app-wide `LinkIndex` build and the Patch relation projection into
     sase-core. Use one batched call or an inverted index keyed by ref lookup key,
     memoized by aggregate signature, so Python asks only about the refs it needs.
   - Today they cost 7.5–8.5 s and 2.2–2.4 s of CPU per build, through tens of thousands
     of per-row FFI calls.
   - Move `sase-core-revision.txt` past the new sase-core commit.
6. **Fix the ToolRun glance coalescing bug
   ([described above](#the-toolrun-glance-refresh-piles-up-during-slow-startups)).**
   *(Code, small.)*
   - Keep `scheduled` set while the refresh defers behind `_agents_loading`, so only one
     deferred chain exists.
   - Add a test that schedules repeatedly during a long Agents load and asserts that only
     one glance load runs.
7. **Take convoy-prone loops off the loader's critical path.** *(Code plus sase-core;
   medium.)*
   - Open the dismissed index with `create=False` for reads, so a read never commits a
     write transaction.
   - Fetch dismissed identities in one Rust call, or from a materialization keyed by the
     index signature.
   - Make `AgentIdentitySnapshot` discovery lightweight and cached, without
     `realpath`-ing every workspace × repo pair.
   - Batch the per-record decode probes.
   - Longer term: run the startup Agents load as a single Rust call that releases the GIL
     once, or in a helper process.
8. **Trim imports and event-loop imports.** *(Code, small–medium; plus ops.)*
   - Import `repro.capture` only when capture is enabled, and move the post-update-toast
     import off the loop.
   - Defer `_agent_enter_action`, `_metadata_search`, `gate_turn`/`notification_gates`,
     `agent_detail`, and `prompt_panel` until first use.
   - Watch the startup dataclass count, and keep `test_app_import_budget.py` as the
     ratchet.
   - Then move apollo's tool env to Python 3.14. Global installs are human-only:
     `uv python install 3.14`, then `just install-dev --python 3.14`. Expect roughly
     0.5–1 s off import plus 15–20% on pure-Python loops.
9. **Make cliffs diagnosable from telemetry alone.** *(Code, small.)*
   - Split the loader's `disk` stage into dismissed / index / decode / normalize-identity /
     projections.
   - Record load1, runner count, relation-index builds before ready, and the
     deferred-release reason in `tui_startup.jsonl`.
   - Fix the misleading clock names and anchors.
   - Consider driving the footer stopwatch from `visible_ready`.
   - Both of today's root causes needed py-spy to find; these fields would have shown them
     directly.
10. **Fix steady-state slowness after startup.** *(Code plus ops; after the items above.)*
    - When the 4,096-watch inotify budget can't cover the ~20 k artifact directories
      (apollo's `max_user_watches` is 250 k), make auto-refresh reload by change token
      instead of escalating to full loads.
    - Back off `sase tool wait`/`_join` polling: they reconcile every 0.5 s, at
      0.2–0.5 core and about 490 writes/s each.
    - Keep gen-2 GC pauses (0.8–1.4 s) out of the first-load window.
    - Contain the gateway: single-flight snapshot rebuilds in sase-core, `MemoryMax`, and
      swap or memory caps, so the Oct 9 incident can't recur.
11. **A faster droplet, last.** *(Ops, costs money.)*
    - Only consider it after items 1–8, measured on the same revision and data.
    - More vCPUs can't fix GIL serialization. Better per-thread speed from a newer
      CPU-optimized class would cut every CPU-bound stage by an estimated 1.3–2×.

**Expected outcome.** Items 1–3 plus 6 should roughly reproduce the
[A/B fix arm](#lead-experiment-with-the-combined-fixes): about 12 s from init (15–18 s
wall) at load ≈25, with the cliffs gone. Item 4 lowers that floor further. Items 5, 7,
and 8 are what it takes to approach athena's ~5 s.
