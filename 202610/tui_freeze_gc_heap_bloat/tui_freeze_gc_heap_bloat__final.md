# The TUI's "10% frozen" is stop-the-world garbage collection over a heap bloated by superseded snapshot copies

> **Research query:** `prompt_space_and_project_cycle_latency.md` reports that the TUI is
> frozen about 10% of the time. Dig into the logs and profiling data, find out why, and
> recommend a fix.

Lead researcher: cld (swarm `research.3e`), consolidating the cdx, cld, grk, mus, and gem
reports with new live measurements · 2026-10-02 · sase master `3691b88ae7` · live TUI
PID 872820 (CPython 3.14.7, Textual 8.2.8, editable install) · host athena (64 cores,
62 GiB RAM).

## Bottom line

1. **The 10% figure is real, and it comes back within an hour of a restart.**
   - All five researchers reproduced it from `~/.sase/logs/tui_stalls.jsonl{,.1}`: 10.7–11.4%
     of wall time inside ≥1.5 s event-loop hitches from 10:28 to 14:24. The spread comes
     only from counting method.
   - The image restarted in place at 14:24:47. It logged **zero** hitches for 18 minutes,
     then went back to **12.9%** frozen from 15:02 to 15:20. That window has no probes in
     it, and the rate limiter dropped another 11 episodes.
   - The watchdog undercounts badly:
     - it cannot see pauses under 1.5 s;
     - it records at most 4 episodes per minute;
     - in my probe window, **7 of 13 full collections (2.0–3.1 s each) produced no hitch
       row**. Only 2 of those 7 were even counted as rate-limited (§2.1).

     The true frozen share is higher than any number computed from the stall log.
2. **Most of that frozen time is CPython's full (generation-2) garbage collection, which
   stops the whole process.** This was the main disagreement between the reports, and it is
   now measured directly rather than inferred:
   - **My live `gc.callbacks` probe, 15:24–15:27, image about 1 h old:**
     - 13 full collections, one every 11–18 s;
     - each took **1.8–3.1 s (p50 2.16 s)**;
     - **16.7% of wall time in gen-2 alone, 25.5% in all GC.**
   - **cld's probe at +22–35 min:** p50 1.38 s every about 9 s, which was 15.3% of wall time.
   - **Hitches line up with collections.** Every recorded hitch with a late-detection gap in
     my window overlaps a gen-2 collection. Two of the stacks were captured *inside* the GC
     callback itself.
3. **Most of those collections run off the UI thread.** 8 of my 13 full collections ran on
   worker or input threads; cld counted 67 of 88. A collection on any thread holds the GIL
   and freezes the UI. So moving more work into workers cannot fix this part.
   - My passive `/proc` sampler shows the same shape. In 13 one-second windows, exactly one
     thread ran at about 100% CPU while the main thread and every other thread sat near zero.
   - Some of these windows coincide with a recorded hitch. Others coincide with a stop that
     the watchdog never logged.
4. **The heap grows by about 100 MB per minute.**
   - The fresh image went from 1.48 GB RSS at 14:31 to **4.66 GB RSS plus 1.46 GB swap** at
     15:20.
   - Pause length scales with the size of the heap. Once that heap is partly in swap, a
     collection must page it back in while holding the GIL; my sampler saw bursts of up to
     2,764 major faults per second. Swap is how 1 s pauses become 3–10 s pauses.
5. **A cache-keying bug is a confirmed, measured contributor to that growth.** Several
   module-level snapshot caches use the file's `(mtime_ns, size)` as part of the key. They
   cap the *number of versions* at 32 or 64 rather than keeping one version per file.
   - Agents append to these files constantly, so every append creates a new key, and the
     superseded copies are never read again.
   - **Live census at 15:28:** 22 full copies of the 26.8k-row artifact index and 10 copies of
     the 35k-row artifact-links snapshot.
   - The artifact-index copies alone are roughly 0.9 GB, using cld's standalone measurement
     of about 40 MB per copy.
6. **Real UI-thread work is a smaller, separate share, about 1.5–3% of wall time.**
   - These are the "on-time" hitches, where the watchdog itself kept running:
     - the 1 s countdown tick;
     - building the info-panel metrics cache key;
     - fleet clan projection;
     - the prompt-panel content digest;
     - `current_config_token()` starting a thread.
   - These are worth fixing, but they are not the 10%.
   - The `<space>` and `<ctrl+n/p>` prompt keys from the source report account for only
     **1.6%** of freeze-seconds.

**Recommendation** (details in [Recommended solution](#recommended-solution)):

- **Fix the snapshot caches** so each holds one live version per path or scope.
- **Take gen-2 GC off the interactive path:** freeze the startup heap once, raise
  `threshold2`, and run full collections only while you are idle, with a backstop.
- **Instrument GC pauses and RSS** in the same change.
- **Then** cut the medium-lived allocation churn and the per-second UI-thread work.

Caches plus GC policy turn freezes of 2–3 s every 10–20 s into rare sub-second collections
that run only while you are idle.

---

## 1. What "10% frozen" measures, and why it undercounts

The watchdog (`src/sase/ace/tui/util/_stall_watchdog_monitor.py:213–257`) works like this:

- A daemon thread wakes every **0.5 s** (`DEFAULT_POLL_INTERVAL_SECONDS`, not 0.25 s as gem
  stated). Each time, it schedules a `call_soon_threadsafe` ping onto the loop.
- If the gap since the last processed ping reaches 1.5 s, it logs `tui_hitch`.
- It logs recovery at the first poll after the ping runs again.
- Hitch records are rate-limited to 4 per minute.

| Window (PID 872820) | Image age | Hitches (+ rate-limited) | Frozen share | Median / max |
| --- | --- | --- | --- | --- |
| 10:28–14:24 (cdx/cld/grk/gem union) | 0.2–4.2 h | 413–422 (+35) | **11.2–11.3%** | 3.85 / 10.1 s |
| 13:04–14:24 (still in the rotated log) | 2.8–4.2 h | 147 (+5) | 14.2% | 4.66 / 10.1 s |
| 14:24:47–14:43, after the restart | 0–18 min | **0** | 0% | — |
| 14:43–15:02 (cld's probes ran here, so the numbers are inflated) | 18–37 min | 52 (+22) | 13.1% | 2.70 / 9.6 s |
| **15:02–15:20, no probes** | **38–56 min** | **42 (+11)** | **12.9%** | 3.08 / 5.6 s |

Notes on interpretation, merged from cdx, cld, and grk:

- **Duration bias.** A recorded duration is the true pause plus up to one poll interval.
  That is why no recorded hitch is shorter than about 2 s.
- **Blind spot.** Pauses under 1.5 s are invisible. A fresh image's full collections
  (about 1.0–1.3 s) only start showing up around 18 minutes in, once they cross the
  threshold.
- **Overlapping tiers.** Loop and pump hitch tiers overlap, so summing every recovered row
  double-counts. The loop-only union (11.2%) is the right headline number.
- **"Late" detection marks whole-process stops.** If only the UI thread were busy, the
  watchdog would still poll on time and record a gap of 1.5–2.0 s. A larger gap means the
  watchdog thread itself could not run.
  - Late detection covers 80% of hitches in the old image (cld) and 76% in 15:02–15:20.
  - On-time hitches, which are genuine UI-thread work, total about 1.5% of wall time.
- **The image was about 4 hours old, not 26.** SASE restarts the TUI with `os.execv`,
  which keeps the PID and `ps etime`. `tui_startup.jsonl` shows this image starting at
  10:15:09 and again at 14:24:47 (cdx, cld).
  - So grk's "1.5 GB RSS at 27 h" was a measurement of the *fresh* post-restart image. It
    does not contradict the 5.9 GB figure.
  - The same exec bug corrupts the startup telemetry: `interpreter_cli_import_seconds` reads
    96,984 s (cdx).

## 2. Direct measurement: the frozen time is GC

### 2.1 Probe results

I ran three probes against the live TUI. Each probe script was validated on a dummy process
first, and the GC callback was removed afterwards (`callbacks_left: 0`).

- **A GC timer.** I used CPython 3.14's `sys.remote_exec` (PEP 768) to install a
  `gc.callbacks` timer for 179 s. It recorded generation, duration, thread, and collected
  count.
- **A cache-size census.**
- **A passive per-thread CPU sampler**, reading `/proc/872820/task/*/stat` once a second.

| Generation | Collections in 179 s | Total | Share of wall time | p50 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| gen 0 | 5,776 | 7.7 s | 4.3% | 0.2 ms | 86 ms |
| gen 1 | 526 | 8.1 s | 4.5% | 11 ms | 182 ms |
| **gen 2 (full)** | **13** | **29.9 s** | **16.7%** | **2.16 s** | **3.09 s** |
| all | | 45.7 s | **25.5%** | | |

- **Where they ran.** 5 full collections ran on `MainThread`, 7 on `asyncio_N` workers, and
  1 on `textual-input`.
- **Interval.** 10.9–18.2 s between full collections.
- **Collector settings.** `gc.get_threshold()` is `(2000, 10, 10)`, with three generations.
  Nothing is frozen (`gc.get_freeze_count() == 0`), and nothing in `src/sase/ace` tunes the
  collector.
  - gem quoted a default of `(700, 10, 10)`. That is wrong for this interpreter.
- **Garbage found.** Each full collection reclaimed only **48k–80k objects**. Each 2 s pass
  scans the whole old generation, about 3M objects estimated from the pause length, to find a
  few percent of garbage. Deferring these passes therefore costs little memory.
- **Match with the watchdog.** Every hitch logged in the window with a late-detection gap
  overlaps a gen-2 collection. Two stacks end in the probe's own GC callback. The only
  non-overlapping hitches are two on-time ones, with gaps of 1.53 s and 1.61 s, in
  `renderable_digest._update_text_digest`. That is real UI-thread work.
- **The watchdog missed most of the collections.**
  - Only 6 of the 13 full collections produced a `tui_hitch` row. The rate limiter accounts
    for 2 more (the `suppressed_count` on later rows).
  - **The other 5, each 1.97–2.16 s, left no row at all.** That includes collections on
    `MainThread` at 15:26:02 and 15:26:43.
  - The likely mechanism is a race for the GIL when the pause ends. The watchdog thread, the
    UI thread, and the collecting thread all wake up wanting the GIL. If the UI thread wins
    and runs its pending beacon first, the watchdog then measures a small gap and sees
    nothing. I have not proven this mechanism; it is an inference.
  - Either way, the stall-log share is a floor. That is why step 1 below records GC pauses
    directly, and why it also makes the watchdog measure its *own* wake-up lateness.
- **Thread pattern.** The `/proc` sampler, over 150 s just before this probe, found the
  same shape:
  - 10 one-second windows where one worker ran at 93–101% CPU while the main thread used
    0–4 ticks and every other thread at most 1 tick;
  - 3 windows where the main thread ran at 100% while everything else was stopped.

  That is the signature of a GIL holder that never yields: a collection, or a long C call.
  cld's native `py-spy` dumps identified it as `gc_collect_main` in 54 of 58 triggered
  samples.

### 2.2 Why the reports disagreed about GC, and how that is resolved

| Claim | Who | Verdict |
| --- | --- | --- |
| GC is about 90% of the frozen time (measured) | cld | **Confirmed** by an independent probe at a later image age. |
| "Full-GC stacks don't appear in any hitch, so GC isn't the 10% track" | grk | **Refuted.** GC adds no Python frames. The watchdog photographs whatever frame the main thread was parked at when it ran (`selectors.select`, `enum.__hash__`, `Strip.__init__`). |
| GC is plausible but unmeasured; don't freeze blindly | cdx | It is now measured. The caution about retention is right, which is why the cache fix comes before or alongside the GC policy. |
| GC and GIL starvation are 64% of the frozen time, inferred from stacks | gem | Right direction, but the number was not measured, and the proposed thresholds `(5000, 20, 25)` would not help (§3). |
| GC is a hypothesis that needs `gc.callbacks` | mus | That hook has now been run; see the table above. |

## 3. Why collections are so frequent, and why heap size alone isn't the knob

A full collection on this interpreter needs two conditions:

- more than `threshold2` (10) gen-1 collections since the last full collection; **and**
- objects promoted since the last full collection exceeding **25% of the old generation**.

In my window there were 2.9 gen-1 collections per second, so the count condition alone would
allow a full collection about every 3.4 s. They actually ran about every 14 s. **The 25% rule
is the binding constraint.** That gives cld's model:

```
pause    ≈ c · L        (L = old-generation size; c grows sharply once pages are in swap)
interval ≈ 0.25 · L / r (r = promotion rate of medium-lived objects)
share    ≈ pause / interval ≈ 4 · c · r   ← independent of heap size
```

The data fits this model:

- **The share stays flat.** It was about 15% at 25 minutes and 16.7% at 60 minutes, and
  6–17% across the old image's life by watchdog accounting.
- **The pause grows.** About 1.2 s → 2.2 s → 3–5 s as the heap grows and starts swapping.

Consequences:

- **Fixing the caches shortens each freeze but does not make freezes much rarer.** With a
  smaller L, you get shorter, *more frequent* full collections.
- **Raising thresholds 0 and 1, as gem proposed, barely changes gen-2 cadence.** The
  25%-of-old rule still fires. Raising `threshold2` far enough that it becomes the binding
  condition (for example 10,000) is what actually stops automatic full collections.
- **Slow loads are both a victim and a cause.** Objects that survive a few young collections
  get promoted, and promotion counts toward the 25% rule even if refcounting frees them a
  moment later.
  - Since the restart, the loader logged 215 *slow* loads (≥2 s), totaling 1,921 s of stage
    time in 66 minutes:
    - 114 `inflight_poll` artifact deltas, mean 6.45 s;
    - 10 `tier1_index_revalidate` loads, **mean 58 s**.
  - GC pauses stretch those loads. A longer load keeps its intermediate objects alive across
    more young collections, so more of them are promoted. That pushes the next full
    collection sooner. This is a positive feedback loop.
  - grk's "load storm" is real, and this is how it feeds the GC problem.
  - grk's specific claim that `agent_meta.json` is rewritten every second was not borne out.
    The live file I watched changed once in 60 s. The poll does still treat *any* marker
    mtime/size change as dirty (`_loading_refresh_polling.py:351`).

## 4. What fills the heap

The table below joins cld's holder-chain census at +30 minutes with my length census at
+63 minutes. Both are cheap `len()` reads of module globals.

| Holder | Key | Cap | Live entries | Cost of one entry (cld, standalone) |
| --- | --- | --- | --- | --- |
| `sase.core.artifact_file_explicit._artifact_file_index_cache` (`:44–48`, `:421–445`) | `(path, (mtime_ns, size))` | `_INDEX_CACHE_MAX_PATHS = 32`, but it bounds *versions* | 10 → **22** | 26.8k `ArtifactFile`, about 40 MB, 1.3 s parse |
| `sase.ace.tui.relations.artifact_links._CACHE` (`:81–139`) | tuple of 37 projects' `(key, mtime_ns, size)` | `_CACHE_MAX = 64` | 5 → **10** | 35.2k row dicts, about 27 MB, 0.5 s |
| `relations.link_index._INDEX_CACHE` (`:74–99`) | `snapshot.source_key` | 64 | **1** at +63 min | 53 MB, 208k objects, **6.6 s build** |
| `_artifact_ref_completion_catalog._ARTIFACT_INDEX_CACHE` | per path, correctly keyed | 1 per path | 1 | Another full 26.8k-row parse, about 40 MB |

- **The comment already admits the bug.** `artifact_links.py:82–85` says that "a superseded
  signature is never looked up again". The fix that followed (`sase-zn.9.3`) capped the
  number of dead versions at 64 instead of keeping one.
- **Growth rate.** `index.jsonl` (26.5 MB) and the sase `artifact-links.json` (13.9 MB) both
  changed within the 3 minutes before I checked. At the caps, these caches alone can reach
  about 1.3 GB plus about 1.7 GB, with millions of tracked objects.
- **They are not the whole heap.** Measured copies explain roughly 1–1.2 GB of a 6 GB
  footprint. cdx's September heap capture (after `e5f902ddd6`) also shows
  `json/decoder.py:361` retaining 895 MB.
- **Fix the measured bug, but don't assume it is the only one.** Ship heap and RSS telemetry
  with the fix and confirm that RSS goes flat.
- **Medium-lived churn.** These sources drive the promotion rate *r* rather than the size L:
  - `notification_store_facade._clone_notification` (`:367–383`) deep-copies every row,
    about 1.6k rows with five list/dict copies each, on **every cache hit**. In cld's
    `py-spy` samples it was the hottest worker allocation site.
  - `dismissed_agents` snapshot rebuilds return a fresh 44k–59k-element `set` copy on every
    hit (cld).
  - The `LinkIndex` is rebuilt from scratch on every aggregate change.
  - `_get_cached_artifact_file_index` returns `list(rows)`, a new 26.8k-element list on every
    hit.

## 5. The real UI-thread work (secondary, about 1.5–3% of wall time)

These are the on-time hitches, with stack attribution from cdx, grk, and gem. They agree
closely: all five reports found the same five sites.

| Source | Evidence | Fix direction |
| --- | --- | --- |
| **1 s countdown tick:** `_on_countdown_tick` → `patch_active_runtime_rows` → `aggregate_clan_runtime` | 49–54 hitch starts. The adapter takes 10 ms per 1,000 members in a clean benchmark (cdx), so seconds of hitch here mean GC, not Rust. | Compare, then skip: key each row on `(membership, displayed second)` and skip `asdict()`/Rust when the displayed second hasn't changed. Don't replace interval-union semantics with naive `+= 1`. |
| **Info-panel metrics:** building the cache key walks `bulk_ack_roster_universe` every second (`_display_detail_info.py:42–77`) | 14–19 starts in `enum.__hash__` | Key the cache on explicit roster, status, and unread generations. |
| **Fleet projection** on the loop after the awaits (`_fleet_refresh.py:160` → `resolve_clan_tribe`) | 56–71 starts | Project on the worker from immutable inputs. Revalidate the generation and selection on apply. |
| **Prompt-panel digest** walks the whole Rich tree (`renderable_digest.py`) | 20–62 starts; on-time hitches in my window | Skip on a cheap identity or content token before building and hashing. Honor existing `CachedRenderable` digests. |
| **`current_config_token()`** calls `Thread.start()` from the 5 s `LaunchContextSource` timer (`config/core.py:340–355`) | 21–23 starts, waiting in `_started.wait()`. That wait is mostly the new thread waiting for the GIL behind a collection. | Use one long-lived revalidator thread. The getter only peeks at the cache. |
| `_prompt_input_active()` is a DOM `query(PromptInputBar)` | 9–13 starts | Make it an explicit boolean. This is also Phase 2's prerequisite in the source report. |

**Prompt keys** (`<space>`, `<ctrl+n/p>`) are 1.6% of freeze-seconds. They have their own
synchronous costs: MRU validation with `git config` subprocesses, and a watcher
`stop()`/`join` on first visit. The source report's Phase 1 fixes stand. mus independently
re-verified the code paths. They will only *feel* fast once the GC freezes are gone.

## Recommended solution

Ship as one small epic, in this order. Steps 1–3 are small and carry the perceived win.
Ship them together: step 2 without step 3 still loses about 15% of wall time to GC, and
step 3 without step 2 lets the dynamic heap keep growing between backstop collections.

### Step 1: Instrument first (hours of work, and it makes every later claim checkable)

- Add a `src/sase/ace/tui/util/gc_policy.py` with a `gc.callbacks` recorder.
  - Record every gen-2 collection, plus any collection of 50 ms or more: monotonic start,
    duration, thread name, collected count.
  - Write into a bounded buffer. Flush from a timer to `tui_stalls.jsonl` as `tui_gc_pause`.
  - **No I/O, stack dumps, or JSON inside the callback.**
- Add a 5-minute heartbeat with RSS, `VmSwap`, major-fault delta, `gc.get_count()`, and
  `gc.get_freeze_count()`.
- Add an app-instance ID to watchdog, startup, and load records, and make the startup clock
  aware of exec restarts (cdx).
- Watchdog fixes:
  - **Detect stops from the watchdog's own lateness.** If the time since the previous poll is
    at least 1.5 s, the whole process stopped. Record that whether or not the beacon
    already ran (see §2.1).
  - record `late: true` / `poll_lag_s`;
  - subtract poll granularity from durations;
  - include rate-limited episodes in totals.

### Step 2: One live version per logical key in the snapshot caches (small, low risk)

1. **`artifact_file_explicit._artifact_file_index_cache`.**
   - Key by resolved path and store `(stat, rows)` as the value. A stat mismatch *replaces*
     the entry.
   - Keep the cap as a bound on *paths*.
   - Return the cached tuple, not `list(rows)`.
2. **`artifact_links._CACHE` and `link_index._INDEX_CACHE`.**
   - Key by scope (`tuple(k for k, _, _ in signature)`) and store the signature in the value.
   - Bound the number of scopes, for example to 8.
   - A new `source_key` replaces that scope's index.
3. **One parse per change of `index.jsonl`.**
   - The Rust completion path and the Python JSONL path should share one source.
   - `index.jsonl` only grows by appends, so a change with the same inode and a larger size
     can parse just the tail.
4. **Structural test, cheap enough for `just check`.** After N external rewrites of each
   backing file, each module-level snapshot cache holds at most one entry per path or scope.
   Then audit the other token-keyed caches:
   `rg "move_to_end|popitem|_CACHE_MAX" src/sase/ace src/sase/core`.

### Step 3: Take gen-2 GC off the interactive path (small code, biggest perceived win)

1. **Freeze the startup heap once.** After `_mount_state_loads_done`, run
   `gc.collect(); gc.freeze()` one time.
   - This takes modules, classes, CSS, keymaps, and the startup roster out of every later
     scan.
   - Don't re-freeze periodically. Frozen objects are still freed by refcounting, but cyclic
     garbage among them is never reclaimed.
2. **Make automatic full collections a rare backstop:**
   `gc.set_threshold(2000, 10, 10_000)`. At today's rate of about 2.9 gen-1 collections per
   second, that is roughly once an hour. Gen-0 and gen-1 stay automatic; they take
   milliseconds.
3. **Collect while you are idle.** Use a 1 s timer, or piggyback on the countdown tick. Keep
   the callback thin, per `tui_perf.md` rule 2.
   - Run `gc.collect()` only when all of these hold:
     - no key or mouse input for at least 3 s;
     - no prompt bar or modal is being typed into (the rule 13 gate, backed by the explicit
       prompt-active flag);
     - at least 60 s since the last full collection.
   - **Backstop:** force a collection after 5 minutes without one, or if RSS has grown by
     more than about 500 MB.
   - At a lower cadence, reuse `src/sase/axe/runner_idle_memory.py`'s `malloc_trim` helper
     so freed arenas actually leave RSS. That module exists because `gc.collect()` alone
     doesn't return pages.
4. **Expected result.** No full collection starts within 2 s of input. With step 2 in place,
   the unfrozen heap stays around 0.5–1M objects, so an idle collection takes about
   0.3–0.7 s (cld's estimate from its synthetic policy benchmark).
   - Deferring is cheap in memory: each full collection today reclaims only 50k–80k objects.

### Step 4: Lower the promotion rate (medium effort; shrinks idle collections and total CPU)

- **Notifications.** Return immutable cached rows instead of deep-cloning on every hit.
- **Dismissed identities.** Return the cached `frozenset` and update it incrementally.
- **In-flight poll.** Only `done.json`, `waiting.json`, `pending_question.json`,
  `retry_state.json`, or the first-observation markers should dirty a row. Count dirty
  reasons in the trace first. Then find out why bounded artifact-delta loads take 4–6 s,
  and why `tier1_index_revalidate` takes about 58 s; re-measure after step 3.
- **`LinkIndex`.** Update it incrementally from the delta, or hold it in Rust and expose
  lookups.
  - Moving large indexes into `sase_core` takes them out of Python's GC entirely. That is the
    structural long-term fix for both L and r.
  - It crosses the Rust-core boundary, so it needs wire/API changes, bindings, and a
    `sase-core-revision.txt` pin bump.
- **Then** measure whether a larger `threshold0` (10k–25k) cuts promotions without hurting
  young-generation p95.

### Step 5: Remove the per-second UI-thread work (the on-time residue in §5)

- countdown tick: compare, then skip;
- generation-keyed info metrics;
- fleet projection moved to the worker;
- a cheap skip token for the digest;
- a long-lived config-token revalidator;
- an explicit prompt-active flag.

The prompt-key epic from the source report (MRU snapshot, `ensure_watches()`, de-duplicated
`on_mount`) proceeds in parallel.

### Stopgap until steps 2–3 land

Restarting the TUI buys about 18 hitch-free minutes. Sub-1.5 s collections continue
throughout. After that, the frozen share is back to about 13% within the hour. A restart is a
band-aid, not a fix.

### Acceptance targets (after a TUI restart, since the editable install keeps its imported code)

| Target | Measured by |
| --- | --- |
| Zero gen-2 collections start within 2 s of input; idle collections p95 ≤ 500 ms (≤ 300 ms after step 4) | `tui_gc_pause` rows |
| Total GC below 3% of wall time on a busy Agents tab | `tui_gc_pause` rows |
| RSS grows less than 0.5 GB over 4 h after warm-up, `VmSwap` about 0, then a 24 h soak | heartbeat |
| Under 0.5% of wall time in hitches during a busy hour, and no late hitches | watchdog (with step 1's fields) |
| N external appends leave one cache entry per path or scope | structural test |
| j/k p95 under 16 ms; prompt-key targets from the source report | `SASE_TUI_PERF=1` |

## Evidence and provenance

| Item | Details |
| --- | --- |
| Stall logs | `~/.sase/logs/tui_stalls.jsonl{,.1}`. Rows before 13:04 have rotated away since the swarm snapshot (cdx recorded SHA-256 hashes of both segments as they were). |
| My live probes (PID 872820) | Per-thread CPU sampler 15:21:15–15:23:45 and 15:24:41–15:27:41 (passive `/proc` reads). `gc.callbacks` timer 15:24:42–15:27:41, removed afterwards. Cache `len()` census at about 15:28:31. The callback's cost is microseconds per collection and the census is one dict-length read, so the 15:24–15:28 stall rows are usable. Scripts and raw output are in `/tmp/lead_probe/` (ephemeral). |
| cld's probes | `py-spy` native dumps 14:39–15:00; GC timer and holder-chain censuses 14:43–15:00. Its censuses added pauses at 14:43:29, 14:49:36, 14:52:25, and 14:53:55 (about 8.6 s); exclude those rows. |
| Load telemetry | `~/.sase/logs/tui_agent_loads.jsonl` logs slow loads only (threshold 2.0 s); 215 rows since the restart. |
| Code verified at `3691b88ae7` | `_stall_watchdog_monitor.py:213–257`; `_stall_watchdog_config.py:23–26`; `artifact_file_explicit.py:44–48, 421–445`; `artifact_links.py:81–139, 375–381`; `link_index.py:74–99`; `notification_store_facade.py:367–383`; `_loading_refresh_polling.py:28–34, 333–366`; `axe/runner_idle_memory.py`; no GC tuning anywhere in `src/sase/ace` |
| Interpreter | `cpython-3.14.7-linux-x86_64-gnu`: three generations, `(2000, 10, 10)`. The classic generational collector, consistent with cdx's note that 3.14.5 restored the middle generation. |

### What each researcher contributed

- **cld:** direct GC measurement, the cache-retention holder chains, the trigger-rule model,
  and the GC policy benchmark. This is the core of the recommendation.
- **cdx:** the exec-restart correction, rigorous union accounting, an adapter microbenchmark
  showing Rust aggregation is not the cost, the September heap capture, the config-token
  mechanism, and the cautions about GC policy.
- **grk:** the load-storm data that became the promotion-feedback explanation, the
  `LaunchContextSource` refresh and `_prompt_input_active` DOM walks, and the case for
  compare-then-skip on the tick. Its "not GC" conclusion is refuted above.
- **gem:** the same UI-thread hotspots with code excerpts. Its GC share was not measured, its
  poll interval and default thresholds are wrong, and its threshold proposal would not help.
- **mus:** an independent reproduction of the 10% figure, and verification of the prompt-key
  mechanics (MRU loader, watcher join, mount-per-press). It correctly kept those keys
  separate from the stall budget.
