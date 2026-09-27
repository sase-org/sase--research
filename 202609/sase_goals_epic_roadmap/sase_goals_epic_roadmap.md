# SASE Goals: six verifiable epics, not one

_Lead synthesis · 2026-09-27 · project: sase · sase `2d8f2f0566`, sase-core `f1ddeb5`_

**Sources.** Five independent reports, all read through `sase artifact read`:
[cdx](sase_goals_epic_roadmap__cdx.md), [cld](sase_goals_epic_roadmap__cld.md),
[grk](sase_goals_epic_roadmap__grk.md), [mus](sase_goals_epic_roadmap__mus.md), and
[gem](sase_goals_epic_roadmap__gem.md). Each one takes the design,
[sase_goals_design](../sase_goals_design/sase_goals_design.md), as the destination and
asks only how to deliver it.

I also checked the contested points myself:

- **Epic statistics.** I recomputed epic size against outcome from the bead store: 335
  root epics created since 2026-08-01.
- **The land-agent prompt.** I read it, along with how it gets launched.
- **Code at HEAD.** I verified every code seam that the recommendation depends on.

§3 lists where individual reports were wrong or out of date.

---

## 0. Bottom line

**Don't build this as one epic.** All five reports agree, and the project's own history
backs them up:

- **It is large.** The design comes to about **35 phases** across **five released
  contracts**: the ledger wire, the launch/scan wire, the finalizer context wire, a new
  gate kind, and the TUI.
- **Large epics go wrong here.** Root epics with more than 7 phases are 2–3× as likely to
  spawn remediation child epics, and they take 3–10× longer to close (§1.1).
- **The land agent makes it worse.** It runs with `%auto` and is told to *plan any
  unfinished work as a child epic*. A single Goals epic would be audited against the
  whole design, so every unmet item would turn into a nested "finish it" epic. That is
  exactly the hard-to-verify outcome you're worried about.

**Recommendation: six epics plus one small bug task.** Each epic has:

- at most 7 phases, mostly medium;
- one released contract;
- one verification world;
- a short "check it" list you can run in minutes.

| # | Unit | ≈ phases | Verification world | What you can check yourself when it lands |
| --- | --- | --- | --- | --- |
| **pre** | Bug task: `JumpToAgent` reveals collapsed rows | — | one TUI test | A `done` notification for an agent in a collapsed group opens and selects that row |
| **G1** | Goal ledger, manual `sase goal` CLI, `goal:` artifact | 6 | Rust unit tests, two-clone fixtures, benchmark | A goal created on athena shows up in `sase goal list` on apollo with "synced Ns ago". `list` stays under 50 ms with 100k settled goals. |
| **G2** | Deterministic binding: explicit, inherited, plan-derived | 6 | launch-path matrix | Approve an epic plan. The plan and every phase and land agent carry the same `goal_id`, and `sase goal show` lists them. |
| **G3** | Claims and verification: `builtin@goal` + `GoalVerify` | 7 | finalizer protocol + gate end-to-end tests | An epic's land produces exactly **one** GoalVerify gate with a claim, check-it steps, and `@commit` evidence. Reject from Telegram relaunches onto the goal. |
| **G4** | Every agent has a goal: drafts, naming, adoption, answer acknowledgement | 6 | matrix + model-judgment metrics | A question produces one self-named goal and one claim, and opening the answer acknowledges it. A 5-agent swarm makes one goal. `sase goal audit` reports 0 unbound turns. |
| **G5** | Goals tab + Agents-tab integration | 6 | goldens + TUI performance budgets | The tab badge equals the Review count. Pressing a chip number jumps to a collapsed agent. `v` verifies. |
| **G6** | Attention cutover | 4 | notification truth table + before/after volume report | Successful runs stop pinging; claims still ping. |

```text
pre ─► G1 ledger ─► G2 binding ─► G3 claims ─┬─► G4 drafts ─┐
                                             └─► G5 tab ────┴─► soak ≥7d, metric-gated ─► G6 cutover
```

**Where this departs from the design's P0–P4 table.** That table is a good dependency
sketch, but it doesn't partition the work into epics:

1. **P0 is not an epic.**
   - The jump fix is a small bug task.
   - The parent-lineage write turns out not to be needed for Goals (§3).
   - The prompt-publication trigger belongs where naming happens, in G4.
2. **P1 is split three ways:** the ledger (G1), deterministic binding (G2), and drafts
   (G4). On its own, P1 is about 14 phases by cld's count.
3. **Claims ship before drafts.** Claims are proven on goals whose identity isn't in
   question (epics and explicit `%goal`) before universal draft naming adds a second
   model-judgment risk. That puts the payoff first on the noisiest work shape: 841 of the
   2,048 runs last week were epic-bound.

---

## 1. Why not one epic

### 1.1 What this project's epics show

These are root epics created 2026-08-01 to 2026-09-21, recomputed by me from the bead
store:

| Phases | Root epics | Spawned a child epic | Median hours to close |
| --- | --- | --- | --- |
| 1–3 | 55 | 16% | 3.9 |
| 4–5 | 98 | 20% | 4.8 |
| 6–7 | 66 | 23% | 4.8 |
| 8–9 | 33 | 27% | 15.5 |
| 10–11 | 10 | 50% | 30.1 |
| 12+ | 12 | 58% | 48.2 |

cld counted independently from the event streams and got the same shape (22 → 29 → 45 →
58%), and also found relaunch rates rising from 29% (6–7 phases) to 67% (12+).

**Phase count alone isn't the danger.** Mechanical sweeps close fine at any size;
`sase-3a` had 88 phases and closed in about 20 h. The chains come from **contract-crossing
work with live, multi-machine acceptance**:

| Epic | What happened (verified) |
| --- | --- |
| `sase-xe` | Started with 15 phases, grew to **82 phases** and 11 child plans, 6 levels deep, over 20 days |
| `sase-zm` | 14 phases; superseded after 6 days without landing a phase |
| `sase-x7` | Started with 15 phases, now 33 phases and 4 child plans, still open after 21 days |

Goals has that profile: five contracts, plus a cross-machine requirement (R8).

**The converse lesson matters just as much.** `sase-1ah` (E4 receipts) has only 7 phases
and is still open with a remainder child. Its definition of done required a published
wheel and a live athena demo. So the rule has two halves: **cap the phase count, and keep
calendar waits out of every definition of done.**

**The positive precedent is the `sase tool` program.** It split one feature into sibling
epics under the rule "one epic, one released contract, one acceptance surface":

| Epic | Phases | Time to close |
| --- | --- | --- |
| `sase-135` | 7 | 38 h |
| `sase-16h` | 6 | 7 h |
| `sase-17p` | 6 | 7.6 h |
| `sase-18j` | 9 | 27 h, plus one child. This is the epic that broke the ≤7 rule. |

### 1.2 The land agent turns leftovers into child epics

I checked this in code:

- `bd/land_epic` (`src/sase/default_config.yml`) says: "Unresolved issues caused by this
  epic remain epic work: plan and finish them before closing." It also says: "If steps
  1-2 uncover remaining work, use your /sase_plan skill…".
- `bead/work_prompt.py` appends `%auto` to every land agent.

A single Goals epic's land audit would be judged against all 12 of the design's
acceptance tests, which cover storage, launch, finalizer, gates, TUI, and attention. Any
gap would become an auto-approved child epic. That is how `sase-11e` nested four rounds
deep in a single day (grk).

**Landing is also the current bottleneck.** 65 of 98 in-progress epics have every phase
closed but are still waiting to land (verified). So the goal is the *smallest* split that
isolates the verification worlds, not the largest one.

### 1.3 Six verification worlds that one epic would tangle together

| Hazard | Why it's hard to verify | Owner | Instrument that makes it checkable |
| --- | --- | --- | --- |
| **Launch-path combinatorics.** About 14 paths: direct, plan, bead, swarm, `%alt`, `%repeat`, session, child, retry, dispatch, gate, pipe, question, monitor. | A binding bug shows up days later as a wrong or missing goal | G2 (deterministic paths), G4 (draft paths) | A frozen launch-path matrix, plus `sase goal audit` (unbound-turn report) |
| **Model judgment:** honest claims; name vs. adopt | Non-deterministic, so no single test can prove it | G3 (claims), G4 (naming) | `sase goal stats` measured over a soak: precision per model, adopt:name ratio, merge rate |
| **Multi-machine convergence** | The top driver of deep remediation chains | G1 only | Deterministic two-clone fixtures. The athena↔apollo smoke check is a check-it step, not a landing blocker. |
| **Pixel-level TUI** | Golden churn: sase has about 815 golden PNGs | G5 only | Rule: **G1–G4 cause zero golden churn** |
| **Attention semantics:** did silencing successes lose anything? | Can only be judged against real traffic | G6, gated on G3/G4 data | Shadow coverage while success pings are still loud |
| **Every-turn blast radius:** a required finalizer runs on every turn | One bug fails every agent | G3 | `builtin@goal` fails open to `keep_open`; its trigger is "goal is bound" |

---

## 2. What makes a good epic boundary here

These rules are merged from cdx, cld, and grk. Every epic below satisfies all of them:

1. **One primary invariant and one verification world.** Examples: core unit tests, a
   launch matrix, finalizer/gate tests, goldens, or an observational soak. Mixing worlds
   is how remainder children get created.
2. **A black-box endpoint.** The epic can be exercised without code from a later epic,
   and master is coherent and useful after it lands.
3. **At most 7 phases,** mostly medium and small, with at most two large. Data: §1.1.
   cld found that every xlarge phase, and 10% of large phases, escalated into a child
   epic.
4. **A frozen, numbered definition of done with no calendar waits.** Soaks, PyPI floors,
   and "the owner will click around" stay out of phases. Ratcheting the linked-checkout
   pin (`sase-core-revision.txt`) is enough.
5. **Rust core, binding, pin, Python caller, and tests land in the same epic.** Never
   split by repository. The repository boundary is not a verification boundary.
6. **Rollback is bounded.** Disabling one capability never corrupts another capability's
   data.

---

## 3. Where the reports disagreed, and how I resolved it

| Question | Positions | Resolution | Why |
| --- | --- | --- | --- |
| **How many units?** | cdx: 4 epics + a cutover tale. grk: 4 + a cutover epic + 2 tales. gem: 5 + 4 prep tasks. mus: 6. cld: 6 + 1 task. | **6 epics + 1 bug task** | This is the smallest count that keeps every epic at ≤7 phases (§1.1) *and* separates the two model-judgment risks. cld checked the merges; none stays ≤7 phases. |
| **Binding: one epic or two?** | cdx, grk, mus, gem: one epic including drafts. cld: deterministic binding (G2) and drafts (G4) as separate epics. | **Split** | One binding epic is about 12 phases by cld's itemized count. It would also mix a deterministic matrix with naming/adoption judgment that can only be measured over a soak. The existing `agent_tab` pattern keeps deterministic binding bounded (next row but one). |
| **Claims before drafts, or after?** | Four reports: drafts first. cld: claims first. | **Claims first** | (1) Epic-bound runs are about 41% of the weekly volume, so the noisiest shape pays off first. (2) Claim honesty gets measured on goals whose identity isn't in doubt. (3) It avoids grk's own "intake tax with nothing to claim" gap. (4) From G3 on, you verify G4–G6 *through GoalVerify gates*. **Cost:** the universal "every turn has a goal" invariant arrives one epic later. |
| **Finalizer and gate: one epic or two?** | mus splits them; the other four keep them together | **Together** | A claim with no decision path isn't independently verifiable. A gate with no producer can only be tested synthetically. The two form one transactional review loop (cdx). |
| **Feature flags** | grk, gem, mus: one `goals` flag spanning every epic. cdx, cld: per-epic flags. | **At most one beta flag per epic, removed before that epic lands** | The `sase_flags` memory says an agent creates a beta flag only for an epic plan, as scaffolding that *the epic removes before it lands*. An umbrella flag is allowed only if **you** ask for it (precedents: `typed_launch_units`, `provider_drain`). The price is both-state tests in six epics and removal becoming a seventh unit of work. gem's "create the flag now as a prep task" breaks the rule outright. |
| **Is persisting parent lineage a prerequisite?** | grk, gem, mus: yes. cld: no. | **Not a Goals prerequisite** | Verified: `xprompt/_tab_inheritance.py` stamps `%tab:<name>` into child prompt segments at LaunchApproval, `bead work`, and dispatch. `agent_tab` survives re-exec (`axe/run_agent_directive_metadata.py`), and monitor members inherit it through `_MONITOR_INHERITED_METADATA_FIELDS`. `%goal` can reuse the same mechanism. The missing `parent_agent_name` writer is real, but it's an Agents-ancestry bug, not a Goals blocker. |
| **Other prep tasks** | gem: `%goal` directive and the flag as prep tasks | **Rejected** | A directive with nothing to bind to belongs in G2. The flag conflicts with the flag rules. |
| **Where do the four new relations land?** | cld: all four in G1. grk: E3. cdx: the UI epic. mus: the tab epic. | **With the epic that produces the fact each one projects:** `pursues` and `defines` in G2, `evidences` in G3, `follows` in G4 | Each is testable through the CLI when it lands. The registry already has projection-sourced relations (`produced-by`, `launched-by`, `awaits`), and adding a relation is additive, not breaking. Only the *event* vocabulary needs freezing up front, because the ledger is immutable. |
| **Answer acknowledgement** | cld: G4. mus: the gate epic. cdx, grk, gem: the cutover. | **G4** | Answer-only claims first appear in G4. Without ack, G4 would create about 25 explicit-verify chores a day during the soak. |
| **Where the soak goes** | gem: a 7-day soak *inside* E5. grk: a human-gated flag-removal phase. cld: a metric-based start gate before G6. | **cld:** soak between G4/G5 and G6, measured on shadow data while success pings are still loud. Never an agent phase. | `sase-1ah`'s remainder stalled on waits inside `sase bead work`. |
| **Is the cutover a tale?** | cdx: probably | **A small epic** (4 phases). It can be a medium tale only if trimmed to "silence + migrate unread". | `sase_sizes`: tales are single-agent and at most `medium`. |
| **TUI timing** | cdx, grk, gem, mus: strictly after claims. cld: parallel with drafts. | **Parallel with G4,** once G3's claim payload is frozen | The card's core is *You asked → Claim → Check it → Evidence*, so designing it before real claims exist is mechanism before corpus. G4 and G5 touch disjoint code. |
| **Human status verbs in G1** | cld includes `verify`; cdx: `new`/`edit`/`drop`/`reopen`/`merge` | **cdx** | `verify` and `reject` settle a *claim*, so they belong in G3. |
| **Parent (umbrella) epic** | grk: none | **None.** Use sibling beads linked with `sase bead dep`, tracked by this note. | A parent's `%auto` land agent can plan more children. |

**Corrections to researcher claims:**

- **cld:** "the FINAL deck is behind `ace_final_deck`" is out of date. HEAD `2d8f2f0566`
  removed that flag, so the FINAL deck is always on. G5's Goal enricher no longer waits
  on a flag, though it should still coordinate with `sase-1b2` (19/20 phases closed) and
  `sase-1b1`.
- **gem:**
  - The "≤5 phases per `sase_sizes.md`" cap has no source; that memory says nothing about
    phase counts.
  - The `sase-19i` "depth 7" claim is unverified.
  - Binding belongs in `build_agent_meta`, where `agent_tab` is applied, rather than in
    `run_agent_runner.py`.
- **mus:** Deferring all of the design's open questions to the last epic won't work. Each
  one blocks an earlier epic, so decide each just before the epic that needs it (§7,
  following cdx).
- **grk:**
  - Labeling E1–E4 as `xlarge` is fine as sizing for the bead that authors the plan.
  - But its single `goals` flag spans five epics (see the flags row above).

---

## 4. The program, epic by epic

### Pre-task: `JumpToAgent` reveals collapsed rows (bug, small)

- **The bug (verified):** `handle_jump_to_agent`
  (`ace/tui/actions/agents/_notification_handlers.py`) linearly scans `app._agents`, sets
  `current_idx`, and never calls `reveal_agent_navigation_target`. No bead exists for it
  yet.
- **Why do it first:** it improves today's notifications, and every later goal → agent
  jump reuses this path.
- **How to file it:** `/sase_new_task`, type `bug`, size `small`.

### G1: Goal ledger, manual CLI, and the `goal:` artifact

**Outcome:** goals are durable, conflict-free, cross-machine records. You can create,
list, show, edit, drop, reopen, merge, and cite them by hand, and they stay fast no
matter how much history piles up.

| # | Phase | Size |
| --- | --- | --- |
| 1 | `core-contract`: ids, the `STORE.json` fence, the **full** event vocabulary and status machine (including `claimed`, `claim_retracted`, `adopted`, and `merged`, which later epics produce), the reducer, and basis validation | large |
| 2 | `ledger-io`: `live/` markers, `items/<id>/events/`, the machine-local `goals-hot.json` projection, `doctor --repair` | medium |
| 3 | `sidecar-sync`: a `goals` role co-hosted in the beads repo; hidden-clone writes; bounded fetch → rebase → revalidate → push; outbox plus `↑ unpublished`; sync watermark; local-only mode; a push-retry counter | medium |
| 4 | `cli`: `new` / `list` / `show` / `edit` / `drop` / `reopen` / `merge` / `doctor`; human verbs refused inside agent runs; Rust fast path; `--json` | medium |
| 5 | `artifact-kind`: `goal:` in the compiled kind catalog; `sase artifact read goal:<id>` renders the card; `@goal:<id>` cites it | medium |
| 6 | `acceptance`: two-clone concurrency and marker-race fixtures; crash-between-event-and-marker repair; 100k-settled benchmark with file-open tracing; unsupported schema versions fail closed | medium |

- **Out of scope:** binding, drafts, finalizer, gates, TUI, relations.
- **Owns design acceptance tests:** 8, 9 (the CLI half), and 12.
- **Check it:**
  1. `sase goal new` on athena, then `sase goal list` on apollo within the TTL shows it.
  2. `time sase goal list` is under 50 ms.
  3. `sase goal drop <id>` removes it from the list.
  4. A prompt citing `@goal:<id>` expands to the card.
- **Decide before planning:** ledger visibility (the beads repo is public) and
  co-hosting.
- **Coordinate with:** `sase-x7` (canonical shared formats).

### G2: Deterministic binding (explicit, inherited, plan-derived)

**Outcome:** whenever the host already *knows* the goal, it binds it before the provider
starts, on every launch path, and the agent sees one line naming it. There are no drafts
and no model judgment yet.

| # | Phase | Size |
| --- | --- | --- |
| 1 | `core-resolver`: a pure `resolve_goal_binding` (explicit → session → plan → clan → parent → bead) with a **reserved `draft` variant**; scan-wire `goal_id` | medium |
| 2 | `directive`: `%goal:<id>` / `%goal:new`, completion, `goal_id` and its source in `agent_meta.json`, `SASE_GOAL_ID`, refusal to bind a settled goal | medium |
| 3 | `inheritance`: generalize `_tab_inheritance` into shared directive inheritance; add `goal_id` to the session-successor copy, retry spawn, re-exec allowlist, monitor/gate inherited fields, LaunchApproval, `bead work`, and dispatch | medium |
| 4 | `plan-goals`: `sase plan propose` creates or refines the goal and stamps `goal_id`; epic phase and land agents resolve it through epic → plan; PlanApproval outcomes; origin digest recorded | medium |
| 5 | `bound-line`: the ~40-token `SASE GOAL ⌖id — …` line; `pursues` and `defines` relation projections; `show` lists contributors | small |
| 6 | `audit-and-matrix`: `sase goal audit --since` and the frozen launch-path table as the acceptance suite | medium |

- **Resolve in the runner** (`build_agent_meta`), not only on `AgentUnitWire`.
  `typed_launch_units` is still a beta flag, so a wire-only field would miss the untyped
  path (cld).
- **Out of scope:** drafts, clan-*shared draft* naming, routine standing goals, claims.
- **Owns design acceptance tests:** 2 (deterministic rows) and 5 (the unit digest).
- **Check it:**
  1. Launch a `%goal:<id>` agent that `/sase_run`s a child and pipes to a successor.
     `sase goal show` lists all three.
  2. Approve a small epic. Every phase and land agent carries the plan's `goal_id`.
  3. `%goal:<settled>` is refused.
- **Useful on its own:** `sase goal list` becomes the inventory of every approved epic in
  flight.
- **Wait for:** `sase-1bc`, which has 7 phases still in progress and owns the `%tab`
  inheritance and directive seams. Land it first, then generalize its helper.

### G3: Claims and verification

**Outcome:** an agent on a bound goal ends each turn with `keep_open` or `claim`. A claim
moves the goal to Review and opens exactly one `GoalVerify` gate. You verify, reject
(optionally relaunching with your feedback), or drop it from the TUI inbox, the CLI,
mobile, or Telegram. **Today's success pings stay on.**

| # | Phase | Size |
| --- | --- | --- |
| 1 | `core-policy`: `decide_goal_action`; roles derived from launch structure plus liveness; evidence rules per claim shape; `assigned_goal` on the finalizer context (**breaking**, because the wire is `deny_unknown_fields`); a **reserved `name` field** for G4 | large |
| 2 | `provider`: `builtin@goal` across the hard-coded builtin sites (cld counts about 12 Python modules) plus the Rust `FIRST_PARTY_PROVIDERS`; `after: [commit]`; trigger is "goal bound"; **refusal or error falls open to `keep_open` plus a diagnostic, never a failed turn**; declaration-recovery turn; predeclared decision for prepared monitors | large |
| 3 | `evidence`: host-gathered candidates, symbolic `@commit`, embedded receipt snapshots, provenance checks, strength badge; the `evidences` relation | medium |
| 4 | `gate`: `GoalVerify` as a generic-form gate kind (verify / reject + relaunch / drop), idempotent on `goal:<id>:claim:<n>`, Remote Attention dedupe; `sase goal verify` / `reject`; `JumpToGoal` opens the `goal:` card until G5 retargets it | medium |
| 5 | `lifecycle-and-stats`: a follow-up during Review retracts the claim; stale-basis handling; concurrency rules; `sase goal stats`; **shadow coverage** | medium |
| 6 | `skills`: the `sase_final` paragraph; `/sase_goal` list/show | small |
| 7 | `acceptance`: end-to-end epic claims; phase agents can't claim; a claim is refused while a contributor is live; one gate across retries and machines; dismissing a row never settles it | medium |

- **Owns design acceptance tests:** 4, 6, and 7.
- **Check it:**
  1. Land a small epic. You get **one** GoalVerify with a claim sentence, check-it steps,
     `@commit`, and a receipt snapshot. Phase agents record `keep_open`.
  2. Reject it from Telegram. A relaunched agent joins the same goal.
  3. Kill a phase agent. No claim appears.
- **Notification load:** about **+15%** until G6, at one claim per roughly 6.6 turns.
- **Before planning, close `sase-rr`** ("Retire the pluggable finalizers beta and legacy
  controller"). All 5 of its phases are closed, but it's still in progress, which leaves
  finalizer ownership ambiguous.
- **Coordinate with:** `sase-1ah` (the receipt contract claims will embed), `sase-zq`,
  `sase-11t`, and `sase-117`.

### G4: Every agent has a goal (drafts, naming, adoption, answer acknowledgement)

**Outcome:** any LLM turn the host can't bind gets a machine-local draft. The agent's
first act is to name it or adopt an active goal. Swarms share one draft, and questions
settle when you open the answer.

| # | Phase | Size |
| --- | --- | --- |
| 1 | `core-drafts`: the draft rung; a machine-local draft store; compare-and-swap `name`; `adopt` (which retracts a Review claim); drafts are never published until named | medium |
| 2 | `launch-drafts`: a draft is created before spawn; clan-shared drafts; a follow-up after Done becomes a new draft linked by `follows`; routine **standing goals**; mechanical members inherit | medium |
| 3 | `intake`: the ~80-token intake block; `name` / `adopt` limited to the agent's own draft; `/sase_goal` naming guidance | medium |
| 4 | `finalizer-drafts`: a draft-bound payload must include `name`; auto-naming with a badge when a run dies unnamed; **naming publishes the creator's prompt** | medium |
| 5 | `answer-ack`: `@reply` snapshot evidence; opening the answer settles it `done · acknowledged`, with undo; the `goals.answer_claims` config | medium |
| 6 | `acceptance-and-instruments`: `audit` reports 0 orphans; a 5-agent swarm gives 1 goal and 1 claim; an adopted draft never appears in the shared ledger; adopt:name and merges per 100 goals added to `stats` | medium |

- **Owns design acceptance tests:** 1, 2 (draft rows), 3, 5 (swarm root), and 11.
- **Overflow rule:** if planning exceeds 7 phases, move standing goals to G6.
- **Check it:**
  1. Ask a question. It produces one self-named goal and a claim, and opening the answer
     acknowledges it.
  2. A 5-agent research clan produces one goal.
  3. Re-asking something already in flight makes the agent adopt the existing goal,
     with its reason shown.
  4. `sase goal audit --since 24h` reports 0.

### G5: Goals tab and Agents-tab integration

**Outcome:** Goals become the daily loop: one keystroke, one badge, and numbered jumps in
both directions.

| # | Phase | Size |
| --- | --- | --- |
| 1 | `read-model`: a cached snapshot with change tokens and off-thread refresh | medium |
| 2 | `tab`: `TAB_ORDER` gains `goals`; Review / Running / Idle lanes plus collapsed Standing and Done today; contributor pips; `synced Ns ago`; badge | large |
| 3 | `card`: *You asked → Outcome → Claim → Check it → Evidence → Gaps → Agents → Timeline*; relation-rail chips; agent jumps through the reveal path with an archived-agent fallback; `JumpToGoal` retargeted to the tab | large |
| 4 | `keys`: `v r x l e m a p n / P h`, registered in `default_config.yml` | medium |
| 5 | `agents-integration`: identity-header chip; FINAL-deck Goal enricher; *by goal* grouping in the `o` ladder | medium |
| 6 | `goldens-and-budgets`: scoped visual snapshots; projection refresh < 2 ms at n = 100; highlight → paint ≤ 16 ms | medium |

- **This is the only epic with golden churn.** The Artifacts-tab scaffold re-blessed 179
  PNGs (cld).
- **Owns design acceptance tests:** 9 (the TUI half) and 10.
- **Coordinate with:** `sase-1bc` (the `o`/`O` ladder), `sase-1b1` and `sase-1b2` (decks),
  and the TUI performance epics.

### G6: Attention cutover

**Start gate.** Write the G6 plan only once all of these hold. The thresholds are
proposals for you to confirm:

| Measure | Proposed threshold |
| --- | --- |
| Time and volume since G4 landed | ≥ 7 days **and** ≥ 100 settled claims |
| Shadow coverage | ≥ 90% of success pings belong to a goal that reached a claim, or went Idle, within 1 h of its last contributor finishing |
| Claim precision: (verify + ack) ÷ (verify + ack + reject) | ≥ 80%, reported per model |
| Merges per 100 goals | ≤ 5 |
| Unbound LLM turns (`audit`) | 0 |
| Turns failed by `builtin@goal` | 0 |

| # | Phase | Size |
| --- | --- | --- |
| 1 | `silence-successes`: `JumpToAgent(done)` goes quiet (one send site, `run_agent_runner_finalize.py:469`); claims keep the chime | medium |
| 2 | `retire-unread`: remove the ✅ success unread projection and migrate unread success rows; ❌ stays | medium |
| 3 | `idle-and-hygiene`: quiet Idle notices with the last progress note, aging, `goals.idle_nudge_days`, and an optional stale-review lapse flavor | medium |
| 4 | `unflag-and-measure`: flag removed, docs, before/after notification-volume report, startup-tab decision | small |

If you want loud success pings to stay available *permanently*, that's a config field,
not a flag.

---

## 5. Cross-epic rules to put in every plan

1. **Freeze contract vocabulary early.**
   - G1 defines every event kind and the status machine.
   - G2 reserves the `draft` binding variant.
   - G3 reserves the `name` payload field.
   - Later epics add producers, not breaking schema changes.
2. **A goal problem never fails an agent turn.** Binding failures leave the turn unbound,
   and finalizer errors become `keep_open` with a diagnostic that `sase goal audit`
   surfaces.
3. **Zero golden churn outside G5.**
4. **A frozen, numbered definition of done, with the successor epics named as out of
   scope** in the land section. This is what stops the `%auto` land agent from planning
   later epics as child epics.
5. **Put the source pin in the definition of done, never a PyPI floor.** Moving
   `sase-core-revision.txt` is enough; raising the floor is a follow-up task.
6. **`just check` only.** `check-full` runs only when explicitly requested
   (`check-full-is-explicit`).
7. **Acceptance never depends on a green master.**
8. **Each successor opens with a contract test** against its predecessor's frozen shape
   (mus).
9. **Plan one epic at a time.** Write only G1 now, naming G2–G6 as successors. Revise
   the later plans from what each predecessor measures, especially push-retry contention
   and list latency.
10. **No parent epic.** Link sibling beads with `sase bead dep`.
11. **After every landing, rerun one small program-level integration matrix** (from
    cdx):

| Scenario | After G2 | After G3 | After G4 | After G5 | After G6 |
| --- | --- | --- | --- | --- | --- |
| plan → epic → land | one goal, all agents bound | land-only claim, one gate | — | plan/evidence chips | approval + one claim, no success pings |
| `%goal` parent → child → pipe | shared goal | owner claims once | — | contributor jumps | one claim signal |
| direct question | unbound (fail-open) | no claim | draft → named → ack | answer card | one acknowledgement |
| 5-agent research swarm | unbound | — | one goal, lead-only claim | contributor pips | one claim signal |
| monitor success / failure | inherited | claim / keep_open | — | receipt visible | claim / error only |
| two-machine race | — | one winning claim and gate | — | freshness visible | no duplicate signal |

---

## 6. Alternatives considered

| Option | Verdict |
| --- | --- |
| **One epic** | **Reject.** It would be about 35 phases, in the 58%-child-epic bucket, with the `sase-xe` profile, and a `%auto` land agent auditing 12 cross-world tests. |
| **The design's P0–P4 as five epics** | **Reject as written.** P0 is a grab bag, and P1 alone is about 14 phases. |
| **Four epics + cutover** (the cdx/grk/gem shape: ledger, binding including drafts, claims + gate, tab, cutover) | **The close runner-up.** Choose it if you want the universal invariant before claims. The cost: a 10–12-phase binding epic, and both model-judgment risks land in the first user-visible release. |
| **Finalizer and gate as separate epics** (mus) | **Reject.** Neither half is verifiable end to end on its own. |
| **Fewer approvals: merge G1 + G2** | **The only acceptable merge** (grk's MVP). It's about 12 phases, but both halves are deterministic, with no model judgment and no TUI. Expect one remediation child. Never merge G4 with G5, G5 with G6, or G3 with anything. |
| **Claims without goals** (a per-agent flag) | **Reject.** It's throwaway work, and G3-on-epics gives the same early signal. |

---

## 7. Decisions you need to make, and which epic each one blocks

| Decision | Blocks | Recommendation |
| --- | --- | --- |
| Ledger visibility (the beads repo is public) and co-hosting | G1 | Co-host; accept bead-level publicity; offer a `local` visibility option |
| Umbrella flag vs. per-epic flags | G1 | Per-epic, unless you explicitly want one dark-launched program flag |
| Cross-project work: the goal lives in the launching project | G2 | Accept |
| Stale-review lapse flavor | G3 (state) / G6 (nudges) | Yes, never an auto-verify |
| Routines: standing goals or exemption | G4 | Standing goals, or move them to G6 if G4 overflows |
| Answer acknowledgement default | G4 | Ack on open, with undo |
| Tab position, direct key, startup tab | G5 / G6 | Second position; decide the startup tab after the soak |
| G6 soak thresholds | G6 | The table in §4 |

---

## 8. Risks, and what would change this plan

| Risk | Signal | Response |
| --- | --- | --- |
| A launch path can't be bound in the runner | G2 matrix fails for a structural reason | Bind that path on `AgentUnitWire` inside G2. It's still one contract, so no new epic. |
| Low claim precision on some models | Precision < 60% in `stats` | Apply a per-model claim policy (force `keep_open`, or mark claims `unreviewed`) before G4 widens exposure. Don't start G6. |
| Push contention in the beads repo | The G1 push-retry counter rises, or claims queue in the outbox | Split the `goals` role into its own repo. That's a config change, not an epic. |
| Shadow coverage stays below 90% | G6's gate never opens | Fix Idle detection or role derivation in a small follow-up. Goals still work without G6; they're just noisier. |
| An epic plans at more than 7 phases | The planner's phase list | Push the overflow to a successor; don't widen the epic. |
| `sase-1bc` or `sase-rr` doesn't land | G2 or G3 can't start cleanly | Close `sase-rr` deliberately (its phases are done). For `sase-1bc`, coordinate on the helper seam rather than waiting indefinitely. |

**Timeline.** Recent comparable epics closed in 7–38 h, and the median root epic of ≤7
phases closes in about 5 h. So G1–G5 plausibly take one to two weeks, and the program
takes **roughly 2½–4 weeks including the ≥7-day soak**. Splitting costs little calendar
time.

---

## 9. Recommended solution

**Build Goals as six sequential sibling epics plus one small bug task, not one epic.**
Each epic has at most 7 mostly-medium phases, one released contract, one verification
world, a frozen numbered definition of done with no calendar waits, and a check-it list
you can run in minutes.

1. **Pre-task.** `JumpToAgent` reveals collapsed rows (small `bug` task).
2. **G1: Goal ledger, manual CLI, `goal:` artifact** (6 phases).
   - A conflict-free event ledger plus `live/` markers, co-hosted in the beads repo and
     written through the hidden clone.
   - Manual `sase goal` verbs.
   - The **full event vocabulary frozen here**.
   - Verified by two-clone fixtures, a 100k-settled latency benchmark with file-open
     tracing, and an athena → apollo `list` check.
3. **G2: Deterministic binding** (6 phases).
   - `%goal`, plan-derived goals, and inheritance across every launch path, built by
     **generalizing the existing `%tab` inheritance** and resolved in the runner.
   - No drafts.
   - Verified by the frozen launch-path matrix and `sase goal audit`.
4. **G3: Claims and verification** (7 phases).
   - A **fail-open** `builtin@goal` after commit, with host-gathered, provenance-checked
     evidence.
   - One generic-form `GoalVerify` gate per claim.
   - Human `verify` / `reject` / `drop`, plus `sase goal stats` and shadow coverage.
   - Success pings stay on.
   - Verified on real epic landings. From here on, **you verify the remaining Goals epics
     through the feature itself.**
5. **G4: Drafts, naming, adoption, answer acknowledgement** (6 phases), **in parallel
   with G5: the Goals tab and Agents integration** (6 phases).
   - G4 is verified by 0 orphans and one goal per swarm.
   - G5 is verified by the badge, lanes, card, jumps, and the performance budgets.
   - G5 is the only epic with golden churn.
6. **Soak for at least 7 days.** Then **G6: Attention cutover** (4 phases), once shadow
   coverage, claim precision, merge rate, orphans, and zero finalizer failures clear the
   §4 thresholds. It silences success pings, retires ✅ unread, and adds Idle hygiene.
   Verified by a before/after notification-volume report.

**Program rules:**

- **Flags.** Each epic owns at most one beta scaffolding flag and removes it before it
  lands. There is no umbrella flag unless you ask for one.
- **Structure.** No parent epic; link the siblings with `sase bead dep`.
- **Land sections.** Each epic's land section names its successors as out of scope.
- **Checks.** Source pin, not PyPI; `just check` only.

**First moves, in order:**

1. Record the "the host binds, agents claim, users settle" invariants as a decision
   record (via `/sase_memory_write`), so that six plans cite it instead of re-arguing it.
2. File the JumpToAgent bug task.
3. Close `sase-rr`.
4. Settle the two G1 questions: visibility, and flag strategy.
5. Write **only the G1 plan**, naming G2–G6 as successors.
