# Generalizing Plan, Question, and Launch Notifications

**Date:** 2026-07-16  
**Status:** Research — no product code changed  
**Scope:** `sase`, `sase-core`, and the notification-facing parts of `sase-telegram`

## Executive summary

Plan, question, and launch notifications already share the lowest-level `Notification` row and JSONL append path, but
they do **not** share an actionable-request protocol. Each producer independently creates request artifacts, constructs
notification fields, defines response filenames and schemas, decides whether the requesting agent blocks or continues,
and wires its response into ACE, CLI, mobile, and Telegram behavior.

The existing `sase notify create` command is much smaller than the feature this initiative needs. It currently:

- reads an unversioned JSON object from stdin;
- overrides `sender` and appends CLI tags;
- generates an id and timestamp;
- instantiates `Notification` directly;
- appends it to the store and prints only the id.

It does not validate field types or action-specific data, create a request/response directory, capture agent identity,
produce a preview, implement response choices, choose continuation behavior, run plan/launch preflight, report a
structured result, or make request-file creation and notification registration atomic. Passing `action:
PlanApproval`, `UserQuestion`, or `LaunchApproval` to the command only works if the caller has already hand-built the
correct directory and kind-specific files.

The clean target is two layers rather than one large generic function:

1. A **common interaction-request constructor** owns ids, timestamps, a versioned request envelope, standard request and
   response paths, context capture, the derived notification row, pending-action registration, and structured CLI
   output.
2. **Kind adapters** for plan, question, and launch own payload validation, presentation, response schema, privileged
   side effects, and continuation behavior.

`sase notify create` should be the public CLI front door to that service. Internal Python producers should call the
same service in-process rather than spawning the CLI as a subprocess. This gives the command and internal callers one
constructor without making Python code parse its own command output.

The safest migration preserves `PlanApproval`, `UserQuestion`, and `LaunchApproval` as compatibility projections at
first. A later decision can collapse them to one public `InteractionRequest` action. Collapsing the action immediately
is a cross-repository wire migration: the Rust core and Telegram plugin both switch exhaustively on those action names
and on their distinct response choices.

Removing the unused custom `improve_plan` and `tester` lifecycle-role system is related and helpful, but conceptually
separate from manual dynamic family attachment. The custom lifecycle machinery adds member options to plan requests,
adds `selected_member_ids` to plan responses, inserts post-plan/post-code roles in the runner loop, snapshots role
definitions, adds status-label projections, and extends the plan approval CLI and modal. Removing it first produces a
much cleaner plan request for the common constructor. Manual `%n(parent, suffix)` attachment and the standard
plan/question/code chain can remain.

The strongest evidence that the lifecycle roles are safe to retire is:

- the bundled `improve_plan.yml` and `tester.yml` definitions live under an intentionally inactive examples directory;
- the current installation reports no active `type: agent_family` definitions;
- only their prompt xprompts are active by default;
- `on_done` is validated and persisted but never read;
- failure paths never emit the `role_completed` event that would interpret `on_failure`;
- only the first custom role at a placement can run, silently ignoring additional matching roles.

## 1. The key terminology distinction

The current code uses “notification” for two different things.

### 1.1 Notification row

`src/sase/notifications/models.py::Notification` is an inbox/delivery record:

```text
id, timestamp, sender, notes, files, tags,
action, action_data,
read, dismissed, silent, muted, snooze_until
```

The Rust wire mirrors this shape and constrains `action_data` to `map<string, string>`. The row is suitable for inbox
state and for pointers to richer data. It is not suitable for storing a plan, a set of question choices, or a full
launch graph inline.

### 1.2 Actionable interaction bundle

Plan, question, and launch requests are actually bundles:

- a request id and directory;
- one or more request/preview files;
- a notification row pointing at those files;
- a response schema and response file;
- pending-action state for remote transports;
- a producer that waits, resumes, or continues asynchronously;
- a response executor that performs kind-specific side effects.

The initiative should generalize this bundle. Merely routing three helper functions through the `Notification`
dataclass would not materially change the architecture, because they already do that.

## 2. How the three flows work today

| Concern                         | Plan                                                                                              | Question                                                                                   | Launch                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| Agent-facing command            | `sase plan propose PLAN_FILE`                                                                     | `sase questions '<json>'`                                                                  | `sase launch request ...`                                                   |
| Initial command behavior        | Validates/formats/archives plan, writes `.sase_plan_pending`, terminates current model subprocess | Validates questions, writes `.sase_questions_pending`, terminates current model subprocess | Parses and preflights the launch immediately; does not terminate requester  |
| Notification creation site      | Runner later calls `handle_plan_approval()`                                                       | Runner later calls `handle_questions_flow()`                                               | Request command calls `create_launch_approval_request()` directly           |
| Request location                | sharded `plan_approval/<session>` directory                                                       | `user_question/<uuid>` directory                                                           | `launch_requests/<request_id>` directory                                    |
| Request artifacts               | `plan_request.json`; plan file attached separately                                                | `question_request.json`                                                                    | `launch_request.json`, `launch_preview.md`                                  |
| Response artifact               | `plan_response.json`                                                                              | `question_response.json`                                                                   | `launch_response.json`                                                      |
| Notification action             | `PlanApproval`                                                                                    | `UserQuestion`                                                                             | `LaunchApproval`                                                            |
| Continuation                    | Runner blocks, then may create feedback/custom/coder phase                                        | Runner blocks, reacquires a runner slot, then creates a Q&A continuation phase             | Requesting agent is told to poll; approval dispatches a new detached launch |
| Auto behavior                   | May bypass notification and auto-approve as approve/tale/epic                                     | May bypass notification and choose the first option                                        | Agent-initiated requests require approval                                   |
| Important preflight             | Plan tier validation, format/archive, member-option snapshot                                      | Question-schema validation                                                                 | Xprompt expansion, fanout planning, max-slot check, launch preview          |
| Important response side effects | Dismiss/handled state, plan archive/metadata, SDD actions, coder/epic handoff                     | Dismiss/answered state, Q&A history, prompt reconstruction                                 | Dismiss/handled state, revalidate and dispatch launch                       |

### 2.1 Plan path

The `/sase_plan` generated skill ultimately runs `sase plan propose`. `handle_plan_propose_command()` validates the plan,
formats and moves it into the machine-local plan archive, writes `.sase_plan_pending` under the current artifacts
directory, pulses ACE refresh, and terminates the agent runner's process group.

The runner detects the marker, turns it into a `plan_submitted` handoff event, and calls
`handle_plan_approval()`. That function creates:

- `plan_request.json` with `plan_file`, `session_id`, timestamp, and custom lifecycle member options;
- `plan_response.json` as the watched response path;
- a `PlanApproval` notification with the plan as its first attachment;
- `action_data` containing `response_dir`, `session_id`, project and agent identity, provider/model/runtime, and VCS tag.

Plan approval is more than a generic choice. It supports approve, run, tale, epic, commit, reject, and feedback; optional
coder prompt/model overrides; plan-tier validation; SDD archive/commit behavior; epic launch ownership; status updates;
and a runner transition to feedback, code, commit, or terminal state.

### 2.2 Question path

The `/sase_questions` generated skill runs `sase questions`. The command validates the question list, writes
`.sase_questions_pending`, and terminates the current model subprocess. The runner then creates
`question_request.json`, a `UserQuestion` notification, and a `pending_question.json` marker used by ACE as a fallback
when the notification was dismissed but the agent is still paused.

After `question_response.json` appears, the runner records request/response provenance, appends the Q&A round, rebuilds
the prompt, creates a follow-up artifacts directory, and continues in the interrupted family role. This is a dynamic
continuation protocol, not just a notification.

### 2.3 Launch path

`sase launch request` normalizes a versioned request, expands xprompts and fanout, enforces `max_slots`, builds a launch
wire preview, and writes `launch_request.json` plus `launch_preview.md`. It then creates a `LaunchApproval`
notification.

Unlike plan and question, this path does not kill and hand control to the runner. `/sase_run` tells the requesting agent
to poll `launch_response.json`. Approval re-reads the stored request, validates the original cwd, and dispatches the
stored prompt through the normal launcher. The response is updated with `dispatch_status` and `launched_count`.

### 2.4 What is already shared

All three ultimately:

- instantiate `Notification`;
- call `append_notification()`;
- register in the pending-action store as a side effect of append;
- use a notification action and string-valued `action_data`;
- point at a response directory;
- use write-once response files;
- dismiss the notification after a response;
- participate in ACE/mobile/Telegram action handling.

This is useful common infrastructure, but it begins after most request construction has already diverged.

## 3. Why `sase notify create` needs substantial enhancement

`src/sase/main/notify_handler.py::_handle_notify_create()` is a raw notification-row writer. The following gaps matter
for this initiative.

### 3.1 No input schema or version

The command checks only that a sender is present. It does not require the stdin value to be a JSON object, reject
unknown fields, validate list element types, validate `action`, or coerce `action_data` to strings before passing it to
the Rust wire. Invalid values can fail late at the binding or be rehydrated differently from how they were supplied.

A generalized request needs its own `schema_version`, `kind`, and deterministic diagnostics.

### 3.2 No request artifact construction

The command does not create a response directory or request file. An actionable notification made through the current
command is useful only if the caller already knows private conventions such as:

- `plan_request.json` / `plan_response.json`;
- `question_request.json` / `question_response.json`;
- `launch_request.json` / `launch_response.json`;
- which action-data path key is required;
- which attachments each renderer expects.

That is the opposite of a constructor.

### 3.3 No action registry

The command will accept arbitrary action names. Pending-action registration, ACE, Rust mobile projections, and Telegram
then each decide independently whether that action is supported. A successful CLI exit therefore does not mean the
result is actionable.

The enhanced command should distinguish a plain inbox notification from a registered interaction kind and validate the
latter through a kind registry.

### 3.4 No producer context capture

Plan and question helpers independently copy environment fields such as `SASE_AGENT_CL_NAME`, project file,
`SASE_AGENT_TIMESTAMP`, and root timestamp. Plan adds model/provider/runtime/VCS fields. Launch creates a separate
requester context. A common constructor should capture one normalized producer context and let adapters select what is
displayed.

### 3.5 No continuation policy

Plan/question hand control back to the runner; launch is asynchronous. The constructor needs an explicit continuation
or delivery mode, or the mode must be intrinsic to the registered kind. Hiding this difference behind one undifferenced
“notify” operation would make callers guess whether the current session survives.

### 3.6 No preflight or privileged response executor

The command cannot validate a plan tier, archive a plan, build a launch preview, enforce slot limits, validate question
choices, dispatch an approved launch, or execute plan approval side effects. These belong in kind adapters, not in an
ever-growing `if action == ...` block inside the parser handler.

### 3.7 Weak output contract

Only the notification id is printed. `/sase_run` already needs a richer result containing request id, notification id,
response directory, request path, preview path, and response path. A generalized creator should support stable JSON
output and a concise human form.

### 3.8 Non-atomic multi-store behavior

`append_notification()` first appends the JSONL row and then best-effort registers the pending action. A registration
failure leaves an inbox row that local ACE may open but remote action lookup may not resolve. Adding request-directory
creation creates a third unit that can be orphaned.

The implementation needs a declared failure policy and cleanup strategy. Full transactionality across files may be
unnecessary, but successful CLI output should imply that the request file, notification row, and pending-action record
are mutually usable.

### 3.9 Privilege/provenance risk

Today a caller can use the generic command to write a `LaunchApproval` or `PlanApproval` row pointing at handcrafted
local files. Approval paths can dispatch agents, archive plans, launch epics, and mutate metadata. Enhancing the generic
command increases the importance of validating that:

- request files live under a SASE-owned directory or an explicitly allowed path;
- request kind and filenames agree;
- launch content is revalidated at action time;
- immutable/request hashes or equivalent provenance prevent a reviewed preview from being silently replaced;
- arbitrary notification producers cannot smuggle unsupported privileged actions through a raw mode.

The system currently assumes a trusted local user, but a generic constructor should make that assumption explicit
rather than accidentally broadening it.

## 4. The action names are public contracts today

Changing construction is local. Changing the shape or action name is not.

### 4.1 SASE Python and ACE

The main repository switches on `PlanApproval`, `UserQuestion`, and `LaunchApproval` in:

- priority classification;
- pending-action registration and stale/handled detection;
- notification tabs, labels, toasts, and dispatch;
- plan/question/launch modals;
- plan and launch CLI selectors;
- attachment discovery;
- agent status and notification matching;
- mobile action execution;
- unread projection and dismissal behavior.

Several paths also hard-code the request and response filenames.

### 4.2 Rust core

`sase-core` exposes distinct public wire variants:

- `MobileActionKindWire::{PlanApproval, UserQuestion, LaunchApproval}`;
- `MobileActionDetailWire` variants with different fields;
- separate request and choice enums for plan, question, and launch;
- pending-action mapping from action string to kind;
- action-specific handled-state checks using kind-specific filenames;
- action-specific priority and attachment behavior.

The core notification row still has only `action: Option<String>` and `action_data: BTreeMap<String, String>`, so the
rich payload correctly lives in request files today. A common request envelope would let Rust inspect common pointers
without forcing all payload fields into `action_data`.

### 4.3 Telegram plugin

`sase-telegram` has separate formatters, inline keyboards, callback flows, request-file readers, response writers, and
stale cleanup for all three actions. It imports SASE's plan and launch response executors for privileged host behavior,
but still branches on the legacy action strings and filenames.

### 4.4 Consequence

There are two valid scopes:

- **Constructor unification:** one request envelope/service, while legacy action names remain adapter projections. This
  can be migrated incrementally and keeps existing mobile/Telegram clients compatible.
- **Protocol unification:** one generic action and declarative interaction schema consumed by all surfaces. This is a
  larger, versioned cross-repository change.

These should not be conflated. Constructor unification delivers most of the maintenance value without requiring the
protocol decision on day one.

## 5. What the dynamic `improve_plan` / `tester` hooks actually are

There are two different “dynamic family” features, and only one is implicated.

### 5.1 Manual family attachment should remain separable

`%n(parent, suffix)` attaches a normally launched agent to an existing family. A suffix such as `tester` is an open,
generic role name. This path is useful independently of plan approval and does not use the custom lifecycle evaluator.

Removing the lifecycle hooks does **not** require removing:

- `%n(parent, suffix)`;
- same-prompt or agent-initiated family attachment;
- open custom suffixes such as reviewer/tester;
- generic RUNNING/DONE behavior for manually attached members;
- `LaunchApproval` for agent-initiated launches.

### 5.2 Custom lifecycle roles are the removable subsystem

The removable system is `kind: agent_family` YAML plus its runner integration. A definition declares a role with:

- a suffix and prompt template;
- placement after `plan`, `code`, or another role;
- `on_done`, `on_failure`, `auto`, default, and visit-cap settings;
- optional status labels.

The inactive examples define:

- `improve_plan`, inserted after plan approval and prompted to resubmit a revised plan;
- `tester`, inserted after code completion and prompted to inspect/test the implementation.

### 5.3 Runtime path

The lifecycle system currently works through all of these steps:

1. Discover and validate `kind: agent_family` files alongside xprompts.
2. Add every discovered role to `plan_request.json` as `member_options` and `default_member_ids`.
3. Show those options in the plan approval custom modal and CLI `--with` / `--without` flags.
4. Persist `selected_member_ids` in `plan_response.json`.
5. Filter active roles after plan and after code using the captured selection.
6. Mutate the runner loop so the next iteration executes the role's prompt.
7. Snapshot definition identity, role data, visit counts, and custom display labels in artifacts.
8. Emit `role_completed` after successful follow-up iterations so a post-code role can be inserted.

`spawn_custom_role_followup()` does not launch a separate agent process. It mutates `LoopState` and creates the next
artifacts directory for the same runner process.

### 5.4 Evidence of low use and incomplete semantics

- The two example YAML definitions are deliberately outside active discovery.
- `sase xprompt list` on this installation shows no `type: agent_family` definitions.
- The two prompt templates are discoverable, but they do nothing unless an example definition is copied to an active
  xprompt directory.
- `_select_custom_role_after()` returns the first matching role. Multiple roles at one placement are discovered and
  sorted, but all except the first are silently ignored.
- `on_done` is parsed, validated, listed, and snapshotted, but no runtime code reads it. The `improve_plan` loop works
  only because its prompt instructs the agent to submit another plan.
- `on_failure` is consulted only when a `role_completed` event has a non-success outcome, but the execution loop emits
  that event only after a normal successful workflow return. Failed workflows take the error/break path instead.
- Even in the evaluator, both failure policies currently make the transition terminal, so their intended distinction
  is not implemented.

### 5.5 Why removal helps this initiative

Without custom lifecycle roles, the plan interaction no longer needs:

- member discovery during request creation;
- `member_options` and `default_member_ids` in the request;
- “Also run” notification notes;
- plan-modal member toggles;
- `sase plan approve --with/--without`;
- `selected_member_ids` in responses;
- role filtering and visit counts in the execution loop;
- post-code custom-role insertion;
- custom-role definition snapshots and display labels.

This reduces the plan adapter to plan-specific approval choices and the standard feedback/code/epic transitions. It
also prevents the new generic request envelope from prematurely growing a general dynamic-controller schema solely to
preserve an unused feature.

## 6. Expected lifecycle-role removal surface

The exact deletion set should be confirmed by tests, but the direct surface is broad.

### 6.1 Definition/discovery layer

- Remove `src/sase/agent_family/custom_definitions/`.
- Remove exports from `src/sase/agent_family/__init__.py`.
- Stop excluding `kind: agent_family` mappings from ordinary workflow loading, or explicitly reject the retired kind
  with a useful migration error.
- Remove `agent_family` catalog entries from `sase xprompt list`.
- Remove the inactive YAML examples and the two dedicated prompt xprompts unless they are worth retaining as ordinary
  manual-use xprompts.

### 6.2 Plan request/response and UI

- Remove `PlanApprovalMemberOption` and all member request/selection helpers.
- Remove member payload creation from `handle_plan_approval()`.
- Remove default-member notes from `notify_plan_approval()`.
- Remove `selected_member_ids` from plan response dataclasses and writers.
- Remove `--with` / `--without` from `sase plan approve`.
- Remove member rows and digit toggles from `ApproveOptionsModal`.
- Remove prompt-bar state that carries selected members through custom coder-prompt editing.

### 6.3 Runner/evaluator

- Remove `run_agent_exec_custom_roles.py`.
- Remove `custom_role_visit_counts` and selected-member state from `LoopState`.
- Remove custom-role selection from accepted-plan and completed-follow-up paths.
- Simplify `FamilyRuntimeMetadata`, `FamilyEvaluation`, and `PlanApprovalTransition` by deleting custom-role fields.
- Decide whether to keep the typed `role_completed` event as a future controller seam or remove it because the standard
  chain simply terminates after a completed follow-up.
- Retain the standard plan/question transition evaluator if it remains useful for the generalized interaction
  controller.

### 6.4 Artifact and display compatibility

- Stop writing `agent_family_custom_role` and custom config identity/visit data for new runs.
- Remove custom role label fields and propagation from ACE's agent model if historical artifacts do not need the labels.
- Alternatively, keep the read-only label projection for old artifacts during a compatibility window while removing all
  writers.
- Remove or update related agent-scan wire fields in Python and Rust if full cleanup is desired.

### 6.5 Configuration and documentation

- Remove `agent_family.plan_approval.default_members` from default config, JSON schema, and configuration docs.
- Rewrite `docs/agent_families.md` to retain manual attachment and agent-initiated `LaunchApproval`, while deleting
  custom lifecycle roles, member selection, sticky defaults, loop caps, and labels.
- Update ACE, xprompt, CLI, and notification docs.
- Remove custom-role unit, golden, config, TUI, and visual tests while retaining generic manual-family tests that happen
  to use suffix names such as `tester`.

### 6.6 Compatibility choice

If users may have copied the example definitions despite the current installation showing none, silently interpreting
those YAML files as workflows after removal would be confusing. Prefer either:

- a clear “`kind: agent_family` is no longer supported; use an explicit launch/xprompt workflow” load issue; or
- a documented one-release deprecation before deletion.

## 7. Recommended common interaction model

The following is a design direction, not a final schema.

### 7.1 Common request envelope

Store one versioned JSON request under a SASE-owned directory, with kind-specific data nested rather than flattened into
the notification row:

```json
{
  "schema_version": 1,
  "request_id": "req_...",
  "kind": "plan",
  "created_at": "2026-07-16T12:00:00-04:00",
  "producer": {
    "surface": "agent_skill",
    "project": "sase",
    "agent_name": "example",
    "agent_timestamp": "...",
    "agent_root_timestamp": "..."
  },
  "presentation": {
    "renderer": "plan_review",
    "summary": ["Plan ready for review"],
    "attachments": ["/path/to/plan.md"]
  },
  "response": {
    "mode": "runner_handoff",
    "path": "response.json"
  },
  "payload": {}
}
```

The common fields should be deliberately small. Plan content, question arrays, and launch graphs remain adapter payloads
or referenced files.

### 7.2 Common notification projection

The constructor derives a notification row containing:

- sender, notes, tags, and attachments from the adapter's presentation;
- an action (legacy action during migration, possibly `InteractionRequest` later);
- string pointers such as `request_id`, `request_kind`, `request_dir`, `request_file`, and `response_file`;
- selected producer identity fields needed for agent matching.

Do not put the full request JSON in `action_data`; Rust and transport wires intentionally treat that map as strings.

### 7.3 Adapter registry

Each registered kind should implement an interface conceptually like:

```text
prepare(raw payload, producer context) -> request payload + presentation
validate_request(request bundle)
validate_response(request bundle, response)
execute_response(request bundle, response) -> side-effect result
continuation_policy(request bundle) -> async | runner_handoff | other
```

The adapters remain responsible for:

- **Plan:** plan validation/archive, approval vocabulary, SDD and epic side effects, feedback/code transition.
- **Question:** question/option validation, response normalization, Q&A continuation.
- **Launch:** expansion/preview, capacity checks, immutable dispatch data, approval-time revalidation and launch.

A future HITL adapter can use the same envelope without forcing this initial change to migrate HITL immediately.

### 7.4 Library and CLI ownership

Add a service below `main/notify_handler.py`, for example under `sase.notifications`, and make the CLI a thin parser and
renderer around it. The service should return a typed result including all paths and ids.

Internal callers should use that service directly. Agent-facing generated skills can use `sase notify create` once the
CLI supports the registered kinds. Existing commands can remain as compatibility frontends that translate their
arguments into the same service.

Because request construction, pending-action state, and mobile interpretation are shared backend behavior, the stable
envelope and generic pending-state rules belong at or below the Rust core boundary. Plan archival and launch dispatch
can remain Python adapters until there is a reason for another frontend to execute them directly.

### 7.5 Suggested CLI behavior

One possible shape is:

```bash
sase notify create --kind question --file request.json --output json
```

or a single stdin object that includes `kind`. The final spelling should follow the project CLI rules: complete help,
alphabetized options, and short aliases for every public long option.

Stable JSON output should include at least:

```json
{
  "schema_version": 1,
  "notification_id": "...",
  "request_id": "...",
  "kind": "question",
  "request_dir": "...",
  "request_file": ".../request.json",
  "response_file": ".../response.json",
  "preview_file": null
}
```

Plain notification creation should remain possible, either as `kind: notification` or a clearly separate raw mode. Raw
mode should not be able to impersonate privileged registered actions without adapter validation.

## 8. Compatibility-first migration plan

### Phase 0: settle the contract boundary

Decide whether the goal is constructor unification or immediate protocol unification; define the common envelope,
continuation modes, and trust policy; and decide how long in-flight legacy requests must remain actionable.

### Phase 1: retire custom lifecycle roles

Remove the unused definition, selection, runner, status-label, config, docs, and test surfaces. Keep manual `%n` family
attachment and the standard plan/question/code chain. This prevents unused member-selection fields from entering the new
contract.

### Phase 2: add the shared service behind `sase notify create`

Implement typed input validation, context capture, standard paths, request/response bundle creation, notification
projection, pending-action registration, cleanup on partial failure, metrics, and structured output. Preserve the
existing raw notification mode.

At this phase, adapters may still project legacy action names and filenames.

### Phase 3: migrate launch first

Launch is the best first adapter because it already has:

- a versioned input schema;
- a request id and owned request directory;
- a preview artifact;
- a typed creation result;
- explicit async behavior;
- a shared response executor.

Use the common service for its envelope/notification, then keep launch-specific planning and dispatch in the adapter.

### Phase 4: migrate question

Move question validation and request-file creation under the adapter. Replace the kind-specific request path with the
common pointers while preserving the pending marker and runner handoff. Consolidate TUI and mobile response writing
around one question response executor; today question response logic is more duplicated than plan/launch logic.

### Phase 5: migrate plan

Plan is last because it has the most side effects and compatibility behavior. Translate `sase plan propose` into plan
adapter preparation while retaining validation, archive semantics, auto approval, feedback, SDD/epic behavior, status
updates, and runner continuation.

### Phase 6: normalize consumers

Teach pending-action state, ACE, Rust mobile, attachments, and Telegram to resolve common request pointers and generic
filenames. During the transition, fall back to legacy action-specific paths so pending requests created by an older
process remain usable.

### Phase 7: optionally collapse action variants

Only after every consumer reads the common envelope should the project consider replacing the three action names with a
generic action and declarative renderer/choice schema. Version Rust/mobile wires and coordinate the Telegram plugin in
the same rollout. This phase is optional; distinct typed action variants can coexist with a common constructor.

## 9. Generated skills and CLI compatibility

If the agent-facing invocation changes, update the source templates under `src/sase/xprompts/skills/`:

- `/sase_plan` currently documents `sase plan propose`;
- `/sase_questions` currently documents `sase questions`;
- `/sase_run` currently documents `sase launch request` and launch-specific polling.

Do not edit deployed generated skills directly. After source changes, the repository procedure requires regenerating
with `sase skill init --force` and deploying through the managed configuration flow.

The compatibility commands can remain thin aliases for at least one release. That avoids breaking existing skills,
scripts, or older agents while allowing new generated skills to converge on `sase notify create`.

## 10. Risks and design traps

### 10.1 Treating all interactions as synchronously equivalent

Plan and question are runner handoffs; launch is async. A shared path must preserve this difference visibly.

### 10.2 Moving privileged policy into user-provided JSON

Do not let a payload declare arbitrary Python handlers, response paths, or side effects. `kind` should select a
registered host adapter. The request may describe choices, but the adapter owns what those choices are allowed to do.

### 10.3 Breaking active requests during deployment

Old processes may be waiting on `plan_response.json` or `question_response.json` while a new ACE/mobile process is
installed. Consumers need legacy fallback, or the rollout must explicitly declare that pending requests are discarded.

### 10.4 Hiding plan semantics in a generic response schema

Plan approve/run/tale/epic/commit/feedback choices encode SDD and launch policy. A generic form renderer can display
them, but it should not replace the typed plan choice registry or its validation with arbitrary strings.

### 10.5 Preview/request time-of-check versus time-of-use

Launch already replans at dispatch, but the reviewed request files are mutable. A common bundle should record hashes or
another immutable snapshot contract so transports can show what will actually execute.

### 10.6 Inconsistent stale policy

Pending actions currently use a fixed 24-hour deadline while runners may still be waiting on response files. The common
envelope should define whether expiry is advisory to remote transports, terminal for the producer, or configurable per
kind.

### 10.7 Assuming custom-role removal means family removal

Many tests and UI paths use custom-looking suffixes for generic manual family members. Delete lifecycle-specific
behavior, not every occurrence of `tester`, `reviewer`, custom role strings, or `agent_family_role`.

### 10.8 Expanding the first milestone to all HITL

HITL already resembles the same bundle, and eventually belongs in the common model. Including it in the schema design
is prudent; migrating it in the same first change is optional and may obscure the plan/question/launch objective.

## 11. Validation matrix

The implementation should verify more than successful row creation.

### 11.1 Common constructor and CLI

- strict validation for object/list/string fields and unknown kinds;
- id, timestamp, tag normalization, and context capture;
- stable text and JSON output;
- request directory permissions and path confinement;
- partial-failure cleanup for request, notification, and pending-action writes;
- concurrent creates and notification-prefix uniqueness behavior;
- raw non-action notification compatibility;
- excellent `--help` and documented short aliases.

### 11.2 Per-kind contracts

- plan validation, archive behavior, every approval choice, feedback, auto modes, SDD/epic ownership, and coder handoff;
- single/multiple/multi-select questions, custom answers, runner-slot reacquisition, dismissed-notification marker
  fallback, and Q&A prompt reconstruction;
- launch fanout/max-slots, preview fidelity, approval/rejection/feedback, cwd validation, replan at dispatch, partial
  launch rollback, and requester polling.

### 11.3 Cross-surface compatibility

- ACE modal dispatch, status overrides, unread/dismiss behavior, toasts, and attachments;
- CLI plan/launch selectors and response executors;
- Rust pending-action state and mobile detail/action wires;
- Telegram formatters, keyboards, callbacks, handled-state cleanup, and request attachments;
- old request filenames/action names during the compatibility window;
- mixed-version scenario: old producer/new consumer and new producer/old consumer, if supported.

### 11.4 Lifecycle-role removal

- `kind: agent_family` gives the chosen deprecation/error behavior;
- no member options or defaults appear in plan request/response/UI/CLI;
- standard plan feedback, question continuation, coder handoff, and manual `%n` attachment still work;
- generic custom family suffixes still render and group correctly;
- historical artifacts either retain read-only custom labels or degrade cleanly to generic RUNNING/DONE;
- no dead default config/schema/docs remain.

## 12. Principal files and repositories involved

This is not an exhaustive edit list, but it identifies the implementation seams.

### Main `sase` repository

- Notification creation/storage: `src/sase/notifications/models.py`, `senders.py`, `store.py`, `pending_actions.py`
- Generic CLI: `src/sase/main/notify_handler.py`, `parser_commands.py`
- Plan producer/response: `src/sase/main/plan_propose_handler.py`, `src/sase/llm_provider/_plan_utils.py`,
  `src/sase/plan_approval_actions.py`, plan CLI/modal files, runner plan files
- Question producer/response: `src/sase/main/questions_command_handler.py`, runner question helpers, ACE question modal,
  mobile question action
- Launch producer/response: `src/sase/agent/launch_request.py`, `launch_preview.py`,
  `src/sase/launch_approval_actions.py`, launch CLI/modal files
- Dynamic lifecycle roles: `src/sase/agent_family/custom_definitions/`, standard evaluator custom-role branches,
  `src/sase/axe/run_agent_exec_custom_roles.py`, member selection/config/UI/catalog files
- Generated skill sources: `src/sase/xprompts/skills/sase_plan.md`, `sase_questions.md`, `sase_run.md`
- Documentation and focused/golden/visual tests across notifications, plans, launch approval, agent families, mobile, and
  ACE

### `sase-core`

- `crates/sase_core/src/notifications/wire.rs`
- `crates/sase_core/src/notifications/pending_actions.rs`
- `crates/sase_core/src/notifications/mobile.rs`
- Python binding/wire adapters in the main repository

### `sase-telegram`

- notification formatting and action keyboards;
- inbound callback routing and response execution;
- outbound pending-action persistence and attachments;
- plan/question/launch integration and formatting tests.

## Questions that must be answered before confident design and implementation

1. When you say all three should use the “same structure,” do you mean one common request-directory/envelope and
   constructor while retaining typed plan/question/launch actions, or do you want one generic notification action and
   one declarative response protocol across ACE, mobile, and Telegram?

2. Should `sase notify create` become the agent-facing command for plan, question, and launch immediately, with `sase
plan propose`, `sase questions`, and `sase launch request` retained as compatibility aliases, or should those commands
   remain the public domain-specific front doors while sharing the constructor internally?

3. Should internal SASE Python call a shared in-process notification service (recommended), or do you specifically want
   internal producers to invoke the `sase notify create` executable as a subprocess?

4. Should the common envelope standardize only creation and response-file plumbing, or should it also own continuation
   behavior such as terminating the current model subprocess, pausing/reacquiring runner slots, reconstructing prompts,
   and asynchronous polling?

5. Is the intended common directory/file layout a new neutral form such as
   `interaction_requests/<kind>/<id>/{request,response,preview}`, and must requests created under the legacy plan,
   question, and launch paths remain actionable after upgrade?

6. Do you want to remove the entire `kind: agent_family` custom lifecycle-role subsystem—including arbitrary user-defined
   roles, plan member toggles, sticky defaults, role snapshots, visit caps, and custom status labels—or only delete the
   bundled `improve_plan`/`tester` examples and prompt templates?

7. Confirm that manual `%n(parent, suffix)` family attachment, arbitrary generic suffixes such as `tester`, and
   agent-initiated family launches through `LaunchApproval` should remain.

8. After lifecycle-role removal, should the now-standard-only `role_completed` evaluator event and custom-role metadata
   readers be deleted completely, or retained as a compatibility/future-controller seam for historical artifacts and
   the broader run-group initiative?

9. Should HITL be included in the new interaction envelope and adapter registry now, even if its producer is migrated
   later, or is the schema intentionally limited to plan/question/launch?

10. Should plan-specific choices and side effects remain a typed host-owned adapter (recommended), or is part of the
    goal to make choices, validation, and response effects declarative in the notification request itself?

11. What should each kind's continuation policy be under the new command: preserve plan/question runner handoff and
    launch async polling exactly, or move toward a single blocking/waiting behavior visible to the requesting agent?

12. What are the required auto policies: preserve plan auto-approve, first-option question auto-answer, and mandatory
    launch approval, or should auto behavior also become a common configurable field?

13. Is a successful create required to guarantee that the request bundle, notification row, and pending-action record
    are all durable, and if one write fails should the constructor roll back the other files or return a recoverable
    partial result?

14. Should actionable request files be confined to a SASE-owned directory and protected by content hashes or immutable
    snapshots so an approved plan/launch cannot differ from its preview?

15. Do you want the first implementation to preserve the current Rust/mobile/Telegram wire variants for compatibility,
    or should the same initiative version and migrate `sase-core` and `sase-telegram` to a generic interaction action?

16. How long must mixed-version compatibility last—for example, an old agent waiting on a legacy response while a new
    ACE/Telegram process handles it—and is it acceptable to require clearing all pending actions during upgrade?

17. Should raw `sase notify create` remain able to create arbitrary action strings, or should privileged/actionable
    notifications be restricted to registered kinds while raw mode is limited to non-action inbox rows?

18. What structured output must `sase notify create --output json` guarantee to generated skills: notification id only,
    or request id plus request/response/preview paths and continuation mode?
