---
create_time: 2026-08-12
updated_time: 2026-08-12
status: research
---

# Adding a Grok LLM Provider to SASE

**Question.** What would it take to add a Grok-backed LLM provider to SASE? There are
two things called a "grok CLI" — which one should SASE integrate, and how does it map
onto SASE's provider contract?

**Scope.** SASE facts verified against `sase@bb60a0bd1` (2026-08-12) and
`sase-core@origin/master` as of the same day. Grok facts verified against the shipped
Linux x86-64 binary of **`@xai-official/grok` 1.0.3**, installed into an isolated npm
prefix and run under an isolated `HOME`/`XDG_*` root.

**Evidence status.** Every Grok CLI claim below was produced by running the binary
(`--help`, `help <subcommand>`, `inspect --json`, `models`, argument-parse probes) or by
reading the vendor documentation and Rust source that ship inside it, cross-checked
against the public source mirror `xai-org/grok-build` (`SOURCE_REV`
`5d08d7e4123092567ccd584cd9f99afa2972065c`). Binary SHA-256:
`2a7d46dea3fbed067e4072258b835d401e017d6848dc996279f0fb3d668a0961`.

Claims that require an authenticated xAI account are quarantined in §8 and appear
nowhere else. Nothing in the recommendation depends on them.

**Freshness warning.** Grok Build reached `1.0.0` on **2026-08-07** — five days before
this note — and shipped `1.0.1`, `1.0.2`, and `1.0.3` in the five days since. Treat
every flag and schema below as a dated snapshot of `1.0.3`, not a stable contract.

---

## 1. Executive summary

Yes, there is a `grok-cli` — but it is almost certainly not the one to build on. The
name now points at two different tools, and the community one that popularized it
(`superagent-ai/grok-cli`) has been renamed `grok-dev`, has not shipped since
2026-05-15, and emits a bespoke event stream. xAI's own **Grok Build** (`grok`,
`@xai-official/grok`) is the real integration target.

Grok Build is the best-fitting provider candidate SASE has evaluated. It has a
first-class headless mode, native `AGENTS.md` support, explicit model / effort /
permission / cwd / session flags, and a skills root that lands on SASE's *default*
deploy path with no hook at all.

The load-bearing finding is §3.4: Grok Build ships an output format,
`--output-format streaming-messages-json`, that is **deliberately wire-compatible with
Claude Code's `stream-json`**, down to the four token-usage field names SASE already
accumulates. SASE's existing Claude stream parser and Claude tool-call normalizer can be
reused essentially verbatim. Every other provider SASE has added (Codex, Qwen, OpenCode,
Muse) needed a bespoke `_subprocess_*.py` **and** a bespoke `_tool_call_*.py`. Grok needs
neither.

That collapses the work from "two new parsers plus a provider" to "one new provider
module plus a ~5-line error-detail improvement in shared code." No new hooks. No Rust
core changes (§4.5). No new agent-instruction shim file.

**Recommendation (full detail in §7): build a native, in-tree `grok` provider driven by
`--output-format streaming-messages-json`, reusing the Claude parsers, registered
explicit-only with no autodetect priority.** Ship it in three stages.

---

## 2. Which "grok CLI"? Three candidates

| | **Grok Build** (recommended) | **grok-dev** (ex-`grok-cli`) | **Point OpenCode at xAI** |
|---|---|---|---|
| Identity | xAI's own terminal coding agent | Community agent by superagent-ai | No new provider; existing OpenCode provider + xAI model |
| Binary | `grok` | `grok` (**same name**) | `opencode` |
| Package | `@xai-official/grok` 1.0.3 | `grok-dev` 1.1.7 (was `@vibe-kit/grok-cli`) | n/a |
| Published by | `security@x.ai` | community | n/a |
| License | Apache-2.0 (wrapper + platform binaries) | MIT | n/a |
| Last release | **2026-08-12** (today) | **2026-05-15** (3 months stale) | n/a |
| Source | `xai-org/grok-build`, Rust, synced from monorepo since 2026-07-16 | `superagent-ai/grok-cli`, Bun + OpenTUI | n/a |
| Headless | `-p/--single`, 4 output formats | `--prompt/-p`, `--format json` | already supported |
| Machine output | ACP-native NDJSON **and Claude-compatible NDJSON** | bespoke `step_start`/`text`/`tool_use`/`step_finish`/`error` | OpenCode's own |
| Auth | subscription (SuperGrok / X Premium+) **or** `XAI_API_KEY` | `XAI_API_KEY` only (per-token billing) | any OpenCode credential |
| Harness features | plan mode, subagents, worktrees, skills, hooks, plugins, MCP, LSP, memory, sandbox | sub-agents, MCP, hooks, schedules, Telegram | OpenCode's |

**Why not `grok-dev`.** It is the tool most people mean by "grok-cli," and it is real and
MIT-licensed — but the repo's last commit is 2026-05-15, ten days before xAI shipped its
own CLI, and the npm package has not moved since. Its `--format json` stream is a
bespoke shape that would need a full `_subprocess_grokdev.py` + `_tool_call_grokdev.py`
pair, i.e. *more* work than the official CLI for a *less* maintained target. It also
uses `XAI_API_KEY` exclusively, so every run bills per token rather than drawing on a
subscription.

**Why not "just use OpenCode with an xAI model".** This is the cheapest option and it is
genuinely worth doing as a smoke test — it costs nothing and tests whether the *model*
is useful to Bryan before any code is written. But it integrates none of the harness.
Grok Build ships plan mode, subagents with worktree integration, its own skills and
hooks systems, and a session store; a SASE `grok` provider that routes through OpenCode
gets the model and discards all of it. Same argument the Muse research made, and it
holds here.

**Why Grok Build.** It is vendor-maintained, actively released, source-available under
Apache-2.0, drives a subscription Bryan may already have, and — decisively — it went out
of its way to be consumable by tools built for Claude Code.

---

## 3. What Grok Build actually exposes

### 3.1 Install, update, versioning

Two install paths, both verified:

```bash
npm install -g @xai-official/grok        # bin: grok
curl -fsSL https://x.ai/cli/install.sh | bash
```

The npm package is a 17 KB Node trampoline (`bin/grok`) plus per-platform optional
dependencies (`@xai-official/grok-{linux,darwin,win32}-{x64,arm64}`) carrying a
brotli-compressed Rust binary. On first run the trampoline decompresses to
`$GROK_HOME/bin/grok-<version>` (default `~/.grok/bin/`, 166 MB uncompressed) and
symlinks `grok` to it. This matters for SASE's `agent-cli` inventory: the *installed
version* lives under `~/.grok/bin`, not under `node_modules`.

`grok --version` prints `grok 1.0.3 (1a29d5bc12)`. SASE's default semver scan in
`agent_clis/detect.py::_parse_version` extracts `1.0.3` correctly — **no `version_regex`
is needed** (unlike Muse, which required one).

Self-update is `grok update` (with `--check`, `--json`, `--version <V>`, `--alpha`,
`--stable`). Because npm is also a valid channel, SASE can use either `manager: "npm"`
with `latest_version_package: "@xai-official/grok"` (giving it the same
already-implemented update path as Claude/Codex/Qwen) or `self_update_argv: ["update"]`.
npm is the better default — it keeps the CLI on SASE's existing npm update rail.

Release velocity, from the npm registry: 550 published versions, `0.1.0` on 2025-10-22,
`0.2.0` on 2026-05-26, **`1.0.0` on 2026-08-07**, `1.0.3` on 2026-08-12. Weekly stable
channel with a faster alpha channel.

### 3.2 Authentication

- `grok login` (browser OAuth) or `grok login --device-code` (headless hosts). Token
  cached in `~/.grok/auth.json`.
- **or** `XAI_API_KEY` in the environment.
- Auth failure is clean and machine-readable — the unauthenticated probe exits `1`,
  writes a human message to stderr, and still emits a well-formed terminal `result`
  line to stdout (§3.4).

OAuth draws on a SuperGrok / X Premium+ subscription (no per-token billing);
`XAI_API_KEY` bills through the xAI API.

### 3.3 The headless surface

Headless is triggered by `-p/--single <PROMPT>`, `--prompt-file <PATH>`, or
`--prompt-json <JSON>`. Verified flags relevant to SASE:

| Flag | Notes |
|---|---|
| `-p, --single <PROMPT>` | prompt as an argv value |
| `--prompt-file <PATH>` | **`/dev/stdin` works** — verified to parse |
| `-m, --model <MODEL>` | model id |
| `--reasoning-effort` / `--effort <LEVEL>` | canonical `none\|minimal\|low\|medium\|high\|xhigh\|max` |
| `--output-format <FMT>` | `plain\|json\|streaming-json\|streaming-messages-json` |
| `--permission-mode <MODE>` | `default\|acceptEdits\|auto\|dontAsk\|bypassPermissions\|plan` |
| `--yolo` | auto-approve; **accepted but absent from `--help`** — prefer `--permission-mode bypassPermissions` |
| `--always-approve` | documented equivalent of `--yolo`, listed in `--help` |
| `--cwd <PATH>` | working directory |
| `-s, --session-id <UUID>` | new session with a caller-chosen UUID (errors if it exists) |
| `-r, --resume`, `-c, --continue`, `--fork-session` | session resume |
| `--max-turns <N>` | headless-only turn cap |
| `--tools` / `--disallowed-tools` | allow/deny built-in tools by internal id (`run_terminal_cmd`, `read_file`, …); `Agent(...)` entries gate subagents |
| `--allow` / `--deny <RULE>` | `Bash(...)`, `Edit(...)`, `Read(...)`, `WebFetch(...)`, `MCPTool(...)` glob rules |
| `--sandbox <PROFILE>` | filesystem/network sandbox (`GROK_SANDBOX`) |
| `--rules <TEXT>` / `--system-prompt-override <TEXT>` | prompt shaping |
| `--no-auto-update` | suppress background update checks (also `GROK_DISABLE_AUTOUPDATER`) |
| `--no-plan`, `--no-subagents`, `--no-memory`, `--disable-web-search` | feature toggles |
| `--json-schema <SCHEMA>` | constrain output to a JSON Schema; implies `--output-format json` |

Verified argument-parse probe (the exact shape a SASE provider would emit):

```bash
grok -p "<prompt>" --output-format streaming-messages-json \
     --permission-mode bypassPermissions --no-auto-update \
     --effort high -m grok-4.5 --max-turns 5
```

parses cleanly (it fails only at authentication), while a bogus flag is rejected with
`error: unexpected argument`.

Also present: `grok agent stdio` (ACP over JSON-RPC), `grok agent serve` (WebSocket),
`grok mcp`, `grok plugin`, `grok sessions`, `grok export`, `grok worktree`,
`grok memory`, `grok inspect --json`.

One concurrency note: `grok` supports a shared "leader" backend process at
`~/.grok/leader.sock`, which would be a hazard for SASE's many-agents-at-once model. It
is **off by default** (`[cli] use_leader = true` opts in); `--no-leader` forces a fresh
agent. Leave it off and this is a non-issue.

### 3.4 Output formats — the load-bearing finding

Four formats. Two matter.

**`streaming-json`** is xAI's native shape, derived from ACP session updates:

```json
{"type":"thought","data":"Analyzing the directory structure..."}
{"type":"tool_call","toolCallId":"call_1","title":"Read","kind":"read","status":"in_progress","toolName":"read_file","rawInput":{"path":"src/main.rs"},"content":[],"locations":[]}
{"type":"tool_call_update","toolCallId":"call_1","status":"completed","rawOutput":{"lines":42}}
{"type":"text","data":"Here's a summary"}
{"type":"end","stopReason":"end_turn","sessionId":"abc123","usage":{...},"num_turns":7,"modelUsage":{...}}
```

Clean, but it would require a new parser.

**`streaming-messages-json`** is the interesting one. From the CLI's own documentation:

> Newline-delimited JSON in the Messages API `stream-json` wire format. The data-bearing
> surface matches the Messages shape exactly. […] **A consumer that reconstructs
> messages, reads spend, or detects errors works without changes.**

It emits a `system`/`init` line, `assistant` messages whose `message.content[]` carries
`text` / `thinking` / `tool_use` blocks, `user` messages carrying `tool_result` blocks,
and a terminal `result` line. `--include-partial-messages` adds `stream_event` deltas.

That is, line for line, the shape `sase/llm_provider/_subprocess_claude.py` already
parses. Concretely:

| SASE Claude parser expects | Grok `streaming-messages-json` emits | Match |
|---|---|---|
| `type == "assistant"` → `message.content[].text` | same | ✅ |
| `type in ("error", "result")` for diagnostics | `result` with `subtype`, `is_error`, `errors[]` | ⚠️ see below |
| `result.usage.input_tokens` | `input_tokens` | ✅ |
| `result.usage.output_tokens` | `output_tokens` | ✅ |
| `result.usage.cache_read_input_tokens` | `cache_read_input_tokens` | ✅ |
| `result.usage.cache_creation_input_tokens` | `cache_creation_input_tokens` | ✅ |
| tool calls: `assistant` → `tool_use` blocks | same | ✅ |
| tool results: `user` → `tool_result` blocks | same | ✅ |
| optional top-level `tool_use_result` envelope | absent (read with `.get()`, degrades cleanly) | ✅ |

Those four usage keys are exactly `initial_usage_totals()`. Confirmed independently in
the public source at
`crates/codegen/xai-grok-pager/src/headless/reducer/messages/wire.rs`, which serializes
`MessageUsage { input_tokens, output_tokens, cache_read_input_tokens,
cache_creation_input_tokens }` and a `ResultLine { subtype, is_error, num_turns, result,
stop_reason, total_cost_usd, usage, modelUsage, errors, session_id, uuid }`.

**The one real gap.** `_subprocess_claude.py::_process_json_line` extracts a failure
detail with `event.get("error") or event.get("message") or event.get("result", "")`.
Grok puts failure text in **`errors[]`** (plural, a list) and omits `result` on failure.
Measured against the unauthenticated run: exit code `1`, stderr carries
`Error: Not signed in…`, and the JSON `errors[]` array carries the same text — but SASE
would capture an empty detail from the JSON and rely on stderr alone. This is a ~5-line
fix in shared code (append `errors[]` when present), and it is the *only* parser change
required. Note that `append_error_events` is gated on a non-zero return code, so Grok's
success-path `result.result` (final text) is never mistaken for an error.

**Honest caveat about fidelity.** Grok's own docs warn that the `system`/`init` and
terminal `result` lines "may not pass strict `init`/`result` schema validation" because
Grok omits placeholder fields it cannot fill (`claude_code_version`, `output_style`,
`plugins`, `permission_denials`) rather than zero-filling them. SASE ignores `system`
entirely and reads only `usage` and diagnostics off `result`, so this does not bite —
but a future SASE feature that reads `init` fields would need to tolerate absences.

### 3.5 Models and reasoning effort

`grok models` works unauthenticated and reports the bundled default catalog:

```
Default model: grok-4.5
Available models:
  * grok-4.5 (default)
```

The bundled `default_models.json` embedded in the binary contains exactly one model,
`grok-4.5` ("SpaceXAI's new frontier model", 500 000-token context, `responses` API
backend, `supports_reasoning_effort: true`, default effort `high`, advertised efforts
**high / medium / low only**). The real catalog is server-driven
(`GROK_MODELS_LIST_URL`, `GROK_MODELS_BASE_URL`), so an authenticated account will very
likely see more — the vendor headless docs use `grok-build` as their `-m` example, which
is not in the offline catalog. See §8.

**Effort maps 1:1.** Grok's canonical levels are `none`, `minimal`, `low`, `medium`,
`high`, `xhigh`, `max` — byte-identical to SASE's canonical set. No translation table is
needed, unlike Muse (`max` → `ultra`). The wrinkle: "a model only accepts the levels its
menu advertises," and `grok-4.5` advertises only low/medium/high. Two defensible
choices:

- **Pass through all seven** and let Grok reject per-model. Honest about the canonical
  surface; a `%effort:xhigh` against `grok-4.5` fails at the CLI rather than in SASE.
- **Declare only low/medium/high.** SASE raises early with a clear message, but blocks
  levels a future model may accept.

Recommended: pass through all seven (§7), because SASE's `effort_cli_args` contract is
about *what the provider CLI understands*, and Grok understands all seven.

### 3.6 Config, instruction files, and skills

Verified by `grok inspect --json` run inside this workspace:

- **Instruction files.** `AGENTS.md` is native, with a documented precedence of
  `~/.grok/AGENTS.md` → `<repo-root>/AGENTS.md` → `<cwd>/AGENTS.md`. **No `GROK.md`
  shim is needed** — SASE's generated `AGENTS.md` is read directly.
- **Skills.** `~/.grok/skills/`, `<repo-root>/.grok/skills/`, `./.grok/skills/`.
  SASE's `skill_deploy_subpaths()` defaults to `.<provider>` when no hook is declared,
  so a provider named `grok` gets `.grok` for free — **no
  `llm_skill_deploy_subpath` hook needed** (Qwen, OpenCode, Antigravity, and Muse all
  needed one).
- **Config.** `~/.grok/config.toml`, plus `~/.grok/{sessions,memory,hooks,plugins,agents,workflows,logs}`,
  `~/.grok/lsp.json`, `~/.grok/sandbox.toml`, `~/.grok/trusted_folders.toml`.
- **Built-in subagents:** `general-purpose`, `explore`, `plan`.
- **Claude/Cursor compatibility surfaces** — see §5.1, this is the notable one.

---

## 4. Mapping onto SASE's provider contract

### 4.1 Hook-by-hook

SASE registers providers as `sase_llm` entry points (`pyproject.toml`), each a pluggy
plugin implementing `LLMHookSpec`. Proposed values:

| Hook | Value | Notes |
|---|---|---|
| `llm_provider_name` | `"grok"` | |
| `llm_provider_short_name` | `"grk"` | free; existing are `cld`, `cdx`, `qwn`, `opc`, `agy`, `mus`, `fky` |
| `llm_resolve_model_name` | `large` → `grok-4.5`, `small` → `grok-4.5` | revisit `small` once the authenticated catalog is known (§8) |
| `llm_known_model_names` | `["grok-4.5"]` | grow from the authenticated catalog |
| `llm_model_short_aliases` | `{"grok-4.5": "grok45"}` | |
| `llm_skill_template_context` | `provider_name: "Grok"`, `provider_tool_name: "Grok Build"`, `provider_native_ask_tool: "ask_user_question"` | tool id seen in the binary as `x.ai/ask_user_question`; confirm in §8 |
| `llm_skill_deploy_subpath` | **omit** | default `.grok` is already correct |
| `llm_cli_status_color` | e.g. `#FFFFFF`/near-black xAI palette | ACE style; unknown providers fall back to neutral, so this is polish |
| `llm_autodetect_cli_name` | `"grok"` | enables doctor + `agent-cli` inventory |
| `llm_autodetect_priority` | **omit** | explicit-only — see §5.2 |
| `llm_auth_evidence` | `credential_paths: ["~/.grok/auth.json"]`, `api_key_env_vars: ["XAI_API_KEY"]` | |
| `llm_install_metadata` | `manager: "npm"`, `package: "@xai-official/grok"`, `scope: "global"`, `display_name: "Grok Build"`, `docs_url: "https://docs.x.ai/build/overview"`, `latest_version_package: "@xai-official/grok"` | no `version_regex`, no `version_argv` override |
| `llm_default_retry_config` | patterns for xAI transport/rate-limit wording | must not collide with Codex's `429`/`Too Many Requests` ownership |
| `llm_model_advisories` | probably none | no discounted-tier data-sharing terms found offline |

### 4.2 The invocation vector

```python
[
    _grok_bin(),                       # SASE_GROK_PATH or "grok"
    "-p", prompt,                      # or --prompt-file /dev/stdin
    "--output-format", "streaming-messages-json",
    "--permission-mode", "bypassPermissions",
    "--model", model,
    "--no-auto-update",
    "--session-id", str(uuid.uuid4()),
    *effort_args,                      # ["--effort", level]
]
```

**Prompt transport.** Unlike Claude (`-p` with the prompt on stdin), Grok's `-p` takes
an argv value. Two options: pass it as argv, or keep SASE's stdin habit with
`--prompt-file /dev/stdin` (verified to parse). Prefer `--prompt-file /dev/stdin` —
SASE prompts routinely exceed comfortable argv sizes, and it keeps `_run_subprocess`
identical to the Claude implementation.

**`--no-auto-update` is not optional.** Without it Grok may swap its own 166 MB binary
mid-run; SASE should own updates through `sase agent-cli`, exactly as it does for Muse
via `MUSE_NO_AUTO_UPDATE=1`.

**Session id.** SASE's Claude provider generates a UUID per cycle; Grok's `--session-id`
has the same "new session, must be a fresh UUID" semantics, so the pattern transfers
directly and gives resumable sessions under `~/.grok/sessions` for free.

### 4.3 Reused unchanged

- `_subprocess_claude.stream_and_parse_json_output` — the whole stream reader.
- `_tool_call_claude.append_claude_tool_call_event` — Tools-panel records from
  `assistant`/`user` frames; the optional `tool_use_result` envelope is read with
  `.get()` and its absence degrades cleanly.
- `_subprocess_artifacts` usage/live-reply artifact writers.
- `_subprocess_plain.start_interrupt_monitor` and the interrupt/continue loop.
- `_effort_args.effort_cli_args`.

### 4.4 Genuinely new code

1. `src/sase/llm_provider/grok.py` — the provider (~250–300 lines, closely modeled on
   `claude.py`, which is 348).
2. A ~5-line `errors[]` branch in `_subprocess_claude.py::_process_json_line`, guarded
   so Claude behavior is unchanged.
3. Entry point in `pyproject.toml`.
4. Tests plus recorded NDJSON fixtures (needs §8's authenticated capture).

### 4.5 No Rust core changes

Verified against `sase-core@origin/master`: `llm_provider` is carried as a plain
`String`/`Option<String>` throughout (`agent_group_archive`, `notifications::mobile`,
`sase_core_py`, `sase_gateway::routes`). The only `*Provider` enums in the tree are
`PushProviderMode` and `PushProviderWire` in `sase_gateway`, which are push-notification
providers, unrelated. This confirms the Muse research's finding and means the whole
change stays Python-side.

---

## 5. Risks and gotchas

### 5.1 Grok reads `CLAUDE.md` too — and SASE generates both files

`grok inspect --json`, run in this workspace, reports:

```json
"projectInstructions": [
  {"path": ".../CLAUDE.md", "scope": "project", "fileType": "agents_md", "approxTokens": 2829},
  {"path": ".../AGENTS.md", "scope": "project", "fileType": "agents_md", "approxTokens": 2829}
]
```

Both files, identical content (11 319 bytes each), both injected. SASE's `sase memory
init` generates `CLAUDE.md` as a provider shim of `AGENTS.md`, so **every Grok run in a
SASE repo pays ~2 800 duplicated instruction tokens** and gives the model the same rules
twice.

Worse, this is not configurable away. Grok's `[compat.claude]` block can disable the
`agents` cell, but its own documentation states that "generic top-level `Claude.md`,
`CLAUDE.md`, and `CLAUDE.local.md` stay recognized" regardless.

Options: accept the duplication (it is instruction text, cache-friendly, and only a few
thousand tokens); or have SASE not emit `CLAUDE.md` in repos where the configured
provider is `grok` — which is a memory-generation change with its own blast radius, and
breaks any human running `claude` in the same tree. **Recommendation: accept it for now,
measure it, and file a follow-up.** Flag it in `docs/agent_providers.md` so it is not
discovered as a mystery.

### 5.2 The `grok` binary name is contested

`grok-dev` (the community CLI) also installs a binary named `grok` **and also uses
`~/.grok/`**. If both are installed, whichever wins `PATH` gets launched. A SASE
autodetect that picks up a stale `grok-dev` would hand it Grok Build's flags, which it
would reject.

Precedent: SASE declines to autodetect `muse` "because `muse` is a generic executable
name." The same reasoning applies more strongly here, because the collision is concrete
rather than hypothetical. **Declare `llm_autodetect_cli_name: "grok"` (which is enough
for `sase doctor` and `sase agent-cli` inventory) but no `llm_autodetect_priority`.**
Select Grok explicitly via `llm_provider.provider: grok`, `%model:grok/<model>`, or
`SASE_GROK_PATH`.

For reference, current priorities: `claude=0`, `codex=10`, `qwen=15`, `opencode=18`,
`agy=30`, `fakey=1000`; `muse` has none.

### 5.3 Version velocity

`1.0.0` landed 2026-08-07 and three patches shipped within five days. The four
`--output-format` values, the `errors[]` field, and the `--yolo`/`--always-approve`
duplication are all `1.0.3` observations. Two mitigations: pin fixtures by version in
their filenames (the repo already does this — `muse_exec_read_tool_R708.1.jsonl`), and
keep `--no-auto-update` on so a run's CLI cannot change under it.

### 5.4 Undocumented and inconsistent flags

`--yolo` is accepted by the parser and documented in the embedded manual but is **not
in `--help`**. Prefer the `--help`-visible `--permission-mode bypassPermissions` or
`--always-approve`. Likewise `--no-auto-update` is documented and accepted but absent
from `--help`; verify it survives each upgrade.

### 5.5 Claude-compat cross-contamination

`[compat.claude]` defaults to **on** for `skills`, `rules`, `agents`, `mcps`, `hooks`,
and `sessions`. That means a Grok run will also pick up `~/.claude/skills/` and
`./.claude/skills/` — where SASE already deploys its generated skills for the Claude
provider. Grok would therefore see each SASE skill twice once `.grok/skills/` is also
populated (name collisions resolve by scope precedence, so this is duplication in the
listing rather than a hard failure). Also note `grok inspect` reports it consults
`/etc/claude-code/managed-settings.json` for managed policy.

Cleanest resolution: set `[compat.claude] skills = false` in the SASE-managed
`~/.grok/config.toml`, or simply verify the precedence rules dedupe acceptably. Worth an
explicit check during stage 2.

### 5.6 Subscription vs API key

OAuth uses a SuperGrok / X Premium+ subscription; `XAI_API_KEY` bills per token. SASE
launches many agents in parallel — the cost profile differs enormously between the two,
and subscription rate limits are undocumented. Decide the auth mode deliberately, and
note that `total_cost_usd` is only stamped on API-key traffic (per Grok's docs, "pool/OAuth
paths often omit it"), so SASE's cost accounting will be blank on subscription runs.

### 5.7 Satellite touchpoints

From the Muse precedent (7 commits, ~50 files), the non-provider edits are: badge in
`integrations/provider_badges.py`, palette in `ace/tui/provider_styles.py`, doctor hints
in `doctor/checks_providers.py`, the provider list comment in `default_config.yml`, and
docs across `docs/agent_providers.md`, `docs/configuration.md`, `docs/llms.md`,
`docs/cli.md`, `INSTALL.md`, `README.md`. Badge and palette are optional — unknown
providers already fall back to a neutral style and a `None` badge. Docs are not.

---

## 6. Alternatives considered

| Approach | Cost | Verdict |
|---|---|---|
| **A. Native `grok` provider on `streaming-messages-json`** | 1 module + ~5 shared lines + tests + docs | **Recommended.** Cheapest path to the full harness; reuses two parsers outright. |
| B. Native provider on `streaming-json` (ACP-native) | + a full `_subprocess_grok.py` and `_tool_call_grok.py` | Rejected. xAI's own docs call `streaming-messages-json` the compatibility surface. Reconsider only if the Messages projection proves lossy in practice — its `thought`/`plan`/`available_commands` events are genuinely richer. |
| C. Provider wrapping `grok-dev` | 2 bespoke parsers, unmaintained target, API-key-only billing | Rejected. Strictly more work for a strictly worse target. |
| D. Out-of-tree plugin package (`sase-grok`) | same code, separate release train | Viable — the `sase_llm` entry-point group supports third-party plugins. Rejected for now: every first-party provider is in-tree, and splitting one out adds release coordination for no benefit while the CLI is this young. |
| E. OpenCode pointed at an xAI model | ~zero | Not a substitute, but **do this first** as a cheap model-quality probe before writing any code. |
| F. `grok agent stdio` (ACP/JSON-RPC) | new transport layer in SASE | Rejected for this task. SASE's provider contract is subprocess-and-parse; ACP is the right shape for a future editor/daemon integration, not for `llm_invoke`. |

---

## 7. Recommendation

**Build a native, in-tree `grok` LLM provider that drives xAI's Grok Build CLI in
headless mode with `--output-format streaming-messages-json`, reusing SASE's existing
Claude stream and tool-call parsers, registered explicit-only with no autodetect
priority.**

Ship in three stages so nothing lands unverified.

### Stage 0 — decide, before writing code (hours)

1. Authenticate a Grok Build account (`grok login`, or set `XAI_API_KEY`) and settle the
   subscription-vs-API-key question from §5.6.
2. Run `grok models` authenticated to capture the real catalog (§8).
3. Capture three NDJSON traces under `--output-format streaming-messages-json` — a
   read-only run, a write+bash run, and a deliberate failure — as versioned fixtures
   (`grok_messages_read_1.0.3.jsonl`, etc.). These are the test corpus.
4. Optional but cheap: run the same prompt through the existing OpenCode provider
   against an xAI model to sanity-check that the *model* earns its place.

Stage 0 is the only genuine blocker, and it is small.

### Stage 1 — the provider (the bulk of the work)

1. `src/sase/llm_provider/grok.py` modeled on `claude.py`: `SASE_GROK_PATH` override,
   `SASE_LLM_{LARGE,SMALL}_ARGS` / `SASE_GROK_{LARGE,SMALL}_ARGS` passthrough, the
   interrupt/continue loop, and the invocation vector from §4.2.
2. Effort: pass through all seven canonical levels as `["--effort", level]` (§3.5).
3. `pyproject.toml`: `grok = "sase.llm_provider.grok:GrokProvider"` under
   `[project.entry-points."sase_llm"]`.
4. Extend `_subprocess_claude.py::_process_json_line` to fold `errors[]` into the
   diagnostic detail, with a Claude-path regression test proving no behavior change.
5. Doctor hints in `doctor/checks_providers.py`: install
   `npm install -g @xai-official/grok`, auth "run `grok login` (or `grok login
   --device-code`), or set `XAI_API_KEY`".
6. Tests against the Stage 0 fixtures: text extraction, the four usage keys, tool-call
   records, the error path, and the exact argv the provider builds.

Deliberately **not** implemented in Stage 1: `llm_skill_deploy_subpath` (default `.grok`
is correct), `version_regex` (default semver scan works), `llm_autodetect_priority`
(§5.2), and any Rust core change (§4.5).

### Stage 2 — integration polish

1. Badge and ACE palette.
2. `default_config.yml` provider-list comment.
3. Docs: a Grok Build section in `docs/agent_providers.md` (install, auth, update,
   explicit-only selection) plus the usual sweep of `docs/configuration.md`,
   `docs/llms.md`, `docs/cli.md`, `INSTALL.md`, `README.md`.
4. Verify skill deployment end to end: `sase init skills` → `~/.grok/skills/`, and
   confirm the `[compat.claude] skills` overlap from §5.5 is acceptable or disable it.
5. Document the `CLAUDE.md` + `AGENTS.md` double-load from §5.1 and file a follow-up
   task bead for it.

### Why this is the right call

- It is the **cheapest** viable option: the one format xAI built for Claude-Code
  consumers is the one SASE already parses. Every other route pays for two bespoke
  parsers.
- It is the **most complete**: SASE gets Grok Build's plan mode, subagents, worktrees,
  skills, hooks, MCP, and session store, not just the model.
- It is the **most maintainable**: vendor-published, weekly stable releases,
  Apache-2.0 source available for exactly the schema questions that matter.
- Its **risks are known and bounded**: version velocity (mitigated by pinned fixtures
  and `--no-auto-update`), a contested binary name (mitigated by explicit-only
  selection), and instruction duplication (measured at ~2 800 tokens, documented, and
  deferred).

The honest counter-argument is timing: `1.0.0` is five days old and the surface is
moving weekly. If that is unacceptable, the correct move is to wait a release cycle and
re-run §3 — not to build against `grok-dev`, which is not moving at all.

---

## 8. Open questions requiring an authenticated account

Nothing above depends on these; all are Stage 0 work.

1. **The real model catalog.** Offline the binary knows only `grok-4.5`. The vendor
   headless docs use `-m grok-build`, which is absent offline, so at least one
   server-side model exists that this note cannot name. Needed to fill
   `llm_known_model_names`, `llm_model_short_aliases`, and the `small` tier — until then
   `small` should alias `grok-4.5` rather than guess.
2. **Per-model effort menus.** `grok-4.5` advertises low/medium/high offline. Whether
   any model accepts `xhigh`/`max` is unverified.
3. **Real `streaming-messages-json` traces.** The schema in §3.4 comes from the vendor
   docs and the Rust `wire.rs` serializers; a successful authenticated run is needed to
   confirm the `assistant`/`user` framing and usage accumulation against live output,
   and to record fixtures.
4. **The ask-user tool id.** The binary contains `x.ai/ask_user_question`; whether that
   is the name SASE should put in `llm_skill_template_context.provider_native_ask_tool`
   needs one authenticated run to confirm.
5. **Rate limits and cost reporting on the subscription path.** Undocumented, and
   `total_cost_usd` appears to be omitted for OAuth traffic — material for SASE's
   parallel-agent workloads.
