# Goals vs. structural completion notifications: should SASE keep building Goals?

_Lead synthesis · 2026-09-28 · project: sase · sase `77438b4ef`_

**Question.** Should SASE press forward with Goals (the G1–G6 roadmap, epic `sase-1bu`)?
If the only value-add is better notifications — being pinged only when work you asked
for is complete — couldn't xprompt swarms and/or agent clans just be customized to send
a completion notification for certain agents only?

**Sources.**

- **Five independent reports:** [cdx](goals_vs_structural_completion_notifications__cdx.md),
  [cld](goals_vs_structural_completion_notifications__cld.md),
  [grk](goals_vs_structural_completion_notifications__grk.md),
  [mus](goals_vs_structural_completion_notifications__mus.md), and
  [gem](goals_vs_structural_completion_notifications__gem.md), all read through
  `sase artifact read`.
- **The plan being judged:**
  [`research:202609/sase_goals_epic_roadmap/sase_goals_epic_roadmap.md`](../sase_goals_epic_roadmap/sase_goals_epic_roadmap.md)
  and its design,
  [`research:202609/sase_goals_design/sase_goals_design.md`](../sase_goals_design/sase_goals_design.md).
- **Beads:** `sase-1bu` (G1) and its landing child `sase-1bu.8`.
- **Accepted decision records:** `decisions:goals-host-binds` and
  `decisions:corpus-before-mechanism`.

**What I checked myself.** The reports disagree on several facts, so I verified these
against the code and data:

- **Epic structure.** How `sase bead work` builds an epic: its clan and its `%wait`
  edges (`src/sase/bead/work_prompt.py`).
- **Notification plumbing:**
  - the success-ping send site (`src/sase/axe/run_agent_runner_finalize.py:309`,
    `:468–469`);
  - the clan lookups (`src/sase/agent/names/_lookup_groups.py:266`, `:297`);
  - the planner-deferral module that gem cites (`src/sase/bead/epic_launch_handoff.py`);
  - delivery-rule semantics (`docs/notifications.md`, "What a rule does not change").
- **Traffic.** I classified one week of apollo's notification store, joining each
  success ping to its agent's `agent_meta.json`. cdx sampled apollo's store too, but it
  counted rows only; this is the first classification of apollo's pings by agent shape.
- **Roadmap gating.** The G6 start gate and the interim notification load.

---

## 0. Short answer

- **Is notifications the only value-add?** On paper, no. Goals also promises:
  - a verify/reject record backed by evidence;
  - an inventory of what you are trying to get done;
  - continuity across follow-ups, retries, and relaunches.

  In practice, notifications are the only one of these with evidence that you are
  feeling the pain today. The others are plausible, unproven, and each has a cheap test.
- **Could clans and swarms do it?** Yes, for the attention problem. But do it **once,
  at the host**, keyed on the structure SASE already records (clan membership, `%wait`
  edges, epic phase and land roles). Don't customize individual xprompts. On real
  traffic that cuts success pings by **58% (apollo) to 72% (athena)** within days. That
  matches or beats the Goals end state on volume.
- **Should you press forward?** **Not now.** Finish G1's landing fixes, pause G2–G6,
  build the host-side policy, and re-decide in two weeks against explicit triggers. The
  full recommendation is at the end.

---

## 1. Where things stand

- **G1 is built and almost clean.**
  - `sase-1bu` closed all seven phases between 2026-09-27 and 2026-09-28. That added:
    - the event ledger;
    - the hidden-clone sync;
    - the `sase goal` CLI;
    - the `goal:` artifact.
  - Its landing child `sase-1bu.8` has 1 of 2 phases closed, and the second is in
    progress. It fixes a long list of correctness defects: phantom goals on unknown ids,
    unstable criterion ids, one corrupt event aborting `list`, and CLI behavior that
    didn't match its help text. cld counts 18 defects.
  - The warm-list latency miss (about 38 ms against a 5 ms target) is filed separately
    as `sase-1c3`.
  - G1 is about 16–19k lines across sase and sase-core, tests included.
- **Nothing binds agents to goals yet.** Today the ledger is a manual tool that only a
  human writes to.
- **About 29 phases remain:** G2 (6), G3 (7), G4 (6), G5 (6), and G6 (4), plus a soak of
  at least 7 days.

**The finding none of the reports states outright: under the current roadmap, the
notification payoff arrives last, and the inbox gets louder first.**

- **Claims add noise before anything is silenced.** G3 turns on claims but keeps success
  pings loud. The roadmap estimates notification load at about **+15% until G6**.
- **G6 is the only epic that silences success pings, and it has a start gate** (roadmap
  §4). The gate requires all of these:
  - at least 7 days since **G4** landed;
  - at least 100 settled claims;
  - 90% shadow coverage;
  - 80% claim precision;
  - **zero unbound LLM turns**.
- **Zero unbound turns requires G4.** G4 is the universal-drafts epic: the most
  model-judgment-heavy, the most per-turn-tax-heavy, and the least evidenced part of the
  program.

So if quieter notifications are what you want, the roadmap delivers them after about 29
phases, a soak, and the riskiest epic.

mus calls G6 "the last and smallest epic," which is true of its phase count. But it sits
behind everything else, so judging the program by G6 undersells its cost rather than
overstating it.

---

## 2. Is notifications the only value-add?

The design lists four values, and the program implies two more. For each one, this
table shows what exists today, the cheapest way to test it, and what only Goals adds.
It merges the tables from cld and gem.

| Value Goals claims | What exists today | Cheapest test or substitute | What only Goals adds | Read |
| --- | --- | --- | --- | --- |
| **1. Attention matches outcomes** | One ping per run. Pipe, question, and plan successors collapse. Monitor and gate handoffs are skipped. The epic planner's ping is folded into the launch. | Host structural policy (§4) | "Done" judged by the agent, not by structure; adoption across unrelated launches | **Most of the benefit, cheaply** |
| **2. A definition of done up front** | Tale and epic plans already require `goal:`. Epics have frozen DoDs. Land agents write verification notes. | Nothing needed for plan-bound work (about 41% of runs) | A one-line DoD for ad-hoc turns | Unmeasured; probably small |
| **3. Inventory of intent** | Agents tab (processes), beads (scheduled work), plans (designs) | **G1 already ships `sase goal new/list`.** Use it by hand for two weeks. | A durable, cross-machine list of open asks | Plausible, unproven, and free to test |
| **4. Continuity** | Sessions, pipes, and clans carry most follow-ups | — | Cross-day follow-ups and reject-and-relaunch on one object | Small for a solo user today |
| **5. Verified-outcome record** | Land notes, research syntheses, receipts. Dismissing a row is the only "state." | An optional `outcome` field on the final declaration, plus a "check it" line in the loud ping (§5) | Human verdict history and per-model claim precision | Real, but it turns passive pings into about 30 decisions a day |
| **6. Cross-machine visibility** | Remote Attention relays gates and questions, but not `%dispatch` completions | Relay loud outcome pings through Remote Attention | A shared ledger of open asks | A real gap with a small fix |

**Your original request asked for more than notifications.** The 2026-09-26 prompt that
produced the design asked for:

- prompt linkage;
- "all agents MUST have a goal";
- evidence-backed closure;
- a Goals panel;
- cross-machine access.

It also said, *"I really only need to be alerted when my agent claims that a goal which
was set is now complete"* (cld). So the honest form of today's question is not "is
notifications the only value?" It is: **do you still want values 3–5 enough to pay for
them, now that value 1 can be had without them?** Nothing in the evidence shows those
pains today. SASE's own `corpus-before-mechanism` decision says to wait for that
evidence. That record is scoped to memory retrieval, but it records the same lesson,
learned three times at real cleanup cost: build the mechanism after its corpus exists.

---

## 3. Where the pings actually come from

**Two hosts, one week each.**

| | athena (cld) | apollo (mine) |
| --- | ---: | ---: |
| Window | 2026-09-21 12:42 → 09-28 12:42 | 2026-09-21 13:00 → 09-28 13:00 EDT |
| All notification rows | 2,007 | 637 |
| Agent success pings (`JumpToAgent`, `done`) | 883 (44%) | 260 (41%) |
| Task triage | 288 local + 326 relayed apollo gates ≈ 614 (31%) | 277 (43%) |
| Agent failures | 96 | 17 |

**Apollo's 260 success pings, by agent shape.** I joined each ping to its
`agent_meta.json`, and all 260 resolved.

| Shape | Pings | Share | Can the host already tell it's not the outcome? |
| --- | ---: | ---: | --- |
| Epic phase (`phase_bead_id`) | 71 | 27% | **Yes.** The phase is in the epic clan, and the land agent `%wait`s on it. |
| Research-swarm researcher | 49 | 19% | **Yes.** It is a clan member, and `.final` `%wait`s on it. |
| Epic land | 31 | 12% | This *is* the outcome. |
| Other clan fan-out | 29 | 11% | **Yes.** It is a clan member. |
| Swarm lead or tail (`.final`, `.image`, `.critique`) | 19 | 7% | The last one to finish is the outcome. |
| Session or pipe turn, no clan | 35 | 13% | Usually the thing you asked for |
| Standalone | 26 | 10% | Usually the thing you asked for |

- **Three quarters of apollo's success pings come from clan members:** 199 of 260 (77%).
- **The athena week is similar** (cld):
  - epic phases 49%;
  - researchers 12%;
  - other clans 11%;
  - leads and tails 5%;
  - landers 9%.

  That makes about 86% clan members.
- **Collapsing each clan generation to one ping cuts the volume sharply:**
  - apollo drops from 260 to about **108** (47 clan generations plus 61 non-clan pings),
    a **58%** cut;
  - athena drops from 883 to about **245**, a **72%** cut.
- **Goals would not do better on volume.** The design's own Goals end state is about
  **310 claims a week** on athena, plus quiet Idle notices.
- **This dispatch is a live example.** Five researcher pings and one lead ping for one
  question. The structural policy would send one.

**The finding the Goals program ignores: triage is at least as large a stream as
completions.**

- On apollo, `TaskTriage` gates (277) outnumber success pings (260).
- On athena, local triage plus relayed apollo triage gates come to about 88 a day.
- After a structural completion fix, triage becomes the largest source of notifications
  on both hosts, and **Goals does nothing about it.**

If the real complaint is "too many notifications," triage is the next target, and it is
not Goals-shaped.

**Caveats.**

- A clan generation that straddles the window edge counts as one ping, which slightly
  overstates the apollo cut.
- Some session turns might collapse further.
- `read`/`dismissed` flags don't measure interruptions: 261 of apollo's 262 success rows
  were dismissed. A before/after count of *arrivals* from the same store is the right
  metric.

---

## 4. Can clans and swarms do this? Yes, once, at the host

### 4.1 Today's knobs are not enough

Every report agrees on these points, and I verified each one:

- **`ace.notification_rules` changes only the toast and the sound.** The docs say it
  directly: the row "is still stored, still unread, still counted in the top-bar
  indicator, and still listed in the panel."
  - It is a useful one-day diagnostic of how much of the pain is the bell rather than the
    unread pile.
  - It is not a fix.
- **`%hide` is the wrong tool.**
  - It sets `silent=agent_hidden` on the completion (`finalize.py:468`), which silences
    **failures too**.
  - It also hides the Agents row by default.
  - Researchers and phases are work you watch.
- **Nothing at the send site looks at clan, `%wait`, or epic role.** The only existing
  suppressions are:
  - `plan_rejected` and the shell-handoff outcomes (`finalize.py:39–41`);
  - hidden agents;
  - the `epic_approved` fold.

So the shortcut is **a small missing feature, not a config change.**

### 4.2 Why a host rule and not per-xprompt customization

Marking "the notifying segment" inside `#research_swarm` would work for its default
shape and nothing else:

- **It misses the biggest bucket.** Epic phases are 27–49% of pings, and their prompts
  come from `bead/work_prompt.py`, not from a swarm xprompt.
- **It breaks on optional members.**
  - With `critique=true` or `image=true`, those members `%wait` on `.final`, so a
    hard-coded "notify the lead" rule pings while work is still running.
  - `.final` is only a naming convention.
  - The `critique`/`image` wrinkle was already flagged for Goals' own claim routing in
    [`research:202609/xprompt_swarm_goals.md`](../xprompt_swarm_goals.md).
- **It repeats per template and drifts.** A host rule covers every clan and `%wait`
  graph, including `#reads`, `toobig-*` clans, chop clans, and ad-hoc `%clan` launches.

### 4.3 The policy

This merges cld's truth table, grk's wait-graph rule, and cdx's contract. Rules apply in
order, and the first match wins.

| # | Condition | Success ping |
| --- | --- | --- |
| 0 | The run failed, or the event is a question, approval, gate, sudo request, or held workspace | **Loud and unchanged.** Never suppressed. |
| 1 | `%notify` on the launch (a new per-launch override) | Loud |
| 2 | Some not-yet-terminal agent lists this one in its `%wait` | Quiet |
| 3 | Clan member, and another member of the same clan generation is still non-terminal | Quiet |
| 4 | Clan member that is the last to reach a terminal state | **Loud, once per clan generation.** Dedup key `clan:<clan>:<gen>`. The note summarizes the clan, for example "research.k: 5/6 done, 1 failed," and uses the clan's declared `summary=`/`summary_script=` as the headline. |
| 5 | Routine (`chop_*`) run | Quiet (configurable) |
| 6 | Everything else: standalone, session end, `/sase_run` child | Loud, as today |

**Design details that matter:**

- **What "quiet" means.**
  - The row is written `silent` **and** already dismissed.
  - History is kept and the Agents row stays visible.
  - There is no toast, bell, unread dot, Telegram message, or mobile push.
  - Plain `silent` is not enough: the Agents-row unread projection keys on
    not-dismissed completions.
- **What "terminal" means.** It is "done *or* failed." It is not
  `AgentClan.is_complete`, which means every member *succeeded*.
- **No missed or doubled ping.** Each member writes its own `done.json` before it
  checks the rest of the clan, so the last finisher always sees a settled clan. The
  dedup key absorbs two members finishing at the same moment. This is a local scan of
  agent metadata (`find_agent_clan`) and needs no distributed coordination.
- **Epics need no special rule.**
  - `sase bead work` puts every phase and the land agent in `%clan(<epic>, tribe=epic)`,
    and the land segment waits on every launched phase. On apollo, every land agent's
    `wait_for` listed its phases.
  - So rules 2 and 3 quiet the phases, and the lander finishes last and pings.
  - A child epic gets its own clan and its own `.land`.
- **The escape hatch.** Add `ace.completion_notifications: outcomes | all` so you can
  always get today's behavior back. It needs updates to `default_config.yml`, the
  schema, and the docs.
- **Placement.**
  - Write it as a pure function over metadata:
    `completion_attention(meta, clan_snapshot) -> loud | quiet`.
  - Telegram and mobile only consume the resulting `silent` flag.
  - Under `rust_core_backend_boundary`, the planner should decide whether the predicate
    lives in sase-core now or moves there once another frontend needs it.
- **Size.**
  - Roughly 100–250 lines at one send site, plus the directive and config plumbing.
  - That is one large tale or a 3–4-phase epic.
  - Verify it with a truth-table test and a before/after arrival count from the same
    store.

### 4.4 Gaps this policy leaves, and their cheap fixes

| Gap | Size | Cheap fix |
| --- | --- | --- |
| The terminal agent finishes but the outcome isn't true (a lander admits gaps; a lead's report misses the question) | Unknown; **measure it** | §5, option C |
| A long-lived or incrementally joined clan holds a deliverable quiet until its last member ends | Small | `%notify`; log "silenced-but-needed" cases during the pilot |
| Multi-agent prompts with **no** clan have no persisted group id | Small (swarms, epics, and `toobig` all use clans) | Make swarms and `---` fan-outs auto-declare a clan |
| `%dispatch`ed members live on another host, so the local clan scan can't see them, and remote completions stay in the remote inbox | Real, and independent of Goals | Relay loud outcome pings through Remote Attention |
| An epic whose phases closed but whose land never ran goes quiet | Moderate (the roadmap counted 65 of 98 in-progress epics waiting to land) | `wait_checks` already pings blocked dependencies; an "idle clan" digest is the cheap version of Goals' Idle lane |

**This is not throwaway work if Goals resumes.**

- G3 keeps success pings loud, and G6 edits the same send site
  (`run_agent_runner_finalize.py:469`).
- A success-only suppression seam with a dedup key is plumbing that G6 would need
  anyway.
- The before/after counts are exactly the shadow baseline that G6's start gate asks for.
- At most the clan-terminal branch (about 150 lines) becomes redundant.

---

## 5. What only Goals can add, and what that implies

**What the structural policy cannot do.** grk, mus, and gem are right about its limits.
It can truthfully say "the configured orchestration settled." It **cannot** say "your
outcome is true," and it gives you none of these:

- a claim with check-it steps and resolvable evidence;
- a Verify/Reject/Drop verdict that relaunches onto the same outcome;
- an inventory of open asks;
- identity across plan → epic → remediation child → follow-up.

**The sharper point: for attention specifically, a scoped Goals rollout buys nothing
over the structural rule.**

- **The continuing reports all drop G4.** grk, mus, and gem each recommend G2 plus G3
  without universal drafts.
- **Their binding reads the same structure.** G2's ladder (explicit → session → plan →
  clan → parent → bead) derives a goal from the very clan, plan, and session structure
  the policy above reads.
- **gem says so outright.** Its proposal silences `JumpToAgent(done)` "only for agents
  that have an active bound goal." That is the structural rule, keyed on `goal_id`
  instead of `agent_clan`.

So a scoped Goals rollout's quieter inbox comes from structure, not from the goal
object. What the goal object adds is the claim card, the verdict, and the ledger.

**Option C tests the claim card without the ledger.**

- **Add a field, not a store.** Add an optional `outcome` field to the final
  declaration (`done | progress | needs_you`) and a single "check it" line (cld).
- **Use it only on pings the policy already makes loud:**
  - `done` stays loud and carries the check-it line;
  - `progress` becomes a quiet "still going" note;
  - `needs_you` stays loud and is tagged as such.
- **This answers the design's objection to "claims without goals."** The design
  rejected them because "a researcher can't know the synthesis is done." With §4, the
  *host* decides who may ping. The agent answers only the question it can answer: is
  what I was asked for done?
- **Cost.** One finalizer-context wire change in sase-core. It is breaking, because that
  wire uses `deny_unknown_fields`.
- **The roadmap called a per-agent flag "throwaway."** That verdict assumed agents
  choosing their own loudness, not a host-gated field.

**Build C only if the policy's loud pings turn out to include too many not-done
outcomes.**

---

## 6. Where the reports disagreed, and how I resolved it

| Claim | Who | Resolution |
| --- | --- | --- |
| Epics don't use clans; clans and swarms are about 15% of runs; clan silencing cuts only about 15% of noise | gem | **False.** Every epic phase and lander is in `%clan(<epic>, tribe=epic)` (`work_prompt.py`). Clan members are 77% (apollo) to 86% (athena) of success pings. gem's noise-reduction percentages have no measurement behind them. |
| Wait-graph silence can't cover epic phases, because nothing waits on a phase when it finishes | grk | **False for the standard flow.** The land segment `%wait`s on every launched phase, and apollo's land-agent metadata confirms it. |
| Clan-terminal detection needs distributed synchronization and would recreate `epic_launch_handoff.py`'s locks and TTL sweeps | gem | **Overstated.** That module defers a planner ping until a *separate asynchronous* event, the epic launch settling. Clan terminality needs no deferral: the last member to write `done.json` sees a settled clan, and a dedup key absorbs ties. Only `%dispatch`ed members are a real cross-host gap. |
| A filter becomes throwaway once G3 lands | mus | **False.** G3 keeps success pings on, and G6 needs G4 plus a soak. The shared seam is one send site. |
| Notification filtering is "the last and smallest epic" | mus | True of G6's phase count, but G6 is gated on G4, 0 unbound turns, and a soak of at least 7 days. |
| Abandoning Goals "wastes G1" | gem | A sunk-cost argument. G1's future value depends on whether anything consumes it. grk states the real risk: **G1 with no consumer and no decision is dead weight.** Pause or mothball *explicitly*; don't drift. |
| Pause G2–G6 (cdx, cld) vs. proceed to G2+G3 now (grk, mus, gem) | split | **Pause.** See the reasons below. |

**Why I sided with pausing.**

1. **Structure delivers the attention win without a goal object.** See §5.
2. **The continuing reports already concede the design is over-scoped.** All three
   defer G4, which contradicts the accepted `goals-host-binds` decision ("the host binds
   every LLM turn to exactly one goal"). It also means G6's gate, which requires 0
   unbound turns, can never open. Their path would supersede a decision record and
   rewrite G6 anyway.
3. **Their remaining case is unproven, and pausing is cheap.** What's left for G2+G3 is
   the claim card and the inventory. Both can be tested more cheaply (option C and the
   manual G1 CLI). Pausing forecloses nothing: G1 stays, and the policy's measurements
   become G6's baseline.

**Fact reconciliations.**

- **G1 size.** cdx measured about 7.4k lines of Rust production code, about 2.4k lines
  of Python production code, and about 6.6k lines of tests. cld's "about 19k inserted
  lines" is the same work counted by commits.
- **Apollo success pings.** My classification found 260 for the week, which matches
  cdx's 263.

---

## 7. What pressing on with G2–G6 would cost

This summarizes cld, cdx, and mus.

- **Ownership, not build time.**
  - The fleet builds fast: G1 went from creation to all phases closed in about 17
    hours.
  - What lingers is the surface. G2 changes goal resolution on about 14 launch paths.
  - G3 adds a finalizer to **every** bound turn.
  - G5 adds a top-level tab. It is the program's only golden churn; the Artifacts tab
    scaffold re-blessed 179 PNGs.
  - G1 is the most deterministic slice of the program, and it still needed a remediation
    child epic.
- **Two loops that tests can't prove.** Claim honesty (G3) and name-vs-adopt judgment
  (G4) are model judgments. The design itself says "a wrong merge is worse than a
  duplicate."
- **A per-turn tax.**
  - Bound turns get about 40 tokens.
  - Draft turns get about 80 tokens of intake plus a `sase goal list`/`name` call before
    any work starts.
  - About 25 ad-hoc questions a day would need answer-acknowledgement plumbing just to
    avoid becoming chores.
- **A new daily chore.** Roughly 30 outcomes a day go from "dismiss a ping" to Verify,
  Reject, Drop, or Acknowledge. The design already plans for Review-lane rot.
- **Your review bandwidth.** Five more epics to approve and land, while landing is
  already the bottleneck: 65 of 98 in-progress epics were waiting to land.
- **It targets the smaller share of the noise.** It does nothing for triage, and it
  makes the inbox about 15% louder until G6.

**The steelman for continuing.**

- You asked for more than notifications.
- G1 is paid for.
- `goal-ledger` and `goals-host-binds` are accepted decisions.
- Structure can't do cross-launch adoption.
- Per-model claim-precision data would be genuinely new.

All of that is true, and none of it requires committing to G2 *today*. The policy
forecloses nothing.

---

## 8. Recommendation

**Don't press forward with G2–G6 now.** Goals is a reasonable design for a different
problem than the one you're feeling: verifying outcomes and tracking intent, versus
notification noise. Build the cheap fix for the problem you have. Buy the expensive
program only once the other problem shows up in your own usage.

1. **Finish `sase-1bu.8` (one phase left), then stop.**
   - It fixes known-broken behavior in code already on master (phantom goals, id forks,
     a corrupt event aborting reads).
   - Leaving it half-landed is the worst outcome.
   - Don't write the G2 plan.
2. **Build the host-side structural completion policy (§4.3) as one tale or a 3–4-phase
   epic.** Its contract:
   - success-only suppression;
   - failures and every other attention event loud;
   - one loud ping per clan generation from its last finisher, with a dedup key;
   - quiet means silent **and** pre-dismissed, with the row still visible;
   - a `%notify` override;
   - `ace.completion_notifications: outcomes | all`.

   Verify it with a truth-table test and a before/after arrival count from the same
   notification store.
3. **Fold in the small gaps as separate tasks:**
   - auto-declare a clan for swarms and `---` fan-outs;
   - relay loud `%dispatch` outcome pings through Remote Attention;
   - optionally, an "idle clan" digest.
4. **Aim the next attention effort at task triage.** It is 43% of apollo's rows and
   about 88 a day on athena. It will be the largest stream once completions are fixed,
   and Goals doesn't touch it.
5. **Test the other Goals values for free while the policy runs:**
   - Whenever you catch yourself wanting to remember an ask, run `sase goal new` by hand.
   - Keep a short log of two kinds of miss:
     - "pinged, but it wasn't actually done";
     - "silenced, but I needed it."
6. **Re-decide on or around 2026-10-12, two weeks after the policy lands.** Resume Goals
   if any of these fires:
   - **(a) Loud pings keep lying.** Loud pings regularly point at outcomes that aren't
     done. Try option C first (the `outcome` field plus a check-it line), and go to
     Goals only if C isn't enough.
   - **(b) Structure can't express what you needed.** The policy silenced something you
     needed, or you lost track of work that spanned several launches or days (the
     cross-launch continuity case).
   - **(c) You actually used the inventory.** Roughly 10 or more hand-made goals, and you
     kept checking `sase goal list`.
   - **(d) Someone else needs the list.** A second person starts working in these
     projects and needs a shared list of open asks.
7. **If a trigger fires, resume narrowly.**
   - Build G2 (deterministic binding only, no drafts), then G3 (claims and `GoalVerify`
     on epics and explicit `%goal`).
   - Keep G4 (universal drafts), G5 (tab), and G6 (cutover) behind measured claim
     precision and review burden.
   - Dropping the universal invariant means superseding `decisions:goals-host-binds`
     through `/sase_memory_write`, not editing it.
8. **If no trigger fires, archive the roadmap deliberately.**
   - Keep G1 as a small manual tool, or file a cleanup to remove it before more surfaces
     depend on it.
   - Record that choice as a superseding decision rather than letting the program
     drift.

**Direct answer.** Yes: structure-aware notification filtering gets you most of what
Goals promised for attention, sooner and more cheaply. Do it once at the host, keyed on
clan terminality, `%wait` edges, and epic roles, not by customizing individual swarms.
Goals' remaining value (verified claims, an inventory of intent, cross-launch
continuity) is real but unproven for how you work today. It is also cheap to test before
paying for about 29 more phases and their permanent per-turn and review costs.
