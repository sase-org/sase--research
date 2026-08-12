---
create_time: 2026-08-12
updated_time: 2026-08-12
status: research
---

# Why `sase ace` Takes >5s To Start, And What To Do About It

**Research question:** what actually consumes the >5s that `sase ace` now spends between
process launch and the startup stopwatch stopping, and which single change buys back the
most of it?

**Scope:** the `sase` repo at master `56d6bd772` and the linked `sase-core` repo at
`c1a0a73`, both on 2026-08-12, measured against Bryan's live `~/.sase` state on the
64-core `athena` host. Evidence is a mix of (a) the durable timing logs ACE already
writes, (b) direct microbenchmarks of the loader and the Rust index binding, and (c)
`strace -c` syscall counts. Where a measurement contradicts an intuition about where the
time goes, the measurement wins and this note says so.

## Bottom line

ACE's startup cost is **not** dominated by rendering, widget mounting, or Textual. It
splits into two costs, and one of them is almost entirely waste.

1. **~1.2–1.7s is Python import**, before a single line of ACE code runs. `import
   sase.ace.tui.app` pulls **2,401 modules**, 1,676 of them from `sase` itself.
2. **~2.6s (p50) to ~4.6s (p90) is the first agent load's `disk` stage**, per ACE's own
   `tui_agent_loads.jsonl`. That stage is gating: the startup stopwatch cannot stop until
   it finishes.
3. **The single largest item inside that disk stage is a repair pass that operates
   exclusively on rows the query is about to throw away.** Every call to
   `query_agent_artifact_index` re-stats the artifact directory of every `hidden = 1` row
   in the index — currently 4,706 of 6,732 rows. Measured cost: **50,877 extra filesystem
   syscalls per query**, 0.23–0.42s even with a fully warm page cache.
4. **That waste is the "progressively worse" mechanism.** The repair cost scales with the
   count of *hidden* (completed-and-dismissed) rows, which grows monotonically at roughly
   46/day and is never pruned. Startup gets slower every day you use SASE, independently
   of how many agents are actually running.
5. It also fires on **every 10s auto-refresh**, not just startup — roughly 360 times an
   hour, ~18 million wasted syscalls per hour of ACE being open.

The recommended fix is in `sase-core`, is roughly a dozen lines, and does not change any
user-visible behavior. See [Recommended solution](#recommended-solution).

## How startup is defined

`_maybe_end_startup_stopwatch()` (`src/sase/ace/tui/actions/_startup_mount.py:162`) only
stops the stopwatch once **both** `_agents_first_load_done` and `_axe_first_load_done` are
set. Widgets mount and paint their loading spinners well before that
(`_apply_startup_loading_state()`), so the number the user watches tick past 5s is
`import + max(first agent load, first axe load)`. In practice the agent load is the long
pole.

## Measurement 1 — import cost

Measured with `-X importtime`, from `/tmp`, workspace venv (Python 3.14):

| Metric | Value |
| --- | --- |
| Modules imported by `import sase.ace.tui.app` | **2,401** |
| Sum of self-time | **1.343s** |
| Wall clock, warm FS cache, best of 4 | **1.24–1.67s** |

Self-time by top-level package:

| Package | Self time | Modules |
| --- | --- | --- |
| `sase` | **1.003s** | **1,676** |
| `textual` | 0.075s | 143 |
| `rich` | 0.026s | 56 |
| `jsonschema` | 0.020s | 10 |
| everything else | <0.02s each | — |

This is not one slow import. It is 1,676 `sase` modules averaging ~0.6ms each — a flat
module explosion. Within `sase`, `sase.ace` alone is 787 modules / 0.410s, followed by
`sase.core` (88 / 0.103s) and `sase.xprompt` (83 / 0.058s).

Two concrete defects surfaced while reading the dependency chains:

- **`sase/logs/toast_log.py:20`** does a module-level `from sase.axe.state import
  read_tail_seek`. That one edge drags the whole `sase.axe` subtree — `sase.axe.state` →
  `sase.axe.lumberjack` → `sase.axe.chop_lifecycle` → `sase.axe.chop_policy` →
  `sase.agent.running` → `sase.agent.multi_prompt` → `sase.xprompt` — into a *toast
  logging* module. `-X importtime` attributes **238ms cumulative** to `sase.logs`, nearly
  all of it this chain.
- **`src/sase/ace/tui/actions/patch/_loading.py:8`** imports `unittest.mock.Mock` at module
  scope in production code, solely to run `isinstance(x, Mock)` test-double checks
  (lines 57, 59, 88, 327, 330). Production startup pays for `unittest` + `unittest.mock`
  (10 modules) to support test detection.

Neither is the headline cost, but both are unambiguous and cheap to fix.

## Measurement 2 — the agent load's `disk` stage

ACE already records this. `~/.sase/logs/tui_agent_loads.jsonl` (+ `.1`) holds 7,780
`tui_agent_load_slow` records — note this log is **censored at 2.0s**, so these are the
percentiles *of loads already known to be slow*, not of all loads.

For `source: startup` (n=458):

| Stage | p50 | p90 | max |
| --- | --- | --- | --- |
| **disk** | **2.655s** | **4.554s** | 225.4s |
| prep | 0.073s | 0.121s | 1.178s |
| apply | 0.057s | 0.099s | 0.339s |

`prep` and `apply` are already well-optimized and off the event loop. **`disk` is ~95% of
the load.** Adding the import cost gives 1.24 + 2.66 ≈ **3.9s at p50** and 1.24 + 4.55 ≈
**5.8s at p90**, which matches the reported "regularly >5s".

### The disk stage is not O(agents)

This is the key negative result, and it rules out the intuitive explanation ("you just
have more agents now"). Bucketing the same records by agent count:

| Agents in load | `disk` p50 | n |
| --- | --- | --- |
| 0–99 | 2.77s | 567 |
| 200–299 | 2.64s | 1,201 |
| 400–499 | 2.67s | 1,569 |
| 700–799 | **2.46s** | 185 |

Flat, and if anything *decreasing*. The dominant term is a **fixed overhead** paid
regardless of how much data the query returns.

## Measurement 3 — locating the fixed overhead

`load_tiered_agents` → `query_artifact_index_for_loader`
(`src/sase/ace/tui/models/_agent_loader_artifacts.py:94`) → `query_agent_artifact_index`,
a PyO3 call into `sase-core`. Direct timing against the live 103 MB index:

| Call | Time |
| --- | --- |
| `query_agent_artifact_index` (production params) | **0.45–0.67s** |
| — of which, Rust side | **0.51s** |
| — of which, Python `agent_scan_wire_from_dict` | 0.05s |

So the Python tolerant-reader conversion is not the problem; the Rust call is. Sweeping
the limits down exposes the floor:

| Query | Time | Records |
| --- | --- | --- |
| active=1000, recent=200 (production) | 0.449s | 529 |
| active=200, recent=200 | 0.418s | 400 |
| active=100, recent=50 | 0.287s | 150 |
| active=50, recent=25 | 0.262s | 75 |
| **active=0, recent=0** | **0.241s** | **0** |

**0.24s to return zero records.** For comparison, plain `sqlite3` against the same file
fetches all 27,817 `dismissed_agents` rows in 0.025s and 529 `record_json` blobs in
0.007s. The floor is not SQLite.

## Root cause — `repair_stale_rows_for_query`

`query_agent_artifact_index` (`crates/sase_core/src/agent_scan/index.rs:418`) calls
`repair_stale_rows_for_query` *before* doing any selection. At line 1258:

```rust
if !query.include_hidden {
    clauses.push("hidden = 1");
}
```

The TUI always passes `include_hidden: false`
(`src/sase/ace/tui/models/_agent_loader_artifacts.py:118`). So on every ACE refresh the
repair pass selects **every row where `hidden = 1`** and hands it to `refresh_stale_rows`
(index.rs:1493), which for each row calls `MarkerSignatures::from_artifact_dir`
(index.rs:2175). That function, per row, performs:

- 8 × `marker_signature()` — one `stat` each for `agent_meta.json`, `done.json`,
  `running.json`, `waiting.json`, `pending_question.json`, `workflow_state.json`,
  `plan_path.json`, `xprompts.json`
- 1 × `fs::read_dir()` of the artifact directory
- 1 × `stat` + `is_file()` per `prompt_step_*.json` entry found

Current index contents: **4,706 of 6,732 rows have `hidden = 1`** (4,137 of them status
`done`). So ACE stats ~4,700 directories it has explicitly asked to exclude from the
result set.

The `SELECT` is also wider than it needs to be: `refresh_stale_rows` selects
`record_json` for all 4,706 rows up front (index.rs:1499) but only deserializes it for
rows whose signature actually differs. `record_json` averages ~11.8 KB/row (79.7 MB
across 6,732 rows), so this materializes roughly **55 MB** of row data per query to use
almost none of it.

### Syscall proof

`include_hidden: true` makes `clauses` empty, so `repair_stale_rows_for_query` returns
early — which gives a clean A/B. Same index, same process, `strace -c`:

| | `include_hidden=false` (production) | `include_hidden=true` (repair skipped) |
| --- | --- | --- |
| `statx` | 46,073 (28,374 **ENOENT**) | 8,327 (4,434 ENOENT) |
| `getdents64` | 10,518 | 1,764 |
| `openat` | 5,403 | 1,026 |
| **total** | **62,009** | **11,132** |
| wall (warm cache) | 0.46s (p50 0.65s) | 0.23s |
| records returned | 529 | **858** |

**50,877 extra syscalls** to return **fewer** rows. 28,374 of the statx calls fail with
`ENOENT` — those are marker files that legitimately do not exist for terminal agents, so
the pass is re-confirming the absence of the same ~28k files on every refresh.

On a warm page cache this costs ~0.23–0.42s. At first launch, when the page cache is cold
for `~/.sase/projects` (208k files), those ~51k syscalls hit real disk — which is where
the gap between my 2.9s warm reproduction and the observed 4.6s p90 comes from.

### Why it gets worse over time

`hidden` is set when an agent is dismissed/archived (index.rs:3508). There is no retention
or pruning of hidden rows — only a wholesale `DELETE FROM agent_artifacts` on full rebuild
(index.rs:116) and per-directory deletes (index.rs:194). Hidden rows by month in the
current index:

| Month | Hidden rows |
| --- | --- |
| 202607 | 4,155 |
| 202608 (12 days) | 551 |

≈46 new hidden rows/day, each adding ~13 syscalls to **every** refresh forever. That is
the "progressively worse lately" the report describes: it tracks cumulative dismissed
agents, not current workload.

### It is also redundant

ACE already starts an inotify `ArtifactWatcher` at mount
(`_start_artifact_watcher()`, `_startup_loads.py:84`) and applies exact-artifact deltas
through `_load_agent_artifact_delta_async`. Marker changes are already detected by a
mechanism that costs nothing when nothing changes. The synchronous full repair is a second,
far more expensive detector for the same events.

## Recommended solution

**Fix the hidden-row repair pass in `sase-core`. Do the import work second, and only if
you still want it.** One change, in one function, removes the growth term and most of the
fixed cost.

### Primary — `crates/sase_core/src/agent_scan/index.rs`

Three edits to `repair_stale_rows_for_query` / `refresh_stale_rows`, in decreasing order
of payoff:

1. **Gate each row on one directory `stat` instead of 9+ file operations.** Compare the
   artifact directory's own `mtime` against the row's stored `indexed_at` before calling
   `MarkerSignatures::from_artifact_dir`. Marker files are written *into* that directory,
   so any marker change bumps the directory mtime — the cheap check is sound. This alone
   turns ~4,700 × 13 syscalls into ~4,700 × 1, cutting the ~51k overhead by roughly 92%.
2. **Bound the repair by recency.** Add `AND timestamp >= <cutoff>` (7 days is generous)
   to the `hidden = 1` clause. A `done`-and-hidden agent from five weeks ago does not
   change. This makes the pass O(recent activity) instead of O(lifetime agents), which is
   what actually kills the daily-growth term.
3. **Stop selecting `record_json` in the repair query.** Select only `artifact_dir`,
   `projects_root`, and the `*_sig` columns; fetch `record_json` lazily for the rows whose
   signature actually differs. Saves materializing ~55 MB per query.

Do 1 and 2 together; 3 is independent and cheap. Expected result: the 0.24s zero-record
floor drops to near-nothing, and the cold-cache first-launch penalty largely disappears.
Since the repair only ever *un-hides* rows that changed on disk — and the inotify watcher
already covers live changes — no user-visible behavior changes.

Verify with the same A/B used above: `strace -c` the production `include_hidden=false`
query and confirm total syscalls land near the 11k baseline rather than 62k, then
re-check `disk` p50 in `tui_agent_loads.jsonl`.

### Secondary — reduce ACE's import surface (`sase` repo)

Worth doing, but it is ~1.2s of a ~4–6s problem, and it is diffuse work across 1,676
modules. Start with the two unambiguous defects:

- Move `from sase.axe.state import read_tail_seek` in `src/sase/logs/toast_log.py:20`
  inside the function that uses it. Removes the `sase.axe` → `sase.agent` → `sase.xprompt`
  chain (~238ms cumulative) from anything that touches logging.
- Replace the module-level `from unittest.mock import Mock` in
  `src/sase/ace/tui/actions/patch/_loading.py:8` with a lazy check (or a non-`unittest`
  seam), dropping `unittest`/`unittest.mock` from production startup.

Beyond those, the systematic lever is `sase.ace` (787 modules / 0.410s): the app module
imports the full action/widget graph eagerly, including surfaces the user may never open.
Deferring per-tab widget and action subtrees to first use is the real win, but it is an
epic, not a patch, and it should be measured against `-X importtime` before and after
rather than done on intuition.

### Explicitly not the problem

Ruled out by measurement, so they should not absorb effort:

- **Textual / widget mounting / rendering.** `textual` is 0.075s of import and the `apply`
  stage is 0.057s p50.
- **Agent count.** The `disk` stage is flat from 0 to 799 agents.
- **The Python↔Rust wire conversion.** `agent_scan_wire_from_dict` is 0.05s of a 0.51s
  Rust call; `known_field_kwargs` already memoizes dataclass field names
  (`src/sase/core/wire.py:262`).
- **The 33 MB archive ProjectSpec.** `gh_sase-org__sase-archive.sase` is genuinely large
  (304k lines, 3,317 `NAME:` entries) and is parsed cold on the first load — but
  `parse_project_file` handles it in **0.20s**, and `PatchSnapshotCache`
  (`src/sase/ace/patch/cache.py`) keys on `(mtime_ns, size)` so later refreshes are free.
  It is a real but second-order cost, and worth revisiting only after the repair pass is
  fixed.

## Reproduction

```bash
# Import cost
python -X importtime -c "import sase.ace.tui.app" 2>&1 | wc -l   # module count

# Observed startup stages (censored at 2.0s)
jq -r 'select(.source=="startup") | .stages_seconds.disk' ~/.sase/logs/tui_agent_loads.jsonl

# Hidden-row share of the index
sqlite3 ~/.sase/agent_artifact_index.sqlite \
  'select hidden, count(*) from agent_artifacts group by hidden'

# The A/B: production query vs repair-skipped, under strace -c
# (differ only by include_hidden on AgentArtifactIndexQueryWire)
```

Established tooling for follow-up, per `sase/memory/tui_perf.md`: `sase ace --profile`,
`SASE_TUI_TRACE=1` (`~/.sase/perf/tui_trace.jsonl`), and the always-on stall watchdog at
`~/.sase/logs/tui_stalls.jsonl`. The trace log independently corroborates the finding —
`agents.load_from_disk` is the single largest span at p50 971ms / max 3,166ms, an order of
magnitude above the next span.
