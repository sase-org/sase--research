---
create_time: 2026-07-16
updated_time: 2026-07-16
status: research
---

# Unifying Plan / Question / Launch Notifications Behind One Constructor

## Scope

Bryan's ask: *"generalize the concept of plan / question / launch notifications so all of them use the
same structure and sase notification constructor. We should use the existing `sase notify create`
command for this, which will need to be significantly enhanced. As a part of this change, I intend to
remove the (never used) dynamic `improve_plan` and `tester` family member hooks."*

This report establishes what exists today, corrects three premises in the ask, identifies the real
seam for generalization, enumerates the constraints (most of them in Rust), and ends with the
questions that must be answered before design.

Evidence is first-hand: every claim below carries a `file:line` reference and the load-bearing ones
were re-verified directly rather than taken from a summary.

---

## Three Premise Corrections (read this first)

### 1. There are no hooks. The word is stale.

Nothing in the plan or question flow is a hook. Both are a **marker file + SIGTERM self-kill**:

1. The skill runs a CLI command (`sase plan propose <file>` / `sase questions '<json>'`).
2. The handler writes a marker (`.sase_plan_pending` at `plan_propose_handler.py:90`;
   `.sase_questions_pending` at `questions_command_handler.py:81`) and fsyncs it.
3. It calls `kill_agent_runner_group(artifacts_dir)` — SIGTERMs the runner's own process group.
4. The runner wakes at `run_agent_exec.py:154`, reads and deletes the marker, and dispatches a
   typed event (`kind="plan_submitted"` at `:163`, `kind="questions_submitted"` at `:171`).

Launch is different again: no marker, no SIGTERM, no runner involvement — just a CLI call
(`launch_request.py:109`).

The provider-native tools are disabled and replaced by skills (`claude.py:89`,
`sase_questions.md:8`), so "via hook" in the `notify_user_question` docstring (`senders.py:205`) is
simply wrong and should be corrected in passing.

### 2. `improve_plan` and `tester` are inactive *examples* of a feature that was fully built.

They are two YAML files in `src/sase/xprompts/examples/agent_families/` plus two prompt bodies
(`agent_family_improve_plan.md`, `agent_family_tester.md`). They are inactive because discovery uses
a **non-recursive** `directory.glob(pattern)` (`discovery.py:106`) that never descends into
`examples/`; the docstring at `discovery.py:36` states this is deliberate — *"Bundled example
definitions live under `xprompts/examples` and are intentionally not active."*

**No Python code branches on either id.** They are pure data. The two ids appear in source only as
incidental strings: a CLI epilog example (`parser_plan.py:56`), a skill doc example
(`sase_run.md:96`), and a Rust-binding probe fixture (`tools/validate_sase_core_rs:163`).

Critically, the machinery they exemplify is **not** aspirational. `plan_approval_choices.py:1-4`
describes itself as *"the approval-gate vocabulary source of truth"*, and the custom-role evaluator
(`standard_plan_chain_evaluator.py:112-152`), role spawning
(`run_agent_exec_custom_roles.py:45-134`), `--with`/`--without` CLI flags
(`plan_approve_handler.py:130-184`), and the `ApproveOptionsModal` "Also run:" toggles
(`approve_options_modal.py:189-196`) all ship today.

This matters because the 2026-07-05 research doc (`dynamic_agent_families_v1_v2_design.md:193-341`)
describes all of this as unbuilt "v2 direction". **That doc is now out of date.** Its stage 2
("collapse the four hard-coded choice tables into one data-driven choice registry") and stage 4
("custom roles as data") have landed. Anyone starting from that doc will misjudge the work.

### 3. `sase notify create` is already half-way there — but it rings a doorbell, not opens a gate.

`append_notification` (`store.py:113-123`) already calls `pending_actions.register_notification(n)`
internally. So a notification minted today via `sase notify create` with
`action="PlanApproval"` and a `response_dir` in `action_data` **already lands in the pending-action
store and already renders as actionable on mobile**. The capability gap is narrower than it looks.

What is missing is not the notification — it is everything *around* it. See the next section.

---

## The Real Structure: These Are Gates, Not Notifications

The unifying abstraction is not "a notification". All four actionable kinds
(`PlanApproval`, `UserQuestion`, `LaunchApproval`, `HITL`) are instances of a **request/response
gate**, of which the notification is merely the doorbell:

```
gate := (
    response_dir,            # the conversation directory
    <kind>_request.json,     # producer  -> approver   (payload, choices, context)
    <kind>_response.json,    # approver  -> producer   (decision, feedback)
    notification,            # the doorbell (action + action_data{response_dir} + files)
    poller,                  # producer blocks until the response file appears
)
```

`pending_actions.py:308-345` proves the regularity — it hard-codes the identical predicate four
times, varying only the filenames:

| Kind | dir key | request file | response file | extra signal |
|---|---|---|---|---|
| `PlanApproval` | `response_dir` | `plan_request.json` | `plan_response.json` | `plan_approved.marker` |
| `UserQuestion` | `response_dir` | `question_request.json` | `question_response.json` | — |
| `LaunchApproval` | `response_dir` | `launch_request.json` | `launch_response.json` | `launch_preview.md` |
| `HITL` | `artifacts_dir` | `hitl_request.json` | `hitl_response.json` | — |

**This is the seam.** "Significantly enhanced `sase notify create`" should mean: it stops being
*"append a row to notifications.jsonl"* and becomes *"open a gate"* — create `response_dir`, write
`<kind>_request.json`, append the notification, register the pending action, and print the
`response_file` path for the caller to poll. Every current producer then collapses to one call plus
a poll.

The duplication this would retire is real: **17 files** currently branch on the four action string
literals.

```
14  src/sase/ace/tui/actions/agents/_notification_modal_flow.py
11  src/sase/notifications/pending_actions.py
 8  src/sase/ace/tui/actions/agents/_toasts.py
 4  src/sase/notifications/senders.py
 4  src/sase/integrations/_mobile_notification_actions.py
 4  src/sase/ace/tui/modals/notification_modal_constants.py
 4  src/sase/ace/tui/actions/agents/_notification_status_overrides.py
 ... 10 more
```

Plus `question_summary.py:60-71`, which independently re-implements the same filesystem state rules
that `pending_actions.py` already owns.

---

## What Resists Unification

Three things are genuinely not the same shape. A design that ignores them will produce a leaky
abstraction.

### A. Launch is inverted, and its loop is not closed

For plan and question, the approver **unblocks a waiting producer**. For launch, the approver
**performs the work**: `dispatch_approved_launch_request` (`launch_request.py:128`) `os.chdir`s and
calls `launch_agents_from_cwd`.

Worse — and verified directly — **nothing in the codebase polls `launch_response.json`**. The only
non-test references are the constant (`launch_preview.py:24`), the writer
(`launch_approval_actions.py`), an existence check (`pending_actions.py:341`), and one line of
**prose in a skill** (`sase_run.md:100`: *"Poll that path until `launch_response.json` appears."*).
Rejection is enforced by `sase_run.md:114` (*"If rejected, do not spawn anyway"*) — an honor system,
not a mechanism.

So launch is a "gate + host-side execution with an LLM-honour-system poller". Unifying it with plan
and question means deciding whether that inversion is *part of* the abstraction or an exception to it.

Relatedly, `sase run` outside an agent bypasses approval entirely (`_launch.py:47` gates only on
`bool(os.environ.get("SASE_AGENT"))`).

### B. The plan gate has a member-options bulge

`plan_request.json` is the only request that carries extra structure:
`plan_approval_member_request_payload()` (`plan_approval_choices.py:332-348`) injects
`member_options` and `default_member_ids`, and `senders.py:274-280` turns the latter into a second
notes line (`"Also run: improve_plan, tester"`) — the only way remote approvers (Telegram/mobile),
which have no toggles, learn that members will run.

**This is the only place the custom-roles feature touches the notification system**, and it is why
Bryan's instinct that "we will need to do something about them" is directionally right — though the
thing to do is about *member options*, not about the two example files (see below).

### C. The choice vocabulary is closed, in Rust

`PlanActionChoiceWire{Approve,Run,Reject,Epic,Feedback}`, `QuestionActionChoiceWire{Answer,Custom}`,
`LaunchActionChoiceWire{Approve,Reject,Feedback}`, `HitlActionChoiceWire{Accept,Reject,Feedback}`
(`mobile.rs:178-263`) are closed enums, **hardcoded and always emitted regardless of payload**
(`mobile.rs:424-430`). Data-driven per-gate choices therefore cross the Rust wire.

---

## The Rust Boundary: Five Hard Constraints

`NotificationWire` (`wire.rs:8-32`) mirrors the Python dataclass field-for-field. The constraints
that bound any design:

1. **`action_data` is `BTreeMap<String, String>`.** Flat, string-valued, no nesting, no ints.
   `slot_count`/`question_count` are stringified and parsed back with a silent `.unwrap_or(0)`
   (`mobile.rs:455`, `:470`) — a malformed value degrades to `0` rather than erroring. Non-string
   values raise `PyValueError` at the PyO3 chokepoint (`sase_core_py/src/lib.rs:2863`).
   *Good news:* the existing design already respects this by keeping rich payloads in
   `<kind>_request.json`. A unified constructor must keep doing so.

2. **`action` is an open `Option<String>` — but unknown values fail silently, in three independent
   places.** `mobile.rs:724-733` maps unknown → `Unsupported` (non-actionable);
   `pending_actions.py:26-32` returns `None` (no pending entry); `priority.py:11` won't classify it.
   A typo'd action produces a notification that looks fine and quietly does nothing.

3. **Priority and error classification are hardcoded `(action, sender)` functions in Rust.**
   Verified at `mobile.rs:400-411`:
   ```rust
   matches!(notification.action.as_deref(),
       Some("PlanApproval" | "UserQuestion" | "JumpToMentorReview") | Some("LaunchApproval"))
       || matches!(notification.sender.as_str(), "axe" | "crs")
   ```
   **This is the single most important constraint.** A naive "one generic action string" design —
   e.g. collapsing everything to `action="Gate"` — would *silently* drop plan/question/launch out of
   the priority badge counts (`store.rs:611-628`) and make them non-actionable on mobile. It is not
   expressible via `tags`, which Rust never inspects.

4. **No field may be added Python-side only.** There is no `deny_unknown_fields` *and* no
   flatten-catch-all, so an unknown field deserializes without error and is then **permanently
   dropped** on the next `rewrite_notifications` / `apply_notification_state_update`
   (`store.rs:506-520`). Adding a field Python-first means marking a notification read from the TUI
   silently destroys it. Rust first, always.

5. **`NotificationWire` has no `schema_version` field.** Versions exist only on envelope types
   (`wire.rs:54-73`), are stamped on output and never validated on input. Every JSONL row on disk is
   unversioned. Compat today is implicit: `#[serde(default)]` everywhere, unknown-action fallback,
   and bad rows counted-and-skipped.

**Lowest-risk conclusion:** generalize the *structure and construction path*, but keep the four
action literals as the type tag. Unify the plumbing, not the vocabulary. That keeps all 28 parity
tests and 2 golden fixtures green with zero Rust change.

---

## The `improve_plan` / `tester` Removal: Three Separable Layers

The ask treats these as one thing. They are three, and only one touches notifications:

| Layer | What | Active? | Touches notifications? | Removal cost |
|---|---|---|---|---|
| **L1** | `improve_plan.yml`, `tester.yml` + 2 prompt bodies | No (glob never descends) | No | ~Free |
| **L2** | Custom-role machinery: discovery, validation, evaluator, spawn | Yes, generic over role ids | No | Large feature deletion |
| **L3** | Plan-gate member options: `member_options`/`default_member_ids`, "Also run:" note, `--with`/`--without`, modal toggles | Yes, plan-specific | **Yes** | Moderate |

**Deleting L1 alone is nearly free — and unblocks nothing.** The two YAML files are unreferenced by
any test (all tests define their own inline YAML). The only functional breakage is
`tests/test_agent_family_custom_definitions.py:148-181`, which validates prompt refs against the
xprompt catalog and would fail if `agent_family_tester.md` disappears. Everything else is mechanical
renames plus **PNG snapshot regeneration** (`tests/ace/tui/visual/test_ace_png_snapshots_agents.py:252-285`
bakes the labels `IMPROVING PLAN`/`TESTING` into committed images) and golden JSON
(`tests/plan_chain_golden/`).

**L3 is what actually de-bulges the plan gate** and makes it the same shape as question/launch.

**Removing L3 does not remove L2.** `filter_roles_by_selected_member_ids` treats `None` as "no
filtering" (`plan_approval_choices.py:461-475`), so custom roles would still run — just without
gate-time selection. They would fall back to their own `default_enabled` and config
(`agent_family.plan_approval.default_members`, `sase.schema.json:168-188`).

Note the side effect of L1 removal: `docs/agent_families.md:129-131` positions the examples as the
onboarding path (*"Copy the `.yml` file into an active xprompts directory to enable it"*). Deleting
them leaves a shipped feature with **no shipped examples**.

---

## Latent Bugs and Debt the Refactor Should Absorb

Found while tracing; each is independent of the refactor but sits directly in its path.

1. **TUI-answered questions are never marked handled.** `_notification_modal_responses.py:36`
   early-returns unless `action_kind == "plan_approval"`, so a `UserQuestion` resolved from the TUI
   never gets `mark_already_handled` — its pending entry stays `available` until re-derived from the
   filesystem. Launch avoids this by calling it itself (`launch_approval_actions.py:119`).
   *Verified directly.*
2. **`LaunchApproval` is missing from agent-dismissal in Rust.** `store.rs:677` matches
   `Some("PlanApproval" | "UserQuestion")` only — launch notifications are not dismissed when their
   agent is killed. *Verified directly.* Likely a bug; confirm rather than assume.
3. **Nothing polls `launch_response.json`** (above). An approved launch dispatches host-side even if
   the requesting agent has died and will never learn of it.
4. **`silent` is unreachable from the CLI.** `notify_handler.py:59-68` never reads it from stdin
   JSON, despite it being a first-class field the mobile bridge filters on
   (`_mobile_notification_snapshot.py:36-37`).
5. **Duplicate string→enum ladders in Rust**: `mobile_action_kind` (`mobile.rs:724`) and
   `action_kind_from_str` (`pending_actions.rs:438`) must stay in sync by hand.
6. **`question_summary.py:60-71`** re-implements `pending_actions.py`'s filesystem rules.
7. **Doc/comment drift**: "via hook" (`senders.py:205`); the stale comment at
   `_notification_modal_flow.py:154` naming only PlanApproval/UserQuestion while the code list
   includes LaunchApproval; `sase_notify.md:18-20` omits `tags` from the documented row shape.

---

## Recommended Direction (for discussion, not decided)

1. **Do not change the wire.** Keep the four action literals as the type tag. Constraint 3 makes any
   vocabulary collapse silently destructive.
2. **Introduce a gate abstraction in Python** — one constructor that owns: `response_dir` creation,
   `<kind>_request.json` write, notification append, pending-action registration, and returning the
   response path. Name the request/response files from the kind rather than the current bare string
   literals (only launch has constants today: `launch_preview.py:22-24`).
3. **Make `sase notify create` the CLI face of that constructor**, not a second path. The senders are
   in-process Python; having them shell out to their own CLI would be slow and circular — especially
   on the plan path, which is latency-sensitive and must then poll. The CLI and the in-process
   senders should share one builder.
4. **Fold the four `_externally_handled` branches into gate metadata** — this is pure win and
   independently shippable.
5. **Decide launch's status explicitly** (part of the abstraction, or an acknowledged exception)
   before writing code.
6. **Sequence L3 (member options) removal first if it is happening at all** — it is the only
   notification-facing part of the family work, and doing it after the gate refactor means touching
   the plan request payload twice.

---

## Questions

Answering these would let me design and implement this confidently.

### On intent and scope

1. **What does "use `sase notify create`" mean operationally** — (a) all producers shell out to the
   CLI as a subprocess, (b) the CLI and in-process senders share one Python constructor, or (c) the
   CLI becomes the only *public/agent-facing* way to create gates while internals use the shared
   builder? My read is (b), but this changes the whole design.
2. **Is the target abstraction "a notification" or "a gate"?** I argue the useful unit is the
   request/response gate (dir + request + response + doorbell + poller), and that generalizing only
   the notification row leaves the actual duplication untouched. Do you agree?
3. **Should `HITL` be in scope?** It is the fourth instance of the identical pattern (differing only
   in using `artifacts_dir` instead of `response_dir`). Including it makes the abstraction honest;
   excluding it leaves a fourth copy of the logic.
4. **Are the `memory_review`, `JumpToChangeSpec`, `JumpToMentorReview`, `ViewErrorReport` senders in
   scope**, or does "same structure" apply only to the three blocking gates? Note `memory_review` is
   registered as a pending action (`pending_actions.py:31`) but is unknown to Rust entirely.

### On the improve_plan / tester removal

5. **Which layer do you actually want removed — L1, L3, or L2+L3?** Given they're inactive examples
   of a built feature, deleting L1 costs almost nothing but also unblocks nothing. My read is that
   L3 (member options) is what you actually need gone to make the plan gate uniform. Confirm?
6. **If L3 goes, what happens to the custom-roles feature?** It keeps working via config defaults
   (`agent_family.plan_approval.default_members`) but loses gate-time selection, `--with`/`--without`,
   and the modal toggles. Is that the intent, or should L2 go too?
7. **If L1 goes, do we ship replacement examples?** `docs/agent_families.md:129-131` makes them the
   documented onboarding path.
8. **Are you willing to regenerate the PNG visual snapshots and plan-chain goldens?** Any removal
   touching the labels `IMPROVING PLAN`/`TESTING` requires it.

### On the gate design

9. **Does `sase notify create` become responsible for writing `<kind>_request.json` and creating
   `response_dir`?** That is what "significantly enhanced" implies to me, and it is the difference
   between a doorbell and a gate. If yes — does it print the response path (JSON) for the caller to
   poll?
10. **Is there one generic poller?** Plan polls with a shared `_POLL_INTERVAL = 0.5`
    (`_plan_utils.py:21`) and re-checks auto-approve mid-loop (`:392`); question hardcodes
    `time.sleep(0.5)` (`run_agent_helpers_questions.py:146`); launch has no poller at all. Should the
    constructor ship a `wait_for_response()` too?
11. **How uniform must `response_dir` be?** Plan is sharded (`plan_approval/YYYYMM/<uuid>/`),
    question is flat (`user_question/<uuid>/`), launch is keyed by request id
    (`launch_requests/<id>/`). Unify on sharding, or leave as a per-kind detail?
12. **Do gate choices become data-driven?** If yes, that crosses the Rust wire (`mobile.rs:178-263`
    are closed enums always emitted in full) and needs wire versioning. If no, each new gate kind
    still requires a coordinated Rust change.
13. **What is the launch inversion's status** — is "the approver performs the work" part of the
    abstraction, or is launch an acknowledged exception? And should this change close its loop (make
    something actually poll `launch_response.json`) or keep the honour system?

### On compatibility and rollout

14. **Is a `NotificationWire` change acceptable at all?** Staying wire-identical keeps 28 parity
    tests + 2 golden fixtures green and needs no `sase-core` release. If we need a row-level
    `schema_version` or a structured payload field, that is a Rust-first change with a release
    dependency. Which side of that line are we on?
15. **Do in-flight gates need to survive the refactor?** Notifications on disk are unversioned; a
    live `plan_request.json` written by the old code must still be answerable by the new code (or we
    accept a drain window).
16. **Should the latent bugs (§Latent Bugs 1-3) be fixed in this change or split out?** #2 is a Rust
    fix in a different repo; #3 is a design question about launch, not a small fix.
17. **Is `sase notify create` meant to become agent-facing?** `sase_notify.md:9-10` is emphatically
    read-only today (*"do not dismiss, mute, snooze, mark read, or otherwise mutate"*). If agents
    should open gates, that skill and its contract change materially — and per
    `memory/generated_skills.md:18-24`, CLI arg changes require same-turn skill + test updates.

---

## Key References

- **Gate predicates (the duplication)**: `src/sase/notifications/pending_actions.py:308-345`
- **Constructors**: `src/sase/notifications/senders.py:196` (question), `:231` (plan), `:296` (launch)
- **CLI**: `src/sase/main/notify_handler.py:37-72`, `src/sase/main/parser_commands.py:197-302`
- **Producers/pollers**: `src/sase/llm_provider/_plan_utils.py:196-400`,
  `src/sase/axe/run_agent_helpers_questions.py:40-148`, `src/sase/agent/launch_request.py:73-128`
- **Marker/SIGTERM triggers**: `src/sase/main/plan_propose_handler.py:90`,
  `src/sase/main/questions_command_handler.py:81`, `src/sase/axe/run_agent_exec.py:154-171`
- **Rust wire**: `crates/sase_core/src/notifications/wire.rs:8-32`,
  `mobile.rs:393-411` (priority/error), `mobile.rs:724-733` (action kind), `store.rs:506-520` (rewrite merge),
  `store.rs:611-628` (counts), `store.rs:677` (dismissal gap)
- **Family/member options**: `src/sase/plan_approval_choices.py`,
  `src/sase/agent_family/custom_definitions/discovery.py:106` (why examples are inactive)
- **Rules**: `memory/cli_rules.md` (short aliases, alphabetical, bare-`list` default),
  `memory/generated_skills.md:18-24` (CLI/skill contract sync)
- **Superseded**: `202607/dynamic_agent_families_v1_v2_design.md:193-341` — describes as "v2
  direction" work that has since shipped. Do not start from it.
