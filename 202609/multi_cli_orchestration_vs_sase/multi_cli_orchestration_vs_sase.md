# Developing One Project With Many Agent CLIs: The September 2026 Landscape vs. SASE

- **Type:** consolidated research report (lead synthesis)
- **Date:** 2026-09-21
- **Inputs:** two independent researcher reports, [cld](multi_cli_orchestration_vs_sase__cld.md)
  and [mus](multi_cli_orchestration_vs_sase__mus.md), plus the lead's own verification.
  The lead's work had three parts:
  - two targeted web-verification passes over every claim the reports disagreed on or
    sourced weakly, plus a search for competitors both reports missed;
  - `gh api` metadata and a count of the live ACP registry;
  - first-hand reads of the SASE code.
- **Question:** Which projects do an equally good or better job than SASE at letting one
  developer build a single project with several agent CLIs (Claude Code, Codex,
  Antigravity/Gemini, Grok Build, Muse Code, OpenCode, Qwen, Cursor, Copilot, …)
  seamlessly? How good is SASE really in this space?

---

## 1. Bottom line

1. **Nothing beats SASE at its whole bundle.** Several projects beat it on the parts a
   user *feels* as "seamless". SASE's bundle is:
   - provider-neutral landing;
   - routing pools that span providers;
   - one memory source for every CLI;
   - durable work state: beads, Patches, scheduler, artifacts.

   I found no project that combines all of these. SASE is below the median of serious
   competitors on four things: how many CLIs it supports, continuing a live task in a
   different CLI, interactive or visual collaboration, and adoption.
2. **The closest peers, after verification:**
   - **Maestro:** same headless integration model as SASE. Better cross-CLI handoff and
     moderated group chat.
   - **Multica** (~51k★): an issue board where many CLIs act as teammates; it auto-detects
     26 of them. *Missed by both researchers.*
   - **Orca** (~74k★): 35 CLIs, account hot-swap, and an agent-to-agent inbox.
   - **Agent Orchestrator:** per-role harnesses plus a reviewer loop.
   - **NTM + Agentic Coding Flywheel:** the closest to SASE in philosophy.
   - **Omnigent** (Databricks): a governance-first meta-harness. *Also missed by both.*
3. **The biggest strategic threat is the Agent Client Protocol (ACP), not a rival
   orchestrator.**
   - The live ACP registry lists **41 agents**. That includes **six of SASE's seven
     providers**: Claude and Codex through adapters, plus Antigravity, Grok Build, Qwen
     Code and OpenCode. Only Muse Code is missing.
   - It also covers Cursor, Copilot CLI, Factory Droid, Amp, Goose, Kimi, Junie, Cline,
     Devin, Kilo, Pi and others.
   - `session/list`, `session/resume` and `session/close` are stable, and so is a
     `usage_update` notification.
   - SASE has no ACP client. Its only ACP code is the Grok usage probe.
4. **Grade: B.** The architecture is strong and the execution uneven.
   - SASE is excellent at *launching, routing, supervising and landing* work on any of
     its providers.
   - It is mediocre at *continuing* work across providers. Handoff is a text replay, a
     quota drain restarts from scratch, and interrupts rebuild context from text.
   - Features are uneven across providers.
   - In practice, "multi-CLI" today means Claude + Codex + Grok, with Muse in the smaller
     tiers.

---

## 2. What "seamless multi-CLI development" requires

The two researchers used different rubrics: cld had ten dimensions, mus had five. They
merge into this ladder, from "can launch several CLIs" up to "several CLIs behave like
one team":

| # | Dimension | What best-in-class looks like |
|---|---|---|
| D1 | Breadth | Many CLIs, plus a generic path for new ones (ACP or "any CLI") |
| D2 | Integration depth | Structured output (headless JSON, ACP, SDK), not scraping a terminal |
| D3 | Isolation and landing | Per-agent isolation and a provider-neutral path to commit or PR |
| D4 | Shared context | One source for instructions, skills, memory and MCP, rendered for every CLI |
| D5 | Collaboration | Fan-out and compare, cross-agent review, live messaging or moderation |
| D6 | Handoff and portability | Continue a task in a different CLI without losing state |
| D7 | Routing and quota | Aliases that span providers, fallback, and awareness of accounts and quotas |
| D8 | Observability | One transcript, tool-call and usage view across all CLIs |
| D9 | Durable work state | Tasks, plans, PR lifecycle and scheduling that outlive sessions |
| D10 | Maturity and reach | Adoption, platforms, UI surfaces, stability |

---

## 3. What SASE actually does today (code-verified)

Paths are relative to the sase repo. Items marked (lead) were added or corrected by the
lead's own checks.

### Providers (D1)

- There are seven real `sase_llm` providers: `claude`, `codex`, `agy`, `qwen`,
  `opencode`, `muse` and `grok`, plus the `fakey` test provider (`pyproject.toml`).
- SASE adapts to the ecosystem fast (lead, from git history):
  - Gemini CLI was swapped for `agy` on 2026-06-19, one day after Google's consumer
    shutdown of Gemini CLI.
  - Muse Code was added on 2026-08-07, two days after Meta launched it.
  - Grok was added on 2026-08-13.
- There are no Cursor, Copilot, Amp, Factory Droid, Pi, Kimi, Kiro or Goose providers.
  There is no generic path for an arbitrary CLI.
- `sase agent-cli list/update/install` inventories, updates and installs the supported
  CLIs, showing the install script's URL and SHA-256 first (lead). Neither report
  mentioned this.

### Integration (D2)

- Every provider runs headless with structured output: `claude -p --output-format
  stream-json`, `codex exec --json`, `muse exec --json`, Grok streaming JSON,
  `opencode run --format json`, and so on.
- All of them run with approvals and sandboxes bypassed.
- Output is normalised into `live_reply.md`, a runtime-neutral `tool_calls.jsonl`,
  `usage.json` and chat transcripts.
- Interactive `sase tmux-agent` windows are "unmanaged agent CLIs, not SASE agents"
  (`docs/agent_providers.md`).

### Routing (D7): SASE's strongest multi-provider feature

- The built-in size aliases span providers (`src/sase/llm_provider/model_alias_defaults.yml`).
- The pool grammar supports `A | B` round-robin, `A || B` ordered fallback,
  `(A | B) || C` last resort, and weights.
- One effort ladder is mapped onto each CLI's own flags.
- When a provider hits its usage limit, SASE disables it machine-wide until the reset
  time the CLI reported.
- Checked by the lead:
  - `agy` appears only in `@xsmall`, and Qwen and OpenCode are in no pool.
  - `@large` and `@xlarge` are Claude/Codex/Grok only.
  - Subscription-usage collectors exist for Claude, Codex, Grok and Muse. `docs/llms.md`
    §Subscription Usage states that collection is separate from auto-disable. No routing
    path consumes the remaining-window data.

### Shared context (D4)

- `sase memory` renders one `AGENTS.md`. `CLAUDE.md`, `GEMINI.md`, `QWEN.md` and
  `OPENCODE.md` are byte-identical copies, 14,147 bytes each (lead: measured).
- Skills are authored once and deployed per provider.
- The memory semantics (core, reference and web notes, audited reads, generated webs) are
  richer than any sync tool found.
- There is **no MCP configuration anywhere** (lead: grep of `src/` and `docs/`), and no
  sync of provider-native hooks, subagents or commands.

### Collaboration (D5)

- Model fan-out (`%{%m:… | %m:…}`), xprompt swarms, `%wait`, multi-parent
  `#fork(a, b)`, and agent families, clans and tribes.
- **Mentors** are scheduler-driven automated review agents on Patches (lead; neither
  report credited them). But `MentorConfig` has no model field
  (`src/sase/config/mentor.py`), so you cannot configure "Codex reviews what Claude
  wrote".
- **There is no live inter-agent messaging.** Durable "family channels" were recommended
  in research on 2026-09-07 but have not shipped; only the `fakey` test provider mentions
  channels (lead).
- Coordination is asynchronous and scripted: waiting on artifacts, forking transcripts,
  beads.

### Handoff (D6)

- Continuing in another CLI means `#fork:<agent>` with a different `%model`. That
  injects the prior conversation as text.
- A drain "deletes the previous run's artifacts before relaunching. Any in-flight
  progress on a `RUNNING` row is lost" (`docs/llms.md` §Draining). Automatic drain is
  behind the `provider_drain` beta flag.
- Interrupts:
  - Claude's interrupt path starts a *fresh* session containing only the user's message
    (`active_session_uuid = None`), even though the same loop already passes `--resume`
    for its wait-continuation nudge (lead: `src/sase/llm_provider/claude.py`).
  - Codex rebuilds a "Work So Far" prompt under the comment "Codex has no session
    persistence" (`codex.py:478`), although current Codex supports resume.

### Isolation and landing (D3)

- Each agent gets a full numbered workspace clone.
- Completion is host-owned: the agent submits a `/sase_final` declaration and host
  finalizers do the commit. This is the same for every provider.

### Observability (D8)

The ACE TUI shows agents, retry chains, diffs, chats, artifacts, LLM calls and a usage
panel. Parity gaps reported by cld:

| Provider | Gap |
|---|---|
| Codex | no per-run `usage.json` |
| agy | no token usage; tool calls for only one pinned CLI version |
| OpenCode | no tool-call capture |
| All except Codex and Grok | no thinking capture |

### Maturity (D10)

- Alpha, POSIX-only, TUI-only.
- 94 commits under `src/sase/llm_provider` in the last 30 days (lead: re-counted).
- cld found tests heavily skewed toward Claude and Codex.

---

## 4. The landscape (verified September 2026)

Star counts come from `gh api` on 2026-09-21 unless marked "~".

### 4.1 Orchestrators that keep the vendor CLIs (direct competitors)

| Tool | CLIs | Integration | Stand-out multi-CLI features | Maturity |
|---|---|---|---|---|
| **Maestro** | 9: 3 full (Claude Code, Codex, OpenCode) + 6 beta (Droid, Copilot, Hermes, Pi, Qwen, Oh-My-Pi); no Gemini/agy yet | Headless structured JSON | **"Send to Agent"**: start in Claude Code, hand off to Codex, optionally with cleaned context. **Moderated Group Chat** with @mentions. Per-provider usage and cost dashboard | 3.4k★, AGPL, one maintainer |
| **Multica** *(new)* | 26 auto-detected (Claude Code, Codex, Cursor, Copilot, Antigravity, Grok, Qwen, OpenCode, Kimi, Kiro, Pi…) | Local daemon; headless per a third-party deep dive (Claude stream-json, `codex app-server`, ACP for a few) | Agents are assignees on an issue board: they comment, and shared skills work for every agent. Self-hostable (Compose, single binary, k8s). **No explicit cross-agent handoff** | ~51k★, created 2026-01, license not SPDX-recognised |
| **Orca** (Stably AI) | 35 in docs (27 on homepage) | GPU terminals; native chat for Claude and Codex | Fan-out and compare, "merge the winner". **Account hot-swap even mid-session** for Claude and Codex. Agent inbox mail (`dispatch`, `worker_done`, `@all`). **No cross-CLI conversation handoff** | 74.2k★, MIT, v1.4.206 (2026-09-20) |
| **Superset** | 20+ and any terminal agent | PTY plus lifecycle hooks | **"Continue with another agent"**, seeded from recent terminal output only; race agents | 14.4k★, Elastic License 2.0 (source-available) |
| **Emdash** | **35** | PTY/tmux plus hooks; ACP chat mode (unverified on its docs page) | Shared Library of skills, prompts and MCP symlinked into every agent; issue intake | 5.8k★, Apache-2.0 |
| **Agent Orchestrator** (ex-Composio, now Untrivial) | 25–27 | tmux plus native chat for Claude, Codex, OpenCode, Droid | **Per-role harnesses** (e.g. Claude orchestrates, Codex implements, a third agent reviews); CI failures and review comments routed back to the right session | ~12k★, Apache-2.0 |
| **Agent Deck** | ~11 | tmux TUI plus hooks | **Switch harness Claude ↔ Codex ↔ Pi** (PR #2237, merged 2026-09-12), carrying a readable text tail, not a native resume; Recall search; cost dashboard | 935★, MIT |
| **NTM + Agentic Coding Flywheel** | Claude, Codex, agy, Grok, Pi | tmux panes plus robot JSON/REST | Beads, **Agent Mail** with file leases, **`ntm quota` / `ntm rotate`** across seats, cass search. The closest to SASE in philosophy, spread across ~14 separate tools | ~450★ |
| **Omnigent** (Databricks) *(new)* | Claude Code, Codex, Pi, SDK agents (Cursor per repo description) | Common API: "messages and files in, text streams and tool calls out" | Switch harness with one line of YAML; OS sandbox and contextual policies; cost caps; shared live sessions. Subscription vs API-key auth not documented | 10.1k★, Apache-2.0, alpha (2026-06) |
| **Vibe Kanban** | 10 | Headless executors (ACP for some) | Compare attempts across agents; board over MCP. **Bloop shut down 2026-04-10.** Community-maintained: v0.1.45 shipped 2026-09-19 after a five-month gap | 28.2k★, Apache-2.0 |
| **Conductor** | **4** (Claude Code, Codex, Cursor since 2026-06-08, OpenCode since 2026-06-23) | Agent SDK / bundled CLIs | Several harnesses per workspace; plan handoff; config sync | Closed-source, macOS-only |
| **Gas Town** | Presets for Claude Code, Gemini CLI, Codex, Aider, plus custom; **runtime chosen per role or per task** | tmux nudges | Beads ledger, merge queue. Yegge (Aug 2026): "Gas Town effectively burned down"; he replaced it with "Wheelhouse" | 18.1k★ (gastownhall/gastown), still getting commits |
| **Claude Squad** | Claude Code, Codex, OpenCode, Amp, plus any command | tmux plus worktree | Launch several sessions and watch them; no cross-agent semantics | 8.5k★, AGPL |

**Smaller tools** (under ~3.5k★):
- **Every Code:** Codex fork with `/plan` consensus and `/code` best-of-N.
- **Nimbalyst** (ex-Crystal).
- **Agent of Empires:** ACP structured view by default, tmux fallback, containers.
- **ccmanager:** 9 CLIs over PTY, devcontainers.
- **ORCH:** 164★; task state machine plus inter-agent messaging across Claude, Codex,
  OpenCode and Cursor.
- **Kodo:** 133★; separate architect and tester agents check the work.
- **OMK:** 144★; won't mark work done without fresh evidence.
- **OpenCastle:** 62★.

**Dead, declining or not multi-CLI:**
- Coder AgentAPI: archived 2026-09-13.
- Coder Tasks: removed in v2.37.
- Omnara: pivoted to its own harness.
- Sculptor: Claude-only in containers.

### 4.2 Platform hubs and ACP

- **ACP:**
  - 41 agents in the live registry; the overview page lists about 46 including adapters.
  - `session/list`, `session/resume`, `session/close` and `session/delete` are stable,
    and so is `usage_update`.
  - The clients page lists 100+ clients.
- **Zed, JetBrains (Air), Devin Desktop and Toad** run any registered agent. Air adds
  Docker or worktree isolation. Its Claude agent needs API billing, not a subscription.
- **VS Code Agents window:** Copilot, Claude (Agent SDK) and Codex.
- **GitHub Agent HQ:** cloud-only, Claude and Codex only, still in preview.
- **Cursor 3:** runs only Cursor's own agent. It can load Claude Code hooks and skills,
  but it does not run other harnesses.
- **The hubs make breadth nearly free.** They lack durable work state, routing and
  landing.

### 4.3 Sync, portability, coordination and observability layers

- **Context sync:**
  - rulesync (61 targets: rules, ignore files, MCP, commands, subagents, skills, hooks,
    permissions).
  - Ruler (33 agents), Sentry dotagents, Vercel `npx skills`.
  - All of them only generate files; none has SASE's memory semantics.
- **Session portability, now a category of its own:**
  - **casr** converts sessions through a canonical intermediate format and writes a
    *native* session file for the target CLI.
  - **Skillsync** (YC W26, Launch HN 2026-09-17) moves "the entire session, including all
    the messages, reasoning and tool calls". Its engine, txcript, is Apache-2.0.
  - OpenAI's **codex-plugin-cc** added **`/codex:transfer`** (v1.0.5, 2026-06-23), which
    turns a Claude Code session into a resumable Codex thread. It is one-way only.
- **Coordination:** MCP Agent Mail and Beads.
- **Observability:** cass (26+ agents, including Muse and Grok Build), ccusage (18 CLIs),
  tokscale (~57 clients).

### 4.4 Contrast class: one harness, many models

**The tools:**
- **OpenCode:** 209k★, now more stars than the `anthropics/claude-code` repo's 147k.
- **Claude Code Router:** ~30k★.
- **Goose:** its "CLI providers" (claude-code, codex, gemini-cli) are now deprecated in
  favour of `claude-acp` and `codex-acp`.
- Also Aider, Kilo and Crush.

**Why they matter:** they answer "I want any model" without juggling CLIs. They give up
each vendor's tuned harness and, increasingly, subscription eligibility.

**Why this favours SASE:** wrapping the real CLIs, as SASE does, is on the right side of
this split. Anthropic's June 15 plan to move `claude -p` and Agent SDK usage to a
separate credit pool was paused that day ("nothing has changed"). No change followed
through 2026-09-21.

---

## 5. Where the researchers disagreed, and how it resolves

| Topic | cld | mus | Resolution (lead-verified) |
|---|---|---|---|
| SASE breadth | C: 7 is narrow | "Breadth with fidelity"; "only Vibe Kanban claims broader" | **cld is right on count.** Orca and Emdash support 35, Multica 26 (headless), Agent Orchestrator ~27, ACP 41. mus's fidelity point holds only against PTY tools; Maestro, Multica and ACP clients are also structured |
| Gas Town | Multi-runtime, effectively abandoned | "Claude-only, not multi-CLI" | **cld is right.** It ships presets for Claude Code, Gemini CLI, Codex and Aider, with the runtime set per role. The "burned down" quote is real, but the repo is still maintained |
| Inter-agent coordination | Swarms, `%wait`, forks: "most programmable" | "No inter-agent coordination primitive" | **Both partly right.** SASE has scripted, asynchronous coordination but no live messaging (family channels not shipped). Orca, ORCH, NTM Agent Mail and Maestro Group Chat have it |
| Conductor | 4 CLIs | 2 CLIs | **4.** Cursor and OpenCode were added in June 2026 |
| ACP registry | ~60 agents | not covered | **41** in the live registry JSON |
| Star counts | Orca 74.2k (unverified) | OpenCode ~160k, Claude Squad ~6k | Orca **74.2k confirmed**; OpenCode **209k**; Claude Squad **8.5k** |
| Vibe Kanban | Shut down, community-maintained | "Dying parent" | Both right. It still ships releases, but its momentum is gone |
| Maestro breadth | ~9–11 | not covered | **9** (3 full + 6 beta), no Gemini/agy |

**What each report missed:**
- cld missed Claude Squad, ORCH, Kodo, OMK and CCR as a lane. These are minor, except
  that Claude Squad is a useful low end.
- mus missed Maestro, Orca, Superset, Emdash, Agent Orchestrator, Agent Deck, NTM, the
  ACP hubs, and the session-portability tools. This is a material gap: they are most of
  the serious field.
- **Both** missed Multica and Omnigent.

---

## 6. Head-to-head scores

Grades A–F are relative to the best tool found on each dimension.

| Dim | SASE | Best in class | Who beats SASE |
|---|---|---|---|
| D1 Breadth | **C** | ACP hubs (41), Orca and Emdash (35), Multica (26) | Nearly every serious competitor |
| D2 Integration depth | **B+** | SASE, Maestro, Multica, ACP clients | Tied with the structured tools; ahead of PTY tools (Superset, Emdash, Claude Squad, Gas Town) |
| D3 Isolation and landing | **A−** | SASE for landing; Omnigent, Air and Agent of Empires for sandboxing | Only on sandboxing |
| D4 Shared context | **B** | rulesync (breadth), Emdash Library (MCP) | On MCP and hook sync, not on semantics |
| D5 Collaboration | **B−** | Maestro Group Chat, Agent Orchestrator reviewer roles, Orca inbox, Every Code best-of-N | On live and interactive collaboration and on role-pinned cross-provider review |
| D6 Handoff | **C** | casr / Skillsync (native, with tool calls), `/codex:transfer`, Maestro | casr, Skillsync, codex-plugin-cc, Maestro, Agent Deck |
| D7 Routing and quota | **A−** | SASE (cross-provider pools); Orca and NTM (cross-account) | Only on seat rotation and on steering by usage data |
| D8 Observability | **B** | Maestro dashboard, cass, ccusage | On consistency across providers and on cross-session search |
| D9 Durable work state | **A** | SASE; NTM + beads, Multica and Gas Town come nearest | Nobody clearly |
| D10 Maturity and reach | **D** | Orca, Multica, Vibe Kanban, Superset | Nearly everyone |

**Which projects are "equally good or better"? It depends on what you mean by
seamless:**

| If your goal is… | Better than SASE today |
|---|---|
| Talk to several CLIs and move a conversation between them | **Maestro** |
| Assign issues to many CLIs as if they were teammates, on a board, self-hosted | **Multica** (Vibe Kanban as a fallback) |
| Maximum CLI breadth plus a polished desktop plus account juggling | **Orca**, then Superset and Emdash |
| Built-in cross-CLI review loops tied to CI and PR comments | **Agent Orchestrator**; Every Code for best-of-N |
| Governance, sandboxing and shared sessions for a team | **Omnigent** (alpha) |
| Carry a full session (tool calls included) from one CLI to another | **casr**, **Skillsync**, `/codex:transfer` |
| Just run a few CLIs side by side | Claude Squad, ccmanager |
| Any *model* rather than any *CLI* | OpenCode, Claude Code Router |

**Nothing I found beats SASE on the combination of D3 + D7 + D9.** That combination is
provider-neutral landing, cross-provider routing and durable work state.

---

## 7. Critique: how good is SASE actually in this space?

### 7.1 What is genuinely strong (and rare)

1. **Provider-neutral landing is the underrated killer feature.**
   - Every provider ends through the same `/sase_final` declaration and host-owned
     finalizers, so *which CLI did the work* stops mattering to Git, Patches and review.
   - Most competitors let each CLI commit its own way, or rely on a "create PR" button.
   - This is what makes mixing CLIs in *one project* safe rather than merely possible.
2. **Cross-provider pools are a real abstraction.**
   - `@large` means the best large model on whichever of Claude, Codex or Grok has
     capacity.
   - Effort is normalised across CLIs, and a usage limit quietly reroutes work.
   - No orchestrator found has an equivalent pool grammar that spans providers. The
     nearest are model proxies (CCR) and seat rotators (NTM, Orca).
3. **One memory source with real semantics.**
   - Core, reference and web memory, audited reads, and generated decision and glossary
     webs, rendered for every CLI.
   - This is deeper than rulesync, Ruler or Emdash's symlinked library.
4. **Scriptable multi-provider pipelines.**
   - Swarms, `%{…}` fan-out, `%wait`, multi-parent forks, model-switching pipes and
     mentors turn "ask Claude and Codex, then reconcile" into a reusable xprompt.
   - This report was produced that way.
5. **Structured headless integration for every provider, plus fast adaptation.**
   - SASE never scrapes a terminal.
   - It had a Muse provider within two days of launch and `agy` within a day of the Gemini
     CLI shutdown.
   - `sase agent-cli` keeps the CLIs installed and current.

### 7.2 Where "seamless" is weaker than advertised

1. **Seven providers is narrow, and in practice it is three.**
   - SASE has no generic path. Each provider costs roughly 500–2,800 lines of bespoke
     Python.
   - The providers are not equal citizens: `agy` appears only in `@xsmall`, Qwen and
     OpenCode are in no pool, and `@large`/`@xlarge` are Claude/Codex/Grok.
   - Meanwhile ACP clients reach 41 agents through one adapter, including six of SASE's
     seven.
2. **Continuity is the weakest link, and SASE's best feature makes it worse.**
   - Routing pools deliberately spread work across CLIs. But:
     - a quota drain *discards in-flight progress* at the exact moment a provider runs
       out;
     - `#fork` replays text without tool traces;
     - Claude interrupts start a fresh session even though the code already resumes
       sessions elsewhere;
     - Codex interrupts rebuild context by hand.
   - casr, Skillsync and OpenAI's own `/codex:transfer` now move *native* sessions,
     including tool calls.
3. **Features differ by provider.**
   - Codex has no per-run token usage.
   - agy has no usage data, and its tool calls work for only one CLI version.
   - OpenCode has no tool-call capture.
   - Thinking is captured only for Codex and Grok.
   - So when a pool picks a provider, it also decides what you can observe about the run.
4. **Usage data is collected but not used for steering.**
   - Four providers have usage probes, but routing waits for a hard usage-limit error.
   - Orca, NTM and Agent Deck rotate accounts *before* the failure.
5. **No live coordination, and review is not pinned to a provider.**
   - SASE's multi-agent work is asynchronous: wait on artifacts, then fork or summarise.
   - There is no inbox, group chat or @mention. Family channels exist only as a design.
   - Mentors can't pin a model, so "have a different vendor review this Patch" is not a
     policy you can express. Agent Orchestrator makes it the default.
6. **Interactive work falls outside SASE.**
   - `sase tmux-agent` sessions are explicitly unmanaged.
   - There is no MCP sync and no hook sync.
   - A developer who wants to *drive* a CLI for part of a task leaves the system.
   - Superset, Emdash, Orca, Conductor and Multica all manage interactive or visual
     sessions.
7. **The safety posture is the same everywhere, and it is permissive everywhere.**
   - Every provider runs with approvals and sandboxes bypassed.
   - Yet SASE's blog (`docs/blog/posts/why-coding-agents-need-orchestration.md:137`)
     says users "inherit each CLI's auth, sandboxing, approval model".
   - Omnigent, JetBrains Air, Agent of Empires and Conductor Cloud offer containers or OS
     sandboxes.
8. **Reach and cost of entry.**
   - Alpha, POSIX-only, single-player and TUI-only.
   - A glossary of about 50 terms.
   - About 14 KB of core memory paid on every turn.
   - Multica (51k★), Orca (74k★) and Vibe Kanban (28k★) show the demand is real and is
     being captured by GUI or board-first tools.
9. **Squeezed from two sides.**
   - From below: single harnesses like OpenCode (209k★) keep adding providers.
   - From beside: ACP turns breadth into a commodity.
   - SASE's moat is the *union* of real-CLI fidelity, landing discipline and durable
     state. Each side narrows it.

### 7.3 Verdict

| Question | Answer |
|---|---|
| Is SASE's multi-CLI support a real value-add? | **Yes.** No single competitor matches its combination of cross-provider routing, provider-neutral landing, one memory source and durable work state. |
| Is SASE the *best* at seamless multi-CLI development? | **No.** It is best at *seamless dispatch and landing*. Others beat it on specific axes: Maestro, casr, Skillsync and codex-plugin-cc on handoff; ACP hubs, Orca, Emdash and Multica on breadth; Maestro, Agent Orchestrator and Orca on live collaboration; Orca, Multica and Superset on reach and UX. |
| Grade | **B.** The architecture is A-range and the continuity and parity are C-range. The first three fixes below would move it to A−. |

### 7.4 Highest-leverage improvements (ranked)

1. **Add a generic ACP provider plugin.**
   - One client would cover Cursor, Copilot, Droid, Amp, Goose, Kimi, Junie, Cline, Pi
     and more.
   - It would give SASE standard `session/resume` and `usage_update`.
   - It could eventually replace the bespoke Qwen, OpenCode and agy plugins.
   - Keep native plugins where the headless path is richer (Claude, Codex, Muse).
   - `src/sase/llm_provider/usage/grok.py` already speaks ACP to Grok Build for its
     billing probe.
2. **Make continuation lossless where possible.**
   - Resume native sessions on interrupt: `claude --resume` is already wired for wait
     continuations; use `codex exec resume` and ACP `session/resume`.
   - Make drain *continue* instead of restart.
   - For cross-provider forks, adopt a canonical session format that carries tool
     traces. Study casr and txcript (Apache-2.0).
3. **Enforce provider parity.**
   - Add a CI capability matrix (usage, tool calls, thinking, resume) asserted per
     provider.
   - Close the gaps in Codex token usage, OpenCode tool calls and agy usage.
4. **Steer routing with usage data.** Weight pool members by the remaining subscription
   window and rotate before failure.
5. **Ship narrow family channels, and add provider-pinned review.** Add a per-mentor or
   per-role model field, so a Patch can be reviewed by a different vendor than the one
   that wrote it.
6. **Sync MCP and hooks across CLIs.** Emit MCP configs from `sase memory init`, or
   integrate rulesync.
7. **Fix documentation drift:**
   - the blog's sandbox claim;
   - the blog's stale description of the paused Anthropic billing change;
   - the Codex "no session persistence" comment;
   - `src/sase/skills/cli_list.py`, which lists `amp` and `cursor` providers that don't
     exist;
   - the missing `mus` and `grk` suffixes in `docs/xprompt.md:2972`.

---

## 8. Method and caveats

- **SASE facts:**
  - cld read the repo through an exploration pass.
  - The lead re-checked these first-hand: the providers, the alias pools, the drain
    wording, the usage-steering wording, the Claude and Codex interrupt paths, MCP/ACP
    greps, the mentor config, the channel status, the `cli_list.py` contents, the blog
    sandbox line, the memory-file sizes, the xprompt suffix list, and the
    provider-addition dates.
- **Competitor facts:**
  - Sources were docs sites, changelogs, blogs, Launch HN, and GitHub release, issue and
    PR pages.
  - Stars come from `gh api` repo metadata.
  - The ACP count comes from the live registry JSON.
  - No repository file contents were fetched from the web.
- **Still unverified:**
  - Multica's exact integration mechanics (from a third-party deep dive).
  - Emdash's ACP mode.
  - Omnigent's auth model and its Cursor support (the repo description says yes; the
    launch blog doesn't list it).
  - Skillsync's agent count.
  - The Agent Orchestrator and NTM star counts (from cld; not re-queried).
  - Whether Muse Code is open source or will adopt ACP.
- **Scope:** this compares multi-CLI development of *one project*. General agent
  frameworks and cloud-only agents are included only as context.

## 9. Key sources

- **Researcher reports:** [cld](multi_cli_orchestration_vs_sase__cld.md) (full
  source list for Maestro, Superset, Orca, Emdash, Agent Orchestrator, Agent Deck, NTM,
  Conductor, Nimbalyst, hubs, sync tools) · [mus](multi_cli_orchestration_vs_sase__mus.md)
- **ACP:** https://agentclientprotocol.com/get-started/registry ·
  https://cdn.agentclientprotocol.com/registry/v1/latest/registry.json ·
  https://agentclientprotocol.com/rfds/updates · https://agentclientprotocol.com/get-started/clients
- **Multica:** https://multica.ai/ ·
  https://dev.to/truongpx396/multica-deep-dive-how-to-build-a-managed-agents-platform-54l2
- **Omnigent:** https://www.databricks.com/blog/introducing-omnigent-meta-harness-combine-control-and-share-your-agents
- **Maestro:** https://docs.runmaestro.ai/context-management · https://docs.runmaestro.ai/features
- **Orca:** https://onorca.dev/docs/agents/claude-code · https://onorca.dev/docs/cli/orchestration
- **Conductor:** https://conductor.build/docs/reference/harnesses · https://conductor.build/changelog
- **Gas Town:** https://github.com/gastownhall/gastown/discussions/606 ·
  https://simonwillison.net/2026/Aug/4/steve-yegge/
- **Superset:** https://superset.sh/changelog/2026-08-30-seventeen-languages-session-handoff
- **Emdash:** https://emdash.com/docs/providers
- **Vibe Kanban:** https://vibekanban.com/blog/shutdown
- **Agent Deck:** https://github.com/asheshgoplani/agent-deck/pull/2237
- **Portability:** https://news.ycombinator.com/item?id=49743049 (Skillsync) ·
  codex-plugin-cc release v1.0.5 (`/codex:transfer`, PR #374)
- **Agent of Empires:** https://www.agent-of-empires.com/docs/structured-view/
- **Goose CLI providers:** https://goose-docs.ai/docs/guides/cli-providers/
- **Cursor 3:** https://cursor.com/changelog/3-0
- **GitHub Agent HQ:** https://docs.github.com/en/copilot/concepts/agents/about-third-party-coding-agents
- **Coder:** https://coder.com/changelog/coder-2-37
- **Muse Code:** https://techcrunch.com/2026/08/05/meta-launches-muse-code-an-ai-agent-for-large-code-bases/
- **Grok Build:** https://x.ai/news/grok-build-cli
- **Anthropic policy:** https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan
- **SASE (repo-relative):** `pyproject.toml` · `src/sase/llm_provider/` (`claude.py`,
  `codex.py`, `model_alias_defaults.yml`, `load_balancing.py`, `usage/grok.py`) ·
  `src/sase/config/mentor.py` · `src/sase/skills/cli_list.py` · `docs/llms.md` ·
  `docs/agent_providers.md` · `docs/mentors.md` · `docs/xprompt.md` ·
  `docs/blog/posts/why-coding-agents-need-orchestration.md`
