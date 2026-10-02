# The TUI's "10% frozen" is stop-the-world garbage collection over a heap bloated by multi-version snapshot caches

> **Research query:** `prompt_space_and_project_cycle_latency.md` reports that the TUI is frozen 10% of the
> time. Dig into the logs and profiling data, find out why, and recommend a fix.

Researcher: cld (swarm `research.3e`) · 2026-10-02 · sase master `34079430e3` · live TUI PID 872820,
CPython 3.14.7 (uv python-build-standalone), Textual 8.2.8 · host athena (64 cores, 62 GiB RAM).

## Bottom line

1. **The 10% figure is real, and it undercounts.** I re-mined the stall log (10:28–14:24, 411 hitches).
   It shows 11.2% of wall time frozen in hitches of ≥1.5 s. I then timed every collection inside the live
   TUI. **15–17% of wall time goes to full (gen-2) garbage collections alone, and 20.5% to GC overall**,
   and that was only 20–35 minutes after a restart. The watchdog misses most of it, because pauses under
   about 1–1.5 s never cross its threshold.
2. **About 90% of the frozen time is CPython's stop-the-world cyclic GC, not slow UI code.** Three pieces of
   evidence agree:
   - 80% of logged hitches froze the watchdog's own daemon thread too, which only a process-wide stop can do.
   - 54 of 58 freezes caught live with py-spy had `gc_collect_main` running on the thread that held the GIL.
   - A `gc.callbacks` timer installed in the live process measured full collections every 6–8 s, each
     taking 1.0–2.2 s.

   **76% of those full GCs ran on worker threads.** Moving more work off the UI thread therefore can't help:
   a collection on any thread holds the GIL, so the UI thread waits too.
3. **Pause length grows with the heap, and the heap grows about 100 MB per minute.**
   - The fresh process went from 1.5 GB to 4.4 GB RSS in 30 minutes and had started swapping.
   - The previous process image reached 5.9 GB RSS plus 2.7 GB swapped in **about 4 hours**, not 26 hours.
     The PID stays the same across in-place restarts, which is why the earlier report read 26 hours.
   - Once the heap is in swap, every full collection has to page it back in. The logged median hitch rose
     from 3.4 s to 5.0 s over that image's life, and the frozen share rose from 6% to 17%.
4. **What fills the heap: snapshot caches that keep superseded versions.** Several caches key on a content
   signature (file `mtime`/`size`) but cap the *number of versions* at 32 or 64. Agents append to these
   files constantly, the signature changes every time, and dead versions are never read again but stay
   cached:
   - `sase.core.artifact_file_explicit._artifact_file_index_cache` keeps up to **32 copies** of the parsed
     26.8k-row artifact index. Each copy is 40 MB and 26.8k tracked objects. The live heap held 10 copies
     after 40 minutes.
   - `sase.ace.tui.relations.artifact_links._CACHE` and `link_index._INDEX_CACHE` keep up to **64 copies**
     of the artifact-link snapshot and its `LinkIndex`. Each pair is about 80 MB and 243k tracked objects,
     and each `LinkIndex` build costs **6.6 s of CPU**. Five snapshot versions were live after 40 minutes.
5. **Fixing the caches is necessary but not sufficient.** I benchmarked CPython's trigger rule: a full
   collection runs whenever promotions reach 25% of the old generation. So:
   - *pause length* scales with heap size;
   - *total* GC time scales with how fast medium-lived objects are promoted, regardless of heap size.

   The fix needs a GC policy as well: freeze the static startup heap and run gen-2 collections only when
   the user is idle.

**Recommendation** (details in [Recommended solution](#recommended-solution)):

- **A. Fix the caches.** Keep one entry per logical key, holding the signature in the value. This stops the
  growth and the swapping.
- **B. Take gen-2 GC off the interactive path.** Run `gc.collect(); gc.freeze()` once after startup. Raise
  `threshold2` so automatic full collections effectively stop, and collect explicitly during idle windows,
  with a backstop. Add GC instrumentation.
- **C. Reduce promotion churn.** The main sources are the `LinkIndex` rebuild, notification deep-clones, the
  dismissed-identity rebuilds, and the duplicate artifact-index parse.
- **D. Fix the watchdog's blind spots** so the number it reports matches what the user actually feels.

A+B should turn 1–5 s freezes every 6–20 s into rare 100–500 ms collections that only happen while you are
idle, and keep RSS flat.

---

## 1. Re-reading the stall log: what "10%" actually measures

Source: `~/.sase/logs/tui_stalls.jsonl{,.1}`, 968 rows, one image of PID 872820, 10:27:57–14:24:45 EDT
(3.92 h). The watchdog (`src/sase/ace/tui/util/_stall_watchdog_monitor.py`) works like this:

- A daemon thread polls every 0.5 s and schedules a `call_soon_threadsafe` ping onto the loop.
- It records a `tui_hitch` when the gap since the last processed ping is at least 1.5 s.
- It records `tui_hitch_recovered` at the first poll after the ping runs again.

| Metric | Value |
| --- | --- |
| Hitches (paired hitch/recovery) | 414; 35 more episodes were rate-limited (4/min cap) and never paired |
| Frozen time | 1,579 s = **11.2%** of wall time (≈10.5% after correcting for the poll bias below, plus the suppressed episodes) |
| Duration | min 2.08 s, p50 3.84 s, p90 5.0 s, max 10.1 s |
| Spacing | median 24 s between hitches |

There are three measurement quirks to keep in mind:

- **Duration bias.** A reported duration is the true freeze plus 0–1.0 s (0.5 s on average) of poll
  granularity. That is why no duration is below 2.0 s.
- **Blind spot.** Freezes shorter than about 1.0–1.5 s are invisible. That matters a lot here, because a
  fresh process's full GCs take about 1.0–1.3 s ([§4](#4-measured-inside-the-live-process)).
- **Correction to the earlier report.** The "26 h, 5.9 GB" process had **re-exec'd** at 10:15:09 EDT.
  `tui_startup.jsonl` shows PID 872820 starting again at `14:15:09Z` and `18:24:47Z`, and exec keeps both
  the PID and `ps etime`. That image reached **5.9 GB RSS plus 2.67 GB `VmSwap`** in about 4.2 hours.

The trend over that image's life (half-hour bins from the 10:15 start; "late" is defined in §2):

| Image age | Hitches | Late (whole-process) | Median duration | Frozen share |
| --- | --- | --- | --- | --- |
| +0.0 h (from 10:28) | 24 | 8% | 2.40 s | 5.9% |
| +0.5 h | 62 | 35% | 2.54 s | 9.2% |
| +1.0 h | 60 | 93% | 3.43 s | 11.6% |
| +1.5 h | 52 | 100% | 3.77 s | 10.9% |
| +2.0 h | 29 | 93% | 3.92 s | 6.6% |
| +2.5 h | 64 | 97% | 4.14 s | 14.6% |
| +3.0 h | 45 | 91% | 4.32 s | 10.6% |
| +3.5 h | 58 | 93% | 4.87 s | 16.1% |
| +4.0 h (to 14:24) | 20 | 70% | 5.03 s | 17.2% |

Spacing stays at about 18–26 s throughout, while each freeze gets longer as the image ages.

## 2. The watchdog's own thread froze too, so these are process-wide stops

The watchdog polls every 0.5 s. If only the UI loop were busy, for example in long Python code that still
yields the GIL every 5 ms, the watchdog would poll on schedule. It would then detect the hitch at a gap of
1.5–2.0 s, and recovery would come later. Instead:

- **80% of hitches (330 of 414) were detected "late"**, at gaps of 2–6.4 s. In those cases the watchdog
  thread itself did not run for the whole freeze, and recovery was recorded 0.55–1.05 s after detection.
  In other words, the freeze was already over by the time the watchdog could look.
- Late hitches add up to **1,376 s, or 9.7% of wall time.** On-time hitches, the genuine UI-thread work,
  add up to 217 s, or 1.5%.
- Late detection jumps from 8–35% in the image's first hour to 91–100% afterwards. That is when full-GC
  pauses grow past the watchdog's detection threshold.

When a whole Python process stops like this, some thread is holding the GIL without reaching an
eval-breaker check. Candidates are a GC pass, a long GIL-holding C call, or a GIL holder stuck in a swap-in
page fault. The UI thread's sampled stack points the same way:

- 44 late hitches show it parked in `selectors.select`, 19 in `Thread.start()` → `wait`, and 38 at the
  `aggregate_clan_runtime` Rust call (which detaches the GIL). These are all points where it had released
  the GIL and was waiting to get it back.
- Most of the rest sit at allocation sites such as `textual/cache.py:226` (`FIFOCache.__init__`),
  `Strip.__init__`, and `enum.__hash__`. That is where an allocation triggers a collection on the UI
  thread itself.

## 3. Caught in the act: py-spy shows `gc_collect_main`

The live process was restarted at 14:24:47, so I probed the *fresh* image. I used a `/proc`-only sampler
running at 10 Hz. It fires one native `py-spy dump` whenever, over a 1 s window, either:

- a single thread uses at least 85% of a CPU while the UI thread uses at most 30 ms of CPU; or
- the UI thread itself is pegged.

The interpreter binary isn't stripped, so I symbolized the native frames with `nm`.

- **58 triggers from 14:39 to 15:00: 54 of them (93%) had `gc_collect_main` on the GIL-holding thread.**
  That was a worker in 37 cases and the UI thread in 17. Every other thread, including the UI thread, sat
  in `futex_wait_queue` (waiting for the GIL), with 0.00–0.03 s of CPU in that second. The other 4
  triggers were genuine CPU work.
- The trigger sites are incidental: whichever thread happened to allocate the object that tripped the
  counter.
  - Worker examples: `_clone_notification` (`notification_store_facade.py:371`),
    `dismissed_bundle_identities_snapshot` (`dismissed_agents.py:189`), `query_summary_identities`,
    `compute_apply_loaded_agents`, `issue_from_dict` (`bead_wire.py`).
  - UI-thread examples: Textual `Strip.divide` → `FIFOCache.__init__`.
- The first trigger came **15 minutes after the restart**. Even a fresh process already has full GCs of
  1 s or more.

## 4. Measured inside the live process

I used CPython 3.14's supported attach API (`sys.remote_exec`, PEP 768) to do two things:

- install a tiny `gc.callbacks` timer that records generation, duration, triggering thread, and (for gen 2)
  the triggering stack;
- run three read-only censuses.

I validated every script on a dummy process first, wrapped all of them in `try`/`except`, and **removed
the callbacks afterwards** ("0 callbacks remain").

| Window (after the 14:24:47 restart) | Full GCs | Interval | Pause p50 / max | Share of wall time in gen-2 | All GC |
| --- | --- | --- | --- | --- | --- |
| 14:43:00–14:44:47 (+18 min) | 13 | ~8 s | 1.16 s / 1.54 s | **14.5%** | 20% |
| 14:46:29–14:49:22 (+22 min) | 24 | 6.3 s | 1.17 s / 1.65 s | **16.9%** | 22% |
| 14:46:29–15:00:00 (+22–35 min) | 88 | ~9 s | 1.38 s / 2.17 s | **15.3%** | 20.5% |

Other readings from the same probes:

- **Who ran them:** 21 of 88 full GCs ran on `MainThread` and 67 on `asyncio_N` workers.
- **How many:** `gc.get_stats()` counted 84 gen-2 collections in the first 18.7 minutes and 194 by about
  15:00.
- **Collector settings:** `gc.get_threshold()` is `(2000, 10, 10)`, nothing is frozen, and nothing in
  `src/sase` tunes the collector.
- **Census:** 1,619,741 tracked objects at 14:43 and 1,724,450 at 14:49.
- **RSS:**

  | Time | RSS | Swap |
  | --- | --- | --- |
  | 14:31 | 1.48 GB | — |
  | 14:41 | 2.02 GB | — |
  | 14:46 | 2.60 GB | — |
  | 14:51 | 3.69 GB | 134 MB |
  | 15:00 | 4.41 GB | 207 MB |

  Major page faults started climbing again once the process began to swap.

As a cross-check, the watchdog logged nothing for the first 18 minutes after the restart. It then logged 50
hitches (145 s, about 13% of 14:43–15:02) once full GCs crossed about 1.1 s. That matches the blind spot in
§1.

**Probe side effects, so nobody misreads the log.** My censuses added one-off pauses at 14:43:29 (1.2 s),
14:49:36 (1.3 s), 14:52:25 (2.1 s), and 14:53:55 (about 8.6 s), plus a few py-spy native-dump pauses of
roughly 20–60 ms each between 14:39 and 15:00. Exclude those rows when you analyze today's
`tui_stalls.jsonl`.

## 5. What is in the heap: holder chains

For every collection of 3,000 or more elements in the live heap, I used `gc.get_referrers` to walk up to
the owning module global or app attribute. The census at 14:53, about 30 minutes after the restart, found
these:

| Holder (module global) | What it retains | Cap | Cost of one entry (measured standalone) |
| --- | --- | --- | --- |
| `sase.core.artifact_file_explicit._artifact_file_index_cache` (`OrderedDict`, key `(path, (mtime_ns, size))`) | **10 tuples of 26,824–26,845 `ArtifactFile`**, one per `index.jsonl` version | `_INDEX_CACHE_MAX_PATHS = 32` (meant as *paths*, applied to *versions*) | 40.0 MB, 26.8k tracked objects, 1.32 s parse |
| `sase.ace.tui.relations.artifact_links._CACHE` (key: signature over 37 projects' `artifact-links.json` `(mtime_ns, size)`) | **5 `ArtifactLinksSnapshot`s of about 35.2k row dicts** | `_CACHE_MAX = 64` | 26.6 MB, 35.2k tracked objects, 0.52 s |
| `sase.ace.tui.relations.link_index._INDEX_CACHE` (key: `snapshot.source_key`) | `LinkIndex` objects (60k-entry dicts of `LinkChip` tuples and `ArtifactEntryTarget`) | `_INDEX_CACHE_MAX = 64` | **53.4 MB, 207.6k tracked objects, 6.59 s build** |
| `widgets.artifact_ref_completion._ARTIFACT_INDEX_CACHE` | 1 more `ArtifactFile` copy (26,838), a separate Rust-path parse | 1 per path (the correct pattern) | about 40 MB |
| `AceApp._dismissed_agents`, `_dismissed_agents_disk_identities`, `dismissed_agents._dismissed_bundle_identities_snapshot_cache` | 59k-, 59k-, and 43.8k-element identity sets, plus copies | grows with history | rebuilt on every dismissal signature change; `set(frozenset)` copy on every hit |
| `memory_reads` / `skill_uses` / `artifact_reads` / `_bead_touches_loader` snapshot caches | 16k / 10k / 7.6k / 11.4k events | keyed by project and replaced in place (fine) | — |

The code comments already note half the problem:

> "A project's aggregate mtime/size signature changes every time a link is created, so a superseded
> signature is never looked up again; without a cap this grows by one permanent entry per aggregate change
> for the life of the process (sase-zn.9.3 heap attribution)."

The fix that followed was a cap of **64** dead versions, which is still enough to hold about 5 GB. The
artifact-index cache came from `093088abb9 perf: cache shared store snapshots` (sase-l6.2, Aug 13). Its
docstring promises caching "by resolved path, mtime, and size". But only same-process writers invalidate
it, and the agents that append to `index.jsonl` are other processes.

Worst case at the caps:

| Cache | Cap × size per entry | Memory | Tracked objects |
| --- | --- | --- | --- |
| Artifact index | 32 × 40 MB | 1.3 GB | 0.86M |
| Artifact-link snapshot + `LinkIndex` | 64 × 80 MB | 5.1 GB | 15.5M |

The sase aggregate (`~/.sase/projects/gh_sase-org__sase/artifact-links.json`, 13.9 MB) changes every few
minutes. Every scope that a pane loads, `None` plus individual projects, keeps its own set of versions.
That is enough to explain the 8.6 GB image and its multi-second collections.

## 6. Why full GCs are so frequent, and why shrinking the heap isn't enough

On this interpreter, automatic gen-2 collections are stop-the-world. A microbenchmark on the TUI's own
`python3.14` measured:

- 8M tracked objects → a 684–730 ms full collection; after `gc.freeze()` → about 0 ms;
- the live 1.6–1.9M *real* objects take 1.2–1.4 s, because real object graphs are denser and the host is
  loaded.

CPython runs a full collection when the objects promoted from gen 1 since the last full collection exceed
**25% of the old generation**, and at least 11 gen-1 collections have happened. That gives:

```
pause    ≈ c · L          (L = old-generation size, c ≈ 0.7 µs/object live, far more if swapped)
interval ≈ 0.25 · L / r   (r = promotion rate of medium-lived container objects)
share    ≈ pause/interval ≈ 5 · c · r      ← independent of heap size
```

The live numbers fit: L ≈ 1.7M objects, a pause of about 1.2 s, an interval of 6–9 s, and r ≈ 50–70k
promotions/s. The model makes two predictions, and both hold:

- **Heap size sets how long each freeze is, not how much total time is lost.** The share was about 15%
  both at 20 minutes and 4 hours. Freezes grew from about 1.2 s to 3–5 s once the heap was large and
  partly swapped. The swap penalty raises `c`, which is why the share also crept up, from 6% to 17%.
- **Fixing the caches alone turns rare long freezes into frequent shorter ones.** You also need to control
  *when* gen-2 runs.

Synthetic policy benchmark (`/tmp/cld_tui_probe/gcbench.py`, same interpreter). The workload is a static
base heap, plus a 250k-object "cache version" replaced every 20 ticks, plus medium-lived and cyclic
churn; 2,400 ticks:

| Policy | Base heap | Automatic full GCs | Max full pause | Total full-GC time |
| --- | --- | --- | --- | --- |
| default `(2000,10,10)` | 1.5M | 74 | 176 ms | 10.8 s |
| default | 5.0M | 27 | **500 ms** | **11.1 s** (same total, longer pauses) |
| `gc.freeze()` after base | 5.0M | 126 | 106 ms | 8.3 s |
| freeze + `threshold2=1e6` + explicit collect every 60 ticks ("idle") | 5.0M | **0** | idle collects ≤ 77 ms | idle only |
| `threshold0=100k` | 5.0M | 1 | 463 ms | 0.46 s (young max 78 ms) |

Freeze plus idle-time gen-2 is the combination that keeps full collections off the interactive path. A
larger `threshold0` cuts promotions a lot, but makes young-generation pauses longer. Tune it from data, not
by guessing.

## 7. Swap amplifies the problem

The host is heavily loaded:

- load average about 28–30;
- 43–48 GiB of 62 GiB RAM in use, mostly agent and pytest workers of about 1 GB each;
- **16–19 GiB of swap in use**;
- IO pressure stall `full avg10 ≈ 14%`.

The old image had 2.67 GB swapped out and 1.31M lifetime major faults. In its last 2 minutes it took about
31.6k major faults, or about 260 per second. The new image took none until about 3.7 GB RSS, then started
swapping and faulting again. A full collection must touch every tracked object, so it pages the cold heap
back in from disk while holding the GIL. That is how roughly 1 s pauses become 3–10 s ones.

## 8. Secondary: real UI-thread work (about 1.2–1.5% of wall time)

The on-time hitches (84, 217 s) are the classic Agents-tab sources the earlier report named:

- per-row `aggregate_clan_runtime` from `_on_countdown_tick` → `patch_active_runtime_rows`;
- `resolve_clan_tribe` inside `project_clan_tree` during fleet projection;
- `renderable_digest._update_text_digest`;
- `bulk_ack_roster_universe`;
- `current_config_token` waiting in `Thread.start()`. Thread start blocks until the new thread acquires the
  GIL, so this is mostly another GC victim.

These are worth fixing, but they are about a tenth of the problem. Some of them are themselves short GCs
that the watchdog caught on time.

## Recommended solution

### A. Make the snapshot caches hold one live version per logical key (do first; small, low risk)

1. **`src/sase/core/artifact_file_explicit.py`.** Key `_artifact_file_index_cache` by resolved path and
   keep `(stat, rows)` in the value. A stat mismatch *replaces* the entry rather than adding one. This is
   the same pattern `read_cached_artifact_index` already uses. Keep the explicit same-process
   invalidation, and keep `_INDEX_CACHE_MAX_PATHS` as a bound on *paths*.
2. **`relations/artifact_links._CACHE` and `relations/link_index._INDEX_CACHE`.**
   - Key both by *scope*, the tuple of project keys: `tuple(k for k, _, _ in signature)`.
   - Store the signature in the value, and return the cached snapshot only if the signature matches.
   - Bound the number of scopes, for example to 8.
   - Make `link_index_for_snapshot` replace the scope's previous index when the snapshot's `source_key`
     changes.
3. **One parse per artifact-index change.**
   - `_ARTIFACT_INDEX_CACHE` (the Rust `query_artifact_files` path) and `read_artifact_file_index` (the
     Python JSONL path) each materialize the full 26.8k rows. Have one source serve both.
   - Because `index.jsonl` is append-mostly, a growth-only change (same inode, larger size) can parse just
     the tail.
4. **Regression guard.** Add a test pattern: after N external rewrites of the backing file, each
   module-level snapshot cache holds at most one entry per logical key. Then audit the other token-keyed
   LRUs: `rg "move_to_end|popitem|_CACHE_MAX"` over `src/sase/ace` and `src/sase/core`.

**Expected effect:** RSS stays near its warmed-up size (about 1.5–2 GB) instead of growing by about
100 MB/min. No more swapping, and full GCs stop lengthening over the session. A alone does **not** fix how
often GC runs (§6).

### B. Take gen-2 GC off the interactive path (small code, largest perceived win)

1. After the startup loads settle (`_mount_state_loads_done`), run `gc.collect(); gc.freeze()` once. This
   moves modules, classes, functions, CSS, and keymaps out of every later scan. Freeze only once: a
   periodic re-freeze would pin dynamic garbage.
2. Then `gc.set_threshold(2000, 10, 10_000)`. Automatic gen-2 now needs 10k gen-1 collections, about
   50 minutes at today's rate, so it becomes a backstop rather than the normal path. Gen-0 and gen-1
   collections stay automatic; they take milliseconds.
3. Add a small idle collector to a new `ace/tui/util/gc_policy.py`, driven by a 1 s `set_interval`. Keep
   the timer callback synchronous and thin, per `tui_perf.md` rule 2.
   - It runs `gc.collect()` only when there has been **no key or mouse input for at least 2–3 s**, no
     prompt bar or modal is being typed into (`tui_perf.md` rule 13's activity gate), and at least about
     30 s have passed since the last full collection.
   - **Backstop:** force a collection if 5 minutes pass without one, or if RSS grew by more than about
     500 MB since the last one.
4. **Instrumentation in the same change.** Register a `gc.callbacks` hook that writes every gen-2 pause
   (and any collection of 50 ms or more) with duration, thread, and tracked count. Write it to
   `tui_stalls.jsonl` as `tui_gc_pause`, or to the perf log. Add an RSS and tracked-object heartbeat every
   5 minutes.

**Expected effect:** gen-2 runs only while you're idle. With A in place, the non-frozen heap is around 0.5–1M
objects, so an idle collection takes about 0.3–0.7 s. After C, it should be well under that. Keystrokes stop
landing in collections.

### C. Reduce promotion churn (medium effort; shrinks the idle collections and total CPU)

1. **`LinkIndex`** rebuilds 208k objects (6.6 s of CPU) on every aggregate change. Update it incrementally
   from the delta, or keep the index in Rust and expose lookups. Moving it to Rust crosses the
   `sase-core` boundary: it needs a wire/API change plus a binding and pin bump. Projection belongs in
   core by the boundary rule anyway, because the CLI and web need the same edges.
2. **Notifications.** `_read_snapshot_cached` deep-clones all ~1.6k notifications on every cache *hit*:
   `replace()` plus five list/dict copies per row. This loop was the hottest worker in the py-spy samples,
   with 45 of 120 active worker samples. Make the rows immutable and return the cached snapshot.
3. **Dismissed identities.** Return the cached `frozenset` instead of a fresh `set(...)` copy, and update it
   incrementally rather than rebuilding 43.8k tuples on every signature change.
4. After A–C, measure whether a larger `threshold0` (for example 10k–25k) lowers the gen-1 share without
   hurting the young-generation p95.

### D. Make the watchdog report the truth

1. Record `late: true` and `poll_lag_s` when the detection gap is well above the poll interval. A
   whole-process stop is a different bug class from a busy UI thread, and the log should say which one it
   saw.
2. Record GC pauses directly (B4), because sub-1.5 s pauses are invisible today. Lowering the hitch
   threshold alone would only add noise.
3. Report recovery durations net of poll granularity (about −0.5 s), and count rate-limited episodes in
   the totals.

### Stopgap until A and B land

Restarting the TUI shortens the pauses, but it does not make them less frequent. Full GCs still took 15%
of wall time 20 minutes after a restart. Restarting every 1–2 hours keeps freezes near 1 s instead of 3–5
s, and nothing more.

## Acceptance targets

| Target | Measured by |
| --- | --- |
| Over a 4-hour session, RSS grows less than 0.5 GB after warm-up and `VmSwap` stays about 0 | the RSS heartbeat |
| Zero gen-2 collections start within 2 s of user input | `tui_gc_pause` rows |
| Idle collections p95 ≤ 300 ms after A+C | `tui_gc_pause` rows |
| GC takes less than 2% of wall time while active; under 0.5% of wall time in hitches; no late hitches | watchdog (with D) |
| After N external appends to `index.jsonl` / `artifact-links.json`, each snapshot cache holds one entry per path or scope | structural tests, cheap enough for `just check` |
| Live check after deploying | Restart the TUI first, because an editable install keeps running the code it imported (`tui_perf.md` rule 15). Then confirm one session hour of `tui_gc_pause` and heartbeat rows. |

## How this relates to the canonical latency report

`prompt_space_and_project_cycle_latency.md` correctly identified the 10% stall budget, the
select-parked hitches, and GC as "part of" the problem. Its recommendation was `gc.freeze()` plus a
separate investigation. The data here shows that GC is not one factor among several. It is about 90% of
the frozen time, and it is driven by a cache-retention bug.

- **`gc.freeze()` alone is not enough.** Without A, the dynamic heap keeps growing. Without the idle
  policy in B, freeze makes collections *more frequent* (§6).
- **The `<space>` and `ctrl+n/p` fixes there are still worth doing.** They remove each key's own cost, but
  the "sometimes slow" tail goes away only with A+B.

## Sources and evidence

| Item | Details |
| --- | --- |
| Logs | `~/.sase/logs/tui_stalls.jsonl{,.1}` (968 rows before restart, plus post-restart rows); `tui_startup.jsonl` (re-exec evidence); `tui.log` |
| Live probes, 14:22–15:02 EDT | `/proc/872820/{status,stat,smaps,task/*}`; `py-spy 0.4.2 dump` (non-blocking sweep of 677 samples at 14:25–14:30, then 58 triggered native dumps); symbolization with `nm -n` on `cpython-3.14.7-linux-x86_64-gnu/bin/python3.14`; `sys.remote_exec` scripts for the GC timer, censuses, and holder chains (all removed). Raw artifacts are in `/tmp/cld_tui_probe/` (ephemeral). |
| Standalone measurements | `read_artifact_file_index()` (40.0 MB, 26,852 tracked objects, 1.32 s); `load_artifact_links_snapshot(None)` (26.6 MB, 35,187 objects, 0.52 s); `link_index_for_snapshot` (53.4 MB, 207,557 objects, 6.59 s); GC microbenchmark and policy benchmark on the TUI interpreter |
| Code | `src/sase/core/artifact_file_explicit.py:44–50, 205–233, 420–454`; `src/sase/ace/tui/relations/artifact_links.py:80–140, 375–381`; `src/sase/ace/tui/relations/link_index.py:74–100`; `src/sase/ace/tui/widgets/_artifact_ref_completion_catalog.py:239–257`; `src/sase/core/notification_store_facade.py:365–430`; `src/sase/ace/dismissed_agents.py:160–195`; `src/sase/ace/tui/util/_stall_watchdog_*.py` |
| Prior work | `sase-v3` (2.3–2.5 GB RSS bug, canceled as stale); `sase-19i.7.3.3.3.3.3.2` notes (gen-2 of about 380 ms on a 563k heap, driven by tracked-allocation volume); `sase-zn.9.3` (the 64-entry caps); `093088abb9` (the artifact-index cache) |
