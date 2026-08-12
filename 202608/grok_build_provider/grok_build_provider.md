---
create_time: 2026-08-12
updated_time: 2026-08-12
status: research
---

# Adding a Grok LLM Provider to SASE

**Question.** Is there a `grok-cli`, and what is the best way to add Grok support to
SASE?

**Answer.** Yes — but the name is ambiguous, and the one you probably mean is the wrong
target. Build a native, in-tree `grok` provider around **xAI's Grok Build**
(`@xai-official/grok`) in headless `--output-format streaming-messages-json` mode,
reusing SASE's existing Claude stream and tool-call parsers, registered explicit-only
with no autodetect priority.

This is a consolidation of two independent research passes (`__a`, `__b` in this
directory) plus a third verification pass by the lead. Where the two disagreed, the
disagreement was settled by running the shipped binary and reading the vendor's Rust
source; those adjudications are marked **[verified]** below.

**Scope.** SASE at `bb60a0bd1`; `sase-core@origin/master`; Grok Build **1.0.3**
(`grok 1.0.3 (1a29d5bc12)`, 166 MB Linux x86-64 binary) run under an isolated
`HOME`/`GROK_HOME`; vendor source mirror `xai-org/grok-build`. All three passes ran
2026-08-12.

**Freshness warning.** Grok Build hit `1.0.0` on **2026-08-07** — five days ago — and has
shipped `1.0.1`–`1.0.3` since. Treat every flag and schema below as a dated snapshot,
not a stable contract.

---

## 1. Which "grok CLI"?

Three candidates. Only one is a real target.

| | **Grok Build** (recommended) | **grok-dev** (ex-`grok-cli`) | **OpenCode → xAI** |
|---|---|---|---|
| Identity | xAI's own terminal coding agent | Community agent by superagent-ai | Existing SASE provider + xAI model |
| Binary | `grok` | `grok` (**same name**) | `opencode` |
| Package | `@xai-official/grok` **1.0.3** | `grok-dev` **1.1.7** | n/a |
| Last publish | **2026-08-12** (today) | **2026-05-15** (3 months stale) | n/a |
| License | Apache-2.0 | MIT | n/a |
| Machine output | ACP NDJSON **and Anthropic-Messages NDJSON** | bespoke `step_start`/`text`/`tool_use`/… | OpenCode's own |
| Auth | SuperGrok / X Premium+ subscription **or** `XAI_API_KEY` | `XAI_API_KEY` only | any OpenCode credential |

npm freshness **[verified]** by direct registry query: `grok-dev@1.1.7` modified
`2026-05-15T10:13:54Z`; `@xai-official/grok@1.0.3` modified `2026-08-12T08:33:22Z`.

**Why not `grok-dev`.** It is the tool that popularized the name "grok-cli," it is real
and MIT-licensed — and it has not moved since ten days before xAI shipped its own CLI.
Its bespoke `--format json` stream would need a full `_subprocess_grokdev.py` +
`_tool_call_grokdev.py` pair, i.e. *more* work than the official CLI for a *less*
maintained target, with API-key-only per-token billing.

**Why not "just point OpenCode at an xAI model".** Cheapest option and worth doing as a
model-quality smoke test before any code is written (`%model:opencode/xai/grok-4.5`).
But it integrates none of the harness: Grok Build ships plan mode, subagents with
worktree integration, skills, hooks, MCP, LSP, and a session store, and routing through
OpenCode gets the model and discards all of it. The run would also report as `opencode`
in SASE's identity, doctor, and inventory surfaces.

**Why Grok Build.** Vendor-maintained, weekly stable releases, Apache-2.0
source-available, drives a subscription you may already hold, and — decisively — it went
out of its way to be consumable by tools built for Claude Code.

**Naming caution.** Homebrew also ships a deprecated, unrelated `grok` regex utility.
Together with `grok-dev`, that makes three distinct tools competing for the same
executable name. This drives the explicit-only registration in §4.

---

## 2. The load-bearing finding: a Claude-compatible wire format

Grok Build's `--help` documents four output formats **[verified verbatim from the
binary]**:

```
--output-format <OUTPUT_FORMAT>
    Possible values:
    - plain
    - json
    - streaming-json:          NDJSON of the agent native ACP session updates
    - streaming-messages-json: NDJSON in the Anthropic Messages API wire format
```

`streaming-messages-json` emits a `system`/`init` line, `assistant` messages whose
`message.content[]` carries `text` / `thinking` / `tool_use` blocks, `user` messages
carrying `tool_result` blocks, and a terminal `result` line. That is, line for line, the
shape `sase/llm_provider/_subprocess_claude.py` already parses.

Verified against SASE source and live Grok output:

| SASE Claude parser expects | Grok emits | Status |
|---|---|---|
| `type == "assistant"` → `message.content[].text` | same | ✅ |
| `result.usage.input_tokens` | `input_tokens` | ✅ |
| `result.usage.output_tokens` | `output_tokens` | ✅ |
| `result.usage.cache_read_input_tokens` | `cache_read_input_tokens` | ✅ |
| `result.usage.cache_creation_input_tokens` | `cache_creation_input_tokens` | ✅ |
| tool calls: `assistant` → `tool_use` blocks | same | ✅ |
| tool results: `user` → `tool_result` blocks | same | ✅ |
| failure detail via `error`/`message`/`result` | **`errors[]`** | ⚠️ §2.1 |

Those four keys are *exactly* `initial_usage_totals()`
(`_subprocess_artifacts.py:133`), and `_process_json_line` accumulates them with
`for key in usage_totals: usage_totals[key] += usage.get(key, 0)` — so Grok's extra
nested `server_tool_use` key is simply ignored. **[verified]** against a live
`streaming-messages-json` frame and against `MessageUsage` in
`crates/codegen/xai-grok-pager/src/headless/reducer/messages/wire.rs`.

**Consequence:** SASE reuses `_subprocess_claude.stream_and_parse_json_output` and
`_tool_call_claude.append_claude_tool_call_event` essentially verbatim. Every other
provider SASE has added (Codex, Qwen, OpenCode, Muse, Agy) needed a bespoke
`_subprocess_*.py` **and** a bespoke `_tool_call_*.py`. Grok needs neither. That collapses
the work from "two new parsers plus a provider" to "one provider module plus a ~5-line
fix in shared code."

### 2.1 The one required parser change

`_subprocess_claude.py:109-111` extracts failure detail as:

```python
detail = event.get("error") or event.get("message") or event.get("result", "")
```

Grok's failure frame carries none of those keys. **[verified]** — the live
unauthenticated failure frame is:

```json
{"type":"result","subtype":"error_during_execution","is_error":true,
 "usage":{"input_tokens":0,"output_tokens":0,"cache_read_input_tokens":0,
          "cache_creation_input_tokens":0,"server_tool_use":{"web_search_requests":0}},
 "errors":["Not signed in. To authenticate without a browser, run:\n  grok login --device-code…"],
 "session_id":"","uuid":"…"}
```

Exit code `1`; the same text also goes to stderr. `ResultLine` in `wire.rs` declares both
`result: Option<String>` and `errors: Option<Vec<String>>` with
`skip_serializing_if = "Option::is_none"`, so on failure `result` is absent and `errors`
is present; on success the reverse. SASE would capture an empty detail and fall back to
stderr alone.

Fix: fold `errors[]` into the diagnostic detail when present. Safe by construction —
`append_error_events` (`_subprocess_stream.py:104`) returns early when
`return_code == 0`, so the success-path `result.result` (final text) is never mistaken
for an error. **[verified]**

### 2.2 New finding: the compat projection silently loses usage

**Neither prior report caught this, and it is the strongest argument against blindly
trusting the compatibility surface.**

`streaming-messages-json` is a *projection* of Grok's native usage ledger, not the ledger
itself. From `headless/reducer/messages/usage.rs:24-60`, every token field is read with
`.unwrap_or(0)`, and the CLI warns about its own output:

```rust
if end_usage.is_none() {
    tracing::warn!("streaming-messages-json: no aggregate usage ledger at turn end; \
                    `result.usage` token counts fall back to zero (the Messages API \
                    schema has no absent-usage marker)");
} else if usage_is_incomplete {
    tracing::warn!("streaming-messages-json: usage is incomplete; `result.usage` token \
                    counts may under-count or fall back to zero (the Messages API schema \
                    has no incompleteness marker)");
}
```

The `usage_is_incomplete` flag **exists** in Grok's own ledger
(`extensions/notification.rs:103`) and rides the native `streaming-json` `end` event, but
the Messages projection reads it only to emit a `tracing::warn!` and then **drops it**.
A `streaming-messages-json` consumer therefore cannot distinguish "this turn cost zero
tokens" from "we lost the accounting." `apiDurationMs` is likewise "dropped by the
projection" (source comment, `usage.rs:69`).

The trigger condition is `ledger_incomplete || cancellation_may_hide_usage`
(`agent/subagent/handle_request.rs:7-14`). Both halves matter to SASE specifically:

- **Subagents.** Grok Build ships built-in `general-purpose`, `explore`, and `plan`
  subagents. Unattributable subagent usage sets the flag — not an exotic edge case for a
  coding agent.
- **Cancellation.** `cancellation_may_hide_usage` is precisely SASE's interrupt path
  (`start_interrupt_monitor` / the interrupt-and-continue loop). Every interrupted Grok
  run is a candidate for silently zeroed usage.

This does **not** overturn the recommendation — the failure mode is under-reported
*usage*, not wrong *text* or wrong tool records, and SASE's token accounting is
telemetry rather than control flow. But it converts "reuse the Claude parser and you are
done" into "reuse the Claude parser, and treat Grok usage numbers as best-effort." See
§6 for the mitigation, which is cheap.

---

## 3. What Grok Build exposes

**Install & update.** `npm install -g @xai-official/grok` or the `x.ai/cli/install.sh`
shell installer. The npm package is a small Node trampoline plus per-platform optional
dependencies carrying a brotli-compressed Rust binary; on first run it decompresses to
`$GROK_HOME/bin/grok-<version>` (default `~/.grok/bin/`, 166 MB) and symlinks `grok` to
it. **The installed version lives under `~/.grok/bin`, not `node_modules`** — relevant to
SASE's `agent-cli` inventory. Self-update is `grok update`, but `manager: "npm"` keeps
Grok on SASE's existing npm update rail alongside Claude/Codex/Qwen.

`grok --version` prints `grok 1.0.3 (1a29d5bc12)`. SASE's default `_SEMVER_RE`
(`agent_clis/detect.py:28`) extracts `1.0.3` correctly — **no `version_regex` hook
needed**, unlike Muse. **[verified]** by running the regex against the real string.

**Auth.** `grok login` (browser OAuth) or `grok login --device-code` (headless hosts),
cached in `~/.grok/auth.json`; or `XAI_API_KEY` in the environment. OAuth draws on a
SuperGrok / X Premium+ subscription; `XAI_API_KEY` bills per token.

**Headless flags** (verified present in `1.0.3 --help` unless noted):

| Flag | Notes |
|---|---|
| `-p, --single <PROMPT>` | prompt as an argv value |
| `--prompt-file <PATH>` | **`/dev/stdin` works end-to-end** — see §4 |
| `-m, --model <MODEL>` | model id |
| `--reasoning-effort` / `--effort <LEVEL>` | canonical `none\|minimal\|low\|medium\|high\|xhigh\|max` |
| `--output-format <FMT>` | `plain\|json\|streaming-json\|streaming-messages-json` |
| `--permission-mode <MODE>` | `default\|acceptEdits\|auto\|dontAsk\|bypassPermissions\|plan` |
| `--always-approve` | auto-approve all tool executions |
| `--cwd <PATH>` | working directory |
| `-s, --session-id <UUID>` | new session with a caller-chosen UUID (errors if it exists) |
| `--max-turns <N>` | headless turn cap |
| `--tools` / `--disallowed-tools`, `--allow` / `--deny` | tool and permission rules |
| `--sandbox <PROFILE>` | filesystem/network sandbox (`GROK_SANDBOX`) |
| `--no-plan`, `--no-subagents`, `--no-memory`, `--disable-web-search` | feature toggles |
| `--include-partial-messages` | adds `stream_event` deltas to `streaming-messages-json` |
| `--no-auto-update` | **parses, but absent from `--help`** |
| `--no-ask-user` | **parses, but absent from `--help`** |
| `--yolo` | **parses, but absent from `--help`**; prefer `--permission-mode bypassPermissions` |

The three hidden flags were **[verified]** by argument-parse probe: all reach the auth
check, while `--bogus-flag-xyz` is rejected with `error: unexpected argument`. This
settles a disagreement — report `__a` asserted `--no-ask-user` from source reading and
`__b` did not list it; it is real, but undocumented in `--help`, so pin it with a probe
test and re-verify on each upgrade.

**Config, instructions, skills** (from `grok inspect --json`):

- **`AGENTS.md` is native**, with precedence `~/.grok/AGENTS.md` → `<repo-root>/AGENTS.md`
  → `<cwd>/AGENTS.md`. **No `GROK.md` shim is needed** — SASE's generated `AGENTS.md` is
  read directly.
- **Skills** at `~/.grok/skills/`, `<repo-root>/.grok/skills/`, `./.grok/skills/`. SASE's
  `skill_deploy_subpaths()` (`main/_init_skills_sources.py:26-28`) defaults to
  `f".{provider}"` when no hook is declared, so a provider named `grok` gets `.grok`
  **for free** — no `llm_skill_deploy_subpath` hook, unlike Qwen, OpenCode, Antigravity,
  and Muse. **[verified]**
- Config at `~/.grok/config.toml`; built-in subagents `general-purpose`, `explore`, `plan`.

**Concurrency note.** `grok` supports a shared "leader" backend process at
`~/.grok/leader.sock`, which would be a hazard for SASE's many-agents-at-once model. It
is **off by default** (`[cli] use_leader = true` opts in); `--no-leader` forces a fresh
agent. Leave it off and this is a non-issue.

### 3.1 Models — unsettled, and both reports were partly right

This is the one place where neither prior report could reach ground truth, and where
they diverged:

- `__a` recommended resolving both SASE tiers to a stable product alias `grok-build`, and
  stated that current docs identify **`grok-4.6`**.
- `__b` recommended `grok-4.5`, the only entry in the binary's offline catalog.

**[verified]** findings:

- `grok models` run unauthenticated reports `Default model: grok-4.5` and exactly one
  available model, `grok-4.5`. `__b` is right about the offline catalog.
- Scanning the binary's strings finds **no `grok-4.6` at all**. `__a`'s `grok-4.6` claim
  is **unsupported** and should not be carried forward.
- But `grok-build` appears 69 times (vs. 24 for `grok-4.5`), and the vendor's *embedded
  documentation examples* for `streaming-messages-json` use it as a model id verbatim:
  `{"type":"system","subtype":"init",…,"model":"grok-build",…}` and
  `{"type":"assistant","message":{…,"model":"grok-build",…}}`. A `grok-build-plan`
  variant also appears. So `__a`'s alias instinct has more support than `__b` credited.

The real catalog is server-driven (`GROK_MODELS_LIST_URL`, `GROK_MODELS_BASE_URL`), so an
authenticated account will very likely see more. **Do not hardcode confidently.** Ship
`grok-4.5` as the only known model, map both tiers to it, and settle `grok-build` versus
a dated flagship in Stage 0 (§6). Mapping both tiers to one model is conservative but
honest: inventing a `small` mapping to a model that may not exist under OAuth would make
ordinary SASE routing unreliable.

**Effort maps 1:1.** Grok's canonical levels are `none`, `minimal`, `low`, `medium`,
`high`, `xhigh`, `max` — **byte-identical** to `EFFORT_LEVELS_ORDERED` in
`sase/xprompt/effort.py:20-30`. **[verified]** No translation table is needed, unlike
Muse (`max` → `ultra`). The wrinkle: a model only accepts the levels its menu advertises,
and `grok-4.5` advertises low/medium/high offline. Prefer `__b`'s call — **pass all seven
through** — because SASE's `effort_cli_args` contract is about what the provider CLI
understands, and Grok understands all seven; a `%effort:xhigh` against a model that
refuses it then fails at the CLI with Grok's own message rather than being blocked early
by a SASE list that will go stale.

---

## 4. Mapping onto SASE's provider contract

### 4.1 Hooks

| Hook | Value | Notes |
|---|---|---|
| `llm_provider_name` | `"grok"` | |
| `llm_provider_short_name` | `"grk"` | free; existing are `cld`, `cdx`, `qwn`, `opc`, `agy`, `mus`, `fky` |
| `llm_resolve_model_name` | `large` → `grok-4.5`, `small` → `grok-4.5` | revisit both once the authenticated catalog is known (§3.1) |
| `llm_known_model_names` | `["grok-4.5"]` | grow from the authenticated catalog |
| `llm_skill_template_context` | `provider_name: "Grok"`, `provider_tool_name: "Grok Build"`, `provider_native_ask_tool: "ask_user_question"` | tool id seen in the binary as `x.ai/ask_user_question`; confirm in Stage 0 |
| `llm_skill_deploy_subpath` | **omit** | default `.grok` is already correct |
| `llm_autodetect_cli_name` | `"grok"` | enables doctor + `agent-cli` inventory |
| `llm_autodetect_priority` | **omit** | explicit-only — §4.3 |
| `llm_auth_evidence` | `credential_paths: ["~/.grok/auth.json"]`, `api_key_env_vars: ["XAI_API_KEY"]` | offline evidence only; never attempt a network login, never manage the credential |
| `llm_install_metadata` | `manager: "npm"`, `package: "@xai-official/grok"`, `scope: "global"`, `display_name: "Grok Build"`, `docs_url: "https://docs.x.ai/build/overview"` | no `version_regex`, no `version_argv` override |
| `llm_default_retry_config` | xAI transport/rate-limit wording | must not collide with Codex's `429`/`Too Many Requests` ownership |

### 4.2 Invocation

```python
[
    _grok_bin(),                       # SASE_GROK_PATH or "grok"
    "--prompt-file", "/dev/stdin",     # prompt written to stdin, as Claude does
    "--output-format", "streaming-messages-json",
    "--permission-mode", "bypassPermissions",
    "--model", model,
    "--cwd", workspace,
    "--no-plan",
    "--no-auto-update",
    "--session-id", str(uuid.uuid4()),
    *effort_args,                      # ["--effort", level]
]
```

**Prompt transport — disagreement resolved.** `__a` proposed a mode-`0600` temporary file
(Muse's pattern); `__b` proposed `--prompt-file /dev/stdin`. **[verified]** `/dev/stdin`
works end-to-end, not merely "parses": piping a prompt in advances past file reading to
the auth check, while the control case (`--prompt-file /tmp/does_not_exist`) fails
distinctly with `Error: Failed to read '…': No such file or directory (os error 2)`.
Prefer `/dev/stdin` — SASE's Claude provider already writes the prompt to
`process.stdin` (`claude.py:329-340`), so `_run_subprocess` stays identical and there is
no temp file to leak or clean up on interrupt. Both options avoid `-p`'s argv exposure,
so `__a`'s process-listing concern is satisfied either way.

**Permissions — merged.** Use `__b`'s `--permission-mode bypassPermissions` (visible in
`--help`, unlike `--yolo`) as the primary control, but keep `__a`'s `--no-plan`: SASE's
`/sase_plan` owns planning and artifact handoff, and Grok's native plan mode would
conflict. `__a`'s `--no-ask-user` is real and worth adding for the same reason
(`/sase_questions` ends the run cleanly and asks through SASE's gate) — but it is
undocumented in `--help`, so guard it with a parse test. Leave `--sandbox` unset rather
than `__a`'s explicit `--sandbox off`: SASE skills need controlled access to state
outside the checkout, and setting a profile explicitly is more likely to break that than
inheriting the default. Document the resulting posture (auto-approved tool execution,
no sandbox) in `docs/agent_providers.md` — this is powerful local execution and should
not be discovered by surprise.

**`--no-auto-update` is not optional.** Without it Grok may swap its own 166 MB binary
mid-run. SASE should own updates through `sase agent-cli`, exactly as it does for Muse
via `MUSE_NO_AUTO_UPDATE=1`.

**Session id.** SASE's Claude provider already generates a UUID per cycle; Grok's
`--session-id` has the same "new session, must be a fresh UUID" semantics, so the
pattern transfers directly and yields resumable sessions under `~/.grok/sessions`.

### 4.3 Explicit-only registration (both reports agree)

`grok-dev` installs a binary named `grok` **and** uses `~/.grok/`; Homebrew's deprecated
regex tool also claims the name. If more than one is installed, whichever wins `PATH`
gets launched, and a stale `grok-dev` handed Grok Build's flags would reject them.

SASE's autodetect only checks PATH presence. The precedent is explicit in `muse.py:1-8`:
Muse "deliberately publishes no `llm_autodetect_priority` — `muse` is a generic
executable name … so a same-named binary must never win the default provider on its
own." **[verified]** The same reasoning applies more strongly here, because the collision
is concrete rather than hypothetical.

Declare `llm_autodetect_cli_name: "grok"` (enough for `sase doctor` and `sase agent-cli`
inventory) but **no** `llm_autodetect_priority`. Select Grok via
`llm_provider.provider: grok`, `%model:grok/<model>`, or `SASE_GROK_PATH`. Current
priorities for reference: `claude=0`, `codex=10`, `qwen=15`, `opencode=18`, `agy=30`,
`fakey=1000`; `muse` has none.

A later generic enhancement could let providers supply a read-only identity probe and
auto-select Grok Build only when `grok --version` matches its product signature. Not
required now.

### 4.4 Genuinely new code

1. `src/sase/llm_provider/grok.py` — the provider, ~250–300 lines, closely modeled on
   `claude.py` (which is 348 lines **[verified]**).
2. A ~5-line `errors[]` branch in `_subprocess_claude.py::_process_json_line`, guarded so
   Claude behavior is unchanged.
3. Entry point in `pyproject.toml` under `[project.entry-points."sase_llm"]`.
4. Tests plus recorded NDJSON fixtures (needs the Stage 0 authenticated capture).

**No Rust core changes. [verified]** against `sase-core@origin/master`: `llm_provider` is
carried as `Option<String>` throughout (`agent_scan/wire.rs`, `agent_group_archive/wire.rs`,
`agent_archive`, `sase_core_py`), and the only `*Provider` enums in the tree are
`PushProviderMode` and `PushProviderWire` in `sase_gateway`, which are push-notification
providers and unrelated. The whole change stays Python-side, consistent with the Rust
core boundary rule.

### 4.5 Reused unchanged

`_subprocess_claude.stream_and_parse_json_output`;
`_tool_call_claude.append_claude_tool_call_event` (the optional `tool_use_result`
envelope is read with `.get()` and its absence degrades cleanly);
`_subprocess_artifacts` usage/live-reply writers;
`_subprocess_plain.start_interrupt_monitor` and the interrupt/continue loop;
`_effort_args.effort_cli_args`.

---

## 5. Risks and gotchas

**Usage accounting is best-effort (§2.2).** The highest-value caveat, and the one that
should shape expectations rather than the design. Mitigation in §6.

**Grok reads `CLAUDE.md` too.** `grok inspect --json` in a SASE workspace reports *both*
`CLAUDE.md` and `AGENTS.md` as project instructions — identical content, ~2,829 tokens
each, injected twice, because `sase memory init` generates `CLAUDE.md` as a provider shim
of `AGENTS.md`. This is not configurable away: Grok's `[compat.claude]` block can disable
the `agents` cell, but generic top-level `CLAUDE.md` stays recognized regardless.
Options: accept it (instruction text, cache-friendly, a few thousand tokens), or stop
emitting `CLAUDE.md` when the configured provider is `grok` — a memory-generation change
with real blast radius that would also break any human running `claude` in the same tree.
**Accept it for now, document it in `docs/agent_providers.md`, and file a follow-up.**

**Claude-compat cross-contamination.** `[compat.claude]` defaults to **on** for `skills`,
`rules`, `agents`, `mcps`, `hooks`, and `sessions`, so a Grok run also picks up
`~/.claude/skills/` and `./.claude/skills/` — where SASE already deploys generated skills
for the Claude provider. Once `.grok/skills/` is also populated, Grok sees each SASE skill
twice (name collisions resolve by scope precedence, so this is listing duplication rather
than a hard failure). `grok inspect` also reports consulting
`/etc/claude-code/managed-settings.json` for managed policy. Either set
`[compat.claude] skills = false` in a SASE-managed `~/.grok/config.toml`, or verify the
precedence dedupe is acceptable. Check explicitly in Stage 2.

**Version velocity.** `1.0.0` landed five days ago; three patches in five days. Pin
fixtures by version in their filenames (the repo already does this —
`muse_exec_read_tool_R708.1.jsonl`) and keep `--no-auto-update` on so a run's CLI cannot
change under it. Parse tolerantly and ignore unknown event types.

**Undocumented flags.** `--no-auto-update`, `--no-ask-user`, and `--yolo` all parse but
are absent from `--help`. Guard each with a parse test and re-verify on upgrade.

**Subscription vs API key.** OAuth uses a SuperGrok / X Premium+ subscription;
`XAI_API_KEY` bills per token. SASE launches many agents in parallel, so the cost profile
differs enormously, and subscription rate limits are undocumented. Note also that
`total_cost_usd` is only meaningfully stamped on API-key traffic — combined with §2.2,
expect SASE cost accounting to be blank or zero on subscription runs. Decide the auth
mode deliberately.

**Init-line schema drift.** Grok's `system`/`init` and terminal `result` lines may not
pass strict Anthropic schema validation, because Grok omits placeholder fields it cannot
fill (`claude_code_version`, `output_style`, `plugins`, `permission_denials`) rather than
zero-filling them. SASE ignores `system` entirely and reads only `usage` and diagnostics
off `result`, so this does not bite today — but a future SASE feature reading `init`
fields must tolerate absences.

**Privacy.** Prompts, agent-selected repository context, and tool results go to xAI.
Provider docs should link current xAI data/privacy terms and avoid implying
zero-data-retention unless the org is eligible and configured for it.

**Satellite touchpoints.** From the Muse precedent (7 commits, ~50 files): badge in
`integrations/provider_badges.py`, palette in `ace/tui/provider_styles.py`, doctor hints
in `doctor/checks_providers.py`, the provider-list comment in `default_config.yml`, and
docs across `docs/agent_providers.md`, `docs/configuration.md`, `docs/llms.md`,
`docs/cli.md`, `INSTALL.md`, `README.md`. Badge and palette are optional (unknown
providers fall back to a neutral style and a `None` badge). Docs are not.

---

## 6. Alternatives weighed

| Approach | Cost | Verdict |
|---|---|---|
| **A. Native `grok` provider on `streaming-messages-json`** | 1 module + ~5 shared lines + tests + docs | **Recommended.** Reuses both parsers outright. |
| B. Native provider on native `streaming-json` (ACP) | + full `_subprocess_grok.py` and `_tool_call_grok.py` | Not now — but §2.2 gives it a real argument it did not have before: the native `end` event keeps `usage_is_incomplete`, `apiDurationMs`, and a richer per-model ledger that the Messages projection discards. Revisit if usage fidelity turns out to matter. |
| C. Provider wrapping `grok-dev` | 2 bespoke parsers, unmaintained target, API-key-only billing | Rejected. Strictly more work for a strictly worse target. |
| D. Out-of-tree plugin (`sase-grok`) | same code, separate release train | Viable — the `sase_llm` entry-point group supports third-party plugins — but every first-party provider is in-tree, and splitting one out adds release coordination for no benefit. |
| E. OpenCode pointed at an xAI model | ~zero | Not a substitute, but **do this first** as a cheap model-quality probe. |
| F. Direct xAI Responses/API provider | build and maintain an entire agent loop | Rejected. SASE's provider boundary is deliberately thin; tool execution, permissions, sessions, and context management are the CLI's job. |
| G. `grok agent stdio` (ACP/JSON-RPC) | new persistent-session transport | Deferred. Right shape for a future editor/daemon integration; `LLMProvider.invoke()` is one-shot and needs none of it. |

Option B deserves a note on how the two prior reports split: `__a` recommended it,
`__b` rejected it, and on the evidence `__b` is right for now — xAI's own docs call
`streaming-messages-json` the compatibility surface, and paying for two bespoke parsers
up front to buy usage fidelity is the wrong trade before a single authenticated run has
happened. But `__a`'s instinct was not wrong, and §2.2 identifies exactly the measurement
that would justify switching.

---

## 7. Recommendation

**Build a native, in-tree `grok` LLM provider that drives xAI's Grok Build CLI in
headless mode with `--output-format streaming-messages-json`, reusing SASE's existing
Claude stream and tool-call parsers, registered explicit-only with no autodetect
priority.**

Ship in three stages so nothing lands unverified.

### Stage 0 — decide, before writing code (hours)

The only genuine blocker, and it is small.

1. Authenticate (`grok login`, or set `XAI_API_KEY`) and settle the
   subscription-vs-API-key question (§5).
2. Run `grok models` authenticated to capture the real catalog, and resolve
   `grok-build` vs `grok-4.5` vs a dated flagship (§3.1). Confirm the ask-user tool id
   (`x.ai/ask_user_question`).
3. Capture three NDJSON traces under `--output-format streaming-messages-json` — a
   read-only run, a write+bash run, and a deliberate failure — as version-pinned fixtures
   (`grok_messages_read_1.0.3.jsonl`, …). These are the test corpus.
4. **Measure the usage gap (§2.2).** Run the *same* prompt twice, once under
   `streaming-messages-json` and once under `streaming-json`, and compare
   `result.usage` against the native `end.usage` ledger — including one run that spawns a
   subagent and one that is interrupted mid-turn. Run with `--debug-file` to catch the
   `usage is incomplete` warning. If the projection holds up, proceed as planned; if it
   zeroes routinely, reconsider option B or plan a hybrid (Messages for text and tools,
   a side-channel for usage).
5. Optional, cheap: run the same prompt through the existing OpenCode provider against an
   xAI model to sanity-check that the *model* earns its place.

### Stage 1 — the provider

1. `src/sase/llm_provider/grok.py` modeled on `claude.py`: `SASE_GROK_PATH` override,
   `SASE_LLM_{LARGE,SMALL}_ARGS` / `SASE_GROK_{LARGE,SMALL}_ARGS` passthrough, the
   interrupt/continue loop, and the invocation vector from §4.2.
2. Pass all seven canonical effort levels through as `["--effort", level]` (§3.1).
3. `pyproject.toml`: `grok = "sase.llm_provider.grok:GrokProvider"`.
4. Extend `_subprocess_claude.py::_process_json_line` to fold `errors[]` into the
   diagnostic detail, with a Claude-path regression test proving no behavior change.
5. Doctor hints in `doctor/checks_providers.py`: install
   `npm install -g @xai-official/grok`; auth "run `grok login` (or
   `grok login --device-code`), or set `XAI_API_KEY`". Treat a cached auth file or
   `XAI_API_KEY` as offline evidence; never attempt a network login.
6. Tests against the Stage 0 fixtures: exact argv; model and effort mapping; the four
   usage keys; tool-call start/result records; text chunks split at arbitrary token
   boundaries; the `errors[]` failure path; missing-executable and unauthenticated
   failures; partial-output preservation across an interrupt; a parse-probe test pinning
   the three undocumented flags; and the collision case where an unrelated `grok` is on
   `PATH`.

Deliberately **not** implemented in Stage 1: `llm_skill_deploy_subpath` (default `.grok`
is correct), `version_regex` (default semver scan works), `llm_autodetect_priority`
(§4.3), and any Rust core change (§4.4).

### Stage 2 — integration polish

1. Badge and ACE palette.
2. `default_config.yml` provider-list comment.
3. Docs: a Grok Build section in `docs/agent_providers.md` (install, auth, update,
   explicit-only selection, and the auto-approve/no-sandbox posture) plus the usual sweep
   of `docs/configuration.md`, `docs/llms.md`, `docs/cli.md`, `INSTALL.md`, `README.md`.
4. Verify skill deployment end to end: `sase init skills` → `~/.grok/skills/`, and
   confirm the `[compat.claude] skills` overlap (§5) is acceptable or disable it.
5. Document the `CLAUDE.md` + `AGENTS.md` double-load and file a follow-up task bead.

Because this broadens the provider registry and touches subprocess, doctor, model, and
skill paths, run `just install` then `just check-full`, not only provider unit tests.
Finish with authenticated smoke runs: a no-tool prompt, a file edit, a shell tool, a SASE
skill that writes state outside the checkout, an intentional model error, and an
interrupt/relaunch.

### Why this is the right call

- **Cheapest viable option.** The one format xAI built for Claude Code consumers is the
  one SASE already parses. Every other route pays for two bespoke parsers.
- **Most complete.** SASE gets Grok Build's plan mode, subagents, worktrees, skills,
  hooks, MCP, and session store — not just the model.
- **Most maintainable.** Vendor-published, weekly stable releases, Apache-2.0 source
  available for exactly the schema questions that matter.
- **Bounded risks.** Version velocity (pinned fixtures, `--no-auto-update`), a contested
  binary name (explicit-only selection), instruction duplication (measured, documented,
  deferred), and usage fidelity (measured in Stage 0, with option B as the escape hatch).

The honest counter-argument is timing: `1.0.0` is five days old and the surface is moving
weekly. If that is unacceptable, the correct move is to wait a release cycle and re-run
§3 — not to build against `grok-dev`, which is not moving at all.

---

## 8. Open questions requiring an authenticated account

Nothing above depends on these; all are Stage 0 work.

1. **The real model catalog** — offline the binary knows only `grok-4.5`, while the
   vendor's own embedded examples use `grok-build`. Needed to fill
   `llm_known_model_names`, `llm_model_short_aliases`, and the `small` tier.
2. **Per-model effort menus** — `grok-4.5` advertises low/medium/high offline; whether any
   model accepts `xhigh`/`max` is unverified.
3. **Real `streaming-messages-json` success traces** — the success-path framing
   (`assistant`/`user`, `tool_use`/`tool_result`) is confirmed from vendor source and
   embedded examples but not from a live authenticated run.
4. **Usage fidelity under subagents and interrupts (§2.2)** — the single most important
   open measurement.
5. **The ask-user tool id** — the binary contains `x.ai/ask_user_question`; confirm it is
   what belongs in `llm_skill_template_context.provider_native_ask_tool`.
6. **Rate limits and cost reporting on the subscription path** — undocumented, and
   material for SASE's parallel-agent workloads.

---

## Sources

- **Direct measurement** — `@xai-official/grok` 1.0.3 Linux x86-64 binary
  (`grok 1.0.3 (1a29d5bc12)`) run under an isolated `HOME`/`GROK_HOME`: `--help`,
  `models`, `--version`, argument-parse probes, and live `streaming-messages-json` /
  `streaming-json` failure frames.
- **Vendor source** — `xai-org/grok-build` (Apache-2.0), opened via `sase repo open`:
  `crates/codegen/xai-grok-pager/src/headless/reducer/messages/{usage.rs,wire.rs}`,
  `crates/codegen/xai-grok-shell/src/extensions/notification.rs`,
  `crates/codegen/xai-grok-shell/src/agent/subagent/handle_request.rs`.
- **xAI docs** — [Grok Build overview](https://docs.x.ai/build/overview),
  [CLI Reference](https://docs.x.ai/build/cli/reference),
  [Headless & Scripting](https://docs.x.ai/build/cli/headless-scripting),
  [Permissions](https://docs.x.ai/build/features/permissions),
  [Skills, Plugins & Marketplaces](https://docs.x.ai/build/features/skills-plugins-marketplaces),
  [Enterprise Deployments](https://docs.x.ai/build/enterprise).
- **Package registry** — `@xai-official/grok` and `grok-dev`, queried 2026-08-12.
- **SASE** at `bb60a0bd1` — `llm_provider/{_subprocess_claude,_subprocess_stream,_subprocess_artifacts,_tool_call_claude,claude,muse}.py`,
  `main/_init_skills_sources.py`, `agent_clis/detect.py`, `xprompt/effort.py`.
- **sase-core** at `origin/master` — `agent_scan/wire.rs`, `agent_group_archive/wire.rs`,
  `sase_gateway/{push,wire}.rs`.
- **Prior passes** — `grok_build_provider__a.md` (research.0c.cdx),
  `grok_build_provider__b.md` (research.0c.cld), in this directory.
