---
create_time: 2026-09-19
updated_time: 2026-09-19
status: research
---

# Athena Is Out Of Memory Because Of SASE — And Agent Nodes Are Only The Third-Largest Slice

**Research question:** Athena is almost out of RAM. Is SASE the cause? Where does the
memory actually go? Can the Agents tab hold 1000+ agent nodes on a machine like Athena
without reproducing this host-level memory failure?

**Scope:** Live forensics on `athena` (Debian 13, 64 GiB RAM / 64 GiB swap, hostname
`athena`, Tailscale `athena.tail297af1.ts.net`) captured over SSH from `Kellys-MBP` on
**2026-09-19 07:45–07:54 EDT**, plus the sase checkout in workspace `sase_10` and the
already-landed Athena performance record in `docs/perf_runbook.md`. No Athena process
was killed, restarted, or reconfigured. Numbers below are measured unless marked as
estimates.

---

## Bottom line

**The suspicion is confirmed: SASE is the cause.** At 07:45 EDT, `ps` accounted for
**48.4 GiB** of RSS on a 62 GiB host. About **41 GiB of that was SASE** (agent runners,
pytest workers those agents launched, two ACE TUI processes, and other `sase` helpers).
The kernel reported **52 GiB used**, **2.6 GiB free**, **10 GiB available**, and
**25 GiB of 64 GiB swap in use**. Load average was **29 / 33 / 37**. This is not a
generic Linux leak and not Prometheus-alone: SASE owns the working set.

**The suspicion that "too many Agents-tab nodes" are the *majority* of host RAM is
denied.** Ranked RSS at the 07:45 snapshot:

| Rank | Class | Processes | RSS | What it actually is |
| --- | ---: | ---: | ---: | --- |
| 1 | `run_agent_runner.py` | 61 | **19.4 GiB** | Live SASE agent shells, including parked waiters |
| 2 | pytest xdist workers | 13 | **13.0 GiB** | `just check` / `test-cost` launched *by* those agents |
| 3 | ACE TUI (`sase tui` / `sase ace`) | 2 real | **6.6 GiB RSS + ~2.0 GiB swap** | Agents-tab process heap, twice |
| 4 | Prometheus | 2 | 2.7 GiB | Not SASE; 30-day TSDB |
| 5 | Other `sase *` | 46 | 2.3 GiB | axe routines, federation worker, stitch, jobs |

Nine minutes later the picture was even sharper. Joining `sase agent list -j` PIDs to
`/proc` RSS:

| Agent status | Count | RSS | Average |
| --- | ---: | ---: | ---: |
| **WAITING** | 50 | **16.74 GiB** | **343 MiB each** |
| RUNNING | 4 | 2.93 GiB | 751 MiB |
| QUEUED | 4 | 2.62 GiB | 671 MiB |
| TESTING | 3 | 0.04 GiB | 15 MiB |

Athena's configured runner cap is **8**
(`~/.sase/max_running_agents_override.json`, no expiry). Fifty waiters are still
holding a full Python `run_agent_runner.py` process at a third of a gigabyte each.
That single fact is most of the host emergency.

Agent **nodes** still matter, and they are not innocent. The interactive TUI is already
hydrating **~650–900** Agents-tab rows on periodic revalidate (peak **909** on a
`input_quiet_tier2_reconcile` at 07:33 EDT), while first paint only shows ~6–18 rows.
That process is **3.8 → 4.1 GiB RSS in 17 hours**, and a second abandoned
`sase ace -t agents` from **2026-09-15 14:25 EDT** is still alive at **2.9 GiB**. So the
Agents tab cannot honestly claim "1000+ nodes are fine": it is already near that count
and each TUI is a multi-gigabyte resident.

**Recommended solution (short):** treat this as two coupled bugs. (1) Parked WAITING
shells must not retain a 300+ MiB Python process — that recovers ~17 GiB immediately
and is the only way 8-at-a-time agents plus a 1000-row tab can coexist on 64 GiB.
(2) The Agents tab must stop holding a fat in-memory `Agent` roster plus Textual
`OptionList` rows plus an unbounded dismissed-bundle snapshot; keep sqlite handles,
hydrate the viewport, cap caches. Target: **one TUI, <400 MiB RSS at 1000+ nodes**.
Until (1) and (2) land, do not run two ACE sessions, and do not let several
`pytest -n 4` suites overlap.

---

## 1. Host state: Athena is in the red, and SASE is why

### 1.1 Kernel snapshot (2026-09-19T07:45:56-04:00)

```
MemTotal:       65712596 kB   (62.7 GiB)
MemFree:         2723768 kB
MemAvailable:   10568232 kB
AnonPages:      51996012 kB   (49.6 GiB anonymous)
Committed_AS:  110637476 kB   (overcommitted vs 62 GiB)
SwapTotal:      67108180 kB
SwapFree:       40801604 kB   → 25.1 GiB swap used
Load:           28.96, 32.91, 37.01   up 6d 23h
Disk /:         715G / 875G (83%)
/tmp tmpfs:     2.0G / 32G
```

`MemAvailable` at 10 GiB with 25 GiB already swapped is not "a bit busy". The
anonymous working set is ~50 GiB and is being touched: `Active(anon)` was 38 GiB.
That is why the machine feels out of memory even though `MemAvailable` is not yet
zero — the hot set does not fit, so the VM thrashes.

By 07:54, `MemFree` had fallen to **1.0 GiB** (available recovered to 14.8 GiB as
file cache filled). The emergency is current, not historical.

### 1.2 Process RSS by class (same 07:45 snapshot)

Classified from `ps -eo pid,rss,args` (KiB summed, then converted):

```
class                      n     rss_gib
sase_agent_runner         61      19.39
pytest_xdist_worker       13      12.98
sase_tui                   3       6.55   (2 Python TUIs + 1 bash wrapper)
prometheus                 2       2.72
sase_other                46       2.33
browser                   32       1.55
other                    907       1.26
prometheus_pushgateway     1       0.90
pytest                     8       0.58
python_other              16       0.14
TOTAL_PS                1090      48.40
```

SASE-attributed rows (runners + pytest workers + TUI + `sase_other`) = **41.3 GiB**,
**85%** of all process RSS. Prometheus is a real but secondary tenant (~3.6 GiB with
pushgateway). Chrome is 1.6 GiB. There is no mystery consumer hiding in `other`.

### 1.3 This is a known Athena pattern, now worse in a new way

`docs/perf_runbook.md` already recorded Athena host-pressure on 2026-09-11
(bead `sase-zn.1`): one `sase tui` at **10.0 GiB RSS + 3.2 GiB swap**, `/tmp` 62%
full of SASE cargo/core scratch. After scratch relief the TUI dropped to **766 MiB**.
On 2026-09-12 (`sase-zn.8`) a 5-hour TUI was **1.2 GiB RSS + 275 MiB swap** under
agent load.

Today's interactive TUI is **4.1 GiB RSS + 1.0 GiB swap after 17 hours**, and it is
not alone. The dominant new (or newly visible) term is **tens of parked agent
runners**, not `/tmp` scratch. Scratch placement looks fixed:
`SASE_TMPDIR=/home/bryan/.cache/sase/tmp`, `/tmp` is only 2.0G of 32G.

Disk is a separate long-term problem (bead `sase-zw`, in progress): `~/.sase` 21G,
`~/.cache/sase` 81G, `~/.local/state/sase` 116G including **36 workspace clones /
93G** for `sase-org/sase`. That is not the RAM emergency, but it is why Athena
cannot absorb another leak class.

---

## 2. Where the RAM goes, in causal order

### 2.1 Parked WAITING runners are the majority (confirmed)

`sase agent list -j` on Athena at 07:51 EDT: **61 live agents**, all
`gh_sase-org__sase`.

- 50 WAITING, 4 RUNNING, 3 QUEUED, 3 TESTING, 1 STARTING (counts drifted by one
  QUEUED between the two samples).
- `pgrep -cf run_agent_runner.py` → **60**.
- Every WAITING row had a live PID; **50/50 matched** `/proc` RSS.

Those 50 waiters hold **16.74 GiB**. Median runner RSS across the earlier 61-process
histogram was **316 MiB** (p90 381 MiB, max 794 MiB, min 21 MiB). WAITING average
**343 MiB** is not a stub. It is a full `uv` CPython 3.14 process that imported the
sase package and is sitting on `%wait` / runner-slot admission.

This contradicts the *intent* of bead `sase-za` ("Make parked runners cheap",
closed 2026-09-10). That work made the **slot poll cheaper** (capacity-only scan,
shared scan). It did not make the **waiter process small**. A parked shell still
costs as much RAM as a modest JVM.

Meanwhile the admission cap is 8:

```json
// ~/.sase/max_running_agents_override.json
{"version": 1, "limit": 8, "expires_at": null, "source": "ace"}
```

Feature flag `queue_capacity_budget` is on. The cap is therefore an *admission
budget for running work*, not a cap on resident `run_agent_runner.py` processes.
Waiters queue fairly — and each one keeps ~340 MiB forever.

RUNNING/QUEUED shells are worse per process (670–750 MiB) because they also host
the provider CLI. Four RUNNING + four QUEUED = **5.6 GiB**. Necessary. The 50
waiters are not.

**If WAITING shells dropped to ~20 MiB** (the current minimum we actually observed
on a runner), 50 waiters would be ~1 GiB instead of 17 GiB. That single change
would put Athena back inside RAM without touching the Agents tab.

### 2.2 Agent-launched pytest is the second slice (confirmed, SASE-caused)

At 07:45, 13 xdist workers summed to **13.0 GiB** (~1.0 GiB each) from overlapping
`just` invocations:

| Workspace | Workers | RSS | Suite |
| --- | ---: | ---: | --- |
| `sase_28` | 4 | 4.17 GiB | `tools/run_pytest cost` / `test-cost` (`-n 4`) |
| `sase_15` | 4 | 4.05 GiB | same pattern |
| `sase_29` | 4 | 3.73 GiB | `test-cost` (`-n 4`) |
| `sase_25` | 1 | 1.03 GiB | `test-scoped` (`-n 1`) |

These are not "the Agents tab". They are SASE agents running the sase test suite
on Athena, each worker importing Textual + the full package. Two concurrent
`test-cost -n 4` suites are ~8 GiB by themselves.

By 07:54 this had eased to **9 workers / 9.54 GiB** — still the second-largest
SASE class, and it comes and goes as agents enter TESTING.

This is the cost of using Athena as both the always-on control tower *and* the
CI box. The suite-gate token pool (`temporary_high_capacity_test_machine.md`)
limits CPU overlap; it does not limit RSS. Four 1 GiB workers × several agents
still fit in the token pool and still blow RAM.

### 2.3 Two ACE TUI processes are the third slice (confirmed, and growing)

| PID | Command | Started | RSS @07:45 | RSS @07:54 | Swap | CPU |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| **1598377** | `python -m sase tui --restart-service` | 2026-09-18 14:03 EDT (17h) | 3.72 GiB | **4.06 GiB** | 1.05 GiB | 57% |
| **1880150** | `sase ace -t agents` | 2026-09-15 14:25 EDT (**3d 17h**) | 2.83 GiB | 2.84 GiB | 1.02 GiB | 27% |
| 1880059 | bash wrapper around 1880150 | same | 2.8 MiB | 2.8 MiB | — | 0 |

smaps_rollup on 1598377: **Pss 3.86 GiB, almost all anonymous private dirty**. This
is Python heap, not shared maps. 26 threads. `current_tab` in stall logs: **agents**.

smaps_rollup on 1880150: **Pss 2.95 GiB**. Last keypress age in a hitch record:
**321,560 seconds (~3.7 days)**. tmux session `sase_accept_ghost_rows` is an
abandoned acceptance window that was never torn down. It still holds a full Agents
corpus in RAM.

`--restart-service` is **not** a slim service host. The live feature-flag blob on
PID 1598377 has `"service_host": false`. It is a second full ACE, bound to the
Agents tab, restarting axe, burning **half a core continuously** (57% CPU), and
growing **~280 MiB in the eight minutes between snapshots**.

`SASE_TUI_HEAP` is **off**. There is no `~/.sase/perf/tui_heap.jsonl`. Bead
`sase-zn.7` shipped the sampler; it was never enabled on these sessions. Bead
`sase-v3` ("ACE TUI holds 2.3–2.5 GB RSS while idle on the Agents tab", opened
2026-08-28) is still open. Today's 4.1 GiB is that same process class, larger.

Historical ceiling: **10.0 GiB RSS** on 2026-09-11 before scratch relief. The
architecture can still go there.

### 2.4 Agents-tab node count: large inbox, not the 12k archive, still too fat

The artifact index is huge, but the TUI is **not** currently materializing all of
it as rows.

**Index (`~/.sase/agent_artifact_index.sqlite`, 197 MiB):**

| Table | Rows |
| --- | ---: |
| `agent_artifacts` | **12,090** |
| `dismissed_agents` | **51,483** |
| `agent_output_variables` | 375 |
| `agent_artifact_model_aliases` | 4,355 |

- 11,038 of 12,090 artifacts are `gh_sase-org__sase`.
- 7,290 visible / 4,800 hidden.
- Status column is stale (`running` 2,824 vs `SUM(has_running_marker)` = 0).
- `record_json` payload: **158 MiB total, 13 KiB average, 680 KiB max**.
- Distinct `agent_name`: 11,791. Distinct families: 2,449.
- Dismissed bundle files: **34,328 JSON / 231.5 MiB**.

**What the live TUI actually loads** (`~/.sase/logs/tui_agent_loads.jsonl` and
`tui_startup.jsonl`):

- First paint for PID 1598377: **7–18 `agent_row_count`**, `index_row_count`
  typically 260–900. Tier 1, artifact index. `agents_ready_seconds` 3.4–13.2.
- Slow-load events (495 in the current log, 378 from PID 1598377): typical
  `tier1_index_revalidate` hydrates **~650–700 agents**; peak **909** on
  `input_quiet_tier2_reconcile` at 07:33 EDT.
- Abandoned TUI PID 1880150: max recorded load **62** agents; it still occupies
  2.9 GiB, which is a strong leak/retention signal independent of current inbox
  size.

Viewport code *intends* to be small:

```45:46:src/sase/ace/tui/data_providers/_types.py
    def requested_limit(self) -> int:
        return max(1, self.start_row + self.visible_rows + self.prefetch_rows)
```

Visible rows are clamped to 12–80, prefetch is `2 × visible`, so a first window
is ~36–240 records. The TUI then **converges toward the full non-dismissed inbox
(~700–900 objects)** on quiet-time / revalidate. That is already the "1000+
nodes" regime the user wants to support.

If TUI RSS were linear in those 900 objects, 4.1 GiB would be **~4.5 MiB per
node**, which is absurd for a row. So the per-node Option is not the whole
story. The TUI's heap is a **fat baseline plus a roster plus caches that grow
with distinct-agent and dismissed-bundle count**.

### 2.5 Why ~900 nodes still cost gigabytes (code, not guess)

Several independent retainers, all in the ACE process:

1. **Fat `Agent` / `AgentState` model.**
   `src/sase/ace/tui/models/_agent_state.py` is a dataclass with **200+ fields**,
   including monitor, gate, proc, retry, archive, clan, family pointers,
   `followup_agents: list[Agent]`, `runtime_children: list[Agent]`,
   `output_variables`, `step_output: dict`, and `proc_log_tail`. The loader
   keeps **both** `_agents` (visible) and `_agents_with_children` (unfiltered),
   plus `_hideable_agents`, `_agents_capacity_with_children`, and local-mode
   copies. One logical node is many Python objects.

2. **Textual `OptionList` is not data-virtualized.**
   `AgentList` subclasses `textual.widgets.OptionList`. `build_list()`
   (`_agent_list_build_rebuild.py`) `clear_options()` then emits an `Option`
   with Rich `Text` for every *tree-visible* row. The compositor virtualizes
   painting; the Python list of `Option` objects is the full roster. The
   render LRU (`_AGENT_CACHE_MAX = 512`) is smaller than the 900-row inbox, so
   it thrashes rather than bounding total row memory.

3. **`AgentSnapshotCache._GLOBAL_CACHE` never evicts (bead `sase-10t`, open).**
   `invalidate()` exists and has **no production caller**. It memoizes attempt
   history, retry state, and **all dismissed bundles**:

   ```python
   # src/sase/ace/tui/actions/agents/_snapshot_cache.py
   bundles = dismissed_agents.load_dismissed_bundles()  # suffixes=None → every bundle
   self._dismissed_bundles = (sig, bundles)
   ```

   `load_dismissed_bundles` with no suffix set walks **every** summary
   (`limit=None`) and `_load_bundle_paths` constructs an `Agent` per file.
   Athena has **34,328** dismissed JSON files. The in-UI revive list is capped
   (`DISMISSED_AGENT_OBJECTS_MAX = 500` in `_dismiss_memory.py`); the **module
   cache is not**. 34k fat `Agent` objects is enough, by itself, to explain
   multiple gigabytes.

4. **`_tools_cache` never pops (same bead `sase-10t`).**
   Keyed by agent identity. `invalidate_cached_tool_calls()` only stamps
   `artifact_mtime_ns = -1`. Tool-call JSON for every agent ever opened in the
   session stays for process lifetime.

5. **Periodic Agents-tab work keeps the heap hot.**
   Stall log: 411 records, mostly `tui_hitch` / `tui_hitch_recovered` on tab
   `agents`. A recent hitch in PID 1880150 was in
   `_on_countdown_tick` → `_update_agents_info_panel_impl` →
   `len(self._agents)`. A 57% CPU TUI does not let the 4 GiB fall into swap
   file pages; it keeps touching it.

6. **Duplicate session.**
   Two processes × the above. Killing the abandoned 3.7-day ACE is a 3 GiB
   gift that requires no code.

There is still no tracemalloc proof of the 34k-bundle hypothesis — the sampler
is off — but the code path is unconditional and the file count is measured.
sase-v3's "measure first" remains the right next instrumentation step; it does
not block the architectural conclusion.

### 2.6 What is *not* the RAM problem

- **`/tmp` scratch.** Fixed since `sase-zn.1`. 2.0G used of 32G.
- **The 12,090-row sqlite index as a memory map.** 197 MiB on disk. Python is
  not mapping the whole DB; it is decoding `record_json` for the rows it
  hydrates (~700 × 13 KiB ≈ 9 MiB of JSON, then many times that as objects).
- **Live `sase agent list` count (61).** Small versus 12k history. The 61
  *processes* are the problem, not the 61 *names*.
- **Prometheus** (2.7 GiB, 30-day retention) and **Chrome** (1.6 GiB): real,
  not SASE, not enough to explain 52 GiB used.
- **`tui_trace.jsonl` at 491 MiB** on disk (stale as of 2026-09-18 16:33).
  Neither live TUI has `SASE_TUI_TRACE` in its environment. Disk, not RSS.

---

## 3. Can the Agents tab hold 1000+ nodes on Athena?

**Not with the current architecture, and not on a host that also keeps 50
full-size waiter processes.**

Evidence:

- The tab is **already at ~900 hydrated nodes** on the interactive TUI and
  that process is **4.1 GiB RSS + 1.0 GiB swap**, 57% CPU, hitching on the
  Agents tab.
- Perf targets in `docs/perf_runbook.md` gate **j/k p95 < 16 ms at 1k
  agents**. They do not gate RSS. The 1k fixture in
  `tests/perf/fixtures.py` (`AGENT_SIZES = 50, 200, 1000`) is a latency
  fixture, not a heap fixture.
- First-page limit in the artifacts pane is 500
  (`AGENTS_FIRST_PAGE_LIMIT`). The Agents **tab** viewport is ~40 rows, then
  the process quietly expands to the full inbox.
- Bead `sase-v3` already called 2.3–2.5 GiB idle RSS "one to two orders of
  magnitude above what a terminal UI process should hold" in August. We are
  past that.

A 1000-node Agents tab that is safe on a 64 GiB Athena **that is also the
agent host** needs a TUI budget of roughly **≤400 MiB RSS** so that 8 running
agents (~6 GiB), a small waiter set, and one pytest suite still leave tens of
GiB for cache. 4 GiB × 2 TUI sessions is incompatible with that.

1000 **visible nodes** is a UI requirement. It is not a requirement to hold
1000 fat `Agent` dataclasses, 1000 Rich `Option`s, 34k dismissed bundles, and
an unbounded tool-call cache in one Python process.

---

## 4. Related beads (do not duplicate; this report routes through them)

| Bead | Status | Relation |
| --- | --- | --- |
| `sase-zn` | in progress | Athena TUI typing lag: memory pressure, O(corpus) refresh, unreaped scratch |
| `sase-v3` | open | Idle ACE RSS 2.3–2.5 GiB; still unattributed with heap tools |
| `sase-10t` | open | Bound `_tools_cache` and `AgentSnapshotCache`; eviction APIs never run |
| `sase-za` | closed | Parked-runner *CPU* diet; **does not bound waiter RSS** (this report's gap) |
| `sase-zd` | open | Runner-slot scan still parses most artifact dirs (8696 records / 51 MiB `runner_slots.scan.json` today) |
| `sase-zw` | in progress | Disk footprint (21G+81G+116G on Athena) |
| `sase-11n` | ready | Agents-sidecar hoods have no retention (2043 hoods historically) |
| `sase-zu` / `sase-124` / `sase-132` | mixed | Load-tiering / freshness / startup on this same archive |

The missing bead-shaped gap is **waiter-process RSS**, not another TUI j/k
pass. `sase-za` closed the poll; it did not close the process.

---

## 5. Recommended solution

Three layers. Do not skip layer A: it is most of the 64 GiB.

### A. Immediate host relief (operations, hours, no design debate)

1. **Kill the abandoned ACE.** tmux `sase_accept_ghost_rows` / PID 1880150 has
   not been keyed in 3.7 days and holds ~3 GiB + 1 GiB swap. One session, one
   TUI.
2. **Stop using `--restart-service` as a second full Agents-tab ACE** until
   `service_host` is actually a slim supervisor. Today's flag is `false`; the
   process is a 4 GiB UI.
3. **Drain or hibernate WAITING shells.** 50 waiters × 343 MiB is the
   emergency. Until code exists to hibernate them, do not launch work that
   parks dozens of `%wait` / slot waiters on Athena. Prefer `%queue` budgets
   that do not materialize a runner process until a slot is free — if the
   current launcher cannot do that, do not queue 50.
4. **Serialize heavy pytest.** One `test-cost -n 4` at a time on Athena, not
   three. The suite-gate token pool is not an RSS cap.
5. **Optional:** shorten Prometheus TSDB retention (2.7 GiB). Not SASE, not
   first.

Expected recovery if 1–4 happen: **~20–25 GiB RSS gone**, swap collapses,
TUI hitches from host thrash disappear even before heap work.

### B. Make parked waiters cheap (largest durable host fix)

Replace "one full Python runner per WAITING/QUEUED agent" with one of:

- **Deferred materialization:** the slot waiter is a row in
  `runner_slots` / `waiting.json` only. `run_agent_runner.py` starts when
  admitted. This is the correct end state under `queue_capacity_budget`.
- **Or a single waiter daemon** that parks N logical waiters in one process
  (~tens of MiB), and forks a runner only on admission.
- **Or a stub process** budgeted at <25 MiB (the size we already see on the
  cheapest runner) with no sase package import beyond a tiny supervisor.

Acceptance: **50 WAITING agents add <1 GiB RSS combined** on Athena. The
configured `max_running_agents=8` must bound *resident runner processes*,
not just LLM concurrency. Add a host metric (RSS sum of `run_agent_runner.py`
by status) to the Admin Center Perf view.

This is the Athena-scale prerequisite for 1000+ *nodes*. Nodes are display;
waiters are RAM.

### C. Agents tab: 1000+ nodes without a 4 GiB process (durable UI fix)

Build for a **handle/viewport** architecture. Do not try to make 1000 fat
`Agent` objects "a bit smaller".

1. **Roster = sqlite / artifact-index handles**, not `list[Agent]`.
   Keep `AgentState` for the selected row and maybe a small prefetch
   window (viewport + 2 screens). `_agents_with_children` must not be the
   archive.
2. **Stop loading dismissed bundles in bulk.** `load_dismissed_bundles()`
   with `limit=None` is incompatible with 34k files. Page it (the `_page`
   API already exists, limit 250). **Cap `AgentSnapshotCache`** with real
   LRU and wire `invalidate()` to dismiss/cleanup (`sase-10t`).
3. **Cap `_tools_cache`** the same way; pop on dismiss.
4. **Data-virtualize the list widget.** `OptionList` of 1000 Rich `Option`s
   will not stay at 400 MiB once node count is the actual 1000+ inbox plus
   expanded families. Render the visible strip from a slim row struct
   (`name, status, age, fold, tribe`). The pager already documents this
   pattern (`src/sase/pager/_layout.py`).
5. **Slim the row struct.** 200+ fields cannot be the list model. Split
   "Agents-tab row" from "detail-panel Agent". Nested
   `followup_agents` / `runtime_children` pointers should not pin the whole
   family graph in the list path.
6. **One TUI per host.** `--restart-service` / axe supervision must not
   clone the Agents-tab heap. If a service host is required, it should not
   import ACE widgets.
7. **Heap gate, not just j/k.** Enable `SASE_TUI_HEAP=1` on the next
   long-lived Athena ACE (`sase-v3`). Add a perf acceptance: **RSS < 400 MiB
   after 1 hour idle with a 1000-row inbox, and < 600 MiB after 24 hours.**
   Latency at 1k without an RSS cap will ship another 4 GiB TUI.

### D. Retention, so 12k does not become 50k next quarter

Index and sidecar growth is the reason every "bounded prefix" eventually
becomes an inbox of hundreds and a dismissed corpus of tens of thousands.

- Bead `sase-11n`: hood retention.
- Bead `sase-zw`: workspace / artifact / cache reaping.
- Drop stale `running` index rows (2,824 "running" with zero running
  markers) so revalidate does not treat ghosts as live.

Without retention, layer C's handle architecture still has to *index* an
unbounded corpus; it just must not *hydrate* it.

---

## 6. What "done" looks like on Athena

A machine like Athena (64 GiB, always-on TUI, ~8 running agents, 1000+
Agents-tab nodes, occasional `just check`) is healthy when:

| Signal | Today (2026-09-19 07:45–07:54 EDT) | Target |
| --- | --- | --- |
| `MemAvailable` | 10–15 GiB with 25 GiB swap used | >25 GiB, swap <4 GiB |
| `run_agent_runner.py` RSS | 19.4 GiB / 61 procs | ≈ running-only; waiters <1 GiB total |
| pytest workers | 9–13 GiB overlapping | one suite at a time, or workers << 1 GiB |
| ACE TUI count | 2 | 1 |
| ACE TUI RSS | 4.1 GiB + 2.9 GiB | <400 MiB at 1000+ nodes |
| Agents-tab hydrated `Agent` objects | ~650–900 + 34k dismissed in cache | viewport + selected + LRU |
| `SASE_TUI_HEAP` | off | on for the next soak, then a committed baseline |

Until the waiter-process and TUI-roster changes land, **do not** treat
"1000+ agent nodes in the Agents tab" as a display-only feature request. On
this architecture it is a host-OOM request.

---

## Appendix: how this was measured

All Athena commands ran as `bryan@athena` (SSH `Host athena` /
`athena.tail297af1.ts.net:34857`). Nothing was written on Athena.

- `free -h`, `/proc/meminfo`, `swapon`, `uptime`, `df -h`
- `ps -eo pid,user,rss,vsz,pmem,pcpu,etime,comm,args --sort=-rss`
- Python classifier summing RSS by `run_agent_runner.py` / xdist
  `exec(eval` / `sase tui` / `sase ace` / prometheus
- `/proc/<pid>/status` and `/proc/<pid>/smaps_rollup` for PIDs 1598377 and
  1880150
- `sase agent list -j` joined to `ps` RSS by PID
- sqlite read-only on `~/.sase/agent_artifact_index.sqlite`
- walk of `~/.sase/dismissed_bundles/**/*.json`
- `~/.sase/logs/tui_agent_loads.jsonl`, `tui_startup.jsonl`,
  `tui_stalls.jsonl`
- `~/.sase/max_running_agents_override.json`, `/proc/<tui-pid>/environ`
  feature flags
- `tmux list-panes -a`
- Code in this workspace: `AgentState`, `AgentList` / `build_list`,
  `AgentSnapshotCache`, `llm_calls/cache.py`, `dismissed_agents_bundles.py`,
  `AgentsViewport`, `_loading_apply.py`, `_dismiss_memory.py`

This report did not consult the swarm peer's `__a` write-up. Independent
prior art used: `docs/perf_runbook.md` Athena baselines, beads `sase-zn`,
`sase-v3`, `sase-10t`, `sase-za`, `sase-zw`, `sase-11n`.
