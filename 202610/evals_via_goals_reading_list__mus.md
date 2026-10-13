# Evals via Goals: inspiration reading list

_Researcher mus · 2026-10-13 · independent swarm report (suffix `__mus`)_

**Brief.** Bryan is new to evals, still thinking through goals, and leaning toward
implementing evals *using goals* (which do not exist yet). This report finds
articles/papers to inspire that design. I worked independently: I did not open any
peer swarm report (`__cdx` / `__cld` / `__grk` / `__gem`) for this swarm; filenames
were listed only to avoid overwriting my own output.

**Context I consulted (base syntheses and own prior work only).**

- Databricks thread: `research:202610/databricks_nyc_cv_and_role_pitches/databricks_nyc_cv_and_role_pitches.md`
  (base synthesis) and my own prior `__mus` in the same directory. The key line for
  this task: SASE has strong *harness-reliability* signals (ToolRun records,
  normalized failure signatures, NEW/KNOWN/FLAKY/UNKNOWN verdicts, `fakey`
  conformance, per-commit CI) but **no task-success evaluation of real agents** —
  and the synthesis proposes a small 8–12 task pilot with frozen start commits,
  explicit success checks, timeouts kept in the denominator, recorded
  harness/model/version/prompt, repeated subsets for variance, and MLflow traces.
- Goals thread, favoring recent work as instructed: the AutomationXP26 goals paper
  and Bryan's annotations on it (see below); my prior
  `research:202610/goals_redesign_recent_reading_list/goals_redesign_recent_reading_list__mus.md`
  (2026-10-05, ten recent articles) and
  `research:202610/goals_inspiration_round_two_reading_list/goals_inspiration_round_two_reading_list__mus.md`
  (2026-10-06). I deliberately avoid repeating their ranked picks; this list is
  eval-first and goal-conditioned.
- Annotation spine (from `bob ref show` on the AutomationXP26 paper, 13 comments):
  "goals enable evaluation … benchmarks for success and iterative improvement …
  bidirectional: humans assess AI outputs, AI gives goal-referenced feedback" →
  Bryan's comment: *"Use goals to drive evals that databricks research
  recommended!"* Related annotations: goals as ChangeLog/persistence endpoint,
  every goal links back to a user prompt, new sub-goals reviewed for alignment,
  beads get an optional `goal` field, planner agents run `sase goals list` before
  planning. I treat these as the design hypotheses the reading list should stress.

**Method.** Web search + page fetch. Every ranked URL below was fetched or
corroborated by two independent indexes this session; dates are publisher/byline or
arXiv v1 dates. Ranked by expected leverage on *evals-implemented-as-goals for a
single-turn, host-owned-completion agent system*, not by general quality.

## What "evals via goals" could mean in SASE

Five concrete shapes recur across the sources below; I use them as the ranking lens:

1. **Goals as eval tasks.** A goal with acceptance criteria *is* a task case:
   frozen start commit + prompt + explicit success checks. The goal ledger becomes
   the eval dataset.
2. **Goal claims as trials.** Each agent claim against a goal is a trial with a
   transcript (ToolRun record + trajectory). Grade outcomes *and* trajectories.
3. **Host verification as grader.** Deterministic checks first (tests, diff scope,
   artifact existence), LLM-judge only where determinism cannot reach, human Verify
   as the gold judge. This mirrors Anthropic's task/trial/grader/transcript split.
4. **Production flywheel.** Real goal runs (pass and fail) become regression cases;
   eval results route back into harness/prompt fixes — the Databricks "evaluation
   to improvement flywheel" at SASE scale.
5. **Criteria drift as a feature.** Grading real outputs changes what the criteria
   should have said (Shankar's finding). Goal criteria must be versioned and
   revisable, not frozen prose.

## Ranked list

### 1. Anthropic — "Demystifying evals for AI agents" (Jan 9, 2026) — read this first

https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents

Task / trial / grader / transcript vocabulary; 20–50 tasks drawn from real failures
beat hundreds of synthetic ones; run multi-trial because outputs vary; grade
outcomes *and* trajectories; the Opus 4.5 anecdote where the agent "failed" by
finding a *better* solution than the test allowed. Fetched this session (200 OK).

**Why for SASE.** This is the eval discipline the Databricks pilot spec is missing:
it tells you what a goal-claim must carry as evidence (transcript, not
self-report), why Completed needs a check stronger than "the agent says so," and
how to design graders so a genuinely better outcome is not scored a failure. Map
directly: goal = task, claim = trial, host checks + judge = graders, ToolRun
record = transcript.

**Caveat.** Vendor engineering blog, not controlled evidence. Already in Bryan's
library (queued, legacy backlog) — the one re-read worth doing because everything
else below assumes its vocabulary.

### 2. Hamel Husain — "Your AI Product Needs Evals" (Mar 29, 2024; updated 2026)

https://hamel.dev/blog/posts/evals/

Canonical "unsuccessful products share one root cause: no robust eval system."
Three levels (scoped unit tests → human/model eval on logged traces → A/B), with
the operative rule: remove all friction from looking at your data; error analysis
before eval construction; don't trust generic frameworks. Fetched this session.

**Why for SASE.** The mindset bridge for someone new to evals: start from SASE's
existing strength (ToolRun logs, failure signatures, triage verdicts) and build the
smallest eval that targets observed failures. Directly justifies the "1–2 weekend"
pilot framing and the keep-timeouts-in-the-denominator rule. Pairs with #1 as
theory + practice.

### 3. Gergely Orosz & Hamel Husain — "A pragmatic guide to LLM evals for devs" (Dec 2, 2025)

https://newsletter.pragmaticengineer.com/p/evals

Reaches the broad-engineering audience: LLM non-determinism breaks traditional
testing; error analysis → code-based evals for deterministic failures,
LLM-as-judge for subjective ones; align the judge against human labels (TPR/TNR);
evals in CI/CD plus production monitoring; the analyze → measure → improve →
automate flywheel. Fetched (paywalled body, full outline verified).

**Why for SASE.** The CI/CD + production-monitoring chapter is the template for
wiring goal-evals into SASE's two-speed CI (fast gate + scheduled matrix) without
making every commit pay judge costs. The judge-alignment section (partition data so
the judge must generalize; validate against humans) is the prerequisite for any
goal-judge Bryan builds.

### 4. Shreya Shankar et al. — "Who Validates the Validators?" (UIST 2024; arXiv:2404.12272)

https://arxiv.org/abs/2404.12272

EvalGen: humans grade a subset of outputs, then the system selects judge
implementations that best match; headline finding is **criteria drift** — users
cannot fully specify criteria a priori; grading outputs *is how* they discover
criteria. Corroborated by multiple independent indexes this session.

**Why for SASE.** The single most important paper for *goals-as-evals*: goal
acceptance criteria will drift the first time Bryan grades real claims. Design
consequence: criteria must be versioned, diffable, and revisable (merge/split
story from the goals thread), and the goal Verify UI should capture the human
grade that re-aligns the judge. Read before freezing any goal schema.

### 5. Zheng et al. — "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" (NeurIPS 2023; arXiv:2306.05685)

https://arxiv.org/abs/2306.05685

GPT-4-as-judge agrees with humans >80% on the tested sets *when* reference-guided;
documents position bias, verbosity bias, self-enhancement bias; pairwise comparison
beats absolute scoring on close calls; swap-order mitigation. Heavily corroborated.

**Why for SASE.** If any goal grader uses an LLM judge (open-ended code review,
"stayed in scope" checks), these biases are the failure modes. Practical takes:
never let the judge be the same model family as the worker without disclosure,
always swap order on pairwise grades, prefer reference-guided judging (the goal's
acceptance criteria *are* the reference). Short paper, high leverage.

### 6. Lightman et al. (OpenAI) — "Let's Verify Step by Step" (May 2023; arXiv:2305.20050; ICLR 2024)

https://arxiv.org/abs/2305.20050

Process supervision (reward each reasoning step, PRM800K) significantly outperforms
outcome supervision on MATH; catches right-answer-wrong-process; foundation for
later reasoning-model work. Corroborated.

**Why for SASE.** Frames the central grading choice: outcome-only (did the goal's
end state hold?) vs process (+ did the trajectory stay sane?). SASE's transcripts
make process grading feasible, but per-step labels are expensive — the paper helps
Bryan decide where outcome checks suffice (tests pass, artifacts exist) and where
trajectory checks pay (scope creep, secret exfiltration, destructive commands).
Read as the intellectual parent of "grade transcripts, not just end states."

### 7. Jimenez et al. — "SWE-bench: Can Language Models Resolve Real-World GitHub Issues?" (ICLR 2024; arXiv:2310.06770)

https://arxiv.org/abs/2310.06770

2,294 real Python GitHub issues with execution-based validation (FAIL_TO_PASS /
PASS_TO_PASS tests in Docker); the template every coding-agent benchmark since has
copied or reacted against. Note OpenAI's Feb 2026 "SWE-bench Verified no longer
measures frontier capabilities" as a staleness warning. Corroborated.

**Why for SASE.** The existence proof that real-issue + containerized-test evals
work — and the cautionary tale: static sets saturate and leak. For SASE, the lesson
is to build the *harness that mints fresh tasks from own history* (production goal
runs → regression set) rather than adopting SWE-bench itself. Skim the paper,
study the harness design.

### 8. Yao et al. (Sierra) — "τ-bench: Tool-Agent-User Interaction" (2024; arXiv:2406.12045; τ²-bench follows)

https://arxiv.org/abs/2406.12045

Retail/airline domains with user simulation and DB-state-diff grading; pass^k
consistency metric (all k trials must pass); empty/no-op result as explicit fail.
Corroborated.

**Why for SASE.** Closest benchmark analog to SASE's world: multi-turn tool use
under domain policy, graded on end-state diff rather than chat text. Steal three
mechanics: state-diff graders (repo diff + test results, not prose), simulated-user
trials for planner/clan flows, and pass^k to report reliability instead of a
single lucky pass. The Opus 4.5 "better solution failed the eval" story (#1) comes
from this family — read together.

### 9. Merrill et al. (Stanford / Laude) — "Terminal-Bench 2.0" (Jan 2026; arXiv:2601.11868)

https://arxiv.org/abs/2601.11868

89 hard terminal-environment tasks from real workflows in Docker; harness-only
gains cited elsewhere (same model, large rank jumps) argue most agent failures are
configuration failures. Corroborated.

**Why for SASE.** SASE agents live in a terminal; this is the eval that looks most
like SASE work (shell, repo, tools, long horizon). Use it as the external
calibration set and as the argument that goal-eval investment should go to harness
fidelity (environment, timeouts, isolation) before judge cleverness. Do not adopt
wholesale — sample tasks relevant to SASE's loop.

### 10. Mialon et al. — "GAIA: General AI Assistants" (2023; arXiv:2311.12983)

https://arxiv.org/abs/2311.12983

466 real assistant tasks requiring reasoning + tools + web use, stratified by human
task-length; humans ~92% vs GPT-4 ~15% at release — a durable "general assistant"
yardstick. Corroborated.

**Why for SASE.** The counterweight to code-only evals: SASE goals include answer,
research, and plan goals, not just code. GAIA's level-by-difficulty design suggests
stratifying goal-evals by expected human-minutes, which would let Bryan report
"reliable up to 30-minute goals, experimental beyond" instead of one blended score.
Read lightly — for the stratification idea, not the tasks.

## Honorable mentions (did not make the ten)

- **Eugene Yan / AlignEval + "A Field Guide to Rapidly Improving AI Products"
  (O'Reilly Radar, 2025; https://hamel.dev/blog/posts/field-guide/).** The
  operational companion to #4: upload data, label good/bad, measure judge-vs-human
  alignment, iterate. Recommend the field-guide post as the first follow-up after
  #1–#3 if Bryan wants a hands-on loop this weekend.
- **MLflow GenAI evaluation docs
  (https://mlflow.org/docs/latest/genai/eval-monitor/).** The Databricks-base
  synthesis already points here (`mlflow.genai.evaluate`, scorers, traces in Unity
  Catalog). Include in the pilot (log runs as MLflow traces) but read docs, not a
  paper — and keep `fakey` conformance separate from real-agent success scores.
- **Locke & Latham, "Building a practically useful theory of goal setting and task
  motivation" (American Psychologist, 2002).** The 35-year-odyssey statement of
  goal-setting theory (specific + difficult goals + feedback → performance). Not
  ranked because the AutomationXP26 paper already covers what SASE needs from goal
  theory, but cite it if Bryan wants the psychometric root.
- **Anthropic "Effective harnesses for long-running agents" (Nov 2025) and Addy
  Osmani "Loop Engineering" (Jun 2026).** Ranked #1–#2 in my 2026-10-05 goals
  report; not repeated here but still the best loop/heartbeat background for
  Permanent goals.

## Suggested reading order

1. Weekend 1: #1 → #2 → #3 (vocabulary + pilot shape + CI/flywheel).
2. Before writing any judge: #4 → #5 (criteria drift, then bias mitigations).
3. Before freezing goal-eval mechanics: #6 (outcome vs process) → #8 (state-diff +
   pass^k) → #7/#9 (harness lessons).
4. When reporting results: #10 (stratify by difficulty); keep the AutomationXP26
   annotations open throughout as the goals-side checklist.

## Caveats

- I am new-source-heavy on engineering blogs (#1–#3) because Bryan is new to evals;
  mine them for mechanics and pilot shape, not for scientific claims.
- Benchmark papers (#7–#10) saturate and leak; treat them as harness-design
  references and external calibration, never as the SASE eval set itself.
- Nothing above settles the open goals questions (goal types, ledger schema,
  review rhythms); it constrains the eval half so the goals half can be designed
  against real grading needs.

Library check: 1 of 10 candidates already in your library (0 finished).
