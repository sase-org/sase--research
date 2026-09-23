# SASE vs. Nous Research's Hermes Agent: A Functional Comparison (September 2026)

**Researcher:** cld (one of three independent researchers in a swarm)
**Date:** 2026-09-23
**Question:** People keep describing Hermes Agent as "a lot like OpenClaw" and maybe "a lot like sase". How do Hermes and sase
actually compare and contrast? How well does sase compete with Hermes *functionally*? Popularity and adoption are
deliberately left out of the rating.

---

## Bottom Line

- **Hermes and sase are different kinds of product, and they meet in a narrow but important zone.**
  - Hermes is a **self-improving personal agent harness**. It owns its own LLM tool-calling loop, memory, skills, sandboxes and
    a 28-platform chat gateway. It has grown outward into multi-agent work through Kanban, `delegate_task`, `/goal` and
    Bot Mode.
  - sase is a **control plane for supervised software engineering across *other* agents' CLIs**. It drives Claude Code, Codex,
    Antigravity, Qwen Code, OpenCode, Muse and Grok Build, one run per numbered workspace clone. On top of that it adds
    durable task tracking, host-owned commits, human gates, scheduling, and audit trails.
  - Hermes is "like OpenClaw" at the category level: both are personal agents that live in your chat apps. Hermes is only
    "like sase" inside the overlap zone.
- **Inside the overlap, sase is the stronger system for supervised multi-agent coding.** The overlap is "run many agents on
  real repo work, track it durably, schedule it, and supervise it from your phone". There are three structural reasons:
  1. sase natively orchestrates heterogeneous vendor CLIs. Hermes's own docs say external-CLI Kanban lanes are "*not yet a
     paved path*".
  2. sase's host-owned completion (commit finalizers, Patches, mentors, land agents) has no Hermes counterpart. In Hermes
     the worker LLM runs `git`/`gh` itself.
  3. sase has a deeper work model (plan → epic → sized phases → land agent) and much richer provenance and audit.
- **Hermes is ahead in a few places even inside the overlap:**
  - a native review column with auto-spawned reviewers
  - PR "completion contracts" that check required GitHub checks
  - `/goal` judge loops with shell quality gates
  - checkpoint and rollback
  - LSP diagnostics after each edit
  - real sandbox backends
- **Outside the overlap, sase does not compete, and does not try to.** Hermes offers all of the following; sase has
  essentially none of them:
  - voice, browser and computer use
  - a closed learning loop
  - cross-session recall and user modeling
  - 28 messaging platforms
  - desktop, web dashboard and API server
  - MCP and ACP
  - cron with delivery anywhere
  - Windows support
- **Rating: 5 / 10 overall.** sase matches or beats Hermes on roughly half of Hermes's functional surface, weighted by
  importance. The split is sharp: **about 8.5 / 10 for supervised multi-agent software engineering**, **about 1.5 / 10 as a
  general personal assistant**. The scorecard is in §8.

---

## 0. Method, Sources, and What Changed Since April

**Hermes.**
- I read a local checkout of `NousResearch/hermes-agent`, opened through `sase repo open gh:NousResearch/hermes-agent`, at
  HEAD `358d50ca6d` (2026-09-23). The latest tag is `v2026.9.21`, and `pyproject.toml` says `version = "0.21.4"`.
- I read the root `AGENTS.md`, `README.md` and `SECURITY.md`, the Docusaurus docs under `website/docs/` (≈440 pages), and
  selected code. Examples of the code: `hermes_cli/kanban_db*.py`, `agent/background_review.py`, `tools/approval*.py`.
- I did **not** run Hermes. Claims about its behavior come from its docs and code.
- Where docs and code disagree, I say so. Hermes moves fast (~20.8k commits since 2026-08-01), so exact counts drift.

**sase.**
- This workspace is on `master` at `e1c4208cd`. The latest release is 0.17.1 (2026-08-29), and there have been about 1.2k
  commits since that release.
- Sources: `README.md`, `docs/*.md`, `src/sase/default_config.yml`, `pyproject.toml`, and the xprompt and skill sources.

**Web context.**
- The Hermes docs site and third-party comparisons, used only for release timing and OpenClaw context (see Sources).

**Prior research.**
- `research:202604/sase_vs_hermes_agent.md` (April 2026) compared an earlier Hermes snapshot, pinned at `456955c2` on
  2026-04-29. Much of it is now out of date:
  - Hermes has since shipped or matured Kanban (its doc was added 2026-04-26, which that report missed), `/goal`
    (2026-04-30), the skill Curator (2026-04-29), Hermes Desktop (June), A2A (August) and Bot Mode (Desktop v0.20.3,
    2026-08-16).
  - sase has since removed the Prometheus/Grafana stack (telemetry is now local SQLite). It retired keyword-driven
    "dynamic memory" in favor of core/reference notes plus memory webs. It replaced Gemini CLI with Antigravity (`agy`),
    and added remote dispatch, the mobile gateway, and typed sudo gates.
- This report stands on its own and does not reuse the April conclusions without re-checking them.

---

## 1. What Hermes Is (September 2026)

**Hermes describes itself as a harness**: "a personal AI agent that runs the same agent core across a CLI, a messaging
gateway (Telegram, Discord, Slack, ~20 platforms), a TUI, and an Electron desktop app. It learns across sessions (memory +
skills), delegates to subagents, runs scheduled jobs, and drives a real terminal and browser" (`AGENTS.md`).

- **One agent core.** Every entry point feeds `AIAgent` (`run_agent.py` → `agent/conversation_loop.py`, `agent/turn_*.py`):
  CLI, gateway, ACP, batch runner, API server and Python library. Hermes calls LLM APIs directly in three modes
  (`chat_completions`, `codex_responses`, `anthropic_messages`). It runs tool calls concurrently and has a 500-iteration
  budget (`website/docs/developer-guide/architecture.md`, `agent-loop.md`).
- **Tools and backends.**
  - 70–100 tools, depending on which doc you read.
  - Seven terminal backends: local, Docker, SSH, Singularity, Modal, Daytona and Vercel Sandbox.
  - Eight browser backends, plus computer use, vision, image generation, TTS/STT and voice mode.
- **Models.** About 45 inference providers (`website/docs/integrations/providers.md`), including local Ollama, vLLM and
  llama.cpp. Also fallback chains, credential pools, and Nous Portal's "300+ models".
- **Learning loop.**
  - Every ~10 user turns (memory) and ~10 tool iterations without a skill write (skills), a background fork reviews the
    conversation. It writes memory and skills with no human in the loop by default (`agent/background_review.py`).
  - A Curator ages out and consolidates agent-created skills.
  - FTS5 `session_search` recalls past conversations.
  - Pluggable user-model and memory providers are available, such as Honcho and Mem0.
- **Reach.**
  - A single gateway process serves ~28 messaging platforms (`website/docs/user-guide/messaging/index.md`), plus
    webhooks, an OpenAI-compatible API server, A2A and relay.
  - It also serves the CLI, an Ink TUI, an Electron Desktop app (with Bot Mode and Bot Screen), a web dashboard, and an
    ACP server for VS Code, Zed and JetBrains.
- **Automation.**
  - Cron: natural language or cron expressions, with delivery to any platform.
  - `delegate_task` in-process subagents: 10 concurrent by default.
  - `/goal` judge loops, `/loop`, and `/heartbeat`.
  - Kanban: a SQLite multi-profile task board with a dispatcher, auto-decomposition, a review lane and swarms.

**Relationship to OpenClaw.**
- OpenClaw and Hermes are the two dominant open-source "personal agent" frameworks of 2026 (Composio, Sep 15 2026). OpenClaw
  leads on channel breadth and its ClawHub marketplace; Hermes leads on its learning runtime and safer defaults.
- Hermes ships `hermes claw migrate`, which imports OpenClaw's `SOUL.md`, memories, skills, allowlists and platform
  configs (`README.md`). That is why people describe it as "OpenClaw-like".
- Neither is a software-engineering control plane at heart. Both are agents you *talk to*.

---

## 2. What sase Is

sase is "One developer. A team of coding agents. Tracked, reviewable, repeatable work." It "turns Claude Code, Codex,
Antigravity, Qwen Code, OpenCode, Meta's Muse Code, and xAI's Grok Build into a coordinated engineering team"
(`README.md`). Its defining choices:

- **No LLM loop of its own.** "SASE normally orchestrates an existing coding-agent CLI" (`docs/agent_providers.md`), and the
  README advises "if you want a standalone agent instead of a coordination layer, use those CLIs directly".
  - Providers are `sase_llm` entry points: `agy`, `claude`, `codex`, `grok`, `muse`, `opencode`, `qwen`, plus the test
    provider `fakey` (`pyproject.toml`).
  - Model choice uses cross-provider size aliases (`@xsmall`…`@xlarge`) with round-robin (`|`) and fallback (`||`). Routing
    is aware of each subscription's usage window (`docs/llms.md`).
- **Single-turn agents in isolated clones.** Each run is one provider turn in a numbered workspace clone (`<project>_<N>`).
  Continuation is always mechanical: pipe, monitor, gate or follow-up, never a promise to resume. The architecture decision
  records `single-turn-agents` and `gates-never-block` spell this out.
- **Host-owned completion.** Agents never commit. They submit a `/sase_final` declaration, and host finalizers make exactly
  one Conventional Commit per dirty repo through `sase stitch create`. Leftover dirty work fails the run
  (`docs/commit_workflows.md`; decision record `host-owned-completion`).
- **Durable work model.**
  - Beads: plans (tales and epics), sized phases (xs–xl), and typed tasks. Storage is an event-sourced Rust core with
    dependencies, notes and `+1` corroboration.
  - `sase bead work` runs phase waves and then a land agent.
  - Patches track PR-sized units of work.
  - Mentors run AI review after hooks pass.
  - SDD plan storage (`docs/beads.md`, `docs/sdd.md`, `docs/mentors.md`, `docs/change_spec.md`).
- **Human gates everywhere**, as durable records rather than blocking processes:
  - plan approval
  - questions
  - launch approval, required for any agent-initiated agent launch
  - custom gates
  - typed sudo requests with hashed executables (beta flag `agent_sudo_requests`)
  - task-triage gates (`docs/notifications.md`, `docs/sudo.md`)
- **Operations.**
  - A per-machine service host runs the scheduler (routines and jobs, interval-based) and an optional gateway.
  - The Textual TUI has Agents, Artifacts and Services tabs plus an Admin Center.
  - A Telegram plugin, a Rust mobile gateway (for an Android client), and a Neovim/LSP integration.
  - Tailnet remote dispatch (`%dispatch:<machine>`).
  - Audit logs for memory reads, repo opens, artifact reads and skill use; local telemetry; usage-window probes.

---

## 3. Is Hermes "a lot like" sase? A Layer Model

The clearest way to see both the overlap and the difference is to stack the layers of an agent system:

| Layer                                       | Hermes                                                                                   | sase                                                                                                      |
| ------------------------------------------- | ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| 1. Model access                             | Owns it: ~45 providers, local models, fallback, credential pools                         | Delegates to vendor CLIs; adds cross-CLI size aliases, usage windows, auto-disable on limits              |
| 2. Agent loop and tools                     | **Owns it**: `AIAgent`, 70–100 tools, 7 terminal backends, browser, voice                | **Does not own it**: inherits Claude Code's, Codex's, etc. tools and harness                              |
| 3. Session, memory and learning             | **Deep**: learning loop, session FTS, curator, user modeling                             | Curated, audited, structured project memory; no autonomous learning                                       |
| 4. Multi-agent orchestration and tracking   | Solid: Kanban board and dispatcher, `delegate_task`, `/goal`, Bot Mode                   | **Deep**: beads, epics, phases, land agents, clans/families, typed launches, capacity, remote dispatch    |
| 5. Engineering governance and landing       | Thin to moderate: worker-owned git, review lane, PR required-checks contract             | **Deep**: host-owned commits, Patches, hooks, mentors, CRS, gates, provenance                             |
| 6. Surfaces and reach                       | **Very broad**: 28 chat platforms, desktop, web, TUI, ACP, API, voice                    | Focused: TUI, CLI, Neovim/LSP, Telegram, Android gateway                                                  |

**What the table shows.**
- Hermes is thick in layers 1–3 and 6. It has grown a respectable layer 4 and a thin layer 5.
- sase deliberately skips layers 1–2, keeps layers 3 and 6 thin, and is thick in layers 4 and 5.
- So "Hermes is a lot like sase" is true for **layer 4 and part of layer 5**, the Kanban / "Engineering pipelines" story.
  Hermes lists that pipeline as one of five Kanban use cases: "decompose → implement in parallel worktrees → review →
  iterate → PR" (`website/docs/user-guide/features/kanban.md`). It is not true for the rest of either product.

**The two products are complementary, not just competitive** (inference, with evidence):
- Hermes's Kanban explicitly lacks what sase's core does. Hermes says: "Wiring a non-Hermes CLI tool (Codex CLI, Claude Code
  CLI, OpenCode CLI…) as a kanban worker lane is *not yet a paved path*" (`kanban-worker-lanes.md`).
- Conversely, Hermes has a clean headless mode, `hermes chat -q "…" --oneshot --format stream-json`
  (`website/docs/reference/cli-commands.md`). That is exactly the shape of a sase `sase_llm` provider.

---

## 4. Capability Matrix

Edge key: **H** = Hermes clearly ahead, **S** = sase clearly ahead, **≈** = rough parity or different-but-equivalent,
**H≫** / **S≫** = one side has it and the other effectively does not.

| Area                                   | Hermes                                                                                                                                                         | sase                                                                                                                                                              | Edge |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- |
| Own agent loop                         | Yes (`AIAgent`), 3 API modes, prompt-cache discipline                                                                                                           | No, by design; relies on vendor CLIs                                                                                                                              | H≫   |
| Coding quality per agent run           | Own loop + LSP diagnostics + checkpoints; optional Codex app-server runtime                                                                                    | Inherits Claude Code, Codex, Grok Build, etc.: frontier coding harnesses                                                                                          | ≈    |
| Heterogeneous vendor agents            | Skills that drive `claude -p` / `codex exec` / tmux through the terminal; Codex runtime opt-in; no Kanban lane                                                 | 7 CLIs natively; multi-model fan-out; `%alt`; cross-provider aliases                                                                                              | S≫   |
| Durable task graph                     | Kanban: SQLite, `task_links`, runs, events, claims, retries, auto-decompose, swarm                                                                             | Beads: event-sourced; plan/epic/phase/task, deps, notes, `+1`, task types, triage                                                                                 | ≈/S  |
| Structured epics and landing           | Flat graph + "root" card; no plan tier; no integration/land agent                                                                                              | Plan approval → epic → sized phases → land agent (verify, integrate, nested epics)                                                                                 | S    |
| Per-task review loop                   | Built-in `review` column; auto-spawned `sdlc-review` reviewer; request-changes loop                                                                            | Mentors on Patches, land-agent verification, CRS for human PR comments; no per-bead review lane                                                                   | H    |
| Commit and PR ownership                | Worker LLM runs `git`/`gh`; host gate checks GitHub required checks, read-only                                                                                 | Host-owned finalizers; one Conventional Commit per dirty repo; Patches; `#pr` workflow                                                                            | S≫   |
| Workspace isolation                    | Git worktrees per task or subagent (opt-in for subagents); scratch dirs                                                                                         | Full numbered clones with git alternates, registry, rescue store                                                                                                   | ≈/S  |
| Checkpoint / rollback                  | Shadow-git checkpoints, `/rollback` (off by default)                                                                                                            | Workspace isolation + commits; no in-run rollback UX                                                                                                               | H    |
| Goal / "Ralph" loops                   | `/goal` judge + shell quality gates; `/loop`; `/heartbeat`                                                                                                      | `%repeat`, pipes, monitors, `%wait`; no judge-driven continuation loop                                                                                             | H    |
| Scheduling                             | Cron: NL or cron expressions, delivery anywhere, `wakeAgent` pre-checks, executions ledger                                                                      | Scheduler: interval routines/jobs, triggers, `proposed_launches`, `%wait(time=…)`                                                                                  | H    |
| Human approval gates                   | Per-command approvals (smart/manual/off), block/unblock, pending memory/skill writes                                                                            | Durable typed gates: plan, question, launch, sudo, custom, triage; `%auto`                                                                                        | ≈    |
| Runtime containment                    | Docker (cap-drop ALL, pids limits), Modal, Daytona, Singularity, SSH, Vercel; egress proxy; hardline blocklist                                                  | None: CLIs run with bypass flags; isolation is the git clone; sudo gate                                                                                           | H≫   |
| Prompt-injection defenses              | Context-file scanning, `<untrusted_tool_result>` wrapping, memory/cron write scans, SSRF guard                                                                  | Relies on vendor CLIs; audited repo and artifact reads                                                                                                             | H    |
| Memory                                 | Bounded `MEMORY.md`/`USER.md`, auto-written; session FTS recall; 9 external providers                                                                           | Core/reference notes + memory webs (glossary, decisions); audited reads; gated writes                                                                              | ≈ (different goals) |
| Autonomous learning                    | Background review → memory + skills; Curator; `/learn`; `/journey`                                                                                               | None by design; discovered work → task/memory beads → human triage                                                                                                 | H≫   |
| Skills                                 | 58 bundled + 150 optional; agentskills.io; hubs with trust tiers; agent-authored                                                                                 | 19 generated control-plane skills deployed to each provider; provenance-guarded deploys; usage audit                                                               | H    |
| Reusable prompts / workflows           | Skills-as-slash-commands, bundles, cron `context_from`, `execute_code` RPC scripts                                                                               | XPrompts (typed, Jinja2), YAML workflows (agent/bash/python/parallel/loop/HITL), swarms                                                                            | S    |
| Messaging and mobile                   | ~28 platforms, DM pairing, per-user sessions, voice memos, deliverable uploads                                                                                  | Telegram plugin + Android client over the Rust gateway                                                                                                             | H≫   |
| Desktop / web / IDE                    | Electron Desktop, web dashboard, Ink TUI, ACP server                                                                                                            | Textual TUI (deep ops console), Neovim + xprompt LSP; no web UI                                                                                                    | H    |
| Programmatic interfaces                | OpenAI-compatible API (`/v1/runs`), MCP client **and** server, A2A, Python library                                                                              | CLI (~62 commands, JSON outputs), plugins; no MCP/ACP/API server                                                                                                  | H    |
| Multi-machine                          | Federation of full installs (Desktop connections, peer, A2A, relay); SSH/cloud sandboxes; Kanban single-host                                                    | Tailnet remote dispatch of CLI agents with unified Agents list and remote gates; sidecar sync                                                                      | ≈    |
| Model and provider flexibility         | ~45 providers incl. local; fallback; credential pools                                                                                                           | 7 subscription CLIs; size aliases; usage-window routing; provider drain                                                                                            | H (breadth) / S (subscription economics) |
| Observability and provenance           | Logs, `/usage`, `/insights`, Kanban events/runs, observer hooks                                                                                                  | Memory/skill/repo/artifact audit logs, telemetry DB, Statistics tab, LLM Calls timeline, bead history, `SASE_BEAD` footers                                         | S    |
| Extensibility                          | Plugins (tools, platforms, memory, context engines, providers, secrets, terminals); 4 hook systems incl. Claude-Code-compatible shell hooks                     | 11 pluggy entry-point groups (LLM, VCS, workspace, finalizers, task types, artifact refs…)                                                                         | H    |
| OS support                             | macOS, Linux, native Windows, WSL2, Termux, Docker, Nix                                                                                                         | Linux and macOS only                                                                                                                                                | H    |
| Voice / browser / vision / computer use | Yes                                                                                                                                                            | Only what the wrapped CLI offers; nothing from sase                                                                                                                | H≫   |
| RL / trajectory data                   | `batch_runner.py`, trajectory compressor, ShareGPT trajectories                                                                                                 | None                                                                                                                                                                | H≫   |

---

## 5. Deep Dives on the Overlap

### 5.1 Multi-agent orchestration: Hermes Kanban vs. sase beads and `sase bead work`

**Hermes Kanban** (`website/docs/user-guide/features/kanban*.md`, `hermes_cli/kanban_db*.py`) is well engineered.

*Data model and dispatch*
- Every task is a row in a per-board SQLite DB with `task_links`, `task_runs`, append-only `task_events` and comments.
- A dispatcher inside the gateway ticks every 60 seconds. On each tick it reclaims stale claims, promotes `todo → ready`
  when all parents are `done`, claims tasks atomically (`BEGIN IMMEDIATE`), and spawns each worker as its own
  `hermes -p <profile> … chat -q "work kanban task <id>"` process.

*Failure handling*
- Claim TTLs.
- PID fingerprinting.
- Exit-code classes: `75` means rate-limited and is requeued; `78` means a terminal provider error and blocks the task.
- A "protocol violation" budget for workers that exit without a terminal board call.
- Respawn guards, for example not respawning while an active PR exists.

*Workflow features*
- Auto-decomposition of triage cards by an auxiliary LLM.
- `hermes kanban swarm` topologies: workers → verifier → synthesizer.
- A native review lane.
- Per-task model, provider, skills and goal-mode overrides.

*Where you can control it*
- CLI, the dashboard, Desktop, and `/kanban` from any chat platform.

**sase's equivalent** is spread across several parts, and each is deeper in the software-engineering direction:
- **Task structure is richer.** Plans have a *tier* (tale vs epic). Epics break into *sized* phases (xs–xl), and phase size
  picks the model alias, so large and xlarge phases get `#plan` first. A **land agent** then verifies every child's claims
  against the source and commits. It also integrates changes that landed on the base branch meanwhile, triages
  `PROPOSED FOLLOW-UP:` notes into task beads, cleans up `--epic-symbol` whitelists, and resumes nested landings
  (`src/sase/default_config.yml`, `bd/land_epic`). Hermes has no plan tier and no land or integration agent. Its
  equivalent is a synthesizer card or a human.
- **Workers can be any vendor CLI.** One prompt can fan out to Claude, Codex and Antigravity at once (`README.md`). Hermes
  workers are always Hermes processes; external CLIs are reached only through prompt-level skills that drive
  `claude -p` / `codex exec` / tmux.
- **Launch control is richer:**
  - clans, families and tribes
  - `%wait` on agents, beads, procs or times
  - `%queue` with weights and priorities
  - capacity units (`max_running_agents`)
  - `%hold`, `%repeat`, `%alt`
  - launch approval for any agent-initiated launch (`docs/xprompt.md`, `docs/agent_families.md`)
- **Discovered work is governed.** Agents file typed task beads through a dedupe/corroborate skill (`/sase_new_task`).
  Human `TaskTriage` gates decide whether to launch, close or snooze them.

**Hermes is ahead on:**
- **Built-in per-task review.** `request_review` automatically spawns a reviewer with the bundled `sdlc-review` skill, which
  rotates artifact → execution → contract lenses and can send work back.
- **Automatic decomposition.** sase leaves decomposition to a human-approved `/sase_plan`, which is safer but slower.
- **Explicit exit-code taxonomy and protocol-violation budgets.**

**Neither distributes one task graph across machines.** Hermes: "Kanban is deliberately single-host". sase's
remote-dispatch v1 cannot combine `%dispatch` with `%wait`/`%queue`/`%clan` (`docs/remote_dispatch.md`).

**Verdict:** sase is ahead for engineering epics. Hermes is ahead for generic agent pipelines (research, ops, "digital
twins") and on built-in review.

### 5.2 Isolation and landing

**Hermes: isolation**
- Kanban `worktree` workspaces use `<repo>/.worktrees/<task-id>` on branch `wt/<task-id>`.
- Subagent worktrees are opt-in and "degrade silently" to a shared directory without git or with a non-local backend
  (`delegation.md`).
- Isolation is "cooperative runtime scoping, **not OS confinement**" unless you choose a container backend.

**Hermes: landing**
- Landing is the worker LLM's job. The tutorial tells workers to use "terminal/file tools… commit".
- The Codex skill's example pushes with `git push -u` and opens a PR with `gh pr create` from the agent.
- The host's only landing control is the PR completion contract (`--completion-contract OWNER/REPO`). It verifies
  required checks and rulesets through `gh`, and "No remote writes are performed by this gate".
- Hermes also has shadow-git **checkpoints** with `/rollback`. They are off by default and unavailable on container
  backends.

**sase**
- Isolation is a full clone per run. Landing is owned by the host: agents cannot commit, and finalizers enforce one
  Conventional Commit per dirty repo, record evidence, and fail runs that leave dirty work.
- Every commit carries a `SASE_BEAD=` footer.
- Patches track PR state, hooks, comments and mentor reviews.
- sase has **no** built-in "all required CI checks green" completion gate. Agents watch CI through monitors and file `ci`
  beads.
- sase has no in-run rollback UX.

**Verdict:** sase's model is stronger governance. The agent cannot mis-land, and every landing is attributable. Hermes's
PR-contract gate and checkpoints are worth borrowing.

### 5.3 Human-in-the-loop and safety

These are **opposite philosophies**.

**Hermes: governs individual actions**
- Command approvals run in `smart` mode by default: an auxiliary LLM rates each command APPROVE, DENY or ESCALATE.
  Alternatives are `manual` and `off`.
- Headless modes (cron, single-query, unattended) default to `deny`.
- A hardline blocklist applies even under `--yolo`.
- Container hardening; an egress proxy that gives sandboxes proxy tokens instead of real keys; a credential vault.
- Prompt-injection scanning of context files; `<untrusted_tool_result>` wrapping; scanning of memory and cron writes.
- DM pairing with rate limits and lockouts.
- Hermes is candid that "The only security boundary against an adversarial LLM is the operating system" (`SECURITY.md`),
  and much of this is defense in depth.

**sase: governs lifecycle decisions, not individual commands**
- Gates cover what gets planned, launched, escalated (sudo) and landed.
- Every CLI runs with its permission bypass (`--dangerously-skip-permissions`,
  `--dangerously-bypass-approvals-and-sandbox`, and so on) in a git clone, with no container option (`docs/llms.md`).
- sase has no per-command approval or containment layer of its own.
- It does add unusually strong provenance: hash-bound gate commands, sudo manifests with executable SHA-256s, audited reads
  of repos, artifacts and memory, and write-once decision receipts.

**Verdict:** Hermes is far ahead on containment, and more generally on safety when running untrusted inputs. sase is ahead
on governance and auditability of a trusted developer's own agent fleet. For sase's stated use (one developer, their own
repos, their own machines) its model is coherent. For anything facing untrusted input, such as public chat bots, it is not
sufficient.

### 5.4 Memory and the learning loop

This is the sharpest **philosophical** contrast.

**Hermes: adaptive and autonomous**
- A bounded memory (2,200 chars in `MEMORY.md`, 1,375 in `USER.md`) is written *by the agent*, loaded as a frozen snapshot
  per session, and scanned for injection.
- Background reviews write memory and skills without approval by default. Opt-in `write_approval` stages them for
  `/memory approve` or `/skills approve`.
- `session_search` gives FTS5 recall over all past sessions.
- Optional user-modeling providers (Honcho "dialectic reasoning").
- A Curator marks unused agent-authored skills stale and archives them, with snapshots, a ledger and rollback
  (`website/docs/user-guide/features/memory.md`, `curator.md`, `sessions.md`).

**sase: curated, typed and audited**
- Core notes are inlined into every provider's instruction file. Reference notes are read on demand with a logged reason.
  Memory webs are keyed strand collections with `[[links]]` and supersession (the `glossary` and `decisions` webs).
- Agents may edit memory only when the prompt, an approved plan or an assigned bead authorizes it. Otherwise they file a
  `memory` task bead (`docs/memory.md`, the `sase_memory_write` skill).
- There is no automatic session-to-memory distillation. There is no cross-session recall index beyond transcript lookup
  (`sase chat list -q`, `/sase_chats`). There is no user model.
- sase's own decision records say not to build retrieval machinery ahead of a corpus that needs it (decision
  `corpus-before-mechanism`).

**Verdict:**
- For a personal assistant, Hermes is decisively better: it "gets sharper over time" without human effort.
- For a codebase several agents share, sase's approach has real advantages: memory is reviewable, versioned, attributable
  and cannot be poisoned by a prompt-injected session. But it depends on human curation.
- Hermes's own documentation shows the cost of its approach. The review prompt must explicitly warn against capturing
  "negative claims about tools" and failed workflows. Small models "claim a save without calling the tool". The agent-write
  content scanner is off by default because of false positives.

### 5.5 Skills

**Hermes.** Skills are its main extension mechanism for *capability*:
- 58 bundled and ~150 optional skills.
- The agentskills.io format.
- Hubs (ClawHub, LobeHub, skills.sh, GitHub taps) with trust tiers and install-time scanning.
- Every skill becomes a slash command.
- Agent-authored skills are managed by the Curator.

**sase.** Its 19 skills are mostly *protocol* skills:
- `sase_final`, `sase_plan`, `sase_questions`, `sase_run`, `sase_monitor`, `sase_memory_*`, and so on.
- They teach any vendor CLI to follow sase's lifecycle.
- They are rendered from versioned templates into each provider's skill directory, with provenance-guarded deploys and a
  usage audit.
- sase's real reusable-capability layer is **XPrompts and YAML workflows**, which are more structured than Hermes's skills:
  typed inputs, parallel, loop and HITL steps, and swarms.

**Verdict:** Hermes is ahead on breadth and on self-authoring. sase is ahead on reproducibility and on cross-provider
deployment. The two treat "skill" as quite different things.

### 5.6 Scheduling and automation

**Hermes.** Cron is a user-facing product feature:
- "every weekday at 9, triage my inbox and Slack me"
- cron expressions, intervals or ISO timestamps
- `wakeAgent` pre-check scripts that can skip the LLM
- `context_from` chaining
- `[SILENT]` suppression
- webhook triggers
- an executions ledger that never automatically reruns "unknown" attempts
- delivery to any platform

Add `/goal`, `/loop` and `/heartbeat` for in-session autonomy.

**sase.** The scheduler is mainly the *engine* behind its engineering automation. Its default routines run:
- hook checks
- mentor checks
- wait checks
- task triage
- external PR and issue mirroring
- usage refresh
- error digests
- housekeeping

User jobs are interval-based scripts that can return `proposed_launches`. There are no cron expressions, no natural-language
scheduling, and delivery goes only to sase's own notification channels (`docs/axe.md`).

**Verdict:** Hermes is clearly ahead as a scheduling product. sase's scheduler is sufficient for sase's workflows.

### 5.7 Surfaces and reach

| Surface                  | Hermes                                                                                                     | sase                                                            |
| ------------------------ | ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| Terminal                 | prompt_toolkit CLI + Ink TUI (chat-centric)                                                                | Textual TUI (ops-console-centric: agents, artifacts, services, admin) |
| Desktop                  | Electron app (macOS, Windows, Linux), Bot Mode, Bot Screen                                                  | —                                                               |
| Web                      | Dashboard, auth-gated off loopback, embeds the TUI                                                          | — (roadmap only)                                                |
| Chat                     | ~28 platforms from one gateway; per-user sessions; DM pairing                                               | Telegram (plugin)                                               |
| Mobile                   | Via chat apps and the web dashboard                                                                         | Android client over the Rust gateway (fixed product actions)    |
| Editor                   | ACP server (VS Code, Zed, JetBrains)                                                                        | Neovim plugin + xprompt LSP                                     |
| Machine APIs             | OpenAI-compatible API, `/v1/runs`, MCP server, A2A, Python library                                          | CLI with JSON output; mobile gateway API                        |
| Voice                    | Voice mode, wake word, Discord voice                                                                        | —                                                               |

sase's TUI is a much deeper *operations* console for a fleet of engineering agents than anything in Hermes. Hermes's
closest equivalents are the Kanban dashboard and Desktop's live-subagent panes. Everywhere else, Hermes's reach is an order
of magnitude broader.

### 5.8 Multi-machine

**Hermes** federates whole installs:
- Desktop's multi-connection registry: local, remote gateway, SSH, Hermes Cloud.
- `hermes peer`, A2A (`a2a_orchestrate`), and relay for NAT'd gateways.
- Commands can also run remotely through the SSH, Modal, Daytona or Vercel backends.

**sase** has Tailnet machine enrollment and `%dispatch:<alias>`, which sends a CLI agent to another enrolled host.
Remote agents appear in the same Agents list with a host chip, remote gates come back to the local inbox, and state syncs
through git sidecars (`docs/remote_dispatch.md`, `docs/agents_sidecar.md`).

**Verdict:** rough parity with different shapes. Hermes is broader (cloud sandboxes, hosted instances). sase's model of
"my fleet as one pane" is more integrated for supervising coding agents.

### 5.9 Models and cost model

**Hermes:**
- Much wider model reach, including local models, which sase can only get indirectly through OpenCode or Qwen.
- Treats per-conversation prompt caching as an invariant ("Per-conversation prompt caching is sacred", `AGENTS.md`).
- By default it pays per token, unless you route through Nous Portal, `hermes proxy` or the Codex runtime.

**sase** is built to exploit **flat-rate subscription CLIs** (Claude, Codex, Grok, and others):
- usage-window probes
- automatic disable at limits
- weighted round-robin and fallback across vendors
- an effort ladder for size aliases (decision `size-alias-effort-ladder`)

For heavy coding workloads this is a real functional advantage in throughput per dollar. Hermes does not attempt it.

### 5.10 Engineering maturity (context, not scored as popularity)

| Measure                  | Hermes                                             | sase                                              |
| ------------------------ | -------------------------------------------------- | ------------------------------------------------- |
| Tests                    | ~39k tests (`AGENTS.md`, Sep 2026)                 | ~40.2k `def test_` across 4,393 test files        |
| Commits                  | ~40.8k since 2025-07-22 (~20.8k since 2026-08-01)  | ~14.8k since 2026-02-14 (~3.2k since 2026-08-01)  |
| Contributors             | Thousands (open community)                         | One developer plus their agent fleet              |
| Languages                | Python + TypeScript (Desktop, TUI, web)            | Python + a required Rust core (`sase_core_rs`)   |

Both projects are heavily engineered with comparable test depth. Hermes's surface is far larger. sase's is narrower and
unusually disciplined: host-owned completion, decision records, audited reads, and the Rust core boundary.

---

## 6. Summary: Where Each Wins

**sase clearly wins (functionally):**
1. Orchestrating *heterogeneous* vendor coding CLIs as first-class, supervised, tracked workers.
2. Host-owned, attributable landing: finalizers, Patches, `SASE_BEAD` footers, no agent-authored commits.
3. Epic-scale engineering work: plan approval → sized phases → verifying and integrating land agents → nested epics.
4. Lifecycle governance: durable typed gates, launch approval, sudo with hashed executables, task triage.
5. Provenance and audit: memory, skill, repo and artifact read logs, bead event history, the prompt archive.
6. Subscription-aware routing across vendors (usage windows, auto-disable, effort ladders).
7. An operations console (TUI) for a fleet of coding agents across projects and machines.

**Hermes clearly wins (functionally):**
1. Being an agent at all, including for non-coding work: its own loop, ~100 tools, browser, computer use, voice, vision.
2. The closed learning loop: autonomous memory and skill growth, curation, FTS session recall, user modeling.
3. Reach: 28 chat platforms, Desktop, web dashboard, ACP, API server, MCP (both directions), A2A.
4. Runtime containment: 7 terminal backends, hardened Docker, egress proxy, injection defenses, per-command approvals.
5. Scheduling as a product: cron expressions and natural language, delivery anywhere, `/goal`, `/loop`, `/heartbeat`.
6. Built-in per-task review lanes, PR required-checks completion contracts, checkpoints and rollback, LSP feedback.
7. Model breadth (~45 providers, local models) and OS breadth (native Windows, Termux, Docker, Nix).

**Roughly even (different shapes):** durable task graphs, multi-machine operation, workspace isolation, and HITL gating
(per-command in Hermes vs per-lifecycle in sase).

---

## 7. Implications for sase (Brief)

The prompt asked for a comparison and a rating, not a roadmap. Still, the comparison points to a few high-leverage, on-strategy
moves. Each would keep sase's governance philosophy.

1. **Add Hermes as an 8th `sase_llm` provider.** Hermes has a headless mode: `hermes chat -q … --oneshot --format
   stream-json`. As a provider it would bring Hermes's any-model and local-model loop, browser and LSP under sase's
   workspaces, gates and finalizers. It turns the main competitor into a supplier, and it fills exactly the "external CLI
   lane" gap that Hermes's Kanban documents.
2. **A per-bead review lane** in `sase bead work`: reviewer agent → request-changes loop before a phase closes. Hermes's
   `request_review` + `sdlc-review` shows the pattern.
3. **A required-checks completion gate for `#pr` Patches**, modeled on Hermes's read-only `--completion-contract`.
4. **Staged, agent-proposed memory drafts.** This is Hermes's `write_approval` pattern. It fits sase's gated model better
   than memory task beads for small facts, and would give sase part of the learning loop without giving up curation.
5. **Transcript recall** (an FTS index over chats and artifacts, callable by agents). The April report recommended this
   too, and it is still the most-requested capability Hermes has that sase lacks.
6. **An optional container or sandbox execution mode** for untrusted inputs (for example GitHub-issue-driven launches through
   `external_issue_mirror`).

---

## 8. Rating: How Well Does sase Compete Functionally with Hermes?

**Scale.**
- Per dimension, sase scores **0 = absent, 10 = matches or exceeds Hermes**. Exceeding Hermes is capped at 10, so sase's
  wins cannot mask missing capabilities.
- Weights reflect how central each dimension is to Hermes's functional value. They sum to 100.
- Popularity and adoption are excluded, as requested.

| Dimension                                              | Weight | sase score | Rationale                                                                                                        |
| ------------------------------------------------------ | -----: | ---------: | ---------------------------------------------------------------------------------------------------------------- |
| Single-agent capability (tools, modalities, coding)    |     10 |          4 | Coding runs inherit frontier CLIs (≈ parity); no voice, browser or vision of its own; single-turn, not conversational |
| Learning loop, memory, recall                          |     13 |          3 | Excellent curated memory, but no autonomous learning, no session recall index, no user model                       |
| Skills                                                 |      5 |          5 | Versioned cross-provider protocol skills; no self-authoring, hub or breadth                                         |
| Reach and surfaces (chat, desktop, web, voice, IDE)    |     13 |        2.5 | TUI, Telegram, Android, Neovim vs ~28 platforms, Desktop, web, ACP, voice                                           |
| Scheduling and autonomous loops                        |      7 |        4.5 | Solid interval scheduler; no cron or NL, delivery breadth, or `/goal` loops                                         |
| Multi-agent orchestration and task tracking            |     11 |        8.5 | Exceeds on heterogeneous CLIs and epic structure; trails on auto-decompose and built-in review                     |
| Engineering governance and landing                     |      8 |          9 | Host-owned commits, Patches, mentors, land agents exceed Hermes; lacks a PR required-checks gate and rollback       |
| Human-in-the-loop gating                               |      4 |          7 | Richer lifecycle gates; no per-command approvals                                                                    |
| Safety and runtime containment                         |      8 |        3.5 | No sandbox; bypass flags; sudo gate and audits are real but not containment                                         |
| Multi-machine                                          |      5 |          6 | Integrated remote dispatch; no cloud sandboxes or hosted instances                                                  |
| Model and provider flexibility                         |      5 |          6 | Fewer providers and no direct local models; unique subscription-window economics                                    |
| Observability and provenance                           |      4 |          9 | Exceeds Hermes on audit and provenance                                                                              |
| Extensibility and interop (plugins, MCP, ACP, API)     |      4 |          4 | Good plugin groups; no MCP, ACP or API surface                                                                      |
| Platform support                                       |      3 |          3 | POSIX only vs Windows, Termux, Docker, Nix                                                                          |
| **Weighted total**                                     |  **100** | **≈ 5.1**  |                                                                                                                  |

### Final rating: **5 / 10**

What the number means: weighted by what Hermes offers, sase matches or beats it on about half the functional surface.
**The distribution matters more than the average:**

- **Supervised, multi-agent, multi-vendor software engineering: ~8.5 / 10.** In this domain sase is the more capable
  system. A developer running epics across Claude Code, Codex and Grok, who wants every landing attributable and
  gate-approved, gets more from sase than from Hermes Kanban. Hermes cannot yet run those CLIs as Kanban workers at all.
- **General-purpose, always-on personal agent (Hermes's home turf, and OpenClaw's): ~1.5 / 10.** sase is not a
  competitor here. It has no loop of its own, no learning, a single chat platform, no voice or browser, and no sandbox.

### What would move the rating

**Upward** (most leverage first):
- Hermes-as-provider (§7.1)
- agent-callable transcript recall
- staged agent-proposed memory
- a sandbox mode
- an MCP control-plane server
- broader chat delivery through the existing gateway

Together these could plausibly lift the overall score to about 6–6.5 without abandoning sase's identity.

**Downward:** Hermes shipping a paved external-CLI Kanban lane plus host-side commit ownership. Both are explicitly
anticipated in its docs (`spawn_fn` is pluggable; there are reserved `workflow_template_id` columns for "v2 workflow
routing"). That would erode sase's strongest differentiators.

---

## Caveats

- I did not run Hermes. Its behavior is taken from docs and code at `358d50ca6d`. The docs drift in places: the curator's
  stale/archive windows (docs say 30/90 days, config defaults are 14/30), whether "session search" uses LLM summarization
  (the README says yes, the docs say "no LLM calls"), and tool and test counts.
- Several sase capabilities are beta or flag-gated (sudo requests, `%proc`, provider drain). Remote dispatch v1 has
  documented limits.
- The weights in §8 are judgment calls. Someone who only cares about software-engineering orchestration should read the
  domain-level ratings (~8.5 vs ~1.5) rather than the blended 5 / 10.

---

## Sources

**Hermes (local checkout via `sase repo open gh:NousResearch/hermes-agent`, HEAD `358d50ca6d`, tag `v2026.9.21`)**

- `README.md`, `AGENTS.md`, `SECURITY.md`, `pyproject.toml`
- `website/docs/user-guide/features/{kanban,kanban-worker-lanes,kanban-multi-gateway,delegation,goals,loops,heartbeat,cron,curator,skills,memory,memory-providers,hooks,plugins,codex-app-server-runtime,lsp,code-execution,api-server,acp,mixture-of-agents,batch-processing,deliverable-mode}.md`
- `website/docs/user-guide/{security,git-worktrees,checkpoints-and-rollback,sessions,profiles,desktop,bot-mode,multi-connection-desktop}.md`,
  `website/docs/user-guide/messaging/{index,a2a,relay}.md`
- `website/docs/developer-guide/{architecture,agent-loop,subagent-lifecycle-api,multiplexing-gateway,gateway-internals}.md`,
  `website/docs/reference/cli-commands.md`, `website/docs/integrations/providers.md`
- `skills/autonomous-ai-agents/{claude-code,codex,opencode}/SKILL.md`, `skills/devops/sdlc-review/SKILL.md`
- `hermes_cli/kanban_db.py`, `hermes_cli/kanban_db_dispatch.py`, `hermes_cli/kanban_db_workspace.py`,
  `hermes_cli/kanban_pr_acceptance.py`, `agent/background_review.py`, `agent/prompt_builder.py`, `tools/approval*.py`

**sase (this repository, `master` at `e1c4208cd`)**

- `README.md`, `CHANGELOG.md`, `pyproject.toml`, `src/sase/default_config.yml`, `src/sase/xprompts/`
- `docs/{architecture,agent_providers,llms,agent_families,xprompt,workflow_spec,beads,sdd,axe,memory,mentors,commit_workflows,change_spec,vcs,notifications,sudo,tool,remote_dispatch,agents_sidecar,mobile_gateway,telemetry,plugins,editor,cli,workspace}.md`
- Prior research: `research:202604/sase_vs_hermes_agent.md` (read via `sase artifact read`)

**Web (context and timing only)**

- [Hermes Agent: Nous Research](https://hermes-agent.nousresearch.com/)
- [Hermes Agent documentation](https://hermes-agent.nousresearch.com/docs/)
- [OpenClaw vs Hermes Agent: Composio (Sep 15, 2026)](https://composio.dev/content/openclaw-vs-hermes-agent)
- [Hermes Agent vs OpenClaw: Pickaxe](https://pickaxe.co/post/hermes-agent-vs-openclaw)
- [Hermes Agent vs OpenClaw, May 2026: Lushbinary](https://lushbinary.com/blog/hermes-agent-vs-openclaw-updated-comparison-may-2026/)
- [Nous Research Ships Bot Mode for Hermes Agent: MarkTechPost (Aug 17, 2026)](https://www.marktechpost.com/2026/08/17/nous-research-hermes-bot-mode/)
- [Hermes Agent Updates, September 2026: Releasebot](https://releasebot.io/updates/nousresearch/hermes-agent)
