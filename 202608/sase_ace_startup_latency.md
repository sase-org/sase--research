---
create_time: 2026-08-12
updated_time: 2026-08-12
status: research
---

# Reducing `sase ace` Startup Latency

**Research question:** why does `sase ace` now regularly take more than five seconds
to become ready, which parts of startup scale with accumulated SASE data, and what
change will reduce both today's latency and its continuing growth?

**Scope:** local measurements on the `athena` development host on 2026-08-12, at
`sase` commit `56d6bd772` and `sase-core` commit `95c5028ae`. The investigation used
the supported TUI trace, an instrumented headless Textual run, direct timing,
`cProfile`, syscall tracing, repository history, and inspection of the Python and Rust
startup paths. Measurements describe this host's current data set and are intended to
identify scaling behavior, not to serve as portable microbenchmarks.

## Bottom line

The main problem is not rendering. `sase ace` waits for a nominally indexed Agents
load which still walks and stats thousands of artifact directories, decodes about
14.5 MB of cached records, and repeatedly reads and parses about 20 MB of diff files.
In the measured startup, the Agents load took 2.688 seconds; preparing and applying
the resulting rows took only 130 milliseconds. AXE finished sooner, at 1.77 seconds,
but startup did not finish until Agents did, at 3.98 seconds in the headless harness.
Terminal startup, cold filesystem cache, imports, and renderer setup readily account
for the user's observed total above five seconds.

The artifact index is currently used more like a self-healing filesystem scan than a
materialized view. Before answering a Tier-1 query it checks every hidden index row
(4,706 today), then checks every selected row (532 today) again. One query generated
121,292 syscalls, including 46,105 `statx` calls and 10,520 directory reads. This work
grows with archived history even though hidden history is not shown at startup.

Two recent display enrichments amplify the cost: plan-only diff classification and
linked-repository change badges cause over 1,200 diff classifications during initial
normalization. Disabling that classification reduced a warm loader run by about
30 percent. AXE has its own secondary growth problem: its initial collector eagerly
loads lumberjack logs, all configured chop histories, hundreds of run snapshots, and
a log tail for every included run even when AXE is hidden.

The durable fix is to make first paint a cached, read-only operation. ACE should read
the current artifact-index snapshot without filesystem revalidation, paint the visible
tab, declare startup complete, and reconcile freshness in a coalesced background pass.
Diff badges and deep AXE history should also be deferred or precomputed. Reducing row
limits or deleting history would only postpone the same regression.

## What “startup” currently waits for

`AceApp.__init__` performs about 180 milliseconds of synchronous configuration and
state loading. Textual then composes all three tabs, including hidden tabs. On mount,
ACE launches Agents and AXE workers in parallel. The startup stopwatch ends only after
both `_agents_first_load_done` and `_axe_first_load_done` are true, regardless of which
tab is visible.

```text
process / app construction
        |
        +-- synchronous state and configuration (~0.18 s)
        |
        +-- Textual mount
             |
             +-- Agents Tier-1 load -------- 3.98 s to ready  <-- critical path
             |
             +-- AXE full collector -------- 1.77 s to ready
             |
             +-- startup ends only after both
```

The relevant control flow is:

- `src/sase/main/ace_handler.py` constructs and runs `AceApp`.
- `src/sase/ace/tui/app/_state_init_late.py` performs synchronous startup reads.
- `src/sase/ace/tui/app/_startup_mount.py` starts post-mount workers and ends the
  stopwatch only after both Agents and AXE finish their first load.
- The Agents worker calls the Tier-1 artifact-index loader and then prepares, applies,
  and displays the rows.
- The AXE worker calls `collect_axe_status_data`, which constructs a deep snapshot of
  lumberjacks, chops, runs, and log tails.

This means moving work to a worker is not sufficient: the event loop remains
responsive, but the work is still on the semantic startup critical path.

## Measured startup

### End-to-end headless run

I ran the real `AceApp` under Textual's headless test harness, retaining the real
Agents and AXE collectors while disabling unrelated writers and long-running services.
The default tab was Agents. Times are relative to immediately before app construction.

| Milestone | Run 1 | Traced run |
| --- | ---: | ---: |
| `AceApp` construction complete | 0.182 s | comparable |
| Textual test context entered | 0.814 s | comparable |
| AXE first load done | 1.815 s | 1.767 s |
| Agents first load done | 4.097 s | 3.982 s |
| Both startup gates satisfied | 4.097 s | 3.982 s |

The harness omits normal terminal negotiation and painting costs, so it is a lower
bound on the user's interactive command rather than a contradiction of the observed
five-plus seconds. It also had a warm host filesystem for much of the run.

The supported `SASE_TUI_TRACE=1` trace attributes the dominant run as follows:

| Agents startup span | Duration |
| --- | ---: |
| `agents.load_from_disk` | 2,688.0 ms |
| Prepare 174 agents | 62.4 ms |
| Apply prepared snapshot | 36.0 ms |
| Final display of 12 visible rows | 31.7 ms |

The first expensive operation is data acquisition and normalization. Widget work is a
small fraction of the total, so optimizing Textual row painting first would miss the
critical path.

### Historical trace confirms deterioration

The retained `~/.sase/perf/tui_trace.jsonl` contains 14 startup Agents-load samples.
They are sparse and affected by machine load, but the direction is clear:

| UTC date | Samples | Minimum | Median | Maximum |
| --- | ---: | ---: | ---: | ---: |
| 2026-07-07 | 1 | 389 ms | 389 ms | 389 ms |
| 2026-07-15 | 6 | 1,037 ms | 1,496 ms | 3,166 ms |
| 2026-07-18 | 3 | 1,192 ms | 1,384 ms | 1,451 ms |
| 2026-07-28 | 2 | 1,778 ms | 2,003 ms | 2,228 ms |
| 2026-07-29 | 2 | 2,023 ms | 2,059 ms | 2,094 ms |
| 2026-08-12 | 1 | 2,688 ms | 2,688 ms | 2,688 ms |

This is not a clean controlled time series, but it is consistent with an operation
whose cost rises with retained artifact and diff history.

## Root cause 1: the artifact-index query re-walks the archive

The current host data set is large enough to expose the query's scaling behavior:

| Data set | Current size/count |
| --- | ---: |
| `~/.sase/projects` | 4.4 GB, 208,103 files |
| Artifact subtrees | 14,723 directories, 146,719 files |
| `~/.sase/agent_artifact_index.sqlite` | 99 MB |
| Indexed agent artifacts | 6,737 rows |
| Hidden index rows | 4,706 rows |
| Visible index rows | 2,031 rows |
| Indexed JSON payload | about 80 MB |

The ACE Tier-1 query asks for active artifacts plus the 200 most recent completed
artifacts, excludes hidden records, and caps active results at 1,000. On this host it
returns 532 unique records:

| Tier component | Rows | Query time | Approximate returned representation |
| --- | ---: | ---: | ---: |
| Active only | 343 | 0.318 s | 2.27 MB |
| Recent completed only | 200 | 0.415 s | 12.42 MB |
| Combined and deduplicated | 532 | 0.495 s | 14.55 MB |

All 343 records classified as active are `ace-run` artifacts. Of these, 203 have a
waiting marker and no workflow, 71 have a running workflow, and the remainder include
failed or completed workflows without a `done` marker. That breadth is intentional:
“active” means either not done or workflow non-terminal. The problem is therefore not
simply a mistaken high result limit.

The surprising cost is in
`sase-core/crates/sase_core/src/agent_scan/index.rs`:

1. `query_agent_artifact_index` calls `repair_stale_rows_for_query`.
2. Because `include_hidden` is false, repair selects every hidden row so a newly
   visible record cannot be filtered out by stale indexed state.
3. For each of today's 4,706 hidden rows, `MarkerSignatures::from_artifact_dir` stats
   marker paths, reads the directory, and stats prompt-step files. Changed rows may be
   rescanned and written back to SQLite.
4. `select_records` then repeats marker-signature collection for every selected row
   before decoding its cached `record_json`.

Thus a query for 532 visible Tier-1 records validates roughly 5,238 directories before
it returns. It is O(hidden archive + selected rows), not O(selected indexed rows).

One syscall-traced Tier-1 query returned the same 532 records and made:

| Syscall | Calls | Interpretation |
| --- | ---: | --- |
| All syscalls | 121,292 | Total query activity |
| `statx` | 46,105 | Marker and prompt-step checks; 28,387 were expected misses |
| `getdents64` | 10,520 | Almost exactly two reads per checked artifact directory |
| `openat` | 5,400 | Directory, marker, and database access |
| `pread64` | 37,593 | SQLite and file reads |
| `pwrite64` | 7,653 | Query-time self-healing writes |

The query also issued `fsync` and unlink operations. In other words, the read path can
perform synchronous repair and durable writes before first paint.

For comparison, a read-only SQL query implementing the same active/recent visibility
selection, followed by Python JSON decoding but no artifact-directory revalidation,
took 0.183–0.204 seconds over three runs. It returned the same 532 current snapshot
rows and decoded 14,478,921 bytes. This does not prove the entire loader can finish in
200 milliseconds, but it demonstrates that most of the index-query cost is freshness
validation rather than selection.

### How this entered the path

Repository history shows that the behavior accumulated through individually sensible
correctness and startup changes:

- `sase-core` commit `7ae7277` added per-selected-row self-healing.
- `sase-core` commit `b70847b` added broad stale-row repair, including hidden rows that
  might need to become visible before filtering.
- `sase` commit `c029ba2da` and its core companion later bounded active startup work
  and moved some stale-terminal cleanup to the background, but retained unconditional
  hidden-row repair.
- `sase` commit `f4639414a` moved stale schema rebuilding off startup, establishing the
  right architectural precedent: repair belongs outside first paint.

The remaining query-time repair now dominates at this host's archive size.

## Root cause 2: diff badges repeatedly parse large files

After the Rust query returns, Python normalizes status and derives display badges.
Profiling the loader shows a second material cost:

| Profiled work | Calls | Cumulative time under profiler |
| --- | ---: | ---: |
| Tiered agent loading | — | 2.365 s |
| Status normalization/overrides | — | 1.311–1.345 s |
| Diff-badge classification | 1,202 | 1.260 s |
| `diff_text_has_real_edits` | 393 | 1.030 s |
| `changed_files_from_diff` | 393 | 1.027 s |
| Diff-header `shlex` parsing | 6,722 | 0.538 s |

Profiler overhead exaggerates absolute time, so I also measured an unprofiled A/B test
in three fresh processes. The normal loader took 1.382–1.414 seconds; replacing diff
classification with a no-op took 0.949–0.995 seconds. The warm-process saving was
0.42–0.46 seconds, or about 30 percent of loader time.

Instrumentation recorded 1,204 classification calls over 502 unique diff paths.
Those calls read 53.0 MB in total, representing 19.9 MB of unique file content. The
current cache is process-local and keyed by mtime, so every new `sase ace` process pays
the cold read and parse cost. Duplicate references also repeat metadata checks.

Two feature additions explain why this work became more prominent:

- `575e6b45d` (2026-06-10) added plan-only diff classification.
- `c962280a9` (2026-07-07) expanded linked-repository change badges.

The badges are valuable, but they are enrichment rather than data required to make the
Agents table interactive. Computing all of them before first paint makes startup scale
with diff size and reference count.

## Root cause 3: hidden AXE eagerly loads deep history

AXE was not the critical path in the measured run, but it is a second startup growth
vector. `collect_axe_status_data` loads:

- status, metrics, and up to 500 log lines for every lumberjack;
- every configured chop and a bounded terminal-run history;
- run snapshots and up to 500 log lines for every included run; and
- background-command status.

The current `~/.sase/axe` tree is 496 MB and contains 10 lumberjacks, 33 chops, and 335
run snapshots. A direct collector call took 0.491 seconds after import; in the real
startup worker AXE became ready at about 1.77–1.81 seconds. Commit `487a0c20d`
(2026-05-11) added chop-run history and caching to this full startup collector.

The problem is architectural even while it remains secondary: ACE collects deep AXE
details when AXE is hidden, and then makes their completion a condition of Agents-tab
startup. Continued AXE history growth can eventually make this branch critical too.

## Why obvious smaller fixes are insufficient

| Candidate | Likely effect | Why it is not the durable answer |
| --- | --- | --- |
| Reduce the 200 recent-completed limit | Less JSON decode and normalization | Still validates all 4,706 hidden rows and all active rows; loses useful history |
| Delete old artifacts or rebuild the index | Immediate local relief | Destructive, temporary, and allows the same slope to return |
| Move loaders to threads | Preserves event-loop responsiveness | They already run as workers and the stopwatch still waits for them |
| Optimize only diff parsing | Saves roughly 0.4 s warm | Leaves the archive-wide revalidation and 121k-syscall query intact |
| Cache only within the process | Helps refreshes | A fresh CLI process has a cold cache on every launch |
| End the spinner earlier without moving work | Improves the metric cosmetically | Does not make the visible tab interactive sooner or remove resource use |

## Proposed architecture

### 1. Add a cached-snapshot freshness mode in `sase-core`

Extend `AgentArtifactIndexQueryWire` with an explicit freshness policy, for example
`CachedSnapshot` and `Revalidate`. Preserve the current revalidating behavior as the
default for compatibility, but have ACE's startup Tier-1 query request
`CachedSnapshot`.

In cached-snapshot mode, the Rust query should:

- skip `repair_stale_rows_for_query`;
- skip `MarkerSignatures::from_artifact_dir` for selected rows;
- perform no artifact-tree reads and no index writes;
- select and decode the current materialized `record_json` view directly; and
- retain a narrow fallback for a missing, corrupt, or schema-incompatible index.

This changes the startup complexity from O(hidden archive + selected filesystem rows)
to O(selected indexed rows). The important win is not merely the measured 0.3 seconds
on a warm direct query; it is removal of tens of thousands of cache-sensitive
filesystem calls whose count currently rises with history.

### 2. Reconcile after the visible table is interactive

Immediately after the cached Agents snapshot is painted, launch one coalesced
background revalidation pass. Reuse the existing refresh coordinator and row-patching
path so changes discovered by repair update the current view without rebuilding it
multiple times.

Normal lifecycle writes and artifact watchers should remain the primary freshness
mechanism. The broad hidden-to-visible audit should become bounded, low-frequency
maintenance rather than a prerequisite of every query. A crash can then produce a
briefly stale cached first paint, but the post-paint reconcile restores correctness.
This is the same deliberate stale-while-revalidate tradeoff already used by responsive
UIs and is preferable to making every launch prove the entire archive fresh.

### 3. Move badge enrichment behind first paint

Do not classify every referenced diff during initial status normalization. First paint
rows with either cached badge values or an unknown badge state, then calculate badges
for visible rows and patch them in. Deduplicate paths before scheduling work.

As a follow-up, persist badge inputs and results in the core artifact index: at minimum
the diff signature (mtime/size or content identity) and aggregate booleans needed by
the UI. Update them when the artifact row is upserted. This avoids parsing immutable or
unchanged diffs once per process and keeps shared domain classification in the Rust
core rather than another frontend-specific cache.

### 4. Split AXE summary from AXE details

Create a lightweight AXE summary collector for startup: daemon state, names, metrics,
and enough current/latest-run state to render the top-level rows. Load log tails, chop
history, and historical run details on AXE activation or item selection. Cache those
details independently so switching tabs remains fast.

### 5. Make readiness visible-surface based

The startup stopwatch should end when the initially visible tab is interactive, not
when every hidden tab's deep data is ready. For an Agents launch, the cached Agents
snapshot is the gate. For an AXE launch, the lightweight AXE summary is the gate.
Hidden tabs can retain localized loading indicators until their deferred work finishes.

This is not merely changing a metric: it makes the critical path match the user's
actual surface and prevents future hidden-tab features from silently regressing all
startup modes.

## Validation and rollout

Implement the change in separable stages so correctness and latency are both visible:

1. Add the core cached-snapshot mode and unit tests proving it performs no
   artifact-directory reads or writes.
2. Switch only ACE's startup Tier-1 query to that mode; run the normal revalidation
   immediately after first paint and compare the before/after row sets in diagnostics.
3. Defer diff classification, measuring first-paint time and badge-settle time
   separately.
4. Split AXE summary/detail collection and make the stopwatch visible-tab-aware.
5. After an observation period, reduce broad repair frequency if existing lifecycle
   updates and watchers demonstrate reliable freshness.

Add a scale regression fixture approximating today's host: at least 4,700 hidden rows,
500 selected Tier-1 rows, roughly 15 MB of returned JSON, and hundreds of repeated diff
references. The important assertions are:

- cached-snapshot query syscall count is independent of hidden-row count;
- cached-snapshot mode does zero artifact-tree `stat`/`read_dir` operations and zero
  writes;
- warm cached selection plus decoding stays below 250 milliseconds on the benchmark
  host;
- Agents data is painted before background reconciliation begins;
- reconciliation eventually produces the same state as a revalidating query; and
- adding hidden archive rows does not materially change startup duration.

For the whole TUI, a reasonable first target is a warm Agents-tab time-to-interactive
below two seconds and p95 below 2.5 seconds on `athena`, with a separately reported
background-settle time. The raw measurements suggest the cached query and deferred
diff work could bring the loader into roughly the 0.6–0.8 second range, but this should
be treated as a projection until measured in the terminal application.

## Recommended solution

Implement a **cached-first, stale-while-revalidate startup path**. Add a read-only
`CachedSnapshot` mode to the Rust artifact-index query and use it for ACE's initial
Agents load, paint that snapshot, and only then run one coalesced background repair.
In the same startup contract, defer diff-badge computation to visible-row enrichment,
split AXE's lightweight summary from its logs and run history, and end readiness when
the initially visible surface is interactive.

This is the recommended solution because it removes the dominant O(hidden archive)
work rather than tuning its current constants. It also addresses both secondary growth
paths without sacrificing eventual freshness or useful history. At today's scale it
should remove tens of thousands of startup filesystem operations and most of the
roughly 0.4-second diff tax, while making future startup cost depend on what ACE shows,
not on everything SASE has ever retained.
