---
create_time: 2026-09-04
updated_time: 2026-09-04
status: research
---

# Ending `stitch_timeout` Agent Failures: Consolidated Findings And Recommendation

**Research question:** SASE agents on apollo keep failing with
`LLMInvocationError: Error: sase stitch create stitch_timeout`. What is actually
consuming the budget, and what fix is reliable and robust on all machines, including
low-resource ones?

**Provenance:** This consolidates two independent research reports —
`stitch_timeout_hardening__a.md` (evidence audit of all nine apollo failures, options
analysis, durable-architecture design) and `stitch_timeout_hardening__b.md` (code-path
trace, live `just fix` timing measurement, incremental fix sequence) — plus a third
verification pass on 2026-09-04 that re-checked the code claims against master
`b8f62f182` and pulled fresh post-fix evidence from apollo.

---

## Executive summary

**The error is not an LLM failure.** The model turn finished and submitted a valid
final declaration; `LLMInvocationError` is only the wrapper that carries a host-side
failure through the provider boundary. What actually failed is the host-owned commit
finalizer: its `sase stitch create` subprocess hit a hard wall-clock cap and was
killed.

**Nine of twenty-five finalizer runs on apollo (36%) timed out on Sep 3–4, and every
one ran under the old 600-second cap.** The mitigation raising it to 1800s
(`ad1da7fc2`, with marker-based rescue and TERM-before-KILL) reached apollo's checkout
at 10:31 UTC on Sep 4 — after the last failure. Both researchers found zero post-fix
runs; the verification pass now finds **four finalizer runs completed since the fix
landed, all `success` with zero diagnostics**. A positive but modest signal: ~7 quiet
hours, and the rescue path has not yet been exercised in anger.

Three facts explain the failures and shape the fix:

1. **Seven of the nine failures happened *after* the commit had already landed.**
   stdout shows `✅ create_commit completed successfully!`, a repo-matching
   `commit_results.json` marker exists, and the checkpoint had completed through
   prompt-archive publication. The process was SIGKILLed during post-commit tail work
   (sidecar publication, COMMITS entry, bead close) and the old finalizer classified
   the whole agent as failed without consulting the marker. One of these was visibly
   stuck on `.git/index.lock` in the `agents` sidecar — which, unlike `beads`, `plans`,
   and `linked`, exists **once per project** and is shared by every concurrent agent on
   the host.
2. **The two real pre-commit timeouts died inside the before-commit hook.**
   `commit_hooks.before` is `just fix`, and `just fix` re-enters the full `_setup`
   bootstrap chain: a network fast-forward of the linked `sase-core` checkout, venv
   re-validation, PyPI plugin installs, possible `npm ci`/`go install`, and — whenever
   the fast-forward moves `sase-core` — **two full release cargo builds**
   (`sase_core_rs` and `sase_xprompt_lsp`, at `opt-level=3 lto=thin`). Measured live on
   an idle, already-bootstrapped 8-core/8 GiB M1: **`just fix` took 19m40s and changed
   zero files** — 3.3× the old cap and 65% of the new 1800s cap, in the hook alone,
   with no other agent competing. Under concurrency it will find whatever ceiling is
   set.
3. **Nothing inside `sase stitch create` is itself bounded.** `_run_commit_hook` calls
   `subprocess.run(..., shell=True)` with no `timeout=`
   (`src/sase/workflows/commit/command_hooks.py`), and ~153 of 202 `subprocess.*` call
   sites in `src/` pass no timeout (both facts re-verified on master). The finalizer's
   outer cap is the only bound in the whole process tree, so every slow step competes
   for one undifferentiated budget and `stitch_timeout` names the victim, never the
   culprit.

**Recommendation in one line:** deploy and trust the landed rescue as the floor, then
remove bootstrap and publication work from the commit-critical path, bound what remains
on *progress* rather than elapsed wall-clock, and resume — rather than merely excuse —
a killed stitch. Details in §5.

---

## 1. Incident evidence (merged)

All nine failures, correlated from `finalizer_result.json`, bounded-subprocess
inputs/stdout, `commit_state.json`, `commit_results.json`, and file mtimes on apollo.
Eight preserved both boundary timestamps and measured exactly 600–601 seconds of stitch
lifetime; agent wall-clock burned before the failure ranged from 15 minutes to nearly
two hours.

| Start (local) | Agent / artifact | Project | Where the stitch died | Classification |
| --- | --- | --- | --- | --- |
| Sep 3 09:22 | `sase-w0.1` / `…092208` | sase | after commit `f67169ea7` | false failure |
| Sep 3 14:18 | `sase-w2.2` / `…141823` | sase | after commit `e09a5f9ab`; `index.lock` in shared agents sidecar | false failure |
| Sep 3 14:26 | `sase-w3.2` / `…142629` | sase | inside `just fix`; no marker | real pre-commit timeout |
| Sep 3 14:52 | `c--code` / `…145239` | sase | after commit `d60eecd87` | false failure |
| Sep 3 15:50 | `sase-w3.1--code` / `…155000` | sase | after commit `8c3e7b6bf`, in publication | false failure |
| Sep 3 15:52 | `research.0.final` / `…155246` | research | after commit `a4333c690` | false failure |
| Sep 3 16:19 | `d--code` / `…161913` | bob-cli | after commit `92dfd5ebd` | false failure |
| Sep 3 17:46 | `bob-cli-1w.1` / `…174616` | bob-cli | after commit `d5747a3d7` | false failure |
| Sep 4 00:49 | `sase-w0.5--1` / `…004954` | sase | inside `just fix`; no marker | real pre-commit timeout |

The false failures are unambiguous: stdout reports commit success, the marker's `cwd`
matches the target repo, `commit_state.json` lists `dispatch` through
`publish_prompt_archive` as completed — and `finalizer_result.json` still says
`stitch_timeout`. The failed tracebacks point at the old unconditional raise, proving
those processes had imported pre-fix code. Two projects and two hook spellings
(`just fix`, `sase_git_fix`) show the same mode, because `sase_git_fix` just
`exec`s `just fix` — this is not sase-repo-specific.

**Environment during the incident window vs now.** The failures occurred while apollo
was on its ordinary 4-shared-vCPU/8 GB shape; a temporary resize means it now reports
16 vCPU/31 GiB (re-verified), so current capacity is not representative. Two
concurrency knobs both matter and are not in conflict: the SASE config default is
`max_running_agents: 10` (`src/sase/default_config.yml:38` — occupied runner slots),
while apollo's axe runs `--max-agent-runners 3` (live process cap, confirmed via `ps`).
The slot gate limits agent count, not the CPU/RAM each agent's children consume, and a
running agent keeps its slot through finalization.

**The contention feedback loop is still live.** Workspaces `#10` and `#16` are
confirmed (2026-09-04) still `PINNED` by the two dead failed runs
(`ace(run)-260903_145239`, `ace(run)-260904_004954`). Timeouts hold workspaces, held
workspaces shrink the pool, a starved pool makes the next run slower. On the build
side, each workspace carries its own cargo target tree (6.5 G / 5.8 G / 8.5 G on the
big ones — ~22 GB duplicated), so every workspace pays a cold release build instead of
sharing one warm cache.

---

## 2. The mechanism, end to end

1. The agent submits its final declaration; the host finalizer runs
   `sase stitch create -M <message-file>` via `run_bounded_subprocess`
   (`src/sase/finalizers/commit_repair.py:417`), bounded by
   `HARD_MAX_SUBPROCESS_TIMEOUT_SECONDS` (now 1800.0,
   `src/sase/finalizers/bounded_subprocess.py:17`).
2. The bounded runner is well-built for what it does: it starts the child in its own
   POSIX session, drains stdout/stderr incrementally on reader threads (no pipe-fill
   deadlock, bounded memory), and at the deadline escalates SIGTERM → 5s grace →
   SIGKILL against the whole process group.
3. Inside the child, `CommitWorkflow.run` runs the before-commit hook with **no
   timeout**, dispatches the commit, then runs tracking/publication tail work —
   patch creation, result markers, sidecar publication, COMMITS entry, bead close —
   all inside the same single outer budget.
4. On overrun the finalizer maps the bounds failure to `stitch_timeout`
   (`src/sase/finalizers/commit_dispatch.py:632`), which is deliberately **not** in
   `RETRYABLE_DIAGNOSTIC_CODES` (`src/sase/finalizers/ledger.py` — only
   `stitch_failed` retries). One timeout is terminal for the whole agent turn.

Both reports agree, and the code confirms: retry-blocking is *correct* — the first
attempt may have committed even though its process never returned, and a blind re-run
would re-pay the multi-minute hook and risk duplicate work. Recovery must go through
evidence (markers) or a checkpoint resume, never a fresh commit.

### Why the rebuild is structural, not an edge case

The compiled `sase_core_rs` extension lives inside the linked `sase-core` checkout
(editable `.pth` install). `_setup` fast-forwards that checkout over the network; a
fast-forward invalidates the built extension; the next `_setup` rebuilds it. Agent runs
routinely last 30–120 minutes, during which `sase-core` master moves — so the commit
hook, at the *end* of the run, is precisely where the rebuild is most likely to fire.
The cost lands on the slowest machines at the worst moment, and per-workspace target
dirs guarantee it is paid cold, N times.

One flagged anomaly, worth its own follow-up: the observed rebuild trigger was
`cannot import sase_core_rs: … partially initialized module` — a *failed import*, not
a version comparison. If that import can fail for reasons other than genuine staleness,
some of these rebuilds are pure waste, upstream of everything else here.

---

## 3. What `ad1da7fc2` already covers — and its two real gaps

The landed fix does three correct things: raises the cap 600s → 1800s, escalates
SIGTERM before SIGKILL (fewer stale `.git/index.lock` files), and rescues a bounds
failure when the current run produced a repo-matching commit marker — the rescued run
reports success with a `stitch_timeout_after_commit` warning, and the normal
clean-tree/hook reconciliation still runs so a marker alone cannot hide attributable
dirt. It directly prevents the seven observed false failures, is safe against duplicate
retry, and should not be reverted. As of this writing it has 4/4 post-fix successes on
apollo and zero new timeouts.

Two gaps remain, and they define the rest of the work:

- **Gap 1 — the ceiling is still a guess.** The measured hook alone is 19m40s idle and
  warm; under the incident-window shape and concurrency it will exceed any fixed
  number. Raising the cap also makes a genuinely wedged run three times more expensive
  to detect. A wall-clock ceiling penalizes exactly the machines the fix is supposed to
  protect.
- **Gap 2 — a rescued run is excused, not finished.** The SIGKILL still aborted
  whatever tail step was in flight; the run is now reported successful with sidecar
  publication, the COMMITS entry, or the bead close silently undone, and its workspace
  stays pinned. Two of the seven false failures had already printed explicit
  "publication deferred/skipped" warnings before the kill — the incompleteness is
  observed, not hypothetical.

One deployment mechanic matters everywhere: **updating files on disk does not update a
running Python process.** Apollo's six live runner processes started Sep 3 still hold
pre-fix code. Any fix is only deployed once ACE and long-lived agent runners have been
restarted (or drained).

---

## 4. Options considered and rejected

- **Raise the cap again / per-host timeout knob.** No — the hook cost is unbounded and
  machine-dependent; doubling a guess is not machine-independence, and per-host tuning
  makes correctness depend on fleet config drift. Keep 1800s only as a backstop.
- **Remove the timeout.** No — a lost child, lock cycle, or blocked prompt would hold
  an agent and workspace forever.
- **Make `stitch_timeout` retryable.** No — unsafe after dispatch (the commit may have
  landed); resume from a validated checkpoint is the only sound second attempt.
- **Drop the before-commit hook entirely.** No — commit-time formatting is
  load-bearing: bead/plan handling runs before the hook precisely so generated files
  get formatted, keeping `just check` green after landing.
- **Move the hook into the agent's own turn.** No — the agent cannot see the plan/bead
  files the host writes after the declaration, and it violates
  `decisions:host-owned-completion`.
- **More nested timeouts around unchanged synchronous publication.** Better
  diagnostics, same architecture; use stage bounds for required phases, but move
  optional publication off the critical path instead of timing it more precisely.

---

## 5. Recommended solution

The two reports converge on the same shape from different directions; their proposals
compose cleanly. In dependency order:

### Immediately (containment, this week)

1. **Require `ad1da7fc2`+ on every machine, then restart ACE and drain/restart any
   pre-update agent runner processes.** The fix does nothing for processes that
   imported old code. Release the workspaces still pinned by dead failed runs
   (`#10`, `#16` on apollo).
2. **On low-resource hosts, temporarily cap concurrency**: `max_running_agents` (and/or
   axe `--max-agent-runners`) to 1–2 and `CARGO_BUILD_JOBS=1–2`. These are containment
   measures, not the architecture.
3. **Baseline honestly.** Let a day of runs accumulate and re-measure the 36% rate;
   the ceiling raise plus rescue may already move it far, and that number sizes the
   remaining work. (First data point: 4/4 post-fix successes.)

### Structural fix 1 — take bootstrap off the commit hook (biggest win, lowest risk)

Point `commit_hooks.before` at a formatting-only recipe (e.g. `just fix-fast`) that
assumes a bootstrapped environment and does **not** depend on `_setup`: ruff
format/fix, prettier, keep-sorted — each guarded by "binary present, else skip with a
loud warning" rather than "install it now". A commit hook is the wrong place to acquire
a toolchain; agents already run `just install`/`just check` during their turn, so the
warm path is the normal path and the degraded path costs a warning in stitch stdout,
not a failed run. (The stricter variant — fail fast with a
`finalizer_environment_unprepared` diagnostic — is defensible; prefer warn-and-skip for
pure formatters so a missing prettier never voids a finished agent turn.)

This single change removes from every commit: a network `git fetch` of `sase-core`, a
venv validation pass, PyPI plugin installs, possible `npm ci` and `go install`, and the
possible full cargo release rebuild — the entire measured 19m40s worst case.

### Structural fix 2 — bound on progress, not only elapsed; name the phase

Extend `run_bounded_subprocess` with an **idle timeout** beside the total one: kill
when no output byte has arrived for N seconds, reported distinctly as `stitch_stalled`
vs `stitch_timeout`. (Verification note: the reader threads drain incrementally but do
not yet record chunk timestamps — a last-progress monotonic timestamp must be added in
the reader; it is a few lines.) This is the genuinely machine-independent bound: a
slow-but-progressing job on a weak host survives however long it needs, while a wedged
`git push` or `index.lock` spin emits nothing and dies fast with an accurate code.

Two provisos, both from the live measurement: this must land **after** fix 1, because
`rustc` under thin LTO went silent for 4+ minutes and would trip a tight idle bound;
and the idle bound should be sized against the quietest legitimate remaining step
(600s generous beats 300s clever — a merely-generous idle bound still strictly
dominates a total-elapsed bound because it does not charge a slow machine for being
slow). Pair it with a phase heartbeat: print a line at each workflow boundary
(`before_hook`, `dispatch`, `file_hooks`, `after_hook`, `publication`, `tracking`) and
persist per-stage start/duration in the timeout artifact, so a timeout names the exact
phase instead of requiring mtime archaeology. Follow up with a per-hook
`commit_hooks.timeout` key (new key — add to `src/sase/default_config.yml` and parse in
`_run_commit_hook`) and a default timeout in the shared `run_shell_command` helper; 153
untimed subprocess sites are a systemic hazard the commit path merely surfaced first.

### Structural fix 3 — finish, don't excuse: resume now, durable outbox next

Close Gap 2 in two stages:

- **Resume-on-timeout (small, uses existing machinery).** The workflow already
  checkpoints `completed_steps` to `commit_state.json`, `sase stitch create --resume`
  already skips completed steps, and `resume_runner` is already threaded into
  `dispatch_commit_decisions` (used today only for conflict repair). In the rescue
  path: if a live checkpoint lists `dispatch` complete, run the resume under a fresh
  bounded budget before deciding; on success record `stitch_timeout_resumed` and take
  the normal success path with the tail work actually done; on failure fall back to
  today's rescue exactly. The resume guard already fails closed when HEAD's subject
  does not match the checkpoint. Keep `stitch_timeout` non-retryable; resume is the
  only sanctioned second attempt.
- **Durable asynchronous publication (the end-state architecture).** Make the primary
  commit plus its verified marker the synchronous success boundary. Enqueue every
  derived projection — prompt archive, agent hood, plan-header refresh, COMMITS entry,
  bead close — into the existing durable outbox, keyed idempotently by (project, repo,
  commit SHA, operation), and let `sase agent sync` or a supervised worker drain it
  off the commit call stack. If an enqueue is interrupted, a reconciler re-derives
  missing work from the commit marker. This is the transactional-outbox pattern, and
  SASE already has most of the mechanism; the missing step is to stop draining it
  synchronously inside the committing process. Once this lands, resume-on-timeout
  shrinks to a rarely-used safety net and the commit-critical section becomes small
  and predictable on any machine.

### Structural fix 4 — reduce contention (follow-ups, in impact order)

1. **One build, reused everywhere.** Best: provision a `sase-core-rs` wheel keyed by
   source revision + Python ABI + OS/arch and install it into workspaces via the
   existing `SASE_CORE_WHEEL` seam, so finalization *never* invokes cargo. Cheaper
   interim: a shared `CARGO_TARGET_DIR` across workspaces (turns N cold builds into
   one and reclaims ~22 GB on apollo) plus a host-derived `CARGO_BUILD_JOBS`.
2. **Serialize the finalizer critical section.** A host-wide FIFO lane (crash-releasing
   OS lock) with default concurrency 1, acquired *before* the stitch clock starts;
   waiting is visible as `queued_for_finalizer`, not spent budget. On small machines
   this converts contention into orderly queueing — the key "works on weak hardware"
   property. Keep an override for measured high-capacity hosts.
3. **Give the shared per-project `agents` sidecar a real bounded lock** instead of
   racing for `.git/index.lock` and deferring; one clone serving N agents is a designed
   serialization point and should behave like one. Use `GIT_OPTIONAL_LOCKS=0` for
   background read-only git scans.
4. **Auto-release workspaces held by rescued or dead runs** — breaking the observed
   feedback loop — and record the SASE code revision in `agent_meta.json`/timeout
   artifacts so operators can see which running agents predate a fix.

### Verification

- Unit: idle-watchdog behavior (slow-printer survives past total budget; print-once
  -then-sleep child killed at idle bound with `stalled=True`).
- Extend `tests/test_commit_dispatch_stitch_timeout_rescue.py`: timeout + checkpoint
  with `dispatch` completed → resumed success-with-warning; timeout without checkpoint
  → unchanged `stitch_timeout`.
- Stress: concurrent finalizers against shared sidecars with injected slow hook,
  blocked publication, index-lock contention, SIGTERM-ignoring child, crash between
  commit and enqueue, and a 1-CPU/low-memory profile. Assert: no duplicate commits, no
  orphaned process groups, no failed status after a verified commit, eventual outbox
  convergence.
- Field: compare `just fix` vs `fix-fast` cold and warm on apollo and an 8-core Mac
  (target: small constant, never builds), and re-measure the timeout rate after each
  stage lands.

---

## Bottom line

`stitch_timeout` was one opaque wall-clock timer wrapped around four unrelated jobs:
environment bootstrap, native compilation, the commit itself, and shared-sidecar
publication — evaluated on machines whose speed varies 10×. Seven of nine failures
threw away agent turns whose commits had already landed; the other two spent their
entire budget bootstrapping. The landed rescue (`ad1da7fc2`) correctly stops the
false failures and is already 4-for-4 in production — deploy it everywhere and restart
long-lived processes. The durable fix is to shrink the commit-critical section until
the timer barely matters: formatting-only hook, prebuilt core extension, publication in
a durable idempotent queue, finalizers serialized per host, and the remaining bound
keyed to progress (idle detection + phase heartbeats) rather than to a wall-clock guess
that penalizes slow machines. A one-core box then queues and finishes instead of
failing completed work.
