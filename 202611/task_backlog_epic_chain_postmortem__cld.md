# Task-Backlog Epic Chain Postmortem (sase-1pm → sase-1qt)

_Researcher: cld · 2026-11-02 · Scope: the five-epic task-bead cleanup chain started on
2026-10-29, plus the identical earlier chain started on 2026-10-26, as a comparison._

## Bottom Line

The chain was **good at fixing defects and bad at shrinking the backlog**.

- **Fixes landed and mostly held.** Five epics closed 23 distinct seed tasks plus one
  related task (sase-1i9), all with recorded evidence, and every one of them is still
  closed. On athena, the seed flakes with full-run data show **zero recurrences** after
  their fix: sase-1p5 had 24 hits in the 14 days before its fix and none in 311 runs
  after; sase-1mv went 54 → 0 in 106 runs; sase-xo went 9 → 0 in 76 runs. The landers'
  audits caught real defects the phase workers missed, such as Rust-boundary violations
  and an over-budget import closure.
- **The backlog barely moved.** The chain closed about 34 task beads (seeds plus triage
  closures), but the open count only went from 398 to 382 in 4.4 days. The fleet filed
  about 34 new tasks over the same window, and the chain itself added 5. The prompt's
  stop condition, "until all task beads in this project are closed," cannot be reached:
  its own rules never select the 130 open feature and memory beads.
- **Three process defects cost the most time and work:**
  1. **"Propose the next epic as your last action" keeps losing work.** Plan proposal
     ends the turn before host finalization. This lost all of epic 5's landing repairs,
     which took about 11 hours to discover and redo. It also left the plans for epics
     1–4 marked `status: wip` on origin. Every lander claimed to mark its plan done.
  2. **A human saw only epic 1.** Epics 2–5 were approved with no human review, and each
     decision took the planner's default. The prompt's "give the user the option to opt
     out" turned into a boilerplate `optional_scope` decision that nobody ever answered.
  3. **Large, design-shaped seeds became nested epics and stalled the serial chain.**
     Epic 3 took 68 hours. Four of its phases finished in about 3 hours; the fifth,
     sase-1cc, turned into an epic inside an epic, and one of its phases sat unclosable
     for about 2 days.
- **The chain also broke master for others.** It introduced at least four master-red
  regressions: the contract manifest, the scoped suite-gate helper, completion kinds,
  and the Justfile fix test. Each was caught and repaired, but it appeared in tens of
  athena full-run records in the meantime.

**Recommendation in one line:** Run the chain again with a revised prompt (§8):
defect-only scope, no nested epics, an explicit stop rule, and landers that write the
next plan as a **validated draft and stop**. They do not propose it. You approve each
epic with one quick review. Do the housekeeping in §8.3 before you start.

---

## 1. What Ran

### 1.1 The Originating Prompt

The athena agent `15r` (claude/opus at `@xlarge`) received this prompt on 2026-10-29 at
01:40 EDT. It was quoted from the athena transcript
`~/.sase/chats/202610/gh_sase_org__sase-ace_run-15r__plan-261029_010851.md`:

> You are responsible for working through all open task beads in this project. Follow
> the steps below:
>
> - Close the ones that you can verify are duplicates or are obsolete (already resolved,
>   for example) then plan a 5-phase maximum epic to work any open task beads in this
>   project.
> - This epic should be responsible for at most 5 task beads (the 5 most important
>   ones). It is fine for one phase to work more than one bead, but if there are more
>   than 5 beads that should be investigated, then the epic lander of that epic MUST be
>   responsible for creating a new epic to work the remaining beads, 5 at a tine, using
>   the same epic rules, until all task beads in this project are closed.
> - Each epic plan should specify decisions if necessary. Keep these to a minimum but
>   make sure to use them to verify any questionable work that might not actually need
>   to get done. In other words, give the user the option to opt-out of feature work or
>   memory changes, for example, that might not actually be desirable.
>
> Create your first epic plan using your /sase_plan now. %m:@xlarge

You had sent the **identical prompt** three days earlier to agent `14m` (2026-10-26). It
started a first chain, sase-1oh → sase-1ou, that was still open when `15r` started the
second one. On 2026-10-30 the sase-1ou lander merged its continuation into the new chain
"instead of forking another parallel backlog chain" (sase-1pu note #7, sase-1ou note
#9). So for about a day, **two backlog chains ran at once**.

### 1.2 The Chain

| #   | Epic bead | Plan (sase--plans)                                               | Proposed by / model                    | Seeds (phases)                                 | Created → closed (UTC)                      | Wall time                         |
| --- | --------- | ---------------------------------------------------------------- | -------------------------------------- | ---------------------------------------------- | ------------------------------------------- | --------------------------------- |
| 1   | sase-1pm  | `202610/task_backlog_epic_1.md`                                  | `15r`, claude/opus, **human-reviewed** | 1nh, 1ll, 1p5, 1ic, 1cb (5)                    | 10-29 05:44 → 10-29 14:33                   | 8.8 h                             |
| 2   | sase-1pn  | `202610/task_backlog_epic_2.md`                                  | sase-1pm.land, claude/opus, auto       | 163, 1p9, o7, 1cs + vr (4)                     | 10-29 14:44 → 10-29 23:08                   | 8.4 h (+ finish tale)             |
| 3   | sase-1pu  | `202610/task_backlog_epic_3.md`                                  | sase-1pn.land tale, codex/luna, auto   | 1os, 12v, 1mv, 120, 1cc (5)                    | 10-29 23:19 → 11-01 19:23                   | **68 h**                          |
| 4   | sase-1qn  | `202611/task_backlog_epic_4.md`                                  | sase-1pu.land, claude/opus, auto       | o7, 1ic, 1gz, 13a, 19m (5)                     | 11-01 19:34 → 11-01 22:50                   | **3.3 h**                         |
| 5   | sase-1qt  | `202611/task_backlog_epic_5.md`                                  | sase-1qn.land, claude/opus, auto       | 1ia + 1l3 + 1hy, xo, 15h (3), plus related 1i9 | 11-01 23:08 → 11-02 03:39, reopened → 14:28 | 4.5 h, then 15.3 h after the loss |
| (6) | —         | draft only, athena `~/.sase/plans/202611/task_backlog_epic_6.md` | sase-1qt tale, never approved          | 1oy, 1em, zo, 1pw, 1ce (5)                     | —                                           | —                                 |

From `15r` to the final close of epic 5 took about **105 hours (4.4 days)**. The chain
published **160 agent runs** to the agents sidecar, counting phases, plans, gates,
monitors, landers, and tales: 51 for epic 1, 11 for epic 2, 51 for epic 3, 20 for epic
4, and 27 for epic 5. Phase workers ran on muse, codex (astra/luna), and grok. Landers
ran on claude/opus or codex/astra at `xhigh`.

### 1.3 The Rules Drifted, Mostly for the Better

Epic 1's planner turned the prompt into a five-step **"Mandatory: continue the backlog
chain"** block plus a list of seed leads. Each lander was supposed to pass that block on
"verbatim." It did not:

- **Epic 3** (written by codex) dropped "MUST" and the seed-lead list.
- **Epic 4** added a **"Rules for every phase"** block: reproduce first; no skips,
  xfails, timeouts, or budget raises; sase-core boundary; read `lint_and_test`; record
  base, runtime, before/after results, and limits.
- **Epic 5** added ranking from the **selection-health full-run records** (objective
  recurrence counts) and "on any fleet host."
- **The epic-6 draft** adds "re-run each candidate at the current tree" and a list of
  carried-forward "prior leads."

These were real lessons, so the drift was useful. But the chain's operating contract
lived only inside generated plans and changed with every lander. Plans also grew each
round: the epic-4 plan is 16.8 KB, epic 5 is 17.3 KB, and the epic-6 draft is 23.0 KB,
mostly from accumulated "rejected candidates" context.

---

## 2. Did the Fixes Work?

### 2.1 Seed Outcomes

All 24 seed and related beads are **closed `done`** as of 2026-11-02, each with commit
and test evidence in its close note. Two of epic 1–2's ten fixes **did not hold** and
had to be redone in epic 4:

| Bead     | First fixed by | Reopened                             | Reworked by | Note                                                                                       |
| -------- | -------------- | ------------------------------------ | ----------- | ------------------------------------------------------------------------------------------ |
| sase-o7  | epic 2         | 11 h later (10-30 10:23Z, toobig-8u) | epic 4      | Sixth close. The epic-2 close guard also contributed to epic 3's stall (§4.2).             |
| sase-1ic | epic 1         | 2 days later (10-31 16:44Z, 16n)     | epic 4      | Third close. The epic-4 strict cap left 1,326 B of headroom, and epic 5 overran it (§5.3). |

### 2.2 Evidence From the Full-Run Records

I counted failures in athena's selection-health full-run records
(`~/.sase/test-selection/gh_sase-org__sase/*-full-run.json`, 1,321 records). The counts
use only runs with at most five failures, the same filter epic 5 used. "After" runs from
the seed's close time to 2026-11-02 14:08Z.

| Seed           | Hits in 14 days before close | Hits after close | Runs after close |
| -------------- | ---------------------------: | ---------------: | ---------------: |
| sase-1p5       |                           24 |            **0** |              311 |
| sase-1pg†      |                           23 |                1 |              285 |
| sase-1mv       |                           54 |            **0** |              106 |
| sase-120       |                            2 |            **0** |              106 |
| sase-13a       |                            6 |            **0** |               83 |
| sase-19m       |                            3 |            **0** |               83 |
| sase-xo        |                            9 |            **0** |               76 |
| sase-1ic       |                          105 |            **3** |               83 |
| sase-1ia / 1hy |              0 (apollo-only) |                0 |               76 |

† sase-1pg was closed by the epic-2 lander as a follow-up, not as a seed.

The post-fix windows are short, between 1 and 4 days, but the direction is clear. The
seeds the chain picked from recurrence data really were what kept checks red, and the
fixes removed them. sase-1ic's three post-close hits are the epic-5 overrun; the redo
lander repaired it.

### 2.3 The Landers Were the Real Quality Gate

In two of five epics, the lander found unfinished epic work that the phase workers had
reported as done:

- **Epic 2:** quarantine policy still decided in Python, the epic-symbol upstream-union
  problem, and a contract-manifest collision. A finish tale fixed them.
- **Epic 5:** a Python 1.0 fallback that violated the required-Rust boundary, a fixture
  lock held through the child wait, and the import-closure overrun. This needed a finish
  tale and then a redo tale.

Epic 3's nested landers did the same thing twice. The xhigh landing audit is earning its
cost; keep it.

---

## 3. Did the Backlog Shrink?

| Point in the chain           | Non-closed task beads |
| ---------------------------- | --------------------: |
| Before epic-1 triage (10-29) |                   398 |
| Epic-1 lander (10-29)        |                   384 |
| Epic-2 lander (10-29)        |                   385 |
| Epic-3 lander (11-01)        |                   388 |
| Epic-4 lander (11-01)        |                   387 |
| Now (11-02, my listing)      |                   382 |

During the chain window (10-29 05:44Z → 11-02 14:30Z), **34 task beads were created**
(14 flake, 9 ci, 7 bug, 3 feature, 1 memory) and **44 were closed** (33 done, 10
canceled, 1 superseded). Chain agents performed 26 of those closures. Most of the 10
cancellations came from the _other_ chain's dormant-flake sweep, which closed ten quiet
flakes under sase-1ou's `dormant_flakes = close` decision. The `15r` chain's own rule
was "dormant beads stay open."

The duplicate/obsolete re-triage that every lander must run produced **8, 0, 0, 1, 0,
and 0** closures across the initial sweep, epics 1–4, and the epic-6 draft. After the
first sweep, each lander spent a full re-list of about 385 beads to close one bead
total.

### 3.1 What Is Left

| Breakdown of the 382 non-closed tasks                | Count                                    |
| ---------------------------------------------------- | ---------------------------------------- |
| bug / feature / flake / memory / ci / flag / untyped | 139 / **100** / 89 / **30** / 12 / 7 / 5 |
| Size: large / medium / small / xsmall / xlarge       | 208 / 71 / 94 / 8 / 1                    |
| +1 corroboration: 0 / 1–2 / 3–9 / 10+                | **305** / 58 / 16 / 3                    |
| Last updated over 30 days ago                        | 161                                      |

Two things follow from this:

- **The stop condition can never be met.** The chain ranks by fleet-wide cost and keeps
  `optional_scope = keep_five_seeds`, so it never selects the 100 feature and 30 memory
  beads, about a third of the backlog. Even with no new tasks, 252 defect beads at 5 per
  epic is about 50 more epics. At the observed rates (about 7.7 new tasks a day against
  about 6 chain closures a day), it does not converge.
- **The highest-value remaining bead is excluded by a rule loophole.** sase-j0
  ("check-full is red on master," **+38**, the most-corroborated open bead) has been
  `in_progress` since August. Agent `14m` recorded on 10-26 that its holder agent "is no
  longer running." Epic 1's seed list even called it "in_progress since August with no
  live holder." Still, epics 4 and 5 and the epic-6 draft all skip it as "in_progress
  under its own holder." The rules have no way to handle a stale claim.

---

## 4. Where the Time Went

### 4.1 Phases Are Fast; Nested Epics and Landing Repairs Are Slow

| Epic | Phase span (non-nested) | Long pole                                                               | Landing                                                       |
| ---- | ----------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------- |
| 1    | 0.2–1.6 h               | Phase .5 (sase-1cb rebase gate) became nested epic 1pm.5.1: 7.8 h       | about 1 h                                                     |
| 2    | 0.8–2.6 h               | —                                                                       | about 5.8 h (audit → finish tale → 108-minute check)          |
| 3    | 0.6–3.1 h               | Phase .5 (sase-1cc) became epic 1pu.5.1, then 1pu.5.1.5: **about 68 h** | about 10 min after the nested epics closed                    |
| 4    | 1.0–3.0 h               | —                                                                       | **18 min**                                                    |
| 5    | 0.5–2.6 h               | —                                                                       | 1.9 h, then a lost tale, then about 11 h to discover and redo |

Epic 4 is the model run: five large phases, clear per-phase rules, and an 18-minute
landing. The slow epics all had either a **design-shaped seed** (sase-1cb, a new
pre-push gate; sase-1cc, a run-state convergence subsystem with 6 phases across two
nested plans) or **lost or unfinished landing work**.

### 4.2 Epic 3's Two-Day Stall

Phase **sase-1pu.5.1.4** finished its work at 10-30 09:01Z but could not close. The
epic-symbol close guard combines local and upstream `--epic-symbol` rows, and
origin/master still held 8 of the phase's rows until its own commit landed (note #3).
Nothing retried the close after the host landed the commit. The phase sat until an
athena restart and the `16p` recovery agent closed it on 11-01 14:51Z (note #4).

The close guard that blocked it came from epic 2's sase-o7 work (8bea2e8414). Epic 4
later reworked that guard with a freshness preflight. This is a clear case of one epic's
fix stalling a later epic, and the chain is strictly serial, so the whole chain waited
too.

---

## 5. What Went Wrong

### 5.1 Ending the Lander Turn With a Plan Proposal Loses Work (Highest Severity)

The prompt's design, carried as step 5 in every plan, is "Propose it with `/sase_plan`.
Proposing ends the land agent's turn, so do it last." With `staged_handoffs` off (still
`beta, default=off` today), that proposal ends the turn **before host finalization
commits the lander's edits**. Observed damage:

| When          | Who                               | What was lost                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ------------- | --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 10-28         | sase-1ou.land (first chain)       | The sase-core sase-1p6 fix and flake-baseline edits. The bead was closed as done while the code was not on master. A recovery epic (sase-1ph) redid it.                                                                                                                                                                                                                                                                                        |
| 10-29 → 11-01 | Landers of epics 1, 2, 3, 4       | Their `status: done` plan edits. **The plans for epics 1–4 still say `status: wip` on origin/main today**, as do `finish_task_backlog_epic_2.md` and `redo_1qt_landing.md`.                                                                                                                                                                                                                                                                    |
| 11-01 22:51   | sase-1qt.land--code (codex/astra) | **All of epic 5's landing repairs**, in sase and sase-core. The provider was SIGTERMed (exit 143) after proposing epic 6, and the gate turn failed ("workspace claim is no longer owned"). When the workspace was reused, it was reset and the linked core was re-cloned. The epic and six task beads were closed as done anyway. On 11-02, the lander was relaunched on the closed bead, found the loss, and redid the work in a second tale. |

Each lander documented the hazard. The epic-1 lander wrote that the plan edits "may not
be committed; epic 2's Landing re-checks them." Even so, the plans kept the propose-last
rule until the redo tale chose `chain_continuation = defer_to_owner`. The system fix is
still in flight: sase-1pj.7.1 "Retain stranded handoff workspaces" is in progress, with
phase .4 open, and `staged_handoffs` is not default-on.

### 5.2 The Human Opt-Out Became Theater

Only epic 1 shows "Reviewer decisions … reviewer via ACE." Epics 2–5 show "Auto
decisions … **no human reviewed this plan**," because the lander launch prompt includes
`%auto` and approves its own continuation.

- **Epic 2's** auto-approved decisions included real product changes. For example,
  `claude_tools = inbound_and_async` removed ListAgents, Workflow, Monitor, Cron\*, and
  RemoteTrigger from every SASE Claude agent.
- **Epics 3–5** carried one placeholder decision, `optional_scope = keep_five_seeds`. It
  existed to satisfy the prompt's "give the owner a way to opt out" rule, but
  auto-approval meant you never saw it.

### 5.3 The Chain Broke Master for Other Agents

These are athena full-run records containing the node; the counts include runs with many
failures:

| Regression                                                                                   | Introduced by                                           | Full-run records failing                 |
| -------------------------------------------------------------------------------------------- | ------------------------------------------------------- | ---------------------------------------- |
| `test_fix_routes_generated_docs_to_their_declared_venvs` (Ruff stub vs the pinned toolchain) | Epic 2 phase .4 (995c451c38)                            | 13 on 10-29                              |
| `test_contract_manifest_matches_marker_selection` (manifest collision with d97902c0df)       | Epic 2 integration (partly pre-existing under sase-1pi) | 42 on 10-29, 23 on 10-30                 |
| `test_suite_gate_scoped_integration` (missing helper in the mini-repo copy list)             | Epic 3 phase .3 (fd8882c6af)                            | 26 on 10-30, also Full CI on py3.12–3.14 |
| `test_every_value_slot_is_kinded…` (new state-repair CLI slots)                              | Epic 3 phase .5                                         | 14 on 10-30, also a Master Gate red      |
| `test_tui_app_import_stays_under_startup_budget`                                             | Epic 1's "fix" didn't hold; epic 5 overran epic 4's cap | 35 after epic 1's close, 3 from epic 5   |

Over the chain window, 87 of 334 athena full-run records included at least one of these
nodes. Some import-budget and manifest failures predate the chain, so not all 87 are
chain-caused. Other agents found most of these and recorded them as DISCOVERED ISSUEs on
the epic. Phase checks are scoped, and each phase worked in isolation, so cross-cutting
guards (contract manifest, kind coverage, import budget, mini-repo copy lists) only
failed once the changes merged.

### 5.4 Large Seeds Turned Batch Epics Into Feature Epics

Ranking "by fleet-wide cost first, then by cost to fix" let a large, design-shaped bead
into a batch of quick fixes. sase-1cb (a new pre-push rebase gate) and sase-1cc (a
published run-state convergence subsystem) each became a nested epic. sase-1cc became an
epic inside an epic. Each set its batch's wall time, and in a serial chain that sets the
whole chain's pace.

### 5.5 Smaller Issues

- **Two chains at once.** The same prompt was launched on 10-26 and again on 10-29. The
  second chain's planner had to exclude seeds the first chain owned (sase-1a7), and the
  first chain had to hand its continuation over.
- **Re-triage cost with no yield.** See §3: one closure in four full re-lists.
- **Stale claims.** See sase-j0 in §3.1.
- **Closed-as-done while code is missing.** This recurred in epic 5 even though the
  first chain had worked sase-yo ("never leave a bead closed as done when its turn's
  commit never lands"). Landers close task beads directly, before host-owned commits
  land.

---

## 6. What Went Well (Keep These)

- **Seed selection improved over the run.** By epic 5, the lander ranked by objective
  recurrence in full-run records, excluded runs with many failures and failures in a
  run's own changed files, and re-checked candidates on the host that shows the failure.
  That surfaced the apollo-only prompt-render cluster (sase-1ia, 1l3, 1hy), which
  earlier landers had skipped because it passes on athena.
- **"Rules for every phase"** (from epic 4 on): reproduce first; no skips, timeouts, or
  budget raises; sase-core boundary; before/after evidence. Epic 4 ran five large phases
  with an 18-minute landing.
- **Phase workers don't create or close task beads.** Proposed follow-ups went to the
  lander, which used `/sase_new_task`. The chain created only 5 new tasks across five
  epics (sase-1po, 1pp, 1pq, 1pr, 1qu) and routed the rest to existing beads or active
  epics instead of adding to the backlog.
- **Integration review.** Each lander reviewed the drift on master since its epic
  started (for example, about 100 non-epic commits for epic 3) and found the real
  collisions.
- **Small and medium seeds finish within hours, in parallel.**

---

## 7. Options Considered

| Change                                                                                         | Benefit                                                              | Cost                                                                                                | Verdict                                                                      |
| ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Lander writes and validates the next plan as a **draft** and finishes normally; you propose it | Removes the lost-work vector. Gives you a review checkpoint per epic | One manual step per epic, minutes of latency                                                        | **Adopt.** Matches what the redo tale already did (`defer_to_owner`).        |
| Keep auto-propose but turn on `staged_handoffs` for chain agents                               | Fully autonomous chain                                               | Beta flag; the epic-5 loss came from a gate-turn claim failure that sase-1pj.7.1 hasn't fully fixed | Revisit after sase-1pj.7.1 closes and `staged_handoffs` is default-on.       |
| Restrict scope to defect types (bug, flake, ci)                                                | A stop condition that can be met; no placeholder decisions           | Feature and memory beads need a separate review                                                     | **Adopt**, and add a one-time feature/memory review (§8.3).                  |
| Cap seed size (no nested epics in the chain)                                                   | Predictable batches that finish in hours                             | Design-shaped defects need their own epic                                                           | **Adopt.** List them as "needs its own epic" for you.                        |
| Explicit stop rule (K epics, or nothing above a cost threshold)                                | Bounded spend; a summary report at the end                           | The chain stops before the backlog is empty                                                         | **Adopt.**                                                                   |
| Full duplicate/obsolete sweep only at chain start                                              | Saves a 385-bead re-list per lander                                  | Some duplicates found later                                                                         | **Adopt.** Landers re-verify only the candidates they pick.                  |
| Dormant-flake policy as a real owner decision                                                  | Lets the backlog actually shrink                                     | A wrong close is reopened by a later +1                                                             | **Ask once** at chain start (the first chain used `dormant_flakes = close`). |

---

## 8. Recommendations

### 8.1 Change the Prompt

Save the prompt as a project macro so it is versioned rather than pasted. Suggested
text:

```text
#gh:gh_sase-org__sase You are starting a task-bead backlog chain for this project.

Before planning:
- If an open epic titled "Task backlog epic N" (or any other backlog chain) exists,
  stop and report it instead of starting a second chain.
- Do one full duplicate/obsolete sweep of non-closed task beads. Close only verified
  duplicates (resolution superseded, naming the canonical) or obsolete beads
  (resolution done, citing the fixing commit, a grep, or a passing focused test).
- Treat an in_progress task whose holder agent is no longer running as unowned.
- Ask me, as a plan decision, whether to close flakes with no full-run recurrence and no
  +1 in the last 30 days as canceled (a later +1 reopens them).

Scope and ranking (copy this block verbatim into every epic's Landing section):
1. Seeds are defect tasks only: task types bug, flake, ci, and untyped beads that
   describe a defect. Never seed feature, memory, or flag beads.
2. Rank by recurrence in the selection-health full-run records over the last 14 days
   (runs with at most 5 failures; ignore failures inside a run's own changed files),
   on every fleet host. Then rank by security/data-loss risk, then +1 corroboration,
   then cost to fix. Re-run each candidate at the current tree before choosing it.
3. At most 5 seeds and 5 phases. Every seed must be fixable by one phase, with no
   nested epic. A defect that needs a design or a multi-phase epic is not a seed: list
   it under "Needs its own epic" in the plan for me.
4. Add plan decisions only for real choices I might answer differently. No placeholder
   decisions.
5. Phases follow "Rules for every phase": reproduce first; no skips, xfails, timeout or
   budget raises; shared backend in sase-core; before/after evidence; run the
   cross-cutting guards your change can affect (contract manifest, completion kind
   coverage, TUI import budget, scoped suite-gate integration).
6. Landing: verify, integrate drift, close seeds, triage follow-ups, mark the plan done.
   Then, unless the stop rule below applies, write the next epic as a draft plan under
   ~/.sase/plans/<YYYYMM>/, validate it with `sase plan validate`, record its path on
   the epic bead, and finish normally with /sase_final. Do NOT run `sase plan propose`
   or /sase_plan from a landing turn. I will propose the draft.
7. Stop rule: write a chain summary note instead of a next epic when (a) this was epic
   <K>, or (b) no remaining defect has a full-run recurrence in 14 days or 3+ +1s, or
   (c) the non-closed defect count has not fallen over the last two epics.

Create the first epic plan with /sase_plan now. %m:@xlarge
```

Choose `<K>` to fit your budget. I suggest **3**, then reassess with a summary. This
run's five epics cost 160 agent runs and several check runs of 38–108 minutes.

### 8.2 Process Settings

- **Keep a human on every epic.** Under step 6, the lander drafts and you propose, which
  also gives you a per-epic review in a few minutes. If you want an unattended chain
  later, re-enable lander proposals only after sase-1pj.7.1 has landed and
  `staged_handoffs` is default-on. Even then, require that the proposal come from a turn
  whose tree is already clean.
- **Keep the xhigh lander.** It is the chain's quality gate (§2.3).
- **Run one chain at a time.** Step 0 of the prompt enforces this.

### 8.3 Housekeeping Before the Next Run

1. **Plan status.** Set `status: done` on `202610/task_backlog_epic_1.md`,
   `202610/task_backlog_epic_2.md`, `202610/finish_task_backlog_epic_2.md`,
   `202610/task_backlog_epic_3.md`, `202611/task_backlog_epic_4.md`,
   `202611/redo_1qt_landing.md`, and (first chain)
   `202610/backlog_epic_top_five_task_beads.md`. Their epics are closed, but the
   landers' status edits were lost (§5.1).
2. **sase-j0** (+38, holder dead since at least 10-26). Either release it into the next
   ranking or split it. It is the most-corroborated open defect.
3. **The epic-6 draft** on athena (`~/.sase/plans/202611/task_backlog_epic_6.md`, seeds
   sase-1oy, 1em, zo, 1pw, 1ce) is still a good seed list. But its Landing section
   carries the old "propose it last" step. Either regenerate it with the new prompt, or
   replace its continuation block with §8.1 steps 6–7 before you propose it.
4. **Feature and memory beads.** Review the 100 feature and 30 memory beads once,
   separately: a questions round with keep/cancel per bead, or one triage agent that
   proposes cancellations for you to approve. The chain cannot reach them by design.

---

## Sources

- **Epic beads, read with `sase bead read`:** sase-1pm, sase-1pn, sase-1pu (and nested
  sase-1pu.5.1, sase-1pu.5.1.4, sase-1pu.5.1.5), sase-1qn, sase-1qt, and the first-chain
  epics sase-1oh and sase-1ou. Also all 24 seed and related task beads, phase beads for
  every epic, sase-j0, and sase-1pj.7.1.
- **Plans, in the sase--plans sidecar:** `202610/task_backlog_epic_{1,2,3}.md`,
  `202610/finish_task_backlog_epic_2.md`, `202611/task_backlog_epic_{4,5}.md`,
  `202611/finish_1qt_landing.md`, `202611/redo_1qt_landing.md` and its
  `.plan-decisions.json`, `202610/backlog_epic_{,2_}top_five_task_beads.md`, and their
  frontmatter on origin/main at 13b003818. Also the athena epic-6 draft.
- **Transcripts, on athena, read-only over Tailscale SSH:** `15r--plan`, `14m--plan`,
  and the sase-1qt lander relaunch.
- **Agents sidecar, origin/main at aff8b7b93b:** per-agent `meta.json` and `state.json`
  for 160 chain agent runs.
- **Task tracker:** `sase bead list -t task -s all -n 0 -f json` (1,386 task beads) for
  backlog counts, composition, and window inflow/outflow.
- **Selection-health:** athena full-run records
  `~/.sase/test-selection/gh_sase-org__sase/*-full-run.json` (1,321 records), for
  before/after recurrence and the chain-caused master-red counts.
- **Feature flags:** `sase flag list` (`staged_handoffs`: beta, default off).

**Limits.**

- Token and dollar costs for each agent were not available on apollo. Agent-run counts
  and check durations stand in for cost.
- The full-run records are athena-only, so apollo-only failures (such as the
  prompt-render cluster) are invisible to them.
- The post-fix windows are 1–4 days.
- Backlog counts at past times ignore reopen intervals; I used the landers' reported
  counts where they exist.
