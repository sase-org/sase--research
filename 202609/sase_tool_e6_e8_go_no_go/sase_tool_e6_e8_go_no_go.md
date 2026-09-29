# `sase tool` E6–E8: go or no-go after E1–E5

**Consolidated report** · 2026-09-29 · lead researcher on apollo, with read-only queries of
athena's ToolRun store · sase master `c2aec595c8` · sase-core `runner_capacity` schema v7

**Sources:** five independent researchers:

- [cdx](sase_tool_e6_e8_go_no_go__cdx.md): staged E6, conditional E7, E8 later;
  concurrency tables within a single definition.
- [cld](sase_tool_e6_e8_go_no_go__cld.md): Muse ceiling kills, chronological backtest,
  and PSI versus concurrency.
- [grk](sase_tool_e6_e8_go_no_go__grk.md): apollo corpus, adoption metric, and a phase
  cut for E6.
- [mus](sase_tool_e6_e8_go_no_go__mus.md): CLI spot check, with `sase-17e`/`sase-17g` as
  cheaper substitutes.
- [gem](sase_tool_e6_e8_go_no_go__gem.md): feature-level walk-through and a risk matrix.

Also used: the 2026-09-17 roadmap
(`research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md`) and my own checks of
the tree, the bead store, and the athena/apollo ledgers (§8).

**Question.** Assuming E1–E5 are done, are E6 (forecasts and automatic inline-vs-hand-off),
E7 (local tool capacity admission), and E8 (fleet capacity surfaces and rollout) still
worth building? What would each give you right away, what would each make possible
later, and what should you do?

---

## 1. Answer up front

**Don't launch E6–E8 as the roadmap scoped them. Build the two useful parts of E6 in a
different form now, and hold the rest behind conditions you can measure.**

All five researchers agree that the three epics are not equally worth doing, that E8
should not start now, and that E7 should not start before E6's evidence exists. They
disagree about E6 itself. Four of the five say to build E6 advisory-first. cld says E6's
headline feature, automatic inline-vs-hand-off routing, is better delivered without a
forecast. I re-ran cld's key measurements against athena's store. They reproduce exactly,
and they decide the question in cld's favour (§3.1, §5).

| Epic | Worth today | Why |
| --- | --- | --- |
| **E6** Forecasts + auto-routing | **Split it.** Routing: high value, but build it reactively (`sase-17e` + `sase-17g`). `stats`: high value, cheap. Forecasts, ETAs, and `timeout: auto`: low to moderate, so hold them. | The biggest measured cost is Muse killing inline `check` runs at 540 s. Forecast bands are too wide to route on (median p90/p10 ratio 18.6×). |
| **E7** Local admission | **Hold.** Medium strategic value, low value today. | The heaviest stage is already admitted by the pytest worker-token pool. What it costs under concurrency is a narrower grant, not thrashing (§3.3). |
| **E8** Fleet surfaces + rollout | **Hold.** Low value today; option value depends on remote placement becoming a product goal. | It would publish E7's snapshot, which doesn't exist yet. Athena runs 87% of ToolRuns, the Mac has none, and `sase-x7` is still in progress. |

**Recommended sequence (§7):**

1. Close E4.
2. Fix the unbounded ToolRun store (`sase-1bo`).
3. Ship one **reactive routing** epic (`sase-17e` + `sase-17g`).
4. Ship a small read-only **`sase tool stats` + demand instrumentation** unit.
5. Park the rest of E6, all of E7, and all of E8, each with a written reconsider
   condition.

About 7–9 phases of focused work capture most of the value the ten-day corpus shows. The
other ~14 planned phases would be built ahead of the evidence, which
`decisions:corpus-before-mechanism` and `decisions:record-before-admit` exist to prevent.

## 2. Is the premise true? Almost: E4's root bead is still open

| Epic | Bead | State (read 2026-09-29) | What you have now |
| --- | --- | --- | --- |
| E1 named tools + ledger | `sase-135` | closed | Catalog in `sase/sase.yml`; `list`/`run`/`runs`/`show`; fingerprints; stage timelines; load/PSI samples every ~10 s; LAST + TYPICAL |
| E1.5 enforced adoption | `sase-16h` | closed | Guarded `check`/`check-full`. apollo's 7-day adoption: 10 wrapped / 0 raw / 0 bypassed (grk) |
| E2 durable hand-off | `sase-17p` | closed | `run -H`, `show -F`, `wait`, `stop`, one run id across monitor/proc |
| E3 failure triage | `sase-18j` | closed | NEW/KNOWN/FLAKY/UNKNOWN, `sase tool failures`, agent known-continuation |
| **E4 verdict receipts** | **`sase-1ah`** | **IN_PROGRESS** | All 7 phases and the child epic `.8` are closed. Receipts mint and query, and prepared completion may consult them. The root waits on a **live athena prepared-completion run that commits a verified tree** (or an explicit accepted limitation). |
| E5 TUI surfaces | `sase-1bt` | closed | `⚒` chips (elapsed, amber past TYPICAL, silent after 60 s), Runs card, Admin Center Tools pane, LLM Calls linkage |

gem's table marks E4 as "Closed / Landed". That is wrong: the bead is in progress. The
roadmap's E4 promise that the second `check` returns instantly did **not** ship.
`decisions:receipts-prove-before-they-skip` turned receipts into proof only, with reuse
("E4b") gated on ≥2 h/week of content-equivalent repeats for two consecutive weeks plus
a hermeticity proof. So neither E6 nor E7 can be sold as reuse.

No E6, E7, or E8 bead or plan exists. The roadmap's E6 acceptance demo ("`check-full`
hands off with a one-line reason") is out of date: `decisions:check-full-is-explicit`
moved agents to `check`, and athena has recorded one `check-full` run (apollo zero).

## 3. What ten days of ToolRuns show

| At 2026-09-29 | athena (64 CPU / 62 GB) | apollo (16 CPU / 31 GB) | mac |
| --- | ---: | ---: | ---: |
| Native ToolRuns (since 09-20) | 1,687 | 259 | 0 |
| sase `check` runs | 1,394 | 183 | 0 |
| outcomes: failed / signaled / succeeded / lost | 1,092 / 186 / **84** / 31 | 137 / 37 / **1** / 8 | — |
| settled `check` longer than 540 s | 19.9% | **50%** (p50 568 s, p90 2,645 s) | — |
| Max concurrent `check` runs | 7 | 4 | — |
| Load/PSI sample rows | 86,518 | 22,682 | 0 |

The decision to record first has paid off: every finding below came from ad-hoc SQL over
`runs.sqlite`, which `stats` would make routine. Two facts shape everything else:

- **94% of athena `check` runs don't succeed** (99% on apollo). A duration forecast is
  mostly a forecast of *time until the first failure*.
- **The recipe keeps changing.** athena saw seven `check` definition digests in about
  ten days (cdx), which splits any forecast into small cohorts.

### 3.1 The largest measured cost: Muse kills inline `check` at 540 s

`src/sase/llm_provider/muse.py` sets `_MUSE_SYNC_CEILING_SECONDS = 600` and wraps
commands at 540 s. The Muse CLI kills any command still running at that point. I
reproduced cld's figures exactly. On athena, sase `check` runs that were inline,
signaled, and 530–550 s long:

| athena | 09-23 | 09-24 | 09-25 | 09-26 | 09-27 | 09-28 | 09-29 (partial) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Inline runs killed at the ceiling | 1 | 13 | 13 | 35 | 47 | 47 | 4 |
| Runs handed off | 8 | 18 | 81 | 40 | 32 | 52 | 13 |

- **160 kills, about 24 h of compute** on athena. By provider: 112 Muse, 48 unattributed,
  **0 from any other provider**.
- **57 of the kills** were followed by the same agent starting `check` again within
  30 minutes. That is the cancel-and-restart failure `sase-17g` was filed for.
- apollo adds **26 kills (3.9 h)**, and half of apollo's settled `check` runs are longer
  than 540 s.
- The daily count grew with Muse's share of the work and has not levelled off.

**Routing also fails the other way, which no report measured.** Of athena's 248 handed-off
`check` runs, **15% finished in under 2 minutes and 38% in under 5 minutes**. On apollo,
26% of hand-offs took under 5 minutes. Each of those paid a turn boundary and a
follow-up agent for a run that would have fit inline. Meanwhile Claude, Codex, and Grok
run `check` inline past 540 s without being killed (Claude: 21% of its inline runs,
15 h). That holds the turn open, but the compute isn't lost.

**Why this points to reactive escalation, not forecasting.** grk puts apollo's inline
`check` wall time (25.7 h) down as waste. It isn't: the same compute runs under a
monitor. Only two things are actually lost: work killed at a provider's ceiling, and
turn boundaries paid for short runs. **Both** go away with `sase-17g`. Every run starts
inline. A run still going at the caller's ceiling minus a margin moves into a monitor
without restarting (`--detach`, a ceiling-bounded `wait`, `monitor start --join`).
`sase-17e` supplies the ceiling (`SASE_PROVIDER_SYNC_CEILING_SECONDS`).

Predictive routing (E6 phase 6) has three problems here:

- **Timing.** It waits on corpus age (about 2026-10-11) and on reaching ≥80% calibration.
- **Accuracy.** It would be wrong in both directions, given the band widths in §3.2.
- **Fit.** It can't help a run that has already started.

grk objects that routing without forecasts is a hard-coded "always `-H`". That applies to
a static rule, not to escalation, which treats a 30 s `test` and a 9-minute `check`
correctly without knowing either duration in advance.

### 3.2 Forecasts: bands too wide to act on, and load explains little

- **Chronological backtest** (cld, athena): a p10–p90 band built from the prior 60 runs
  covers **75%** of held-out runs, but the median band is **18.6× wide** (about 47 s to
  15 min). Using successful runs only, coverage is 55%, from 84 samples.
- **Where the spread comes from.** It is the *outcome* and the **scoped test stage**. The
  lint stages are tight: mypy p50 45 s, feature-flags 63 s, both with p90/p50 ≈ 1.3×.
  When the scoped test stage fails, it runs p50 663 s and p90 2,275 s. Whether it runs
  at all depends on where the run fails. How long it runs depends on how many tests were
  selected and whether the selection escalated.
- **Load is a small overall factor.** Stages that ran at load per CPU above 1.0 roughly
  double in duration, but only 2.8% of athena samples are that high. On apollo, duration
  correlates weakly with load at run start (r ≈ 0.08 for loadavg1 and 0.07 for CPU PSI,
  per cdx).

**Implication.** If forecasting is ever built, it should be **per stage, conditioned on
selection size and continuation mode**, with load as a minor adjustment. The roadmap's
phase 1 ("load-bucket empirical quantiles") starts with the weakest variable.

### 3.3 Contention: the researchers disagree, and the pytest pool reconciles them

- **cdx:** holding the tool definition constant, athena's `check` p50 rises about
  2–2.6× with overlap (for example 205 → 385 → 538 s at 0 / 1 / 2–3 other runs), so E7
  "has become more compelling".
- **cld:** athena's CPU PSI p90 stays at or below 0.4% at every concurrency level. Memory
  PSI (p90 0.5 → 4.9) and I/O PSI (12.8 → 32.2) rise only modestly, so contention is too
  low to justify E7.

Both are right, for one reason neither report mentioned. **The heaviest stage is already
admission-controlled.** `tests/_suite_gate*.py` runs a host-wide pytest **worker-token
pool**:

- Budget: min(CPUs − CPUs/8, (MemAvailable − 8 GiB) / 700 MiB, 32).
- Each automatic lease requests a floor of 4 and a fair-share ceiling of min(28, budget)/2.

On athena that is at most 32 tokens out of 64 CPUs. With the 25 GB that was available
when I checked, the memory term brings it to about 24, so **memory, not CPU, is the
binding limit**. That explains why CPU pressure stays flat. Stratifying the slowdown on
athena:

| athena sase `check`, by other runs active at stage start | 0 | 1 | 2–3 | 4+ |
| --- | ---: | ---: | ---: | ---: |
| lint (mypy), p50 | 41 s | 47 s | 52 s (all ≥2) | ↤ |
| lint (feature flags), p50 | 62 s | 64 s | 68 s (all ≥2) | ↤ |
| scoped test, non-escalated ≥41-file selections, p50 (n) | 52 s (35) | 93 s (12) | 120 s (9) | 98 s (3) |
| scoped test, escalated to the governed full lane, p50 (n) | 276 s (35) | n/a¹ (43) | 553 s (38) | 2,087 s (16) |
| share of scoped stages that escalated | 42% | 50% | 41% | 39% |
| runs whose log shows a token *wait*² | 0 | 4 | 2 | 3 |

Most rows are grouped by other runs active **when each stage starts**. That is why the
stratified cells are so much smaller than the whole-run counts in the next paragraph.

¹ The p50 is 0 s: most of these stages ended almost immediately, so the cell isn't
comparable. ² Grouped by other runs active when the *run* started.

- **Lint stages** (not governed by the pool) slow down by 10–27%.
- **Serial scoped runs** roughly double in duration, but the samples are small.
- **Almost all of the tail inflation is in the escalated full-suite lane.** That lane
  leases from the pool. Explicit token *waits* are rare (9 runs), and the escalation rate
  stays flat, so the pattern **fits** fair-share grants shrinking when peers hold tokens.

The sample sizes are small and the grant width isn't recorded in the ToolRun, so this is
consistent with the explanation rather than proof of it. Over whole runs the effect is
p50 183 → 235 → 323 → 469 s for 0 / 1 / 2–3 / 4+ other runs (n = 554 / 355 / 217 / 50).

**What this means for E7.** A new admission layer would mostly **move** the wait (queue
before start instead of a narrower grant inside the run) and make it visible. It would
not create capacity. E7's real additions would be:

1. an expected start and queue position;
2. governing the non-pytest stages;
3. putting agent claims and pytest tokens under one authority.

Monitors already keep their session's weighted runner claim (`docs/monitors.md` §Runner
slots), so handed-off runs are already counted. Separately, apollo is CPU-pressured with a
**single** heavy run (CPU PSI p90 25%, per cld). That is a queue-capacity multiplier
setting, not something admission would fix. Concurrent exact duplicates are negligible:
3 runs (0.4 h) in 9.5 days on athena.

## 4. What each epic gives you: right away and later

### E6: forecasts and automatic inline-vs-hand-off (roadmap: large, ~8–9 phases)

**Right away (as scoped):**

- `sase tool stats`: distributions, outcome and censoring mix, waste, calibration.
- `run -E`: predicted interval, sample count, fallback level, and the inline/hand-off
  decision, with no side effects.
- **Automatic routing**, explained in one stderr line.
- Upgrades to E5's chips: survival-conditional remaining time, and "overdue" and
  "stalled" states instead of just "silent".
- `timeout: auto` = clamp(3×p90, 10 m, 3 h).
- Deduplicated overdue/stall notifications.

**Later:**

- E5's deferred ETA chips and the `⚒N` top-bar count (gated on ≥80% coverage).
- Revisiting a "redirect" mode for guarded recipes.
- Duration-regression and change-point detection after suite or toolchain changes.
- Cost attribution by agent, bead, epic, and machine.
- SLOs ("90% of checks finish within X").
- E7's demand hints, expected starts, and backfill.
- E8's per-machine hints.

**Value today:**

- *Routing* is the most valuable item on the whole list, but §3.1 shows reactive
  escalation delivers it sooner, more reliably, and without a calibration gate.
- *`stats`* is high value and cheap. It turns the corpus you already pay for into
  routine readouts, and it measures every reconsider condition in §7.
- *Forecast-driven ETAs, overdue, and `timeout: auto`* are low to moderate. The bands are
  too wide, and cld counted only 13 monitor-timeout hand-offs on athena in 9.5 days.

### E7: local tool capacity admission (roadmap: large, ~8 phases)

**Right away:**

- ToolRun demand inside Rust `runner_capacity`, now at **schema v7** (gem and the
  roadmap say v5, which is out of date).
- A heavy run that doesn't fit queues with a position, a finite wait, and an expected
  start.
- Typed refusals that print the retry, and a recorded `-B` force.
- Pytest workers drawn from the same grant as agents, replacing the separate
  `WorkerTokenLease` pool.
- Release on stop, crash, or reboot.

**Later:**

- Classes, priorities, and protected interactive headroom.
- Backfill driven by E6 intervals.
- Admission-aware worker scaling.
- Single-flight joining, if duplicates ever become measurable.
- The local truth that E8 and any remote placement need.

**Value today:** low. The pool already rations the heaviest stage (§3.3), CPU is never
the bottleneck on athena, and duplicates are negligible. The reconsider condition in
`decisions:record-before-admit` ("a measured concurrent-duplicate or queue-starvation
rate") has not happened. E7 would also be the first *fail-closed* scheduler in a system
whose neighbours deliberately fail open (`gates-never-block`, `hold-pull-fail-open`,
`sase-10h`'s zero-weight gate), so it adds a new way to freeze a host.

Its substrate isn't settled either: `sase-zp` and `sase-10h` are still in progress, even
though all of their phases are closed. `%hold` remains the interim way to stop more heavy
work from starting.

### E8: fleet capacity surfaces and coordinated rollout (roadmap: medium, ~6 phases)

**Right away:**

- Per-machine capacity snapshots over the existing fleet wire. From athena, apollo's
  gateway answers at fleet contract schema v7 (cdx).
- Fresh / stale / unknown meters, and a "why is apollo busy?" drill-down.
- Machine capacity set explicitly through init and doctor.
- A staged athena → apollo → mac activation with drain and proven rollback.
- Optional cross-machine hints in `run -E`.

It does **not** run anything remotely, migrate runs, pool machines, or share receipts.

**Later:**

- Remote placement suggestions.
- A remote `sase tool run` transport or a dispatch policy.
- Heterogeneous routing across CPU, memory, and macOS.
- Fleet drain for maintenance, plus SLOs and alerts.

**Value today:** very low. There is no local admission snapshot to publish, athena
carries 87% of runs, the Mac has no corpus or configured peer, and machine tabs already
show stale and offline machines for agents. `sase-x7` (the canonical-only fleet cutover)
is still in progress. Live acceptance across several machines is the project's measured
top cause of deep remediation chains.

gem's "shelve indefinitely" and cdx's "later" differ only in timing. E8's option value
depends entirely on **whether remote tool placement becomes a product goal**. If it
doesn't, shrink E8 to whatever minimal visibility operating E7 safely requires.

## 5. Disagreements and how I resolved them

| Question | Positions | Resolution |
| --- | --- | --- |
| Build E6 as scoped? | grk, mus, gem, and cdx (staged): yes, advisory first, auto-routing once calibrated. cld: no, route reactively and ship `stats`. | **cld.** Verified on athena: 160 ceiling kills, all Muse or unattributed, 57 reruns, still growing, plus 38% of hand-offs under 5 minutes. Reactive escalation fixes both directions now. A 18.6×-wide forecast fixes neither. mus already called `sase-17e`/`sase-17g` "alternatives *and* complements", and the kill data makes them the first move. |
| Is E7 now justified by contention? | cdx: more compelling (2–2.6× inflation). cld, grk, mus, gem: not yet. | **Not yet.** Both sets of observations hold. The existing pytest token pool reconciles them (§3.3). cdx's instrumentation point stands: E7 can't be priced from elapsed time alone. |
| E8: defer, or shelve and re-scope? | cdx, grk, mus, cld: defer until E7 and `sase-x7`. gem: shelve, and use lightweight telemetry instead. | **Hold with a trigger.** Tie it to remote placement becoming a goal. |
| Does E4's open root block E6? | grk: no, it's landing residue. cdx and cld: finish it first. | It is small either way. Close or waive it first so "E1–E5 done" is actually true. |

**Factual corrections:**

- gem:
  - E4 is not closed.
  - `runner_capacity` is v7, not v5.
  - athena has 64 CPUs and apollo 16, not 32 and 8.
  - The corpus is about 1,394 / 183 sase `check` runs, not "~30–50". n = 30 is the
    TYPICAL window.
- grk: inline wall time isn't waste (§3.1).
- Receipts repeats: athena reports **32 groups, 39 repeats, 6.94 h** for both `-d 7` and
  `-d 14`, because the corpus is only about 9.5 days old. That is roughly 5 h/week,
  already above E4b's one-week threshold. The report doesn't say whether kill→rerun pairs
  count as repeats, so measure again after reactive routing lands before using this
  number to argue for reuse (cld).

## 6. The bottom line in one table

| | E6 routing | E6 `stats` | E6 forecasts / ETAs / `timeout: auto` | E7 | E8 |
| --- | --- | --- | --- | --- | --- |
| Immediate value | High | High | Low–moderate | Low | Very low |
| Future unlock | Removes routing guesswork for every provider | The instrument for every later decision | E5's ETA chips; E7 hints | Unified budget; backfill; placement substrate | Remote placement (if wanted) |
| Best vehicle | `sase-17e` + `sase-17g` | New small read-only unit | Redesigned per-stage forecast, later | Roadmap E7, re-planned against v7 | Roadmap E8 or a smaller version |
| Start now? | **Yes** | **Yes** | No: hold | No: hold | No: hold |

## 7. Recommendation

1. **Close E4 (`sase-1ah`).** Run the live athena prepared-completion demo, or record the
   gate as an accepted limitation. This makes "E1–E5 are done" literally true.
2. **Fix `sase-1bo`** (small, ready). Stage rows are never pruned because stage timestamps
   are epoch-ms while the cutoff is epoch-s. The athena store is 168 MB of SQLite plus
   logs, growing about 30 MB/day. The corpus is only worth keeping if it stays bounded.
3. **Now: one "reactive routing" epic** (replaces E6's routing half).
   - Scope:
     - `sase-17e`'s `SASE_PROVIDER_SYNC_CEILING_SECONDS`: Muse declares 600/540; other
       adapters declare their own ceiling or a configurable soft ceiling, so Claude,
       Codex, and Grok turns stop sitting on 40-minute runs.
     - `sase-17g`'s `--detach`, the ceiling-bounded `wait`, and `monitor start --join`.
     - Skill and guidance updates, so agents run inline and escalate at the ceiling by
       default.
   - `sase-17e`'s duration-class refusal is optional and advisory at most.
   - It crosses the sase-core boundary (ToolRun state), so plan the core-pin bump inside
     the epic.
   - **Accept when**, over one week on athena:
     - zero `check` runs are signaled at 530–550 s;
     - there are no same-agent kill→rerun pairs;
     - fewer than 5% of monitor-owned runs finish in under 2 minutes;
     - every escalated run keeps **one** ToolRun id, so `show -F`, `wait`, and `stop`
       work across the move.
4. **Now: a small read-only `sase tool stats` unit** (2–3 phases). Report per tool,
   stage, machine, and provider:
   - p50/p90;
   - outcome and censoring mix;
   - kill, timeout, and lost counts with wasted hours;
   - repeat and duplicate counts;
   - trend;
   - a built-in chronological backtest showing **coverage and band width**.

   Add the **demand instrumentation** a future E7 needs to the recorded run: the pytest
   grant width and any token-wait time, process-tree CPU seconds, and peak RSS (cdx's
   gap, sharpened by §3.3). Elapsed time alone can never price admission.
5. **Hold, don't cancel.** Record each reconsider condition in the relevant decision or
   bead, and have `stats` report the signals:
   - **Rest of E6** (forecasts, ETAs, overdue/stalled, `timeout: auto`): reconsider when a
     **per-stage** forecast, conditioned on selection size and continuation mode, holds
     **≥80% p10–p90 coverage with median band width ≤3×** on athena `check` for two
     consecutive weeks, **and** a consumer such as E5's ETA chips needs it. Redesign
     phase 1 around stages, not load buckets.
   - **E7:** reconsider when any of these holds:
     - memory PSI above 10% in ≥10% of athena heavy-busy buckets for a week;
     - an OOM kill caused by concurrent heavy runs;
     - concurrent same-fingerprint duplicates above about 1 h/week;
     - measured queueing or starvation that `%hold`, `%queue`, and the pytest pool can't
       express.

     It also requires `sase-zp` and `sase-10h` to be closed, a plan written against
     `runner_capacity` v7, one capacity authority (migrate the pytest pool, don't sit
     beside it), a tested break-glass, and **shadow mode on athena first**.
   - **E8:** reconsider only after E7 is stable on one host, `sase-x7` is closed, a second
     machine carries more than about 25% of ToolRuns, **and** you decide remote tool
     placement is a goal.
   - Meanwhile, tune apollo's effective concurrency with its existing queue-capacity
     multiplier (config, not a plan). Keep the roadmap's §4 cross-epic invariants so any
     future plan inherits them.
6. **Watch E4b as a competing investment.** Athena's repeats already clear the reuse gate
   for one week. If they still do after step 3 removes kill-reruns, reuse may beat any
   remaining E6–E8 item on hours saved.

**Net:** the evidence doesn't support E6–E8 as written. The corpus E1–E5 built says the
remaining money is in *not losing runs at provider ceilings* and *not paying for
unnecessary hand-offs*, which is a reactive-routing problem, and in *reading the ledger
routinely*, which is a `stats` problem. Forecasting, admission, and fleet surfaces remain
sound designs, each waiting on a measurement that `stats` will show you when it arrives.

## 8. Lead verification (2026-09-29)

- **Beads.**
  - `sase-1ah` is IN_PROGRESS with all phases closed.
  - `sase-17e` (READY, large) and `sase-17g` (READY, xlarge) are both filed by
    `sase-177.land`. `sase-17g` cites "46+ Muse occurrences Sep 20–23".
  - `sase-1bo` is READY, small.
  - `sase-zp`, `sase-10h`, `sase-x7`, `sase-124`, `sase-s6`: in progress.
  - `sase-11l`: closed. `sase-zm`: closed as superseded.
  - No E6, E7, or E8 bead exists.
- **Code.**
  - `muse.py` ceiling: 600 s, with commands wrapped at 540 s.
  - Pytest pool budget and fair-share rules: `tests/_suite_gate_budget.py`.
  - Escalating to the governed full lane instead of queueing: `tools/run_pytest`.
  - `RUNNER_CAPACITY_POLICY_SCHEMA_VERSION = 7` in sase-core
    `runner_capacity/wire.rs`.
  - Monitors keep their session's runner claim: `docs/monitors.md`.
- **athena** (`ssh athena`, `runs.sqlite` opened `?mode=ro`):
  - Checked: kill counts per day and per provider (via `agent_meta.json`), reruns,
    hand-off duration shares, the stage-by-concurrency tables, and selection-size
    stratification parsed from run logs.
  - Only 60 scoped stages had a parseable selection count; 132 were marked escalated.
  - Token-wait and escalation messages were counted from the retained logs (1,131 runs
    with logs).
  - Also ran `sase tool receipts -d 7` and `-d 14`.
- **apollo** (local, read-only): check outcomes, kills, and hand-off shares.

**Caveats.**

- Ten days is short. The window spans E2→E5 landing churn, the `sase-177` Muse change,
  and a mostly red tree, all of which make durations look noisier than they would on a
  green tree.
- The 48 unattributed kills are inferred to be Muse from the 540 s signature.
- Concurrency tables are observational. Workload, time of day, and selection size can
  confound them.
- PSI is `some`, not `full`, and is sampled only while a ToolRun is running.
