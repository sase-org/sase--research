# Should `sase tool` E6–E8 go ahead? A re-evaluation against ten days of real ToolRuns

**Researcher cld** · 2026-09-29 · measured on **athena** (read-only, over SSH) and
**apollo** · sase master `c2aec595c8`
**Input:** `research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md` (plus its
`__a`/`__b` sources), the E1–E5 plans in the plans sidecar, the current decision records,
and the live ToolRun stores on both machines.

**Question.** You believe E1–E5 are done. Should you go on to E6 (forecasts and automatic
inline-vs-hand-off), E7 (local capacity admission), and E8 (fleet capacity surfaces and
rollout)? What would each give you right away, and what would each make possible later?

---

## 1. Answer up front

**Don't start E6–E8 in the form the roadmap gives them.** The roadmap made the right call
on 2026-09-17 by recording first and deciding later. The recording has now run for ten
days, and it points somewhere else:

1. **The biggest live cost in this area is the Muse ~9-minute kill.** The roadmap
   expected E6's automatic routing to solve this. The Muse adapter kills any synchronous
   command at 540 s. On athena, **160 inline `check` runs died at 530–550 s (23.7 h)**,
   and 57 of them were followed by the same agent running `check` again within 30
   minutes. The daily count went **1 → 13 → 13 → 35 → 47 → 47** from 09-23 to 09-28, so
   it is still growing. The fix does not need a forecast. Two beads are already filed and
   ready: `sase-17e` (the provider's ceiling) and `sase-17g` (start the run inline and
   move it to a monitor without restarting). Together they fix this more simply and more
   reliably than a prediction-driven router. **Do this now, as a medium epic.**
2. **Forecasting as E6 designs it would model the wrong variable.** A simple rolling
   p10–p90 band covers 75% of held-out athena `check` runs, but its median upper bound is
   **18.6× its lower bound**, so it tells you almost nothing. Nearly all of the spread
   comes from **how the run ends** (94% of sase `check` runs don't succeed) and from the
   **scoped test stage** (p50 663 s, p90 2,275 s when it fails). Host load contributes
   very little: load per CPU is above 1.0 in only 2.8% of athena samples. E6's first
   phase, grouping runs by load level, targets the smallest factor. E6's headline
   acceptance test ("`check-full` hands off with a one-line reason") targets a command
   agents have stopped running (1 run on athena, 0 on apollo since
   `decisions:check-full-is-explicit`).
3. **Contention is too low for E7, and it isn't where E7 looks.** On athena (64 CPUs),
   CPU pressure stays near zero at every concurrency level. Memory and I/O pressure rise
   with concurrency, but only slightly. On apollo (16 CPUs), CPU pressure is already high
   with **one** heavy run, so the machine is undersized for its settings. That is a
   config problem, not missing admission. Only 3 runs in 9.5 days were exact duplicates
   running at the same time. A handed-off run is already counted, because the monitor
   keeps its session's weighted runner claim. The condition under which the
   `record-before-admit` decision says to reconsider has not happened.
4. **E8 has no fleet to serve yet.** Athena records 87% of ToolRuns (1,687 vs apollo's
   259), and the Mac has no tool corpus. Machine tabs already show which machines are
   stale or offline. E8 also depends on E7, and live acceptance across several machines
   is the most common cause of long remediation chains in this project.

**What to do instead** (details in §7):

- (a) Finish E4, whose root is still open.
- (b) Ship reactive routing (`sase-17e` + `sase-17g`) as the one epic worth doing now.
- (c) Ship a small read-only `sase tool stats`. It pays off the corpus you are already
  recording, and it is the measurement you need before deciding whether the rest of E6
  is worth it.
- (d) Put the rest of E6, all of E7, and all of E8 on hold, each with a measurable
  condition for reconsidering.

## 2. Are E1–E5 actually complete? Almost — E4's root is still open

| Epic | Bead | Status (read 2026-09-29) |
| --- | --- | --- |
| E1 named tools + ledger | `sase-135` | ✓ closed (created 09-18; first recorded ToolRun 09-20) |
| E1.5 enforced adoption | `sase-16h` | ✓ closed |
| E2 durable hand-off | `sase-17p` | ✓ closed |
| E3 failure triage | `sase-18j` (+ `sase-191`, `sase-18j.10`) | ✓ closed |
| **E4 verified completion** | **`sase-1ah`** | **◐ IN_PROGRESS.** All 7 phases and child epic `sase-1ah.8` are closed. Landing note #2 (09-27) says the root cannot close until someone records a **live athena prepared-completion run that commits an exact verified tree** (accept pass, or no-new if red), or explicitly accepts that gate as a limitation. |
| E5 TUI surfaces | `sase-1bt` | ✓ closed (≈09-28) |

What E4 left on athena: 25 retained receipts (24 `no_new_failures`, 1 `pass`), all
expired. Nothing shows a host finalizer ever used one. The public-schema regression the
land agents reported (`receipt:` missing from the schema) has been fixed on master
(`src/sase/config/sase.schema.json` now declares `toolReceiptPolicy`).

One more change since the roadmap was written: **E4 became "receipts prove; they never
skip"** (`decisions:receipts-prove-before-they-skip`). The roadmap's E4 promise, "the
second `check` on an unchanged tree returns instantly," did **not** ship. Reuse ("E4b")
is on hold until there are ≥2 h/week of content-equivalent repeats for one tool on one
machine, for two consecutive weeks, plus a proof that those repeats are hermetic.

State of E6–E8's prerequisites: `sase-zm` is closed (superseded) and `sase-11y` is
closed. `sase-zp`, `sase-10h`, `sase-x7`, `sase-124`, and `sase-s6` are all **still in
progress**. The roadmap starts E7 only after zp, 10h, and 11l settle, and E8 only after
x7. Neither can start cleanly yet.

## 3. The corpus E6 would consume — what ten days recorded

| | athena | apollo |
| --- | --- | --- |
| ToolRuns (2026-09-20 → 09-29) | **1,687** | 259 |
| Stage rows / load+PSI samples | 13,274 / 86,518 | — / 22,682 |
| sase `check` outcomes | 1,092 failed · 186 signaled · **84 succeeded** · 31 lost | 137 failed · 37 signaled · **1 succeeded** · 8 lost |
| `check-full` runs | 1 | 0 |
| Store size | 168 MB SQLite + 133 MB logs | 40 MB SQLite |
| Heavy-run busy time (≥1 of check/test running) | 118 h | 47 h |

The corpus is **~9.5 days old**. The roadmap's gate is ~3 weeks after E1 lands, so the
earliest E6 start is about **2026-10-11**. Samples are taken about every 10 s and include
loadavg 1/5/15 plus CPU/memory/IO PSI. The recording design is doing its job: none of
the analysis below would be possible without it.

Two cost notes. The store grows about 30 MB/day on athena, including logs. And
`sase-1bo` (stage rows are never pruned because stage timestamps are epoch-ms while the
cutoff is epoch-s) means one part of that growth has no bound. If you keep recording for
a future E6, fix `sase-1bo` first.

## 4. Finding 1 — the most valuable part of E6 doesn't need a forecast

### 4.1 What is happening

`src/sase/llm_provider/muse.py:70-74` sets `_MUSE_SYNC_CEILING_SECONDS = 600` and
`_MUSE_SYNC_COMMAND_TIMEOUT_SECONDS = 600 - 60 = 540`. Any synchronous command a Muse
agent runs is killed at 540 s. Muse runs 66% of athena's inline `check` runs (775 of
1,175).

| athena, sase `check`, by day | 09-23 | 09-24 | 09-25 | 09-26 | 09-27 | 09-28 |
| --- | --- | --- | --- | --- | --- | --- |
| Inline runs killed at 530–550 s | 1 | 13 | 13 | 35 | 47 | 47 |
| Runs handed off | 0 | 7 | 77 | 40 | 31 | 51 |

- **160 kills, 23.7 h of compute** on athena. 112 are attributed to Muse and 46 to runs
  with no provider record. No other provider shows the pattern. Apollo adds 26 more
  (20 Muse).
- **57 of the 160** were followed by the same agent running `check` again within 30
  min. That is the cancel-and-restart failure `sase-17g` describes ("46+ Muse
  occurrences Sep 20–23"), and it is still getting worse.
- **21% of all athena `check` runs take longer than 540 s**, so a Muse agent that runs
  `check` inline loses about one run in five.
- These reruns probably inflate the "content-equivalent repeats" figure that decides
  whether E4b happens (athena: **32 groups, 39 repeat runs, 6.94 h** in the last 7 days).
  Fix the kills, then measure repeats again, before letting that number argue for reuse.

### 4.2 Why reactive escalation beats E6's predictive routing here

E6 phase 6 would compare a calibrated forecast against the provider's inline budget
before starting a run. That approach has three problems:

- **It can't ship soon.** It is gated on corpus age (≥ 10-11) and on calibration (≥80%
  coverage). Meanwhile the kills cost about 2.5 h of compute and roughly six reruns per
  day.
- **It would be wrong in both directions.** With a band that wide, the router either
  hands off the 79% of runs that would have finished inline (each costing a turn
  boundary and a follow-up agent) or keeps inline the 21% that get killed.
- **It solves the wrong problem.** The actual issue is that a run can't change
  executors once it has started.

`sase-17g` (`sase tool run --detach`, a `sase tool wait` bounded by the caller's
ceiling, and `sase monitor start --join`) removes the guess entirely. Start inline; if
the run is still going at the ceiling minus a margin, move it to a monitor **without
restarting**. `sase-17e`'s `SASE_PROVIDER_SYNC_CEILING_SECONDS` export is the piece
`sase-17g`'s bounded wait needs. `sase-17e`'s own refusal gate, driven by duration
classes, is optional once escalation exists. The E2 plan left both beads open on purpose
("E2 routes only on the explicit `-H` and on monitor start"), and E2's durable
reservation, owner binding, and `wait` are the base they build on.

## 5. Finding 2 — what forecasting would actually have to model

### 5.1 Whole-run bands are too wide to use

I ran a chronological backtest on athena. For each settled sase `check` run, I predicted
[p10, p90] from the previous 60 runs.

| Band source | Coverage | Median band width (hi/lo) |
| --- | --- | --- |
| All outcomes, prior 60 runs | **75%** (839/1,114) | **18.6×** |
| Succeeded runs only, prior 30 successes | 55% (41/74) | — |

"Between 47 s and 15 minutes" gets you close to the roadmap's ≈80% exit target, but it
isn't useful to anyone. Successful runs alone (n=84: p10 149 s, p50 276 s, p90 820 s)
are too few, and too prone to drift, to calibrate.

### 5.2 The spread comes from outcome and the scoped test stage, not load

| athena stage (sase `check`) | n | p50 | p90 | p90/p50 |
| --- | --- | --- | --- | --- |
| lint (feature flags), ok | 840 | 63 s | 85 s | 1.3× |
| lint (mypy), ok | 940 | 45 s | 64 s | 1.4× |
| SASE validation, ok | 346 | 77 s | 103 s | 1.3× |
| lint (symvision), ok | 338 | 77 s | 177 s | 2.3× |
| **test (scoped), failed** | 242 | **663 s** | **2,275 s** | 3.4× (66.5 h total) |
| test (scoped), ok | 61 | 60 s | 726 s | 12× |

- The lint stages before the test stage are **tight and predictable** (about five
  minutes in total). The scoped test stage accounts for almost all of the spread.
  Whether it runs at all depends on where the run fails. How long it runs depends on how
  many tests were selected and whether selection escalated. This matches the E3 plan's
  warning: "E6 must forecast from stage durations or condition on the recorded
  continuation mode."
- **Load has a real effect per run but a small effect overall.** In athena stages that
  ran at load per CPU > 1.0, p50 roughly doubles (mypy 44 → 95 s, feature flags 62 →
  127 s). But only 2.8% of athena samples are above 1.0, which gives n = 6–16 high-load
  samples per stage out of 800+. On apollo it matters more (20.7% of samples above 1.0;
  mypy 75 → 114 s), but apollo contributes only 13% of runs.
- **94% of sase `check` runs don't succeed** on athena (99% on apollo). A duration
  forecast mostly predicts *time until the first failure*. Of the failed runs that were
  triaged, 201 have NEW items, 160 are UNKNOWN only, and 34 are KNOWN/FLAKY only. KNOWN
  items are dominated by `lint (symvision)` (1,807).

**Implication.** If E6 is ever built, its model should be a **per-stage** forecast,
**conditioned on selection size and continuation mode**, with load as a minor adjustment.
The roadmap's "load-bucket empirical quantiles" as phase 1 has this backwards.

## 6. Finding 3 — measured contention does not justify E7 or E8

### 6.1 Pressure vs. heavy-run concurrency (distinct 30 s buckets)

| Concurrent heavy runs | athena CPU PSI p90 | athena mem PSI p90 / share >10% | athena IO PSI p90 | apollo CPU PSI p90 | apollo load/CPU p90 |
| --- | --- | --- | --- | --- | --- |
| 1 | 0.2 | 0.5 / 2.1% | 12.8 | **25.0** | 1.38 |
| 2 | 0.4 | 1.4 / 3.7% | 15.3 | 32.1 | 1.49 |
| 3 | 0.4 | 2.5 / 4.0% | 20.6 | 17.5 | 1.19 |
| 4 | 0.4 | 2.6 / 4.1% | 22.2 | 18.4 | 1.32 |
| 6 | 0.4 | 4.9 / 5.4% | 32.2 | — | — |

(athena: 64 CPUs / 62 GB; apollo: 16 CPUs / 31 GB; both `max_running_agents: 10`.)

- **athena** often runs heavy work concurrently: ≥2 runs for 49% of heavy-busy time, up
  to 7 at once. CPU is never the bottleneck. Memory and I/O pressure rise with
  concurrency but stay low: memory PSI above 10% in at most about 5% of buckets, even at
  six concurrent runs. E7's weight-token model, which follows the CPU-centric
  `runner_capacity` accounting, would be rationing a resource athena has plenty of.
- **apollo** is CPU-pressured with a single heavy run (p90 25%). A second run raises that
  only to 32%. Admitting tool runs one at a time wouldn't fix this. What would fix it is
  running fewer concurrent agents on apollo, and the existing weighted queue capacity and
  `%queue` multiplier (`sase-z4`/`sase-zt`/`sase-19f`, all closed) already do that. It
  is a config change, not an epic.
- **Duplicates:** only 3 overlapping runs with the same content fingerprint (0.4 h) in
  9.5 days on athena. There is still no case for single-flight joining.
- **Already counted:** `docs/monitors.md` § Runner slots says a monitor keeps its
  session's weighted claim for its whole lifetime. So a handed-off `check` already sits
  inside agent admission. E7's extra value would be *per-command demand* (a pytest-heavy
  agent weighing more than an idle one), and the pressure data above says that
  difference is small today.
- **The reconsider condition isn't met:** `decisions:record-before-admit` says to
  reconsider "when the ledger itself measures a concurrent-duplicate or queue-starvation
  rate that recording, triage, and receipts do not mitigate." The ledger measures
  neither.
- **Structural risk:** E7 plans *fail-closed* admission. Everything nearby was
  deliberately designed to fail open or never block: `gates-never-block`,
  `hold-pull-fail-open` (whose decision rejected a fail-closed store because it "turns a
  scheduling aid into a host-wide freeze"), and the `sase-10h` zero-weight gate. E7
  would be the first scheduling component that can freeze the host, and it would be
  built to prevent an oversubscription that the measurements don't show.

### 6.2 E8

E8's user-facing result is fleet meters and drill-down ("why is apollo busy?"), plus a
staged athena/apollo/Mac cutover. Today:

- The tool fleet is really **one machine**. Athena has 87% of runs, and the E4 landing
  note says "apollo has too little corpus and mac is unconfigured."
- Machine tabs (`⌨ <alias>`, amber when stale, red when offline) and fleet rows carrying
  `queue_capacity`/multipliers already answer "which machine is loaded, and is its data
  fresh?" for agents.
- E8 publishes E7's capacity snapshot, so without E7 there is almost nothing new to
  publish. The optional part without E7 ("cross-machine prediction hints in `run -E`")
  needs a calibrated E6.
- Live acceptance across several machines is the roadmap's own measured top cause of
  long remediation chains (§3.1, B's 600-epic analysis). And `sase-x7`, which E8 waits
  for, is still in progress.

## 7. What each epic would give you — now vs. later

| Epic | What it gives you right away (as planned) | What it enables later | Measured value today | Verdict |
| --- | --- | --- | --- | --- |
| **E6** Forecasts + auto routing | `sase tool stats`; `run -E` explanation; ETAs, "overdue"/"stalled" states; `timeout: auto`; auto inline-vs-hand-off; notifications; Stats view | TUI ETAs and the `⚒N` top-bar count (E5 plan deferred these until E6 reaches ≥80% coverage); revisiting "redirect" mode for guarded recipes (E1.5: "Revisit after E6"); authored-weight suggestions for E7; E8 hints | **Routing: high, but reactive escalation delivers it better (§4).** Stats: high, and cheap. ETAs / `timeout: auto` / overdue: low to moderate (13 monitor-timeout hand-offs on athena in 9.5 days; hung and lost runs are handled by reconcile). | **Split.** Take routing via `sase-17e`/`sase-17g` now and `stats` now. Put forecasting on hold. |
| **E7** Local admission | Queued heavy runs with an expected start; typed refusals with a retry command; `-B` recorded force; pytest workers drawn from one shared grant | Fair backfill; admission priced from measured demand; fleet placement; the basis for E8 | **Low.** CPU is never the bottleneck on athena. Apollo's pressure doesn't depend on concurrency. 3 concurrent duplicates. Monitors already hold claims. | **Hold,** with a reconsider condition (§8). Tune apollo's queue capacity instead. |
| **E8** Fleet surfaces + rollout | Fresh/stale/unknown capacity meters; machine drill-down; staged three-machine cutover | Remote placement hints; eventually a dispatch advisor | **Very low** for a fleet that is effectively one machine. | **Hold** until E7 exists *and* a second machine carries real tool load. |

## 8. Recommendation

**Do not start E6, E7, or E8 as scoped. Do these five things instead, in this order:**

1. **Close E4 (`sase-1ah`).** Run the live athena prepared-completion demo, or record
   that gate as an accepted limitation. It is small, and it makes "E1–E5 are done" true.

2. **Now: one medium epic, "reactive routing"** (it replaces E6's routing half).
   - Scope:
     - `sase-17e`'s `SASE_PROVIDER_SYNC_CEILING_SECONDS` export (Muse 600 s/540 s;
       other adapters declare theirs or none).
     - `sase-17g`'s `--detach`, the `wait` bounded by that ceiling, and
       `monitor start --join`.
     - Guidance and skill updates, so the default agent pattern becomes "run inline,
       escalate at the ceiling."
   - Optionally, `sase-17e`'s duration classes as advisory hints.
   - Acceptance:
     - Over one week on athena, zero sase `check` runs signaled at 530–550 s.
     - No same-agent kill→rerun pairs.
     - Every escalated run keeps **one** ToolRun id (`show -F`/`wait`/`stop` work
       across the move).
   - Payoff: about 23.7 h of compute and dozens of rerun turns per 9.5 days on athena
     alone, available as soon as it lands, with no calibration gate.
   - It crosses the sase-core boundary (ToolRun state), so plan the core-pin update
     inside the epic.

3. **Now: small `sase tool stats`** (2–3 phases, read-only). It reports, per tool, stage,
   and machine:
   - p50/p90 and outcome mix;
   - kill/timeout/lost counts and wasted hours;
   - repeat and duplicate counts;
   - trend;
   - **a built-in backtest readout** (coverage *and* band width).

   Everything in §3–§6 of this report took ad-hoc SQL over `runs.sqlite`. `stats` makes
   that routine. It is the payoff for the recording you already pay for, and it is the
   instrument that tells you whether the rest of E6 is worth building. It is also where
   E4b's repeat measurement and E7's reconsider signals would appear.

4. **Hold, not cancel, the rest of E6** (ETAs, overdue/stalled, `timeout: auto`,
   calibrated routing). Reconsider when `stats` shows, for athena `check`, a **per-stage
   forecast (conditioned on selection size and continuation mode)** reaching **≥80%
   p10–p90 coverage with median band width ≤3×** for two consecutive weeks, **and** a
   consumer such as E5's deferred ETA chips needs it. If you then build it, redesign
   phase 1 around stages, not load buckets.

5. **Hold E7 and E8.** Keep the §4 cross-epic invariants from the roadmap so a future
   plan inherits them.
   - Reconsider **E7** when any one of these holds:
     - memory PSI >10% in ≥10% of athena heavy-busy buckets for a week;
     - an OOM kill caused by concurrent heavy runs;
     - concurrent same-fingerprint duplicates above about 1 h/week;
     - measured starvation or queueing that `%queue`/`%hold` can't express.
   - Reconsider **E8** only after E7 lands and a second machine carries more than about
     25% of ToolRuns.
   - For apollo today: lower its effective concurrency with the existing queue-capacity
     multiplier. That is a config change, not a plan.

Keep recording load and PSI samples. They are cheap, they can't be backfilled, and they
are what any future E6/E7 decision will need. Fix `sase-1bo` so the store stays bounded.
Also watch **E4b** as a competing investment. Athena's 6.94 h/week of content-equivalent
repeats already clears E4b's 2 h/week threshold for one week, but measure again after
step 2 so that kill-reruns don't inflate the case for reuse.

**Net:** of roughly 22–24 planned phases across E6–E8, about **7–9 phases of focused
work** (reactive routing plus `stats`) capture almost all of the value the ten-day corpus
shows. The remaining ~14 phases, including the whole fail-closed admission and
multi-machine rollout surface, would be built ahead of evidence. That is the pattern
`decisions:corpus-before-mechanism` and `decisions:record-before-admit` exist to prevent.

---

## Appendix A — Method (all reproducible; read-only)

- **Bead state:** `sase bead read <id> -r …` for `sase-135`, `sase-16h`, `sase-17p`,
  `sase-18j`, `sase-1ah`, `sase-1bt`, `sase-zm`, `sase-11y`, `sase-zp`, `sase-10h`,
  `sase-x7`, `sase-124`, `sase-s6`, `sase-17e`, `sase-17g`, `sase-1bo`, `sase-j0`;
  `sase bead list --tier epic --status all`.
- **apollo corpus:** `sase tool runs -a -j -n 1000` (259 runs) and one
  `sase tool show <id> -j` per run (stages, samples, triage).
- **athena corpus:** `ssh athena` running a Python script against
  `~/.sase/tools/runs.sqlite` opened `?mode=ro`, over the tables `runs`, `attempts`,
  `stages`, `samples`, `tool_triage_items`, and `tool_receipts`. Providers were mapped
  from `agent_meta.json` (`llm_provider`) by agent name. Unmapped runs are shown as
  unattributed.
- **"Killed at the ceiling"** = state `signaled`, not handed off, duration 530–550 s.
  **Rerun** = same agent starts `check` within 30 min after the kill.
- **Concurrency** = overlap of `running_ts`–`settled_ts` intervals over
  check/check-full/test runs. **Pressure** = one sample per 30 s bucket (to remove
  duplicates from concurrent runs), grouped by the number of concurrent runs at the
  sample time.
- **Backtest** = runs sorted by start time; band from the previous 60 settled
  (`succeeded`/`failed`) runs; the prediction is checked against the next run.
- **Load effect** = mean loadavg1/CPU of the samples inside a stage's time window;
  "lo" < 0.5 and "hi" > 1.0.
- **Duplicates** = SHA-256 of `fingerprint_before_json` with workspace paths removed;
  overlapping intervals with the same hash.
- `sase tool receipts` on athena supplied the receipt and content-equivalent repeat
  figures.

## Appendix B — Caveats

- Ten days is a short window. It spans E2→E5 landing churn, the `sase-177` Muse change
  (09-23), and a period when `check` was red on symvision/rename drift. Failure-heavy
  outcome mixes make durations look more random than they would on a green tree.
- 46 of athena's ceiling kills have no provider attribution (no matching
  `agent_meta.json`). The 540 s value and the absence of other providers point to Muse,
  but that is an inference.
- PSI is `some`, not `full`, and the samples are taken only while a ToolRun is running.
  Pressure from agents alone, with no tool run, is not observed.
- I did not open peer reports from this swarm. I also did not file or corroborate beads:
  the `sase-17e`/`sase-17g` evidence above belongs on those beads, but five researchers
  each adding "+1" would overstate independent corroboration. The lead can record it
  once.
