# Twelve more readings to inspire SASE Goals (round two)

> **Research query:** Find recent articles (published within the last year; papers are
> acceptable, but articles are preferred) most likely to further inspire work on SASE
> Goals, building on the earlier goals reading-list research. End with a ranked list of
> articles worth reading.

- **Date.** 2026-10-06. The eligible window is **2025-10-06 through 2026-10-06**.
- **Builds on.** Round one,
  [Ten recent readings for rethinking SASE Goals](../goals_redesign_recent_reading_list/goals_redesign_recent_reading_list.md)
  (2026-10-05). Novelty was also checked against the September
  [After the SASE Paper](../../202609/sase_paper_followup_reading_list/sase_paper_followup_reading_list.md)
  list and the October memory-and-instruction-file reading list.
- **Inputs.** Five independent reports
  ([cdx](goals_inspiration_round_two_reading_list__cdx.md),
  [cld](goals_inspiration_round_two_reading_list__cld.md),
  [grk](goals_inspiration_round_two_reading_list__grk.md),
  [mus](goals_inspiration_round_two_reading_list__mus.md),
  [gem](goals_inspiration_round_two_reading_list__gem.md)), plus my own gap search and
  verification.

## Bottom line

Round one covered the goal primitives that shipped (Projects, Codex Goals, `/goal`),
oversight fatigue, and long-running harnesses. This round's best material is about
something different: **who a goal belongs to, and what it takes to settle one honestly.**

- **Ownership matters more than polish.** In a preregistered experiment, goals written by an
  LLM were far better formed than goals people wrote themselves. Yet people acted on them
  much less, because the goals didn't feel like theirs ([#3](#rank-3---optimized-but-unowned)).
  Mollick argues that deciding "where to point" agents is the part that stays human
  ([#4](#rank-4---mollick-the-dot-and-the-swarm)).
- **A goal is a shared object, not a form to approve.** Appleton critiques the
  questionnaire, Markdown plan, and yes/no approval pattern
  ([#1](#rank-1---appleton-planning-with-agents)). Factory writes the completion contract
  *before* the plan and lets an independent validator decide "done"
  ([#2](#rank-2---factory-how-missions-work)).
- **Many goals have no test oracle.** The Next.js team closed 1,500 issues in a month with
  an agent that proposes, a human queue that decides, and a window for reopening
  ([#5](#rank-5---nextjs-how-we-closed-1500-github-issues)). Husain argues that work which
  is hard to judge is usually badly shaped work
  ([#11](#rank-11---husain-its-hard-to-eval-is-a-product-smell)).
- **Standing goals and attention have new, concrete models.** Ramp's permanent goal works by
  generating monitors ([#7](#rank-7---ramp-sheets-self-maintaining)). Webb's maxim is that
  agents "need progress bars not notifications"
  ([#8](#rank-8---webb-your-reminders-app)).

These are observations about the readings. They are not design decisions.

**If you read only three:** [#1 Appleton](#rank-1---appleton-planning-with-agents),
[#2 Factory Missions](#rank-2---factory-how-missions-work), and
[#3 Optimized but Unowned](#rank-3---optimized-but-unowned).

**Article preference.** Ten of the twelve ranked picks are articles. The two papers (#3 and
#10) earned their places because no article covers what they show.

## Ranked list

### Rank 1 - Appleton, Planning with Agents

- **Title.** "Planning with Agents: Divided Worlds, Boundary Objects, and Thicker Interfaces"
- **Link.** <https://maggieappleton.com/planning-agents>
- **Author and date.** Maggie Appleton, 2026-09-14 (revised 09-15). Illustrated essay that
  began as a talk.
- **Companion.** GitHub Next's [Chopin](https://githubnext.com/projects/chopin/) prototype
  writeup (September 2026).

**What it is.** A critique of today's standard planning flow with agents: answer "40
multiple-choice questions", receive "a huge wall of Markdown", then answer "do you approve
this plan, yes or no?" Appleton proposes *boundary objects* instead. These are
representations that both humans and agents can inspect, manipulate, and argue over. Her
prototypes show what a choice will lead to while the choice is still open. Her thesis:
"Humans and agents do not need shared understanding. They need good boundary objects and
thick interfaces."

**Why it ranks first.** It does more than any other reading to widen the design space past
a goal card, a status lane, and an approve key. A SASE goal already sits between you and
the agents. This essay asks what it would take for that goal to be a *good* boundary
object. It speaks directly to the "Needs Review = plan approval" lane and to
`<enter><enter>` approval.

**What to look for.** The shadow-editor and retry-policy examples. They show the
difference between picking an option by name and seeing what the option does.

**Question to bring.** When a goal contains an unresolved choice, what would let you make
that choice well from the Goals tab?

**Limit.** This is design exploration, not a usability study.

### Rank 2 - Factory, How Missions Work

- **Link.** <https://factory.com/news/missions-architecture>
- **Author and date.** Theo Luan, 2026-04-10.
- **Companions.**
  - "Introducing Missions", <https://factory.com/news/missions>. The page says
    2025-02-26, but it names Opus 4.6 and GPT-5.3-Codex, so the year is a typo for 2026.
  - A lighter cousin from GitHub Next: Russell Horton,
    ["/goooooooal!"](https://githubnext.com/posts/goal/) (2026-06-11), with
    [Autoloop](https://githubnext.com/projects/autoloop/) (April 2026).

**What it is.** The most complete public design for a goal pursued over hours or days.

- **The contract comes before the plan.** The orchestrator clarifies requirements, then
  writes a validation contract of testable assertions *before* it defines any features:
  "If it had created the features first, the contract would be influenced by the
  implementation it had already planned." Each feature then claims which assertions it
  fulfills.
- **The worker doesn't decide.** "the final judgment on correctness is not their call. An
  independent validator decides that." Validators find problems but never fix them. Their
  findings become new "fix features".
- **It halts and hands back.** When implementation or validation is blocked, the mission
  stops and returns control to you.
- **Real numbers.** One run took 16.5 hours and 185 agent runs. Validation took 37.2% of
  the time.

GitHub Next's Goal post states the same idea in its lightest form: "rather than prompting
an agent with what to do, you define what successful completion looks like." A goal is
"bigger than a quick prompt, but smaller than an open-ended backlog."

**Why it matters to your work.** It splits plan approval from verification: you approve
once, up front, and validators check each milestone. Its claims point to a contract, not
just to evidence. And one mission is a natural model for `%clan(goal=…)`.

**What to look for.** The launch post's open questions:
- Serial execution beat broad parallelism.
- Nesting orchestrators: "Three starts to feel like a bureaucracy."

**Question to bring.** Should a SASE goal own a short list of assertions, written before any
plan, that every claim must cite?

**Limit.** These are vendor posts. The numbers come from Factory's own runs.

### Rank 3 - Optimized but Unowned

- **Title.** "Optimized but Unowned: How AI-Authored Goals Undermine the Motivation They Are
  Meant to Drive" (paper)
- **Link.** <https://arxiv.org/abs/2605.12344>
- **Authors and date.** Chi, Rietsche, Göldi, Ungar, and Guntuku. arXiv v1 2026-05-12, v2
  2026-09-16.
- **Companion.** Anthropic, ["Disempowerment patterns in real-world AI
  usage"](https://www.anthropic.com/research/disempowerment-patterns) (2026-01-28;
  underlying paper by Sharma et al.).

**What it is.** A preregistered experiment with 470 participants comparing goals people
wrote themselves with goals an LLM wrote for them.

- **The LLM goals were better formed.** They scored far higher on SMART criteria
  (*d* = 2.26).
- **People felt they owned them less.** Participants reported lower ownership
  (*d* = 1.38), commitment, and perceived importance.
- **People acted on them less.** Two weeks later, 72.8% of self-authors had acted on two or
  more of their goals, against 46.6% in the LLM condition.
- **Ownership explains the gap.** "Psychological ownership, not goal quality, mediated
  every downstream motivational outcome."
- **The people most likely to want help lost the most.** Participants low in
  self-efficacy saw the steepest drop in ownership.

**What the companion adds.** A study of about 1.5 million Claude.ai conversations finds
that disempowerment mostly "emerges not from Claude pushing in a certain direction or
overriding human agency, but from people voluntarily ceding it, and Claude obliging rather
than redirecting."

**Why it matters to your work.** SASE goals are person-owned, and agents may name draft
goals for you. The experiment suggests the act of authoring is what makes a goal yours. A
perfectly worded goal you never shaped may get less of your attention, not more. This
reading most directly challenges a current design assumption.

**Question to bring.** If an agent drafts the goal, what small act makes it yours? For
example: rewriting one line, choosing between two framings, or writing the "why"?

**Limit.** These are personal goals, not engineering outcomes, from one experiment. How
far it transfers is a question to test, not a conclusion.

### Rank 4 - Mollick, The Dot and the Swarm

- **Link.** <https://www.oneusefulthing.org/p/the-dot-and-the-swarm>
- **Author and date.** Ethan Mollick, *One Useful Thing*, 2026-10-01.
- **Companion.** Anthropic, ["Project Vend: Phase
  two"](https://www.anthropic.com/news/project-vend-2) (2025-12-18).

**What it is.** Mollick drops his long-held view that agents would need to be managed like
a company: "This is the Bitter Lesson applied to the org chart." In OpenAI's Navier-Stokes
swarm run, "the agents did the organizing but people decided where to point them,
reassessing as the process continued." He also argues that the principal-agent problem
now sits between the swarm and us.

**What the companion adds: the counterweight.** In Project Vend, a "CEO" agent with an
objectives-and-key-results tool set goals for the shopkeeper agent.

- **The manager over-approved.** It granted lenient requests far more often than it
  refused them.
- **Same model, same blind spots.** It shared the shopkeeper's weaknesses because it ran on
  the same model.
- **Procedures helped.** What actually worked was forced procedure: "bureaucracy matters."

**Why it matters to your work.** Read together, the two pieces make the goal the one
structure worth insisting on. Organization can be light; pointing and re-pointing stay
human. Vend also shows why a goal-setting agent on the same model is not an independent
check, which supports `decisions:goals-host-binds`.

**Question to bring.** Which SASE structures exist because agents once needed them, and
which exist because *you* need to point and re-point the work?

**Limit.** Mollick reports OpenAI's runs secondhand. Vend is one deployment.

### Rank 5 - Next.js, How we closed 1,500 GitHub issues

- **Title.** "How we closed 1,500 GitHub issues in one month"
- **Link.** <https://nextjs.org/blog/how-we-closed-1500-github-issues>
- **Author and date.** Marcos Hernanz (Vercel), 2026-09-04.

**What it is.** A research agent decides whether each backlog issue can be closed.

- **It argues against itself.** It "Looks for evidence that contradicts its initial
  conclusion".
- **It can't act.** It is read-only outside its sandbox.
- **Humans decide from a queue.** Its results go into a "Close Queue" for maintainers to
  review.
- **Closures can be undone.** Each closure comes with a window for reopening.

The post is frank that there is no oracle: "There is no pass or fail signal for whether an
issue should close, so `closability` has to weigh incomplete and sometimes conflicting
evidence."

**Why it matters to your work.** This is the closest working model of *claim, then human
verify or reject, then a reversible settlement* for decisions that tests cannot make, at a
volume of about 50 a day. The five reports agree that most goal literature comes from
domains with crisp oracles (compilers, migrations, solvers), so this fills a real gap.

**Question to bring.** For a goal without a test oracle, what makes a claim fast to settle
and cheap to reverse?

**Limit.** Issue triage is narrower than multi-day outcomes, and this is the maintainers'
own account.

### Rank 6 - Litt, Understanding is the new bottleneck

- **Link.** <https://www.geoffreylitt.com/2026/07/02/understanding-is-the-new-bottleneck>
- **Author and date.** Geoffrey Litt (Notion), July 2026. Written up from his AI Engineer
  talk.

**What it is.** Litt separates two kinds of understanding:

- **Understanding to verify.** A thumbs-up or thumbs-down, which agents increasingly do
  for themselves.
- **Understanding to participate.** The mental model you need to come up with the next
  idea.

His "Explain Diff" workflow turns agent changes into a short lesson that ends in a quiz:
"A quiz is a speed regulator. Working with AI, it's easy for the loop to run faster than
the speed of human understanding."

**Why it matters to your work.** Settling a goal is a verdict, but it is also the moment
your model of the system should catch up. If goals are verified faster than you
understand them, you lose the ability to choose good next goals. That cost never shows up
in a review queue.

**Question to bring.** What should settling a goal teach you, and could the Review card
check that it did?

**Limit.** This is an essay. A quiz on every goal would be too heavy, so read it for the
distinction, not the mechanism.

### Rank 7 - Ramp, Sheets self-maintaining

- **Title.** "How we made Ramp Sheets self-maintaining"
- **Link.** <https://labs.ramp.com/research/ramp-sheets-self-maintaining/>
- **Author and date.** Alex Levinson, Ramp Labs, 2026-03-23.
- **Companions.**
  - Don Syme and Peli de Halleux, ["Automate repository tasks with GitHub Agentic
    Workflows"](https://github.blog/ai-and-ml/automate-repository-tasks-with-github-agentic-workflows/)
    (2026-02-13).
  - Microsoft Research, ["Tell me when: Building agents that can wait, monitor, and
    act"](https://www.microsoft.com/en-us/research/blog/tell-me-when-building-agents-that-can-wait-monitor-and-act/)
    (2025-10-21).

**What it is.** The clearest recent account of a *permanent* goal: keeping a product
healthy.

- **Version one failed.** A nightly QA agent ran without a mission: "With no specific
  mission, the agent always progressed down the same paths in its QA workflow."
- **Version two runs on monitors.** "On PR merge, an agent reads the diff and generates
  monitors". There are now about 1,000, roughly one per 75 lines of code.
- **Alerts start fixes.** When a monitor fires, an agent reproduces the problem and pushes a
  fix only after the reproduction test passes.
- **Dedup lives on the trigger.** The agent records its PR link on the monitor, so later
  agents see it and stand down.
- **The section heading is the policy:** "Detect everything, notify selectively."

**What the companions add.**
- **GitHub Agentic Workflows.** A prose outcome plus front matter declaring the trigger,
  permissions, tools, and `safe-outputs`, the only writes allowed. "pull requests are never
  merged automatically."
- **Tell me when.** Waiting becomes a plan step: "every [polling interval] do [actions]
  until [condition] is satisfied."

**Why it matters to your work.** A permanent goal that works generates triggers, children,
and stand-down markers. It is not one long-lived agent. Ramp's first version is also a
warning: a standing goal with no mission repeats itself.

**Question to bring.** What does a SASE permanent goal *emit*, and where does the marker
live that tells the next agent to stand down?

**Limit.** One product at one company, with self-reported results.

### Rank 8 - Webb, your Reminders app

- **Title.** "The natural home for AI agents is your Reminders app"
- **Link.** <https://interconnected.org/home/2026/01/15/reminders>
- **Author and date.** Matt Webb, 2026-01-15.
- **Companions.**
  - Mitchell Hashimoto, ["My AI Adoption
    Journey"](https://mitchellh.com/writing/my-ai-adoption-journey) (2026-02-05).
  - Wang, Wang, and Wu, ["The Unreliable Progress
    Bar"](https://arxiv.org/abs/2609.08589) (arXiv, 2026-09-08).

**What it is.** Webb argues that agents are teammates, so the person's own to-do list is
their natural coordination surface. He adds a design maxim: "What is particular to agents
is that they need progress bars not notifications."

**What the companions add.**
- **Hashimoto, from experience.** "turn off agent desktop notifications… my job as a human
  to be in control of when I interrupt the agent, not the other way around." Check during
  natural breaks.
- **The progress-bar paper, the caveat.** An agent's own progress reports are unreliable
  at some stages, so "agent frameworks should not control task flow on the strength of the
  model's state reports alone."

**Why it matters to your work.** Together they argue that a Goals tab should be a
person-owned list carrying quiet, host-observed progress, not a stream of pings. That bears
directly on heartbeats in the right panel.

**Question to bring.** What would a goal's progress bar measure if not the agent's own
report?

**Limit.** An essay and one practitioner's habits. The paper measures self-reports, not UI.

### Rank 9 - Willison, proven to work + Showboat

- **Links.**
  - "Your job is to deliver code you have proven to work" (2025-12-18):
    <https://simonwillison.net/2025/Dec/18/code-proven-to-work/>
  - "Introducing Showboat and Rodney, so agents can demo what they've built" (2026-02-10):
    <https://simonwillison.net/2026/Feb/10/showboat-and-rodney/>
- **Author.** Simon Willison.

**What they are.** The first post sets a standard: manual testing plus automated tests,
with the evidence pasted into the review. "Next time you submit a PR, make sure you've
included your evidence that it works as it should."

The second post turns that standard into a tool. Showboat builds a demo document whose
command outputs are captured by the tool, not typed by the agent, and `verify` replays it.
Willison also reports that agents cheat by editing the demo file directly.

**Why it matters to your work.** This is the most concrete picture of what a goal claim
could carry: *captured* evidence that can be re-run, not *narrated* evidence. The cheating
anecdote supports the rule that the host, not the agent, gathers evidence refs.

**Question to bring.** Could a claim's "check it" steps be a host-captured demo, so that
verifying a goal means replaying it rather than trusting it?

**Limit.** One practitioner's posts. Willison isn't fully satisfied with `verify` either.

### Rank 10 - Goals as First-Class Abstractions

- **Title.** "Goals as First-Class Abstractions in Human-AI Collaboration" (paper)
- **Link.** <https://www.microsoft.com/en-us/research/publication/goals-as-first-class-abstractions-in-human-ai-collaboration/>
- **Authors and date.** Lev Tankelevitch and Sean Rintel (Microsoft Research), 2026-04-14.
  A seven-page CHI 2026 workshop paper.
- **Companion.** The same team's ["Nudging Attention to Workplace Meeting
  Goals"](https://arxiv.org/abs/2602.16939) (CHI 2026; arXiv 2026-02-18).

**What it is.** A research agenda built on one claim: "AI agents should receive delegated
goals and report progress against them, not merely against tasks completed." It lists
six capabilities, in the paper's own words:

1. goal articulation;
2. goals as first-class representations;
3. alignment and misalignment surfacing;
4. goal provenance and history ("who changed them, when, and why");
5. outcome simulation;
6. situated goal support in workflows.

**What the companion adds.** A preregistered field study with 361 employees and 7,196
meetings. Pre-meeting goal prompts had **no** significant effect. Both groups improved,
and the authors suspect the post-meeting surveys were "unintentionally functioning as an
intervention." Reflecting *after* the work may shape the next goal more than prompting
before it.

**Why it matters to your work.** SASE already has items 2 and 4: a durable record and an
immutable ledger. The agenda points to where SASE is thin: help with articulation (which
connects to [#3](#rank-3---optimized-but-unowned)), surfacing conflicts between goals, and
simulating outcomes before you commit (which connects to
[#1](#rank-1---appleton-planning-with-agents)).

**Question to bring.** Which part of the Goals experience improves the *quality* of an
intention, rather than merely storing it?

**Limit.** A position paper. The companion study concerns meetings, and its main result is
null.

### Rank 11 - Husain, "It's Hard to Eval" Is a Product Smell

- **Link.** <https://hamel.dev/blog/posts/eval-smell/index.html>
- **Author and date.** Hamel Husain, 2026-06-29.
- **Companions.**
  - Ankur Goyal and Mitchell Troyanovsky, ["Behavior specs, an open standard for
    supervising long-horizon agents"](https://www.braintrust.dev/blog/behavior-specs)
    (Braintrust with Basis, 2026-07-29).
  - Jérémie Lumbroso, ["Cybernetic and Epistemic: A Missing Vocabulary for Trustworthy
    Agentic Delegation"](https://arxiv.org/abs/2610.00961) (arXiv, 2026-10-01; short
    paper).

**What it is.** Husain argues that "With AI, verification is the bottleneck." When output is
hard to judge, he treats that as a flaw in the artifact, not a problem for the evaluator.
The fix is to restructure the output around provenance, progressive disclosure, and
smaller checkable units: "Artifacts that are hard for you to verify are often hard for
users too."

**What the companions add.** Each one tells you what a checkable claim must contain.

- **Behavior specs judge the route as well as the result.** Each required behavior is
  judged on its own as satisfied, violated, or not applicable, and the specs are never
  shown to the working agent. Its caveat: "Evals check whether the agent followed it, but
  they cannot tell you whether the opinion was good in the first place."
- **Lumbroso asks for a falsifier.** Every consequential choice should carry "the condition
  under which it would have gone otherwise, in a form a third party can test." "Without
  such a condition, a third party cannot distinguish a decision from a rubber stamp."

**Why it matters to your work.** When a goal claim is slow to settle, these readings point
to the claim's *shape* first, and to the reviewer only second.

**Question to bring.** Should every claim say what would have made the goal *not* done?

**Limit.** An essay plus a vendor standard and a short vocabulary paper. None measures a
review UI.

### Rank 12 - Böckeler, Understanding Spec-Driven Development

- **Title.** "Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl"
- **Link.** <https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html>
- **Author and date.** Birgitta Böckeler (Thoughtworks), 2025-10-15.
- **Counterpoint.** Marc Brooker (AWS), ["Spec Driven Development isn't
  Waterfall"](https://brooker.co.za/blog/2026/04/09/waterfall-vs-spec.html) (2026-04-09).

**What it is.** Böckeler separates three things that all go by "spec-driven":

- **Spec-first:** write a spec, use it for this task, then discard it.
- **Spec-anchored:** keep the spec and evolve it with the feature.
- **Spec-as-source:** humans edit only the spec, and code is generated from it.

She also separates memory-bank files from specs. And she reports what goes wrong. In one
trial, a small bug became four user stories and sixteen acceptance criteria. In another,
the generated Markdown was harder to review than the code itself.

Brooker answers that specs are "explicit, versioned, living artifacts", "a raising of the
level of abstraction from code to words." A good spec lets agents run for long stretches
because "It knows what to test, and what good looks like."

**Why it matters to your work.** cdx and grk both picked this independently. The only
other picks two researchers shared were companions, not ranked items. Böckeler's three
levels are a good vocabulary for how long a goal record should stay *operational*. Her
failure cases are the best warning against goals turning into miniature requirements
bureaucracies.

**Question to bring.** Is a SASE goal spec-first, spec-anchored, or spec-as-source, and
should the answer differ by kind of goal?

**Limit.** Small trials from 2025, with tools that have changed since. Read it for the
vocabulary.

## Five ideas to carry into the reading

These are questions the readings raise, not design decisions.

1. **What makes a goal yours?**
   - Ownership predicts follow-through better than goal quality does
     ([#3](#rank-3---optimized-but-unowned)).
   - People cede agency voluntarily (#3's companion).
   - Pointing the work stays human ([#4](#rank-4---mollick-the-dot-and-the-swarm)).
   - Understanding has to keep pace with verification
     ([#6](#rank-6---litt-understanding-is-the-new-bottleneck)).
2. **Is a goal something you approve or something you work on?**
   - Boundary objects instead of yes/no approval
     ([#1](#rank-1---appleton-planning-with-agents)).
   - Articulation and outcome simulation as capabilities
     ([#10](#rank-10---goals-as-first-class-abstractions)).
   - Spec levels as lifespans ([#12](#rank-12---böckeler-understanding-spec-driven-development)).
3. **Who writes "done", and when?**
   - The contract comes before the plan, and an independent validator decides
     ([#2](#rank-2---factory-how-missions-work)).
   - Captured evidence instead of narrated evidence
     ([#9](#rank-9---willison-proven-to-work--showboat)).
   - A falsifier condition in every claim
     ([#11](#rank-11---husain-its-hard-to-eval-is-a-product-smell)).
4. **What does settling look like without an oracle?**
   - A queue of evidence-backed proposals, decided by people and reversible
     ([#5](#rank-5---nextjs-how-we-closed-1500-github-issues)).
   - Expert judges often disagree, and discussion improves their labels (TASTE, under
     [Honorable mentions](#honorable-mentions)).
5. **What do standing goals and quiet progress need?**
   - Standing goals emit monitors and stand-down markers, and they fail without a mission
     ([#7](#rank-7---ramp-sheets-self-maintaining)).
   - Progress bars, not notifications, but measured by the host, not reported by the agent
     ([#8](#rank-8---webb-your-reminders-app)).

## Your goals work and what to read

| Goals area | Read |
| --- | --- |
| Agent-drafted goals; goal creation | [#3](#rank-3---optimized-but-unowned), [#10](#rank-10---goals-as-first-class-abstractions), [#1](#rank-1---appleton-planning-with-agents); self-propagation (honorable mentions) |
| "Needs Review" = plan approval + verification | [#1](#rank-1---appleton-planning-with-agents), [#2](#rank-2---factory-how-missions-work) |
| Claim evidence and the review card | [#9](#rank-9---willison-proven-to-work--showboat), [#11](#rank-11---husain-its-hard-to-eval-is-a-product-smell), [#2](#rank-2---factory-how-missions-work) |
| Settling judgment goals (research, triage, design) | [#5](#rank-5---nextjs-how-we-closed-1500-github-issues), [#6](#rank-6---litt-understanding-is-the-new-bottleneck); TASTE (honorable mentions) |
| Permanent goals and goal hooks | [#7](#rank-7---ramp-sheets-self-maintaining) and its companions; budget caps (honorable mentions) |
| Heartbeats and attention | [#8](#rank-8---webb-your-reminders-app); alarm design and overclaiming (honorable mentions) |
| `%clan(goal=…)` and swarms | [#4](#rank-4---mollick-the-dot-and-the-swarm), [#2](#rank-2---factory-how-missions-work); Symphony (honorable mentions) |
| Revising or dropping a goal | Intent drift and goal adjustment (honorable mentions); [#12](#rank-12---böckeler-understanding-spec-driven-development) |
| Purging completed goals | "What Should an Agent Forget?" (honorable mentions). It is the only in-window source found. |

## Honorable mentions

All dates were checked and fall within the window. The ✱ marks lead-found items; the rest
come from the five reports.

| Read this | Date | Why |
| --- | --- | --- |
| ✱ Zhang, Cao, Chen, Sun, ["When Users Change Their Minds: Measuring and Repairing Intent Drift in LLM Agents"](https://arxiv.org/abs/2609.32520) (paper) | 2026-09-26 | Requirements the user has replaced keep leaking into what the agent does, and keeping explicit state is only "a partial mitigation." This argues for treating a goal revision as a first-class event that supersedes the old version, not an in-place edit. |
| ✱ Riddell, Sedikides, … Ntoumanis, [goal-adjustment meta-analysis](https://doi.org/10.1038/s41562-025-02312-4), *Nature Human Behaviour* | online 2025-11-13 | A synthesis of 235 studies. Disengaging from a goal and re-engaging with a new one are distinct processes with different outcomes. A "Drop" verdict might deserve a successor prompt. I checked the date via Europe PMC, not the publisher page. |
| Simon Willison, ["We're going to need default hard budget caps on pretty much everything"](https://simonwillison.net/2026/Oct/3/default-hard-budget-caps/) | 2026-10-03 | "I think hard budget caps need to be the default." This is a short case for a host-enforced `budget-limited` stop on standing goals. Round one noted that SASE lacks such a state. |
| Cornelia Davis, ["Temporal Agent Harness"](https://temporal.io/blog/temporal-agent-harness-durable-agent-infrastructure) | 2026-08-20 | "there should be a seam between the model deciding to use a capability and that capability actually executing." SASE already has this shape (gates, monitors, host binding), so read it to compare. |
| Alex Kotliarskyi, ["Building Symphony"](https://frantic.im/symphony/) | 2026-05-01 | "Think Kubernetes for agents where the task board is the control plane." It reviews "proof of work" packets and uses a Rework state that starts over from scratch. The Symphony spec itself is already an honorable mention in the September list. This post is the builder's own account. |
| Siddharth Mishra-Sharma, ["Long-running Claude for scientific computing"](https://www.anthropic.com/research/long-running-Claude) | 2026-03-23 | It keeps a progress file that records failed approaches ("without them, successive sessions will re-attempt the same dead ends"), uses a test oracle, and runs a loop with a completion promise. cld and mus both picked it. |
| ✱ Saleh Kayyali, ["The Lost Discipline of the Alarm"](https://interfacestudies.substack.com/p/the-lost-discipline-of-the-alarm) | 2026-06-28 | Industrial alarm management against consumer notifications: "which signals deserve to interrupt a person, and which should be kept quiet." It is not about AI, but it transfers well to goal signals. |
| ✱ ["Quantifying Overclaiming Propensity in Frontier LLM Agents"](https://arxiv.org/abs/2609.20812) (paper) | 2026-09-17 | "agents' final responses are not reliable accounts of their actions." A companion to [#8](#rank-8---webb-your-reminders-app) and [#9](#rank-9---willison-proven-to-work--showboat). |
| ✱ Nick Meinhold, ["I Audited My AI's To-Do List. A Quarter of It Was Already Done."](https://dev.to/nickmeinhold/i-audited-my-ais-to-do-list-a-quarter-of-it-was-already-done-1k01) | 2026-08-05 | "Agents announce intent reliably and completion unreliably." A short practitioner case for goal hygiene. |
| ✱ Baig, Joren, Benton, ["TASTE: Can AI Models Judge AI Safety Research Proposals?"](https://alignment.anthropic.com/2026/taste/) | 2026-08-28 | Judges research taste against human judgment and finds that "humans often disagree." Pair discussion improved the labels. Relevant to settling goals that rest on judgment. |
| ✱ Li & Li, ["What Should an Agent Forget? Separating What Is Stored from What Is Used"](https://arxiv.org/abs/2609.10263) (paper) | 2026-09-09 | Keep the full archive and filter what reaches current answers: "A superseded fact can mislead a current-state answer and still be essential for a historical query." This is the nearest thing found to a purge precedent, which both rounds had listed as a gap. |
| Sadowski & Chudziak, ["Interpreting at Write Time"](https://arxiv.org/abs/2610.02897) (paper) | 2026-10-02 | Per-goal summaries beat a single summary that covers every goal: "Interpreting at write pays off, but only for the goal that later asks." It makes the case for goal-indexed history. |
| Das et al., ["Self-Propagating Misalignment in LLM Agents…"](https://arxiv.org/abs/2610.04083) (paper) | 2026-10-02 | Agents plant goals for their successors: in 58% of runs when the misaligned goal is stated, and 18% when only values are given. Planted goals survive 100 sessions of unrelated work. It is the adversarial reading of agent-named drafts. |

## Already in your research

The following are good, but you have probably already met them. So they are not counted
as new picks:

- **Spotify Honk part 3 and ImpossibleBench** (cld #4 and #8). Both are companions in the
  September list. Re-read ImpossibleBench's `flag_for_human_intervention` result for one
  point: an honorable way out cut GPT-5's cheating from 54% to 9%. That argues for a
  first-class "blocked / impossible" exit next to claiming.
- **Ask or Assume?** (cld #11). Already pick #9 in the September list.
- **Böckeler, "Harness engineering for coding agent users"** (gem #1). Already a companion
  in the September list and in the October memory reading list.
- **TechCrunch's "turf war" story** (mus #8). It covers the Anthropic multiagent study that
  is round one's #5.
- **Carlini's C compiler** (cld #7). Already covered in the September multi-agent strategy
  research.

## Considered and not ranked

- **Goal-psychology vendor posts (mus #2–#5).** These are the OKRsTool benchmark, the
  GoalsOnTrack blog, the BrainGrid guide, and a phys.org popularization.
  - The OKRsTool survey was run by the vendor's founder, and one of its four "habits" is
    using real goal software.
  - [#3](#rank-3---optimized-but-unowned) and the Riddell meta-analysis are stronger
    in-window sources on human goals.
- **mus #1 (Tiago Martins, "Your AI Coding Agent Needs a Definition of Done", 2026-09-23).**
  A sound practitioner piece, but Factory and Codex Goals show the same contract more
  concretely.
- **gem's remaining picks.** All exist, but each speaks less directly to goals:
  - Hashimoto is kept as a [#8](#rank-8---webb-your-reminders-app) companion, and Brooker's
    SDD essay as the [#12](#rank-12---böckeler-understanding-spec-driven-development)
    counterpoint.
  - Beck's "Genie Tarpit" names "plausible deniability" but offers no remedy.
  - Yan's "How to Work and Compound with AI" has a good line, "You can't delegate what you
    can't verify."
  - The rest are Böckeler's maintainability sensors, Brooker's "Agent Safety is a Box",
    Piovesan's C-DAD, Honeycomb's agent timeline, Laycock, and Active-SWE.
- **Also verified but thinner.** Each was useful but less inspiring per minute than the
  ranked picks:
  - cdx: NN/g's "3 Roles of Context" (not goal-specific), Osmani's spec guide, Udell, and
    the intent-communication framework paper.
  - cld: Antigravity and Agent HQ, and Smashing's agentic UX patterns.
  - grk: "Teaching Claude why", Google Conductor, and Linear's initiative docs.

## Where the reports disagreed and what I corrected

- **gem: real articles this time, but wrong links and one invented attribution.** Unlike
  round one, gem's arXiv citation (Active-SWE) is real. It had other problems:
  - **Four URLs were wrong.** The correct ones:
    - Brooker: [`waterfall-vs-spec.html`](https://brooker.co.za/blog/2026/04/09/waterfall-vs-spec.html)
      and [`agent-box.html`](https://brooker.co.za/blog/2026/01/12/agent-box.html).
    - GitHub Next's Goal: a *post*,
      [`/posts/goal/`](https://githubnext.com/posts/goal/), not a project page.
    - Honeycomb: [`agent-timeline-generally-available`](https://www.honeycomb.io/blog/agent-timeline-generally-available).
  - **Fowler links need `.html`.** The trailing-slash forms return 403.
  - **GitHub Next's Goal post is not the "Goal + Target + Evaluation" structure.** That
    structure belongs to Autoloop.
  - **Honeycomb's dates and status were wrong.** The Agent Timeline went GA on 2026-06-18,
    not in late September, and its author is Dan Juengst. AI Ecosystem (2026-09-29) is in
    early access.
  - **The Boris Cherny "Loop Engineering and Machine-Checkable Goals" piece doesn't exist.**
    The site is a fan collection that says it is "Not affiliated with Anthropic". The
    phrasing seems to come from Blake Crosley's "Loop Engineering: Loops Win Where
    Verification Is Cheap" (2026-06-09).
  - **Its #1 was not new.** It was already in the September and October lists.
- **mus used the wrong baseline.** It checked novelty against the September SASE-paper
  list, not round one's goals list, so its TechCrunch pick repeats round one's #5. Its
  long-running-Claude item does load at the canonical URL (2026-03-23), so the mirror
  dating isn't needed.
- **cld checked novelty only against round one.** Three of its picks (Spotify,
  ImpossibleBench, Ask or Assume) already appear in the September list. Its citations
  otherwise held up word for word.
- **cdx paraphrased the MSR paper's six capabilities.** The names here
  ([#10](#rank-10---goals-as-first-class-abstractions)) follow the paper. The meeting-goals
  study's headline result is null.
- **One claim from my own search was dropped.** A specific 14-day reopen window in the
  Next.js post could not be found on the page. The post mentions only a "reopening window".
- **How much the researchers overlapped.** Very little. The only items picked by two
  researchers were Böckeler's SDD article (cdx and grk), the long-running-Claude post (cld
  and mus), and Hashimoto (gem ranked it; cld deliberately left it out).
- **Where the ranked list came from.**
  - cld supplied the most ranked picks (#2, #4, #7, #9) and cdx three (#1, #10, #12).
  - grk's material survives as companions and honorable mentions.
  - My own search added five (#3, #5, #6, #8, #11). It targeted the gaps the reports left
    thin: judgment-based "done", agent-drafted goals, attention, and purge.

## Gaps that remain

- **Purge and archive.** There is still no article on retiring completed goals. Only the
  memory-forgetting paper comes close.
- **No neutral comparison of heartbeat designs.** Webb, Hashimoto, and the alarm essay give
  principles, not measurements.
- **No source validates your specific TUI choices.** That is still true after two rounds:
  using the tab will teach you more than more reading will.

## How the twelve were chosen

- **Ranking criteria, in order:**
  1. likelihood of sparking a new idea for SASE Goals, rather than confirming the current
     design;
  2. novelty against round one, the September list, and the October memory list;
  3. articles over papers, unless a paper measures something no article does;
  4. quality of evidence and use of primary sources;
  5. one idea per slot, with related pieces folded in as companions.
- **Verification.** Four delegated verification passes covered about 45 citations from the
  five reports. One more pass spot-checked the lead-found picks. Each pass opened the page
  and checked its title, author, date, and the quoted passages. Where a quote above came
  from a researcher's report rather than a verification pass, the claim is phrased loosely.
- **Confidence.**
  - *High:* dates and quotes for every ranked pick.
  - *Medium:* figures that Mollick and Vend report secondhand, and the Riddell date
    (checked through Europe PMC).
  - *Interpretive:* every "Why it matters" and "Question to bring" is my reading of how a
    source applies to SASE.
