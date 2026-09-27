# Memory after the Goals epics: what to write, what to skip, and when

_Independent research · researcher `grk` · 2026-09-27 · project: sase_

**Question.** Once every SASE Goals epic is complete (none have been planned yet), which
memory files should be added or updated?

**Primary context.** [sase_goals_epic_roadmap.md](sase_goals_epic_roadmap/sase_goals_epic_roadmap.md)
(lead synthesis: six sibling epics G1–G6 plus one bug task). Destination contract:
[sase_goals_design.md](sase_goals_design/sase_goals_design.md). Domain split:
[sase_goals_why_not_beads.md](sase_goals_why_not_beads.md). Persistence:
[sase_goals_persistence.md](sase_goals_persistence.md).

**Method.** Audited reads of the roadmap and design; `sase memory read` of the live
beads, artifacts, flags, sizes, CLI, TUI, xprompts, and generated-skills notes;
glossary and decision strand shapes; the generated-note templates under
`src/sase/main/init_memory/templates/`; the skill sources under
`src/sase/xprompts/skills/`. No peer reports from this swarm were consulted.

---

## 0. Bottom line

**Do not wait until G6 closes to write all of this.** Most agent-facing memory should
land with the epic that makes the contract true. Waiting until "all epics complete"
would leave G2–G5 agents without the rules they need, and would freeze a six-epic
rollout story into always-loaded context.

**Do run a completion sweep after G6.** That sweep is small: make every note describe
the *steady state* (no flags, no G1–G6 numbering, no "alongside success pings"), fill
any gaps the incremental landings left, and delete leftover rollout language.

The completion-state corpus is:

| Action | Path | Kind |
| --- | --- | --- |
| **Add** | `sase/memory/sase_goals.md` (via a new generated template, sibling to beads/artifacts) | reference, deployed to every SASE-managed project |
| **Add** | `sase/memory/glossary/goal.md` | glossary strand |
| **Add** | `src/sase/xprompts/skills/sase_goal.md` | generated skill (`/sase_goal`) |
| **Add** | `sase/memory/decisions/host-binds-agents-claim-users-settle.md` | decision (write *before* G1; still load-bearing after G6) |
| **Add** | `sase/memory/decisions/goals-are-not-beads.md` | decision (write when G1 lands the ledger, or at the sweep if it was skipped) |
| **Patch** | `memory-sase.template.md` → generated `sase.md` | one sentence in Final Declaration |
| **Patch** | `memory-sase-artifacts.template.md` Model paragraph; glossary `artifact.md` and `artifact-reference.md` | `goal:` as a kind |
| **Patch** | `memory-sase-beads.template.md` | one paragraph: beads are scheduled work; goals are verified intent |
| **Patch** | `glossary/sase-gate.md` | `GoalVerify` in the typed-kinds list |
| **Patch** | `glossary/nav-item.md`, `nav-section.md` | Goals tab rows |
| **Patch** | `xprompts.md` | `%goal` directive row |
| **Patch** | `sase_final.md` skill | `keep_open` / `claim` payload |
| **Patch** | `sase_plan.md`, `sase_run.md`, `sase_notify.md`, `sase_new_task.md` skills | inheritance, propose-names-goal, GoalVerify, "do not file a goal" |
| **Patch** | `tui.md` + `tui_perf.md` | Goals tab as a TUI surface; G5 budgets |
| **Patch** | `rust_core_backend_boundary.md` | one-line example: ledger / binding / `decide_goal_action` |
| **Leave alone** | `gotchas.md`, `cli_rules.md`, `sase_flags.md`, `sase_sizes.md`, `task_types/*`, core essays, a goals *web* | already sufficient, or would add tokens without changing agent behavior |

**Do not put Goals in core memory beyond one sentence.** The host already injects a
~40-token bound line or an ~80-token draft-intake block on every turn. A second copy of
that text in `AGENTS.md` is paid again, forever, for every agent in every project.

---

## 1. What "complete" means for memory

The roadmap's program is:

```text
pre ─► G1 ledger ─► G2 binding ─► G3 claims ─┬─► G4 drafts ─┐
                                             └─► G5 tab ────┴─► soak ≥7d ─► G6 cutover
```

After G6, these things are *unconditionally true*:

1. Every LLM agent turn has exactly one primary `goal_id` before the provider starts.
2. The host bound it from facts it already had, or created a machine-local draft the
   agent named or adopted.
3. A required `builtin@goal` finalizer, after commit, makes the turn choose `keep_open`
   or `claim`. A claim is not a close.
4. You settle Review through a `GoalVerify` gate (or by opening an answer).
5. Successful agent completions are quiet. Claims, errors, questions, and approvals
   still ping.
6. There is no `goals` feature flag. Per-epic beta flags were removed before each epic
   landed (`sase_flags.md`).

Memory should describe that world, and only that world. The six-epic split, soak
thresholds, shadow-coverage percentages, and "success pings stay on until G6" are
research and plan text. They are not agent context.

### 1.1 Three windows, not one dump

| Window | What memory is for | What to write |
| --- | --- | --- |
| **Before any plan** (now) | Stop six plans from re-arguing the same invariant | One decision record: *the host binds, agents claim, users settle*. The roadmap already names this as first move #1. |
| **With each epic** | Teach the contract that just became true | G1: glossary stub + `goal:` kind. G2: `%goal` + bound-line. G3: `sase_final` + `builtin@goal` fail-open. G4: `/sase_goal` + draft name/adopt + full `sase_goals.md`. G5: TUI notes. G6: notify/attention. |
| **After G6** | Steady-state sweep | Delete flag/rollout wording; confirm every note matches HEAD; add the "goals are not beads" decision if it was deferred; regenerate `AGENTS.md` via `sase memory init`. |

The completion sweep is real work. It is not where the corpus is *invented*.

---

## 2. How the current corpus is shaped, and why that shape should be reused

Live memory (this workspace, `sase memory list`):

- **Loaded core** ≈ 5.2k tokens across 9 files. `sase.md` (generated), `gotchas.md`,
  `rust_core_backend_boundary.md`, plus always-inlined web descriptors (`glossary`,
  `decisions`, `task_types`).
- **Reference notes** are on-demand: `sase_beads.md` (~2.0k tokens), `xprompts.md`
  (~3.0k), `sase_artifacts.md` (~1.1k), `sase_flags.md`, `tui.md` and children.
- **Glossary** is 63 strands, bodies never inlined. **Decisions** are 22 records;
  only the roster is always loaded.

Three patterns already in the tree tell you where Goals belongs:

1. **A domain with agent-facing rules that `-h` cannot tell you** gets a reference
   note. `sase_beads.md` is the template: "this note covers only what that help output
   cannot tell you." Goals has the same shape — human-only verbs, draft vs named,
   claim vs settlement, fail-open, "do not create a goal for discovered work."
2. **A first-class noun** gets a glossary strand. Bead is not a glossary term today
   (it lives in the beads note); Gate, Artifact, Receipt, and Tool Run are. Goal is
   closer to Gate/Artifact: it is cited as `goal:<id>`, it has a tab, and the word
   *claim* collides with bead `claimed`. A strand is how you pin that collision.
3. **An architectural choice with rejected alternatives** gets a decision record, not
   a design dump. The decisions descriptor says so: a record is not a subsystem
   overview. Two records are justified; five are not.

`corpus-before-mechanism` also applies, inverted: do not invent a *goals memory web*.
There is one domain, not a catalog of independent strands. A web would be mechanism
ahead of corpus.

### 2.1 Generated notes cannot be hand-edited

`sase.md`, `sase_artifacts.md`, `sase_beads.md`, and `sase_sizes.md` are produced from
`src/sase/main/init_memory/templates/` (`memory-sase.template.md`,
`memory-sase-artifacts.template.md`, `memory-sase-beads.template.md`,
`memory-sase-sizes.template.md`). `/sase_memory_write` already says a generated note
refuses direct edits — change the template.

The artifacts note's relation list is interpolated from the live registry
(`{{ artifact_relation_rows }}`). Once G2–G4 register `pursues`, `defines`,
`evidences`, and `follows` as projection relations, `sase memory init` will print them
with no extra prose. Do not hand-maintain that list.

Skills are the same story: edit `src/sase/xprompts/skills/*.md`, land, then
`sase skill init` from a clean canonical tree (`generated_skills.md`).

---

## 3. Why a new note, not a beads addendum

[sase_goals_why_not_beads.md](sase_goals_why_not_beads.md) is the memory-design
constraint: reuse the beads *repository*, not the beads *model*. Folding Goals into
`sase_beads.md` would teach the wrong noun in the file agents already open for
scheduled work.

The collisions that memory has to prevent:

| Word | Bead meaning | Goal meaning |
| --- | --- | --- |
| claimed | runner reserved the bead | agent says the outcome is done |
| close | agent closes its own work | you verify, reject, or drop |
| draft | `open` task, already shared | machine-local, unpublished until named |
| done | agent ran `sase bead close` | you settled Review |

A future feature will ask "bead or goal?" The answer belongs in two places: a short
paragraph at the top of `sase_beads.md` *and* a decision record, both pointing at
`sase_goals.md`. The test from the why-not-beads note is the right sentence:

> If you would schedule it, it is a bead. If you would verify it, it is a goal.

---

## 4. Recommended additions

### 4.1 `sase/memory/sase_goals.md` — the one new reference note

**Type:** `reference`, `parent: AGENTS.md`.

**Description (one paragraph, for the AGENTS.md list):**

> Read before naming or adopting a draft goal, claiming or keeping a bound goal open,
> citing `goal:<id>`, or treating a goal as if it were a bead.

**Deploy it as a generated project note**, sibling to `sase_beads.md` /
`sase_artifacts.md` / `sase_sizes.md`:

- Add `memory-sase-goals.template.md`.
- Register it in `_GENERATED_PROJECT_LONG_MEMORY_SPECS` in
  `src/sase/main/init_memory/root_rendering_notes.py`.
- Every SASE-managed project then receives the same agent-facing rules. That matches
  the feature: `/sase_goal` is a globally deployed skill, `builtin@goal` runs on every
  bound turn, and the ledger is per-project.

A sase-project-only note (like `tui.md`) would be the wrong scope. `tui.md` is for
people changing sase's TUI. Goal rules are for *every* agent that names, adopts, or
claims.

**What the body should contain** (modeled on beads: rules `-h` cannot tell you):

1. **Noun.** A goal is verified intent. It is not scheduled work. Link
   `[[sase_beads.md]]` and `[[decisions:goals-are-not-beads]]`.
2. **Who does what.** The host binds. Agents `list` / `show` / `name` / `adopt`.
   Humans `new` / `verify` / `reject` / `drop` / `reopen` / `merge`. Status verbs are
   refused inside agent runs.
3. **Draft vs bound.** A draft-bound turn's first act is name or adopt. Naming is
   compare-and-swap. Adopting a Review goal retracts the claim. An adopted draft never
   publishes. Do not restate the injected intake block; point at it.
4. **Finalizer.** Bound turns choose `keep_open` or `claim` through `/sase_final`.
   Phase agents and live contributors cannot claim. A goal problem never fails the
   turn (`keep_open` + diagnostic; `sase goal audit` surfaces it).
5. **Claim ≠ settlement.** Evidence must be resolvable, mostly host-gathered.
   `@commit` is refused when commit was deferred. You close the goal.
6. **Discovered work.** Follow-ups stay task beads. Agents do not mint extra goals.
7. **Citations.** `sase artifact read goal:<id>` / `@goal:<id>`. Prompt bodies live in
   the agents sidecar; the goal stores ref + digest.
8. **Standing goals.** Routine (chop) runs bind to a per-routine standing goal and
   never claim.

**Size cap.** `sase_beads.md` is ~2.0k tokens because of task-triage ritual. Aim this
note at **800–1,200 tokens**. CLI option lists, TUI key tables, on-disk layout
(`STORE.json`, `live/`, `goals-hot.json`), and soak metrics stay out — those are `-h`,
`default_config.yml`, `sase goal doctor`, and research.

**When.** Author the template in G4 (first epic whose agents *must* name/adopt). G3
can ship a stub paragraph inside `sase_final` so epic-bound claims work without the
full note. After G6, strip any "drafts land in G4" / flag wording.

### 4.2 Glossary strand `goal.md`

```yaml
---
keyword: Goal
aliases: [sase goal, draft goal]
---
```

One short definition:

- Durable `goal:` artifact for an outcome the host bound, an agent claimed, and a
  human settled.
- Lifecycle `draft → active → review → done | dropped` (Idle/Running are derived, not
  stored).
- Distinct from a bead. A goal *claim* is not bead status `claimed`.
- Mechanical members inherit and never decide. Routines bind to a standing goal.

Do **not** add separate strands for Claim, Draft, GoalVerify, or Check-it. Those are
roles inside Goal. GoalVerify is a typed gate kind — mention it on `glossary:sase-gate`.

**When.** G1 can add a one-sentence stub ("a durable intent record with a `goal:`
id"). Expand at G4 once drafts exist. After G6, confirm the lifecycle sentence matches
HEAD.

### 4.3 Skill `src/sase/xprompts/skills/sase_goal.md`

The design is explicit: **keep `/sase_goal`, never a mandatory `/sase_new_goal`.**
The host enforces the invariant; the skill is used when the host says the goal is
still a draft.

Teach only `list` / `show` / `name` / `adopt`. Point at `/sase_final` for claims.
Refuse to document human verbs as agent actions.

**When.** G3 ships list/show (roadmap G3 phase 6). G4 adds naming guidance. After G6,
no further skill shape change unless HEAD drifted.

### 4.4 Decision records

Decision records are immutable once accepted and their *roster lines* are always
loaded. Two records, not a web of six.

#### A. `host-binds-agents-claim-users-settle` — write *before* G1

This is the roadmap's first move. It is still the load-bearing invariant after G6.
Do not wait for completion to write it; six plans should cite it instead of
re-arguing it.

**Claim.** The host binds every LLM turn to exactly one primary goal before spawn.
Agents name or adopt only when the host created a draft. Agents claim; they never
settle. Humans verify, reject, or drop. A goal failure never fails the agent turn.

**Why.** `SASE_PLAN` is commit plumbing, not a "has a plan" signal; a mandatory
skill cannot enforce an invariant; five parallel researchers would mint five goals;
an agent-closed goal is the opposite of "tell me what to verify."

**Rejected alternatives.** Agent-created goals via `/sase_new_goal`; claims without
a Goal object; folding goals into beads; blocking the turn on a missing goal.

**Reopens when.** A launch path cannot be bound in the runner *and* cannot be bound
on `AgentUnitWire`; or claim precision stays below a published floor after G4 soak
*and* per-model policy cannot contain it.

Link `[[decisions/host-owned-completion]]`: `builtin@goal` is another host-owned
finalizer, not a supersession. Agents still do not close work; they submit a
declaration.

#### B. `goals-are-not-beads` — write with G1, or at the G6 sweep

**Claim.** Goals are a distinct domain. They may co-host in the beads repository and
copy beads infrastructure (hidden clone, event sourcing, Rust fast path). They do
not reuse the bead reducer, status machine, or close authority.

**Why.** Different noun (intent vs scheduled work), inverted authority (you close),
no `review` state on beads, word collision on *claimed*, O(unsettled) vs
O(everything) reads, TaskTriage ritual that would bury ~25 answer-goals/day in the
work queue.

**Rejected alternative.** `task_type: goal`.

**Reopens when.** Most goals map 1:1 to epics *and* answer-only goals are rare *and*
the bead store grows an unsettled-only hot path for its own reasons.

Do **not** add separate decisions for fail-open (fold into A), attention cutover
(that becomes a config default, per the roadmap: loud success pings as a config
field, not a flag), or co-hosting (an operational split-out of the `goals` role is a
config change, not a reopened architecture).

---

## 5. Recommended patches to existing memory

Each row is a *steady-state* edit. Land it with the epic in the "With" column; the
G6 sweep only confirms it and deletes rollout tense.

| File | With | Change |
| --- | --- | --- |
| `src/sase/main/init_memory/templates/memory-sase.template.md` → generated `sase.md` | G3 | In **SASE Final Declaration**, one sentence: when the finalizer context includes an assigned goal, the declaration chooses `keep_open` or `claim`; `/sase_final` covers the payload. Do not paste the intake block. Direct edits to `sase.md` are refused. |
| `memory-sase-artifacts.template.md` | G1 | In **Model**, add goals to the list of durable records ("…beads, agents, **goals**, Patches…"). Relation rows for `pursues` / `defines` / `evidences` / `follows` appear automatically once the registry has them (G2–G4). |
| `glossary/artifact.md` | G1 | Same noun list. |
| `glossary/artifact-reference.md` | G1 | Builtin kinds today are hardcoded `@stitch`, `@patch`, `@bead`, `@agent`, `@file`. Add `@goal` when `goal:` is in the compiled kind catalog. |
| `memory-sase-beads.template.md` | G1 or G4 | After **Types, Tiers, And Launching**, a short paragraph: beads are scheduled work; goals are verified intent; `sase bead work` on a bead linked to one unsettled goal binds the agent to that goal; discovered follow-ups stay task beads. Link `[[sase_goals.md]]`. Keep bead `claimed` defined in **Statuses** so the collision stays visible. |
| `glossary/sase-gate.md` | G3 | Typed kinds today: "plan, epic plan, question, launch, task triage". Add **goal verify**. Agents do not create this kind; the host does. Still useful so `sase gate` / notify skills do not look incomplete. |
| `glossary/nav-item.md`, `glossary/nav-section.md` | G5 | Today they name Agents, Services, Artifacts. Add the Goals tab: Review / Running / Idle lanes are nav sections; a goal row is a nav item; Standing and Done-today collapsed groups follow the same collapsed-banner rule as Agents. `sase-node.md` can stay Agents-only (nodes are the agent tree). |
| `sase/memory/xprompts.md` | G2 | Add `%goal:<id>` / `%goal:new` to the directives table, next to `%tab`. One line: inheritance reuses the `%tab` mechanism; settled goals refuse bind; `%goal:new` starts a new goal with a `follows` link. |
| `src/sase/xprompts/skills/sase_final.md` | G3 | New subsection **Goal action**. Mirror `bead_action`: `keep_open` vs `claim`; required claim fields (check-it steps, gaps, evidence refs the host already gathered); draft-bound payloads must include `name`; errors fall open to `keep_open`. Prepared-monitor path: predeclare the decision. This is the highest-leverage patch in the set — every normal turn runs it. |
| `sase_plan.md` skill | G2 | `sase plan propose` names or refines the goal from the plan's `title`/`goal` and stamps `goal_id`. Plan-mode launches skip the draft intake block. |
| `sase_run.md` skill | G2 | Child launches inherit the requester's `goal_id` unless the prompt sets `%goal`. Do not tell agents to add `%goal` on every `/sase_run`. |
| `sase_notify.md` skill | G3, then G6 | G3: `GoalVerify` is a typed gate projection, same bundle rules as PlanApproval. Dismissing a row does not settle the goal. G6: successful completions no longer create unread ✅ rows; claims remain the loud signal. |
| `sase_new_task.md` skill | G4 | One sentence near the top: discovered follow-up is a task bead, never a second goal. Prevents the obvious misuse once agents can `sase goal name`. |
| `sase/memory/tui.md` | G5 | Point at Goals as a first-class tab. Keep screenshot/perf children; do not add `tui_goals.md` unless G5 leaves more than a handful of Goals-only gotchas. |
| `sase/memory/tui_perf.md` | G5 | Record the G5 budgets as gotchas: projection refresh < 2 ms at n = 100; highlight → paint ≤ 16 ms; off-thread snapshot with change tokens. Reuse rules 1–2 (never block the event loop / pump). |
| `sase/memory/rust_core_backend_boundary.md` | G1 | One example sentence: goal ids, events, reducer, binding, `decide_goal_action`, and the `list`/`show` fast path live in sase-core. Python owns launch injection, TUI, and skill text. The litmus test already covers this; the example stops a later agent from putting the reducer in Python. |

### 5.1 Auto-updated, so do not duplicate

- **Artifact relation registry** in `sase_artifacts.md` — generated from code.
- **Task-type catalog** — Goals is not a task type. Do not add `task_types/goal.md`.
- **Glossary roster line** — `sase memory init` rebuilds `**GLOSSARY TERMS:**` from
  strand files.
- **Decisions roster** — rebuilt from strand summaries.

---

## 6. What not to add or change

These look tempting and would either waste tokens or teach the wrong thing.

| Candidate | Why skip |
| --- | --- |
| A Goals **memory web** | One domain, not a catalog. `corpus-before-mechanism`. |
| A core-memory **Goals** section | The host already injects per-turn goal text. Core is ~5.2k tokens today. |
| `gotchas.md` keymap reminder | It already says: change `src/sase/default_config.yml`. G5 keys belong there. |
| `cli_rules.md` | The design already follows it (alphabetical options, short aliases, bare `sase goal` → `list`). No new rule. |
| `sase_flags.md` | After G6 there is no goals flag. Permanent loud-success preference is a config field, which this note already distinguishes from flags. |
| `sase_sizes.md` | Goals are not sized by agents. |
| `task_types/*` | Explicitly rejected as `task_type: goal`. |
| Storage-layout memory (`live/`, `STORE.json`, hidden clone) | Implementation. `sase goal doctor` and docs own it. Persistence research is for planners, not every turn. |
| Rollout / G1–G6 / soak numbers in any note | Stale the day after G6. Keep them in the research sidecar. |
| TUI key table (`v r x l e m a p n / P h`) in memory | `default_config.yml` plus human docs. Agents do not press those keys. |
| Duplicating the intake block in memory | Already injected. A third copy will drift. |
| Editing `host-owned-completion` in place | Immutable. `builtin@goal` *composes* with it. Link from the new decision. |
| Home-memory copies of `sase_goals.md` | Goals are per-project. Generated *project* memory is the deploy path. |
| `sase_gate.md` skill rewrite | Agents do not author `GoalVerify`. A glossary mention plus `sase_notify` is enough. Custom gates stay custom. |

---

## 7. Token budget

Always-loaded cost of the recommended set after G6:

| Addition | Always loaded? | Approx extra tokens |
| --- | --- | --- |
| `sase.md` Final Declaration sentence | yes | ~40 |
| `rust_core_backend_boundary.md` example sentence | yes | ~30 |
| Decisions roster: 2 new summaries | yes | ~80 |
| Glossary roster: `Goal` (+ aliases) | yes | ~10 |
| `sase_goals.md` | no (description only in AGENTS.md) | ~40 in the reference list; 800–1,200 on demand |
| Glossary `goal.md` body | no | on demand |
| Skill `/sase_goal` | only when the runtime loads skills | not in AGENTS.md core |

Net always-loaded increase: **on the order of 200 tokens**, against a 5.2k loaded
baseline. That is the right order of magnitude. A core Goals essay would be 10× that
and would duplicate the injected bound line.

On-demand, agents working a draft pay the intake block (~80) plus `/sase_goal` plus,
if they open it, `sase_goals.md`. Bound epic turns pay the 40-token line plus the
`sase_final` goal subsection. That matches the design's own tax table.

---

## 8. Authorization and how to actually land the files

`/sase_memory_write` allows a write only when the user's prompt, an approved plan, or
the assigned bead names the change. A research note is not authorization.

Practical path:

1. **Now (before G1 is planned):** the user (or the G1 planner, after asking) records
   decision A via `/sase_memory_write`. That is the only memory write that should
   happen before code exists.
2. **Each epic plan** names its memory/skill/template edits in its phases, so plan
   approval *is* authorization. Put those edits in the same epic as the contract they
   describe — G3's `sase_final` paragraph in the G3 skills phase, not in a later
   "docs" epic.
3. **G6 land / completion sweep:** one explicit phase (the roadmap already has
   `unflag-and-measure`: "flag removed, docs, …") should list the sweep: delete
   rollout wording, add decision B if missing, run `sase memory init`, deploy
   `/sase_goal` from the landed tree per `generated_skills.md`.
4. If an agent finds a stale note *after* G6 without that authorization, it files a
   `task(memory)` bead (`path` + `proposed_change`) and does not edit.

Do not file a stack of memory task beads *now* for a feature that has no plan. They
would describe a future contract, rot during G1–G5, and trip
`corpus-before-mechanism` in spirit: notes about code that does not exist.

---

## 9. Completion-sweep checklist

Run this only after G6 has removed the last flag and silenced success pings. It is
the actual answer to "what do I do once all goal epics are complete."

1. **Read HEAD, not the research.** Confirm event vocabulary, verbs, gate kind name,
   and tab order against the code. Memory follows the shipped contract.
2. **Confirm the new files exist and match the table in §0.**
   `sase_goals.md` (generated), `glossary/goal.md`, `/sase_goal`, both decision
   records.
3. **Grep memory and skill sources for rollout tense:** `goals flag`, `G1`–`G6`,
   `until cutover`, `alongside success pings`, `beta`, `under the flag`. Delete or
   rewrite those lines.
4. **Confirm generated artifacts relation rows** include `pursues`, `defines`,
   `evidences`, `follows` after `sase memory init` — no hand list.
5. **Confirm `@goal` appears** in `glossary/artifact-reference.md` and that
   `sase artifact read goal:<id>` is the documented read path.
6. **Confirm `sase.md` Final Declaration** mentions the goal action and still does
   not duplicate the intake block.
7. **Confirm beads vs goals** is one paragraph in `sase_beads.md` plus decision B,
   not a third essay.
8. **Deploy skills from the landed canonical tree** (`generated_skills.md` commit-
   then-deploy rule).
9. **Do not add anything** from §6.

If the incremental landings were disciplined, this sweep is an afternoon, not an
epic.

---

## 10. Recommended set (copyable)

**Write before any Goals epic is planned**

- [ ] `sase/memory/decisions/host-binds-agents-claim-users-settle.md`

**Must exist in the tree after G6 (add during the owning epic, sweep after G6)**

Additions:

- [ ] `src/sase/main/init_memory/templates/memory-sase-goals.template.md` → generated
      `sase/memory/sase_goals.md` on every SASE-managed project
- [ ] `sase/memory/glossary/goal.md`
- [ ] `src/sase/xprompts/skills/sase_goal.md`
- [ ] `sase/memory/decisions/goals-are-not-beads.md`

Patches:

- [ ] `memory-sase.template.md` (Final Declaration, one sentence)
- [ ] `memory-sase-artifacts.template.md` (Model paragraph)
- [ ] `memory-sase-beads.template.md` (intent vs scheduled work)
- [ ] `glossary/artifact.md`, `glossary/artifact-reference.md`
- [ ] `glossary/sase-gate.md`
- [ ] `glossary/nav-item.md`, `glossary/nav-section.md`
- [ ] `sase/memory/xprompts.md` (`%goal`)
- [ ] `src/sase/xprompts/skills/sase_final.md`
- [ ] `src/sase/xprompts/skills/sase_plan.md`
- [ ] `src/sase/xprompts/skills/sase_run.md`
- [ ] `src/sase/xprompts/skills/sase_notify.md`
- [ ] `src/sase/xprompts/skills/sase_new_task.md`
- [ ] `sase/memory/tui.md`, `sase/memory/tui_perf.md`
- [ ] `sase/memory/rust_core_backend_boundary.md`

Then: `sase memory init`, skill deploy from the landed tree, grep for leftover
rollout language.

**Do not**

- Core Goals essay, goals web, `task_type: goal`, storage-layout note, TUI keymap
  dump, CLI help dump, soak metrics, G1–G6 numbering, third copy of the intake
  block, in-place edit of `host-owned-completion`.

The feature changes what every agent owes the host at the end of a turn. Memory
should teach that obligation in the three places agents already look — the injected
line, `/sase_final`, and one on-demand domain note — and pin the two architectural
choices so the next program does not re-litigate them.
