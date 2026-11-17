# SASE routines: what they do, what they are good for, and how they differ

**Date:** 2026-11-17
**Question:** What can sase's routines do, what is each capability good for, and what makes them different from other agent harnesses?
**Snapshot:** sase `master` at `e6ee9fd446`, with the default config and docs at that commit. Competitor claims come from this repo's blog posts and its October 2026 comparison reports, not from a fresh check of those products.

---

## Bottom line

- A **routine** is a supervised scheduler lane. You declare it under `axe.routines.<name>` with an `interval`, and it runs its **jobs** on that cadence. A routine is the process unit. A job is one script-only unit inside it.
- The core design choice is that **cheap scripts sense and the runner acts.** A job is an external executable that checks state and returns a structured JSON result. It can propose agent launches, but it never launches anything itself. The runner validates each proposal and launches it only after triggers, guards, dedupe, and capacity limits have all been applied. Most ticks spend no model tokens.
- Routines are the background engine for SASE's agent lifecycle, not only for user-defined recurring tasks. They advance hooks, mentors, CRS and fix-hook workflows, `%wait` dependencies, comment polling, PR-submitted checks, bead triage gates, and housekeeping.
- The main gap is the trigger model. Routines support intervals, file-state changes, and commit counts. They do not support wall-clock schedules, webhooks, or event triggers, and a job cannot start a standalone workflow. Gas City's "orders" cover those cases.

---

## The vocabulary

| Term | What it is |
| --- | --- |
| **Orchestrator** | The parent process that the scheduler runs. It spawns every routine, restarts crashed ones with bounded backoff, and forwards `SIGTERM` on shutdown. |
| **Routine** (legacy name: lumberjack) | An independent process on a fixed `interval`. Each routine keeps its own status, metrics, logs, and run history under `~/.sase/axe/lumberjacks/<name>/`. |
| **Job** (legacy name: chop) | One executable run as `<script> --context <json>`. It has its own cadence, trigger, guards, timeout, and dedupe policy. |
| **Proposal** | A launch request in a job's result file. Each proposal carries a prompt, a workspace, and optional waits, clans, tribes, and dedupe keys. |
| **Service host / scheduler proc** | The platform-supervised layer. The service host (`sase service run`) keeps the scheduler proc alive, and the scheduler owns the routine tree below it. |

The `sase_job_*` script names are the current spelling. `sase_chop_*` names still resolve. The CLI accepts `sase axe routine` and `sase axe job`, plus hidden `lumberjack` and `chop` aliases.

---

## The default routines

These come from `axe.routines` in `src/sase/default_config.yml`. The config defines **ten** routines. The default-routines page in the docs says nine, so that page is stale.

| Routine | Interval | What it owns |
| --- | --- | --- |
| `hooks` | 5 s | Hook completion and starts, mentors once prerequisites pass, CRS and fix-hook workflows, background check polling, zombie marking, suffix repair, orphan and dead-process cleanup. Per-job timeout 90 s. |
| `waits` | 10 s | Bead-claim reconciliation, epic launch flushing, agent auto-restart sweeps. |
| `agent_waits` | 2 s | `wait_checks`: resolves `%wait` dependencies and writes `ready.json`. Kept in its own lane so a slow sync cannot delay it. |
| `sidecar_sync` | 30 s | Fetches and fast-forwards opted-in sidecar clones (plans, beads). |
| `publication` | 15 s | Drains queued hood, artifact-link, and Referenced-By work. It wakes on a filesystem doorbell and also runs on a five-minute backstop. |
| `checks` | 5 min | Bead task triage gates, required-plugin gates, PR-submitted checks, backstop cleanup, orphaned agent-scope reaping. |
| `usage` | 60 s | Due-only refresh of subscription-usage windows, with no per-agent polling. |
| `external_mirror` | 15 min | Polls remote trackers (`external_pr_mirror`, `external_issue_mirror`) in isolation. |
| `comments` | 1 min | Polls review comments and launches critique agents. |
| `housekeeping` | 1 h | Error digests, Footprint folding, notification compaction, managed temp reaping, proc runtime sweeps, disk-pressure response, stale bead cleanup, gate-turn reclaim, staged-handoff reconciliation, artifact link backfill, retention, and run pruning. |

---

## The capabilities, one at a time

### 1. Script jobs that return structured launch proposals

A script exits zero for success, or writes a schema-versioned JSON result to `SASE_JOB_RESULT_FILE`. The result has a `status` of `ok`, `no_op`, or `check_error`, plus counters and evidence paths. A `proposed_launches` list can request agents. Each proposal requires `prompt` and `workspace`. Optional fields include `id`, `wait_on`, `clan`, `agent_name`, `tribe`, `model`, `effort`, `env`, and `dedupe_key`.

**Good for:** detection work that sometimes needs an agent. A script can run every few seconds for almost nothing, and it spends tokens only when it finds something to act on.

**Example:** the built-in `refresh_docs` job fans out over enabled projects and proposes an `update` agent, then a `polish` agent that waits on it.

### 2. Triggers that decide when a job is even considered

- **`always`** (default): run on every cadence tick.
- **`fs`**: compute a cheap token from the stat data and glob matches of watched paths, such as `projects/*/*.sase`. The job fires when the token changes. A `max_quiet` heartbeat guarantees a fire after a quiet period. The default Patch-lifecycle jobs use this, so an idle tick costs a few `stat()` calls rather than a subprocess spawn.
- **`git.commits_since`**: fire after a threshold number of commits in a project. It keeps its own checkpoint, and a missing checkpoint fires once so a new job is not silently inert.

Checkpoints advance on one of three policies: `on_observation`, `on_action_accepted`, or `on_action_success`. The last one advances only after every linked proposal agent succeeds.

**Good for:** reacting to changes in state, not to the clock. A "run a deeper audit after ten new commits, at most once every 90 minutes" rule is one YAML block.

### 3. Guards that inhibit a job while other work is in flight

`inhibit_if` supports four guard kinds: `patch` (the old name `changespec` still works), `agent_hood`, `agent_clan` (matched by name prefix), and `agent_runners` (inhibits while more than N participating lanes are occupied). A guard skip is recorded as a visible `skipped` run that names the guard and the agent it matched. It does not consume the job's cadence, so the job is re-checked on the next tick.

**Good for:** avoiding conflicts. For example, a repository-wide check can wait while a large refactor clan is running.

### 4. Cadence and fan-out per project

`run_every` sets a per-instance cadence. `for_each: source: projects` (with optional `vcs`, `name`, or `names` filters) expands one job into stable instances such as `refresh_docs[sase-core]`. Each instance has its own cadence, run history, checkpoints, and dedupe state. Targets can override fields such as `run_every` and trigger thresholds.

**Good for:** writing one script and running it across many repos with different schedules and independent state.

### 5. Dedupe and idempotency

- `once_per` renders a bounded per-proposal key. A proposal's own `dedupe_key` takes precedence.
- A key is reserved only by a successful launch. If a launch never starts, or the agent ends in terminal failure, the key is released and the next run can retry.
- A proposal that names an `agent_name` already in use is recorded as skipped, not as an error.
- If dedupe removes a proposal that another proposal waits on, the wait is rewired to the nearest surviving predecessor, or removed if none survives. A dropped step does not orphan the rest of its chain.

**Good for:** "same unit of work, don't repeat it" semantics without each script keeping its own ledger.

### 6. Proposal chains, capacity, and admission

- `wait_on` builds dependency chains among proposals, so `update → polish` runs in order.
- `wait_runners: N` on a routine becomes `%queue(capacity=N)` on each proposal. With `1`, a lane's agents run alone.
- A proposal can carry an `%if` predicate that is checked at admission time, not only when the script ran.
- `clan` groups related members under one declared clan with an optional summary, and `tribe` sets the display group.
- Hook runners and agent runners have separate global limits (`max_hook_runners` and `max_agent_runners`, both 3 by default), enforced across processes with a shared counter. A full pool defers work instead of queueing it.

**Good for:** multi-step automated work that must stay ordered and must not flood the runner pool.

### 7. Dry runs and manual runs

`sase axe job run <job> -n` (or `--dry-run`) validates the result and prints the proposals, including the rewired waits and the dedupe reasons, without launching anything. A manual run bypasses triggers but still honors guards. `-f` bypasses both for one run.

**Good for:** checking what an automation would do before it does it.

### 8. Supervision, recovery, and maintenance

- The service host restarts a crashed scheduler under `restart: on-failure`, with backoff from 1 s up to 60 s. Three failures within 60 s mark it `crash_loop`, which raises one notification per episode. A clean exit is not restarted.
- Inside the orchestrator, a crashed routine is restarted with the same bounded backoff. The cap is `axe.routine_restart_backoff_max_seconds`, which defaults to 60 s.
- **Maintenance mode** (`sase axe maintenance enter --reason "..."`) pauses routine ticks without stopping the orchestrator. Stale markers clear themselves after 24 hours, or when the owning PID is gone or has been recycled.
- A best-effort lifecycle journal at `~/.sase/axe/lifecycle.jsonl` records each start, stop, and restart with its source.
- Per the docs, agents and procs launched by routines run in their own systemd scopes, so restarting the scheduler does not kill them. Those scopes use `OOMPolicy=continue`, so one OOM kill does not stop the whole scope.

**Good for:** running unattended without losing agents on a restart, and pausing automation during installs or moves.

### 9. Visibility and reports

- Each job keeps run history with streamed logs and a status per run, such as `skipped` when a guard matches.
- The Services tab shows routines, jobs, run history, and per-job output. In the TUI, `a` adds a routine or job, `e` edits one, and `E` opens its recorded output.
- CLI: `sase axe routine status`, `sase axe job list`, and `sase axe job doctor`, which exits 1 when a configured script cannot be resolved. `sase doctor -C axe.jobs` runs the same checks.
- A job can publish a standalone report document to its state directory (`JobReport`, validated). A notification then carries a `ViewReport` action that opens the document in the TUI. Rewriting it each tick keeps it fresh without network calls.
- `error_digest` summarizes the last 100 recorded errors into a digest, with a notification that opens it.

**Good for:** answering "what did automation do, and where do things stand?" without reading logs.

### 10. Safe configuration

- Validation fails closed. Unknown fields, duplicate job identities, and non-positive durations produce errors with the config path.
- Map-form jobs merge across config layers. A machine overlay can set `enabled: false` for one job, and the rest of the entry is kept.
- Secret references resolve at dispatch, and a missing secret fails closed.
- `agent:` and `macro:` job fields are rejected. Scheduled agent work must come from a script's proposals.
- Scripts are found through `axe.job_script_dirs`, the interpreter's directory, or `$PATH`. Plugins can contribute full-name console scripts.

**Good for:** keeping automation auditable. Each agent launch traces back to a script result, a trigger, and a guard decision.

### 11. The lifecycle engine: how routines move agent work forward

This is the part that most other harnesses do not have. Routines finish and follow up on work that is already running:

- **`%wait` is fail-closed.** `wait_checks` releases a dependent only when the dependency's `done.json` says `completed`. Failed, killed, crashed, malformed, and missing results all keep the dependent parked. Multi-agent workflows wait for their children too.
- **Hooks, mentors, and workflows** are driven by the `hooks` routine. Stale ones restart, and finished ones are recorded.
- **Bead task triage** keeps one pending gate per live task bead. One job owns that invariant, and triage gates require independent `+1` reports before they appear.
- **Publication** drains queued artifact and hood work through a filesystem doorbell.

**Good for:** running a chain of agents, plan, then code, then review, that does not start the next step after a failure.

---

## What makes routines different

1. **Cheap sensing, metered acting.** The sensor is a deterministic script on a short interval. The actuator is an agent, and it runs only when the script's proposal clears every guard. Designs where the agent itself polls, or where each trigger starts a full session, pay model cost on every check. SASE pays model cost only for work that is actually needed.
2. **One chokepoint for launches.** Scripts never self-launch. The runner validates results, applies triggers, guards, dedupe, capacity, naming, and wait rewiring, and then launches. Every policy sits in one place, not in each script.
3. **Policy is data.** Cadence, triggers, guards, dedupe, and fan-out live in YAML. One script can serve many projects, and each instance keeps independent state.
4. **Routines manage what is already running.** Most scheduled-automation features only start new work. SASE's routines also advance hooks, mentors, and workflows, and they resolve `%wait` dependencies. That is the engine that moves a Patch from submission to review to landing.
5. **Deterministic supervision.** In the October 2026 comparisons, Gas Town's supervisors are LLM-driven patrol agents, and the Gas Town report says they caused incidents. Gas City moved its watchdog logic into deterministic orchestrator code. SASE's routines are already in that deterministic form.
6. **Operator-first control surface.** Dry runs, manual runs, maintenance mode, a lifecycle journal, a TUI Services tab, and doctor checks are built for one developer supervising many agents.

### How this compares with specific harnesses

| Harness | Scheduling and automation | Versus SASE routines |
| --- | --- | --- |
| **Gas City** (October 2026 report) | "Orders" with cooldown, cron, condition, event, manual, and webhook triggers. An order runs a formula or an exec command directly. Formulas compile to a durable graph with check and retry primitives. | More trigger types and direct workflow execution. SASE has stronger completion integrity, a human approves plans and launches, and agents are single-turn with host-owned finalization. |
| **Gas Town** (October 2026 report) | Long-lived role agents (Mayor, Deacon, Witness, Refinery) supervise each other in tmux. Its public docs describe a "propulsion principle." | Its supervision is LLM-driven and more dispatch-oriented. SASE's supervision is deterministic. SASE has no equivalent of its role hierarchy, and it does not run long-lived agent sessions. |
| **Codex app** (cited in this repo's blog) | Automations and background worktrees. The blog calls it the closest product competitor. I did not verify its current feature set in this session. | Codex is a polished product on one vendor's stack. SASE is local, provider-pluggable, and built around durable records and routines that manage work already running. |
| **Claude Code** | This session's `schedule` skill describes "routines" as cloud agents on a cron schedule. | The name collides with SASE's term but means something different. I did not inspect that feature in depth. |

---

## Gaps and friction

- **No wall-clock triggers.** Routines use intervals (`interval`, `run_every`), `fs`, and `git.commits_since`. The trigger set is exactly `always`, `git.commits_since`, and `fs` (`src/sase/axe/chop_runner_policy.py:29`). There is no cron, time-of-day, webhook, or event trigger.
- **A job cannot launch a workflow directly.** Only agent proposals are allowed. Gas City's orders can run a formula directly.
- **Scripts are subprocesses.** Ticks must stay short. The blog's guidance is that heavy work should become an agent. That is the right rule, but it puts a limit on what a job can do inline.
- **Routines do not verify landings.** The October 2026 comparisons report that SASE's Master Gate passed only 8 of its last 60 runs, and that nothing on the landing path refuses a red change. The scheduler does not address that. The Gas City comparison ranks landing discipline as the largest measured gap.
- **Documentation drift.** The default-routines page says nine routines; the config has ten. The jobs reference is about 660 lines, which makes it hard to read quickly.
- **Naming churn.** Routine and lumberjack, job and chop, and `sase_job_*` and `sase_chop_*` all coexist. The compatibility aliases are hidden, which makes the surface harder to learn. The project's own blog calls the learning curve real.

---

## Recommendation

1. **Keep the current model.** Intervals, the three triggers, guards, dedupe, and the proposal chokepoint cover the lifecycle work SASE already does. They are the part that differs from other harnesses, and it should not be traded away for a generic cron feature.
2. **Decide whether wall-clock schedules are needed.** A cron trigger would be a bounded addition next to `_TRIGGER_PROVIDERS`, and it would close the largest gap against Gas City. This is a product decision. The repo does not show a concrete user request for it yet.
3. **If you add event triggers, feed them from the event log.** The October 2026 Gas City report recommends a typed, sequenced event log as the foundation for triggers. Event triggers should still produce proposals, not direct workflow launches, so guards and dedupe still apply.
4. **Do not expand the routines into landing verification.** That is a separate lane. The Gas City comparison points to the separate design `merge_queue_fenced_master_and_exact_sha_releases` as the right place for it.
5. **Fix the docs.** Update the default-routines page to ten routines and tighten the jobs reference, so the public description matches the config.

---

## Evidence and confidence

- **Verified in code this session:** the default routine keys and intervals in `src/sase/default_config.yml`; the trigger set in `src/sase/axe/chop_runner_policy.py:29`; the guard kinds in `src/sase/axe/chop_policy_preflight.py`; the restart backoff in `src/sase/axe/orchestrator.py:55`; the checkpoint policy names in `src/sase/axe/chop_policy_checkpoint.py`; and the built-in `sase_job_*` entry points in `pyproject.toml`.
- **From the docs, not re-verified in code:** systemd scope detach, the lifecycle journal's 256 KiB cap, the crash-loop thresholds, and the `JobReport` publishing path.
- **From existing research, not re-verified here:** the Gas Town and Gas City comparisons, taken from the consolidated reports `research:202610/gastown_vs_sase_lessons_to_borrow/gastown_vs_sase_lessons_to_borrow__final.md` and `research:202610/gascity_advantages_over_sase_and_what_to_borrow/gascity_advantages_over_sase_and_what_to_borrow__final.md`.
- **Not checked:** the current feature sets of Codex and Claude Code, and any live behavior of a running scheduler.

## Sources

- `docs/reference/automation/scheduler.md`: architecture, supervision, maintenance, process lifecycle.
- `docs/reference/automation/scheduler-jobs.md`: structured results, proposals, triggers, guards, dedupe, targets, run history, Services views.
- `docs/reference/automation/scheduler-configuration.md`: routine and job fields, validation, layering.
- `docs/reference/automation/scheduler-default-routines.md` and `scheduler-housekeeping.md`: the built-in lanes.
- `docs/guides/schedule-recurring-work.md`: adding a routine and a job.
- `docs/blog/posts/axe-background-daemon.md` and `docs/blog/posts/why-coding-agents-need-orchestration.md`: design rationale and the Codex comparison.
- `src/sase/default_config.yml`, `src/sase/axe/`, and `pyproject.toml`: the implementation details listed above.
- The glossary entries for Routine, Sase Scheduler, and Job.
