---
create_time: 2026-08-07
updated_time: 2026-08-07
status: research
---

# Custom Inputs for SASE Gate Commands: The Gap Is Collection, Not Transport

**Question.** When a user reviews a SASE gate and picks a command to run, how can they
supply their own inputs/arguments to that command? What exists today, where does it
break, and what should be built next?

**Sources.** Consolidates two independent research passes (`__a`, `__b` in this
directory) plus a third verification pass. Everything below was re-verified against
`sase@8be11ae29`, `sase-core@` linked checkout, and `sase-telegram@33ada2ab`.

## Executive Summary

**The mechanism exists in the data model and is almost entirely unreachable from the
UI.** Every gate option already carries an `input_schema`; the shared executor already
pipes one JSON `input` value to each selected command's stdin and validates it against
that schema before any command starts. The transport is sound — typed, shell-free,
hash-verified, auditable. What is missing is the product contract between that executor
and the people answering gates: **no generic surface can collect a value to put in it.**

The one gate kind users and agents can author on the fly — `kind: "custom"` — is the
worst case. ACE hardcodes `input_data={}` for it, so a custom gate that declares any
required input field is accepted at creation and then **permanently unanswerable** from
the TUI, with no error recorded anywhere. The free-text note a reviewer types into a
custom gate's feedback box reaches `response.json` (so the *producing agent* sees it)
but never reaches that gate's *own command*.

Meanwhile the three client surfaces that can deliver a string each use a **different,
incompatible heuristic** for deciding whether to do so, so the same gate answers
differently depending on where you tap it. And every gate kind that genuinely needs
arguments (plan, question, HITL, launch, snooze, triage) paid for it with a bespoke
hardcoded modal or by smuggling structured data through the free-text field and
re-parsing it host-side.

**The recommended path** is a small **closed, declarative `inputs:` vocabulary declared
per option and submitted per option**, rendered generically by the shared branch
controls, with `input_schema` retained as the enforcement layer. The single most
important addition this pass makes: *SASE already has that vocabulary.* The xprompt
`input:` args (`InputArg` / `InputType`) already have a polished ACE renderer
(`InputCollectionModal`) and a frozen mobile wire record (`MobileXpromptInputWire`).
Gate inputs should reuse it rather than invent a fourth form system.

## Part 1 — Mechanics: How Input Reaches a Gate Command

### The command is fixed; only stdin is variable

`_GateCommand` holds an immutable `argv` tuple validated at creation
(`model_options.py:23-53`). `argv[0]` must be a relative path to a bundle-owned
executable resource. The executor resolves it, re-verifies its SHA-256 against the
envelope, and execs `(/proc/self/fd/N, *argv[1:])` with `shell=False`
(`executor.py:391-437`). There is no interpolation, binding, template, or
environment-variable field anywhere in the command object.

**User input can never become an argv element.** Both prior passes independently reached
this conclusion and it is correct and deliberate: the command is hashed at creation, so
anything that mutated argv would break the "the user approved exactly this command"
contract. The consequence is that "arguments" in the user-facing sense must be expressed
as **stdin JSON fields** — and neither the docs nor the `/sase_gate` skill says so.

### One JSON value, on stdin, shared by every selected option

```python
normalized_input = {} if input_data is None else input_data
for option in selected:
    _validate_json_instance(
        normalized_input, option.input_schema, f"option {option.id} input"
    )
```

`executor.py:84-90`. The docstring is explicit: *"Every selected option receives the
same JSON input value."* It is written to stdin as canonical JSON plus a newline
(`executor.py:415`) and persisted verbatim into the write-once response as `"input"`
(`executor.py:197-207`). Omitting `input_schema` yields `{}` — the *permissive* empty
schema, which accepts every JSON value, so omission does **not** mean "no input."

Three consequences follow, all verified:

1. **AND-branch members must all admit each other's fields.** `plan_gate.py:551-578`
   carries an explicit comment working around this — `commit` must accept
   `coder_prompt`/`coder_model` even though only `approve` reads them, because both are
   selected together. The model says "per option"; execution means "shared
   intersection." Strict `additionalProperties: false` schemas make this especially
   brittle.
2. **An input-schema failure leaves no trace.** The validation loop sits *before* the
   per-option `try` block that calls `_record_execution_error`
   (`executor.py:84-136`, confirmed by reading the control flow). A rejected input raises
   straight out with no entry in the bundle's `errors/` directory, so pressing `d` on the
   notification shows nothing. This is the hardest possible failure to diagnose, and it is
   exactly the failure a would-be user of custom input hits first.
3. **Multi-command execution is sequential but not transactional.** `response.json` is
   written only after *every* selected option succeeds (`executor.py:197-207`). A
   mid-branch failure therefore leaves the gate pending and answerable while earlier
   commands have already produced side effects; retrying re-runs them. This matters much
   more once inputs are user-supplied (deployment targets, deletion scopes) than it does
   for today's mostly-fixed commands.

### `feedback` is a parallel channel, not an input field

Feedback is normalized independently (`executor.py:349-379`), ranked
`disabled < optional < required` across the selected options, and written to the
response's top-level `feedback` key. **It is never merged into `input` by the executor.**
Whether a command sees it depends entirely on the client surface deciding to copy it in.

### The authoring surface is closed

`GateOption.from_mapping` rejects unknown fields, allowing only `id`, `label`, `command`,
`input_schema`, `result_schema`, `icon`, `default_selected`, `feedback`
(`model_options.py:79-92`). The top-level request is likewise closed
(`model_request.py:195-215`), and pins `schema_version == 3`. There is no field anywhere
in v3 by which a producer can say *"ask the reviewer for a target environment before
running this."*

## Part 2 — Surface by Surface: Who Can Actually Supply Input

| Surface | Structured input? | Free text → `input`? | Mechanism |
|---|---|---|---|
| ACE — generic/custom gate | **No** | **Never** | `input_data={}` hardcoded |
| ACE — plan / epic | Yes, bespoke | via `feedback` key | dedicated modal + host assembly |
| ACE — question | Yes, bespoke | as `global_note` | generated per-question schema + 654-line form modal |
| ACE — HITL | Yes, bespoke | separate | dedicated modal builds the dict |
| Mobile (app → gateway → host) | No | iff option **id** == `"feedback"` | id-string heuristic |
| Telegram | No | iff `input_schema.required` contains `"feedback"` | schema-inspection heuristic |
| CLI (`sase gate`) | **No answer path at all** | — | only `create` and `wait` exist |
| Direct Python caller | Yes, arbitrary | n/a | `execute_gate_selection(..., input_data=...)` |

### ACE: the plumbing is ready, the collection is missing

```python
GateSubmission(
    selected_option_ids=result.selected_option_ids,
    feedback=result.feedback,
    input_data={},
)
```

`_notification_custom_gate.py:55-63`. `GateSubmission` is documented as *"Surface-neutral
input for one gate executor call"* and its `input_data` is an `object | None` passed
straight through to the executor (`_notification_gate_execution.py:19-24`). The **only**
thing missing is a way for the modal to produce a value — and the modal cannot:
`GateBranchControls` composes exactly one text widget, `#gate-feedback-input`
(`gate_branch_controls.py:162-163`), and its `Resolved` message carries only
`selected_option_ids` and `feedback` (`:36-46`). `CustomGateModalResult` mirrors that
pair (`custom_gate_modal.py:59-65`).

**Net effect:** author a custom gate with `"input_schema": {"type": "object", "required":
["target_env"]}` and creation succeeds (there is no `custom.py` in
`kind_validation/` — verified: the directory holds `plan.py`, `question.py`, `launch.py`,
`bead_snooze*.py`, `task_triage*.py`, `preview_recovery.py`, `resources.py`, and no
custom validator). Every ACE submission then fails `schema_validation_failed`, with no
error recorded, and the gate stays pending until it times out or is cancelled. This has
not bitten yet only because the `/sase_gate` skill's example and every test fixture use
the permissive `{"type": "object"}` (`skills/sase_gate.md:117-119`,
`tests/ace/tui/test_notification_custom_gate.py:95`) — copied without explanation.

### Three surfaces, three incompatible feedback→input rules

This is a live correctness bug, not merely an inconsistency:

- **ACE** never copies feedback into input (`_notification_custom_gate.py:61`).
- **Mobile** copies it iff the literal string `"feedback"` is among the *selected option
  ids*: `if feedback and "feedback" in selected_option_ids`
  (`_mobile_notification_actions.py:67-69`). Added specifically to repair launch gates
  whose `feedback` option requires the same-named input property (commit `1bf22f300`).
- **Telegram** copies it iff the selected option's `input_schema.required` contains
  `"feedback"` — `feedback_is_command_input()`
  (`sase-telegram/src/sase_telegram/gate_flow.py:326-337`), applied in
  `inbound.py:324-336`. Verified verbatim in the checkout.

Telegram's rule is the best of the three and is the closest thing to a general principle
already shipping. The same custom gate can be answerable from Telegram and unanswerable
from ACE.

### The mobile path is four layers across two repos — and contract-frozen

Neither prior pass traced this, and it materially changes the cost of any wire change.
The mobile route is: **mobile app → `sase_gateway` (Rust) → host bridge → Python
`mobile_notifications.py` → executor.**

- The request struct is Rust: `MobileGateActionRequest` in
  `sase_core::notifications::mobile` (`mobile.rs:331`) and `routes.rs:1446`.
- The wire shape is a **published contract**: `GateActionRequestWire` in
  `sase_gateway/contracts/api_v1/mobile_api_v1.json`, declaring exactly
  `{prefix, schema_version, selected_option_ids, feedback}` and nothing else.
- That snapshot is **freeze-tested**: `contract.rs::committed_contract_snapshot_is_current`
  fails if the generated snapshot drifts from the committed JSON.
- Python then re-validates the same two fields at
  `mobile_notifications.py:60-95` (`MOBILE_NOTIFICATION_WIRE_SCHEMA_VERSION = 4`).

So adding `input` / `option_inputs` to the mobile path means: edit `contract.rs`,
regenerate the snapshot, update the Rust request struct and `routes.rs`, then update the
Python bridge — a cross-repo change with a version bump. This also engages the repo's own
**Rust Core Backend Boundary** rule: a submission-normalization contract that ACE,
mobile, Telegram, and a CLI must all agree on is core backend behavior by that rule's own
litmus test, so it belongs in `sase-core`, not in Python glue.

### The bespoke-modal tax

Every kind that needs a real argument bought it with hand-written code:

- **plan/epic** — `coder_prompt`, `coder_model`, `epic_launch_mode` assembled in
  `plan_approval_actions.py:238-260`, collected by `ApproveOptionsModal`
  (`approve_options_modal.py:277-342`), schema in `plan_gate.py:551-578`.
- **question** — a JSON Schema generated per question set
  (`user_question_actions.py:259-335`) and a 654-line bespoke form modal
  (`user_question_modal.py`). The richest input UI in the system, reachable by exactly one
  gate kind.
- **HITL** — `{action, approved, edited_output}` built by hand
  (`_notification_hitl_modal.py:177-190`).
- **launch** — needs one string, so it invents a *third option id* (`feedback`) whose only
  job is to carry it (`launch_request_gate.py:109-114`;
  `launch_approval_actions.py:141-148`). A selection is silently rewritten from `reject`
  to `feedback` when text is present.

Each also needs a matching mobile route and Telegram flow, or it simply does not work
there.

### Smuggling structured data through free text

`GateAdapter.validate_selection` documents the compromise in its own docstring
(`adapters.py:218-238`):

> *"The generic gate form carries structured input for some kinds in their one free-text
> feedback field, which no option command can see. Kinds that parse that text check it
> here so a typo leaves the gate pending instead of answering it with an instruction the
> host cannot follow."*

Snooze durations ride in the feedback string and are re-parsed twice — defensively before
the response is persisted (`snooze_gate.py:373-388`, `_task_gate_response.py:123-140`),
and again host-side in `apply_side_effects`. The command never sees the duration.

### Non-terminal input: `edit_file`

A second, quite different channel: `operations` with `kind: "edit_file"`
(`model_request.py:25-50`). The reviewer opens an editable bundle resource in `$EDITOR`;
SASE revalidates and refreshes the reviewed hash before approval continues
(`service.py:423-448`). In practice it is plan-only — `plan_gate.py:155-158` is the sole
producer and `kind_validation/plan.py:115` pins its exact shape. A custom gate may
declare an operation and nothing will render it.

## Part 3 — What Already Exists That You Should Reuse

This is where the two prior passes disagreed, and the disagreement dissolves once you
count the form systems already in the tree.

ACE currently contains **three independent, non-interoperating form implementations**,
~1,850 lines total:

| Implementation | Lines | Driven by | Used by |
|---|---|---|---|
| `schema_object_form.py` | 624 | JSON Schema (Draft-ish subset) | axe entry editor only |
| `input_collection_modal.py` | 566 | xprompt `InputArg` | prompt/xprompt input collection |
| `user_question_modal.py` | 654 | generated per-question schema | question gate only |

**`SchemaObjectForm`** (report `__a`'s pick) is a genuinely good pure model — no Textual,
no I/O, local `$ref` resolution, deterministic required-first ordering, and a documented
editor-kind ladder: `enum`, `bool`, `int`, `number`, `string`, string arrays, with a
**YAML fallback for any compound or ambiguous shape** (`oneOf`/`anyOf`/`allOf`/`not`, or
multi-type). Caveat report `__a` did not note: it is coupled to `sase.config` types
(`ConfigEditOp`, `ConfigField`, `ConfigConstraints`) and models config *layering*
(effective / target / inherited / provenance), which a gate form does not have. Reusable,
but not a drop-in.

**`InputArg` / `InputType` + `InputCollectionModal`** is the better fit, and it directly
validates report `__b`'s "closed vocabulary" recommendation — because the closed
vocabulary **already exists and is already cross-surface**:

- Model: `InputArg{name, type, default (UNSET ⇒ required), description, repeatable}`
  with `InputType ∈ {word, line, text, path, agent, int, bool, float}`
  (`xprompt/models.py:22-90`), including `validate_and_convert` per type.
- ACE renderer: `InputCollectionModal` — typed validation, required/optional reveal,
  `ctrl+t` path completion, literal-escape hatch.
- **Frozen mobile wire:** `MobileXpromptInputWire{name, type, required, default_display,
  description, position, repeatable}` already exists in the same `mobile_api_v1.json`
  contract that carries `GateActionRequestWire`.

Two honest gaps: `InputType` has **no `enum`/`choices`** member (snooze durations and
target-environment pickers want one), and Telegram does **not** yet render xprompt inputs
(verified: no `InputArg` usage in `sase-telegram/src/`). So reuse buys you ~2 of 3
surfaces and a contract precedent, not a free lunch — but it is far cheaper than a fourth
form system.

**Resolution of the `__a` / `__b` disagreement.** `__a` recommended schema-driven forms
(reusing `SchemaObjectForm`); `__b` recommended a closed declarative vocabulary
compiling *down to* schema, explicitly warning that a general schema-to-form renderer is
a rabbit hole (`question_response_schema()` really does emit `allOf`/`if`/`then`/
`prefixItems`). **`__b` is right on direction, `__a` is right that the renderer already
exists.** The synthesis: adopt the closed authoring vocabulary (`__b`), implement it by
extending `InputArg`/`InputCollectionModal` rather than inventing one (`__a`'s instinct,
better asset), and keep `SchemaObjectForm`'s YAML-fallback pattern as the escape hatch
for schemas the vocabulary cannot express.

Their second apparent conflict — `__a` ranked the per-option submission contract #1 while
`__b` ranked it #5 — also dissolves. `inputs:` is *declared* per option, so its natural
submission shape *is* per option. These are not two competing items; they are one item,
and doing them separately would mean designing the wire twice.

## Part 4 — Quick Overview: How Custom Gate Command Inputs Work Today

1. A gate option declares an optional JSON Schema in `input_schema`. Omitted means `{}`,
   the **permissive** empty schema — not "no input."
2. At submission a client passes one JSON value as `input_data`. The executor validates
   that **same** value against **every** selected option's `input_schema`, then writes it
   to each command's **stdin** as canonical JSON. It is persisted in the response as
   `"input"`.
3. Command `argv` is fixed and hashed at creation. **No user input ever reaches the
   command line.** "Arguments," in the user-facing sense, are stdin JSON fields.
4. `feedback` is a separate top-level string with a three-mode ladder
   (`disabled`/`optional`/`required`). It is *not* part of `input` unless a client surface
   explicitly copies it in — and the three surfaces disagree about when to: ACE never,
   mobile iff an option *id* is literally `feedback`, Telegram iff a selected schema's
   `required` lists `feedback`.
5. **For custom gates specifically:** ACE sends `input_data={}` unconditionally. There is
   no field, prompt, or form by which a reviewer can supply an argument. The `feedback`
   note is stored in `response.json` and returned by `sase gate wait --json` — so the
   *producing agent* sees it, but the *reviewed command* does not.
6. Every gate kind that does take real arguments (plan, question, HITL, launch) gets them
   from a hardcoded modal written for that kind, with matching hardcoded assembly on each
   remote surface. Snooze and triage instead smuggle structured data through the free-text
   field and re-parse it host-side.
7. There is no `sase gate answer`. `sase gate` exposes only `create` and `wait`
   (`main/parser_gate.py`), so there is no headless or scriptable way to supply input and
   no way to exercise a non-trivial `input_schema` in a test.
8. A custom gate whose schema requires any property is accepted at creation, is
   permanently unanswerable from ACE and mobile, and its failure is recorded nowhere.
9. Neither `docs/notifications.md` nor the `/sase_gate` skill explains any of this. The
   skill shows `input_schema` in its example without a word about where a value comes
   from.

## Part 5 — Ranked Improvements

Items **2, 4, 6, and 7** are cheap, independent, and can land immediately without waiting
on item 1. Item 1 is the real project and requires cross-repo contract work.

### 1. Declarative per-option `inputs:`, declared and submitted per option

The headline fix, merging what `__a` ranked #1–#2 with what `__b` ranked #1 and #5.

Add an optional per-option `inputs` array — a **closed** widget vocabulary, e.g.
`{id, label, type, required, default, placeholder, choices, help}` — rendered by
`GateBranchControls` beneath the branch it belongs to, so the widgets appear in ACE and
the same declaration drives Telegram's step flow and the mobile form. Every surface then
builds input mechanically from field ids, with no per-kind code.

Three design commitments that make this tractable:

- **Reuse `InputArg`/`InputType` and `InputCollectionModal`** instead of inventing a
  fourth vocabulary and a fourth form. Add the missing `enum`/`choices` type; the mobile
  wire record (`MobileXpromptInputWire`) already exists and can be reused or mirrored.
- **Submit per option** (`{"restart": {...}, "verify": {...}}`), not as one shared blob.
  This is the same decision as the authoring shape, so make it once. It removes the
  "every AND member must admit every other member's fields" workaround that
  `plan_gate.py:551-578` documents in a comment, and makes the schemas honest. Keep the
  current shared-value behavior for existing v3 bundles.
- **Keep `input_schema` as the enforcement layer.** `inputs` is the *authoring* layer;
  creation compiles the declared fields into (or validates them against) the schema, so
  the executor contract is untouched. Do **not** attempt to render arbitrary Draft 2020-12
  schemas; provide `SchemaObjectForm`'s YAML-style raw fallback for anything the
  vocabulary cannot express, or reject such schemas at creation.

Plan for the cross-repo cost up front: per the Rust Core Backend Boundary rule the
submission normalization belongs in `sase-core`, and the mobile wire change touches
`contract.rs`, the committed `mobile_api_v1.json` snapshot (freeze-tested), the Rust
request struct, `routes.rs`, and the Python bridge. Settle two things early: field values
land verbatim in `response.json`, so a `secret` field type needs a redaction story before
it is offered; and recalling the last value per gate kind is a cheap, high-value
follow-on.

### 2. Unify the feedback→input rule across every surface

Pick one rule, put it in shared code, delete the other two. Recommended: inject the
reviewer's note as `input.feedback` whenever the selected option's `input_schema`
declares a `feedback` **property** — essentially Telegram's `feedback_is_command_input()`
generalized from `required` to `properties` and lifted into shared Python (ideally Rust
core, since all three surfaces consume it).

Cheap, fixes a live cross-surface bug, natural prerequisite for #1 (feedback becomes just
another input field with special presentation), and it lets the launch gate drop its fake
`feedback` option id. **Flag the risk:** generalizing `required` → `properties` changes
behavior for existing gates on all three surfaces, so audit built-in schemas first.
Treat the unified helper as an explicitly-labelled compatibility shim with a deletion
trigger: once #1 lands, feedback stops being magic and the shim goes.

### 3. Fail closed at creation instead of at submission

Add `kind_validation/custom.py` — its absence is why the trap exists — and validate that
each option's `input_schema` accepts what clients can actually produce (`{}` today, or the
compiled `inputs` after #1). A gate that cannot be answered should be a creation error
with a pointed message, not an accepted request that dies silently at submit time. While
there: declare the JSON Schema dialect explicitly, validate declared defaults, distinguish
"no input" from the permissive `{}`, decide deliberately whether `format` is
annotation-only (today it is: the executor builds `Draft202012Validator` with no
`FormatChecker`), and impose size/depth/property-count limits before values reach stdin
and durable response files.

### 4. Record input-validation failures in the bundle error log

Move the validation loop (`executor.py:84-90`) inside the error-recording path, or wrap
it in its own `_record_execution_error` call, so a rejected input shows up under `d` like
every other gate failure. Today it raises before the `try` and leaves no trace. Pure
defect, ~10 lines, and it converts the #3 trap from "silently stuck forever" to
"diagnosable in one keystroke" even before #3 ships.

### 5. `sase gate answer` CLI

```bash
sase gate answer --id <request-id> --kind custom --option restart \
  --input @input.json --set target_env=staging --feedback "..."
```

A headless escape hatch when a gate is unanswerable from the TUI, the only way to make
input contracts exercisable in tests (nothing tests a non-trivial `input_schema` today),
and a supported alternative to the forbidden "run the bundle command by hand." Pair it
with a **cross-surface conformance fixture matrix** run through ACE, the mobile bridge,
Telegram, and the CLI: no-input, required/optional/defaulted scalars, invalid input, two
selected options with different inputs, feedback plus input, cancellation races, and
retry after a later-command failure. That matrix is what prevents the current
surface-specific drift from returning.

### 6. Surface the submitted input

Show `input` in the gate detail pane and debug view (neither `summary.py` nor `debug*.py`
reads it today), show which selected commands require which fields *before* execution,
and add `input` plus `option_results` to `sase gate wait --json` — currently only
`status`, `selected_option_ids`, `feedback`, `response_path` (`cli_wait.py:56-93`). A
producing agent should not have to open `response.json` to learn what the user chose.
Note that input is durable audit data, so introduce redaction/reference semantics before
supporting secrets; masked display alone is insufficient.

### 7. Document the input contract

Add a "gate inputs" section to `docs/notifications.md` and a paragraph to the
`/sase_gate` skill stating plainly: arguments are **stdin JSON fields, never argv**; here
is how to declare them; here is what the reviewer sees. Include one worked example with a
non-empty schema. Right now an agent's only signal is a `{"type": "object"}` it copies
without understanding — which is precisely why nothing has broken loudly, and why the
first author who deviates gets the silent trap in #3.

### 8. Migrate snooze and triage off free-text smuggling

Once #1 exists, express the snooze duration as a real `enum`/`string` input field and
delete the two `validate_selection` special cases (`adapters.py:218-238`,
`snooze_gate.py:373-388`, `_task_gate_response.py:123-140`). The duration then reaches the
command instead of being re-parsed host-side. This is the proof that the new mechanism is
strong enough to retire the workaround it replaces — make it the acceptance test for #1.

### 9. Harden AND-branch partial-failure and retry semantics

Before encouraging high-impact parameterized gates, at minimum document and enforce an
idempotency expectation for commands in an AND branch. Preferably persist an
execution-attempt journal (request hash, normalized/redacted option input, started and
completed option ids, results) so a retry can distinguish "run again" from "resume after
the failed option." User-selected deployment targets and deletion scopes make silent
re-execution far more consequential than today's fixed commands.

### 10. Decide `edit_file`'s scope explicitly

Either surface `operations: edit_file` in the generic gate modal — "edit this config,
then approve" is a compelling custom-gate shape — or document it as plan-only and reject
it at creation for other kinds. Today it is silently accepted and silently ignored.

### Explicit non-recommendation

**Do not let user input flow into `argv`.** Both prior passes independently reached this
and it is right. Templating or appending reviewer-supplied arguments would break the
hashed-command trust model that makes gates safe for dangerous operations. Stdin JSON is
the correct channel; the gap is collection and delivery, not transport. If a concrete use
case ever demands direct argv, it should come *after* the structured-input contract is
stable, as constrained declarative binding of a validated scalar to a complete argv
element — never `argv[0]`, no shell or template expansion, effective argv shown before
confirmation and recorded in the response. Never a free-form "extra args" text box.

## Evidence Index

| Concern | Location |
|---|---|
| Fixed argv, hashed command, `shell=False` | `notification_gates/model_options.py:23-53`, `executor.py:391-437` |
| Shared input, validated per selected option | `notification_gates/executor.py:84-90` |
| Input-validation failure not error-logged | `notification_gates/executor.py:84-136` |
| Response written only after all options succeed | `notification_gates/executor.py:197-207` |
| Feedback normalized separately | `notification_gates/executor.py:349-379` |
| Closed option/request field sets; `schema_version == 3` | `model_options.py:79-92`, `model_request.py:184-215` |
| ACE custom gate sends `{}` | `ace/tui/actions/agents/_notification_custom_gate.py:55-63` |
| `GateSubmission` is surface-neutral and generic | `ace/tui/actions/agents/_notification_gate_execution.py:19-24` |
| One text widget in shared branch controls | `ace/tui/modals/gate_branch_controls.py:36-46`, `:162-163` |
| No custom-kind validation | `notification_gates/kind_validation/` (no `custom.py`) |
| Mobile id-string heuristic | `integrations/_mobile_notification_actions.py:67-69` |
| Mobile bridge accepts only two fields; wire v4 | `integrations/mobile_notifications.py:46`, `:60-95` |
| Mobile gate wire is a frozen Rust contract | `sase-core/crates/sase_gateway/contracts/api_v1/mobile_api_v1.json` (`GateActionRequestWire`), `contract.rs:844`, `contract.rs:947` (freeze test), `routes.rs:1446`, `sase_core/src/notifications/mobile.rs:331` |
| Existing cross-surface input wire precedent | `mobile_api_v1.json` (`MobileXpromptInputWire`) |
| Telegram schema heuristic (`required`) | `sase-telegram/src/sase_telegram/gate_flow.py:326-337`, `inbound.py:324-336` |
| Telegram has no xprompt input collection | no `InputArg` usage in `sase-telegram/src/` |
| xprompt input vocabulary (no `enum` type) | `xprompt/models.py:22-32` (`InputType`), `:67-90` (`InputArg`) |
| xprompt input renderer | `ace/tui/modals/input_collection_modal.py` (566 lines) |
| Config schema form + YAML fallback ladder | `ace/tui/modals/schema_object_form.py:168-267`, `:505-524`; coupled to `sase.config` types |
| Three non-interoperating ACE form systems | `schema_object_form.py` (624), `input_collection_modal.py` (566), `user_question_modal.py` (654) |
| Plan bespoke input + AND-intersection comment | `plan_approval_actions.py:238-260`, `plan_gate.py:551-578`, `approve_options_modal.py:277-342` |
| Question generated schema + bespoke form | `user_question_actions.py:259-335`, `modals/user_question_modal.py` |
| HITL bespoke input | `ace/tui/actions/agents/_notification_hitl_modal.py:177-190` |
| Launch's fake `feedback` option | `agent/launch_request_gate.py:109-114`, `launch_approval_actions.py:141-148` |
| Free-text smuggling, acknowledged in-source | `notification_gates/adapters.py:218-238` |
| Snooze/triage re-parsing | `bead/snooze_gate.py:373-388`, `_task_gate_response.py:123-140` |
| `edit_file` operation, plan-only in practice | `model_request.py:25-50`, `plan_gate.py:155-158`, `service.py:423-448` |
| CLI has no answer path | `main/parser_gate.py` (only `create`, `wait`) |
| `wait --json` omits input | `notifications/cli_wait.py:56-93` |
| Skill/test fixtures use permissive schema | `xprompts/skills/sase_gate.md:117-119`, `tests/ace/tui/test_notification_custom_gate.py:95` |
