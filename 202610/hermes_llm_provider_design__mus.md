# Adding Hermes as a Fully Supported SASE LLM Provider

**Researcher:** mus · **Date (UTC):** 2026-10-19 · **Report:** `hermes_llm_provider_design__mus.md`
**Question:** What is the best way to add [hermes-agent](https://github.com/nousresearch/hermes-agent)
as a new, fully supported SASE LLM provider?

**Pins verified firsthand for this report:**

| Project | Pin |
| ------- | --- |
| SASE (this workspace) | `0.18.0`, HEAD `4b7b981532` (2026-10-19) |
| Hermes (`NousResearch/hermes-agent`, via `sase repo open gh:NousResearch/hermes-agent`) | HEAD `8f5693af41` |

**Method.** I read the SASE provider stack directly
(`src/sase/llm_provider/`: `base.py`, `_hookspec.py`, `model_manifest.py`,
`muse_provider.py`, `grok.py`, `opencode.py`; `models.yml`; `pyproject.toml`
entry points; `docs/contribute/llm-invocation.md`,
`docs/reference/providers/`) and the Hermes checkout directly (its
`website/docs/reference/cli-commands.md`, `hermes_cli/oneshot.py`,
`hermes_cli/_parser.py`, `hermes_cli/main.py`, `README.md`). I did **not**
install or execute Hermes (`which hermes` finds nothing in this workspace),
so every Hermes behavior claim below is docs/code-grounded at the pinned SHA
and marked for a live spike. Prior Hermes↔SASE comparisons
(`202604/sase_vs_hermes_agent.md`, `202609/sase_vs_hermes_agent/`,
`202610/can_hermes_replace_sase/`) were used as pointers only. I did not
read any peer swarm report.

## 1. TL;DR and recommended solution

**Recommended: add Hermes as an 8th bundled provider (`sase.llm_provider.hermes:HermesProvider`,
short name `her`) whose transport is `hermes chat --oneshot --query-file - --format stream-json`,
with `--yolo --ignore-rules --source tool --in <cwd>`, the SASE memory-built root bundle
prepended into the prompt (Muse pattern), `--model` carrying the resolved model, `--reasoning`
carrying effort, and per-run usage plus tool calls parsed from the `stream-json` event stream.
Keep `hermes -z --usage-file` as the documented fallback transport if `stream-json` proves
flaky during the spike. Ship it opt-in (no autodetect priority, no size-alias membership) in v1;
promote to alias pools only after a soak period.**

Why this shape:

- `chat --oneshot --format stream-json` is Hermes's only headless entry point that yields
  **structured progress** (`system`/`text`/`tool_use`/`tool_result`/`result` events with token
  counters) — the thing SASE needs for live replies, `tool_calls.jsonl`, and `usage.json`.
  The purer `hermes -z` prints only final text and would leave SASE blind on tool calls.
- `--query-file -` (stdin) solves the prompt-transport problem the way SASE's Claude/Grok
  stdin transports do: no argv byte-limit risk, no shell interpretation — critical because
  preprocessed SASE prompts are large and untrusted text must arrive verbatim.
- `--ignore-rules` plus explicit bundle-prepend gives SASE the same instruction-isolation
  posture it already enforces for Grok/Muse (no native `AGENTS.md`/memory/skills from
  untrusted workspaces; exactly one SASE-built bundle, delivered once).
- Hermes natively supports everything the SASE harness needs around the edges:
  per-run `--model`/`--provider`, 8-level `--reasoning` (a superset of SASE's levels),
  `--resume` for headless retry continuation (better than Muse, which has none),
  distinctive exit codes, and `--source tool` so SASE runs stay out of the user's
  session pickers.

## 2. How a SASE provider is built (the checklist Hermes must satisfy)

A bundled provider is a class implementing `LLMProvider.invoke()` plus pluggy metadata
hooks (`_hookspec.py`), registered in `pyproject.toml` under `sase_llm`, with its model
catalog in `models.yml`. Concretely, from the Muse/Grok/OpenCode implementations:

| Piece | What it is | Hermes answer (this report, §3–§4) |
| ----- | ---------- | ---------------------------------- |
| Module | `src/sase/llm_provider/hermes.py` (+ `_subprocess_hermes.py`, `_tool_call_hermes.py` siblings) | New files following the Muse split pattern |
| Entry point | `hermes = "sase.llm_provider.hermes:HermesProvider"` in `pyproject.toml` | Add one line |
| Names | `llm_provider_name()` → `"hermes"`; short name for `foo.<short>` agent names | `"her"` (all of `agy/cld/cdx/fky/grk/mus/opc/qwn` are taken) |
| Catalog | `models.yml` entry: `models` list + `tiers: {large, small}` (manifest **requires** exactly both tiers, each naming a listed model) | Seed with 2+ provider-qualified Hermes model IDs; see §4.4 |
| Invoke loop | Build argv, stream stdout, interrupt monitor, completion watchdog, non-zero exit → `CalledProcessError` | `chat --oneshot` + shared JSON-line streaming helpers |
| Tool calls | Parse stream events → `$SASE_ARTIFACTS_DIR/tool_calls.jsonl` | `tool_use`/`tool_result` events map cleanly; see §4.6 |
| Usage | Accumulate counters → `usage.json` | `result.tokens` inline; see §4.7 |
| Retry | `llm_default_retry_config()` with provider-specific patterns | Hermes 429/5xx/timeout wording TBD in spike |
| Usage limits | `llm_default_usage_limit_config()` patterns | `hermes usage --json` exists for a future probe; patterns TBD |
| Interrupts | `start_interrupt_monitor` + continuation prompt | Hermes `--resume` allows true continuation; see §4.8 |
| Single-turn | Provider directive naming its own wait primitives | New `_HERMES_SINGLE_TURN_DIRECTIVE`; see §4.5 |
| Instruction delivery | `llm_instruction_delivery()` slot map + channel constant | New `CHANNEL_HERMES_ROOT`, prepend pattern (Muse-like) |
| Skills | `llm_skill_template_context()` + `llm_skill_deploy_subpath()` | `~/.hermes/skills/` → subpath `".hermes/skills"` (verify) |
| Doctor/auth | `llm_auth_evidence()` credential paths + env vars | `~/.hermes/.env`, `~/.hermes/config.yaml` |
| Install | `llm_install_metadata()` (manager/package or script) | `manager: "script"`, script installer URL, `self_update_argv: ["update"]` |
| Interactive | `llm_interactive_cli()` menu key/bypass/model args | `menu_key` free letters; bypass `--yolo`; model via `-m/--model` |
| Autodetect | `llm_autodetect_cli_name()` + optional priority (0/10/15/18/30 used) | Name `hermes`; **omit priority in v1** (opt-in only) |
| Effort | `invocation_option_args()` via `effort_cli_args` | `--reasoning` accepts a superset; forward all levels |
| Docs | `docs/reference/providers/hermes.md` + index link; generated model tables via `just fix` | New page mirroring `grok.md`/`muse.md` |
| Tests | `tests/llm_provider/test_hermes_*.py` (core/invocation/stream/metadata) | Mirror `test_muse_*` / `test_grok_*` files |
| Color | `llm_cli_status_color()` hex | Pick unused hex |

## 3. Hermes's headless surface (grounded at `8f5693af41`)

Hermes has **two** scripted entry points. They are not equivalent; the choice between
them is the single most load-bearing decision in this design.

### 3.1 Option A (recommended): `hermes chat --oneshot --format stream-json`

- Invocation: `hermes chat --oneshot -q "<prompt>"` or `--query-file PATH` (`-` = stdin).
  Docs: "answer the query and exit". Exit codes `0` completed / `1` failed-or-partial-or-budget /
  `130` interrupted, plus `75` (`EX_TEMPFAIL`) for a Kanban-worker rate-limit/5xx path.
- `--format stream-json` requires `-q`/`--query-file`, implies quiet non-interactive mode,
  rejects `--tui`. Every stdout line is one JSON object with `timestamp` (epoch ms);
  diagnostics stay on stderr. Event types: `system` (`init` + `model` + `session_id`),
  `text` deltas, `tool_use` (`name`, `input`), `tool_result` (`name`, `output` capped at
  5000 chars, `duration_ms`, `is_error`), and a terminal `result` (`session_id`,
  `exit_code`, full `text`, `tokens: {input, output, total, cache_read, cache_write}`,
  `duration_ms`, `error` on failure, `replay_gap` flag). "Treat that record as the
  completion signal; the process exit code matches its `exit_code`."
- Relevant per-run flags (all verified in `hermes_cli/_parser.py` + cli-commands.md):
  `-m/--model`, `--provider` (note: `-z` refuses `--provider` without `--model`;
  assume the same discipline on the chat path), `--reasoning none|minimal|low|medium|
  high|xhigh|max|ultra` (per-run override of `agent.reasoning_effort`),
  `-t/--toolsets`, `-s/--skills`, `--resume/--continue`, `--in DIR` (cwd scoping),
  `--max-turns N` (default 500), `--yolo`, `--pass-session-id`,
  `--ignore-user-config`, `--ignore-rules` (skip `AGENTS.md`/`SOUL.md`/memory/skills
  injection), `--safe-mode` (implies both ignores + no plugins/MCP; requires explicit
  `--model`), `--source <tag>` ("Use `tool` for third-party integrations that should
  not appear in user session lists"), `--query-file` (verbatim, no shell interpretation).
- Caveat: `--query-file` exists on the **chat** path. The top-level `-z` parser snapshot
  (`_VALUE_FLAGS_FALLBACK`) lists `-z --oneshot -m --model --provider --reasoning
  -t --toolsets -r --resume -s --skills --usage-file --in` — **no `--query-file`**.
  So large-prompt stdin transport is a chat-path advantage, not available to `-z`
  (whose prompt is an argv value, subject to OS argv limits — SASE prompts plus an
  explicit bundle can be tens of KiB).

### 3.2 Option B (fallback): `hermes -z PROMPT` (top-level one-shot)

- "Single prompt in, final response text out, nothing else on stdout or stderr. No banner,
  no spinner, no tool previews, no `Session:` line." Approvals auto-bypassed
  (`HERMES_YOLO_MODE=1`, `HERMES_ACCEPT_HOOKS=1` in `oneshot.py`), stateless channel so
  `delegate_task` children join inline instead of being discarded.
- Exit codes **differ from chat**: `0` completed / `2` failed-or-partial / `130`
  interrupted / `1` completed-but-empty ("reserves `1` for 'answered nothing'").
  Judge by exit code, not by empty stdout.
- `--usage-file PATH`: machine-readable report (`estimated_cost_usd`, `input/output/
  cache_read/cache_write/reasoning/total_tokens`, `api_calls`, `model`, `provider`,
  `session_id`, `service_tier`, `completed/failed/partial/interrupted`,
  `turn_exit_reason`, plus `auxiliary.by_task` and `total_including_auxiliary`).
  Written **even on failure**; a broken write never masks the run outcome.
- Weaknesses for SASE: no tool-call events (SASE's TUI LLM-calls panel would go dark),
  no token stream (usage only via the sidecar file), prompt-as-argv only, and a
  **separate exit-code dialect** to special-case. Also `hermes-agent` (the legacy
  minimal runner) is explicitly not for this use — docs: "For anything else use
  `hermes`".

### 3.3 Russ-relevant Hermes facts

- **Install:** `curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`
  (Linux/macOS/WSL2; APT repo for Termux; PowerShell installer for native Windows).
  There is **no npm package** — `llm_install_metadata()` must use `manager: "script"`
  (like Muse's `install_script_url` pattern) or `manual`, never `npm`. Self-update is
  `hermes update` (`--check` previews). Binary name on PATH is `hermes` — distinctive,
  so no `muse`/`grok`-style wrong-binary hazard.
- **Auth/home:** `~/.hermes/config.yaml` + `~/.hermes/.env`, overridable via
  `HERMES_HOME`; per-profile homes exist. Doctor evidence:
  `credential_paths: ["~/.hermes/.env", "~/.hermes/config.yaml"]`.
  (`hermes auth` manages OAuth/API keys; keys live in `.env`, so no single
  `api_key_env_vars` anchor — list the common provider-key names only if the spike
  confirms them, else paths alone.)
- **Skills:** user skills live in `~/.hermes/skills/` (confirmed via the
  Claude/Codex import mapping). Expected deploy subpath: `".hermes/skills"` —
  verify SASE's subpath-join semantics against the Muse (`.config/muse`) precedent
  during implementation.
- **Model routing inside Hermes:** Hermes is itself a 40+ provider router
  (`--provider` choices include `openrouter/nous/anthropic/gemini/openai-codex/…`;
  model IDs are provider-qualified like `anthropic/claude-sonnet-4.6`). SASE's
  `--model` value passes straight through, so `%model:hermes/<anything-hermes-knows>`
  works with zero SASE-side catalog maintenance.
- **Isolation flags:** `--ignore-rules` is the exact lever SASE needs for untrusted
  workspaces (skips `AGENTS.md`/`SOUL.md`/memory/skills injection); `--ignore-user-config`
  goes further (built-in defaults; `.env` credentials still load). `--safe-mode` is too
  strong for normal use (disables MCP/plugins the user's Hermes setup may need for the
  task) — reserve it for diagnostics, not the default argv.
- **Version probe:** `hermes --version` exists; output format unverified (not installed
  here) — the spike must confirm whether the default semver regex suffices or a
  `version_regex` (Muse pattern) is needed.

## 4. Decision-by-decision analysis

### 4.1 Transport: `chat --oneshot --format stream-json` (primary), `-z` (fallback)

`stream-json` gives SASE all three things its harness consumes — reply text
(`text` + terminal `result.text`), tool calls (`tool_use`/`tool_result`), and usage
(`result.tokens`) — over one pipe, reusing the existing bounded JSON-line streaming
helpers (`_subprocess.py` family) that Claude/Codex/Grok already use. `-z` gives only
the first, via a second file (`--usage-file`) with different key names and a different
exit-code dialect. The prior `__mus` comparison already foresaw this integration
("adding Hermes as an 8th `sase_llm` provider via its headless one-shot/stream-json
mode"); the new evidence since then is that **both** halves exist and the chat path
additionally solves prompt transport (`--query-file -`). Prototype the chat path first;
fall back to `-z` only if `stream-json` shows drift (Hermes docs admit config/prose
drift in places).

### 4.2 Prompt transport: stdin via `--query-file -`

Preprocessed SASE prompts are large (directives + bundle + user work) and must arrive
verbatim. `--query-file -` reads the query from stdin with "nothing shell-interpreted"
— the same property SASE relies on for Claude/Grok stdin transports, and it avoids the
Linux single-argv-element ceiling that Grok had to guard with a 120 KiB check. Never
pass the prompt as `-q` argv (shell-quoting + size risk) and never as `-z` argv.

### 4.3 Working directory: inherit process cwd; pass `--in` only if needed

SASE launches each provider with the workspace clone as cwd (see Grok `--cwd`, Muse
`--workspace`, OpenCode `--dir`). Hermes uses CWD plus `--in DIR` override and
workspace-scoped session lookup. Simplest correct behavior: rely on inherited cwd
(zero new flags) and add `--in <cwd>` only if the spike shows Hermes resolving
elsewhere (e.g. under `--resume`). Do **not** pass `--worktree` — SASE owns isolation
through numbered clones; a Hermes-managed worktree would double-isolate and break
finalizer path assumptions.

### 4.4 Model catalog: seed a small provider-qualified list; tiers name real entries

`model_manifest.py` requires `tiers: {large, small}`, each naming a `models` entry
(same value twice is not forbidden by the validator, but distinct tiers are the
honest signal). Because Hermes routes to 40+ backends, any fixed SASE default will be
wrong for some users — so:

- Seed `models` with 2–4 stable, widely-available provider-qualified IDs observed in
  Hermes docs/code (e.g. an Anthropic Sonnet-class and a frontier-class ID — re-verify
  IDs at implementation time; Hermes picker lists rot fast), plus `short_aliases`.
- Map `large`/`small` to the two seeds. Document that the catalog is a **default route,
  not a capability list**: `%model:hermes/<any-hermes-model-id>` and Hermes-side
  `HERMES_INFERENCE_MODEL`/`config.yaml` defaults always work through `--model`
  passthrough, and per-run `--provider` stays unset (Hermes auto-detects from the model
  string) unless the user explicitly overrides.
- Do **not** add Hermes targets to the shipped `@xsmall…@xlarge` alias pools in v1
  (those pools are the subscription-economics surface; Hermes billing is per-token and
  unmeasured by SASE until a usage probe exists). Revisit after soak + usage support.

### 4.5 Single-turn directive: required, Hermes-specific, small

Hermes finite runs already neutralize two classic hazards (approvals auto-bypassed,
`delegate_task` joins inline per the finite-chat-runs contract). The directive must
still cover what Hermes *doesn't* neutralize, naming Hermes primitives the way the
Grok directive names `block_until_ms`/`spawn_subagent`: never end the turn to wait
(no `cronjob_manage` schedules, gateway/monitor round-trips, or "continues in a new
turn" constructs survive process exit); run terminal work in the foreground to
completion; handoff commands (`sase monitor start`, `sase plan propose`, `sase pipe`,
`sase questions`) can take up to a minute — wait for the handoff to exit. Draft it
from the Grok/Muse directive templates and verify wording against Hermes tool names
(`delegate_task`, terminal tool, `cronjob_manage`) in the spike.

### 4.6 Tool-call capture: parse `tool_use`/`tool_result`, no hooks

Mirror the Grok approach: stream-parse, never install provider hooks. Map Hermes's
`tool_use.name`/`input` and `tool_result.output` (5000-char cap — note the truncation
in previews) onto SASE's canonical display names in a new `_tool_call_hermes.py`
(write the name map from a live `--list-tools`-equivalent capture during the spike;
unmapped names survive verbatim per the Grok precedent). Append normalized records to
`$SASE_ARTIFACTS_DIR/tool_calls.jsonl` with a Hermes runtime/source tag so the TUI
LLM-calls panel lights up.

### 4.7 Usage accounting: `result.tokens` → `usage.json` now, `--usage-file` semantics later

`result.tokens {input, output, total, cache_read, cache_write}` maps onto SASE's four
accumulator keys (`input_tokens`, `output_tokens`, `cache_creation_input_tokens` ←
`cache_write`, `cache_read_input_tokens` ← `cache_read`). Treat counts as telemetry
(Grok precedent: subagent turns can under-count). The richer `-z --usage-file` ledger
(cost, aux breakdown) is a reason to keep `-z` as fallback, not a reason to prefer it:
SASE's contract needs inline counters, which only the chat path provides. A future
`llm_usage_probe` collector can shell `hermes usage --json` (exists for rate-limit
windows); declare `llm_usage_capabilities()` only when that collector lands, not before.

### 4.8 Interrupts, retries, resume: Hermes is strictly better than Muse here

- Interrupts reuse the shared `start_interrupt_monitor` + continuation-prompt loop.
- Retry defaults (`llm_default_retry_config`, 3 retries / 60-300-1800s backoff) need
  Hermes-specific `error_patterns` captured live in the spike (429/overload/5xx/timeout
  and billing-wall wording); keep them Hermes-namespaced so they can't collide with
  Codex's generic `429` ownership (Grok precedent).
- Resume: Hermes `--resume <session_id>` (from the `system.init`/`result` events SASE
  already parses) enables **true headless continuation** — no "reconstruct the context"
  dance like Muse/Codex/OpenCode. Use it for both interrupt continuation and retry
  continuation (`preserve_workspace=True` still applies). This is a genuine
  Hermes-provider advantage worth calling out in the docs page.

### 4.9 Instruction delivery: explicit-prepend, new channel, no native files

Follow the Muse explicit pattern, not the Grok `--rules` pattern (Hermes has no
`--rules` equivalent): pass `--ignore-rules` on every SASE run and prepend
`{explicit_bundle}\n\n--- User Prompt ---\n{prompt}` into the stdin payload — or the
`wrap_hermes_prompt()` equivalent when delivery is legacy/disabled. Register
`CHANNEL_HERMES_ROOT = "hermes.prompt_prefix"`-style channel constant per the
`CHANNEL_RE` convention and implement `llm_instruction_delivery()` with
`root: explicit / subagent: none` behind a sunset flag (Grok/Muse precedent), so the
legacy path stays reachable. Never let a Hermes run in a SASE workspace see the
workspace's native `AGENTS.md` twice (once natively, once in the bundle).

### 4.10 Identity, autodetect, interactive, TUI

- Short name `her`; status color: any unused hex (spike: pick one, e.g. teal family
  clear of Grok `#00C8D7` and Muse `#3D9BFF`).
- Publish `llm_autodetect_cli_name() = "hermes"` but **omit `llm_autodetect_priority()`**
  in v1 (Muse/Grok precedent for caution), making Hermes strictly opt-in via
  `llm_provider.provider: hermes` / `%model:hermes/<model>` / alias pools later.
  The name is distinctive so autodetect would be *safe*; the reason to defer is
  behavioral (a Hermes run inherits the user's whole Hermes config — model, skills,
  MCP), not collision risk. Revisit after soak.
- `llm_interactive_cli()`: bare `hermes` REPL would stay open (no one-shot flag) —
  the tmux launcher wants a persistent session, so omit bypass args or pass none;
  set `menu_key` to a free letter and `model_args: ["-m", "{model}"]`. Verify the
  launcher contract before claiming support; marking `supported: False` initially is
  acceptable and honest if the REPL doesn't fit.
- Skill template context: `provider_name: "Hermes"`, `provider_tool_name:
  "Hermes"`, native ask-tool name from the spike's tool list.

### 4.11 Effort mapping: forward everything

Hermes `--reasoning` accepts `none/minimal/low/medium/high/xhigh/max/ultra` — a
superset of SASE's canonical levels — so `_EFFORT_CLI_ARGS` maps every level through
and nothing is rejected SASE-side (OpenCode precedent: forward, let the CLI validate).
`none`/`minimal`/`max` need no special rejection logic, unlike Grok.

## 5. Risks and what the spike must verify (before committing to the design)

1. **Stream-json stability:** confirm event shapes (`tool_use.input` availability,
   `result.tokens` keys, `session_id` presence) against installed Hermes; pin the
   Hermes version that passes.
2. **`--query-file -` + `--format stream-json` + `--oneshot` compose** on one command
   line (docs imply yes; run it).
3. **`--ignore-rules` + `--source tool` + `--in`** accepted together on the chat
   one-shot path (all documented; confirm no `--tui`-style conflicts).
4. **`hermes --version` output format** (default semver regex vs. custom
   `version_regex`) and `hermes update` argv for `self_update_argv`.
5. **Exit-code and failure-wording capture** for retry/limit patterns (need 2–3 real
   failures: bad model, rate limit, billing wall).
6. **Skill dir join semantics** for `llm_skill_deploy_subpath` (`.hermes/skills`?).
7. **Cold-start cost:** Hermes boots a Python agent + session DB per run; measure
   one-shot latency vs. Codex/Claude — if it dominates short turns, document it and
   consider `--max-turns` budget guidance, not a SASE-side timeout change.
8. **Config inheritance surprise:** a SASE run inherits the user's Hermes default
   model/provider/skills/MCP. Decide the v1 contract explicitly (recommendation:
   `--ignore-rules` always; user config otherwise honored and documented as a
   feature — "your Hermes, supervised" — not a bug).

## 6. Implementation plan (phased; v1 is the shippable slice)

- **Phase 0 — spike (no SASE changes):** install Hermes in a scratch env, verify §5
  items 1–6, record exact argv, event samples, version string, and failure wording.
- **Phase 1 — minimal bundled provider:** `hermes.py` + `_subprocess_hermes.py`
  (stream-json parse → reply/usage/exit), entry point, `models.yml` seeds, auth
  evidence, script install metadata, `SASE_HERMES_PATH` + `SASE_HERMES_{LARGE,SMALL}_ARGS`
  env parity, directive + `--ignore-rules` prepend, docs page, `test_hermes_*`
  mirroring the Muse/Grok suites. Opt-in only.
- **Phase 2 — fidelity:** `_tool_call_hermes.py` name map, interrupt/resume via
  `--resume`, retry + usage-limit patterns from live captures, wait-guard
  (`ends_with_wait_claim`-equivalent), teardown watchdog wiring (shared helper).
- **Phase 3 — citizenship:** `hermes usage --json` probe collector + capabilities,
  skill deploy subpath + template context, TUI color/menu, size-alias pool proposal,
  autodetect-priority proposal, `just fix` model-table regen + `just check`.

## 7. Recommendation restated

Build Hermes as a **bundled, opt-in, chat-path provider** per §1 — not as an external
plugin (the value is first-class `sase doctor`/`agent-cli`/TUI citizenship, and core
owns no provider-specific branching either way, so bundling costs nothing
architecturally), and not via `-z` (which blinds tool-call and usage telemetry).
The design reuses every shared harness seam (stdin prompt transport, JSON-line
streaming, interrupt monitor, completion watchdog, explicit instruction delivery,
`effort_cli_args`, retry/limit config) and adds exactly one provider-shaped unit of
new code. The two genuine unknowns — stream-json drift and Hermes-side model-ID churn —
are contained by the Phase 0 spike and by routing all model selection through
`--model` passthrough rather than SASE-side enumeration.

## Sources

- SASE `4b7b981532`: `src/sase/llm_provider/{base,muse_provider,grok,opencode,
  _hookspec,_subprocess_muse,model_manifest}.py`, `models.yml`, `pyproject.toml`
  (`sase_llm` entry points), `src/sase/agent_clis/detect.py`,
  `docs/contribute/llm-invocation.md`, `docs/reference/providers/{index,plugins,
  grok,muse}.md`.
- Hermes `8f5693af41`: `website/docs/reference/{cli-commands,model-catalog}.md`,
  `hermes_cli/{oneshot,_parser,main}.py`, `hermes_constants.py`, `README.md`.
- Pointer-level only: `sase/repos/research/202604/sase_vs_hermes_agent.md`,
  `sase/repos/research/202609/sase_vs_hermes_agent/`,
  `sase/repos/research/202610/can_hermes_replace_sase/`.
