# Integrating Jev into SASE: Architectural Analysis, Feasibility Critique, and Recommended Solution

- **Researcher:** `gem` (Researcher `research.y.gem` in 5-researcher swarm)
- **Date:** 2026-10-01
- **Workspace:** `sase-org/sase` @ workspace #23
- **Context:** Exploring integration feasibility of TypeSafe AI's "Jev" System One decision/judgement model into the SASE platform, command plane, and agent orchestrator.
- **Related Prior Research:**
  - `sase/repos/research/202609/agents_tab_finalizers_decks_and_cards__gem.md` (Finalizer lifecycles, host-owned completion)
  - `decisions:triage-annotates-does-not-change-exit-codes` (Deterministic witness vs probabilistic labeling)
  - `decisions:corpus-before-mechanism` (Strict prerequisite for adding retrieval/inference machinery)
  - `decisions:rust-core-required` & `decisions:adapters-normalize-harnesses` (Backend boundaries and harness contracts)

---

## 1. Executive Summary

In mid-September 2026, TypeSafe AI publicly debuted **Jev** (`jev-1.13.0`), a specialized "System One" decision model designed by former OpenAI researcher Diogo Almeida. Unlike generative Large Language Models (LLMs) that produce autoregressive token streams (System Two), Jev is a non-autoregressive decision engine that takes arbitrary state and returns strictly typed enums (`Choice`), ordinal ratings (`Score`), or calibrated boolean probabilities (`Noul`). With advertised inference latencies between 70 ms and 500 ms and an aggressive pricing structure ($0.042 per million input tokens, with free output), Jev has provoked widespread interest as an alternative to "LLM-as-a-judge" patterns, prompt routers, and policy guardrails.

This research investigates whether and how Jev should be integrated into **SASE (Structured Agentic Software Engineering)**.

### The Central Dilemma
SASE's core architecture is built upon **hard, deterministic evidence, git witnesses, immutable event journals, host-owned execution boundaries, and a hermetic Rust core**. In contrast, Jev is a **probabilistic, cloud-hosted, proprietary black-box decision function with zero reasoning transparency (no chain-of-thought, no natural language justifications)**. 

Integrating Jev presents an immediate tension between:
1. **The Promise:** Near-instantaneous, penny-fraction classification of developer intents, model routing tiers, and background task bead enrichment without burning expensive Claude/Gemini/Codex reasoning tokens.
2. **The Peril:** Contaminating SASE's deterministic guarantees (such as failure triage, gate enforcement, goal settlement, and test pass/fail semantics) with non-explainable, closed-source heuristics that violate core architectural decisions.

### Bottom Line Verdict & Recommendation
**Do NOT integrate Jev into SASE's core execution loop, ToolRun failure triage, gate approvals, or goal settlement.** Making Jev an authoritative gatekeeper or embedding it in the Rust backend (`sase-core`) would violate multiple foundational SASE decision records (`triage-annotates-does-not-change-exit-codes`, `rust-core-required`, `goals-host-binds`, and `corpus-before-mechanism`).

Instead, adopt a **Decoupled Advisory Provider Architecture** implemented strictly in the Python/Tool layer:
1. **Primary Use Case — Fast-Path Model & Effort Routing (`%model auto`):** Deploy Jev as an optional pre-flight prompt classifier to automatically route developer tasks to appropriate size tiers (`@small`, `@medium`, `@large`, `@xlarge`) in ~150 ms, saving up to 50% in agent token costs.
2. **Secondary Use Case — Asynchronous Bead Triage Enrichment (`sase chop bead-task-triage`):** Utilize Jev in background Lumberjack routines to score task bead duplicates and recommend task types/subsystems, recording predictions as non-binding advisory metadata for human operators.
3. **Strict Invariant — Fail-Open & Advisory Only:** Every Jev interaction must be bounded by a 500 ms hard timeout, must fail open to deterministic defaults upon any network or API error, and must never possess authoritative permission to alter command exit codes, bypass human gates, or close beads.

---

## 2. Technical Profile: What is Jev?

To evaluate Jev objectively, we must understand its architectural profile, operational economics, and documented edge-case behavior.

```
                    ┌───────────────────────────────────────────────┐
                    │            Jev Evaluation Contract           │
                    └───────────────────────────────────────────────┘
                                           │
                        ┌──────────────────┴──────────────────┐
                        │ State Payload (up to 32,000 tokens) │
                        │  • Prompt, Diffs, Logs, JSON State  │
                        └──────────────────┬──────────────────┘
                                           │
               ┌───────────────────────────┼───────────────────────────┐
               ▼                           ▼                           ▼
        ┌─────────────┐             ┌─────────────┐             ┌─────────────┐
        │   Choice    │             │    Score    │             │    Noul     │
        │ Predefined  │             │   Ordinal   │             │   Boolean   │
        │ Categorical │             │   Rubric    │             │ Probability │
        │    Enum     │             │  (e.g. 1-5) │             │ (0.0 - 1.0) │
        └─────────────┘             └─────────────┘             └─────────────┘
               │                           │                           │
               └───────────────────────────┼───────────────────────────┘
                                           ▼
                    ┌───────────────────────────────────────────────┐
                    │   Parallel Forward Pass (Single Inference)    │
                    │         Latency: 70 ms - 500 ms               │
                    │        Cost: $0.042 / 1M Input Tokens         │
                    └───────────────────────────────────────────────┘
```

### 2.1 Architectural Primitives
Jev (`jev-1.13.0`) is engineered specifically as a "System One" decision model. Traditional autoregressive models generate text word-by-word, incurring high time-to-first-token (TTFT) and cumulative token generation latency. Jev discards the autoregressive decoder in favor of a parallel classification head trained via **Reinforcement Learning for Calibrated Decisions (RLCD)**.

The API (`POST https://api.typesafe.ai/v1/systemone`) takes:
- **`state`**: Context data (up to 32,000 tokens of text, code, or JSON).
- **`questions`**: A map of typed evaluation questions using three primitives:
  1. `Choice`: Categorical selection among a closed set of string literals (e.g. `["small", "medium", "large"]`).
  2. `Score`: Numeric rating against an ordered rubric (e.g. 1 to 5).
  3. `Noul`: Calibrated boolean likelihood (0.0 to 1.0) answering a yes/no hypothesis.

### 2.2 Performance & Economic Metrics
- **Context Window:** 64,000 tokens total; maximum 32,000 tokens for `state` plus the longest question.
- **Latency:** Vendor-reported 70 ms to 500 ms p95 end-to-end. (Network transit to TypeSafe AI's edge typically contributes 40–80 ms of this budget).
- **Pricing:** $0.042 per 1,000,000 input tokens. Output tokens are completely free since no text tokens are emitted.
- **SDK Ecosystem:** Official `typesafe-sdk` in Python; integration with Pydantic AI (`TypeSafeModel`); community Rust crates (`typesafe_api`, `typesafe_ai_client`).

### 2.3 Critical Weaknesses & Failure Modes
Independent analysis reveals several non-trivial risks:
1. **Total Absence of Reasoning Traces:** Jev produces zero chain-of-thought, scratchpads, or textual rationale. It returns only the label and a confidence float. When a decision is counterintuitive or wrong, there is no log to diagnose *why*.
2. **Input "Jaggedness":** TypeSafe's technical papers acknowledge sensitivity to document layout and position. Reordering sections in the input state or changing whitespace can induce label flipping on borderline cases.
3. **Counting & Arithmetic Failure:** Jev cannot count lines of diffs, tally occurrences, or evaluate mathematical invariants reliably.
4. **Structural Validity ≠ Semantic Correctness:** While Jev structurally guarantees valid schema output (an invalid enum variant is mathematically impossible), the semantic validity of the label remains probabilistic.
5. **Closed Ecosystem & Proprietary Dependency:** Jev is hosted exclusively by TypeSafe AI (waitlist-gated API, with select availability via OpenRouter and Vercel AI Gateway). There are no self-hosted weights, no local CPU/GPU runtimes, and no airgapped deployment path.

---

## 3. SASE Architectural Alignment & Invariant Conflicts

Before evaluating features, we must examine how Jev intersects with SASE's durable design decisions. SASE is intentionally opinionated; its design records establish strict operational invariants.

### 3.1 `decisions:rust-core-required`
> *"Shared backend behavior lives in sase-core with no Python fallback and no env-var backend switch."*

`sase_core` (written in Rust) manages the SQLite stores, process isolation, ToolRun ledgers, and workspace locks. Putting an external network call to TypeSafe AI's cloud service into `sase-core` would destroy the hermetic, sub-millisecond guarantees of the Rust backend. Any Jev integration **must live strictly in the Python userland/CLI orchestration layer**, completely outside `sase-core`.

### 3.2 `decisions:triage-annotates-does-not-change-exit-codes`
> *"Failure triage annotates each failed tool-run with durable NEW, KNOWN, FLAKY, or UNKNOWN items and a verdict, but never changes its exit code. KNOWN requires an independent witness; insufficient evidence is UNKNOWN."*

This is the strongest philosophical barrier in SASE. When a test fails in `sase tool run`, SASE classifies it as `KNOWN` only when an identical failure has been witnessed on an ancestor or master-red commit. Probabilistic classification is explicitly rejected: if there is no hard witness, the failure is `UNKNOWN`. **Using Jev to guess whether a test failure is "known" or "expected" violates this decision directly.**

### 3.3 `decisions:goals-host-binds` & `decisions:host-owned-completion`
> *"The host binds every LLM turn to exactly one goal before spawn; agents only name or adopt their own draft and claim or keep open; only a human settles."*

SASE forbids autonomous agents from settling goals, creating git commits, or finalizing PRs without host-supervised execution. A "System One" model cannot be given authority to approve PRs, mark goals settled, or declare tasks finished.

### 3.4 `decisions:corpus-before-mechanism`
> *"SASE does not ship memory retrieval, linking, or recall machinery ahead of a corpus that demonstrably needs it. Mechanism follows corpus; the corpus is the evidence that the mechanism is the right shape."*

Speculatively integrating an AI decision engine because it is novel or trendy is an explicit anti-pattern. Three prior attempts at building speculative predictive mechanisms in SASE were subsequently deleted from the codebase (`e8c2f14bb`, `37973b8b3`, `21e1640ee`). Jev must be justified by an existing, concrete problem that deterministic algorithms cannot solve.

---

## 4. Subsystem-by-Subsystem Feasibility Analysis

We evaluate six potential candidate areas where Jev could theoretically be applied within SASE:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SASE Subsystem Evaluation Map                         │
├─────────────────────────────────────┬───────────────────────────────────────┤
│ Subsystem Area                      │ Verdict & Suitability                 │
├─────────────────────────────────────┼───────────────────────────────────────┤
│ 1. ToolRun Failure Triage           │ ❌ REJECT (Violates Witness Invariant)│
│ 2. Dynamic Model & Effort Routing   │ ✅ ADOPT (High ROI, Fast-Path Opt-in) │
│ 3. Task Bead Triage & Deduplication │ ⚠️ ADVISORY ONLY (Background Chops)   │
│ 4. Gate Intent & Plan Guardrails    │ ⚠️ EXPERIMENTAL (Requires Fallback)  │
│ 5. Code Review (CRS) Comment Triage │ 🟡 SECONDARY (Moderate Benefit)       │
│ 6. Goal Settlement & Milestones     │ ❌ REJECT (Violates Human Settlement) │
└─────────────────────────────────────┴───────────────────────────────────────┘
```

### 4.1 Candidate 1: ToolRun Failure Triage (`executor_triage.py`)
- **Concept:** When a test or build fails, pass the failure logs and diff to Jev to classify the failure.
- **Analysis:** In SASE, failure triage settles into SQLite within a strict budget (`_TRIAGE_BUDGET_SECONDS = 5.0`). SASE uses deterministic extractors (`tool_run_triage_extract`) to parse pytest, cargo, or ruff output into discrete failure keys, comparing them against the baseline ledger.
- **Fatal Flaw:** If Jev labels a failure as `KNOWN` based on semantic similarity, SASE might allow an agent to continue past a critical newly-introduced regression. `decisions:triage-annotates-does-not-change-exit-codes` explicitly forbids this: *insufficient evidence is UNKNOWN*.
- **Verdict:** **REJECT as triage arbiter.** (Permissible only as a non-authoritative semantic tag in the TUI, e.g. `tag: "network_timeout"`, but never influencing the verdict).

### 4.2 Candidate 2: Dynamic Model & Effort Routing (`launch_selection.py`, `%model auto`)
- **Concept:** When a user or workflow launches an agent without an explicit model tier (`@small`, `@large`, `@xlarge`), run Jev on the prompt and repo status to select the most cost-effective model and reasoning effort.
- **Analysis:** 
  - Today, users either manually specify size aliases or default to large models. Running `@xlarge` (e.g. Claude 3.5 Sonnet at high reasoning) for a 1-line typo fix burns thousands of tokens and adds 15–30 seconds of reasoning latency.
  - Generative routing (using an LLM to pick an LLM) is too slow: spending 4 seconds for an LLM to decide which LLM to call defeats the purpose.
  - Jev can evaluate prompt complexity, target repository, and command history in **~120 ms for $0.0001**:
    ```json
    {
      "questions": {
        "tier": {
          "type": "choice",
          "options": ["small", "medium", "large", "xlarge"]
        },
        "reasoning_effort": {
          "type": "choice",
          "options": ["none", "low", "medium", "high"]
        },
        "is_pure_query": {
          "type": "noul"
        }
      }
    }
    ```
- **Economics:** If 40% of runs in a high-volume workspace can be safely downgraded from `@large` to `@small` or `@medium`, workspace token consumption drops by ~35% with zero perceivable launch delay.
- **Verdict:** **HIGH FEASIBILITY. The single best application of Jev in SASE.**

### 4.3 Candidate 3: Task Bead Triage & Deduplication (`sase chop bead-task-triage`)
- **Concept:** SASE agents automatically file task beads for discovered bugs, flakes, and CI failures. A background routine (Lumberjack chop) runs periodically to triage ready beads.
- **Analysis:** 
  - Currently, `task_triage_policy.py` relies on simple reporter counts (`+1` bar) and time-based staleness sweeps.
  - SASE forbids agents from creating duplicate task beads (`sase/memory/sase_beads.md`), requiring them to corroborate existing tasks instead. However, agents frequently file semantic duplicates under slightly different titles.
  - Jev can ingest a batch of recent open task beads and evaluate a newly proposed bead:
    - `is_duplicate`: `Noul` likelihood that this matches an active bead.
    - `best_match_id`: `Choice` among the top candidate bead IDs.
    - `suggested_task_type`: `Choice: ["bug", "ci", "feature", "flake", "memory"]`.
- **Verdict:** **VIABLE AS ADVISORY CHOP ENRICHMENT.** It runs out-of-band in Lumberjack, never blocks interactive agent work, and merely annotates beads with suggestions for human review.

### 4.4 Candidate 4: Gate Intent & Plan Guardrails (`gate_intent_guard.py`)
- **Concept:** When an agent proposes an implementation plan via `/sase_plan`, use Jev to pre-screen the plan for safety violations (e.g., modifying protected files, violating `AGENTS.md` instructions, mentioning ephemeral `sase_<N>` directories) before creating a human `PlanApproval` gate.
- **Analysis:**
  - Jev's `Noul` can detect policy violations quickly.
  - **Critical Drawback:** Because Jev cannot generate text, if it flags `violates_policy: 0.94`, it cannot explain *which line* or *which policy* was violated! A human or agent receiving an unelaborated rejection cannot take corrective action.
- **Verdict:** **UNFAVORABLE.** A lightweight generative model (e.g., Gemini Flash Lite) that outputs structured JSON *with an explanation* is far superior for plan review.

---

## 5. Detailed Comparative Evaluation

How does Jev compare against alternative decision strategies already available to SASE?

| Dimension | Deterministic Code (Regex / AST / Rust) | Fast Generative LLM (Gemini 2.0 Flash Lite / Claude 3.5 Haiku) | Heavyweight LLM (Claude 3.5 Sonnet / GPT-4o / Gemini 1.5 Pro) | TypeSafe AI Jev (`jev-1.13.0`) |
|---|---|---|---|---|
| **Latency** | **< 1 ms** | 300 ms – 900 ms | 2,000 ms – 12,000 ms | **70 ms – 400 ms** |
| **Input Cost / 1M Tokens** | **$0.00** | $0.075 – $0.25 | $3.00 – $15.00 | **$0.042** |
| **Output Cost** | **$0.00** | $0.30 – $1.25 / 1M | $15.00 – $75.00 / 1M | **$0.00 (Free)** |
| **Schema Guarantee** | 100% Strict TypeSafe | Near 100% (with Pydantic/Instructor) | Near 100% (with Pydantic/Instructor) | **100% Guaranteed Native** |
| **Explainability** | High (Code traces & stack errors) | **High (Emits rationale & citations)** | **Very High (Deep Chain-of-Thought)** | **Zero (Raw label/float only)** |
| **Offline / Airgapped** | **Native (Local)** | Possible via local models (Qwen 2.5 7B / Ollama) | Rarely practical locally | **Impossible (Hosted SaaS Only)** |
| **Determinism** | **Deterministic** | Slightly stochastic | Slightly stochastic | Non-autoregressive (Stable across identical inputs) |
| **SASE Fit** | **Foundational (`sase-core`)** | Excellent for CRS, Mentors, Plan Review | Standard for primary Agent turns | **Niche: Pre-flight Advisory Routing** |

### The Critical Trade-off: Latency vs Explainability
The primary advantage Jev holds over models like Gemini 2.0 Flash Lite or Claude 3.5 Haiku is a ~250 ms latency advantage and a marginal cost reduction. However, in developer toolchains, **explainability is paramount**. 

If a system makes a decision that alters developer workflow (e.g., rejecting a plan, marking an issue as duplicate, or denying a gate), developers demand an explanation. Because Jev cannot provide explanations, its utility is strictly confined to domains where:
1. Latency is critical (<200 ms budget).
2. The user does not interact with the intermediate reasoning.
3. Errors fail harmlessly to a safe baseline.

---

## 6. Recommended Architecture: The Decoupled Advisory Provider Pattern

If SASE integrates Jev, it must be implemented cleanly to preserve architectural integrity.

```
                          ┌────────────────────────┐
                          │   SASE CLI / Runner    │
                          └───────────┬────────────┘
                                      │
                         User Prompt / Workflow Step
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │  sase.judgement Provider  │
                        └─────────────┬─────────────┘
                                      │
                 ┌────────────────────┴────────────────────┐
                 │                                         │
        [Jev Feature Enabled]                    [Disabled / Timeout]
                 │                                         │
                 ▼                                         ▼
   ┌───────────────────────────┐             ┌───────────────────────────┐
   │ TypeSafeClient (Jev API)  │             │   Static Heuristics       │
   │  - Timeout: 500 ms        │             │   - Size Aliases          │
   │  - Parallel Question Pass │             │   - Default Priorities    │
   └─────────────┬─────────────┘             └─────────────┬─────────────┘
                 │ (Success)                               │
                 ▼                                         │
   ┌───────────────────────────┐                           │
   │ Advisory Decision Record  │                           │
   │  - tier: "small"          │                           │
   │  - confidence: 0.91       │                           │
   └─────────────┬─────────────┘                           │
                 │                                         │
                 └────────────────────┬────────────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │    Primary Agent Launch   │
                        │ (Claude / Gemini / Codex) │
                        └───────────────────────────┘
```

### 6.1 Architectural Rules for Integration

1. **Strictly Outside `sase-core`:**
   Implement Jev in a new Python package under `src/sase/judgement/` (or an optional plugin `sase-jev`). Do not link C or Rust bindings into `sase_core_rs`.
2. **Advisory, Never Authoritative:**
   Jev outputs are labeled as `advisory`. They may recommend a model tier or suggest an issue tag, but they never possess write permissions on the bead status lifecycle or git state.
3. **Hard 500 ms Timeout & Fail-Open Semantics:**
   The judgement client must enforce a strict 500 ms timeout. If the TypeSafe API times out, returns an HTTP 5xx, or experiences rate limits, SASE logs a debug warning and falls back immediately to the existing deterministic defaults. The developer experience must never be blocked by an external decision API.
4. **Audit Trail Recording:**
   Every Jev call must record an event in `sase_log` / artifacts detailing:
   - State fingerprint (SHA-256)
   - Questions schema passed
   - Latency in milliseconds
   - Returned choice/score/probability
   - Fallback status (if triggered)

### 6.2 Implementation Blueprint: `%model auto`

The most compelling integration is **Adaptive Tier Selection**:

```python
# src/sase/judgement/routing.py
from __future__ import annotations

import os
import time
from typing import Literal
from sase.llm_provider.types import ModelTier

def resolve_adaptive_tier(
    prompt: str,
    *,
    timeout_ms: int = 500,
) -> tuple[ModelTier, float]:
    """Resolve an optimal model tier via Jev in under 500ms.
    
    Fails open to 'large' if Jev is unreachable or unconfigured.
    """
    api_key = os.getenv("TYPESAFE_API_KEY")
    if not api_key:
        return "large", 1.0

    try:
        from typesafe_sdk import TypeSafeClient
        client = TypeSafeClient(api_key=api_key, timeout_ms=timeout_ms)
        
        start_time = time.monotonic()
        response = client.evaluate(
            state=prompt[:16000],  # Bounded state context
            questions={
                "tier": {
                    "type": "choice",
                    "options": ["small", "medium", "large", "xlarge"],
                    "description": "Select the minimum engineering capability required."
                },
                "is_complex_refactor": {
                    "type": "noul",
                    "description": "Does this require complex multi-file architectural changes?"
                }
            }
        )
        latency = (time.monotonic() - start_time) * 1000
        
        tier_choice = response.choices["tier"].value
        confidence = response.choices["tier"].confidence
        
        # Guardrail: High complexity forces at least 'large'
        if response.nouls["is_complex_refactor"].probability > 0.70:
            if tier_choice in ("small", "medium"):
                tier_choice = "large"

        return tier_choice, confidence

    except Exception:
        # Fail open seamlessly to standard large tier
        return "large", 0.0
```

---

## 7. Phased Implementation Roadmap

If the project proceeds with a trial of Jev, execute the integration across three strictly gated phases:

### Phase 1: Shadow Corpus Collection (Adhering to `decisions:corpus-before-mechanism`)
- **Objective:** Gather an empirical corpus of decision accuracy before giving Jev control over any launches.
- **Action:** Implement a passive shadow hook in `src/sase/llm_provider/launch_selection.py`. Whenever a user invokes an agent with `@small`, `@medium`, or `@large`, send an asynchronous background query to Jev to predict what tier it would have selected.
- **Success Criteria:** Measure Jev's agreement rate against actual human-selected tiers across 500+ turns. Verify that p95 API latency is reliably under 300 ms.

### Phase 2: Opt-In `%model auto` (Gated behind Feature Flag)
- **Objective:** Allow developers to explicitly opt into automated routing.
- **Action:** Introduce feature flag `flag:jev_model_routing` and the model alias `@auto`. When active, SASE evaluates prompts using the `resolve_adaptive_tier` function.
- **Success Criteria:** Zero agent launch failures attributable to Jev timeouts (100% fail-open reliability); measurable reduction in workspace token expenditure without an increase in failed agent turns.

### Phase 3: Lumberjack Chop Task Bead Enrichment
- **Objective:** Assist in background backlog grooming.
- **Action:** Implement a specialized chop `sase chop bead-enrichment` that scans open, uncorroborated task beads, uses Jev to calculate duplicate probabilities against the bead index, and appends advisory notes (`sase bead note <id> "JEV-ADVISORY: Potential duplicate of sase-x9 (prob: 0.88)"`).
- **Success Criteria:** Human operators confirm high precision (>85%) on duplicate suggestions during triage gate reviews.

---

## 8. Summary & Final Recommendation

| Question | Assessment |
|---|---|
| **Is Jev a good idea in general?** | **Yes, for high-frequency routing, classification, and scoring.** Its sub-200 ms latency and $0.042/M token pricing make it exceptionally efficient compared to traditional LLMs. |
| **Is Jev a good fit for SASE's core engine?** | **No.** SASE relies on deterministic git witnesses, hermetic Rust state, and human-settled goals. Jev cannot replace test triage, finalizers, or verification proofs. |
| **What is the best way to implement it?** | As a **decoupled, fail-open advisory service in Python**, scoped specifically to **fast-path model routing (`%model auto`)** and **asynchronous bead triage enrichment**. |
| **Immediate Next Step:** | Do not write code immediately. Deploy a shadow evaluation logger (Phase 1) to collect an empirical corpus, ensuring compliance with `decisions:corpus-before-mechanism`. |
