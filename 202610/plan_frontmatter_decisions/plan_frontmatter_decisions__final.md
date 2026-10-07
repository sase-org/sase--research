# Plan Decisions: Typed Reviewer Choices in Tale and Epic Frontmatter

_Lead researcher's consolidated report · 2026-10-07 · Merges five independent swarm
reports (`__cdx`, `__cld`, `__grk`, `__mus`, `__gem`, in this directory) with my own
source checks against sase `95806cf189`, sase-core `d742e207`, sase-telegram `d335fb8`,
the plans sidecar, and the retained gate bundles under `~/.sase/interaction_requests`._

---

## Bottom line

**Build it, but not as "gate options".** All five researchers agree that the
need is real. Today a planner with one plan-shaping question has two bad choices:

- **Block.** It opens `/sase_questions`, ends its turn, and the human answers
  without seeing the plan. Then a second agent turn writes the plan, and the human
  reviews it in a second sitting.
- **Guess.** It writes optional work into the prose, where the coder will implement
  it or skip it with nothing enforcing either.

Memory authorization has the same shape. Planners currently hand-write memory
authorization into plan prose, and under `%auto`, which settles about 75% of plan
approvals on this host, nobody reviews it at all.

What should be embedded is **decisions, not gates**. The plan should declare a few
typed, defaulted choices. The host compiles them into **typed inputs on the existing
`approve` option** of the plan-approval gate. The reviewer answers them in the same
review where they read the plan. The answers are recorded in the gate response and
also written into the archived plan, which every implementer already reads.

Do not embed real gate options. The plan gate's query, options, commands, and groups
are a sealed, host-owned contract. AND-group members can be submitted in any non-empty
subset. Plan follow-ups are routed by the exact set of selected options. Embedding
options breaks all three properties. Four of the five reports reached this conclusion
independently. The fifth (`gem`) proposed extending the AND group; §5 explains why that
design fails.

**The recommendation in one screen:**

```yaml
---
tier: tale
title: Keymap help overlay
goal: Pressing ? in ACE shows every active binding, grouped for scanning.
size: small
decisions:
  grouping:
    ask: How should the overlay group bindings?
    choices:
      pane: By pane, matching the footer hints
      mode: By leader mode; denser, but splits pane actions
    default: pane
  tui_note:
    ask: Record the overlay's keymap conventions in the tui memory note?
    memory: [tui.md]
    requested: "and note the convention in the tui memory"
    default: true
---
```

- **One optional `decisions:` map.** It holds at most five entries. Each entry is a
  toggle or a 2–5-way choice, and every entry requires a `default`.
- **Memory decisions.** A decision that carries `memory:` is a memory decision. Its
  `memory:` field uses the same selectors as `sase memory read`.
- **The `requested:` quote.** A memory decision may default to on only if `requested:`
  quotes the human's words. The host checks the quote word for word and forces the
  default off when the check fails.
- **Validation and compilation.** `sase-core` validates the map. The host compiles it
  into inputs on the plan gate. ACE shows a **Decisions** section that is always
  visible, Telegram shows "Approve as shown", and the CLI gains `-D`.
- **Recording.** Answers are recorded once in the gate response and stamped as
  `answer:` into the archived plan.
- **Consumption.** The coder and every epic phase receive a short host-written
  "Reviewer decisions" block.
- **Enforcement.** A finalizer guard behind a beta flag checks memory diffs against
  the accepted memory decisions. It starts advisory and later enforces.

---

## 1. What exists today (verified)

Each row was either checked directly by me or cross-confirmed by at least two reports.

| Fact | Evidence | Design consequence |
| --- | --- | --- |
| Plan frontmatter is a closed Rust schema. Unknown keys are errors, and duplicate YAML keys are rejected (`yaml-invalid: duplicate entry with key`, which I reproduced). | sase-core `crates/sase_core/src/plan/validate.rs:24-39`, which uses `serde_yaml` | New keys start in sase-core. A map keyed by id is safe, because a duplicate id fails validation. |
| Validation has two modes, `Authoring` and `Launch`. | `validate.rs` `PlanValidationMode` | Forbid the system-written `answer:` while authoring and allow it in archived plans. |
| The tale query is `(approve AND commit) OR reject OR feedback`. The epic query is `approve OR reject OR feedback`. Kind validation pins the query, options, groups, and operations. | `src/sase/notification_gates/kind_validation/plan.py:43-109` | Any extra option fails `invalid_plan_query` / `invalid_plan_options`. |
| AND semantics accept any non-empty subset of one branch. | `notification_gates/selection.py`: `selected_set <= set(branch)` | If `memory` joined the AND group, a reviewer could submit `memory` alone with no approval. |
| Tale follow-ups are routed by the exact selected-option key: `approve+commit`, `approve`, `commit`. | `plan_gate_turn/create.py:62-72` | Each added AND member doubles the number of routing keys (2ⁿ). |
| Tale `approve` and `commit` both accept the same inputs, because every selected option receives the same input. Shared ids are collected once. | `plan_gate.py:240-272`; `notification_gates/input_collection.py:21` | The intended carrier for decisions already exists. |
| The declared-input vocabulary covers `bool` and `enum` (with `{value,label}` choices), plus `default`, `help`, and `required`. | `notification_gates/model_inputs.py:90-130` | Decisions compile directly into it. |
| `%auto` picks the primary branch's `default_selected` options. `automatic_input` supplies `{}` for tales and `{"epic_launch_mode":"launch"}` for epics. | `notification_gates/adapters.py:46,334-349` | JSON Schema does not fill in defaults, so the approve command has to resolve them. |
| **Question gates under `%auto` take the first option.** | `user_question_actions.py:403-419` | Even `/sase_questions` does not stop `%auto`. A "required" plan decision would therefore be the only construct that blocks it, which would be inconsistent. |
| In-gate `edit_plan` re-validates the plan but never rebuilds options or schemas: `regenerate_previews` is a no-op. | `adapters.py:330-332` | Freeze the decision set for the duration of a review. |
| The tale coder starts fresh with `@<archive plan ref>` and "Implement it now". | `axe/run_agent_exec_plan_accept.py:528-551` | Answers that are not in the plan file or the host prompt never reach the coder. |
| The epic bead's `design` field is the plan ref, and `sase bead read` shows it to every phase as **EPIC PLAN**. | `bead/epic_from_plan.py:145`; `bead/cli_detail_resolution.py:269-299` | Answers stamped into the archived plan reach every phase and the land agent automatically. |
| ACE: the plan modal's left column has a section titled **"Decision"**. The `c` modal collects host inputs that are otherwise hidden (`HOST_COLLECTED_PROPERTIES`). An `enum` with up to 5 choices cycles in place. **A `bool` input has no toggle widget** and falls through to a text box. | `plan_approval_modal.py:166`; `plan_approval_gate_data.py:42-51`; `widgets/typed_input_form.py:145,307-323` | Rename "Decision" to "Verdict". Add a real bool toggle. Never put decisions behind `c`. |
| Telegram has a typed declared-input flow. An `enum` gets an inline keyboard. Non-required fields get a skip button (`k`) that keeps the default. A **`bool` gets no keyboard** and falls back to a typed reply. | sase-telegram `gate_inputs.py`, `inbound_handlers/gate_input_steps.py:88-105`, `formatting.py:1166-1200` | Telegram can collect decisions today. It needs a yes/no keyboard and a one-tap "approve as shown". |
| Memory authorization is enforced only by skill text. Its route 2 says "plan approval is user approval". No finalizer inspects memory diffs. | `macros/skills/sase_memory_write.md:19-40`; no memory-diff logic under `src/sase/finalizers/` | The feature can make the policy precise, and a later guard can enforce it. |
| The memory skill already says another agent's request does not count as authorization. | `sase_memory_write.md` ("Nothing else counts — not … another agent's request") | Quote verification must use only text a human wrote, never prompts written by agents. |
| `sase memory read` addresses notes as `tui.md`, `glossary`, or `glossary:stitch`. It resolves project memory first and falls back to `~/sase/memory/`. | `sase memory read --help` | Memory decisions can name their scope in a grammar agents already use. |
| `sase plan approve` already accepts `-n/--dry-run`, `-k`, `-m`, `-p`, and `-w`, and can approve a plan file with no live gate. | `sase plan approve --help` | Add `-D id=value`. This direct route must apply the same resolution rules as the gate. |

**Corrections to individual reports:**

- **gem** claims a tool-execution guard or pre-commit hook would reject memory writes.
  Neither exists today.
- **mus** routes answers to the coder through the question-gate Q&A merge path. Plan
  coder prompts are rebuilt by the host (`raw_prompt: True`, `plan_gate_turn/followup.py`),
  so that path does not reach the coder. The archived plan plus a host-written prompt
  block is the channel that works.

---

## 2. Evidence from this host

| Signal | Number | Implication |
| --- | --- | --- |
| Tale plan-gate responses | 198: **144 auto (73%)**, 42 TUI, 12 CLI (`plan_response`) | Whatever the planner sets as `default` is what happens in about 3 of 4 plans. Defaults carry the policy. |
| Epic plan-gate responses | 92: **75 auto (82%)**, 12 TUI, 5 CLI | Same pattern. |
| Selections | Tales: 197 `approve+commit`, 1 reject, 0 feedback. Epics: 91 approve, 1 reject. | Reviewers almost never touch the existing toggles. Enter must stay one keystroke. |
| Human tale reviews that set a hidden `c` input (`coder_prompt` / `coder_model` / `wait`) | **0 of 54** | A control behind a secondary screen goes unused. Decisions must be visible in the main review. |
| Archived plans, Aug–Oct 2026 | 1,867 total. **≥20** explicitly create or edit memory notes. **65** contain hand-written disclaimers such as "This plan does not authorize memory edits. Do not edit `sase/memory/`." | Planners already improvise a memory-authorization field in prose. Structure would replace it. |
| Plans mentioning `sase/memory/` (Sept 2026) | 146 of 807, mostly read-only references ("read the tui note") | Detecting memory edits by scanning the body would raise many false alarms. Use a warning, not an error. Do precise enforcement on the diff. |
| Memory-consent question gate (found by `cld`) | One of the 3 settled question gates. The planner asked whether to keep a decision-record step, and the answer was "Keep". | This is use case 1 nearly word for word. It cost one extra question gate, one extra agent turn, and a second interruption. |

One finding deserves emphasis. **Today's route 2, "plan approval is user approval",
grants no real authorization for roughly three quarters of plans**, because those plans
are approved automatically. A memory step written into an `%auto` plan is never seen
by a human. The feature closes a policy gap that exists right now, beyond the
convenience it adds.

---

## 3. Critique: is this a good idea?

**Yes.** Every report agreed, and the evidence above supports it.

### Why it is right

1. **One review instead of two.** A pre-plan question costs an agent turn and an
   interruption, and the human answers without seeing the plan. A decision rides
   along with the plan and has a default already filled in.
2. **The answer becomes part of the plan.** It sits in the archived plan, next to the
   question and the planner's recommended default, and it can be diffed and audited.
3. **It removes three failure modes:** guessing, blocking, and optional work buried in
   prose (`grk`).
4. **It turns memory consent into a structured default-deny.** A plan with no memory
   decision authorizes no memory edits, so the 65 hand-written disclaimers become
   unnecessary.
5. **It fits the architecture.** It adds zero new gates and zero new family members
   (`decisions:gates-never-block`, `decisions:single-turn-agents`), and the host still
   owns completion.

### Risks, and what answers each one

| Risk | Answer |
| --- | --- |
| **Plans that branch on everything.** Lazy planners hand their judgment to the reviewer. | A cap of 5. A `default` is required on every decision. A skill rule says to embed a decision only when you would defend the default yourself (§6.2). |
| **Rubber-stamping.** Most approvals take the defaults. | Memory defaults are verified mechanically. `default` sits next to `answer` in the archive, so the override rate measures how well planners choose defaults. The `%auto` notification lists the decisions it took. |
| **Combinatorial plans.** Five toggles allow 32 combinations (`cdx`). | Decisions must be local. Each one must be referenced in the body, which the validator warns about. Anything that changes the tier, the phase graph, or the architecture goes to `/sase_questions`. |
| **Stale schema after an in-review edit.** | Freeze the decision set for the review. Changing the set goes through feedback and a replan. |
| **Surfaces that lag.** | An omitted value means the default, so an old surface still settles correctly. Telegram gets a summary of the decisions in the message text from day one. |
| **Policy without teeth.** | A finalizer guard, phased in later. Be honest about its limit: it stops unauthorized memory changes from being published, but it does not stop an agent from writing the file (`cdx`). |

---

## 4. Adjustments to the requirements (called out explicitly)

**A1. Embed "gate options" as typed decisions, not gate options.**
- **What changes:** frontmatter declares choices. The host compiles them into typed
  inputs on the existing `approve` option. Frontmatter never contains a `query`,
  `command`, `resources`, `groups`, or `turn` block.
- **Why:** the reasons in §1 — the plan gate contract is sealed, AND groups accept any
  subset, routing keys would multiply by 2ⁿ, and the query grammar cannot express
  "approve and pick exactly one of {A, B}".
- **Effect on you:** none visible. You still get ☑️/⬜ toggles in the same modal.

**A2. Every decision must declare a default; no decision can block `%auto`.**
- **Why:** 73–82% of plan approvals are automatic, and question gates already
  auto-answer with their first option.
- **The planner's rule:** if you cannot name a default you would defend, ask now with
  `/sase_questions`.
- **Disagreement:** `cdx` and `mus` wanted required decisions that block `%auto`;
  `cld` and `grk` did not. I side with `cld` and `grk`.

**A3. "Default on iff the user explicitly requested it" becomes a checkable
attestation.**
- **The rule:** a memory decision may default to `true` only with a `requested:` quote.
- **The check:** the host matches the quote word for word against **text a human
  wrote** in the plan chain: the original human prompt, feedback bullets, and Q&A
  answers. It never matches against prompts written by agents.
- **When it runs:** at `propose`, which fails with a fixable error while the planner is
  still alive, and again when the gate is built, which fails closed by forcing the
  default to off and flagging the review.
- **What this does not do:** it cannot detect intent from the prompt; `mus` and `grk`
  were right that nobody can. A planner-asserted `requested_by_user: true` also counts
  for nothing (`cdx`).

**A4. Scope "all memory changes must be planned" to plan-driven work.**
- **Plans:** any plan, tale or epic, that changes memory must cover every changed note
  with a memory decision. Plan approval alone no longer authorizes memory changes.
- **Direct requests stay valid:** a specific instruction in the human's current
  prompt, such as "add X to the tui note", still authorizes an agent that is not
  planning.
- **Why:** that prompt is already the human gate. Forcing a plan there turns one turn
  into three (planner → gate → coder) and adds no information.
- **Your call:** zero exceptions is available as a later switch (§9).

**A5. Epic phase graphs stay fixed in v1.**
- **What changes:** decisions apply to the whole plan and reach every phase through
  EPIC PLAN.
- **What waits:** `phases[].when:` (from `cld`) is reserved. The v1 validator rejects
  it with a "reserved" diagnostic.
- **Why:** skipping phases changes dependencies, waves, resume, and the land agent. In
  recent epics, memory work rides inside documentation or policy phases alongside
  other work, so the decision boundary rarely matches a phase boundary. Four of five
  reports chose a fixed graph.

**A6. Freeze the decision set for one review.**
- **What changes:** an in-gate edit may change prose or the wording of an `ask`. It may
  not change ids, kinds, choice keys, or memory scope. Changing those goes through
  feedback and a replan.

**A7. Memory scope uses `sase memory read` selectors, not a blanket `sase/memory/**`.**
- **Why:** the reviewer sees exactly which notes are covered, and the guard can check
  them.

**A8. Ship behind a beta flag until ACE, Telegram, and `%auto` default resolution have
soaked (`grk`).**
- **Then:** remove the flag and delete the old code path. This is not a permanent
  configuration knob.

---

## 5. Where the reports disagreed, and the resolution

| Question | cdx | cld | grk | mus | gem | **Resolution** |
| --- | --- | --- | --- | --- | --- | --- |
| Mechanism | Inputs on `approve` | Inputs on `approve` | Inputs on `approve` | Synthesized section in the review plus the Q&A merge path | **Extra AND members** | **Inputs on `approve`** (and on tale `commit`, which shares inputs). gem's AND design allows approval-less subsets, multiplies routing keys by 2ⁿ, and cannot express exclusive choices. |
| Key name | `approval.decisions` | `decisions:` map | `gates:` + `memory:` | `gates:` | `gate_options:` | **`decisions:` map** (§6.1). `gates` promises gates that do not exist, and `gate_options` names the mechanism this design rejects. |
| Required, no default? | Allowed; blocks `%auto` | Default required | Default required | `required: true` | Default required | **Default required** (A2). |
| Memory default verification | Host attaches evidence | Word-for-word quote check | Quote required, not checked | Warning cross-check | Vague host check | **Word-for-word check against human-written text**, fail closed (A3). grk's unchecked quote only helps when a human looks, and in 73% of cases none does. |
| Memory under `%auto` | Always held for a human | Verified default applies | Default applies | Never auto-answer | Always off | **Verified default applies.** Holding for a human would stall a plan the user asked to run unattended. Treating a verified `true` as `false` would contradict the user's own request. The `%auto` notification shows what was decided. |
| Where answers live | Host receipt only; never in the file | `answer:` in the archived plan | `selected:` in the archived plan | Response plus plan record | `gate_selections:` in the plan | **Both.** The gate response and receipt are authoritative. `answer:` in the archived plan is the projection implementers read. Authoring mode forbids `answer:`, which addresses cdx's forgery concern. |
| Edit during review | Recompile | Freeze | Freeze | — | — | **Freeze** (A6). |
| Epic phases | Fixed | `when:` skips phases | Fixed | Fixed (v2: scoping by phase) | Fixed | **Fixed; reserve `when:`** (A5). |
| Memory touched with no decision | — | Heuristic warning | — | Auto-inject a default-off confirm | Hard error | **Warning at propose; precise check in the finalizer guard.** A hard error or auto-injection would trip on the many plans that only reference memory or say "do not edit memory". |
| Declined memory change | — | No auto-bead | Coder files a memory bead | — | Coder prohibited | **Split by who decided.** If `decided_by: auto` left an unrequested change off, the coder files a `memory` task bead through `/sase_new_task`, because no human saw it. If a human turned it off, file nothing. |

---

## 6. Recommended design: Plan Decisions

### 6.1 Authoring grammar

`decisions:` is an optional top-level map keyed by decision id, valid on tales and
epics. sase-core rejects duplicate ids, and YAML map order is preserved. The kind is
inferred: a decision with `choices:` is a **choice**, and one without is a **toggle**.
That removes the need for a `type:` key, which is easy to get wrong.

| Field | Rule |
| --- | --- |
| id (map key) | `^[a-z][a-z0-9_]*$`, at most 32 characters, at most **5** decisions. Must not use a name already taken by an approval input or option (`approve`, `commit`, `reject`, `feedback`, `coder_prompt`, `coder_model`, `wait`, `epic_launch_mode`, `capacity`). |
| `ask` | Required. One line, at most 120 characters. A warning fires if it does not end in `?`. Phrase a toggle so that **yes means do the work**. |
| `choices` | Choices only. 2–5 entries mapping a slug key to a one-line consequence of at most 100 characters. Five matches what ACE's enum control cycles through in place. |
| `default` | **Required.** A toggle takes the YAML booleans `true` or `false`; `yes`/`on` are rejected because YAML 1.1 and 1.2 disagree about them. A choice takes one of its keys. |
| `memory` | Toggles only. A non-empty list of memory selectors (`tui.md`, `glossary:plan-decision`, `decisions:<slug>`). It marks a **memory decision**. Existing notes resolve as edits. Missing strands or notes are allowed and are shown as **new**. |
| `requested` | A one-line quote of the human's words. **Required when a memory decision defaults to `true`.** Verified per A3. |
| `answer` | **System-managed.** Forbidden in Authoring mode and written at approval (§6.6). |

**Validator warnings.** These do not fail validation.

- A decision id is never mentioned in the plan body. This suggests the planner did not
  describe both branches.
- The body appears to edit a `sase/memory/` path, but no memory decision covers it.
- An `ask` has no `?`.

**Epics.** `phases[].when` is reserved, as described in A5.

### 6.2 When to embed a decision and when to ask now

This rule goes into `/sase_plan`:

> **Ask now** (`/sase_questions`) when the answer changes what you would write: the
> tier, the size, the phase graph, or the architecture. **Embed a decision** when you can
> write one complete plan that covers every answer, the difference is local (a step, a
> section, a parameter), and you would defend your default. Never embed a decision you
> should make yourself.

GitHub's Spec Kit uses the same split in `/speckit.clarify`. Critical and high-impact
ambiguities are asked before planning. Medium and low ones become recorded
assumptions. Plan decisions are recorded assumptions that the reviewer can flip.

This rule goes into `/sase_memory_write`, replacing "confirm with `/sase_questions`
before propose":

> Every memory change a plan makes is a **memory decision**. Default it to `true` only
> when the user asked, and quote their words in `requested:`; otherwise `false`. Describe
> each change in the plan body. Do not add "do not edit memory" prose: a plan with no
> memory decision authorizes none.

### 6.3 Compiling decisions into the gate

1. **Payload.** `payload.decisions` holds the normalized, frozen list: id, kind, ask,
   choices, default, memory selectors with their resolved note type, `requested`, and
   `requested_verified`.
2. **Inputs.** Each decision becomes a declared, non-required input with its default.
   A toggle becomes `bool` and a choice becomes `enum`, with a label equal to its
   consequence. The input goes on tale `approve` and `commit` and on epic `approve`.
   - **Wire names:** use internal names such as `decision_<id>`, so they can never
     collide with host fields.
   - **Collection:** the shared-id collection already handles the tale AND pair.
   - **Settle in the gate phase:** whether plan options move from raw `input_schema` to
     declared `inputs`, or merge the two.
3. **Resolution.**
   - **Where:** the approve command calls one sase-core function. It combines the
     submitted values with the defaults and applies the verification rule for memory
     defaults.
   - **What it records:** the result schema gains a **required**, fully resolved
     `decisions` object, so `response.json` records every value explicitly. Omitted
     inputs therefore still settle under `%auto`, Enter, and older clients.
4. **Kind validation.** Add one check: the inputs derived from `payload.decisions` must
   equal the declared inputs. That prevents a forged request from drifting from its own
   payload. The query, options, commands, and groups stay exactly as they are.
5. **Receipts.** Decision receipts already bind the identity of option inputs. Decisions
   that travel through `option_inputs` are bound to the reviewed request hash at no
   extra cost.

### 6.4 The review experience (the beauty layer)

**ACE Plan Review modal.** A new **Decisions** section sits above the renamed
**Verdict** section:

```
┌ Plan Review · claude/opus ──────────────────────────────────────────────────────┐
│ ✏️  Edit plan                       e │ sase_plan_keymap_help_overlay.md         │
│                                       │ ---                                      │
│ Decisions                     2 · 🧠  │ tier: tale                               │
│ ◆  Grouping             ‹ mode ›  •   │ title: Keymap help overlay               │
│      By leader mode; denser           │ …                                        │
│ ☑️ 🧠 Record keymap conventions        │ ## Grouping                              │
│      tui.md · reference · ✓ requested │ …                                        │
│                                       │                                          │
│ Verdict                               │                                          │
│ ☑️ 🚀 Launch coder agent               │                                          │
│ ☑️ 💾 Commit plan file                 │                                          │
│ 1 ✅ Tale   2 ❌ Reject   3 💬 Feedback │                                          │
│ → coder · grouping=mode · edit tui.md │                                          │
└───────────────────────────────────────┴──────────────────────────────────────────┘
  Enter Tale · Space toggle/cycle · j/k move · e edit · c custom · 1–3 submit
```

**Controls:**

- Toggles use the existing ☑️/⬜ glyphs. Choices use the `_EnumField` control that
  cycles in place.
- The focused row shows its consequence line, dimmed.
- A value changed from its default gets a `•` and the accent colour.

**Memory rows:**

- Each row shows 🧠, the note selectors, and the note type. `core` costs context on
  every turn and `reference` does not, which is worth knowing at a glance.
- A provenance chip shows `✓ requested`, `not requested` (dimmed), or
  `⚠ request not found`.

**The outcome line (from `cdx`).** One live sentence above the submit row
("→ coder · grouping=mode · edit tui.md") catches mistaken defaults before you press
Enter.

**Enter submits the values shown.** Accepting the defaults stays one keystroke. Add any
new keybindings to `src/sase/default_config.yml`.

**Generic fix.** Give typed `bool` inputs a real toggle widget in `TypedInputForm`.

**Telegram.** The approval message lists the decisions and their current values. The
first button is **✅ Approve as shown**, which submits nothing for decisions, so the
defaults apply. A second button, **🎛 Change decisions**, enters the existing step flow,
which already supports enum keyboards and skip-to-default. Add a yes/no keyboard for
`bool` there. Do not force every approval through N steps.

**CLI.**

- `sase plan approve keymap_help_overlay -D grouping=mode -D tui_note=no` (`-D` is
  `--decide` and is repeatable). Unknown ids or values fail before any side effect and
  list the allowed values. `--dry-run` prints the resolved decisions.
- `sase plan show` gains a Decisions table with the columns id, ask, default, and answer.
- Read the `cli_rules` reference note before adding the flag.

**Notifications.** Use the existing count channel, for example
`Tale ready · 2 decisions · 🧠`. An auto-resolved plan's notification lists each
decision taken and marks it `auto`.

### 6.5 Edits and feedback

- **In-gate edit.** `validate_edited_resource` compares the edited plan's decision set
  with `payload.decisions`. If the set changed, it refuses with: "Decisions are fixed
  for this review — toggle them in the Decisions panel, or send feedback to change
  the set."
- **Feedback.** The `feedback` option also accepts provisional decision values. The
  replan prompt then includes "you changed `tui_note` → no", and the replanner treats
  those values as the new defaults (`cld`).

### 6.6 Recording the answers

The approve command already sits where the reviewed plan, the inputs, and the archive
write meet. Before it syncs and archives, it stamps the resolved values into the
plan's frontmatter:

```yaml
decisions:
  grouping:
    ask: How should the overlay group bindings?
    choices:
      pane: By pane, matching the footer hints
      mode: By leader mode; denser, but splits pane actions
    default: pane
    answer: mode
  tui_note:
    ask: Record the overlay's keymap conventions in the tui memory note?
    memory: [tui.md]
    requested: "and note the convention in the tui memory"
    default: true
    answer: true
decided_by: reviewer        # reviewer | auto | cli
```

- **Answers are immutable.** Relaunching a failed coder with `sase plan approve` reuses
  them. Changing them requires a new review.
- **Commit-only and approve-only tales** also stamp their answers, so a coder launched
  later sees them.
- **Epics** stamp before the launch monitor runs `sase bead work`, so the archive and
  the phase beads see the answers.
- **Direct routes** (`sase plan approve <file>` with no live gate, or a hand-run
  `sase bead work`) resolve through the same sase-core function. A memory `true`
  requires either a verified quote or an explicit `-D` from a human shell. An agent
  process cannot submit `-D <memory>=yes`.
- **Precedent.** This mirrors Copier: the template stays pristine and the answers are
  recorded with the generated output. Here, the authored proposal plays the template
  and the archived, approved plan plays the output.

### 6.7 How implementers consume the answers

**Tale coder.** The host appends a short block after "Implement it now." It contains
only enum keys and booleans, and `ask` text appears as quoted data, so nothing
free-form is interpolated:

```
Reviewer decisions for this plan (final):
- grouping — "How should the overlay group bindings?" → mode (you recommended pane).
- tui_note — "Record the overlay's keymap conventions in the tui memory note?" → yes.
  Memory edits are authorized for: tui.md. No other memory note.
Implement only the branch each answer selects.
```

**Epic.**

- `sase bead read` gains a **DECISIONS** section for epic and phase beads, read from
  the archived plan.
- `bd/work_phase_bead` and `bd/land_epic` gain one sentence: "Honor the epic's DECISIONS
  shown by `sase bead read`."

**Memory authorization.** `/sase_memory_write` route 2 becomes: "an approved plan's
memory decision that covers the note was answered `true`."

### 6.8 `%auto`

- **Behavior.** `%auto` takes every default. A memory default can be `true` only if its
  quote was verified, so unattended runs edit memory only when the human asked.
- **Visibility.** The notification records `decided_by: auto` and the values taken.
- **Declined changes.** An unrequested memory change that `%auto` left off becomes a
  `memory` task bead (§5).
- **What `%auto` does not get.** No per-decision override language. If a later `%auto`
  redesign wants one, it can read `payload.decisions` (`grk`).

### 6.9 Enforcement backstop (later phase, beta flag)

- **What it checks.** A commit-finalizer guard runs for agents launched from an
  approved plan (coder, phase, and land agents). Every changed memory path must be
  covered by a memory decision answered `true`. That includes project
  `sase/memory/**`, home memory, and the regenerated `AGENTS.md` and provider shims,
  which count only as derived from a covered note.
- **Rollout.** Advisory first, as a warning in the declaration. Enforcing after a soak
  period, when the finalizer refuses with the uncovered notes listed.
- **What it promises.** Unauthorized memory changes cannot be **published**. It cannot
  stop an agent from writing the file, and it cannot prove that the prose matches the
  `ask`. Say exactly that (`cdx`).

---

## 7. Alternatives considered and rejected

| Approach | Why not |
| --- | --- |
| Full custom-gate JSON in frontmatter | Puts executable commands in Markdown, effectively a sudo vector. It would duplicate about 40 gate rules and turn a dozen readable keys into about 80 lines of JSON. |
| Extending the AND group (`(approve AND commit AND memory)`) | Allows approval-less subsets, needs 2ⁿ routing keys, expresses only yes/no, and breaks kind validation. |
| A separate gate after approval, one per decision | N interruptions, which breaks the single review. |
| Body checklists toggled with `edit_plan` | Untyped, cannot be used from Telegram, and has no `%auto` behavior. Its best idea, that the file records the answer, is kept. |
| `/sase_questions` before propose (status quo) | Costs an extra turn and interruption. The human answers without seeing the plan, and `%auto` takes the first option rather than the recommended one. Keep it only for questions that block planning. |
| Questions asked by the coder mid-run | Keeps the latency and has less context. Keep it only as a fallback for questions that genuinely arise during implementation. |
| Rebuilding the decision schema after each edit | Needs schema-rebuild and re-hash machinery for an edge case that feedback already covers. |
| Host language analysis to detect "requested" | Errs in both directions. A checked quote is better. |

---

## 8. Implementation shape

This is an epic. The Rust boundary applies: parsing, validation, resolution, quote
verification, and later guard matching belong in sase-core. Python adapts and
orchestrates, and ACE and Telegram render.

| Phase | Work | Depends on | Size |
| --- | --- | --- | --- |
| `core` | sase-core: the `decisions` schema and diagnostics. Authoring forbids `answer`/`decided_by`, and `when` is reserved. Resolve, apply-to-content, and verify-quote APIs. Wire changes. A plan-wire version bump if the exact-match adapter requires one. | — | large |
| `gate` | Move the `sase-core-revision.txt` pin. Python wire. Payload and declared inputs. Kind-validation equality check. Resolution and stamping in the approve command. Edit freeze. Feedback carry. Verification at propose and at gate build. Direct routes. | `core` | large |
| `consumers` | Coder prompt block. DECISIONS in `bead read` plus the macro sentences. `sase plan approve -D`. `sase plan show`. `%auto` notification text. | `gate` | medium |
| `surfaces` | ACE Decisions section, Verdict rename, outcome line, bool toggle, toast counts. Telegram decision summary, "Approve as shown", bool keyboard (follow-up bead in sase-telegram). | `gate` | medium |
| `policy` | The `/sase_plan` and `/sase_memory_write` skill templates (generated skills), `docs/sdd.md`, `docs/notifications.md`, and a **Plan Decision** glossary strand. The strand is itself a memory change, so it needs your sign-off, which makes it a good first use of the feature. | `consumers`, `surfaces` | small |
| `guard` | A finalizer memory guard behind a beta flag: advisory first, then enforcing. | `policy` | medium |

`policy` lands last on purpose. Agents start writing decisions only once every surface
you use can show and change them. Until then, older surfaces still settle correctly,
because an omitted value means its default.

Implementers must first read the `cli_rules`, `tui`, `generated_skills`, `sase_flags`,
and `lint_and_test` reference notes. I did not read those notes for this report.

---

## 9. Open questions for you

1. **Direct-prompt memory edits (A4).**
   - **Recommended:** keep the direct path for explicit, specific instructions in the
     current human prompt.
   - **Alternative:** require a plan for every memory change, with no exceptions,
     enforced by the guard.
2. **Memory under `%auto` (§5).**
   - **Recommended:** let a verified `requested` default apply.
   - **Alternative (`cdx`):** hold every memory-bearing plan for a human.
3. **Bead route.** Route 3 ("a bead you were asked to work describes it") still lets an
   agent-filed memory bead authorize an edit during automated bead work. Should beads
   worked plan-first follow this feature's rules too? Recommended: yes.
4. **The name.**
   - **Recommended:** `decisions:` with `ask`/`default`/`answer`, and the glossary term
     "Plan Decision". "Decision" is already used for the decision-record web and gate
     decisions; both are in different namespaces.
   - **Runner-up:** `questions:`, which matches `/sase_questions` but reads oddly for
     consents.
5. **Guard strictness.** In enforcing mode, should the guard fail the whole commit, or
   commit everything except the uncovered memory paths?

---

## 10. Recommended solution

**Ship Plan Decisions.**

1. **Author.**
   - An optional `decisions:` map in tale and epic frontmatter: at most five decisions,
     each a toggle or a 2–5-way choice, each with a required `default`.
   - Memory decisions add `memory:` selectors. To default on, they need a `requested:`
     quote of the human's words.
   - The plan body describes every branch.
2. **Validate in sase-core.**
   - Strict schema, caps, and authoring-forbidden `answer`.
   - The quote is checked against text a human wrote, at propose and again at gate
     build. An unverified `true` is forced off and flagged.
   - Warnings fire when a decision is not referenced in the body or when the body
     appears to edit memory with no decision covering it.
3. **Review in one place.**
   - Decisions compile into typed inputs on the existing approve option. The query,
     commands, and groups stay sealed.
   - ACE shows an always-visible Decisions section with an outcome line. Telegram
     offers "Approve as shown" plus a typed step flow. The CLI gains `-D`.
   - Enter, `%auto`, and older surfaces take the defaults.
   - The decision set is frozen for one review; feedback can change it.
4. **Record once, project once.**
   - The gate response and receipt are authoritative.
   - The approve command stamps `answer:` and `decided_by:` into the plan before it is
     archived, so the archive is the durable, readable record of question,
     recommendation, and answer.
5. **Consume mechanically.**
   - The tale coder gets a host-written "Reviewer decisions" block.
   - Epic phases and the land agent see DECISIONS through `sase bead read`.
   - `/sase_memory_write` treats an accepted memory decision as the only
     plan-based authorization.
   - The epic graph stays fixed in v1, with `when:` reserved.
6. **Enforce later.** A beta-flagged finalizer guard, advisory then enforcing, checks
   memory diffs against accepted memory decisions.

Together this is:

- **Intuitive:** YAML no heavier than `phases:`, a planner rule you can state in a
  sentence, and the controls you already know.
- **Reliable:** sealed commands, defaults that always settle, a frozen set, answers
  stamped in two places, verified memory consent, and a guard.
- **Beautiful:** one review, one Decisions panel, one outcome sentence, and one
  archived plan that tells the whole story.

---

## Sources

**Swarm reports in this directory:**

- `plan_frontmatter_decisions__cdx.md`
- `plan_frontmatter_decisions__cld.md`
- `plan_frontmatter_decisions__grk.md`
- `plan_frontmatter_decisions__mus.md`
- `plan_frontmatter_decisions__gem.md`

**Internal sources I verified:**

- **sase:**
  - Plan gate: `src/sase/plan_gate.py`, `src/sase/plan_gate_turn/create.py`
  - Gate machinery: `src/sase/notification_gates/{selection.py,adapters.py,kind_validation/plan.py,model_inputs.py,input_collection.py}`
  - Questions: `src/sase/user_question_actions.py`
  - ACE: `src/sase/ace/tui/modals/{plan_approval_modal.py,plan_approval_gate_data.py,plan_approval_decisions.py}`, `src/sase/ace/tui/widgets/typed_input_form.py`
  - Handoff and beads: `src/sase/axe/run_agent_exec_plan_accept.py`, `src/sase/bead/{epic_from_plan.py,cli_detail_resolution.py}`
  - Skills: `src/sase/macros/skills/{sase_memory_write.md,sase_run.md}`
  - CLI: `sase plan approve --help`, `sase memory read --help`
- **sase-core:** `crates/sase_core/src/plan/validate.rs`, plus a duplicate-key
  reproduction through `sase plan validate`.
- **sase-telegram:** `src/sase_telegram/{gate_inputs.py,formatting.py,inbound_handlers/gate_input_steps.py}`
- **Data:** `~/.sase/interaction_requests/{plan,epic_plan,question}/*/response.json`
  and the plans sidecar for 2026-08 through 2026-10.

**External analogs:**

- [Copier: configuring a template](https://copier.readthedocs.io/en/v9.3.0/configuring/).
  Typed questions with `choices` and `default`, and answers recorded with the generated
  output in `.copier-answers.yml`.
- [GitHub Spec Kit: clarify workflow](https://github.com/github/spec-kit/pull/1238) and
  a [summary of `/speckit.clarify`](https://skills.sh/dceoy/speckit-agent-skills/speckit-clarify).
  Critical and high ambiguities are asked before planning; medium and low ones become
  recorded assumptions.
- [GitHub issue forms syntax](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms)
  (via `grk`). The complexity ceiling for forms written in YAML.
- [GOV.UK checkboxes](https://design-system.service.gov.uk/components/checkboxes/) and
  [radios](https://design-system.service.gov.uk/components/radios/) (via `cdx`). Radios
  for one choice, checkboxes for toggles, and caution about preselecting.
- [Terraform apply with a saved plan](https://developer.hashicorp.com/terraform/cli/commands/apply)
  (via `cdx`). Execute the frozen configuration that was reviewed.
- [Argo intermediate inputs](https://argo-workflows.readthedocs.io/en/latest/intermediate-inputs/)
  (via `cdx`). A typed human decision value feeds downstream steps.
- [W3C: grouping form controls](https://www.w3.org/WAI/tutorials/forms/grouping/)
  (via `cdx`).
