# Overnight epic stalls on apollo and athena: consolidated findings and prevention plan

_Lead-researcher consolidation of researcher A (`overnight_epic_stall_prevention__a.md`),
researcher B (`overnight_epic_stall_prevention__b.md`), and independent verification
performed 2026-09-18 08:15–08:30 EDT. Night studied: 2026-09-17 18:00 → 2026-09-18 07:00
EDT. Times are EDT unless marked `Z`._

## TL;DR

The fleet does not fail because agents crash. Of the ~187 agent shells started overnight
(athena ~157, apollo ~30), only two failed outright. Epics stall because a small set of
**systemic mechanisms** either hide a stall behind a reported success or turn one failed
verification into an unbounded, host-saturating retry chain. Five mechanisms, ranked by
overnight impact:

1. **Silent success with an open bead.** A phase agent hits a blocker outside its
   control (a PyPI release, a red host-wide gate), records a `PROPOSED FOLLOW-UP`, keeps
   its bead open, and exits green. Dependents wait forever and no alert fires. This
   idled apollo for ~6 hours last night and is why three older epics are still stuck.
2. **Lost monitor handoff.** On athena, `sase monitor start` takes 23–68 s; codex can
   end the turn while it is in flight, killing it before any record exists. The host
   then reports the run as a clean success. Two land continuations — the ones that close
   parent epics — vanished this way.
3. **Unbounded verification retry loops under cost-blind admission.** A failed verify
   monitor always launches a fix-and-rerun successor with no failure classification, no
   retry ceiling, and no host lease over the full pipeline. `sase-126.4` ran 15
   monitor→fix cycles (14 failures, ~6 h of failed monitor runtime) while widening its
   own scope each cycle, and contention it generated helped time out two other 90-minute
   `check-full` monitors.
4. **Loud failures with no recovery path.** An invalid `--model` copied from the
   `sase_monitor` skill doc 400'd a follow-up at 03:10; a 41-hour waiter woke into a
   `NameCollisionError`; an epic launch failed on a plans-sidecar path collision that
   was detectable before approval. Each produced at best a passive notification.
5. **Landing recursion and the missing plan→plan close.** Land agents `%auto`-spawn
   nested child epics (8–9 new last night; chains now 4–6 levels deep), and closing a
   follow-up epic never cascades to its parent *plan* — that step is left to an LLM
   running inside the same handoff that mechanism 2 loses. Result: ~29 "zombie" epics
   whose children are all closed, buried in 153 in-progress beads that hide real stalls.

**Recommended solution** (detailed in §5): make epic liveness a **host-owned,
deterministic invariant** — no silent success, handoff intent markers with runner
replay, and an epic-liveness watchdog (P0/P1) — and put heavyweight verification under a
**host-level lease with failure classification and a retry circuit breaker** (P2). P0+P1
would have caught every silent stall last night within minutes; P2 is what stops the
`sase-126.4`-style loops that consume the rest of the night.

## 1. How the two reports relate, and what independent verification showed

The reports approached the same night from opposite ends and are largely complementary:
A quantified the **verification-retry economics** (monitor counts, runtimes, host
contention, scope creep) while B catalogued the **stall mechanisms and their
silencing** (open beads, lost handoffs, recursion, zombie epics). Both independently
found the two 90-minute `check-full` timeouts, the `sase-126.4` 15-cycle loop, athena
overload, and the two-speed-verification violation.

Material disagreements, resolved:

- **"Automatic continuation usually worked" (A) vs. two silent handoff losses (B).**
  Both are right: continuation worked in every *loud* failure, but B's two lost
  handoffs (23:26 and 03:19) were invisible to A's method because the host recorded
  them as successes. I verified B's mechanism directly in the code:
  - `begin_gate_intent`/`raise_if_gate_intent_lost` (the sase-11t guard) is used by
    gate, sudo, and gate-shell code paths but **nowhere under `src/sase/monitor/`**.
  - The monitor start flow persists its intent only *after* the supervisor
    acknowledges (`persist_monitor_start_intent_after_ack` in
    `src/sase/monitor/start.py`), so a start killed mid-flight leaves no trace.
  - The codex turn-integrity check (`_subprocess_codex.py:72`) returns no error
    whenever the final agent message is non-empty — a confident "handing off" message
    defeats it exactly as B described.
- **Apollo's `sase-zr.7.1.1.5.4.2` "spent 6h51m in its first agent" (A).** This is a
  duration artifact. The bead record shows `.4.2` is dependency-blocked by `.4.1`
  (`BLOCKS` edge), `.4.1`'s note #1 (23:50) recorded the PyPI floor blocker and left
  the bead open, and the rerun's notes #2–#3 closed it at 05:51. So `.4.2`'s shell
  existed from 23:22 but sat in B's silent open-bead stall for ~6 h; its active run was
  roughly 30 minutes before the 06:13–07:43 monitor timeout. B's account explains
  apollo's idle night; A's contribution is what happened *after* the stall cleared.
  Notably, the 05:42 rerun closed the bead on the same evidence the 23:22 run used to
  keep it open — close criteria are model judgement today, which is why this mechanism
  is nondeterministic.
- **Where the retry loop ranks.** B lists the `sase-126.4` loop as an "amplifier"; A
  makes it a primary mechanism. A's accounting (14 failed monitors, 5.98 h failed
  runtime, scope accumulating flake promotions, golden refreshes, and budget
  recalibration cycle after cycle) justifies treating it as primary: it consumed the
  host, which in turn manufactured timeout and timing failures for everyone else
  (wall/CPU splits of 7,089 s vs 3,787 s in one run classified as busy-host).

Other independent verifications:

- Suite-gate admission: `tests/_suite_gate_budget.py` sets
  `_DEFAULT_AUTOMATIC_FAIR_SHARE_RUNS = 2` — the default ceiling is a peer-sized share,
  i.e. the pool deliberately admits **two** concurrent full runs, and the gate governs
  only pytest worker tokens, not `install`/visual/perf/selection-health (A's claim).
- Admission weight: `src/sase/default_config.yml` — every agent claims 1.0 capacity
  unit unless it requests more, so a `check-full` monitor is admitted like a light
  reasoning agent (A's "cost-blind admission").
- `wait_checks`: `_identity_terminal_blocker` (`sase_chop_wait_checks.py:467`) requires
  a done marker with a **non-success** outcome — a successful run that left its bead
  open can never trip it (B's claim).
- Backlog: 153 beads are in-progress right now (B counted 154), corroborating the
  zombie-epic burial problem.

## 2. What actually happened, condensed timeline

**apollo** (30 shells; idle ~23:53–03:07):

- 19:55–23:22 — the `sase-zr.7` chain recursed two more levels
  (`sase-zr.7.1.1.5` → `sase-zr.7.1.1.5.4`), reaching nesting level 4.
- 23:53 — `.5.4.1` completed but left its bead open on the PyPI 0.34.50 blocker
  (mechanism 1). `.4.2` and `.4.land` waited; **no alert**; apollo idle.
- 05:42 — Bryan reran the epic by hand; the rerun closed `.4.1` at 05:51.
- 06:13–07:43 — `.4.2`'s `just check-full` monitor timed out at its 90-minute budget
  (`monitor_state=timeout`, exit −15, `status_bucket=Failed` — while the display label
  said `TESTED`). Continuation launched; still running as of 08:20, with `.4.land` and
  the whole upper `sase-zr.7` chain (`.2`, `.3`, `.5`, `.land`) still WAITING.
- ~02:00 — family `0f`'s epic launch failed in 7 s on a plans-sidecar path collision
  (`completion_freshness.md` already existed for an older epic), labeled
  `EPIC CREATED` despite `monitor_state=failed` (mechanism 4). Recovered by hand at
  ~10:03Z as superseded `sase-z8` → new `sase-12o`, now running.

**athena** (157 shells, 42 monitors):

- Five land agents spawned nested child epics through the night (mechanism 5).
- 23:26 — **lost handoff #1**: `sase-11y.2.1.5.land`'s `sase monitor start … just
  check-full` was killed when codex ended the turn 24 s after the call; run reported
  `completed`; parent epics `sase-11y.2.1`/`.2` stayed open, blocking `sase-11y.4`–`.10`
  until Bryan intervened at 03:16.
- 20:15–06:22 — `sase-126.4` ran 15 monitor→fix cycles (mechanism 3): a
  command-construction error, then successive full pipelines each exposing a different
  condition (Hypothesis health check, Rust-core contract pins, 106 visual snapshot
  failures, temp-leak audit, performance budgets, selection-health baselines), with the
  phase absorbing fixes for all of them plus 22 flake promotions before closing at
  05:03. The `sase-126` land agent then failed *its* verification because a concurrent
  agent's `~/.cache/sase/tmp/usage-probes` entry tripped a host-global temp audit —
  42,791 tests passed, run failed anyway (shared-state escape).
- 01:38–03:10 — `sase-124.8.4.3.2`'s `check-full` timed out; its follow-up died with
  `400 … 'gpt-5' model is not supported` from the copied `--model codex/gpt-5` example
  (mechanism 4). The 03:12 "can never self-resolve" notification looked like the other
  noise; nothing acted. `sase-124.8.4.3` is still open now with its land waiter gone.
- 03:19 — **lost handoff #2**: `sase-11l.5.1.land--1`, same race. Bryan closed the epic
  by hand at 06:18; the 41-hour waiter `sase-11l.6` then woke into a
  `NameCollisionError` and needed a manual relaunch.
- Still stalled from earlier nights: `sase-11h.4` (red selection-health gate),
  `sase-11i.6.4` (over-budget benchmark + 602 visual mismatches), `sase-11o.2`
  (agents-sync reconcile blocked) — all mechanism 1, all still open today.

**Amplifiers** behind all of it: red host-wide gates (`check-full` master red per
sase-j0, visual drift per sase-x5, pyscripts lint per sase-12n) turned every
verification phase into a coin flip; athena ran all runner slots full with `check-full`
taking 30–153 minutes; sase self-updated 6× on athena and 4× on apollo mid-flight
(no failures last night, but wire-schema/import failures earlier in the week); and 17
"Epic launch outcome is unknown" false alarms since 09-11 trained the operator to
ignore the one notification that mattered.

## 3. Root-cause model

One sentence per mechanism, with the structural gap that makes it possible:

1. **Nothing checks the bead post-condition.** A run's outcome is computed from the
   provider run and finalizer only; a `completed` run with an open assigned bead is
   indistinguishable from success, and `wait_checks` only alerts on *failed*
   dependencies. Close-vs-keep is unbounded LLM judgement.
2. **The monitor handoff has no intent record until after acknowledgement.** The
   sase-11t intent-guard pattern exists precisely for this race but was never applied
   to `sase monitor start`; the codex integrity check trusts any non-empty final
   message; the declaration-recovery turn then launders the loss into a success.
3. **Verification is admitted cost-blind and retried judgement-free.** Weight-1
   admission, a worker-token gate that deliberately seats two peer full runs and
   governs nothing else in the pipeline, follow-up prompts that say "fix and rerun
   everything," no failure classification (own-diff vs flake vs contamination vs
   capacity), no retry ceiling, and a monitor timeout that counts contention against
   the execution budget.
4. **Launch- and wake-time failures have no generic recovery layer.** Model strings,
   plan paths, and agent names are validated only after the requester is dead; the
   failure classes rotate nightly, so per-class fixes never converge.
5. **The bead graph makes every one of the above a hard barrier, invisibly.** Deep
   `%auto`-approved recursion multiplies land steps; the plan→plan close is manual;
   display labels (`TESTED`, `EPIC CREATED`) describe intent while `status_bucket`
   holds the truth; and zombie epics bury the live stalls.

## 4. Immediate recovery (no code required)

- `sase-124.8.4.3` — rerun `sase bead work sase-124.8.4.3`; its land waiter is gone and
  phase `.2` failed on the bad-model follow-up.
- `sase-zr.7` — decide whether the four-level `sase-zr.7.1` chain should be collapsed
  so `.2`, `.3`, `.5`, and the land agent can run; the `.5.4.2` continuation is the
  only live path today.
- `sase-11h.4`, `sase-11i.6.4`, `sase-11o.2` — override-close, block, or cancel each;
  they will not self-resolve.
- Triage the ~29 zombie epics (in-progress plans with all children closed).
- Bedtime checklist until the fixes land: green `just check` on master (fix or waive
  sase-12n; keep sase-j0/sase-x5 gates out of phase criteria); no in-progress epic
  whose open beads lack a live agent; no phase criterion that needs a PyPI release or
  cross-host drill; pause `dev_update` on athena.

## 5. Recommended solution

**Organizing principle:** extend the `host-owned-completion` decision to *progress*.
Agents may claim progress; the host verifies it, records the truth, and recovers
deterministically. In parallel, govern heavyweight verification as a host resource with
bounded retries. Priority order:

### P0 — stop the silent stalls (would have caught 23:53, 23:26, 03:19 within minutes)

- **P0-a No silent success.** When a run with an assigned phase/land bead ends
  `completed`, the runner re-reads the bead. Open bead + no live family handoff + not
  explicitly blocked ⇒ record `completed_blocked` (not success) and raise **one**
  high-priority `EpicStalled` notification (Telegram) with three actions: relaunch
  phase / close anyway / cancel phase. Render true outcomes first everywhere:
  `FAILED (wanted: TESTED)`, `RETRYING 4`, `ATTENTION` — never the authored stop label
  alone.
- **P0-b Handoff intent markers for `sase monitor start`.** Write a
  `.sase_handoff_intent.monitor` file (full argv) as the *first* action, before heavy
  imports, the lane lock, and preflight. After the provider exits, an unconsumed intent
  with no matching monitor record ⇒ the runner **replays the start itself** from the
  recorded argv (it still holds the workspace claim), else fails the run with
  `HandoffLost` via the sase-11t guard machinery. Tighten the codex integrity check:
  any pending `monitor start`/gate/pipe/plan/questions/sudo command at turn end is a
  failure regardless of the final message. Reword the `sase_monitor` skill: never end
  the turn while the start command is in flight.
- **P0-c Validate at request time; retry with inherited settings.** Check `--model`
  against the provider's live catalog and account limits while the starter is alive,
  and on a non-retryable launch failure relaunch once with the starter's inherited
  route. Validate/reserve the plans-sidecar destination before the approval gate (a
  collision forces a unique stem or an explicit supersession decision). Remove
  `codex/gpt-5` from the skill doc examples. Every epic-launch monitor failure must end
  in a recovery continuation or a gate, never a failed `EPIC CREATED` row.

### P1 — epic-liveness watchdog (catches everything P0 misses, including waker crashes)

An AXE job every ~10 minutes enforcing: **every open descendant bead of a launched epic
has a live owner** (running/queued/waiting shell, running monitor, human-waiting gate,
or an explicit blocked mark). For an orphan, fixed policy: retryable failed phase ⇒ one
`sase bead work <epic>` relaunch; plan with all children closed and no live land agent
⇒ relaunch the land agent (this deterministically closes the plan→plan cascade gap and,
in report-only mode, triages the 29 zombies); waiter process gone ⇒ relaunch the
waiter; otherwise, or on second orphaning, escalate `EpicStalled` once per epic. Add
A's progress clocks: track last bead transition and heavy-verification attempts per
epic, escalate after two hours without a transition, and emit a morning digest (stalled
epics, cause, one-key fix). The liveness computation belongs in `sase-core` (TUI, CLI,
and Telegram need the same answer); the job and a `sase bead liveness` command are thin
adapters.

### P2 — govern verification (stops the retry loops and the timeout cascade)

- **Whole-job host lease.** A `heavy_verify` resource class acquired *before* the
  monitor's execution timeout starts and held across the entire pipeline (`install`,
  `check-full`, visual, performance, selection-health) — initially one per host, with
  queued waiters shown as `QUEUED FOR VERIFY` and not burning their budget. Stopgap
  until it ships: set the suite-gate worker floor = ceiling = pool so two full runs
  cannot overlap.
- **Enforce two-speed verification** (per the `two-speed-verification` decision):
  `just check` is the phase default; one serialized `just check-full` gates landing;
  deduplicate identical full-tree requests for the same integrated commit.
- **Classify before retrying, and cap retries.** A cheap diagnostic continuation sorts
  each failure: caused-by-this-diff ⇒ fix, run the failing lane, one fresh full
  attempt; known/reproducible flake ⇒ record it, retry once under a clean lease;
  shared-state contamination or capacity timeout ⇒ clean/namespace and requeue, never
  edit product code or goldens; unrelated deterministic failure ⇒ route to its owner.
  **Circuit breaker:** after two failed heavy attempts, stop automatic full retries,
  mark the family `ATTENTION`, and raise one actionable gate. This is what prevents the
  next `sase-126.4`.
- **Timeouts from measurement.** Derive `check-full` monitor budgets from clean-host
  p95 per machine (athena needs ≥3 h; 90 minutes timed out twice), and exclude
  lease-wait time from the execution budget.

### P3 — stop generating stalls

- **Cap landing recursion** (implements the 09-16 research): no `%auto` approval of a
  child epic at nesting depth ≥2 — require a human `EpicApproval`; release- or
  gate-blocked residuals become typed task beads, not nested epics; add a sanctioned
  "land-with-residuals" exit that closes the epic and leaves the parent chain
  unblocked.
- **First-class blocked state.** `sase bead block <id> --on release|global-gate|human
  --reason …` (lifecycle-owned, since agents never hand-edit status) raising one triage
  gate; change `bd/work_phase_bead` to require it instead of leaving beads open; the
  watchdog and P0-a treat blocked beads as human-owned.
- **Isolate host-global test state.** Per-lease temp/cache namespaces (usage-probe
  roots, selection-health scratch); shared-root audits must snapshot at lease start or
  hold the exclusive lease — one legitimate concurrent agent action must not fail
  another run.
- **Freeze self-updates while epics are in flight**, applying them at quiescent points.
- **Cut alert noise.** Suppress "Epic launch outcome is unknown" when success arrives
  within 60 s; route `EpicStalled` above `TaskTriage`.

### Why this order

P0-a/b/c are small, verified-gap fixes (one bead read per run; an intent file plus
replay; request-time validation) that convert every silent stall into a loud,
actionable one. P1 is the safety net that survives crashed wakers and future unknown
failure classes — the classes rotate nightly, so the generic invariant beats per-class
patches. P2 is the largest build but addresses the only mechanism that actively
consumes the night rather than merely pausing it, and its stopgap (fair-share = pool)
is a one-line configuration change. Together they make an unattended night boring:
epics keep advancing, expensive verification is serialized and predictable, and the
exceptional epic stops once, visibly, with a precise blocker.

## 6. Follow-up work

Concrete defects identified (candidates for task beads, deduplicated against known
work): the monitor-start handoff race (P0-b), silent success with an open bead (P0-a),
`--model` accepted unvalidated plus the stale skill example (P0-c), the plan→plan close
cascade gap, monitor-start latency scaling with archive size on athena (23–68 s vs
2.5–5 s on apollo; related to open epic sase-zu), and waiter `NameCollisionError` at
wake after long waits. The plans-sidecar collision and pyscripts lint already have
recovery/beads (sase-12o launched; sase-12n filed).
