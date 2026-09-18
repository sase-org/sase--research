# Overnight SASE agent and epic-stall forensics

**Researcher:** A  
**Observation cutoff:** 2026-09-18 11:46 UTC / 07:46 EDT  
**Machines:** `apollo` and `athena`  
**Quantitative window:** 2026-09-18 00:00–11:46 UTC (2026-09-17 20:00–2026-09-18 07:46 EDT)

## Executive conclusion

Last night's main problem was not a lack of automatic continuation. Automatic continuation
usually worked. The problem was that it turned verification failures into long, effectively
unbounded repair/retry chains on an epic's critical path.

Three mechanisms combined:

1. Resource governance is split. Runner slots account for an agent or monitor as one unit,
   while the pytest suite gate governs only pytest worker tokens and deliberately admits two
   peer full-suite runs. It does not reserve the host for the entire verification pipeline
   (`install`, visual tests, performance checks, `check-full`, and selection-health). Heavy
   monitors therefore overlap with one another and with ordinary agents.
2. A failed verify monitor always hands its failure to another agent, but there is no causal
   failure classifier or retry budget. The successor commonly fixes or absorbs whatever the
   latest full run exposed, then launches the entire pipeline again. A phase can expand from
   its intended change into flake hardening, golden refreshes, host-state cleanup, performance
   budget changes, and baseline maintenance before it is allowed to close.
3. Bead dependencies make that retry loop a hard scheduling barrier. The phase bead remains
   `in_progress`, so the land agent and dependent phases remain `WAITING`. Meanwhile the
   ordinary status label says `TESTED` (or even `EPIC CREATED`) for a failed monitor; only
   `status_bucket=Failed` and `monitor_state` reveal the truth.

The clearest example was Athena phase `sase-126.4`: 15 verification monitors settled in the
window, 14 failed and one passed. The failed attempts consumed 5.98 aggregate monitor-hours,
the phase accumulated fixes and baseline changes well beyond a simple verification pass, and
it finally closed at 09:03 UTC. Its parent land agent then failed another verification because
a host-global temp entry existed, so the epic was still open at the observation cutoff even
though every phase was closed.

On Apollo, `sase-zr.7.1.1.5.4.2` spent 6h51m in its first agent, then its `just check-full`
monitor timed out at 90 minutes. The phase bead was still open and the land agent still waiting
at the cutoff. A continuation did launch, but the epic had made no bead transition for more
than eight hours.

## Method and evidence

I independently inspected:

- `sase agent list -a -j` and `sase agent show` on both hosts;
- authoritative `agent_meta.json`, `done.json`, workflow checkpoints, and retained monitor
  output under each host's SASE artifact tree;
- saved chats with `sase chat list/show`;
- current bead state with `sase bead show/search`;
- host load, runner-slot holders, and relevant suite-gate/monitor implementation code.

I treated `done.json.monitor_state`, `done.json.status_bucket`, and exit code as authoritative,
not the display label. Durations below are aggregate monitor runtime and may overlap in wall
clock time. I did not inspect or obtain findings from the other researcher in this swarm.

## What happened on Athena

### The verification loop dominated the night

Across all monitors that settled in the quantitative window:

| Metric | Athena total | `sase-126.4` | `0mi` |
| --- | ---: | ---: | ---: |
| Settled monitor runs | 25 | 15 | 7 |
| Failed or timed out | 19 | 14 | 3 |
| Aggregate failed runtime | 10.60 h | 5.98 h | 3.53 h |
| Aggregate total runtime | 13.44 h | 6.69 h | 5.64 h |

The `sase-126.4` chain began with an avoidable command-construction failure:
`just install '&&' ...` passed `&&` as a Just recipe. The continuation corrected the shell
chaining, but subsequent full pipelines exposed a succession of different conditions:

- a Hypothesis `too_slow` health check;
- three gate-decision tests incompatible with the newly pinned Rust-core contract;
- 106 visual snapshot failures, then several smaller snapshot and five-second UI timeout
  failures;
- a git-identity/temp-leak test failure;
- performance/cost failures and selection-health failures;
- a managed-temp horizon failure;
- repeated cleanup-confirmation and artifacts-pane golden mismatches.

The agents did not merely retry. They changed the phase tree after each result. The final bead
note says the phase ultimately included the core pin, VCS property-test hardening, gate
failure-attempt compatibility, several groups of visual goldens and fixture hardening,
usage-probe temp isolation, test-cost CPU-budget recalibration, and selection-health baseline
maintenance. Another note records 22 newly promoted reproducible-flake node IDs. This is
retry amplification and scope accumulation, not a bounded verification step.

The successful monitor, `sase-126.4--mon-d`, settled at 09:02 UTC and the bead closed one
minute later. The parent `sase-126` epic nevertheless remained `in_progress`: all four phases
were closed, but the land agent's first monitor failed. Its test process reported **42,791
passed**, then the enclosing `test-scoped` recipe exited nonzero because
`/home/bryan/.cache/sase/tmp/usage-probes` appeared as a new entry in a watched, host-global
temp directory. This is direct evidence that workspace isolation is insufficient for tests
which audit shared host state. A second land monitor was still running at the cutoff.

Representative Athena evidence:

- Initial `sase-126.4` monitor:
  `/home/bryan/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/17/20260917201508/`
- Successful fifteenth monitor:
  `/home/bryan/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/18/20260918041841/`
- Failed land monitor:
  `/home/bryan/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/18/20260918065415/`
- Chats are named with the `sase_126_4__mon*` and `sase_126_4__1` through
  `sase_126_4__f` family names in `~/.sase/chats/202609/` on Athena.

### Contention was observable in the test evidence

One `0mi` full run reported 7,089 seconds of aggregate file wall time versus 3,787 seconds of
CPU time and explicitly classified the wall-clock overruns as consistent with a busy host.
`sase-126.4` later recorded a similar 5,895 wall / 3,486 CPU split. Other runs failed
five-second TUI convergence waits. These are exactly the failure modes expected when multiple
large xdist, visual, and agent workloads overlap.

At 11:42 UTC Athena had seven runner slots occupied, three agents queued, 12 `just` processes,
and a load average near 31. It has 64 CPUs, so the load number alone is not proof of CPU
exhaustion; the stronger evidence is the wall/CPU divergence, timing-sensitive failures, and
simultaneous full verification chains.

## What happened on Apollo

### A phase timed out and held its land agent

`sase-zr.7.1.1.5.4.2--plan` started at 23:22 EDT and ran for 24,674 seconds (6h51m). It added
three acceptance-test groups, passed targeted tests, `just fix`, and `just check`, then started
`just check-full` in a verify monitor.

That monitor reached the lint and validation stages but did not finish within its 5,400-second
budget. At 11:43:55 UTC its authoritative result became:

- `monitor_state=timeout`;
- `monitor_exit_code=-15`;
- `status_bucket=Failed`;
- error: did not finish within 1h30m;
- `monitor_followup_outcome=launched`.

At the cutoff, successor `sase-zr.7.1.1.5.4.2--1` was running, the phase bead was still
`in_progress`, and `sase-zr.7.1.1.5.4.land` had been `WAITING` since 23:22 EDT. The monitor's
ordinary status string was nevertheless `TESTED`.

Evidence:

- First agent:
  `/home/bryan/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/17/20260917232233/`
- Timed-out monitor:
  `/home/bryan/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/18/20260918061327/`

At 11:42 UTC Apollo had all six runner slots occupied, eight `just` processes, a 16-CPU host,
and load averages around 21. A monitor's total timeout currently includes any resource-waiting
and slow progress caused by competing work, so a nominal 90-minute verification budget is not
a 90-minute execution budget under this load.

### Epic launch failure was terminal to its monitor

Family `0f` approved a new `completion_freshness.md` epic, but its launch monitor failed in
seven seconds because the plans sidecar already contained the same path for a differently
titled older epic. The monitor was labeled `EPIC CREATED`, while `done.json` says
`monitor_state=failed`, `status_bucket=Failed`, and has no follow-up outcome.

Current bead history shows the old `sase-z8` epic was subsequently closed as superseded at
10:03 UTC and the new `sase-12o` epic was created at 10:05 UTC, so this incident was recovered.
The failed monitor itself did not encode that recovery, however. A collision detectable before
approval was allowed to fail after approval, and the operator-facing status asserted the
opposite outcome.

Evidence:
`/home/bryan/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/18/20260918060027/`.

## Root-cause model

The incidents fit one model rather than several unrelated agent mistakes:

1. **Cost-blind admission.** A verify monitor has default queue weight 1, the same as a light
   agent. The pytest suite gate budgets worker processes, but its default fair-share policy
   intentionally leaves room for two peer full runs. It does not cover every expensive step in
   the monitor command.
2. **Shared host state escapes the workspace boundary.** The suite reads and audits paths such
   as `~/.cache/sase/tmp`, completion state, installed bindings, and host-local selection-health
   records. Concurrent agents can make another workspace fail without touching its git tree.
3. **Every failure becomes implementation work.** Follow-up prompts usually say to fix whatever
   failed and rerun the whole pipeline. They do not first decide whether the failure is caused
   by the phase, is a known flake, is host contamination, or is capacity-induced.
4. **No circuit breaker.** Fourteen failed monitors in one phase are legal. There is no
   per-family retry ceiling, no maximum time without a bead transition, and no automatic
   escalation from `retrying` to `attention required`.
5. **The dependency graph makes verification a global barrier.** An open phase prevents its
   land agent and dependent phases from starting. Even when continuation is healthy, the epic
   appears stalled because the only runnable path is the retry chain.
6. **Status semantics conceal the failure.** Stop labels describe the intended operation
   (`TESTED`, `EPIC CREATED`), while `status_bucket` describes the actual outcome. Most quick
   status views and human scanning naturally privilege the former.

## Recommended solution

Implement a **host-level verification controller with an epic watchdog**, and make it the only
path by which automated agents run heavyweight landing verification.

### 1. Govern the whole verification job, not only pytest workers

Add a SASE resource class such as `heavy_verify`. Acquire its host lease before the monitor's
execution timeout starts, retain it across the entire command, and expose the wait as
`QUEUED FOR VERIFY` rather than `TESTING`. Initially allow exactly one heavy verification per
host. The lease must cover `install`, `just check-full`, visual tests, performance checks, and
selection-health, not just the xdist subprocess interval.

Give heavy verification a resource weight reflecting its real fan-out. Ordinary agent slots
may continue to admit light reasoning/editing work, but additional full-suite monitors should
queue without consuming their execution budget. Measure clean-host p95 duration separately on
Apollo and Athena and derive timeouts from that measurement.

As an immediate configuration mitigation, make each governed full pytest run request the
entire configured suite-gate pool (set the worker floor and ceiling equal to the pool size), so
two full runs cannot overlap. Choose a memory-safe pool per host. This is only a stopgap because
visual/performance and other host-global steps still need the outer lease.

### 2. Enforce two-speed verification

Make `just check` the phase-worker default and reserve one serialized `just check-full` for the
integrated land agent, matching the repository's documented two-speed policy. An epic may
explicitly designate one verification phase, but the scheduler should deduplicate identical
full-tree verification requests for the same integrated commit. Do not run the same exhaustive
tree once per phase and again at land.

### 3. Classify before retrying, and cap retries

On failure, a small diagnostic continuation should classify the result:

- **deterministic and caused by this diff:** fix it, run the failing node/lane, then make one
  fresh full attempt;
- **known or newly reproducible flake:** reproduce in isolation, record/corroborate it, and
  retry only once under a clean heavy lease;
- **shared-state contamination or capacity timeout:** clean or namespace the offending state
  and requeue; do not edit product code or goldens;
- **unrelated deterministic failure:** route it to its owner and preserve evidence rather than
  absorbing it into the active phase.

Use a circuit breaker: after two failed heavy attempts, or after two hours without a bead-state
transition, stop automatic full retries. Mark the family `ATTENTION`, keep the diagnostic refs,
and raise one actionable notification/gate. This sacrifices the illusion of continuous motion
but prevents a single phase from consuming the entire night and obscuring the actual blocker.

### 4. Add an epic-progress watchdog

Track, per epic, the last bead transition, current live owner, heavy-verification attempts, and
dependency frontier.

- If an epic has runnable non-closed beads but no live agent, automatically rerun the existing
  idempotent `sase bead work <epic>` recovery.
- If all phases are closed, prioritize the land agent for the next heavy-verification lease.
- If the only live path is over its retry/time budget, surface `DEGRADED`/`ATTENTION` instead of
  leaving dependents as unexplained `WAITING` rows.
- Emit a morning summary of epics with no bead transition for two hours, failed monitor counts,
  and the exact frontier bead.

### 5. Isolate host-global test state

Give each verification lease a private managed temp/cache namespace and make shared-state audits
lease-aware. At minimum, isolate the usage-probe/temp roots and selection-health scratch state.
Tests that intentionally inspect a shared production root must either snapshot it at lease start
or hold the same exclusive lease; otherwise one legitimate agent action can fail another run.

### 6. Make launch and status outcomes truthful

- Reserve or validate the plans-sidecar destination before the approval gate. A conflicting
  archived plan should force a unique stem or an explicit supersession decision before approval.
- Every epic-launch monitor failure should have a recovery continuation or a gate; never end at
  a failed `EPIC CREATED` row.
- Render the actual bucket first: `FAILED (wanted: TESTED)` or `TIMEOUT (wanted: TESTED)`.
  Aggregate family rows should show `RETRYING 4/2` or `ATTENTION`, not only the latest authored
  stop label.

## Why this is the best first investment

Improving prompts or increasing timeouts would treat symptoms. Last night already demonstrated
that agents can diagnose and continue; what they lack is orchestration policy that distinguishes
productive recovery from retry amplification. A whole-job verification lease, causal failure
classification, and a bounded epic watchdog directly address every observed stall:

- Apollo's 90-minute timeout would wait outside its execution budget and run without a competing
  full verification;
- Athena's 14-failure chain would trip a clean-host retry and then a circuit breaker instead of
  repeatedly widening the phase;
- the land temp-leak failure would be classified as cross-agent contamination rather than a code
  regression;
- the plan collision would be rejected before approval;
- Bryan would see the true failed frontier immediately, even when a continuation is running.

That combination should make unattended nights boring: most epics keep advancing, expensive
verification is serialized and predictable, and the exceptional epic stops once with a precise,
visible blocker instead of silently burning the rest of the night.
