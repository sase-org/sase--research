# Plan-Embedded Reviewer Choices: UX Across TUI, Telegram, and CLI

> Researcher mus · 2026-10-07 · Independent UX design for embedding sase gate
> options (reviewer decisions) in plan frontmatter (tales and epics).
> Prior work reviewed: `plan_frontmatter_decisions.md` (lead consolidated report,
> 2026-10-07, merging five swarm reports with source checks against sase,
> sase-core, sase-telegram, and retained gate bundles). I agree with all of its
> recommendations; where this report differs it is on UX emphasis and a few
> concrete interaction details, which are flagged inline.

## Question

What is the best possible UX — across the TUI (ACE), Telegram, and the CLI — for
letting sase plans embed reviewer choices in their frontmatter, so that:

1. memory-file changes can be planned with explicit human gates that default to
   on only when the user explicitly requested them; and
2. an agent with a plan-affecting question can write one good plan now and let
   the coder implement whichever branch the reviewer selects?

## Bottom line

**Ship "Plan Decisions", not "gate options".** The plan declares a small,
typed, defaulted `decisions:` map (at most five toggles or 2–5-way choices).
The host compiles each decision into a typed, non-required input on the
existing `approve` option (`bool` for toggles, `enum` for choices). The reviewer
answers them inside the plan-approval review they were already going to do —
one review, one keystroke to accept defaults, one archived plan that records
question, recommendation, and answer together.

Concretely, for each surface:

- **TUI:** a new always-visible **Decisions** section above the renamed
  **Verdict** section in the Plan Review modal. Toggles render as ☑️/⬜,
  choices cycle in place (existing `_EnumField`), a live outcome sentence shows
  what Enter will do, and changed-from-default rows get a `•` marker. Add the
  one missing widget — a real bool toggle in `TypedInputForm` — and never hide
  decisions behind the `c` custom screen.
- **Telegram:** the approval message lists decisions with current values; the
  first button is **✅ Approve as shown** (submits nothing, defaults apply) and
  the second is **🎛 Change decisions** (enters the existing typed step flow,
  extended with a yes/no keyboard for `bool`). Non-required steps keep the
  existing skip-to-default behavior.
- **CLI:** `sase plan approve … -D id=value` (`--decide`, repeatable) plus
  `--dry-run` resolution preview and a Decisions table in `sase plan show`.
  Unknown ids/values fail before any side effect. The direct-approve path
  (no live gate) resolves through the same function as the gate.

Everything else — sealed query/options/groups, AND-subset semantics, exact-set
routing keys, receipts, `%auto` taking defaults, omitted-means-default for old
clients, a frozen decision set per review, and `answer:` stamped into the
archived plan — follows from that one compiling choice, and is what makes the
feature reliable.

## What the prior research settled (and where I stand)

The consolidated report's verdict is correct and I adopt it wholesale as the
starting point:

- **Decisions, not gates (A1).** Frontmatter never contains `query`, `command`,
  `resources`, `groups`, or `turn` blocks. The plan gate's contract stays
  sealed; decisions travel as `option_inputs` on `approve` (and tale `commit`,
  which shares inputs). I verified the load-bearing facts myself: the tale
  query is `(approve AND commit) OR reject OR feedback`, AND branches accept any
  non-empty subset, tale follow-ups route on the exact selected-option key, and
  the declared-input vocabulary already covers `bool` and `enum` with `default`.
- **Every decision declares a default (A2).** Nothing blocks `%auto`. The
  planner rule — "if you cannot defend a default, ask now with
  `/sase_questions`" — is the correct split, matching the Spec Kit
  critical/high-vs-medium/low precedent the lead cites.
- **Requested-defaults are checked quotes (A3).** A memory decision may default
  to `true` only with a `requested:` quote matched word-for-word against
  human-written text (prompt, feedback, Q&A answers), checked at `propose` and
  again at gate build, failing closed to off. A planner assertion flag alone
  counts for nothing. This is the only design that survives the 73–82%
  auto-approval rate: defaults *are* the policy.
- **Scope, fixed graphs, frozen sets, read selectors, beta flag (A4–A8).**
  Plan-driven memory work needs covering decisions; direct specific human
  instructions stay valid without a plan; epic phase graphs stay fixed with
  `phases[].when` reserved; the decision set freezes per review; memory scope
  uses `sase memory read` selectors; everything ships behind a beta flag until
  all three surfaces soak.

My contributions in this report are: (a) the per-surface interaction spec with
keystrokes, widgets, message shapes, and CLI grammar; (b) the cross-surface
consistency contract that keeps three renderers feeling like one feature;
(c) the memory-consent moment-by-moment UX; and (d) the beauty pass — the
small details that make defaults reviewable at a glance instead of
rubber-stamped blind.

## Design principles

1. **One review, not two.** The failure of `/sase_questions`-before-plan is
   latency plus blindness: the human answers without seeing the plan, pays two
   sittings, and `%auto` takes the first option rather than the recommended
   one. Every design choice below preserves "decisions ride along with the
   plan".
2. **Accepting defaults stays the cheapest action.** Reviewers approve
   `approve+commit` essentially always (197/198 tales in the lead's host
   sample) and never touch the hidden `c` screen (0/54). So Enter must always
   submit what is shown, and decisions must be visible in the main review —
   never behind `c`, never N extra gates, never a mandatory per-decision step.
3. **Omitted means default, everywhere.** JSON Schema does not fill defaults
   and `%auto` submits `{}` (tales) — so the approve command resolves
   submitted-plus-defaults through one sase-core function, and old clients
   settle correctly without knowing decisions exist.
4. **Reviewer-visible provenance for memory.** Because defaults decide ~3/4 of
   plans, a memory `true` must show *why* it is on: the quote, the match chip,
   and the note type's cost (`core` costs context every turn, `reference`
   does not).
5. **The file tells the whole story.** Gate responses and receipts are
   authoritative, but the archived plan's stamped `answer:` + `decided_by:` is
   what the coder, every epic phase (via EPIC PLAN), the land agent, and future
   audits actually read. The prompt channel to the tale coder must be a
   host-written block of enum keys and booleans only — never free-form
   interpolation — because the coder starts fresh from `@<archive ref>`.

## TUI (ACE Plan Review modal): the primary surface

The TUI is where the feature lives or dies: 42/54 human tale reviews in the
host sample happened here, and it is the only surface that can show plan prose
and decisions side by side.

### Layout: Decisions above Verdict, always visible

```
┌ Plan Review · claude/opus ─────────────────────────────┐
│ plan body (right pane, scrollable)      │ Decisions     │
│                                         │ ◆ Grouping    │
│                                         │   ‹ mode ›  • │
│                                         │   By leader…  │
│                                         │ ☑ 🧠 Record…  │
│                                         │   tui.md · ✓  │
│                                         │ Verdict       │
│                                         │ ☑ Launch coder│
│                                         │ ☑ Commit plan │
│                                         │ 1 Tale 2 Rej… │
│                                         │ → coder · …   │
└────────────────────────────────────────────────────────┘
  Enter submit · Space toggle/cycle · j/k move · e edit · c extras · 1–3 verdict
```

- Rename the existing left-column `Decision` section (today a literal
  `Static("Decision", …)` in the modal compose) to **Verdict**. The word
  "decision" now means reviewer choices; the verdict is approve/commit/reject/
  feedback. Keeping both under one word guarantees confusion in help text and
  keymap docs.
- The **Decisions** section sits directly above Verdict, always mounted —
  even when the plan declares zero decisions (where it renders as a single
  dimmed line, "No reviewer decisions in this plan", so reviewers learn where
  to look). Rationale: the `c`-screen precedent proves anything hidden goes
  unused; decisions must be in the tab order of the main modal.
- Each decision is one row: glyph + short ask + control + consequence line.
  The consequence (choice label, ≤100 chars) renders dimmed under the focused
  row only, keeping the list scannable at five rows max.

### Controls: reuse enum, build the bool toggle

- **Choices** reuse the existing `_EnumField`: Space (or →) cycles in place
  through ≤5 labels, storing canonical values; >5 is rejected at validation
  (the authoring cap is five), so the picker path never triggers for
  decisions. Required-without-default sentinels do not apply — every decision
  has a default, so the control always shows a submittable value.
- **Toggles** need the one genuinely new widget: a real bool toggle in
  `TypedInputForm`. Today a `bool` input falls through to a generic text box
  (the `_build_editor` chain handles `model`, `enum`, `secret`, `path`,
  `text`/repeatable, and otherwise a plain input) — typing "true" into a box
  is the opposite of beautiful and will produce validation friction on every
  memory consent. Spec: Space flips ☑️/⬜, the row label is phrased so **yes
  means do the work**, and the widget exposes the same `value`/`set_value`
  contract as `_EnumField` so `GateBranchControls` needs no special case.
- **Changed marker.** Any row whose current value differs from its default
  gets a `•` plus the accent color (matching the lead's mock). This is the
  cheapest anti-rubber-stamp device available: the reviewer sees at a glance
  "I touched two rows", and screenshots in declarations stay legible.

### The outcome line and the keyboard

- One live sentence above the submit row, always current:
  `→ coder · grouping=mode · edit tui.md` (or `→ commit only`, `→ no memory
  edits`). It is computed from branch selection × decision values and is the
  reviewer's last chance to catch a mistaken default. Keep it to one line;
  truncate the plan-name side, never the decision side.
- Keys (additions to `src/sase/default_config.yml` where the gate modal
  bindings live): `Enter` submits the primary branch with values shown;
  `Space` toggles/cycles the focused decision; `j/k` (and arrows) move between
  decision rows and branch rows in one list; `e` opens in-gate plan edit;
  `c` keeps its current meaning (coder extras: `coder_prompt`, `coder_model`,
  `wait`, `capacity`) and must never show decisions; `1–3` submit verdict
  branches directly. Number keys submit with current decision values, not
  defaults — otherwise `1` becomes a footgun that silently discards visible
  edits.
- **In-gate edit (`e`) freezes the set.** The adapter's preview regeneration
  is a no-op by design, so recompiling schemas mid-review is out. If the
  edited file changes ids, kinds, choice keys, or memory scope, refuse with
  the lead's wording ("Decisions are fixed for this review — toggle them in
  the Decisions panel, or send feedback to change the set") and keep the
  review open on the old payload. Wording-only `ask` edits are allowed. This
  must be a refusal, not a silent recompile: silent recompiles break receipts
  binding the reviewed request hash.

### Memory rows: provenance at a glance

Each memory toggle row shows: 🧠 + selectors + note type + provenance chip:

- `✓ requested` (accent, quote verified), `not requested` (dimmed, default
  off), `⚠ request not found` (warning, planner claimed `requested:` but the
  word-for-word check failed — default forced off).
- Note type matters for consent cost: `core` (every-turn context) vs
  `reference`. Show it; reviewers cannot otherwise tell why one memory toggle
  feels heavier than another.
- The `requested:` quote itself is one `e`-away in the frontmatter, but the
  row should surface it on demand (focused-row detail line, truncated at ~80
  chars). Do not paste full quotes into every row — five quotes would drown
  the panel.

### Toasts and counts

Use the existing count channel: `Tale ready · 2 decisions · 🧠`. An
auto-resolved plan's notification lists each decision taken and marks it
`auto` (see %auto section). The toast is not the consent record — the stamped
plan is — but it is how `%auto` stays honest in a one-line world.

## Telegram: approve-as-shown plus a typed step flow

Telegram cannot show plan prose and decisions side by side the way the TUI
can, so its UX must optimize for the common case (accept defaults on a phone)
while keeping the uncommon case (change one toggle) to a bounded number of
taps. The existing typed declared-input flow already supports `enum`
keyboards and skip-to-default for non-required fields; the gap is `bool`,
which today falls back to a typed reply.

### Message shape

```
📋 Plan ready: Keymap help overlay (tale, small)
Decisions (defaults shown — Approve as shown to accept):
 ◆ Grouping: pane — By pane, matching footer hints
 ☑ 🧠 Record conventions in tui.md? YES · ✓ requested · reference
→ coder · grouping=pane · edit tui.md
[✅ Approve as shown] [🎛 Change decisions]
[❌ Reject] [💬 Feedback]
```

- The message lists every decision with its default and consequence text from
  day one, so even a client that cannot render keyboards still settles
  correctly by tapping Approve (omitted = default).
- Memory rows compress provenance to text chips (`✓ requested`, `not
  requested`, `⚠ request not found`) plus note type. Telegram has no hover
  state, so the consequence line and chip must be inline, not on-focus.
- Keep the whole message comfortably under one phone screen for ≤3 decisions
  and under the platform's text limits at the 5-decision cap; truncate
  consequence labels before truncating ids or values, because the id is what
  the step flow will reference.

### Two-button approval (do not force N steps)

- **✅ Approve as shown** submits the primary branch with no decision inputs,
  so the server resolves defaults. One tap, matching TUI Enter. This button
  must be first and must be the visually primary action.
- **🎛 Change decisions** enters the existing step flow (`gate_input_steps`),
  one decision per step, in frontmatter order. Each step shows ask +
  consequence labels + current default, offers value buttons, and always
  offers **Skip (= default: X)** — the Telegram analogue of "Enter accepts
  what is shown". Back/confirm affordances follow the existing flow; do not
  invent a parallel flow for decisions.
- **New: yes/no keyboard for `bool`.** Spec: two buttons, `✅ Yes (<default?>)`
  and `⬜ No`, plus Skip. Mark which one is the default so the reviewer can
  distinguish "I chose Yes" from "I skipped and got Yes". Without this,
  every memory consent degrades to free-typed "yes/no" parsing — the exact
  friction the TUI bool toggle removes.
- Reject and Feedback stay exactly where they are. Feedback may additionally
  carry provisional decision values (recorded as "you changed `tui_note` →
  no" in the replan prompt, per the lead), but the step flow must not require
  it: feedback-without-values remains one message + send.

### Reliability notes specific to Telegram

- Step-flow answers submit canonical values (`mode`, `true`), never labels —
  the same wire names (`decision_<id>`) as the TUI, so kind-validation
  equality holds across surfaces.
- If the plan is edited mid-review (frozen set violated), the Telegram flow
  must fail the step with the same "fixed for this review" text rather than
  silently recompiling: the phone reviewer is the least equipped to notice a
  schema swap.
- Follow-up bead work for the Telegram rendering (keyboards, message
  templates) belongs in sase-telegram; the sase side only gains the payload
  inputs and resolution. Call that out in the epic so the two repos stay in
  phase behind the beta flag.

## CLI: scriptable, previewable, same resolution

The CLI serves two masters: the human who prefers the terminal (12 CLI tale
reviews in the host sample) and scripts/automation that must resolve decisions
without a modal.

### Grammar

```bash
sase plan approve keymap_help_overlay -D grouping=mode -D tui_note=no
sase plan approve keymap_help_overlay --decide grouping=mode --dry-run
sase plan show keymap_help_overlay   # Decisions table: id · ask · default · answer
```

- `-D` / `--decide` is repeatable, `id=value` with `=` required. Booleans
  accept exactly `yes/no`/`true/false` (lowercase; `1/0` rejected — they read
  as counts, not consent) normalized to canonical `true/false`. Enums accept
  the canonical key only, not the label (labels contain spaces and punctuation
  and would need quoting heuristics that differ by shell).
- Unknown ids or out-of-range values fail **before any side effect** (no
  archive write, no coder launch, no bead creation) and print the allowed
  table: `unknown decision 'group' — did you mean 'grouping'? choices:
  pane | mode`. This ordering matters: a typo must never launch a coder with
  defaults silently substituted.
- `--dry-run` prints the fully resolved decision set (submitted + defaults +
  verification outcome, including forced-off `⚠` rows) without changing
  anything. It is the CLI analogue of the TUI outcome line and the cheapest
  way to test planner output in CI.
- `sase plan show` gains the Decisions table (id, ask truncated at ~60 chars,
  default, answer or `—` when pending). Full `ask`/choice/consequence text
  stays in the frontmatter; the table is an index, not a second source.

### Direct routes and the agent boundary

- `sase plan approve <file>` with no live gate (and hand-run `sase bead
  work`) resolves through the **same** sase-core function as the gate path,
  with the same verification rule: a memory `true` requires either a verified
  quote or an explicit human `-D` from a shell. Document the one hard rule
  where UX meets security: **an agent process cannot submit `-D <memory>=yes`**
  — the CLI detects the agent context and refuses, so scripts cannot launder
  consent the reviewer never gave. (Exact mechanism — env/role detection — is
  an implementation detail; the UX contract is the refusal message naming the
  covering decision and how a human approves it.)
- Read the `cli_rules` reference note before adding the flag (short help,
  examples, `-D` collision check against existing `-d`/`-D` in adjacent
  commands). The help text must state the omitted-means-default rule in one
  line: "Omitted decisions resolve to their defaults."

## Cross-surface consistency contract (one feature, three renderers)

These rules are what make three different renderers feel like one feature.
Enforce them in sase-core + the shared gate layer, not per surface:

1. **Wire names are internal.** Decisions compile to `decision_<id>` inputs so
   they can never collide with host fields (`approve`, `commit`, `feedback`,
   `coder_prompt`, `coder_model`, `wait`, `epic_launch_mode`, `capacity`).
   Frontmatter ids matching a reserved name fail validation with a named
   diagnostic.
2. **Inputs are non-required with defaults; the result schema's resolved
   `decisions` object is required and fully explicit.** Every approval writes
   every value explicitly into `response.json`, so receipts bind the reviewed
   request hash with no extra machinery.
3. **Kind-validation equality.** The inputs derived from `payload.decisions`
   must equal the declared inputs — a forged request cannot drift from its
   payload, and the query/options/commands/groups stay byte-identical to
   today's sealed contract.
4. **Frozen set per review.** Ids, kinds, choice keys, memory scope frozen;
   `ask` wording editable. Violations refuse with one shared string across
   TUI, Telegram, and CLI.
5. **Canonical order is frontmatter order.** YAML map order is preserved;
   TUI rows, Telegram steps, CLI tables, and the stamped `answer:` map all use
   it. Never alphabetize — the planner's ordering is information (most
   important decision first).
6. **Glyph language is shared.** ◆ choice, ☑️/⬜ toggle, 🧠 memory, • changed,
   ✓/⚠ provenance. Telegram uses the same glyphs as text; the CLI uses them
   in `plan show` where the terminal supports Unicode and falls back to
   `[x]`/`[ ]` otherwise. Do not let each surface invent its own icons.

## Memory consent: the moment-by-moment UX

Memory is the feature's hardest consent problem and its best justification —
today route 2 ("plan approval is user approval") authorizes memory edits on
~3/4 of plans that no human ever sees.

- **Authoring.** The planner writes one toggle per note-cluster, phrased so
  yes-means-work ("Record the overlay's keymap conventions in the tui memory
  note?"), with `memory:` selectors the reviewer recognizes from `sase memory
  read`, and `requested:` quoting the human's words verbatim when — and only
  when — defaulting on. The `/sase_memory_write` skill template carries this
  rule; the old "do not edit memory" prose disclaimers (65 in the host
  sample) become unnecessary and should be called out in the skill migration
  notes so planners stop writing them.
- **Propose-time check (planner still alive).** Word-for-word match against
  human-written chain text only (prompt, feedback, Q&A answers — never
  agent-written prompts). Failure is a fixable validation error naming the
  decision and showing the quote vs. the closest human text, so the planner
  can flip the default to `false` or fix the quote in the same turn.
- **Gate-build check (fail closed).** Unverified `true` is forced to off and
  flagged `⚠ request not found` in every surface. The review still proceeds —
  blocking the whole plan on one quote mismatch would punish the reviewer for
  the planner's error — but the outcome line visibly changes to `no memory
  edits`, which is exactly what the reviewer must notice.
- **`%auto` behavior.** `%auto` takes every default (verified `true` applies;
  unverified stays off) and its notification lists each decision taken marked
  `auto` with `decided_by: auto` stamped in the plan. An unrequested memory
  change that `%auto` left off becomes a `memory` task bead via
  `/sase_new_task` (no human saw it); a human's explicit off files nothing.
  I side with the lead here against hold-for-human: holding every
  memory-bearing `%auto` plan hostage contradicts the user's own request to
  run unattended, and contradicting the user's words with their own quote
  verified is worse UX than transparent auto-resolution.
- **Coder consumption.** The host appends the short "Reviewer decisions
  (final)" block (enum keys + booleans, `ask` quoted as data) after
  "Implement it now", plus "Memory edits are authorized for: tui.md. No other
  memory note." Epic phases see a DECISIONS section in `sase bead read`.
  Anything not covered is not authorized — and the later finalizer guard
  (advisory → enforcing, beta-flagged) checks diffs against accepted memory
  decisions, with the honest caveat that it stops *publishing* unauthorized
  edits, not the write itself.

## Authoring UX (the planner's side)

Good review UX cannot rescue bad planner output, so the authoring experience
needs equal care:

- **Frontmatter stays light.** The lead's grammar (no `type:` key — kind
  inferred from presence of `choices:`; strict `true`/`false` spelling;
  ≤120-char `ask` ending in `?`; ≤100-char consequence labels; `^[a-z][a-z0-9_]*$`
  ids ≤32 chars; max five decisions) is right. My one UX addition: the
  validator's duplicate-id and reserved-name errors must print the offending
  id *and* the nearest legal suggestion, because the fix loop runs inside a
  planner turn where every round trip costs a full agent cycle.
- **The planner rule in `/sase_plan`.** Ship the lead's sentence verbatim:
  "Ask now when the answer changes what you would write (tier, size, phase
  graph, architecture). Embed a decision when you can write one complete plan
  covering every answer, the difference is local, and you would defend your
  default. Never embed a decision you should make yourself." Add the
  combinatorial corollary: each decision must be referenced in the body (warn
  when not), and anything changing tier/graph/architecture goes to questions.
  This is what prevents five-toggle 32-combination plans.
- **Preview before propose.** `sase plan validate` (or propose dry-run)
  renders the Decisions section exactly as the TUI will show it — rows,
  defaults, chips — so the planner sees the review before filing it. The
  cheapest beauty win available: planners who see an ugly review write better
  asks.
- **Warnings, not errors, for body-scan heuristics.** "Body edits
  `sase/memory/` with no covering decision" must warn (146/807 plans mention
  memory read-only), while the precise diff check waits for the finalizer
  guard. A hard error here would train planners to avoid the word "memory"
  rather than to declare decisions.

## Beauty pass: the details that make it feel designed

- **Enter never moves.** Accepting defaults is one keystroke / one tap /
  one bare `approve` command on all three surfaces. Every new control must
  preserve that.
- **The outcome sentence is the feature's signature.** One line, always
  visible, always current. It turns defaults from an invisible trap into a
  readable promise.
- **Changed-means-colored.** The `•` marker plus accent color is enough;
  resist per-row "modified!" banners, confirmation dialogs, or a separate
  "review your changes" screen. Confirmations for confirmations are how
  consent UI dies.
- **Name it `decisions:`.** `gates:` promises gates that do not exist and
  `gate_options:` names the rejected mechanism (embedded gate JSON). The
  glossary term "Plan Decision" collides mildly with the decision-record web
  and gate decisions, but namespaces differ and the alternatives (`questions:`
  reads oddly for consents) are worse. Keep `ask`/`default`/`answer` — the
  three words tell the lifecycle in order.
- **Empty-state copy.** Zero-decision plans show "No reviewer decisions in
  this plan" in the TUI, omit the section in Telegram (no noise on a phone),
  and show an empty table with a one-line hint in `plan show`. Three surfaces,
  three densities, one meaning.

## Open questions (my recommendations)

1. **Direct-prompt memory edits:** keep the direct path (lead A4). Forcing a
   plan for "add X to the tui note" turns one turn into three with zero new
   information. Revisit only with a measured abuse signal.
2. **Memory under `%auto`:** verified default applies (lead's resolution).
   Holding for a human stalls unattended runs the user explicitly requested.
3. **Bead route 3:** yes, beads worked plan-first should follow this
   feature's rules — otherwise the bead path becomes the consent bypass. Needs
   its own small UX pass (what DECISIONS looks like in bead triage), deferred
   to the guard phase.
4. **Guard strictness:** fail the memory portion, commit the rest, and list
   uncovered paths. Failing an entire code+docs commit over one note edit
   teaches agents to bundle less, not to ask better. The refusal message must
   name the covering decision that would have authorized it.
5. **One residual risk to watch:** planners defaulting memory `true` with
   stretched quotes ("the user said 'notes' so this counts as requested").
   The word-for-word check plus forced-off flag handles the mechanics; the
   remaining defense is the override-rate metric (default vs. answer in the
   archive) per planner/model, reviewed periodically — not more UI.

## Sources and verification

Prior research (read via audited artifact reads):
`research:202610/plan_frontmatter_decisions/plan_frontmatter_decisions.md`
(lead consolidated report; I additionally saw its evidence tables and the
`decisions:`/compiling/review/recording/consumption/enforcement shape, and
adopt them).

Code I inspected directly in this checkout (paths relative to workspace
root; line numbers approximate to current tree):

- `src/sase/ace/tui/modals/plan_approval_modal.py:166` — left-column
  `Static("Decision", …)` section title (rename to Verdict); branch controls
  with `HOST_COLLECTED_PROPERTIES`.
- `src/sase/ace/tui/modals/plan_approval_gate_data.py:42` —
  `HOST_COLLECTED_PROPERTIES` (`feedback`, `coder_prompt`, `coder_model`,
  `epic_launch_mode`, `wait`, `capacity`); fallback tale/epic branch models.
- `src/sase/ace/tui/modals/plan_approval_decisions.py:42` —
  branch-resolution handler carrying `option_inputs` through to the result.
- `src/sase/ace/tui/widgets/typed_input_form.py:142` — `_EnumField`
  in-place cycling (≤5) and picker fallback; `_build_editor` chain
  confirming `bool` has no dedicated toggle today.
- `src/sase/notification_gates/model_inputs.py:42` — declared-input
  vocabulary (`word/line/text/path/agent/int/bool/float/enum`, `enum`
  requires non-empty `choices`, `default` validated at parse time).
- `src/sase/plan_gate.py:51` — tiered plan-gate entry point;
  `_plan_gate_shared.py:12` option ids (`approve/commit/reject/feedback`).
- `sase plan approve --help` (run 2026-10-07) — current flags
  (`-n/--dry-run`, `-k`, `-m`, `-P`, `-p`, `-w`), no `-D` yet; direct-file
  approve path exists.
- `src/sase/default_config.yml` gate-modal bindings region — Enter/Space/
  numbered-branch keymap home for the new bindings.
- Telegram typed-input behavior (`enum` keyboards, skip-to-default,
  `bool`-as-typed-reply) as verified in the lead report against
  sase-telegram `gate_inputs.py` / `gate_input_steps.py` / `formatting.py`
  (linked repo not checked out in this workspace, so cited from the lead's
  source-checked evidence rather than re-verified here).

Deliberately not consulted: peer swarm reports for this question
(`*__cdx.md`, `*__cld.md`, `*__grk.md`, `*__gem.md`) — per the swarm
instructions I checked filenames only to avoid overwriting and did not open
any peer contents. The `__mus` suffixed file under
`202610/plan_frontmatter_decisions/` is prior-swarm work, likewise unopened.
