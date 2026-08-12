---
create_time: 2026-08-12
updated_time: 2026-08-12
status: research
---

# Adding a Grok LLM Provider to SASE

**Research question:** does an official Grok coding-agent CLI exist, and what is the
best way to add Grok support to SASE without duplicating an agent loop or weakening
SASE's provider abstractions?

**Scope:** SASE at commit `bb60a0bd1` and the public Grok Build source mirror at commit
`be713136d`, inspected on 2026-08-12. Current xAI and OpenCode documentation was also
reviewed on that date. The `grok` executable was not installed in this workspace, so
the proposed command line and stream mapping are source- and documentation-validated,
but not yet verified by an authenticated end-to-end run.

## Bottom line

Yes, an official tool now exists. The product is **Grok Build**, its executable is
`grok`, its official npm package is `@xai-official/grok`, and its source is published
under Apache-2.0 in [`xai-org/grok-build`](https://github.com/xai-org/grok-build).
Calling it “grok-cli” is understandable but ambiguous: several older third-party tools
use that name, and Homebrew still has a deprecated, unrelated `grok` regular-expression
utility.

Grok Build is an unusually good fit for SASE's existing provider architecture. It is a
full coding agent, not merely a model API client; it supports headless prompts,
newline-delimited streaming JSON, model and effort selection, local authentication,
native skills, and ACP. SASE should integrate its headless interface first. A direct
xAI API integration would require SASE to build and maintain its own Grok agent loop,
while ACP would introduce a persistent-session protocol that the current one-shot
`LLMProvider.invoke()` contract does not need.

The best target is therefore a built-in, first-party `grok` provider modeled on the
existing Muse/OpenCode subprocess providers, with an event parser and tool-call
normalizer specific to Grok Build.

## What “Grok CLI” means in 2026

xAI's official [Grok Build overview](https://docs.x.ai/build/overview) describes three
supported modes: an interactive TUI, headless use for scripts and bots, and Agent Client
Protocol (ACP) integration. The documented install command is the xAI shell installer,
and xAI's [enterprise deployment guide](https://docs.x.ai/build/enterprise) also names
the official npm alternative:

```bash
npm install -g @xai-official/grok
```

Both install the `grok` executable. The npm registry reported version `1.0.3` as
`latest` on 2026-08-12. The public source mirror's package metadata lagged that release,
so SASE should treat the installed executable's `version`/`--help` output as the
compatibility authority and use captured output from the actual supported release for
fixtures.

The name collision matters. The [Homebrew `grok` formula](https://formulae.brew.sh/formula/grok.html)
is an unrelated regex utility and installs the same executable name. There are also
multiple older community repositories called `grok-cli`. SASE must not select the Grok
provider merely because some command named `grok` appears on `PATH`.

## Fit with SASE's provider design

SASE's `LLMProvider` boundary is intentionally thin: a provider resolves a model,
launches an external coding-agent CLI, translates its output into SASE artifacts and
usage metadata, and returns an `InvokeResult`. Shared retry, finalizer, prompt
preprocessing, interrupt, and skill behavior stays above the provider. The existing
providers are registered through the `sase_llm` entry-point group, while most
capabilities—model aliases, auth evidence, installation metadata, skill location, and
CLI discovery—are already provider hooks.

Grok Build supplies all the primitives that boundary expects:

- `grok -p ...` runs a single headless request.
- `--output-format streaming-json` emits newline-delimited events suitable for live
  reply, tool timeline, usage, and run metadata artifacts. See xAI's
  [headless and scripting guide](https://docs.x.ai/build/cli/headless-scripting).
- `--model` and `--effort` provide the SASE model-override and reasoning-effort hooks.
- `--cwd`, `--always-approve`, `--no-auto-update`, `--no-plan`, and sandbox controls
  make execution deterministic under an external orchestrator. The supported common
  flags are summarized in the official [CLI reference](https://docs.x.ai/build/cli/reference).
- Browser OAuth, device-code login, and `XAI_API_KEY` cover desktop, SSH, and CI use.
- Grok discovers native skills at `~/.grok/skills/` and repo-local `.grok/skills/`, as
  documented in [Skills, Plugins & Marketplaces](https://docs.x.ai/build/features/skills-plugins-marketplaces).

This is the same architectural shape as Muse and OpenCode, not a new class of provider.

## Options considered

| Option | Advantages | Disadvantages | Judgment |
| --- | --- | --- | --- |
| Built-in adapter around official Grok Build | First-party agent harness; native OAuth and API-key auth; structured stream; native skills; consistent SASE identity, doctor, inventory, and artifacts | Requires a Grok-specific parser, tests, and docs | **Best long-term solution** |
| Use Grok through SASE's existing OpenCode provider | Works with no new subprocess provider; OpenCode supports xAI OAuth and API keys; useful for early smoke tests | Reports and behaves as OpenCode, uses a second agent harness and credential store, and does not validate Grok Build integration | Good temporary workaround |
| External SASE provider plugin | Smaller initial blast radius; can validate the contract independently | A mainstream first-party CLI would remain absent from built-in docs, defaults, doctor behavior, and compatibility tests | Reasonable prototype, unnecessary as the final home |
| Direct xAI Responses/API provider | No CLI dependency; direct control over API requests | SASE would have to implement tool execution, permissions, sessions, context management, and the coding-agent loop; conflicts with its thin-provider design | Reject |
| ACP via `grok agent stdio` | Persistent sessions and a standard JSON-RPC protocol; could eventually improve in-session control | More lifecycle and protocol state than `invoke()` currently models; no immediate benefit for one-shot agent runs | Defer |
| Third-party `grok-cli` package | Some packages predate Grok Build | Ambiguous provenance, divergent behavior, and unnecessary supply-chain risk now that an official CLI exists | Reject |

### OpenCode as an immediate workaround

OpenCode's current [provider documentation](https://opencode.ai/docs/providers#xai)
supports xAI through either SuperGrok device-code OAuth or an API key. Once OpenCode is
connected, SASE can already pass an explicit nested model name through its OpenCode
provider, conceptually:

```text
%model:opencode/xai/grok-4.6
```

This is useful for confirming that Grok performs well on SASE workloads before the new
adapter lands. It should not be presented as first-class Grok support: SASE's provider
will still be `opencode`, OpenCode's agent loop and permissions will be in charge, and
SASE's current OpenCode metadata does not advertise xAI models or `XAI_API_KEY` for
automatic routing and doctor checks.

## Proposed provider contract

### Identity and discovery

Use the following initial metadata:

| Hook or setting | Proposed value |
| --- | --- |
| Provider key / entry point | `grok` |
| Display name | `Grok Build` |
| Short name | `grk` |
| Executable | `grok` |
| Path override | `SASE_GROK_PATH` (derived by the registry) |
| Skill deployment subpath | `.grok` |
| Native ask tool | `ask_user_question` |
| Auth files | `$GROK_HOME/auth.json`, `~/.grok/auth.json` |
| Auth environment | `XAI_API_KEY` |
| Package manager metadata | npm / `@xai-official/grok` |
| Self-update fallback | `grok update` |

Register the CLI name for inventory and doctor checks, but initially omit an autodetect
priority. That makes Grok explicit-only through configuration, a provider-qualified
model override, or `SASE_GROK_PATH`. PATH-only autodetection cannot distinguish Grok
Build from the old Homebrew executable. A later generic enhancement could let providers
supply a read-only identity probe and only auto-select Grok Build when `grok version`
matches its expected product signature.

The doctor check should treat either the cached auth file or `XAI_API_KEY` as offline
evidence, without attempting a network login. SASE should never copy or manage Grok
credentials itself.

### Invocation

The candidate command is:

```text
grok
  --no-auto-update
  --cwd <workspace>
  --output-format streaming-json
  --always-approve
  --no-ask-user
  --no-plan
  --sandbox off
  --model <resolved-model>
  [--effort <level>]
  --prompt-file <mode-0600-temporary-file>
```

The public source exposes `--prompt-file` and `--no-ask-user`; because they are not both
prominent in the high-level CLI reference, the first implementation step must verify
them against the exact supported `grok` release and pin captured `--help` and JSONL
fixtures in tests.

The choices are deliberate:

- A mode-`0600` prompt file avoids command-line length limits and keeps the full prompt
  out of process listings. Remove it in a `finally` block on success, failure, or
  interruption, following the Muse provider's pattern.
- `streaming-json` is needed for incremental `live_reply.md`, timestamped event logs,
  normalized tool calls, and authoritative usage.
- `--always-approve` prevents an unattended provider subprocess from waiting for a
  permission dialog. xAI documents that permissions and the sandbox are independent in
  its [permissions guide](https://docs.x.ai/build/features/permissions).
- `--no-ask-user` prevents Grok's native question tool from blocking a headless run.
  SASE already provides `/sase_questions`, which ends the run cleanly and asks through
  SASE's own gate.
- `--no-plan` avoids an interactive native planning workflow when SASE's `/sase_plan`
  owns planning and artifact handoff.
- `--no-auto-update` prevents a provider invocation from mutating its runtime halfway
  through a SASE run.
- `--sandbox off` should be explicit even if it is currently the Grok default. SASE
  skills such as stitch, task, and artifact operations need controlled access to SASE
  state outside the checkout; a workspace-only Grok sandbox can block those operations.

The last point is a real security tradeoff. In SASE's ephemeral workspaces, the agent is
already the authorized process that edits files and executes commands, so an additional
provider sandbox must not silently break supported SASE workflows. The provider docs
should make `always-approve` plus sandbox-off visible. A future opt-in
`SASE_GROK_SANDBOX=workspace` mode could be added for read/review workloads, with a clear
warning that stateful SASE skills may fail. Enterprise policies may also forbid
always-approve; doctor should surface that cleanly rather than attempting to bypass it.

### Streaming event translation

Grok's streaming format contains incremental text and thought chunks, tool-call start
and update events, usage events, errors, and a terminal `end` event with session and
request metadata. The parser should be tolerant because the official event list is
explicitly extensible.

The important translation rules are:

1. Concatenate `text.data` as deltas. Do not insert paragraph separators between every
   chunk; token boundaries may occur inside a word.
2. Convert `tool_call` and `tool_call_update` into SASE's normalized tool timeline,
   keyed by Grok's tool-call ID. Preserve title, kind, tool name, status, input, output,
   content, and locations when present.
3. Use the terminal `end.usage` object as authoritative aggregate usage. Per-response
   `usage` events are useful for live telemetry but must not be summed into the final
   total, especially when subagents and cache buckets are involved.
4. Store `sessionId`, `requestId`, stop reason, turn count, actual model information,
   and cost fields in `run_metadata.json` when emitted.
5. Persist raw JSONL with timestamps for debugging. Ignore unknown event types while
   recording bounded schema diagnostics, following the Muse parser's defensive pattern.
6. Treat a terminal error or non-zero process exit as failure even if earlier text was
   emitted. Preserve accumulated text so SASE's interrupt/relaunch flow can prepend a
   useful “Work So Far” section.

The implementation should add a dedicated Grok parser and `_tool_call_grok.py` adapter
rather than growing provider conditionals in the shared subprocess code.

### Model and effort policy

Model names are the least stable part of the integration. The current docs identify
`grok-4.6` as the model powering Grok Build, while the checked source snapshot still
contained older defaults. Authentication mode can also affect the model catalog. SASE
should not bind the meaning of `large` or `small` permanently to a dated flagship ID.

For the first release:

- Resolve both SASE tiers to Grok Build's stable CLI product alias, `grok-build`.
- Allow explicit provider-qualified catalog IDs such as
  `%model:grok/grok-4.6`.
- Keep the static known-model list intentionally short—`grok-build`, the currently
  supported flagship, and any API-only coding model verified during the authenticated
  smoke test. Document that `grok models` is authoritative.
- Initially advertise the widely supported `low`, `medium`, and `high` effort levels as
  `--effort` mappings. Add `xhigh` or other levels only when captured tests verify them
  against the chosen default and explicit models.

Mapping both tiers to one alias is conservative, but honest. Inventing a “small” mapping
to a model that is absent under OAuth would make ordinary SASE routing unreliable. A
future provider-model-catalog hook could make dynamic Grok model discovery available to
all SASE frontends; it is not required for the initial adapter.

## Implementation outline

The provider should be landed as one coherent built-in feature:

1. Add `GrokProvider` and register `grok` in the `sase_llm` entry-point group.
2. Add `_subprocess_grok.py` for command construction, temporary prompt lifecycle,
   JSONL parsing, artifacts, usage, errors, and interrupt reconstruction.
3. Add `_tool_call_grok.py` and export it through the shared tool-call layer.
4. Add provider metadata for models, skills, auth evidence, npm inventory/update, docs,
   and an explicit-only executable declaration.
5. Extend doctor setup fallbacks, the default-config provider comment, provider docs,
   model-override examples, README matrices, and generated-skill compatibility tests.
6. Install an authenticated supported Grok Build release in a disposable development
   environment and capture real JSONL fixtures before finalizing the parser.

At minimum, tests should cover:

- exact argv and model/effort mapping;
- missing executable and unauthenticated failures;
- prompt-file permissions and cleanup on success, failure, and interrupt;
- text chunks split at arbitrary byte/token boundaries;
- tool-call start/update/completion and malformed/unknown events;
- terminal aggregate usage versus intermediate usage events;
- session/request/cost metadata;
- partial-output preservation and interrupted-run reconstruction;
- registry aliases, explicit routing, doctor evidence, install/update inventory, and
  `.grok/skills` deployment;
- the collision case where an unrelated `grok` executable is on `PATH`.

Because this broadens the provider registry and touches subprocess, doctor, model, and
skill paths, run `just install` followed by `just check-full`, not only provider-unit
tests. Finish with authenticated smoke runs for a no-tool prompt, a file edit, a shell
tool, a SASE skill that writes state outside the checkout, an intentional model error,
and an interrupt/relaunch.

## Risks and open questions

- **CLI stability:** Grok Build is moving quickly, and the source mirror can lag the npm
  release. Capture a supported-release fixture and test tolerant parsing rather than
  coupling to every field.
- **Executable collision:** explicit-only selection is the safe initial policy. Do not
  add Grok to priority-based autodetection without an identity probe.
- **Model churn:** prefer `grok-build` and explicit overrides; avoid a large hard-coded
  alias catalog.
- **Headless permissions:** `always-approve` and sandbox-off are required for parity with
  current SASE coding workflows, but should be documented as powerful local execution.
- **Enterprise policy:** managed Grok requirements can restrict auth and permission
  modes. Provider errors should preserve Grok's actionable message.
- **Privacy:** prompts, repository context selected by the agent, and tool results are
  sent to xAI. The provider documentation should link to current xAI data/privacy terms
  and avoid implying zero-data-retention unless the user's organization is eligible and
  configured for it.
- **ACP timing:** ACP becomes attractive only if SASE adds a persistent provider-session
  abstraction for true in-flight steering or resumption. It should not delay the
  headless provider.

## Sources consulted

- xAI: [Grok Build overview](https://docs.x.ai/build/overview),
  [Headless & Scripting](https://docs.x.ai/build/cli/headless-scripting),
  [CLI Reference](https://docs.x.ai/build/cli/reference),
  [Enterprise Deployments](https://docs.x.ai/build/enterprise),
  [Skills, Plugins & Marketplaces](https://docs.x.ai/build/features/skills-plugins-marketplaces),
  and [Permissions](https://docs.x.ai/build/features/permissions).
- Official source: [`xai-org/grok-build`](https://github.com/xai-org/grok-build),
  inspected locally at `be713136d` in accordance with SASE's repository workflow.
- Package registry: [`@xai-official/grok`](https://www.npmjs.com/package/@xai-official/grok),
  queried on 2026-08-12.
- OpenCode: [xAI provider documentation](https://opencode.ai/docs/providers#xai).
- Homebrew: [deprecated unrelated `grok` formula](https://formulae.brew.sh/formula/grok.html).
- Local SASE implementation and docs at `bb60a0bd1`, especially `llm_provider/base.py`,
  `_hookspec.py`, `_registry.py`, the Muse and OpenCode providers, agent-CLI detection,
  doctor provider checks, generated-skill deployment, and `docs/llms.md`.

## Recommended solution

Implement a **built-in, explicit-only `grok` LLM provider that wraps the official Grok
Build `grok` executable in one-shot headless `streaming-json` mode**. Base its process
and artifact lifecycle on the Muse provider, add a dedicated tolerant Grok event parser
and tool-call normalizer, deploy SASE skills to `~/.grok/skills`, recognize OAuth cache
or `XAI_API_KEY` authentication, and describe installation through the official
`@xai-official/grok` npm package. Resolve both SASE tiers to the stable `grok-build`
alias initially, while preserving explicit model overrides. Do not enable PATH-priority
autodetection until SASE can verify executable identity, and defer ACP until SASE has a
persistent-session provider contract. Use the existing OpenCode provider only as an
immediate evaluation path, not as the permanent Grok integration.
