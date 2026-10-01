# Integrating Jev into SASE: decision layer, not a provider

- **Researcher:** grk (`research.y.grk`)
- **Date:** 2026-10-01
- **Question:** What is the best way to integrate Jev (TypeSafe AI's System One decision/judgement model) into SASE, and is the idea sound?
- **Independence:** This report does not consult peer swarm reports. Sources are TypeSafe's docs and launch materials, independent papers and explainers from September 2026, and the SASE tree as of this workspace.

## Recommended solution

Treat Jev as an **optional host-side decision backend**, never as an LLM provider, never as a mentor replacement, and never as an auto-approver of human gates.

Ship it in four stages, with a hard stop after stage 0 if SASE-labelled data does not support the vendor claims:

| Stage | What lands | Acts on live work? |
| --- | --- | --- |
| **0. Offline eval** | Labelled SASE traces (mentor skip-worthiness, LaunchApproval outcomes, bead duplicate vs new, skill/xprompt relevance). Measure accuracy, expected calibration error, and coverage at frozen thresholds. Compare against `@small` JSON classification. Pin `jev-1.13.0`. | No |
| **1. Shadow client** | A `DecisionClient` protocol in Python host code, TypeSafe backend behind an optional extra/`sase-typesafe` plugin, feature flag default **off**. Log `{state_hash, questions, answers, confidence, downstream_outcome}` next to the decision the host already made. | No |
| **2. First acting feature: mentor skip/run** | One `noul` ("does this stitch need a full mentor?") plus a `score` for review intensity. Skip the LLM mentor only when the noul is clearly low; otherwise run today's mentor. Fail **open** (Jev down → run mentor). User can still force `,C`. | Yes, reversible |
| **3. Advisory chips only** | LaunchApproval risk chip, skill/xprompt suggestion line, bead-duplicate score on `sase-new-task` candidates. Humans and agents still decide. | Informational |

Do **not** add `jev` to `sase_llm`, do **not** put this in `sase-core`, do **not** auto-settle `LaunchApproval` / `SudoRequest` / `PlanApproval` / `TaskTriage`, and do **not** cascade Jev into a cheap LLM-as-judge that scores the same rubric. Independent work shows those two judges err in the same places.

The idea is **good if scoped this way**, and **a category error if "integrate Jev" is read as "add another coding-agent provider."** TypeSafe says so themselves: Jev is not a drop-in for Claude Code, Codex, OpenCode, Muse, or Grok Build.

---

## 1. What Jev actually is

Jev is TypeSafe AI's first **System One** model, launched in early access on 2026-09-15 (sixteen days before this report). Founder Diogo Almeida is a former OpenAI researcher on the RLHF line. The product pitch is a function call, not a chat:

> unstructured state in, typed probabilistic decisions out.

### 1.1 Interface

One HTTP endpoint: `POST https://api.typesafe.ai/v1/systemone`. Request body is `{state, model, questions}`. `state` is a string, JSON object, or array of text (no image/audio/video). Every question is one of three primitives, evaluated in parallel against the same state:

| Primitive | Question | Returns | Limits |
| --- | --- | --- | --- |
| **Choice** | Which of these unordered options? | `choice`, per-option `probabilities`, `confidence` | ≤ 255 options |
| **Score** | Which level on this ordered rubric? | probability-weighted `score`, `legend`, `probabilities`, `confidence` | 2–10 levels |
| **Noul** | Is this statement true? (Bernoulli) | `noul` in `[0, 1]` | no separate `confidence` field |

Question ids are for the caller's code; they are not sent to the model. Instructions and criteria are the actual classifier. Several questions in one request barely change latency, because the state is read once.

Python SDK: `pip install typesafe-sdk` / `uv add typesafe-sdk`. `TypeSafeClient` / `AsyncTypeSafeClient` read `TYPESAFE_API_KEY` and default to `jev-latest`. OpenRouter is a documented alternative base URL (`~typesafe/jev-latest`).

### 1.2 Published operating numbers (vendor, unless noted)

| Property | Value | Source |
| --- | --- | --- |
| Current version | `jev-1.13.0`; aliases `jev-latest` / `jev-preview` both point here | [Models](https://docs.typesafe.ai/models) |
| Price | **$0.042 / million input tokens; output free** | same |
| Rate limits | 100K tokens/s, 40 rps (changing without notice while demand is high) | same |
| Context | 64k per request; **32k for state + the longest single question** | same |
| Latency | TypeSafe: 70–500 ms. Independent: ~0.15 s median (Li et al.), 141 ms (Arize), 0.44–0.48 s median (Jevals) | mixed |
| Input | English-primary text; other languages including CJK accepted at lower accuracy | Models |
| Training on customer data | TypeSafe says no. ZDR is an enterprise extra | [Legal](https://docs.typesafe.ai/legal) |
| Fine-tuning / LoRA | Not offered. Shape answers via `state` + `instructions`/`criteria` | Models |

TypeSafe's own four-workflow eval (reference = average of GPT-6 Astra and Fable 5.1) is the source of the "444× cheaper / ~200× faster" homepage numbers. Third-party writeups put Jev near GPT-5.6 Terra on those workflows (~67.8% vs 67.9%) and behind Opus 5 / GPT-5.6 Sol, with a larger gap on invoice processing (61.8% vs Sol 79.1%). Treat the Pareto-frontier charts as **vendor evals designed around System One tasks**, not as a general-intelligence ranking.

### 1.3 How a decision model works (independent reconstruction)

Victor Dibia's 2026-09-24 explainer is the clearest public reconstruction. TypeSafe has not disclosed Jev's internals. The API and the open reproductions fit this procedure:

1. Write the decision as a sentence to complete.
2. **Score** every option as a completion (read token log-probs; generate nothing).
3. Normalise into a probability distribution.

On Qwen2.5 7B, scoring was 7–54× faster than generating probabilities and at least as accurate as generating a label. The lead over generating one label shrinks as the option count grows and reverses at 77 options unless each option is a one-token code. Instruct models were overconfident (ECE 0.10 on the 7B); base models were closer to calibrated; temperature scaling on labelled task data brought ECE to 0.03. A 0.5B model trained ~40 minutes on shuffled option letters jumped from 7% to 67% on unseen Banking77 intents.

Implication for SASE: **the accuracy you get is the accuracy of the questions you write, plus a calibration you must measure on SASE data.** Vendor ECE on prompt-injection (0.0588 on 662 messages, Gaurav-Gosain/jev-sec-bench) does not transfer.

### 1.4 What Jev cannot do (TypeSafe's own jaggedness list, `jev-1.13`, reviewed 2026-09-17)

- Generate text, code, explanations, or streaming replies. Chaining choices to fake generation is slow and bad.
- Count, do arithmetic, interpolate a Score into an exact magnitude, or compare dates as ordered quantities. Keep that in code.
- Follow indirection, double negatives, or "a property of a property."
- Stay accurate as `state` fills with irrelevant detail (context rot). Filter first.
- Treat adversarial / prompt-injection content as hostile by default.
- Honour structural identities: `P(noul)` and `1 − P(not noul)` need not sum to 1; a Noul and a yes/no Choice on the same proposition need not agree.
- See images, audio, or video.

TypeSafe's coding-agent page is explicit: **there is no `model: "jev-latest"` that turns a coding agent into a Jev-powered agent.**

---

## 2. Independent evidence on Jev-as-a-judge

Two September 2026 papers, plus an Arize blog, bound what SASE should expect.

### 2.1 Li, Miao, Krishnan, Padman (arXiv:2609.26550v3, 2026-09-29)

*JEV-as-a-Judge: Accept When Confident, Escalate When Unsure.*

- Against sixteen generative and reward-model judges, with blinded human adjudication, Jev is **within ~3 points of GPT-6 where the verdict can be read off the text**, at **0.36% of GPT-6's fee** and **0.15 s median latency**.
- It **falls behind where the verdict must be derived** (math, code, logic). On JudgeBench-style derivation it trails by a large margin (press coverage: 14.6 points).
- **Confidence marks that boundary.** A threshold frozen in advance, accept-when-confident / escalate-the-rest, was **0.9 points more accurate than GPT-6** on 1,610 held-out pairs at 41% of its fee. A pre-specified live test on two new workloads matched GPT-6 exactly.
- Confidence routing **weakens on style-adversarial pairs and reference-free prose.**

This is the paper that justifies a **cascade into a reasoning coding agent**, not into another classifier.

### 2.2 Rao and Callison-Burch (arXiv:2609.29769v2, 2026-09-28)

*JEV vs. LLMs as Rubric Judges: Cheaper, Faster, and Wrong in the Same Places.*

- Three flash-tier LLM judges vs Jev, identical criterion texts, nine panels from seven human-labelled benchmarks.
- LLM judges cost **16–325×** as much and take **28–350×** as long. Jev's accuracy differs significantly in at most 8 of 27 paired comparisons: **ahead on binary checklist criteria, behind only on ordinal ones.**
- On ordinal criteria, **Jev and the LLM judges depart from humans together**, agree with each other more than with the labels, and mostly assign lower levels.
- On Jev's most confident errors, **~96% of LLM verdicts repeat the same wrong answer** (independent errors would give ~50%).
- Cascades of Jev → flash LLM judge **mostly save money; they add little accuracy.** Even with oracle thresholds, none beat the best single judge by more than 2.7 points.

This is the paper that **kills "Jev pre-scores, cheap mentor confirms"** as an accuracy strategy. Complementary errors are required for a cascade to help. Flash-tier rubric judges do not provide them.

### 2.3 Arize (Laurie Voss, 2026-09-23)

On RAGTruth hallucination detection, **threshold tuning is the whole game.** At a naive 0.5 cutoff Jev lost to Opus 5 (76% vs 83%). After tuning (Jev cutoff 0.80, Opus 0.65) both hit 87%. Jev ran at ~$0.05 / 1,000 judgements vs $14.30 for Opus, ~141 ms vs >3 s. GPT-5.6 Terra needed a 0.95 cutoff and still only reached 80%.

Implication: **every SASE call site needs its own labelled set and its own frozen threshold.** Shipping 0.5 as a default will look like "Jev doesn't work."

### 2.4 The failure mode that survives "no hallucination"

Prefactor (Matt Doughty, 2026-09-22) puts the safety point cleanly: Jev cannot hallucinate a string, so it cannot invent a citation or a product id. It **can** return a wrong classification at 0.94 confidence, and software that treats typed output as ground truth will act. TypeSafe's "can't hallucinate" marketing is schema-safety, not decision-safety. SASE already distinguishes those: a mentor that emits invalid JSON is `FAILED`; a mentor that emits well-typed wrong comments is `COMMENTED`. Jev only eliminates the first class.

Victorino Group / Archestra (2026-09-25) is a useful floor: on 337 tool-call labels where three LLM judges agreed, Jev scored 93% and a constant "benign" scored 79%. Leaderboard numbers below the majority baseline are worse than doing nothing.

---

## 3. SASE's actual decision surfaces

SASE already splits **generation** (LLM providers) from **control flow** (Python host + Rust core). Jev is neither. Mapping call sites is the whole design problem.

### 3.1 Surfaces that look like Jev and are not

| Surface | What it is today | Jev as a replacement? |
| --- | --- | --- |
| **`sase_llm` providers** (Claude, Codex, OpenCode, Qwen, Muse, Grok, Antigravity, fakey) | Thin CLI wrappers. `LLMProvider.invoke(prompt) -> InvokeResult(content, usage)`. Streaming, tools, file edits, session transcripts. | **No.** Category error. TypeSafe documents this. |
| **Size aliases / pools / fallbacks** (`@xsmall`…`@xlarge`, `\|` round-robin, `\|\|` fallback, usage-limit auto-disable) | Deterministic routing from config, availability, and advisory flags. | Weak. A Choice among providers is legal, but a wrong route wastes a full agent turn — far more than Jev's fee. Today's config already encodes preference. Latency of 150–500 ms on every launch is real. |
| **Mentors** | Background **LLM agents** on Patch stitches. `#mentor` xprompt → structured JSON comments (`focus_name`, `file_path`, `line_number`, `description`, `severity`). `FAILED` on invalid JSON. | **Cannot write `description`.** Can only skip/run or score a closed rubric. |
| **Human gates** (`LaunchApproval`, `PlanApproval`, `EpicApproval`, `SudoRequest`, `TaskTriage`, `CustomGate`, `HITL`) | Durable, command-backed, hash-verified user decisions. SASE's safety model. | **Must not auto-settle.** May attach an informational score. |
| **Finalizers** (`bead_action` keep/close, commit vs defer) | Rule-based host policy. | **No.** Policy belongs in code. |
| **Tool-run triage** (`NEW` / `KNOWN` / `FLAKY` / `UNKNOWN`) | Deterministic signatures, witnesses, flake baseline. | Optional classifier on the *message*, never a replacement for witnesses. Missing evidence stays `UNKNOWN`. |
| **Rust core** | Deterministic, offline, pin-ratcheted. | **No network, no vendor, no probabilities.** |

### 3.2 Surfaces where Jev is a natural fit

These share four properties: the answer set is known in advance, the decision is frequent, one look at a filtered state is enough, and today's alternative is either a heuristic, a human, or a full agent turn.

**A. Mentor skip/run (highest ROI).** Mentors consume **runner slots** (`max_running_agents`), wait on hooks, take minutes, and die as `FAILED` when JSON does not parse. Many stitches are trivial. A noul "does this diff need a human-quality review given these focus areas?" is a System One question. Skip is reversible (`,C` still runs a profile). Fail open.

Do **not** use Jev to invent comments. Do **not** use Jev to predict what a flash mentor would say (Rao: same errors). If a stitch clears the skip bar, run the existing reasoning mentor.

A second, cheaper mentor use: after a mentor returns comments, a **binary checklist** (one noul per focus: "is this comment a real defect vs nit?") can rank the Mentor Review modal. Binary checklist is where Rao found Jev *ahead* of flash judges. Ordinal `error|warning|suggestion` is where it lagged.

**B. Skill / xprompt / memory-strand suggestion (lowest risk).** TypeSafe's skill-suggestion cookbook is almost a SASE diagram. Two requests: Choice over the roster plus nouls for "does this turn need a skill at all?", then a shortlist rerank with full `SKILL.md` excerpts. On Hermes (182 skills, Haiku 4.5) they cut wrong loads 16.8% → 7.3% and needless loads 9.8% → 4.0%. SASE's roster is smaller and several skills are mandatory (`sase_final`, `sase_memory_read`, …), so the absolute win is smaller — but the blast radius is "one extra line the agent may ignore," which is the right first production experiment if mentor skip is too hot.

**C. LaunchApproval risk chip (informational).** Agent-initiated `sase launch request` already pauses for a human. Jev can score `{out_of_scope, destructive, duplicate_of_running_work, fine}` as a Choice plus a noul "would a careful owner approve this without reading the prompt?" Paint the chip on the modal. Never bind `approve` to it. High-stakes, high-confidence still goes to the human; that is TypeSafe's own confidence-routing example.

**D. Bead duplicate scoring for `/sase_new_task`.** The skill already does regex search plus a one-week sweep, then asks the agent to judge semantic duplicate vs related vs new. That judgement is a Choice over a shortlist of existing titles+descriptions. Host-side scoring would make corroboration (`sase bead +1`) cheaper and cut duplicate filing. Keep the agent in the loop for the first season.

**E. Notification / attention ranking.** The inbox already has typed panels. A Score for "needs a human this hour" plus a noul for "safe to snooze" could order the Attention panel. Wrong snooze is user-visible and recoverable. Good shadow-mode candidate.

**F. Guardrails on inbound prompts and outbound replies.** TypeSafe's guardrails cookbook is a battery of nouls (jailbreak, harm, …) plus a harm Score, with thresholds in code. SASE already has provider-native refusals and host rules (no exploits, no minor sexual content, sudo gates). A Jev battery is extra defence in depth, not a replacement for those rules, and adversarial jaggedness means it will miss crafted injections. Useful as a *log* and a *review* path; dangerous as the only block.

### 3.3 Surfaces that look tempting and are a poor fit

- **Code-correctness judging.** Li: Jev trails where the verdict must be derived. Mentors looking for logic bugs, races, and missing tests are derivation. Keep the reasoning LLM.
- **Counting test failures, dates, token math, coverage deltas.** Jaggedness items 2–3. Code already does this.
- **Commit-message / bead-close policy.** Host rules exist. A noul "is this bead done?" will be over-eager.
- **Auto-mute of error notifications.** Fail-closed needed; Jev is the wrong default.
- **Replacing `#research` / plan writing / chat replies.** Generation.

---

## 4. Critique of "integrate Jev into SASE" as a plan

The plan as stated is **underspecified**. That is the main risk. Four readings, ranked:

### 4.1 Add Jev as an `sase_llm` provider — bad idea

`LLMProvider` is a subprocess that consumes a preprocessed prompt and returns generated text. Jev has no prompt loop, no tools, no streaming, no `AGENTS.md`, no commit finalizer, no session. Wiring it here would force a fake chat adapter (TypeSafe even publishes a "System One LLM wrapper" for the reverse direction: making *LLMs* look like Jev). SASE would then try to run mentors, landers, and `sase final` on a model that cannot write a commit message. **Reject.**

### 4.2 Drop Jev into every host `if` that currently feels fuzzy — also bad

Jev is a 16-day-old early-access API with dynamically adjusting rate limits, one version (`jev-1.13.0`), no customer fine-tunes, English-primary accuracy, 32k state budget, and known weakness on adversarial input. SASE sends diffs, prompts, and bead text that can include secrets and private beads. Putting it on the control path of LaunchApproval or sudo is the Prefactor failure mode: typed, confident, wrong, acted on.

TypeSafe's own advice is: atomic questions, compose in **your** code, threshold on **your** labelled data, pin the version if thresholds matter. That is a season of work per call site, not a flag flip.

### 4.3 Optional decision backend, shadow then one reversible acting feature — good idea

This matches SASE's architecture:

- Host owns control flow (already true).
- Typed artifacts over parsed prose (already true: gates, mentor JSON, ToolRuns, finalizer manifests).
- Optional vendor integrations live outside core (`sase-github`, `sase-telegram`, `sase-nvim`).
- Feature flags already exist as a first-class task type.
- Runner slots are scarce, so skipping an LLM mentor is real money **and** real capacity.
- Mentors already fail on invalid JSON; Jev cannot fail that way for skip/run.

It also matches the only independent result that has held up in two papers: **Jev is a cheap, fast stand-in for flash-tier judges on binary, readable-from-text questions, and a poor stand-in for reasoning judges on code/math.** SASE has both kinds of question. Use Jev for the first. Keep Claude/Grok/Codex for the second.

Caveats that remain even in this reading:

1. **Vendor concentration.** No open weights from TypeSafe. Open clones appeared within two days (Dibia cites djev and others) but they are not Jev. The `DecisionClient` protocol must not leak `typesafe_sdk` types.
2. **Calibration is per-task.** Arize's 0.5 vs 0.80 gap is a warning. Shadow mode is not optional.
3. **Complementary-error problem.** Rao: cascading Jev into a flash mentor that scores the same rubric is a cost trick, not a quality trick. Escalate to a *reasoning* agent, or to a human, or do not escalate.
4. **Privacy.** Filter state. Redact secrets. Never send `local only` goals or private bead attachments. Prefer truncated diffs and structured fields over whole transcripts. 32k is smaller than a p90 session Reply.
5. **Literal instructions.** Jev answers the question you wrote. Mentor focus areas written as persona flavour ("Python style expert") will underperform a literal checklist.
6. **Product immaturity.** Rate limits "adjusting dynamically." Pin `jev-1.13.0`. Retune on every version bump. `jev-latest` is for the playground.

### 4.4 Wait a quarter — also a defensible idea

A 16-day-old model, one version, vendor evals, two independent papers that already disagree on how much cascades help. SASE's control plane is not the place to be an early-access design partner unless stage 0 pays for itself on SASE labels. If stage 0 loses to `@small` JSON classification on mentor skip, **stop**. The interface work (protocol, logging, redaction) is still worth keeping for the next decision model.

---

## 5. Implementation options compared

| Option | Effort | Blast radius | Reversibility | Verdict |
| --- | --- | --- | --- | --- |
| **A. `sase_llm` provider** | Medium (looks easy, is a trap) | Every launch | High once shipped (agents will `%model:jev`) | Reject |
| **B. Hardcode `typesafe_sdk` in core** | Low | Dependency + network in the default install | Medium | Reject. Core stays vendor-free. |
| **C. New `sase_decision` plugin group on day one** | High (12th group, doctor, catalog, docs) | Ecosystem | High | Premature. Extract later if a second backend appears. |
| **D. Protocol in host + optional extra/plugin + flag** | Medium | Only flag-on machines | High | **Do this.** |
| **E. Agent skill only** (install TypeSafe's `typesafe-ai` skill so SASE agents write Jev calls into *other* apps) | Trivial | None to SASE | Total | Fine as a side quest, does not "integrate Jev into SASE." |
| **F. Local open clone** (letter-scoring Qwen, djev, …) | High (serve, calibrate, GPU) | Ops | High | Later, as a `DecisionClient` backend, if TypeSafe pricing/limits/privacy bite. |

### 5.1 Recommended shape for option D

Keep the vendor SDK off the default wheel. Mirror `sase-telegram`: an optional package that the host calls through a tiny protocol.

```text
src/sase/decision/
  types.py       # Question (choice|score|noul), Answer, Usage
  protocol.py    # DecisionClient.evaluate(state, questions) -> Result
  config.py      # decision.enabled, backend, model, fail_mode, log
  redact.py      # secret scan + size cap before any backend sees state
  backends/
    noop.py      # default: raises DecisionDisabled
    recording.py # wraps another backend, writes JSONL audit
```

Optional extra (name bikeshed: `sase-typesafe` or `sase[decision]`):

- implements `DecisionClient` with `typesafe_sdk.AsyncTypeSafeClient`
- reads `TYPESAFE_API_KEY` / `decision.api_key_env`
- pins `model: jev-1.13.0` in shipped config (not `jev-latest`)
- retries 429/529 with the SDK policy
- never logs raw `state` at info; log hashes and question ids

Call-site contract, copied from TypeSafe and tightened for SASE:

1. **Atomic questions.** One judgement per question. Compose in Python.
2. **Filter state.** Send the diff hunks, focus-area list, and stitch note — not the session transcript.
3. **Frozen thresholds** per call site, stored next to the questions, versioned with the model id.
4. **Fail mode by stakes.** Skip/run and ranking: fail **open**. Anything that could settle a gate: fail **to human**. Never fail closed into "approve."
5. **Shadow first.** Acting code paths read a `decision.acting.<site>` flag that stays off until the shadow log's ECE and coverage clear a written bar.
6. **Audit.** Every acting decision is a span: question set version, model id, answers, threshold, action taken, later human override if any. This is how you notice Prefactor's "confidently wrong" class.

Do not add a 12th plugin group until a second backend (local clone, OpenRouter-only, or another System One vendor) is real.

### 5.2 First acting feature, specified

**Mentor skip/run**, because it buys runner slots and is reversible.

State (filtered):

```json
{
  "patch": "<name>",
  "stitch": "<id>",
  "files": [{"path": "...", "status": "M", "diff": "<truncated>"}],
  "profile": "python_review",
  "focus_areas": [{"name": "style", "description": "PEP 8 ..."}]
}
```

Questions (one request):

- `needs_review`: noul, "Does this stitch contain a defect, a safety issue, or a design problem that a careful reviewer would comment on, given `focus_areas`? Cosmetic nits and formatter noise are no."
- `intensity`: score, levels `skip` / `light` / `full`.
- plus one noul per focus area if the profile is small.

Policy (illustrative; freeze from stage 0, do not ship these numbers):

- skip only if `needs_review` < θ_low **and** `intensity` mass on `skip` is high
- otherwise run the existing mentor
- Jev error / timeout / 429 after retries → run the mentor
- user `,C` always available

Out of scope for v1: generating comments, changing severities, killing a running mentor because Jev later disagrees.

### 5.3 Eval harness (stage 0 is the real project)

Without this, the rest is theatre.

Label ~200–500 historical examples per site:

| Site | Positive | Negative | Existing SASE signal |
| --- | --- | --- | --- |
| Mentor skip | Human accepted ≥1 mentor comment on that stitch | Mentor `PASSED`, or all comments rejected in `,C` | `~/.sase/mentors/`, Patch `MENTORS` |
| LaunchApproval | Human rejected / edited | Human approved as-is | interaction_requests/launch |
| Bead duplicate | Reporter `+1`'d | Reporter created a new task after search | bead store |
| Skill suggestion | Agent loaded skill X and the turn succeeded | Loaded nothing, or loaded Y and was corrected | agent transcripts (noisier) |

Report, per site: accuracy, ECE, fraction above the acting threshold, confusion vs `@small` JSON, and the constant-baseline (Archestra's 79% lesson). If Jev cannot beat the constant and cannot beat `@small` on **coverage at a high-precision skip threshold**, do not turn acting on.

Retune on every `jev-*` version bump. The response's `model` field is the join key.

---

## 6. Cost and capacity sketch

Numbers are order-of-magnitude, for one machine.

A mentor that launches `@medium` for three minutes is dollars-to-tens-of-dollars and **one runner slot**. A Jev skip call on a 4k-token filtered diff is `4000 / 1e6 * 0.042 ≈ $0.00017` and ~0.2 s, no slot. Skipping 30% of mentor launches is the entire economic case. The Li cascade (accept 59% of verdicts, escalate the rest to a reasoning judge) is the same shape: most of the quality of the expensive judge at ~41% of its fee, **if** the question is "read this text" rather than "derive this proof."

Wrong skips are the residual cost: a missed security comment. That is why θ_low must be high-precision, why fail-open exists, and why `,C` stays.

Adding 200 ms to every `sase run` to pick `@small` vs `@large` is a much weaker case. Size aliases already exist; a misroute costs a whole turn.

---

## 7. Alternatives to Jev itself

If the goal is "cheaper structured judgements in the host," Jev is the current commercial point on that curve, not the only one.

- **`@small` JSON classification** with a strict schema. SASE already pays for those providers. Slower, parse-fragile (mentors already `FAILED` here), usually overconfident (Dibia: instruct models). Fair baseline in stage 0.
- **Letter-scoring a local 7B** (Dibia; Together's "train your own Jev" tutorial). More ops, full data control, good enough up to ~25 options on a 7B instruct. A later `DecisionClient` backend.
- **Deterministic heuristics** SASE already has (globs, diff regexes, failure signatures, `+1` bars). Keep them as the first filter; Jev sees only what they pass.
- **Wait for System One competitors.** Clones appeared in two days. Do not couple call sites to TypeSafe's SDK.

---

## 8. Recommended solution (full)

**Yes, integrate Jev — as a decision layer, on a leash.**

1. **Reject** the provider reading. TypeSafe, the `LLMProvider` ABC, and Jev's jaggedness list all agree.
2. **Do not** auto-settle any human gate. Attach scores; keep the durable command-backed path.
3. **Do not** replace mentors' generated comments. Use Jev to **skip or run** them, and optionally to **rank binary checklist** comments after the fact.
4. **Do not** cascade Jev into a flash LLM that scores the same rubric (Rao). Escalate to a reasoning agent or a human, or accept the skip.
5. **Implement** a host `DecisionClient` protocol, optional TypeSafe backend, default-off flag, redaction, pinned `jev-1.13.0`, JSONL audit.
6. **Prove it on SASE labels** (stage 0) before any acting path. If it loses to `@small` or to a constant at the high-precision operating point, stop.
7. **Act first** on mentor skip/run (reversible, slot-saving). Then advisory chips: LaunchApproval risk, skill/xprompt suggestion, bead-duplicate score.
8. **Keep questions, thresholds, and model id in one file per call site** so a human can review them without spelunking (TypeSafe's own agent-skill advice).
9. **Leave Rust core, finalizers, sudo, and ToolRun witnesses alone.**

If only one sentence survives synthesis: **Jev is a calibrated `if` for SASE's host, not a new agent, and it earns that `if` only after SASE-specific calibration.**

---

## Sources

### Primary (TypeSafe)

- [Introduction](https://docs.typesafe.ai/introduction.md)
- [Jev with coding agents](https://docs.typesafe.ai/introduction/coding-agents.md)
- [System One](https://docs.typesafe.ai/concepts/system-one.md)
- [Primitives](https://docs.typesafe.ai/primitives.md)
- [API reference](https://docs.typesafe.ai/api.md)
- [Models](https://docs.typesafe.ai/models.md) (`jev-1.13.0`, $0.042/MTok, 64k/32k, 40 rps)
- [Confidence](https://docs.typesafe.ai/confidence.md)
- [Confidence-gated routing](https://docs.typesafe.ai/patterns/confidence-routing.md)
- [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md) (reviewed 2026-09-17)
- [Skill suggestion cookbook](https://docs.typesafe.ai/cookbooks/skill_suggestion.md)
- [LLM guardrails cookbook](https://docs.typesafe.ai/cookbooks/llm_guardrails.md)
- [Agent skill](https://docs.typesafe.ai/agent-skill.md)
- [Legal](https://docs.typesafe.ai/legal.md) (no training on customer data; ZDR enterprise)
- Diogo Almeida, [Introducing System One Models & Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev) (2026-09-15)

### Independent

- Victor Dibia, [How Jev works: calibrated decision models](https://victordibia.com/explainers/jev/) (2026-09-24)
- Yubo Li et al., [JEV-as-a-Judge](https://arxiv.org/abs/2609.26550) (arXiv:2609.26550v3, 2026-09-29)
- Delip Rao & Chris Callison-Burch, [JEV vs. LLMs as Rubric Judges](https://arxiv.org/abs/2609.29769) (arXiv:2609.29769v2, 2026-09-28)
- Laurie Voss / Arize, [Jev vs LLM-as-a-Judge](https://arize.com/blog/jev-as-a-judge/) (2026-09-23)
- Matt Doughty / Prefactor, [Why a model that cannot hallucinate can still fail](https://prefactor.tech/blog/jev-system-one-model-what-it-means-for-agent-evaluation) (2026-09-22)
- Ben Lutkevich / TechTarget, [Jev decision model touted as quicker, cheaper LLM alternative](https://www.techtarget.com/it-infrastructure/news/366650696/Jev-decision-model-touted-as-quicker-cheaper-LLM-alternative) (2026-09-22)
- Thiago Victorino, [Jev scored 93%. A constant scored 79%](https://victorinollc.com/thinking/decision-model-on-the-control-path) (2026-09-25)

### SASE (this tree)

- `docs/llms.md`, `docs/agent_providers.md` — provider contract
- `docs/mentors.md` — LLM mentors, JSON comments, `FAILED` on invalid JSON
- `docs/architecture.md` — host vs Rust vs providers; LaunchApproval
- `docs/notifications.md`, `docs/plugins.md`, `docs/tool.md` — gates, plugins, ToolRun triage
- `src/sase/llm_provider/base.py` — `invoke(prompt) -> text`
- `/sase_gate`, `/sase_run`, `/sase_new_task` skills — human gates and duplicate policy
