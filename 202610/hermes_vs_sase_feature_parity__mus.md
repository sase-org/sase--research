# Hermes vs. sase: Can Hermes Do Everything sase Can?

**Researcher:** mus · **Date:** 2026-10-09 · **Question:** "Hermes can do
everything that sase can, so just about any user except Bryan should not bother
with sase." Support or refute on feature sets alone (popularity/adoption
excluded), then recommend.

**Pins verified firsthand for this report:**

| Project | Pin |
| ------- | --- |
| Hermes (`NousResearch/hermes-agent`) | HEAD `1e0c7730d7` (2026-10-08) |
| sase | `0.17.1`, checkout `96dd8ed2` (2026-10-09) |

**Method.** I worked from the two checkouts and docs directly, re-verifying the
load-bearing claims myself rather than trusting earlier write-ups: Hermes's
`AGENTS.md` self-description, `website/docs/user-guide/features/kanban-worker-lanes.md`
(external-CLI lanes), `website/docs/reference/cli-commands.md` (headless mode),
`tools/approval.py` + `tools/write_approval.py` + `agent/background_review.py`
+ `tools/kanban_tools.py` (all present), `plugins/model-providers/` (42 entries)
and `plugins/platforms/` (20 entries) counts, and sase's `README.md` provider
table (7 supported CLIs) and self-description ("does not replace coding
agents"). Prior-round comparisons (2026-04, 2026-09) were used as pointers, not
as evidence. I did not run Hermes.

## 1. What each product is

**Hermes is a self-contained personal AI agent.** Its `AGENTS.md`: "Hermes is a
personal AI agent that runs the same agent core across a CLI, a messaging
gateway (Telegram, Discord, Slack, ~20 platforms), a TUI, and an Electron
desktop app. It learns across sessions (memory + skills), delegates to
subagents, runs scheduled jobs, and drives a real terminal and browser." It owns
its own LLM tool-calling loop, ~40+ model providers, a large tool surface,
terminal/browser/voice backends, autonomous memory/skill learning
(`background_review`, a skill Curator, session search), cron scheduling with
delivery to any channel, and — since 2026 — a real multi-agent layer (Kanban
board with dispatcher, `delegate_task`, `/goal` judge loops, swarms, review
lane, PR completion contracts).

**sase is a supervision and coordination layer on top of other vendors' coding
CLIs.** Its README: "One developer. A team of coding agents," and "sase does
not replace coding agents; it makes agent-driven engineering dependable." It has
no LLM loop of its own. It natively drives 7 CLIs (Claude Code, Codex,
Antigravity, Qwen Code, OpenCode, Muse Code, Grok Build), one run per numbered
workspace clone, with durable work tracking (beads: plans/epics/phases/tasks),
host-owned commits (agents never commit; host finalizers land one attributable
commit per repo), durable processless human gates (plan, question, launch
approval, typed sudo, triage, custom), a scheduler/service host, a Textual ops
TUI, and audit trails for memory/repo/artifact/skill reads.

These are different product categories that overlap in exactly one area:
**running multiple agents on real repo work under durable supervision.**

## 2. Feature comparison (feature sets only)

| Capability | Hermes | sase | Verdict |
| ---------- | ------ | ---- | ------- |
| Own agent loop (works with zero vendor CLIs) | Yes, `AIAgent` loop | No, by design | Hermes only |
| Vendor-CLI orchestration as a paved path | Docs: external-CLI Kanban lane is "*not yet a paved path*"; `spawn_fn` pluggable but integration is per-design work | 7 CLIs native, multi-model fan-out of one prompt, cross-provider size aliases | sase, decisively |
| Durable multi-agent task graph | Kanban: SQLite board, dispatcher, claims/retries, links, auto-decompose, swarms | Beads: plan→epic→sized-phase→task, dependencies, triage, `sase bead work` waves | Rough parity, sase deeper for SE |
| Plan tier + integration (land) agent | Flat graph + root card; no plan tier, no land agent | Plan approval, sized phases, verifying/integrating land agent, nested epics | sase only |
| Commit/PR ownership | Worker LLM runs git/gh itself; read-only PR completion contract | Host-owned finalizers, attributable commits, Patches, mentors | sase, structurally different |
| Per-task review lane | Built-in `review` column, auto-spawned reviewer, request-changes loop | Mentors on Patches + land-agent verification; no per-bead review lane | Hermes |
| Checkpoint/rollback in-run | Shadow-git `/rollback` (opt-in) | Clone isolation + commits; no in-run rollback | Hermes |
| Judge-driven goal loops | `/goal`, `/loop`, `/heartbeat` | `%repeat`, pipes, monitors; no judge loop | Hermes |
| Scheduling | Product-grade cron (NL + cron exprs), delivery anywhere, executions ledger | Scheduler/service host geared to engineering automation; delivery to own channels | Hermes for users; sase adequate for fleet |
| Human gating | Per-command approvals, blocking gateway round-trip, ~300 s fail-closed timeout | Durable processless gates that survive days; hash-bound commands | Different philosophies; sase for async, Hermes for per-action |
| Containment/sandboxing | Docker/Modal/Daytona/Singularity/SSH/Vercel backends, egress proxy, hardline blocklist | None; CLIs run with bypass flags, clone is the only isolation | Hermes, wide margin |
| Memory/learning | Autonomous: background review writes memory+skills, Curator, FTS session recall, user models | Curated/typed/audited project memory + webs; writes gated; no auto-learning | Hermes for assistant; sase for shared-codebase governance |
| Reusable prompts/workflows | Skills-as-slash-commands, ~58 bundled + ~150 optional, hubs, agent-authored | Typed Jinja2 XPrompts, YAML workflows (agent/bash/python/parallel/loop/HITL), swarms | sase for SE workflows; Hermes for breadth |
| Messaging/surfaces | ~28–30 channels, desktop app, web dashboard, TUI, voice | TUI ops console, CLI, Neovim/LSP, Telegram, Android; no web/desktop/voice | Hermes breadth; sase TUI deeper for fleet ops |
| Programmatic interop | OpenAI-compat API, MCP client+server, ACP, A2A, Python lib | CLI+JSON, pluggy plugins; no MCP/ACP/API server | Hermes |
| Multi-machine | Federation of installs, cloud sandboxes; Kanban itself single-host | Tailnet `%dispatch`, one Agents list, remote gates, sidecar sync (v1 limits) | Rough parity, different shapes |
| Subscription economics | Per-token default; Portal subscription | Usage-window routing, auto-disable, round-robin/fallback, effort ladder over flat-rate CLIs | sase for heavy CLI-subscription coding |
| Observability/provenance | Logs, `/usage`, `/insights`, Kanban events | Read-audit logs, telemetry DB, bead history, LLM-calls timeline | sase |
| OS support | macOS/Linux/Windows/WSL2/Termux/Docker/Nix | POSIX only | Hermes |

## 3. Testing the claim, clause by clause

**Clause A: "Hermes can do everything sase can." Refuted.** sase has at least
five capabilities Hermes lacks as a product (not as a possible DIY integration):

1. **Heterogeneous vendor-CLI orchestration as a paved path.** Hermes's own docs
   say wiring Codex/Claude/OpenCode CLIs as Kanban workers is "not yet a paved
   path." sase's entire core is this.
2. **Host-owned landing.** In Hermes the worker LLM commits and pushes; in sase
   agents cannot commit at all. No Hermes feature removes the worker's hands
   from git.
3. **Plan tier + land agent.** Hermes has no plan-approval tier, no sized
   phases selecting model aliases, and no verifying/integrating land agent.
4. **Durable processless gates.** Hermes approvals block in-process and fail
   closed after ~5 minutes; a developer away for a day loses the turn. sase
   gates are records that wait indefinitely and resume mechanically.
5. **Subscription-CLI economics.** Usage-window-aware routing across 7 flat-rate
   CLIs has no Hermes equivalent.

A fairer statement: Hermes can *approximate the overlap* (board + dispatcher +
review lane + PR contracts ≈ supervised multi-agent coding), and for
single-model, Hermes-native work that approximation is genuinely good. But
"everything sase can" is false on the features that define sase.

**Clause B: "The smart move for just about any user except Bryan is to not
bother with sase." Refuted as stated; true for a large user segment.**
The error is treating "users" as one population. Feature sets segment them:

- **Personal-assistant users** (chat from phone, inbox triage, home
  automation, voice, browser errands, scheduled briefings): Hermes wins
  outright; sase is not even applicable (~2/10 equivalent). For these users the
  claim's advice is correct.
- **Supervised multi-agent SE drivers** (epics across Claude/Codex/Grok with
  reviewable, attributable landings): sase is the stronger system (~8.5/10
  equivalent), and Hermes's missing lanes/gates/landing are disqualifying, not
  cosmetic. For these users the advice is wrong.
- **Solo single-CLI coders** who want one good harness: neither layer is
  needed; use the CLI directly. Both products are overhead.

"Except for Bryan" confuses authorship with fit: sase fits whoever runs the
second workflow, whether or not they are Bryan.

## 4. Recommendation

**Do not accept the claim. Adopt a both/and positioning:**

1. **For general personal-agent use, recommend Hermes (or its peers), not
   sase.** sase deliberately cedes layers 1–3 and 6 of the stack (model
   access, agent loop/tools, learning; surfaces). Contesting that would mean
   building a second Hermes.
2. **Keep and invest in sase as the supervised-SE control plane**, and say so
   plainly: it is the team layer above frontier coding CLIs, not a competitor
   agent. Its roadmap should deepen the five differentiators in §3, plus borrow
   four Hermes features that fit its model: per-bead review lane,
   required-checks completion gate for Patches, staged agent-proposed memory
   drafts (Hermes's `write_approval` pattern), and FTS transcript recall.
3. **Bridge, don't duplicate:** adding Hermes as an 8th `sase_llm` provider via
   its headless one-shot/stream-json mode would turn the main overlap
   competitor into a supplier, bringing Hermes's any-model/local-model loop
   under sase's workspaces, gates, and finalizers — and simultaneously fill
   Hermes's own documented external-CLI-lane gap from the other side.

## 5. sase's role for the many (not just Bryan)

**Role: the vendor-neutral supervision plane for subscription-CLI-driven
software engineering.** Concretely: the tool a developer (any developer running
2+ coding CLIs on flat-rate subscriptions) uses to fan one prompt out to
several frontier harnesses in isolated clones, track the work as
plan→epic→phases with human approvals, govern launches/escalations/landings
through durable gates, land every change as an attributable host-owned commit,
and audit all of it afterwards. Nothing in Hermes's feature set provides that
combination, and Hermes's docs concede the key gap explicitly. That role grows
more valuable, not less, as coding CLIs proliferate — because somebody has to
sit above them, and Hermes sits beside them instead.

## Caveats and sources

- I did not execute Hermes; behavior claims rest on its docs/code at the
  pinned HEAD. Its docs drift in places (config defaults vs. prose).
- Several sase capabilities are beta or flagged; remote dispatch v1 has
  documented limits (no `%wait`/`%queue`/`%clan` combined with `%dispatch`).
- Blended scores are weight-dependent; the domain split (§3, segments) is the
  robust result, not any single number.

**Sources:** Hermes checkout at `1e0c7730d7`: `AGENTS.md`,
`website/docs/user-guide/features/kanban-worker-lanes.md`,
`website/docs/reference/cli-commands.md`, `tools/approval.py`,
`tools/write_approval.py`, `agent/background_review.py`, `tools/kanban_tools.py`,
`plugins/model-providers/` (42), `plugins/platforms/` (20). sase checkout at
`96dd8ed2`: `README.md` (7-CLI table, "does not replace coding agents"),
`pyproject.toml` (0.17.1). Pointer-level context only: prior comparisons at
`202604/sase_vs_hermes_agent.md` and `202609/sase_vs_hermes_agent/`.
