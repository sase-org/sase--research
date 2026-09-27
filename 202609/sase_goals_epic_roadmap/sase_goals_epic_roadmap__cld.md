# Splitting SASE Goals into distinct, verifiable epics

_Researcher cld · 2026-09-27 · project: sase · sase `c8a7a5ed3c`, sase-core pin
`0e8981a1`, local bead store on athena_

**Input.** The lead design, `research:202609/sase_goals_design/sase_goals_design.md`
(read with `sase artifact read`). Everything that design says about behavior is taken as
the destination here. This report only asks how to deliver it.

**My own evidence:**
- **Bead history:** 893 epic-tier beads. Phase counts, relaunch counts, child-epic chains
  and time to close, computed from `beads/events/streams/*.jsonl`.
- **The `sase tool` roadmap**, the only planned split of one feature into several epics
  (`research:202609/sase_tool_epic_roadmap/…`), and the overnight epic-stall study.
- **Code at HEAD:** 13 of the design's code claims checked in sase and sase-core.
- **In-flight epics** that touch the same code as Goals.

---

## 0. Bottom line

**This should not be one epic. It should be six, plus one small task beforehand.** The
destination is about **35 phases**. The bead store shows that SASE epics get
unreliable above about 7 phases:

| Phases per epic | Relaunched | Spawned a child epic |
| --- | --- | --- |
| 6–7 | 29% | 22% |
| 8–9 | 53% | 29% |
| 12 or more | 67% | 58% |

The feature epics this size that did go wrong were cross-cutting contract work with
live multi-machine acceptance:
- `sase-xe` (15 phases) grew to 82 phases over 20 days.
- `sase-zm` (14 phases) never landed a phase.
- `sase-x7` (15 phases) is 22 days in.

Goals has exactly that profile.

Six is also the **minimum** that gives every epic **at most 7 phases, one released
contract, and one acceptance surface**. The `sase tool` roadmap called that rule "one
epic, one released contract, one acceptance surface," and it has held up in practice:

| Epic | Phases | Time to close |
| --- | --- | --- |
| E1 | 7 | 38 h |
| E2 | 6 | 7.6 h |
| E3 | 9 | 27 h, plus a follow-up child — the one that broke the ≤7 rule |

**The recommended program:**

| # | Epic | Phases | What you can verify yourself when it lands |
| --- | --- | --- | --- |
| **pre** | Task: `JumpToAgent` opens collapsed rows | — | A notification jump lands on an agent inside a collapsed group |
| **G1** | Goal ledger, `sase goal` CLI, `goal:` artifact | 6 | `sase goal new` on athena shows up in `sase goal list` on apollo with "synced Ns ago"; `list` stays under 50 ms with 100k settled goals |
| **G2** | Deterministic binding: explicit, inherited, plan-derived | 6 | Every agent in an approved epic, and every child or successor of a `%goal:X` launch, has `goal_id = X`; `sase goal show X` lists them |
| **G3** | Claims and verification (`builtin@goal` + `GoalVerify`) | 7 | An epic's land agent produces exactly **one** `GoalVerify` gate with a claim, check-it steps, and `@commit` evidence; Reject from Telegram relaunches onto the goal |
| **G4** | Every agent has a goal: drafts, naming, adoption | 6 | A question gets one draft that the agent names, then one answer claim that opening it acknowledges; a 5-member swarm makes one goal; `sase goal audit` reports 0 unbound LLM turns |
| **G5** | Goals tab and Agents-tab integration | 6 | The Goals tab shows Review/Running/Idle with a Review-count badge; a numbered chip jumps to a collapsed agent; `v` verifies |
| **G6** | Attention cutover | 5 | Successful completions go quiet and claims are the loud signal; a before/after notification-volume report |

**Order:** G1 → G2 → G3 → {G4 ∥ G5} → **a soak of at least 7 days** → G6. The soak is
set by data, not by how quickly the epics finish.

**Where this differs from the design's own P0–P4 rollout:**
1. **Claims before drafts.** Claims (G3) ship on *deterministically* bound work — epics,
   explicit `%goal`, and their descendants — before universal draft naming (G4). This
   keeps the two model-judgment risks apart: "does the agent claim honestly?" and "does
   the agent name or adopt correctly?" Each gets its own epic and its own metrics. Epics
   are also where today's noise is worst: 841 of 2,048 agent runs last week were bound
   to an epic.
2. **The design's P1 is really two or three epics** (ledger + binding + drafts + skill +
   plan naming ≈ 14 phases), so it is split.
3. **The design's P0 is not an epic.**
   - The jump fix is a small task.
   - The prompt-publication trigger belongs in G4.
   - The parent-lineage prerequisite is largely unnecessary. The `%tab` lineage
     inheritance that landed today (`aff4fc082f`, sase-1bc.5) already solves "the child
     inherits from its parent" without writing `parent_agent_name`.
4. **The cutover (G6) is its own epic**, started only once shadow-coverage and
   claim-precision data from G3 and G4 pass the thresholds in §5.7.

---

## 1. Why not one epic

### 1.1 Size of the destination

This counts phases for the design's §4 scope. Sizes follow the project's recent mix of
69% medium, 22% small and 7.5% large phases.

| Area | Main pieces | Rust contracts touched | ≈ phases |
| --- | --- | --- | --- |
| Ledger and CLI | ids, events, reducer, live markers, hot projection, `goals` sidecar role, hidden-clone push/outbox, freshness, local-only mode, fast `list`, `goal:` kind | goal wire, artifact kind/relations | 6 |
| Deterministic binding | `%goal` directive, pure resolver, inheritance on 14 launch paths, plan `goal_id`, epic chain, scan-wire `goal_id`, bound-turn line | launch/scan wire | 6 |
| Claims and verification | `goal_action` policy, roles and liveness, evidence validation, `builtin@goal` wired through ~12 hard-coded builtin sites, `GoalVerify` gate, `JumpToGoal`, retraction, stats | finalizer context wire (breaking) | 7 |
| Drafts | draft rung, clan-shared draft, compare-and-swap naming, adopt, intake injection, `/sase_goal`, auto-name, publish-on-name, answer acknowledgement, routine standing goals | resolver extension | 6 |
| Surfaces | Goals tab, lanes, card, keys, Agents chip, FINAL Goal enricher, by-goal grouping, goldens, performance budgets | none, or the scan wire | 6 |
| Cutover | silence successes, retire ✅ unread, Idle notices, `follows` chains, hygiene, unflag | none | 4–5 |
| **Total** | | **5 released contracts** | **≈ 35** |

For scale, the code this touches is large:
- The `finalizers/` package alone is about 55 files and 17.5k lines, and `builtin@commit`
  is 17 files.
- sase has 815 golden PNGs.
- A new top-level tab re-blesses most of them. The Artifacts-tab scaffold `a62647069c`
  touched 221 files, 179 of them PNGs.

### 1.2 What the bead store says about epics this large

This covers 280 root epics created 2026-08-01 to 2026-09-21:

| Phases | N | Relaunched | Any child epic | Median duration | Mean `PROPOSED FOLLOW-UP` |
| --- | --- | --- | --- | --- | --- |
| 1–3 | 57 | 26% | 15% | 3.9 h | 4 |
| 4–5 | 100 | 26% | 21% | 4.8 h | 8 |
| 6–7 | 66 | 29% | 22% | 4.8 h | 10 |
| 8–9 | 34 | 53% | 29% | 10.9 h | 15 |
| 10–11 | 11 | 64% | 45% | 19.7 h | 18 |
| 12+ | 12 | 67% | 58% | 37.8 h | 28 |

**Phase count alone is not the danger:**
- **Mechanical sweeps close fine at any size:** `sase-3a` (88 phases, 19.7 h), `sase-2i`
  (34), `sase-2s` (20).
- **What goes wrong is contract-crossing feature work with live acceptance:** `sase-xe`,
  `sase-x7`, `sase-zm` and `sase-z4` (four generations of "finish and land" children).
  Goals crosses five contracts and is cross-machine by requirement (R8).
- **Phase size predicts escalation too.** Every xlarge phase (4 of 4) and 10% of large
  phases became child epics. Medium, small and xsmall phases never did. So each Goals
  epic should be made of medium and small phases, with at most one or two large ones.

A single Goals epic would be the riskiest shape this project has attempted. The honest
prediction is a `sase-xe`-style chain of nested "finish" epics that makes verification
*harder* — which is exactly your worry.

### 1.3 Why not more than six

Each extra seam adds a cross-epic contract handoff and another land step. Land steps
are SASE's current bottleneck:
- 65 of the 98 in-progress epics have every phase closed but the epic still open.
- `sase-kp` has sat that way since mid-August.

I looked for merges that stay at 7 phases or fewer, and none work:
- G1 + G2 is about 12 phases.
- G5 + G6 is about 11 phases, with different start gates.
- G3 + G4 is about 13 phases and merges the two model-judgment risks.

Going to eight, by splitting ledger sync or cutover hygiene out further, buys nothing
verifiable.

---

## 2. What makes Goals hard to verify, and how the split handles each part

Your worry is real, but the difficulty comes from six separate **verification hazards**
that one epic would tangle together. The split gives each hazard exactly one owner and
one instrument.

| # | Hazard | Why it's hard | Owner | Instrument that makes it checkable |
| --- | --- | --- | --- | --- |
| H1 | **Many launch paths.** Direct, plan, bead, swarm, `%alt`, `%repeat`, session, child, retry, dispatch, gate, pipe, question, monitor. | A binding bug on one path shows up only as a wrong or missing goal, days later | G2 (deterministic), G4 (draft rung) | A launch-path matrix test, plus **`sase goal audit`**, which lists LLM turns with no `goal_id` ("orphans") over a time window. It is an invariant you can run any day. |
| H2 | **Model judgment:** claiming honestly; naming vs. adopting. | Not deterministic, so one test can't prove it | G3 (claims), G4 (naming) | **`sase goal stats`**: claims/day; verify/ack/reject/lapse per model; adopt:name ratio; merges per 100 goals. Measured over a soak, not asserted. |
| H3 | **Multi-machine convergence** | The top measured driver of deep follow-up chains | G1 only | Deterministic **two-clone** concurrency tests (design test 8) with no live fleet needed, plus one athena ↔ apollo smoke check-it step that is *not* a landing blocker |
| H4 | **Pixel-level TUI** | Golden churn and performance budgets | G5 only | **Rule: G1–G4 cause zero golden churn.** Only G5 re-blesses. |
| H5 | **Attention semantics:** "did silencing successes lose anything?" | Can only be judged against real traffic | G6, gated on data from G3 and G4 | **Shadow coverage.** For every success ping during the soak, did its goal reach a claim or go Idle within 1 h of the last contributor finishing? |
| H6 | **Every-turn blast radius:** a required finalizer on every turn | One bug fails every agent | G3 | `builtin@goal` is **fail-open to `keep_open`**: a goal problem never fails a turn. Its trigger is "goal is bound", so G3 touches only bound turns until G4 widens it. |

The recommendation rests on this table. Each epic's acceptance is a small, local,
repeatable check. The model-judgment and cross-machine questions are answered by
instruments the epics ship, never by one agent's claim that an E2E run "looked right."

---

## 3. Code facts that change the rollout (verified at HEAD `c8a7a5ed3c`)

1. **`%tab` lineage inheritance is the binding template.**
   - `aff4fc082f` (sase-1bc.5, landed today, 17 files, +716) adds
     `xprompt/_tab_inheritance.py`. Turns export `SASE_AGENT_TAB`.
   - Agent-initiated launches stamp `%tab:<name>` into each child prompt segment:
     - LaunchApproval: `launch_request.py`
     - epic `bead work`: `cli_work_handler.py`
     - dispatch: `dispatch/launch.py`
   - Monitor and gate members inherit `agent_tab` through `_MONITOR_INHERITED_METADATA_FIELDS`.
   - This is exactly the design's *Parent*, *Session* and *Epic* rungs. Generalizing it
     to `%goal` means **G2 does not need the "persist `parent_agent_name`" prerequisite**
     for binding. The design's lineage finding is still true: no writer exists (readers
     at `launch_request_planning.py:317`, `inventory_sources.py:277`).
   - A bonus: the goal id appears in the prompt the LaunchApproval reviewer sees.
2. **Typed launch units are still behind a beta flag.**
   - `typed_launch_units` is beta (`feature_flags/registry.py:221`, flag bead `sase-s7`).
   - A `goal_binding` field that exists only on `AgentUnitWire`
     (`agent_launch/wires.rs:237`) would miss the untyped path.
   - So G2 should **resolve in the runner** before spawn, in `build_agent_meta`
     (`axe/run_agent_directive_metadata.py:214`), from directive + env + plan facts
     using a pure Rust resolver. That works on both paths. The typed-wire field can
     follow when `sase-s6` lands.
   - Precedents for pure resolvers: `resolve_effective_agent_tab` (`agent_tab.rs:168`)
     and `hold_directive.rs`.
3. **Successor metadata copying is uneven.**
   - `_add_agent_session_metadata` (`run_agent_directive_metadata.py:463-515`) copies
     clan and tab, but **not** bead or epic fields.
   - Retries pass only retry pointers (`run_agent_retry_spawn.py:272-280`).
   - Runner re-exec uses a separate allowlist (`:80-171`).
   - So `goal_id` needs three explicit additions. This is a G2 phase in its own right.
4. **Finalizers.** `builtin@goal` is G3's largest cost and the design understates it:
   - **`bead_action` is not a finalizer.** It is a `close`/`keep` field inside the commit
     declaration, decided by Rust `decide_bead_action`. `builtin@goal` would be the
     first new *first-party* finalizer since the protocol became unconditional.
   - **Builtins are hard-coded in ~12 Python files:** `providers.py`, `config.py`,
     `executor.py`, `declaration_store.py`, `controller.py`, `prepare.py`,
     `declaration_manifest.py`, `declaration_deferrals.py`,
     `monitor/host_completion_state.py`, `decks/final/enrichers.py`, and others.
   - **Rust side:** builtins are also listed in `FIRST_PARTY_PROVIDERS`
     (`continuation/completion.rs:31`).
   - **The context wire is `deny_unknown_fields`** (`finalizer/wire.rs:202`), so
     `assigned_goal` is a breaking (`feat!`) change.
   - **Budget:** one large phase for the core policy and one for the provider wiring.
   - **A plugin finalizer (`sase_finalizers` entry point) is not a substitute.** It would
     need no host changes, but the FINAL-deck enricher registry
     (`decks/final/enrichers.py:182`) only serves builtins, and `required:` must be
     host-owned.
5. **Gates.**
   - Gate kinds are a Python registry (`notification_gates/adapters.py:451-600`).
   - A `generic_form=True` kind routes to the custom-gate handler automatically.
   - The mobile enum maps unknown actions to `Unsupported`, which is forward-compatible.
   - So `GoalVerify` is **medium**. Precedents: `flag_triage` (32 files),
     `bead_stale_cleanup` (19 files).
   - Using the generic form keeps **sase-telegram and mobile untouched** in G3.
   - `JumpToGoal` is one more branch in the `_notification_dispatch.py:69-104` if/elif
     chain. Precedent: `JumpToMentorReview`, 15 files.
6. **The FINAL deck is still behind the `ace_final_deck` beta flag at HEAD**
   (`registry.py:24,45`). `sase-1b2` has 19 of 20 phases closed. The Goal-card enricher is
   a one-entry change *after* 1b2 lands, so it belongs in G5, not G3.
7. **No generic event store in sase-core.**
   - The bead ledger (`bead/events/`, about 3.9k LOC) and the artifact-link ledger
     (`artifact_link/events.rs`, 1.7k LOC) are separate, typed implementations.
   - The goal ledger is new code that copies the bead pattern.
     `write_stream_append_preserving` (`bead/jsonl.rs:509`) already enforces "never
     rewrite published history."
   - Budget this as G1's largest phase. Do **not** add an "extract a generic stream
     store" epic first (`corpus-before-mechanism`).
8. **Cross-repo sequencing is cheap, so it doesn't decide epic boundaries.**
   - sase-core cut 261 tags in 60 days, 24 of them minor (breaking) bumps.
   - The sase pin moved 92 times since 2026-08-27.
   - A breaking contract per epic is routine.
9. **The beads repo is busy, but co-hosting is still fine.**
   - It had 3,750 commits in the last 7 days (hidden clone on athena).
   - Goal events use disjoint paths, so rebases never conflict. Push *races* will still
     happen.
   - G1 should record the push-retry count as an instrument. That is the measurement
     the design's "split only when contention is measured" rule needs.
10. **Name collision.** Plan frontmatter already has a required free-text `goal:` field
    (`plan_validate.py:218-223`). Keep the design's `goal_id` for the stamped field, and
    say plainly in G2's docs that `goal:` text becomes the Goal's *outcome*.
11. **The jump fix is truly small.**
    - `handle_jump_to_agent` (`_notification_handlers.py:17-51`) scans linearly and never
      opens collapsed rows.
    - `reveal_agent_navigation_target` (`navigation/_agent_reveal.py:314`) already exists
      and has three callers.
    - This is a 1–2 file task with its own check, so it doesn't need an epic.

---

## 4. Options considered

| Option | Shape | Verdict |
| --- | --- | --- |
| **A. One epic** | About 35 phases, 5 contracts | **Reject.** The worst bucket in §1.2, and the `sase-xe` profile. |
| **B. The design's P0–P4 as five epics** | P0 is 3 unrelated small items; P1 ≈ 14 phases; P2 ≈ 8; P3 ≈ 7; P4 ≈ 4 | **Reject as written.** P0 isn't an epic, and P1 alone is in the 12+ bucket. Its *order* (drafts before claims) also stacks both model-judgment risks into the first user-visible release. |
| **C. Six epics, claims before drafts** (recommended) | 6 / 6 / 7 / 6 / 6 / 5 | **Adopt.** Every epic ≤7 phases, with one contract, one surface, and one instrument each (§5). |
| **D. Four epics** (G1+G2, G3, G4, G5+G6) | 12 / 7 / 6 / 11 | **Reject.** Two epics land in the 53–67% relaunch buckets, and G5+G6 would couple pixel acceptance to a notification cutover. |
| **E. "Claims without goals" first** | A per-agent finalizer flag, then Goals later | **Reject.** It is throwaway work. G3-on-epics gets the same early signal on claim quality with no rework, because epics already carry the outcome identity through the plan. |
| **F. Surfaces before claims** (G5 before G3) | A read-only inventory tab first | **Reject as the default.** The card's core is *You asked → Claim → Check it → Evidence*; designing it before any real claim exists is mechanism before corpus. Allowed as an overlap: G5 may start once G3's claim-payload phase is closed. |

---

## 5. The recommended program

These rules apply to every epic unless an epic says otherwise:
- **Flags:** the epic owns at most one beta flag, removed before it lands (the
  `sase_flags` rule and the `sase tool` precedent).
- **Acceptance:** it must not depend on a green master (`sase-th` and `sase-126` are
  still open).
- **Tests:** `just check` only (`check-full-is-explicit`).
- **Phases:** mostly medium and small, with at most two large.
- **Planning:** write only the G1 plan now. Name G2–G6 as successors in it so reviewers
  can see what G1 deliberately leaves out.

### 5.1 Pre-task (not an epic): `JumpToAgent` opens collapsed rows

- **Scope:** route `handle_jump_to_agent` through `reveal_agent_navigation_target`.
- **Check it:** collapse a tribe group, then open a `done` notification for an agent
  inside it. The row is opened and selected.
- **Why first:** every later goal → agent jump reuses this path, and it helps today's
  notifications on its own.
- **How to file:** `/sase_new_task`, type `bug`, size `small`.

### 5.2 G1: Goal ledger, `sase goal` CLI, and the `goal:` artifact

**Outcome:** Goals exist as durable, conflict-free, cross-machine records that you can
create, list, show, cite and settle by hand. They are fast no matter how much history
accumulates.

**Phases:**

| # | Phase | Size | Depends on |
| --- | --- | --- | --- |
| 1 | `core-contract`: ids, `STORE.json` schema fence, the **full** event vocabulary (including `claimed`, `adopted` and `merged`, which later epics produce), reducer, transition validation against basis | large | — |
| 2 | `ledger-io`: `live/` markers, `items/<id>/events/`, the machine-local `goals-hot.json` projection, `doctor --repair` | medium | 1 |
| 3 | `sidecar-sync`: `goals` role mapped into the beads repo, hidden-clone writes, bounded fetch → rebase → revalidate → push, outbox with `↑ unpublished`, sync watermark, local-only mode, push-retry counter | medium | 2 |
| 4 | `cli`: `new` / `list` / `show` / `verify` / `drop` / `reopen` / `merge` / `edit`; human verbs refused inside agent runs; fast `list` path; `--json` | medium | 2 |
| 5 | `artifact-kind`: resolvable `goal:` kind, `sase artifact read goal:<id>` card, `@goal:<id>` citation, and registration of all four relations (`pursues`, `evidences`, `defines`, `follows`) in one contract bump | medium | 1 |
| 6 | `acceptance`: two-clone concurrency and marker-race tests, a 100k-settled benchmark with file-open tracing, athena ↔ apollo smoke | medium | 3, 4, 5 |

**Check it (you):**
1. `sase goal new -t "Try goals" -o "…"` on athena. Within the TTL, `sase goal list` on
   apollo shows it next to `synced Ns ago`.
2. `time sase goal list` is under 50 ms. `sase goal verify <id>` removes it from the list;
   `list -s done` shows it.
3. A prompt containing `@goal:<id>` expands to the goal's card.

**Released contract:** the goal ledger wire plus the `goal:` kind and relations.

**Flag:** optional `goals_cli` scaffolding.

**Owns design acceptance tests** 8, 9 and 12.

**Settle before planning:**
- **Visibility.** The beads repo is public, so titles, outcomes and claims become as
  public as bead titles.
- **Freeze the event vocabulary.** Retrofitting event kinds into an immutable ledger
  means versioned events.
- **Coordinate with in-flight work:**
  - `sase-yy` / `sase-yy.8.6` (immutable artifact-link events)
  - `sase-y2` (machine-link writes off the primary)
  - `sase-x7.5.1` (canonical shared formats: the goal wire should be canonical from the
    start)

### 5.3 G2: Deterministic binding (explicit, inherited, and plan-derived goals)

**Outcome:** Whenever the host already *knows* the goal, the goal is bound before the
provider starts, on every launch path, and the agent sees one line naming it. There are
no drafts and no model judgment yet.

**Phases:**

| # | Phase | Size | Depends on |
| --- | --- | --- | --- |
| 1 | `core-resolver`: pure `resolve_goal_binding` over launch facts. The ladder is explicit → session → plan → clan → parent → bead, with a **reserved `draft` variant** so G4 isn't a breaking change. Scan-wire `goal_id`. | medium | G1 |
| 2 | `directive`: `%goal:<id>` / `%goal:new` in `_KNOWN_DIRECTIVES`, completion over unsettled goals, `goal_id` in `agent_meta.json`, `SASE_GOAL_ID` export, refusal to bind to a settled goal | medium | 1 |
| 3 | `inheritance`: generalize `_tab_inheritance` into a shared directive-inheritance helper; add `goal_id` to the session-successor copy, retry spawn, re-exec allowlist, monitor/gate member fields, LaunchApproval, `bead work` and dispatch | medium | 2 |
| 4 | `plan-goals`: `sase plan propose` creates or refines the goal from the plan's `title`/`goal` and stamps `goal_id`. Epic phase and land agents resolve it through epic → plan. PlanApproval outcomes: approve continues, plan-only acceptance settles `done · acknowledged`, reject returns to active. | medium | 2 |
| 5 | `bound-line`: the ~40-token `SASE GOAL ⌖id — …` line at the `invoke_agent` injection point (`llm_provider/_invoke.py`, between preprocessing and `save_prompt_to_file`); `pursues`/`defines` projections; `sase goal show` lists contributors | small | 2, 4 |
| 6 | `audit-and-matrix`: `sase goal audit [--since]` (orphan and unexpected-binding report) plus the launch-path matrix acceptance | medium | 3, 4, 5 |

**Check it (you):**
1. `sase goal new …`, then launch a `%goal:<id>` agent that `/sase_run`s a child and pipes
   to a successor. `sase goal show <id>` lists all three.
2. Approve a small epic plan. The plan file carries `goal_id`, and every phase and land
   agent's metadata has the same `goal_id`.
3. `%goal:<settled id>` is refused with a pointer to `%goal:new`.

**Released contract:** scan wire `goal_id` plus the resolver binding.

**Flag:** `goal_binding` scaffolding. Plan-derived goals reach every epic as soon as
phase 4 lands.

**Owns design acceptance tests** 2 (deterministic paths) and 5 (digest recorded on
creation).

**Wait for / coordinate with:**
- `sase-1bc` (agent tabs). It owns the directive, inheritance and scan-wire seams right
  now: land it first, then generalize its helper.
- `sase-1ab` (turn rename vocabulary).

**Out of scope:** drafts, clan-*shared draft* naming, routine standing goals.

### 5.4 G3: Claims and verification

**Outcome:** An agent working on a bound goal ends each turn with `keep_open` or `claim`.
A claim moves the goal to Review and opens exactly one `GoalVerify` gate. You verify,
reject (optionally relaunching with feedback) or drop it from the TUI, the CLI or
Telegram.

**Phases:**

| # | Phase | Size | Depends on |
| --- | --- | --- | --- |
| 1 | `core-policy`: `goal_action` (`keep_open`/`claim`), `decide_goal_action`, roles derived from launch structure plus liveness, evidence rules per claim shape, `assigned_goal` on the finalizer context (breaking), a **reserved `name` field** for G4 | large | G2 |
| 2 | `provider`: `builtin@goal` across the ~12 builtin sites plus `FIRST_PARTY_PROVIDERS`; `after: [commit]`; trigger `goal_bound`; **refusal or failure → `keep_open` plus a diagnostic, never a failed turn**; declaration-recovery turn; predeclared decision for prepared monitors | large | 1 |
| 3 | `evidence`: host-gathered candidates (symbolic `@commit`, created `file:` artifacts, plan ref, covering-receipt **snapshot**), provenance checks, strength badge | medium | 2 |
| 4 | `gate`: `GoalVerify` as a generic-form gate kind with verify / reject(+relaunch pre-filled with `%goal:<id>`) / drop, idempotent on `goal:<id>:claim:<n>`, and Remote Attention dedupe. `JumpToGoal` opens the `goal:` card from G1 until G5 retargets it. | medium | 1 |
| 5 | `lifecycle-and-stats`: claim retraction when your follow-up hits a goal in Review (R12), stale-basis handling, concurrency rules, **`sase goal stats`** (claims, verify/reject/lapse per model, time to verify), **shadow coverage** for bound turns | medium | 2, 4 |
| 6 | `skills`: `sase_final` paragraph and `/sase_goal` list/show, through generated skill sources | small | 2 |
| 7 | `acceptance`: epic land claims end to end; phases can't claim; a claim is refused while a contributor is live; one gate across retries and machines; reading or dismissing a row never settles it | medium | 3, 4, 5, 6 |

**Check it (you):**
1. Approve a small epic plan. When it lands you get **one** `GoalVerify` notification
   carrying a claim sentence, 1–3 check-it steps, `@commit` evidence and a receipt
   snapshot. Phase agents' finalizer records show `keep_open`.
2. Reject it from Telegram with a note. A relaunched agent appears on the same goal, and
   the claim shows as retracted.
3. Kill a phase agent mid-run. No claim appears, and the goal stays active.
4. `sase goal stats` shows the claim and your decision.

**Released contract:** the finalizer context wire (`assigned_goal`).

**Flag:** `goal_claims` scaffolding.

**Notification load while claims ship alongside today's pings:** about **+15%** more
notifications. That is one claim per ~6.6 agent turns, from the lead's count of about
310 outcomes to 2,048 runs a week. This is temporary and bounded by the soak.

**Owns design acceptance tests** 4, 6 and 7.

**Wait for / coordinate with:**
- `sase-rr`: all 4 phases and its child epic are closed, but the epic is still open.
  Close it so finalizer ownership isn't ambiguous.
- `sase-1ah` (E4 receipts): claims embed *its* receipt contract.
- `sase-zq` (bead decisions inside commit declarations).
- `sase-11t` (crash-safe gate handoff).
- `sase-117` / `sase-117.5` (settlement notification targeting).

**Dogfooding:** from G3 on, every later Goals epic has a plan-derived goal. **You verify
G4, G5 and G6 through the feature itself.**

### 5.5 G4: Every agent has a goal (drafts, naming, adoption)

**Outcome:** An LLM turn the host can't bind gets a machine-local draft. The agent's
first act is to name it or adopt an active goal. Swarms share one draft. Questions
settle when you open the answer.

**Phases:**

| # | Phase | Size | Depends on |
| --- | --- | --- | --- |
| 1 | `core-drafts`: the draft rung in the resolver, machine-local draft store, compare-and-swap `name`, `adopt` (retracts a Review claim), drafts never published until named | medium | G2, G3 |
| 2 | `launch-drafts`: draft creation before spawn, clan-shared draft (first namer wins), routine **standing goals** (claims refused), mechanical members inherit | medium | 1 |
| 3 | `intake`: the ~80-token intake block; `sase goal name` / `adopt` restricted to the agent's own draft; `/sase_goal` naming guidance | medium | 1 |
| 4 | `finalizer-drafts`: a draft-bound payload requires `name`; auto-name with an `auto-named` badge if the run dies; **naming publishes the creator's prompt** (the new publication trigger) | medium | 2, 3 |
| 5 | `answer-ack`: `@reply` snapshot evidence; opening the answer settles `done · acknowledged`, with undo; `goals.answer_claims` config | medium | 4 |
| 6 | `acceptance-and-instruments`: `audit` reports 0 orphans; a 5-member swarm makes 1 goal and 1 claim; an adopted draft never appears in the shared ledger; adopt:name ratio and merges per 100 goals added to `stats` | medium | 4, 5 |

**Check it (you):**
1. Ask a quick question. `sase goal list` shows one goal that the agent named itself.
   The answer arrives as a claim, and opening it settles the goal as acknowledged.
2. Launch a 5-member research clan. It produces exactly one goal and one claim, from
   the lead.
3. Re-ask something already in flight. The agent adopts the existing goal, and its
   written reason shows in `sase goal show`.
4. `sase goal audit --since 24h` reports 0 unbound LLM turns.

**Released contract:** the resolver's `draft` variant, already reserved in G2, so this
is additive.

**Flag:** `goal_drafts` scaffolding.

**Owns design acceptance tests** 1, 3 and 11.

**Can run in parallel with G5.** G4 touches launch, intake and skills; G5 touches TUI
and artifact panes.

### 5.6 G5: Goals tab and Agents-tab integration

**Outcome:** Goals become the daily loop: one keystroke, one badge, and numbered jumps in
both directions.

**Phases:**

| # | Phase | Size | Depends on |
| --- | --- | --- | --- |
| 1 | `read-model`: a cached goal snapshot with change tokens and off-thread refresh (`tui_perf` rules, no per-render filesystem access) | medium | G3 |
| 2 | `tab`: `TAB_ORDER = (agents, goals, artifacts, services)`; Review/Running/Idle lanes plus collapsed Standing and Done today; contributor pips; `synced Ns ago`; badge | large | 1 |
| 3 | `card`: *You asked → Outcome → Claim → Check it → Evidence → Gaps → Agents → Timeline*; numbered chips through the relation rail; agent jumps through `reveal_agent_navigation_target` with an Artifacts ▸ Agent fallback; `JumpToGoal` retargeted to the tab | large | 2 |
| 4 | `keys`: `v r x l e m a p n / P h`, registered in `default_config.yml` | medium | 3 |
| 5 | `agents-integration`: identity-header goal chip, FINAL-deck **Goal enricher** (after `sase-1b2` lands), `BY_GOAL` grouping (after `sase-1bc.8`'s `o`/`O` ladder) | medium | 1 |
| 6 | `goldens-and-budgets`: visual snapshots in both flag states, projection refresh < 2 ms at n = 100, highlight → paint within 16 ms, live inspection | medium | 2–5 |

**Check it (you):**
1. The Goals tab badge equals the Review count, and the lanes read in the order you'd
   act on them.
2. On a Review card, press `3`. It jumps to that agent even when its group is collapsed.
   Press `v` to verify.
3. In the Agents tab, the identity header shows the goal chip, and `o` offers *by goal*.

**Flag:** `goals_tab` scaffolding.

**Owns design acceptance test** 10.

**Wait for / coordinate with:**
- `sase-1b2` and `sase-1b1` (decks)
- `sase-1bc` (tabs and layout ladder)
- `sase-124`, `sase-132` and `sase-zn` (TUI performance)
- `sase-19i` (Node Finder)

### 5.7 G6: Attention cutover

**Start gate.** The G6 plan is written only after all of the following hold. The
thresholds are proposals for you to confirm.

| Measure | Proposed threshold |
| --- | --- |
| Time and volume since G4 landed | ≥ 7 days **and** ≥ 100 settled claims |
| Shadow coverage | ≥ 90% of success pings belong to a goal that reached a claim or Idle within 1 h of its last contributor finishing |
| Claim precision: (verify + ack) ÷ (verify + ack + reject) | ≥ 80% overall, reported per model |
| Merges per 100 goals | ≤ 5 |
| `audit` orphans | 0 |
| Turns failed because of `builtin@goal` | 0 |

**Phases:**

| # | Phase | Size | Depends on |
| --- | --- | --- | --- |
| 1 | `silence-successes`: `JumpToAgent(done)` goes quiet; claims keep the chime | medium | gate |
| 2 | `retire-unread`: remove the ✅ Agents-row unread projection (`_notification_matching.py:62-68` and its consumers) and migrate unread success rows; ❌ stays | medium | 1 |
| 3 | `idle-and-hygiene`: quiet Idle notices with the last progress note, aging, `goals.idle_nudge_days`, and the lapse flavor for stale reviews if you want it (design open question 6) | medium | 1 |
| 4 | `follows`: a follow-up after Done starts a new goal linked by `follows` | small | — |
| 5 | `unflag-and-measure`: remove the flag, docs, memory, before/after notification-volume report, and a decision on the startup tab | small | 1–4 |

**Check it (you):**
1. A successful agent run makes no ✅ dot and no chime. Its goal's claim does.
2. The volume report shows notifications per day before and after.

**Flag:** `goal_attention` scaffolding.

**Wait for:** `sase-117.5` (notification targeting).

---

## 6. Sequencing, timeline, and cross-epic rules

```text
pre-task ─┐
          ▼
 G1 ledger ──► G2 binding ──► G3 claims ──┬──► G4 drafts ──┐
                                          └──► G5 tab ─────┴──► soak ≥7d + metrics ──► G6 cutover
```

**Timeline.** The `sase tool` series closed E1 in 38 h, E2 in 7.6 h and E3 in 27 h, with
3 h–2 day gaps between plans. Median time to close a recent root epic is 5.3 h (p90
32.7 h). On that basis, G1–G5 take about **7–12 days** and the program about
**2½–3½ weeks** including the soak. That is short enough that splitting costs little
calendar time.

**Cross-epic rules** (state them in every plan):
1. **Freeze the contract vocabulary early.**
   - G1 defines every event kind and the status machine, even ones later epics produce.
   - G2 reserves the `draft` binding variant.
   - G3 reserves the `name` payload field.
   - Later epics add producers, not breaking schema changes.
2. **A goal problem never fails an agent turn.** Binding failures and finalizer
   refusals fall back to "unbound" or `keep_open`, with a diagnostic that `sase goal
   audit` surfaces.
3. **Zero golden churn outside G5.** G1–G4 prove themselves through the CLI, the
   notification inbox, generic gate forms and `sase artifact read goal:`.
4. **Acceptance never depends on a green master.** Each epic's check-it steps run on
   master as it stands.
5. **Gate on acceptance, not bead status.** A successor plan may be approved once its
   predecessor's check-it steps pass on master. If a predecessor's land bead sits for
   more than 24 h with all phases closed, which is the common stall, close it
   deliberately rather than letting it block the chain.
6. **Plan one epic at a time.** Write G1 only. Revise G2–G6 using what G1 measures,
   especially push-retry contention and list latency.

**First moves, in order:**
1. **A decision record** via `/sase_memory_write`: *"Goals: the host binds, agents
   claim, users settle"*. It should cover the three invariants, why the alternatives
   lost (the `SASE_PLAN` check, agent-closed goals, a mutable snapshot store), what it
   costs, and what would reopen it. All six plans can then cite it instead of
   re-arguing it. `record-before-admit` played the same role for the `sase tool`
   series.
2. **File the pre-task** via `/sase_new_task`.
3. **Close `sase-rr`** (every phase and its child epic are closed) so finalizer
   ownership is clear before G3.
4. **Answer the G1-blocking questions:** ledger visibility and co-hosting in the beads
   repo. The other open questions in the design (answer ack, tab position, routines,
   stale reviews) can wait until G4, G5 or G6.
5. **Write the G1 plan** via `/sase_plan`, naming G2–G6 as successors.

---

## 7. Risks and what would change this recommendation

| Risk | Signal | Response |
| --- | --- | --- |
| G2's launch-path matrix finds a path that can't be bound in the runner (for example, a typed-unit-only path) | A matrix test fails for structural reasons | Move that path's binding onto `AgentUnitWire` inside G2. It's still one contract; don't add an epic. |
| G3 claims are low-precision on some models | Per-model precision < 60% in `stats` | Add a per-model claim policy (claims shown as `unreviewed`, or `keep_open` forced) before G4 widens exposure. Don't start G6. |
| Push contention in the beads repo | The G1 push-retry counter rises, or claims queue in the outbox | Split the `goals` role into its own repo. The role indirection already allows it, and it's a sidecar config change, not an epic. |
| Shadow coverage stays below 90% | G6's gate never opens | Something is lost between contributor finish and claim, usually Idle detection or role derivation. Fix it in a small G3/G4 follow-up and keep success pings loud meanwhile. The program still works without G6; it's just noisier. |
| You'd rather have one dark-launched program flag | Your preference | Allowed: `sase_flags` permits a user-requested flag, and `typed_launch_units`, `provider_drain` and `ace_final_deck` each span epics. The cost: both-state tests in all six epics, and removal becomes a seventh unit of work. I'd still use per-epic flags. |
| An epic grows past 7 phases while planning | The planner's phase list | Push the overflow into the successor (for example, routine standing goals can move from G4 to G6). Don't widen the epic. |

---

## 8. Recommended solution

**Build Goals as six sequential epics plus one small task beforehand, not one epic.**
Each epic has at most 7 mostly-medium phases, one released contract, one acceptance
surface you can check in minutes, and its own instrument for whatever can't be checked
by a single test.

1. **Pre-task:** make `JumpToAgent` open collapsed rows (small `bug` task).
2. **G1 — Goal ledger, CLI, `goal:` artifact** (6 phases). A conflict-free,
   cross-machine event ledger in a `goals` role co-hosted in the beads repo, and human
   `sase goal` verbs. Freeze the full event vocabulary here. Verified by two-clone
   concurrency tests, a 100k-settled latency benchmark, and an athena → apollo
   `sase goal list` check.
3. **G2 — Deterministic binding** (6 phases). `%goal`, plan-derived goals, and
   inheritance across all launch paths, built by **generalizing the `%tab` inheritance
   that landed today** and resolved in the runner so it works on both launch paths.
   Verified by the launch-path matrix and `sase goal audit`.
4. **G3 — Claims and verification** (7 phases). A fail-open `builtin@goal` after commit,
   host-gathered and provenance-checked evidence, one generic-form `GoalVerify` gate
   answerable from the TUI, the CLI and Telegram, claim retraction on your follow-ups,
   and `sase goal stats` plus shadow coverage. It is exercised first on epics, where
   today's noise is worst. Verified by one gate per landed epic.
5. **G4 — Drafts, naming and adoption** (6 phases). Universal binding: clan-shared
   drafts, compare-and-swap naming, adoption with reasons, routine standing goals,
   answer acknowledgement, and publish-on-name. Verified by 0 orphans and one goal per
   swarm. It runs in parallel with G5.
6. **G5 — Goals tab and Agents-tab integration** (6 phases). The only epic with golden
   churn. It waits for `sase-1b2` and `sase-1bc` to land. Verified by the badge, lanes,
   card, jumps, and performance budgets.
7. **G6 — Attention cutover** (5 phases). Started only after a soak of at least 7 days
   passes the coverage, precision, merge-rate, orphan and zero-failure thresholds. It
   silences success pings, retires ✅ unread, and adds Idle notices and `follows`
   chains. Verified by a before/after notification-volume report.

**Start now** by recording the "host binds, agents claim, users settle" decision,
closing `sase-rr`, settling ledger visibility, and writing **only the G1 plan**. Revise
the later plans from what each predecessor measures.
