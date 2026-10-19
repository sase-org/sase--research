# Adding pi as a fully supported SASE provider

_Consolidated report, 2026-10-19. It merges five independent researcher reports (`__cdx`,
`__cld`, `__grk`, `__mus`, `__gem`, all in this directory) with the lead researcher's own
check of every disputed claim against the pi, SASE, and sase-core source. It builds on
the 2026-10-11 consolidated report
[SASE for pi users](../sase_for_pi_users/sase_for_pi_users__final.md). That report
decided **whether** SASE should host pi. This one decides **how** to build the provider._

## 1. Bottom line

- **Build pi as an in-tree, built-in `sase_llm` provider.** It runs **one
  `pi --mode json` process per SASE provider invocation**, in the claimed workspace. All
  five researchers agree on this shape. It follows the existing adapter split (`pi.py`,
  `_subprocess_pi.py`, `_tool_call_pi.py`), and v1 needs **no sase-core change**.
- **The event stream decides the outcome; the exit code does not.** In JSON mode, pi
  exits nonzero only when it throws. A model error, an abort, or output truncation all
  exit 0 (`modes/print-mode.ts`). `agent_end` does not end the turn; only
  `agent_settled` does. This is the integration's most important correctness rule.
- **Deliver instructions explicitly from day one.** In a SASE workspace, pi's native walk
  loads both the workspace `AGENTS.md` and `~/AGENTS.md`. On athena both contain the
  Final Declaration contract, which is the double load the instruction-bundle epic fixed.
  The fix has three parts:
  - deliver the bundle with `--append-system-prompt <file>`;
  - suppress native discovery with `-nc` in SASE-managed projects, as Codex does with
    `project_doc_max_bytes=0`;
  - re-add the user's own pi files that `-nc` and the append flag drop.

  The prior report said native `AGENTS.md` loading was enough. That claim is stale.
- **Send the prompt on stdin.** Argv is capped at 128 KiB per argument on Linux. `@file`
  is no better: pi wraps the file's content in `<file name="…">` tags.
- **Keep sessions under the run's artifacts, and never continue with `--session`.** Pi
  runs a reopened session's tools in the cwd stored in the session header. Reopening a
  session from another numbered workspace would therefore edit the old clone.
  - Continuations inside one invocation reuse the same `--session-id`. The cwd is the
    same, so this is safe.
  - Continuations across workspaces use `--fork <abs path> --session-id <new>`.
- **Preserve the user's pi.** Keep their auth, default model, extensions, MCP, Codemode,
  tool selection, and trust decisions. Pass no `-ne`, no tool flags, and no blanket
  `--approve`.
- **Join the fleet conservatively:**
  - no autodetect priority, because `pi` is a generic binary name (the same reason
    `grok` and `muse` have none);
  - no size-alias membership yet;
  - no usage-limit auto-disable. SASE keys its disable store by provider name, and pi
    fronts many vendors, including subscriptions that SASE's own providers also use.
- **Phase 2 adds a bundled pi extension, `sase_contract.ts`.** It is loaded with `-e` and
  needs no npm step. It adds mechanical enforcement:
  - a commit/PR guard;
  - a bounded declaration nudge at settle time;
  - exact filtering of SASE-owned context files.

  A host-side check on pi's per-command `PI_SESSION_ID` can also make "only roots declare"
  mechanical. Pi would be the first provider where that is possible.
- **Later epics:**
  - RPC steering;
  - native pi→pi fork/resume;
  - a first-class cost surface;
  - backend-scoped quota disable.

  Never keep a pi process alive across SASE turns.

**Effort:** a Phase 0 live spike (S), then Phase 1 (M–L) and Phase 2 (M). The full plan
is in §12.

## 2. Evidence and confidence

| Source | Snapshot |
|---|---|
| pi monorepo (`sase repo open gh:earendil-works/pi`) | `d2e7d8b7c` (2026-10-19); `@earendil-works/pi-coding-agent` **1.3.0** (2026-10-15), MIT, Node `>=22.19.0` |
| SASE | `4b7b981532` (release 0.18.0); eight `sase_llm` entry points: `agy`, `claude`, `codex`, `fakey`, `grok`, `muse`, `opencode`, `qwen` |
| sase-core | `753fa21a` |
| Prior research | `202610/sase_for_pi_users/sase_for_pi_users__final.md` (pi 1.1.0, 2026-10-11) |
| Decision records | `instructions-per-invocation`, `readable-agents-md`, `rust-core-required`, `helpers-return-roots-declare`, `adapters-normalize-harnesses`, plus the `sase_flags` note |

**Not done.** No live pi run was made. Pi is not installed on athena: there is no `pi` on
PATH and no `~/.pi`. Athena's Node is also v22.14.0, below pi's floor. Every pi claim
below comes from source and docs at `d2e7d8b7c`. Phase 0 (§12) closes this gap.

**What the lead checked directly.** Every disagreement in §10 was resolved by reading the
code it depends on: pi's `main.ts`, `session-manager.ts`, `resource-loader.ts`,
`print-mode.ts`, `file-processor.ts`, `skills.ts`, `tools/bash.ts`,
`extensions/{types,runner}.ts`, `agent-loop.ts`, `ai/src/auth/oauth/`; SASE's
`instruction_delivery.py`, `codex.py`, `grok.py`, `claude.py`, `model_manifest.py`,
`model_policy.py`, `_effort_args.py`, `feature_flags/registry.py`; and sase-core's
`provider_disable.rs` and module list.

**Confidence.** It is high for:

- placement;
- transport;
- the outcome rules;
- instruction suppression;
- session semantics;
- omitting autodetect.

It is medium for:

- tier defaults and usage-limit strings (both need a live `pi --list-models` and captured
  failures);
- the Phase 2 extension's interaction with arbitrary user extensions.

## 3. What the 2026-10-11 report got right, and what changed

**Still right:**

- host pi; don't become it;
- the provider comes first;
- JSON mode first and RPC later, behind one event normalizer;
- `agent_settled` is terminal, and exit code 0 is not success;
- no daemon across turns;
- leave pi's tools, MCP, and Codemode alone;
- project trust is a per-project decision;
- a `sase-pi` extension is the strongest follow-up;
- pin a minimum pi version and test against recorded fixtures.

**Corrections:**

1. **Instruction delivery.** The report said that because pi loads `AGENTS.md`/`CLAUDE.md`
   natively, "no extra instruction delivery is needed." SASE has since cut over to
   per-invocation bundles. On this machine, native loading double-loads the contract
   (§6, D6). mus still repeats the old claim; the other four reports and the code
   reject it.
2. **Session continuity.** The report's §6.5 recommended "an absolute `--session <path>`
   with a SASE-owned `--session-dir`." `SessionManager.open()` takes its cwd from the
   session header (`session-manager.ts:1782`), and `main.ts` passes no override. Tools
   then run in that cwd (`main.ts:867`). Use `--fork` across workspaces (D7).
3. **Skill names.** Pi validates names against `^[a-z0-9-]+$` (`skills.ts:99`). Every
   SASE skill name contains underscores, so each launch prints a warning per skill. The
   skills still load (`skills.ts:329`).
4. **Helper identity.** The report proposed a root token passed through `-e`. A better,
   host-verifiable signal exists: pi deletes and re-sets `PI_SESSION_ID` for every bash
   command (`tools/bash.ts:194–206`). See D13.
5. **Pi churn.** Pi made 8 releases in the 15 days after 1.0.0. The 1.0.3 and 1.2.0
   releases have "Breaking Changes" sections. Changes that matter here:
   - 1.2.0 removed the experimental server/client/protocol stack;
   - `--thinking` now accepts `max`;
   - print-mode `length` now exits 1, while JSON mode is unchanged;
   - since 1.3.0, an ambiguous `--model` prefers the provider that has credentials.

   The JSON event vocabulary has stayed stable since 1.1.0.
6. **`docs/agent_providers.md`** no longer exists at that path (mus). The current
   contract lives in `_hookspec.py` and the provider modules.

## 4. What "fully supported" means in SASE today

**The contract.** `LLMProvider` (`base.py`) has one abstract method,
`invoke(...) -> InvokeResult(content, usage)`. Everything else comes from about two dozen
pluggy hooks in `_hookspec.py`:

- identity and catalog;
- instruction delivery;
- skill template context and deploy subpath;
- autodetect, install, auth evidence, and the interactive CLI;
- retry and usage-limit defaults;
- usage capabilities and probe;
- sync ceiling.

`SASE_PI_PATH` falls out of `provider_path_env_var("pi")`. Nested model strings already
route: `registry.py` splits on the first `/`, so `pi/anthropic/<id>` resolves to provider
`pi` and model `anthropic/<id>` once `pi` is registered.

**Surfaces that only an in-tree provider can reach.** An external plugin can run models,
but it cannot appear here:

| Surface | Where |
|---|---|
| Bundled catalog and its uniqueness, descent, and "exactly N providers" tests | `llm_provider/models.yml`, `model_manifest.py`, `_MANIFEST_PROVIDERS` |
| Effort mirror | `model_policy._PROVIDER_SUPPORTED_EFFORTS`, `_CLI_VALIDATED_PROVIDERS` |
| Single-turn directive registry | `instructions/directives.py` `DIRECTIVE_PROVIDERS` |
| Verify and coverage observers | `instructions/run_index.py` `_KNOWN_PROVIDERS`, `coverage_sessions.py`, `_verify_observers.py`, `_verify_aggregate.py` |
| Channel ids | `instruction_delivery.py` `CHANNEL_*` |
| Presentation | `integrations/provider_palette.py`, `provider_badges.py`, `AGENT_PROVIDER_VALUES`, doctor hints, menu-key tests |
| Docs | `docs/reference/providers/`, generated model tables |

The provider is therefore **in-tree**. Use an external plugin only as a private spike.
When pi lands, update the sentence in `docs/contribute/plugin-api.md` that says extra
providers belong in external packages; Grok and Muse already broke that rule.

**Closest templates:**

| Concern | Template |
|---|---|
| JSONL stream parser | OpenCode, Qwen (`_subprocess_opencode.py`, 155 lines) |
| Stranded-wait continuation that resumes the same session | Claude (`--resume` + `_WAIT_CONTINUATION_NUDGE`), Muse |
| System-prompt file channel plus native suppression | Claude (`--append-system-prompt-file` + `claudeMdExcludes`) |
| Coarse suppression applied only in SASE-managed projects | Codex (`project_doc_max_bytes=0` behind `project_is_sase_managed`, `codex.py:300`) |
| Generic binary name, no autodetect priority, doctor identity check | Grok, Muse |
| Nested `provider/id` catalog | OpenCode (`models.yml`) |
| Script installer | Muse (`manager: "script"`) |

Grok's first commit was 908 lines including tests, followed by about 15 polish commits.
Muse runs to roughly 2k lines across modules. Expect pi to fall between the two.

## 5. Pi's host surface (verified at `d2e7d8b7c`)

### Modes

| Mode | Lifetime | Fit |
|---|---|---|
| `--mode json` | All prompts up front; streams JSONL; exits | **v1.** Single-turn shaped. Extension dialogs resolve at once in headless mode (`confirm`→false, `select`→undefined; `runner.ts` `noOpUIContext`), so nothing can hang |
| `--mode rpc` | Long-lived JSONL commands and events | **Later**, for steer, follow-up, and abort. A `prompt` response means only that the prompt was accepted. Dialogs become requests that must be answered. Rejects `@file` |
| `-p` print | Final text only | Rejected: no tool, usage, or settle events |
| SDK (`createAgentSession`) | In-process Node | Rejected: a TypeScript bridge coupled to a fast-moving API |
| Pi Durable | Experimental; one process per storage | Rejected: a second owner of lifetime and durability |

### The JSON contract the adapter depends on

- **First record:** the session header,
  `{"type":"session","version":3,"id",…,"cwd"}`.
- **Run boundaries:** `agent_start`, `turn_start`, `message_*`, `tool_execution_*`,
  `turn_end`, `agent_end`, **`agent_settled`** (`{aborted}`).
  - `turn_end` can be followed by more tool and model work.
  - `agent_end` can be followed by retries, compaction recovery, or queued messages.
- **Streaming:**
  - `message_update.assistantMessageEvent` carries `text_delta`, `thinking_delta`, and
    `toolcall_*` deltas.
  - The top-level `usage` on `message_update` is cumulative for that one response.
  - `message_end.message` is the authoritative final message.
- **Assistant message fields:**
  - `provider`, `model`, `responseModel`, `thinkingLevel`;
  - `usage` (`input`, `output`, `cacheRead`, `cacheWrite`, `cost.total` in USD);
  - `stopReason`: one of `stop`, `length`, `toolUse`, `error`, `aborted`, `deferred`;
  - optional `errorMessage`.
- **Tools:**
  - `tool_execution_start` carries `toolCallId`, `toolName`, and `args`;
  - `tool_execution_end` carries `result`, `isError`, and `durationMs`;
  - nested Codemode calls carry `parentToolCallId`.
- **Retry and compaction:**
  - `auto_retry_start` and `auto_retry_end` (on final failure: `success:false` plus
    `finalError`);
  - `compaction_start` and `compaction_end` (with `result.usage`).
- **Framing:** split strictly on LF. U+2028 and U+2029 are valid inside JSON strings.
  SASE's `stream_json_lines` already splits only on `\n` at the byte level
  (`_JsonlPipe.feed`). Do not use `splitlines()`.
- **Exit codes:**
  - a thrown error exits 1;
  - startup failures exit 1: no model, an extension load failure, or any error-level
    diagnostic (`main.ts:917–925`);
  - SIGTERM exits 143, after killing tracked detached children and disposing the
    runtime;
  - everything else exits 0.
- **Teardown:** print and JSON mode set `process.exitCode` and return without calling
  `process.exit` (`main.ts:987–998`). A lingering user extension or MCP handle can
  therefore keep Node alive after settle.

### Flags SASE needs

| Need | Flag | Verified note |
|---|---|---|
| Machine output | `--mode json` | |
| Prompt | stdin, with no message argv | `readPipedStdin` reads stdin outside RPC mode (`main.ts:894`). `@file` is wrapped in `<file name="…">` tags (`cli/file-processor.ts:57–78`) |
| Session storage | `--session-dir <abs>` | With a custom dir, files are `<ts>_<id>.jsonl`, and lookups filter by header cwd (`session-manager.ts:1874`) |
| Session id | `--session-id <id>` | Opens the session if it exists *for this cwd*. Otherwise it creates one and prints a stderr warning |
| Cross-workspace continuation | `--fork <path> [--session-id <new>]` | Writes a new header with the **current** cwd and `parentSession`. Cannot be combined with `--session`, `--continue`, `--resume`, or `--no-session` |
| Display name | `-n/--name` | Shows the SASE agent name in pi's `/resume` picker |
| Model | `--model provider/id` | Fuzzy matching. If ambiguous, prefers the provider with credentials; JSON mode cannot prompt |
| Effort | `--thinking off…max` | **Silently clamped** to what the model supports (`agent-session.ts:2638–2644`) |
| Suppress native context | `-nc/--no-context-files` | Drops the agent-dir context file **and** every ancestor context file |
| Explicit channel | `--append-system-prompt <text\|path>` | Repeatable. **Replaces** a discovered `APPEND_SYSTEM.md` (`resource-loader.ts:663`). A path that does not exist is treated as literal text |
| Extensions | `-e <path>`; `-ne` | `-ne` still loads explicit `-e` paths |
| Trust | `-a`/`-na` | Saved trust: the nearest ancestor's decision wins. Untrusted project `.pi/` resources are skipped headlessly. Context files load regardless of trust |
| Auth probe | `pi auth check --provider <p> --model <m> --json` | Prints `ready`, `not_ready`, or `invalid`, and exits 0, 1, or 2 |
| Startup noise | `PI_SKIP_VERSION_CHECK=1` | |

**Context discovery** (`resource-loader.ts:184–268`). Pi loads the agent-dir file first,
then walks from cwd up to `/`. It takes one file per directory, in the order
`AGENTS.override.md` > `AGENTS.md` > `AGENTS.MD` > `CLAUDE.md` > `CLAUDE.MD`.

**System prompt.** It is built from named sections:

- `preamble`
- `tools`
- `rules`
- `addendum` (from the append flag)
- `project_context` (each file wrapped in `<project_instructions path>`)
- `skills`
- `cwd`

The session's first system message persists every section, and later changes are stored
as section patches (`docs/session-format.md`). That makes exact delivery verification
possible.

## 6. Design decisions

### D1. Placement and packaging: in-tree Python provider; TypeScript extension as package data

All five reports agree on placement. Phase 2's extension ships inside the wheel as
`src/sase/llm_provider/pi_extension/sase_contract.ts` and is loaded by absolute path.
Pi loads extensions with jiti and aliases its own `typebox`, `pi-ai`, and
`pi-coding-agent` dependencies, so a single `.ts` file needs no `npm install`. That keeps
the adapter and the guard in version lockstep, with no npm publishing. A
gallery-published `sase-pi` bridge package is an optional, separate step.

### D2. Transport: JSON per invocation now; RPC per turn later; never a daemon

JSON mode has no stdin protocol and no dialog loop, and it uses the same kill and reap
semantics as every other provider. RPC buys steer, follow-up, abort, and `get_state`, but
it belongs to a live-control epic. The Agents-tab `m` interrupt feature was removed in
`1a46198f14` without recorded rationale, and that epic needs a decision record on in-turn
steering first.

JSON and RPC share event shapes. Write the normalizer as a **pure function over event
dicts**, so RPC can reuse it. RPC that lives only within one SASE turn is compatible with
`single-turn-agents`. A child kept alive across turns is not.

### D3. Code location: Python in v1; sase-core only for cross-frontend wires

cdx argued for a Rust event reducer in sase-core from the start. The other four said v1
needs no Rust. **Resolution: Python.**

- Every existing provider parser is Python.
- sase-core contains no provider stream parsing. Its only provider-specific code is
  `provider_usage/{agy,grok,muse}.rs`.
- Frontends read the artifacts the host writes, not raw pi streams. So the
  `rust_core_backend_boundary` test ("would another frontend need this to match the
  TUI?") does not apply to the parser.

What does cross the boundary, and should land in sase-core with a
`sase-core-revision.txt` bump when needed:

- a first-class cost field;
- backend-scoped quota disable (D9);
- any change to model validity.

Keeping the normalizer a pure function makes a later port cheap. sase-core's
`retryability` classifier is the precedent for that shape.

### D4. Prompt transport: stdin

Write the prompt to stdin and close it. Pi reads stdin to EOF before starting.
Drain stdout and stderr while writing, for example from a writer thread, so large prompts
cannot deadlock against startup diagnostics. Reject argv, which OpenCode uses today
(`opencode.py:277`) and which hits the 128 KiB limit that Grok guards against. Reject
`@file` too (grk), because it changes the prompt into a tagged file attachment.

Reserve `--mode`, the session flags, and the managed `-e` against conflicting user extra
args. Note that pi prompt templates and input handlers may still transform a prompt.
Treat an empty or handled run as an explicit result, never as a silent success.

### D5. Turn outcome: the stream decides

Track:

- whether `agent_settled` arrived, and its `aborted` flag;
- the last assistant `message_end`;
- the latest `auto_retry_end.finalError`;
- any compaction `errorMessage`.

| Observation | Adapter result |
|---|---|
| rc ≠ 0 | Failure. Pass stderr through, and add the last `errorMessage` |
| rc = 0, no `agent_settled` (EOF, crash after the header, malformed terminal records) | Failure: "pi stream ended before agent_settled" |
| `agent_settled.aborted` | Failure (aborted) |
| Last `stopReason` is `error` or `aborted` | Failure. Synthesize rc = 1, and write `[pi] <errorMessage>` and `finalError` into stderr so `llm_default_retry_config` patterns can match |
| Last `stopReason` is `length` | Failure: "truncated at output limit". Retryable, as with Grok's truncation handling |
| Last `stopReason` is `deferred` | Incomplete. Unsupported in v1, and never an invisible wait |
| Last `stopReason` is `toolUse` | Success only if the final tool batch ended the run (pi's `terminate:true`) and the host's normal declaration checks pass. Otherwise incomplete |
| Last `stopReason` is `stop` | Success |

Two cases are deliberately **not** failures:

- a tool result with `isError`, because the model may repair it;
- an earlier model error that pi's own retry then recovered from.

Keep the existing handling for real plan, monitor, questions, and pipe handoffs, and the
post-declaration completion watchdog.

**Add a settle watchdog.** If the process is still alive N seconds after `agent_settled`
(for example 15), send SIGTERM and record a teardown stall. This does not change an
outcome that was already classified.

### D6. Instruction delivery: explicit, exactly once, preserving the user's own pi files

**Why native discovery is wrong here.** Pi's walk from a SASE workspace loads the
workspace `AGENTS.md` and `~/AGENTS.md`, and both contain the contract heading. No
directory between the workspace and `$HOME` has a context file today. That walk is a
textbook `instructions-per-invocation` violation. Pi has both a suppression switch and a
system-prompt file channel, so it belongs with Claude, Codex, Grok, and Muse, not with
the legacy agy, Qwen, and OpenCode group.

**Delivery plan:**

- root slot: `{"status":"explicit","channel":"pi.append_system_prompt"}`. The id matches
  `CHANNEL_RE`. No `max_bytes` is needed, because the bundle travels as a file path;
- subagent slot: `{"status":"none"}`. Pi has no native subagents, and subagent
  extensions spawn separate pi processes.

**Phase 1 adapter steps:**

1. Call `delivery.materialize("root")`, which writes a 0600 file. Assert that the file
   exists before exec, because pi treats a missing path as literal text. Pass
   `--append-system-prompt <bundle>`.
2. **If `project_is_sase_managed(cwd)`, pass `-nc`.** This is the Codex rule: coarse
   suppression only where SASE owns the project's files. In other projects, repo-owned
   `AGENTS.md` files keep loading natively (R1). The SASE-owned `~/AGENTS.md` still
   double-loads there, exactly as it does for Codex today. Phase 2 removes that gap.
3. **Re-add the user's pi files** that step 1 or 2 would drop. Pass each as an additional
   `--append-system-prompt`, unless SASE owns it:
   - when `-nc` is set: the first agent-dir context file in
     `$PI_CODING_AGENT_DIR` or `~/.pi/agent`, checked in the order
     `AGENTS.override.md`, `AGENTS.md`, `AGENTS.MD`, `CLAUDE.md`, `CLAUDE.MD`;
   - always: `<agent-dir>/APPEND_SYSTEM.md`, because any append flag replaces the
     discovered file.

   Known v1 loss: a trusted project's `.pi/APPEND_SYSTEM.md`. Document it.
4. Call `delivery.record_session(session_id)`.
5. On any materialization failure, call `report_fallback(...)` and use the legacy path.
   That path drops `-nc` and passes `--append-system-prompt "<pi single-turn
   directive>"`; native discovery then supplies the readable projection.

**Phase 2: exact filtering.** In the extension's `before_agent_start`, remove exactly the
`sase_owned_instruction_paths()` entries from `systemPromptOptions.contextFiles`,
comparing realpaths. `types.ts` documents those options as mutable. Then drop `-nc`.
This keeps every unrelated context file in its native `project_context` position, and it
closes the non-SASE-managed gap.

Caveat: a handler that throws at runtime is logged and the run continues, so a filter
failure turns into a silent double load. The verify observer (D14) must catch it, and the
`-nc` path must stay as the fallback.

**No sunset flag.** grk proposed `pi_explicit_instructions` (sunset); cld said none.
**Resolution: none.**

- The four existing `*_explicit_instructions` flags are checked inside each adapter's
  `instruction_delivery()` (`grok.py:327`), not in the shared boundary. A pi adapter can
  declare explicit delivery without a flag.
- `sase_flags` reserves sunset flags for keeping an *old* branch reachable, and pi has no
  old branch.
- The boundary's per-invocation legacy fallback is already the safety net.

If the epic would expose a half-built pi between phases, use a `beta` flag as epic
scaffolding (per `sase_flags`), or simply land the entry point last.

**Directive.** Add `_PI_SINGLE_TURN_DIRECTIVE` to `directives.py`, along with its
`DIRECTIVE_PROVIDERS`, display-name, and symbol entries, so the bundle gets a
`pkg.provider.pi` section. The directive should say:

- this session is one turn, and nothing can wake you;
- `bash` runs in the foreground with no default timeout, so never background with `&`,
  `nohup`, or `setsid`, and hand long commands to `/sase_monitor`;
- skills are files to read: `/sase_final` means
  `~/.pi/agent/skills/sase_final/SKILL.md`, and pi's own form is `/skill:<name>`;
- never commit.

`llm_sync_ceiling_seconds` returns `None`, because pi's bash tool has no default timeout.
Do not copy Muse's 10-minute value.

### D7. Sessions and continuations

- **Storage:** `--session-dir "$SASE_ARTIFACTS_DIR/pi/sessions"`, an absolute path. The
  session files stay durable with the agent record and out of the user's
  `~/.pi/agent/sessions` picker.
- **Fresh id per invocation:** a new UUID through `--session-id`. Record `pi_session_id`
  and `pi_session_file` in `run_metadata.json`. Filter pi's "creating a new session with
  that id" warning out of stderr.
- **Continuations inside one invocation** (the stranded-wait nudge, the interrupt
  message): rerun with the **same** `--session-dir` and `--session-id` in the same
  workspace. `findById` matches because the cwd matches, so the session reopens with
  tool fidelity and a warm prompt cache. This is grk's point, and it mirrors Claude's
  `--resume`. Use `ends_with_wait_claim` and the existing continuation cap, and log to
  `wait_guard_log.jsonl`.
- **Continuations across workspaces:** `--fork <abs predecessor .jsonl> --session-id
  <new>`. This covers a retry that preserves the workspace (once it lands elsewhere), and
  later the native pi→pi `#fork`/`#resume`. The fork records `parentSession`, and the
  copied prefix keeps the provider-side prompt cache warm. A fork copies context only,
  never repository state.
- **Default for successor SASE turns:** a fresh session, plus SASE's existing portable
  history injection (cdx). Automatically reusing native sessions risks stale workspace
  paths, an old bundle, and duplicated history. Native fork for pi→pi is a later
  opt-in.
- **Forbidden:**
  - `--session <path|id>`. A path runs in the header's cwd. An id that matches only
    another project's session triggers a y/N "Fork this session into current
    directory?" prompt, which reads the same stdin as the prompt (`main.ts:401–404`).
  - `--continue` and `--resume`.
  - `--no-session`, which discards the verify evidence.

  Add a unit test asserting that argv never contains `--session`.

### D8. Models, tiers, and effort

- **Catalog.** Add `models.yml` `providers.pi` with nested `provider/id` entries, as
  OpenCode does, so ids stay unique across providers. Explicit `%model:pi/<anything>`
  passes through untouched; that covers virtual models and any vendor the user has
  credentials for. Do not enumerate pi's 30+ backends. Do not register bare popular
  names such as `sonnet` that would steal routing from other providers. **Do not use
  gem's list** (`claude-3-7-sonnet`, `gpt-4o`, …). It was stale on arrival.
- **Tiers: a `pi-default` sentinel** (cld). The manifest requires every tier to name a
  catalog model (`model_manifest.py:154`), so list `pi-default` as a model and use it for
  both tiers. For that model the adapter omits `--model`, and also omits `--thinking`
  unless an effort was requested, so pi uses the user's own `defaultModel` and
  `defaultThinkingLevel`. SASE cannot know which vendors the user has credentials for,
  and a hardcoded `anthropic/…` tier fails with "no API key" for many users.
  - The cost: SASE's internal `small`-tier calls go to the user's default model.
  - The alternative (grk, mus): concrete OpenCode-style tiers.
  - Add a few curated short aliases picked from `pi --list-models` at implementation
    time, and record that date.
- **Prefer exact provider-qualified ids** for reproducible tasks. Record what pi actually
  resolved, from the assistant `provider`, `model`, and `responseModel` fields, in
  `run_metadata.json`, so the row can honestly show `PI(pi-default → anthropic/…)`.
- **Effort map:**
  - `none` → `--thinking off`;
  - `minimal`, `low`, `medium`, `high`, `xhigh`, and `max` map 1:1;
  - pass effort only through `--thinking`, never as a `:<level>` model suffix;
  - set `_PROVIDER_SUPPORTED_EFFORTS["pi"]` to all seven levels.
- **Clamping and SASE's no-silent-downgrade promise** (cdx). Pi clamps silently, but an
  explicit `%effort` must never be silently downgraded (`_effort_args.py`). Pi does not
  belong in `_CLI_VALIDATED_PROVIDERS`, because it does not validate; it clamps.
  - v1 records the effective `thinkingLevel`. When an explicit effort was clamped, it
    raises a visible run warning.
  - Phase 2's extension checks the effective level before the first model request and
    fails clearly.
- **Size aliases:** not in v1. Add pi only after doctor identity and auth checks exist
  and usage is measured (`size-alias-effort-ladder`). Note that
  `llm_provider.provider: pi` does not override an explicit `default_model: @large`
  pool; document that.

### D9. Usage, cost, retry, and quota

- **Tokens.** Count each completed assistant message once, from `message_end.usage`:

  | pi field | SASE field |
  |---|---|
  | `input` | `input_tokens` |
  | `output` | `output_tokens` |
  | `cacheRead` | `cache_read_input_tokens` |
  | `cacheWrite` | `cache_creation_input_tokens` |

  - Never sum `message_update.usage`; it is cumulative per response. gem's sketch makes
    this mistake.
  - Never re-count the copies in `turn_end` and `agent_end`.
  - Add `compaction_end.result.usage`.
  - Label the total "assistant usage" until nested model-tool and session-only usage is
    reconciled against session entries (cdx).
- **Cost.** Accumulate `usage.cost.total` into `run_metadata.json` as `pi_cost_usd`,
  labeled pi-priced. A zero or missing price does not mean the call was free.
  `InvokeResult.usage` holds only integers, and a first-class cost field is a
  cross-frontend sase-core change for later.
- **Retry.** Pi already retries transient errors itself (`auto_retry_*`), so keep the
  SASE layer conservative:
  - match patterns on the synthesized stderr: `overloaded`, `rate limit`, `429`, `529`,
    `fetch failed`, `ECONNRESET`, and `truncated at output limit`;
  - use longer waits;
  - set `preserve_workspace=True`.
- **No usage-limit auto-disable in v1.** Omit `llm_default_usage_limit_config`; gem's
  shipped patterns are rejected. sase-core's provider-disable store is keyed by the
  provider string (`provider_disable.rs`). One Anthropic limit would therefore disable
  every pi route, including OpenRouter and local models.
- **New lead finding: pi shares subscriptions with SASE's other providers.** pi-ai ships
  sign-in flows for Anthropic, OpenAI Codex and ChatGPT, xAI, Meta (Muse), and GitHub
  Copilot (`packages/ai/src/auth/oauth/`). So:
  - a pi route can drain the same subscription SASE attributes to `claude`, `codex`,
    `grok`, or `muse`;
  - SASE's per-provider usage windows and disables cannot see that link in either
    direction.

  Model it later in sase-core as a backend-scoped routing identity: harness × credential
  or backend × model. Until then, document the overlap. SASE should not default tiers to
  a subscription route; whether a vendor allows subscription use through a third-party
  harness is that vendor's terms and the user's call.
- **Usage probe:** none. Pi has no remaining-quota API of its own.

### D10. Skills

- `llm_skill_deploy_subpath() → ".pi/agent"`, which deploys to
  `~/.pi/agent/skills/<name>/SKILL.md`. In chezmoi that is `dot_pi/agent/skills/…`, so
  the deploy is a linked-repo change. Deploy only from a landed source revision
  (`generated_skills`).
- Do not add `~/.agents/skills` as an extra deploy path (mus suggested it). Other CLIs
  read that path too.
- Keep the underscore names, because the instructions say `/sase_final`. Filter pi's
  "name contains invalid characters" warnings for paths under the SASE deploy dir. Watch
  upstream in case those warnings become errors.
- `llm_skill_template_context`: `provider_name` and `provider_tool_name` are `"Pi"`, and
  there is no native ask tool. The `sase_questions` and `sase_plan` templates need a
  "no native tool" branch.

### D11. The user's customizations and trust

- **Extensions: inherit them.** That is why a pi user would try SASE at all. Add a config
  field, `llm_provider.pi.extensions: inherit | none`. `none` maps to `-ne`, and SASE's
  `-e` still loads. Raw commits made by extensions are caught by
  `commit_finalizer_raw_commits`.
- **Trust: inherit by default.** Pass neither `-a` nor `-na`.
  - Saved trust follows the nearest ancestor, so one decision on the workspace parent
    covers every `sase_N` clone.
  - Headless runs skip untrusted project resources.
  - Add a per-project setting, `llm_provider.pi.project_trust: inherit | approve | deny`.
  - Never pass a blanket `--approve`: it loads executable project TypeScript. grk's
    "approve SASE-managed clones automatically" becomes an explicit per-project opt-in.
- **Hands off:** never pass `--tools`, `--no-tools`, or MCP or Codemode switches. Keep
  the user's `PI_CODING_AGENT_DIR`; an empty one would hide their login. Set
  `PI_SKIP_VERSION_CHECK=1`, and leave `PI_OFFLINE` and telemetry to the user.
- **Interactive `bypass_args: []`.** The hook means "skip this CLI's approval prompts",
  and pi has none. `--approve` is resource trust, not a permission bypass, so grk's
  `["--approve"]` is rejected.

### D12. Identity, install, doctor, and the interactive CLI

- **Identity:**
  - `llm_provider_name` and `llm_provider_short_name` are `"pi"`;
  - pick a status color distinct from the existing seven;
  - the menu key is `p`, which is free (`a`, `c`, `g`, `m`, `o`, `q`, and `x` are
    taken).
- **No `llm_autodetect_priority`.** Grok and Muse set the precedent, so gem's 22 and
  mus's 17–19 are rejected. `llm_autodetect_cli_name` returns `"pi"`.
- **Install metadata:**
  - `manager: "script"`, with `install_script_url: "https://pi.dev/install.sh"`. Muse is
    the precedent. The script pins transitive dependencies and can install Node, which
    matters because athena's Node is below the floor.
  - npm (`@earendil-works/pi-coding-agent`, `--ignore-scripts`) is the documented
    alternative.
  - Also set `self_update_argv: ["update"]`, `version_argv: ["--version"]`,
    `latest_version_package`, `display_name: "Pi"`, and `vendor: "Earendil"`.
- **Doctor:**
  - check a version floor of 1.3.0;
  - check identity with `pi --help`, because `pi --version` prints a bare semver that
    cannot tell Earendil's CLI from other `pi` binaries;
  - for npm installs, check Node ≥ 22.19;
  - add a deep check with `pi auth check --provider <p> --model <m> --json` for the
    model SASE will actually launch;
  - never use `--credentials` or any command that prints credentials.
- **Auth evidence:** `~/.pi/agent/auth.json` (or `$PI_CODING_AGENT_DIR/auth.json`) plus a
  few common key variables. This is advisory only.

### D13. Phase 2: the `sase_contract.ts` enforcement extension

Load it with `-e` in root invocations only. It has five parts:

- **`tool_call` guard.** Block `git commit` and `git push`, and `gh pr create` and
  `gh pr merge`, with a reason that names the sanctioned path. A handler failure also
  blocks. Treat this as guidance, not a security boundary: a regex misses indirect
  execution. Leave guarded-recipe refusal to the existing `just` guard rather than gem's
  `just check-full` regex.
- **`agent_before_settle` nudge.** Fire only when no `final_submission.json` newer than
  the run's start exists and no plan, monitor, pipe, or questions handoff is pending.
  Then return `continue: true` **once** with a reminder. Log it, and coordinate with the
  host's continuation budget so there are not two recovery loops (cdx).
- **`before_agent_start`.** Filter context exactly (D6), and check the effective thinking
  level (D8).
- **`session_start`.** Write the session file path to the artifacts directory.
- **Optional typed `sase_final` tool.** It must delegate to `sase final`, never
  reimplement it. gem's tool, which "executes finalization" itself, is rejected. Also,
  `terminate: true` ends the run only when **every** call in the batch terminates
  (`agent-loop.ts:691`). It is not a kill switch.

**Host-side root check.** Export `SASE_PI_ROOT_SESSION_ID=<uuid>`. Teach
`sase final context|defer|prepare|submit` to refuse when `PI_SESSION_ID` is set and
differs from it.

- Pi re-sets `PI_SESSION_ID` for every bash command, so a nested pi helper's commands
  carry its own id, even an in-memory one.
- This meets the reopen condition of `helpers-return-roots-declare` ("a provider exposing
  'this call came from a subagent' outside the hook payload"). It needs a new decision
  record, written through `/sase_memory_write`.
- Residual gap: a non-pi helper started from the root's bash, such as `claude -p`,
  inherits the root's id. Text coverage still applies there.

**Failure modes.** An extension that fails to **load** stops a headless run with exit 1,
so a missing or broken `-e` fails closed at startup. cdx's worry that load failures are
mere diagnostics does not hold at this revision. A handler that **throws at runtime** is
logged and the run continues, except in `tool_call`, where a throw blocks the call. So a
filter or thinking-level check can fail silently, and the verify observer must catch it.
Certify the extension for JSON mode first. Do not claim it works with every pi package.

### D14. Exact instruction verification

Add an `instructions/pi.py` observer. It replays the session JSONL's system messages: the
first message carries all sections, and later ones carry section patches. Compaction
checkpoints carry `systemMessage`. The observer asserts two things:

- the bundle marker appears exactly once, in `addendum` or in the Phase 2 section;
- no SASE-owned path appears in `project_context`.

Wire pi into `_KNOWN_PROVIDERS`, a session finder that reads the artifacts session dir
(not cwd-grouped `~/.pi/agent/sessions`), `coverage_sessions.py`, `_verify_observers.py`,
and `_verify_aggregate.py`. Pi then becomes the first JSONL-CLI provider whose delivery is
verified from the session record itself rather than inferred.

## 7. Touchpoint checklist

**R** means required for a working provider; **R\*** means required for in-tree CI.

| # | Touchpoint | Req |
|---|---|---|
| 1 | `pyproject.toml`: `pi = "sase.llm_provider.pi:PiProvider"` | R |
| 2 | `pi.py`: hooks, argv, `SASE_PI_PATH`, `SASE_PI_{LARGE,SMALL}_ARGS`, invoke loop with continuation, missing-binary error | R |
| 3 | `_subprocess_pi.py` (+ `_subprocess.py` re-export): pure normalizer, D5 table, live reply, thinking sink, usage, `run_metadata`, settle watchdog | R |
| 4 | `_tool_call_pi.py` (+ `_tool_calls.py`): `tool_execution_*` → `tool_calls.jsonl` (`runtime: "pi"`) | R |
| 5 | `models.yml` `providers.pi`; regenerate model docs with `just fix` | R |
| 6 | `model_policy._PROVIDER_SUPPORTED_EFFORTS` | R\* |
| 7 | `CHANNEL_PI_ROOT`; `directives.py` registration | R |
| 8 | `instructions/pi.py` observer + run index / coverage / aggregate wiring | R |
| 9 | Skill deploy subpath, template context and no-ask branch, chezmoi `dot_pi/agent/skills` | R |
| 10 | Doctor: identity, version floor, Node floor, `pi auth check` | R |
| 11 | Palette, badge, `AGENT_PROVIDER_VALUES`, interactive metadata | R\* |
| 12 | `default_config.yml`: `llm_provider.pi.{extensions,project_trust}` plus provider comments (see the `gotchas` core memory) | R |
| 13 | Docs: `docs/reference/providers/pi.md`, index and agent-clis tables, `plugin-api.md`, `instruction-bundles` delivery table, env vars, `mkdocs.yml`. Read `docs_writing` first | R |
| 14 | Tests and fixtures (§8) | R\* |
| 15 | Phase 2: `pi_extension/sase_contract.ts` as wheel data; `sase final` root check; decision record | Phase 2 |

## 8. Tests and acceptance

**Fixtures.** Store recorded `--mode json` streams under
`tests/fixtures/pi_stream/<pi-version>/`. Cover:

- a reply with no tools, and a reply that uses tools;
- a provider error (exit 0);
- truncation;
- abort;
- auto-retry, both success and failure;
- compaction;
- missing settle and EOF;
- `deferred`;
- UTF-8 split across reads, and U+2028 inside strings.

pi-ai ships a scriptable `faux` provider. A fixture-only extension that registers it
could let the real CLI emit deterministic streams with no API key. This is plausible but
unverified; check it in Phase 0.

**Unit tests:**

- the normalizer as a pure function, and the D5 table;
- argv construction, for both explicit and legacy delivery:
  - `-nc` appears only in SASE-managed projects;
  - argv never contains `--session`;
  - the user's pi files are re-added;
- the effort map and the clamp warning;
- in-invocation same-id continuation, and cross-workspace `--fork`;
- usage counted once, with no doubled final text.

**Repo-wide tests to update:**

- `_MANIFEST_PROVIDERS`;
- the effort mirror;
- menu-key uniqueness;
- palette and badge;
- skill target paths.

Keep a small opt-in real-model matrix that covers at least two backends and one local or
custom route, so the adapter does not quietly become "Anthropic through pi."

**Phase 1 acceptance:**

1. A pi user with an untouched `~/.pi` runs `%m:pi-default`, and the host finalizer
   lands the result.
2. `sase instructions verify` shows the marker exactly once and no SASE-owned native
   file.
3. Auth failure, 429, overload, truncation, and abort each surface as readable failures
   and retry where configured. None counts as success.
4. A run that retries or compacts and then succeeds counts as success. Nothing finalizes
   early on `agent_end`.
5. Monitor, plan, and questions handoffs leave no orphaned pi child.
6. The LLM Calls panel shows pi tool calls.
7. `just check` is green.

## 9. Risks

| Risk | Mitigation |
|---|---|
| Pi churn (8 releases in 15 days; 2 with breaking sections) | Doctor floor; version-named fixtures; tolerant normalizer that ignores unknown events; a scheduled pi-contract lane |
| JSON mode exits 0 on model failure or missing credentials | D5 table; a missing `agent_settled` counts as failure |
| Cross-workspace reopen runs tools in the old clone | `--fork` only; a test that argv never contains `--session` |
| `-nc` or the append flag drops the user's pi files | Re-add them (D6); exact filtering in Phase 2 |
| A missing bundle path becomes literal prompt text | Assert the file exists before exec |
| Silent effort clamp | Record the effective level; warn in v1, fail before model work in Phase 2 |
| Provider-wide disable over a multi-vendor harness; shared subscriptions | No auto-disable in v1; backend-scoped identity in sase-core later |
| User extensions add background work, subagents, or commits | `extensions: none` option; raw-commit absorption; settle nudge; root check |
| Node floor (athena 22.14 < 22.19) | Script installer; doctor check |
| Node lingers after settle | Settle watchdog |
| Underscore skill-name warnings | Filter them; watch upstream |
| A bundle of about 5–6k tokens is now visible in pi's context meter | Expected; fold into bundle-diet work and pi-style paired evals, but do not gate on it |

## 10. Where the researchers disagreed, and how it was resolved

| Topic | Positions | Resolution | Deciding evidence |
|---|---|---|---|
| Instruction delivery | mus: native `AGENTS.md`; the other four: explicit | **Explicit** | Workspace and home `AGENTS.md` both carry the contract |
| Suppression mechanism | cld, grk, gem: `-nc`; cdx: extension filter from day one | `-nc` in SASE-managed projects for v1; extension filter in Phase 2 | Codex precedent (`codex.py:300`); extension handler errors are not fatal |
| Prompt transport | cdx, cld: stdin; grk: `@file`; gem: argv | **stdin** | `file-processor.ts` wraps `@file`; `initial-message.ts` reads stdin |
| Continuation | prior report and gem: `--session <path>`; grk: same id; cld: `--fork`; cdx: fresh by default | Same id within an invocation; `--fork` across workspaces; fresh for successors | `session-manager.ts:1782,1874`; `main.ts:401` |
| Code location | cdx: Rust reducer; others: Python | **Python v1** | No provider parsing in sase-core; frontends read artifacts |
| Sunset flag | grk: yes; cld: no | **No** (`beta` only as epic scaffolding) | `sase_flags`; flags are checked inside adapters |
| Tier defaults | gem: stale Claude 3.x; grk, mus: curated concrete; cld: sentinel | `pi-default` sentinel + curated aliases | The manifest requires every tier to be in the catalog; credentials vary |
| Effort | 4 reports: 1:1 map; cdx: clamp breaks the contract | Map 1:1 and handle the clamp explicitly | `agent-session.ts:2638`; `_effort_args.py` |
| Autodetect | gem: 22; mus: 17–19; cdx, grk: omit | **Omit** | Grok and Muse precedent |
| Usage-limit patterns | gem: ship them; cdx, cld: off | **Off** | `provider_disable.rs` keyed by provider; shared subscriptions |
| Token accounting | gem: accumulate `message_update`; others: `message_end` | `message_end`, once per message | `json.md`: update usage is cumulative |
| Interactive bypass | grk: `--approve`; others: `[]` | **`[]`** | The hook means approval prompts, and pi has none |
| Extension load failure | cdx: diagnostic only; cld: exit 1 | **Exit 1**; runtime handler errors are not fatal | `main.ts:917–925`; runner `onError` |
| JSON-mode dialogs | mus: they wait; cld: they resolve | They resolve in JSON mode; RPC waits | `noOpUIContext` |
| `terminate: true` | gem, mus: ends the run; cdx: only if the whole batch agrees | Whole batch | `agent-loop.ts:691` |
| `.agents/skills` deploy | mus: add; cld: no; grk: later | **No** | Other CLIs read it |
| Install manager | grk, gem: npm; cld: script | Script (npm alternative) | Athena's Node is below the floor |
| Trust | grk: auto-approve SASE clones; cld: inherit; cdx, mus: per-project | Inherit + per-project config | `-a` loads executable TypeScript |

gem's report adds no unique correct design point. Its code sketches are useful as shape
only: its usage accumulation double-counts, its model list is stale, and its autodetect
priority and quota patterns conflict with established precedent.

## 11. Sources

**pi** (`d2e7d8b7c`, opened with `sase repo open gh:earendil-works/pi`):

- `packages/coding-agent/`:
  - `README.md`, `package.json`, `CHANGELOG.md`;
  - `docs/{cli,cli-integration,json,rpc,message-types,session-format,sessions,configuration,security,skills,extensions,providers}.md`;
  - `src/{main.ts, cli/{args,initial-message,file-processor}.ts, modes/print-mode.ts}`;
  - `src/core/{resource-loader,system-prompt,session-manager,agent-session,skills}.ts`;
  - `src/core/extensions/{types,runner,loader}.ts`, `src/core/tools/bash.ts`.
- `packages/agent/src/agent-loop.ts`.
- `packages/ai/src/auth/oauth/`, `packages/ai/src/providers/faux.ts`,
  `packages/ai/CHANGELOG.md`.

**SASE** (`4b7b981532`):

- `pyproject.toml`.
- `src/sase/llm_provider/`:
  - `{_hookspec,base,instruction_delivery,_instruction_boundary,_claude_instruction_delivery}.py`;
  - `{claude,codex,grok,muse_provider,opencode}.py`;
  - `{_wait_guard,_effort_args,model_manifest,model_policy}.py`, `models.yml`.
- `src/sase/feature_flags/registry.py`, `src/sase/instructions/{run_index,directives}.py`,
  `src/sase/agent_clis/{install,models}.py`.
- The project and home `AGENTS.md` (contract headings and ancestors on athena).

**sase-core** (`753fa21a`): `crates/sase_core/src/{provider_disable.rs, retryability/,
provider_usage/}` and the module list.

**Memory:**

- `decisions:{instructions-per-invocation, readable-agents-md, rust-core-required,
  helpers-return-roots-declare, adapters-normalize-harnesses}`;
- `sase_flags.md`.

**Research:**

- `202610/sase_for_pi_users/sase_for_pi_users__final.md`;
- the five researcher reports in this directory.

## 12. Recommended solution

**Build a first-class, in-tree `pi` provider as one epic in three phases, with live
control as a separate later epic.** The provider:

- runs `pi --mode json` once per SASE invocation, in the claimed workspace, with the
  prompt on stdin;
- lets the event stream, not the exit code, decide each outcome (D5);
- delivers the instruction bundle explicitly through `--append-system-prompt`, with
  `-nc` in SASE-managed projects and the user's own pi files re-added (D6);
- keeps a fresh session file per invocation under the agent's artifacts. It reopens the
  same id only within an invocation, uses `--fork` across workspaces, and never uses
  `--session` (D7);
- preserves the user's pi: default model through a `pi-default` tier, plus their
  extensions, MCP, Codemode, tools, and trust;
- stays out of autodetect, size aliases, and quota auto-disable until evidence exists.

sase-core needs no change for Phases 0–2.

### Reference invocation

```text
PI_SKIP_VERSION_CHECK=1 SASE_PI_ROOT_SESSION_ID=<uuid> \
pi --mode json \
   --session-dir "$SASE_ARTIFACTS_DIR/pi/sessions" \
   --session-id <uuid>                    # fresh per invocation; reused for in-invocation continuations
   [--fork <abs predecessor .jsonl>]      # cross-workspace continuation only (with a new --session-id)
   --name "<sase agent name>" \
   [--model <provider/id>]                # omitted for pi-default
   [--thinking <off|minimal|low|medium|high|xhigh|max>] \
   --append-system-prompt <materialized bundle> \
   [-nc]                                  # SASE-managed projects only (Phase 1)
   [--append-system-prompt <agent-dir AGENTS.md>]       # when -nc is set
   [--append-system-prompt <agent-dir APPEND_SYSTEM.md>] \
   [-e <sase>/llm_provider/pi_extension/sase_contract.ts]   # Phase 2
   [-ne]                                  # only when llm_provider.pi.extensions = none
   [$SASE_LLM_*_ARGS | $SASE_PI_*_ARGS] \
   < prompt on stdin
```

The legacy fallback, used when materialization fails, drops `-nc` and the bundle and
passes `--append-system-prompt "<pi single-turn directive>"` instead.

### Phases

**Phase 0: live spike (S, about half a day).**

- Install pi on athena with the script installer. That is a global CLI install, so
  Bryan runs it or approves it through a gate.
- Capture fixtures from a cheap real model and, if it works, the faux provider.
- Confirm the remaining source-only claims:
  - exit 0 on error, and the stderr shape;
  - the skill warnings;
  - `--fork` cwd behavior, and same-id reopen;
  - the session system sections under `-nc` plus the append flag;
  - whether a process lingers after settle;
  - whether `thinking_level_change` lands before the first request;
  - whether a `before_agent_start` filter shows up in the first persisted system
    message.
- Output: version-named fixtures and a short "verified / changed" note attached to this
  research.

**Phase 1: core provider (M–L).**

- Touchpoints 1–14.
- Explicit delivery with the user's files preserved.
- The D5 outcome table and the settle watchdog.
- Usage, cost, and the physical model recorded in `run_metadata.json`.
- Stranded-wait continuation on the same session.
- Doctor, `sase agent-cli install pi`, and tmux-agent `p`.
- Docs.
- Must meet the §8 acceptance list.

**Phase 2: enforcement and exact delivery (M).**

- `sase_contract.ts`:
  - the commit/PR guard;
  - the bounded settle nudge;
  - exact SASE-owned context filtering, which replaces `-nc`;
  - the explicit-effort check;
  - session recording.
- The `PI_SESSION_ID` root check in `sase final`, with a new decision record that amends
  `helpers-return-roots-declare` for pi.
- `llm_provider.pi.project_trust`.

**Later, separate epics:**

- RPC transport behind the same normalizer for steer, follow-up, and abort, after a
  decision record on in-turn steering;
- native pi→pi `#fork`/`#resume`;
- a cost field and rollups in sase-core;
- a backend-scoped quota identity and disable in sase-core;
- size-alias membership after usage data exists;
- an optional pi-gallery bridge package and a pi-user on-ramp.

### Not recommended

- An SDK or Node bridge; Pi Durable; a pi process kept alive across turns.
- Print mode.
- An out-of-tree plugin as the "fully supported" form.
- Native `AGENTS.md` delivery.
- `--session` for any continuation.
- argv or `@file` prompts.
- Overriding the user's tools, Codemode, MCP, extensions, or trust by default.
- Usage-limit auto-disable for pi in v1.
- A sunset flag for explicit delivery.
- A static catalog of pi's 30+ backends.

### Decisions for Bryan

1. **Default tier.** The recommended `pi-default` sentinel lets pi pick the user's
   default model. Concrete SASE-chosen tiers are the alternative.
2. **User extensions in SASE runs.** Inherit them (recommended), or load none by
   default?
3. **First backend.** Which backend do you plan to route through pi first: a
   subscription you already use through `claude`, `codex`, `grok`, or `muse`, or an API
   key? A shared subscription makes the quota overlap in D9 a day-one concern rather
   than a later one.
4. **OpenCode's future.** Pi now covers OpenCode's niche as SASE's multi-vendor harness,
   and `readable-agents-md` notes that Qwen and OpenCode lack real usage. Should a later
   decision consider retiring OpenCode once pi has usage data?
