# Comparing SASE and Omnigent

**Researcher:** grk (independent swarm member)
**Date:** 2026-10-07
**Question:** How does SASE compare with Omnigent, and which Omnigent ideas are worth adopting in SASE?
**Naming:** The request used “omniagent.” The repository at `https://github.com/omnigent-ai/omnigent` is **Omnigent** (CLI aliases `omnigent` / `omni`). This report uses that product name.

## Sources and revisions

Primary evidence is local checkouts opened through `sase repo open`, plus GitHub metadata and public product pages. Peer swarm reports were not read.

| Tree | Path | HEAD | Version |
| --- | --- | --- | --- |
| SASE (this workspace) | workspace primary | `6e2bc57726` (2026-10-07) | PyPI/package `0.17.1`, tag `v0.17.1` |
| sase-core | `sase/repos/linked/sase-core` | `d2a56b4c` (2026-10-07) | tag `v0.37.0` |
| Omnigent | `sase/repos/external/gh/omnigent-ai/omnigent` | `ee2488aee` (2026-10-07) | package `0.18.0.dev0`, tag `v0.4.0.dev0` |

Public GitHub metadata on 2026-10-07 (`gh api repos/...`):

| Repo | Created | Stars | Forks | Open issues | License |
| --- | --- | --- | --- | --- | --- |
| `sase-org/sase` | 2026-03-14 | 5 | 1 | 4 | MIT |
| `omnigent-ai/omnigent` | 2026-06-11 | 10,651 | 1,707 | 1,843 | Apache-2.0 |

Omnigent also ships a React/Electron/iOS/Android client tree (`web/`), 2,404 Python test files, 12 native harness packages, and a FastAPI server with a committed `openapi.json`. SASE’s Python host has ~5,144 `test_*.py` files plus a required Rust core (~975 `.rs` files in the linked checkout). Commit volume on this SASE clone is ~15,753 vs ~4,543 on Omnigent: SASE is denser in work-state machinery; Omnigent is denser in product surface area.

External pages used for product positioning only: [omnigent.ai](https://omnigent.ai/), the Databricks-adjacent launch writeups, and Omnigent’s own README/docs in the checkout.

---

## 1. Executive judgment

These products sit at the **same layer of the stack** and solve **different jobs**.

Both wrap existing coding-agent CLIs (Claude Code, Codex, OpenCode, Antigravity, Qwen, Grok Build, and others) rather than replacing the model. Both add scheduling, multi-agent fan-out, a control surface, and some form of approval. Both are alpha.

The split is the unit of durability:

- **Omnigent’s unit is the live session.** A runner wraps a vendor harness in a sandboxed, uniform session. A server holds history, policies, and sharing. Humans join, steer, fork, and watch from terminal, browser, desktop, or phone while the vendor TUI is still running.
- **SASE’s unit is the work record.** A numbered workspace clone, a bead/Patch/goal/artifact graph, a single provider turn, and host-owned completion. Humans supervise from the TUI, Telegram, or the mobile gateway. Continuation is mechanical (monitor, gate, successor) rather than a promise that the same process will keep chatting.

Omnigent is a **meta-harness**: one control plane over many harnesses, with policies and collaboration at the session layer. SASE is an **operating layer for software engineering**: git-portable intent, isolated workspaces, reviewable patches, and a single-turn agent contract.

Copying Omnigent’s live-session model into SASE would undo decisions that already pay rent (`single-turn-agents`, `host-owned-completion`, `adapters-normalize-harnesses`, file-backed SDD). The high-value imports are the pieces Omnigent built **because** wrapping many harnesses is messy: a declared capability matrix with a live bench, OS sandboxing plus secretless credential proxying, stateful spend/tool policies that pause for a human, multi-surface feature maps, and a drain-then-upgrade install story.

---

## 2. What each product is

### 2.1 Omnigent

From `README.md` and `docs/AGENT_YAML_SPEC.md`:

> A common orchestration layer over Claude Code, Codex, Cursor, OpenCode, Hermes, Pi, and the agents you write yourself: swap or combine harnesses without rewriting, enforce policies and sandboxing, and collaborate in real time from any device.

Architecture (README + `omnigent/host/`, `omnigent/runner/`, `omnigent/server/`):

1. **Runner** — wraps one agent in a sandboxed session with a uniform API. Owns MCP dispatch, tool-call policies, native TUI bridges, and sub-agent fan-out (`sys_session_send`, `sys_session_create`).
2. **Server** — SQLite `chat.db` under `~/.omnigent` (`docs/DATA_DIR_LAYOUT.md`), policies, sharing, automations, REST/OpenAPI, web UI on `:6767`.
3. **Host** — a machine that can run sessions (`omnigent host`). Local laptop, LAN phone, or a cloud sandbox (Modal, Daytona, Blaxel, E2B, Kubernetes, Databricks, …).

Agents are **YAML specs**: prompt/instructions, executor harness+model+auth, tools (MCP, Python, `type: agent` sub-agents), policies, `os_env` sandbox, terminals. Framework-owned lifecycle instructions are appended at runtime in `omnigent/runtime/prompt.py` and are explicitly *not* part of the portable spec (`AGENTS.md` in the Omnigent repo).

Two integration styles coexist (`omnigent/harness_capabilities.py`):

- **SDK / ACP / CLI-subprocess** — in-process or per-turn vendor APIs (`claude-sdk`, `codex`, `antigravity`, `grok`/`devin` over ACP).
- **Native TUI** — tmux/PTY wrappers (`omnigent claude`, `omnigent codex`, …) with bubblewrap (Linux, mandatory) or seatbelt (macOS).

Example agents: **Polly** (orchestrator that writes no code, delegates to vendor CLIs in worktrees, routes each diff to a different-vendor reviewer), **Debby** (two-model debate), **Deep Research** (cited report via MCP search).

### 2.2 SASE

From `README.md` and `docs/architecture.md`:

> One developer. A team of coding agents. Tracked, reviewable, repeatable work.

Architecture:

1. **Python host** — CLI, TUI, macro expansion, workflows, launch, provider adapters, AXE/scheduler, plugins.
2. **Rust core (`sase-core`)** — required for parsing, query, notifications, agent scan, launch admission, beads, goals, mobile gateway. No Python fallback (`rust-core-required`).
3. **Sidecars** — agents, plans, research, beads, attachments. Work state lives in files and git, not in a chat database.
4. **Numbered workspaces** — isolated clones of the project primary, claimed by one agent until completion, usually sharing the primary object database via git alternates.

A SASE agent is **one provider turn** (or a session of turns joined by monitors and gates). The LLM provider contract is `invoke(prompt) -> InvokeResult` (`src/sase/llm_provider/base.py`). Adapters make vendor CLIs obey that single-turn contract. Host finalizers commit, close beads, and archive. Native helpers return to their parent; only roots declare (`helpers-return-roots-declare`).

The durable objects are the product: **Macros**, **Beads**, **Patches**, **Goals**, **Artifacts**, **ToolRuns**, **Memory** (core / reference / webs), **Gates**, **AXE jobs**, **instruction-bundle manifests**.

---

## 3. Side-by-side

### 3.1 Stack position

| Concern | SASE | Omnigent |
| --- | --- | --- |
| Self-description | Structured Agentic Software Engineering; orchestration around CLIs | Meta-harness; common layer above CLIs and YAML agents |
| Durable unit | Workspace + bead/Patch/goal/artifact | Conversation/session in `chat.db` plus artifact dirs |
| Agent process model | One-shot `invoke`; mechanical continuation | Long-lived session; mid-turn steer where the harness allows |
| Control surface | Keyboard TUI first; Telegram; loopback mobile gateway | Web first; Electron desktop; iOS/Android; REPL; Slack |
| Backend language | Python host + required Rust core | Python server/runner + TypeScript web + Kotlin/Swift |
| Isolation | Git workspace clones; process detach into systemd scopes | OS sandbox (bwrap/seatbelt) + L7 egress proxy + cloud VMs |
| Auth/collab | Single-operator local; fleet enrollment via Tailscale + bootstrap secret | Multi-user accounts, OIDC, invite links, live session share/co-drive/fork |
| Scheduling | AXE / service host / named procs / monitors | Automations (`scheduled-tasks`, RFC 5545 RRULE) with per-run cost cap |
| Policy | Gates, holds, sudo, launch approval, usage-limit auto-disable | ALLOW/DENY/ASK at request, tool_call, tool_result, response |
| Work graph | Beads, epics, plans, Patches, stitches, goals | Sessions, PRs observed on the runner, YAML sub-agents |
| Instruction story | Memory-built bundles + shadow manifests (E2); per-provider verify | Portable YAML prompt + framework-owned append; `InstructionDelivery` enum |

### 3.2 Provider / harness coverage

SASE built-in `sase_llm` providers (`docs/plugins.md`): Claude, Codex, Antigravity (`agy`), OpenCode, Qwen, Muse, Grok. Cursor/Hermes/Pi/Devin/Kiro/Copilot are absent as first-class adapters. `sase tmux-agent` can launch unmanaged vendor TUIs; those runs are *not* SASE agents.

Omnigent native packages under `omnigent/harnesses/`: `claude_native`, `codex_native`, `cursor_native`, `opencode_native`, `pi_native`, `qwen_native`, `antigravity_native`, `hermes_native`, `goose_native`, `kimi_native`, `kiro_native`, `devin_native`. SDK/ACP ids include `claude-sdk`, `openai-agents`, `copilot`, `grok`/`grok-build`. Community harnesses load through `omnigent.community.harness` entry points (`designs/harness-plugin-interface.md`).

Both treat Grok Build as ACP-shaped and credential-owned by the vendor CLI. Omnigent refuses `--model` on that path rather than silently dropping it (README). SASE already has a full Grok adapter plus usage-limit auto-disable.

### 3.3 The capability problem both hit

Wrapping N vendor CLIs produces implicit `if harness == "x"` branches. Omnigent named this and started paying it down:

`HarnessCapabilities` (`omnigent/harness_capabilities.py`) declares, per harness:

- `integration_mode` (sdk-in-process / cli-subprocess / acp-subprocess / native-tui / native-server)
- `elicitation` (how ASK reaches the UI: hook, jsonrpc, approval-mirror, sse-permission)
- `resume`, `effort` family, `model_family`, `auth`
- `subagents`, `interrupt`, `streaming`, `steering`, `live_queue`, `images`, `compaction`
- `fork_history`, `instruction_delivery`

The **harness bench** (`docs/harness-bench-design.md`) is an executable conformance suite: live probes, `DRIFT` when a declaration disagrees with observed behavior. Status in-tree: shipped, with P0 probes already catching declaration drift.

SASE has the same problem in a different costume. `docs/agent_providers.md` already publishes a per-provider helper-coverage table (Claude has a PreToolUse guard; Codex inherits process-level developer instructions; Grok subagents get nothing; Muse/agy have no helper coverage) and `sase instructions verify` scoreboard. Instruction delivery is still E2 *shadow only* (`docs/instruction_bundles.md`): the bundle is recorded, not delivered. Provider adapters still encode wait/steer/sync-ceiling behavior as one-off subprocess parsers (`src/sase/llm_provider/_subprocess_*.py`).

This is the highest-leverage overlap.

### 3.4 Policy and human pause

**Omnigent policies** (`docs/POLICIES.md`, `omnigent/policies/`, `omnigent/runner/policy.py`):

- Verdicts: ALLOW, DENY, ASK.
- Layers: session (first), agent spec, server-wide (last). DENY short-circuits.
- Phases: request (before the LLM turn), tool_call, tool_result, response.
- Builtins: `cost_budget` (soft ASK thresholds + hard “downgrade off expensive models”), max tool calls, GitHub write-repo/branch, Google Drive, working-dir, CEL expressions, risk score, routing.
- ASK elicitation is dual-evaluated: runner fast-path for ALLOW/DENY, server owns the human channel (`pending_approvals`).
- Unpriced models fail **closed** on the cost gate: missing `total_cost_usd` with token usage present is DENY, not a silent $0.

**SASE human pause** is already a first-class turn kind (`docs/architecture.md`):

- Gate turns persist a request bundle, release the runner slot, and wait with no provider process.
- Plan review, questions, launch approval, workflow HITL, and beta sudo all use this.
- Sudo never proxies a password (`docs/sudo.md`): typed argv, SHA-256 of executables, human PAM in a real terminal, ledger back to a successor.
- Agent holds are durable reverse waits (`sase agent hold` / `%hold`).
- Usage-limit handling is **reactive**: classify vendor “you’ve hit your limit” text and hard-disable the provider for a window (`src/sase/llm_provider/usage_limit_config.py`). Continuation-budget preflight is a separate, Rust-owned prompt-size gate.

Omnigent can intercept a *tool call inside a live vendor session*. SASE, by design, mostly sees the vendor CLI as a black box for one turn. The exception is Claude’s helper PreToolUse guard. That is why a SASE policy engine has to ride **provider hooks + gate turns**, not a mid-session MCP proxy, unless SASE grows a runner like Omnigent’s.

### 3.5 Isolation and secrets

Omnigent’s sandbox story is the one SASE does not have:

- Linux native wrappers **require** `bwrap`; missing binary is a hard start failure (README).
- macOS uses seatbelt; Windows Job Objects contain the process tree without FS/network isolation.
- L7 egress MITM plus **secretless credential proxy** (`designs/SANDBOX_CREDENTIAL_PROXY.md`, marked implemented): real secrets stay in the parent; the sandbox sees nothing, or a non-secret `oa_cred_*` placeholder that the proxy swaps on the bound host and 403s on any other host. This is the difference between “YOLO in a clone” and “YOLO that cannot exfiltrate `GH_TOKEN`.”
- Cloud sandbox providers implement `SandboxLifecycle` (`docs/extending/sandbox_providers.md`) with optional warm pools, shallow `git_clone` policy, and per-session managed hosts.

SASE isolation is **workspace-shaped**: numbered clones, claim/release, systemd `OOMPolicy=continue` detach on Linux, remote `%dispatch` onto an enrolled machine. Secrets in the agent environment are the host user’s secrets. Unattended AXE jobs inherit that. For a local supervised coding agent this is acceptable. For “run YOLO on a schedule against a private repo” it is not.

SASE already has the right *human* privileged-exec story (sudo gates). It lacks the *machine* privileged-exec story (sandbox + brokered credentials).

### 3.6 Collaboration and surfaces

Omnigent’s product bet is “sessions follow you”:

- Same session on terminal, localhost:6767, LAN phone, macOS desktop.
- Share URL, co-attach (`omnigent attach`) so a teammate’s messages execute on *your* machine, fork (`omnigent run --fork`).
- Multi-user with `OMNIGENT_AUTH_ENABLED`, invite links, OIDC.
- Slack integration tree; VS Code extension; browser extensions.

SASE’s product bet is “one operator, a team of agents, reviewable output”:

- TUI Agents / Patches / notifications / artifacts.
- `sase-telegram` as a chop: launch, approve, kill, review images from chat.
- Mobile gateway in Rust (`docs/mobile_gateway.md`): pairing, SSE, list/launch/kill/retry, Patch/macro/bead helpers, loopback + Tailscale. Native Android is an MVP; web frontend is still a design question (`docs/blog/posts/whats-next-memory-mobile-web.md`).
- Remote dispatch enrolls *machines*, not *teammates sitting in your session*.

Omnigent is years ahead on “open it on your phone and keep chatting.” SASE is years ahead on “the PR, the bead, the goal, and the artifact are the objects teammates review.” A SASE web surface that replays **agent records** (prompt, chat, diff, gates, artifacts) matches SASE’s state model. A SASE web surface that proxies a live vendor PTY would fight it.

### 3.7 Multi-agent orchestration

**Polly** (`examples/polly/config.yaml`) is the Omnigent canonical pattern: orchestrator brain on `claude-sdk`, seven coding workers as native harnesses, first-turn roster preflight via `sys_session_get_info` / `configured_harnesses`, `sys_advise_models` before fan-out, each implementer opens its own PR, independent different-vendor reviewer, human merges. `spawn: true` also lets Polly author new agent configs at runtime.

SASE already does the engineering version of this: `%model` / size aliases, swarm/repeat/clan directives, typed `LaunchPlan` in Rust when `typed_launch_units` is on, isolated workspaces per slot, research swarms with named researchers, native helpers that must not declare, host-owned commit. What SASE does *not* ship as a productized object is “this YAML *is* the orchestrator, portable across harnesses, with a readiness map the brain is required to read.”

Macros and workflows are more powerful than Omnigent YAML for *software engineering* (typed inputs, `#` refs, `%wait`/`%if`/`%proc`, human checkpoints). They are less obvious as a *shareable agent identity*.

### 3.8 Scheduling

Omnigent automations (`docs/AUTOMATIONS.md`) fire a real session from an RRULE, optional `max_cost_usd` per firing, `permission_mode` for Claude-native, `execution_target: managed_sandbox` for a fresh VM each run, and agent tools so the agent can schedule itself. Firing is fire-and-forget after guard steps; a dead host records `host_offline` rather than hanging.

SASE AXE is a fuller orchestrator: routines, jobs, mentors, workflow checks, comments, cleanup, digests, `%proc` named procs, monitors that can complete a prepared finalizer. It is also more operator-heavy. The Omnigent idea worth stealing is the **per-run budget + unattended permission mode + explicit execution target** attached to the schedule row, not RRULE syntax itself.

### 3.9 State and source of truth

Omnigent: `~/.omnigent/chat.db` is the runtime conversation store. Two worktrees share it unless `OMNIGENT_DATA_DIR` is set. Sharing mode files (`sharing_mode`, `public_sharing`) sit beside it. This is the right store for a multi-user product. It is a poor store for git-portable research, plans, and beads.

SASE: ProjectSpecs under `~/.sase/projects/`, agent artifacts under `~/.sase/`, SDD in sidecars, memory in-tree, Patches in the project spec, goals as event logs. Agents reconstruct context from files. Instruction bundles are content-addressed (`common_digest`) and omit host paths/timestamps so two workspaces render identical bytes.

Keep SASE’s file-backed model. If SASE grows a web/mobile collab surface, it should project those files, not replace them with a session database.

### 3.10 Productization contrast

Omnigent, three months after create-date, has 10k+ stars, a one-line installer, Homebrew, Docker/K8s/Fly/Railway/Render/Modal deploys, `omni upgrade` that **drains in-flight sessions**, `omnigent uninstall` with an install ledger and optional purge-with-backup, a desktop app download, and a Discord. The issue tracker is loud (1.8k open). That is both traction and load.

SASE has a deeper engineering core, a handbook, two-speed CI, and almost no public footprint on GitHub. That is a positioning choice as much as a gap. The comparable *product* lessons are installer/upgrade/uninstall UX and “one URL that is the same session,” not “get 10k stars.”

---

## 4. What SASE already does better (keep)

These are load-bearing. Treat them as constraints on any import.

1. **Single-turn agents + host-owned completion.** A gate never blocks a live provider process. Continuation is a new session member. This is how SASE survives OOM, TUI restart, and “the human went to dinner.”
2. **Adapters normalize harnesses** into `invoke(prompt)`. Live steer, tmux attach, and vendor TUI takeover stay in `sase tmux-agent` (unmanaged) rather than becoming the SASE agent.
3. **Work graph:** beads, epics, plans, Patches, stitches, goals, ToolRuns, artifact refs/links, audited memory. Omnigent has almost none of this as a first-class, git-portable domain.
4. **Numbered workspaces** with claim/release and git alternates. Parallel agents do not share a dirty tree unless you ask them to.
5. **Rust core for deterministic hot paths** and a committed mobile-gateway contract snapshot.
6. **Feature flags as beads** with sunset discipline. Omnigent’s `OMNIGENT_FEATURES=a,b` env var is a coarser rollout switch (`designs/FEATURE_FLAGS.md`).
7. **Instruction inventory and `sase instructions verify`.** E2 is already walking toward what Omnigent calls `InstructionDelivery`.
8. **Sudo without secret proxying** and **holds that fail open.**
9. **Two-speed verification** (`just check` vs explicit `check-full`) and receipt-backed completion.

---

## 5. Where Omnigent is ahead in ways SASE can use

Ranked in the next section. The themes:

- **Declare then probe** harness behavior, instead of hoping adapter comments stay true.
- **Govern at the tool boundary** with ASK that maps onto SASE gates, including spend.
- **Sandbox unattended execution** so YOLO is a policy, not a personality setting.
- **Prove every entry point** of a user-facing feature (TUI, CLI, Telegram, gateway).
- **Share the work record** on a URL, with the same objects the TUI already shows.
- **ACP as a third integration mode** for vendors that will not grow a custom JSONL stream.
- **Upgrade drains work; uninstall has a ledger.**
- **Per-schedule cost cap and execution target** on AXE jobs.

---

## 6. Ranked recommended changes for SASE

Scoring: **fit** with SASE’s single-turn / file-state / host-owned model, **user value**, **cost**, and **evidence** that Omnigent already paid the learning tax. Higher number is later / more optional.

### 1. Declared provider capability matrix + live conformance bench

**Do this first.**

Add a `ProviderCapabilities` (or `HarnessCapabilities`) record next to each `sase_llm` plugin, covering at least: integration mode, instruction delivery channel, helper coverage, interrupt/sync ceiling, usage-probe, images, effort family, auth evidence, steer/live-queue (almost always false for SASE agents), ACP yes/no.

Drive `sase doctor -C llm.*`, `sase instructions verify`, and Launch Control from that record. Add a small live bench that flags **DRIFT** when Claude’s helper guard, Codex developer-instruction inheritance, or Grok’s empty child channel disagrees with the declaration.

Omnigent evidence: `omnigent/harness_capabilities.py`, `docs/harness-bench-design.md` (shipped; already corrected real drift). SASE already has the seed tables in `docs/agent_providers.md`.

Fit: this is the `adapters-normalize-harnesses` decision made inspectable. Cost: medium. It prevents the next “Grok helpers declared / Muse silently dropped the contract” class of bugs.

### 2. OS sandbox + secretless credential proxy for unattended AXE / `%proc` / YOLO

For scheduler jobs, named procs, and an explicit “unattended” launch mode:

- Linux: optional then later default `bwrap` (or Landlock) around the provider process, with a tight FS map of the numbered workspace plus read-only toolchain.
- macOS: seatbelt profile.
- Parent-side L7 or git-credential helper that injects `GH_TOKEN` / git HTTPS creds **on the bound host only**, with placeholders inside the sandbox (`oa_cred_*` design).

Do not put real tokens in the agent environment for unattended runs.

Omnigent evidence: mandatory Linux bwrap for native wrappers; implemented `designs/SANDBOX_CREDENTIAL_PROXY.md`.

Fit: extends sudo/gates/holds into the machine. Cost: high, but one backend (bwrap) plus git/gh broker covers most of SASE’s threat model. Skip the 12-cloud-provider zoo until one local sandbox is real.

### 3. Stateful spend and tool policies as gate turns

Add a small policy table (project and/or machine) evaluated at **request** (before `invoke`) and, where a provider hook exists, at **tool_call**:

- Soft ASK at spend checkpoints → existing gate turn (session pauses, runner slot released).
- Hard DENY or “downgrade off expensive models” at `max_cost_usd`.
- Fail closed when usage exists and USD is missing (Omnigent’s unpriced-model rule).
- Optional max-tool-calls / write-path allowlists for unattended jobs.

Wire Claude PreToolUse first (SASE already has a helper guard channel). Other providers stay request-phase-only until hooks exist.

Omnigent evidence: `omnigent/policies/builtins/cost.py`, `docs/POLICIES.md`, runner/server dual evaluation of ASK.

Fit: ASK *is* a SASE gate. This replaces “disable Claude for a week after the vendor yells” with “pause at $5 and ask.” Cost: medium. Requires honest usage from adapters (Claude/Codex already write usage artifacts).

### 4. Feature-map recipes with multi-surface entry-point proof

Adopt Omnigent’s `feature-map/` contract for SASE user-facing features:

- One file per feature: sub-feature IDs, every user entry point grouped by surface (TUI, CLI, Telegram, gateway, nvim), driving steps, traps.
- A fix is verified only when **every listed entry point** has proof (screenshot golden, CLI exit, Telegram chop, gateway JSON).

SASE already has TUI screenshot goldens and `just check`. The failure mode Omnigent named is “proved it in the web UI, broke the native TUI.” SASE’s analogue is “proved it in the TUI, broke Telegram or `sase agent wait`.”

Omnigent evidence: `feature-map/README.md`, `AGENTS.md` (“start with feature-map/README.md”).

Cost: low-medium; mostly process plus a few index files. High leverage for ACE + gateway divergence.

### 5. Shareable agent-record surface (web or richer mobile), artifact-centric

Build the web/mobile view around **existing durable objects**: agent identity, prompt, live-reply file, diff, artifacts, gate cards, Patch, goal citations. One URL per agent (or clan) that a teammate can watch and, later, answer gates on.

Keep live vendor-TUI co-drive in `sase tmux-agent`. Do not make “attach to my Claude pane” the SASE collab primitive.

Omnigent evidence: share/co-drive/fork are the growth loop; SASE’s `whats-next` post already names web as the open design. The mobile gateway’s committed API is the right backend to extend, rather than a second control plane.

Cost: high. Value: high for anyone who is not in the TUI. Sequence: gateway API completeness → read-only web of agent records → gate answers → launch.

### 6. ACP as a first-class integration mode

Add `integration_mode: acp-subprocess` beside today’s JSONL/CLI adapters. Use it for new vendors (Devin, future CLIs) and as a conformance target for Grok.

Omnigent evidence: Grok and Devin are ACP-only; `--model` is refused rather than dropped; credentials stay in the vendor CLI. SASE already speaks Grok; a shared ACP client would cut the next adapter from “new `_subprocess_foo.py`” to “capability record + argv.”

Fit: still one-shot `invoke` wrapping an ACP session that SASE starts and reaps. Cost: medium.

### 7. Launchable agent spec (YAML or card) distinct from a macro

Macros are prompts and workflows. Omnigent YAML is **identity + harness + tools + policies + sub-agents**.

SASE already has Agent Data Cards in the glossary. Promote a checked-in spec (for example `sase/agents/polly.yml`) that binds:

- default `%model` / effort
- allowed tools / MCP
- policy profile (from #3)
- sub-agent roster (named macros or providers)
- sandbox profile (from #2)

`sase run @agent:polly …` then expands to today’s launch path. Polly’s “read `configured_harnesses` before dispatch” becomes a first-turn skill that calls `sase doctor -C llm.auth --json`.

Cost: medium. This is how SASE ships a portable “research swarm” or “cross-vendor review” as a product object rather than a prompt you have to remember.

### 8. Drain-then-upgrade and an install/uninstall ledger

`omni upgrade` waits for in-flight sessions, stops the local server, then upgrades. `omnigent uninstall` reads `install_ledger.json`, previews, and can purge with an off-tree backup.

SASE already has an Updates tab and `sase plugin install`. Add:

- `sase upgrade` that drains `max_running_agents`, stops the service host, then `uv tool upgrade`.
- An install ledger for PATH shims, completions, systemd/LaunchAgent units, and plugin extras.
- `sase uninstall --yes` / `--purge` with the same preview/backup shape.

Cost: low-medium. Operator trust is the value. Fits a tool that already detaches work into systemd scopes.

### 9. One managed execution target on AXE jobs

Do not import Modal+Daytona+Blaxel+E2B+K8s in one epic. Add **one** extra target on a scheduled job:

- `execution_target: connected_host` (today’s machine / `%dispatch` alias)
- `execution_target: sandbox` (bwrap from #2, same machine)
- later: `execution_target: remote_sandbox` once one cloud provider is proven

Attach `max_cost_usd` and an unattended permission profile to the job row (see #3). Record `host_offline` as a failed run instead of a hung waiter.

Omnigent evidence: `docs/AUTOMATIONS.md` `execution_target` + `max_cost_usd` + `permission_mode`.

SASE already has richer scheduling. This is a **job annotation**, not a new daemon.

### 10. Model advisor at swarm fan-out

Before a multi-slot launch, optionally call a cheap advisor (or a table) that maps each slot’s size/role to a provider+model given current auth, usage windows, and disable state. Surface it in Launch Control and as a tool the orchestrator agent can call (Polly’s `sys_advise_models`).

SASE already has size-alias effort ladders, provider priority, and usage-limit auto-disable. The missing piece is **task-aware routing at fan-out time**, including “this reviewer must be a different vendor than the implementer.”

Cost: low-medium. High value for research swarms and Patch review.

### 11. Publish the gateway OpenAPI and keep it as the collab contract

Omnigent’s `openapi.json` is a product artifact. SASE’s gateway already has a committed API snapshot in sase-core. Publish it, generate a typed client, and refuse ad-hoc Telegram/web endpoints that are not in that snapshot.

Cost: low. Prevents the “second control surface” failure mode named in the SASE web roadmap note.

### 12. CLI stream contract: stdout is data, stderr is chrome

Omnigent’s `designs/CLI_CONTRACT.md`: stdout is machine-readable, stderr is banners/spinners, `NO_COLOR` / `OMNIGENT_NO_BANNER` gates, no brand on ordinary commands.

SASE is already JSON-friendly (`-j` / `-f json`) but mixed. Codify the same rule for `sase agent list`, `sase repo open` (already prints the path on stdout and AGENTS.md hints on stderr — keep that), and doctor. Ban new `click.secho` on stdout.

Cost: low. Pays off in macros, chops, and tests.

### 13. Compaction-aware import of vendor transcripts

When SASE captures or imports a Claude/Codex session (`docs/session-compaction.md` in Omnigent; SASE continuation-capture + `sase instructions verify` already read vendor session files):

- Detect the last compaction boundary (`isCompactSummary`, Codex `compacted` records).
- Below a size threshold, keep full history; above it, keep the post-compaction baseline plus later items.

Cost: low. Protects instruction-verify and chat replay from multi-megabyte pre-summary JSONL.

### 14. Ship cross-vendor review as a first-class workflow

Productize Polly’s rule as a SASE workflow/macro:

- Implementer slot and reviewer slot **must** resolve to different providers (doctor-backed).
- Each implementer workspace opens/updates its own Patch.
- Human merge remains host-owned.

SASE research swarms already do a version of this. Give it a stable name and a card (see #7).

Cost: low once #1 and #7 exist.

### 15. Promote `InstructionDelivery` into the E2 manifest

Align vocabulary with Omnigent’s enum: `composed-per-turn`, `composed-session-snapshot`, `agent-startup-additive`, `first-user-prefix`, `not-delivered`. Write that field on the shadow manifest so `sase instructions verify` can say “declared X, observed Y” per provider.

This is a refinement of work already in flight (`docs/instruction_bundles.md`). Do it as part of #1 rather than a separate epic if possible.

---

## 7. Explicitly decline (or defer hard)

These look attractive in Omnigent and fight SASE’s architecture.

| Omnigent idea | Why it stays out (or last) |
| --- | --- |
| Live multi-turn session as the SASE agent | Breaks single-turn, host-owned completion, and gate-as-turn. Keep `tmux-agent` unmanaged. |
| Mid-turn steer / client-side live queue as default | Requires a resident vendor TUI. SASE already has prompt Stash + successor turns. |
| `chat.db` as source of truth | Conflicts with git-portable SDD, beads, and content-addressed instruction bundles. |
| Twelve cloud sandbox providers | One local OS sandbox first (#2), then one remote. |
| CEL policy language | SASE should evaluate policies in-process and pause via gates. CEL is an extra runtime (and a C++ wheel) for a problem gates already express. |
| Co-drive on the operator’s machine via share URL | Wrong trust model for a single-operator TUI that already has sudo and holds. Share **records**, not a shell. |
| Env-var feature flags | SASE flag beads already have sunset and inventory. |
| Framework-owned prompt append that every harness must transport | SASE is investing in memory-built bundles with facts/overlays. Keep composition on the SASE side; adapters only transport. Omnigent’s own `AGENTS.md` agrees: adapters must not duplicate policy. |

---

## 8. Suggested sequence

If this comparison becomes an epic, the dependency order that respects SASE’s constraints is:

1. Capability matrix + bench (#1) and InstructionDelivery on manifests (#15).
2. Feature-map discipline (#4) and CLI stream contract (#12) while #1 lands — cheap, parallel.
3. Request-phase spend/tool policies as gates (#3), Claude hook first.
4. bwrap sandbox + credential broker for unattended jobs (#2), then AXE execution targets (#9).
5. Agent spec cards (#7), model advisor (#10), cross-vendor review workflow (#14).
6. Gateway OpenAPI (#11) → read-only shareable agent-record web (#5).
7. ACP mode (#6) as the next-provider factory.
8. Upgrade/uninstall ledger (#8) whenever the service-host story is touched.
9. Compaction-aware import (#13) opportunistically in continuation-capture work.

---

## 9. Closing

Omnigent is the best public demonstration that a **meta-harness** can sit above Claude/Codex/Cursor/Pi and sell collaboration, policy, and sandboxing as the product. SASE is the best demonstration (even with almost no public GitHub footprint) that the hard part of agentic software engineering is **durable work state**: where the patch went, what it was for, who is waiting, and whether the host will commit.

Steal Omnigent’s *discipline around harness diversity* (capabilities, benches, policies, sandboxes, install UX). Keep SASE’s *discipline around turns and files*. The ranked list above is that split, in the order I would actually start work.
