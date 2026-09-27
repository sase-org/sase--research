# Memory after SASE Goals: what to record, where, and when

_Researcher cld · 2026-09-27 · project: sase · sase `24e80d42e`, research `0710ef1`_

**Question.** Once the six Goals epics (G1–G6 in the roadmap) are complete, which SASE
memory files should change, and which should be added?

**Inputs, all read through audited commands:**

- The roadmap: `research:202609/sase_goals_epic_roadmap/sase_goals_epic_roadmap.md`.
- The design: `research:202609/sase_goals_design/sase_goals_design.md`.
- Two companion notes: `sase_goals_why_not_beads.md` and `sase_goals_persistence.md`.
- The prior memory audit: `research:202609/memory_bead_backlog_audit/memory_bead_backlog_audit.md`.
- Every reference note, decision record, and glossary strand that Goals touches, read
  with `sase memory read`.

**Checked in the tree:**

- The `sase memory init` templates in `src/sase/main/init_memory/templates/`.
- The `bd/land_epic` prompt.
- The `/sase_plan` skill source.
- The git history of `sase/memory/` since 2026-09-01.
- The open `memory` task beads.

---

## 0. Bottom line

1. **The real decision isn't what to change after the epics. It's making sure each
   change lands inside the epic that makes it true.** This project's own rules stop a
   phase agent from editing memory unless an approved plan names the change. So any
   memory step left out of a G-plan turns into a `memory` task bead after that epic
   lands. It happened again today: `sase-1b1` shipped deck views with no glossary term,
   and its land agent filed `sase-1bg` (§2.2). The fix is cheap and has to happen
   *before* planning: put a memory list in every G-plan prompt (§7).
2. **Goals will make some existing memory wrong, not just incomplete.** Eight places in
   memory list a closed set that Goals extends: artifact kinds, prompt-ref kinds,
   directives, typed gate kinds, TUI tabs, and required finalizers. Agents would read
   those as complete. They must be fixed in the epic that ships the change (§3).
3. **Keep the new memory small. Most of what agents need about Goals already reaches
   them another way:**
   - the host injects a goal line on every turn;
   - `/sase_final` carries the claim-or-keep-open rules;
   - `/sase_goal` carries naming and adoption;
   - `docs/goals.md` carries the contract.

   Memory should add only four things: the *why* (decision records), the *words*
   (glossary terms, because Goals reuses four words SASE already uses for other
   things), a short *maintainer tripwire* (a `goals.md` reference note), and *fixes* to
   the lists that would go wrong.
4. **Recommended end state:**
   - 4 decision records, plus 1 more only if the program goes well;
   - 2 new glossary terms;
   - 1 new reference note, about 40 lines;
   - about 11 edits to existing notes, strands, and generated templates;
   - **zero core-memory changes**.

   Always-loaded cost: about **+300 tokens per turn** (~7% of today's generated
   `AGENTS.md`). That is several times the ~40-token goal line Goals itself adds to each
   bound turn, so keep roster lines short (§9).
5. **After G6 lands, run one consolidation pass (§8):**
   - audit every memory item Goals touched;
   - record any decisions no one has written down yet;
   - apply supersession marks where the program changed course;
   - remove wording that only made sense mid-rollout.

   Only one item truly belongs *after* the program: a process decision on how to split
   epics. Record it only if G1–G6 validate it.

---

## 1. What memory is for once Goals exists

Goals delivers most agent-facing guidance through channels that are more precise, and
cheaper, than memory. Memory should fill only the gaps between them.

| Channel | Reaches | Cost | Carries |
| --- | --- | --- | --- |
| Host-injected `SASE GOAL ⌖id — …` line (G2) or intake block (G4) | Every bound or draft LLM turn, in every project | ~40 / ~80 tokens, only on turns where it applies | Which goal you're on; name or adopt your draft |
| `/sase_final` paragraph (G3) | Every turn that declares | Skill-load cost | When to claim vs. keep open; evidence, check-it steps, gaps |
| `/sase_goal` skill (G3/G4) | Agents that need to list, show, name, or adopt | On demand | Command usage, naming guidance |
| CLI help, `docs/goals.md` | Humans and agents on demand | 0 always-loaded | Full contract |
| **Decision records** | Every turn (roster line); body on demand | ~60 tokens per record | *Why* the invariants hold, and what would reopen them |
| **Glossary** | Every turn (term name); body on demand | ~6 tokens per term | Words that collide with existing SASE vocabulary |
| **Reference note** | Every turn (description); body on demand | ~45 tokens | Invariants for agents changing launch, finalizer, notification, or ledger code |
| Core memory | Every turn, every project | Full body | Nothing Goals needs (§6) |

The gap memory fills: an agent **changing a launch path, a finalizer, or notification
routing** gets no goal line telling it that its change can break the "every turn has
exactly one goal" invariant. And an agent **reading the words** "claim", "draft", "goal",
or "done" gets no signal that they now mean two different things.

---

## 2. How memory has tracked past programs here

### 2.1 The closest precedent: the `sase tool` program

`git log -- sase/memory` since 2026-09-01 has 60+ commits. The `sase tool` program (E1–E4
plus triage) shows the pattern Goals will follow:

| Date | Commit | Memory change | Relation to the epics |
| --- | --- | --- | --- |
| 09-17 | `85d6fc74b` | `decisions/record-before-admit` | **Before** E1 landed. The program's governing decision. |
| 09-20 | `9cfb06a54` | glossary `tool-catalog`, `tool-run`; `lint_and_test.md` | Inside E1's landing commit |
| 09-22 | `7fad3394c` | `decisions/guarded-recipes`; **partial supersede** of `record-before-admit` | Inside E3's commit |
| 09-24 | `c91690efc` | glossary `tool-run`; `lint_and_test.md` | Inside E2's flag-removal commit |
| 09-25 | `49c32e19e` | decision `triage-annotates…`; glossary `failure-signature`, `triage-verdict` | Inside the triage commit |
| 09-26 | `306511750` | decision `receipts-prove…`; glossary `receipt` | Inside E4's flag-removal commit |
| 09-26 | `7eceb61ad` | decisions `explicit-handoff-fails-closed`, `machine-link-writes-off-primary`; **second partial supersede** of `record-before-admit` | **Decision debt**: recorded 2 days after E2 landed. E2's plan had left it as "a follow-up." |

Three lessons:

- **Memory landed with the code that made it true.** It wasn't batched at the end.
- **The governing decision was recorded up front.** It was then partly superseded
  **twice within 9 days**, because it bundled mechanism clauses (bypass measured; fail-open
  recording) in with the core claim. So an up-front Goals decision should state only
  the invariants and leave each mechanism to its own record (§5.1).
- **Decision debt still happened.** An end-of-program sweep is worth doing.

The `%tab` directive, which G2 generalizes, followed the same pattern two days ago:
`372ecc97c` updated `xprompts.md`, and `aff4fc082` (sase-1bc.5) added the "`%tab`
travels with the prompt" bullet to `dispatch.md`.

### 2.2 What happens when a plan doesn't name the memory change

- **The 2026-09-26 memory audit** found 15 open `memory` beads. Nine were valid backlog
  from shipped work. Three of their stored proposals would have written *new* errors into
  memory if applied word for word, because the code had moved on in the meantime.
- **`sase-1bg`, created today (2026-09-27 14:47).** "Deck views (sase-1b1) shipped with
  docs but no glossary term; sase-1b1.7 proposed the strand…" The phase agent couldn't
  write it, so it left a `PROPOSED FOLLOW-UP`, and the land agent turned that into a
  ready memory task. It is now the only open memory bead.

### 2.3 Why the deferral is structural, not carelessness

- **Authorization.** The `sase_memory_write` skill allows a memory write only when:
  - the user's prompt asks for it,
  - an **approved plan names the change in its steps**, or
  - an assigned bead describes it.

  A planner that adds memory steps on its own must first confirm with `/sase_questions`.
  So unless the G-plan prompts ask for memory changes, the plans won't contain them, and
  the phase agents *can't* make them.
- **The pipeline has no memory step:**
  - `bd/land_epic` (`src/sase/default_config.yml:1954`) has no memory check.
  - `/sase_plan` (`src/sase/xprompts/skills/sase_plan.md`) never mentions memory, apart
    from reading `sase_sizes.md`.
  - The roadmap's 11 cross-epic rules (§5) don't mention memory either.
- **Generated notes change for every project at once.** `sase_artifacts.md`,
  `sase_beads.md`, `sase_sizes.md`, the `task_types` descriptor, and the core `sase.md`
  are rendered from `src/sase/main/init_memory/templates/`. A template edit reaches every
  SASE project on its next `sase memory init`. It should ship with the code it
  describes, not weeks later.

---

## 3. What Goals will make wrong in today's memory

Each row below states a closed list, or a rule, that a specific epic invalidates. I read
every quoted line through `sase memory read` at `24e80d42e`.

| # | Memory item | Text today | Wrong after | Fix |
| --- | --- | --- | --- | --- |
| E1 | `glossary:artifact` | "…a plan or a research report, a bead, a completed agent, a Patch, a stitch, or an indexed file" | G1 (`goal:` kind) | Add "a goal" |
| E2 | `glossary:artifact-reference` | "Builtin kinds are `@stitch`, `@patch`, `@bead`, `@agent`, and the special `@file`" | G1 | Add `@goal`, and say it **cites** a goal (expands its card) and never binds one |
| E3 | `sase_artifacts.md` (**generated**; template `memory-sase-artifacts.template.md`) | Model: "sidecar documents, beads, agents, Patches, stitches, and indexed files all count" | G1 | Edit the template sentence. The relation list is rendered from the registry (`{{ artifact_relation_rows }}` ← `assembled_artifact_relations`), so `pursues`, `defines`, `evidences`, and `follows` appear on their own. Just check that `sase memory init` ran after G2, G3, and G4. |
| E4 | `xprompts.md` › Directives table | No `%goal` row. The `%tab` row sits next to where it would go. | G2 | Add a `%goal:<id>` / `%goal:new` row. Add one sentence: agent-initiated launches inherit the goal the way `%tab` does, `%goal:new` opts out, and `@goal:` only cites. |
| E5 | `xprompts.md` › `%final` paragraph | "Required instances cannot be removed by `none` or `!name`" (true, but no instance is required today: `required: []`, `default_config.yml:1784`) | G3 | Add a clause saying `goal` is required and runs after `commit` |
| E6 | `dispatch.md` › Launch selector | "`%tab` travels with the prompt: … agent-initiated launches stamp `%tab:<name>`…" | G2 | **Rewrite** the bullet so it covers `%tab` and `%goal` together (don't add a second, near-identical bullet). Also state the remote-binding rule for goals the target hasn't fetched yet (§10, Q4). |
| E7 | `sase_beads.md` (**generated**; template `memory-sase-beads.template.md`) | Epic launch and closing rules; no goal | G2/G3 | One sentence: an epic's plan `goal_id` binds every phase and land agent; phase workers keep the goal open and only the land agent claims; **closing a bead never settles a goal**. |
| E8 | `glossary:sase-gate` | "Typed kinds (plan, epic plan, question, launch, task triage) have their own front doors" | G3 | Add goal verification (`GoalVerify`), whose front door is `sase goal verify\|reject\|drop` |
| E9 | `glossary:nav-item`, `glossary:nav-section` | "On the Agents tab …; on the Services tab …; on the Artifacts tab …" | G5 (Goals tab) | Add the Goals tab's lanes and rows |
| E10 | `glossary:agent-relation-jump-target` | Lists which numbered things are *not* agent relation jump targets (Artifacts tab `<`/`>`, `,j`/`,J` unread jumps, …) | G5, then G6 | G5: classify the Goals tab's numbered agent chips. G6: recheck the `,j`/`,J` "unread" wording once ✅ success unread is retired. |
| E11 | `decisions/host-owned-completion` | "refusal requires a reason and normally fails the run" | G3 | **No edit.** A fail-open `builtin@goal` is covered by that "normally". Record the exception as a new record that links back (D2). Don't supersede. |

**Unaffected (I checked each):**

- **Core notes.**
  - `sase.md`: its final-declaration paragraph stays accurate. Handoffs make no goal
    decision, and "an unfinished turn still declares" maps to `keep_open`.
  - `gotchas.md`: the keymap rule already covers G5's keys.
  - `rust_core_backend_boundary.md`: Goals follows it.
- **Reference notes.**
  - `cli_rules.md`: the design's CLI already follows it.
  - `sase_flags.md`: the roadmap's per-epic scaffolding flags *are* its rule.
  - `sase_sizes.md`, unless D5 is adopted (§5.1).
  - `lint_and_test.md`, `symvision.md`, `generated_skills.md`: no change.
  - `tui_perf.md`, `tui_screenshot.md`: G5 follows the existing rules. Edit only if G5
    finds a new trap.
- **Webs.** The `task_types` web needs nothing.

---

## 4. The vocabulary problem

Goals mostly reuses words that already have a SASE meaning. That is exactly the kind of
confusion the glossary exists to prevent.

| Word | Existing SASE meaning(s) | Goals meaning |
| --- | --- | --- |
| **claim / claimed** | Bead status `claimed` ("runtime reserved", `sase_beads.md`); "holds a workspace claim" (`glossary:agent-turn`, `sase-workspace`); every decision record's opening **Claim.**; a lander's `%q(w=2.0)` "resource claim" (`check-full-is-explicit`) | An agent asserts the outcome is true now. The goal event is literally named `claimed`. `why_not_beads` calls this "same word, opposite end of the lifecycle." |
| **goal** | A plan's **required** `goal:` frontmatter field (`docs/sdd.md:462`, `plan_properties.py`). Land agents already write "GOAL NOT MET: the plan goal is…" in bead notes (`sase-1aq.10.7`, `sase-17d.10.1`). | The durable `goal:<id>` artifact. The plan's `goal:` text only *seeds* its outcome. |
| **draft** | Bead `open` "(draft)"; Patch status `Draft`; prompt-stash "drafts" | A machine-local, unnamed goal |
| **done** | Bead resolution `done`; the `JumpToAgent` notification tag `done` | A settled goal: `done · verified` or `done · acknowledged` |
| **card** | `glossary:agent-data-card`: "one titled unit of detail inside an agent data deck" | (a) a real Goal card in the FINAL deck; (b) the Goals tab's review "card", which is *not* inside a deck |
| **review / verify** | `bd/review/*` plan-review prompts; `just check` "verification", receipt verdicts | The Review lane; the `GoalVerify` gate; the `verified` settlement |

Two strands, **Goal** and **Goal Claim**, each with an explicit "not to be confused
with" clause, cover the first four rows. The **card** collision is a naming decision G5
should make on purpose (§10, Q5).

---

## 5. Recommended additions

Draft bodies follow the conventions of each web: decision strands use Claim / Why / Cost /
Reopens when, and glossary strands are one short paragraph. The implementing agent
should author them through `/sase_memory_write`, which covers frontmatter, links, and
republishing.

### 5.1 Decision records

**D1: `goals-host-binds`, "The Host Binds Goals, Agents Claim, You Settle."**
Write it **before G1**, as the roadmap's first move, so six plans cite it instead of
re-arguing it.

- **Roster phrase:** *Every LLM turn is host-bound to one goal before spawn; agents only
  name or adopt their draft and claim or keep open; only a human settles.*
- **Claim:** every LLM agent turn is bound to exactly one goal before its provider
  starts.
  - A pure host resolver picks the goal from launch facts: explicit `%goal`, session,
    plan `goal_id`, clan, parent, bead, or routine.
  - If none applies, it creates a machine-local draft, and the agent names or adopts it
    as its first act.
  - The agent's goal authority stops there, plus the required `builtin@goal` decision:
    `keep_open` or `claim`.
  - A claim moves the goal to review. It never settles it.
  - `verify`, `reject`, `drop`, `reopen`, and `merge` are human verbs, refused inside
    agent runs.
- **Why:**
  - `SASE_PLAN` is commit plumbing: it is popped on every spawn, and epic phase and land
    agents avoid it. A "check `SASE_PLAN`, else run `/sase_new_goal`" rule would misfile
    ~840 epic turns a week, create duplicate goals across parallel swarms, and rest an
    invariant on a skill the model can skip.
  - Agents over-claim, so a claim is evidence for a human decision, not the decision
    itself.
  - **Rejected alternatives:**
    - agent-created goals through a mandatory skill;
    - agents closing their own goals;
    - claims without a Goal object (about ⅕ the cost, but a phase worker can't know its
      epic is done, and you get no inventory);
    - silent fuzzy joins;
    - an LLM verifier pass before you're notified.
  - **Links:**
    - It extends [[decisions/host-owned-completion]] from turns to outcomes.
    - GoalVerify gates are host-created after the turn, so [[decisions/gates-never-block]]
      holds.
    - Test evidence comes only from receipts ([[decisions/receipts-prove-before-they-skip]]).
- **Cost:**
  - ~40 tokens per bound turn;
  - ~80 tokens plus one CLI call per draft turn;
  - a required finalizer on every normal turn;
  - ~30 human verifications a day, eased by answer acknowledgement.
- **Reopens when:** `sase goal stats` shows a model's claim precision below the G6 floor
  (80%) for a sustained period, or time-to-verify and lapse rates show that humans aren't
  working the settle loop.
- **Scope discipline:** keep ledger layout, fail-open, and the attention cutover **out**
  of D1. Those were the kinds of mechanism clauses that got `record-before-admit`
  partly superseded twice in 9 days (§2.1).

**D2: `goal-fails-open`, "A Goal Problem Never Fails An Agent Turn."** Write it in
**G3**.

- **Claim:**
  - `builtin@goal` is required *and* fail-open. A refusal, an error, or an ineligible
    claim records `keep_open` plus a diagnostic that `sase goal audit` reports.
  - A binding failure launches the turn unbound.
  - No goal defect fails a turn or blocks its commit.
  - This narrows [[decisions/host-owned-completion]]'s "normally fails the run" for this
    one finalizer.
- **Why:** a required finalizer runs on every normal turn in every project, so a
  fail-closed bug would fail every agent. **Rejected:** fail-closed; an optional
  finalizer (the every-turn invariant would silently disappear).
- **Cost:** failures are quiet. After G6, a suppressed claim means *no* loud signal; the
  quiet Idle notice becomes the only backstop. I haven't seen this point in the roadmap
  or the design, and it belongs in the record.
- **Reopens when:** audit shows fail-open diagnostics hiding claims you needed, or the
  Idle backstop misses finished work.
- **If you want fewer records:** fold D2 into D1 as one paragraph. It saves ~60 tokens
  per turn, but the fail-open rule loses its own reopen condition.

**D3: `goal-ledger`, "Goals Reuse The Beads Repo, Not The Beads Model."** Write it in
**G1**, citing G1's measured list latency and push-retry numbers.

- **Claim:**
  - A goal is a Rust-owned `goal:` artifact, **not a bead type**.
  - Canonical state is immutable event files plus one empty `live/<id>` marker per
    unsettled goal.
  - It lives under a `goals` sidecar role, co-hosted in the beads repo, and is written
    only through the hidden host clone.
  - Reads cost O(unsettled goals) through a machine-local projection. Settled goals are
    never opened on the hot path.
  - Freshness is shown ("synced 12s ago"), never promised.
  - Drafts stay local until they are named.
- **Why:** beads are the wrong fit.
  - They have no review state.
  - Their authority is inverted: agents close beads, but humans settle goals.
  - Their read path is O(history): 6,479 beads, 93% closed, and a year of goals would be
    about 16k records.
  - Their triage rituals would bury ready tasks.

  The storage format is chosen for conflict-freedom: unique event files and marker
  add/delete can't conflict on rebase, while mutable snapshots can. **Rejected:**
  - `task_type: goal`;
  - the agents sidecar (a publication store that rebuilds pages on every pull);
  - a mutable `live/<id>.json`;
  - `active/` → `settled/` moves;
  - a dedicated repo before contention is measured
    ([[decisions/corpus-before-mechanism]]).

  Hidden-clone writes follow [[decisions/machine-link-writes-off-primary]].
- **Cost:**
  - a second writer in the beads repo;
  - eventual cross-machine visibility;
  - named goal text is as public as bead titles (unless `local` visibility is set);
  - a doctor repair path.
- **Reopens when:** the push-retry counter or outbox depth shows contention (split the
  role, which is a config change), or hot-list p95 grows with settled history.

**D4: `claims-replace-success-pings`, "Claims, Not Completions, Earn Attention."**
Write it in **G6**, with G6's before/after notification-volume numbers.

- **Claim:**
  - A successful agent completion is silent.
  - A goal claim, carried by one GoalVerify gate, is the loud signal.
  - Errors, questions, approvals, and sudo keep their existing routes.
  - A goal going Idle notifies quietly.
  - Loud success pings survive only as a user config field.
- **Why:**
  - There are ~6.6 turns per outcome.
  - The shadow-coverage and precision gates passed on real traffic (cite the measured
    values).
  - **Rejected:** keeping both (double noise); silencing before claims were proven;
    per-agent "needs attention" flags.
- **Cost:** you lose per-agent completion awareness. The Idle notice is the backstop for
  [[decisions/goal-fails-open]].
- **Reopens when:** shadow coverage drops back below the G6 threshold, or finished work
  keeps being discovered late.

**D5 (conditional, post-program): `epic-per-verification-world`, "One Epic, One
Released Contract, One Verification World."**

- **Claim:** a feature that crosses several contracts ships as sibling epics linked by
  `sase bead dep`, with no umbrella parent. Each epic has:
  - at most 7 mostly-medium phases;
  - one released contract and one verification world;
  - a frozen, numbered definition of done with no calendar waits;
  - its successors named as out of scope in its land section.
- **Why:**
  - Across 335 root epics, the child-epic rate rises from 16% to 58%, and median time to
    close from 3.9 h to 48 h, as phase count grows.
  - The `%auto` land agent turns leftovers into child epics.
  - `sase tool`'s siblings of 7 phases or fewer closed in 7–38 h. The one 9-phase epic
    spawned a child.
  - Add the Goals program's own numbers.
- **Write it only if** G1–G6 finish with at most one remediation child epic in total, and
  each epic closes within about 2× the median for its phase count. If the program fails
  that test, record what actually happened instead, or record nothing.
- **Why this one waits:** it is the only item whose evidence exists only after the
  program.
- **A roster line alone is a weak lever.** Pair it with one sentence in the `/sase_plan`
  skill source, where epic plans are actually written. That is a generated-skill change
  (`generated_skills.md` workflow), not a memory change. Today nothing in `/sase_plan`,
  `sase_sizes.md`, or `default_config.yml` caps phase count; gem's "≤5 per
  `sase_sizes.md`" claim had no source, as the roadmap noted.

### 5.2 Glossary strands

**`glossary:goal`** (aliases `goals`, `⌖`). Build it up across epics so it is true on
master at every point: identity and statuses in G1, binding in G2, drafts and every-turn
coverage in G4. Final form:

> A goal is the durable outcome behind one or more sase turns, addressed as `goal:<id>`
> (five Crockford base32 characters) and shown with `⌖`. Its status is `draft`
> (machine-local, not yet named), `active` (shown as Running or Idle, derived from
> contributor liveness rather than stored), `review` (claimed, awaiting you), `done`
> (verified or acknowledged), or `dropped` (canceled, merged, or superseded). The host
> binds every LLM agent turn to exactly one goal before spawn; monitor, gate, and proc
> turns inherit it. A plan's `goal:` frontmatter is text that seeds its goal's outcome,
> not the goal; a task bead is scheduled work, not intent; and agent status is not goal
> status — a failed agent leaves its goal active. `%goal:<id>` binds a launch;
> `@goal:<id>` only cites one.

**`glossary:goal-claim`** (aliases `claim`, `claims`). Written in G3:

> A goal claim is an agent's `builtin@goal` assertion that its goal's outcome is true
> now: a claim sentence, resolvable evidence refs the host mostly gathers (`@commit`,
> created files, the plan, an embedded receipt snapshot, `@reply`), one to three
> check-it steps, and any gaps. It moves the goal to `review` and opens one GoalVerify
> [[glossary:sase-gate]]; it is never a settlement — only you verify, reject, or drop.
> Only an owner with no live contributor may claim, so epic phase workers and swarm
> researchers keep the goal open. Not a bead's `claimed` status (the runner reserved
> it), a workspace claim, or a decision record's **Claim.**

**No other new terms.**

- *Draft goal*, *standing goal*, *goal binding*, and *GoalVerify* fit as clauses in the
  strands above or in E8.
- Each new term costs ~6 tokens every turn and adds one more thing to keep in step.
- *Standing goal* gets one clause in `glossary:routine` only if G4 ships standing goals
  (§10, Q3).

### 5.3 A short `goals.md` reference note (create in G2; grow it through G6)

**Description** (the part that is always loaded): *Read before changing agent launch
paths or inherited launch metadata, finalizers, notification routing, or the goal
ledger, CLI, or Goals tab.*

That trigger is the note's real value. Goals is cross-cutting, and agents working on
`sase-1bc`-style launch seams, finalizers, or notifications won't know they're touching
it. Keep the body to about 40 lines of tripwires plus pointers:

- **Contract and rationale.** `docs/goals.md`; [[decisions/goals-host-binds]],
  [[decisions/goal-ledger]], [[decisions/goal-fails-open]].
- **Launch paths (G2).** Binding is resolved in the runner (`build_agent_meta`) through
  the core resolver. A new launch path or successor kind must carry `goal_id` in the
  preserved and inherited metadata, and must be added to the launch-path matrix test.
  `sase goal audit` must stay at 0 unbound turns. *Better still:* make the matrix test
  fail on any launch path it hasn't registered, so the code enforces this rule even
  when nobody has read the memory note.
- **Finalizer (G3).** `builtin@goal` runs after `commit` and fails open. Never make a
  goal error fail a turn.
- **Authority (G3).** Agents may `list`/`show`, and may `name`/`adopt` only their own
  draft. Every status verb is human-only.
- **Ledger (G1).**
  - Never edit or delete an event file; only add or remove markers.
  - Write only through the hidden clone.
  - Never open settled goals on a hot path.
- **Relations.** `pursues`, `defines`, `evidences`, and `follows` are *projections*. Never
  write link events per agent.
- **Privacy (G4).** A named goal's title, outcome, claim, check-it steps, and gaps publish
  to the beads repo, which is public today. So does the creator's prompt, which naming
  publishes to the agents sidecar.
- **Attention (G6).** Successes are silent, claims are loud, and the Idle notice is the
  backstop.

The agent-facing half of the privacy rule ("never put secrets or personal data in a goal
title or claim") belongs in the intake block and `/sase_goal`, which every naming agent
sees. It doesn't belong in memory.

---

## 6. What should *not* go into memory

| Candidate | Verdict | Why |
| --- | --- | --- |
| A core note, or a Goals paragraph in the generated `sase.md` | **No** | It would repeat what the host injects on every bound turn, and it would cost every turn in *every* SASE project. Add one only if `sase goal audit`/`stats` show a behavior gap that the injection text and `/sase_final` can't fix, and fix those two first. |
| Copying the design or the roadmap into a reference note | **No** | Design goes stale as code changes; that is the decisions web's own warning. Point to `docs/goals.md` and the research refs. |
| One memory note per epic | **No** | Epics are delivery units; memory describes the finished system. |
| The program's own scaffolding rules (≤7 phases *within Goals*, zero golden churn outside G5, one flag per epic, "plan one epic at a time") | **No** | These are plan-prompt rules for this program. The durable lesson is D5, and it's conditional. |
| A notifications memory note for the G6 cutover | **No** | `docs/notifications.md` owns the truth table. D4 records the why. |
| Standing-goal, draft-goal, or GoalVerify glossary terms | **No** | They fit as clauses (§5.2). |
| A "don't create goals for follow-up work" rule | **No** | The CLI refuses it. Follow-up work stays in task beads, which `sase_beads.md` and `/sase_new_task` already cover. Whether a claim's `gaps` should also become task beads is a G3 design choice, and belongs in `/sase_final`. |
| A mechanism that mines rejected claims to write memory | **Not now** | [[decisions/corpus-before-mechanism]]. See §8, item 9. |

---

## 7. The per-epic memory list (put it in each plan prompt)

Because of the authorization rule (§2.3), the easiest way to get these changes made is
to paste the relevant row into the prompt that asks for each G-plan. For example: *"This
plan is authorized to make these memory changes, in the phase that makes each one true:
…"*. The planner then won't need to stop and ask, and phase agents can land memory with
their code. Add one line to each plan's definition of done: *"`sase memory init --check`
is clean, and the listed memory items match the landed behavior."*

| When | Memory changes | Kind |
| --- | --- | --- |
| **Now, before G1 is planned** | D1 | New decision |
| **G1** | D3 (with G1's measured numbers). `glossary:goal`, stage 1: identity, statuses, not a bead, not the plan's `goal:` field. E1, E2, E3. | 1 decision, 1 new strand, 2 strand edits, 1 template edit |
| **G2** | E4 (`%goal` row), E6 (rewritten dispatch bullet), E7 (epic binding sentence). Create `goals.md` with the launch-path tripwire. `glossary:goal`, stage 2: host binding. | 2 note edits, 1 template edit, 1 new reference note, 1 strand edit |
| **G3** | D2. `glossary:goal-claim`. E5, E7 (closing sentence), E8. `goals.md` finalizer and authority sections. *Optional:* one clause in `glossary:receipt` saying a claim embeds a receipt snapshot, so other machines can render it. | 1 decision, 1 new strand, several edits |
| **G4** | `glossary:goal`, stage 3: drafts, every turn. `goals.md` privacy section. The E6 remote-draft rule, once decided. `glossary:routine` clause if standing goals ship. | Edits |
| **G5** | E9, E10 (Goals tab), and the card-naming decision. `tui_perf.md` only if G5 finds a new trap. | Strand edits |
| **G6** | D4 (with before/after numbers). E10 `,j` recheck. Remove any mid-rollout wording such as "until the cutover" or "behind `goals_*`". | 1 decision, cleanup |
| **After G6** | The consolidation pass (§8). D5, if it qualifies. | Audit, then 0–1 decision |

---

## 8. The consolidation pass after G6

Run it once, after G6 lands and its flag is gone. Scope it like the 2026-09-26 memory
audit: one small epic or tale, or a research round followed by one memory commit.

1. **Audit.** Run `sase memory read` on every item in §7 and grep the memory tree for
   `goal`. Check each against the landed code, not against plan text: the backlog audit
   found stored proposals that had gone stale in days.
2. **Memory beads.** List the `memory` task beads filed during the program. Apply them,
   merge them into the audit commit, or close them with a reason.
3. **Decision debt.** For each G-plan, list every decision that has a rejected
   alternative and a reopen condition. Record it as a strand, or explicitly decline to.
   This is the `explicit-handoff-fails-closed` lesson.
4. **Supersession, not edits.** If the program changed a D1 clause, write a new record
   and add a `superseded-in-part` mark to D1. Don't edit D1's accepted body. Likely
   triggers: routines exempted instead of getting standing goals; `ack` no longer the
   answer default; an umbrella flag.
5. **Remove mid-rollout wording.** No memory should still describe two-state behavior
   once the flags are removed.
6. **D5.** Apply the qualifying test from §5.1, then write the record and the
   `/sase_plan` sentence, or skip both.
7. **Token check.** Compare the size of `AGENTS.md` before G1 and after G6. If the
   program added more than ~350 tokens, shorten roster phrases before adding anything
   else.
8. **Revisit `host-owned-completion`.** Its reopen condition is "after operational soak
   across enough real runs". A required finalizer on every turn, soaked through G3–G6,
   is exactly that soak. If the protocol held up, that is evidence for keeping it, and
   no edit is needed. If it didn't, that is a new record.
9. **Watch item, not a change.** GoalVerify rejections with written feedback are the
   first structured corpus of human verdicts on agent claims. Per
   [[decisions/corpus-before-mechanism]], build nothing now. Once a few hundred
   rejections exist, a manual review of recurring reasons is the evidence-based way to
   find which memory is missing.

---

## 9. Cost

Measured on today's generated `AGENTS.md`: 16,773 bytes, about 4,200 tokens.

| Always-loaded section | Today | Marginal cost per item |
| --- | --- | --- |
| Decisions roster (22 records) | 5,851 B ≈ 1,460 tokens (35% of the file) | ~60 tokens per record |
| Glossary term list (~62 terms) | 1,845 B ≈ 460 tokens | ~6 tokens per term |
| Reference-note list (10 notes) | 2,072 B ≈ 520 tokens | ~45 tokens per note |

The recommended set adds:

| Item | Tokens |
| --- | --- |
| D1–D4 | ~240 |
| 2 glossary terms | ~12 |
| `goals.md` description | ~45 |
| **Total** | **~300 per turn (+7%)** |
| D5, if written | +60 |
| Folding D2 into D1 | −60 |

At ~2,048 turns a week (the design's athena count), 300 tokens is about 0.6 M input
tokens a week, most of it prompt-cached. That's affordable, but it is **about 7× the
~40-token goal line** Goals adds to each bound turn. So the discipline matters: short
roster phrases, and no memory that repeats the injection.

---

## 10. Your decisions that change this set

| # | Question | Affects | My recommendation |
| --- | --- | --- | --- |
| Q1 | Record D1 now, before planning G1? | Every G-plan cites it | **Yes.** `sase tool` did the same, and it worked. Keep it to the invariants only. |
| Q2 | Keep D2 as its own record, or fold it into D1? | ~60 tokens per turn | **Keep it separate.** It narrows another record and needs its own reopen condition. |
| Q3 | Routines: standing goals, or an exemption? (a roadmap §7 decision) | `glossary:routine`, `glossary:goal`, a D1 clause | Whichever you pick, state it in D1 when D1 is written, so it never needs superseding. |
| Q4 | A remote `%dispatch` child of a goal-bound parent, when the target hasn't fetched the goal yet, or the goal is still a local draft | The E6 `dispatch.md` rule | Decide in G2 or G4. Neither research doc settles it: drafts are machine-local, and naming and progress pushes are batched. |
| Q5 | Is the Goals tab's detail view a "card"? | `glossary:agent-data-card` vs. `glossary:goal` | Either make it a real deck with cards, or give it a non-"card" name (e.g. *goal review panel*). Record the choice in G5. |
| Q6 | Write D5 even if the program doesn't meet its test? | 0–1 decision | Only if it passes. Otherwise record what actually happened, or nothing. |

---

## 11. Recommended memory updates

**A. Before planning G1 (now).**

1. **New decision `decisions/goals-host-binds`** (D1): the host binds every LLM turn to
   one goal; agents only name, adopt, claim, or keep open; only humans settle. It holds
   invariants only, with no mechanism clauses.
2. **Process change, not a memory file:** paste the §7 memory row into every G-plan
   prompt, and add "`sase memory init --check` is clean and the listed memory items
   match landed behavior" to each definition of done. Without this, items 3–13 will
   become follow-up memory beads, as `sase-1bg` did today.

**B. Inside the epics.** Each item lands with the code that makes it true.

3. **G1: new decision `decisions/goal-ledger`** (D3): reuse the beads *repo*, not the
   beads *model*; append-only events plus `live/` markers; O(unsettled) reads; freshness
   shown, not promised.
4. **G1→G4: new glossary strand `glossary:goal`,** built up in stages. It separates a
   goal from a plan's `goal:` field, from task beads, and from agent status, and
   separates `%goal` (binds) from `@goal` (cites).
5. **G3: new decision `decisions/goal-fails-open`** (D2). A goal problem never fails a
   turn. It extends `host-owned-completion` without superseding it, and names the Idle
   notice as the post-G6 backstop.
6. **G3: new glossary strand `glossary:goal-claim`,** separating it from bead `claimed`,
   workspace claims, and a decision record's "Claim."
7. **G2→G6: new reference note `goals.md`** (~40 lines): tripwires for launch paths,
   finalizers, notifications, and the ledger, plus pointers to `docs/goals.md` and the
   decisions.
8. **G6: new decision `decisions/claims-replace-success-pings`** (D4), with the measured
   before/after notification volume.
9. **Edits to lists that would otherwise be wrong:**
   - `glossary:artifact` (G1)
   - `glossary:artifact-reference` (G1)
   - the `sase_artifacts.md` template's Model sentence (G1)
10. **`xprompts.md`:** the `%goal` directive row and inheritance sentence (G2); the
    `%final` clause saying `goal` is required (G3).
11. **`dispatch.md`:** rewrite the "`%tab` travels" bullet to cover `%goal` too, plus the
    remote-binding rule (G2/G4).
12. **`sase_beads.md` template:** epic `goal_id` binding, phase workers keep open, only
    the land agent claims, and closing a bead never settles a goal (G2/G3).
13. **Glossary edits:**
    - `glossary:sase-gate`: add GoalVerify to the typed kinds (G3).
    - `glossary:nav-item` and `glossary:nav-section`: add the Goals tab (G5).
    - `glossary:agent-relation-jump-target`: classify Goals-tab chips (G5), recheck
      `,j` (G6).
    - *Optional:* `glossary:receipt` (claim snapshot, G3); `glossary:routine` (standing
      goal, G4, only if shipped).

**C. After G6: one consolidation pass (§8).**

14. Audit every item above against the landed code, and apply or close the memory beads
    filed during the program.
15. Clear decision debt from the six plans. Supersede, rather than edit, any D1 clause
    the program changed.
16. **Conditional new decision `decisions/epic-per-verification-world`** (D5), plus one
    sentence in the `/sase_plan` skill. Write it only if G1–G6 meet the §5.1 test.

**D. Leave unchanged:**

- **Core memory:** the `sase.md` template, `gotchas.md`, `rust_core_backend_boundary.md`.
- **Reference notes:** `cli_rules.md`, `sase_flags.md`, `sase_sizes.md` (unless D5),
  `lint_and_test.md`, `symvision.md`, `generated_skills.md`, `tui.md` / `tui_perf.md` /
  `tui_screenshot.md` (unless G5 finds a new trap).
- **Webs:** the `task_types` web.
- **Existing decisions:** `host-owned-completion` and every other existing decision
  record, extended by links rather than superseded.
