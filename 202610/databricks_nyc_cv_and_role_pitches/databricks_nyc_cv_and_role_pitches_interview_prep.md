# Interview-prep pack: Databricks NYC (Agent Quality and AI Platform)

> **Question:** What can Bryan rehearse, from SASE decisions and Agent Quality
> literature, so the Staff Agent Quality (`8842963002`) and Sr. Backend AI Platform
> (`8379331002`) loops have design stories and eval vocabulary ready?
>
> **Evidence:** decisions `single-turn-agents`, `host-owned-completion`,
> `triage-annotates-does-not-change-exit-codes`, `rust-core-required`,
> `ci-two-speed-split`, `check-full-is-explicit`; commit `62a8b95c72`; sase docs at
> `@20ddc1b154`; MLflow GenAI eval docs; Zheng et al. 2023; Chen et al. 2021.
>
> **Recommendation:** Rehearse the six cards as spoken answers. Lead Agent Quality
> with ToolRun records, triage that never masks an exit code, and the gap: **SASE
> has no task-success eval of real agents** (`eval_pilot = skip`; `fakey` is
> conformance). Lead AI Platform with the provider contract, host-owned completion,
> and the Rust-core boundary. Do not draft why Bryan left Google; only he knows.

Companion to [`databricks_nyc_cv_and_role_pitches.md`](databricks_nyc_cv_and_role_pitches.md).
Checked 2026-10-10 against this checkout and the decision records above.

## Claims to defend first

From the original report. Fold them into the cards:

- **Isolation is not OS sandboxing.** Numbered git clones (`README.md`). Providers
  get approval-bypass by default (`tmux_agent.bypass_permissions: true`,
  `docs/configuration.md`; `--dangerously-skip-permissions`). `+home` "sandbox" is
  a project tag. Omnigent's OS sandboxes and credential proxy are stronger; say so
  first. The CV never says "sandbox".
- **Adoption is operation, not traction.** 5★ / 1 fork vs Omnigent ~10.7K★. Pitch
  the live control plane, not a user count.
- **Rust is a boundary.** Litmus test (`docs/rust_backend.md`,
  `decisions:rust-core-required`): if another frontend must match the TUI, it
  belongs in `sase-core`. Much of that crate is agent-written.
- **Agent-written volume is reliability.** ~11.8K SASE commits since 2026-05-01
  (original report) is a host-owned-completion / ToolRun / triage story.

## Design-story cards

Claim, rejected alternative, cost, reopen condition, evidence, 45–60s spoken
version, likeliest follow-up.

### 1. Single-turn agents

- **Claim.** One provider turn. Continuation is a mechanism that terminates the
  runner (`sase monitor`, `/sase_handoff`, `/sase_plan`, `/sase_questions`).
- **Rejected.** Sleep/poll in place; native cron; long-lived daemons. All assume
  the process survives. Experiment: `b20637f4f` detached-only, reversed `ac5d95810`.
- **Cost.** Every durable wait needs mechanical infrastructure.
- **Reopens when.** True suspend/resume that keeps workspace claims and budget
  (`decisions:gates-never-block`). None exists.
- **Evidence.** `decisions:single-turn-agents`; `docs/monitors.md`.
- **Spoken (45–60s).** "In SASE an agent is one provider turn. When the runner
  captures it, the process is gone, so a background tool or a sleep loop cannot
  wake anyone. For 'run just check, then fix what broke,' the agent starts a
  monitor and ends. The monitor is a supervised OS command under the same
  workspace claim; a follow-up turn starts with the frozen result. We shipped
  detached-only runs in July and retired them in August because they fought the
  model. The cost is real plumbing for every kind of wait. I would reopen this if
  a platform offered suspend/resume that kept the claim and the budget. Until
  then, promising to keep running is a lie the model will tell itself."
- **Follow-up.** *Ceremony versus a long-lived agent?* A long-lived agent hides
  crashes, double-spends quota, and cannot prove which turn owned a file.

### 2. Host-owned completion

- **Claim.** The host's selected finalizers complete the turn. The agent submits
  one atomic declaration and never creates commits, branches, or PRs.
- **Rejected.** Provider stop-hooks; a hard-coded commit finalizer; prompt-selected
  executors; trusting self-report. `2f9c4ae29` made pluggable finalizers the only
  path.
- **Cost.** Protocol and evidence: plan before the turn, immutable context,
  independent postconditions.
- **Reopens when.** Soak shows the protocol is not paying for itself (flagged).
- **Evidence.** `decisions:host-owned-completion`. Why agent-written volume is a
  reliability claim.
- **Spoken (45–60s).** "The agent never commits. It writes one declaration: which
  repos, what message, whether the assigned bead closes. Host finalizers — commit,
  bead close, and the rest — run after the turn, each verifying its own
  postcondition. If I let the model run git commit, I cannot tell a successful
  turn from a model that said it committed. The cost is ceremony: a manifest,
  independent checks, refusal with a reason when a postcondition fails. I would
  reopen it if that protocol stopped earning its keep. Until then I will not say
  'the agent shipped a PR'; the host did, from evidence the agent supplied."
- **Follow-up.** *Land a fix mid-turn?* It edits the tree and declares. A monitor
  or handoff ends the turn; the successor sees the dirty tree. No in-turn git
  write path for agents.

### 3. Triage never changes an exit code

- **Claim.** ToolRun triage annotates NEW / KNOWN / FLAKY / UNKNOWN and never
  changes the exit code. KNOWN needs an independent witness; thin evidence is
  UNKNOWN. `run_silent --finish` still returns the first continued failure's code.
- **Rejected.** Bead-owner → KNOWN; merge-base redness as enough; rerun chains;
  always-continue.
- **Cost.** Continued runs take longer; thin ledgers stay UNKNOWN-heavy.
- **Reopens when.** FLAKY costs >~2h/week of manual reruns; UNKNOWN stays above
  ~40%; a KNOWN label lacks a witness.
- **Evidence.** `decisions:triage-annotates-does-not-change-exit-codes`;
  `docs/tool.md`. The CV's "trustworthy, reproducible signals" line.
- **Spoken (45–60s).** "Every named check becomes a ToolRun: fingerprints before
  and after, normalized failure signatures, a verdict — NEW, KNOWN, FLAKY,
  UNKNOWN. KNOWN needs an independent witness on another run or machine, not
  'this looks like a bead I filed.' The verdict never rewrites the exit code.
  Agents may continue past stages that are only KNOWN or FLAKY, but the recipe
  still exits with the first failure's code. You can keep working behind
  witnessed master-red, and CI still sees red. I rejected mapping a failure to a
  bead and calling it KNOWN, because ownership is a suggestion. If someone asks
  whether we mask flakes, the answer is no."
- **Follow-up.** *Quarantine or skip?* Skip deletes the signal. Quarantine often
  flips the job green. We keep the code and attach a label.

### 4. The Rust core boundary

- **Claim.** Shared deterministic backend lives in `sase-core` via `sase_core_rs`.
  No `SASE_CORE_BACKEND` switch, no Python reimplementation of a ported operation.
- **Rejected.** All-Python (frontends diverge). All-Rust (loses plugins, FS side
  effects, TUI). A dispatcher with a Python fallback (paths silently disagree).
- **Cost.** Strict loader, pinned `sase-core-rs` window, two coordinated commits.
- **Reopens when.** Duplicated adapters or wire-version churn dominate — not a
  preference for writing the next feature in Python.
- **Evidence.** `decisions:rust-core-required`; `docs/rust_backend.md`. Claim the
  litmus test, not hand-written depth.
- **Spoken (45–60s).** "Before I write a feature I ask: would a web app, an editor
  plugin, or another CLI need this to match the TUI? If yes, it goes in Rust, in
  sase-core, and Python only adapts. Layout, keybindings, one-off glue stay in
  Python. We had a dispatcher with a Python fallback and the two implementations
  drifted, so I deleted the fallback. The cost is a hard wheel pin and two repos
  for one behavior change. I will not pretend I typed every line of sase-core;
  agents write a lot of it under the same host-owned completion rules. What I
  will defend is the boundary, because that is what keeps a mobile client and the
  TUI from inventing two truths."
- **Follow-up.** *Why not Go, or all-Rust?* Go was never the runtime. All-Rust
  drops the plugin surface and Textual. The split is "must match across
  frontends," not language prestige.

### 5. Two-speed CI (and explicit-only check-full)

- **Claim.** Master push runs Master Gate (`master-gate.yml`): per-SHA,
  never-cancelled, lint plus eight shards of the non-visual fast suite.
  Exhaustive Full CI (`full.yml`) runs every two hours off the push path.
  `ci_watch` wants this SHA's gate green and a recent Full CI. Agents run
  `just check` unless the prompt names `just check-full`.
- **Rejected.** `queue: max` on master; per-SHA concurrency on full `ci.yml`;
  cancel-in-progress on master; merge queue; every-Nth commit; diff-scoped CI
  selector; `just check-full` as the default landing gate.
- **Cost.** Heavy-only regressions can wait ~2h. Flake-baseline and screenshot
  gates are no longer an agent default.
- **Reopens when.** Fast-gate p50 no longer fits cadence, heavy lane catches
  misses often enough, or the check heuristic is wrong.
- **Evidence.** `decisions:ci-two-speed-split`; `decisions:check-full-is-explicit`;
  `docs/development.md`; `docs/fakey.md` (deterministic provider on the real path).
- **Spoken (45–60s).** "We split CI because the host, not the tests, was the
  constraint. Every master SHA gets a fast gate that a newer push cannot cancel,
  sharded eight ways. The heavy lane — visual, performance floors, the rest —
  runs on a two-hour schedule. Release waits for both: this SHA's gate, and a
  fresh Full CI. Agents run just check, not check-full, unless someone names the
  full recipe. Making landers run the heavy suite turned flake-baseline and
  screenshot drift into epic blockers. The cost is detection lag. I would reopen
  it if the heavy lane were where we actually found regressions, often. fakey is
  the other half: it drives real provider plumbing with no model, so the fast
  gate can be deterministic."
- **Follow-up.** *Ship without the full suite?* We ship with a per-SHA fast signal
  and a freshness check on the exhaustive lane.

### 6. Crash-safe settlement

- **Claim.** Once a monitored command's outcome is frozen (status, exit code,
  reason, `command_ended_at`), a later bookkeeping crash resumes that observation.
  It does not rerun the command or SIGTERM a group that already exited.
- **Rejected.** Treat any dead supervisor as `lost` and kill leftover groups;
  rerun on resume; recover follow-up policy by running it twice.
- **Cost.** Settlement must tell "never observed" from "observed, then the
  bookkeeper died," including across reboot. Python consumes the Rust-frozen row.
- **Reopens when.** A frozen row disagrees with the process, or resume reruns a
  command that already had a side effect.
- **Evidence.** `62a8b95c72`; `docs/monitors.md` (`begin_proc_settlement` in the
  Rust proc store).
- **Spoken (45–60s).** "A monitor is a supervised command whose result has to
  survive the supervisor dying. Rust freezes status, exit code, reason, and end
  time under the same lock that moves the proc into settling. If settlement then
  crashes, resume reads that row. It does not run the command again. It does not
  SIGTERM a group that already exited — we had a bug where leftover-group cleanup
  fired after the child was gone. Lost means we never observed the command, so we
  must not invent an exit code. I landed this as 62a8b95c72: consume the frozen
  outcome, skip leftover SIGTERM when the command already exited, reuse
  command_ended_at as the result identity, recover follow-up policy once. For
  Agent Quality this is the same idea as not double-counting a trace: the
  observation is the source of truth, not the retry."
- **Follow-up.** *How do you test a bookkeeper crash?*
  `tests/test_ops_settlement.py` and `tests/monitor/test_monitor_proc_settlement.py`
  inject a frozen row and a dead supervisor and assert the command is not
  relaunched.

## Agent Quality topic brief

**SASE has no task-success eval of real agents.** `eval_pilot = skip`, so that
gap is still Bryan's. `fakey` scores harness conformance. ToolRun triage scores
check/test reliability. Neither is "did the agent complete the task."

### Trace-based evals

**Primer.** A trace is one agent or LLM execution: spans, I/O, timing, tokens.
MLflow's loop is dataset + scorer + predict_fn (or pre-logged traces):
`mlflow.genai.evaluate(...)` attaches scorer feedback to traces. Evaluation
Datasets are the test database
([eval-monitor](https://mlflow.org/docs/latest/genai/eval-monitor/)). Production
shape: `mlflow.search_traces()` then `evaluate(data=traces, scorers=...)`
([evaluations](https://mlflow.org/genai/evaluations)).

**SASE.** Closest verified object is a **ToolRun** (`docs/tool.md`): named tool,
argv, stage timings, before/after fingerprints, retained logs, triage verdict.
That is a *check* record, not an LLM trajectory. LLM Calls (`docs/ace.md`) are
the Agents-tab view of provider activity, not an eval dataset. SQLite telemetry
(`docs/telemetry.md`) is process metrics. Do not call ToolRuns "MLflow traces."

**Ask.** "When a Genie Agent fails, is the stored unit a whole session, a single
tool span, or a scored trace you can re-eval without re-running the agent?"

### LLM-judge failure modes

**Primer.** Zheng et al. 2023 (arXiv:2306.05685, NeurIPS D&B): a strong judge can
match human agreement (~80%) and still show **position bias** (A/B order flips
the winner), **verbosity bias** (longer scores higher), **self-enhancement**, and
limited reasoning. Mitigations: swap order and keep consistent verdicts; pin the
judge; prefer code-based scorers when a check is executable. MLflow tells you to
pin `MLFLOW_GENAI_JUDGE_DEFAULT_MODEL`
([regression testing](https://mlflow.org/docs/latest/genai/eval-monitor/regression-testing/)).

**SASE.** No LLM judge on agent output. Triage is rule-plus-witness. `fakey`
never calls a model. Honest analogue: we refused a judge for exit-code decisions
because a judge can be argued with and an exit code cannot.

**Ask.** "How do you measure judge position and verbosity bias on the Genie eval
set, and do you pin the judge independently of the candidate model?"

### Nondeterminism, repeated trials, pass@k

**Primer.** Chen et al. 2021 (arXiv:2107.03374) defined **pass@k** on HumanEval:
P(at least one of *k* samples passes), estimated unbiased from *n ≥ k* samples.
Codex: 28.8% on one sample, 70.2% at 100. A single pass@1 is not a reliability
number. Keep timeouts and failed runs in the denominator.

**SASE.** Real runs vary by harness, model, and prompt. We do not compute pass@k.
What we freeze: start commit (workspace clone), command argv (ToolRun), and —
after `62a8b95c72` — the monitor's observed exit. `fakey` makes *plumbing*
deterministic. A future task-success pilot should freeze those three, repeat a
subset, and report pass@k with failures in the denominator (original report
item 4).

**Ask.** "For Genie, is the published quality number pass@1, pass@k, or a judge
mean, and are failed and timed-out trials in the denominator?"

### Production traces → regression sets

**Primer.** MLflow splits *measurement* (dataset score: correctness 82%) from
*gating* (this known failure must not return). Loop: trace production → capture a
thumbs-down → pin the input as `@mlflow.test` → `evaluate` + assert
`result.passed` → run it in CI like pytest. Grow the suite from real failures
([regression testing](https://mlflow.org/docs/latest/genai/eval-monitor/regression-testing/)).

**SASE.** Closest loop: failed `just check` → ToolRun → triage classifies the
signature → KNOWN needs an independent witness → later matching runs are labeled,
not deleted. That is harness-failure regression, not agent-behavior regression.
There is no "this coding task used to pass" suite over real agents. Building one
is the skipped eval pilot.

**Ask.** "What fraction of Genie regression tests were authored a priori versus
promoted from a production trace, and who is allowed to promote one?"

## Sources

If a card's cost or reopen condition has moved in `sase/memory/decisions/`, trust
the decision record. Do not draft why Bryan left Google.

- Decisions (`sase memory read`, 2026-10-10): `single-turn-agents`,
  `host-owned-completion`, `triage-annotates-does-not-change-exit-codes`,
  `rust-core-required`, `ci-two-speed-split`, `check-full-is-explicit`.
- sase `@20ddc1b154`: `README.md`, `docs/tool.md`, `docs/monitors.md`,
  `docs/fakey.md`, `docs/telemetry.md`, `docs/development.md`,
  `docs/rust_backend.md`, `docs/configuration.md`, `docs/plugins.md`.
- Commits: `62a8b95c72` (frozen monitor outcomes); `b20637f4f` / `ac5d95810`
  (detached-run experiment); `2f9c4ae29` (finalizers-only completion).
- Original report in this directory (claims to defend; application-plan item 4).
- [MLflow GenAI eval](https://mlflow.org/docs/latest/genai/eval-monitor/),
  [regression testing](https://mlflow.org/docs/latest/genai/eval-monitor/regression-testing/),
  [evaluations](https://mlflow.org/genai/evaluations).
- Zheng et al. 2023, arXiv:2306.05685; Chen et al. 2021, arXiv:2107.03374.
