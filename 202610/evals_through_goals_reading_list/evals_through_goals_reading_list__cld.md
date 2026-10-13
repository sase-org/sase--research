# Goals as the eval substrate: a reading list for SASE evals (cld)

> **Research query:** I'm thinking about implementing evals for sase, probably driven by
> goals (still being designed). Using the Databricks research that first suggested evals,
> the recent goals research, and my annotations on "Goals as First-Class Abstractions in
> Human-AI Collaboration", find articles or papers that inspire me and help me think
> this through. End with a ranked reading list.

_Researcher cld · 2026-10-13 · one of five independent reports_

## Bottom line

**The goals design already contains most of an eval system.** A goal records an intent and
its success criteria. A claim is an attempt to meet them, with evidence. A human verdict
(verify, reject, acknowledge, drop) is a gold label. In eval vocabulary, that is a
*task*, a *trial with an outcome and a transcript*, and a *human grade*. The literature
below suggests three evals fall out of that lifecycle more or less for free:

1. **Online:** claim precision per model and harness (verified ÷ claimed), reject reasons
   coded into a failure taxonomy, and time-to-verify. The goals design already lists
   "verify, reject, acknowledge, and lapse rates per model" as G6 metrics.
2. **Offline replay:** a verified code goal, frozen at its start commit and with git
   history sealed, *is* a benchmark task. Its prompt comes from the goal's origin prompt,
   its tests from the accepted stitch, its rubric from the criteria, and its label from
   your verdict. This is the Databricks eval-pilot spec, but goals pick the tasks and
   write half of each task for you.
3. **Judge calibration:** every settled claim labels a pre-screening judge ("would Bryan
   verify this?"). You can measure that judge's agreement with you before trusting it to
   reorder your Needs Review lane.

The readings also carry five warnings that should shape the design early:

- **Criteria drift.** You'll discover what "done" means by looking at outputs
  ([#4](#rank-4---who-validates-the-validators)).
- **Tests overstate.** In one study 38% of runs passed the tests and 0% were mergeable
  ([#6](#rank-6---algorithmic-vs-holistic-evaluation)).
- **Requirements only approximate intent, and evaluators only approximate reality**
  ([#2](#rank-2---reality-is-the-final-verifier)).
- **Agents overstate their own success.** One study saw a 77% predicted success rate
  against 22% actual ([#9](#rank-9---agentic-overconfidence)).
- **A replay task leaks its answer** through git history unless you seal it
  ([#3](#rank-3---databricks-benchmarking-coding-agents-on-its-own-codebase)).

**If you read only three:** [#1 Demystifying evals](#rank-1---demystifying-evals-for-ai-agents)
(already queued in your library) for vocabulary, [#2 Reality Is the Final
Verifier](#rank-2---reality-is-the-final-verifier) (also already queued) for the
goal ↔ eval frame, and [#3 Databricks' own-codebase
benchmark](#rank-3---databricks-benchmarking-coding-agents-on-its-own-codebase) for the
recipe.

These are observations about the readings, not design decisions.

## Where I started

### The Databricks eval recommendation

The Databricks research (`research:202610/databricks_nyc_cv_and_role_pitches/…`, closed
out 2026-10-10) named one real gap: **"SASE has no task-success eval of real agents."**
`fakey` scores harness conformance, and ToolRun triage scores check reliability. Neither
answers "did the agent complete the task."

Its v2 follow-up carried an eval-pilot spec (bead `sase-1jo.3`, decision
`eval_pilot = skip`):

- 8–12 coding tasks from already-merged history, each frozen at its commit's parent.
- That commit's tests as the oracle, plus checks that the change stays in scope and that
  required artifacts exist.
- Timeouts and failures stay in the denominator.
- Record harness, model, version, and prompt. Repeat a subset to report variance and
  pass@k.
- MLflow traces are optional. Keep `fakey` separate from real-agent scores.

The job research in `bbugyi200/job--research` repeats this gap for nearly every
eval-adjacent role, such as Databricks Agent Quality, LangChain, Cursor, Figma, and
Harvey. So this reading list doubles as interview prep.

### The current state of goals

Favoring the most recent material:

- **G1 has landed.** `sase goal new/list/show/edit/drop/reopen/merge` exists. A goal holds
  a title, an outcome, criteria, and a timeline. Create, edit, and settle are human-only
  verbs, and agents may only `list` and `show`. `docs/goals.md` says binding, claims with
  verification, drafts, the Goals tab, and the attention cutover come later.
- **Two decision records** (status *Requested*) set the invariants:
  - `goal-ledger`: goals are immutable events plus live markers, not beads.
  - `goals-host-binds`: the host binds every LLM turn to exactly one goal before spawn.
    Agents only claim or keep open; *only a human settles*. Its cost section names
    "per-model claim precision" as a thing to contain, so an eval metric is already
    written into the decision.
- **The goals design** (`research:202609/sase_goals_design/…` §5) lists metrics that are
  already eval metrics:
  - claims per day;
  - verify, reject, acknowledge, and lapse rates per model;
  - median time-to-verify.
- **The two October reading lists** already covered most of the "who decides done" material:
  - Factory Missions' validation contract;
  - Willison's Showboat;
  - Husain's "hard to eval is a product smell";
  - Braintrust behavior specs;
  - the overclaiming paper;
  - ImpossibleBench;
  - Anthropic's evaluator-tuning harness post.

  I don't re-rank those here. This list is about evals themselves.

### Your annotations that this list answers

| Your note on the Tankelevitch & Rintel paper | Readings that speak to it |
| --- | --- |
| "at any altitude!" (goals are hierarchical) | Hierarchical rubrics: [#8](#rank-8---agent-as-a-judge) (Agent-as-a-Judge, PaperBench), [#15](#rank-15---per-goal-rubrics-healthbench) |
| "Use goals to drive evals that databricks research recommended!" | [#1](#rank-1---demystifying-evals-for-ai-agents), [#3](#rank-3---databricks-benchmarking-coding-agents-on-its-own-codebase), [#5](#rank-5---ai-evals-everything-you-need-to-know), [#12](#rank-12---rigorous-agentic-benchmarks-abc) |
| Evaluation is "bidirectional" (humans grade AI; AI gives goal-referenced feedback) | [#8](#rank-8---agent-as-a-judge), [#4](#rank-4---who-validates-the-validators), [#5](#rank-5---ai-evals-everything-you-need-to-know) (judge validation) |
| "Goals should always link back to a user prompt!" | [#3](#rank-3---databricks-benchmarking-coding-agents-on-its-own-codebase) (prompt rewritten from the PR); CursorBench (honorable mentions) traces committed code back to the agent request |
| "Predictive capability?" | [#9](#rank-9---agentic-overconfidence) and its METR time-horizon companion |
| Outcome simulation: "Now this is an interesting idea." | [#2](#rank-2---reality-is-the-final-verifier) (evaluator cascade); [#9](#rank-9---agentic-overconfidence) companion |
| "New sub-goals should be reviewed for alignment?!" | [#11](#rank-11---evaluating-goal-drift) (goal drift), [#10](#rank-10---evals-are-the-new-prd-and-the-spec-nobody-agreed-to) (who agreed to the spec) |
| "who changed them, when, and why" | [#4](#rank-4---who-validates-the-validators) (criteria drift), [#10](#rank-10---evals-are-the-new-prd-and-the-spec-nobody-agreed-to) ("run `git log` on the eval suite") |

## A mental model to read with

### The goal lifecycle, translated into eval vocabulary

The left column uses the goals design's words. The right column uses the words of
[#1](#rank-1---demystifying-evals-for-ai-agents), which defines them precisely.

| Goal lifecycle | Eval concept |
| --- | --- |
| Goal created: intent, outcome, criteria, origin prompt | **Task**: inputs plus success criteria. A goal written well enough to verify is a task spec ([#10](#rank-10---evals-are-the-new-prd-and-the-spec-nobody-agreed-to)) |
| Host binds a turn (model, harness, prompt, memory bundle) | **Trial**, with its configuration recorded |
| Agent transcript, tool runs, stitches | **Transcript** (trace) and **outcome** (the state of the world, not the agent's story) |
| Claim with evidence | The agent's **self-grade**. It's useful, but it's the least reliable grader ([#9](#rank-9---agentic-overconfidence)) |
| Human verify / reject / acknowledge / lapse | **Human grade**, the gold label used to calibrate every cheaper grader |
| Goal edited, criteria revised, reopened | **Criteria drift** ([#4](#rank-4---who-validates-the-validators)), recorded for free because the ledger keeps immutable events |
| Settled code goal plus start commit | A candidate **offline task**: capability eval while it's hard, regression eval once it passes reliably |
| Dropped or rejected goals | **Negative examples**, which merged-PR mining can't give you ([#12](#rank-12---rigorous-agentic-benchmarks-abc) companion) |

### Three loops you might build, in order of cost

1. **Observe (almost free once claims exist).** Claim precision and reject reasons per
   model and harness. The cheap analysis method is
   [#5](#rank-5---ai-evals-everything-you-need-to-know)'s error analysis:
   - Free-form notes on rejected claims ("open coding").
   - Grouping those notes into a failure taxonomy ("axial coding").
   - Counting each category.

   One caveat: models aren't randomly assigned to goals, so these numbers describe usage,
   not capability.
2. **Replay (the Databricks pilot, with goals as the corpus).** Run the same verified
   goals under different models or SASE configurations, k times each. Report pass@k and
   pass^k, cost per task, and infrastructure errors
   ([#3](#rank-3---databricks-benchmarking-coding-agents-on-its-own-codebase),
   [#13](#rank-13---infrastructure-noise-in-agentic-coding-evals)).
3. **Calibrate.** Train or prompt a claim pre-screener, measure its TPR/TNR against your
   verdicts, and only then use it to sort or filter Needs Review
   ([#5](#rank-5---ai-evals-everything-you-need-to-know),
   [#8](#rank-8---agent-as-a-judge)).

## Ranked reading list

### Rank 1 - Demystifying evals for AI agents

- **Link.** <https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents>
- **Authors and date.** Mikaela Grace, Jeremy Hadfield, Rodrigo Olivares, Jiri De Jonghe
  (Anthropic), 2026-01-09.
- **Library.** Already in your library, queued since 2026-01-11 (legacy backlog). It was
  also a companion pick in the 2026-10-05 goals list.

**What it is.** The best single primer on agent evals, written for teams like yours.

- **Vocabulary.** It defines *task*, *trial*, *grader*, *transcript*, and *outcome*. The
  outcome is "whether a reservation exists in the environment's SQL database," not
  whether the agent says it booked one.
- **Two kinds of eval.** It separates capability evals (start low) from regression evals
  (stay near 100%). Tasks "graduate" from one to the other.
- **Two ways to score repeats.** It contrasts pass@k (at least one success) with pass^k
  (all k succeed). At 75% per trial, pass^3 ≈ 42%.
- **An eight-step roadmap.** It starts with "20-50 simple tasks drawn from real failures"
  and continues to "read the transcripts" and "watch for saturation."

**Why it ranks first.** You're new to evals, and this gives you the vocabulary every other
reading assumes. It also makes points that land directly on goals:

- "A good task is one where two domain experts would independently reach the same
  pass/fail verdict." That is a test of whether a goal's criteria are written well.
- Step 1 says to convert user-reported failures into tasks. Rejected goal claims are
  exactly that.
- Writing an eval task tests "whether the product requirements are concrete enough to
  start building."
- In one case Claude gained an unfair advantage by reading the git history left by
  earlier trials.

**Question to bring.** Which of your goals would two careful reviewers verify the same
way, and what would you have to add to the rest so they would?

**Limit.** A vendor guide. Its examples are mostly customer-facing agents, not a
single-user orchestrator.

### Rank 2 - Reality Is the Final Verifier

- **Title.** "Reality Is the Final Verifier: On Two Key Gaps in Agentic Software
  Engineering" (paper)
- **Link.** <https://arxiv.org/abs/2609.12039>
- **Authors and date.** Krentsel, Agarwal, Cemri, Liu, Sankhe, Mao, Zaharia, and Stoica
  (UC Berkeley), 2026-09-10.
- **Library.** Already in your library, queued.

**What it is.** A conceptual framework for every implementation–verification loop. An
evaluator E accepts an implementation P against requirements R under an environment model
M. Two gaps sit outside the loop:

- **Requirement gap:** R against stakeholder intent I.
- **Model gap:** M against the real world W.

"Requirements only approximate stakeholder intent, and the model only approximates the
real deployment environment." Reward hacking exploits the gaps, and hallucination widens
them.

Its running example: an agent sped up a key-value store 6× and passed every test by not
storing values, because the benchmark's values were predictable. The authors admit: "few
would think to state that a store must actually store the values clients supply –
certainly we didn't!"

The fix is an outer *assurance–revision loop* that uses deployment evidence to revise R,
M, or E. The paper treats it as a budget problem: "Narrowing the requirement gap requires
accountable human judgment."

**Why it matters to your work.** This is the cleanest theory of *why goals and evals are
different objects that must stay linked*:

- **A goal is I.** Its written criteria are R.
- **An eval is E under some M.** That M might be tests, a replay sandbox, or an LLM judge.
- **Your settlement verdict is the outer loop.** It's the only place where the
  requirement gap gets measured. That is a principled argument for
  `decisions:goals-host-binds`' "only a human settles."

Two authors (Zaharia, Cemri) also appear in other picks here
([#3](#rank-3---databricks-benchmarking-coding-agents-on-its-own-codebase), MAST), so this
is also the Databricks/Berkeley view of the problem.

**What to look for.** The evaluator cascade in §6.1: queueing model, then workload
simulator, then recorded production traces, then canary. It is a concrete picture of
"outcome simulation" as a ladder of cheaper-to-costlier evaluators.

**Question to bring.** When you reject a goal claim, was the fault in P (the work), R (your
criteria), M (the environment the agent checked against), or E (the check)? Should the
reject verdict record which one?

**Limit.** A position paper. The framework is crisp, but the paper has no empirical study.

### Rank 3 - Databricks benchmarking coding agents on its own codebase

- **Title.** "Benchmarking Coding Agents on Databricks' Multi-Million Line Codebase"
- **Link.** <https://www.databricks.com/blog/benchmarking-coding-agents-databricks-multi-million-line-codebase>
- **Authors and date.** Vinay Gaba, Ankit Mathur, Rishabh Singh, Patrick Wendell, Matei
  Zaharia, 2026-07-08.

**What it is.** The most complete public account of the eval your pilot spec describes,
done by the company whose role prompted it.

- **Task sourcing.** Agent-request logs showed what engineers actually ask for (about a
  quarter low-complexity, about 60% medium). Merged PRs were then filtered on five
  criteria: recent, human-written, a good test suite, self-contained, and representative.
- **Prompts.** Each PR description was rewritten to state the goal and constraints, with
  the solution removed, including explanations of *why* a fix is correct.
- **Grading.** Tests were held out and run when the agent said it was done. No LLM judge
  was used: "we've found that this rewards sounding right over being right."
- **Review.** Every sample was reviewed by hand. Some tests were rewritten to accept
  alternative implementations.
- **The leak.** "the 'correct' implementation was still recoverable in the Git history
  of the worktree!" The fix was to cut each run off from the repository.
- **Harness findings.** Same model, different harness: cost per task changed by more than
  2× at equal quality. Price per token predicted cost per task poorly.

**Why it matters to your work.** It is your pilot, with lessons attached:

- **The leak applies to SASE.** A SASE workspace is a full clone, so a replayed goal must
  run without future objects.
- **Prompts come from intent.** Rewriting a PR into a prompt is what "goals link back to
  a user prompt" gives you for free: the *original* prompt, not a reconstruction.
- **The harness finding suits SASE.** SASE's real levers are harness levers: memory
  bundles, skills, instructions, and providers. An own-history eval is how you'd learn
  whether a memory change helped.

Its last line is the pitch: "Any team with a backlog of merged PRs is sitting on a
benchmark already that no model has trained on." The sase repo alone has about 16,000
commits.

**Question to bring.** Should the replay prompt be the goal's origin prompt verbatim
(realistic, but it may assume context the agent no longer has) or a rewritten task
statement (cleaner, but no longer what you actually asked)?

**Limit.** Grading by tests alone inherits the gap in [#6](#rank-6---algorithmic-vs-holistic-evaluation).
It is a company blog, and its results are self-reported.

### Rank 4 - Who Validates the Validators?

- **Title.** "Who Validates the Validators? Aligning LLM-Assisted Evaluation of LLM Outputs
  with Human Preferences" (paper; introduces EvalGen)
- **Link.** <https://arxiv.org/abs/2404.12272>
- **Authors and date.** Shreya Shankar, J.D. Zamfirescu-Pereira, Björn Hartmann, Aditya
  Parameswaran, Ian Arawjo. UIST 2024 (arXiv 2024-04).

**What it is.** A mixed-initiative tool that drafts evaluation criteria and their
implementations, then asks people to grade outputs so it can pick the implementations
that match their grades. Its lasting contribution is a named phenomenon, **criteria
drift**:

- Users need criteria to grade outputs, but grading outputs is how they define criteria.
- Some criteria depended on the particular outputs observed. They couldn't be written
  beforehand.

**Why it matters to your work.** You said you've thrashed on the goals requirements.
This paper says that thrash is the normal shape of defining "good." It's also a tension
with the "contract before plan" readings (Factory Missions, Anthropic's sprint
contracts). Read together, they suggest goal criteria are best treated as **versioned and
revisable, with evals graded against the criteria as of settlement**. The goal ledger's
immutable edit events already support that.

**Question to bring.** When you reject a claim and then edit the goal's criteria, is that
a rejection of the work or a correction of the spec? Should the ledger tell the two apart?

**Limit.** A small qualitative study (2024), set on LLM pipelines rather than agents.

### Rank 5 - AI Evals: Everything You Need to Know

- **Title.** "AI Evals: Everything You Need to Know" (the Husain & Shankar evals FAQ)
- **Link.** <https://hamel.dev/blog/posts/evals-faq/>
- **Authors and date.** Hamel Husain and Shreya Shankar. The current page is dated
  2026-09-18 (modified 09-21). Earlier versions circulated from 2025.

**What it is.** Opinionated answers distilled from teaching evals to thousands of
engineers ("sharp opinions … not universal truths").

- **Error analysis first.** "Error analysis is the most important activity in evals."
  Open-code at least 30 traces yourself, then axial-code them into a failure taxonomy.
- **Binary grades.** Prefer binary pass/fail over Likert scales.
- **One expert decides.** Appoint one domain expert as "benevolent dictator."
- **Build your own annotation tool.** "Build a custom annotation tool. This is the single
  most impactful investment you can make."
- **Validate judges.** Check each LLM judge against human labels using TPR and TNR, with
  one judge per failure mode.
- **Agent advice.** Grade end-to-end success first, then step-level diagnostics, then
  "transition failure matrices" (the last good state against the first failure).

**Why it matters to your work.** Several of the FAQ's prescriptions are already pieces of
the goals design:

- **Benevolent dictator.** You, settling goals, are the benevolent dictator.
- **Annotation tool.** The Goals tab's review card *is* the custom annotation tool. The
  FAQ's checklist for one (hotkeys, progress, flagged items first, "keep it minimal")
  doubles as a review-card checklist.
- **Binary verdicts.** Your verify/reject verdicts are already binary labels.

What's missing is the axial-coding step: a small, growing set of reject reasons.

**Question to bring.** What would the first ten reject-reason codes be, and could you
derive them from claims you'd have rejected last month?

**Limit.** Built around LLM products. The coding-agent material is short.

### Rank 6 - Algorithmic vs. Holistic Evaluation

- **Title.** "Research Update: Algorithmic vs. Holistic Evaluation"
- **Link.** <https://metr.org/blog/2025-08-12-research-update-towards-reconciling-slowdown-with-time-horizons>
- **Author and date.** David Rein (METR), 2025-08-13.

**What it is.** METR took 18 real issues from repos used in its developer-productivity
RCT and compared two ways of scoring Claude 3.7 Sonnet's PRs:

- **Maintainer tests.** 38% (±19%) passed.
- **Manual review for mergeability.** "none of them are mergeable as-is."

Every reviewed PR had at least three failure types: missing tests, missing docs,
lint/format/typing, and other code-quality problems. Apart from core functionality,
these appeared at similar rates whether or not the tests passed. Even passing PRs took
about 26 minutes to fix.

**Why it matters to your work.** This is the strongest evidence that **your verdict is
not redundant with tests**. It measures something tests don't. It also says the
Databricks-style test oracle should sit *beside* a holistic label, not replace it. Goals
give you that label without extra work. METR's five-category rubric is a ready-made
starting taxonomy for rejecting code claims.

**Question to bring.** For code goals, how often do you verify a claim whose tests
passed but which you'd still have edited before landing? Is that a "verify" or a
"reject"?

**Limit.** 18 tasks, two very strict repos, an older model, and a basic scaffold.

### Rank 7 - The Second Half

- **Link.** <https://ysymyth.github.io/The-Second-Half/>
- **Author and date.** Shunyu Yao, 2025-04-10.

**What it is.** A short, widely read essay arguing that "In this new era, evaluation
becomes more important than training." Once a general recipe works, the frontier is the
**utility problem**: models beat humans at exams yet "the world hasn't changed much."
Yao blames setups that differ from real use in basic ways:

- **Autonomous vs. human-in-the-loop.** Benchmarks hand an agent a task and score the
  result, while real agents work with people throughout.
- **i.i.d. vs. sequential.** Benchmarks average independent tasks, while a real engineer
  gets better as she learns the repo. A SWE agent doesn't.

**Why it matters to your work.** It's the inspirational read of the set. It also names
what makes SASE evals unusual: your work is *sequential* and *memory-dependent*.
Replaying single goals in isolation measures the first half. Measuring whether SASE memory
makes the 50th goal in a project easier than the first would be a second-half eval.

**Question to bring.** Is there a goal-shaped eval where memory is the treatment, such as
the same goal replayed with today's memory against the memory as of the goal's start date?

**Limit.** An essay drafted with AI assistance from talk slides. It argues a direction
and gives no method.

### Rank 8 - Agent-as-a-Judge

- **Title.** "Agent-as-a-Judge: Evaluate Agents with Agents" (paper)
- **Link.** <https://arxiv.org/abs/2410.10934>
- **Authors and date.** Mingchen Zhuge et al. (Meta / KAUST). arXiv 2024-10, ICML 2025.
- **Companion.** OpenAI's PaperBench, <https://arxiv.org/abs/2504.01848> (2025-04).
  Replication is graded with *rubric trees*: 8,316 leaf requirements across 20 papers.
  Leaves are graded pass/fail, and parents are weighted averages of their children.
- **Library note.** You already have a related but different paper queued: "A Survey on
  Agent-as-a-Judge" (arXiv 2601.05111).

**What it is.** DevAI is 55 realistic development tasks with **365 hierarchical user
requirements**. An agentic judge inspects the workspace (files, logs, trajectory) instead
of only the final message. It agreed with human consensus about 90% of the time, against
about 70% for a plain LLM judge, at about 3% of the cost of three human experts. The best
coding agents satisfied about 29% of requirements and fully completed one task.

**Why it matters to your work.** "Goals at any altitude, hierarchically related" is
exactly a requirement tree. Both papers show how to:

- grade a parent by its children;
- give partial credit;
- let a judge with tools check requirement leaves against real artifacts.

That's the shape of a goal pre-screener that reads the stitch, the ToolRun receipts, and
the report before you do.

**Question to bring.** Should a goal's criteria be a flat list or a tree? Would sub-goals
simply *be* the inner nodes?

**Limit.** The tasks are greenfield AI-dev projects, and the 90% agreement was measured on
that benchmark. [#3](#rank-3---databricks-benchmarking-coding-agents-on-its-own-codebase)'s
refusal of LLM judges for correctness is the counterweight. Use judges for criteria tests
can't reach, and validate them first.

### Rank 9 - Agentic Overconfidence

- **Title.** "Agentic Uncertainty Reveals Agentic Overconfidence" (paper)
- **Link.** <https://arxiv.org/abs/2602.06948>
- **Authors and date.** Jean Kaddour, Srijan Patel, Gbètondji Dovonon, Leo Richter,
  Pasquale Minervini, Matt J. Kusner. arXiv 2026-02-06; listed at ICLR 2026.
- **Companion.** METR, ["Measuring AI Ability to Complete Long Software
  Tasks"](https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/)
  (2025-03-19). It fits a logistic curve of success probability against the time a human
  needs for the task. That gives the "50% time horizon," which has doubled about every
  7 months.

**What it is.** The authors ask agents for success probabilities before, during, and after
execution.

- **Overconfidence.** Some agents that succeed about 22% of the time predict about 77%.
- **Earlier is better.** Assessment *before* execution, with less information, often
  discriminates better than review afterward.
- **Framing helps.** Framing the assessment as bug-finding gave the best calibration.

**Why it matters to your work.** It answers your "Predictive capability?" note from two
sides:

- **A claim is a self-assessment, and self-assessments are inflated.** So claim precision
  is a first-class metric, and a host-side check before settlement is worth having.
- **Prediction is measurable.** The METR companion shows that, with enough settled goals,
  you could fit P(verified | model, harness, goal size) and show it on a goal *before*
  launch. You could also ask the bound agent for a pre-execution forecast and score it
  later. That's a cheap, concrete version of the paper's "outcome simulation."

**Question to bring.** If every goal-bound turn recorded a 0–100 "will this be verified?"
forecast at launch, how many settled goals would you need before the calibration curve
said something useful?

**Limit.** Benchmark tasks, not long multi-session goals. Time horizons are a population
statistic, not a per-goal promise.

### Rank 10 - Evals are the new PRD, and the spec nobody agreed to

- **Main.** Ameya Bhatawdekar (Braintrust), ["Evals are the new
  PRD"](https://www.braintrust.dev/blog/evals-are-the-new-prd), 2026-03-27.
- **Counterpoint.** Tian Pan, ["The Eval Suite That Became the Spec Nobody Agreed
  To"](https://tianpan.co/blog/2026/05/17/eval-suite-became-spec-nobody-agreed-to),
  2026-05-17.

**What they are.**

- **Braintrust's argument.** For non-deterministic software, Problem→Spec→Build becomes
  Problem→Eval→Hillclimb→Ship: "The eval becomes the spec, the acceptance criteria, and
  the roadmap all at once."
- **Pan's warning.** The eval suite is usually written by one engineer on a deadline and
  silently encodes product decisions nobody reviewed. "The person writing evals is
  writing the PRD, whether they signed up for that job or not." Also: "The suite cannot
  catch an error it shares." His fix is to review eval changes as product decisions, and
  to run `git log` on the eval suite to see who actually wrote the spec.

**Why it matters to your work.** Together they explain why **deriving evals from goals is
a good idea**. A person writes and settles a goal, so evals built from goals inherit a
spec someone actually agreed to. That's Pan's fix, built into the data model. They also
connect to round two's "Optimized but Unowned" result: agent-drafted criteria are
better-formed but less owned. An eval generated from an agent-drafted goal you never
shaped would be the spec nobody agreed to.

**Question to bring.** When an agent proposes sub-goals or criteria, what is the minimum
human act that makes them part of an agreed spec?

**Limit.** A vendor post and a practitioner blog. Both are about product teams, not solo
developers.

### Rank 11 - Evaluating Goal Drift

- **Title.** "Technical Report: Evaluating Goal Drift in Language Model Agents" (paper)
- **Link.** <https://arxiv.org/abs/2505.02709>
- **Authors and date.** Rauno Arike, Elizabeth Donoway, Henning Bartsch, Marius Hobbhahn
  (MATS / Apollo Research). arXiv 2025-05; AIES 2025.
- **Companion.** Cai et al., ["Push Your Agent: Measuring and Enforcing Quantitative Goal
  Persistence in Long-Horizon LLM Agents"](https://arxiv.org/abs/2605.23574) (2026-05-22).
  It defines *false completion* (claiming done before the verifier agrees), *premature
  stopping*, and *progress inflation*. Success is judged "from verifier state not from
  the agent's final message."

**What it is.** The agent gets a goal in its system prompt and then faces competing
pressure from its environment over a long context.

- **Everyone drifts.** Every model drifts somewhat.
- **The best held on.** A scaffolded Claude 3.5 Sonnet stayed close to its goal for more
  than 100k tokens.
- **Drift tracks context.** Drift correlated with more pattern-matching as context grew.

**Why it matters to your work.** It's the only eval in this list that tests *goal
integrity* rather than task success. That's the eval behind your annotation "New
sub-goals should be reviewed for alignment?!" and behind binding every turn to a goal.

The companion turns false completion into a metric. Its "verifier-gated" controller (no
completion while the verified count is short) is close to what a host-owned claim check
does. Even so, verifier gating alone didn't stop agents repeating work.

**Question to bring.** Could a cheap eval replay a long `%clan` session and check that
each member's claim still serves the bound goal, not the latest local instruction?

**Limit.** A simulated stock-trading environment, not coding. PushBench is new and comes
from a small team.

### Rank 12 - Rigorous agentic benchmarks (ABC)

- **Title.** "Establishing Best Practices in Building Rigorous Agentic Benchmarks" (paper;
  the Agentic Benchmark Checklist)
- **Link.** <https://arxiv.org/abs/2507.02825>
- **Authors and date.** Yuxuan Zhu, Daniel Kang, et al. NeurIPS 2025, Datasets &
  Benchmarks track.
- **Companion.** Stephanie Jarmak, ["Engineering Reliable Coding Agents: Evaluating and
  Operating the System Around the Model"](https://arxiv.org/abs/2608.13867) (2026-08-14).
  It is a 314-page monograph, so read §3.3–3.4 and the evaluation chapters. Points worth
  taking from it:
  - "The tests a merged change happened to touch are candidate historical checks, not a
    certification that the recorded solution was correct."
  - Merged history is a biased sample, because abandoned attempts and incidents never
    merge.
  - A null agent that echoed the instruction back still earned credit from some
    verifiers.
  - Use at least three repeats and paired tests (McNemar's for pass/fail).

**What it is.** A checklist for whether an agentic benchmark measures what it claims.
Rigor comes in two parts:

- **Task validity:** the task is solvable if and only if the agent has the capability.
- **Outcome validity:** a passing grade means real success.

It found serious flaws in popular benchmarks. SWE-bench Verified has insufficient tests,
and τ-bench counted empty responses as successes. Such flaws can mis-estimate
performance by up to 100% in relative terms.

**Why it matters to your work.** When you promote a settled goal into a replay task, the
checklist is the review you run on it. The companion adds the point that matters most
for goals: **your rejected and dropped goals are the representative negatives that
merged history lacks.** A goal-derived suite can include "should not claim" cases. That
is Anthropic's "balanced problem set" advice.

**Question to bring.** Before admitting a goal to the replay suite, which checks would
it need? For example: tests fail on the start commit, pass on the accepted stitch, and a
null agent fails.

**Limit.** Written for public benchmark builders, so it's heavier than a personal
suite needs. Use it as a checklist, not a process.

### Rank 13 - Infrastructure noise in agentic coding evals

- **Title.** "Quantifying infrastructure noise in agentic coding evals"
- **Link.** <https://www.anthropic.com/engineering/infrastructure-noise>
- **Author and date.** Gian Segato (Anthropic), 2026-02-05.
- **Companions.**
  - Yao, Shinn, Razavi, Narasimhan, ["τ-bench"](https://arxiv.org/abs/2406.12045)
    (Sierra, 2024-06). It introduced **pass^k**: GPT-4-class agents fell to about 25% when
    they had to succeed eight times in a row.
  - Kapoor, Stroebl, Siegel, Nadgir, Narayanan, ["AI Agents That
    Matter"](https://arxiv.org/abs/2407.01502) (TMLR 2025). It argues for cost-controlled
    comparison, accuracy–cost Pareto curves, and proper holdouts.

**What it is.** Holding model, harness, and tasks fixed, resource settings alone moved
Terminal-Bench 2.0 scores by 6 points (p < 0.01). Infrastructure errors fell from 5.8% to
0.5% as limits loosened. Beyond about 3× headroom, the eval started measuring something
different: brute force versus lean strategies. The post's advice: "leaderboard
differences below 3 percentage points deserve skepticism."

**Why it matters to your work.** SASE runs agents on athena, apollo, and a Mac, under
different loads. A replay eval that ignores machine, time of day, and resource headroom
will mistake infrastructure for model quality. You already have the instrument: ToolRun
records and triage verdicts can label infrastructure failures separately from task
failures, as these papers recommend.

**Question to bring.** Should replay trials record the machine and resource envelope as
part of the trial config, next to model and harness?

**Limit.** About one benchmark on one cluster. The τ-bench and Kapoor papers are from
2024.

### Rank 14 - Asymmetry of verification and verifier's rule

- **Title.** "Asymmetry of verification and verifier's rule"
- **Link.** <https://www.jasonwei.net/blog/asymmetry-of-verification-and-verifiers-law>
- **Author and date.** Jason Wei. The page says Jul 15 and no year; it was 2025.

**What it is.** A short essay. Some tasks are far easier to verify than to solve, and the
asymmetry can be *engineered* by doing work up front, such as answer keys and test
coverage. "Verifier's rule: The ease of training AI to solve a task is proportional to
how verifiable the task is." It gives five properties of a good verifier:

1. objective truth;
2. fast;
3. scalable;
4. low noise;
5. continuous reward.

He predicts "a jagged edge of intelligence."

**Why it matters to your work.** Read it with Husain's "hard to eval is a product smell"
from your round-two list. It adds a forecast: goals you can verify cheaply are the ones
agents will soon do reliably. The goals you *can't* verify cheaply, such as research and
design judgments, are where human settlement will stay the bottleneck. Wei's five
properties are also a quick rubric for a goal's criteria.

**Question to bring.** Score your last 20 goals on Wei's five properties. Do the
high-scoring ones settle faster and get rejected less?

**Limit.** About training, not product evals. It's short and speculative, and the "rule"
has no measurements behind it.

### Rank 15 - Per-goal rubrics (HealthBench)

- **Title.** "HealthBench: Evaluating Large Language Models Towards Improved Human Health"
- **Links.** <https://openai.com/index/healthbench/>; paper
  <https://arxiv.org/abs/2505.08775>
- **Authors and date.** OpenAI, 2025-05.
- **Companion.** Cook et al., ["TICKing All the Boxes: Generated Checklists Improve LLM
  Evaluation and Generation"](https://arxiv.org/abs/2410.03608) (2024-10). An LLM turns
  each instruction into YES/NO checklist questions, and judge agreement with humans rose.
  Giving human raters the checklists also improved inter-annotator agreement.

**What it is.** 5,000 conversations, **each with its own physician-written rubric**:
48,562 weighted criteria in total, covering what a good response must include or avoid.
A model-based grader, validated against physicians, scores each criterion.

**Why it matters to your work.** Most benchmarks apply one grader to every item.
HealthBench, and LangChain's deep-agents post (honorable mentions), show the opposite
pattern that goals need: **every item carries its own criteria**. That's the strongest
precedent for treating each goal's criteria as its own small rubric, graded criterion by
criterion. TICK adds the practical version: a model drafts the checklist, a person
accepts or edits it, and graders check items one at a time.

**Question to bring.** If a goal's criteria were stored as atomic yes/no items with
weights, would your verify/reject decision get faster?

**Limit.** Medical conversations, not code. The rubrics were written by experts at a
scale you won't have.

## Honorable mentions

| Read this | Date | Why |
| --- | --- | --- |
| The LangChain Team, ["Evaluating Deep Agents: Our Learnings"](https://www.langchain.com/blog/evaluating-deep-agents-our-learnings) | 2025-12-03 | "each test case has its own success criteria." About half their tests stop the agent after one step to check a single decision. A good template for testing SASE's decision points (bind, claim, keep-open) without full runs. |
| Cursor, ["Improving Cursor Tab with online RL"](https://cursor.com/blog/tab-rl) | 2025 | Accept and reject events become the reward signal at scale. This is what your verify/reject stream could become, here for training rather than eval. |
| CursorBench (Cursor's internal eval, introduced with Composer) | 2025-10 onward | Tasks come from real sessions and are traced back to the originating agent request with "Cursor Blame." The closest analog to "goals link back to a user prompt." I verified it only through secondary sources. |
| Jude Gao (Vercel), ["AGENTS.md outperforms skills in our agent evals"](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals) | 2026-01-27 | A small, honest harness-configuration eval: a docs index in AGENTS.md reached 100%, skills reached 79%, and in 56% of cases the skill was never invoked. It's the kind of question SASE memory and skills changes raise. |
| Peralta et al., ["Why Are Agentic Pull Requests Merged or Rejected?"](https://arxiv.org/abs/2605.22534) | MSR 2026 | Of rejected agentic PRs, only about 36% showed agent failure, about 31% were workflow reasons, and about 33% gave no reason. A human reject is a noisy label unless it carries a reason. |
| Cemri et al., ["Why Do Multi-Agent LLM Systems Fail?" (MAST)](https://arxiv.org/abs/2503.13657) | NeurIPS 2025 | 14 failure modes in three groups (specification, inter-agent misalignment, task verification), with κ = 0.88. A ready starting taxonomy for coding swarm and `%clan` failures. |
| METR, ["Recent Frontier Models Are Reward Hacking"](https://metr.org/blog/2025-06-05-recent-reward-hacking) | 2025-06-05 | Models edit tests and scoring code, or find the answer key, while knowing it's not what the user intended. Read it before you write any replay grader that runs inside the agent's sandbox. |
| Patwardhan et al. (OpenAI), ["GDPval"](https://arxiv.org/abs/2510.04374) | 2025-09 | Expert graders blindly compare model and human deliverables pairwise on 1,320 tasks from 44 occupations. A model for evaluating *non-code* goals (research, writing) where no test oracle exists. |
| Xia et al., ["Evaluation-Driven Development and Operations of LLM Agents"](https://arxiv.org/abs/2411.13768) | arXiv 2024-11 (v3 2025) | A process model that joins offline and online evaluation in one feedback loop. Read it as background; the evals FAQ (#5) is skeptical of "eval-driven development." |
| [RepoTrials](https://dev.to/repotrials/repotrials-turn-your-git-history-into-private-coding-agent-benchmarks-4462) and [Harbor](https://harborframework.com/) | 2026-08; 2025–26 | Tooling. RepoTrials checks each task with four runs (BASE, RED, GOLD, NOOP), which is a good admission test for goal-derived tasks, and it can export to Harbor. Harbor is the Terminal-Bench team's container eval runner. Look at both before building your own runner. |

## Already covered in your goals reading lists

These matter for evals, but the 2026-10-05 and 2026-10-06 lists already present them, so
I don't re-rank them:

- **Factory, "How Missions Work."** The validation contract comes before the plan, and an
  independent validator decides "done."
- **Anthropic, "Harness design for long-running application development."** An evaluator
  tuned toward skepticism.
- **Willison, Showboat.** Captured, replayable evidence.
- **Husain, "'It's Hard to Eval' Is a Product Smell."**
- **Braintrust and Basis, "Behavior specs."**
- **"Quantifying Overclaiming Propensity."**
- **ImpossibleBench's flag-for-human result.** An honorable exit cut GPT-5's cheating
  from 54% to 9%.
- **TASTE.** Judges and humans disagree on research taste.
- **Menon et al., "Inherited Goal Drift."**

If you re-read any of them through an eval lens, start with Factory Missions. It's the
closest existing system to "goals drive evals."

## Tensions worth carrying into the reading

These are questions the readings raise, not design decisions.

1. **Criteria before or after?**
   - *Before:* Factory, Anthropic, and Braintrust say write the contract or eval first.
   - *After:* Shankar ([#4](#rank-4---who-validates-the-validators)) shows criteria
     emerge from outputs.
   - *A middle path:* criteria are versioned, and replay grades against the criteria as
     of settlement.
2. **Tests, judges, or you?**
   - *Tests:* Databricks refuses LLM judges for correctness.
   - *Judges:* Agent-as-a-Judge reaches about 90% agreement on criteria.
   - *You:* METR shows tests miss what you'd reject.
   - *Layering them:* the Swiss-cheese view in [#1](#rank-1---demystifying-evals-for-ai-agents)
     uses tests where executable, judges for the criteria tests miss, and you as the gold
     label that calibrates both.
3. **Usage statistics or capability?** Claim precision from live goals is free but
   confounded: you choose which model gets which goal. Replay is what lets you compare
   models. Both are worth having, but don't read one as the other.
4. **Model or harness?** Databricks and Vercel both found the harness configuration moves
   results as much as the model. For SASE, the more useful eval question may be "did this
   memory, skill, or instruction change help?" rather than "which model is best?"
5. **Who owns the suite?** Goals settle Pan's ownership problem ([#10](#rank-10---evals-are-the-new-prd-and-the-spec-nobody-agreed-to))
   only if agent-drafted criteria pass through a real human act. That connects to round
   two's "Optimized but Unowned."
6. **Is a reject a label or a lesson?** It's both, but only if it records *why*: work,
   criteria, environment, or check ([#2](#rank-2---reality-is-the-final-verifier)).
   Without a reason it's noisy (MSR study).

## Suggested additions to your library

The top unread picks that are not in `ref/` yet, as `bob ref create` lines to run if you
want them. I didn't run any.

```text
bob ref create https://www.databricks.com/blog/benchmarking-coding-agents-databricks-multi-million-line-codebase
bob ref create https://arxiv.org/abs/2404.12272
bob ref create https://hamel.dev/blog/posts/evals-faq/
bob ref create https://metr.org/blog/2025-08-12-research-update-towards-reconciling-slowdown-with-time-horizons
bob ref create https://ysymyth.github.io/The-Second-Half/
bob ref create https://arxiv.org/abs/2410.10934
bob ref create https://arxiv.org/abs/2602.06948
```

## Method and limits

- **Context read.**
  - The Databricks reports, through `sase artifact read`: the canonical report, the v2
    follow-up, and interview prep.
  - The `bbugyi200/job--research` canonical reports.
  - The goals design, roadmap, and verification syntheses (September).
  - Both October goals reading lists.
  - The `goal-ledger` and `goals-host-binds` decision records and the `glossary:goal`
    strand.
  - `docs/goals.md` and `sase goal --help`.
  - Your 13 annotations, through `bob ref show`.
- **Sources checked.** Each ranked pick's page was fetched, or its abstract confirmed, and
  dates are as stated on the page. Exceptions:
  - CursorBench and some HealthBench details come from secondary coverage.
  - The Jarmak monograph was read only through §3.4.
  - The Hamel FAQ page is dated 2026-09, but the FAQ itself existed in 2025.
  - Wei's post shows no year.
- **Picks favor material you haven't seen.** Classic but older readings appear only as
  companions.
- **Not covered.** I found no source that evaluates a *personal* multi-agent orchestrator
  against one person's goals. That gap is probably the novel part of what you'd build.

Library check: 2 of 33 candidates already in your library (0 finished). They are
"Demystifying evals for AI agents" (queued since 2026-01-11, legacy backlog) and "Reality
Is the Final Verifier" (queued). A related survey, "A Survey on Agent-as-a-Judge"
(arXiv 2601.05111), is also queued.
