# Re-evaluating `sase tool` epics E6–E8

**Independent researcher grk** · 2026-09-29 · host apollo ·
sources: `research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md` and its
`__a.md` / `__b.md` siblings, `research:202609/sase_tool_control_plane/sase_tool_control_plane.md`,
`research:202609/e4_verified_completion_practical_value.md`, the live ToolRun ledger on
this machine, `docs/tool.md`, `docs/ace.md`, and the current bead graph.

**Question.** E1–E5 look complete. Are E6 (forecasts and automatic inline-vs-hand-off),
E7 (local tool capacity admission), and E8 (fleet capacity surfaces and coordinated
rollout) still worth doing? What do they give immediately, what do they unlock later,
and what should happen next?

This report does not consult other researchers in the present swarm.

---

## 1. Recommendation

**Plan and land E6. Defer E7 until E6 is calibrated and a load-inflation measurement
from the existing corpus justifies a queue. Leave E8 on the shelf until E7 exists and
the canonical-only fleet cutover (`sase-x7`) actually settles.**

Do not launch E6–E8 as a block. The original roadmap's strongest claim still holds:
each epic has to pay for itself if its successors never ship. On today's tree, only E6
clears that bar.

E6 is the remaining product that attacks the fleet's scarcest resource — **agent
turns held open by `check`**. On this machine, 108 inline (unowned) `check` runs in
nine days consumed 25.7 hours of wall time; 25 of them ran past 20 minutes. The
hand-off mechanism (E2) and the live chip (E5) already exist. What is missing is the
decision that uses them.

E7 and E8 are the original `sase-zm` admission/fleet work, postponed on purpose until
a corpus could price them. The corpus now exists, and it does **not** yet show an
admission emergency: peak concurrency is 4, agent-capacity machinery has landed on
its own (`sase-z4`, `%hold`, `%queue` multipliers), and E8's fleet-wire prerequisite
(`sase-x7`) is still mid-cutover. Building a tool queue before forecasts are
calibrated would repeat the admission-first failure mode that retired `sase-zm`.

Two caveats on "E1–E5 are complete":

- **E1, E1.5, E2, E3, and E5 are closed.** The user-verifiable results from the
  2026-09-17 roadmap are in the CLI, the TUI, and `docs/tool.md`.
- **E4's parent bead `sase-1ah` is still `IN_PROGRESS`.** All seven phases and the
  child epic `sase-1ah.8` are closed, receipts mint and query, and the beta flag is
  gone. The remaining gap is a live athena prepared-completion demonstration plus two
  public-schema/completion follow-ups. That is landing residue, not a reason to delay
  E6. It is a reason to finish E4 on its own bead rather than pretend the legend is
  fully closed.

Close `sase-1ah` (or record the live demo as an accepted limitation) in parallel with
E6 planning. Do not open E7 or E8 plans yet.

---

## 2. What E1–E5 actually delivered

The 2026-09-17 consolidated roadmap promised eight epics, each with one
user-verifiable result. Mapping those promises onto today's product:

| Epic | Bead | Status | Landed user-visible result |
| --- | --- | --- | --- |
| **E1** Named tools and the ToolRun ledger | `sase-135` | closed 2026-09-20 | `sase tool list/run/runs/show`; catalog in `sase/sase.yml`; fingerprints; PSI/loadavg samples; LAST + TYPICAL |
| **E1.5** Enforced adoption (added after the roadmap) | `sase-16h` | closed 2026-09-23 | Guarded `check`/`check-full`; monitor wrapping; linked-repo catalogs |
| **E2** Durable hand-off | `sase-17p` | closed | `sase tool run -H`, `show -F`, `wait`, `stop`; monitor-owned runs; fail-closed `-H` |
| **E3** Failure triage | `sase-18j` (+ `.10`) | closed 2026-09-26 | NEW/KNOWN/FLAKY items; `sase tool failures`; agent known-continuation past all-KNOWN stages |
| **E4** Receipts | `sase-1ah` (+ `.8`) | **parent still open** | Mint/query receipts; `sase tool receipt` / `receipts`; prepared-completion *may* consult a covering receipt |
| **E5** TUI surfaces | `sase-1bt` | closed 2026-09-28 | Live `⚒` chips, Tools deck Runs card, Admin Center Tools pane, LLM Calls linkage |

`sase-zm` is closed **superseded** (2026-09-17), with the close reason pointing at the
roadmap. No E6, E7, or E8 plan bead or `sase/repos/plans/202609/tool_e6*` file exists.

Two landed decisions reshape the original E6–E8 value proposition:

1. **`decisions:receipts-prove-before-they-skip`.** A receipt is proof for host
   completion. Every `sase tool run` still executes its child. The original E4 demo
   ("the second `check` returns instantly citing a receipt") was deliberately not
   shipped. Reuse waits on a measured E4b gate: ≥2 h/week of content-equivalent
   covered repeats for one tool on one machine for two consecutive weeks, plus a
   hermeticity proof.
2. **`decisions:check-full-is-explicit`.** `just check` is the agent default.
   `check-full` is no longer the thing agents run. The original E6 acceptance story
   ("`check-full` hands off with a one-line reason") is a demo for a command this
   machine has **never recorded**.

A third decision still governs sequencing: **`decisions:record-before-admit`**.
Prediction consumes the corpus only after weeks of samples and stays advisory until
backtested; admission consumes calibrated prediction. That record is partly
superseded on recording/enforcement details (`guarded-recipes`,
`explicit-handoff-fails-closed`) and still in force on "admit last."

---

## 3. What the live corpus says (apollo, 9 days)

E1 started recording on this machine on 2026-09-20. From that morning through
2026-09-29 13:15 the project ledger holds **226 ToolRuns** (paginated `sase tool
runs -j`).

### 3.1 Shape of the work

- **183 `check`, 20 `test`, 23 ad-hoc/unnamed. Zero `check-full`, zero `install`,
  zero `test-visual`.**
- `sase tool list` TYPICAL for `check` is **7m 11s (n=30)**. `check-full` and
  `install` still render an em dash: duration unknown, not zero.
- Timed `check` durations: p50 **9.0 min**, p90 **42.5 min**, max **88.7 min**,
  summed wall **46.3 h**.
- Outcomes for `check`: **1 succeeded**, 137 failed, 37 signaled, 8 lost. Failed
  `check` alone is 40.7 h. Triage and receipts are doing the work a queue cannot:
  almost every recorded `check` is a red-master run.
- Fingerprint-before complete on 207/216 runs that have one. Load samples are real:
  a recent monitor-owned `check` stored 158 host samples with `loadavg_*` and
  `psi_*` on host `apollo`. The 2026-09-17 "nothing samples load" gap is closed.

### 3.2 The remaining waste is turn-holding, not missing records

| Path | `check` runs | Timed wall | ≥10 min | ≥20 min |
| --- | ---: | ---: | ---: | ---: |
| Unowned / inline (agent or shell holds the turn) | 108 | 25.7 h | 31 | 25 |
| Monitor-owned hand-off | 75 | 20.6 h | 39 | (included in the 20.6 h) |

Agents already hand off a large minority of `check` runs (E2 + monitor wrapping).
They still run the majority inline. The inline p50 is nine minutes; a quarter of
inline `check` runs exceed twenty minutes. That is the original control-plane
finding ("most heavy verification runs inline"; "prose rules do not steer agents")
still true after the wrapper, the guard, and the TUI chip exist.

E3 changed the economics of those inline runs. Agent `check` continues past
all-KNOWN stages, so a `check` that used to die in seconds at a red lint gate now
proceeds into tests. Handing the **whole** `check` off is more justified today than
it was on 2026-09-17, when a 4–7 second lint failure could burn a monitor turn
boundary. Cheap-stages-inline-before-hand-off was assigned to E4 and did not land
as execution skip; known-continuation is the substitute, and it makes automatic
hand-off of `check` the right default for agents.

### 3.3 Adoption is no longer the blocker

`tools/tool_adoption_report -d 7` on this host: **10 wrapped / 0 raw / 0 bypassed**
classifiable heavy calls (100% wrapped wall and count share; 9 ambiguous pipelines
excluded). The 14-day window still shows 68 raw calls because it includes the days
before `sase-16h` landed on 2026-09-23. The guard did what the original roadmap
said instructions alone would not.

E6 therefore has the corpus property the 2026-09-17 plan required: heavy agent
`check` is a ToolRun by construction, with load samples attached.

### 3.4 Oversubscription is moderate, not an emergency

Sweeping recorded intervals: **max concurrency 4** (2026-09-26 12:30). Starts at
concurrency 1/2/3/4: 139 / 65 / 16 / 6. A 16-logical-CPU host running four
`check`s can still inflate duration — the 2026-09-14 control-plane report measured
inline `just check` median rising 5.0 → 7.2 → 14.3 min as overlapping heavy
commands went 0–2 → 2–5 → 5–10 (r = 0.31). That relationship is now
*backtestable* from stored PSI/loadavg samples. It has not been backtested. That
measurement is a few hours of analysis, not an epic, and it should precede any E7
plan.

### 3.5 Receipts are not yet a wall-time saver

`sase tool receipts -d 14` on this project: **2 retained receipts, both expired**;
12 content-equivalent groups; 22 repeat runs; **2.71 h** summed duration
(~1.35 h/week). The E4b reopen threshold is 2 h/week of *covered* repeats for two
consecutive weeks plus a hermeticity proof. Today's opportunity report is below
that line, and it is measurement only. E6 does not need skip-reuse; E7 does not
get to claim "admission will delete duplicate work." Duplicate work is E4b's
problem, and E4b is not ready.

---

## 4. E6 — Forecasts and automatic inline-vs-hand-off

Roadmap size: large, ~8–9 phases. Flag sketched as `tool_forecasts`. Original
user-verifiable result: `run -E` explains predicted duration and the decision;
`check-full` hands off with a one-line reason; `stats` reports ≥80% interval
coverage.

Rewrite the demo around **`check`**. `check-full` has no rows to calibrate.

### 4.1 Functionality this epic gives immediately

Once it lands, a person or agent gets:

1. **`sase tool run -E check`** — a side-effect-free preflight: predicted p10–p90
   (or a labeled fallback), sample count, load bucket, and the inline-vs-hand-off
   decision. This is the original "one verb, one turn" replacement for a separate
   `plan` subcommand.
2. **Automatic routing on a real `run`.** If predicted duration exceeds the
   provider's inline budget, the wrapper hands off (E2's `-H` / monitor path) and
   prints one stderr line naming the inputs. A short tool stays inline. A
   low-sample tool stays `unknown` / fallback rather than inventing a number.
   Agents stop guessing. The 25.7 h of inline `check` wall in nine days is the
   budget this attacks.
3. **`sase tool stats`** — distributions, load-bucket quantiles, censor rates
   (this corpus has 11 timeouts), calibration (`--by` bead/agent/epic as sketched).
   Admin Center Tools already reserved a Stats view for this epic (E5's plan:
   Runs first; Stats/Failures arrive with E6/E3; Failures already shipped with
   E3/E5).
4. **Honest live time on surfaces that already exist.** E5 chips already show
   stage progress, elapsed minutes, **amber past TYPICAL**, and **silent** after
   60 seconds of missed samples. E6 upgrades TYPICAL from a 30-day median to
   load-conditioned remaining time, and upgrades silent to overdue (`+4m over
   typical`) versus stalled (overdue with no stage progress) — without a
   regenerated countdown, per the original "no fake precision" invariant.
5. **`timeout: auto`** — `clamp(3 × p90, 10m, 3h)` per tool per machine, replacing
   hand-guessed monitor timeouts. Eleven recorded timeouts in nine days are the
   local fixture.

None of this requires a queue, a fleet wire, or skip-reuse.

### 4.2 Functionality this unlocks later

- **Calibrated demand for E7.** Admission that prices a `check` at "weight 1"
  because a human said so is `sase-zm` again. E6's load-bucket p90 is the first
  number E7 is allowed to treat as a price suggestion.
- **Expected start** for a queued run (E7) and **backfill** of small requests in
  front of a protected heavy one.
- **Hang detection** that is more than E5's 60-second silence chip.
- **Provider-budget tables** other catalogs can reuse (Claude Bash timeout, Codex
  exec limits, conservative default).
- A measured answer to whether load buckets matter here. If chronological
  backtest shows load adds nothing over a global p50/p90, E6 still ships routing
  off the global curve and E7's "PSI-respecting ceiling" gets a weaker brief.

### 4.3 Why it is worth a large epic now

The original gate was calendar time: ~3 weeks of load samples after E1, because
load cannot be backfilled. E1 has been recording for **9 days**. That is short of
three weeks for *enabling* automatic routing. It is enough to **plan** E6. An
8-phase epic will not land this week; by the time the predictor is wired, the
corpus will be past the original three-week mark (around 2026-10-11). Keep the
original safety: **automatic routing stays behind a calibration gate** (~80% of
held-out runs inside the predicted p10–p90 band). `run -E` and `stats` can ship
advisory first.

E3 makes the routing decision easier, not harder: `check` is now a long test run
that happens to walk through known-red lint, so "hand off `check`" is the correct
agent default. E5 makes the result visible the moment it exists. E1.5 makes the
training data complete. Every prerequisite E6 actually needs is in production.

### 4.4 Risks and how to bound them

- **Wrong hand-off of a 12-second lint-only failure.** Known-continuation reduced
  this. Keep a cheap-stage exception: if the catalog can see that only lint
  remains, stay inline. Do not block E6 on a full E4-style stage-receipt skip.
- **Thin cohorts.** `test` has 20 rows; `check-full`/`install` have zero. Fallback
  levels with sample counts (the original design) are mandatory. Do not invent
  ETAs for tools with n=0.
- **Almost all `check`s fail.** Duration quantiles must include failed and
  signaled runs (they are the typical `check`) and treat timeouts/lost as
  censored, as the roadmap already specified.
- **Scope creep into admission.** E6's "explicitly out" list still applies: no
  admission influence, no automatic weight rewrite, no remote dispatch, no ML.

A reasonable phase cut, smaller than the original 8–9 if epic-budget is tight:

1. Load-bucket quantiles + `stats` + `run -E` (advisory).
2. Automatic inline-vs-hand-off behind the calibration gate.
3. Remaining-time / overdue / stalled / `timeout: auto` / Stats pane.

Phase 2 is the piece that changes daily agent behavior. Phases 1 and 3 still pay
for themselves as observability.

---

## 5. E7 — Local tool capacity admission

Roadmap size: large, ~8 phases. Original user-verifiable result: a second heavy run
queues with an expected start instead of oversubscribing; refusals print an
executable retry.

### 5.1 Functionality this epic would give immediately

- One Rust `runner_capacity` ledger that counts **ToolRun demand** next to agent
  claims. A `check` that does not fit is queued or refused; it does not start
  early; crash/reboot recovery does not leak demand.
- **Expected start** on the waiter, using E6's duration curve.
- Typed refusals that print the retry (`-B` force, recorded as forced; finite
  `-W` wait).
- **Pytest worker tokens absorbed into the same grant** (`tests/_suite_gate_lease.py`
  `WorkerTokenLease` is still a separate pool with its own directory, 45-minute
  default, 30-minute stale heartbeat). That unification is still unbuilt and is
  the one E7 item that is locally painful even at concurrency 4: tests and agent
  `check` currently account for CPU in two ledgers.
- Preservation of zero-weight gates (`sase-10h`'s contract) and `%hold` boundaries
  (`sase-11l`, closed).

### 5.2 Functionality this would unlock later

- E8's fleet snapshot (there is nothing honest to publish until local admission
  exists).
- Suggested weights and a PSI-respecting effective-capacity ceiling — recommended,
  never silently applied.
- Backfill of small requests in front of a protected heavy one.
- The reopen condition on `record-before-admit`: a measured concurrent-duplicate
  or queue-starvation rate that recording, triage, and receipts do not mitigate.

### 5.3 Why it is not worth starting now

The original brief said E7 starts after **E6 calibration** and after
`sase-zp` / `sase-11l` / `sase-10h` settle.

- E6 is not calibrated; it is not even planned.
- `sase-11l` is closed. `sase-z4` (weighted agent capacity) is closed.
  `sase-19f` (`%queue` multiplier, including fleet contract work) is closed.
- `sase-zp` and `sase-10h` still show `IN_PROGRESS` with **all child phases
  closed** — the same "parent bead not closed" pattern as E4. The contracts those
  epics own appear to be in the tree; the beads are not settled. That is a
  close-out problem, not a green light to extend `runner_capacity` with ToolRun
  demand.
- Peak ToolRun concurrency of 4, with 6 starts at concurrency 4, is not the
  "machine melting" story `sase-zm` was written to solve. Agent admission already
  caps running agents. `%hold` is the documented interim for "don't start more
  heavy work," and it needs no new ledger.
- Fail-closed admission is the first consumer that can *strand* agents. The
  original design requires a designed break-glass and finite queue wait because
  the failure mode is a frozen host. That cost is worth paying for a measured
  oversubscription problem. It is not worth paying to complete a roadmap.

The cheap next step is a **read-only backtest**: join this machine's 167 timed
`check` rows to their load samples and reproduce (or refute) the 2026-09-14
duration-vs-overlap curve. If load inflation is small, E7's brief shrinks to
"unify pytest workers." If it is large, E6's buckets and E7's queue both gain a
numeric case. Either way, that analysis belongs in E6's planning session, not in
an E7 kickoff.

---

## 6. E8 — Fleet capacity surfaces and coordinated rollout

Roadmap size: medium, ~6 phases. Original user-verifiable result: machine
badges/meters show fresh/stale capacity fleet-wide; drill-down answers "why is
apollo busy?"; staged athena/apollo/mac cutover with proven rollback. Optional T7
cross-machine prediction hints in `run -E`.

### 6.1 Functionality this epic would give immediately

- A versioned **per-machine tool-capacity snapshot** on the existing fleet wire:
  holders, queued demand, PSI, capacity source, freshness.
- Honest **fresh / stale / unknown** badges when peers are current, old, or
  offline. Remote rows already omit ToolRun chips because the ledger is
  machine-local (`docs/ace.md`); E8 is the first time a remote machine can show
  *why* it is busy without lying that it has no runs.
- `sase init` / doctor requiring explicit persistent machine capacity.
- A drain / activate / rollback rehearsal so old and new admission ledgers never
  coexist.
- Optional **hints only** in `run -E` ("athena's p90 for `check` is 12 min right
  now"). No remote dispatch, no cross-machine receipt cache.

### 6.2 Functionality this would unlock later

- A later remote-placement epic (explicitly out of E8, and still a bad idea until
  hermeticity is proven).
- Fleet-wide "don't launch another `check` on apollo" advice to humans and to
  launch policy.

### 6.3 Why it is not worth starting now

E8 is the only epic in the set whose exit is inherently multi-machine. Researcher
B's bead-graph finding, adopted in the consolidated roadmap, was that live
multi-machine acceptance is the #1 driver of deep remediation chains — which is
why E7 and E8 were split in the first place.

Today:

- **There is no local tool-admission snapshot to publish.** Shipping fleet meters
  for a ledger that does not exist is a UI over an empty model.
- **`sase-x7` (canonical-only cutover) is still `IN_PROGRESS`**, with `.5` and
  `.7`–`.15` open. The 2026-09-17 rule was "defer cross-machine publication until
  that cutover settles." It has not.
- Agent-side fleet capacity already has surfaces: `sase-z4` badges, `sase-19f`
  multiplier display, machine tabs (`sase-1bc` in progress). "Why is apollo busy?"
  is partially answerable for *agents*. The missing slice is ToolRun demand, which
  is E7.
- Coordinated three-machine rollout of admission is process, not product, until
  admission exists.

E8 remains a correct *eventual* epic. It is the wrong next epic.

---

## 7. What changed since the roadmap that should revise E6–E8

These are the environmental shifts that a 2026-09-17 plan could not see:

1. **E1.5 exists.** Adoption is a guard, not a hope. E6's corpus is the actual
   agent `check` population.
2. **E3 known-continuation exists.** `check` is a long, usually-red run that
   proceeds into tests. Automatic hand-off of `check` is the right agent default.
3. **E4 shipped proof, not skip.** Original ranked use-case #3 (receipts deleting
   74.5 h of `install` and 176 re-runs) is not available as wall-time savings.
   `install` has no TYPICAL and no rows here. Do not sell E6 or E7 as reuse.
4. **`check-full` left the default path.** Original E6/E2 guidance that "the tool
   decides" for `check-full` is a demo without a denominator. Point E6 at `check`.
5. **E5 already has elapsed, TYPICAL-amber, and silent.** E6 is an upgrade to
   those chips, not a greenfield surface. Keep E6 off pixel-level TUI invention.
6. **Agent capacity landed while E1–E5 ran.** `sase-z4`, `sase-11l`, `sase-19f`,
   `sase-11y` (service host) are closed. E7 is an *extension* of a live authority,
   which raises the merge cost and lowers the urgency: the host already admits
   agents.
7. **`sase-x7` did not settle.** E8's wire gate is still open.
8. **E4 and two capacity parents are "all phases closed, epic open."** Treat
   `sase-1ah`, `sase-10h`, and `sase-zp` as close-out work, not as hidden blockers
   for an E6 plan. They *are* blockers for an E7 plan that would extend the same
   capacity contracts.

---

## 8. Immediate versus unlocked, at a glance

| Epic | Immediate new capability | Unlocks later | Start now? |
| --- | --- | --- | --- |
| **E6** | `run -E`; auto inline/hand-off for `check`; `stats`; load-conditioned remaining time / overdue / stalled; `timeout: auto` | Calibrated prices, expected start, hang detection, E7 | **Yes — plan now, auto-route behind calibration** |
| **E7** | ToolRuns share `runner_capacity`; queue + expected start; `-B`/`-W`; pytest workers in the same grant | E8 snapshots; suggested weights; PSI ceiling | **No — after E6 calibration and a load-inflation backtest** |
| **E8** | Fleet fresh/stale/unknown tool-capacity meters; drill-down; staged admission cutover; optional cross-machine hints | Any future remote placement | **No — after E7 and `sase-x7`** |

---

## 9. Recommended next moves (in order)

1. **Finish E4 close-out on `sase-1ah`.** Live prepared-completion demo or an
   explicit accepted limitation; public schema `receipt:` field; completion value
   slots. This is hours-to-a-small-tale, not a new epic.
2. **Write only the E6 plan** (`/sase_plan`), with:
   - `check` as the acceptance tool;
   - advisory `run -E` / `stats` shipping before auto-routing;
   - auto-routing gated on chronological backtest coverage;
   - load-bucket fallbacks with sample counts;
   - censored timeouts/lost;
   - "out: admission, fleet wire, skip-reuse, ML";
   - a planning-session analysis of PSI/loadavg vs `check` duration on the
     existing ~167 timed rows (this is the E7 go/no-go seed, produced as E6
     evidence, not as an E7 phase).
3. **Keep `%hold` as the interim for "stop starting more heavy work"** until E7
   has a measured brief.
4. **Do not author E7 or E8 plans in the same batch.** The 2026-09-17 first-move
   list was "write the E1 plan only" for the same reason: later epics should be
   revised by what the previous one measures.

If epic budget is tight enough that even E6's original 8–9 phases look like
`sase-zm` again, cut E6 to three phases as in §4.4 and still include auto-routing
as phase 2. Auto-routing is the only remaining wrapper behavior that frees an
agent turn. Forecasts without routing are a nicer chip. Routing without forecasts
is a hard-coded "always `-H` for `check`" skill change — cheaper, and worse,
because a 30-second `test` and a 9-minute `check` would get the same policy.

---

## 10. Close

E1–E5 (plus E1.5) delivered the record, the hand-off, the triage, the proof
receipt, and the live surface. The wrapper's original thesis — value is the
record, admission last — is still the right thesis, and it is half-finished in
exactly the place the 2026-09-14 control-plane ranking predicted: **the tool does
not yet decide inline versus hand-off.**

E6 is that decision, now with nine days of load-sampled `check` history, 100%
7-day wrapped adoption, and a TUI that can show the result tomorrow. E7 is a
calibrated consumer of E6. E8 is a fleet publisher of E7. Start E6; let E7 and E8
earn their keep from E6's measurements.
