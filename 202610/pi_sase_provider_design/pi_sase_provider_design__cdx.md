# Adding pi as a fully supported SASE provider

Independent research by **cdx**, 2026-10-19.

## Decision in brief

Add a built-in **`pi` harness provider** through the existing `sase_llm` entry point, initially using **one `pi --mode json` process per SASE turn**. Pair it with a small, explicitly loaded SASE pi extension for instruction delivery and narrowly defined harness controls. Keep SASE responsible for workspaces, admission, durable handoffs, and finalization; let pi retain its model loop, credentials, tools, MCP, and user customization.

Build the event interpretation and success rules as a tested Rust domain module in `sase_core`, with Python responsible for provider registration, subprocess I/O, and existing artifact writers. Share that event implementation with a later RPC transport if SASE adds live steering. Do not make RPC, a TypeScript SDK host, a pi fork, or Pi Durable prerequisites for initial provider parity.

The largest implementation risks are **false success, duplicated instructions, silent effort changes, extension behavior, and confusing the pi harness with its underlying model providers**. Registering an executable alone is a small fraction of full support.

## Evidence and limits

I independently inspected the current SASE checkout, the upstream pi checkout opened through `sase repo open`, and the linked Rust core. I also read the earlier [SASE for pi users consolidated report](sase_for_pi_users/sase_for_pi_users__final.md) through `sase artifact read`. I did not consult this swarm's other reports or researchers.

| Component | Inspected revision |
|---|---|
| SASE | `4b7b98153227a355e7d183ea25df4d56694e2998` |
| pi | `d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03`, dated 2026-10-19 |
| sase-core | `753fa21aa5b1d042d23112c04d30b0acd4159970` |
| pi coding-agent package at that revision | `@earendil-works/pi-coding-agent`, version `1.3.0`, MIT, Node `>=22.19.0` |

These are source snapshots, not claims that an npm release or installed binary was tested. There is no `pi` executable on this research environment's PATH; its Node is `v22.14.0`, below the inspected package's minimum. I did not install pi, change global configuration, run paid model calls, or benchmark it. The acceptance tests below are proposed work. Upstream links are pinned to the inspected revision wherever practical. [Pi package metadata][P0]

## 1. What the integration should and should not own

SASE's provider is a **coding harness**, not necessarily a model vendor. This is already true of OpenCode. Pi can run Anthropic, OpenAI, Google, local/custom endpoints, extension-defined providers, and virtual models. SASE should select the pi harness and pass a provider-local model identifier; pi should authenticate and execute it. Replacing SASE's provider layer with `pi-ai` would change every existing harness's behavior and duplicate pi's agent runtime. [SASE OpenCode adapter][S1], [Pi providers][P1]

The existing SASE extension point is sufficient: a class implementing `LLMProvider.invoke(prompt, model_tier, suppress_output, model_override, options)` returns `InvokeResult(content, usage)`. Pluggy hooks supply discovery, model catalogs, instruction delivery, skill locations, install/update information, interactive launch, retry policy, and usage capabilities. Built-ins and third-party packages use the same `sase_llm` entry-point group. I recommend a bundled provider because the requested outcome is maintained parity, with one coordinated release for the adapter, fixtures, instructions, and managed extension. An external Python plugin is a reasonable prototype, but packaging it separately does not remove any lifecycle obligations. [Provider interface][S2], [Hook contract][S3], [Registration][S4]

Keep these ownership boundaries:

| Owner | Responsibilities |
|---|---|
| SASE host | Workspace claim, run identity, admission, durable waits/gates, final declaration validation, commit/finalizer execution, retry/recovery policy |
| `sase_core` | New shared event/state semantics, terminal outcome classification, usage accounting rules, model/effort or quota policy changes, durable wire records |
| Python provider adapter | CLI argv/environment, process and pipe management, calls into Rust, existing live-output/artifact adapters, metadata hooks |
| Small pi extension | Pi-native prompt-section changes, exact native-context filtering, resolved runtime observations, limited compatibility guards |
| pi | Agent/model loop, normal compaction and transient retries, credentials, built-in/user tools, resource loading, session persistence |

Existing Python adapters contain considerable parser logic, but copying that pattern wholesale would violate this project's current Rust backend boundary. A frontend other than the Python TUI must classify the same pi stream identically. Keep the new Rust reducer small and pi-specific; this work does not require migrating every old provider or inventing a universal agent protocol. The Rust instruction-manifest channel validator is already generic, and model validity already recognizes a registered provider followed by an opaque remainder after the first slash. [Core model validity][C1], [Core instruction validation][C2]

## 2. Transport choice

| Option | Advantages | Costs / limitations | Recommendation |
|---|---|---|---|
| Text print mode | Simple subprocess; final text | Omits tool/thinking events and structured usage | Insufficient for full provider support |
| JSON mode | One invocation; structured progress; natural existing SASE lifecycle | No later control commands; headless extension UI limitations | **Initial supported transport** |
| RPC, scoped to one SASE turn | Same event vocabulary plus steer, abort, state/model queries | Request correlation, stdin writer, UI subprotocol, startup/completion/shutdown races | Add when there is a concrete control requirement |
| TypeScript SDK sidecar | Exact resource-loader and prompt control; direct model/session APIs | New executable/runtime build boundary and broader upstream API coupling | Fallback if extension/CLI controls cannot meet the contract |
| Persistent RPC daemon or Pi Durable | More persistent agent-runtime capabilities | Adds a second lifetime/durability owner; contradicts SASE's single-turn model | Do not use for this provider |

Pi explicitly documents JSON as one-shot and RPC as long-lived. **RPC itself is compatible with SASE if the adapter terminates the child at the end of each SASE turn**; retaining a child across turns is the conflicting design. Both transports share `JsonAgentSessionEvent`. [CLI integration][P2], [JSON events][P3], [RPC lifecycle][P4]

An illustrative launch, using a model ID confirmed for the user's installation, is:

```text
pi --mode json
   --session-dir <absolute-run-owned-session-directory>
   --session-id <fresh-invocation-id>
   --model <pi-provider/model-id>
   --thinking <mapped-level>
   --extension <absolute-packaged-sase-extension-path>
```

Send the already-preprocessed SASE prompt through stdin and close stdin after writing. This avoids argument-length limits and pi's command-line `@file` interpretation of positional arguments. Drain stdout and stderr concurrently, including while writing a large prompt, so startup diagnostics cannot deadlock the writer. Pi's main entry point reads piped stdin in JSON mode; RPC reserves stdin for commands. Do not send multiple positional prompts for one SASE invocation. [CLI][P5], [Pi main][P6]

Reserve `--mode`, session identity/storage, and the managed extension against conflicting user extra arguments. Preserve supported ordinary pi customization. Prompt templates and input handlers can still transform or consume a prompt inside pi; this needs a documented policy and an explicit empty/handled-run result, not an assumption that stdin bypasses every pi expansion.

## 3. Completion is the critical correctness work

**Do not reuse an exit-code-only success test.** In pi JSON mode an assistant response with `stopReason: error` or `aborted` can still produce process exit code zero. The print-mode source applies final assistant error/length exit classification only to text output. [Print-mode implementation][P7]

Likewise:

- `message_end` finalizes one message, not the whole run.
- `turn_end` can be followed by tool execution and more model work.
- `agent_end` can be followed by retry, overflow recovery, compaction, or queued messages.
- `agent_settled` is the session-level completion boundary for automatic work.
- Even a settlement must be combined with process exit and terminal message inspection for JSON mode. An extension can schedule new work around settlement, and shutdown can still fail. [JSON events][P3], [Session implementation][P8]

Proposed normal outcome state machine:

```text
spawn -> observe session/run -> messages/tools/retries/compaction
      -> final settlement -> drain and reap -> classify -> SASE finalizers
```

Return a successful ordinary provider result only after the supplied run has settled, the process exits acceptably, and the final completed assistant outcome is successful. A tool's `isError` does not alone fail the run: the model may repair the error. An earlier model error followed by a successful pi retry also must not permanently poison the outcome.

Treat terminal `error`, `aborted`, and `length` as failure/cancellation/truncation with retained partial text and diagnostics. Treat unresolved `pending`, `deferred`, or tool-use-only termination as incomplete unless an explicit SASE handoff/accepted-finalization rule accounts for it. Pi's message type now includes `deferred`; it must not silently become success or an invisible background wait. Unexpected EOF, malformed required terminal records, and missing settlement are protocol/incomplete outcomes, even with exit zero. Unknown additive event types may be retained and ignored. [Message types][P9]

Do not make a required final declaration a condition for every generic LLM call: the shared host decides whether this invocation has finalizer obligations. Preserve the existing special handling for a real monitor/questions/plan/pipe handoff and the accepted-declaration teardown watchdog. A watchdog-killed pi process may legitimately lack settlement; only the existing host-owned accepted-declaration evidence can justify that exception. Do not generalize it into “SIGTERM means success.” [Completion watchdog][S5]

Pi's built-in bash runs synchronously and has an optional timeout with no default. It has process-tree cleanup and no built-in “wake me on completion” contract that SASE should adopt. Report the actual ceiling rather than copying Muse's ten-minute value. SASE's durable long-command path remains `sase monitor`. User extensions can add background behavior, so baseline conformance does not imply arbitrary extension conformance. [Bash tool][P10]

### If RPC is added

Subscribe before sending the prompt; correlate request IDs; a successful `prompt` response is acceptance, not completion. Handle `disposition: handled` without waiting forever for a run that never started. After the owned run settles, close stdin for orderly shutdown, with bounded termination and descendant cleanup if needed. For cancellation, clear queued messages before abort if the intention is to stop all pending work: pi documents that abort alone can continue queued messages. Extension dialog requests require a response; ignoring them can hang the child. Route supported interactions through SASE's durable handoffs or cancel unsupported dialogs explicitly. [RPC lifecycle][P4], [RPC commands][P11], [RPC UI][P12]

## 4. Event mapping and observability

Use the existing shared JSONL reader for transport after conformance tests. It already incrementally decodes UTF-8 and splits on LF, which matches pi's framing requirement; do not replace it with `str.splitlines()`. U+2028/U+2029 inside JSON strings are not record boundaries. Keep stderr separate. [SASE stream reader][S6], [JSON events][P3]

| Pi event/data | SASE behavior |
|---|---|
| `session` header | Record native session ID and correlate to the run-owned session file |
| `message_update.assistantMessageEvent.text_delta` | Append to live reply; track message and `contentIndex` |
| `thinking_delta` | Write thinking output separately, where exposed |
| `message_end` | Authoritative completed message; replace reconstructed partial state rather than append duplicate final text |
| `tool_execution_start/update/end` | Correlate by `toolCallId`; preserve name, arguments, output/error, duration; finalize interrupted pending calls |
| Retry and compaction events | Progress/diagnostics; intermediate failure does not equal failed run |
| `agent_settled` | Mark a settlement boundary; retain `aborted` |
| Assistant `provider`, `model`, `responseModel`, thinking fields | Preserve requested identity separately from observed physical identity |

Maintain a raw pi event artifact for diagnosis and future parser changes, alongside normal `live_reply`, tool-call, usage, and chat artifacts. Apply existing retention and privacy behavior; do not log resolved credentials. Keep full structured tool results in the raw record rather than pretending every MCP or extension result is a string. Normalize familiar names such as `bash` for existing displays while preserving the original tool name. [Existing artifact interfaces][S7], [Message types][P9]

### Usage accounting

For the standard SASE counters:

| Pi | SASE |
|---|---|
| `input` | `input_tokens` |
| `output` | `output_tokens` |
| `cacheWrite` | `cache_creation_input_tokens` |
| `cacheRead` | `cache_read_input_tokens` |

Count each completed assistant message once. Do not sum repeated cumulative `message_update.usage`, or count the same message again in `turn_end` and `agent_end.messages`. `reasoning` is already included in output and `cacheWrite1h` is a subset of cacheWrite. Preserve pi's cost object separately; zero/missing pricing is not proof of a free request. [Message types][P9]

A subtle completeness issue: pi can also record usage from compaction, branch summaries, nested model tools, and non-message operations such as cache warming. Assistant-only totals are not necessarily the full session cost. Retain session records and reconcile non-overlapping entries using native entry IDs and an invocation boundary. Do not add the full lifetime session total after already accumulating stream counters. Label any first-stage total honestly as assistant usage until reconciliation is implemented. For virtual models, attribute observed physical usage without erasing the selected logical model. [Session format][P13]

SASE's `InvokeResult` currently contains text and integer token counters, not a general cost/model trace. A richer shared record belongs in Rust with bindings and schema tests; it need not block basic provider parity if raw/native evidence is preserved and limitations are visible. [Provider types][S8]

## 5. Instructions, skills, and extension compatibility

### Explicit instructions, exactly once

The October 11 report suggested native `AGENTS.md` discovery could suffice. That is too weak for the current per-invocation bundle contract. SASE already exposes an explicit instruction-delivery hook, bundle materialization, an invocation marker, exact SASE-owned native paths, and a verification framework. Use those mechanisms for pi from the first supported release. [Instruction delivery][S9]

Pi offers `--append-system-prompt <text|path>`, `--no-context-files`, and mutable structured prompt options. The useful extension hook is **`before_agent_start`**, whose `systemPromptOptions` includes `contextFiles` and named `sections`. `resources_discover` only adds skill, prompt, and theme paths; it is not a native-context suppression hook. [CLI][P5], [Extension types][P14], [System prompt builder][P15]

Recommended delivery:

1. The host supplies the materialized bundle plus exact canonical paths of its own native projections.
2. The managed extension removes only those paths from `contextFiles`, preserving unrelated home/project/nested instructions and user pi system configuration.
3. Add the bundle as a dedicated structured section, for example `sase_instructions`, with the existing bundle/invocation marker. Declare an explicit channel such as `pi.system_prompt_section`.
4. Record observed session identity, extension version, bundle hash, and effective model/effort in a run-local receipt. Extend `sase instructions verify` to replay pi system messages/section patches and compaction checkpoints, checking delivery exactly once.

A simpler `--append-system-prompt <bundle> --no-context-files` prototype is useful diagnostically, but it drops unrelated native context. Do not ship that as invisible behavior. Conversely, appending without filtering loads SASE's bundle and native projection twice. Replacing the entire pi system prompt also risks losing useful tool/skill instructions. [Pi context loader][P16], [Session format][P13], [SASE verification observers][S10]

This extension needs explicit startup verification. Pi collects extension-load failures as diagnostics; merely passing `-e` is not evidence that the extension ran. Exercise missing/broken-extension cases before claiming fail-closed preflight behavior. If an installed pi version cannot guarantee instruction filtering and validation before the first model request, use a declared, visible fallback or refuse the supported mode. A narrowly scoped SDK launcher is the fallback architecture if source-level testing shows CLI/extension startup cannot enforce that contract. Do not silently claim explicit delivery after a missed extension.

### Retain the user's pi

Keep the normal `PI_CODING_AGENT_DIR`, auth, model configuration, skills, extensions, and MCP behavior. A new empty agent directory would hide the user's login and customization. Ship the managed extension inside the SASE distribution and load it by absolute path; do not require an unrelated npm extension installation just to run the provider. Keep pi's native resources separate from SASE's instruction source of truth. [Configuration][P17]

Pi project trust is important in ephemeral clones: saved trust is path-based, and noninteractive modes skip trust-gated project resources when no applicable approval exists. Define a project-specific policy: a SASE-authorized project can explicitly opt into loading its `.pi` resources with `--approve`; an untrusted/external checkout should not gain that authorization automatically. `--approve` is resource trust, not a per-tool permission bypass. A workspace clone is also not a security sandbox. [Pi security and trust][P18]

Pi's default headless support cannot reproduce every extension's TUI. State the supported baseline: normal tools, skills, custom providers/models, and headless-compatible extensions. Test representative MCP/Codemode configurations without overriding tool exposure or disabling all extensions. Native subagent/orchestrator packages need a separate compatibility story: inheriting SASE environment variables does not authorize a helper to submit the root's final declaration.

### Skills and host completion

Declare `.pi/agent` as the provider skill deployment base and provide pi-specific template context. Pi understands standard `SKILL.md` and `.agents/skills`, but explicit commands are `/skill:name`; it has no universal native “ask user” tool to name in a generic template. Generate SASE's skills through the existing template pipeline, preview before landing, and deploy from a clean landed source per the project memory. Do not hand-edit generated global copies. [Pi skills][P19], [SASE hook contract][S3]

Keep `sase_final` and the generic finalizer controller authoritative. A typed pi finalization tool is optional, not a prerequisite. Its schema and checks must delegate to SASE, and `terminate: true` is not an unconditional process stop: pi terminates a completed tool batch only when all completed calls agree. An `agent_before_settle` reminder must be bounded and coordinated with the host's existing recovery budget, or the integration creates two recovery loops. Regex checks for `git commit` are useful guidance but not a security boundary or complete detection of indirect execution. Prefer a small extension initially over reimplementing finalization, policy, and command parsing in TypeScript. [Pi extension contract][P20], [Agent loop][P21], [SASE invocation internals][S11]

## 6. Models, reasoning effort, authentication, and quotas

### Model identity

Use explicit nested syntax:

```text
%model:pi/anthropic/<exact-model-id>
%model:pi/openrouter/<vendor>/<exact-model-id>
%model:pi/<extension-provider>/<virtual-model-id>
```

SASE removes only the leading `pi/`; the rest remains opaque and goes to pi's model resolver. Preserve slashes inside IDs. This is compatible with the existing OpenCode pattern and current registry splitting. Avoid registering bare popular names such as `sonnet` in a way that steals existing provider routing. Use a small curated catalog for defaults/completions and allow explicit custom models beyond it. Dynamic catalog refresh can improve discovery later; it must not run network/auth work during every UI render. [Registry routing][S12], [Model manifest][S13], [Pi CLI model selection][P5]

Pi accepts fuzzy model patterns. For reproducible SASE tasks prefer exact provider-qualified IDs; record the actual resolved model whenever a user deliberately supplies a pattern or virtual model. Do not force every user onto one paid backend. Document how to set both the harness and SASE's scalar/default alias routing: `llm_provider.provider: pi` alone does not necessarily override an existing explicit `default_model: @large` pool. Keep global size-alias pools unchanged until pi targets are deliberately selected and validated. [Default config][S14]

### Effort is not just flag translation

Map SASE `none` to pi `off`; pass `minimal`, `low`, `medium`, `high`, `xhigh`, and `max` as named levels. But pi **clamps requested effort to model capabilities**, whereas SASE promises not to silently downgrade an explicit effort. CLI-level support for `xhigh` therefore does not establish model-level support. [Pi CLI][P5], [Session thinking implementation][P8], [SASE effort contract][S15]

For an explicit request, inspect the resolved model/effective thinking before model work and fail clearly if it cannot honor the request. For inherited defaults, preserve SASE's best-effort policy and record the effective level. Virtual models may own per-request effort; do not claim a static launch-level check proves every routed request's level. Establish and test an explicit policy for that case. The managed extension can supply runtime observations; shared precedence/validation policy belongs in Rust. Test pi's `:<thinking>` suffix against SASE's `@<effort>` precedence rather than silently permitting two contradictory effort settings.

### Authentication and installation

Use package metadata for `@earendil-works/pi-coding-agent`, executable `pi`, `--version`, and `pi update`; expose a proposed `SASE_PI_PATH` executable override consistently across launch, doctor, and install detection. Check Node `>=22.19.0` when using the inspected npm package, while supporting upstream standalone binaries without assuming Node is needed for them. Select a tested minimum pi version instead of claiming support for all older versions. [Package metadata][P0], [Pi CLI][P5]

Do not copy credentials out of another harness or pass secrets in argv. Prefer pi's auth resolution. `pi auth check --provider ... --json` provides a useful model/backend-specific diagnostic; never add `--credentials` or invoke credential-printing commands for a health check. Honor a custom agent directory. A file-exists check is advisory, not proof that the selected backend is authenticated; local/ambient-credential models need different handling. [Pi providers][P1], [Pi CLI auth][P5]

Declare CLI metadata so pi appears in management and doctor, but initially **omit global executable-only autodetection priority**. `pi` is a generic executable name; other SASE providers already avoid automatic default selection for this reason. Explicit selection is unambiguous, and doctor can verify the runtime/version. [SASE OpenCode adapter and metadata pattern][S1], [Invocation internals][S11]

### Quota scope

Token/cost telemetry and subscription usage windows are different capabilities. Pi does not expose one universal remaining-quota number for every backend. Mark unsupported quota probes as unavailable rather than inventing a common percentage.

More importantly, today's automatic provider-disable store is keyed by the **SASE provider name**. Disabling `pi` after an Anthropic quota error would also disable unrelated OpenAI/local routes. Do not ship generic pi-wide “quota exceeded” patterns that cause this behavior. Initially expose the actionable error and use conservative/no automatic pi-wide quota matching. If backend-scoped disable/fallback is required, implement a Rust routing identity that distinguishes the harness, credential/backend scope, and model, with cross-frontend tests. Keep intentional manual “disable pi” as the harness-wide operation. Avoid multiplying adapters into `pi-anthropic`, `pi-openai`, etc. just to work around this domain mismatch. [Provider-disable domain][C3], [Usage-limit configuration][S16]

## 7. Session policy

Persist a native session file in the SASE run's artifact area. This gives diagnostic context, instruction evidence, and later replay without a daemon. Persist the actual path and ID rather than finding “the newest pi session.” Use absolute paths because a SASE successor may run in a different workspace.

Start with a **fresh native session for each ordinary SASE provider invocation**, preserving SASE's existing portable fork/history behavior. Do not automatically reopen the last native session for every retry or successor. That can reuse stale workspace paths, an old instruction bundle, prior failed tool side effects, and duplicate transcript history already injected by SASE. Pi's native session support is a capability, not proof that all SASE continuations should share context. [Sessions/CLI][P5], [Session format][P13]

Native resume/fork can be a follow-up capability when source/target are pi and the host explicitly selects it. It needs immutable parent provenance, one writer per session, new child identity, fresh instructions, workspace-path handling, and suppression of duplicate text-history injection. Forking context is not rolling back repository state. A process crash requires reconciliation of existing changes before retrying tools; reopening JSONL does not grant exactly-once side effects.

## 8. Implementation sequence and release gate

The work is medium-sized provider integration, with most effort in conformance rather than CLI invocation. I would stage it as follows, without requiring a broad provider-framework rewrite.

1. **Protocol and policy core.** Add a pi event reducer and outcome/usage wire records in `sase_core`; fixtures for settlement, retry, compaction, malformed streams, tool-only stops, deferred responses, and duplicate usage. Expose bindings. Move `sase-core-revision.txt` past the landed core change before Python consumes the binding.
2. **Working adapter.** Add built-in entry point, metadata, a small model catalog, subprocess transport using shared stream/teardown helpers, live/tool/usage artifacts, run-owned native sessions, error translation, and conservative retry/quota behavior. Preserve the generic invocation/finalizer flow.
3. **Instruction and customization conformance.** Ship the explicit extension, exact native-context filtering, model/effort observations, delivery manifest/verification support, generated skill context, project trust configuration, and compatibility diagnostics.
4. **Product parity and acceptance.** Verify explicit model selection, aliases/completions, launch and retry paths, doctor/install/update/interactive launch, remote provider inventory where applicable, and existing UI consumption of standard artifacts. Update the default-config provider documentation and user docs. Run the project's required checks for any implementation, with source changes and screenshots tested according to their applicable memory notes.
5. **Optional control extension.** Add per-turn RPC only with a real steering/abort or dialog requirement. Reuse the event reducer; keep native resume/fork, cost dashboards, and an interactive pi-to-SASE bridge separately scoped.

Representative source surfaces are `pyproject.toml`, `src/sase/llm_provider/`, `models.yml`, `default_config.yml`, `src/sase/instructions/directives.py`, instruction observers/coverage, generated skill templates, and the Rust core/binding modules. New names such as `pi.py`, `_subprocess_pi.py`, and a Rust `pi_events` module are proposed, not existing implementation. Any Python helper around Rust should remain an adapter rather than duplicate the state machine.

Acceptance must demonstrate:

- A real authenticated pi task edits the intended clone, submits the normal declaration, and is finalized by SASE.
- Missing declaration follows bounded host recovery; monitor/plan/questions handoffs end normally without an orphaned pi child.
- Zero-exit JSON model errors, output truncation, unresolved deferred work, missing settlement, and unexpected EOF do not become success.
- Retry/compaction followed by success does become success; no early finalization on `agent_end`.
- Text/thinking reconstruction has no doubled final answer; tool errors and interrupted calls are visible; usage totals do not double-count cumulative events or resumed history.
- UTF-8 split across reads, CRLF, Unicode separators, large output, slow readers, stdin backpressure, cancellation, and shutdown cleanup are handled.
- The SASE contract and current invocation marker appear once; unrelated instructions remain; a broken managed extension cannot masquerade as explicit delivery; compaction and native resume verification are correct where supported.
- Exact and nested custom model IDs work; explicit unsupported effort fails before model work; default effort and virtual routing report honest effective values.
- Existing user pi auth/resources work, unapproved project resources are handled predictably, and representative MCP/Codemode configurations retain their tool exposure.
- A backend quota failure does not disable unrelated pi routes; unavailable quota data is labeled honestly.

Use deterministic captured/fabricated stream fixtures and a fake subprocess executable for most tests; reserve a small opt-in real-model matrix for release qualification. Exercise at least two different model backends and a custom/local route so the adapter is not accidentally “Anthropic through pi.” Pin fixtures and managed-extension tests to supported pi versions and test upgrades before widening support.

## 9. How this updates the earlier pi research

The earlier report correctly identifies pi as a harness SASE should host, favors JSON before RPC, preserves user tools/configuration, and warns about `agent_settled` and zero-exit failures. Those conclusions survive inspection of the newer source.

I would refine four recommendations:

- Native `AGENTS.md` discovery alone is not the current SASE instruction contract. Ship explicit bundle delivery and exact suppression/verification.
- Persisting sessions is valuable; automatically reusing the same session for every successor is a separate policy change with stale-context and replay risks.
- A typed finalization tool and settlement guard can help, but should not duplicate host finalization/recovery or rely on `terminate: true` as a universal kill switch.
- Broad pi model access requires explicit handling of effort clamping and backend-specific quota identity. These are more consequential than adding a large static model list.

This research does not justify promising compatibility with every pi package, a cost reduction, higher coding quality, or faster tasks. Those claims require runtime trials and measured evidence.

## Sources

All GitHub source references below were inspected from locally opened checkouts, not fetched as repository files over the web. The earlier report was read through the audited artifact interface as `research:202610/sase_for_pi_users/sase_for_pi_users__final.md`. Project decisions `adapters-normalize-harnesses` and `single-turn-agents`, artifact rules, and generated-skill guidance were read through `sase memory read`.

[P0]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/package.json
[P1]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/docs/providers.md
[P2]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/docs/cli-integration.md
[P3]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/docs/json.md
[P4]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/docs/rpc.md
[P5]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/docs/cli.md
[P6]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/src/main.ts
[P7]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/src/modes/print-mode.ts
[P8]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/src/core/agent-session.ts
[P9]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/docs/message-types.md
[P10]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/src/core/tools/bash.ts
[P11]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/docs/rpc-commands.md
[P12]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/docs/rpc-extension-ui.md
[P13]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/docs/session-format.md
[P14]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/src/core/extensions/types.ts
[P15]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/src/core/system-prompt.ts
[P16]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/src/core/resource-loader.ts
[P17]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/docs/configuration.md
[P18]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/docs/security.md
[P19]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/docs/skills.md
[P20]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/coding-agent/docs/extensions.md
[P21]: https://github.com/earendil-works/pi/blob/d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03/packages/agent/src/agent-loop.ts
[S1]: https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/llm_provider/opencode.py
[S2]: https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/llm_provider/base.py
[S3]: https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/llm_provider/_hookspec.py
[S4]: https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/pyproject.toml
[S5]: https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/llm_provider/_subprocess_plain.py
[S6]: https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/llm_provider/_subprocess_stream.py
[S7]: https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/llm_provider/_tool_calls.py
[S8]: https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/llm_provider/types.py
[S9]: https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/llm_provider/instruction_delivery.py
[S10]: https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/instructions/_verify_observers.py
[S11]: https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/docs/contribute/llm-invocation.md
[S12]: https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/llm_provider/registry.py
[S13]: https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/llm_provider/models.yml
[S14]: https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/default_config.yml
[S15]: https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/llm_provider/_effort_args.py
[S16]: https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/llm_provider/usage_limit_config.py
[C1]: https://github.com/sase-org/sase-core/blob/753fa21aa5b1d042d23112c04d30b0acd4159970/crates/sase_core/src/model_validity/classifier.rs
[C2]: https://github.com/sase-org/sase-core/blob/753fa21aa5b1d042d23112c04d30b0acd4159970/crates/sase_core/src/instruction_manifest/normalize.rs
[C3]: https://github.com/sase-org/sase-core/blob/753fa21aa5b1d042d23112c04d30b0acd4159970/crates/sase_core/src/provider_disable.rs

## Recommended solution

**Ship a bundled `pi` provider using a fresh, persisted JSON-mode process per SASE turn, a Rust-backed event/outcome reducer, and a small version-tested pi extension for explicit instructions and runtime observations.** Preserve the user's pi authentication, models, tools, and compatible resources. Make correct settlement/error handling, exactly-once instruction delivery, honest effort/usage reporting, and host-owned completion release requirements.

Keep RPC as the next transport when SASE needs live control, and native resume/fork as a separately tested policy. This delivers full support for SASE's current provider contract while preserving pi's strengths and avoiding a second agent host inside SASE.
