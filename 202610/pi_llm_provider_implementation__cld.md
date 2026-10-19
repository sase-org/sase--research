# Adding pi as a fully supported SASE LLM provider

_Researcher report (cld), 2026-10-19. One of five independent swarm reports on the same
question. It builds on the consolidated 2026-10-11 report
`202610/sase_for_pi_users/sase_for_pi_users__final.md`, which asked *whether* SASE should
host pi. This report asks *how* to build the provider, and checks each step against the
current pi and SASE source._

## 1. Bottom line

- **Build pi as an in-tree `sase_llm` provider that runs `pi --mode json` once per SASE
  invocation.** JSON mode matches SASE's single-turn contract: it takes the prompt up
  front, streams events, and exits. The provider follows the Grok and Qwen adapter
  pattern: a provider class, a stream normalizer, a tool-call writer, a `models.yml`
  entry, and a fixture-driven test suite. No `sase-core` (Rust) change and no
  `sase-core-revision.txt` bump are needed. Rust has no provider enum.
- **Use explicit instruction delivery from day one, not native `AGENTS.md` discovery.**
  The 2026-10-11 report said "no extra instruction delivery is needed". That is wrong
  for this machine. Pi walks from the workspace up to `/` and loads one context file per
  directory. Here that means both the project `AGENTS.md` and `~/AGENTS.md`, and both
  contain the SASE Final Declaration contract. Native discovery would load the contract
  twice, which is the exact bug class the instruction-bundle epic fixed. Pi has both a
  suppression switch (`-nc`) and a system-prompt file channel
  (`--append-system-prompt <file>`). That satisfies the reopen condition of
  `decisions:readable-agents-md`, so pi belongs with Claude, Codex, Grok, and Muse, not
  with agy, Qwen, and OpenCode.
- **Never trust pi's exit code.** In JSON mode, a failed, aborted, or truncated model
  response exits 0. Missing credentials surface the same way. The adapter must decide the
  turn's outcome from the event stream: `agent_settled`, then the last assistant
  message's `stopReason`, then `errorMessage`. It then synthesizes a nonzero return code
  and readable stderr, so SASE's retry and error paths still work.
- **Never resume with `--session <path>` in another workspace.** Pi reopens a session in
  the *cwd recorded in its header*, not the process cwd. A successor turn in `sase_14`
  would therefore run its tools against `sase_13`. Continuations must use
  `--fork <abs path> --session-id <new>`, which forks into the current cwd. Never pass a
  session *id* either: an id that matches only another project's session triggers an
  interactive y/N prompt (`src/main.ts:401`). Pi reads that prompt from the same stdin
  that carries SASE's prompt.
- **Preserve the user's pi.** Pass `--model` only when SASE has chosen one; a
  `pi-default` tier sentinel lets pi use the user's own default model. Leave the user's
  extensions, MCP servers, Codemode, tool selection, and project-trust decisions alone.
  Re-add the two user files that `-nc` and `--append-system-prompt` would otherwise drop:
  `~/.pi/agent/AGENTS.md` and `APPEND_SYSTEM.md`.
- **Ship mechanical contract enforcement in a second phase** as a single TypeScript pi
  extension, packaged as sase package data and loaded with `-e`. Pi aliases its own
  dependencies for extensions, so no npm step is needed. Pi also offers something no
  other provider does: `PI_SESSION_ID` is injected into every bash command and is
  host-verifiable. That meets the reopen condition of
  `decisions:helpers-return-roots-declare`, and makes a host-side "only the root may
  declare" check possible for the first time.
- **Defer RPC mode** to the steering/follow-up epic, which needs its own decision record.
  Reject an SDK bridge, print mode, and an out-of-tree plugin repo for the "fully
  supported" goal.

## 2. Question, scope, and evidence

**Question.** What is the best way to implement pi
([earendil-works/pi](https://github.com/earendil-works/pi)) as a new, fully supported
SASE LLM provider?

| Source | Snapshot |
|---|---|
| pi checkout (via `sase repo open gh:earendil-works/pi`) | `d2e7d8b7c` (2026-10-19); `@earendil-works/pi-coding-agent` **1.3.0** (2026-10-15), plus an Unreleased section |
| SASE checkout | `4b7b981532` (release 0.18.0) |
| Prior research | `202610/sase_for_pi_users/sase_for_pi_users__final.md`, read with `sase artifact read` |
| SASE decision records | `adapters-normalize-harnesses`, `single-turn-agents`, `instructions-per-invocation`, `readable-agents-md`, `helpers-return-roots-declare`, `rust-core-required` (read with `sase memory read`), plus the `sase_flags` note |
| Helper inventory | A read-only Explore pass over sase and sase-core, listing every provider-keyed touchpoint (§7) |

**Not done.** Pi is not installed on athena, and its floor is Node ≥ 22.19 while
athena's nvm default is v22.14.0. No live pi run was made. Every pi claim below is
checked against pi's source and docs at `d2e7d8b7c`, not against observed runs. §9
Phase 0 is the live spike that closes this gap.

**Pace of change.** Pi made 8 releases in the 15 days after 1.0.0 (1.0.0 on 2026-10-01
through 1.3.0 on 2026-10-15). 1.0.3 and 1.2.0 both have "Breaking Changes" sections, and
1.2.0 removed the experimental server/client/protocol stack. The CLI and JSON contracts
the adapter depends on have stayed stable, but plan for churn.

## 3. What the 2026-10-11 research got right, and what to correct

**Still right.** The provider comes first. Start with JSON mode, treat `agent_settled` as
terminal, and share one event normalizer that RPC can reuse later. Use a `sase-pi`
extension for enforcement. Make trust a per-project decision rather than a blanket
`--approve`. Don't run a long-lived pi daemon across turns, and don't override pi's tool
exposure.

**Corrections and additions from this pass:**

1. **Instruction delivery.** The report said "Pi natively loads `AGENTS.md`/`CLAUDE.md`
   ... so no extra instruction delivery is needed." That causes a double contract load
   here; see §6 D3. Delivery should be explicit, not native.
2. **Session continuity.** The report recommended "`--session <path>` with a SASE-owned
   `--session-dir`" for successor turns. `SessionManager.open(path)` takes its cwd from
   the session header (`packages/coding-agent/src/core/session-manager.ts:1782`;
   `src/main.ts:338` passes no cwd override). The runtime and tools are then built on
   that cwd (`src/main.ts:867`). Use `--fork` instead; see §6 D6.
3. **Skills.** Deploying to `~/.pi/agent/skills` works. However, pi validates skill names
   against `^[a-z0-9-]+$` (`src/core/skills.ts:99`), and every SASE skill uses
   underscores (`sase_final`, `sase_plan`, …). Bad names only produce warnings, and the
   skill still loads (`skills.ts:329`). Expect about 25 warning lines on stderr per
   launch unless the adapter filters them.
4. **Helper identity.** The report proposed a root token passed through `-e`. A cleaner,
   host-side check exists: pi sets `PI_SESSION_ID` for every bash-tool command, and SASE
   chooses the root's `--session-id`. See D11.
5. **Pi changes since then.**
   - `--thinking` now accepts `max`, so all seven SASE effort levels map.
   - Resumed sessions keep their active tools.
   - Print-mode truncation exits 1; JSON mode is unchanged.
   - The experimental server/client/protocol packages and the Chord dependency were
     removed in 1.2.0.

## 4. How a SASE provider is built today

- **Contract.** `src/sase/llm_provider/base.py` `LLMProvider` has one abstract method,
  `invoke()`. Everything else comes from pluggy `@hookimpl` methods declared in
  `_hookspec.py`. These cover identity, catalog, tiers, short aliases, skill template
  context and deploy subpath, color, autodetect, auth evidence, install metadata,
  interactive CLI, retry, usage-limit, usage capabilities/probe, and instruction
  delivery. The entry point lives in `pyproject.toml` `[project.entry-points."sase_llm"]`.
- **Instruction boundary.** `_instruction_boundary.invoke_with_instructions` wraps every
  root invocation. It resolves the provider's delivery plan, renders and stores the
  bundle and manifest, and exposes `current_instruction_delivery()` to the adapter. On
  any failure it falls back to native discovery for that invocation. An explicit adapter
  must do three things:
  - deliver the bundle once;
  - suppress SASE-owned native files (`instruction_delivery.sase_owned_instruction_paths()`:
    the project `AGENTS.md` and `CLAUDE.md`, plus `~/AGENTS.md` and `~/CLAUDE.md` when
    they contain the contract heading);
  - drop its legacy directive.
- **Streaming.** `_subprocess_stream.stream_json_lines` is a non-blocking, byte-level
  pump. It splits records only on `\n` (`_JsonlPipe.feed`), which is exactly the strict
  LF framing pi requires: U+2028/U+2029 inside JSON strings are safe. Per-provider
  parsers feed shared artifact writers:
  - `live_reply.md` through `append_stream_delta` and `append_stream_text`;
  - `usage.json` through `write_usage_artifact`;
  - `run_metadata.json` through `write_run_metadata_artifact`, the provider-neutral place
    for facts like "the model a CLI actually used";
  - `tool_calls.jsonl` through `_tool_call_common._base_stream_tool_call_record`.
- **Process lifecycle.** `start_interrupt_monitor` handles the legacy kill-and-redirect
  path, which currently has no writer. `start_completion_watchdog` reaps a provider that
  lingers more than 120 s after `final_submission.json` appears
  (`_subprocess_plain.py:104`, `_subprocess_reap.py`).
- **Rust.** sase-core carries provider names as plain strings and has no provider enum.
  Provider-specific Rust exists only for subscription usage windows
  (`provider_usage/{grok,muse,agy}.rs`, `indicator.rs`). Pi needs none of it in the
  phases recommended here.
- **Template providers.** Grok (`grok.py`, added 2026-08-13, 908 lines including tests in
  its first commit, then about 15 polish commits) is the newest explicit-delivery
  adapter. Qwen and OpenCode are the closest JSONL-stream parsers. OpenCode is the
  precedent for nested `provider/model` ids (`models.yml:225`).

## 5. Pi's integration surface (verified at `d2e7d8b7c`)

### Modes

| Mode | Lifetime | Fit for SASE |
|---|---|---|
| `--mode json` | Prompts supplied at start; streams JSONL events; exits | **v1.** Single-turn shaped. Extension dialogs resolve immediately with no UI (`confirm` → false; `runner.ts:331`), so nothing can hang. |
| `--mode rpc` | Long-lived; JSONL commands in, responses and events out | **Later**, for steer, follow-up, and abort. Extension dialogs become requests that must be answered. |
| `-p` print | Final text only | Rejected: no tool calls, usage, or thinking. |
| SDK (`createAgentSession`) | In-process Node | Rejected: requires a TypeScript bridge that resolves pi's global install, and couples SASE to a fast-moving API. |

### JSON-mode contract that the adapter depends on

Sources: `docs/json.md`, `docs/cli-integration.md`, `src/modes/print-mode.ts`.

- **First record:** the session header,
  `{"type":"session","version":3,"id",...,"cwd"}`.
- **Run boundaries:** `agent_start`, `turn_start`, `message_*`, `tool_execution_*`,
  `turn_end`, `agent_end`, **`agent_settled`**. `agent_end` is not terminal, because
  retries, compaction recovery, and queued work can follow it.
- **Streaming:** `message_update` records carry deltas: `text_*`, `thinking_*`, and
  `toolcall_*`. Their top-level `usage` is cumulative for that one response. The
  `message_end` record holds the authoritative final message.
- **Assistant message fields:** `provider`, `model`, `responseModel`, `thinkingLevel`,
  and `usage` (`input`, `output`, `cacheRead`, `cacheWrite`, `cost.total` in USD).
  `stopReason` is one of `stop`, `length`, `toolUse`, `error`, `aborted`, or `deferred`,
  and `errorMessage` is optional.
- **Tool events:** `tool_execution_start` (`toolCallId`, `toolName`, `args`) and
  `tool_execution_end` (`result`, `isError`, `durationMs`). Nested Codemode calls carry
  `parentToolCallId`.
- **Retry and compaction events:** `auto_retry_start` and `auto_retry_end`; on final
  failure, `auto_retry_end` carries `success:false` and `finalError`. Compaction emits
  `compaction_start` and `compaction_end`, the latter with `result.usage`.
- **Exit codes:** `runPrintMode` sets `exitCode` only in text mode. In JSON mode, a model
  error, abort, or truncation exits **0**. A thrown error still exits 1. Startup failures
  such as no model or an extension load error exit 1 with stderr.
- **Signals:** SIGTERM kills tracked detached children, disposes the runtime, and exits
  143.
- **Prompt input:** with no message argv, the piped stdin *is* the prompt
  (`src/cli/initial-message.ts`, `src/main.ts:894`). Passing it on stdin avoids Linux's
  128 KiB per-argv limit, which Grok had to guard against.

### Flags SASE needs

| Need | Flag | Note |
|---|---|---|
| Machine output | `--mode json` | |
| Session storage | `--session-dir <dir>` | With an explicit dir, files go directly inside it as `<ts>_<id>.jsonl`, with no cwd grouping |
| Deterministic id | `--session-id <id>` | Creates the session if absent. Combine with `--fork` to name the forked id |
| Continuation | `--fork <abs path>` | Forks into the **current** cwd. Cannot be combined with `--session`, `--continue`, or `--no-session` |
| Display name | `-n/--name` | Shows the SASE agent name in pi's `/resume` picker |
| Model | `--model provider/id`, `--provider` | Fuzzy matching; on ambiguity pi prefers the provider with credentials |
| Effort | `--thinking off\|minimal\|low\|medium\|high\|xhigh\|max` | Clamped to what the model supports |
| Suppress native context | `-nc/--no-context-files` | Also drops `~/.pi/agent/AGENTS.md` |
| Explicit channel | `--append-system-prompt <text\|path>` | Repeatable. **Replaces** discovered `APPEND_SYSTEM.md` (`resource-loader.ts:663`). A path that does not exist is treated as literal text |
| Extensions | `-e <path>`; `-ne` | `-ne` keeps explicit `-e` paths |
| Trust | `-a/--approve`, `-na/--no-approve` | Without either, saved trust (`~/.pi/agent/trust.json`, nearest ancestor wins) or `defaultProjectTrust` applies; in JSON mode `ask` means skip |
| Startup noise | `PI_SKIP_VERSION_CHECK=1` | Avoids a network version check on every launch |
| Auth probe | `pi auth check --model <m> --json` | Prints `ready`, `not_ready`, or `invalid`, and exits 0, 1, or 2 |

### Context files and the system prompt

Context discovery (`resource-loader.ts:184–268`) loads the agent-dir file, then walks
from cwd up to `/`. It loads **one file per directory**, in the order
`AGENTS.override.md` > `AGENTS.md` > `AGENTS.MD` > `CLAUDE.md` > `CLAUDE.MD`. The
committed `AGENTS.md`/`CLAUDE.md` pair therefore loads once per directory. Trust does not
gate context discovery.

The system prompt is built from named sections (`src/core/system-prompt.ts`): `preamble`,
`tools`, `rules`, `docs`, **`addendum`** (from `--append-system-prompt`),
**`project_context`** (context files, each wrapped in
`<project_instructions path="…">`), `skills`, and `cwd`. The first session JSONL system
message persists every section (`docs/session-format.md`). `sase instructions verify` can
therefore observe delivery exactly, not by inference.

### Other relevant behavior

- **Bash tool:** no default timeout (`tools/bash.ts:42`). Output is truncated, and the
  full output is saved to a temp file.
- **Shell environment:** bash-tool commands receive `PI_SESSION_ID`, `PI_SESSION_FILE`,
  `PI_PROVIDER`, `PI_MODEL`, and `PI_REASONING_LEVEL`, resolved per command. The process
  also sets `AI_AGENT=pi` and `PI_CODING_AGENT=true`.
- **Skills:** pi reads `~/.pi/agent/skills/` and `~/.agents/skills/`. It advertises each
  skill's name, description, and path; the model reads `SKILL.md` with `read`.
- **Extensions:** loaded by jiti with aliased `typebox`, `@earendil-works/pi-ai`, and
  `pi-coding-agent` (`extensions/loader.ts:64–124`). A single `.ts` file needs no
  `npm install`. Relevant hooks:
  - `tool_call` can block. A handler failure also blocks, so the hook fails safe.
  - `agent_before_settle` can append entries and set `continue: true` for one more model
    request.
  - `before_agent_start` can mutate `systemPromptOptions`, including `contextFiles` and
    `appendSystemPrompt`.
  - `session_start` and `session_shutdown`.
- **Install:** run `curl -fsSL https://pi.dev/install.sh | sh`, which pins transitive
  dependencies and can install Node, or `npm install -g --ignore-scripts
  @earendil-works/pi-coding-agent`. `pi update` handles self-updates, except for Nix
  installs.

## 6. Design decisions

### D1. Integration mode: JSON now, RPC later

**Options:** JSON per invocation, RPC per invocation, RPC across turns, SDK bridge, print.

**Recommendation: JSON per invocation.** It is the smallest correct slice:

- one process per provider call;
- no stdin protocol;
- no extension-UI request loop to answer;
- the same kill and teardown semantics as every other SASE provider.

RPC gives steer, follow-up, abort, `get_state`, and in-process continuation. Those are
valuable, but they belong to the live-control epic: reviving the Agents-tab message
feature removed in `1a46198f14`, with a decision record about in-turn steering. JSON and
RPC share event shapes (`docs/json.md`), so build the normalizer as a pure function over
event dicts that both transports can reuse. An RPC process kept alive across turns is
ruled out by `decisions:single-turn-agents`.

### D2. Packaging: in-tree Python provider, TypeScript extension as package data

**Options:**

- (a) in-tree provider in `src/sase/llm_provider/`;
- (b) a `sase-pi` Python plugin repo exposing a `sase_llm` entry point
  (`docs/reference/providers/plugins.md`);
- (c) a published npm package for the pi side.

**Recommendation: (a), with the phase-2 pi extension shipped as
`src/sase/llm_provider/pi_extension/sase_contract.ts` package data** and loaded by
absolute path with `-e`.

An out-of-tree provider would lose:

- `models.yml` membership and its uniqueness and descent checks;
- the hardcoded presentation tables: palette, emoji badge, `AGENT_PROVIDER_VALUES`, and
  doctor setup hints;
- the `model_policy._PROVIDER_SUPPORTED_EFFORTS` mirror;
- the directive registry (`instructions/directives.py`);
- verify and coverage observers keyed by provider name;
- in-repo docs and generated model docs.

That is the opposite of "fully supported". Shipping the extension inside the wheel keeps
the Python adapter and the TypeScript guard in version lockstep, with no npm publishing.
A gallery package (a pi → SASE bridge, the earlier report's item 6) is a separate,
optional distribution step later.

### D3. Instruction delivery: explicit, with the user's pi files preserved

**Why native discovery is wrong here.** In a SASE workspace, pi's walk loads
`<workspace>/AGENTS.md` (20.3 KB) and `~/AGENTS.md` (4.3 KB). Both contain the contract
heading (`#### 1.1.4` and `#### 1.1.3 SASE Final Declaration`, respectively). That is a
double contract load, the R-delivery bug that `decisions:instructions-per-invocation`
exists to prevent. The agy precedent (rejected prefix delivery) does not apply, because
agy has no suppression switch and pi does.

**Recommended root slot:**
`{"status": "explicit", "channel": "pi.append_system_prompt"}`. The channel id matches
`CHANNEL_RE` (`instruction_delivery.py:40`). No `max_bytes` is needed, because transport
is a file path, not argv. The subagent slot is `{"status": "none"}`: pi has no native
subagents, and subagent extensions spawn independent pi processes.

**Adapter steps for an explicit invocation:**

1. `path = delivery.materialize("root")` produces the 0600 bundle file. Assert that it
   exists before exec, because pi treats a missing path as literal text.
2. Pass `-nc --append-system-prompt <path>`.
3. Re-add the user's pi files that step 2 would drop. Pass each as an additional
   `--append-system-prompt` unless it is SASE-owned:
   - `<agent-dir>/AGENTS.override.md|AGENTS.md|AGENTS.MD|CLAUDE.md|CLAUDE.MD` (first
     match), where the agent dir is `PI_CODING_AGENT_DIR` or `~/.pi/agent`;
   - `<agent-dir>/APPEND_SYSTEM.md`.

   v1 limitation: a trusted project `.pi/APPEND_SYSTEM.md` is not re-added. Document it,
   or see the alternative below.
4. Call `delivery.record_session(session_id)`.
5. On any materialization problem, call `report_fallback("root", "delivery_failed", …)`
   and run the legacy path: no `-nc`, plus `--append-system-prompt "<pi single-turn
   directive>"`. Pi's native discovery then supplies the readable projection, as for
   every legacy provider.

**Alternative for later (needs a spike).** Filter `systemPromptOptions.contextFiles`
against SASE-owned paths inside the extension's `before_agent_start`, and append the
bundle there. That is pi's equivalent of Claude's `claudeMdExcludes`. It keeps every
non-SASE context file in its native `project_context` position, including project
`APPEND_SYSTEM.md`. `agent-session.ts:_prepareRun` shows the handler result feeding
`_preparePromptAndToolLoadout`, which emits a system patch when the prompt changes.
Before switching, confirm with a live fixture that a fresh session's *first* persisted
system message already reflects the filtered set.

**Flag?** None. This is not a deprecation of existing behavior: there is no Off branch
users depend on, and `sase_flags` reserves sunset flags for that case. The boundary's
per-invocation legacy fallback is the safety net. If the epic lands the provider before
explicit delivery is ready, the interim legacy behavior is complete on its own and needs
no beta flag.

**Directive.** Add `_PI_SINGLE_TURN_DIRECTIVE` to `instructions/directives.py`
(`DIRECTIVE_PROVIDERS`, `PROVIDER_DISPLAY_NAMES`, `_DIRECTIVE_SYMBOLS`) so the bundle
gets a `pkg.provider.pi` section. The directive text should say:

- this session is one turn, and nothing can wake you;
- `bash` runs in the foreground with no default timeout, so do not background commands
  with `&`, `nohup`, or `setsid`;
- hand anything long to `/sase_monitor`;
- skills are files you read: `/sase_final` means read
  `~/.pi/agent/skills/sase_final/SKILL.md`;
- never commit.

### D4. Prompt transport: stdin

Write the prompt to stdin and close it, with no message argv. This avoids the argv limit
that Grok guards with 120 KiB, and that OpenCode currently risks by passing the prompt
as argv.

### D5. Turn-outcome classification: the stream decides, not the exit code

The parser tracks four things: `saw_settled` and `settled.aborted`, the last assistant
`message_end`, the latest `auto_retry_end.finalError`, and any `compaction_end`
`errorMessage`.

| Condition | Adapter result |
|---|---|
| rc ≠ 0 | Failure. Pass stderr through and add the assistant `errorMessage` if one was seen |
| rc = 0, no `agent_settled` | Failure: "pi stream ended before agent_settled". This also catches the y/N-prompt exit and crashes after the header |
| `agent_settled.aborted` | Failure ("aborted") |
| last `stopReason` ∈ {`error`, `aborted`} | Failure: synthesize rc = 1 and add `[pi] <errorMessage>` and `finalError` to stderr, so `llm_default_retry_config` patterns can match |
| last `stopReason` = `length` | Failure ("truncated at output limit"), retryable, matching Grok's `max_tokens_truncation` handling |
| last `stopReason` ∈ {`stop`, `toolUse`} | Success |
| `deferred` | Failure (unsupported in v1) |

**Hardening: a settle watchdog.** If the process is still alive N seconds (for example
15) after `agent_settled`, terminate it and record it like a teardown stall. Print mode
returns without calling `process.exit`, so a user MCP server or extension handle could
otherwise keep Node alive. The existing post-declaration watchdog only covers turns that
did declare.

### D6. Sessions: one fresh session file per provider invocation

- **Storage:** `--session-dir "$SASE_ARTIFACTS_DIR/pi/sessions"`. Durable with the agent
  record, and out of the user's `~/.pi/agent/sessions` picker.
- **Ids:** a fresh UUID per invocation (`--session-id`). Record it, plus the resolved
  file (glob `*_<id>.jsonl`), in `run_metadata.json` as `pi_session_id` and
  `pi_session_file`.
- **Continuations:** `--fork <abs predecessor file> --session-id <new>`. This covers
  retry with `preserve_workspace`, the wait-claim nudge, and (later) native `#resume`
  and `#fork`. The fork lands in the current workspace's cwd, the new header's
  `parentSession` records lineage natively, and the provider-side prompt cache still
  hits because the copied prefix is identical.
- **Forbidden:**
  - `--session <path>` across workspaces: it runs in the header cwd.
  - `--session <id>` and `--continue`/`--resume`: these look up sessions by cwd. An id
    that matches only another project's session prompts y/N on stdin.
- **Inspection:** use `pi --export <file> out.html`, which is safe and read-only.
  Opening a SASE session interactively should also go through `--fork`, never
  `--session`.

### D7. Models, tiers, and effort

- **`models.yml` `providers.pi`.** Use pi's `provider/id` form, as OpenCode does, so ids
  stay unique across providers (the manifest raises "claimed by both" on a collision).
  Explicit `%model:pi/<anything>` already passes through unchanged as a nested
  provider-local path. That covers virtual models and any vendor the user has
  credentials for.
- **Tiers (recommended): a `pi-default` sentinel** for both `large` and `small`. The
  adapter omits `--model` (and `--thinking` unless an effort is requested), so pi uses
  the user's `defaultModel` and `defaultThinkingLevel`. SASE cannot know which of pi's
  30+ vendors the user has credentials for, so a hardcoded `anthropic/...` tier is a
  guess that fails as "no API key" for many users. `%m:pi-default` then reads naturally.
  Add a few curated, verified ids (from `pi --list-models` at implementation time) as
  short aliases.
  - *Alternative:* concrete tiers, which match the other providers' tests and labels.
    The cost: they break for users without that vendor's credentials.
- **Effort.** `_EFFORT_CLI_ARGS = {none: off, minimal, low, medium, high, xhigh, max}`,
  passed as `--thinking <level>` and mirrored in
  `model_policy._PROVIDER_SUPPORTED_EFFORTS`. Pi clamps silently to what the model
  supports. Record the effective `thinkingLevel` from the assistant message in
  `run_metadata.json` instead of claiming the requested level.
- **Model label.** Record the physical model (`provider/model`, plus `responseModel`)
  from each assistant `message_end` in `run_metadata.json`, so the agent row can show
  `PI(pi-default → anthropic/claude-…)` honestly.
- **Size aliases.** Not in v1. Add pi to `@cheap` or `@xlarge` pools only after there is
  measured usage, per `decisions:size-alias-effort-ladder`.

### D8. Usage, cost, retry, and limits

- **Tokens.** Sum each assistant `message_end.usage`, never `message_update`:
  `input` → `input_tokens`, `output` → `output_tokens`, `cacheRead` →
  `cache_read_input_tokens`, `cacheWrite` → `cache_creation_input_tokens`. Add
  `compaction_end.result.usage` and tool-result `usage` (nested model work). Ignore
  `turn_end` and `agent_end` copies, which would double count.
- **Cost.** Accumulate `usage.cost.total` into `run_metadata.json` as `pi_cost_usd`.
  `InvokeResult.usage` is `dict[str, int]`, and `usage.json` holds only integers.
  Promoting cost to a first-class, cross-frontend field (TUI, mobile, rollups) is
  core-backend logic by the `rust_core_backend_boundary` litmus test, and is a later
  sase-core change.
- **Retry.** Pi already auto-retries transient provider errors (`auto_retry_*`). The
  SASE layer should be conservative:
  - match patterns on the synthesized stderr: `overloaded`, `rate limit`, `429`, `529`,
    `fetch failed`, `ECONNRESET`, and `truncated at output limit`;
  - use longer waits;
  - set `preserve_workspace=True`;
  - continue via `--fork` of the failed session rather than a text nudge.
- **Usage-limit auto-disable: off in v1.** Omit `llm_default_usage_limit_config`.
  sase-core's provider-disable wire is provider-wide (`provider_disable.py`, wire v2),
  and pi multiplexes many vendors. One Anthropic subscription limit would disable every
  pi route, including OpenRouter and local models. Revisit after a model-scoped disable
  exists in sase-core.
- **Usage probe: none.** Pi has no subscription-quota API of its own.

### D9. Skills

- `llm_skill_deploy_subpath() -> ".pi/agent"` places skills at
  `~/.pi/agent/skills/<name>/SKILL.md`. In chezmoi that is `dot_pi/agent/skills/…`,
  which makes the deploy a chezmoi linked-repo change. Do not use `~/.agents/skills`,
  which other CLIs may also read.
- Keep the underscore names: the instructions say `/sase_final`, and renaming would
  break that cue. Filter pi's `name contains invalid characters` warnings for paths
  under the SASE deploy dir out of stderr. Track it as a risk in case pi ever turns the
  warnings into errors.
- `llm_skill_template_context`: `provider_name: "Pi"`, `provider_tool_name: "Pi"`. Pi
  has no native ask tool (`questionnaire.ts` is only an example extension), so the
  `sase_questions` and `sase_plan` templates need a branch for "no native tool".

### D10. The user's customizations and trust

- **Extensions:** inherit them by default. That is the reason a pi user would try SASE
  at all. Add one config field, `llm_provider.pi.extensions: inherit | none`, where
  `none` means `-ne`, with explicit SASE `-e` still loading. The safety net already
  exists: raw commits from extensions like the shipped `auto-commit-on-exit.ts` example
  are caught by `commit_finalizer_raw_commits` (`raw_commit_policy = absorb`).
- **Trust:** inherit the user's saved decision by default and pass neither `--approve`
  nor `--no-approve`. A parent-directory decision covers every `sase_N` clone under it.
  Add `llm_provider.pi.project_trust: inherit | approve | deny` as a per-project setting.
- **Hands off:** never pass `--tools`, `--no-mcp`, or Codemode settings.
- **Environment:** set `PI_SKIP_VERSION_CHECK=1`. Leave `PI_TELEMETRY` and `PI_OFFLINE`
  to the user.

### D11. Mechanical contract enforcement (phase 2)

`sase_contract.ts`, loaded with `-e` in root invocations only:

```typescript
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { existsSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";

export default function (pi: ExtensionAPI) {
  const artifacts = process.env.SASE_ARTIFACTS_DIR;
  const started = Date.now();
  let nudges = 0;
  pi.on("session_start", async (_e, ctx) => {
    if (artifacts) writeFileSync(join(artifacts, "pi_session.json"),
      JSON.stringify({ file: ctx.sessionManager.getSessionFile() }));
  });
  pi.on("tool_call", async (event) => {
    if (event.toolName !== "bash") return;
    const cmd = String(event.input.command ?? "");
    if (/\bgit\s+(commit|push)\b|\bgh\s+pr\s+(create|merge)\b/.test(cmd))
      return { block: true, reason: "SASE: the host commits and lands work; declare with /sase_final." };
  });
  pi.on("agent_before_settle", async () => {
    const sub = artifacts && join(artifacts, "final_submission.json");
    const declared = !!sub && existsSync(sub) && statSync(sub).mtimeMs >= started;
    if (declared || nudges >= 1) return;
    nudges++;
    return { continue: true, entries: [/* custom_message: "Declare with /sase_final before ending." */] };
  });
}
```

The sketch is illustrative. The real version must also:

- honor pending handoffs (plan, monitor, pipe, or questions), which are exempt from
  declaring;
- log nudges to a `wait_guard_log.jsonl` equivalent;
- leave guarded-recipe refusal to the existing `just` guard.

**What this buys:**

- The single-turn declaration rule is enforced in-process with the prompt cache
  preserved. Claude does this with a host-side resume nudge.
- Commit and PR guards fail closed, the pi-native way.
- The session file path is recorded deterministically.

**Host-side helper identity.** Export `SASE_PI_ROOT_SESSION_ID=<invocation uuid>` into
pi's environment. Teach `sase final context|defer|prepare|submit` to refuse when
`PI_SESSION_ID` is present and differs from it.

- Helpers spawned by a pi subagent extension run their own pi session, whose bash tool
  sets their own `PI_SESSION_ID`, so they are detected.
- The root's commands always match.

`decisions:helpers-return-roots-declare` rejected env-based identity because "helpers
inherit the env". Pi breaks that premise: it *overrides* `PI_SESSION_ID` per command.
This meets the record's reopen condition ("a provider exposing 'this call came from a
subagent' outside the hook payload"). The change needs a new decision record, written
through `/sase_memory_write`.

**Residual gap.** A non-pi helper launched from the root's bash tool, such as
`claude -p …`, inherits the root's value. Text coverage still applies to that case.

### D12. Install, doctor, and the interactive CLI

- **`llm_install_metadata`:**
  - `manager: "script"`, `install_script_url: "https://pi.dev/install.sh"`. It pins
    transitive dependencies and can install Node, which matters on athena (Node
    22.14 < 22.19).
  - `self_update_argv: ["update"]`, `version_argv: ["--version"]`,
    `latest_version_package: "@earendil-works/pi-coding-agent"`.
  - `display_name: "Pi"`, `vendor: "Earendil"`.
- **Doctor:**
  - check `node --version` ≥ 22.19 for npm installs;
  - check `pi --version` ≥ a tested floor (1.3.0);
  - add a deep check with `pi auth check --model <resolved model> --json`, which reports
    readiness for the model SASE will actually launch;
  - `llm_auth_evidence`: `~/.pi/agent/auth.json`, plus the common key variables
    (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `XAI_API_KEY`,
    `OPENROUTER_API_KEY`, …);
  - `SASE_PI_PATH` falls out of `provider_path_env_var()`.
- **`llm_interactive_cli`:** `menu_key: "p"` (free; used keys are a, c, g, m, o, q, x),
  `model_args: ["--model", "{model}"]`, and `bypass_args: []`, since pi has no
  permission prompts.
- **Identity:** `llm_provider_short_name: "pi"` (there is no length rule) and
  `llm_cli_status_color`. Pick a hue distinct from the existing seven.

### D13. Tests and fixtures

- **Recorded fixtures.** Capture real `--mode json` streams into
  `tests/fixtures/pi_stream/*.jsonl`, named per pi version as Grok does. Cover:
  - a no-tool reply and a tool-using reply;
  - a provider error (`stopReason: error`, exit 0);
  - a truncation;
  - an abort;
  - auto-retry, success and failure;
  - compaction.
- **Credential-free capture.** pi-ai ships a scriptable `faux` provider
  (`packages/ai/src/providers/faux.ts`). A tiny fixture-only extension that registers it
  through `pi.registerProvider` should let the real CLI emit deterministic streams with
  no API key, which could also feed an opt-in integration test. This is plausible but
  unverified; check it in Phase 0.
- **Unit tests:** the normalizer as a pure function, argv construction (explicit and
  legacy), the outcome table in D5, the effort map, re-adding user pi files, and the
  `--fork` continuation path.
- **Repo-wide tests to update:** `_MANIFEST_PROVIDERS` ("exactly the seven"),
  model-policy effort mirroring, menu-key uniqueness, palette and badge tests, and the
  skill target-path tests.

## 7. Touchpoint checklist

From the helper inventory. **R** means required for a working provider; **R\*** means
required for in-tree CI; **O** means polish. Every file is in sase; sase-core needs
nothing for these phases.

| # | Touchpoint | Req |
|---|---|---|
| 1 | `pyproject.toml` entry point `pi = "sase.llm_provider.pi:PiProvider"` | R |
| 2 | `src/sase/llm_provider/pi.py`: hooks, argv, `SASE_PI_PATH`, `SASE_PI_{LARGE,SMALL}_ARGS`, invoke loop with `--fork` continuations, missing-binary error | R |
| 3 | `_subprocess_pi.py`, plus re-export in `_subprocess.py`: event normalizer, D5 outcome table, live reply, thinking sink, usage, `run_metadata` | R |
| 4 | `_tool_call_pi.py`, plus export in `_tool_calls.py`: `tool_execution_*` → `tool_calls.jsonl` (`runtime: "pi"`) | R for the ACE tool view |
| 5 | `models.yml` `providers.pi`: models, short aliases, tiers (§D7) | R |
| 6 | `docs/reference/providers/models.md`, regenerated with `just fix` | R\* |
| 7 | `model_policy._PROVIDER_SUPPORTED_EFFORTS` | R\* |
| 8 | `instruction_delivery.py`: `CHANNEL_PI_ROOT`; `instructions/directives.py` registration | R (explicit) |
| 9 | `instructions/pi.py`: session-JSONL observer for `sase instructions verify` and coverage (marker once in `addendum`; no SASE-owned path in `project_context`) | R for "fully supported" |
| 10 | Skill deploy subpath `.pi/agent`, template context, `sase_questions`/`sase_plan` template branch, chezmoi `dot_pi/agent/skills` | R |
| 11 | `doctor/checks_providers.py` hints; `checks_deep_providers.py` (Node floor, version floor, `pi auth check`) | O+ |
| 12 | `integrations/provider_palette.py`, `provider_badges.py`, `ace/query_profile/profiles/_agents_shared.py` `AGENT_PROVIDER_VALUES` | O |
| 13 | `default_config.yml` comments and examples; `llm_provider.pi.{extensions,project_trust}` config fields (see the `gotchas` core memory) | O / R for D10 |
| 14 | Docs: new `docs/reference/providers/pi.md`; `agent-clis.md`, `index.md`, `configuration.md`, `retry-and-fallback.md`, `reference/memory/instruction-bundles.md` (delivery table), `environment-variables.md`, `llms.md`; `mkdocs.yml` nav. Read the `docs_writing` memory first | O (convention) |
| 15 | Tests and fixtures (§D13) | R\* |
| 16 | Phase 2: `pi_extension/sase_contract.ts` package data (include it in wheel data); `sase final` `PI_SESSION_ID` check; new decision record | Phase 2 |

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Pi churn: 8 releases in 15 days, 2 with breaking sections | Doctor version floor; fixtures named per version; the normalizer ignores unknown event types; a pi-CLI contract test run in a scheduled lane |
| JSON mode exits 0 on model failure or missing credentials | The D5 outcome table. Absence of `agent_settled` counts as failure |
| Cross-workspace resume runs tools in the old cwd | `--fork` only; forbid `--session`. A unit test asserts argv never contains `--session` |
| `--session <id>` y/N prompt consumes stdin | Never pass ids, only absolute paths through `--fork` |
| Contract double-load under native discovery | Explicit delivery (D3); `verify` observes the result |
| `-nc` and `--append-system-prompt` drop the user's pi `AGENTS.md` and `APPEND_SYSTEM.md` | Re-add them (D3 step 3). Later, move to `before_agent_start` filtering |
| `--append-system-prompt` treats a missing path as text | Assert the file exists before exec |
| User extensions add background tools, subagents, or auto-commits | `extensions: none` option; raw-commit absorption; settle guard; helper identity check |
| Node floor (athena has 22.14) | Script installer; doctor check |
| Underscore skill-name warnings | Filter them from stderr; watch upstream |
| Provider-wide usage-limit disable over a multi-vendor harness | No auto-disable in v1; model-scoped disable in sase-core later |
| A lingering Node process after settle | Settle watchdog (D5) |
| Token and cost semantics differ per vendor | Record pi's own numbers verbatim; label cost "pi-priced" |

## 9. Recommended solution

**Build a first-class, in-tree `pi` provider as one epic in three phases, plus a later
epic for live control.** The provider runs `pi --mode json` once per SASE invocation and
delivers the instruction bundle explicitly through `-nc` plus `--append-system-prompt`.
The event stream, not the exit code, decides each turn's outcome. Each invocation gets
its own session file under the agent's artifacts directory, and continuations always use
`--fork`. The user's pi configuration is preserved: their default model, extensions,
MCP, trust, `AGENTS.md`, and `APPEND_SYSTEM.md`. Mechanical contract enforcement follows
as a bundled pi extension plus a host-side `PI_SESSION_ID` root check. sase-core needs no
changes for any of this.

### Reference invocation

```text
PI_SKIP_VERSION_CHECK=1 SASE_PI_ROOT_SESSION_ID=<uuid> \
pi --mode json \
   --session-dir "$SASE_ARTIFACTS_DIR/pi/sessions" \
   --session-id <uuid>                     # fresh per invocation; delivery.record_session()
   [--fork <abs predecessor .jsonl>]       # retry, nudge, and successor continuations only
   --name "<sase agent name>" \
   [--model <provider/id>]                 # omitted for the pi-default tier
   [--thinking <off|minimal|low|medium|high|xhigh|max>] \
   -nc --append-system-prompt <materialized bundle> \
   [--append-system-prompt ~/.pi/agent/AGENTS.md] [--append-system-prompt ~/.pi/agent/APPEND_SYSTEM.md] \
   [-e <sase>/llm_provider/pi_extension/sase_contract.ts]   # phase 2
   [-ne]                                   # only when llm_provider.pi.extensions = none
   [$SASE_LLM_*_ARGS | $SASE_PI_*_ARGS] \
   < prompt on stdin
```

The legacy fallback, used when materialization fails, drops `-nc` and the bundle
argument and passes `--append-system-prompt "<pi single-turn directive>"` instead.

### Phases

**Phase 0: live spike (S, about half a day).**

- Install pi with the script installer on athena.
- Capture real fixtures: a cheap real model plus the faux-provider extension.
- Confirm the unverified items: exit 0 on error, the stderr shape, skill warnings, the
  `--fork` cwd behavior, the session system-message sections under `-nc` +
  `--append-system-prompt`, and whether a lingering process appears after settle.
- Output: a fixture set and a short "verified / changed" note appended to this research.

**Phase 1: core provider (M–L).**

- Touchpoints 1–10, 13, 15, and 14 (docs).
- Explicit delivery with user-file preservation.
- The D5 outcome table and settle watchdog.
- Usage, cost, and physical model recorded in `run_metadata.json`.
- `--fork` retry continuations.
- Doctor, `agent-cli install pi`, and tmux-agent `p`.

Acceptance:

- A pi user with an untouched `~/.pi` runs `%m:pi-default` and gets a landed commit.
- `sase instructions verify` shows the marker exactly once and no SASE-owned native
  file.
- Auth failure, 429, overload, and truncation each surface as readable failures and
  retry where configured.
- The LLM Calls panel shows pi tool calls.
- `just check` is green.

**Phase 2: enforcement (M).**

- `sase_contract.ts`: session record, commit/PR guard, bounded declaration nudge at
  `agent_before_settle`.
- The `sase final` `PI_SESSION_ID` root check, with a new decision record that amends
  `helpers-return-roots-declare` for pi.
- Optional: move context filtering into `before_agent_start` if the Phase 0 spike shows
  clean first system messages.

**Later epic: live control and lineage (M–L, separate).**

- RPC-mode transport behind the same normalizer for steer, follow-up, and abort. This
  revives the Agents-tab message feature and needs a decision record on in-turn
  steering.
- Native pi→pi `#fork`/`#resume` through `--fork`.
- A cost surface and rollups in sase-core.
- A model-scoped usage disable in sase-core.
- Size-alias pool membership after usage data exists.
- An optional pi-gallery bridge package.

### Not recommended

- An SDK or Node bridge.
- A long-lived pi process across turns.
- Print mode.
- An out-of-tree plugin repo for the "fully supported" goal.
- Native `AGENTS.md` delivery as the default.
- `--session` for continuation.
- Overriding the user's tools, Codemode, MCP, or trust by default.
- Usage-limit auto-disable for pi in v1.
- A sunset feature flag for explicit delivery.

### Open questions for Bryan

1. **Default tier.** The `pi-default` sentinel (pi picks the user's default model) is
   recommended. Concrete SASE-chosen tiers are the alternative.
2. **User extensions in SASE runs.** `inherit` (recommended) or `none` by default?
3. **OpenCode's future.** Pi now covers OpenCode's niche as SASE's multi-vendor backend,
   and `readable-agents-md` notes that Qwen and OpenCode lack real usage. Should a later
   decision consider retiring OpenCode once pi has usage data?

## 10. Sources

**pi** (`d2e7d8b7c`):

- `README.md`;
- `packages/coding-agent/{package.json,CHANGELOG.md}`;
- `docs/`: `cli.md`, `cli-integration.md`, `json.md`, `rpc.md`, `message-types.md`,
  `session-format.md`, `sessions.md`, `configuration.md`, `settings.md`, `security.md`,
  `skills.md`, `extensions.md`, `environment-variables.md`, `providers.md`,
  `custom-provider.md`;
- `src/`: `main.ts`, `cli/initial-message.ts`, `modes/print-mode.ts`,
  `core/resource-loader.ts`, `core/system-prompt.ts`, `core/skills.ts`,
  `core/session-manager.ts`, `core/session-cwd.ts`, `core/agent-session.ts`,
  `core/extensions/{types.ts,runner.ts,loader.ts}`, `core/tools/bash.ts`,
  `utils/shell.ts`;
- `examples/extensions/{auto-commit-on-exit.ts,permission-gate.ts,hello.ts,todo.ts}`;
- `packages/ai/src/providers/faux.ts`.

**SASE** (`4b7b981532`):

- `pyproject.toml`;
- `src/sase/llm_provider/`: `base.py`, `_hookspec.py`, `grok.py`, `qwen.py`,
  `opencode.py`, `claude.py`, `_subprocess_stream.py`, `_subprocess_opencode.py`,
  `_subprocess_plain.py`, `_subprocess_reap.py`, `_subprocess_artifacts.py`,
  `instruction_delivery.py`, `_claude_instruction_delivery.py`, `_registry_metadata.py`,
  `registry.py`, `model_manifest.py`, `model_validity.py`, `models.yml`,
  `provider_disable.py`, `types.py`, `commit_finalizer_raw_commits.py`;
- `src/sase/instructions/{directives.py,fingerprints.py}`;
- `docs/contribute/instruction-bundle-internals.md`;
- `docs/reference/memory/instruction-bundles.md`;
- `docs/reference/providers/{agent-clis.md,models.md,plugins.md,qwen.md}`;
- git history for Grok, Qwen, and OpenCode: `3085a0d287`, `8847d07a08`, `724f9ea9c2`,
  `4d0c348ddb`, `aca73324c3`;
- the project and home `AGENTS.md` (sizes and contract headings).

**Memory:**

- `decisions:{adapters-normalize-harnesses, single-turn-agents,
  instructions-per-invocation, readable-agents-md, helpers-return-roots-declare,
  rust-core-required}`;
- `sase_flags.md`.

**Prior research:** `202610/sase_for_pi_users/sase_for_pi_users__final.md`.
