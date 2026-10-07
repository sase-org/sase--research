# Plan Decisions: Embedding Gate Choices in Tale and Epic Frontmatter (cld)

_Researcher: cld · 2026-10-07 · Scope: how SASE plans, plan-approval gates, coder and
epic-phase handoffs, and the memory-write policy work today; a critique of the request
to embed sase gate options in plan frontmatter; and a recommended design._

---

## TL;DR

- **The idea is good, and the evidence supports it.** Today a planner that needs one
  answer from you before proposing must open a `/sase_questions` gate. That ends its
  turn and costs a whole extra agent turn, which re-finalizes the plan and proposes
  it. The one memory-consent question on this host says exactly that: _"Whichever you
  choose, the follow-up agent will finalize the plan and run sase plan propose."_
  Folding such questions into the plan review you already do saves one agent turn and
  one interruption per question. It also makes the answer a durable part of the
  archived plan.
- **Reframe the requirement: these are gate _inputs_, not gate _options_.** In SASE a
  gate option is a command-backed branch of the gate's query. The plan gate's query is
  pinned by kind validation (`kind_validation/plan.py:47-68`). The gate turn routes
  follow-ups by the exact selected-option key (`approve+commit`, `approve`, `commit`;
  `plan_gate_turn/create.py:62-72`). Adding a toggle as an extra AND member would:
  - multiply those keys by 2ⁿ;
  - let a reviewer submit "memory only" without approving;
  - only ever express yes/no.

  What you want is **typed parameters of the approve branch**: yes/no toggles and
  single-choice selections, each with a default. The gate system already has that
  vocabulary.
- **Every decision must carry a default.** About 75% of plan approvals on this host
  never meet a human:
  - **Tales:** 143 of 197 retained responses were `auto_resolution`, 42 came from the
    TUI and 12 from the CLI.
  - **Epics:** 75 of 92 were auto-resolved.

  Defaults are therefore the main path, not a fallback. If a value is omitted, the
  default applies. That one rule covers Enter, `%auto`, and surfaces that don't render
  decisions yet (Telegram, mobile).
- **Make "default on iff explicitly requested" checkable by a machine.**
  - A memory decision may default to `true` only with a `requested:` quote.
  - SASE checks that the quote appears word for word in the planner's prompt, feedback,
    or Q&A answers.
  - If the quote is missing, the default is forced off and the review shows a warning.
  - Today memory authorization is enforced only by skill text. Nothing in code inspects
    memory diffs (`sase_memory_write.md:19-40`; no matches in `src/sase/finalizers`).
- **Epics get `phases[].when:`.** A phase gated on a declined decision is never
  created. A memory change then has to be agreed to before work starts; nobody relies
  on N phase agents reading and following an answer.
- **The plan file stays the only handoff.** Answers are written back into the archived
  frontmatter as `answer:`. Each decision then sits in one durable, diffable file with
  its question, the planner's default, and your answer. The coder prompt gets a short
  "Reviewer decisions" block. Phase agents see the answers through `sase bead read`.
- **Recommendation:** ship **Plan Decisions**.
  - **Frontmatter:** an optional `decisions:` map (at most five; toggle or choice; a
    required `default`; optional `memory:` and `requested:`), plus `phases[].when:`.
  - **Schema:** validated in `sase-core`.
  - **Gate:** compiled into one typed `decisions` input on the approve option.
  - **TUI:** rendered inline in the Plan Review modal.
  - **Downstream:** written back into the archived plan and passed to the coder.
  - **Backstop:** an optional finalizer guard, behind a beta flag.

  Details are in §6 and §8.

---

## 1. What exists today

### 1.1 The plan frontmatter schema lives in Rust and is closed

- `sase plan validate` delegates to `sase_core_rs.plan_validate`
  (`src/sase/sdd/plan_validate.py:1-6, 94-111`).
- The allowed keys are fixed in `sase-core` (`crates/sase_core/src/plan/validate.rs:24-39`):

  | Group     | Keys                                                                   |
  | --------- | ---------------------------------------------------------------------- |
  | Common    | `tier`, `title`, `goal`, `model`                                       |
  | Tale      | `size`                                                                 |
  | Transient | `links`                                                                |
  | System    | `create_time`, `status`, `prompt`, `bead`, `proposed_by`, `parent`, `bead_id` |
  | Epic      | `phases`, `patch`, `changespec`, `bug_id`, `parent_bead`               |
  | Phase     | `id`, `title`, `depends_on`, `description`, `size`, `model`            |

- Any other key is an `unknown-key` **error**.
- So any new field has to start in `sase-core`. That matches the project rule that
  shared domain behavior belongs in the Rust core.
- Python reads a `ValidatedPlanWire` with `PLAN_WIRE_SCHEMA_VERSION = 3`.
- There are two validation modes, `Authoring` and `Launch` (`validate.rs:75-80`). That
  is the natural place to forbid a system-written `answer:` while authoring and allow it
  in archived plans.
- Precedents for both directions already exist:
  - SASE writes system fields into frontmatter (`create_time`, `status`, `bead_id`).
  - SASE consumes a transient authoring field (`links:`).

### 1.2 The plan gate is fixed, but its inputs are open

- `build_plan_approval_gate_spec` (`src/sase/plan_gate.py`) builds the gate. Its query
  is `(approve AND commit) OR reject OR feedback` for tales and
  `approve OR reject OR feedback` for epics.
- Kind validation pins:
  - the query and branches;
  - the option commands (`kind_validation/plan.py:47-68`);
  - the tale submit group;
  - the `edit_plan` operation;
  - the command scripts;
  - the turn block.
- It does **not** pin `input_schema`. A new input on the approve option passes plan
  kind validation; a new option does not.
- Tale `approve` and `commit` already take approval-time inputs: `coder_prompt`,
  `coder_model`, `wait`. Epic `approve` takes `epic_launch_mode`, `wait`, `capacity`
  (`plan_gate.py:240-272`).
- Those inputs travel this path to the next agent:
  1. the option command (`_plan_gate_command.py`);
  2. `translate_plan_gate_response` (`_plan_gate_envelope.py:59-164`);
  3. `PlanApprovalResult`;
  4. the successor prompt (`run_agent_exec_plan_accept.py:528-567`).

  **That chain is the exact precedent for decisions.** The difference is that today's
  inputs are free text, and decisions would be typed and declared by the plan.
- Every selected option receives the same input. Both AND-group members therefore have
  to admit an approve field (comment at `plan_gate.py:253-254`).
- `%auto` fills plan inputs through `automatic_input` (`notification_gates/adapters.py:334-349`):
  - for tales it supplies `{}`;
  - for epics it supplies `{"epic_launch_mode": "launch"}`.

  Treating an omitted value as its default therefore needs no change to `%auto`.

### 1.3 How approval reaches the implementers

- **Tale coder.** The prompt is built in `run_agent_exec_plan_accept.py:545-551`:

  ```python
  # The coder starts with a fresh context window; the approved plan file is
  # the hand-off artifact. It does not inherit the planner's chat.
  successor_prompt = (
      f"{model_prefix}{vcs_prefix}"
      f"@{coder_plan_ref}\n\n"
      "The above plan has been reviewed and approved. "
      f"Implement it now.{coder_extra}\n{embedded_refs}"
  )
  ```

  **The plan file is already the only handoff.** Decisions should reach the coder
  through it.

- **Epic phases.**
  - `sase bead work` archives the plan and creates phase beads in
    `bead/epic_from_plan.py:165-181`. It re-validates first at `:96`.
  - The `bd/work_phase_bead` macro tells each phase agent to run `sase bead read <id>`.
    That command shows the parent epic's `design` as **EPIC PLAN**
    (`bead/cli_detail_resolution.py:269-299`).
  - The `Issue` model has no free-form metadata, so the archived plan is the only place
    every phase agent and the land agent are sure to look.
- **Archive.**
  - `sdd/plan_archive.py:52-148` formats the plan, stamps `create_time`/`status`,
    validates it, and projects the header.
  - For tales, the approve option's command archives the plan in a leased workspace
    (`_plan_archive_approval.py`).
  - Before that, the reviewed bundle copy is synced back to the durable proposal
    (`_plan_approval_side_effects.py:80-102`).
  - **The approve command is the single moment where the answers, the reviewed plan,
    and the archive write all meet.**

### 1.4 Editing the plan inside the gate

- The `edit_plan` operation re-validates the edited origin and rolls it back on failure
  (`notification_gates/edits.py:91-197`).
- It does **not** rebuild the gate's options or input schema: `regenerate_previews` is a
  no-op (`adapters.py:330-332`).
- Any design that compiles decisions into the gate when it is created must either
  rebuild after an edit or freeze the decision set. §6.4 freezes it.

### 1.5 The review surfaces

- **`PlanApprovalModal`** (`ace/tui/modals/plan_approval_modal.py:151-199`):
  - Left column: gate actions (Edit plan), a section titled **"Decision"** holding the
    generic `GateBranchControls`, then Cancel.
  - Right side: the plan markdown.
  - AND members render as `☑️`/`⬜` toggles (`gate_branch_layout.py:72-81`).
- **Hidden fields.** The plan-specific inputs are deliberately hidden from the generic
  raw-schema YAML box through `HOST_COLLECTED_PROPERTIES`
  (`plan_approval_gate_data.py:38-51`). They are gathered by the bespoke "custom
  approval" modal on `c`.
- **Typed input widgets:**
  - an `enum` input renders as a button that cycles in place when there are ≤5 choices,
    and opens a picker when there are more;
  - a **`bool` input has no toggle widget**: it falls through to a plain text box
    (`ace/tui/widgets/typed_input_form.py:307-323`).

  That is a small, separate gap worth fixing either way.
- **Telegram and mobile** get the same normalized envelope through
  `sase gate show --json` and submit `option_inputs`. Their renderers live in other
  repos, so I could not confirm here whether they render typed inputs.

### 1.6 Memory policy today

`sase_memory_write.md:19-40` authorizes a memory edit only when one of these holds:

1. **The current prompt asks for it.**
2. **An approved plan names the change in its steps.** The skill puts it as "plan
   approval is user approval".
3. **A worked bead describes it.**

The two other routes:

- A plan whose memory changes the user did **not** ask for must
  _"Confirm with `/sase_questions` **before** `sase plan propose`"_.
- Anything else must become a `memory` task bead.

Nothing in code enforces this. The finalizers, `main/`, `Justfile`, and `tools/` have
no logic that inspects memory diffs. Whether the user "explicitly requested" a change is
left to the agent's judgment.

### 1.7 Usage evidence on this host

These counts come from `~/.sase/interaction_requests` (retained bundles only):

| Gate kind          | Responses | Auto-resolved | TUI | CLI/API | Non-default outcome         |
| ------------------ | --------- | ------------- | --- | ------- | --------------------------- |
| `plan` (tale)      | 197       | 143 (73%)     | 42  | 12      | 1 reject, 0 feedback        |
| `epic_plan`        | 92        | 75 (82%)      | 12  | 5       | 1 reject, 0 feedback        |
| `question`         | 3 settled | —             | —   | —       | 1 was the memory-consent Q  |

- An earlier, unrelated research report in this folder
  (`auto_directive_autonomy_profiles__cld.md`) found that about 70% of prompts carry
  `%auto`. The numbers above agree.
- **Implication:** whatever the planner writes as the default is what happens in roughly
  three out of four plans. The `default` rule carries the policy. The toggle is the
  override for the minority of plans a human actually reviews.

The memory-consent question in full:

> "The validated epic plan sase_plan_athena_agent_sync_repair.md is ready to propose,
> but one step writes SASE memory and needs your sign-off first: the v1-retirement phase
> would create a new decisions-web strand … Keep that step in the plan? Whichever you
> choose, the follow-up agent will finalize the plan and run sase plan propose."
>
> Options: Keep the decision record (recommended) · Drop it entirely · Defer via memory
> task bead. Answer: **Keep**.

This is your first use case almost word for word. Today it costs one question gate, one
extra agent turn, and a second interruption for the plan review.

---

## 2. Critique: is this a good idea?

**Yes.** I would build it, with the adjustments in §3.

### Why it is right

1. **It batches attention into a review you already do.** A question gate before the
   proposal is a second interruption that the plan review then repeats. A plan decision
   rides along with the plan, pre-answered.
2. **It removes a whole agent turn per pre-proposal question.** Single-turn agents make
   each question a handoff (`decisions:single-turn-agents`). A plan decision costs zero
   extra turns.
3. **It turns ephemeral answers into durable records.** A question gate's answer lives
   in a bundle and is folded into the next prompt. A decision answer lives in the
   archived plan, next to the question and the planner's recommendation.
4. **It behaves correctly under `%auto`.** Question gates auto-resolve to the **first**
   option (`user_question_actions.py:403-419`). Decisions resolve to the planner's
   **recommended** default, and memory defaults are off unless requested.

### Risks, and how the design answers them

| Risk | Mitigation |
| --- | --- |
| **Decision sprawl.** Planners push judgment calls onto you ("Add tests?"). | Cap of 5. A `default` is required. The skill says to decide anything you can defend yourself. |
| **Rubber-stamping.** Most approvals are auto or Enter, so a bad default quietly wins. | Memory defaults must be verified against your prompt. The archive keeps `default` and `answer`, so the override rate shows how well planners choose defaults. |
| **Branching plans confuse coders.** | Choices carry one-line consequences. A rendered "Reviewer decisions" block goes in the coder prompt. Epic `when:` makes phase gating mechanical. |
| **Edits make the gate's schema stale.** | Freeze the decision set during in-gate edits (§6.4). |
| **Surfaces lag.** Telegram and mobile don't render decisions yet. | An omitted value means the default, so old surfaces still approve correctly. |
| **Policy without teeth.** Agents can still edit memory outside a plan. | A finalizer guard as a later, flagged phase (§6.9). |

### What I would do differently from the literal request

I would not embed _gate options_, and I would not make "every memory change needs a
plan" absolute (§3, A1 and A4).

I also considered gating the memory _diff_ after implementation instead of the
_intent_ before it (§5). The intent gate is the right default. Diff review stays a
possible later complement for `type: core` notes only.

---

## 3. Adjustments to the requirements (called out explicitly)

**A1 — "Gate options" become typed "decisions" on the approval.**
- The request says "embed sase gate options". I recommend decisions that compile into
  one typed `decisions` input on the existing approve option.
- **Why:** options are mutually exclusive, command-backed outcomes. Decisions are
  parameters of one outcome (approve).
- **What changes for you:** nothing visible. Toggles still look like `☑️`/`⬜`, still
  "default on/off", and still sit in the same review modal.

**A2 — Every decision must declare a `default`.**
- No decision may require an answer.
- **Why:**
  - It keeps approval to one keystroke. Today 196 of 197 tale approvals take the
    default branch.
  - It keeps `%auto` total.
  - It degrades safely on surfaces that can't render decisions.
- **The boundary rule for planners:**
  - If you can't name a default you'd defend, the plan depends on the answer. Ask now
    with `/sase_questions`.
  - If you can write one complete plan that covers every answer, embed a decision.

**A3 — "Default on iff explicitly requested" is checked by a machine.**
- A memory decision may default to `true` only if it carries a `requested:` quote.
- SASE checks that quote, word for word, against the planner's original prompt plus
  all feedback bullets and Q&A answers in the plan chain.
- **When it checks:**
  - at `sase plan propose`, against the agent's `raw_prompt.md`, so the agent can fix
    the quote;
  - again when the gate is built, as defense in depth.
- **If the check fails:** the default is forced to `false` and the review shows
  "⚠ request not found".
- **Why:** the weak link today is the agent's judgment of "explicitly requested", and
  under `%auto` nobody is watching.

**A4 — Scope "all memory changes must be planned" to work that already runs through a
plan or bead.**
- **Plans:** any plan whose steps change memory must cover every change with a memory
  decision.
- **Plan-first beads:** a bead that is big enough to be worked plan-first follows the
  same rule.
- **A direct, specific instruction in the current prompt** ("add X to the tui note")
  stays a valid authorization for a non-planning agent.
- **Why:** that prompt is itself the human gate. Forcing a plan there turns one turn
  into three (planner → gate → coder) and adds no information.
- **If you want zero exceptions:** the same quote check (A3) can later be required in
  the final declaration of non-plan turns, and the guard (§6.9) can enforce it. Making
  that switch is your call; it's listed in §7.

**A5 — Epic phases can be conditional (`when:`).**
- This is not in the request.
- **Why:** without it, a declined memory decision in an epic relies on every phase agent
  reading the answer and doing nothing. With it, the phase never exists.
- It also lets planners split memory work into its own small phase, which is the
  pattern the skill should recommend.

**A6 — Decisions are frozen for the life of one review.**
- An in-gate edit may change prose but not the decision set.
- To change the set, send feedback; the replan then produces a new gate.
- **Why:** `edit_plan` does not rebuild the input schema (§1.4). A frozen set keeps the
  gate's typed contract honest without a schema-rebuild subsystem.

**A7 — Hard caps.**
- At most **5** decisions per plan, and **2–5** choices per choice decision.
- Each `ask` is one line of ≤120 characters.
- **Why:**
  - Five choices is exactly what the existing enum control cycles through in place.
  - Five decisions fit above the fold in the review column.
  - More than five means the plan's shape depends on them (see A2).

---

## 4. Naming

I recommend **`decisions:`** for the frontmatter key and **"Plan Decision"** for the
glossary term. Each decision has an **`ask`**, a **`default`**, and, once approved, an
**`answer`**.

| Candidate | Verdict |
| --- | --- |
| `gates:` | Misleading. These create no gates; they configure the one gate that already exists. |
| `options:` | Collides with gate options and with question options. |
| `questions:` | Defensible: they are deferred questions. But "Update the memory note?" reads like a consent rather than a question, and `questions.<id>.question` stutters. |
| `choices:` | Collides with the nested `choices:` of a choice decision. |
| `decisions:` | Reads naturally ("decisions for the reviewer"). The `ask`/`default`/`answer` trio is self-explanatory. |

`decisions:` has two collisions to manage:

1. **The `decisions` memory web** (ADR-style records). The contexts are distinct
   (frontmatter key vs. `sase memory read decisions:…`), and the glossary entry should
   say "not a decision record".
2. **The plan modal's existing "Decision" section title.** Rename that one to
   **"Verdict"** in the plan modal (approve / reject / feedback _is_ the verdict). The
   new section takes the title "Decisions".

---

## 5. Alternatives considered

| Approach | Verdict |
| --- | --- |
| **Status quo:** `/sase_questions` before propose | Costs an extra agent turn and interruption per question. The answer is not part of the plan. Auto picks the first option, not the recommended one. |
| **Literal AND-group options:** `(approve AND commit AND memory)` | Only booleans. Allows nonsense selections ("memory" alone). 2ⁿ turn-branch keys. Requires dynamic queries against pinned kind validation. **Rejected.** |
| **One gate per decision**, after approval | N interruptions. Breaks the "one review" story. **Rejected.** |
| **Checklists in the plan body**, toggled via `edit_plan` | No new UI and the file is the record, but toggling means editing a file. No typed validation. Impossible from Telegram or mobile. Fragile parsing. **Rejected**, but its best idea (the archived plan records the answers) is kept. |
| **Decisions as typed approval inputs, declared in frontmatter** | Reuses the inputs precedent and the plan-as-handoff architecture. Works with `%auto` and old surfaces. **Chosen.** |
| **Dynamic decision schema re-derived after every edit** | More flexible, but needs new schema-rebuild and re-hash machinery for an edge case that feedback already covers. **Rejected for v1** in favor of freezing (A6). |
| **Gate the memory diff after implementation** | Reviews the actual text, which matters most for `type: core` notes. But it adds a second interruption per change and a blocking handoff inside completion. **Deferred:** a possible later complement for core memory only. |

---

## 6. Recommended design: Plan Decisions

### 6.1 Authoring grammar

`decisions:` is an optional top-level map keyed by decision id. Mapping keys make ids
unique by construction, and `serde_yaml` and PyYAML both preserve order. There are two
shapes, inferred from the fields present, so no `type:` key is needed.

A tale with one memory toggle and one choice:

```yaml
---
tier: tale
title: Keymap help overlay
goal: Pressing ? in ACE shows every active binding, grouped for scanning.
size: small
decisions:
  memory:
    ask: Record the overlay's keymap conventions in the `tui` memory note?
    memory: [tui.md]
    requested: "and note the convention in the tui memory"
    default: true
  grouping:
    ask: How should the overlay group bindings?
    choices:
      pane: By pane, matching the footer hints (recommended)
      mode: By leader mode; denser, but splits pane actions
    default: pane
---
```

**Rules.** `sase-core` enforces these; `--explain` documents them.

| Field | Rule |
| --- | --- |
| id (map key) | Slug `^[a-z][a-z0-9_]*$`, ≤32 chars. At most 5 decisions. |
| `ask` | Required. One line, ≤120 chars. Should end in `?` (warning otherwise). A toggle's `ask` is phrased so **yes means do the work**. |
| `choices` | Optional. Present makes a **choice**; absent makes a **toggle**. 2–5 entries with slug keys; each value is a one-line consequence, ≤100 chars. |
| `default` | Required. A toggle takes `true`/`false` (YAML booleans; `yes`/`on` are rejected with a clear error, because YAML 1.1 and 1.2 disagree about them). A choice takes one of its keys. |
| `memory` | Optional, toggles only. Memory note paths relative to the memory root (`tui.md`, `decisions/<slug>.md`, `glossary/<slug>.md`). Marks a **memory decision**. |
| `requested` | Optional one-line quote of the user's words. **Required when a memory decision defaults to `true`.** Checked word for word (A3). |
| `answer` | **System-managed.** Forbidden in `Authoring` mode; written at approval (§6.6). |

**Epic phases** gain `when:`:

```yaml
phases:
  - id: retire_v1
    title: Retire the v1 import leg
    depends_on: [repair]
    size: medium
  - id: record
    title: Record the retirement decision record
    depends_on: [retire_v1]
    size: xsmall
    when: decision_record      # toggle shorthand for decision_record=true
```

`when` grammar: `<id>` or `<id>=<value>`. It must name a declared decision and a valid
value. More rules:

- **Error** if every phase is conditional; an epic needs at least one phase that always
  runs.
- **Warning** when an unconditional phase depends on a conditional one ("the dependency
  is dropped if `record` is skipped").
- **Warning** when an epic memory decision is never used in a `when:`. Memory work
  belongs in its own conditional phase.
- **Heuristic warning** when the plan body mentions a `sase/memory/` path that no memory
  decision covers.

### 6.2 When planners embed a decision versus ask now

This rule goes into the `/sase_plan` skill:

> **Ask now** (`/sase_questions`) when the answer changes what you would write: the
> tier, the phase graph, or the architecture. **Embed a decision** when you can write
> one complete plan that covers every answer, the difference is local (a step, a phase,
> a parameter), and you would defend your default. Never embed a decision you should
> make yourself.

And into `/sase_memory_write`, replacing the "confirm with `/sase_questions` before
propose" route:

> Every memory change a plan makes is a **memory decision**. Default it to `true` only
> when the user asked for it, and quote their words in `requested:`. Otherwise default
> it to `false`. In an epic, put the memory work in its own phase with `when:`.

### 6.3 Compiling decisions into the gate

The gate side of `sase-core` produces the decisions JSON schema, so every frontend
(including mobile, which lives in `sase-core`) validates against the same shape.

1. **Payload.** `payload.decisions` carries the normalized decisions, each with `id`,
   `kind` (`toggle`/`choice`), `ask`, `choices`, `default`, `memory`, `requested`, and
   `requested_verified`.
2. **Approve input.** Tale `approve` and `commit` (both, because every selected option
   receives the same input), and epic `approve`, gain one optional property:

   ```json
   "decisions": {
     "type": "object",
     "additionalProperties": false,
     "properties": {
       "memory":   { "type": "boolean" },
       "grouping": { "enum": ["pane", "mode"] }
     }
   }
   ```

   A missing key means "use the default". The gate executor's JSON-schema check rejects
   unknown ids and bad values before any command runs.
3. **Approve result.** The result schema gains a **required**, fully resolved
   `decisions` object. `response.json` therefore records every final answer
   explicitly, never only implicitly through defaults.
4. **Feedback.** The `feedback` option also accepts an optional `decisions` input. The
   replan prompt then includes the reviewer's provisional toggles ("you changed
   `memory` → no"). The replanner treats changed values as the new defaults.
5. **Host fields.** `HOST_COLLECTED_PROPERTIES` gains `decisions`, so the generic
   raw-YAML box never shows it.
6. **Kind validation** adds one check: the `decisions` input schema must equal the
   schema derived from `payload.decisions`. A hand-forged request can't drift from its
   own payload.
7. **`%auto`.** `automatic_input` is unchanged. Omission means defaults.

### 6.4 Edits and replans

- **In-gate edit.** `validate_edited_resource` additionally compares the edited plan's
  decision set with `payload.decisions`. If they differ, it refuses: _"Decisions are
  fixed for this review — toggle them in the Decisions panel, or send feedback to change
  the set."_ Prose edits keep working.
- **Replan via feedback** produces a fresh gate, with any newly authored decisions.

### 6.5 The review experience

The **Plan Review** modal's left column gains a **Decisions** section above the renamed
**Verdict** section:

```
┌ Plan Review  claude/opus ──────────────────────────────────────────────────┐
│ ✏️  Edit plan                    e │ sase_plan_keymap_help_overlay.md       │
│                                    │ ---                                    │
│ Decisions                          │ tier: tale                             │
│ ☑️ 🧠 Record keymap conventions    │ title: Keymap help overlay             │
│      tui.md · reference · requested│ …                                      │
│ ◆  Grouping            ‹ pane ›    │                                        │
│      By pane, matching the footer  │ # Plan: Keymap help overlay            │
│                                    │ …                                      │
│ Verdict                            │                                        │
│ ☑️ 🚀 Launch coder agent           │                                        │
│ ☑️ 💾 Commit plan file             │                                        │
│ 1 ✅ Tale                          │                                        │
│ 2 ❌ Reject    3 💬 Send Feedback  │                                        │
└────────────────────────────────────┴────────────────────────────────────────┘
  Enter Tale · Space toggle/cycle · j/k move · e edit · c custom · 1–3 submit
```

**Controls:**
- A toggle uses the same `☑️`/`⬜` vocabulary as AND members.
- A choice reuses the `_EnumField` control that cycles in place.
- The focused row shows its one-line consequence, dimmed.
- **Enter still submits the primary branch with the current values.** Accepting
  defaults stays one keystroke.

**Memory rows:**
- Show `🧠`, the note names, the note type, and a provenance chip:
  - `requested` when the quote was verified;
  - `not requested`, dimmed, otherwise;
  - `⚠ request not found` when a quote failed the check.
- Showing the note type (`core` vs `reference`) tells you whether the change costs
  context on every turn.

**Feedback while you edit:**
- A value changed from its default gets a `•` marker and the accent colour. The footer
  shows "1 decision changed".
- **Epics:** the Epic button shows the live phase count, e.g. `✅ Epic · 4 → 3 phases`
  as `when:` decisions are toggled. That makes a toggle's effect visible before you
  commit.

**Notifications:** the toast and the notification row add a count, e.g.
`Tale ready · 2 decisions · 🧠`. They use the same `encode_plan_counts` channel epic
toasts already use for phases.

**Other surfaces:**
- **CLI:** `sase plan approve keymap_help_overlay -D memory=no -D grouping=mode`
  (`-D/--decide`, repeatable).
  - Unknown ids and bad values fail before any side effect and list the allowed values.
  - `--dry-run` prints the resolved decisions.
  - `sase plan show` gets a Decisions table (`id`, `ask`, `default`, `answer`).
  - Per the `cli_rules` reference note, read that note before adding the flag.
- **Telegram and mobile:** render toggles as inline buttons and choices as cycling
  buttons, from `payload.decisions`. Until they do, they submit nothing for
  `decisions` and the defaults apply. They degrade safely.
- **Generic fix (independent of this feature):** give typed `bool` inputs a real toggle
  widget in `TypedInputForm`.

### 6.6 Recording the answers

The approve command already sits where the reviewed plan, the inputs, and the archive
meet (§1.3). Before it syncs and archives, it:

1. resolves the submitted values plus defaults through `sase-core`;
2. writes them into the reviewed plan's frontmatter.

The archived plan then reads:

```yaml
decisions:
  memory:
    ask: Record the overlay's keymap conventions in the `tui` memory note?
    memory: [tui.md]
    requested: "and note the convention in the tui memory"
    default: true
    answer: false
  grouping:
    ask: How should the overlay group bindings?
    choices: { pane: …, mode: … }
    default: pane
    answer: pane
answered_by: reviewer        # reviewer | auto | cli
```

The rules:

- **Answers are immutable.** Relaunching a failed coder with `sase plan approve` reuses
  them; changing them is a new review.
- **Commit-only tale approvals** still record answers, so a coder launched later sees
  them.
- **Epics:** the epic approve command writes answers into the durable proposal before
  the launch monitor runs `sase bead work`. The archive and bead creation then see them.
- **A plan launched with no answers** (for example a hand-run `sase bead work`) has its
  answers resolved to defaults and written by the first consumer. The archive never
  depends on implicit defaults.
- Keeping `default` next to `answer` turns every archived plan into a data point on how
  well planners choose defaults.

### 6.7 How implementers consume the answers

**Tale coder.**
- The successor prompt from §1.3 gains a block after "Implement it now.". The answers
  are booleans or enum keys and the ask text is shown as quoted data, so nothing free
  form is interpolated.

  ```
  The reviewer answered this plan's decisions. They are final:

  - `memory` — "Record the overlay's keymap conventions in the `tui` memory note?" → no
    (you recommended yes). Do not edit tui.md.
  - `grouping` — "How should the overlay group bindings?" → pane: By pane, matching
    the footer hints.

  Implement only the branch each answer selects.
  ```

**Epic.**
- `sase bead work` evaluates `when:` against the answers. It never creates skipped
  phases and drops dependencies on them.
- The epic bead's creation reason records them: "phase `record` skipped by decision
  `decision_record=false`".
- `plan_phase_waves` runs over the active phases only.
- `sase bead read` gains a **DECISIONS** section for epic and phase beads, drawn from
  the archived plan.
- `bd/work_phase_bead` and `bd/land_epic` gain one sentence: "Honor the epic's
  DECISIONS shown by `sase bead read`."

**Memory authorization.**
- `/sase_memory_write`'s "approved plan names the change" route becomes "an approved
  plan's memory decision covering that note was answered `true`".

### 6.8 Verifying memory requests

- **Rust side.** One `sase-core` function, `plan_decisions_verify_requests(plan,
  evidence[])`, does the matching:
  - case-folded, whitespace-collapsed, with Markdown emphasis stripped;
  - a substring match per `requested:` quote;
  - it returns which quotes it verified.
- **At propose.** `sase plan propose` passes `raw_prompt.md` from the agent's artifacts
  directory and fails with an actionable error. The agent is still alive and can fix
  the quote or flip the default.
- **At gate build.** `create_plan_gate_turn` already has `state.original_prompt`, the
  feedback bullets, and the Q&A rounds. It verifies again and **fails closed**: an
  unverified memory default becomes `false` and the review is flagged.
- **What counts as a request.** A bead-originated planner whose request lives in a bead
  description, not in the prompt, simply defaults to off. Your one keystroke turns it
  on. That is acceptable friction for the rare case.

### 6.9 Enforcement backstop (later phase, beta flag)

- **What it checks.** A commit-finalizer guard (`src/sase/finalizers/commit*`, which
  already inspects dirty paths) runs for agents launched from an approved plan (coder,
  phase, land). Changed paths under the memory root, plus the regenerated
  `AGENTS.md`/shims, must be covered by a memory decision answered `true`.
  - **Advisory mode** (first): a warning in the declaration.
  - **Enforcing mode**: the commit finalizer fails with the uncovered notes listed.
- **Rollout.** Start advisory behind a `beta` flag, then switch to enforcing after soak.
- **Why last.** It is the only part with teeth, and it should not land until the
  decisions it checks against are reliably produced.

### 6.10 Where the code goes (Rust boundary)

| Layer | Work |
| --- | --- |
| `sase-core` `plan/validate.rs` + a new `plan/decisions.rs` | Schema and validation; `PlanDecisionWire`, `PlanPhaseWire.when`, `ValidatedPlanWire.decisions`. `Authoring` forbids `answer`/`answered_by`. Functions: input schema, resolve answers, apply answers to content, active phases, verify requests. Wire v3 → v4. |
| `sase` wire and pin | `sdd/plan_validate.py` dataclasses; bump `sase-core-revision.txt` (per `docs/rust_backend.md`). |
| `sase` gate | `plan_gate.py` (payload, inputs, result schemas); `_plan_gate_command.py` (resolve and write answers); `_plan_gate_envelope.py` and `PlanApprovalResult`; `kind_validation/plan.py` (schema equals payload); `adapters.py` (edit freeze); `plan_gate_turn/create.py` (verification); `plan_gate_turn/followup.py` (feedback carry). |
| `sase` consumers | `run_agent_exec_plan_accept.py` (prompt block); `bead/epic_from_plan.py` (`when`); `bead/cli_detail_resolution.py` (DECISIONS); `default_config.yml` macros; `sase plan approve -D`; `sase plan show`. |
| `sase` TUI | `plan_approval_modal.py` (Decisions section, Verdict rename); a `bool` toggle in `typed_input_form.py`; toast counts. |
| Skills, docs, memory | `src/sase/macros/skills/sase_plan.md` and `sase_memory_write.md` (generated skills; see the `generated_skills` note); `docs/sdd.md`, `docs/notifications.md`; a **Plan Decision** glossary strand. The strand is itself a memory change, so it needs your explicit sign-off. |
| Other repos | Follow-up beads for `sase-telegram` and mobile rendering. |

---

## 7. Open questions for you

1. **Direct-prompt memory edits (A4).** Keep the direct path for explicit, specific
   instructions in the current prompt (my recommendation)? Or require a plan for every
   memory change, with no exceptions?
2. **Declined memory decisions.** Should declining one auto-file a `memory` task bead?
   - My recommendation is **no**. The archived plan already preserves the proposal,
     and with ~1,050 retained task-triage bundles on this host, more automatic beads
     would add noise.
   - The athena question's "defer via bead" option stays available through Additional
     instructions.
3. **Should any decision be able to stop `%auto`?**
   - My recommendation is **no** in v1. A decision that needs a human is a question to
     ask now.
   - Revisit if `%auto` gains typed autonomy profiles.
4. **The name.** `decisions:` with `ask`/`default`/`answer`, or `questions:`?
5. **Guard strictness (§6.9).** Should enforcing mode fail the run, or only block the
   memory paths and commit the rest?

---

## 8. Recommended solution

**Build Plan Decisions as typed parameters of plan approval, declared in frontmatter and
recorded back into the plan.**

1. **Author.**
   - An optional `decisions:` map: at most five, each a toggle or a 2–5-way choice,
     each with a required `default`.
   - Memory decisions add `memory:` notes and, to default on, a `requested:` quote of
     the user's words.
   - Epic phases may declare `when:` on a decision.
2. **Validate in `sase-core`.**
   - Strict schema, one-line asks, caps, `when` checks.
   - The system-managed `answer` is forbidden while authoring.
   - Requested quotes are checked against the prompt chain at propose and again at gate
     build; an unverified default is forced off.
3. **Review in one place.**
   - Decisions compile into one typed `decisions` input on the existing approve option.
   - They render as a Decisions section of the Plan Review modal.
   - Enter accepts the shown values; `%auto` and older surfaces take the defaults.
   - In-gate edits can't change the set; feedback can.
4. **Record once.**
   - The approve command writes `answer:` and `answered_by:` into the plan before it is
     archived.
   - The archived plan is the single, immutable record of question, recommendation,
     and answer.
5. **Consume mechanically.**
   - Coders get a short "Reviewer decisions" block.
   - Epics never create phases whose `when:` is false.
   - `sase bead read` shows DECISIONS to every phase and land agent.
   - The memory-write skill treats an accepted memory decision as the authorization.
6. **Enforce later.** A flagged commit-finalizer guard, advisory then enforcing, checks
   memory diffs against accepted memory decisions.

**Suggested epic shape** (sizes per `sase_sizes`):

| Phase | Work | Depends on | Size |
| --- | --- | --- | --- |
| `core` | `sase-core` schema, wire v4, resolve/apply/when/verify APIs, tests | — | large |
| `gate` | Pin bump, Python wire, gate compile, approve-command write-back, edit freeze, feedback carry, verification at propose and gate build | `core` | large |
| `consumers` | Coder prompt block, `when` phase filtering, `bead read` DECISIONS, macro sentence, `sase plan approve -D`, `sase plan show` | `gate` | medium |
| `tui` | Decisions section, Verdict rename, bool toggle widget, toast counts | `gate` | medium |
| `policy` | `/sase_plan` and `/sase_memory_write` templates, docs, glossary strand | `consumers`, `tui` | small |
| `guard` | `beta`-flagged finalizer memory guard, advisory first | `policy` | medium |

`policy` lands last on purpose. Agents start authoring decisions only once every
surface you use can show and change them. Older surfaces still behave correctly in the
meantime, because an omitted value means its default.
