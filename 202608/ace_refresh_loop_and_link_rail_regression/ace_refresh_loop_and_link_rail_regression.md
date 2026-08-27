---
create_time: 2026-08-27
updated_time: 2026-08-27
status: research
---

# Why `sase ace` Is Slow: A Chronic Refresh Loop Plus an Acute Link-Rail Regression

**Research question:** the ACE TUI became "incredibly slow recently". What do SASE's own
logs say is consuming the time, and what change buys back the most responsiveness?

**Scope:** `sase` 0.16.0+1638 at master `5cc5da03a`..`7e1214ced`, linked `sase-core` at
`f0224ef`, measured 2026-08-27 on `athena` (64 cores, 62 GB RAM) against live `~/.sase`
state. Evidence is ACE's own JSONL instrumentation (`tui_startup`, `tui_agent_loads`,
`tui_stalls`, `tui_git_ops`, `tui.log`), the production SQLite index, source in both
repos, and benchmarks re-run here. **All log timestamps are UTC; all git commit
timestamps are EDT (UTC−4).** Both source reports conflated these; several conclusions
change once they are aligned.

**Companion:** [`ace_startup_critical_path/`](../ace_startup_critical_path/ace_startup_critical_path.md)
(2026-08-12) covered the *launch* path. This report covers the steady state and a
same-day regression.

---

## Bottom line

There are **two independent problems**, and conflating them has been the main obstacle to
fixing either.

1. **Chronic (weeks old).** Every 5–10 s, ACE rebuilds ~429 agents from ~795 index
   records to paint **~12 visible rows** — a 36:1 waste ratio. One load costs ~1.0 s warm
   and idle, 2–3 s typical, and roughly half of it is spent holding the GIL, so it
   freezes the UI thread in ~100–400 ms chunks.
2. **Acute (landed 2026-08-27).** An app-level Link Rail added synchronous, uncached
   link-subject resolution to the **filesystem-watcher path**. Startup `agents_ready` p50
   went from ~4.9 s to a peak of **25.1 s**, and every readiness metric roughly doubled.
   A partial mitigation landed the same day at 12:08 UTC; it is still ~2× baseline.

**The user's "recently" is #2.** It is also by far the cheapest to fix. Neither source
report identified it, because both bucketed a partial UTC day against local-time commits.

The three numbers that matter:

| Measurement | Value | Source |
| --- | ---: | --- |
| Records loaded per refresh to paint ~12 rows | **795 records / 429 agents** | profiled here |
| Slow (>2 s) loads per active hour, 08-27 vs the 08-20→08-23 quiet baseline | **147/hr vs 18–25/hr** | `tui_agent_loads.jsonl` |
| `agents_ready` p50, 08-26 → 08-27 peak → now | **4.90 s → 25.11 s → 8.21 s** | `tui_startup.jsonl` |

---

## Part 1 — The acute regression (this is the "recently")

### The step change is real and is not explained by load or data size

`tui_startup.jsonl`, 363 launches, p50/p95 seconds per UTC day:

| Day | n | `start_to_on_mount` | `first_paint` | `agents_ready` | `axe_ready` | `visible_ready` | rows | idx rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 08-22 | 26 | 0.77/0.95 | 0.27/0.35 | 4.04/5.12 | 2.05/2.97 | 3.25/4.14 | 18 | 659 |
| 08-24 | 38 | 0.96/1.18 | 0.31/0.42 | 4.85/7.17 | 2.27/2.80 | 3.80/5.97 | 19 | 672 |
| 08-25 | 36 | 0.97/1.27 | 0.31/0.44 | 4.88/6.16 | 2.29/2.71 | 3.88/5.28 | 18 | 676 |
| 08-26 | 18 | 0.93/1.29 | 0.31/0.38 | 4.90/6.81 | 2.33/2.77 | 3.81/5.91 | 20 | 675 |
| **08-27** | **20** | **0.98/1.48** | **0.39/0.57** | **11.15/25.11** | **4.43/8.05** | **9.85/24.17** | **12** | **782** |

Three candidate explanations, all tested and all rejected:

- **More rows to render?** No — the opposite. `agent_row_count` p50 fell 33 → 12 over the
  window. `corr(agent_row_count, agents_ready) = 0.061` (n=363): essentially zero.
- **A bigger index?** Weak at best. `index_row_count` rose 675 → 782 (+16%) while
  `agents_ready` rose 128%. `corr(index_row_count, agents_ready) = 0.386`.
- **Machine load / concurrent ACE instances?** **Rejected as the cause of the step.**
  Splitting 08-27 startups by how many distinct ACE instances were active within ±5 min:

  | Day | low concurrency (≤1) n / p50 | high concurrency (≥2) n / p50 |
  | --- | ---: | ---: |
  | 08-24 | 31 / 4.89 s | 7 / 4.28 s |
  | 08-25 | 20 / 4.85 s | 16 / 4.91 s |
  | 08-26 | 18 / 4.90 s | 0 / — |
  | **08-27** | **7 / 10.17 s** | **13 / 11.15 s** |

  On 08-27 `agents_ready` is ~10–11 s **at both concurrency levels**, where every prior
  day sat at ~4–5 s regardless. Concurrency does not produce the step. (It does drive the
  *tail* — see Part 3.)

That leaves a code change.

### Bounding the regression window, and what landed inside it

There is a measurement gap between the last 08-26 startup (**23:38 UTC**, `agents_ready`
6.72 s) and the first 08-27 startup (**10:36 UTC**, 8.65 s — already elevated). Commits
inside that window, converted from EDT to UTC:

| UTC | Commit | Subject |
| --- | --- | --- |
| 04:44 | `e8f30d25f` | feat(ace): add artifact links panel |
| 05:04 | `d8e8b5ab8` | feat(tui): add app-level link trail for Ctrl+O/Ctrl+Shift+O across tabs |
| **05:50** | **`a7b702863`** | **feat(tui): move links to app-level rail, drop link_rail flag and L bindings** |

The per-launch timeline then shows a spike and a partial recovery:

```
10:36  8.65     11:25  25.11        12:29  11.96      14:12  12.71
10:38 10.17     11:34  11.86        12:30   6.36      14:35   7.36
10:49 16.44     11:36  15.62        13:26   6.84      14:57   8.78
10:51 12.18     11:46  25.01        13:50  10.97      15:10   8.21
                    ^ peak       ^ 12:08 UTC: f49030db6 perf fix lands
```

Pre-fix (10:36–11:46 UTC, n=8) median **14.0 s**; post-fix (12:29–15:10 UTC, n=12) median
**9.5 s** — a 32% recovery, still ~2× the 08-26 baseline of 4.90 s.

### The mechanism

`LinkRail.refresh_from_app()` (`widgets/link_rail.py:69-83`) is **synchronous and
uncached**: it calls `selected_link_subject(host)` and then `link_edges_for_selection()`
on every invocation. It is invoked from three call sites in
`src/sase/ace/tui/_app_watchers.py` (lines 35-37, 175-177, 206-208) — i.e. **on the
filesystem-watcher path**, the same watcher that 29 concurrent `run_agent_runner`
processes keep firing.

`selected_link_subject` → `accent_and_icon_for_ref` (`relations/link_subject.py:96,120`;
also per-neighbor at `relations/link_index.py:224`) → `artifact_tabs.py:74` →
`provider_source_token()`. That function's own docstring
(`_artifact_tab_discovery.py:215-217`) says it "walks every configured project's record
and stats its config file, so callers on the render path … must not pay that cost on
every lookup" — and its cache TTL is **0.75 s**, recomputed **synchronously** on expiry
(`_artifact_tab_discovery.py:218, 249-260`).

Report `__a` independently caught this in the stall log without connecting it to the
regression: three captures of link-action availability calling `selected_link_subject`
and `accent_and_icon_for_ref` — doing provider rediscovery, project/sidecar store
resolution and Git invocation — blocking the event loop for **1.52–1.59 s** each.

This violates `tui_perf.md` rules 1 (never block the loop), 8 (render paths never
stat/glob) and 11 (keystroke paths are read-only). It is app-level, which is why *every*
readiness metric degraded together — `axe_ready` +90%, `agents_ready` +128%,
`visible_ready` +158% — rather than just the agent loader.

`f49030db6` (12:08 UTC) added the `provider_source_token` cache and recovered a third of
it. The remaining 2× is consistent with a 0.75 s TTL that still expires between watcher
bursts, plus the uncached `link_edges_for_selection()` work on the same path.

---

## Part 2 — The chronic refresh loop

### ACE loads 429 agents to paint 12 rows, every 5–10 seconds

Cadence, all verified in source:

- `refresh_interval` default **10 s** (`ace/tui/app.py:284`)
- `AGENTS_LOAD_MIN_INTERVAL_SECONDS = 5.0` — floor between loads
- `FULL_SANITY_REFRESH_SECONDS = 60.0` — full reconcile that ignores every gate
  (all in `actions/event_refresh/_constants.py:14-20`)

The `disk` stage wraps exactly one `asyncio.to_thread` call
(`actions/agents/_loading_disk.py:211-232`). Profiled here, warm, idle
(`best = 0.986 s`, 429 agents, ~12 displayed):

| Cost | Cumulative | Note |
| --- | ---: | --- |
| `query_agent_artifact_index` (facade) | **0.449 s** | 45% of the stage |
| — of which the Rust binding itself | 0.299 s | 30% |
| `load_workflow_agent_steps_from_snapshot` | 0.316 s | 365 records |
| `enrich_agent_from_meta` | 0.278 s | **1,559 calls**, filesystem |
| `load_done_agents_from_snapshot` | 0.184 s | 795 records |
| `agent_scan_wire_from_dict` | 0.137 s | 795 dict→object |
| `dismissed_bundle_identities_snapshot` | 0.136 s | |
| `_done_extra_files` | 0.123 s | 232 calls, filesystem |
| `pathlib.__str__` | 0.099 s | **12,223 calls** |

Report `__b` profiled the same path independently and got the same ordering within ~15%.
Two independent profiles agreeing is the strongest single result in this report.

**The shape is the finding: 795 records queried, 429 agents constructed, 1,559 filesystem
enrichments — to paint ~12 rows.**

### The payload, and why "off-thread" does not help

Measured against the live index with the real binding:

| Query | Time | Records | Payload | Python objects |
| --- | ---: | ---: | ---: | ---: |
| unbounded, cached | 1.076 s | 3,284 | 87.1 MB | 1,831,499 |
| bounded (what the loader uses) | 0.300 s | 795 | 12.7 MB | 344,303 |
| unbounded, `freshness=revalidate` | 1.466 s | 3,284 | 87.1 MB | — |

The binding correctly releases the GIL for the SQL and Rust decode, then **re-acquires it
for the entire object graph** (`sase_core_py/src/lib.rs`, `py_query_agent_artifact_index`):

```rust
let snapshot = py.allow_threads(|| { core_query_agent_artifact_index(...) })?;
let value = serde_json::to_value(&snapshot)?;   // GIL HELD
json_value_to_py(py, &value)                     // GIL HELD — recursive rebuild
```

Reproduced independently (CPython 3.14.7, `Py_GIL_DISABLED = 0`), with a 1 ms probe
thread standing in for the Textual event loop:

| Concurrent loads | Wall | probe p50 | **probe max** | ticks >100 ms |
| ---: | ---: | ---: | ---: | ---: |
| 0 (idle) | — | 1.06 ms | 1.1 ms | 0 |
| 1 | 0.38 s | 1.06 ms | **100.1 ms** | 1 |
| 4 | 1.15 s | 1.06 ms | **233.8 ms** | 2 |
| 8 | 2.06 s | 1.07 ms | **425.8 ms** | 3 |

Two conclusions:

1. **Each concurrent load makes the worst UI freeze worse** — 100 ms → 426 ms. `tui.log`
   records ACE exiting with **20 live `asyncio_N` threads**. This is the direct cause of
   the stall stacks: the main thread is caught inside cheap operations
   (`query(PromptInputBar)` at 7.42 s, `textual/css/match.py`,
   `_compositor._render_chops`) simply because that is where it was standing when the GIL
   was taken away.
2. **Threading buys little, but not nothing.** 8 threads take 5.4× a single load, not 8×.
   Report `__b`'s "exactly zero parallelism" overstates it — the `allow_threads` region
   yields ~1.5× effective parallelism at 8 threads. The accurate statement is that
   **roughly 70% of the work is GIL-held**, so `to_thread` moves work off the loop but
   mostly not off the GIL.

### `record_json` is 95% of the index and 98% of the payload

`~/.sase/agent_artifact_index.sqlite` is **194.7 MB / 9,509 rows**:

| Column | Total | Avg/row | Share |
| --- | ---: | ---: | ---: |
| **`record_json`** | **140.3 MB** | **14,759 B** | **95.3%** |
| everything else (45 columns) | ~9 MB | — | 4.7% |

`select_records` (`sase-core .../agent_scan/index.rs:3142-3148`) selects it for every row
on every refresh, then `serde_json::from_str::<AgentArtifactRecordWire>` deserializes each
one — even though the table already denormalizes the 45 scalar columns the list view
renders. Measured at the SQL layer over all 9,509 rows:

| Query | Time | Payload |
| --- | ---: | ---: |
| current (`… record_json, *_sig …`) | 0.144 s | 142.6 MB |
| projected (drop `record_json`) | 0.075 s | 2.25 MB |
| projected + 24 render scalars | 0.121 s | 5.59 MB |

**Dropping `record_json` cuts the payload by 98.4%.** Note carefully what this does and
does not mean — see the corrections below.

### The delta path exists and is poisoned by its own fallback

`load_kind` across 10,482 slow loads: `full` **10,083 (96%)**, `artifact_delta` **223
(2%)**, `monitor_reconcile` 168. By source: `auto_refresh` 8,848,
`tier1_index_revalidate` 709, `notification` 273, `launch` 244, `startup` 180.

The reason is visible in `actions/event_refresh/_artifact_delta.py:60-105`: the batch is
all-or-nothing. A single watched path that does not map to an artifact dir sets
`_dirty_agent_artifact_fallback_reason = "unknown_watcher_path"`, **discards the entire
queued delta** (`_dirty_agent_artifact_dirs = ()`), and escalates to a full reload. So
does exceeding `AGENT_ARTIFACT_DELTA_QUEUE_LIMIT = 64`. With 29 concurrent agent runners
writing artifacts, both fire constantly. The fast path is built; the policy prevents it
from ever being taken.

### The viewport contract exists and is explicitly discarded

`AgentsViewport` (`data_providers/_types.py:37-46`) defines `visible_rows=40,
prefetch_rows=80` → `requested_limit = 120`. But `make_agents_data_provider()`
(`_factory.py`) always returns `DirectAgentsDataProvider`, whose `load_agents` begins
`del search_query, viewport` and ends `full_reload=True` (`_direct.py:16-46`). The
bounded read window is designed, typed, and thrown away on every call.

---

## Part 3 — Contention, and what the evidence does *not* support

Both source reports made claims the data does not carry. Correcting them matters, because
two of them would misdirect the fix.

**The `disk` stage is not disk I/O.** Report `__a` attributes the cost to "disk/index
work" and I/O contention. But a warm SQLite read of the *entire* 195 MB table takes
**0.144 s**, with 31 GB of page cache on a 62 GB host. The stage is ~97% CPU —
JSON deserialize → `serde_json::Value` → Python object graph → dataclasses → filesystem
enrichment. Optimizing I/O would target almost nothing.

**Reads do take the write lock, but that is not what is stalling ACE.** Report `__a` is
right in code: `open_index` (`index.rs:1961-2265`) calls `fs::create_dir_all`, opens
`Connection::open` with default **READ_WRITE|CREATE** flags (there is no read-only path
anywhere in the file), replays `PRAGMA journal_mode = WAL` plus **25 `CREATE TABLE/INDEX
IF NOT EXISTS`** statements, and ends with an unconditional
`INSERT OR REPLACE INTO meta(key,value) VALUES ('schema_version', ?1)` on **every open**.
But the evidence says it is secondary: that write costs **14 ms** measured, and the
disk-time histogram shows **no pileup at 5 s multiples** — 60% of slow loads land in the
2–3 s bin, immediately above the 2 s logging threshold, and the distribution decays
smoothly. `DEFAULT_INDEX_BUSY_TIMEOUT` is 5 s (`index.rs:177`), and it is essentially
never being hit. Worth fixing for correctness and multi-writer hygiene; not the cause.

**Concurrency drives the tail, not the median.** Across 10-minute buckets over 8 days:

| Concurrent ACE instances | buckets | median disk p50 | median bucket max |
| ---: | ---: | ---: | ---: |
| 1 | 804 | 2.52 s | 4.68 s |
| 2 | 14 | 3.50 s | 10.78 s |
| 3 | 5 | 2.79 s | 19.56 s |
| 4 | 1 | 4.77 s | 37.56 s |

The median barely moves; the **tail grows 8×**. Same pattern in startup p95 (7.36 s at
≤1 instance → 15.62 s at 3). The 373 s outlier and the multi-minute freezes are
contention events; the everyday 2–3 s cost is not.

**`record_json` projection is necessary but not sufficient.** Report `__b` calls it "100%
of the marshalling cost" and "the single highest-leverage change". The payload claim is
right (98.4%), but the Rust binding is only **30%** of the disk stage and the whole
query-plus-conversion path is **45%**. The other ~55% — `enrich_agent_from_meta` (1,559
filesystem calls), `_done_extra_files`, `dismissed_bundle_identities_snapshot` — is
per-agent Python and filesystem work that projection does not touch, and that *is*
genuine I/O contending with 29 agent runners. Expect projection to remove ~35–45% of the
stage, not ~95%.

**The DOM/widget-bloat finding rests on n=1.** Both reports built a "hundreds of hidden
Markdown widgets" thesis on the same **single** stall record — the only one of 51 that
carries `asyncio_task_stacks` (pid 4111822, 874 tasks, 2.29 MB on one line). Their class
histograms disagree (`__a`: 199 `MarkdownTableCellContents`, 165 `MarkdownParagraph`;
`__b`: ~25 and 102) because both parsed the same repr strings differently. The 874 tasks
are real and worth a dedicated soak, but *no* leak-vs-steady-state conclusion is
supportable from one sample, and neither report's histogram should be quoted.

Two smaller corrections: `agents_ready` 25.11 s on 08-27 is the **p95**, not the max
(`__b` mislabels it). And `__b`'s per-day slow-load table omits 08-25, which was actually
the busiest day at 2,179 records.

**Confirmed and carried forward.** The watchdog writes its stall record *from the event
loop* (`util/_stall_watchdog_records.py:170`), so a 2.29 MB serialization extends the
freeze it is measuring. `agent_name_registry.json` is 17 MB / 13,118 entries;
`dismissed_agents.json` is 2.4 MB; the index holds 38,220 `dismissed_agents` rows and
**17.4 MB (8.9%) of never-`VACUUM`ed freelist**. `tui_git_ops.jsonl` shows 30.6 min of
git subprocess time, but by `cwd` it is overwhelmingly agent processes, not ACE — real
contention, not ACE's critical path.

---

## Recommended solution

Fix the acute regression first — it is hours of work, it is what changed, and it is worth
about half the current pain. Then attack the chronic loop in evidence order.

### Step 0 — Repair the Link Rail regression (hours; highest value per unit risk)

`refresh_link_rail()` must not do synchronous provider discovery on the watcher path.

1. Coalesce it: one pending refresh at a time, dropped if the subject is unchanged.
2. Cache `link_edges_for_selection()` per selected subject; invalidate on selection
   change, not on every watcher event.
3. Raise `_PROVIDER_SOURCE_TOKEN_REFRESH_INTERVAL_SECONDS` from 0.75 s to something on
   the order of 30 s, and refresh it in the background on expiry (as
   `current_config_token()` already does) rather than synchronously.
4. Re-sweep the three `_app_watchers.py` call sites against `tui_perf.md` rules 1/8/11.

Target: `agents_ready` p50 back under the 08-26 baseline of 4.9 s.

### Step 1 — Project `record_json` off the list-render path (core; no behavior change)

In `sase-core`:

1. Add a projected selection to `select_records` (`index.rs:3142`) returning only the
   scalar columns the loader renders plus the `*_sig` columns. They already exist and are
   already populated.
2. Fetch `record_json` lazily per artifact dir when a row is expanded or zoomed — the
   single-row query already exists elsewhere in the file.
3. Apply the same projection to `refresh_stale_rows` — flagged on 08-12, still open.
4. Replace the `record_json LIKE` predicates in
   `repair_abandoned_agent_artifact_index_rows` (`index.rs:684`) with an indexed scalar
   column; they force a full scan of a 140 MB text column (~0.15 s measured).

Expected: payload −98%, object graph down proportionally, ~35–45% off the disk stage, and
the GIL-held `json_value_to_py` spike — the thing that freezes the UI in 100–400 ms
chunks — shrinks with it.

### Step 2 — Make the delta path the default, not the 2% exception

In `_artifact_delta.py`: an unmapped watcher path should invalidate only what it cannot
classify, not discard the whole queued batch. Apply the delta for dirs that *did* map and
schedule a narrow reconcile for the remainder. Raise or shard
`AGENT_ARTIFACT_DELTA_QUEUE_LIMIT = 64`, which overflows routinely at 29 concurrent
agents and escalates into something strictly more expensive than the delta it replaced.

This is the step that attacks **frequency** — 147 slow loads/hour on 08-27 versus 18–25
on quiet days — which is what the logs actually show exploding.

### Step 3 — Honour the viewport contract (the 36:1 waste)

Steps 1–2 make each load cheaper and rarer; they do not stop ACE loading 429 agents to
show 12. Wire `AgentsViewport` through `DirectAgentsDataProvider` instead of
`del ...viewport`, push search/filter/order into Rust, and return the requested window
plus prefetch (`requested_limit = 120`) rather than the full recent set. Fetch detail,
logs and relations only for the selected row. This is also the only step that reduces the
1,559 per-agent filesystem enrichments, which Step 1 does not touch.

This is the correct destination of report `__a`'s daemon-backed read-model proposal — but
as a bounded provider change, not a new long-lived service. **Defer the daemon itself.**
It is a large change whose main benefit (escaping the GIL, amortising index opens) is
mostly delivered by Steps 0–3 at a fraction of the risk. Revisit only if measurements
after Step 3 still miss target.

### Step 4 — Hygiene (independent, cheap, do anytime)

`VACUUM` the index (recovers 17.4 MB immediately, far more after Step 1). Add retention
for the 38,220 `dismissed_agents` rows and the 13,118-entry `agent_name_registry.json`.
Make `open_index` use read-only flags on query paths and drop the unconditional
`schema_version` write. Write the watchdog's stall record from a worker thread and cap
`asyncio_task_stacks` so a 2.3 MB serialization cannot extend the freeze it measures.

### On the `tui_perf.md` memory note

Report `__b` proposes amending rule 1. Rule 1 ("never block the event loop") is still
correct, and rule 2 already warns that off-the-loop is not off-the-pump. What is missing
is a GIL corollary — worth adding to rule 1 as: *for CPU-bound Python and PyO3
marshalling, `to_thread` moves work off the loop but only partially off the GIL
(~1.5× effective parallelism at 8 threads measured); additional concurrent loads make the
worst UI stall worse, not better.* Per project policy this needs the user's explicit
approval before any memory file is edited — flagging, not doing.

---

## What to measure after

The instrumentation to confirm each step already exists:

- `tui_startup.jsonl` — **Step 0**: `agents_ready` p50 back below 4.9 s. Split by
  concurrency (as in Part 1) so a quiet hour is not mistaken for a fix.
- `tui_agent_loads.jsonl` — **Steps 1–2**: slow loads per *active hour* (not per day —
  08-27 was a 13-hour day and the raw count understated it by 40%), and `load_kind`
  inverting from 96% `full` toward majority `artifact_delta`.
- `tui_stalls.jsonl` — hitch inter-arrival decoupling from the 10 s refresh tick.
- `SASE_TUI_PERF=1` → `~/.sase/perf/tui_jk.jsonl`, target p95 < 16 ms per `tui_perf.md`.
  The existing capture is from 08-14 and is stale; take a fresh baseline first.

Budgets worth adopting as regression gates: no event-loop stall above 250 ms, keystroke-
to-paint p95 < 16 ms, visible-data readiness < 2 s, and no broad auto-refresh in steady
state.

## Separate bugs found along the way

Not performance, but confirmed in the logs and worth their own task beads:

- 14 × `WorkerFailed: RuntimeError('asyncio.run() cannot be called from a running event
  loop')` in `tui.log`.
- 90+ `git rebase failed` warnings on workspace plans clones.
