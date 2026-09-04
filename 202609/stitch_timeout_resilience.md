---
create_time: 2026-09-04
updated_time: 2026-09-04
status: research
---

# Making `sase stitch create` Survive Slow Hosts: Ending `stitch_timeout` Agent Failures

**Research question:** SASE agents on **apollo** keep dying with
`LLMInvocationError: Error: sase stitch create stitch_timeout for <repo>`. What is
actually consuming the budget, and what is the most reliable, robust fix — one that
holds on low-resource machines, not just on a fast box?

**Scope:** sase at master `719275bc8`; apollo's checkout at
`/home/bryan/projects/github/sase-org/sase` (16 vCPU, 31 GiB, load ~5.5–6.1 at probe
time). Evidence is from apollo's own run artifacts under
`~/.sase/projects/*/artifacts/ace-run/`, apollo's `git reflog`, apollo's workspace
registry and on-disk cargo trees, plus the finalizer/commit sources in this repo and a
live `just fix` timing run on an M1 Mac (8 cores, 8 GiB). Prior art: the accepted plan
`plan:202609/stitch_timeout_false_failures.md`, landed as `ad1da7fc2`.

---

## Executive Summary

**Nine of the twenty-five commit-finalizer runs on apollo (36%) failed with
`stitch_timeout`.** Every one of them ran under the *old* 600-second cap: the mitigation
that raises it to 1800s landed in apollo's checkout at `2026-09-04 10:31 UTC`, and at
the time of this research **zero runs had executed with it**. So the first honest
finding is that the recent fix is untested in production, not that it failed.

The second finding is that the recent fix is a **ceiling raise, not a cure**. The budget
is being spent on work that has no business being on the commit critical path:

- `commit_hooks.before` is `just fix` (`sase/sase.yml:1-2`), and `just fix` re-enters the
  full `_setup` chain (`Justfile:352-377`, `Justfile:78`). That chain fast-forwards the
  linked `sase-core` checkout over the network, re-resolves the venv, re-installs
  required plugins from PyPI, can run `npm ci`, and — whenever the fast-forward moves
  `sase-core` — **rebuilds the `sase_core_rs` PyO3 extension from scratch with cargo.**
- A live measurement on a clean, previously-bootstrapped 8-core/8 GiB workspace with a
  clean tree: `just fix` printed `[setup] Rebuilding stale or missing sase_core_rs …`
  and took **19 minutes 40 seconds** — **3.3× the old 600s cap and 65% of the new 1800s
  cap, in the hook alone**, on a machine running nothing else. It changed zero files.
  That is the commit hook, inside a fixed wall-clock budget, on the critical path of
  "did the agent's turn succeed".
- Nothing inside `sase stitch create` is itself bounded: `_run_commit_hook` calls
  `subprocess.run(..., shell=True, capture_output=True)` with **no `timeout=`**
  (`src/sase/workflows/commit/command_hooks.py:25-27`), and 153 of 202 `subprocess.*`
  call sites in `src/` pass no timeout at all. The finalizer's outer bound is the only
  bound in the entire process tree, so every slow step competes for one undifferentiated
  budget and every failure is reported with one undifferentiated code.

The third finding is where the time actually goes. Of the nine failures, **seven had
already printed `✅ create_commit completed successfully!`** — the commit landed and the
process was killed doing post-commit tail work (sidecar publication, COMMITS entry, bead
close). Only two died inside `just fix`. One of the seven was visibly stuck on
`.git/index.lock` contention in the **shared, host-level agents sidecar** that every
concurrent agent on the machine writes to.

**Recommendation (detail in §6): three changes, in this order.**

1. **Take bootstrap off the commit hook.** Point `commit_hooks.before` at a
   formatting-only recipe that does not re-enter `_setup`. This removes cargo builds,
   PyPI installs, `npm ci`, and a network `git fetch` from the budget — the single
   largest and most machine-dependent cost.
2. **Replace the fixed wall-clock cap with an idle-progress watchdog.**
   `run_bounded_subprocess` already drains stdout/stderr incrementally, so it can kill
   on *time since last output* in addition to a generous total ceiling. This is the one
   bound that is genuinely machine-independent: a slow-but-progressing job on a weak
   host survives however long it needs; a wedged `git push` or an `index.lock` spin
   emits nothing and dies quickly with an accurate diagnostic. It must land *after* (1),
   because a silent `rustc` under LTO can go quiet for four minutes (§6.2).
3. **Make a post-dispatch timeout resumable instead of terminal.** The commit workflow
   already checkpoints `completed_steps` to `$SASE_ARTIFACTS_DIR/commit_state.json`
   (`src/sase/workflows/commit/checkpoint.py:41-55`), and `resume_runner` is already
   threaded into the dispatch path. On a timeout with a live checkpoint, run `sase stitch
   create --resume` under a fresh budget before declaring failure.

Together these convert the dominant failure mode from "the agent run failed after 1h59m"
into "the commit landed and the tail work finished on resume", and they do it without
picking a magic wall-clock number per host.

---

## 1. The Failures, Measured

### 1.1 Incidence

Across every `ace-run` artifact directory on apollo:

| Metric | Value |
| --- | --- |
| Finalizer runs with a `finalizer_result.json` | 25 |
| Runs whose finalizer reported a `*timeout` diagnostic | **9 (36%)** |
| Runs executed since the 1800s mitigation landed | **0** |

The nine failures, with the wall-clock the *agent* burned before being thrown away:

| Artifact timestamp | Project | Agent duration | Where the stitch died |
| --- | --- | --- | --- |
| `20260903092208` | sase | 42m21s | after `create_commit` succeeded |
| `20260903141823` | sase | 1h16m50s | after `create_commit`; `index.lock` in shared agents sidecar |
| `20260903142629` | sase | 34m18s | inside `just fix` |
| `20260903145239` | sase | 1h59m16s | after `create_commit` succeeded |
| `20260903155000` | sase | — | after `create_commit`, in publication |
| `20260903155246` | sase | 39m30s | after `create_commit` succeeded |
| `20260903161913` | bob-cli | 14m54s | after `create_commit` succeeded |
| `20260903174616` | bob-cli | 1h39m3s | after `create_commit` succeeded |
| `20260904004954` | sase | 17m38s | inside `just fix` |

Two projects, two different hook spellings (`just fix` and `sase_git_fix`), one failure
mode — because `sase_git_fix` is just a dispatcher that `exec just fix`
(`src/sase/scripts/sase_git_fix:13-15`). This is not a sase-repo-specific problem.

### 1.2 Every failure ran the old 600s cap

`HARD_MAX_SUBPROCESS_TIMEOUT_SECONDS` was raised from `600.0` to `1800.0` in
`ad1da7fc2` (committed `2026-09-03 16:42 EDT`). Apollo's reflog shows the checkout moved
to a revision containing it only at `2026-09-04 10:31 UTC`; `git merge-base
--is-ancestor ad1da7fc2 9e2d95bb0` is false for the revision apollo ran during the last
failure. The observed subprocess lifetimes corroborate it exactly — for
`20260904004954`, `final_context.json` was written at `04:57:32 UTC` and the stitch
artifacts at `05:07:34 UTC`: **10m02s ≈ 600s**.

So: the fix has not yet had a chance to work. Everything below is about why raising the
ceiling is necessary but not sufficient.

### 1.3 Where the budget went

The captured stitch stdout is the whole story. For `20260904004954` it is one line:

```
🔄 Running before commit hook: just fix
```

600 seconds, entirely inside the hook, no commit. For six others it reads:

```
🔄 Running before commit hook: just fix
🔄 Dispatching create_commit to VCS provider...
✅ create_commit completed successfully!
```

— the commit landed, and the kill arrived during `_run_tracking_steps`
(`src/sase/workflows/commit/workflow.py:290`): patch creation, result markers, sidecar
publication, the COMMITS entry, delta refresh, bead close. One run
(`20260903155000`) additionally warned that prompt-archive publication was skipped, and
one (`20260903141823`) ended on:

```
⚠️ The primary commit succeeded, but prompt archive publication was deferred and
will retry with agent publication: could not reset prompt archive index: fatal:
Unable to create
'/home/bryan/.sase/projects/gh_sase-org__sase/repos/agents/.git/index.lock':
File exists.
```

Note the path. Unlike `beads`, `plans`, and `linked`, which are materialized *per
workspace*, the `agents` sidecar exists **once per project** at
`~/.sase/projects/<project>/repos/agents` — verified on apollo, where every
`sase_1*` workspace carries `beads linked plans` and none carries `agents`. Every
concurrent agent on the host therefore serializes on that one clone's index during
post-commit publication, inside the same budget that the commit hook has already
largely spent.

---

## 2. The Mechanism, End To End

1. The agent submits its final declaration. The host-owned commit finalizer runs
   `sase stitch create -M <message-file>` as a bounded subprocess
   (`src/sase/finalizers/commit_repair.py:404-427`), passing
   `HARD_MAX_SUBPROCESS_TIMEOUT_SECONDS` directly as the timeout.
2. `run_bounded_subprocess` starts the child in its own session, drains both pipes on
   reader threads, and at the deadline sets `timed_out=True` and escalates
   SIGTERM → SIGKILL to the whole process group
   (`src/sase/finalizers/bounded_subprocess.py:128-160`).
3. Inside that child, `CommitWorkflow.run` calls `run_before_commit_hook(cwd)`
   (`workflow.py:160`) → `_run_commit_hook` → `subprocess.run(cmd, shell=True, …)` with
   **no timeout** (`command_hooks.py:25-27`). `just fix` runs here.
4. `just fix` = `fmt-py fmt-docs fmt-md fix-keep-sorted` (`Justfile:352`). `fmt-py` and
   `fmt-docs` both depend on `_setup` (`Justfile:358`, `:370`), and `_setup`
   (`Justfile:78-98`) runs `_refresh-sase-core-checkout` — a network `git fetch` +
   fast-forward of the linked `sase-core` clone (`Justfile:834-841`,
   `tools/refresh_linked_checkout`) — then validates the environment, re-installs
   required plugins from PyPI (`tools/setup_required_plugins`), and rebuilds
   `sase_core_rs` when the extension no longer matches the checkout. `fmt-md` runs
   `npm ci` when `node_modules` is missing (`Justfile:142-146`); `fix-keep-sorted` can
   `go install` keep-sorted (`Justfile:126-138`).
5. If any of that overruns, the finalizer sees `stitch.timed_out`,
   `_stitch_bounds_failure_code` returns `stitch_timeout`
   (`src/sase/finalizers/commit_dispatch.py:630-636`), and the run fails.
   `stitch_timeout` is deliberately **not** in `RETRYABLE_DIAGNOSTIC_CODES`
   (`src/sase/finalizers/ledger.py:17-25`), so one timeout is terminal for the entire
   agent turn.

### 2.1 Why the rebuild is structural, not an edge case

Each ephemeral workspace has its **own** `sase-core` clone and its **own** cargo target
directory, and `sase_core_rs` is installed as an editable pointer into that clone. In
this workspace:

```
.venv/lib/python3.12/site-packages/sase_core_rs.pth
  → …/sase_14/sase/repos/linked/sase-core/crates/sase_core_py/python
```

So the compiled extension lives inside the linked checkout. `_setup` fast-forwards that
checkout; a fast-forward invalidates the built extension; the next `_setup` rebuilds it.
Agent runs routinely last 30–120 minutes, during which `sase-core` master moves — so the
*commit hook* is precisely where the rebuild is most likely to be triggered.

There is no shared build cache. Measured on apollo:

| Workspace | `sase-core/target` |
| --- | --- |
| `sase_13` | 6.5 G |
| `sase_14` | 5.8 G |
| `sase_15` | 8.5 G |
| `sase_10` | 945 M |
| `sase_16` | 727 M |
| `sase_11` | 377 M |

That is ~22 GB of duplicated Rust artifacts and, more importantly, N cold builds instead
of one warm one.

### 2.2 A live timing

On an M1 Mac (8 cores, 8 GiB) — a fair proxy for "a machine with few resources" — `just
fix` in a clean, already-bootstrapped workspace with a clean tree printed:

```
[validate_sase_core_rs] cannot import sase_core_rs: cannot import name 'sase_core_rs'
  from partially initialized module 'sase_core_rs' (most likely due to a circular import)
[setup] Rebuilding stale or missing sase_core_rs from …/sase/repos/linked/sase-core
  before Python dependency resolution.
🍹 Building a mixed python/rust project
```

and then compiled 70+ crates. It is not one build but **two release builds**: the PyO3
extension, then `cargo build --release -p sase_xprompt_lsp` — both at `-C opt-level=3
-C lto=thin -C codegen-units=1`, the slowest profile cargo has. Load average peaked past
**25** on an 8-core box. Final result:

```
just fix  893.29s user 156.58s system 88% cpu 19:40.29 total
```

**19m40s.** The formatting it exists to do ran at the very end, reported every file as
`(unchanged)`, and `git status` was empty afterwards. Essentially 100% of that budget
was environment bootstrap.

Put against the caps: **3.3× the old 600-second cap**, and **65% of the new
1800-second cap** — on an idle machine, in a warm workspace, with no other agent
competing for CPU, disk, or the shared `uv`/`cargo` caches. Apollo runs up to three
agent runners concurrently. The conclusion is unavoidable: **raising the ceiling to
1800s does not make this safe; it only moves where the cliff is.**

Note the first line: the staleness verdict came from a *failed import*, not from a
version comparison. Whether that particular import failure is itself a bug (the linked
checkout's pure-Python shim shadowing the built extension) deserves its own look; it is
called out as a follow-up in §8 rather than assumed here.

---

## 3. Root Causes

**R1 — Bootstrap work is on the commit critical path.** The commit hook re-enters the
full environment setup, including a network fetch and a native build. Its cost is
unbounded, machine-dependent, and correlated with exactly the thing that makes it slow
(a busy host running many agents).

**R2 — The process tree has exactly one bound, at the outermost layer.**
`_run_commit_hook` has no timeout; `run_shell_command` (`src/sase/core/shell.py:25-34`),
the shared helper, has no timeout; 153 of 202 `subprocess.*` call sites in `src/` have
no timeout. Every internal step therefore inherits the finalizer's whole budget and
reports the same code when it overruns. `stitch_timeout` names the *victim*, never the
*culprit*.

**R3 — A timeout is terminal, even though the work is checkpointed.** The commit
workflow persists a `CommitCheckpoint` with `completed_steps` to
`$SASE_ARTIFACTS_DIR/commit_state.json` before dispatch (`workflow.py:243-244`,
`checkpoint.py:41-55`), and `sase stitch create --resume` skips completed steps.
`resume_runner` is already a parameter of `dispatch_commit_decisions` — used only for
conflict repair. Nothing consults it on a timeout.

**R4 — The current rescue can mask a partial commit.**
`_rescue_landed_commit_after_bounds_failure` (`commit_dispatch.py:638-690`) downgrades a
timeout to a warning when a `commit_results.json` marker exists. That is right for the
run's *status*, but the SIGKILL still aborted whatever tail step was in flight — sidecar
publication, the COMMITS entry, the bead close. The run is now reported successful with
that work silently undone. All seven post-commit failures were killed with tail work in
flight, and two of them (`20260903155000`, `20260903141823`) had already printed an
explicit "prompt archive publication was skipped / deferred" warning before the kill —
i.e. the incompleteness is not hypothetical.

**R5 — Contention amplifies all of the above.** Per-workspace cargo targets defeat build
caching; `uv`, `npm`, and `cargo` caches are shared and lock-contended; and the `agents`
sidecar is a single host-level clone that every concurrent agent mutates during
post-commit publication, which is where the observed `.git/index.lock` collision
happened. And each failure *holds* its workspace ("Workspace #10 held (visible failed
run)"), shrinking the pool and raising contention for the next run — a feedback loop.

---

## 4. What `ad1da7fc2` Already Covers

The landed plan did three things, all correct:

| Change | Covers | Does not cover |
| --- | --- | --- |
| `600s → 1800s` | Slow-but-finite hooks on medium hosts | Measured: the hook alone is 19m40s on an idle 8-core box — 65% of the new cap before the commit starts. Under concurrency it will still blow through. The number remains a per-host guess |
| SIGTERM before SIGKILL (5s grace) | Leftover `.git/index.lock` after a kill | The contention that created the lock in the first place |
| Rescue when a commit marker exists | The 6/9 post-commit cases — status now `success` with a `stitch_timeout_after_commit` warning | The 2/9 pre-commit cases (no marker → still terminal); and the tail work the kill aborted (R4) |

It is a good floor. The remaining work is to stop spending the budget on the wrong
things, to bound the pieces individually, and to finish rather than merely excuse a
killed stitch.

---

## 5. Options Considered

| Option | Verdict |
| --- | --- |
| Raise the cap again (1800s → 3600s) | **No.** The measured hook is 19m40s *idle and warm*; under concurrency it will find whatever ceiling you set. Doubling a guess does not make it machine-independent, and it doubles the worst-case cost of a genuinely wedged run. |
| Per-host timeout config knob | **Not on its own.** The prior plan deferred this for good reason: it makes every new machine a tuning exercise, which is the opposite of "works well on all machines". Useful only as an escape hatch on top of a progress-based bound. |
| Drop the before-commit hook entirely | **No.** Formatting at commit time is load-bearing: it is what keeps `just check` green after plan files and bead edits land (`workflow.py:151-157` runs bead/plan handling *before* the hook precisely so generated files get formatted). |
| Make `stitch_timeout` retryable | **No, not as a blind re-run.** Re-running `sase stitch create` re-runs the multi-minute hook and, when nothing landed, usually times out again. Retry is only sound through `--resume`. |
| Move the hook into the agent's own turn (agent runs `just fix` before declaring) | **Tempting, rejected.** It cannot see the plan/bead files the host writes after the declaration, and it puts host-owned work back in the agent's hands, against `decisions:host-owned-completion`. |
| **Slim the hook + idle watchdog + resume-on-timeout** | **Yes** — §6. |

---

## 6. Recommendation

Three changes, in dependency order. **(1) and (2) are the fix; (3) is what makes the
remaining failures cheap.** (4)–(5) are worthwhile follow-ups, not prerequisites.

### 6.1 Take bootstrap off the commit hook (largest win, lowest risk)

Add a formatting-only recipe that assumes a bootstrapped venv and does **not** depend on
`_setup`:

```just
# Format only. No environment bootstrap, no network, no native build.
# Used by commit_hooks.before, where the venv is already warm.
fix-fast: (_header "fix-fast")
    {{ venv_bin }}/ruff format src/ tests/
    {{ venv_bin }}/ruff check --fix src/ tests/
    {{ venv_bin }}/python tools/render_model_alias_docs
    …prettier + keep-sorted, each guarded by "binary present, else skip with a warning"…
```

and point the hook at it in `sase/sase.yml`:

```yaml
commit_hooks:
  before: "just fix-fast"
```

Guard each tool on "already installed, else skip and warn" rather than "install it now" —
a commit hook is the wrong place to acquire a toolchain. Agents already run `just
install` and `just check` during their turn, so the warm path is the normal path; the
degraded path costs a warning in the stitch stdout, not a failed run.

This alone removes, from every commit: a network `git fetch` of `sase-core`, a
`uv sync`/validation pass, PyPI plugin installs, a possible `npm ci`, a possible
`go install`, and — the big one — a possible full cargo rebuild.

### 6.2 Bound on *progress*, not only on total elapsed

Extend `run_bounded_subprocess` with an idle deadline alongside the total one. The
reader threads already timestamp every chunk they receive, so this is a small change:

- `idle_timeout` (default ~300s): kill when no byte has arrived on stdout **or** stderr
  for that long.
- `timeout` (total) stays as a backstop, raised generously (1800s is fine, and could go
  higher once idle-kill exists because it is no longer the thing that fires).
- Report the two cases distinctly: `stitch_stalled` vs `stitch_timeout`.

Why this is the machine-independent bound: a job that is genuinely working emits output
and survives however long it needs; a `git push` blocked on a dead TLS connection, or a
loop spinning on `index.lock`, emits nothing and dies quickly with a diagnostic that
names the real problem. No per-host tuning, and the weak-machine case gets *more*
headroom, not less.

**One caveat, and it is why 6.1 must land first.** "Progressing" is not the same as
"printing". During the M1 measurement, cargo went **silent for over four minutes**
while a single `rustc` compiled `sase_core` under thin LTO — the captured tail did not
move between the 3m40s and 7m30s probes. So a 300s idle bound would kill a legitimate
build. Two consequences:

- Order matters. Do 6.1 first so the hook never builds; only then is a tight idle bound
  safe.
- Size the idle bound against the *quietest legitimate step that remains*, and prefer
  raising it to 600s over being clever. An idle bound that is merely generous still
  strictly dominates a total-elapsed bound, because it does not charge a slow machine
  for being slow.

Pair it with a heartbeat: have the commit workflow print a phase line at each boundary
(`before_hook`, `dispatch`, `file_hooks`, `after_hook`, `publication`, `tracking`). The
captured stdout then says exactly where the budget went — reconstructing this run
required correlating file mtimes.

### 6.3 Resume instead of failing when a checkpoint exists

In `_rescue_landed_commit_after_bounds_failure`, before deciding anything:

1. Load `$SASE_ARTIFACTS_DIR/commit_state.json`. If it exists and lists `dispatch` in
   `completed_steps`, call the already-available `resume_runner(repo, context)` under a
   fresh bounded budget.
2. Re-check `new_commit_markers(...)`. If the resume completed, record a warning
   (`stitch_timeout_resumed`) and continue down the normal success path — with the tail
   work actually done, closing the R4 gap.
3. If the resume also times out or fails, fall back to today's behaviour exactly.
4. Keep `stitch_timeout` out of `RETRYABLE_DIAGNOSTIC_CODES`. Retry remains blocked; the
   resume path is the only sanctioned second attempt, and it is idempotent by
   construction.

`resume_commit_workflow` already refuses to run when HEAD's subject does not match the
checkpoint (`workflow_resume.py:63-77`), so a stale or foreign checkpoint fails closed.

### 6.4 Bound each hook individually (follow-up)

Give `commit_hooks` its own timeout, enforced with the same process-group semantics:

```yaml
commit_hooks:
  before: "just fix-fast"
  timeout: "5m"
```

`commit_hooks` currently declares only `before` and `after`
(`src/sase/default_config.yml:9-11`), so this is a new key and must be added there as
well as parsed in `_run_commit_hook`. Then a slow hook fails as `before_hook_timeout`
with its own output tail, leaving the rest of the budget for the commit — instead of consuming everything and reporting
`stitch_timeout`. More broadly, `run_shell_command` (`src/sase/core/shell.py:25`) should
grow a default timeout; 153 untimed `subprocess.*` call sites is a systemic hazard, and
the commit path is simply where it surfaced first.

### 6.5 Reduce contention (follow-up)

- **Share one cargo target directory** across workspaces
  (`CARGO_TARGET_DIR=~/.cache/sase/cargo-target/sase-core`). Turns N cold builds into
  one, and reclaims ~22 GB on apollo.
- **Serialize commit-time hooks per repo** with an advisory lock, so N concurrent agents
  do not run N formatters against N clones of the same tree at once.
- **Give the shared `agents` sidecar a real lock with a bounded wait**, rather than
  letting concurrent publications race for `.git/index.lock` and fall back to
  "deferred, will retry". One clone per project serving N agents is a designed
  serialization point; it should behave like one.
- **Release the workspace on a rescued run.** A run whose commit landed should not hold
  a workspace pending manual dismissal; that is the feedback loop in R5.

---

## 7. How To Verify

1. **Baseline, honestly.** Apollo has run zero finalizers since the 1800s fix landed.
   Before changing anything else, let a day of runs go by and re-measure the 36% rate —
   the ceiling raise plus the rescue may already move it a long way, and that number
   sizes the rest of the work.
2. **Hook cost.** Time `just fix` vs `just fix-fast` in a cold workspace and in a warm
   one, on both apollo and the 8-core Mac. Target: the hook is a small constant, and
   *never* triggers a build.
3. **Idle watchdog.** Unit-test `run_bounded_subprocess` with (a) a child that prints
   slowly for longer than `idle_timeout` — must survive; (b) a child that prints once and
   then sleeps — must be killed at `idle_timeout` with `stalled=True`.
4. **Resume path.** Extend the fixtures in
   `tests/test_commit_dispatch_stitch_timeout_rescue.py`: a timeout with a checkpoint at
   `completed_steps=["dispatch"]` resumes and reports success-with-warning; a timeout with
   no checkpoint still raises `stitch_timeout`.
5. **Regression watch.** `just check` for the Python changes; the finalizer live-e2e
   cycles (`tests/test_finalizers_live_e2e_cycles.py`) for the dispatch wiring.

---

## 8. Open Questions And Follow-Ups

- **Is the `sase_core_rs` staleness verdict itself wrong?** The rebuild in §2.2 was
  triggered by `cannot import sase_core_rs: … partially initialized module … circular
  import`, not by a version mismatch — the `.pth` points into the linked checkout, whose
  pure-Python shim needs the compiled artifact beside it. If that import can fail for
  reasons other than genuine staleness, some fraction of these rebuilds are pure waste.
  Worth a dedicated look; it is upstream of everything in §6.1.
- **Runner admission and the held-workspace loop.** apollo's axe runs with
  `--max-agent-runners 3`. At probe time the sase project file listed nine `RUNNING`
  entries and seven live `run_agent_runner.py` processes: six queued at workspace `#0`,
  one holding `#11`, and **two entries whose processes were already dead but whose
  workspaces `#10` and `#16` were still `PINNED`** — both of them `stitch_timeout`
  failures from this incident. That is the R5 feedback loop, visible in the live state:
  timeouts hold workspaces, held workspaces starve the pool, a starved pool makes the
  next hook slower. Confirm queued runners cannot reach the commit hook concurrently,
  and auto-release workspaces held by a rescued run.
- **Should `commit_hooks` be repo-relative at all?** Every project on the host resolves
  to the same `just fix` through `sase_git_fix`. A per-project declaration of "the cheap
  formatter" would make the cost explicit rather than incidental.
