# Apollo high CPU (2026-10-09): `sase_gateway` fleet-snapshot stampede

**Investigation window:** 2026-10-09 12:41–13:02 UTC. Bryan's local time is EDT (UTC−4); all
times below are UTC unless marked EDT. Every probe was read-only except one extra artifact-index
query (§5.3), and nothing on apollo was changed. apollo was restarted twice during the
investigation by something other than this research: a `sase.service` restart at 12:47:59 and
a full reboot at about 12:54. Both turned out to be useful natural experiments.

## TL;DR

- **The CPU hog is the `sase_gateway` service proc**, not agents. In every sample it used
  **6.6–10.9 of apollo's 16 cores** by itself. Roughly **60% of that was kernel time**. It
  held **~500 threads**, **~1,000 open SQLite handles** on `~/.sase/agent_artifact_index.sqlite`
  (1,023 fds against a 1,024 soft limit), and **8–12 GB RSS**. The 1-minute load average was
  **~150–180**.
- **This is not "the last few minutes."** It started around **2026-10-09 00:00 UTC** (Oct 8
  20:00 EDT) and has run continuously since:
  - Kernel CPU went from 1–9% before to 25–57% after.
  - Load peaked at **563** at 03:50.
  - The 01:26→12:19 service run alone burned **89.6 CPU-hours** (≈8.2 cores).
  - `sase.service` had **two OOM kills** (02:46, 04:20).
- **Mechanism: a stampede of uncancellable snapshot rebuilds.** `FleetReadService` wraps each
  fleet snapshot rebuild (`spawn_blocking(build_snapshot_blocking)`) in a **4-second
  `tokio::time::timeout`**. When a rebuild takes longer than 4 s:
  1. The timeout drops only the join handle. The blocking build keeps running.
  2. The refresh lock is released, so the next request starts another build.
  3. A build that finishes late is discarded and never fills the cache.
  4. `retain_previous_or_error` keeps the old `build_instant`, so every later request is still
     a cache miss.

  Each orphaned build holds its own read-write SQLite connection and does `Revalidate` work.
  Builds pile up at **~50 per minute** until tokio's default **512-thread blocking pool** is
  full. CPU contention then makes every build slower still, so the gateway never recovers.
- **The client keeping it alive is athena's TUI.** athena's `sase_federation_worker` polls
  apollo's gateway through `tailscale serve` on every Agents-tab refresh (about every 7 s,
  with up to ~18 calls per refresh). It has no per-host in-flight dedup and no back-off, and it
  respawns the worker and retries immediately after an IPC timeout.
- **Restarting does not help.** The pile-up came back within a minute after both the 12:48
  service restart and the ~12:54 reboot. The reboot also shrank the WAL to 1 MB, and the
  gateway still reached ~11 cores, 285 threads and 274 index connections within 7 minutes. The
  **4.9 GB SQLite WAL is a symptom/amplifier, not the cause.**
- **Root cause:** a design defect in `crates/sase_gateway/src/fleet_reads/service.rs`
  (sase-core). The snapshot refresh has no single-flight across timeouts, no back-off after a
  failure, and no bound on concurrent index work. Any build slower than 4 s turns into a
  self-sustaining meltdown. **Fix:** make the rebuild a single detached in-flight task per
  scope that always fills the cache, add a failure back-off and a concurrency cap, and take
  `Revalidate` off the request path. Until that ships, run `sase service proc stop gateway` on
  apollo (details in §8).

---

## 1. What is using the CPU right now

apollo is a DigitalOcean droplet with 16 vCPU, 31 GiB RAM and no swap.

Snapshot at **12:41:59–12:44**:

| Metric | Value |
| --- | --- |
| Load average | **177.76 / 173.49 / 146.31** |
| CPU split | 65.7% us, **14.6% sy**, 16.7% ni, 3.0% id, 0.0% wa |
| Runnable threads | 289 R threads system-wide. 260 of them were gateway `tokio-rt-worker` threads |

Top consumers in that window:

| Process | CPU | Notes |
| --- | --- | --- |
| `sase_gateway --bind 127.0.0.1:7629` (pid 463583) | **6.6 cores** in a 10 s sample, **8.5 cores** in a second one. Lifetime average 676% (2h35m CPU in 23 min) | 500 threads, 7.6–8.0 GB RSS (VmHWM = VmRSS, still growing) |
| `rustc --crate-name sase_core_rs` ×3 | ~1 core each in a 15 s window, bursting higher | Release `maturin build` of `sase_core_rs`. Two came from workspace `sase_10`'s `just rust-install` validation, niced 10/19 |
| `sase tui --restart-service` (apollo's own TUI) | ~1 core | 15h CPU over 25h of uptime |
| pytest, `sase_job_*` chops, provider CLIs | < 1 core each | Normal agent workload |

The agent builds account for the `ni` share and are bursty. The gateway accounts for the
steady 7–9 cores and almost all of the `sy` time.

## 2. The gateway's pathological state

Measured on pid 463583 at 12:42–12:44:

- **Threads:** 500 in total: 499 `tokio-rt-worker` plus the main thread. 260 were runnable
  (`R`); most of the rest were in `futex_wait_queue`. Tokio's default blocking pool caps at
  512 threads.
- **File descriptors:** **1,023**, against a soft `RLIMIT_NOFILE` of **1,024**. That breaks
  down as:
  - **526** handles on `agent_artifact_index.sqlite`;
  - **483** handles on `agent_artifact_index.sqlite-wal`;
  - 6 sockets;
  - a few pipes and eventfds.

  At this limit new SQLite opens and `accept()` calls fail with EMFILE.
- **CPU split (10 s):** user +32.0 s, system +53.0 s. That is **8.5 cores, 62% of it kernel
  time.**
- **I/O (10 s):** `rchar` **9.1 GB**, with about 2.3 M `read` syscalls (≈4 KiB each) and
  `read_bytes` 0. Every read is a page-cache `pread` of SQLite pages, most of them WAL frames.
  Writes were 2.8 MB.
- **Thread creation timeline** (from `/proc/<pid>/task/*/stat` start times, service started
  12:19:07):

  ```text
  12:19 34 | 12:20 29 | 12:21 35 | 12:22 50 | 12:23 55 | 12:24 47
  12:25 47 | 12:26 54 | 12:27 64 | 12:28 47 | 12:29 17 | then 1-5/min (pool full)
  ```

  New blocking threads appeared at about 50 per minute from the moment the service started,
  until the pool hit its cap about 10 minutes later.
- **SQLite files:**
  - `agent_artifact_index.sqlite`: **86 MB** (21,046 pages × 4 KiB; 2,800 rows, 1,447 of
    them hidden).
  - `-wal`: **4.88 → 4.90 GB**, growing about 20 MB/min.
  - `-shm`: 9.5 MB.

## 3. Timeline: chronic since about 00:00 UTC

**`sar -u` on apollo, hourly samples:**

| Window | %user | %nice | %system | %idle |
| --- | --- | --- | --- | --- |
| Oct 7 (daily average) | 8.2 | 2.2 | **1.7** | 87.5 |
| Oct 8 (daily average) | 15.9 | 17.8 | **4.0** | 60.7 |
| Oct 8 23:50 | 14.1 | 36.9 | 4.1 | 44.0 |
| **Oct 9 00:10** | 27.7 | 39.5 | **25.6** | 6.3 |
| Oct 9 01:24 | 1.1 | 0.2 | **57.0** | 0.0 |
| Oct 9 (daily average to 12:40) | 28.5 | 17.0 | **36.2** | 9.6 |

**`sar -q` load:**

- Oct 8: under ~28 all day.
- Oct 9:
  - 00:40: 125.5
  - 02:30: 164
  - 03:00: 537
  - **03:50: 562.9** (runq 530)
  - 08:10–12:40: 75–160

**`sase.service` runs, from the user journal:**

| Run | Duration | CPU consumed | Average cores | Memory peak |
| --- | --- | --- | --- | --- |
| 10-08 22:10 → 22:53 | 43 min | 1h28m | ~2.0 | — |
| 10-08 22:53 → 10-09 01:25 | 2.5 h | 7h10m | ~2.8 (meltdown begins inside this run) | 9.3 G |
| 10-09 01:25 → 12:19 | 10.9 h | **3d 17h 36m (89.6 h)** | **~8.2** | — |
| 10-09 12:19 → 12:48 | 29 min | 3h48m | ~7.9 | **11.7 G** |

The journal also records two OOM kills inside `sase.service`, at 02:46:10 and 04:20:43
(`A process of this unit has been killed by the OOM killer`). The gateway's 8–12 GB RSS makes
it the obvious candidate. The kernel log for that boot wasn't available to confirm the victim.

**Client-side evidence from athena.** athena's TUI logs a fleet-refresh failure whenever a
remote host returns a diagnostic, such as a timeout. Hourly totals of
`fleet federation diagnostics[0] … missing field schema_version` in athena's `tui.log*`:

```text
before Oct 8 20:00 EDT: sporadic (0-19/hr, e.g. 2/hr on Oct 4)
2026-10-08 20 EDT (=00 UTC Oct 9): 267   21: 337   22: 414   23: 518
2026-10-09 00 EDT: 324   01: 96   02: 52 ... 08: 105
```

apollo's gateway began failing athena's requests in the **same hour** that apollo's kernel CPU
jumped. athena's TUI process (pid 40057) had been running since Oct 8 12:40 EDT, so no
client-side restart or upgrade lines up with the onset.

## 4. Restarts reproduce it within a minute, even with a clean WAL

### 4.1 After the 12:47:59 service restart

The restart was dev-update driven. The new gateway was pid 600193; WAL size and load are
excluded from the table.

| Time | Threads | Index connections | RSS | Gateway CPU (cumulative) |
| --- | --- | --- | --- | --- |
| 12:48:53 | 41 | 34 | 0.5 GB | 123 s |
| 12:50:08 | 106 | 96 | 1.9 GB | 803 s |
| 12:51:24 | 153 | 141 | 2.8 GB | 1,491 s |
| 12:52:39 | 216 | 204 | 3.4 GB | 2,226 s |

That is about 9.3 cores from the first minute, with roughly 50 new connections per minute.

### 4.2 After the reboot at about 12:54

The new gateway was pid 1324, started at 12:55:02. The **WAL was truncated to 1.1 MB** and
**stayed at 1.1 MB** throughout. The host was otherwise idle, with a 1-minute load of 2.8 at
12:55:14.

| Time | Threads | Index connections | RSS | Gateway CPU (cumulative) | Load (1 min) |
| --- | --- | --- | --- | --- | --- |
| 12:55:14 | 24 | **7** (12 s after start) | 0.16 GB | 22 s | 2.8 |
| 12:56:30 | 69 | 56 | 1.2 GB | 854 s | 24.6 |
| 12:58:31 | 162 | 147 | 2.9 GB | 2,310 s | 46.1 |
| **13:01:50** | **285** | **274** | **4.6 GB** | **74 min (≈10.9 cores)** | 31.7 |

At 13:01 the whole host showed 32.8% us, **40.1% sy**, 24% id, and no rustc or agent builds
were running. **The gateway alone produces the load, and it does so without the big WAL.**

The oldest blocking threads (created 12:55:05–12:55:16) already had 55–61 s of CPU each,
split about 1:2 user:system. Builds were not finishing within the 4 s budget even in the
first seconds after boot.

## 5. Mechanism in the code (sase-core)

All paths below are in the linked `sase-core` checkout. The 4 s timeout pattern dates back to
at least `v0.34.71`, and apollo runs `sase_core_rs 0.37.0+`, so the deployed build has it.

### 5.1 The refresh path: `crates/sase_gateway/src/fleet_reads/service.rs`

- **`SNAPSHOT_REFRESH_TIMEOUT = 4 s`** (line 60). It is the only timeout used in production
  (`FleetReadService::new`, line 94).
- **`current_snapshot`** (lines 469–525) and **`current_history_snapshot`** (lines 548–604)
  work like this:
  1. Return the cache if it is less than 60 s old (`FLEET_SNAPSHOT_STALE_SECONDS`).
  2. Otherwise take the async `refresh_lock` and run
     `timeout(4 s, spawn_blocking(build_snapshot_blocking))`.
  3. When the timeout fires, they return through `retain_previous_or_error`. That drops
     `_guard` and **releases the refresh lock** while the blocking build **keeps running**,
     because a `spawn_blocking` task can't be cancelled.
  4. The next waiting request takes the lock, still finds no fresh cache, and **starts
     another build**.
- **A late result is thrown away.** The cache is written only in the `Ok(Ok(Ok(snapshot)))`
  arm (lines 521–523 and 600–602). A build that finishes after its caller timed out never
  fills the cache.
- **No back-off.** `retain_previous_or_error` (lines 726–741) marks the old snapshot stale
  but keeps its `build_instant`. `unexpired_cached_snapshot` (lines 632–644) treats anything
  60 s or older as a miss, so **every** later request tries a fresh build again. After a
  restart there is no previous snapshot at all, and every request simply errors and leaves
  another orphan build behind.
- **Other request-scoped blocking work has no limit.** `overlay_missing_into_snapshot`
  (lines 693–707) runs one `spawn_blocking` index query per Presentation `catalog` call, with
  no lock and no timeout. If the HTTP client gives up, that work still runs to completion.
- **Fan-out.** `summary`, `catalog`, `batch_lookup`, `detail` and `authoritative_snapshot` all
  go through `stamped_snapshot`. A History-scope `catalog` additionally goes through the
  separate History lock (lines 157–185). Each scope can therefore start a new orphan about
  every 4 s, and the overlay path adds more on top.
- **Runtime.** `crates/sase_gateway/src/cli.rs:32` uses `tokio::runtime::Runtime::new()`, so
  `max_blocking_threads` is the default 512. That matches the plateau of ~500 threads and
  ~500 index connections.

### 5.2 What each build does to SQLite: `crates/sase_core/src/agent_scan/index/`

- **`build_snapshot_blocking`** (`fleet_reads/snapshot.rs:67`) queries with
  `freshness: Revalidate`. In `query.rs:262–267`, Revalidate opens a **new read-write
  connection on every call** (`open_index`). There is no pool.
- **Every open** runs `PRAGMA journal_mode=WAL` plus all the `CREATE TABLE/INDEX IF NOT
  EXISTS` statements (`storage.rs:27–45`), and sets `busy_timeout` to 5 s.
- **What Revalidate does:**
  - recomputes marker signatures for the rows it touches, which costs about 9 `stat` calls
    plus a `read_dir` per row;
  - re-checks every hidden row's signature;
  - upserts anything that changed, as **autocommit statements with no enclosing
    transaction**.
  - History scope also walks every artifact directory and always writes two `meta` rows.

  This explains the system-time-heavy profile.
- The snapshot build then runs **`resolve_agent_session_dismissal_lineage`**. It opens a
  second, read-only connection and runs several queries plus a record-JSON decode for each
  candidate (`lineage.rs:144–235`). After that it builds per-record presentation, liveness
  and owner-file facts.
- **No WAL hygiene anywhere.** No code sets `wal_autocheckpoint`, `journal_size_limit` or
  `synchronous`, and no code calls `wal_checkpoint`. With hundreds of overlapping readers and
  writers the WAL can never restart, so it grows without limit. That is how the 86 MB database
  ended up with a 4.9 GB WAL. Every read then has to resolve pages through a huge wal-index
  across ~1.2 M frames, which makes each build slower again.
- **The Python side serializes index access; the gateway doesn't.** sase's Python facade
  wraps every index operation in `agent_artifact_index_operation_lock()`
  (`src/sase/core/agent_scan_facade.py:451`, an in-process `RLock`). The Rust gateway calls
  `query_agent_artifact_index` directly from up to 512 threads at once.

### 5.3 The index query alone is not what makes a build slow

As a calibration I ran one Presentation-shaped index query on apollo through the installed
`sase` venv. It used the same knobs as the gateway: `include_active`,
`recent_completed_limit=512`, `window_limit=512` and full records. The host's 1-minute load
was about 39 at the time, almost all of it from the gateway.

| Freshness | Records | Wall time | CPU time |
| --- | --- | --- | --- |
| `cached` | 314 | 1.22 s | 1.13 s user + 0.09 s sys |
| `revalidate` | 314 | 0.60 s | 0.46 s user + 0.14 s sys |

The query takes about 1 s even on a loaded host. The rest of a build's time therefore comes
from the post-query steps (dismissal lineage, presentation selection, record resolution) and,
above all, from contention with hundreds of sibling builds. I couldn't measure one isolated
build end to end: `kernel.perf_event_paranoid=4` and `ptrace_scope=1` block `perf` and
`strace`, and the gateway has no build-duration logging.

## 6. The client side: athena's federation polling

The only gateway clients are athena's TUI, through athena's `sase_federation_worker` (pid
4084810, which held 3 TLS connections to `apollo.tail297af1.ts.net:443`), and apollo's
`tailscale serve` proxying `https://apollo.tail297af1.ts.net/` to `127.0.0.1:7629`. The
gateway's peers on 7629 show no PID because tailscaled (root) owns them.

From the sase Python code (`src/sase/ace/tui/actions/agents/_fleet_refresh.py`,
`src/sase/dispatch/federation/_supervisor.py`):

- **What triggers a fleet refresh:** every local-agents apply while the Agents tab is visible.
  That means every 5–10 s on the auto-refresh tick, plus watcher deltas, tab switches and
  forced refreshes.
- **What one refresh sends:**
  - `summary`;
  - optionally `followed_batch` and `attention`;
  - `catalog` (limit 100);
  - up to **15 more catalog pages**.

  That is up to about 18 requests per refresh, and each one is preceded by a worker `health`
  op and `replace_config`.
- **No per-host in-flight dedup.** A new refresh task starts each time. Older ones are
  ignored by generation, but their worker calls keep running.
- **Immediate retry on IPC timeout.** `FederationWorkerUnavailable` (5 s socket timeout)
  respawns the worker with `ensure_started(force=True)` and resends the same request
  (`_supervisor.py:97–103`). Against a slow remote this doubles the request rate.
- **Timeout:** `dispatch.federation_worker.request_timeout_seconds: 5`
  (`default_config.yml:56`). It sits just above the gateway's 4 s build budget, so a slow
  apollo produces a timeout and an orphan build on nearly every call.

Peak failure counts of 267–518 per hour line up with a refresh every 7–13 s.

**Secondary bug (not the cause).** athena's refresh fails completely whenever any host returns
a diagnostic, with
`ValueError: fleet federation diagnostics[0] is not a valid fleet wire value: missing field schema_version`.
It has happened intermittently since 2026-09-20. It is why the apollo outage appears as a
broken fleet view rather than a clear "apollo timed out" row.

## 7. Why it started at about 00:00 UTC (trigger, partly inferred)

No sase-core commit between Oct 6 and the onset touched `sase_gateway`, `fleet*`,
`agent_scan` or `host_liveness`. The only nearby commits were wait/epic wire fields on Oct 6–7.
athena's client did not restart either. The most consistent explanation is a **load-induced
tip-over of a bistable system**:

- In the hour before onset apollo was already busy with niced agent work:
  - 23:50 showed `%nice` 36.9;
  - 00:10 showed `%nice` 39.5 and `%user` 27.7;
  - release builds of `sase_core_rs` were running.
- Once one snapshot build took longer than 4 s, §5's loop kept orphan builds accumulating.
  The CPU they used kept every later build above 4 s too, so the gateway never returned to
  the healthy state.
- Each restart started from an empty cache under the same constant client polling, and the
  service host was starting its scheduler and chops at the same moment. That was enough to
  tip it again within seconds, even right after the reboot.

What I could **not** determine is why the very first post-reboot builds missed 4 s on a
nearly idle host. It may be startup contention, gradual growth in per-build cost (2,800
indexed agents, 314 presentation records, an 86 MB index of ~30 KB record JSON each), or
both. The fix below makes this question non-critical, and the instrumentation it adds will
answer it.

## 8. Root cause and proposed solution

### Root cause

`sase_gateway`'s `FleetReadService` turns a slow snapshot rebuild into an unbounded pile of
concurrent rebuilds. Three properties combine:

1. the 4 s `tokio::time::timeout` around `spawn_blocking` does not cancel the build, but it
   does release the refresh lock;
2. late results are discarded, and a failure does not advance `build_instant`, so every
   request triggers another rebuild with no back-off;
3. nothing caps concurrent artifact-index work in the gateway, so up to tokio's 512 blocking
   threads each run a read-write `Revalidate` index query plus a lineage pass.

Under athena's TUI polling this creates a metastable meltdown: ~500 threads, ~1,000 SQLite
handles at the fd limit, 8–12 GB RSS with OOM kills, 7–11 cores of mostly kernel CPU, and a
WAL that grows without bound and slows every build further. It is fixed in sase-core. Per the
Rust-core boundary rule, that means `crates/sase_gateway` and `crates/sase_core/src/agent_scan`;
sase Python only needs client-side hardening.

### Immediate mitigation (minutes, no code)

1. **On apollo, stop the gateway proc until it is fixed:**
   `~/.local/bin/sase service proc stop gateway`. This stops it until the next boot; use
   `sase service proc disable gateway` to survive reboots.
   - Cost: athena loses the apollo fleet view, which is already broken because every refresh
     fails (§6).
   - The scheduler, axe routines and agents keep running.
   - **Don't rely on restarting.** Restarts at 12:19 and 12:48 and the reboot at ~12:54 all
     re-tipped within a minute.
2. **If the WAL has regrown** (check `ls -la ~/.sase/agent_artifact_index.sqlite-wal`), run
   `PRAGMA wal_checkpoint(TRUNCATE)` once the gateway is stopped. The reboot already cleared
   it, to 1.1 MB at 12:55.
3. **Optionally, on athena:** keep the TUI off the Agents tab, or drop apollo from the
   dispatch remote hosts, to stop the polling pressure while the gateway is down or being
   tested.

### Code fix, P0: sase-core `crates/sase_gateway/src/fleet_reads/service.rs`

1. **Single-flight that survives timeouts.**
   - Keep the in-flight build per scope in shared state, for example a
     `futures::Shared<JoinHandle<…>>` or a `tokio::sync::watch` slot.
   - Run the build as a detached task that **always writes the cache when it finishes**.
   - Callers wait up to 4 s. On timeout they get the previous snapshot marked `stale`, or a
     clean "warming" error if there isn't one, and **never start a second build while one is
     in flight**.
   - Invariant: at most one Presentation build, one History build and one overlay pass at any
     moment.
2. **Back-off after a failed or timed-out refresh.** Track `last_attempt_at` separately from
   `build_instant`. While a build is in flight, or within N seconds (for example 15–30 s)
   after a failure, serve the stale snapshot instead of trying again.
3. **Bound index work.** Put every gateway path that opens the artifact index (snapshot,
   history, overlay, lineage) behind one `tokio::sync::Semaphore`, for example with 2
   permits. Use `try_acquire` for best-effort work such as the overlay. As a backstop, build
   the runtime with `max_blocking_threads` around 32 instead of 512.
4. **Take `Revalidate` off the request path.** Let request handlers use `Cached` freshness.
   A single background refresher, triggered by the invalidation hub or a timer, does the
   read-write revalidation, matching the Python side's serialized index access.
5. **Instrument it.** Log or emit build duration, in-flight builds per scope, timeouts and
   discarded results. Today the gateway emits nothing about this, so the outage ran for about
   13 hours with no gateway-side signal.
6. **Regression test.** There are existing hooks: `new_with_timeout`, an injected slow
   `OwnerLivenessObserver`, and `refresh_count_for_test`. Fire many requests against a build
   that takes longer than the timeout, and assert:
   - only one build runs at a time;
   - the late result fills the cache;
   - no new build starts during the back-off window.

### P1: SQLite hygiene (`crates/sase_core/src/agent_scan/index/storage.rs`, maintenance)

7. Set `PRAGMA journal_size_limit` (for example 64 MiB) on open. Add a housekeeping
   `wal_checkpoint(TRUNCATE)` when the WAL passes a threshold, so a future reader pile-up
   can't leave a multi-GB WAL behind.
8. Wrap each record's multi-statement upsert in one transaction. Skip the unconditional
   `meta` writes when nothing changed. Reuse connections (a small pool) instead of opening a
   read-write connection and re-running the schema DDL on every query.

### P1: client hardening in sase Python (athena side)

9. Dedup fleet refreshes per host: skip a host that already has a request in flight. Add
   exponential back-off for a host after timeouts.
10. Don't respawn the worker and retry immediately on IPC timeout
    (`dispatch/federation/_supervisor.py:97–103`). A slow remote is not a dead worker.
11. Fix the `diagnostics[0] … missing field schema_version` normalization so one failing host
    degrades to a diagnostic row instead of failing the whole fleet refresh.

### P2: blast-radius containment (ops)

12. Run the gateway proc under its own cgroup limits (`MemoryHigh`/`MemoryMax`, a CPU weight
    or quota). A future runaway would then get throttled or restarted alone, instead of
    pushing `sase.service` into OOM kills and starving agents. Raising `LimitNOFILE` alone
    would only let the pile-up grow larger.

### How to verify the fix

After deploying, restart the gateway on apollo while athena's TUI sits on the Agents tab.

- Threads should stay at roughly 16 workers plus a handful of blocking threads.
- Open index handles should stay at 3 or fewer (`ls -l /proc/<pid>/fd | grep -c index.sqlite$`).
- Gateway CPU should stay under 1 core, and RSS under 1 GB.
- The WAL should stay at or below `journal_size_limit`.
- athena's `tui.log` should stop logging `sase-agents-fleet-refresh` failures for apollo.

## Appendix: key commands (all run read-only over `ssh apollo` / `ssh apollo-do`)

- `uptime; top -b -n1; ps -eLo stat=,comm= | …` gave thread states and top consumers.
- `/proc/<gw>/{status,limits,io,stat}`, `/proc/<gw>/task/*/{stat,wchan}` and
  `ls -l /proc/<gw>/fd` gave threads, fds, the CPU split, I/O, thread ages and SQLite handles.
- `ss -tanp | grep :7629` and `tailscale serve status` identified the clients (tailscaled
  proxy); on athena, `ss -tnp` pointed to `sase_federation_worker`.
- `journalctl --user -u sase.service` gave restarts, per-run CPU, memory peaks and OOM kills.
- `sar -u` / `sar -q` on `/var/log/sysstat/sa07..sa09` established onset and history.
- `~/.sase/logs/dev_update.jsonl` (apollo) explained the 12:19 and 12:48 restarts as
  dev-update reinstalls.
- athena `~/.sase/logs/tui.log*` gave fleet-refresh failure counts per hour.
- One read-only SQLite count (`mode=ro`) and one calibration `query_agent_artifact_index` run
  through the installed sase venv (§5.3).
- `perf record` and `strace -c` were attempted and refused (`perf_event_paranoid=4`,
  `ptrace_scope=1`). No sudo was used.
