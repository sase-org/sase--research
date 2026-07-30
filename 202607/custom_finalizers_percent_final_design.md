# Custom SASE finalizers and the `%final` directive

Date: 2026-07-30

## Executive conclusion

SASE should replace the special-purpose `run_commit_finalizer()` path with a generic, SASE-owned finalizer engine. A
finalizer should be a versioned declarative definition containing a prompt, a post-prompt executable, optional
preflight behavior, trigger conditions, retry policy, dependencies, timeout, and failure policy. Definitions should be
discoverable from project and user directories, a new `sase_finalizers` plugin resource entry point, and bundled core
resources.

`%final` should select finalizers for one agent run; it should not embed their definitions in the prompt. With no
directive, SASE uses its configured default selection. Repeated selectors modify that selection in order:

```text
%final:lint                  # add lint to the configured selection
%final:!commit               # remove the commit finalizer for this run
%final:none %final:lint      # run only lint; suppress current and future defaults
%final:lint,artifact_index   # add more than one
```

Global configuration should independently support `enable_defaults: false`, which disables every core finalizer marked
as a default, including defaults added by a future SASE release. A name-to-boolean selection map should permit
individual enable/disable choices without relying on SASE's layer-dependent list merge behavior.

The selected, fully resolved DAG must be validated and snapshotted into the run artifacts before the first provider
invocation. The engine then runs it after the provider succeeds but before `done.json`, workspace release, and the
completion notification. Each selected finalizer may run a preflight command; if work remains, each attempt invokes the
same provider with the finalizer prompt, reloads the agent's latest SASE variables, then executes the finalizer script.
The script returns a versioned structured result. Dependencies execute in stable topological order, and blocking
failures prevent dependents from running.

The in-progress `sase-be` epic is a good foundation, not an alternative design. Its `commit_*` variables and
deterministic `sase commit` subprocess should become the implementation of the built-in `commit` finalizer. The generic
engine should land on top of that work to avoid recreating or destabilizing its variable, exclusion, and ordering
contracts.

## Scope and research method

This report examines:

- the current provider-neutral commit finalizer and its lifecycle position;
- prompt directive parsing, stripping, metadata persistence, fan-out, retries, and runner refreshes;
- SASE configuration layering and list-merge behavior;
- plugin resource discovery and diagnostics;
- SASE output variables and the active `sase-be` epic;
- the Rust core boundary and existing versioned wire patterns;
- the script-context and structured-result protocol already used by Axe chops.

The analysis is based on the SASE and `sase-core` source trees, their tests and documentation, git history beginning
with commit `b2190a5e3` ("add provider commit finalizer"), the `sase-be` bead tree, and
`plans:202607/commit_vars_finalizer.md`.

## Current architecture

### The commit finalizer is correctly placed, but intrinsically singular

`src/sase/llm_provider/_invoke.py` calls `run_commit_finalizer()` immediately after the initial
`provider.invoke()` succeeds and before success postprocessing. The later runner lifecycle writes `done.json`, releases
the workspace, and sends the completion notification. This placement is the central invariant worth preserving:
finalization is owned by the process that owns the agent invocation, not by provider-specific stop hooks.

`src/sase/llm_provider/commit_finalizer.py` currently owns all of the following:

- enable/disable checks;
- SASE-run detection;
- project-directory resolution;
- dirty-state collection for the primary, linked, external, and SDD repositories;
- special auto-commits for machine-managed SDD changes;
- follow-up prompt construction and provider invocation;
- retry counting;
- response/usage accumulation;
- artifact naming and result serialization;
- terminal failure when cleanliness cannot be proved.

The May 2026 history shows this was deliberately introduced to replace runtime-specific enforcement and the
Codex-only fallback. That reasoning remains correct. The problem is not the lifecycle seam; it is that the lifecycle
seam directly imports one hard-coded policy.

The single-finalizer assumption also appears in names and compatibility surfaces:

- `commit.finalizer.enabled` and `commit.finalizer.max_passes`;
- `SASE_DISABLE_COMMIT_STOP_HOOK`;
- `commit_finalizer_result.json`;
- `commit_finalizer_pass_<N>_prompt.md` and response artifacts;
- tests patching `run_commit_finalizer`;
- prompt selection code that specially excludes commit-finalizer follow-up artifacts.

A generalization therefore needs a compatibility plan, not merely a loop around the current function.

### The directive parser can support `%final`, but selection must survive stripping

Directive recognition is centralized in `src/sase/xprompt/_directive_types.py`,
`_directive_collect.py`, and `_directive_extract.py`. Known directives are expanded, validated, and stripped before the
model sees the prompt. `_MULTI_VALUE_DIRECTIVES` already establishes the repeated-value model used by `%wait`.

`%final` fits that mechanism naturally:

- add `final` to `_KNOWN_DIRECTIVES`;
- add it to `_MULTI_VALUE_DIRECTIVES`;
- optionally reserve `%f` as its short alias;
- preserve ordered arguments rather than collapsing them into one value;
- add the resolved operations to `PromptDirectives`;
- persist the resolved plan or selection in `agent_meta.json` and a dedicated artifact.

Only adding a `PromptDirectives.finalizers` field is insufficient. Directives are parsed in several planning,
fan-out, static-inspection, deferred-launch, retry, and refresh paths. The authoritative result should therefore be a
launch-time plan artifact that later stages consume, rather than reparsing the raw prompt or reloading mutable
configuration during finalization.

### Configuration lists are a poor representation of selection policy

SASE's merge chain concatenates lists in plugin, machine-overlay, and project-local layers, but replaces them in the
user `sase.yml` layer. A configuration such as:

```yaml
finalizers:
  defaults: [commit]
```

would be awkward to disable from a project-local file: appending an empty list changes nothing, while repeating entries
creates duplicates. This is especially dangerous for a policy that needs a future-proof "disable every default"
switch.

Selection should instead use scalars and maps:

```yaml
finalizers:
  enabled: true
  enable_defaults: true
  select:
    commit: true
    plugin/audit: false
  overrides:
    commit:
      max_attempts: 2
      timeout_seconds: 300
```

Mappings deep-merge predictably in every layer. `enable_defaults: false` suppresses all current and future core
defaults. `select.<id>: false` disables one finalizer, while `true` opts into a non-default definition. A master
`enabled: false` remains useful as an emergency kill switch.

### The active variables work provides the right handoff

Today, `src/sase/core/agent_output_variables.py` stores scalar strings in `agent_meta.json` under
`output_variables`, guarded by `flock` and an atomic replace. The `sase-be` epic is actively extending this contract to
`str | list[str]`, adding safe clearing, recording `commit_*` intent, and teaching the commit finalizer to execute that
intent before completion.

The relevant planned variables are:

- `commit_message`;
- `commit_exclude_files`;
- `commit_repo_root`;
- optional `commit_name`, `commit_parent`, `commit_bug_id`, `commit_status`, and `commit_method`.

The finalizer engine should not invent a second variable store. It should load the current output-variable map before
preflight, before rendering every attempt prompt, and again immediately before the script. This matters because the
finalizer prompt is expected to cause the agent to call `sase var set` or `sase commit --vars`; a launch-time snapshot
of values would miss exactly the data the finalizer requested.

Definitions may declare the variables they read and consume for diagnostics and cleanup, but the generic engine should
pass the complete normalized map in the script context. Clearing consumed variables should occur only after a
successful script result and should use the locked storage API from `sase-be`.

### Plugin infrastructure already distinguishes providers and resources

Installed plugins currently contribute:

- provider classes through `sase_vcs`, `sase_workspace`, and `sase_llm`;
- package resources through `sase_xprompts`, `sase_config`, and `sase_plugin_manifest`.

Resource modules are discovered deterministically with `importlib.metadata.entry_points()`, can be disabled by
resource-specific environment switches, appear in plugin inventory, and are checked by `sase doctor`.

A finalizer is a resource definition plus executable code, not a provider hook. A dedicated `sase_finalizers`
resource group is a better fit than adding pluggy hooks. It preserves package-relative prompt paths and definition
provenance, allows one plugin to contribute several definitions, and keeps the engine in SASE rather than letting
plugins take over lifecycle dispatch.

Using only `sase_config` plus `sase_xprompts` would require a finalizer to be assembled indirectly from two resources,
would lose the source directory when merged config contains relative paths, and would make validation and catalog
display harder. Recasting finalizers as ordinary YAML xprompt workflows is also a poor fit: workflow agent steps launch
new runner jobs, while a finalizer must continue the current provider invocation, share its model/options and
workspace, accumulate its usage, and complete before the current run's terminal markers.

## Design goals

The design should preserve these invariants:

1. **Supervisor ownership.** Provider plugins expose invocation, but SASE owns whether a run may complete.
2. **Provider neutrality.** Every supported runtime follows the same finalizer plan and script protocol.
3. **Launch-time reproducibility.** Config or plugin upgrades during a long wait must not change that run's finalizers.
4. **Deterministic ordering.** Multiple finalizers form a validated DAG with stable tie-breaking.
5. **No unnecessary LLM turn.** A finalizer already satisfied by main-turn variables or external state can complete in
   preflight.
6. **Live variable reads.** Values written during a finalizer turn are visible to its script and later finalizers.
7. **Bounded execution.** Attempts, process time, output size, and overall finalization time are capped.
8. **Observable results.** Selection, source, attempts, prompts, script results, and failure propagation are durable.
9. **Safe defaults.** Installing a plugin may make a finalizer available, but must not silently make its script run
   after every agent.
10. **Compatibility.** Existing commit configuration, result readers, and the `sase-be` behavior migrate without a
    flag day.

## Recommended user model

### Definition discovery

Use first-wins discovery, mirroring xprompt resource behavior:

1. `<project>/sase/finalizers/`;
2. `~/sase/finalizers/`;
3. installed `sase_finalizers` entry points, sorted by entry-point name;
4. bundled SASE finalizers.

Each source contains one or more `*.yml` definitions. Prompt files are resolved relative to the definition that names
them. Duplicate definitions within one tier are errors; a higher-priority definition may intentionally shadow a
lower-priority definition and the plan records both the winner and shadowed source.

Use a namespaced ID grammar such as `plugin/audit` for third-party definitions. Reserve simple IDs such as `commit` for
core. Only bundled core definitions may set `default: true`; plugin, project, and user definitions require explicit
selection through config or `%final`. This prevents plugin installation alone from activating arbitrary post-run code.

Example plugin packaging:

```toml
[project.scripts]
sase-finalizer-license-audit = "my_sase_plugin.finalizers.license:main"

[project.entry-points."sase_finalizers"]
my_plugin = "my_sase_plugin"
```

```text
my_sase_plugin/
├── __init__.py
└── finalizers/
    └── license_audit/
        ├── finalizer.yml
        └── prompt.md
```

Plugin inventory, `sase plugin show`, and `sase doctor -C plugins.resources` should recognize the new entry-point
group. `SASE_DISABLE_PLUGIN_FINALIZERS` should disable only these resource definitions, while
`SASE_DISABLE_PLUGINS` continues to disable all resource plugins.

### Definition schema

A useful v1 definition is:

```yaml
schema_version: 1
id: plugin/license_audit
description: Ensure newly added dependencies have acceptable licenses.
default: false

trigger:
  events: [success]
  variables:
    any_present: [dependency_files_changed]

depends_on: [commit]
max_attempts: 2
timeout_seconds: 120
on_failure: fail

preflight:
  command: [sase-finalizer-license-audit]

prompt:
  file: prompt.md

script:
  command: [sase-finalizer-license-audit]

variables:
  reads: [dependency_files_changed, license_waivers]
  consumes: []
```

Important schema choices:

- `command` is an argv list. Do not invoke `shell=True`.
- `events` should initially support `success`; other lifecycle events can be added without pretending the current
  `_invoke.py` seam handles provider failures.
- v1 variable trigger predicates can cover `all_present`, `any_present`, equality, and absence. Checks requiring
  workspace, network, or plugin-specific logic belong in `preflight`.
- `preflight` is optional. It receives the same context as the main script and may return success without an LLM turn,
  skip as not applicable, or request a prompt.
- `prompt` may be a package-relative file or inline text. The engine, not the definition, wraps it with the original
  task, accumulated response, attempt count, dependency summaries, and previous script diagnostics.
- `max_attempts` counts prompt-plus-script attempts, avoiding the ambiguity of whether "retries" includes the first
  attempt.
- `on_failure` should be `fail` or `warn` in v1. `fail` is the default. A warning satisfies ordering but remains visible
  in the aggregate result and completion notification.
- `depends_on` names prerequisites. Dependencies that were not otherwise selected are added automatically. If a
  prerequisite was explicitly removed with `%final:!name`, launch validation fails rather than silently overriding the
  user's choice.

The built-in `commit` definition can use its preflight to implement the `sase-be` flow: execute already-recorded commit
intent, accept a clean workspace, auto-commit narrowly proven machine-managed changes, or request a finalizer prompt
when unresolved dirt remains. Its attempt script then executes the newly recorded intent and returns `retry` for
conflict recovery or other remediable failures.

### `%final` selection semantics

Treat `%final` arguments as ordered operations over the configuration-derived selection:

| Form | Meaning |
| --- | --- |
| no `%final` | Use defaults plus the effective `finalizers.select` map. |
| `%final:name` | Add `name` if it is not already selected. |
| `%final:!name` | Remove `name` and remember that it was explicitly removed. |
| `%final:none` | Clear the selection and suppress default/dependency re-addition unless later operations select a finalizer. |
| `%final:a,b` | Apply both operations in order. |
| repeated `%final` | Apply occurrences from left to right. |

Bare `%final` should be rejected with a short usage message rather than acting as a hard-to-see no-op. `none` and the
leading `!` are reserved selector syntax and cannot be definition IDs.

Examples:

```text
# Run configured defaults plus the plugin audit.
%final:plugin/audit

# Keep other defaults, but allow this read-only agent to finish dirty.
%final:!commit

# Ignore every current/future default and run exactly two named finalizers.
%final:none %final:plugin/audit,artifact_publish
```

This additive model avoids a dangerous property of exact-list semantics: `%final:lint` does not accidentally disable
commit enforcement. `none` provides an explicit exact-selection starting point when desired.

Unknown selected names, unknown removals, cycles, self-dependencies, invalid commands, missing prompt assets, and
explicitly removed required dependencies should fail before the provider is invoked. The planned selection should be
shown by prompt inspection and completion tooling.

### Script protocol

Reuse the proven shape of script-backed Axe chops:

- write an atomic, schema-versioned JSON context file;
- pass it via `--context`;
- set a private `SASE_FINALIZER_RESULT_FILE`;
- require a versioned structured result;
- capture stdout and stderr to attempt artifacts;
- validate result data in `sase-core`;
- impose timeout and output-size limits.

The context should include:

```json
{
  "schema_version": 1,
  "phase": "preflight",
  "finalizer": {"id": "commit", "attempt": 0, "max_attempts": 2},
  "run": {
    "agent_name": "example",
    "artifacts_dir": "...",
    "project_dir": "...",
    "workspace_dir": "...",
    "event": "success"
  },
  "variables": {},
  "dependencies": {},
  "previous_result": null
}
```

The script result should use terminal and retryable states explicitly:

```json
{
  "schema_version": 1,
  "status": "succeeded",
  "summary": "Committed the primary workspace",
  "retryable": false,
  "evidence": ["commit_result.json"],
  "details": {}
}
```

Recommended statuses are `succeeded`, `skipped`, `retry`, and `failed`. A nonzero process exit, timeout, missing result,
or malformed result is an infrastructure failure; retry it only when the finalizer's retry policy opts into that
failure class. A normal script-requested `retry` consumes an attempt and is fed into the next prompt. `failed` is
terminal. This is clearer than assigning long-lived semantic meanings to process exit codes.

The context must reload `variables` immediately before each command. After `succeeded`, the engine clears only
definition-declared consumed keys and records the values' names, not secret values, in the public result.

### Execution and dependency semantics

The engine should:

1. Load the launch-time `finalizer_plan.json`.
2. Topologically order the selected definitions, preserving selection/discovery order among equally ready nodes.
3. For each finalizer, evaluate its trigger against the current run and variable context.
4. Run optional preflight. `succeeded` or `skipped` completes the node without a provider call.
5. Render the prompt envelope and invoke the same provider with the same model tier, model override, suppression flag,
   and resolved invocation options as the original turn.
6. Append the response and usage to the accumulated invocation result.
7. Reload SASE variables and run the script.
8. Retry only according to the definition and structured result.
9. On a blocking failure, mark all descendants `blocked`; independent branches need not run after an overall blocking
   failure in v1.
10. Return the accumulated response only after every required finalizer is terminal.

A trigger-skipped dependency counts as satisfied because it was not applicable to this run. A warned dependency also
counts as satisfied, but its warning propagates to the aggregate result. A failed dependency does not.

Scripts run in the primary project workspace by default. A definition may declare another already-resolved run path,
but arbitrary unresolved working directories should be rejected. The engine should pass the existing launch
environment plus finalizer-specific variables without string interpolation through a shell.

### Planning and artifact model

Write `finalizer_plan.json` before the initial provider call. It should contain:

- schema version;
- selector operations and their source;
- every selected definition and why it was selected (`default`, `config`, `directive`, or `dependency`);
- resolved source/provenance;
- prompt content or digest plus durable content snapshot;
- command argv;
- normalized trigger/retry/dependency/failure policy;
- stable topological order;
- a digest of the complete plan.

Do not merely record paths to plugin resources: a plugin upgrade during `%wait` must not change the prompt or
definition that eventually runs. Package scripts cannot be copied safely, so record their installed distribution and
version and fail clearly if the executable disappears.

Use a canonical aggregate `finalizers_result.json` and per-finalizer directories:

```text
finalizers_result.json
finalizers/
└── commit/
    ├── result.json
    ├── preflight.context.json
    ├── preflight.result.json
    ├── attempt_1_prompt.md
    ├── attempt_1_response.md
    ├── attempt_1_context.json
    ├── attempt_1_stdout.log
    ├── attempt_1_stderr.log
    └── attempt_1_result.json
```

The aggregate should record `skipped`, `succeeded`, `warned`, `failed`, and `blocked` nodes, durations, attempt counts,
summaries, evidence, and the overall status. Completion notifications should surface warnings and failures without
dumping raw variables or script output.

### Rust/Python ownership boundary

The finalizer registry is shared backend/domain behavior: a CLI, web frontend, TUI, or editor integration must agree on
definition validity, selection, dependency closure, ordering, and result state. Per the SASE backend boundary, put the
following in a new `sase-core` finalizer module with a versioned Python binding:

- definition and plan wire types;
- manifest/config normalization and validation;
- selector application;
- dependency closure, cycle detection, and stable topological planning;
- trigger predicate validation;
- script-result validation;
- aggregate status reduction.

Keep these in Python:

- `importlib.metadata` and package-resource discovery;
- reading project/user definitions and config layers;
- provider invocation;
- prompt rendering;
- subprocess lifecycle, timeouts, and log capture;
- output-variable storage calls;
- artifact writes and notification integration.

This mirrors existing SASE patterns: Rust plans and validates stable domain state, while Python performs host and
provider side effects.

## Alternatives considered

### A list of Python callback objects

The smallest refactor would define a `Finalizer` protocol and loop over built-in Python instances around the current
function.

This is a useful internal implementation step, but not an adequate public model. User-authored definitions would still
require importable Python code, prompt and retry configuration would have no stable schema, plugin provenance and
diagnostics would be weak, and `%final` planning could not be validated without importing arbitrary code. It also
encourages finalizers to take over orchestration instead of conforming to one engine.

### Treat finalizers as YAML xprompt workflows

Workflows already have prompt, Bash/Python, conditions, repetition, output, environment, and `finally` steps, so reuse
is tempting.

The lifecycle mismatch is decisive. Workflow `agent` steps launch jobs and have their own completion semantics;
finalizer prompts must continue the current invocation before its terminal state. Workflow repetition and failure
handling also do not express dependency closure among independently selected finalizers. Some low-level template and
step-execution helpers can be reused, but finalizers should have their own schema and runner.

### Put definitions only in merged config

This avoids a new entry-point group, and plugins could contribute definitions through `sase_config`.

It performs poorly for prompt/script assets. Merged config loses the contributing file/module directory, so relative
paths are ambiguous. Large inline prompts make `sase.yml` unwieldy, and catalog/doctor output cannot easily report
definition provenance. Config remains the right place for selection and overrides; resource bundles are the right
place for definitions.

## Migration strategy

1. **Finish and land `sase-be` first.** The generic work should consume its string/list variable model, clearing API,
   `commit_*` contract, deterministic commit subprocess, exclusion behavior, and ordering tests.
2. **Add the Rust definition/planning wires.** Cover duplicate IDs, selector operations, default suppression, dependency
   closure, explicit-removal conflicts, stable order, and cycles.
3. **Add discovery, config, `%final`, and launch snapshots.** Update directive completion, prompt inspection, static
   planners, runner refresh/retry preservation, plugin inventory, and doctor diagnostics.
4. **Add the generic Python engine and script SDK.** Initially test with synthetic finalizers before migrating commit.
5. **Wrap the landed commit behavior as bundled `commit`.** Keep its specialized repository inspection and SDD safety
   logic behind the built-in preflight/script implementation.
6. **Provide compatibility reads and warnings.**
   - Map `commit.finalizer.enabled: false` to `finalizers.select.commit: false`.
   - Map `commit.finalizer.max_passes` to the commit override's `max_attempts`.
   - Keep `SASE_DISABLE_COMMIT_STOP_HOOK` disabling only `commit`; add `SASE_DISABLE_FINALIZERS` for the master kill.
   - Dual-write `commit_finalizer_result.json` and legacy pass artifact names for one deprecation window.
7. **Update result consumers and docs.** Prompt-file selection, notifications, artifact retention, sidecar publication,
   configuration schema, plugin docs, and current finalizer tests all contain commit-specific assumptions.
8. **Remove compatibility only after readers have migrated.**

Tests should pin more than the happy path:

- no directive uses defaults;
- `enable_defaults: false` survives future added default fixtures;
- `%final:none` suppresses all defaults;
- additive and negative selectors preserve order;
- a removed required dependency fails at launch;
- cycles and unknown IDs fail before invoking a provider;
- prompt-written scalar and list variables reach the script;
- consumed variables clear only after success;
- preflight can finish without an LLM call;
- retry diagnostics enter the next prompt;
- warning vs blocking failure behavior;
- plugin discovery, disable switches, missing assets, and duplicate precedence;
- runner refresh, deferred launch, spawn-on-retry, repeats, families, clans, and fan-out preserve the exact plan;
- finalizers finish before `done.json` and notification;
- the migrated commit finalizer retains every `sase-be` ordering and exclusion guarantee.

## Recommended solution

Implement a **versioned declarative finalizer registry with a SASE-owned DAG runner**, and make `%final` an ordered
per-run selection overlay rather than a definition language.

Concretely:

- discover definitions from project, user, `sase_finalizers` plugin, and core resource bundles;
- keep plugin finalizers opt-in and permit only core definitions to be defaults;
- configure selection with `enabled`, `enable_defaults`, and a boolean `select` map;
- define `%final:name`, `%final:!name`, and `%final:none`, with repeated/comma-separated operations;
- validate and snapshot the fully resolved plan before provider invocation;
- support optional preflight, then bounded prompt → live-variable reload → structured script attempts;
- execute selected finalizers in stable dependency order before any successful terminal marker or notification;
- put schema, selection, DAG planning, and result validation in `sase-core`, leaving provider and subprocess effects in
  Python;
- migrate the post-`sase-be` commit implementation into the built-in `commit` definition with a compatibility window
  for existing config, environment switches, artifacts, and tests.

This gives users precise per-run control, a future-proof way to disable all defaults, deterministic multi-finalizer
ordering, first-class SASE-variable handoff, and a plugin surface that is powerful without surrendering the run
lifecycle to arbitrary hooks.
