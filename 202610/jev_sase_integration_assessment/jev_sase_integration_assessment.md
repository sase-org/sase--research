# Jev in SASE: consolidated assessment, critique, and recommendation

_Lead researcher synthesis · 2026-10-01 · Merges five independent reports (`__cdx`, `__cld`,
`__grk`, `__mus`, `__gem`) with the lead's own fact-checking of vendor claims and
measurements of local SASE state on `apollo`._

## Bottom line

- **Do not put Jev into SASE itself yet.** Jev is a 16-day-old, early-access, hosted
  classifier ([what Jev is](#what-jev-is)). Its advantages are latency (~70–500 ms) and
  price ($0.042 per million input tokens). SASE's judgment-shaped decisions are few (tens
  to hundreds a day), usually high-stakes, and mostly need reasoning. Jev's comparative
  advantage, high-volume low-stakes classification, barely overlaps that workload. The one
  high-volume stream, about 8,100 agent tool calls a day, is the worst possible fit.
- **All five researchers agree on four rejections:**
  - Jev must not be a `sase_llm` provider. That is a
    [category error](#jev-is-not-a-provider-and-does-not-replace-anything), and TypeSafe
    says so itself.
  - Jev must never live in `sase-core`.
  - Jev must never settle a gate, mint a KNOWN or FLAKY verdict, change an exit code,
    satisfy a finalizer, or close a bead.
  - Every use must be default-off, fail-open, version-pinned, and shadowed before it
    acts.
- **The researchers disagreed on the first use case.** Their five picks were post-run
  trace review, task-triage queue scoring, mentor skip/run, stranded-wait detection, and
  model-tier routing. [Local measurement](#where-the-researchers-disagreed) eliminates
  three of them on this machine:
  - The wait guards logged **zero** firings across ~1,770 retained agent runs.
  - **No mentor profiles are configured**, and no mentor run has ever been recorded.
  - Model routing has **no outcome-quality corpus**.
- **[Recommended](#recommended-solution):** a cheap (<$0.10 of tokens), pre-registered,
  **out-of-tree [offline evaluation](#pre-registered-offline-evaluation)** on the one
  labeled corpus SASE already has, the closed task beads.
  - Run it with [corrected labels](#the-task-bead-corpus-is-noisier-than-it-looks) and
    against a small-LLM baseline.
  - If it passes, ship an **out-of-tree, advisory-only `sase-jev` routine**. It writes
    scores to a sidecar record, never to bead notes
    ([why](#where-advice-is-delivered-matters-more-than-the-score)), and it decides
    nothing.
  - Build a vendor-neutral `sase decide` seam in the core only when a second consumer
    with its own labeled corpus appears.
  - If the evaluation fails, stop. Keep the finding that SASE lacks a cheap typed
    judgment primitive, which is a real gap whatever vendor fills it.

![Jev × SASE infographic: the narrow fit between Jev's strengths and SASE's workload, local evidence for each candidate first use, the task-bead label cleanup and sidecar score delivery, and the recommended path from offline test to advisory pilot to later vendor-neutral generalization](jev_sase_integration_assessment_infographic.png)

## What Jev is

The lead fact-checked the reports' claims against TypeSafe's docs, the papers, and
third-party write-ups. Corrections to individual reports are collected in
[Errata in the individual reports](#errata-in-the-individual-reports).

| Property | Verified value |
| --- | --- |
| Vendor / release | TypeSafe AI. Launched 2026-09-15 as limited, waitlisted early access. Proprietary, with no open weights and no self-hosting. |
| Interface | `POST https://api.typesafe.ai/v1/systemone` with `{model, state, questions}`. Several questions are answered against one state in one call. |
| Primitives | **Choice**: up to 255 caller-supplied options; returns `choice`, per-option `probabilities` and `confidence`. **Score**: 2–10 ordered levels; returns a probability-weighted `score`, `legend`, `probabilities` and `confidence`. **Noul**: a single P(true), with no confidence field. Question keys are not sent to the model; all meaning goes in `instructions` and `criteria`. |
| Model | `jev-1.13.0`. The aliases `jev-latest` and `jev-preview` both point to it today. **Pin the exact version**, because thresholds drift when an alias moves. |
| Limits | 64K tokens per request; 32K for state plus the longest question. Text only, English first. |
| Rate limits | **Currently 100K tok/s and 40 req/s**, "adjusting dynamically". The 250K tok/s and 1,200 req/min figure cited elsewhere came from an earlier version of the same page, read 2026-09-18. |
| Price | $0.042 per million input tokens; output is free. The launch post concedes pricing may be subsidized. |
| Latency | Vendor figure 70–500 ms. Independent medians: ~0.15 s (Li et al.), ~141 ms (Arize), 0.44–0.48 s (Jevals). |
| SDK / auth | `typesafe-sdk` (`TypeSafeClient`, `AsyncTypeSafeClient`), configured through **`TYPESAFE_API_KEY`**. JS/TS SDK, a Pydantic AI `TypeSafeModel`, and roughly 25 unofficial Rust crates. |
| Distribution | Direct API; OpenRouter beta (`typesafe/jev-1.13`, `jev-latest`, `jev-router`); Vercel AI Gateway (`typesafe-ai/jev`). |
| Data | No training on customer data. **Zero data retention is available only to enterprise customers.** Standard accounts have no fixed retention period. |
| Architecture | TypeSafe says only "a new model architecture, parallel sampler" trained with "Reinforcement Learning for Calibrated Decisions (RLCD)", and that it "outputs all probabilities in parallel". No paper has been published. It claims answers are "more consistent", not deterministic. |
| Access here | No `TYPESAFE_API_KEY` exists in this environment, so access must be obtained before anything can run. |

TypeSafe's own coding-agents page says Jev is not a drop-in replacement for the model
behind Claude Code, opencode, Muse Spark, Grok, or similar tools. It is a "System One"
model: a calibrated `if` that ordinary code branches on, not an agent.

## How strong is the evidence

### Converging independent findings

1. **Parity with flash-tier judges on readable-from-text questions; behind on derived
   ones.**
   - Li et al. (arXiv 2609.26550): Jev is within ~3 points of GPT-6 where the verdict can
     be read off the text, at 0.36% of the fee.
   - It trails by 7–28 points on JudgeBench code, math, logic and expert knowledge.
   - A confidence-gated cascade frozen in advance (accept when confident, escalate the
     rest) scored 93.4% against GPT-6's 92.5%. It escalated 31.5% of decisions and cost
     41% of GPT-6's fee.
2. **Errors are correlated with cheap LLM judges** (Rao & Callison-Burch, arXiv
   2609.29769).
   - Jev is ahead on **binary checklist** criteria and behind on **ordinal** ones.
   - On Jev's most confident errors, ~96% of flash-LLM verdicts repeat the same wrong
     answer.
   - Jev → flash-LLM cascades save money but add ≤2.7 points even with oracle
     thresholds.
   - **Escalate to a reasoning model or a human, never to a cheap judge on the same
     rubric.** This reconciles cdx (pro-cascade) and grk (anti-cascade).
3. **Decomposition plus your own calibration is the whole game.**
   - beri.net phishing study: one broad question scored 62.6% against Claude Haiku 4.5's
     81.3%.
   - Five narrow nouls combined with logistic weights fitted on 1,000 labels reached
     95.0%, against Haiku's 93.2% (not significant).
   - Arize, RAGTruth: at a naive 0.5 cutoff Jev scored 76% against Opus 5's 83%. With
     tuned thresholds (Jev 0.80, Opus 0.65) both reached 87%.
   - **Every call site needs its own labeled set and frozen threshold.**
4. **"Calibrated" carries an asterisk.**
   - On public benchmarks ECE is 0.024–0.032, but it rose to 0.107 on out-of-distribution
     synthetic support tickets.
   - In TypeSafe's own jaggedness example, a question and its negation sum to 1.19.
   - Choice and Noul formulations of the same proposition need not agree.
5. **Documented weak spots (TypeSafe's jaggedness page for 1.13):**
   - arithmetic and counting;
   - dates;
   - double negatives and indirection;
   - contradictory instructions;
   - long irrelevant state;
   - **adversarial content and prompt injection**.
6. **"Cannot hallucinate" means schema safety, not decision safety** (Prefactor). Jev can
   be confidently wrong at 0.94, and code that trusts typed output will act on it.
   Baselines matter: on one tool-call set Jev scored 93% and a constant "benign" scored
   79% (Victorino).

### Reasons for caution

- Much of the workflow evidence is vendor-authored. TypeSafe's reference labels are
  averages of frontier-LLM judgments.
- The independent papers are weeks old and not peer-reviewed.
- The ecosystem paper (arXiv 2609.30216) shows routing projects drawing ~41% of the
  stars. That is fashion, not evidence that routing works.

## Architectural fit with SASE

### Jev is not a provider and does not replace anything

- `sase_llm` providers are thin CLI-harness wrappers. `LLMProvider.invoke(...) ->
  InvokeResult(content, usage)` returns text.
- `invoke_agent()` runs finalizers and saves chat history. Jev cannot produce a
  declaration, a transcript, a commit, or a tool call.
- **SASE has no cheap structured-judgment path today** (cld). Judgment-shaped decisions
  are made one of two ways:
  - by an agent inside its own turn, as in `/sase_new_task` deduplication; or
  - by deterministic code: regexes, `+1` bars, globs, Rust policy.
- Even `get_file_summary()` runs a full workflow at the default size.
- **Jev therefore adds a capability, a dependency, and a trust surface.** It substitutes
  for nothing.

### Binding constraints from SASE's decision records

- **`triage-annotates-does-not-change-exit-codes`.** KNOWN needs an independent witness,
  and a model probability is never one.
  - The record reopens only if UNKNOWN stays above ~40% of items.
  - Measured UNKNOWN is ~4% of failing runs over 30 days (cld, all groups), with the
    same order in the lead's top-50 sample.
  - mus's proposal to treat Jev output as an "additional witness" therefore conflicts
    with this record and is rejected.
- **`corpus-before-mechanism` and `record-before-admit`.**
  - SASE built speculative recall machinery three times and deleted it three times.
  - Prediction "stays advisory until backtested", and admission consumes only
    calibrated prediction.
  - A generic decision subsystem built before one proven consumer repeats that pattern.
- **`host-owned-completion` and `receipts-prove-before-they-skip`.** A Jev score must
  never satisfy a finalizer, skip a check, or act as a receipt.
- **`rust-core-required` and the Rust-core boundary.**
  - The network transport, credentials, and retries stay in Python, preferably out of
    tree.
  - Only a *normalized decision record and threshold policy* could later move into
    `sase-core`, and only once more than one frontend needs it.
- **`hold-pull-fail-open` (fail open for courtesies).** An early-access service whose
  rate limits change without notice may drive only courtesies: ordering, hints,
  annotations. When it is down, SASE must behave exactly as it does today.
- **`adapters-normalize-harnesses`.** Any per-tool-call integration needs four
  harness-specific hooks (Muse, Claude, Grok, Codex), and no provider-neutral pre-tool
  veto hook exists.

## Critique of the plan

**Is integrating Jev a good idea? Mostly no as a product integration today. Yes as a
time-boxed, out-of-tree experiment.**

1. **The economics are irrelevant at SASE's scale.**
   - Outside tool calls, SASE makes at most a few hundred judgments a day.
   - At ~2K tokens each that is about $0.04 a day on Jev, or about $1 on a Haiku-class
     model.
   - Jev's 40–400× price advantage is real but worth little here, and its latency
     advantage matters only in hot loops, where its other weaknesses hurt most.
   - The real draws are typed outputs that never fail to parse, probabilities you can
     threshold in order to abstain, and not spending a quota-bearing agent turn on a
     one-bit question.
2. **"Typed" is not "trustworthy".** The biggest conceptual trap is a polished
   probability with no rationale that looks more authoritative than it is. Any surface
   must show provenance and the underlying deterministic facts, not a bare percentage.
3. **Vendor maturity is low.**
   - The model is weeks old, waitlisted, single-version, has no SLA, and changes its
     limits without notice.
   - Alias drift silently invalidates thresholds.
   - SASE must work identically with the plugin uninstalled.
4. **Data governance has a cost.**
   - Without enterprise ZDR, restrict state to public-repo bead metadata.
   - Transcripts, tool I/O, Bob-vault and Gmail-derived content are out of bounds.
5. **The plan as stated is underspecified** (grk). "Integrate Jev" admits four
   readings:
   - provider — wrong;
   - sprinkle it into every fuzzy `if` — wrong;
   - an optional advisory decision layer — right shape;
   - wait a quarter — also defensible.
6. **What Jev usefully exposes is a gap.** SASE lacks a cheap, typed judgment
   primitive. If that gap is filled, it should be filled
   [vendor-neutrally](#vendor-neutral-generalization), with Jev as one backend and a
   small-LLM structured call (or a local letter-scoring model) as another. Jev should
   not be the architecture.

## Choosing the first use case

### Where the researchers disagreed

Each researcher picked a different first use. The lead resolved the disagreement with
local evidence, checking each pick against measured volume and label availability on
`apollo`:

| Proposed first use (by) | Lead's measurement | Verdict |
| --- | --- | --- |
| **Stranded-wait / no-progress detection** (mus) | Codex and Muse write `wait_guard_log.jsonl`; Claude writes `interrupt_log.jsonl`. **Zero files of either kind exist across ~1,770 retained agent runs.** Claude's wait detection is mostly structural (outstanding background tasks, `ScheduleWakeup` use); the 700-character regex only applies once background tasks are outstanding. | **Reject.** There is no measured problem and no corpus, and it would add a network call to every turn end. Revisit only if guard firings or misses ever appear in the logs. |
| **Mentor skip/run** (grk) | **No mentor profiles are configured**, `~/.sase/mentors/` does not exist, and no agent metadata mentions a mentor run. | **Reject for this installation.** The design (fail-open skip, `,C` override, binary-checklist reranking) is sound and is the best fit *if* mentors become heavily used. |
| **`%model auto` tier routing** (gem) | There is no outcome-quality corpus. Gem's metric, agreement with the tier a human chose, measures imitation, not outcome. Its "~35% savings" figure is unsourced. Usage is quota-windowed, so a misroute wastes a whole agent turn of quota, far more than Jev saves. | **Defer.** Routing needs per-size outcome measurements first. Size aliases are deliberately curated (`size-alias-effort-ladder`). |
| **Post-run trace review / review prioritization** (cdx) | ~97 agent runs a day make tool calls (cld), but **no human labels exist**, so a labeling program would have to come first. It also sends transcripts and tool output to a third party (Bob vault, Gmail-derived content). | **Plausible second pilot.** It needs a written rubric, several hundred hand labels, an allowlisted redaction schema, and ideally enterprise ZDR. |
| **Task-bead triage scoring** (cld; gem secondary) | **The only existing labeled corpus**: 672 closed task beads (389 done, 235 canceled, 45 superseded), 313 ready, 635 typed, 943 sized. Inflow is 471 created against 241 closed in the last 30 days, so the backlog grows ~230 a month. Data is low-sensitivity public-repo metadata. | **First candidate, but only with the corrections to its [labels](#the-task-bead-corpus-is-noisier-than-it-looks) and [advice delivery](#where-advice-is-delivered-matters-more-than-the-score).** |

### Other proposals

- **LaunchApproval risk chips and skill suggestion** (grk): reasonable *later* advisory
  surfaces.
- **Pre-tool-call guardrail** (`pi-warden` pattern): rejected for now by every report
  that considered it, because it is injectable, sends every tool call off-machine, needs
  four harnesses, and SASE already has structural guards.

### The task-bead corpus is noisier than it looks

_Lead finding._ cld proposed using `done` versus `canceled ∪ superseded` as the label.
Inspecting `close_reason` shows the "canceled" label is largely **not a per-bead
judgment**:

| Canceled subset | Count | What actually drove it |
| --- | --- | --- |
| "Stale task bead swept from triage." | 95 | The automatic age-based stale sweep |
| Bulk backlog cuts ("Backlog triage 2026-08-0x", "Deprioritized in the 2026-08-14…", "Backlog cut to seven…") | 78 | Batch decisions on a given day |
| Individually judged (duplicate, obsolete, not reproducible, fixed manually, …) | 62 | Real per-bead judgment |

Consequences for the evaluation:

- A naive label lets bead **age** and the final `plus_one_count` leak the answer. A
  logistic regression on age would "win" without any semantic understanding.
- **Use only features available at filing time.** Either drop stale-swept and bulk-cut
  beads or report them as a separate stratum.
- The clean negative set is about **107** (62 individually canceled plus 45 superseded)
  against 389 done. That is small. Use cross-validation with bootstrap confidence
  intervals instead of a single 50/50 split, and treat the go criterion as a lower
  confidence bound, not a point estimate.

### Where advice is delivered matters more than the score

_Lead finding._

- **The human never answers triage gates.** Of 884 task-triage gate generations in 30
  days, **0 have a response**:
  - 695 were cancelled: 542 for `task_triage_presentation_changed`, 95 because the bead
    was no longer ready, 54 because the project was disabled, plus a few for closed or
    changed beads;
  - 189 are pending.
- Beads are resolved outside the gate UI. A chip painted on the gate would go unseen.
- **Bead `notes` are part of the triage gate's presentation fingerprint**
  (`presentation_fingerprint` in `scripts/_bead_task_triage_gates.py`). Writing Jev
  advice as a bead note, as cld and gem both propose (`sase bead note <id>
  "JEV-ADVISORY: …"`), would cancel and regenerate pending gates on every scoring pass.
  That worsens the existing 542-cancellation churn.
- Scores must therefore live in a **separate sidecar record** keyed by bead ID, input
  hash, model version, and question-set version. Surface them where the human actually
  works: ranked ordering in a bead list or a periodic digest, not bead text and not the
  gate presentation.

## Integration shape

| Option | Verdict |
| --- | --- |
| Jev as a `sase_llm` provider (in tree or as an entry-point plugin) | **Reject** (unanimous). |
| Hard-coding `typesafe-sdk` into the default install | **Reject.** The core stays vendor-free. |
| Inline HTTP calls at each call site | **Reject.** It repeats auth, timeout, redaction, and telemetry bugs N times. |
| Network calls or probabilities in `sase-core` | **Reject** (unanimous). |
| **Out-of-tree `sase-jev` repo shipping `sase_chop_*` / `sase_job_*` scripts** | **Do this first** (cdx, cld). Axe discovers these on `PATH` or in the venv (`axe/chop_script_runner.py`), so this needs **zero core changes**, and uninstalling is a full rollback. |
| In-tree `DecisionClient` / `judge` protocol with an optional TypeSafe backend (grk, mus, gem) | **Right eventual shape, premature now.** Extract it once a second consumer with its own corpus exists. Then add `DecisionRequest`/`DecisionRecord` wire types and threshold/abstain policy in `sase-core`, plus a `sase decide` CLI (read `cli_rules.md`) and a feature flag (`sase_flags.md`). |
| `%if::` code-form predicate calling Jev (behind the `typed_launch_units` beta flag) | **Free personal experimentation.** The runtime copies `os.environ` and treats exit 0 as eligible and exit 1 as skipped, so a 10-line script can gate a routine on a noul with nothing built. |

### Call-site contract for any Jev use

Merged from all five reports:

1. **Atomic, literal questions.** One judgment per question, composed in code. Include
   an explicit `none_of_these` option on every Choice. Never derive one answer from
   another (no complement algebra).
2. **Filter state.** Allowlisted fields, secret redaction, size caps. Never send
   transcripts, raw tool I/O, or source trees by default.
3. **Pin `jev-1.13.0`.** Keep thresholds frozen per call site in one reviewable file,
   versioned with the model ID and a question-set digest. Recalibrate on every version
   bump, using the response's `model` field as the join key.
4. **Fail open to today's behavior.**
   - Use a short timeout.
   - Back off on 429 and 529; never retry 401 or 422.
   - Bound concurrency and add a circuit breaker.
5. **Append-only observation records.** Each record holds the input hash, model and
   question versions, probabilities, threshold, action, latency and tokens, plus the
   later human disposition. Records are written before anything consumes them.
6. **Monotone authority.** Jev may add or raise scrutiny and reorder a queue. It may
   never suppress an alert, approve, skip, settle, close, or route away from an explicit
   user choice.
7. **Escalate to a reasoning model or a human,** never to a cheap judge scoring the same
   rubric ([why](#converging-independent-findings)).

## Recommended solution

### Prerequisites

**Step 0 — Prerequisites (about an hour, no code).**

- Request early access and keep the key only in `TYPESAFE_API_KEY`.
- Fix the data boundary: **public sase task-bead metadata only**. Exclude bob-cli,
  personal projects, transcripts and tool calls.
- Pin `jev-1.13.0`.

### Pre-registered offline evaluation

**Step 1 — Pre-registered offline evaluation (out of tree, about a day, under $0.10 of
tokens). This is the real decision point.**

- **Corpus.** Closed sase task beads, using filing-time features only (title,
  description, task type, size). Label: `done` against *individually judged*
  cancellations plus superseded ([see the label analysis](#the-task-bead-corpus-is-noisier-than-it-looks)).
  Stale-swept and bulk-cut beads are dropped or reported as a separate stratum.
- **Arms:**
  1. majority class;
  2. logistic regression on cheap filing-time features;
  3. Jev with one Choice question;
  4. Jev with about five narrow nouls and scores combined by fitted logistic weights;
  5. a small-LLM structured baseline (cheapest `@xsmall` member, same questions);
  6. optionally, embedding similarity for the superseded/duplicate sub-task.
- **Secondary checks in the same harness:** agreement with the filing agent's task type
  (635 typed beads) and size (943 sized).
- **Metrics:**
  - AUROC with bootstrap confidence intervals;
  - ECE after per-question calibration;
  - coverage at 0.9 precision for "will be canceled";
  - cost and p50/p95 latency.
- **Go criterion (pre-registered).** Arm 4 must beat arms 2 and 5 on AUROC by ≥0.05 at
  the lower confidence bound, **and** reach ≥30% coverage at 0.9 precision. Otherwise
  stop: either cheap features already carry the signal, or a provider SASE already pays
  for does as well without a new vendor.
- Write the result up as a research report. File nothing in sase yet.

### Advisory triage routine

**Step 2 — Only if Step 1 passes: an advisory `sase-jev` routine (2–3 days, separate
repo).**

- One `sase_chop_jev_task_triage_score` script. It sends all of a bead's questions in
  one request, so the state is sent once.
- Results go to a **sidecar decision record, never to bead notes or the gate
  presentation** ([see advice delivery](#where-advice-is-delivered-matters-more-than-the-score)).
- Expose a ranked view or digest of ready beads ("likely to launch", "likely stale or
  obsolete", "likely duplicate of X"), with provenance next to every number.
- Never resolve a gate. The `task_triage` auto-policy stays `forbidden`.
- Never close or snooze a bead. Fail open everywhere.
- Re-run the held-out set weekly to detect drift.
- **Kill criteria after four weeks:**
  - ready-queue age and net backlog growth (now ~+230 a month) do not improve; or
  - the human routinely overrides high-confidence hints.

  In either case, uninstall.

### Vendor-neutral generalization

**Step 3 — Only when a second consumer has its own labeled corpus: generalize
vendor-neutrally.**

- Likely next consumers, each needing labels first:
  - post-run trace review (cdx's design, which needs a rubric and hand labels);
  - mentor skip/run, if mentors come into use;
  - LaunchApproval risk chips;
  - skill/xprompt suggestion.
- Then add the `sase-core` decision-record schema and abstain policy, a `sase_decision`
  backend group with Jev and small-LLM backends, a `sase decide` CLI, and a decision
  record: "A model probability is an advisory courtesy, never a witness, receipt, or
  approval."

### What not to do now

- No `sase_llm` provider.
- No gate auto-policy driven by a model.
- No KNOWN or FLAKY minting, check skipping, or finalizer satisfaction.
- No per-tool-call guardrail.
- No transcripts, tool I/O, Bob-vault or Gmail content sent to TypeSafe.
- No generic decision subsystem before Step 1 produces a corpus-backed win.

### When to reopen this recommendation

Reopen this recommendation when:

- TypeSafe ships GA with an SLA and standard ZDR, or independent calibration results
  broaden. Then revisit trace review and guardrails in shadow mode.
- SASE grows a bounded, low-stakes, labeled decision stream above ~10K a day.
- Mentors or wait-guard firings start producing real volume.
- Step 1 passes on a second corpus.

## Errata in the individual reports

| Report | Claim | Correction |
| --- | --- | --- |
| mus | Env var `JEV_API_KEY` | The SDK reads `TYPESAFE_API_KEY`. |
| mus | Pilot stranded-wait detection, which "costs up to 2 extra provider turns when they misfire" | There are zero logged guard firings across ~1,770 retained runs, so no problem or corpus has been demonstrated. |
| mus | Jev output as an "additional witness" for UNKNOWN triage items | This conflicts with `triage-annotates-does-not-change-exit-codes`. A probability is not a witness. |
| mus | `retries=0` | This contradicts TypeSafe's guidance to back off on 429 and 529. |
| grk | Mentor skip/run is the "highest ROI" first acting feature | No mentors are configured or run on this installation. |
| grk | Li cascade "accepts 59%" | The paper reports **31.5% escalated** overall (64.8% on the JudgeBench subset). |
| cld | ECE 0.107 attributed to the phishing study | That figure comes from a separate out-of-distribution synthetic-ticket test. Public-benchmark ECE is 0.024–0.032. |
| cld | Rate limits 100K tok/s and 40 rps vs 250K tok/s and 1,200 rpm "disagree" | Both are TypeSafe figures. The larger one is from an earlier reading of the page (2026-09-18); 100K and 40 rps is current. |
| cld, gem | Write advisory scores as bead notes | Notes feed the triage-gate presentation fingerprint, so this causes gate churn. Use a sidecar record. |
| cld | Label = done vs canceled ∪ superseded | 173 of 235 cancellations were stale sweeps or bulk cuts. Correct as in [the label analysis](#the-task-bead-corpus-is-noisier-than-it-looks). |
| gem | Comparison table against Claude 3.5 Sonnet, GPT-4o, Gemini 2.0 Flash Lite, Claude 3.5 Haiku | These are stale model generations. Current comparisons in the papers are against GPT-6, Opus 5, Haiku 4.5, and GPT-5.6 Terra/Sol. |
| gem | "Non-autoregressive parallel classification head", "stable across identical inputs", "TypeSafe technical papers" | None of these is sourced. TypeSafe discloses only a "parallel sampler" and RLCD, publishes no paper, and claims only "more consistent". |
| gem | `%model auto` routing as the single best use, with ~35% savings | There is no outcome corpus, and the savings figure is unsourced. Its example code uses an invented SDK surface (`client.evaluate`, `timeout_ms`). |
| cdx, grk | The coding-agents page names Codex / "Grok Build" | It names Claude Code, Cursor, opencode, Copilot, Muse Spark, and Grok Bot. Codex is not named. The conclusion is unaffected. |

## Sources

**TypeSafe:**

- [Models](https://docs.typesafe.ai/models)
- [Primitives](https://docs.typesafe.ai/primitives)
- [API](https://docs.typesafe.ai/api)
- [Python SDK](https://docs.typesafe.ai/sdk/python.md)
- [Coding agents](https://docs.typesafe.ai/introduction/coding-agents)
- [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)
- [Legal](https://docs.typesafe.ai/legal)
- [Skill-suggestion cookbook](https://docs.typesafe.ai/cookbooks/skill_suggestion)
- [Launch post](https://typesafe.ai/blog/introducing-system-one-models-and-jev)

**Distribution:**

- [OpenRouter](https://openrouter.ai/typesafe)
- [Vercel AI Gateway](https://vercel.com/changelog/typesafe-ai-jev-now-available-on-ai-gateway)
- [AI SDK provider](https://ai-sdk.dev/providers/ai-sdk-providers/typesafe-ai)
- [Rate-limit history](https://opentweet.io/jev/limits)

**Independent evaluation:**

- [Li et al., arXiv 2609.26550](https://arxiv.org/html/2609.26550)
- [Rao & Callison-Burch, arXiv 2609.29769](https://arxiv.org/abs/2609.29769)
- [Beyond Calibration, arXiv 2609.33209](https://arxiv.org/abs/2609.33209)
- [Jev in the Wild, arXiv 2609.30216](https://arxiv.org/html/2609.30216v1)
- [beri.net](https://www.beri.net/article/typesafe-jev-typed-decision-model-calibration-decomposition-shadow-eval)
- [Arize](https://arize.com/blog/jev-as-a-judge/)
- [Prefactor](https://prefactor.tech/blog/jev-system-one-model-what-it-means-for-agent-evaluation)
- [Victorino](https://victorinollc.com/thinking/decision-model-on-the-control-path)
- [Victor Dibia explainer](https://victordibia.com/explainers/jev/)

**SASE tree:**

- `src/sase/llm_provider/{base.py,_invoke.py,_wait_guard.py,_wait_signals.py,claude.py}`
- `src/sase/bead/task_triage_policy.py`
- `src/sase/scripts/{sase_chop_bead_task_triage.py,_bead_task_triage_gates.py}`
- `src/sase/axe/chop_script_runner.py`
- `src/sase/agent/launch_condition_runtime.py`
- `src/sase/ace/mentor_output.py`
- Decision records read via `sase memory read`: `triage-annotates-does-not-change-exit-codes`,
  `corpus-before-mechanism`, `record-before-admit`.

**Local measurements (2026-10-01, `apollo`):**

- `sase bead list -t task -s all -n 0 -f json`
- `~/.sase/interaction_requests/task_triage/`
- `~/.sase/projects/*/artifacts/ace-run/` (wait-guard and interrupt logs, agent
  metadata)
- `sase tool failures -a -d 30 -j`
- Tool-call volume per `__cld` (`tool_calls.jsonl`, 7 days)

**Swarm reports** (`jev_sase_integration_assessment__{cdx,cld,grk,mus,gem}.md` in this
directory): [cdx](jev_sase_integration_assessment__cdx.md),
[cld](jev_sase_integration_assessment__cld.md),
[grk](jev_sase_integration_assessment__grk.md),
[mus](jev_sase_integration_assessment__mus.md),
[gem](jev_sase_integration_assessment__gem.md).
