# Can Hermes Agent Do Everything sase Does? A Feature-Set Test of "Just Use Hermes"

**Date:** 2026-10-09
**Researcher:** cld (one of five independent researchers in a swarm)
**Claim under test:** "Hermes can do everything that sase can, so for just about any user except Bryan, the smart move is
to not bother with sase."
**Scope:** This compares feature sets only. Popularity, adoption, community size and stars are excluded, as the request
asked.

---

## Bottom Line

The claim combines two separate claims, and they get different verdicts.

1. **"Hermes can do everything sase can": refuted.** I checked 20 capabilities sase ships against current Hermes:
   - Hermes core covers **5** of them at parity or better.
   - **4** more need an opt-in runtime or an experimental plugin.
   - **6** are covered only by community catalog plugins or by the Hermes LLM improvising with its shell.
   - **5** have no equivalent at all.

   The four that matter most are differences of architecture, not features Hermes simply hasn't got to yet:
   - **Vendor coding CLIs are not first-class workers.** Hermes cannot run Claude Code, Codex, Gemini/Antigravity, Grok
     Build and the rest as supervised workers. Its own docs still call an external-CLI Kanban lane "*not yet a paved
     path*".
   - **The host never owns the commit.** In Hermes the worker LLM runs `git` and `gh` itself.
   - **Human approval is synchronous.** Approvals block a thread and time out after 300 s. An attempt to make them durable
     was merged and reverted on the same day, 2026-10-01.
   - **There is no shared, audited project memory.** Hermes has nothing like versioned, human-curated project memory
     delivered the same way to every vendor CLI, with audited reads.
2. **"For just about any user, skip sase": largely supported.** Most users fall into one of these groups, and each is
   better served by Hermes or by a vendor CLI alone:
   - people who want a personal agent
   - developers who code with one agent at a time
   - anyone who needs sandboxing, Windows, or exposure to untrusted input
   - developers who want an always-on agent that can also run a moderate coding pipeline

   Hermes's Kanban is now a real coding pipeline. It has per-task worktrees, a built-in review lane, a PR gate that
   checks required CI, swarms and `/goal` judge loops, and sase lacks several of those. For these users sase adds cost:
   POSIX only, alpha, no sandbox, a large set of concepts to learn, and nothing released since 0.17.1. It adds little
   value.
3. **sase has a real role, but a narrow one.** It is the **control plane for one developer's multi-vendor fleet of
   frontier coding CLIs, working on trusted repos.** It suits someone who runs many concurrent Claude Code, Codex, Grok
   and similar agents on flat-rate subscriptions, supervises them asynchronously, often from a phone, and needs every
   change to be attributable, reviewed and landed through a governed path. That is a well-defined profile that applies
   to more people than Bryan. In that slot Hermes is not a drop-in substitute. If anything, sase is the "external CLI
   worker lane plus governance" that Hermes's own docs say it does not have.

**Recommendation:** Accept the practical advice ("most people should not bother with sase") and reject the strong
feature claim ("Hermes does everything sase does"). Position sase deliberately for the one profile above, and
consider making it *complement* Hermes rather than compete with it. See §8.

---

## 1. Method and Version Pins

**What "can do" means here.** Hermes is a general agent with a shell. In the weakest sense it can do *anything* a
person could do at a terminal, including running `claude -p`, `git commit` and `tmux`. If "can do" means "an LLM could be
prompted into it", the claim is trivially true, and also true of a bare shell. So I grade each capability on how
*Hermes the product* provides it:

| Grade | Meaning |
| ----- | ------- |
| ✅ Core | Ships in Hermes core and is on by default or set by first-class config |
| 🟡 Opt-in | Ships, but is opt-in, experimental, or in an official-tier catalog plugin |
| 🟠 Approx. | Only through a community-tier catalog plugin, or the Hermes LLM improvising with skills and its terminal (no mechanism enforces it) |
| ❌ Absent | No equivalent found |

**Version pins** (both projects move fast; check them before reusing any count):

| Project | Pin |
| ------- | --- |
| Hermes Agent | `NousResearch/hermes-agent` HEAD `1e0c7730d7` (2026-10-08). Latest stable release `v0.21.6` (2026-10-08). `rc.3-v0.21.7` was abandoned. There are 10,032 commits since the 2026-09-23 baseline. The plugin catalog has 510 entries, up from 246. |
| sase | `master` HEAD `96dd8ed270` (2026-10-09). Declared version and latest PyPI release: **0.17.1** (2026-08-29). Master is 2,259 commits past the `v0.17.1` tag, with 1,027 of them since 2026-09-23. |

**Sources.**

- Hermes code and docs: a local checkout opened with `sase repo open gh:NousResearch/hermes-agent`. In the citations
  below, `docs/` means `website/docs/` in that checkout.
- sase: this workspace's `README.md`, `docs/`, `pyproject.toml` and `src/`.
- Anthropic's billing pages, for subscription economics.
- Baseline: an earlier, separate swarm's comparison, `research:202609/sase_vs_hermes_agent/sase_vs_hermes_agent.md`.
  I re-checked every load-bearing claim from it against the October pins. That report asked "how well does sase compete
  with Hermes?" This one asks the reverse: "does Hermes make sase unnecessary?"

---

## 2. What Changed Since September That Bears on the Claim

**Hermes** (10k commits, mostly hardening, desktop, telemetry and catalog work):

- **The external-CLI Kanban lane is still unbuilt.** The text in `docs/user-guide/features/kanban-worker-lanes.md:121`
  is unchanged: wiring Codex CLI, Claude Code CLI or OpenCode CLI as a worker lane "is *not yet a paved path*". The
  historical issue #19931 is still open, and the Codex PR #19924 was "closed-not-merged".
- **Durable approvals were merged and reverted.** `e57fa350cb`, "feat(approval): a turn can hold its approval prompts
  open until answered", landed 2026-10-01 03:50. It was reverted the same day by `afc47d6e4f`, along with its CLI, TUI
  and desktop companions. Hermes clearly wants this capability. Retrofitting it onto a design where approvals block
  inside a running thread is evidently hard.
- **Kanban groundwork:** the board's columns and transitions are now stored as data, which prepares for user-defined
  workflows. `96db175da7` says itself that this is "Not consulted by the kernel yet". A new `kanban_schedule` tool was
  also added, and the PR gate now authenticates as the assignee profile's own `gh` login.
- **Codex app-server runtime:** `/model`, reasoning effort and `/fast` now pass through to the app-server.
- **Subscriptions:** a desktop chip now warns before a subscription limit is hit, and usage is reported per pooled
  credential.

**sase** (1,027 commits, all unreleased):

- **Goals ledger, stage G1** (`docs/goals.md`): person-owned outcome records. Binding goals to agents is "a later epic".
- **ToolRun control plane** (`docs/tool.md`): hand-off and detached runs, failure triage (NEW, KNOWN, FLAKY, UNKNOWN),
  and verdict receipts.
- **Plan Decisions**, with a Telegram decision keyboard.
- **Instruction bundles**, currently shadow-rendered only.
- **systemd agent scopes** that sweep leaked processes.
- Renames: xprompts became macros, and families became sessions.
- **Not added:** new providers, MCP, sandboxing, or Windows support.

Neither side closed the gaps that decide this question.

---

## 3. The Forward Test: Each sase Capability vs. Hermes

| # | sase capability | Hermes equivalent (Oct 2026) | Grade |
| - | --------------- | ---------------------------- | ----- |
| 1 | **Seven vendor coding CLIs as supervised workers**: Claude Code, Codex, Antigravity, Qwen Code, OpenCode, Muse Code and Grok Build, each run headless in its own workspace (`docs/llms.md` §Command Construction) | Codex only, through the opt-in app-server runtime, which "Hermes never auto-routes you onto" (`codex-app-server-runtime.md:10`). Claude Code is available only through an *experimental* official-tier plugin that makes the `claude` CLI a **model provider** under Hermes turns (`plugin-catalog/claude-subscription-directsdk.yaml`), or through the bundled `claude-code` skill, in which the Hermes LLM runs `claude -p` through its terminal tool with `timeout=120` (`skills/autonomous-ai-agents/claude-code/SKILL.md`). There is no Kanban lane for external CLIs (`kanban-worker-lanes.md:121`). Qwen Code and Gemini CLI: none. Antigravity: community plugins only. | 🟡 / 🟠 |
| 2 | **Multi-vendor fan-out:** one prompt goes to Claude, Codex and Grok agents at once, each in an isolated clone (`%{%m:… \| %m:…}`) | Mixture-of-Agents *merges* answers from several models into one. The community `hermes-council` plugin deliberates. Nothing fans one task out to several vendor *agent harnesses* side by side. | 🟠 |
| 3 | **Orchestration with no LLM in it.** Dispatch, waits, gates, commits and landing are deterministic Python and Rust, so the orchestration itself costs zero tokens | The Kanban dispatcher is deterministic. Decomposition (orchestrator profile, auto-decompose) and the skill route to vendor CLIs both spend tokens on Hermes's own model. | 🟡 |
| 4 | **Usage-aware cross-provider routing**: size aliases with `\|` round-robin and `\|\|` fallback, auto-disable when a provider hits its limit, an effort ladder (`docs/llms.md`) | Credential pools, rotation on "usage limit reached", reset-aware `fallback_providers`, `/usage` reading the five-hour and seven-day windows. Both systems react only after a limit is hit. | ✅ |
| 5 | **Isolated workspace per agent**: numbered full clones, rescue bundles (`docs/workspace.md`) | Per-task worktrees under `<repo>/.worktrees/<task-id>`, created by the dispatcher (`hermes_cli/kanban_db_dispatch.py`). Worktrees are good enough for most users. | ✅ |
| 6 | **Dependency-ordered launches**: `%wait` for agents or epics, `%queue`, capacity admission | Kanban `task_links`; the dispatcher promotes a task from `todo` to `ready` once its parents are done (`kanban.md:132`); `scheduled_at` delays a start. | ✅ |
| 7 | **Scheduling and follow-up on long commands**: AXE routines, `sase monitor` turns a finished command into a follow-up agent | cron with natural language or cron expressions and delivery anywhere, `/goal` with `wait <pid>` up to 30 minutes, `/loop`, `/heartbeat`. Broader than sase for user-facing schedules. | ✅ |
| 8 | **Phone and chat supervision**: Telegram plugin, Android client through the mobile gateway | 28 chat platforms, desktop, web dashboard. A superset. | ✅ |
| 9 | **Fleet operations console**: Agents tab with live diffs, retry chains, LLM Calls timeline, ToolRuns | Kanban dashboard, desktop subagent panes, community monitor plugins. Different, and adequate for most users. | 🟡 |
| 10 | **Remote dispatch**: `%dispatch:<machine>` over a tailnet into one Agents list, with remote gates (`docs/remote_dispatch.md`; v1 cannot combine with `%wait`, `%queue`, `%clan` or `%hold`) | Desktop multi-connection shows one roster, but "Sessions intentionally show one active gateway at a time". `hermes peer run`; A2A is opt-in. "Kanban is deliberately single-host" (`kanban.md:1449`). | 🟡 |
| 11 | **Host-owned completion**: agents cannot commit; a finalizer writes one Conventional Commit per dirty repo with `SASE_BEAD`, `SASE_AGENT` and `SASE_PLAN` footers; a run that leaves dirty work fails; a discarded-work guard (`docs/commit_workflows.md`; decision `host-owned-completion`) | The worker LLM commits and pushes. The `github` skill runs `git commit && git push`, and subagent worktrees are told to "Commit your changes to your branch when done" (`tools/subagent_worktree.py:202`). No provenance trailers. The community `git-hook` plugin auto-commits and *pushes* after every turn, which has different semantics. The Desktop review pane offers human commit buttons. | ❌ (🟠 via community plugin) |
| 12 | **Plan → epic → sized phases → land agent**: human plan approval, phase size picks the model, the land agent checks children's claims against the source, integrates them, and triages follow-ups (`docs/beads.md`, `docs/sdd.md`) | A flat Kanban graph with auto-decompose, swarms (workers → verifier → synthesizer), a review lane and the PR completion contract. `/plan` is "prompt-only… no engine" (`agent/plan_prompt.py:1-6`). Real plan approval exists only in the community `plan-mode` plugin. No epic or phase tier, and no integration step. | 🟠 |
| 13 | **Durable human gates that do not block**: questions, plan approval, launch approval, task triage and custom gates; asking ends the agent's turn, the answer can come days later from the TUI, CLI, Telegram or Android, and a new turn starts with a receipt (decision `gates-never-block`) | Approvals block a thread "until `/approve` / `/deny` resolves it or the approval timeout elapses" (`tools/approval_gateway_wait.py:1-10`). The default `timeout: 300` fails closed, and pending approvals live in memory. The `clarify` tool also blocks, for up to 3600 s. Durable exceptions: `kanban_block` on a card, and the community `hermes-workflows` DAG gates, which survive session end. | 🟠 |
| 14 | **Typed prompt language**: Jinja2 macros with typed inputs, launch directives (`%wait`, `%hold`, `%repeat`, `%alt`, `%dispatch`, `%auto`, …), YAML workflows with HITL steps, swarms (`docs/macros.md`, `docs/workflow_spec.md`) | Skills work as slash commands, but "String-only prompt shortcuts are not supported" (`slash-commands.md:181`). Kanban workflow templates are reserved "for v2". The community `hermes-workflows` plugin adds a JSON DAG runner. | 🟠 |
| 15 | **PR-sized work tracking**: Patches with hooks, background mentor reviewers, CRS handling of PR comments, external PR mirroring | The PR completion contract (required checks only; "no remote writes are performed by this gate", `kanban.md:67`), the `sdlc-review` reviewer card, and reading PR threads with `gh`. | 🟠 |
| 16 | **Discovered-work governance**: agents file *typed* task beads; a human triage gate decides Launch, Close or Snooze | Kanban auto-decompose plus agents creating cards. No human triage gate. | 🟠 |
| 17 | **Project memory, versioned and curated**: core memory inlined into *every* vendor's instruction file (AGENTS.md, CLAUDE.md, GEMINI.md, …), reference memory and webs (glossary, decisions) read on demand, gated writes (`docs/memory.md`) | Memory is global per profile (`MEMORY.md`, `USER.md` under `~/.hermes`) and written by the agent itself; `write_approval` is off by default. Hermes loads *one* project context file, in priority order `.hermes.md` > AGENTS.md > CLAUDE.md > `.cursorrules` (`agent/prompt_builder.py:1772`); GEMINI.md is never loaded. | ❌ |
| 18 | **Audited reads and a provenance graph**: logged reasons for memory, artifact, repo and skill reads; a typed artifact link graph; commit footers that link bead, plan and agent | Session transcripts, Kanban events, usage analytics, optional Langfuse. "There is no `read` action" for memory (`memory.md:98`). | ❌ |
| 19 | **Cross-vendor skill deployment**: one skill source rendered into the skill directories of all seven CLIs (`sase skill init`) | Skills target Hermes only. | ❌ |
| 20 | **ToolRun control plane**: recorded project checks, failure triage (NEW, KNOWN, FLAKY), verdict receipts | Nothing comparable. | ❌ |

**Tally:** 5 ✅, 4 🟡, 6 🟠, 5 ❌. Hermes core covers the *operational* half of sase: usage routing,
workspaces, dependencies, scheduling and chat reach (rows 4–8). The *governance and identity* half has no Hermes core
equivalent. Rows 2 and 11–20 are all 🟠 or ❌, and row 1 reaches 🟡 only through the opt-in Codex runtime. That half is
vendor-CLI workers, host-owned completion, epics, durable gates, curated memory and provenance.

### A note on subscription economics (row 1)

This part of the comparison changed in 2026 and is easy to get wrong.

- **sase.** It runs `claude -p` while you are signed in to your Claude plan. Anthropic's support article, updated
  2026-10-07, says `claude -p` and Agent SDK usage "still draw from your plan's usage limits". The new monthly API
  credits for Max and Team apply only when you use an API key.
- **Hermes, native Anthropic OAuth.** This path "**only works on a Claude Max plan with purchased extra usage credits**…
  Claude Pro subscribers cannot use this path" (`docs/integrations/providers.md:148`). To get through Anthropic's
  billing classifier, the adapter:
  - sends `user-agent: claude-code/<ver>` and `x-app: cli`
  - prefixes the system prompt with "You are Claude Code, Anthropic's official CLI for Claude."
  - renames Hermes's `memory` and `session_search` tools on the wire (`agent/anthropic_adapter.py:305-316, 405-411`)

  A related code comment concedes that one variant would run "against its OAuth usage policies"
  (`hermes_cli/web_server_oauth.py:166`).
- **Hermes, Claude subscription plugin.** The *experimental* `claude-subscription-directsdk` plugin is the clean
  route: Hermes turns go through the real `claude` CLI and are billed to the subscription.
- **Codex.** Parity: both systems use the ChatGPT subscription through Codex's own auth.

Hermes *can* reach subscription-priced frontier models. Doing it cleanly for Claude means an experimental plugin, and
that plugin swaps the Claude Code harness in as Hermes's model. It does not supervise Claude Code as an independent
worker.

---

## 4. The Reverse Test: What Hermes Does That sase Cannot

These are listed to be fair about scope. Every one is a capability sase **lacks by design**, and sase's README says as
much: "if you want a standalone agent instead of a coordination layer, use those CLIs directly".

- **Its own agent loop, and a lot of models.** About 40–45 model providers, including local llama.cpp, Ollama and vLLM,
  with fallback chains and credential pools.
- **Personal-agent breadth.** Voice with a wake word, browser, computer use, vision, image generation, and 28 chat
  platforms. Cron jobs can deliver to any of them.
- **Autonomous learning.** Memory and skills written by the agent, a Curator that prunes them, FTS search over past
  sessions, and optional user-model providers.
- **Containment.** Seven terminal backends: Docker, SSH, Singularity, Modal, Daytona, Vercel Sandbox and local. Also an
  egress proxy, a hardline command blocklist, a guardian LLM in the `smart` approval mode, and prompt-injection
  scanning. sase, by contrast, runs every vendor CLI with its permission bypass and sandbox switched off
  (`docs/llms.md`). Its sudo gates are beta and off by default (`docs/sudo.md:29`).
- **Coding-loop extras sase lacks:**
  - checkpoints with `/rollback` (opt-in)
  - LSP diagnostics after each edit (on by default)
  - a built-in per-task review lane
  - a PR gate that waits for required CI checks
  - `/goal` judge loops
- **Interop:** an MCP client and server, ACP for VS Code, Zed and JetBrains, an OpenAI-compatible API server, A2A, and
  a 510-entry plugin catalog.
- **Platforms:** native Windows, WSL2, macOS, Linux, Docker and Nix. sase supports Linux and macOS only.

---

## 5. Steelman: The Strongest Case *for* "Just Use Hermes"

The claim deserves its best version, and that version is strong.

1. **Hermes Kanban has become a credible coding pipeline.** It has a durable SQLite board with claims, TTLs, an
   exit-code failure taxonomy and retries. On top of that it adds automatic decomposition, a worktree per task, a review
   column that spawns an `sdlc-review` reviewer, and a PR completion contract that will not close a card until GitHub's
   required checks pass. It also has swarms with an independent verifier and synthesizer, and per-task model overrides.
   On *verification before completion*, it is arguably ahead of sase, which has no per-bead review lane and no
   required-checks gate for `#pr` Patches.
2. **The community catalog closes much of the gap, on paper.**
   - `crew`: a coordinator owns every card until a proof command exits 0, with one writer per card and an independent
     verifier.
   - `hermes-workflows`: a DAG runner whose human and machine gates survive session end.
   - `plan-mode`: plan approval.
   - `git-hook`: automatic commits.
   - `hermes-council`: multi-model deliberation.

   A motivated user can assemble something sase-shaped from these.
3. **sase's costs fall on every user, and its benefits on few.**
   - It is POSIX-only and alpha, and needs the Rust extension.
   - It has **no release since 0.17.1** (2026-08-29), so Goals, ToolRuns, Plan Decisions and the other features since
     are master-only.
   - It runs every agent with permission bypass and no sandbox.
   - Its concept surface is very large: beads, Patches, stitches, macros, clans, sessions, tribes, gates, gate turns,
     webs, artifacts and ToolRuns.
4. **Some sase guarantees are softer than they sound.**
   - Memory-write gating is mostly skill-level instruction, and the finalizer memory guard is advisory.
   - Guarded recipes are "a guardrail against habit, not a security boundary" (`docs/tool.md`).
   - Containment is the clone directory plus a systemd scope for process lifetime, not access control.
5. **Hermes covers the other 90% of what a person might want an agent for.** One tool reachable from a phone that
   triages email, runs cron jobs, browses and *also* runs a coding board is worth more to most people than one that only
   supervises coding CLIs.

For users whose coding needs are "a few background tasks on one model family, landed as PRs", the steelman wins
outright.

---

## 6. Why the Strong Claim Still Fails: Gaps of Architecture, Not Features

The remaining gaps are not a backlog that Hermes will clear by next month. Each follows from a design choice that runs
the opposite way from sase's.

1. **Who does the work.** In Hermes, *Hermes's own loop* is the worker. Vendor harnesses come in only as a runtime swap
   (Codex), as a model provider (Claude, experimental), or as a tool the Hermes LLM calls (skills). sase's premise is
   the reverse: do no agent work itself, and wrap whichever vendor harness is best at the moment. That vendor-neutrality
   is the product. A user who wants Claude Code, Codex and Grok Build working one board under one governance model has
   no paved path in Hermes. Hermes's docs describe that lane as open design work.
2. **Who owns the commit.** Hermes gives git to the LLM. sase takes it away: the agent declares, the host commits with
   provenance, and dirty or discarded work fails the run. For long-lived codebases where the question is "which agent,
   working under which plan, produced this line?", that is a guarantee, not a convenience. No Hermes plugin provides it.
   `git-hook` automates committing and pushing; it does not take ownership away from the agent.
3. **How a human is consulted.** Hermes asks synchronously: a blocked thread and a 300 s timeout that denies. sase asks
   asynchronously: a durable gate ends the turn and frees the slot, and the answer starts a new turn. One sase
   developer can supervise ten agents across a day of meetings. Hermes's approval model is built for a person who is
   watching. The 2026-10-01 add-then-revert shows Hermes wants the asynchronous model and has not been able to retrofit
   it.
4. **Whose memory it is.** Hermes memory is *about the user*, learned autonomously and kept per profile. sase memory is
   *about the codebase*: versioned in the repo, curated by humans, rendered the same way into seven vendors' instruction
   files, and read with an audit trail. Those are different products answering different questions, and neither
   substitutes for the other.
5. **The shape of the work.** Hermes has a flat task graph, plus swarms. sase has plan approval, then an epic, then
   phases whose size chooses the model, then a land agent that checks each phase's claims against the source.
   Large features need the second shape. A Hermes user can imitate it with prompts, but nothing enforces it.

Gaps 1–3 are the decisive ones. If Hermes ships **(a)** a paved external-CLI Kanban lane for at least Claude Code and
Codex, **(b)** durable asynchronous approvals in core, and **(c)** a host-side commit finalizer, the strong claim
becomes nearly true. sase's remaining edge would then be memory curation and provenance. Those are the conditions under
which to reopen this verdict.

---

## 7. Segment Analysis: Who Is "Just About Any User"?

| User profile | What they need | Best fit | What sase adds for them |
| ------------ | -------------- | -------- | ----------------------- |
| Wants a personal assistant (developer or not) | Chat reach, voice, browsing, cron, memory of *them* | **Hermes** | Nothing. sase is a different category. |
| Developer, one coding agent at a time | A strong harness | **The vendor CLI directly**, or Hermes if they want everything in one tool | Overhead outweighs value. sase's own README says so. |
| Developer who wants background coding plus chat control, a few parallel tasks, one model family, PRs as output | Task board, worktrees, review, CI gate | **Hermes Kanban** | Little. Hermes's review lane and CI gate are things sase lacks. |
| Exposed to untrusted input, or needs a security boundary, or uses Windows | Sandboxing, approvals, Windows | **Hermes** | sase is effectively ruled out: permission bypass, no sandbox, POSIX only. |
| **Developer running a sustained multi-vendor fleet**: several frontier CLIs (Claude Code, Codex, Grok Build, …) concurrently on subscriptions, on long-lived trusted repos, supervising asynchronously, landing large multi-phase work | Vendor-neutral workers, host-owned attributable commits, durable asynchronous gates, epics with verified landing, shared project memory across vendors | **sase** | The capabilities in §6. Hermes has no paved path to most of them. |

The first four rows hold most people who want "an AI agent", so the practical advice in the claim is sound. The fifth
row is not "Bryan and nobody else". It is a describable profile defined by features: anyone who has moved from "I use
an agent" to "I manage agents". Its members are the people for whom vendor lock-in, unattributable commits and blocking
approvals are daily problems.

---

## 8. Recommendation

1. **Endorse the practical claim; drop the strong one.** "Most people should use Hermes, or just a vendor CLI, and not
   bother with sase" holds up on features. "Hermes can do everything sase can" does not: 11 of the 20 sase capabilities
   I checked have no Hermes core or official equivalent. That count is generous to Hermes, because it grades row 1 as
   🟡 on the strength of the opt-in Codex runtime and the experimental Claude plugin. Phrase the argument as the first sentence, not the second.

2. **sase's realistic role is a vendor-neutral control plane for agent fleets, not an agent.** It is the layer *above*
   Claude Code, Codex, Grok Build and their successors for a developer who manages many of them at once:
   - deterministic, token-free orchestration
   - host-owned and attributable landing
   - asynchronous human gates
   - shared, audited project memory

   As vendor CLIs keep improving and multiplying, a layer that rides the best harness of the moment without rewriting
   any agent loop is valuable, and Hermes, by its architecture, is not that layer. This justifies sase as a tool for
   *a class of users*, not one person. It does not justify sase as a general alternative to Hermes, and sase should not
   present itself as one.

3. **Make the role reachable.** If sase is meant for more than its author, the feature set itself has to stop shutting
   out that class of user:
   - **Cut a release.** Everything since 0.17.1 is master-only.
   - **Offer at least an opt-in sandboxed run mode.** Today, every agent runs with its permission bypass on.
   - **Present a small "core path"** that a new user can adopt without learning the full vocabulary: workspaces,
     launch, final declaration, gates, TUI.
   - **Close the verification gaps Hermes exposed:**
     - a required-checks gate for `#pr` Patches
     - a per-bead review lane
     - in-run rollback
4. **Treat Hermes as a complement rather than a rival.**
   - Hermes's missing "external CLI worker lane plus governance" is *exactly* what sase is.
   - Hermes has a clean headless mode, `hermes chat --oneshot -q … --format stream-json` (`cli-commands.md:127-134`),
     which is the shape a `sase_llm` provider needs.
   - A user can keep Hermes as their always-on personal and chat front door and use sase for the engineering fleet.
     That is a stronger position for sase than competing on Hermes's ground, where §4 shows sase does not and should not
     try to win.

**Final verdict:**

- **Claim as stated:** refuted. Hermes cannot do everything sase can.
- **Claim as advice to most users:** supported. Most users should not bother with sase.
- **sase's role:** real but narrow. It is the governed, vendor-neutral control plane for developers who run fleets of
  frontier coding CLIs on trusted repos. That profile reaches beyond Bryan, and Hermes does not currently serve it.

---

## Sources

- **Hermes Agent**, local checkout of `NousResearch/hermes-agent` at `1e0c7730d7`. Docs paths are under `website/docs/`.
  - `user-guide/features/kanban.md`, `kanban-worker-lanes.md` and `codex-app-server-runtime.md`
  - `integrations/providers.md`, `reference/cli-commands.md` and `reference/slash-commands.md`
  - Code: `agent/anthropic_adapter.py`, `tools/approval_gateway_wait.py`, `tools/subagent_worktree.py`,
    `agent/prompt_builder.py` and `agent/plan_prompt.py`
  - `skills/autonomous-ai-agents/claude-code/SKILL.md` and `plugin-catalog/*.yaml`
  - Commits `e57fa350cb`, `afc47d6e4f` and `96db175da7`
- **sase**, at `96dd8ed270`:
  - `README.md`
  - `docs/llms.md`, `docs/workspace.md`, `docs/commit_workflows.md`, `docs/beads.md` and `docs/sdd.md`
  - `docs/notifications.md`, `docs/macros.md`, `docs/memory.md` and `docs/remote_dispatch.md`
  - `docs/sudo.md`, `docs/tool.md`, `docs/goals.md` and `docs/plugins.md`
- **Anthropic**:
  - [Use the Claude Agent SDK with your Claude plan](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan),
    update of 2026-10-07
  - [Monthly API credits for Max and Team plans](https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-and-team-plans)
  - Context on the paused June 2026 change: [Zed blog](https://zed.dev/blog/anthropic-subscription-changes)
- **PyPI**: `sase` latest is 0.17.1. The `hermes-agent` PyPI name shows 0.19.0, which may not be the official
  distribution channel.
- **Baseline**: `research:202609/sase_vs_hermes_agent/sase_vs_hermes_agent.md` (2026-09-23), read through
  `sase artifact read`. I re-verified its claims against the October pins.
