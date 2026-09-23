# SASE vs. Nous Research's Hermes Agent: Consolidated Functional Comparison

**Date:** 2026-09-23
**Question:** Hermes Agent is often called "a lot like OpenClaw", and maybe "a lot like sase". How do Hermes and sase
compare? How well does sase compete with Hermes *functionally*? Popularity and adoption are excluded.

**Inputs.** Three independent researcher reports sit next to this file:

- `sase_vs_hermes_agent__cld.md`: the deepest one. It reads the Hermes code and docs with file citations.
- `sase_vs_hermes_agent__mus.md`: a code-listing-level survey.
- `sase_vs_hermes_agent__gem.md`: mostly from web and background knowledge, with an SE-weighted rating.

I also did my own verification against local checkouts, focused on the points where the reports disagreed. See §5.

**Version pins.**

| Project | Pin |
| ------- | --- |
| Hermes | `NousResearch/hermes-agent` HEAD `3cf26c82b4` (2026-09-23), tag `v2026.9.21`, `version = "0.21.4"`. The researchers read `358d50ca6d`, from the same day. |
| Hermes companion repo | `NousResearch/hermes-agent-self-evolution` HEAD `0a929e3` (2026-06-17) |
| sase | `master` at `848a90a1b`, release 0.17.1 |

Both projects move fast, so check these pins before reusing any count below.

---

## Bottom Line

- **The two are different kinds of product that overlap in one narrow but important area.**
  - **Hermes is a self-improving personal agent.** It runs its own LLM tool-calling loop with ~70–100 tools, 7 terminal
    backends, browser, computer use and voice. It learns across sessions through memory, auto-written skills and session
    search. It is reachable from ~28 messaging platforms, a desktop app, a web dashboard, an API server and ACP. Over
    2026 it has grown a real multi-agent layer: Kanban, `delegate_task`, `/goal`, swarms and A2A.
  - **sase is a control plane for supervised software engineering that runs on top of *other vendors'* coding CLIs.**
    It drives Claude Code, Codex, Antigravity, Qwen Code, OpenCode, Muse Code and Grok Build, one run per numbered
    workspace clone. Around those runs it adds:
    - durable work tracking (beads, epics, phases, land agents)
    - host-owned commits (finalizers, Patches, mentors)
    - durable human gates
    - scheduling, remote dispatch and audit trails
- **"Like OpenClaw" is accurate for Hermes, and inaccurate for sase.** Hermes and OpenClaw are both always-on agents that
  you *talk to* through chat apps. Hermes ships `hermes claw migrate` to import OpenClaw setups. sase is something you
  *supervise agents through*.
- **"Like sase" is true only in the overlap.** The overlap is: run many agents on real repo work, track it durably,
  schedule it, and supervise it remotely. That is Hermes's Kanban "engineering pipeline" use case.
- **Inside the overlap, sase is the stronger system.** It is the only one of the two that:
  - natively orchestrates heterogeneous vendor CLIs. Hermes's docs say external-CLI Kanban lanes are "*not yet a paved
    path*".
  - takes commits out of the agent's hands.
  - has a plan → epic → sized-phase → land-agent work model.
- **Hermes still leads on some coding-pipeline features**, and sase should borrow them:
  - a built-in per-task review lane
  - PR completion contracts
  - `/goal` judge loops
  - checkpoints and rollback
  - LSP feedback
  - real sandboxes
- **Outside the overlap, sase does not compete, and does not try to.** It has no agent loop of its own, no autonomous
  learning, one chat platform, no voice or browser of its own, no sandbox, no MCP, ACP or API surface, and no Windows
  support.
- **Final rating: 5 / 10 overall** as a functional competitor to Hermes. The spread across domains matters more than the
  average:
  - **~8.5 / 10 for supervised multi-agent, multi-vendor software engineering**
  - **~2 / 10 as a general personal agent**

  §7 explains why the three input ratings (5, 6 and 9) differ and why 5 is the defensible number.

---

## 1. Lineage: Who Is "Like" Whom

- **OpenClaw.** Peter Steinberger first published it in November 2025 as *Clawdbot*. After a trademark complaint it
  became *Moltbot* on 2026-01-27, then *OpenClaw* three days later. Steinberger announced on 2026-02-14 that he was
  joining OpenAI and that a foundation would steward the project.
- **Hermes Agent.** Nous Research launched it publicly on **2026-02-25** under the MIT license. Its repository started
  earlier: the first commit (`21d80ca683`) is dated **2025-07-22**, before Clawdbot existed.
  - So Hermes is a **parallel competitor that absorbed OpenClaw's user base**, through the `claw migrate` importer, the
    `~/.openclaw/` detection banner and `COMPAT_MANIFEST.md`. It is **not a fork or descendant of OpenClaw**.
  - The gem report's diagram, which shows Hermes and sase both "diverging" from OpenClaw, is wrong on both branches.
- **sase.** Its current history starts on 2026-02-14 as a migration from the earlier `gai` project. It shares no lineage
  with either of them.
- **Where the two agents differ.** Third-party comparisons (Composio, 2026-09-15; innfactory; Toolradar) describe
  OpenClaw and Hermes as the two dominant open-source personal-agent frameworks of 2026:
  - OpenClaw leads on channel breadth and its ClawHub marketplace.
  - Hermes leads on its learning runtime and safer defaults.

---

## 2. The Two Systems in Brief

### Hermes: an agent harness

`AGENTS.md` describes Hermes as "the same agent core across a CLI, a messaging gateway, a TUI, and an Electron desktop
app". It "learns across sessions (memory + skills), delegates to subagents, runs scheduled jobs, and drives a real
terminal and browser".

- **Its own loop.** `AIAgent` calls LLM APIs directly in three API modes. It runs tool calls concurrently. Per-conversation
  prompt caching is treated as "sacred".
- **Models.** 39 model-provider plugins, and roughly 45 providers in the docs, including local Ollama, vLLM and
  llama.cpp. It also offers fallback chains, credential pools and a Nous Portal subscription.
- **Tools.**
  - roughly 70–100 tools
  - 7 terminal backends: local, Docker, SSH, Singularity, Modal, Daytona and Vercel Sandbox
  - browser backends, computer use, vision, image generation, TTS/STT and voice mode, with a wake word
- **Learning loop.**
  - A background fork reviews the conversation every ~10 turns or tool iterations and writes memory and skills. By
    default no human approves these writes (`agent/background_review.py`).
  - A Curator ages out unused agent-written skills.
  - FTS5 `session_search` recalls past sessions.
  - Optional user-model and memory providers, such as Honcho and Mem0.
- **Reach.**
  - 22 platform plugins (`plugins/platforms/`) plus gateway-level Signal, BlueBubbles, WeChat, QQ, Yuanbao, WhatsApp Cloud,
    webhooks and MS Graph, for **~28–30 channels** in total.
  - It also runs an OpenAI-compatible API server, an MCP client *and* server, ACP for VS Code, Zed and JetBrains, A2A,
    and relay.
- **Automation.**
  - Cron, using natural language or cron expressions, with delivery to any platform.
  - `delegate_task` subagents.
  - `/goal`, a judge-driven "Ralph loop" modeled on Codex CLI's `/goal`, plus `/loop` and `/heartbeat`.
  - **Kanban**: a durable, SQLite, multi-profile task board. It has a dispatcher, `task_links` dependencies, claims and
    retries, auto-decomposition, a review lane, swarms and PR completion contracts.
- **Platforms.** macOS, Linux, native Windows, WSL2, Termux, Docker and Nix.

### sase: a coordination layer

sase describes itself as "One developer. A team of coding agents. Tracked, reviewable, repeatable work." Its README says
it "does not replace coding agents". Its defining choices:

- **No LLM loop of its own.** Providers are `sase_llm` entry points wrapping 7 vendor CLIs (plus the `fakey` test
  provider).
  - Model routing uses cross-provider size aliases with round-robin and fallback.
  - Routing is aware of each subscription's usage window.
- **Single-turn agents in isolated full clones.** Each run gets its own numbered workspace clone, not a git worktree.
  Continuation is always mechanical: pipe, monitor, gate or follow-up. See the decision records `single-turn-agents` and
  `gates-never-block`.
- **Host-owned completion.**
  - Agents never commit. They submit a `/sase_final` declaration.
  - Host finalizers make one Conventional Commit per dirty repo, with a `SASE_BEAD=` footer.
  - A run that leaves uncommitted work behind fails.
- **Durable work model.**
  - Beads: plans (tales and epics), phases sized xs–xl, and typed tasks.
  - `sase bead work`: runs phase waves, then a land agent that verifies and integrates the result.
  - Patches track PR-sized work, and mentors review it.
  - YAML workflows and swarms.
- **Human gates as durable records, not blocking processes.** Gate types:
  - plan approval
  - questions
  - launch approval for any agent-initiated launch
  - typed sudo requests with hashed executables
  - task triage
  - custom gates
- **Operations.**
  - A per-machine service host runs the scheduler and the gateway.
  - A Textual TUI serves as the operations console.
  - A Telegram plugin, a Rust mobile gateway with an Android client, and Neovim with an xprompt LSP.
  - Tailnet remote dispatch (`%dispatch:<machine>`).
  - Audited reads of memory, repos, artifacts and skills.
- **Platforms.** POSIX only (Linux and macOS). The Rust core (`sase_core_rs`) is required.

---

## 3. A Layer Model of the Overlap

This model is adapted from cld. It is the clearest way to see where the two products meet.

| Layer                                     | Hermes                                                                  | sase                                                                                |
| ----------------------------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| 1. Model access                           | **Owns it**: ~40–45 providers, local models, fallback, credential pools | Delegates to vendor CLIs; adds cross-CLI aliases and usage-window routing           |
| 2. Agent loop and tools                   | **Owns it**: `AIAgent`, ~70–100 tools, 7 backends, browser, voice       | **Does not own it**: inherits Claude Code's and Codex's harnesses                   |
| 3. Memory and learning                    | **Deep**: autonomous learning loop, session FTS, curator, user model    | Curated, typed, audited project memory; no autonomous learning                      |
| 4. Multi-agent orchestration and tracking | **Solid**: Kanban and dispatcher, `delegate_task`, `/goal`, swarms, A2A | **Deep**: beads, epics, phases, land agents, clans and families, admission, dispatch |
| 5. Engineering governance and landing     | Thin to moderate: worker-owned git, review lane, PR-checks contract     | **Deep**: host-owned commits, Patches, hooks, mentors, gates, provenance            |
| 6. Surfaces and reach                     | **Very broad**: ~28 chat channels, desktop, web, TUI, ACP, API, voice   | Focused: TUI, CLI, Neovim/LSP, Telegram, Android                                    |

- Hermes is thick in layers 1–3 and 6, and has grown a respectable layer 4.
- sase deliberately skips layers 1–2 and is thick in layers 4–5.
- **"Hermes is like sase" is true for layer 4 and part of layer 5, and nowhere else.**

The products are also **complementary**:

- Hermes's Kanban lacks exactly what sase's core provides: external-CLI worker lanes (`kanban-worker-lanes.md`).
- Hermes has a clean headless mode: `hermes chat --oneshot -q … --format stream-json` (`reference/cli-commands.md`). That
  is exactly the shape a `sase_llm` provider needs.

---

## 4. Capability Matrix

Edge key:

- **H** means Hermes is ahead; **S** means sase is ahead.
- **≫** means the other side effectively lacks the capability.
- **≈** means rough parity, or different approaches that are about equally good.

| Area                                 | Hermes                                                                                                                 | sase                                                                                                        | Edge   |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ------ |
| Own agent loop / zero-CLI operation  | Yes                                                                                                                    | No, by design; needs at least one vendor CLI                                                                | H≫     |
| Coding quality per run               | Own loop plus LSP diagnostics after edits, checkpoints, optional Codex app-server runtime                              | Inherits frontier harnesses: Claude Code, Codex, Grok Build and others                                      | ≈      |
| Heterogeneous vendor agents          | Only through skills that drive `claude -p` or `codex exec` from a terminal; no Kanban lane                             | 7 CLIs natively; multi-model fan-out; `%alt`; cross-provider aliases                                        | S≫     |
| Durable task graph                   | Kanban: SQLite, `task_links`, runs, events, claims, retries, auto-decompose, swarms                                    | Beads: event-sourced Rust core; plan, epic, phase, task; dependencies, notes, `+1`, task types, triage      | ≈/S    |
| Epics and landing                    | Flat graph plus a root card; no plan tier; no integration agent                                                        | Plan approval → epic → sized phases → verifying and integrating land agent, including nested epics          | S      |
| Per-task review loop                 | Built-in `review` column; `kanban_request_review` auto-spawns an `sdlc-review` reviewer; request-changes loop          | Mentors on Patches, land-agent verification, CRS for PR comments; no per-bead review lane                  | H      |
| Commit and PR ownership              | Worker LLM runs `git` and `gh`; the read-only PR completion contract checks required checks                            | Host-owned finalizers; `SASE_BEAD` footers; Patches; `#pr` workflow                                         | S≫     |
| Workspace isolation                  | Kanban worktrees per task; subagent worktrees opt-in, falling back silently to a shared dir                             | Full numbered clones with alternates, registry, rescue store                                                | ≈/S    |
| Checkpoint / rollback                | Shadow-git `/rollback` (opt-in, off by default)                                                                        | Clone isolation plus commits; no in-run rollback                                                            | H      |
| Goal loops                           | `/goal` judge plus shell quality gates; `/loop`; `/heartbeat`                                                          | `%repeat`, pipes, monitors, `%wait`; no judge-driven continuation                                           | H      |
| Scheduling                           | Cron (natural language or cron expressions), delivery anywhere, `wakeAgent` pre-checks, executions ledger              | Interval routines and jobs, `proposed_launches`, `%wait(time=…)`; delivery only to sase's own channels     | H      |
| Human approval                       | Per-command approvals (smart, manual or off) that **block in-process** with a 300 s fail-closed timeout; `kanban_block` | **Durable, processless** typed gates (plan, question, launch, sudo, triage, custom) that can wait for days | ≈ (see §6.3) |
| Runtime containment                  | Hardened Docker, Modal, Daytona, Singularity, SSH, Vercel; egress proxy; hardline blocklist                            | None: CLIs run with bypass flags; the clone is the only isolation                                           | H≫     |
| Prompt-injection defenses            | Context-file scanning, `<untrusted_tool_result>` wrapping, SSRF guard                                                  | Relies on vendor CLIs; audited reads                                                                        | H      |
| Memory                               | Bounded `MEMORY.md` and `USER.md`, auto-written; FTS session recall; external providers                                | Core and reference notes, memory webs (glossary, decisions), audited reads, gated writes                    | ≈ (different goals) |
| Autonomous learning                  | Background review writes memory and skills; Curator                                                                    | None by design; discovered work becomes task or memory beads for human triage                               | H≫     |
| Skills                               | ~58 bundled and ~150 optional; agentskills.io; hubs; agent-authored                                                    | ~19 generated protocol skills deployed to every provider; usage audit                                       | H      |
| Reusable prompts and workflows       | Skills as slash commands, `execute_code` RPC scripts                                                                   | Typed Jinja2 XPrompts; YAML workflows (agent, bash, python, parallel, loop, HITL); swarms                    | S      |
| Messaging and mobile                 | ~28–30 channels, DM pairing, voice memos                                                                               | Telegram plugin and Android client                                                                          | H≫     |
| Desktop, web and IDE                 | Electron desktop, web dashboard, Ink TUI, ACP                                                                          | Textual TUI (a deeper ops console), Neovim and LSP; no web UI                                               | H      |
| Programmatic interfaces              | OpenAI-compatible API (`/v1/runs`), MCP client and server, A2A, Python library                                         | CLI with JSON output, pluggy plugins; **no MCP, ACP or API server**                                         | H      |
| Multi-machine                        | Federation of full installs (peer, A2A, relay, Desktop connections); cloud sandboxes; **Kanban is single-host**        | Tailnet `%dispatch`: one Agents list, remote gates, sidecar sync; v1 limits                                 | ≈      |
| Model breadth vs. subscription cost  | ~40–45 providers, local models                                                                                         | 7 subscription CLIs; usage-window routing; auto-disable; effort ladder                                      | H (breadth) / S (flat-rate cost) |
| Observability and provenance         | Logs, `/usage`, `/insights`, Kanban events                                                                             | Audit logs for memory, skill, repo and artifact reads; telemetry DB; bead history; LLM Calls timeline       | S      |
| Extensibility                        | Plugins for tools, platforms, memory, providers and terminals; 4 hook systems                                          | 11 pluggy groups: LLM, VCS, workspace, finalizers, task types, artifact refs and others                     | H      |
| OS support                           | Adds Windows, WSL2, Termux and Nix                                                                                     | Linux and macOS                                                                                             | H      |
| Voice, browser, vision, computer use | Yes                                                                                                                    | Only what the wrapped CLI offers                                                                            | H≫     |

---

## 5. Where the Researchers Disagreed, and How I Resolved It

| Claim | Who said it | Verdict and evidence |
| ----- | ----------- | -------------------- |
| Hermes "lacks a native issue tracker or persistent dependency graph"; decomposition is "in-prompt checklists". | gem | **False.** `kanban.md` describes "a durable task board… every task is a row in `~/.hermes/kanban.db`". It has `kanban_link`, dependency promotion, claims, retries, auto-decomposition and swarms. |
| Hermes has "no multi-agent scheduling framework… no multi-machine fleet dispatch"; code review is "None". | gem | **Mostly false.** Hermes has a Kanban dispatcher, `delegate_task`, A2A, peer and relay, a `review` column with an auto-spawned `sdlc-review` reviewer, and PR completion contracts. One part is **true**: Kanban itself "is deliberately single-host" (`kanban.md`). |
| Hermes self-improves through DSPy + GEPA (scored 8.5/10). | gem | **Misattributed.** DSPy + GEPA live in a *separate* repo, `hermes-agent-self-evolution`. That repo has **8 commits**, and its last commit was on 2026-06-17. It implements Phase 1 only: it evolves `SKILL.md` files offline and opens PRs against hermes-agent "for human review, never direct commit". Phases 2–5 are "Planned". The runtime hermes-agent repo does not reference it. Hermes's *real* runtime learning loop is `background_review` plus the Curator, and it is substantial. |
| sase uses "ephemeral numbered git worktrees". | gem | **Imprecise.** sase uses full numbered clones (`docs/workspace.md`). The difference matters: worktrees are Hermes's mechanism. |
| sase's guarded recipes mean "agents cannot execute unadmitted raw commands". | gem | **Overstated.** `docs/tool.md` says only `check` and `check-full` are guarded, and calls the guard "a guardrail against habit, not a security boundary". sase agents otherwise run vendor CLIs with bypass flags. |
| Symvision, two-speed CI, visual snapshots and `detach_scope` as competitive safety features. | gem | **Mostly internal hygiene.** Symvision, two-speed CI and the visual snapshots belong to the sase repo's own development discipline. They are not capabilities sase provides to the projects it manages. `detach_scope` (`src/sase/detach_scope.py`) is a real feature: service restarts do not kill running agents. |
| HITL: Hermes "pauses in chat while the agent process remains in memory". | gem | **Correct, and cld under-weighted it.** `tools/approval.py` uses a "blocking gateway round-trip". `security.md` sets a default `timeout: 300` that fails closed. sase gates are durable and processless, and they survive days. |
| Messaging reach: 15+, 16–20 or ~28. | gem, mus, cld | **About 28–30.** There are 22 plugins in `plugins/platforms/`, plus gateway-level Signal, BlueBubbles, Weixin, QQ, Yuanbao, WhatsApp Cloud, webhook and MS Graph adapters. |
| Model providers: ~35 or ~45. | mus, cld | **Both are defensible.** There are 39 `plugins/model-providers/` entries, and the docs table lists more. "~40–45" is fair. |
| Scheduling: sase 8/10 or 4.5/10. | mus, cld | **Closer to cld.** sase's scheduler, service host and monitors are enough for engineering automation. Hermes's cron-as-a-product has natural language, cron expressions and delivery anywhere, plus `/goal`, `/loop` and `/heartbeat`, and none of those have sase equivalents. I score sase **5**. |
| Overall rating: 9, 6 or 5. | gem, mus, cld | See §7. |

The pattern is clear. gem's picture of Hermes is the **early-2026 personal-assistant Hermes**. Between April and September
2026, Hermes shipped Kanban, `/goal`, the Curator, Desktop, A2A and Bot Mode, and gem's picture predates all of them.
gem's architectural points about sase are right (single-turn, host-owned completion, processless gates), but its
comparative scores are built on the stale picture of Hermes.

---

## 6. The Overlap in Detail

### 6.1 Multi-agent orchestration: Hermes Kanban vs. sase beads and `sase bead work`

**Hermes Kanban is well engineered:**

- a 60 s dispatcher tick with atomic claims
- claim TTLs and PID fingerprinting
- an exit-code taxonomy: `75` means rate-limited, requeue; `78` means a terminal error, block
- a protocol-violation budget, and a checkpoint notice at 90% of the iteration budget
- auto-decomposition of triage cards
- `swarm` topologies (workers → verifier → synthesizer)
- per-task model and skill overrides
- control from the CLI, the dashboard, Desktop, or `/kanban` in any chat

**sase is deeper in the software-engineering direction:**

- **A plan tier.** Plans are tales or epics, and they need human approval.
- **Sized phases.** Phase size selects the model alias, and large or xlarge phases get `#plan` first.
- **A land agent.** It verifies each child's claims against the source, integrates changes that landed on the base
  branch meanwhile, triages `PROPOSED FOLLOW-UP:` notes into beads, and resumes nested landings.
- **Any vendor CLI as a worker**, including fan-out of one prompt to Claude, Codex and Antigravity at once.
- **Richer launch control:** clans, families and tribes; `%wait`, `%queue`, `%hold`, `%repeat` and `%alt`; capacity
  admission; launch approval.
- **Governed discovered work:** agents file typed task beads through `/sase_new_task`, and humans triage them.

**Hermes is ahead on** built-in per-task review, automatic decomposition, and an explicit taxonomy of worker failures.

**Neither distributes one task graph across machines.** Hermes Kanban is single-host. sase's remote-dispatch v1 cannot
combine `%dispatch` with `%wait`, `%queue` or `%clan`.

### 6.2 Landing

- **In Hermes, landing is the worker LLM's job.** Its docs have workers commit, `git push` and `gh pr create` themselves.
  The host's only landing control is the read-only PR completion contract. It checks required checks and rulesets, and
  "no remote writes are performed by this gate".
- **In sase, an agent cannot mis-land.** Finalizers own every commit, every commit is attributable, and a run that leaves
  dirty work fails.
- **sase lacks two things here:**
  - a required-checks gate for `#pr` Patches (agents watch CI through monitors instead)
  - in-run rollback

### 6.3 Human-in-the-loop and safety: opposite philosophies

**Hermes governs *individual actions*:**

- The `smart` approval mode uses a guardian LLM to rate each command APPROVE, DENY or ESCALATE.
- Headless and cron runs default to deny.
- A hardline blocklist applies even under `--yolo`.
- Containers are hardened, and an egress proxy keeps real keys out of sandboxes.
- It scans for prompt injection and pairs DMs.

Hermes's own `SECURITY.md` concedes that "the only security boundary against an adversarial LLM is the operating
system". Its approvals are **synchronous and time-limited**: an unanswered card is denied after 5 minutes, and the turn
ends without the command.

**sase governs *lifecycle decisions*:** what gets planned, launched, escalated through sudo, and landed.

- Its gates are durable records. Creating one ends the agent's turn and frees its slot. An answer from the TUI, the CLI,
  Telegram or Android starts a new turn with a decision receipt.
- A developer who is away for a day loses nothing.
- There is no per-command approval layer and no containment: every CLI runs with its permission bypass in a git clone.

**Verdict:**

- **Containment, and any exposure to untrusted input: Hermes, by a wide margin.** sase is not safe to point at untrusted
  input, such as a public bot or issue-triggered launches, without adding a sandbox.
- **Governing a trusted developer's own agent fleet: sase.** It wins on asynchronous governance and auditability, with
  hash-bound gate commands, sudo manifests carrying executable SHA-256s, and audited reads.

### 6.4 Memory and learning: the sharpest philosophical contrast

**Hermes adapts on its own:**

- The agent writes its memory and skills itself, with no approval by default. An opt-in `write_approval` setting stages
  the writes instead.
- FTS recall covers all past sessions.
- A user model is available.
- The Curator archives stale skills.

Hermes's docs also show what this costs:

- The review prompt has to warn against capturing "negative claims about tools".
- Small models "claim a save without calling the tool".
- The content scanner for agent writes is off by default because of false positives.

**sase is curated:**

- Core notes are inlined into every provider's instruction file.
- Reference notes and web strands are read on demand, with a logged reason.
- Writes are gated. Unauthorized updates become `memory` task beads.
- There is no automatic distillation of sessions into memory, no cross-session recall index beyond transcript lookup,
  and no user model. The decision record `corpus-before-mechanism` explains why.

**Verdict:**

- For a personal assistant, Hermes is clearly better.
- For a shared codebase, sase's memory is reviewable, versioned and harder to poison, but it depends on a human to curate
  it.

### 6.5 Scheduling, surfaces and cost

- **Scheduling.** Hermes's cron is a user-facing product ("every weekday at 9, triage my inbox and Slack me"). sase's
  scheduler is the engine behind its own engineering automation: hook, mentor and wait checks, triage, PR mirroring and
  usage refresh.
- **Surfaces.** Hermes's reach is an order of magnitude broader. sase's TUI is a deeper operations console for a fleet
  of coding agents than anything Hermes has; the closest Hermes equivalents are the Kanban dashboard and Desktop's
  subagent panes.
- **Cost.** Hermes pays per token by default. sase is built to get the most out of **flat-rate subscription CLIs**,
  through usage-window probes, automatic disable at limits, weighted round-robin and fallback, and an effort ladder. For
  heavy coding workloads that is a real functional advantage, and Hermes does not attempt it.

---

## 7. Rating: How Well Does sase Compete Functionally with Hermes?

### Why the three inputs disagreed

| Report | Rating | What it measured |
| ------ | ------ | ---------------- |
| cld | **5 / 10** | sase against **Hermes's whole functional surface**, with 14 weighted dimensions |
| mus | **6 / 10** | 10 unweighted dimensions; scores sase's scheduling (8) and extensibility (7) more generously |
| gem | **9 / 10** | "weighted for SE core", which means how good sase is at *sase's* job. It also rests on the claims §5 refutes: that Hermes has no task graph, no review, and no multi-agent or multi-machine support |

The question asks how well sase competes with Hermes, so the yardstick has to be **what Hermes does**, not what sase
does. cld's method answers that question. gem's number answers a different question.

### Scorecard

The scale runs from 0 (absent) to 10 (matches or exceeds Hermes). Scores are capped at 10, so sase's wins cannot hide
missing capabilities. The weights reflect how central each dimension is to Hermes's value and sum to 100. The weights and
most scores come from cld; the right-hand column notes where I changed them.

| Dimension                                 | Weight | sase | Notes                                                                                                   |
| ----------------------------------------- | -----: | ---: | ------------------------------------------------------------------------------------------------------- |
| Single-agent capability                   |     10 |    4 | Coding runs inherit frontier CLIs; no voice, browser or vision of its own; not conversational           |
| Learning, memory, recall                  |     13 |    3 | Excellent curated memory; no autonomous learning, recall index or user model                            |
| Skills                                    |      5 |    5 | Cross-provider protocol skills; no self-authoring, hub or breadth                                       |
| Reach and surfaces                        |     13 |  2.5 | TUI, Telegram, Android and Neovim, against ~28 channels, Desktop, web, ACP and voice                    |
| Scheduling and autonomous loops           |      7 |    5 | Solid scheduler and monitors; no cron or natural language, delivery breadth, or `/goal` (cld 4.5, mus 8) |
| Multi-agent orchestration and tracking    |     11 |  8.5 | Ahead on heterogeneous CLIs and epics; behind on auto-decompose and a review lane                       |
| Engineering governance and landing        |      8 |    9 | Host-owned landing ahead; lacks a PR-checks gate and rollback                                           |
| Human-in-the-loop gating                  |      4 |    8 | Durable asynchronous gates beat 300 s blocking approvals; no per-command approvals (cld 7)              |
| Safety and runtime containment            |      8 |  3.5 | No sandbox; bypass flags; sudo gate and audits are not containment                                      |
| Multi-machine                             |      5 |    6 | Integrated remote dispatch; no cloud sandboxes or hosted instances                                      |
| Model and provider flexibility            |      5 |    6 | Fewer providers, no direct local models; unique subscription economics                                  |
| Observability and provenance              |      4 |    9 | Ahead                                                                                                   |
| Extensibility and interop                 |      4 |  4.5 | Good plugin groups; no MCP, ACP or API server (cld 4, mus 7)                                            |
| Platform support                          |      3 |    3 | POSIX only                                                                                              |
| **Weighted total**                        | **100** | **≈ 5.2** |                                                                                                  |

### Final rating: **5 / 10**

Weighted by what Hermes offers, sase matches or beats it on about half of Hermes's functional surface. A reasonable
range is 5–6 depending on the weights. **The split by domain is the real answer:**

- **Supervised, multi-agent, multi-vendor software engineering: ~8.5 / 10.**
  - Here sase is the more capable system. A developer who runs epics across Claude Code, Codex and Grok, and wants every
    landing gate-approved and attributable, gets more from sase than from Hermes Kanban.
  - Hermes cannot yet run those CLIs as Kanban workers at all.
  - Looking the other way, Hermes as a competitor on *sase's* turf rates about **6 / 10**, well above gem's 4. It has a
    real board, dispatcher, review lane and PR contracts, but no vendor-CLI lanes, no host-owned landing, and no plan or
    epic tier.
- **General-purpose, always-on personal agent (Hermes's and OpenClaw's home turf): ~2 / 10.**
  - Here sase is not a competitor. It has no agent loop of its own, no learning, one chat channel, no voice or browser,
    and no sandbox.
  - This gap is a deliberate architectural choice, not missing polish.

### What would move the rating

**Upward**, most leverage first. Each of these keeps sase's governance model:

1. **Hermes as an 8th `sase_llm` provider.**
   - Hermes's `--oneshot -q … --format stream-json` mode is exactly the shape a provider needs.
   - It would bring Hermes's any-model and local-model loop, browser and LSP under sase's workspaces, gates and
     finalizers.
   - It would fill the external-CLI-lane gap that Hermes itself documents.
   - It turns the main competitor into a supplier. sase currently has no Hermes references at all.
2. **Agent-callable transcript recall:** an FTS index over chats and artifacts. The April 2026 comparison
   (`research:202604/sase_vs_hermes_agent.md`) recommended this too, and sase still lacks it.
3. **Staged, agent-proposed memory drafts,** following Hermes's `write_approval` pattern. For small facts this fits
   sase's gated model better than memory task beads.
4. **A per-bead review lane** in `sase bead work`, and a **required-checks completion gate** for `#pr` Patches.
5. **An optional container or sandbox execution mode,** before any launches driven by untrusted input.
6. **An MCP control-plane server,** plus broader chat delivery through the existing gateway.

Items 1–4 alone could plausibly lift the overall score to about **6–6.5**.

gem suggested an offline `sase xprompt optimize` built on DSPy/GEPA. It is interesting, but it is low priority. Even Nous
has shipped only Phase 1 of that pipeline, and it has been dormant since June.

**Downward:** Hermes shipping a paved external-CLI Kanban lane together with host-side commit ownership. Its docs
already anticipate the lane: `spawn_fn` is pluggable, and `workflow_template_id` is reserved for "v2 workflow routing".
That would erode sase's two strongest differentiators.

---

## Caveats

- No researcher ran Hermes. Its behavior comes from its docs and code. The docs drift in a few places:
  - the curator's stale and archive windows: 30/90 days in the docs, 14/30 days in the config defaults
  - whether session search uses an LLM for summaries
  - tool and test counts
- Several sase capabilities are beta or behind flags: sudo requests, `%proc`, provider drain and typed launch units.
  Remote dispatch v1 has documented limits.
- The weights in the scorecard are judgment calls. A reader who only cares about software-engineering orchestration
  should use the domain ratings (~8.5 vs. ~2), not the blended 5 / 10.

## Sources

**Hermes checkout** (`sase repo open gh:NousResearch/hermes-agent`, HEAD `3cf26c82b4`):

- `README.md`, `AGENTS.md`, `SECURITY.md`, `pyproject.toml`
- `website/docs/user-guide/features/{kanban,kanban-worker-lanes,goals,delegation,cron,curator,memory,skills}.md`
- `website/docs/user-guide/{security,checkpoints-and-rollback}.md`, `website/docs/reference/cli-commands.md`
- `plugins/platforms/`, `gateway/platforms/`, `plugins/model-providers/`
- `tools/approval.py`, `hermes_cli/kanban_pr_acceptance.py`, `agent/background_review.py`

**Hermes self-evolution companion** (`sase repo open gh:NousResearch/hermes-agent-self-evolution`, HEAD `0a929e3`):

- `README.md` and its git history (8 commits, 2026-03-09 to 2026-06-17)

**sase** (`master` at `848a90a1b`):

- `README.md`, `pyproject.toml`
- `docs/{workspace,tool,agent_providers,llms,beads,axe,memory,commit_workflows,remote_dispatch,notifications,sudo}.md`
- `src/sase/detach_scope.py`

**Research inputs:**

- `sase_vs_hermes_agent__{cld,mus,gem}.md`, read through `sase artifact read`
- the cld report's use of `research:202604/sase_vs_hermes_agent.md`

**Web** (for dates and positioning only):

- [OpenClaw: Wikipedia](https://en.wikipedia.org/wiki/OpenClaw)
- [OpenClaw vs Hermes Agent: innfactory](https://innfactory.ai/en/blog/openclaw-vs-hermes-agent-comparison/)
- [OpenClaw vs Hermes Agent (2026): Toolradar](https://toolradar.com/blog/openclaw-vs-hermes-agent)
- [OpenClaw vs Hermes Agent: Composio (2026-09-15)](https://composio.dev/content/openclaw-vs-hermes-agent)
- [Hermes Agent docs](https://hermes-agent.nousresearch.com/docs/)
