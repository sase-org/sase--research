---
create_time: 2026-08-27
updated_time: 2026-08-27
status: research
---

# Why `sase ace` Feels Slow: The Steady-State Refresh Loop

**Research question:** the ACE TUI has become "incredibly slow" recently. What does
SASE's own instrumentation say is consuming the time during a *running* session (not
just at launch), and what single change buys back the most responsiveness?

**Scope:** `sase` at master `5cc5da03a`, linked `sase-core` at `b7ca9ce`, measured
2026-08-27 against live `~/.sase` state on `athena`. Evidence is ACE's own JSONL logs
(`tui_startup`, `tui_agent_loads`, `tui_stalls`, `tui_git_ops`, `tui.log`) plus
benchmarks re-run here against the production index. Absolute times are host- and
cache-specific; the *scaling* behavior is the portable result.

**Companion:** [`ace_startup_critical_path/`](./ace_startup_critical_path/ace_startup_critical_path.md)
(2026-08-12) analyzed the *launch* path. This report analyzes the *steady state*, which
turns out to be the dominant cost — the same loader that gates startup once then re-runs
every 5–10 seconds for the entire session. Where the two overlap I note it.

---

## Bottom line

ACE reloads **the whole agent history from the artifact index every 5–10 seconds**,
materializes **~784,000 Python objects** from a **25.5 MB** payload to render **~12
visible rows**, and does it in a way the GIL forces to serialize against the UI thread.

The three numbers that matter:

| Measurement | Value | Source |
| --- | ---: | --- |
| Slow (>2 s) agent loads logged on 2026-08-27 | **1,878** | `tui_agent_loads.jsonl` |
| Cumulative time in those loads, one day | **168 min** | same |
| Python objects built per refresh, to show ~12 rows | **784,314** | measured here |

`load_kind: full` accounts for **10,027 of 10,418** slow loads (96%). The bounded
incremental path (`artifact_delta`) already exists and is taken **223 times (2%)**.

The refresh is nominally "off the event loop" via `asyncio.to_thread`. It is not off the
**GIL**. Measured directly: running 8 agent loads concurrently takes **8× as long** as
running one (1.08 s → 9.21 s), i.e. exactly zero parallelism, while the UI thread's
worst stall grows from 122 ms to 359 ms. The threads buy nothing and cost jitter.

**Recommendation:** stop selecting and marshalling `record_json` on the list-render path,
and make the incremental delta the default refresh. See
[Recommended solution](#recommended-solution).

---

## The regression is real, and it is dated

`~/.sase/logs/tui_startup.jsonl`, 362 launches, median / max seconds per day:

| Day | n | `process_start_to_on_mount` | `agents_ready` | `axe_ready` | `visible_ready` |
| --- | ---: | ---: | ---: | ---: | ---: |
| 08-12 | 11 | 0.62 / 1.39 | 3.44 / 15.79 | 1.70 / 3.28 | 2.81 / 14.40 |
| 08-16 | 22 | 0.73 / 0.95 | 6.50 / 13.77 | 1.92 / 4.10 | 5.77 / 12.82 |
| 08-20 | 6 | 0.74 / 1.24 | 4.05 / 5.75 | 1.96 / 3.38 | 3.34 / 4.51 |
| 08-24 | 38 | 0.96 / 1.20 | 4.81 / 9.69 | 2.27 / 2.97 | 3.78 / 8.75 |
| 08-26 | 18 | 0.93 / 1.29 | 4.88 / 6.81 | 2.33 / 2.77 | 3.77 / 5.91 |
| **08-27** | **19** | **0.96 / 1.48** | **11.15 / 25.11** | **4.43 / 8.05** | **9.85 / 24.17** |

Two distinct effects:

1. **A slow creep.** `process_start_to_on_mount` grew 0.62 s → 0.96 s (+55%) in fifteen
   days. That is import time: `import sase.ace.tui.app` is now **1.58 s warm across 2,835
   modules** (2,124 of them `sase.*`). The 08-12 report measured 2,402 modules — an 18%
   growth in the import graph in fifteen days.
2. **A step change on 08-27.** `agents_ready` median jumped 4.88 s → 11.15 s and
   `axe_ready` 2.33 s → 4.43 s.

The step change is **not** explained by more agents to display. `agent_row_count` moved
the *opposite* way over the same window — median 33 rows on 08-12, **12 rows on 08-27**.
Fewer rows, slower load. The cost is not proportional to what is on screen.

What *did* grow is the data behind the rows, and the machine's concurrent load: 23 live
`run_agent_runner` processes at the time of measurement, each writing artifact files that
wake ACE's inotify watcher.

---

## Where the time actually goes

### The loader is a full-history rebuild, and it runs constantly

`tui_agent_loads.jsonl` (+`.1`) records every load exceeding a 2.0 s threshold — 10,418
records over 8 days. The slow stage is `disk` in **10,195** of them (98%).

| Day | slow loads | disk p50 | disk p95 | disk max | agents loaded p50 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 08-19 | 612 | 2.85 s | 12.61 s | 85.8 s | 535 |
| 08-24 | 1,603 | 2.58 s | 8.91 s | 74.5 s | 313 |
| 08-26 | 1,978 | 2.58 s | 5.73 s | 58.7 s | 283 |
| **08-27** | **1,854** | **3.00 s** | **10.54 s** | **373.1 s** | **355** |

By source: `auto_refresh` **8,799**, `tier1_index_revalidate` 706, `notification` 273,
`launch` 242, `startup` 179.

The cadence constants:

- `refresh_interval` defaults to **10 s** (`src/sase/ace/tui/app.py:284`)
- `AGENTS_LOAD_MIN_INTERVAL_SECONDS = 5.0` — the floor between loads
- `FULL_SANITY_REFRESH_SECONDS = 60.0` — a full reconcile that **ignores every gate**

So the worst case is a full history rebuild every 5 s, and the guaranteed case is one
every 60 s regardless of whether anything changed. At a p50 of 3.0 s against a 10 s tick,
ACE spends roughly **30% of its wall clock inside a full agent reload** — and that is
counting only the loads that crossed the 2 s logging threshold.

This correlates directly with what the user feels. In `tui_stalls.jsonl` the median
inter-arrival between hitch events is **7.9 s**, tracking the refresh tick.

### Profile of one load

Benchmarked here against the live index, warm, in an otherwise idle process:

```
disk_load = 1.06–1.17 s   →  404 agents returned, ~12 displayed
```

`cProfile`, cumulative, one load (1.65 s under profiler overhead):

| Cost | Time | Note |
| --- | ---: | --- |
| `sase_core_rs.query_agent_artifact_index` | **0.421 s** | Rust; 1,368 records |
| `load_workflow_agent_steps_from_snapshot` | 0.331 s | 366 records |
| `enrich_agent_from_meta` | 0.274 s | **1,554 calls**, filesystem |
| `dismissed_bundle_identities_snapshot` | 0.218 s | |
| `load_done_agents_from_snapshot` | 0.191 s | 791 records |
| `agent_scan_wire_from_dict` | 0.153 s | 791 dict→object conversions |
| `pathlib.resolve` → `realpath` | 0.106 s | **1,651 calls** |

Note the shape: **1,368 records queried, 791 done-agents constructed, 1,554 filesystem
enrichments — to paint ~12 rows.**

### `record_json`: a 141 MB blob on the hot path

`~/.sase/agent_artifact_index.sqlite` is **195 MB**. Column-level breakdown of the
`agent_artifacts` table (9,700 rows):

| Column | Total | Avg/row | Share |
| --- | ---: | ---: | ---: |
| **`record_json`** | **141.3 MB** | **14,572 B** | **95.3%** |
| `clan_summary` | 1.9 MB | 195 B | 1.3% |
| everything else (44 columns) | ~5 MB | — | 3.4% |

The table already denormalizes 45 scalar columns — `status`, `agent_name`, `model`,
`started_at`, `finished_at`, `workflow_status`, `hidden`, and so on. The list view needs
those. It does not need the blob.

But `select_records` (`sase-core/crates/sase_core/src/agent_scan/index.rs:3134`) selects
it for every row anyway:

```rust
"SELECT artifact_dir, projects_root, record_json, \
 agent_meta_sig, done_sig, running_sig, waiting_sig, \
 pending_question_sig, workflow_state_sig, plan_path_sig, \
 prompt_steps_sig, xprompts_sig \
 FROM agent_artifacts {}"
```

…and then `serde_json::from_str::<AgentArtifactRecordWire>` deserializes each one.
Reading 800 such rows moves **15.4 MB** from SQLite.

The 08-12 report flagged this in `refresh_stale_rows` (`index.rs:1499`). It is also true
of the *main* query, which is the one that runs every 5–10 seconds.

A separate query, `repair_abandoned_agent_artifact_index_rows` (`index.rs:684`), runs
three `LIKE` predicates **against that 141 MB text column** — an unavoidable full-table
scan. Measured: **0.157 s warm**, matching **36 rows**.

### The PyO3 boundary is where the UI thread dies

This is the finding that reframes the rest. The Rust query correctly releases the GIL:

```rust
let snapshot = py.allow_threads(|| {
    core_query_agent_artifact_index(&index, &root, query_wire, opts)
})?;
let value = serde_json::to_value(&snapshot)?;   // <-- GIL HELD
json_value_to_py(py, &value)                     // <-- GIL HELD
```

Only the *SQL and Rust decode* run GIL-free. The result is then re-serialized into a
`serde_json::Value` tree and expanded into a Python object graph **while holding the
GIL**. Measured against the live index:

```
rust binding total        = 0.561–0.655 s   (1,368 records)
returned payload          = 25.5 MB of JSON
python objects in graph   = 784,314
agent_scan_wire_from_dict = 0.205–0.249 s   (pure Python, GIL held)
```

Then Python converts that dict graph into dataclasses — another 0.2 s of GIL-held work —
and enriches from the filesystem.

**Direct measurement of UI-thread starvation.** A probe thread ticking every 1 ms
(standing in for the Textual event loop), while background threads run real agent loads:

| Scenario | Wall | UI tick p50 | p95 | **max** | ticks >100 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| idle baseline | — | 1.06 ms | 1.06 ms | 1.43 ms | 0 |
| 1 concurrent load | 1.08 s | 1.06 ms | 6.13 ms | **122 ms** | 1 |
| 4 concurrent loads | 4.15 s | 1.07 ms | 6.21 ms | **264 ms** | 5 |
| 8 concurrent loads | 9.21 s | 1.08 ms | 6.96 ms | **359 ms** | 9 |

Two conclusions, both important:

1. **Wall time scales 1:1 with thread count** (1.08 → 4.15 → 9.21 s). Eight threads
   deliver zero parallelism. The work is GIL-serialized Python and GIL-held marshalling.
   `Py_GIL_DISABLED` is **0** on the interpreter ACE runs (CPython 3.14.7). The
   `asyncio.to_thread` calls in `_loading_disk.py` — there are six per load — do not make
   this concurrent. They only add scheduling jitter.
2. **Every additional thread makes the worst UI stall worse.** ACE runs many. `tui.log`
   records ACE exiting with **20 live worker threads** (`asyncio_0` … `asyncio_19`).

This explains the otherwise-puzzling stall stacks. `tui_stalls.jsonl` shows the main
thread caught inside ordinary, cheap operations — `query(PromptInputBar)` at **7.42 s**,
`textual/css/match.py`, `_compositor._render_chops`, `Strip.__init__`. None of those are
slow code. They are simply where the UI thread happened to be standing when the GIL was
taken away from it for seconds at a time.

The `agent_artifact_index_operation_lock()` wrapped around every index call
(`src/sase/core/agent_artifact_index_lock.py:13`) adds a second serialization layer on
top of the GIL.

### The incremental path exists and is bypassed 98% of the time

`_load_agent_artifact_delta_async` (`_loading_disk.py:362`) applies a bounded, exact set
of changed artifact dirs. The watcher already computes them
(`_enqueue_agent_artifact_delta_paths`). Yet `load_kind` across 10,418 slow loads is
`full: 10,027` / `artifact_delta: 223`.

The reason is visible in `_artifact_delta.py:60-105`: the batch is **all-or-nothing**. A
single watched path that does not map to an artifact dir sets
`_dirty_agent_artifact_fallback_reason = "unknown_watcher_path"`, which **discards the
entire queued delta** and escalates to a full reload. So does exceeding
`AGENT_ARTIFACT_DELTA_QUEUE_LIMIT = 64`. With 23 agents writing concurrently, both fire
routinely.

The fast path is built. It is being poisoned by its own fallback policy.

### Secondary contributors

Real, but an order of magnitude smaller than the refresh loop:

- **Blocking calls on keystroke paths.** Stall stacks show, on `j`/`k` keypresses:
  `subprocess._execute_child` (a `fork` from `bare_git_workspace._run_git`),
  `posixpath.realpath` from `_linked_repo_config.normalize_path`, and
  `config/core.py:262 current_config_token → refresh_thread.start()`. On
  `text_area_changed`: `os.listdir` in `artifact_files_cache.select_prompt_file`, reached
  from `get_prompt_content` — a render path. These violate rules 1, 8 and 11 of
  `sase/memory/tui_perf.md`.
- **DOM size.** At the worst captured stall the app held **874 live asyncio tasks, 847 of
  them Textual widget message pumps** — 102 `MarkdownParagraph`, 55 each of
  `MarkdownBullet` / `Horizontal` / `Vertical`, plus ~25 `MarkdownTableCellContents`.
  Textual mounts one widget per Markdown block, so a large rendered document inflates
  every DOM query and every CSS re-match. One snapshot is not enough to distinguish a
  leak from steady state, but it is a multiplier on all main-thread work. Worth a
  dedicated look.
- **The watchdog worsens the freeze it records.** The `tui_pump_stall` record is written
  **from the event loop** (`_stall_watchdog_records.py:170`, reached via
  `asyncio/events.py:94`). One such record was **2.29 MB on a single line**, 2.24 MB of it
  `asyncio_task_stacks` for 874 tasks. Capturing and serializing that on the loop extends
  the stall it is reporting.
- **Machine load.** `tui_git_ops.jsonl` shows **30.6 minutes of git subprocess time**
  across 2,381 operations (`sdd.clone.remote` p50 6.4 s / max 52 s). By `cwd` these are
  overwhelmingly *agent* processes, not ACE — so this is not on ACE's critical path, but
  with 23 agents running it is real CPU and I/O contention against a TUI that is already
  GIL-bound. `tui.log` also carries 90+ `git rebase failed` warnings on workspace plans
  clones and 14 `WorkerFailed: RuntimeError('asyncio.run() cannot be called from a running
  event loop')` crashes — both worth separate task beads.
- **Unbounded state files.** `agent_name_registry.json` is **16.7 MB / 13,118 entries**
  (116 ms to parse); `dismissed_agents.json` is 2.4 MB; the index carries **38,214**
  `dismissed_agents` rows and 16.2 MB (8.3%) of freelist pages, never `VACUUM`ed. These
  set the floor that everything else builds on.

---

## Alternatives considered

**Raise `refresh_interval` / lower the sanity cadence.** One config line, immediate
relief. But it trades freshness for speed on a tool whose entire job is watching live
agents, and the 60 s sanity pass still rebuilds everything. Palliative, not a fix — though
worth doing as a stopgap while the real fix lands.

**Move the loader into a subprocess.** Genuinely escapes the GIL. But it needs the full
result marshalled back across a pipe — the same 25.5 MB — and adds process lifecycle,
failure modes, and startup cost. It treats the symptom (the work is expensive) rather than
the cause (the work is unnecessary).

**Build free-threaded CPython.** Would make `to_thread` deliver real parallelism. Requires
every native dependency to support it, is a large operational change, and would let ACE
burn 8 cores doing work it should not do at all.

**Cache the loaded snapshot in Python between ticks.** Helps only if the data is unchanged
— but the watcher fires precisely because it changed. It also does not reduce the
first-load or post-change cost, which is what the user feels.

**Prune history aggressively.** Reduces the constant factor and is worth doing on its own
merits, but the loop is O(history) either way; pruning just resets the clock on the same
degradation.

None of these change the fact that ACE reads and rebuilds ~1,368 records to display ~12.

---

## Recommended solution

Fix the *shape* of the refresh, in this order. Stage 1 is the largest win per unit of
risk and requires no behavior change at all.

### Stage 1 — stop putting `record_json` on the list-render path (core)

`record_json` is 95.3% of the index and 100% of the marshalling cost, and the list view
does not read it. In `sase-core`:

1. Add a **projected selection** to `select_records` (`index.rs:3134`) that returns only
   the scalar columns the loader renders, plus the `*_sig` columns. The columns already
   exist and are already populated.
2. Fetch `record_json` **lazily**, per artifact dir, only when a row is expanded, zoomed,
   or otherwise needs the full record. `SELECT record_json FROM agent_artifacts WHERE
   artifact_dir = ?1` already exists in several places (`index.rs:6635`, `:6950`).
3. Apply the same projection to `refresh_stale_rows` (`index.rs:1499`) — already
   recommended on 08-12 and still open.
4. Replace the three `record_json LIKE` predicates in
   `repair_abandoned_agent_artifact_index_rows` (`index.rs:684`) with an indexed scalar
   column (e.g. a `done_outcome` column), or move the pass off the read path entirely.
   It scans 141 MB to find 36 rows.

Expected: the ~25.5 MB payload collapses by roughly 95%, and with it the 784,314-object
graph. Both the GIL-free Rust decode and the GIL-held `json_value_to_py` shrink in
proportion. This is the single highest-leverage change in the report.

### Stage 2 — make the delta path the default, not the exception

The machinery is already written and is used 2% of the time. Change the fallback from
all-or-nothing to partial:

- An unmapped watcher path should invalidate **only what it cannot classify**, not discard
  the entire queued delta. Apply the delta for the dirs that *did* map, and schedule a
  narrow reconcile for the remainder.
- Raise or shard `AGENT_ARTIFACT_DELTA_QUEUE_LIMIT = 64`; with 23 concurrent agents it
  overflows into a full reload, which is strictly more expensive than the delta it
  replaced.
- Keep `FULL_SANITY_REFRESH_SECONDS` as the backstop, but once Stage 1 lands a projected
  full reload is cheap enough that its 60 s cadence stops mattering.

Expected: the common case — one agent wrote one file — costs one row, not 1,368.

### Stage 3 — stop paying for threads that provide no parallelism

Once Stages 1–2 land, revisit the six `asyncio.to_thread` calls per load in
`_loading_disk.py`. They are measurably counterproductive today: zero parallelism, and
each additional thread raises the worst UI stall. Either collapse them into a single
Rust-side call under `allow_threads`, or run the remaining small residue inline. Update
`sase/memory/tui_perf.md` rule 1 to say what the data shows: **for CPU-bound Python,
`to_thread` moves work off the loop but not off the GIL, and it makes stalls worse.**

Then clear the keystroke-path violations the stall log names directly: the `fork` in
`bare_git_workspace._run_git`, `realpath` in `_linked_repo_config.normalize_path`,
`refresh_thread.start()` in `current_config_token`, and `os.listdir` in
`artifact_files_cache.select_prompt_file`.

### Stage 4 — housekeeping (independent, do anytime)

`VACUUM` the index (recovers 16.2 MB of freelist immediately, more after Stage 1 shrinks
`record_json` usage); add a retention policy for the 38,214 `dismissed_agents` rows and
the 13,118-entry `agent_name_registry.json`; write the watchdog's stall record from a
worker thread rather than the event loop, and cap `asyncio_task_stacks` so a 2.3 MB
serialization cannot extend the freeze it is measuring.

---

## What to measure after

The instrumentation to confirm the fix is already in place:

- `tui_agent_loads.jsonl` — the count of slow (>2 s) loads per day should collapse, and
  `load_kind` should invert from 96% `full` to majority `artifact_delta`.
- `tui_startup.jsonl` — `agents_ready` should return below the 08-12 baseline, not just
  below today's.
- `tui_stalls.jsonl` — hitch inter-arrival should decouple from the 10 s refresh tick.
- `SASE_TUI_PERF=1` → `~/.sase/perf/tui_jk.jsonl`, target p95 < 16 ms per
  `sase/memory/tui_perf.md`. The existing capture there is from 08-14 and is stale; take a
  fresh baseline before starting.
