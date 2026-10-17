# Gas City (`gastownhall/gascity`): What It Is, What It's For, and Where It's Going

*Researcher: cld · Date: 2026-10-17 · Repo snapshot: `main` @ `2dec01c71a` (2026-10-17 01:04 UTC), 7,161 commits*

## TL;DR

- **What it is.** Gas City is an MIT-licensed Go **"orchestration-builder SDK"** for multi-agent
  coding systems. It ships as a single `gc` binary. It was built by pulling the reusable machinery out of
  Steve Yegge's **Gas Town** and turning Gas Town's hard-coded roles (Mayor, Deacon, Polecat,
  Refinery, …) into plain configuration. Its slogan-level invariant is **"ZERO hardcoded roles."**
  Gas Town becomes just one shippable **pack**; Ralph loops, Claude Code Agent Teams, and StrongDM-style
  factories are meant to be other packs.
- **What it's used for.** It runs fleets of CLI coding agents (Claude Code, Codex, Gemini, Cursor,
  Copilot, AMP, OpenCode, Kimi, Grok, Pi and more: 16 built-in harnesses) as a **"software factory."**
  You write a **formula**, a TOML method for how a job gets done. The controller turns it into a graph of
  durable **beads**, a Dolt-backed work store. It then fans the ready work out to many agents in parallel,
  gates each step on its dependencies, retries failures, and drives the run to completion *outside your
  interactive session*. The flagship user is Gas City itself. Its maintainers report ~100 agents running
  around the clock and 50–74 merged PRs per day.
- **Long-term vision.** There are three distinct layers:
  1. **Yegge's thesis:** developers become *shepherds* of agent flocks. Gas City is "the ultimate
     de-SaaSer," and its factories are "light" (observable, addressable), not dark.
  2. **Gas City, Inc.'s thesis:** "orchestration is all you need." This is a bitter-lesson argument
     that orchestration turns more compute into better output, so better models make factories better
     rather than unnecessary. The commercial shape is **open core**: Beads and Gas City are free and OSS;
     Beads Team Server and **Gasworks** are paid, multi-operator, managed or VPC products. A hosted
     `gascity.com` service is being built on a published, vendor-neutral wire protocol.
  3. **The near-term engineering roadmap (1.6):** reliability (reconciler v2), performance (moving
     infrastructure bookkeeping off Dolt into SQLite), and onboarding contributors, human or agent.
- **Important tension.** By August 2026, Yegge, the project's originator and now only an advisor, wrote
  that Gas Town "fell apart at the seams with Opus 4.7." He said he had "given up on building reusable
  harnesses" and is running a private, bespoke orchestrator ("Wheelhouse") instead. Gas City's whole
  premise is a *reusable* orchestration SDK. Independent reviewers (Every, May 2026) said: "sharp ideas…
  not yet ready for prime time."

---

## 1. What Gas City is

From the repo's own `AGENTS.md`:

> Gas City is an orchestration-builder SDK — a Go toolkit for composing multi-agent coding workflows.
> It extracts the battle-tested subsystems from Steve Yegge's Gas Town into a configurable SDK where
> **all role behavior is user-supplied configuration** and the SDK provides only infrastructure.
> … You can build Gas Town in Gas City, or Ralph, or Claude Code Agent Teams, or any other
> orchestration pack.

It also gives the origin story. Gas Town proved multi-agent orchestration works, but all its roles
were hardwired in Go. Steve realized that the way work is expressed (beads composed into formulas)
could abstract roles into configuration.

### The six user-facing primitives (`docs/getting-started/how-gas-city-works.md`)

| Primitive | Role | What it is |
|---|---|---|
| **Agent** | WHO | A configured worker: a name, a provider (harness), a prompt template, and a scope. When it runs it is a *session*, which can be pooled with `min/max_active_sessions` and a `scale_check` demand query. |
| **Bead** | WHAT | One durable unit of work (ID, title, status, type). Tasks, mail, sessions, and convoys are *all* beads that differ only by `type`. Blocking `needs` edges give ordering "with no central scheduler." |
| **Formula** | HOW | A TOML method of steps and dependencies. Applying it *materializes* beads, so a run outlives the file and any session. `gc sling` creates and routes work. |
| **Rig** | WHERE | A registered external project, usually a git repo, with its own bead-ID namespace and agent scope. |
| **Pack** | CONFIGURES | A directory with `pack.toml` declaring agents, formulas, and orders, plus skills, commands, MCP config, and doctor checks. **The City is the root pack**, and it imports shared packs. |
| **Event** | OBSERVE | An append-only, sequence-numbered outbound record (`bead.closed`, `session.crashed`, `order.fired` …) watched by humans (`gc events --follow`, dashboard) and by event-triggered orders. |

Three pieces of machinery, none of which know about roles, sit underneath:

- the **orchestrator/controller**, which reconciles declared state to running sessions and executes
  control beads;
- the **bead store**, which defaults to `bd`/Dolt and can alternatively be a file store, an in-memory
  store, or an exec-backed store;
- the **event bus**, backed by `.gc/events.jsonl`.

**Orders** trigger formulas on a cron, cooldown, condition, event, or manually. **Health patrol** is one
kind of order and keeps the fleet alive.

### Formula v2: "orchestration is the value"

The docs insist that the product is graph orchestration, not just agent hosting. In formula v2, the
control dispatcher (`internal/dispatch`) executes *control beads*: check, retry, fan-out, tally, drain,
scope-check, and workflow-finalize. Agents execute *work beads*.

The 1.3 release post shows the canonical example. A convoy of beads drains into parallel worktrees, and
three reviewer agents (acceptance, test evidence, simplicity) write verdicts. An exec `check` gate
loops "until the reviewers approve or `max_attempts` is hit." Single-agent, in-session formulas (v1)
still work as a peer shape.

### Runtime surface

- **Session providers:** tmux (the default and the fallback), subprocess, exec (script), ACP,
  Kubernetes, hybrid/auto routing, and [herdr](https://herdr.dev).
- **Harnesses:** 16 built in, per `docs/guides/harness-recipes.md`. They are Claude Code, Codex, Gemini,
  Grok, Kimi, Kiro, Cursor, Copilot, AMP, OpenCode (plus Groq/Cerebras gateways), Pi, Auggie, Oh My Pi,
  and Antigravity. The blog calls the provider contract a `FactoryWorker` / "Factory Worker API" so that
  agent vendors can make their CLI a Gas City worker.
- **Interfaces:** a CLI (`cmd/gc`) and an HTTP+SSE API (`internal/api`, with a generated OpenAPI spec)
  are "projections over the domain packages." There is also a run-centred web dashboard served from the
  binary.
- **Ecosystem:** a pack registry at `registry.gascity.com` (shipped in 1.4) and Homebrew packaging
  (`brew install gascity`).
- **Dependencies:** tmux, git, jq, pgrep, and lsof, plus dolt ≥ 2.1, `bd` 1.x, and flock for the default
  beads provider. Setting `GC_BEADS=file` avoids Dolt.

---

## 2. What it's used for in practice

1. **Running a coding "software factory" over your own repos.** You `gc init` a city, `gc rig add` a
   repo, `bd create` a task, and `gc session attach mayor` to talk to the coordinating agent. The FAQ
   pitch: "You describe a feature once and come back to a finished branch." Typical formulas are
   implement → multi-vendor review → apply findings → merge. Multi-vendor review (the same diff sent to
   Claude, Codex, and Kimi) is a signature pattern.
2. **Running Gas Town without Gas Town.** The default Gastown pack "runs an exact replica of Gas Town."
   Per Yegge it can import existing rigs and beads. `docs/getting-started/coming-from-gastown.md` maps
   every Town role to config. For example, Deacon becomes controller health patrol, Polecats become a
   pooled agent, and Dogs become exec orders.
3. **Non-coding agent workflows.** Yegge's launch essay names devops and monitoring, ETL and data
   pipelines, ticket queues, and incident response. His own example is moderating player-uploaded images
   for his game *Wyvern*.
4. **Dogfooding: Gas City builds Gas City.** The maintainers' "Maintainer City" is visible at
   `factory.gascity.com`. The company says it runs issue triage, deployment, and ops on itself and
   "hired 15 agentic employees" (named personas such as *Randy* for releases and *Seth* for SRE, reachable
   over Discord). Every reported Julian Knutsen's server at ~100 agents, ~50 PRs/day, and ~1B tokens/day.
   The commit log shows agent identities such as `gascityinc-randy[bot]` and `gascityinc-olivia[bot]`.

Who should use it today? Every's hands-on review said it was worth it only for people "already running
more than 10 Claude Code sessions in parallel and reading source code." It also reported that it took a
room of experienced engineers a full day to get running. Teams in production pair it with Jira or Linear
because Beads is CLI- and agent-first.

---

## 3. Design philosophy, which is the core of the "vision" inside the code

The repo's `AGENTS.md` encodes an unusually opinionated philosophy. It is the clearest statement of what
the maintainers think will last.

- **Zero Framework Cognition ("keep judgment out of Go").** "Go handles transport, not reasoning. … An
  `if stuck then restart` is framework intelligence. Move the decision to the prompt."
- **The Bitter-Lesson filter on every primitive.** "A primitive must become more useful as models
  improve." The *Primitive Test* (`engdocs/contributors/primitive-test.md`) admits a capability to the
  SDK only if three conditions hold:
  - (a) agents can't do it safely without atomicity (for example, a CAS claim on a bead);
  - (b) it stays exactly as necessary with a model that is 10x smarter;
  - (c) it is transport, not cognition.
- **The system converges because work persists.** Sessions are disposable and beads are durable.
  Redundant idempotent observers are "the reliability mechanism." The controller *adopts* live sessions
  on restart instead of respawning them.
- **No status files: query live state.** No PID or lock files. "The process table is the single source
  of truth."
- **SDK self-sufficiency.** Every infrastructure operation must work with only the controller running.
  "If removing an `[[agent]]` entry breaks an SDK feature, it's a violation."
- **Permanent exclusions** ("not 'not yet'"): no skills system ("the model IS the skill system"), no
  capability flags, no MCP or tool registration, no decision logic in Go, and no hard-coded role names.
- **Settled decisions:** a city is a directory, TOML config (`pack.toml` for definition, `city.toml` for
  deployment), "tutorials win over architecture docs," no premature abstraction, and everything stays in
  `internal/` until the API stabilizes. `pkg/` currently contains only `eventexport`.

**Observed tension (my analysis).** In practice the "no skills / no MCP" exclusions have softened into
*projection*. PackV2 ships `skills/` and `mcp/` directories, and `internal/materialize` projects them into
each provider's native skill dirs and MCP config. MCP projection landed 2026-04-19 (#867). The likely
reconciliation is that Gas City doesn't *own* a tool or skill runtime; it only delivers pack content to the
harness. Even so, the principle reads more absolute than the code.

---

## 4. History, people, and cadence

| Date (2026) | Event |
|---|---|
| Oct 2025 – Jan 2026 | Yegge releases **Beads** (Oct 13, 2025) and then **Gas Town** (Jan 1, 2026). |
| Feb 22 | Repo created; first commit by Julian Knutsen. |
| Mar 4 | Yegge's "Welcome to the Wasteland: A Thousand Gas Towns" (federation over a shared DoltHub database). |
| Mar 8 | "Session-first" refactor removes the original Agent Protocol primitive. |
| Apr 21 | **v1.0.0** tag and changelog entry; Sells' manifesto "Orchestration Is All You Need." |
| Apr 24 | Yegge's essay "Welcome to Gas City" ("Gas City hit 1.0 today"). |
| Apr 28 | Chris Sells, CEO of "the newly minted Gas City, Inc.", announces 1.0. |
| May 6 / May 25–29 | v1.1.0 / v1.2.0. |
| Jun 18 / Jul 3 | v1.3.0: Formulas 2.0 (convoys and drain), Mayor-as-a-skill, built-in packs written out as pinned imports, `--json` everywhere. |
| Jul 12 | `gc login` / `gc whoami` plus **Service Protocol v0** for hosted auth (#4135). |
| Jul 24–28 | v1.4.0: the "quality of life" release, with the pack registry, a run-centred dashboard, and Maintainer City. |
| Aug | Yegge's "The Shape of Things to Come: The Continuous Thunderdome," in which Gas Town "burned down" and he moves to a private orchestrator. |
| Oct 5–7 | **v1.5.0** with Beads 1.3: proxied Dolt server by default (~75% less idle RAM in one test) and a preview SQLite ledger for infrastructure beads (130–250× faster infrastructure reads). |
| Oct 5 | ROADMAP rewritten for 1.6; tracking issues #7093, #7094, and #7095 opened. |

**People.**

- **Julian Knutsen** is CTO and a former Block tech lead. He wrote ~4,050 of the 7,161 commits under two
  author spellings, about 57%, and owns the roadmap.
- **Chris Sells** is CEO and is credited with growing Flutter.
- **Steve Yegge** has 4 commits. He is an advisor and calls himself "only lightly affiliated with the
  code, in the sense that I outlined my vision in a blog post, and they built it."
- **Donna Box** is an advisor and Beads co-maintainer.
- Other heavy committers: Jim Wordelman (730) and Stephanie Jarmak (241).

**Scale and velocity (2026-10-17).**

- The git history has 228 distinct author names.
- GitHub shows 1,395 stars, 447 forks, and 1,564 open issues and PRs.
- Commit volume has been sustained at 500–1,400 per month since March. Much of it is agent-authored.
- The company claims more than 35K stars across Beads, Gas Town, and Gas City, and 500+ contributors.
- Discord had 2,000+ members at launch.

**Engineering maturity signals.**

- Bazel is the CI gate, with remote execution.
- The OpenAPI spec is generated, and every event type must have a typed payload.
- CI enforces boundary guards: a "vendor-neutral hosted-service wire" check and a worker-boundary
  migration test.
- There are 39 design docs, an archive of audits, and release-gate documents.
- Many runbooks exist for **Dolt bloat, compaction and backup cleanup**, which points to a real
  operational cost of the Dolt substrate.

---

## 5. The long-term vision

### 5a. Yegge's vision: shepherds, light factories, and de-SaaSing ("Welcome to Gas City", Apr 24)

- **Developers as shepherds:** "In the very near future, devs will become shepherds, tending flocks
  of agents which do the ground-level work." His AI-adoption chart grows from 8 to 11 stages:
  - Stage 9 is your first deployed pack ("a garden you're tending").
  - Stage 10 is many packs, where "you, the human, are the control plane."
  - Stage 11 is the "Factory Builder" (architect, curator, shepherd).
- **A factory of factories:** "Gas City is the only dark factory that has been designed with the goal
  of creating other factories." He frames it as a **Light Factory** because every worker is visible and
  addressable.
- **Enterprise de-SaaSing:** "Enter Gas City: The ultimate de-SaaSer." "A small team of three to five
  human engineers running Gas City packs can credibly replace seven-figure SaaS bills." He gives a
  multi-year horizon ("It's going to take a few years to find out").
- **Audit trail as compliance:** every agent action lands in git-versioned Dolt, which he calls "your
  SOC2 story."
- **Reliability as a dial:** he would not yet use it where people could be physically hurt ("Not in
  2026"), but expects progress over "the next couple of years."
- **Federation (the Wasteland):** a public commons board for "federated work arbitrage" over a shared
  DoltHub database (`steveyegge/wl-commons`), with multi-dimensional "stamps" as cross-rig reputation.
  Gas City's own engineering items are tracked as Wasteland items (for example
  `w-gc-004-orchestration-framework-survey.md`). The Gas Town federation doc says core federation
  features are not yet implemented.

### 5b. Gas City, Inc.'s vision: orchestration all the way down, sold as open core

- **The thesis ("Orchestration Is All You Need," Sells, Apr 21).** Every human engineering process
  (write, review, iterate, merge, and also PM and UX) can become an agentic orchestration. Under Sutton's
  bitter lesson, betting that better models will make orchestration unnecessary is the losing side:
  "Orchestrations are how you turn more compute into better output, indefinitely." "A better model just
  makes the orchestration better." The end state: "Instead of building the software, you're going to be
  building the factory that builds the software."
- **Multiplayer.** Sells calls agentic engineering "largely a single-player sport" today. Making it
  multiplayer is an active build target, with named agent teammates reachable over Discord, Slack, SMS,
  and email.
- **Product stack** (from `gascity.com`, © Gas City, Inc.; tagline "Agent work that lasts. A factory
  your team can improve."):
  - **Beads**: free/OSS agent memory and work graph. It is being extended into "durable organizational
    memory" (Memory Beads, a typed graph, an HTTP "Beads Protocol," and versioning).
  - **Gas City**: a free/OSS factory platform ("configured, not coded").
  - **Beads Team Server**: *commercial*, a shared and governed work graph with traceability and cost
    reporting. It is in early access, offered as managed SaaS or self-hosted in your VPC.
  - **Gasworks**: *commercial*, "One factory. Multiple operators." It is built on Beads Team Server, with
    design partnerships opening **December 2026**. "Bring your own keys. Zero markup." It does not toll
    tokens.
- **Hosted Gas City on a neutral protocol.** `docs/reference/specs/service-protocol-v0.md`
  (`gascity.dev/service/v0`) is designed like `docker login`. `https://gascity.com` is only a flag
  default, any conforming server works, and "Generic and vendor-neutral are the same constraint." Only
  auth and identity have shipped (`gc login`/`gc whoami`, July). **Cities** (provisioning) and **runs**
  (formula submission) are reserved surface.

  The internal design `engdocs/plans/hosted-onboarding/DESIGN.md` (status: "exploration/design. No code";
  produced by an 11-agent design and red-team pass) lays out three flows:
  - **Flow 0**: a web playground with a "Run this" button that gets you to a live run in about 10 s with
    nothing installed.
  - **Flow 1**: `gc init --at`, a hosted wizard that ends with a provisioned city.
  - **Flow 2**: `gc run <formula> --at`, an anonymous ephemeral run with a watch link. This is the
    "killer demo," but it is flagged as "literally RCE-and-inference-as-a-service to strangers" until
    credential-less LLM egress exists.

  The hosted controller runs *stock OSS `gc`*. Private server repos are referenced as `crucible` and
  `gasworks`. The OSS client is "~10% of the work; the hosted server is ~90%." A CI boundary script
  (`scripts/check-core-boundary.sh`) keeps billing, trial, and plan logic out of the OSS tree.

### 5c. The engineering roadmap (`ROADMAP.md`, last updated 2026-10-05, "priority areas for 1.6")

The roadmap is deliberately undated ("current thinking, not commitments"):

1. **Session and reconciler reliability (#7093).** After a crash, restart, or upgrade, a city returns
   to the correct state with no manual intervention. The keyed **reconciler v2** fully replaces the
   legacy tick reconciler, and P0/P1 session bugs get burned down.
2. **Performance (#7094).** "Fast and quiet as cities grow." Infrastructure-class beads (order tracking,
   wisps, controller and session bookkeeping) move to local SQLite while Dolt keeps the versioned work
   beads (#3926), plus `gc`/`bd`/reconciler hot-path work.
3. **Contributor onboarding (#7095).** "A new contributor, human or agent" finds colocated `AGENTS.md`
   rules, package `doc.go` files, and a generated codebase map.

Other stated future work:

- Public SDK exports in `pkg/` once the API stabilizes.
- The worker-boundary migration (`worker.Handle`) and worker conformance.
- An external messaging fabric.
- A machine-wide supervisor following an Erlang/OTP-style supervision tree.
- Runs-view event sourcing for the dashboard.

---

## 6. Counterpoints and risks

- **The founder's own pivot away from reusable harnesses.** In "The Continuous Thunderdome" (Aug 2026),
  Yegge says Gas Town was only ever used to build itself and "fell apart at the seams with Opus 4.7." He
  writes: "I have given up on building reusable harnesses," and "Harnesses need to be part of your
  application, chemically bonded in." His Wheelhouse orchestrator is "closed-source, made just for me."

  He does not disavow Gas City. He calls it "also a Beads machine" and praises the Gas City team as
  Beads co-maintainers. But his argument cuts directly against Gas City's reusable-SDK premise. Gas
  City's answer is the pack model: bespoke behavior lives in your own pack, and only role-free plumbing is
  shared. Whether that is a sufficient reconciliation is the central open question for the project's
  long-term thesis.
- **Independent assessment.** Every (Katie Parrott with Mike Taylor, May 19): "Gas City has some sharp
  ideas that reflect the direction software development is headed, but it's not yet ready for prime
  time." The verdict: "Learn from the ideas. Skip the toolkit for now." The cited issues are fresh-context
  cost per step (a six-step job costs about six sessions), confusing vocabulary, and review loops that
  better models make less necessary.
- **Operational weight.** It is tmux-required, and Dolt brings bloat, compaction, and backup runbooks.
  The 1.5 and 1.6 work moving infrastructure beads to SQLite and making Dolt proxied/idle-stopping is
  the team responding to this.
- **Concentration and autonomy risks.** About 57% of commits come from one person. An autonomous agent
  maintainer released Beads v1.2.1 without release-specific human sign-off (August 11), which the team
  wrote up as an incident.
- **Churn.** Five minor releases in about six months, each with "Upgrading Notes," breaking changes, and
  `gc doctor --fix` migrations. The `[Unreleased]` changelog already lists more API write-path removals.
- **Branding drift.** Docs use `docs.gascityhall.com` while the company site uses `gascity.com` /
  `docs.gascity.com`, and the GitHub org is `gastownhall`.

---

## 7. Relevance to SASE (my analysis, brief)

Gas City is the closest public analogue to SASE's own design space: beads as the durable substrate,
fleets of CLI coding agents across many providers, host-driven orchestration, and agent-written
`AGENTS.md` rules. A few contrasts may be worth the lead's attention:

- **Agent lifetime.** Gas City keeps long-lived tmux sessions and adopts them on restart, and it relies
  on nudges and mail. SASE instead treats agents as single-turn, with mechanical continuation.
- **Where judgment lives.** Gas City's ZFC rule ("judgment in prompts, transport in Go") and its
  Primitive Test are a crisp, reusable litmus test, close in spirit to SASE's Rust-core boundary test.
- **Graph orchestration.** Formula v2's control-bead vocabulary (check, retry, fan-out, tally, drain) is
  a concrete model for graph orchestration over beads.
- **Hosted service.** The "URL is configuration, not vendor logic" hosted-protocol discipline is a clean
  pattern if SASE ever grows a hosted service.

---

## Sources

**Repository (opened via `sase repo open gh:gastownhall/gascity`):**

- `README.md`, `AGENTS.md`, `ROADMAP.md`, `CHANGELOG.md`
- `docs/getting-started/{how-gas-city-works,coming-from-gastown,faq}.md`,
  `docs/guides/{harness-recipes,understanding-packs}.md`
- `engdocs/architecture/nine-concepts.md`, `engdocs/contributors/primitive-test.md`
- `engdocs/research/w-gc-004-orchestration-framework-survey.md`
- `engdocs/plans/hosted-onboarding/DESIGN.md`, `docs/reference/specs/service-protocol-v0.md`,
  `internal/cliauth/AGENTS.md`
- `engdocs/proposals/{skill,mcp}-materialization.md`, `internal/materialize/`
- `examples/gastown/{FUTURE,SDK-ROADMAP}.md`
- `git log` / `git shortlog` / tags

**GitHub discussion:**

- Tracking issues [#7093](https://github.com/gastownhall/gascity/issues/7093),
  [#7094](https://github.com/gastownhall/gascity/issues/7094), and
  [#7095](https://github.com/gastownhall/gascity/issues/7095)
- Repo metadata via `gh api`

**Web:**

- Steve Yegge, [Welcome to Gas City](https://yegge.ai/essays/welcome-to-gas-city/) (2026-04-24;
  [Medium original](https://steve-yegge.medium.com/welcome-to-gas-city-57f564bb3607))
- Steve Yegge, [The Shape of Things to Come, Part 1: The Continuous Thunderdome](https://yegge.ai/essays/the-shape-of-things-to-come/) (Aug 2026)
- Steve Yegge, [Fences, not Sandboxes](https://yegge.ai/essays/fences-not-sandboxes/) (2026-08-24; does not discuss Gas City directly)
- Chris Sells, [Orchestration Is All You Need](https://blog.gascity.com/posts/orchestration-is-all-you-need/) (2026-04-21)
- Chris Sells, [Announcing Gas City 1.0!](https://blog.gascity.com/posts/announcing-gas-city-1-0/) (2026-04-28)
- Chris Sells, [Gas City 1.3: Now We're Looping With Gas!](https://blog.gascity.com/posts/gas-city-1-3-now-were-looping-with-gas/) (2026-07-03)
- Wesley Davidson, [Gas City 1.4: The View From The Factory Floor](https://blog.gascity.com/posts/gas-city-1-4-the-view-from-the-factory-floor/) (2026-07-28)
- Wesley Davidson, [Beads 1.3 and Gas City 1.5](https://blog.gascity.com/posts/beads-1-3-and-gas-city-1-5/) (2026-10-07)
- Chris Sells, [Fun Facts About Beads On Its First Birthday!](https://blog.gascity.com/posts/fun-facts-about-beads-on-its-first-birthday/) (2026-10-15)
- [The City Wire archive](https://blog.gascity.com/archive/)
- [gascity.com](https://gascity.com/), [Gasworks](https://gascity.com/gasworks/), [Beads Team Server](https://gascity.com/beads-team-server/), [About](https://gascity.com/about/)
- Very Good Ventures, [interview with Chris Sells](https://verygood.ventures/blog/chris-sells-gas-city-future-of-software-development-ai-and-quality/) (2026-07-22)
- Katie Parrott, Every, [Inside the 100-agent Software Factory](https://every.to/context-window/inside-the-100-agent-software-factory) (2026-05-19)
- Search-snippet only, body not retrievable: The New Stack, [Gas Town comes to the cloud and brings the Wasteland with it](https://thenewstack.io/steve-yegges-ai-agent-orchestration-project-gas-town-comes-to-the-cloud-and-brings-the-wasteland-with-it/)
- Search-snippet only: [gastown.dev federation design](https://gastown.dev/docs/design/federation)

**Could not read:** the Medium "Welcome to the Wasteland" post (HTTP 403), the MetaFilter "Gas Town
Burned Down" thread (HTTP 403), and The New Stack article body (it rendered only site chrome). Claims
about the Wasteland and the Kilo cloud partnership therefore rest on search snippets and should be treated
as lower confidence.

## Confidence

- **High:** what Gas City is, its architecture and philosophy, its release history, and its stated 1.6
  roadmap. These come from the repo itself.
- **High:** the company's product stack and commercial direction. These come from first-party sites.
- **Medium:** usage and traction numbers (100 agents, 74 PRs/day, 35K stars), which are self-reported.
- **Medium:** the interpretation of Yegge's August pivot as a challenge to Gas City's premise. That is my
  reading; he does not say so explicitly.
