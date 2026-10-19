# pi as a fully supported SASE LLM provider: integration research

> **Research query:** Decide the best way to add pi
> ([earendil-works/pi](https://github.com/earendil-works/pi)) as a new, fully
> supported SASE LLM provider. Review the pi-related prior research in the
> research sidecar and verify its load-bearing claims against the current pi
> checkout and the current SASE source. End with a recommended solution.

## Bottom line and recommended solution

**Ship a `pi` provider in three phases: (1) a JSON-mode subprocess adapter
modeled directly on the existing OpenCode adapter; (2) a small `sase-pi`
extension, loaded with `-e` on every provider invocation, that turns SASE's
paragraph-level contracts (single-turn declaration, never commit, no raw
guarded recipes, helpers never declare) into pi lifecycle mechanisms; and
(3) a pi observer for `sase instructions verify` plus a cost/usage follow-up.
Defer RPC mode until live steering is actually designed; never keep a pi
process alive across SASE turns.**

Concretely, the work is:

1. **Phase 1 — JSON-mode provider (one epic).** New `src/sase/llm_provider/pi.py`
   (`PiProvider`, entry point `pi = "sase.llm_provider.pi:PiProvider"` in
   `pyproject.toml`), new `src/sase/llm_provider/_subprocess_pi.py` event
   normalizer reusing `stream_json_lines` from `_subprocess_stream.py`, a
   `models.yml` entry (or hook-direct answers, see
   [the model-catalog decision](#3-model-catalog-pi-has-30-providers-sase-wants-one-list)),
   skill deploy to `.pi/agent/skills` (+ `.agents/skills` additionally),
   install/interactive-cli/auth metadata, usage-limit patterns, and a
   `tests/test_llm_provider_pi.py` suite mirroring
   `tests/test_llm_provider_opencode.py` including a recorded event-stream
   fixture. Launch shape: `pi --mode json --session-dir <sase-owned>
   --session-id <agent> --model <pattern> [--thinking <level>] [--append-system-prompt …]
   "<prompt>"` with cwd set to the claimed workspace. Turn end is
   **`agent_settled`**, never exit code 0.
2. **Phase 2 — `sase-pi` enforcement extension (same epic or next).** A tiny
   TypeScript package, loaded via `-e`, providing: a typed `sase_final` tool
   whose handler returns `terminate: true`; an `agent_before_settle` guard
   that requests exactly one continuation when no declaration was submitted;
   a `tool_call` guard that blocks `git commit` / `gh pr create` / raw
   guarded-recipe argv with fail-safe (handler-throw-blocks) semantics; and a
   root-token check so non-root (helper-spawned) processes refuse
   `sase_final`. Plus a per-project trust setting governing `-a/--approve`.
3. **Phase 3 — proof and visibility.** A pi session observer
   (`observe_pi`) for `sase instructions verify` that replays the persisted
   system-message sections (pi's session format makes this exact, not
   inferred), and a home for pi's priced `cost` telemetry, which has no field
   in `InvokeResult` today.
4. **Explicitly deferred:** RPC-mode steering/follow-up/abort (needs a
   steering decision record first), a SASE-native Codemode, a virtual-model
   router, adopting pi-ai/Durable/Chord inside SASE, and any long-lived pi
   daemon shared across SASE turns.

The rest of this report is the evidence behind that recommendation. All
SASE paths below are relative to the SASE checkout; all pi paths to the pi
checkout listed in [Evidence base](#evidence-base-and-confidence).

## Prior research reviewed

The related file is `202610/sase_for_pi_users/sase_for_pi_users.md` (the
consolidated lead report of the earlier "SASE for pi users" swarm, with its
five researcher variants alongside). I read the consolidated base report only.
Its provider-relevant claims check out against today's trees, with three
updates that change the details (not the direction):

- **Provider count and roster changed.** The report says eight `sase_llm`
  providers; `pyproject.toml` still lists exactly eight
  (`agy`, `claude`, `codex`, `fakey`, `grok`, `muse`, `opencode`, `qwen`),
  but the module set has since grown (`muse_provider.py`,
  `_subprocess_agy.py`, `_subprocess_muse.py`, usage-probe hooks). The
  adapter-split pattern the report describes (`<name>.py` +
  `_subprocess_<name>.py` + optional `_tool_call_<name>.py`) is still the
  current convention — OpenCode is now the closest template for pi.
- **Pi moved fast.** The report pins pi at 1.1.0 (2026-10-07); the checkout
  in this workspace is at **1.3.0** with commits like "Durable and pi-ai
  telemetry" landing since. Two minor versions in eight days confirms the
  report's churn warning: pin a minimum pi version in `sase doctor` and test
  against a recorded event fixture, not a live pi.
- **`docs/agent_providers.md` no longer exists under `docs/`.** The report
  cites it for helper-coverage gaps ("sentence only" for Grok, absent for
  Muse/agy). The doc has moved or been removed; I verified the current
  contract surface directly from `src/sase/llm_provider/_hookspec.py` and the
  provider modules instead (see next section). The substance of the claim —
  that most SASE contracts ride on instruction text for most providers, and
  pi hooks could make them mechanical — survives: nothing in the current
  provider modules contradicts it, and pi's `tool_call` /
  `agent_before_settle` / `terminate: true` semantics are confirmed in pi's
  `extensions.md` and JSON/RPC docs (details below).

## 1. What "fully supported provider" means in SASE today

I derived this checklist from first principles in the current tree:
`pyproject.toml` entry points, `src/sase/llm_provider/_hookspec.py`,
`base.py`, `opencode.py` (the closest analog), `model_manifest.py`, the
`instructions verify` wiring, and `tests/test_llm_provider_opencode.py`.

### 1.1 Registration and invocation core (required)

- **Entry point.** One line under `[project.entry-points."sase_llm"]` in
  `pyproject.toml`, e.g. `pi = "sase.llm_provider.pi:PiProvider"`.
- **`LLMProvider` subclass** (`base.py`): the entire abstract surface is one
  method, `invoke(prompt, *, model_tier, suppress_output, model_override,
  options) -> InvokeResult`, where `InvokeResult` is just `{content, usage}`.
  Two near-free overrides: `invocation_option_args` (effort → CLI flags via
  the shared `effort_cli_args` helper) and `instruction_delivery`.
- **Pluggy hooks** (`_hookspec.py`) that make the provider a first-class
  citizen rather than a bare invoker:
  - identity/routing: `llm_provider_name`, `llm_provider_short_name`,
    `llm_resolve_model_name`, `llm_known_model_names`,
    `llm_model_short_aliases`, `llm_skill_template_context`;
  - fleet surfaces: `llm_skill_deploy_subpath` (+
    `llm_additional_skill_deploy_subpaths`), `llm_cli_status_color`,
    `llm_autodetect_priority` + `llm_autodetect_cli_name`,
    `llm_auth_evidence`, `llm_install_metadata`, `llm_interactive_cli`
    (these wire the provider into `sase agent-cli install`, `sase doctor`,
    and the tmux agent chooser with no further code);
  - robustness: `llm_model_advisories`, `llm_default_retry_config`,
    `llm_default_usage_limit_config`, `llm_sync_ceiling_seconds`,
    `llm_usage_capabilities`, `llm_usage_probe`.
- **A subprocess module** (`_subprocess_<name>.py`) for JSONL CLIs, built on
  the shared `stream_json_lines` loop in `_subprocess_stream.py` plus the
  live-reply/usage/diagnostic helpers in `_subprocess_artifacts.py` and
  `_subprocess_diagnostics.py`. OpenCode's parser is 155 lines; pi's will be
  similar size.
- **Tests** mirroring `tests/test_llm_provider_opencode.py`: provider-type
  check, model resolution, command construction (mocked `Popen`), failure
  surfacing, parser unit tests over recorded event lines, a fake-CLI
  end-to-end (artifacts written), and auth-evidence assertions.

### 1.2 Model catalog (a real decision, not boilerplate)

`model_manifest.py` loads a bundled `models.yml` (schema version 1) with
per-provider `models`, `short_aliases`, `tiers`, `supersedes`, `advisories`.
The module docstring is explicit that **third-party providers answer the
model hooks directly and never touch the manifest** — but a built-in pi
provider would normally take a manifest entry. A static list is the wrong
shape for pi: pi fronts 30+ providers plus user-registered custom and
virtual models, and its `--model` flag already accepts exact IDs, fuzzy
matches, `provider/id` scoping, and `:<thinking>` suffixes. Three options:

1. **Thin manifest entry (recommended):** tier defaults pointing at two
   stable, widely-credentialed IDs plus a couple of short aliases; everything
   else passes through `model_override` → `--model` untouched, exploiting
   pi's fuzzy matching. Small, honest, never blocks a user whose pi knows a
   model SASE never heard of.
2. **Dynamic catalog via `pi --list-models`:** accurate but slow, fragile
   (requires credentials to be fully informative), and a new failure mode on
   every launch path that resolves models. Reject.
3. **Full static catalog of pi's 30+ providers:** stale on arrival given
   pi's release cadence (1.1.0 → 1.3.0 in eight days). Reject.

### 1.3 Effort mapping (near-free)

SASE's canonical effort vocabulary (`src/sase/macro/effort.py`) is
`none, minimal, low, medium, high, xhigh, max`. Pi's `--thinking` levels
(`cli.md`) are `off, minimal, low, medium, high, xhigh, max`. The mapping is
1:1 except `none → off`, forwarded as `["--thinking", level]` through the
existing `effort_cli_args` helper (explicit-unsupported raises, default
falls back silently). Additionally, pi accepts `--model <pattern>:<thinking>`
suffixes and extension-registered virtual models — pass model strings
through verbatim and both keep working.

### 1.4 Instruction delivery (pi is the easy case)

Pi natively discovers `AGENTS.md`/`CLAUDE.md` from the working directory
upward, so launching pi with cwd set to the claimed workspace delivers the
workspace context files with no extra machinery. Two refinements:

- **SASE bundle text** (the rendered per-invocation bundle, which is *not* a
  context file pi would find) should travel via `--append-system-prompt`,
  which is repeatable and appends without replacing pi's short preamble.
  Do not use `--system-prompt` (it replaces the whole prompt) and do not
  fight pi's loader with `-nc/--no-context-files`.
- **Exactly-once audit** is genuinely achievable for pi, unlike current
  providers: pi's session file persists the full system prompt as named
  `sections` plus tool declarations in the first system message, with later
  patches (`session-format.md`, "SessionMessageEntry"). A new `observe_pi`
  in `src/sase/instructions/` can replay sections in order and compare
  against the delivered bundle hash — the same slot the verify aggregator
  already reserves per provider (`_verify_aggregate.py` orders
  `claude, codex, muse, grok, agy`; opencode/qwen are absent, so pi would be
  the first JSONL-CLI provider with exact verification).

### 1.5 What has no home yet: priced cost

`message_update` carries cumulative `usage` including a priced
`cost: {input, output, cacheRead, cacheWrite, total}` object — per-model,
per-physical-model cost that no SASE provider surfaces today
(`InvokeResult` has only token counters; the usage-artifact helpers record
tokens, not dollars). Options in increasing cost: (a) log pi's cost object
into the stderr/diagnostics channel of the run artifacts; (b) extend the
usage-artifact schema with an optional cost block (touches the shared
`_subprocess_artifacts.py` path, so it needs care); (c) full per-clan/epic
dollar rollups (the prior report correctly places this in `sase_core`, and
it is out of scope for provider support). Recommend (a) in Phase 1, (b) as
the Phase 3 follow-up.

## 2. Pi's machine surface: what I verified in the current checkout

All claims below were read in the pi checkout (`packages/coding-agent/`,
version 1.3.0) during this investigation, not carried over from the prior
report.

### 2.1 JSON mode is the correct first transport

- `pi --mode json "prompt"` runs the supplied prompts, writes strict-LF
  JSONL to stdout (diagnostics on stderr), and exits (`cli.md`, `json.md`).
  This matches SASE's single-turn contract exactly and reuses SASE's
  existing `stream_json_lines` reader — which I checked splits stdout
  strictly on `"\n"` at the byte level (`_JsonlPipe.feed`), satisfying pi's
  documented framing rule (split only on LF; never use Node-style readline
  semantics that also split on Unicode separators).
- **Exit code 0 means nothing about task success.** A failed or aborted
  assistant response appears in the event stream with no nonzero exit
  ("Inspect the events when success or failure matters",
  `cli-integration.md`). The adapter must therefore derive failure from
  events: `agent_settled` with `aborted: true`, `auto_retry_end` with
  `success: false` + `finalError`, provider `error` stream events, and the
  assistant `stopReason` (`error`/`aborted` on the final `message_end`).
  OpenCode's adapter already funnels non-zero exits into
  `CalledProcessError`; pi's needs the additional event-based failure
  check on the exit-0 path. This is the single most important correctness
  detail of the whole integration.
- **`agent_settled` is the turn boundary** (`json.md` event table):
  `agent_end` may be followed by retries, compaction recovery, steering, or
  follow-up work; only `agent_settled` means "no remaining automatic work."
  The normalizer must accumulate across `agent_end` boundaries and return
  only at `agent_settled` (or process exit, treated as abnormal if no
  settle was seen — record it as a diagnostic).
- **Authoritative text, not delta soup.** Unlike OpenCode's incremental
  `text` parts, pi emits `message_update` deltas for live display and then
  `message_end` with the complete message ("replace the whole partial
  message with `message_end.message` when it arrives"). The adapter should
  stream deltas to the live-reply file and build the returned content from
  `message_end` bodies — strictly better fidelity than the OpenCode parser.
- **Usage arrives free.** `message_update.usage` is the latest cumulative
  `{input, output, cacheRead, cacheWrite, totalTokens, cost}`. Accumulate
  the max (not the sum) per assistant response; sum across responses.
- **Tool visibility arrives free.** `tool_execution_start/end` carry
  `toolCallId/toolName/args/result/isError/durationMs`. SASE's
  `InvokeResult` has no tool channel, but the parser should still record
  tool calls into run artifacts — that is also what makes a future
  `tool_call` enforcement story auditable.

### 2.2 Session flags solve SASE's continuity problem without a daemon

- `--session-dir <dir>` overrides storage/lookup with highest precedence;
  default is `~/.pi/agent/sessions/` grouped by cwd (`sessions.md`,
  `configuration.md`). SASE must pass a SASE-owned `--session-dir` (e.g.
  under the agent's artifacts dir) plus `--session-id <agent-scoped-id>`,
  because successor turns can land in different numbered workspaces and a
  cwd-grouped lookup would otherwise fork across projects. Each SASE turn
  launches a fresh `pi --mode json` against the same session file — no
  standing process, consistent with the `single-turn-agents` and
  `adapters-normalize-harnesses` decisions.
- `--fork <path|id> [--session-id <new>]` implements native context fork;
  keep SASE's text-injection fallback for cross-provider forks, and label
  every fork context-only vs repo-state (pi's tree never rolls files back).
- `--append-system-prompt` (repeatable) is the bundle-delivery flag;
  `-e/--extension` (repeatable) loads the enforcement extension;
  `-a/--approve` vs `-na/--no-approve` scopes project-local trust;
  `--tools`/`--exclude-tools`/`--no-tools` select tools. **Restraint
  applies:** do not pass tool-selection flags in Phase 1 — Codemode, MCP,
  and the user's extensions stay under the user's pi settings.

### 2.3 Extension hooks make contracts mechanical (verified in source)

- `tool_call` handlers can mutate input or block execution, and **a handler
  failure blocks the tool as a fail-safe** (`extensions.md`, plus the
  `permission-gate.ts` example combining `tool_call` with fail-closed
  behavior). A guard blocking `git commit`, `gh pr create`, and raw guarded
  recipe argv is therefore a mechanism, not a paragraph — and it fails
  closed.
- `agent_before_settle` handlers can append entries and return
  `continue: true` for exactly one further model request
  (`extensions.md` lifecycle diagram and boundary table). That is precisely
  the "no declaration yet → remind once → continue once" guard for the
  single-turn declaration contract.
- A tool can return `terminate: true` to end the run after its batch; a
  typed `sase_final` tool that validates the declaration against a schema
  and terminates is the natural root-only declaration channel.
- Caveat I confirm rather than hand-wave: pi's helper story. Pi's own
  subagent example spawns `pi --mode json -p --no-session` children that
  inherit environment and context files — so the extension must distinguish
  root from helper (e.g. a root token injected only via the provider's `-e`
  invocation environment) and refuse `sase_final` off-root, mirroring
  `helpers-return-roots-declare`. Also, RPC mode stubs some TUI methods and
  extension dialogs wait in-process — certify the extension for JSON/print
  mode first; do not claim universal compatibility.

### 2.4 Doctor/auth/install wiring (verified in source)

- `pi auth check --provider <p> --model <m> --json` prints
  `{status: ready|not_ready|invalid, provider, reason}` with exit codes
  0/1/2 (`main.ts`, `cli/auth-check.ts`). For a 30-provider harness this is
  a better `sase doctor` / autodetect probe than any static
  `llm_auth_evidence` env-var list — recommend the hook carry the standard
  credential paths *plus* wiring doctor to the auth-check probe.
- `pi update` self-updates; npm package is
  `@earendil-works/pi-coding-agent`; Nix and curl installers exist. That
  fills `llm_install_metadata` directly (manager npm, self-update argv
  `["update"]`, docs `https://pi.dev/docs/latest`).
- Interactive chooser: bare `pi` opens the TUI; `llm_interactive_cli`
  `{menu_key, bypass_args: [], model_args: ["--model", "{model}"]}` follows
  the OpenCode precedent (no approval-bypass flag exists for the interactive
  surface; keep `-a` out of it).
- Skill deploy: user skills live in `<agent-dir>/skills/` (default
  `~/.pi/agent/skills/`), project skills in `.pi/skills/`, plus Agent Skills
  interop at `~/.agents/skills` and `.agents/skills` (`configuration.md`,
  `skills.md`). Recommend `llm_skill_deploy_subpath → ".pi/agent/skills"`
  with `llm_additional_skill_deploy_subpaths → [".agents/skills"]`.
- Autodetect: `llm_autodetect_cli_name → "pi"`; priority just below claude
  (0) and near opencode (18) — pi and opencode are both third-party CLIs a
  user may have installed without SASE; exact number follows the registry's
  existing ordering, default suggestion 17–19.

## 3. Decisions the implementer needs recorded

1. **JSON first, RPC later.** JSON and RPC share event shapes (`json.md` is
   the canonical reference for both), so one normalizer serves both phases.
   RPC buys steering/follow-up/abort/model-switching *within* a turn — but
   in-turn steering itself needs a product decision (the old Agents-tab `m`
   keybinding was removed without recorded rationale; the kill-and-redirect
   plumbing in `_subprocess_plain.py` still ships). Write the steering
   decision record before writing RPC code, not after.
2. **No daemon across turns.** One SASE turn = one `pi --mode json`
   process on a pinned session file. Rejected alternative documented with
   reason (standing daemons violate single-turn-agents; the session file
   already provides continuity).
3. **Model catalog: thin manifest entry + verbatim pass-through** (option 1
   in §1.2). Rejected: dynamic `pi --list-models` (slow, credential-gated),
   full static catalog (stale on arrival).
4. **Trust is per-project, not a blanket `-a`.** Auto-approving a clone of a
   registered project is reasonable; auto-approving newly opened or external
   repos is not, because `-a` loads executable project-local extensions.
   Default to `-na` except where the project record says trusted.
5. **Minimum-version pin + recorded fixture.** Given 1.1.0 → 1.3.0 in eight
   days with event-adjacent changes (telemetry), `sase doctor` should refuse
   pi below the validated floor, and parser tests must run against a
   checked-in JSONL fixture (the fakey precedent) so pi upgrades break tests
   before they break users.

## 4. Phased implementation sketch

**Phase 1 — provider slice (must include all of these to be "supported,"
nothing more):**
`pi.py` (all hooks in §1.1; effort via `effort_cli_args` with
`none → --thinking off`); `_subprocess_pi.py` (session-header capture,
delta→live-reply, `message_end` accumulation, cumulative-usage max-per-turn,
`tool_execution_*` artifact logging, `agent_settled`-gated return,
event-based failure on the exit-0 path); `pyproject.toml` entry point;
thin `models.yml` entry; usage-limit patterns mined from real pi output
(seed with `rate limit`, `quota`, `overloaded`, `529`, then tighten —
`test_llm_provider_opencode.py` shows the honest "unverified baseline"
comment convention); `SASE_PI_PATH` binary override + missing-binary error
following `_opencode_bin`; interrupt monitor + completion watchdog reuse;
`tests/test_llm_provider_pi.py` (command construction incl. session flags,
parser unit tests, fake-CLI e2e with artifacts, failure-surfacing tests for
exit-0-with-error-events).
Out of Phase 1: RPC, steering, cost schema, verify observer, gallery
package, on-ramp docs.

**Phase 2 — enforcement extension + trust setting** (the highest-leverage
follow-up; makes pi the best-governed provider): `sase_final` typed tool,
`agent_before_settle` one-continuation guard, `tool_call` fail-safe block
for commits/PRs/raw guarded recipes, root-token helper refusal, per-project
trust setting driving `-a`/`-na`. Dogfood by making the Claude PreToolUse
guard converge toward the same blocked-command list.

**Phase 3 — proof and visibility:** `observe_pi` for `sase instructions
verify` (replay system sections from the session JSONL; assert bundle hash
present exactly once); cost handling per §1.5; native `--fork` resume for
pi→pi `#fork`/`#resume`.

**Explicitly not recommended:** SASE-native Codemode or virtual-model
routing (pass pi's through; SASE owns no tool execution); replacing SASE
internals with pi-ai/Durable/Chord (shared logic belongs in `sase_core`;
Durable is experimental and single-process); Windows/binary packaging or
gallery bridge before Phases 1–2 land; claiming extension-dialog
compatibility.

## 5. Risks and open questions

- **Churn.** Pi ships breaking changes in minor releases. Mitigations: floor
  pin in doctor, recorded fixture, and keeping the normalizer tolerant
  (ignore unknown event types, as the OpenCode parser does).
- **Silent failure is the default failure.** Everything about pi's JSON mode
 exit semantics pushes toward treating green runs as successes. The
  event-based failure check (§2.1) is the one line of code that matters most;
  its tests should include: error stopReason with exit 0, `aborted: true`
  settle, `auto_retry_end success: false`, and exit-0-with-no-settle.
- **Model-tier defaults.** Any two IDs I name today may be wrong by
  implementation time; the implementer should pick tier defaults from
  `pi --list-models` output at build time and note the date. The pass-through
  design means a stale default degrades gracefully (user override always
  works).
- **Usage-limit wording** needs capture from real pi runs; the seed patterns
  above are guesses until confirmed.
- **Instruction-bundle size** (≈5–6k tokens of always-on SASE text) will now
  show up inside pi's own context meter and startup header. That turns bundle
  diet into a user-visible adoption issue — worth an eval pass (pi's own
  `evals` package documents a paired with/without method SASE could borrow),
  but it must not gate Phase 1.

## Evidence base and confidence

| Source | Snapshot |
|---|---|
| pi checkout (opened via `sase repo open gh:earendil-works/pi`) | 1.3.0, HEAD `d2e7d8b7c`; docs `cli.md`, `json.md`, `cli-integration.md`, `rpc.md` (skimmed), `sessions.md`, `session-format.md`, `extensions.md` (lifecycle + `permission-gate.ts` example), `configuration.md`, `skills.md`, `settings.md`; source `src/main.ts`, `src/cli/auth-check.ts` |
| SASE checkout (workspace) | `pyproject.toml` `sase_llm` entry points (8 providers); `src/sase/llm_provider/` — `base.py`, `types.py`, `_hookspec.py`, `opencode.py`, `_subprocess_opencode.py`, `_subprocess_stream.py`, `_subprocess_plain.py`, `model_manifest.py`, `instruction_delivery.py`, `main/_init_skills_sources.py`, `instructions/_verify_aggregate.py`; `tests/test_llm_provider_opencode.py` |
| Prior research | `202610/sase_for_pi_users/sase_for_pi_users.md` (consolidated base only; swarm variants deliberately not opened) |

Method: source and documentation review only — no pi model calls, no
benchmarks, no prototype adapter. Every pi behavior cited above was re-read
in the current checkout during this investigation; disagreements with the
prior report are noted inline in [Prior research reviewed](#prior-research-reviewed).
Confidence is high on the transport/event/normalizer design (documented
protocol + in-tree reader already compatible) and medium on effort around
the enforcement extension (one new TypeScript package plus trust plumbing).
The costliest unknown is not technical but taxonomic: tier-default model IDs
and usage-limit strings, both of which the phased plan isolates behind
pass-through and clearly-marked unverified baselines.

