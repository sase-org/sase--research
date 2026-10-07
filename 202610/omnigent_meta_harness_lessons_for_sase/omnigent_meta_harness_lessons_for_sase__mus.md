# SASE vs OmniAgent (omnigent): comparison and recommended changes

- Researcher: mus (`__mus`)
- Date: 2026-10-07
- SASE checkout: v0.17.1 (`pyproject.toml`), workspace `sase_16`
- OmniAgent checkout: `gh:omnigent-ai/omnigent` at `ee2488aee` ("Make v2 UX switcher visible (#9424)"), version `0.18.0.dev0`, Apache-2.0 license. SASE is MIT-licensed, v0.17.1.
- Sources (all independently read for this report): omnigent `README.md`, `AGENTS.md`, `docs/POLICIES.md`, `docs/AGENT_YAML_SPEC.md`, `docs/DATA_DIR_LAYOUT.md`, `feature-map/{sessions,composer}.md`, `omnigent/{harness_aliases,harness_plugins}.py`, tree listings of `omnigent/*`; sase `README.md`, `docs/{architecture,agent_providers,mobile_gateway,agent_sessions,ace}.md`, `sase memory` inventory, `sase agent --help`.
- Independence note: this report was produced without opening any peer swarm report (`__cdx`, `__cld`, `__grk`, `__gem`); only filenames were listed to avoid output collision.

## TL;DR

SASE and OmniAgent solve adjacent but different problems. OmniAgent ("Omnigent") is a
**meta-harness**: one orchestration + UI layer over many vendor CLIs and SDKs, with
sessions that follow the user across terminal, browser, phone, and desktop, plus
declarative governance (policies) and cloud-sandbox execution. SASE is an
**engineering-team coordinator**: parallel agents in isolated workspace clones, with
durable work items (Patches, beads, goals, ToolRuns), reusable prompts (macros,
workflows), memory/instruction machinery, and a review-to-PR pipeline — all
keyboard-driven from a TUI and CLI.

Neither subsumes the other. SASE's durable-work-item model (Patches/beads/goals,
stitches, mentors, triage) has no counterpart in OmniAgent and should be protected.
OmniAgent's leads worth borrowing are: portable single-file agent definitions,
declarative spend/behavior policies with ASK approvals, queue-and-steer into live
turns, user-facing session fork/clone across providers, per-feature entry-point docs,
and a community harness-plugin API. Full multi-device sync and a cloud-sandbox fleet
are the two big items I recommend *not* chasing directly; narrower slices of each
capture most of the value at a fraction of the cost.

## 1. Positioning

| | SASE | OmniAgent |
|---|---|---|
| One-liner | Structured Agentic Software Engineering: one developer supervises a team of coding agents | Open-source meta-harness for all your AI agents |
| Primary object | Work item (Patch / bead / goal / ToolRun); chats attach to work | Session (conversation); work is what happens inside it |
| Provider stance | Orchestrates installed vendor CLIs (Claude Code, Codex, Antigravity, Qwen, OpenCode, Muse, Grok Build); needs ≥1 authenticated CLI; `fakey` only for tests | Abstracts harnesses behind one layer: Claude Code, Codex, Cursor, OpenCode, Hermes, Pi, Kimi, Kiro, Goose, Devin, ACP-generic, custom YAML agents; swap/combine without rewriting |
| Client surfaces | CLI + keyboard-driven TUI; phone is a paired client via workstation-hosted mobile gateway (SSE, Rust `sase_gateway`); Neovim + Telegram plugins | Terminal CLI, browser web UI, iOS + Android apps, Electron/macOS desktop, Python/UI/web-extension SDKs, Slack integration |
| Execution | Isolated numbered local workspace clones; `%dispatch` to remote machines | Server / host / runner split; local + managed cloud sandboxes (Modal, Daytona, Blaxel, E2B, K8s, CoreWeave, Databricks, …) |
| Review/landing | Patches with lifecycle, stitches, hooks, comments, mentors, triage verdicts → PRs | No engineering review pipeline; session ends or forks |
| Collaboration | Single developer; no session sharing | Real-time sharing, co-drive, fork-to-continue, public sessions |
| Status | Alpha, POSIX-only | Alpha (`status: alpha` badge), cross-platform desktop/mobile |

The mental-model difference matters for every recommendation below: OmniAgent asks
"how do people work *with* agents everywhere?", SASE asks "how does one developer
ship *reviewed engineering work* with agents?". Features that strengthen SASE's
question are in scope; features that would turn SASE into a second OmniAgent are not.

## 2. Dimension-by-dimension comparison

### 2.1 Provider / harness coverage

OmniAgent supports a wider bench (Cursor, Hermes, Pi, Kimi, Kiro, Goose, Devin,
generic `acp:<slug>`, community entry-point plugins) plus model gateways
(Databricks, Bedrock, Vertex) and subscription auth as first-class. SASE supports
seven CLIs with a `sase doctor` readiness story, install/update automation, and
usage-limit auto-disable (hard-disable Claude for a week, Grok Build for 48h) —
operational depth over breadth. OmniAgent's `harness_capabilities` registry and
alias canonicalization (`harness_aliases.py`, `harness_plugins.py`) is the cleaner
abstraction; SASE's provider knowledge is spread across `agent_clis/` + docs +
doctor hints, with an `instruction verify` matrix that already proves per-provider
behavioral differences are real and load-bearing.

### 2.2 Client surfaces and session mobility

OmniAgent's headline is sessions that follow the user: start in terminal, continue
in browser, pick up on phone; messages, sub-agents, terminals, files stay in sync.
SASE's mobile story is deliberately thinner — the phone is a paired *client* of a
workstation gateway with a product-shaped API (no generic shell/file/RPC surface),
which is a principled security posture but means no "continue the run from the
train" equivalent. SASE's TUI is, conversely, far denser for supervision (Agents
tab, Patches view, launch control, capacity gauge) than anything in OmniAgent's
feature-map, which is chat-centric.

### 2.3 Session operations

OmniAgent's `feature-map/sessions.md` enumerates pin/reorder/rename/archive/fork/
clone/reconnect/bulk-actions with per-entry-point behavior and per-sub-feature
repro tests. Fork keeps images and elapsed time and can switch agent *or host*;
reconnect has explicit affordances for stranded runners. SASE has restart, revert,
archive, `#fork` (clan-member session forking — an internal machinery concept,
not a user "fork this onto another provider"), and runner recovery, but no
user-facing fork-across-providers or first-class stranded-runner reconnect
dialog. Each OmniAgent sub-feature names every entry point (sidebar row,
right-click, bulk selection, header menu, mobile) — a documentation discipline
SASE's TUI docs don't currently enforce.

### 2.4 Multi-agent supervision

Both mix providers: OmniAgent mixes harnesses *inside one session* (ask one agent
to review another's work, split a task across agents); SASE fans one prompt out to
parallel agents in isolated workspaces (the ACE multi-model fanout) with clan/wait
machinery (`%wait`, `%queue`, `%if`, typed launch plans). SASE's isolation model is
stronger for reviewable engineering (separate clones, diffs per agent); OmniAgent's
is stronger for collaboration between agents. Complementary, not overlapping.

### 2.5 Governance: policies vs holds/gates

OmniAgent policies are declarative gates (ALLOW/DENY/ASK) evaluated in declaration
order at three levels — session (user) → agent spec (developer) → server (admin) —
with a builtin registry (`cost_budget` with `ask_thresholds_usd`,
`max_tool_calls_per_session`), custom function modules, and approval cards in
chat. SASE's equivalents — agent holds, LaunchApproval, command-backed gates,
sudo gates, provider hard/soft disables, guarded recipes — are individually
capable but are five separate mechanisms with five separate UIs and no unified
ordering, no portable declaration, and (verified by grep across `docs/` and
`src/sase/`) **no spend-based budget**: SASE budgets are runner-capacity weights
(`max_running_agents`), never dollars. This is the single largest functional gap.

### 2.6 Reusable agent definitions

OmniAgent's `AGENT_YAML_SPEC.md`: one YAML file (harness/model/auth, prompt or
`instructions: AGENTS.md`, MCP/function/sub-agent tools, handoffs, policies,
typed `params`, `os_env`, `terminals`, async/timers) runnable via
`omnigent run path/to/agent.yaml` and installable as import bundles. SASE's
macros + workflows + instruction bundles + memory webs are more expressive for
engineering (typed inputs, directives, multi-step agent/bash/python/parallel/loop
with human checkpoints, memory-built instruction shadow manifests), but nothing
in SASE is a *single portable file* a user could hand to someone else. SASE can
express more; OmniAgent can be handed around.

### 2.7 Execution placement

OmniAgent's managed-host cloud sandboxes (ten-plus vendors) mean "no laptop
required". SASE's `%dispatch` covers remote machines but there is no disposable-
sandbox lane and no per-session host switching. SASE's workspace-clone isolation
is arguably better for git-based review; OmniAgent's is better for elastic,
device-free runs.

### 2.8 Persistence and audit

OmniAgent: single `~/.omnigent` data dir (`OMNIGENT_DATA_DIR`-relocatable),
SQLite `chat.db`, per-harness session state, artifacts dir — documented in
`DATA_DIR_LAYOUT.md`. SASE: git-portable beads, sidecar repos (plans, research,
agents, attachments), artifact refs with audited reads (`sase artifact read`),
ToolRun records, prompt MRU. SASE's model is more durable and VCS-native;
OmniAgent's is simpler and single-node. Both take audit seriously; SASE's
audited-read discipline is the deeper idea.

### 2.9 Contributor quality process

OmniAgent: PR template requiring Summary/Test Plan/Demo (video/images for UI
changes)/coverage checkboxes/release-notes verdict; `feature-map/*.md` per
feature with entry points + repro-environment commands; `just` recipes;
pre-commit gate; DCO. SASE: two-speed CI (fast per-SHA gate + scheduled full
matrix), symvision lint, decision records, lint-and-test memory gate. Both are
strong; OmniAgent's per-feature *user-entry-point + repro* documentation contract
is the piece SASE lacks, and SASE's immutable decision records are the piece
OmniAgent lacks.

## 3. What SASE should protect (do not trade away)

- Patches/beads/goals/ToolRuns as durable, git-portable work items with a
  review-to-PR pipeline. OmniAgent has nothing like this; it is SASE's moat.
- Memory webs + instruction bundles + `sase instructions verify` (prove what
  each provider actually loaded, from the provider's own records).
- The paired-client mobile posture (product-shaped API, no generic shell/RPC).
  OmniAgent's richer device sync is convenient but widens the attack surface;
  any sharing work in SASE should preserve the narrow-API principle.
- Single-turn agent contract, typed launch plans, clan/wait machinery.
- Decision records and the Rust-core boundary for deterministic operations.

## 4. Ranked recommendations

Ordered by (value to SASE's mission) ÷ (cost + risk). Each item names the
OmniAgent source, the concrete SASE-shaped proposal, and the main risk.

### 1. Unified declarative policy layer with spend budgets and ASK approvals

Source: `docs/POLICIES.md` (ALLOW/DENY/ASK, three evaluation levels, builtin
`cost_budget` + `ask_thresholds_usd`).
Proposal: converge holds, LaunchApproval, sudo gates, provider disables, and
guarded recipes behind one ordered policy declaration (session → macro/agent →
server config), and add the missing primitive — a **dollar budget** per
patch/goal/session with ASK thresholds. SASE already tracks LLM calls; attach
cost accounting and enforce `DENY`/`ASK` at launch admission next to the
existing capacity check. Surface approvals as command-backed gates (which SASE
already has) so no new UI paradigm is needed.
Risk: moderate — touches admission, the most load-bearing path; gate behind a
flag and start with monitor-only (log, don't deny) policies.

### 2. Portable single-file agent/macro bundle (import + export)

Source: `docs/AGENT_YAML_SPEC.md`, composer import-bundle (`.tar.gz` install).
Proposal: `sase macro export <name> -o bundle.tgz` / `sase macro import`,
packaging prompt text, typed inputs, referenced memory strands, workflow steps,
and policy declarations with a versioned manifest. This gives SASE OmniAgent's
hand-around-ability without surrendering macro expressiveness, and creates a
natural interchange point between the two ecosystems later.
Risk: low — additive; main work is reference-closure (strand/artifact
resolution) and a schema version.

### 3. Community provider-plugin API via entry points

Source: `omnigent/harness_plugins.py` (builtin contribution + community entry
points, capability registry, alias canonicalization).
Proposal: let third parties register provider CLIs (install/auth/launch/parse
contract) without touching `src/sase/agent_clis/`, reusing the `sase doctor`
hint interface as the conformance surface. SASE already ships plugins
(`sase-github`, `sase-telegram`); extend the pattern to providers so breadth
can grow without core-team bandwidth.
Risk: low-moderate — needs a capability contract (which providers support
effort levels, resumption, etc.; SASE's `instruction verify` matrix is the
seed data).

### 4. Queue-and-steer into live turns + stranded-runner reconnect

Source: `feature-map/composer.md` (`queue-and-steer`, `delivered-send-recovery`),
`feature-map/sessions.md` (`reconnect`, `message-recovery`).
Proposal: allow follow-up prompts to queue onto a *running* agent (steer vs
wait choice) instead of only blocking on `%wait`/terminal state, and add a
first-class reconnect affordance for stranded runners (SASE has `drain` for
hard-disabled providers; generalize to any lost runner with the exact resume
command shown). Both fit the existing Agents tab + notifications with no new
surface.
Risk: moderate — steering changes prompt-assembly timing; reconnect needs
per-provider resume commands inventoried.

### 5. User-facing fork/clone across providers

Source: `feature-map/sessions.md` (`fork`, `fork-custom-agent`, `clone`).
Proposal: one action — fork this agent's session (whole or from a message)
onto a *different provider/model*, keeping prompt, files, and elapsed context
— as the review-loop primitive ("have Codex redo this with Claude judging").
SASE's `#fork` machinery and multi-model fanout are the building blocks; what's
missing is the single user gesture plus provider-switch at fork time.
Risk: low-moderate — mostly TUI/CLI wiring over existing relaunch paths.

### 6. Feature-map-style per-surface documentation contract

Source: `feature-map/*.md` + PR template (Summary/Test Plan/Demo/Release-notes).
Proposal: for each TUI surface, document every entry point (as OmniAgent does:
row menu, header menu, bulk selection, mobile gateway, CLI equivalent) plus a
repro command. Start with Agents tab + Patches view. Adopt the Demo-evidence
habit for TUI changes (short screen recording linked from the Patch, matching
SASE's existing demo culture in `demos/`).
Risk: low — docs-only; enforce lightly via the existing lint-and-test memory
note rather than a hard gate.

### 7. Model/effort/permission picker parity in launch control

Source: `feature-map/composer.md` (pill, tooltip, pickers, refused-switch
states).
Proposal: make SASE's launch control show one consistent harness/model/effort/
permission readout with the same refused-change semantics OmniAgent specifies
(the pill keeps the applied model on refusal). SASE already surfaces provider
routing and disables; this is presentation convergence, and it kills a class
of "I thought I launched with X" confusion.
Risk: low — UI-only.

### 8. Attachment admission controls for agent uploads

Source: `docs/POLICIES.md` attachment admission section (per-type size/count
caps, denylist, no content sniffing claims).
Proposal: adopt explicit per-type upload caps for files entering agent
workspaces via chat/gateway/attachments, documented as filename-based limits
with the same honesty OmniAgent shows about what is *not* inspected. Small,
unglamorous, and the kind of thing that prevents a real incident.
Risk: low.

### 9. One disposable-sandbox execution lane (pilot, not fleet)

Source: managed hosts / cloud-sandbox providers; `git_worktree.py` host support.
Proposal: add exactly one sandbox backend (whichever is cheapest to operate)
as an alternative to a numbered local clone for short, untrusted runs —
explicitly a pilot. Do not build OmniAgent's ten-vendor fleet; SASE's
workspace-clone + `%dispatch` model covers the core, and fleet breadth is pure
maintenance surface.
Risk: high if expanded beyond a pilot — hence the ranking. Revisit only if the
pilot shows device-free or untrusted-execution demand SASE can't otherwise meet.

### 10. Read-only share links for sessions/Patches (no co-drive yet)

Source: session sharing / public sessions / co-drive.
Proposal: read-only, revocable links to a Patch or agent transcript for
reviewers, served through the existing mobile-gateway narrow API — *not*
multi-user co-drive, which contradicts SASE's single-developer model and its
security posture. Captures most collaboration value (someone can see and
comment) with none of the concurrent-control machinery.
Risk: moderate — auth/token lifecycle; keep read-only and expiry-capped.

## 5. Explicit non-recommendations

- Do not rebuild OmniAgent's multi-device live sync or desktop Electron shell;
  the TUI + paired-client gateway is the right scope for a POSIX engineering tool.
- Do not adopt subscription-auth brokering or model gateways; SASE's
  bring-your-own-CLI stance is simpler and matches its audience.
- Do not replace beads/Patches with a SQLite chat store; git-portability is a
  feature, not legacy.

## Appendix: verification notes

- OmniAgent version/license from `pyproject.toml` (`0.18.0.dev0`) and
  `README.md` badges; HEAD `ee2488aee` from `git log`.
- OmniAgent harness breadth from `omnigent/harnesses/` (15 entries incl.
  `acp_*`, native CLIs) and `harness_plugins.py` builtin contribution.
- SASE provider set (7 CLIs + `fakey`) from `docs/agent_providers.md` and
  `README.md` quickstart; auto-disable durations from the same page.
- Absence of spend budgets in SASE verified by grepping `docs/*.md` and
  `src/sase/*.py` for `max_cost|cost_budget|spend` (only runner-capacity and
  render budgets match); `sase agent --help` confirms no budget subcommand.
- SASE `#fork`/queue semantics from `docs/agent_sessions.md` and `docs/ace.md`:
  fork is clan-member machinery, queue is admission-capacity — neither is the
  user-facing OmniAgent counterpart, grounding recommendations 4–5.
