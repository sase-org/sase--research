---
create_time: 2026-07-16
updated_time: 2026-07-16
status: research
---

# Unifying Plan / Question / Launch Notifications Behind One Constructor (Consolidated)

**Sources:** two independent research reports — `__a` (codex, `research.e.cdx`) and `__b`
(claude, `research.e.cld`) — merged by a third lead-researcher pass that re-verified every
load-bearing and disputed claim first-hand in both `sase` and `sase-core`. Claims below marked
*(verified)* were confirmed directly during consolidation.

**The ask:** generalize plan / question / launch notifications so all use the same structure and one
sase notification constructor, enhance `sase notify create` to be that constructor, and remove the
never-used dynamic `improve_plan` / `tester` family member hooks.

---

## Executive summary

The three flows already share the lowest layer — a `Notification` row appended through the Rust
store, which also registers a pending action — but everything above that diverges: each producer
independently builds its request directory, request/response files, notification fields, response
schema, continuation behavior, and per-surface (ACE / mobile / Telegram) handling. **The useful
unit to generalize is not the notification row but the request/response gate**: a response
directory holding `<kind>_request.json` and `<kind>_response.json`, with the notification as the
doorbell and a pending-action record for remote transports. Seventeen files currently branch on the
four action string literals; `pending_actions.py:308-345` hard-codes the same handled-state
predicate four times varying only filenames *(verified)*.

`sase notify create` today is a raw row writer (stdin JSON + `--sender`/`--tag`, prints only the
id). It is closer to useful than it looks — because `append_notification()` registers pending
actions internally, the CLI can already mint an actionable `PlanApproval` row *(verified,
`store.py:113-123`)* — but it creates no request directory, no request file, validates nothing,
captures no producer context, and prints no response path. "Significantly enhanced" should mean it
stops appending a row and starts **opening a gate**.

Three corrections to the ask's premises (all verified):

1. **There are no hooks.** Plan and question work by writing a marker file
   (`.sase_plan_pending` / `.sase_questions_pending`) and SIGTERM-ing the runner's own process
   group; the runner wakes, converts the marker to a typed handoff event, and creates the
   notification. Launch is a plain CLI call with no runner involvement. The "via hook" docstring at
   `senders.py:205` is stale.
2. **`improve_plan` and `tester` are inactive example files for a feature that shipped.** They are
   two YAML files under `src/sase/xprompts/examples/agent_families/`, kept inactive by a
   deliberately non-recursive glob (`custom_definitions/discovery.py:106`). The machinery they
   exemplify (discovery, evaluator, `--with`/`--without`, modal toggles) is fully built and active
   — but parts of its semantics are dead code, which strengthens the removal case (§4).
3. **The hard constraints live in Rust.** Action names, priority classification, and the
   flat-string `action_data` map are public wire contracts in `sase-core`, consumed by mobile and
   `sase-telegram`. A naive "one generic action" design silently breaks badge counts and mobile
   actionability.

**Consensus recommendation from both reports:** unify the *plumbing* (one gate
constructor/service, shared by the CLI and in-process senders), keep the four action literals
(`PlanApproval`, `UserQuestion`, `LaunchApproval`, `HITL`) as the type tag, and defer any
wire/protocol collapse to an optional later phase. On the family hooks, the removal decision is
really a choice between three separable layers (§4), and the layer that actually blocks this
initiative is the plan gate's *member-options* bulge, not the two example files.

---

## 1. How the three flows work today

| Concern | Plan | Question | Launch |
|---|---|---|---|
| Agent-facing command | `sase plan propose <file>` | `sase questions '<json>'` | `sase launch request …` |
| Trigger mechanics | Marker `.sase_plan_pending` + SIGTERM runner group (`plan_propose_handler.py:90,117`) | Marker `.sase_questions_pending` + SIGTERM (`questions_command_handler.py:81,95`) | Direct CLI; requester keeps running (`launch_request.py`) |
| Notification created by | Runner, after `plan_submitted` event → `handle_plan_approval()` | Runner, after `questions_submitted` event | The request command itself |
| Request dir | Sharded `plan_approval/<shard>/<session>` (`_plan_utils.py:242`, `sharded_path`) | Flat `user_question/<uuid>` | `launch_requests/<request_id>` |
| Request artifacts | `plan_request.json` (+ plan file as attachment, in `files[0]`) | `question_request.json` (+ `pending_question.json` ACE fallback marker) | `launch_request.json`, `launch_preview.md` |
| Response artifact | `plan_response.json` (+ `plan_approved.marker`) | `question_response.json` | `launch_response.json` |
| Action literal | `PlanApproval` | `UserQuestion` | `LaunchApproval` |
| Continuation | Runner blocks polling (0.5s), then feedback/code/epic transition | Runner blocks, reacquires slot, rebuilds prompt, continues in role | Async: requester told (in skill prose) to poll; approval dispatches a new detached launch |
| Auto behavior | Auto-approve modes can bypass the gate | First-option auto-answer can bypass | Agent-initiated requests always require approval |
| Preflight | Plan tier validation, format/archive, member-option snapshot | Question schema validation | Xprompt expansion, fanout planning, max-slot check, preview |
| Response side effects | Archive/metadata, SDD actions, coder/epic handoff, status | Q&A history, prompt reconstruction | Revalidate cwd/request, dispatch launch, write `dispatch_status` |

What is already shared *(verified)*: all three instantiate `Notification`
(`senders.py:196/231/296`), call `append_notification()` (which best-effort registers the pending
action, swallowing failures with a warning), use `action` + string-valued `action_data` with a
`response_dir` pointer, use write-once response files, and dismiss after response. The sharing
begins only *after* request construction has already diverged.

**HITL is a fourth instance of the identical pattern**, differing only in keying off
`artifacts_dir` instead of `response_dir` — relevant to whether the abstraction includes it.

### Launch is inverted, and its loop is not closed *(verified)*

For plan/question the approver *unblocks a waiting producer*; for launch the approver *performs the
work* (`dispatch_approved_launch_request` chdirs and launches). And **nothing in the codebase polls
`launch_response.json`** — the only non-test references are the constant (`launch_preview.py:24`),
the writer, a pending-action existence check (`pending_actions.py:341`), and one line of prose in
`sase_run.md:100` telling the LLM to poll. Rejection enforcement ("do not spawn anyway",
`sase_run.md`) is an honor system. Also, `sase run` outside an agent bypasses approval entirely —
the gate is `running_agent_context_requires_launch_approval()` = `bool(os.environ.get("SASE_AGENT"))`
(`launch_request.py:187`, called from `main/query_handler/_launch.py:47`).

Any unification must decide whether this inversion is part of the abstraction or an acknowledged
exception — and whether to close the polling loop mechanically.

---

## 2. What `sase notify create` is and lacks

Current implementation (`main/notify_handler.py:37-72`, parser at `parser_commands.py:197-240`):
reads unversioned JSON from stdin (`sender`, `notes`, `files`, `tags`, `action`, `action_data`),
lets `--sender`/`--tag` override/extend, generates id + timestamp, appends, prints the id. Bare
`sase notify` defaults to `list`.

Gaps that matter for this initiative:

- **No input schema/versioning or validation** — no object-shape checks, no action registry, no
  `action_data` string coercion; a typo'd action produces a row that looks fine and silently does
  nothing (see §3, constraint 2). `silent` (and `read`/`muted`/…) are unreachable from stdin JSON
  *(verified)* even though the mobile bridge filters on `silent`.
- **No request bundle construction** — no response dir, no `<kind>_request.json`; an actionable
  notification made through it only works if the caller hand-builds the private per-kind file
  conventions.
- **No producer context capture** — plan/question senders each copy `SASE_AGENT_CL_NAME`,
  timestamps, project file, model/provider/runtime/VCS fields from the environment independently.
- **No continuation policy** — plan/question hand control to the runner; launch is async. The
  constructor needs an explicit (or kind-intrinsic) delivery mode so callers know whether the
  current session survives.
- **No preflight or privileged response executor** — plan tier validation, launch preview/slots,
  question schema, and response side effects belong in kind adapters, not an `if action == …`
  ladder in the CLI handler.
- **Weak output contract** — prints the notification id only; a gate-opening command must emit
  stable JSON with request id, request/response/preview paths, and continuation mode for the caller
  to poll.
- **Non-atomic multi-store writes** — row append then best-effort pending-action registration;
  adding request-dir creation makes a third orphanable unit. A declared failure/cleanup policy is
  needed (full transactionality probably isn't).
- **Privilege/provenance** — today anyone can mint a `PlanApproval`/`LaunchApproval` row pointing
  at handcrafted files, and approval paths dispatch agents and archive plans. A generic
  constructor should confine request files to SASE-owned paths, validate kind↔filename agreement,
  and consider content hashes so a reviewed preview cannot be silently replaced (launch already
  revalidates at dispatch; the request files themselves are mutable).

**Subprocess vs in-process:** internal senders are in-process Python on latency-sensitive paths
(plan polls at 0.5s). Both reports agree the CLI should be the *front door* to a shared in-process
service, not a subprocess dependency for internal producers.

---

## 3. Hard constraints (mostly Rust) — verified

`NotificationWire` (`sase-core/crates/sase_core/src/notifications/wire.rs:8-32`) mirrors the Python
dataclass field-for-field, `#[serde(default)]` on everything, **no `schema_version`** on rows.

1. **`action_data` is `BTreeMap<String, String>`** — flat, string-valued. `slot_count` /
   `question_count` are stringified and parsed back with silent `.unwrap_or(0)`; non-string values
   raise `PyValueError` at the PyO3 chokepoint. Rich payloads must stay in `<kind>_request.json`
   (the current design already respects this).
2. **Unknown `action` values fail silently in three independent places** — Rust's
   `mobile_action_kind` maps unknown → `Unsupported`, Python's pending-action map returns `None`,
   priority won't classify. A successful CLI exit does not mean the result is actionable.
3. **Priority/error classification is a hardcoded `(action, sender)` function in Rust**
   (`mobile.rs:400-411`): `PlanApproval | UserQuestion | JumpToMentorReview | LaunchApproval`, or
   sender `axe`/`crs`. Not expressible via `tags` (Rust never inspects them). **Collapsing to one
   generic action string would silently drop all three gates out of badge counts and mobile
   actionability.** This is the single strongest argument for keeping the four literals as the type
   tag.
4. **No field may be added Python-side first.** No `deny_unknown_fields` *and* no flatten
   catch-all: an unknown JSON field survives a read but is **permanently dropped** on the next
   rewrite/state-update (`store.rs:506-520`). Marking a notification read from the TUI would
   destroy a Python-only field. Rust first, always — and the wire is locked by 28 parity tests
   (`notification_store_parity.rs`, including an exact-JSON-keys test) plus golden fixtures for the
   mobile contract.
5. **The choice vocabulary is closed, in Rust.** `PlanActionChoiceWire{Approve,Run,Reject,Epic,
   Feedback}`, `QuestionActionChoiceWire{Answer,Custom}`, `LaunchActionChoiceWire{Approve,Reject,
   Feedback}`, `HitlActionChoiceWire{Accept,Reject,Feedback}` are closed enums, always emitted in
   full regardless of payload. Data-driven per-gate choices therefore cross the Rust wire and need
   versioning.

Downstream of Rust, **`sase-telegram`** has separate formatters, inline keyboards, callback flows,
request-file readers, and stale cleanup per action, importing SASE's plan/launch response executors
for privileged host behavior. Report A's framing is the right scope split: **constructor
unification** (one envelope/service; legacy actions as projections; incremental, no client breaks)
vs **protocol unification** (one generic action + declarative choices across ACE/mobile/Telegram; a
versioned cross-repo flag-day). These must not be conflated; the first delivers most of the value.

One boundary note: request construction, pending-state rules, and mobile interpretation are shared
backend behavior, so under the repo's Rust-core litmus test the *stable envelope* arguably belongs
at or below `sase-core` eventually. The wire-identical Python-first path defers that decision; it
should still be made consciously (question 3 below).

---

## 4. The `improve_plan` / `tester` removal: three separable layers

The ask treats "the hooks" as one thing. They are three layers, and only one touches notifications:

| Layer | What | Active? | Touches notifications? | Removal cost |
|---|---|---|---|---|
| **L1** | `improve_plan.yml`, `tester.yml` (`xprompts/examples/agent_families/`) + 2 prompt bodies (`agent_family_improve_plan.md`, `agent_family_tester.md` — these two *are* in the active catalog) | Definitions: no | No | ~Free |
| **L2** | Custom lifecycle-role machinery: `agent_family/custom_definitions/` (discovery/loading/models/validation), evaluator branches (`standard_plan_chain_evaluator.py`), `run_agent_exec_custom_roles.py`, role snapshots/visit caps/status labels | Yes, generic over role ids | No | Large feature deletion |
| **L3** | Plan-gate member options: `member_options`/`default_member_ids` in `plan_request.json`, `"Also run: …"` notes line (`senders.py:274-280`), `--with`/`--without` on `sase plan approve`, `ApproveOptionsModal` toggles, `selected_member_ids` in responses | Yes, plan-specific | **Yes** | Moderate |

Verified facts that reconcile the two reports' framings ("fully built" vs "incomplete"):

- The feature *shipped and can run*: evaluator, spawn (`spawn_custom_role_followup` mutates
  `LoopState` in the same runner process — no new agent process), CLI flags, and modal toggles all
  exist. No Python code branches on the ids `improve_plan`/`tester`; they are pure data.
- But key semantics are **dead code** *(all verified)*: `on_done` is parsed, validated, listed, and
  snapshotted but never read at runtime; `on_failure` is consulted only when a `role_completed`
  event carries a non-success outcome, yet the only emission site hardcodes
  `"outcome": "success"` (`run_agent_exec.py:218`) — failures take the error/break path instead;
  and `_select_custom_role_after()` returns the **first** matching role at a placement, silently
  ignoring the rest.
- No `kind: agent_family` definitions are active on this installation *(verified via the xprompt
  catalog)*; only the two prompt xprompts are.
- Removing **L3 does not remove L2**: `filter_roles_by_selected_member_ids` treats `None` as "no
  filtering", so activated custom roles would still run via their own `default_enabled` and
  `agent_family.plan_approval.default_members` config — just without gate-time selection.
- **L3 is what actually de-bulges the plan gate.** The member-options payload and "Also run" note
  are the only places this feature touches the notification system, and they are the plan-specific
  structure that stops the three gates from being the same shape. If any removal happens, sequence
  L3 before the gate refactor, or the plan request payload gets touched twice.

If the decision is full removal (L2+L3), report A's removal surface applies: the
`custom_definitions/` package and exports; `kind: agent_family` catalog entries (decide: hard error
with migration message vs one-release deprecation); `PlanApprovalMemberOption` and member payload
helpers; `--with`/`--without`; modal member rows/digit toggles and prompt-bar member state;
`run_agent_exec_custom_roles.py`; `custom_role_visit_counts` and selected-member state in
`LoopState`; custom-role fields on `FamilyRuntimeMetadata`/`FamilyEvaluation`/
`PlanApprovalTransition`; `agent_family_custom_role` artifact fields and ACE label projections
(decide: keep read-only for historical artifacts?); `agent_family.plan_approval.default_members` in
default config + JSON schema + docs; and a `docs/agent_families.md` rewrite. Manual `%n(parent,
suffix)` attachment, generic suffixes like `tester`/`reviewer`, and agent-initiated family launches
via `LaunchApproval` are a *different* feature and must remain — many tests use custom-looking
suffixes for generic members; delete lifecycle behavior, not every occurrence of the strings.

Practical costs either way: `tests/test_agent_family_custom_definitions.py` validates the example
prompt refs; PNG visual snapshots bake the `IMPROVING PLAN`/`TESTING` labels into committed images
(regeneration required); plan-chain golden JSON; and `docs/agent_families.md:129-131` positions the
examples as the onboarding path — deleting L1 alone leaves a shipped feature with no shipped
examples, and unblocks nothing.

---

## 5. Latent bugs and debt in the refactor's path (all re-verified)

1. **TUI-answered questions are never marked handled** —
   `_notification_modal_responses.py:36` early-returns unless `action_kind == "plan_approval"`, so
   a `UserQuestion` resolved from the TUI never gets `mark_already_handled`; Telegram keyboards
   stay live until state is re-derived from the filesystem. Launch handles itself
   (`launch_approval_actions.py:119`); questions are the odd one out.
2. **`LaunchApproval` is missing from Rust agent-dismissal** — `store.rs:677` matches only
   `Some("PlanApproval" | "UserQuestion")`, so launch notifications are not dismissed when their
   agent is killed. (The *priority* match does include `LaunchApproval` — only dismissal is
   inconsistent.) Likely a bug; confirm intent rather than assume.
3. **Nothing polls `launch_response.json`** (§1) — an approved launch dispatches host-side even if
   the requester died and will never learn of it.
4. **`silent` is unreachable from `sase notify create`** despite being first-class on the wire and
   filtered by the mobile bridge.
5. **Duplicate string→enum ladders in Rust** — `mobile_action_kind` (`mobile.rs:724`) and
   `action_kind_from_str` (`pending_actions.rs:438`) must be kept in sync by hand.
6. **`question_summary.py:60-71`** independently re-implements the pending-actions filesystem
   state rules.
7. **`memory_review`** is registered as a pending-action kind in Python but unknown to Rust
   entirely *(verified: zero matches in `sase-core/crates/`)* — a preview of what constraint 2
   does to any new kind added Python-side only.
8. **Doc drift**: "via hook" (`senders.py:205`); stale action list comment in
   `_notification_modal_flow.py`; `sase_notify.md` omits `tags` from the documented row shape.
9. **Stale-policy mismatch**: pending actions expire at a fixed 24h (`STALE_THRESHOLD_SECONDS`)
   while runners may still be blocked on response files — the envelope should define whether expiry
   is advisory, terminal, or per-kind.

Items 1, 4, 6, 8 are absorbed naturally by the refactor; 2 and 5 are Rust changes in another repo;
3 and 9 are design questions, not small fixes.

---

## 6. Recommended direction

Both reports converge on the same architecture; differences were emphasis, not substance.

1. **Do not change the wire (initially).** Keep the four action literals as the type tag. Zero
   Rust change keeps all parity tests and golden fixtures green and needs no `sase-core` release.
2. **Two layers, not one mega-function**: a common **gate constructor/service** (owns ids,
   timestamps, versioned request envelope, response-dir creation, `<kind>_request.json` write,
   producer-context capture, notification projection, pending-action registration, partial-failure
   cleanup, structured result) + **kind adapters** (own payload validation, presentation/choices,
   preflight, response schema, privileged response execution, continuation policy). A registry
   maps `kind` → adapter; raw inbox notifications remain possible but cannot impersonate
   registered privileged actions.
3. **`sase notify create` is the CLI face of that service**; internal senders call it in-process.
   Structured `--output json` returns at least notification id, request id, kind, request dir,
   request/response/preview paths, and continuation mode. Follow `cli_rules.md` (short aliases,
   alphabetized options); note bare `sase notify` already defaults to `list`.
4. **Keep rich payloads in request files**, only string pointers (`request_id`, `request_kind`,
   `request_dir`, `response_file`, agent-identity fields) in `action_data`.
5. **Fold the four `_externally_handled` branches into gate metadata** (request/response filenames
   derived from kind) — pure win, independently shippable.
6. **Decide launch's status explicitly before writing code** — part of the abstraction or an
   acknowledged exception; and whether to close its polling loop.
7. **Sequencing** (condensed from report A's phases, adjusted by report B's L3 insight):
   - **Phase 0:** settle contract boundary (constructor vs protocol unification), continuation
     modes, trust policy, in-flight compatibility window.
   - **Phase 1:** family-hook removal at the chosen layer — at minimum L3 (member options) so the
     plan request enters the new envelope clean.
   - **Phase 2:** build the shared service behind `sase notify create`; legacy action names and
     filenames remain as projections.
   - **Phase 3-5:** migrate **launch first** (already has a versioned schema, request id, owned
     dir, preview, typed result, explicit async), then **question** (consolidate its more-duplicated
     TUI/mobile response writing around one executor), then **plan** last (most side effects).
   - **Phase 6:** teach pending-state/ACE/Rust/Telegram to resolve common pointers with legacy
     fallback for in-flight requests.
   - **Phase 7 (optional, separate decision):** collapse action variants to a generic
     interaction protocol with versioned Rust/mobile/Telegram wires.
8. **Generated-skill discipline:** if the agent-facing invocation changes, update source templates
   under `src/sase/xprompts/skills/` (`sase_plan.md`, `sase_questions.md`, `sase_run.md`) —
   never deployed copies — regenerate via `sase skill init --force`, and note the `/sase_notify`
   skill contract is emphatically read-only today; per `memory/generated_skills.md`, CLI arg
   changes require same-turn skill + test updates.

Design traps to avoid (from report A, still apply): treating the gates as synchronously
equivalent; letting payload JSON declare handlers/side effects (kind must select a registered host
adapter); breaking in-flight requests during deployment; replacing typed plan choices with
arbitrary strings; time-of-check/time-of-use on mutable request files; assuming custom-role removal
means family removal; and expanding the first milestone to all of HITL.

Also: `202607/dynamic_agent_families_v1_v2_design.md` describes as unbuilt "v2 direction" work
that has since shipped (choice registry, custom roles as data). **It is superseded — do not design
from it.**

---

## Questions to answer before design and implementation

Merged and deduplicated from both reports (A: 18, B: 17), grouped; the first three are the ones
that most change the design.

### Intent and scope

1. **What does "use `sase notify create`" mean operationally** — (a) producers shell out to the
   CLI as a subprocess, (b) the CLI and in-process senders share one Python constructor, or (c) the
   CLI is the only *agent-facing* way to open gates while internals use the shared service? Both
   researchers read (b)/(c); (a) is slow and circular on the latency-sensitive plan path.
2. **Is the target abstraction "a notification" or "a gate"**, and does the common envelope own
   only creation/response-file plumbing, or also continuation behavior (marker+SIGTERM handoff,
   runner-slot reacquisition, prompt reconstruction, async polling)?
3. **Constructor unification or protocol unification** — keep typed `PlanApproval` /
   `UserQuestion` / `LaunchApproval` actions as projections (wire-identical, zero Rust change), or
   version and migrate `sase-core` + mobile + `sase-telegram` to one generic interaction action?
   Relatedly: is *any* `NotificationWire` change (e.g. row-level `schema_version`) acceptable in
   this initiative, and does the stable envelope eventually belong in Rust core per the backend
   boundary rule?
4. **Is HITL in scope now?** It is the fourth instance of the identical gate pattern; including it
   makes the abstraction honest, migrating it can still come later.
5. **Are the non-gate actionable senders in scope** (`memory_review`, `JumpToChangeSpec`,
   `JumpToMentorReview`, `ViewErrorReport`), or does "same structure" apply only to the blocking
   gates?

### The improve_plan / tester removal

6. **Which layer goes — L1 (example files), L3 (plan-gate member options), or L2+L3 (the whole
   custom lifecycle-role subsystem)?** L1 alone is nearly free but unblocks nothing; L3 is what
   makes the plan gate uniform; both researchers read the intent as at least L3.
7. **If L3 goes but L2 stays**, custom roles still run via config defaults with no gate-time
   selection, no `--with`/`--without`, no modal toggles — intended, or is that the signal L2
   should go too?
8. **Confirm what must remain**: manual `%n(parent, suffix)` attachment, arbitrary generic
   suffixes (`tester`, `reviewer`), and agent-initiated family launches via `LaunchApproval`.
9. **After removal, what happens to the seams** — delete the now-standard-only `role_completed`
   event and custom-role metadata/label readers entirely, or keep them as a compatibility/future-
   controller seam for historical artifacts?
10. **Cleanup posture**: hard "no longer supported" load error vs one-release deprecation for
    `kind: agent_family` files; ship replacement examples for `docs/agent_families.md`'s
    onboarding path?; PNG snapshot + plan-chain golden regeneration is required — acceptable?

### Gate design

11. **Does `sase notify create` own `response_dir` creation and `<kind>_request.json` writing**,
    with stable JSON output (request id, paths, continuation mode) for the caller to poll?
12. **How uniform is the directory layout** — a new neutral
    `interaction_requests/<kind>/<id>/{request,response,preview}` vs keeping per-kind layouts
    (sharded `plan_approval/`, flat `user_question/`, `launch_requests/<id>`) as adapter details?
13. **Is there one generic `wait_for_response()` poller** (plan and question both poll at 0.5s
    with separate implementations; launch has none), and does plan's mid-loop auto-approve
    re-check generalize?
14. **What is launch's status** — is "the approver performs the work" part of the abstraction or
    an exception? Should this change close the loop so something mechanically observes
    `launch_response.json` (and enforce rejection), and should non-agent `sase run` remain exempt
    from approval?
15. **Do gate choices become data-driven** (crosses the closed Rust choice enums → wire
    versioning) **or stay typed per-kind** (each new kind needs a coordinated Rust change)?
16. **Auto policies** — preserve plan auto-approve / question first-option / launch
    mandatory-approval as kind-intrinsic, or make auto behavior a common configurable field?
17. **Atomicity**: must a successful create guarantee request bundle + row + pending action are
    all durable, with rollback on partial failure, or is a documented best-effort with cleanup
    acceptable? (Today pending-action registration failure is silently swallowed.)
18. **Trust and provenance**: confine request files to SASE-owned directories, validate
    kind↔filename agreement, add content hashes so approved previews can't be swapped? Should raw
    `notify create` be barred from minting registered privileged actions without adapter
    validation?
19. **Stale policy**: is the 24h pending-action expiry advisory to transports, terminal for the
    producer, or per-kind configurable under the new envelope?

### Rollout and compatibility

20. **Mixed-version window**: must in-flight legacy requests (`plan_request.json` etc. written by
    old code) remain answerable by new consumers, and for how long — or is a drain/clear of
    pending actions at upgrade acceptable?
21. **Are the latent bugs (§5, esp. 1-3) fixed in this change or split out?** #2 is a Rust fix in
    another repo; #3 is a launch-design decision, not a small fix.
22. **Does `sase notify create` become agent-facing** (new/changed generated skills, and the
    read-only `/sase_notify` skill contract changes materially), or do `sase plan propose` /
    `sase questions` / `sase launch request` remain the public front doors sharing the constructor
    internally — and if so, for how long do they persist as compatibility aliases?

---

## Key references

- **Gate predicates (the duplication):** `src/sase/notifications/pending_actions.py:26-32,308-345`
- **Senders:** `src/sase/notifications/senders.py:196` (question), `:231` (plan), `:296` (launch);
  `append_notification` registration at `src/sase/notifications/store.py:113-123`
- **CLI:** `src/sase/main/notify_handler.py:37-84`, `src/sase/main/parser_commands.py:197-240`
- **Producers/pollers:** `src/sase/llm_provider/_plan_utils.py` (plan, sharded dir at `:242`),
  `src/sase/axe/run_agent_helpers_questions.py`, `src/sase/agent/launch_request.py` (approval gate
  `:187`), `src/sase/main/query_handler/_launch.py:47`
- **Marker/SIGTERM triggers:** `src/sase/main/plan_propose_handler.py:90,117`,
  `src/sase/main/questions_command_handler.py:81,95`, `src/sase/axe/run_agent_exec.py:154-171`
- **Rust wire:** `sase-core` `crates/sase_core/src/notifications/wire.rs:8-32`,
  `mobile.rs:393-411` (priority/error), `:724` (action kind), `store.rs:506-520` (rewrite merge),
  `store.rs:677` (dismissal gap), `pending_actions.rs:438`; parity tests in
  `crates/sase_core/tests/notification_store_parity.rs`
- **Family layers:** `src/sase/xprompts/examples/agent_families/` (L1),
  `src/sase/agent_family/custom_definitions/` + `standard_plan_chain_evaluator.py:112-176` +
  `src/sase/axe/run_agent_exec_custom_roles.py` (L2), `src/sase/plan_approval_choices.py` +
  `senders.py:274-280` (L3); dead `on_failure` path via `run_agent_exec.py:218`
- **Source reports:** `unified_notification_gates_consolidated__a.md` (codex — design layers,
  migration phases, removal surface, validation matrix),
  `unified_notification_gates_consolidated__b.md` (claude — premise corrections, gate abstraction,
  Rust constraints, latent bugs)
- **Superseded:** `202607/dynamic_agent_families_v1_v2_design.md` — do not design from it.
