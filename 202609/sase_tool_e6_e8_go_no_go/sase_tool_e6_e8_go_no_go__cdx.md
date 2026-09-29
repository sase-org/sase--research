# Re-evaluating the remaining `sase tool` epics: E6–E8

**Independent researcher:** cdx  
**Date:** 2026-09-29  
**SASE revision inspected:** `c2aec595c83802163e3c6c504f99d2bdbf8985f8`  
**sase-core revision inspected:** `1ad57ea426fe400da427042294d815259744453a`  
**Primary prior roadmap:** [`sase_tool_epic_roadmap.md`](sase_tool_epic_roadmap/sase_tool_epic_roadmap.md)

## Executive answer

E6–E8 are still worthwhile, but they no longer deserve one undifferentiated “continue
the roadmap” decision.

- **E6 (forecasts and routing) is the best next investment.** Its most valuable result
  is not an ETA: it is choosing foreground versus durable hand-off for an agent and
  explaining that choice. The ledger now has enough volume to build `stats`, a
  chronological backtester, and advisory `run -E` immediately. It does **not** yet have
  the roadmap's required time coverage for automatic policy: Athena and Apollo each
  have only about nine days of native data, versus the proposed three-week gate.
- **E7 (local capacity admission) has become more compelling, especially on Athena.**
  Athena has already reached seven concurrent `check` runs. Within the same tool
  definition, median and tail duration rise materially with overlap. This is the first
  direct ToolRun evidence that unadmitted concurrency is costing throughput and
  responsiveness. However, E7 cannot yet derive honest capacity prices: today's
  samples record host load/PSI, but not per-run CPU seconds, peak RSS, or worker demand.
- **E8 (fleet surfaces and rollout) has low standalone value today but meaningful
  option value.** It makes an E7 rollout understandable and reversible across machines,
  and it creates the data plane future remote placement could consume. It does not
  itself dispatch a tool remotely or balance work. The Mac has no ToolRun corpus or
  configured fleet peer, Apollo has no configured peer, and the canonical-fleet epic
  `sase-x7` is still active. E8 should wait.

My recommendation is therefore: **proceed with E6 in two gated pieces; plan E7 after
the measurement piece proves demand/resource models; defer E8 implementation until E7
is stable on one host and the fleet prerequisites are closed.** Close E4's remaining
live-acceptance gate first or explicitly waive it—E4's code is largely shipped, but its
parent epic is not actually closed.

## What has really shipped from E1–E5

The user's premise is nearly, but not literally, true.

| Epic | Live bead state | What is available now |
| --- | --- | --- |
| E1, `sase-135` | **closed** | Project-owned catalog; foreground `run`; Rust-owned ToolRun store; fingerprints, stage timelines, host samples, retention; `list`, `runs`, `show` |
| E2, `sase-17p` | **closed** | Durable `-H` hand-off, monitor/proc ownership, follow/wait/stop, crash settlement, one durable run id |
| E3, `sase-18j` | **closed** | Failure extraction and NEW/KNOWN/FLAKY/UNKNOWN classification, failure groups, structured continuation behavior |
| E4, `sase-1ah` | **in progress** | Verdict receipts, receipt query/reporting, prepared-completion integration, and released Rust bindings are present; every child phase and child epic is closed |
| E5, `sase-1bt` | **closed** | Live row/header chips, ToolRuns card, stage/triage/log detail, links from LLM Calls and Context, Admin Center Tools pane |

E4 remains open because no bead evidence proves its required live Athena
prepared-completion commit using a covering `pass` or `no-new` receipt. The public
schema and completion omissions noted on E4 have since been fixed in the inspected
tree, so this is now primarily an acceptance/closeout gap, not a missing product
surface. This should not be described as a fully closed prerequisite.

Two post-roadmap decisions also narrow what E6–E8 should promise:

1. **Receipts prove before they skip.** Every `sase tool run` still executes. E6 must
   not advertise “reuse” as a routing outcome, and E7 must not treat a receipt as a
   cached result.
2. **Guarded recipes refuse raw agent runs.** `check` and `check-full` now route through
   the ledger by construction unless an explicit bypass is supplied. This makes the
   E6/E7 corpus much more representative than the opt-in corpus anticipated by the
   roadmap.

## Fresh evidence from the shipped ledger

I queried the machine-local ToolRun stores read-only on Apollo and Athena and queried
the Mac through its installed SASE CLI. These are native records, not the historical
provider-call import.

| Metric at 2026-09-29 | Apollo | Athena | Mac |
| --- | ---: | ---: | ---: |
| Native ToolRuns | 259 | 1,687 | 0 |
| Native `check` runs | 206 | 1,487 | 0 |
| `check` runs attributed to agents | 201 | 1,465 | 0 |
| Corpus span | 9.1 days | 9.3 days | — |
| Load/PSI sample rows | 22,682 | 86,518 | 0 |
| Maximum concurrent ToolRuns | 4 | 8 | — |
| Maximum concurrent `check` runs | 4 | 7 | — |

The data already validates the decision to build the ledger first. A 14-day receipt
opportunity report found 22 content-equivalent repeats totaling 2.71 hours on Apollo,
and 39 repeats totaling 6.94 hours on Athena. Under the accepted receipt decision these
are measurement, not saved time, but they demonstrate that the corpus is producing
actionable evidence.

### Manual routing is still common and imperfect

On Athena, 1,262 of 1,487 `check` runs were foreground and only 225 were explicit
hand-offs. Foreground runs had a 228-second median and 769-second p90. Thirty-one of 32
lost `check` runs and 175 of 188 signaled `check` runs were foreground; hand-offs had 13
signaled runs and no lost runs in this sample.

This is observational, not causal—people preferentially hand off runs they already
expect to be long, and “signaled” includes more than provider timeout. Still, the
combination is strong evidence that the caller is repeatedly being asked to make a
choice the system can make more consistently. E6 would turn the existing explicit
mechanisms into one policy-backed entry point.

The routing problem is not “always hand off `check`,” however. Of 1,441 settled Athena
checks with durations, 355 ended within two minutes and 869 within five minutes,
usually because an early stage failed. A useful predictor must distinguish an early
lint exit from a full test lane, or run a bounded preflight before committing to the
hand-off. A single global median will annoy users and waste agent turns.

### Concurrency is now a measured capacity problem

Athena's duration inflation remains after holding the tool definition constant:

| Tool definition | Other runs active at start | Runs | p50 | p90 |
| --- | ---: | ---: | ---: | ---: |
| `f0b2638a3056…` | 0 | 225 | 205 s | 967 s |
| `f0b2638a3056…` | 1 | 173 | 385 s | 1,405 s |
| `f0b2638a3056…` | 2–3 | 96 | 538 s | 1,432 s |
| `12b1748a5cb7…` | 0 | 344 | 206 s | 856 s |
| `12b1748a5cb7…` | 1 | 219 | 227 s | 1,388 s |
| `12b1748a5cb7…` | 2–3 | 165 | 397 s | 2,572 s |
| `12b1748a5cb7…` | 4+ | 48 | 469 s | 3,620 s |

Overlap is not a randomized experiment: workload shape, early-failure stages, worker
counts, and time of day can confound it. Nevertheless, a roughly 2–2.6× median increase
at higher overlap within a stable definition is too large to dismiss. The original
roadmap said admission should move forward when the ledger demonstrates contention or
starvation that records/triage/receipts do not solve. Athena now supplies that evidence.

Apollo provides a useful warning about the forecast design. Check duration's
correlation with the **first** load sample was weak (`r≈0.08` for loadavg1, `r≈0.07`
for CPU PSI, `r≈0.03` for I/O PSI). E6 should not overfit to start-of-run load buckets.
Concurrent managed work, stage path, selected test shape, and load integrated over the
run are more promising covariates.

### The current corpus cannot price E7 honestly

`src/sase/tool/sample.py` records load averages, logical CPU count, and Linux PSI every
approximately ten seconds. It does not record child/process-tree CPU seconds, peak RSS,
I/O volume, or granted pytest workers. Runtime tells us how long a run occupied the
machine, not how many capacity units it demanded.

This is the largest missing prerequisite the old roadmap understated. E7 can begin
with authored weights and shadow accounting, but “calibrated admission” needs resource
demand observations, not duration quantiles alone. E6's measurement scope should be
expanded before E7 enforces anything.

## E6 — forecasts and automatic inline-versus-hand-off routing

### Immediate functionality

E6 would add four user-visible capabilities that do not exist today:

1. **`sase tool stats`**: distribution, outcome/censor mix, stage path, concurrency and
   load cohorts, waste, and chronological calibration rather than the current single
   `TYPICAL` median.
2. **`sase tool run -E`**: a side-effect-free answer to “what would happen if I ran
   this now?” including interval, sample count, fallback level, inline/handoff choice,
   and the reasons.
3. **Automatic routing**: a short likely run stays in the current turn; a long likely
   run reserves its durable identity and hands off; low-confidence cases remain
   explicit or use a conservative catalog policy.
4. **Live time semantics**: stage-conditioned remaining interval, `overdue`/`stalled`
   state, evidence-based timeout suggestions, and deduplicated completion/stall
   notifications.

The most important result is (3). An ETA chip is convenient; preventing a provider
turn from sitting on a 10–40 minute command or being killed mid-command is an agent
reliability feature.

### Future unlocks

E6 supplies the evidence layer for:

- E7 demand recommendations, expected queue starts, bounded deference, and backfill;
- E8 per-machine comparisons and future placement hints;
- duration-regression/change-point detection after toolchain or suite changes;
- cost attribution by agent/bead/epic and machine;
- later reconsideration of receipt reuse or single-flight only if their separate
  evidence gates are met;
- SLOs such as “90% of checks start within X and finish within Y,” which cannot be
  expressed from today's median-only surface.

### Revised scope and readiness

E6 should be split at the policy boundary:

**E6a — measurement and advisory (start now)**

- Rust-owned stats and chronological backtester;
- `run -E`, with no execution or scheduling side effect;
- explicit stage/outcome/censor cohorts and transparent fallback;
- integrated concurrency over the run, not just load at start;
- per-process-tree CPU seconds, peak RSS, and worker-grant observations for E7;
- advisory remaining interval and overdue state in the already-shipped TUI surfaces.

**E6b — automatic policy (activate only after calibration)**

- automatic inline/handoff;
- `timeout: auto`;
- stall/completion notifications;
- policy use of a model only after chronological held-out coverage is near the stated
  interval (the roadmap's approximately 80% p10–p90 target).

Volume is already sufficient to build E6a, but chronology is not: both large ledgers
are under ten days old, and Athena has seven check definition digests in that period.
Imported or cross-definition history can be a labeled fallback, not proof that the
current cohort is calibrated. Keep the original “about three weeks” gate for E6b.

**Worth:** high. **Start now:** advisory half only.

## E7 — local tool capacity admission

### Immediate functionality

E7 makes agents, ToolRuns, and pytest workers respect one host budget:

- a ToolRun that does not fit queues instead of starting and amplifying contention;
- the user sees the reason, queue position, finite maximum wait, and expected start;
- aging prevents starvation while bounded deference allows a light request to pass a
  blocked heavy request;
- stop/cancel/reboot recovery release demand exactly once;
- an explicit forced run is possible and durably recorded;
- nested pytest width comes from the shared grant rather than today's separate
  `WorkerTokenLease` pool.

This is meaningful functionality even on one machine. The user-visible win is not just
lower load: a light agent remains responsive while expensive checks are serialized or
width-limited, and a queued request explains when it can begin.

### Future unlocks

E7 creates the local scheduling authority needed for:

- E8's honest capacity snapshots and drain/rollback semantics;
- future remote placement or dispatch choosing among machines;
- workload classes/priorities and protected interactive headroom;
- safe backfill based on E6 intervals;
- admission-aware worker scaling (for example, fewer xdist workers instead of only
  queue/run decisions);
- eventually, single-flight joining without introducing a second resource authority,
  if duplicate concurrency becomes measured and cancellation semantics are solved.

### Revised scope and readiness

The value case is stronger than it was on September 17 because Athena now shows up to
seven concurrent checks and large within-definition duration inflation. The old plan is
not executable unchanged, though:

- `runner_capacity` is now schema **v7**, not the roadmap's v5, and includes queue
  capacity multipliers and later claim semantics;
- `sase-zp` and `sase-10h` still show in-progress parent landings even though their
  listed phases are closed;
- the separate pytest worker-token pool is still real and must be migrated, not merely
  observed;
- current ToolRun sampling lacks resource demand metrics;
- fail-closed admission needs a tested break-glass because it can otherwise make a
  sick host harder to repair.

Plan E7 only after E6a establishes a resource-demand model. Ship E7 first in shadow
mode: compute the decision, record “would queue/would force,” and compare predicted
capacity with actual contention. Enforce on Athena before Apollo; leave Mac unknown
until it has a corpus and explicit capacity. Do not infer capacity weight directly
from elapsed duration.

**Worth:** medium-high now, likely high after E6a. **Start now:** planning/research only,
not enforcement.

## E8 — fleet capacity surfaces and coordinated rollout

### Immediate functionality

E8 would publish E7's authoritative local snapshot through the existing fleet wire and
show, per machine:

- configured/effective capacity, occupied demand, holders, and waiters;
- fresh/stale/unknown capability and data states;
- expected starts and “why is this machine busy?” drill-down;
- explicit capacity setup and doctor checks;
- drain, staged activation, and proven rollback without old and new admission owners
  running together.

This is chiefly an operator and rollout product. It does **not** run a command on a
different machine, migrate a running command, combine machines into one budget, or
share receipts/results across machines.

### Future unlocks

Once E8 exists, later work can safely add:

- remote placement recommendations in `run -E`;
- a remote `sase tool run` transport or agent-dispatch policy;
- host-aware routing for heterogeneous CPU/memory/macOS requirements;
- fleet backfill and drain-aware maintenance;
- fleet capacity SLOs, alerts, and historical planning;
- policy that moves new work away from a stale, overloaded, or incompatible peer.

Those are genuine strategic options, but none are delivered by E8 itself.

### Readiness and present value

The fleet transport is healthier than the old roadmap assumed: from Athena, Apollo's
gateway answers successfully with fleet contract schema v7 and current read/launch/
mutation capabilities. That makes E8 additive rather than a new transport.

The rollout target is not ready, however:

- Athena is configured to view Apollo, but Apollo has no configured machine alias;
- the Mac is reachable but reports zero ToolRuns and no configured machines;
- `sase-x7` (canonical-only fleet cutover) is still in progress, including its shared
  format and final convergence phases;
- `sase-124` (Agents-tab freshness) still has an in-progress child epic;
- E7 does not yet provide the local truth E8 is supposed to publish.

Building E8 now would mostly create empty/unknown meters and compete with the active
fleet-format cutover. Retain it as a separate epic because a three-machine activation
and rollback has real operational risk, but do not plan its detailed phases until E7's
wire has stabilized.

**Worth:** low immediately, high as an enabler for future cross-machine placement.
**Start now:** no.

## Recommended sequence and gates

1. **Finish E4 closeout.** Produce the live Athena prepared-completion proof required
   by `sase-1ah`, or record an explicit accepted limitation and close it honestly.
2. **Launch E6a now.** Ship stats, backtesting, `run -E`, better covariates, and
   per-run resource/worker demand. Keep it advisory.
3. **Wait for chronological evidence, not more raw volume.** Activate E6b only after at
   least roughly 21 days per target host and held-out interval coverage near the stated
   80% target. Low-sample hosts must say unknown or use a labeled conservative fallback.
4. **Re-plan E7 against current contracts.** Require closed `sase-zp`/`sase-10h`
   landings, runner-capacity v7 parity, one capacity authority, migration of the worker
   token pool, and a break-glass. Run shadow admission, then enforce on Athena first.
5. **Defer E8.** Start only after E7 is stable on one host, `sase-x7` and the relevant
   freshness work are closed, and at least Apollo is intentionally enrolled as a
   bidirectional operational target. Add Mac only after SASE and a ToolRun corpus are
   configured there.

## Final recommendation

**Move forward with the roadmap's intent, but authorize only E6a now.** E6's advisory
half immediately converts a rapidly growing ledger into explanations and usable
statistics; its automatic half should remain gated. The new Athena evidence is strong
enough that E7 should stay on the roadmap and likely follow, but only after resource
demand—not runtime alone—is measured and shadow admission validates the policy. Defer
E8 until it has a real local admission system to expose and a settled fleet wire to
carry it.

In short: **E6: yes, staged. E7: yes, conditional. E8: later.** If future remote tool
placement is not a product goal, E8's option value falls sharply and it can be reduced
to the minimum fleet rollout/visibility work needed to operate E7 safely.

## Sources and method

- Audited artifact reads of the consolidated
  [`sase tool` epic roadmap](sase_tool_epic_roadmap/sase_tool_epic_roadmap.md), its prior
  independent phase sketch `research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap__a.md`,
  and the earlier consolidated control-plane report
  `research:202609/sase_tool_control_plane/sase_tool_control_plane.md`.
- Audited bead reads for `sase-135`, `sase-17p`, `sase-18j`, `sase-1ah`, `sase-1bt`,
  `sase-zp`, `sase-10h`, `sase-11l`, `sase-x7`, `sase-11y`, and `sase-124`.
- Current SASE and sase-core source inspection, especially ToolRun sampling,
  `runner_capacity` schema v7, fleet contract code, and the separate pytest
  `WorkerTokenLease` implementation.
- Read-only queries of Apollo and Athena's `~/.sase/tools/runs.sqlite` stores, plus
  `sase tool receipts`, `sase machine list/status`, and the Mac's installed SASE CLI.
- Correlations and overlap tables are descriptive observations, not causal estimates.
  No report or transcript from another researcher in the current swarm was opened or
  consulted.
