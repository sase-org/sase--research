# Plan Decisions: one review across the TUI, Telegram, and CLI

Independent UX research by **cdx** · 2026-10-07

**Recommendation:** retain the accepted Plan Decisions design, and make its defining interaction **“approve the plan with the choices shown.”** Put a small, visible decision summary beside the plan; let reviewers change a choice without submitting anything; accept all final values together; and show those same values to every implementer and retry.

The best experience is a review with editable assumptions, rather than a questionnaire the user must complete before they can approve. The default path stays one Enter press in the TUI or one tap in Telegram. Changing an assumption remains deliberate, reversible, and separate from launching work.

This report extends the supplied [Plan Decisions research](plan_frontmatter_decisions/plan_frontmatter_decisions.md). Its schema and policy recommendations are the baseline: an optional `decisions:` map, at most five boolean or enum decisions, mandatory defaults, verified human-request quotes for memory defaults on, answers in both the gate record and approved plan, and a fixed epic graph. I investigated the current source independently. I did not read this swarm's other researchers' reports, transcripts, or findings.

Everything described as a recommendation below is proposed behavior, not a claim that the feature already exists. This was source and design research, not a live usability study.

## 1. The experience to aim for

A reviewer should be able to answer four questions immediately:

1. What work am I reviewing?
2. Which choices can I change, and what will each change do?
3. Which memory notes will this approval allow the agent to change?
4. What happens when I approve: save a plan, launch a coder, or start epic work?

The same answers should appear in all three interfaces. The arrangement can differ.

| Surface | Initial experience | Changing an answer | Submitting |
| --- | --- | --- | --- |
| TUI | Plan and Decisions are visible together | Toggle a boolean or open a small choice picker | Enter approves the currently displayed values |
| Telegram | Review card lists every decision and its current value | Change one decision, then return to the review card | “Approve as shown” accepts that card's version and values |
| CLI | `plan show` and approval dry-run expose the complete resolved values | Repeat `-D id=value` for overrides | `plan approve` accepts one validated vector; a review-version option can bind it to a preview |

Use the label **Decisions** consistently. Keep **Verdict** for approve, feedback, and reject. Decision rows configure the work; verdict controls settle the review.

Five decisions is a ceiling, not a target. Most plans should have zero, one, or two. A planner should make ordinary engineering choices itself. Include a decision only when the user has a meaningful preference, or when a scoped authorization is needed.

## 2. What the current source establishes

I checked sase at `ca3a1944235af56cb583f0837625dfc151457951`, sase-core at `d2a56b4ca928c602379619bb35869d133df9800e`, and sase-telegram at `d335fb8f9dfa5f0b534b3fdbbc591e505e7b5947`.

| Verified observation | Consequence for the design |
| --- | --- |
| Rust plan validation has explicit accepted-field lists and Authoring/Launch modes; there is no decisions field today. [Core validator](https://github.com/sase-org/sase-core/blob/d2a56b4ca928c602379619bb35869d133df9800e/crates/sase_core/src/plan/validate.rs) | Schema, normalization, and diagnostics start in sase-core. Do not add a Python-only permissive parser. |
| Plan kind validation pins the tale/epic queries, commands, groups, and edit operation. [Kind contract](https://github.com/sase-org/sase/blob/ca3a1944235af56cb583f0837625dfc151457951/src/sase/notification_gates/kind_validation/plan.py) | Decisions should be inputs to existing approval options. Arbitrary frontmatter commands or extra approval branches are the wrong extension point. |
| An AND branch accepts any nonempty subset; tale follow-up routing distinguishes `approve+commit`, `approve`, and `commit`. [Selection](https://github.com/sase-org/sase/blob/ca3a1944235af56cb583f0837625dfc151457951/src/sase/notification_gates/selection.py), [turn routing](https://github.com/sase-org/sase/blob/ca3a1944235af56cb583f0837625dfc151457951/src/sase/plan_gate_turn/create.py) | Adding a memory checkbox as another gate option could permit a memory-only submission and complicate routing. A boolean decision avoids both problems. |
| The TUI review already has separate controls and document panes, and switches layout at a width of 100. Its section is currently named “Decision”; host launch fields live behind `c`. [Modal](https://github.com/sase-org/sase/blob/ca3a1944235af56cb583f0837625dfc151457951/src/sase/ace/tui/modals/plan_approval_modal.py), [gate data](https://github.com/sase-org/sase/blob/ca3a1944235af56cb583f0837625dfc151457951/src/sase/ace/tui/modals/plan_approval_gate_data.py) | Add Decisions to the main review, above Verdict. Reuse responsive layout and leave infrequent launch customization behind `c`. |
| `TypedInputForm` has an enum editor, but no boolean-specific editor; booleans fall through to the general text input. [Typed form](https://github.com/sase-org/sase/blob/ca3a1944235af56cb583f0837625dfc151457951/src/sase/ace/tui/widgets/typed_input_form.py) | A proper boolean control is required. Typing “true” is unsuitable for a central consent interaction. |
| Telegram renders enum keyboards and optional Skip controls. Its final input step calls gate execution directly. [Formatting](https://github.com/sase-org/sase-telegram/blob/d335fb8f9dfa5f0b534b3fdbbc591e505e7b5947/src/sase_telegram/formatting.py), [step handler](https://github.com/sase-org/sase-telegram/blob/d335fb8f9dfa5f0b534b3fdbbc591e505e7b5947/src/sase_telegram/inbound_handlers/gate_input_steps.py) | Reusing that flow unchanged would turn the last choice into approval. Plan decision editing needs a return-to-review step and boolean buttons. |
| Shared input ids are collected once. Their types, choices, and repeatability must agree, but differing defaults and labels currently use the first declaration. [Input collection](https://github.com/sase-org/sase/blob/ca3a1944235af56cb583f0837625dfc151457951/src/sase/notification_gates/input_collection.py) | Compile tale `approve` and `commit` decision inputs from the same normalized definition, with identical defaults and labels. Reject conflicting per-option decision values. |
| Gate acceptance is fast and durable, separate from slower archive and launch work. Receipt identity includes the request hash, selected options, input identity, and feedback. Existing generic recovery can supersede a failed or dead execution owner's receipt. [Acceptance](https://github.com/sase-org/sase/blob/ca3a1944235af56cb583f0837625dfc151457951/src/sase/notification_gates/decision.py), [Rust policy](https://github.com/sase-org/sase-core/blob/d2a56b4ca928c602379619bb35869d133df9800e/crates/sase_core/src/gate_decision/policy.rs) | “Approved” and “implementation started” are separate states. Plan retries need a feature-specific rule to preserve accepted answers instead of silently replacing them. |
| Accepted edits increment `review_revision` and rehash the reviewed resource; the plan adapter's preview-regeneration hook does not rebuild its inputs. [Edits](https://github.com/sase-org/sase/blob/ca3a1944235af56cb583f0837625dfc151457951/src/sase/notification_gates/edits.py), [adapter](https://github.com/sase-org/sase/blob/ca3a1944235af56cb583f0837625dfc151457951/src/sase/notification_gates/adapters.py) | Freeze decisions for a review, and make submissions identify the revision the reviewer actually saw. Verifying the latest bundle alone does not establish that a stale client saw it. |
| The tale coder receives a fresh prompt referencing the approved plan; epic/phase reads expose the parent plan. [Coder handoff](https://github.com/sase-org/sase/blob/ca3a1944235af56cb583f0837625dfc151457951/src/sase/axe/run_agent_exec_plan_accept.py), [bead plan display](https://github.com/sase-org/sase/blob/ca3a1944235af56cb583f0837625dfc151457951/src/sase/bead/cli_detail_resolution.py) | Answers must reach implementers through the approved artifact and a host-written decision block. Planner chat and Telegram's private progress file are insufficient. |

I also checked `sase plan approve -h`, `sase plan show -h`, and `sase gate answer -h`. Direct-file approvals, failed-coder recovery, JSON plan display, declared-field `--set`, and gate resume already exist. The new feature must cover these routes, not only notifications.

The prior report's host approval percentages are useful motivation, but I did not recount them. No recommendation here depends on treating those percentages as current measurements.

## 3. Keep the frontmatter small

Retain the accepted grammar. This is a hypothetical plan whose quoted sentence came from its human request:

~~~yaml
---
tier: tale
title: Keymap help overlay
goal: Show active bindings in a readable help overlay.
size: small
decisions:
  grouping:
    ask: How should help be grouped?
    choices:
      pane: By pane, matching the footer hints
      mode: By leader mode, keeping related modes together
    default: pane
  tui_note:
    ask: Record the help convention in memory?
    memory: [tui.md]
    requested: "Record the help convention in the tui memory note."
    default: true
---
~~~

Without a human request for the note change, omit `requested` and use `default: false`. Require literal YAML `true`/`false` for authored toggles, and canonical keys for choices. Do not put executable gate JSON, commands, templates, or arbitrary input schemas in this block.

Use the complete `ask` text in each UI. Do not manufacture a title by humanizing `tui_note` or truncating the question so severely that the action becomes ambiguous. Wrap it. Choice labels should describe consequences, not just “A” and “B.”

Preserve author order across surfaces. It lets a planner put a choice next to its relevant consent and keeps screenshots, Telegram cards, CLI output, and the approved plan easy to compare.

### Describe both branches in the body

For the example:

> Decision grouping: pane groups bindings by their visible pane; mode groups them by leader mode. All other overlay behavior stays the same.
>
> Decision tui_note: if true, add the overlay convention to tui.md and regenerate its instruction projections. If false, complete the overlay without editing memory.

That is enough structure for a local variation. Avoid a new Markdown conditional language in v1. A decision id mentioned in the body is an authoring check, not proof that all combinations are implementable.

Plan size and verification must cover the most expensive allowed combination. An unchecked memory row should not conceal a larger architectural alternative. If an answer changes the tier, core architecture, or phase graph, ask before planning.

For epics, decisions are plan-wide. A phase can perform its explicitly described “off” branch or complete as an intentional no-op. Do not implicitly skip phase beads or rewrite dependencies.

## 4. One interaction contract for every surface

These rules should be release acceptance criteria:

- **Every value is visible before approval.** A collapsed question editor may hide alternative details, but the current value and memory scope remain in the main review.
- **Editing an answer never approves.** It updates a draft only.
- **Defaults are explicit recommendations.** The UI says “Default,” rather than implying that a human already answered.
- **An unanswered decision differs from an answer of false.** A pending proposal can show `default: false` with no `answer`. An approved plan must show an explicit final `answer: false`.
- **Approval accepts one complete vector.** Fill omissions from the frozen defaults on the host, then validate and record every value.
- **Accepted answers remain fixed.** Retry the implementation using those answers; changing them requires a new review.
- **Approval refers to the displayed review version.** A stale display cannot approve a newly edited document.
- **A failed launch does not erase an approval.** Recovery shows what was accepted and which subsequent step failed.

Keep drafts local to a reviewer/surface in v1. A Telegram draft should not silently change what an already-open TUI will submit. Shared durable state is the reviewed proposal and accepted receipt, not every intermediate click. Persist Telegram's draft across bot restarts; preserve the TUI draft through its `c` customization and editor round trips.

### Why retain defaults despite form guidance?

GOV.UK warns that preselected checkboxes and radios can cause missed questions or wrong answers. That is a real risk. This feature deliberately presents a planner's complete proposal, including its recommendations, rather than collecting unknown facts from a blank form. Retain defaults because they are part of SASE's accepted automation contract; compensate with persistent visibility, “Default” labels, change markers, and a final outcome sentence. Memory defaults remain constrained by provenance. This is a design judgment, not a claim that the form guidance endorses preselection. [Checkbox guidance](https://design-system.service.gov.uk/components/checkboxes/), [radio guidance](https://design-system.service.gov.uk/components/radios/).

## 5. TUI: a decision rail beside the plan

Reuse the current two-pane review. Put the plan title in the header and the decision count in its own section. The document continues to occupy the larger pane.

~~~text
┌ Plan Review · Keymap help overlay ───────────────────────────────────┐
│ Decisions · 2                  │ Reviewed plan · version 4           │
│                                │                                    │
│ How should help be grouped?    │ ## Overlay behavior                │
│   [ By pane ▾ ]  Default       │ ...                                │
│   Matching the footer hints    │                                    │
│                                │ ## Decisions                       │
│ [x] Record the help convention │ grouping: pane or mode ...         │
│     in memory?                 │ tui_note: update only if enabled   │
│     tui.md · reference         │ ...                                │
│     From your request          │                                    │
│                                │                                    │
│ Verdict                        │                                    │
│ [x] Launch coder               │                                    │
│ [x] Save approved plan         │                                    │
│                                │                                    │
│ Save plan; launch coder; group by pane; update tui.md.                │
│ [ Approve & launch ]  [ Feedback ]  [ Reject ]                       │
└─────────────────────────────────────────────────────────────────────┘
  Enter approve · Space change · Tab move · e edit plan · c launch options
~~~

This is a wireframe, not a proposal to replace all existing keybindings or their configured labels. Use the configured gate navigation bindings and update default_config.yml for any new bindings.

### Controls and hierarchy

**Boolean:** a checkbox with visible Yes/No semantics. Space changes it immediately. For a memory row, unchecked means that this review grants no authorization for that change.

**Choice:** a compact selected-value control. Space may retain the existing enum-cycle shortcut. Also provide a small picker that shows every alternative and consequence; sequential cycling alone hides the alternatives. In the picker, Enter selects a value and returns to the review. It must not also trigger the outer approval handler.

For two or three choices, an expanded focused row can show a short radio list. For four or five, the same picker remains usable. Do not display two checkboxes for a mutually exclusive choice.

Show “Changed · default: By pane” when the current value differs from the planner's default. Do not rely on a colored dot alone. Offer “Restore default” in the focused editor rather than adding another global hotkey.

**Memory:** include the note selector, its resolved project/home identity where needed, and a concise type hint. Core notes can show “core · loaded every turn”; newly created notes show “new.” These facts help assess a durable context change. Put the full quoted request and its source behind an inspectable provenance detail, not a tooltip that keyboard users cannot reach.

The outcome sentence updates after every decision or launch-option change. It lists included memory edits by name and summarizes omitted memory changes when relevant. A zero-memory plan can simply omit that clause; do not add routine warnings.

**Primary action:** label the current effect, such as “Approve & launch,” “Launch coder,” “Save approved plan,” or “Approve & start phases.” The server's existing option ids remain stable. A commit-only tale records its answers but does not start implementation; show that clearly after settlement.

### Narrow terminals and accessibility

Stack Decisions, the document, and Verdict when width requires it. Keep the outcome and primary action available without scrolling through the entire plan again. On a short terminal, use a bounded decision area and a sticky summary; never truncate the last memory consent out of view without a visible count.

Keep a visible focus indicator, text state alongside glyphs, wrapped labels, and a usable plain-text rendering. Escape closes a picker first; Escape at the review closes the view and leaves the gate pending. Closing is not rejection.

W3C's grouping guidance supports associating related inputs with a clear group label and making individual labels understandable. The analogous TUI rule is that Decisions and Verdict have distinct focus groups and comprehensible rows. This does not by itself establish terminal screen-reader support. [W3C grouping controls](https://www.w3.org/WAI/tutorials/forms/grouping/).

### Keep the plan readable without rewriting it

Do not mutate the YAML or hide sections of plan prose while the user clicks choices. The document is the stable proposal; the decision rail is its current configuration. After approval, render a compact “Accepted decisions” summary above the body and keep the original branch descriptions available for audit.

A jump from a focused decision to its body mention is useful later. It should not require adding `section:` fields or a conditional document engine to v1.

## 6. Telegram: a review card, with targeted changes

The initial card should fit an ordinary phone screen when a plan has two short decisions:

~~~text
📋 Tale · Keymap help overlay
Show active bindings in a readable help overlay.

Decisions
1. Help grouping: By pane · default
2. Memory: Update tui.md · from your request

On approval
Save the plan and launch the coder.

[ ✅ Approve as shown ]
[ Change decisions ] [ View plan ]
[ Feedback ] [ Reject ]
~~~

Use full questions and resolved note names in the detail view. The compact labels above are illustrative; do not infer shortened wording mechanically from an id.

“View plan” uses the existing document delivery/view route, such as its plan attachment. Do not require a Telegram Mini App or an external web review site for this bounded form.

### Preferred change flow

1. **Change decisions** opens a list of questions with their current values.
2. The reviewer chooses the one they want to change.
3. A boolean gets two explicit buttons; an enum gets one button per labeled alternative.
4. Choosing a value saves the draft and returns to the review card.
5. The updated card marks the changed value and still offers **Approve as shown**.

There is no need to answer unchanged questions. An initial implementation can reuse the typed step flow, but completing it must return to the review card. The ideal UX is targeted editing, not a mandatory walk through five questions.

Example detail:

~~~text
Record the help convention in memory?
tui.md · reference
Default: Yes · quoted from your request

“Record the help convention in the tui memory note.”

[ ✓ Yes, update memory ]
[ No, skip this update ]
[ Restore default ] [ Back to review ]
~~~

For a default-false row, show “Not requested · default: No.” That is neutral context, not an alarm. The user can explicitly enable it.

Replace generic **Skip** in this decision editor with **Keep default: No** or **Restore default**, as appropriate. The current generic Skip removes a field; it does not communicate which resolved value approval will use. The last answer must not execute the approval command. GOV.UK's check-answers pattern returns users directly to the summary after a targeted change; it supports this interaction shape. [Check answers](https://design-system.service.gov.uk/patterns/check-answers/).

### Make “as shown” technically true

A callback should identify a server-stored card snapshot containing the reviewed request version and draft values. Do not resolve it against whatever happens to be in a mutable progress file when the tap finally arrives.

Telegram limits callback data to 1–64 bytes. Use compact opaque handles and server-side state, not the YAML, a decision JSON object, or long labels in callback payloads. Answer callback queries promptly, then update the card with the result; Telegram otherwise keeps showing its progress indicator. [Telegram Bot API](https://core.telegram.org/bots/api#inlinekeyboardbutton), [callback queries](https://core.telegram.org/bots/api#callbackquery).

Prefer callbacks that **set a value** to callbacks that blindly toggle it. A repeated delivery of “set memory=false” is harmless; a repeated “toggle memory” can undo the user's intended choice. Bind callbacks to the authorized reviewer, request identity, and displayed draft/review version.

If a card is stale, say:

> This plan changed since this card was shown. Review the updated plan before approving.

Provide **Refresh review**. Do not silently replace the version and approve.

Once acceptance succeeds, remove or replace the approval keyboard and edit the original card:

~~~text
✓ Approved via Telegram
Grouping: By mode
Memory: Update tui.md
Starting coder…
~~~

A later update can say “Coder started” or “Approved; coder could not start — retry implementation.” Retrying uses the accepted values. A concurrent approval elsewhere shows the actual accepted values and source, rather than leaving an actionable old keyboard.

## 7. CLI: explicit overrides and useful previews

Add the accepted repeatable option `-D/--decide ID=VALUE` to `sase plan approve`. Keep defaults noninteractive. Do not open a surprise questionnaire simply because the target has decisions.

Proposed usage:

~~~sh
sase plan show keymap_help_overlay
sase plan approve keymap_help_overlay -n
sase plan approve keymap_help_overlay -D grouping=mode -D tui_note=no -n
sase plan approve keymap_help_overlay -D grouping=mode -D tui_note=no
~~~

For booleans, accept `yes/no` and `true/false` as CLI conveniences, and canonicalize to boolean JSON. The YAML grammar remains stricter. Enum values are keys, not translated display labels.

Validate every override before accepting a receipt, editing an archive, saving a plan, or launching work. Reject unknown ids, invalid values, and repeated ids; list permitted values and show the corresponding question. Do not accept “last override wins.”

Example dry-run:

~~~text
Keymap help overlay · tale · review version 4

Decision    Selected    Default    Effect
grouping    mode        pane       Group help by leader mode
tui_note    no          yes        Leave tui.md unchanged

Will save the approved plan and launch the coder.
Memory edits authorized by this approval: none.
Preview only.
~~~

The actual command prints the accepted values and subsequent action status. Distinguish a rejected override from an accepted approval whose launch failed.

### Bind previews when exact reproduction matters

Recommend a small optional `-V/--review-version TOKEN` on plan approval, returned by its dry-run. The token should identify the reviewed content and frozen decision definition; a simple user-visible version number can accompany it.

~~~sh
sase plan approve keymap_help_overlay -D grouping=mode -D tui_note=no -V REVIEW_TOKEN
~~~

This is an addition to the earlier report. It lets scripts make “approve what I previewed” an enforceable promise. Without the token, a manual approval operates on the current proposal at acceptance time. Never use a hidden global “last preview” as authorization.

Choose this alias only after checking the parser's complete flag inventory. The generic gate command already uses `-r` and `-R` for resume/restart, so those are poor cross-command choices for a revision token.

Existing `sase plan show -f json` should include ordered definitions, defaults, review version, accepted answers if any, and provenance. Preserve existing `--color` behavior and text output usability when piped. Use `-h` examples that explain a default, an override, and an immutable-answer retry.

Generic `sase gate answer --set` remains the advanced typed-input route. It must use the same decision resolver as `plan approve`, including rejecting differing values supplied separately for tale `approve` and `commit`. Users should not need internal names such as `decision_tui_note` for ordinary plan approvals.

### Already approved plans

`sase plan approve PLAN` can currently relaunch a failed coder. Preserve that convenience, and make its output explicit:

> Retrying implementation with the accepted decisions: grouping=mode; tui_note=no.

Refuse decision changes on this recovery route:

> This plan is already approved. Retry uses its accepted answers. Start a new review to change tui_note.

Also cover direct approvals with no live gate, commit-only approvals followed by later implementation, and epic launches through bead work. No route should infer authorization from a hand-edited `answer: true`.

## 8. Memory consent: show scope and provenance precisely

Retain the earlier recommendation for plan-driven work: a memory edit requires an accepted memory decision covering the note. A specific direct human request outside a planning workflow stays valid. This research does not recommend forcing a three-stage plan workflow onto a one-line requested note correction.

| Situation | Effective default | What the reviewer sees | Result on approval/automation |
| --- | --- | --- | --- |
| Human explicitly requested the scoped update; matching quote found | On | “From your request,” with source context available | Human approval or authorized %auto may retain On |
| Planner suggests an extra update | Off | “Not requested · default: No” | Omission leaves it unauthorized |
| Authored On but its quote is missing/unmatched | Proposal should fail while the planner can repair it | If detected at gate construction, show “Request quote not found · default changed to No” | Clamp to Off; never silently retain On |
| Human deliberately enables an unrequested update | Off initially, changed to On | “Changed · will update tui.md” | Explicit reviewer action authorizes that scope |
| Human disables a requested update | On initially, changed to Off | “Changed · skip this update” | Coder omits it; do not file a bead reopening the human's decision |
| %auto leaves an unrequested update Off | Off | Settled notification shows the values and automation source | Omit it; retain the baseline's deduplicated memory-follow-up route |
| No memory decision covers a proposed edit | No plan authorization | Heuristic authoring warning if detectable; precise uncovered path at guard | Guard eventually blocks publication of the uncovered edit |

**A quote match proves that those words occur in human-authored text. It does not prove intent.** For example, a fragment “edit tui.md” also occurs inside “do not edit tui.md.” Preserve the accepted deterministic quote check, but show the source sentence/turn when inspected and instruct authors to quote the complete affirmative request. Avoid presenting a green “Verified consent” seal as if intent were mechanically established. “From your request” with inspectable context is more honest.

Scope must resolve to durable resource identities: repository/project or home memory, note/strand, and operation context where relevant. A selector's meaning must not change because a phase runs in another workspace or because home fallback resolves differently later. Show ambiguous project/home scope before approval. New notes need an explicit project/home target.

If a broad memory selector expands to a web, freeze and display its covered notes; new strands added later should not acquire authorization accidentally. If multiple decisions cover the same note, reject ambiguous overlapping grants in v1 rather than inventing boolean precedence.

Note-level authorization is still coarse. It does not prove that the agent's prose matches the planned change. The body must describe the update; a scope guard checks changed paths, not semantic fidelity.

Generated AGENTS.md and provider shims are derived work. Coverage of an authorized canonical note covers its regeneration, not arbitrary manual edits to instruction files.

Keep automation mode visible. A receipt should distinguish the decision mechanism, such as human or auto, from transport, such as TUI, Telegram, or CLI. `source=cli` alone is not proof that a human invoked it: agents also run CLIs. Allow human-shell `-D tui_note=yes` only through the host's trusted caller classification; an agent must not confer memory authorization on itself by selecting a source label.

Start the finalizer guard in advisory mode, as the prior report recommends. Later enforce it for the coder, every phase, and the land agent. When enforcing, refuse publication as a whole and explain the uncovered notes. Automatically splitting out memory files can leave source, policy, generated shims, and implementation inconsistent. Offer recovery choices; do not silently publish half the intended result.

## 9. Reliability details that determine the UX

### Normalize before accepting, not only inside the approve command

Today the receipt fingerprints the submitted per-option inputs. The generic resolver does not fill declared defaults. Consequently, an omitted choice and an explicit value equal to its default have different submitted input identities.

For Plan Decisions, resolve omissions and memory-default verification **before receipt identity is computed**. Then the following are the same decision:

- Telegram's initial “Approve as shown” with omitted overrides.
- TUI submitting all currently visible defaults.
- CLI explicitly naming those same default values.

Keep raw submission provenance separately if useful. Every command receives the same fully resolved decision vector. `approve` and `commit` must not independently resolve or stamp divergent values. This is a refinement to the baseline's “resolve in the approve command,” motivated by the current acceptance boundary.

### Acceptance, projection, and launch are separate stages

A safe sequence is:

~~~mermaid
flowchart LR
    P["Frozen proposal and defaults"] --> D["Reviewer draft"]
    D --> A["Accept version and resolved answers"]
    A --> S["Write approved-plan projection"]
    S --> L["Save plan and launch requested work"]
    A --> R["Durable acceptance record"]
    R --> S
~~~

The accepted record needs a durable, recoverable resolved vector, not just its digest. `response.json` still records completed command results. Stamp `answer` and `decided_by` in the approved plan as the readable projection. Preserve enough identity to verify that projection against the accepted record.

If projection/publication fails after acceptance, show “Approved; saving plan failed.” Do not launch an implementer against an unstamped plan. Recovery repairs the projection from the original receipt rather than asking again or applying current defaults.

Do not promise literal exactly-once side effects across arbitrary process crashes. Use the existing execution journal and idempotent archive/launch recovery to prevent duplicate work. The relevant user promise is one accepted set of answers, recoverable execution, and no hidden change of scope.

HashiCorp's saved-plan mode is a useful analogy: a saved plan contains finalized choices, and applying it cannot accept new planning options. SASE's approved artifact should likewise be an execution contract; a retry should not renegotiate it. This is an architectural analogy, not an assertion that SASE has Terraform's execution semantics. [Terraform apply](https://developer.hashicorp.com/terraform/cli/commands/apply).

### Freeze the entire decision meaning during a review

Freeze ids, kinds, alternatives, defaults, memory scope, request evidence, and question/choice wording. The earlier report permits editing `ask` wording while freezing the set. I recommend the stricter rule for v1: changing “Record the convention?” to “Skip the convention?” inverts boolean meaning without changing an id.

Allow body edits through the existing edit action; accepted edits advance the review version. To change a decision definition, submit feedback and create a new review. Preserve a rejected editor draft using the current origin-draft mechanism, and explain the repair:

> Decision definitions are fixed for this review. Change answers in Decisions, or send feedback to revise the questions.

Feedback may carry the reviewer's provisional choices. They are preferences for the replanner, not approval. Preserve them by stable id only when their meanings remain compatible; recheck all memory provenance. Human On in a rejected review is not an authorization receipt for the next plan.

### Error messages should explain the next useful action

| State | Suggested message/action |
| --- | --- |
| Unknown CLI enum key | “grouping must be pane or mode. You supplied panes.” |
| Unmatched requested quote | “tui_note defaults to Yes, but its request quote was not found in human-authored text. Quote the request or default to No.” |
| Stale Telegram/TUI review | “This plan changed. Refresh review before approving.” |
| Another surface accepted first | “Already approved via CLI. Accepted choices: grouping=mode; tui_note=no.” |
| Plan approved, launch failed | “Approved with these choices. Coder could not start. Retry implementation.” |
| Guard found an uncovered memory file | “glossary/new-term.md is not covered by an accepted memory decision. Remove that edit or review a revised plan.” |
| Invalid in-editor draft | Keep the draft; show field/path diagnostics and “Reopen editor” |

Preserve valid draft answers after a recoverable validation error. Put the error beside the affected row and provide a focusable summary when several errors exist. This adapts the GOV.UK error-summary pattern to a review modal rather than treating a toast as the only explanation. [Error summary guidance](https://design-system.service.gov.uk/components/error-summary/).

## 10. What to ship first, and what to defer

**Ship together:** the Rust schema/resolver, frozen definitions, accepted-answer propagation, memory provenance, TUI controls, Telegram review-return flow, CLI overrides, direct/recovery route coverage, and accurate acceptance/launch status. Enable the beta only when the deployed surfaces can display the decisions they are approving.

Older clients can still omit inputs and resolve defaults correctly at the protocol level. That is useful compatibility, but it is not equivalent to informed review. Do not label a legacy card “Approve as shown” if it never showed the decisions. Surface capability checks and the beta rollout should prevent that mismatch. %auto remains a separately authorized default-resolution route and never masquerades as a human click.

**Defer:** conditional phase graphs, free-text decisions, dependent questions, arbitrary frontmatter commands, per-decision automation overrides, live rewriting of plan prose, cross-device draft synchronization, and a custom Telegram web application. None is needed to solve the two requested use cases.

Do not let the enforcement guard delay a useful review feature; ship it advisory and move to enforcement after real recovery paths are verified. Until enforcement lands, describe memory consent as structured authorization plus agent instructions, not a filesystem write barrier.

## 11. How to evaluate the design before calling it finished

Use two actual task shapes: a tale with one optional memory update, and an epic with one local product choice plus one requested memory update. Exercise each in the TUI, Telegram, and CLI.

| Scenario | Required outcome |
| --- | --- |
| Accept defaults | All three surfaces produce identical final values and memory scope |
| Flip only memory Off | Product work proceeds; canonical memory and its projections receive no new change |
| Flip only a product choice | Both the plan archive and every implementer receive the selected key |
| Commit-only tale, then launch later | Later coder receives the recorded choices, with no new default resolution |
| Automation | Defaults settle without a questionnaire; requested On needs matched human provenance |
| Last Telegram input | Returns to review; no approval, archive write, or coder launch yet |
| Accepted body edit plus stale card | Old card cannot approve the new version |
| Double tap and concurrent CLI approval | One accepted vector; other client reports that vector accurately |
| Crash after acceptance, before archive/launch | Original answers survive, and recovery does not duplicate a coder |
| Failed coder retry | Uses accepted values even if current schema defaults changed |
| Changed decision definition during editing | Review refuses the definition change and preserves the editable draft |
| Direct-file approval and epic bead launch | Same resolver and authorization checks as notification review |
| Narrow terminal and long note selectors | Value, memory scope, and approval effect remain discoverable |
| Uncovered memory diff | Advisory/enforcing guard names exact paths and offers a coherent recovery |

For a short usability pass, ask Bryan to review without explaining the new mechanics, then have him state what Enter or the main Telegram button will do. Observe whether he discovers changed values, understands an Off memory choice, and can change one answer without approving. That evidence is more valuable than a speculative numeric conversion target.

Track default override rate by decision kind, stale-review rejections, post-approval launch failures, and uncovered-memory guard findings. The useful question is whether defaults and labels are intelligible, not whether every approval is fast.

## 12. Decisions for the lead designer

The baseline can proceed without another broad architecture debate. The highest-value UX decisions are:

1. **Treat the main view as the final check.** Keep Decisions visible and make the submit label describe the current launch/save action.
2. **Separate choice editing from approval everywhere.** Telegram needs an explicit return-to-review stage; TUI nested pickers must consume Enter locally.
3. **Make “as shown” a versioned contract.** Snapshot card values, reject stale reviews, and offer CLI preview binding.
4. **Normalize once before acceptance.** This makes omitted defaults and explicit defaults equivalent and prevents tale approve/commit divergence.
5. **Keep accepted answers immutable through recovery.** Repair projection or retry work; a changed choice means a new review.
6. **Show memory scope and the human quote's context.** Provenance matching is valuable, but must not be dressed up as a proof of intent.

The feature's beauty should come from a calm, consistent review: the work, the choices, and the next action are all visible, and every interface tells the same story.

## Source and method notes

The supplied consolidated report was read through `sase artifact read research:202610/plan_frontmatter_decisions/plan_frontmatter_decisions.md` before independent investigation. It is the accepted design input, not a current swarm peer report.

Repository source was read from this workspace and from checkouts returned by audited `sase repo open` calls for sase-core and sase-telegram. GitHub links above identify the exact locally inspected revisions; repository content was not fetched through the web.

Audited project memory reads included artifact handling, gate/single-turn definitions and decisions, macro conventions, TUI guidance, and CLI rules. The current `sase_memory_write` skill was reviewed as policy context. No memory files, skills, application code, gates, or user messages were changed or sent by this research.

External sources were primary documentation: GOV.UK Design System, W3C WAI, Telegram Bot API, and HashiCorp Terraform documentation, accessed 2026-10-07. Their patterns inform the recommendations; none is evidence of a SASE usability study. Wireframes are design proposals, and the feature and CLI additions remain unimplemented.
