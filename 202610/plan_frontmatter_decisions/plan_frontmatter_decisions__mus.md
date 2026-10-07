# Embedding Gate Options in SASE Plan Frontmatter

Researcher: mus (`__mus`) — independent swarm report.

## Summary

Embedding human decisions in plan (tale/epic) frontmatter is a good idea,
but the request as stated ("embed sase gate options") is too broad and
picks the wrong layer. Plans should embed **questions and confirmations**
(intent), never full gate specifications (mechanism: queries, commands,
resources, turn blocks). SASE should synthesize the actual gates at
`propose` time from that intent, present them inside the existing plan-review
moment, and forward the typed answers to the coder. With that narrowing, the
feature is intuitive (it reuses the `sase questions` vocabulary agents
already know), reliable (strict Rust-owned validation, no executable content
in frontmatter), and beautiful (one review sitting, existing renderers).

Recommended v1: an optional `gates:` frontmatter list whose items are a
strict, id-tagged subset of the `sase questions` schema plus
`default`/`required`, plus a reserved memory-edit confirm produced by policy
rather than hand-authored each time. Details in §6.

## 1. What exists today

### 1.1 Plan frontmatter (Rust-owned, strict)

- Plan tiers are `tale` (one coder agent) and `epic` (phased, multi-agent).
  The authoring contract is tiny: tale requires
  `tier/title/goal/size[xsmall|small|medium]`; epic requires
  `tier/title/goal/phases[{id,title,depends_on,size}]` with unique slug ids,
  earlier-only dependencies, and per-phase sizes. Optional: `model`, transient
  `links`, and SASE-managed provenance (`bead`, `proposed_by`, `status`,
  `create_time`). Verified via `sase plan validate --explain` against the
  live schema.
- The authoritative schema lives in `sase-core` (Rust); the Python
  `src/sase/sdd/plan_validate.py` adapter only rehydrates binding payloads.
  Any new frontmatter field therefore needs a Rust schema change, a wire
  version bump, binding updates, and a `sase-core-revision.txt` pin move —
  per the Rust core backend boundary rule. This is the main implementation
  cost and it argues for a *small* schema addition.
- Precedent for transient authoring inlets: `links` is consumed by
  `sase plan propose` into typed artifact links and **stripped** from the
  archived frontmatter. A `gates:` inlet can follow the same pattern
  (consume at propose), except the questions *and answers* should be
  archived as provenance rather than stripped (§6.5).

### 1.2 Plan approval is already a gate

- `sase plan propose` archives the plan and creates a tier-specific
  `PlanApproval`/`EpicApproval` gate turn. Tale query is
  `(approve AND commit) OR reject OR feedback`; epic is
  `approve OR reject OR feedback`. Each branch has a defined follow-up:
  approve→coder/phase launch, feedback→replan, reject→end.
- Consequence: there is exactly one moment when the human studies the plan.
  Any embedded decision should surface **in that same review**, not as a
  second popup before or after it. A chained second gate doubles latency
  (each gate turn is a full human round-trip) and splits context.

### 1.3 `sase questions` (the right vocabulary)

- `sase questions '<json>'` takes
  `[{question, header?, options[{label, description?}], multiSelect?}]`,
  creates a question gate turn with a single `submit` option, kills the agent
  turn, and hands merged Q&A to the follow-up agent via the existing
  Q&A-round machinery (`build_qa_round` / `merge_qa_for_prompt`, chainable
  across rounds). Validation (`validate_user_questions`) is strict: non-empty
  question text, unique non-`"Other"` labels, boolean `multiSelect`.
- This is the vocabulary planners already use, and its answers already flow
  to the next agent as fenced, labelled prompt sections. Reusing it for
  plan-embedded decisions buys validation, rendering, and coder-delivery
  for free.

### 1.4 Custom gates (the wrong vocabulary for frontmatter)

- Full custom gates (schema v3: `query`, `options` with `command.argv`,
  `inputs`, `result_schema`, `groups`, `operations`, `resources`,
  `turn/next/branches`) are powerful *because* they carry executable
  commands. Letting a Markdown plan file declare commands/resources would be
  code execution from an authorable document: a reviewer could approve a
  plan and unknowingly authorize embedded shell. It also duplicates ~40
  gate-validation rules inside the plan schema and breaks the Rust boundary
  twice over. Reject this reading of "gate options" outright.

### 1.5 Memory-write routing (the motivating pain)

- `sase_memory_write` authorizes memory edits only when the user prompt
  asked, an approved plan names the change, or the worked bead describes it.
  A planner whose steps touch memory unprompted must ask via
  `/sase_questions` **before** `propose` — i.e. the human answers without
  seeing the plan — or file a `memory` task bead instead.
- The status quo is correct on authorization but wrong on timing: the human
  decides blind, and the decision is not recorded against the plan. This is
  the strongest argument for the feature.

## 2. Critique: is this a good idea?

Yes, for the two motivating cases, with adjustments:

1. **Memory gate (confirm).** Real problem, real fix. Deciding "may this
   plan touch memory?" while looking at the plan's memory steps is strictly
   better than deciding before the plan exists. Recording the permission
   with the approval is an audit improvement too.
2. **Plan-affecting questions (choice).** Real problem, real fix. Today the
   agent must choose between blocking on `sase questions` (latency, and it
   cannot show a plan it has not written yet) and guessing (rework risk).
   Writing the plan around explicit decision points and letting the reviewer
   resolve them at approval time removes a false dilemma.

Would I take a different approach? Only in mechanism, not in goal:

- **Do not build a second asking path.** Alternatives like "propose, then
  the coder asks questions mid-implementation" preserve latency instead of
  removing it, and mid-execution questions have less context than
  at-review questions. The review moment is the Schelling point; use it.
- **Do not implement as Markdown-body convention** ("## Open Questions"
  section). Prose questions are untyped: the TUI cannot render controls,
  `gate show` cannot project them, `%auto` cannot resolve them, and the
  coder must parse English. Typed frontmatter is the whole point.
- **Do not scope v1 to epics-per-phase.** Per-phase gates are the natural
  generalization but they entangle dependency scheduling (a phase blocked
  on an unanswered gate stalls its wave). Ship plan-level gates first.

## 3. Adjustments to the requirements (explicit)

1. **"Embed gate options" → "embed decision intent".** Frontmatter declares
   questions/confirms with ids, labels, options, defaults — never `query`
   strings, `command.argv`, `resources`, `operations`, or `turn` blocks.
   SASE compiles intent into gates at propose time. (Security §5.1.)
2. **Memory default "on iff the user explicitly requested" is not
   automatable as stated.** "Explicitly requested" cannot be reliably
   detected from the prompt at propose time (paraphrase, implication,
   multi-turn context). Replace the fragile auto-default with:
   planner-declared `default` + a mechanical propose-time cross-check that
   warns when a memory-touching plan declares no memory gate, or declares
   `default: true` while the turn prompt never mentioned memory. The human
   remains the source of truth; the check catches planner dishonesty or
   sloppiness, it does not replace judgment.
3. **Memory permission should be policy-synthesized, not hand-authored per
   plan.** Planners should not re-derive the memory-confirm wording on every
   plan. If the plan steps touch `sase/memory/` (or home-memory
   equivalents), `propose` injects a reserved `memory_edits` confirm into
   the review automatically; frontmatter only tunes it (see schema §6.1).
   Hand-authoring is reserved for plan-affecting choices.
4. **One review sitting, not a gate chain.** The gates ride along with plan
   approval (same modal/session), not as follow-up gates after it. This
   constrains the design but is where the beauty comes from.

## 4. Design space

| Option | Shape | Verdict |
| ------ | ----- | ------- |
| A. Full gate JSON in frontmatter | `query`/`options`/`command`/`resources`/`turn` verbatim | Reject: executable content in plans, huge schema, breaks Rust boundary, ugly. |
| B. `gates:` as question intent + synthesized review (recommended) | Typed questions/confirms; SASE builds the review UI and forwards answers | Adopt (v1). |
| C. Body-convention questions | `## Decisions` prose section | Reject: untyped, invisible to gate machinery. |
| D. Coder-time questions | Plan ships vague; coder asks via `sase questions` mid-run | Reject as primary: preserves latency, less context. Keep as fallback for genuinely emergent questions. |
| E. Plan-approval inputs | Fold choices as `inputs` on the existing approve option | Reject as sole mechanism: conflates "approve plan" with "decide X"; muddies `%auto`, audit, and per-question `required`. |

## 5. Constraints the design must respect

- **5.1 No executable content.** Frontmatter is data. The `inputs`
  vocabulary (`word/line/text/path/agent/int/bool/float/enum`) is closed and
  declarative and would be acceptable in principle, but v1 does not even
  need it: choice questions reuse the `sase questions` option shape, which
  compiles to a response schema server-side.
- **5.2 Single-turn agents.** Planner ends at `propose` (SIGTERM handoff);
  reviewer answers asynchronously; coder receives answers in its prompt.
  Embedded gates must not require the planner to stay alive.
- **5.3 `%auto` must fail closed.** A `required` gate without a usable
  default blocks auto-resolution; fully-defaulted gates resolve
  synchronously in-process (mirroring the custom-gate auto rule). Never
  auto-answer a `required` memory permission.
- **5.4 Untrusted-data discipline.** Gate question/option text is
  reviewer-visible and coder-visible; like all gate content it must be
  fenced and labelled in the coder prompt, never interpolated as
  instructions (the gate-turn `next.prompt` rule already establishes this).
- **5.5 Caps.** Gate count, option count, and text lengths need hard caps
  (suggested: ≤5 gates, ≤6 options each, question ≤300 chars, label ≤80
  chars) so one plan cannot crowd the review modal. Validation rejects
  overflow with actionable diagnostics, exactly like size/tier errors today.

## 6. Recommended solution (v1)

### 6.1 Frontmatter schema (Rust core addition)

```yaml
---
tier: tale
title: Ship cached reads
goal: Reads are cached end to end.
size: small
gates:
  - id: cache_backend
    question: Which cache backend should the coder use?
    header: Cache            # optional sidebar label
    multi: false             # default false; true = multi-select
    required: true           # default true
    default: Redis           # optional; must name an option label (or list when multi)
    options:
      - label: Redis
        description: Shared and persistent.
      - label: In-memory
        description: Single-host only, no new dependency.
  - id: allow_memory_edits   # reserved id: the memory confirm (§6.2)
    confirm: Allow memory file updates during implementation?
    default: false
---
```

Field-by-field rationale:

- `gates:` — name it `gates`, not `questions`, because the memory confirm
  is not a question and reviewers meet them as one "Decisions" section.
  Optional on both tiers; v1 semantics are plan-level (epic phases share
  the answers; reserve a `phase:` scoping key for v2 without accepting it).
- Choice items reuse the `sase questions` shape (`question/header/options`
  with `label/description`, `multi` spelling the existing `multiSelect`)
  plus `id` (unique slug, the answer key the coder programs against),
  `default` (validated against the option labels at creation — the same
  "fail loudly at creation" rule gate `inputs` defaults follow), and
  `required` (whether approval may submit with this question unanswered).
- The memory item uses the reserved `id: allow_memory_edits` with a
  `confirm:` (boolean) shape instead of options, because Yes/No options for
  a permission read worse than a toggle, and because it maps onto the
  existing tale `(approve AND commit)` toggle idiom: permission toggles
  beside commit toggles is the beautiful rendering (§6.3).
- Strictness: unknown keys rejected; `id` slug-unique across `gates`;
  labels unique per gate and never `"Other"` (inherit both rules from
  `validate_user_questions`); `default` must be submittable; `required:
  false` requires a `default` (an unanswerable-and-defaultless gate is a
  creation error, mirroring the unanswerable-option rule).

### 6.2 Memory-gate policy (the §3.2 adjustment, made concrete)

- `sase plan propose` scans the plan body/steps for memory-touching intent
  (`sase/memory/`, home-memory paths, `sase memory init` republication).
  If found and no `allow_memory_edits` item is declared, propose does **not**
  fail; it injects the confirm with `default: false` and emits a warning
  naming the detected files — secure by default, zero planner burden.
- If declared, the planner's `default` is honored but cross-checked: `true`
  while the turn prompt never mentioned memory produces a warning ("planner
  claims explicit request; prompt shows none — reviewer, verify"). This
  keeps the "default on iff explicitly requested" spirit as an audited
  attestation instead of a spooky heuristic.
- On approval with the toggle on, the permission is recorded in the
  approval response (`action_data`/audit) and the coder prompt carries an
  explicit "memory edits permitted for: <files>" line; with it off, the
  coder inherits today's rule (touching memory without permission is a
  violation, and `sase_memory_write` keeps enforcing it). This satisfies the
  motivating example: planned memory changes with an explicit human gate.

### 6.3 Reviewer experience (beauty)

- One modal, three blocks: the plan diff/summary (as today), a
  **Decisions** section rendering each gate with the question-gate controls
  reviewers already know (radio/multi-select + the memory toggle beside the
  approve/commit toggles), then the approval branches. `Enter` still submits
  the primary branch (`approve` + defaults), preserving the existing muscle
  memory; `gate show` projects gates alongside branches/inputs/actions.
- Wording discipline from the gate skill applies unchanged: each gate needs
  a decision-reading question ("Which backend…?", not "Cache question"),
  every option a label + description a non-expert can act on, one glyph per
  control. `plan validate --explain` should print gate schema guidance with
  the same care as the current size/tier guidance.

### 6.4 Coder delivery (reliability)

- On approve, answers are merged into the coder (or each epic phase agent)
  prompt through the **existing** Q&A merge path (same fenced
  `## Your next action` + Q&A sections question follow-ups use), keyed by
  gate `id`, plus the memory-permission line. No new prompt-injection
  surface beyond what question gates already have; no templating of answers
  into instructions.
- `feedback`/`reject` discards gate answers with the plan (answers are
  review-scoped, not plan properties). Re-proposal after feedback re-asks;
  the planner may adjust `default`s in the revised plan.

### 6.5 Lifecycle and archiving

- Author → `validate --explain` (gate diagnostics inline) → `propose`
  (consume `gates`, synthesize review, inject memory confirm if needed) →
  review (one sitting) → settle (answers archived with the approval
  response and the plan record; questions retained, unlike `links`) →
  coder launch (prompt carries answers) → `%auto` resolves fully-defaulted
  reviews synchronously, blocks on `required`-without-answer.
- Epic v2 reserves phase-scoped gates (`phase: <id>`); v1 validators reject
  the key with a "reserved for future use" diagnostic rather than silently
  ignoring it.

### 6.6 Work plan (where the code goes)

1. `sase-core`: `gates` schema + validation + caps + reserved-id rule;
   wire-version bump; frontmatter spec for both tiers.
2. Python: rehydrate validated gates in `plan_validate.py` records;
   `plan propose` compiles questions→review section and injects the memory
   confirm; approval response carries `{gate_id: answer}` + memory flag;
   coder/phase prompt assembly reuses `merge_qa_for_prompt`.
3. Display: `gate show` projection, `plan show` decisions section, TUI
   review-modal Decisions block, `validate --explain` gate guidance text.
4. Tests: schema accept/reject table (bad ids, dup labels, bad defaults,
   over-cap, phase-key reservation), propose injection + cross-check
   warnings, `%auto` fail-closed matrix, coder-prompt merge golden test,
   memory-permission audit test.

## 7. Open risks and non-goals

- Gate fatigue: planners may launder uncertainty into questions ("which X?"
  for every X). Mitigate with caps + reviewer-side cost (each gate is
  review work) + guidance that a good plan answers its own trivia and gates
  only true branch points.
- Stale defaults: a `default` correct at planning time can rot before
  review. `required: true` on consequential gates forces an active choice;
  defaults are conveniences for the obvious case, not decisions.
- Non-goals for v1: arbitrary gate embedding (Option A), phase-scoped
  gates, gate `inputs` beyond choice/confirm, conditional gates
  (`ask Q2 only if Q1=x` — express as independent questions or defer to
  coder-time follow-up), editing gates after propose.

## 8. Bottom line

Build it, narrowed: frontmatter declares **decisions**, SASE owns
**gates**. The v1 `gates:` list above covers both motivating cases with
one mechanism, reuses the two best-built existing paths (question-gate
asking/answering and the plan-approval review moment), keeps executable
content out of plans, and fails closed under `%auto`. The adjustments in
§3 — intent-not-mechanism, attested memory defaults with cross-checks, and
policy-synthesized memory confirms — are the difference between a feature
that is merely expressive and one that stays trustworthy.
