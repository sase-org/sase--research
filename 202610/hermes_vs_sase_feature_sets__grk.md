# Hermes vs SASE: can Hermes cover SASE's feature set?

**Researcher:** grk
**Date:** 2026-10-09
**Question:** Can Hermes do everything SASE can, and should a typical user skip SASE?
**Method:** Feature-set comparison of current product surfaces. Popularity and adoption are out of scope.

## Verdict

The claim that Hermes can do everything SASE can is **false** as a feature-set claim. The two products occupy different layers. Hermes is a self-hosted personal agent runtime with its own model loop, tools, memory, messaging gateway, and multi-agent board. SASE is a coordination operating layer that launches other coding-agent CLIs, keeps work state outside any one chat, and owns completion, review, and workspace isolation for those runs.

The claim that a typical user should skip SASE is **true**. SASE's own README says that if you want a standalone agent, use a coding CLI directly. Hermes is a complete product of that kind, and it covers a much wider set of personal-assistant jobs than SASE even attempts. SASE is alpha software, POSIX-only, and assumes you already have at least one authenticated agent CLI.

SASE still has a realistic role for people other than its author: it is an **Agent Command Environment** for operators who run several coding-agent CLIs as a supervised engineering team and need durable, git-native, provider-neutral work records. That audience is smaller than "anyone who wants an agent" and larger than "only the person who wrote SASE."

## Scope and sources

**Hermes** here means [Nous Research Hermes Agent](https://github.com/NousResearch/hermes-agent) (MIT), the self-hosted agent harness, distinct from the Hermes model family. Snapshot used: checkout `1e0c7730d791f5ce855c5c78935cfea6fb1e43a9` (2026-10-08), described as `abandoned-rc.3-v0.21.7-47-g1e0c7730d7`, plus the live docs index at [hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs/) and [docs/llms.txt](https://hermes-agent.nousresearch.com/docs/llms.txt).

**SASE** here means Structured Agentic Software Engineering, package version `0.17.1` in this tree, documented at [sase.sh](https://sase.sh/) and in `docs/` of the sase-org/sase repo. Status in the README: alpha; POSIX only (Linux and macOS); Windows unsupported.

A prior comparison exists as `research:202604/sase_vs_hermes_agent.md` (Hermes at `456955c2`, 2026-04-29). That note is six months old. Hermes has since shipped kanban, persistent `/goal` loops with quality gates, PR completion contracts, a native desktop app, native Windows, Android/Termux, bot mode, and a much larger messaging surface. SASE has since shipped the goals ledger, ToolRuns, command-backed gates, monitors, instruction bundles, sudo requests, remote dispatch, Grok Build and Muse Code providers, and a thicker TUI/artifact model. This report re-derives conclusions from current docs and does not inherit the April verdicts.

Library check for cited papers: 2 of 5 lookup candidates were already in the Bob library (0 finished). Hassan et al. 2025 is in-library, queued (modern capture 2026-10-07). Vaziri et al. 2024 (PDL) is in-library, started (legacy). Product docs for sase.sh, Hermes docs, and the Hermes GitHub repo were not in the library.

## Category mismatch

This is the load-bearing fact. Almost every later row in the comparison follows from it.

SASE's README states the product in one sentence: it turns Claude Code, Codex, Antigravity, Qwen Code, OpenCode, Muse Code, and Grok Build into a coordinated engineering team. It does not replace those agents. Getting Started repeats the same framing: SASE is a coordination layer that sits **above** coding-agent CLIs. Architecture docs describe a Python host plus a required Rust core that keep work state in files and stores so agents can be launched, tracked, resumed, reviewed, retried, and handed off without relying on one session's context window.

Hermes's README and docs describe a different object: an open-source autonomous agent with a closed learning loop, persistent memory, a messaging gateway, and its own tool registry. Official docs place it in the same category as Claude Code, Codex, and OpenClaw — "autonomous coding and task-execution agents that use tool calling to interact with your system." Hermes **is** the agent. It talks to model APIs (Nous Portal, OpenRouter, Anthropic, OpenAI, Google, local endpoints, and others), owns context compression and prompt caching, and executes tools in-process.

Hermes can import a Claude Code or Codex **setup** (`hermes import-agent`) — instructions, allowlists, MCP servers, skills, memories — into Hermes. That is a migration path **off** those CLIs and **onto** Hermes. SASE's provider layer is the inverse: it keeps those CLIs as execution engines and wraps them with a shared launch, workspace, commit, and review path.

A user who wants "an agent that lives on my VPS and talks to me on Telegram" is shopping for Hermes. A user who wants "Claude Code, Codex, and Grok running in parallel isolated clones, with host-owned commits and a TUI of every run" is shopping for SASE. Treating those as the same shopping trip is how the original claim overreaches.

## Feature inventory

### Hermes, current surface

From the official docs index, README, and feature pages:

| Area | What ships |
| --- | --- |
| Identity | Self-improving personal agent; MIT; CLI, Ink TUI, Electron desktop, web dashboard, ACP for VS Code/Zed/JetBrains, OpenAI-compatible API server and proxy |
| Models | Provider-agnostic: Nous Portal, OpenRouter, OpenAI, Anthropic, Google, DeepSeek, xAI, NVIDIA NIM, Hugging Face, Ollama, LM Studio, Bedrock, Vertex, Azure Foundry, MiniMax, custom OpenAI-compatible endpoints; credential pools; fallbacks; Mixture of Agents |
| Learning loop | Autonomous skill creation after complex tasks; skill self-improvement; curator; agentskills.io Skills Hub; MEMORY.md / USER.md / SOUL.md; FTS5 session search with LLM summarization; optional Honcho and other memory providers |
| Execution | Built-in tools (web, terminal, files, browser, vision, image gen, TTS, memory, delegation, cron, kanban, …); MCP; computer use; code-execution RPC; seven terminal backends (local, Docker, SSH, Singularity, Modal, Daytona, Vercel Sandbox) |
| Parallel work | `delegate_task` isolated children; `hermes -w` and `/worktree` git worktrees; kanban board with named profiles, dispatcher, dependencies, review, PR completion contracts |
| Continuity | `/goal` Ralph loop with completion contracts, quality gates, and turn budget; session resume; heartbeats; `/loop`; checkpoints/`/rollback` (opt-in) |
| Automation | Gateway-hosted cron with natural-language schedules, skill attachment, platform delivery, no-agent script jobs, webhooks, preflight validation |
| Messaging | 21+ platforms (Telegram, Discord, Slack, WhatsApp, Signal, iMessage, SMS, email, Matrix, Teams, and others) from one gateway |
| Safety | Dangerous-command approval modes, gateway pairing/allowlists, managed scope, credential vault, network egress isolation |
| Platforms | Linux, macOS, WSL2, native Windows, Android via Termux |
| Research extras | Batch trajectory generation and compression for training tool-calling models |

Hermes kanban is the closest thing in this product to SASE's engineering control plane. It is a durable SQLite task board (`~/.hermes/kanban.db`) with statuses, parent/child links, comments, attachments, named-profile workers as full OS processes, worktree or directory workspaces, a gateway-embedded dispatcher, human-in-the-loop review, and optional GitHub PR completion contracts that refuse `kanban_complete` until required checks pass. Official docs contrast it with `delegate_task`: delegation is an RPC fork/join; kanban is a work queue whose handoffs survive restarts.

Hermes `/goal` is a different object from SASE Goals. It is a standing objective inside one session. After each turn a judge model decides `done` / `continue` / `blocked` / `wait`, with optional shell quality gates that must exit 0 before the judge can mark done. Default budget is 20 continuation turns. Docs explicitly say `/goal` never creates kanban cards.

### SASE, current surface

From README, architecture, CLI index, and subsystem guides:

| Area | What ships |
| --- | --- |
| Identity | Coordination layer above coding-agent CLIs; Python host + required `sase_core_rs`; MIT; CLI + sase's TUI (ACE) + service host |
| Providers | Bundled LLM providers: Claude Code, Codex, Antigravity (`agy`), Qwen Code, OpenCode, Muse Code, Grok Build; pluggy plugins for more; VCS and workspace plugins (bare git, GitHub) |
| Work units | **Patches** (PR-sized review records with stitches, hooks, comments, mentors, deltas); **Beads** (git-native event-sourced issues: plan/epic/phase/task, deps, `sase bead work`); **Goals** (person-owned outcome ledger); **SDD** (prompts, tales, epics, research sidecars) |
| Agent contract | Single-turn agents; host-owned `/sase_final` + `builtin@commit`; monitors for long commands; command-backed **gates** (questions, plans, launch approval, sudo) that persist without holding a provider process |
| Isolation | Numbered workspace clones per agent, atomic claims, Git alternates, linked repos and SDD sidecars, `%dispatch` remote machines |
| Launch language | Macros (`#name`) with typed inputs; YAML workflows (agent/bash/python/parallel/loop/HITL); directives (`%wait`, `%queue`, `%hold`, `%if`, `%proc`, swarm/repeat/alternatives) |
| Control plane | TUI Agents / Artifacts / Services; notifications; pager; prompt history and stash; agent search; holds; tribes/hoods/clans; instruction bundle render/verify |
| Automation | Service host + AXE scheduler (hooks, mentors, workflows, comments, cleanup, digests); named tools and ToolRuns with admission, receipts, triage |
| Memory | Author-curated core/reference notes and memory webs; audited `sase memory read`; TUI Memory panel; history |
| Reach | Telegram plugin as a control surface over the same notification/gate store; mobile gateway; Neovim/Macro LSP; `sase-listen` command plugin |
| Platforms | Linux and macOS only; alpha |

SASE's distinctive bet, stated in acknowledgements and the (draft) orchestration post: the bottleneck is coordination — isolated workspaces, tracked PR-sized work, reusable prompts, durable plans, a TUI instead of tmux tabs, and a scheduler instead of babysitting sessions. The name and ACE/AEE split are borrowed from Hassan et al., *Agentic Software Engineering* (arXiv:2509.06216; already in library, queued). YAML workflows are influenced by PDL (arXiv:2410.19135; already in library, started).

## Capability matrix

Legend: **native** = first-class product feature; **approx** = a user can assemble a similar job from other primitives; **absent** = not in the current feature set.

| Job / capability | Hermes | SASE |
| --- | --- | --- |
| Be the coding/task agent (own tool loop) | native | absent (wraps other CLIs) |
| Wrap Claude Code / Codex / Grok / … as workers | approx (skills, import, optional Codex app-server) | native |
| Switch models/providers under one runtime | native | native at launch (each worker still uses its CLI) |
| Isolated parallel checkouts | native (worktrees, `-w`, kanban workspaces) | native (numbered clones + claims) |
| Git-native issue DAG that clones with the repo | absent (kanban is `~/.hermes`) | native (beads events in sidecar/repo) |
| PR-sized review object with lifecycle, comments, mentors | approx (kanban review + PR contracts) | native (Patches + mentors) |
| Host-owned commits (agent cannot git-commit) | absent | native (`/sase_final` + stitch) |
| Durable human decision that frees the runner | approx (approvals, clarify, kanban block) | native (gates; processless pending turn) |
| Single-turn agent contract + monitor handoff | absent (multi-turn session is the product) | native |
| Typed reusable prompts / YAML HITL workflows | approx (skills, hooks, cron, execute_code) | native (macros + workflow spec) |
| Person-owned outcome ledger (human settle only) | absent (`/goal` is a session loop) | native (Goals) |
| Always-on messaging personal assistant | native (21+ platforms) | approx (Telegram plugin over notifications) |
| Cron with delivery to chat | native | approx (AXE jobs; Telegram outbound) |
| Persistent personal memory + session search | native | approx (authored memory webs + chat search) |
| Agent-written self-improving skills | native | absent (generated skills are static, VCS-authored) |
| MCP / ACP | native | absent as host protocol |
| Desktop app / Windows / Android | native | absent |
| Browser, voice, image gen, computer use | native | absent in the host (inherited from worker CLI if it has them) |
| Instruction-load verification | absent | native (`sase instructions verify`) |
| Recorded named tool runs, receipts, triage | absent | native (ToolRuns) |
| Remote enrolled machines, `%dispatch` | approx (SSH/Docker/Modal backends) | native (machine enrollment + attention) |
| Trajectory/RL batch generation | native | absent |
| TUI as operations console over many heterogeneous runs | approx (chat TUI + dashboard + kanban) | native (ACE Agents/Artifacts/Services) |

"Approx" rows are where the original claim is most tempting. They are also where the products feel similar in a demo and diverge in the durable record.

## Where Hermes can cover a SASE-shaped job

These are the honest overlaps. A determined Hermes user can get a large fraction of the *day-to-day sensation* of SASE without installing SASE.

**Parallel coding in isolation.** `hermes -w`, `/worktree new`, and kanban `worktree` workspaces give each agent its own branch and checkout. SASE's numbered clones with Git alternates are a stricter isolation model (full workspace claim, linked-repo materialization, rescue bundles), but worktrees are enough for many parallel experiments.

**Multi-agent decomposition.** `delegate_task` covers short fork/join subtasks. Kanban covers durable queues, named roles, retries, human comments, and review. `sase bead work` launching one agent per epic phase plus a land agent is the SASE version of that pipeline. A Hermes-only shop can run "decompose → implement in worktrees → review → PR" on the kanban board.

**Scheduled unattended work.** Hermes cron is richer on the delivery side (natural language, platform targets, skill attachment, no-agent script jobs, webhook fires, preflight). SASE AXE is richer on engineering housekeeping (mentors, Patch hooks, disk pressure, bead sync, workflow checks). For "every morning summarize X and send it to Telegram," Hermes wins on features. For "when a Patch lands, run mentors and keep the TUI inbox honest," SASE wins on features.

**Goals as "keep going until done."** Hermes `/goal` with quality gates is a strong Ralph loop. SASE Goals are a person-owned ledger agents may cite (`@goal:id`) and may not settle. Same English word, different types. Hermes covers the "don't stop until tests pass" job. SASE covers the "this outcome exists across runs and only a human closes it" job.

**Messaging control.** Hermes's gateway *is* the agent on Telegram/Discord/Slack/WhatsApp/…. SASE's Telegram plugin is a control surface for an already-running SASE host: notifications, plan approvals, launches, artifact review. If the user job is "talk to my agent from my phone," Hermes has the feature. If the user job is "approve a SASE plan gate from my phone," SASE has the feature.

**Memory.** Hermes remembers the user across sessions by design. SASE injects authored, audited memory into worker CLIs. Hermes covers personal continuity. SASE covers reproducible, reviewable project instruction.

**Provider choice.** Both are model-agnostic in different ways. Hermes swaps the model under one harness. SASE swaps the entire harness (Claude Code vs Codex vs Grok) under one coordinator. That difference matters when the user believes Claude Code's coding tools, compaction, and permissions are the product, and wants them as workers rather than as a source of skills to import.

## SASE capabilities Hermes does not currently have

These are the rows that keep the "Hermes can do everything SASE can" claim from being true.

### 1. Provider-neutral host over other coding CLIs

SASE's LLM providers are thin subprocess wrappers. They inherit the host CLI's tools, safety harness, compaction, and updates. Commit finalization is host-owned and uniform across providers. Usage-limit auto-disable, `sase agent drain` off a hard-disabled provider, instruction-bundle verification, and per-prompt `%model:` routing are all consequences of that host position.

Hermes can *call* other agents as skills or import their config. It does not launch Claude Code as a first-class worker in a claimed SASE workspace with a shared finalizer. `hermes import-agent` is designed to replace those CLIs.

A user who wants Opus-inside-Claude-Code for one task and GPT-inside-Codex for another, with the same Patch/bead/commit pipeline around both, is using a SASE feature.

### 2. Host-owned completion and stitches

SASE agents are instructed not to create commits. `/sase_final` declares dirty repos and messages; `builtin@commit` runs `sase stitch create`. Stitches are the tracked commit/proposal/PR timeline. Patches accumulate stitches, deltas, hooks, comments, and mentors.

Hermes agents use the terminal tool and git like a person. Checkpoints/`/rollback` snapshot the filesystem in a shadow repo; they do not replace a host-owned VCS workflow. Kanban PR completion contracts can refuse to mark a card done until GitHub required checks pass, which is a real quality gate, and still leaves commit authorship with the worker.

Host-owned completion is a policy feature: the human/host remains the only git writer on the agent path. Hermes has no equivalent policy object.

### 3. Git-portable beads and SDD

Beads are event-sourced issues in the project's SDD store (sidecar or in-tree). They clone, merge, and conflict like code. Epic approval creates a DAG; `sase bead work` launches phase agents. Task beads have typed catalogs, corroboration (`+1`), snooze, attachments, and audited reads.

Hermes kanban lives under `~/.hermes/`. Boards can bind a project directory, and worktrees are preserved on completion, but the board itself is host-local SQLite. A teammate who clones the git repo does not clone the kanban DAG. That is a feature-set gap for shared engineering state.

SDD (prompt archive, tales, epics, research sidecars, plan decisions, memory-consent) is the rest of that git-native intent trail. Hermes sessions and skills persist; they are not a spec-driven development store linked to commit footers.

### 4. Single-turn contract, gates, and monitors

SASE's mechanical contract: one provider turn, then the host continues via a successor, a monitor, or a gate. A pending question or plan approval is a gate turn with no LLM process and no runner slot. The decision is a write-once receipt. Monitors exist because provider-native background wake-ups die when the SASE turn ends.

Hermes's product is the long-lived session: `/goal` continuation, heartbeats, `/loop`, gateway FIFO, kanban workers that run until `kanban_complete`. That is a valid and popular agent shape. It is a different feature. You cannot get "the runner is free while a human thinks" from a multi-turn Hermes session without building SASE-like gate machinery.

### 5. Operations console over heterogeneous runs

sase's TUI is an operations surface: live agents, retry chains, diffs, chats, artifacts, Patches, beads, stitches, files, notifications, service procs, prompt stash. Agent search uses a Boolean catalog over historical runs. This matches the paper's Agent Command Environment: the human triages work products, not chat tabs.

Hermes's Ink TUI, desktop app, and dashboard are excellent **agent** surfaces (chat, sessions, cron, kanban, config). They are not a control tower over Claude Code + Codex + Grok runs in numbered clones.

### 6. ToolRuns, instruction verification, mentors, remote attention

These are smaller individually and jointly they describe an engineering control plane:

- **ToolRuns:** project-declared commands recorded with fingerprints, duration class, receipts, and triage. Guarded recipes refuse raw agent `just check`.
- **Instruction bundles:** render intended context; `sase instructions verify` compares what providers actually loaded.
- **Mentors:** scheduled review agents attached to Patches, structured comments, apply path from the TUI.
- **Remote dispatch:** enrolled machines, `%dispatch:alias`, remote attention inventory in the TUI.
- **Holds, clans, tribes, hoods:** admission and grouping for a fleet of workers.
- **Macros + LSP:** typed, composable prompt programming with editor completion.

Hermes has hooks, `/review`, cron, SSH/Docker backends, and profiles. It does not have this bundle as a coherent host protocol.

## Hermes capabilities SASE does not currently have

The reverse gap is larger in raw feature count, which is why "skip SASE" is the right default for most people.

Hermes is a personal OS for an always-on agent: 21+ messaging platforms, voice and wake word, browser and computer use, image generation, TTS, credential vault, Google Workspace, Spotify, Home Assistant, bot mode, skins, pets, language packs, Windows and Android, local models, MCP/ACP, OpenAI-compatible proxy so *other* apps can use Hermes's OAuth, trajectory export for training, and a closed learning loop that writes skills from experience.

SASE would have to become a different product to grow those features. Several of them conflict with SASE's own invariants (authored memory, static generated skills, single-turn agents, wrapping CLIs rather than owning the tool loop).

SASE Telegram is a plugin over notifications. Hermes Telegram is the agent. Equating them by the word "Telegram" is a naming collision.

## Evaluation of the two claims

### Claim A: "Hermes can do everything SASE can"

**Refuted.**

Even after giving Hermes every generous approximation (kanban ≈ beads+epics, worktrees ≈ workspaces, cron ≈ AXE, `/goal` ≈ keep-going, `/review` ≈ mentors, import-agent ≈ using Claude Code), the following SASE features remain missing as product objects:

1. First-class hosting of other coding-agent CLIs with a shared finalizer.
2. Host-owned git writes and Patch/stitch review records.
3. Git-portable bead/SDD state.
4. Single-turn agents with processless gates and monitors.
5. An operations TUI over a heterogeneous worker fleet.
6. ToolRuns, instruction verification, and the rest of the engineering control-plane bundle.

A user can *get work done* in Hermes that a SASE user would get done in SASE. That is job substitution, not feature-set equality. The original claim is the latter.

The April 2026 comparison said Hermes "treats work as conversation, not as typed objects in a repo." That sentence is now too strong: kanban tasks, PR contracts, and `/goal` completion contracts are typed objects. They still live in the Hermes home directory and inside Hermes's own runtime. They do not make Hermes a SASE-shaped host.

### Claim B: "The smart move for just about any user except [SASE's author] is to skip SASE"

**Supported**, with a bounded exception in the next section.

Reasons that follow from the feature sets (not from popularity):

1. **SASE requires another agent product.** Hermes is sufficient to start chatting, coding, scheduling, and messaging. SASE's getting-started path is: install SASE, install and authenticate Claude Code or Codex or another CLI, then launch. The user already had an agent before SASE added value.
2. **SASE's README tells standalone-agent users to leave.** That is an accurate description of the feature set, not marketing humility.
3. **Hermes covers the common jobs more directly.** Personal memory, always-on chat, cron-to-Telegram, browser, voice, Windows, a desktop app, self-written skills — these are majority-user jobs. SASE either lacks them or offers a thinner plugin.
4. **SASE's unique features have a high conceptual tax.** Beads, Patches, stitches, gates, macros, workspaces, providers, ToolRuns, instruction bundles, and single-turn mechanics are a professional operating system. They pay off when you already run a fleet. They are ballast if you wanted a chatbot that can also patch files.
5. **Platform and maturity.** Alpha + POSIX-only excludes Windows-native users and anyone who wants a polished installer/desktop path. Hermes ships those surfaces.
6. **Lock-in direction.** Choosing Hermes means living in one harness that can talk to many models. Choosing SASE means living in a coordinator that can talk to many harnesses. Most people need the first. The second is a specialist need.

"Skip SASE" here means "do not take on SASE as your agent product." It does not mean SASE's unique features are fake.

## SASE's realistic role (for many users, not only the author)

SASE has a coherent niche that is implied by its feature set and by the paper whose name it took.

Hassan et al. describe Structured Agentic Software Engineering as closing a speed-vs-trust gap with durable artifacts: an Agent Command Environment where humans triage evidence, and an Agent Execution Environment where agents work. SASE's TUI (historically ACE) and scheduler (AXE) are an implementation of that split. The product is for people whose output is reviewed patches in real repositories, produced by several agents, possibly from several vendors, over days, with an audit trail.

**Who that is, in feature terms:**

- Operators who already run **two or more coding-agent CLIs** (or want the option to swap them) and need one cockpit.
- Teams that want **work state in git** (beads, plans, research, Patch records) so a clone is enough to see what the agents were doing.
- Teams that want **the host to be the only git writer** on the agent path.
- People supervising **parallel isolated workspaces** at a cadence where tmux tabs and mental bookkeeping fail (the Boris Cherny parallel-checkout pattern, automated).
- People who need **durable human pauses** (plan review, questions, sudo, launch approval) without burning a model session or a runner slot.
- People who care that **instructions actually loaded** in the worker CLI, that **named checks ran** and left receipts, and that **mentor comments** attach to a Patch rather than a chat scrollback.

That is a real job. It is the job of an engineering control plane. It is not the job of a personal agent.

How large is "many"? Feature-set analysis cannot count users, and this report was told not to use adoption as evidence. The *existence* of the role does not depend on SASE winning a popularity contest. Every organization that standardizes on "agents may write code, humans and policy own git and review" needs *some* ACE. Today that ACE can be:

- homegrown tmux + scripts (Boris's method),
- a single harness's own board (Hermes kanban, Claude Code channels, Codex cloud),
- or a harness-neutral coordinator (SASE).

SASE's wedge among those options is **harness neutrality plus git-native durable records plus host-owned completion**. Hermes kanban is the strongest in-harness alternative, and it is now good enough that a Hermes-standardized team has a credible reason to stay inside Hermes. SASE's remaining reason to exist for that team is the wish to keep Claude Code and Codex as workers rather than as import sources.

If SASE disappeared, those users would not be feature-complete in Hermes. They would give up provider-as-worker, host-owned git, git-portable issues, and the single-turn/gate model. Many of them would accept that trade. Some would not. The ones who would not are SASE's realistic market.

**What SASE should not try to be**, if this role is the point: a Telegram companion, a learning-loop personal OS, a Windows desktop agent, or a replacement for Claude Code's inner loop. Those are Hermes (or Claude Code) features. Competing there dilutes the ACE.

## Recommendation

1. **Do not argue that Hermes is a superset of SASE.** The feature sets refute it. Hermes is a better *agent*. SASE is a coordinator of *agents*.
2. **Do tell a typical user to skip SASE.** If they want one process that remembers them, talks on their phone, writes skills, and can also edit a repo, Hermes matches the feature set. SASE will feel like an operating system they did not ask to administer. Use Hermes, or use Claude Code/Codex directly if the work is almost entirely in one repo and one harness.
3. **Keep SASE aimed at the ACE niche.** Market and design it as the control plane for multi-CLI, multi-workspace, host-owned, git-native agentic engineering. That role is valid for many people who run agents as a team: small engineering orgs, power users with several subscriptions, and anyone who refuses to collapse "which model/harness runs" into "which coordinator I installed."
4. **Treat Hermes kanban as the competitive baseline inside that niche**, not Telegram bots or pets. If SASE cannot stay clearly better at heterogeneous workers, host-owned VCS, and repo-portable work graphs, the niche collapses into "use Hermes and standardize on it."
5. **Do not copy Hermes's learning loop, dialectic memory, or self-editing skills into SASE core.** Those features fight SASE's reproducibility story (authored memory, VCS-backed skills, audited reads). Steal cautiously from Hermes where the ACE is weak: session search, webhook ingress, MCP as a *control-plane* API for SASE operations, richer mobile delivery of gates. Those are coordinator features. Voice memos and SOUL.md are not.

**Bottom line for the original case.** You can honestly say most people should run Hermes (or a single coding CLI) and ignore SASE. You cannot honestly say Hermes already has SASE's feature set. The true sentence is: *Hermes dominates the personal-agent feature set; SASE is a specialist control plane whose features only pay off once you are already running coding agents as a fleet.*

## Sources

Primary:

- SASE README, `docs/architecture.md`, `docs/cli.md`, `docs/llms.md`, `docs/plugins.md`, `docs/beads.md`, `docs/change_spec.md`, `docs/commit_workflows.md`, `docs/goals.md`, `docs/tool.md`, `docs/macros.md`, `docs/workflow_spec.md`, `docs/monitors.md`, `docs/notifications.md`, `docs/workspace.md`, `docs/sdd.md`, `docs/instruction_bundles.md`, `docs/mentors.md`, `docs/remote_dispatch.md`, `docs/acknowledgements.md`, `docs/getting_started.md`, `docs/blog/posts/why-coding-agents-need-orchestration.md`, `docs/blog/posts/telegram-mobile-agents.md` (sase 0.17.1 tree).
- Hermes Agent README and docs tree in `NousResearch/hermes-agent@1e0c7730d7` (2026-10-08); [docs/llms.txt](https://hermes-agent.nousresearch.com/docs/llms.txt); feature pages for tools, kanban, goals, cron, delegation, git worktrees, checkpoints, import-from-other-agents, overview.
- [sase.sh](https://sase.sh/) product copy (coordination layer; ACE TUI; beads/patches).

Background (re-verified, not copied as conclusions):

- `research:202604/sase_vs_hermes_agent.md` (April 2026 snapshot; kanban/goals/desktop/Windows were absent or immature; SASE Goals/ToolRuns/gates were absent).

Papers named by SASE itself:

- Ahmed E. Hassan et al., *Agentic Software Engineering: Foundational Pillars and a Research Roadmap*, arXiv:2509.06216. Already in library (queued).
- Mandana Vaziri et al., *PDL: A Declarative Prompt Programming Language*, arXiv:2410.19135. Already in library (started, legacy).

## Limitations

- This is a docs-and-source feature comparison. I did not run Hermes end-to-end or benchmark coding quality of Hermes-the-harness against Claude Code-under-SASE.
- Hermes docs warn that the hub skill is not the complete feature list; `llms.txt` plus the checkout were used to reduce false negatives, and some subsystems (for example every messaging adapter) were inventoried at index level only.
- SASE is moving quickly (alpha). Features behind flags (`typed_launch_units`, `agent_sudo_requests`) are counted when they are documented product surface, and called out as beta where the docs do.
- Third-party blog comparisons of Hermes vs Claude Code were used only as pointers to official docs, never as evidence of capability.

Library check: 2 of 5 cited-URL candidates already in the Bob library (0 finished).
