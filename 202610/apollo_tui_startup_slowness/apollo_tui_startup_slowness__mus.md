# Profiling sase TUI startup on apollo (and in general)

Researcher: mus · 2026-10-13 · independent swarm report (`__mus`)

## TL;DR

On a quiet checkout (athena, this session) sase's TUI startup is already
**~4–5 s to agents-ready and ~7–9 s to all-surfaces-ready**, of which **~2.5 s
is pure Python import** and **~2.5–3 s is Agents-tab Python prep**. On apollo
— a 16-vCPU / 31 GiB / **no-swap** droplet that has recently run at load
150–560 with a `sase_gateway` snapshot stampede eating 6–11 cores, ~500
threads, ~1,000 SQLite handles and 8–12 GB RSS — every one of those stages
gets slower at once, and two cliff paths (full source scan ~8–11 s,
lock-busy fallback source scan ~6.7–7.4 s) become likely. The ranked fix list
is at the end. The single highest-leverage item is **not a TUI tweak at all:
fix or contain the gateway fleet-snapshot stampede and the federation
polling that feeds it**, because no startup optimization survives a host at
load 150.

## 1. What I measured, where, and what I did not

I worked in workspace `sase_13` on host **athena**
(`Linux 6.12.111+deb13-amd64`, 62 GiB RAM + 63 GiB swap, load ~8.6 at probe
time, `/` 81% full). I did **not** SSH to apollo or change anything on it;
apollo evidence below comes from (a) this repo's committed perf record, (b)
two prior apollo research notes I read as input material, and (c) live
`sase` telemetry on this host, which shares the same startup pipeline. I did
not open any peer swarm report.

Key inputs:

- `docs/perf_runbook.md` — startup cliff history, load-tiering benchmarks,
  idle-CPU-diet recipe, trace recorder docs.
- `sase/memory/tui_perf.md` (+ parent `tui.md`) — the 15 startup/perf rules,
  including "keep startup off data-scaled work" and the measure-don't-guess
  tooling list. Read as governing reference memory for this domain.
- Startup pipeline source: `src/sase/ace/tui/util/startup_clock.py`,
  `src/sase/ace/tui/app.py` (`AceApp.__init__`), `src/sase/ace/tui/actions/`
  (`startup.py`, `_startup_mount.py`, `_startup_loads_core.py`,
  `_startup_telemetry.py`), `src/sase/main/ace_handler.py` (`--profile`).
- Prior apollo findings: `apollo_high_cpu_gateway_snapshot_stampede.md`
  (2026-10-09 investigation) and `bob_cli_6l_2_1_6_apollo_health_check.md`
  (2026-10-11).
- Fresh inline probes (all read-only, seconds each): timed
  `from sase.ace.tui import AceApp` import, `-X importtime` top offenders,
  `~/.sase/logs/tui_startup.jsonl` + `tui_agent_loads.jsonl` tails,
  `~/.sase` disk breakdown, artifact-index size.

## 2. Machine profile: what "apollo" is

From the 2026-10-09 stampede note (read-only probes, two natural restarts as
experiments) plus the 10-11 health check:

| Signal | apollo value |
|---|---|
| Shape | DigitalOcean droplet, **16 vCPU, 31 GiB RAM, no swap** |
| Steady load (10-11) | **13–16** with other agents running; `cargo test` cycles 50–180 s |
| Meltdown load (10-09) | **150–180 sustained, peak 563**; gateway alone 6.6–10.9 cores (~60% kernel) |
| Gateway process | ~500 threads, **~1,023 SQLite fds** vs 1,024 soft limit, 8–12 GB RSS |
| Service history | 89.6 CPU-hours in one 11 h run; **two OOM kills** (02:46, 04:20); 4.9 GB WAL at peak |
| Recovery behavior | Pile-up returned **within ~1 min of both a service restart and a full reboot** |
| Client amplifier | **athena's TUI federation worker** polls apollo's gateway via tailscale on every Agents refresh (~7 s, up to ~18 calls/refresh), no per-host in-flight dedup or back-off, immediate retry after IPC timeout |

Root cause as established there: `FleetReadService` wraps each
`spawn_blocking(build_snapshot_blocking)` in a 4 s `tokio::time::timeout`
(`crates/sase_gateway/src/fleet_reads/service.rs` in sase-core). On timeout
only the join handle is dropped — the blocking build keeps running, the
refresh lock releases, the next request starts another build, late builds are
discarded without filling the cache, and `retain_previous_or_error` keeps
every later request a cache miss. Builds pile up at ~50/min until the 512-thread
blocking pool fills. This is a **sase-core (Rust) defect**, not TUI code, but
it dominates any TUI-startup measurement taken on apollo while it is active.

Implication for startup: on apollo, `sase tui` starts into a CPU-, memory-,
and SQLite-contended host. Import (CPU), index revalidation (SQLite + stat
storm), Python decode (CPU), and federation/axe readiness (gateway IPC) all
degrade together. Profiling startup on apollo without first checking
`uptime`, gateway CPU/threads/fds, and OOM history will misattribute host
pressure to TUI code.

## 3. sase startup pipeline and where the seconds go

### 3.1 Stage model (from `startup_clock.py` + `_startup_telemetry.py`)

`tui_startup.jsonl` splits one launch into additive fields:

- `interpreter_cli_import_seconds` — OS process start → CLI ready
- `app_module_import_seconds` — CLI ready → `AceApp` imported
- `app_construct_seconds` — `AceApp()` construction
- `compose_seconds` — Textual `compose()` consumption
- `process_start_to_on_mount_seconds` (historical: init stamp → `on_mount`)
- `on_mount_to_first_paint_seconds`, `agents_ready_seconds`,
  `visible_ready_seconds`, `axe_ready_seconds`, `all_surfaces_ready_seconds`

`on_mount` itself is deliberately light (`_startup_mount.py`: wire keymaps,
cache widget refs, apply loading state, `call_after_refresh` the background
loads). Post-first-paint services (proc reconciler, stall watchdog, heap/GC
telemetry, refresh timers) start in `_start_post_first_paint_services`.
First paint is **not** the bottleneck; everything after it is.

### 3.2 Measured: quiet-startup shape on athena (same code apollo runs)

Live tail of `~/.sase/logs/tui_startup.jsonl`, three launches today (PID
1424661, sase 0.17.1, Agents tab, `tier1_index_revalidate` / `artifact_index`):

| Field | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| interpreter + CLI import | 0.65 s | 0.73 s | 0.60 s |
| app-module import | 1.86 s | 1.92 s | 1.61 s |
| app construct | 0.46 s | 0.52 s | 0.49 s |
| compose | 0.014 s | 0.010 s | 0.014 s |
| process → on_mount | 1.23 s | 1.37 s | 1.30 s |
| on_mount → first paint | 0.45 s | 0.46 s | 0.43 s |
| **agents_ready** | **4.14 s** | **4.43 s** | **4.97 s** |
| visible_ready | 2.91 s | 3.06 s | 3.67 s |
| axe_ready | 8.28 s | 9.01 s | 9.16 s |
| all_surfaces_ready | 7.05 s | 7.64 s | 7.86 s |

Fresh inline timing agrees: `from sase.ace.tui import AceApp` = **1.95 s
wall**, `import textual.app` alone = 0.15 s, and the import pulls in **3,517
modules**. `-X importtime` cumulative leaders (i.e. the subtrees whose import
closure costs the most) include `actions.agents._core` (~1.27 s cumulative),
`_agent_enter_action`, `gate_turn(.models/.status)`, `notification_gates`,
`_metadata_search`, and `widgets/agent_detail` + `_agent_detail_state` +
`llm_calls_panel` — the Agents-tab detail stack is imported before first
paint even though its content is not visible yet.

Meanwhile `tui_agent_loads.jsonl` today shows even **tiny delta loads**
(3–6 agents, `artifact_delta` via `inflight_poll`) spending **2.4–3.1 s in
`prep`** with `disk` only 0.1–0.6 s and `apply` 0.3–1.1 s. That matches the
runbook's stage attribution for full-history loads: per-row Python work
dominates — dict-to-wire conversion (~1.3 s), `Agent` decode (~2.0 s),
agents-live filter building one field entry per row (~2.9 s) on a 13k
fixture. The Rust calls underneath are close (source scan p50 ~1.9 s vs
cached index read ~1.6 s warm); **Python per-row work is the startup tax,
not the index read itself**.

### 3.3 The two cliffs (from `docs/perf_runbook.md`, sase-zu.7/8.5)

The runbook's benchmark tables are the best "before/after" we have for the
`not machine:apollo`-style broad-query cliff, and the mechanism generalizes
to any broad default query on a big archive:

| Path (13k synthetic / 11k real archive) | Cost |
|---|---|
| Bounded Tier-1 indexed first window | p50 **~100 ms** synth / **~1.0 s** real |
| Full source scan | p50 **~8.9 s** synth / **~10.9 s** real |
| Full-history indexed (revalidating) | p50 ~9.3 s synth (parity, not faster warm) / ~3.0 s real |
| Periodic Tier-1 revalidate | ~0.14 s synth / ~1.1–1.6 s real |
| Lock-busy fallback (50 ms process-local index-lock read timeout) | **6.7–7.4 s source scan** instead of indexed |
| Live TUI startup, real archive | first paint ~0.41 s, agents_ready **~6.5 s**, one 7.2 s quiet-time reconcile |

Three trapdoors for apollo fall out directly:

1. Any startup (or auto-refresh) path that escalates to a **source scan**
   pays 8–11 s. The 50 ms lock timeout that forces that escalation
   (`62ad9b657c`) will trip constantly on a loaded host.
2. A **non-selective full-history load is not faster than the scan** on a
   warm fixture — the win is *bounded-first-then-reconcile*, not
   index-everything-up-front. A "just load it all from the index" change
   does not fix startup.
3. The remaining per-load cost after the index is Python decode/filter, and
   hidden-row repair (6.8k marker checks on the real archive) dominates
   revalidation. Old artifact dirs sit outside the bounded startup inotify
   budget, so their changes arrive via revalidation marker storms, not
   watcher deltas.

### 3.4 Host-scale context on this machine (why apollo will be worse)

`~/.sase` here is **31 GB**: projects 16 GB, cache 4.5 GB, artifacts
2.4 GB, axe 885 MB, chats 892 MB, and the **agent artifact index alone is
271 MB** (+212 MB pre-deploy backup). `/` is 81% full, `/tmp` 14%. That is a
healthy-athena picture and startup still costs 4–9 s. Apollo has less RAM,
no swap, and recent 10–500+ load — every stage in §3.2 (§3.3's revalidate
marker checks and Python decode most of all) stretches under exactly those
conditions, and the gateway stampede adds a competing 6–11-core consumer
that survives reboots.

## 4. How to profile apollo itself (machine + startup, ~15 min, read-only)

Do these **on apollo**, in order, before changing code. Each step separates
one confound so the TUI numbers that follow are attributable.

1. **Host triage (30 s).** `uptime; free -g; df -h / /tmp; ls ~/.sase/*.sqlite* -lh`
   (WAL size); `ps -o pid,pcpu,pmem,nlwp,comm -C sase_gateway` or
   `pidof -x sase_gateway`; fd count `ls /proc/<gw-pid>/fd | wc -l`; thread
   count; `dmesg | grep -i oom` / `journalctl --since '24h ago' | grep -i oom`.
   If load > ~20, gateway threads in the hundreds, fds near 1,024, or fresh
   OOM kills: stop, fix §5 item 1 first, then re-profile. Nothing else you
   measure today is valid until then.
2. **Startup split (2 min).** Quit sase TUI, run one clean launch of the
   normal command, quit, then read the newest
   `~/.sase/logs/tui_startup.jsonl` record's split fields (§3.1). Compare
   `app_module_import_seconds` (import tax), `agents_ready_seconds` (data
   path), `axe_ready_seconds` (services/federation). Re-launch 2–3× to
   separate cold page-cache from steady state.
3. **Import tax (1 min).**
   `python -X importtime -c "from sase.ace.tui import AceApp" 2>&1 | awk … |
   sort -rn | head` plus wall-clock
   `python -c "import time; t0=time.perf_counter(); from sase.ace.tui import
   AceApp; print(time.perf_counter()-t0)"` and `len(sys.modules)`.
   Expect ~2–3 s / ~3.5k modules on a quiet host; much more on apollo means
   CPU contention, not new imports.
4. **Event-loop profile (one launch).** `sase tui --profile [path]`
   (pyinstrument; see `ace_handler.py`) for the startup window. This is the
   only step that names Python functions; do it after steps 1–2 say the host
   is quiet enough to believe.
5. **Per-load stages (no new run needed).**
   `tail ~/.sase/logs/tui_agent_loads.jsonl` — `disk` vs `prep` vs `apply`
   splits `prep` (Python decode/filter) from storage. `prep`-dominated =
   code fix; `disk`-dominated = index/host fix. `source: lock busy` rows
   point at the 50 ms lock timeout.
6. **Freeze forensics + hot-path spans.**
   `~/.sase/logs/tui_stalls.jsonl` (watchdog loop/pump stalls with task
   stacks; lower `SASE_TUI_STALL_*` thresholds for short runs) and
   `SASE_TUI_TRACE=1` spans (`refresh.auto_tick`, `axe.collect` with
   `file_opens`). A quiet tick should reload ~0 surfaces and open ~0 axe
   files (`docs/perf_runbook.md` "Idle-host CPU diet").
7. **Synthetic confirmation (optional,jamin).**
   `.venv/bin/python tests/perf/bench_agent_load_tiering.py` with
   `--sase-home ~/.sase` (real archive) reproduces bounded-vs-scan-vs-revalidate
   without the TUI in the loop. Only worth it if steps 2–5 disagree.

## 5. Ranked changes to consider

Ordered by expected startup improvement on apollo per unit risk. Items 1–2
are host/scale fixes; 3–5 are the code hot path; 6–8 are deferral/bound
fixes; 9–10 are hygiene that prevents recurrence. Where a fix belongs in
sase-core (Rust) rather than this repo, I say so per the Rust-boundary rule
— the TUI must not reimplement index/gateway behavior in Python.

1. **Contain the gateway stampede; stop polling it into meltdown.**
   Single-flight the fleet-snapshot rebuild per scope (one detached in-flight
   task that always fills the cache), add failure back-off + concurrency cap,
   take `Revalidate` off the request path (sase-core
   `fleet_reads/service.rs`); on the TUI side add per-host in-flight dedup +
   back-off to the federation worker and stop immediate retry after IPC
   timeout. Until that ships, `sase service proc stop gateway` on apollo is
   the documented mitigation. Expected effect: removes the 6–11-core
   competitor that makes every other startup stage unmeasurable; no TUI-only
   change pays off while load is 150+.
2. **Guarantee bounded-first-paint for apollo's actual default query.**
   Confirm apollo's committed startup query is Tier-1 pushdown-covered
   (`agent_live_query_pushdown.py` / `KNOWN_FALLBACK_FIELDS`); an unsupported
   query must mark history incomplete and reconcile at quiet time, never widen
   first-paint reads (tui_perf rule 9). Revisit the 50 ms process-local index
   read timeout: under apollo load it converts indexed loads into 6–7 s
   source scans — retry-with-backoff or serve-stale-then-revalidate beats
   fail-to-scan. Expected effect: eliminates the 8–11 s cliff; keeps
   agents_ready in the 4–7 s band instead of 15–40 s.
3. **Cut Python per-row startup cost (the `prep` stage).**
   The runbook attributes ~1.3 s dict-to-wire + ~2.0 s `Agent` decode + ~2.9 s
   agents-live field expansion per full-history load; today's delta loads
   still burn 2.4–3.1 s `prep` for 3–6 rows. Push more fields down or into
   `KNOWN_FALLBACK_FIELDS`, decode lazily (visible rows first, details on
   highlight via the existing 150 ms debouncer), and avoid rebuilding one
   filter entry per row for non-visible fields. Expected effect: 1–3 s off
   every Agents load including startup; also fixes the slow-refresh tail.
4. **Cut the ~2.5 s import + ~0.5 s construct tax.**
   3,517 modules for first paint is the floor to attack: lazily import the
   `-X importtime` leaders (Agents detail stack, `gate_turn`,
   `notification_gates`, metadata search) until their tab/panel is first
   shown; keep the startup closure lean (the codebase already does this in
   `_agent_completion_wait_*` — extend the pattern); move update checks,
   prompt-catalog/glossary warms, and roster warmups behind first paint or
   the existing deferred-release gate. Enforce with the import-budget tests
   (`test_chop_import_budget.py`, `test_idle_cpu_diet_guardrails.py`).
   Expected effect: ~0.5–1.5 s off every cold start on any host; proportionally
   more on a contended apollo.
5. **Take revalidation off the critical path and shrink the index working set.**
   Revalidate marker storms (7–13k checks, hidden-row repair) are the real-archive
   cost; old dirs are outside the startup inotify budget so everything arrives
   via revalidation. Prefer stat-only change tokens on ticks (already the
   `ace_refresh_tokens` default — do not regress it), widen/age-tier the watch
   budget or accept staleness-with-quiet-reconcile for old dirs, and consider
   index maintenance (VACUUM/REINDEX cadence for the 271 MB SQLite file) plus
   bounding `tier1_index_revalidate` decode to changed rows. (Index lifecycle
   itself lives in sase-core: `agent_artifact_index_lifecycle_schema`.)
   Expected effect: 0.5–2 s off startup + periodic revalidates on large archives.
6. **Don't gate visible-ready on axe/federation.**
   `axe_ready` (8–9 s here) trails `agents_ready` by ~4 s and apollo's gateway
   IPC makes it worse. Keep services, proc reconciler, federation, and
   update-check timers strictly post-first-paint and off the visible-ready
   definition; show cached/partial services state with async upgrade.
   Expected effect: interactive TUI 2–4 s sooner even when services are slow.
7. **Give apollo an operating margin: swap, tmpfs/scratch, disk headroom.**
   No swap + 31 GB RAM + memory-hungry gateway/agents = OOM kills that poison
   every later measurement. Add swap (or enforce memory caps), keep
   `SASE_TMPDIR` on local fast disk per the athena host-relief baseline
   (which recovered ~10 GB swap and ~9 GB RSS by moving scratch out of sync
   and clearing 37 GB of stale cargo-target/recovery dirs), bound managed
   `cargo-targets/`, and keep `/` well under ~90%. Expected effect: removes
   the swap/OOM noise floor; makes profiles reproducible.
8. **Narrow apollo's default startup scope.**
   Start apollo's TUI with an explicit narrow tab/query (e.g. local-machine
   Agents view rather than a fleet-wide `not machine:X` query), raise the
   auto-refresh interval under load, and avoid committing broad queries
   interactively at startup. This is configuration, not code — cheapest test
   of whether the cliff is query-shape. Expected effect: immediate 2–8 s win
   if the default query is the broad one; diagnostic even if not.
9. **Keep the measurement loop closed.**
   Treat `tui_startup.jsonl` split fields + `--profile` + `TRACE` spans +
   stall-watchdog as the acceptance gate for every item above (profile before
   and after per tui_perf). Concretely: agents_ready back toward the 4–6 s
   band on apollo, quiet-tick `surfaces_reloaded=0` with near-zero
   `axe_file_opens`, zero `lock busy` fallbacks, and p95 key-to-paint < 16 ms.
   Do not land "faster on synthetic, unmeasured on apollo" — the sase-zu.8.5
   lesson is that cached-index synthetics flatter full-history paths.
10. **Sweep for rule violations at the seams.**
    Past epics missed slow async pump callbacks at phase seams and reintroduced
    unconditional full reconciles (tui_perf rules 2, 5, 10). Any new startup
    work must go through `spawn_pump_free_task()`, the fast-path
    show-cached-then-background-reload shape, and tick-revalidate (not
    recompute) cadence — with the bench + watchdog evidence attached.
    Expected effect: prevents the next 2–5 s regression rather than buying
    speed today.

## 6. Honest limits of this report

- I measured import and startup telemetry **on athena, not apollo**; apollo
  numbers are inferred from the committed benchmarks and the two prior apollo
  notes. Step §4.1–4.2 on apollo itself is required before committing to
  items 3–5 over item 1.
- I did not run `sase tui --profile`, py-spy, or the 13k bench harness here:
  each needs either a TUI launch or minutes of CPU that this single-turn
  session correctly spends on the widest-attribution evidence (telemetry +
  import splits + runbook tables) instead.
- The gateway single-flight fix is sase-core work needing the
  `sase-core-revision.txt` pin move (`docs/rust_backend.md`); a TUI-side
  back-off/dedup is the this-repo complement, not a substitute.

## Sources checked

- `docs/perf_runbook.md` (startup cliff, sase-zu.7/8.5 tables, idle-CPU recipe)
- `sase/memory/tui_perf.md`, `sase/memory/tui.md`
- `src/sase/ace/tui/util/startup_clock.py`, `src/sase/ace/tui/app.py`,
  `src/sase/ace/tui/actions/{startup,_startup_mount,_startup_loads_core,_startup_telemetry}.py`,
  `src/sase/main/ace_handler.py`
- Prior apollo research: `apollo_high_cpu_gateway_snapshot_stampede.md`,
  `bob_cli_6l_2_1_6_apollo_health_check.md` (both under
  `sase/repos/research/202610/`)
- Live local evidence: `~/.sase/logs/tui_startup.jsonl`,
  `~/.sase/logs/tui_agent_loads.jsonl`, `~/.sase` disk breakdown, timed
  `AceApp` import (1.95 s / 3,517 modules), `-X importtime` leaders.
