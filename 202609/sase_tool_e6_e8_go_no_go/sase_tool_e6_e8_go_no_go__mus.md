# Re-evaluating E6–E8 of the `sase tool` epic roadmap

**Researcher mus · 2026-09-29 · independent report**
**Input:** `202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md` (consolidated,
2026-09-17) plus its sibling researcher reports `__a.md` / `__b.md`, read as background
only; all conclusions below are my own, verified against today's tree and bead store.
I did not locate, open, or consult any peer `__cdx/__cld/__grk/__gem` report from this
swarm.
**Premise taken as given:** E1–E5 are complete. I spot-checked this rather than
re-proving it (§1).

## 1. Is the premise true? (spot check, 2026-09-29)

Mostly yes — the E1–E5 user-verifiable results exist on today's tree:

- `sase tool --help` offers `failures, list, receipt, receipts, run, runs, show, stop,
  wait`. That is the E1 ledger + E2 hand-off + E3 triage + E4 receipt surface in one
  command.
- `sase tool list` prints `LAST` and `TYPICAL` columns; `check` shows `7m 11s (n=30)`.
  The duration corpus E6 needs is accumulating, not hypothetical.
- `sase tool receipts` reports retained receipts plus measured content-equivalent
  repeats (observed: 12 groups, 22 repeat runs, 2.71 h summed duration). That is E4
  paying off in the exact currency B predicted: repetition, not mis-scheduling.
- `sase tool failures` groups signatures with a `CLASS` column (observed `KNOWN`
  rows). That is E3's NEW/KNOWN machinery working.
- What is *absent* is exactly E6–E8: `sase tool run --help` has no `-E/--explain`,
  there is no `stats` subcommand, no queue/expected-start language, no capacity
  snapshot or fleet meter. The roadmap's cut lines held: E6–E8 are genuinely
  unshipped, separable work — not leftovers accidentally omitted from E1–E5.

One caveat: E4's parent bead `sase-1ah` is still `IN_PROGRESS` with all 7 phases plus
a child epic closed. The feature works, but the epic has not formally landed. Treat
"complete" as "shipped and observable," with landing hygiene still pending — it does
not block E6 evaluation, but E7/E8 should not start while their prerequisites are in
the same half-landed state.

## 2. E6 — Forecasts and automatic inline-vs-hand-off (large, ~8–9 phases)

### What it immediately gives you

- `run -E/--explain`: predicted duration interval + sample count + the inline / reuse /
  hand-off decision, before paying for the run.
- Automatic routing: `run` makes the inline-vs-hand-off call itself and says why in one
  stderr line, instead of relying on a prompt rule the agent must remember and often
  gets wrong (B measured both failure directions on apollo: 75-minute inline turns
  held open *and* 4–7-second failed hand-offs).
- `stats` with honest calibration (≥80% interval coverage on chronological backtest),
  survival-conditional remaining time, overdue/stalled states (never a regenerated
  ETA), and calibrated `timeout: auto`.
- Notifications for overdue/stalled through the existing dedup store.

### What it unlocks later

- E6 is the pricing oracle for E7: admission prices are guesses until durations are
  calibrated. Both researchers agree E7 must not start before E6 calibration, and the
  consolidated roadmap sequences E6's *start* by corpus age (~3 weeks post-E1), not by
  roadmap position.
- `timeout: auto` and overdue detection compound with every future long-running
  feature (fleet hints, staged verification).

### Why the timing is now favorable

- The calendar gate that blocked E6 in September is the one gate that passes by
  itself: E1–E5 shipped, the ledger has been recording, and `check` already has
  n=30 typical-duration samples. The corpus concern has flipped from "nothing
  recorded" (zero load hits anywhere in `src/`, per B) to "verify calibration on real
  data."
- The design is deliberately un-ML: empirical load-bucket quantiles with transparent
  fallback and sample counts, censored-observation handling, advisory-until-calibrated.
  This bounds the downside — the failure mode is "says unknown," not "confidently
  wrong."

### Costs and risks

- It is the largest remaining epic (~8–9 phases) and its value is advisory until the
  backtest passes; there is a real chance of building the machinery and discovering
  some cohorts never reach calibration (e.g. `check-full` with n≈0 typical samples —
  `sase tool list` currently shows `check-full` with no typical at all).
- Cheaper substitutes exist and are already scoped as READY task beads: `sase-17e`
  (mechanical routing: per-tool duration classes + provider sync ceiling) and
  `sase-17g` (inline-then-escalate: `--detach`, ceiling-bounded `wait`,
  `monitor start --join`). Either captures a large share of the "stop choosing badly"
  value with no predictor at all. They are alternatives *and* complements: 17e/17g
  remove the need for an up-front guess; E6 makes the guess good.

### E6 verdict: worth doing, highest of the three

The measured pain (hour-long inline turns, instant-fail hand-offs, unpriced heavy
work) is real, the corpus gate has matured, and the no-ML/advisory-first design keeps
it honest. Sequence it as: read-only forecasting first (`stats`, `-E`, calibration
report), auto-routing only after the backtest passes.

## 3. E7 — Local tool capacity admission (large, ~8 phases)

### What it immediately gives you

- One authoritative budget shared by tools, agents, and pytest workers (extend Rust
  `runner_capacity`, absorb the `WorkerTokenLease` pool from `tests/` — no second
  ledger, no Python queue).
- A second heavy run queues with an expected start instead of oversubscribing; typed
  refusals print an executable retry; `-B` bypass is recorded as forced.
- Fail-closed admission with designed break-glass (recording itself stays fail-open);
  `sase-10h` zero-weight gate semantics and `sase-11l` hold boundaries preserved.

### What it unlocks later

- Safe concurrency for everything that runs heavy work: recipe setup/build/pytest
  behind one grant, nested-grant validation, crash/reboot recovery of reservations.
- It is the prerequisite for E8 (nothing fleet-wide to publish until the local
  authority is real).

### Why it is weaker than E6 right now

- The substrate is ready (`runner_capacity` schema v5 exists; `sase-zp` and `sase-10h`
  have all phases closed with epics near landing), but the *demand* evidence is thin.
  B's core empirical finding was that dominant waste is re-discovery and repetition —
  exactly what E3/E4 attack without any queue. Zero repeated request fingerprints in
  14 days on apollo undercuts the single-flight case, and no one has published a
  queue-starvation or concurrent-duplicate rate that would force admission-first.
- Fail-closed admission is the only remaining epic that can *block* work by design.
  On a 1–3-machine personal fleet where contention is occasional, the expected value
  is "prevents rare oversubscription" against a persistent cost of "a new way for a
  run to refuse to start." The roadmap itself prescribes a cheap interim (`%hold` on
  heavy runs, no ledger) — that stopgap has not been shown insufficient.
- Gating is explicit: E7 wants E6 calibration *and* settled `sase-zp`/`sase-11l`/
  `sase-10h`. The phases are closed but the epics are still open; starting E7 now
  inherits their landing risk.

### E7 verdict: defer until contention is measured

Adopt the decision record the roadmap asks for ("recorded before admitted") with the
stated reopen condition — a measured concurrent-duplicate or queue-starvation rate —
and instrument that rate first. Keep the `%hold` stopgap. E7 is the classic
"valuable but not yet priced" epic, and its own roadmap says prices come from E6.

## 4. E8 — Fleet capacity surfaces and coordinated rollout (medium, ~6 phases)

### What it immediately gives you

- Trustworthy fleet-wide capacity: machine badges/meters with fresh/stale/unknown
  honesty, drill-down answering "why is apollo busy?" (holders, queued target,
  pressure, expected start), per-machine capacity through init/doctor.
- Staged athena/apollo/mac activation with drain, proven rollback, and no double
  admission.

### What it unlocks later

- Optional cross-machine prediction *hints* in `run -E` (explicitly no remote
  dispatch, no cross-machine result caches, no combined fleet denominator). It keeps
  the door open to placement-aware scheduling without committing to it.

### Why it must wait regardless of worth

- Hard prerequisite `sase-x7` (canonical-only fleet) is still `IN_PROGRESS` with
  `.5/.7/.8/.9/.10` and beyond open. The consolidated roadmap defers all
  cross-machine publication until that cutover settles — that condition is not met.
- Its value scales with fleet size and multi-machine daily pain. On today's
  athena/apollo/mac fleet the "which machine is busy" question is real but
  answerable by direct inspection; E8 turns it into a surface, which matters more as
  agents genuinely span machines (dispatch work is active but separate).
- Risk profile is the project's worst measured category: multi-machine cutover is the
  #1 driver of deep remediation chains in B's 600-bead analysis. The roadmap's split
  of E7/E8 exists precisely to quarantine that risk — which argues for doing E8
  *last and alone*, never bundled.

### E8 verdict: worth doing eventually, not now

When `sase-x7` settles and E7's local authority exists, E8 is a clean medium epic
with honest-staleness semantics and proven rollback. Today it is blocked on both.

## 5. Recommendation

**Do E6. Defer E7. Schedule E8 after `sase-x7` and E7.**

Concretely:

1. **E6 — proceed**, staged read-only first: land `stats` + `run -E` + the
   chronological calibration report against the now-real corpus (`check` n=30 is the
   seed; `check-full`'s empty typical is the known hard cohort). Enable automatic
   inline-vs-hand-off only when the ≥80% coverage gate passes per cohort, low-sample
   cohorts staying `unknown`. In parallel or first, land the cheap `sase-17e` /
   `sase-17g` mechanics — they pay off even where calibration never arrives, and
   `sase-17g`'s escalate pattern is independently the end of ad-hoc monitor-guessing.
2. **E7 — do not start.** Record the reopen condition as a decision (measured
   queue-starvation / concurrent-duplicate rate), instrument that rate off E1's
   ledger, and use `%hold` as the interim. Revisit after E6 calibration plus
   `sase-zp`/`sase-10h`/`sase-11l` fully landed.
3. **E8 — do not start.** Gate on `sase-x7` cutover settled *and* E7's local
   authority real. When both hold, it is a well-scoped medium epic; keep it isolated
   from any supervision or admission cutover per B's "one epic, one acceptance
   surface" lesson.

Net: E6 converts the corpus E1–E5 already paid for into decisions; E7/E8 each lack
one prerequisite (contention evidence; settled fleet contracts) that time and the
E6 work itself will supply. Every epic still pays for itself alone if its successors
never ship — but only E6's payment is currently due.
