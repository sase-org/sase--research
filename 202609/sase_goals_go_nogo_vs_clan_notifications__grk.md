# Goals go/no-go: is a notification filter enough?

_Independent critique · 2026-09-28 · researcher grk · project: sase_

**Question.** Should SASE press forward with Goals (`sase-1bu` and the G2–G6 program), or is the real payoff just quieter completions — in which case we could customize xprompt swarms and/or agent clans so only certain agents send a completion notification?

**Sources (shared input, then code).** The Goals design of record
[`research:202609/sase_goals_design/sase_goals_design.md`](sase_goals_design/sase_goals_design.md),
the six-epic roadmap
[`research:202609/sase_goals_epic_roadmap/sase_goals_epic_roadmap.md`](sase_goals_epic_roadmap/sase_goals_epic_roadmap.md),
[`research:202609/xprompt_swarm_goals.md`](xprompt_swarm_goals.md),
[`research:202609/sase_goals_why_not_beads.md`](sase_goals_why_not_beads.md),
the G1 plan `plan:202609/goal_ledger.md`, epic bead `sase-1bu` (and landing child `sase-1bu.8`),
the live `#research_swarm` xprompt, and HEAD code for completions, `%hide`, delivery rules, and unread projection.

I did not read any other researcher's report from this swarm.

---

## Recommendation

**Press forward, but not as a six-epic notification project, and not by editing xprompts.**

The hypothetical is false: better notifications are one payoff of Goals, not the only one, and clan/xprompt notification filters cannot even deliver that payoff except on statically authored parallel fan-outs.

Do these four things, in order:

1. **Finish G1.** `sase-1bu` has all seven phases closed and is in landing behind child epic `sase-1bu.8` (phantom ids, corrupt-event isolation, CLI honesty). A frozen ledger with those bugs is worse than no ledger. Do not mothball mid-land.
2. **Ship a small, host-owned quiet-success tale now**, independent of Goals. The correct form of the xprompt idea is: on a *successful* completion, if another live/queued/waiting agent `%wait`s on this agent, send the completion as `silent` (or skip the user-facing send). Failures, questions, and gates stay loud. Optionally add `%quiet` so sequential contributors (epic phases) can be silenced without `%hide`. This is days of work, not five epics.
3. **Plan and run G2, then G3, then stop and look.** That is the actual product: the host binds an outcome, the owner claims it with evidence and check-it steps, you settle it. Keep today's success pings on, as the roadmap already requires, until claim precision is measured.
4. **Hold G4, G5, and G6** until G3's shadow coverage says a claim would have replaced the success ping. If it would not, you still have epic verification and a cheap swarm quiet, and you have not spent a top-level tab or an attention cutover.

**Do not** try to get "notify me when the work I asked for is done" by putting `%hide` on researchers or by adding a `notify=` knob to `#research_swarm`. That approximates the wait graph in templates, gets the claimer wrong when `critique` or `image` is on, ignores the 41% of weekly runs that are epic-bound, and still pings "agent stopped" rather than "here is what to check."

If, after using G3 on real epics, the inventory and verification loop is not worth the remaining cost, stop there. That is an honest no to G4–G6. It is not a reason to abandon G1 in landing or to skip G2–G3.

---

## 1. Steelman the shortcut

The pain is real. A completion is a process event: `send_completion_notification` in
`src/sase/axe/run_agent_runner_finalize.py` emits `JumpToAgent` tagged `done` (line 469)
for almost every successful LLM turn. That row becomes an unread inbox item, a toast, a
bell, a Telegram outbound candidate, a mobile snapshot row, and an Agents-tab unread
dot (`_notification_unread_projection.py`). A five-researcher swarm plus a lead is six
of those for one question. This swarm is that shape.

The design's own count (athena, week of 2026-09-27): **2,048** `agent_meta.json` files
in 7 days, **841** epic-bound (~41%), about **310 distinct outcomes**, ~**6.6 turns per
outcome**. Almost every turn can light an unread.

So the shortcut says: if the user-visible win is "ping me when the work I asked for is
complete," author the fan-out so only the finishing agent notifies. Researchers stay
quiet; `.final` chimes. Maybe epic phases stay quiet; the lander chimes. Clans already
exist. Xprompts are editable. Why build a ledger, a finalizer, a gate, a tab, and a
cutover?

That is a serious alternative. It is also how a lot of orchestrators actually ship
"notify on workflow complete." It deserves to be answered on the code that exists
today, not on the design's aspirations.

---

## 2. What already exists (the shortcut is partly here)

Four mechanisms already touch this problem. None of them is "notify only when the
outcome is done."

| Mechanism | What it actually does | Why it is not enough |
| --- | --- | --- |
| **Handoff suppression** | `_COMPLETION_NOTIFICATION_SUPPRESSED_OUTCOMES` already skips monitor and gate handoff turns (`run_agent_runner_finalize.py` 39–41, `SHELL_HANDOFF_OUTCOMES`). Pipes and question handoffs do not double-ping the predecessor. | The *successor's* successful completion still pings. Parallel clan members are not handoffs; each is a full run. |
| **`%hide` / `%h`** | Hidden agents set `silent=agent_hidden` on the completion payload (finalize.py:468). Silent rows are dropped from the TUI inbox, toasts, Telegram outbound, and mobile snapshots. | `%hide` also hides the Agents-tab row (`docs/xprompt.md`). Researchers and epic phases are work you watch. Quiet-without-hide does not exist. |
| **`ace.notification_rules`** | Ordered globs on tab/sender/action/tags/title/note. Can set `toast: false` and `sound: none` for `tags: done` or `note: "*@research.*.cdx*"`. | Docs are explicit: a rule **does not change whether a notification is created, stored, unread, counted, or listed**. The Done tab and Agents unread dots still fill. Telegram still delivers non-silent unread. |
| **Per-row mute** | `M` in the inbox, `sase notify … mute`. | After the fact. You still got dinged. |

So: you can already mute the *chime* for researcher completions with a delivery rule
this afternoon. You cannot, with current knobs, stop those completions from being
unread work. `%hide` stops the unread and also hides the agents. There is no
`%quiet` / `%notify:off` directive. Clans have no `notify=` policy. The notification
layer has no "this agent is waited on" check at send time.

The shortcut is therefore **a small missing feature**, not a config change.

---

## 3. Critique: why xprompt/clan notification filters fail as a substitute

### 3.1 "Last agent to exit" is a bad proxy for "work I asked for"

`#research_swarm` already has a wait graph. Researchers do not wait on each other. The
lead waits on every researcher (`research_swarm.md` around the `%id:research.{@1}.final`
segment). If `image=true` or `critique=true`, those members wait on `.final`, not on
each other.

A template that "only notifies the lead" is right on the default five-researcher
dispatch and wrong as soon as a later waiter exists. The earlier swarm-goals note
already flagged this: under the host role rule "an agent another pending agent waits on
is a contributor," `.final` becomes a contributor and the infographic or critique agent
is the one that would claim. The same inversion hits a notify-the-leaf policy. You
wanted the synthesis; you get a ping from the image model.

Encoding the claimer in the xprompt means every flag combination has to name it.
`#reads` has the same shape (three searchers, one consolidator). Chop clans, `%alt`
fan-out, `/sase_run` children, and ad-hoc `%clan` launches have no template author in
the loop. A host wait-graph rule is the general form of the idea; a per-xprompt knob
is a fork of it that will drift.

### 3.2 The noisy half of the workload is not a swarm

Epic-bound runs were ~41% of last week's volume. Epic work is **sequential**:
`sase bead work` launches a phase, that phase completes and pings, the next phase
starts, then `bd/land_epic` runs and pings. At the moment a phase succeeds, nothing is
`%wait`ing on it. Wait-graph silence does nothing. Clan membership does nothing unless
you also invent an epic-role rule (phase = contributor, land = owner), which is G2/G3's
`decide_goal_action` under another name.

Questions are ~25/day and 1:1. Silencing "certain agents" does not apply. The
completion *is* the answer, and the design's answer-ack path (open the answer →
`done · acknowledged`) is the thing that keeps those from becoming verify-chores. An
xprompt filter cannot acknowledge.

Ad-hoc coding agents, retries, `%repeat`, monitor recoveries, and LaunchApproval
children are not in `#research_swarm`. Editing that xprompt leaves them loud.

### 3.3 A successful last-agent ping is still the wrong object

Even if only `.final` chimes, the payload is still:

```text
CLAUDE(opus) @research.k.final completed: ace(run)-…
action: JumpToAgent
```

That is "a process stopped." It does not carry the outcome sentence, 1–3 check-it
steps, or clickable evidence refs. You still hunt the report, reread the prompt, and
decide whether the work is actually done. Goals' claim is a different noun: a
`GoalVerify` gate with *You asked → Claim → Check it → Evidence → Gaps*, settled by
Verify / Reject / Drop, with dismiss-is-not-a-decision already defined in
`docs/notifications.md`.

The stated wish was "users are only notified when work they asked for is complete."
**Complete** here has to mean "the outcome is ready to check," not "the last subprocess
exited 0." A land agent can finish a turn successfully while the epic's goal is false.
A research lead can write a report that does not answer the question. Silencing
siblings does not detect that. A required `builtin@goal` claim with host-checked refs
is the check.

### 3.4 `%hide` on researchers is the wrong tool even for swarms

Putting `%hide` on `research.*.cdx` etc. would silence their completions today. It
would also remove them from the default Agents view, break the usual "watch the
swarm" loop, and still leave `.final` as a process ping. Hidden is for harness helpers
(the blog post's "noisy helper"), not for first-class researchers you may need to
inspect, fork, or follow up on.

### 3.5 Delivery rules train you to ignore the Done tab

A `tags: done` → `toast: false, sound: none` rule is the cheapest experiment available
*right now*. It will tell you, in a day, how much of the pain is the bell versus the
unread pile. It will not empty the pile. If the complaint is the inbox chip and the
Agents dots — and the unread projection says it is — delivery rules are a diagnostic,
not a fix.

### 3.6 Goals' other payoffs do not fall out of a notify filter

The design ranks value as:

1. Attention matches what you verify (one claim per outcome).
2. A written outcome up front, so the agent can judge its own claim.
3. A project inventory of **intent** (Agents = processes, Beads = scheduled work,
   Plans = designs; nothing lists "what am I trying to get done").
4. Continuity: reject, follow-up, and relaunch accumulate on one object.

(2)–(4) are not notification features. A quiet researcher does not give you
`sase goal list` of every in-flight epic. It does not stamp `goal_id` on phase and land
agents. It does not retract a claim when you follow up. It does not prevent four
parallel researchers from each believing they finished a different outcome.

cld's earlier "claims without goals" alternative (a per-agent needs-attention flag,
no Goal object) was the closest relative of this shortcut. The design rejected it for
the same structural reason: a researcher cannot know the synthesis is done, a phase
worker cannot know the epic is done, and you get no inventory. Host wait-graphs can
fix the first of those for parallel fan-outs. They cannot fix sequential epics, and
they cannot give you the inventory.

---

## 4. Where the shortcut *does* win

It is the right **stopgap**, and it should be built as host policy rather than as
xprompt art.

**Wait-graph quiet successes** (recommended tale):

- If `success` and some not-yet-terminal agent lists this agent in `%wait`, set
  `silent=True` on the completion (or skip the user-facing send).
- Failures, `ViewErrorReport`, questions, gates, sudo, and LaunchApproval stay loud.
- Applies to `#research_swarm`, `#reads`, chop clans, and any ad-hoc `%wait` graph
  with no template edit.
- Does not hide Agents rows.
- Matches Telegram/mobile, because those already filter `silent`.

**`%quiet` (optional, sequential):** same send-site `silent` without hiding, for epic
phases and other contributors that are not waited on at completion time. This is the
one place an xprompt (or `bd/` work prompt) edit is justified — as a consumer of a
host directive, not as a one-off `research_swarm` fork.

Cost: small/medium tale. Risk: you miss a researcher failure if you accidentally
silent errors (so: success-only). Risk: `critique`/`image` still ping after the lead;
that is correct under wait-graph and may be what you want, or you wait-chain them.

This is complementary to Goals. G6's `silence-successes` is a global cutover of the
same send site (`run_agent_runner_finalize.py:469`). A wait-graph/`%quiet` flag is
plumbing G6 would want anyway. Building it now does not strand work.

What it will **not** do: cut epic-phase success pings (without `%quiet` on phases),
turn the ping into a claim, or list in-flight intent.

---

## 5. What pressing forward actually costs from here

G1 is not a proposal. It is in landing.

| Unit | State now | What you still pay |
| --- | --- | --- |
| **G1 ledger** `sase-1bu` | 7/7 phases closed; land spawned `sase-1bu.8` | Finish the landing-fix child (core refusals, criterion ids, corrupt isolation, CLI honesty, pin ratchet). The frozen event vocabulary is already in `sase-core` and `src/sase/goals/`. |
| **G2 binding** | Not planned | ~6 phases. Generalize `%tab` inheritance (`sase-1bc` is still in progress and owns that seam). Launch-path matrix. No model judgment. |
| **G3 claims** | Not planned | ~7 phases, two of them large. Required `builtin@goal` on every bound turn. **Success pings stay on. Notification load ~+15% until G6.** |
| **G4 drafts** | Not planned | Universal "every turn has a goal," swarm shared drafts, naming/adoption judgment. Needed for swarm *goals*, not for swarm *quiet*. |
| **G5 tab** | Not planned | Only golden-churn epic. Daily loop UX. |
| **G6 cutover** | Gated on ≥7d and ≥100 settled claims, 90% shadow coverage, ≥80% claim precision | The actual "success pings go silent" switch. |

The roadmap's calendar guess was 2½–4 weeks for the whole program including soak.
G1 already demonstrated the project's usual landing-child tax on a ≤7-phase epic.
Expect G2 and G3 to do the same. That is not a reason to stop; it is a reason not to
commit to G4–G6 on momentum.

Two sequencing traps:

1. **G3 makes the inbox louder before G6 makes it quieter.** If the pain is today's
   firehose, shipping G3 without the wait-graph quiet tale is the wrong week. The
   stopgap is what lowers volume *now*; G3 adds a better *kind* of ping alongside the
   old ones.
2. **G4 is how swarms get a goal, not how they get quiet.** After G2–G3, a research
   swarm is still unbound unless you pass `%goal`. Wait-graph quiet already handles
   swarm noise. Do not start G4 in order to silence researchers.

G1 with no G2 is dead weight: a `sase goal` CLI nobody binds, a public `goals/` tree
in the beads repo, and a landing-fix epic to keep a contract honest for consumers
that do not exist. That is the one outcome to avoid. Either consume the ledger
(G2–G3) or, after `sase-1bu.8` lands, explicitly mothball it (stop planning G2, leave
the CLI as a manual curiosity). Do not drift.

---

## 6. Decision table

| If the real wish is… | Do this | Do not do this |
| --- | --- | --- |
| The bell from `#research_swarm` researchers | Wait-graph quiet successes (tale). Optional delivery-rule experiment today to separate bell-pain from unread-pain. | Edit `research_swarm.md` with `%hide`. Start G4. |
| One ping when an *epic* is actually done, with something to check | G2 then G3. Land claims, phases `keep_open`. Optional `%quiet` on phase work prompts as a stopgap. | Clan notify knobs. Silencing `.final` equivalents that do not exist on sequential phases. |
| "What am I trying to get done?" as a first-class view | G2–G3 for the data; G5 only after the claim corpus exists | A Done-tab filter. Another Artifacts subtab of agent rows. |
| Replace success pings globally | G6, after G3/G4 metrics clear. Keep a config to leave them loud. | G6 without shadow coverage. Cutting success pings in xprompts one template at a time. |
| Spend nothing more on Goals | Finish `sase-1bu.8`, ship wait-graph quiet, mothball G2+. Say so. | Leave G1 half-landed. Pretend xprompt edits are the Goals cutover. |

---

## 7. Direct answers

**Is the only value-add better notifications?** No. The distinctive value is a durable
*outcome* the host binds, the owner claims with evidence, and you settle — plus an
inventory of intent and continuity across follow-ups. Notification cutover (G6) is the
last epic because it is the last thing you can measure. Treating G6's effect as G1–G5's
purpose inverts the program.

**Could we just customize xprompt swarms and/or clans so only certain agents notify?**
You could approximate it for *authored parallel fan-outs*, and a host wait-graph rule
does that better than a template fork. That is worth doing this week. It does not
cover sequential epics, 1:1 questions, ad-hoc children, or "is the outcome actually
true." It leaves the ping as `JumpToAgent`. It fights `critique`/`image`. It is not
Goals.

**Should you press forward?** Yes, through **G1 landing + G2 + G3**, with a **quiet-success
tale in parallel**, and an explicit **hold on G4–G6** until claims earn the cutover.
No to the full six-epic push driven by notification relief. No to cancelling Goals
because a swarm xprompt could be quieter.

The test after G3: land a small epic and a research swarm (the swarm still using
wait-graph quiet). If you actually verify from the claim card and stop caring about
phase/researcher dots, schedule G5 then G6. If you still only wanted the dots to go
away, you already have that for swarms, and you can add `%quiet` for phases, and you
should not build a Goals tab.
