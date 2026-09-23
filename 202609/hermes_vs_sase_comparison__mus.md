# Hermes Agent vs SASE — Comparison and Functional Rating

Researcher: mus (`__mus`) — independent swarm report.
Date (UTC): 2026-09-23.
Scope: compare/contrast the Hermes project with this project (SASE), functionally only (no popularity/adoption weighing). End with a rating of how well SASE competes with Hermes.

## Sources and provenance

Hermes checkout (opened for this research via `sase repo open gh:NousResearch/hermes-agent`):

- Path used for reads: `sase/repos/external/gh/NousResearch/hermes-agent/`
- Hermes version: `0.21.4` (`pyproject.toml`), `description`: "The self-improving AI agent".
- Hermes HEAD at read time: `358d50ca6d`.
- Key files read: `README.md`, `AGENTS.md`, `SOUL.md`, `toolsets.py`, `providers/README.md`, `plugins/model-providers/` listing, `plugins/platforms/` listing, `tools/` listing, `gateway/channel_directory.py` (head), `cron/` listing, `tools/environments/` listing, `batch_runner.py` (head), `hermes_cli/` listing, `apps/desktop` + `ui-tui` listings.

SASE checkout (this workspace):

- SASE version: `0.17.1` (`pyproject.toml`); `sase-core-revision.txt`: `430016645d10590c75bff39fdbfc62cc89177fcd`.
- SASE HEAD at read time: `e1c4208cd`.
- Key files read: `README.md`, `docs/architecture.md`, `docs/cli.md` (head), `docs/agent_providers.md`, `docs/workspace.md`, `docs/axe.md`, `docs/ace.md` (head), `docs/xprompt.md` (head), `docs/memory.md` (head), `docs/mobile_gateway.md` (head), `docs/integrations.md` (head), `docs/monitors.md` (head), `src/sase/` listing.

External sources (used only for content a checkout does not contain — docs/discussion/positioning):

- Hermes docs/positioning snippets via web search (OpenRouter-era "successor to OpenClaw" framing, "agent that grows with you", OpenClaw-migration reporting, multi-platform gateway descriptions).
- OpenClaw architecture descriptions (gateway + brain/ReAct + Markdown memory + skills + heartbeat/cron) for the "like OpenClaw" half of the question.

What this report did NOT use: no peer swarm reports (`__cld.md` / `__gem.md`), no chat transcripts, no filenames beyond a `grep -i hermes` existence check (result: no hermes files yet) plus an exact-path existence check for the new report filename.

Caveat: both projects move fast. Pin the versions/SHAs above when reusing this comparison.

## TL;DR

Hermes and SASE rhyme but are not the same kind of thing:

- **Hermes is a personal autonomous agent** in the OpenClaw shape: one long-lived assistant with its own LLM loop, ~60+ core model tools, memory + self-improving skills, a 16–20-platform messaging gateway, cron, subagents, browser/computer-use, voice/image/TTS, an Electron desktop app and TUI, and seven terminal backends from laptop to serverless VMs. It explicitly courts OpenClaw users (`hermes claw migrate`; onboarding banner detects `~/.openclaw/`).
- **SASE is an orchestration layer over other agents' CLIs**: it does not implement its own coding-agent loop (the only bundled exception is the `fakey` test provider). It turns Claude Code, Codex, Antigravity, Qwen Code, OpenCode, Muse Code, and Grok Build into a supervised team via isolated numbered workspaces, Patches/stitches, beads, artifacts/artifact-refs, XPrompts/workflows, a keyboard-driven TUI, a scheduler (AXE), a service host, monitors, and a mobile gateway.

So "a lot like OpenClaw" is accurate for Hermes and mostly inaccurate for SASE. "A lot like this project" is true only at the supervision/automation vocabulary level (TUI, scheduler/cron, subagents/parallelism, memory, plugins, mobile/remote operation). At the product level they are complements, not substitutes: Hermes replaces your agent; SASE supervises your agents.

Functional rating (SASE as a Hermes competitor, popularity excluded): **6/10 overall** — strong parity-or-better in team orchestration, weak as a drop-in personal agent. See scoring section for the dimension breakdown and what would move the number.

## What Hermes is (grounded)

- Personal agent core run across CLI, messaging gateway, TUI, and Electron desktop app ("same agent core" per its own `AGENTS.md`).
- Tagline "The agent that grows with you"; "self-improving" = closed learning loop: agent-curated memory with nudges, autonomous skill creation after complex tasks, skill self-improvement during use, FTS5 session search with LLM summarization, Honcho dialectic user modeling, `agentskills.io` compatibility (per `README.md` table).
- Tool surface: shared core tool list in `toolsets.py` (`web_search`, `web_extract`, `terminal`, `process_manage`, file tools, vision/image-gen, ~15 browser tools + `browser_exec` backend switch, `text_to_speech`, `todo_list`, `memory`, `session_search`, `clarify`, `execute_code`, `delegate_task`, `cronjob_manage`, Home Assistant, kanban, `computer_use`, `manage_connections`); 20 named toolsets; `tools/` holds ~270 files. Design invariant: "core is a narrow waist; capability lives at the edges" — new capability should be CLI+skill, service-gated tool, plugin, or MCP, not a new core tool.
- Messaging omnipresence: `plugins/platforms/` lists a2a, buzz, dingtalk, discord, email, feishu, google_chat, homeassistant, irc, line, matrix, mattermost, ntfy, photon, raft, simplex, slack, sms, teams, telegram, wecom, whatsapp (plus gateway-level signal/webhook/weixin/bluebubbles/qqbot/yuanbao/api-server support). Voice memo transcription, cross-platform continuity.
- Automation: built-in cron scheduler with delivery to any platform, plus an OpenAI-compatible `/v1/chat/completions` API server with REST cron management (v0.4.0-era docs), and `batch_runner.py` trajectory generation/compression for training next tool-calling models.
- Delegation: isolated subagents (`delegate_task`, `tools/delegate_tool*.py`, `async_delegation*.py`) plus `execute_code` RPC scripts that "collapse multi-step pipelines into zero-context-cost turns".
- Execution backends (`tools/environments/`): local, Docker, SSH, Singularity, Modal (+managed Modal), Daytona, Vercel Sandbox — serverless hibernate/wake to cost ~nothing when idle.
- Providers: registry + ABC in `providers/` with profiles as plugins under `plugins/model-providers/` (~35 entries observed: anthropic, openai-codex, gemini, xai, deepseek, qwen-oauth, bedrock, azure-foundry, vertex, ollama-cloud, openrouter, nous, copilot, zai/kimi, alibaba, huggingface, fireworks, novita, nebius, nvidia, minimax, gmi, stepfun, upstage, xiaomi, kilocode, commandcode, arcee, ai-gateway, router, custom, etc.). `hermes model` switches with no code changes; Nous Portal bundles models + tool gateway (Firecrawl search, FAL images, OpenAI TTS, cloud browser) under one subscription.
- Cost discipline: per-conversation prompt caching is "sacred"; slash commands that mutate system-prompt state default to deferred invalidation with opt-in `--now`.
- Safety/posture: approvals (human/gateway/smart/floors), file-mutation checkpoints/rollback snapshots, authz mixins, sandboxing per backend, `SECURITY.md`.
- Install/reach: `curl ... install.sh | bash` (Linux/macOS/WSL2/Termux), PowerShell installer for native Windows (bundles MinGit, uv, Python 3.11, Node, ripgrep, ffmpeg); Python `>=3.11,<3.14`; MIT license; runs on $5 VPS, GPU cluster, or serverless.
- OpenClaw lineage signals (not a fork claim — a product-positioning claim): `hermes claw migrate`, onboarding banner for `~/.openclaw/`, `COMPAT_MANIFEST.md`, code comments referencing OpenClaw PRs/issues as regression models, and the same gateway/skills/memory/cron/MCP/voice shape as OpenClaw's gateway+brain+memory+skills+heartbeat.

## What SASE is (grounded)

- "Structured Agentic Software Engineering" ("sassy"): "One developer. A team of coding agents. Tracked, reviewable, repeatable work." (README). "SASE does not replace coding agents; it makes agent-driven engineering dependable."
- Requires at least one real provider CLI installed and authenticated (Claude Code, Codex, Antigravity `agy`, Qwen Code, OpenCode, Muse Code, Grok Build); `sase doctor` is the readiness authority; autodetect never selects generic-named `muse`/`grok` binaries implicitly. Model-alias pools (`@small/@medium/@large/@xlarge`) can route across providers.
- System boundary (`docs/architecture.md`): CLI, TUI, service host, AXE/scheduler, XPrompt, workflows, gates, Patches, memory, SDD, beads, providers, required Rust core (`sase_core_rs`), integrations.
- Workspaces: numbered clones per project (`registry.json`), bare-git + GitHub workspace-provider plugins via pluggy (`sase_workspace` entry points), `#git:`/`#gh:`/`+project` refs, workspace claim guard and admission (`max_running_agents`, `%queue`, holds, `%wait`).
- Review rigor: Patches (PR-sized records with lifecycle/stitches/hooks/comments/mentors), `sase stitch` timelines, beads (git-portable issues + executable epic launch plans), artifacts + artifact refs (immutable explicit snapshots, indexed files, typed links, pager traversal).
- Reuse: XPrompts (reusable fragments, typed inputs, Jinja2, `#name`/`#!name`), YAML workflows (agent/bash/python/parallel/loop/human-checkpoint steps), prompt history/search/replay.
- Supervision: keyboard-driven TUI (Agents/Patches/Artifacts/Services tabs, command palette, live screenshots via tmux, diffs/chats/artifact panes); `sase run`, `sase agent` (list/show/kill/wait/hold/restart/drain/archive/search), LaunchApproval for agent-initiated launches, typed `LaunchPlan` admission under the `typed_launch_units` flag.
- Background: service host (systemd/launchd per-machine supervisor for daemon procs + transient oneshots; owns scheduler + mobile-gateway procs); scheduler/AXE (orchestrator + routines: hooks/waits/checks/mirror/comments/housekeeping; structured launch proposals, `%if`/`%proc` dispatch); monitors (single-turn-native replacement for provider background/wake-up: a monitor shell supervises one OS command as an agent-family member).
- Memory: core (always-loaded into managed `AGENTS.md`) + reference (on-demand) + webs (keyword strands), audited `sase memory read`, TUI memory panel, `/sase_memory_write` routing. No autonomous skill-creation loop.
- Remote: workstation-hosted mobile gateway (phone = paired client over product-shaped APIs + SSE; no generic file/shell/RPC surface; Rust `sase_gateway` + Android handoff), `sase-telegram` linked plugin, editor integrations, notifications + command-backed gates.
- Constraints: POSIX only (Linux/macOS, no Windows), Python 3.12+, `uv`, `git`, `$EDITOR`; Rust core required with no Python fallback; MIT license.

## Head-to-head

| Dimension | Hermes | SASE | Note |
|---|---|---|---|
| Product identity | Personal agent (you talk to it) | Team orchestrator (you supervise agents) | Different layers; the central non-overlap |
| Agent loop | Own ReAct-style core, subagents, RPC code execution | None of its own; drives 7 external CLIs | SASE cannot act with zero providers installed; Hermes can |
| Provider breadth | ~35 model-provider plugins, direct LLM + local + OAuth + portal | 7 coding-CLI providers, BYO-CLI, pools/tiers | Hermes wider as a model router; SASE deeper as a CLI-team router |
| Tool surface | ~60+ core tools / 20 toolsets (browser, computer-use, HA, kanban, image/TTS, cron, memory, code exec) | No core agent tools; inherits whatever the provider CLI offers | SASE deliberately has no tool waist to defend |
| Messaging presence | 16–20 platforms first-class + voice + desktop + API server | TUI + mobile client + Telegram plugin + editor; no general gateway | Largest end-user gap |
| Learning/memory | Closed loop: nudges, auto-created/improved skills, FTS5 sessions, Honcho user model | Durable core/reference/webs + prompt/chat archives, human-routed writes | Hermes remembers and generalizes; SASE records and retrieves |
| Scheduling | Cron in natural language, deliver anywhere | AXE orchestrator/routines tied to patch/agent lifecycle + LaunchApproval | Rough parity in power, different idiom (assistant reminders vs eng automation) |
| Parallelism | Isolated subagents, zero-context RPC | Numbered workspaces, swarms/families/clans/tribes, workflow fan-out, admission budgets | SASE's model is built for parallel PR-shaped work |
| Eng rigor | Checkpoints/rollback, kanban, evals, trajectories | Patches/stitches/beads/artifacts/links, review pipeline, audit trails | SASE is the reviewable-engineering system; Hermes is the doer |
| Deployment | Laptop/VPS/serverless/Docker/SSH/Modal/Daytona/Vercel; Windows+WSL+Termux | POSIX-only workstation + per-machine service host | Hermes runs where you live; SASE runs where you engineer |
| Extension | Plugins + skills + MCP catalog, compat manifest | pluggy providers (LLM/VCS/workspace/config/xprompt), XPrompts/workflows, skills | Both plugin-heavy; different waists |
| OpenClaw-likeness | High: same shape + explicit migration path | Low: shares only supervision vocabulary | Answers the prompt's "like OpenClaw" question |

Similarities worth naming (the "maybe a lot like this project" grain of truth): both supervise long-running work from a TUI; both schedule unattended work; both fan out to subagents/parallel workers; both keep durable memory plus prompt/run history; both are plugin-extensible with provider abstractions; both support remote operation (Hermes messaging gateway vs SASE mobile gateway + Telegram); both care about cost/discipline (Hermes prompt-cache sacredness vs SASE admission budgets/holds/queues).

Differences that dominate: agency location (inside vs above the agent), tool ownership (built-in universe vs inherited CLI tools), interface center (chat-everywhere vs TUI review queue), memory dynamics (self-improving vs human-routed), artifact model (sessions/skills vs patches/beads/PRs), platform span (Windows/mobile-IoT vs POSIX-workstation).

## Rating: how well SASE competes functionally with Hermes

Scale: 0 = cannot substitute on any Hermes job; 10 = full functional substitute (popularity ignored).

- Agent execution (own loop, zero-provider operation): **3/10** — by design SASE does not do this.
- Model/provider routing: **6/10** — SASE's 7-CLI + pools vs Hermes's ~35-provider direct routing.
- Tool universe (browser, computer-use, media, HA, kanban): **4/10** — inherited, not owned.
- Messaging/voice/desktop omnipresence: **3/10** — Telegram plugin + mobile client only.
- Memory + self-improvement loop: **4/10** — durable and audited, but not self-improving.
- Scheduling/automation: **8/10** — AXE + service host + monitors ≈ cron for eng purposes.
- Parallel/multi-agent supervision: **9/10** — workspaces + admission exceed Hermes delegation for team coding.
- Engineering reviewability (patches/beads/artifacts/audit): **9/10** — SASE's home turf.
- Deployment portability: **5/10** — POSIX-only vs Hermes anywhere.
- Extensibility: **7/10** — both strong; different waists.

**Overall: 6/10.** SASE is not a functional Hermes replacement (and Hermes is not a functional SASE replacement — the reverse rating would rhyme). SASE matches or beats Hermes at supervised team software engineering and scheduled eng automation, competes weakly as a personal everywhere-assistant, and does not compete at all as a zero-provider standalone agent. Within its chosen scope (dependable multi-agent engineering on top of paid CLIs) it is ~9/10; as a general Hermes substitute it is ~5–6/10, hence 6 overall.

What would move the number (functional only, no adoption claims): a bundled standalone loop (even optional) for zero-provider operation; a real multi-channel gateway (not just Telegram/mobile-client) with voice handling; browser + computer-use execution backends; an opt-in skill-learning loop over prompt/chat/artifact history; and Windows/serverless execution parity. Each is a large, deliberate scope expansion — which is itself the finding: the gap is architectural choice, not missing polish.

## Reuse note

Lead researcher: this report is an independent `__mus` input. I did not read the `__cld`/`__gem` siblings. Synthesize freely; version pins above bound my claims.
