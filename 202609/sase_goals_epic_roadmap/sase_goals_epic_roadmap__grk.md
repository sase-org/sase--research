# Splitting SASE Goals into distinct, verifiable epics

_Researcher `grk` · 2026-09-27 · independent 2s-swarm report_

**Question.** The Goals design in
[`research:202609/sase_goals_design/sase_goals_design.md`](../sase_goals_design/sase_goals_design.md)
is ready to implement. Is it one `xlarge` epic, or a program of smaller epics whose
lands a human (and a land agent) can actually close?

**Answer.** Treat the design as a **program of four sibling epics plus one cutover
epic**, sequenced with bead dependencies. A single epic covering P0–P4 of the design
is the wrong unit: the verification axes do not fit in one land audit, and this repo's
recent remainder/child-epic pattern is exactly what that unit produces.

---

## 0. Recommended solution

Ship Goals as **five beads**, not one:

| # | Bead | Size | What "done" means | User-visible? |
| --- | --- | --- | --- | --- |
| T0 | Two **tales** (or first phases of E2/E4) | `medium` / `small` | Child `agent_meta.json` records `parent_agent_name`; `JumpToAgent` uses the reveal path | No |
| **E1** | **goals-ledger** | `xlarge` | Conflict-free goal ledger, hot list, `sase goal` CLI, `goal:` kind, `goals` beta flag | CLI only, flag off |
| **E2** | **goals-binding** | `xlarge` | Every new LLM turn has exactly one `goal_id` before spawn; name/adopt/skill/plan stamp | CLI inventory of live work |
| **E3** | **goals-claims** | `xlarge` | Required `builtin@goal`; one claim → one `GoalVerify` gate; evidence rules | Notifications + CLI verify |
| **E4** | **goals-surfaces** | `xlarge` | Top-level Goals tab, Agents chip / FINAL Goal card / by-goal grouping | Yes, still opt-in |
| **E5** | **goals-cutover** | `large` | Success completions silent; answer ack; Idle notices; flag removed after a **human** soak | Default-on Goals |

Dependencies: `T0-lineage → E2`; `T0-jump → E4`; `E1 → E2 → E3 → E4 → E5`.

Do **not** create a parent epic whose land agent is allowed to plan children. Track the
program in this research note (and, if wanted, a human-owned plan bead that is closed
by hand when E5's flag bead closes).

The design's own five-phase table (P0–P4 behind one `goals` flag) is a good *delivery
order* and a bad *epic boundary*. Keep the order; change the unit of land.

---

## 1. Why this is hard to verify as one epic

The design is coherent. The implementation surface is several products sharing one
model. A land agent has to certify all of the following at once:

1. **A new `sase-core` domain** (types, events, reducer, ledger I/O, hot projection,
   binding function, eligibility, evidence validation, `goal:` kind). The existing
   `bead` module is ~33k lines / 61 files; `finalizer` ~8.5k; `artifact_ref` ~9.4k;
   `artifact_link` ~7.5k. Goals will be smaller than beads and still a full crate
   module plus `sase_core_py` bindings plus a pin move in `sase-core-revision.txt`
   (currently `0e8981a1f1…`).
2. **Launch-path combinatorics.** The design's acceptance list names direct, plan,
   bead, swarm, `%alt`, `%repeat`, session, child, retry, dispatch, gate, pipe,
   question, and monitor paths. Binding is a pure function over launch facts, but
   Python has to *supply* those facts at every entry point (`launch_spawn.py`,
   `bead/work.py`, pipe/questions/monitor/gate follow-ups, `/sase_run`, clan fan-out).
3. **A required finalizer on every normal return**, ordered after commit, including
   clean trees. Today's config is `defaults: [commit]` and `required: []`
   (`src/sase/default_config.yml`). `builtin@commit` already dominates
   `src/sase/finalizers/`. Adding `builtin@goal` touches declaration context, recovery,
   prepared-monitor completion, and token resolution (`@commit` / `@reply` after the
   model has exited).
4. **A new typed gate** (`GoalVerify`) in a gate system that already has dedicated
   kind validators for plan, question, launch, task triage, sudo, flag triage, and
   others (`src/sase/notification_gates/kind_validation/`). Remote Attention must
   dedupe on goal id + claim id (`docs/notifications.md`).
5. **TUI chrome.** `TAB_ORDER` is currently `("agents", "artifacts", "services")`
   (`src/sase/ace/tui/tab_order.py`), with a regression test that pins that triple.
   A fourth tab implies keymap, persistence, goldens, inbox-chip, empty state, and
   Agents-tab enrichers (chip, FINAL Goal card, `o` grouping). PNG snapshots are
   outside `just check`; they live in `just fix-tui-screenshots` / CI `visual-test`.
6. **An attention cutover.** Successful completion today sends `JumpToAgent` tagged
   `done` (`run_agent_runner_finalize.py` around the `tags=["done"]` payload). The
   design retires that unread projection. That is a sunset of default UX, and it
   needs soak *after* claims and the tab exist.
7. **Cross-machine sync and a performance contract** (`sase goal list` p95 < 50 ms
   at 1,000 unsettled; adding 100k settled goals must not move hot-list p95 more
   than 10%). The 100k test is a bench. Two-machine rebase is a fixture. Neither
   belongs in the same land as visual goldens.
8. **A new sidecar role** that co-hosts in the beads repo. `RESERVED_SIDECAR_ROLES`
   is `{plans, beads, agents}` (`src/sase/sdd/_store_types.py`). Writes go through
   the hidden host clone (`machine-link-writes-off-primary`). Local-only projects
   need a labeled fallback.

Those are **six independent definitions of done**. One land agent cannot hold them.
The design already lists twelve acceptance tests spanning all six.

### 1.1 What "hard to verify" looks like in this repo right now

September 2026 plans under `202609/` contain **265** `tier: epic` files. Counting
`- id:` phase entries:

- median **3** phases, mean ~3.9
- only **5** epics have 12+ phases
- the outlier is `agents_tab_final_deck.md` at **20** phases (core wire → Python
  journal → TUI deck → cutover → docs)

The design's P0–P4, written as five *fat* phases of one epic, will expand toward
that 20-phase shape as soon as a planner decomposes "the ledger, the binding
ladder, the finalizer, the tab, the cutover."

The remainder pattern is already the project's pressure valve:

- `e4_landing_remainder.md` (`sase-1ah.8`): parent E4 closed seven phases; the land
  audit still needed Rust report + published-wheel pin + live Athena proof. The
  child stalled on a `just check` that failed for unrelated Symvision findings, a
  PyPI floor the local pin had already passed, and a live demonstration no phase
  note recorded.
- `deck_cutover_landing_repairs.md` (`sase-17d.10.1.4`): three cutover phases
  closed; the land agent found the goldens phase closed without finishing its
  goal. The child is *only* visual migration + coverage goldens + live screenshots.
- `sase-11e` nested four rounds of child epics in a day because `bd/land_epic`
  plus `%auto` has two exits (close, or plan the leftovers) and no owner freeze
  (`research:202609/sase_11e_round4_child_epic.md`).
- Overnight stall research: silent success with an open bead, lost
  `just check-full` handoffs, unbounded verify retries, and land agents spawning
  nested children (`research:202609/overnight_epic_stall_prevention/…`).

A Goals mega-epic would combine **all four** of those failure modes: core pin,
visual goldens, live soak, and a land agent whose leftover list is unbounded
("one more launch path", "one more golden", "wheel not on PyPI yet").

### 1.2 A single epic is appropriate only for a narrow first slice

If the goal is "start coding this week" rather than "finish the design," **E1+E2
as one epic** is a defensible MVP: ledger + host binding + CLI, flag off, no
claims, no tab, no cutover. That epic's land is: every new LLM turn has a
`goal_id`, `sase goal list` meets the hot-path budget, a five-member swarm shares
one goal. It is still `xlarge`. It is *not* the design. Claims, the tab, and the
attention cutover remain later epics.

Putting the whole design in one epic in order to "keep the invariant atomic" does
not make the invariant easier to prove. It makes the land agent the bottleneck
that currently produces remainder children.

---

## 2. Split criteria (what makes an epic distinct and verifiable)

An epic boundary is good when all of these hold:

1. **One verification world.** Either sase-core unit tests, or a launch-path
   matrix, or finalizer/gate tests, or ACE PNG goldens, or an observational soak.
   Mixing two worlds is how remainder children get created.
2. **A frozen, numbered DoD** that a land agent can grep for. Open-ended clauses
   ("every launch path", "every reachable message", "check-full green including
   host-red budgets") are how `sase-11e` grew rounds.
3. **No calendar wait in a phase.** PyPI `sase-core-rs` floors, 14-day soaks, and
   "owner will click around" are human or release-plz work. Put them on the flag
   bead or a task, not in `sase bead work` close criteria. Linked-checkout pin
   ratchet is enough for *this* repo's agents.
4. **User-reaching behavior behind one beta flag** (`sase flag new goals`),
   created in E1, removed in E5. Tests cover both states until E5 deletes the Off
   branch. E5 is the only epic allowed to change default attention.
5. **Independently useful once landed.** Someone who enables the flag after E2
   can list in-progress outcomes. After E3 they get a verify inbox. After E4 they
   get the tab. After E5 the old success dots go away. Each step is a product.
6. **Land agents may not spawn child epics.** Leftovers become task beads or a
   human-approved follow-up. This is a written constraint in every plan's land
   section, because the runner still `%auto`-approves land proposals today.

---

## 3. Groupings that look tempting and fail the criteria

### 3.1 Design P0–P4 as five phases of one epic

This is the design's own table. P0 is unrelated bugfix work (lineage, jump,
prompt publication). P1 mixes crate I/O with launch injection. P2 is a new
finalizer. P3 is a new top-level tab. P4 is a sunset. One land, five products.

### 3.2 "Core vs Python vs TUI" (the E4 remainder shape)

Rust-then-adapter-then-live is the split that *already stalled* `sase-1ah.8`.
The live phase waits on a published wheel and a human demo. Keep core work
inside E1's own phases, ratchet the **source pin** in the last E1 phase, and
leave the PyPI floor as a follow-up task.

### 3.3 "MVP tab that also claims and also silences pings"

That is the whole design minus storage. The tab has nothing to show until
binding exists; claims have nowhere to persist until the ledger exists; silencing
pings without a working GoalVerify inbox loses attention rather than moving it.

### 3.4 Micro-epics (one per CLI verb, one per TUI widget, one per event type)

Integration then happens in a sixth "wire it together" epic whose land audit
reopens everything. Four product-shaped epics plus cutover is the coarsest split
that still isolates verification worlds.

### 3.5 A parent epic with child epics as phases

Child epics are how this project encodes leftovers, not how it encodes a
roadmap. `sase-xe` reached depth 6 with 11 children and was still open after 10
days; 13% of September roots reached depth ≥2
(`research:202609/sase_11e_round4_child_epic.md`). Sibling epics with `sase bead
dep` keep each land scoped. A parent whose land is "children closed, do not
plan more" still runs `bd/land_epic` with `%auto` unless a human launches it
without `%auto`. Skip the parent.

---

## 4. The program, epic by epic

### T0a. Persist parent lineage — tale, `medium`

**Why it is separate.** `parent_agent_name` is **read** from requester
`agent_meta.json` in `launch_request_planning.py` (`requester_context` /
`_agent_meta_requester_context`) and listed in the name-migration allowlist. The
child bootstrap path (`run_agent_runner_bootstrap.py` `_write_bootstrap_agent_meta`)
writes pid, process identity, output path, and launch scratch key. It does not
write `parent_agent_name`. `launch_spawn.py` already pops inherited `SASE_PLAN`.
The design's binding ladder step 5 ("Parent") cannot work until this write
exists. It is also useful for Agents-tab ancestry and LaunchApproval without
Goals.

**Done when:** a `/sase_run` child and a LaunchApproval child both persist
`parent_agent_name` (and, once E2 exists, `parent_goal_id`) in `agent_meta.json`;
tests cover the write, not only the list projection. Hidden helpers inherit.
Mechanical monitor/gate/`%proc` members do not invent a new parent.

**Stay out:** goal objects, CLI, TUI.

### T0b. `JumpToAgent` uses the reveal path — tale, `small`/`medium`

**Why it is separate.** `handle_jump_to_agent` in
`actions/agents/_notification_handlers.py` linearly scans `app._agents`, sets
`current_idx`, and returns. It does not expand collapsed groups, clear a blocking
filter, or call `reveal_agent_navigation_target`
(`actions/navigation/_agent_reveal.py`). Goal→agent jumps will be wrong on a
grouped Agents tab until this is fixed. The design is right that fixing
`JumpToAgent` the same way is cheap and unblocks E4.

**Done when:** a test drives a grouped/collapsed live row and a filtered-out row
(toast + reveal or Artifacts ▸ Agent fallback). Existing JumpToAgent
notifications keep working.

**Stay out:** Goals tab, `JumpToGoal`.

Either tale may be absorbed as the first phase of E2 / E4 if launching two extra
plans is more overhead than it is worth. They must not sit inside E1 (ledger
land should not touch TUI jump code).

---

### E1. `goals-ledger` — the store and the CLI

**Intent.** A goal is a durable artifact you can create, name, show, and list in
O(n_unsettled) time. No agent is bound yet. Humans (and tests) use `sase goal new`.

**Repos.** `sase-core` first, then sase CLI/bindings, then pin ratchet.

**Suggested phases (5, all `medium` except the pin `small`):**

1. **domain** — ids, statuses (`draft`/`active`/`review`/`done`/`dropped` and
   flavors), events, reducer, compare-and-swap `named`, marker invariant
   (marker exists iff reduced status is unsettled). Pure tests, no git.
2. **ledger-io** — `goals/` layout in the beads hidden clone: `STORE.json`,
   `live/<id>` empty markers, `items/<id>/events/<ulid>.json`. Append-only
   writes, fetch/rebase/revalidate/push with conflict-free fixtures (two clones,
   two claims, drop-vs-claim, adopt-vs-verify). Local-only fallback repo for
   projects without a beads sidecar, labeled `local only`.
3. **hot-projection** — machine-local `goals-hot.json` keyed by directory
   signatures; rebuild from `live/` alone; file-open tracing proving settled
   `items/` are not opened on `list`. Rust fast path analogous to
   `bead_fast_path.py`.
4. **cli-and-kind** — `sase goal` group (bare → `list`, alphabetical verbs, short
   aliases per `cli_rules`). Agent-safe verbs: `list`, `show`, `name`, `adopt`.
   Human-only: `new`, `verify`, `reject`, `drop`, `reopen`, `merge` (the last
   five can 501 until E3 if that keeps the land small; `new`/`list`/`show`/`name`
   are required). `goal:` catalog entry in `artifact_ref/kinds.rs` (live,
   reserved, completion-offered). `sase artifact read goal:<id>` renders a card
   from the ledger. Create the `goals` **beta** flag (`sase flag new`); Off =
   CLI refuses / no-ops with a one-line "disabled" message.
5. **pin-and-budget** — move `sase-core-revision.txt`; Python adapter tests;
   measured `list` p50/p95 against 0 / 100 / 1,000 live markers and 100k settled
   junk. Record the numbers in the phase note. **Do not** wait for PyPI.

**Land DoD (frozen):**

1. `sase goal new` + `name` + `list --json` round-trip on a throwaway project.
2. Two hidden clones appending events rebase without a content conflict; marker
   races resolve by reduction.
3. `strace`/`file-open` (or the core test's open tracer) on `list` after 100k
   settled goals does not open settled event dirs; p95 within the design's
   budget on the test machine, numbers recorded.
4. Flag off: CLI exits with the disabled message; tests cover both states.
5. `goal:` parses and `sase artifact read` renders; no `pursues`/`evidences`
   relations yet (those need agents and claims).

**Out of scope for E1:** launch injection, finalizer, TUI, notifications,
prompt publication, `/sase_goal` skill (no agent loop yet), `goals` sidecar
**split** (co-host in beads; split only after measured contention, per
`corpus-before-mechanism`).

**Why this epic is independently useful.** You can create and inspect goals
from a shell. Later epics consume a stable reducer rather than inventing one
under launch-path pressure.

---

### E2. `goals-binding` — the host guarantees a goal

**Intent.** Every LLM agent turn is bound to exactly one primary goal before the
provider starts. The agent names a draft or adopts an active goal. Planners stamp
`goal_id` on the plan. You never have to write a goal.

**Depends on:** E1, T0a.

**Suggested phases (6 `medium`):**

1. **wire** — `goal_binding` on the launch plan (not `extra_env`); persist
   `goal_id` in `agent_meta.json`; `SASE_GOAL_ID` convenience only.
2. **resolver** — the Rust ladder from the design (§4.2), facts supplied by
   Python: explicit `%goal` / `%goal:new`, session, plan `goal_id`, clan, parent,
   bead, routine standing (or **defer standing routines** — see below), else
   draft. Drafts machine-local; prompt excerpt stripped of directives.
3. **injection** — bound turns get the ~40-token line; draft turns get the
   intake block after preprocessing; `submitted_xprompt.md` untouched.
   Plan-mode skips intake; `sase plan propose` names/refines from
   `title`/`goal` with source `plan`.
4. **skill-and-cli-agent** — generated `/sase_goal` from
   `src/sase/xprompts/skills/` teaching `list`/`show`/`name`/`adopt`. Naming is
   compare-and-swap. Adopt of a `review` goal is a no-op on claim until E3
   exists (document that; do not implement retract yet). `%goal` in
   `_KNOWN_DIRECTIVES`; `@goal:` cites only.
5. **path-matrix** — one table in the plan, one test module per row. The table
   *is* the DoD. Suggested frozen rows (trim rather than add):

   | Path | Expected bind |
   | --- | --- |
   | Ad-hoc user launch | new draft, agent names |
   | `%goal:<id>` | that unsettled goal; settled → refuse |
   | `%goal:new` | new draft, no inherit |
   | Clan of 5 | one shared draft; first `name` wins |
   | Pipe / questions / monitor / gate follow-up | inherit |
   | Plan propose → code successor | plan's `goal_id` |
   | Epic phase + land | same `goal_id` via bead → plan |
   | `/sase_run` child | parent's goal |
   | Retry / `%repeat` / `%alt` | inherit |
   | Dispatch | inherit launching project |
   | Hidden helper | inherit, not listed as owner |

6. **hygiene** — unnamed crashed draft auto-named + Idle (Idle is derived from
   inventory; without TUI, CLI `list` shows `active` with no live contributor).
   Adopted drafts never appear in the shared ledger.

**Land DoD:**

1. Fixture launches for every row of the frozen table; each child `agent_meta.json`
   has exactly one `goal_id` before simulated spawn.
2. Mechanical procs create none.
3. Five-member clan → one goal.
4. Binding to a settled goal is refused.
5. Flag off: no `goal_id`, no intake block, existing launches unchanged.

**Defer from E2 (task beads, not phases):**

- Routine **standing** goals. The design wants them; they are a special case that
  will expand the matrix (can't claim, collapsed Standing group). Ship E2 with
  "routines inherit a per-routine unclaimable goal **or** bind like hidden
  helpers" as an owner decision in the plan, then file the standing-goal UX as a
  task for E4.
- Follow-up-prompt retract/chain (needs Review/Done from E3).
- `can_claim` roles (needs E3).

**Why this epic is independently useful.** `sase goal list` becomes the answer
to "what is in progress?" even before anyone claims. Swarm duplicate-goal
spam is already gone.

---

### E3. `goals-claims` — agents claim, you settle

**Intent.** A required `builtin@goal` after commit. Eligible agents `keep_open`
or `claim`. A claim publishes a `claimed` event, opens one `GoalVerify` gate,
and notifies. You verify / reject / drop from TUI inbox, CLI, mobile, Telegram.
Successful agent completions **still ping** (cutover is E5).

**Depends on:** E2.

**Suggested phases (6 `medium`):**

1. **obligation-and-payload** — host context: goal id/revision/status/title/
   outcome/criteria, `draft`, `can_claim` + reasons, evidence candidates.
   Agent payload: `keep_open` + progress, or `claim` + sentence + refs +
   check-it steps + gaps. Draft turns include `name`. `decide_goal_action` in
   sase-core. `sase_final` skill paragraph.
2. **eligibility** — host-derived roles (phase worker cannot claim; land can;
   wait-dependency cannot; routine cannot; else owner). No other contributor
   live. `@commit` requires commit success. Stale revision →
   `stale_final_context`.
3. **evidence** — resolvable refs with provenance; `@commit`/`@reply` tokens
   resolved after commit; receipt **snapshot** embedded in the event (receipts
   are machine-local — glossary *Receipt*). Strength badge. Gaps required as a
   field (may be empty). No blanket test-receipt rule;
   `goals.require_receipt_for_code` is config, default off.
4. **gate-and-notify** — `GoalVerify` kind (Verify / Reject+feedback /
   Drop). Notification action `JumpToGoal` (handler can be a stub that opens
   CLI/`sase goal show` until E4). Idempotent on `goal:<id>:claim:<n>`. Read or
   dismiss is never a decision. Remote Attention dedupe. Plan-only goals
   suppress a duplicate alert next to PlanApproval.
5. **relations-and-prompts** — projected `pursues` (agent→goal), `evidences`
   (artifact→goal), `defines` (plan→goal). Closed registry additions in
   `docs/artifact_links.md` + core. Naming a goal publishes the creator's
   `submitted_xprompt.md` into the agents-sidecar archive (today publication is
   mostly commit/plan-approval — answer-only goals would otherwise never
   leave the machine). Bodies stay in the archive; the goal stores ref+digest.
6. **handoffs** — plan/questions/monitor/pipe/gate make no goal decision;
   prepared monitor green claims with the monitor receipt; red `keep_open`;
   declaration-recovery turn asks for the goal payload; follow-up prompt to a
   Review goal retracts the claim.

**Land DoD:**

1. Flag on: every normal return includes a goal decision; `keep_open` is silent.
2. One claim → exactly one gate across retry and two machines (fixture).
3. Missing/stale/cross-project evidence blocks the claim; no gate created.
4. Phase worker `can_claim=false`; land worker true; live sibling blocks claim.
5. `@commit` refused when commit was deferred.
6. Adopted draft still never hits the shared ledger.
7. Flag off: `required: []` behavior unchanged; no GoalVerify.

**Stay out of E3:** Goals tab, Agents chip, silencing `done` pings, answer-ack
default (explicit `v` is fine until E5), Idle notices, visual goldens.

**Why this epic is independently useful.** This is the attention product the
design is for. You can verify from the inbox and `sase goal verify` without a
new tab. Shipping claims *alongside* today's success pings is the design's own
step 1 of cutover; stopping here lets you live with dual noise until E5.

---

### E4. `goals-surfaces` — the Goals tab and Agents integration

**Intent.** Discoverability. `Agents | Goals ⌖N | Artifacts | Services`. Review →
Running → Idle. Card order You asked → Outcome → Claim → Check it → Evidence →
Gaps → Agents → Timeline. Numbered jumps. Agents-tab chip, FINAL Goal card
(enricher on the existing FINAL deck, not a new widget type), `o` grouping by
goal.

**Depends on:** E3, T0b.

**Suggested phases (6–7 `medium`):**

1. **tab-shell** — `TAB_ORDER`, badge = Review count, persistence, empty state,
   keymap registration in `default_config.yml`, `synced Ns ago` watermark.
   Contract tests first; goldens in a later phase.
2. **lanes-and-rows** — Review / Running / Idle derived from ledger + local
   agent inventory; contributor pips; Idle progress note; collapsed Standing /
   Done today (Done today lazy).
3. **card-and-keys** — v/r/x/l/e/m/a/p/n///P/h as in the design; same renderer
   for the Agents FINAL Goal card.
4. **agents-integration** — identity-header chip; by-goal grouping banners
   Review→Running→Idle; unread ✅ retired **only in this tab's local chrome
   when the flag is on**, without silencing the notification send path (E5).
5. **jumps** — `JumpToGoal`; agent chips through reveal; artifact chips through
   the relation rail; fallback to Artifacts ▸ Agent.
6. **goldens** — scoped `just fix-tui-screenshots` for Goals tab + Agents chip
   + FINAL Goal card, desktop-width and a narrow width. Inspect every PNG.
   Inbox chip `⌖N` if it shares the top bar.
7. **docs** — `docs/` page, changelog, skill already exists from E2.

**Land DoD:**

1. Flag on: tab exists in second position; badge hides at 0 Review.
2. A claimed goal appears in Review with evidence chips that jump.
3. Goal → collapsed live agent reveals the row (T0b).
4. Flag off: `TAB_ORDER` remains three tabs; no Goals keymap collisions;
   existing Agents goldens unchanged.
5. Visual `--check` green for the new fixtures; no requirement that the
   entire snapshot corpus was regenerated.

**Stay out of E4:** silencing JumpToAgent `done`, answer-ack-on-open, flag
removal, 100k TUI benches (reuse E1's CLI numbers; TUI paints the projection
off-thread per `tui_perf` — add a frame-budget test if cheap, not a soak).

**Why this epic is independently useful.** This is the daily loop. It can land
while success pings still exist; you will have two ways to notice a finished
outcome, which is the safe order.

---

### E5. `goals-cutover` — quiet process, loud outcomes

**Intent.** Claims replace success pings. Answer-only claims acknowledge when
you open the answer (`done · acknowledged`, undoable). Idle goals get a quiet
notice. The `goals` beta flag's Off branch is deleted and On becomes
unconditional.

**Depends on:** E4, plus a **human** soak (not an agent phase).

**Suggested phases (3):**

1. **ack-and-idle** (`medium`) — implement answer-ack and Idle notices behind
   the flag, still sending `done` pings. Metrics counters: claims/day, verify/
   reject/ack/lapse, adopt vs name, notification volume.
2. **silence-success** (`medium`) — under the flag, stop emitting
   `JumpToAgent`+`done` and retire Agents-row unread ✅ for successes. Errors,
   questions, approvals, sudo, triage unchanged. Migrate existing unread
   success rows. Dual-path tests: flag on silent, flag off noisy (until
   removal).
3. **flag-removal** (`small`) — **human-gated**. After you have used flag-on
   for a real interval (days, not an agent `sleep`), run `sase flag` removal:
   delete the Off branch, make On unconditional, close the flag bead. Record
   the metric snapshot in the close note.

**Land DoD:**

1. Flag on: a successful `keep_open` turn produces no completion notification;
   a claim still produces exactly one GoalVerify.
2. Opening an `@reply`-only claim acknowledges; `u` undoes; dismiss does not
   settle.
3. Failures still `ViewErrorReport`.
4. After phase 3: no `goals` flag; tests have no Off branch.

**Do not** encode "14-day soak" as a worker that waits. E4's remainder and
E4-receipts both died on live/owner checks sitting inside `sase bead work`.
Phase 3 is a FlagTriage / human close.

---

## 5. Flag, pin, and landing rules that keep the program closable

**One beta flag, `goals`.** Created in E1 with `sase flag new`. Enabled on your
machines when you want to eat the dogfood (after E2 at the earliest). Removed
in E5. Do not add `goals_tab` / `goals_quiet_success` unless E5's soak shows
you need to ship the tab without silencing pings; that would be a *config*
field, not a second flag (flags are temporary).

**Source pin, not PyPI, in DoD.** E1 and any later core-touching phase ratchet
`sase-core-revision.txt` and run sase against the linked checkout. A
`sase-core-rs>=…` floor raise is a task after release-plz publishes, owned by
the same human who closes E5. Writing "fresh install must load `goal:`" into
E1/E3 land criteria recreates `sase-1ah.8`.

**`just check` is the phase default.** `just check-full` is the land agent's
one serialized gate, and only when the prompt names it. Visual work in E4 uses
scoped `just fix-tui-screenshots`. This is `check-full-is-explicit` plus the
overnight-stall lesson about unbounded full-suite retries.

**Land section in every plan (copy this):**

- Completion is judged against **this plan's numbered DoD**, not against the
  design doc's twelve-item list.
- Unmet design items that belong to a later epic are out of scope.
- Regressions caused by this epic become phases or tasks **in this epic** only
  if they break this epic's DoD; otherwise `/sase_new_task`.
- **No child epic.** If the land agent wants to plan leftovers, it stops and
  writes `PROPOSED FOLLOW-UP` / a task, and a human decides.
- Launch the land agent **without `%auto`** until nested-epic auto-approve is
  capped in the runner.

**Cross-project work.** The design's open question 5 (goal lives in the
launching project) is an E2 owner decision. Accept it in E2's plan; do not
leave it for a land audit to reinvent.

---

## 6. Mapping from the design's P0–P4

| Design phase | Goes to | Why the land changes |
| --- | --- | --- |
| P0 parent lineage | **T0a** / E2.1 | Independent bugfix; needed for binding step 5 |
| P0 JumpToAgent reveal | **T0b** / E4.5 | Independent TUI bugfix; needed for goal→agent jumps |
| P0 prompt publication on name | **E3.5** | Needs a named goal and the archive trigger; answer goals |
| P1 ledger / reducer / fast CLI | **E1** | Core verification world |
| P1 binding ladder, drafts, skill, plan stamp | **E2** | Launch-path verification world |
| P2 `builtin@goal`, GoalVerify alongside `done` pings | **E3** | Finalizer + gate world |
| P3 Goals tab, Agents enrichers, `goal:` relations | **E1** kind, **E3** relations, **E4** tab | Split so goldens do not share a land with the reducer |
| P4 silence successes, ack, Idle, soak, remove flag | **E5** | Sunset + human soak |

The design's twelve acceptance tests map cleanly: 1–2, 11–12 → E2; 3–4, 6–8 →
E3 (8's concurrency also E1); 5 → E3.5; 9 → E1; 10 → E4.

---

## 7. What I independently checked in code

- `SASE_PLAN` is popped on every spawn (`launch_spawn.py`
  `_remove_inherited_sase_plan_env`). Using it as "has a plan" would mis-bind
  epic turns. The design is right; E2 must not revive that check.
- `parent_agent_name` is requester context, not a child write. T0a is real
  work, not scaffolding theater.
- `handle_jump_to_agent` does not reveal. T0b is real work.
- `TAB_ORDER` is three tabs; `tests/ace/tui/test_services_tab_id.py` asserts it.
  E4 owns that churn.
- Finalizers: `required: []`, only `builtin@commit` in defaults. E3 is a
  behavior change on every turn.
- Artifact relation registry is closed (`docs/artifact_links.md`). E3 must add
  `pursues` / `evidences` / `defines` / `follows` as schema, projected from
  events.
- Artifact kinds are a compiled catalog (`artifact_ref/kinds.rs`). `goal:` is
  an E1 catalog row plus a resolver, not a document-role sidecar kind.
- Sidecar roles: `goals` is not reserved today. Co-hosting in beads is an E1
  layout choice (`goals/` prefix) plus hidden-clone writes; a later split is a
  role-registry change, not a v1 epic.
- Completion noise is centralized in `run_agent_runner_finalize.py` (`action =
  "JumpToAgent"`, `tags=["done"]`). E5 has a single send-path to change.
- Project epic size: median 3 phases. Targeting 5–7 medium phases per Goals
  epic matches landed work. Targeting 20 (FINAL deck) does not.

Prior Goals research (`goal_outcomes_and_verification`) already sequenced
"core model → launch bind → finalizer → notify then retire pings → TUI." The
later design flipped TUI earlier for discoverability. For **verification**,
the older order is better: **claims (inbox) before the tab**, tab before
silencing pings. You can live in the inbox for a week without a fourth tab.
You cannot silence success pings before claims exist.

---

## 8. Risks of this split, and how to contain them

**Schema churn.** E1 ships statuses and events E3 extends (`claimed`,
`claim_retracted`, `settled`). Define the **full event enum** in E1 with E3
events rejected as "not enabled until claims," or reserve the event names in
the schema fence so E3 does not break E1 readers. Prefer a versioned
`STORE.json` fence and additive events.

**Flag-on dogfood gap.** After E2, flag-on agents pay the intake tax with no
way to claim. That is acceptable for a short window and is why E3 follows E2
immediately. Do not dogfood flag-on during E1-only (CLI-only, no binding).

**Dual attention (E3–E5).** You will get both a success dot and a GoalVerify
for the same outcome. The design already wants that as a cutover step. Keep it
calendar-short.

**Integration at E3.** Binding roles (`can_claim`) need launch structure from
E2. If E2's path-matrix missed a path, E3 will find it. That is a **task on
E2's bead or a small E2.1 tale**, not a reason to merge E2 and E3.

---

## 9. Recommended solution

Implement Goals as a **program of four `xlarge` sibling epics plus a `large`
cutover epic**, with two small prerequisite tales:

1. **T0.** Write `parent_agent_name` into child metadata. Make `JumpToAgent`
   use `reveal_agent_navigation_target`. Each is a tale (or the first phase of
   E2 / E4).
2. **E1 goals-ledger.** sase-core events + markers + hot projection + `sase
   goal` CLI + `goal:` kind + `goals` beta flag. Land on reducer tests, two-clone
   rebase, and a recorded `list` budget. No launch changes, no TUI, no PyPI wait.
3. **E2 goals-binding.** Host binds every LLM turn; drafts are named or adopted;
   `/sase_goal`; plan `goal_id`. Land on a **frozen** launch-path table. Swarm of
   five → one goal.
4. **E3 goals-claims.** Required `builtin@goal`, evidence, one `GoalVerify` gate
   per claim, projected relations, prompt publication on name. Success pings
   remain. Land on eligibility + evidence + idempotent gates.
5. **E4 goals-surfaces.** Top-level Goals tab and Agents enrichers. Land on
   scoped visual goldens and jump tests. Flag still off-by-default.
6. **E5 goals-cutover.** Answer ack, Idle notices, silence `done` pings, then a
   **human** flag removal after soak. Land on send-path tests; the soak is not an
   agent phase.

Track the program here and with `sase bead dep` between the five beads. Do not
wrap them in a parent epic that can `%auto`-plan a sixth. Freeze each plan's
DoD so a land agent cannot promote the rest of the design into leftovers.

A **single epic covering the whole design** will not verify: it mixes six
verification worlds, matches the remainder/child-epic pattern already visible
in E4 receipts, deck cutover, and `sase-11e`, and asks a land agent to certify
a performance contract, a TUI chrome change, a required finalizer, and an
attention sunset together.

A **single epic covering only E1+E2** is a reasonable "start here" if you want
one approval this week. Treat claims, the tab, and the cutover as the next
three epics the moment that MVP lands — not as landing leftovers of the first.
