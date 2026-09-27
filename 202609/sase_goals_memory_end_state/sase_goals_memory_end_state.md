# Memory after SASE Goals: the end state, and how to get there without a backlog

_Lead synthesis · 2026-09-27 · project: sase · sase `24e80d42e`, research `ee2be10`_

**Question.** Once every SASE Goals epic (G1–G6 in the
[roadmap](../sase_goals_epic_roadmap/sase_goals_epic_roadmap.md)) is complete, which
memory files should change and which should be added? None of the epics has been
planned yet.

**Sources.** I read five independent reports through `sase artifact read`:
[cdx](sase_goals_memory_end_state__cdx.md), [cld](sase_goals_memory_end_state__cld.md),
[grk](sase_goals_memory_end_state__grk.md), [mus](sase_goals_memory_end_state__mus.md),
and [gem](sase_goals_memory_end_state__gem.md). I also read the roadmap and the
[design](../sase_goals_design/sase_goals_design.md) myself.

**Checked myself.** I checked the points where the reports disagreed against HEAD:

- the relevant glossary, decision, and reference-memory bodies, read with
  `sase memory read`;
- the `init_memory` templates and generator;
- the `/sase_memory_write` and `/sase_plan` skill sources;
- the `bd/land_epic` prompt;
- the `sase-1bg` bead;
- the size of the generated `AGENTS.md`, by section;
- the linked `sase-core` checkout.

§2 lists the results.

---

## 0. Bottom line

1. **Make the updates, but keep them small.** When the program is done, memory should
   hold four things:

   - the **why**: 4 decision records, plus 1 more only if the program earns it;
   - the **words**: 2 glossary strands;
   - one short **maintainer tripwire**: a reference note, `sase_goals.md`;
   - **fixes** to about 12 existing notes, strands, and templates whose closed lists
     Goals makes wrong.

   Make **no core-memory changes.** Agents learn the per-turn contract from the
   host-injected goal line, the `/sase_final` skill, and the `/sase_goal` skill. Memory
   would be a fourth copy, and one that every turn in every project pays for.

2. **Don't save the work for the end.** Goals doesn't just leave memory incomplete; it
   makes some of it *wrong*. Today, memory states closed sets that Goals extends:
   artifact kinds, ref kinds, directives, required finalizers, typed gate kinds, and
   TUI tabs. Agents working on G2–G6 would read those lists as complete.

   The authorization rule also means that a memory step a plan doesn't name can't be
   done by that epic's phase agents. It becomes a follow-up `memory` bead instead.
   That happened today: `sase-1b1` shipped deck views with no glossary term, and its
   land agent filed `sase-1bg`.

   So each change should land inside the epic that makes it true. The cheap way to
   make that happen is to paste each epic's memory list into its plan prompt (§4).

3. **Write one record now.** Record the "host binds, agents claim, users settle"
   decision before G1 is planned. The roadmap already lists this as its first move.

4. **Your actual "after completion" job is a single consolidation pass** (§5):

   - audit every item against landed code;
   - clear decision debt, using supersession rather than edits;
   - delete wording that only made sense mid-rollout;
   - decide whether a process record about epic sizing has earned its place.

5. **Cost.** The recommended set adds about **+320 always-loaded tokens (~7.6%)** to
   today's ~4,190-token `AGENTS.md`. Nearly all of that is decision-roster lines, so
   keep them short.

---

## 1. What memory is for once Goals exists

Goals reaches agents through channels that are more precise than memory and cheaper than
core memory. Memory only has to cover the gaps between them.

| Channel | Who it reaches | What it carries |
| --- | --- | --- |
| Bound line `SASE GOAL ⌖id — …` (~40 tokens, G2) and draft intake block (~80 tokens, G4) | Exactly the turns where they apply, in every project | Which goal you're on; name or adopt your draft |
| `/sase_final` goal paragraph (G3) | Every turn that declares | Whether to claim or keep open; evidence, check-it steps, and gaps |
| `/sase_goal` skill (G3/G4) | Agents on a draft, or agents that need `list`/`show` | `list` / `show` / `name` / `adopt` |
| CLI refusals | Every agent | `new`, `verify`, `reject`, `drop`, `reopen`, and `merge` are refused inside agent runs (design §4.11) |
| **Decision records** | Every turn gets the roster line; the body is read on demand | *Why* the invariants hold, and what would reopen them |
| **Glossary strands** | Every turn gets the term; the body is read on demand | Words that collide with existing SASE meanings |
| **A reference note** | Every turn gets the description; the body is read on demand | Tripwires for agents changing seams that Goals depends on |

The gap is the **maintainer** (cld, cdx). An agent editing a launch path, a finalizer,
notification routing, or ledger code gets no goal line warning that its change can break
the "every turn has exactly one goal" invariant. And an agent reading "claim", "goal",
"draft", or "done" gets no signal that each word now has two meanings.

---

## 2. What I verified, and how the disagreements resolve

### 2.1 Facts confirmed at HEAD

- **Closed lists that Goals invalidates (cld).** Each of these is exact text in memory
  today:
  - `glossary:artifact` lists "a plan or a research report, a bead, a completed agent, a
    Patch, a stitch, or an indexed file."
  - `glossary:artifact-reference` says "Builtin kinds are `@stitch`, `@patch`, `@bead`,
    `@agent`, and the special `@file`."
  - `glossary:sase-gate` says "Typed kinds (plan, epic plan, question, launch, task
    triage)."
  - `glossary:nav-item` and `glossary:nav-section` enumerate only the Agents, Services,
    and Artifacts tabs.
  - `xprompts.md` has no `%goal` row, and its "Rule" paragraph names only
    `builtin@commit`.
  - The `dispatch.md` "`%tab` travels with the prompt" bullet describes exactly the
    mechanism G2 generalizes for `%goal`.
- **Two of the notes are generated (grk, cld).**
  - `sase_artifacts.md` and `sase_beads.md` are rendered from
    `src/sase/main/init_memory/templates/` (`_GENERATED_PROJECT_LONG_MEMORY_SPECS`) into
    every SASE project, so their edits go to the templates.
  - The artifact relation rows come from `{{ artifact_relation_rows }}`, so `pursues`,
    `defines`, `evidences`, and `follows` appear on their own after `sase memory init`.
    Don't hand-maintain them.
- **The words collide (cld).**
  - A bead's status `claimed` means "runtime reserved."
  - `glossary:agent-turn` says a turn "holds a workspace claim."
  - Every decision record opens with **Claim.**
  - Plans already have a `goal:` frontmatter field (`src/sase/sdd/plan_properties.py`,
    `docs/sdd.md`).
  - So both "goal" and "claim" need disambiguation.
- **The authorization rule is binding (cld, mus).**
  - `/sase_memory_write` allows a write only when the user's prompt asks for it, when
    an approved plan names it, or when an assigned bead describes it. "Nothing else
    counts — not a design doc."
  - Neither `bd/land_epic` nor `/sase_plan` has a memory step. `/sase_plan` mentions
    memory only to read `sase_sizes.md`.
  - `sase-1bg` exists exactly as cld described. It is a `memory` task created by
    `sase-1b1.land` because deck views shipped with no glossary strand.
- **Bundling clauses into one decision gets it superseded (cld).**
  - `record-before-admit` was partly superseded **twice** within days. One of the
    retired clauses was its blanket *fail-open* clause.
  - The same risk applies to a Goals governing decision that bundles fail-open
    behavior.
- **Existing notes already cover some of it.**
  - `tui_perf.md` already requires off-thread refresh, stat-only change tokens, and
    "p95 < 16 ms on every tab."
  - `tui.md` is a two-link entry point, not a list of tabs.
  - `sase_flags.md` already says per-epic scaffolding flags are removed before landing,
    and that a permanent preference is a config field.
  - `generated_skills.md` covers generation and deploy mechanics; it is not a catalog
    of skills.
  - `cli_rules.md` holds generic CLI conventions only.
- **The token cost is measured, not guessed.**
  - `AGENTS.md` is 16,773 bytes (~4,190 tokens).
  - The decisions roster alone is ~1,460 tokens, or **~66 tokens per record**.
  - The glossary list costs ~6 tokens per term, and the reference-note list ~45 tokens
    per note.
- **The pattern since 2026-09-01 (cdx).** Memory gained 13 decision strands, 28
  glossary strands, and only 3 flat notes. This project records rationale as
  decisions and vocabulary as strands, and adds a flat note only for a real
  operational workflow.

### 2.2 Disagreements and rulings

| Question | Positions | Ruling | Why |
| --- | --- | --- | --- |
| **Wait until all epics finish?** | All five: no, stage the changes | **Stage them, then run one sweep after G6** | Closed lists go wrong mid-program, and unplanned memory steps turn into beads (§2.1). |
| **Core memory (`sase.md`)** | grk, gem: add one Final Declaration sentence. cdx, cld, mus: no change. | **No change** | The text stays accurate. Handoffs make no goal decision, which matches the existing exemption list. "An unfinished turn still declares" maps to `keep_open`. The template renders into every project, including the home root. Add a sentence only if `sase goal audit`/`stats` show turns skipping the goal decision *and* a `/sase_final` fix fails. |
| **How many decision records?** | mus 1, grk 2, cdx 3, gem 3, cld 4 + 1 | **4, plus 1 conditional** (§3.1) | Split fail-open out of D1: it narrows `host-owned-completion` and needs its own reopen condition, and `record-before-admit` shows bundled clauses get superseded. Merge grk's "goals are not beads" into the ledger record (cld's D3), since it's the same choice. |
| **How many glossary strands?** | grk, mus 1; cld 2; cdx 3; gem 8 | **2: `goal` and `goal-claim`** | Both words have verified collisions. Binding, draft, GoalVerify, standing goal, answer-ack, and idle fit as clauses in these strands. gem's eight add terms that don't collide with anything. |
| **Who is `sase_goals.md` for?** | grk: a generated note for every project, agent-facing. mus, gem: agent-facing, holding the full contract. cdx, cld: sase-only, for maintainers. | **sase-only, a maintainer tripwire, ≤ ~60 lines** | Agent-facing rules already reach every project through injection, skills, CLI refusals, and the edited *generated* beads and artifacts templates. A generated goals note would be a fourth copy. Promote it only if post-G4 audits show agents in other projects misusing goals. |
| **`tui.md` / `tui_perf.md`** | grk, gem: add the tab, keys, and budgets. mus: one link. cdx, cld: only if a new trap appears. | **No change unless G5 finds a new trap** | `tui_perf` already states the rules generically. Keys belong in `default_config.yml`, which the `gotchas` note already routes to. |
| **`cli_rules.md`** | gem: add a human-only-verb rule | **No** | It's a domain rule for one command group, so it belongs in `sase_goals.md`. |
| **`generated_skills.md`** | gem: list `/sase_goal` | **No catalog entry.** Optional widening only (§3.4). | The note describes mechanics, not skills. |
| **`rust_core_backend_boundary.md`** (core) | grk: one example sentence | **No** | It costs every turn, and the litmus test already routes the reducer, resolver, and `decide_goal_action`. |
| **`dispatch.md`** | Only cld | **Rewrite the `%tab` bullet to cover `%goal` as well** | Verified: G2 generalizes exactly this mechanism. |
| **When to write the attention record** | cdx, cld: after G6, with measured numbers. grk: never (just a config default). | **At G6, with the before/after volume** | A future notification cleanup could quietly restore per-turn pings. The *why* ("claims, not completions, earn attention") is not obvious from reading the code. |

### 2.3 Corrections to individual reports

- **gem**
  - Its always-loaded estimate (~80 tokens) is too low. Three decision roster lines
    alone cost ~200.
  - `gate-turn.md` is the wrong target for GoalVerify. The typed-kind list lives in
    `glossary:sase-gate`.
  - It proposes hand-editing the `sase_artifacts.md` relation list, which is generated.
- **grk**
  - It proposes shipping `sase_goals.md` as a generated every-project template. That's
    premature (see the audience ruling in §2.2).
  - Its `tui_perf` budget additions duplicate existing rules.
- **cld**
  - It points memory at `docs/goals.md` as "the contract", but no epic owns such a
    page. The roadmap says only "docs" in G6 phase 4, and the design names no file.
  - Either the G1 plan should create a user doc, or `sase_goals.md` should link the
    design until one exists.
- **cdx**
  - Its D1 claim includes "failures fail open." Move that clause into its own record
    (see the decision-count ruling in §2.2).
  - A separate `goal-binding` strand isn't needed.
- **mus**
  - A single decision record leaves the storage choice undefended. "Why not just use
    beads?" was already asked once and needed its own research note.
  - Putting TUI keys in memory duplicates `default_config.yml`.

---

## 3. The recommended end state

### 3.1 Decision records

Keep each roster summary to 25 words or fewer; roster lines are the main cost.

| ID | Slug (suggested) | When | Claim (short) | Reopens when |
| --- | --- | --- | --- | --- |
| **D1** | `goals-host-binds` | **Now, before G1 planning** | The host binds every LLM turn to exactly one goal before spawn. Agents only name or adopt their own draft, and claim or keep open. Only a human settles. | A launch path can be bound neither in the runner nor on the unit wire; or per-model claim precision stays under the floor you set and a per-model policy can't contain it. |
| **D2** | `goal-ledger` | G1, citing G1's measured list latency and push retries | A goal is its own Rust-owned domain, not a bead type. Its state is immutable events plus live markers, written via the hidden clone. Hot reads are O(unsettled). Freshness is shown, never promised. Drafts stay local until named. | Push contention or hot-list p95 grows with settled history. Splitting the `goals` role into another repo is a *config* change, so co-hosting in the beads repo is deployment, not part of the claim (cdx). |
| **D3** | `goal-fails-open` | G3 | `builtin@goal` is required but fails open. A refusal, error, or ineligible claim becomes `keep_open` plus a diagnostic that `sase goal audit` reports. A binding failure launches the turn unbound. This narrows `host-owned-completion`'s "normally fails the run" for this one finalizer. | Audit shows fail-open diagnostics hiding claims you needed. |
| **D4** | `claims-replace-success-pings` | G6, with before/after notification volume | A successful completion is silent. One idempotent GoalVerify claim is the loud signal, and dismissing it never settles it. Errors, questions, and approvals keep their existing routes. Idle is a quiet backstop. | Shadow coverage falls below threshold, or finished work keeps being discovered late. |
| D5 *(conditional)* | `epic-per-verification-world` | After G6 | A cross-contract feature ships as sibling epics, each with ≤7 phases, one released contract, one verification world, and a done-definition with no calendar waits. | Write it **only if** G1–G6 finish with at most one remediation child in total. Pair it with one sentence in the `/sase_plan` skill source. Otherwise record what actually happened, or nothing. |

Notes on these records:

- **Why D1 and D3 are separate.** The roadmap already treats fail-open as a
  program-wide rule (cross-epic rule 2). But it is also the clause most likely to be
  narrowed later, and a D1 that bundles it would face the same partial supersession
  `record-before-admit` did.
- **D3's cost is new, and the record should say so (cld).** After G6, a suppressed
  claim produces *no* loud signal. The quiet Idle notice becomes the only backstop,
  which ties D3 to D4.
- **D1 links:**
  - It extends `host-owned-completion` from turns to outcomes. Link it; don't
    supersede it.
  - It is consistent with `gates-never-block`, because GoalVerify is created by the
    host after the turn.
  - Test evidence comes only from receipts (`receipts-prove-before-they-skip`).

### 3.2 Glossary strands

- **`glossary:goal`** (aliases: `goals`, `⌖`)
  - **Build it up with the program:** identity and statuses in G1, binding in G2,
    drafts and "every turn" in G4.
  - **Final form**, one paragraph:
    - Addressed as `goal:<id>` and shown with `⌖`.
    - Statuses: `draft` (machine-local), `active` (Running/Idle is derived, not
      stored), `review`, `done` (verified or acknowledged), and `dropped`.
    - The host binds every LLM turn to exactly one goal. Mechanical turns (monitor,
      gate, proc) inherit it.
    - **Not to be confused with:** a plan's `goal:` frontmatter field, which only seeds
      the outcome; a task bead, which is scheduled work; or agent status (a failed
      agent leaves its goal active).
    - `%goal:<id>` binds a launch; `@goal:<id>` only cites a goal.
- **`glossary:goal-claim`** (aliases: `claim`, `claims`), written in G3
  - An agent's `builtin@goal` assertion that the outcome is true now, carrying a claim
    sentence, resolvable evidence (mostly gathered by the host), 1–3 check-it steps,
    and any gaps.
  - It moves the goal to `review` and opens one GoalVerify gate. It is **never** a
    settlement.
  - Only an owner with no live contributor may claim, so phase workers and swarm
    members keep the goal open.
  - **Not** a bead's `claimed` status, a workspace claim, or a decision record's
    **Claim.**

**No other strands.** Draft, standing goal, binding, GoalVerify, answer
acknowledgement, and Idle are clauses inside these two strands or inside the
`sase-gate` edit. Add a separate term only when the landed code, docs, and UI use one of
them in ways that genuinely create ambiguity.

### 3.3 Reference note `sase/memory/sase_goals.md`

**Scope and size:**

- `type: reference`.
- **sase-project only**, hand-authored, not generated.
- About 40–60 lines.
- Create it in G2 (the first cross-cutting seam), and grow it through G6.

**Description.** The description is always loaded, and the trigger it names is the
note's real value:

> Read before changing agent launch paths or inherited launch metadata, finalizers,
> notification routing, or the goal ledger, CLI, or Goals tab.

**Body: tripwires plus pointers, not a second design doc.**

- **Authority.**
  - The host binds.
  - Agents may `list` and `show`, and may `name` or `adopt` only their own draft.
  - Every status verb, and `new`, is human-only.
  - Goal status is not agent status or bead status.
- **Launch paths (G2).**
  - Binding is resolved in the runner (`build_agent_meta`).
  - A new launch path or successor kind must carry `goal_id` through the preserved and
    inherited metadata, and must be added to the launch-path matrix.
  - `sase goal audit` stays at 0 unbound turns.
  - Prefer making the matrix fail on any unregistered path, so code enforces this rule
    even when nobody reads the note.
- **Finalizer (G3).**
  - `builtin@goal` runs after `commit` and fails open. Never let a goal error fail a
    turn (link D3).
  - Receipts are machine-local, so a claim embeds a receipt snapshot.
- **Ledger (G1).**
  - Never edit or delete an event file; only add or remove markers.
  - Write only through the hidden clone.
  - Never open settled goals on a hot path.
  - Relations are projections. Never write per-agent link events.
- **Privacy (G4).**
  - Named goal text publishes to the public beads repo.
  - Naming a goal publishes the creator's prompt.
  - `goals.visibility: local` exists for projects that need it.
- **Attention (G6).** Successes are silent, claims are loud, dismissing is not a
  verdict, and Idle is the backstop.
- **Links.**
  - D1–D4, `glossary:goal`, `glossary:goal-claim`.
  - `sase_beads.md`, `sase_artifacts.md`, `xprompts.md`, `dispatch.md`.
  - The user doc once it exists; until then, the design research note.

**Keep out:** the G1–G6 sequence, soak thresholds, flags, source line numbers, the full
CLI, key tables, the event vocabulary, and storage file names (`STORE.json`,
`goals-hot.json`). These belong to `-h`, `default_config.yml`, `sase goal doctor`, and
research.

### 3.4 Edits to existing memory

| # | File | Epic | Change |
| --- | --- | --- | --- |
| 1 | `glossary:artifact` | G1 | Add "a goal" to the list of durable records. |
| 2 | `glossary:artifact-reference` | G1 | Add `@goal` to the builtin kinds. It **cites** a goal (expands its card) and never binds one. |
| 3 | `memory-sase-artifacts.template.md` (the Model sentence) | G1 | Add goals. Relation rows come from the registry: just confirm `sase memory init` ran after G2, G3, and G4. |
| 4 | `xprompts.md`, Directives table | G2 | Add a `%goal:<id>` / `%goal:new` row. Add one sentence: agent-initiated launches inherit the goal the way `%tab` does, `%goal:new` opts out, settled goals are refused, and `@goal` only cites. |
| 5 | `dispatch.md` | G2 (remote-draft rule in G4) | **Rewrite** the "`%tab` travels" bullet so it covers `%tab` and `%goal` together, rather than adding a near-duplicate bullet. Once decided, state the rule for a remote child whose goal the target hasn't fetched yet, or which is still a local draft. |
| 6 | `memory-sase-beads.template.md` | G2/G3 | Two sentences. (a) An epic plan's `goal_id` binds every phase and land agent; phase workers keep the goal open and only the land agent claims. (b) A goal is verified intent and a bead is scheduled work; **closing a bead never settles a goal.** Keep `claimed` defined under Statuses so the collision stays visible. Link `sase_goals.md`. |
| 7 | `xprompts.md`, the `%final` paragraph and the "Rule" paragraph | G3 | Say that `builtin@goal` is a required instance ordered after `commit`, and that it fails open. |
| 8 | `glossary:sase-gate` | G3 | Add goal verification to the typed kinds. Its front door is `sase goal verify\|reject\|drop`, and the host, not the agent, creates it. |
| 9 | `glossary:routine` | G4, only if standing goals ship | One clause: routine runs bind to a per-routine standing goal and never claim. |
| 10 | `glossary:nav-item`, `glossary:nav-section` | G5 | Add the Goals tab: its lanes are nav sections and each goal row is a nav item. Collapsed Standing and Done-today groups follow the collapsed-banner rule. |
| 11 | `glossary:agent-relation-jump-target` | G5, then G6 | G5: classify the Goals-card agent chips. G6: recheck the "`,j`/`,J` unread" wording once ✅ success unread is retired. |
| 12 | *Optional:* `glossary:receipt` | G3 | One clause: a claim embeds a receipt snapshot so other machines can render it. |
| 13 | *Optional:* `generated_skills.md` › CLI/Skill Contract Synchronization | G3 | Widen its scope from `sase stitch create` alone to also cover `sase final submit` (the goal payload) and `sase goal`. |

**Why row 13 is worth considering (my addition):**

- The finalizer wire is `deny_unknown_fields`, and `builtin@goal` fails open.
- So if the `/sase_final` examples drift from the wire, agents' claims degrade
  *silently* into `keep_open`.
- The stronger fix is a G3 test that validates the skill's payload examples against the
  wire. The memory line is the backstop.

### 3.5 Leave unchanged

| Item | Why |
| --- | --- |
| Core `sase.md` template, `gotchas.md`, `rust_core_backend_boundary.md` | Already accurate or already covered, and each added line costs every turn in every project (§2.2). |
| `tui.md`, `tui_perf.md`, `tui_screenshot.md` | Existing rules cover G5. Edit only if G5 finds a *new* trap. |
| `cli_rules.md`, `sase_flags.md`, `lint_and_test.md`, `symvision.md` | Goals follows them as written. There is no goals flag after G6, and permanent loud pings would be config. |
| `sase_sizes.md` | Unchanged unless D5 is adopted. |
| The `task_types` web | `task_type: goal` was rejected twice. `sase goal new` is refused inside agent runs, so discovered work stays in task beads. |
| Existing decision records, including `host-owned-completion` | Extend them with links. Supersede only if the program actually reverses a clause. |
| A Goals memory web, per-epic notes, or copies of the design/roadmap | `corpus-before-mechanism`. The design goes stale as code moves, and epics are delivery units, not system facts. |
| `sase-core`'s `AGENTS.md` | Its conventions and recipes are generic. Enforce ledger rules with sase-core tests rather than prose. |

**Adjacent, but not memory.** The epics themselves own these skill sources:

- `/sase_final` goal paragraph (G3);
- `/sase_goal` (G3/G4);
- `/sase_plan`, `/sase_run`, and `/sase_notify` deltas (G2–G6).

Deploy them per `generated_skills.md` (commit, land, then `sase skill init`). Don't
copy their procedure into memory.

---

## 4. How to get there: memory inside each plan

Because of the authorization rule, the most useful thing you can do is outside memory:
**paste the matching row below into each G-plan prompt**. For example: *"This plan is
authorized to make these memory changes, in the phase that makes each one true: …"*

Add one line to each definition of done:

> `sase memory init --check` is clean and the listed memory items match landed behavior.

| When | Memory work |
| --- | --- |
| **Now** | D1 (only with your explicit OK, or as a `memory` bead; this research prompt doesn't authorize the write). Settle the routines policy first if you can: "every LLM turn" depends on whether routines get standing goals or an exemption. |
| **G1** | D2; `glossary:goal` stage 1; edits 1–3 |
| **G2** | Create `sase_goals.md` (authority, launch paths); `glossary:goal` stage 2; edits 4, 5, and 6a |
| **G3** | D3; `glossary:goal-claim`; edits 6b, 7, 8, and optionally 12–13; `sase_goals.md` finalizer section |
| **G4** | `glossary:goal` stage 3; edit 9 if standing goals ship; the remote-draft rule in edit 5; `sase_goals.md` privacy section |
| **G5** | Edits 10–11; decide on purpose whether the Goals-tab detail view is a "card" (it collides with `glossary:agent-data-card`), or give it another name |
| **G6** | D4 with the measured numbers; edit 11 recheck; `sase_goals.md` attention section; delete mid-rollout wording |

**What batching everything after G6 would cost instead:**

- Two to four weeks of agents reading false closed lists.
- A pile of `memory` beads, each filed with a proposal. The 2026-09-26 memory audit
  found that three of fifteen such proposals would have written *new* errors if
  applied verbatim, because the code had moved on in the meantime.

The end state is the same either way. Only the error window and the rework differ.

---

## 5. The pass to run once all epics are complete

Run this once, after G6 has removed its last flag. It is a small tale or one memory
commit, not an epic.

1. **Read HEAD, not the research.** Check every §3 item against the landed code: event
   names, verbs, the gate kind name, and tab lanes.
2. **Grep memory and skill sources for rollout tense**, such as `goals_` flags, `G1`–`G6`,
   `until cutover`, `alongside success pings`, and `beta`. Rewrite or delete each hit.
3. **Apply or close the `memory` beads** filed during the program.
4. **Clear decision debt.** For each G-plan, list every choice that came with a rejected
   alternative and a reopen condition. Record it or explicitly decline.
   `explicit-handoff-fails-closed` was recorded two days late during the `sase tool`
   program.
5. **Supersede; don't edit.** If the program changed a D1 clause (a routines exemption,
   a different ack default, an umbrella flag), write a new record and mark D1
   `superseded-in-part`.
6. **Revisit `host-owned-completion`.** Its reopen condition is "operational soak across
   enough real runs," and a required finalizer on every turn from G3 through G6 is that
   soak. If the protocol held, change nothing. If it didn't, write a new record.
7. **Evaluate D5** against its test. Write it plus the `/sase_plan` sentence, or skip
   both.
8. **Check the token budget.** Compare the size of `AGENTS.md` before G1 and after G6. If
   Goals added more than ~350 tokens, shorten roster summaries before adding anything.
9. **Run `sase memory init`.** Deploy skills from the landed tree.
10. **Watch item, not a change.** GoalVerify rejections with written feedback become the
    first structured corpus of human verdicts on agent claims. Per
    `corpus-before-mechanism`, build nothing yet. After a few hundred rejections, review
    the recurring reasons by hand to find which memory is actually missing.

---

## 6. Cost

| Always-loaded addition | Tokens |
| --- | --- |
| D1–D4 roster lines (~66 each at today's average) | ~265 |
| 2 glossary terms | ~12 |
| `sase_goals.md` description | ~45 |
| **Total** | **~320 (+7.6%)** |
| D5, if written | +66 |

- **Against the design's own tax.** The +320 tokens is several times the design's own
  per-turn tax (~40 tokens on a bound turn), so the discipline in §3.1 matters.
- **What it would take to go lower.** Folding D3 into D1 saves ~66 tokens, at the
  supersession risk described in §3.1. That is the only fold I'd consider.

---

## 7. Decisions for you

| # | Question | My recommendation |
| --- | --- | --- |
| Q1 | Record D1 before G1 is planned? | **Yes.** The `sase tool` program did the same with `record-before-admit`. Keep D1 to invariants. |
| Q2 | Routines: standing goals, or an exemption? | Decide before writing D1 if you can, so its "every LLM turn" claim never needs superseding. |
| Q3 | Keep D3 separate, or fold it into D1? | **Separate.** It narrows another record and needs its own reopen condition. |
| Q4 | A remote `%dispatch` child when the target hasn't fetched the goal, or the goal is still a draft? | Decide in G2 or G4, and record it in `dispatch.md` (edit 5). |
| Q5 | Is the Goals-tab detail view a "card"? | Make it a real deck, or give it a non-card name. Decide in G5. |
| Q6 | Which user doc owns the Goals contract? | Have the G1 plan create one, so memory can point to it instead of to research. |

---

## 8. Recommended memory updates and additions

**Before any Goals epic is planned**

1. **Add `decisions/goals-host-binds`** (D1). The host binds every LLM turn to one goal;
   agents only name or adopt their draft and claim or keep open; only humans settle. It
   holds invariants only: no fail-open, no storage, no attention clauses.
2. **Change your process, not a memory file:** put the §4 memory row into every G-plan
   prompt, and add `sase memory init --check` plus a memory-match check to each
   definition of done.

**Added during the epics, and present when the program is complete**

3. **Add `decisions/goal-ledger`** (D2, G1). Goals reuse the beads *repo*, not the beads
   *model*: immutable events plus live markers, hidden-clone writes, O(unsettled) reads.
4. **Add `decisions/goal-fails-open`** (D3, G3). A goal problem never fails a turn, and
   the Idle notice is the post-cutover backstop.
5. **Add `decisions/claims-replace-success-pings`** (D4, G6), with measured before/after
   volume.
6. **Add `glossary/goal.md`** (G1 → G4) and **`glossary/goal-claim.md`** (G3), each with
   a "not to be confused with" clause.
7. **Add `sase_goals.md`** (G2 → G6). It is a sase-only reference note of ~40–60 lines:
   maintainer tripwires for launch paths, finalizers, ledger, privacy, and attention.
8. **Edit the lists Goals would make wrong:**
   - `glossary:artifact`;
   - `glossary:artifact-reference`;
   - the Model sentence in the artifacts template;
   - `xprompts.md` (the `%goal` row, and `builtin@goal` as a required instance);
   - `dispatch.md` (merge `%tab` and `%goal` into one bullet, plus the remote rule);
   - the beads template (epic binding, and "closing a bead never settles a goal");
   - `glossary:sase-gate` (GoalVerify);
   - `glossary:nav-item` and `glossary:nav-section` (Goals tab);
   - `glossary:agent-relation-jump-target`;
   - `glossary:routine`, only if standing goals ship.
9. **Optional:**
   - a clause in `glossary:receipt` about claim snapshots;
   - widening the CLI/Skill contract-sync rule in `generated_skills.md` to cover
     `sase final submit` and `sase goal`.

**Once all epics are complete**

10. **Run the §5 consolidation pass:**
    - audit against HEAD;
    - remove rollout wording;
    - clear or close memory beads;
    - clear decision debt, superseding rather than editing;
    - check the token budget;
    - republish.
11. **Only if G1–G6 meet its test,** add the conditional
    `decisions/epic-per-verification-world` (D5) plus one sentence in the `/sase_plan`
    skill source.

**Don't:**

- change core memory (`sase.md`, `gotchas.md`, `rust_core_backend_boundary.md`);
- create a Goals memory web, a `task_type: goal`, or per-epic notes;
- make `tui`/`tui_perf`, `cli_rules`, `sase_flags`, or `generated_skills` catalog
  additions;
- copy into memory the CLI, the keymap, the event vocabulary, storage filenames, soak
  thresholds, G1–G6 numbering, or the injected intake text;
- edit `host-owned-completion` in place.
