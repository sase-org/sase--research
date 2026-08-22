# Conditional launch units with `%if`

**Date:** 2026-08-22  
**Status:** Design research  
**Scope:** Prompt directives, xprompt swarms, agent/proc launch planning, and a structured fenced-code argument type

## Executive summary

SASE should implement `%if` as a condition attached to a typed launch unit, not as prompt text, an xprompt workflow step, a synthetic agent, or a persistent proc. The condition should be supplied as one fenced-code value:

````markdown
%if::
```bash
test -f pyproject.toml
```
````

After all xprompt and fanout expansion, each final agent or proc unit receives its own condition. SASE should validate and preview the entire plan, obtain launch approval, evaluate all conditions, and only then allocate agent names, timestamps, artifacts, runner slots, or workspaces. Exit `0` means launch, exit `1` means intentionally skip, and every other exit, signal, timeout, or execution failure is an error that aborts the batch before any unit starts.

This design aligns with [the standalone proc launch-unit research](../standalone_proc_launch_units/standalone_proc_launch_units.md): both features use the same structured `CodeValue`, robust fence parser, interpreter selection, private script-file handling, typed launch plan, and dependency identities. They differ at the lifecycle boundary. A `%proc` body is a durable asynchronous launch unit; a `%if` body is a synchronous, bounded preflight predicate whose only result is eligible, skipped, or error. A false condition must not create a synthetic proc or agent record.

## Decision being made

The design needs to answer five questions:

1. What syntax binds a condition to the intended launch unit without allowing its code to be reinterpreted as prompt syntax?
2. At what point is the condition evaluated relative to xprompt expansion, approval, waits, and workspace allocation?
3. What do true, false, and erroneous conditions mean?
4. How does a skipped launch interact with swarms, `%repeat`, `%alt`, `%wait`, agents, and future `%proc` units?
5. How much of a general `code` argument type must ship with `%if`?

## Relevant current architecture

### Prompt parsing and xprompt expansion

The current directive extractor in `src/sase/xprompt/_directive_extract.py` deliberately protects fenced blocks before finding and stripping `%` directives. `_directive_types.py` has a closed directive registry and stores agent-oriented fields in `PromptDirectives`. The shorthand pass only gives special `::` behavior to `%clan`; there is no general mechanism for a directive to consume an adjacent fence.

The good foundation is `src/sase/xprompt/_fenced_blocks.py`. Its scanner understands backtick and tilde fences, variable fence lengths, indentation, info strings, content spans, and unclosed blocks. By contrast, the Rust fanout implementation in `sase-core/crates/sase_core/src/agent_launch/mod.rs` currently has a simpler backtick-oriented literal-zone scan. A `%if` implementation should not add a third fence grammar.

Xprompt inputs currently include scalar types such as `word`, `line`, `text`, `path`, `int`, `bool`, and `float`. The Python binder stringifies raw values, while Rust frontmatter/catalog schemas and editor metadata enumerate the same closed set. Therefore, adding `code` is not merely adding one enum member: it changes binding, serialization, previews, editor completion, and the contract for preserving literal source.

This matters because xprompt expansion and multi-prompt splitting treat `%`, `#`, `---`, artifact references, and Jinja-like text as syntax in some phases. Once a fence is captured as code, its content must become an opaque value. Raw string substitution followed by another expansion pass would be incorrect and potentially unsafe.

### Launch planning and approval

SASE already separates a pure preview/guard path from approved execution. Launch requests persist the submission working directory and dispatch from that directory after approval. Fanout is expanded before the executor allocates timestamps, names, and workspaces, although the current execution model remains agent-shaped and launches slots sequentially.

That separation supplies the right security boundary:

- Parse, expand, resolve, validate, and preview without running user code.
- Show the condition language, source, working directory, and a digest in the approval surface.
- Run code only after approval.
- Evaluate all conditions before the first resource allocation or spawn, so one later condition error cannot leave a partially launched swarm.

### Existing workflow `if:` is not the right primitive

YAML xprompt workflows already have an `if:` field based on rendered expressions. That condition belongs to a workflow step, not to the launch unit produced by prompt fanout. Its evaluator also treats evaluation errors like false conditions. Reusing it would create surprising differences between direct prompts, markdown xprompts, swarms, and YAML workflows, and it would silently convert condition defects into skipped work.

The implementation should preserve workflow `if:` unchanged and introduce a separate launch-condition contract.

## Reconciliation with standalone proc launch units

The standalone proc proposal reaches the right architectural conclusion: mixed prompt submission should become a plan of typed `LaunchUnit` values, with classification occurring after swarm and template expansion but before agent-only normalization and resource allocation. `%if` strengthens that conclusion because a condition should be equally applicable to an agent unit and a proc unit.

The shared pieces should be implemented once:

| Concern | `%if` | `%proc` | Shared primitive |
|---|---|---|---|
| Body | Predicate script | Workload script | `CodeValue { source, language, info_string }` |
| Parsing | One adjacent closed fence | One adjacent closed fence | Canonical robust fence scanner |
| Interpreter | Bash or Python in v1 | Bash or Python in v1 | Interpreter registry and private script materialization |
| Planning | Unit metadata | Unit variant | Typed `LaunchUnit` plan |
| Execution | Synchronous and bounded | Asynchronous and durable | Process-launch safety utilities only |
| Result | Eligible / skipped / error | Proc identity and terminal state | Typed result vocabulary, not the same lifecycle record |

There are two clarifications to the proc report:

1. The existing Python fence scanner should be the behavioral reference, but the canonical shared implementation belongs in `sase-core` under the Rust core boundary. Python should consume the Rust result through the binding or a thin adapter. Parity tests should cover every existing fence edge case while the implementations are consolidated.
2. Reusing the proc execution machinery must stop below persistence. A condition is not a background task, has no proc identity, creates no proc row or log artifact, and does not need proc monitoring. It may reuse interpreter resolution, environment scrubbing, timeout/termination, output bounding, and mode-`0600` script creation.

This arrangement lets `%if` land before or alongside `%proc` without creating a disposable implementation. It also avoids making the standalone proc work a prerequisite for all conditional launches: the common code/parser and generic launch-plan pieces can land first, followed independently by the condition evaluator and the persistent proc runtime.

## Proposed surface syntax

Use one unambiguous form in v1:

````markdown
%if::
```python
from pathlib import Path

raise SystemExit(0 if Path("pyproject.toml").exists() else 1)
```

Review the Python package layout.
````

Rules:

- `%if::` must appear on its own line.
- Optional blank lines may occur before the fence.
- Exactly one closed fenced block follows it.
- The fence is part of the directive argument and is stripped with the directive; it never reaches the launched model.
- The remainder is the unit's ordinary agent prompt or proc declaration.
- Only one `%if` is allowed per final unit in v1. Users can compose predicates inside one script, avoiding an implicit ordering or short-circuit grammar.
- An omitted language means `bash`. V1 explicitly supports `bash` and `python`; aliases can be added only through the shared interpreter registry.
- Unknown languages, missing or unclosed fences, extra argument fences, and an otherwise empty agent prompt are validation errors.
- The source inside the fence is literal. `%`, `#`, `---`, `$()`, braces, artifact-looking references, and nested prompt syntax are not expanded or interpreted by SASE.

A colon expression such as `%if: test -f ...` should not be supported initially. It mixes shell quoting with directive parsing, makes language selection implicit, and produces a second condition grammar. A parenthesized Boolean DSL is also premature: users need filesystem, repository, and tool checks that a small expression language would quickly fail to cover.

## The `code` argument type

The semantic value should be structured rather than a string:

```text
CodeValue
  source: string
  language: string | null
  info_string: string
```

Keeping `info_string` as well as the normalized language preserves future interpreter options and accurate previews without reparsing source text. It also lets editor tooling recognize that the directive accepts a fenced value rather than a colon, parenthesized, or scalar value.

The complete internal slice includes:

- a canonical core fence parser and wire type;
- a `FencedCode` directive syntax/argument role in the core editor directive registry;
- Python binding/model support that does not coerce `CodeValue` through `str()`;
- round-trip serialization for local xprompts and the Rust xprompt catalog;
- syntax diagnostics, completion, preview redaction/bounding, and literal-zone preservation;
- tests for tildes, long fences, indentation, info strings, blank bodies, unclosed fences, and syntax-like text inside source.

There are two reasonable exposure levels:

1. Keep `CodeValue` internal to fenced directives initially.
2. Simultaneously expose `input: {type: code}` to xprompt authors.

The first is the safer `%if` milestone. A public input type implies that `#template::` argument collection and substitution can transport a fence as a structured value without losing its literal provenance. It should be exposed only when those paths, frontmatter schemas, catalog transport, completion, diagnostics, and previews all work. This is the same completeness requirement identified by the proc research. Internally defining the type now avoids redesign; prematurely advertising it avoids none.

## Evaluation contract

### Three outcomes

The contract should be deliberately narrow:

| Result | Meaning | Batch effect |
|---|---|---|
| Exit `0` | Eligible | Keep the unit |
| Exit `1` | Intentionally ineligible | Mark the unit skipped |
| Exit `>=2`, signal, timeout, or exec failure | Predicate error | Abort before any launch |

This resembles [systemd's `ExecCondition=`](https://lists.freedesktop.org/archives/systemd-devel/2019-September/043401.html) distinction between continue, skip, and failure, but reserves only exit `1` for a normal false result. Systemd treats a wider nonzero range as a skip; for SASE that would hide common shell and Python errors such as exit `2`. The narrower rule is easier to diagnose.

GitHub Actions and GitLab CI both evaluate job conditions before sending work to a runner, and represent false conditions as skipped rather than failed. GitLab also evaluates rules separately for expanded matrix jobs. Those are useful precedents for pre-allocation evaluation and per-final-unit semantics. SASE should not copy GitHub's automatic downstream-skip behavior, however, because `%wait` is currently an ordering/terminal-state relationship rather than a successful-output dependency. See the official [GitHub job condition documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-jobs-with-conditions), [GitHub workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax), [GitHub contexts overview](https://docs.github.com/en/actions/concepts/workflows-and-actions/contexts), [GitLab job rules](https://docs.gitlab.com/ci/jobs/job_rules/), and [GitLab matrix-job control](https://docs.gitlab.com/ci/jobs/job_control/). Airflow's short-circuit operator demonstrates why downstream propagation must be explicit rather than accidental: it provides configurable behavior for skipping downstream work ([Airflow API](https://airflow.apache.org/docs/apache-airflow-providers-standard/stable/_api/airflow/providers/standard/operators/python/index.html)).

### Interpreter, timeout, and output

- Bash runs with `/bin/bash --noprofile --norc`.
- Python runs with `sys.executable`, preserving the installed SASE environment.
- Source is written to a private mode-`0600` temporary file rather than interpolated into `sh -c` or `python -c`.
- SASE must not inject `set -e`, `set -u`, or `pipefail`; doing so changes user code semantics.
- A fixed, bounded v1 timeout should be used. Ten seconds is a reasonable default; timeout configuration can be designed later if real predicates need it.
- Standard output and error are captured with strict byte limits. They are diagnostic output, not prompt input or artifact references.
- False results should normally be quiet. Error results display the language, exit cause, and a bounded stderr/stdout excerpt.

### Working directory and environment

Evaluate in the launch request's persisted submission directory, after confirming it still exists. This follows current LaunchApproval dispatch behavior and gives the condition a stable, previewable meaning. Do not allocate the future worker workspace merely to evaluate a predicate.

The v1 limitation should be documented plainly: `%if` inspects the state visible from the submission directory at approval-time dispatch. It does not inspect a not-yet-created worker workspace, and it does not wait for an earlier unit to modify state. Conditions that need prior outputs require a later scheduler/context design rather than hidden reevaluation.

Start from the existing proc environment-scrubbing policy, then add only explicit launch metadata such as:

```text
SASE_CONDITION=1
SASE_LAUNCH_CWD=<persisted cwd>
SASE_PROJECT=<display name>
SASE_PROJECT_FILE=<resolved project file, if any>
SASE_UNIT_INDEX=<stable plan index>
```

Agent identity, artifact-directory, chop context, and proc identity variables should be removed. The approval preview must show the working directory and the names of injected variables. It should not dump secret-bearing inherited values.

## Ordering in the launch pipeline

The target pipeline is:

1. Parse frontmatter and split top-level prompt swarms using fenced literal zones.
2. Expand markdown xprompts, xprompt swarms, templates, and substitutions until stable.
3. Expand `%alt`, `%repeat`, model variants, and other fanout into final logical units.
4. Parse `%if::` and its adjacent fence from each final unit. Strip both while retaining a `CodeValue` on the unit.
5. Classify the unit as agent or proc, assign stable logical unit IDs, compile waits/references to those IDs, resolve projects, and capture the condition working directory.
6. Validate the entire typed plan. Produce a pure preview and request authorization; do not execute predicates here.
7. After approval, evaluate every condition serially in source order and collect all eligible, skipped, and error results.
8. If any condition errored, abort with no spawns. Otherwise prune skipped units, resolve waits on them as already terminal, then allocate identities/resources and dispatch eligible units.

Evaluating per final unit after `%alt` and `%repeat` expansion is important. It gives each visible branch a real launch decision, makes previews match results, and naturally extends to xprompt swarms whose segments target different projects. Even identical condition source should run once per unit in v1; caching would assume purity that arbitrary code does not have.

All conditions must finish before the first launch. The current preview claims all-or-nothing behavior, and this ordering makes that true for predicate errors. It also ensures a false condition consumes no agent name, timestamp, artifacts directory, runner slot, or workspace preclaim.

## Swarms, waits, and skipped identities

### Swarms and fanout

`%if` applies to the final segment where it appears. If a parent xprompt expands into several swarm segments, each segment may inherit or introduce its own fenced condition according to normal template expansion, after which each result is parsed independently. `%alt` and `%repeat` copies receive separate condition evaluations.

For example, these are two independently gated swarm units:

````markdown
%if::
```bash
test -d sase/repos/linked/sase-core
```
Review the Rust launch-plan boundary.

---

%if::
```bash
test -d src/sase/xprompt
```
Review Python directive extraction.
````

The top-level `---` splits the swarm, while any separator-looking text inside either code value remains literal. The resulting preview contains two units and two predicates.

A false condition becomes a first-class `Skipped` launch outcome in the batch receipt. It must not create a fake agent, proc, `done.json`, artifact directory, or workspace. CLI/TUI/LaunchApproval responses should report launched and skipped counts and allow inspection of the predicate result.

### Wait semantics

The proc research already identifies the need to compile waits against stable logical launch-unit IDs before names and resources exist. `%if` makes that a correctness requirement.

Recommended semantics:

- A skipped unit is terminal, so a pure ordering wait on it is immediately satisfied.
- A bare `%wait` must bind to the preceding logical unit before condition pruning. It must not silently retarget to the preceding surviving unit.
- Explicit external named waits retain their current meaning.
- A value-producing reference to a possibly skipped unit—fork state, agent output, artifact path, or similar—must not be fabricated. In v1, reject such a dependency during plan validation unless the consumer has an explicit future-safe mechanism for absence.

SASE should not automatically cascade-skip all downstream waits. That would redefine `%wait` as a success dependency. A later typed dependency system can add policies such as `terminal`, `succeeded`, `present`, or `always`; `%if` should not smuggle that larger semantic change into v1.

## Alternatives considered

### Boolean expression language

A declarative expression could be statically inspected and safely evaluated, but a useful version would need variables, filesystem predicates, command availability, project metadata, string operations, and clear portability rules. It would become a second language before actual use cases are known. Structured code offers immediate utility and shares machinery already needed by `%proc`.

### Inline shell expression

`%if: test -f file` is concise, but quoting, multiline commands, interpreter choice, and directive delimiters become ambiguous. It also encourages execution through a shell command string. The fenced form is more verbose but inspectable and mechanically safe.

### Reuse YAML workflow `if:`

This would gate workflow steps rather than the generic launch units produced by direct prompts and swarms. It would also inherit silent-error-as-false behavior. It is the wrong abstraction level.

### Launch a proc to decide

A condition is not durable work and should not require monitoring, a proc row, a session, or a log artifact. Treating it as a proc would pollute history and complicate waits. Sharing only low-level execution safety gives the benefits without the lifecycle mismatch.

### Evaluate while launching each slot

This fits the current sequential executor but can partially launch a swarm before a later predicate fails. It also allocates resources too early. Batch preflight is the more coherent contract.

## Diagnostics and observability

The approval preview for each conditional unit should show:

- unit index and kind;
- condition language;
- full source or the existing bounded/redacted source presentation;
- SHA-256 digest of the exact source and interpreter metadata;
- evaluation working directory;
- timeout and the true/false/error exit contract.

The post-dispatch result should distinguish `launched`, `skipped-condition-false`, and `condition-error`. Persist this on the launch request/batch receipt rather than in agent history. The skipped record should include the digest, evaluation timestamp, duration, exit status, and bounded diagnostic output. This makes approval delays and changing checkout state debuggable without inventing an agent artifact.

## Security and reliability considerations

The directive executes arbitrary user-supplied code with the user's authority. It is not a sandbox boundary. The protections are therefore about informed authorization, predictable execution, bounded resource usage, and avoiding accidental reinterpretation:

- Never execute during parsing, preview, completion, or guard evaluation.
- Include the exact code and execution context in the approval request.
- Preserve code as a literal structured value across every expansion boundary.
- Use argument-vector execution and private files, never command-string interpolation.
- Scrub transient SASE identity/context variables and bound time/output.
- Treat all parse and runtime anomalies as errors, not false predicates.
- Validate every unit before executing the first predicate, then evaluate every predicate before launching the first unit.
- Avoid condition-result caching until the language is constrained enough to establish purity.

Because this is new user-reaching behavior, implementation should begin behind a disabled SASE feature flag created through the normal `sase flag new` workflow. The flag should cover parsing through execution so disabled clients do not partially understand the directive.

## Test and rollout plan

The minimum convincing test matrix is:

- parser tests for backtick/tilde fences, long fences, indentation, info strings, optional blank lines, missing/unclosed/extra fences, duplicates, and code containing `%`, `#`, `---`, Jinja, and artifact-like text;
- Rust/Python parity tests while fence parsing moves into core;
- round-trip tests for `CodeValue` over the binding and launch-plan wire;
- Bash and Python true, false, exit `2`, signal, timeout, interpreter failure, and bounded-output tests;
- proof that preview and authorization do not execute code;
- proof that false units allocate no names, timestamps, artifacts, runner slots, or workspaces;
- proof that any predicate error prevents every launch in the batch;
- xprompt swarm, `%alt`, and `%repeat` tests showing per-final-unit evaluation;
- bare and explicit `%wait` tests showing skipped units are terminal and are not removed before dependency compilation;
- LaunchApproval delay tests showing the persisted working-directory contract;
- parity across direct CLI launch, ACE/TUI launch, and agent-initiated LaunchApproval;
- regression tests showing YAML workflow `if:` is unchanged;
- environment tests proving agent/proc/artifact identity is scrubbed and only documented metadata is injected.

A practical delivery sequence is:

1. Consolidate robust fence parsing and add internal `CodeValue` plus editor directive metadata in `sase-core`.
2. Carry structured code through Python bindings and typed launch-plan wires, with no public `input: type: code` promise yet.
3. Generalize plan identities, dependency compilation, preview, and outcomes so skipped units are representable before resource allocation.
4. Add the bounded condition evaluator, batch preflight, diagnostics, and feature-flagged `%if::` surface.
5. Add `%proc` using the same code/interpreter primitives and the persistent proc lifecycle described in the standalone report.
6. Expose general xprompt `type: code` only after structured argument collection, substitution, schemas, catalog transport, and editor tooling are complete.

## Recommended solution

Implement `%if::` as a feature-flagged, fenced-code condition on the generic typed `LaunchUnit`:

````markdown
%if::
```bash
test -f pyproject.toml
```

Inspect the project only when it exists.
````

Define the argument as a core-owned `CodeValue`, using a single robust fence grammar shared with `%proc`. Parse it only after xprompt/swarm/alt/repeat expansion, preserve the body as an opaque literal, attach it to each final logical unit, and compile waits before pruning. Preview the exact condition without executing it; after approval, run all predicates serially from the persisted submission directory with a scrubbed environment, private script files, bounded output, and a ten-second timeout. Exit `0` keeps the unit, exit `1` records a first-class skip, and any other outcome aborts the whole batch before names, artifacts, workspaces, or processes are allocated.

Keep condition execution synchronous and receipt-oriented rather than representing it as a proc. Share its code parser, interpreter registry, file materialization, environment scrubbing, timeout, and termination utilities with standalone proc launch units. Make a skipped unit terminal for `%wait`, never retarget a bare wait after pruning, and reject value-producing references to possibly absent units until typed optional dependencies exist. Initially keep `CodeValue` internal to fenced directives; publish general `input: type: code` only when every binding, serialization, expansion, diagnostic, preview, and editor path preserves its structured literal semantics.
