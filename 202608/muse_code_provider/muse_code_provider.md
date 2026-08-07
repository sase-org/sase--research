---
create_time: 2026-08-07
updated_time: 2026-08-07
status: research
---

# Adding Meta Muse Code as a SASE LLM Provider

**Research question:** What would it take to add Meta's new Muse Code agentic harness as
a first-class SASE LLM provider, what integration risks are hidden behind the apparently
simple CLI wrapper, and what implementation approach should SASE take?

**Research date:** 2026-08-07. Muse Code is only two days old and is explicitly a beta.
Findings about its live binary and launcher should therefore be treated as a dated
compatibility snapshot, not a permanent upstream contract.

**SASE revision inspected:** `98114b0e20c757c52ec43c96d7dff616cbfdc38a`.

## Executive summary

This is feasible without changing SASE's core provider abstraction. Muse Code has the
exact basic surface a SASE provider needs:

- a headless command, `muse exec`;
- JSON Lines output, `muse exec --json`;
- large-prompt transport through `--prompt-file`;
- explicit workspace, model, reasoning-effort, permission, and session options;
- noninteractive handling for user-input requests;
- deterministic exit codes and a terminal JSON event;
- native `AGENTS.md` and Agent Skills support;
- retained append-only sessions and an offline export command.

The SASE adapter itself can remain thin: construct the command, stream and parse events,
return `InvokeResult`, and publish normal provider metadata. Most of the work is
compatibility hardening and tests rather than architectural invention.

The main traps are:

1. Muse's binary and JSON event contract are beta and can change through its hourly
   self-updater.
2. SASE calls its highest reasoning level `max`; Muse calls its highest level `ultra`.
3. Muse's executable name, `muse`, is generic and already collides with unrelated
   software, so path presence alone is unsafe for default-provider autodetection.
4. Muse's persistent inner subagents are invisible to SASE's agent-slot and workspace
   accounting.
5. Muse imports Claude and Codex personal rules/skills by default, which would duplicate
   or shadow SASE's own generated context unless the adapter deliberately selects one
   context source.
6. Sending the Meta model through OpenCode is a useful smoke test, but it is not a Muse
   Code integration: it omits Muse's co-trained prompts, tools, background agents, event
   log, compaction, and built-in skills.

The recommended solution is a staged native `muse exec --json` provider. First capture
sanitized authenticated traces against one pinned Muse release. Then add a conservative
built-in SASE adapter with explicit selection, native Muse skill deployment,
SASE-compatible permission flags, tolerant text/terminal parsing, and no special retry
policy until real failures have been characterized. Add tool-call, usage, and
retained-session artifact parity in a second step.

## Evidence and source boundaries

Primary sources used:

- Meta's
  [Muse Code and Muse Spark 1.2 announcement](https://research.meta.ai/blog/introducing-muse-code-and-muse-spark-1-2),
  published 2026-08-05.
- Meta's
  [Muse Spark 1.2 evaluation methodology](https://research.meta.ai/static/muse-spark-1-2-methodology).
- Meta's live [installer](https://dev.meta.ai/install.sh),
  [launcher](https://api.meta.ai/muse-launcher.sh), release channel, and release
  manifest.
- The checksummed Linux x86-64 Muse binary supplied by that manifest, inspected only
  through its help/version/echo-provider interfaces.
- SASE's provider hooks, registry, provider implementations, provider docs, skill
  deployment code, doctor checks, and agent-CLI management at the revision above.

The official release manifest reported `0.1.0-R708.1`; its Linux x86-64 artifact's
SHA-256 was verified as
`50937b6470cd0edf28eb683c352a5e7af3bcb1b015cd9a3b21dbf79d22af8182` before inspection.
`muse --version` reported `Muse Code 0.1.0 (0.1.0-R708.1)`.

Meta has not published Muse Code's source or a standalone public specification for its
JSONL event schema. The report distinguishes observed behavior from inferred
implementation details. A real authenticated trace is still required before implementing
usage and tool-call parsing.

## What Muse Code actually provides

Meta describes Muse Code as a terminal coding agent powered by Muse Spark 1.2. The
distinguishing harness features are not merely model access:

- a main agent plus specialized asynchronous background agents that persist for the
  session;
- an append-only local event log covering model calls, tools, approvals, and edits;
- replay-exact, restart-safe execution;
- bundled `/plan`, `/grill`, and `/goal` skills;
- context compaction and goal conditioning for long-horizon work;
- a harness and model that were co-trained together.

Meta's methodology is important when interpreting its benchmark claims: on
Terminal-Bench and DeepSWE, Muse Spark 1.2 ran in Muse Code while competitor models ran
in their selected agent products. This is evidence that Meta treats the harness as part
of the product, and it is also why substituting OpenCode is not equivalent.

### Installation, platforms, authentication, and updates

The public install command is:

```bash
curl -fsSL https://dev.meta.ai/install.sh | bash
```

The installer places a `muse` launcher in `${MUSE_INSTALL_DIR:-~/.local/bin}`. The
launcher supports x86-64 and ARM64 on Linux and macOS, downloads a checksummed static
binary, and stores the active release beside the launcher. It checks the stable channel
at most hourly by default and can update itself and the binary in the background.
Relevant launcher controls include `MUSE_NO_AUTO_UPDATE`, `MUSE_SYNC_UPDATE`,
`MUSE_UPDATE_INTERVAL_SECONDS`, `MUSE_AUTH_PATH`, and `MUSE_INSTALL_DIR`.

Muse accepts either:

- `META_API_KEY`;
- credentials stored by `muse auth set --provider meta --api-key-stdin`; or
- Meta account OAuth established by `muse login`.

The default credential file is `$XDG_CONFIG_HOME/muse/auth.json` when `XDG_CONFIG_HOME`
is set, otherwise `~/.config/muse/auth.json`. The current launcher also knows how to
perform device login if a protected download requires it.

### Headless contract

The current command surface is unusually integration-friendly:

```text
muse exec [OPTIONS] [PROMPT]
  --json
  --prompt-file <PATH>
  --provider <echo|meta>
  --model <ID>
  --reasoning-effort <none|minimal|low|medium|high|xhigh|ultra>
  --workspace <PATH>
  --session-id <UUID>
  --user-input-auto-resolve
  --no-foreign-personal-context
  --trust-workspace
  --disable-approval
  --disable-sandbox
  --no-session-log
```

There are also controls for model-step limits, tool-output size, context-compaction
strategy, web tools, shell/write access, network sandboxing, images, and worktrees. SASE
should not create a Muse worktree because SASE has already allocated an isolated
workspace.

`--prompt-file` is preferable to a positional prompt or stdin. It avoids OS argv limits
for preprocessed SASE prompts and leaves stdin available for Muse's `--api-key-stdin`
contract.

### JSONL output

A local, no-credential probe using Muse's deterministic `echo` provider established the
following:

- stdout is pure JSONL when `--json` is set;
- human diagnostics such as the selected workspace go to stderr;
- every envelope carries `schema_version`, `payload_type`, stream identity, sequence,
  timestamp, durability, and payload;
- assistant streaming text appears as `payload_type: "run.output.delta"` with
  `payload.text`;
- successful completion appears as `payload_type: "run.terminal.completed"` with the
  complete final answer in `payload.text`;
- the process exits zero on success and nonzero for launch/authentication failures;
- JSONL is considerably richer than the seven-event streams used by many coding CLIs:
  task lifecycle, model, subagent, approval, reminder, tool, and run state are all
  represented.

The parser should prefer the terminal event's complete text as the authoritative return
value while using deltas for live display. This avoids duplicate output if a delta is
retried or replayed. It should be tolerant of unknown payload types and newer schema
versions, preserving raw diagnostics on failure.

The current binary contains typed usage and provider-tool event families, but an echo
run does not exercise them. Their exact live Meta shapes must not be guessed from binary
strings; capture fixtures from an authenticated text-only run, tool-using run, subagent
run, rate-limit/error run, and interrupted run first.

### Sessions and restart evidence

With session logging enabled and `--session-id <UUID>`, Muse writes under:

```text
${XDG_DATA_HOME:-~/.local/share}/muse/sessions/YYYY/MM/DD/<UUID>/
  session.jsonl
  cron.db
```

`muse export --session <UUID> --out <path>` reads this offline and emits a
self-contained document with `export_schema_version: 1`. Meta documents the export as
including messages, tool calls/results, approvals, model IDs, usage-related evidence,
and subagent lineage. The default export is raw and may contain sensitive prompts, tool
outputs, and encrypted reasoning blobs; `--redacted` is available.

SASE should preserve Muse session logging initially, because restart evidence is a core
reason to choose this harness. It should not automatically copy the entire raw export
into SASE artifacts. A small artifact containing the Muse session UUID and release is
sufficient for routine runs; export should be opt-in for diagnosis.

`muse resume` is interactive. The current CLI does not advertise a headless
`exec --resume` mode, so SASE cannot yet make Muse's exact restart path part of its
automatic retry loop. SASE can still preserve workspace edits and restart with an
accumulated continuation prompt, as its Codex/OpenCode adapters do, while retaining the
original Muse log for manual recovery.

### Instructions and skills

Muse natively reads `AGENTS.md`. `muse init --dry-run` describes it as the project rules
file, so SASE does not need a new generated provider instruction shim.

Muse's native personal skill root is:

```text
${XDG_CONFIG_HOME:-~/.config}/muse/skills/<skill-id>/SKILL.md
```

Its native project skill root is `.agents/skills/<skill-id>/SKILL.md`. Muse can also
import personal Claude and Codex rules and skills. A probe on this development host
showed Muse discovering both `~/.claude/skills` and `$CODEX_HOME/skills`, with shadowing
diagnostics for duplicate SASE skills.

For a first-class provider, SASE should deploy generated skills directly through:

```python
def llm_skill_deploy_subpath(self) -> str:
    return ".config/muse"
```

and launch with `--no-foreign-personal-context`. That yields one authoritative SASE
skill copy instead of relying on another provider's directory and avoids duplicate
skills. Project `AGENTS.md` remains active through `--trust-workspace`.

## How this maps onto SASE

SASE discovers LLM providers through the `sase_llm` entry-point group and wraps one
plugin in `LLMPluginManager`. A provider owns invocation and metadata; SASE owns prompt
preprocessing, model/provider selection, retries, commit finalization, chat history,
artifacts, and postprocessing.

Muse fits that boundary. No new hooks are necessary for an MVP.

| SASE contract              | Muse mapping                                                                                              |
| -------------------------- | --------------------------------------------------------------------------------------------------------- |
| Provider entry point       | `muse = "sase.llm_provider.muse:MuseProvider"`                                                            |
| Provider name / short name | `muse` / `mus`                                                                                            |
| Executable                 | `muse`, overridable by derived `SASE_MUSE_PATH`                                                           |
| Headless invocation        | `muse exec --json`                                                                                        |
| Prompt transport           | secure temporary file plus `--prompt-file`                                                                |
| Workspace                  | explicit `--workspace <SASE active workspace>`; do not request a Muse worktree                            |
| Permissions                | `--trust-workspace --disable-approval --disable-sandbox` (equivalent to `--yolo`, but explicit)           |
| Interactive questions      | `--user-input-auto-resolve` so a headless run cannot hang                                                 |
| Context                    | `--no-foreign-personal-context`; use project `AGENTS.md` and native Muse skills                           |
| Model override             | `--model <model>`                                                                                         |
| Effort                     | direct for `none` through `xhigh`; map SASE `max` to Muse `ultra`                                         |
| Live answer                | `run.output.delta.payload.text`                                                                           |
| Final answer               | `run.terminal.completed.payload.text`                                                                     |
| Token usage                | return `None` in MVP; add after authenticated fixtures establish the live shape                           |
| Interrupt                  | terminate the subprocess through SASE's existing interrupt monitor; restart with accumulated context      |
| Session evidence           | generated UUID passed through `--session-id`; retain Muse's log and record a small SASE metadata artifact |
| Skills                     | deploy to `~/.config/muse/skills` via `.config/muse` hook                                                 |
| Authentication evidence    | `META_API_KEY`, `$XDG_CONFIG_HOME/muse/auth.json`, `~/.config/muse/auth.json`                             |
| Install/update metadata    | native user install; official docs/installer URL; `--version` probe                                       |

### Suggested command

For a normal SASE invocation, the adapter should construct the equivalent of:

```bash
MUSE_NO_AUTO_UPDATE=1 muse exec \
  --json \
  --workspace "$SASE_ACTIVE_PROJECT_DIR" \
  --trust-workspace \
  --disable-approval \
  --disable-sandbox \
  --user-input-auto-resolve \
  --no-foreign-personal-context \
  --session-id "$INVOCATION_UUID" \
  --prompt-file "$SECURE_TEMP_PROMPT" \
  --model muse-spark-1.2 \
  --reasoning-effort high
```

The example shows model and effort flags for clarity. The implementation should append
them only when SASE has resolved a value. It should also honor the normal generic
`SASE_LLM_LARGE_ARGS` / `SASE_LLM_SMALL_ARGS` escape hatch and Muse-specific
`SASE_MUSE_LARGE_ARGS` / `SASE_MUSE_SMALL_ARGS` fallbacks.

`MUSE_NO_AUTO_UPDATE=1` prevents an hourly launcher update from changing the binary or
event schema at the start of a SASE-controlled run. Users can update Muse outside an
active SASE invocation. This is compatibility containment, not a replacement for a
documented update policy.

### Model tiers

The standard model ID appears to be `muse-spark-1.2`, but the live authenticated model
catalog should be treated as authoritative during the trace-capture spike. Meta's public
launch materials do not document a distinct smaller Muse model or the terms of any
alternate catalog variants. SASE must not infer a `small` tier from unverified catalog
names or third-party reports.

Until Meta exposes a documented smaller model, map both tiers to the standard Muse Spark
1.2 model or allow Muse's default catalog choice for both. This is semantically honest
but means `small` is not a cost guarantee. Any alternate variant should enter SASE's
known-model list only after its identity and data terms are verified, and it should
remain an explicitly selected, clearly documented opt-in when those terms differ.

### Reasoning effort

SASE's canonical vocabulary is:

```text
none, minimal, low, medium, high, xhigh, max
```

Muse accepts:

```text
none, minimal, low, medium, high, xhigh, ultra
```

The provider should map `max` to `--reasoning-effort ultra`. All other levels map
one-to-one. This is exactly the kind of vendor spelling difference SASE's
`invocation_option_args()` hook is intended to absorb.

Muse defaults to `high` if no flag is supplied. SASE currently records only resolved
prompt/config effort, so a provider-default Muse run may display no effort even though
Muse used `high`. That minor observability mismatch should be documented or addressed
later with provider-default metadata; it is not a reason to broaden the MVP hook
contract.

## Native Muse versus simpler alternatives

| Approach                                                    | Benefits                                                                                                             | Costs / omissions                                                                                          | Verdict                                                                        |
| ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Native `muse exec --json` provider                          | Uses the co-trained harness, persistent agents, event log, compaction, Muse tools, skills, and verification behavior | Beta schema, new parser, nested-agent accounting, native install/auth lifecycle                            | **Recommended**                                                                |
| Configure existing OpenCode provider against Meta Model API | Fastest way to test Muse Spark model quality; almost no SASE code                                                    | Not Muse Code; loses Meta's harness behavior and benchmark comparability                                   | Useful preflight only                                                          |
| Add a direct Meta Model API client inside SASE              | Full API control and no extra CLI process                                                                            | Reimplements an agent harness in SASE; violates the current thin-provider design; still not Muse Code      | Do not do this                                                                 |
| Ship Muse as a separate external SASE plugin                | Isolates beta churn and can release independently                                                                    | Additional package/repository/update burden; first-party docs and skill deployment still need coordination | Reasonable incubation option, but unnecessary for the initial built-in adapter |

The key distinction is model provider versus agent harness. The requested feature is an
agent harness integration, so the native CLI is the right boundary.

## Risks and design decisions

### 1. Beta auto-update and event-schema drift

The launcher can replace the binary hourly, while SASE's parser is compiled and tested
against a particular event shape. A future Muse release could therefore break a run
without SASE or the user changing anything.

Mitigation:

- suppress launcher auto-update for SASE subprocesses;
- record Muse's version in run metadata;
- tolerate unknown event and field additions;
- key parser fixtures by Muse release;
- fail with a diagnostic that includes the observed schema/version rather than returning
  an empty successful answer;
- keep the raw stdout/stderr in `CalledProcessError` for postmortem and retry logic.

### 2. Unsafe autodetection by executable name

`muse` is not a unique product name. SASE's current autodetection checks only whether
the plugin's CLI name resolves on `PATH`; it does not verify a product-specific version
signature. A music, modeling, or unrelated coding tool called `muse` could be selected.

For the first release, publish `llm_autodetect_cli_name() == "muse"` so doctor and
agent-CLI inventory can find it, but omit `llm_autodetect_priority()`. Users select it
with `llm_provider.provider: muse`, `%model:muse/...`, or `SASE_MUSE_PATH`. Add
automatic selection only after SASE has a provider identity-probe contract, or after
enough field experience shows the collision risk is acceptable.

### 3. Nested agent and worktree ownership

Muse's background agents run inside one SASE provider process. SASE counts that as one
agent slot, cannot name or steer the inner agents, and may not see inner worktrees in
its workspace registry. This is not necessarily wrong—Claude and other harnesses also
perform internal parallel tool work—but Muse makes it central to long-horizon behavior.

The initial adapter should:

- never request a top-level Muse worktree;
- leave Muse's documented per-child worktree behavior at its default;
- record that inner agents are provider-internal and outside SASE scheduling;
- test concurrent SASE runs for CPU, memory, worktree, and Git-lock pressure before
  making Muse a default provider.

Longer term, SASE may want optional provider resource hints, but that is a
cross-provider capacity feature and should not be invented solely for Muse.

### 4. Duplicate orchestration and retry layers

Muse has its own provider retry, reminders, goals, context compaction, approvals, and
session recovery. SASE also has retries, goal workflows, commit finalization, prompt
directives, and artifacts. Blindly enabling both policies can multiply retries or
produce contradictory instructions.

The adapter should keep Muse's core harness intact but start without SASE-supplied Muse
retry defaults. Let Muse exhaust its own transport retry behavior; then let a nonzero
process exit enter SASE's generic failure path. Add provider retry patterns only after
capturing real terminal failures. Keep SASE's provider-neutral commit finalizer, because
that is an outer workflow invariant rather than a duplicate Muse feature.

### 5. Permission boundary

Current SASE adapters deliberately disable native approval/sandbox prompts so an
unattended provider can operate in the SASE-assigned workspace. Muse defaults both
approval and sandboxing on, and its default network sandbox is `proxy-only`.

Using explicit `--trust-workspace --disable-approval --disable-sandbox` matches existing
SASE provider behavior and avoids a headless deadlock. It also means Muse has the same
host authority as the SASE process. This must be visible in docs. A future opt-in mode
could retain Muse's sandbox, but changing the default security semantics for only one
runtime would violate SASE's uniform-runtime rule.

### 6. Session-data growth and sensitive exports

Muse session logs are valuable and can be large. Its own 24-hour case study used more
than 1,000 tool calls. Retaining every log indefinitely without indexing or cleanup can
consume substantial disk, while automatic raw exports duplicate sensitive material.

Keep Muse's native log, record a locator, do not auto-export it, and add retention or
artifact capture only through an explicit SASE-wide design. A user-requested diagnostic
export should prefer `--redacted` unless raw evidence is specifically needed.

### 7. Provider update management

SASE's `sase agent-cli` can manage npm, Homebrew, or a provider-declared self-update
command. Muse uses a launcher-side updater and does not advertise `muse update`.
Declaring `--version` as a fake self-update command would be misleading.

For the MVP, report Muse as a native/manual install with the official installer URL and
version probe. Document that normal Muse launches update it. A later generic
`auto_updates: true` install-metadata field could improve agent-CLI presentation, but it
is not required to run the provider.

## Concrete implementation scope

### Provider and parser

Add:

- `src/sase/llm_provider/muse.py`
  - command construction;
  - model-tier and effort mapping;
  - executable/workspace resolution;
  - temporary prompt-file lifecycle;
  - metadata hooks;
  - SASE interrupt handling and accumulated-context restart;
  - release/session metadata artifact.
- `src/sase/llm_provider/_subprocess_muse.py`
  - nonblocking JSONL parsing;
  - delta streaming into `live_reply.md`;
  - authoritative terminal-text extraction;
  - failure-event capture;
  - later, usage and tool-call artifact extraction.
- a compatibility export in `src/sase/llm_provider/_subprocess.py` only if current tests
  or callers benefit from the shared facade.

Register the provider in `pyproject.toml` under `[project.entry-points."sase_llm"]`. The
existing registry, model-alias resolver, `<provider>_coder` alias generation, provider
path override derivation, and most doctor/Models-panel behavior are already data-driven.

### Metadata

The provider should publish approximately:

```python
provider_name = "muse"
short_name = "mus"
cli_name = "muse"
skill_deploy_subpath = ".config/muse"
auth_evidence = {
    "credential_paths": [
        "$XDG_CONFIG_HOME/muse/auth.json",
        "~/.config/muse/auth.json",
    ],
    "api_key_env_vars": ["META_API_KEY"],
}
install = {
    "manager": "native",
    "scope": "user",
    "display_name": "Muse Code",
    "docs_url": "https://research.meta.ai/blog/introducing-muse-code-and-muse-spark-1-2",
    "version_argv": ["--version"],
    "version_regex": r"Muse Code (?P<version>\d+\.\d+\.\d+)",
}
```

Do not publish an autodetect priority or a self-update argv in the MVP. Add a distinct
Meta/Muse color through `llm_cli_status_color`; add an emoji badge only as optional UI
polish because unknown providers already render correctly with a neutral badge policy.

SASE doctor currently derives install text from plugin metadata but needs a small local
fallback entry to give the exact authentication hint: run `muse login`, use
`muse auth set --provider meta --api-key-stdin`, or set `META_API_KEY`.

### Documentation and presentation

Update the provider lists and Muse sections in:

- `docs/llms.md`;
- `docs/agent_providers.md`;
- `docs/plugins.md`;
- `docs/configuration.md` where examples enumerate built-ins;
- `src/sase/default_config.yml` comments if examples enumerate provider names;
- `docs/ace.md` and `src/sase/integrations/provider_badges.py` only if a dedicated
  provider badge is added.

No `MUSE.md` instruction shim should be added: Muse reads `AGENTS.md` directly. Adding
another generated shim would increase memory-maintenance surface without serving the
runtime.

### Test plan

The implementation should not depend on paid API calls in the normal suite.

1. **Release-pinned parser fixtures**
   - text deltas plus successful terminal;
   - no deltas but terminal text;
   - duplicate/replayed delta;
   - malformed and unknown events;
   - failed terminal plus nonzero exit;
   - tool start/result pairs;
   - usage-bearing completion;
   - subagent lifecycle;
   - interrupted/abnormal session.
2. **Provider unit tests**
   - executable override and missing-binary diagnostic;
   - workspace resolution;
   - prompt file used instead of argv/stdin;
   - exact safety/context/session flags;
   - `max -> ultra` effort mapping and direct lower mappings;
   - explicit model override;
   - generic versus Muse-specific extra args;
   - interrupt reconstruction;
   - prompt temp file removed after success and failure.
3. **Registry and product integration**
   - entry-point discovery;
   - explicit provider/model selection;
   - known model aliases and model-picker rows;
   - `SASE_MUSE_PATH` cache invalidation;
   - doctor auth evidence and setup hints;
   - `sase agent-cli` version parsing;
   - generated skills target `~/.config/muse/skills`;
   - provider display/badge tests.
4. **Hermetic CLI smoke test**
   - run the official or a stub Muse CLI with `--provider echo --json` and isolated XDG
     config/data roots;
   - assert stdout/stderr separation, terminal extraction, and no workspace writes.
5. **Manual authenticated acceptance test**
   - real text-only task;
   - real file edit and test command;
   - tool-call/usage artifacts;
   - user steer/termination;
   - two concurrent SASE Muse runs;
   - long run with context compaction or a background subagent;
   - retained log export and manual resume.

The authenticated acceptance lane should be opt-in and secret-aware, not a default CI
test.

## Expected size and unknowns

A text-capable MVP is small: one provider module, one parser, an entry point, metadata,
docs, and focused tests. A first-class integration with usage/tool artifacts,
version-aware diagnostics, session locators, and realistic interruption fixtures is a
moderate provider project rather than a one-file wrapper.

The only genuine pre-implementation blocker is authenticated evidence. Before coding the
usage and tool parsers, someone with Meta Model API access must capture sanitized JSONL
from the current release. The standard model ID, alternate-model disclosures,
pricing/availability, rate-limit errors, usage fields, and tool-result shapes should be
confirmed from the authenticated catalog and traces rather than inferred from launch
marketing or third-party reports.

## Recommended approach

Implement a **native, built-in Muse Code provider in two stages**.

**Stage 0: one short compatibility spike.** Install the official launcher in an isolated
location, authenticate with a test account, pin and record the Muse release, and capture
sanitized fixtures for text, tools, usage, subagents, interruption, and one failure.
Confirm the live `muse-spark-1.2` model ID and the identity and data terms of any
alternate catalog variants. This converts the remaining guesses into executable test
inputs.

**Stage 1: conservative production MVP.** Add `MuseProvider` around `muse exec --json`,
use a secure prompt file, explicit workspace and permission flags, native
`~/.config/muse/skills` deployment, `--no-foreign-personal-context`, a retained session
UUID, and a forward-tolerant parser for answer deltas plus the terminal event. Map SASE
`max` to Muse `ultra`; map both model tiers to the standard model until a safe small
model exists. Keep Muse explicit-only initially because the `muse` command name is
ambiguous. Disable launcher auto-update during SASE runs and record the actual version.
Return `usage=None` and omit Muse-specific outer retries until the Stage 0 fixtures
justify them.

**Stage 2: parity and operational hardening.** Parse usage and tool-call artifacts,
record a small Muse session locator, add version-specific diagnostics, exercise
interrupt/retry behavior, and measure nested-agent resource pressure. Only then consider
default-provider autodetection or mapping Muse into shipped role aliases.

Use OpenCode pointed at Meta Model API only as a preflight for model access and quality.
Do not ship that configuration as the Muse Code solution: the co-trained agentic harness
is the feature being integrated.
