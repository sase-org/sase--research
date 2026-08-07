---
create_time: 2026-08-07
updated_time: 2026-08-07
status: research
---

# Custom Inputs and Arguments for SASE Gate Commands

## Question

When a user reviews a SASE gate and picks a command to run, how can they supply their own inputs/arguments to that
command? What exists today, where does it break, and what should be built next?

## Executive Summary

**The mechanism exists in the data model and is almost entirely unreachable from the UI.** Every gate option already
carries an `input_schema`, and the shared executor already pipes a JSON `input` value to each selected command's stdin
and validates it against that schema. But no client surface has a general way to *collect* that value from the user.

The one gate kind users and agents can author on the fly — `kind: "custom"` — is the worst case: ACE hardcodes
`input_data={}` for it, so a custom gate that declares any required input field is accepted at creation and then
**permanently unanswerable** from the TUI. The free-text note a reviewer types into a custom gate's `feedback` box is
never delivered to that gate's own command; it lands only in `response.json`.

Meanwhile the three client surfaces that *can* deliver a string each use a **different, incompatible heuristic** for
deciding whether to do it, so the same gate answers differently depending on where you tap it. And the gate kinds that
genuinely need arguments (plan, question, HITL, snooze, triage) each pay for it with a bespoke hardcoded modal, or by
smuggling structured data through the free-text field and re-parsing it host-side.

The recommended path is a small declarative `inputs:` vocabulary on gate options, rendered generically by the shared
branch controls and consumed uniformly by every surface, with `input_schema` retained as the enforcement layer.

## Mechanics: How Input Reaches a Gate Command

### The command is fixed; only stdin is variable

`_GateCommand` holds an immutable `argv` tuple validated at creation time
(`src/sase/notification_gates/model_options.py:23-53`). The executor resolves `argv[0]` to a hashed bundle resource,
re-verifies its SHA-256, and execs it as `(/proc/self/fd/N, *argv[1:])` with `shell=False`
(`src/sase/notification_gates/executor.py:391-437`).

**User input can never become an argv element.** That is a deliberate and correct security property — the command is
hashed at creation, so anything that changed argv would break the "the user approved exactly this command" contract.
The consequence is that "arguments" in the user-facing sense must be expressed as **stdin JSON fields**, and the docs
and skill should say so explicitly (they currently say nothing).

### One JSON value, on stdin, shared by every selected option

```python
normalized_input = {} if input_data is None else input_data
for option in selected:
    _validate_json_instance(normalized_input, option.input_schema, f"option {option.id} input")
```

`src/sase/notification_gates/executor.py:84-90`. The docstring is explicit: *"Every selected option receives the same
JSON input value."* It is written to stdin as canonical JSON plus a newline (`executor.py:415`), and persisted verbatim
into the write-once response as `"input"` (`executor.py:197-207`).

Two consequences follow:

- **AND-branch members must all admit each other's fields.** `plan_gate.py:559-571` carries an explicit comment
  working around this — `commit` must accept `coder_prompt`/`coder_model` even though only `approve` reads them,
  because both are selected together.
- **An input-schema failure is not recorded.** The validation loop sits *before* the per-option `try` block that calls
  `_record_execution_error` (`executor.py:105-136`). A rejected input raises straight out with no entry in the
  bundle's `errors/` directory, so pressing `d` on the notification shows nothing.

### `feedback` is a parallel channel, not an input field

Feedback is normalized independently (`executor.py:349-379`), ranked `disabled < optional < required` across the
selected options, and written to the response's top-level `feedback` key. **It is not merged into `input`.** Whether a
command sees it depends entirely on the client surface deciding to copy it in — see the divergence below.

### Option authoring surface is closed

`GateOption.from_mapping` rejects unknown fields, allowing only `id`, `label`, `command`, `input_schema`,
`result_schema`, `icon`, `default_selected`, `feedback` (`model_options.py:79-92`). The top-level request is likewise
closed (`model_request.py:195-215`). There is no field anywhere in schema-version 3 by which a producer can say *"ask
the reviewer for a target environment before running this."*

## Surface-by-Surface: Who Can Actually Supply Input

| Surface | Structured input? | Free text → `input`? | Mechanism |
|---|---|---|---|
| ACE — generic/custom gate | **No** | **Never** | `input_data={}` hardcoded |
| ACE — plan / epic | Yes, bespoke | via `feedback` key | dedicated modal + host assembly |
| ACE — question | Yes, bespoke | as `global_note` | generated per-question schema + form modal |
| ACE — HITL | Yes, bespoke | separate | dedicated modal builds the dict |
| Mobile gateway | No | iff option **id** == `"feedback"` | id-string heuristic |
| Telegram | No | iff `input_schema.required` contains `"feedback"` | schema-inspection heuristic |
| CLI (`sase gate`) | **No answer path at all** | — | only `create` and `wait` exist |

### ACE generic gate: input is hardcoded empty

```python
submit_gate_execution_task(
    app, notification,
    GateSubmission(
        selected_option_ids=result.selected_option_ids,
        feedback=result.feedback,
        input_data={},
    ),
)
```

`src/sase/ace/tui/actions/agents/_notification_custom_gate.py:55-63`.

The plumbing beneath it is fully generic — `GateSubmission.input_data` is an `object | None` passed straight through
to the executor (`_notification_gate_execution.py:18-24`, `:128-138`). The *only* thing missing is a way for the modal
to produce a value.

And the modal cannot: `GateBranchControls` composes exactly one text widget, `#gate-feedback-input`
(`gate_branch_controls.py:162-163`), and its `Resolved` message carries only `selected_option_ids` and `feedback`
(`gate_branch_controls.py:36-46`). `CustomGateModalResult` mirrors that pair (`custom_gate_modal.py:59-65`).

**Net effect:** author a custom gate with

```json
"input_schema": {"type": "object", "required": ["target_env"]}
```

and creation succeeds (there is no `custom.py` in `src/sase/notification_gates/kind_validation/`, so nothing checks
it), but every ACE submission fails `schema_validation_failed`, with no error recorded in the bundle. The gate stays
pending until it times out or is cancelled. The reason this has not bitten yet is cargo cult: the `/sase_gate` skill's
example and every test fixture use the permissive `{"type": "object"}`
(`src/sase/xprompts/skills/sase_gate.md:117-119`, `tests/ace/tui/test_notification_custom_gate.py:95`).

### Three surfaces, three incompatible feedback→input rules

This is a live correctness bug, not merely an inconsistency:

- **ACE** never copies feedback into input (`_notification_custom_gate.py:61`).
- **Mobile** copies it iff the literal string `"feedback"` is among the *selected option ids*:
  `if feedback and "feedback" in selected_option_ids` (`_mobile_notification_actions.py:67-69`). That works only
  because the launch gate happens to name an option `feedback`. The bridge accepts nothing but
  `selected_option_ids` and `feedback` (`mobile_notifications.py:74-94`).
- **Telegram** copies it iff the selected option's `input_schema.required` contains `"feedback"` —
  `feedback_is_command_input()` in `sase-telegram/src/sase_telegram/gate_flow.py:326-336`, applied in
  `inbound.py:324-336`.

Telegram's rule is the best of the three and is the closest thing to a general principle already shipping. The same
custom gate can therefore be answerable from Telegram and unanswerable from ACE.

### The bespoke-modal tax

Every kind that needs a real argument bought it with hand-written code:

- **plan/epic** — `coder_prompt`, `coder_model`, `epic_launch_mode` assembled in `plan_approval_actions.py:238-248`,
  collected by `ApproveOptionsModal` (`p` = edit prompt, `m` = model picker, `approve_options_modal.py:277-342`),
  with a per-option schema built in `plan_gate.py:551-578`.
- **question** — a JSON Schema generated per question set (`user_question_actions.py:259-335`) and a 654-line bespoke
  form modal (`user_question_modal.py`). This is the richest input UI in the system and it is reachable by exactly one
  gate kind.
- **HITL** — `{action, approved, edited_output}` built by hand in `_notification_hitl_modal.py:177-190`.
- **launch** — needs one string, so it invents a *third option id* (`feedback`) whose only job is to carry it
  (`launch_request_gate.py:109-114`, `:142-149`; `launch_approval_actions.py:141-148`). A selection is silently
  rewritten from `reject` to `feedback` when text is present.

Each of these also needs a matching mobile route and Telegram flow, or it simply does not work there.

### Smuggling structured data through free text

`GateAdapter.validate_selection` documents the compromise in its own docstring
(`src/sase/notification_gates/adapters.py:218-238`):

> *"The generic gate form carries structured input for some kinds in their one free-text feedback field, which no
> option command can see. Kinds that parse that text check it here so a typo leaves the gate pending instead of
> answering it with an instruction the host cannot follow."*

Snooze durations ride in the feedback string and are re-parsed twice — once defensively before the response is
persisted (`snooze_gate.py:373-388`, `_task_gate_response.py:123-140`), and again host-side in `apply_side_effects`.
The command itself never sees the duration. This is a workaround for exactly the gap this document is about.

### Non-terminal input: `edit_file`

There is a second, quite different input channel: `operations` with `kind: "edit_file"`
(`model_request.py:25-50`). The reviewer opens an editable bundle resource in `$EDITOR`; SASE revalidates and refreshes
the reviewed hash before approval continues (`service.py:423-448`). In practice it is plan-only — `plan_gate.py:155-158`
is the sole producer and `kind_validation/plan.py:115` pins its exact shape. A custom gate may declare an operation and
nothing will render it.

## Overview: How Custom Gate Command Inputs Work Today

1. A gate option declares an optional JSON Schema in `input_schema`. It defaults to `{}` (accept anything).
2. At submission a client passes one JSON value as `input_data`. The executor validates that **same** value against
   **every** selected option's `input_schema`, then writes it to each command's **stdin** as canonical JSON. It is
   persisted in the response as `"input"`.
3. Command `argv` is fixed and hashed at creation. **No user input ever reaches the command line.**
4. `feedback` is a separate top-level string with a three-mode ladder (`disabled`/`optional`/`required`). It is *not*
   part of `input` unless a client surface explicitly copies it in — and the three surfaces disagree about when to.
5. **For custom gates specifically:** ACE sends `input_data={}` unconditionally. There is no field, prompt, or form by
   which a reviewer can supply an argument. The `feedback` note is collected, stored in `response.json`, and returned
   by `sase gate wait --json` — so the *producing agent* sees it, but the *reviewed command* does not.
6. Every gate kind that does take real arguments (plan, question, HITL, launch) gets them from a hardcoded modal
   written specifically for that kind, with matching hardcoded assembly on each remote surface.
7. There is no `sase gate answer` CLI. `sase gate` exposes only `create` and `wait` (`main/parser_gate.py`), so there
   is no headless or scriptable way to supply input, and no way to exercise an input contract in a test.
8. Neither the docs (`docs/notifications.md`) nor the `/sase_gate` skill explains any of this. The skill shows
   `input_schema` in its example without a word about where a value comes from.

## Recommended Improvements, Ranked

### 1. Declarative `inputs:` on gate options, rendered generically

Add an optional per-option `inputs` array — a small **closed** widget vocabulary, e.g.
`{id, label, type: string|text|enum|bool|number|path, required, default, placeholder, choices, help}` — and render it
in `GateBranchControls` beneath the branch it belongs to, so the widgets appear in ACE, and the same declaration drives
Telegram's step flow and the mobile form. Every surface then builds `input_data` mechanically from field ids.

Keep `input_schema` as the **enforcement** layer and make `inputs` the **authoring** layer: creation compiles the
declared fields into (or validates them against) the schema, so the executor contract is untouched.

Deliberately *do not* try to render arbitrary Draft 2020-12 schemas. `question_response_schema()`
(`user_question_actions.py:259-335`) shows what real schemas look like — `allOf`/`if`/`then`/`prefixItems` — and a
general schema-to-form renderer is a rabbit hole. A closed vocabulary that compiles *down* to a schema is tractable,
reviewable, and enough for every use case in the repo today.

This is the headline fix. It makes `input_schema` reachable, retires the bespoke-modal-per-kind tax, and is the thing
that lets `/sase_gate` offer genuine arguments. Design notes worth settling up front: field values land in
`response.json`, so a `secret` field type needs a redaction story; and recalling the last value per gate kind is a
cheap, high-value follow-on.

### 2. Unify the feedback→input rule across every surface

Pick one rule and delete the other two. Recommended: **inject the reviewer's note as `input.feedback` whenever the
selected option's `input_schema` declares a `feedback` property** — essentially Telegram's existing
`feedback_is_command_input()` (`gate_flow.py:326-336`), generalized from `required` to `properties` and lifted into
shared Python so all three surfaces call it.

Cheap, fixes a live cross-surface bug, and is a natural prerequisite for #1 (feedback becomes just another input field
with special presentation). It also lets the launch gate drop its fake `feedback` option id.

### 3. Fail closed at creation instead of at submission

Validate at `sase gate create` that each option's `input_schema` accepts the input its clients can actually produce —
`{}` today, or the compiled `inputs` after #1. A gate that cannot be answered should be a creation error with a
pointed message, not an accepted request that dies silently at submit time. Add a `kind_validation/custom.py` for this;
its absence is why the current trap exists.

### 4. `sase gate answer` CLI

```bash
sase gate answer --id <request-id> --kind custom --option restart \
  --input @input.json --set target_env=staging --feedback "..."
```

Gives a headless escape hatch when a gate is unanswerable from the TUI, makes input contracts exercisable in tests
(nothing tests a non-trivial `input_schema` today), and gives agents and scripts a supported alternative to the
forbidden "run the bundle command by hand."

### 5. Per-option input instead of one shared blob

Let `input_data` optionally be keyed by option id (`{"restart": {...}, "verify": {...}}`), falling back to the current
shared-value behavior. Removes the "every AND member must admit every other member's fields" workaround that
`plan_gate.py:559-571` documents in a comment, and makes the schemas honest.

### 6. Record input-validation failures in the bundle error log

Move the `input_schema` validation loop (`executor.py:84-90`) inside the error-recording path, or wrap it in its own
`_record_execution_error` call, so a rejected input shows up under `d` (debug) like every other gate failure. Today it
raises before the `try` and leaves no trace — the hardest possible failure to diagnose.

### 7. Surface the submitted input

Show `input` in the gate detail pane and debug view (neither `summary.py` nor `debug*.py` reads it today), and add
`input` plus `option_results` to the `sase gate wait --json` payload — currently only `status`,
`selected_option_ids`, `feedback`, `response_path` (`notifications/cli_wait.py:56-93`). A producing agent should not
have to open `response.json` to learn what the user actually chose.

### 8. Migrate snooze and triage off free-text smuggling

Once #1 exists, express the snooze duration as a real `string`/`enum` input field and delete the two
`validate_selection` special cases (`adapters.py:218-238`, `snooze_gate.py:373-388`,
`_task_gate_response.py:123-140`). The duration then reaches the command instead of being re-parsed host-side. Good
proof that the new mechanism is strong enough to retire the workaround it replaces.

### 9. Document the input contract

Add a "gate inputs" section to `docs/notifications.md` and a paragraph to the `/sase_gate` skill stating plainly:
arguments are **stdin JSON fields, never argv**; here is how to declare them; here is what the reviewer sees. Include
one worked example with a non-empty schema. Right now an agent's only signal is a `{"type": "object"}` it copies
without understanding, which is precisely why nothing has broken loudly.

### 10. Decide `edit_file`'s scope explicitly

Either surface `operations: edit_file` in the generic gate modal — "edit this config, then approve" is a compelling
custom-gate shape — or document it as plan-only and reject it at creation for other kinds. Today it is silently
accepted and silently ignored.

### Explicit non-recommendation

**Do not let user input flow into `argv`.** Templating or appending reviewer-supplied arguments would break the
hashed-command trust model that makes gates safe for dangerous operations. Stdin JSON is the right channel; the gap is
collection and delivery, not the transport.

## Evidence Index

| Concern | Location |
|---|---|
| Fixed argv, hashed command | `src/sase/notification_gates/model_options.py:23-53`, `executor.py:391-437` |
| Shared input, schema validation | `src/sase/notification_gates/executor.py:84-90` |
| Input not error-logged | `src/sase/notification_gates/executor.py:84-136` |
| Feedback normalized separately | `src/sase/notification_gates/executor.py:349-379` |
| Closed option/request field sets | `model_options.py:79-92`, `model_request.py:195-215` |
| ACE custom gate sends `{}` | `src/sase/ace/tui/actions/agents/_notification_custom_gate.py:55-63` |
| Only one text widget in shared controls | `src/sase/ace/tui/modals/gate_branch_controls.py:36-46`, `:162-163` |
| Mobile id-string heuristic | `src/sase/integrations/_mobile_notification_actions.py:67-69` |
| Mobile bridge accepts only two fields | `src/sase/integrations/mobile_notifications.py:74-94` |
| Telegram schema heuristic | `sase-telegram/src/sase_telegram/gate_flow.py:326-336`, `inbound.py:324-336` |
| Plan bespoke input | `src/sase/plan_approval_actions.py:238-248`, `plan_gate.py:551-578` |
| Plan input UI | `src/sase/ace/tui/modals/approve_options_modal.py:277-342` |
| Question generated schema + form | `src/sase/user_question_actions.py:259-335`, `modals/user_question_modal.py` |
| HITL bespoke input | `src/sase/ace/tui/actions/agents/_notification_hitl_modal.py:177-190` |
| Launch's fake `feedback` option | `src/sase/agent/launch_request_gate.py:109-114`, `launch_approval_actions.py:141-148` |
| Free-text smuggling, acknowledged | `src/sase/notification_gates/adapters.py:218-238` |
| Snooze/triage re-parsing | `src/sase/bead/snooze_gate.py:373-388`, `_task_gate_response.py:123-140` |
| `edit_file` operation | `model_request.py:25-50`, `plan_gate.py:155-158`, `service.py:423-448` |
| CLI has no answer path | `src/sase/main/parser_gate.py`, `main/gate_handler.py:14-25` |
| `wait --json` omits input | `src/sase/notifications/cli_wait.py:56-93` |
| No custom-kind validation | `src/sase/notification_gates/kind_validation/` (no `custom.py`) |
| Skill/test fixtures use permissive schema | `src/sase/xprompts/skills/sase_gate.md:117-119`, `tests/ace/tui/test_notification_custom_gate.py:95` |
