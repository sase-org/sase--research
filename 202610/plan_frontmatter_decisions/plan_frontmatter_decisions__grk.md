---
create_time: 2026-10-07
updated_time: 2026-10-07
status: draft
tags:
  [
    research_swarm,
    plan-frontmatter,
    notification-gates,
    plan-approval,
    memory-write,
    sase-core,
    hitl,
  ]
---

# Plan-embedded gates: a decision dialect, not a custom-gate dump

**Question.** How should SASE tales and epics embed gate options in plan
frontmatter, so a human can (1) approve optional memory-file edits at plan
review with a default that is on only when they asked for those edits, and
(2) answer plan-affecting questions at approval time so the coder implements
from the selections? Is that a good idea? What should change about the
request?

**Researcher.** grk (`research.0f.grk`). Independent report. I did not read
peer reports from this swarm.

**Scope.** Current tale/epic frontmatter (sase-core closed schema), the
trusted PlanApproval / EpicApproval gate contract, UserQuestion vs custom
gates, memory-write authorization, `%auto`, gate-turn follow-up prompts, and
the `links:` authoring-inlet precedent. External analogs: GitHub issue forms
and GitHub Actions `workflow_dispatch` inputs. Recommendation for a design
SASE can implement without turning plan YAML into a privilege-escalation
language.

## Bottom line

This is a **good idea** with the wrong literal reading.

Embedding *sase gate options* in frontmatter, if that means pasting a
schema-version-3 custom-gate request (query, options, commands, resources,
turn block) into YAML, is a bad idea. Plan gates today are a **closed,
adapter-owned command contract**. Custom gates can run arbitrary argv. The
option-query language is deliberately flat. Tale AND-groups can be submitted
as any non-empty subset. The tale coder does not read generic `## Results`;
it reads `@plan` plus a host-rebuilt prompt. Those four facts make a
naive dump both ugly and unsafe.

The good idea underneath is: **fold structured, defaulted, auto-capable
plan forks into the existing plan-approval HITL**, and make the archived
plan the source of truth for what the human chose.

Recommended solution: a small **plan-decision dialect** in frontmatter
(`gates:` plus first-class `memory:` sugar) that the host **compiles onto
the existing PlanApproval / EpicApproval gate as typed inputs**, never as
new query branches or agent-authored commands. The host stamps `selected:`
onto the archived plan, injects a compact decision table into the coder /
phase-worker prompt, and applies defaults on `%auto` and on Enter-to-approve.
Do not open a second gate. Do not ask `/sase_questions` before propose for
forks the planner can already write both sides of.

## Verdict on the request

| Claim | Verdict |
| --- | --- |
| Put human forks on the plan-approval gate instead of a pre-plan question round | **Keep.** One HITL, with the plan in view. |
| Memory edits in a plan should be an explicit human gate, default on iff the user asked | **Keep the policy; drop the magic.** Planner-authored boolean + required `because:` quote. Host does not NLP the prompt. |
| The coder implements from gate selections | **Keep**, but stamp the archived plan. Prompt injection is a second channel, not the only one. |
| "Embed sase gate options in frontmatter" as full custom-gate JSON | **Reject.** Compile a constrained dialect. No `command:`, no `query:`, no `resources:`. |
| Use this for every clarifying question | **Reject.** Questions that *block writing a good plan* still go through `/sase_questions`. |

## 1. What exists today

### 1.1 Plan frontmatter is a closed Rust schema

Authoritative field lists live in
`sase-core` `crates/sase_core/src/plan/validate.rs`. Unknown keys are
errors (`unknown-key`). The accepted sets are:

- Common: `tier`, `title`, `goal`, `model`
- Tale-only: `size`
- Epic-only: `phases`, `patch`, `changespec`, `bug_id`, `parent_bead`
- Transient authoring inlet: `links`
- System-managed: `create_time`, `status`, `prompt`, `bead`, `proposed_by`,
  `parent`, `bead_id`

There is no `gates`, `options`, `decisions`, or `memory` field. Adding one
is a sase-core schema change, then a Python adapter pin
(`PLAN_WIRE_SCHEMA_VERSION` is currently `3` and is exact-match). Per
`docs/rust_backend.md` and the rust-core boundary, **validation of the new
dialect belongs in sase-core**, not a Python-only parser that `sase plan
validate` could drift from.

`links:` is the closest precedent: a nested YAML list, validated at
`sase plan propose`, consumed, and **stripped** from the archived plan
(`src/sase/sdd/artifact_link_inlet.py`, docs in
`docs/artifact_links.md`). Plan-embedded decisions should **not** be
stripped. They are the handoff. They should persist, with the human's
answers stamped in.

### 1.2 Plan approval is already a typed gate, and it is sealed

Tale query (`src/sase/_plan_gate_metadata.py`):

```text
(approve AND commit) OR reject OR feedback
```

Epic query:

```text
approve OR reject OR feedback
```

`src/sase/notification_gates/kind_validation/plan.py` pins **query,
branches, option command paths, tale submit group, the single edit
operation, and the exact command-script bytes**. An extra agent-authored
option id fails `invalid_plan_query` / `invalid_plan_options`. That seal
is load-bearing: plan option commands archive the plan, launch the coder,
and commit to the plans sidecar. They are host-owned side effects, not
planner toys.

The option-query grammar (`src/sase/notification_gates/query.py`) is
deliberately flat:

```text
query  := branch ( OR branch )*
branch := option ( AND option )*
```

Parentheses cannot nest. An option id appears **exactly once**. Exclusive
choices therefore **cannot** be expressed as

```text
(approve AND commit AND redis) OR (approve AND commit AND filesystem) OR reject
```

`approve` would repeat. The language cannot say "approve, and also pick
exactly one of {A, B}". That is what **typed inputs on the approve
option** already exist to do (`GateInputField`: `bool`, `enum`, …).

AND-group semantics are the other trap. Answering selects a non-empty
subset of exactly one branch. Tale already uses that on purpose: commit
without approve is a real path ("commit the plan file, do not run the
coder"). If `memory` joined that AND group, a reviewer could submit
**only** `memory` — a selection with no defined host side effect. Extra
query members also change epic UX: epic approve is a singleton button
today; AND-extending it turns Epic into a checkbox group.

### 1.3 The coder does not inherit the planner, and barely inherits the gate

`src/sase/axe/run_agent_exec_plan_accept.py`:

> The coder starts with a fresh context window; the approved plan file is
> the hand-off artifact. It does not inherit the planner's chat.

The successor prompt is essentially `@<plan-ref>` plus "Implement it now"
plus optional reviewer `coder_prompt`. Plan gate-turns set
`raw_prompt: True` (`src/sase/plan_gate_turn/create.py`), so the generic
gate-turn `## Results` JSON **is not** in that prompt.
`plan_next_action` rebuilds the prompt from durable artifacts
(`src/sase/plan_gate_turn/followup.py`).

Reliability rule: **if the archived plan does not contain the
selections, the coder does not have them.** Prompt injection is a
courtesy. The plan file is the contract.

Epic phase workers are even further away: `sase bead work` renders
per-phase prompts from the epic plan and phase beads
(`src/sase/bead/work_prompt.py`). Top-level decisions must be stamped on
the epic plan **and** copied into every phase / land prompt, or a phase
agent that only reads its bead description will miss them.

### 1.4 Questions and custom gates already exist, and they are the wrong shape here

`/sase_questions` creates a **question gate turn** that kills the planner
and resumes it with Q&A (`sase/macros/skills/sase_questions.md`,
`src/sase/notification_gates/kind_validation/question.py`). One singleton
`submit` option; the questions are an input form. Correct when the
planner **cannot write a good plan** without the answer (which bug? which
repo? is this in scope at all?).

Wrong when the planner can write both forks and the human should see the
plan while choosing. Today the memory-write skill does exactly that
wrong thing:

> Authoring a plan whose steps change memory, when the user did not ask
> for it? Confirm with `/sase_questions` **before** `sase plan propose`.

(`src/sase/macros/skills/sase_memory_write.md`)

The human answers without seeing the edits. Then they approve the plan in
a second HITL. Two gate turns, two follow-ups, and the authorization
still collapses to "the approved plan names the change in its steps" —
so a default-on memory section the human never noticed is already
"approved."

Custom gates (`sase gate create`) are the third existing shape. They
allow arbitrary queries and **command resources**. Putting that power in
plan YAML would let a planner propose `rm -rf` next to `tier: tale`.
Plan kind validation exists so that cannot happen on PlanApproval.

### 1.5 `%auto` applies primary-branch `default_selected`, not input defaults

`GateAdapter.resolve_auto_selection` picks primary-branch members whose
`default_selected` is true (`src/sase/notification_gates/adapters.py`).
`automatic_input` for tales is `{}`; for epics it is
`{"epic_launch_mode": "launch"}`. jsonschema does not fill property
defaults. So if plan decisions compile to extra input fields, **`%auto`
and Enter-to-approve both miss them unless the host fills defaults at
execution time.** That is a required implementation hook, not a polish
item.

Decision-receipt hashing already binds typed input identities
(`docs/notifications.md`, fast decision acceptance). Compiled inputs
participate in that receipt automatically if they go through
`option_inputs`. Good.

### 1.6 Memory authorization is skill-only

Nothing in `sase plan validate` or the finalizer currently checks that a
plan which touches `sase/memory/` carried a human-selected memory gate.
Authorization is three bullets in a skill. That is why "plan approval is
user approval" is both the feature and the bug: it is too coarse. A
structured memory toggle is how we make it finer without a second HITL.

## 2. Is this a good idea?

Yes, as a **structured fork at the approval HITL**. No, as **nested
custom gates**.

### 2.1 Why the underlying need is real

Three failure modes exist today:

1. **Guess.** The planner picks Redis, writes only that path, and the
   human who would have wanted the filesystem never sees the fork.
2. **Block.** The planner calls `/sase_questions`, the human answers in
   the dark, then reviews a plan that already baked the answer in.
3. **Prose optional sections.** The plan says "optionally also update
   memory." The coder, told "implement it now," implements the optional
   part. Or skips it. Either way is unenforced.

A plan-local decision that the human sees **on the same modal as the
plan**, with a default, with `%auto` honoring that default, and with the
archived plan recording the answer, kills all three.

This also matches `decisions:gates-never-block` and
`decisions:single-turn-agents`. The planner already dies at
`sase plan propose`. Continuation is the plan gate-turn. Folding extra
questions into that same turn adds **zero** extra family rows. A
pre-plan question gate, or a post-approval custom gate, each adds one.

### 2.2 Why a literal custom-gate dump is a bad idea

- **Trust.** Plan option commands are hashed adapter scripts. Agent-authored
  `command:` / `resources:` in a plan would either be refused (so why
  author them?) or accepted (so the plan file is a sudo vector).
- **Query physics.** Exclusive choices cannot nest under approve.
  Independent toggles as AND members can be submitted without approve.
- **Beauty.** A schema-version-3 gate request is ~80 lines of JSON. Plan
  frontmatter is currently a dozen keys a human can read in a glance.
  `phases:` is the complexity budget we should match, not exceed.
- **Sealed kind.** Opening `validate_plan_spec` to arbitrary options
  throws away the trusted-adapter property for a convenience.
- **Surfaces.** TUI, Telegram, mobile, and `sase gate answer` already
  know how to submit `option_inputs` for declared fields. They do not
  know how to grow a plan query per plan file without breaking labeled
  **Tale** / **Epic** submit groups.

### 2.3 Strongest alternative I considered and rejected

**Just edit the plan during review.** The gate already declares an
`edit_plan` operation (`edit_target: "origin"`, re-validated on save).
A human who hates Redis can change the markdown and approve.

That is the right tool for **wording and mistakes**. It is the wrong
tool for **forks the coder must mechanically honor**:

- The unselected path tends to remain in the file as prose, and the
  coder still sees it.
- There is no default-on-iff-requested, no `%auto` story, no compact
  decision table, no way for a skill to require a toggle.
- Editing under a notification modal is a worse questionnaire than
  toggles and radios.

Keep the edit operation. Do not pretend it is a forms product.

## 3. Adjustments to the requirements

These are intentional. Each one is a change to the request as written.

### A1. Do not embed full gate options

**Adjustment.** Frontmatter authors a **decision dialect** (`toggle` and
`choice` only). The host compiles it. Plans must not contain `query`,
`command`, `resources`, `turn`, `primary_branch`, or `groups`.

**Why.** Closed trusted contract, no privilege escalation, query
language cannot express exclusive choices under approve.

### A2. Do not mix decisions into `(approve AND commit)`

**Adjustment.** Compiled decisions become **typed inputs on the approve
option** (and, for tales, on commit as well — the same mirroring already
used for `coder_prompt`). They are ignored on reject. Feedback leaves
them in the plan for the replanner; it does not treat them as answers.

**Why.** AND-subset submission, epic singleton UX, reserved option ids
(`approve`, `commit`, `reject`, `feedback`). Inputs already have a
cross-surface submission path (`option_inputs`, schema_version 5+ on
mobile).

### A3. Replace pre-plan memory questions; do not add a second gate

**Adjustment.** Rewrite `/sase_memory_write`: when authoring a plan that
changes memory, **do not** call `/sase_questions` first. Put the edits
in the plan body and declare `memory:` (or a `gates` toggle with
`id: memory`). Propose. The human sees the edits and the toggle on the
same modal.

Keep `/sase_questions` for questions that block planning.

**Why.** This is the actual UX win. Two HITLs was the bug.

### A4. `default: on iff the user requested` is a planner rule, not host NLP

**Adjustment.** Every decision has an explicit boolean (toggle) or
option-id (choice) `default`. `default: true` on a toggle **requires**
`because:` — a one-line quote of the user request. Missing `because`
fails `sase plan validate`. There is no `requested` token the host
evaluates by scanning the prompt.

**Why.** Agents already rationalize "the user would have wanted this."
A required quote is reviewable. Host-side phrase matching will both
false-negative ("please keep the notes in sync") and false-positive
(quoted docs). The human still sees the default and can flip it.

### A5. Stamp answers into the archived plan; freeze the set at propose

**Adjustment.** Authoring `selected:` is an error
(`gates-selected-authored`). After approve / commit / epic, the host
writes `selected:` on each item. Editing `gates:` / `memory:` during
review **does not** rebuild the live gate; approve-time validation
requires the frozen ids to still be present. Additions or id changes in
the editor fail closed. Label/notes tweaks may pass.

**Why.** The editable `plan.md` resource is a copy. The gate spec is
built at propose. If the human could add a new fork in the editor, the
modal would lie. If we did not stamp `selected:`, the coder's only copy
of the answer would be a rebuilt prompt that `raw_prompt: True` already
strips generic results from.

### A6. Top-level only for v1; no per-phase `gates`

**Adjustment.** Defer `phases[].gates`. Epic decisions are answered once
at Epic approval and apply to every phase and the lander.

**Why.** Per-phase gates either explode the approval modal or reintroduce
HITL at every phase start. The two stated use cases are whole-plan
forks.

### A7. Body describes both sides; frontmatter is the switch

**Adjustment.** The plan body still writes both forks (or a `## Memory`
section the coder skips). `when_on` / `when_off` / per-choice `when:`
are short coder instructions, not a second copy of the design. Do not
conditionally rewrite the body at approval.

**Why.** Git history of the plan should show what was offered. The
coder is told which branch to take. Host-rewriting the body races the
edit operation and makes diffs noisy.

### A8. Beta flag, then unconditional

**Adjustment.** This is user-reaching plan-approval UI. Land behind a
`beta` flag (`sase flag new`) until the TUI decision sheet and `%auto`
defaults have soaked. Removing the flag deletes the off branch.

**Why.** `sase/memory/sase_flags.md`: flags for user-reaching behavior
that is not yet ready to be unconditional. This is not a forever config
knob.

### A9. Cap the list

**Adjustment.** At most **six** decisions per plan (the `memory:` sugar
counts). More is a smell that the planner should have asked blocking
questions or split an epic.

**Why.** Beauty. A review modal with twelve radios is a form, not a
plan.

### A10. Mechanical memory enforcement is follow-up, not v1

**Adjustment.** v1 is dialect + compile + stamp + prompt + skill. A
later phase may fail a coder finalizer whose dirty paths include
`sase/memory/` when the plan's memory toggle is missing or
`selected: false` (and require filing a memory task bead instead).

**Why.** Finalizer coupling is real work and easy to get wrong around
`sase memory init` generated files. Ship the HITL first.

## 4. Recommended dialect

### 4.1 Shape

Two keys, both optional, both valid on tale and epic:

```yaml
---
tier: tale
title: Add plan-embedded decisions
goal: Humans decide plan forks at approval time
size: medium
memory:
  default: false
  files:
    - path: sase/memory/sase_sizes.md
      change: Mention plan-local gates in the authoring notes.
    - path: sase/memory/cli_rules.md
      change: Document `sase plan validate` diagnostics for `gates:`.
gates:
  - id: cache
    kind: choice
    label: Cache backend
    icon: "🗄️"
    default: redis
    options:
      - id: redis
        label: Redis
        description: Shared cache; needs redis-server.
        when: "Implement the Redis path in §Cache."
      - id: filesystem
        label: Filesystem
        description: Local only; no extra service.
        when: "Implement the filesystem path in §Cache."
  - id: telemetry
    kind: toggle
    label: Emit debug telemetry
    default: false
    when_on: "Include the telemetry hooks in §Observability."
    when_off: "Do not add telemetry files or config."
---
```

When the user *did* ask for memory edits:

```yaml
memory:
  default: true
  because: "User: 'update the memory notes for plan gates'"
  files:
    - path: sase/memory/sase_sizes.md
      change: Mention plan-local gates in the authoring notes.
```

After approval the host stamps:

```yaml
memory:
  default: true
  because: "User: 'update the memory notes for plan gates'"
  selected: true
  files:
    - path: sase/memory/sase_sizes.md
      change: Mention plan-local gates in the authoring notes.
gates:
  - id: cache
    kind: choice
    default: redis
    selected: filesystem
    # ...
```

### 4.2 Field contract

**`memory:`** (sugar, reserved toggle id `memory`)

| Field | Rule |
| --- | --- |
| `default` | bool, required |
| `because` | non-empty string; **required if `default: true`** |
| `files` | non-empty list of `{path, change}` |
| `path` | repo-relative; must start with `sase/memory/` or the home-memory equivalent the validator already knows |
| `change` | one-line intended edit |
| `selected` | bool; authoring-forbidden, host-stamped |
| `icon` | optional; default `🧠` |
| `label` | optional; default `Apply memory edits` |

Compiles to a toggle. Error if `gates` also contains `id: memory`.

**`gates[]`**

| Field | Rule |
| --- | --- |
| `id` | `^[a-z][a-z0-9_]*$`; unique; not in `{approve, commit, reject, feedback, memory}` unless it is the sugar |
| `kind` | `toggle` \| `choice` |
| `label` | non-empty, ≤80 chars, single line |
| `icon` | optional, one grapheme |
| `notes` | optional string list; review-modal copy |
| `default` | toggle: bool. choice: an `options[].id`. Required. |
| `because` | required when toggle `default: true` |
| `when_on` / `when_off` | toggle only; optional short coder instructions |
| `options` | choice only; 2–6 items, unique ids, unique labels |
| `options[].when` | optional short coder instruction for that pick |
| `selected` | authoring-forbidden |

No `command`, `query`, `type: text` free-response, no nested AND/OR.
If the planner needs a paragraph from the human, that is
`/sase_questions` or the existing feedback branch.

### 4.3 Compilation onto the live plan gate

At `sase plan propose`, after today's validation:

1. Parse `memory:` + `gates:` in sase-core. Fail the proposal on
   diagnostics, same as a bad `size:`.
2. Freeze the compiled list into the gate bundle payload
   (`payload.plan_decisions`) so review-time plan.md edits cannot
   silently grow it.
3. Extend approve (and tale commit) `input_schema` /
   `result_schema` with one property per decision:
   - toggle → `{type: boolean, default: <bool>}`
   - choice → `{enum: [...], default: <id>}`
4. Do **not** change `query`, `groups`, option ids, or command scripts.
   Kind validation stays sealed.
5. `execute_plan_gate_command` echoes the resolved decisions into the
   option result as `decisions: {id: value, ...}`.
6. `automatic_input` for `plan` / `epic_plan` fills those defaults so
   `%auto` and a client that submits `{}` still settle.
7. Archive writer stamps `selected:` via
   `set_frontmatter_fields` (same path as `status:` / `create_time`).
8. `prepare_accepted_plan_successor` appends a short **Plan decisions**
   block to the tale coder prompt. `sase bead work` prefixes the same
   block on every epic phase and land segment.
9. `when_*` text is planner-authored: wrap it in the disabled-macro
   region the gate-turn follow-up already uses. The host instruction
   is a single trusted sentence: *Honor the selected plan decisions.
   Do not implement unselected optional work. If memory is unselected,
   file a memory task bead instead of editing `sase/memory/`.*

Tale result_schema currently sets `additionalProperties: False`. That
must grow a `decisions` object. Kind validation today does **not** pin
input/result schemas (it pins query, commands, groups, scripts), so this
is an additive command-result change, not a kind-validator rewrite.

### 4.4 Review UX (the beauty layer)

Compiling to inputs is enough for CLI (`sase gate answer --option-input`),
mobile `option_inputs`, and ACE's existing input panel (`i`). It is
**not** beautiful enough for the headline use case. A memory toggle
hiding behind `i` will be missed, then `%auto` or Enter will apply the
default, and we are back to coarse "plan approval is user approval."

v1 of the TUI should show a **decision sheet** on the plan review
modal: the same visual language as gate options (icon, label, default
chip, notes), always visible next to the plan, not a second screen.
Toggles are checkboxes. Choices are radios. Enter still submits the
primary branch, now with whatever the sheet holds.

This is why the data model is inputs even if the chrome is a sheet:
Telegram and `sase gate answer` keep working without a custom query.

`sase plan show` should render a compact table of gates and, once
stamped, the selected values as chips. The PLAN lane in sase's TUI
follows.

### 4.5 Worked examples

**Memory, user did not ask** (the skill's current pre-plan question):

```yaml
memory:
  default: false
  files:
    - path: sase/memory/sase_sizes.md
      change: Note that tale `gates:` does not change size routing.
```

Human sees the proposed edits in `## Memory`, toggle off. They can
turn it on. `%auto` skips memory. Coder files a memory task bead if
the toggle stays off.

**Memory, user asked:**

```yaml
memory:
  default: true
  because: "User: 'require memory file changes to be planned with an explicit gate'"
  files:
    - path: sase/memory/sase_memory_write.md
      change: Replace pre-plan questions with the memory: frontmatter gate.
```

`%auto` applies the edits. That is correct: the user asked.

**Fork that does not block planning:**

```yaml
gates:
  - id: store
    kind: choice
    label: Goal store layout
    default: events_plus_markers
    options:
      - id: events_plus_markers
        label: Events + markers
        when: "Keep the current events-plus-markers layout."
      - id: single_log
        label: Single log
        when: "Collapse to a single log; update the lander checklist."
```

Planner writes both layouts in the body. Coder implements one.

## 5. Implementation map

This is epic-shaped. Tale-sized only if you ship compile-to-hidden-inputs
without the decision sheet, which I recommend against.

| Phase | Size | Where | What |
| --- | --- | --- | --- |
| `schema` | medium | sase-core `plan/validate.rs` | Accept `gates` / `memory`; diagnostics; authoring vs launch (`selected` forbidden vs required-after-archive); schema table + example for `--explain` |
| `compile` | medium | sase `plan_gate.py`, `_plan_gate_command.py`, adapters `automatic_input` | Freeze payload; extend input/result schemas; echo `decisions`; fill defaults |
| `stamp-and-prompt` | medium | archive writer, `run_agent_exec_plan_accept.py`, `bead/work_prompt.py`, `plan_gate_turn/followup.py` | Stamp `selected:`; inject decision table for tale coder, epic phases, lander |
| `review-ui` | medium | ACE plan approval modal | Always-visible decision sheet; keep `option_inputs` as the wire |
| `memory-skill` | small | `sase_memory_write` skill, plan authoring docs, `sase plan` explain text | Drop pre-plan questions; require `memory:` when the body edits memory |
| `surfaces` | small | CLI / Telegram / mobile | Confirm bool/enum inputs render; no new query branches |
| `flag` | xsmall | `sase flag new` | Beta around compilation + UI; off = today's sealed plan gate |

sase CI will stay red on the Python callers until
`sase-core-revision.txt` ratchets past the schema commit
(`docs/rust_backend.md`).

Do not bump `PLAN_WIRE_SCHEMA_VERSION` just to add optional nested
fields if `ValidatedPlanWire` can omit them the way it omits `links`.
Bump only if the Python adapter's exact-version check would otherwise
reject old cores — in which case it is a `feat!` in sase-core.

## 6. Risks

| Risk | Mitigation |
| --- | --- |
| Planner sets `default: true` with a fake `because:` | The quote is on the modal. Humans catch it. `%auto` remains the sharp edge; conservative skill text ("true only when the user's prompt for this turn asked") is the same honesty bar memory-write already has. |
| Human never notices hidden inputs | Decision sheet is in the same epic, not a later wish. Flag stays off until the sheet ships. |
| Review-time plan edit desyncs `gates:` | Freeze ids in payload; approve-time equality check. |
| Coder implements the unselected body section | Host sentence + stamped `selected:` + `when_off`. Mechanical path checks are phase two. |
| Exclusive choices stuffed into extra OR branches | Dialect forbids it; compiler only emits inputs. |
| Epic phase worker never opens the parent plan | Prompt prefix on every `sase bead work` segment. |
| `additionalProperties: False` drops `decisions` | Extend result_schema in the same change as the command echo. |
| Six-decision cap too small | Raise later. Start tight. |
| Name `gates:` overpromises | Docs: "plan-local decisions compiled into the approval gate." The user-facing word in the request is `gates`; keep it so agents grep the right key. |

## 7. What I would not do

- A parallel `sase plan ask` command.
- Per-phase gates in v1.
- Free-text inputs on the approval modal (feedback already exists).
- Host NLP for `requested`.
- Stripping `gates:` at archive the way `links:` is stripped.
- Letting plans declare `auto: true` on their own decisions.
- Using this dialect to re-ask "approve this plan?" — that is `reject` /
  `feedback`.
- Growing `%auto` into a per-decision override language. Defaults plus
  the existing plan auto aliases are enough. If a later `%auto` redesign
  (see the HITL-policy research) wants `auto.plan.decisions`, it can
  consume this payload; this feature must not invent that DSL.

## 8. Recommended solution

Ship **plan-local decisions** as closed YAML in tale/epic frontmatter:

1. `gates:` list of `toggle` and `choice` items, plus `memory:` sugar
   that compiles to a reserved toggle with required `files:`.
2. Host compiles them to **typed inputs on the existing approve/commit
   options**. Query, groups, and command scripts stay sealed.
3. Host fills defaults for `%auto` and empty client input. Enter
   approves with those defaults.
4. Host stamps `selected:` on the archived plan and injects a decision
   table into every worker prompt that implements that plan.
5. TUI shows an always-visible decision sheet on the plan modal.
6. Memory-write skill stops asking questions before propose; it authors
   `memory:` instead. Default on only with a `because:` quote of the
   user.
7. Beta flag until the sheet and default-filling have soaked.

That is intuitive (YAML that looks like `phases:`), reliable (frozen,
stamped, default-filled, sealed commands), and beautiful (one HITL, one
sheet, one archived source of truth). It is also smaller than "plans can
contain gates," which is the version of this idea that would make SASE
worse.

## Sources

Internal (this workspace and opened repos):

- `sase-core` `crates/sase_core/src/plan/validate.rs` — closed frontmatter schema
- `src/sase/sdd/plan_validate.py` — Python adapter, `PLAN_WIRE_SCHEMA_VERSION = 3`
- `src/sase/_plan_gate_metadata.py` — tale/epic queries
- `src/sase/plan_gate.py` — gate spec builder, sealed input/result schemas
- `src/sase/_plan_gate_command.py` — adapter-owned command scripts
- `src/sase/notification_gates/kind_validation/plan.py` — trusted plan contract
- `src/sase/notification_gates/query.py` — flat AND/OR grammar
- `src/sase/notification_gates/model_inputs.py` — `GateInputField` vocabulary
- `src/sase/notification_gates/kind_validation/question.py` — UserQuestion shape
- `src/sase/notification_gates/adapters.py` — `%auto` selection and `automatic_input`
- `src/sase/notification_gates/service.py` — auto-resolution execution
- `src/sase/plan_gate_turn/create.py` — `raw_prompt: True` coder branch
- `src/sase/plan_gate_turn/followup.py` — rebuilt tale prompt
- `src/sase/axe/run_agent_exec_plan_accept.py` — `@plan` handoff
- `src/sase/bead/work_prompt.py` — epic phase prompts
- `src/sase/sdd/artifact_link_inlet.py` — `links:` transient inlet
- `src/sase/macros/skills/sase_memory_write.md` — pre-plan question rule
- `src/sase/macros/skills/sase_plan.md` — authoring / propose handoff
- `docs/sdd.md`, `docs/notifications.md`, `docs/artifact_links.md`
- Glossary: Sase Gate, Gate Turn, Sase Turn
- Decisions: `gates-never-block`, `single-turn-agents`, `host-owned-completion`,
  `rust-core-required`

External analog (forms-in-YAML, not workflow engines):

- [GitHub issue forms syntax](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms)
  — `dropdown` / `checkboxes` / `input` with stable `id`s; not a general
  Actions workflow. That is the complexity ceiling this dialect should
  copy.
