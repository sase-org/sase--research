# Why `sase tui` starts slowly on apollo — host + startup profile (cld)

**Date:** 2026-10-13 (measurements 13:00–13:55 UTC)
**Researcher:** cld (one of a 5-researcher swarm)
**Code under test:** sase `010185b0c4` (the editable checkout apollo's uv tool env runs), sase 0.17.1
**Hosts:** apollo (profiled), athena (comparison baseline)

---

## TL;DR

On apollo, TUI startup is slow for three separate reasons that stack:

1. **A slow, oversubscribed host.** Apollo is a 16-vCPU DigitalOcean KVM guest on a 2017 Skylake-SP Xeon 8168 at 2.7 GHz.
   - While I profiled, load average was **13–31**, with 9–17 agent runners. Agent-launched `pytest -n 6/7` runs alone used **8–10 of the 16 cores**.
   - CPU pressure (PSI `cpu some`) was about **10–23 %**. I/O pressure (`io full`) was about **3.5 %**, mostly ext4 journal-commit (`jbd2`) fsync waits.
   - With the same interpreter, single-thread Python is **2.2–2.9× slower than athena**. The TUI's import alone takes **5.6 s vs 1.85 s**.
2. **The Patches relation index runs non-stop at startup, even though the Artifacts tab isn't visible.**
   - Every artifact change the fs-watcher sees triggers a Patches reload immediately. The code comment says "Patch refreshes are cheap enough to keep immediate".
   - Each reload rebuilds the relation index by walking **all ~44 k artifact-link rows**: 2.4 s of pure CPU on apollo, 0.8 s on athena.
   - With 10–17 agents writing files, these reloads run back-to-back for the whole startup window: **7–11 builds before the Agents tab is ready**. That is about 30 % of all GIL time.
   - The first build also runs **synchronously on the event loop**.
3. **A GIL convoy multiplies every syscall on the Agents loader's critical path.**
   - CPython gives up the GIL around each `sqlite3` row step, `stat`/`lstat`, `open`, and so on.
   - When a CPU-bound thread is also running, each re-acquire waits for the 5 ms switch interval.
   - Measured on apollo: the dismissed-identity query takes 59 ms alone. With one CPU-bound thread running it takes **36.4 s**, and with three it takes **71.8 s**. The cost is exactly 5.0 ms per row.
   - The same effect turns a 0.5 s first call to `AgentIdentitySnapshot.current()` (a `realpath` storm over the repo inventory) into **7.6 s** inside the TUI.

Two outcomes are possible depending on whether the relation-index treadmill overlaps the loader:

- **Slow:** about 20–30 s to Agents rows.
- **Cliff:** 37–97 s to Agents rows. This is the "it took forever" case you've been seeing, and it is getting more frequent. Weekly p90 rose from 18 s to 33 s to 55 s over the last 3 weeks.

**A/B on apollo** (n = 17 startups, interleaved, real archive):

| Variant | Agents ready (mean) | SD | Range |
| --- | --- | --- | --- |
| Unmodified | 34.0 s | 15.1 | 19.7–65.6 s |
| Relation index stubbed out | 26.3 s | 0.6 | 25.4–27.0 s, at load ~30 |
| Relation index stubbed out + 1 ms switch interval | 21.0 s | 0.6 | — |

The ranked change list is at the end (§8).

---

## 1. What I did

All profiling on apollo was read-only with respect to sase state, apart from the TUI's normal startup side effects. Scratch files live in `/tmp/cld_prof` on apollo and `/tmp/apollo_prof` on athena.

1. **Host profile.** I collected `lscpu`, `/proc/pressure/*`, `vmstat`, `iostat -x`, `pidstat -d`, per-thread `/proc/<pid>/task/*/stat`, and a 10 s CPU census grouped by workload category.
2. **Telemetry history.** I copied apollo's `~/.sase/logs/tui_startup.jsonl`, `tui_agent_loads.jsonl(.1)` and `tui_stalls.jsonl(.1)`, and compared them with athena's `tui_startup.jsonl`.
3. **Live profiled startups.** Apollo has `kernel.yama.ptrace_scope=1`, so py-spy cannot attach to your running TUI. Instead I launched fresh `python -m sase tui -x -t agents` instances as **children** of `py-spy record`, inside a private tmux server (`tmux -L cldprof`), with `SASE_TUI_TRACE=1`:
   - run 1: `--idle --threads -r 100` (raw)
   - run 2: `--gil --threads -r 100` (raw). This samples only GIL holders.
   - run 3: `--idle --threads -r 50` (speedscope). This gives a time-ordered loader-thread timeline.
4. **Micro-benchmarks on both hosts.** These covered interpreter speed, dataclass creation, `-X importtime`, cProfile of the AceApp import, the GIL-convoy reproduction, relation-index build cost, and the identity-snapshot cost.
5. **A/B startups.** I ran 17 un-profiled traced startups through a small wrapper (`/tmp/cld_tui_wrap.py`) that can (a) stub `_build_patch_relation_index` to return `None` and/or (b) call `sys.setswitchinterval(0.001)`.

My runs added about 20 records to apollo's `~/.sase/logs/tui_startup.jsonl` between 13:11 and 13:55 UTC on 2026-10-13. Filter them out of future analyses by `app_instance_id`: `c821b277 b91b2270 b03680b6 f270239a 3de9a8e8 608be202 40af5e27 6ac26670 719cdb19 12f41a35 c3fb0ca3 8c489ae2 b29b98ab 942ee863 4bdc1b35 304e46b8 63041704 30c8b13a 3ec66b31 e058da08`.

---

## 2. Machine profile: apollo vs athena

|                       | **apollo**                                                         | **athena**                         |
| --------------------- | ------------------------------------------------------------------ | ---------------------------------- |
| Hardware              | DO droplet (NYC1), KVM, 16 vCPU Xeon Platinum 8168 @ 2.7 GHz (Skylake-SP), 1 thread/core visible | Threadripper 3970X, 32C/64T (Zen 2, up to 4.5 GHz) |
| RAM / swap            | 31 GiB / none                                                      | —                                  |
| Disk                  | virtio `vda`, ext4 `discard,commit=30`, mq-deadline                 | local                              |
| OS / kernel           | Ubuntu 24.04.3, 6.8.0; PTI + IBRS mitigations active               | Debian 13, 6.12                    |
| sase tool env Python  | **system `/usr/bin/python3.12` (3.12.3)**                          | **uv-managed CPython 3.14.7**      |
| Load during profiling | **13–31** on 16 vCPU; 9–17 `run_agent_runner.py`                    | ~5–7 on 64 threads                 |
| CPU PSI `some` avg60  | 10–23 %                                                            | —                                  |
| I/O PSI `full` avg60  | 2–3.8 %; D-state tasks sit in `jbd2_log_wait_commit`; 266–412 flushes/s | —                           |

**Who uses apollo's CPU** (10 s census, measured twice): about 11.2 cores busy in total.

- Agent `pytest` runs (`-n 6`/`-n 7` from `sase_10` and `sase_16`): **8.1–9.6 cores**
- axe routines/jobs: 0.6–1.8 cores
- axe agent runners: 0.1–0.5 cores
- one `sase tool wait` poller: 0.16–0.24 cores
- your idle TUI: 0.24–0.33 cores

Runnable threads were 15–20 on 16 vCPUs.

**Per-thread speed** (best of 3, same uv CPython 3.10.20 on both hosts):

| Microbench | apollo | athena | Ratio |
| --- | --- | --- | --- |
| `fib(27)` | 0.100 s | 0.043 s | 2.3× |
| 1 M dict inserts | 0.751 s | 0.345 s | 2.2× |
| sort 500 k strings | 0.517 s | 0.179 s | 2.9× |

On athena, 3.12 → 3.14 is about 15–20 % faster on the same loops.

**`sase tool wait` / `sase tool _join` pollers** (`src/sase/tool/control_wait.py:36-77`) are a background tax on apollo.

- Each waiter runs `reconcile_unsettled_tool_runs()` every ≤ 0.5 s (`_POLL_MAX_SECONDS = 0.5`).
- That costs about **50 % of a core**, about 9 MB/s of reads, about **490 write syscalls/s**, and about 2.2 MB/s of block writes, most of which are cancelled rewrites.
- Two of these were live during the census (`/proc/<pid>/io`, `pidstat -d`). It is not the main problem, but it feeds the fsync/IO pressure every interactive process sees.

---

## 3. What the telemetry history says

From `tui_startup.jsonl`. "Wall" adds the pre-`AceApp` import stages to the stopwatch fields. The `*_ready_seconds` fields are measured from `AceApp` init, not OS process start.

| Since 2026-09-20                 | apollo                               | athena                            |
| -------------------------------- | ------------------------------------ | --------------------------------- |
| Blank screen → first paint, wall | p50 **7.4 s**, p90 10.2 s            | p50 4.1 s, p90 6.8 s              |
| `app_module_import_seconds`      | p50 **3.8 s** (now 5.0–5.3 s under today's load) | p50 2.0 s                         |
| AceApp init → `on_mount`         | p50 2.3 s                            | p50 1.3 s                         |
| Agents ready, wall               | p50 10.3 s, p90 **24.8 s**, max **97 s** | p50 11.8 s, p90 22.2 s, max 54 s |
| Agents-tab startups > 30 s       | 10 %                                 | 5 %                               |

**Apollo's trend** (`agents_ready_seconds`, weekly):

| Week of | p50 | p90 | Max |
| --- | --- | --- | --- |
| 09-21 | 4.9 s | 18.2 s | 38 s |
| 09-28 | 5.5 s | 18.4 s | 65 s |
| 10-05 | 6.0 s | 32.6 s | 92 s |
| 10-12 | 13.4 s | **55.5 s** | 79 s |

Athena over the same weeks: p90 12–19 s.

**The cliff signature.** `tui_agent_loads.jsonl` attributes every > 37 s startup to the loader's **`disk` stage**:

| Startup | Disk stage | Agents ready |
| --- | --- | --- |
| 10-09 01:26 | 62.8 s | 73.6 s |
| 10-10 19:03 | 61.1 s | 67.4 s |
| 10-10 19:36 | 84.8 s | 91.9 s |
| 10-13 11:55 | 41.2 s | 55.6 s |
| 10-13 13:02 (your last start) | 72.0 s | 79.0 s; about 85 s wall including imports |

Mid-range startups (10–17 s) instead show `prep` 3–7 s and `apply` 2–5 s. Fast ones (4–6 s) log no slow stage at all.

The stall watchdog (`tui_stalls.jsonl`) shows only 1.5–2 s main-thread hitches during the 79 s startup. So the time was **not** spent blocking the event loop. It was spent in worker threads, which is consistent with GIL/CPU starvation (§5).

Your 13:02 TUI was also at **1.2 GB RSS** five minutes after start (370 MB at 15 s). It burned about 30 % of a core while idle, and gen-2 GC pauses ran 0.8–1.4 s (p50/p90). Athena's TUIs are larger still (about 4 GB), so this is general rather than apollo-specific, and it is outside this startup analysis.

---

## 4. Anatomy of one apollo startup

This trace is from an un-profiled A/B **base** run at load ~25. Times are relative to the first trace event, which is about 0.5 s after `AceApp` init.

```
-5.7 s  process start → CLI import 0.5 s → `from sase.ace.tui import AceApp` 5.0 s  (blank terminal)
 0.0    AceApp() 0.7 s, compose, Textual CSS/stylesheet, on_mount ≈ +3.4 s
 3.6    agents.load_from_disk (worker)  ─────────────────────────────────────────── 10.5–48 s
          dismissed_snapshot 0.3–29 s  (SQLite fetchall; see §5.3)
          index 0.6 s (Tier-1 artifact index, ~275 rows)
          decode 1.2–16.5 s (≈1.25 k records incl. workflow steps)
          normalize → AgentIdentitySnapshot.current() ≈ 7 s  (realpath storm; §5.4)
          projections 0.7–2.9 s
 4–7    deferred mount loads read Patches, then **_apply_patches() on the event loop builds the
        relation index synchronously (3.6 s)**; then fs-watcher churn re-runs Patch reloads +
        relation index back-to-back (5–6 s each) for the rest of the window
 ~13    first auto-refresh tick: axe.collect with 768 file opens / 361 run-JSON parses (5–15 s)
 +1–2   worker_prep 0.8–1.5 s → apply 1.5–2.2 s → first Agents paint
        then post-paint warmups (bead confirmation, plan previews 8–10 s, diff badges, live hints)
```

**Where wall time went in worker threads.** These are active (non-idle) samples from run 1, at about 100 Hz, so 100 samples ≈ 1 s:

| Samples | Task |
| --- | --- |
| 4382 | prompt/macro catalog build (`build_prompt_catalog_snapshot`) — mostly `importlib.metadata.entry_points()` rescans |
| 3767 | the **Agents loader** (critical path) |
| 3517 + 3158 | **Patches load + relation link index** |
| 2807 | axe status collect |
| 2782 | startup update-check toast |
| 1896 | proc-observer thread |
| ~550 each | plan-preview warmup, archive build, prompt-bar import warm, dismissed artifact-index sync, bead-cache warmup |

**Who actually held the GIL** (run 2, `--gil`; 4575 GIL samples):

| Samples | Share | Holder |
| --- | --- | --- |
| 1463 | **32 %** | Patches load + relation index |
| 378 | 8 % | main thread, AceApp lazy import |
| 162 + 73 | — | main thread, deferred mount loads + startup prepare |
| 164 | **3.6 %** | Agents loader; it mostly *waits* for the GIL |
| 127 | — | proc observer |
| 106 | — | bead warmup |
| 79 | — | axe collect |
| 70 | — | prompt catalog |
| 50 | — | update check |

The `importlib.metadata` scans account for about 69 s of wall time across threads but only about 1.3 s of GIL time. They are convoy *victims* (file I/O), not hogs.

The **main thread was busy for about 75 %** of run 1:

| Samples | Main-thread work |
| --- | --- |
| 858 | Textual compositor render |
| 555 | AceApp import |
| 510 | CSS/stylesheet apply |
| 343 | timers |
| 253 | relation-index build inside `_apply_patches` |
| 246 | `sase.ace.tui.repro.capture` lazy import (see §5.5) |
| 151 | post-update-toast import |

---

## 5. Root causes, with evidence

### 5.1 Patch reload + relation-index treadmill (largest single cause of the cliffs)

**Trigger.** `src/sase/ace/tui/actions/event_refresh/_watcher.py:83-89` schedules `_schedule_patches_async_refresh()` immediately for any "artifacts" fs event. The comment reads: *"Patch refreshes are cheap enough to keep immediate…"*.

- This path ignores whether the Artifacts/Patches tab is visible.
- It also ignores the startup window and the navigation/typing gates.
- The pending/loading guard (`patch/_loading.py:579-618`) coalesces requests, but when a reload costs 5–6 s and files change more often than that, it simply **re-runs back-to-back**.

**Cost.** Every reload calls `_build_patch_relation_index` (`patch/_loading.py:638-656`) through `_prepare_patch_load_from_disk`.

- That builds `artifact_link_edges` (`relations/artifact_links.py:150-185`), which loops over **every row** of every project's `artifact-links.json`. On apollo that is 44,344 rows (15 MB for `gh_sase-org__sase` alone).
- For each row it resolves both refs through several per-ref Rust FFI calls: `parse_link_ref`, `artifact_row_ref_lookup_keys`, `target_for_ref_kind`. All of this produces 320 edges for 284 Patches.
- Measured standalone with the same import closure:

| Host | Build #1 | Build #2 | Build #3 |
| --- | --- | --- | --- |
| apollo | 2.39 s | 2.34 s | 2.38 s |
| athena | 0.94 s | 0.76 s | 0.78 s |

- **There is no memoization across identical inputs.**

**On the event loop at startup.** `_startup_loads_index.py:37-40` reads Patches off-thread and then calls `self._apply_patches(all_cs)` on the event loop. `_apply_patches` (`patch/_loading.py:244-253`) builds the relation index synchronously. That is 2.5–3.6 s of blocked event loop in my runs, for a tab that isn't visible at startup. This is the same violation as TUI perf rules 1 and 9.

**Evidence from traces** (`relations.index.patches` spans before Agents ready):

| Run | Index builds before ready | Total build time | `load_from_disk` | Agents ready |
| --- | --- | --- | --- | --- |
| profiled run 1 | 10 | 46.7 s | 51.5 s | 63.1 s |
| profiled run 2 | 7 | 38.4 s | 44.9 s | 58.3 s |
| base A/B, fast | 1 | 3.3–3.6 s | 11.7–13.6 s | 19.7–24.9 s |
| base A/B, cliff | 8 | 38.9 s | 48.2 s | 65.6 s |
| any `norel` A/B | 0 | 0 | 10.1–14.0 s | 20.5–27.0 s |

### 5.2 The GIL convoy (why the loader is 10–500× slower than its isolated cost)

Reproduction on apollo uses apollo's real `~/.sase/dismissed_bundles/index.sqlite`, opened read-only. The query is the exact `query_summary_identities` SQL, which returns 7,313 rows. Times shown are fetch time / time for 500 `os.stat` calls.

| Competing CPU-bound Python threads | 5 ms switch interval (default) | 0.5 ms switch interval |
| --- | --- | --- |
| 0 | **0.059 s** / 0.002 s | 0.060 s / 0.003 s |
| 1 | **36.4 s** / 0.46 s | 4.7 s / 0.21 s |
| 3 | **71.8 s** / 2.56 s | 13.1 s / 0.25 s |

Athena running CPython 3.14.7 behaves the same: 0.022 s alone and 31.8 s with one competing spinner. **This is a CPython property, not an apollo bug.**

Apollo simply has more, and longer-running, CPU-bound threads overlapping the loader. Its slower cores also make each competing task run 2–3× longer.

### 5.3 Dismissed-bundle identity snapshot

`dismissed_bundle_identities_snapshot()` → `query_summary_identities()` (`dismissed_bundle_index/_api.py:273-305`) runs its query in **55 ms** standalone on apollo. Inside the profiled TUI it took **28.9 s**.

- py-spy put 1,999 samples on line 300 (`conn.execute(sql).fetchall()`).
- That is exactly the 5 ms-per-row convoy from §5.2.

The read also goes through `connection(root)` with the default `create=True`.

- `_connect` → `_ensure_schema` (`_schema.py:21-31, 57-87`) runs `BEGIN IMMEDIATE`, schema checks, `INSERT OR REPLACE` of the schema version, and `COMMIT` **on every read**.
- That is a write transaction, plus WAL fsync, on an fsync-bound disk, with a 30 s `busy_timeout`.
- `index_signature` already passes `create=False`. The identity query does not.

### 5.4 The `AgentIdentitySnapshot.current()` realpath storm on the loader thread

`normalize_loaded_agents` → `apply_status_overrides` calls `AgentIdentitySnapshot.current()` (`models/_agent_status_apply.py:509-511`). That goes through `_discover_known_owner_roots` → `_configured_agents_sidecar_paths` → `resolve_sync_targets` → `collect_repo_inventory`.

- The inventory calls `normalize_path` (`realpath`) for every workspace × linked repo × sidecar × external repo. Apollo has 45 workspace dirs; athena has 185.
- Standalone, the first call costs **0.51 s** on apollo (0.48 s on athena) and is cached afterwards.
- In the run 3 timeline it cost **7.6 s** on the loader thread. This is the unexplained "provider" time after `decode` in otherwise-healthy runs.
- Every `lstat` inside `realpath` is a GIL release, so it pays the convoy tax.
- Decode has the same pattern on a smaller scale. Per-record probes over about 1.25 k records include `cached_plan_tier → Path.resolve()`, `agent_is_reverted → is_file`, `commit_results_marker_exists → is_file`, `read_commit_results_metadata → json.load`, and `is_process_running`. The UI shows about 150 agents and 46 top-level rows.

### 5.5 Startup work that competes with first paint for no visible benefit

- **First auto-refresh tick.** It fires about 9–10 s after mount, while Agents is still loading. It runs a full `axe.collect` with **766–768 file opens and 361 run-JSON parses**, taking 5–15 s.
- **Prompt/macro catalog and plugin discovery.** `get_plugin_input_type_registry` → `_discover_macro_plugin_entry_points` → `importlib.metadata.entry_points()` scans all 94 dist-infos *twice*. On top of that, `load_plugin_catalog` and the axe composition/config-layer discovery scan again.
- **Startup update check** (`_run_startup_update_toast_check` → `compute_update_status`).
- **Post-apply warmups.** Bead confirmations, plan previews, archive build, dismissed artifact-index sync, and diff badges each run 2–10 s under contention.
- **Main-thread lazy imports.**
  - `from ...repro.capture import record_agents_tab_loader_result` (`agents/_loading_disk_full.py:271`) imports **+293 modules** (0.56 s isolated on apollo, about 2.5 s in-TUI). It does this *on the event loop, unconditionally*, even though `record_agents_tab_loader_result` is a no-op unless repro capture is enabled.
  - `_maybe_show_post_update_toast` costs another 1.5 s of main-thread import time in run 1.

### 5.6 Import time: 3× slower than athena, about half of it dataclass creation

`python -X importtime -c "from sase.ace.tui.app import AceApp"`:

| Host | Self time | Modules |
| --- | --- | --- |
| apollo | **5.65 s** | 3,433 |
| athena | 1.85 s | 3,441 |

`sase.*` modules account for 4.83 s of apollo's total. The `.pyc` files are present (5,998 `cpython-312` pycs), so this is execution cost, not compilation.

The heaviest subtrees on apollo, with athena in brackets:

| Subtree | apollo | athena |
| --- | --- | --- |
| `actions.agents._core` | 3.86 s | 1.28 s |
| `_agent_enter_action` | 1.89 s | 0.61 s |
| `_metadata_search` | 1.31 s | 0.37 s |
| `gate_turn` / `notification_gates` | 1.15 s | 0.40 s |
| `widgets.agent_detail` | 1.11 s | 0.30 s |
| `prompt_panel` | 0.94 s | 0.24 s |

cProfile of the import on apollo found **2,012 dataclasses decorated at import time, making 11,164 `_create_fn` → `exec` calls**. `dataclasses._process_class` accounts for about 4.1 of the 7.5 profiled seconds.

Python 3.13+ batches each class's methods into one `exec` (`_FuncBuilder`). On the same host, a 2,000-dataclass microbench is only about 8 % faster on 3.14 than on 3.12 (0.76 → 0.72 s on athena). So upgrading the interpreter helps a little; the 3× gap is mostly per-core speed plus contention.

---

## 6. A/B results (un-profiled, apollo, real archive)

`agents_ready_seconds` is measured from AceApp init. Add about 4–6 s of import for wall time.

- **Base:** unmodified.
- **switch:** `sys.setswitchinterval(0.001)`.
- **norel:** `_build_patch_relation_index` replaced with `lambda *a, **k: None`. This is profiling-only and changes no code in the repo.

| Variant        | n | Runs (s)                              | Mean | SD   | Host load1 |
| -------------- | - | ------------------------------------- | ---- | ---- | ---------- |
| base           | 6 | 19.7, 25.1, 34.6, 24.9, 34.5, **65.6** | 34.0 | 15.1 | 14.8–31.3  |
| switch         | 3 | 19.8, 27.9, 39.0                      | 28.9 | 7.9  | 17.9–25.4  |
| norel          | 3 | 25.4, 27.0, 26.3                      | 26.3 | 0.6  | 17.0–31.1  |
| norel + switch | 5 | 20.5, 21.7, 20.5, 20.5, 21.7          | 21.0 | 0.6  | 19.3–26.3  |

How to read this:

- Removing the relation-index treadmill eliminates the cliff and the variance. The 65.6 s base run and the 27.0 s / 26.3 s norel runs were interleaved at the same load (about 30, with 17 runners).
- A lower switch interval **by itself did not help**. The CPU hog is still there, and more frequent switching adds overhead.
- Combined with `norel`, the lower switch interval may shave a few more seconds, but n is small and host load differed. Treat that part as a hypothesis.
- Even the best variant still needs about 21 s on this host. That remainder is the §5.4/§5.5 work plus contention.

---

## 7. Things I ruled out

- **Not memory pressure:** 20 GiB available, no swap, memory PSI 0.
- **Not CPU steal:** `st` about 0.
- **Not missing bytecode:** pycs are present and `dont_write_bytecode=0`.
- **Not the artifact-index tier:** every slow startup since 10-03 was `tier1` / `artifact_index` with 50–300 index rows. Unlike September's `not machine:apollo` cliff, apollo's only Tier-2 Agents-tab startup since 09-15 was a 6.8 s one on 09-17.
- **Not the SQLite plan:** both joins are indexed (`SCAN s` + `SEARCH v USING sqlite_autoindex…`), and the query takes 55 ms.
- **Not event-loop stalls:** the watchdog saw only 1.5–2 s hitches during the slowest startups.

---

## 8. Ranked changes to consider

Ranking is by expected effect on apollo's startup, weighted by confidence and effort. Most items also help athena.

1. **Stop rebuilding the Patches relation index when nobody is looking, and never on the event loop.** *(code; highest impact; A/B-proven)*
   - In `_watcher.py`, mark Patches dirty instead of reloading when the Artifacts/Patches pane isn't visible. Reload on tab entry, the way Agents uses its gates. Also respect the startup window and NavigationGate.
   - Rate-limit visible-tab reloads to at least the last reload's duration (adaptive debounce) so they can't run back-to-back.
   - Move the startup `_apply_patches()` relation-index build in `_startup_loads_index.py:37-40` and `patch/_loading.py:244-253` into the worker, or build it lazily on first relation-rail use.
   - Expected: removes the 37–97 s cliffs and about 30 % of startup GIL time. In the A/B the mean went 34.0 s → 26.3 s and the SD went 15 s → 0.6 s.

2. **Take load off apollo while you use it interactively.** *(ops; no code; large effect on the tail)*
   - Agent `pytest -n 6/7` runs alone use 8–10 of 16 vCPUs.
   - Cap xdist workers for agents on apollo (for example `-n 2–3`), and/or lower axe `--max-agent-runners`, and/or run agent test work under `nice`/`ionice`.
   - Alternatively, `%dispatch` heavy agents to athena. Athena is idling at load 5–7 on 64 threads; apollo is your rendezvous box, not your best compute.
   - Every number in this report scales with contention: the convoy penalty grows with the number of busy threads (§5.2), and per-thread speed falls as runnable tasks exceed 16. For reference, apollo's weekly p50 was 4.9–6.0 s in late September. I don't have load data for those weeks.

3. **Make the relation-edge projection cheap everywhere.** *(code, sase-core boundary; medium–high)*
   - Memoize `_build_patch_relation_index` on (link-aggregate signatures, Patch-set identity/signature). Builds #2 and #3 repeat identical 2.4 s work today.
   - Push `artifact_link_edges` into sase-core as one batched call, or keep an inverted index keyed by ref lookup key. Then a Patches load resolves only the links that touch its 284 known targets, not all 44 k rows with per-row FFI.
   - Expected: 2.4 s → well under 0.1 s on unchanged inputs (0.8 s → ~0 on athena).

4. **Push non-critical startup work behind Agents first paint.** *(code; medium–high; general)*
   - Delay the first auto-refresh tick (axe.collect with 768 opens), the prompt/macro catalog and plugin entry-point scans, the update check, and the warmups until `agents_ready` plus a quiet period. This applies TUI perf rule 9: "don't add work before the startup stopwatch ends".
   - Gate `from ...repro.capture import …` on the capture-enabled check, and keep the post-update-toast import off the event loop.
   - Cache `importlib.metadata.entry_points()` once per process. It is currently scanned 3–4 times.

5. **Remove GIL-releasing syscall storms from the Agents critical path.** *(code; medium; general)*
   - Warm `AgentIdentitySnapshot.current()` off the critical path, or cache it on disk keyed by config token / workspace-registry mtime. Also stop `realpath`-ing every workspace×repo pair in `collect_repo_inventory` (7.6 s in-TUI vs 0.5 s isolated).
   - Fetch dismissed identities through Rust (one `allow_threads`) or from a cached materialization keyed by the index signature, instead of a 7 k-row Python `fetchall`.
   - Open the dismissed index with `create=False` for pure reads; today every read commits a write transaction.
   - Batch the per-record decode probes (`Path.resolve`, marker `is_file`s, commit-metadata JSON) into the Rust scan, or memoize them per artifact dir by mtime.

6. **Reinstall apollo's sase tool env on Python 3.14.** *(ops; low effort; modest)*
   - It currently uses Ubuntu's system 3.12.3; athena uses uv-managed 3.14.7.
   - Run `just install-dev --python 3.14` from the apollo checkout yourself. Global installs are human-only, and it will rebuild `sase-core-rs` for cp314.
   - Expected: about 15–20 % faster pure-Python loops and a slightly cheaper dataclass import. Roughly 0.5–1 s off imports and proportional gains elsewhere. It does **not** fix the convoy.

7. **Fix the `sase tool wait` / `_join` poll loop.** *(code; host-health)*
   - Each waiter reconciles the whole unsettled-run ledger every ≤ 0.5 s. That costs about 0.2–0.5 core, about 490 write syscalls/s, and about 2 MB/s of churn per waiter.
   - Back off to a multi-second maximum, skip reconcile writes when nothing changed, or wait on a ledger change token. This reduces the fsync/IO pressure every apollo process feels.

8. **Consider a faster droplet class for apollo.** *(ops/$; medium)*
   - Most of the 3× import gap and the 2–3× per-thread gap is the 2.7 GHz Skylake-SP guest.
   - A newer premium/CPU-optimized class (recent Xeon or EPYC) would likely cut every CPU-bound stage by 1.3–2×. Combine with #2 if apollo must keep hosting many agents.

9. **Keep trimming the TUI import closure.** *(code; about 1–2 s on apollo)*
   - Defer the heaviest subtrees from first paint: `_agent_enter_action`, `_metadata_search`, `gate_turn`/`notification_gates`, `agent_detail`/`llm_calls_panel`, `prompt_panel`.
   - Watch the dataclass count on the startup path. 2,012 decorations cost about half of the import time on 3.12.
   - The existing `test_app_import_budget.py` ratchet is the right mechanism.

10. **Make cliffs attributable from telemetry alone.** *(observability; small)*
    - Add `load1`, agent-runner count, relation-index build count and seconds before ready, and the loader's per-stage split (dismissed / index / decode / normalize) to `tui_startup.jsonl`.
    - Today `tui_agent_loads.jsonl` only says "disk 72 s" and below-threshold startups are censored. Both of today's root causes needed py-spy to find.

11. **Longer term: get the loader out from under the GIL.** *(design)*
    - Run the startup Agents load as a single Rust call that releases the GIL once, or in a helper process. Free-threaded CPython (3.14t) is the eventual version of this.
    - Any Python-level critical path with thousands of tiny GIL releases will be convoy-prone while the TUI keeps 20+ worker threads busy.

**Not recommended on its own:** lowering `sys.setswitchinterval`. It made the A/B worse or equal without #1. Revisit it only after the CPU hogs are gone.

---

## Appendix A — Reproduce

On apollo (uses the tool env Python; py-spy must be the **parent** because `ptrace_scope=1`):

```bash
# traced + profiled startup in a private tmux server (quit with q after the stopwatch stops)
tmux -L prof new-session -d -s p -x 200 -y 55 \
  "env SASE_TUI_TRACE=1 SASE_TUI_TRACE_PATH=/tmp/trace.jsonl SASE_TUI_LOADER_LOG_THRESHOLD_SECONDS=0.05 \
   ~/.local/bin/py-spy record --gil --threads --nonblocking -r 100 -f raw -o /tmp/spy.txt -- \
   ~/.local/share/uv/tools/sase/bin/python3 -m sase tui -x -t agents"

# relation-index treadmill check
jq -c 'select(.span=="relations.index.patches" or (.span // "" | startswith("agents.load_from_disk")))
       | {span, duration_ms, count}' /tmp/trace.jsonl

# import split
~/.local/share/uv/tools/sase/bin/python3 -X importtime -c "from sase.ace.tui.app import AceApp" 2>&1 | sort -t'|' -k2 -n | tail
```

GIL-convoy reproduction script (read-only against the real dismissed index): `/tmp/convoy_cld.py` on apollo. Benchmarks: `/tmp/relbench_cld.py`, `/tmp/identbench_cld.py`, `/tmp/dcbench_cld.py`. Raw captures: `/tmp/cld_prof/` on apollo (about 18 MB; safe to delete).

## Appendix B — Caveats

- **Contention and observer effects.** Apollo's load drifted from 13 to 31 during the hour of measurement, and other swarm researchers may have been profiling it too. Absolute numbers are noisy; the A/B was interleaved to control for this. py-spy at 100 Hz on about 30 threads adds overhead, so the profiled runs (58–63 s) are slower than un-profiled base runs. They were used for *attribution*, while the A/B was used for *magnitude*.
- **Sample sizes.** The `switch` and `norel` arms are n = 3. The robust conclusion is about the relation index, which held at n = 6 vs n = 8 across all loads.
- **Not changed.** I did not modify sase code, config, or apollo's installed environment.
