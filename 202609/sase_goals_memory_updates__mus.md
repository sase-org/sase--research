# Memory file updates for after the sase goal epics land

_Research note · 2026-09-27 · project: sase · status: **advisory, nothing built yet**_

**Question.** What `sase/memory/` updates (if any) should be made once all sase goal
epics are complete? No goal epic has been planned yet; `sase goal` does not exist at
HEAD and the string "goal" appears nowhere under `sase/memory/`.

**Bottom line.** Yes, make updates, but keep them small: one decision record, one new
reference note, one new glossary strand, and one-line touch-ups (plus `[[link]]`s) in
four existing notes. Touch nothing else. Write the decision record before G1 is
planned; carry every other edit as a named step inside the G-epic plan that lands the
behavior it documents, so plan approval authorizes each memory write. Keep all soak
numbers, precision thresholds, and notification-volume statistics out of memory — they
are ephemeral and belong in the epic plans and reports.

Recommended set (details in §4):

| # | Memory change | When | Authorized by |
| --- | --- | --- | --- |
| 1 | New decision record: host binds, agents claim, users settle | Now, before the G1 plan | This report + `/sase_memory_write` routing (or a `memory` task bead) |
| 2 | New reference note `sase_goals.md`: the agent-facing goal contract | G1 (lifecycle/CLI) → extended G3 (claims), G4 (drafts), G5 (tab), G6 (attention) | Named steps in each epic plan |
| 3 | New glossary strand `goal` (claim, GoalVerify, draft folded in) | G3, when `claim` vocabulary freezes | G3 plan steps |
| 4 | `sase_beads.md`: bead-or-goal rule + link | G1 | G1 plan steps |
| 5 | `sase_artifacts.md`: `goal:` kind + 4 new relations | G1 (kind), G2–G4 (one relation each) | Respective epic plans |
| 6 | `xprompts.md`: `%goal` row, `@goal` cite-vs-bind, `SASE_GOAL_ID` | G2 | G2 plan steps |
| 7 | `tui.md`: one link line to the goals note | G5 | G5 plan steps |

Explicitly **no change**: `cli_rules.md`, `sase_flags.md`, `generated_skills.md`,
`rust_core_backend_boundary.md`, `gotchas.md`, `lint_and_test.md`, `dispatch.md`,
`task_types/`, `sase_sizes.md`. Reasons in §5.

---

## 1. Sources and method

Read (all in the research sidecar, opened via `sase repo open research`):

- `202609/sase_goals_epic_roadmap/sase_goals_epic_roadmap.md` — the lead synthesis:
  six epics (G1 ledger, G2 deterministic binding, G3 claims + `GoalVerify` gate, G4
  drafts/naming/adoption/answer-ack, G5 Goals tab, G6 attention cutover) plus a
  `JumpToAgent` bug pre-task, sibling beads with `sase bead dep`, per-epic flags
  removed before landing, and a ≥7-day metric-gated soak before G6.
- `202609/sase_goals_design/sase_goals_design.md` (§§4–5) — the destination: lifecycle
  `draft → active (Running/Idle) → review → done / dropped`, host binding ladder,
  `builtin@goal` (`claim`/`keep_open`) after commit, one `GoalVerify` gate per claim,
  human-only settle verbs, `goals/` ledger co-hosted in the beads repo, `goal:` kind
  with relations `pursues`/`evidences`/`defines`/`follows`, `%goal` vs `@goal:<id>`,
  `SASE_GOAL_ID`, the intake block, the `/sase_goal` skill, and the attention cutover.
- `202609/sase_goals_persistence.md` — named→pushed→fetched; drafts never leave the
  machine; claims/settlements push synchronously; freshness is honest, not instant.
- `202609/sase_goals_why_not_beads.md` — reuse the beads *repository*, not the beads
  *model*; the durable rule: **if you would schedule it, it's a bead; if you would
  verify it, it's a goal.**
- `202609/xprompt_swarm_goals.md` — swarm mechanics (one shared draft, first-namer
  wins, contributors `keep_open`, lead claims), landing in G4.

Checked against HEAD myself:

- `sase goal --help` fails: there is no `goal` subcommand (expected — designed, not
  built).
- `grep -ri "goal" sase/memory/` finds nothing goal-related (one false positive in a
  decisions strand about tier vocabulary).
- `sase memory read` used for all reference-memory bodies cited here
  (`sase_beads.md`, `sase_artifacts.md`, `xprompts.md`, `tui.md`, `sase_flags.md`,
  `generated_skills.md`, `cli_rules.md`, `dispatch.md`, `lint_and_test.md`,
  `glossary:stitch` as a strand-format example).

I did **not** open, read, or consult any peer report from this swarm (`__cdx`,
`__cld`, `__grk`, `__gem`); conclusions below are my own. Per the roadmap's own
corrections table I treat the lead synthesis (not any single researcher report) as the
settled plan, and flag where the plan is still contingent (§6).

## 2. What goals changes for agents (the durable facts memory must capture)

Filtering the design/roadmap for facts an agent needs on every turn *after* landing,
versus facts that belong in code, plans, or reports:

1. **A new noun with its own lifecycle.** Goal: `draft → active → review →
   done/dropped`, Running/Idle derived from contributor liveness. Orthogonal to bead
   status; a goal's `claim` is the opposite end of the lifecycle from a bead's
   `claimed`.
2. **Inverted authority.** Agents may only `claim` (via the `builtin@goal` finalizer:
   `claim` or `keep_open` with a progress note). `verify / reject / drop / reopen /
   merge` are human-only and refused inside agent runs — mirroring "agents never
   hand-edit bead status."
3. **Allowed agent verbs are few.** `list`, `show`, `name`, `adopt` (plus `doctor`
   off-path). Agents create no goal except their own draft; discovered follow-up work
   stays as task beads.
4. **Binding is host-owned.** `%goal:<id>` / `%goal:new` binds; `@goal:<id>` only
   cites (expands to card text, binds nothing). `SASE_GOAL_ID` is convenience, not
   source of truth — same standing as `SASE_PLAN`.
5. **A new artifact kind and four relations.** `goal:` joins the kind catalog;
   `pursues`/`defines` land with G2, `evidences` with G3, `follows` with G4 (per the
   roadmap's resolution, not the design's P-table).
6. **A new notification semantics.** Success completions go silent; the claim
   (`GoalVerify` gate, `JumpToGoal` row, `⌖` glyph, `inbox: ⌖N`) is the loud signal.
   Read/dismiss is never a decision. Answer-only claims settle on acknowledgement
   (`done · acknowledged`, undoable).
7. **Bead-or-goal triage.** Schedule it → bead; verify it → goal.

Everything else — soak thresholds (≥7 days, ≥100 claims, ≥90% shadow coverage, ≥80%
precision, ≤5 merges/100, 0 orphans), latency targets (<50 ms list), phase tables,
flag strategy — is plan/report material, not memory.

## 3. Guiding principles

- **Memory is per-turn tax.** Every core token is paid on every turn; every reference
  note costs a read. The `/sase_memory_write` skill says it plainly: prefer rewriting
  an existing note over adding one, prefer deleting a stale line over appending a
  caveat, prefer `type: reference` over `type: core`.
- **One home for the contract, links everywhere else.** The lifecycle, verb lists,
  and cite-vs-bind distinction must live in exactly one note. The four existing notes
  that touch goals get one sentence plus a `[[sase_goals.md]]` link — not a copy.
- **No new core memory.** Nothing about goals needs to be inlined into every turn.
  The decision descriptor roster and the glossary descriptor roster each gain one
  line (that is how those webs work); no flat core note should grow a goals section.
- **Authorization routes the timing.** Memory writes need (a) the user's prompt, (b)
  a named step in an approved plan, or (c) an assigned bead's description — nothing
  else (design docs and researcher conclusions don't count). Since no goal epic is
  planned yet, the only legitimate near-term write is #1 below via explicit user
  approval or a `memory` task bead; everything else rides as named steps in the
  G-epic plans, confirmed through `/sase_questions` if the user didn't ask for it.
- **Each edit ends with `sase memory init`.** Authorization for the edit covers the
  republish; never hand-edit `AGENTS.md` or provider shims.

## 4. Recommended updates, file by file

### 4.1 #1 — New decision record (before G1; this is roadmap first-move #1)

**Form:** `sase/memory/decisions/<slug>.md`, e.g. `host-binds-agents-claim-users-settle.md`,
with `keyword:`, `aliases:`, `summary:`, `metadata.status: accepted`, following the
existing record shape (claim / why + rejected alternatives / cost / reopens-when).

**Claim (proposed):** *The host binds every LLM turn to exactly one goal; agents name
drafts and claim outcomes with evidence; only users settle goals.* So six epic plans
cite it instead of re-arguing R1/R2/R4 (§2.2 of the design).

**Why:** the invariant is load-bearing across all six epics (binding ladder,
finalizer eligibility, human-only verbs, attention cutover) and is exactly the kind
of cross-epic contention a record exists to settle once.

**Cost (state honestly):** the record freezes the claims-before-drafts order and the
no-fuzzy-join rule; if the G6 soak shows adopt-before-name failing (duplicate goals
above the merge budget), the record must be amended, not silently ignored.

**Reopens when:** claim precision per model, merge rate, or orphan count miss the G6
gate thresholds over the soak — i.e. the invariant isn't surviving contact with real
traffic.

**Routing:** use `/sase_memory_write` first; the user prompt for *this* research does
not authorize a write, so either ask the user directly or file a `memory` task bead
naming the path and the claim above.

### 4.2 #2 — New reference note `sase_goals.md` (G1, extended G3–G6)

**Form:** `type: reference`, parent `AGENTS.md`, one-line description. This is the
single agent-facing goal contract. Sketch (final wording belongs to the epic workers,
kept under ~100 lines):

- Lifecycle in one table (`draft · active · review · done · dropped`; Running/Idle
  derived, not stored) and the sentence "Goal status is not agent status."
- Agent verbs: `list / show / name / adopt` (+ `doctor` off-path); agents create no
  goal except their own draft; follow-up work stays as task beads (`/sase_new_task`).
- Authority: finalizer `claim` vs `keep_open`; human-only
  `verify/reject/drop/reopen/merge` refused in agent runs.
- Cite vs bind: `@goal:<id>` cites, `%goal:<id>` binds, `%goal:new` opts out;
  `SASE_GOAL_ID` is convenience, like `SASE_PLAN`.
- Claim minimum: resolvable refs + 1–3 check-it steps + gaps; receipts are
  machine-local snapshots; `receipts-prove-before-they-skip` applies.
- Surfaces: Goals tab lanes, `⌖` glyph, `v r x l e m a p n / P h` keys, Agents-tab
  chip, `inbox: ⌖N`; success-silent / claim-loud; answer-ack default with undo.
- Links: `[[sase_beads.md]]`, `[[sase_artifacts.md]]`, `[[xprompts.md]]`,
  `[[tui.md]]`, `[[decisions/<record>]]`.

**Why one note instead of scattering:** the same lifecycle would otherwise be copied
into beads, artifacts, xprompts, and TUI notes and drift within a quarter. The
`/sase_memory_write` preference for rewriting existing notes is about avoiding *new
concepts*; goals is genuinely a new concept with a new CLI noun, tab, gate kind, and
artifact kind, so one note is cheaper than four overlapping sections.

**Phasing:** land the skeleton in G1 (lifecycle + CLI verbs + bead-or-goal pointer);
extend in G3 (claims/evidence/`GoalVerify`), G4 (drafts/naming/adoption/answer-ack),
G5 (tab/keys), G6 (attention semantics). Each extension is a named plan step in that
epic.

### 4.3 #3 — New glossary strand `goal` (G3)

**Form:** `sase/memory/glossary/goal.md`, keyword `goal`, following the strand shape
(short definition + aliases). Proposed coverage in one strand: goal (identity
`goal:<id>`, title/outcome), draft, claim (with check-it/evidence/gaps pointer),
`GoalVerify` gate. Do **not** create separate strands for claim, draft, standing
goal, or `GoalVerify` — four roster lines for one feature is exactly the sprawl the
glossary's one-line estimated cost warns against; fold them as aliases/mentions in
the `goal` strand and let `link_reference: implicit` surface them.

**Why G3:** the `claim` vocabulary (claim sentence ≤280 chars, evidence strength
badge, `evidences` relation) freezes in G3; naming the strand earlier risks
redefining it mid-program.

### 4.4 #4 — `sase_beads.md`: bead-or-goal rule (G1)

Add one paragraph plus `[[sase_goals.md]]`: the triage sentence from the why-not-beads
note ("if you would schedule it, it's a bead; if you would verify it, it's a goal"),
the word-collision warning (bead `claimed` = runner reserved; goal *claim* = agent
says done), and that phase workers still file `PROPOSED FOLLOW-UP:` on their phase
bead (goals change nothing about that path). G1 owns it because G1 is when the
second work-item system first becomes real for agents doing manual `sase goal` work.

### 4.5 #5 — `sase_artifacts.md`: kind + relations (G1–G4)

- G1: `goal:` joins whatever passage lists built-in kinds (with `sase artifact read
  goal:<id>` rendering the card), since G1 ships the artifact kind.
- G2: `pursues` / `defined-by` (`defines`) added to the closed relation registry
  table as projection-sourced (like `produced-by`/`launched-by`/`awaits`).
- G3: `evidences` / `evidenced-by`.
- G4: `follows` / `followed-by`.
- Each addition is one registry row plus the `[[sase_goals.md]]` link; the semantic
  detail lives in the goals note, not here.

### 4.6 #6 — `xprompts.md`: directives (G2)

G2 generalizes directive inheritance and adds `%goal`, so the Directives table gains
the `%goal:<id>` / `%goal:new` row (with the `%tab`-travels note as the model), plus
one line that `@goal:<id>` cites without binding and that `SASE_GOAL_ID` mirrors the
`SASE_PLAN` standing. The intake-block text, finalizer payload shape, and `/sase_goal`
skill text live in code/skill sources, not memory — do not copy them here. (The
design's "`sase_final` gains one paragraph" is a skill-text change, covered by
`generated_skills.md` rules as-is.)

### 4.7 #7 — `tui.md`: one link line (G5)

`tui.md` is an entry point, not a surface catalog: add one line pointing at the Goals
tab section of `[[sase_goals.md]]` (and, if the worker judges the keymap table load-
bearing, the `v r x l e m a p n / P h` keys — though `gotchas.md` already routes
`default_config.yml` registration, so no gotchas change is needed). G5 is the only
epic with golden churn; that rule ("zero golden churn outside G5") belongs in the G5
plan's land section, not in memory.

## 5. Considered and rejected (do not write these)

- **`cli_rules.md` — no change.** The G1 CLI already conforms (alphabetical options,
  short aliases, bare-`sase goal` → `list` default). The G1 planner verifies
  conformance; a passing check needs no memory edit.
- **`sase_flags.md` — no change.** Per-epic beta flags removed before landing are
  exactly what the note already prescribes; an umbrella `goals` flag is allowed only
  if the user asks. If the user does ask, that decision goes in the decision record
  (#1), not the flags note.
- **`generated_skills.md` — no change.** `/sase_goal` is generated from
  `src/sase/xprompts/skills/`; commit-then-deploy and CLI/skill-contract-sync rules
  already cover it.
- **`rust_core_backend_boundary.md` — no change.** The litmus test already routes the
  goal wire, reducer, resolver, and `decide_goal_action` to `sase-core`; the G-epics
  move the pin per the existing rule.
- **`gotchas.md`, `lint_and_test.md`, `symvision.md`, `dispatch.md` — no change.**
  Keymap registration, `just check` discipline, and `%dispatch`/session-inheritance
  mechanics are unchanged by goals (goal inheritance rides the existing session-
  successor and tab-inheritance generalization in code).
- **No new `task_type`.** The prior `task_type: goal` proposal was rejected in the
  outcomes synthesis and again in why-not-beads; goal-adjacent follow-up work is
  `bug`/`feature`/etc. as today.
- **No `sase_sizes.md` change.** The ≤7-phase epic rule lives in the roadmap, not the
  size scale; don't smuggle phase-count caps into the size note.
- **No soak metrics in memory.** Thresholds, precision rates, and volume comparisons
  are point-in-time judgments — memory that quotes them rots on arrival.

## 6. Contingencies (what would change this recommendation)

| If … | Then … |
| --- | --- |
| G1 planning finds the ledger needs different verbs (e.g. `verify` re-enters G1) | Reshape the `sase_goals.md` skeleton in the G1 plan; the note is reference, so reshaping is cheap |
| The user orders an umbrella `goals` flag | Record it in the decision record as the allowed exception (precedents: `typed_launch_units`, `provider_drain`); still no `sase_flags.md` change |
| Drafts-before-claims wins after all (the close runner-up, §6 of the roadmap) | Move the glossary strand and claim sections from G3 to the binding epic; file count unchanged |
| Relations land centrally (all four in G1, per cld) rather than per-epic | Collapse the three `sase_artifacts.md` steps into the G1 plan |
| G4 overflows 7 phases and standing goals move to G6 | The goals note gains its Standing-goals paragraph in G6 instead; no extra note |
| The program stalls after G3 (claims without drafts/tab) | The G1+G3 subset of this recommendation still stands alone; G4–G6 rows become conditional |

## 7. Suggested first moves, in order

1. Route this report through `/sase_memory_write` (run `sase skill use
   sase_memory_write` with a reason): either get explicit user approval to write the
   decision record now, or file a `memory` task bead naming the path and claim in
   §4.1. This is also the roadmap's first move, and it unblocks six plans citing one
   invariant.
2. When writing **only the G1 plan**, include as named steps: the `sase_goals.md`
   skeleton, the `sase_beads.md` paragraph, and the `goal:` kind row — each ending
   with `sase memory init`. Name G2–G6's memory steps as successor scope, not G1
   work.
3. Add a standing instruction to each G2–G6 plan template: "extend `sase_goals.md`
   and its linked registry rows for this epic's contract; quote no numbers that the
   soak could invalidate."
4. After G6, do a memory-only pass: confirm no `sase/memory/` line still describes
   success-ping/✅-unread behavior as current, and confirm the decision record needs
   no `superseded_in_part` mark from soak learnings.

*Method note: this report was written without consulting the sibling `__cdx`,
`__cld`, `__grk`, `__gem` reports of this swarm. Quoted code paths
(`run_agent_runner_finalize.py:469`, `bead_fast_path`, `_tab_inheritance`) and bead
statistics are taken from the cited lead syntheses, which verified them against HEAD;
I re-verified only the memory-tree and CLI facts in §1. Exact memory wording should
be authored by the epic workers against the landed behavior, not frozen from this
report.*
