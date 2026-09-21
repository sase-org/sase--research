# Multi-Agent-CLI Development of One Project: The 2026 Landscape vs. SASE

- **Researcher:** cld (one of two researchers in a swarm; written independently)
- **Date:** 2026-09-21
- **Question:** Which projects are as good as SASE, or better, at letting one developer build a
  single project with several agent CLIs (Claude Code, Codex, Antigravity/Gemini, Grok
  Build, Muse Code, OpenCode, Qwen, Cursor, Copilot, …) seamlessly? How good is SASE
  really in this space?

---

## 1. Bottom line

1. **No single project beats SASE across the board. Several beat it clearly on
   individual axes, and SASE's lead is narrower than its README suggests.** SASE is
   best-in-class at two things:
   - treating agent CLIs as interchangeable engines behind a durable, provider-neutral
     work system (workspaces, host-owned landing, beads, Patches, xprompts, scheduler);
   - cross-provider routing (size aliases that span providers, weighted and fallback pools,
     one effort ladder, usage-limit auto-disable).

   It is *not* best-in-class at the parts users feel as "seamless": how many CLIs it
   supports, continuing a live session in another CLI, side-by-side collaboration UX, and
   giving every provider the same features.
2. **The closest overall peers:**
   - **Maestro** (RunMaestro) — same integration model (headless, structured JSON). It
     beats SASE on cross-provider handoff, moderated group chat, and a usage/cost
     dashboard.
   - **Agent Orchestrator** (ex-Composio, now Untrivial) — per-role harnesses plus a
     reviewer loop across 25+ CLIs.
   - **NTM + the Agentic Coding Flywheel** — closest to SASE in philosophy: beads, agent
     mail, quota rotation.
   - **Superset** and **Orca** — they win on breadth, polish and adoption, but mostly
     integrate at the terminal (PTY) level.
3. **The biggest strategic threat is not another orchestrator. It is the Agent Client
   Protocol (ACP).** In 2026 ACP stabilised session list/resume/close, `usage_update`,
   1.0 SDKs and a registry of ~60 agents. Zed, JetBrains Air and Devin Desktop now reach
   more agent CLIs through one adapter than SASE reaches through seven hand-written
   plugins. SASE has no ACP client. Its only ACP code is the Grok billing probe.
4. **On "seamless" specifically, I rate SASE a B overall.** SASE is excellent at *launching,
   routing, supervising and landing* work on any of its seven providers. It is mediocre at
   *continuing* work across providers: handoff is a text replay, a quota drain restarts
   from scratch, and interrupts rebuild context from text. Feature parity between
   providers is uneven.

---

## 2. Rubric: what "seamless multi-CLI development" requires

I scored every tool on ten dimensions. They form a ladder from "can launch several CLIs"
up to "several CLIs behave like one team".

| # | Dimension | What best-in-class looks like |
|---|---|---|
| D1 | **Breadth** | Many CLIs, plus a generic path for new ones (ACP, or "any CLI") |
| D2 | **Integration depth** | Structured output (headless JSON, ACP, SDK), not screen-scraping a terminal |
| D3 | **Isolation and landing** | Per-agent isolation, plus a provider-neutral path to commit and PR |
| D4 | **Shared context** | One source for instructions, skills, memory and MCP, rendered for every CLI |
| D5 | **Collaboration** | Fan-out and compare, cross-agent review, moderated or consensus work |
| D6 | **Handoff and portability** | Continue a task in a different CLI without losing state |
| D7 | **Routing and quota** | Provider-spanning aliases, fallback, account/quota awareness |
| D8 | **Observability** | One transcript, tool-call and usage/cost view across CLIs |
| D9 | **Durable work state** | Tasks, plans, PR lifecycle and scheduling that outlive sessions |
| D10 | **Maturity and reach** | Adoption, platforms, maintainers, stability |

---

## 3. What SASE actually does today (code-verified)

Everything below comes from this repo. Paths are repo-relative.

**Providers (D1).** There are eight `sase_llm` entry points (`pyproject.toml`): `claude`,
`codex`, `agy` (Antigravity CLI), `qwen`, `opencode`, `muse`, `grok`, plus the `fakey` test
provider.
- The README (lines 23-25, 104-113) marks all seven real providers "Supported".
- There is no Cursor CLI, Copilot CLI, Amp, Factory Droid, Kimi, Pi, Kiro or Goose
  provider.
- The Gemini CLI provider was removed on 2026-06-19 in favour of `agy`, one day after
  Google's consumer shutdown of Gemini CLI. That was a fast adaptation.
- Muse and Grok landed in August 2026. Muse Code support is rare among competitors: I
  found it only in the cass session indexer.

**Integration model (D2).** Every provider runs headless with structured output:
- `claude -p --output-format stream-json`, `codex exec --json`, `grok … streaming-messages-json`,
  `muse exec --json`, `opencode run --format json`, and so on.
- All run with approvals and sandboxes bypassed.
- Output is normalised into `live_reply.md`, a runtime-neutral `tool_calls.jsonl` (schema
  v2, `_tool_call_common.py`), `usage.json`, and `~/.sase/chats` transcripts.
- Interactive CLIs can be opened with `sase tmux-agent`, but those windows are
  "unmanaged agent CLIs, not SASE agents" (`docs/agent_providers.md:18-21`).

**Provider abstraction.** A pluggy hookspec with 22 `firstresult` hooks
(`src/sase/llm_provider/_hookspec.py`) covers identity, model catalog, short aliases,
skill deploy path, autodetect, auth, retry, usage-limit patterns and usage probes.
- Durable routing state (disables, priorities, eligibility, effort resolution, usage
  normalisation) lives in the Rust core (`sase_core_rs`).
- The boundary leaks a little. Provider names are hard-coded in the shim list
  (`src/sase/amd/constants.py`), TUI styles, doctor hints and `skills/cli_list.py`. That
  last one still lists `amp` and `cursor`, which have no providers.

**Routing and quota (D7). This is SASE's strongest multi-provider feature.**
- Built-in size aliases span providers
  (`src/sase/llm_provider/model_alias_defaults.yml`), for example
  `@large = claude/opus@high | codex/gpt-5.6-sol@high | grok/grok-4.6@high`.
- The pool grammar supports round-robin `A | B`, ordered fallback `A || B`, last-resort
  `(A|B) || C`, and weights.
- One effort ladder (`none…max`) maps onto each CLI's own flag. An explicit effort the
  provider doesn't support raises an error; an unsupported *default* effort is silently
  skipped.
- When a provider hits its usage limit, SASE disables it machine-wide. The expiry comes
  from the CLI's reset hint, then the collected usage window, then a flat duration. Pools
  then route around the disabled provider.
- Subscription-usage probes exist for claude, codex, muse and grok.
- **Two limits:**
  - Collected usage percentages do not steer routing (`docs/llms.md` §Subscription Usage).
  - Draining a disabled provider relaunches stranded agents and discards "the previous
    run's artifacts… Any in-flight progress on a `RUNNING` row is lost"
    (`docs/llms.md` §Draining). Automatic drain is behind the `provider_drain` beta flag.

**Shared context (D4).**
- `sase memory` renders one `AGENTS.md` from `sase/memory/`. `CLAUDE.md`, `GEMINI.md`,
  `QWEN.md` and `OPENCODE.md` are byte-identical copies; Muse and Grok read `AGENTS.md`.
- Skills are authored once in `src/sase/xprompts/skills/`, rendered per provider through
  a Jinja frame, and deployed to each CLI's skills directory.
- The memory model is semantically richer than any sync tool I found:
  - core, reference and web notes;
  - audited on-demand reads;
  - generated glossary, decision and task-type webs.
- **Missing:**
  - no MCP configuration at all (no MCP references under `src/` or `docs/`);
  - no provider-native hooks;
  - no subagent, command or permission sync;
  - roughly 14 KB of core memory paid on every turn, loaded twice by Grok, which reads
    both files.

**Collaboration (D5).**
- **Model fan-out:** `%{%m:opus | %m:gpt-5.6-sol}` launches `foo.cld` / `foo.cdx`.
- **Xprompt swarms:** one agent per `---` segment. This very report comes from a
  two-researcher swarm, one Claude and one peer agent (`__mus`, presumably Muse).
- **Other building blocks:** `%wait` plus templated access to the other agents' reports;
  multi-parent `#fork:a,b` with reconcile guidance; agent families, clans and tribes;
  `sase pipe --model` to hand off to a different model.
- **Result:** very programmable, but merging is left to an LLM summariser. I found no
  dedicated side-by-side diff comparison, "merge the winner", or live moderated group chat.

**Handoff (D6).** Cross-provider continuation is `#fork:<agent>` with a different
`%model`. What carries over is the rendered chat transcript (prompts and final replies)
as text.
- There is no native session conversion.
- Interrupts rebuild a "Work So Far" prompt. Codex's comment says it "has no session
  persistence" (`codex.py`), although current Codex does support `exec resume`.
- Claude's interrupt path restarts a fresh session with only the user's message.

**Isolation and landing (D3).**
- Each agent gets a full numbered clone (`sase_<N>`), not a worktree.
- Completion is host-owned: the agent submits a `/sase_final` declaration, and host
  finalizers create the stitch or commit. All of this is provider-neutral.
- This is one of SASE's real differentiators. Most competitors leave landing to the agent
  or to a UI button.

**Observability (D8).** The ACE TUI shows agents, retry chains, per-agent diffs, chats,
artifacts, an LLM-calls panel, and a Providers · Usage panel. Parity is uneven:

| Provider | Gap |
|---|---|
| Codex | no per-run `usage.json` (`docs/llms.md` §Token Usage Tracking) |
| agy | no token usage; tool calls only for one pinned CLI version |
| OpenCode | no tool-call capture |
| Grok | usage is best-effort |
| (all but Codex and Grok) | no thinking capture |

**Maturity (D10).**
- Alpha software, POSIX-only, no GUI beyond the TUI.
- Very high churn: 509 commits under `src/sase/llm_provider` since February 2026, 94 of
  them in the last 30 days.
- Test depth is heavily skewed toward claude and codex: about 450 test files mention each,
  versus 25–98 for the others.

---

## 4. The competitive landscape (September 2026)

Two shocks shaped every tool this year:
- **Google retired Gemini CLI for consumers on 2026-06-18.** Its replacement is the
  closed-source Antigravity CLI (`agy`).
- **Anthropic's rules for using a subscription in third-party tools kept moving.** It
  blocked OAuth impersonation in January, formalised the terms in February, and announced
  an Agent-SDK/`claude -p` credit bucket for 2026-06-15. It then paused that bucket on
  June 15: "For now, nothing has changed". SASE drives `claude -p`, so it sits directly in
  this blast radius.

### 4.1 Agent-agnostic orchestrators (the direct competitors)

| Tool | CLIs | Integration | Isolation | Stand-out multi-CLI features | Maturity (approx.) |
|---|---|---|---|---|---|
| **Maestro** (RunMaestro) | ~9–11 (Claude Code, Codex, OpenCode, Droid, Copilot, Qwen, Pi, Hermes…; agy/Grok in RC) | **Headless structured JSON** (`claude --print`, `codex exec`, `opencode run`, `droid exec`) | worktree sub-agents, SSH | **"Send to Agent" moves a conversation Claude Code → Codex** (cleaned or verbatim); moderator-led **Group Chat** across Claude/OpenCode/Codex with @mentions; Cue triggers; per-provider usage and cost dashboard | ~3.4k★, AGPL, solo maintainer, v0.17/0.18-RC |
| **Superset** | 20+ and any terminal agent | PTY with lifecycle hooks; CLI, SDK, MCP | worktrees, SSH, cloud | **"Continue with another agent"** seeds from recent terminal output (their blog: "lossy by construction"); race agents; `superset:orchestrate` skill; Claude/Codex usage tab | ~14k★, ELv2 (source-available), YC, very active |
| **Orca** (Stably AI) | 27 and any CLI | GPU terminals, native chat for Claude and Codex | worktree per task, SSH | Fan-out and compare, "merge the winner"; **account hot-swap with live usage and reset times**; cross-agent search | 74.2k★ (shown on its own site), MIT, YC |
| **Emdash** (YC W26) | **35** (widest found) | PTY/tmux, lifecycle hooks for 20 providers; ACP chat mode | worktree pool, SSH | Shared **Library** of skills, prompts and MCP symlinked into every agent; issue intake from Linear, Jira, GitHub and others | ~5.8k★, Apache-2.0, cross-platform |
| **Agent Orchestrator** (ex-Composio → Untrivial) | 25–27 | tmux/ConPTY plus native chat for Claude/Codex/OpenCode/Droid | worktree per worker | **Per-role harnesses** (e.g. Claude orchestrates, Codex implements, another agent **reviews**); CI failures and review comments routed back to the owning session | ~12k★, Apache-2.0, many open bugs |
| **Agent Deck** | ~11 | tmux TUI plus hooks | worktree/jj, Docker, SSH | **Cross-harness switch** Claude↔Codex↔Pi (merged 2026-09-12; readable-text projection, tool and MCP state dropped); **Recall**: full-text search across 6 agents' transcripts; cost dashboard | ~1k★, MIT, solo, several releases a day |
| **NTM + Agentic Coding Flywheel** | Claude, Codex, agy, Grok (phase 1), Pi | tiled tmux panes, robot JSON/REST APIs | shared checkout with Agent Mail file reservations, or per-agent worktrees | Beads triage, **`ntm quota` / `ntm rotate`** across subscription seats, CASS session search, CM memory, broadcast by agent type | ~450★ (NTM), "MIT with OpenAI/Anthropic rider" |
| **Vibe Kanban** | 10 | headless executors (ACP for Gemini/Qwen, SDK for OpenCode) | worktree per attempt | Compare attempts across agents; board exposed over MCP. **Bloop shut down 2026-04-10**; now community-maintained | ~28k★, Apache-2.0 |
| **Conductor** (Melty Labs) | 4 (Claude, Codex, Cursor, OpenCode) | Agent SDK / bundled CLIs | worktrees, cloud microVMs | Several harnesses per workspace; plan handoff; "Sync Agent Configs" for skills, commands and MCP | closed source, macOS-only, $22M Series A |
| **Nimbalyst** (ex-Crystal) | Claude, Codex (prod) plus 5 alpha incl. Grok Build | SDK / app-server / ACP | optional worktrees | Workstreams of sibling sessions on different models; agent teams; AI usage report per provider | ~1.8k★, MIT |
| **Every Code** (just-every) | Codex-led, with Claude, Gemini/agy, Qwen as sub-agents | Codex fork | worktree per agent | `/plan` consensus, `/solve` race, `/code` best-of-N with auto review | ~3.7k★, Apache-2.0 |
| **Gas Town** (Yegge) | ~11 presets and any tmux CLI | tmux keystroke nudges | worktree per worker | Beads as shared ledger, mixed runtimes per role, merge queue. **Yegge (Aug 2026): "Gas Town effectively burned down."** | ~16–18k★, effectively abandoned |
| Others | Claude Squad, CCManager, Agent of Empires (ACP structured view, container sandboxes), Jean, Parallel Code (Arena), Cline Kanban, cmux, Toad (pure ACP client, stalled since May), Warp (detects 16 CLIs; full integration for ~4), Happy (remote control) | mostly PTY/tmux | worktrees | Mostly "launch several CLIs side by side" without cross-agent semantics | varies |

### 4.2 Platform hubs (vendors hosting third-party agents)

- **Zed + ACP Registry, JetBrains Air, Devin Desktop.** These are ACP *clients* that can
  run any of ~60 registered ACP agents side by side (Claude Agent adapter, Codex,
  Antigravity, Grok Build, Copilot, Cursor, OpenCode, Goose, Kimi, Qwen, Kiro, Droid…).
  - Air adds Docker or worktree isolation and runs agents in parallel.
  - Air's Claude Agent requires Anthropic Console (API) billing, not a subscription.
- **VS Code Agents window.** Three harnesses (Copilot, Claude via the Agent SDK, Codex),
  with delegation and comparison between them. Native ACP is missing.
- **GitHub Agent HQ.** Cloud Claude and Codex agents working through PRs, billed via
  Copilot. The promised Jules/Devin/xAI agents are still not shipped as far as I could
  verify.
- **Takeaway:** the hubs win on breadth-per-line-of-code thanks to ACP, and they lose on
  durable work state, routing and landing.

### 4.3 Standards and sync layers

- **AGENTS.md** is now under the Linux Foundation's Agentic AI Foundation (AAIF). Claude
  Code reportedly reads it natively when no `CLAUDE.md` exists.
- **Agent Skills (`SKILL.md`)** has 40+ clients.
- **MCP** is the universal tool layer.
- **rulesync** syncs to **61 targets**: rules, ignore files, MCP, commands, subagents,
  skills, hooks and permissions.
- **Ruler** (33 agents), Sentry's **dotagents**, and Vercel's **`npx skills`** cover
  narrower slices.
- **Relevance to SASE:** these tools reach far more agents than SASE's five shim files and
  per-provider skill deploys, but they only generate files. They have none of SASE's
  memory semantics (core vs. reference, audited reads, generated webs).

### 4.4 Coordination, portability and observability layers

- **Cross-agent coordination:**
  - **MCP Agent Mail:** agent identities, threaded inboxes, advisory file leases. Claimed
    40–50 concurrent Claude/Codex/Gemini agents on one repo.
  - **Beads:** git- and Dolt-backed agent issue tracker, ~27k★. SASE's bead system is a
    sibling concept.
  - **OpenAI's `codex-plugin-cc`** (2026-03-30): runs Codex *inside* Claude Code with
    `/codex:review`, `/codex:adversarial-review`, `/codex:rescue` and **`/codex:transfer`**,
    which exports the Claude session into a persistent Codex thread and prints a resume
    command.
  - **PAL/Zen MCP `clink`:** a CLI-to-CLI bridge, now dormant (last release Dec 2025).
- **Session portability, now a category of its own:**
  - **casr** (Cross Agent Session Resumer) converts a session into a canonical model and
    writes a *native* session file for the target CLI (Claude, Codex, Gemini, Cursor,
    Cline, Aider, Amp, OpenCode, Factory, Pi, Grok Build).
  - **Skillsync** (YC W26, launched 2026-09-17) moves messages, reasoning *and tool calls*
    between nine agents.
- **Cross-CLI observability:**
  - **cass** indexes 26+ agents' sessions, including Muse and Grok Build.
  - **ccusage** covers 18 CLIs; **tokscale** about 57 clients; **CodexBar** shows plan
    windows for 76+ providers.

### 4.5 Contrast class: multi-model single harness

OpenCode, Kilo, Goose, Crush, Xum (formerly Coder Mux), oh-my-openagent and Claude Code
Router swap the *model* under one harness. They are not multi-CLI orchestration.
- **Gain:** consistency.
- **Loss:** each vendor's tuned harness and, increasingly, subscription eligibility.
  Anthropic's terms allow the unmodified `claude` binary inside other products, but not
  third-party use of subscription OAuth.
- **Why this favours SASE:** wrapping real CLIs, as SASE does, is the strategically correct
  side of this split.

---

## 5. Head-to-head: where others beat SASE, and where SASE wins

Scores are A–F relative to the best tool found on each dimension.

| Dimension | SASE | Best-in-class | Who beats SASE here |
|---|---|---|---|
| D1 Breadth | **C** (7 CLIs; no Cursor/Copilot/Amp/Droid/Pi; no generic path) | Emdash (35), Orca/Agent Orchestrator (~27), ACP hubs (~60) | Almost everyone with PTY-level "any CLI" support, and every ACP client |
| D2 Integration depth | **B+** (structured headless for all 7; normalised tool-call schema; usage-limit strings traced to CLI binaries) | Maestro, Vibe Kanban, ACP clients | Roughly tied with Maestro. Ahead of PTY tools (Superset, Emdash, Claude Squad, Gas Town) |
| D3 Isolation and landing | **A−** (full clones plus host-owned provider-neutral finalizers; but no container sandbox and all approvals bypassed) | SASE for landing; AoE, Air, Conductor Cloud for sandboxing | Only on sandboxing |
| D4 Shared context | **B** (one memory source to all shims plus per-provider skills; rich memory semantics; no MCP/hooks/subagents/commands) | rulesync for breadth; Emdash Library for MCP and skills | rulesync, Emdash, Conductor (MCP sync) |
| D5 Collaboration | **B** (swarms, fan-out, `%wait`, multi-parent fork, families: most programmable; weakest UX) | Maestro Group Chat, Agent Orchestrator reviewer roles, Every Code consensus/best-of-N, Orca "merge the winner" | On live, interactive, UI-driven collaboration, not on scripted pipelines |
| D6 Handoff | **C** (text-replay fork; drain discards progress; interrupts rebuild from text) | casr / Skillsync (native session files), `/codex:transfer`, Maestro "Send to Agent" | casr, Skillsync, codex-plugin-cc, Maestro, Agent Deck |
| D7 Routing and quota | **A−** (cross-provider aliases, weighted and fallback pools, effort normalisation, reset-aware auto-disable, 4 usage probes) | SASE for cross-*provider* routing; NTM/Orca for cross-*account* rotation | Only on multi-account seat rotation (NTM, Orca, Agent Deck) and usage-steered routing |
| D8 Observability | **B** (unified TUI, chats, tool calls, usage panel; parity gaps for Codex tokens, agy and OpenCode) | Maestro dashboard, cass (search), ccusage/tokscale (usage) | On consistency and cross-session search |
| D9 Durable work state | **A** (beads, Patches, plans, gates, scheduler, artifacts, finalizers) | SASE; Gas Town/NTM+beads and Nimbalyst come nearest | Nobody clearly |
| D10 Maturity and reach | **D** (alpha, POSIX-only, TUI-only, one maintainer, heavy concept load, high churn) | Orca, Superset, Vibe Kanban, Emdash by adoption | Nearly everyone |

**Which projects are "equally good or better" overall?**

- **Maestro** is the closest peer by integration model. It **beats SASE on D6 and on
  interactive D5 and D8**, and loses on D3, D4, D7 and D9. For someone who mostly wants to
  *talk* to several CLIs and move conversations between them, Maestro is better today.
- **Agent Orchestrator** beats SASE on breadth and on built-in *cross-agent review
  roles* plus CI and review-comment feedback loops. It loses on routing, memory and
  stability.
- **Superset and Orca** beat SASE on breadth, UX, account and usage management, and
  adoption by one to two orders of magnitude. Their integration is shallower
  (terminal-level, lossy handoff, no provider-neutral landing).
- **NTM + Flywheel (with Agent Mail, beads and cass)** is the only stack that matches
  SASE's "durable ecosystem around interchangeable CLIs" philosophy. It is ahead on
  multi-account quota rotation and session search, and behind on routing abstraction,
  landing discipline and cohesion: it is about 14 separate tools.
- **ACP hubs (Zed, Air, Devin Desktop)** are not better at SASE's job, but they make
  *breadth* nearly free. That erodes one of SASE's claimed value-adds.

**Net:** SASE is at or near the top of the category, but only as the leader of a sub-genre:
"headless, provider-neutral, work-state-first orchestration". On the combination of
D3 + D7 + D9, I found nothing better. On D1 + D6 + D10, SASE is below the median of
serious competitors.

---

## 6. Critique: how good is SASE actually at multi-CLI development?

### 6.1 What is genuinely strong (and rare)

1. **Provider-neutral landing is the underrated killer feature.** Because every provider
   ends through the same `/sase_final` declaration and host-owned finalizers, *which CLI
   did the work* stops mattering to Git, Patches and review. Almost every competitor lets
   each CLI commit its own way, or relies on a "create PR" button. This is what makes
   mixing CLIs within one project safe rather than merely possible.
2. **Cross-provider aliases are a real abstraction, not a dropdown.**
   - `@large` means "the best available large model on whichever of claude, codex or grok
     has capacity".
   - Effort is normalised across CLIs.
   - A usage limit on one provider quietly reroutes work.
   - I found no orchestrator with an equivalent provider-spanning pool grammar. The
     nearest are model proxies (Claude Code Router) and multi-account rotators (NTM,
     Orca).
3. **One memory source feeds every agent, with real semantics.**
   - Core/reference/web memory, audited reads, and generated glossary and decision webs
     rendered into each CLI's instruction file.
   - This is deeper than rulesync or Ruler, which only copy text around, and deeper than
     Emdash's symlinked library.
4. **Scriptable multi-provider collaboration.** Swarms, `%{…}` fan-out, `%wait` with
   templated report paths, multi-parent forks and model-switching pipes turn "ask Claude
   and Codex, then reconcile" into a reusable xprompt instead of manual copy-paste. The
   research swarm that produced this report is a working example.
5. **Headless, structured integration for every provider.** SASE never scrapes a terminal.
   It gets real tool-call records, usage-limit strings traced to each CLI binary, and
   deterministic completion.
6. **Fast adaptation to ecosystem shocks.** The Gemini CLI → `agy` migration happened
   within a day of Google's cutoff, and Muse and Grok landed within weeks of release.

### 6.2 Where the "seamless" claim is weaker than advertised

1. **Seven providers is narrow for September 2026.**
   - There is no Cursor CLI, Copilot CLI, Amp, Factory Droid, Pi, Kimi, Kiro or Goose.
   - There is no generic "any CLI" or ACP path, and each provider costs roughly
     500–2,800 lines of bespoke Python plus tests.
   - Qwen and OpenCode are second-class: they are in no size-alias pool, have the fewest
     tests, and ship stale-looking default models (`anthropic/claude-sonnet-4-5`). In
     practice, "multi-CLI" today means Claude + Codex + Grok (+ Muse for small tiers).
2. **Handoff is the weakest link.**
   - Continuing work in another CLI means `#fork`: a text replay of prompts and final
     replies, without tool traces or reasoning.
   - A quota drain *discards in-flight progress and artifacts* and restarts. That is the
     opposite of seamless at exactly the moment you need it, when a provider hits its
     limit mid-task.
   - Interrupts rebuild context from text, even for CLIs with native resume. Codex's code
     comment claims no session persistence, but `codex exec resume` exists.
   - Competitors have moved on: casr and Skillsync write *native* session files for the
     target CLI, and OpenAI's own `/codex:transfer` does Claude → Codex natively.
3. **Providers don't all get the same features.**
   - Codex (the second most-used provider) records no per-run token usage.
   - agy has no usage data, and its tool calls work for only one CLI version.
   - OpenCode has no tool-call capture.
   - Thinking is captured only for Codex and Grok.
   - Only four providers have usage probes.
   - Tests concentrate on claude and codex.

   A user who switches `%model` gets a noticeably different observability experience per
   provider.
4. **Usage data is collected but not used for routing.**
   - Subscription windows are probed, but routing ignores them until a hard usage-limit
     error trips an auto-disable.
   - Competitors (Orca, NTM, Agent Deck) rotate *accounts* before failure.
   - SASE has the data to do usage-weighted pool selection and doesn't.
5. **No MCP, no hooks, no native interactive integration.**
   - Nothing configures MCP servers across CLIs, even though MCP is the de-facto tool
     layer every CLI speaks.
   - Provider-native hooks were removed.
   - Interactive sessions (`sase tmux-agent`) are explicitly unmanaged.

   So a user who wants to *drive* a CLI interactively for part of a task falls outside
   SASE entirely. Superset, Emdash, Conductor and Orca all manage interactive sessions.
6. **The safety posture is uniform, but uniformly permissive.** Every provider runs with
   approvals and sandboxes bypassed; isolation is only the workspace clone.
   - The SASE blog claims users "inherit each CLI's auth, sandboxing, approval model",
     which the code contradicts.
   - Competitors increasingly offer containers or microVMs (Agent of Empires, JetBrains
     Air, Conductor Cloud, Warp cloud).
7. **Exposure to vendor policy.**
   - SASE drives `claude -p`, exactly the path Anthropic proposed to move to a separate
     Agent-SDK credit bucket on 2026-06-15. That change was paused on June 15, but the
     SASE blog still describes it as taking effect, which is stale.
   - Google reportedly discourages third-party access to Antigravity.
   - A pure headless strategy is maximally exposed to these moves. PTY-level orchestrators
     running the unmodified interactive binary are less exposed.
8. **Reach and cost of entry.**
   - Alpha, POSIX-only, TUI-only, with a vocabulary of ~50 glossary terms (families,
     clans, tribes, shells, gates, stitches, chops…), about 14 KB of core memory paid on
     every turn, and very high churn.
   - Orca (74k★), Vibe Kanban (28k★), Superset (14k★) and Emdash have far broader
     adoption and GUI onboarding.
   - SASE's multi-CLI power is real, but mostly available to users willing to learn its
     model.

### 6.3 Verdict

| Question | Answer |
|---|---|
| Is SASE's multi-CLI support a real value-add? | **Yes.** Its combination of provider-spanning routing, one memory source and provider-neutral landing is not matched by any single competitor I found. |
| Is it the *best* at "seamless" multi-CLI development? | **No.** It is best at *seamless dispatch and landing*. Maestro and Agent Deck (handoff), the ACP hubs, Emdash and Orca (breadth), Agent Orchestrator, Maestro and Every Code (interactive collaboration), and casr, Skillsync and codex-plugin-cc (portability) beat it on specific axes. |
| Overall grade in this niche | **B** (strong architecture, uneven execution). It would be A-range with the four fixes below. |

### 6.4 Highest-leverage improvements (ranked)

1. **Add a generic ACP provider plugin.** One well-built ACP client provider would unlock
   the ~60-agent registry (Cursor, Copilot, Droid, Goose, Kimi, Kiro, Pi, Amp…).
   - It would also give SASE standardised `session/resume`, `usage_update` and tool-call
     events.
   - Keep bespoke plugins only where the native headless path is richer: Claude and Codex.
   - SASE already speaks ACP for Grok billing (`src/sase/llm_provider/usage/grok.py`), so
     the transport groundwork exists.
2. **Make handoff and drain lossless where possible.**
   - Use native resume for same-provider continuation: `claude --resume`,
     `codex exec resume`, ACP `session/resume`.
   - Adopt a canonical session model, casr-style, for cross-provider forks, carrying tool
     traces.
   - Make drain *continue* rather than restart.
3. **Close the per-provider feature gaps.** Priorities: Codex token usage, OpenCode tool
   calls, agy usage. Add a CI parity matrix test so each capability row is asserted per
   provider.
4. **Use the usage data for routing.** Pick pool members weighted by remaining
   subscription window, and rotate before failure.
5. **Sync MCP servers and rules across CLIs.** Either integrate rulesync or Ruler, or
   extend `sase memory init` to emit MCP configs. That would give D4 the breadth it lacks.
6. **Fix documentation drift.** The blog's sandbox claim and billing-change claim, the
   OpenCode tool-call docstring, the `cli_list.py` provider list, and the missing
   `mus`/`grk` suffixes in `docs/xprompt.md`.

---

## 7. Method and caveats

- **Sources for SASE:** facts came from reading this repo (code, docs, git history)
  through a read-only exploration pass, and I spot-checked the key ones myself: README
  claims, alias defaults, the drain wording, codex usage, ACP and MCP greps.
- **Sources for competitors:** two parallel web-research passes over docs sites,
  changelogs, blogs, Hacker News and GitHub release, issue and PR pages. The shared
  WebSearch budget ran out partway through, so later facts come from direct page fetches.
  - The sub-researchers opened these external repos read-only via `sase repo open` for
    README and license checks: emdash, ntm, superset, pal-mcp-server,
    coding_agent_session_search, ruler, cross_agent_session_resumer, tokscale.
  - I re-verified these claims first-hand: Maestro "Send to Agent" (Claude Code → Codex)
    and Group Chat; Superset's handoff and its "lossy by construction" note; Vibe
    Kanban's shutdown date; Orca's feature list and 74.2k★; Agent Deck PR #2237;
    `/codex:transfer`; JetBrains Air's supported agents and auth; Emdash's 35 providers;
    Yegge's Gas Town quote; Anthropic's pause of the June 15 billing change.
- **Unverified:** star counts are approximate. Items the sub-researchers marked
  unverified are excluded or explicitly hedged above, including Orca's handoff support,
  whether GitHub Agent HQ has added more partner agents, the Antigravity ACP listing,
  and Claude Code's exact AGENTS.md behaviour.
- **Scope:** I did not evaluate the `sase-research-artifacts` plugin's `#research`
  internals, and I did not consult the peer researcher's report.

## 8. Sources

**Competitor orchestrators**
- Maestro: https://docs.runmaestro.ai/context-management.md ·
  https://docs.runmaestro.ai/group-chat.md · https://docs.runmaestro.ai/usage-dashboard.md ·
  https://docs.runmaestro.ai/multi-provider.md · https://github.com/RunMaestro/Maestro/releases
- Superset: https://superset.sh/changelog/2026-08-30-seventeen-languages-session-handoff ·
  https://superset.sh/blog/switching-between-ai-coding-agents ·
  https://docs.superset.sh/agent-integration · https://docs.superset.sh/recipes/race-agents
- Orca: https://onorca.dev · https://github.com/stablyai/orca/releases
- Emdash: https://emdash.com/docs/providers · https://emdash.com/docs/skills ·
  https://emdash.com/changelog
- Agent Orchestrator: https://orchestrator.inc/docs/guides/per-role-agents ·
  https://orchestrator.inc/docs/guides/review-loop ·
  https://github.com/Untrivial-ai/agent-orchestrator/releases
- Agent Deck: https://github.com/asheshgoplani/agent-deck/pull/2237 ·
  https://github.com/asheshgoplani/agent-deck/releases
- NTM / Flywheel: https://agent-flywheel.com/flywheel ·
  https://github.com/Dicklesworthstone/ntm/releases · https://mcpagentmail.com/
- Vibe Kanban: https://vibekanban.com/blog/shutdown ·
  https://vibekanban.com/docs/supported-coding-agents
- Conductor: https://conductor.build/docs/reference/harnesses · https://conductor.build/changelog ·
  https://conductor.build/blog/series-a
- Nimbalyst: https://nimbalyst.com/blog/open-sourcing-nimbalyst ·
  https://docs.nimbalyst.com/session-management/workstreams.md
- Every Code: https://news.ycombinator.com/item?id=46401513 · https://github.com/just-every/code/releases
- Gas Town: https://simonwillison.net/2026/Aug/4/steve-yegge/ ·
  https://yegge.ai/essays/the-shape-of-things-to-come
- Agent of Empires: https://www.agent-of-empires.com/docs/structured-view
- Warp: https://docs.warp.dev/agents/cli-agents/overview
- Toad: https://batrachian.ai
- Directory of ~48 orchestrators: https://yetanotherorchestrator.app/

**Hubs and protocols**
- ACP: https://agentclientprotocol.com/get-started/registry ·
  https://agentclientprotocol.com/updates · https://zed.dev/docs/ai/external-agents ·
  https://zed.dev/blog/acp-registry
- JetBrains Air: https://www.jetbrains.com/help/air/supported-agents.html ·
  https://blog.jetbrains.com/air/2026/03/air-launches-as-public-preview-a-new-wave-of-dev-tooling-built-on-26-years-of-experience/
- Devin Desktop: https://docs.devin.ai/desktop/acp
- VS Code: https://code.visualstudio.com/docs/agents/run/agent-harnesses ·
  https://code.visualstudio.com/docs/agents/run/agents-window
- GitHub Agent HQ: https://github.blog/changelog/2026-02-04-claude-and-codex-are-now-available-in-public-preview-on-github/ ·
  https://docs.github.com/en/copilot/concepts/agents/about-third-party-coding-agents
- AGENTS.md / AAIF: https://agents.md/ ·
  https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation
- Agent Skills: https://agentskills.io/

**Sync, coordination, portability**
- rulesync: https://rulesync.dyoshikawa.com/reference/supported-tools
- dotagents: https://docs.sentry.io/ai/dotagents
- Vercel skills: https://vercel.com/changelog/introducing-skills-the-open-agent-skills-ecosystem
- Codex plugin for Claude Code: https://community.openai.com/t/introducing-codex-plugin-for-claude-code/1378186 ·
  https://dev.to/terminalblog/openai-just-shipped-an-official-codex-plugin-for-claude-code-heres-what-it-does-2577
- Beads: https://steveyegge-beads-62.mintlify.app/
- Skillsync: https://skillsync.com · https://news.ycombinator.com/item?id=49743049
- ccusage: https://ccusage.com/
- CodexBar: https://codexbar.app/

**Ecosystem policy**
- Gemini CLI to Antigravity CLI: https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/
- Anthropic Agent SDK credit (paused): https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan
- Anthropic third-party terms: https://www.theregister.com/software/2026/02/20/anthropic-clarifies-ban-on-third-party-tool-access-to-claude/5014546

**SASE (repo-relative)**
- `README.md` · `pyproject.toml` · `src/sase/llm_provider/` (`_hookspec.py`, `codex.py`,
  `model_alias_defaults.yml`, `usage/grok.py`) · `src/sase/amd/constants.py`
- `docs/llms.md` · `docs/agent_providers.md` · `docs/xprompt.md` · `docs/agent_families.md`
- `docs/blog/posts/why-coding-agents-need-orchestration.md`
