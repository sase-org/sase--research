# Gas City vs. SASE: where Gas City is ahead, and what SASE should borrow

*Researcher `mus` · 2026-10-17 · one of five independent swarm reports*

**Snapshots compared**

| Component | Revision | Notes |
| --- | --- | --- |
| Gas City (`gastownhall/gascity`) | `45c804d59` (2026-10-17 03:34 UTC) | `main` after v1.5.0 (tagged 2026-10-04). Opened with `sase repo open`. |
| SASE (`sase-org/sase`) | `28ced2a125` (`master`, 2026-10-17) | Primary workspace checkout. |

Gas City paths are relative to its repo root. SASE paths are relative to the SASE repo root. CI
numbers come from `gh run list` on 2026-10-17; each is labelled with its window.

---

## 0. Bottom line

1. **Gas City and SASE are different species, so most of Gas City's headline vocabulary is not
   where it is ahead.**
   - Gas City is a *factory platform*: long-lived tmux sessions, a Dolt-backed bead graph, a
     controller that reconciles declared agents to live sessions, and "zero hardcoded roles".
   - SASE is an *operator-centric software-engineering environment*: single-turn agents,
     host-owned completion, a memory and decision-record system, and a human in the loop through
     the TUI, gates and mobile.
   - Packs, mail, nudges, the Mayor and session adoption either have a SASE analogue already or
     cannot be borrowed without reopening `decisions:single-turn-agents`.
2. **Gas City is genuinely ahead in three places that SASE can use.**
   1. **It holds `main` green at high throughput, mechanically.** A merge queue, rulesets, a
      fail-closed PR evidence watchdog and a hermetic Bazel gate with remote execution run in
      about 5 minutes (§3.1). Over the last six days all **300 of 300** push-to-`main` Bazel runs
      were green, against **49 of 300** for SASE's Master Gate. This is the largest measured gap.
   2. **It executes verification and retry as data.** `check`, `retry`, `drain`, scope and finalize
      are control nodes run by a deterministic dispatcher, with typed failure classes and an
      "infrastructure outcome" that does not burn the retry budget (§3.2). SASE parks a failed phase
      for a human, and its verification is proof recorded at completion, not a loop the host drives.
   3. **A judgement-free controller, not an agent, owns convergence.** Gas City's principle is that
      "removing an `[[agent]]` entry must not break an SDK feature". SASE's service host and
      scheduler can adopt the same principle for *work graphs* without any long-lived agents (§3.3).
3. **There are seven further, smaller advantages.** These are a five-axis agent model with an
   upstream/endpoint axis and containerized runtimes; a typed event/API control plane with
   event-triggered automation; usage facts, a price table and reliability analytics; declarative
   packs with a registry and lockfile; reason-coded decision tracing; honest-docs conventions; and
   reach (§3.4–§3.10).
4. **Do not over-read Gas City's maturity.**
   - It has 1,561 open issues and PRs and ~57 commits a day.
   - Its keyed reconciler v2 is still opt-in (`default=legacy`).
   - Its nightly Tier B acceptance run failed on 52 of its last 60 runs (Aug 19–Oct 16). All 8 green
     runs are since Oct 8, and the last six nights (Oct 11–16) were green.
   - Its own spec has an "Accepted But Inert" section.
   - Its originator publicly gave up on reusable harnesses.
   - Treat it as a parts bin, not a reference architecture (§5).
5. **Top recommendations** (full ranked list in §6):
   1. Make the pre-land gate fast and mechanical: set a gate SLO, measure critical path, and reopen
      the `ci-two-speed-split` merge-queue rejection once the gate fits the cadence.
   2. Add verification-aware attempts to bead phases and workflows, with a "no verdict" outcome that
      does not consume the retry budget.
   3. Add a deterministic epic-convergence job on the scheduler's existing launch-proposal
      machinery.
   4. Add usage facts and a price table.

   Recommendations 1–3 compound: a fast gate makes retries affordable, and retries need typed
   failure classes.
6. **Relation to the Gas Town report** (`research:202610/gastown_vs_sase_lessons_to_borrow`). That
   report ranked an LLM-patrolled Refinery, liveness, failure policy and mail. This report finds
   that **Gas City solved the "keep master green" problem mechanically instead** (queue plus fast
   hermetic gate plus rulesets, no LLM judge). It also finds a more precise vocabulary for
   verification loops than Gas Town's formulas had, and several areas Gas Town never covered
   (substrate axes, usage facts, packs, typed API).

---

## 1. Method, evidence tags, and limits

**What I did**

- Read the two prior reports through `sase artifact read`: Gas City's purpose and vision, and Gas
  Town vs. SASE. I took their verified facts as given and spent my effort on what they left open.
- Opened Gas City with `sase repo open gh:gastownhall/gascity` and read, in order: `AGENTS.md`,
  `ROADMAP.md`, `engdocs/architecture/{dispatch,health-patrol,orders}.md`,
  `docs/reference/specs/formula-spec-v2.md` (§0, §1.6, §3, §4), `engdocs/research/w-gc-004-…`,
  `engdocs/design/{usage-facts-v0,inline-ralph-v0,idle-session-sleep,session-reconciler-tracing,two-minute-ci-blacksmith}.md`,
  `engdocs/bazel-ci-budget.md`, `docs/guides/{configuring-an-agent,harness-recipes,shareable-packs,connected-clients}.md`,
  `docs/reference/{cli,trust-boundaries}.md`, `docs/runbooks/remote-hardened-city.md`,
  the dispatch package sizes, `.github/workflows/`, and `docs/reference/cli.md`.
- Checked each SASE-side claim in this checkout (docs, `src/`, `.github/workflows/`, `gh run list`).
- Pulled CI outcomes for both repos with `gh run list`.
- Read the SASE decision records `ci-two-speed-split`, `receipts-prove-before-they-skip`,
  `corpus-before-mechanism` and `single-turn-agents`.

**Process note.** I first read the two prior research reports with the file reader, before
re-reading them through `sase artifact read`. The audited re-reads are recorded. I used only the
audited command afterwards.

**Evidence tags**

| Tag | Meaning |
| --- | --- |
| **[shipped]** | In source with a production caller, or a documented CLI command that exists in `docs/reference/cli.md`. |
| **[measured]** | A number I computed from CI history today. |
| **[spec]** | Authoritative spec text ("Last verified" header) that I did not trace to a caller. |
| **[design]** | A proposal or design doc. It may not be built. |
| **[inert]** | Accepted by the parser or reserved in a registry, but nothing consumes it. |

**Not done**

- I did not install or run Gas City, and I did not benchmark any workload on either system.
- Throughput claims about Gas City's internal fleet are the maintainers' own (see the vision
  report).
- CI windows are short, and some are one day or one week. They show current state, not a long-run
  rate.

---

## 2. Two different machines

| Dimension | Gas City | SASE |
| --- | --- | --- |
| **Core bet** | "Orchestration is all you need": process knowledge becomes versioned configuration (packs, formulas) that a controller runs outside any session | "Completion is host-owned": an agent submits a declaration and host finalizers verify, commit and publish |
| **Agent lifetime** | Long-lived sessions in tmux or other runtimes, adopted after restarts; work survives, sessions are disposable | One provider turn per run; continuation is always mechanical (`decisions:single-turn-agents`) |
| **Work store** | Beads in Dolt (moving infra-class beads to SQLite) | Git event-stream beads in sidecars plus Rust-owned SQLite stores |
| **Graph engine** | Control dispatcher executes `check`, `retry`, `fanout`, `drain`, `scope-check` and `workflow-finalize` beads | Epics run in Kahn waves, one agent per phase plus a land agent. Typed macro workflows run in-process |
| **Who handles failure** | Orchestrator, by policy in the formula | A human, via `sase bead work` retry or `TaskTriage` |
| **Config unit** | Pack (TOML plus Markdown prompts, agents, formulas, orders, commands, doctor checks, skills, MCP) | Python plugin entry points (13 groups) plus YAML/Markdown macros |
| **Agent selection** | Five axes: harness × model × upstream × transport × runtime | Provider, model and effort, with size aliases and fallbacks |
| **Extension philosophy** | Primitive Test: atomic, still necessary with a 10× smarter model, transport not cognition | Rust-core litmus test plus immutable decision records with reopen conditions |
| **Human loop** | Mayor session, dashboard, escalation by mail | Durable non-blocking gates, autonomy profiles, TUI, mobile, Telegram |
| **Ops weight** | tmux mandatory, Dolt server, `bd`, a supervisor | `uv tool install`, a service host, no database server |

---

## 3. Where Gas City is ahead, ranked

Ranked by **measured size of the gap × relevance to SASE's current pain × confidence that Gas City's
version actually works**.

### 3.1 A gate that keeps `main` green at high throughput (rank 1)

**Gas City** [shipped, measured]

- **Never push to `main`.** `AGENTS.md`: "Branch from `main` … push to your branch — never to
  `main`." The pre-push hook runs `bazel test //...` (`AGENTS.md`, Build and test).
- **A merge queue.** `.github/workflows/bazel.yml` and `ci.yml` trigger on `merge_group`
  (`checks_requested`). The queue ref "is already the merge", so the gate runs against the exact
  integrated tree, and the OpenAPI gate diffs against `merge_group.base_sha`.
- **Rulesets.** Four exist: "Protect release tags", `main`, "hotfix and release branches: CI /
  required", and "release and hotfix lines from v1.6: Bazel gates".
- **Fail-closed evidence.** `.github/workflows/pr-evidence-watchdog.yml` fails a PR whose head commit
  "never produces complete CI evidence". It runs under `pull_request_target` and never executes PR
  content. `ci-verdict-watchdog.yml` is a sibling.
- **A fast hermetic gate.** Bazel with remote execution and caching. `engdocs/bazel-ci-budget.md`
  sets a goal of **`bazel test //...` ≤ 60 s at steady state** and tags every number by cache tier
  (T1 warm, T2 cold client, T3 cold farm). It has a formal decision rule: if
  `gap = elapsed − critical_path` is under 15% of elapsed, attack the longest critical-path
  component; otherwise attack farm capacity. In the doc's own table, one flag (`--jobs=64`) took CI
  from 841 s to 167 s because a 2-vCPU runner capped remote actions at 2 in flight.
- **A named SLO program.** `engdocs/design/two-minute-ci-blacksmith.md` [design] plans
  planner-driven sharding from historical timings and 45–75 s shards.
- **Ratchets as CI jobs.** `complexity.yml`, `cmd/openapi-breaking`, the `check-core-boundary.sh`
  script, `docs-render.yml` and `govulncheck.yml`.

**Measured outcomes** (`gh run list`, 2026-10-17)

| Metric | Gas City `bazel.yml` | Gas City `ci.yml` | SASE Master Gate |
| --- | --- | --- | --- |
| Push to default branch, green | **300 / 300** (Oct 11–17) | 13 / 13 | **49 / 300** (Oct 10–17) |
| Merge-queue runs, green | 23 / 24 (median 273 s) | 13 / 13 (median 57 s) | no queue |
| PR runs, green first time | 49 / 54 (median 301 s) | 34 / 34 (median 104 s) | n/a (direct push) |
| Median wall time, last 100 completed | 288 s (push) | 56 s (push) | **747 s** |
| Exhaustive tier | Nightly Tier B: 8 / 60 green since Aug 19, all since Oct 8, and **green on the last 6 nights (Oct 11–16)** | | Full CI: **0 / 40** green, median **6,566 s** |

**SASE today** [measured, plus the 2026-10-01 report]

- Master Gate runs *after* the push. The last 100 completed runs (Oct 14–17) were 23 green, with a
  median of 747 s.
- The 2026-10-01 report found 42% of pushes landing before the previous push's gate finished, `sase
  final submit` recording `verdict_provenance: "unverified"`, and no branch protection or rulesets.
- The decision record `ci-two-speed-split` rejected a GitHub merge queue and larger or self-hosted
  runners. It reopens "when the fast gate's p50 wall time stops fitting the commit cadence". On
  those numbers, a 12.5-minute p50 against the 14.7-minute median push gap recorded on Oct 1 is
  close to that line. I did not recompute the gap for this week.
- SASE already shards the fast suite into eight timing-balanced shards
  (`.github/workflows/master-gate.yml`, `tests/shard_timings.json`, `shard-timings-ratchet.yml`).

**Why it matters.** Every unattended-work feature (epics, jobs, auto-launch) multiplies landings.
A gate that cannot refuse red makes each extra landing worse. Gas City shows the combination that
works at ~57 commits a day: *a short required check, run on the exact integrated tree, behind a
queue, enforced by rulesets*.

**Caveats**

- **Push-to-`main` green is by construction.** With a queue, a red change never reaches `main`, so
  300 / 300 is the expected result. The informative numbers are the queue's 1-in-24 rejections and
  the PR first-pass rate.
- **The speed comes from infrastructure SASE does not have.** Gas City runs its own remote-execution
  farm (`rbe-worker-pool.yml`, `rbe-fork-pool.yml`, a Blacksmith partnership) on a hermetic Bazel
  build of a Go repo. SASE is a Python plus Rust repo on GitHub-hosted runners, and
  `ci-two-speed-split` records that bigger and self-hosted runners were tried and did not settle
  the tip.
- **Its slow tier has been red too.** Nightly Tier B failed on 52 of its last 60 runs, with no green
  before Oct 8. Gas City's fast gate stays green partly because the slow tier is separate, which is
  the same trade SASE made.
- **The windows are short** (the 100 Bazel runs span about 16 hours).

**One genuine opening for SASE.** `receipts-prove-before-they-skip` found **0** already-passing
repeats among 527 fingerprinted `check` runs, so whole-command reuse has no opportunity. That
measures *whole-command* repeats. Bazel's remote cache hits at *target* granularity, where partial
repeats are the norm (a commit touches a few files, so most shards' inputs repeat). Whether SASE's
shards or test files show per-unit repeat rates that justify a per-unit cache is a hypothesis that
needs measuring, not a finding.

**Confidence.** High that the gap is real and large. Medium on how much of it SASE can close
without Bazel.

### 3.2 Verification and retry as orchestrator-executed data (rank 2)

**Gas City** [shipped; spec last verified 2026-06-12]

The v2 compiler turns a formula into a workflow root, ordinary step beads, and **control beads**.
The control dispatcher in `internal/dispatch` (about 10,000 non-test lines: `runtime.go`,
`control.go`, `drain.go`, `ralph.go`, `retry.go`, `fanout.go`) executes every control bead. "No
agent participates in control execution" (`docs/reference/specs/formula-spec-v2.md` §0.2).
Specific semantics worth studying:

- **`check` (§3.1).** After each iteration closes, the orchestrator runs a script.
  - Exit 0 closes the step; any other nonzero is a "not yet" verdict that appends the next
    iteration, within `max_attempts`.
  - **Exit 75 (`EX_TEMPFAIL`) means "I could not reach the infrastructure to tell".** It is recorded
    as an infrastructure outcome and *does not consume an attempt*. It is bounded by a separate
    infrastructure budget, so it still terminates.
  - A script that cannot be launched leaves the step *open* (not failed) and emits a single
    `control.stalled` event after 15 minutes, because "the fix is out of band".
- **`retry` (§3.2).** The orchestrator classifies each closed attempt as `pass`, `hard` or
  `transient`. `on_exhausted = soft_fail` closes the step as a pass with
  `gc.final_disposition = soft_fail`, so downstream work continues "with degraded coverage".
- **Attempts are appended beads under a stable logical step** (`<step>.attempt.N`,
  `<step>.iteration.N`). Downstream `needs` point at the logical step, so retries never reopen old
  work (`engdocs/design/inline-ralph-v0.md`).
- **`drain` (§3.3).** It scatters a convoy into one-member unit convoys and runs an item formula per
  unit. It is bounded to 1–100 units, has `on_item_failure = skip_remaining | continue`, and
  `member_access = exclusive` takes a per-member reservation.
- **Scopes (§3.5).** `abort_scope` is fail-closed: a member that declares it and closes with a
  missing outcome counts as failed. Teardown work runs *after* settlement and may read the final
  outcome, so "clean up on pass, preserve the workspace on fail" is expressible.
- **Close-ownership invariant.** The compiler rejects any graph where a node is blocked by the
  control bead that closes it, because the store refuses to close a blocked issue and the graph
  would deadlock.
- **`workflow-finalize`.** It closes the root first, so a crash retries finalization. Failures
  deliberately leave parent source beads open.

**SASE today**

- **Epic failure parks for a human.** A failed phase leaves its dependents and the land agent
  parked. Recovery is a human `sase bead work` retry (`docs/reference/work-units/bead-work.md`).
  The standalone-task path waits for `TaskTriage`.
- **Verification proves but does not loop.** The commit finalizer records fingerprint-bound receipts
  (`decisions:receipts-prove-before-they-skip`). The host never spawns the next attempt from a
  verdict.
- **Macro workflows are expressive but not durable.**
  - They have `if`, `for`, `while`, `repeat/until`, `parallel`, `finally`, HITL and typed
    cross-step field checking (`docs/reference/workflows.md`). Gas City's formulas have only
    compile-time `condition` filters and string-only variables (the `type` field is "parsed but not
    enforced", spec §1.4), so SASE's authoring surface is richer. The gap is durability, not
    expressiveness.
  - They execute in-process. `WorkflowExecutor.execute()` (`src/sase/macro/workflow_executor.py:201`)
    always iterates from step 0.
  - State is saved (`_save_state()`) and a per-step skip hook exists (`self._step_inputs`, line
    256), but there is no `resume` command.
- **Provider retries cover API errors, not task failure.** `llm_provider.retry` waits `[60, 300,
  1800]` seconds and may fall back to a cheaper model (`docs/reference/providers/retry-and-fallback.md`).

**A SASE data point for exit-75 semantics.** In the 2026-10-01 report, of the last 1,000 local
`just check` runs, 762 failed, **199 were killed by signal and 12 were lost**. Those 211 runs are
"no verdict", not "fail". Today they are indistinguishable from a real failure in any retry loop,
and they are exactly the class Gas City's exit-75 convention protects.

**Caveats**

- Gas City documents its own gaps: `until` loops run one iteration, `[steps.gate]` types are
  vocabulary only, `waits_for` modes are inert, `[steps.tally]` was removed, and the review-quorum
  Go finalizer "is not invoked by formula synthesis yet" [inert] (§4 of the spec,
  `engdocs/architecture/dispatch.md`).
- There is **no mid-step checkpoint** (`engdocs/research/w-gc-004-…`: work resumes at bead
  boundaries, not mid-tool-call).
- Every's review reported that a six-step job can cost about six single-session jobs, because each
  step starts fresh. SASE's per-phase agents have the same property.

**Confidence.** High on the mechanism. Medium on payoff, since SASE's epics are shorter than Gas
City's factory runs.

### 3.3 A judgement-free controller owns convergence (rank 3)

**Gas City** [shipped; mostly from `engdocs/architecture/health-patrol.md`, last verified 2026-05-29]

- The controller reconciles declared agents (`city.toml`) against live sessions on a 30 s tick plus
  `fsnotify` config reloads. A healthy session is skipped, a drifted one (SHA-256 config
  fingerprint) is drained and restarted, and an orphan is drained or killed.
- **Crash-loop quarantine** (`max_restarts` within `restart_window`) is in-memory and
  intentionally resets on a controller restart.
- **Zombie capture** reads pane output before restarting a dead agent.
- **Dependency-aware bounded parallel starts and force-stops**, in waves.
- Orders dispatch on their own lane. **Exec orders run with no LLM at all.**
- **Principles in `AGENTS.md`:** "SDK self-sufficiency — if removing an `[[agent]]` entry breaks an
  SDK feature, it's a violation", "no status files — query live state", and "redundant idempotent
  observers are the reliability mechanism".

**SASE today** [from the prior reports, plus `docs/reference/automation/scheduler*.md`]

- The service host restarts daemons, with PID and boot-time liveness and orphan-scope reaping.
- Update-skew auto-restart covers only pre-model-turn deaths.
- A `bead_claim_checks` reconciler exists for claims.
- Nothing continuously converges an *epic*. A killed or failed phase waits for a human.
- A provider wedged before declaring is a known blind spot (`docs/contribute/llm-invocation.md:378`).

**What transfers.** The tmux sessions and adoption do not. The *principle* does: a deterministic
loop compares desired state (the epic and its beads) with actual state (agent registry, claims,
bead statuses) and acts within budgets. SASE's scheduler already has the machinery for the action
half: jobs return schema-versioned `proposed_launches` with `dedupe_key`, `wait_on`, clans, models
and guards (`docs/reference/automation/scheduler-jobs.md`). A "converge epics" job is therefore
mostly new *detection* logic.

**Caveats.** Reconciler v2 is not the default (`internal/config/config.go:2805`,
`default=legacy`); 1.6's top priority is session reliability. `session.quarantined` is a reserved
event with no emitter. The Gas Town report's warning stands: automatic killers caused incidents,
so detection must be deterministic and generation-aware.

**Confidence.** High on the principle. Medium on which parts SASE needs.

### 3.4 A five-axis agent model and pluggable execution substrate (rank 4)

**Gas City** [shipped; `docs/guides/configuring-an-agent.md`, `harness-recipes.md`]

- **Five independent axes:** harness (`provider`), model (`option_defaults.model`), **upstream**
  (who serves the model), transport (`session`), and runtime (where it runs).
- **Upstream abstraction.** `[upstreams.bedrock] base_url / api_key / auth_token` renders onto each
  harness's own env vars (`ANTHROPIC_BASE_URL`, `OPENAI_BASE_URL`, …), so a Bedrock, proxy or vLLM
  endpoint works across harnesses. Secrets are `$VAR` references, never inline.
- **Sixteen built-in harness presets** (Claude, Codex, Gemini, Grok, Kimi, Kiro, Cursor, Copilot,
  AMP, OpenCode, Groq and Cerebras via OpenCode, Pi, Auggie, Oh My Pi, Antigravity), with
  inheritance (`[providers.fast] base = "builtin:claude"`).
- **Runtimes:** tmux, subprocess, exec (a user script as the provider, JSON on stdin), ACP,
  Kubernetes (`gc build-image` prebakes pods, so startup drops "from 30–60 s to seconds") and herdr.
- **`gc runtime conformance <executable>`.** A golden, requirement-coded (RPP-GROUP-NNN) suite for a
  third-party runtime, "kept honest by negative tests" in which a broken reference fails exactly its
  requirement's check.

**SASE today**

- Seven production providers plus the `fakey` test provider; model, effort and size aliases;
  fallbacks and usage-window routing. A third-party `sase_llm` entry point exists.
- **No endpoint axis.** `ANTHROPIC_BASE_URL` / `OPENAI_BASE_URL` appear nowhere in `src/`.
- **No container or sandbox runtime** (a targeted grep found none).
- **No requirement-coded conformance suite for providers.** `fakey` and
  `tests/test_vcs_provider_contract.py` are the nearest things.
- SASE's scale-out answer is different and strong for a personal fleet: `%dispatch` to your own
  machines through authenticated gateways (`docs/reference/integrations/remote-dispatch.md`).

**Why it matters.** The upstream axis is what makes Bedrock/Vertex/proxy deployments and enterprise
users possible. A runtime axis is where containment would live. The Gas Town report found that SASE
runs providers with approvals bypassed and no containment, relying on gates and host-owned pushes.

**Caveats.** Gas City's own `docs/reference/trust-boundaries.md` says its commands are "a feature,
not a sandbox", and a hardened city exposes a fully unauthenticated read plane. Containment is an
option there, not a delivered guarantee. Sixteen presets also means sixteen sets of CLI-UI
internals to keep working.

**Confidence.** High that the axes exist. Medium on value for a single-operator SASE.

### 3.5 A typed event and API control plane (rank 5)

**Gas City** [shipped]

- **Events.** An append-only, sequence-numbered stream (`.gc/events.jsonl`, `gc events --follow`,
  SSE). Every event type has a registered payload, enforced by
  `TestEveryKnownEventTypeHasRegisteredPayload`.
- **One API behind everything.** The CLI, the HTTP+SSE supervisor API and the embedded dashboard are
  "projections over the domain packages" (`internal/api/AGENTS.md`). The OpenAPI spec is generated
  and diffed for breaking changes in CI.
- **Event-triggered automation.** Orders fire on `cooldown`, `cron`, `condition` (a shell command
  exits 0), `event` (matching events after a cursor) or `manual`
  (`engdocs/architecture/orders.md`).
- **Webhooks.** Packages for sink, verification, matching and SSRF defence.
- **External messaging fabric** (`internal/extmsg`): provider-neutral conversation identity,
  bindings, scoped delivery contexts and HTTP adapters. `docs/guides/connected-clients.md` builds a
  voice client in a page.

**SASE today**

- A Rust mobile gateway with an SSE event stream, push hints and a committed API contract
  (`docs/reference/integrations/mobile-gateway.md`, `docs/contribute/mobile-gateway-api.md`).
- Scheduler job triggers are `always`, `git.commits_since` and `fs`, with `run_every` and
  `inhibit_if` guards (`docs/reference/config/scheduler.md:55–79`). Jobs are polled scripts.
- Telegram runs as job scripts (`sase_job_tg_outbound` / `_inbound`), with no provider-neutral
  conversation identity.

**Assessment.** The API gap is small (the gateway is a real typed API). The real gaps are
**event-triggered jobs** and a **chat-fabric abstraction**. The first is cheap (§6, R6).

### 3.6 Usage facts, a price table and reliability analytics (rank 6)

**Gas City** [shipped CLI; design doc `engdocs/design/usage-facts-v0.md`]

- `UsageFact` records (model tokens, cache tokens, compute wall-seconds) with idempotency keys and a
  write-only sink (`local` or `exec:<script>`), a transactional outbox, and a run identity resolved
  per operation from the acting work bead. The design explains why the "obvious" run id was wrong.
- `internal/pricing` and `gc costs` aggregate by run, flagging unpriced models rather than dropping
  them.
- `gc analyze reliability` reports crash, idle-kill and drain counts per **(model, prompt version,
  rig)**, with the denominator included. It turns production runs into evidence for choosing models
  and prompt changes.

**SASE today.** Usage windows and rate-limit probes (`src/sase/llm_provider/usage/`), per-model
attribution in the Admin Center statistics, and local SQLite telemetry. **There is no dollar cost
model and no pricing table** (greps found none).

**Why it matters.** SASE has already had a quota-burn episode (`research:202610/muse_quota_burn_2026_10_12`).
Any launch budget, auto-promotion or epic-convergence job (R3) needs a unit to budget in.

**Caveats.** Costs are list-price estimates. Gas City's pricing is Claude-heavy. The doc itself says
cost is "decision-support, not an authoritative charge".

### 3.7 Shareable declarative packs with a registry (rank 7)

**Gas City** [shipped]

- A pack is a directory: `pack.toml`, `agents/<name>/{agent.toml,prompt.template.md}`, `formulas/`,
  `orders/`, `commands/`, `doctor/`, `overlay/`, `skills/`, `mcp/`, `template-fragments/`.
- **Namespaced imports** with local bindings (`gastown.polecat` and `review.polecat` coexist),
  `version` constraints (`sha:…` pins), and a **lockfile** with **content hashes**
  (`internal/packman/{lockfile,install,check}.go`, `internal/packregistry/content_hash.go`).
- **A registry** (`gc pack registry search | show | publish | login | refresh`) and a release flow
  (`gc pack release validate | hash | stamp | verify`).

**SASE today.** Distribution is Python packages via entry points. Resource plugins can ship macros
and `default_config.yml` (`sase_macros`, `sase_config`), and `sase plugin install` fetches from a
catalog. There is no declarative-only bundle format, no version-pinned import with a content-hash
lockfile, and no publish flow for non-Python authors.

**Why it ranks low.** `decisions:corpus-before-mechanism` applies. SASE has no second external
consumer demanding bundles yet. Note this as a *watch* item, not a build.

### 3.8 Decision-grade observability: tracing (rank 8)

**Gas City.** `gc trace start | status | show | tail | cycle | reasons | stop` [shipped CLI]. The
design (`engdocs/design/session-reconciler-tracing.md`, "Proposed") records, per reconcile cycle,
*what* happened and *why the controller chose it*, with always-on compact summaries and
short-lived high-detail traces for chosen templates.

**SASE today.** ToolRun, receipts and `sase final status` explain completion decisions. The
scheduler, service host and admission queue explain themselves through logs and TUI panels.

**Assessment.** A reason-coded decision stream is a good debugging aid once R3 exists, because
convergence jobs make "why did it not relaunch?" the central question.

### 3.9 Honest-docs and guard-test conventions (rank 9, cheap)

- **"Accepted But Inert"** is a section of the formula spec (§4) listing constructs the parser
  accepts but nothing consumes.
- **"Last verified against code: <date>"** headers on architecture docs.
- **Guard tests named in `AGENTS.md`** (for example `TestGCNonTestFilesStayOnWorkerBoundary`,
  `TestAgentFieldSync`), and colocated `AGENTS.md` files per area (`internal/api/`,
  `internal/session/`, …).
- **A CI-enforced boundary for hosted logic** (`scripts/check-core-boundary.sh`).
- **Release gates as documents** (`release-gates/*.md`, with criteria conventions).

SASE already has decision records, a memory system, `tools/` ratchets and generated reference docs.
The genuinely new, cheap borrowings are the *inert* section convention and the *verified-on*
header with a staleness check.

### 3.10 Reach (rank 10, not a design advantage)

16 harness presets; Homebrew (`brew install gascity`); macOS CI (`mac-regression.yml`) and
Windows-specific code paths (`*_windows.go` files in several packages; I did not test them); about
1,400 stars, 447 forks, a public Discord and a dogfooding "Maintainer City"; and a commercial path (Beads Team Server, Gasworks, a vendor-neutral hosted protocol of which
only auth has shipped). SASE is single-operator, POSIX-only and installed with `uv`.

---

## 4. Where Gas City is *not* ahead

| Area | Verdict | Evidence |
| --- | --- | --- |
| Completion integrity | **SASE ahead** | Declarations, host-selected finalizers, rescue store, fingerprinted commit attempts. In Gas City, "done" is a CLI an agent runs, and its tests of merged results are LLM judgements in Gas Town's Refinery. |
| Human-in-the-loop | **SASE ahead** | Durable non-blocking gates, autonomy profiles, plan and epic approval, TUI, mobile and Telegram. Gas City's human surface is a Mayor session, mail and a dashboard. |
| Knowledge system | **SASE ahead** | Core, reference and web memory plus immutable decision records. Gas City's `AGENTS.md` permanently excludes a skills system ("the model IS the skill system"), though its PackV2 ships `skills/` and `mcp/` directories (a tension the vision report noted). |
| Typed workflows | **SASE ahead on expressiveness** | Typed inputs and outputs, cross-step type checking, `while`/`repeat`/`for`/`parallel`/`finally`, HITL. Gas City's variables are string-only, its conditions are compile-time, and its `until` loops are inert. |
| Provenance and verification evidence | **SASE ahead** | Commit footers, ToolRun ledger, verdict receipts, audited reads. |
| Admission control | **SASE ahead** | Weighted queue, holds with TTL, runner slots. Gas City scales pools through `scale_check` shell probes. |
| Goals | **SASE only** | Goal ledger with human settlement. |
| Operational weight | **SASE lighter** | No Dolt server, no tmux dependency. Gas City's runbooks for Dolt bloat, compaction and backup show the cost. |
| Scheduling and triggers | **Parity** | SASE jobs are polled but emit validated launch proposals with dedupe and `wait_on`. Orders add only `event`, `cron` and `condition` triggers. |
| Automated review | **Parity** | SASE mentors run focused reviewers with severities and apply flows. Gas City's `mol-review-quorum` is two read-only reviewer lanes plus a synthesis step, and its Go finalizer is not wired in. |
| GitHub PR repair | **Parity** | Gas City's `gc github pr backfill` makes repair beads for failed checks, conflicts and behind-base PRs. SASE has Patches, `ci_watch` and mentors. |
| Remote fleet | **SASE ahead for a personal fleet** | `%dispatch` over tailnet gateways. Gas City is ahead only for Kubernetes. |
| Mail and nudges | **Not a gap to copy** | Single-turn agents have no live session to nudge (see the Gas Town report's R5 for the single-turn-compatible half). |

---

## 5. Cautions: what Gas City's own record says

- **Maturity signals.**
  - 1,561 open issues and PRs (GitHub `open_issues_count`).
  - Reconciler v2 is still opt-in, and legacy is the default.
  - Storage migration (`gc storage migrate`) was flagged unsafe on production cities you cannot
    restore (vision report).
  - The 1.6 roadmap's first priority is crash-safe session reliability.
  - Six minor releases in about six months.
  - About 62% of `main` commits come from one author.
- **The slow tier has been red.** Nightly Tier B failed on 52 of its last 60 runs, with no green
  before Oct 8.
- **Documentation honesty cuts both ways.** The "Accepted But Inert" section is a strength, and the
  inert constructs themselves are a cost. `session.quarantined` and `session.suspended` are
  registered events with no emitter. `gc.detached` metadata has "no in-repo producer".
- **Security posture.** "A feature, not a sandbox." A hardened city's read plane is "FULLY
  UNAUTHENTICATED" and needs a network front. Trust is operator-level.
- **The reusable-harness thesis is contested by its originator.** Yegge's August 2026 essay says
  "I have given up on building reusable harnesses" and that Gas Town "fell apart at the seams".
  Every's review said "learn from the ideas, skip the toolkit for now". The review predates
  releases 1.3–1.5.
- **Persistence is not correctness.** Durable beads let a replacement session resume. They do not
  show the review was sound. This is why SASE's host-owned verification matters.

**Reading.** Copy the *mechanisms that survived* (queue plus fast gate, control-node semantics, a
judgement-free convergence loop). Do not copy the vocabulary, the storage, or the session model.

---

## 6. Ranked recommendations for SASE

Ranked by leverage × fit with SASE's decision records × size. Sizes: S ≈ days, M ≈ 1–3 weeks, L ≈ a
month or more. Items marked **(core)** belong in `sase_core` under `rust_core_backend_boundary`, with
thin Python and TUI adapters.

### R1. Make the pre-land gate fast and mechanical · from §3.1 · L, staged

1. **Set and publish a gate SLO.** For example, p50 ≤ 5 minutes and p90 ≤ 10 for the *required*
   tier. Report `elapsed`, `critical path` and `gap` for every Master Gate run, as
   `engdocs/bazel-ci-budget.md` does. Use its rule: gap < 15% means shorten the critical path,
   and gap ≥ 15% means add capacity. Adopt its cache-tier tagging (warm, cold client, cold farm) so
   the numbers stop lying.
2. **Do not migrate to Bazel as step one.** Take the measurement discipline and the shape: hermetic
   inputs, a content-addressed cache, timing-balanced shards (SASE already has eight, plus the
   timings ratchet), one build-and-test invocation, and a fixed prebuilt runner image.
3. **Measure per-shard and per-file input repeat rates** before deciding on any cache. The
   `receipts-prove-before-they-skip` finding (0 repeats at whole-`check` granularity) does not rule
   out finer-grained repeats.
4. **Add the cheap fences now:**
   - a ruleset protecting `master`, tags and release branches;
   - a fail-closed "no CI evidence for this SHA" check, in the style of `pr-evidence-watchdog.yml`;
   - a required status once a short required tier exists.
5. **Reopen the merge-queue rejection in a new decision record** once the gate's p50 sits well
   inside the commit cadence. `ci-two-speed-split` already names this reopen condition. Prefer
   *one* mechanical landing lane: the local lease, rebase, verify, push, prove lane from the Gas
   Town report's R1, or a GitHub queue. The queue is the proven shape at ~57 commits a day.
6. **Guardrails.** Refusals route through a gate and never name a bypass (the Gas Town report's
   lesson 5).

**Success measure.** Master Gate green rate on `master` pushes, red-minutes per week, and the share
of pushes that land before the previous gate finishes. Gas City's comparison point is 300 of 300 and
about 5 minutes.

### R2. Verification-aware attempts for bead phases and workflows · from §3.2 · M · (core)

1. **A `verify:` policy on a phase** (and an equivalent on a workflow step). After a phase agent
   finishes, the host runs the named check (for example `just check` or a project script). Exit 0
   closes the phase; a "not yet" verdict starts the *next attempt as a new, appended record* under
   the same logical phase, up to `max_attempts`. The next attempt receives the previous attempt's
   evidence (diff from the rescue store plus the failing output).
2. **A three-valued verdict.** `pass`, `fail` and `no_verdict`. `no_verdict` covers a check killed by
   a signal, lost, or unable to reach its infrastructure. It does not consume an attempt, but it is
   bounded by a separate budget so it still terminates. Define an exit code for scripts to opt in,
   following exit 75.
3. **Failure classes** (`hard` | `transient`) written by the finalizer, with `on_exhausted: park |
   soft_fail`. A `soft_fail` passes the phase with an explicit "degraded coverage" disposition that
   the lander must report.
4. **A check that cannot be launched** leaves the phase open and raises one stalled event after a
   timeout. It does not fail the phase.
5. **Workflow resume.** `sase workflow resume <run>` uses the recorded `workflow_state.json` and the
   existing `_step_inputs` skip hook.
6. **Compiler invariant.** Reject any epic or workflow graph that blocks a node on the thing that
   closes it (Gas City's close-ownership invariant).

**Fit.** The host decides; agents stay single-turn (`single-turn-agents`, `host-owned-completion`).
Receipts remain proof for host completion and never skip a run.

**Measure.** The share of failed phases resolved without a human, and the number of `no_verdict`
runs miscounted as failures.

### R3. A deterministic epic-convergence job on the scheduler · from §3.3 · M · depends on R2

- A scheduler job scans active epics each cycle, compares *desired* state (phases that should be
  running or done) with *actual* state (agent registry, claims, bead statuses, last progress), and
  emits `proposed_launches` for work that is stuck, lost or failed. It reuses `dedupe_key`, `wait_on`
  and `inhibit_if`.
- **Budgets** per epic and per day (attempts, launches, usage), with every action recorded in bead
  history. A crash-loop quarantine like Gas City's stops a bad phase from burning the budget.
- **No LLM in the detection path.** Notify first. Automatic relaunch only when configured.
- **Generation-aware identity** so a reaper never judges a previous session's state (the Gas Town
  issue #4890 lesson).
- **Fit.** The job proposes and the runner launches (the existing contract). Nothing waits.
  `gates-never-block` holds.

### R4. Usage facts and a price table · from §3.6 · M · (core)

- A `UsageFact`-style record per model turn (tokens, cache tokens) and per run (compute
  wall-seconds), with idempotency keys and a per-operation run id (take the lesson that a frozen
  per-session id misattributes reused workspaces).
- A configurable price table, with an `unpriced` flag instead of dropping or zeroing.
- `sase costs` and a reliability report per (model, size alias, prompt/macro version) with the
  denominator included.
- **Purpose.** It supplies the budget unit for R3, a launch-budget autonomy rule, and evidence for
  size-alias choices (`size-alias-effort-ladder`).

### R5. A conformance suite for provider adapters and plugins · from §3.4 · S–M

- A requirement-coded golden suite (`PRV-<GROUP>-NNN`) that any `sase_llm` provider can run
  (`sase provider conformance <ref>`), covering streaming, interrupt, resume, usage, retry
  classification and declaration delivery. Add *negative* tests that prove each requirement gates.
- Extend `fakey` into the reference implementation of the suite.
- **Why.** SASE has seven providers, each with turn-integrity and error-pattern special cases (the
  Codex turn-integrity check is one). A suite turns per-provider lore into a contract.

### R6. Event-triggered scheduler jobs · from §3.5 · S–M

- Add `trigger: {provider: event, types: […], cursor: …}` beside `always`, `git.commits_since` and
  `fs`. Read existing lifecycle events (agent finished, bead closed, gate opened, CI result) from the
  local store with a durable cursor.
- Start local. Add GitHub webhook verification only if a polling cost justifies it.

### R7. An endpoint ("upstream") axis, then a runtime axis · from §3.4 · S–M, then M–L

- **Upstream first (S–M).** A named `upstreams:` block (`base_url`, `api_key` / `auth_token` as env
  references) rendered into each harness's own env vars by the adapter. This unlocks Bedrock, Vertex,
  proxy and OpenAI-compatible endpoints without new providers.
- **Runtime next.** Use systemd sandbox properties on agent scopes (`ProtectHome=`,
  `ReadWritePaths=`) as the first containment step, as the Gas Town report's R12 suggested. Only
  consider a container or Kubernetes runtime if unattended or multi-tenant use grows. This is the
  place to apply `corpus-before-mechanism`.

### R8. Honest-docs conventions · from §3.9 · S

- A **"Last verified against code: <date>"** header on architecture and reference docs, with a CI
  warning when a doc is older than N days and its owning paths changed.
- An **"Accepted but inert"** section convention for config keys, flags and events that exist but
  have no consumer.
- **Guard-test naming:** each area's rules name the tests that enforce them.

### R9. Reason-coded decision traces · from §3.8 · S–M

- A short-lived, targeted trace for the scheduler, admission queue and R3 job: *what* it did and
  *why*, with the reason code. `sase trace start <job|epic> --for 10m`.
- Build it after R3 has produced real "why didn't it relaunch?" questions.

### R10. A declarative bundle format and registry · from §3.7 · watch only

- Revisit only when a second external consumer asks for non-Python distribution of agents, workflows,
  schedules and doctor checks. `corpus-before-mechanism` applies.
- If built, take Gas City's **namespaced imports, version pins and content-hash lockfile**, not its
  vocabulary.

### Explicitly not recommended

- tmux as the substrate, and screen-scraping or keystroke injection.
- Dolt, or any database server as the work store.
- "Zero hardcoded roles" as a rule in SASE's code. SASE's finalizer, landing and gate roles are
  deliberate.
- A "no skills, no MCP" stance. SASE's memory and skill system is a strength.
- LLM patrol agents for mechanical checks. Gas City itself moved patrol logic into deterministic
  code.
- A hosted SaaS tier, or a vendor-neutral hosted-service protocol, before any consumer exists.
- A wholesale Bazel migration as a first step (see R1).
- Gas City's mail, nudge and Mayor machinery. The Gas Town report's R5 and R6 cover the
  single-turn-compatible version.
- Copying Gas City's vocabulary (city, rig, wisp, convoy, sling, molecule).

---

## 7. Sequencing and success measures

| Order | Item | Why this order |
| --- | --- | --- |
| 1 | R1 steps 1 and 4 (SLO, measurement, rulesets, fail-closed evidence check) | Cheap, immediate, and prerequisite for everything else landing safely |
| 2 | R2 (verify policy, three-valued verdict, resume) | Gives retry loops a defined meaning |
| 3 | R4 (usage facts) | Provides the budget unit for R3 |
| 4 | R3 (epic-convergence job) | The payoff of 2 and 3 |
| 5 | R1 steps 3 and 5 (cache decision, queue or lane) | Once the gate's p50 fits the cadence |
| 6 | R5, R6, R7 (upstream), R8 | Independent, parallelisable |
| 7 | R9, R7 (runtime), R10 | As measured need appears |

**A small repeated benchmark.** Run a fixed workload: independent tasks, one dependency chain, one
failing verification, one killed check (the `no_verdict` case) and one gated decision. Track
human interventions, `no_verdict` runs miscounted as failures, ready-to-landed time, red-master
hours, and tokens spent supervising. The first target is **fewer operator interventions at
unchanged correctness**, not more simultaneous agents.

---

## 8. Confidence and open questions

**High**

- CI outcomes and wall times (computed from `gh run list` today).
- The existence and semantics of Gas City's control nodes, exit 75, soft-fail and scopes (authoritative
  spec plus ~10,000 lines of dispatch code).
- SASE's lack of an endpoint axis, a price table, a container runtime and event-triggered jobs
  (targeted greps).

**Medium**

- Whether SASE can reach a ~5-minute required gate without a remote-execution farm.
- Whether per-unit repeat rates would justify a content-addressed test cache (a hypothesis).
- The payoff of R2 and R3 on SASE's shorter epics.

**Low or unverified**

- Gas City's throughput claims for its internal fleet (self-reported).
- Whether the machine-wide supervisor and reconciler v2 are further along than the docs say.
- The state of the Gas City nightly beyond the last six nights.

**Open questions**

1. What share of Master Gate wall time is critical path versus queueing and setup?
2. What would a `no_verdict` outcome look like in the current `TaskTriage` and receipt vocabulary?
3. Is the epic-convergence job better as a scheduler job or as a finalizer-adjacent host action?

---

## Sources

**Gas City** @ `45c804d59`

- **Core:** `AGENTS.md`, `ROADMAP.md`, `README.md`, `CHANGELOG.md`.
- **Architecture and design:**
  - `engdocs/architecture/{dispatch,health-patrol,orders,reconciler-v2}.md`
  - `engdocs/design/{usage-facts-v0,inline-ralph-v0,idle-session-sleep,session-reconciler-tracing,two-minute-ci-blacksmith}.md`
  - `engdocs/bazel-ci-budget.md`
  - `engdocs/research/w-gc-004-orchestration-framework-survey.md`
- **Specs and guides:**
  - `docs/reference/specs/formula-spec-v2.md`
  - `docs/reference/{cli,trust-boundaries}.md`, `docs/runbooks/remote-hardened-city.md`
  - `docs/guides/{configuring-an-agent,harness-recipes,shareable-packs,connected-clients}.md`
  - `docs/getting-started/dashboard.md`
- **Code:**
  - `internal/dispatch/`, `internal/convergence/`, `internal/reviewquorum/`, `internal/usage/`,
    `internal/pricing/`
  - `internal/packman/`, `internal/packregistry/`, `internal/extmsg/`, `internal/runtime/`
  - `internal/config/config.go:2805`
- **CI:** `.github/workflows/{bazel,ci,nightly,pr-evidence-watchdog}.yml`, plus `gh api` rulesets.

**SASE** @ `28ced2a125`

- **Docs:**
  - `docs/reference/work-units/bead-work.md`
  - `docs/reference/workflows.md`
  - `docs/reference/providers/retry-and-fallback.md`
  - `docs/reference/automation/{scheduler,scheduler-jobs}.md`
  - `docs/reference/config/scheduler.md`
  - `docs/reference/integrations/{plugins,remote-dispatch,mobile-gateway}.md`
  - `docs/concepts/landing.md`
- **Code:** `src/sase/macro/workflow_executor.py`.
- **CI:** `.github/workflows/master-gate.yml`, `shard-timings-ratchet.yml`.
- **Decision records:** `ci-two-speed-split`, `receipts-prove-before-they-skip`,
  `corpus-before-mechanism`, `single-turn-agents`.

**Prior research** (read through `sase artifact read`)

- `research:202610/gascity_software_factory_purpose_and_vision/gascity_software_factory_purpose_and_vision__final.md`
- `research:202610/gastown_vs_sase_lessons_to_borrow/gastown_vs_sase_lessons_to_borrow__final.md`
- `research:202610/master_ci_red_why_and_how_to_stay_green/master_ci_red_why_and_how_to_stay_green.md`

**Live data** (2026-10-17)

- `gh run list` for `gastownhall/gascity` (`bazel.yml`, `ci.yml`, `nightly.yml`) and `sase-org/sase`
  (Master Gate, Full CI).
- `gh api` for repo stats and rulesets.
