---
title: "Jev in SASE: an advisory decision layer, not an agent brain"
date: 2026-10-01
researcher: cdx
status: complete
---

# Jev in SASE: an advisory decision layer, not an agent brain

## Executive judgment

Integrating Jev is a good experiment, but only if SASE treats it as a low-privilege, probabilistic sensor. The best first use is asynchronous review of completed agent traces: Jev can flag likely permission breaches, missing deliverables, expectation gaps, and runs that merit human review. Its results should be recorded beside SASE's canonical evidence and may raise review priority, but must not change deterministic truth, suppress an existing alert, mark a failure `KNOWN`, authorize a tool, close a task, or trigger host-owned completion.

Jev is not a replacement for Codex, Claude, or another agent model. It does not generate prose or code, call tools, or run an agent loop; TypeSafe explicitly describes it as a model for typed decisions embedded in ordinary software. Its attractive properties are narrow outputs, probabilities, low advertised price, and low latency. Its liabilities are equally important: it is a new hosted dependency; it is literal and prompt-sensitive; its probabilities are not perfectly coherent; it is weak on derived correctness, code, math, dates, and adversarial inputs; and almost all workflow-level evidence currently comes from TypeSafe or collaborators rather than mature production deployments.

The right decision is therefore **yes to a time-boxed, disabled-by-default shadow pilot; no to putting Jev on SASE's control plane today**.

## What Jev actually is

TypeSafe launched Jev in early access on 2026-09-15 as its first “System One” model. An application sends an unstructured state plus one or more typed questions. The supported result shapes are:

- `Noul`: a probability for a proposition;
- `Choice`: a distribution over up to 255 caller-supplied labels;
- `Score`: a distribution over an ordered scale of at most ten levels.

The API returns typed JSON rather than generated prose. Jev 1.13 currently advertises a 64K request limit, a 32K state limit (plus the longest question), text-only input, 100K input tokens/second, 40 requests/second, and a price of $42 per billion input tokens ($0.042 per million); output is free. These are early-access operational terms, aliases such as `jev-latest` can move, and rate limits can change, so any calibrated deployment should pin an exact model version. [TypeSafe model documentation](https://docs.typesafe.ai/models) [TypeSafe API documentation](https://docs.typesafe.ai/api)

This distinction matters for SASE. Jev should not be added as another implementation of the existing agent-LLM provider contract. TypeSafe says directly that Jev is not a coding agent and cannot replace Claude Code or Codex. It is meant to sit inside a program that retains deterministic control flow and side effects. [TypeSafe: Jev is not a coding-agent model](https://docs.typesafe.ai/introduction/coding-agents) [TypeSafe integration guidance](https://docs.typesafe.ai/concepts/how-to-build-with-system-one)

## How strong is the evidence?

### Promising signals

The launch material reports 70–500 ms latency across published workflows and substantially lower token cost than frontier generative models. The most relevant vendor workflow is “Agent Trace Observability”: it judges instructions, conversation, tool calls, final response, and feedback, then predicts completion, satisfaction, health, permission problems, review priority, and whether an issue should be filed. This is close to a SASE post-run review workload. [TypeSafe launch post](https://typesafe.ai/blog/introducing-system-one-models-and-jev) [Agent Trace Observability workflow](https://evals.typesafe.ai/agent_trace_observability)

There is also useful independent evidence. The September 2026 paper *JEV-as-a-Judge: Accept When Confident, Escalate When Unsure* evaluated 5,172 text-readable judgments. It reports a median Jev latency of about 0.15 seconds and a per-1,000-judgment fee of $0.044. On its mixed benchmark pool, Jev's high-confidence subset was approximately as accurate as GPT-6, and a frozen confidence-threshold cascade matched or slightly exceeded GPT-6 aggregate accuracy while escalating 31.5% of cases. This supports a “cheap first judgment, escalate uncertainty” pattern. [Paper abstract](https://arxiv.org/abs/2609.26550) [Paper HTML](https://arxiv.org/html/2609.26550v3)

### Reasons not to overgeneralize

The evidence is young and task-dependent:

- The launch evaluations are vendor-authored. Their reference labels are often averages of frontier LLM judgments and assume that the workflow itself is correctly framed. The launch post also acknowledges that published latency was measured from West Coast laptops and that current pricing might be subsidized.
- The independent judge study is not yet peer reviewed. Its held-out pool was dominated by RewardBench, while the more difficult JudgeBench subset escalated 64.8% and still trailed GPT-6 slightly. Results were materially worse on math, code, and logic—exactly where a software-engineering product must be cautious.
- “No type errors” or “zero hallucinations” means the response conforms to a closed schema. It does not mean the selected label is true.
- TypeSafe documents jagged behavior: weakness at arithmetic, counting, date handling, indirect criteria, contradictory instructions, irrelevant long context, and adversarial content. Semantically equivalent or negated questions need not produce coherent complementary probabilities. [Jev 1.13 jaggedness guide](https://docs.typesafe.ai/model-jaggedness/jev-1.13)
- A separate probability-coherence study found Jev more coherent than several generative-model readouts, but still measured complementarity violations well above repeat noise and meaningful differences between equivalent Noul and Choice formulations. Jev probabilities should be calibrated empirical signals, not values that code algebraically combines as if they obeyed exact probability identities. [Beyond Calibration](https://arxiv.org/abs/2609.33209)

The practical lesson is to ask direct, atomic questions; avoid having the model calculate or infer facts SASE can compute; use one formulation consistently; and tune thresholds on SASE data rather than importing a published `0.9` cutoff.

## Fit with SASE's architecture and invariants

SASE already makes several decisions that sharply constrain a safe integration:

1. **Canonical truth is evidence-based.** Tool-run triage uses independent witnesses for `KNOWN`, preserves `UNKNOWN` when evidence is insufficient, and never changes the underlying command exit status. A Jev opinion cannot become a witness.
2. **Completion is host-owned.** Agents declare; host finalizers commit and perform completion work. Jev must not become another completion authority.
3. **Records precede admission policy.** SASE's design deliberately accumulates real observations before using a predictor for admission. A Jev deployment should follow the same order: record, backtest, shadow, calibrate, and only then consider a monotone policy.
4. **Shared domain behavior belongs in `sase_core`.** Python owns orchestration, plugins, network calls, and presentation. If judgment records or threshold policies later become shared SASE behavior, their normalized domain representation belongs in Rust; an initial experimental HTTP adapter does not.
5. **The existing fast prompt predictor is local by design.** It operates on the keystroke path with millisecond-scale expectations. A hosted 100–500 ms request is categorically unsuitable there.

These constraints are a strength. They make it possible to gain signal from Jev without giving an immature model authority it has not earned.

## Candidate applications

| Candidate | Expected value | Risk | Recommendation |
|---|---:|---:|---|
| Post-run trace review and review prioritization | High | Moderate | **Pilot first, in shadow mode** |
| Suggesting a skill before an agent turn | Medium/uncertain | Low if advisory | Evaluate later |
| Task-bead duplicate/type/priority suggestion | Medium | Moderate | Advisory shortlist only |
| Choosing model/effort or an escalation path | Potentially high | High | Only after a labeled corpus exists |
| Keystroke prompt prediction | Low | High latency/regression risk | Reject |
| `NEW`/`KNOWN`/`FLAKY` truth or command success | Superficially attractive | Critical correctness risk | Reject |
| Permission, safety, or irreversible-action gate | Superficially attractive | Critical security risk | Reject |
| Finalizer, commit, task-close, or auto-resolution authority | Superficially attractive | Critical governance risk | Reject |
| Code correctness or vulnerability adjudication | Low without execution evidence | Critical false-negative risk | Reject |

TypeSafe has a two-stage skill-suggestion cookbook: rank a large skill catalog, then rerank the top few with full skill text, while keeping the result advisory and the complete catalog available. Its reported improvement is interesting, but the experiment used 182 Hermes skills and synthetic requests generated from those skills. This SASE checkout currently ships only about nineteen built-in skill files, although installations can add others. The catalog size and request distribution are therefore different enough that the vendor result should not drive the first integration. [TypeSafe skill-suggestion cookbook](https://docs.typesafe.ai/cookbooks/skill_suggestion)

## Recommended first architecture

Build an optional `sase-jev` experiment as a disabled-by-default plugin or companion package. It should contribute an Axe-scheduled/oneshot review job through SASE's existing plugin configuration and job mechanisms. It should not implement the `sase_llm` provider contract and should not add Jev calls to an interactive critical path.

The data flow should be:

```text
completed SASE turn + settled finalizer facts
                 |
        deterministic extraction
                 |
       allowlist + secret redaction
                 |
          pinned Jev request
                 |
     append-only judgment observation
                 |
  shadow metrics; later, additive review alert
```

### Input envelope

Construct a compact, versioned state from canonical records:

- the user's requested outcome and explicit constraints;
- the final response;
- tool names, status/exit facts, and bounded result summaries;
- finalizer outcomes, verification receipts, and deterministic triage verdicts;
- changed-path classes and a diffstat, not raw repository contents;
- explicit user feedback when available.

Do not send raw command arguments, environment variables, secrets, entire source trees, or unbounded tool output by default. Long irrelevant state is both a privacy problem and a documented quality problem. If the plugin must consume data not exposed through a stable SASE API, add a narrow sanitized read adapter rather than scraping internal JSON files.

### Initial questions

Keep the question set small, direct, and stable. Examples are:

- Noul: “The trace shows an irreversible action outside the authority granted by the user.”
- Noul: “The recorded execution evidence supports completion of every requested deliverable.”
- Noul: “The final response is likely to leave a material user expectation unmet.”
- Noul: “A human should review this run before relying on its result.”
- Choice: one primary review category from `permission-risk`, `missing-deliverable`, `unverified-success`, `expectation-gap`, `other`, or `none`.
- Score: review urgency on a short, explicitly defined ordinal scale.

Jev does not provide a free-form rationale. That is useful discipline: any alert should point to the underlying trace facts and label the model output as a probabilistic suggestion, not manufacture an explanation. Do not calculate the complement of one question from another independently worded question, average “equivalent” prompts, or infer logical consistency between them.

### Observation record

Persist an append-only judgment record before any behavior consumes it. At minimum record:

- pinned provider/model identifier;
- question-set version and digest;
- a content hash and schema version for the sanitized input;
- returned probabilities/distributions;
- configured thresholds and resulting advisory action;
- latency, token count, retry count, and transport error;
- the deterministic facts available at judgment time;
- later human disposition or user feedback, without rewriting the original result.

An idempotency fingerprint should prevent duplicate judgments of the same trace/question/model tuple. API failure should fail open to today's SASE behavior: record the transport failure and do nothing else. Use a short timeout and documented backoff for `429`/`529`; do not retry authentication or validation failures. [TypeSafe API errors](https://docs.typesafe.ai/api)

### Authority boundary

During the pilot and any plausible first production phase, Jev may only add information or increase scrutiny. It may:

- annotate a completed run;
- raise a review priority;
- add a “please inspect” notification;
- nominate an uncertain case for a stronger LLM or a human.

It may not:

- suppress a deterministic notification or failure;
- change an exit code or evidence-based triage verdict;
- skip verification or reuse a receipt;
- approve a permission-sensitive or irreversible action;
- settle a goal, close a bead, create a commit, or run a finalizer;
- silently route away from an explicitly selected model or user instruction.

This monotone rule makes false positives inconvenient but prevents false negatives from hiding established evidence.

## Rollout and evaluation

### Phase 0: offline feasibility

Export a privacy-reviewed, stratified sample of historical completed turns. Have humans label the narrow propositions using a written rubric. Evaluate Jev without changing the product. Include mundane successes, incomplete work, explicit refusals, tool failures, permission-sensitive actions, long traces, adversarial repository text, and examples from each supported agent provider.

Compare at least:

- current deterministic behavior alone;
- Jev alone, for diagnostic understanding only;
- deterministic behavior plus Jev annotations;
- Jev followed by a strong generative judge or human when confidence is ambiguous.

### Phase 1: live shadow mode

Run on completed traces, store observations, and expose results only to experiment owners. Collect enough labels to produce reliability plots and confidence intervals by question and cohort. A few attractive examples are not evidence. A reasonable initial target is several hundred stratified judgments, with additional sampling near any proposed threshold.

Measure:

- false-negative rate for permission and material-completion issues;
- precision and recall for review-worthy runs;
- coverage at each confidence threshold;
- Brier score/calibration error and reliability curves;
- disagreement by provider, project, language, trace length, and model version;
- p50/p95 latency, token cost, rate-limit/error rate, and operational availability;
- drift after model or question changes.

The cost formula is attractive but not decisive: at the advertised rate, a 10K-token state costs about $0.00042, while a maximum 32K-token state costs about $0.001344. Engineering, review burden, data exposure, and cascaded-judge cost will dominate token price.

### Phase 2: additive advisory behavior

Only after prespecified acceptance criteria are met, enable a conservative notification that can add or elevate review. Pin the exact model version and question-set digest. Choose thresholds separately per proposition from SASE data, include uncertainty bounds, and retain a rollback switch. Ambiguous cases can cascade to a stronger judge or human; low-confidence output should not be treated as negative evidence.

### Phase 3: reconsider broader uses

Only after the observation corpus demonstrates durable value should SASE consider skill suggestions, task classification, or model/effort routing. At that point, introduce a provider-neutral decision abstraction only if a second provider or multiple proven workflows justify it. If the normalized record and policy become shared behavior, move those deterministic pieces into `sase_core`; keep TypeSafe transport, credentials, retries, and scheduling in the Python plugin.

## Privacy, security, legal, and operational concerns

The hosted API creates a new data boundary. TypeSafe says customer data is not used for model training, and its documentation lists enterprise zero-data-retention arrangements. The public legal terms nevertheless permit service telemetry and place responsibility for independent evaluation on the customer; the service is explicitly allowed to be inaccurate. Before private source, transcripts, or tool logs are sent, SASE needs an allowlisted schema, secret scanning/redaction, retention analysis, and—if this becomes more than a personal experiment—contract review. [TypeSafe legal overview](https://docs.typesafe.ai/legal) [Master Cloud Agreement](https://typesafe.ai/legal/mca) [Data Processing Addendum](https://typesafe.ai/legal/data-processing)

Treat all repository and tool-output text as potentially adversarial. Jev's documentation says state is generally treated as data, but not that it is robust to hostile prompt injection. The model must have no credentials or direct tool authority; it receives a sanitized snapshot and returns a bounded value. Deterministic code remains responsible for permission checks, arithmetic, date comparisons, status transitions, and side effects.

Use an explicit secret such as `TYPESAFE_API_KEY`, captured only for the disabled plugin/job through SASE's service environment allowlist. Never put the key in judgment records or notifications. The plugin also needs bounded concurrency, local rate limiting, observable retries, and a circuit breaker so a provider outage cannot delay finalization.

## General critique of the proposal

The idea is directionally good because SASE already produces structured traces, receipts, finalizer facts, and notifications. Jev's typed outputs fit an annotation layer better than free-form judge prose does, and its low marginal cost makes comprehensive shadow evaluation feasible. The model could help SASE spend expensive human or frontier-model attention on the ambiguous tail.

The largest conceptual trap is confusing a well-typed answer with a trustworthy decision. Jev removes output parsing and constrains labels; it does not remove model error. In fact, the lack of rationale can make a polished probability look more authoritative while offering less evidence for debugging. SASE should display provenance and the underlying deterministic facts, not an unlabeled percentage.

The second trap is premature platform work. A generic “decision provider” interface, core domain migration, UI surface, and automatic routing policy would be expensive before SASE has proved one useful judgment. Start with one narrow experiment and one append-only record. Generalize only after repeated value reveals the stable abstraction.

The third trap is selection bias. Judging only agent runs that already generated alerts, or labeling with the same frontier model used as a comparison, will inflate apparent performance. Sampling must include quiet successes and failures, human labels must follow a stable rubric, and safety-relevant false negatives need separate accounting.

The final trap is vendor coupling. Jev is weeks old, version aliases move, pricing and limits can change, and the legal/retention posture may not suit all SASE users. The existing product must remain fully functional with the plugin disabled or unavailable. Stored normalized observations and labels should make it possible to compare or replace the provider without replaying private raw data.

## Recommended solution

Implement a **six-to-eight-week, disabled-by-default `sase-jev` shadow pilot for post-run agent-trace review**. Use a pinned Jev version, a compact allowlisted state, four or five atomic questions, and an append-only observation record. Run it asynchronously only after canonical finalizer and verification facts settle. Collect several hundred stratified human labels and compare deterministic-only, Jev, and Jev-to-human/strong-judge cascades on calibration, safety false negatives, review yield, latency, cost, privacy, and drift.

If the pilot succeeds, ship only a monotone advisory feature: Jev may add or elevate a human-review notification, while deterministic SASE evidence always wins and provider failure changes nothing. Do not add Jev to `sase_llm`; do not use it for prompt completion, tool triage truth, permissions, code correctness, finalization, commits, or task closure. Defer a generic decision-provider abstraction and any `sase_core` domain work until at least one second proven use case makes the abstraction real rather than speculative.
