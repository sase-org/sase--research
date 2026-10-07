---
title: "Omnigent (meta-harness) vs SASE: architecture comparison and recommended changes"
researcher: cld
date: 2026-10-07
subjects:
  - omnigent-ai/omnigent @ ee2488aee (2026-10-07, version 0.18.0.dev0; last release v0.17.0 on 2026-10-05)
  - sase @ 6e2bc57726 (2026-10-07, version 0.17.1)
method: >-
  Local read-only study of the omnigent checkout (opened as an external repo via
  `sase repo open gh:omnigent-ai/omnigent`) and of the sase repo, its docs/, and its
  decision records. Four parallel code explorations (omnigent execution core; omnigent
  governance/sandboxing/cost; omnigent authoring/automation/engineering practice; sase
  architecture), followed by direct spot-checks of the claims that drive the
  recommendations. No code from either project was executed.
---

# Omnigent vs SASE

## TL;DR

- **The two projects solve different problems.** Omnigent is a team product: a
  server-centric "meta-harness" with a web, desktop, and phone UI over long-lived chat
  sessions. Its core value is *one session surface over any coding CLI*, plus
  governance (policies, sandboxes, budgets) and collaboration. SASE is a single-operator
  engineering system. Its core value is *durable, structured work state outside
  transcripts*: beads/epics, plans, gates, host-owned completion, memory, and a Rust
  core. In SASE an agent is one turn, not a chat.
- **Omnigent is far ahead on governance and harness coverage.**
  - It has a real ALLOW/DENY/ASK policy engine at six enforcement points, and maps it
    into the native CLIs' own hooks (Claude `PreToolUse`, Codex, Cursor, Pi, Hermes, …).
  - It has optional OS sandboxing (bwrap + seccomp, Seatbelt), an L7 egress allowlist
    proxy, and a credential swap-on-access proxy.
  - It has dollar cost accounting with budget policies.
  - It covers about 27 harness ids (about 16 agent products) through four integration
    modes, including a generic ACP harness.
  - It checks its capability matrix with an executable conformance bench that reports
    `DRIFT`.
  - **SASE has none of these mechanically.** Every SASE provider runs with its
    permission-bypass flag and inherits the full host environment.
- **SASE is ahead on durability and work structure.**
  - Omnigent keeps authoritative turn and approval state in runner/server memory
    (`omnigent/server/DBSPEC.md`). Its own resilience lab pins eight open failure modes,
    such as messages lost while the host is unreachable and approval cards missing
    after a restart.
  - SASE's file-durable gates, write-once responses, single-turn contract, and
    host-verified finalizers avoid that whole class of bugs.
  - Omnigent's multi-agent orchestration is LLM-driven, through supervisor prompts and
    skills. SASE's is structural: epic waves, LaunchApproval, holds, and admission.
- **The most transferable omnigent ideas** are mechanisms SASE can add *without*
  giving up its single-turn, host-owned philosophy:
  - hook-enforced tool-call guardrails;
  - vendor-diverse, contract-only review;
  - a provider conformance bench;
  - environment allowlisting;
  - cost/budget rollups;
  - a "join" wake for agent fan-out.
- **What not to copy:** long-lived steerable sessions, the server/web/multi-tenant
  stack, LLM-judged "policies", and speculative memory (Hindsight).

---

## 1. What omnigent is

> "Omnigent is an open-source **meta-harness** that gives you a common orchestration
> layer over Claude Code, Codex, Cursor, OpenCode, Hermes, Pi, and the agents you write
> yourself: swap or combine harnesses without rewriting, enforce policies and
> sandboxing, and collaborate in real time from any device." (`README.md`)

**Scale and pace** (as of HEAD `ee2488aee`):

| Metric | Omnigent | SASE |
|---|---|---|
| Age | first release v0.1.0 on 2026-06-13 | first commit 2026-02-14 |
| Commits | 4,543 | 15,753 |
| Contributors | 278. Heavily Databricks/MLflow staff; an `omni-resolve-agent[bot]` has 261 commits | essentially 1 human plus agents |
| Python LOC (product) | ~514K in `omnigent/` (898 files), plus a large TS web app, Electron desktop, iOS/Android, VS Code, and Slack | ~1.29M raw lines in `src/sase/` (543K of that is the TUI), plus the separate Rust `sase-core` |
| Tests | 2,121 `test_*.py` (~1.02M lines) plus 488 web test files | 5,910 test files (~1.45M lines) |
| Releases | 21 releases in ~4 months, about weekly since v0.6.0, plus nightlies | 0.17.1, with continuous master |
| CI | 113 workflow files | 10 workflow files (two-speed: per-SHA gate plus a 2h full suite) |

Omnigent's headline features:
- **Sessions everywhere:** terminal, browser, phone, and desktop app, with sharing,
  co-drive, and fork.
- **Mix harnesses in one session:** for example, Polly, a "tech lead" orchestrator that
  delegates to Claude Code, Codex, Cursor, OpenCode, Hermes, Pi, and Antigravity workers.
- **Any model or credential type:** API key, subscription, gateway, or Databricks.
- **Cloud sandboxes:** 12+ providers (Modal, Daytona, E2B, Kubernetes, …), provisioned per
  session as "managed hosts".
- **Policies:** approvals, spend caps, and tool limits at server, agent, and session
  scope.

---

## 2. Side-by-side at a glance

| Dimension | Omnigent | SASE |
|---|---|---|
| **Primary user** | Teams. Multi-user accounts, OIDC, invites, sharing | One power user across several tailnet machines |
| **Unit of work** | A long-lived **session** (multi-turn chat) bound to a runner | A single **agent turn**, chained into sessions, clans, and epics, with durable artifacts |
| **Topology** | Server (FastAPI + SQL DB) ⇄ host daemon ⇄ runner (one per session, forked from a zygote) ⇄ harness subprocess ⇄ vendor CLI/SDK, over outbound WebSocket tunnels | CLI/TUI ⇄ per-machine service host (scheduler/AXE, mobile gateway) ⇄ detached runners; state in files under `~/.sase` plus sidecar git repos; required Rust core |
| **Harness coverage** | ~27 ids, ~16 products, in modes SDK in-process, CLI subprocess, **ACP**, native TUI (tmux), native server | 7 CLIs (claude, codex, agy, qwen, opencode, muse, grok) + `fakey`, all headless print-mode |
| **Event normalization** | Executor events → one Responses-API-style SSE vocabulary, published as `openapi.json` | Provider-specific stream parsers → `live_reply.md`, `tool_calls.jsonl`, `usage.json`, chat history |
| **Multi-agent** | LLM supervisor calls `sys_session_send` (async). Children run; parent is woken with an inbox notice. Worktrees are prompt/skill-driven | Macro swarms, `%alt`, `%wait` chains, clans and tribes, epic waves plus land agent, LaunchApproval for agent-initiated launches, remote `%dispatch` |
| **Human-in-the-loop** | In-turn ASK → approval card, URL, or TUI prompt; first answer wins; waits up to 1 day | Gates **end the turn**; a durable bundle with a write-once response; answered from TUI, Telegram, mobile, or CLI |
| **Completion** | The agent itself commits, opens PRs (`gh pr create`), and the PR observer records them | Host-owned finalizers; the agent never commits; postconditions verified |
| **Governance** | Policy engine (6 phases, 27 builtins, 3 scope levels), enforced through native-CLI hooks | Orchestration-boundary controls only: gates, LaunchApproval, sudo gates, holds, capacity, guarded recipes, Claude helper guard |
| **Isolation** | Optional bwrap/Seatbelt/seccomp, egress MITM allowlist, credential proxy, env allowlist; git worktrees optional | Per-agent full workspace clones; **no OS sandbox**; providers run with `--dangerously-*` / `--yolo`; env is `os.environ.copy()` |
| **Cost** | Token pricing via model catalog; per-session, per-user-day, and per-period budgets; sub-agent budgets; downgrade gate | Subscription usage windows, auto-disable on limit, per-run `usage.json` tokens; no $ accounting or budgets |
| **Durability** | Conversations in DB; **turn, steer, and approval state in memory** | Everything durable on disk / Rust-owned stores; single-turn by design |
| **Knowledge** | Agent `AGENTS.md` + skills; optional Hindsight memory; full-text conversation search | Memory core/reference/webs (decisions, glossary, task types), audited reads, instruction-delivery verification |
| **Surfaces** | Web, desktop, iOS/Android, VS Code iframe, Slack, Python SDK, REST/OpenAPI | Textual TUI, CLI, Telegram, Android via Rust gateway, Neovim |
| **Scheduling** | RRULE "Automations" (no backfill, no lease; replicas double-fire) | AXE routines and jobs with validated launch proposals, holds, admission |
| **Conformance testing** | Harness bench (12 probes, `DRIFT` verdicts), resilience lab with fault proxies, feature map plus `verify-omnigent` | `just check` (symvision, flag lint, diff-scoped tests), triage verdicts, receipts, `sase instructions verify`, TUI golden screenshots |

---

## 3. Dimension-by-dimension comparison

### 3.1 Execution model: long-lived sessions vs single-turn agents

**Omnigent sessions** are multi-turn conversations with states
`idle → running → waiting → idle | failed` (`omnigent/server/API.md`).
- **Binding:** the same `PATCH /v1/sessions/{id} {runner_id}` endpoint handles
  create-bind, resume-bind, and recover-bind.
- **Runner:** one runner per session. It is forked copy-on-write from a zygote that
  pre-imports the runner graph (~120 MB shared, `omnigent/runner/_zygote.py`).
- **Harness subprocess:** each conversation gets one, served over a Unix socket and
  reaped after 1h idle (`omnigent/runtime/harnesses/process_manager.py`).
- **Queue vs steer** (`docs/QUEUE_STEER_DESIGN.md`):
  - Queued messages live client-side and stay editable until the session goes idle.
  - "Steer" injects into a live turn: Codex `turn/steer` RPC, or a paste into the
    Claude TUI pane.
- **Resume:** warm-reattach for native TUIs, cold rebuild from history for most SDK
  harnesses.
- **Fork:** deep-copies items and either rebuilds the vendor transcript file or replays
  a text preamble.

**SASE** does the opposite on purpose.
- Decision `single-turn-agents`: "A SASE agent run is exactly one provider turn."
  Continuation is mechanical only, through monitor, handoff/pipe, plan, questions, or
  launch gate turns.
- Decision `adapters-normalize-harnesses` makes each adapter *disable* native wake and
  background primitives.
- The decision record cites a real experiment: detached-only mode was introduced and
  then retired (`b20637f4f`, `ac5d95810`).

**Why this matters for the comparison.** Omnigent pays for its long-lived model in
resilience:
- `DBSPEC.md` states that "the authoritative turn/steering state today lives in-memory
  in the runner process … and is never written to the DB."
- `docs/network-resilience.md` pins open gaps as strict xfails:
  - R1: the server keeps pending approvals in memory, so a restart loses the card until
    the hook re-POSTs.
  - R3: a message sent while the host is unreachable is lost.
  - R4: Stop reports success while the host is unreachable.
  - R6: repeated blips add up to a disconnect failure.
  - R8: Codex status sticks on `running` after a reconnect.

SASE's single-turn + durable-gate model is structurally immune to most of these. That
is a point in favour of keeping SASE's model, not copying omnigent's.

**Convergence worth noticing.** Omnigent's own best orchestrator, Polly, behaves
single-turn-ish:
- Her prompt says "act in the same turn you announce", "no polling", "no `sys_timer_set`
  for waiting", and to end the turn after dispatch.
- She is woken by inbox notices when children finish (`examples/polly/config.yaml`,
  `omnigent/runner/subagent_work.py`).

So omnigent arrived independently at "end the turn, get woken mechanically" for
orchestration. SASE formalized this. The one ergonomic piece omnigent has that SASE
lacks is the **automatic wake-on-children-complete with a structured inbox**; see
recommendation 6.

### 3.2 Harness / provider integration

**Omnigent has one executor interface.** `omnigent/inner/executor.py` defines
`run_turn(...) -> AsyncIterator[ExecutorEvent]` with 12 normalized event types. It also
declares capability methods (`supports_streaming`, `handles_tools_internally`,
`supports_live_message_queue`, …). Five integration modes are declared in
`omnigent/harness_capabilities.py`:

- **SDK in-process:** claude-sdk, openai-agents, cursor, antigravity, copilot,
  open-responses.
- **CLI subprocess:** codex (long-lived `codex app-server`), pi (`--mode rpc` JSONL),
  kimi, hermes.
- **ACP subprocess:** generic `acp:<slug>`, goose, qwen, grok, jcode. Any Agent Client
  Protocol server can be added by config.
- **Native TUI:** the vendor CLI runs in a private tmux pane.
  - Input goes in via `tmux send-keys`.
  - Output is recovered by tailing the vendor's JSONL transcript (claude-native
    forwarder: 7.2k lines).
  - Approvals and policy run through vendor hooks.
- **Native server:** opencode.

**The capability matrix is explicit data** (`HarnessCapabilities`). Its axes include:
- elicitation mechanism, resume mode, interrupt, streaming, steering, live queue,
  compaction, fork-history mode;
- instruction delivery: composed-per-turn, session-snapshot, first-user-prefix, or
  *not-delivered* (declared honestly for several natives).

**The matrix is tested, not trusted.** `docs/harness-bench-design.md` and
`tests/harness_bench/` give:
- 12 probes: basic turn, streaming, tool calling, policy deny, model override,
  interrupt, fork replay, reasoning, MCP, policy allow/ask, and cost tracking;
- three drivers;
- a `reconcile()` that emits `DRIFT` when declared and observed behavior differ.

The bench has already flipped several declarations (kiro-, cursor-, and qwen-native
`streaming=False`).

The motivation reads like a description of SASE's own provider docs:

> "There are already **three disagreeing sources of truth** for any given capability:
> the spreadsheet … the Executor capability flags … model_override.py."

**SASE has 7 bespoke providers.** Each is a pluggy `sase_llm` entry point with its own
`_subprocess_*` and `_tool_call_*` modules (`src/sase/llm_provider/`).
- Capability knowledge is spread across prose and code:
  - prose tables in `docs/agent_providers.md` (helper coverage per provider) and
    `docs/llms.md` (for example the agy "Structured Artifacts Parity Gap": no tool-call
    timeline, no usage, no thinking);
  - `llm_usage_capabilities()` methods;
  - the Claude helper-channel capability probe cache.
- `sase instructions verify` is the closest analogue to the bench. It is
  *observational*: it reads providers' own session records to show what instructions
  were actually loaded, and "reports; it does not gate".
- There is no generic ACP provider. SASE already speaks ACP to Grok, but only for
  billing usage (`src/sase/llm_provider/usage/grok.py`).

**Prompt composition: the same idea, independently.** Omnigent's `AGENTS.md` rule:
"Agent-spec and per-request instructions are user-authored. Framework-owned
instructions are additive … appended after them in `omnigent/runtime/prompt.py`. …
Harness adapters should only transport the composed instructions." SASE's instruction
bundles with shadow manifests and delivery verification are more rigorous here.
Omnigent does not verify delivery. It just declares `NOT_DELIVERED` for several
natives.

### 3.3 Multi-agent orchestration

**Omnigent's orchestration is prompt-and-skill driven, with a thin mechanical layer.**

The mechanical layer:
- **Sub-agents** are tools (`type: agent`), each with its own harness and model, so one
  tree can mix vendors.
- **`sys_session_send(agent, title, args)`** returns immediately. Several sends in one
  response run in parallel. The `(agent, title)` pair keys a persistent child
  conversation, so re-sending to the same title *continues* that worker.
- **Results return asynchronously.** The runner tracks each dispatch and delivers the
  result to the parent's inbox. It then posts
  `[System: sub-agent X finished … N results waiting in inbox]`, which starts a parent
  turn if the parent is idle (`omnigent/runner/subagent_work.py`).
- **Blocked children** wake the parent after a 120 s grace
  (`runtime/subagent_block_notifier.py`).
- **Vendor-native sub-agents** (Claude `Task`, Codex `spawn_agent`, Devin) are mirrored
  as omnigent child sessions.
- **Policies bound the orchestrator:**
  - `spawn_bounds` (max dispatches per turn);
  - `headless_subagent_purpose_guard` (every dispatch must declare `implement`,
    `review`, `explore`, or `search`);
  - `blast_radius`, `worktree_guard`, `read_only_os`
    (`omnigent/policies/builtins/orchestration.py`).

**Polly's pattern** (`examples/polly/`) is the most instructive artifact in the repo:
- **Roster preflight:** one `sys_session_get_info` call, then read
  `configured_harnesses`.
- **`fanout` skill:** `git worktree add .worktrees/<task_id>`, one implementer per
  worktree, each driving tests green and opening **its own PR**.
- **`cross-review` skill:**
  1. Run deterministic gates first.
  2. Snapshot the diff to an absolute path with base and head SHAs.
  3. Dispatch a reviewer **from a different vendor** than the implementer, given **only
     the diff snapshot and the acceptance contract**: "never the implementer's
     transcript or worktree. The cross-vendor independence is the whole point."
  4. Send blocking issues back to **the same implementer conversation** (reuse the
     title) so it keeps its worktree, branch, and context and updates its PR.
  5. Loop, and escalate after a few rounds.
- **Polly never merges.** The PR is the deliverable and the human merges it.
- The same pattern runs as a PR bot: `.github/workflows/polly-review.yml` runs Polly on
  incoming PRs to post a cross-vendor review.

**SASE's orchestration is structural.**
- Epics become phase beads with dependency waves, executed by `sase bead work` with a
  final land agent.
- Macro swarms (`---` segments), `%alt` multi-variant fan-out, and `%wait` chains.
- Clans, tribes, and hoods for grouping.
- Agent-initiated launches require **LaunchApproval**: a human approves a `LAUNCH` gate.
- Holds and the `max_running_agents` budget govern admission.

This is much stronger on *durable plan → execution → landing* than anything in
omnigent, which has no plan or bead concept at all.

**Two gaps relative to Polly:**

1. **No vendor diversity in review.**
   - The epic land agent "verifies" by reading child notes, source, and commits
     (`bd/land_epic` in `src/sase/default_config.yml`). It runs on `@large` / `@xlarge`
     (`epic_lander_model` / `big_epic_lander_model`) with no constraint relative to the
     implementers' providers.
   - Mentors are configured by role and focus areas (`mentor_profiles` schema:
     `macro`, `prompt`, `mentor_name`, `role`, `focus_areas`). They have no notion of
     "different provider than the author".
   - The land agent also reads implementers' narratives (bead notes), which is exactly
     the contamination Polly's contract-only review avoids.
2. **No join-on-children wake.**
   - LaunchApproval's `requester_continuation.mode` is either `resume_requester` or
     `terminal_handoff` (`src/sase/agent/launch_request_continuation.py`).
   - `resume_requester` resumes the requester when the **gate settles** (approve,
     reject, timeout, failed), not when the launched children **finish**.
   - A join can be hand-built from `%wait` segments plus `terminal_handoff`, but it is
     not first-class and does not hand the parent a structured summary of child
     outcomes.

### 3.4 Human-in-the-loop

**Omnigent:**
- An ASK becomes an MCP-shaped elicitation. It surfaces as a web approval card, a
  standalone `/approve/...` URL, the native TUI's own prompt, a tmux popup for cost
  checkpoints, or a Slack card. **First answer wins** across devices.
- Default timeout is 86,400 s (1 day); a timeout is DENY.
- The agent's turn **blocks** in place while waiting. For native CLIs, the hook's HTTP
  request is parked server-side until a human answers
  (`_hold_native_ask_gate_impl`).

**SASE:**
- Decision `gates-never-block`: creating a gate ends the agent's turn.
- A processless gate turn owns the decision, runs argv-only commands for the chosen
  branch, and launches the follow-up.
- Bundles live under `~/.sase/interaction_requests/` with a write-once `response.json`.
- TUI, Telegram, mobile, and CLI answer the same bundle, so SASE also has "first answer
  wins", but *durably*.

**Verdict:** SASE's model is more robust (restart-safe, no parked HTTP requests, no
burned provider budget while waiting). Omnigent's is more granular: per tool call,
inside a turn. Recommendation 1 below adapts the granularity without the blocking.

### 3.5 Governance: the policy engine

This is omnigent's most distinctive subsystem (`docs/POLICIES.md`, `omnigent/policies/`,
`omnigent/runtime/policies/engine.py`).

**Shape.** A policy is a Python callable, `fn(event) → {result: ALLOW|DENY|ASK,
reason, data?, state_updates?, set_labels?} | None` (`None` abstains).
- Only `type: function` exists; LLM "prompt" policies are a builtin, not a type.
- Policies can redact or rewrite arguments (`data`), keep per-session state, set
  labels, and gate on labels.

**Phases:** `request`, `tool_call`, `tool_result`, `response`, `llm_request`,
`llm_response`. Every event carries actor, model, harness, labels, cumulative usage and
$ cost, subtree usage, and the user's daily cost.

**Composition:**
- Policies run in order; the first DENY short-circuits.
- ASKs aggregate, and ASK side effects apply only if approved.
- Every evaluation emits an OTel span.
- **Fail-closed** for `tool_call` and `request` when no verdict can be obtained;
  fail-open for `tool_result` and the LLM phases, with stated rationale.

**Scope levels:**
- Order: session (user) → agent spec (developer) → server (admin), plus a hidden
  always-on `ask_on_add_policy`.
- Children run the root's session policies first and cannot weaken them.
- Session-scope handlers are restricted to a registry ("accepting unregistered handlers
  is RCE").

**Enforcement inside native CLIs** (`omnigent/native/native_policy_hook.py`):
- Claude Code gets `PreToolUse` / `PostToolUse` / `UserPromptSubmit` hooks pointing at
  an evaluate-policy command.
- DENY → `permissionDecision: deny`.
- ALLOW → no output, so Claude's own permission prompt still applies ("two independent
  gates").
- If the server is unreachable, Claude and Codex fall back to the native prompt; Kimi
  and Devin fail closed.
- Cursor, Hermes, Pi (a JS extension), and Antigravity have their own adapters.

**Builtins** (27): the ones most relevant to SASE are
- `blast_radius`: always DENY force-push, `rm -rf /`, and hard reset to a remote ref;
  ASK or DENY on other risky commands, parsed from shell argv;
- `worktree_guard`: DENY writes with absolute or `..`-escaping paths;
- `read_only_os`: DENY every write/edit tool, including Claude/Codex/Pi native
  aliases, for report-only agents;
- `detect_thrashing` (N consecutive tool errors or an error-rate window),
  `detect_loop`, `max_tool_calls_per_session`;
- `cost_budget` and per-user/period variants;
- `github_policy`: repo/branch allowlists applied to MCP tools *and* parsed `git`/`gh`
  shell commands;
- `cel_policy`: a CEL expression.

Several are LLM-judged: `prompt_policy`, `intent_based_authorization`,
`detect_task_switch`. Their own docstrings warn they are "not a security control" and
fail open without an LLM.

**SASE today:**
- No tool-call policy layer. All seven providers run with bypass flags
  (`src/sase/llm_provider/claude.py`: `--dangerously-skip-permissions`; `codex.py`:
  `--dangerously-bypass-approvals-and-sandbox`; `qwen`/`muse`: `--yolo`; `grok`:
  `bypassPermissions`; `agy`/`opencode`: `--dangerously-skip-permissions`).
- **Mechanical, but boundary-level:**
  - LaunchApproval;
  - sudo gates;
  - host-owned completion, with finalizers verifying postconditions;
  - guarded recipes (`just check` refuses to run outside `sase tool run`; the decision
    calls it "a guardrail against habit, not a security boundary");
  - holds and capacity;
  - the **Claude helper guard**, a real `PreToolUse` hook blocking turn-ending `sase`
    commands from native helpers (`src/sase/llm_provider/_claude_helper_guard.py`).
- **Prose-only rules** sit in core memory and are unenforced, for example:
  - "be mindful not to run commands outside of these workspace directories";
  - "Do NOT read sidecar artifact files directly";
  - "do not … web-fetch another repo's contents" (use `/sase_repo`);
  - "An agent never creates commits, branches, or PRs";
  - don't run `just check-full` unless told to.

So SASE already owns the exact mechanism omnigent uses (a Claude `PreToolUse` hook). It
just uses it for one rule.

### 3.6 Isolation and credentials

**Omnigent:**
- **OS sandboxes:**
  - `linux_bwrap`: read-only system, cwd read-only unless declared writable, `$HOME`
    never mounted, net unshared when off.
  - seccomp: k8s RuntimeDefault denylist, ptrace hardening, no new namespaces, socket
    families restricted.
  - `darwin_seatbelt`: `(deny default)` SBPL.
  - `windows_jobobject`: process-tree containment only.
  - `copy_on_write`: overlay with discarded writes.
- **L7 egress proxy** (`omnigent/inner/egress/`): TLS-intercepting, with
  method/host/path rules such as `"GET,POST api.github.com/repos/org/**"`. Unmatched
  requests get 403. It refuses private, loopback, IMDS, and CGNAT destinations by
  default.
- **Credential proxy** (`designs/SANDBOX_CREDENTIAL_PROXY.md`):
  - The parent holds the secret; the proxy injects `Authorization` only for the bound
    host.
  - Clients that insist on a local token (`gh`) get a single-host `oa_cred_*`
    placeholder that 403s anywhere else.
- **Model signer:** the sandboxed Codex never sees the model credential.
- **Env allowlists at two layers:** host→runner (`_RUNNER_ENV_ALLOWLIST` in
  `omnigent/host/connect.py`) and runner→CLI (`omnigent/inner/agent_env.py`). The
  documented rationale: otherwise the agent could run `env` and exfiltrate keys.
- **Caveat on the README.** It says native wrappers sandbox the agent terminal with
  bwrap on Linux. But the generated `claude-native` spec declares
  `os_env.sandbox: {type: none}` ("Claude Code already operates on the user's workspace
  with full filesystem access", `omnigent/harnesses/claude_native/main.py`). Native
  terminals inherit the agent's `os_env` (`runner/native/orchestration.py`). So the
  default `omnigent claude` posture appears unsandboxed, like SASE's. Sandboxing is
  strongest for SDK and headless workers that declare it.

**SASE:**
- Isolation is per-agent *workspace clones* (shared git objects), with cleanup TTLs and
  rescue bundles. That is good for change isolation, but there is no process, network,
  or credential isolation.
- Provider subprocesses inherit the whole environment (`env = os.environ.copy()` in
  `claude.py`, `codex.py`, `agy.py`, `muse_provider.py`).
- Research and review agents read arbitrary web content, which is a prompt-injection
  vector, while holding a shell, every exported token, and write access to `~/.sase`.

### 3.7 Cost and usage

**Omnigent:**
- `PolicyEngine.record_usage` prices tokens, including cache read and write, from a
  model catalog. Totals go to `conversations.session_usage`; per-user per-day spend goes
  to `user_daily_cost`.
- Native harnesses report usage via `external_session_usage`.
- **`cost_budget`:**
  - Soft thresholds ASK once, with the approval stored on the root so sub-agents don't
    re-ask.
  - The **hard limit is a downgrade gate**: it DENYs only while on an "expensive" model
    rather than killing the session.
  - Unpriced models trigger an ASK.
- **Other caps:** `subagent_cost_budget` is attached per dispatch, and scheduled tasks
  carry `max_cost_usd`.

**SASE:**
- Excellent *subscription* awareness: `sase usage` probes provider usage windows
  (5-hour, weekly); usage-limit errors auto-disable a provider until reset; size aliases
  and fallbacks route around exhausted providers.
- Per-run tokens are written to `usage.json`; agy writes none.
- **No $ or window-% accounting is rolled up per epic, clan, goal, or tribe, and nothing
  budgets admission.**

### 3.8 Durability, resilience, and testing discipline

**Omnigent:**
- **Resilience lab** (`docs/network-resilience.md`, `tests/e2e/resilience/`): a real
  server, host, runner, and real Claude/Codex CLIs behind fault proxies, across seven
  scenarios, with known gaps pinned as strict xfails.
- **CUJ map** (`designs/CUJ-MAP.md`): a journey tree × matrix (harness × client ×
  connection state × turn state) × invariants, with ⚠️ marking failure branches.
- **Feature map** (`feature-map/`): every user-facing feature, every user entry point,
  the test that drives each, and the rule "a fix is verified only when every entry point
  listed … has proof", checked by a CI contract test.

These are good *practices*. The heavy need for them follows from omnigent's distributed,
in-memory design.

**Documentation drift is visibly worse in omnigent.** The explorations found many stale
claims, which SASE's immutable decision records and generated memory largely avoid:
- harness counts (23 vs 27);
- table counts (17 vs 19);
- P1 probe counts (5 vs 6);
- `REUSABLE_USER_AGENTS.md` marked "PROPOSED" but implemented;
- AGENTSPEC skill-naming rules contradicted by the parser;
- design docs cited by code but absent from the tree (`RUNNER.md`,
  `SERVER_HARNESS_CONTRACT.md`, `LIVE_POLICIES.md`, …);
- a `workflow.py` docstring describing a removed DBOS engine.

### 3.9 Knowledge, memory, instructions

**Omnigent:**
- `AGENTS.md` plus `SKILL.md` skills. Discovery reads every vendor's native skill
  directories, and user-invocable skills appear in the web `/` menu.
- Long-term memory is only the optional Hindsight integration
  (`hindsight_retain`/`recall`/`reflect`) plus full-text conversation search.
- Project memory is proposed in `PROJECTS_PRD.md` but unimplemented.

**SASE is clearly ahead:**
- core, reference, and web memory;
- audited reads;
- a decision web with supersession;
- a glossary;
- task-type catalog;
- instruction bundles with delivery verification;
- an explicit, evidence-backed refusal to build retrieval before a corpus exists
  (decision `corpus-before-mechanism`).

### 3.10 Surfaces and remote execution

**Omnigent:**
- Web, desktop, and mobile UI over a REST/SSE API (94 OpenAPI paths); Slack; VS Code;
  a Python SDK.
- Sessions can be shared, co-driven (`omnigent attach`), and forked.
- Managed cloud sandboxes, with per-launch tokens, keepalive, a reaper, and Kubernetes
  warm pools.

**SASE:**
- TUI, CLI, Telegram, Android via the Rust `sase_gateway`, and Neovim.
- `%dispatch` to enrolled tailnet machines.
- A web UI appears only in a draft roadmap post.

For a single operator, SASE's surfaces cover the real needs. Omnigent's surface area is
the bulk of its code and of its bugs; most recent CHANGELOG entries are UI and
connection fixes.

---

## 4. Where SASE is ahead (keep these; don't regress toward omnigent)

1. **Durable, transcript-independent work state:** beads, plans, epics, goals, gates,
   artifacts, and Rust-owned stores. Omnigent has no plan or issue graph. Its "projects"
   are just new-chat defaults.
2. **Host-owned completion.** Omnigent agents commit and open PRs themselves, and a PR
   observer scrapes `gh pr create` output after the fact. SASE's
   declaration-plus-verified-finalizer protocol is a real trust boundary.
3. **Gates that never block.** Approvals survive restarts and burn no provider budget.
4. **Admission control:** holds, weighted queue budgets, and capacity. Omnigent's
   automations scheduler has "no distributed lease, so multiple replicas double-fire",
   no backfill, and no retry.
5. **Instruction delivery verification** and **audited memory**.
6. **Decision records.** Omnigent's docs drift is the counterexample.
7. **Per-agent full clones are the default.** Omnigent's worktrees are opt-in and
   prompt-driven: "Nothing in the framework enforces per-child worktrees".

## 5. Things to deliberately NOT copy

- **Long-lived, steerable sessions / mid-turn steer.** They contradict
  `single-turn-agents` and are the root of omnigent's resilience gaps.
- **Server + multi-tenant web stack** (accounts, OIDC, sharing, co-drive, managed cloud
  sandboxes). Enormous surface area for a team use case SASE does not have. The mobile
  gateway and Telegram already cover remote attention.
- **In-turn ASK that parks the agent** for up to a day. Use gates. SASE's version of
  "ask" should be *deny-and-redirect to a gate* (recommendation 1).
- **LLM-judged "policies"** (`prompt_policy`, `intent_based_authorization`,
  `detect_task_switch`). They are non-deterministic and fail open, and omnigent's own
  docs disclaim them as security controls. If SASE wants judgment, it already has
  mentors and gates.
- **Hindsight-style memory.** Blocked by `corpus-before-mechanism` until a corpus
  demands it.
- **Per-message LLM-judge model routing** ("smart routing"). SASE's deterministic size
  aliases and plan-size routing are easier to reason about. Revisit only with cost data
  from recommendation 5.

---

## 6. Ranked recommendations

Ranking weighs (a) expected value for a single operator running many agents, (b) fit
with SASE's existing decisions, and (c) cost. Effort is S (days), M (1–2 weeks of agent
epics), or L (multi-epic). Every user-reaching item should ship behind a beta flag with
a flag bead (`sase_flags` memory). Shared evaluation logic belongs in `sase_core` per
the Rust-core boundary.

### 1. Mechanical tool-call guardrails via provider hooks ("deny-and-redirect" policies) — **Effort M, highest value**

**What omnigent shows.** One policy engine can be enforced inside heterogeneous native
CLIs through their own hook systems: Claude `PreToolUse`, Codex, Cursor `preToolUse`,
a Pi extension, Hermes. Tool-call DENY fails closed. Deterministic builtins like
`blast_radius`, `worktree_guard`, and `read_only_os` parse shell argv, not prose.

**SASE gap.** Every provider runs with bypass flags. Several of SASE's most important
rules are prose in core memory, and SASE already has the Claude `PreToolUse` plumbing,
used for one rule (the helper guard).

**Proposed shape (SASE-native):**
- **Verdicts are only ALLOW or DENY inside a turn.** No in-turn ASK, preserving
  `gates-never-block`. Each DENY returns a *redirect reason* naming the sanctioned path:
  - "commit via `/sase_final`";
  - "run privileged commands via `/sase_sudo`";
  - "open other repos via `sase repo open`";
  - "read sidecar artifacts via `sase artifact read`";
  - "confirm destructive ops via `/sase_gate`".
  This is omnigent's ASK, reshaped into SASE's gate idiom.
- **Starter rule set** (all deterministic, argv/path-based):
  - `no_agent_vcs_mutation`: deny `git commit|push|rebase|reset --hard`, `gh pr
    create|merge` from agent turns. This makes `host-owned-completion` mechanical
    instead of prompt-plus-postcondition.
  - `workspace_escape`: deny writes outside the claimed `sase_<N>` workspace, its
    opened repos, and `/tmp`.
  - `blast_radius`: port omnigent's argv parser semantics for force-push, `rm -rf` of
    catastrophic targets, and hard reset to a remote.
  - `role_read_only`: for research, mentor, review, and question roles, deny
    Write/Edit/NotebookEdit and shell redirects into the repo.
  - `sidecar_direct_read` and `repo_web_fetch`: deny raw reads of sidecar artifact paths
    and `raw.githubusercontent.com` / GitHub file-content fetches.
  - Optionally, `guarded_recipe` could move from the Justfile shim into the hook.
- **Coverage first where hooks exist:** Claude (existing hook path), then Codex. Publish
  a per-provider coverage table like the existing helper-coverage table in
  `docs/agent_providers.md`. Providers without hooks stay prompt-only, and that is
  stated rather than hidden.
- **Record every DENY** as a triage-style annotation on the run (Tools card / FINAL
  card), so rules can be tuned from evidence.

**Risks.** False positives blocking legitimate work. Mitigate by starting
report-only (log what would be denied) for one soak period, then flipping per rule.

### 2. Vendor-diverse, contract-only review for land agents and mentors — **Effort S–M, high value**

**What omnigent shows.** Polly's `cross-review` has three parts:
- The reviewer must be from a **different vendor** than the implementer.
- It sees **only the diff snapshot (with base/head SHAs) plus the acceptance contract**,
  never the implementer's transcript or worktree.
- Blocking issues go back to **the same implementer conversation**, looping with an
  escalation cap.

Omnigent runs this pattern on its own PRs (`polly-review.yml`).

**SASE gap:**
- The land agent runs on `@large`/`@xlarge` with no provider-exclusion constraint, and
  is primed with implementer bead notes.
- Mentors have no author-relative provider selection.
- SASE's size aliases already span multiple providers (decision
  `size-alias-effort-ladder`), so the pool for diversity exists.

**Proposed shape:**
- Add an **author-relative exclusion to model resolution**, for example a resolver
  option or directive meaning "resolve this alias excluding the provider(s) that
  authored commits X..Y" (from agent/Patch metadata). Use it in the land agent and in
  mentors.
- Add a **contract-only review mode** for mentors and the land agent's verification
  step:
  - Inputs: the diff snapshot plus the plan's acceptance criteria and bead
    descriptions. Exclude bead *notes* and chats until after an independent verdict is
    written.
  - Then let the land agent reconcile.
- **Route blocking findings back to the implementer as a session successor** of the
  original phase agent (SASE sessions already support successors), rather than having
  the land agent fix everything itself.

**Why rank this high.** It is cheap, reuses existing machinery (aliases, sessions,
mentors), and directly attacks the most common multi-agent failure: same-model
blind spots plus narrative contamination.

### 3. A provider capability matrix with an executable conformance bench — **Effort M, high value**

**What omnigent shows.**
- `HarnessCapabilities` as declared data, plus `tests/harness_bench/`:
  - 12 probes;
  - three drivers;
  - `reconcile()` → `DRIFT`.
- It has caught real declaration errors.

**SASE gap.**
- SASE's adapter decision depends on per-CLI mechanisms that can silently break on any
  CLI release:
  - disabling background and wake;
  - wait guards;
  - helper channels;
  - tool-call capture;
  - usage capture;
  - resume;
  - instruction channels.
- These facts live in prose tables and scattered methods.
- `sase instructions verify` covers instruction delivery only, and never gates.

**Proposed shape:**
- **Declare one capability row per provider** (Rust- or Python-owned data), covering:
  - `single_turn_enforcement` (mechanical | guard | prompt-only);
  - `background_disabled`;
  - `wake_disabled`;
  - `helper_channel`;
  - `tool_call_capture`;
  - `usage_capture`;
  - `thinking_capture`;
  - `resume`;
  - `instruction_channels`;
  - `policy_hook` (for recommendation 1);
  - `max_sync_wait`.
- **Add live probes** using cheap prompts, for example:
  - asking the model to schedule a wake-up must be refused or blocked;
  - a background task must not survive the turn;
  - `tool_calls.jsonl` must be non-empty after a forced tool call;
  - `usage.json` must be populated;
  - the helper guard must block `sase final` from a helper;
  - the policy hook must DENY a canary command.
- **Run the bench in three places:**
  - on `sase update` / agent-CLI upgrade;
  - as a scheduled full-CI or AXE job;
  - on demand via `sase doctor -D`.
- **On `DRIFT`:** notify, and optionally soft-disable the provider for non-critical
  roles.
- **Fold `instructions verify` in** as one probe family, so there is one source of
  truth.

### 4. Environment allowlisting for provider subprocesses — **Effort S, medium-high value (cheapest security win)**

**What omnigent shows.**
- Two-layer env allowlists (`_RUNNER_ENV_ALLOWLIST`, `agent_env.py`): process
  essentials plus the harness's own credential family plus explicit `env_passthrough`.
- The rationale is stated: an agent can run `env` and exfiltrate keys.

**SASE gap.** `os.environ.copy()` for every provider. Because completion is host-owned,
agents need *fewer* credentials than in omnigent. For example, pushes and PRs are done
by host finalizers.

**Proposed shape.** For each provider, build the env from:
- a base allowlist;
- the provider's own auth variables;
- the `SASE_*` variables agents need;
- a `sase.yml` `agent_env.passthrough` list (per project and per role).

Log what was dropped once per run, so breakage is diagnosable. Start in report-only
mode (compute and log the drop set) before enforcing.

### 5. Cost and usage rollups with budget-aware admission — **Effort M, medium-high value**

**What omnigent shows.**
- Per-session, per-user-day, and per-period $ accounting.
- Soft thresholds that ASK once per root.
- A hard limit that **downgrades the model** rather than killing the run.
- Sub-agent budgets attached at dispatch.
- Unpriced models trigger ASK, not silence.

**SASE gap.** SASE knows tokens per run and provider window state, but not "what did
this epic, clan, or goal cost", and nothing budgets admission.

**Proposed shape:**
- **Normalize per-run cost** into two units:
  - **window-%** of each subscription's 5h and weekly windows, which matters for
    subscription CLIs;
  - **$-equivalent** at list price, for comparability and API-billed paths.
- **Roll up** by clan, epic, tribe, and goal (the goal ledger is the natural owner
  later). Show it in Statistics and on gate previews: "this epic's phases used ~18% of
  Claude weekly".
- **Admission integration:** an optional `budget:` on `sase bead work` / `%clan`.
  - When the projected or actual spend crosses a soft threshold, raise a gate.
  - When it crosses the hard threshold, *step the size alias down* instead of refusing
    (omnigent's downgrade-gate idea), for example `@large → @medium` for remaining
    phases.
  - This fits holds and capacity, which already live in admission.

### 6. First-class "join" continuation for agent-initiated fan-out — **Effort S–M, medium value**

**What omnigent shows.** `sys_session_send` is async. The parent ends its turn, and a
mechanical notice wakes it with an inbox of structured child results when children
finish. Polly's whole orchestration loop rests on this. It is fully compatible with
single-turn semantics.

**SASE gap.** `requester_continuation` offers only `resume_requester`, which wakes when
the *gate settles*, and `terminal_handoff`. Joins are hand-built with `%wait`.

**Proposed shape:**
- Add `mode: "join_launched"`. After approval, the requester's successor is launched
  with an implicit `%wait` on every approved slot, and is admitted only when all have
  reached a terminal state.
- Its prompt gets a generated **inbox block** per child: status, final reply excerpt,
  artifact refs, and the FINAL card summary.
- Keep LaunchApproval as-is. The human still approves the fan-out; the join is just the
  mechanical wake.
- This makes Polly-style "plan → fan out → cross-review → fix loop" expressible as an
  ordinary SASE session without long-lived agents.

### 7. Thrash and loop detection over normalized tool calls — **Effort S, medium value**

**What omnigent shows.**
- `detect_thrashing`: last N tool results all errors, or the window error rate ≥ 0.8.
- `detect_loop` and `max_tool_calls_per_session`.

**SASE gap.**
- SASE already normalizes tool calls into `tool_calls.jsonl` for most providers.
- It has only provider-specific stall recovery (the agy no-progress path) and the
  single-turn wait guard.
- Agents that spin on a failing command burn usage windows silently.

**Proposed shape:**
- **A scheduler routine (or Rust scan) over live runs** flags:
  - N consecutive failing tool calls;
  - repeated identical commands;
  - an extreme tool-call count.
- **On a flag:**
  - Emit a notification with a "kill / hold / let run" choice.
  - Annotate the run, triage-style; per decision
    `triage-annotates-does-not-change-exit-codes`, it never changes outcomes by itself.

### 8. A generic ACP provider adapter — **Effort M–L, medium strategic value**

**What omnigent shows.** One `acp:<slug>` harness lets users register any Agent Client
Protocol agent by config; goose, qwen, grok, and jcode use it. ACP's
`session/prompt → stopReason` is naturally *one turn*. Its `session/request_permission`
is a natural policy hook point.

**SASE gap.** Each new CLI costs a bespoke provider: command construction, stream
parser, tool-call capture, usage. SASE already speaks ACP (Grok usage collector).

**Proposed shape:**
- A `sase_llm` provider that drives any configured ACP command headlessly:
  - one `session/prompt` per turn;
  - tool calls captured from `session/update` notifications into `tool_calls.jsonl`;
  - permission requests answered by the recommendation-1 policy engine (ALLOW/DENY,
    never ASK);
  - usage taken from ACP extensions where offered.
- Keep bespoke providers where they add value (Claude, Codex). Use ACP to onboard the
  long tail cheaply: Gemini CLI, Goose, Kiro, Devin, and future CLIs.
- Capability rows (recommendation 3) declare what each ACP agent actually supports.

### 9. A feature/entry-point map for SASE's user surfaces, as a memory web — **Effort S–M, medium-low value**

**What omnigent shows.** `feature-map/*.md` has a fixed contract:
- sub-feature IDs;
- every user entry point;
- the test that drives each;
- gotchas.

It comes with a rule — "a fix is verified only when every entry point listed … has
proof" — plus an isolated `verify-env` and a CI contract test. The CUJ map adds a
journey × surface matrix with failure branches marked.

**SASE gap.** The TUI is ~543K lines with many parallel entry points for the same
feature: keymap, palette, command line, CLI, Telegram button, mobile gateway. Agents
verifying a change often prove one path. SASE has `sase screenshot` and visual goldens
but no per-feature entry-point inventory.

**Proposed shape:** a `features` memory web with one strand per user-facing feature in
the omnigent four-section shape, read on demand (`sase memory read features:<slug>`).
Add a lint that every strand names a driving test or explicit manual steps. This fits
SASE's memory-web model and stays out of core context.

### 10. Optional OS sandbox profile for untrusted-input, read-only roles — **Effort L, medium value (security), lower rank due to cost and friction**

**What omnigent shows.**
- bwrap/Seatbelt/seccomp profiles, an egress allowlist proxy, and a credential proxy.
- Its own default for `omnigent claude` still appears to be unsandboxed, which shows
  how hard it is to sandbox full coding CLIs.

**SASE gap.** Research and review agents ingest untrusted web content with full
filesystem, network, and credentials.

**Proposed shape:**
- **First,** use vendors' *own* sandbox modes instead of bypass flags for read-only roles
  (research, mentor, review), where a CLI offers a workspace-scoped mode. Codex's
  sandbox modes are the clearest case.
- **Later,** add a `%sandbox` directive wrapping the provider in bwrap:
  - workspace read-only (or write limited to an artifacts dir);
  - `$HOME` hidden except provider auth dirs and the specific `~/.sase` paths the
    `sase` CLI needs.
- **Pair it with recommendations 1 and 4.** Most of the value comes from the hook plus
  env scrubbing, at a fraction of the cost.

### 11. Adopt external CLI sessions into SASE — **Effort S–M, low-medium value**

**What omnigent shows.** `omnigent/session_import/local.py` imports local transcripts
from seven CLIs (Claude, Codex, Kimi, Kiro, OpenCode, Pi, Qwen) into first-class
sessions, trimming over-2 MB transcripts to the last compaction boundary.

**SASE angle.** A `sase agent adopt <provider> <session-id>` command would wrap an
ad-hoc Claude Code or Codex session into a SASE agent session. That gives it a deck
entry, a `#fork:` source, and finalizer-driven completion. Work started outside SASE
could then enter the structured flow without copy-paste.

### 12. Editable queued follow-ups for running agents — **Effort S, low value (UX)**

**What omnigent shows.** Queued messages are client-side, editable, deletable, and
reorderable until the session goes idle, then auto-flushed.

**SASE angle.** If it is not already ergonomic in the TUI, add a "queue follow-up" action
on a running agent. It would create a pending session successor, visible and editable in
the deck until the current turn ends. It must be a successor turn, not a steer, to keep
`single-turn-agents`.

### Summary table

| Rank | Recommendation | Effort | Main SASE decision it must respect |
|---|---|---|---|
| 1 | Hook-enforced deny-and-redirect tool-call guardrails | M | `gates-never-block`, `host-owned-completion`, Rust boundary |
| 2 | Vendor-diverse, contract-only review (land and mentors) plus loop-back to implementer | S–M | `size-alias-effort-ladder` |
| 3 | Provider capability matrix plus conformance bench (`DRIFT`) | M | `adapters-normalize-harnesses` |
| 4 | Provider env allowlist | S | `host-owned-completion` (agents need fewer creds) |
| 5 | Cost/usage rollups plus budget-aware admission with alias step-down | M | `hold-pull-fail-open` / admission design |
| 6 | `join_launched` requester continuation (inbox wake) | S–M | `single-turn-agents`, LaunchApproval |
| 7 | Thrash/loop detection over `tool_calls.jsonl` | S | `triage-annotates-does-not-change-exit-codes` |
| 8 | Generic ACP provider | M–L | `adapters-normalize-harnesses` |
| 9 | Feature/entry-point map memory web | S–M | `corpus-before-mechanism` (the map *is* the corpus) |
| 10 | Optional sandbox for read-only, untrusted-input roles | L | — |
| 11 | Adopt external CLI sessions | S–M | `single-turn-agents` (adopted session becomes turn history) |
| 12 | Editable queued follow-ups | S | `single-turn-agents` |

---

## 7. Caveats and unverified points

- **Nothing was executed.** Bench results, the zygote memory savings, and sandbox
  behavior come from code and docs.
- **Some omnigent design docs are missing.** Code cites docs that are not in the
  open-source tree (`designs/RUNNER.md`, `SERVER_HARNESS_CONTRACT.md`,
  `LIVE_POLICIES.md`, `STEERABLE_SUBAGENTS.md`, …), so some rationale could not be read.
- **Native sandbox posture is inferred.** The claim that `omnigent claude` runs
  unsandboxed by default comes from the generated spec (`sandbox: {type: none}`)
  combined with terminals inheriting `os_env`. It contradicts the README's bwrap
  statement, and I did not run it to confirm.
- **Policy coverage outside Claude and Codex was not traced.** Omnigent's
  enforcement inside Cursor, Hermes, Pi, and Antigravity is described from adapter code
  only.
- **SASE size figures are raw line counts.** The Rust `sase-core` repo was not
  measured. Research-swarm macro bodies (`sase-research-artifacts` plugin) were not
  inspected.
- **Two SASE gaps were checked only in the main repo.** "No $ budgeting" and "no join
  continuation" were verified there; a plugin could implement either without my
  noticing.

## Appendix: key references

**Omnigent** (repo-relative):
- Overview: `README.md`, `AGENTS.md`
- Execution core:
  - `omnigent/server/API.md`, `omnigent/server/DBSPEC.md`
  - `omnigent/runner/_zygote.py`, `omnigent/runner/subagent_work.py`
  - `omnigent/runtime/harnesses/_scaffold.py`
  - `omnigent/inner/executor.py`
- Harness capabilities and bench:
  - `omnigent/harness_capabilities.py`, `omnigent/harness_plugins.py`
  - `docs/harness-bench-design.md`, `tests/harness_bench/`
- Policies:
  - `docs/POLICIES.md`
  - `omnigent/policies/builtins/{orchestration,safety,cost,context}.py`
  - `omnigent/runtime/policies/engine.py`, `omnigent/runtime/policies/builder.py`
  - `omnigent/native/native_policy_hook.py`
- Sandboxing, egress, credentials:
  - `omnigent/inner/{bwrap_sandbox,seatbelt_sandbox,_seccomp,agent_env,credential_proxy}.py`
  - `omnigent/inner/egress/`
  - `designs/SANDBOX_CREDENTIAL_PROXY.md`
- Polly: `examples/polly/config.yaml`, `examples/polly/skills/{fanout,cross-review,investigate}/SKILL.md`
- Interaction and resilience: `docs/QUEUE_STEER_DESIGN.md`, `docs/network-resilience.md`
- Verification maps: `designs/CUJ-MAP.md`, `feature-map/README.md`
- Other: `docs/AUTOMATIONS.md`, `omnigent/session_import/local.py`

**SASE** (repo-relative):
- Docs:
  - `docs/architecture.md`, `docs/llms.md`, `docs/agent_providers.md`
  - `docs/agent_sessions.md` (LaunchApproval / requester continuation)
  - `docs/mentors.md`, `docs/beads.md`, `docs/tool.md`
- Code:
  - `src/sase/llm_provider/{claude,codex,agy,qwen,opencode,grok,muse_provider}.py` (bypass flags, env)
  - `src/sase/llm_provider/_claude_helper_guard.py`
  - `src/sase/agent/launch_request_continuation.py`
  - `src/sase/default_config.yml` (`bd/land_epic`, `epic_lander_model`)
  - `src/sase/config/sase.schema.json` (`mentor_profiles`)
- Decisions: `single-turn-agents`, `adapters-normalize-harnesses`,
  `host-owned-completion`, `gates-never-block`, `corpus-before-mechanism`,
  `size-alias-effort-ladder`.
