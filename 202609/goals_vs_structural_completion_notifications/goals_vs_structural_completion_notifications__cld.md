# Goals vs. outcome-shaped notifications: should SASE keep building Goals?

_Researcher cld · 2026-09-28 · project: sase · sase `52a18073e4`_

**Question.** Is Goals (roadmap G1–G6, epic `sase-1bu`) worth continuing? If its main
payoff is "only notify me when work I asked for is done," could xprompt swarms and agent
clans just be customized to send one completion notification?

**Method.**

- **Plan and design.** I read the roadmap
  ([`research:202609/sase_goals_epic_roadmap/sase_goals_epic_roadmap.md`](sase_goals_epic_roadmap/sase_goals_epic_roadmap.md)),
  the design
  ([`research:202609/sase_goals_design/sase_goals_design.md`](sase_goals_design/sase_goals_design.md)),
  the first-round synthesis
  ([`research:202609/goal_outcomes_and_verification/goal_outcomes_and_verification.md`](goal_outcomes_and_verification/goal_outcomes_and_verification.md)),
  the `sase-1bu` bead and its land notes, and your original Goals prompt (the
  `research.2m.final` transcript on athena).
- **Code at HEAD.** I traced the completion-notification path and the swarm, clan, epic,
  and lineage metadata.
- **Traffic.** I classified one week of real notification traffic from athena's store,
  plus four weeks from apollo's.
- **Independence.** I did not consult any other report from this swarm.

---

## 0. Bottom line

**Don't press forward with G2–G6 now.** Let the in-flight G1 landing fixes
(`sase-1bu.8`) finish, then pause Goals. Build a small **host-side "outcome-shaped
completion" policy** first. It is your idea, implemented at the single notification
choke point instead of per xprompt.

Last week on athena that policy would have cut success pings by about **70%**, from 883
to about 245 per week. That matches or beats the Goals end state (about 310 claims per
week, from the design's own outcome count) in days rather than weeks. It needs no new
store, no per-turn tax, no model judgment, and no new daily verification chore.

Resume Goals only if one of the explicit triggers in §8 fires. If it does, use a trimmed
scope that drops universal drafts and adoption (G4).

Three findings drive this:

1. **The notification win does not need a Goal object.**
   - About 70% of success pings come from agents whose "I'm not the outcome" status the
     host already knows from structure:
     - epic phases: 49%;
     - swarm researchers: 12%;
     - other fan-out clan members: 11%.
   - Epics, clans, and sessions already record who is terminal. The design rejected
     "claims without goals" because a researcher or a phase worker can't know the group
     outcome is done (design §1). The host can, from clan and epic metadata, without a
     goal.
2. **The other value claims are real but unproven, and each has a cheaper test.**
   - The inventory of intent can be tried today with G1's manual `sase goal new`.
   - Verify/reject records can come from a one-field outcome flag on the final
     declaration.
   - Nothing in the evidence shows you are feeling those pains now. SASE's own decision
     record `corpus-before-mechanism` says to wait for that evidence.
3. **The costs of G2–G6 are mostly ownership costs, not build time.**
   - **Scope.** The remaining program touches every launch path (about 14), adds a
     required finalizer to every turn, and adds a gate kind, a top-level tab, and two
     model-judgment loops (naming/adoption and claim honesty).
   - **G1 as a sample.** G1 alone added about 19k lines across sase and sase-core
     (including tests). Its land audit reproduced **18 defects** plus a 7× miss on the
     warm-list latency target. That is the cheapest, most deterministic slice of the
     program.

---

## 1. Where things stand

- **G1 is essentially built.** `sase-1bu` was created 2026-09-27 19:03. All 7 phases are
  closed. It delivers:
  - the event ledger with `live/` markers;
  - the hidden-clone sync;
  - `sase goal new|list|show|edit|drop|reopen|merge|doctor`;
  - the `goal:` artifact kind.
- **Size of G1 so far.** It is about 7.4k inserted lines in five sase commits and about
  12k inserted lines in five sase-core commits. The sase-core count includes tests and
  the core-fixes commit `32d80d6`.
- **G1's landing child epic, `sase-1bu.8`, is in progress.** It fixes the 18 defects,
  for example:
  - `edit`/`drop` of an unknown id creates a phantom active goal;
  - uppercase ids fork `items/<ID>`;
  - one corrupt event aborts `list`/`show`/`doctor`;
  - `edit -x N` silently does nothing.

  The warm-list miss (p50 about 37 ms against a 5 ms contract) is filed separately as
  `sase-1c3`.
- **Nothing binds agents to goals yet.** There is no `%goal` directive, and
  `docs/goals.md` says "binding is a later epic." Today G1 is a manual ledger that only
  humans can write.
- **What remains:**
  - G2 (6 phases), G3 (7), G4 (6), G5 (6), and G6 (4): about **29 phases**;
  - a pre-task bug;
  - a soak of at least 7 days before the G6 attention cutover.

  The attention payoff you actually want arrives last, in G6.

Your original request (2026-09-26) asked for more than notifications:

- prompt linkage;
- "all agents MUST have a goal";
- evidence-backed closure;
- a Goals panel;
- cross-machine access.

It named notifications as "**one** motivation": _"I really only need to be alerted when
my agent claims that a goal which was set is now complete."_ So the honest version of
your current question is: which of the other motivations still justify the program if
notifications can be solved without it? §2 answers that.

---

## 2. Is notifications the only value-add?

Not in the design's framing. It lists four values (design §1), and the program implies
two more. For each value, this table compares what exists today, the cheapest
substitute, and what only Goals would add.

| Value Goals claims | What already exists | Cheapest substitute | What only Goals adds | My read |
| --- | --- | --- | --- | --- |
| **1. Attention matches outcomes** | One ping per agent run. Pipe, plan-approval, and in-process question successors already collapse to one ping per session. Monitor/gate handoffs are skipped. The epic planner's ping is folded into the launch. | Outcome-shaped completion policy (§4) | "Done" judged by the agent rather than by structure; adoption across unrelated launches | **About 80–90% of the benefit, cheaply** |
| **2. Definition of done up front makes agents better** | Tale/epic plans require `goal:`. Epics have frozen DoDs. Land agents write detailed LAND VERIFICATION notes (see `sase-1bu` note #3). | Nothing needed for plan-bound work (about 41% of runs are epic-bound) | A one-line DoD for ad-hoc turns | **Unmeasured, probably small.** Plan-bound work already has one. |
| **3. Inventory of intent** ("what am I trying to get done?") | Agents tab (clans, tribes, sessions); in-progress epics via beads; plans | **G1 already ships a manual `sase goal new/list`.** Use it by hand for two weeks. | A durable, cross-machine list of open asks that survives dismissal | **Plausible, unproven.** It is the cheapest thing to test, because the tool exists. |
| **4. Continuity** (follow-ups and rejects accumulate on one object) | Sessions, pipes, follow-up prompts to the same agent, clans | — | Cross-day follow-ups linked by `follows`, and reject-and-relaunch | **Small for a solo user.** Most continuity already rides sessions and clans. |
| **5. Verified-outcome record** (verify/reject plus evidence) | Land notes, research syntheses, receipts. Dismissing a row is the only "state." | An optional `outcome` field on the `sase_final` declaration, plus one "check it" line in the ping (§5) | An explicit human-verdict history; per-model claim-precision stats | **Real, but** it turns passive pings into roughly 30 decisions a day (the design's estimate) |
| **6. Cross-machine visibility** | Remote Attention relays questions and gates only. `%dispatch` completions stay in the remote host's inbox. | Relay loud outcome pings from dispatched agents through Remote Attention | A shared ledger of open asks | **A real gap with a small fix** |

**Verdict.** Notifications are the only value with evidence of current pain behind it.
You wrote that you use completion pings and unread dots as your to-verify list, and they
are noisy. The other values are either already partly served (2 and 4), cheaply testable
(3 and 5), or a small gap (6).

---

## 3. The traffic: where the pings come from

**Athena, all notifications, 2026-09-21 12:42 → 2026-09-28 12:42.** That is 2,007 rows,
about 287 per day.

| Source | Rows / week | Share |
| --- | ---: | ---: |
| Agent success completion (`JumpToAgent`, `done`) | **883** | 44% |
| Remote Attention: gates relayed from apollo (sampled notes are task-bead titles) | 326 | 16% |
| Bead `TaskTriage` | 288 | 14% |
| `wait_checks` blocked-dependency | 97 | 5% |
| Agent failure (`ViewErrorReport`) | 96 | 5% |
| `epic-launch` | 71 | 4% |
| `PlanApproval` / `EpicApproval` | 67 / 37 | 3% / 2% |
| Everything else (axe errors, file-hooks, ci_watch, …) | about 140 | 7% |

**The 883 success pings, by agent shape.** I classified them by name shape:
`<bead>.<n>` is an epic phase, `.land` is a lander, and `research.<x>.<model>` is a swarm
researcher.

| Shape | Pings | Share | Already knowable by the host as "not the outcome"? |
| --- | ---: | ---: | --- |
| Epic phase agents (about 104 epics) | 435 | 49.3% | **Yes.** Phases carry `phase_bead_id`, and the lander is `<epic>.land` (`_is_land_agent_name`, `agent/bead_display.py:115`). |
| Epic land agents | 79 | 8.9% | These *are* the outcome. |
| Research swarm researchers (32 swarms) | 109 | 12.3% | **Yes.** They are members of a clan whose `.final` member `%wait`s on them. |
| Swarm lead or tail (`.final`, `.image`, `.critique`) | 41 | 4.6% | The last one per swarm is the outcome. |
| Other clan fan-outs (mostly `toobig-*` file-split clans, 13 clans) | 97 | 11.0% | **Yes.** They are clan members; only the clan's terminal completion matters. |
| Routine (`chop.*`) runs | 9 | 1.0% | Yes (`chop_*` metadata) |
| Standalone agents (questions, `/sase_run` children, ad hoc) | 113 | 12.8% | No, and they shouldn't be: these are usually exactly what you asked for |

**Rough simulation of the policy in §4:**

- phases go to 0, and landers keep their 79;
- each of the 32 swarms produces 1 ping;
- the other clans produce about 20;
- routines produce 0;
- the 113 standalone pings stay.

That is about **245 pings a week, roughly 35 a day, a cut of about 72%**. The design's
Goals end state is about **310 outcomes a week, one claim each**, plus quiet Idle notices,
with PlanApproval unchanged. On raw volume, the structural rule lands at or below Goals.

**What remains noisy after either approach:**

- **Task-triage traffic** is now the largest single stream: local `TaskTriage` plus the
  relayed apollo triage gates come to about **614 a week (about 88 a day)**.
- Goals does nothing for it.
- Once completions are fixed, they fall to roughly 18% of notifications, and triage
  becomes about 45%.
- If attention is the real problem, triage is the next target, and it is not
  Goals-shaped.

**Caveats.**

- Name-shape classification is heuristic; a few `toobig-*` members probably fall in the
  wrong bucket.
- The 310-outcomes figure comes from the design, not from my own classification.
- Apollo shows the same pattern at lower volume: 468 success pings in 4 weeks, against
  723 `TaskTriage` rows.

---

## 4. Can swarms and clans do this? Yes, at the host rather than per xprompt

### 4.1 Today's plumbing (verified at HEAD)

- **One choke point.** Every user-agent success ping is built in
  `send_completion_notification()` (`axe/run_agent_runner_finalize.py:309`) and
  published through `send_completion_payload()`.
- **Existing gates:**
  - Killed runs, `%repeat` STOP-skips, and all-hidden-step runs are skipped
    (`run_agent_runner_lifecycle.py:382`).
  - The outcomes `plan_rejected`, `monitored`, and `gated` are skipped
    (`finalize.py:39-41`).
  - `%hide` makes the row `silent` (`finalize.py:468`).
  - `epic_approved` is deferred and folded into the epic-launch notification
    (`finalize.py:471-475`).
- **Nothing gates on clan, tribe, swarm, epic role, or `%wait`.**
- **Config can't do it today.**
  - `ace.notification_rules` only changes toast and sound. The row is still stored,
    still counts as unread, and still reaches Telegram.
  - `%hide` silences the ping but also hides the Agents row by default, and silent rows
    still light the ✅ unread dot (`_notification_unread_projection.py`).
  - Adding `%hide` to researcher segments would be a crude hack, not a fix.
- **The building blocks exist:**
  - `agent_meta.json` records `agent_clan` and `agent_clan_generation`
    (`agent/clan_membership.py`), `wait_for`, `phase_bead_id`, `epic_bead_id`, `chop_*`,
    `agent_session`, `piped_from`, and `turn_kind`.
  - `find_agent_clan()` and `is_agent_clan_complete()` live in
    `agent/names/_lookup_groups.py:297`.
  - `upsert_notification(dedup_key=…)` provides idempotent emission
    (`notifications/store.py:200`).

### 4.2 Why do it at the host and not by customizing each swarm

Per-xprompt customization (marking which segment should ping) would work for the
research swarm, but it has three problems:

1. **It misses the largest bucket.** Epic phases are 49% of pings, and their prompts are
   generated by `bead/work_prompt.py`, not written as swarms.
2. **It depends on conventions the code doesn't enforce.**
   - `.final` is a naming convention only.
   - The member that declares the clan is not always the lead (in `sase/xprompts/reads.md`
     the first member declares it).
   - When the research swarm's optional `image`/`critique` members run, `.final` is not
     the last agent.
3. **It repeats per xprompt,** where a host rule covers every clan once.

A host rule keyed on **clan terminality** avoids all three. The outcome ping is sent by
whichever member finishes last.

### 4.3 The policy, as a truth table

The rules apply in order, and the first match wins:

| # | Condition | Success ping |
| --- | --- | --- |
| 0 | The run failed | **Loud.** Unchanged `ViewErrorReport`. |
| 1 | `%notify` on the launch (new per-launch override) | Loud |
| 2 | `phase_bead_id` set (an epic phase) | **Quiet** |
| 3 | Clan member, and some member of the same clan generation is still non-terminal (waiting, running, or queued) | **Quiet** |
| 4 | Clan member, and it is the last to reach a terminal state | **Loud, once per clan generation.** Use `dedup_key = clan:<clan>:<gen>`. The note says "research.k: 5/6 done, 1 failed" and jumps to the terminal member. |
| 5 | Routine run (`chop_*`) | Quiet (configurable) |
| 6 | Everything else: standalone, `/sase_run` child, session end, land agent without a clan | Loud (today's behavior) |

**Design details:**

- **What "quiet" means.** Write the row `silent` **and** already dismissed. History is
  kept, but there is no ✅, toast, bell, mobile push, or Telegram message. The clan's
  gold unread pip is driven by the one loud terminal row.
- **Terminality.**
  - It must mean "done *or* failed," not `AgentClan.is_complete`, which means *all
    members succeeded*.
  - The terminal check runs after the member writes its own `done.json`. That write
    happens in `run_agent_exec_finalize.py`, before shutdown, so the last finisher sees
    a complete clan.
  - The dedup key absorbs the race where two members finish at once.
- **A failed researcher leaves the lead parked.**
  - The lead's `%wait` needs a successful `done.json`.
  - The failure ping (rule 0) is the signal.
  - The clan's terminal ping arrives only once you resolve it.
  - This is the same as today, minus the success noise.
- **Epic landers need no special rule.**
  - The land agent is a member of the `<epic>` clan and finishes last, so rule 4 makes it
    loud.
  - A lander that plans a child epic already goes through the `epic_approved` fold.
  - The child epic has its own clan and its own `.land`.
- **Knobs:**
  - `ace.completion_notifications: outcomes | all`, with `outcomes` as the default and
    `all` as the escape hatch;
  - the `%notify` directive.

  Both need updates to `default_config.yml`, the schema, and the docs.
- **The Rust boundary.** Keep the decision as a pure function over metadata
  (`completion_attention(meta, clan_snapshot) -> loud | quiet`). If mobile or a web
  frontend ever needs to reproduce it, move it into sase-core under the
  `rust_core_backend_boundary` rule.

**Estimated size.**

- The runner filter plus clan-terminal emission is roughly 100–250 lines in one module
  plus tests.
- The `%notify` directive touches about 6–8 files.
- That is one large tale or a 3–4-phase epic.
- It lands in days, verified by a truth-table test plus one week of before/after counts
  from the same store I used here.

### 4.4 Gaps this policy leaves

| Gap | Size | Cheap fix |
| --- | --- | --- |
| Swarms or multi-agent prompts **without** a clan have no persisted group id (`template_group` is never saved) | Small. The research swarm, epics, and `toobig` all use clans. | Make xprompt swarms and `---` fan-outs auto-declare a clan, or persist a swarm invocation id |
| `/sase_run` children have no lineage (`parent_agent_name` is read but never written) | Small. They ping loudly, which is usually right, since the requester has already ended its turn. | Write `parent_agent_name` at LaunchApproval. The roadmap calls this "a real Agents-ancestry bug" either way. |
| The terminal agent may finish without the outcome being done (a question needing clarification, a lander leaving remainders) | Unknown. Measure it. | Option C (§5): the agent declares `outcome: done | progress | needs_you` |
| `%dispatch` completions stay on the remote host | Real, and independent of Goals | Relay the *loud* rows through Remote Attention, which already relays gates and questions |
| Stalled work (for example an epic whose phases all closed but whose land never finished) goes quiet | Moderate. The roadmap counted 65 of 98 in-progress epics waiting to land. | `wait_checks` already pings blocked dependencies. An "idle clan" digest is a small add-on and would be the equivalent of Goals' Idle lane. |

---

## 5. This removes the design's main argument against "claims without goals"

The design and the roadmap considered a per-agent "needs your attention: yes/no plus
evidence" flag without a Goal object. They rejected it because it "fails exactly where
the noise is worst. A researcher can't know the synthesis is done, and a phase worker
can't know the epic is done."

That objection assumes the *agent* must decide who is terminal. With §4, the **host**
decides who may ping, from structure it already records. The agent then only answers a
question it *can* answer: "is what I was asked for done?" The two together are **option
C**:

- Add an optional `outcome` field to the `sase_final` declaration (`done`, `progress`,
  or `needs_you`) and a single "check it" line.
- The host uses them only on pings that §4 already makes loud:
  - `done` stays loud and carries the check-it line;
  - `progress` becomes a quiet "still going" note;
  - `needs_you` stays loud and is tagged as such.
- The cost is one finalizer-context wire change in sase-core, which is breaking because
  the wire is `deny_unknown_fields`, plus the skill text.

C delivers most of G3's user-visible benefit ("tell me what to verify, and how") without:

- the ledger;
- binding on 14 launch paths;
- drafts, naming, or adoption;
- a new gate kind;
- a new tab.

Build it only if §4's loud pings still include too many not-actually-done outcomes.

---

## 6. What pressing on with G2–G6 would cost

1. **Ownership cost, not build time.**
   - The fleet builds fast: G1 went from creation to "all phases closed" in about 17 hours.
   - What lingers is the surface. G1 alone added about 19k lines for a manual ledger, and
     it needed an 18-defect remediation epic.
   - G2–G6 go wider:
     - G2 changes resolution on every launch path;
     - G3 adds a finalizer that runs on **every turn** (the roadmap rightly makes it fail
       open);
     - G5 adds a top-level tab that is the program's only golden churn (the Artifacts
       scaffold re-blessed 179 PNGs).
2. **Two non-deterministic loops.**
   - Claim honesty (G3) and name-vs-adopt judgment (G4) cannot be proven by tests. That
     is why the roadmap needs a soak of at least 7 days and six metric thresholds before
     G6.
   - A wrong adoption corrupts provenance: the design itself says "a wrong merge is worse
     than a duplicate."
3. **A new daily chore.**
   - Goals turns "dismiss a ping" into Verify, Reject, Drop, or Acknowledge, for about 30
     user-level outcomes a day.
   - The design already plans for Review-lane rot with a "stale-review lapse" flavor and
     Idle aging.
   - The verdict history pays off only if someone reads it later. Mostly that means
     claim-precision stats, which measure the feature itself.
4. **A per-turn tax.**
   - Every one of about 2,000 turns a week carries a goal line (about 40 tokens).
   - Every draft turn also pays for an intake block (about 80 tokens) and a
     `sase goal list`/`name` call before doing any work.
   - The dollars are small. The latency, and the new way for a turn to go wrong, are
     not.
5. **Your review bandwidth.**
   - That is five more epic plans to approve and five landings to verify, while landing
     is already the bottleneck.
   - The roadmap counted 65 of 98 in-progress epics waiting to land.
6. **It aims at the smaller share of the noise.**
   - After §4, completions are about 18% of notifications.
   - Triage (about 88 a day) is untouched by Goals.

**The steelman for continuing:**

- You asked for more than notifications.
- G1 is already paid for, and the `goals-host-binds` and `goal-ledger` decisions are
  accepted.
- Structural heuristics can't handle cross-launch adoption.
- Per-model claim-precision data would be genuinely new.

All true. None of it requires committing to G2–G6 *today*:

- The §4 policy doesn't foreclose Goals.
- It is essentially the measurement baseline that G6's start gate needs anyway (shadow
  coverage of success pings).
- If Goals later proceeds, only the clan-terminal code (about 150 lines) becomes
  redundant when G6 silences all successes.

---

## 7. Options

| Option | Build cost | Attention outcome | Other value | Risk |
| --- | --- | --- | --- | --- |
| **A. Continue the roadmap (G2–G6)** | About 29 phases plus a soak of at least 7 days. Touches every launch path and every turn. | About 310 claims a week, after about 3–4 weeks | Inventory, verdict record, continuity | High: two model-judgment loops, blast radius, a daily chore |
| **B. Outcome-shaped completion policy (§4)** | 1 large tale or a 3–4-phase epic; one choke point | **About 245 pings a week, within days** | None beyond attention | Low: a fail-safe `all` mode |
| **C. B plus a declared `outcome` flag (§5)** | B plus one finalizer wire change and skill text | Loud only when a terminal agent says "done" or "needs you," with a check-it line | Most of G3's "what to verify" | Low to medium |
| **D. Goals-lite: G2 (deterministic binding) + G3 + G5, skip G4** | About 19 phases | Same as A for plan, epic, and explicit `%goal` work | Inventory of plan-bound work, verdict record | Medium: needs a successor to the `goals-host-binds` decision (not every turn gets a goal) |
| **E. Stop now and remove G1** | A cleanup epic | — | — | Wastes a finished asset and forecloses the cheap test of value 3 |

---

## 8. Recommendation

**Pause Goals after G1's landing fixes. Build option B now, and C only if B's data asks
for it. Re-decide Goals in about two weeks against explicit triggers.**

1. **Let `sase-1bu.8` land.** It fixes known correctness bugs (phantom goals, id forks,
   and so on) in code already on master, and its core commit is already in. Leaving
   known-broken commands on master is worse than finishing the fix. Then **don't write
   the G2 plan.**
2. **Build B,** the outcome-shaped completion policy:
   - quiet epic phases;
   - one loud ping per clan generation from its last finisher;
   - failures always loud;
   - `%notify` and `ace.completion_notifications: outcomes | all`;
   - "quiet" means silent **and** pre-dismissed, so no ✅.

   Verify it with the §4.3 truth table and a before/after count from the notification
   store.
3. **Fold in the cheap gaps as separate small tasks:**
   - write `parent_agent_name` at LaunchApproval;
   - make swarms and fan-outs always carry a clan;
   - optionally relay loud `%dispatch` outcome pings through Remote Attention.
4. **Point the next attention effort at triage.** It is about 88 pings a day, now the
   largest stream, and Goals doesn't touch it.
5. **Test the inventory claim for free.** For two weeks, when you catch yourself wanting
   to remember an ask, run `sase goal new` by hand. G1 already supports it.
6. **Resume Goals if any of these triggers fires:**
   - **(a)** After B, success pings stay above about 50 a day, or you log more than a
     handful of "pinged for a non-outcome" cases a week that need *agent* judgment.
     Try C first; go to Goals only if C isn't enough.
   - **(b)** You log cases where B silenced something you needed that structure can't
     express. This usually means cross-launch continuity.
   - **(c)** You actually used the manual ledger: roughly 10 or more hand-made goals, and
     you kept checking `sase goal list`. That means the inventory is valued.
   - **(d)** A second person starts working on these projects and needs a shared list of
     open asks.

   If a trigger fires, resume with **option D's scope**. Claims and the tab would be
   proven on plan-bound and explicit-`%goal` work first. Universal drafts, naming, and
   adoption (G4) would be a separate later decision, because G4 carries the most model
   judgment and the per-turn tax for the least-evidenced value.
7. **If no trigger fires,** archive the roadmap. Then either keep G1 as a small manual
   tool or file a cleanup to remove it.
   - If you drop the universal-binding invariant, record that through
     `/sase_memory_write`: supersede `goals-host-binds` rather than editing it.
   - The same applies if you decide against Goals altogether.

**Direct answer to your question:** yes. Structure-aware notification filtering gets you
most of what Goals promised for attention. Do it at the host, keyed on clan terminality
and epic phase/land role, not by customizing individual swarms. Goals' remaining value
(inventory, verdict history, cross-launch continuity) is real but unproven for how you
work today, and it is cheap to test before paying for about 29 more phases and the
permanent per-turn and review costs.
