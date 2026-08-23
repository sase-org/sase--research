---
create_time: 2026-08-23
updated_time: 2026-08-23
status: research
---

# Moving Task-Type Guidance to a Managed-Project Finalizer

**Research question:** What is the best way to remove
`sase/memory/task_types.md` from always-loaded agent instructions and replace it with a
configurable finalizer that asks agents, only at normal turn completion, whether
discovered work should become task beads?

**Scope:** SASE at `0ccfd7a6ff3c`, `sase-core` at `dd198449b4e3`, the generated
task-type memory and catalog pipeline, managed-project initialization, and the current
host-owned finalizer protocol. Prior finalizer research was consumed through audited
artifact reads. This is architecture research, not an implementation; no SASE runtime
or memory behavior was changed.

## Bottom line

Implement a first-party **declaration-only `builtin@tasks` finalizer**. Activate it only
from a SASE-managed repository's project-local `sase/sase.yml`, and have `sase init`
reconcile that entry automatically:

```yaml
finalizers:
  required: [tasks]
  instances:
    tasks:
      use: builtin@tasks
      max_attempts: 1
      refusal: fail
```

The finalizer should not create task beads. At `/sase_final` time it should render late
guidance from the committed `sase/task_types.json` snapshot, ask the agent to disposition
any discovered follow-up, and require a small typed payload. The agent performs any
judgment-bearing action through `/sase_new_task` before submission; the host validates
and verifies the result. If that action changes bead state, `/sase_final` refreshes the
context before submitting so commit obligations include the bead-sidecar mutation.

Keep the late guidance behind a content-source interface. The first implementation can
use a packaged Markdown template plus the task-type snapshot. The upcoming memory-file
type can later become that source without changing finalizer selection, payloads, or
execution.

This is preferable to putting the text in the generic `/sase_final` skill, using
`builtin@command`, or forcing a second model turn: it is project-scoped, config-owned,
auditable, deterministic, and late-disclosed on the normal compliant path.

## 1. Current-state findings

### 1.1 The expensive part is presentation, not the catalog

`src/sase/main/init_memory/root_rendering_task_types.py` currently does two distinct
jobs:

1. it builds and snapshots the committed task-type catalog at
   `sase/task_types.json`; and
2. it renders the agent-creatable subset into the short memory note
   `sase/memory/task_types.md`.

Only the second job should move. The JSON snapshot is the correct deterministic source:
it includes built-ins, project-local types, and types from `plugins.required`, while
excluding whatever optional plugins happen to be installed on one machine. Removing the
snapshot would make a late finalizer less reproducible than today's instructions.

The checked-in memory inventories estimate the project task-type note at about 925
tokens and the home-root copy at about 820. Together they account for roughly 1,745 of
5,944 always-loaded SASE memory tokens (about 29%), although the exact effective stack
depends on the launch context.

### 1.2 The finalizer substrate already has almost every required primitive

The current controller already provides:

- project-aware config layers and explicit instance activation;
- pre-turn plan resolution and authentication;
- required instances that `%final:none` and `%final:!name` cannot remove;
- turn-bound context and atomic declaration manifests;
- one bounded declaration-recovery turn when an agent forgets `/sase_final`;
- provider-specific payload validation before execution;
- deterministic execution, verification, evidence, and failure artifacts; and
- recomputation of repository obligations before accepting a submission.

The proposal can reuse `trigger: always` with `submission_required: true`. It does not
need a new Rust trigger enum or a finalizer wire-version bump. Rust can continue to own
plan, requirement-coverage, digest, and submission validation, while Python owns the
task-specific Markdown presentation and bead-domain adapter.

### 1.3 There is one missing generic seam: late declaration guidance

`sase final context` currently exposes selected instances, trigger state, repository
obligations, and a manifest template. It does not expose provider-specific guidance.
External providers have a `describe` operation, but it is currently run in the later
executor pipeline, after the declaration that would need its instructions.

Do not special-case task prose in the `/sase_final` skill. Add a generic context-level
guidance collection instead, keyed by selected instance:

```json
{
  "guidance": [
    {
      "instance_id": "tasks",
      "format": "markdown",
      "content": "...late-rendered guidance...",
      "content_digest": "..."
    }
  ]
}
```

The raw guidance can remain presentation data outside the Rust context wire. Bind its
digest, the task-catalog digest, the agent's task mode, and the payload-schema digest
into the existing `requirement_digest`. A fresh context then changes whenever any input
to the guidance changes, and submission-time live-context comparison rejects stale
manifests. This adds a reusable late-prompt channel without making Rust interpret
Markdown.

### 1.4 Project-local finalizer lists currently have a layering trap

The ordinary config stack documents user-base lists as replacing and selected-overlay
and project-local lists as concatenating. `sase.finalizers.config`, however, replays
`defaults` and `required` by unconditional replacement and ignores each
`ConfigLayer.list_strategy`.

That makes naive initialization unsafe:

- local `defaults: [tasks]` silently drops inherited `commit`;
- local `defaults: [commit, tasks]` freezes today's inherited defaults in the repo;
- local `required: [tasks]` silently drops any machine- or user-required instances.

Fix this before auto-writing activation. Finalizer list replay should honor the existing
layer strategy: user-base values replace, overlays and local config append uniquely,
and plugin layers remain forbidden from activating defaults, requirements, or
instances. Then project-local `required: [tasks]` composes with higher-level policy
instead of cloning it.

## 2. Why this should be a declaration finalizer

The decision "did this turn reveal durable follow-up?" is model judgment informed by
the full conversation and work performed. The host cannot derive it from a diff. The
host *can* verify concrete consequences: a referenced bead exists, the current agent
created or corroborated it, or a phase worker added the required proposed-follow-up
note.

That matches the completion-contract split established by the earlier finalizer
research:

- trusted config decides that the review is required;
- late guidance asks the agent for the judgment;
- the agent takes the judgment-bearing action during the declaration step; and
- the provider validates and verifies evidence rather than inventing the action.

`builtin@command` cannot do this: it accepts no model payload and is meant for bounded,
deterministic argv checks. An external plugin could, but task beads and managed-project
semantics are first-party SASE domain behavior; requiring a plugin would add packaging,
availability, and trust complexity without creating a useful extension boundary.

The declaration should be required rather than merely advisory. Otherwise `%final:none`
could silently restore the exact "agent forgot to think about follow-up" failure the
migration is intended to eliminate. It remains configurable: removing `tasks` from the
project-local `required` list disables the policy for that project.

## 3. Recommended end-of-turn flow

```text
initial agent prompt
  (generic /sase_final rule; no task catalog or task-bead reminder)
        |
        v
ordinary work and verification
        |
        v
/sase_final -> sase final context
        |
        +-- host renders builtin@tasks guidance from sase/task_types.json
        +-- host identifies ordinary-agent vs epic-phase mode
        +-- host supplies a typed tasks payload template
        |
        v
agent reviews discovered work
        |
        +-- no candidate: provide a short reason
        +-- candidate: invoke /sase_new_task and record/corroborate a bead
        +-- phase worker: add PROPOSED FOLLOW-UP on its phase bead, never create a task
        |
        v
refresh final context if bead state changed
        |
        v
submit one atomic manifest (tasks disposition + any commit decisions)
        |
        v
host validates task evidence, then executes/verifies selected finalizers
```

This does not add a second LLM call when the agent follows the existing terminal-action
rule. Declaration recovery remains the one-shot fallback for noncompliance.

The refresh step is essential. The first context is what discloses the task guidance,
but `/sase_new_task` can mutate the bead sidecar. Reusing the first manifest would be
correctly rejected as stale and could omit a new commit obligation. The generated
`/sase_final` skill should explicitly treat guidance-driven mutations as a reason to
rerun `sase final context -f json` before building the final manifest.

## 4. Payload and verification contract

A boolean `reviewed: true` is too easy to satisfy without leaving useful evidence. A
small outcome list supports multiple discoveries and the phase-worker exception:

```json
{
  "reviewed": true,
  "outcomes": [
    {"kind": "created", "ref": "bead:sase-a1"},
    {"kind": "corroborated", "ref": "bead:sase-b2"}
  ],
  "no_task_reason": null
}
```

Allowed outcome kinds should initially be:

- `created`: a genuinely new task was filed through `/sase_new_task`;
- `corroborated`: an existing task received independent evidence rather than a
  duplicate being created; and
- `proposed_follow_up`: an epic phase worker recorded the exception on its own phase
  bead.

An empty `outcomes` list requires a nonblank `no_task_reason`; a nonempty list forbids
that field. Keep the reason short and do not require the agent to restate its entire
chain of thought.

Submission validation should reject unknown keys/kinds, malformed or duplicate refs,
and a disposition incompatible with the host-issued task mode. Verification should
resolve every ref and, where the bead event stream exposes the fact reliably, confirm a
matching current-agent event after the run began. Start with existence, type, and mode
checks if attribution is not yet a stable query; do not delay the memory reduction on a
large new provenance system.

The built-in executor should be non-mutating. All bead creation, corroboration, and
phase-note writes remain agent actions governed by `/sase_new_task` and the existing
bead rules. This also means provider ordering relative to `commit` is not semantically
important in version 1: task payload validation occurs before any executor, and a
post-submit task executor only verifies.

## 5. Guidance content and the upcoming memory-file type

Extract the type-entry renderer from its memory-specific module into a shared task-type
presentation module. The finalizer needs the same facts as today's note:

- the project catalog and `list`/`show` commands;
- each agent-creatable type's label, `when_to_use`, and required/optional field names;
- the instruction to invoke `/sase_new_task` before creating anything; and
- the epic-phase exception.

Do not embed that prose in Rust, in the provider registry, or permanently in the
generic `/sase_final` skill. Define a narrow content-source contract such as:

```python
class FinalizerGuidanceSource(Protocol):
    def render(self, instance_id: str, context: GuidanceContext) -> Guidance: ...
```

The first `tasks` source can render a packaged Markdown template against
`sase/task_types.json`. When the new memory type exists, its resolver can supply the
same `Guidance` object. The context/digest/payload protocol and project config remain
unchanged. This is the useful compatibility seam to establish now; guessing the future
memory frontmatter or type name is not.

## 6. `sase init` ownership and migration

The memory initializer is the best current owner of this reconciliation, even though
the runtime feature is a finalizer:

- it already owns the SASE-managed opt-in in project-local `sase/sase.yml`;
- it already plans, previews, applies, and commits generated instruction changes;
- this migration must add finalizer config while retiring a generated memory note in
  one coherent change; and
- the future finalizer-scoped memory source will naturally return to the same
  initializer.

Factor the YAML edit as a project-config reconciliation helper rather than adding more
one-off writes to `prepare_project_memory_opt_in`. `plan_init_memory` should surface the
action in `sase init --check` and `--diff`; `run_init_memory` should apply it only when
the *raw local* config says `is_sase_managed: true`. Bare `sase init` and `sase init
--all` will then pick it up through the existing memory spec.

Use the raw local authorization check, not the merged config, and add a defense-in-depth
diagnostic that refuses a selected `builtin@tasks` instance outside a SASE-managed
project. That preserves the strict meaning of "only active for SASE-managed projects"
even if a machine config or copied repository block names the provider accidentally.

Initialization must preserve comments, existing instance settings, and user policy. It
should add the missing `tasks` requirement/instance idempotently, but should not
overwrite a deliberately configured `tasks` instance whose `use` or policy differs;
surface that as already user-managed or as a targeted conflict.

## 7. Retiring `task_types.md` safely

Stop generating `task_types.md` at both project and home memory roots, remove it from
`generated_memory_note_relative_paths`, and remove the renderer from
`render_expected_memory_files`. Keep `sase/task_types.json` generation and validation.
Update `memory-sase-beads.template.md` so its long note points to
`sase bead task-type list/show` and the terminal tasks contract rather than promising a
generated short note.

The old note lacks an explicit generated-file marker, so do not blindly unlink any file
at that path. Use a one-release retirement rule:

1. delete it automatically when its frontmatter and body exactly match a known packaged
   generated render;
2. if the path exists with different content, block with an actionable message rather
   than deleting possible user edits; and
3. exclude a retired exact match from AMD/instruction discovery in the same planning
   pass, so generated `AGENTS.md`, provider shims, and the memory README converge
   immediately.

Retain the legacy template or known render digest only as long as needed for safe
migration, then remove that compatibility code. Tests should cover both the home and
project copies because deleting only the project note would leave much of the prompt
cost in place.

## 8. Options considered

| Option | Advantages | Problems | Verdict |
| --- | --- | --- | --- |
| Put the text in `/sase_final` | Late skill disclosure; small change | Applies outside managed projects, bypasses finalizer config/selection, couples one domain policy to a generic terminal skill | Reject |
| `builtin@command` | Already implemented and bounded | Cannot ask for model judgment or accept a declaration payload | Reject |
| External `sase_finalizers` provider | Uses current extension protocol | Makes core SASE bead policy depend on plugin packaging and availability | Reject |
| Always force a recovery model turn | Very late and easy to inject custom prose | Adds latency/cost to every normal turn and appends a second response even when the agent was compliant | Reject |
| Finalizer reads the live optional-plugin registry | Shows everything installed now | Machine-dependent and can disagree with committed project instructions | Reject |
| Built-in declaration finalizer using `sase/task_types.json` | Project-scoped, deterministic, typed, auditable, no extra compliant-path model call | Requires a generic guidance field and init/memory migration | **Recommend** |
| Wait for the future memory type | Avoids a temporary packaged template | Leaves the current prompt cost and behavior in place; activation/payload design is needed either way | Defer only the content backend |

## 9. Acceptance tests that matter

Configuration and initialization:

- managed project: `sase init --check` reports missing tasks finalizer config;
- apply is comment-preserving and idempotent;
- unmanaged project and home/non-project contexts remain untouched;
- local required-list activation preserves user/machine required instances;
- `sase init --all` reconciles every enabled managed project; and
- `%final:none` cannot remove `tasks` while the local required entry exists.

Late prompting and declarations:

- the generated `AGENTS.md` and provider shims contain no task-type section or task-bead
  reminder from `task_types.md`;
- `sase final context` includes task guidance only when `tasks` is selected;
- guidance is rendered from the committed snapshot and its digest participates in the
  requirement/context digest;
- ordinary and epic-phase agents receive the correct mode;
- empty outcomes require a reason, and evidence refs are validated;
- bead mutations after the first context force a refresh and produce correct commit
  obligations; and
- omission gets exactly one existing declaration-recovery turn, not a new task-specific
  recovery loop.

Memory migration:

- exact generated home and project notes are retired;
- a modified note blocks rather than being deleted;
- `sase/task_types.json` remains generated and checked;
- the memory README no longer inventories `task_types.md`; and
- no generated provider instruction file retains the removed section.

Provider/controller coverage:

- `builtin@tasks` appears in finalizer inventory and diagnostics;
- selecting it outside a locally managed project fails before the model turn;
- its executor never mutates bead or repository state; and
- task verification evidence appears in `finalizer_result.json`.

## Sources and provenance

The main repository evidence came from
`src/sase/main/init_memory/root_rendering_task_types.py`,
`src/sase/main/init_memory/root_planning.py`, `src/sase/project_management.py`,
`src/sase/config/{core,layers}.py`, and `src/sase/finalizers/`. The shared protocol
boundary was checked in `sase-core/crates/sase_core/src/finalizer/{wire,selection,submission}.rs`.

Two prior reports were consumed through audited artifact reads:

- `research:202608/finalizer_protocol_and_extensibility/finalizer_protocol_and_extensibility.md`
  for the plan/context/declaration/execute/verify split and demand-driven recovery; and
- `research:202608/finalizer_completion_contracts/finalizer_completion_contracts.md`
  for the rule that agent judgment should happen during the turn while a finalizer
  validates and verifies host-observable consequences.

No new external comparison was needed for this decision. The earlier reports already
established the general completion-contract model; the open questions here were
specific to SASE's current config layering, task-type snapshot, managed-project init,
and declaration implementation.

## Recommended solution

Add `builtin@tasks` as a required, declaration-only finalizer activated by
SASE-managed project-local config that `sase init memory` reconciles automatically.
Teach `sase final context` to expose digest-bound, per-instance late guidance; render
the tasks guidance from the committed `sase/task_types.json` catalog; and require a
typed disposition whose concrete bead or phase-note outcomes the host can verify. Have
the agent perform any task action through `/sase_new_task`, refresh context after that
mutation, and submit tasks plus commit intent atomically.

At the same time, make finalizer list replay honor project-local concatenate semantics,
retire exact generated `task_types.md` notes from both home and project instruction
roots, and keep the JSON catalog. Put the Markdown behind a small guidance-source
interface so the upcoming memory-file type can replace the packaged template later
without redesigning config, declarations, or provider execution.
