# Apollo TUI startup profile (researcher grk)

**Question.** Why does `sase tui` take a very long time to start on apollo, and what should change — on that machine, in sase, or both?

**Investigator.** Independent swarm researcher `grk`. Measurements were taken over SSH from athena on 2026-10-13 13:08–13:20 UTC. The live TUI on apollo was left running. Nothing on apollo was restarted, killed, or reconfigured.

**Headline.** Apollo's TUI is not waiting on a huge SQLite index. A quiet process on that same box loads the Agents snapshot in **1.5 s**. The interactive TUI's latest startups took **55–79 s** to become Agents-ready because the 16-vCPU droplet is saturated, the TUI starts competing index/GIL work 3 s after mount, and auto-refresh then keeps doing full loads. Import of `AceApp` is a second, quieter tax: **5.7 s** on apollo versus **1.9 s** on athena for the same ~3500 modules.

---

## 1. Method

- Host inventory over `ssh apollo` (`lscpu`, `free`, `df`, `iostat`, `uptime`, process table, `sase version`).
- Durable TUI telemetry already on disk: `~/.sase/logs/tui_startup.jsonl` (493 records), `tui_agent_loads.jsonl`, `tui_stalls.jsonl`.
- Isolated microbenchmarks in apollo's installed uv Python, without attaching to the live TUI:
  - cached artifact-index query
  - `get_all_project_files` / `find_all_patches_cached` / decode / `load_tiered_agents`
  - `importlib.import_module("sase.ace.tui.app")`
- Same loader and import probes on athena (Threadripper workstation running the same sase revision) as a control.
- Code path review of `StartupLoadsMixin`, `AgentLoadingDiskFullMixin`, `query_artifact_index_for_loader`, and `docs/perf_runbook.md`.
- Prior durable research `research:202610/apollo_high_cpu_gateway_snapshot_stampede.md` (2026-10-09) for the gateway/index-lock failure mode. That outage is **not** the live state today; it is the blast radius if the gateway tips over again.

`sase -p tui` on apollo is the global `--print-command` flag plus the `tui` subcommand. It is not pyinstrument.

---

## 2. Machine profile: apollo versus athena

| Signal | apollo (TUI host) | athena (control) |
| --- | --- | --- |
| Hardware | DigitalOcean KVM, Intel Xeon Platinum 8168 @ 2.70 GHz, **16 vCPU**, 1 thread/core | AMD Ryzen Threadripper 3970X, **32 cores / 64 threads**, boost to 4.55 GHz |
| RAM | 31 GiB, **no swap** | 62 GiB |
| Disk | 200 G virtio `vda` ext4, 142 G / 193 G used (74%), reports `rotational=1` | local NVMe-class workstation disk |
| OS | Ubuntu, kernel 6.8.0-146-generic, up 4 d | Debian 6.12, up 4 d |
| Python | 3.12.3 | **3.14.7** |
| sase | `0.17.1+2496.g010185b0c` editable from `~/projects/github/sase-org/sase` | same revision |
| sase-core-rs | `0.39.0+3.g2fc3d7754` | same |
| Load during this work | **8.9 → 14.2** (1/5/15 min around 12–14) | ~6 on 64 threads |
| Artifact index | 83 MB, 3,353 rows, 9,668 dismissed | 284 MB, 18,157 rows, 71,021 dismissed |
| Agent dirs on disk | sase sidecar 16,402; bob-cli 3,738 | larger archive, still faster |
| Workspaces | 20 `sase_*` clones under `~/.local/state/sase` | many more, more RAM/CPU to absorb them |

During the 13:08 snapshot apollo was not idle:

- `rustc --crate-name sase_core_rs` at ~98–145% CPU, **thin LTO, `codegen-units=1`**, writing into `~/.cache/sase/tmp/cargo-targets/gh_sase-org__sase-ws10-…`
- two `tools/check_feature_flags` Python processes at ~99% each
- a parallel bob-cli debug `rustc` fan-out
- 9 `run_agent_runner.py` processes
- `sase_gateway` at ~13% CPU, 18 threads, 11 fds (healthy; see §7)
- the interactive TUI itself at **76–88% CPU**, 30 threads, **1.2–1.38 GB RSS**

CPU steal was 0%. iowait was 0.5–2.4%. This is a **CPU / lock / GIL** problem, not a dying disk.

`/home/bryan/.cache/sase` is 24 G, almost all `tmp/`. `~/.local/state/sase` is 45 G of workspace clones. Root has 52 G free, so the box is not full, but scratch and clones are the bulk of the 142 G used.

---

## 3. What “startup” actually measures

The visible stopwatch in the keybinding footer is **not** process-start → first paint. `StartupTelemetryMixin` (`src/sase/ace/tui/actions/_startup_telemetry.py`) records:

| Field | Meaning | Latest apollo session (pid 3192631, 13:02 UTC) |
| --- | --- | --- |
| `interpreter_cli_import_seconds` | OS start → just before `AceApp` import | 0.53 s |
| `app_module_import_seconds` | `from sase.ace.tui import AceApp` | **5.29 s** |
| `app_construct_seconds` | `AceApp()` | 0.70 s |
| `compose_seconds` | Textual `compose()` | 0.029 s |
| `process_start_to_on_mount_seconds` | AceApp-init stamp → `on_mount` (historical field) | 3.16 s |
| `on_mount_to_first_paint_seconds` | mount → first refresh callback | 0.81 s |
| `agents_ready_seconds` | process start → Agents first load | **78.95 s** |
| `axe_ready_seconds` | process start → Services first load | 10.91 s |
| `visible_ready_seconds` | mount → initially visible tab ready | **75.79 s** |
| `all_surfaces_ready_seconds` | mount → **both** Agents and Services ready (this is the badge) | **75.79 s** |

Startup sequence in code (`_startup_mount.py`, `_startup_loads_core.py`):

1. Synchronous `on_mount` wires widgets and paints a loading spinner. Slow disk is deferred.
2. `call_after_refresh` starts post-mount work. Visible surface (Agents) goes first.
3. `_run_agent_index_startup_prepare_and_refresh` cheaply checks index schema, then runs the ordinary async Agents refresh (cached Tier-1 index when the schema is current).
4. A **3.0 s fallback timer** (`_STARTUP_DEFERRED_FALLBACK_SECONDS`) releases every hidden-surface and maintenance task if visible-ready has not happened yet: Services/axe, deferred mount-state, dismissed-index sync, monitor reconcile, artifact-index maintenance.
5. The stopwatch ends only when **both** `_agents_first_load_done` and `_axe_first_load_done` are true.

That 3 s fallback is the right idea when Agents is fast. On apollo today Agents is not fast, so at t=3 s the TUI starts a second wave of index and GIL work while the first Agents load is still in `asyncio.to_thread`.

---

## 4. Telemetry: this is a tail event on a busy host, not a 5 s baseline

### 4.1 Historical apollo startups (`tui_startup.jsonl`, n=493)

Excluding the broken `interpreter_cli_import_seconds` values left by in-process exec restarts (p50 of 6123 s all-time — ignore those):

| Metric | min | p50 | p90 | p95 | max |
| --- | --- | --- | --- | --- | --- |
| `app_module_import_seconds` | 2.94 | 3.76 | 5.11 | 5.46 | 8.97 |
| `agents_ready_seconds` | 2.52 | **5.89** | 18.2 | 26.7 | 91.9 |
| `axe_ready_seconds` | 1.89 | **8.41** | 12.8 | 14.1 | 19.6 |
| `visible_ready_seconds` | 0.48 | 3.21 | 15.5 | 24.3 | 89.2 |
| `all_surfaces_ready_seconds` | 1.43 | **7.96** | 15.5 | 24.3 | 89.2 |

Typical apollo startup, historically: **~6 s Agents, ~8 s Services, ~8 s stopwatch**. The badge is often gated on Services even when Agents was ready earlier (`visible_ready` p50 3.2 s vs `all_surfaces_ready` p50 8.0 s).

### 4.2 2026-10-13 on apollo (six recorded sessions)

| UTC | pid | `agents_ready` | `visible_ready` | import | rows (shown / index) |
| --- | --- | --- | --- | --- | --- |
| 08:12 | 2217726 | 11.0 s | 8.2 s | 4.08 s | 36 / 235 |
| 08:21 | 2217726 | 11.3 s | 8.8 s | 4.61 s | 36 / 236 |
| 10:16 | 2217726 | 14.5 s | 11.8 s | 3.97 s | 39 / 243 |
| 11:55 | 2217726 | **55.5 s** | 52.4 s | 5.12 s | 42 / 238 |
| 13:02 | 3192631 | **79.0 s** | 75.8 s | 5.29 s | 45 / 268 |
| 13:13 | 3263463 | **63.1 s** | 59.1 s | 5.12 s | 45 / 270 |

Morning sessions on this host are already slower than the all-time median (11–15 s vs 6 s). From 11:55 onward they fall off a cliff, in the same window as release `rustc` of `sase_core_rs` and a dense agent swarm.

Worst `agents_ready` in the whole log is 91.9 s (2026-10-10 19:36). Today's 79 s is the second-worst. The 2026-10-09 01:26 session (73.6 s) sits inside the gateway-stampede window documented in §7.

Almost every record is `tier1` / `artifact_index`. The slow path is **not** a silent fallback to a 16 k-directory source scan. `artifact_source=source_scan` is only 42 of 493 historical records.

### 4.3 Matching slow-load rows (`tui_agent_loads.jsonl`)

The 13:02 session (pid 3192631) logged:

| Time | source | kind | disk | prep | apply | `agents` field |
| --- | --- | --- | --- | --- | --- | --- |
| 13:02:12 | `startup` | full | **72.05 s** | 0.71 s | 0.64 s | **955** |
| 13:03:29 | `tier1_index_revalidate` | full | **69.04 s** | 3.07 s | 1.25 s | — |
| 13:04:30 | `notification` | delta | 54.4 s | 3.35 s | 1.03 s | — |
| 13:04:45 | `dismissed_index_sync` | full | 11.6 s | 2.81 s | 0.59 s | — |
| then | `auto_refresh` / `inflight_poll` / `watcher` | full or delta | 2–29 s | 1.7–4.9 s | 0.5–2.2 s | — |

`load_kind=full` here is the TUI's coarse counter (not “Tier 2 source scan”). The startup row's `agents: 955` is `len(all_agents)` after disk decode, before the inbox filter that leaves 45 visible rows.

Oct 13 as a whole: **230 slow loads** (≥2 s). By source: `inflight_poll` 87, `auto_refresh` 60, `tier1_index_revalidate` 21, `watcher` 20, `notification` 20, `launch` 10, `startup` 8. The TUI does not go quiet after first paint.

`tui.log` has repeated screenshot failures of the form `pending_workers=['startup-visible:agents']`. Capture times out because the Agents first-load worker is still running. That is an independent witness of the same stall.

### 4.4 Athena control (same sase SHA, n=1944 startup records)

| Metric | p50 | p90 | last few today |
| --- | --- | --- | --- |
| import | 2.01 s | 4.17 s | 1.61–1.92 s |
| `agents_ready` | **4.55 s** | 10.6 s | **3.0–5.0 s** |
| `axe_ready` | **3.29 s** | 7.14 s | 8.3–9.2 s |
| `all_surfaces_ready` | **3.94 s** | 9.37 s | 7.0–7.9 s |

Athena's index is **3.4× larger** (284 MB, 18 k rows) and its visible inbox is similar (21–23 rows). It still starts in ~5 s Agents-ready while apollo's quiet median is ~6 s and today's busy sessions are 55–79 s.

---

## 5. Isolated probes: the loader is fine; the process is not

Run on apollo at 13:16 UTC, load average ~14, **without** going through the live TUI:

| Step | apollo | athena |
| --- | --- | --- |
| `import sase.ace.tui.app` | **5.74 s wall / 6.61 s**, 3493 modules, Python 3.12 | **1.87 s**, 3502 modules, Python 3.14 |
| `sase version` (CLI import) | 0.92 s | — |
| cached index query (273 records) | 1.37 s cold, **0.39 s** warm | — |
| `get_all_project_files` | 5 files, 1 ms | 10 files, 1 ms |
| `find_all_patches_cached` | 284 patches, 45 ms | 315 patches, 25 ms |
| dismissed-bundle snapshot | 7,313 ids, 151 ms | — |
| Tier-1 cached snapshot | 273 records, 349 ms | 434 records, 282 ms |
| decode from snapshot | 457 agents + **807 workflow steps**, 864 ms | 643 + 869, 354 ms |
| `load_tiered_agents(...)` | **969 agents, 1.54 s** | 822 agents, **0.96 s** |

So on apollo, under the same load average that stretched the interactive TUI to 79 s:

- the Rust/SQLite index answers a cached Agents query in well under a second once warm
- the full Python `load_tiered_agents` path is **1.5 s**
- import of the TUI app module is **5.7 s** and is the largest *uncontended* startup term

The 72 s `disk` stage inside the live TUI is therefore **queueing**: the same function, in a process that already has ~30 Python threads, overlapping `to_thread` workers, gen-2 GC pauses of 1.3 s, and an index lock shared with revalidate / dismissed-sync / gateway / other agents.

`_load_agents_from_all_sources` still hydrates **every** artifact-backed row in the snapshot plus RUNNING-field rows plus every Patch's HOOKS / MENTORS / COMMENTS. First paint then throws most of that away (955 decoded → 45 inbox rows). That extra decode is ~0.9 s when the GIL is free and much more when it is not.

---

## 6. Why the live TUI amplifies 1.5 s into ~70 s

Several mechanisms stack. None of them is “the SQLite file is 83 MB.”

### 6.1 Host saturation

16 vCPUs, load 9–14, plus a release `rustc` of `sase_core_rs` with `-C lto=thin -C codegen-units=1`. That compile is a known memory-bandwidth hog. Two `check_feature_flags` interpreters at 99% and a bob-cli rustc fan-out sat on the same box. The TUI's worker thread is CFS-scheduled against all of that.

Athena absorbs a similar agent swarm on 64 threads. Apollo cannot.

### 6.2 The 3 s deferred-load fallback fights the visible load

`_release_startup_deferred_loads` starts Services, dismissed-index sync, monitor reconcile, and index maintenance if Agents is not ready by 3 s. On a healthy host Agents *is* ready by then. On apollo it is not, so the fallback is guaranteed to fire during the expensive load.

The 13:02 trace is the textbook overlap: startup disk 72 s, then an immediate `tier1_index_revalidate` of 69 s, a notification delta of 54 s, and `dismissed_index_sync` of 12 s. Those are not independent 70 s algorithms. They are several writers/readers serialized on one index plus the GIL.

### 6.3 Inotify budget of 4096 versus 20 k artifact dirs

`src/sase/ace/tui/util/fs_watcher.py` caps watches at `MAX_INOTIFY_WATCHES = 4096`. Apollo has ~20 k agent artifact directories. Old dirs sit outside the watch set, so marker changes miss the watcher and the tab falls back to revalidation and `auto_refresh` full loads (`infer_broad_load_fallback_reason` maps `auto_refresh` to `unknown_watcher_path`). That matches today's 60 slow `auto_refresh` rows and 21 `tier1_index_revalidate` rows.

`docs/perf_runbook.md` already names this: old artifact directories are outside the startup inotify budget; their changes arrive through revalidation, not watcher deltas.

### 6.4 GIL + GC inside the TUI process

Pid 3192631 after ~15 min:

- 30 threads, 76% CPU, 1.38 GB RSS
- heartbeat window 300 s: **13 loop hitches / 36 s**, **11 pump hitches / 28 s**
- gen-2 GC: 5 collections, **max 1.32 s**, total 5.66 s
- `gc_freeze_count` 350,893 (idle-GC freeze policy is active; freeze is not free)
- 17 `tui_gc_pause` rows for this pid, 6.4 s summed, max 1.30 s

Disk decode runs in `asyncio.to_thread`. Every other `to_thread` worker and the UI thread compete for the same GIL. A 0.9 s decode plus a 1.3 s gen-2 pause plus lock wait is enough to turn “1.5 s” into “a minute” when it happens several times in a row.

### 6.5 Import tax is real even on a quiet interpreter

`tests/ace/tui/test_app_import_budget.py` caps `import sase.ace.tui.app` at **5.0 s process-time** and 3513 modules. Apollo measured **5.74 s wall, 6.14 s user, 3493 modules** — over the budget on this CPU even with no TUI running. Athena: 1.87 s for 3502 modules.

Two compounding differences: Xeon 8168 @ 2.7 GHz KVM versus Threadripper 3970X, and **Python 3.12.3 versus 3.14.7**. The TUI is an editable checkout (`sase.__file__` → `~/projects/github/sase-org/sase/src/sase/__init__.py`), so every startup pays source-tree import, not a frozen wheel.

On a *healthy* apollo session (11 s Agents-ready) import is already ~40% of the wait. On today's 79 s session it is only ~7%, because the loader queue dominates.

### 6.6 Stopwatch semantics make Services count even when you are on Agents

`all_surfaces_ready_seconds` is what the badge uses. Historical p50: Agents 5.9 s, Services 8.4 s, badge 8.0 s. `visible_ready_seconds` is recorded and unused. When Agents is the disaster path, both numbers match. When Agents is fine, the user still stares at a spinner until axe header-only status returns.

Axe first load is already supposed to be header-only (`_run_axe_startup_init_body`). On apollo it still takes ~11 s from process start (~8 s after mount). That is the floor of the badge on this machine until the stopwatch is retargeted.

---

## 7. Related failure mode: gateway snapshot stampede (currently idle)

Prior research on 2026-10-09 (`research:202610/apollo_high_cpu_gateway_snapshot_stampede.md`) found `sase_gateway` using 7–11 of 16 cores, ~500 threads, ~1000 SQLite fds at `RLIMIT_NOFILE=1024`, 8–12 GB RSS, WAL of ~5 GB, load 150–560, and OOM kills of `sase.service`. Cause: a 4 s `tokio::time::timeout` around `spawn_blocking` that does not cancel the build, so timed-out rebuilds pile up. Athena's TUI fleet poller was the client that kept it tipped.

**Today (13:14 UTC) the gateway is healthy:** pid 2924239, 18 threads, 11 fds, 0 index fds, 115 MB RSS, ~13% CPU. WAL files were not present next to the 83 MB sqlite (checkpointed). `sase machine status` from athena earlier in the morning reported version skew (`sase-gateway` 0.39.0 vs local `sase-core-rs` 0.38.0) and later a transient `transport_failed`; SSH and hello recovered.

This is not the 79 s startup. It is the reason apollo TUI startup *can* look like 70 s plus a dead machine if the gateway tips again. The 2026-10-09 01:26 startup (73.6 s) is likely that mix.

---

## 8. What I did not measure

- No py-spy / perf on the live TUI (`py-spy` missing; `perf_event_paranoid` / `ptrace_scope` blocked this class of work on 2026-10-09).
- No `SASE_TUI_TRACE=1` recapture of the 13:02 session (that file on apollo is stale, 2026-10-10).
- No headless `sase tui` of my own: the user already had a TUI on pts/0 / tmux `%29`, and another process on the box was constructing `AceApp` under `run_test()`.
- Sub-stage split of the in-process 72 s `disk` timer (index vs decode vs patch fields vs lock wait) is inferred from isolated probes plus overlap in `tui_agent_loads.jsonl`. Adding those fields to the slow-load record is recommendation 14.

---

## 9. Ranked changes

Highest expected reduction in *apollo-perceived* TUI startup first. “Code” vs “ops” is labeled. Effort is relative.

### 1. Keep interactive TUI off a saturated 16-vCPU droplet (ops, immediate)

Do not expect a 5 s Agents-ready TUI on apollo while a thin-LTO `sase_core_rs` compile, feature-flag checkers, and ~9 agent runners share 16 vCPUs. Isolated loader 1.5 s → in-TUI 72 s is the proof.

Practical controls:

- Nice / cgroup the `just rust-install` / maturin release builds (`codegen-units=1` LTO).
- Cap concurrent agent runners on apollo below what athena uses.
- Use athena (or a bigger droplet) as the interactive TUI host when a swarm is running on apollo.

This is the only change that would have turned today's 13:02 session into a ~12 s start without shipping code.

### 2. Do not release deferred startup work at 3 s if Agents is still loading (code, P0)

`_STARTUP_DEFERRED_FALLBACK_SECONDS = 3.0` plus `_release_startup_deferred_loads` starts axe, dismissed-index sync, and index maintenance while the visible load still holds the GIL and the index lock.

Change the fallback to fire on `agents_ready` **or** a much larger bound (30–60 s), and **never** start `dismissed_index_sync` / `tier1_index_revalidate` until the startup Agents load has finished. Keep the “user switched to Services” fast-path (`_maybe_start_startup_surface_for_tab`).

Expected effect on apollo-busy: cut the 72 s + 69 s + 54 s pile-up down toward a single ~few-second load.

### 3. Stop treating auto-refresh as a full-history-class load (code, P0)

Today: 60 slow `auto_refresh` full loads on Oct 13, mapped to `unknown_watcher_path`. After startup the TUI stays at 76% CPU with 2–18 s disk stages every tick.

Honor `ace_refresh_tokens` (already the default in `tui_perf.md`): stat-only change tokens, reload only drifted surfaces. If the inotify set cannot cover the archive, **do not** escalate every 10 s tick to `load_kind=full`. Revalidate on the long sanity interval (default 300 s) or on an explicit Refresh-panel action.

This is the difference between “slow to open” and “slow forever.”

### 4. Raise or shard the 4096 inotify cap, or watch only the hot prefix (code, P0)

16 k+ artifact dirs and `MAX_INOTIFY_WATCHES = 4096` guarantee missed events. Options, in order of preference:

- Watch the index file + a bounded “active / recent” directory set; treat the rest as index-driven.
- Raise the cap only after `sase doctor` confirms `fs.inotify.max_user_watches`.
- Compact / archive agent artifacts so the live tree fits the budget.

Without this, recommendation 3 has to fight a constant stream of “maybe something changed.”

### 5. First paint should not decode 800+ workflow steps (code, P1)

Isolated decode produced 457 agents + 807 workflow steps to show 45 inbox rows. Skip `load_workflow_agent_steps_from_snapshot` (and Patch HOOKS/MENTORS/COMMENTS) until after `visible_ready`, matching the existing “bounded first window” rule in `tui_perf.md` §9.

Cheap on a quiet host (~0.5 s). On a GIL-saturated host it is one of the things that inflates `disk` from 1.5 s toward tens of seconds.

### 6. Single-flight the artifact index in the TUI process (code, P1)

Startup, revalidate, dismissed-sync, notification deltas, and inflight_poll all hit `~/.sase/agent_artifact_index.sqlite`. The 50 ms “lock busy → source scan” path is the *other* cliff (`docs/perf_runbook.md` still records it). Cached queries that *wait* on a writer show up as 50–70 s `disk` with `artifact_source=artifact_index`.

One in-flight index operation per process, queued freshness (`cached` can share a result; `revalidate` coalesces). This is the Python-side analogue of the gateway single-flight fix in §7.

### 7. Cut `AceApp` import below 2 s on apollo-class CPUs (code, P1)

3493 modules, 5.7 s on Xeon 8168 / Python 3.12, 1.9 s on Threadripper / Python 3.14. The import-budget test is already at its 5.0 s process-time cap.

- Keep deferring (`TYPE_CHECKING`, function-local imports); the ratchet in `test_app_import_budget.py` is the guard.
- Ship a wheel on apollo instead of an editable tree for the interactive TUI.
- Move apollo's uv tool to Python 3.14, matching athena. That is a one-line ops win for import and GC.

This dominates *quiet* startup. It does not fix the 79 s busy case by itself.

### 8. Drive the visible stopwatch from `visible_ready_seconds` (code, P2)

The field has been recorded for this reason. Historical p50 badge is Services-gated (~8 s) while Agents was ready in ~3 s of mount time. Changing the badge does not make Agents faster; it stops lying about which surface the user is waiting on.

### 9. Keep the gateway stampede fix, and contain the blast radius (code + ops, P1)

Confirm `FleetReadService` single-flight / back-off / `Cached` request path from the 2026-10-09 report is actually in `sase-core` 0.39.0. Add `PRAGMA journal_size_limit` and a WAL checkpoint threshold. Run `sase_gateway` under `MemoryMax` / CPU quota so a recurrence cannot OOM `sase.service` or stall the TUI's index.

Do **not** “fix slowness” by restarting the gateway. Restarts re-tipped within a minute in that incident.

### 10. GC / heap: keep gen-2 off the input path (code, P2)

This pid's gen-2 max is 1.32 s with policy `raised`. Combined with 1.38 GB RSS that is enough to miss keypresses (`last_action=a` on every hitch). Follow the existing idle-GC / `gc.freeze` work (`tui_freeze_gc_heap_bloat` research, `install_gc_policy`). Do not freeze less if that reintroduces the 13 s glob freeze from `tui_perf.md` rule 8; do keep gen-2 away from the first-load window.

### 11. SQLite hygiene (ops, P2)

83 MB with **8,965 freelist pages** (~35 MB of dead space), 9,668 dismissed rows. Isolated query is already 0.4 s warm, so VACUUM will not move the 79 s needle. Still worth `journal_size_limit`, periodic `wal_checkpoint(TRUNCATE)` after gateway work, and not leaving a multi-GB WAL next time.

### 12. Add swap or a userspace memory cap (ops, P2)

31 GiB and **zero swap**. The Oct 9 gateway run hit 8–12 GB RSS and OOM-killed `sase.service`. A modest swap file (8–16 G) plus cgroup limits on gateway/rustc is safer than hoping RSS stays at 1.4 GB.

### 13. Instrument the `disk` stage (code, P2)

`tui_agent_load_slow` only records `disk` / `prep` / `apply`. Split `disk` into `index_query`, `decode`, `running_field`, `patches`, `lock_wait_s`, `index_error`. Today's 72 s row cannot distinguish lock wait from decode without a second isolated probe. One extra object in that JSONL would have made this report a 10-minute job.

### 14. Align fleet Python and restart the target gateway after skew (ops, P3)

Athena talks to apollo's gateway across a 0.38 vs 0.39 `sase-core-rs` skew (observed this morning). Harmless when hello succeeds; expensive when federation retries. After deploying recommendation 9, restart the gateway **once** under low TUI polling, not in a loop.

### 15. Screenshot / remote-drive timeouts (code, P3)

`sase screenshot --host apollo` currently dies waiting on `startup-visible:agents`. Either wait on `visible_ready` with a 90 s budget on remote hosts, or capture the loading frame and say so. This is a diagnostic of (2)+(3), not a startup fix.

---

## 10. Suggested order of work

If the goal is “apollo TUI opens in under 15 s while a swarm is running”:

1. Ops: cgroup/nice LTO rustc; fewer parallel runners (rec 1).
2. Code: hold deferred startup + revalidate until Agents ready (rec 2, 6).
3. Code: tokenized auto-refresh + inotify hot-prefix (rec 3, 4).
4. Code: slimmer first-paint decode (rec 5).
5. Import + Python 3.14 + stopwatch retarget (rec 7, 8).
6. Gateway containment so Oct 9 cannot repeat (rec 9, 12).

If the goal is “quiet apollo matches athena (~5 s Agents-ready)”:

- Rec 7 (import) and rec 8 (badge) are enough for the median historical session.
- Rec 5 is polish.
- Rec 1 still matters whenever someone types `sase tui` in the middle of `just rust-install`.

---

## 11. Sources

- apollo live probes, 2026-10-13 13:08–13:20 UTC, `ssh apollo`.
- `~/.sase/logs/tui_startup.jsonl` (493 records), `tui_agent_loads.jsonl`, `tui_stalls.jsonl`, `tui.log` on apollo.
- athena `~/.sase/logs/tui_startup.jsonl` (1944 records) and isolated `load_tiered_agents` / import.
- `src/sase/ace/tui/actions/_startup_loads_core.py`, `_startup_loads_index.py`, `_startup_telemetry.py`, `_startup_mount.py`
- `src/sase/ace/tui/actions/agents/_loading_disk_full.py`, `models/agent_loader.py`, `models/_agent_loader_artifacts.py`
- `src/sase/ace/tui/util/fs_watcher.py` (`MAX_INOTIFY_WATCHES = 4096`)
- `tests/ace/tui/test_app_import_budget.py`, `docs/perf_runbook.md`, `sase/memory/tui_perf.md`
- `research:202610/apollo_high_cpu_gateway_snapshot_stampede.md`
