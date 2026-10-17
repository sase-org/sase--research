# Gascity vs SASE: where the factory is ahead

> **Research query:** Compare SASE with Gascity (`gastownhall/gascity`), using recent
> sidecar research on Gascity and Gastown as context. In particular: in what ways is
> Gascity superior to SASE? End with a ranked list of recommended SASE improvements.

**Researcher:** `research.1x.grk` · **Date:** 2026-10-17

This is an independent comparison. It uses prior sidecar reports as orientation, then
checks the claims against current Gascity, Gastown, and SASE source. It does not consult
peer reports from this swarm.

## Bottom line

Gascity is a **software factory**: a Go controller that compiles a written-down method
(a **formula**) into a durable bead graph, then drives that graph to completion
*outside any chat session*. Agents are configured workers. The orchestrator owns
control flow. SASE is a **transaction host**: a single-turn agent is launched with a
prompt, the host owns completion, and a human remains responsible for correctness.

That is the whole comparison. Gascity is ahead wherever unattended, configurable,
graph-shaped work is the goal. SASE is ahead wherever a human must stay the integration
point, and where memory, goals, gates, and a cockpit matter more than a standing
workforce.

The most expensive Gascity advantages, in order, are:

1. **Host-executed control over a durable work graph.** Formula v2 materializes steps
   as independently routable beads and gives the orchestrator check, retry, fan-out,
   drain, tally, and finalize. SASE workflows are typed DAGs, but they run inside a
   host executor; they do not become a crash-surviving bead graph that other agents
   can claim.
2. **Mechanical "done."** A Gascity check loop is a script the orchestrator runs. The
   step is done when the script says so. SASE treats an agent's declaration as the
   completion signal, then runs finalizers. The agent still owns the meaning of done.
3. **User-authored orders.** Cron, cooldown, condition, event, and manual triggers
   fire formulas or exec commands with no human dispatch. SASE's scheduler is a strong
   *system* automation plane. It is not a user-authored "when X happens, run method Y"
   surface.
4. **Packs as shareable process knowledge.** A Gascity pack is TOML plus prompts plus
   formulas plus orders. Swapping a pack changes the factory. SASE plugins are Python
   packages. SASE macros are reusable prompts. Neither is a complete, code-free
   topology.
5. **Ready-work pools.** Gascity standing workers claim `bd ready` work. SASE launches
   an agent *for* a prompt. Ready task beads raise a human `TaskTriage` gate. The
   factory does not pull work; the operator pushes assignments.

Steal Gascity's **control plane**, not its **session model**. Steve Yegge's August 2026
reversal — Gas Town "fell apart at the seams," reusable harnesses abandoned, private
Wheelhouse with "crons watch, models act" — cuts against long-lived role agents and
against LLM patrols. It does *not* cut against host-owned check/retry/dispatch over a
durable graph. That split is already Gascity's own design: the orchestrator executes
every control bead; agents execute only work beads. SASE already has the single-turn
worker. It is missing the graph.

## Method and snapshots

### Snapshots

| System | Revision | Notes |
| --- | --- | --- |
| **Gascity** (`gastownhall/gascity`) | `45c804d59` (2026-10-17 03:34 UTC) | Latest stable tag **v1.5.0**. `main` is active. |
| **Gastown** (`steveyegge/gastown`) | `649b832b` (2026-07-23) | Frozen. Context only: Gascity is the successor. |
| **SASE** | `5ea5fa5452` (2026-10-16) | This checkout. |

Gascity paths are relative to that repo root. SASE paths are relative to the SASE repo
root.

### Inputs

Audited sidecar reads:

- `research:202610/gascity_software_factory_purpose_and_vision/gascity_software_factory_purpose_and_vision.md`
  — what Gascity is for, and the factory thesis.
- `research:202610/gastown_vs_sase_lessons_to_borrow/gastown_vs_sase_lessons_to_borrow.md`
  — Gastown vs SASE, with Gascity as the living successor.
- `research:202605/sase_vs_gastown.md` — May 2026 comparison. Several of its
  recommendations (coordinator agent, health subsystem, landing queue) still have no
  first-class SASE equivalent.

Independent verification in this turn:

- Opened `gh:gastownhall/gascity` and `gh:steveyegge/gastown` with `sase repo open`.
- Read Gascity `AGENTS.md`, `README.md`, `ROADMAP.md`, `docs/getting-started/how-gas-city-works.md`,
  `coming-from-gastown.md`, `docs/guides/understanding-formulas.md`,
  `understanding-packs.md`, `docs/tutorials/{04,05,07}-*.md`,
  `docs/reference/specs/formula-spec-v2.md`, `engdocs/contributors/primitive-test.md`,
  `docs/guides/harness-recipes.md`, `internal/api/AGENTS.md`, and dispatch tests under
  `internal/dispatch/`.
- Read SASE `docs/reference/workflows.md`, `work-units/{bead-work,bead-triage}.md`,
  `automation/{scheduler,monitors}.md`, `agent-auto-restart.md`,
  `agents/agent-launches.md`, `integrations/plugins.md`, `runner-slots.md`.
- Fetched Chris Sells, *Orchestration Is All You Need* (2026-04-21) and the Beads 1.3 /
  Gascity 1.5 post (2026-10-07).

### Not done

Nobody in this turn installed Gascity, started a city, or ran a matched workload
against SASE. Throughput, cost-per-step, and quality claims from Gascity maintainers
are labeled as claims. Upstream issues are cited as reported, not reproduced.

## Two machines

### Gascity

Gascity is an orchestration-builder SDK extracted from Gastown. The non-negotiable
rule is **zero hardcoded roles** (`AGENTS.md`): if a line of Go names Mayor, Deacon,
Polecat, or Refinery, it is a bug. Those names exist only as **pack configuration**.

Six primitives (`docs/getting-started/how-gas-city-works.md`):

| Primitive | Role | Meaning |
| --- | --- | --- |
| Agent | WHO | Configured worker: prompt, provider, scope. A running agent is a **session**. |
| Bead | WHAT | One unit of work. Tasks, mail, sessions, and convoys are beads that differ by `type`. |
| Formula | HOW | A reusable TOML method. Applying it *produces* beads. |
| Rig | WHERE | A registered git repo with its own bead-ID prefix and agent scope. |
| Pack | CONFIGURES | Agents, formulas, orders, prompts. The city *is* a pack. |
| Event | OBSERVE | Append-only outbound record. Also a trigger for orders. |

The controller (`gc start`) reconciles desired sessions to running sessions, evaluates
orders every ~30s, and runs the formula-v2 **control dispatcher**
(`internal/dispatch`). Formula v2 (`docs/reference/specs/formula-spec-v2.md`) compiles
to:

```text
formula.toml
  → recipe (flat steps + edges)
    → workflow root bead
    + independently routable step beads   (agents execute these)
    + control beads: check, retry, fanout, drain,
      scope-check, workflow-finalize      (orchestrator executes these)
```

Runtime providers actually in tree: tmux, subprocess, exec, ACP, Kubernetes, herdr,
SSH, hybrid, t3bridge (`internal/runtime/`). Sixteen built-in CLI harnesses
(`docs/guides/harness-recipes.md`): Claude, Codex, Gemini, Grok, Kimi, Kiro, Cursor,
Copilot, AMP, OpenCode, Groq, Cerebras, Pi, Auggie, Oh My Pi, Antigravity.

The HTTP+SSE API and the dashboard SPA are **projections** over the same domain
packages as the CLI (`internal/api/AGENTS.md`). CI fails the build if either
re-implements domain logic, if the OpenAPI spec drifts, or if an event type lacks a
registered payload.

v1.6 priorities (`ROADMAP.md`, 2026-10-05): reconciler v2 as the only reconciler;
move infrastructure beads (orders, sessions, wisps) off Dolt onto SQLite; contributor
onboarding. The 1.5 post reports an experimental SQLite infra ledger at 130–250×
faster infrastructure reads on a production-scale city (maintainer measurement).

### SASE

SASE is a multi-project host for existing CLI coding agents. A run is one provider
turn. Continuation is mechanical (gates, monitors, pipe, plan, questions, host
finalizers). The human settles goals. Shared backend logic lives in `sase-core`.

Closest SASE analogues to Gascity primitives:

| Gascity | SASE analogue | The gap |
| --- | --- | --- |
| Formula v2 graph | YAML macro workflows (`docs/reference/workflows.md`) | Workflows are an in-process DAG of agent/bash/python/HITL steps. They do not materialize as a durable, independently claimable bead graph. No `sase workflow resume` in the spec. |
| Pack | Plugins (`sase_macros`, `sase_config`, …) plus home/project macros | Plugins are Python entry points. A pack is files. |
| Order | Scheduler jobs + monitors | Scheduler jobs are mostly *system* jobs (hooks, waits, bead triage). Monitors supervise one OS command inside one agent session. |
| Agent pool + `bd ready` | `sase run` / `sase bead work` + runner slots | Capacity admission (`docs/reference/runner-slots.md`) queues already-launched work. It does not pull ready beads into new workers. Task beads raise a human gate (`docs/reference/work-units/bead-triage.md`). |
| Control beads | Workflow `if` / `for` / `while` / `repeat`, provider retry/fallback, HITL gates | Control lives in the executor and in LaunchApproval. It is not durable graph state the host can resume after a crash. |
| Event bus | Notifications + scheduler polling | Notifications are an inbox. They do not, as a primitive, fire user methods. |
| Mail | `sase chat`, notify, pipe, handoff | No durable inter-agent mail in the work graph, injected at turn start. |
| Rig | Project + linked/sidecar/external repos + `%dispatch` | Multi-repo is real and richer in VCS terms. It is not one city with prefix-isolated work and a shared controller. |
| HTTP+SSE + dashboard | Textual TUI, Telegram, nvim, mobile gateway | The TUI is a better *cockpit*. There is no typed factory API that a dashboard, a script, and the CLI all project. |
| Health patrol | Agent auto-restart (`docs/reference/agent-auto-restart.md`) | Auto-restart covers *update-skew before the model turn*, once per lineage. It does not classify live-turn stalls or reclaim stranded `in_progress` work. |

SASE already has several things Gascity treats as out of scope or as consumer-layer
concerns: memory webs and instruction bundles, human-settled goals, HITL gates,
artifacts with typed links, feature flags, receipts, two-speed CI, a plugin catalog,
and a personal multi-project TUI. Those are reasons *not* to copy Gascity wholesale.
They are not answers to the factory gaps.

### Gastown, briefly

Gastown proved the metaphor (Mayor, Polecats, Convoys, Refinery, Deacon) and then
froze. Gascity's migration guide is explicit about what survived (`coming-from-gastown.md`):

- Deacon watchdog → **orchestrator health patrol + reconciliation** (no role agent).
- Plugins → **orders** (exec for shell; formula for agent work).
- Formulas → **in-process compiler + orchestrator graph** (v2), not in-session molecules.
- Roles → **pack agents**. Crew vs polecat is an operating *style* (persistent vs
  scalable), not a type.

The May 2026 SASE-vs-Gastown note and the October Gastown-vs-SASE synthesis already
flagged landing discipline, liveness, failure policy, and a coordinator. Five months
later those are still the live gaps. Gascity is the version of those ideas that
*moved the watchdog out of the LLM*. That is the version worth borrowing.

## Ranked ways Gascity is superior to SASE

Each item is a Gascity capability with a production caller or an authoritative spec,
paired with the SASE surface that comes closest. Rank is by how much unattended
correctness it buys, not by how flashy the metaphor is.

### 1. Durable graph orchestration outside any session

**Gascity.** A v2 formula is a method. `gc formula cook`, `gc sling --formula`, or an
order compiles it and writes beads. From that moment the run is independent of the
TOML file and of every session (`understanding-formulas.md`). Step beads are
Ready-visible and routable to different agents or pools (`gc.run_target`). The
dispatcher in `internal/dispatch` executes control beads; tests such as
`TestFanoutSettlesScopeBeforeClosing` and the workflow-finalize suite pin that this
is live code, not a doc.

**SASE.** `docs/reference/workflows.md` is a real typed DAG: agent, bash, python,
prompt_part, parallel, join modes, `if`/`for`/`while`/`repeat`, HITL, cleanup,
typed outputs. It is a better *authoring* language than Gascity TOML in several
places (Jinja, typed inputs, HITL). It is a worse *runtime*. The graph lives in
`workflow_state.json` inside one executor. A crashed executor does not leave
independently claimable work. There is no resume verb in the workflow spec.
Cross-agent handoff uses `sase var set` and `%wait`, which is a prompt-time
injection, not a store query.

**Why it matters.** This is the factory. "Describe a feature once and come back to a
finished branch" is only possible if the method outlives the chat. SASE's
single-turn contract is compatible with that *if* the host holds the graph. Today
the host holds the turn, not the graph.

### 2. Mechanical "done": check loops owned by the orchestrator

**Gascity.** `[steps.check]` / `[template.check]` run an exec script after the step
closes. Pass closes the step. Fail with budget left respawns the iteration.
Exhaustion fails the step and blocks downstream work (`understanding-formulas.md`,
"Self-Checking Work"). The production pattern is the `build-basic-review` /
`fix-loop-base` style: three review lanes, a synthesizer, a fix step, then
`.gc/scripts/checks/implementation-review-approved.sh` with `max_attempts = 6`. The
orchestrator — never an agent — decides whether to iterate. "Done" means the
validator agrees.

`retry` is a different construct: transient provider failures, `on_exhausted =
"soft_fail"` so an optional reviewer lane can drop out without blocking the build.

**SASE.** Completion is a declaration plus host finalizers. `just check` is
agent-initiated and explicit-only for `check-full`. Mentors and HITL can pause a
workflow. Nothing in the workflow spec says "this step is not closed until this
script exits 0, and if it doesn't, respawn the whole review subtree." Provider
retry/fallback is about *calling the model again*, not about *the work not being
done*.

**Why it matters.** Agents lie, drift, and declare victory. A factory that cannot
say "done" without believing the worker will ship slop at volume. Sells' essay
states the same bar: humans define done; the factory encodes it. Gascity put that
bar in the graph. SASE left it in the prompt.

### 3. User-authored orders: when the method runs

**Gascity.** An order is a TOML file in `orders/` (`docs/tutorials/07-orders.md`):

| Trigger | Fires when |
| --- | --- |
| `cooldown` | `interval` since last run |
| `cron` | 5-field schedule |
| `condition` | shell `check` exits 0 |
| `event` | named event on the bus (`on = "bead.closed"`) |
| `manual` | `gc order run` only |

The action is a formula *or* an exec command, never both. Drop a file in `orders/`;
the orchestrator rescans within a minute. No restart. Health patrol is an order,
not a role. The bundled core pack ships housekeeping orders (`beads-health`,
`gate-sweep`, `reaper`, …). Exec orders handle mechanical work with no LLM.

**SASE.** The scheduler (`docs/reference/automation/scheduler.md`) is a real
control plane: orchestrator, routines, jobs, Patch filtering, crash-restart of
routines. The jobs are *ours*: hook checks, wait checks, bead task triage, comment
polling, auto-restart, disk pressure. A user cannot drop a file that says "every
night, run this review formula on every dirty project." Monitors supervise one
command inside one session and then maybe launch a follow-up. That is the opposite
shape: a turn hands off to a command, rather than a clock handing a method to the
fleet.

**Why it matters.** Unattended work is a trigger problem. Gascity's answer is
configuration. SASE's answer is "write another scheduler job in the product." The
May 2026 note already wanted a coordinator; orders are the cheaper half of that
wish — crons watch, models act.

### 4. Packs: process knowledge as files, not code

**Gascity.** A pack is a directory with `pack.toml` (`understanding-packs.md`). It
declares agents, formulas, orders, prompts, doctor checks, commands. The city is
the root pack and **imports** others. Last-wins layering lets a city override a
shared formula without forking the pack. Examples in tree: `examples/swarm` (flat
peers), `examples/lifecycle` (polecat + refinery as config), `examples/hyperscale`,
`examples/t3bridge-gastown`, plus the Gastown pack as one topology among many.
Sells: Ralph loops, Anthropic agent teams, Gastown, and custom factories are all
packs.

The escalation ladder in `AGENTS.md` is load-bearing: prompt/template → pack
config → compose existing formula/order machinery → adapter behind an existing
provider → new SDK surface (Primitive Test). New capability defaults to
configuration.

**SASE.** Plugins are thirteen Python entry-point groups
(`docs/reference/integrations/plugins.md`). That is the right shape for VCS
providers, LLM adapters, and `sase listen`. It is the wrong shape for "here is how
this team reviews a PR." Macros and workflows *are* files, and discovery order is
documented, but they do not bundle standing workers, orders, and routing into one
importable topology. Research swarms, epic phase workers, landers, and mentors are
product features. In Gascity they would be a pack.

**Why it matters.** The factory thesis is that the engineer's job becomes
*improving the factory*. That only works if the factory is versioned
configuration. SASE's process is still mostly in Python, skills, and hardcoded
agent kinds.

### 5. Standing pools, sling, and ready-work claiming

**Gascity.** An agent can be a named session or a **pool** with
`min_active_sessions` / `max_active_sessions` and a `scale_check` query. Each tick
the orchestrator sizes the pool to demand. `gc sling <target> <work>` creates a
bead and routes it in one motion; the target may be a pool. Ready work is a store
query (`bd ready`). "If you find work on your hook, you run it" is rendered into
prompts (`AGENTS.md`). Sessions are disposable; beads survive. On controller
restart, live sessions are **adopted** rather than respawned
(`how-gas-city-works.md`).

Beads 1.3 / Gascity 1.5 add **work leases**: a claim carries a five-minute lease,
workers heartbeat, `bd reclaim` returns expired work after a grace period (1.5
post, citing beads#4537). Dead agents do not strand the queue forever.

**SASE.** `sase run` and `sase bead work` *push* an assignment into a new
single-turn agent. Runner slots (`docs/reference/runner-slots.md`) are a global
capacity budget (default 10) over already-admitted launches. `sase bead work`
for a task bead launches exactly one deterministic worker after the bead is
ready; the scheduled path raises a **human** `TaskTriage` gate once a +1 bar is
met (`bead-triage.md`, `scheduler-behavior.md`). Agent-initiated launches go
through `LaunchApproval` and end the requester's turn
(`docs/reference/agents/agent-launches.md`). Claim/release exists for beads that
die *before* promotion (`bead-lifecycles.md`); it is not a heartbeat lease on
`in_progress` work.

**Why it matters.** A factory has a workforce and a queue. SASE has a launcher and
an inbox. The human is the dispatcher. That is a design choice (`gates-never-block`,
`single-turn-agents`), and it is also why SASE cannot run unattended at Gascity's
shape. The compatible steal is: host pulls ready work and launches single-turn
workers under a bounded policy, without a long-lived Mayor.

### 6. Failure policy in the graph

**Gascity.** Control beads encode policy:

- `retry` + `max_attempts` + `on_exhausted` (`hard_fail` | `soft_fail`)
- `check` loops that respawn a subtree
- `scope-check` failure policy on a workflow
- drain / on_complete / tally for fan-in (`majority`, `unanimous`, `any-pass`)
- `gc.continuation_group` so fix-ups stay coherent

The dispatcher owns this. Agents do not choose the recovery strategy. The
Primitive Test forbids putting "if stuck then restart" in Go as *judgment*; the
allowed form is "execute the control bead the formula compiled." Policy is data.

**SASE.** Provider retry/fallback is about which CLI to call. Workflow `on_error`
is continue-or-stop on a for-loop. Auto-restart is a narrow update-skew healer.
Triage classifies CI failures without changing exit codes
(`triage-annotates-does-not-change-exit-codes`). There is no bead-level "this
failed: retry on a stronger model, skip with degraded coverage, or escalate to a
gate" engine. The October Gastown comparison already ranked this near the top.
Gascity is where that idea landed as shipping graph ops.

### 7. Per-step mixed-vendor routing as configuration

**Gascity.** `metadata = { "gc.run_target" = "gc.implementation-reviewer" }` on a
step. The `code-review` expansion in `understanding-formulas.md` routes
acceptance, test-evidence, and simplicity reviews to three different roles, fans
in to a synthesizer, applies fixes on the implementation worker, then checks.
Sells' essay describes spreading those lanes across Codex, Gemini, and Claude on
purpose. The pack, not Go, names the vendors.

**SASE.** Size aliases and provider routing pick a model for a *launch*. A
research swarm hardcodes named researchers. A workflow can launch several agent
steps in parallel, each with its own prompt, but routing a step to "whoever is
the implementation-reviewer pool, currently Gemini" is not a first-class formula
concern. Mixing vendors on the same diff is a prompt-authoring trick, not a
graph primitive.

**Why it matters.** The bitter-lesson bet in Sells' essay is that more diverse
compute beats a single better model. SASE already runs mixed providers. It does
not encode "three vendors review, one synthesizes, a script decides" as a
reusable method.

### 8. Mail through the store

**Gascity.** Agents never hold references to each other
(`docs/tutorials/04-communication.md`). Mail is a bead. `gc mail send` /
`inbox` / `check --inject`. Mail survives crashes; nudge is terminal input and
does not. A hook injects unread mail at the start of a turn. Sling delegates
work without naming a session: the mayor slings to `my-project/reviewer` and the
controller wakes a pool member.

**SASE.** `sase chat`, notifications, pipe, and handoff are real, and handoff is
honest about ending the turn. They are not a work-graph mailbox. A later agent
does not query "unread mail for this role" from the bead store. Forking a
transcript (`#fork`) is the expensive substitute the Gastown comparison already
called out; seance was the cheap proposed steal.

**Why it matters.** Indirect coordination is how pools scale. Direct references
("tell agent acme") break when acme is a pool of five, or dead, or on another
provider.

### 9. Events as a primitive that closes the automation loop

**Gascity.** Events are one of the six primitives. Sequence numbers, typed
payloads, `gc events --follow`, dashboard watchers, and **event-triggered
orders**. The same stream humans watch can fire a formula. Beads 1.3 adds an
ordered event journal on the store side; community dashboards (Mardi Gras, bddb,
Reef) already consume it. Gascity's own API has a typed event registry enforced
by CI.

**SASE.** Notifications are an inbox with rules for toast/Telegram. The
scheduler polls. Artifact links are a typed graph. None of these is "on
`bead.closed`, cook formula `release-notes` onto pool `writer`." SASE could
grow that from the scheduler without copying Dolt.

### 10. Liveness and reconciliation as orchestrator infrastructure

**Gascity.** Health patrol is an order. The reconciler converges desired
sessions to running sessions. Adopt-on-restart is documented. v1.6's first
priority is making reconciler v2 the only path (`ROADMAP.md` #7093). The
migration guide is blunt: stall detection, restart-with-backoff, and
reconcile-to-desired-state are *not* a Deacon agent.

**SASE.** Auto-restart is excellent at the thing it does (update-skew before
the model turn, one retry, quiescence, never after provider start). It
explicitly does not restart provider errors, rate limits, OOM, or mid-turn
stalls. There is no Problems view that says "this live turn has produced no
tool calls in 20 minutes." The Gastown comparison's R2 is still open. Gascity
moved that watchdog into deterministic code, which is the form SASE can take
without violating `single-turn-agents`.

### 11. HTTP+SSE API and a factory dashboard, as projections

**Gascity.** CLI and API are required to be projections over domain packages
(`internal/api/AGENTS.md`, `AGENTS.md` layering invariants). OpenAPI is
generated. The dashboard SPA lives under `internal/api/dashboardspa/` and has
its own Bazel gates (`make dashboard-check`). Maintainer City is a public
read-only factory at factory.gascity.com (first-party; this turn did not log
in). Reef is an experimental visualizer over supervisor APIs.

**SASE.** The TUI is a better operator cockpit than Gascity's web UI is likely
to be for a single human. There is no equivalent *machine* surface: a typed
HTTP API that a dashboard, a mobile client, and a script all share, generated
from the same domain as `sase` CLI. The mobile gateway is a port, not this.
`sase-core` is the right place to grow it (`rust-core-required`).

**Why it matters.** Unattended fleets need a window that is not a terminal
multiplexer. SASE's Agents tab is that window for one machine. Gascity built
the wire first, then the window.

### 12. Runtime and harness breadth

**Gascity.** Providers in tree include tmux, subprocess, exec, ACP, Kubernetes,
herdr, SSH. Harness recipes cover sixteen CLIs, including Cursor, Copilot, AMP,
Pi, Kimi, and Antigravity, with a serving-env contract so an abstract upstream
(`base_url` / `api_key`) renders onto each harness's env vars.

**SASE.** Built-in LLM plugins: agy, claude, codex, grok, muse, opencode, qwen
(`docs/reference/integrations/plugins.md`). Remote dispatch covers other
machines. `sase tmux-agent` exists for driving the TUI, not for hosting a
worker fleet. There is no ACP, Kubernetes, or herdr provider.

**Why it matters.** Breadth is not quality. It *is* a factory requirement: the
best reviewer today is a different CLI from the best coder, and it changes.
Gascity treats that as configuration. SASE treats it as a plugin plus routing
tables, with a shorter roster.

Caveat: tmux keystroke injection is how Gastown got into trouble, and Gascity
still requires tmux as default-and-fallback (`README.md`). SASE should steal
the *provider interface* and ACP/K8s, not the keystroke backend.

### 13. Rigs: one city, many repos, prefix isolation

**Gascity.** `gc rig add <path>` registers a repo. Isolation is by bead-ID
prefix over a shared store, plus per-rig agent instantiation
(`how-gas-city-works.md`). City-scoped agents may serve any store; sling
refuses cross-store routes otherwise.

**SASE.** Projects, linked repos, sidecars, external `sase repo open`, and
`%dispatch` are a more precise VCS model, and they are audited. The operator
experience is "many systems that know about each other," not "one factory
floor with many lines." Cross-project `sase bead work` exists and is careful
about owner stores (`bead-work.md`). It is still a launch, not a city.

### 14. A sharper primitive boundary

**Gascity.** The Primitive Test (`engdocs/contributors/primitive-test.md`) is
three necessary conditions: atomicity (agents would race), more useful as
models improve, transport not cognition. Fail any one and it belongs in the
pack/prompt. Permanent exclusions: no skills system, no capability flags, no
MCP/tool registration, no decision logic in Go, no hardcoded role names
(`AGENTS.md` "What Gas City does NOT contain"). CI enforces layering, typed
wire, vendor-neutral hosted protocol (`scripts/check-core-boundary.sh`).

**SASE.** `rust-core-required` plus the litmus "if another frontend would need
it to match the TUI, it is core" is the right instinct. In practice a lot of
judgment still lives in Python: auto-restart classification, triage, LaunchApproval
policy, workflow execution. Skills, feature flags, and MCP-like tool catalogs
are first-class SASE product. Gascity's exclusions would be harmful if copied
literally (SASE *should* have skills and flags). The *test* is still sharper
than SASE's boundary, and it would catch "should this be a pack?" earlier.

### 15. Productization of the factory

**Gascity.** `brew install gascity`. One `gc` binary. Mintlify docs.
Discord. Public Maintainer City. Open-core ladder (Beads and Gascity free;
Beads Team Server; Gasworks hosted/VPC, design partnerships December 2026 —
first-party pages, not verified here). Dogfooding is the flagship deployment;
Sells claims 74 PRs merged in a day via the factory (essay; not re-counted
here). Commit velocity on `main` is high (prior synthesis: hundreds of
commits in October 2026).

**SASE.** A personal, deeply integrated host. Install is `uv` + plugins +
Rust pin + sidecars. Docs are excellent. There is no public factory floor
and no "drop this on a laptop and get a city" path. That is fine for Bryan's
machine. It is a Gascity superiority in the product sense: Gascity is trying
to be a thing other people run.

### Explicitly not superior (or not proven)

These Gascity headlines should not be treated as SASE gaps:

- **Long-lived tmux sessions as the default worker.** Yegge's reversal and
  Gastown's idle-reaper incidents argue against this. SASE's single-turn
  contract is the better worker model.
- **Dolt as the work store.** SASE's append-only git event streams plus
  optional beads sidecar are the right shape for this project. Gascity itself
  is moving infra beads *off* Dolt onto SQLite in 1.6.
- **Hardcoded Mayor / Deacon / Refinery.** Gascity deleted them from the
  engine. Do not reintroduce them in SASE as types.
- **Batch-then-bisect merge queue.** Still unwired in Gastown; in Gascity the
  Refinery is a pack formula. SASE's volume does not justify bisecting
  batches. A landing *ratchet* is a different, smaller idea (see
  recommendations).
- **HITL, memory, goals, TUI, artifacts.** SASE is ahead. Gascity's Primitive
  Test would call several of these "consumer layer." For a personal host they
  are the product.
- **Cost and quality of the factory.** Maintainer claims. This turn did not
  measure. The Every review (May 2026, cited in the Gascity vision synthesis)
  called the ideas sharp and the product not ready. Treat "74 PRs in a day"
  as marketing until SASE has its own matched workload.

## Ranked recommended improvements for SASE

Each recommendation is a Gascity idea rewritten to fit `single-turn-agents`,
`host-owned-completion`, `gates-never-block`, `helpers-return-roots-declare`,
`rust-core-required`, and `corpus-before-mechanism`. None of them requires a
long-lived Mayor or tmux injection.

### R1. Host-executed control graphs over beads (the formula-v2 analogue)

**Rank 1 · size L · core**

Materialize a workflow as a durable bead graph. The host executes control
nodes (check, retry, fan-out, join, finalize). Each work node is a single-turn
SASE agent launch, already the SASE worker model.

Concretely:

- A workflow step may declare `check: { cmd, max_attempts }` and
  `retry: { max_attempts, on_exhausted: hard_fail|soft_fail }`.
- Compiling a workflow writes step beads with blocking `needs` edges. Ready
  steps are independently launchable.
- Crash of a worker leaves the step bead open. Crash of the host leaves the
  graph in the store; the next controller tick continues it.
- `sase workflow resume <run>` is then a query, not a new feature.

This is Gascity's actual engine, mapped onto SASE's actual philosophy. It
subsumes a large part of the October Gastown R3 (failure policy) and R9
(crash resume).

Fit: the host already owns completion. Control beads are more host, not less.

### R2. Mechanical "done" as a check node, not a declaration

**Rank 2 · size M · core**

A work step is not closed because the agent declared. It is closed because a
host-run script (or `just check` profile) exited 0. Fail-with-budget respawns
the step or a declared subtree (review-synthesize-fix). Exhaustion fails the
node and blocks dependents, or `soft_fail` continues with a recorded
disposition.

Start with the existing `just check` / monitor-verify path. Promote it from
"the agent was told to run this" to "the graph will not mark this node closed
until this command passes."

This is the landing-discipline idea from the Gastown comparison, generalized
to every factory step, not only master. A master ratchet (Gastown R1) can be
the first check node on the lander.

Fit: `receipts-prove-before-they-skip` already wants proof. Check nodes *are*
proof. `check-full-is-explicit` stays: the check command is authored on the
node, not implied.

### R3. User-authored orders

**Rank 3 · size M**

Give the scheduler a user-facing order file, same discovery order as macros:

```toml
[order]
description = "Nightly review of ready task beads"
formula = "multi-lane-review"   # or: exec = "sase bead ready ..."
trigger = "cron"
schedule = "0 3 * * *"
pool = "reviewer"
```

Triggers: cron, cooldown, condition, event, manual. Actions: a workflow/macro
*or* an exec command. Drop-in reload. Exec orders for mechanical work (reap,
backup, `just` recipes). Formula orders instantiate R1 graphs onto a pool.

This is cheaper than a coordinator agent and matches Wheelhouse's "crons
watch, models act." The May 2026 "Mayor" wish splits: the clock is an order;
the conversation, if wanted later, is a bounded coordinator session (R8).

Fit: orders are scheduler jobs with a public schema. They do not block a
gate. They do not keep an LLM process alive.

### R4. Bounded ready-work pull (pools without long-lived workers)

**Rank 4 · size M · core**

Today `bead_task_triage` raises a human gate for every ready task. Keep that
as the default. Add an opt-in policy per project or task type:

- When a task bead is `ready`, blockers closed, and the policy allows it,
  the host launches `sase bead work <id>` as a single-turn worker, under
  runner-slot capacity and a daily launch budget.
- Every auto-launch is logged. A gate still fires when the policy refuses
  (unknown type, over budget, lander, goal unsettled).
- `in_progress` beads carry a lease. The worker heartbeats. Expiry plus
  grace returns the bead to `ready` (Beads 1.3's reclaim, on SASE's event
  store).

This is Gascity sling+pools, with SASE's LaunchApproval policy as the
governor instead of "if you find work on your hook, you run it" with no
human.

Fit: `gates-never-block` stays for anything the policy cannot prove. The
worker stays single-turn. The host is the pool.

### R5. Failure policy on bead work

**Rank 5 · size M · core**

A closed-failed step (or a red check node) selects a policy from
configuration, not from an LLM:

| Disposition | Host action |
| --- | --- |
| `retry` | Relaunch the same step, maybe with a stronger size alias |
| `soft_fail` | Close with `gc.final_disposition=soft_fail`; dependents proceed |
| `skip` | Close canceled with reason |
| `escalate` | Raise a gate; do not wait inside an agent |

Record the disposition on the bead. Do not put `if stuck then restart` in
Python as an ad-hoc healer. Auto-restart stays the update-skew specialist.

Fit: host decides; agents stay single-turn; gates still never block the
requester because the requester already ended.

### R6. Packs: a code-free topology bundle

**Rank 6 · size M**

A SASE pack is a directory:

```text
review-pack/
  pack.toml
  macros/            # existing macro/workflow files
  orders/            # R3
  agents/            # named routing targets + default provider/size
  checks/            # R2 scripts
```

Import from a project spec. Last-wins overlay (project beats pack beats
bundled). No Python. Plugins remain the right shape for VCS, LLM, and CLI
extensions.

First pack to extract from the product: the research swarm (named
researchers, final, linker, image), so a swarm is configuration rather than
an xprompt special case. Second: epic phase + lander. Third: multi-lane
review (R7).

Fit: `corpus-before-mechanism` — extract packs from workflows SASE already
runs, rather than inventing a pack registry.

### R7. Multi-lane review as a pack, not a swarm special case

**Rank 7 · size S–M**

Encode Sells' review orchestration as R1+R6:

- Parallel review steps, each with a `run_target` (provider/size/role).
- Synthesize step.
- Check node running an artifact schema validator or `just check`.
- `max_attempts` on the whole subtree.

Use it on SASE's own lander before offering it as a general pack. Mixed
vendors are configuration (`gc.run_target` analogue: `%model` / provider pin
per step).

This replaces ad-hoc "launch three reviewers" prompts with a method that
survives the authors.

### R8. Mail as beads, delivered at turn start

**Rank 8 · size S**

`sase mail send <role-or-agent> -s … -m …` writes a mail bead. At the start
of a matching agent's turn, the instruction bundle (or a small injected
block) lists unread mail. Closing a work bead can optionally mail a
downstream role. No wake-the-LLM on send unless `--notify` requests a
bounded R4 pull.

Seance (`sase chat ask` as a read-only fork-resume) remains the cheap way to
query a *finished* transcript. Mail is for *work that still exists*.

Fit: delivery is host-side, at turn start, same as instruction bundles
(`instructions-per-invocation`).

### R9. Live-turn liveness and a Problems view

**Rank 9 · size M**

Classify running turns: making progress, silent, waiting on a gate/monitor,
usage-limited, dead. Surface a Problems view on the Agents tab. Action is
policy (R5), not an LLM Deacon. Generation-aware ownership so a restarted
lineage is not mistaken for the previous one (Gastown #4890 is the warning).

Auto-restart stays for pre-provider update-skew. Liveness covers
`provider_running` and later, which auto-restart currently refuses on
purpose.

Fit: detection on the host; action gated by R5; no agent waits.

### R10. Typed HTTP+SSE API as a projection of sase-core

**Rank 10 · size L · core**

Make the CLI and a future dashboard projections over `sase-core`, with a
generated OpenAPI spec and a CI lock that the spec matches the domain.
First resources: agents, beads, goals, events, workflow runs. The TUI stays
the human cockpit; the API is for scripts, a factory dashboard, and any
second frontend (nvim, mobile) that today re-speaks Python.

Gascity's invariant is the thing to copy: *neither* CLI *nor* API
re-implements domain logic. SASE already wants this (`rust-core-required`).
The dashboard is optional until the wire exists.

### R11. An event bus that orders can subscribe to

**Rank 11 · size M · core**

Emit typed, sequenced events for bead transitions, agent lifecycle, order
fires, and check outcomes. Notifications become a consumer. R3 orders with
`trigger = "event"` become a consumer. The TUI becomes a consumer.

Start from existing notification types and ToolRun records
(`record-before-admit`). Do not build a second store.

### R12. Sling: create and route in one motion

**Rank 12 · size S**

`sase sling <target> "description"` / `sase sling <target> --formula name`
creates the bead (or cooks the graph) and routes it to a role, pool, or
agent. Today's split (`bead create` then `bead work` then a gate) is three
verbs for one intent.

Fit: a CLI projection over R1+R4. No new domain.

### R13. Apply the Primitive Test to sase-core vs Python vs pack

**Rank 13 · size S, ongoing**

Adopt Gascity's three questions as a written test next to
`rust-core-required`:

1. Would two agents race without an atomic host op?
2. Does this get *more* useful as models improve?
3. Is it transport, or is it a judgment call?

Judgment → pack/prompt. Transport that every frontend needs → `sase-core`.
Python stays presentation, CLI glue, and TUI. This would have caught several
"should this be a hardcoded agent kind?" decisions (research swarm, mentors
as types, Deacon-like healers).

Do **not** adopt Gascity's exclusions of skills, flags, or MCP. Those fail
question 2 in Gascity's world and pass it in SASE's.

### R14. Demand-driven launch count (`scale_check`)

**Rank 14 · size S · after R4**

Once R4 exists, size the number of concurrent single-turn workers from a
query over ready work, clamped by runner slots and a budget. This is
Gascity's pool scaler without persistent sessions: the host launches more
workers when `bd ready` (SASE: ready step beads) is deep, and stops when it
is empty.

### R15. Landing ratchet as the first check node on the lander

**Rank 15 · size M**

The October Gastown report's R1 is still the right lander: do not call a
merge done until the integrated tip is tested and the target branch contains
the commit. Implement it as R2 on the lander pack (R6/R7), not as a
Gastown-style Refinery role. No bisecting batch queue.

### R16. Broader harness matrix, ACP first

**Rank 16 · size M, later**

Add Cursor / Copilot / AMP / Pi only when a real SASE workflow needs them
(`corpus-before-mechanism`). ACP is the interesting *protocol* steal: a
structured provider seam instead of another argv dialect. Kubernetes/herdr
wait until SASE has a fleet that does not fit one machine; `%dispatch`
already covers the two-machine case.

### R17. Rigs-like UX over existing repo inventory

**Rank 17 · size S**

Do not replace projects. Add a city-style *view*: one floor, many rigs,
prefix-filtered beads, a default sling target per rig. `sase repo list` is
already the inventory. The gap is operational, not storage.

### Explicitly not recommended

- Tmux keystroke injection and screen-scraping.
- LLM patrol agents for mechanical checks (Gastown Deacon).
- Dolt as the SASE store.
- An always-on Mayor process as the integration point.
- Copying Gascity's "no skills / no flags / no MCP" exclusions.
- Migrating workspaces to git worktrees for disk (alternates already do this).
- Wasteland-style federation.
- Bisecting merge queues.
- Making long-lived sessions the default worker (Gascity's session model).
  Adopt Gascity's *control/work split* and keep SASE's single-turn workers.

### Sequencing

1. **Now:** R2 on the lander (mechanical done for merges) and R13 (write the
   Primitive Test down). These pay off on today's tree.
2. **Next:** R1 (control graph) enough to support check/retry/finalize, then
   R5 (failure policy) as data on that graph, then R3 (orders) to fire it.
3. **Then:** R4 (ready-work pull) + R9 (liveness) + R8 (mail). Together they
   make unattended epics *possible* without a Mayor.
4. **Then:** R6/R7 (extract packs, starting with review and research swarm),
   R12 (sling), R15 if not already done as the lander's R2.
5. **Later:** R10/R11 (API + events), R14, R16, R17 — once a consumer exists.

**Success metric.** A repeated workload with independent tasks, one
cross-repo dependency, one conflict, one failed worker, and one gated
decision. Track ready-to-assigned time, finished-to-landed time, human
interventions, duplicate launches, lost output, and red-master hours.
The target is **fewer operator interventions at unchanged correctness**.

## Mapping onto prior recommendations

The May 2026 SASE-vs-Gastown note wanted a coordinator, a health subsystem,
roles, a landing queue, and a provider-tier matrix. The October
Gastown-vs-SASE synthesis wanted a landing lane, liveness, failure policy,
escalation, inbox, a coordinator session, preservation, a deliverable view,
workflow resume, seance, a repair catalog.

Gascity's contribution is to show which of those belong in **deterministic
host code over a durable graph** (landing, liveness, failure policy,
dispatch, orders, check loops) and which belong in **configuration** (roles,
review topology, Mayor-as-pack). The coordinator session is optional once
orders and ready-work pull exist. Workflow resume falls out of R1. Seance
and preservation remain SASE-specific and still worth doing; they are not
Gascity superiorities.

## Sources

**Gascity** @ `45c804d59`:

- `AGENTS.md`, `README.md`, `ROADMAP.md`
- `docs/getting-started/how-gas-city-works.md`
- `docs/getting-started/coming-from-gastown.md`
- `docs/guides/understanding-formulas.md`
- `docs/guides/understanding-packs.md`
- `docs/guides/harness-recipes.md`
- `docs/tutorials/04-communication.md`
- `docs/tutorials/07-orders.md`
- `docs/reference/specs/formula-spec-v2.md`
- `engdocs/contributors/primitive-test.md`
- `internal/api/AGENTS.md`
- `internal/dispatch/` (control, fanout, retry, finalize tests)
- `internal/runtime/{tmux,subprocess,exec,acp,k8s,herdr,ssh,hybrid,t3bridge}/`
- `examples/{swarm,lifecycle,hyperscale,t3bridge-gastown}/`

**Gastown** @ `649b832b`: context only (`README.md` freeze; migration mapping
via Gascity's coming-from-gastown guide).

**SASE** @ `5ea5fa5452`:

- `docs/reference/workflows.md`
- `docs/reference/work-units/{bead-work,bead-triage,bead-lifecycles}.md`
- `docs/reference/automation/{scheduler,monitors}.md`
- `docs/reference/config/scheduler-behavior.md`
- `docs/reference/agent-auto-restart.md`
- `docs/reference/agents/agent-launches.md`
- `docs/reference/integrations/plugins.md`
- `docs/reference/runner-slots.md`

**Prior research** (audited reads):

- `research:202610/gascity_software_factory_purpose_and_vision/gascity_software_factory_purpose_and_vision.md`
- `research:202610/gastown_vs_sase_lessons_to_borrow/gastown_vs_sase_lessons_to_borrow.md`
- `research:202605/sase_vs_gastown.md`

**Web:**

- Chris Sells, *Orchestration Is All You Need* (2026-04-21),
  https://sellsbrothers.com/orchestration-is-all-you-need
- *Beads 1.3 and Gas City 1.5* (2026-10-07),
  https://blog.gascity.com/posts/beads-1-3-and-gas-city-1-5/
- Yegge's April 2026 "Welcome to Gas City" and August 2026 "Shape of Things
  to Come" / Wheelhouse reversal, as quoted in the sidecar Gascity and
  Gastown syntheses (not re-fetched verbatim in this turn).

## Confidence

- **High:** Gascity primitives, formula v2 split, orders, packs, Primitive
  Test, provider/harness roster, API-as-projection invariant, SASE workflow /
  scheduler / triage / auto-restart / plugin surfaces (all from current
  source).
- **Medium:** how completely reconciler v2 and the SQLite infra ledger are
  wired on `main` (roadmap says in progress; 1.5 post says experimental);
  how far Maintainer City's public dashboard reflects production;
  the reading that Gascity's control/work split is the compatible steal
  (interpretation).
- **Low / unmeasured:** factory throughput, cost per step, review-quality
  gains from mixed-vendor lanes, Gasworks timeline.
