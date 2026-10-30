# TUI slowdown, October 2026: what the stall logs say and what to do first

Research date: 2026-10-30. Scope: why the TUI feels slow again, which
recent changes are implicated, and the smallest safe fix order.
Architecture and reliability first: no new refresh paths, no blocking
work on the loop or the pump, every claim tied to measured evidence.

## TL;DR

Two layers, both real:

1. **Host pressure is back.** Load ~25, swap 44 of 63 GB used,
   `/tmp` 88% full. Same shape as the September incident. A swapped
   heap turns every full GC into a multi-second freeze.
2. **The mitigations now contribute their own stalls.** The watchdog
   logs name three app-level sites: the GC-policy tick running
   `collect()` synchronously on the pump (6.5 s pump stall), the
   surface-token probe inside `os.stat` (5.9 s loop stall), and the
   post-roster warmup chain on the agents apply path (1.6 s pump
   hitch). October also added per-keystroke footprint counting and
   several new surfaces that refresh per tick.

Recommended order: host relief first (minutes, no code risk), then
take `gc.collect()` off the pump timer, then make token probes and
warmup scheduling provably non-blocking, then microbench the
footprint hot path. Details and rationale below.

## Evidence layer 1: the host (measured 2026-10-30 16:52 UTC)

| signal | now | September baseline (perf runbook) |
| --- | --- | --- |
| load average | 25.12 / 27.35 / 27.05 | 38.93 (phase-8, "under real agent load") |
| swap | 44 GB used of 63 GB | 30.4 GB used of 64 GB before relief |
| `/tmp` tmpfs | 28 GB used of 32 GB, 88% | 20 GB used, 62% before relief |
| `/` filesystem | 60% used | 97-98% during the incident |

Two differences from September: `/` has headroom now, and `/tmp`
is full of CI/verify/stress scratch dirs (`sase_v018_verify`,
`sase12_ci`, `s1ou_stress`, cargo-install dirs) rather than the old
`cargo-target` pattern. Same conclusion either way: a TUI process
with a ~1 GB heap under swap pressure pays seconds for anything
that walks the whole heap — which is exactly what `gc.collect()`
does. Host relief was the highest-leverage September fix (TUI RSS
10 GB -> 766 MB after `/tmp` cleanup and `SASE_TMPDIR` move) and
it is again the cheapest first step. The 5-minute idle-host-diet
recipe in `docs/contribute/perf-runbook.md` still applies.

Caveat: a stalled-on-swap process shows up in the watchdog
wherever the thread happened to be sampled. Some individual
stacks below may be descheduling victims rather than culprits.
The fix order accounts for this: relieve the host *before*
trusting fine-grained attribution.

## Evidence layer 2: watchdog stacks (Oct 29-30, pid 2704211)

Totals across `tui_stalls.jsonl` plus the rotated `.1`:
` tui_gc_pause` 874, `tui_hitch` 180, `tui_pump_hitch` 17,
`tui_stall` 13, `tui_pump_stall` 2 (plus recovered rows).

Individual GC pauses are small (0.06-0.09 s in the sampled
rows) but there are 874 of them: allocation churn is high and
the collector runs constantly. Three long stalls have
actionable stacks:

**A. 6.5 s pump stall inside the GC policy itself.**
`textual/timer.py _tick` -> `gc_policy.py:361 tick_safe` ->
`:353 tick` -> `gc_telemetry.py:160 _gc_callback`, i.e. a
synchronous full collection fired from the 1 s `set_interval`
pump timer. The mitigator is the freeze. A synchronous
multi-second `collect()` on a Textual timer callback violates
both rule 1 (never block the event loop) and rule 2 (pump/timer
callbacks stay thin; slow bodies go to `spawn_pump_free_task()`)
of the TUI perf notes. The idle gate (3 s quiet, no
navigation/modal, loads done, collection due) makes this fire
exactly when the user pauses to read — then punishes the next
keystroke.

**B. 5.9 s loop stall sampled inside the token probe.**
`_surface_tokens.py:166 probe_tool_runs_token` ->
`:429 _extend_stat` -> `:394 _stat_path` ->
`pathlib stat` -> `os.stat`. Two interpretations: a hung
underlying path (stale FUSE/Sync mount — the September
`SASE_TMPDIR`-under-Sync incident is precedent) or pure
descheduling with `stat` as the innocent sample. Either way
the probe runs on the loop/pump path where a 5.9 s gap is
fatal to responsiveness, and per-probe timing does not exist
yet to separate the two causes.

**C. 1.6 s pump hitch on the agents apply path.**
`_loading_refresh.py:255 _run_agents_async_refresh` ->
`_loading_disk_full.py:350 _load_agents_async` ->
`_loading_apply.py:99/615` ->
`_startup_loads_maintenance.py:351/374
_run_agents_post_roster_warmups`. The warmup *scheduling* runs
inline on the refresh task. The diff-badge and live-hint
schedulers shown below are correctly shaped (coalescing
guards, `spawn_pump_free_task`, nav-gate deferral), but the
schedulers themselves do synchronous candidate/signature work
before spawning — `_schedule_live_hint_refresh` computes
`_live_hint_candidates()` and a signature inline. On a large
roster that prefix is the suspect for the 1.6 s.

**D. Watcher-thread pileup.** The pump-stall row captured two
live `ace-fs-watcher` threads, one blocked in
`call_from_thread` -> `future.result()`. A worker that blocks
indefinitely on the loop while the loop is stalled is a
cascade amplifier, and two watcher threads suggests a
double-start leak: double callbacks, double refresh
scheduling, twice the `future.result()` exposure.

## Evidence layer 3: what changed lately (code, since Sep 15)

922 TUI commits since 2026-09-15 — roughly triple the surface
that the September measurements validated. Highest-interest
items, newest first:

- **Footprint counters on the input path (Oct 27).**
  `footprint/_tui.py` `bump()` runs on key/tab/click/palette
  paths via `_app_watchers.py` and `_event_keyboard.py`.
  Design is careful (dict bump only, 60 s daemon flush,
  `SASE_FOOTPRINT=off` kill-switch) but it still adds, per
  hit, an env lookup, a `getpid()` syscall, feature-id
  validation, and lock acquisition to the path that rule 11
  says must stay read-only. Unmeasured at this writing —
  needs a microbench, not an argument.
- **More surfaces refreshing per tick.** Statistics Footprint
  views with evidence cards and feature finder, the capacity
  inspector fed by the machine report, occupancy marks on
  Running rows, clan/member jumps, deck Context jumps, Files
  spread. Each is individually reasonable; collectively they
  widen every refresh/repaint and every navigation fan-out,
  which is precisely the mechanism behind the September
  Agents-tab hitches ("remaining hitches point at
  Agents-tab refresh/render work").
- **GC machinery (Oct 20-24).** Policy tick, census,
  telemetry, freeze-report tooling. The census is correctly
  opt-in (`SASE_TUI_GC_CENSUS=1`, default off) and
  `DEBUG_SAVEALL` doubles pause length by construction —
  keep it that way. But the base tick's synchronous
  `collect()` is now a *measured* 6.5 s freeze (item A).
- **Already-landed mitigations (keep).** Skip-unchanged row
  rendering (`patch_row` render-cache peek), bounded LRU
  caches for bead/memory/skill/completion loaders, bounded
  retained event/completion caches. These are the right
  shape and the report recommends more of the same, not
  their removal.

Related in-flight work: bead `sase-1nf.14` ("Fix the measured
GC freeze causes") is open. Coordinate with it rather than
duplicating it.

## Recommended solution, in order

**Step 0 — host relief (no code, do today).**
Run the idle-host-diet recipe: confirm `SASE_TMPDIR` is off
any Sync/FUSE mount, clear the `/tmp` scratch backlog,
re-check load/swap. Re-run the watchdog for one session
before trusting app-level attribution. September proved
this step alone moves RSS by an order of magnitude.

**Step 1 — take `collect()` off the pump timer.**
`GcPolicy.tick` must become gate-only: decide *whether* a
collection is due, then hand the collection itself to the
established slow path (`spawn_pump_free_task()` with the
scheduled/running/pending coalescing guards, cancelled at
teardown) instead of calling `self._collector.collect()`
inline in `tick_safe`. Caution for the implementer:
finalizers and weakref callbacks run on the collecting
thread, so a worker-thread collect needs a safety review of
what Textual objects own `__del__`/weakrefs; if that review
fails, the fallback is a *bounded* on-pump collect (gen-1
only, full collect reserved for the backstop with a longer
`MIN_FULL_INTERVAL_S`) — never the current unbounded full
collect on a 1 s timer. Keep the census opt-in. Success
criterion: zero pump stalls attributed to `gc_policy` over
one week of watchdog logs.

**Step 2 — make token probes non-blocking and timed.**
Add per-probe durations to the existing trace spans, move
`probe_surface_tokens` off the stall-critical path (thread
+ cached snapshot, same pattern as the agents fast path:
serve cached tokens instantly, revalidate in background),
and chase whichever root stat blocks — if one path hangs,
it is a hung-filesystem bug with a TUI symptom, not a TUI
bug. Success criterion: a quiet tick opens near-zero axe
files and stats nothing on the pump (the runbook's
idle-host CPU diet criteria).

**Step 3 — move warmup scheduling cost off the apply path.**
`_schedule_live_hint_refresh` (and siblings) must be O(1)
enqueue: compute candidates/signatures in the worker, not
inline before `spawn_pump_free_task`. Re-sweep all four
pump APIs (`call_later`, `call_after_refresh`, `set_timer`,
`set_interval`) for slow async callbacks — the July epic
missed two at phase seams and October added many more
call sites. Success criterion: `SASE_TUI_PERF=1`
key-to-paint p95 < 16 ms on every tab; `bench_tui_jk`
p50/p95/max table before vs after.

**Step 4 — microbench the footprint path, keep the kill-switch.**
Assert `bump()` < 1 us (cache pid instead of `getpid()` per
hit; snapshot the `SASE_FOOTPRINT` switch instead of
`environ.get` per hit if it measures hot). No behavior
change needed if it passes — just the number, committed as
a regression test. The `SASE_FOOTPRINT=off` escape hatch is
already the rollback plan; document it in the runbook.

**Step 5 — fix the watcher duplication.**
Ensure a single `ace-fs-watcher` instance across tab
switches and remounts; bound `call_from_thread` waits so a
stalled loop parks one coalesced callback instead of a
pileup of blocked workers.

**Reliability guardrails for all of the above** (from the
TUI perf notes, which the implementer must re-read via
memory first): no new refresh code paths — ride the cached
fast path plus background reload with last-request-wins
coalescing; selective `patch_row` updates, full rebuilds
only on membership change; debounced detail panels with
instant highlight paint; activity/navigation gates held;
re-capture tab and selection identity after every await;
stale-install detector acknowledged so a landed fix is
verified in a restarted TUI.

## What was deliberately not recommended

- Raising the stall thresholds to make the graphs green.
  That hides item A without fixing it.
- A new caching layer or new refresh architecture. The
  existing fast-path/incremental/debounce vocabulary covers
  every site found; a parallel mechanism is how the July
  epic left two slow callbacks at the seams.
- `just check-full` or broad refactors as part of this
  work. Per repo policy `just check` is the verification
  gate; the perf benches above are the acceptance gate.
