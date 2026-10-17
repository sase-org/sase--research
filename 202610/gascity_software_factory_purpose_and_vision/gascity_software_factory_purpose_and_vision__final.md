# Gas City (`gastownhall/gascity`): What It Is For and Where It Is Going

*Consolidated report · 2026-10-17 · Merges five independent researcher reports (cdx, cld, grk,
mus, gem) with the lead's own verification against the repository and primary web sources.*

**Snapshot.** `main` @ [`2dec01c71a`](https://github.com/gastownhall/gascity/commit/2dec01c71a3dd5cdd0ca494ea7c72f4806d6c770)
(2026-10-17 01:04 UTC), 7,161 commits on `main`. Latest stable tag **v1.5.0**: tag commit dated
2026-10-04, announced 2026-10-07. Go, MIT license, repo created 2026-02-22. GitHub showed ~1,395 stars
and ~447 forks. Nobody in the swarm installed Gas City or ran a fleet, so all performance and quality
figures below are claims made by the maintainers themselves.

---

## Bottom line

**What it is.** Gas City is an open-source platform for running **fleets of existing CLI coding
agents** as a durable, configurable **"software factory."** Supported agents include Claude Code,
Codex, Gemini, Cursor, Copilot, AMP, OpenCode, Kimi, Grok, Pi and others (16 built-in harnesses).
You write *how* a job gets done once, as a TOML **formula**. The `gc` controller then runs it as a
graph of durable work records (**beads**). It fans ready steps out to many agents, holds each step
until its dependencies close, runs review and check loops, retries failures, and drives the job to
completion *outside any one chat session*. The pitch is "describe a feature once and come back to a
finished branch." The models do the reasoning; Gas City supplies the machinery around them.

Gas City is the generalization of Steve Yegge's **Gas Town**. Its one non-negotiable rule is **zero
hardcoded roles**. Gas Town's Mayor, Deacon, Polecat, Refinery and the rest become *configuration*
(a **pack**). That way the same engine can run Gas Town, a Ralph loop, an Anthropic-style agent team,
or a custom topology.

**Long-term vision: yes, a clear one, though it is not a dated plan.** The vision has three layers,
and they should be kept apart:

1. **The product thesis** (CEO Chris Sells: "Orchestration Is All You Need"). The engineer's job
   shifts from building the software to *building and improving the factory that builds it*.
   Process knowledge (plan, implement, multi-model review, revise, verify, maintain) becomes
   versioned, shareable configuration. The bet is that better models make factories *better*, not
   unnecessary.
2. **The commercial direction** (Gas City, Inc.) is open core. Beads and Gas City are free. They are
   followed by **Beads Team Server**, a shared and governed work graph that design partners can use
   now, and **Gasworks**, a multi-operator factory offered as managed SaaS or inside your VPC, with
   design partnerships opening **December 2026**. A vendor-neutral hosted-service protocol is
   already in the open-source client.
3. **The near-term engineering roadmap** (1.6, undated, "current thinking, not commitments") covers
   three things: crash-safe session reliability (reconciler v2), performance (moving bookkeeping off
   Dolt to SQLite), and onboarding contributors, whether human or agent.

**The biggest caveat.** Steve Yegge originated the idea and is now an advisor. In April 2026 Yegge
called Gas City "our official new direction." By August 2026 Yegge wrote that Gas Town had "fell
apart at the seams," that "I have given up on building reusable harnesses," and that Yegge now runs
a closed-source, bespoke orchestrator instead. That argument cuts directly against a *reusable*
orchestration SDK. Separately, an independent hands-on review (Every, May 2026) concluded:
"sharp ideas … not yet ready for prime time."

---

## 1. What Gas City is

### Origin and people

- **Beads** came first (Oct 2025). It is Yegge's git- and Dolt-backed issue tracker and "memory
  upgrade" for coding agents.
- **Gas Town** followed, open-sourced 2026-01-01. It showed that dozens of agents could do real work
  with durable memory and handoffs. However, every role was hardwired in Go.
- **Gas City** began 2026-02-22 as a **fresh binary, not a fork**. It was built on the insight
  recorded in the repo's `AGENTS.md`: "the way work is expressed — as beads composed into formulas —
  was powerful enough to abstract roles into configuration."

Yegge's launch essay (2026-04-24) is explicit about who wrote it: "I did not write Gas City. It was
created by Julian Knutsen and Chris Sells… I am only lightly affiliated with the code, in the sense
that I outlined my vision in a blog post, and they built it." The same disclaimer adds "I am all-in
with Gas City, contributing myself, and this is our official new direction!"

| Person | Role (per gascity.com/about) | Notes |
|---|---|---|
| Chris Sells | CEO | Founded the Gas City Hall community. Every credits Sells with growing Flutter. |
| Julian Knutsen | CTO, roadmap owner | "The technical force behind Gas City and the Wasteland." Former Block tech lead. |
| Steve Yegge | Advisor | Creator of Beads and Gas Town. 4 commits in this repo. |
| Donna Box | Advisor | Beads co-maintainer. |

The company is small: it is hiring founding engineers, and a secondary listing shows about six
employees. Development is still concentrated in one person. **Knutsen authored 4,457 of the 7,161
commits on `main` (62%) under two spellings, or 4,053 of 6,689 non-merge commits (61%).** Jim
Wordelman is next with 742.

The repo has 228 distinct author names, including agent identities such as `gascityinc-randy[bot]`,
`randy-release-manager[bot]` and `gascity-eddie[bot]`. Activity is high and has re-accelerated:
commits ran 500–1,400 per month from March to September, and **765 landed in the first 17 days of
October**.

### Shape of the product

- **One `gc` binary** with a CLI, a typed HTTP+SSE API (generated OpenAPI spec), and a run-centred
  web dashboard. The CLI and API are required to be "projections over the domain packages."
- **Configuration, not code.** Users write TOML (`pack.toml` defines a pack; `city.toml` describes a
  deployment) plus Markdown prompt templates. No Go is needed unless you are contributing.
- **"SDK" is aspirational at the library level.** The GitHub description says
  "orchestration-builder SDK," but `AGENTS.md` keeps everything in `internal/` "until the API
  stabilizes." `pkg/` contains only `eventexport`. Today the real extension surfaces are packs,
  formulas, prompts, provider contracts and the HTTP API. **It is not a stable importable Go
  library.**
- **Install:** `brew install gascity`. It needs tmux (required even as a fallback), git, jq, and, for
  the default store, Dolt ≥ 2.1 plus `bd` 1.x. `GC_BEADS=file` gives a lighter store without Dolt.

---

## 2. What people use it for

| Use | What Gas City contributes | Evidence |
|---|---|---|
| **Feature work and bug fixing over your own repos** | Decomposes the request into beads, fans ready work to parallel worktrees, gates steps on dependencies, and drives the run to a branch or PR | This is the core documented workflow. The dispatch code (`internal/dispatch/fanout.go`, `control.go`) implements it. |
| **Review and revise loops** | Multiple reviewers (often *different vendors* on the same diff), a synthesizer, exec `check` gates, and a bounded `max_attempts` | The 1.0 and 1.3 posts show one coder, three reviewers and a synthesizer. Any quality gain is a maintainer claim. |
| **Running Gas Town without Gas Town** | The `gastown` pack rebuilds the Town roles as configuration; `coming-from-gastown.md` maps each role | Launch material called it a drop-in replacement. Current docs advise mapping behaviour rather than copying Town's directory layout. |
| **Multi-repo coordination** | Each repo is a **rig** with its own bead-ID prefix and agent scope inside one city | Documented. Isolation is by prefix over a shared store, not by separate databases. |
| **Scheduled and reactive automation** | **Orders** fire formulas or plain commands on cron, cooldown, condition, event or manual triggers. Health patrol is an order, not a special role. | Documented. Mechanical work needs no LLM worker. |
| **Watching a fleet** | Append-only event stream (`gc events --follow`), dashboard, `bd show --watch`, usage visibility | Shipped (dashboard and registry in 1.4). |
| **Trying different team topologies** | Swap packs, prompts, providers and worker pools. Mixed-vendor fleets are just configuration. | Examples include the hierarchical `gastown` pack and a flatter `examples/swarm`. |
| **Non-coding agent work (aspirational)** | The same primitives could apply to DevOps and monitoring, ETL, ticket queues and incident response | Yegge's launch essay proposes these. None is a validated production use. |

**Dogfooding is the flagship deployment.** The maintainers build Gas City with Gas City. A read-only
"Maintainer City" is public at [factory.gascity.com](https://factory.gascity.com/city/maintainer-city/).
These figures are all self-reported:

- ~100 agents, ~50 merged PRs per day and ~1B tokens per day on Knutsen's server (Every).
- A peak of 74 PRs in one day, and "routinely 30+ agents per project" (Sells).
- A public fleet spanning 23 repositories (company factory guide).
- Named "agentic employees" for releases, SRE and other jobs, reachable over Discord. The bot
  commit identities above corroborate that such personas exist.

**Who it fits today.** It fits operators who already run many agent sessions in parallel, and who
are willing to own their workflows and infrastructure. Every's review suggests it pays off only for
people "already running more than 10 Claude Code sessions in parallel and reading source code." The
review also reports that a room of experienced engineers needed a full day to get it running.

**What it is not.** The FAQ is explicit that it is not a replacement for git, CI or the coding
harness. CI *verifies* a change, while a formula is what *produces* it. A bash respawn loop has no
model of the work; Gas City does.

---

## 3. How it works

### Six user-facing primitives (`docs/getting-started/how-gas-city-works.md`)

| Primitive | Role | Plain meaning |
|---|---|---|
| **Agent** | WHO | A worker definition: provider (harness), prompt template, scope. A running agent is a **session**, and sessions can be pooled (`min/max_active_sessions`, `scale_check`). |
| **Bead** | WHAT | A durable unit of work or state. Tasks, mail, sessions and convoys are all beads that differ by `type`. Blocking `needs` edges give ordering. |
| **Formula** | HOW | A reusable method in TOML: steps, dependencies, inputs, control flow. Applying it *materializes* beads, so the run outlives the file and any session. `gc sling` creates and routes work in one motion. |
| **Rig** | WHERE | A registered project, usually a git repo. |
| **Pack** | CONFIGURES | A directory with `pack.toml` holding agents, formulas, orders, prompts, commands, skills, MCP config and doctor checks. **A city is the root pack** plus deployment settings, and it can import shared packs. |
| **Event** | OBSERVE | An append-only, sequence-numbered record (`bead.closed`, `session.crashed`, `order.fired`, …). Humans and event-triggered orders consume it. |

Three role-agnostic pieces of machinery sit underneath: the **controller** (it reconciles declared
agents to live sessions and executes control beads), the **bead store**, and the **event bus**
(`.gc/events.jsonl`).

### Two details the vocabulary hides

1. **Formula v1 and v2 are different things.** In v1, one agent runs the steps in sequence inside
   its own session. In v2 (`graph.v2`), the controller executes **control beads** (check, retry,
   fan-out, tally, drain, scope-check, workflow-finalize) and routes **work beads** to many agents.
   `AGENTS.md`: "graph orchestration is why Gas City exists." Calling something a formula does not
   make it a multi-agent graph.
2. **Harness and session runtime are separate choices.** The harness answers *which agent*: Claude,
   Codex and so on. The runtime answers *how it is hosted*: tmux (the default), subprocess, exec,
   ACP, Kubernetes, or herdr. `examples/hyperscale` scales a pool to 100 Kubernetes pods. Its
   workers only claim a bead, close it and exit, so it demonstrates the mechanics rather than
   benchmarking 100 real coding agents.

### Storage

Dolt-backed `bd` holds versioned work. Infrastructure bookkeeping (order tracking, wisps,
controller and session records) is moving to a local SQLite ledger. That ledger shipped in 1.5 as
an opt-in, experimental preview, with 130–250× faster infrastructure reads claimed. 1.5 also made
the proxied Dolt server the default (~75% less idle RAM in one test). "Everything is a bead"
describes the *domain model*; it does not mean everything lives in one Dolt database. The many
runbooks for Dolt bloat, compaction and backup show that the Dolt substrate has a real operating
cost.

---

## 4. Design philosophy: the vision as encoded in the code

The repo's `AGENTS.md` is unusually opinionated. It is the most durable statement of what the
maintainers believe will last.

- **Zero hardcoded roles.** "If a line of Go references a specific role name, it's a bug."
- **Keep judgment out of Go** (also called Zero Framework Cognition). "Go handles transport, not
  reasoning… An `if stuck then restart` is framework intelligence. Move the decision to the prompt."
- **The Primitive Test** (`engdocs/contributors/primitive-test.md`). A capability enters the SDK only
  if all three conditions hold:
  1. **Atomicity**: agents can't do it safely without races. An example is a CAS claim on a bead.
  2. **It stays exactly as necessary with a model 10× smarter.** This is the Bitter-Lesson filter.
  3. **It is transport, not cognition.**
- **The system converges because work persists.** Sessions are disposable and beads are durable.
  Redundant idempotent observers are "the reliability mechanism." The controller adopts live
  sessions after a restart. There are no PID or status files: "the process table is the single
  source of truth."
- **SDK self-sufficiency.** "If removing an `[[agent]]` entry breaks an SDK feature, it's a
  violation."
- **Permanent exclusions** ("not 'not yet'"): no skills system ("the model IS the skill system"), no
  capability flags, no MCP or tool registration, no decision logic in Go, no role names.
- **Settled decisions:** a city is a directory, config is TOML, "tutorials win over architecture
  docs," no premature abstraction, and code stays in `internal/` until the API stabilizes.

**A tension in the code (verified).** The "no skills or MCP" exclusions now read more absolute than
the code. PackV2 ships `skills/` and `mcp/` directories, and `internal/materialize/` (`skills.go`,
`mcp*.go`) projects them into each provider's native skill directories and MCP config. The likely
reconciliation is that Gas City doesn't *own* a skill or tool runtime; it only *delivers* pack
content to the harness. Even so, the principle and the implementation have diverged.

---

## 5. The long-term vision, layer by layer

### 5a. Product thesis: "orchestration is all you need"

The thesis comes from Sells' manifesto (2026-04-21) and the 1.0 announcement (2026-04-28):

- Every human engineering process (write, review, iterate, merge, and later PM and UX) can become an
  agentic orchestration.
- Sutton's Bitter Lesson favours the orchestration side. "Orchestrations are how you turn more
  compute into better output, indefinitely." "A better model just makes the orchestration better."
- The end state: "Instead of building the software, you'll be building the factory that harnesses
  agents to build, review, test, deploy, and operate it."
- Quality is meant to be a property of the *formula*: multi-provider review, checks and bounded
  loops. It should not depend on a human sitting in the session.
- Every named orchestration style (Ralph loops, StrongDM-style factories, Anthropic Agent Teams)
  should be capturable as a pack. Packs and the live `registry.gascity.com` (shipped in 1.4) are
  how process knowledge is meant to accumulate and be shared, much as libraries accumulate code.
- **Multiplayer.** Sells calls agentic engineering "largely a single-player sport" today; making it
  multiplayer is a stated target.

### 5b. Yegge's broader framing, and Yegge's later reversal

The launch essay "Welcome to Gas City" (2026-04-24) frames the vision this way:

- "In the very near future, devs will become shepherds, tending flocks of agents which do the
  ground-level work."
- Gas City is "an SDK for building your own dark factories," which Yegge prefers to call a
  **"Light Factory"** because every worker is visible and addressable.
- "Enter Gas City: The ultimate de-SaaSer." "A small team of three to five human engineers running
  Gas City packs can credibly replace seven-figure SaaS bills." Yegge puts this on a multi-year
  horizon.
- The audit trail lives in git-versioned Dolt: "That's your SOC2 story, sitting right there in the
  database, already written."
- The essay extends the idea to non-coding domains and enterprise automation at the scale of
  "hundreds" of agents.

Yegge then reversed course in "The Shape of Things to Come, Part 1: The Continuous Thunderdome"
(August 2026):

- "Gas Town fell apart at the seams with Opus 4.7." "Gas Town effectively burned down."
- "Gas Town was intended to be reusable, but I only ever wound up using it to build itself."
- "**I have given up on building reusable harnesses.** … Harnesses need to be part of your
  application, chemically bonded in."
- Yegge's new orchestrator, **Wheelhouse**, is "closed-source, made just for me."

The August essay does not disavow Gas City. It calls Gas City "also a Beads machine" and praises
"the Dolt and Gas City teams (both Beads co-maintainers with me)." However, it says nothing about
using Gas City, and its central claim contradicts Gas City's premise.

Gas City's implicit answer is the pack model: bespoke behaviour lives in *your* pack, and only
role-free plumbing is shared. **Whether that division holds up is the central open question for the
project's long-term thesis.** This is the lead's reading; neither side states it this way.

**Federation is a sibling project, not a Gas City feature.** The Wasteland is a "wanted board"
across Gas Towns with portable reputation "stamps" over a shared DoltHub database. Knutsen is
credited with it, but it is not an in-tree Gas City primitive.

### 5c. Commercial direction: open core, with a hosted layer on a neutral protocol

The gascity.com homepage tagline is "Agent work that lasts. A factory your team can improve." The
product ladder runs:

| Rung | License | Status (2026-10-17) |
|---|---|---|
| **Beads**: durable agent memory and work graph | Free / OSS | Shipping. Being extended toward "durable organizational memory." |
| **Gas City**: open factory platform, "configured, not coded" | Free / MIT | Shipping (v1.5). |
| **Beads Team Server**: shared, governed beads with provenance, private run history, and model-usage and cost reporting | Commercial | "Available now for design partners, with broader availability coming soon." SaaS or VPC. |
| **Gasworks**: "One factory. Multiple operators." Includes Team Server. | Commercial | "Coming soon." "In active development, and design partnerships open in December 2026." SaaS or VPC. "Bring your own keys. Zero markup." It "never tolls your tokens." |

Neither commercial page gives prices. December 2026 is when *design partnerships open*, not general
availability. These pages describe intentions and should not be read as capabilities of the
open-source repo.

**The open-source client is already shaped for hosting:**

- `docs/reference/specs/service-protocol-v0.md` (`gascity.dev/service/v0`) defines a vendor-neutral
  wire protocol. `https://gascity.com` is only a default URL. The design doc describes it as "the
  git/github, docker/docker.io shape — a URL is configuration data, not commercial code."
- Only auth has shipped: `gc login` and `gc whoami` (July 2026). **Cities** (`POST /gc/v0/cities`,
  for `gc init --at`) and **Runs** (`POST /gc/v0/runs`, for `gc run --at`, including anonymous runs)
  are *reserved surface*.
- A CI guard (`scripts/check-core-boundary.sh`) keeps billing, trial and plan logic out of the
  open-source tree.
- `engdocs/plans/hosted-onboarding/DESIGN.md` is marked "exploration/design. No code." It lays out
  three onboarding flows:
  - a zero-install web playground;
  - a `gc init --at` hosted wizard;
  - anonymous `gc run --at`, the "killer demo." The doc warns this is "RCE-and-inference-as-a-service
    to strangers" until credential-less LLM egress and sandboxing exist.
- In that design, the hosted controller runs **stock open-source `gc`**. The open-source client is
  "~10% of the work" and the private hosted server is "~90%."
- Self-hosted remote cities already have a runbook (`docs/runbooks/remote-hardened-city.md`), so
  gascity.com is not required.

### 5d. Engineering trajectory

The current roadmap is `ROADMAP.md`, owned by @julianknutsen and last updated 2026-10-05. It names
three "priority areas for 1.6," gives no dates, and is rewritten at least once per minor release.

| Area | Goal | Named work | Tracking |
|---|---|---|---|
| **Session and reconciler reliability** | After a crash, restart or upgrade, a city returns to the correct state with no manual intervention | Keyed **reconciler v2** fully replaces the legacy tick reconciler, which is then deleted; P0 and P1 session bugs burn down | [#7093](https://github.com/gastownhall/gascity/issues/7093) |
| **Performance** | "Fast and quiet as cities grow" | Infrastructure-class beads move to SQLite while Dolt keeps work beads ([#3926](https://github.com/gastownhall/gascity/issues/3926)); `gc`, `bd` and reconciler hot paths; numeric targets wait for a benchmark | [#7094](https://github.com/gastownhall/gascity/issues/7094) |
| **Contributor onboarding** | "A new contributor, human or agent," finds the rules next to the code | Slim root `AGENTS.md`; per-package `AGENTS.md` for `cmd/gc`, `internal/beads` and `internal/dispatch`; package docs and a generated codebase map; `help-wanted` starter issues | [#7095](https://github.com/gastownhall/gascity/issues/7095) |

**Reconciler v2 is not yet the default.** Its design doc (last verified 2026-10-03) lists `legacy`
as the default `session_reconciler`, with v2 opt-in. The doc is also internally inconsistent: its
summary describes a trace-only "P2 skeleton," while its Admission section describes a completed
cutover. 1.6 is about finishing that cutover.

**Further-out directions found in the repo:**

- **Machine-wide supervisor.** The design (`engdocs/design/machine-wide-supervisor-v0.md`) was
  accepted 2026-03-06. Per-city controllers become an Erlang/OTP-style supervision tree with a
  `/v0/cities` API, "explicitly prepar[ing] for future multi-tenant hosting." A `gc supervisor`
  command exists, but whether the full tree is implemented was not verified.
- Public `pkg/` SDK exports, once the API stabilizes.
- The `worker.Handle` boundary migration, which is CI-enforced and in progress.
- An external messaging fabric, and Kubernetes and ACP backends for remote fleets.
- An internal framework survey (`engdocs/research/w-gc-004-orchestration-framework-survey.md`). It
  compares Gas City with AutoGen, CrewAI, LangGraph, the OpenAI Agents SDK, the Claude Agent SDK and
  Magentic-One. It names **no checkpoint primitive** as an honest gap: work resumes at bead
  boundaries, not mid-step as in LangGraph.

`examples/gastown/SDK-ROADMAP.md` and `FUTURE.md`, and anything under `engdocs/archive/`, are early
gap analyses. They are evidence of how the project got here, not live intent.

**Overall read.** The open-source agenda is to stabilize and scale the factory: make it dependable
and cheap enough to carry the team and hosted ambitions built on top of it. It is not chasing a new
product category.

---

## 6. Maturity, risks and counterpoints

- **Independent verdict.** Every's "mini-Vibe Check" (Katie Parrott, 2026-05-19) says: "sharp ideas
  … not yet ready for prime time." Mike Taylor of Every adds: "Learn from the ideas. Skip the
  toolkit for now." The review names these problems:
  - Cost: "a six-step job can cost six times the cost of one Claude session."
  - Deliberately unfamiliar vocabulary.
  - Fresh sessions per step that don't remember earlier steps.
  - Beads is CLI-first, so production teams pair it with Jira or Linear.

  The review predates releases 1.3 through 1.5.
- **The originator's reversal** (§5b) is the strongest argument against the reusable-SDK thesis.
- **Operational weight.** tmux is mandatory, the Dolt substrate needs runbooks, and the storage
  migration tooling is experimental. 1.5 flags `gc storage migrate` as unsafe on production cities
  you cannot restore.
- **Churn.** There have been six minor releases in about six months (v1.0 tagged Apr 21, v1.1
  May 6, v1.2 May 29, v1.3 Jun 18, v1.4 Jul 24, v1.5 Oct 4). Each has upgrade notes and
  `gc doctor --fix` migrations.
- **Persistence is not correctness.** Durable beads let a replacement session resume. They do not
  prove that a review was sound, that an external action is safe to repeat, or that the code meets
  an unstated requirement. The ongoing reliability work also argues against taking the launch-era
  assurances as settled.
- **Not a sandbox.** `docs/reference/trust-boundaries.md` treats imported packs and configured
  commands as trusted code. Runtimes, permissions and credentials are the operator's
  responsibility. This matters for the enterprise ambition and for anonymous hosted runs.
- **Autonomy incidents.** Beads v1.2.0 and v1.2.1 "went out by mistake on 2026-08-11 without release
  testing." v1.2.1 migrated local schemas so that older binaries refused to run, and v1.2.2
  re-released the tested 1.1 line. The cld report says the team attributed the release to an
  autonomous agent maintainer; the lead confirmed only the accidental, untested release.
- **Concentration.** About 62% of commits on `main` come from one person.
- **Documentation drift.** The reconciler-v2 doc contradicts itself. `SUPPORT.md` says there is no
  real-time support channel, yet the README points to Discord. Branding is split across
  `docs.gascityhall.com`, `docs.gascity.com`, `gascity.com` and the `gastownhall` GitHub org.
- **Do not conflate:** Kilo's hosted *Gas Town* cloud product is a different product from Gasworks.

---

## 7. Where the researchers disagreed, and how it was resolved

| Point | Reports said | Resolution (lead's verification) |
|---|---|---|
| Knutsen's commit share | cld: ~4,050 of 7,161 (~57%). grk: ~8,500 commits. | Both used mismatched scopes. On `main` the figure is **4,457 of 7,161 (62%)**, or **4,053 of 6,689 non-merge (61%)**. grk's ~8,500 counted *all refs* (17,100 commits). cld divided a non-merge numerator by an all-commit denominator. |
| Primitive Test, condition 1 | gem: "can it be decomposed into existing primitives?" | **Incorrect.** Condition 1 asks whether agents can do the operation safely without races, in which case the SDK must supply the atomic version. cld, grk and cdx were right. |
| "NDI" principle | gem: "Non-Destructive Interaction" | **Incorrect.** The term appears in an archived doc as **"Nondeterministic Idempotence."** The idea (sessions die, work survives) is real, but the name was wrong. |
| Hosted-service analogy | gem: git/GitHub. grk: docker/docker.io. | **Both.** `DESIGN.md` says "the git/github, docker/docker.io shape." |
| Yegge's role | gem: Yegge and Knutsen "realized" the insight together and Knutsen maintains it. cld: Yegge is only lightly affiliated. | `AGENTS.md` credits the insight to Yegge, and Knutsen and Sells built it. Yegge said "only lightly affiliated" **and** "all-in… our official new direction" in April, then moved to a private harness in August. |
| Every review author | cld: Katie Parrott with Mike Taylor. Search snippet: Mike Taylor. | Katie Parrott wrote it; the verdict quote is from Mike Taylor. |
| Reconciler v2 status | cdx: avoid claiming it shipped. gem: deleting the legacy loop is under way. | **Legacy is still the default; v2 is opt-in.** Completing the cutover is the 1.6 goal. |
| Erlang/OTP controller | gem presented it as current architecture | It is an **accepted design** (2026-03-06). Whether it is fully implemented was not verified. |
| Maintenance use cases | gem: flaky-test patrol, dependency drift, cross-repo PR cascades | These are **illustrative**. They are plausible with orders and rigs, but the lead did not find them as documented examples. |
| Long-term vision | mus: no single vision manifesto in the repo. Others: a clear vision exists. | **Both are true.** There is no dated multi-year plan in the repo, but the thesis is stated consistently across `AGENTS.md`, Sells' essays, Yegge's essays and gascity.com. |
| Release dates | Various | Tags: v1.0.0 2026-04-21, v1.3.0 06-18, v1.4.0 07-24, v1.5.0 10-04. The launch posts followed days later: Yegge Apr 24, Sells Apr 28, 1.3 post Jul 3, 1.4 post Jul 28, 1.5 post Oct 7. |

---

## 8. Relevance to SASE (brief)

Gas City is the closest public analogue to SASE's design space: beads as the durable substrate,
mixed-vendor fleets of CLI agents, host-driven orchestration, and `AGENTS.md`-governed
contributors. The useful contrasts:

- **Agent lifetime.** Gas City keeps long-lived tmux sessions, adopts them after restarts, and
  relies on nudges and mail. SASE agents are single-turn, with mechanical continuation.
- **The judgment/transport line.** Gas City's Primitive Test and "keep judgment out of Go" rule are
  a crisp litmus test, close in spirit to SASE's Rust-core boundary test.
- **Graph control vocabulary.** Formula v2's control beads (check, retry, fan-out, tally, drain) are
  a concrete model for graph orchestration over beads.
- **Hosted protocol discipline.** "A URL is configuration, not vendor logic," enforced by a CI
  boundary script, is a clean pattern if SASE ever adds a hosted service.
- **Cautionary data.** The cost per fresh step and Yegge's "reusable harnesses" reversal are worth
  weighing against any plan to generalize SASE's orchestration for other users.

---

## Sources

**Repository** (opened via `sase repo open gh:gastownhall/gascity`; links pinned to `2dec01c71a`):

- [README.md](https://github.com/gastownhall/gascity/blob/2dec01c71a3dd5cdd0ca494ea7c72f4806d6c770/README.md),
  [AGENTS.md](https://github.com/gastownhall/gascity/blob/2dec01c71a3dd5cdd0ca494ea7c72f4806d6c770/AGENTS.md),
  [ROADMAP.md](https://github.com/gastownhall/gascity/blob/2dec01c71a3dd5cdd0ca494ea7c72f4806d6c770/ROADMAP.md),
  CHANGELOG.md
- [how-gas-city-works.md](https://github.com/gastownhall/gascity/blob/2dec01c71a3dd5cdd0ca494ea7c72f4806d6c770/docs/getting-started/how-gas-city-works.md),
  [faq.md](https://github.com/gastownhall/gascity/blob/2dec01c71a3dd5cdd0ca494ea7c72f4806d6c770/docs/getting-started/faq.md),
  [coming-from-gastown.md](https://github.com/gastownhall/gascity/blob/2dec01c71a3dd5cdd0ca494ea7c72f4806d6c770/docs/getting-started/coming-from-gastown.md),
  [understanding-formulas.md](https://github.com/gastownhall/gascity/blob/2dec01c71a3dd5cdd0ca494ea7c72f4806d6c770/docs/guides/understanding-formulas.md),
  [understanding-packs.md](https://github.com/gastownhall/gascity/blob/2dec01c71a3dd5cdd0ca494ea7c72f4806d6c770/docs/guides/understanding-packs.md),
  `docs/guides/harness-recipes.md`,
  [trust-boundaries.md](https://github.com/gastownhall/gascity/blob/2dec01c71a3dd5cdd0ca494ea7c72f4806d6c770/docs/reference/trust-boundaries.md)
- `docs/reference/specs/service-protocol-v0.md`, `engdocs/plans/hosted-onboarding/DESIGN.md`,
  `internal/cliauth/AGENTS.md`, `scripts/check-core-boundary.sh`
- [primitive-test.md](https://github.com/gastownhall/gascity/blob/2dec01c71a3dd5cdd0ca494ea7c72f4806d6c770/engdocs/contributors/primitive-test.md),
  [reconciler-v2.md](https://github.com/gastownhall/gascity/blob/2dec01c71a3dd5cdd0ca494ea7c72f4806d6c770/engdocs/architecture/reconciler-v2.md),
  `engdocs/design/machine-wide-supervisor-v0.md`,
  `engdocs/research/w-gc-004-orchestration-framework-survey.md`,
  `engdocs/proposals/{skill,mcp}-materialization.md`, `internal/materialize/`,
  `engdocs/archive/backlogs/worktree-roadmap.md`
- `internal/dispatch/{fanout,control}.go`, `internal/beads/sqlite_store.go`,
  `examples/{swarm,hyperscale,gastown}/`
- `git log`, `git shortlog` and tags. Tracking issues #7093, #7094 and #7095.

**First-party web:**

- Chris Sells:
  - [Orchestration Is All You Need](https://sellsbrothers.com/orchestration-is-all-you-need) (2026-04-21)
  - [Announcing Gas City 1.0](https://sellsbrothers.com/announcing-gas-city-1-0) (2026-04-28)
- Release posts:
  - [Gas City 1.3](https://blog.gascity.com/posts/gas-city-1-3-now-were-looping-with-gas/) (07-03)
  - [Gas City 1.4](https://blog.gascity.com/posts/gas-city-1-4-the-view-from-the-factory-floor/) (07-28)
  - [Beads 1.3 and Gas City 1.5](https://blog.gascity.com/posts/beads-1-3-and-gas-city-1-5/) (10-07)
- Company pages: [gascity.com](https://gascity.com/), [About](https://gascity.com/about/),
  [Beads Team Server](https://gascity.com/beads-team-server/), [Gasworks](https://gascity.com/gasworks/),
  [AI software factory guide](https://gascity.com/guide/ai-software-factory/),
  [Maintainer City](https://factory.gascity.com/city/maintainer-city/)
- Steve Yegge:
  - [Welcome to Gas City](https://yegge.ai/essays/welcome-to-gas-city/) (2026-04-24)
  - [The Shape of Things to Come, Part 1: The Continuous Thunderdome](https://yegge.ai/essays/the-shape-of-things-to-come/) (Aug 2026)
  - [yegge.ai/gastown.html](https://yegge.ai/gastown.html)

**Independent and secondary:**

- Katie Parrott, Every, [Inside the 100-agent Software Factory](https://every.to/context-window/inside-the-100-agent-software-factory) (2026-05-19)
- [Beads v1.2.2 release notes](https://newreleases.io/project/github/gastownhall/beads/release/v1.2.2) (accidental 1.2.0/1.2.1 release)
- [Built In company listing](https://builtin.com/company/gas-city) (company size)
- Very Good Ventures [interview with Sells](https://verygood.ventures/blog/chris-sells-gas-city-future-of-software-development-ai-and-quality/) (2026-07-22, via cld)

**Lower confidence, from the swarm's notes:** The New Stack and Kilo cloud coverage and the
Wasteland federation details rest on search snippets. The GitHub wiki roadmap (May 2026) was an
incomplete fetch.

## Confidence

- **High:** what Gas City is, its architecture and philosophy, its release history, its 1.6 roadmap
  and its commit statistics (all from the repo); the commercial product ladder and its status (from
  first-party pages); Yegge's April and August statements (fetched verbatim).
- **Medium:** traction and throughput numbers (self-reported); the reading that Yegge's August
  essay threatens Gas City's premise (the lead's interpretation, not stated by either side); how far
  the machine-wide supervisor and reconciler v2 cutover are implemented.
