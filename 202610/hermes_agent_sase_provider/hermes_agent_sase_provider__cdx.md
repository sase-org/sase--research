# Hermes as a fully supported SASE provider: the execution contract matters most

Researcher: **cdx**. Date: **2026-10-19**. Independent report for the `research.4w` swarm.

**Decision:** add Hermes as a first-class, officially maintained SASE provider, preferably packaged as `sase-hermes`. Use a foreground subprocess whose entire agent execution belongs to the SASE turn. The strongest long-term design is a small Hermes-side companion command that runs one `AIAgent` conversation and emits a versioned event stream. A pinned stable Hermes CLI is a useful prototype, but current `main` has a different process model and cannot safely be substituted without further work.

The integration is worthwhile: Hermes supplies an agent loop across many inference backends, including local models; SASE supplies workspace ownership, audited research/memory access, durable handoffs, and host-owned completion. The main implementation risk is **execution ownership**, followed by instruction delivery and model/account identity. JSON parsing is relatively straightforward.

## Evidence and limits

I opened all repositories through `sase repo open`. I read prior research through audited `sase artifact read` calls. I did not consult this swarm's other researchers, their reports, or their findings.

| Source inspected | Exact revision / scope |
|---|---|
| SASE workspace | `4b7b98153227a355e7d183ea25df4d56694e2998`, release 0.18.0 commit, 2026-10-19 |
| Linked `sase-core` | `753fa21aa5b1d042d23112c04d30b0acd4159970`, release v0.42.1 commit, 2026-10-19 |
| Hermes current checkout | `8f5693af418256b89da17ddda18a9242f113dcf6`, 2026-10-19; describe: `v0.22.2+canary.20261019T071120Z-144-g8f5693af41` |
| Hermes stable comparison | `v0.22.2`, peeled commit `d923a5eb487a17c0a68801bba9ef0f56c81040a8`, 2026-10-15 |
| Earlier research | `research:202610/can_hermes_replace_sase/can_hermes_replace_sase__final.md` and `research:202609/sase_vs_hermes_agent/sase_vs_hermes_agent.md` |
| Live documentation | Official CLI reference and CLI interface pages, retrieved 2026-10-19 |

This is source and contract research, plus a small executable test of the stable JSON emitter. I did **not** run an authenticated Hermes model conversation, install Hermes globally, start a gateway, benchmark agent quality, or demonstrate SASE finalization through Hermes. Proposed commands and architecture below are explicitly proposals where they do not exist today.

The earlier [October comparison](can_hermes_replace_sase/can_hermes_replace_sase__final.md) already recommended composing the products and identified `hermes chat --oneshot ... --format stream-json` as a promising provider interface. That remains useful context, but it did not establish lifecycle compatibility. Its older version observations should not determine today's implementation.

## 1. The finding that changes the design: stable and main execute differently

**At stable v0.22.2**, `cmd_chat` reaches `cli.main`; the CLI setup constructs `AIAgent` locally. The structured single-query path attaches a JSON emitter, runs the conversation, reports a result, and exits. This is close to SASE's existing subprocess adapters. The CLI also has signal handling that requests a hard interrupt and gives tool subprocess cleanup time. [Stable entrypoint](https://github.com/NousResearch/hermes-agent/blob/d923a5eb487a17c0a68801bba9ef0f56c81040a8/hermes_cli/main.py), [agent construction](https://github.com/NousResearch/hermes-agent/blob/d923a5eb487a17c0a68801bba9ef0f56c81040a8/hermes_cli/cli_agent_setup_mixin.py), [single-query lifecycle](https://github.com/NousResearch/hermes-agent/blob/d923a5eb487a17c0a68801bba9ef0f56c81040a8/hermes_cli/cli_single_query.py).

**At the inspected main revision**, `cmd_chat` sends `--format stream-json` through `launch_gateway_chat`; top-level `-z` does the same. The normal CLI is also gateway-backed. The client discovers or starts a gateway, creates a session, submits an admission, and watches it. A client exit is not worker termination. `launch_from_args` explicitly reports that accepted work continues after a keyboard interrupt. A finite query requiring input can return exit 3 while leaving accepted work pending. [Main dispatch](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/hermes_cli/main.py#L1697), [gateway client lifecycle](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/hermes_cli/gateway_chat.py), [finite-query behavior](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/hermes_cli/gateway_chat_view.py#L419).

The official live CLI guide confirms this gateway ownership and detach behavior. Therefore the same public command shape is not evidence of the same execution contract across releases. [Official CLI interface](https://hermes-agent.nousresearch.com/docs/user-guide/cli).

This matters to SASE in four concrete ways:

1. **Stop and teardown:** SASE killing a CLI client does not necessarily stop a gateway-owned agent or its tools. A workspace could be finalized or reused while Hermes still writes to it.
2. **Environment:** SASE identity, finalizer nonce, artifact paths, monitor/handoff channels, and scratch ownership must reach the actual tools. Putting them in the client environment is insufficient with an existing shared gateway.
3. **Handoffs:** a SASE plan, questions, monitor, or pipe handoff must end the current worker. A gateway surviving the handoff could continue the old turn or run a native follow-up.
4. **Retry:** transport loss is potentially an unknown outcome, not permission to submit the same task again. A naive retry can run two writers against one workspace.

The environment problem is visible in code, not merely hypothetical. Hermes's `agent/session_client_env.py` sends a small set of behavior variables, PATH/toolchain variables, selected prefixes, and configured non-secret additions. It does not include `SASE_*` by default. Configured additions still reject secret-like names, including names containing `KEY`; SASE uses `SASE_LAUNCH_SCRATCH_KEY` for process ownership. The gateway launch environment also needs auditing: arbitrary inherited variables can become daemon-wide state if not explicitly scrubbed. Never solve this by putting one turn's SASE identity into a shared daemon's environment. [Client environment rules](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/agent/session_client_env.py), [gateway spawn](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/hermes_cli/gateway_runtime_start.py), [SASE process ownership](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/agent/process_tree.py).

**Consequence:** pin and test a concrete execution capability, not just the presence of `hermes`, a familiar version string, or a JSON flag. A stable CLI adapter must refuse an unvalidated gateway execution path before submitting work.

## 2. What Hermes already provides

### A usable event vocabulary

The structured CLI emits initialization, assistant text deltas, tool start/result records, and a terminal result. The inspected emitter includes optional `tool_call_id`, tool arguments, elapsed time, error status, final text, session ID, and input/output/cache token counters. Tool-result text is capped at 5,000 characters plus a truncation suffix. It intentionally excludes reasoning events. Current main also marks replay gaps in the terminal result. [Stable emitter](https://github.com/NousResearch/hermes-agent/blob/d923a5eb487a17c0a68801bba9ef0f56c81040a8/hermes_cli/stream_json.py), [main emitter](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/hermes_cli/stream_json.py).

I executed the **unmodified stable emitter**, loaded from the local Git object, with synthetic callbacks. Nine emitted records verified preservation of Unicode/whitespace deltas, two concurrent same-name tool calls correlated by IDs, 5,003-character truncated output, and terminal text distinct from the text deltas. No model or gateway was invoked. This validates the emitter behavior only; it does not establish that every runtime callback supplies IDs or usage correctly.

The SASE parser should use text deltas for live display and terminal `result.text` for the authoritative answer. Do not append the terminal answer to the already streamed answer. Require both a valid terminal outcome and acceptable process termination; empty output, EOF, a tool success, and nonempty prose are not sufficient proof of success.

The official command reference documents structured output, query-file input, oneshot mode, reasoning/model options, and usage commands. It is useful for discovering public surfaces, but the pinned implementation is decisive for lifecycle details. [Official CLI reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands).

### Agent construction and extension seams

`AIAgent` accepts a model/backend, working directory, session ID, toolset choices, reasoning configuration, callbacks, an ephemeral system prompt, and flags for skipping context files, memory, and background review. `run_conversation` returns structured outcome information. Hermes documents direct Python embedding, while its development guide warns that internal module paths can move. This supports a **small, pinned wrapper**, not a claim that all internals are a stable SDK. [AIAgent constructor](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/run_agent.py#L235), [integration guide](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/website/docs/developer-guide/programmatic-integration.md), [upstream development contract](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/AGENTS.md).

Hermes plugins can register a top-level CLI command and pre-tool policy hooks. The pre-tool hooks can block or modify calls and have a fail-closed timeout policy. These are useful seams for a companion worker and its SASE conformance policy. Upstream prefers third-party integrations in standalone plugin repositories. [Plugin registration and hooks](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/hermes_cli/plugins.py#L629), [hook dispatch](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/hermes_cli/plugins_dispatch.py).

Do not confuse a **SASE provider plugin** with a **Hermes plugin**. The former runs inside SASE and implements `sase_llm`; the latter runs inside Hermes and provides the worker command/policy. They can share a source repository while being installed in separate Python environments.

## 3. Architecture choices

| Option | Benefit | Cost / decisive limitation | Verdict |
|---|---|---|---|
| Shell wrapper around quiet/plain text | Very small prototype | Weak live observability; ambiguous outcome parsing; `-z` on main still uses the gateway | Insufficient for full support |
| Stable v0.22.2 `chat --format stream-json` subprocess | Existing structured output and local execution; lowest initial work | Must pin exact compatible release; native completion loops and tools still need normalization; main changes ownership | Good feasibility prototype and possible bounded initial release |
| Current main CLI plus shared gateway | Upstream's normal architecture | Cancellation, worker ownership, environment forwarding, unknown admissions, and native continuation all become integration obligations | Do not use as the default SASE worker |
| ACP | Standard sessions, tool events, cancellation, editor integration | SASE needs a client implementation; current default `HermesACPAgent()` is a gateway projection, so stdio does not restore process ownership | No special advantage for this task |
| HTTP / TUI gateway RPC | Rich session and run control | Introduces service discovery/authentication, attach/replay, admission recovery, and lifetime ownership; requires its own lifecycle proof | Suitable if SASE deliberately adopts service-backed execution later |
| Import Hermes into SASE's Python process | Direct callbacks, simple-looking call | Dependency conflicts, process-global configuration, and teardown coupling; loses the isolation of other SASE providers | Reject |
| **Dedicated foreground Hermes companion command** | Own process/environment, direct callbacks, explicit instructions and tool policy; stable SASE-facing contract | A maintained bridge against pinned Hermes APIs; must correctly reuse runtime/auth setup | **Preferred durable design** |

The ACP conclusion follows the actual constructor: with no injected session manager it returns `GatewayACPAgent`. The legacy `hermes-agent` executable is also not an escape hatch suitable for full support: its parser calls a demo-style runner, prints human summaries, and returns 0 after that function returns; caught initialization failures are not converted into a trustworthy structured result. [ACP constructor](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/acp_adapter/server.py#L245), [gateway ACP](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/acp_adapter/gateway_server.py), [legacy command](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/agent/legacy_cli.py), [legacy runner](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/run_agent.py#L1475).

A private foreground gateway per invocation is another technically plausible solution. It needs proof that it never discovers or multiplexes onto a user's gateway, starts no unrelated services, propagates the turn environment correctly, and dies with all workers on every termination path. That is a larger integration than a single foreground agent unless upstream already supplies those guarantees. I would not choose it solely to avoid a small companion command.

## 4. Recommended provider and worker boundary

The proposed relationship is:

```text
SASE invocation + workspace + finalizer
    -> sase-hermes provider (SASE environment)
        -> foreground Hermes companion command (Hermes environment)
            -> one AIAgent.run_conversation(...)
                -> model API + approved synchronous tools
        <- versioned events + one terminal result + process exit
    -> existing SASE completion/finalizer path
```

Call the companion `hermes sase-exec` or a standalone `sase-hermes-worker`; those names are **proposals**, not existing commands. A plugin-registered command can use the installed Hermes runtime without adding Hermes's dependency graph to SASE. Keep the surface narrow: a capabilities/version query, one request file or stdin request, and one event stream. It must not start or attach to the normal gateway.

The worker should:

- Read a bounded structured request containing the query, exact workspace cwd, selected backend/model, requested effort, instruction-file path/digest, and session/run identity. Use private files or stdin, not shell-interpolated prompts or secrets in argv.
- Reuse Hermes's runtime provider/authentication resolution. Do not recreate OAuth, token refresh, custom endpoint routing, or credential pools in SASE. The existing local oneshot implementation is useful reference code, not a stable private function to depend on blindly.
- Run exactly one conversation. Disable background review, learning hooks, native scheduler/goal loops, and automatic follow-up conversations for this mode. Return a structured failure for unexpected interactive input.
- Emit a schema/version handshake before work, session identity, text/tool events, selected and effective model/backend, usage with scope, and exactly one terminal result with completion/failure/interruption semantics.
- On cancellation, interrupt the agent, terminate owned tools, close resources, and exit within a bounded deadline. On forced termination, SASE's existing process containment must still cover the worker and its descendants.
- Avoid machine-global configuration mutations. A normal personal Hermes installation should continue behaving normally outside this explicit worker mode.

A bridge should reuse existing Hermes orchestration helpers where practical, but keep a compatibility test around each relied-upon seam. In particular, `hermes_cli/oneshot.py` demonstrates runtime resolution, session setup, and outcome collection; its old local execution functions remain present on main even though the top-level CLI now dispatches elsewhere. Calling these private helpers indefinitely is not a maintenance strategy. [Local oneshot implementation](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/hermes_cli/oneshot.py).

An upstream generic supervised-execution entrypoint would be preferable to maintaining these seams forever. It should promise process ownership, per-run environment/instructions, cancellation, and no automatic continuation. SASE is a concrete consumer for that request. Research does not establish that upstream would accept it; implementation should not depend on an unaccepted upstream proposal.

## 5. SASE conformance requirements

### Instructions, skills, and ordinary repository rules

SASE already renders per-invocation instruction bundles. Register explicit root delivery under a channel such as `hermes.system_prompt_file`; have the companion consume the private file and include its exact content in the agent's system context. Record the bundle digest and Hermes session ID through existing instruction manifests. A channel name is proposed; the current generic channel validator accepts provider-qualified identifiers.

Hermes's `ephemeral_system_prompt` is appended to the effective system text at API time. The CLI also accepts `HERMES_EPHEMERAL_SYSTEM_PROMPT`, but a large bundle in an environment variable faces platform size limits and is less auditable than a private file. Native context-file discovery can truncate content and choose precedence among rule files, so it is not a sufficient delivery guarantee for the required SASE bundle. [Prompt assembly](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/agent/turn_context.py#L1352), [context loading](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/agent/prompt_builder.py#L1491), [SASE delivery](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/llm_provider/instruction_delivery.py).

Suppress duplicate **SASE-owned** native files, while preserving ordinary repository and nested directory rules. `--ignore-rules` is broad: it also skips other context, memory, and preloaded skills. It can serve a controlled prototype, but is not a selective suppression implementation. The companion needs a tested exclusion/loading policy or a small upstream extension. It must never silently drop project-specific instructions as a side effect of injecting SASE's bundle.

Deploy SASE skills using the existing provider-rendered skill pipeline. Hermes's normal destination is its profile's `skills/` directory under `HERMES_HOME`; external skill directories are also supported. The SASE metadata hook can describe a default `.hermes` deployment, but a selected profile or isolated runtime must receive the same rendered skills. Include `/sase_final`, `/sase_monitor`, `/sase_questions`, and `/sase_plan`, with Hermes tool names in their template context. Change source templates and deploy only from a landed revision; do not hand-edit generated copies. [Hermes skill discovery](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/tools/skills_tool.py).

Disable native delegation initially, while SASE's normal multi-agent launch remains available. Supporting Hermes helpers later requires explicit helper instruction delivery, root-only final declaration, bounded synchronous joins, and accurate helper usage. Do not claim helpers inherit the correct SASE role merely because they inherit some parent prompt.

### Background work and tool policy

Both inspected versions expose terminal background work. The default foreground ceiling is 600 seconds, and an oversized requested timeout can **promote the command to background execution**. The stable quiet path can drain notifications and run follow-up conversations. Stateless delivery suppresses notifications in some contexts but still permits a background process; it does not enforce the SASE contract. [Terminal policy](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/tools/terminal_tool.py#L1120), [background handling](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/tools/terminal_tool_background.py), [stable completion loop](https://github.com/NousResearch/hermes-agent/blob/d923a5eb487a17c0a68801bba9ef0f56c81040a8/hermes_cli/quiet_single_query.py#L180).

The worker needs mechanical restrictions, not just a prompt:

- Start with a reviewed tool allowlist for shell, file editing/search, web, skill reading, and optional todo. Hermes's broad `coding` set still includes memory, delegation, and other tools; do not assume its name means SASE-compatible.
- Block background/notify/persistent-release modes, native scheduler and goal tools, and automatic completion continuations. Validate that timeout overflow and implicit yielding cannot reintroduce background execution.
- Route commands beyond the advertised synchronous ceiling through SASE monitors. Declare the **actual enforced** ceiling via `llm_sync_ceiling_seconds`; 600 is an upstream default, not a guarantee until the wrapper enforces it.
- Keep SASE handoff commands usable and wait for their own handoff exit. Tests must distinguish those deliberate host-owned handoffs from forbidden provider-native background jobs.
- Ensure alternate paths such as `execute_code`, MCP tools, plugin hooks, and native helpers cannot bypass the chosen execution policy. An allowlist plus pre-tool hook is a useful implementation seam; source inspection alone does not prove complete coverage.

These are workflow guarantees, not a claim that prompt instructions and tool policies sandbox arbitrary shell access. SASE already runs trusted coding agents with powerful execution permissions.

### Workspace, state, and credentials

Set both process cwd and Hermes's tool cwd to the SASE allocation. Use local execution first. Do not request Hermes worktrees or allow a configured SSH/Docker backend to send tools to a different filesystem without an explicit supported mapping.

Use a dedicated SASE Hermes profile with reproducible per-run configuration. Separate credential lifecycle from agent memory, session history, and skill-writing behavior. Reuse Hermes's credential resolver; validate refresh locking under concurrent runs. Do not symlink an entire personal Hermes home into every worker, blindly copy secrets into artifacts, or assume a shared writable config is safe to edit per invocation.

Propagate and test SASE's finalizer nonce, artifact directory, identity, workspace and scratch-ownership environment at the **tool subprocess**, including the command that runs `sase final context`. Keep that data out of ordinary diagnostic logs. No finalizer redesign is required if the worker preserves the existing environment and process contract. [SASE declaration channel](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/finalizers/declaration.py).

## 6. Models, effort, usage, and retries

**Model identity has three layers:** SASE harness provider `hermes`, Hermes inference backend, and the backend's opaque model ID. Keep all three. SASE already strips only the first recognized provider prefix, so nested model IDs need no new top-level syntax. A proposed adapter grammar is:

```text
%model:hermes/openrouter/anthropic/claude-sonnet-4.6
%model:hermes/openai-codex/gpt-6.1-sol
```

After SASE removes `hermes/`, the adapter separates the Hermes backend from the remaining opaque model string. Custom backend names and aliases need explicit grammar tests. This is a SASE adapter convention, not a claim that the entire string is already a Hermes CLI model name. Prefer explicit backend/model pairs to guessing from model names. [SASE routing](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/llm_provider/registry.py#L570).

Publish a small tested catalog and allow arbitrary qualified IDs. Do not register unqualified names already owned by Claude/Codex/etc. No autodetect priority and no automatic additions to shared size pools initially: installing Hermes should not silently change existing routing or spending. User aliases can opt in immediately.

Hermes accepts the effort vocabulary through `--reasoning`, but downstream transports clamp levels differently. Preserve SASE's contract: explicit unsupported effort must error or receive a clearly defined supported mapping; an unsupported inherited default may be omitted. Record requested and effective effort when translation occurs. Do not advertise identical `ultra` semantics across all Hermes backends. [Hermes effort normalization](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/agent/reasoning_effort.py), [SASE invocation options](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/llm_provider/types.py).

Map input/output/cache-read/cache-write to SASE's corresponding token counters once per terminal result. Distinguish absent counters from a measured zero where the upstream surface permits; the stock emitter defaults missing values to zero. Keep auxiliary calls, helper calls, reasoning tokens, and cost estimates in supplemental metadata until the shared schema supports their scope. Hermes's oneshot accounting has separate auxiliary totals; the stream emitter alone is not a complete billing ledger.

Hermes provides `hermes usage --provider ... --json` for supported account backends. It is a candidate for SASE's optional usage hook, not a universal Hermes quota endpoint. SASE's current hook context is provider/account oriented; multiple backend accounts under one `hermes` identity need an explicit mapping before publishing windows. Initially report unsupported where attribution is ambiguous. [Usage command](https://github.com/NousResearch/hermes-agent/blob/8f5693af418256b89da17ddda18a9242f113dcf6/hermes_cli/subcommands/usage.py), [SASE usage extension](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/docs/reference/providers/plugins.md).

Disable automatic cross-backend/model fallback for an explicitly selected SASE route unless the user opts in and the actual route is recorded. Otherwise a named comparison or budget silently changes. Credential rotation within the selected backend can remain Hermes-owned if its account provenance is adequate.

Retries need bounded ownership: no whole-task retry while the previous worker might still run. Start with conservative captured error classes, no text-only quota guessing, and an explicit decision about retrying after file changes. Avoid multiplying Hermes API retries by SASE whole-invocation retries. A gateway unknown-admission error must never be treated as ordinary transient failure. Likewise, exhausting one Hermes backend should not automatically disable every unrelated backend behind the `hermes` provider; leave broad automatic disabling off until scope is modeled correctly.

## 7. What changes in SASE

SASE has a real plugin contract; external packaging does not make a provider second-class. `LLMHookSpec` already covers invocation, identity, model names/aliases, installation/auth evidence, interactive launching, skill deployment, instruction delivery, retry defaults, usage, and synchronous ceiling. [Hook specification](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/llm_provider/_hookspec.py), [entry-point discovery](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/llm_provider/_registry_plugins.py).

| Area | Expected implementation |
|---|---|
| Provider package | `sase_llm` entry point `hermes`; unique short name such as `hrm`; resolved executable override; opt-in availability |
| Process adapter | argv-only launch, private query/instruction files, simultaneous stdout/stderr draining, interrupt monitor and completion watchdog |
| Stream artifacts | live reply and timestamps, normalized tool records, usage, session/effective-model provenance, bounded malformed-event diagnostics |
| Metadata | CLI/install/version compatibility diagnostics, profile-aware auth evidence, interactive Hermes launcher, provider color and skill context |
| Instruction support | explicit channel and digest; root-only finalization; generic extension for a provider-specific directive if externally packaged |
| Models/config | qualified catalog/aliases, large/small defaults, selected backend/profile settings, default-config/schema updates as appropriate |
| Shared backend | Rust wire and reducers for any new deterministic event/usage/model policy required across frontends; Python remains transport/plugin glue |
| UI/docs | verify model picker, completion, status, tool display, doctor, CLI management, and installation/upgrade guidance |

One non-generic seam deserves attention: `src/sase/instructions/directives.py` hardcodes the built-in providers' directive imports. An external Hermes plugin will register as a provider but receive no provider-specific directive from that map. Add a small generic directive metadata extension, or deliberately bundle the adapter and register its directive there. Do not rely on accidental prompt prepending while claiming the instruction manifest covers it. [Current directive lookup](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/instructions/directives.py).

I prefer external packaging because it isolates the rapid Hermes compatibility cadence and its companion installation. A built-in adapter is also viable if repository policy prefers it; it does not remove any execution-contract work.

Existing Python parsers offer reusable transport/artifact patterns, particularly OpenCode for nested models and Muse for harness normalization. New shared deterministic normalization belongs in `sase-core`, according to this project's boundary. If a new binding is needed, ship the Rust change/binding/tests and move SASE's `sase-core-revision.txt` pin before its caller lands. This research did not find a need to rewrite the host scheduler or finalizer.

## 8. A staged implementation decision

**First, run a bounded conformance spike on v0.22.2.** Use an isolated profile and a deliberately small tool surface. The baseline native command shape is:

```text
hermes chat --oneshot --format stream-json --query-file <private-query-file>
  --model <model> --provider <backend> --yolo --source tool
```

This is only a baseline: it lacks the necessary lifecycle restrictions, instruction policy, state controls, and compatibility guard. Do not label it production-ready. Check a local or low-cost model and one actually desired hosted backend. Verify the real `sase final` and monitor handoff paths, not just a hello-world response.

**Then make the worker contract explicit.** Build the companion foreground command against a pinned Hermes revision, with a schema/capabilities response that the provider validates. Reuse the native stream vocabulary, add only the missing version/outcome/provenance fields, and keep the request format private to this integration until it stabilizes. Upstream a generic equivalent if feasible.

**Finally complete provider parity and qualify upgrades.** Add metadata/skills/docs and model surfaces, then expand tested backends and optional usage/helper support. Pin release hashes or verified builds; an upstream update must rerun the conformance suite. A compatibility refusal should be actionable and occur before any model call or workspace mutation.

No credible elapsed-time estimate follows from static review. The stream adapter is small; the lifecycle/state policy is the substantial work. The first spike should decide whether a thin companion is sufficient or whether an upstream runtime capability is necessary. If process cleanup, tool-policy enforcement, or instruction delivery requires pervasive monkeypatching, stop and pursue the upstream execution seam instead of maintaining a private Hermes fork.

## 9. Acceptance criteria for “fully supported”

| Test family | Evidence required |
|---|---|
| Routing | Qualified backend/model IDs, custom endpoints, aliases, effort defaults/overrides; no collisions with existing providers |
| Protocol | Unicode and partial lines, stderr flood, malformed events, unknown additive events, missing/duplicate result, mismatched process/result codes, truncated tool output |
| Observability | Final answer shown once; parallel tool IDs; correct invocation token scope; requested/effective backend/model; usable live artifacts |
| Instructions | Exact bundle marker/hash reaches model context; no duplicate SASE root file; ordinary nested rules retained; skills discoverable |
| Lifecycle | SIGINT, SIGTERM, forced kill, process-tree cleanup, stdout closure, and host teardown leave no worker writing to the workspace |
| Handoffs | Real final declaration; real monitor/plan/questions handoff; no Hermes continuation after handoff or finalizer acceptance |
| Native tools | Background requests, timeout promotion, process persistence, delegation, hooks, MCP and execute-code paths cannot silently bypass the selected policy |
| Isolation | Two simultaneous SASE turns preserve different cwd, nonce, artifacts, session IDs, and environments; neither contaminates personal Hermes state |
| Failure/retry | Auth failure, invalid model, exhausted iteration budget, rate limiting, partial response, and crash after editing remain failures with preserved evidence |
| Management | Missing binary, wrong runtime/bridge version, unavailable auth, profile selection, interactive launch, install/update compatibility guidance |

These should be behavior tests, using synthetic streams and fake executables for most SASE coverage, plus a small opt-in real integration suite for auth/tool/environment/lifecycle behavior. A fake stream cannot prove gateway isolation or OAuth refresh concurrency. Run the project's required `just check` through its managed tool workflow for implementation changes; `check-full` remains explicit-only. This report changes no SASE implementation files.

Full support should mean the documented contract is tested, with unsupported optional capabilities reported accurately. It does not require every Hermes messaging, scheduling, personal-memory, or Kanban feature to operate inside a SASE worker.

## Recommended solution

**Build an official `sase-hermes` provider plus a small foreground Hermes companion command, with Hermes kept in its own runtime environment and a pinned, tested compatibility contract.** Keep SASE responsible for workspace allocation, turn lifecycle, durable handoffs, and finalization; keep Hermes responsible for its model loop, tools, and inference authentication.

Use stable v0.22.2's native JSON CLI to establish feasibility and capture fixtures cheaply. Do not turn that prototype into an unqualified “latest Hermes” adapter: current main's shared-gateway behavior changes the ownership guarantees, and even the stable CLI needs native-background normalization. Prefer a maintained generic upstream supervised-execution mode when available; until then, a narrow companion is a more controllable dependency than teaching SASE to own Hermes's shared service, admissions, and private continuation semantics.

The go/no-go test is concrete: a Hermes worker must receive the correct SASE instructions and environment, perform useful edits, submit the normal final declaration or a deliberate handoff, and cease all workspace activity when that turn ends. Once those invariants pass, the remaining provider integration is conventional SASE work.
