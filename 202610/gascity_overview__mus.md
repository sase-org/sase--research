# GasCity: What It Is, What It's For, and Where It's Headed

Research date: 2026-10-17. Sources: the
[gascity repo](https://github.com/gastownhall/gascity) checked out at
`main` (~Oct 17 2026), its README, AGENTS.md, ROADMAP.md, user docs, and
engineering docs. Repo at time of research: Go module
`github.com/gastownhall/gascity`, MIT license, ~1,395 stars / ~447 forks,
created 2026-02-22, actively pushed (latest commits Oct 2026, v1.5.x
release line).

## One-sentence summary

GasCity (`gc`) is a **composable orchestration infrastructure / SDK for
multi-agent coding workflows**: instead of giving you one AI coding
assistant, it runs a *fleet* of coding agents against durable,
dependency-gated work graphs, driven by user-supplied configuration.

## Origin

GasCity extracts the reusable infrastructure out of **Gas Town**
(Steve Yegge's multi-agent orchestration system,
`github.com/steveyegge/gastown`). Gas Town proved multi-agent
orchestration works, but all its roles (Mayor, Deacon, Polecat, crew,
etc.) are hardwired in Go code. The key insight, per the repo's own
AGENTS.md: the way work is expressed — as *beads composed into
formulas* — was powerful enough to abstract roles into configuration.
GasCity is that extraction: Gas Town becomes **one configuration
(pack) among many** runnable on the same engine.

## What it is used for

The canonical use case, from the FAQ and tutorials: a developer (or
team) writes down *how a job gets done* once, as a **formula**, and the
orchestrator runs it as a graph across many agents **outside the user's
own session** — decomposing the job into units of work, fanning
independent pieces out in parallel, holding each step until its
dependencies close, reviewing/gap-checking results, retrying failures,
and driving the graph to completion. "You describe a feature once and
come back to a finished branch." Concrete uses:

- **Fleet orchestration of coding agents** across one or many repos
  (each repo registered as a *rig* via `gc rig add <path>`; typical
  loop: `gc start` → `gc sling mayor "add a /health endpoint"` →
  `gc session attach mayor`).
- **Scheduled/event-driven automation** via *orders* (cron, cooldown,
  condition, or event triggers that fire formulas; *health patrol*
  keeps the fleet alive: stall detection, restart-with-backoff,
  reconcile-to-desired-state).
- **Reusable orchestration styles** via *packs*: the same engine can
  behave as Gas Town, Ralph, Claude Code Agent Teams, or a custom
  setup, purely by swapping configuration.
- **Multi-project setups**: rig-scoped orchestration with per-rig bead
  namespaces, pack imports/overrides, shareable versioned packs
  (`pack.toml` + `agents/`, consumed via a `gascity-packs` module).
- **Observability**: an append-only event bus (`gc events --follow`,
  dashboard, HTTP+SSE API) so humans and agents watch the same stream;
  events can also trigger orders, closing the automation loop.

### The six-primitive model

Everything composes from six primitives (the user-facing model in
`docs/getting-started/how-gas-city-works.md`):

| Primitive | Role | Meaning |
|---|---|---|
| Agent | WHO | A configured worker: prompt template + scope + provider. No roles are built in. |
| Bead | WHAT | One unit of work (tasks, mail, sessions, convoys are all beads differing by `type`); the universal persistence substrate, so work survives agent crashes. |
| Formula | HOW | A reusable written method (TOML steps + dependencies) compiled into a bead graph and executed by the orchestrator. |
| Rig | WHERE | A registered external project/repo with its own bead namespace and agent scope. |
| Pack | CONFIGURES | The unit of configuration (`pack.toml` + agents/formulas/orders); the city itself is the root pack and can import shared packs. |
| Event | OBSERVE | Immutable append-only notifications fired by activity. |

Underneath sit three pieces of role-agnostic plumbing: the
**orchestrator** (controller/supervisor loop reconciling desired state
to running state, incl. the control dispatcher executing check/retry/
fan-out/tally/drain control beads), the **bead store** (Dolt-backed
`bd` by default, file-backed via `GC_BEADS=file`), and the **event
bus**.

### Design rules that shape what it's for (and not for)

- **ZERO hardcoded roles** — a role name in Go source is treated as a
  bug; roles are pure configuration.
- **Judgment out of Go** — Go handles transport, never reasoning ("if
  stuck then restart" in Go is a violation; decisions go in prompts).
- **Primitives must become *more* useful as models improve** — hence
  permanent exclusions: no skills system, no capability flags, no
  MCP/tool registration, no decision logic in Go.
- **Sessions are disposable; work is not** — convergence comes from
  persistent beads plus idempotent observers, not from keeping agents
  alive.
- 16 built-in agent harnesses (Claude Code, Codex CLI, Gemini CLI,
  Cursor, Copilot, AMP, OpenCode, Grok, Kimi, Pi, …); agents run under
  the user's existing logins/keys; mixed fleets are just config.
- Runtime providers: tmux (default/fallback session backend),
  subprocess, exec, ACP, Kubernetes, herdr; plus an HTTP+SSE API and
  dashboard.
- No Go coding required to use it: user-facing surface is TOML config
  plus Markdown prompt templates. (Contributing is Go + Bazel-gated
  CI.)

## Long-term vision (as stated and as implied)

There is **no single "Vision 2030" manifesto** in the repo. The closest
to an official direction statement is a layered set:

1. **The platform thesis (the durable vision).** GasCity is not one
   orchestrator but the *platform every orchestrator is expressed on*:
   "a feature added to Gas City lifts *every* orchestrator built on
   it — Gas Town included." The long-term bet is that orchestration
   knowledge (formulas, packs) becomes reproducible, legible,
   shareable, version-controlled configuration, and that hand-rolled
   multi-agent coordination (context in chat, branch setup by hand,
   truth in people's heads) moves into pack/city content run by an
   orchestrator. The "Set Up a Multi-Agent Engineering Environment"
   guide makes this team-level ambition explicit.
2. **The primitives ratchet.** The Primitive Test gates new platform
   surface (atomicity, more-useful-as-models-improve, judgment-out-of-Go),
   and `internal/` stays private until the API stabilizes, with public
   SDK exports (`pkg/`) marked as future work — i.e., the engine
   hardens first, the embeddable SDK comes later.
3. **Near-term roadmap (ROADMAP.md, owned by @julianknutsen,
   rewritten at least once per minor release; "current thinking, not
   commitments; dates deliberately absent").** Priority areas for 1.6:
   - *Session and reconciler reliability* — sessions and their work
     converge on their own after crash/restart/upgrade; keyed v2
     session reconciler becomes the only reconciler; legacy tick
     reconciler deleted.
   - *Performance* — infra-class beads move to local SQLite while
     Dolt keeps versioned work beads; hot-path speedups in `gc`,
     `bd`, reconciler; numeric targets after benchmarks exist.
   - *Contributor onboarding* — slim root AGENTS.md, colocated area
     rules, per-package docs, curated starter issues (humans *and*
     agents as contributors).
4. **Accepted design directions pointing further out.**
   - *Machine-wide supervisor* (accepted Mar 2026): per-city
     controllers evolve into an Erlang/OTP-style supervision tree
     with a `/v0/cities` API resource — explicitly preparing for
     future multi-tenant hosting.
   - *Gas Town feature parity* (tracked analysis): 100% of Gas Town
     behavior gets a Gas City equivalent, constrained by zero
     hardcoded roles.
   - Kubernetes and herdr providers, external-messaging fabric
     designs, and a `hyperscale` example city point toward larger,
     possibly remote fleets.
5. **What it will never become.** The permanent exclusions (skills,
   capability flags, tool registration, in-Go decision logic) plus
   "no premature abstraction" bound the vision: the platform stays
   role-agnostic plumbing that gets *thinner* in judgment as models
   get smarter, not a smarter agent itself.

## Caveats for the synthesizer

- Roadmap priorities move per minor release; ROADMAP.md (last updated
  2026-10-05) is the fresher signal than any single design doc.
- Archived engdocs (`engdocs/archive/`) contain superseded thinking
  (e.g., early composable-config drafts, startup roadmaps); treat as
  evidence of trajectory, not current intent.
- Commercial/hosted ambitions are nascent: the wire is kept
  vendor-neutral by CI invariant, and multi-tenancy appears only as
  "explicitly prepared for," not committed.
