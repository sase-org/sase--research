# Lumberjack and Chop Configuration Audit

**Date:** 2026-07-12  
**Scope:** SASE commit `599f6feb29689c4926184ccd26638163796f77c4`; chezmoi commit
`f6f90f86ab3c8ae622c71b6005b2554a16a8846a`; effective installed runtime
`sase 0.10.2+untagged.gf115c3c5b`  
**Question:** What can lumberjack/chop configuration express today, what do Bryan's real non-built-in chops require, and
which capabilities deserve first-class support?

## Executive summary

The current design has a strong execution substrate but a deliberately small configuration language.

Today a lumberjack is a fixed-interval process lane. Each chop is either:

1. a discovered executable, with a JSON ChangeSpec context, per-chop environment, timeout, live output, bounded history,
   and live-run deduplication; or
2. a static agent prompt, with prompt-hash live deduplication and normal SASE/xprompt launch behavior.

That is enough to build sophisticated automation, and Bryan's configuration proves it. The effective Athena config has
10 lumberjacks and 25 chop entries: 17 scripts and 8 agent prompts. Twelve entries come from the chezmoi config rather
than SASE's built-in lumberjacks. They poll Telegram, repair failing checks, split oversized Python files, audit recent
commits, refresh documentation across five repositories, and react to failed GitHub Actions runs.

The cost is that user code repeatedly implements the layer between **polling** and **launching**:

- detect whether useful work exists;
- retain a watermark or dedupe key;
- prevent semantically duplicate work after the launcher process has exited;
- fan one definition out across repositories;
- launch an agent or workflow with dynamic evidence;
- report `no-op`, `actioned`, and `check_error` as meaningful outcomes.

The highest-leverage improvement is therefore not “more built-in chops.” It is a first-class, extensible
**trigger/probe → decision → action** contract, backed by runner-owned checkpointing, keyed concurrency, and structured
outcomes. GitHub- and Telegram-specific detection should remain plugin-owned; the core should own the generic contract,
scheduling, state, run history, and operator UX.

Four changes should be treated as the core package:

1. **Structured trigger/action chops with transactional checkpoints.** A cheap deterministic probe can decide whether to
   run a script, workflow, or agent without allocating an agent workspace just to discover a no-op.
2. **End-to-end outcomes and keyed concurrency.** `agent_launched` should be a launch phase, not the terminal truth about
   an agent-backed chop. Dedupe should optionally last through a ChangeSpec/workflow lifecycle and work across
   lumberjacks and targets.
3. **Fail-closed validation.** Invalid durations currently degrade to “unset,” which can turn an intended hourly chop
   into an every-tick chop. Doctor should validate agent/xprompt references, duplicate identities, intervals, and semantic
   field applicability.
4. **Typed workflow actions and matrix expansion.** The five nearly identical `refresh_docs` prompt strings should be one
   validated action expanded over typed targets.

Cron/one-shot schedules, jitter, pause/resume, hot reload, per-chop metrics, and richer retention remain worthwhile, but
they are secondary to the trigger, lifecycle, and state gaps demonstrated by the actual Athena workloads.

Do **not** simply restore the retired arbitrary shell `gate:` field. Its removal was reasonable: workflow logic is a
better home for multi-step decisions. The missing abstraction is a safe typed trigger/probe protocol, not another opaque
shell string embedded in YAML.

## Method and evidence

This audit reviewed:

- the current configuration parser and JSON schema;
- default lumberjacks and executable entry points;
- the scheduler, script runner, agent runner, registry, run-history store, inventory, doctor, CLI, TUI documentation,
  and config merge rules;
- the numbered-workspace checkout of Bryan's chezmoi repository, including both custom executable chops and their bash
  regression tests;
- all xprompt workflows referenced by the custom agent chops;
- relevant git history, particularly the addition and later removal of chop `gate:` support;
- earlier research under `202603`–`202605`, distinguishing still-valid conclusions from features subsequently shipped;
- the effective runtime inventory via `sase axe chop list --json`, `sase axe chop doctor --json`, and
  `sase axe lumberjack list` from Bryan's home directory.

The live inventory found every configured script resolvable. Doctor returned `WARN` only because
`pr_submitted_checks` and `pushgateway_cleanup` are installed but not configured. This report does not treat that warning
as a defect.

## What configuration allows today

### Merge and extension model

The effective config is a deep merge in this order:

1. bundled defaults;
2. plugin defaults, with list concatenation;
3. user `~/.config/sase/sase.yml`, with list replacement;
4. sorted `sase_*.yml` overlays, with list concatenation;
5. project-local `./sase.yml`, with list concatenation when local loading is enabled.

Maps merge recursively. This makes it easy for Bryan's `sase_athena.yml` to add new lumberjack names while retaining the
built-ins. Lists are not merged by chop identity, however. An overlay can append a chop but cannot cleanly patch or
delete one existing list item. Re-declaring the same name creates another entry rather than overriding it. The base user
file can replace the whole list, but that requires copying every item that should remain.

This is adequate for additive configuration and awkward for lifecycle operations such as “disable one packaged chop,”
“change only its timeout,” or “replace the prompt but keep plugin updates.”

### Configured fields

| Scope | Field | Current behavior | Important boundary |
| --- | --- | --- | --- |
| `axe` | `max_hook_runners` | Global limit used by hook runner work. | Does not directly gate configured agent-chop launches. |
| `axe` | `max_agent_runners` | Limit passed into hook/mentor job infrastructure and script context. | Direct `agent:` chops call the launcher without acquiring this limit. |
| `axe` | `zombie_timeout_seconds` | Timeout used by hook/workflow zombie handling. | Not an agent-chop lifetime. |
| `axe` | `query` | One global ChangeSpec filter; both all and filtered snapshots are provided to scripts. | No per-lumberjack or per-chop query. |
| `axe` | `chop_script_dirs` | Extra executable search directories. | Configured directories accept exact names; interpreter/PATH discovery uses `sase_chop_` names. |
| `axe` | `lumberjack_log_max_bytes` | Bounds aggregate lumberjack logs. | Per-run history retention is separately hard-coded to 10 terminal runs. |
| `axe` | `verbose_lumberjack_diagnostics` | Adds diagnostic detail to scheduled script context. | The one-shot context path does not currently copy this flag. |
| lumberjack | `interval` | Integer seconds between scheduler ticks; the first tick runs immediately. | Fixed-delay only; no cron, calendar, jitter, or one-shot time. Schema has no positive minimum. |
| lumberjack | `chop_timeout` | Default script duration limit, using integer `s`, `m`, or `h` syntax. | Ignored by agent-backed chop lifetimes. |
| chop | `name` | Script lookup name and state/history identity. | No separate stable ID, target, or implementation name. Duplicate identities are not rejected. |
| chop | `description` | Operator-facing label. | Docs call it required, while parser/schema allow it to be absent. |
| chop | `agent` / `xprompt` | Static raw prompt launched through normal SASE agent machinery; `agent` wins if both exist. | No typed workflow/reference validation, inputs map, target matrix, or dynamic template context. |
| chop | `run_every` | Persistent minimum cadence in integer `s`, `m`, or `h`; manual runs bypass it. | Invalid values become `None`, meaning every tick. Semantics differ after script and agent failures. |
| chop | `timeout` | Per-script timeout overriding `chop_timeout`. | Parsed for agent chops but not applied to the launched agent/workflow. |
| chop | `env` | String environment values injected into script subprocesses. | Custom `env` is not propagated to `agent:` launches; only SASE's chop identity variables are. |

Plain string chop entries remain accepted as a legacy form, but object entries are the meaningful modern interface.

### Script chop contract

A chop with no `agent`/`xprompt` is resolved in this order:

1. an executable exactly named `<name>` in `chop_script_dirs`;
2. `sase_chop_<name>` beside the active Python interpreter;
3. `sase_chop_<name>` on `PATH`.

It is called as:

```text
<executable> --context <context.json>
```

The context points to atomically written `all_changespecs.json` and `filtered_changespecs.json` snapshots and includes
runner limits, the global query, lumberjack name, and a writable lumberjack state directory. The runner:

- injects configured environment variables plus chop identity variables;
- runs from the lumberjack state directory rather than a potentially deleted daemon CWD;
- merges stdout/stderr into a live per-run log;
- starts a new process group and kills it on timeout;
- records the PID early;
- dedupes a live script by `(lumberjack, chop name)`;
- recovers stale PID/PID-less `running` records;
- records `success`, `failure`, `timeout`, or `missing_script` plus timing and output size.

Eligible script chops in one lumberjack tick run concurrently in an unconfigured `ThreadPoolExecutor`. Separate
lumberjacks are separate processes, so the same implementation can also overlap across lumberjacks. A tick waits for all
of its script futures before completing.

### Agent chop contract

A chop with `agent` or legacy `xprompt` launches the raw string through `launch_agent_from_cwd`. This is powerful because
the string can contain VCS refs, directives, xprompt workflow calls, swarms, waits, and approval behavior. Agent chops are
visible in ACE unless the prompt uses `%hide`.

The runner creates a durable registry entry and injects:

- `SASE_CHOP_LUMBERJACK`;
- `SASE_CHOP_NAME`;
- `SASE_CHOP_RUN_ID`;
- `SASE_CHOP_PROMPT_HASH`.

Live dedupe is scoped to lumberjack, chop name, and normalized prompt hash. Agent launches are sequential within one
lumberjack tick to avoid workspace-allocation races, but different lumberjacks can launch concurrently.

The chop run ends as `agent_launched` immediately after launch. The registry can later tell whether the process is still
live, but the chop's run-history row is not finalized with the workflow's eventual no-op, success, failure, retry chain,
or produced ChangeSpec. Consequently the chop dashboard answers “did AXE launch it?” rather than “did this maintenance
job succeed?”

### Scheduling semantics that matter in practice

- The first tick runs immediately on lumberjack start.
- `interval` schedules the whole tick, not each chop independently.
- `run_every` is persisted by chop name under its lumberjack, so restarts preserve cadence.
- A successful script updates its timestamp. A failed script does not, so it retries on the next lumberjack tick rather
  than after its nominal `run_every`.
- A successful agent launch updates its timestamp before the agent completes.
- An agent launch failure also updates its timestamp, intentionally throttling bad launch config to the normal cadence.
- A later agent/workflow failure does not change the chop timestamp or chop history.
- A daemon outage produces at most one catch-up launch on restart; missed intervals are not replayed.
- Manual CLI/TUI runs bypass `run_every` but retain timeout, context, dedupe, and history behavior.

These rules are individually defensible, but they are implicit and asymmetric. A user cannot configure cadence to anchor
on attempt, successful probe, accepted action, or completed action, nor choose a backoff policy.

### Operations and observability already present

The current system is substantially ahead of the March 2026 `lumberjack_vs_openclaw.md` snapshot. It now has:

- per-execution metadata and live logs;
- duration, exit code, PID, source, and start/finish timestamps;
- 10 retained terminal runs per chop, with live runs protected from pruning;
- manual runs from CLI and TUI;
- configured/available inventory and doctor checks;
- live output and run-history navigation in ACE;
- Prometheus metrics for cycles, cycle duration, active lumberjacks, restarts, and aggregate errors;
- a global configurable IANA timezone used by SASE timestamp generation and display.

Still missing are a CLI runs query, configurable history retention, per-chop action/no-op metrics, semantic agent
completion, scheduled one-shots, cron/calendar schedules, individual pause/resume, and hot reload.

## Effective Athena inventory

The effective runtime contains 10 lumberjacks and 25 configured entries.

| Lumberjack | Tick | Effective chops | Provenance |
| --- | ---: | --- | --- |
| `hooks` | 5s | 8 script chops | bundled defaults |
| `waits` | 10s | 1 script chop | bundled defaults |
| `checks` | 300s | 2 script chops | bundled defaults |
| `comments` | 60s | 1 script chop | bundled defaults |
| `housekeeping` | 3600s | 1 script chop | bundled defaults |
| `telegram` | 5s | `tg_inbound`, `tg_outbound` | chezmoi base config + `sase-telegram` executables |
| `run_every` | 60s | `sase_pylimit_split`, `sase_fix_just` | chezmoi Athena overlay |
| `code_quality` | 60s | two recent-commit audit agents | chezmoi Athena overlay |
| `refresh_docs` | 60s | five repository-specific docs agents | chezmoi Athena overlay |
| `github_actions` | 300s | `gh_actions_fix` | chezmoi Athena overlay + custom executable |

The 12 user-configured entries deserve separate examination rather than being folded into a built-in inventory.

### User-defined chop audit

| Chop(s) | Type and cadence | What the definition/workflow adds beyond AXE | Capability signal |
| --- | --- | --- | --- |
| `tg_inbound`, `tg_outbound` | Plugin scripts every 5s | Telegram credentials/identity, inbound cursoring, outbound notification high-water state, and channel semantics live in the plugin. | Plugin activation, credential references, and event-source health are configuration concerns; transport logic is not core AXE logic. |
| `sase_pylimit_split` | Agent workflow every 60m | Scans `src`/`tests`, skips when no file exceeds limits, creates collision-free agent names, fans out one agent per file, and wait-chains them. | A deterministic preflight occurs only after an outer agent/workspace launch; typed probe/action separation could avoid that overhead. |
| `sase_fix_just` | Custom script every 60m | Reads all ChangeSpecs, blocks while any open `sase_fix_just_` ChangeSpec exists, then invokes `sase run` with a static workflow prompt. | Live-process dedupe is insufficient; users need lifecycle/keyed inhibition and a native workflow action after a cheap guard. |
| `sase_recent_bug_audit` | Agent workflow checked every 60m | Counts commits since a per-project SHA/timestamp marker, launches only at 200 commits, then advances the marker after launch. | Runner-owned watermarks, conditional triggers, and commit-count providers would remove repeated state code. |
| `sase_recent_improvement_audit` | Agent workflow checked every 60m | Nearly duplicates the bug-audit marker/count/launch protocol with a different prompt and marker. | The repetition is an abstraction signal, not a request for another hard-coded built-in chop. |
| `sase_refresh_docs` | Agent workflow every 3h | Checks a 100-commit project marker, launches update+polish agents, and advances the marker. | Schedule cadence and useful-work cadence are different concepts; both should be visible to the scheduler. |
| four plugin `*_refresh_docs` chops | Four copied agent strings every 24h | Run the same workflow for four project/ref pairs with threshold 25. | Typed target matrices and structured workflow inputs would collapse five definitions and enable validation. |
| `gh_actions_fix` | Custom script probed every 15m, 120s timeout | Iterates repositories from a space-delimited env var; checks the latest run; classifies conclusions; retrieves bounded failed logs; stores per-run-attempt dedupe state atomically; blocks on open fixer ChangeSpecs; builds a dynamic PR/agent prompt; launches agents; prints summary counters. | This is the clearest case for plugin-provided triggers plus core watermark, per-target keyed concurrency, dynamic evidence attachment, action launch, and structured result support. |

### Detailed observations from the custom implementations

#### 1. “Do I have work?” is implemented three different ways

- `pylimit_split` scans files.
- audit/docs workflows compare Git history to marker files.
- `gh_actions_fix` polls provider state and a local seen set.

All are deterministic probes. Today they live either inside a full agent workflow or inside a script that must launch
another agent itself. AXE cannot display the probe decision independently from the action.

#### 2. There are at least three dedupe lifetimes

The runner natively prevents only overlapping live executions. Bryan's workloads also need:

- **event dedupe:** do not process the same GitHub run attempt twice;
- **work-product dedupe:** do not launch another fixer while an open matching ChangeSpec exists;
- **watermark dedupe:** do not re-audit commits already covered by a successful launch.

These should not be conflated. A single `already_running` bit cannot represent them.

The two custom repair scripts both implement the same open-ChangeSpec prefix guard. `gh_actions_fix` currently makes
that guard global: one open `sase_gha_fix_` ChangeSpec blocks checking every configured repository. A native keyed guard
could scope inhibition per repository/run while retaining a global cap if desired.

#### 3. State commit timing is part of correctness

The Git and GitHub markers are advanced only after an action launches successfully. That protects against lost work, but
“launch succeeded” still does not mean “work completed.” Some jobs should checkpoint on observation, some on accepted
launch, and some only on successful completion. This needs an explicit policy and transactional state helper, not an
unwritten convention in every script.

#### 4. User output is already trying to be structured

`gh_actions_fix` emits bounded fields such as `repos_checked`, `actionable_failures`, `dedupe_skips`,
`launch_successes`, `launch_failures`, and `check_errors`. The xprompt workflow steps emit `should_launch`, `reason`,
`launched`, and marker metadata. AXE stores this as text only. Its status remains binary process success or
`agent_launched`, so the TUI cannot distinguish a healthy no-op from an action or a partially degraded provider check.

#### 5. Raw prompt strings are flexible but opaque

The current config repeatedly embeds `%n`, `#gh`, `%g:chop`, `#!workflow`, `#pr`, and workflow arguments in one string.
Doctor treats every non-empty agent field as `agent-backed`; it does not verify the workflow exists, its inputs typecheck,
the VCS ref resolves, or the prompt has a stable name. The five docs definitions demonstrate where a typed convenience
layer would improve safety without taking away the raw-prompt escape hatch.

#### 6. Direct agent chops are outside the named runner cap

`max_agent_runners` is consumed by hook/mentor job machinery and exposed to scripts. The configured agent-chop runner
itself does not acquire a shared runner slot before calling the agent launcher. Sequential launch within one lumberjack
prevents a workspace race, but the `code_quality`, `refresh_docs`, and `run_every` lumberjacks may launch concurrently.
With eight configured agent chops, this is no longer a theoretical distinction. AXE needs a clear resource policy for
direct agent actions.

## Recommended built-in capabilities

### P0: Structured trigger → action chops

Add an optional declarative shape that separates a cheap probe from an action:

```yaml
- id: refresh_docs_sase_core
  schedule:
    every: 24h
  trigger:
    provider: git.commits_since
    project: sase-core
    threshold: 25
    checkpoint: on_action_accepted
  action:
    workflow: sase/refresh_docs
    vcs_ref: sase-org/sase-core
    inputs:
      project: sase-core
      gh_ref: sase-org/sase-core
      threshold: 25
```

The core contract should support:

- a typed trigger result: `action`, `no_op`, or `check_error`;
- a stable event/dedupe key and optional evidence file references;
- runner-owned checkpoint storage scoped by chop and target;
- checkpoint timing: `on_observation`, `on_action_accepted`, or `on_action_success`;
- an action type: script, workflow, raw agent prompt, or plugin-defined action;
- an optional plugin trigger namespace.

Core can ship generic triggers such as `always`, `script_probe`, `changespec_query`, and perhaps `git.commits_since` if
the backend boundary is respected. `github.actions.failed` belongs in `sase-github`; Telegram event sources belong in
`sase-telegram`.

A script-probe escape hatch should use argv, timeout, a minimal read-only context, and a result file/JSON protocol. It
should not be a shell-interpreted YAML string.

This single abstraction directly improves every non-Telegram custom chop.

### P0: End-to-end action lifecycle and structured outcomes

Extend run history so a launchable chop has phases rather than treating `agent_launched` as terminal:

```text
probing → no_op
        → check_error
        → action_queued → action_running → action_succeeded
                                      └─→ action_failed
```

Record at least:

- probe outcome and reason;
- event/dedupe key;
- target/project;
- checkpoint before/after values;
- launched agent/workflow IDs and ChangeSpec name;
- final agent/workflow outcome;
- bounded counters and evidence paths;
- retries and next eligible time.

For backward compatibility, current scripts can continue to map exit 0/other to success/failure. New scripts should
receive `SASE_CHOP_RESULT_FILE` and atomically write a versioned result document. AXE can then render the excellent
human-readable log and also ingest stable fields.

The outer chop should subscribe to the existing agent completion artifacts rather than inventing a second completion
channel. This would let `sase_fix_just` and the audit/docs chops show their real result in the chop dashboard.

### P0: Keyed concurrency, inhibition, and resource limits

Generalize live-run dedupe into explicit policies:

```yaml
concurrency:
  key: "refresh_docs:{project}"
  max_running: 1
  scope: global
  hold_until: action_terminal
inhibit_if:
  changespec:
    name_prefix: "sase_fix_just_"
    status: [WIP, Draft, Ready, Mailed]
```

Needed dimensions are:

- scope: chop, lumberjack, project/target, or global;
- key templates based on trigger output;
- duration: process live, agent terminal, or matching ChangeSpec terminal;
- policy: forbid, queue, or replace;
- a real global/per-lumberjack cap for configured script and direct-agent actions.

This avoids copying ChangeSpec prefix scans into scripts and prevents multiple lumberjacks from bypassing each other's
resource limits.

### P0: Fail-closed configuration and doctor validation

Runtime configuration should reject or disable invalid entries with a precise path. In particular:

- invalid `run_every`, `timeout`, or `chop_timeout` must not silently become `None`;
- `interval` must be a positive integer;
- a chop must have a non-empty stable ID/name;
- duplicate IDs within a lumberjack should be errors;
- conflicting `agent` and `xprompt` should be rejected or explicitly normalized;
- script-only fields on agent actions should produce a warning/error rather than being silently ignored;
- `env` on agent actions should either work or be rejected;
- agent/workflow references, xprompt inputs, VCS refs, and plugin trigger names should be checked by doctor;
- merged list collisions should be reported with provenance.

The dangerous case is an intended `run_every: 1d` or numeric `3600`: the schema can catch it in the Admin Center, but
the runtime parser converts it to every-tick behavior if unvalidated config reaches it. Scheduling config should fail
closed.

### P1: Typed workflow actions and target matrices

Keep `agent: <raw prompt>` as the universal escape hatch, but add a structured form:

```yaml
action:
  workflow: sase/refresh_docs
  vcs_ref: sase-org/sase
  name: "sase_refresh_docs-{target.project}-@"
  group: chop
  inputs:
    project: "{target.project}"
    gh_ref: "{target.gh_ref}"
    threshold: "{target.threshold}"
targets:
  - {project: sase, gh_ref: sase-org/sase, threshold: 100, every: 3h}
  - {project: sase-core, gh_ref: sase-org/sase-core, threshold: 25, every: 24h}
  - {project: sase-github, gh_ref: sase-org/sase-github, threshold: 25, every: 24h}
  - {project: sase-nvim, gh_ref: sase-org/sase-nvim, threshold: 25, every: 24h}
  - {project: sase-telegram, gh_ref: sase-org/sase-telegram, threshold: 25, every: 24h}
```

Normalize the structured form to the same prompt/launcher path so runtimes remain uniform. Benefits are validation,
completion, provenance, readable inventory, safer renames, less quoting, and one source of truth for repeated jobs.

Matrix expansion must produce stable target-specific chop IDs and state directories. A single shared timestamp keyed only
by the parent chop name would be incorrect.

### P1: Keyed configuration composition and activation

Accept a map form in addition to the current list:

```yaml
lumberjacks:
  telegram:
    chops:
      tg_inbound:
        enabled: true
        action: {script: tg_inbound}
```

Normalize legacy list entries internally. Keyed maps would let config layers patch a timeout, set `enabled: false`, or
override an action without duplicating the whole entry. Provenance can be reported per chop field.

Add `enabled` at both lumberjack and chop level, plus CLI/Admin Center enable/disable that writes an explicit managed
overlay. This aligns with the earlier preferred plugin/chop installation research: package installation can expose
capabilities while activation remains an intentional user decision.

For credentialed plugins, support references rather than secrets embedded in config, for example environment-variable
names or a provider-defined credential source. The current Telegram doctor logic is a good precedent. Core should not
become a secret vault.

### P1: Explicit cadence, retry, and backoff policy

Replace the implicit failure asymmetry with visible policy:

```yaml
schedule:
  every: 60m
  anchor: action_accepted
retry:
  on: [check_error, launch_error]
  delays: [1m, 5m, 15m]
  max_attempts: 3
```

The trigger result protocol makes retry classification tractable: a healthy `no_op` is not a failure, provider/network
errors can be retryable, and action failures can follow the existing provider retry machinery or a chop-specific policy.

Persist `next_eligible_at` so daemon restarts do not erase backoff. Add deterministic jitter for fleet/load spreading.
Avoid holding a lumberjack's entire tick inside sleep-based retries.

### P2: Richer scheduling and runtime management

Add schedule forms alongside `every`:

- `cron` plus an IANA timezone;
- one-shot `at`/`in` jobs;
- deterministic jitter/stagger;
- optional catch-up policy (`skip`, `once`, or bounded replay);
- quiet windows or maintenance calendars.

The global timezone already exists, so a per-job timezone can default to it. These features remain valuable, especially
for human-facing reports, but none of Bryan's current custom chops is blocked by their absence. They should follow the
more pressing trigger/lifecycle work.

Also add `sase axe reload` or config watching once keyed identity and validation exist. Hot reload before stable identity
would make state migration and duplicate detection harder.

### P2: Per-chop observability and configurable retention

Current aggregate metrics do not answer which chop is failing or how often a trigger finds work. Add bounded-cardinality
metrics keyed by lumberjack/chop, not repository or event ID:

- probe outcomes (`action`, `no_op`, `check_error`);
- action launches and terminal outcomes;
- probe/action durations;
- retry count and backoff state;
- skipped-by-concurrency count;
- last successful action timestamp.

Make run-history retention configurable globally and per chop, and add a read-only `sase axe chop runs` CLI/JSON surface.
Keep high-cardinality target/event detail in run metadata rather than Prometheus labels.

## What should remain outside lumberjack config

### Multi-step workflow logic

Xprompt workflows already provide typed inputs, conditionals, outputs, steps, agent launches, waits, and cleanup. AXE
should reference and supervise them, not duplicate the workflow language in chop YAML. File scanning and multi-agent
fan-out in `pylimit_split`, or update+polish sequencing in `refresh_docs`, remain workflow concerns.

### Provider business logic

The core should define extension interfaces for triggers, credentials diagnostics, and actions. GitHub conclusion
classification/log retrieval belongs in `sase-github`; Telegram update and notification semantics belong in
`sase-telegram`. This also follows the Rust core boundary: shared scheduling/state contracts belong in the backend, while
provider-specific operations remain provider implementations.

### Arbitrary shell gates

Git history shows `gate:` was added to prevent pointless `pylimit_split` agent spawns, then removed after discovery moved
into the xprompt. Restoring it would make configuration opaque, shell-dependent, difficult to validate, and easy to run
from the wrong workspace. A typed trigger or executable probe with a versioned result contract preserves the useful
preflight while avoiding those problems.

### A large catalog of opinionated built-in jobs

Bryan's custom chops are valuable because they are policy: audit every 200 commits, refresh these five repositories,
repair these CI failures, use these ChangeSpec naming conventions. SASE should make such policies concise and safe, not
hard-code them all as universal defaults.

## Suggested migration path

### Phase 0: Safety and truthful docs

1. Make duration/interval parsing fail closed with config paths and provenance.
2. Validate duplicate chop identity and field applicability.
3. Extend doctor to resolve agent/xprompt workflows and typed inputs.
4. Document that `timeout`/custom `env` do not currently apply to agent chops and that direct agent chops are not governed
   by `max_agent_runners`.
5. Add regression tests for these semantics before changing them.

### Phase 1: Result and checkpoint protocol

1. Introduce versioned `ChopProbeResult` and `ChopActionResult` wire types in the shared backend boundary.
2. Add `SASE_CHOP_RESULT_FILE` for executable probes/actions.
3. Store structured result fields beside existing logs without breaking current entry points.
4. Provide atomic scoped checkpoint helpers and explicit checkpoint timing.
5. Render `no_op`, `check_error`, `action_running`, and final action status in CLI/TUI.

Migrate `gh_actions_fix` first as the richest acceptance test. Its existing bash tests already cover event classification,
dedupe, failed-log fallback, ChangeSpec guards, prompt construction, and summaries.

### Phase 2: Trigger/action and lifecycle supervision

1. Add generic trigger/action config and plugin registration.
2. Link launched agents/workflows back to chop runs through existing agent metadata and completion artifacts.
3. Add keyed global concurrency and ChangeSpec-query inhibition.
4. Apply real caps to direct configured agent actions.

Migrate `sase_fix_just` next. Its custom wrapper should collapse to a ChangeSpec inhibition rule plus a typed workflow
action.

### Phase 3: Typed matrices and config composition

1. Add structured workflow actions with xprompt input validation.
2. Add target/matrix expansion with stable derived identities.
3. Accept keyed chop maps and `enabled` overlays.
4. Collapse the five docs entries into one target matrix.
5. Consider a reusable `git.commits_since` trigger and migrate the audit/docs markers.

### Phase 4: Scheduling and operational polish

1. Add retry/backoff/jitter with persisted eligibility.
2. Add cron and one-shot schedules.
3. Add CLI run-history queries and retention settings.
4. Add validated hot reload and individual pause/resume.
5. Add per-chop outcome metrics.

## Acceptance criteria derived from Bryan's chops

A new design is materially better only if it can express all of these without losing current behavior:

1. Poll two Telegram plugin scripts every 5s with credential-source diagnostics and no credentials in logs.
2. Check Python size limits hourly without launching an LLM agent/workspace when no file qualifies; when files qualify,
   preserve the existing workflow's fan-out and wait chaining.
3. Run `fix_just` hourly only when no matching open repair ChangeSpec exists, with the inhibition lasting beyond the
   short launcher process.
4. Audit Git commits at a threshold, recover when a marker SHA disappears, and checkpoint only at the configured action
   phase.
5. Configure one docs policy across five typed repository targets with two distinct cadences/thresholds.
6. Detect failed GitHub Action run attempts per repository, retrieve bounded evidence, avoid replay after restart, and
   allow unrelated repositories to proceed when one repository already has an open fixer.
7. Show no-op, degraded check, launched action, and final action status separately in AXE history.
8. Prevent the eight direct agent chops from exceeding an explicit resource policy across lumberjacks.
9. Preserve the current raw script and raw prompt escape hatches.
10. Preserve manual CLI/TUI runs, live output, timeout kill, durable dedupe, and bounded history.

## Bottom line

Lumberjacks do not need to become a second workflow engine. Their current strengths are process supervision, periodic
polling, context delivery, history, dedupe, and operator visibility. Bryan's custom chops show that the missing middle is
the reusable automation control plane between “tick” and “run this prompt.”

Build that middle around typed triggers, stateful event keys, structured outcomes, lifecycle-aware concurrency, and
validated actions. Then let xprompts own multi-step work and plugins own provider details. This would turn the current
collection of capable but bespoke wrappers into concise configuration while preserving the flexibility that made those
wrappers possible.

## Source map

Paths below are relative to the SASE primary repository unless prefixed `chezmoi:` or `research:`.

### Current implementation

- `src/sase/axe/config.py:18-176` — parsed fields and duration behavior.
- `src/sase/config/sase.schema.json:365-494` — declared AXE/lumberjack/chop schema.
- `src/sase/config/core.py:92-137,289-364` — merge order and list semantics.
- `src/sase/default_config.yml:248-298` — built-in lumberjacks and chops.
- `src/sase/axe/lumberjack.py:143-389,409-487,534-575` — tick eligibility, concurrency, cadence, dedupe, and schedule.
- `src/sase/axe/chop_runner_script.py:143-340` — script dedupe, environment, timeout, and outcomes.
- `src/sase/axe/chop_runner_agent.py:70-178` — agent launch, immediate terminal history, and dedupe.
- `src/sase/axe/chop_agents.py:27-76,207-237` — identity variables and durable live registry.
- `src/sase/axe/chop_script_context.py:24-93` — external script context contract.
- `src/sase/axe/chop_script_runner.py:18-53,108-227` — discovery and streamed process execution.
- `src/sase/axe/_state_chops.py:20-61,117-181,254-330` — statuses, metadata, and ten-run retention.
- `src/sase/axe/chop_inventory.py:69-166` and `src/sase/axe/chop_doctor.py` — inventory/diagnostics.
- `docs/axe.md:160-347` and `docs/configuration.md:677-783` — documented operator contract.
- `tests/test_axe_lumberjack_config.py:79-175` — invalid duration fallback and parsing tests.
- `tests/test_axe_chop_runner_agent.py:14-127` — agent identity env and launch-only history.

### Bryan's non-built-in configuration and code

- `chezmoi:home/dot_config/sase/sase.yml:96-110` — Telegram lumberjack.
- `chezmoi:home/dot_config/sase/sase_athena.yml:66-129` — custom scheduled agent/script chops.
- `chezmoi:home/bin/executable_sase_chop_sase_fix_just:1-157` — ChangeSpec guard and workflow launch.
- `chezmoi:home/bin/executable_sase_chop_gh_actions_fix:1-550` — provider polling, state, evidence, dedupe, and launch.
- `chezmoi:tests/bash/sase_fix_just_chop_test.sh` and `chezmoi:tests/bash/gh_actions_fix_chop_test.sh` — custom chop
  regression expectations.
- `xprompts/pylimit_split.yml` — deterministic scan and per-file agent fan-out.
- `xprompts/audit_recent_bugs.yml` and `xprompts/audit_recent_improvements.yml` — duplicated Git watermark triggers.
- `xprompts/refresh_docs.yml` — Git watermark plus two-agent docs action.
- `xprompts/fix_just.yml` — conditional repair workflow.

### History and prior research

- chezmoi commit `919ba759` — introduced a `pylimit_split` shell gate to prevent unnecessary spawns.
- chezmoi commit `edf0f1c4` — removed that gate after discovery moved into the workflow.
- SASE commit `0d1f4909e` — removed `gate` from parser, runtime, schema, docs, and tests.
- chezmoi commit `1eda9cd9` — moved `sase_fix_just` behind a script/ChangeSpec guard to prevent duplicate repair
  ChangeSpecs.
- `research:202603/lumberjack_vs_openclaw.md` — earlier scheduler comparison; several observability/timezone conclusions
  are now obsolete.
- `research:202603/refresh_docs_workflow.md` — marker/checkpoint design alternatives.
- `research:202604/email_reading_chop.md` — state, dedupe, activation, and plugin-boundary lessons.
- `research:202605/preferred_plugins_chops_install_strategy.md` — package discovery versus explicit activation.
- `research:202605/sase_chops_rust_repo_research.md` — executable contract and backend boundary.
- `research:202605/dream_chop_agent_chat_distillation.md` — probe-before-agent, checkpoints, budgets, and no-op behavior.
