# Custom user input for SASE gate commands

**Research date:** 2026-08-07  
**SASE revision:** [`4c7c635d2db3b6b882a8f1844c4153771d73dc91`](https://github.com/sase-org/sase/commit/4c7c635d2db3b6b882a8f1844c4153771d73dc91)  
**sase-telegram revision:** [`33ada2abf1f8d40acd6d5e109b4d8edae589a533`](https://github.com/sase-org/sase-telegram/commit/33ada2abf1f8d40acd6d5e109b4d8edae589a533)

## Executive conclusion

SASE already has most of a secure backend protocol for user-supplied command input:
an option can declare an `input_schema`, the executor can accept an arbitrary JSON
value, the value is validated before any selected command starts, and the value is sent
to commands as JSON on stdin without invoking a shell. The missing piece is the product
contract between that executor and the people answering gates.

Today, a normal reviewer cannot supply arbitrary gate command input in ACE, the mobile
gateway, or Telegram. ACE always submits `{}`. Mobile accepts only option IDs and
feedback, with a special case that turns feedback into command input when an option is
literally named `feedback`. Telegram has a slightly broader but still hard-coded bridge:
it copies its one feedback string to `input.feedback` when a selected option's schema
lists `feedback` as required. Only direct Python callers and specialized built-in gate
flows can populate general `input_data`.

This means `input_schema` is currently a validation/execution capability, not a generic
interactive-form capability. A custom gate may be valid at creation time yet impossible
to answer successfully from ACE or mobile if its schema requires user input.

The most important improvement is not an argv text box. It is a versioned,
transport-neutral submission contract that makes per-option structured input a
first-class part of selecting a branch. SASE should continue to use validated JSON stdin
as the canonical command boundary and add direct argv binding only later, if concrete use
cases justify it.

## Scope and terminology

There are four distinct concepts in the current implementation, and the naming can make
them easy to conflate:

| Concept | Who defines it? | Current representation | Mutable when answering? |
| --- | --- | --- | --- |
| Static command arguments | Gate author | `options[].command.argv` | No |
| Selected commands | Reviewer | `selected_option_ids` | Yes |
| Reviewer note | Reviewer | top-level `feedback` | Yes, when enabled |
| Command input | In principle, reviewer/caller | top-level `input` in the response; JSON on command stdin | Backend: yes; generic UIs: effectively no |

In this report, **custom input** means values entered by the reviewer while choosing a
gate branch. It does not mean only the `kind: "custom"` gate type, although that type is
where the missing generic behavior is clearest.

## How the current protocol works

### 1. The gate author fixes argv and declares an input schema

Each option owns a shell-free command descriptor. `argv[0]` must be a relative path to a
bundle-owned executable command resource; every remaining argv element is also fixed by
the gate author. The command object has no interpolation, binding, environment-variable,
or reviewer-argument field. See
[`model_options.py`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/notification_gates/model_options.py#L23-L53).

An option may also declare `input_schema` and `result_schema`. SASE validates both as
Draft 2020-12 JSON Schema objects at gate creation. Omitting either schema produces `{}`;
an empty JSON Schema accepts every JSON value, so omission does **not** mean "no input."
See
[`GateOption.from_mapping`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/notification_gates/model_options.py#L56-L137),
[`check_json_schema`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/notification_gates/model_validation.py#L194-L202),
and the [JSON Schema explanation of the empty schema](https://json-schema.org/understanding-json-schema/basics).

The custom-kind validator requires good presentation metadata, verifies command resource
ownership, and accepts valid option schemas, but it does not check whether any installed
review surface can render or collect those schemas. See
[`validation.py`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/notification_gates/validation.py#L75-L83)
and the custom presentation checks at
[`validation.py`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/notification_gates/validation.py#L188-L209).

### 2. The executor accepts one shared JSON value

`execute_gate_selection(bundle_path, selected_option_ids, input_data, ...)` normalizes a
missing input to `{}`. Before starting any command, it validates that **same value**
against the `input_schema` of every selected option. It then runs selected options in
query order and sends the same canonical JSON value, followed by a newline, to each
command's stdin. See
[`executor.py`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/notification_gates/executor.py#L46-L122)
and the shell-free process launch at
[`executor.py`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/notification_gates/executor.py#L391-L429).

On success, the write-once response records the shared `input`, normalized `feedback`,
selected IDs, and per-option results. It does not record an effective dynamic argv
because dynamic argv does not exist. See
[`executor.py`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/notification_gates/executor.py#L197-L207).

This is a good execution boundary: input is typed, shell injection is avoided, bundle
commands are hash-verified, and all schemas are checked before the first selected command
runs. It also has two important implications:

1. An AND branch's usable input is the intersection of every selected option's schema.
   There is no per-option input. The plan gate works around this explicitly by admitting
   `coder_prompt` and `coder_model` in both `approve` and `commit` schemas even though
   only `approve` consumes them. The source comment documents why:
   [`plan_gate.py`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/plan_gate.py#L551-L578).
2. Multi-command execution is sequential but not transactional. A later command failure
   leaves the gate answerable, while earlier commands may already have produced side
   effects. Retrying can run those earlier commands again. Custom input makes it more
   important that commands are idempotent or that SASE eventually journals option-level
   completion.

### 3. Feedback is a separate channel, except where surfaces overload it

Every option declares feedback as `disabled`, `optional`, or `required`. For an AND
selection, the strongest selected mode wins. The executor normalizes and validates the
single top-level feedback string independently of `input_data`; it never inherently
copies feedback into command stdin. See
[`_normalize_feedback`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/notification_gates/executor.py#L349-L379).

Built-in plan, launch, question, and HITL flows have specialized code that knows how to
construct their command input. For example, the plan response path builds an input object
containing feedback, coder prompt/model, or epic launch mode before invoking the common
executor. See
[`plan_approval_actions.py`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/plan_approval_actions.py#L238-L260).
That is typed adapter behavior, not a generic facility available to a custom gate author.

## What each review surface can submit today

### ACE

The shared branch controls render singleton buttons, AND toggles, and one optional or
required feedback field for the active branch. Their resolved message contains only
`selected_option_ids` and `feedback`. See
[`gate_branch_controls.py`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/ace/tui/modals/gate_branch_controls.py#L33-L47)
and the feedback widget at
[`gate_branch_controls.py`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/ace/tui/modals/gate_branch_controls.py#L162-L199).

The custom gate handler then hard-codes `input_data={}` when it submits the selection:
[`_notification_custom_gate.py`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/ace/tui/actions/agents/_notification_custom_gate.py#L45-L63).

Consequences:

- A schema that accepts `{}` works, but the command receives no reviewer-defined values.
- A schema requiring any property lets the user open and submit the modal, then fails in
  the tracked executor with `schema_validation_failed`. The modal has already closed and
  there is no ACE path to provide the missing value.
- Feedback entered in ACE is persisted as feedback but is not command input, even if an
  `input_schema` declares a `feedback` property.

ACE already has useful building blocks, although none is a drop-in gate form. The pure
[`SchemaObjectForm`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/ace/tui/modals/schema_object_form.py#L168-L267)
projects direct JSON Schema properties into typed editor metadata and supports booleans,
integers, numbers, strings, enums, string arrays, constraints, and YAML fallbacks for
compound shapes. The prompt
[`InputCollectionModal`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/ace/tui/modals/input_collection_modal.py#L94-L168)
already provides a polished required/optional field collection flow with inline
validation, but it consumes xprompt `InputArg` definitions rather than JSON Schema.

### Mobile gateway

The schema-version 4 gate action wire accepts only `selected_option_ids` and `feedback`.
There is no generic `input` field. The host creates `{}` and copies feedback into
`input.feedback` only when a selected option ID is literally `feedback`. See
[`mobile_notifications.py`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/integrations/mobile_notifications.py#L74-L95)
and
[`_mobile_notification_actions.py`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/integrations/_mobile_notification_actions.py#L47-L77).

That special case was added to repair launch gates whose `feedback` option requires the
same-named input property; the commit message is explicit that empty input had caused
schema failure. See
[`1bf22f300`](https://github.com/sase-org/sase/commit/1bf22f300b7da9712d0616180f8b00a77f0bb8dd).
It solves one built-in convention, not arbitrary custom input.

### Telegram

Telegram also presents branch choices and one feedback string. It has a different
compatibility heuristic: if any selected option's `input_schema.required` array contains
the exact property name `feedback`, Telegram copies the user's two-step feedback message
to `input_data["feedback"]`. See
[`feedback_is_command_input`](https://github.com/sase-org/sase-telegram/blob/33ada2abf1f8d40acd6d5e109b4d8edae589a533/src/sase_telegram/gate_flow.py#L326-L337)
and
[`process_text_message`](https://github.com/sase-org/sase-telegram/blob/33ada2abf1f8d40acd6d5e109b4d8edae589a533/src/sase_telegram/inbound.py#L296-L337).

This supports exactly one string-shaped convention. It cannot collect other property
names or multiple typed fields, ignores an optional (not required) command-input
`feedback` property, and depends on the separate option feedback mode to enter the
two-step text flow. It also differs from mobile, which keys the behavior from the option
ID rather than the schema, and from ACE, which never performs the copy.

### CLI and direct Python callers

The CLI exposes only `sase gate create` and `sase gate wait`; there is no generic
`answer`, `select`, or `submit` command. `wait --json` deliberately projects status,
selected IDs, feedback, and the response path, but not the recorded input or option
results. See
[`parser_gate.py`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/main/parser_gate.py#L8-L23)
and
[`cli_wait.py`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/src/sase/notifications/cli_wait.py#L59-L65).

A Python caller can invoke `execute_gate_selection(..., input_data=...)` directly and is
currently the only generic way to exercise arbitrary option input. The tests prove that
the value is validated, reaches stdin, appears in command output, and is written once:
[`test_notification_gate_execution.py`](https://github.com/sase-org/sase/blob/4c7c635d2db3b6b882a8f1844c4153771d73dc91/tests/test_notification_gate_execution.py#L97-L113).

## Main design problems

### The model says “per option,” but execution means “shared intersection”

Putting `input_schema` on each option naturally suggests that each selected command owns
its input. The executor instead validates one shared value against every selected schema
and sends it to every command. This is workable for controlled built-in producers but
awkward for open-ended custom gates. Two independently selectable commands commonly need
different arguments, and strict `additionalProperties: false` schemas make accidental
intersections especially brittle.

### Review surfaces are not protocol-equivalent

The public docs say that surfaces submit only selected IDs and feedback. That is accurate
for the UI contract but incomplete relative to the executor contract. The three generic
surfaces then apply three different input rules: always `{}`, option-ID inference, and
schema-name inference. A gate's answerability therefore depends on where it is reviewed.

### Feedback has two meanings

Feedback is designed as context for the sender and is summarized as a reviewer note.
Plan/launch compatibility code also treats it as a command parameter. That coupling
makes a generic field named `feedback` special without declaring the special behavior in
the gate request. A review note and a command's `reason`, `message`, or `ticket` argument
may overlap, but they should not be implicitly identical.

### Valid schema does not mean renderable schema

SASE accepts full Draft 2020-12 object-form schemas, while a useful interactive form
renderer needs a defined subset and presentation rules. JSON Schema provides `title`,
`description`, `default`, and `examples` annotations specifically useful to UI tools,
but `default` is only metadata and is not automatically inserted during validation. See
the official [JSON Schema annotations reference](https://json-schema.org/understanding-json-schema/reference/annotations).
SASE currently neither materializes defaults nor tells authors which annotations a gate
surface will honor.

JSON Schema also does not define a complete form layout language. Established form
systems keep validation schema and UI layout separate; for example, JSON Forms uses a
distinct UI schema for controls, layouts, and renderer-specific options. See the
[JSON Forms UI schema documentation](https://jsonforms.io/docs/uischema/). SASE should
follow that separation rather than overload validation keywords with layout policy.

The executor also constructs `Draft202012Validator(schema)` without a `FormatChecker`,
so `format` is informational rather than enforced. That is valid JSON Schema behavior,
but should be explicit in the contract if formats drive widgets such as paths, dates, or
password fields. See the
[`jsonschema` format-checking documentation](https://python-jsonschema.readthedocs.io/en/stable/api/).

### Inputs are durable audit data, not secret fields

Successful input is stored verbatim in `response.json` alongside feedback and results.
That is valuable for auditability, but it means a future form renderer should not imply
that password/token fields are safe merely because it can mask them on screen. Secret
collection needs an explicit non-persistence/redaction/reference design; until then,
gate input should be documented as durable non-secret data.

## Quick overview of how custom gate command inputs/arguments work today

- Gate authors may define fixed argv strings and an `input_schema` for every option.
- Reviewers choose a non-empty subset of one query branch and may supply one feedback
  string when the selected feedback mode permits it.
- The generic executor can accept one arbitrary JSON input value, validates that same
  value against every selected option schema, and sends it to every selected command as
  JSON on stdin. It never interpolates reviewer values into argv and never invokes a
  shell.
- ACE always supplies `{}`. Mobile supplies `{}` except for a literal `feedback` option.
  Telegram can additionally copy one feedback string to `input.feedback` when that exact
  property is required. These are incompatible special cases, not a generic input form.
- Specialized built-in gates and direct Python callers can construct richer input, but
  `sase gate` has no generic answer/submit command.
- The successful response records the input, yet normal gate summaries and `gate wait`
  omit it. A custom gate requiring arbitrary reviewer input can therefore be valid and
  durable while being unanswerable from the normal generic surfaces.

## Ranked improvements to consider

1. **Define a versioned, per-option submission contract and make it the one path for all
   surfaces.** Introduce a request/response revision whose submission looks conceptually
   like `{"selected_option_ids": [...], "option_inputs": {"deploy": {...},
   "verify": {...}}, "feedback": "..."}`. Validate each input only against its owning
   selected option and send that option's value to its command. Preserve the current
   top-level shared `input` behavior for existing v2/v3 bundles, but do not extend it as
   the long-term model. Put the submission normalization in SASE core code used by ACE,
   mobile, Telegram, and future clients; remove surface-specific inference from option
   IDs or schema property names. This resolves the deepest semantic mismatch and gives
   the UI work a stable target.

2. **Add a schema-driven input collection step to the generic gate review flow.** When a
   reviewer chooses a branch, derive fields for the selected options, collect values,
   validate them before dismissing the modal, then show a final command/input review
   summary. Start with an intentionally small portable subset: object roots; string,
   boolean, integer, number, enum, and string-array properties; `required`; defaults;
   scalar length/range/pattern constraints; and `title`/`description`/`examples`.
   Reuse or extract the parsing/editor logic in `SchemaObjectForm` and the interaction
   patterns in `InputCollectionModal`. Provide a raw JSON editor fallback for valid but
   unsupported schemas, or reject those schemas at creation when the producer requires
   universal interactive support. Required fields must disable Enter/submit until valid.

3. **Keep feedback semantically separate from command input and delete the compatibility
   heuristics.** `feedback` should remain the reviewer's note to the sender. If a command
   needs a reason or message, declare it as ordinary structured input. Migrate built-in
   feedback commands through explicit adapter-owned mapping during a compatibility
   window, then remove mobile's `option_id == "feedback"` and Telegram's
   `required contains "feedback"` tests. If an explicit convenience binding is still
   desirable, make it declared request metadata, never an inferred property-name
   convention.

4. **Keep JSON stdin as the canonical user-input boundary; treat dynamic argv as a later,
   explicit feature.** JSON stdin already preserves types, avoids shell expansion, and
   produces an auditable response. Most commands can translate structured input into
   their own flags. If real use cases demand direct argv, add constrained declarative
   bindings after the structured-input contract is stable: bind a validated scalar to a
   complete argv element, never to `argv[0]`, never use shell/template expansion, show
   the effective argv before confirmation, impose length/count limits, and record the
   effective argv in the response. Do not begin with a free-form “extra args” text box.

5. **Add creation-time answerability and schema-quality checks.** For the new contract,
   require interactive option schemas to be object-shaped, define the JSON Schema
   dialect explicitly, validate declared defaults, distinguish “no input” from the
   permissive `{}` schema, and report unsupported renderer features before publishing a
   notification. For legacy shared-input AND branches, detect incompatible strict
   schemas early and explain the intersection rule. Decide deliberately whether `format`
   is annotation-only or validated. Add size/depth/property-count limits before values
   reach command stdin or durable response files.

6. **Expose input requirements and results consistently.** Gate detail views should show
   which selected commands require which fields before execution. After resolution,
   summaries/debug views should show normalized non-secret input next to each option and
   its result. Extend machine-readable waiting/inspection with an opt-in full response or
   `option_inputs` projection rather than forcing callers to open `response.json`.
   Introduce redaction/reference semantics before supporting secrets; masked display
   alone is insufficient because input is durable.

7. **Add a generic CLI submission path and cross-surface conformance tests.** A command
   such as `sase gate answer --id ... --kind ... --select deploy --option-input
   deploy=@deploy.json` would make the protocol testable, accessible, and usable without
   ACE while still going through the verified executor. Build one conformance fixture
   matrix and run it through ACE, the mobile bridge, Telegram, and the CLI: no-input,
   required/optional/defaulted scalar fields, invalid input, two selected options with
   different inputs, feedback plus input, cancellation/races, and retry after a later
   command failure. This will prevent the current surface-specific drift from returning.

8. **Harden multi-command retry semantics before encouraging high-impact parameterized
   gates.** At minimum, document and enforce an idempotency expectation for commands in
   an AND branch. Preferably persist an execution-attempt journal containing the request
   hash, normalized (redacted as needed) option input, started/completed option IDs, and
   results, so a retry can distinguish “run again” from “resume after the failed option.”
   User-selected deployment targets, deletion scopes, and similar parameters make silent
   re-execution more consequential than today's mostly fixed commands.
