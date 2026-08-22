---
create_time: 2026-08-22
updated_time: 2026-08-22
status: final
tags: [xprompt, directives, launch-units, proc]
---

# Conditional launch with `%if` and a `code` argument type

## Research question

How should SASE add a `%if` prompt directive that launches an agent shell or proc
shell only when a condition holds, with that condition specified by a new fenced-code
argument type — especially inside xprompt swarms?

This is architecture research, not an implementation plan. It inspects the current
tree (sase `eae9cf76b`, sase-core `fc9e98c`) and reconciles the proposal with
[standalone proc launch units](standalone_proc_launch_units/standalone_proc_launch_units.md),
the existing directive / wait / workflow-condition machinery, and earlier research on
directives vs xprompts and `%repeat` STOP.

## Executive recommendation

Treat `%if` as a **launch-unit admission predicate**, not as a workflow Jinja `if:`,
not as a `%wait` variant, and not as template-time `{% if %}`. A mixed swarm should
still expand into typed launch units (`Agent` or `Proc`). Each unit may carry at most
one `%if` whose argument is a structured `CodeValue`. After the unit's `%wait`
dependencies become terminal — and before it claims a workspace, occupies an LLM
runner slot, or spawns a proc child — SASE evaluates that code. True admits the unit.
False publishes a terminal `skipped` status and never runs the payload.

The missing primitive is not unique to `%if`. The proc-launch research already
requires a complete `type: code` slice plus `::` + fence parsing so `%proc` can take a
literal script. `%if` should be the second consumer of that same type, not a
one-off fence parser.

Recommended surface:

````text
%if("test -f Cargo.toml")
%if(bash="test -f Cargo.toml")
%if(python="from pathlib import Path; Path('Cargo.toml').exists()")

%wait:review
%if::
```python
from pathlib import Path
from sase.launch_conditions import waited

waited["review"].succeeded and Path(waited["review"].workspace, "needs_fix.md").exists()
```
%id:fix
Fix the issues found by review.
````

Do **not** land `%if` by adding the name to `_KNOWN_DIRECTIVES` and hoping extraction
strips it. The same trap the proc research called out for `%proc` applies: a known
directive whose fence is not captured as a literal argument will either leak code into
the model prompt or drop the predicate while still launching the unit.

## 1. Alignment with stand-alone proc launch units

The proc report is the right parent architecture. `%if` should extend it, not fork
it. Points of agreement, and the few places this note tightens or fills a gap:

| Proc-launch finding | `%if` consequence |
| --- | --- |
| Mixed submissions become typed `LaunchUnit`s (`Agent` \| `Proc`) | `%if` is a field on that unit, not a third kind |
| Classification happens after swarm expansion, before agent-only normalization | `%if` must be recognized on the same pass as `%proc`, while fences are still attached to the directive |
| `%proc::` needs a real fenced-code parser; today's `%clan...::` captures prose | Share that parser. `%if::` and `%proc::` are the same grammar with different consumers |
| Land a complete `CodeValue` / `type: code` slice before advertising it | `%if` is blocked on that slice. Do not invent a second "condition block" type |
| Script text is a literal zone after xprompt expansion | Same for `%if` fences in the composed prompt. Do not re-expand `#`, `%`, `---`, `$()`, or refs inside them |
| Unlabelled fence language is preserved as `null`; `%proc` maps `null` → Bash | Keep that mapping for `%proc`. `%if` should use the **same** default so unlabeled fences are not consumer-specific |
| `%wait` should mean "the preceding launch unit is terminal"; success is a separate condition | `%if` **is** that separate condition. This is the cleanest product justification for the wait generalization |
| Supervisor waits first and leases second | Evaluate `%if` after wait and before lease / runner admission, for both proc and agent units |
| Do not expose a known-but-unlaunchable directive | Parse, strip, and honor `%if` only behind one beta flag, together with the `code` type |
| `%repeat` / `%alt` deferred for proc v1 until typed-unit fan-out is stable | `%if` applies **after** those expansions. Each resulting unit evaluates independently |

The proc report's `LaunchUnit` sketch should grow an optional predicate:

```text
LaunchUnit {
  kind: Agent | Proc,
  source_index,
  wait,
  if_condition: CodeValue | null,
  project,
  payload
}
```

Admission sequence, shared by both kinds:

```text
reserve identity
-> start wait (no LLM slot, no operational lease)
-> evaluate %if (cheap, no lease)
-> on false: publish skipped, stop
-> on true: claim workspace / admit runner / spawn child
```

That is the same "wait, then acquire" order the proc report already requires, with one
inserted predicate. It also matches the runner-side post-wake STOP check from
[repeat STOP research](../202606/repeat_stop_variable_consolidated.md), except the
decision is an explicit per-unit predicate rather than a reserved output variable.

### 1.1 Differences worth stating, not papering over

1. **`%if` is a modifier, `%proc` is a classifier.** A segment with `%if` remains an
   agent unit unless `%proc` is also present. Two fences in one unit are valid:
   `%if::` + python fence, then `%proc::` + bash fence.
2. **Python truthiness is predicate-shaped, not job-shaped.** `%proc` runs a script
   for its exit status and logs. `%if` must answer a boolean. A Python file whose last
   statement is an expression should use that value; otherwise the process exit code
   wins. Bash is always the exit code. This mapping is consumer-specific and does not
   change `%proc`.
3. **Skip must be a first-class terminal status.** The proc report says dependents
   should unblock when the target is terminal, and that requiring success is a
   separate condition. `%if` false is exactly "terminal but not successful work."
   Today's `%wait` only unblocks on `completed` / `noop` / `epic_approved` /
   `plan_committed`. Implementation has to face that gap (section 5).
4. **Template-time `{% if %}` already exists** and can delete swarm segments before
   they become units. The proc report does not discuss that split; this note does,
   because authors will otherwise jam runtime predicates into Jinja or vice versa.

Nothing in those differences requires backing away from typed launch units, `CodeValue`,
or deferred resource acquisition.

## 2. What exists today

### 2.1 Directives are launch controls, not prompt modules

`%` tokens are a closed vocabulary of runner controls, stripped before the model sees
the prompt
([directives vs xprompts](../202606/directives_xprompts_architecture_consolidated.md)).
The live set in `src/sase/xprompt/_directive_types.py` and the matching Rust
`DIRECTIVES` table in `sase-core` `editor/directive.rs` is:

`auto`, `clan`, `effort`, `final`, `hide`, `model`, `id`, `repeat`, `wait`, plus
`%alt` / `%{}` fan-out and `%xprompts_enabled` as parser control.

There is no `%if`. Unknown `%` names are left in the prompt, so a naive author who
writes `%if` today would send the token to the model.

Argument grammar is shared with xprompts (colon, paren, backtick, plus). The only
`::` directive form is `%clan...::` prose, rewritten to `summary=` by
`preprocess_directive_double_colon_shorthand`. That helper **protects** fenced code
rather than capturing it, which is why it cannot host `%if::` or `%proc::`.

Rust `DirectiveSyntaxForm` is `Bare | Colon | Parenthesized | Plus | BraceShorthand`.
There is no fence form and no `DirectiveValueRole::Code`. ACE, the xprompt LSP, and
runtime parsing all share this contract; `%if` has to be added there, not only in
Python.

### 2.2 Workflow `if:` is the wrong evaluator for swarm launch

YAML workflows already have `if:` on `WorkflowStep`
(`src/sase/xprompt/workflow_models.py`). It is a Jinja2 expression against the
workflow's step context. `_evaluate_condition` renders the expression and treats
anything other than empty / `false` / `none` / `0` / `[]` / `{}` as true. Exceptions
become false — fail-open skip.

That is a good fit **inside one workflow run**, where previous steps have just
written structured outputs into `self.context`. It is a poor fit for markdown swarms:

- Swarm segments do not share a workflow context. They share `%wait`, artifacts,
  output variables, workspaces, and (soon) proc results.
- Launch-time authors need filesystem / git / predecessor inspection, not only Jinja
  over step JSON.
- Fail-open skip would hide a broken predicate. For "only launch if", a crashed
  condition must not look like a calm skip.
- `{% if %}` in an xprompt body already covers template-time omission. Reusing the
  name `if` for a third, quieter Jinja path would make three different `if`s.

Keep YAML `if:` as-is. `%if` is the swarm / prompt-control analogue, evaluated in
code against launch-unit state.

### 2.3 Template-time `{% if %}` can already drop swarm segments

Xprompt `.md` bodies are Jinja-rendered. A swarm author who knows the condition from
invocation arguments can already write:

```jinja
%id:review
Review {{ path }}
{% if fix %}
---
%id:fix
Fix issues in {{ path }}
{% endif %}
```

When `fix` is false, the second unit **does not exist**. There is no identity, no
wait target, no skipped row. That is cheaper and clearer than a runtime skip, and it
should remain the tool for argument-known conditions.

Two limits make it insufficient for the requested feature:

1. `substitute_placeholders` runs `protect_fenced_blocks_only` **before** Jinja, so
   `{{ args }}` inside a fenced block in the xprompt body do not expand. A runtime
   `%if::` fence in an xprompt cannot see invocation args via Jinja.
2. Template-time Jinja cannot see predecessor results, proc exit codes, or files an
   earlier unit wrote into a claimed workspace.

Use `{% if %}` when the decision is a function of xprompt inputs. Use `%if` when it
depends on the world after waits.

### 2.4 `%wait` is "start after success-like completion," not "start after terminal"

`wait_checks` unblocks a named dependency only when the newest matching artifact has
`done.json` outcome in `WAIT_SUCCESS_OUTCOMES`: `completed`, `noop`, `epic_approved`,
`plan_committed`. Failed, killed, stopped, missing, or unknown outcomes leave the
waiter parked. `noop` already satisfies waits and is hidden from ordinary done-agent
lists (workflow ran and had nothing to do).

The agent runner that honors `%wait` is already alive: `wait_for_dependencies()`
writes `waiting.json` and polls. So today a gated agent **does** occupy a runner
process while waiting. The proc report's "wait without an LLM slot" is a change, not
current behavior.

`%repeat` is launch-time fan-out with `%wait` chains, not a runtime loop. STOP is a
post-wake skip that still writes `done.json` so the chain continues. That pattern is
the closest existing "don't actually run this slot" behavior, and it is a useful
implementation analog — not a replacement for an explicit `%if`.

### 2.5 There is no `code` input type

`InputType` in Python and the Rust frontmatter schema are `word`, `line`, `text`,
`path`, `agent`, `int`, `bool`, `float`, `enum`. `#name::` always captures prose into
`[[...]]` as `text`. The proc report's `CodeValue { source, language, info_string }`
is not implemented. `%if` should not ship a private cousin of that type.

## 3. What `%if` is — and is not

| Mechanism | When it runs | If false / unmet | Typical question |
| --- | --- | --- | --- |
| Jinja `{% if %}` in an xprompt body | Template expansion | Segment never becomes a unit | "Did the caller pass `fix=true`?" |
| YAML workflow `if:` | Start of a workflow step | Step `SKIPPED` | "Did the previous step's JSON say `has_changes`?" |
| `%wait` | Admission, blocking | Stay parked | "Has `review` finished successfully?" |
| `%if` | Admission, one-shot, after waits | Skip the unit | "Did `review` actually succeed *and* write `needs_fix.md`?" |
| `%repeat` STOP | Post-wake, after wait | Exit early, still `completed` + `repeat_stopped` | "Did an earlier iteration ask the chain to stop?" |

`%if` is **not**:

- wait-until-true (no polling; that remains `%wait`);
- an else/elif chain (invert in a second unit, or omit);
- an LLM judge;
- a clan/family/tribe identity;
- a substitute for YAML workflow control flow.

It **is** a per-unit gate on already-planned work.

## 4. The `code` argument type

Ship one structured value, as the proc report specified:

```text
CodeValue { source: str, language: str | null, info_string: str | null }
```

Use it in three places in the same slice:

1. Xprompt frontmatter `type: code`.
2. Directive `::` fence arguments (`%if`, `%proc`).
3. Parenthesized keyword/positional string forms that parse into the same value
   (`%if(python="...")`, `%if(bash="...")`).

### 4.1 Parsing

`%if::` / `%proc::` capture **exactly one** closed CommonMark fence after optional
horizontal whitespace and blank lines. Reuse `fenced_block_details`. Unclosed fences,
extra prose between `::` and the fence, and a second fence bound to the same
directive are errors.

After the xprompt that introduced the text has rendered, the fence body is a literal
zone: no nested directive, xprompt, separator, command substitution, artifact
reference, or Jinja pass. The authoring-time exception is the xprompt body's own
Jinja pass, which already expands **outside** fences. Parameterized conditions should
therefore use the runtime API (section 6) or the parenthesized form, where Jinja can
still rewrite the argument string.

Type-directed `#xprompt::` binding: if the next unbound input is `code`, `::` captures
a fence into a `CodeValue`; if it is `text`, keep today's prose capture. An enum
member without that binding would advertise a type that cannot be supplied.

Stringification of `CodeValue` is `source`. Templates may use `.source` and
`.language`.

### 4.2 Languages

v1 languages: omitted, `bash`, `python`. Reject `sh`, `shell`, `py`, `python3` until
each has a contract. Omitted language means Bash for **every** consumer, including
`%if`, so authors are not surprised when they copy a fence from a proc to a
condition.

Python always runs as `sys.executable` (SASE's interpreter, `import sase` works, no
activation scripts). Bash is `/bin/bash --noprofile --norc` on a `0600` temp file, as
the proc report specified for jobs. `%if` should reuse that execution shape, with a
short timeout and no workspace lease.

### 4.3 Why not a Jinja or DSL type instead?

A `type: expr` Jinja snippet would look familiar to workflow authors and would avoid
subprocess overhead. It fails the swarm case: there is no step context, and the
interesting predicates inspect predecessor workspaces and output variables. A tiny
boolean DSL (`file_exists=`, `success=`) is tempting sugar and can be added later as
kwargs; it is not general enough to be the only form. The user-facing request is a
code block, and `%proc` already needs that block type.

## 5. Skip, wait, and identity

This is the load-bearing runtime design.

### 5.1 Allocate identity before skipping

If a skipped unit has no stable name / proc id, `%wait:fix` hangs. Preflight must
reserve identities for every unit, including those that later skip, then compile bare
`%wait` to those identities. That is the same reservation the proc report requires so
mixed-swarm waits have typed targets.

### 5.2 Publish a distinct terminal outcome

Do **not** reuse `noop`. `noop` means "the workflow ran and had nothing to do." `%if`
false means "the payload never ran."

v1 recommendation:

- Write `done.json` with `outcome: "skipped"` and `skip_reason: "if"` (plus a short
  captured reason/stderr preview).
- Hide skipped units from ordinary done-agent lists, as `noop` already is.
- Until wait-on-terminal lands, add `skipped` to `WAIT_SUCCESS_OUTCOMES` so
  `%wait:skipped_unit` unblocks. That is a compatibility shim, not the end state.
- The end state, from the proc report: `%wait` resolves on **any terminal** outcome;
  `%if` (or a later `success=` sugar) is how a dependent requires real success.

A failed **evaluation** (timeout, crash, non-boolean Python result that is not an
exit code) is `failed`, not `skipped`. Broken predicates must be loud. Workflow
`if:` fail-open is the wrong default here.

### 5.3 Do not take scarce resources to evaluate

Target admission (typed launch plan / proc supervisor):

1. Wait with no LLM runner slot and no operational workspace lease.
2. Run the predicate in the supervisor / launch process with a bounded timeout
   (match clan `summary_script`: ~20s, kill-responsive).
3. Only then claim a workspace or admit a provider runner.

Agents-only incremental path, if `%if` must ship before supervisor-side waiting: hook
immediately after `wait_for_dependencies()` returns and before workspace claim /
provider invoke — the same seam STOP uses. That still occupies a runner process
during the wait, which is today's `%wait` cost. It is acceptable as a stepping stone
and unacceptable as the mixed-swarm end state, because a skipped `%proc` must not
pretend to be an LLM runner at all.

### 5.4 `%wait` plus `%if` on the same unit

Prompt order does not matter. Semantic order is always wait, then predicate. A unit
may have both. `%if` without `%wait` evaluates at admission against invocation inputs
and the submitting context only.

Multiple `%if` in one unit: **reject** in v1 (same "one body" rule as `%proc`). AND
can be written inside the code.

`%else` / `%elif`: **defer**. A second swarm segment with the inverted predicate is
the else-branch.

## 6. Condition environment

A predicate that cannot see the predecessor it just waited on is useless in swarms.
Clan `summary_script` and workflow Python steps already prove that SASE should give
user code a documented environment rather than forcing path scraping.

v1 Python API (name illustrative):

```python
from sase.launch_conditions import inputs, waited, current

waited["review"].succeeded          # identity-success outcomes
waited["review"].skipped            # %if false
waited["review"].failed
waited["review"].outcome
waited["review"].vars["NEEDS_FIX"]  # sase var / output_variables
waited["review"].workspace          # claimed workspace dir, if any
waited["review"].artifacts_dir      # agent artifacts; None for stand-alone procs
inputs["path"]                      # bound xprompt args for this swarm invocation
current.project
```

Bash should get the same facts as env vars and/or a small `sase launch-condition`
helper on `PATH`, but Python is the structured default for inspecting JSON-ish
predecessor state. Document both.

Do **not** inject an implicit `from sase.launch_conditions import *` prelude. The
proc report's "explicit imports" rule applies.

Default filesystem view without a lease: the submitting cwd / current project
checkout, which is racy if another agent holds the project. Predicates that care
about files an upstream unit wrote must go through `waited[...].workspace`, not
`Path("needs_fix.md")` in the launch cwd.

No operational lease for the predicate itself. `workspace=true` on `%if` is not a v1
kwarg; if a future case needs a consistent tree, lease as part of the unit after the
predicate, or inspect the waited workspace.

Conditions are a documented read-only, idempotent contract. SASE cannot fully enforce
that. Same trust model as `%proc` and clan summary scripts: user-authored code at
launch, no extra sandbox in v1.

Do not execute the predicate at authorization preview. Show the expanded source,
language, timeout, and waited names. Execution happens at admission.

## 7. Surface contract

### 7.1 Syntax

Accept in v1:

```text
%if("test -f Cargo.toml")
%if(bash="test -f Cargo.toml")
%if(python="from pathlib import Path; Path('Cargo.toml').exists()")
%if:: + exactly one following fenced block
```

Reject:

- empty source;
- duplicate bodies (positional plus `bash=`/`python=`, or `bash=` plus `python=`);
- colon shorthand `%if:test -f foo` (same boundary problem the proc report cited);
- unknown kwargs other than `timeout=`;
- unclosed / extra fences;
- unsupported languages;
- more than one `%if` per unit;
- `%if` with no remaining payload (nothing to gate).

No alias. `%i` is `%id`. `%f` is not worth the collision with "final" / "file."

### 7.2 Python truthiness

1. Parse the source with `ast`. If the last statement is an `Expr`, execute the
   prefix and `bool()` the last expression (so a body ending in
   `Path("Cargo.toml").exists()` works).
2. Otherwise run it as a script; exit code `0` is true, non-zero is false.
3. If the last expression exists but is not boolean-coercible in an obvious way,
   still use `bool()` — and document that.
4. Interpreter crash, timeout, or syntax error: unit **fails**, does not skip.

Bash: exit code only. `test -f` and `sase …` compose naturally.

### 7.3 Compatibility with other directives

| Surface | `%if` behavior |
| --- | --- |
| xprompt swarm expansion, project refs | support |
| `%wait` (agent/proc/bead/time) | support; always evaluated after waits |
| `%id`, `%hide`, `%clan` / tribe on **agent** units | support; skipped units keep identity |
| `%proc` in the same unit | support; predicate then proc payload |
| `%model`, `%effort`, `%auto`, `%final` | allowed on agent units; irrelevant if skipped |
| `%wait(runners=...)`, `%wait(priority=...)` | agent-only; reject on proc units as the proc report says |
| `%repeat`, `%alt` | apply `%if` to each expanded unit |
| YAML workflow `if:` | unchanged, separate |

When the flag is off, `%if` must **error**, not remain in the model prompt and not
silently launch. Same closed-vocabulary rule as other directives.

## 8. Alternatives considered

### A. Reuse YAML `if:` Jinja in markdown swarms

Lowest new surface. No way to inspect waited workspaces or proc results without
inventing a Jinja namespace that is then a worse, stringly-typed version of the
Python API. Fail-open skip is wrong. Rejected as the primary design. Keep it for
workflows.

### B. Make `%if` poll until true

Collapses into `%wait`. Authors would not know which to use. Rejected.

### C. Structured kwargs only (`%if(success=review, file=needs_fix.md)`)

Nice sugar for two common cases, terrible as the only language. Can be layered later
on top of `CodeValue` evaluation. Not v1.

### D. Template-only: require authors to use `{% if %}`

Does not meet the request. Cannot see predecessor results. Fences in xprompt bodies
are Jinja-protected. Rejected as the only mechanism; retained as the argument-time
tool.

### E. Implement `%if` as a tiny proc unit that gates the next segment

A bash/python unit plus `%wait` is already "run a check." Making every condition a
visible proc row would clutter Procs history, force `%wait` boilerplate, and still
need skip semantics for the *following* agent. The directive is the right
compression. The check should not be a peer launch unit.

### F. Skip without allocating identity

Breaks `%wait` and mixed-plan previews. Rejected.

### G. Reuse `noop` for skip

Hides the distinction in listings and in `waited[...].outcome`. Cheap, but it lies.
Rejected.

### H. Agents-only `%if` now, procs later, private fence parser

Would duplicate the `code` type the proc report already says to land first, and would
teach a parser that then has to be rewritten for `%proc`. Sequence the shared slice
once.

## 9. Internal architecture

Cross-frontend planning belongs in `sase-core`, same litmus as `%proc`: CLI, ACE,
editor, and any future web surface must agree on classification, fence capture, wait
targets, and "this unit may skip." Python owns subprocess evaluation, skip
finalization, and the `launch_conditions` API.

Planning order, extending the proc report:

1. Split on top-level swarm separators.
2. Expand xprompt swarms/templates, preserving ordinary literal zones.
3. Recognize and protect `%if` and `%proc` fence spans on every expansion iteration.
4. Classify each final segment (`Agent` or `Proc`) and attach `if_condition`.
5. Fan-out `%alt` / `%repeat` so predicates apply to concrete units.
6. Reserve identities; compile bare waits.
7. Validate the mixed plan (including `%if` syntax) before spawning anyone.
8. Preview, including condition source.
9. Admit: wait → `%if` → payload.

Rust work:

- `InputType::Code` in the frontmatter schema, aliases none, rule text describing
  fenced source plus language.
- `DirectiveSyntaxForm` fence/double-colon form; `DirectiveValueRole::Code`.
- `%if` in `DIRECTIVES` (no alias, parenthesized + `::` fence, optional `timeout=`).
- `LaunchUnit.if_condition: Option<CodeValue>`.

Python work:

- `InputType.CODE` + binding + `::` fence capture.
- `PromptDirectives.if_condition: CodeValue | None`.
- Admission hook / supervisor evaluator.
- `skipped` outcome + listing filters + wait shim.
- `sase.launch_conditions` and tests.

Feature flag: one beta flag covering the `code` type **and** `%if` (and `%proc` if
they ship in the same epic). Create it only with `sase flag new`. Disabled means
`%if` / `type: code` error closed. Do not parse-but-ignore.

## 10. Risks and tests

- **Known directive without fence capture:** predicate stripped, unit always launches,
  or code reaches the model. Classifier + literal-zone tests are mandatory.
- **Jinja-in-fence expectation:** authors will put `{{ path }}` inside `%if::`
  fences in xprompt bodies and it will not expand. Docs and a diagnostic when a
  protected fence contains `{{` after a `%if::` would help; the runtime `inputs`
  API is the real fix.
- **Python script footgun:** a body that is not a last-expression and does not
  `sys.exit` would otherwise skip-never. Last-expression evaluation is the mitigation;
  tests must cover both the `Path(...).exists()` form and `sys.exit`.
- **Wait hang on skip:** if `skipped` is not wait-success and wait-on-terminal has
  not landed, dependents park for 24h then proceed anyway. Ship the shim in the same
  change as `%if`.
- **Success vs skip confusion:** `%wait:fix` after a skipped `fix` will proceed under
  the shim. Authors who wanted "only if fix ran" must add `%if`. Document with
  examples; this is the intended split.
- **Resource leak:** evaluating `%if` after claiming a workspace, or in an LLM
  runner that then skips, burns the scarce thing the predicate exists to save.
- **Preview side effects:** never exec at approve-time.
- **Partial mixed launch:** a syntax-broken `%if` in unit 4 must fail the whole plan
  before unit 1 starts.
- **Name collision with Jinja `{% if %}`:** docs must show them side by side. Do not
  rename to `%when`; the user-facing name is `%if`.

Tests worth requiring:

- agent skipped after `%wait` on a successful predecessor;
- agent skipped after `%wait` on a skipped predecessor (chain of optional units);
- dependent `%wait` unblocks on `skipped`;
- dependent `%if` inspecting `waited["x"].succeeded` does **not** run;
- `%if` + `%proc` in one unit, both fence orders;
- unlabeled fence is Bash for `%if` and `%proc`;
- Python last-expression true/false;
- Python crash → `failed`;
- timeout → `failed`;
- fenced `%wait` / `#refs` / `---` stay literal;
- xprompt-body Jinja does not rewrite `%if` fences, but parenthesized `%if(python=...)`
  does expand;
- flag off → error, no model leak;
- preview shows source and does not exec;
- `%alt` / `%repeat` slots evaluate independently.

## 11. Delivery sequence

This sequence is meant to sit **inside** the proc-launch delivery, not beside it as a
second parser project.

1. **`CodeValue` + fence-after-`::` parser + complete `type: code` slice** (Python
   binding, Rust schema, completion, diagnostics, `#xprompt::` type-directed
   capture, show/preview). No user-facing `%if` / `%proc` yet, or both still flagged
   off.
2. **Rust directive contract for `%if` (and `%proc`)** behind one beta flag. Extractor
   captures fences as literal `CodeValue`s. Unknown/disabled → hard error.
3. **Typed mixed launch plan** with `if_condition` on every unit; stable identity
   reservation; authorization preview of predicates.
4. **Skip outcome + wait shim** (`skipped` wait-success). Prefer landing wait-on-terminal
   in this same step if the proc work is already touching the resolver; otherwise
   ship the shim and record the generalization as follow-up on that epic, not as a
   new task.
5. **Admission evaluator** (supervisor-side for procs; post-wait pre-claim for agents
   until supervisor-side waiting exists) + `launch_conditions` API.
6. **Docs, LSP/ACE completion, both-flag-states tests.**
7. Flag removal once skip, mixed agent/proc, and wait behavior are boring.

If `%proc` is delayed, steps 1–2, 4–6 still yield a valuable agents-only `%if`. Do not
delay the `code` type for that split — it is the argument type the user asked for,
and it is what keeps `%if` from growing a private fence dialect.

## Recommended solution

Implement `%if` as an optional **admission predicate on typed launch units**, using
the `CodeValue` / `type: code` / `%name::` + fence grammar the stand-alone proc
research already specified for `%proc`.

Parse one Bash or Python condition per unit, with parentheses for one-liners and
`::` plus exactly one fence for blocks. After `%wait` resolves and before any
workspace lease or LLM admission, evaluate the code: Bash by exit status, Python by
last-expression truthiness or exit status. True runs the unit. False publishes
`outcome: "skipped"` with `skip_reason: "if"`, keeps the reserved identity so
dependents can `%wait`, and never executes the payload. Evaluation errors fail the
unit.

Give condition scripts an explicit `waited` / `inputs` API so swarm xprompts can
inspect predecessor success, output variables, and workspaces without Jinja-inside-
fences. Leave YAML `if:` and template `{% if %}` alone: they answer different
questions at different times.

This aligns with the proc report instead of competing with it: same launch plan, same
code type, same literal-zone rule, same wait-then-acquire order, with `%if` filling
the "success is a separate condition" hole that report left open. The alternative —
a Jinja prompt directive, a private condition-block type, or skip-without-identity —
would either fail the swarm case or make `%proc` more expensive to land later.
