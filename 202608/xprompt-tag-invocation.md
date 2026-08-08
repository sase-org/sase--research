# Reliable XPrompt Invocation by Tag

Date: 2026-08-08

## Executive summary

SASE already uses xprompt tags as semantic dependency-injection keys: core code asks
for roles such as `mentor`, `diff_file`, or `work_phase_bead`, then invokes whatever
xprompt name currently provides that role. The useful feature is therefore mostly
present. What is missing is a user-facing reference syntax and a reliable, shared
resolution contract.

The current resolver is not reliable enough to expose directly. `get_by_tag()` chooses
the last matching value in a merged Python dictionary and assumes insertion order is
source priority. Overwriting an existing key does not move it, and `get_all_prompts()`
also concatenates all converted Markdown xprompts before all YAML workflows. The result
can disagree with the documented discovery precedence. Meanwhile,
`get_by_tag_strict()` rejects every surviving second name, so a higher-priority custom
xprompt with a different name cannot override a built-in tagged role as the docs imply.
Several tags are intentionally many-valued traits, so “invoke the xprompt with this
tag” is not meaningful for every tag anyway.

The recommended interface is an explicit reserved namespace:

```text
#tag/work_task_bead(bead_id=sase-123)
#tag/mentor(...)
#!tag/some_standalone_role(...)
```

Resolve it through one policy-aware resolver backed by explicit discovery ranks and
provenance. Allow invocation only for singleton or context-scoped role tags; reject
trait tags such as `vcs` and `rollover`. Select the highest-precedence candidate, use
the active VCS provider for VCS-scoped roles, and fail on an unresolved tie. Rewrite to
the canonical target before ordinary argument binding and execution, while retaining
the selector and selected implementation in trace/usage metadata.

## Scope and audit method

I audited:

- the primary SASE checkout at `72ec6aa3a0b79fc344032528c0c5fb2ac965817d`;
- the installed catalog produced by `sase xprompt list` from that checkout;
- the linked `sase-github` plugin at
  `7dd02fcec77649b34cba23ae33f30793311869dd` because it supplies tagged VCS
  implementations visible in the catalog; and
- the linked Rust core at `f56e8653760bc074c0aa2d4ca757542ba8f8e031`
  because it owns editor catalog, completion, hover, definition, and diagnostic
  behavior.

The installed catalog contained 15 tagged definitions and no existing name under the
`tag/` namespace. The inventory below distinguishes tags declared in the enum from
implementations that are actually visible in this environment.

## What xprompt tags mean today

`src/sase/xprompt/tags.py:12` defines a closed `XPromptTag` enum of 15 strings.
`parse_tags()` accepts a comma-separated string or YAML list and rejects any value not
in that enum. Tags survive conversion from `XPrompt` to `Workflow`, appear in the CLI
and editor catalogs, and are recorded with used-xprompt metadata.

The tags are not one homogeneous concept. They currently serve three distinct jobs:

1. **Callable roles** identify one replaceable implementation, such as the mentor
   prompt or the prompt used to work a task bead.
2. **Context-scoped callable roles** identify one implementation after another axis,
   currently the VCS provider, has been selected.
3. **Traits** annotate behavior shared by several workflows. They are predicates, not
   aliases to one callable definition.

That distinction is essential to a safe invocation feature.

### Complete tag inventory

| Tag | Current provider(s) | Live purpose / consumer | Semantic class |
| --- | --- | --- | --- |
| `vcs` | `git`; plugin `gh` | Gives a workspace workflow outermost setup/teardown ordering; the embedded executor permits at most one per prompt (`workflow_executor_steps_embedded_expand.py:197-214`). Also anchors VCS-provider disambiguation. | Multi-valued trait |
| `rollover` | `commit`, `file`, `git`, `json`, `pr`, `propose`; plugin `gh` | Preserves an embedded workflow reference in rebuilt follow-up prompts (`axe/run_agent_exec_plan_artifacts.py:60-89`). | Multi-valued trait |
| `crs` | None visible | `workflows/crs.py:90-105` looks it up, then falls back to the literal name `crs`. Intended to select the Code Review Summary prompt. | Optional singleton role |
| `fix_hook` | `fix_hook` | Axe resolves the prompt used by the hook-fix agent, with a literal-name fallback (`axe/fix_hook_runner.py:169-181`). | Singleton role |
| `mentor` | `mentor` | Mentor prompt construction uses strict lookup; reporting uses non-strict lookup (`workflows/mentor.py:74-120`). | Singleton role |
| `commit` | `commit` | Mentor review appends the selected direct-commit workflow (`ace/tui/actions/agent_workflow/_mentor_review.py:187-194`). | Singleton role |
| `propose` | `propose` | Mentor review appends the selected proposal workflow at the same call site. | Singleton role |
| `make_mentor_changes` | `make_mentor_changes` | Strictly selects the workflow that applies accepted mentor comments (`_mentor_review.py:152-184`). | Singleton role |
| `diff_file` | plugin `pr_diff` | Selects VCS-specific diff context for a mentor prompt; `vcs_hint` tries to choose an implementation from the active provider plugin (`workflows/mentor.py:86-88`). | VCS-scoped role |
| `append_to_pr` | None visible | The embedded executor optionally appends provider-specific context for `create_pull_request` (`workflow_executor_steps_embedded_expand.py:286-304`). | Optional VCS-scoped role |
| `append_to_commit_and_propose` | plugin `prdd` | The same executor appends provider-specific context for commit/proposal finalizers. | Optional VCS-scoped role |
| `create_epic_bead` | None visible | Present in the enum, docs, and parser tests, but no live definition or production consumer was found. | Reserved/stale singleton role |
| `work_phase_bead` | `bd/work_phase_bead` | Strictly selects the per-phase prompt for `sase bead work` (`bead/xprompts.py:38-40`). | Singleton role |
| `work_task_bead` | `bd/work_task` | Strictly selects the task-bead prompt (`bead/xprompts.py:43-45`). | Singleton role |
| `land_epic` | `bd/land_epic` | Strictly selects the final epic integration/landing prompt (`bead/xprompts.py:47-50`). | Singleton role |

The runtime inventory is already evidence that cardinality cannot be inferred from the
number of matches at one moment. `vcs` and `rollover` are designed to have multiple
providers. The three optional/reserved tags currently have none. VCS plugins are
expected to add parallel implementations of `diff_file` and the two append roles.

### How internal tag invocation works

Internal callers do not invoke a tag reference. They call `get_by_tag()` or
`get_by_tag_strict()`, obtain a `Workflow`, then manufacture a conventional reference
using its name. For example, bead work resolves `work_phase_bead` and `land_epic`, then
emits `#<resolved-name>:<bead-id>` (`bead/work.py:374-462`). CRS, fix-hook, and mentor
do the same thing.

This is good dependency-injection intent, but it spreads policy among callers:

- some roles use non-strict lookup plus a legacy name fallback;
- some require global uniqueness;
- some silently use the last match;
- some pass `vcs_hint`; and
- traits are inspected directly with `has_tag()` instead of resolved.

A user-facing feature should consolidate those rules rather than expose the current
split APIs.

## Reliability problems in the existing resolver

### 1. Dictionary order is not discovery precedence

`get_by_tag()` says the merged dictionary is ordered from lowest to highest priority
and returns the last match (`xprompt/tags.py:73-118`). The loaders do build values by
starting with lower-priority sources and calling `dict.update()` with higher-priority
sources (`xprompt/loader.py:197-239`, `workflow_loader.py:630-651`). However, Python
assignment to an existing key replaces its value without changing that key's insertion
position.

One concrete failure shape is:

1. a built-in named `crs` is inserted and tagged `crs`;
2. a plugin named `my_crs` is inserted with the same tag; and
3. a project-local definition named `crs` correctly replaces the built-in by name.

The effective `crs` value is project-local, but its key remains before `my_crs`.
Returning the last tag match selects the lower-priority plugin. This is exactly the
kind of override tag lookup is supposed to make portable.

There is a second ordering distortion: `get_all_prompts()` returns
`{**converted_xprompts, **workflows}` (`loader.py:266-288`). Thus every surviving YAML
workflow key follows every converted Markdown/config xprompt key regardless of source
precedence. A selector must not derive semantic priority from that order.

### 2. Strict lookup does not implement documented override behavior

`get_by_tag_strict()` rejects more than one surviving name. Name-based discovery only
collapses equal names; it does not collapse two differently named definitions with the
same tag. Therefore adding a project-local `my_mentor` tagged `mentor` beside the
built-in `mentor` produces an ambiguity instead of an override.

`tests/test_bead_xprompt_tags.py:171-181` describes a different-name user override but
mocks a registry containing only that override. Its comment assumes the loader yields
one workflow per tag, which the loader does not do. The test therefore does not exercise
the real override situation.

### 3. The fallback policy can hide misconfiguration

When `vcs_hint` cannot be resolved to a plugin, cannot be mapped to a plugin module, or
does not match a provider, `get_by_tag()` falls back to the last match. Missing CRS and
fix-hook tags similarly fall back to conventional names. Those fallbacks are useful for
legacy compatibility inside known workflows, but they are unsafe for an explicit user
selector: a selector should either explain what it selected or fail.

### 4. Python and Rust do not share tag validation or selection semantics

The Python loader rejects unknown tags through `XPromptTag`. The Rust editor catalog's
`parse_tags()` accepts arbitrary strings into a `BTreeSet`
(`sase-core/crates/sase_core/src/xprompt_catalog.rs:2714-2732`). Rust uses sorted
`BTreeMap`s for catalog storage, so it cannot reproduce a resolution scheme based on
Python insertion order. Today that does not affect execution because Rust only presents
tags, but it would create misleading completion, hover, and diagnostics if tag
invocation were added only to Python.

### 5. The terminology already invites confusion

SASE documentation and UI prose often call `#name` references “tags,” while the
frontmatter `tags:` field is separate semantic metadata. A bare `#mentor` could mean
the definition named `mentor`, not “the definition tagged `mentor`.” An invocation
syntax must make that distinction visible.

## Lessons from established selector and plugin systems

The external systems point toward an explicit selector plus an explicit cardinality
and priority contract:

- [Kubernetes labels and selectors](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/)
  explicitly state that labels are not unique and selectors identify sets. They also
  warn that overlapping selectors can create controller conflicts. This is the closest
  analogy to SASE's `vcs` and `rollover` tags: a tag match is naturally a set until the
  consuming operation imposes stronger rules.
- [Python entry points](https://docs.python.org/3/library/importlib.metadata.html#entry-points)
  separate a semantic group/name from the implementation value, and selection returns
  an `EntryPoints` collection. Consumers that require one implementation destructure or
  validate that collection rather than assuming filtering created uniqueness.
- [pluggy's hook call semantics](https://pluggy.readthedocs.io/en/stable/#call-time-order)
  make multi-provider ordering and “first result” behavior part of the public hook
  specification. `tryfirst`/`trylast` are explicit controls. The relevant lesson is not
  to copy pluggy's LIFO rule; it is to make selection order an intentional contract.
- [Debian's alternatives system](https://manpages.debian.org/update-alternatives)
  gives implementations explicit priorities and selects the highest-priority
  alternative in automatic mode, while retaining a manual choice. SASE already has a
  discovery-precedence equivalent to automatic priority, but the tag resolver needs to
  carry that priority as data.

Together these argue against treating an arbitrary tag as a unique alias or choosing a
winner using incidental container order.

## Design goals

A tag invocation design should provide:

1. **Explicit intent.** A reader can tell name invocation from tag selection.
2. **Determinism.** The same effective catalog and context select the same target,
   independent of dictionary or filesystem iteration order.
3. **Safe ambiguity.** A tie produces a diagnostic listing candidates and provenance.
4. **Normal argument behavior.** Parenthesized, colon, plus, text-block, HITL, and
   `#!` forms continue to work.
5. **Override compatibility.** Project and user sources can replace lower-priority
   implementations without copying their names.
6. **Provider context.** VCS-scoped roles select the implementation belonging to the
   active workspace provider.
7. **Observability.** Expansion trace, `show`/`explain`, used-xprompt metadata, hover,
   and definition navigation show both selector and chosen target.
8. **One cross-frontend contract.** CLI, ACE, mobile/editor catalog, and LSP agree.
9. **No behavioral fallback.** Explicit tag syntax never silently degrades to a
   same-named xprompt.

## Options considered

### Bare-name fallback: `#work_task_bead`

Interpret an unknown xprompt name as a tag. This is concise but unreliable. Installing
an xprompt with that name would silently change meaning; typos could unexpectedly
resolve as tags; traces would not reveal the lookup mode; and completion could not
distinguish the two namespaces. Reject.

### Alias generation through `xprompt_aliases`

Generate `tag -> target-name` aliases in merged config. This reuses preprocessing, but
aliases are static name substitutions. They do not encode cardinality, provenance,
provider context, or same-tier ambiguity, and their merge rules would become a second
resolution system. Reject as the implementation mechanism.

### New punctuation: `#@mentor`, `#[mentor]`, or `#tag:mentor`

These are explicit, but each conflicts with an existing surface or requires a parallel
grammar. `#@` opens ACE's xprompt picker; `#tag:mentor` already means “invoke the
xprompt named `tag` with argument `mentor`”; bracket syntax would require changes in
every Python and Rust reference scanner and editor token path. The target's own
arguments also become awkward. Reject.

### Wrapper xprompt: `#by_tag(mentor, ...)`

A dynamic wrapper is possible, but it conflates selector arguments with target
arguments, obscures the selected input schema from completion, and makes marker/kind,
trace, recursive expansion, and definition navigation special cases. Reject.

### Reserved namespace: `#tag/mentor`

This is explicit and is already legal under the xprompt name grammar, including the
existing `__` slash shorthand. Target arguments remain unchanged:

```text
#tag/work_phase_bead:sase-e.2
#tag/fix_hook(hook_command="just lint", output_file=/tmp/out)
```

The approach mirrors SASE's reserved `memory/` and `skills/` reference namespaces.
No currently visible xprompt occupies `tag/`. It still requires a real resolver, but it
minimizes parser churn and gives editor surfaces a clean completion prefix. Accept.

### Separate `role:` metadata

A singular `role:` field would model callable aliases more precisely than the existing
many-valued `tags:` field. It is a reasonable future cleanup, but introducing it first
would migrate all definitions and APIs without solving priority/provenance on its own.
The existing enum already identifies the intended roles. Defer; encode role/trait
policy centrally now and consider a schema split later.

## Proposed resolution contract

### Tag policies

Associate every enum value with one policy in a shared specification:

```text
Trait
  vcs, rollover

SingletonRole
  crs, fix_hook, mentor, commit, propose, make_mentor_changes,
  create_epic_bead, work_phase_bead, work_task_bead, land_epic

VcsScopedRole
  diff_file, append_to_pr, append_to_commit_and_propose
```

Trait tags remain queryable in catalogs and usable by runtime predicates, but
`#tag/vcs` and `#tag/rollover` fail with a message that the tag identifies multiple
behaviors and is not callable.

### Candidate model

Build tag resolution from effective name-resolved definitions. Each candidate must
retain, as structured fields rather than parsed strings:

- canonical xprompt/workflow name;
- tag set;
- kind and canonical marker;
- source ID and display/definition path;
- discovery layer/rank;
- project scope; and
- provider/plugin identity, if any.

Do not use map order as rank. The canonical content-layout source list should provide
the discovery rank in Rust core; Python should consume that result through the binding
or an equivalent thin adapter. This follows the project's Rust backend boundary because
CLI, TUI, LSP, and other frontends need identical answers.

### Selection algorithm

For `#tag/<role>`:

1. Validate that `<role>` is a known tag and its policy is callable.
2. Resolve project context exactly as ordinary xprompt discovery does.
3. Start with the effective definitions carrying the tag.
4. For a VCS-scoped role, derive the active VCS provider from the prompt/workspace and
   retain candidates from that provider. If no provider context exists and more than
   one provider remains, report ambiguity.
5. Find the highest-precedence discovery layer represented by the remaining candidates.
6. If exactly one candidate exists at that winning layer, select it.
7. If multiple different names remain at the winning layer, fail and list each name,
   source, project/provider identity, and the way to invoke it explicitly by name.
8. If none remain, fail. Explicit tag syntax must not fall back to `<role>` as a name.

This lets `my_mentor` in a higher-priority project source override built-in `mentor`,
while two project-local definitions both tagged `mentor` are a visible configuration
error. Same-name shadowing continues to be handled by ordinary discovery before tag
selection.

### Reference normalization and execution

Treat `tag/<role>` as a selector reference, not as a materialized duplicate Workflow.
Resolve it to the target before input binding so all existing argument types and
workflow execution paths operate on the target object. Preserve:

- the original marker (`#` or `#!`) for canonical-marker validation;
- any `!!`/`??` suffix;
- the original argument source; and
- the original source span for diagnostics.

Recursive expansions can introduce tag references, so resolution must participate in
the shared iterative reference-processing path rather than run once only at launch.
The simple-xprompt processor, embedded-workflow executor, used-xprompt scanner, trace,
and unresolved-reference scanner should all call the same reference resolver.

The usage record should contain the canonical target name and an additive field such as
`invoked_as: "tag/work_phase_bead"`. Expansion trace should render a step similar to:

```text
#tag/work_phase_bead -> #bd/work_phase_bead
  reason: highest-precedence provider for role work_phase_bead
  source: default_config
```

That makes a run reproducible even if the provider changes later.

## Editor and command behavior

The structured catalog should expose tag selectors as alias-like records pointing at
the resolved target, including the target's inputs, definition, description, and
canonical name. To avoid doubling the normal picker, show selector records when the
typed prefix is `#tag/` (and optionally in a dedicated “Roles” group), not for an empty
`#` query.

Expected behaviors:

- completion after `#tag/` lists callable tags and target summaries;
- argument completion uses the selected target's input schema;
- hover says “tag role `<role>` resolves to `<name>`” and shows provenance;
- go-to-definition opens the selected target;
- diagnostics distinguish unknown tag, non-callable trait, missing provider, ambiguous
  provider, and marker mismatch;
- `sase xprompt show tag/<role>` and `sase xprompt explain tag/<role>` display the
  winner and rejected candidates/reasons; and
- `sase xprompt expand --trace '#tag/...'` records the selection before expansion.

The Rust editor code already accepts namespaced reference tokens and the catalog wire
already carries tags and definitions. `tag/` therefore fits the lexer, but resolution
and synthetic completion records belong in core so the Python and Rust catalogs cannot
disagree.

## Migration and implementation outline

1. Add the tag policy table and structured resolution result/errors in `sase-core`.
   Extend discovery/catalog records with explicit source rank and provider identity.
2. Reserve `tag/` in the content-layout validation, with the same style of diagnostics
   used for the reserved `memory/` namespace. Audit/deprecate before hard rejection;
   the current visible catalog has no collisions.
3. Expose tag resolution through `sase_core_rs` and a thin Python facade. Replace the
   internals of `get_by_tag()` and `get_by_tag_strict()` with compatibility wrappers
   over the new resolver, then migrate callers to explicit policy-aware calls.
4. Extend the shared Python reference representation to recognize `tag/<role>` as a
   selector and resolve it in both simple and embedded workflow paths. Preserve the raw
   selector in trace and used-xprompt metadata.
5. Add tag selector records/fields to the structured catalog and implement focused
   completion, hover, definition, and diagnostics in Rust/LSP and ACE.
6. Update `show`, `explain`, `list`, docs, workflow schema documentation, and the xprompt
   memory after implementation. Align Rust tag validation with the authoritative policy
   table.
7. Audit the three declared-but-unprovided tags. Either add/restore providers for
   `crs`, `append_to_pr`, and `create_epic_bead`, mark them intentionally optional, or
   remove stale declarations. Do not let their current absence define future policy.

Compatibility can be additive: ordinary `#name` references keep their exact behavior,
and internal callers can continue receiving the selected Workflow through wrapper APIs
while user-facing selectors roll out.

## Verification plan

At minimum, tests should cover:

- every supported argument spelling after `#tag/<role>`;
- inline and standalone marker validation plus HITL suffixes;
- references inside literal/disabled zones and references introduced recursively;
- project-specific catalog selection;
- a higher-priority different-name override winning over a lower built-in;
- the same-name replacement/insertion-order failure case described above;
- same-layer ambiguity producing a stable, provenance-rich error;
- VCS-scoped selection for at least two provider plugins;
- missing VCS context with one candidate (success) and multiple candidates (error);
- rejection of `vcs` and `rollover` as non-callable traits;
- missing and unknown tag diagnostics with no same-name fallback;
- `show`, `explain`, trace, and used-xprompt provenance;
- ACE and LSP completion, argument help, hover, definition, and diagnostics; and
- Python/Rust conformance fixtures that feed the same candidate catalog and expect the
  same resolution result.

## Recommended solution

Implement `#tag/<role>` as a reserved, first-class selector and back it with one
policy-aware resolver in the Rust core. Carry explicit discovery rank and provenance;
never infer precedence from dictionary iteration. Permit singleton roles and
VCS-scoped roles, reject trait tags, use active provider context when required, and fail
on a tie at the winning precedence layer. Resolve to the canonical target before normal
argument binding/execution, while retaining both the selector and target in diagnostics,
trace, and usage metadata. Keep `#name` unchanged and route the existing Python
`get_by_tag*` APIs through the new resolver during migration.
