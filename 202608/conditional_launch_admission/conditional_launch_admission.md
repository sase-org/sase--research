# Conditional launch admission with `%if`

**Date:** 2026-08-22  
**Status:** Consolidated design research  
**Scope:** xprompt directives, swarms, typed agent/proc launch units, waits, and fenced-code arguments

## Executive summary

Implement `%if` as an optional admission predicate on a typed `LaunchUnit`, applicable
equally to agent and stand-alone proc units. Its argument should be the same structured
fenced-code value proposed for `%proc`:

````text
%if::
```bash
test -f pyproject.toml
```
Review the Python package.
````

Expansion and planning remain pure. SASE captures the fence as an opaque `CodeValue`,
validates the whole mixed launch graph, shows the exact condition in LaunchApproval,
and executes no predicate until approval. At runtime a unit reserves a stable logical
identity, waits for its dependencies without consuming a runner or workspace, evaluates
its condition, and acquires execution resources only if eligible.

Use a strict three-way result: exit `0` means eligible, exit `1` means skipped, and any
other exit, signal, timeout, or execution failure means error. A skipped unit is a real
terminal launch outcome for dependency ordering, but it is not a fake agent or proc and
does not receive a worker workspace or LLM slot.

This extends, rather than competes with, the stand-alone proc launch-unit design. `%proc`
classifies what a unit runs; `%if` controls whether that unit is admitted. Both consume
the same core-owned code value, fence grammar, interpreter registry, private script-file
materialization, and process-safety utilities.

## Evidence from the current architecture

The current system has useful pieces, but no safe one-line insertion point:

- `src/sase/xprompt/_fenced_blocks.py` already recognizes backtick and tilde fences,
  variable fence lengths, indentation, info strings, and unclosed blocks. Directive
  extraction protects fences, but `%clan` is currently the only special `::` shorthand;
  adding `%if` only to the known-directive set would strip metadata without binding the
  following block.
- Xprompt input parsing and the Rust catalog/frontmatter contract currently assume scalar
  types (`word`, `line`, `text`, `path`, `int`, `bool`, and `float`). A useful `code`
  type therefore requires end-to-end structured transport, not another enum value.
- YAML workflow `if:` is a Jinja-rendered step condition. It operates inside one workflow,
  catches evaluation failures as false, and cannot consistently gate final markdown-swarm
  units. It should remain a separate feature.
- The launch path expands fanout before allocating concrete agent resources, while the
  stand-alone proc research correctly identifies the need for a typed mixed launch plan,
  stable dependency targets, and wait-before-lease execution.

The Rust core boundary matters here. Fence parsing, directive metadata, `CodeValue`,
typed launch plans, and dependency semantics are shared backend behavior and should be
canonical in `sase-core`; Python should call the binding or a thin adapter. The existing
Python fence scanner is the behavioral reference and should seed parity tests rather
than becoming a second permanent implementation.

## Reconciliation with stand-alone proc launch units

The stand-alone proc report recommends `LaunchUnit = Agent | Proc`, proc-native
identity, typed waits, and the sequence “wait, then lease, then execute.” `%if` fits as
common metadata on either variant:

```text
LaunchPlan { units: Vec<LaunchUnit> }
LaunchUnit {
    logical_id,
    source_index,
    project,
    waits,
    condition: Option<CodeValue>,
    payload: AgentUnit | ProcUnit,
}
CodeValue { source, language, info_string }
```

The shared and distinct responsibilities are:

| Concern | `%if` | `%proc` | Shared substrate |
|---|---|---|---|
| Meaning | admission modifier | unit kind/payload | typed launch plan |
| Execution | synchronous, bounded | asynchronous, durable | interpreter and process safety |
| Result | eligible / skipped / error | proc lifecycle result | typed outcome vocabulary |
| Persistence | plan receipt only | proc record and logs | stable logical identity |
| Resources | none while testing | workspace after waits | sanitized environment |

Do not implement a condition as a tiny proc, a synthetic agent, or a workflow step.
Those approaches pollute lifecycle history or gate at the wrong abstraction layer.

## Surface and code-value contract

### Recommended v1 syntax

Support exactly one block form first:

````text
%if::
```python
from pathlib import Path
raise SystemExit(0 if Path("Cargo.toml").exists() else 1)
```
%id:rust-review
Review the Rust boundary.
````

Rules:

- `%if::` appears on its own line and consumes exactly one following closed fence, with
  optional blank lines before it.
- An unlabelled fence means Bash. V1 supports `bash` and `python`; unknown languages are
  errors.
- Only one `%if` is allowed per final unit. Authors compose multiple tests inside it.
- The directive and fence are stripped from the model/proc payload.
- Fence contents are opaque across every later expansion pass: `%`, `#`, `---`, `$()`,
  Jinja braces, artifact-looking references, and file-inclusion syntax remain literal.
- Empty source, duplicate conditions, missing/unclosed fences, unsupported languages,
  or an empty residual agent prompt are plan-validation errors.

Parenthesized one-line forms such as `%if(bash="test -f Cargo.toml")` are convenient,
and `%proc` research recommends them, but they can follow after the fenced path is solid.
Do not add `%if: ...`; it creates ambiguous boundaries and a shell-quoting dialect.

### `CodeValue`

Use a structured value:

```text
CodeValue {
    source: String,
    language: Option<String>,
    info_string: Option<String>,
}
```

Internally ship this with `%if`. Public `input: {type: code}` should become available
only when type-directed `#xprompt::` fence binding, Rust/Python serialization, template
access, catalog display, completion, diagnostics, and previews all preserve the
structure and literal-zone provenance. This reconciles the reports: the internal type
must not be postponed, but advertising a partially transported public input type is
also unsafe.

## Planning and runtime semantics

### Planning (pure and whole-plan)

1. Split top-level swarms using canonical fenced literal zones.
2. Expand xprompts, templates, embedded swarms, `%alt`, `%repeat`, and model fanout.
3. Capture `%if::` and `%proc::` fences on every expansion iteration before their source
   can be reinterpreted.
4. Classify final segments into typed units; attach conditions to the final unit where
   they occur.
5. Allocate stable logical IDs and compile bare `%wait` against the preceding logical
   unit before any pruning.
6. Resolve projects and validate all syntax, interpreters, directive compatibility,
   references, and graph cycles.
7. Preview the complete plan and request approval. Do not run conditions in preview.

This retains the strongest point from the batch-preflight proposal: every statically
detectable error must fail before any launch.

### Runtime (dependency-aware admission)

After approval, each unit follows:

```text
reserve logical outcome -> wait for dependencies -> evaluate `%if`
    -> eligible: acquire runner/workspace and execute payload
    -> false: publish skipped terminal outcome
    -> error: publish condition error and apply batch failure policy
```

This resolves the main disagreement between the two reports. Evaluating every condition
in one pre-launch batch is attractive for all-or-nothing behavior, but it cannot support
conditions that depend on predecessor results—the important swarm case—and conflicts
with the proc report's wait-before-admission model. Evaluating conditions only as each
slot is launched is correct if the full graph was already statically validated and no
scarce resource is acquired first.

Consequently, SASE should not promise runtime atomicity for dependency-aware conditions:
an earlier independent unit may already be running when a later predicate crashes.
The planner can optionally pre-evaluate dependency-free predicates as an optimization,
but that must not change visible semantics and should not be a v1 requirement.

### Result contract

For both Bash and Python, use process exit status only:

| Result | Meaning | Outcome |
|---|---|---|
| `0` | true | execute payload |
| `1` | false | `skipped`, reason `if` |
| `>=2`, signal, timeout, exec failure | broken predicate | condition error |

Do not interpret Python's final expression specially. Requiring `sys.exit(0|1)` keeps
Bash and Python equivalent, avoids AST rewriting, and makes mistakes diagnosable.

Materialize source in a mode-`0600` temporary file. Run Bash as
`/bin/bash --noprofile --norc script.sh` and Python with SASE's `sys.executable`. Do not
inject shell strict mode. Use a short fixed timeout (ten seconds is a reasonable v1
default), kill the process group on timeout, and bound captured stdout/stderr. Conditions
run after approval in the persisted submission directory unless their documented context
requires a predecessor workspace.

## Waits, context, and skipped units

A bare `%wait` binds before pruning and never retargets. A skipped predecessor is terminal,
so an ordering-only dependent becomes ready. Do not automatically cascade skips: `%wait`
means ordering/terminality, not success.

Conditions need a language-neutral, explicit view of waited results. Instead of a
Python-only implicit import API, write a private JSON context file and expose its path as
`SASE_CONDITION_CONTEXT`. Its versioned schema can include:

```json
{
  "schema_version": 1,
  "inputs": {},
  "waited": {
    "review": {
      "outcome": "succeeded",
      "workspace": "/path/when-authorized",
      "outputs": {}
    }
  },
  "unit": {"logical_id": "fix", "project": "sase"}
}
```

Both Bash (`jq`) and Python can consume this without language-specific magic. Only
explicitly safe output variables and paths should appear; inherited secrets and agent
environment should not. Missing optional outputs remain distinguishable from empty
values. Direct value-producing references to a possibly skipped unit should fail plan
validation unless the consumer handles absence through this conditional context.

Logical identity and receipt persistence are necessary even when no payload starts, but
a skip must not fabricate agent artifacts, `done.json`, a proc row, a worker workspace,
or a model invocation. CLI/TUI results should show eligible, launched, skipped, and
condition-error counts and the relevant bounded diagnostic.

## Security and approval

`%if` is arbitrary code, not a declarative expression. Therefore:

- expansion, planning, previews, and dry runs never execute it;
- LaunchApproval shows language, expanded source (bounded if needed), digest, working
  directory, waits, and names of injected context variables;
- execution occurs only after approval with the same environment-scrubbing policy as
  stand-alone procs;
- no condition output is automatically injected into a prompt;
- false is quiet, while errors show bounded stderr/stdout and the exit cause;
- a disabled feature flag must reject `%if` explicitly rather than leak it to the model
  or silently ignore it.

The arbitrary-code surface is justified because filesystem, repository, command, and
predecessor-result checks would quickly outgrow a new Boolean DSL. A declarative helper
layer can later cover common cases without replacing `CodeValue`.

## Delivery sequence

1. Consolidate the robust fence scanner in `sase-core`, preserving current Python
   behavior with parity tests; add `CodeValue` and directive argument-shape metadata.
2. Complete structured transport and literal-zone protection through expansion,
   serialization, previews, diagnostics, and editor tooling.
3. Introduce typed mixed `LaunchPlan`/result models, stable logical IDs, and typed
   dependency compilation as recommended by the stand-alone proc research.
4. Add feature-flagged `%if` parsing and pure whole-plan validation. Disabled or malformed
   directives fail closed.
5. Add the bounded evaluator, versioned condition-context file, skipped terminal outcome,
   and wait-then-condition-then-resource admission path for agents.
6. Reuse the same contract for proc units; add mixed swarm, skip, failure, cancellation,
   and recovery tests.
7. Expose public `type: code` only when type-directed xprompt binding is complete, then
   remove the feature flag after operational evidence.

Critical tests include long/tilde/indented/unclosed fences; literal `%`, `#`, `---`, `$()`,
and Jinja text; nested expansion; `%alt`/`%repeat` copies; dependency-free and waited
conditions; agent→agent, agent→proc, proc→agent, and proc→proc waits; false versus exit
`2`; timeout and cancellation; skip without resource allocation; no bare-wait retargeting;
context-schema compatibility; and full-plan static failure before any spawn.

## Recommended solution

Build `%if::` as a feature-flagged fenced-code admission predicate on the generic typed
`LaunchUnit`. Reuse the stand-alone `%proc` architecture: one core `CodeValue`, one robust
literal fence grammar, one typed mixed launch plan, stable logical dependency IDs, and
shared interpreter/process-safety utilities. Keep predicate lifecycle separate from proc
and agent lifecycle.

Plan and validate the complete graph before approval. After approval, reserve logical
outcomes, wait for dependencies, then evaluate each predicate before acquiring a runner,
workspace, agent artifacts directory, or proc execution resources. Exit `0` launches,
exit `1` records a first-class terminal skip, and every other result is an error. Keep
`%wait` terminal/order-based; express success requirements inside `%if` using a versioned,
language-neutral condition-context file.

Ship fenced `%if` first and keep `CodeValue` internal until the complete public
`type: code` binding slice works. This yields conditional xprompt swarms now without a
private parser or lifecycle shortcut, while preserving a direct path to stand-alone proc
units and richer declarative conditions later.
