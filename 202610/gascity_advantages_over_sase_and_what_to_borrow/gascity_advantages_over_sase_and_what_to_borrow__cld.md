# SASE vs. Gas City: where Gas City is ahead, and what SASE should borrow

> **Research query:** Compare SASE with Gas City (`gascity`, the
> [gastownhall/gascity](https://github.com/gastownhall/gascity) repo), using the recent Gas City
> and Gas Town research in this sidecar for context. In particular, in what ways is Gas City
> superior to SASE? End with a ranked list of recommended improvements to SASE.

*Researcher report (cld) · 2026-10-17 · one of five independent swarm reports.*

## Bottom line

1. **The two systems make different bets.**
   - **Gas City is a configurable factory.** A controller runs *methods* (TOML formulas) as
     graphs of durable work records (beads) across pools of long-lived agent sessions. Roles,
     schedules and supervision policies are configuration, shipped in shareable *packs*.
   - **SASE is a transaction system.** Single-turn, headless agents run in pooled workspaces.
     The host owns completion, and humans approve plans, launches and questions. Instructions
     are built from memory.
2. **Gas City's main structural lead is that the method is data the orchestrator executes.**
   - A v2 formula compiles into beads. A control dispatcher executes `retry`, `check`
     (compiled to `ralph`), `fanout`, `drain`, `scope-check` and `workflow-finalize` beads.
     After a crash it resumes from state saved on those beads.
   - In SASE the equivalent pieces are mostly prompts. Macro workflows restart from step 0.
     Epic phases are agents launched up front and chained with `%wait`. Whether a phase is
     "done" is mostly the agent's or the lander's judgment.
3. **The most expensive gap is how the Gas City *project* lands code, not the `gc` product.**
   - `main` has a GitHub ruleset: PRs only, required `bazel test` and CodeQL checks, and an
     enabled merge queue (squash; up to 5 entries per group; all entries must pass).
   - **Result:** 99 of the last 100 CI runs on `main` passed, and 60 of 60 merge-queue runs
     passed. Its cadence is comparable to SASE's: 20–114 commits a day.
   - **SASE:** 8 of the last 60 Master Gate runs passed, and `master` has no ruleset. This
     is direct counterevidence to the merge-queue rejection recorded in
     `decisions:ci-two-speed-split`. Gas City does pay for it with remote Bazel caching and
     paid runners (see [§1](#1-main-stays-green-because-nothing-lands-unverified-project)).
4. **Gas City has a much wider integration surface.** It has:
   - cron, event, condition and webhook **orders** that fire whole methods;
   - a typed, sequence-numbered **event log** streamed over SSE;
   - a generated **OpenAPI** API (130 paths) and an embedded **web dashboard**;
   - **packs** with versioned imports, a lockfile and a registry;
   - **18** harness presets and about 10 session runtimes.
5. **Read Gas City's docs skeptically.** Code-level checks found about a dozen features that
   are advertised but removed, unwired or partial. Examples:
   - `tally` voting was removed, but the docs still recommend it.
   - "Health patrol is an order" is false; it is Go controller code.
   - Check-script timeouts burn retry attempts on the path the compiler actually emits.
   - `on_item_failure` is ignored for parallel drains.
   - Crash-loop quarantine is never fed.
   - The keyed reconciler v2 is still opt-in, and it refuses many features.

   SASE's decision-record discipline is genuinely better here (see
   [calibration](#gas-city-claims-that-do-not-survive-the-code)).
6. **Top recommendations** (full list in [the recommendations](#ranked-recommendations-for-sase)):
   1. **Make `master` green by construction:** verify before landing, using Gas City's
      ruleset and merge-queue shape.
   2. **Durable, resumable workflow runs** in the Rust core.
   3. **Host-run `check:` gates with bounded loops over several steps,** plus typed failure
      dispositions.
   4. **A typed, durable event log.**
   5. **Cron and event triggers that can fire workflows.**

## Method and evidence

**Snapshots compared**

- **Gas City:** `main` @ `45c804d59e` (2026-10-17 03:34 UTC). Latest tag v1.5.0. Opened with
  `sase repo open gh:gastownhall/gascity`.
- **SASE:** `master` @ `5ea5fa5452`. Master Gate data runs through `28ced2a125`
  (2026-10-17 04:07 UTC).

**What I read**

- **Gas City docs and rules:**
  - `AGENTS.md`, `ROADMAP.md`, `CHANGELOG.md` (Unreleased);
  - `docs/getting-started/{how-gas-city-works,faq,dashboard}.md`;
  - `docs/guides/{understanding-formulas,understanding-packs,shareable-packs,registry-showcase,capabilities-for-coding-agent-users,multi-agent-engineering-environment}.md`;
  - `engdocs/contributors/{primitive-test,release-gate-criteria-conventions}.md`;
  - core pack orders and formulas;
  - `.github/workflows/{ci,bazel,pr-evidence-watchdog,ci-verdict-watchdog}.yml`.
- **Gas City code:** two code-level sweeps of `internal/dispatch`, `internal/formula`,
  `internal/orders`, `internal/events`, `internal/api`, `internal/mail`, `internal/runtime`,
  `internal/usage`, `internal/doctor`, and the `cmd/gc` reconciler. Both sweeps cite file
  and line for every claim.
- **SASE:**
  - two sweeps of `src/` and `docs/`, plus my own spot checks;
  - decision records `ci-two-speed-split`, `single-turn-agents` and `host-owned-completion`;
  - `sase bead search` for planned overlapping work;
  - `git log`.
- **Live data:**
  - `gh run list` for both repos: Master Gate for SASE; `CI` and `bazel.yml` for Gas City;
  - the GitHub branch-ruleset API for both default branches;
  - merged-PR authorship for Gas City.

**Prior research**

This report builds on two earlier consolidated reports and does not repeat them:

- `research:202610/gascity_software_factory_purpose_and_vision/gascity_software_factory_purpose_and_vision.md`
  covers what Gas City is and where it is heading.
- `research:202610/gastown_vs_sase_lessons_to_borrow/gastown_vs_sase_lessons_to_borrow.md`
  ranked Gas Town's advantages and proposed 14 changes to SASE (R1–R14). Where Gas City
  changes that evidence, I say so.

**Evidence tags**

- **[wired]:** in Gas City code, with a production caller.
- **[partial]:** wired, but with a verified gap.
- **[unwired]:** code exists, but nothing calls it in production.
- **[doc-only]:** described in docs, but not in code.
- **[project]:** how the Gas City *repository* is run, not a feature of the `gc` product.

**Not done.** I did not install Gas City, run a city, or benchmark equal workloads. Gas
City's throughput figures are its maintainers' own claims.

## The two systems at a glance

- **Unit of execution**
  - *Gas City:* A session: a long-lived CLI agent, usually in tmux, that claims beads from a
    hook and is reused across steps
  - *SASE:* One provider turn, run headless with stream-JSON output; continuation is
    mechanical (`decisions:single-turn-agents`)
- **Unit of method**
  - *Gas City:* A formula (TOML). v2 compiles it into a bead graph executed by a control
    dispatcher
  - *SASE:* A macro or workflow (typed YAML), executed in-process by the runner; epics run
    as `%wait`-chained agents
- **Roles**
  - *Gas City:* Pure config: `agents/<name>/agent.toml` plus a prompt template, with pools
  - *SASE:* Implicit in macros. Every launch is an ad hoc run, and epic role macros are
    resolved by tag
- **Work store**
  - *Gas City:* `bd` beads (Dolt by default; a SQLite infrastructure ledger is in preview)
  - *SASE:* Git event-stream beads in sidecars, plus Rust-owned SQLite stores
- **Completion**
  - *Gas City:* Pack formulas: the core `mol-polecat-commit` runs
    `git push origin HEAD:{{base_branch}}`. There is no landing code in Go
  - *SASE:* Host-owned finalizers with an atomic declaration and independently verified
    postconditions
- **Automation**
  - *Gas City:* Orders: cooldown, cron, condition, event, manual and webhook triggers →
    formula or exec
  - *SASE:* Scheduler routines on intervals; job triggers `always`, `git.commits_since` and
    `fs`
- **Observation**
  - *Gas City:* Typed event bus, SSE, OpenAPI, web dashboard, `gc trace`
  - *SASE:* ACE TUI, Android app and gateway, Telegram, local telemetry, ToolRun triage
- **Sharing**
  - *Gas City:* Packs, imports with version pins, `packs.lock`, a registry with publishing
  - *SASE:* Python plugins (13 entry-point groups), a GitHub-topic catalog, committed
    `sase/macros`
- **Humans**
  - *Gas City:* Human gates as beads; mail and nudges; attaching to a live session
  - *SASE:* Durable non-blocking gates, autonomy profiles, LaunchApproval, a sudo gate,
    mobile

## Where Gas City is ahead

### 1. Main stays green because nothing lands unverified [project]

**Gas City**

- **The `main` ruleset** (GitHub API) contains:
  - `pull_request`, `non_fast_forward` and `deletion` rules;
  - **required checks** `Check`, `bazel test (side-by-side)`, `BUILD files in sync`, and
    four CodeQL analyses;
  - a code-scanning threshold;
  - a **merge queue**: squash, up to 4 groups building at once, up to 5 entries per group,
    `ALLGREEN` grouping (every entry must pass), a 5-minute wait, and a 60-minute check
    timeout.
- **Verification is fast because it is cached.** Bazel runs with a remote cache and remote
  execution (`.bazelrc` `fork-cache` / `remote-exec`). The last 20 `bazel.yml` runs had a
  **p50 of about 4.9 minutes**. Two of the eight PR runs among them failed, and both were
  caught before merge.
- **Missing evidence counts as failure.**
  - `pr-evidence-watchdog.yml` "fails closed when a PR's head commit never produces complete
    CI evidence".
  - `ci-verdict-watchdog.yml` exists because a run cancelled while queued "looks identical
    to 'everything passed'".
- **Release-gate files.** There are 517 files in `release-gates/*.md`, each a numbered
  table of criteria with evidence.
  - `release-gate-criteria-conventions.md` requires "Tests pass" to name the CI jobs that
    are actually required.
  - It was written after two gates signed off suites that had skipped the regression.
- **Agents author much of the work.** Of the last 30 merged PRs, 9 came from
  `gascityinc-randy[bot]`.
- **Outcome:**
  - **99 of the last 100** `CI` runs on `main` passed (Oct 13–17).
  - **60 of 60** merge-queue runs passed.
  - First-parent commits ran 8–114 a day from Oct 10 to 17, and 762 since Oct 1, all
    squash-merged PRs.

**SASE today**

- **No ruleset:** `gh api repos/sase-org/sase/rules/branches/master` returns `[]`.
- **Landing comes before verification.** The commit finalizer rebases and pushes straight
  to `master`, and Master Gate runs *after* the push.
- **Master Gate results:**
  - **8 of the last 60 runs passed** (Oct 16: 6 passed, 38 failed; Oct 17 so far: 2
    passed, 14 failed);
  - p50 12.5 minutes, p90 24.4 minutes;
  - a comparable cadence of 27–62 commits a day.
- **The design record rejected this approach.** `decisions:ci-two-speed-split` lists "a
  GitHub merge queue" among the measured alternatives that "consumed the account's capacity
  without reliably settling the tip".
- **Nothing is planned.** `sase bead search` finds no landing-lane or merge-queue work.

**Caveats**

- **Capacity.** Gas City buys capacity with Blacksmith runners and a remote-execution
  fleet. Its push-to-`main` CI has a median of about 1 minute because the work already
  passed the queue.
- **Speed.** Bazel's hermetic cache is what makes full verification of each change cheap.
  SASE's Python suite has no equivalent cache.
- **Per-group, not per-SHA.** Grouped verification checks the tip of each group, not every
  SHA. `ci-two-speed-split` values "an attributable per-SHA signal" explicitly.
- **Not a product feature.** The `gc` product has no Go landing machinery: the
  `merge_strategy` metadata that `sling` writes is read by nothing.

**Verdict.** This is the largest and best-measured gap. It strengthens the Gas Town
report's R1. It also changes that report's advice: Gas City shows a GitHub merge queue
working at SASE's cadence with agent-authored PRs, which that report had ruled out.

### 2. Workflow runs survive crashes [wired]

**Gas City**

- **Applying a v2 formula creates beads.** From then on a run is "independent of the file
  and of any session".
- **The control dispatcher keeps nothing in memory.** On restart it re-queries open, ready
  control beads (`cmd/gc/dispatch_runtime.go`). Each control kind resumes from state saved
  on its bead: `gc.retry_state`, `gc.fanout_state`, `gc.drain_state` plus
  `gc.drain_manifest`, and `gc.control_epoch`.
- **Ordering is crash-safe.** Each kind settles its logical bead first and closes the
  control bead last, so an interrupted settle is re-driven.
- **Idempotency keys.** Attempts use `"<controlID>:attempt:<n>"` plus a compare-and-swap
  on the epoch (`internal/dispatch/control.go`, `internal/molecule/molecule.go`). Drain
  units use deterministic keys.
- **Crash tests.** A crash-injection harness faults every write position
  (`internal/dispatch/crash_injection_test.go`).
- **Drift detection.** `gc formula version-check <bead>` reports when a running instance
  no longer matches the formula file it came from (`gc.formula_hash`).

**SASE today**

- **Workflow state is written but never read.** `workflow_state.json` is rewritten on every
  step change, but only the TUI reads it.
  - `WorkflowExecutor` always starts at `current_step_index=0`
    (`src/sase/macro/workflow_executor.py:101-112`).
  - Provider retries re-run the whole workflow (`src/sase/axe/run_agent_exec.py:310-353`).
  - Restart and auto-restart "stop, wipe, relaunch" and delete the old artifacts.
- **Epics are chained, not driven.** Every phase and the lander are dispatched at once,
  ordered by `%wait` lines (`src/sase/bead/work_prompt.py:196-248`). A failed phase "keeps
  dependents and the land agent parked" until a human re-runs `sase bead work`
  (`docs/reference/work-units/bead-work.md`).

**Caveats**

- **One dispatcher per scope.** `ProcessControl` is explicitly not CAS-guarded against two
  concurrent dispatchers.
- **Serial sweeps.** A slow check blocks every other control bead behind it.
- **Side effects repeat.** The data plane is not idempotent (Gas City issue #3005): a
  retried step repeats its pushes, comments and mail.
- **Resume granularity.** Work resumes at bead boundaries, never mid-step.

**Verdict.** A structural lead, with high confidence.

### 3. "Done" means a host-run check passed [partial]

**Gas City**

- **`[steps.check]`** compiles to a `ralph` control. After the step closes, the
  **dispatcher runs** the exec script, not an agent.
  - The script gets a whitelisted environment: `GC_BEAD_ID`, `GC_ITERATION`, and the work
    and artifact directories.
  - The default timeout is 5 minutes (`internal/dispatch/ralph.go`,
    `internal/convergence/condition.go`).
  - On failure with budget left, it **re-creates the whole subtree** as iteration N+1, for
    example review lanes → synthesis → fix (`control.go`).
  - When attempts run out, the step fails and downstream work is blocked.
- **`retry` reads metadata, not error text.** The worker writes `gc.outcome` and
  `gc.failure_class` (`transient` or `hard`).
  - `on_exhausted = "hard_fail" | "soft_fail"` lets an optional lane degrade without
    blocking the build.
  - A "pass" with a missing required artifact is downgraded to transient
    (`internal/dispatch/retry.go`).
- **The shipped review loop** (`build-basic-review`) works like this:
  - acceptance, test-evidence and simplicity reviewers run in parallel on different roles;
  - a synthesizer combines them, then an apply-findings step makes the fixes;
  - the host re-runs the loop until `implementation-review-approved.sh` passes, at most 6
    times.

**SASE today**

- **Loops cover one step.** `repeat: {until, max}` wraps a single step, and the step's own
  output decides when to stop (`src/sase/macros/sync.yml`). Hitting `max` fails the
  workflow.
- **No retry field, no multi-step loop body.**
- **Mentors have no model field and no synthesizer.** A human accepts their comments in a
  modal (`docs/reference/automation/mentors.md`).
- **Finalizers verify the commit, not the task.** They check commit postconditions, not
  whether the task was accepted.
- **Epics end in judgment.** The only acceptance step is the lander's prompt.

**Caveats (all from the code)**

- **Infrastructure failures cost attempts.** On the compiled `ralph` path a check timeout
  or exit 75 *spends an attempt*. The protection described in the spec exists only in the
  legacy `check` path (`ralph.go:94-130` vs `control.go:314-323`).
- **Incomplete kill.** There is no process-group kill, so a script's grandchildren survive.
- **Silent hold.** A missing check script holds the step open without saying so.
- **Voting is gone.** `tally` quorum voting was removed (`955dfd28c`), but
  `AGENTS.md` and the formulas guide still advertise it.

**Verdict.** High value, and the idea fits SASE's `host-owned-completion` decision
naturally.

### 4. Reactive automation: orders [partial]

**Gas City**

- **An order is a trigger plus either a formula or an `exec` command** (never both).
  Triggers (`internal/orders/triggers.go`):
  - `cooldown`;
  - `cron` (5 fields with ranges and steps, plus a time zone);
  - `condition` (a shell check, 10-second timeout);
  - `event` (for example `bead.closed`, read with a sequence cursor);
  - `manual`;
  - `webhook`.
- **Run-once guarantees.** A single-flight "open-work gate" and tracking beads stop
  re-fires, and an `order.suppressed` event reports long skips.
- **The core pack ships supervision policy as editable orders:**
  - `orphan-sweep`: "reset beads assigned to dead agents back to the work pool", every 5
    minutes;
  - `spawn-storm-detect`;
  - `renudge-stale-human-gates` and `notify-on-human-gate-creation` (an event trigger);
  - `cascade-nudge-on-blocker-close` (an event trigger);
  - `convoy-autoclose-backstop`, `prune-branches` and `reaper`.
- **Intake packs.** The `github`, `slack-*` and `discord` packs supply webhook intake.

**SASE today**

- **Interval routines only.** Job triggers are `always`, `git.commits_since` and `fs`
  (`src/sase/axe/chop_runner_policy.py:29`). There is no cron and no event trigger.
- **Gating tools exist:** `run_every`, `inhibit_if`, `%if::` predicates and `once_per`.
- **Jobs can launch agents but not workflows.** A job can propose launches, but
  "standalone `#!workflow` references are forbidden"
  (`docs/reference/automation/scheduler-jobs.md:199-201`).
- **The reactive pieces** are `%wait(bead=…)` and monitor outcome policies.

**Caveats**

- **Polling, not subscription.** Event triggers poll on each tick, about 30 seconds by
  default, and fire once per batch of events rather than once per event.
- **No variables.** Orders cannot pass vars (Gas City issue #1813).
- **Unimplemented field.** `reserved_dispatch` is declared but nothing reads it.
- **Health patrol is not an order.** Despite the docs, it is Go controller logic.

**Verdict.** Medium-high. SASE jobs are already scripts, so the gap is triggers and what a
job is allowed to launch.

### 5. A typed event stream, API and dashboard [wired]

**Gas City**

- **The event log** is `.gc/events.jsonl`.
  - Each city has its own increasing `seq`, assigned under a mutex plus a flock.
  - About 106 known event types each have a registered payload, enforced by
    `TestEveryKnownEventTypeHasRegisteredPayload`.
  - Rotation writes gzip archives, and replay reads across them.
- **`gc events --follow`** streams over SSE, with composite cursors across cities.
- **The API.** Huma generates the OpenAPI spec: 130 paths and 167 operations, with
  `TestOpenAPISpecInSync` catching drift.
- **The dashboard** is a React app embedded in the binary. Views: cockpit, agents, beads,
  runs with diffs, mail, activity and health.
- **Safe defaults.** It binds to loopback and is read-only on other addresses unless
  `allow_mutations` is set. Mutations need a CSRF header, and signed write grants are
  optional.

**SASE today**

- **The global log is thin.** `~/.sase/logs/events.jsonl` is untyped, has one-second
  timestamps and no sequence numbers, rotates at 2 MiB, and cannot be followed
  (`src/sase/logs/run_log.py:103-120`).
- **Follow works per entity only** (`sase tool show -F`, `sase monitor show --follow`).
- **The gateway stream does not survive restarts.** Its SSE stream resumes with
  `Last-Event-ID`, but it lives in memory, so a restart forces `resync_required`. It has
  only three coarse event kinds.
- **No OpenAPI and no web dashboard.**

**Caveats**

- **Delivery is best-effort.** Recording can drop events, and some alert events go out
  untyped.
- **The TUI is the better daily surface.** For a single operator, SASE's TUI and mobile
  app beat a local web page.

**Verdict.** An infrastructure gap. A durable event log is the foundation for
[§4](#4-reactive-automation-orders-partial), for integrations, and for any web surface.

### 6. Methods compose [partial]

**Gas City**

- **`extends` chains with same-id overrides.** The pack's build pipeline is
  `build-base` → `build-from-*-base` → 21-line entry points. A child replaces an inherited
  step in place, which splices new steps into the middle (`internal/formula/parser.go`).
- **Vars are validated before any bead exists.** `required`, `enum` and `pattern` are
  checked at compile time and again before instantiation.
- **Compile-time `condition` policy forks.** The same file yields either a parallel drain
  or a shared-session drain.
- **Swappable sub-formulas.** A var such as `code_review_formula` swaps the reviewer.
- **`drain`** fans one item formula, itself a full v2 graph, out over every member of a
  runtime-discovered convoy:
  - members are ordered by their dependencies;
  - each is reserved exclusively;
  - at most 100 units.

**SASE today**

- **Workflows are expressive within one run:** typed inputs, `use:` step imports, and
  `if`, `for` and `while`.
- **No partial overrides.** A project override replaces the whole file.
- **No real fan-out inside a workflow.** `for` runs sequentially. `parallel` is a fixed
  list of steps run on threads in one process, not separate agents in separate workspaces
  (`src/sase/macro/workflow_executor_parallel.py`).
- **The epic pipeline has a fixed shape:** phase agents, then a lander.
  - Its role macros can be overridden by tag (`src/sase/bead/macros.py`).
  - A phase cannot become a multi-step method.

**Caveats**

- **Drain gaps.**
  - A drain creates no worktrees; pack scripts do that.
  - `on_item_failure` is ignored for `separate` drains.
  - The exclusive reservation only blocks *other drains*.
- **Composition gaps.** `extends` drops advice, and `vars.type` is not enforced.
- **Cost.** Every's review found that "a six-step job can cost six times the cost of one
  Claude session".

**Verdict.** Medium-high. The idea to transfer is "a phase is a method, not a prompt".

### 7. Packs make methods shareable [wired]

**Gas City**

- **A pack is a directory** with `pack.toml` (schema 2) and standard subdirectories:
  `agents/`, `formulas/`, `orders/`, `commands/`, `doctor/`, `skills/`, `mcp/`, `overlay/`,
  `template-fragments/` and `assets/`.
- **Imports.**
  - Each import is a named binding with a `source` URL and a `version` constraint (semver or
    `sha:`), recorded in `packs.lock`.
  - Packs can be imported at city or rig scope.
  - Names are namespaced, so `review.worker` and `build.worker` coexist.
- **The registry** supports `search`, `show` and `publish`, with review before a pack goes
  public. First-party packs: `gascity`, `gastown`, `github`, `slack-*`, `discord` and
  `cass`.

**SASE today**

- **Sharing is Python packaging.** Plugins use 13 entry-point groups, a GitHub-topic
  catalog, and `sase plugin install` (needs a uv tool install).
- **Macros spread by copying.** They are shared by committing `sase/macros` or through
  chezmoi.
- **No lockfile and no data-only bundle.** Plugins cannot ship memory
  (`docs/reference/macros/fields.md:321-324`).

**Caveats**

- Imported packs are trusted code; Gas City says so in its `trust-boundaries.md`.
- SASE's plugins are more powerful at the code level: providers, VCS, finalizers.

**Verdict.** Medium. It matters most for adoption: the launch post and users outside this
machine.

### 8. Declarative roles, pools and routing of ready work [partial]

**Gas City**

- **Role definitions.** `agents/<name>/agent.toml` plus a prompt template defines a role.
- **Pools.** A role becomes a pool with:
  - `min_active_sessions` and `max_active_sessions`;
  - a `scale_check` measuring demand (by default, the count of ready beads);
  - idle retirement and drain-acknowledgement.
- **Routing.**
  - `gc sling` routes work.
  - Beads are routed by `gc.routed_to`.
  - Claims go through `bd update --claim`, which `bd` makes atomic.
  - Continuation groups keep related steps in one session.

**SASE today**

- **No declared roles.** Every launch is an ad hoc run.
- **Admission control is strong:** a weighted queue, priorities and holds.
- **Little routes itself.**
  - Ready standalone tasks wait for human triage.
  - Epics dispatch automatically only after a plan is approved.

**Caveats**

- **Reconciler status.** The legacy reconciler is still the default, and v2 refuses
  `scale_check`, `max_session_age`, the stall timeouts, and the k8s, ssh and exec
  runtimes (`cmd/gc/reconcile_latch.go`).
- **Claude-only idle detection.** Content-based idle tracking applies only to Claude.
- **Long sessions cost money and degrade context.**

**Verdict.** Medium. The idea to transfer is "ready work of type X routes to role Y within
a budget". Long-lived pools do not transfer.

### 9. Reach: harnesses and runtimes [wired]

**Gas City**

- **18 harness presets** (`internal/worker/builtin/profiles.go`): claude, codex, gemini,
  grok, kimi, kiro, cursor, copilot, amp, opencode, mimocode, zcode, groq, cerebras,
  auggie, pi, omp and antigravity.
- **New harnesses are config-only.** A `[providers.x]` entry is enough to launch a new one.
- **Runtimes:**
  - tmux (the default), `subprocess`, `acp`, `t3bridge`, `k8s`, `herdr`, `hybrid`,
    `exec:<script>` and `ssh:<host>`;
  - packs can declare their own runtimes.

**SASE today**

- **7 production providers:** agy, claude, codex, grok, muse, opencode and qwen, plus
  `fakey` for tests. Each provider is a Python plugin.
- **Execution:** headless stream-JSON, plus `%dispatch` to enrolled machines.
- **No ACP, containers or Kubernetes.**

**Caveats**

- **Fragility.** tmux control relies on pane scraping.
- **Support depth.** Deep support (transcripts, usage) is code per provider; only claude
  and codex get usage extraction.

**Verdict.** Medium-low. ACP is SASE's cheap route to breadth.

### 10. Messaging and live steering [wired]

**Gas City**

- **Mail** is a bead with threads and read labels. Hooks inject it at `UserPromptSubmit`.
- **Nudges** run in `immediate`, `wait-idle` or `queue` mode, with a persisted queue.
- **Live access:** `gc session attach`, `peek` and `logs -f`.

**SASE today:** no addressed inbox.

**Verdict.** This confirms the Gas Town report's R5, a turn-start inbox. Live steering
conflicts with `single-turn-agents`; skip it.

### 11. Doctor extensibility and repair [wired]

- **Gas City:**
  - About 113 check types, of which about 37 can fix their problem.
  - Packs and cities add checks as `doctor/<name>/doctor.toml` with `run`, an optional
    `fix`, and `warmup`.
- **SASE:**
  - About 103 checks, with two narrow `--fix-*` flags.
  - Projects cannot contribute checks.
- **Verdict:** small and cheap.

### 12. Cost in dollars, and OTel [partial]

- **Gas City:**
  - Usage facts carry `cost_usd_estimate`, from pricing tables layered as shipped defaults,
    then pack, then city.
  - Readers: `gc costs`, a usage API, and OTel token metrics.
  - Limits: only claude and codex are covered, and no budget is enforced.
- **SASE:** tokens and the percentage of the subscription window used; no dollars and no
  OTel.
- **Verdict:** small, unless SASE starts serving users who pay per API key.

### 13. Contributor governance [project]

**Gas City**

- **A capability ladder.** "Prefer the lowest rung that works": a prompt change, then pack
  config, then composing existing machinery, then an adapter, and only then new SDK surface.
- **The Primitive Test.** A capability enters the SDK only if it needs atomicity, would be
  just as necessary with a model 10× smarter, and is transport rather than cognition.
- **Invariants enforced in CI:** OpenAPI sync, typed events, the worker boundary, and
  config field sync.
- **Executable tutorials.** `TestTutorial01` runs the tutorial scenarios through
  `testscript`, and there are docsync tests.

**SASE today**

- Decision records with reopen conditions. These are better than Gas City's "settled, do
  not revisit" list.
- The Rust-core boundary litmus test.
- Reference memory for each area.

**Verdict.** SASE is mostly at parity or ahead. Two things are worth borrowing: the ladder
as a one-line rule, and executable tutorials.

## Gas City claims that do not survive the code

Each claim below was checked against `45c804d59e`. Calibrate Gas City's documentation
accordingly:

1. **Quorum voting.** `AGENTS.md`, `nine-concepts.md` and the formulas guide recommend
   `on_complete` plus `tally` for majority, unanimous or any-pass voting. **Tally was
   removed.** The parser rejects `[steps.tally]`, and `internal/reviewquorum` has no
   importers.
2. **Health patrol.** "Health patrol is one kind of order" (`how-gas-city-works.md`) is
   false: it is Go controller logic.
3. **Check infrastructure retries.** The spec says a check that times out or exits 75
   re-runs without spending an attempt. That only holds on the legacy path. The compiled
   `ralph` path spends an attempt either way.
4. **`on_item_failure`** is validated and stamped for `separate` drains, but never read.
5. **Crash-loop quarantine** through `max_restarts`/`restart_window` is never fed:
   `recordStart` has no production caller. The `session.quarantined` and
   `session.suspended` events have no emitters.
6. **The reconciler v2 docs contradict themselves.** They say it is both a "trace-only
   skeleton" and a completed cutover, and they name files that do not exist. In the code,
   legacy is the default, and v2 is refused for many configs.
7. **"No skills system" and "No MCP/tool registration"** are listed as permanent
   exclusions in `AGENTS.md`, but `internal/materialize/` projects both into every
   provider.
8. **"Keep judgment out of Go."** The opt-in stall recycler, the pane-text rate-limit
   heuristics, the Claude-only idle clock and a hard-coded nudge prompt are all judgment in
   Go.
9. **"Sixteen" harnesses** (FAQ). The code has 18.
10. **Exclusive drain reservation** is enforced only against other drains; claim and sling
    paths ignore it. The `read` access mode is a label with no enforcement.
11. **Unimplemented order field.** `reserved_dispatch` is set by two core orders but read
    by nothing.
12. **Stale docs.** `orders.md` (cron syntax, blocking checks) and `messaging.md` ("nudges
    are fire-and-forget") describe older behavior.

## Where SASE is ahead (do not over-borrow)

- **Completion integrity.**
  - SASE: an atomic declaration, host-selected finalizers that verify independently,
    absorption of raw commits, discarded-work guards, and resumable commit attempts.
  - Gas City: "done" is whatever a pack's formula pushes.
- **Robust adapters.** Stream-JSON subprocesses, not tmux keystrokes and pane scraping.
- **Capacity admission.** A weighted queue, priorities, holds with TTLs, and usage-window
  probes with drain. Gas City has count caps and an endpoint circuit breaker, and no
  token or dollar budget.
- **Human-in-the-loop.** Gates that hold no resources, autonomy profiles, LaunchApproval,
  a typed sudo gate, an Android app, and Telegram.
- **Memory and instructions.** Memory-built instruction bundles, decision records, a
  glossary and audited memory reads. Gas City's stance is "the model IS the skill system".
- **Docs that match the code.** Compare the list above.
- **Lighter operations.** No Dolt server, no mandatory tmux, and pooled workspaces that
  share Git objects through alternates.
- **Fleet across your own machines.** `%dispatch` with machine attention.
- **Domains Gas City lacks:** a goals ledger, artifacts, research swarms, and provenance
  receipts.

## Ranked list: ways Gas City is superior to SASE

Ranked by impact on SASE's outcomes × size of the gap × confidence that Gas City's version
actually works.

1. **Its default branch stays green.** It verifies every change before it lands: required
   checks, a batched merge queue, cached Bazel tests, and evidence watchdogs. The measured
   result is 99/100 green on `main` against 8/60 for SASE's Master Gate. *(High
   confidence; [project]. This is how the repo is run, not a `gc` feature.)*
2. **Workflow runs are durable graphs.** They survive crashes and resume at bead
   boundaries, using idempotency keys and crash-injection tests. *(High; [wired].)*
3. **The host decides "done".** A host-run check loop can re-create a whole subtree, and
   explicit failure classes support soft-fail lanes. *(High in design, medium in
   execution; [partial]: infrastructure failures burn attempts, and voting was removed.)*
4. **Its automation reacts.** Cron, event, condition and webhook orders fire full methods,
   and supervision policy ships as editable orders (orphan sweep, re-nudging stale gates,
   spawn-storm detection). *(Medium-high; [partial].)*
5. **It has a typed, durable, followable event stream,** with a generated OpenAPI API and
   a web dashboard. *(High; [wired].)*
6. **Its methods compose.** `extends` with overrides, validated vars, policy forks, and
   `drain` running an item formula over a runtime-discovered set. *(Medium-high;
   [partial].)*
7. **Packs** share agents, formulas, orders, commands and doctor checks through versioned
   imports, a lockfile and a registry. *(High; [wired].)*
8. **Declarative roles and demand-scaled pools** route ready work automatically. *(Medium;
   [partial]: v2 refuses `scale_check`.)*
9. **Reach:** 18 harnesses and about 10 runtimes, including ACP, k8s and ssh. *(High in
   count; medium in robustness.)*
10. **Agents can mail and nudge each other,** and a human can attach to a live session.
    *(High; already ranked in the Gas Town report.)*
11. **Packs can extend the doctor,** and about 37 checks can fix their problem. *(High.)*
12. **It estimates cost in dollars and exports OTel metrics** (claude and codex only).
    *(Medium.)*
13. **Contributor heuristics:** the capability ladder and executable tutorials. *(Medium;
    SASE is otherwise at parity or ahead.)*

## Ranked recommendations for SASE

Ranked by leverage × fit with SASE's decision records ÷ size. Items marked **(core)**
belong in `sase_core` under the Rust-core boundary.

### R1. Verify before landing, so `master` is green by construction

Addresses superiority #1 · S (ruleset) → M (finalizer) · supersedes part of
`ci-two-speed-split`

1. **Now (configuration, S).** Add a `master` ruleset:
   - block force-pushes and deletion;
   - require Master Gate's aggregate check for PR merges;
   - add tag and release rulesets so only the release workflow can tag.
2. **Landing through a queue.** Copy Gas City's shape:
   - **Mechanics.** The commit finalizer, through sase-github's PR path, opens and enqueues
     a squash PR. A merge queue with `ALLGREEN` groups of 5 or fewer runs **Master Gate**
     (not Full CI) as the required check. A monitor watches the outcome.
   - **Push proof.** Close beads and resolve `%w(bead=…)` waiters only when the merge
     lands. This is the Gas Town report's "push proof".
   - **Capacity.** Today every push already runs Master Gate, so runner time is roughly
     unchanged, and grouping reduces it.
   - **Wall clock.** About 50 commits a day at a p50 of 12.5 minutes is about 10.4 gate-hours
     of serial time; groups of 5 cut that to about 2.1 hours.
3. **Rejections become repair work.** When the queue rejects an entry, launch one repair
   agent with the failing log and the rejected diff. This fits `host-owned-completion`.
4. **Missing evidence counts as red** (Gas City's evidence watchdog). A landing with no
   gate verdict counts as a failure.
5. **Write the decision record.**
   - Name the trade: verification of each group's tip instead of each SHA.
   - Note what changed since the merge queue was rejected: a measured outside example at
     the same cadence, and Master Gate rather than full CI as the required check.
   - If the GitHub queue still fails on capacity, fall back to the Gas Town report's local
     landing lane.
6. **Success criterion:** Master Gate at least 95% green on `master` over two weeks,
   holding up for at least 30 commits a day.

### R2. Durable, resumable workflow and epic runs (core)

Addresses #2 · M–L

1. **Authoritative run records.** Each workflow run records, per step: status, outputs, an
   attempt counter and an idempotency key (`<run>:<step>:<attempt>`).
   - Write in the order "settle the step, then advance the cursor".
   - Cover every write position with crash-injection tests.
2. **Resume instead of rerun.** `sase workflow resume <run>` starts at the first unfinished
   step, and the runner's retry and auto-restart paths call it instead of re-running from
   step 0 and deleting artifacts.
3. **Side-effect classes.** Steps declare one: `pure`, or `effectful` (pushes, PR comments,
   notifications). Effectful steps record what they already did so a resume never repeats
   it. This is Gas City's issue #3005, avoided by design.
4. **Host-driven epic waves.** The host launches each wave of an epic when it becomes
   ready, instead of dispatching every phase up front with `%wait` chains. That makes
   [R3](#r3-host-run-check-gates-bounded-multi-step-loops-and-failure-dispositions-core)'s
   retry policy possible.

- **Fit:** compatible with `single-turn-agents`. The *run* is durable; each agent turn is
  still one turn.

### R3. Host-run `check:` gates, bounded multi-step loops, and failure dispositions (core)

Addresses #3 · M · depends on R2 · absorbs the Gas Town report's R3 (failure policy)

1. **A host-run check.** A step field
   `check: {run: <script or just target>, max_attempts: N, timeout: …}` is executed by the
   host through `sase tool run`, so its verdict becomes a fingerprinted receipt.
   - It may wrap a **group of steps** (lanes → synthesis → fix). Each failed iteration
     re-runs the group.
2. **Retry from a declared class.** `retry: {max_attempts, on_exhausted: hard_fail |
   soft_fail}`, driven by a `failure_class: transient|hard` field in the agent's final
   declaration, not by matching error text.
3. **Phase acceptance checks.** An epic phase bead may name an acceptance check. On
   failure, retry with the previous attempt's evidence and a model promoted up the effort
   ladder; then skip-and-continue or park, as the Gas Town report recommended.
4. **Avoid Gas City's bugs:**
   - a timeout or exit 75 must not burn an attempt;
   - kill the whole process group;
   - a missing check script fails loudly.

- **Fit:** extends `host-owned-completion` from "the commit is correct" to "the task is
  accepted". Receipts stay proof, never a reason to skip, per
  `receipts-prove-before-they-skip`.

### R4. A typed, durable, sequenced event log (core)

Addresses #5 · M

- **The log.** A Rust-owned, append-only log with a per-host sequence number and a typed
  payload registry. Add a test that every event kind has a schema.
- **Retention.** Rotation into archives that replay can still read.
- **CLI.** `sase events [--follow] [--after N] [--type …] [-j]`.
- **Gateway.** Back the gateway's SSE stream with this log so `Last-Event-ID` survives a
  restart.
- **First events to emit:**
  - agent lifecycle;
  - bead created and closed;
  - gate created and answered;
  - ToolRun verdicts;
  - landing outcomes (R1);
  - scheduler jobs fired.

### R5. Cron and event triggers that can fire workflows

Addresses #4 · S–M · depends on R4 for event triggers

- **New triggers.** Add `trigger: cron` (5 fields plus a time zone) and `trigger: event`
  (a type filter and a durable cursor) to scheduler jobs.
- **Workflow targets.** Let a job launch a standalone workflow with variables, under the
  same admission and autonomy controls. Today's prohibition exists only because no
  durable run model exists (see R2).
- **Default reactive jobs:**
  - an orphaned-claim sweep: a bead claimed by a dead agent triggers a notification or
    reopen;
  - a stale-gate re-notify that escalates channels (the Gas Town report's R4);
  - spawn-storm detection;
  - a notification when a blocker closes.

### R6. Make an epic phase a method, and add real fan-out to workflows

Addresses #6 · M

- **A method per phase.** `sase bead work` accepts an item workflow per phase, for example
  implement → check → review loop. Today's `bd/work_phase_bead` prompt stays the default.
- **Parallel fan-out.** Add `for: … parallel: true`, which launches separate SASE agents
  in their own workspaces under runner-slot admission, then joins their results.
- **Step overrides.** Same-id overrides of steps through `extends` or overlays, as in the
  Gas Town report's R9.

### R7. Multi-provider review lanes with a synthesizer, shipped as a macro

Addresses #3 and #6 · S → M

- **Step 1, possible today.** Ship a `review_lanes` macro: `%{%m:… | %m:… | %m:…}`
  reviewers, a `%wait` on the clan, then a synthesizer.
- **Step 2.** Add `model:` to mentor profiles, plus an optional synthesizer and a `check:`
  loop (R3) that runs until approved.
- **Humans keep the default.** Accepting comments in the TUI stays the default.

### R8. Data-only method packs with versioned imports

Addresses #7 · M

- **Format.** A directory or git subdirectory bundling macros and workflows, skills,
  scheduler jobs, doctor checks and file hooks.
- **Imports.** Declared through `imports:` in `sase.yml`, each with a source, a version or
  `sha:` pin, and a lockfile.
- **Namespacing and discovery.** Macro names are namespaced by binding. The existing
  GitHub-topic catalog serves as the registry.
- **Code stays in plugins.** Python plugins remain the home for code.

### R9. Project-contributed doctor checks with fixes

Addresses #11 · S

- **Format.** `sase/doctor/<name>/{check.yml,run.sh,fix.sh}`, surfaced by `sase doctor`
  and offered by `--fix`.
- **Scope.** This also gives the Gas Town report's R11 (a typed repair catalog) a natural
  extension point.

### R10. Route ready beads to roles within a launch budget

Addresses #8 · M · overlaps the Gas Town report's R6

- **Routing config.** Map a bead's `task_type` or labels to a role macro, a model alias,
  and a maximum concurrency.
- **Dispatch job.** A scheduler job launches agents for ready beads within that budget.
  An autonomy rule decides which types skip LaunchApproval, and every auto-launch is
  logged.

### R11. An ACP provider adapter

Addresses #9 · M

- **What.** One generic adapter for agents that speak the Agent Client Protocol, giving
  structured events without tmux.
- **Plus:** config-only presets for CLIs that have a headless JSON mode.

### R12. Dollar cost estimates and optional OTel

Addresses #12 · S–M · low priority (the Gas Town report's R13)

- **Cost.** A configurable pricing table joined to `usage.json`.
- **OTel.** Export only once a consumer exists.

### R13. Small governance borrowings

Addresses #13 · S

- **The capability ladder** as one line in the relevant memory note: prompt → config →
  compose → adapter → new core surface.
- **Executable quick-start docs.** Run the `docs/start/` steps as scripted CI scenarios.
- **Evidence in landing audits.** "Tests pass" must name the required gate that actually
  covers the changed paths.

### Explicitly not recommended

- **Long-lived tmux sessions,** `send-keys` nudges, and pane-text heuristics.
- **Always-on pools of sessions.**
- **Dolt.**
- **"Zero hardcoded roles" absolutism.** SASE's built-in roles (lander, triage, mentor) are
  fine as overridable macros.
- **Dropping skills or memory** in the name of "the model is the skill system". Gas City
  itself contradicts that rule.
- **A fresh session for every small step.** It multiplies cost; Every's reviewers report
  a six-step job costing up to six times one session.
- **A hosted service protocol** before there is a hosted product.
- **Migrating to Bazel.** The transferable idea is content-addressed, cached verification,
  and that waits on the hermeticity proof `receipts-prove-before-they-skip` requires.
- **Taking Gas City's docs at face value.** Verify against code first.

### Sequencing

1. **Now:** the R1 ruleset, then the R1 queue trial.
2. **Next:** R2, then R3. Together they make unattended epics safe.
3. **Then:** R4 and R5, then R6 and R7.
4. **Later, as need appears:** R8 through R13.

**Measure success with a repeated workload.** Run the same mix each time:

- independent tasks;
- one dependency chain;
- one injected crash mid-workflow;
- one failed phase;
- one gated decision.

Track red-`master` hours, human interventions, work lost to crashes, re-run cost, and time
from finished to landed.

## Sources

**Gas City** @ `45c804d59e`, opened with `sase repo open gh:gastownhall/gascity`:

- **Overview and rules:** `AGENTS.md`, `ROADMAP.md`, `CHANGELOG.md` (Unreleased), and
  `engdocs/contributors/{primitive-test,release-gate-criteria-conventions}.md`.
- **User docs:**
  - `docs/getting-started/{how-gas-city-works,faq,dashboard}.md`
  - `docs/guides/{understanding-formulas,understanding-packs,shareable-packs,registry-showcase,capabilities-for-coding-agent-users,multi-agent-engineering-environment}.md`
- **Engine code:**
  - `internal/dispatch/{runtime,control,ralph,retry,fanout,drain,crash_injection_test}.go`
  - `internal/formula/{compile,parser,types}.go`, `internal/molecule/molecule.go`
- **Controller code:**
  - `internal/orders/{order,triggers}.go`, `cmd/gc/{order_dispatch,dispatch_runtime,reconcile_latch,reconcile_mode,adoption_barrier}.go`
  - `internal/events/{events,recorder}.go`, `internal/api/event_payloads.go`,
    `internal/api/openapi.json`
- **Other code:** `internal/worker/builtin/profiles.go`, `internal/usage/usage.go`,
  `internal/pricing/pricing.go`, `internal/materialize/`, and `cmd/gc/main_test.go`
  (`TestTutorial01`).
- **Packs and CI:**
  - `internal/bootstrap/packs/core/{orders,formulas}/`
  - `.github/workflows/{ci,bazel,pr-evidence-watchdog,ci-verdict-watchdog}.yml`,
    `.bazelrc`, and `release-gates/` (517 files)
- **Live GitHub data, 2026-10-17:**
  - the `main` ruleset (`gh api repos/gastownhall/gascity/rules/branches/main`);
  - `gh run list` for `CI` on `main`, `CI` merge-group and PR runs, and `bazel.yml`;
  - the last 30 merged PRs.

**SASE** @ `5ea5fa5452`:

- **Docs:**
  - `docs/reference/workflows.md`, `docs/reference/work-units/bead-work.md`
  - `docs/reference/automation/{scheduler,scheduler-jobs,mentors,monitors}.md`
  - `docs/reference/integrations/{plugins,mobile-gateway,remote-dispatch}.md`,
    `docs/contribute/mobile-gateway-api.md`
  - `docs/reference/agent-auto-restart.md`
- **Code:**
  - `src/sase/macro/{workflow_executor,workflow_executor_loops,workflow_executor_parallel}.py`
  - `src/sase/bead/{work_prompt,macros}.py`, `src/sase/axe/{run_agent_exec,chop_runner_policy}.py`
  - `src/sase/logs/run_log.py`
- **Decision records:** `decisions:{ci-two-speed-split,single-turn-agents,host-owned-completion}`.
- **Live data:**
  - `gh run list` for Master Gate on `master` (last 60 runs);
  - `gh api repos/sase-org/sase/rules/branches/master`;
  - `sase bead search`.

**Prior research:**

- `research:202610/gascity_software_factory_purpose_and_vision/gascity_software_factory_purpose_and_vision.md`
- `research:202610/gastown_vs_sase_lessons_to_borrow/gastown_vs_sase_lessons_to_borrow.md`
  (its R1–R14 are cross-referenced above)
- Every's review (Katie Parrott, 2026-05-19), as cited in the Gas City purpose report, for
  the six-times cost observation.
