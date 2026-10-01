# Integrating Jev (TypeSafe System One decision model) into SASE — research

Researcher: mus (`__mus`). Independent swarm report. No peer reports consulted.

## TL;DR

Jev is a real, narrow thing: TypeSafe AI's System One **decision** model
(`jev-latest`, `POST https://api.typesafe.ai/v1/systemone`, also via Vercel AI
Gateway since Sept 2026). It does not generate text. It takes `state` text
(≤32k tokens) plus a map of **typed questions** — `noul` (yes/no →
probability), `choice` (pick-one → distribution + confidence), `score`
(rubric level) — and returns calibrated answers in one pass, ~70–500 ms,
~$0.042/M input tokens.

It is worth integrating into SASE, but **not as an eighth `sase_llm`
provider**. `LLMProvider.invoke()` returns assistant text; Jev returns
verdicts. Forcing it into that interface is a category error and would break
the "providers are thin" contract in `docs/llms.md`.

The right shape is a small, optional, fail-open **judgement service** behind a
feature flag, used first for exactly one high-signal, low-risk pilot:
**stranded-wait / no-progress detection** (Claude wait-guard, agy
no-progress, Codex stranded commands). Then, only if shadow-mode calibration
holds, extend to failure-triage assistance and retryability as *advisors*,
never as deciders. Keep all current deterministic gates deterministic.

## 1. What Jev actually is (and is not)

Sources: TypeSafe positioning via community docs (HF practical guide, Sept
2026; AI-Stack enterprise explainer, Sept 2026; emlab-ai/wye design spec,
Sept 2026; LinkedIn JEV explainer). No Jev references exist in the SASE tree
today (searched `src`, `docs`, `sase/memory` — zero hits), so everything
below about Jev is external; everything about SASE is from-tree.

- **Mental model: "smart if-statements", not a chatbot.** Canonical example:
  `if safeguarding_risk > 0.95: escalate()`. Caller supplies state, declares
  the bounded answer space, receives `Choice`/`Score`/`Boolean` + probabilities.
  Code owns policy (thresholds); the model owns the judgement.
- **API shape (per public writeups):** one request carries `state` + N typed
  questions; one response answers all of them. `noul` = statement true?
  (p 0–1). `choice` = which of K options? (distribution). `score` = which
  rubric level? Good fit for "one state, many questions" (e.g. one agent
  tail → is-waiting? + made-progress? + stranded-kind? in one call).
- **Performance envelope:** 150–200 ms typical per decision call in
  interactive use; 70–500 ms range quoted; >1k-item batches classified in
  seconds. Cost ~$0.042/M input tokens — roughly two orders of magnitude
  cheaper than spending a generative turn for the same judgement.
- **What it is not:** not a code writer, not a reviewer, not a replacement
  for Claude/Codex/Muse/Grok/agy/qwen/opencode. It cannot produce the
  `InvokeResult(content=...)` SASE agents need. It has a 32k-token state
  cap, so full agent transcripts do not fit; callers must summarize/extract
  evidence first (which SASE triage gatherers already do under tight
  budgets).

## 2. Where SASE makes judgements today

SASE already has a judgement layer — it is just regexes, heuristics, and
expensive LLM-as-judge fallbacks:

| # | Current mechanism | Location | Jev fit |
|---|---|---|---|
| 1 | Stranded-wait detection: regex list (`will be notified`, `background(ed)?`, …) + tail-prose heuristics | `llm_provider/_wait_signals.py`, `llm_provider/agy.py` (no-progress recovery), `_subprocess_agy.py`, `_subprocess_codex.py`, `_wait_guard.py` | **Best fit.** Bounded question, ground truth in logs, latency-sensitive (continuation budget ≤2). |
| 2 | Failure triage: deterministic ancestry/baseline/selection/owner gatherers + label reduction (`new`/`known`/`flaky`/`unknown`), 5 s budget, fail-open | `tool/executor_triage.py`, `tool/triage_stage.py`, `tool/triage_inputs.py`, Rust `tool_run_triage_classify` | Good fit as **advisor only**. Project decision `triage-annotates-does-not-change-exit-codes` forbids triage changing outcomes; Jev may suggest labels, never flip `continue/stop`. |
| 3 | Retryability classifier: deterministic Rust rules over git/gh stdout/stderr/exit/operation | `core/retryability_facade.py`, `core/retryability_wire.py` | Medium fit. Rules are auditable and offline; Jev could cover the long-tail "unknown" class behind a flag. |
| 4 | Artifact-link / intent matching, gate-intent guards, kill-intent parsing | `dispatch/*intent*.py`, `agent/gate_intent.py`, `llm_provider/gate_intent_guard.py`, artifact-hook intent research (202609) | Medium fit. Real semantic task, but precision bar is high and failures are user-visible. |
| 5 | Provider routing / load balancing / alias pools | `llm_provider/load_balancing.py`, `provider_priority_routing.py`, `models.yml` | Poor fit now. Routing is availability + user config, not a semantic judgement; adding a network call into the hot admission path hurts. |
| 6 | Mentor review (code review comments on patches) | `axe/mentor_runner.py`, `workflows/mentor.py` | Poor fit as decider. Mentors must *write* findings; Jev could at most pre-score "likely-actionable?" — unproven, and risks suppressing true positives. |
| 7 | Commit finalizer / bead-action / gate lifecycle | `finalizers/`, `core/bead_action_facade.py`, `core/gate_decision_facade.py` | **Must not use Jev.** Host-owned completion; `gates-never-block`, `explicit-handoff-fails-closed`, and completion-is-host-owned require deterministic, auditable decisions. |

Two structural facts constrain every option:

- **Rust-core boundary** (`docs/rust_backend.md`, `rust-core-required`):
  shared deterministic backend lives in `sase-core` with no Python fallback
  and no env-var backend switch. A network model call can never move into
  the Rust core. Jev must stay a Python-side optional advisor.
- **Generative vs. decision split** (`docs/llms.md`): providers are thin
  CLI wrappers returning text. Jev has no CLI, no streaming, no tiers, no
  `model_override` semantics. It belongs beside the provider layer, not in it.

## 3. Critique: is integrating Jev a good idea?

**Yes, narrowly — as an advisor for heuristic judgements, not as a
provider or a decider.** Arguments for and against:

**For:**
- The regex wait-detectors are the weakest link in the single-turn guard
  story (Claude wait-guard, agy no-progress). They are brittle across model
  phrasings and already cost bounded continuations (up to 2 extra full
  provider turns when they misfire). A 150 ms, sub-cent calibrated
  `is_waiting`/`made_progress` call that *saves* a wasted continuation pays
  for itself ~1000×.
- Triage gatherers already produce bounded evidence plus "unknown" labels
  under 1–8 s budgets. Jev's one-state-many-questions shape maps 1:1 onto
  "one failure bundle → several labels". Fail-open design already exists,
  so a Jev advisor degrades to today's behavior on any error.
- Cost/latency vs. LLM-as-judge is not close. Anywhere SASE would
  otherwise spend a `small`-tier turn to classify, Jev is faster and
  cheaper by 10–100×, with a usable confidence signal instead of parsed prose.

**Against / risks (all manageable, none fatal):**
- **New network + vendor dependency in the agent hot path.** TypeSafe is a
  single small vendor (Sept 2026 vintage); API, pricing, and calibration
  can shift. Mitigation: optional, default-off, fail-open with local
  heuristic fallback; also route via Vercel gateway as alternate transport.
- **Privacy.** Agent tails, diffs, and failure logs sent to TypeSafe are
  subject to its retention, like the existing Grok/Muse training-data
  caveats in `docs/agent_providers.md`. Needs per-call redaction (reuse the
  `SASE_TOOL_LOG_FULL=0` bounded-summary convention), an explicit opt-in,
  and docs. Never send full source by default; send the same bounded
  excerpts triage already persists.
- **Offline/determinism.** SASE works offline with local CLIs; Jev does
  not. Any Jev call must have a timeout (≤1–2 s for wait-guard, ≤3 s for
  triage), run concurrently with or after the deterministic path, and lose
  ties to determinism.
- **32k state cap.** Full prompts/transcripts do not fit. Callers must pass
  tails + extracted signals (which is also the privacy win).
- **Calibration is not accuracy.** Probabilities need per-question
  threshold tuning on SASE's own logs plus an abstain band (e.g.
  0.4–0.6 → fall back to heuristic). Ship shadow mode first; do not trust
  vendor calibration blindly.
- **Maturity.** Community reports are weeks old. Treat the API as
  unstable: pin `jev-latest` vs. versioned model explicitly, version the
  question schemas, and log model id per verdict.

Net: the failure mode of *not* doing anything is continued regex churn on
wait/no-progress phrasing across every new model release. A bounded pilot
is cheap and reversible; a full "Jev provider" rewrite is not.

## 4. Integration options considered

**A. Jev as 8th `sase_llm` provider — reject.** Breaks `LLMProvider`
contract, tier mapping, `models.yml` catalog, autodetect, `%model`
routing, usage accounting, and TUI model picker. Nothing to salvage; do
not do this even behind a flag.

**B. Jev as external `sase_llm` plugin package — reject for the same
reason.** The plugin group is the wrong extension point. A judgement
service is not an LLM backend.

**C. Jev as judgement advisor service (new module, e.g.
`sase.judge.jev` + `sase.judge.policy`) — recommend.** New narrow
interface, e.g. `ask(state, questions) -> {answers, confidences,
model_id, latency_ms}`, with three implementations: `heuristic`
(current behavior), `jev` (HTTP), `shadow` (both, log disagreement).
Call sites opt in one at a time. Config lives under a new
`judge:` section in `sase.yml`, not `llm_provider:`. Env:
`JEV_API_KEY` (or existing secret-manager convention), `SASE_JEV_TIMEOUT`,
`SASE_JEV_MODE=off|shadow|assist`.

**D. Inline `requests` calls at each call site — reject.** Repeats auth,
timeout, redaction, and telemetry bugs N times. One module or nothing.

**E. Rust-core verdicts — reject.** Violates `rust-core-required` (no
network in core, no Python fallback carve-outs beyond the two documented
ones). Rust keeps deterministic classifiers; Jev advises from Python.

## 5. Recommended solution

**Do C, in three gated phases. Default off throughout until Phase 3 exit.**

**Phase 0 — scaffolding (1 short epic):**
- New `src/sase/judge/` module: `client.py` (single HTTP call with timeout,
  retries=0, model pin, schema version), `policy.py` (thresholds + abstain
  bands per question, owned in code), `telemetry.py` (per-verdict row:
  question, answer, p, threshold, winner heuristic-vs-jev, latency, cost).
- Config: `judge.mode` (`off` default), `judge.questions` allowlist,
  `judge.redact` (default bounded tails only). Doctor check
  `sase doctor -C judge -v` reports key presence + reachability without
  spending a paid call (mirror the `agy`/`muse` probe discipline).
- Hard rules: Jev never changes exit codes, never blocks a gate, never
  runs inside Rust, never sees unredacted secrets (reuse tool-call
  redaction helpers). Every Jev-influenced log line names the model id.

**Phase 1 — pilot: stranded-wait / no-progress (the one bet):**
- Questions: `is_waiting` (noul), `made_progress` (noul), optionally
  `stranded_kind` (choice: none/backgrounded/approval/waiting-prose).
  State: provider name + last ~2–4 KB of reply tail + structural facts
  already extracted (tool-use count, pending run_command?) — never the
  full transcript.
- Behavior: run heuristic first (sync, current path). If heuristic says
  no-progress/wait, *or* confidence demands it, consult Jev within the
  existing continuation budget (still ≤2 continuations). Disagreement →
  deterministic tie-break documented per provider (suggest: heuristic wins
  on `stop`, Jev may only *add* a continuation, never remove a needed one
  in Phase 1). Shadow-mode for one release first: log only, change nothing.
- Success bar to exit Phase 1: on a labeled corpus of past
  `wait_guard_log.jsonl` + agy trajectory cases, Jev-assisted path shows
  higher precision/recall than regex alone with p95 added latency <500 ms
  and zero fail-closed incidents. If it misses, delete the pilot and keep
  the interface.

**Phase 2 — conditional: triage + retryability advisors:**
- Triage: `is_known`/`is_flaky` (noul pair) over the already-gathered
  evidence bundle; Jev output becomes an *additional witness*, consumed
  only where the deterministic label is `unknown`. Settle path unchanged.
- Retryability: Jev covers only the Rust classifier's `unknown` verdicts.
- Mentors, routing, finalizers, gates: explicitly out of scope until
  Phases 1–2 prove calibration on SASE's own data.

**Phase 3 — graduate or kill:** enable `assist` by default for the pilot
question only if Phase 1/2 bars are met, with per-question kill switches
and the heuristic fallback intact. Publish the calibration report
(thresholds, corpus size, disagreement rate) in `docs/` next to the
`llms.md` judgement section.

**What to decide up front (smallest decision set):** question schemas +
threshold ownership in code (yes, per §5); `off/shadow/assist` flag with
`off` default (yes); bounded redacted state only (yes); pilot = wait-guard
(yes). Everything else (more questions, default-on, gateway vs. direct)
waits for Phase 1 data.

## 6. Costs, latency, privacy — quick numbers

- Cost: at $0.042/M input tokens, a 2 KB state + questions is a fraction
  of a cent per call (~$0.00002–0.0001). Even 10k agent runs × 2 calls is
  single-digit dollars. Negligible vs. one wasted `small`-tier continuation.
- Latency: 70–500 ms fits inside existing 1–8 s triage/gather budgets and
  the wait-guard continuation loop; run with a hard timeout and
  heuristic-first ordering so Jev never sits on the critical path.
- Privacy: bounded tails + structured facts, same redaction as
  `tool_calls.jsonl` writer; explicit opt-in flag; document retention link
  alongside the Grok/Muse privacy notes in `docs/agent_providers.md`.
  Consider enterprise allowlist (`judge.allow_questions`, project-level
  opt-out) before any default-on.

## 7. Open questions for the lead (not blockers for Phase 0)

1. Data retention contract with TypeSafe: confirm ZDR/enterprise terms
   before any non-shadow use on proprietary checkouts.
2. Direct `api.typesafe.ai` vs. Vercel AI Gateway transport (auth, audit,
   failover).
3. Whether to publish the shadow corpus + thresholds as a versioned eval
   (recommended: yes, small sampled fixture, redacted).

---
*Method: repo read (`docs/llms.md`, `docs/agent_providers.md`,
`docs/architecture.md`, `docs/plugins.md`, `docs/rust_backend.md`,
`llm_provider/` wait/no-progress path, `tool/executor_triage.py`,
`triage_stage.py`, `core/retryability_facade.py`,
`load_balancing.py`); external Jev writeups (TypeSafe/HF/AI-Stack/wye
spec/ToolNerd/pricing example); zero Jev hits in-tree confirmed by search.*
