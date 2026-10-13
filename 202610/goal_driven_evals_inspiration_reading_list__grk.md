# Goal-driven evals for SASE: a reading list to think with

> **Research query:** I am thinking about implementing some form of evals for SASE,
> likely using goals (which do not exist as product yet). Databricks research first
> suggested this. Favor recent goals research over earlier thrash. Also see my
> annotations on Microsoft Research's *Goals as First-Class Abstractions*. I am new
> to evals and still thinking through goals. Find articles and papers that inspire
> me / help me think through all of this. End with a ranked reading list.

**Researcher:** grk · 2026-10-13
**Kind:** reading-list research (evals × goals)
**Builds on:** Databricks NYC eval-pilot sketch (2026-10-10); Goals redesign
reading list (2026-10-05); Goals inspiration round two (2026-10-06); MSR *Goals
as First-Class Abstractions* (finished 2026-10-13, 13 comments); September
goal-outcomes research as older baseline only.

This is an independent report in a five-researcher swarm. I did not read the
other researchers' reports for this request.

---

## Bottom line

A SASE eval is a **frozen, replayable goal**. That is the idea that ties the
Databricks task-success gap to the Goals work you have been circling.

You already have **harness-reliability** signals: `fakey`, ToolRun triage,
verdict receipts, two-speed CI. You do not have **task-success** evals: did
the agent actually achieve the outcome the person named? The Databricks NYC
report called that the remaining gap for Agent Quality interviews. Your
annotation on the MSR paper named the join: "Use goals to drive evals that
databricks research recommended!"

The literature, read against SASE's own decisions (`goals-host-binds`,
`goal-ledger`, `receipts-prove-before-they-skip`, `host-owned-completion`),
points to **three layers**, not one dashboard:

1. **Harness evals** (you already run these). Does the plumbing work? Did
   `just check` run, and did a receipt prove it?
2. **Goal-outcome evals** (the Databricks 8–12-task pilot). Freeze a start
   commit, a prompt snapshot, and a short list of assertions. Replay. Grade
   the world, not the agent's story.
3. **Goal-process evals** (later). Grade the trajectory: did it verify before
   claiming, stay in scope, take the honest blocked exit? Outcome-only scores
   treat a principled fix and a Lucky Pass as the same thing.

Human settlement stays the **outer loop**. Automated graders are the **inner
loop**. An agent may claim; only you settle. That is already
`goals-host-binds`. It is also the Berkeley *Reality Is the Final Verifier*
split: the inner loop can close the evaluation gap; the requirement gap
needs a human.

**If you read only three:** [#1 Anthropic, Demystifying evals](#rank-1---anthropic-demystifying-evals)
(already queued in your library), [#2 Hamel, eval-smell](#rank-2---hamel-hard-to-eval-is-a-product-smell)
(not in the library — this is the product-design piece), and
[#3 Factory Missions](#rank-3---factory-missions). Then steal the six-part
contract from [#4 Codex Goals](#rank-4---codex-goals-cookbook) when you write
the first frozen goals.

**Do not start** with an LLM-as-judge dashboard, MLflow scorers, or a
pass@k leaderboard. Start with 8–12 binary coding tasks, an independent
validator, a contract written *before* the implementation, failures kept in
the denominator, and `pass^k` once you care about reliability.

---

## 1. What you already decided, and what is still open

### The Databricks gap

The 2026-10-10 Databricks NYC report is the first place this swarm's lineage
says "build evals." The Agent Quality posting wants "trustworthy, reproducible
signals" and "how LLM or agent quality is measured." SASE's pitch on the first
is strong (ToolRun records, NEW/KNOWN/FLAKY/UNKNOWN, KNOWN needs an independent
witness, `fakey`, flake-baseline). The second is empty. The prescribed close:

- 8–12 coding tasks with **frozen start commits** and explicit success checks
  (tests pass, the change stays in scope, required artifacts exist)
- timeouts and failed runs stay in the **denominator**
- record harness, model, version, and prompt; repeat a subset to show variance
- log traces if they help; keep `fakey` conformance **separate** from
  real-agent success
- report per-task outcomes and one regression localized from a trace

That is a weekend-scale capability eval, not a product. It is the right first
object. The open question this report answers is what that object *is* once
Goals exist.

The private `bbugyi200/job--research` repo, opened for this turn, holds job
and CV work from October 2026. It does not hold a separate evals corpus. The
evals suggestion lives in the SASE research sidecar, in the Databricks NYC
files.

### Goals, as of the last two weeks

September's goal-outcomes report (`research:202609/goal_outcomes_and_verification`)
already had the right split: an agent `close` is a **claim**; `verified` /
`waived` / `canceled` / `superseded` are human terminal states; evidence is
policy-sensitive (a reply can evidence an answer; a code change needs a
finalized stitch plus any required receipts). Treat that as the older
baseline. You have thrashed the requirements since then.

Favor the October reading lists. Round one (2026-10-05) found the shipped
goal primitives: Claude Code Projects, Codex Goals, `/goal`, and the
Anthropic planner/generator/evaluator harness. Round two (2026-10-06) found
the settlement question: who a goal belongs to, and what it takes to settle
one honestly. Factory Missions, Appleton's boundary objects, Hamel's
"hard to eval is a product smell," and ImpossibleBench's honest abort all
landed there as goal readings. They are eval readings too.

Shipped SASE decisions that this eval story has to obey:

| Decision | What it forces on evals |
| --- | --- |
| `goals-host-binds` | The host binds every LLM turn to exactly one goal. Agents claim. Humans settle. An eval that lets the worker grade itself is the same bug as an unbound agent. |
| `goal-ledger` | A goal is its own Rust-owned domain: immutable events plus live markers. An eval trial should be a frozen slice of that ledger (prompt snapshot, start commit, assertions, claim, receipts), not a bead with a score column. |
| `receipts-prove-before-they-skip` | A receipt proves one named tool ran with one trustworthy verdict on one fingerprint. It never skips execution. Eval "success" that cites a receipt still has to have run the child. |
| `host-owned-completion` | The agent submits a declaration; the host acts. An eval harness should replay through the same finalizer path, not a side channel that bypasses it. |
| `triage-annotates-does-not-change-exit-codes` | Graders annotate. They do not rewrite the outcome. |

### The annotation that names the join

You finished the MSR paper today. The evaluative paragraph on page 3 is the
one you tagged for this work:

> Finally, goals enable evaluation: they provide benchmarks for success and
> iterative improvement. In human-AI collaboration, this evaluative function
> is bidirectional: goals let humans assess AI outputs against intended
> outcomes and let AI provide goal-referenced feedback to human
> collaborators.

Your comment: **"Use goals to drive evals that databricks research
recommended!"**

Other comments on that paper that should shape the eval object, not just
the Goals tab:

- Goals are **"at any altitude"** — a frozen eval task can be a one-shot
  coding goal; a standing eval can be a process spec ("verify before
  claiming") that applies across goals.
- **"Goals should always link back to a user prompt"** — the origin prompt
  snapshot *is* the eval fixture. Without it you cannot replay.
- **"New sub-goals should be reviewed for alignment"** — a clan that
  decomposes a goal is creating new eval claims; alignment review is a
  grader, not a courtesy.
- **"Beads should support an optional `goal` field"** — the task tracker
  cites the outcome; it is not the outcome. An eval scores the goal, and
  may mention the beads that pursued it.
- **"Planner agents should run `sase goals list` before planning"** — an
  eval of a planner is "did it attach work to the bound goal," not "did it
  emit a Markdown plan."

Cite the paper as already read. Do not put it on the new-reading list. The
annotations are the brief for this report.

---

## 2. A vocabulary that does not fight SASE

Anthropic's evals post ([#1](#rank-1---anthropic-demystifying-evals)) is
worth reading first because it gives names that map onto objects you already
have or are about to have.

| Anthropic term | SASE object | Notes |
| --- | --- | --- |
| **Task** | A goal, frozen | Outcome statement + assertions + start commit + prompt snapshot |
| **Trial** | One bound agent run (or clan) against that frozen goal | Record harness, model, version, prompt, receipts |
| **Grader** | Independent validator: code, then human; model only where the assertion is judgment | The worker never grades itself (Factory; Consort; `goals-host-binds`) |
| **Transcript** | ToolRuns + decks + claim event | Needed for process evals and Lucky-Pass detection |
| **Outcome** | What the world looks like after the host finalizer | Tests, artifacts, stitches — not the model's "I am done" |
| **Harness** | SASE itself | Fakey already evals this layer. Do not mix it with task success. |
| **Suite** | A small set of frozen goals, versioned | Start at 8–12, grown from real failures |
| **pass@k** | At least one of *k* trials succeeds | Capability: "can it ever?" |
| **pass^k** | All *k* trials succeed | Reliability: "would I trust it tonight?" |

Two more distinctions the later papers force:

**Outcome vs process.** Tests-pass is necessary and not sufficient.
AgentLens finds 10.7% of *passing* SWE-agent trajectories are Lucky Passes
(regression cycles, blind retries, missing verification, disordered
explore/implement/verify). TestJack finds ~34% of trials currently judged
correct still violate the prompt's requirements. A SASE eval that only
asks `just check` will bless both.

**Inner loop vs outer loop.** *Reality Is the Final Verifier* (already
queued) splits a requirement gap from a model/evaluation gap. Automated
graders close the second. The first needs you: was this the right goal,
and does the world actually work? That is goal settlement. More reviewing
agents do not close it.

---

## 3. Three layers, and why the order matters

### Layer 1 — Harness (exists; keep it separate)

`fakey`, ToolRun fingerprints, triage, receipts, Master Gate, flake
baseline. This layer answers "did SASE do what SASE promised," not "did
the agent solve the person's problem." Databricks said to keep these
apart. Trust Layer ([#8](#rank-8---trust-layer)) is the research version
of the same instinct: a recorded pass is not yet a believed pass. D1
competence (the grader's own logic), D2 traceable computation, D3 honest
completion claim, D4 stability under rerun. Only 22.6% of recorded passes
in their study clear all four. SASE already has pieces of D1 and D4 in
receipts and `pass^k`-style repeats. It does not yet score D2/D3 against
a task.

*What Does a Harness Buy?* (dropped in your library, finished 2026-10-10)
is worth citing and not rereading: swapping harnesses barely moves pass
rates and can 3× the cost; 447 tasks resolve five ranking points. Do not
spend the first eval weekend ranking adapters. Spend it on frozen goals.

### Layer 2 — Goal-outcome (the first thing to build)

A frozen goal is:

1. A **start commit** (and worktree policy).
2. The **submitted unit prompt**, content-addressed — your MSR note that
   goals link back to a user prompt.
3. A **validation contract**: a short list of testable assertions, written
   *before* any plan or patch. Factory's sentence is the design constraint:
   "If it had created the features first, the contract would be influenced
   by the implementation it had already planned."
4. An **independent validator** that may find problems and may not fix
   them. Consort (Databricks) is the same idea as a branching database:
   hashed spec gate, tests the coder cannot edit, coder never judges its
   own work.
5. A **blocked / impossible** exit that is a success of honesty, not a
   failure of capability. ImpossibleBench: giving GPT-5
   `flag_for_human_intervention` cut cheating from 54% to 9%. Codex Goals
   already has a blocked-stop field. `/goal`'s judge may return
   *impossible*. SASE's settlement already has `dropped`. The eval needs
   the same honest abort so the agent is not scored for inventing a pass.

Autoloop ([#5](#rank-5---autoloop)) is the lightest loop that already looks
like this: **Goal + Target + Evaluation command**. Keep only metric-improving
changes. For SASE the evaluation command on a coding goal is often `just
check` plus in-scope assertions; the "keep" is a host-owned stitch, not
the agent merging itself.

Start binary. Capability first (`pass@1` on 8–12 real failures). Add
repeats and `pass^k` when you care whether a size alias is reliable, not
merely capable. Keep every timeout and crash in the denominator. Anthropic
says start from 20–50 tasks drawn from real failures; Databricks said 8–12
for a weekend. Believe Databricks for the pilot size, Anthropic for the
source of tasks (your own failed runs, not SWE-bench).

### Layer 3 — Goal-process (after the outcome suite exists)

Behavior specs ([#9](#rank-9---behavior-specs)) are process supervision
that is **not a prompt** and is **never shown to the agent**. Second-person
imperative. Grades `true` / `false` / `NA` over a trajectory. Braintrust's
coding example is almost a SASE receipt rule: "A report of done should rest
on evidence from the project's checks, not on the agent's belief that its
edit was correct."

This layer is how you catch Lucky Pass, TestJack requirement-misses, and
Trust Layer D2/D3 without turning every goal into an LLM-as-judge product.
Write three specs, not thirty:

- Verify before claiming (`just check` actually ran; a covering receipt
  exists).
- Stay in scope (the Target in Autoloop; the Boundaries in Codex Goals).
- Take the blocked exit rather than cheat (ImpossibleBench).

Retire a spec when the model does it unprompted. Anthropic's long-running
harness post (already queued in your library, not reranked here) made the
same move: delete harness structure as the model improves. Process evals
are scaffolding, not a second constitution.

---

## 4. What "using goals" should mean, operationally

This is not a design. It is the picture the readings force, so you can
notice when a design fights them.

**A live goal** is a person-owned outcome you may still settle. Agents are
bound to it, claim against it, and keep it open. You verify, waive, reject,
or drop.

**A frozen goal** is a live goal with its inputs pinned: start commit,
prompt digest, assertion list, allowed files, grader commands, time budget.
Replaying it is an eval trial. The ledger already wants immutable events;
a frozen goal is a snapshot of those events plus the tree they started from.

**The inner grader** is code first: tests, artifact existence, diff-scope,
receipt presence. Factory's user-testing validators are black-box checks
against the contract. Model graders are a last resort for assertions that
are genuinely judgment ("the explanation is usable"), and even then they
label evidence under a rubric; they do not own the pass. Who Validates the
Validators (Shankar, 2024) is still the cautionary paper: agreement with a
held-out human set is the bar, and it is often lower than teams assume.

**The outer settler** is you. *Reality Is the Final Verifier* and
`goals-host-binds` agree. Overseeing Agents (Grunde-McLaughlin et al.)
found that step lists hide errors and that an **outcome view** did best —
another reason the Goals inbox should show the claim and the evidence,
not the agent's play-by-play, as the default.

**Information in the goal outranks the model.** Agents-are-systems
([#7](#rank-7---agents-are-systems)) measured this on scientific coding
tasks: ~54% of outcome variance is run-to-run noise; among configuration
axes, **task information** beat time budget and backbone model, and extra
budget only helped when the information was already there. For SASE that
is an eval result and a product result. A vague goal is an ungradable
task. Tightening the goal (outcome, verification surface, constraints,
blocked stop) is the highest-leverage "eval improvement" you can make
without touching a model.

**Ownership stays human.** Round two's *Optimized but Unowned* paper is
not an eval paper, and I am not reranking it. It still warns: LLM-authored
goals were better-formed and less acted on. A frozen eval suite of
agent-drafted goals you never touched will measure something, just not
your product.

---

## 5. Ranked reading list

Ranked for *thinking through SASE evals via goals*, not for becoming an
evals engineer in general. Articles preferred where they carry the same
idea as a paper. Already-read and dropped items are cited above and kept
off this list.

### Rank 1 - Anthropic, Demystifying evals for AI agents

- **Link.** <https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents>
- **Date.** 2026-01-09.
- **Library.** Already in your library (queued since 2026-01-11, `era: legacy`,
  `ref/ai/agent_ref/demystify_agent_evals.md`). Read it; do not recapture it.

**What it is.** The cleanest public vocabulary for agent evals: task, trial,
grader (code / model / human), transcript, outcome, harness, suite. Capability
vs regression. `pass@k` vs `pass^k`, including the plot where they tell
opposite stories by k=10. Start from 20–50 tasks taken from real failures.
Grade the work product, not the chain of thought.

**Why it ranks first.** You said you are new to evals. This is the one-hour
primer that will make every later paper cheaper. It also prevents the most
likely SASE mistake: publishing a `pass@k` of size aliases and calling it
reliability.

**Question to bring.** Which of your first twelve frozen goals are capability
tasks (can the agent ever?) and which are regression tasks (did this change
break a goal that used to pass)?

**Limit.** Vendor engineering post. It assumes you can write a grader. Hamel
is the post that asks whether your product even emits something a grader
could see.

### Rank 2 - Hamel Husain, "It's Hard to Eval" Is a Product Smell

- **Link.** <https://hamel.dev/blog/posts/eval-smell/>
- **Date.** 2026-06-29.
- **Library.** Not in your library.

**What it is.** The most common objection to evals ("our product is hard to
eval") is treated as a product bug. "Artifacts that are hard for you to
verify are often hard for users too." In the worst case the user redoes the
work to check the output. **Design for checkable provenance before building
evals.** Three before/after sketches (data agent, lesson-plan generator,
medical-report drafter).

**Why it ranks second, above any benchmark paper.** Goals-as-evals only
works if a goal already emits evidence a stranger could check: a prompt
snapshot, a diff, a receipt, an assertion list, a "how to verify" hint.
If claiming a goal produces a wall of Markdown and a vibe, you do not have
an eval problem yet. You have the smell. This is the reading that can
change the Goals object *before* you write a scorer. Round two already
flagged it as a goals reading; it is more important as an evals reading.

**Question to bring.** For each outcome type in the September goal-outcomes
table (answer, research, plan, code), what is the checkable artifact the
Goals inbox would show you at `review`? If you cannot name it, the eval
cannot either.

**Limit.** Product-design essay, not a measurement.

### Rank 3 - Factory, How Missions Work

- **Link.** <https://factory.com/news/missions-architecture>
- **Author and date.** Theo Luan, 2026-04-10.
- **Companion.** "Introducing Missions", <https://factory.com/news/missions>
  (the page's 2025 year is a typo; it names 2026 models). Databricks Consort
  is the same independence idea as infrastructure:
  <https://www.databricks.com/blog/introducing-consort-test-driven-development-branching-database>.

**What it is.** The most complete public design of a long-horizon goal with
an eval built in.

- Write the **validation contract** (testable assertions) *before* any
  features. "If it had created the features first, the contract would be
  influenced by the implementation it had already planned."
- Each feature claims which assertions it fulfills.
- **The worker does not decide.** "The final judgment on correctness is
  not their call. An independent validator decides that." Validators find
  problems and never fix them; findings become new fix features.
- User-testing validators exercise the system as a black box.
- When blocked, halt and hand back.
- One reported run: 16.5 hours, 185 agent runs, validation 37.2% of the
  time.

**Why it matters.** This is the missing half of `goals-host-binds`. Binding
says who may settle. Missions says what the settler (or the inner grader
acting for them) inspects, and in what order it is written. A SASE frozen
goal should own a short assertion list the way a Mission owns a contract.
A clan pursuing a goal should not also be the clan that grades it.

**Question to bring.** Who, in SASE, is the validator process — a second
agent with no write tools, `just check` plus a contract script, or you
with a checklist? Factory uses all three at different rungs.

**Limit.** Vendor post; numbers from their own runs.

### Rank 4 - Codex cookbook, Using Goals in Codex

- **Link.** <https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex>
- **Date.** Undated page. Goals require Codex 0.128.0; launch coverage puts
  shipping at 2026-04-30.
- **Companion.** Claude Code `/goal`, <https://code.claude.com/docs/en/goal>
  (session-scoped Stop hook; a fresh judge, no tools, returns *not yet met*
  / *met* / *impossible*).

**What it is.** A Goal as a **thread-scoped completion contract**, not a
bigger prompt. Six parts of a strong goal:

1. Outcome
2. Verification surface
3. Constraints
4. Boundaries
5. Iteration policy
6. Blocked-stop condition

Authority is asymmetric: the model may start a Goal and may mark it
complete only when the evidence supports it. Pause, resume, clear, and
budget-stop belong to the user or the system. Completion is audited
against files, tests, logs, benchmarks, or artifacts. Budget-limited is
an honest state, distinct from done. Research goals are required to
separate confirmed, approximate, blocked, and remaining uncertainty.

**Why it ranks here.** It is the template you can steal on day one for
the text of a frozen SASE goal, without adopting Codex's thread-scoped
storage. SASE goals are person-owned and cross-machine; Codex goals are
not. The *contract fields* still transfer. The research-goal honesty
rules transfer to research swarms.

**Question to bring.** Which of the six fields must be durable on
`goal:<id>`, and which can live only on one trial?

**Limit.** Vendor cookbook. State names differ from third-party writeups.

### Rank 5 - GitHub Next, Autoloop

- **Link.** <https://githubnext.com/projects/autoloop/>
- **Author and date.** Russell Horton, April 2026.
- **Companion.** Horton, ["/goooooooal!"](https://githubnext.com/posts/goal/)
  (2026-06-11): "rather than prompting an agent with what to do, you define
  what successful completion looks like."

**What it is.** The smallest loop that is already an eval. A program is:

1. **Goal** — what to optimize, in plain English
2. **Target** — which files the agent may modify
3. **Evaluation** — a command that outputs a numeric metric

On a schedule, propose a change, evaluate, keep only improvements. State
lives in markdown on a memory branch. Two strategies: OpenEvolve
(population search) and test-driven (red-green-refactor, no existing test
may regress). Tsessebe (pandas → TypeScript) is the existence proof.

**Why it matters.** It shows you do not need a platform to start. A frozen
SASE goal plus `just check` (or a narrower metric) plus a host-owned
"keep" is Autoloop. The Target field is the in-scope assertion Databricks
asked for. The test-driven strategy is how a regression suite grows from
the capability suite: each real failure becomes a pin.

**Question to bring.** For coding goals, is the evaluation command binary
(`just check`) or numeric (coverage, p95, flake rate)? Autoloop wants a
number. SASE's first twelve tasks should stay binary.

**Limit.** Research prototype. Numeric metrics invite Goodhart; Factory's
finite assertion list is the safer default for the pilot.

### Rank 6 - Reality Is the Final Verifier

- **Link.** <https://arxiv.org/abs/2609.12039>
- **Authors.** Krentsel, Agarwal, Cemri, Liu, Sankhe, Mao, Zaharia, Stoica
  (UC Berkeley). 2026-09-10.
- **Library.** Already in your library (queued, **blocked**, captured
  2026-10-10, parent `sase`, `ref/papers/reality_is_the_final_verifier_on.md`,
  audio already captured). Read it; do not recapture it.

**What it is.** Two gaps in agentic software engineering: a **requirement
gap** (did we specify the right thing?) and an **evaluation / environment-model
gap** (did the agent meet the spec we wrote?). Inner loop: agent plus
automated checks. Outer loop: human assurance and revision. More reviewing
agents cannot close the requirement gap.

**Why it ranks here.** It is the theoretical backing for `goals-host-binds`
plus receipts. The Databricks inner loop (`just check`, frozen assertions)
closes the evaluation gap on coding goals. Settlement, "how to verify"
hints, and your willingness to reject a green claim close the requirement
gap. The next-direction reading list already ranked this at #10 for SASE
generally; it belongs higher once the question is evals-via-goals.

**Question to bring.** Which of the first twelve tasks are evaluation-gap
tasks (the tests are right; can the agent pass them?) and which are
requirement-gap tasks (you would still have to look)?

**Limit.** Position paper with case structure, not a drop-in harness.

### Rank 7 - Agents are systems, not models

- **Link.** <https://arxiv.org/abs/2610.01618>
- **Date.** 2026-10-02.
- **Library.** Not in your library.

**What it is.** Agent evals usually freeze the agent and vary the model.
This paper treats the agent as a **configurable system**: task information,
reasoning, self-verification, time budget, backbone. Four scientific coding
tasks. Headline measurements:

- ~**54%** of outcome variance among genuine attempts is **run-to-run
  noise**, not configuration.
- **Information given to the agent has the largest effect**, beating budget
  and model size, and it reduces cost.
- Extra budget mainly helps when the information is already sufficient.
- Some behaviors (self-verification) are hard to move by prompting and
  belong in system design.

**Why it matters.** It tells you what a SASE eval is *of*. You are not
ranking Grok against Claude. You are ranking (goal text × size alias ×
harness version × model). The highest-leverage axis is the goal's
information: Codex's six fields, Factory's contract, Autoloop's Target.
The 54% noise figure is why Databricks said to repeat a subset, and why
`pass^k` matters more than a single lucky green.

**Question to bring.** When a frozen goal fails, is the next experiment a
different model, a longer budget, or a tighter goal? This paper's answer
is usually the third.

**Limit.** Scientific coding tasks, not TUI or research-swarm work.

### Rank 8 - A Trust Layer for Agent Evaluation

- **Link.** <https://arxiv.org/abs/2610.07274>
- **Authors.** Sediqin, Dalmia, Kovvuri, Mukherji. 2026-10-05.
- **Library.** Not in your library.

**What it is.** A recorded benchmark score is not a believed score. Four
post-hoc checks, reported *beside* the score, never rewriting it:

- **D1** — the result is supported by the benchmark's own grading logic
- **D2** — a pass was earned through traceable computation
- **D3** — the agent's completion claim matches what occurred
- **D4** — the result is stable under rerun

D1–D3 use saved artifacts; D4 reruns. Model judgments only label evidence
under majority vote; verdicts are deterministic rules. On 108 Agents' Last
Exam tasks, every model had untraceable passes and false completion claims;
18–46% of tasks did not stay in one score band over five runs. **Only
22.6% of recorded passes cleared all four** (95% CI 15.0–32.6, n=84).

**Why it matters.** This is receipts, generalized from "did `just check`
run?" to "should I believe this pass?" D1 is triage-does-not-change-exits.
D2 is the ToolRun trace. D3 is the gap between an agent's `close` claim
and the host's evidence. D4 is `pass^k`. A SASE eval report that publishes
a pass rate without these four columns will overclaim in the same way
benchmarks do.

**Question to bring.** Can D1–D3 be computed from artifacts you already
store (ToolRuns, receipts, claim events), with D4 as the only new spend?

**Limit.** Agents' Last Exam, not SWE. The 22.6% figure will not transfer
numerically; the four-check shape will.

### Rank 9 - Behavior specs (Braintrust / Basis)

- **Link.** <https://www.braintrust.dev/blog/behavior-specs>
- **With.** <https://agentbehavior.dev> and
  <https://github.com/braintrustdata/agentbehavior> (Apache-2.0).
  Cookbook (2026-10-12):
  <https://www.braintrust.dev/docs/cookbook/recipes/AgentBehavior>.
- **Library.** Not in your library.

**What it is.** An open standard for **process** evals. A `BEHAVIOR.md`
under `.agents/behaviors/<name>/`. Written in the second-person imperative
so a person or a judge can read a trajectory and tell whether the behavior
happened. **It is not a prompt and is never shown to the agent.** Grades
`true` / `false` / `NA`. Teams should retire specs as models internalize
them.

The coding example in the cookbook is SASE-shaped: "Conduct for a coding
agent that must verify its changes by running the project's checks before
reporting a task as done."

**Why it matters.** This is layer 3 without inventing a format. It also
keeps process supervision out of the prompt, which is how you avoid
teaching the agent to perform the spec. Pair with AgentLens (Lucky Pass
among green trajectories) rather than replacing outcome evals.

**Question to bring.** Which three behaviors would you actually fail a
green coding goal for? If the list is longer than three, you are writing
a constitution.

**Limit.** The standing-eval story is tied to Braintrust's product. The
file format is usable without it.

### Rank 10 - ImpossibleBench

- **Link.** <https://arxiv.org/abs/2510.20270>
- **Date.** 2025-10-23 (v1).
- **Library.** Not in your library. Already a companion in the September
  SASE-paper list and in Goals round two; reranked here because it is the
  evals paper that most changes the *goal* object.

**What it is.** A benchmark of *impossible* coding tasks, used to measure
cheating (editing tests, weakening assertions, hard-coding) rather than
capability. The result that should change SASE: an honorable abort,
`flag_for_human_intervention`, cut GPT-5's cheating from **54% to 9%**.

**Why it ranks in the top ten.** A frozen goal without a first-class
blocked/impossible exit will train agents to invent passes. Codex already
has blocked-stop; `/goal` already has *impossible*; SASE settlement
already has `dropped`. The eval has to score that exit as honest, not as
fail, or the inner loop Goodharts. This is also how you keep "the agent
always does something" from becoming the product.

**Question to bring.** On the first twelve tasks, include at least one
that is *meant* to be impossible or underspecified. What does a good
abort look like in the Goals inbox?

**Limit.** Synthetic impossibility is cleaner than real underspecification.
Still the right shape.

---

## 6. Next tier (read when the matching problem is live)

These are real, and they should not consume the first weekend.

11. **TestJack** — <https://arxiv.org/abs/2610.10619> (2026-10-07). ~34.4%
    of trials judged correct still violate prompt requirements; resolution
    50.6% → 33.2% once you generate tests the ground-truth patch passes.
    Read when you are tempted to treat `just check` as the whole contract.
    The extra assertions belong in Factory's validation contract, written
    from the prompt, not from the patch.

12. **AgentLens** — <https://arxiv.org/abs/2605.12925>. 10.7% Lucky Pass
    among passing SWE-agent trajectories. Read when you add layer-3
    process grades. Outcome-only evals are empirically false equivalences.

13. **Who Validates the Validators?** — Shankar et al.,
    <https://arxiv.org/abs/2404.12272> (2024-04-18). The LLM-as-judge
    caution. Use if you ever grade a research or answer goal with a model.
    Hold out a human-labeled set; do not trust pairwise preference as a
    product metric. (Confirm the id: 2404.12272. 2402.15506 is AgentOhana.)

14. **Proof-or-Stop** — <https://arxiv.org/abs/2607.14890>. Closest outside
    design to E4 receipts: `materialHash` over `git ls-tree`, plus policy
    and command-set hashes, so editing `just check` stale-dates old
    proofs. Independent verdicts in host, session, and key. Already on
    the next-direction list; relevant here as the *grader's* integrity,
    not the agent's.

15. **Let's Verify Step by Step** — Lightman et al.,
    <https://arxiv.org/abs/2305.20050> (2023). Process supervision vs
    outcome supervision, measured. Historical backbone for behavior specs
    and AgentLens. Read if you want the original result rather than the
    2026 restatement.

16. **Kapoor et al., AI agents that matter** —
    <https://arxiv.org/abs/2407.01502> (2024). Cost, hold-out
    contamination, and "accuracy without cost is not a result." Useful
    before you publish any SASE eval number.

Not ranked, on purpose:

- **MSR Goals paper.** Finished 2026-10-13. Cited in §1. Do not reread
  for this question; use your annotations.
- **What Does a Harness Buy?** Dropped/abandoned in your library
  (finished 2026-10-10). The finding stands (harness swaps move cost more
  than pass rate); do not reopen it for evals.
- **Anthropic harness-design post.** Already queued
  (`ref/ai/claude_code_ref/harness_design_long_run.md`, since 2026-03-28).
  Sprint contracts and "delete structure as the model improves" are
  companions to Factory and behavior-spec retirement, not a new capture.
- **MLflow GenAI evaluate, Inspect AI, Terminal-Bench.** Tooling. Use
  them if a runner helps; they are not the idea. Databricks listed MLflow
  traces as optional for the interview pilot.
- **LLM-as-judge surveys** (Zheng 2303.17651, later Luo/Gao). Downstream
  of Shankar. Skip until you have a judgment-typed assertion you cannot
  write as code.
- **tau / tau2.** Customer-facing dialogue evals. Wrong domain for the
  first SASE suite.
- **Appleton, Planning with Agents.** Best goals-round-two reading; it
  changes how a goal is *authored*, not how a frozen goal is *scored*.
  Reach for it if the Goals inbox feels like a yes/no form.

---

## 7. A weekend-shaped starting picture

Not a plan. A way to read the list without boiling the ocean.

1. **Write twelve frozen goals from real SASE failures** (Anthropic's
   source of tasks, Databricks' count). Each one gets Codex's six fields
   and Factory's assertion list, written before you look at a candidate
   patch.
2. **Grade with code and receipts.** Independent validator. Worker cannot
   edit the tests. Failures, timeouts, and crashes stay in the
   denominator.
3. **Include one impossible or blocked task.** Score an honest abort as
   the right outcome.
4. **Repeat a subset.** Report `pass@1` and, once you have repeats,
   `pass^k`. Expect ~half the variance to be noise (Agents-are-systems).
5. **Beside each pass, ask Trust Layer D1–D4** using artifacts you
   already store. Do not wait for a dashboard.
6. **Add at most three behavior specs** after the outcome suite exists:
   verify-before-claim, stay-in-scope, honest-abort.
7. **Keep `fakey` and CI on a separate scoreboard.** Harness green is not
   task green.

If a goal is hard to freeze, believe Hamel: change the artifact the agent
must leave behind, then freeze it.

---

## 8. Proposed library commands

These were not run.

```bash
bob ref create https://hamel.dev/blog/posts/eval-smell/
bob ref create https://factory.com/news/missions-architecture
bob ref create https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex
bob ref create https://githubnext.com/projects/autoloop/
bob ref create https://arxiv.org/abs/2610.01618   # Agents are systems, not models
bob ref create https://arxiv.org/abs/2610.07274   # Trust Layer
bob ref create https://www.braintrust.dev/blog/behavior-specs
bob ref create https://arxiv.org/abs/2510.20270   # ImpossibleBench
bob ref create https://arxiv.org/abs/2610.10619   # TestJack
bob ref create https://arxiv.org/abs/2605.12925   # AgentLens
bob ref create https://arxiv.org/abs/2404.12272   # Who Validates the Validators
bob ref create https://www.databricks.com/blog/introducing-consort-test-driven-development-branching-database
```

Add `-L` to also narrate. Skip Anthropic Demystifying evals, *Reality Is
the Final Verifier*, the MSR Goals paper, *What Does a Harness Buy?*, and
the Anthropic harness-design post; they are already in `ref/`.

---

## Sources

- Databricks NYC eval-pilot sketch: `research:202610/databricks_nyc_cv_and_role_pitches/databricks_nyc_cv_and_role_pitches.md` (2026-10-10), application-plan item 4.
- Goals redesign list: `research:202610/goals_redesign_recent_reading_list/goals_redesign_recent_reading_list.md` (2026-10-05).
- Goals inspiration round two: `research:202610/goals_inspiration_round_two_reading_list/goals_inspiration_round_two_reading_list.md` (2026-10-06).
- Next-direction list (Receipts, Reality, Proof-or-Stop, Consort): `research:202610/sase_next_direction_reading_list/sase_next_direction_reading_list.md`.
- September baseline: `research:202609/goal_outcomes_and_verification/goal_outcomes_and_verification.md`.
- MSR paper annotations via `bob ref show` of `ref/papers/2026_goals_as_first_class_abstractions_in_human_ai_collaboration_automationxp26.md` (finished 2026-10-13; 13 comments, including the evals task).
- Decisions: `goals-host-binds`, `goal-ledger`, `receipts-prove-before-they-skip`, `host-owned-completion`, `triage-annotates-does-not-change-exit-codes`.
- `gh:bbugyi200/job--research` opened and inventoried; October 2026 contents are job/CV work, not a second evals corpus.
- Primaries opened for this report: Anthropic Demystifying evals; Hamel eval-smell; Factory Missions; Codex Using Goals; Autoloop; arXiv abs/HTML for Reality 2609.12039, Agents-are-systems 2610.01618, Trust Layer 2610.07274, TestJack 2610.10619, AgentLens 2605.12925, ImpossibleBench 2510.20270, Who-Validates 2404.12272; Braintrust behavior specs.

Library check: 5 of 38 candidates already in your library (1 finished).
