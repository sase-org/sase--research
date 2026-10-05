# Goals: ten recent articles worth reading before you re-cut the design

_Researcher cld · 2026-10-05 · project: sase · reading list, not a design_

**What you asked for.** You didn't want the Goals feature designed or researched. You
wanted recent (≤ 1 year old) articles likely to sharpen your thinking about it. This report
gives you a ranked list of ten, each with a justification tied to the revised direction in
your incomplete goals prompt. It also has a TODO → reading map and a short list of
honorable mentions.

**Context I read first.** Your incomplete prompt (`~/tmp/incomplete_goals_prompt.md`), the
lead syntheses
`research:202609/sase_goals_epic_roadmap/sase_goals_epic_roadmap.md` and
`research:202609/sase_goals_design/sase_goals_design.md` (both via `sase artifact read`),
and the `decisions:goal-ledger` and `decisions:goals-host-binds` records. I needed these
only to judge which articles would matter. I'm not re-litigating them here.

**Window.** "≤ 1 year old" means published on or after 2025-10-05. Nine of the ten primary
picks are from 2026, and three are from the last seven weeks. Every primary pick was opened
and read (dates checked) unless §6 says otherwise.

---

## 0. Bottom line

The last twelve months produced a lot of work that bears directly on your revised Goals
plan. The two big coding-agent vendors both shipped a **first-class "goal" primitive**:
Claude Code `/goal` in May 2026 and Codex goal mode, GA in May 2026. Anthropic then shipped
**Claude Code Projects** (2026-09-17), whose Overview pane looks a lot like the Goals tab
you sketched. HCI researchers at Microsoft, Hugging Face, and Data & Society published
**empirical and critical work on review inboxes and approval fatigue**, which bears on your
`<enter><enter>` approval idea and your "Needs Review" section. And heartbeat and
standing-objective designs (OpenClaw, Salesforce's "levels and ticks", Gas Town's patrols)
have matured enough to steal from.

**If you read only three:**

1. **Claude Code Projects docs** (#1). It is the nearest shipped analog to your tab.
2. **Claude Code `/goal` docs** (#2). It shows how light a goal can be and still work.
3. **"Overseeing Agents Without Constant Oversight"** (#4). It is the best evidence on what
   a verification card should show.

---

## 1. How I chose

I ranked candidates on four things, in this order:

1. **Direct bearing on a TODO in your prompt.** That means lighter goal origination, the
   Goals tab IA (Needs Review / Active / Permanent / Completed), approval from the tab, goal
   hooks, clan-goal units, heartbeats, or purge-and-dismiss.
2. **Primary source over commentary.** Vendor docs and engineering posts beat secondary
   blog summaries. Papers beat press coverage.
3. **Evidence over opinion.** Measured results or shipped behavior rank above essays.
4. **Novelty relative to your existing research.** The September Goals reports already
   cover ledger storage, binding, and the rationale for not using beads. I favored readings
   that challenge or extend those reports rather than restate them.

I searched about 30 queries across vendor blogs and docs, arXiv, martinfowler.com, Medium,
and tech press. I then had every primary pick fetched and checked for date, author, and the
specific mechanisms I cite.

---

## 2. Five threads that run through the list

These are the things the readings, taken together, make me want you to think about. They
are framed as questions, not design.

1. **How heavy is a "goal"?** Both vendor goal primitives are a single sentence scoped to
   one session or thread, with a tiny state machine, and they **clear themselves** when
   resolved (#2, #3). Projects makes its Goal an *optional* one-liner (#1). Your prompt's
   "much lighter approach" is in step with the field. The readings make you ask which goals
   actually need cross-machine durable identity and which are just a completion condition on
   a unit of work.
2. **Who decides "done"?** The readings take three distinct positions:
   - the working model, forced through an evidence audit (Codex, #3);
   - a *fresh* cheap evaluator model after every turn (Claude `/goal`, #2);
   - a separate skeptical evaluator agent with a pre-negotiated "sprint contract"
     (Anthropic harness, #5).

   Your design adds the human as the final arbiter. The readings suggest the layers can be
   stacked, so that a cheap judge filters what reaches "Needs Review".
3. **Low-friction approval cuts both ways.** Outcome- and spec-shaped review views find
   more errors than process traces (#4). But faster review didn't mean more accurate review,
   and missed errors came with *higher* confidence (#4). The approval-fatigue literature
   (#7, #8) is a direct counterweight to `<enter><enter>`.
4. **A heartbeat is two different things.** In these sources a heartbeat is either *a status
   signal for the human*, or *a wake-up for the agent*: OpenClaw, ticks (#9), and Claude
   `/goal` idle check-ins (#2). The best designs are **silent by default**, skip the wake
   deterministically when nothing is due, and back off over time. Developers in practice
   watch *indirect* cues such as unusual runtime more than streams (#8).
5. **Event hooks on work units are converging.** Gas Town's GUPP (#6), Cursor's "planners
   should wake up when their tasks complete" (honorable mention), Codex's "continue only at
   safe points" (#3), and Claude `/goal` being *implemented as* a Stop hook (#2) all point at
   your "goal hooks replace file hooks" TODO.

---

## 3. Your TODOs → what to read

| Your TODO (from the incomplete prompt) | Read |
| --- | --- |
| Lighter goal origination ("all goal creations trace back to one of…") | #2, #3, #1, #10 |
| Goals tab first; Needs Review / Active / Permanent / Completed sections | #1, #8, #4 |
| "Needs Review" = plan approval + verification | #5, #4, #8, #7 |
| `<enter><enter>` tale/epic approval from the tab | #7, #4, #8 |
| Goal hooks replace file hooks (e.g. `#research_swarm`) | #6, #2, #3, Cursor (HM) |
| `%clan(goal=[[<goal>]])` launched as its own unit | #10, #5, #6 |
| Right panel shows heartbeats for Active prompts/goals | #9, #2, #8, #1 |
| "Permanent" (standing/service) goals | #9 (and OpenClaw), #1 (Routines), Codex app (HM) |
| Purge Completed goals → dismiss agents | #1, #6, #3 |

---

## 4. The ranked list

### #1. Claude Code docs: "Let Claude coordinate ongoing work with Projects"

- **Where:** <https://code.claude.com/docs/en/claude-projects>. Launch coverage: Carl
  Franzen, VentureBeat, **2026-09-17**,
  <https://venturebeat.com/orchestration/anthropic-launches-claude-code-projects-an-always-on-conversation-that-remembers-and-delegates-your-long-running-dev-work>
- **What it is:** "One ongoing conversation where Claude coordinates a stream of related
  work". It has an optional one-line **Goal** (e.g. "Hold p95 API latency under 200 ms"). An
  always-on coordinator routes each message to an answer, a new thread, or an existing
  thread, and "sees what threads report back, not every step they take."
- **Why it's #1:** It is the closest shipped thing to the tab you sketched, released three
  weeks ago.
  - **The Overview pane** groups work as **Ready for review / Waiting on you / Working /
    Landing / Idle / Resolved**.
  - **Recurring work** lives on a separate **Routines** tab, an analog of your "Permanent"
    section.
  - **Threads resolve** when the user resolves them, when Claude finishes the final step
    (such as a merge), or **"automatically after a week with no activity"**. That is a
    shipped answer to your "purge periodically" question.
- **What to look for:**
  - **Section split.** Anthropic separated "Ready for review" from "Waiting on you". Your
    "Needs Review" merges plan approval with verification. Should those be one section or
    two?
  - **Advisory check-ins.** Check-in frequency is set by telling Claude ("Only post when
    something finishes or is blocked"). The docs admit these are "instructions Claude keeps
    to, not enforced settings". Compare that with a host-enforced heartbeat.
  - **Permission prompts.** They block inside the thread, and telling the coordinator "go
    ahead" doesn't reach them. That is a cautionary tale for approve-from-the-tab.

### #2. Claude Code docs: "Keep Claude working toward a goal" (`/goal`)

- **Where:** <https://code.claude.com/docs/en/goal>. Companion: Emilia David, VentureBeat,
  **2026-05-14**, "Claude Code's '/goals' separates the agent that works from the one that
  decides it's done",
  <https://venturebeat.com/orchestration/claude-codes-goals-separates-the-agent-that-works-from-the-one-that-decides-its-done>
- **What it is:** `/goal <condition>` (≤ 4,000 chars) sets one session-scoped goal. It is
  implemented as a prompt-based **Stop hook**. After every turn a *fresh* small model judges
  the condition against the transcript and returns one of three verdicts:
  - **Not yet met:** the reason becomes guidance for the next turn.
  - **Met:** the goal clears and an "achieved" entry is recorded.
  - **Impossible:** the goal clears and a "failed" entry is recorded.

  Idle check-ins start at 30 min and back off to every 2 h, with at most 3 per goal between
  user prompts. Evaluation is skipped while a subagent or background shell is running.
- **Why read it:**
  - **Weight.** It is the purest example of how *little* a goal needs to be.
  - **Separation.** "Completion is decided by a fresh model rather than the one doing the
    work." That bears directly on your claims → Needs Review loop.
  - **Origin.** Your redesign wants every goal to trace back to an origin. Here the origin
    is just the user's sentence.
- **What to look for:**
  - **The "impossible" verdict.** Your current status machine has no first-class "can't be
    done" outcome. It has only `dropped`, which is a human act.
  - **The check-in backoff schedule.** It is a ready-made answer to "how often should an
    Active heartbeat fire?"
  - **Evaluator scope.** "Write the condition as something Claude's own output can
    demonstrate." The evaluator calls no tools, which is the same constraint your evidence
    refs face.

### #3. OpenAI Cookbook: "Using Goals in Codex: Persistent Objectives for Long-Running Work"

- **Where:** <https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex>.
  The page shows no date; goals shipped in Codex 0.128.0 on 2026-04-30 and went GA on
  2026-05-21. Companion with implementation detail: Daniel Vaughan, **2026-05-03**,
  <https://codex.danielvaughan.com/2026/05/03/codex-cli-goal-mode-persistent-objectives-token-budgets-agentic-loops/>
- **What it is:** A goal is durable per-thread state holding the objective, lifecycle,
  budget, and progress. Its states are active, paused, complete, and budget-limited.
  Vaughan's reading of the source adds `unmet` (blocked).
  - **Model permissions:** the model may only *start* a goal or *mark it complete*, and only
    with evidence.
  - **User or system transitions:** pause, resume, clear, and budget-limited.
  - **Continuation:** it fires only at "safe points" (turn finished, thread idle, nothing
    queued).
  - **Spin guard:** a continuation turn with no tool calls suppresses the next one.
  - **Budget:** exhausting it is a *soft stop* that summarizes progress.
- **Why read it:**
  - **A crisp authority split.** It is a clean statement of which transitions belong to the
    agent and which to the human or host. Compare it with `decisions:goals-host-binds`.
  - **A template for writing goals.** It defines a goal by outcome, verification surface,
    constraints, boundaries, iteration policy, and a blocked stop condition. That template
    may be exactly the "lighter" structure your origination step needs.
- **What to look for:**
  - "A Goal is not background autonomy without boundaries. It is a scoped, user-controlled
    completion contract."
  - "A Goal should not be marked complete because the model believes it is probably done."
  - **Failure modes in Vaughan.** Compaction can strip the goal and its audit prompt and
    cause early completion. Plan Mode silently stops continuation. These are useful to know
    before you lean on in-context goal lines.

### #4. "Overseeing Agents Without Constant Oversight: Challenges and Opportunities"

- **Where:** Grunde-McLaughlin, Mozannar, Murad, Chen, Amershi, Fourney (UW / Microsoft
  Research), arXiv 2602.16844, **2026-02-18**, <https://arxiv.org/abs/2602.16844>
- **What it is:** Three user studies of verifying a computer-use agent's results.
  - **Step lists** with interleaved summaries were verbose, and participants missed "small
    but impactful errors".
  - **Of three design probes,** the outcome-focused **Specification** view found the most
    errors and was liked most. The process-focused Flowchart found the fewest.
  - **The final interface** cut error-finding time (g ≈ −0.65) but did not meaningfully
    improve accuracy. When participants missed an error, they were *more* confident
    (g ≈ 0.85).
- **Why read it:** It is the best evidence I found on what a **verification card** should
  look like. That card is the core of your "Needs Review" section.
  - **Spec view layout.** It lists **requirements** (known before the run) and
    **assumptions** (decided during the run). Each item is ✓ / ? / ✗ and links to evidence.
  - **What the agent did NOT do.** One discussion heading reads: "Trace displays can extend
    to show what the agent did not do."
- **What to look for:**
  - "A summary of the high-level process can hide execution errors."
  - **The "bird's-eye view with drill-down" finding.** Use it when you decide what the right
    panel shows for an Active goal.

### #5. Anthropic Engineering: "Harness design for long-running application development"

- **Where:** Prithvi Rajasekaran, **2026-03-24**,
  <https://www.anthropic.com/engineering/harness-design-long-running-apps>. Companion:
  Justin Young, "Effective harnesses for long-running agents", **2025-11-26**,
  <https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents>
- **What it is:** A planner / generator / evaluator harness.
  - **Sprint contract:** before each sprint, the generator and evaluator negotiate a
    **sprint contract**, "agreeing on what 'done' looked like for that chunk of work before
    any code was written". One sprint had 27 criteria.
  - **Evaluator tuning:** out of the box the evaluator would "identify legitimate issues,
    then talk itself into deciding they weren't a big deal and approve the work anyway". It
    had to be tuned toward skepticism.
  - **Simplification:** as models improved, sprints were dropped and the evaluator became a
    single end pass.
- **Why read it:**
  - **Plan approval and verification belong together.** The sprint contract shows why your
    "Needs Review: plan approval + verification" pairing is natural. The contract is the
    plan-time half of the verification.
  - **Harness components are temporary.** The closing principle, "every component in a
    harness encodes an assumption about what the model can't do on its own", is an argument
    for designing Goals machinery that can be *deleted* as models improve. That fits your
    instinct to go lighter.
  - **The companion post** documents the failure of agents declaring victory early. A
    later session would "see that progress had been made, and declare the job done". It
    also describes a JSON feature list in which agents may only flip `passes`.
- **What to look for:** The cost table (solo $9 vs full harness $200) is a reality check on
  stacking evaluators.

### #6. Maggie Appleton: "Gas Town's Agent Patterns, Design Bottlenecks, and Vibecoding at Scale"

- **Where:** <https://maggieappleton.com/gastown>. The page shows no date; it reads
  "planted 8 months ago" and cites a 2026-01-14 post, so roughly February 2026.
  Companions: Steve Yegge, "Welcome to Gas Town" (early January 2026),
  <https://steve-yegge.medium.com/welcome-to-gas-town-4f25ee16dd04>, and "Gas Town: from
  Clown Show to v1.0" (≈ April 2026),
  <https://steve-yegge.medium.com/gas-town-from-clown-show-to-v1-0-c239d9a407ec>. Plus
  Daniel Vaughan's explainer (2026-04-08),
  <https://codex.danielvaughan.com/2026/04/08/gas-town-multi-agent-factory/>.
- **What it is:** A designer's reading of Yegge's beads-based orchestrator. Its ideas:
  - **Hooks and GUPP.** Each worker has a **hook** pointing at its current work. **GUPP**
    says "if there is work on your hook, you must run it".
  - **Durable vs ephemeral work.** **Molecules** are durable chained bead workflows that
    survive restarts. **Wisps** are ephemeral beads destroyed after runs.
  - **Patrol roles.** The Deacon runs patrol cycles, Boot checks the Deacon every 5 minutes,
    and the Witness restarts stalled workers.
  - **A single interface.** The **Mayor** is the human's one point of contact.
- **Why read it:** Gas Town is the system closest to SASE in lineage, since you already use
  beads. Its "hook" concept is a worked example of what "goal hooks" could mean. The
  molecule/wisp split is a ready vocabulary for which completed goals to purge and which to
  keep. Appleton's critique is the part I most want you to see. She calls Gas Town "vibe
  designed", with too many overlapping concepts (polecats, convoys, molecules, wisps,
  rigs…) that only make sense to their author. SASE now has goals, beads, tales, epics,
  clans, swarms, and is adding permanent goals. That is worth a gut check.
- **What to look for:**
  - **Her design-bottleneck thesis:** "You can move so fast you never stop to think." It is
    a good argument for why a goal inventory is valuable at all.
  - **An HN criticism of v1.0:** "Claude would close a Bead, without validating anything."
    Keep it in mind before you couple purge to completion.
  - *Note:* Medium blocked automated fetching, so I verified Yegge's posts only through
    secondary sources (§6).

### #7. "AI Agents Push Humans Out of the Loop"

- **Where:** Margaret Mitchell, Avijit Ghosh (Hugging Face), Samir Passi (Data & Society),
  arXiv 2608.23642, **2026-08-24** (v3 2026-09-06), <https://arxiv.org/abs/2608.23642>
- **What it is:** A position paper. Its central claim: "Oversight degrades the overseer."
  - **How oversight erodes:** repeated approvals breed approval fatigue, System-1 skimming,
    deskilling, and automation and complacency bias.
  - **The feedback loop:** if fast approvals count as success, systems learn to emit
    "confident summaries" and "oversimplified plans that are easy to skim".
- **Why read it:** It is the strongest counterweight to `<enter><enter>` approval and to
  auto-acknowledging answer goals. Its affordances are concrete enough to evaluate against
  your keymap:
  - **Strategic friction.** Examples include pre-commitment, reasoning probes, and offering
    alternatives instead of a bare accept/reject.
  - **Batch review as a diff.**
  - **Behavioral monitoring.** Flag when review time falls while the approval rate stays
    flat, and when the override rate declines.
- **What to look for:** "A reviewer who stops asking questions has likely stopped
  reviewing." Ask whether SASE could cheaply log your own review latency and override rate
  per goal.

### #8. "Human oversight of agentic systems in practice: Examining the oversight work, challenges, and heuristics of developers using software agents"

- **Where:** Dhanorkar, Passi, Vorvoreanu (Microsoft), arXiv 2606.05391, **2026-06-03**,
  <https://arxiv.org/abs/2606.05391>
- **What it is:** Interviews with 17 experienced developers. They found four forms of
  oversight work: **a priori control, co-planning, real-time monitoring, post hoc review**.
  They also found risky heuristics: the plan as a "faithful proxy" for what happened, and
  "passing tests guarantee correctness". Real-time monitoring is rare and leans on indirect
  cues such as unusually long runtimes. "Developers opt for efficient, not perfect,
  oversight."
- **Why read it:** The four forms map almost one-to-one onto your proposed sections:
  - Permanent goals ≈ a priori control;
  - plan approval in Needs Review ≈ co-planning;
  - Active + heartbeats ≈ real-time monitoring;
  - verification ≈ post hoc review.

  That gives you an empirical check on whether the IA covers the work people actually do.
  The "plan as faithful proxy" finding also warns against letting plan approval stand in
  for verification when both share one section.
- **What to look for:** The design implications. They include surfacing constraints early,
  showing timing and memory signals during runs, and mixing intent rationale and proposed
  tests into the diff. These map to the right-panel and review-card content.

### #9. "An Architecture for Long-Horizon Agents: Levels, Ticks and Cascaded Intelligence"

- **Where:** Nijkamp, Koul, Pakhomov, Pang (Salesforce AI Research), arXiv 2609.19519,
  **2026-09-17**, <https://arxiv.org/abs/2609.19519>. Companion: OpenClaw's heartbeat docs,
  <https://docs.openclaw.ai/gateway/heartbeat> (living docs, undated).
- **What it is:** An agent that ran for **10 days** and reproduced a published RL result.
  - **Levels.** It has seven levels indexed by time scale, from tool call to a weekly
    **goal** level (goal, spec, budget). Each level keeps a bounded summary file of the
    level below, with a 1,500-char daily report to the human.
  - **Ticks.** The unit of autonomy is a clocked **tick**, about 1 h. A deterministic
    pre-check skips the wake when nothing is due. A hook refuses to end a session before
    the checkpoint is written. "The principal's answers are kept as standing decisions,
    read at every wake."
  - **Escalation.** Work goes up a model tier only after failing review twice.
- **Why read it:** It is the most rigorous recent treatment of heartbeats for Active goals
  and of standing goals. The level hierarchy is also a candidate shape for "goal → clan
  goal → agent turn".
- **What the companion adds:** OpenClaw adds the practical protocol:
  - **Silent by default:** `NO_REPLY` or `notify: false`.
  - **Skip empty runs:** if the heartbeat checklist is empty, the run is skipped.
  - **Coalesce:** due tasks merge into one turn.
  - **Active hours.**
  - **Explicit split:** "monitor scratch is prompt context, not a scheduler", which
    separates heartbeat from cron.

  OpenClaw's current docs say the old `HEARTBEAT.md` and `HEARTBEAT_OK` are now legacy.
  Most blog posts are out of date on this.

### #10. "Intelligent AI Delegation"

- **Where:** Tomašev, Franklin, Osindero (Google DeepMind), arXiv 2602.11865,
  **2026-02-12**, <https://arxiv.org/abs/2602.11865>
- **What it is:** A framework that treats delegation as a transfer of authority,
  responsibility, and accountability. Tasks are characterized along axes including
  **verifiability** and **reversibility**. Monitoring can be continuous, periodic, or
  event-triggered. Re-delegation has external and internal triggers. Verifiable task
  completion gets its own section.
- **Why read it:** It is the theoretical anchor for two of your choices.
  - **Which goals need a human verify.** Easy-to-verify, reversible goals can be closed
    cheaply. Hard-to-verify or irreversible ones need you.
  - **Why `%clan(goal=…)` should be its own unit.** The paper's "contract-first
    decomposition" (from the tool summary of the later sections, so check the PDF) says to
    decompose only as finely as you can verify. A clan goal is a verification unit.
- **What to look for:** "Dynamic cognitive friction": agents should push back on unclear
  intent instead of propagating it. That argues for the goal-naming step at origination.
  Also note the monitoring taxonomy (continuous / periodic / event-triggered), which maps to
  heartbeat versus hook design.

---

## 5. Honorable mentions (read if a specific question comes up)

- **Kief Morris, "Humans and Agents in Software Engineering Loops"** (martinfowler.com,
  2026-03-04),
  <https://martinfowler.com/articles/exploring-gen-ai/humans-and-agents.html>.
  - **The why loop vs the how loop.** Goals are why-loop objects.
  - **"On the loop."** When an output disappoints, fix the harness that produced it, not the
    artifact. That is a principled reason a rejected goal should feed a *goal hook* or
    harness change, not just a relaunch.
- **Wilson Lin, Cursor, "Scaling long-running autonomous coding"** (2026-01-14),
  <https://cursor.com/blog/scaling-agents>.
  - **Flat coordination failed.** Self-coordination with locks failed, and the agents became
    risk-averse.
  - **What worked.** The planner / worker / judge roles worked.
  - **Open problems.** These include "planners should wake up when their tasks complete",
    which is literally a goal hook, and "We still need periodic fresh starts to combat
    drift".
- **Anthropic, "Measuring AI agent autonomy in practice"** (2026-02-18),
  <https://www.anthropic.com/research/measuring-agent-autonomy>. It has real numbers on
  oversight drift:
  - auto-approve rises from ~20% to >40% of sessions with experience;
  - interrupts rise from ~5% to ~9% of turns;
  - Claude asks for clarification more than twice as often as humans interrupt it.

  Useful for calibrating how much "Needs Review" traffic you will actually tolerate.
- **Karri Saarinen, Linear, "Now Linear writes the code, too"** (2026-06-11),
  <https://linear.app/now/coding-sessions-for-linear-agent>.
  - "The session belongs to the organisation rather than to the person who started it."
  - "You decide where it starts and how far it goes before it's back in your hands."

  It is a clean framing of handing goals off and getting them back.
- **OpenAI, "Introducing the Codex app"** (2026-02-02),
  <https://openai.com/index/introducing-the-codex-app/>. Automations run on a schedule and
  return results to a **review queue**, which is a shipped analog of Permanent goals
  feeding Needs Review. *I could not fetch this page (HTTP 403). The review-queue detail
  comes from a secondary guide.*
- **Mohsen Arjmandi, "The LLM Proposes, the Executive Disposes"** (arXiv 2608.04066,
  2026-08-04), <https://arxiv.org/abs/2608.04066>. It splits goal drift into *commitment
  drift* and *binding drift*. A deterministic Executive owns all state, and "an LLM saying
  done is not an event". The philosophy is close to SASE's "host binds, agents claim". The
  evidence is weak: single author, and zero tasks completed in its benchmark.
- **Birgitta Böckeler, "Understanding Spec-Driven-Development: Kiro, spec-kit, and
  Tessl"** (2025-10-15, just inside the window),
  <https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html>. Her critique fits
  any heavyweight goal or criteria scheme: "one workflow for every task size" (Kiro turned
  a small bug into 4 stories and 16 acceptance criteria), and "I'd rather review code than
  all these markdown files".

---

## 6. Caveats and verification notes

- **Undated pages.** Three primary pages show no date: the Claude Code `/goal` and Projects
  docs, and the Codex Cookbook. I dated them from launch coverage (VentureBeat 2026-05-14
  and 2026-09-17) and from release facts (Codex 0.128.0 on 2026-04-30, GA 2026-05-21).
  OpenClaw's docs are living docs with no date.
- **Partial reads.** Some fetches returned only part of the page verbatim:
  - Projects docs: the first ~40k of ~61k characters;
  - arXiv HTML for #4, #7, and #10: about 39k characters each;
  - Appleton: about the first half of the essay.

  I cite only points from the verbatim portions, except where I flag a point as coming from
  the fetch tool's summary (#10's "contract-first decomposition").
- **Gas Town.** Medium returned HTTP 403 for both Yegge posts. Their dates and contents are
  corroborated only through Leo Simons (2026-01-02), Daniel Vaughan (2026-04-08), and the HN
  threads. The v1.0 date (≈ mid-April 2026) is inferred from relative HN timestamps.
- **Codex state names.** The Cookbook (active / paused / complete / budget-limited) and
  Vaughan (pursuing / paused / achieved / unmet / budget_limited) disagree. The GitHub
  sources that would settle it were not opened.
- **Not considered.** Anything published before 2025-10-05. That excludes several classics
  that would otherwise rank: Anthropic's multi-agent research system post (June 2025),
  "Evaluating Goal Drift in Language Model Agents" (May 2025), and LangChain's "ambient
  agents" (January 2025).
- **Independence.** I did not open or consult any other researcher's report from this
  swarm.
