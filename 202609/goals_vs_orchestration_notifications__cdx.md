# Goals versus orchestration-aware completion notifications

_Independent research · 2026-09-28 · researcher: cdx_

## Question

Should SASE continue the full Goals program, or is the useful part simply suppressing
intermediate agent-completion notifications and notifying once when a user-requested
unit of work is complete?

## Executive conclusion

The proposed Goals system is **not merely a notification feature**. Its unique promise
is a durable, person-owned outcome above plans, beads, agents, sessions, and retries;
agents claim that outcome with evidence, while the person verifies or rejects it. An
xprompt swarm or agent clan cannot supply that semantic layer by itself.

However, if the actual problem Bryan wants solved is only notification noise, the full
Goals roadmap is disproportionate. A small orchestration-aware notification policy can
cover research swarms, epics, and other explicit DAGs without a new ledger, universal
binding, finalizer, gate kind, or TUI tab. SASE does not expose that policy cleanly
today, but the missing mechanism is much smaller than G2–G6.

**Recommendation: do not press forward with the full six-epic program yet.** Finish the
already-running G1 correctness repair so the landed ledger is not left broken, then
pause G2–G6. Run a one-week/100-root-run notification-only pilot on research swarms and
epics. Continue into Goals only if that pilot shows a recurring need for durable
cross-run outcome identity, an active-outcome inventory, or human verification with
evidence. If those needs appear, implement G2 and G3 as the next bounded MVP; keep
universal drafts, the Goals tab, and the global attention cutover gated on actual use.

## Evidence reviewed

- The requested roadmap,
  [`research:202609/sase_goals_epic_roadmap/sase_goals_epic_roadmap.md`](sase_goals_epic_roadmap/sase_goals_epic_roadmap.md).
- The live `sase-1bu` epic and its `sase-1bu.8` landing-fix child, read with
  `sase bead read`.
- The design destination,
  [`research:202609/sase_goals_design/sase_goals_design.md`](sase_goals_design/sase_goals_design.md).
- The prior focused notes
  [`research:202609/xprompt_swarm_goals.md`](xprompt_swarm_goals.md) and
  [`research:202609/sase_goals_why_not_beads.md`](sase_goals_why_not_beads.md).
- Current SASE source and documentation, especially
  `src/sase/axe/run_agent_runner_finalize.py`,
  `src/sase/axe/run_agent_runner_lifecycle.py`,
  `src/sase/xprompt/_directive_types.py`,
  `src/sase/agent/clan_membership.py`, `docs/notifications.md`, and
  `docs/goals.md`.
- The installed `#research_swarm` definition, inspected with
  `sase xprompt show research_swarm`.
- The current goal-domain files in the linked `sase-core` checkout.
- A read-only snapshot of this host's notification catalog for 2026-09-21 through
  2026-09-28, excluding the current research clan.

I did not inspect any other report from the current research swarm.

## 1. What has actually been built

The roadmap describes six epics. Only G1 has substantially landed:

- `sase-1bu` has seven closed phases implementing the goal domain, ledger, hidden-clone
  write lane, sync, CLI, artifact kind, fixtures, benchmark, docs, and memory.
- Its child `sase-1bu.8` is still in progress with two phases repairing ledger and CLI
  correctness. The landing audit found phantom goals on edits of unknown ids, unstable
  criterion ids, corruption paths that could abort reads, reconcile/doctor defects,
  and CLI behavior inconsistent with help text.
- The measured warm-list p50 is about 37–39 ms at 1,000 unsettled goals against the
  intended 5 ms projection contract. A separate follow-up owns that optimization.
- `docs/goals.md` is explicit that binding, drafts, claims, the Goals tab, and attention
  cutover are later work. Today G1 is a manually managed ledger and `goal:` artifact.

A rough file census illustrates the cost already paid by G1. The current goal-specific
surface is about 7,404 lines of Rust production code plus 2,427 lines of Python
production and adapter code, with about 6,611 additional Rust/Python test and fixture
lines. These counts are not a complexity metric by themselves, but they make one point
hard to ignore: the project has already incurred a substantial permanent subsystem
before testing the notification hypothesis with users.

The remaining roadmap is still about 29 planned phases:

- G2: deterministic binding (6)
- G3: claims and verification (7)
- G4: universal drafts, naming, adoption, and answer acknowledgement (6)
- G5: Goals tab and Agents integration (6)
- G6: attention cutover (4)

The choice is therefore not between “do nothing” and “finish the last 10%.” It is
between a small notification experiment and most of the product program.

## 2. What xprompts and clans can solve

For structured work, the orchestration already knows much of what a notification
policy needs:

- An xprompt swarm has explicit segments and `%wait` edges.
- `#research_swarm` names researchers and a `.final` synthesizer; the synthesizer waits
  for all researchers.
- Epic work has phase roles and a land agent.
- Agent metadata records clan identity, clan generation, waits, sessions, phase bead,
  and epic bead.
- Clan lookup already knows when every member of a generation has completed.
- Successful completion notification creation is centralized in
  `run_agent_runner_finalize.py`.

That is enough to implement “do not interrupt me for successful intermediate workers;
do notify me for the terminal result.” A suitable policy would:

1. Keep every agent row visible and preserve its completion history.
2. Suppress only the *visible successful-completion* notification for members marked as
   intermediate.
3. Never suppress failures, questions, approvals, held workspaces, or other
   attention-requiring events.
4. Let an xprompt nominate a terminal member, or let a known workflow role such as an
   epic land agent be terminal.
5. For a genuinely rootless clan, either emit one idempotent aggregate notification
   when the generation settles or require an explicit terminal/notification owner.

This is not available cleanly today. `%hide` is the only nearby public directive, and
it is the wrong tool: hidden agents produce `silent=True` completion *and failure*
notifications, and their rows are hidden by default. Delivery rules can match the
successful completion's `done` tag, but the documentation says those rules suppress
only toast and sound: the row remains stored, unread, counted, and listed. The internal
`suppress_completion_notification` state is for runner control paths, not an authored
per-agent policy. A narrow new metadata field or directive is therefore needed.

The roadmap's headline volume evidence also uses the wrong denominator for the specific
problem. Its 2,048 `agent_meta.json` records measure agent turns, not notification rows,
toasts, audible announcements, or unread burden. SASE already suppresses handoff
outcomes, makes hidden-agent rows silent, folds some epic-plan completions, and emits at
most one sound per notification poll. On this host, a fixed catalog snapshot from
2026-09-21 00:00 through 2026-09-28 13:00 EDT contained 667 nonsilent rows after
excluding this research clan. Of those, 282 were user-agent completion rows: 263
successful and 19 unsuccessful. Only one visible successful row was still unread and
undismissed at the sampling instant. The query included dismissed and silent rows;
there happened to be no silent rows in this window. These local figures are not
directly comparable to the roadmap's athena run census, and read/dismissed state at one
instant is not a count of arrivals, toasts, or interruptions. That is precisely the
point: a same-host baseline of actual delivery events is required before attributing
6.6 interruptions to each outcome.

The important distinction is that this alternative is a **notification policy**, not
an inference that an agent understood the user's outcome. It can truthfully say “the
configured orchestration settled” or “the designated terminal agent finished.”

## 3. What xprompts and clans cannot solve

An xprompt is a launch recipe. A clan is deliberately a rootless execution container.
Neither is a durable outcome record.

That creates hard limits:

- **No stable identity across shapes.** A prompt can move through a planner, approval,
  epic, phases, lander, rejection, relaunch, and follow-up. The xprompt or clan that
  launched one portion does not name the user-level outcome across all of them.
- **No semantic definition of done.** “All members exited successfully” is not the same
  as “the requested result is true.” A research agent may finish while the synthesis is
  still pending; a land agent may finish with admitted gaps; an optional critique or
  image step may run after the nominal lead.
- **No outcome inventory.** Suppressed notifications cannot answer “what am I trying to
  get done?”, “what is idle?”, or “what is awaiting my verification?”
- **No claim/evidence protocol.** A completion notification can link to an agent, but it
  does not require a concise claim, resolvable evidence, check-it steps, or disclosed
  gaps.
- **No human settlement.** There is no durable Verify/Reject/Drop decision that can
  relaunch onto the same outcome.
- **Poor coverage of ad-hoc work.** Direct questions, manual agent launches, pipe
  chains, follow-ups, and work spanning several orchestration recipes do not all have a
  common terminal node.

The current `#research_swarm` demonstrates both sides. Its default graph has an obvious
terminal `.final` agent, so success-ping suppression is easy. But optional critique and
image members wait on `.final`, making `.final` nonterminal. A generic “last finisher is
the owner” rule could let an infographic agent represent the whole outcome. Explicit
workflow metadata fixes the notification case; a Goal fixes the semantic identity
case.

## 4. Capability comparison

| Capability | Xprompt/role notification policy | Clan aggregate notification | Full Goals design |
| --- | --- | --- | --- |
| Silence successful intermediate workers | Yes | Yes | Yes, at G6 |
| Keep failures loud | Yes, if implemented separately from `%hide` | Yes | Yes |
| One signal for a known research/epic DAG | Yes | Usually | Yes |
| Truthfully report that all configured members settled | With an explicit terminal edge | Yes | Yes |
| Know that the user's outcome is actually complete | No | No | Claim + human verdict |
| Span plan → epic → retries → follow-ups | Only with bespoke propagation | No | Yes |
| Work for unstructured/ad-hoc requests | Weak | No | Yes, via drafts |
| Show an inventory of active/review/idle outcomes | No | No | Yes |
| Require evidence, checks, and gaps | No | No | Yes |
| Preserve cross-machine outcome history | No new record | No new record | Yes |
| Implementation and operational cost | Low | Low-to-medium | High |

This table is the decision. If the first four rows are the desired product, Goals is
overbuilt. If the middle five rows are desired, notification customization is not a
substitute.

## 5. Critique of the Goals design

### 5.1 The design solves a real higher-level problem

The strongest case for Goals is not fewer pings. It is the missing noun between intent
and execution:

```text
person's outcome → plan / beads → agents / sessions / clans → artifacts
```

Today SASE has durable records for every layer except the first. A stable outcome can
make follow-ups coherent, keep a rejected claim attached to the same request, show
running versus idle work independently of agent liveness, and make the user's verdict
authoritative. Those are meaningful capabilities, especially for multi-agent epics and
research programs.

The “agents claim; users settle” split is also better than treating a successful
process exit as proof. Evidence candidates, check-it steps, gaps, and provenance-aware
claims are the part of the proposal most likely to improve trust rather than merely
reduce noise.

### 5.2 The product hypothesis has not earned the universal machinery

The design assumes every LLM turn needs exactly one primary goal. That expands a useful
idea for long-running work into mandatory bookkeeping for questions, tiny edits,
routines, hidden helpers, monitors, gates, and recovery turns. The special cases in the
design—draft naming, adoption, standing routine goals, answer acknowledgement,
plan-approval suppression, prepared-monitor claims, auto-naming after crashes—are
evidence that universal coverage is expensive.

There are at least four unvalidated behavioral hypotheses:

1. Agents will name/adopt goals accurately enough not to create sprawl or mis-link work.
2. Claims will be precise enough that review is useful rather than another inbox chore.
3. Users will consult an outcome inventory rather than the existing Agents, Beads, and
   Artifacts views.
4. Definitions of done injected into every turn will improve work enough to justify the
   token, latency, and mental overhead.

The roadmap sensibly delays G6 until after a soak, but it does not similarly require
product evidence before G2–G5. That is backwards: the cheapest version of the stated
benefit should be tested before mandatory goal binding and a new top-level tab.

### 5.3 The blast radius is unusually broad

G3 proposes a required `builtin@goal` finalizer on every bound normal return. G4 puts
every LLM turn into the domain. The ledger is cross-machine, append-only, projected,
and co-hosted in the public beads sidecar. The TUI, Telegram, mobile gates, artifact
relations, launch inheritance, retries, sessions, dispatch, monitors, and plans all
become participants.

The G1 landing audit is a concrete warning rather than a theoretical objection. Even
the isolated ledger epic produced a remediation child for correctness defects and a
separate performance follow-up. The roadmap's split is responsible engineering, but it
does not make the accumulated subsystem cheap.

### 5.4 “Claims without goals” was rejected too quickly

The design rejects per-agent claims because a researcher cannot know when synthesis is
done and a phase worker cannot know when an epic is done. That is correct for arbitrary
agents, but structured orchestration already knows those roles. A designated swarm
terminal or epic lander can produce a richer completion notification with result refs
and optional check-it text, while contributors stay quiet.

This would not create a durable outcome inventory, but it is not throwaway work. A
success-notification policy remains useful even if Goals later ships: failures and
intermediate roles still need transport policy, and G6 eventually needs the same
suppression seam. It is therefore a legitimate product probe, not merely a temporary
hack.

## 6. The cheaper experiment

Implement one narrow capability before G2:

### Contract

- Add launch metadata equivalent to `success_notification: notify|suppress` (the exact
  spelling is less important than keeping it distinct from visibility).
- Default to today's behavior.
- The setting affects successful completion only. Failure and all other attention
  events remain visible and loud.
- Preserve the completion record and visible agent row; suppress its inbox/bell/
  Telegram projection rather than erasing history.
- Give aggregate/terminal notifications a stable deduplication key.

### First adopters

1. `#research_swarm`: researchers suppress success; the configured final deliverable
   owner notifies. Optional critique/image variants explicitly nominate their terminal
   owner.
2. Epic work: phase agents suppress success; land notifies. Existing approval,
   question, failure, and launch-settlement notifications remain unchanged.
3. One pipe/session workflow: intermediate turns suppress success; the last normal
   return notifies.

Do not infer a terminal owner merely from “last process to exit.” A rootless clan can
instead get one aggregate “clan settled” notification, which should say exactly that
and not claim the user's result is verified.

### Measure for at least one working week or 100 root requests

- Visible success notifications per root request, before and after.
- Percentage of successful member notifications safely suppressed.
- Failure/question/approval recall: target 100%.
- How often Bryan opens or replies to a suppressed intermediate result anyway.
- How often the terminal notification points to the wrong deliverable.
- How often one requested outcome spans more than one orchestration and becomes hard to
  find or resume.
- Manual `sase goal` creation/list/show usage during the pilot.
- Qualitative answer to: “Do I still need a list of outcomes awaiting verification, or
  did I only need fewer pings?”

## 7. Decision rule after the pilot

### Stop after G1 plus notification policy when

- nearly all painful notification bursts come from structured swarms, epics, or
  sessions;
- explicit terminal-role metadata reliably selects the useful result;
- Bryan rarely needs to resume, reject, or inspect work by a stable outcome identity;
- the manual goal ledger is not used as an active-work inventory.

In that world, keep G1 only if its manual ledger/artifact value justifies its ongoing
maintenance. Otherwise define a deliberate deprecation path before more surfaces depend
on it. Sunk cost is not a reason to build G2–G6.

### Continue with a Goals MVP when

- notification suppression makes the inbox quieter but work is still difficult to
  track across plans, retries, follow-ups, or machines;
- users want to distinguish “agent stopped” from “outcome ready to verify”;
- evidence/check-it/gaps materially shorten review;
- an outcome inventory is consulted enough to replace agent-process scanning.

The next MVP should then be **G2 + G3 only**: deterministic binding for explicit goals,
plans, epics, sessions, and clans, followed by claims and human verification. That
tests the unique value of Goals on work whose identity the host already knows. Do not
yet force draft naming on every ad-hoc question. G4, G5, and G6 should depend on
measured adoption, claim precision, and review burden.

## Recommendation

**Pause the full Goals roadmap after repairing G1. Build and measure orchestration-aware
completion notification suppression first.**

This recommendation does not reject Goals. It rejects using a durable cross-machine
outcome domain to answer an unproven notification-policy question. If the experiment
shows that quieter terminal notifications are enough, stop: xprompts and explicit
workflow roles are the right abstraction. If it shows that the remaining pain is
continuity, inventory, evidence, and human settlement, proceed with G2 and G3—the parts
that deliver those unique semantics—and earn the universal G4–G6 expansion with data.
