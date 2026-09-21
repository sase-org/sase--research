# Generic ACP Provider Plugin for SASE: Implementation Research

- **Type:** independent researcher report (`mus`)
- **Date:** 2026-09-21
- **Question:** The `multi_cli_orchestration_vs_sase.md` synthesis recommends SASE
  "Add a generic ACP provider plugin." What is the best way to implement this?
  Is it a good idea? What would I change?
- **Input read (audited):**
  `sase artifact read "research:202609/multi_cli_orchestration_vs_sase/multi_cli_orchestration_vs_sase.md"`.
  I did not open either prior-swarm researcher report (`__cld.md` / `__mus.md`
  in the `multi_cli_orchestration_vs_sase/` subdirectory); all SASE-side claims
  below are from first-hand reads of the workspace checkout, and all
  ACP-side claims from the `agent-client-protocol`, `python-sdk`, and
  `registry` checkouts opened via `sase repo open`.
- **Bottom line:** Yes, build it — but not as the source report describes it.
  The "one client covers everything, plus free resume and usage" framing is
  overstated in three load-bearing ways (launch argv is heterogeneous,
  `usage_update` is not billing usage, cross-process resume is agent-dependent).
  The good news: SASE's provider system is *already* a plugin system, a bounded
  JSON-RPC transport already exists, and the spec sanctions auto-approving
  permissions. The recommended shape is one shared sync ACP client plus one
  entry point per validated agent (not one `acp` provider), additive alongside
  the natives, gated by a per-agent capability spike.

---

## 1. What the source report recommends (recap)

§7.4 item 1 of the synthesis (lines ~440–447):

1. One generic ACP client covering Cursor, Copilot, Droid, Amp, Goose, Kimi,
   Junie, Cline, Pi "and more".
2. It would give SASE standard `session/resume` and `usage_update`.
3. It could eventually replace the bespoke Qwen, OpenCode and agy plugins.
4. Keep native plugins where the headless path is richer (Claude, Codex, Muse).
5. Notes `src/sase/llm_provider/usage/grok.py` already speaks ACP to Grok Build
   for its billing probe.

I agree with the direction and with point 4. Points 1–3 and 5 need correction
before they become work items.

---

## 2. SASE-side facts (code-verified in this checkout)

All paths relative to the sase repo.

### 2.1 Providers are already plugins — no new machinery is needed

- Providers are discovered via
  `importlib.metadata.entry_points(group="sase_llm")`
  (`src/sase/llm_provider/registry.py:3-7`) and dispatched through a pluggy
  `PluginManager` (`_plugin_manager.py`). Eight entry points are registered in
  `pyproject.toml:206-214`: `agy`, `claude`, `codex`, `fakey`, `grok`,
  `muse`, `opencode`, `qwen`.
- The hook surface a new provider must implement is fully specified in
  `src/sase/llm_provider/_hookspec.py`: core dispatch (`llm_invoke`,
  `llm_resolve_model_name`, `llm_provider_name`) plus metadata hooks that are
  all optional-with-sane-defaults (`llm_autodetect_cli_name`,
  `llm_install_metadata` for `sase agent-cli`, `llm_auth_evidence` for doctor,
  `llm_interactive_cli`, `llm_default_retry_config`,
  `llm_default_usage_limit_config`, `llm_usage_capabilities` /
  `llm_usage_probe`, `llm_hidden_from_*`).
- **Consequence:** "add a generic ACP provider plugin" means *one new module
  plus entry-point lines*, reusing `invoke_agent()` (`_invoke.py`),
  preprocessing/postprocessing, routing, disable state, and the TUI for free.
  The source report's costing intuition ("each provider costs ~500–2,800 lines
  of bespoke Python", §7.2) is roughly right for the provider modules
  themselves (`qwen.py` 344, `opencode.py` 345, `agy.py` 646, `grok.py` 431,
  `claude.py` 556, `codex.py` 548 lines), but the number overstates what a new
  ACP agent costs once the shared client exists: it should cost one table row
  plus capability quirks, not a new 400-line module.

### 2.2 A bounded JSON-RPC transport already exists — but it cannot drive a turn

- `src/sase/llm_provider/usage/transport.py` provides `JsonLineSession`: argv-
  spawned child, JSON lines over stdio, correlated response ids, output bounds,
  killable. `usage/grok.py` uses it to send `initialize` + the vendor
  extension `_x.ai/billing` to `grok --no-auto-update agent stdio`.
- Its documented contract is explicit (transport.py:40-46): it **"skips
  notifications" and "never services unsolicited requests"**, and
  `UNSERVICED_REQUEST_METHODS` includes `session/new`.
- A full ACP *prompt* flow, unlike a probe, **must** service agent→client
  traffic: the turn only completes if the client answers
  `session/request_permission`, `fs/*`, and terminal requests, and cancellation
  requires answering `$/cancel_request` for in-flight requests
  (spec `cancellation.mdx`). The probe transport is therefore a starting point,
  not a reusable client. Extending it (or writing a sibling duplex client on
  the same bounded-transport core) is the single biggest implementation chunk.

### 2.3 Providers are synchronous; the official SDK is not

- Every provider implements blocking `invoke()` on threads with
  `start_interrupt_monitor` / `start_completion_watchdog`. There is no asyncio
  in the provider runtime (`asyncio_mode = "auto"` in `pyproject.toml` is test
  config only).
- The official Python SDK (`python-sdk`, v0.12.1, schema v1.23.0) is
  asyncio-based with a **pydantic ≥ 2.7** dependency. SASE's runtime
  dependencies (`pyproject.toml`) are lean — jinja2, pluggy, textual, etc. —
  and do **not** include pydantic or any async framework.
- **Consequence:** adopting the SDK means either bridging an event loop inside
  the sync invoke path or accepting pydantic into the dependency closure for
  schema types. My recommendation (§6) avoids both: hand-roll a small sync
  client against the vendored method surface, and treat the SDK checkout as a
  conformance reference, not a runtime dependency.

### 2.4 Routing/disable state is keyed by provider name and lives in Rust core

- `provider_disable.py` / `provider_priority.py` / effort resolution call
  through `sase.core.rust` (`require_rust_binding`). Provider identity is the
  entry-point name string throughout.
- **Consequence 1:** one entry point per ACP agent (e.g. `acp-goose`,
  `acp-opencode`) reuses per-provider disable windows, priority, retry config,
  usage-limit patterns, and pool membership with zero Rust changes. A single
  `acp` provider would lump every ACP agent into one disable bucket — one
  agent's quota drain would sideline all of them.
- **Consequence 2:** no Rust wire/API change is needed for the invoke path at
  all. Session-id persistence for resume can live in the agent artifacts dir
  (Python side), next to `interrupt_log.jsonl`.

### 2.5 Interrupt/cancel today destroys sessions; ACP cancel preserves them

- `qwen.py:285-299` shows the current interrupt pattern: kill the subprocess,
  rebuild a "Work So Far" text prompt, relaunch. Claude's interrupt path starts
  a fresh session (`active_session_uuid = None`) even though `--resume` is
  already wired for wait-continuations (synthesis §Handoff, lead-verified).
- ACP `session/cancel` ends the *turn* while the *session* survives for
  `session/resume` — strictly better, **if** the agent persists sessions across
  processes (see §4.3, the main risk).

### 2.6 Pools are config, and ACP agents are absent from them

- `model_alias_defaults.yml` is the single edit point for `@xsmall`…`@xlarge`;
  today `@large`/`@xlarge` are Claude/Codex/Grok only, and Qwen/OpenCode are in
  no pool (matches the synthesis). Adding e.g. `acp-opencode/<model>` to a pool
  target is a config-line change once the provider exists — but see §4.5 on
  model mapping.
- Test skew is real: provider tests cluster around Claude/Codex. `fakey.py`
  (313 lines) shows the established pattern for a scripted fake provider;
  ACP work needs an equivalent **fake ACP agent** (a script speaking the
  `initialize → session/new → session/prompt → session/update…` subset).

---

## 3. ACP-side facts (verified in the opened checkouts)

### 3.1 The stable method surface

From `python-sdk/schema/schema.json` (schema v1.23.0, `PROTOCOL_VERSION = 1`)
and `agent-client-protocol/docs/protocol/v1/`:

| Method | Status | SASE use |
|---|---|---|
| `initialize` | stable | capability discovery per agent (`authMethods`, session capabilities) |
| `session/new`, `session/prompt` | stable | the invoke path |
| `session/cancel` | stable | interrupt path; replaces SIGKILL with a resumable session |
| `session/list`, `session/load`, `session/resume` | stable | resume-after-interrupt, drain-continue — **subject to §4.3** |
| `session/fork` | **UNSTABLE** ("not part of the spec yet, may be removed") | do not build cross-provider forks on it |
| `session/close`, `session/delete` | stable | session hygiene |
| `session/set_mode`, `session/set_config_option` | stable | per-agent model/effort mapping knob |
| `session/update` (notification) | stable | carries `AgentMessageChunk`, `ToolCallStart/Progress/Update`, `AgentThoughtChunk`, `UsageUpdate` — maps directly onto SASE's `live_reply.md` / `tool_calls.jsonl` / thinking capture |
| `session/request_permission` | stable | **client MAY auto-allow** per user settings (`tool-calls.mdx:191`) — spec-sanctions SASE's bypass posture; on cancel the client MUST answer `cancelled` |
| `authenticate` | stable | agents advertise `authMethods`; each agent keeps its own auth (subscription passthrough, not API keys) |

### 3.2 Launch argv is heterogeneous — the registry proves it

`agent.json` `distribution` blocks (registry checkout, all versions current as
of read):

| Agent | ACP launch | Form |
|---|---|---|
| Goose | `goose acp` | subcommand |
| Kimi (`kimi` v1.51.0, mirrors Goose) | `kimi acp` | subcommand |
| OpenCode | `opencode acp` | subcommand |
| Cursor | `cursor-agent acp` | subcommand |
| Kilo | `kilo acp` | subcommand |
| Devin | `devin acp` | subcommand |
| Cline | `cline --acp` (npx package `cline`) | flag |
| Copilot CLI | `@github/copilot --acp` (npx) | flag |
| Qwen Code | `@qwen-code/qwen-code --acp` (npx; installed `qwen --acp`) | flag |
| Junie | `junie --acp=true` | flag with value |
| Factory Droid | `droid exec --output-format acp-daemon` + `DROID_DISABLE_AUTO_UPDATE` env | bespoke |
| Grok Build | `grok agent stdio` (matches `usage/grok.py:59`) | bespoke |
| Antigravity | `agy_acp_server[.par]` sidecar adapter binary | separate binary |
| Claude / Codex | `@agentclientprotocol/claude-agent-acp`, `codex-acp` npx adapters | adapter over vendor CLI |
| pi-acp | `pi-acp` (npx adapter) | adapter |

There is no uniform "run X in ACP mode" spelling. A generic plugin therefore
still needs a **per-agent descriptor table** (argv, env, capability quirks,
model mapping). The genericism is in the protocol client, not in zero
per-agent data. Consuming the registry JSON at runtime for this is not viable
either: registry entries describe *downloadable distributions* (per-OS
archives, npx packages), not the locally installed CLI SASE must detect and
launch — SASE needs its own table with `SASE_<AGENT>_PATH` overrides, exactly
as `_qwen_bin()` does today.

### 3.3 Auth stays with the agent (strategically good)

ACP negotiates auth at `initialize`; agents bring their own credentials. The
adapter entries (claude-acp, codex-acp) exist precisely to reuse vendor-CLI
subscriptions. This preserves SASE's "wrap the real CLIs, keep subscription
eligibility" positioning (synthesis §4.4) — an ACP plugin does **not** push
SASE toward API-key billing the way a model-proxy would. Per-agent
verification is still needed (the synthesis already flags Omnigent-style gaps).

---

## 4. Critique: seven adjustments to the plan

### A1. (CORRECT, reframe) "Generic plugin" is a table + client, not an architecture project

The plugin machinery exists (§2.1). The work is: one sync ACP client
(`~300–500` lines on the `JsonLineSession` core), one descriptor table, one
`AcpProvider` base class, N entry-point registrations, and per-agent
metadata hooks. Frame the bead as client + pilot agents, not as "plugin
system support".

### A2. (OVERSTATED) `usage_update` does not give SASE the usage data it needs

`UsageUpdate` is `{used, size, cost?}` — **context-window pressure**, not token
in/out counts and not subscription-window data. SASE's per-run `usage.json`,
telemetry (`LLM_INPUT_TOKENS`/`LLM_OUTPUT_TOKENS`), and provider-disable
decisions need billing/token data, which in ACP today comes only from
**vendor extensions** (exactly how Grok's `_x.ai/billing` works — the
"already speaks ACP" precedent in point 5 is a probe hitting a vendor
extension, not standard ACP, and does not transfer to other agents). It also
does nothing for the Codex/agy usage gaps, which are headless-CLI gaps, not
protocol gaps.

**Adjustment:** treat `UsageUpdate` as a context-pressure signal (useful for
continuation-budget decisions in `continuation_budget*.py`), and keep
expecting per-agent billing probes/extensions for routing-grade usage. Do not
promise "standard usage" as an ACP deliverable.

### A3. (MISSING) The client must be full-duplex — this is the hard part

Point 5's probe never answers an agent request. A turn-driving client must:
auto-allow `session/request_permission` (spec-sanctioned; record the posture
visibly since SASE already bypasses everywhere), decline-or-service `fs/*`
(prefer declining `write_text_file` outside the workspace; the agent has the
workspace anyway via `cwd`), service-or-decline terminal requests, and answer
`$/cancel_request` during `session/cancel`. Skipping this is not a
simplification — agents block on unanswered permission requests and the turn
hangs. Budget for it explicitly.

### A4. (RISK) Cross-process resume is agent-dependent — spike it, don't assume it

`session/load` requires the agent's `loadSession` capability; `session/resume`
requires `sessionCapabilities.resume`. Both are capability-gated, and worse:
SASE spawns a **fresh agent process per invoke**, so resume-after-interrupt
and drain-continue only work if the agent persists sessions to disk
independently of the client connection. Nothing in the spec guarantees this;
it must be verified per agent with a live CLI (unauthenticated checkouts
cannot prove it). If an agent's sessions die with the process, ACP buys SASE
nothing on D6 for that agent and the resume wiring must be per-agent-gated,
not assumed.

**Adjustment:** Phase 0 is a capability spike per candidate agent
(`initialize` → capabilities, kill-process → `session/list|load|resume`,
permission behavior, `UsageUpdate` semantics, model selection mechanism).
No agent joins the table without passing it. `session/fork` being UNSTABLE
also rules out building SASE's cross-provider `#fork` on native fork for now;
keep text-replay forks and revisit when the method stabilises.

### A5. (PREMATURE) Do not schedule replacing Qwen/OpenCode/agy

"Eventually replace" inverts the burden of proof. The natives encode real
knowledge: Qwen's `--yolo`/stream-json quirks, OpenCode's run format, agy's
version-pinned tool-call parsing, per-provider usage-limit patterns
(`llm_default_usage_limit_config`), and pool membership. Replacement should be
a per-agent decision gated by a **CI capability matrix** (usage, tool calls,
thinking, resume — the synthesis's own rec #3, extended with ACP capability
columns), not a roadmap line. Note also the agy case specifically: ACP for
Antigravity goes through the `agy_acp_server` sidecar adapter binary, not the
`agy` CLI — replacing the native would swap a Google-owned CLI dependency for
an adapter-binary dependency, which needs its own install story in
`llm_install_metadata`.

### A6. (DESIGN) One entry point per agent, not one `acp` provider

§2.4 consequence 1 is decisive: separate entry-point names (`acp-goose`,
`acp-opencode`, …) reuse per-provider disable windows, priorities, retry and
usage-limit configs, `sase agent-cli` inventory, doctor auth evidence, and pool
grammar unchanged. A single `acp` provider would need new multiplexing logic
in exactly the Rust-core state the project is trying to keep stable, and one
agent's drain would disable all of them. The shared code lives in one
`AcpProvider` base class; the entry points are thin subclasses carrying their
descriptor row.

### A7. (MISSING) Model/tier mapping is per-agent work, not free

SASE invokes by tier (`large`/`small`) plus optional override; ACP agents pick
their own models, steerable (if at all) via argv, env, `session/set_mode`, or
`session/set_config_option` — differently per agent. Each descriptor row needs
a `tier_to_model` mapping plus a "no mapping: use agent default" fallback, and
`invocation_option_args` needs a per-agent effort story (most ACP agents have
no reasoning-effort flag; follow the Qwen precedent: explicit `%effort`
raises, config default is skipped). Pool membership for a new ACP agent should
start conservative (e.g. `@xsmall`/`@small` only, mirroring how `agy` is
`@xsmall`-only today) until its parity row is green.

---

## 5. Adjusted requirements (deltas vs the source recommendation)

| ID | Requirement | Delta |
|---|---|---|
| REQ-1 | Ship a shared **sync** ACP client in `src/sase/llm_provider/acp/` reusing the bounded `JsonLineSession` core; full-duplex (permission auto-allow, fs/terminal decline-or-service, cancel cascade) | ADD (hard part the plan omits) |
| REQ-2 | Per-agent descriptor table (argv, env, `SASE_<AGENT>_PATH`, tier→model, effort policy, capability flags from spike); registry JSON is reference only, not runtime input | ADD (replaces "one client covers N agents") |
| REQ-3 | One pluggy entry point per validated agent on a shared `AcpProvider` base; no Rust-core changes | ADJUST (was: "a generic ACP provider plugin" singular) |
| REQ-4 | Phase-0 capability spike per agent (cross-process load/resume, permission behavior, UsageUpdate semantics, model selection); admission-gated | ADD |
| REQ-5 | `UsageUpdate` wired to continuation-budget/context-pressure only; billing usage stays per-agent probes/extensions | ADJUST (was: "standard usage_update") |
| REQ-6 | Interrupt path uses `session/cancel` + `session/resume` where the agent's spike passed; otherwise current behavior | ADJUST (was: blanket "standard session/resume") |
| REQ-7 | CI capability matrix per provider **including ACP capability columns**; fake-ACP-agent test harness (extend `fakey` pattern) | KEEP + extend (agrees with source rec #3) |
| REQ-8 | Pilot additive alongside natives (start: OpenCode + Goose — both `X acp` form, both already in SASE's orbit); natives retire only per-agent on green matrix | ADJUST (was: "eventually replace qwen/opencode/agy") |
| REQ-9 | No dependency on the asyncio/pydantic SDK at runtime; SDK checkout stays a conformance reference; no `session/fork` dependency while UNSTABLE | ADD |
| REQ-10 | `sase agent-cli` install metadata + doctor auth evidence per agent from day one (npx-distributed agents need npm-manager rows) | ADD (integration the plan omits) |

Out of scope (explicit): MCP `mcpServers` session setup (later; SASE has no MCP
config anywhere today), live `session/update` streaming into the TUI (batch
normalize to existing artifacts first), Claude/Codex/Muse migration (natives
stay; adapters are a fallback, not a target).

---

## 6. Recommended solution

**Phase 0 — spike (days, live CLIs required, no committed code):** for
OpenCode and Goose: `initialize` capabilities; kill-process then
`session/list`/`load`/`resume`; permission-request behavior; what
`UsageUpdate.used/size` actually counts; how (if at all) the model is
selectable. Go/no-go per agent. If neither agent's sessions survive the
process, stop: ACP still has value for breadth, but sell it as breadth, not
continuity.

**Phase 1 — thin shared client + one pilot agent:** `sase/llm_provider/acp/`
with `_acp_client.py` (sync, bounded, duplex), `_acp_agents.py` (descriptor
table), `provider.py` (`AcpProvider` base + thin per-agent subclasses),
`acp-opencode` entry point first (its headless behavior is already SASE's
closest analog and its registry entry is a plain `opencode acp`). Map
`session/update` events onto the existing normalized artifacts
(`live_reply.md`, `tool_calls.jsonl`, `usage.json` with context-pressure
fields marked as such). Declare install/auth metadata hooks. Add the
fake-ACP-agent harness and failure-injection tests (hang on permission request,
mid-turn cancel, unknown extension method `-32601`, malformed line).

**Phase 2 — second agent + resume wiring:** add `acp-goose`, then wire
`session/cancel` into the interrupt path behind the existing interrupt
monitor, with resume gated per-agent on the Phase-0 flag. Put pool membership
at `@xsmall`/`@small` first.

**Phase 3 — matrix and scale:** turn on the CI capability matrix (REQ-7) as
the admission gate for further agents (Cursor, Copilot CLI, Cline, Kimi,
Droid, Junie, Pi in roughly that order — subcommand-form first, npx/adapter
forms after the install story is proven). Only then discuss retiring any
native, per-agent, on green rows.

**What I would not do:** a single `acp` provider; the SDK as a runtime
dependency; native replacement as a goal; `session/fork`-based handoff;
runtime consumption of the ACP registry for launch config.

---

## 7. Risks and open questions

1. **Cross-process session persistence** (§4.3) — the plan's central bet, still
   unverified here (no authenticated CLIs in this environment). This is the
   first spike question, not a design assumption.
2. **Subscription-vs-API-billing per agent** — ACP preserves each agent's own
   auth, but whether e.g. Copilot CLI or Cursor over ACP bills the seat
   subscription or metered API (cf. the JetBrains Air caveat in the synthesis)
   needs per-agent confirmation; a wrong default burns user money.
3. **Permission auto-allow visibility** — spec-sanctioned but must stay loud:
   the TUI/doctor surfaces should show an ACP agent runs with auto-allowed
   tool calls, consistent with SASE's existing bypass posture.
4. **Protocol drift** — schema v1.23.0 moves fast with an UNSTABLE fork
   method; pin a supported schema version per release and re-run the matrix.
5. **Windows/POSIX** — SASE is POSIX-only (synthesis D10); several registry
   entries are Windows-shaped (`junie.exe`, `cursor-agent.cmd`). No action,
   but don't design install metadata that assumes otherwise.

---

## 8. Key sources

- **SASE (repo-relative, read first-hand):** `src/sase/llm_provider/base.py`,
  `_hookspec.py`, `_plugin_manager.py`, `registry.py`, `_invoke.py`, `qwen.py`,
  `usage/grok.py`, `usage/transport.py`, `usage/types.py`, `fakey.py`,
  `model_alias_defaults.yml`, `src/sase/skills/cli_list.py`, `pyproject.toml`
  (entry points §206-214, dependencies).
- **ACP spec checkout** (`gh:agentclientprotocol/agent-client-protocol`,
  `docs/protocol/v1/`): `tool-calls.mdx` (permission auto-allow),
  `cancellation.mdx` (cancel cascade), `authentication.mdx`,
  `session-setup`/`prompt-turn` semantics.
- **SDK checkout** (`gh:agentclientprotocol/python-sdk`): `examples/client.py`
  (client obligations), `schema/schema.json` (method surface, `UsageUpdate`
  shape), `pyproject.toml` (asyncio + pydantic dependency footprint).
- **Registry checkout** (`gh:agentclientprotocol/registry`): per-agent
  `agent.json` `distribution` blocks tabulated in §3.2.
- **Prior synthesis (audited read only):**
  `research:202609/multi_cli_orchestration_vs_sase/multi_cli_orchestration_vs_sase.md`.
