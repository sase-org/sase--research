# Pi (earendil-works/pi) vs. SASE: Comparison, Lessons, and What Would Win Over a Pi User

_Researcher: cld · 2026-10-11 · Sources: a local checkout of `earendil-works/pi` (opened via
`sase repo open gh:earendil-works/pi`, HEAD `96abe9a5a`, 2026-10-11), the sase repo at
`e926d4100b`, and the public web coverage listed at the end._

---

## 1. TL;DR

- **Pi and sase are different layers of the stack.** Pi is a minimal, hackable
  **single-agent harness**: it owns the model loop, tools, context, and session. Pi also
  ships an SDK, an RPC protocol, and a growing set of runtime libraries. Sase is a
  **coordination layer above harnesses**: it owns workspaces, launches, scheduling, review
  state, notifications, and completion. Pi is mainly a candidate *backend* for sase, and
  only secondarily a competitor.
- **Sase cannot drive pi today.** Its built-in providers are `claude`, `codex`, `agy`,
  `qwen`, `opencode`, `muse`, `grok`, and `fakey` (`src/sase/llm_provider/`, `docs/plugins.md`).
  I found no pi references in `src/`, `docs/`, `sdd/`, or memory. For someone who already
  lives in pi, the first question is "does it run my pi, with my extensions, models, and
  logins?", and the answer is currently no. This is the top-ranked gap by a wide margin.
- **Pi's own repository documents the pain sase solves.** Pi's `AGENTS.md` has a whole
  section of git rules because "multiple pi sessions may be running in this cwd at the
  same time … Git operations … will stomp on other sessions' work". Its community has
  built `pi-side-agents`, `pi-pr-agents`, `pi-agent-orchestrator`, `pi-worktree`, and
  hundreds of subagent packages to cover isolation and orchestration, which pi
  deliberately leaves out. Sase's workspace-per-agent model, tracked Patches, AXE
  scheduling, and notification gates are the "batteries" those packages try to supply.
- **Lessons for sase, in short:**
  1. Keep a small, legible core and teach "use the least powerful mechanism".
  2. Prefer *mechanical hooks* over prose contracts.
  3. Make extension cheap: drop-in files, git, npm or local sources, and a gallery.
  4. Make context, cost, and session lineage visible.
  5. Ship stable, strictly framed machine interfaces (print, JSON, RPC, SDK).
  6. Measure whether documentation and instructions actually help, using paired evals.
- **Pi is the most hookable harness sase could target.** Its extension lifecycle
  (`tool_call` can block, `agent_before_settle` can request one continuation, a
  `terminate: true` tool can end the run) lets sase *enforce* contracts it currently
  enforces only by instruction text for most providers. These include the single-turn
  final declaration, host-owned completion, guarded recipes, and helper-agent rules. Pi's
  session JSONL also persists the exact system-prompt sections, so
  `sase instructions verify` could prove instruction delivery for pi more precisely than
  for any current provider.

---

## 2. What pi is (evidence from the checkout)

### 2.1 Project facts

| Fact | Value | Evidence |
|---|---|---|
| Positioning | "a minimal, extensible agent harness that you can make your own" | `README.md` |
| Owner | Earendil (Armin Ronacher's company); Mario Zechner joined in April 2026 and brought pi with him | web sources; npm scope `@earendil-works` |
| Release | 1.0.0 on 2026-10-01; 1.1.0 on 2026-10-07 | `packages/coding-agent/CHANGELOG.md`, git tags |
| History | 6,843 commits since 2025-08-09. Top 2026 committers: Zechner 2,587, Ronacher 862 | `git log`, `git shortlog` |
| Language and runtime | TypeScript on Node ≥ 22.19. Installs via `curl \| sh`, npm, Nix flake, or standalone binaries. Runs on Windows, macOS, Linux, and Termux | `README.md`, `docs/quickstart.md` |
| Packages (14 directories) | `ai`, `agent`, `coding-agent`, `tui`, `durable`, `chord`, `server`, `protocol`, `client`, `env`, `mcp`, `codemode`, `telemetry`, `evals` | `packages/` |
| Docs size | about 7.1k lines of coding-agent docs (sase: about 58.5k lines in `docs/*.md`) | `wc -l` |
| Ecosystem | pi.dev package gallery; about 5.4k packages in one search snapshot. Packages install with `pi install npm:…` / `git:…` / `./path` | web; `docs/packages.md` |

### 2.2 Core product philosophy

- **A tiny default surface.** There are four default tools (`read`, `bash`, `edit`,
  `write`), plus optional `grep`, `find`, `ls`, and the extensions `codemode` and
  `tool_search` (`docs/cli.md#tools`). The base system prompt is a few sections built in
  `src/core/system-prompt.ts`. Reviewers put it under 1k tokens.
- **Intentional omissions.** "Pi ships with powerful defaults but skips features like
  sub-agents and plan mode. Ask Pi to build what you want, or install a package that
  does it your way" (`README.md`). Plan mode, subagents, handoff, permission gates,
  sandboxing, todo lists, and git checkpoints all exist only as *example extensions*
  (`examples/extensions/`).
- **"Choose the least powerful mechanism."** The quickstart has a decision table:
  `AGENTS.md` → prompt template → skill → extension → TUI component → custom provider →
  package (`docs/quickstart.md#choose-how-to-customize-pi`).
- **No built-in permission system.** The docs say plainly that safety comes from
  isolation such as a container, VM, or Gondolin micro-VM, not from approvals
  (`docs/security.md`, `docs/containerization.md`). Project trust only gates *loading*
  of project resources (`.pi/settings.json`, extensions, skills, `.pi/mcp.json`).
- **Observability over hidden behavior.** Zechner's stated reason for building pi was
  frustration with hidden prompt changes, injected reminders, and opaque context
  management in commercial agents (web sources). Pi's startup header lists every loaded
  instruction and resource. The footer shows context usage and cost, and `/session`
  shows cost per *physical* model.

### 2.3 Feature inventory relevant to sase

| Area | Pi capability | Where |
|---|---|---|
| Extensions | TypeScript modules loaded by `jiti`, so there is no build step. Users drop a file in `~/.pi/agent/extensions/` or `.pi/extensions/`. They can register tools, commands, shortcuts, flags, providers, MCP servers, virtual models, and renderers, and subscribe to more than 20 lifecycle events | `docs/extensions.md` |
| Lifecycle hooks | `tool_call` (mutate or **block**), `tool_result` (compose), `before_agent_start` (edit prompt sections), `context` (transform messages), `turn_end` / `agent_before_settle` (append entries and **request one continuation**), `agent_settled` (final), `user_bash`, `project_trust`, `cache_warming_decision` | `docs/extensions.md` |
| Packages | Bundle extensions, skills, prompts, and themes. Sources can be npm (pinned), git (pinned ref), or a local path. Per-package resource filters use `!`, `+`, and `-`. Scopes are personal or project, and the gallery indexes the `pi-package` keyword | `docs/packages.md` |
| Skills | Implements the Agent Skills spec. Discovers `~/.agents/skills/` and `.agents/skills/` up to the repo root. Progressive disclosure: only name and description are in the prompt. `/skill:name` forces a skill | `docs/skills.md` |
| Prompt templates | Markdown files become `/name` commands with bash-like `$1`, `${@:N}`, and `${1:-default}` arguments | `docs/prompt-templates.md` |
| Sessions | JSONL **tree** with `id` and `parentId`. `/tree` navigates in place, `/fork` makes a new session from an earlier message, and `/clone` copies the active branch. Branch summaries are written when leaving a branch. `--session-id`, `--fork`, `--continue`, and `--resume` are available | `docs/sessions.md`, `docs/session-format.md` |
| Compaction | Automatic or manual (`/compact [focus]`), with iterative structured summaries. Original entries stay in the tree. Extension hooks are available | `docs/compaction.md` |
| Steering | `Enter` during a run is a *steer* applied after the current turn. `Alt+Enter` is a *follow-up* after the run. `Esc` aborts and returns queued messages | `docs/usage.md` |
| Integration surfaces | `--print`; `--mode json` (strict JSONL events ending in `agent_settled{aborted}`); `--mode rpc` (correlated commands plus the extension-UI protocol); an in-process TypeScript SDK | `docs/json.md`, `docs/rpc.md`, `docs/sdk.md` |
| Models | Unified multi-provider API covering subscriptions, API keys, and local models via llama.cpp. **Virtual models**: an extension-defined router picks the physical model for each request, with router state stored per branch | `docs/models.md`, `docs/virtual-models.md` |
| Codemode | The model writes QuickJS scripts that call tools in parallel; only the script's output enters context. Includes a BM25 `searchTools()` and deferred MCP tools | `docs/codemode.md` |
| MCP | Native since 0.99/1.0, with OAuth hardening and per-server exposure (`direct`, `codemode`, `deferred`, `hidden`) | `docs/mcp.md` |
| Program status | Emits OSC 7501 (`working`, `blocked`, `done`, `error`, `idle`) so terminals and agent dashboards can show its state | `docs/terminal-setup.md#program-status` |
| Sharing | `/export` to HTML or JSONL, `/share` to a gist or Radius, `/bug` bundles. The author also publishes OSS sessions to Hugging Face | `docs/sessions.md`, `README.md` |
| Durable runtime | `pi-durable` (experimental): commit-before-show transcripts, crash-resumable tasks, a task-ownership tree, and subagents as owned conversations, with `failFast` / `allSettled` waits and bottom-up abort | `packages/durable/README.md` |
| Multi-frontend | `chord` (facets, services, replicated state) plus `pi-server`, `pi-protocol` (CBOR), and `pi-client`: one durable session with several attached presentations (TUI, web) | `packages/{chord,server,protocol,client}` |
| Remote execution | `pi-env`: a small Rust daemon deployed over SSH. Tools run remotely while credentials stay local | `packages/env/README.md` |
| Evals | Paired *documentation-lift* evals: each case runs in isolated `without_docs` and `with_docs` containers. Blocked pairs withhold headline numbers | `packages/evals/README.md` |
| Supply chain | Exact-pinned direct dependencies, `min-release-age=2`, `--ignore-scripts` everywhere, an install-lock for the managed installer, and a lifecycle-script allowlist | `README.md#supply-chain-hardening` |

---

## 3. What sase is, in the terms a pi user would use

Sase is a Python CLI and Textual TUI that turns existing agent CLIs into a coordinated
team (`README.md`). For each launch, sase:

- clones a numbered workspace (`sase_<N>`), so parallel agents never share a checkout;
- expands **Macros** (`#name`, `%directives`, `+project` tags);
- routes to a provider and model through size aliases, priority, load balancing, and
  usage-limit auto-disable;
- runs the agent as a **single provider turn** (decision `single-turn-agents`), with
  continuation always mechanical: monitors, gates, handoffs, follow-ups;
- has the agent submit a **final declaration**, after which host-owned finalizers commit
  and open PRs (decision `host-owned-completion`);
- tracks the result as Patches, beads/SDD epics, Goals, ToolRuns, and artifacts;
- surfaces everything in the TUI (Agents, Patches, notifications), plus Telegram, a mobile
  gateway, and remote dispatch.

The extension story is a Python plugin system with 13 entry-point groups over
pluggy/entry points (`docs/plugins.md`). It has six first-party plugin packages and
supports `sase plugin install <name|git+url|path>`.

---

## 4. Head-to-head

| Dimension | Pi | Sase | Who's ahead / note |
|---|---|---|---|
| Layer | Harness (owns the model loop) | Orchestrator (drives harnesses) | Complementary |
| Model access | Owns provider APIs; any model, subscription, or local model | Delegates to each CLI's model set; 7 CLIs | Pi has broader reach. Sase could inherit it *through* pi |
| Parallelism and isolation | None built in; community packages; documented same-cwd git hazards | Workspace-per-agent clones, clans, tribes | **Sase** |
| Work tracking | Sessions only | Patches, beads, epics, Goals, ToolRuns, artifacts | **Sase** |
| Scheduling and background work | None (Durable is a library) | AXE scheduler, monitors, service procs | **Sase** |
| Human-in-the-loop | `ctx.ui.confirm` / `select` in TUI or RPC | Notification gates, plan and question gates, Telegram, mobile | **Sase**, for asynchronous work |
| Extensibility cost | Drop a `.ts` file; `pi install npm:/git:/path`; thousands of packages | Python package with entry points; config macros; 6 plugins | **Pi**, by a lot |
| Hook depth | More than 20 lifecycle events, including block, continue, and transform-context | Hooks on sase's own lifecycle; agent-internal control depends on each provider (e.g. Claude PreToolUse) | **Pi** |
| Session lineage | Native tree; fork, clone, branch summaries | `#fork` / `#resume` inject a `# Previous Conversation` text block (`docs/macros.md`) | **Pi** keeps cache and tool fidelity |
| Mid-run steering | Steer and follow-up queues | No; single-turn, and you kill and `#fork` | **Pi** |
| Transparency | Startup resource header; context and cost footer; per-physical-model cost | `sase instructions verify`, instruction bundles, ToolRun evidence, usage windows | Different strengths: pi is live and cheap, sase is audit-grade |
| Instruction footprint | Base prompt under 1k tokens; context files opt-in | About 22.5 KB of always-loaded `AGENTS.md`/`CLAUDE.md` in this project (18.4 KB project + 4.1 KB home) before provider prompts | **Pi** is cheaper per turn |
| Machine interfaces | print, JSON, RPC, SDK, CBOR protocol | `--json` on many commands, mobile gateway API, Rust core bindings | Pi's are more uniform and better documented |
| Docs and onboarding | 7k lines; "least powerful mechanism" chooser | 58k lines; about 70 glossary terms; alpha | **Pi** is easier to start with |
| Platforms | Linux, macOS, Windows, Termux, Nix | POSIX only | **Pi** |
| Evaluation | Paired doc-lift evals in containers | Strong CI, ToolRun receipts; no doc or instruction lift evals found | **Pi**, for measuring prompts and docs |

---

## 5. What sase can learn from pi

### 5.1 Enforce contracts with hooks, not paragraphs

Pi's extension lifecycle is a contract-enforcement API. `tool_call` handlers can block,
and a handler *failure* blocks as a fail-safe. `agent_before_settle` can append entries
and return `continue: true` once. A tool returning `terminate: true` ends the run on that
call (`examples/extensions/structured-output.ts`).

Sase's own docs admit that enforcement varies by provider. Helper coverage is "sentence
only" for Grok and absent for Muse and agy (`docs/agent_providers.md#root-and-helper-agents`).
The final declaration, "never commit", and "never run raw `just`" rules mostly ride on
instruction text.

**Lesson:** for every harness that offers hooks, express sase's invariants as hooks and
treat prose as the fallback. Pi offers the richest hook set of any harness sase could
target.

### 5.2 Make extension nearly free

A pi user's mental model is: write `hello.ts`, drop it in a directory, `/reload`, done.
To share it, `pi install git:github.com/me/thing@v1`. Sase's equivalent is a Python
distribution with entry points installed into the uv tool environment. That is fine for
first-party plugins and heavy for a 20-line hook.

Sase's config macros are already lightweight. The gap is *executable* behavior
(event handlers, custom gates, custom TUI widgets) without packaging. Pi's per-package
resource filters (`!pattern`, `+path`, `-path`) and personal-vs-project scoping are also
worth copying.

### 5.3 Teach the smallest mechanism first, and keep the always-on core small

Pi's quickstart chooser table, and its refusal to build plan mode or subagents into the
core, keep the cognitive surface small.

Sase's surface is broad: Macros, directives, project tags, clans, tribes, hoods, gates,
monitors, Patches, beads, Goals, memory webs, ToolRuns, receipts, and more, across 58k
lines of docs. Every feature is defensible on its own, but a pi user evaluating sase sees
a wall.

Sase also pays roughly 5–6k tokens of always-loaded instructions in this project before
the provider's own prompt. A pi user chose pi partly to avoid exactly this.

### 5.4 Native session lineage beats transcript re-injection

Pi's tree lets a fork or resume keep exact tool results, thinking signatures, and the
prompt cache. Branch summaries preserve the useful parts of abandoned paths. Sase's
`#fork` injects prior conversation as text, which is the only portable option across all
CLIs. Where a provider has native fork and resume, as pi does with `--fork <session>
--session-id <new>`, sase should prefer it.

### 5.5 Live visibility: context, cost, and state

Pi shows context usage, accumulated cost, the routed physical model
(`auto • high → gpt-5.6-luna • medium`), and emits OSC 7501 program status.

Sase is excellent at *post-hoc* evidence: receipts, ToolRuns, and instruction
verification. It is thinner on dollar cost. I found per-provider `total_cost_usd` only
for some providers, and no cross-provider dollar roll-up surfaced in `docs/ace.md`. Pi
already prices every assistant message, including tiered pricing.

### 5.6 Uniform, strictly framed machine interfaces

Pi documents one event vocabulary across JSON and RPC modes. Framing is exact (LF-only
splitting; a warning not to use Node `readline` because of U+2028). Lifecycle semantics
are explicit: `agent_end` vs `agent_settled`, and `disposition: handled` means don't wait.

This is what makes pi easy to embed, and it is how OpenClaw, pi-chat, and IDEs build on
it. A comparable "sase agent event stream" would let pi extensions, editors, and
dashboards drive and observe sase.

### 5.7 Measure prompt and doc value with paired evals

Pi's `packages/evals` runs each case with and without docs in fresh containers and
withholds headline lift when any pair is blocked. Sase invests heavily in memory, skills,
and instruction bundles, but has no lift measurement for them. This fits sase's own
`corpus-before-mechanism` and `receipts-prove-before-they-skip` instincts: prove value
before adding more always-on text.

### 5.8 Smaller but real lessons

- **Virtual-model routing semantics.** Pi separates *selection* from *dispatch*, keeps
  routing sticky on continuations and retries to preserve caches, and stores router
  state per branch. Sase routes per launch, but the vocabulary is worth reusing. Sase's
  size aliases could also *target* pi virtual models.
- **Ownership semantics in `pi-durable`.** Owned conversations and tasks, `failFast` vs
  `allSettled` waits, bottom-up abort, and "background" boundaries that survive a
  parent's abort. These map closely onto sase clans, tribes, `%wait`, and monitors, and
  are a clean model to check sase's semantics against.
- **Supply-chain posture.** Pinned direct deps, minimum release age, `--ignore-scripts`,
  and an install lock. This is relevant because sase installs agent CLIs for users via
  `sase agent-cli install`.
- **Platform reach.** Windows and Termux support widen pi's audience. Sase's POSIX-only
  stance is reasonable for now, but it is a hard stop for some pi users.

### 5.9 What sase should *not* copy

Pi's "no permissions, no orchestration, no tracking" minimalism makes sense for a
harness. Sase's value *is* the layer pi leaves out. The lesson is to make that layer
**adoptable incrementally** and **mechanically enforced**, not to strip it out. Pi's
community demand for side-agents, worktrees, PR agents, and orchestrators shows the need
is real.

---

## 6. Why a current pi user would bounce off sase today (friction audit)

1. **No pi provider.** Their extensions, logins, models, and virtual routers are
   unusable through sase.
2. **Python plugin story vs. TypeScript extensions.** Their existing customization
   investment doesn't carry over.
3. **Concept and instruction load.** About 70 glossary terms, and multi-KB instruction
   files loaded every turn. This conflicts with the "no hidden prompt changes" ethos
   that drew them to pi. Sase's transparency tools (`sase instructions verify`) exist
   but are audit-oriented, not front-and-center.
4. **No steering.** Pi users steer mid-run all the time. In sase the answer is to kill
   the agent and `#fork` it.
5. **Lossy forks.** Text re-injection instead of native branching.
6. **No live cost and context view** comparable to pi's footer.
7. **POSIX-only and alpha.**

---

## 7. Ranked improvements to make sase appealing to a pi user

Ranking criteria, in order: (a) how much it unblocks or delights an existing pi user;
(b) leverage, meaning it also improves sase for everyone; (c) effort and risk. Effort is
a rough S/M/L.

### 1. First-class `pi` provider (`sase_llm` plugin), effort M, impact critical

**What:** add `pi` alongside the other built-in providers, following the existing
adapter split (`<provider>.py` + `_subprocess_<provider>.py` + `_tool_call_<provider>.py`).
Peer adapters are about 500 lines (OpenCode) to about 1,300 lines (Muse). Decision
`adapters-normalize-harnesses` already says this is how harnesses join.

**How:**
- Launch `pi --mode json --session-id <uuid> --approve --model <pattern>[:<thinking>]
  --append-system-prompt <sase directive file> "<prompt>"`.
- Parse the JSONL stream: `message_update` text deltas go to the live reply,
  `tool_execution_*` events become tool calls, `message_end` carries usage and **cost**,
  and `agent_settled{aborted}` marks completion.
- Pass any pi model pattern through as `%model:pi/<provider>/<id>`, **including
  extension-registered virtual models**, and map sase effort onto pi thinking levels.
- Deploy sase skills to pi's skill location (`~/.pi/agent/skills`, or the cross-tool
  `~/.agents/skills`) via `llm_skill_deploy_subpath`.
- Pi natively loads the workspace `AGENTS.md`/`CLAUDE.md`. Decide on exactly-once
  delivery, the same way the Grok adapter avoids sending `CLAUDE.md` twice.
- Add a pi row to **tmux Agent** for interactive, unmanaged pi windows.
- Extend `sase instructions verify` to read pi session JSONL. Pi persists the exact
  system-prompt **sections** in the first system message (`docs/session-format.md`), so
  verification can be exact rather than heuristic.

**Why first:** without it, nothing else on this list reaches a pi user. It also gives sase
indirect access to every model pi supports (local llama.cpp, OpenRouter, Bedrock, and
others), and that reach helps sase's routing story for all users.

**Risks:** pi changes quickly. CHANGELOG breaking changes appear every few releases,
for example the 1.0.3 provider rename. Pin a minimum pi version in `sase doctor` and
cover the adapter with a `fakey`-style recorded-stream fixture.

### 2. A `sase` pi package that enforces sase's contracts mechanically, effort M, impact very high

**What:** publish `sase-pi` (npm and git) as a pi package. The sase pi provider loads it
explicitly with `-e`, and users can also `pi install` it for interactive use. It
contains:
- **A `sase_final` tool** with a TypeBox schema matching the declaration, returning
  `terminate: true`. The final declaration becomes a typed tool call instead of a bash
  incantation.
- **An `agent_before_settle` guard:** if no declaration was submitted, append a reminder
  entry and `continue: true` once. This turns decision `single-turn-agents` from an
  instruction into a mechanism.
- **A `tool_call` guard** that blocks `git commit`, `gh pr create`, and raw guarded
  `just` recipes, with a reason that points to the sanctioned path (decisions
  `host-owned-completion`, `guarded-recipes`). This closes the "sentence-only"
  enforcement gap for pi, and pi's handler-failure-blocks semantics are fail-safe.
- **Helper safety:** if a pi subagent package is loaded, block `sase_final` in child
  sessions (decision `helpers-return-roots-declare`).
- **Interactive commands for pi users who never open the sase TUI:** `/sase run …` to
  launch an isolated sase agent from the current pi session, `/sase agents` for a status
  widget, and `/sase inbox` for pending gates.

**Why:** it meets pi users inside the tool they already live in, which is how pi's
ecosystem grows. It also makes pi the *best-enforced* sase provider. Lessons learned can
flow back to the Claude PreToolUse guard and future harness hooks.

### 3. Native fork and resume for providers that support it, starting with pi, effort S–M (after #1)

**What:** when the source and target agents share a provider with native lineage,
implement `#fork:<agent>` / `#resume` as a native fork (`pi --fork <session>
--session-id <new>`) instead of injecting `# Previous Conversation` text. Keep the text
path as the portable fallback. Optionally adopt pi's *branch summary* idea when forking
from a long transcript.

**Why:** a pi user's mental model is a session **tree**. Native forks keep tool-result
fidelity and the prompt cache, so they are cheaper and more faithful.

### 4. "Sase Lite" progressive-disclosure profile plus an instruction-budget readout, effort M

**What:**
- A documented, supported profile, for example `sase init --profile lite`, whose
  promise is "parallel isolated agents + TUI + review". SDD, beads, Goals, memory webs,
  and autonomy stay dormant until opted into.
- The always-loaded instruction set shrinks to the minimal contract (final declaration,
  workspace rule), with everything else on demand.
- A pi-style "choose the least powerful mechanism" table at the top of Getting Started:
  prompt, Macro, skill, config macro, plugin.
- A **token-cost readout** for injected instructions in `sase instructions`, shown in the
  TUI per launch. Show the cost the way pi shows context usage, rather than burying it.

**Why:** pi users self-select for minimal prompts and visible context. Sase's existing
transparency machinery (bundles, manifests, verify) is a genuine strength once it is
put front-and-center.

### 5. Live cost and context visibility across providers, effort S–M

**What:** in the Agents tab and `sase agent show`, show each agent's dollar cost,
context-window usage, and the *physical* model that answered. Roll these up per Goal,
epic, clan, and day. The pi adapter can forward pi's already-priced usage, including
tiered pricing, and other providers can contribute what they expose
(`total_cost_usd` and similar).

**Why:** pi's footer and `/session` per-model cost are table stakes for its users. Sase
running many agents in parallel makes aggregate cost *more* important, not less.

### 6. Mid-run steering and follow-ups for providers with a steering channel, effort M, needs a decision record

**What:** `sase agent steer <name> "<msg>"` and a TUI key that queue a steering message
into a *running* turn. Pi supports this via RPC-mode `steer` / `follow_up`, and some
other CLIs have streaming-input modes.

This plausibly stays inside decision `single-turn-agents`, because the run is still one
provider turn. But it changes the "continuation is mechanical" picture enough to deserve
an explicit decision record. It probably requires running pi in `--mode rpc` rather than
`--mode json`.

**Why:** steering is a core pi habit. "Kill and fork" feels like a regression.

### 7. Agent Skills interop in both directions, effort S

**What:**
- Deploy sase-generated skills to the cross-tool `~/.agents/skills` location as an
  option.
- Let sase discover third-party `SKILL.md` directories, from pi packages or
  `.agents/skills`, as sase skills, with progressive disclosure (name and description
  only until needed).

**Why:** a pi user's skills collection should come with them. The Agent Skills spec is
the shared currency.

### 8. Drop-in local extensions and package filters, effort M

**What:** let a plain Python file in `~/.config/sase/extensions/` or a project
`.sase/extensions/` register lightweight hooks (launch, complete, gate created, agent
failed) without packaging. Gate project-local executable extensions behind an explicit
trust decision, modeled on pi's project trust. Add pi-style per-plugin resource filters
(`!`, `+`, `-`) and personal-vs-project scoping to plugin configuration.

**Why:** this closes the extension-cost gap in §5.2 for the "20-line hook" case that
pi users take for granted.

### 9. A stable, documented sase agent event stream (JSONL) and command protocol, effort M–L

**What:** `sase agent watch --json` (or a socket) with a pi-quality spec: strict LF
framing, a documented event vocabulary (launched, routed, tool-call, gate-opened,
declared, finalized, settled), and explicit "settled" semantics. It should be paired
with launch and inspect commands that have stable JSON responses. Per the Rust-core
boundary memory, the event schema belongs in `sase_core`, because every frontend needs
it to match.

**Why:** this lets the `sase-pi` package (#2), editors, the mobile gateway, and
third-party dashboards observe and drive sase without screen-scraping. It mirrors what
pi's JSON and RPC modes did for pi's ecosystem.

### 10. OSC 7501 program status, effort S

**What:**
- Have sase's TUI emit an aggregate status: `working` when agents run, `blocked` when a
  gate awaits the user, `done` or `error`.
- Optionally have `sase run` foreground invocations emit it too.
- In tmux-agent pi windows, which tmux won't forward, consume pi's status through the
  pi package (#2) instead.

**Why:** cheap, and it makes sase a good citizen in Ghostty and agent-dashboard
terminals that pi users already run.

### 11. Paired instruction and memory lift evals, effort M–L

**What:** adopt pi's `packages/evals` methodology for sase instructions. Run the same
tasks with and without a memory note, skill, or instruction section in fresh
workspaces, pair the arms, and withhold headline lift when any pair is blocked. Use the
`fakey` harness for plumbing tests and real providers for lift.

**Why:** it gives evidence for which always-on text earns its tokens, directly feeding
#4. It also answers the pi user's skepticism toward injected instructions with data.

### 12. Platform and installation reach, effort L, lowest priority

**What:**
- A Nix flake and a one-line installer.
- A documented WSL path for Windows users.
- Optionally, pi-style supply-chain notes for `sase agent-cli install`: pinned
  versions, `--ignore-scripts` where supported.

**Why:** these remove hard stops for some pi users. They matter less than #1–#11,
because most pi power users are on macOS or Linux already.

---

## 8. Suggested sequencing

1. **#1 pi provider.** Without this, nothing else matters to a pi user.
2. **#2 `sase-pi` package**, its contract guards first, with interactive commands later.
   Then **#3 native fork**, which is cheap once #1 exists.
3. **#5 cost visibility** and **#10 OSC 7501**, both quick wins.
4. **#4 Lite profile and instruction budget**, then **#11 lift evals** to choose what
   stays in the always-on core.
5. **#7 Skills interop**, then **#8 drop-in extensions**.
6. **#6 steering**, after a decision record, and **#9 the event stream**, through
   sase-core.

A useful framing for the launch post or README: **"Already using pi? Keep it. Sase runs
your pi with your extensions and models in isolated workspaces, enforces its contracts
with pi's own hooks, and gives you the parallelism, scheduling, review pipeline, and
inbox that pi deliberately leaves out."**

---

## 9. Caveats

- Pi facts come from a checkout at HEAD `96abe9a5a` (2026-10-11). Pi changes fast, with
  about 450–900 commits per month recently and breaking changes in point releases.
- Gallery counts (about 5.4k packages) and download figures come from search-result
  snapshots, and the "hundreds of thousands of weekly users" claim is the vendor's. Treat
  both as indicative.
- Sase claims were checked against `README.md`, `docs/agent_providers.md`,
  `docs/plugins.md`, `docs/macros.md`, `docs/ace.md`, and `src/sase/llm_provider/`. I
  did not exhaustively verify the absence of cross-provider dollar-cost roll-ups or a
  project-trust gate for project-local sase configuration. Confirm both before scoping
  #5 and #8.
- Token figures for sase's always-loaded instructions are byte-based estimates
  (about 4 bytes per token) for this project only.

## 10. Sources

Local (primary):
- `earendil-works/pi` checkout: `README.md`, `AGENTS.md`,
  `packages/coding-agent/{CHANGELOG.md,docs/*.md,examples/extensions/*,src/core/system-prompt.ts}`,
  `packages/{durable,chord,server,protocol,client,env,evals,telemetry}/README.md`.
- sase checkout: `README.md`, `docs/{agent_providers,plugins,macros,ace,agent_sessions}.md`,
  `src/sase/llm_provider/*`, and the decision index in the project `CLAUDE.md`.

Web:
- [Pi (pi.dev) overview: agentic-ai docs](https://agentic-ai.readthedocs.io/en/latest/AgentHarness/pi-dev/)
- [Building pi in a World of Slop: Mario Zechner (AI Engineer talk)](https://www.ai.engineer/talks/RjfbvDXpFls-pi-coding-agent)
- [ZenML LLMOps database: Building pi, a minimal extensible coding agent framework](https://www.zenml.io/llmops-database/building-pi-a-minimal-extensible-coding-agent-framework)
- [Pi Coding Agent Review (glukhov.org)](https://glukhov.org/ai-devtools/pi/pi-coding-agent-review/)
- [Pi coding agent review (DEV Community)](https://dev.to/andrew-ooo/pi-coding-agent-review-the-minimal-terminal-harness-5b46)
- [Pi 1.0 coverage: Trending Topics](https://www.trendingtopics.eu/pi-1-0-earendil/)
- [Pi 1.0 brings native MCP & Pi Durable (AlternativeTo)](https://alternativeto.net/news/2026/10/pi-1-0-brings-native-mcp-support-and-pi-durable-for-long-running-crash-resistant-ai-agents/)
- [Pi 1.0 Adds MCP Support and Pi Durable (Let's Data Science)](https://letsdatascience.com/news/pi-10-adds-mcp-and-durable-harness-6241c6f7)
- [Pi 1.0 Release Guide (Developers Digest)](https://www.developersdigest.tech/blog/pi-1-0-release-guide-mcp-codemode-pi-durable)
- [pi.dev Package Catalog: "sub" filter](https://pi.dev/packages?name=sub)
- [pi.dev Package Catalog: "tmux" filter](https://pi.dev/packages?name=tmux)
- [pi-side-agents](https://pi.dev/packages/pi-side-agents?name=tmux)
- [pi-pr-agents](https://pi.dev/packages/pi-pr-agents)
- [@onlinechefgroep/pi-agent-orchestrator](https://pi.dev/packages/@onlinechefgroep/pi-agent-orchestrator?page=29)
- [herdr agent docs](https://herdr.dev/docs/0.7.5/agents/)
- [OSC 7501 program-status protocol coverage (zeli.app)](https://zeli.app/story/49984159)
