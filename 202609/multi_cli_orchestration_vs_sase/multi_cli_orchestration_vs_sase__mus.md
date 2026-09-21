# Seamless Multi-CLI Development on One Project: Landscape vs SASE

Researcher: mus · Date: 2026-09-21
Scope: find projects that do an equally good or (ideally) better job than SASE at
letting one developer build a **single project with multiple agent CLIs**
(Claude Code, Codex, Gemini, Grok Build, Muse, Qwen, OpenCode, …) in a seamless way,
then critique how good SASE actually is in this space.

Method: independent web research (repos, docs, ecosystem surveys) plus SASE's own
docs (`docs/agent_providers.md`, `README.md`) as the baseline. No access to the
sibling researcher's report was sought or used.

## 1. What SASE's value-add actually is (baseline)

SASE is a **coordination layer over vendor CLIs**, not a replacement agent. The
concrete mechanism, per its README and provider docs:

- Supports 7 CLIs: Claude Code, Codex CLI, Antigravity CLI (`agy`), Qwen Code,
  OpenCode, Muse Code (`muse`), Grok Build (`grok`). At least one must be
  installed and authenticated; `sase doctor` is the readiness authority.
- Each agent runs in an **isolated numbered workspace clone** (workspace-per-agent),
  supervised from one keyboard-driven **TUI** (Agents tab: status, retry chains,
  diffs, chats, artifacts).
- Work is tracked as **Patches** (PR-sized units with status/comments/review state),
  prompts are reusable (**XPrompts**), background/recurring work goes through a
  **scheduler** service proc, and durable state covers beads and artifacts.
- Routing: auto-detected providers, explicit `%model:<provider>/<model>` selection,
  and model-alias pools (`@small/@medium/@large/@xlarge`) that can span providers.
  Muse/Grok are never auto-detected from `PATH` (generic binary names) and need
  explicit selection.
- `sase tmux-agent` windows are explicitly **unmanaged** CLIs — they do not appear
  in `sase agent list`.

So "seamless multi-CLI" for SASE means: one prompt fans out to N different vendor
CLIs in isolated workspaces, with uniform supervision, tracked reviewable output
(patches/PRs), repeatable prompts, and scheduled runs. Any rival must be judged
against that full bundle, not just "launches two agents."

## 2. What "equally good or better" means here

I scored candidates on five dimensions:

1. **CLI breadth** — how many real vendor CLIs can work the same project
   (not just models behind one harness).
2. **Isolation** — per-agent filesystem/branch separation (worktrees/clones).
3. **Supervision UX** — one surface to launch, watch, kill, diff, and merge.
4. **Tracked, reviewable output** — task lifecycle, review state, audit trail.
5. **Repeatability/extras** — reusable prompts, scheduling, messaging between
   agents, verification loops.

A project can be "better" on the narrow question (seamless multi-CLI, one project)
while being worse overall (e.g. no scheduling), and vice versa. Section 4 keeps
that distinction explicit.

## 3. Landscape taxonomy

| Lane | Idea | Examples |
|---|---|---|
| A. Session/worktree managers | Wrap existing CLIs, isolate with tmux + git worktrees, one TUI | Claude Squad, agent-deck/dmux/muxcode |
| B. Kanban/desktop orchestrators | Board or desktop app; task → workspace → diff → PR | Vibe Kanban, Conductor, Nimbalyst (ex-Crystal), SigmaLink |
| C. Model gateways/routers | Keep one CLI UX, route its requests to any model | Claude Code Router (CCR) |
| D. Provider-agnostic harnesses | One harness, 10–75+ providers; replaces the CLIs | OpenCode, Aider |
| E. Autonomous multi-agent frameworks | Typed tasks, messaging, architect/tester verification | ORCH, OMK, Kodo, OpenCastle, Gas Town |

Only lanes A, B, and E compete with SASE head-on (they keep the vendor CLIs).
Lanes C and D answer the same user need differently ("why juggle CLIs at all?").

## 4. Candidates, assessed

### 4.1 Claude Squad (`smtg-ai/claude-squad`) — the closest direct rival

- Go TUI managing **multiple CLIs in parallel**: Claude Code, Codex, Gemini,
  Aider, OpenCode, Amp (configurable launch commands). Each task gets an isolated
  **git worktree** and runs in its own **tmux** session; built-in diff view,
  autoyes/yolo mode. ~6k stars, `brew install claude-squad`, run `cs`.
- Verdict: **roughly equal at launch-and-supervise, weaker at tracked output.**
  It matches SASE's core loop (fan out N CLIs, watch, diff) with a leaner install,
  but has no equivalent of Patches lifecycle, beads/artifacts, scheduler, or
  reusable XPrompts, and its hard tmux dependency is a known limitation. If the
  job is "run 5 agents now and eyeball diffs," it is equally good and simpler; if
  the job is "tracked, reviewable, repeatable engineering," SASE is ahead.

### 4.2 Vibe Kanban (`BloopAI/vibe-kanban`) — best breadth + board UX, dying parent

- Local web app (Rust backend + React, SQLite): kanban issues → per-task
  **workspace** (branch + terminal + dev server) → review diff → merge. Supports
  **10+ agents** (Claude Code, Codex, Gemini CLI, Copilot, Amp, Cursor, OpenCode,
  Droid, CCR, Qwen) — broader than SASE's 7. ~25–27k stars, Apache-2.0.
- Critical caveat: parent company **Bloop shut down 2026-04-10**; the project is
  community-maintained, cloud halves (issues/comments) uncertain. Open-source
  analyses from mid-2026 list it as "sunsetting, still self-hostable."
- Verdict: **better at visual task-board supervision and raw agent count; worse
  at durability story and terminal-native supervision.** A team that wants a
  shareable board UI should prefer it; a solo terminal developer trusting a
  maintained core should prefer SASE. Its trajectory is the risk.

### 4.3 Conductor (`conductor.build`) — best Mac UX, narrow and closed

- Native macOS app: parallel agents in isolated git worktrees, dashboard with
  progress, review-and-merge from one UI. Supports Claude Code + Codex.
- Verdict: **better UX on macOS, worse everywhere else.** Closed-source,
  macOS-only, two-CLI breadth. SASE wins on openness, POSIX breadth
  (Linux + macOS), and provider count. No contest outside the Mac, and no
  scheduler/patch-lifecycle depth even on it.

### 4.4 Nimbalyst (ex-Crystal, `stravu/crystal`) and SigmaLink

- Crystal (worktree orchestrator app) was **deprecated Feb 2026**, redirected to
  commercial successor Nimbalyst. SigmaLink is an Electron desktop running 5 CLIs
  (Claude/Codex/Gemini/Kimi/OpenCode) in isolated worktrees with PTY panes.
- Verdict: **cautionary tales, not recommendations.** Both confirm the worktree +
  dashboard shape is commoditised, and both show the failure modes SASE avoids by
  being CLI/TUI-first and open: deprecation toward a paid successor, or a tiny
  fork count. Evaluate Nimbalyst only if its commercial terms are acceptable.

### 4.5 Gas Town (Steve Yegge / Thinky) — scale-proven, but single-vendor

- Open-source orchestration for **20–30 Claude Code instances in parallel** on one
  codebase; role coordination ("Mayor/polecats"), persistent tracking with
  **beads**, Ralph-loop discipline. Landed ~40k lines / 100+ PRs in its author's
  hands — but at ~40 Claude Max accounts, i.e. thousands/month.
- Verdict: **better at proven single-vendor factory throughput; not multi-CLI at
  all.** It is the strongest evidence that the beads + worktree + orchestrator
  shape scales, and SASE's own beads/artifact model rhymes with it — but anyone
  citing Gas Town as a multi-CLI answer is miscategorising it. Claude-only shops
  should study it; multi-CLI shops cannot adopt it as-is.

### 4.6 ORCH (`oxgeneral/ORCH`) — the most SASE-like task model, unproven scale

- Open-source CLI orchestrator managing Claude Code, Codex, Cursor as a **typed
  task queue with a state machine** (todo → in_progress → review → done),
  auto-retry, **inter-agent messaging**, and a TUI dashboard (~100 stars).
- Verdict: **conceptually the nearest to SASE's Patches + messaging gap, but two
  orders of magnitude less adopted.** SASE's TUI has no first-class inter-agent
  messaging primitive; ORCH does. If that primitive matters, ORCH is worth a
  spike — but its durability, provider breadth (3 vs 7), and review/audit depth
  trail SASE. Watch, don't switch.

### 4.7 OMK / Kodo / OpenCastle — autonomy over supervision

- **OMK** (open-multi-agent-kit): provider-neutral control plane, runtime routing,
  scoped MCP, DAG workers, evidence-before-completion checks.
- **Kodo**: directs Claude/Codex/Gemini through architect + tester verification
  loops; SWE-bench-verified.
- **OpenCastle**: turns assistants into ~19 coordinated specialist agents.
- Verdict: **better at autonomous verification, worse at human-supervised
  seamlessness.** They optimise for hands-off correctness (separate tester,
  evidence gates); SASE optimises for a human supervising parallel vendors. A
  SASE user wanting Kodo-style verification must bolt it on (or run Kodo *under*
  SASE as one agent type) — there is no built-in architect/tester gate.

### 4.8 Claude Code Router (CCR, `musistudio/claude-code-router`) — the "skip multi-CLI" answer

- Local gateway: Claude Code / Codex / Grok / Kimi / OpenCode / Pi clients hit one
  stable endpoint; CCR routes to OpenAI, Gemini, DeepSeek, OpenRouter, Ollama, …
  by rule, with multi-key rotation and usage tracking. ~30k stars. The
  `ANTHROPIC_BASE_URL` trick that enables it is public and documented.
- Verdict: **better at model/cost flexibility inside one UX; worse at exploiting
  each CLI's native strengths.** CCR answers "I want any model" without juggling
  CLIs, subscriptions, or per-vendor auth — SASE's model-alias pools overlap this
  but still launch the real vendor CLIs. Cost-optimisers and subscription-poor
  developers may rationally prefer CCR + one CLI; developers who need each
  vendor's hooks, MCP servers, and subscription behaviour still need SASE's
  approach. Note the fidelity risk: routed models in a foreign harness lose
  vendor-specific behaviour.

### 4.9 OpenCode (Anomaly, ex-SST) and Aider — the "one harness" answer

- **OpenCode**: terminal-first harness, **75+ providers** via Models.dev
  (including local Ollama/LM Studio), MCP/plugins first-class, client/server so
  terminal/IDE/remote attach. ~160k stars — the most-starred coding agent,
  ahead of Claude Code. It *replaces* vendor CLIs by calling provider APIs.
- **Aider**: pair-programming CLI with architect/editor model split
  (`--architect --model sonnet --editor-model haiku`), repo map, git auto-commit,
  lint/test repair loop, `--watch-files` IDE bridge.
- Verdict: **better at single-UX multi-model simplicity; not multi-CLI at all.**
  For "one project, any model, one workflow," OpenCode is arguably the strongest
  answer in the entire landscape — but it surrenders exactly what SASE preserves:
  running the vendors' own CLIs with their subscriptions, hooks, and release
  cadence. SASE even lists OpenCode as *one of* its providers, which frames the
  relationship correctly: coexistence, not competition. Aider's architect/editor
  split is a genuinely good idea SASE could imitate in routing policy.

### 4.10 Also-ran / adjacent mentions (checked, not recommended as rivals)

- **claude-octopus**: runs 12 providers against the *same task* to surface
  disagreement — adversarial review, not parallel development. Useful as a review
  step, not a SASE replacement.
- **MultiClaude**: desktop parallel-Claude manager — Claude-only, same
  single-vendor caveat as Gas Town.
- **Happy / VibeTunnel / Mobile Gateway**: remote-control relays (phone/laptop →
  agents). Adjacent to SASE's remote-dispatch/tailnet work, not to multi-CLI
  orchestration itself.
- **tmux-native small tools** (agent-deck, dmux, muxcode): per-agent tmux
  windows with mixed providers — the same primitives as Claude Squad with less
  product around them.

## 5. Comparison matrix (narrow question: one project, many CLIs, seamless)

| Tool | Real CLI breadth | Isolation | Supervision UX | Tracked reviewable output | Repeatability / extras |
|---|---|---|---|---|---|
| SASE | 7 CLIs (incl. Muse/Grok/Qwen/Antigravity) | numbered workspace clones | keyboard TUI, diffs/chats/artifacts | Patches lifecycle, beads, artifacts | XPrompts, scheduler, alias pools |
| Claude Squad | 6+ (Claude/Codex/Gemini/Aider/OpenCode/Amp) | worktree + tmux | Go TUI, diff view | weak (sessions, no patch lifecycle) | autoyes; no scheduler/prompts |
| Vibe Kanban | 10+ (broadest) | worktree workspaces | kanban web UI (shareable) | board + diff + PR | dev servers; parent dead |
| Conductor | 2 (Claude/Codex) | worktrees | polished Mac app | review/merge | macOS-only, closed |
| Gas Town | 1 (Claude-only) | workspaces + beads | factory TUI/CLI | beads tracking (strong) | Ralph loops; $$$/scale-proven |
| ORCH | 3 | processes | TUI dashboard | typed queue + review state | inter-agent messaging (unique) |
| CCR | N/A (routes models, not CLIs) | N/A | one CLI UX | logs/usage | routing rules, key rotation |
| OpenCode | N/A (75+ providers, one harness) | repo | TUI/server | git-native | MCP/plugins, Zen models |

## 6. Critique: how good is SASE actually in this space?

**The honest headline: nobody beats SASE at the full bundle today, but several
beat it on slices — and the bundle itself is a defensible niche, not an obvious
end-state.**

Where SASE is genuinely ahead:

1. **Breadth with fidelity.** Seven real CLIs, including awkward ones
   (Muse's generic binary name, Grok's routing quirks, Antigravity, Qwen), each
   launched as itself with its own auth and subscription behaviour — not
   flattened through a gateway. Neither Claude Squad (6, overlapping set) nor
   Conductor (2) nor any single-vendor tool matches this while preserving
   vendor fidelity. Only Vibe Kanban claims broader support, with a dead parent.
2. **Tracked → reviewable → repeatable, not just parallel.** Patches lifecycle,
   beads, artifacts, XPrompts, and the scheduler compose into an engineering
   system (auditable, resumable, schedulable), where rivals mostly offer parallel
   sessions plus eyeballing. Gas Town is the only rival with comparable
   tracking discipline, and it is single-vendor.
3. **Terminal-native supervision done well.** The Agents tab (status, retry
   chains, per-agent diffs/chats/artifacts, kill controls) plus `sase doctor`
   auth checks is a tighter loop than a kanban board for a solo POSIX developer,
   and it avoids Electron upkeep entirely.
4. **Routing pragmatism.** Auto-detect + explicit `%model` + alias pools +
   usage-limit auto-disable (hard/soft disables with expiry) is unglamorous and
   genuinely useful multi-subscriptionFM management. CCR does cost-routing
   better; nobody else in lanes A/B does subscription-aware routing at all.

Where SASE is weak or exposed:

1. **The supervision UX is single-player-terminal-only.** No shareable board
   (Vibe Kanban), no polished desktop (Conductor/SigmaLink), no mobile relay
   story of its own. Teams, managers, and phone-checkers are underserved.
   `tmux-agent` windows being *unmanaged* (invisible to `agent list`) is a
   concrete seam in "seamless": the escape hatch breaks the supervision model.
2. **No inter-agent coordination primitive.** ORCH's typed messaging and Kodo's
   architect/tester gates have no SASE equivalent; parallel SASE agents share a
   project only through git and human supervision. For genuinely cooperative
   multi-agent work (not just parallel attempts), SASE is a launcher plus a
   review queue, not a team.
3. **Opinionated, POSIX-only, alpha.** Numbered workspace clones + git-based
   flow + Linux/macOS-only + evolving interfaces is a filter: Windows developers,
   non-git projects, and anyone wanting a stable API are excluded. OpenCode runs
   more places; closed tools hide the complexity SASE exposes.
4. **Strategic exposure on two flanks.** From below, OpenCode-style harnesses
   keep absorbing providers (75+ and local models) — every provider they cover
   well erodes the "need the real CLI" argument. From above, CCR-style routing
   commoditises model choice inside one CLI. SASE's moat is the union of vendor
   fidelity *and* engineering tracking; either flank can narrow it. The
   "OpenCode as a SASE provider" coexistence framing is correct but concedes
   that for many tasks one harness is enough.
5. **Scale and cost evidence lags Gas Town.** SASE can fan out, but the public
   proof of 20–30-agent factory throughput with cost accounting is Yegge's, not
   SASE's. Scheduler + usage-limit disables are the right primitives; published
   fleet-scale playbooks are missing.
6. **Adoption risk vs incumbents.** OpenCode (~160k stars), Vibe Kanban (~27k),
   CCR (~30k) dwarf any lane-A orchestrator community. SASE's durability answer
   (open source, maintained, Rust core) is good but must stay visibly true —
   Vibe Kanban's fate is the cautionary exhibit.

Bottom line for the lead: recommend SASE as the best **open, terminal-native,
multi-CLI engineering system** (breadth + tracking + repeatability), with
honest carve-outs — Vibe Kanban for board-centric teams willing to self-host a
sunsetting project, Claude Squad for minimal parallel sessions, CCR/OpenCode
when the real requirement is multi-*model* rather than multi-*CLI*, ORCH's
messaging and Kodo's verification loops as features to watch or imitate, and
Gas Town as single-vendor scale inspiration, not competition. The gap most worth
closing is #2 (inter-agent coordination) and the `tmux-agent` unmanaged seam in #1.

## Sources

- SASE README and `docs/agent_providers.md` (supported CLIs, routing, tmux-agent
  semantics), workspace checkout 2026-09-21.
- Claude Squad: <https://github.com/smtg-ai/claude-squad> (multi-CLI tmux +
  worktree TUI; ~6k stars per ecosystem notes).
- Vibe Kanban: <https://github.com/BloopAI/vibe-kanban> (10+ agents, kanban →
  workspace → diff → PR); Bloop shutdown 2026-04-10 widely reported in surveyed
  orchestrator roundups.
- Conductor: <https://www.conductor.build/> and docs (native Mac, Claude +
  Codex, worktree isolation).
- Gas Town coverage: Cloud Native Now ("Kubernetes for AI coding agents"),
  WebProNews launch piece; gastownhall/beads sync concepts; ~40-account cost
  reporting from practitioner videos.
- ORCH: <https://github.com/oxgeneral/ORCH> (typed task queue, state machine,
  messaging, TUI).
- OMK / Kodo / OpenCastle via awesome-cli-coding-agents harness survey
  (multiple mirrors; star counts ~100–130 range, i.e. two orders below leaders).
- Claude Code Router: <https://github.com/musistudio/claude-code-router>
  (~30k stars; local gateway, multi-provider routing, key rotation).
- OpenCode: <https://opencode.ai/docs> and repo (75+ providers via Models.dev,
  MIT, client/server); star-leadership claim per 2026 ecosystem notes.
- Aider: architect/editor split and `--watch-files` per project docs and skill
  mirrors.
- Landscape corroboration: `florianbruniaux/claude-code-ultimate-guide`
  (agentic-tools, software-factories), `shaahink/conductor`
  (observability-and-market 2026-08-22), `3esign/coddess` research tracks,
  `jlevy/tbd` orchestration-and-UIs survey.
