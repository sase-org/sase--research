# Adding Hermes Agent as a Fully Supported SASE Provider

> **Research query:** Add Nous Research's Hermes Agent (`NousResearch/hermes-agent`) as a new, fully supported SASE
> LLM provider. Research the best way to implement it, review the earlier Hermes research in the research sidecar,
> and end with a recommended solution.

- **Researcher:** cld (one of five independent researchers)
- **Date:** 2026-10-19
- **Pins:**
  - **Hermes Agent:** `8f5693af41`, committed 2026-10-19 03:33 -0700. `git describe` gives
    `v0.22.2+canary.20261019T071120Z-144`. The latest stable tag is `v0.22.2` (2026-10-15).
  - **SASE:** `4b7b981532` (release 0.18.0).
- **Method:** I read both checkouts directly. Hermes was opened with `sase repo open gh:nousresearch/hermes-agent`.
  Two helper agents swept the Hermes CLI surfaces and SASE's provider touchpoints. I re-checked the load-bearing
  claims myself against the source; file:line citations follow. Nothing was executed against a live Hermes install,
  so some behaviour is inferred from code, and those items are labelled.

## Bottom line

1. **Build it as a bundled `HermesProvider` that drives `hermes chat --format stream-json` as a subprocess.**
   - This is the documented machine protocol Hermes ships for "CI runners and orchestrators"
     (`hermes_cli/stream_json.py:1-5`).
   - It matches every other SASE adapter, and the
     [Adapters Normalize Harnesses](#how-sase-adds-a-provider) decision.
   - Make it explicit-only (no autodetect), like Grok and Muse.
2. **The one design point that cannot be skipped: give every SASE agent its own Hermes home.** Since Hermes v0.22.0
   (the "unified gateway runtime", merged 2026-10-14 in `eb75627faf`), every `hermes chat` turn executes inside a
   **background gateway daemon**, one per `HERMES_HOME`. It does not run in the CLI process you launch. Naively
   pointing SASE at the user's `~/.hermes` would cause four problems:
   - **Leaked environment.** Every SASE agent's tools would inherit the environment of whichever agent happened to
     start the daemon. That includes `SASE_*` identity and artifact variables.
   - **Lost cancellation.** SASE's SIGTERM-based interrupt and teardown would *detach* from the turn without
     cancelling it.
   - **Broken containment.** The daemon, and every tool process it spawns, would live in the wrong agent's
     `sase-agent-*` cgroup scope. That scope is swept when its runner exits, which kills other agents' turns mid-flight.
   - **Personal-agent leakage.** Runs could attach to the user's personal gateway and pick up their personal memory,
     SOUL persona, skills curator and session history.

   A SASE-owned home per workspace, under `~/.hermes/profiles/`, fixes all four. Each agent then owns its daemon,
   that daemon inherits the agent's environment and cgroup, and SASE stops it when the turn ends. A profile home still
   reuses the user's subscription logins through Hermes's read-only root `auth.json` fallback.
3. **Deliver SASE instructions explicitly.**
   - Send the bundle through `HERMES_EPHEMERAL_SYSTEM_PROMPT`.
   - Pass `--ignore-rules`, which suppresses `AGENTS.md`, `CLAUDE.md`, `.hermes.md`, SOUL, memory and
     subdirectory hints.
   - Keep the payload under a 120 KiB guard.
   - Mechanically disable Hermes's background and wake primitives where configuration allows. Name the rest in a
     Hermes single-turn directive.
4. **Be clear-eyed about value.**
   - Hermes is a *meta*-harness over about 41 model providers.
   - Routing Claude or Codex through it is strictly worse than SASE's native providers:
     - Claude-via-Hermes OAuth bills **only Max extra-usage credits**, never the base allowance.
     - Codex-via-Hermes draws on the same ChatGPT quota as SASE's `codex` provider.
   - Its real value to SASE:
     - Nous Portal
     - OpenRouter and other API-key models
     - local models
     - Hermes's own tool loop as another harness
     - the "complement, not rival" positioning from the earlier research
5. **Expect churn and plan for it.**
   - Hermes landed about 16,700 commits in the 30 days before this pin.
   - It ships near-daily releases.
   - It moved stream-json onto a new transport twice in five weeks.
   - Pin a minimum version, key test fixtures by CLI version, and send Hermes about five small upstream patches
     ([Upstream asks](#upstream-asks-that-would-simplify-the-integration)).

The full recommendation is [at the end](#recommended-solution).

## Contents

- [Prior research reviewed](#prior-research-reviewed)
- [How SASE adds a provider](#how-sase-adds-a-provider)
- [Hermes's headless surfaces](#hermess-headless-surfaces)
- [The gateway daemon changes the integration](#the-gateway-daemon-changes-the-integration)
- [Options considered](#options-considered)
- [Recommended design in detail](#recommended-design-in-detail)
- [What Hermes is actually good for inside SASE](#what-hermes-is-actually-good-for-inside-sase)
- [Upstream asks that would simplify the integration](#upstream-asks-that-would-simplify-the-integration)
- [Rollout plan](#rollout-plan)
- [Risks and open questions](#risks-and-open-questions)
- [Recommended solution](#recommended-solution)
- [Sources](#sources)

## Prior research reviewed

**`research:202610/can_hermes_replace_sase/can_hermes_replace_sase.md`** is the consolidated five-researcher report
from 2026-10-09. Its relevant conclusions:

- Hermes and SASE are **complements, not rivals**. Hermes *is* an agent with its own tool loop; SASE *wraps* vendor
  coding CLIs as supervised single-turn workers.
- It explicitly recommended making **Hermes the eighth SASE provider**. Then Hermes's local, any-model loop runs under
  SASE's workspaces, gates and host-owned finalizers, and "the main competitor in the overlap becomes a supplier."
- It identified `hermes chat --oneshot -q … --format stream-json` as "the shape a SASE provider needs." It also warned
  that "this requires a maintained integration… shell access alone does not make it exist."
- Two billing details carry over directly:
  - the Anthropic OAuth path consumes only Max extra-usage credits (`providers.md:142-148`)
  - Hermes reaches Codex through ChatGPT OAuth

**Correction to that report, caused by timing.** It pinned Hermes at `1e0c7730d7` (2026-10-08). The unified gateway
runtime merged six days later (`eb75627faf`, 2026-10-14, PR #106742, shipped in v0.22.0). Its "clean headless mode" is
therefore no longer a self-contained subprocess. The stream-json *protocol* survives unchanged, but the execution model
behind it changed. That change is the main subject of this report.

**`research:202604/sase_vs_hermes_agent.md`** is the April comparison. It contrasts Hermes's in-process loop with
SASE's subprocess wrappers, and notes the agentskills.io skill format. That point still matters for skill deployment.

## How SASE adds a provider

### The contract

A "bundled" provider is simply a `sase_llm` entry point in sase's own `pyproject.toml` (`pyproject.toml:212-220`).
`build_llm_plugin_manager()` (`_registry_plugins.py:9-62`) registers every entry point in that group the same way. An
external `sase-hermes` package would be technically identical. What separates "fully supported" is the set of
hard-coded lists and docs outside the adapter.

**The adapter surface.**

- **Invocation.** `LLMProvider.invoke(prompt, *, model_tier, suppress_output, model_override, options) -> InvokeResult`
  (`base.py`). Failures raise `subprocess.CalledProcessError`, which the retry patterns match.
- **About 25 `llm_*` pluggy hooks** (`_hookspec.py:20-258`):
  - identity: name, short name
  - model catalog, short aliases, advisories
  - skill template context and deploy subpath
  - status color
  - autodetect priority and CLI name
  - auth evidence
  - install metadata
  - interactive CLI
  - retry config and usage-limit config
  - usage capabilities and usage probe
  - instruction delivery
  - sync ceiling

**Hard-coded lists a new provider joins** (helper inventory, spot-checked):

| Area | Location | Needed? |
| ---- | -------- | ------- |
| Entry point | `pyproject.toml` `[project.entry-points."sase_llm"]` | Required |
| Model catalog and tiers | `src/sase/llm_provider/models.yml` `providers.<name>` | Required if the adapter uses `provider_tier_model` |
| Effort mirror | `model_policy.py:53-61` `_PROVIDER_SUPPORTED_EFFORTS`; `:66` `_CLI_VALIDATED_PROVIDERS` | Required (a test asserts the mirror) |
| Doctor auth wording | `doctor/checks_providers.py:30-75` `_PROVIDER_SETUP_FALLBACKS` | Required for a useful `sase doctor` |
| Binary identity check | `doctor/checks_deep_providers.py` (the Grok precedent) | Recommended: `hermes` is a generic binary name |
| Query enum | `ace/query_profile/profiles/_agents_shared.py:17-25` `AGENT_PROVIDER_VALUES` | Required for `provider:` queries |
| Instruction verifier | `instructions/directives.py`, `fingerprints.py`, `run_index.py`, `readout.py`, `_verify_*.py`, `coverage_*.py`, `main/instructions_handler.py`, `instructions/cache.py` | Required with explicit delivery or a directive |
| Explicit delivery channel | `instruction_delivery.py:34-38` `CHANNEL_<P>_ROOT` | Required for explicit delivery |
| Badges, palette, family colours | `integrations/provider_badges.py`, `provider_palette.py`, `_registry_catalog.py:8-14`, `skills/cli_list.py` | Optional (fallbacks exist) |
| Closed-list tests | `test_model_manifest.py`, `test_interactive_cli_metadata.py`, `test_provider_text_palette.py`, `test_scoreboard_sessions.py`, `test_candidates_providers.py` | Required |
| Docs | `docs/reference/providers/<p>.md`, `index.md`, `agent-clis.md`, `environment-variables.md`, `models.md` (generated), `mkdocs.yml` nav, README/INSTALL lists, `default_config.yml` comments | Required |

**What needs no provider-specific code.**

- The Rust core (`sase-core`) needs **no** provider-specific change. Routing, disables and effort resolution all take
  Python-supplied facts.
- Rust becomes provider-specific only in the usage-probe normalizers (`provider_usage_normalize_{grok,muse,agy}_*`). A
  Hermes usage probe would need a new binding and a `sase-core-revision.txt` pin bump, as Muse's `6086402725` did.
- `sase agent-cli` install, update and version support is driven entirely by `llm_install_metadata` and
  `llm_autodetect_cli_name`. No code in `src/sase/agent_clis/` names a provider.

### The precedent: Grok

| Provider | First landing | Follow-ups | Feature flags at first landing |
| -------- | ------------- | ---------- | ------------------------------ |
| Grok | Epic `sase-l3`: 9 commits in one day (2026-08-13 to 08-14) | About 25 more over two months: alias pools, usage-limit auto-disable, retry patterns, an ACP usage probe with a Rust billing normalizer, `--rules` delivery, explicit instructions, verifier entries | None (opt-in provider) |
| Muse | Epic `sase-ha`: 7 commits in one evening | — | None (opt-in provider) |

Neither landing used a feature flag, because both providers were opt-in (no autodetect priority). Sunset flags
appeared only when existing behaviour changed: `grok_explicit_instructions` and `muse_explicit_instructions`, both live
today.

### Decision records that constrain the design

- **Agents Are Single-Turn** (`decisions:single-turn-agents`). One provider turn. Nothing may rely on a
  process surviving past the turn.
- **Adapters Normalize Harnesses** (`decisions:adapters-normalize-harnesses`). The adapter must
  mechanically disable native background and wake primitives where the CLI allows. It must tell the model the real
  synchronous ceiling, and otherwise detect violations with a bounded guard. "The host never models a harness's
  private wait semantics." Hermes's daemon is exactly such a private semantic, so the adapter must neutralize it, not
  model it.
- **The Rust Core Is Required.** No Python fallback for shared backend behaviour. This applies only if a usage
  normalizer is added.
- **Readable AGENTS.md / instructions per invocation.** Grok and Muse use explicit, adapter-owned delivery, with native
  files suppressed. agy, Qwen and OpenCode stay on native `AGENTS.md` discovery.

## Hermes's headless surfaces

| Surface | What it is | Fit as a SASE worker |
| ------- | ---------- | -------------------- |
| **`hermes chat --format stream-json`** | One JSON object per stdout line: `system/init`, then `text` deltas, `tool_use` and `tool_result`, then exactly one `result` (`hermes_cli/stream_json.py`). Documented in `website/docs/reference/cli-commands.md:126-252`. | **Best fit.** A documented, closed protocol for orchestrators. Runs through the gateway daemon. |
| `hermes -z PROMPT` | Final text only. Auto-approves ("unattended", `gateway/session_finite.py:27-30`). `--usage-file` writes JSON usage. | No live events or tool calls. Fallback only. |
| `hermes chat -q … -Q` | Text output. On SIGTERM it sends `session.interrupt` (`cli_single_query.py`). | No structured events. |
| `hermes acp` | Agent Client Protocol on stdio, `use_unstable_protocol=True` (`acp_adapter/entry.py:208`). Provides thought chunks, `tool_call`/`tool_call_update`, `session/cancel` and permission requests. | Viable, richer, and a standard protocol. It is **also** a daemon viewer (`entry.py:201`, "this process is a viewer") and forwards no client env. It means building an ACP client in SASE. |
| Python library (`from run_agent import AIAgent`) | Documented in `website/docs/guides/python-library.md`. In-process callbacks for text, reasoning and tool start/complete; `run_conversation()` returns usage, cost and `turn_exit_reason`. | The richest data and **no daemon**. But it couples SASE to a constructor the gateway calls with about 40 kwargs plus a resolved runtime route (`gateway/session_execution.py:150-185`), under heavy refactor. The CLI client is now explicitly "never AIAgent" (`gateway_chat.py:1`). |
| OpenAI-compatible API server (`/v1/runs`) | Lives inside `hermes gateway` on port 8642 and needs `API_SERVER_KEY`. | A long-lived service with no per-request cwd found. Poor fit. |
| TUI gateway JSON-RPC | Internal protocol; the docs flag breaking changes. | Not suitable. |
| MCP server (`mcp_serve.py`) | A messaging bridge only. | Cannot run a prompt. |
| `hermes-agent` legacy runner | In-process. `--max-turns` defaults to 10. No provider flag, no streaming. | Not suitable. |

### The stream-json protocol in detail

Source: `hermes_cli/stream_json.py`. Every line also carries `timestamp` in epoch milliseconds.

```jsonc
{"type":"system","subtype":"init","model":"<-m value or \"\">","session_id":""}
{"type":"text","text":"<delta>"}                         // concatenates byte-for-byte; includes interim commentary
{"type":"tool_use","name":"terminal","tool_call_id":"…","input":{…}}          // input capped ~64 KiB
{"type":"tool_result","name":"terminal","tool_call_id":"…","output":"…","duration_ms":123,"is_error":false} // output capped 5000 chars + "..."
{"type":"result","session_id":"…","exit_code":0,"text":"<final_response>",
 "tokens":{"input":…,"output":…,"total":…,"cache_read":…,"cache_write":…},
 "duration_ms":…, "error":"…"?, "replay_gap":true?}
```

**Differences from Claude-style `stream-json`.**

- The events are flat. There are no `assistant`/`user` message envelopes, so SASE's shared Messages reader
  (`stream_and_parse_messages_json_output`) **cannot** be reused as-is. Grok could reuse it; Hermes needs its own small
  parser.
- **No reasoning or thinking events.** The emitter drops them on purpose ("Other progress events (reasoning…) are not
  part of the protocol").
- **No cost, model or provider in `result`.** The committed result dict has `estimated_cost_usd`, `model` and
  `provider`, but the emitter discards them.
- **No structured failure reason.** `failure_reason`, `billing_block` and `failure_resets_at` exist internally
  (`turn_recovery.py:779-784`) but are not emitted. `error` is free text.
- **`session_id` in `init` is always `""`.** The emitter is built before the session exists. The real id arrives in
  `result.session_id` and on stderr as `Session: <id>` and `session_id: <id>`. Compression can **rotate** the id, so
  read it at exit.
- **The caller cannot choose the session id.** It is derived from a random request id. The closest substitute is a
  caller-chosen title: `-c <title> --create-if-missing`.

**Exit codes** (`gateway_chat.py`, `gateway_chat_view.py`; documented in `cli-commands.md`):

| Code | Meaning |
| ---- | ------- |
| 0 | completed |
| 1 | failed, partial, turn budget hit, or init failed |
| 2 | unsupported option |
| 3 | needs a human (pending approval or clarify), or the turn was lost to a daemon crash |
| 130 | interrupted (detached) |

### Flags that matter

All of these are frozen into the session at creation (`_POLICY` in `gateway_chat.py:21-22`).

- `--query-file -` reads the prompt from stdin, so no prompt appears in argv. An empty prompt exits 2.
- `-m/--model`, `--provider`, `--base-url`, `--api-key`.
- `--reasoning none|minimal|low|medium|high|xhigh|max|ultra`.
- `-t/--toolsets`, `--max-turns` (the default is unlimited), `--skills`.
- `--yolo` (or `HERMES_YOLO_MODE=1`). The hardline blocklist and `approvals.deny` globs still apply.
- `--ignore-rules` (or `HERMES_IGNORE_RULES`).
- `--accept-hooks`, `--pass-session-id`, `--ignore-user-config` / `--safe-mode` (both need `--model`).
- `--in <dir>`, `--source <label>`.

**Refused with exit 2:** `-w`, `--image`, `--run-budget`, `-v`, `--no-restore-cwd`.

## The gateway daemon changes the integration

### What happens on `hermes chat --format stream-json`

From `hermes_cli/gateway_chat.py`, `gateway_client.py`, `gateway_runtime_start.py` and `gateway/run_idle_exit.py`:

1. **The CLI is a WebSocket client.** `cmd_chat` routes stream-json to `launch_gateway_chat` (`main.py:1697-1704`). The
   client connects to the gateway for the current `HERMES_HOME`. `_chat_runs_at_gateway` says it plainly: "Every
   `hermes` / `hermes chat` turn (classic view, `-q`, `-z`, TUI) executes in the gateway" (`main.py:2895-2899`).
2. **If no gateway is running, the client spawns one detached.** It runs `python -m hermes_cli.main gateway run --quiet
   --idle-exit` with `start_new_session=True` (`gateway_runtime_start.py:33-80`). The daemon's environment is **the
   launching client's full `os.environ`**, minus a list of `HERMES_*` launch flags (`DAEMON_STRIPPED_ENV`). The daemon
   is about 270 MB (`run_idle_exit.py:4-5`). It exits after `gateway.unmanaged_idle_exit_seconds` of idleness, 600 s by
   default, and stays up while any background process, async delegation, cron job or Kanban task exists.
3. **Per-session environment is an allowlist, not inheritance** (`agent/session_client_env.py`). A shell client
   forwards only:
   - four behaviour variables: `HERMES_EPHEMERAL_SYSTEM_PROMPT`, `HERMES_PREFILL_MESSAGES_FILE`,
     `HERMES_INFERENCE_PROVIDER`, `HERMES_ENABLE_PROJECT_PLUGINS`
   - toolchain variables: `PATH`, `VIRTUAL_ENV`, `GOPATH`, `CARGO_HOME`, `JAVA_HOME`, and the `CONDA_*`, `NODE_*`,
     `NVM_*`, `PYENV_*` prefixes
   - names listed in `terminal.client_env_passthrough`

   It never forwards secret-looking names or `HERMES_*` names. Total size is capped at 256 KiB and 256 names. **Every
   other variable a tool sees comes from the daemon's environment.**
4. **Interrupting the client does not stop the turn.**
   - On `KeyboardInterrupt`, the client prints "Detached; accepted work continues at the gateway." and exits 130
     (`gateway_chat.py:393-397`).
   - Nothing installs a SIGTERM handler on this path, so SIGTERM uses Python's default action: the client dies, no
     `result` is written, and the admitted turn keeps running in the daemon. This is inferred from the code; verify it
     in the spike.
   - Only the classic `-q -Q` text path forwards SIGTERM, SIGINT and SIGHUP as `session.interrupt`.
   - There is no CLI command to interrupt another session's running turn.
5. **The session's cwd is the caller's cwd**, sent as `cwd` on `session.create`. A per-workspace cwd therefore works.

### Why this breaks a naive adapter

| SASE mechanism | Naive behaviour against a shared or personal daemon | Severity |
| -------------- | ---------------------------------------------------- | -------- |
| **Agent identity and env.** Agents rely on `SASE_ARTIFACTS_DIR`, agent and workspace ids and similar variables reaching their tool subprocesses. Skills and `sase` commands run by the agent read them. | `SASE_*` names are not on the allowlist. Tools see the **daemon's** values: the env of whichever SASE agent first started that daemon. Declarations, artifacts and gates would be attributed to the wrong agent. | **Critical** (silent misattribution) |
| **Process containment.** "An agent runner's `sase-agent-*` scope bounds every process the agent starts: leftovers are swept at runner exit" (`detach_scope.py:1-8`). | The daemon lives in the cgroup of the agent that spawned it, and so do all tools it runs for *other* agents. When that first agent's runner exits, the sweep kills the daemon and every other Hermes agent's in-flight turn. Per-agent resource and OOM accounting is also wrong. | **Critical** |
| **Interrupts.** `start_interrupt_monitor` calls `process.terminate()` and then relaunches with a continuation prompt (`_subprocess_plain.py:40-70`). | The old turn keeps running in the daemon while the continuation starts a second turn in the same workspace. Two writers race on one checkout. | **High** |
| **Teardown watchdog.** After the final declaration it terminates a wedged provider and reaps descendants by `ppid` (`_subprocess_reap.py`). | It reaps the client. The daemon may or may not still be a `ppid` descendant at snapshot time. A turn that outlives the declaration keeps running. | Medium |
| **Hermeticity.** | The default `~/.hermes` home loads the user's SOUL persona, user memory, the skills curator and personal plugins and MCP servers. SASE sessions also land in the user's personal history. | High |
| **Version churn.** | `stream_json.py` moved to the gateway transport on 2026-09-16 (`49ee9d6c74`), and the whole runtime model changed on 2026-10-14. That is about 16,700 commits in 30 days. | Ongoing |

### The fix: one SASE-owned Hermes home per workspace

Point `HERMES_HOME` at a SASE-owned profile directory per workspace, for example `~/.hermes/profiles/sase-<hash>`,
derived from the absolute workspace path. Then each SASE agent run behaves like this:

- **The agent's first `hermes` client starts the daemon** for that home. The daemon inherits the agent's full
  environment, including `SASE_*`, plus anything SASE sets for Hermes such as `TERMINAL_MAX_FOREGROUND_TIMEOUT`. It
  also lands in the agent's cgroup scope, so all tool subprocesses are contained, accounted and swept with the agent.
  This is exactly SASE's model.
- **Cancellation becomes "stop this agent's daemon".** That kills the in-flight turn without touching other agents.
- **Auth still works.** For any home under `<root>/profiles/<name>`, Hermes falls back read-only to the root
  `~/.hermes/auth.json` per provider. Token refreshes write back to the store that was read (`hermes_cli/auth.py:490-520`,
  `hermes_constants.py:269-300`). Subscription logins made with plain `hermes model` are reused.
- **The home stays warm.** Workspaces are claimed by one agent at a time. Keying the home by workspace keeps `state.db`
  and the synced bundled skills warm across runs, and bounds the number of homes to the number of workspaces.
- **The personal Hermes is untouched.** Separate config, sessions, memory and daemon.

**Cost.** Each running Hermes agent pays about 270 MB of RAM and the daemon's cold start. That is acceptable for
multi-minute agent turns, but it is worth tracking given the past research on apollo OOM wipeouts.

## Options considered

| # | Option | Correctness against SASE's model | Data fidelity | Build cost | Coupling and churn risk | Verdict |
| - | ------ | -------------------------------- | ------------- | ---------- | ----------------------- | ------- |
| A | **stream-json subprocess + per-workspace home** | ✅ once the home is isolated and the daemon is owned per agent | Text, tools and tokens; no reasoning or cost | Medium (adapter plus home manager) | Medium: a documented, closed, test-pinned protocol | **Recommended** |
| B | ACP client (`hermes acp`) + per-workspace home | ✅ with the same isolation; real `session/cancel` | Adds thought chunks and the `plan` update; usage semantics unverified | High: SASE has no ACP invocation client (only a usage-probe handshake) | Medium-high: `use_unstable_protocol=True`, editor-shaped | Keep as plan B. Worth it only if SASE wants a **generic ACP provider** for several harnesses. |
| C | In-process runner (a SASE script run by Hermes's interpreter, importing `AIAgent`) | ✅ no daemon; env, cgroup and SIGTERM all native | Best: reasoning, cost, `turn_exit_reason` | Medium-high: must replicate runtime-provider resolution, fallback and prefill plumbing (`session_execution.py:150-185`) | **High**: an internal constructor under active refactor; upstream moved *away* from in-process chat | Reject for core. A possible escape hatch if the daemon proves unworkable. |
| D | One shared SASE-managed gateway + `terminal.client_env_passthrough` listing every `SASE_*` name | ⚠️ tool processes escape agent scopes; a daemon crash kills every Hermes agent; cancelling needs a custom `session.interrupt` client | Same as A | Medium | High: exhaustive env-name lists; secret-looking names silently dropped | Reject. Breaks containment. |
| E | API server / TUI JSON-RPC / MCP | ❌ / ⚠️ | — | — | — | Reject |
| F | `-z` text mode | ✅ with isolation | No tool events | Low | Low | Fallback only |

**Packaging: bundled versus an external `sase_llm` plugin.** The registry makes them technically identical. "Fully
supported", though, requires edits to core-only lists: the effort mirror, doctor fallbacks, the query enum, the
instruction verifier and the docs. Grok and Muse set the precedent of bundling. So bundle it, but keep it explicit-only
and out of the shipped size-alias pools until it has soaked.

## Recommended design in detail

### 1. Command construction

```sh
# env (set by the adapter for this invocation only)
HERMES_HOME=~/.hermes/profiles/sase-<ws-hash>
HERMES_EPHEMERAL_SYSTEM_PROMPT=<SASE root instruction bundle>   # ≤ 120 KiB
TERMINAL_MAX_FOREGROUND_TIMEOUT=<sync ceiling, e.g. 3600>       # inherited by this agent's own daemon

hermes chat --query-file - --format stream-json \
  --yolo --ignore-rules --accept-hooks \
  -m <model> [--provider <hermes-provider>] [--reasoning <level>] \
  -t terminal,file,skills,todo,web,code_execution,delegation,vision \
  [extra args from SASE_LLM_*_ARGS / SASE_HERMES_*_ARGS] \
  < prompt
```

Decisions inside that command:

- **`--query-file -`.** The prompt goes over stdin, as with Claude and Grok, so it never appears in argv or a temp file.
- **`--yolo`.** Without it, `approvals.single_query_mode: deny` (the default) silently *blocks* dangerous commands in
  finite sessions. That matches SASE's bypass posture for every other CLI. The hardline blocklist still applies.
- **`--ignore-rules`.** Sets `skip_context_files`, `skip_memory` and `load_soul_identity=False`, and suppresses
  subdirectory `AGENTS.md`/`CLAUDE.md` hints and `skills.auto_load` (`gateway/session_execution.py:42-54,181-184`;
  `agent/system_prompt.py:317-325`). It does **not** remove the skills index, which is what we want.
- **The toolset list is explicit.** It leaves out:
  - `cronjob`: a native scheduler, which the single-turn decision rules out
  - `memory` and `session_search`: cross-session personal state
  - `clarify`: SASE owns asking through `/sase_questions`. Finite turns auto-answer clarify anyway
    (`gateway/session_finite.py:17-24`).
  - `browser`, `image_gen`, `tts`, `computer_use` and `kanban_*`
- **No `--source` override.** The default `oneshot` source keeps Hermes's one-shot footprint protections: no
  `skill_manage`, and at most two delegation children (`agent/oneshot_footprint.py:24-40`, `config_defaults.py:1401`).
- **No `--max-turns`.** Hermes's default is unlimited. SASE's own watchdogs bound the run.
- **Optional caller handle.** Adding `-c sase-<uuid> --create-if-missing` gives each session a SASE-chosen *title*,
  useful for later lookups. Hermes cannot take a caller-chosen session *id*. SASE resume is transcript-based
  (`#fork` / `#fork_by_chat`), so native resume is not needed.

### 2. Home manager (`_hermes_home.py`)

This is the one genuinely new piece compared with Grok. It has four responsibilities.

**Bootstrap.**

- Requires one user-run step: `hermes profile create sase --clone`, run from the user's configured default. That copies
  `config.yaml`, `.env` and skills, so model and provider settings carry over.
- `sase doctor` and `sase agent-cli` should check for the profile and print this step.
- SASE never logs in on the user's behalf.

**Derivation.** Per workspace, create or refresh `~/.hermes/profiles/sase-<hash>`. Clone from `sase` with `hermes
profile create … --clone-from sase`, so Hermes's own marker files are correct. Then overlay SASE's hermetic keys on top.
Re-derive when the `sase` profile's config fingerprint changes.

**The hermetic overlay.** All keys below exist in `hermes_cli/config_defaults.py`.

| Key | Value | Reason |
| --- | ----- | ------ |
| `updates.check` | `false` | No passive network update checks |
| `plugins.auto_update_check_hours` | `0` | Same |
| `curator.enabled` | `false` | The skill curator runs from the gateway poll |
| `memory.memory_enabled`, `memory.user_profile_enabled` | `false` | No personal memory |
| `memory.nudge_interval`, `skills.creation_nudge_interval` | `0` | No self-improvement nudges |
| `skills.external_dirs` | `[<SASE skills dir>]` | See [Skills](#7-skills) |
| `skills.project_discovery` | `false` | Avoid the untrusted-skills scan of `<root>/.agents/skills` |
| `approvals.mode` | `off` | Belt and braces with `--yolo` |
| `agent.coding_context` | `off` | SASE's bundle owns project context. Hermes's default adds a coding brief and a git snapshot (`config_defaults.py:199-205`). Evaluate in the spike. |
| `agent.disabled_toolsets` | `[memory, session_search, cronjob, clarify]` | Defence in depth beside `-t` |
| `terminal.timeout` | The sync ceiling | Default 180 s |
| `gateway.unmanaged_idle_exit_seconds` | About 30–60 | Backstop if SASE's stop fails |

**Daemon lifecycle.**

- **At start of `invoke()`:** if the home's daemon is alive (`gateway.pid` / runtime state), stop it. On systemd hosts
  the previous agent's scope sweep already killed it. On macOS, and on hosts without systemd scopes, a stale daemon
  carrying the *previous* agent's environment would otherwise serve this agent.
- **At end of `invoke()`** (success, error or interrupt): run `hermes gateway stop` for that `HERMES_HOME`, or signal
  the recorded pid. Verify in the spike that `gateway stop` stops an *unmanaged* runtime; the CLI help says "Stop
  gateway service".
- **On a SASE interrupt request:** stop the daemon. That cancels the turn. Then let the existing continuation loop
  relaunch, which starts a fresh daemon. This replaces `process.terminate()` for Hermes.

### 3. Stream parser (`_subprocess_hermes.py`)

This is a small, dedicated JSONL reader. The flat events do not fit the Messages reader.

- **Text.**
  - `text` deltas go to the live reply file and timer.
  - **`result.text` is the authoritative `InvokeResult.content`.** Deltas include interim commentary, and `replay_gap`
    means the deltas stopped early.
- **Tools.**
  - `tool_use` and `tool_result` go to `append_hermes_tool_call_event`.
  - Pair them by `tool_call_id`, falling back to name order when it is absent. Same-name parallel calls rely on the id.
- **Usage.** Map `result.tokens` onto SASE's keys:

  | Hermes `result.tokens` | SASE key |
  | ---------------------- | -------- |
  | `input` | `input_tokens` |
  | `output` | `output_tokens` |
  | `cache_read` | `cache_read_input_tokens` |
  | `cache_write` | `cache_creation_input_tokens` |

  Whether Hermes's `input` already includes cached tokens is **unverified**. Check it against a real Anthropic-routed
  run before trusting cost displays.
- **Session.** Record `result.session_id`, falling back to stderr `Session:`. Never record `init.session_id`.
- **Errors.**
  - A nonzero `exit_code` raises `CalledProcessError`, with `result.error`, `result.text` and stderr folded into the
    output so retry and usage-limit patterns can match.
  - **Exit 3 ("needs a human") should never happen** under `--yolo` with clarify auto-answered. Treat it as a loud
    adapter failure naming the session id; it means the hermetic setup regressed.
- **Thinking pane.** No sink until upstream emits reasoning
  ([Upstream asks](#upstream-asks-that-would-simplify-the-integration)).
- **Fixtures.** Store them as `tests/fixtures/hermes_stream/<cli-version>/*.jsonl`, the Grok convention. Cover:
  - a no-tool turn
  - a tool turn
  - a failure
  - a usage-limit failure
  - a `replay_gap` run
  - an init failure (Hermes emits init plus a failed result)

### 4. Tool-call capture (`_tool_call_hermes.py`)

Map Hermes tool names onto SASE's canonical display names, as Grok does (`_tool_call_grok.py:25-48`). Names come from
`toolsets.py`.

| Hermes tool | Canonical | Input normalization |
| ----------- | --------- | ------------------- |
| `terminal` | `Bash` | `command` (same key) |
| `read_file` | `Read` | `path` → `file_path` |
| `write_file` | `Write` | `path` → `file_path` |
| `patch` | `Edit` | `path`, `old_string`, `new_string`; V4A mode has `mode`/`patch` |
| `search_files` | `Grep` when `target='content'`, `Glob` when `target='files'` | `pattern` |
| `web_search` | `WebSearch` | |
| `web_extract` | `WebFetch` | |
| `delegate_task` | `Task` | |
| `todo_list` | `TodoWrite` | |
| `skill_view` / `skills_list` | `Skill` / raw | |
| `process_manage`, `execute_code`, `vision_analyze` | Keep raw names | |

Two result-side limits:

- `tool_result.output` is a string capped at 5,000 characters, with no structured exit status.
- If the terminal tool's result string is JSON, parse `exit_code` out of it opportunistically. The shape is unverified.

Unmapped names survive under their own names, matching Grok.

### 5. Instruction delivery

- **Explicit delivery from day one.**
  - Add a new channel constant, `CHANNEL_HERMES_ROOT = "hermes.ephemeral_env"`.
  - Return `{"root": {"status": "explicit", "channel": …, "max_bytes": 120 * 1024}, "subagent": {"status": "none"}}`.
- **The text travels in `HERMES_EPHEMERAL_SYSTEM_PROMPT`.** That variable is on Hermes's per-session forwarding
  allowlist, read through `session_env` at turn time (`gateway/run_config_loaders.py:93-101`), and stripped from the
  daemon so it never leaks between sessions (`gateway_runtime_start.py:28`). The hermetic config sets no
  `display.personality`, so nothing displaces it.
- **The 120 KiB guard.** Linux rejects any single environment string over 128 KiB (`MAX_ARG_STRLEN`), the same limit
  Grok's `--rules` argv guard protects against. Hermes also caps the whole forwarded map at 256 KiB. Oversize or empty
  text calls `report_fallback(...)`. The fallback payload is the directive plus the project `AGENTS.md`, sent through
  the same variable.
- **Subagents get nothing.** `delegate_task` children get their own prompt with `skip_context_files=True` and
  `skip_memory=True` (`tools/delegate_tool.py:282-284`), so the subagent slot is `none`, as for Grok.
- **No sunset flag is needed.** There is no legacy Hermes behaviour to preserve. Grok and Muse needed
  `*_explicit_instructions` only because explicit delivery replaced shipped behaviour.
- **Register Hermes in the instruction verifier and scoreboard**: `directives.py`, `fingerprints.py`, `run_index.py`
  plus a session finder, `readout.py`, `_verify_*`, `coverage_*`, and `instructions/cache.py`'s directive-location
  assumption.

### 6. Single-turn conformance

These follow **Adapters Normalize Harnesses** (`decisions:adapters-normalize-harnesses`).

**Disabled mechanically:**

- `cronjob` is removed from the toolsets.
- The foreground ceiling is raised. Hermes **promotes** any foreground command whose timeout exceeds
  `TERMINAL_MAX_FOREGROUND_TIMEOUT` (default 600 s) to a tracked background process. It also runs any command with a
  lone trailing `&` in the background (`tools/terminal_tool.py:75-76, 1177-1192`).
  - Because the daemon is per agent, the variable SASE sets is inherited by *this agent's* daemon. With a shared daemon
    that would be impossible.
  - Export the ceiling as `llm_sync_ceiling_seconds`, as Claude and Muse do.

**Named in a Hermes single-turn directive** (the Grok and Muse pattern):

- never pass `background: true` to `terminal`, and never end a command with `&`
- if a command returns a process id, call `process_manage` with `action: wait` until it reports an exit code
- `delegate_task` is synchronous in finite turns (`delegation.md:556-570`)
- `/goal`, `/loop` and `/heartbeat` do not exist here
- handoff commands such as `sase monitor start`, `sase plan propose` and `sase questions` may take up to a minute;
  wait for them

**A bounded guard:** flag a `tool_use` of `terminal` with `background: true`, or any `process_manage` start late in
the turn. Do this through the existing `_wait_signals` / `_wait_guard` machinery, warning or nudging the way Claude and
Muse do.

### 7. Skills

- **Deploy to a SASE-owned subpath**, for example `llm_skill_deploy_subpath → .hermes/sase-skills`, giving
  `~/.hermes/sase-skills/<name>/SKILL.md`. List that directory in the overlay's `skills.external_dirs`. Do not use the
  default `.hermes` subpath: that would write into the user's **default** profile's skills directory and pollute their
  personal Hermes. One copy then serves every per-workspace home.
- Hermes skills use agentskills.io-compatible frontmatter. SASE's `name`/`description` `SKILL.md` files already fit.
- **Template context:**

  | Key | Value |
  | --- | ----- |
  | `provider_name` | `Hermes` |
  | `provider_tool_name` | `Hermes Agent` |
  | `provider_native_ask_tool` | `clarify` |

- **Watch-out: description truncation.** Hermes truncates skill descriptions to **60 characters** in the prompt index
  (`agent/skill_utils.py:827-839`). SASE's instruction bundle names skills explicitly ("use your `/sase_final`
  skill"), so the model can still call `skill_view`. Discovery from the description alone will be weaker.
- **Slash-expansion is unverified.** Whether `/sase_final` inside a `-q` prompt is expanded on the gateway path is
  unknown. Verify it in the spike.

### 8. Models and effort

- **Opaque model strings.** Treat Hermes model ids like OpenCode's nested ids. `%model:hermes/<route>` passes
  `<route>` straight to `-m`. Hermes itself splits `provider:model` when the left side is a known provider
  (`hermes_cli/models.py:849-876`), so `hermes/openrouter:anthropic/claude-…` or a Nous Portal model work without SASE
  parsing anything. SASE's `provider/model` routing already accepts unknown ids.
- **Tiers.** Hermes has no fixed catalog, and the Nous Portal list is fetched dynamically. Ship a short curated
  `models.yml` block naming the routes you actually use. Consider a sentinel tier value that means "omit `-m` and use
  the `sase` profile's default model".
- **Effort mirror.** Set `_PROVIDER_SUPPORTED_EFFORTS["hermes"] = (none, minimal, low, medium, high, xhigh, max)`, with
  `_EFFORT_CLI_ARGS` mapping to `--reasoning <level>`.
  - Hermes also accepts `ultra`; SASE has no such level.
  - Add `hermes` to `_CLI_VALIDATED_PROVIDERS`. Hermes clamps per model, and "only ever weakens"
    (`agent/reasoning_effort.py:127-158`).
- **Size-alias pools.** Keep Hermes out at first. That matches the Grok and Muse precedent and
  **Size Aliases Descend The Effort Ladder** (`decisions:size-alias-effort-ladder`). Add it once a route has
  soaked.

### 9. Registry metadata and the rest of "fully supported"

**Identity and presentation:**

| Hook | Value |
| ---- | ----- |
| name | `hermes` |
| short name | `hrm` (unused; existing names are `cld`, `cdx`, `agy`, `qwn`, `opc`, `mus`, `grk`, `fky`) |
| status colour | A Nous brand colour |
| badge | New entry in `provider_badges.py` |
| palette | New entry in `provider_palette.py` |

**Autodetect:** publish `llm_autodetect_cli_name = "hermes"` and **no** `llm_autodetect_priority`.

- `hermes` is a generic binary name; Meta's Hermes JavaScript engine also ships a `hermes` executable.
- Add a `checks_deep_providers.py` identity advisory: real output starts with `Hermes Agent v`.
- Honour `SASE_HERMES_PATH`.

**Install metadata:**

| Field | Value |
| ----- | ----- |
| `manager` | `"script"` |
| `install_script_url` | `https://hermes-agent.nousresearch.com/install.sh` (the documented installer) |
| `self_update_argv` | `["update"]` |
| `latest_version_url` | GitHub `releases/latest`, field `tag_name` (top-level; SASE strips the leading `v`) |
| `version_regex` | `Hermes Agent v(?P<version>\d+\.\d+\.\d+)` |

Hermes is not published on PyPI, npm or Homebrew, so the script installer is the only option.

Note that `hermes --version` performs a **synchronous network update check** (`hermes_cli/_startup_fast.py:219-235`).
Run doctor and agent-cli probes with the SASE profile, whose `updates.check: false` disables it, or ask upstream for a
`--no-update-check` flag.

**Auth evidence:**

- credential paths: `~/.hermes/auth.json`, `~/.hermes/.env`
- common API-key variables: `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `NOUS_API_KEY` (confirm the
  exact name)

**Doctor:**

- a `_PROVIDER_SETUP_FALLBACKS["hermes"]` entry: run `hermes setup` / `hermes model`, then
  `hermes profile create sase --clone`
- a minimum-version check: at least v0.22.2, the stream-json-over-gateway contract this design targets
- a `sase` profile presence check

**Interactive CLI:** `menu_key: "h"` (free), `bypass_args: ["--yolo"]`, `model_args: ["-m", "{model}"]`, launched
with the `sase` profile.

**Retry defaults:** keep the patterns Hermes-specific so they cannot collide with Codex's generic `429` wording. Use:

- `"Gateway connection/read failed"`
- the "rate-limited every one of N attempts" family (`agent/turn_failure_copy.py:179-190,370-387`)

**Usage-limit defaults:**

- Patterns: `"its usage limit resets in"`, `"Billing or credits exhausted"`.
- Hermes **does report a reset instant** in its user-facing copy: "Limit resets at HH:MM (in Xh YYm)". So
  `parse_reset_hint` can be useful here, unlike Grok.
- **Remaining question:** one Hermes limit error may really mean "Codex exhausted" or "OpenRouter credits exhausted".
  Auto-disabling `hermes` as a whole is coarse but safe.

**Usage probe:** phase 3. `hermes usage --provider P --json` returns
`{provider, plan, windows[{label, used_percent, resets_at}], …}` for Codex, Anthropic OAuth and OpenRouter
(`hermes_cli/subcommands/usage.py`). It needs a sase-core normalizer binding plus the revision pin bump. Defer it until
the provider has soaked.

**Docs:**

- `docs/reference/providers/hermes.md`, modelled on `grok.md`: Selection, Command Construction, Hermes Home, Model
  Mapping, Reasoning Effort, Event Stream, Tool-Call Capture, Token Usage, Interrupts and Retries, Skills and
  Instructions, Environment Variables, Timer
- an `agent-clis.md` section
- `environment-variables.md`: `SASE_HERMES_PATH`, `SASE_HERMES_{LARGE,SMALL}_ARGS`, and a variable for the home root
- the index, nav, README and INSTALL lists
- Read the `docs_writing` memory note first.

## What Hermes is actually good for inside SASE

Being "fully supported" does not mean every route through Hermes is a good idea.

| Route through Hermes | Verdict | Why |
| -------------------- | ------- | --- |
| Claude via Anthropic OAuth | **Avoid** | Bills **only Max extra-usage credits**; the base allowance is untouched (`providers.md:142-148`). SASE's `claude` provider uses the base allowance. |
| Codex via ChatGPT OAuth | **Redundant** | The same ChatGPT plan quota as SASE's `codex` provider, with SASE blind to the shared pool. |
| xAI via SuperGrok OAuth | Redundant | SASE has `grok` natively. Hermes's docs flag HTTP 403s on some tiers. |
| **Nous Portal** subscription | **Primary value** | Not reachable by any other SASE provider. |
| **OpenRouter** / any API-key model (Kimi, GLM, MiniMax, DeepSeek, …) | Good | Overlaps OpenCode's niche. Hermes brings a different harness, credential pools and fallback chains. |
| **Local models** (llama.cpp, Ollama, vLLM) | Good | Cheap or offline workers for xsmall-style tasks. |
| Hermes's *harness* as such | Interesting | Fuzzy-matching `patch`, syntax checks on write, LSP diagnostics. It is another harness for swarms like this one. |

Strategically, this delivers the earlier research's "complement, not rival" recommendation. A user keeps Hermes as
their personal front door, and SASE runs Hermes-loop workers under its gates, workspaces and host-owned commits.

## Upstream asks that would simplify the integration

Each is small. The stream-json protocol itself was salvaged from a community PR (`1657a1ce2d`), so upstream accepts
this kind of contribution.

1. **Make SIGTERM and SIGHUP cancel on the stream-json path.** Forward them as `session.interrupt` with a grace period,
   as the classic `-q -Q` path already does (`cli_single_query.py:36-50,402-452`), and still emit the `result` record.
2. **Enrich the protocol:**
   - a `reasoning` event
   - `model`, `provider`, `estimated_cost_usd`, `turn_exit_reason`, `failure_reason` and `failure_resets_at` in
     `result`
   - a populated `session_id` in `init`, or a `session` event once bound
3. **A caller-supplied session id** (`--session-id`), or document the `-c <title> --create-if-missing` handle as the
   supported equivalent.
4. **A finite "private worker" mode.** For example `chat -q --format stream-json --isolated`, running the turn in a
   child of the client that inherits its environment and process group. `--safe-mode` already "runs the turn in an
   isolated worker", so the machinery exists. This one change would let SASE drop the per-workspace home manager.
5. **A network-free version probe** (`--no-update-check`, or an environment variable).

## Rollout plan

The epic shape follows the `sase-l3` (Grok) and `sase-ha` (Muse) precedents.

| Phase | Scope | Notes |
| ----- | ----- | ----- |
| **0. Spike** (about half a day) | Capture real fixtures from Hermes ≥ v0.22.2 under a throwaway `HERMES_HOME`. Settle every item in [Unverified](#unverified-items). | Gate the design on the SIGTERM, `gateway stop` and env-inheritance results. |
| **1. Core provider** | `hermes.py`, `_hermes_home.py`, `_subprocess_hermes.py`, `_tool_call_hermes.py`, the `_tool_calls.py` facade, the entry point, the `models.yml` block, the effort mirror, retry and usage-limit defaults, interrupt-via-daemon-stop, and tests (provider core, invocation, metadata, stream, tool-call reader, model policy, manifest and interactive closed lists). | Explicit-only, so it reaches no user who does not ask for it. No flag needed (the Grok and Muse precedent). |
| **2. Full support** | Explicit instruction delivery and the verifier, the Hermes directive and wait guard, skills deployment with `external_dirs`, doctor (setup fallback, identity, minimum version, profile check), `sase agent-cli install/update hermes`, the interactive launcher key `h`, badges, palette, query enum, docs. | Read the `generated_skills`, `docs_writing` and `tui` memory notes first. |
| **3. Polish** | A usage probe via `hermes usage --json` (plus a sase-core normalizer and pin bump), a thinking pane once upstream emits reasoning, size-alias pool membership, and an opt-in live smoke test. | Send upstream asks 1–2 in parallel with phase 1. |

## Risks and open questions

- **Churn is the dominant risk.** About 16,700 commits in 30 days, release candidates and stables almost daily, and two
  transport rewrites of this exact path since August. Mitigations:
  - a minimum and tested-version window in doctor
  - fixtures keyed by version
  - `agent-cli update` behaviour that warns before moving past the tested window
  - an opt-in live smoke recipe
- **Resource cost.** About 270 MB per concurrently running Hermes agent, plus daemon cold start on every invoke because
  SASE stops the daemon at the end.
- **The user's global controls reach SASE homes.** `hermes gateway stop --all` acts on every profile's gateway, which
  would kill in-flight SASE Hermes agents. Whether `hermes pause` ("global emergency stop… no gateway turns start") is
  per-home or global is **unverified**; if global, it would hold SASE turns.
- **Profile clutter.** `hermes profile list` will show `sase-*` homes. This is acceptable, but document it. `sase
  doctor` could prune homes for deleted workspaces.
- **Security posture.** Unchanged from other SASE providers: permission bypass, with no sandbox. Hermes's hardline
  blocklist may occasionally refuse a legitimate command; surface those refusals in the tool-call rows.
- **Billing surprises** (see [What Hermes is actually good for](#what-hermes-is-actually-good-for-inside-sase)). Doctor
  could warn when the `sase` profile's default provider is `anthropic` OAuth.

### Unverified items

Settle these in phase 0.

- That SIGTERM to the stream-json client leaves the turn running, which is inferred from code. Also whether the
  descendant reap catches the daemon.
- That `hermes gateway stop` stops an unmanaged, idle-exit daemon for a given `HERMES_HOME`, and cancels its in-flight
  turn.
- That a per-agent daemon's tool subprocesses see SASE's variables, and that `TERMINAL_MAX_FOREGROUND_TIMEOUT` is
  honoured from the daemon's inherited environment.
- Whether `/skill` slash commands are expanded inside a `-q` prompt on the gateway path.
- Whether the token counts in `result.tokens.input` include cached tokens.
- Whether `--usage-file` also works with `chat -q --format stream-json` (help says "-z only").
- `hermes pause` scope; Hermes's profile-name rules for `sase-<hash>`; the exact Nous API-key variable name.

## Recommended solution

**Add `hermes` as a bundled, explicit-only SASE provider that runs
`hermes chat --query-file - --format stream-json --yolo --ignore-rules --accept-hooks -m … [--reasoning …] -t <coding
toolsets>` as a subprocess, inside a SASE-owned, per-workspace Hermes profile home.**

Concretely:

1. **Isolate.** Each SASE workspace gets `~/.hermes/profiles/sase-<hash>`.
   - It is cloned from a user-created `sase` profile, so the user's model and provider configuration and subscription
     logins are reused through the root `auth.json` fallback.
   - It is overlaid with hermetic settings: no memory, no curator, no update checks, no project discovery, approvals
     off, SASE skills via `skills.external_dirs`, and a short idle exit.
2. **Own the daemon.** Each agent's first `hermes` client starts that home's gateway, which inherits the agent's
   environment and cgroup scope. SASE stops it at the end of every invoke, and stops any stale one at the start.
   Interrupts cancel by stopping the daemon, then reuse SASE's continuation loop.
3. **Normalize the harness.**
   - Explicit instruction delivery through `HERMES_EPHEMERAL_SYSTEM_PROMPT` (120 KiB guard; subagent slot `none`).
   - A Hermes single-turn directive.
   - `cronjob`, `memory`, `session_search` and `clarify` removed.
   - A raised foreground ceiling exported as the sync ceiling.
   - A bounded guard for `background: true`.
4. **Parse and present.** A dedicated flat-JSONL parser: `result.text` is the content, `result.tokens` is usage, and the
   session id comes from `result`. Tool calls are captured with a Hermes→canonical name map. Registry metadata,
   install, doctor, interactive-launcher, presentation and docs entries follow the Grok template.
5. **Scope the value.** Ship curated routes for Nous Portal, OpenRouter and local models. Document that Claude and
   Codex should stay on SASE's native providers, because the Hermes paths bill extra-usage credits or share quota. Keep
   Hermes out of size-alias pools until it has soaked.
6. **De-risk the churn.** Pin a minimum version (v0.22.2) and a tested window, and key fixtures by version. Send
   upstream the SIGTERM-cancels fix, the richer `result` and reasoning events, and an isolated-worker finite mode. If
   that mode lands, the per-workspace home manager can shrink to a config overlay.

**What to keep in reserve:**

- **ACP**, as the path if SASE later wants a generic ACP provider.
- **The in-process `AIAgent` runner**, as an escape hatch if the daemon model proves unworkable.

Neither should be the first build: one costs more, and the other couples SASE to Hermes's most volatile internals.

## Sources

### Hermes Agent

Checkout `8f5693af41` (2026-10-19), opened via `sase repo open gh:nousresearch/hermes-agent`.

- Gateway client and launch:
  - `hermes_cli/stream_json.py` (whole file)
  - `hermes_cli/gateway_chat.py:14-60, 162-243, 340-397`
  - `hermes_cli/main.py:1697-1704, 2895-2899`
  - `website/docs/developer-guide/gateway-classic-cli.md`
- Daemon runtime and environment:
  - `hermes_cli/gateway_runtime_start.py:12-80`
  - `gateway/run_idle_exit.py:1-60`
  - `agent/session_client_env.py` (whole file)
  - `tools/environments/local.py:414-444`
- Finite sessions and agent construction:
  - `gateway/session_finite.py`
  - `gateway/run_config_loaders.py:93-101`
  - `gateway/session_execution.py:150-185`
- ACP and programmatic integration:
  - `acp_adapter/entry.py:170-224`
  - `acp_adapter/gateway_server.py:269-354`
  - `website/docs/developer-guide/programmatic-integration.md`
  - `website/docs/guides/python-library.md`
- Profiles and auth:
  - `hermes_cli/auth.py:486-530`
  - `hermes_constants.py:269-300`
  - `hermes_cli/subcommands/profile.py:10-40`
- Tools, Kanban, delegation and skills:
  - `toolsets.py:60-140`
  - `tools/terminal_tool.py:75-76, 1170-1192`
  - `tools/file_tools.py:1154-1306`
  - `tools/delegate_tool.py:282-284`
  - `hermes_cli/kanban_db_dispatch.py:2802-2900`
  - `hermes_cli/config_defaults.py` (skills 1463-1503; `terminal.timeout` 314)
- Version and docs:
  - `hermes_cli/_startup_fast.py:185-241`
  - `website/docs/integrations/providers.md:135-150`
  - `website/docs/reference/cli-commands.md:126-252, 335`
- Commits:
  - `eb75627faf` (unified gateway runtime merge, 2026-10-14)
  - `49ee9d6c74` (stream-json moved to the gateway transport, 2026-09-16)
  - `1657a1ce2d` (stream-json added, 2026-08-19)
- Tags: `v0.22.0`–`v0.22.2` (2026-10-14/15).

### SASE

Checkout `4b7b981532`.

- Provider code:
  - `src/sase/llm_provider/grok.py` (whole file)
  - `src/sase/llm_provider/_subprocess_plain.py:36-140`
  - `src/sase/llm_provider/_subprocess_reap.py:1-60`
  - `src/sase/llm_provider/_tool_call_grok.py:1-60`
  - `src/sase/llm_provider/model_policy.py:44-66`
  - `src/sase/llm_provider/models.yml`
  - `src/sase/llm_provider/_registry_catalog.py`
- Scopes and packaging:
  - `src/sase/detach_scope.py:1-60`
  - `src/sase/agent/_scope_sweep_reap.py`
  - `pyproject.toml:212-220`
- Docs:
  - `docs/reference/providers/{index,plugins,grok,opencode,models}.md`
  - `docs/contribute/llm-invocation.md:470-495`
- Git history: epics `sase-l3` (Grok) and `sase-ha` (Muse), via the helper inventory.
- Decision records: `decisions:adapters-normalize-harnesses`, `decisions:single-turn-agents`.

### Prior research

- `research:202610/can_hermes_replace_sase/can_hermes_replace_sase.md` (2026-10-09 consolidated report)
- `research:202604/sase_vs_hermes_agent.md`
