# Pi vs SASE: a pi user's map, and what SASE should steal

**Researcher:** grk
**Date:** 2026-10-11
**Question:** How does [Pi](https://github.com/earendil-works/pi) compare to SASE, and what should SASE implement to become appealing to someone who already uses Pi?
**Method:** Independent product comparison from current source, docs, and public product posts. Peer swarm reports from this run were not read.

## Verdict

Pi and SASE are not substitutes. Pi is a **minimal, in-process coding-agent harness**. SASE is a **coordination operating layer** that launches other coding-agent CLIs, keeps work state outside any one chat, and owns landing.

A typical Pi user should keep using Pi as their daily driver. They should add SASE only if they want a team of isolated, reviewable, git-native agent runs that outlive a conversation. SASE should not try to become another Pi. It should become the control tower a Pi user can sit *on top of* Pi.

The conversion problem is concrete. SASE has no Pi provider. Its default path is a single-turn subprocess against Claude Code, Codex, Antigravity, Qwen, OpenCode, Muse, or Grok. A Pi user lives in a multi-turn session tree with steering, `/reload`, packages, and a cost footer. Asking that person to give those up for beads, macros, and host-owned finalizers is a non-starter. The ranked list at the end is ordered by that conversion, not by what would make SASE more like Pi for its current author.

Pi Durable, shipped experimental with Pi 1.0, is the piece of Pi that actually competes with SASE's thesis. It is a crash-surviving, multi-conversation, multi-surface harness with atomic commits, task graphs, and documents next to transcripts. If Durable becomes the way Pi users run long-lived agents, SASE's remaining unique value is provider-neutral workspace isolation, git landing, and a project operating system. That is still a real product. It is a smaller one than "the missing OS for coding agents" unless SASE can host Pi rather than replace it.

## Scope and sources

**Pi** here means the MIT-licensed Earendil Works monorepo at [github.com/earendil-works/pi](https://github.com/earendil-works/pi), site [pi.dev](https://pi.dev). Snapshot used: checkout `96abe9a5ad45005cae34ed1c52d42f71fc88bedc` (2026-10-11, `feat(coding-agent): use pi.dev configuration schemas (#10751)`), tag `v1.1.0` (2026-10-07). Packages in scope: `pi-coding-agent` (CLI/TUI), `pi-ai`, `pi-agent-core`, `pi-tui`, `pi-durable` (experimental), `chord`, `pi-env`, `codemode`, `mcp`, plus docs under `packages/coding-agent/docs/`. Related but out of repo: [pi-chat](https://github.com/earendil-works/pi-chat), [OpenClaw](https://github.com/OpenClaw/OpenClaw) as an SDK host.

**SASE** here means Structured Agentic Software Engineering, package `0.17.1` in this tree, documented at [sase.sh](https://sase.sh/) and in `docs/`. Status in the README: alpha; POSIX only; Windows unsupported. SASE wraps provider CLIs; it does not ship its own model loop.

Public product posts used as secondary sources: Earendil, *[Pi 1.0](https://earendil.com/posts/pi-1-0/)* (2026-10-01); Earendil, *[Pi Durable](https://earendil.com/posts/pi-durable/)* (2026-10-01). GitHub and npm stats were read live on 2026-10-11.

This report does not inherit conclusions from prior SASE-vs-harness research (`can_hermes_replace_sase`, `openai_harness_engineering_vs_sase`, `omnigent_meta_harness_lessons_for_sase`). Those products occupy nearby categories; the claims below were re-derived from Pi's current tree.

## Category mismatch

This is the load-bearing fact. Almost every later row follows from it.

Pi's README states the product in one sentence: "a minimal, extensible agent harness that you can make your own." It talks to model APIs through `@earendil-works/pi-ai`, owns the agent loop in `@earendil-works/pi-agent-core`, renders a conversation TUI, and executes `read` / `bash` / `edit` / `write` in-process. Customization is TypeScript extensions, Agent Skills, Markdown prompt templates, themes, and npm/git packages. Sub-agents, plan mode, permission popups, to-dos, and background bash are deliberately *not* in core; they are examples or packages. Pi **is** the agent.

SASE's README states a different object: it turns Claude Code, Codex, Antigravity, Qwen Code, OpenCode, Muse Code, and Grok Build into a coordinated engineering team. Getting Started repeats the same framing. Architecture docs describe a Python host plus a required Rust core that keep work state in files and stores so agents can be launched, tracked, resumed, reviewed, retried, and handed off without relying on one session's context window. SASE **wraps** agents.

Pi's four interfaces (interactive, print, JSON, RPC) and the TypeScript SDK all share one agent and one session tree. SASE's TUI, CLI, Telegram, Neovim, and AXE share one launch/admission/completion path around *other* CLIs. `sase tmux-agent` can already open an unmanaged interactive CLI in tmux; those windows "do not appear in `sase agent list`." That is the current closest thing to "use Pi from SASE," and it is explicitly not a SASE agent.

A user who wants "a yellow terminal, four tools, `/model`, `/tree`, and packages I can write in an afternoon" is shopping for Pi. A user who wants "three isolated clones, host-owned commits, beads, and a TUI of every run" is shopping for SASE. Treating those as the same shopping trip is how a naive comparison overreaches.

Pi Durable blurs the line. Mario Zechner and Earendil describe it as the harness for long-running, multi-surface, crash-surviving agents, *without replacing* the coding-agent CLI. That is SASE's original thesis, rebuilt inside TypeScript with storage-first commits. The rest of this report treats Durable as Pi's operating-layer bet, not as the daily-driver `pi` binary.

## Product snapshot

### Pi, current surface

| Field | Value (2026-10-11) |
|---|---|
| Org / authors | Earendil Works; originally Mario Zechner (`badlogic`, libGDX). Moved from `badlogic/pi-mono` / `@mariozechner` to `earendil-works` / `@earendil-works` in May 2026 (v0.74.0). Armin Ronacher's Earendil acquired the project in April 2026. |
| License | MIT |
| Language | TypeScript (Node >= 22.19); native bits in `pi-tui` and a Rust `pi-env` daemon |
| Install | `curl -fsSL https://pi.dev/install.sh \| sh`; Windows PowerShell installer; `npm i -g --ignore-scripts @earendil-works/pi-coding-agent`; Nix `github:earendil-works/pi/stable` |
| Version | `pi-coding-agent` 1.1.0; monorepo HEAD `96abe9a5a`; 6,843 commits; 493 in the last 30 days |
| GitHub | **114,254** stars, **14,537** forks, 346 watchers |
| npm | **4.19M** downloads last week, **16.0M** last month for `@earendil-works/pi-coding-agent` |
| Claimed users | "Hundreds of thousands of people around the world use Pi every week" (Pi 1.0 post) |
| Platforms | Windows, macOS, Linux, Termux; ARM64 and x86-64 |
| Default tools | `read`, `bash`, `edit`, `write` (PowerShell on Windows). `grep` / `find` / `ls` exist but are off by default. `codemode` and `tool_search` are built-in extensions, off until enabled. |
| Default system preamble | One sentence: "You are an expert coding assistant operating inside pi…" Skills are advertised by name/description; full `SKILL.md` loads on demand. |
| Providers | 30+ in `pi-ai`, including Anthropic, OpenAI, Azure, Codex OAuth, Google, Vertex, Bedrock, xAI, OpenRouter, Groq, Cerebras, Mistral, DeepSeek, Hugging Face, GitHub Copilot, Ollama-class OpenAI-compatible endpoints, plus classifier and image catalogs |
| Session model | JSONL tree (`id` / `parentId`), currently v3. Compaction and branch summaries insert entries; originals stay on disk. |
| Extensibility | In-process TS extensions (`ExtensionAPI`), Agent Skills spec, Markdown `/` templates, JSON themes, `pi install npm:…` / `git:…` packages, MCP, virtual models |
| Automation | `--print`, `--mode json`, `--mode rpc`, in-process SDK. OpenClaw is the cited real-world SDK host. |
| Isolation | None in core. Project trust gates loading of `.pi` resources. Containerization docs cover Docker, OpenShell, and the Gondolin host-plus-micro-VM pattern. |
| Philosophy | "Primitives, not features." Core stays small; wait until a pattern proves itself, then adopt it (Codemode/MCP in 1.0 is the canonical example). Contribution gate auto-closes new-contributor issues/PRs. |

The coding-agent package is large in absolute terms (about 744 TypeScript files under `packages/coding-agent`, 305 of them in `src/`) but the *product* surface stays small: four tools, a structured system prompt with independently patchable sections, a session tree, and an extension API that can register tools, commands, shortcuts, flags, providers, virtual models, MCP servers, renderers, and lifecycle hooks.

Pi 1.0 (2026-10-01) added Codemode, virtual models, deferred tool loading, Anthropic cache warming, mid-conversation system-prompt/tool patches, a new theme, and fullscreen TUI by default. 1.1.0 added OSC 7501 program-status reporting, `+name`/`-name` tool selection, Haiku 5.5, and classifier/image work through Codemode.

### SASE, current surface

| Field | Value (2026-10-11) |
|---|---|
| Org | sase-org; Python host + required `sase-core` Rust backend |
| License | MIT |
| Install | `uv tool install sase`; needs Python 3.12+, `uv`, git, and at least one authenticated provider CLI |
| Version | 0.17.1 (released 2026-08-29); tree still moving (pushed 2026-10-11) |
| GitHub | **5** stars, **1** fork |
| PyPI | 58 downloads last week, 344 last month |
| Status | Alpha. POSIX only. Windows unsupported. |
| Agent identity | Provider CLI adapters (Claude, Codex, agy, Qwen, OpenCode, Muse, Grok). Fakey for tests. **No Pi adapter.** |
| Loop | Single-turn provider contract. Continuation is mechanical (handoff, monitor, gate, session), never a promise to resume inside one process. |
| Isolation | Numbered workspace clones claimed atomically; linked/sidecar repos; host-owned hidden clones for machine writes |
| Work records | Beads, Goals, Patches, stitches, artifacts, ToolRuns, receipts, instruction-bundle manifests |
| TUI | Control tower: Agents, Artifacts, Services. Conversation is a pane on a run, not the product. |
| Extensibility | Python entry-point plugins (VCS, workspace, LLM, macros, commands, artifact refs, file hooks, dispatch, finalizers, task types, pager history) |
| Human control | Command-backed gates, sudo requests, LaunchApproval, holds, `%wait` / `%queue` |
| Background | AXE scheduler, service host, monitors, named procs |
| Completion | Host-owned. Agents declare; `builtin@commit` runs `sase stitch create`. |

SASE's README is explicit: if you want a standalone agent, use those CLIs directly. That sentence is the correct answer to "should a Pi user switch?" unless SASE can host Pi.

## Comparison by layer

### 1. Who owns the model loop

Pi owns it. A prompt becomes a session entry, the active branch is projected into provider messages, tools run, results append, and the loop continues until the run settles. Steering (`Enter` while working) lands after the current assistant turn. Follow-up (`Alt+Enter`) waits until pending work finishes. Abort returns queued messages to the editor. `agent_end` is not idle; `agent_settled` is.

SASE does not own it. The provider CLI does, inside a one-shot subprocess whose contract is a single turn plus a finalizer declaration. Long work is chopped into successor turns. That is a deep philosophical choice (see the inlined `single-turn-agents` decision) and it is the first thing a Pi user will feel as a downgrade.

Pi Durable is closer to SASE here than the coding-agent is: `submit()` durably admits input, generation and tools are checkpointed tasks, `requestId` is exactly-once, and `resume()` continues after a crash. SASE already has monitors, gates, and host completion. Durable has a tighter "nothing is shown before its commit is stored" loop around the *model turn itself*.

### 2. Session vs operating records

Pi's unit of memory is a **session file**. Default path: `~/.pi/agent/sessions/--<cwd>--/<timestamp>_<id>.jsonl`. The file is a tree. `/tree` moves within it. `/fork` and `/clone` copy a branch into a new file. Compaction inserts a summary and keeps recent tokens (defaults: reserve 16,384, keep 20,000). Branch navigation can attach a summary of the abandoned path. Original entries are never deleted. `/export` writes HTML or JSONL. `/share` uploads a viewer (Radius, else a private gist). OSS users are asked to publish sessions to Hugging Face.

SASE's unit of memory is a **project operating system**: beads, goals, patches, artifacts, instruction bundles, agent chat logs, ToolRuns. Agent sessions (formerly families) are sequential chains of turns, not conversation trees. Compaction of a chat is not a first-class user command with a lossless tree. The strength is that work state survives swapping Claude for Codex for Grok. The weakness is that a Pi user cannot "go back to the message before the bad refactor and branch."

### 3. TUI

Pi's TUI *is* the conversation: transcript, editor, footer with cwd, session, model, context, usage, and cost. Fullscreen (now default) keeps the editor pinned. `@` attaches files. `!` runs a shell command into the transcript; `!!` runs it without sending output to the model. `/` is a searchable command palette over built-ins, templates, skills, and extension commands. Themes are JSON. Extensions can replace header, footer, editor, and add overlays. The TUI library (`pi-tui`) is a separate package with differential rendering and CSI 2026 synchronized output.

SASE's TUI is a control surface for a fleet: Agents tab, Artifacts, Services, Launch Control, query language, command palette, screenshots. It is better at "what is running, what landed, what is blocked" and worse at "talk to the model." A Pi user who opens `sase tui` will look for the editor and the cost footer and not find them as the center of the product.

`sase tmux-agent` admits this: the satisfying inner loop still lives in the vendor CLI.

### 4. Extensibility

Pi's extension API is the product. A factory receives `ExtensionAPI` and can hook `before_agent_start`, `tool_call`, `tool_result`, `agent_before_settle`, `session_before_compact`, `project_trust`, `cache_warming_decision`, and more. Tools declare TypeBox schemas, exposure (`direct` / `model-only` / `codemode` / `deferred` / `hidden`), MCP-style annotations, and custom renderers. Packages install from npm or git into user or project settings, with project trust as the load gate. The repo ships 50+ examples, including plan-mode, subagent, permission-gate, protected-paths, Gondolin, sandbox, SSH, custom compaction, and a Doom overlay.

SASE's plugin system is entry points and pluggy hooks at the *host* layer: VCS, workspace, LLM provider, macros, commands, artifact refs. That is the right seam for "add GitHub" or "add `sase listen`." It is the wrong seam for "intercept this tool call" or "swap compaction." A Pi user who has written a 40-line `permission-gate.ts` will find SASE's plugin surface heavy and far from the model.

Macros are SASE's closest analog to Pi prompt templates, and they are more powerful (typed inputs, Jinja, swarms, project tags, artifact refs). They are also more to learn. Pi templates are a Markdown file in `~/.pi/agent/prompts/` that becomes `/review`. That on-ramp is the thing to copy, not the whole macro compiler.

### 5. Isolation and permissions

Pi: process permissions of the user. No built-in permission system. Project trust only controls whether `.pi` settings, extensions, skills, and MCP load. Context files (`AGENTS.md`, `CLAUDE.md`) load regardless. Safety docs tell you to containerize. Gondolin keeps Pi and credentials on the host and sends built-in tools into a local Linux micro-VM.

SASE: numbered workspace clones, claim guards, LaunchApproval, holds, sudo gates, command-backed gates, ToolRun recording. The agent can still do anything inside its clone that the provider CLI can do, but it cannot silently mutate the primary checkout, and landing is host-owned.

A Pi user who likes "no permission popups" will like SASE's isolation *if* they understand it as the sandbox they currently have to set up with Docker. They will not like being asked to confirm every stitch unless the default path is quiet for trusted projects.

### 6. Models and routing

Pi switches models mid-session (`/model`, `Ctrl+L`, `Ctrl+P` cycle). Virtual models let an extension route each request (plan on Opus, implement on GPT, stick to the same model across tool follow-ups). Footer shows `auto • high → gpt-5.6-luna • medium`. `/session` breaks down cost per physical model. Classifier and image models are first-class in Codemode (`models.classify()`, `models.generateImages()`).

SASE routes at *launch* via provider adapters and size aliases (`@xlarge` down the effort ladder). Usage-limit auto-disable can hard-block Claude or Grok for hours. Mid-turn model switching is a provider CLI feature, not a SASE one. Size aliases are a good primitive; they are not a virtual-model router the user can write in an afternoon.

### 7. Codemode and tool budget

Pi's Codemode runs JavaScript in a QuickJS sandbox. The model writes a script; the script calls tools (including in parallel), filters output, and only the script's result returns to the model. Tool exposure can hide MCP catalogs from the prompt (`deferred` / `codemode`) and let `tool_search` activate them. This is how Pi absorbed MCP without dumping every server's tools into every request.

SASE has no equivalent at the host layer. MCP, if present, lives inside the provider CLI. Instruction bundles try to control what the *provider* loads, and current providers do not even read `SASE_INSTRUCTIONS_FILE`. A Pi user who has built a workflow around Codemode will see SASE as a prompt-bloat machine unless the Pi provider preserves Codemode.

### 8. Durability and crash behavior

Pi coding-agent: if the process dies, you look at the session file and continue. Compaction and retries exist, but the process is the runtime.

Pi Durable: every generation and tool call is a task with a checkpoint. Replay-safe tools rerun; others report `interrupted`. Submissions are idempotent by `requestId`. Storage backends: memory, SQLite, JSONL, with a conformance suite. Claimed core size without tests: ~15k lines.

SASE: the *run* is durable (launch metadata, chat, artifacts, workspace claim). The *model turn* is owned by the provider process. Monitors and gates continue the *host* workflow after a turn ends. That is the right split for wrapping CLIs. It is weaker than Durable for "the laptop slept in the middle of a tool call and I want the same tool task to resume."

### 9. Multi-agent and remote

Pi coding-agent: no built-in sub-agents. Examples spawn children via extensions or tmux. "No background bash — use tmux."

Pi Durable: sub-agents are a few lines: create an owned conversation, configure a cheaper model, `submit` with a `requestId`, wait. Foreground children keep the parent busy; background children survive Esc.

SASE: multi-agent is the product. Clans, sessions, tribes, hoods, `%wait`, `%queue`, `%dispatch`, isolated clones, fan-out from one prompt. Remote dispatch is a plugin seam. This is the one place SASE is not behind Pi, and it is the reason a Pi user would still want SASE.

`pi-env` is worth a separate look: a small Rust daemon over SSH, host-key pinning, no forwarding, tools run remotely while Durable and credentials stay local. SASE's `%dispatch` is the analog. The daemon-plus-conformance-suite pattern is cleaner than "SSH and hope."

### 10. Onboarding and distribution

Pi: one curl, `/login`, type a task. Windows installer. Nix flake. `pi update`. Package gallery at pi.dev/packages. Docs at pi.dev/docs/latest. Interactive site. Discord.

SASE: `uv tool install sase`, `sase doctor`, authenticate a *different* CLI, `sase run "+home …"`, then `sase tui`. Fifteen-minute getting started, plus a glossary of beads, patches, macros, stitches, gates, and instruction bundles. POSIX only.

Popularity is not quality, but it is a conversion input. Pi is a mass-market MIT coding agent. SASE is a 5-star alpha OS used heavily by its author. A Pi user has never heard of SASE. The first five minutes have to feel like Pi, or they bounce.

### 11. Supply chain and contribution culture

Pi treats lockfiles as reviewed code: exact pins, `min-release-age=2`, install-lock for the curl installer, `--ignore-scripts` by default, lifecycle-script allowlist, scheduled `npm audit`. New issues/PRs from unknown contributors auto-close; `lgtm` / `lgtmi` is the gate. That is a coherent "minimal core, high bar" culture.

SASE's contribution surface is internal and agent-heavy: beads, stitches, `just check`, host-owned commits, auto-close of *agent* work through finalizers. The cultures do not map. A Pi user who has been auto-closed by Pi's gate will not care. A Pi user who wants to extend SASE will hit Python entry points, Rust core pins, and generated instruction files.

## Where SASE is already stronger

These are the reasons a Pi user might *add* SASE, if the inner loop is preserved.

1. **Isolated numbered workspaces.** Pi's cwd *is* the workspace. Isolation is optional Docker. SASE claims a clone per run. That is the correct default for a team of agents editing git.
2. **Host-owned landing.** Pi writes files; git is yours. SASE agents declare; the host stitches. A Pi user who has watched an agent commit garbage will understand this immediately — if it does not add a permission theater they opted out of.
3. **Fleet control.** One prompt, several models, waits, retries, archives. Pi can do this with packages and Durable conversations; SASE already productized it.
4. **Work records outside the chat.** Beads, goals, patches, ToolRuns, receipts. Pi sessions can hold custom entries and Durable can hold documents, but SASE's git-portable issue graph and PR-sized Patch lifecycle are built for engineering operations, not for a conversation.
5. **Provider neutrality.** Pi's superpower is many model APIs in one loop. SASE's is many *harnesses* in one OS. If Pi becomes the user's favorite harness, SASE can still run Codex next to it. Durable cannot wrap Claude Code.
6. **Audited memory.** `sase memory read` with reasons, core vs reference, webs. Pi loads `AGENTS.md` and on-demand skills. SASE's always-on instruction budget is a known problem; the *mechanism* (progressive disclosure with an audit trail) is the right one.
7. **Human gates that are durable.** Pi's permission-gate example is in-process and dies with the process. SASE gates survive the agent. For "approve this deploy tomorrow," SASE wins.
8. **Multi-project and sidecars.** Pi is cwd-scoped. SASE is a machine-wide project registry with research/plans/agents sidecars.
9. **Background OS.** AXE, service host, monitors, named procs, Telegram. Pi-chat and Durable multiplayer are the Pi-side answers; they are not the coding-agent default.

## Where Pi is stronger, for a Pi user

1. **Time-to-first-token of joy.** Curl, login, type. SASE asks you to install two CLIs and learn a vocabulary.
2. **The conversation is the product.** Steering, follow-up, abort-with-queue-restore, `/tree`, `/compact`, cost footer.
3. **Session trees that do not lie.** Branching does not delete. Compaction does not delete. Exports are HTML a human can send.
4. **Make-it-yours loop.** Write an extension, `/reload`, keep going. Ask Pi to write the extension. Publish `npm:@you/pi-tools`.
5. **Model mobility inside one task.** `/model` mid-session, virtual routers, per-model cost.
6. **Codemode.** Parallel tool calls and filtered output without burning the context window on MCP catalogs.
7. **Windows, Termux, Nix, standalone binaries.** SASE is POSIX-only.
8. **Embeddability.** RPC and SDK. OpenClaw exists. SASE is a host, not a library.
9. **Context engineering as a first-class story.** Tiny preamble, structured prompt sections that patch without busting the cache, skills as progressive disclosure, custom compaction hooks.
10. **Polish.** Themes, OSC 7501, inline images, fullscreen editor, `/bug` reports, session sharing, a public docs site that is the product.

## What SASE can learn, without becoming Pi

Steal primitives. Do not steal the product identity.

**From the coding-agent (inner loop).** Live RPC control of a long-lived agent; session trees with lossless compaction; slash-command templates; a cost/context footer; `/reload`; HTML export; virtual-model routing; Codemode-style tool exposure. These make the *control plane* feel as good as Pi's chat.

**From Pi Durable (operating layer).** "Nothing is shown before its commit is stored" around tasks, not only around git. `requestId` idempotency. Documents committed atomically with transcripts (a todo list that cannot disagree with the chat that produced it). Background compaction while the conversation keeps working. Task graphs a TUI can subscribe to. Replay policies on tools.

**From Chord.** Facets that split one plugin across TUI, Telegram, and a future web UI, with replicated state and a transport-independent service wire. SASE already has multiple surfaces; they do not share a state runtime.

**From pi-env.** A tiny verified remote daemon, not "SSH the whole agent."

**From the package system.** `sase install npm:…` / `git:…` for macros, skills, and themes, with project trust. SASE plugins today are Python distributions in the same environment. Pi packages are user-level, reviewable, and scoped.

**From the philosophy, selectively.** "Wait until a pattern proves itself" is how Pi stayed small and how it eventually added MCP. SASE's core memory already fights bloat. The lesson is not "never add features"; it is "features that are not load-bearing belong in packages, and the core exists to be influenced by them."

**Do not copy.** Auto-closing new contributors. Skipping isolation. Skipping host-owned git. Baking a coding-agent loop into SASE that competes with Pi instead of hosting it. Plan mode and sub-agents in core — SASE already has a better multi-agent model.

## Ranked improvements for appealing to a Pi user

Ordered by conversion impact: would a daily Pi user try SASE, keep using it, and tell another Pi user. Effort notes are relative, not schedules.

### 1. First-class Pi provider over RPC, not print-mode oneshot

**Why it ranks first.** Without this, nothing else matters. A Pi user will not abandon `pi` for Claude Code so that SASE can launch it. Print mode (`pi -p`) throws away the session tree, steering, and `/reload`. RPC mode is the documented language-independent control plane: `prompt`, events, `agent_settled`, steer vs follow-up, abort, model changes, session fork.

**What to build.** An `sase_llm` provider that starts `pi --mode rpc` in the claimed workspace, sends the expanded prompt, streams events into the Agents chat pane, and treats `agent_settled` as turn completion. Persist Pi's session id on the SASE agent record so `--continue` / `--session` round-trips. Map SASE handoff/pipe to Pi follow-up, and SASE interrupt to Pi abort.

**Fits existing machinery.** Provider plugin seam, workspace clones, Agents tab chat, instruction-bundle shadow files (Pi will actually load `.pi` / `AGENTS.md` — verify with `sase instructions verify`).

**Risk.** Pi's inner loop is multi-turn. SASE's contract is single-turn. The honest design is: one SASE agent row owns one long-lived Pi RPC process; successor "turns" are additional `prompt` commands on the same session, not new processes. That is a provider-shaped exception to single-turn, similar in spirit to how monitors already continue work mechanically.

### 2. Isolated clones that a live Pi session occupies

**Why.** Pi users who have been burned by an agent editing the wrong tree will adopt SASE for this alone — if Pi still feels like Pi inside the clone.

**What to build.** Default Pi-provider launches into a numbered workspace. Set Pi's cwd and `sessionDir` to workspace-scoped storage so sessions do not leak across clones. Project trust: auto-approve the clone (SASE created it) and keep asking on unfamiliar primary checkouts.

**Fits.** Workspace claim path, `sase repo open`, existing tmux-agent cwd behavior.

### 3. Host-owned git landing that waits for `agent_settled`

**Why.** Pi does not own git. SASE does. The combined product is "Pi types, SASE lands." That is a clearer pitch than either tool alone.

**What to build.** On `agent_settled`, run the existing finalizer path: declaration or a Pi-side equivalent (extension that writes a SASE-shaped summary), then `sase stitch create` from the host. Do not let Pi's `auto-commit-on-exit` example become the landing path.

**Fits.** `/sase_final`, stitches, Patches. Teach a tiny Pi extension to emit a declaration file SASE already understands, rather than reimplementing git inside Pi.

### 4. A "Pi user" on-ramp that hides the OS until it is needed

**Why.** Getting Started currently teaches doctor, providers, `+home`, artifacts, and a glossary. A Pi user needs: install SASE, SASE finds `pi`, `sase tui`, press one key, Pi opens in an isolated clone, landing is reviewed. Beads and macros can wait.

**What to build.** `sase doctor` detects Pi. Launch Control lists Pi next to Claude. A first-run recipe: `sase run --provider pi "…"` with no project-tag lecture. Docs page "SASE for Pi users" that is one screen.

**Fits.** `sase doctor -C llm.auth`, Launch Control, tmux-agent catalog — but the result must be a *managed* agent, not an unmanaged tmux window.

### 5. Attach, steer, and follow up from sase's TUI

**Why.** The Agents chat pane is currently a log of a finished (or streaming-oneshot) turn. A Pi user wants to type while the agent works. Pi already distinguishes steer vs follow-up. RPC already queues them.

**What to build.** When the selected agent is a live Pi RPC session, the prompt box sends steer on Enter and follow-up on a documented chord (match Pi's `Alt+Enter` if the terminal allows it). Show queued messages. Esc aborts and restores the queue into the editor. Footer shows Pi's model, context, and cost.

**Fits.** Agents tab, prompt widget. This is the feature that makes SASE's TUI feel like a cockpit over Pi rather than a job board.

### 6. Import and export Pi session trees as SASE artifacts

**Why.** Pi users have months of JSONL history. If SASE cannot see it, they will not move. If SASE can `/export` HTML the way Pi does, they can share a run without teaching someone SASE.

**What to build.** `sase artifact create` from a Pi JSONL path (tree-aware, not flattened). Agents tab "open in Pi" / "fork this session." HTML export of SASE agent chats that a Pi user would not be ashamed to gist. Optional `/share` analog.

**Fits.** Artifact snapshots, Agents history. Do not flatten the tree into a linear chat; that throws away Pi's whole session model.

### 7. Slash-command prompt templates in the TUI prompt

**Why.** Pi templates are Markdown files that become `/review`. SASE macros are more powerful and more obscure. A Pi user will type `/` and expect a menu.

**What to build.** In the TUI prompt and in `sase run` interactive entry, `/name` expands a macro or a Markdown template. Keep `#name` for the full macro language. Ship a `~/.sase/prompts/` directory that loads like `~/.pi/agent/prompts/`.

**Fits.** Macro catalog, command palette (`;`). The change is discovery and muscle memory, not a new compiler.

### 8. `sase install` for user-level packages (macros, skills, themes)

**Why.** `pi install npm:@foo/pi-tools` is how Pi users share workflows. SASE plugins require a Python environment install. That is the wrong granularity for "a review prompt and a theme."

**What to build.** `sase install npm:…` / `git:…` / `./path` that drops macros, skills, and TUI themes into user or project scope, with a trust prompt analogous to Pi's project trust. Do not run arbitrary Python from those packages in-process on day one; start with data (macros, Markdown, JSON themes) and keep executable plugins on the existing entry-point path.

**Fits.** Macro discovery order, `sase plugin install`, project spec. A gallery can wait (item 15).

### 9. Session-tree visualization for retries, handoffs, and forks

**Why.** SASE already has retry chains, handoffs, pipes, and agent sessions. They are lists. Pi's `/tree` is the reason people trust history. A Pi user looking at a retry chain should see a branch, not a flat log.

**What to build.** In the Agents pane, render a run's successors as a tree: original prompt, retry, handoff, pipe, drain. Let the user fork from an earlier user message into a new isolated clone (SASE-native fork) *or* into a Pi session fork if the provider is Pi.

**Fits.** Agent sessions, clans, hoods. Do not replace those concepts; give them a tree view.

### 10. Live cost, context, and model footer

**Why.** Pi's footer is how people learn to compact, switch models, and stop bleeding money. SASE tracks ToolRuns and provider usage-limits, but the inner-loop number is missing.

**What to build.** For a live Pi session, subscribe to usage events and show them on the agent row and in the chat footer: model, thinking level, context used/window, session cost, cache hits. For other providers, approximate from provider session records where `sase instructions verify` already reads them.

**Fits.** Agents tab, usage-limit auto-disable. This also makes virtual-model routing (item 13) visible.

### 11. One-liner install and `sase update`

**Why.** Pi's curl installer pins transitive deps and self-updates. `uv tool install sase` is fine for Python people and a hurdle for everyone else. Pi users include Windows-first developers.

**What to build.** `curl -fsSL https://sase.sh/install.sh | sh` that installs `uv` if needed, `sase`, and optionally detects `pi`. `sase update`. A Windows story: even a documented WSL2 path with a single script is better than "POSIX only" on the README's first screen. Native Windows is a later, larger bet (item 16).

**Fits.** Getting Started, `sase doctor`. Do not pretend native Windows exists until it does.

### 12. Crash-safe inner tasks, stolen from Durable, not from the coding-agent

**Why.** SASE already survives *turn* boundaries. It still loses *in-turn* provider work. Pi Durable's lesson is: admit the intent first, checkpoint, resume with `requestId`. SASE's ToolRun "record before admit" decision is the same idea for host commands. Extend it to provider RPC sessions: the reservation that a Pi prompt was sent must survive SASE restart, and reconnecting must wait for the same `agent_settled` rather than double-prompting.

**What to build.** Persist RPC request ids on the agent record. On SASE restart, reattach or mark interrupted. Do not rerun a non-idempotent prompt. This is how a Pi user trusts SASE not to fork their session into two agents.

**Fits.** ToolRun ledger, monitors, launch-admission journal. Durable's storage backends are a reference, not a dependency.

### 13. User-writable virtual model routing at launch and mid-session

**Why.** Pi users already write routers (the 1.0 demo plans on Opus, implements on GPT, Jev decides). SASE size aliases are a fixed ladder. A Pi provider should honor Pi virtual models. For other providers, a small router config ("this bead type → that provider/model") would feel like home.

**What to build.** First: pass through Pi virtual models unchanged. Second: let a project declare a named router SASE applies at launch. Mid-session switch only where the provider is Pi RPC.

**Fits.** Size aliases, `%model`, Launch Control routing. Do not build a second `pi-ai`.

### 14. Preserve Codemode and deferred tools; do not flatten MCP into SASE prompts

**Why.** Pi changed its mind about MCP by putting it behind Codemode. SASE instruction bundles already struggle to deliver content providers will load. If SASE injects a giant tool catalog into Pi, it undoes Pi's context engineering.

**What to build.** Pi provider leaves Codemode, MCP, and tool exposure to Pi settings. SASE contributes *instructions* (memory, bead context) as `AGENTS.md` / `.pi/APPEND_SYSTEM.md` in the clone, which Pi already loads as structured sections. Verify with Pi's startup header and `sase instructions verify`.

**Fits.** Instruction bundles E2, project `.pi` layout. This is a restraint item as much as a feature.

### 15. Themes, HTML share, and a package gallery later

**Why.** These are how Pi feels finished. They do not convert a skeptical user on day one, but they keep a converted user from going back.

**What to build.** JSON TUI themes (Pi's schema is public at `pi.dev/schemas/theme.schema.json` as of HEAD). HTML export of agent chats. A gallery only after `sase install` exists and has a trust model.

**Fits.** ACE themes if any, artifact HTML, research sidecar media. Lowest rank among listed items because they are polish on top of 1–10.

## What not to implement just because Pi has it

- **A native SASE coding-agent loop that talks to `pi-ai`.** That competes with Pi and abandons provider neutrality. Host Pi instead.
- **In-process TypeScript extensions inside the Python host.** Use packages for data, plugins for code, Pi extensions for model-loop hooks.
- **Dropping gates and sudo.** Pi's "no permission popups" is a local-agent stance. SASE's job is the operating layer. Keep isolation; make the trusted path quiet.
- **Plan mode and built-in to-dos in core.** Pi left them out. SASE already has beads, goals, and workflows. Do not add a third planning UI.
- **Auto-close of human contributors.** Irrelevant to the product bet.
- **Replacing beads with Pi session files.** Sessions are chats. Beads are issues. Durable documents are the interesting middle; they belong next to transcripts, not instead of beads.

## Recommendation

Build items **1–5** as one epic: "Pi as a managed inner loop." That epic is the only path that makes SASE appealing to someone who already uses Pi. Items 6–10 make the control plane feel native. Items 11–15 are distribution, durability, and polish.

The strategic risk to name in the epic: Pi Durable is Earendil's own operating layer. It will grow multiplayer, crash recovery, and remote envs. SASE stays relevant to Pi users by remaining **harness-neutral and git-native**: isolated clones, host-owned landing, fleet control, and project records that still work when the inner loop is Codex tomorrow. Hosting Pi well is how SASE gets those users. Becoming a worse Pi is how it loses them.

## Sources

Primary (opened via `sase repo open gh:earendil-works/pi`):

- `README.md`, `CONTRIBUTING.md`, `AGENTS.md`
- `packages/coding-agent/README.md`, `CHANGELOG.md` (through 1.1.0 / Unreleased)
- `packages/coding-agent/docs/{index,how-pi-works,usage,cli,cli-integration,sessions,session-format,compaction,extensions,packages,skills,prompt-templates,sdk,rpc,codemode,virtual-models,security,containerization,tui,slash-commands,configuration}.md`
- `packages/coding-agent/src/core/system-prompt.ts`
- `packages/{ai,agent,tui,durable,chord,env}/README.md`
- `packages/coding-agent/examples/extensions/` (inventory)

SASE (this workspace, package 0.17.1): `README.md`; `docs/{architecture,getting_started,ace,agent_providers,agent_sessions,plugins,macros,instruction_bundles,workspace,completion}.md`; inlined core memory (single-turn agents, host-owned completion, rust core, plugin commands).

Public:

- [pi.dev](https://pi.dev) (fetched 2026-10-11)
- [Pi 1.0](https://earendil.com/posts/pi-1-0/) (2026-10-01)
- [Pi Durable](https://earendil.com/posts/pi-durable/) (2026-10-01)
- GitHub `gh repo view earendil-works/pi` and `sase-org/sase` (2026-10-11)
- npm downloads API for `@earendil-works/pi-coding-agent`; pypistats for `sase` (2026-10-11)
