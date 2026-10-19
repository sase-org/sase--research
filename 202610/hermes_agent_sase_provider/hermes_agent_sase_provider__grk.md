# Adding Hermes as a Fully Supported SASE LLM Provider

**Researcher:** grk (independent swarm report)
**Date:** 2026-10-19
**Question:** What is the best way to add Nous Research's Hermes Agent as a new, fully supported SASE LLM provider?

---

## Recommended solution

Ship Hermes as an **eighth built-in `sase_llm` provider** in the sase repo, wrapping the existing headless CLI:

```bash
hermes chat --oneshot --query-file <prompt> --format stream-json \
  --yolo --ignore-rules --source tool --in <workspace>
```

Do **not** start with an external plugin, an ACP client, or a model-only OpenAI-compatible proxy. Those paths either fail the "fully supported" bar or throw away the agent loop that makes Hermes worth wrapping.

Treat Hermes as **Muse's closest cousin, with OpenCode's nested model IDs**:

| Need | Copy from |
| --- | --- |
| Headless JSONL stream, wait guard, prompt-file transport, prompt-prefix instructions | Muse |
| Nested `provider/model` catalog strings, late/optional autodetect, opaque IDs | OpenCode |
| Script installer (`manager: "script"`), `--yolo`-class approval bypass | Muse install + Grok/Muse bypass |
| Sunset flag for explicit instruction delivery | `muse_explicit_instructions` / `grok_explicit_instructions` |
| Host-owned commits, workspaces, gates, finalizers | Every existing provider; do not reimplement |

Keep Hermes **out of the shipped size-alias pools** until the adapter has soaked. Select it with `%model:hermes/<id>`, `llm_provider.provider: hermes`, or `SASE_HERMES_PATH`. Putting a metered any-model router into `@large` would mix subscription-CLI economics with API spend.

Land in two slices. Slice 1 is a working coding worker under SASE governance. Slice 2 is "fully supported" parity (usage probe, isolated profile, explicit instruction flag, docs/doctor/agent-cli).

---

## What "fully supported" means here

SASE's bundled providers (Claude, Codex, agy, Qwen, OpenCode, Muse, Grok) are not "a subprocess that prints text." A fully supported provider is one that participates in the whole operator surface:

1. `sase_llm` entry point and pluggy hooks (`llm_invoke` plus identity/metadata).
2. Headless invoke that finishes in one SASE turn (single-turn contract).
3. Streamed events SASE can turn into live reply, tool-call rows, and token usage.
4. Model catalog in `models.yml` (names, short aliases, large/small tiers).
5. `%model:hermes/<id>` routing and effort flags.
6. `sase doctor` auth evidence and `sase agent-cli install/update`.
7. Interactive tmux Agent launch (`llm_interactive_cli`).
8. Instruction delivery plan (`llm_instruction_delivery`) plus a single-turn directive.
9. Retry patterns and usage-limit auto-disable patterns.
10. Docs: `docs/reference/providers/hermes.md`, index/agent-clis/splits, generated model tables.
11. Tests at Muse/Grok density (identity, invocation argv, stream, wait guard, metadata).

A third-party plugin can do (1)–(5). "Fully supported" is (1)–(11) in-tree, the way Grok and Muse shipped.

---

## Prior research this report builds on

Three sidecar reports already compared the products. None of them implemented a provider; all three pointed at this bridge.

| Artifact | Date | What it established |
| --- | --- | --- |
| `research:202604/sase_vs_hermes_agent.md` | 2026-04 | Different products. SASE wraps coding CLIs; Hermes owns its own loop. Do not copy Hermes's in-process adapters into SASE core. |
| `research:202609/sase_vs_hermes_agent/sase_vs_hermes_agent.md` | 2026-09-23 | First explicit recommendation: **Hermes as an 8th `sase_llm` provider**, citing `hermes --oneshot -q … --format stream-json`. |
| `research:202610/can_hermes_replace_sase/can_hermes_replace_sase.md` | 2026-10-09 | Same bridge, restated as "complement rather than rival." Hermes cannot replace SASE's governance; SASE should wrap Hermes as a worker. |

Instruction-delivery research (`research:202610/instruction_bundle_provider_delivery.md`) decides the channel: Hermes has **no** `--append-system-prompt-file` and **no** `--rules`. The Muse prompt-prefix pattern is the matching explicit channel.

This report re-checked Hermes at `8f5693af41` (2026-10-19, `v0.22.2+canary.20261019T071120Z-144-g8f5693af41`). The October 9 comparison pinned `908e4a4b44` / tag `abandoned-rc.3-v0.21.7`. The oneshot / `stream-json` / `--ignore-rules` / `--yolo` surface is still the right one; details below are from the newer checkout.

---

## The two products, in one sentence each

**Hermes is the agent.** It runs its own tool-calling loop over ~40 inference backends, with files, terminal, browser, cron, Kanban, memory, and skills. Its `AGENTS.md` says so.

**SASE is the control plane.** It has no LLM loop. It runs vendor coding CLIs as single-turn workers in numbered clones, then owns commits, gates, beads, and verification. `docs/reference/providers/index.md` currently lists seven bundled CLIs plus `fakey`.

Wrapping Hermes therefore creates a **nested agent**: SASE turn → Hermes loop → (Claude API / OpenRouter / local / …). That is the point. It is also the main design hazard. The adapter must make Hermes's loop *look like* Claude Code / Muse to SASE: one process, one prompt, one JSONL stream, one exit, no leftover wakes.

---

## SASE provider architecture (the contract to implement)

Providers live in `src/sase/llm_provider/`. Discovery is `importlib.metadata.entry_points(group="sase_llm")` in `pyproject.toml`. The class implements `LLMProvider.invoke` and a large `LLMHookSpec` surface (`_hookspec.py`).

Hooks a Hermes provider must implement to match Grok/Muse:

| Hook | Why |
| --- | --- |
| `llm_provider_name` / `llm_provider_short_name` | Registry id `hermes`; agent suffix **`hrm`** (`foo.hrm`). Taken: `cld cdx agy qwn opc mus grk fky`. |
| `llm_known_model_names` / `llm_model_short_aliases` | From `models.yml`, OpenCode nested-ID style. |
| `llm_invoke` | Subprocess the CLI. |
| `llm_instruction_delivery` | Explicit prompt-prefix channel behind a sunset flag. |
| `llm_autodetect_cli_name` | `"hermes"`. |
| `llm_autodetect_priority` | Optional; see selection below. |
| `llm_auth_evidence` | `~/.hermes/.env`, `~/.hermes/auth.json`; env vars for the common keys. |
| `llm_install_metadata` | `manager: "script"`, Muse-shaped. |
| `llm_interactive_cli` | `menu_key: "h"` (free: `c x a q o m g` taken), `bypass_args: ["--yolo"]`. |
| `llm_skill_template_context` / `llm_skill_deploy_subpath` | Default `.{provider}` already maps to `~/.hermes/skills`, which is Hermes's real skills root when `HERMES_HOME=~/.hermes`. |
| `llm_cli_status_color` | Pick a Nous gold/violet; keep it distinct from Grok cyan. |
| `llm_default_retry_config` | Rate-limit / 5xx / overload wording. Hermes oneshot already exits `75` (`EX_TEMPFAIL`) on dispatcher rate-limits. |
| `llm_default_usage_limit_config` | `"usage limit reached"` plus Hermes-specific quota strings. |
| `llm_usage_capabilities` / `llm_usage_probe` | Slice 2. `hermes usage --json` is the collector. |
| `llm_sync_ceiling_seconds` | Only if a hard kill is found; Hermes terminal `background=true` is the Muse-class problem, not a 600s kill. |

Shared orchestration (`_invoke.py`, preprocessing, finalizers, wait-signal module) stays as-is. **sase-core does not need a change:** provider ids are free strings (`is_provider_id` is a printable-string check), and usage observations are generic.

Hardcoded provider tuples that *will* need Hermes added when the flag is on, or when the provider is bundled:

- `pyproject.toml` `[project.entry-points."sase_llm"]`
- `src/sase/default_config.yml` comment listing providers
- `src/sase/instructions/directives.py` `DIRECTIVE_PROVIDERS` (once a directive exists)
- `src/sase/instructions/readout.py` / `run_index.py` known-provider orders
- `docs/reference/integrations/plugins.md` builtin `sase_llm` list
- `docs/_meta/splits/llms.yml` (new "Hermes Agent Integration" → `reference/providers/hermes.md`)
- `tests/tmux_agent/test_shell_script_parity.py` `_PROVIDERS`

Grok is ~575 lines of provider + a shared Anthropic stream reader. Muse is ~530 lines plus `_subprocess_muse.py` (~418) and `_muse_directive.py`. Hermes needs its **own** stream parser. Budget like Muse, not like a 50-line wrapper.

---

## Hermes CLI surface (what the adapter actually runs)

Verified in `website/docs/reference/cli-commands.md` and `hermes_cli/_parser.py` / `hermes_cli/stream_json.py` at `8f5693af41`.

### The orchestrator mode

`hermes chat --oneshot` (alias: `-Q` implies oneshot on a TTY) + `--query-file PATH` + `--format stream-json` is purpose-built for CI/orchestrators:

- `--query-file` reads the prompt from a file or stdin (`-`). Nothing is shell-interpreted. This is the right transport for SASE prompts (Muse already uses a 0600 tempfile because argv is too small and stdin is reserved).
- `--format stream-json` requires a query, implies `--quiet`, rejects `--tui`. Every stdout line is one JSON object. Diagnostics and `session_id:` stay on stderr.
- Event types: `system` (`subtype: init`, `model`, `session_id`) → `text` deltas → `tool_use` / `tool_result` → terminal `result` (`exit_code`, `text`, `tokens.{input,output,total,cache_read,cache_write}`, `duration_ms`, optional `error` / `replay_gap`).
- Oneshot exit codes: `0` completed, `1` failed/partial/budget, `130` interrupted, `75` tempfail for Kanban rate-limits.

`hermes -z <prompt>` is the wrong entry point. It prints only the final answer, with no tool events. Fully supported SASE needs the JSONL stream for the Agents-tab LLM Calls panel.

`agent/oneshot_footprint.py` already trims oneshot sessions: `skill_manage` is hidden, skill-authoring coaching is dropped, and `delegate_task` is capped and **waits for children in the same turn**. That last point is load-bearing for SASE's single-turn contract.

### Flags the adapter must pass

| Flag | Role |
| --- | --- |
| `--oneshot` | Answer and exit. Without it, `-q` on a TTY seeds an interactive session. |
| `--query-file <0600 tempfile>` | Prompt transport. Delete after the cycle, like Muse. |
| `--format stream-json` | Structured events. |
| `--yolo` (or `HERMES_YOLO_MODE=1`) | Bypass dangerous-command approvals. **Required.** Default `approvals.single_query_mode` is **`deny`**: without yolo, `git`, `rm`, and other engineering commands are blocked in oneshot. Same operator choice SASE already makes with Grok `--permission-mode bypassPermissions` and Muse `--disable-approval`. |
| `--ignore-rules` | Skip auto-injection of `AGENTS.md`, `SOUL.md`, `.cursorrules`, persistent memory, and preloaded skills. Required so SASE can deliver **one** instruction bundle. |
| `--source tool` | Hide the session from the user's session picker (oneshot already defaults to `oneshot`, which pickers hide; `tool` is the documented tag for third-party integrations). |
| `--in <workspace>` | Hermes's cwd flag (Grok's `--cwd`). SASE already cds into the clone; pass it explicitly. |
| `--model <id>` / `--reasoning <level>` | From SASE tier / `%model` / `%effort`. Hermes levels: `none\|minimal\|low\|medium\|high\|xhigh\|max\|ultra`. SASE has no `ultra`; map `max`→`max` and ignore `ultra` unless config extra-args request it. |
| `--toolsets …` | Restrict the loop (below). |

### Flags the adapter must not pass

| Flag | Why |
| --- | --- |
| `--worktree` / `-w` | SASE already isolated the workspace as a numbered clone. A nested git worktree fights claims and finalizers. |
| `--ignore-user-config` (default path) | Drops the user's model/provider routing. Credentials in `.env` would still load, but the configured default model would not. Prefer a dedicated profile (slice 2) over this flag. |
| `--safe-mode` | Implies ignore-user-config **and** ignore-rules **and** disables plugins/MCP. Too stripped for a coding worker. |
| `--resume` / `-c` | Each SASE invoke is a new session. Continuation is SASE's interrupt/wait-guard loop, not Hermes session resume. |
| `--tui` | Conflicts with `stream-json`. |

### Toolsets: what Hermes is allowed to be

Default `hermes-cli` includes file, terminal, web, browser, memory, skills, cronjob, delegation, clarify, computer_use, and Kanban (check_fn-gated). Several of those violate SASE's contract if left on.

**Slice 1 recommended toolsets:** `file,terminal,web,search,todo,skills` plus optionally `browser` and `delegation`.

| Toolset | For a SASE worker |
| --- | --- |
| `file`, `terminal`, `web`, `search`, `todo` | Keep. This is the coding surface. |
| `skills` | Keep `skill_view` / `skills_list`. Oneshot already hides `skill_manage`. |
| `browser` | Optional differentiator. Off until slice 1 is green, then opt-in via extra_args. |
| `delegation` | Oneshot waits for children. Keep only after confirming children cannot cron/commit/ask. Safer off in slice 1. |
| `clarify` | **Off.** SASE owns questions via `/sase_questions`. A blocking clarify on a dead turn is a stranded wait. |
| `cronjob` | **Off.** SASE owns monitors and the scheduler. |
| `kanban` | **Off.** SASE owns beads. |
| `memory`, `session_search` | **Off** unless HERMES_HOME is a SASE-owned profile (slice 2). Otherwise the worker writes into the user's personal Hermes memory. |
| `computer_use` | **Off.** |
| `image_gen` / `tts` / `video_gen` | Off unless a later extra_args opt-in. |

`hermes-acp` already drops `clarify`, `cronjob`, Kanban, computer_use, image_generate, tts. It is a useful *reference* for the toolset, not a reason to speak ACP.

### Terminal background is the Muse problem

`terminal(background=true)` plus `notify_on_complete` / `heartbeat` is Hermes's wait primitive. In oneshot the process exits; a notification after exit never reaches SASE. Same class of bug as Muse's managed bash.

Adapter rules (copy Muse, name the tools):

1. Prompt prefix: run commands in the foreground; `process_manage wait` is allowed *inside* the turn; anything that can outlast the process goes to `/sase_monitor` *before* it starts.
2. Shared `_wait_signals.py` + `_wait_guard.py` stranded-wait continuations (`SASE_HERMES_MAX_WAIT_CONTINUATIONS`, default 2).
3. Do **not** claim a sync ceiling unless a hard kill is measured. Hermes does not document Muse's 600s `shell` kill. Export `SASE_PROVIDER_SYNC_CEILING_SECONDS` only when the number is real.

### Approvals vs host-owned commits

`--yolo` lets Hermes `git commit` through `terminal`, the same way Claude/Grok/Muse can. SASE's guarantee is detection plus a fail-closed finalizer, not prevention (`decisions/host-owned-completion`). The single-turn directive must say: do not commit; submit `/sase_final`. That is existing policy, not a Hermes special case.

Default oneshot `single_query_mode: deny` without `--yolo` would *accidentally* block some git writes and also block legitimate `git status`/`git diff` depending on the dangerous-command list. Do not rely on deny-mode as a commit sandbox.

### Isolation: HERMES_HOME and profiles

Hermes state is profile-aware via `get_hermes_home()` (default `~/.hermes`). Cron, Kanban SQLite, memory, skills, and sessions all live there. If SASE invokes `hermes` against the user's default home:

- A coding worker can schedule cron, write MEMORY.md, or create Kanban cards in the user's personal agent.
- Parallel SASE agents contend on one `state.db`.

**Slice 1 (minimum):** `--ignore-rules` + `--source tool` + toolset lockdown. Accept shared home for auth/config only, and document the leak.

**Slice 2 (fully supported):** `hermes --profile sase` (or `HERMES_HOME=$SASE_ARTIFACTS_DIR/hermes_home` with auth copied/symlinked from the default profile). Profiles are islands by design (`hermes_cli` / profiles docs). A dedicated `sase` profile gives the worker credentials without the user's cron/memory. Do not call `hermes profile use sase` (that mutates the sticky default); pass `--profile` per invocation.

### Instruction delivery

Hermes context-file priority (`.hermes.md` → `AGENTS.override.md` → `AGENTS.md` → `CLAUDE.md` → `.cursorrules`) plus global `SOUL.md` will **double-load** SASE's committed `AGENTS.md` unless `--ignore-rules` is on. SASE's AGENTS.md is the full runtime projection; Hermes also progressively discovers subdirectory AGENTS.md as tools touch them.

Recommended channel, matching Muse and the E3 delivery research:

- `--ignore-rules` always for SASE-managed invokes.
- Root slot `explicit`, channel id `hermes.query_prefix` (new constant next to `CHANNEL_MUSE_ROOT`).
- Transport: prepend the rendered bundle to the query-file, with a delimiter (`--- User Prompt ---`), the way Muse wraps `--prompt-file`.
- Subagent slot `none` (Grok/Muse). Hermes `delegate_task` children get isolated context; they are not SASE helpers.
- Sunset flag `hermes_explicit_instructions`, created only with `sase flag new` (kind `sunset`, default on). Off branch: `--ignore-rules` dropped and native AGENTS.md discovery restored, which is a worse fallback than Claude's, so keep the Off branch tested and remove it after soak.

There is no Hermes equivalent of `--append-system-prompt-file`. Do not wait for one. An upstream feature request is a follow-up, not a blocker.

### Models

Hermes model ids are nested (`anthropic/claude-sonnet-4.6`, often with a separate `--provider openrouter`). SASE already supports this for OpenCode (`opencode/anthropic/claude-sonnet-4-5`).

Adapter policy:

- `models.yml` `providers.hermes.models`: a **curated** list (10–20 ids), not 40 backends × N models.
- Tiers: pick two ids that work on a stock Nous/OpenRouter install; document that `%model:hermes/<opaque>` passes through unknown ids as `--model`.
- Do **not** pass `--provider` unless `SASE_HERMES_INFERENCE_PROVIDER` or extra_args set it. Default to the user's Hermes config (`auto`).
- Short aliases for the curated ids.
- Leave shipped `@xsmall`–`@xlarge` pools unchanged in slice 1. Hermes is often metered; those pools exist to round-robin **subscription coding CLIs**.

### Usage

`hermes usage --json` returns windows with `used_percent` and `resets_at` for **`openai-codex`, `anthropic`, and `openrouter` only**. That is enough for a real probe on the three backends SASE users will actually hit through Hermes, and much simpler than Grok's ACP `_x.ai/billing` collector.

Per-turn tokens come from the stream-json `result.tokens` object (`input`, `output`, `cache_read`, `cache_write`). Map `cache_write` → SASE `cache_creation_input_tokens`. `--usage-file` is `-z`-only; ignore it.

A Hermes usage probe is slice 2. Slice 1 can ship with `llm_usage_capabilities` omitted (supported default: unsupported).

### Install and update

Hermes is a source installer, not npm:

```
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

`scripts/install.sh` at this pin:

- Default `HERMES_HOME=$HOME/.hermes`, `INSTALL_DIR=$HERMES_HOME/hermes-agent`.
- Binary: `$INSTALL_DIR/.hermes/bin/hermes`.
- Adds `~/.local/bin` to PATH.
- `--non-interactive` / `--skip-setup` skips TTY `hermes setup` and `hermes gateway install`.
- `--skip-computer-use` / `--skip-browser` shrink the install.

`sase agent-cli` script installs currently run `(bash, script.path)` with only `install_env`. There is **no `install_argv`**. Muse used env (`MUSE_UPGRADE_MODE=1`) because its installer honored env. Hermes's non-interactive switch is a **flag**.

Fully supported install therefore needs a small SASE extension: honor optional `install_argv` in `llm_install_metadata` (and thread it through `_registry_metadata._install_metadata` and `agent_clis.install`). Then Hermes declares:

```python
{
    "manager": "script",
    "display_name": "Hermes Agent",
    "vendor": "Nous Research",
    "docs_url": "https://hermes-agent.nousresearch.com/docs/",
    "install_script_url": "https://hermes-agent.nousresearch.com/install.sh",
    "install_dir": "~/.local/bin",
    "install_dir_env": "HERMES_INSTALL_DIR",
    "install_argv": ["--non-interactive", "--skip-computer-use"],
    "self_update_argv": ["update"],
    "version_argv": ["--version"],
}
```

Without `install_argv`, `sase agent-cli install hermes` would hang on `hermes setup </dev/tty`. That is a blocker for "fully supported," not polish.

The installer provisions its own Python (3.14 via PM). SASE only subprocesses the `hermes` binary. No venv collision.

---

## Options considered

### A. Built-in `sase_llm` adapter (recommended)

In-tree `HermesProvider`, Muse-class invoke, OpenCode-class model ids. Matches every "fully supported" provider SASE has shipped. Turns the overlap competitor into a supplier, which is what both 202609 and 202610 reports asked for.

**Cost:** a Muse-sized adapter plus a new JSONL parser, a wait guard, an install-argv extension, a sunset flag, and a docs page. Hermes CLI drift is real (canary HEAD moves daily); pin tests to parse-probed flags the way Grok pins `--no-plan`.

### B. External `sase_llm` plugin package

Same hooks, separate distribution. Docs already describe this (`docs/reference/providers/plugins.md`). It is the right shape for a *third-party* CLI. It is not "fully supported": doctor, agent-cli, models.yml, size-alias docs, instruction scoreboard, and tmux catalog all treat bundled providers as first-class. A plugin also cannot add `install_argv` to sase itself.

Use a plugin only as a **spike** to prove stream-json parsing, then promote.

### C. ACP client (`hermes acp`)

Hermes speaks Agent Client Protocol over stdio with the `hermes-acp` toolset. SASE has no ACP client. Building one would be a multi-provider project (Grok already uses ACP for *billing*, not for the agent loop). Reject as the Hermes path. Revisit only if SASE decides to speak ACP to several CLIs.

### D. Model-only: `hermes serve` / OpenAI-compatible proxy

Hermes can front models. SASE would then still need a coding harness (Claude/Codex/…) to *do* the work. That is not adding a provider; it is adding an inference backend behind an existing one. Out of scope.

### E. Reverse integration: SASE as a Hermes Kanban worker

Hermes docs still say external-CLI Kanban lanes are "not yet a paved path." That is Hermes's problem. It does not make Hermes a SASE provider.

### F. `hermes -z` minimal wrapper

Too little visibility for tool calls, usage, and wait detection. Reject.

---

## Recommended design (concrete)

### Identity

- Entry point: `hermes = "sase.llm_provider.hermes:HermesProvider"`
- Short name: `hrm`
- Path env: `SASE_HERMES_PATH`
- Extra args: `SASE_HERMES_LARGE_ARGS` / `SASE_HERMES_SMALL_ARGS` (existing `SASE_LLM_*_ARGS` pattern)
- Inference-provider override: `SASE_HERMES_INFERENCE_PROVIDER` (optional `--provider`)
- Autodetect: declare `llm_autodetect_cli_name = "hermes"` **and** a late priority (e.g. 40, after agy=30). `hermes` is a unique binary name, unlike `grok`/`muse`. If a wrong `hermes` appears on PATH, doctor should probe `hermes --version` the way Grok probes identity.

### Invoke argv (slice 1)

```
hermes chat --oneshot --quiet --format stream-json \
  --yolo --ignore-rules --source tool \
  --in <cwd> --query-file <tmp> \
  --model <id> [--reasoning <level>] \
  --toolsets file,terminal,web,search,todo,skills \
  [extra_args]
```

Prompt file: 0600 under SASE's managed tmp, prefix = single-turn directive (+ bundle when the flag is on) + delimiter + user prompt.

### New modules (mirror Muse)

```
src/sase/llm_provider/hermes.py              # façade
src/sase/llm_provider/hermes_provider.py     # class + hooks + invoke loop
src/sase/llm_provider/_hermes_directive.py   # single-turn text + wait-guard
src/sase/llm_provider/_hermes_launch.py      # executable, prompt-file, argv
src/sase/llm_provider/_subprocess_hermes.py  # stream-json parser
src/sase/llm_provider/_tool_call_hermes.py   # terminal/read_file/… → Bash/Read/…
src/sase/llm_provider/usage/hermes.py        # slice 2: hermes usage --json
```

Map Hermes tools onto canonical display names (same table Grok uses): `terminal`→`Bash`, `read_file`→`Read`, `write_file`→`Write`, `patch`→`Edit`, `search_files`→`Grep`, `web_search`→`WebSearch`, `web_extract`→`WebFetch`, `delegate_task`→`Task`, `todo_list`→`TodoWrite`.

### Feature flag

Create with `sase flag new hermes_explicit_instructions -k sunset`, not by hand-editing `FeatureFlag`. Both states tested. Off = native context-file discovery (bad, so the sunset Off branch exists only as rollback).

### Docs (docs_writing routing)

New user-visible capability → new Reference page `docs/reference/providers/hermes.md` (Grok/Muse are the templates). Link it from `reference/providers/index.md` and `agent-clis.md`. Add a splits row in `docs/_meta/splits/llms.yml`. Run `just fix` so generated model tables pick up `models.yml`. Do not start a Guide page; file a guide-candidate follow-up if a "add Hermes" getting-started step is wanted.

### Tests

Match `tests/llm_provider/test_muse_*.py` + `test_grok_*.py`:

- metadata/hooks (name, short name, color, install, interactive, auth)
- argv construction (oneshot, query-file, yolo, ignore-rules, source, in, toolsets, no worktree)
- stream-json parse (init, text, tool_use/result, result tokens, replay_gap, exit 75)
- wait-guard continuations
- instruction-delivery plan both flag states
- parse-probe for `--oneshot` / `--format stream-json` / `--ignore-rules` / `--yolo` (Grok's undocumented-flag pattern)

Do not run a live Hermes in unit tests. An optional manual `sase doctor -C llm.auth` path is enough until soak.

### sase-core / Rust

No wire change required. Do not add a provider enum.

---

## Phased delivery

### Slice 1 — "Hermes is a SASE worker"

Goal: `%model:hermes/<id>` launches a oneshot coding agent in a numbered clone, streams tool calls, and completes through `/sase_final`.

- Provider class, entry point, `models.yml` curated catalog, short name `hrm`.
- Invoke argv above, stream parser, tool-call mapping, interrupt/retry loop.
- Single-turn directive + wait guard.
- `--yolo --ignore-rules --source tool`; toolsets locked.
- Doctor auth evidence; `SASE_HERMES_PATH`.
- Reference page + splits + index links.
- Tests listed above (except usage probe).
- `install_argv` plumbing + script-install metadata so `sase agent-cli install hermes` is non-interactive.
- **Not** in size-alias pools. **Not** autodetect-first (late priority is fine).

Exit criterion: one real `%model:hermes/…` run on a SASE project that edits files, does not commit, submits `/sase_final`, and shows tool rows in the Agents tab.

### Slice 2 — "fully supported"

- `hermes --profile sase` (or per-run `HERMES_HOME`) so memory/cron/Kanban stay off the user's personal agent.
- `hermes_explicit_instructions` sunset flag and prompt-prefix bundle delivery.
- `llm_usage_probe` via `hermes usage --json` (codex/anthropic/openrouter).
- Usage-limit patterns + retry patterns from captured failures.
- Skill deploy verification into the SASE profile's `skills/`.
- tmux Agent interactive launch.
- Instruction scoreboard / `DIRECTIVE_PROVIDERS` membership.
- Optional `browser` toolset behind extra_args.

### Slice 3 — only after soak

- Membership in a shipped size alias, **weighted low**, and only for a subscription-backed Hermes backend (Nous Portal / Codex OAuth / Anthropic plugin), never a raw OpenRouter key.
- Upstream asks: `HERMES_NONINTERACTIVE=1` env for the installer; a `--system-prompt-file` flag so the bundle can leave the user message.
- ACP client, if SASE grows one for other CLIs.

---

## Risks and non-goals

| Risk | Mitigation |
| --- | --- |
| Nested agent ignores SASE instructions | `--ignore-rules` + prefix bundle; never rely on native AGENTS.md. |
| Worker mutates the user's Hermes home | Slice 2 profile; slice 1 documents the leak. |
| `--yolo` lets Hermes commit | Same as every other provider; directive + finalizer. |
| `clarify` / cron / Kanban leak | Toolset allow-list. |
| Background terminal after exit | Wait guard + directive. |
| Installer hangs on setup TTY | `install_argv --non-interactive`. |
| Model id `anthropic/foo` vs SASE `provider/model` | OpenCode nested-ID path: `%model:hermes/anthropic/foo`. |
| Usage probe covers 3 of ~40 backends | Document; probe those three; treat others as unsupported. |
| Canary CLI drift | Parse-probe tests; pin documented flags. |
| Size-alias spend | Keep Hermes out of pools until economics are chosen. |
| ACE screenshot goldens | Adding a provider to menus can dirty goldens; inspect, do not silently defer. |

**Do not:**

- Reimplement Hermes's tool loop inside SASE.
- Pass `--worktree`.
- Use `hermes -z` as the production invoke.
- Enable autodetect at priority 0 (would steal default from Claude/Codex on machines that have Hermes).
- Put Contributor-class or metered defaults on SASE's `large`/`small` tiers without an advisory.
- Hand-edit `FeatureFlag` (use `sase flag new`).
- Build an ACP client "while we're here."

---

## Implementation checklist (slice 1 + 2)

Copied against Grok/Muse so a later plan can tick it.

**Code**

- [ ] `pyproject.toml` `sase_llm` entry
- [ ] `hermes.py` façade + `hermes_provider.py` + launch/directive/subprocess/tool-call modules
- [ ] `models.yml` `providers.hermes`
- [ ] `default_config.yml` provider list comment
- [ ] `install_argv` support in registry metadata + `agent_clis.install`
- [ ] `sase flag new hermes_explicit_instructions -k sunset`
- [ ] `DIRECTIVE_PROVIDERS` / instruction readout orders
- [ ] Optional `usage/hermes.py` collector (slice 2)

**Docs**

- [ ] `docs/reference/providers/hermes.md`
- [ ] index + agent-clis + plugins builtin list + `docs/_meta/splits/llms.yml`
- [ ] `just fix` regenerated model tables

**Tests**

- [ ] metadata, argv, stream, wait-guard, instruction-delivery both flag states, install plan with `--non-interactive`

**Manual soak**

- [ ] `sase agent-cli install hermes` does not open a TTY wizard
- [ ] `sase doctor -C llm.auth -v` sees Hermes
- [ ] `%model:hermes/<id>` run lands a host-owned commit
- [ ] Default Hermes profile (cron, memory, session list) is unchanged after the run (slice 2)

---

## Sources

**Hermes Agent** (`sase repo open gh:nousresearch/hermes-agent`), HEAD `8f5693af41` (2026-10-19):

- `AGENTS.md`, `README.md`, `pyproject.toml`, `scripts/install.sh`
- `website/docs/reference/cli-commands.md` (oneshot, stream-json, `-z`, `hermes usage --json`, `--ignore-rules`, `--yolo`)
- `website/docs/reference/toolsets-reference.md`
- `website/docs/reference/tools-reference.md` (`terminal` background / heartbeat / `process_manage`)
- `website/docs/user-guide/features/context-files.md`
- `website/docs/user-guide/security.md` (`single_query_mode: deny`, YOLO)
- `website/docs/user-guide/features/acp.md`
- `website/docs/getting-started/installation.md`
- `agent/oneshot_footprint.py`, `hermes_cli/stream_json.py`, `hermes_cli/_parser.py`, `cli.py`

**SASE** (this workspace):

- `src/sase/llm_provider/{base,_hookspec,registry,grok,muse_provider,opencode,models.yml,instruction_delivery,_wait_guard}.py`
- `src/sase/agent_clis/install.py`, `src/sase/feature_flags/registry.py`
- `docs/contribute/llm-invocation.md`, `docs/contribute/plugin-api.md`
- `docs/reference/providers/{index,plugins,grok,muse,agent-clis,models}.md`
- `docs/reference/integrations/plugins.md`
- Decisions: `adapters-normalize-harnesses`, `single-turn-agents`, `instructions-per-invocation`, `host-owned-completion`, `rust-core-required`

**Prior sidecar research** (audited `sase artifact read`):

- `research:202604/sase_vs_hermes_agent.md`
- `research:202609/sase_vs_hermes_agent/sase_vs_hermes_agent.md`
- `research:202610/can_hermes_replace_sase/can_hermes_replace_sase.md`
- `research:202610/instruction_bundle_provider_delivery.md`
