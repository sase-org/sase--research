---
create_time: 2026-08-12
updated_time: 2026-08-12
status: research
---

# The `sase ace` Startup Critical Path

**Research question:** what consumes the >5s between `sase ace` launch and the startup
stopwatch stopping, which parts grow with accumulated SASE data, and what change buys
back the most time per unit of risk?

**Scope:** `sase` at master `56d6bd772`, linked `sase-core` at `95c5028` (release of
`c1a0a73`), measured 2026-08-12 against the live `~/.sase` state on `athena`. Three
independent investigations contributed: report **`__a`** (cached-first architecture),
report **`__b`** (import + repair-pass forensics), and this pass, which re-ran both sets
of measurements and adjudicated where they disagreed. Every figure below was reproduced
here unless explicitly attributed. Absolute times are host- and cache-specific; the
scaling behavior is the portable result.

## Bottom line

Startup is `import + max(first agents load, first axe load)`, gated by
`_maybe_end_startup_stopwatch` (`src/sase/ace/tui/actions/_startup_mount.py:162`), which
requires **both** `_agents_first_load_done` and `_axe_first_load_done` regardless of
which tab is visible. Rendering, widget mounting, and Textual are not the problem.

The verified budget, warm cache:

| Phase | Cost | Notes |
| --- | ---: | --- |
| `import sase.ace.tui.app` | **1.24–1.33 s** | 2,402 modules; serial, before any ACE code |
| AXE first load (parallel) | **0.50 s** | not the gate |
| Agents first load (parallel) | **2.0–2.2 s** warm | **the gate**; 2.66 s p50 / 4.55 s p90 in production logs |
| = stopwatch | **≈3.9 s p50, ≈5.8 s p90** | matches the reported ">5s" |

Inside the Agents load, three costs matter, and the intuitive ranking is wrong:

1. **Diff-badge classification: ~0.8 s** — the largest single warm item, and pure display
   enrichment. Report `__b` missed this entirely; report `__a` found it but under-measured
   it by roughly half.
2. **Query-time hidden-row repair: ~0.2 s warm / ~57,000 filesystem syscalls** — smaller
   warm than the badges, but it is **the only term that grows every day you use SASE**,
   it is the most cold-cache-sensitive, and it currently **repairs zero rows**.
3. **Python import: ~1.25 s** — untouchable by either fix above, and therefore the floor
   that both fixes expose.

The recommended solution is staged and starts with the badges, not the repair pass. See
[Recommended solution](#recommended-solution).

## Verified measurements

### The budget model reconciles both reports

`__a` measured a headless `AceApp` (AXE ready 1.77 s, Agents ready 3.98 s); `__b` mined
ACE's own `~/.sase/logs/tui_agent_loads.jsonl`. They look like different findings but
decompose identically once import is separated out:

- AXE ready 1.77 s ≈ 1.25 s import + 0.50 s collect (measured directly, below).
- Agents ready 3.98 s ≈ 1.25 s import + 2.69 s `agents.load_from_disk`.

Both reports are describing one budget from two ends. Use the model, not either total.

### Production timing logs

Reproduced from `tui_agent_loads.jsonl` (+`.1`), 7,819 records:

| Stage (`source: startup`, n=462) | p50 | p90 | max |
| --- | ---: | ---: | ---: |
| **disk** | **2.660 s** | **4.554 s** | 225.4 s |
| prep | 0.073 s | 0.121 s | 1.2 s |
| apply | 0.058 s | 0.099 s | 0.3 s |

**Critical caveat, from `__b` and worth keeping:** this log is censored at 2.0 s. These
are percentiles *of loads already known to be slow*, not of all loads. They are the right
numbers for "why is it sometimes >5s" and the wrong numbers for a mean.

`disk` is ~95% of the load; `prep` and `apply` are already well-optimized. Load `source`
breakdown also shows the same loader runs **6,354 `auto_refresh`** times against 462
`startup` times — every cost below is paid ~14× more often off startup than on it.

### The disk stage is not O(agents) — confirmed

`__b`'s key negative result, re-bucketed here:

| Agents in load | `disk` p50 | n |
| --- | ---: | ---: |
| 100–199 | 2.54 s | 53 |
| 200–299 | 2.49 s | 101 |
| 300–399 | 2.55 s | 115 |
| 400–499 | 2.79 s | 106 |
| 500–599 | 2.91 s | 53 |

Essentially flat across a 5× range in agent count. "You just have more agents now" is
ruled out. The dominant term is fixed overhead plus archive size, not working-set size.

### Import cost — `__b` reproduced exactly

`-X importtime`, workspace venv (Python 3.14), from `/tmp`:

| Metric | `__b` | this pass |
| --- | ---: | ---: |
| Modules | 2,401 | **2,402** |
| Sum self-time | 1.343 s | **1.264 s** |
| Wall, warm, best of 5 | 1.24–1.67 s | **1.24–1.33 s** |
| `sase` self-time / modules | 1.003 s / 1,676 | **0.964 s / 1,677** |
| `sase.ace` | 0.410 s / 787 | **0.399 s / 787** |
| `textual` | 0.075 s / 143 | **0.066 s / 143** |

Not one slow import: 1,677 `sase` modules averaging ~0.57 ms. Both of `__b`'s concrete
defects confirmed verbatim:

- **`src/sase/logs/toast_log.py:20`** — module-level `from sase.axe.state import
  read_tail_seek` drags `sase.axe` → `sase.agent` → `sase.xprompt` into a *toast logging*
  module.
- **`src/sase/ace/tui/actions/patch/_loading.py:8`** — module-level
  `from unittest.mock import Mock`, used only for `isinstance(x, Mock)` test-double
  checks. Production startup imports `unittest` to detect test doubles.

### Index scale

| Metric | Value |
| --- | ---: |
| `~/.sase/agent_artifact_index.sqlite` | 103.0 MB |
| Rows | 6,740 |
| **Hidden rows (`hidden = 1`)** | **4,706** (4,137 `done`, 501 `completed`, 68 `failed`) |
| Visible rows | 2,034 |
| `record_json` total | 80.0 MB |
| `record_json`, hidden rows only | **29.3 MB** |
| `dismissed_agents` | 27,817 |
| Hidden rows by month | 202607: 4,155 · 202608 (12 d): 551 → **~46/day** |

One correction to `__b`: it estimated the repair query materializes "~55 MB" of
`record_json` by multiplying 4,706 rows by the global 11.8 KB/row average. Hidden rows are
terminal and smaller — the real figure is **29.3 MB**. The defect is real; the magnitude
was ~1.9× overstated.

## Cost 1 — diff-badge classification (~0.8 s, largest warm item)

`normalize_loaded_agents` calls `apply_status_overrides` with the default
`classify_diff_badges=True` (`src/sase/ace/tui/models/_agent_loader_normalization.py:82`),
which wires in `_classify_diff_badges`
(`src/sase/ace/tui/models/_agent_status_overrides.py:63`) and reads every referenced
persisted diff before first paint.

A/B in fresh processes, replacing the classifier with a no-op at the *effective* call site:

| Mode | Loader time | Classify calls | Unique paths | Bytes touched |
| --- | ---: | ---: | ---: | ---: |
| production | 2.01–2.18 s | 1,173 | 489 | 52.4 MB |
| classifier stubbed | **1.21–1.32 s** | 0 | 0 | 0 |

**Saving ≈ 0.8 s, ~38–40% of loader time.** `__a` reported 0.42–0.46 s; its call and byte
counts (1,204 / 502 / 53.0 MB) match this pass almost exactly, so the discrepancy is in
the A/B harness, not the phenomenon — `__a` under-measured. (An initial attempt here
reproduced `__a`'s null result before the patch point was corrected: stubbing
`_agent_status_diff.classify_diff_badges` does nothing, because
`_agent_status_overrides` passes its own module-level reference. Worth knowing before
anyone re-measures.)

The cache in `_diff_badge.py:50` is process-local and keyed on `(path, mtime_ns, size)`,
so a fresh `sase ace` pays the full cost every launch; 1,173 calls over 489 unique paths
means ~58% of calls are same-process repeats that still pay an `os.stat`.

**The precedent for fixing this already exists in the repo.** The docstring of
`classify_live_file_change_hint` (`src/sase/ace/tui/models/_agent_status_diff.py:23`)
records that the *live VCS* pencil hint was already pulled off the loader because
"computing it inline ran hundreds of live VCS diffs on the first agents load and dominated
startup," and is now a deferred coalesced background pass. The persisted-diff classifier is
the same shape of work, one step cheaper, still on the critical path.

## Cost 2 — query-time hidden-row repair (the growth term)

### Mechanism

`query_agent_artifact_index` calls `repair_stale_rows_for_query`
(`sase-core/crates/sase_core/src/agent_scan/index.rs:1251`) *before* any selection. When
`include_hidden` is false — which the TUI always passes
(`src/sase/ace/tui/models/_agent_loader_artifacts.py:118`) — it pushes the clause
`hidden = 1` and hands every matching row to `refresh_stale_rows` (`:1493`). Per row,
`MarkerSignatures::from_artifact_dir` (`:2175`) performs 8 marker `stat`s, one
`read_dir`, and a `stat` + `is_file` per `prompt_step_*.json` found.

So a query for ~534 visible records stat-walks 4,706 directories it has explicitly asked
to *exclude*. Two amplifiers, one from each report:

- `refresh_stale_rows` selects `record_json` for all 4,706 rows up front (`:1499`) but
  deserializes only rows whose signature differs — 29.3 MB materialized to use ~none of
  it (`__b`).
- `select_records` (`:1571`) then repeats `from_artifact_dir` for **every selected row**,
  so the validation is doubled, not merely broad (`__a`; `__b` omitted this).

### Syscall A/B — and why `__a` and `__b` reported different totals

`include_hidden: true` leaves the clause list empty, so the repair returns early. Same
index, same process, `strace -c`:

| Syscall | production (`include_hidden=false`) | repair skipped |
| --- | ---: | ---: |
| `statx` | 46,127 (28,395 ENOENT) | 8,417 |
| `pread64` | 37,793 | 22,046 |
| `getdents64` | 10,642 | 1,892 |
| `pwrite64` | **7,590** | 1,313 |
| `openat` | 6,098 | 1,723 |
| `fsync` / `unlink` | 5 / 4 | 5 / 4 |
| **traced total** | **108,274** | **35,415** |
| records returned | 534 | 865 |

**Repair delta ≈ 57,000 syscalls** (statx −37,710, getdents64 −8,750, pwrite64 −6,277,
openat −4,375) — to return *fewer* rows.

This resolves the reports' apparent conflict: `__a` reported 121,292 total syscalls,
`__b` reported 62,009. Their `statx`/`getdents64`/`openat` counts agree with each other
and with this pass to within 0.3%. `__b` counted **file-metadata syscalls only** (~62 k);
`__a` counted **everything including SQLite page I/O** (~121 k). Both are correct at their
stated scope. Neither was wrong.

Note the `pwrite64` line: the read path performs ~6,300 durable writes plus `fsync` and
`unlink` before first paint. A query mutates the database it is reading.

Warm timings, fresh process each:

| Query | Time | Records |
| --- | ---: | ---: |
| production (active=1000, recent=200) | 0.504–0.602 s | 534 |
| repair skipped (`include_hidden=true`) | 0.311–0.413 s | 865 |
| **active=0, recent=0 (repair still runs)** | **0.230 s** | **0** |

The 0.230 s zero-record floor (`__b` measured 0.241 s) proves the floor is the repair pass,
not SQLite and not selection: plain `sqlite3` reads 529 `record_json` blobs from the same
file in 0.007 s.

### New finding: the repair pass currently repairs nothing

Recomputing every hidden row's marker signature in Python and diffing it against the
stored `*_sig` columns:

```text
hidden rows checked: 4706
hidden rows with a STALE signature: 0 (0.00%)
```

**Zero.** Today, on this host, ~57,000 syscalls and ~6,300 writes per query produce no
repairs at all. That is not luck — freshness is already guaranteed by two other
mechanisms:

- **`update_agent_artifact_index_for_marker_mutation`**
  (`src/sase/core/agent_artifact_index_lifecycle_mutations.py:149`) upserts the index at
  marker-write time, and has **92 call sites** across the write paths.
- ACE starts an inotify `ArtifactWatcher` at mount and applies exact-artifact deltas
  (`__b`), which costs nothing when nothing changes.

Query-time repair is a redundant third detector for events two cheaper mechanisms already
catch. That is a stronger argument than either report made, and it changes the fix: the
pass does not need to be made cheaper so much as removed from the read path.

### Why it gets worse over time

`hidden` is set on dismissal/archival and hidden rows are never pruned — only a wholesale
rebuild or per-directory delete removes them. At ~46 new hidden rows/day, each adding ~13
syscalls to **every** query, and with the loader running every 10 s by default
(`refresh_interval: int = 10`, `src/sase/ace/tui/app.py:227`), the steady-state waste is
~360 refreshes/hour × ~57,000 ≈ **20 M syscalls per hour** of ACE being open. The cost
tracks cumulative dismissed agents, not current workload. This is the "progressively
worse" mechanism.

### Correction: `__b`'s proposed mtime gate is unsound as justified

`__b` recommends gating each row on one directory `mtime` compared against the stored
`indexed_at`, justified as: "Marker files are written *into* that directory, so any marker
change bumps the directory mtime — the cheap check is sound."

**That justification is false on this filesystem.** Direct probe under `~/.sase`
(ext4):

| Write style | Directory mtime | Result |
| --- | --- | --- |
| `mkstemp` + `os.replace` (atomic) | advances | gate would fire correctly |
| `open(path, "w")` in place | **unchanged** | file mtime +1.100 s, **gate misses it** |

In-place rewrites of an *existing* marker change no directory entry, so the parent
directory's mtime never moves. And SASE has such writers:
`write_done_marker` (`src/sase/axe/runner_artifacts.py:275`) writes `done.json` with a
plain `open(done_path, "w")`, and the `run_agent_helpers_artifacts.py` read-modify-write
helpers update `agent_meta.json` in place.

The live tree already shows the violation — 1,534 of 6,740 artifact directories (**22.8%**)
have a marker whose mtime is newer than the directory's own:

| Marker newer than its directory | Dirs |
| --- | ---: |
| `agent_meta.json` | 1,500 |
| `done.json` | 51 |
| `workflow_state.json` | 30 |
| `prompt_step_*.json` | 28 |
| `waiting.json` | 1 |

The gate is still a good idea — it is just a **consequence** of making marker writes
atomic, not a substitute for it. Land it only after `write_done_marker` and its peers go
through an atomic-replace helper (several already exist, e.g.
`sase/axe/agent_meta.py:write_agent_meta_atomic`), or it will silently stop repairing the
exact rows it was added to catch. `__b`'s recency bound (item 2) has the same property in
a milder form: it is a deliberate policy choice, not an invariant.

## Cost 3 — Python import (~1.25 s), the floor both fixes expose

Nothing above touches import, which is serial and precedes everything. Once badges are
deferred and the repair pass is off the read path, the Agents load lands near AXE's
~0.5 s and **import becomes ~65–70% of remaining startup**. Do the two cheap defects with
the first patch; treat the `sase.ace` 787-module explosion as an epic, measured with
`-X importtime` before and after rather than by intuition.

## Explicitly not the problem

Ruled out by measurement — these should not absorb effort:

| Candidate | Evidence |
| --- | --- |
| **Textual / widget mounting / rendering** | `textual` is 0.066 s of import; `apply` p50 0.058 s; `__a`'s trace shows 36.0 ms to apply and 31.7 ms to display 12 rows |
| **Agent count** | `disk` p50 flat across 100–599 agents |
| **AXE collector** | **0.50 s** measured directly (`collect_axe_status_data`, `src/sase/ace/tui/actions/axe_display/_data.py:263`) — see correction below |
| **Python↔Rust wire conversion** | `agent_scan_wire_from_dict` 0.05 s of a ~0.51 s Rust call (`__b`) |
| **The 33 MB archive ProjectSpec** | `parse_project_file` handles it in 0.20 s and `PatchSnapshotCache` keys on `(mtime_ns, size)` (`__b`) |
| **Reducing the recent-completed limit** | Still validates all 4,706 hidden rows; the 0.230 s floor is limit-independent (`__a`) |
| **Deleting artifacts / rebuilding the index** | Destructive, temporary, and restores the same slope (`__a`) |
| **Moving loaders to threads** | They are already workers; the stopwatch still waits on them (`__a`) |

### Correction: AXE is not a near-term gate

`__a` treats AXE as a "second startup growth vector" needing an urgent summary/detail
split, citing AXE readiness at 1.77–1.81 s. Measured directly,
`collect_axe_status_data` takes **0.496–0.524 s** (three fresh processes) — and `__a`'s own
direct call measured 0.491 s. The 1.77 s figure is `import (1.25 s) + collect (0.50 s)`;
it is import cost attributed to AXE. Even if the Agents load dropped to zero, AXE would
gate startup at ~0.5 s, not ~1.8 s.

`__a`'s architectural point still stands as a *growth* concern — the collector eagerly
loads every lumberjack's 500-line log tail, every configured chop's run history, and run
snapshots for a 502.9 MB / 5,179-file tree while AXE is hidden — but at current scale it is
a 0.5 s item behind a 0.8 s item and a growth term. Schedule it third, not first.

## Where the two reports disagreed — resolutions

| Question | `__a` | `__b` | Resolution |
| --- | --- | --- | --- |
| Syscalls per query | 121,292 | 62,009 | **Both right.** Different scopes: `__b` metadata-only, `__a` including SQLite I/O. Measured here: 108,274 across 8 traced types |
| Import cost | not measured | ~1.2–1.7 s, 2,401 modules | **`__b`.** Reproduced: 2,402 modules, 1.24–1.33 s. A real gap in `__a` |
| Diff badges | ~0.42–0.46 s, root cause 2 | not mentioned | **`__a`, understated.** Measured here at ~0.8 s — the largest warm item. A real gap in `__b` |
| AXE | second growth vector, 1.77 s | not measured | **Neither.** Collector is 0.50 s; `__a` conflated readiness time with cost |
| `select_records` double-validation | identified | omitted | **`__a`** — confirmed at `index.rs:1571` |
| Does the archive scale the load? | yes (archive + diffs) | no (flat in agents) | **Both,** on different axes: flat in *active agent count*, linear in *hidden row count* |
| `record_json` materialized by repair | — | ~55 MB | **Overstated.** 29.3 MB for hidden rows |
| Stopwatch source path | `.../app/_startup_mount.py` | `.../actions/_startup_mount.py:162` | **`__b`** |
| The fix | new `CachedSnapshot` query mode + background reconcile | ~12-line mtime gate + recency bound | **`__a`'s direction, `__b`'s scope discipline** — see below |

The core disagreement is the fix. `__b` argues one ~12-line change in `sase-core` with no
behavior change. `__a` argues a cached-first, stale-while-revalidate architecture. Two
findings from this pass break the tie:

- **Against `__b`:** its cheap mtime gate is unsound until marker writes are atomic
  (proven above), so it is not the low-risk 12-liner it is presented as.
- **Against `__a`'s framing:** its centerpiece is a new freshness *mode* preserving
  revalidation as the default. But the repair pass repairs **zero** rows while 92 lifecycle
  upsert sites and an inotify watcher already cover freshness. The read path does not need
  a cheaper revalidation mode so much as it needs to stop revalidating.

## Recommended solution

Stage the work by measured saving per unit of risk. This ordering differs from both source
reports.

### Stage 1 — defer diff-badge classification off first paint (~0.8 s, lowest risk)

Largest verified win, no core change, no correctness surface, and an established in-repo
pattern to copy. First-paint rows with cached or unknown badge state; compute badges for
**visible rows only** in a deferred coalesced pass and patch them in, exactly as
`classify_live_file_change_hint` already does for the live VCS hint. Deduplicate the 1,173
references down to 489 paths before scheduling.

Follow-up (optional, larger): persist the badge input signature and result on the artifact
row so immutable diffs are parsed once per machine rather than once per process. `__a`'s
argument that this belongs in the Rust core rather than a third frontend-side cache is
correct.

### Stage 2 — take the hidden-row repair off ACE's read path (~0.2 s warm, kills the growth term)

Do this second by warm saving, but it is the change that stops startup degrading daily and
removes ~20 M syscalls/hour of steady-state waste.

Implement `__a`'s read-only freshness policy on
`AgentArtifactIndexQueryWire` — ACE's Tier-1 startup query skips
`repair_stale_rows_for_query` **and** the per-selected-row `from_artifact_dir` in
`select_records`, performs no artifact-tree reads and no index writes, and decodes
`record_json` directly. Keep today's revalidating behavior as the default for other
callers. Then run one coalesced revalidation pass *after* first paint, through the existing
refresh coordinator.

The correctness argument for this is stronger than `__a` made it: the pass currently
repairs 0 of 4,706 rows because the 92 lifecycle upsert sites and the inotify watcher
already keep the index fresh. This is not "accept staleness for speed" — it is removing a
third detector for events already covered, with a post-paint reconcile as the backstop.

Independently cheap and worth taking now: stop selecting `record_json` in
`refresh_stale_rows` (`index.rs:1499`) — select `artifact_dir`, `projects_root`, and the
`*_sig` columns, and fetch `record_json` lazily only for rows whose signature differs.
That benefits every remaining caller of the revalidating path.

**Do not land `__b`'s mtime gate as a shortcut here** unless you first route all marker
writes through an atomic-replace helper. If you do fix the writers, the gate becomes a good
follow-up for the background reconcile path — 4,700 × 1 syscall instead of 4,700 × 13 —
and a recency bound on top makes it O(recent activity).

### Stage 3 — the two import defects, then decide about the rest (~0.2 s now)

Move the `sase.axe.state` import in `src/sase/logs/toast_log.py:20` into the function that
uses it, and drop the module-level `unittest.mock` import in
`src/sase/ace/tui/actions/patch/_loading.py:8`. Both are unambiguous and belong in the
Stage 1 patch. After Stages 1–2, import is the majority of what remains; the `sase.ace`
787-module graph is the systematic lever and it is an epic, not a patch.

### Stage 4 — AXE summary/detail split, and make readiness visible-surface based

Split a lightweight AXE summary collector (daemon state, names, metrics, current-run state)
from log tails, chop history, and historical run detail; load the latter on AXE activation.
Then end the stopwatch when the **initially visible** tab is interactive rather than when
every hidden tab's deep data is ready. Sequenced last because AXE's real cost is 0.5 s, but
worth doing: it prevents the next hidden-tab feature from silently regressing every startup
mode, which is how this regression accumulated in the first place.

### Projected result

| After | Agents load | Stopwatch (warm) |
| --- | ---: | ---: |
| today | 2.0–2.2 s | ≈3.9 s p50 |
| Stage 1 | ~1.2–1.3 s | ≈2.5 s |
| Stages 1–2 | ~0.7–0.9 s | ≈2.0–2.2 s |
| Stages 1–3 | ~0.7–0.9 s | ≈1.8–2.0 s |

A reasonable target is warm Agents-tab time-to-interactive **under 2 s, p95 under 2.5 s**
on `athena`, with background badge-settle time reported separately. Treat the table as a
projection from component measurements, not a promise — it should be re-measured in the
real terminal, which neither source report nor this pass did directly.

## Validation

Add a scale regression fixture approximating today's host — ≥4,700 hidden rows, ~530
selected Tier-1 rows, ~15 MB of returned JSON, hundreds of repeated diff references — and
assert:

1. The startup query's syscall count is **independent of hidden-row count**.
2. The startup query performs **zero** artifact-tree `stat`/`read_dir` calls and **zero**
   writes (today it does ~57,000 and ~6,300 respectively).
3. Agents data is painted **before** background reconciliation begins, and reconciliation
   converges to the same row set a revalidating query returns.
4. Warm cached selection plus decode stays under 250 ms.
5. Badge state settles after first paint without a second full rebuild.
6. **If the mtime gate ever lands:** a test that rewrites an existing marker *in place*
   still triggers repair. This is the assertion that would have caught the unsoundness.

Regression watch: re-check `disk` p50 in `tui_agent_loads.jsonl` after each stage, and keep
`-X importtime` module counts in the loop for any import work.

## Reproduction

```bash
# Import cost and module explosion
.venv/bin/python -X importtime -c "import sase.ace.tui.app" 2>&1 | grep -c "import time:"

# Observed startup stages (log is censored at 2.0s — slow loads only)
jq -r 'select(.source=="startup") | .stages_seconds.disk' ~/.sase/logs/tui_agent_loads.jsonl

# Hidden-row share, and the growth curve
sqlite3 ~/.sase/agent_artifact_index.sqlite \
  'select hidden, count(*) from agent_artifacts group by hidden' \
  'select substr(timestamp,1,6), count(*) from agent_artifacts where hidden=1 group by 1'

# Query A/B: production vs repair-skipped (differ only by include_hidden), under strace -c
# Zero-record floor: same query with active_limit=0, recent_completed_limit=0
# Badge A/B: stub _agent_status_overrides._classify_diff_badges  <-- NOT
#            _agent_status_diff.classify_diff_badges, which is not the live reference
# Repair effectiveness: recompute MarkerSignatures per hidden row, diff vs stored *_sig
# mtime soundness: atomic (mkstemp+os.replace) vs in-place open(p,"w"), compare dir mtime
```

Established tooling, per `sase/memory/tui_perf.md`: `sase ace --profile`,
`SASE_TUI_TRACE=1` (`~/.sase/perf/tui_trace.jsonl`), and the always-on stall watchdog at
`~/.sase/logs/tui_stalls.jsonl`.

## Known gaps

- **Cold-cache amplification is inferred, not measured.** Both source reports attribute the
  2.66 s p50 → 4.55 s p90 spread to a cold page cache over `~/.sase/projects` (4.4 GB,
  208 k files) at first launch. That is plausible and consistent with ~57,000 metadata
  syscalls, but dropping the page cache requires root and none of the three passes did it.
  Note both Stage 1 and Stage 2 targets are cold-sensitive (~20 MB of diff reads; ~4,700
  scattered directories), so the ranking between them could shift cold.
- **No end-to-end measurement in a real terminal.** `__a` used a headless harness (a lower
  bound: no terminal negotiation or painting), `__b` used log percentiles, this pass
  measured components. The 3.9 s / 5.8 s totals are modeled, and the model reconciles all
  three data sets — but a `--profile` run in a real terminal is still the missing
  confirmation.
- **`__a`'s diff-volume attribution is unresolved.** Its 53 MB / 19.9 MB-unique figures
  reproduce here at the call level, but a static scan of persisted `diff_path` values on
  visible rows found only 6.4 MB unique, with 821 of 1,015 paths missing from disk. That
  implies the cost concentrates in the linked-repo commit-diff branch
  (`_classify_linked_commit_diffs` → `agent_commit_diffs`) rather than in primary diffs.
  Worth confirming before designing the persisted-badge schema in Stage 1's follow-up.
