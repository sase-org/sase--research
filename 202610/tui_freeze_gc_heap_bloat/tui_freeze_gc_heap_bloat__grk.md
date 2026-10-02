# The TUI's 10% freeze budget: forensics and a fix order

_Independent research (researcher `grk`) into the claim in
`research:202610/prompt_space_and_project_cycle_latency/prompt_space_and_project_cycle_latency.md`
that the live TUI spends about 10% of wall time frozen in ≥1.5 s event-loop
hitches. Goal: quantify the freeze, name the stacks that actually occupy it,
and recommend a solution that will move that number._

Measured 2026-10-02 against the live `sase tui --restart-service` process
**PID 872820** (CPython 3.14.7, Textual 8.2.8, editable checkout
`/home/bryan/projects/github/sase-org/sase`), using
`~/.sase/logs/tui_stalls.jsonl{,.1}`, `~/.sase/logs/tui_agent_loads.jsonl`,
`~/.sase/logs/tui_startup.jsonl`, `/proc/872820`, and the TUI source in this
workspace. I did not consult the other researchers in this swarm.

## Bottom line

The 10% claim is real, and on today's log it is slightly worse.

Over **3.95 hours** (10:27–14:23 local, 2026-10-02) the watchdog recorded
**422 loop recoveries** for PID 872820. Merging overlapping hitch/stall
intervals gives **1,598 s frozen = 11.3% of wall**. Median recovery is
**3.87 s**; p90 is 5.22 s; max is 10.07 s. The rate is **107 loop hitches per
hour**. Every row is on the **Agents** tab.

That freeze is **not** the `<space>` / `<ctrl+n/p>` MRU path. MRU validation
occupies **1.6%** of freeze-seconds (four episodes, including the 8.51 s
`ctrl+p` already named in the source note). Full-GC stacks do not appear in
any ≥1.5 s hitch start. The freeze is an Agents-tab, every-second-tick plus
GIL-starvation problem:

1. **The 1 s countdown timer does too much work on the UI thread.**
   `_on_countdown_tick` patches every ticking runtime suffix through
   `aggregate_clan_runtime` (Rust FFI + `dataclasses.asdict` per clan),
   rebuilds the info-panel metrics by walking the whole roster to *build a
   cache key*, and kicks an in-flight marker poll. 87 hitch starts, **328 s
   (20%)** of loop freeze, stacks sitting in that tick.
2. **Textual's compositor timer then repaints the dirtied Agents list.**
   `_on_timer_update` → `_compositor_refresh` → `Strip.divide` allocating
   `FIFOCache(4)` per chop. 89 hitch starts, **353 s (21%)**.
3. **Fleet projection runs `resolve_clan_tribe` on the pump** after the
   catalog worker returns. 56 hitch starts, **204 s (12%)**.
4. **Worker threads starve the GIL.** `tui_agent_loads.jsonl` for this PID
   records **1,612 loads / 8,460 s of disk+prep+apply** across the process
   lifetime, **924 of them `inflight_poll`** (mean 5.0 s, 4,578 s total).
   Disk+prep run in `asyncio.to_thread` and hold the GIL during Python
   JSON/stat work. 53 hitch starts are sampled in `selectors.poll` with a
   3.6 s median — the loop was idle, the beacon could not run. This inflates
   every other stack's apparent duration.

A fifth, smaller UI-thread trap: `current_config_token()` **starts a daemon
`threading.Thread` from timer callbacks** (`LaunchContextSource._tick` and
tribe-collapse config reads). `Thread.start()` waits until the child
acquires the GIL and signals `_started`. 21 hitch starts, **86 s (5%)**.

**Recommended solution:** treat this as its own track, sequenced ahead of
(or in parallel with) the MRU-snapshot work. The first two code changes —
stop treating `agent_meta.json` mtime bumps as in-flight dirty, and make the
1 s tick O(changed-display-text) — should cut most of the 11%. Details in
[Recommended solution](#recommended-solution).

## How the 10% is measured

The always-on watchdog (`src/sase/ace/tui/util/stall_watchdog.py`) is a
daemon thread that pings the asyncio loop with `call_soon_threadsafe` every
0.5 s. A **hitch** is a ≥1.5 s gap (`SASE_TUI_HITCH_THRESHOLD_SECONDS`); a
**stall** is a ≥5 s gap. A second beacon goes through Textual
`call_later` and records `tui_pump_hitch` / `tui_pump_stall`.

Implications that matter for this number:

- **Start stacks are the forensic ones.** Recovery stacks are often already
  back in `selectors.poll` after the work finished. Attribution below uses
  hitch/stall *start* stacks, with duration taken from the matching
  recovered row.
- **Loop and pump events overlap.** Summing every recovered duration
  double-counts (raw 1,926 s = 13.6%; merged union 1,624 s = 11.4%). The
  11.3% figure is **loop-only merged intervals**. Pump-only merged time is
  249 s (1.8%); almost all of it sits inside a loop hitch.
- **Hitch logging is rate-limited to 4 records/minute.** 35 loop hitches
  were suppressed across 414 recorded starts (max burst skip 3). Recovery
  is also skipped for those, so 11.3% is a slight **lower** bound on
  episode count. Duration of a recorded episode is still the full gap.
- **A start stack names the frame that held the GIL when the beacon went
  late.** Under host load (this machine: 64 CPUs, load 28–33 while
  measuring) that frame may be cheap work plus seconds of GIL wait. The
  `selectors.poll` population proves the inflation: the loop was in C,
  idle, and still accrued a 3.6 s hitch.

The source note's "317 hitches, median 3.6 s, 10% of the last 3 hours" is
the same PID and the same files, sampled a couple of hours earlier. My
window is 3.95 h and includes the 13:30–14:20 rise (see below).

## Freeze time over the session

Loop-recovered freeze per 10-minute bin (duration / 600 s):

| local | n | frozen s | % of bin |
| --- | ---: | ---: | ---: |
| 10:30 | 12 | 29 | 5 |
| 10:50 | 29 | 75 | 13 |
| 11:30 | 21 | 77 | 13 |
| 12:00 | 20 | 78 | 13 |
| 12:50 | 23 | 88 | 15 |
| 13:40 | 20 | 91 | 15 |
| 14:00 | 22 | 119 | **20** |
| 14:10 | 20 | 109 | **18** |

The fraction grows as the session ages. That is app-state growth (more live
rows, more Rich trees, more in-flight agents feeding the poll) on top of a
busy host, not a one-shot keystroke bug.

78% of recovered rows have `last_keypress_age_s > 5`. Only 17 loop starts
have keypress age ≤ 2 s. The freeze is mostly **idle-on-Agents-tab** work.

## Attribution (loop freeze-seconds)

PID 872820, 10:27–14:23 local, hitch+stall *start* class × recovered
duration. Classes are exclusive, first match wins.

| Start class | n | freeze s | % | median s | max s | What the stack is in |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Compositor timer | 89 | 353 | 21.4 | 4.07 | 10.06 | `textual/screen.py:_on_timer_update` → `_compositor_refresh` → `strip.divide` / `_styles_cache` / `FIFOCache.__init__` |
| Countdown tick | 87 | 328 | 19.9 | 3.80 | 6.41 | `_on_countdown_tick` → `_patch_agent_runtime_rows` → `aggregate_clan_runtime`, or `_update_agents_info_panel` → `bulk_ack_roster_universe` |
| Other | 82 | 332 | 20.1 | 4.02 | 7.60 | launch-context peek/stat, CSS match, neighbor index, `_prompt_input_active` DOM walk, self-pipe wakeup, prompt-panel neighbors |
| Fleet projection | 56 | 204 | 12.4 | 3.52 | 5.86 | `_run_agents_fleet_refresh` → `project_clan_tree` → `resolve_clan_tribe` |
| Selector idle | 53 | 198 | 12.0 | 3.62 | 6.75 | `selectors.py:select` / `poll` — loop idle, beacon late |
| `Thread.start` wait | 21 | 86 | 5.2 | 4.22 | 5.88 | `current_config_token` → `threading.Thread.start` → `Event.wait` |
| `renderable_digest` | 20 | 81 | 4.9 | 3.90 | 7.81 | `PromptPanel.update` hashing the whole Rich tree |
| MRU / `ctrl+p` | 4 | 26 | 1.6 | 8.51 | 8.51 | `load_launchable_vcs_xprompt_mru` / `ws_detect_workflow_type` / `subprocess.run` |
| Artifact file IO | 6 | 25 | 1.5 | 4.32 | 5.41 | `select_prompt_file` / `read_reply_chunks` / `_stat_signature` |
| Project records | 3 | 12 | 0.7 | 4.20 | 5.20 | `list_project_records` / `project_alias_map` |
| Auto-refresh body | 1 | 4 | 0.3 | 4.14 | 4.14 | `_run_auto_refresh` (the loader itself is usually off-thread) |
| **Loop total** | **422** | **1,648** | **100** | **3.87** | **10.07** | merged wall 1,598 s / 11.3% |

Leaf-function counts on start stacks that back the table: 51×
`aggregate_clan_runtime`, 58× `selectors.select`, 26× `resolve_clan_tribe`,
23× `threading.Thread.start`, 28× `renderable_digest._update_*`, 14×
`bulk_ack_roster_universe` (via `enum.__hash__` on identity tuples).

## Cause 1 — the 1 s countdown tick is a full Agents refresh

`src/sase/ace/tui/actions/_startup_mount.py` installs
`set_interval(1, _on_countdown_tick)`. On the Agents tab, when the nav gate
and prompt-input gate are quiet, `_on_countdown_tick`
(`_event_countdown.py:36–49`) always does three things:

1. `_update_agents_info_panel()`
2. `_patch_agent_runtime_rows()`
3. `_poll_starting_agent_transitions()` (in-flight marker poll)

There is already a `runtime-tick-caches` fast path
(`AgentList.patch_active_runtime_rows`): skip painting when the suffix
plain text is unchanged. **The skip happens after the expensive compute.**
Every ticking row still calls:

```
build_runtime_suffix
  → compute_row_runtime
    → _aggregate_runtime
      → aggregate_clan_runtime(list(runtime_members), now=now)
        → rust_aggregate([asdict(m) for m in members], now)
```

`_aggregate_runtime` caches the member *wires*, then still crosses into
Rust with a freshly `asdict`'d list **every second for every live clan /
session row**. Under GIL contention that FFI+copy is what the watchdog
photographs (51 start stacks).

The info-panel side has a similar footgun. `_agent_info_metrics`
(`_display_detail_info.py:42–77`) caches the result, but **constructing the
cache key walks the bulk-ack universe every call**:

```python
bulk_universe = bulk_ack_roster_universe(self)
bulk_key = tuple((agent.identity, agent.status) for agent in bulk_universe)
cache_key = (id(self._agents), frozenset(unread_ids), status_key, bulk_key)
```

`bulk_ack_roster_universe` concatenates `_agents_query_result`,
`_agents_with_children`, and `_agents`, hashing every identity. 17 hitch
starts are sampled inside `enum.__hash__` on that walk. A cache that costs
the walk to decide it is hot is not a cache.

The prompt-input gate used to skip this tick is itself a full DOM query:
`_prompt_input_active()` does `bool(query(PromptInputBar))` →
`walk_children`. Nine hitch starts include that walk (watcher dispatch and
the tick gate).

## Cause 2 — compositor timer paints the dirtied list

Textual's screen update timer (`_on_timer_update` → `_refresh_layout` →
`_compositor_refresh`) accounts for as many freeze-seconds as the countdown
tick. Typical leaves:

- `textual/_compositor.py:1236:_render_chops`
- `textual/strip.py:600:divide` constructing `Strip` → `FIFOCache(4)`
- `textual/_styles_cache.py:render_line` / `apply_filter`

Runtime-suffix patches and info-panel `update_state` dirty widgets. Even a
"change-only" suffix patch that does apply (the displayed `Ns`/`Nm` text
advances) invalidates option-list lines. A 1 Hz dirty of a large Agents
`OptionList` on a loaded session is enough for a 4 s compositor hitch once
the GIL is busy.

`LaunchContextSource` makes this worse: `on_mount` does
`set_interval(5.0, self.refresh)`, and `refresh()` calls `_tick()` **then
`super().refresh()`**, which is Textual's "invalidate this widget" API. A
hidden `display: none` source still participates in style/compositor work
when `refresh()` is the poll callback. `alias_overrides_indicator.py` uses
the same `set_interval(..., self.refresh)` pattern.

## Cause 3 — in-flight poll turns running agents into a load storm

`_poll_inflight_agent_transitions` is documented as a bounded backstop for
missed inotify: once per countdown tick, `spawn_pump_free_task` +
`asyncio.to_thread(_collect_inflight_poll_results)` stats five marker
files. That part is correctly off the pump.

The apply step is the problem. After the first observation, **any
signature change** schedules a full artifact-delta refresh:

```python
dirty = previous is not None and current != previous
```

Markers watched (`_INFLIGHT_POLL_MARKERS`): `agent_meta.json`, `done.json`,
`waiting.json`, `retry_state.json`, `pending_question.json`. Statuses
polled (`_LIVE_FILE_REFRESH_STATUSES` plus STARTING): **RUNNING, WAITING,
QUEUED, QUESTION, …** — every live agent, cap 256.

`agent_meta.json` is rewritten while an agent runs (tokens, phase, heartbeat).
Each mtime/size bump is `current != previous`, so the 1 s poll schedules
`source=inflight_poll` artifact-delta loads.

`tui_agent_loads.jsonl` for PID 872820 (2026-10-01 21:07 UTC → 2026-10-02
18:24 UTC, ~21 h):

| source | n | stage-sum s | mean s | max s |
| --- | ---: | ---: | ---: | ---: |
| `inflight_poll` | 924 | 4,578 | 4.95 | 22.9 |
| `auto_refresh` | 269 | 1,550 | 5.76 | 94.9 |
| `watcher` | 187 | 870 | 4.65 | 16.7 |
| `tier1_index_revalidate` | 107 | 630 | 5.88 | 24.8 |
| `notification` | 65 | 372 | 5.72 | 22.1 |
| `launch` | 36 | 215 | 5.97 | 25.3 |
| `input_quiet_tier2_reconcile` | 5 | 127 | 25.4 | 40.3 |
| other | 19 | 118 | — | — |
| **all** | **1,612** | **8,460** | **5.25** | **94.9** |

Stage split: disk 5,439 s (p50 2.61 s, p95 7.72 s, max 58 s), prep 2,327 s,
apply 396 s (p50 170 ms; 183 applies ≥ 0.5 s). Disk+prep run in worker
threads. 8,460 s of Python load work in 21 h is **11.1% of that process's
wall time** in the loader alone. That GIL occupancy is the mechanism behind
the selector-parked hitches and the 3–4 s median on otherwise-cheap frames.

The poll already coalesces (`_inflight_poll_scheduled`), which is why we
see 44 loads/hour rather than one per second. 44 full artifact-deltas per
hour, each ~5 s of GIL-heavy Python, is still enough to freeze the UI ~6%
of wall from this source by itself.

## Cause 4 — fleet projection and prompt-panel digest on the pump

`_run_agents_fleet_refresh` fetches off-thread, then
`_apply_fleet_projection` → `_reproject_agents_from_current_mode` →
`project_clan_tree` → `resolve_clan_tribe` (Rust) **on the UI thread**,
once per clan container. 26 start stacks sit in `resolve_clan_tribe`.
Navigation already defers the apply (`_defer_fleet_projection_apply_if_navigating`);
the projection itself still belongs in the worker.

`PromptPanel.update` hashes the entire Rich document with
`renderable_content_digest` (blake2b over every `Text` span, `Group` child,
and card block) before deciding the render cache can stay. The digest exists
to skip no-op updates; on a large agent card the digest *is* the hitch (20
starts, 81 s). `CachedRenderable` already carries a content digest — the
walk should stop there for the rest of the tree, or the skip key should be
an artifact mtime/identity tuple rather than a full span walk.

## Cause 5 — `Thread.start()` on a timer

`current_config_token()` (`src/sase/config/core.py:302–361`) is documented
as stale-while-revalidate: expired tokens return immediately and a daemon
thread recomputes. The implementation still does this from the caller:

```python
refresh_thread = threading.Thread(target=_refresh_current_config_token, ...)
_current_config_token_refresh_thread = refresh_thread
refresh_thread_to_start = refresh_thread
# later, still on the UI thread:
refresh_thread_to_start.start()
```

CPython's `Thread.start()` waits on the child's `_started` event. The child
must be scheduled and acquire the GIL to signal. Interval is 5.0 s
(`_CONFIG_TOKEN_REFRESH_INTERVAL_SECONDS`), matching
`LaunchContextSource._POLL_INTERVAL_SECONDS`. Call chain on 21 hitch
starts:

```
LaunchContextSource.refresh (the 5 s timer)
  → _tick
    → peek_launch_default_change_token
      → current_config_token
        → Thread.start → Event.wait
```

A long-lived revalidator started once at app mount never pays this wait on
the pump.

## What the 10% is not

**`<space>` / `<ctrl+n/p>` MRU validation** is a real, separate latency
bug (warm 20–26 ms on the key path, live 8.51 s `ctrl+p` at 12:38:05 in
`ws_detect_workflow_type` / `subprocess.run`, plus the 2.8 s watcher-restart
incident at 12:37:48). It is **1.6% of today's freeze-seconds**. Fixing it
will make those two keys fast when the loop is healthy. It will not move
the 11% number.

**Full-GC pauses** (the source note's 445–600 ms, 56 ms after
`gc.freeze()`) sit below the 1.5 s hitch threshold. Zero hitch-start stacks
contain `gc.collect` / `gcmodule`. `gc.freeze()` after startup is still
worth doing for key-to-paint, and there is no `gc.freeze` in the tree
today. It is not the 10% track.

**RSS "5.9 GB after 26 h"** is not what I measure on the same PID at 27 h
uptime. `/proc/872820/smaps_rollup`: RSS 1,501 MB, PSS 1,462 MB, anonymous
1,454 MB, swap 0. `ps` RSS 952 MB (unreferenced pages). VSZ 2.3 GB. 21
threads, lifetime `%CPU` 42.5, main thread ~14% plus twelve `asyncio_*`
workers. Heap sampling (`SASE_TUI_HEAP=1`) is off, so I cannot attribute
the 5.9 GB figure; it may have been a peak, a different aggregator, or a
unit mix-up. Current heap is large for a TUI and worth a `SASE_TUI_HEAP=1`
restart, but the freeze forensics do not depend on a 5.9 GB working set.

**Pump vs loop double-counting** does not create the 10%. Loop-only merged
time is already 11.3%.

## Host load

athena is busy: load average 30–33 on 64 CPUs while agents and pytest run.
That stretches hitch *duration*. It does not invent the stacks: the same
tick, compositor, fleet, poll, and `Thread.start` frames would still fire
on a quiet host, just closer to the 1.5 s floor (or under it, which is the
idle-host target in `docs/perf_runbook.md`: ~0 stall-watchdog records per
30 min, TUI < 10% of a core). Today's session is the opposite of that
target: 107 loop hitches/hour, process lifetime 0.43 cores.

`SASE_TUI_PERF=1` / `tui_jk.jsonl` for this process is stale (last write
2026-09-30). `tui_trace.jsonl` is a 576 MB file from 2026-10-01 06:38, also
not this session. Live verification after the fix needs a TUI restart with
those flags (editable installs keep the imported snapshot —
`tui_perf.md` rule 15).

## Recommended solution

Do this as a dedicated stall-budget track. Keep the MRU snapshot work; do
not wait on it. Sequence by freeze-seconds moved per line of code.

### Phase A — stop the load storm and make the 1 s tick cheap

These four changes should take the 11% to the low single digits on a busy
Agents tab.

1. **In-flight poll: dirty only on status-transition markers.**
   Subsequent observations must not treat `agent_meta.json` mtime/size
   churn as dirty. Schedule an artifact-delta when `done.json`,
   `waiting.json`, `pending_question.json`, or `retry_state.json`
   *appears, disappears, or changes size in a transition-relevant way*,
   and when `agent_meta.json` appears for a STARTING row (already in
   `_first_observation_needs_refresh`). Keep the stat-only
   `asyncio.to_thread` backstop. Add a test: rewriting `agent_meta.json`
   for a RUNNING row does not call `_schedule_agent_artifact_delta_refresh`.
   Acceptance: `inflight_poll` rows in `tui_agent_loads.jsonl` drop from
   ~44/hour to a handful per actual STARTING→RUNNING / RUNNING→DONE /
   WAITING flip.

2. **Countdown tick: compute-then-compare becomes compare-then-skip.**
   Cache the last painted runtime suffix *and* the last `(identity,
   membership-key, displayed-second)` per ticking row. If the displayed
   second (floor of cached wall-clock + elapsed) has not changed, return
   without `asdict` / Rust. When membership changes, recompute once.
   Optional follow-up: one batched `aggregate_clan_runtime` for all live
   containers per tick, instead of N FFI calls.

3. **Info-panel metrics: mutation-keyed cache.**
   Store `_agent_info_metrics_cache` under a generation integer bumped
   when `_agents`, unread ids, or statuses change. The 1 s tick reads the
   cache without walking `bulk_ack_roster_universe`. Update the countdown
   digit with a dedicated setter that does not rebuild counts.

4. **Gates and poll callbacks stay off `Widget.refresh` and off
   `Thread.start`.**
   - Replace `_prompt_input_active()`'s `query(PromptInputBar)` with a
     boolean flipped in prompt-bar mount/unmount (this is also the Phase 2
     prerequisite in the source note).
   - `LaunchContextSource`: `set_interval(_POLL_INTERVAL_SECONDS,
     self._on_poll_tick)`. `_on_poll_tick` peeks tokens; it does not call
     `super().refresh()`. Broadcast only when state changes.
   - `current_config_token`: start **one** long-lived daemon revalidator
     at app mount (or process start), never `Thread.start()` from a timer
     or render path. The 5 s expiry only publishes a "please revalidate"
     flag the existing thread already waits on.

### Phase B — get remaining pump work off the pump

5. **Fleet clan projection in the worker.**
   `project_mixed_agent_tree` / `resolve_clan_tribe` run in the same
   thread that fetched the catalog. The UI-thread apply receives
   precomputed rows and does the incremental list patch only. Keep the
   navigation deferral.

6. **Cheap prompt-panel skip key.**
   Prefer `(agent.identity, header_token, content_mtime_or_chunk_sig)` over
   walking every Rich span. If a digest remains, honor
   `CachedRenderable.content_digest` and do not recurse into hashed
   children.

7. **`gc.collect(); gc.freeze()` after startup loads**, plus a hitch-row
   field for `gc.get_count()` so the next forensics pass can see gen-2
   pauses even when they are < 1.5 s. Helps key-to-paint; small effect on
   the 11%.

### Phase C — the source note's keymap track (parallel, not a substitute)

8. App-owned launchable-MRU snapshot, `prune=False` on the key path,
   `ensure_watches()` instead of watcher `stop()`/`start()`, coalesced
   highlight refresh, de-duplicated mixin `on_mount`. This removes the
   8.51 s `ctrl+p` class of freeze and the 20–70 ms per-press tax. It
   leaves the 1 s tick and the load storm in place.

### Do not do first

- Porting MRU validation to Rust, or a persistent index daemon, does not
  change *when* the 11% work runs.
- Per-key `asyncio.to_thread` in `<ctrl+n/p>` handlers (rejected in the
  source note, still rejected): `tui_perf.md` rule 2, and today's evidence
  is that worker Python *is* the GIL problem.
- Lowering hitch thresholds or rate limits as a "fix". The watchdog is
  correctly reporting a real freeze.

### Acceptance

Busy Agents tab, same host, after a TUI **restart** (editable install):

| signal | target |
| --- | --- |
| Merged loop hitch/stall wall fraction, 1 busy hour | < 2% |
| Idle, no agent work, 30 min (`docs/perf_runbook.md`) | ~0 stall records, TUI < 0.1 core |
| `inflight_poll` loads | only on real status-transition markers |
| Countdown tick when suffix text is unchanged | no `aggregate_clan_runtime`, no roster walk |
| Hitch start stacks | no `Thread.start`, no `load_launchable_vcs_xprompt_mru` |
| `SASE_TUI_PERF=1` Agents j/k | p95 < 16 ms (`tui_perf.md`) |

Add a structural test (cheap enough for `just check`): a 1 s countdown
tick with N live RUNNING rows and unchanged marker signatures performs
zero artifact-delta schedules and zero `list_project_records` /
`subprocess.Popen` / `Thread.start`.

Instrument hitch records with RSS (`/proc/self/smaps_rollup` PSS) and
`gc.get_count()` so the next 27 h session answers the heap question
without a special build. Optionally log `inflight_poll` dirty-reason
(`agent_meta` vs `done` vs first-observation) as a counter on
`refresh.auto_tick` / a new `agents.inflight_poll` span under
`SASE_TUI_TRACE=1`.

## Risks

- **In-flight poll sensitivity.** Ignoring `agent_meta.json` mtime means a
  missed inotify on a meta-only status change waits for the next
  `auto_refresh` / watcher / `done.json`. Status flips that matter already
  write `done.json` / `waiting.json` / `pending_question.json`. Keep
  first-observation of `agent_meta.json` for STARTING rows.
- **Stale runtime suffixes.** Display-second caching can be one second
  behind if a clan's membership changes without bumping the cache key.
  Key membership on the tuple of child identities already used by
  `_aggregate_cache_key`.
- **Stale-while-revalidate config token.** A long-lived thread is the
  same contract as today; only the *start* moves off the UI thread.
- **Host load.** On load-30, even a 2 ms tick can photograph as a hitch if
  workers still parse multi-second artifact-deltas. Phase A item 1 has to
  land for the rest to show up in the 11% number.

## Sources

| Claim | Evidence |
| --- | --- |
| 11.3% merged loop freeze, 422 recoveries, 3.95 h, PID 872820 | `~/.sase/logs/tui_stalls.jsonl` + `.1` (968 rows, events hitch/stall × start/recover × loop/pump); intervals merged from recovered `duration_seconds` |
| Attribution table | Hitch/stall **start** `main_thread_stack` classified; duration from next matching recovered row |
| 51× `aggregate_clan_runtime` on the 1 s tick | Start stacks through `_event_countdown.py:48` → `_agent_time_aggregate.py:270` → `agent_runtime_facade.py:22` |
| Info-panel cache-key walk | `_display_detail_info.py:67–74`; 17 starts in `bulk_ack_roster_universe` / `enum.__hash__` |
| Compositor 21% | 89 starts in `_on_timer_update` / `_compositor_refresh` / `strip.divide` |
| Fleet `resolve_clan_tribe` | 56 starts through `_fleet_refresh.py:187` → `_agent_tree_clan.py:181` |
| Selector-parked 12% | 53 starts whose leaf is `selectors.py:452:select` |
| `Thread.start` on config token | 21 starts through `launch_context_source.py:273` → `launch_default_peek.py:79` → `config/core.py:355` |
| In-flight poll load storm | `~/.sase/logs/tui_agent_loads.jsonl`, PID 872820, 924× `inflight_poll`; dirty rule in `_loading_refresh_polling.py:351` |
| Loader wall 8,460 s / 21 h | Same file, sum of `stages_seconds` |
| RSS 1.50 GB smaps / 0.93 GB ps, 27 h, 21 threads, load ~30 | `/proc/872820/smaps_rollup`, `ps -p 872820`, `uptime` |
| Startup of this PID | `tui_startup.jsonl`: `agents_ready_seconds=11.09`, `agent_row_count=22`, `on_mount_to_first_paint_seconds=0.49` |
| Watchdog semantics / 4-per-minute hitch cap | `_stall_watchdog_monitor.py`, `_stall_watchdog_config.py` (`DEFAULT_HITCH_RATE_LIMIT_PER_MINUTE = 4`); 35 suppressed |
| No `gc.freeze` in tree | repo-wide search |
| Idle-host target | `docs/perf_runbook.md` (Idle-host CPU diet); `sase/memory/tui_perf.md` rules 1, 2, 10, 11, 14 |
| Source claim | `sase artifact read research:202610/prompt_space_and_project_cycle_latency/prompt_space_and_project_cycle_latency.md` |

Researcher: `grk`. Date: 2026-10-02.
