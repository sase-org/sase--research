---
create_time: 2026-10-17
updated_time: 2026-10-17
status: complete
tags:
  [
    gascity,
    gastown,
    beads,
    software-factory,
    multi-agent-orchestration,
    gas-city-inc,
  ]
---

# Gas City: what it is for, and where it is heading

**Question.** What is [gastownhall/gascity](https://github.com/gastownhall/gascity) used for? What is the long-term vision, if any?

**Researcher.** grk. Independent report. I did not read peer reports from this swarm.

**Checkout studied.** External clone of `gh:gastownhall/gascity` at commit `2dec01c71` (2026-10-17, `fix: preserve fresh sessions handling claimed work (#8012)`). Latest tagged release: **v1.5.0** (2026-10-05). GitHub metadata at the time of this write: **1,395 stars**, **447 forks**, MIT license, Go, created 2026-02-22.

## Bottom line

Gas City is an **orchestration-builder SDK** — a Go toolkit and `gc` CLI that turns a fleet of existing coding agents into a **customer-owned software factory**. You write *how* a job gets done once (a **formula**). A controller runs that method as a graph of durable **beads**, fanning independent steps across many agents, gating on dependencies, retrying failures, and finishing the job **outside any one chat session**. Roles such as Mayor or Polecat are **pack configuration**, not Go types. The same engine can be Gas Town, a Ralph loop, Anthropic-style agent teams, or a custom topology.

The long-term vision is stated clearly and is not a five-year Gantt chart. The product bet is: **the engineer’s job becomes building and improving the factory**, while agents execute the work. Near-term OSS work (the 1.6 roadmap, last rewritten 2026-10-05) is reliability, performance, and contributor onboarding. The company around the repo — **Gas City, Inc.** — is productizing the same factory as **Beads Team Server** (team-shared work graph, design partners now) and **Gasworks** (multi-operator hosted or VPC factory, design partnerships targeted for December 2026). A published `gascity.dev/service/v0` protocol already reserves hosted **cities** and **runs** so `gc login` / `gc init --at` / `gc run --at` can talk to any conforming server, with commercial policy kept out of the OSS binary.

## 1. What the repository is

Gas City is the **platform extraction** of Steve Yegge’s Gas Town. Gas Town (open-sourced 2026-01-01) proved that a multi-agent coding workspace could run dozens of agents with durable memory, handoffs, and parallel work. Its roles — Mayor, Deacon, Witness, Refinery, Polecat, Crew, Dog — were **hardwired in Go**. Gas City was started 2026-02-22 as a **fresh `gc` binary, not a fork**, with the design rule: **zero hardcoded roles**. If a line of Go names a role, that is a bug.

The in-repo origin story (`AGENTS.md`):

> Gas Town proved multi-agent orchestration works, but all its roles are hardwired in Go code. Steve realized the way work is expressed — as beads composed into formulas — was powerful enough to abstract roles into configuration. Gas City extracts that insight into an SDK where Gas Town becomes one configuration among many.

Yegge’s own site puts the scale claim next to that extraction: Gas Town runs **dozens** of parallel agents; Gas City is meant to run **hundreds** and to cover **large enterprise AI automation** ([yegge.ai/gastown.html](https://yegge.ai/gastown.html)).

**People and org.** The GitHub org is [gastownhall](https://github.com/gastownhall). The company is [Gas City, Inc.](https://gascity.com/about/):

| Person | Role |
|---|---|
| Chris Sells | CEO; Gas Town Hall community founder |
| Julian Knutsen | CTO; roadmap owner; dominant commit author (~8,500 commits under two identities) |
| Steve Yegge | Advisor; creator of Beads and Gas Town |
| Donna Box | Advisor |

The public GitHub description is “Orchestration-builder SDK for multi-agent coding workflows.” Docs and the company site more often say **software factory platform**. Those are the same product at two altitudes: SDK is how it is built; factory is what a user is supposed to own.

**License and cost.** MIT. The FAQ’s cost claim is that Gas City itself is free; spend is the model usage of whatever harnesses you already pay for.

## 2. What people actually use it for

### 2.1 Day-to-day operator loop

A **city** is a directory: `city.toml` (this deployment), a root **pack** (`pack.toml` plus `agents/`, `formulas/`, `orders/`, …), and `.gc/` runtime state. A **rig** is a git repo registered with that city (`gc rig add`). Typical first path from the README:

```bash
brew install gascity
gc init ~/bright-lights
cd ~/bright-lights
gc start
gc rig add .
bd create "Create a script that prints hello world"
gc session attach mayor
```

Or, for Town veterans: `gc sling mayor "add a /health endpoint"`, then `gc session list` / `gc session attach mayor`.

What that buys versus sitting in one Claude/Codex session:

- Work is a **bead** in a durable store (default: **bd** + **Dolt**; optional file store via `GC_BEADS=file`). A crashed agent leaves open beads; a fresh session picks them up.
- A **formula** is a reusable TOML method. Under the **v2 / `graph.v2` contract**, the controller — not the agent you slung to — executes control beads (check, retry, fan-out, tally, drain, scope-check, workflow-finalize) and fans ready work beads to many agents. **v1** still exists as a peer: one agent runs the steps in sequence in its own session.
- **Orders** fire formulas on cooldown, cron, condition, event, or manual trigger. Health patrol is an order, not a Deacon binary.
- A **controller/supervisor** reconciles declared agents against live sessions (tmux by default; also subprocess, exec, ACP, Kubernetes, herdr).
- Humans and agents **observe** through an append-only event stream (`gc events --follow`), the dashboard, and `bd show --watch`.

The docs’ canonical user story: describe a feature once, come back to a **finished branch**. The factory decomposes the work, implements pieces in parallel, reviews, gap-checks, and fills holes. Review/gap-check is the quality story; fan-out is the speed story.

### 2.2 What it is *not*

The FAQ is explicit. A bash loop can respawn an agent but has no model of the work. CI **verifies** a change after you make it; a formula is what **produces** the change. Gas City does not replace git, CI, or the coding harness. It orchestrates them.

Permanent exclusions (`AGENTS.md`, Primitive Test):

- No skills system in the SDK — “the model IS the skill system.”
- No capability flags — a sentence in the prompt is enough.
- No MCP/tool registration as platform — if a tool has a CLI, the agent uses it.
- No judgment in Go — `if stuck then restart` is a design violation; that decision belongs in a prompt or a formula check.
- No hardcoded role names.

A primitive must pass three tests: it needs atomicity the tools do not already provide; it stays useful as models improve (plumbing, not heuristics); it is transport, not cognition. That is the same “bitter lesson” argument Chris Sells makes in *Orchestration Is All You Need*: waiting for one perfect model is the wrong bet; more compute through orchestrated, multi-provider review is the bet that scales.

### 2.3 Who it is for, in practice

Three overlapping audiences show up in the docs and company site:

1. **Gas Town operators** moving to a primitive-first model. The Gastown pack reconstitutes Mayor / Deacon / Witness / Refinery / Polecat / Crew / Dog as configuration. Command map: `gt` → `gc` / `bd`.
2. **Teams already running multi-agent work by hand** (several terminals, chat as the scheduler, prompts in random files). The “Set Up a Multi-Agent Engineering Environment” guide is the migration path: pack = portable team definition; `city.toml` = this deployment; `.gc/` = machine-local runtime.
3. **The maintainers themselves.** Gas City is built with Gas City. Public **Maintainer City** at [factory.gascity.com](https://factory.gascity.com/city/maintainer-city/) is a read-only view of that factory. Company copy (checked 2026-08-07 on the factory guide) says that public fleet spanned **23 repositories**. Sells has cited a peak of **74 PRs in a day** and “routinely 30+ agents per project.” Those are operator-reported figures, not independent measurements.

## 3. How the machine is factored (the six primitives)

User-facing model (`docs/getting-started/how-gas-city-works.md`):

| Primitive | Role | Meaning |
|---|---|---|
| **Agent** | WHO | Configured worker: name, provider, prompt template, scope. A running agent is a **session**. Pools scale with `scale_check` / min / max sessions. |
| **Bead** | WHAT | One durable unit of work. Tasks, mail, sessions, convoys differ by `type`. Dependencies are blocking `needs` edges. |
| **Formula** | HOW | Written-down method. Applying it materializes beads; the run then outlives the file and any session. **Sling** (`gc sling`) creates and routes in one motion. |
| **Rig** | WHERE | A project registered with the city. Isolation is by bead-ID prefix over a shared store, not a separate database. |
| **Pack** | CONFIGURES | Directory with `pack.toml`. The city *is* the local pack and can import shared packs. |
| **Event** | OBSERVE | Fired, not polled. Sequence numbers let watchers replay. Event-triggered orders close the automation loop without a special agent role. |

Underneath: orchestrator, bead store, event bus. None of that machinery knows what “reviewer” means. Layering invariants: no upward imports; beads are the persistence substrate; events are outbound notification; config is activation; I/O lives at Layer 0; the controller drives SDK infrastructure so that **removing a `[[agent]]` entry must not break an SDK feature**.

**Harness coverage.** Sixteen built-in harnesses, including Claude Code, Codex CLI, Gemini CLI, Cursor Agent, GitHub Copilot, Sourcegraph AMP, OpenCode, Grok, Kimi Code, and Pi (`docs/guides/harness-recipes.md`). Each agent can pick its own harness; mixed fleets are configuration.

**Storage.** Default beads provider is `bd` (Dolt-backed, Dolt ≥ 2.1.0, bd ≥ 1.0.0). File store is the light path. v1.5 / 1.6 direction: keep **versioned work beads on Dolt**, move **infra-class beads** (order tracking, wisps, controller/session bookkeeping) to **local SQLite** so bookkeeping stops loading the versioned store (tracking issue [#7094](https://github.com/gastownhall/gascity/issues/7094), related [#3926](https://github.com/gastownhall/gascity/issues/3926)).

**Runtime backends.** tmux is required even when another backend is primary (it is the fallback). Kubernetes is real enough to ship `examples/hyperscale` — a “shock and awe” demo that scales a worker pool to **100 pods**. `contrib/k8s/` has controller/agent Dockerfiles, Dolt StatefulSet, and RBAC.

## 4. Ecosystem it sits in

Gas City is one layer of a stack that shares Beads as the ledger:

| Piece | What it is | Relation to Gas City |
|---|---|---|
| **Beads** (`gastownhall/beads`) | Durable work ledger / “memory upgrade” for coding agents. Shipped Oct 2025. ~28k stars on the org listing. | Universal persistence substrate. `gc bd` is a passthrough. |
| **Gas Town** (`gastownhall/gastown`) | Opinionated multi-agent workspace with hardcoded roles. ~18k stars. | Now expressible as the **gastown pack** on Gas City. |
| **Gas City** | Role-free orchestration SDK / factory engine. | This repo. |
| **gascity-packs** | First-party and community packs. | Imported by cities; published through `registry.gascity.com`. First-party catalog includes `gascity`, `gastown`, `cass`, `discord`, `github`, Slack variants. |
| **Wasteland** | Federation / “wanted board” across Gas Towns, with portable reputation (stamps). | Adjacent; Julian Knutsen is described as technical force behind both Gas City and Wasteland. Cross-town federation is **not** an in-tree Gas City primitive (an archived parity note marked `gt wl` as N/A / future). |
| **Beads Team Server** | Commercial shared, governed Beads graph. Design partners now; SaaS or VPC. | Team layer above solo OSS Beads/Gas City. |
| **Gasworks** | Commercial multi-operator factory platform; Beads Team Server included. “Coming soon”; design partnerships **December 2026**. BYOK, “zero markup” on tokens. | The hosted/multi-operator product the OSS protocol is designed not to bake into `gc`. |

Other org repos that matter operationally: `homebrew-gascity`, `gascity-otel`, `gascity-project-dashboard`, `acp-unreal`, `rbe-worker`, community/website properties (`gascityhall.com`, `docs.gascity.com`, `docs.gascityhall.com`, Discord `discord.gg/xHpUGUzZp2`).

Kilo hosts a **Gas Town** cloud product (GA May 2026, per third-party research). That is a different commercial host of Town, not Gasworks. Do not collapse them.

## 5. Long-term vision

There is a vision. It is repeated in first-party docs, Sells’s essays, Yegge’s site, and the company homepage. It is **not** a dated multi-year roadmap inside `ROADMAP.md`. Treat three layers separately.

### 5.1 Product thesis (stable)

Stated on the docs homepage and [gascity.com/guide/ai-software-factory](https://gascity.com/guide/ai-software-factory/):

> There are two ways to put coding agents to work. The first is the interactive session. The second is to automate the work itself: turn a fleet of agents into a software factory that runs without you in the loop. An interactive session gives you a faster pair of hands; a software factory is what gets you production quality at machine speed.

Chris Sells, *Announcing Gas City 1.0!* (2026-04-28) and *Orchestration Is All You Need* (2026-04-21):

- A software factory is “a system for building, validating, deploying, operating, and maintaining production software.”
- Quality comes from **multi-provider, multi-agent review loops** encoded as formulas (his example: one coder + Codex/Claude/Gemini reviewers + a synthesizer, looping up to three times).
- “Your job has changed. Instead of building the software, you’ll be building the factory that harnesses agents to build, review, test, deploy, and operate it.”
- The old “features, quality, schedule: pick two” becomes “pick three” via factories (Product Hunt / Sells).
- Any named orchestration style — Ralph Loops, StrongDM-style factories, Anthropic Agent Teams — should be **capturable as a pack**.
- They already run **agentic employees** (Sells: “15 agentic employees” spanning marketing to release management, Discord-chatty via OpenClaw-style packs). That is a company operating model, not an OSS feature flag.

Yegge’s complementary claim: Gas City is the **next-generation declarative orchestration toolkit** on the Beads ledger, sized for **hundreds of concurrent agents** and **enterprise AI automation**. Secondary news aggregators (KuCoin/Phemex, 2026-04-24) attribute a stronger claim to him — Gas City as a **general-purpose business process orchestrator**, with an anecdote of non-technical staff replacing a $30k/year SaaS tool. I could not retrieve the full *Welcome to Gas City* Medium body (bot wall). Treat the SaaS-replacement anecdote as **unverified secondary**; the SDK/enterprise-automation framing is first-party on yegge.ai.

Design decisions marked **settled** in `AGENTS.md` (do not revisit): city-as-directory; fresh binary; TOML for `pack.toml` / `city.toml`; tutorials win over architecture docs when they conflict; no premature abstraction; Mayor-as-overseer is a *pack* convention (“the mayor plans; coding agents work”); **`internal/` until the API stabilizes** — **`pkg/` SDK exports are future work**.

### 5.2 Near-term OSS (1.6, current)

`ROADMAP.md` (owner [@julianknutsen](https://github.com/julianknutsen), last updated **2026-10-05**) is explicit that it is **current thinking, not commitments**, with **no dates**, rewritten at least once per minor release. Three priority areas:

1. **Session and reconciler reliability** ([#7093](https://github.com/gastownhall/gascity/issues/7093), open). After crash/restart/upgrade, a city converges with no manual intervention. Reconciler v2 fully replaces the legacy tick reconciler; P0/P1 session bugs burn down.
2. **Performance** ([#7094](https://github.com/gastownhall/gascity/issues/7094), open). Infra beads → SQLite; Dolt keeps versioned work; hot-path `gc` / `bd` / reconciler work. Numeric targets wait on a benchmark.
3. **Contributor onboarding** ([#7095](https://github.com/gastownhall/gascity/issues/7095), open). Slim root `AGENTS.md`, colocated area rules, per-package `AGENTS.md`, generated codebase map, `help-wanted` starters.

That is a **stabilize-and-scale the factory** agenda, not a new product category.

v1.5.0 (2026-10-05) already shows the same theme: bd 1.3.1 pin, experimental `gc storage migrate`, Dolt compact/federation caution, identity cleanups for pool sessions, retry-counter contract (`gc.retry_attempt`). HEAD on 2026-10-17 is deep in session/worker internals: turn observation, incarnation fences, nudge-queue, opjournal conversation lanes, t3bridge. The factory is being hardened so graph orchestration can be the default operating mode, not a demo.

Historical note: `examples/gastown/SDK-ROADMAP.md` and `FUTURE.md` are **early gap analyses** (“~1,200 lines of Go to make Gas Town run as pure configuration”). Most of those `gt` commands are now marked resolved as `bd` operations, controller jobs, or prompt logic. Do not treat those files as the live roadmap.

### 5.3 Company / hosted (12–24 months)

This is the part of “long-term vision” that lives **beside** the OSS repo, with a deliberate legal/technical seam.

- **gascity.com** positions three rungs: open Beads (solo memory), open Gas City (solo/professional factory), **Beads Team Server** (shared governed graph), then **Gasworks** (multi-operator factory). Configuration is meant to **move from Gas City to Gasworks without converting it**.
- OSS `gc` already speaks a **vendor-neutral hosted-service protocol** (`docs/reference/specs/service-protocol-v0.md`, `gascity.dev/service/v0`). Default URL `https://gascity.com` is configuration, like `docker login` defaulting to Docker Hub. Billing, trials, orgs, quotas **must never be wire fields**; they arrive as opaque `message` / `links`. Enforced by `scripts/check-core-boundary.sh` and `internal/cliauth` goldens. Hosted billing/provisioning lives in **private** repos.
- Reserved v0 surface, not fully specified in the same file: **Cities** (`POST/GET /gc/v0/cities` — `gc init --at`) and **Runs** (`POST/GET /gc/v0/runs` — `gc run --at`, including anonymous). `engdocs/plans/hosted-onboarding/DESIGN.md` (exploration, “no code” in that note) sequences: web playground first (Julian’s “value without installing a CLI”), then `gc init --at` hosted wizard, then anonymous `gc run --at` as the flagship demo **after** credential-less LLM egress and sandbox controls exist. Verdict in that design: OSS client is ~10% of the work; hosted server ~90%; hosted controller is intended to run **stock OSS `gc`**.
- Self-hosted remote cities already have a runbook (`docs/runbooks/remote-hardened-city.md`): signed write grants, `gc rig add --git-url` server-side clone, no requirement to use gascity.com.
- Pack registry at `registry.gascity.com` is live (called out in the v1.4 “factory floor” post). Publishing is a hosted review flow (`gc pack registry publish`).

**Gasworks timing.** Company page: design partnerships open **December 2026**. That is a product calendar, not an OSS milestone.

### 5.4 What would count as “the vision succeeding”

From first-party sources, success looks like:

- A professional developer owns a **repeatable, inspectable factory configuration** (agents, formulas, orders, packs) that produces **reviewed pull requests** without babysitting terminals.
- The same configuration is **portable** across machines, teammates, and eventually Gasworks.
- Quality is a **property of the formula** (multi-agent review, checks, retries), not of sitting in the session.
- The SDK stays a **thin transport layer** that gets *more* valuable as models improve, while packs capture every competing orchestration fashion.
- Optionally: hosted cities/runs and a multi-operator control plane, without contaminating the MIT client with vendor policy.
- Optionally, on Yegge’s framing: the same engine used beyond coding, as enterprise automation — **aspirational**, not what `ROADMAP.md` is executing now.

## 6. Maturity and caveats

- **Young, large, very active.** First commit 2026-02-22; v1.0.0 on 2026-04-21 (610 commits / +304k lines in the v0.15.1→v1.0 window per CHANGELOG); v1.5.0 on 2026-10-05; HEAD still merging multiple features per day. ~8,121 tracked files, ~5,645 Go files at the studied commit.
- **Operationally heavy.** Default path wants tmux, git, jq, Dolt, bd, flock. Managed Dolt has real failure modes (bloat, compact vs remotes, proxied idle timeouts). v1.5 calls `gc storage migrate` **experimental** and unsafe on production cities you cannot restore.
- **Docs vs SUPPORT.md.** README/docs point at Discord; `SUPPORT.md` still says there is no real-time support channel. Discord is the live community; SUPPORT.md looks stale.
- **`pkg/` is not the public SDK yet.** Despite “SDK” in the description, exports are future work; everything is private to `gc` until the API stabilizes.
- **Wiki roadmap** (last edited 2026-05-24 by Chris Sells) mentioned v3 orchestration, a recommended starter pack (Plan/Design/Implement/Bug Fix/PR Review), factory-floor visualization, pack registry, and team usage. Pack registry and factory dashboard have since shipped. Prefer in-tree `ROADMAP.md` over that wiki page for current priorities; the wiki fetch returned an empty body here.
- **Wasteland ≠ Gas City.** Federation is a sibling project. Do not describe Gas City as already linking “a thousand towns.”

## 7. Conclusions

**Used for.** Running **multi-agent software factories**: durable bead-backed work, pack-configured roles, formula graphs executed by a controller, orders for automation, events for observation, across local tmux, exec, ACP, Kubernetes, or (emerging) hosted cities. Concrete jobs: feature delivery with parallel implement/review, the maintainers’ own 24/7 repo factory, reconstituting Gas Town as config, and swapping harnesses without rewriting workflows.

**Long-term vision.** Yes. The durable thesis is **orchestration as the engineering job**: encode quality and process in formulas/packs; keep judgment out of Go; let better models make the same factory better; scale from a single operator’s city to a **shared, governed, multi-operator factory** (Beads Team Server → Gasworks) without forking the OSS engine. The 1.6 OSS plan is the unglamorous prerequisite — sessions that converge, stores that stay fast, contributors who can land changes. The commercial plan is a **docker/docker.io split**: generic OSS client, private hosted control plane, default URL at gascity.com, self-host still first-class.

I would not describe Gas City as “just a Gas Town rewrite” or as “already a general-purpose BPM product.” It is a **coding-agent factory platform** whose authors believe the same primitives generalize, and whose company is building the team/hosted layer now, with OSS 1.6 still aimed at making the local factory trustworthy at scale.

## Sources

Primary, in-repo (commit `2dec01c71`): `README.md`, `AGENTS.md`, `ROADMAP.md`, `CHANGELOG.md` (v1.0.0, v1.5.0), `docs/index.mdx`, `docs/getting-started/how-gas-city-works.md`, `docs/getting-started/coming-from-gastown.md`, `docs/getting-started/faq.md`, `docs/guides/understanding-formulas.md`, `docs/guides/multi-agent-engineering-environment.md`, `docs/guides/registry-showcase.md`, `docs/reference/specs/service-protocol-v0.md`, `engdocs/architecture/{index,nine-concepts}.md`, `engdocs/contributors/primitive-test.md`, `engdocs/plans/hosted-onboarding/DESIGN.md`, `internal/cliauth/AGENTS.md`, `examples/hyperscale/city.toml`, `examples/gastown/{pack.toml,SDK-ROADMAP.md,FUTURE.md}`. GitHub issues #7093–#7095. `gh repo view` / `git log` / `git shortlog`.

Primary, web: [docs.gascity.com](https://docs.gascity.com/), [gascity.com](https://gascity.com/), [gascity.com/about](https://gascity.com/about/), [gascity.com/gasworks](https://gascity.com/gasworks/), [gascity.com/guide/ai-software-factory](https://gascity.com/guide/ai-software-factory/), [yegge.ai/gastown.html](https://yegge.ai/gastown.html), Chris Sells [Announcing Gas City 1.0!](https://sellsbrothers.com/announcing-gas-city-1-0), [Orchestration Is All You Need](https://sellsbrothers.com/orchestration-is-all-you-need), [gascityhall.com](https://gascityhall.com/), GitHub org [gastownhall](https://github.com/gastownhall).

Secondary (used with caution): KuCoin/Phemex 2026-04-24 flash on v1.0; Ry Walker’s Gastown research note; Product Hunt listing; GitHub wiki roadmap (May 2026, incomplete fetch).
