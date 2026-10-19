# Adding Pi as a fully supported SASE LLM provider

> **Research query:** How should SASE add [pi](https://github.com/earendil-works/pi)
> (`earendil-works/pi`) as a new, fully supported LLM provider? Review the prior
> sidecar research on pi, study the current host contract, and recommend an
> implementation path.

## Bottom line

Ship Pi as an **in-tree built-in** `sase_llm` provider, in the same class as Grok
Build and Muse Code. Host the user's existing Pi; do not reimplement it.

**v1** is a JSON-mode adapter with explicit per-invocation instruction delivery:

- Invoke `pi --mode json` in the claimed workspace.
- Deliver the rendered instruction bundle through `--append-system-prompt <file>`
  and suppress native `AGENTS.md` / `CLAUDE.md` discovery with `--no-context-files`.
- Treat `agent_settled` as the end of the turn. Inspect the JSONL event stream;
  exit code 0 is not success.
- Persist `--session-dir` / `--session-id` under the run's artifacts so retries,
  wait-claim continuations, and `sase instructions verify` reuse one session file.
- Pass the user prompt as `@<file>` after `--` so large prompts never hit argv
  limits.
- Omit `llm_autodetect_priority` (`pi` is a generic binary name).
- Keep Pi out of shipped size-alias pools until doctor and auth checks are solid.

**v2** is a `sase-pi` Pi extension loaded with an extra `-e` (user extensions still
load) that mechanically enforces host-owned completion, helper-vs-root declaration,
and stranded wait-claims.

**v3** is RPC, only after a decision record for in-turn steering. Each SASE turn
still launches a fresh Pi process against the same session file.

This updates the 2026-10-11
[SASE for pi users](sase_for_pi_users/sase_for_pi_users.md) ranking. That report's
"first-class pi provider" remains the right product. Its claim that Pi's native
`AGENTS.md` loading is enough for instruction delivery is stale: SASE now renders a
per-invocation bundle and adapters must deliver it through an explicit channel.

## Recommended solution

Implement an in-tree `PiProvider` following the Muse module split for JSONL and
wait-claim, and the Claude/Grok pattern for explicit instruction delivery.

| Piece | Choice |
|---|---|
| Placement | Built-in `sase_llm` entry point in `pyproject.toml` |
| Host mode | `pi --mode json` (one invocation, then exit) |
| Instruction channel | `pi.append_system_prompt` via `--append-system-prompt` + `--no-context-files` |
| Flag | `sase flag new pi_explicit_instructions -k sunset` |
| Session | SASE-owned `--session-dir` under artifacts + `--session-id` |
| Prompt transport | `@<0600 temp file>` after `--` |
| Autodetect | Omit; opt-in like grok/muse |
| Menu key | `p` (free) |
| Short name | `pi` |
| Skills | `llm_skill_deploy_subpath` → `.pi/agent` |
| Install | npm `@earendil-works/pi-coding-agent`; `self_update_argv: ["update"]` |
| Models | Curated `provider/id` catalog + passthrough; OpenCode is the analog |
| Effort | `--thinking` (`none`→`off`; `minimal`/`low`/`medium`/`high`/`xhigh`/`max` 1:1) |
| Min version | 1.3.0 |
| sase-core | No wire change for v1 |
| Size aliases | Leave out of v1 |
| Usage probe | Leave out of v1; parse JSON `usage.cost` later |

Suggested v1 argv:

```text
pi --mode json
   --append-system-prompt <materialized-bundle>
   --no-context-files
   --session-dir <artifacts>/pi-sessions
   --session-id <uuid>
   --name <agent-name>
   --model <provider/id>          # when SASE resolved a model
   --thinking <level>             # when effort is set
   --approve                      # registered/trusted project clones
   --
   @<prompt-file>
```

`--system-prompt` replaces Pi's preamble; never pass it. `-ne` would drop the
user's extensions; never pass it in v1. `--no-session` would throw away resume;
never pass it for a SASE turn.

## Question and scope

The user wants Pi **fully supported**, not a proof-of-concept plugin. This note
answers:

1. What "fully supported" already means in SASE's Python surfaces.
2. Which Pi host mode matches the single-turn adapter contract.
3. How instruction bundles, sessions, models, skills, doctor, and docs have to
   change.
4. What the 2026-10-11 pi research still gets right, and what 1.2.0 / 1.3.0 plus
   SASE's explicit-delivery cutover change.

This is a source-and-docs review. No live Pi model calls, extension-compatibility
tests, or npm-gallery recrawl were run.

## What "fully supported" means today

A `sase_llm` entry point is necessary and not sufficient. Grok and Muse show the
in-tree bar.

### Plugin hook contract

`LLMHookSpec` in `src/sase/llm_provider/_hookspec.py` is the adapter surface.
Core dispatch is `llm_invoke` and `llm_resolve_model_name`. Metadata hooks are
called per instance by the registry. A fully supported provider implements:

- Identity: `llm_provider_name`, `llm_provider_short_name`
- Catalog: `llm_known_model_names`, `llm_model_short_aliases`, optional advisories
- Instruction delivery: `llm_instruction_delivery` returning explicit slots
- Skills: `llm_skill_template_context`, `llm_skill_deploy_subpath`
- CLI: `llm_autodetect_cli_name`, `llm_install_metadata`, `llm_interactive_cli`,
  `llm_auth_evidence`
- Failure policy: `llm_default_retry_config`, optional usage-limit config
- Optional: usage probe, sync ceiling, hidden-from-picker flags

`SASE_<PROVIDER>_PATH` is derived automatically
(`provider_path_env_var("pi")` → `SASE_PI_PATH`). Nested `%model` strings use
`split("/", 1)` in `registry.py`, so `pi/anthropic/claude-sonnet-4-6` already
routes as provider `pi` and model `anthropic/claude-sonnet-4-6` once `pi` is
registered. Unknown rest is passthrough.

### Hardcoded Python lists

Several instruction and docs surfaces name providers in tuples, not via entry
points:

| Surface | Current set | File |
|---|---|---|
| `sase instructions verify` known providers | claude, codex, grok, muse, agy | `src/sase/instructions/run_index.py` `_KNOWN_PROVIDERS` |
| Session discovery | per-provider finders (claude/codex/grok/muse) | `run_index.py`, `coverage_sessions.py`, `_verify_observers.py` |
| Single-turn directives | agy, claude, codex, grok, muse | `src/sase/instructions/directives.py` `DIRECTIVE_PROVIDERS` |
| Explicit-delivery sunset flags | claude, codex, grok, muse | `src/sase/feature_flags/registry.py` |
| Bundled model catalog | agy, claude, codex, grok, muse, opencode, qwen | `src/sase/llm_provider/models.yml` |
| Channel ids | `claude.*`, `codex.*`, `grok.rules`, `muse.prompt_prefix` | `instruction_delivery.py` |
| Docs index / agent-clis table | the seven user-facing CLIs | `docs/reference/providers/` |
| `default_config.yml` comment | claude, codex, qwen, opencode, agy, grok, muse, fakey | `src/sase/default_config.yml` ~1727 |
| Interactive menu-key tests | c, x, a, q, o, g, m | `tests/llm_provider/test_interactive_cli_metadata.py` |

An external plugin can invoke. It cannot appear on those surfaces without
in-tree edits. "Fully supported" therefore means an in-tree provider plus those
edits.

`docs/contribute/plugin-api.md` still says additional providers belong in
external packages. Grok and Muse already shipped in-tree. When Pi lands, update
that sentence to list Pi with the other bundled CLIs. The plugin group remains
the right home for third-party harnesses that SASE will not verify, document, or
flag.

### Closest templates

| Concern | Closest existing adapter |
|---|---|
| JSONL host mode, prompt file, wait-claim continuation | Muse (`muse_provider.py`, `_subprocess_muse.py`, `_tool_call_muse.py`) |
| Explicit system-prompt file + native suppression | Claude (`--append-system-prompt-file`) |
| Explicit delivery with a sunset flag, generic binary name, omit autodetect | Grok (`grok.py`; no `llm_autodetect_priority`) |
| Nested `provider/id` catalog | OpenCode (`models.yml` `opencode:`) |
| Doctor identity for a colliding CLI name | Grok (`checks_deep_providers.py` `_GROK_VERSION_RE`) |
| Skill deploy off the default `.{provider}` | Muse (`.config/muse`) |

Recommended module split, mirroring Muse's size (~2k lines across modules, 9
test files) rather than Grok's single 575-line file:

- `src/sase/llm_provider/pi.py` — class, metadata, invoke loop, flag, effort
- `_subprocess_pi.py` — JSONL parser (`agent_settled`, deltas, usage, errors)
- `_tool_call_pi.py` — `tool_execution_*` → SASE tool-call records
- `_pi_directive.py` — single-turn directive text
- `_pi_launch.py` — executable resolve, prompt file, session dir, argv

sase-core owns the instruction-manifest wire and does not hardcode channel ids.
v1 stays in Python. No `sase-core-revision.txt` bump is required unless a later
phase adds a shared cost/event schema.

## What Pi is in 1.3.0

Checkout: `gh:earendil-works/pi` at `d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03`
(2026-10-19). Package `@earendil-works/pi-coding-agent` **1.3.0** (released
2026-10-15). Node `>=22.19.0`. Bin name `pi`. Agent dir `~/.pi/agent`, overridable
with `PI_CODING_AGENT_DIR`.

Pi is a TypeScript single-agent harness: four default tools (`read`, `bash`,
`edit`, `write`), cheap TypeScript extensions, Agent Skills, and 30+ backends
through `pi-ai`. It owns the model loop, session file, and terminal UI. SASE
owns isolation, admission, waits, records, and host-owned landing. Complementary
layers; Pi is the inner loop.

### Host modes

From `packages/coding-agent/docs/cli-integration.md`:

| Mode | Lifetime | Use |
|---|---|---|
| Interactive | Until the user exits | tmux Agent / `sase agent-cli` |
| Print | One invocation, final text on stdout | Scripts that only need the last reply |
| JSON | One invocation, JSONL events, then exit | Structured host |
| RPC | Long-lived stdin/stdout JSONL | Bidirectional control |
| SDK | In-process Node/Bun | TypeScript embeds |

JSON and RPC share event shapes (`docs/json.md`). `agent_end` is not completion;
retries, compaction recovery, and queued work can follow it. **`agent_settled`**
is the terminal event. A failed or aborted assistant response appears in the
JSON stream and does not by itself produce a nonzero exit. Print mode is the
wrong host: no tool-call stream, and since 1.2.0 a `length` stop reason exits 1
after writing a partial reply.

JSON accepts `@file` prompt arguments. RPC rejects `@file`. JSON is the right
first host mode for SASE's large instruction bundles and prompts.

### Flags the adapter will use

From `docs/cli.md` and `src/cli/args.ts`:

- `--mode json`
- `--append-system-prompt <text|path>` (repeatable; existing path is read as a
  file, otherwise treated as literal text — `resource-loader.ts` uses
  `existsSync`)
- `--no-context-files` / `-nc` — disables `AGENTS.md` / `CLAUDE.md` discovery
- `--session-id`, `--session-dir`, `--fork`, `--name`
- `--model <pattern>` (`provider/id` and optional `:<thinking>` suffix)
- `--provider <name>` (requires `--model`)
- `--thinking off|minimal|low|medium|high|xhigh|max`
- `--approve` / `--no-approve` — project trust for `.pi/` resources
- `-e` / `--extension` (repeatable); `-ne` still loads explicit `-e` paths
- `--` then `@path` for prompt files

`--model` since 1.3.0 prefers a credentialed provider when several match, and
otherwise reports the ambiguity. JSON mode cannot prompt for `--provider`. Pass
`provider/id` (or `--provider` plus `--model`) so lookup is unambiguous.

### Agent directory vs project `.pi`

User config lives in `~/.pi/agent/` (`settings.json`, `auth.json`, `extensions/`,
`skills/`, `SYSTEM.md`, `APPEND_SYSTEM.md`, …). Project `.pi/` loads after
project trust. Context files (`AGENTS.md`, `CLAUDE.md`) load from the agent
directory, cwd, and ancestors **without** project trust. That is why
`--no-context-files` is load-bearing for explicit SASE delivery: otherwise the
committed workspace `AGENTS.md` projection is injected beside the bundle.

Sessions default to
`~/.pi/agent/sessions/--<cwd-path>--/<timestamp>_<id>.jsonl` and are grouped by
cwd. A successor SASE turn in a different numbered workspace would miss that
file. `--session-dir` must be an absolute artifacts path.

### Safety

Pi has no permission system. `--approve` trusts project-local extensions
(executable TypeScript). Auto-approving a clone of a project the user already
registered is reasonable. Auto-approving a newly opened external repo is not.
v1 can key `--approve` on "this is a SASE-managed project clone"; a later
per-project trust setting is the durable form.

## Prior research and what changed

[research:202610/sase_for_pi_users/sase_for_pi_users.md](sase_for_pi_users/sase_for_pi_users.md)
(consolidated 2026-10-11, Pi 1.1.0 / `96abe9a5ad45`) ranked a first-class Pi
provider first, a `sase-pi` extension second, and a pi-user on-ramp third. It
told SASE to host Pi, start with JSON then RPC, and keep no hidden daemon across
turns.

That ranking still holds. Three facts have moved.

### 1. Explicit instruction delivery is now the contract

The 10-11 report said Pi natively loads `AGENTS.md` / `CLAUDE.md`, so no extra
instruction channel was needed. SASE has since cut over to per-invocation
bundles (`instructions-per-invocation`, `readable-agents-md`). The committed
`AGENTS.md` is a readable projection. A SASE run's instructions are the rendered
bundle, delivered once through an adapter-owned channel, with SASE-owned native
files suppressed.

The adapter contract (`docs/contribute/instruction-bundle-internals.md`):

1. Deliver the slot's text once through the channel.
2. Suppress SASE-owned native instruction files.
3. Drop the legacy directive, because the bundle already carries
   `pkg.provider.<p>`.

For Pi that is `--append-system-prompt <materialized file>` plus
`--no-context-files`. `--append-system-prompt` appends after Pi's own preamble
(keep Pi's tool list). `ActiveInstructionDelivery.materialize()` already writes
a private 0600 file; hold that context manager around the subprocess.

`--no-context-files` also suppresses `~/.pi/agent/AGENTS.md`. Users who keep
cross-project notes there should move them to `APPEND_SYSTEM.md` (still loaded)
or SASE home memory. Optionally, v1 may re-append a present agent-dir
`AGENTS.md` as a second `--append-system-prompt` so that Pi-specific file is not
lost.

Sunset flag `pi_explicit_instructions` (kind `sunset`, default on), created only
with `sase flag new`. Off branch: omit `--no-context-files`, pass only the
legacy single-turn directive through `--append-system-prompt`, native context
files load. Both-states tests are required.

Channel id `pi.append_system_prompt` matches `CHANNEL_RE`
(`^[a-z0-9_]+\.[a-z0-9_]+$`). Subagent slot `none`, same as Grok/Muse. Pi
helpers are separate `pi --mode json` processes; v2's extension enforces
`helpers-return-roots-declare`.

### 2. Pi 1.2.0 / 1.3.0 churn

Two minors in four days (1.2.0 on 2026-10-12, 1.3.0 on 2026-10-15). Host-contract
changes that matter:

- Print-mode `length` cutoff now exits 1 (still the wrong host mode).
- `--model` prefers a credentialed provider; JSON cannot prompt.
- Resumed sessions keep their active tools.
- `before_agent_start` now fires for extension-triggered runs and the session
  counts as busy while a run starts (v2 extension authors must check
  `messageType`).
- Internal packages are pinned to exact versions.

The JSON/RPC/`agent_settled` vocabulary is stable from 1.1.0. Pin doctor to
**>= 1.3.0** and cover the adapter with a recorded JSONL fixture. Expect
point-release breakage.

### 3. Session resume is a SASE advantage over Muse

Muse has no headless resume; wait-claim and interrupt paths reconstruct the
prompt. Pi persists a JSONL session tree and accepts `--session-id` on a later
process. v1 should continue wait-claim and interrupt cycles on the **same**
session file with a short nudge prompt. That preserves tool fidelity and the
prompt cache, which is what the 10-11 report wanted from native fork/resume.

Do not keep an RPC daemon across SASE turns. The session *file* is the
continuity. That matches `single-turn-agents` and
`adapters-normalize-harnesses`.

## Alternatives

### A. External `sase_llm` plugin package only

The hookspec is designed so a third-party package can invoke. Plugin-api.md
points additional providers there.

A plugin cannot land on `_KNOWN_PROVIDERS`, `DIRECTIVE_PROVIDERS`,
`models.yml`, the sunset-flag registry, `sase instructions verify` observers,
or `docs/reference/providers/`. Those are the definition of fully supported.
Use a plugin only as a private spike, then fold it in-tree.

### B. RPC as the v1 host

RPC is required for steer, follow-up, abort, and live model switching. It is
long-lived, rejects `@file`, and needs an event listener installed before
`prompt` (`RpcClient.promptAndWait` exists for TypeScript, not Python). JSON
already matches "all prompts up front, stream events, exit." Share one event
normalizer so v3 RPC reuses v1 parsing.

### C. Print mode

`--print` is smaller and now fails closed on `length`. It exposes no
tool-call stream, no usage events, and no `agent_settled`. SASE's live reply
and wait-claim need the JSONL vocabulary.

### D. In-process SDK / Pi Durable

The SDK embeds Pi in Node/Bun. SASE's host is Python; the adapter contract is a
process boundary. Pi Durable is marked experimental, one-process-per-storage,
API-unstable. Both compete with hosting Pi.

### E. `-ne -e sase-pi` as the v1 sandbox

`-ne` plus an explicit `-e` loads only the SASE extension. That strips the
user's `~/.pi/agent/extensions`, which is the opposite of "preserve the user's
Pi." v1 loads the user's extensions. v2 adds `-e <sase-pi>` **without** `-ne`
so the extension's `tool_call` guard still blocks `git commit` / `gh pr create`
even when other extensions are present.

### F. Native `AGENTS.md` discovery (agy/qwen/opencode style)

Leaving Pi on `inherits_native` would load the committed projection plus
ancestor `CLAUDE.md` files, which load regardless of project trust. That
duplicates the bundle and misses the per-invocation render. Claude, Codex, Grok,
and Muse already moved off this path. Pi should ship on explicit delivery from
day one.

### G. Put Pi in shipped size aliases immediately

`@xsmall` already includes muse; `@small`/`@medium` include grok and muse;
`@large`/`@xlarge` include grok. Adding `pi/...` would route launches to
whatever `pi` binary is on PATH, including a colliding namesake, before doctor
identity lands. Add Pi to alias pools only after the identity check and a
credentialed `pi auth check` exist.

## v1 design details

### Invoke and event parsing

Follow Muse's JSONL loop:

1. Materialize the bundle (flag on) or the legacy directive (flag off).
2. Write the prompt to a 0600 managed temp file; unlink after the cycle.
3. `Popen` with stdout/stderr pipes. Stdout is reserved for JSONL; parse by
   splitting on LF only (`docs/json.md` warns that Node `readline` is wrong
   because U+2028/U+2029 are valid inside JSON strings). Python's
   `io` line iteration on `\n` is the matching split if you strip an optional
   CR; do not use `splitlines()`.
4. First JSON-mode record is the session header (`type: session`, version 3).
   `record_session` with its `id`.
5. Assemble live text from `message_update` deltas; replace with
   `message_end.message`.
6. Map `tool_execution_start/update/end` into SASE tool-call records.
7. Wait until `agent_settled`. Then inspect:
   - `agent_settled.aborted`
   - last assistant `stopReason` (`error`, `aborted`, `length`, …)
   - `auto_retry_end.success == false`
   - process return code (nonzero means the invocation threw)
8. A clean settle whose reply tail matches `ends_with_wait_claim` continues on
   the same `--session-id` with `MUSE_WAIT_CONTINUATION_NUDGE`-style text, up to
   the existing wait-claim cap. Same for interrupt messages.
9. Honor `SASE_LLM_LARGE_ARGS` / `SASE_PI_LARGE_ARGS` the way Grok/Muse do.

Do not treat `agent_end` as the end of the turn.

### Models

`models.yml` is the single edit point for built-in catalogs. Do not enumerate
Pi's 30+ backends. Curate a short OpenCode-style list of nested ids the picker
and `%model` completion should offer, with `tiers.large` / `tiers.small`, and
let unknown rest pass through.

Pi's product default lives in the user's `settings.json`. SASE's tier defaults
are SASE's own choice when the user launches `%model:pi` or `provider: pi`
without a rest. Document that. A later `pi/default` sentinel that omits
`--model` can preserve the user's settings.json default; it is not required to
ship v1.

Pass `--model <rest>` when SASE resolved a model. Pass `--thinking` from
`effort_cli_args` separately so effort is not baked into a `model:thinking`
suffix. Supported table:

```python
{
    "none": ["--thinking", "off"],
    "minimal": ["--thinking", "minimal"],
    "low": ["--thinking", "low"],
    "medium": ["--thinking", "medium"],
    "high": ["--thinking", "high"],
    "xhigh": ["--thinking", "xhigh"],
    "max": ["--thinking", "max"],
}
```

Pi's thinking set is a superset of Grok's. Explicit unsupported levels still
raise via `effort_cli_args`.

### Identity, install, doctor

`pi` collides the way `grok` and `muse` do (Raspberry Pi tooling, math CLIs,
unrelated npm bins). Mitigations, copied from those adapters:

- Omit `llm_autodetect_priority` so PATH presence never wins the default
  provider.
- `llm_autodetect_cli_name` returns `"pi"` for agent-cli and doctor.
- `SASE_PI_PATH` overrides the executable.
- Doctor identity: `pi --version` prints only `pkg.version` (a bare semver,
  `main.ts` `console.log(VERSION)`). That is too weak to identify Earendil's
  CLI. Add a help-text advisory: `pi --help` starts with
  `pi - AI coding assistant with read, bash, edit, write tools` and lists
  `--mode json` and `--append-system-prompt`. Pin minimum 1.3.0. Check Node
  `>=22.19` as a next-step when the binary is missing or too old.
- Auth evidence: `~/.pi/agent/auth.json` and `$PI_CODING_AGENT_DIR/auth.json`.
  Do not list all 30 API-key env vars. Optional later: `pi auth check --json`
  once a provider/model is known.
- Install metadata:

```python
{
    "manager": "npm",
    "package": "@earendil-works/pi-coding-agent",
    "scope": "global",
    "display_name": "Pi",
    "vendor": "Earendil",
    "docs_url": "https://github.com/earendil-works/pi",
    "self_update_argv": ["update"],
    "latest_version_package": "@earendil-works/pi-coding-agent",
    "version_argv": ["--version"],
}
```

Pi also has a curl installer and Nix. npm is enough for `sase agent-cli
install`, matching Grok. Interactive CLI: `menu_key: "p"`,
`bypass_args: ["--approve"]`, `model_args: ["--model", "{model}"]`.

### Skills

Default deploy is `.{provider}` → `~/.pi/skills/...`, which Pi does not scan.
Set `llm_skill_deploy_subpath` to `.pi/agent` so generated skills land at
`~/.pi/agent/skills/<name>/SKILL.md`. Chezmoi maps the first segment to
`dot_pi/agent/skills/...`. Optional additional subpath `~/.agents/skills` can
wait; Pi already discovers the Agent Skills locations on its own.

`llm_skill_template_context`: `provider_name` / `provider_tool_name` = `"Pi"`.
Pi has no built-in ask-user tool; omit `provider_native_ask_tool` or leave it
empty. Deploy generated skills only from a landed revision (`generated_skills.md`).

### Usage

JSON `message_update.usage` carries tokens and a priced `cost` object per
physical model. That is session cost, not a subscription window. Skip
`llm_usage_probe` in v1 (no grok-style billing collector). Surface `cost` from
the event stream into live reply / run metadata when that display exists.
Usage-limit patterns can be added later from captured live failures; do not
invent them.

### Completeness checklist

Every item is required for "fully supported":

1. `pyproject.toml` `[project.entry-points."sase_llm"]` `pi = "...:PiProvider"`
2. Provider modules + captured JSONL fixtures
3. `models.yml` `pi:` catalog, tiers, short aliases; `just fix` regenerates
   provider docs tables
4. `CHANNEL_PI_ROOT = "pi.append_system_prompt"` and `llm_instruction_delivery`
5. `sase flag new pi_explicit_instructions -k sunset` (do not hand-edit the
   registry); both-states tests
6. `DIRECTIVE_PROVIDERS` + `_DIRECTIVE_SYMBOLS` + display name
7. `_KNOWN_PROVIDERS` + `find_pi_sessions` (artifacts session-dir, not
   cwd-grouped `~/.pi/agent/sessions`)
8. `coverage_sessions.py`, `coverage_sources.py`, `coverage_diff.py`,
   `_verify_observers.py`
9. `docs/reference/providers/pi.md`; index, agent-clis table, plugin-api
   bundled list, `llm-invocation.md` source layout
10. `default_config.yml` comment: grok/muse/pi declare no autodetect priority
11. Interactive metadata test (`menu_key: p`, vendor Earendil)
12. Doctor identity advisory
13. tmux Agent catalog (falls out of `llm_interactive_cli`)
14. Generated-skill template context + deploy subpath
15. Wait-claim tests (`test_muse_wait_guard.py` is the template)

Docs routing (`docs_writing.md`): this is a new user-visible capability, so a
Reference page is required. `just fix` regenerates model tables. Do not append
a Getting Started narrative in the same change; file a guide-candidate follow-up
if an on-ramp is wanted (prior research rank 3).

## Phased delivery

### Phase 1 — managed inner loop (this recommendation)

In-tree JSON adapter, explicit delivery, session persistence, doctor identity,
verify observers, docs, tests. Success: a Pi user completes a landed SASE task
on their existing `auth.json` / `settings.json` / skills without editing them.

### Phase 2 — `sase-pi` extension

A TypeScript package loaded with `-e`, published later with the `pi-package`
keyword if a gallery on-ramp is wanted. Contents:

- `tool_call` guard: block `git commit`, `git push`, `git commit --amend`,
  `gh pr create`, and raw guarded recipes; name the sanctioned SASE path
- `agent_before_settle`: if no `sase_final` declaration, append a reminder and
  `continue: true` **once**
- Root token so helper `pi --mode json` children cannot submit a declaration
- Optional typed `sase_final` tool with `terminate: true`

Load with extra `-e`; do not pass `-ne`. This is the 10-11 report's strongest
mechanical idea and makes Pi the best-governed SASE provider.

### Phase 3 — RPC for live control

Behind a decision record for in-turn steering (the 10-11 report already called
for one). Same event normalizer. Still one process per SASE turn; RPC lives
only inside that turn. Native `--fork` for `#fork`/`#resume` when both sides
are Pi.

### Later, not blocking v1

Pi-user on-ramp and lite profile; cost footer from JSON usage; OSC 7501 from
the TUI; gallery bridge (`/sase run`, `/sase promote`); size-alias membership;
paired instruction-lift evals; crash-safe request-id persistence.

## What to leave out

- A SASE-native Codemode, virtual-model router, or REPL
- Replacing SASE internals with `pi-ai`, Chord, or Pi Durable
- A hidden Pi RPC process across SASE turns
- Claiming every Pi extension works under JSON/RPC (dialogs wait in-process;
  RPC stubs TUI methods)
- Listing every `pi-ai` backend in `models.yml`
- Plan mode or todos in SASE core

## Risks

| Risk | Mitigation |
|---|---|
| Point-release host-contract churn | Pin >= 1.3.0; JSONL fixtures; doctor version probe |
| Generic `pi` binary | Omit autodetect; help-text identity; `SASE_PI_PATH` |
| `--approve` loads project TypeScript | Approve only SASE-managed project clones in v1 |
| `--no-context-files` drops agent-dir `AGENTS.md` | Document `APPEND_SYSTEM.md`; optional re-append |
| JSON exit 0 on failed assistant | Inspect `agent_settled` / `stopReason` / retry events |
| Numbered workspaces vs cwd-grouped sessions | Absolute `--session-dir` under artifacts |
| User extensions fighting sase-pi | v2 guard fail-closed; v1 has no `-ne` |
| Instruction argv size | File-backed `--append-system-prompt` and `@file` prompt |
| Bundle + Pi preamble + `APPEND_SYSTEM.md` token cost | Expected; trim SASE instructions separately (prior rank 5) |

## Evidence base and confidence

Source review of the Pi checkout, the SASE provider stack, and the 2026-10-11
sidecar research. No Pi model calls, no live `pi --mode json` against a
credentialed backend, no extension-compatibility matrix.

| Source | Snapshot |
|---|---|
| Pi monorepo | `d2e7d8b7c1d31d3661f769d5caef7ba8d50c3e03` (2026-10-19), package 1.3.0, Node >=22.19.0 |
| Prior research | `research:202610/sase_for_pi_users/sase_for_pi_users.md` and `__final.md` (Pi 1.1.0 / 2026-10-11) |
| SASE | this checkout, package 0.18.0, built-ins agy/claude/codex/fakey/grok/muse/opencode/qwen |

High confidence on placement (in-tree), host mode (JSON), instruction channel
(`--append-system-prompt` + `--no-context-files`), session-dir under artifacts,
and omitting autodetect. Medium confidence on the curated `models.yml` list
(needs a live `pi --list-models` against Bryan's auth to pick tiers). Medium
confidence on doctor help-text identity until a colliding `pi` binary is
actually sampled on PATH.

## Sources

**Prior SASE research (audited reads):**

- `research:202610/sase_for_pi_users/sase_for_pi_users.md`
- `research:202610/sase_for_pi_users/sase_for_pi_users__final.md`

**Pi checkout** (`sase repo open gh:earendil-works/pi`):

- `packages/coding-agent/package.json` (1.3.0, bin `pi`, engines)
- `packages/coding-agent/CHANGELOG.md` (1.2.0, 1.3.0)
- `packages/coding-agent/docs/cli-integration.md`, `cli.md`, `json.md`,
  `rpc.md`, `configuration.md`, `skills.md`, `providers.md`, `security.md`,
  `session-format.md`, `extensions.md`
- `packages/coding-agent/src/cli/args.ts`, `src/main.ts`,
  `src/core/resource-loader.ts`, `src/config.ts`

**SASE checkout:**

- `pyproject.toml` `sase_llm` entry points
- `src/sase/llm_provider/_hookspec.py`, `instruction_delivery.py`, `grok.py`,
  `muse_provider.py`, `_wait_signals.py`, `_wait_guard.py`, `models.yml`,
  `registry.py` (`split("/", 1)`), `_registry_metadata.py`, `_effort_args.py`
- `src/sase/instructions/{run_index,directives,coverage_sessions,_verify_observers}.py`
- `src/sase/feature_flags/registry.py`, `src/sase/doctor/checks_deep_providers.py`
- `src/sase/main/_init_skills_sources.py`, `src/sase/default_config.yml`
- `docs/contribute/{llm-invocation,plugin-api,instruction-bundle-internals}.md`
- `docs/reference/providers/{index,agent-clis}.md`
- `tests/llm_provider/test_interactive_cli_metadata.py`,
  `test_grok_provider_invocation.py`

**Decisions and memory consulted:** `adapters-normalize-harnesses`,
`single-turn-agents`, `instructions-per-invocation`, `readable-agents-md`,
`helpers-return-roots-declare`, `rust-core-required`; reference notes
`sase_artifacts.md`, `docs_writing.md`, `generated_skills.md`, `sase_flags.md`.
