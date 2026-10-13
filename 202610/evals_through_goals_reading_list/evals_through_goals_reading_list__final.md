# Evals through goals: a consolidated reading list for SASE

> **Research query:** I am thinking about implementing some form of evals for SASE,
> probably using goals (still being designed; favor recent goals research). See the
> Databricks research that first suggested evals, the private `bbugyi200/job--research`
> repo, and my annotations on *Goals as First-Class Abstractions in Human-AI
> Collaboration*. I'm new to evals. Find articles and papers that inspire me and help me
> think this through, and end with a ranked reading list.

_Lead synthesis · 2026-10-13 · merges five researcher reports
([cdx](evals_through_goals_reading_list__cdx.md),
[cld](evals_through_goals_reading_list__cld.md),
[grk](evals_through_goals_reading_list__grk.md),
[mus](evals_through_goals_reading_list__mus.md),
[gem](evals_through_goals_reading_list__gem.md)) with the lead's own source checks and
gap research._

## Bottom line

**A goal is not an eval, but it is the best source of evals you will have.** A goal
records what you want and why. An eval is a repeatable experiment that produces evidence
about whether some version of the system met a *frozen* version of that want. The
cleanest frame comes from *Reality Is the Final Verifier*
([#2](#2-reality-is-the-final-verifier)). Written criteria only approximate intent, and
any automated check only approximates reality. Your settlement verdict is the one place
where the gap between criteria and intent gets measured.

**The goal lifecycle already speaks eval vocabulary.** A goal is a task spec, a bound turn
is a trial, a claim is the agent grading itself, and your verify/reject verdict is the gold
label. Three evals follow from that, in order of cost:

1. **Observe.** Track claim precision and coded reject reasons per model and harness.
2. **Replay.** Re-run frozen, settled goals. This is the Databricks pilot, with goals as
   the corpus.
3. **Calibrate.** Measure a pre-screening judge against your verdicts before trusting it.

**Your thrashing on goal requirements is not a blocker. It is the normal shape of
defining "good."** Shankar et al. ([#3](#3-who-validates-the-validators)) named it
*criteria drift*: you discover criteria by grading outputs. Version the criteria and keep
evals traceable to the version they used. Don't wait for the criteria to be final.

**Six warnings from the readings should shape the design early:**

- **Criteria drift.** You will learn what "done" means by looking at outputs (#3).
- **Tests overstate.** In one study 38% of runs passed the tests, yet none of the 15
  hand-reviewed PRs was mergeable as-is ([#8](#8-algorithmic-vs-holistic-evaluation)).
- **Agents overclaim.** Some agents that succeed 22% of the time predict 77%
  ([#14](#14-agentic-uncertainty-reveals-agentic-overconfidence)).
- **Replays leak.** Answers leak through git history unless you seal it
  ([#4](#4-benchmarking-coding-agents-on-databricks-multi-million-line-codebase)).
- **Criteria become targets.** Once goal criteria become what agents are graded on,
  optimization bends them (Goodhart; [#12](#12-goodharts-law-and-specification-gaming)).
- **A recorded pass is not a believed pass.** In one audit only 22.6% of recorded passes
  survived four simple checks ([#10](#10-a-trust-layer-for-agent-evaluation)).

**New in this synthesis:** none of the five researchers found the 30-year-old precedent
for your annotation "use goals to drive evals". Basili's **Goal Question Metric**
approach ([#6](#6-the-goal-question-metric-approach)) argues that measurement only works
top-down from stated goals. The lead also found direct evidence on a question cld left
open: whether a replay should use your original prompt or a cleaned-up rewrite.
RealSWE ([#9](#9-agents-are-systems-not-models)) finds that realistic prompts change both
scores and rankings.

**If you read only three:** [#1 Demystifying evals](#1-demystifying-evals-for-ai-agents)
(already queued) for vocabulary, [#2 Reality Is the Final
Verifier](#2-reality-is-the-final-verifier) (already queued) for the goal-to-eval frame,
and [#3 Who Validates the Validators?](#3-who-validates-the-validators) for criteria
drift. Read [#4 Databricks](#4-benchmarking-coding-agents-on-databricks-multi-million-line-codebase)
next for the recipe.

These are observations about the readings, not design decisions.

## 1. Where things stand

### The eval gap the Databricks research named

The Databricks NYC research (2026-10-10) and its v2 follow-up named one real gap: **SASE
has no task-success eval of real agents.** SASE has strong harness-reliability signals:

- `fakey` conformance;
- ToolRun records with NEW/KNOWN/FLAKY/UNKNOWN triage;
- receipts;
- two-speed CI.

None of these answers "did the agent achieve what the person wanted?"

The v2 report carries an eval-pilot spec on bead `sase-1jo.3`. Its decision,
`eval_pilot = skip`, means *deferred*, not done. The spec:

- **Tasks.** 8–12 coding tasks from merged history, each frozen at its commit's parent.
- **Oracle.** That commit's tests, plus checks that the change stays in scope and that
  required artifacts exist.
- **Denominator.** Timeouts and failures stay in it.
- **Records.** Harness, model, version, and the exact prompt.
- **Repeats.** Repeat a subset and report variance and pass@k.
- **Tooling.** MLflow is optional. Keep `fakey` scores separate from real-agent scores.
- **Home.** Its future home is `tools/agent_eval_pilot/`.

cdx and cld report that the `bbugyi200/job--research` repo repeats this gap for nearly
every eval-adjacent role (Agent Quality, LangChain, Cursor, Harvey). This reading list
therefore doubles as interview preparation. grk found no separate evals corpus there.

### Goals as of today (checked against the repo)

Your prompt says goals "do not exist yet." That is true of the parts evals need most,
but not of the whole feature:

- **Landed (G1, 2026-09-28).**
  - The `sase goal new/list/show/edit/drop/reopen/merge/doctor` CLI.
  - A Rust-owned event ledger.
  - The statuses `active`, `review`, `done`, and `dropped`.
  - Human-only verbs that refuse inside agent runs.
  - `@goal:<id>` citations and a `goal:` artifact kind.
- **Not yet.** `docs/goals.md` lists these as "coming next":
  - deterministic agent binding;
  - claims with verification;
  - drafts;
  - the Goals tab;
  - the attention cutover.

  The `draft` and `claimed` vocabulary is reserved but not produced.
- **Invariants already decided.**
  - `goal-ledger`: immutable events plus live markers. Criteria drift is recorded for free.
  - `goals-host-binds`: one goal per turn; agents claim or keep open; *only a human
    settles*. Its cost section already names "per-model claim precision" (cld).
- **Metrics already designed.** The September goals design lists claims per day,
  verify/reject/acknowledge/lapse rates per model, and median time-to-verify. Those are
  eval metrics.

The October 5 and 6 goals reading lists moved the design toward lighter goal creation,
human ownership, standing goals, and honest settlement. They covered Factory's
contract-before-plan, Husain's "hard to eval is a product smell," Showboat, and *Optimized
but Unowned*. All of these are eval readings too. This list doesn't re-rank them,
except as companions.

### Your annotations, and which readings answer them

| Your note on the AutomationXP26 paper | Readings that speak to it |
| --- | --- |
| "at any altitude!" | [#6 GQM](#6-the-goal-question-metric-approach) (goal → question → metric), [#13 GORE](#13-goal-oriented-requirements-engineering-a-guided-tour) (refinement trees), Agent-as-a-Judge/PaperBench rubric trees ([HM](#honorable-mentions)) |
| "Use goals to drive evals that databricks research recommended!" | [#1](#1-demystifying-evals-for-ai-agents), [#4](#4-benchmarking-coding-agents-on-databricks-multi-million-line-codebase), [#6](#6-the-goal-question-metric-approach) (the same idea, from 1994) |
| Evaluation is "bidirectional" | [#3](#3-who-validates-the-validators), [#5](#5-ai-evals-everything-you-need-to-know) (validating judges against you) |
| "Goals should always link back to a user prompt!" | [#4](#4-benchmarking-coding-agents-on-databricks-multi-million-line-codebase) and SWE-Together (replays from real requests), [#9](#9-agents-are-systems-not-models) RealSWE (the original prompt changes the score) |
| "Predictive capability?" | [#14](#14-agentic-uncertainty-reveals-agentic-overconfidence) and its METR time-horizon companion |
| Outcome simulation: "Now this is an interesting idea." | [#2](#2-reality-is-the-final-verifier)'s evaluator cascade (model → simulator → recorded traces → canary) |
| "New sub-goals should be reviewed for alignment?!" | [#13](#13-goal-oriented-requirements-engineering-a-guided-tour) (refinement sufficiency, obstacles), [#12](#12-goodharts-law-and-specification-gaming) (a sub-goal is a proxy), goal drift ([HM](#honorable-mentions)) |
| "who changed them, when, and why" / "Does this only apply to standing goals?" | [#3](#3-who-validates-the-validators) (criteria drift), [#13](#13-goal-oriented-requirements-engineering-a-guided-tour) (*achieve* vs *maintain* goals), [#17](#17-who-actually-wrote-the-spec) (`git log` on the eval suite) |

## 2. A mental model to read with

### Goals as a source of eval cases

The table maps goal-lifecycle objects to eval objects. The middle column uses the
vocabulary of [#1](#1-demystifying-evals-for-ai-agents).

| Goal lifecycle | Eval concept | Caveat |
| --- | --- | --- |
| Goal: outcome, criteria, origin prompt | **Task**: inputs plus success criteria | It is a good task only if two careful reviewers would settle it the same way |
| Host-bound turn: model, harness, prompt, memory bundle, machine | **Trial**, with its configuration recorded | Record the machine and its resource envelope too ([HM](#honorable-mentions): infrastructure noise) |
| Transcript, ToolRuns, stitches | **Transcript** and **outcome** | The outcome is the state of the world, not the agent's story |
| Claim with evidence | The agent's **self-grade** | The least reliable grader (#14) |
| Verify / reject / acknowledge / lapse | **Human grade**, the gold label | Noisy unless it records *why* (MSR study, [HM](#honorable-mentions)) |
| Criteria edited, goal reopened | **Criteria drift** (#3) | The ledger already keeps these events |
| Settled code goal plus start commit | Candidate **replay task**: a capability eval while it is hard, a regression eval once it passes reliably | Seal the history and pass admission checks first (§4) |
| Dropped or rejected goals | **Negative cases** ("should not claim") | Mining merged PRs can't give you these (cld) |

The relation is many-to-many (cdx). A standing goal can motivate many cases, and one run
can provide evidence for several criteria. Goal creation can stay light, because structure
is added only when a scenario is *promoted* into an eval.

Reality Is the Final Verifier's notation helps here:

- **Intent (I)** is what you want. The goal records it.
- **Requirements (R)** are the goal's written criteria.
- **Evaluator (E)** is any grader. It runs under some **environment model (M)**: tests, a
  replay sandbox, or an LLM judge.
- **Work (P)** is what the agent produced.

When you reject a claim, the fault was in P, R, M, or E. Recording which one turns a
verdict from a label into a lesson.

### Three scoreboards to keep separate (grk)

1. **Harness.** This exists already: `fakey`, ToolRun triage, receipts. It asks whether
   SASE did what SASE promised.
2. **Goal outcome.** Build this first. Replay a frozen goal and grade the world.
3. **Goal process.** Build this later. Check the trajectory: verify before claiming, stay
   in scope, take the honest blocked exit. Use at most three behavior specs
   ([#15](#15-behavior-specs)).

### Three loops, in order of cost (cld)

1. **Observe.** This is nearly free once claims exist. Track:
   - claim precision (verified ÷ claimed);
   - reject reasons, first as free-form notes, then grouped into a taxonomy;
   - time to verify.

   Two caveats apply:
   - **The numbers are confounded.** You choose which model gets which goal, so they
     describe usage, not capability.
   - **Precision alone can be gamed by never claiming.** Also track claim recall (the
     share of successful runs that claimed) and premature claims (cdx).
2. **Replay.** Run the Databricks pilot on settled goals, k times per configuration.
3. **Calibrate.** Measure a "would you verify this?" pre-screener against your verdicts
   (TPR/TNR) before it reorders Needs Review.

## 3. Tensions, and what the evidence says

1. **Criteria before or after the work?**
   - *Before:* Factory, Codex Goals, and Anthropic's sprint contracts write the contract
     first, so it isn't shaped by the planned implementation.
   - *After:* Shankar shows criteria emerge from grading outputs.
   - *Resolution:* freeze a criteria version per trial and allow explicit revision. Record
     what changed and why. If you compare systems under revised criteria, regrade both.
     Exploring what you value and measuring against an agreed standard are both
     legitimate, but don't present one as the other (cdx).
2. **Tests, judges, or you?**
   - *Tests alone overstate.* Databricks refuses LLM judges for correctness: they "reward
     sounding right over being right." Yet METR found 38% of runs passed tests while none
     of the reviewed PRs was mergeable. TestJack finds about 34% of trials judged correct
     violate the task's requirements.
   - *Judges can work on a narrow benchmark.* Agent-as-a-Judge reached about 90%
     agreement with humans on its own benchmark.
   - *Resolution:* layer them. Use code graders where they can run, judges only for
     criteria code can't reach (validated against your labels first), and yourself as the
     gold label. **Your verdict is not redundant with tests.**
3. **Should a replay use your original prompt or a rewritten task statement?** cld left
   this open. The lead found new evidence in RealSWE (2026-08, [#9](#9-agents-are-systems-not-models)):
   - Realistic user-written requests cut resolution by **6.4 points on average** and can
     **change model rankings**.
   - Stating the desired behavior and the motivation matters significantly. Environment
     details and reproduction steps "merely add tokens."
   - *Resolution:* replay the origin prompt, because that is the distribution SASE
     actually faces. This is a measurable reason for "goals link back to a user prompt."
     A rewritten variant makes a second condition that measures the value of articulating
     the goal.
4. **What should you vary?** Agents Are Systems (#9) found about 54% of outcome variance
   came from repeating the same configuration. The information given to the agent had the
   largest effect, exceeding both time budget and model size. Databricks saw harnesses
   change cost per task by more than 2× in some cases at equal quality.
   - *Resolution:* SASE's most informative early experiments are about goal text and
     harness (memory, skills, instructions), not model leaderboards. Repeat trials, because
     one green run means little.
5. **What happens when goal criteria become targets?** None of the five reports raised
   this.
   - Manheim and Garrabrant's four Goodhart variants and DeepMind's specification-gaming
     catalogue (#12) describe how optimizing a proxy breaks its link to the goal.
   - ImpossibleBench shows the remedy works. An honorable "flag for human" exit cut
     GPT-5's cheating from 54% to 9%.
   - *Resolution:*
     - Keep graders that agents can't see or edit.
     - Score an honest blocked or impossible exit as *correct*.
     - Treat criteria as prompts for *your* judgment, not as a contract an agent can
       satisfy on its own.
   - DeepMind's line is the case for human settlement: "It is often easier to evaluate
     whether an outcome has been achieved than to specify it explicitly."
6. **Do finished sub-goals mean the parent is done?** GORE (#13) says no.
   - A refinement is a hypothesis that rests on assumptions, so "all children done" does
     not certify the parent.
   - *Maintain* goals, unlike *achieve* goals, are judged over a time window. This answers
     your "does this only apply to standing goals?" note: standing goals need an
     observation window and a sampling policy.
   - GQM's goal template (#6) adds a *viewpoint* field, which states whose goal it is.
7. **Who owns the eval suite?** Tian Pan (#17) writes that "The suite cannot catch an
   error it shares": whoever writes the evals writes the spec. Goals fix this only if
   agent-drafted criteria pass through a real human act. That connects to round two's
   *Optimized but Unowned*.
8. **The review surface needs its own evaluation.** The Overseeing Agents study found that
   its improved interface reduced the time spent finding errors and raised confidence,
   but "final accuracy was not meaningfully improved." A faster Goals review card isn't
   automatically a more accurate one. Measure incorrect acceptances and reversals, not
   just time to verify. (This corrects gem and partly grk; see §5.)

## 4. A first experiment the readings point to

This is not a plan. It shows what the readings converge on, so you can tell when a design
fights them. The purpose is narrow (cdx): **learn whether you can measure task success and
diagnose a disputed result.** A leaderboard is not the goal.

1. **Choose 8–12 tasks from real SASE failures and settled goals.** Databricks sets the
   pilot size. Anthropic says to source tasks from real failures and grow to 20–50.
2. **Admit a task only if it passes four checks** (ABC checklist; RepoTrials'
   BASE/RED/GOLD/NOOP runs):
   - the grader fails on the start commit;
   - it passes on the accepted change;
   - a null agent fails;
   - two careful reviewers would agree on the verdict.
3. **Seal each task.** The workspace must hold no future git objects. Keep the graders
   outside the agent's reach (Databricks; Anthropic's git-history incident).
4. **Include one impossible or underspecified task.** An honest abort is the correct
   outcome (ImpossibleBench).
5. **Make the first comparison about goal articulation.** Run the same workflow on the
   origin prompt with and without an explicit outcome and criteria (cdx, #9).
6. **Record the conditions.** Note model, harness, SASE version, prompt digest, machine,
   and resource envelope. Keep timeouts and crashes in the denominator, and classify
   infrastructure failures separately with ToolRun triage.
7. **Repeat each task and report both pass@k and pass^k.** At 80% per-trial success,
   pass@3 is 99.2% but pass^3 is 51.2%: very different promises. Keep per-task results
   rather than one pooled average.
8. **Ask Trust Layer's four questions beside every pass** (#10), using artifacts you
   already store.
9. **Read every failure before adding machinery.** Was the fault in the agent, the
   environment, the grader, or the goal (P, M, E, or R)?

Postpone choosing a framework (MLflow, Inspect, Harbor) until the pilot shows a real
storage, tracing, or grading need. All five researchers converged on that order.

## 5. Corrections to the researcher reports

The lead checked every ranked source that looked doubtful. Each fix below is reflected in
the ranked list.

| Report | Claim | What the source shows |
| --- | --- | --- |
| gem #2 | Recommends the AutomationXP26 goals paper | You finished it on 2026-10-13. It is used here as the brief, not as a recommendation |
| gem #1 | Anthropic's evals post is by "Prithvi Rajasekaran and the Anthropic Engineering Team" | The page lists Mikaela Grace, Jeremy Hadfield, Rodrigo Olivares, and Jiri De Jonghe |
| gem #8 (also grk, partly) | An outcome view helps reviewers "catch significantly more errors in half the time" | The abstract says the design reduced time to find errors and raised confidence, but "final accuracy was not meaningfully improved" |
| gem #9 | Databricks "Evaluating Agentic Systems: Traces, Judges, and the Quality Flywheel" | The URL returns 404 and no page has that title. The real page is the MLflow "Evaluate and improve" doc |
| gem #10 | Eugene Yan, "Product Evals in Three Simple Steps," at `/writing/evals/` | The title is real but the URL is wrong. That URL is a 2024 post on task-specific evals. The real post is [`/writing/product-evals/`](https://eugeneyan.com/writing/product-evals/) (Nov 2025) |
| gem #6 | OpenAI post at `openai.com/research/evaluating-coding-benchmarks` | The real post is "Why SWE-bench Verified no longer measures frontier coding capabilities" (2026-02-23, `openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/`). The lead confirmed it through search excerpts and coverage, because openai.com blocked direct fetches |
| gem #11 | Governance Decay: soft rules "decay 8.3× faster"; a 47-token header gives 0% | Violations rose 8.3× *more* for soft policies than for hard ones, which is not a rate. About 47 pinned tokens restored 0% *in its benchmark*. The paper has a section titled "Where pinning still fails" |
| gem #12 | Lumbroso requires claims to carry a "falsifier" | Partly right. The falsifier is one field of a recording convention for consequential *choices* (Options, Recommendation, Rationale, Confidence, Falsifier). It is not a protocol for completion claims |
| gem #5 | Behavior specs grade `satisfied/violated/not_applicable` | The labels are `true/false/NA`, and the spec is "never shown to the agent" |
| gem §6 | `sase eval run`, `sase goal claim`, a `builtin@goal` finalizer | None of these exist. Treat them as illustration. "An enterprise-grade evaluation engine for free" overclaims: goals supply a corpus and labels, not experimental control |
| grk #7 | Agents Are Systems is dated 2026-10-02; budget helps when information suffices | v1 is dated 2026-10-01. The abstract says extra time helps "only when the agent has sufficient information **or a capable enough model**" |
| grk §6 | AgentLens: 10.7% of passing SWE-agent trajectories are Lucky Passes | That figure covers one subset: 1,815 OpenHands trajectories on 47 tasks. The per-backend range is 0.5–23.2% |
| cld #9 | Assessment before execution discriminates better | The abstract hedges: "though differences are not always significant" |
| cld #6 | METR: none mergeable; 26 minutes to fix | "None mergeable" covers the 15 PRs reviewed by hand. The 26-minute figure is for the 4 test-passing runs; across all reviewed PRs the average was 42 minutes |
| cld #3 | Databricks harness cost differed by more than 2×; the backlog line is the post's last line | The cost gap was more than 2× only "in some cases." The backlog line sits mid-post |

Where reports disagreed on emphasis:

- **τ-bench.** cdx and mus rank it; grk calls it the wrong domain. *Resolution:* read it
  for pass^k and state-based grading only, so it is an honorable mention.
- **Factory Missions.** grk and gem rank it in their top three, but it was round two's #2.
  *Resolution:* it is a companion to #7.
- **Generic benchmarks.** mus ranks SWE-bench, Terminal-Bench, GAIA, and MT-Bench. These
  are useful background, but none is shaped like SASE's goal loop.

## 6. Ranked reading list

Ranked for *thinking through SASE evals via goals* when you're new to evals.

- **Tier A** gives you the vocabulary and the frame.
- **Tier B** prepares you to build the pilot.
- **Tier C** sharpens goal semantics.

Each pick has a question to carry into the reading.

### Tier A: read first

#### 1. Demystifying evals for AI agents

- **Link.** <https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents>
- **Authors and date.** Grace, Hadfield, Olivares, De Jonghe (Anthropic), 2026-01-09.
- **Library.** Already in your library (queued since 2026-01-11, legacy backlog).
- **Ranked by.** All five reports, each at #1 or #2.

**Why.** It is the vocabulary every other reading assumes:

- task, trial, grader, transcript, and outcome;
- capability evals versus regression evals, where tasks "graduate" from one to the other;
- pass@k versus pass^k;
- start with "20–50 simple tasks drawn from real failures."

It also contains the git-history leak story: Claude gained an unfair advantage by reading
earlier trials' history.

**Question to bring.** Which of your goals would two careful reviewers settle the same way,
and what would the others need?

**Limit.** A vendor guide whose examples are mostly customer-facing agents.

#### 2. Reality Is the Final Verifier

- **Title.** "Reality Is the Final Verifier: On Two Key Gaps in Agentic Software
  Engineering"
- **Link.** <https://arxiv.org/abs/2609.12039>
- **Authors and date.** Krentsel, Agarwal, Cemri, Liu, Sankhe, Mao, Zaharia, Stoica (UC
  Berkeley), 2026-09-10.
- **Library.** Already in your library (queued).
- **Ranked by.** cld #2, grk #6.

**Why.** It is the cleanest theory of why goals and evals are different objects that must
stay linked. The *requirement gap* sits between criteria and intent, and the *model gap*
between the checked environment and reality. An assurance–revision loop uses deployment
evidence to revise requirements, model, or evaluator. That loop is the principled argument
for "only a human settles." Its evaluator cascade is a concrete picture of the "outcome
simulation" you marked as interesting.

**Question to bring.** Should a reject verdict record whether the fault was in the work,
the criteria, the environment, or the check?

**Limit.** A position paper with no empirical study.

#### 3. Who Validates the Validators?

- **Title.** "Who Validates the Validators? Aligning LLM-Assisted Evaluation of LLM Outputs
  with Human Preferences" (introduces EvalGen)
- **Link.** <https://arxiv.org/abs/2404.12272>
- **Authors and date.** Shankar, Zamfirescu-Pereira, Hartmann, Parameswaran, Arawjo,
  2024-04 (UIST 2024).
- **Ranked by.** cdx #3, cld #4, mus #4, grk (next tier).

**Why.** It names **criteria drift**: "users need criteria to grade outputs, but grading
outputs helps users define criteria." This is the strongest bridge between learning evals
and still discovering what goals mean. It is also the counterweight to every
contract-first reading.

**Question to bring.** When you reject a claim and then edit the goal, is that a rejection
of the work or a correction of the spec? Should the ledger tell the two apart?

**Limit.** A small qualitative study (nine practitioners) of LLM pipelines, not agents.

#### 4. Benchmarking Coding Agents on Databricks' Multi-Million Line Codebase

- **Link.** <https://www.databricks.com/blog/benchmarking-coding-agents-databricks-multi-million-line-codebase>
- **Authors and date.** Gaba, Mathur, Singh, Wendell, Zaharia (Databricks), 2026-07-08.
- **Companion (lead find).** Wu et al., ["SWE-Together: Evaluating Coding Agents in
  Interactive User Sessions"](https://arxiv.org/abs/2606.29957) (2026-06-29). It builds
  109 replay tasks from 11,260 real user–agent sessions, keeping those where the repo state
  is recoverable, the user's goal is clear, and the outcome is observable. It measures final
  correctness *and* the number of corrective feedback turns needed.
- **Ranked by.** cld #3.

**Why.** It is your pilot, done by the company whose roles prompted it:

- **Tasks.** Merged PRs filtered for quality.
- **Prompts.** PR descriptions were rewritten to state the goal with the solution removed.
- **Grading.** Held-out tests, and no LLM judge.
- **The leak.** The answer was "still recoverable in the Git history of the worktree!"

It ends on the line "Any team with a backlog of merged PRs is sitting on a benchmark
already that no model has trained on." SWE-Together adds the SASE-shaped admission rule
and an interventions metric that maps onto your corrective follow-ups.

**Question to bring.** Which settled goals meet SWE-Together's three admission conditions?

**Limit.** A company blog with self-reported results, and its test-only grading inherits
#8's gap.

#### 5. AI Evals: Everything You Need to Know

- **Title.** "AI Evals: Everything You Need to Know" (the evals FAQ)
- **Link.** <https://hamel.dev/blog/posts/evals-faq/>
- **Authors and date.** Hamel Husain and Shreya Shankar. The current page is dated
  2026-09; earlier versions circulated from 2025.
- **Companion.** Husain, ["Your AI Product Needs
  Evals"](https://hamel.dev/blog/posts/evals/) (2024-03-29), the narrative on-ramp (cdx #1,
  mus #2).
- **Ranked by.** cld #5, plus the companion's two votes.

**Why.** These are the most actionable practices for a beginner:

- error analysis first, by open-coding traces and then grouping the notes into a failure
  taxonomy;
- binary grades;
- one "benevolent dictator" (you);
- "Build a custom annotation tool," which the Goals review card can be;
- validating each judge against human labels with TPR and TNR.

**Question to bring.** What would your first ten reject-reason codes be?

**Limit.** Built around LLM products; the coding-agent material is thin.

### Tier B: before building the pilot

#### 6. The Goal Question Metric Approach

- **Link.** <https://www.cs.umd.edu/~mvz/handouts/gqm.pdf>
- **Authors and date.** Basili, Caldiera, Rombach, *Encyclopedia of Software Engineering*
  (1994).
- **Ranked by.** Lead find; no researcher included it.

**Why.** This is your annotation, written 30 years ago. Measurement "must be defined in a
top-down fashion… based on goals and models. A bottom-up approach will not work." It has
three levels:

- **Goal** (conceptual): an object, purpose, quality issue, and **viewpoint**.
- **Questions** (operational).
- **Metrics** (quantitative).

The viewpoint field fits person-owned goals, and the hierarchy fits "at any altitude." GQM
also protects against the obvious failure: collecting every metric SASE can emit and then
hunting for meaning. The paper is ten pages long.

**Question to bring.** For one real goal, which questions would decide settlement, and
which metrics answer them?

**Limit.** Built for organizational process measurement, with nothing on agents or
non-determinism.

#### 7. "It's Hard to Eval" Is a Product Smell

- **Link.** <https://hamel.dev/blog/posts/eval-smell/>
- **Author and date.** Hamel Husain, 2026-06-29.
- **Companion.** Theo Luan (Factory), ["How Missions
  Work"](https://factory.com/news/missions-architecture) (2026-04-10). It writes the
  validation contract before the plan, and an independent validator, not the worker,
  decides "done." It was round two's #2, so read it now through an eval lens if you
  haven't yet.
- **Ranked by.** grk #2, gem #4, cdx #5.

**Why.** "Designing your product for ease of verification should come before building
evals." Goals-as-evals works only if a claim leaves evidence someone else can check:

- a prompt snapshot;
- a diff;
- receipts;
- an assertion list.

**Question to bring.** For each outcome type (answer, research, plan, code), what checkable
artifact should sit beside a claim?

**Limit.** A design essay, not a measurement.

#### 8. Algorithmic vs. Holistic Evaluation

- **Title.** "Research Update: Algorithmic vs. Holistic Evaluation"
- **Link.** <https://metr.org/blog/2025-08-12-research-update-towards-reconciling-slowdown-with-time-horizons>
- **Author and date.** David Rein (METR), 2025-08-13.
- **Ranked by.** cld #6.

**Why.** Claude 3.7 Sonnet passed maintainer tests on 38% (±19%) of 18 real issues.
Manual review of 15 PRs found none mergeable as-is. Missing tests, missing docs, and
code-quality problems appeared at similar rates whether or not the tests passed. This is
the strongest evidence that your verdict measures something tests don't, and its failure
categories are a starting reject taxonomy.

**Question to bring.** How often do you verify a green claim you'd still edit before
landing?

**Limit.** 18 tasks, two strict repos, and an older model.

#### 9. Agents Are Systems, Not Models

- **Title.** "Agents Are Systems, Not Models: Rethinking Agentic Evaluation"
- **Link.** <https://arxiv.org/abs/2610.01618>
- **Authors and date.** Wiedmann, Girrbach, Schmid, Akata, 2026-10-01.
- **Companion (lead find).** Kim et al., ["RealSWE: A Compositional Evaluation of Coding
  Agents under Realistic User Requests"](https://arxiv.org/abs/2608.27831) (2026-08-28).
  Realistic requests cut resolution by 6.4 points on average and can change rankings.
  Desired behavior and motivation matter most.
- **Ranked by.** grk #7, with the companion added by the lead.

**Why.** About 54% of outcome variance came from repeating the same configuration. The
information given to the agent mattered more than time budget or model size. Together with
RealSWE, this says **the goal text is an experimental treatment**. It also gives direct
evidence that what you write in a goal changes the outcome.

**Question to bring.** When a frozen goal fails, is the next experiment a different model,
a bigger budget, or a better goal?

**Limit.** Four scientific coding tasks. RealSWE uses public benchmarks, not your repo.

#### 10. A Trust Layer for Agent Evaluation

- **Link.** <https://arxiv.org/abs/2610.07274>
- **Authors and date.** Sediqin, Dalmia, Kovvuri, Mukherji, 2026-10-05.
- **Companions.** [TestJack](https://arxiv.org/abs/2610.10619) (2026-10-07): about 34.4%
  of trials judged correct violate task requirements. [AgentLens](https://arxiv.org/abs/2605.12925):
  10.7% "Lucky Passes" in one subset of passing trajectories.
- **Ranked by.** grk #8; the companions are grk next-tier picks.

**Why.** It reports four checks *beside* a score, never rewriting it:

1. Is the result supported by the benchmark's own grading logic?
2. Was the pass earned through traceable computation?
3. Does the completion claim match what occurred?
4. Is the result stable when rerun?

Only 22.6% of recorded passes cleared all four (95% CI 15.0–32.6). The checks map onto
SASE's triage, ToolRun traces, claim-versus-evidence, and pass^k, and they follow
"triage annotates; it never changes an exit code."

**Question to bring.** Can checks 1–3 be computed from artifacts you already store?

**Limit.** Agents' Last Exam tasks, not SWE. The numbers won't transfer, but the shape will.

#### 11. Measuring What Matters

- **Title.** "Measuring what Matters: Construct Validity in Large Language Model
  Benchmarks"
- **Link.** <https://arxiv.org/abs/2511.04703>
- **Authors and date.** Bean et al. (42 authors, Oxford-led), NeurIPS 2025 Datasets &
  Benchmarks.
- **Companion.** OpenAI, ["Why SWE-bench Verified no longer measures frontier coding
  capabilities"](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)
  (2026-02-23). It reports flawed tests that reject correct solutions, plus contamination.
  gem cited it under a wrong URL.
- **Ranked by.** Lead find.

**Why.** It reviews 445 benchmark papers and gives eight recommendations with a checklist:

1. define the phenomenon;
2. measure only it;
3. sample representative tasks;
4. acknowledge the limits of reused datasets;
5. prepare for contamination;
6. use statistics;
7. do error analysis;
8. justify validity.

The first recommendation is your goals thesis in measurement terms: "The target phenomenon
should be clearly defined before operationalising it in a benchmark." Only 16% of the
papers used uncertainty estimates or statistical tests.

**Question to bring.** What construct does a SASE eval claim to measure: model capability,
harness quality, or "agents achieve your goals"?

**Limit.** Aimed at public benchmark authors; use it as a checklist.

### Tier C: designing goal semantics

#### 12. Goodhart's law and specification gaming

- **Main.** Manheim and Garrabrant, ["Categorizing Variants of Goodhart's
  Law"](https://arxiv.org/abs/1803.04585) (2018). It names four variants: regressional,
  extremal, causal, and adversarial.
- **Companion.** Krakovna et al. (DeepMind), ["Specification gaming: the flip side of AI
  ingenuity"](https://deepmind.google/discover/blog/specification-gaming-the-flip-side-of-ai-ingenuity/)
  (2020-04-21).
- **Second companion.** [ImpossibleBench](https://arxiv.org/abs/2510.20270) (2025-10),
  grk #10. An honorable exit cut cheating from 54% to 9%.
- **Ranked by.** Lead find, plus grk's ImpossibleBench.

**Why.** This is the risk none of the reports named. Once a goal's criteria are what agents
are graded on, the criteria become proxies, and optimization pressure separates them from
your intent. DeepMind's catalogue gives the vocabulary, and its key sentence argues for
human settlement: "It is often easier to evaluate whether an outcome has been achieved
than to specify it explicitly."

**Question to bring.** Which of your goal criteria could an agent satisfy without
satisfying you?

**Limit.** Conceptual. The examples come from RL, not coding agents.

#### 13. Goal-Oriented Requirements Engineering: A Guided Tour

- **Link.** <https://webperso.info.ucl.ac.be/~avl/files/RE01.pdf>
- **Author and date.** Axel van Lamsweerde, RE'01 (2001).
- **Ranked by.** cdx #4.

**Why.** It is the deepest vocabulary for "goals at any altitude":

- refinement into sub-goals, along with the assumptions that make a refinement sufficient;
- obstacles;
- conflicts;
- *achieve* versus *maintain* goals.

It answers two of your annotations: reviewing sub-goals for alignment, and whether change
history only matters for standing goals.

**Question to bring.** If all proposed sub-goals succeed, why should the parent follow?

**Limit.** Formal and safety-critical in places. Borrow the distinctions, not the method.

#### 14. Agentic Uncertainty Reveals Agentic Overconfidence

- **Link.** <https://arxiv.org/abs/2602.06948>
- **Authors and date.** Kaddour et al., 2026-02-06.
- **Companion.** METR, ["Measuring AI Ability to Complete Long
  Tasks"](https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/)
  (2025-03-19).
- **Ranked by.** cld #9.

**Why.** It answers your "Predictive capability?" note. Some agents that succeed 22% of
the time predict 77%, so a claim is an inflated self-grade. Assessment before execution
often discriminates better than review afterward, though not always significantly.
Prediction is measurable: record a "will this be verified?" forecast at bind time and score
it at settlement.

**Question to bring.** How many settled goals would a calibration curve need?

**Limit.** Benchmark tasks, not multi-session goals.

#### 15. Behavior specs

- **Title.** "Behavior specs, an open standard for supervising long-horizon agents"
- **Link.** <https://www.braintrust.dev/blog/behavior-specs>
- **Authors and date.** Goyal (Braintrust) and Troyanovsky (Basis), 2026-07-29.
- **Ranked by.** cdx #6, grk #9, gem #5.

**Why.** It is a ready format for the process scoreboard. Specs are written in the second
person, graded `true/false/NA` over a trajectory, "never shown to the agent," and retired
once models internalize them. Its coding example is nearly a SASE receipt rule: a report of
done should rest on the project's checks.

**Question to bring.** Which three behaviors would make you fail a green claim? If your list
is longer than three, you are writing a constitution.

**Limit.** A vendor-advocated standard.

#### 16. The Second Half

- **Link.** <https://ysymyth.github.io/The-Second-Half/>
- **Author and date.** Shunyu Yao, 2025-04-10.
- **Ranked by.** cld #7.

**Why.** It is the inspirational read: "evaluation becomes more important than training."
Benchmarks are autonomous and i.i.d., while real work is human-in-the-loop and sequential.
SASE's work is sequential and memory-dependent, which suggests an eval where **memory is
the treatment**. Replay a goal with today's memory and with the memory as of the goal's
start date.

**Question to bring.** Does SASE make the 50th goal in a project easier than the first?

**Limit.** An essay with no method.

#### 17. Who actually wrote the spec?

- **Main.** Tian Pan, ["The Eval Suite That Became the Spec Nobody Agreed
  To"](https://tianpan.co/blog/2026/05/17/eval-suite-became-spec-nobody-agreed-to)
  (2026-05-17).
- **Companions.**
  - Braintrust, ["Evals are the new PRD"](https://www.braintrust.dev/blog/evals-are-the-new-prd)
    (2026-03-27).
  - Sean Grove (OpenAI), ["The New Code"](https://www.youtube.com/watch?v=8rABwKRsec4) (AI
    Engineer World's Fair 2025, 22 minutes). In the Model Spec, each clause has an ID linked
    to challenging prompts, so "the document itself actually encodes success criteria."
- **Ranked by.** cld #10; Grove added by the lead.

**Why.** Pan's warning is that whoever writes the evals writes the PRD. Goals settled by a
person fix that. Grove shows the positive version: one intent document serves as spec,
training material, and eval material. By analogy, each goal criterion could carry an ID
that its eval cases cite.

**Question to bring.** What is the minimum human act that makes agent-drafted criteria part
of an agreed spec?

**Limit.** A practitioner blog, a vendor post, and a talk.

### Honorable mentions

| Read this | Why |
| --- | --- |
| [τ-bench](https://arxiv.org/abs/2406.12045) (2024) → [τ²-bench](https://arxiv.org/abs/2506.07982) (2025) | It introduced pass^k and grading on database state. τ² adds a user who also acts on the shared environment |
| Kapoor et al., ["AI Agents That Matter"](https://arxiv.org/abs/2407.01502) (2024) + Anthropic, ["Quantifying infrastructure noise"](https://www.anthropic.com/engineering/infrastructure-noise) (2026-02) | Cost-aware comparisons and holdouts. Resource settings alone moved Terminal-Bench by 6 points |
| Zhuge et al., ["Agent-as-a-Judge"](https://arxiv.org/abs/2410.10934) (2024) + PaperBench rubric trees | Hierarchical requirements graded by an agent with tools. This is what a goal pre-screener could look like |
| Zhu et al., ["Agentic Benchmark Checklist"](https://arxiv.org/abs/2507.02825) (NeurIPS 2025) + Jarmak, ["Engineering Reliable Coding Agents"](https://arxiv.org/abs/2608.13867) (2026) | Task validity and outcome validity, an admission checklist for replay tasks, and the point that merged history is a biased sample |
| Grunde-McLaughlin et al., ["Overseeing Agents Without Constant Oversight"](https://arxiv.org/abs/2602.16844) (2026-02) | It evaluates the review surface itself. Read it for the corrected result: faster and more confident, but not more accurate |
| Arike et al., ["Evaluating Goal Drift"](https://arxiv.org/abs/2505.02709) (2025) + Cai et al., ["Push Your Agent"](https://arxiv.org/abs/2605.23574) (2026) | The only evals here of *goal integrity*: false completion, premature stopping, progress inflation |
| Peralta et al., ["Why Are Agentic Pull Requests Merged or Rejected?"](https://arxiv.org/abs/2605.22534) (MSR 2026) | Per cld, only about a third of rejections showed agent failure. A reject without a reason is a noisy label |
| OpenAI cookbook, ["Using Goals in Codex"](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex) | Six contract fields for a frozen goal: outcome, verification surface, constraints, boundaries, iteration policy, blocked stop (grk #4) |
| GitHub Next, ["Autoloop"](https://githubnext.com/projects/autoloop/) (2026) | The smallest loop that is already an eval: Goal + Target files + Evaluation command (grk #5) |
| Jason Wei, ["Asymmetry of verification"](https://www.jasonwei.net/blog/asymmetry-of-verification-and-verifiers-law) (2025) | Goals that are cheap to verify will be automated first; the rest stay with human settlement |
| [HealthBench](https://arxiv.org/abs/2505.08775) (2025) + [TICK](https://arxiv.org/abs/2410.03608) (2024) | Every item carries its own rubric, the precedent for per-goal criteria graded item by item |
| Chen, ["Governance Decay"](https://arxiv.org/abs/2606.22528) (2026-06) | Context compaction erases soft constraints, and host-pinning restores them in its benchmark. This supports binding goals host-side (gem #11, corrected) |
| Lumbroso, ["Cybernetic and Epistemic"](https://arxiv.org/abs/2610.00961) (2026-10) | Record a falsifier for consequential choices. A possible field for claims (gem #12, corrected) |
| Zheng et al., ["Judging LLM-as-a-Judge"](https://arxiv.org/abs/2306.05685) (2023) | Position, verbosity, and self-preference biases to design around before any goal judge (mus #5) |
| Eugene Yan, ["Product Evals in Three Simple Steps"](https://eugeneyan.com/writing/product-evals/) (2025-11) | An alternative beginner recipe: label, align the evaluator, run the harness on every change |
| [RepoTrials](https://dev.to/repotrials/repotrials-turn-your-git-history-into-private-coding-agent-benchmarks-4462) and [Harbor](https://harborframework.com/) | Tooling to look at before writing your own runner (cld) |

**Not re-ranked because you have read or been offered them:**

- **The AutomationXP26 goals paper.** Finished 2026-10-13. cdx found its empirical
  companion, ["Nudging Attention to Workplace Meeting
  Goals"](https://arxiv.org/abs/2602.16939), worth one caution: post-meeting goal
  measurement itself changed behavior in both groups.
- **Round two's picks.** Factory Missions (companion to #7), Showboat, and *Optimized but
  Unowned*.
- **Already in your library.** grk lists Anthropic's harness-design post as queued and
  *What Does a Harness Buy?* as finished.

### Suggested library captures

These are proposals; none was run. They cover the top unread picks:

```bash
bob ref create https://arxiv.org/abs/2404.12272
bob ref create https://www.databricks.com/blog/benchmarking-coding-agents-databricks-multi-million-line-codebase
bob ref create https://hamel.dev/blog/posts/evals-faq/
bob ref create https://www.cs.umd.edu/~mvz/handouts/gqm.pdf
bob ref create https://hamel.dev/blog/posts/eval-smell/
bob ref create https://metr.org/blog/2025-08-12-research-update-towards-reconciling-slowdown-with-time-horizons
bob ref create https://arxiv.org/abs/2610.01618
bob ref create https://arxiv.org/abs/2610.07274
bob ref create https://arxiv.org/abs/2511.04703
bob ref create https://arxiv.org/abs/1803.04585
```

### Method and limits

- **Context read.** The five researcher reports, the Databricks v2 report, the round-two
  goals list (through `sase artifact read`), your 13 annotations (`bob ref show`), and
  `docs/goals.md` plus `sase goal --help` in the sase repo. The lead did not open
  `bbugyi200/job--research`; claims about it come from cdx, cld, and grk.
- **Verification.**
  - The lead fetched or checked abstracts for every gem pick, the arXiv picks from grk and
    cld, the key Databricks, METR, Anthropic, Hamel, Braintrust, Showboat, and Tian Pan
    pages, and every lead-added source.
  - Some HealthBench, CursorBench, and Peralta details rest on the researchers' reads.
  - The OpenAI SWE-bench post was confirmed through search excerpts and coverage, because
    openai.com blocked direct fetches.
- **Gap that remains.** No source evaluates a *personal* multi-agent orchestrator against
  one person's goals (cld). That is probably the novel part of what you would build.

Library check: 2 of 55 candidates already in your library (0 finished).
