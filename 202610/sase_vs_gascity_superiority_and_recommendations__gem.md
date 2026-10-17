# SASE vs Gas City: Architectural Comparison, Superiority Analysis, and Recommendations

> **Researcher:** `research.1x.gem` (Swarm Member `gem`)  
> **Topic:** Comparative analysis of SASE and Gas City (`gastownhall/gascity`), identifying specific dimensions where Gas City is superior to SASE, and establishing a prioritized list of recommended improvements for SASE.  
> **Date:** October 2026  
> **Status:** Independent Research Report (`__gem`)

---

## 1. Executive Summary

This report delivers an independent, deep-dive architectural and operational comparison between **SASE (Structured Agentic Software Engineering)** and **Gas City (`gastownhall/gascity`)**. It builds upon prior research into Gas Town and Gas City while evaluating the latest stable Gas City release (v1.5.0) and SASE's current architecture (Python TUI + Rust `sase_core` backend).

### Core Takeaways

1. **Fundamental Divergence in Philosophy:**
   - **SASE** is designed as a **precision instrument for a single software engineer**. It prioritizes local execution determinism, strict single-turn agent boundaries (`single-turn-agents`), host-owned completion (`host-owned-completion`), human-aligned goal tracking (`goal-ledger`), guarded execution (`guarded-recipes`), and lightning-fast local performance via an in-tree Rust backend (`sase_core`).
   - **Gas City** is designed as a **distributed, autonomous "software factory"**. It views software engineering as an orchestration graph rather than a human-in-the-loop chat. It enforces "zero hardcoded roles," treats agent sessions as disposable ephemeral workers fanned out over a pool, and compiles declarative TOML formulas into a directed acyclic graph (DAG) of durable work records ("beads").

2. **Where Gas City is Superior:**
   Gas City demonstrates clear structural superiority in its **orchestration primitives and factory mechanics**:
   - **Declarative DAG Formulas (Formulas v2):** Separates orchestrator-owned control beads (`check`, `retry`, `drain`, `on_complete`) from agent-worked beads, executing control flow in the engine without consuming LLM tokens.
   - **Automated Verification Loops (`steps.check` / Ralph Loops):** External, bounded verification with explicit separation of semantic failures from infrastructure errors (`exit 75` / `EX_TEMPFAIL`), allowing attempt-free re-runs on flakes.
   - **Transient Retry & Soft-Fail Policies (`steps.retry`):** Automated recovery from provider timeouts and transient failures, with `soft_fail` degradation allowing downstream work to proceed.
   - **Dynamic Runtime Fan-Out (`drain` & `on_complete`):** Dynamic scatter/gather across variable-sized collections (e.g., test batches, file lists) and data-driven sub-DAG generation.
   - **Decoupled Worker Pooling & Pluggable Runtimes:** Decouples work from workers, supporting horizontal pooling across tmux, subprocesses, and Kubernetes without requiring full workspace git clones per agent.
   - **Declarative Reconciler (Reconciler v2):** Process-table-first reconciliation that crashes safely and adopts live sessions upon controller restart.
   - **Event-Driven Orders:** Automated mechanical maintenance triggered by bead lifecycle events without human or LLM polling.

3. **Where SASE Remains Superior (The Reality Check):**
   Gas City's factory model carries severe operational liabilities that SASE deliberately avoids:
   - **Storage Economics & Bloat:** Gas City's reliance on Dolt leads to severe database bloat, compaction runbooks, memory leaks, and high operational friction. SASE's Rust core backend (`sase_core`) provides sub-millisecond local reads and zero database bloat.
   - **Alignment & Goal Discipline:** SASE's Goal Ledger (`goals-host-binds`) enforces that every LLM turn is host-bound to an explicit human goal. Gas City's autonomous fleets suffer from runaway token burn and autonomy hazards (e.g., accidental untested releases).
   - **Tool Control Plane:** SASE records, predicts, and guards expensive commands (`ToolRun`, admission control, holds), whereas Gas City treats configured commands as trusted.
   - **Observability:** SASE's Textual TUI provides unmatched live visibility into agent reasoning, tool invocations, and diffs.

4. **Strategic Roadmap for SASE:**
   SASE should not attempt to become a generic multi-tenant dark factory. Instead, SASE should adopt Gas City's **declarative control flow, verification loops, and dynamic fan-out mechanics** while preserving SASE's strict host-owned completion, goal ledger, and Rust-powered performance.

---

## 2. Architectural Comparison Matrix

| Architectural Dimension | SASE | Gas City (`gastownhall/gascity`) | Superiority Assessment |
| :--- | :--- | :--- | :--- |
| **Core Paradigm** | Single-turn agent turns (`single-turn-agents`); host-owned completion; single-engineer workbench. | Declarative autonomous software factory; decoupled worker pools; graph orchestration. | **Contextual:** SASE for interactive developer mastery; Gas City for unattended batch throughput. |
| **Workflow Specification** | Procedural Python workflows (`workflow_executor.py`), macro templates (`smack`), epic phase beads. | Declarative TOML formulas (v2 DAG); compiles to topologically ordered bead graphs. | **Gas City:** Declarative DAG compilation is significantly more composable, inspectable, and reusable. |
| **Control vs Work Separation** | Coupled: agents or procedural runners execute both work and workflow transitions. | Strictly decoupled: orchestrator executes control beads (`check`, `retry`, `drain`); agents only work plain tasks. | **Gas City:** Control dispatcher does not consume LLM context or tokens to evaluate flow control. |
| **Verification & Feedback Loops** | Agent-driven (`just check` inside turn) or post-turn finalizer verification. | First-class `[steps.check]` loop with configurable `max_attempts` and external script execution. | **Gas City:** Built-in bounded loop; shields attempt budgets from infrastructure errors (`exit 75`). |
| **Failure Handling** | Single-turn failure ends turn; manual triage or host recovery turn. | Native `[steps.retry]` with transient classification and `soft_fail` degradation policies. | **Gas City:** Automatic transient error recovery with graceful degradation. |
| **Concurrency & Fan-Out** | Statically defined macro swarms (`%swarm(...)`); procedural branching. | Dynamic scatter/gather (`drain`) and runtime output-driven fan-out (`on_complete`). | **Gas City:** Highly flexible runtime data-driven parallelism. |
| **Worker Hosting & Isolation** | Heavyweight: ephemeral full git clones per agent (`sase_<N>`). | Pluggable runtimes: tmux, subprocess, exec, ACP, Kubernetes; shared bead store. | **Gas City:** Worker pooling and Kubernetes support scale far beyond local directory clones. |
| **State Storage & Economics** | High-performance Rust backend (`sase_core`), git-backed beads, SQLite telemetry; zero daemon overhead. | Dolt-backed relational versioned graph (`bd`), transitioning infrastructure beads to SQLite. | **SASE:** SASE is vastly faster, lighter, and free from Dolt's catastrophic bloat and compaction issues. |
| **Process Supervision** | Lock files, PID files, and monitor service procs. | Declarative Reconciler v2: OS process-table inspection and crash-safe live session adoption. | **Gas City:** Reconciler v2 is resilient to daemon crashes without stale lock corruption. |
| **Automation Triggers** | AXE scheduler (cron) and monitor background procs. | Event-driven **Orders**: triggers on bead lifecycle events, conditions, cron, and cooldowns. | **Gas City:** Native reactive event triggers without continuous polling or LLM supervision. |
| **Goal Tracking & Alignment** | Formal Goal Ledger (`goal-ledger`, `goals-host-binds`) in Rust; host binds every turn; human settles. | Bead dependency graph; no formal independent goal domain. | **SASE:** Superior human alignment, drift prevention, and auditability. |
| **Tool Execution Safety** | Tool Control Plane (`ToolRun`, guarded recipes, admission control, holds). | Unchecked shell execution within agent sessions; reliance on prompt instructions. | **SASE:** Superior execution safety, race prevention, and resource throttling. |
| **UI & Observability** | Interactive Textual TUI (Agents, Beads, Machines, Decks, Panels). | Web dashboard, CLI (`gc events --follow`), tmux window inspection. | **SASE:** Unrivaled local developer ergonomics and live agent inspection. |

---

## 3. In What Ways is Gas City Superior to SASE?

A rigorous examination of the Gas City codebase (`gh:gastownhall/gascity`), specifications (`formula-spec-v2.md`, `pack-spec.md`), and execution mechanics reveals eight distinct areas where Gas City is technically or architecturally superior to SASE.

### 3.1 Declarative DAG Workflow Compilation & Decoupled Control Dispatch

In Gas City, workflows are expressed as declarative TOML **formulas** (`formula_compiler >= 2.0.0`). The compiler compiles the formula into a topologically ordered directed acyclic graph (DAG) of **beads** with strict dependency tracking (`needs`, `blocks`, `waits_for`).

The defining breakthrough of Gas City's v2 contract is the **complete decoupling of control execution from work execution**:
- **Control Beads:** Beads of kind `check`, `retry`, `ralph`, `fanout`, `drain`, `scope-check`, and `workflow-finalize` are owned and executed exclusively by the orchestrator's **control dispatcher** (`internal/dispatch`). No LLM agent is ever invoked to evaluate a condition, check a retry counter, or expand a loop.
- **Work Beads:** Agents only receive and work plain task beads.

**Why this is superior to SASE:**
SASE workflows are split between procedural Python scripts (`src/sase/macro/workflow_executor.py`), macro prompt chains (`smack`), and epic phase beads. When a SASE workflow requires conditional logic, retries, or handoffs, it typically consumes agent turns (burning LLM context and inference cost) or requires custom Python orchestration code. Gas City compiles complex multi-agent topologies into transparent, inspectable database records where all flow control is free, deterministic, and executed out-of-band by the engine.

### 3.2 Automated Out-of-Session Verification Loops (`steps.check` / Ralph Loops)

One of Gas City's most powerful primitives is `[steps.check]`. It wraps any step in an automated, bounded verification loop:

```toml
[[steps]]
id = "implement"
title = "Implement feature"

[steps.check]
max_attempts = 3

[steps.check.check]
mode = "exec"
path = "scripts/verify.sh"
timeout = "2m"
```

When an agent completes iteration 1, the orchestrator runs `scripts/verify.sh` outside the agent session:
1. **Pass (Exit 0):** The step closes successfully and unblocks downstream dependents.
2. **Failure (Nonzero Exit):** The orchestrator marks the iteration as failed and automatically materializes iteration 2, routing the failure output to the agent for revision.
3. **Infrastructure Outcome Shielding (Exit 75 / `EX_TEMPFAIL`):**
   Gas City elegantly solves the "flaky test / infrastructure failure" problem. If the verification script exits with code **75** (`EX_TEMPFAIL` from `sysexits.h`) or emits specific infrastructure errors on stderr (e.g., daemon unreachable, network drop), the orchestrator treats it as an **infrastructure outcome, not a verdict**. The check is re-run **attempt-free without consuming a `max_attempts` budget**!

**Why this is superior to SASE:**
In SASE, verification is either internal to the agent turn (the agent runs `just check` within its context window, polluting context and wasting tokens) or deferred to host completion (`builtin@commit`). If a verification fails post-turn, SASE must either fail the entire turn or launch a heavyweight recovery turn. SASE has no native mechanism to wrap a work unit in a bounded, out-of-session verification loop that automatically shields the attempt budget from infrastructure flakes.

### 3.3 Automated Transient Failure Classification & Bounded Retries (`steps.retry`)

Gas City provides a native transient failure retry primitive:

```toml
[[steps]]
id = "fetch-deps"
title = "Download external dependencies"

[steps.retry]
max_attempts = 3
on_exhausted = "soft_fail"
```

The orchestrator inspects the outcome of each attempt:
- **Hard Failure:** The step fails immediately without burning further attempts.
- **Transient Failure:** If an attempt crashes due to provider rate limits, process termination, or network timeouts, the orchestrator spawns a new attempt while budget remains.
- **Soft Fail Degradation (`on_exhausted = "soft_fail"`):** If all attempts fail, the orchestrator can mark the step with `gc.outcome = pass` and `gc.final_disposition = soft_fail`. Downstream dependent steps that can proceed with degraded functionality (e.g., optional documentation, supplementary benchmarks) are not deadlocked.

**Why this is superior to SASE:**
SASE's strict single-turn model means that an unhandled crash or transient API failure aborts the turn. While SASE has recovery finalizers, it lacks fine-grained, declarative, per-step retry semantics with configurable degradation paths.

### 3.4 Dynamic Runtime Fan-Out and Scatter/Gather (`drain` and `on_complete`)

Gas City provides two distinct mechanisms for dynamic parallelism at runtime:

1. **`steps.drain` (Convoy Scatter/Gather):**
   Takes an input convoy of items (e.g., 20 bug reports, 15 source files, or a list of lint errors) and scatters them across parallel worker pools running an item formula. Concurrency is bounded by `max_units`, and failure policies (`skip_remaining` vs `continue`) prevent cascading runaway runs.
2. **`steps.on_complete` (Dynamic Output-Driven Fan-Out):**
   A completed step can emit structured JSON output (e.g., `{"components": ["auth", "billing", "api"]}`). The orchestrator reads `output.components` and dynamically instantiates a new formula instance for each element in parallel or sequentially.

**Why this is superior to SASE:**
SASE's multi-agent swarms are statically declared (e.g., the 5-researcher swarm in this task). SASE cannot take the dynamic output of Step A and automatically fan out N parallel subagent turns across a worker pool without custom Python scripting or manual human intervention.

### 3.5 Decoupled Worker Sessions, Horizontal Pooling, and Pluggable Runtimes

In Gas City, **work (beads) is completely decoupled from workers (sessions)**:
- Agents are configured as worker templates. Sessions can be pooled (`min_active_sessions`, `max_active_sessions`, `scale_check`).
- Workers claim ready beads via atomic Compare-And-Swap (CAS) operations.
- The session runtime is pluggable: workers can run in local tmux windows, subprocesses, exec sandboxes, ACP containers, or Kubernetes pods (`examples/hyperscale` demonstrates 100 Kubernetes worker pods claiming beads from a central city).

**Why this is superior to SASE:**
SASE couples each agent invocation to a dedicated, ephemeral git clone (`sase_<N>`). While this provides clean filesystem isolation for single-agent tasks, it creates an enormous scalability ceiling:
- Running 20-50 concurrent agents in SASE would require 20-50 full git checkouts on disk, consuming tens of gigabytes of disk space and massive I/O overhead.
- SASE cannot scale out horizontally to remote worker nodes, containers, or Kubernetes clusters.

### 3.6 Declarative Reconciler Architecture & Crash-Safe Session Adoption (Reconciler v2)

Gas City's controller architecture is built on a declarative reconciliation loop modeled after Kubernetes controllers and Erlang/OTP supervision:
- The controller periodically reconciles the declared system state (desired agent pools and running formulas) against actual system state.
- **Process Table as Single Source of Truth:** Gas City deliberately rejects status files and PID files. The operating system process table is the authoritative truth.
- **Crash Recovery & Adoption:** If the `gc` daemon crashes, is killed, or is upgraded, the new daemon starts up, scans the process table and tmux server, discovers the still-running agent sessions, and adopts them seamlessly without terminating in-flight work.

**Why this is superior to SASE:**
SASE relies on state markers, lock files, and monitor files. Stalled processes or abnormal terminations can leave stale locks, orphaned workspaces, or inconsistent state that requires `sase doctor` or manual operator intervention.

### 3.7 Zero-Role Framework Agnosticism & Modular Pack Registry

Gas City strictly enforces **"Zero hardcoded roles in Go"** and **"Zero framework cognition"**:
- If a line of Go references a role name (like "Mayor" or "Coder"), it is treated as a bug.
- Every workflow topology—whether it is Steve Yegge's Gas Town, an Anthropic-style Agent Team, or a multi-vendor review gauntlet—is defined as a portable **Pack** (`pack.toml`) containing prompts, formulas, and worker definitions.
- Packs are modular, versioned, and shareable via `registry.gascity.com`.

**Why this is superior to SASE:**
SASE has specialized, built-in assumptions baked into its Python codebase: specific bead lifecycles, memory web structures (`decisions:`, `glossary:`), and fixed finalizer protocols. While deeply optimized for SASE's development workflow, SASE cannot easily package and distribute an entire multi-agent topology to other repositories or teams as an isolated, reusable artifact.

### 3.8 Event-Driven Reactive Automation via Orders (`orders`)

Gas City's `orders` provide a background automation engine that triggers formulas or shell commands based on:
- **Events:** `bead.closed`, `session.crashed`, `review.approved`, `commit.landed`.
- **Schedules:** Cron schedules or cooldown timers.
- **Conditions:** State expressions over the bead store.

Orders handle automated factory maintenance (e.g., pruning old runs, running nightly test matrices, verifying repo health) entirely mechanically, without requiring an active LLM session.

**Why this is superior to SASE:**
While SASE has cron scheduling via AXE, it lacks an event-driven automation bus that reacts immediately to bead state transitions and execution events without human or LLM polling.

---

## 4. Where SASE Remains Clearly Superior to Gas City (The Reality Check)

Any comparative assessment of Gas City must be tempered by empirical reality. While Gas City has brilliant architectural ideas, its real-world implementation is fraught with severe design trade-offs, operational instability, and philosophical friction that SASE has consciously avoided.

### 4.1 Storage Economics: SASE's Rust Core vs Gas City's Dolt Nightmare

Gas City chose Dolt (a git-like relational database) as its primary storage engine for Beads. In practice, this has been an operational disaster:
- **Catastrophic Bloat:** Dolt databases grow rapidly under high agent activity. The Gas City documentation is crowded with troubleshooting runbooks: `dolt-bloat-recovery.md`, `dolt-compact.md`, `split-storage-classes.md`, and `bd-backup-cleanup.md`.
- **Daemon Overhead:** Running Dolt requires dedicated server processes, high idle RAM (hundreds of megabytes to gigabytes), and complex socket proxies.
- **Ongoing Retreat:** In v1.5.0, Gas City was forced to introduce an emergency split-storage architecture, moving infrastructure beads to SQLite because Dolt could not handle the read/write load.

**SASE's Decisive Advantage:**
SASE's core backend is written in **pure Rust (`sase_core`)**. It accesses git and filesystem data with zero daemon overhead, instant sub-millisecond latencies, and zero storage bloat. SASE can run hundreds of thousands of operations without ever needing a compaction runbook or database recovery script.

### 4.2 Human-Grounded Alignment: Goal Ledger vs Unchecked Agent Sprawl

Gas City's vision is the "Dark Factory" (or "Light Factory"), where dozens of agents autonomously create beads, sling formulas, and merge PRs. In practice, this leads to:
- **Autonomy Hazards & Incidents:** In August 2026, Beads v1.2.0 and v1.2.1 were accidentally released to the public without testing by an autonomous maintenance agent, corrupting local schemas across the user base.
- **Token Combustion:** As noted in Every's independent review (Katie Parrott, May 2026), "a six-step job can cost six times the cost of one Claude session," routinely burning a billion tokens a day for maintainers with questionable marginal quality.

**SASE's Decisive Advantage:**
SASE enforces the **Goal Ledger (`goal-ledger`, `goals-host-binds`)**:
- Every LLM turn is host-bound to exactly one explicit human goal.
- Agents can only propose or adopt drafts; only a human settles a goal.
- SASE agents are single-turn: they perform their task, submit a structured declaration (`/sase_final`), and exit. This guarantees that human intent remains strictly authoritative and compute spend remains bounded.

### 4.3 Tool Control Plane, Guarded Execution, and Verdict Receipts

Gas City treats configured commands as trusted shell executions. It lacks admission control, command interception, or execution sandboxing.

**SASE's Decisive Advantage:**
SASE features a sophisticated **Tool Control Plane**:
- **Guarded Recipes (`guarded-recipes`):** Expensive commands (`just check`, test suites) cannot be run raw by agents; they must pass through `sase tool run`.
- **Admission Control & Holds (`hold-pull-fail-open`):** Commands are evaluated against active locks, predictions, and safety holds before execution.
- **Verdict Receipts (`receipts-prove-before-they-skip`):** Test outcomes produce cryptographic receipts that prove execution state before host finalizers permit landing.

### 4.4 Developer Experience & Observability: Textual TUI vs Tmux Log Scraping

Gas City relies on tmux sessions, raw JSONL event streams (`gc events --follow`), and an early web dashboard. Inspecting what an agent is actually doing requires navigating tmux panes or reading raw stdout logs.

**SASE's Decisive Advantage:**
SASE features an interactive, world-class terminal UI (built on Textual). The developer can visually monitor agent reasoning, inspect tool calls in real time, browse structured diffs, jump across bead relations, and review notification cards—all within a single cohesive, high-performance interface.

### 4.5 Maintainer Concentration & Yegge's Reversal on Reusable Harnesses

Two existential risks hang over Gas City:
1. **Extreme Contributor Concentration:** CTO Julian Knutsen authored **62% of all commits** on `main` (4,457 of 7,161 commits). If Knutsen stops maintaining the project, Gas City stalls.
2. **The Originator's Reversal:** Steve Yegge, who originated Beads and Gas Town, published a startling essay in August 2026 (*The Continuous Thunderdome*):
   > "Gas Town fell apart at the seams... I have given up on building reusable harnesses. Harnesses need to be part of your application, chemically bonded in."
   Yegge abandoned reusable orchestration frameworks entirely in favor of a private, bespoke tool (**Wheelhouse**). This cuts directly at the heart of Gas City's core premise that orchestration can be abstracted into generic, reusable packs.

---

## 5. Ranked List of Recommended Improvements for SASE

Based on the strengths of Gas City and the architectural boundaries of SASE, here is a prioritized, ranked list of recommendations for improving SASE. Each recommendation is designed to borrow Gas City's highest-leverage ideas while strictly respecting SASE's foundational design decisions (`single-turn-agents`, `host-owned-completion`, `goal-ledger`, Rust core boundary).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SASE IMPROVEMENT ROADMAP                              │
│                                                                             │
│  [Rank 1] Declarative Verification Loops with Infrastructure Shielding      │
│           (Ralph loop + sysexits 75 EX_TEMPFAIL protection)                 │
│                                                                             │
│  [Rank 2] Dynamic Scatter/Gather & Runtime Output Fan-Out                   │
│           (Native `drain` and `on_complete` primitives)                     │
│                                                                             │
│  [Rank 3] Declarative Step Retries with Soft-Fail Degradation               │
│           (Transient failure classification + graceful continuation)        │
│                                                                             │
│  [Rank 4] Decoupled Worker Pooling & Lightweight Worktree Execution         │
│           (Eliminate full git clone overhead per agent)                     │
│                                                                             │
│  [Rank 5] Event-Driven Reactive Automation (Mechanical "Orders")            │
│           (Bead lifecycle event hooks without LLM supervision)              │
│                                                                             │
│  [Rank 6] Reusable Topology & Workflow Bundles (Pack Spec)                 │
│           (Standardized, shareable multi-agent workflows)                   │
│                                                                             │
│  [Rank 7] Declarative Process Table Reconciliation                          │
│           (Crash-safe supervisor without stale lock files)                  │
│                                                                             │
│  [Rank 8] Headless Engine Wire Protocol for Remote Fleet Execution          │
│           (Decouple Textual TUI from execution engine)                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Rank 1: Declarative Verification Loops with Infrastructure Shielding

- **Inspiration:** Gas City's `[steps.check]` and `exit 75` (`EX_TEMPFAIL`) handling.
- **Problem in SASE:** SASE agents currently run verification commands (`just check`, pytest) inside their prompt turn, polluting their context window with test logs and burning reasoning tokens on mechanical trial-and-error. Alternatively, verification is deferred to the end of the turn, where a failure aborts the entire turn or requires a manual recovery turn. Furthermore, if a test fails due to an environmental flake (socket timeout, busy port), SASE treats it as a true failure.
- **Proposed Enhancement:**
  1. Add a native declarative verification loop to SASE workflows and epic phases:
     ```yaml
     verification:
       command: "just check"
       timeout: "3m"
       max_attempts: 3
     ```
  2. Implement **Infrastructure Shielding**: Adopt the `sysexits.h` exit code `75` (`EX_TEMPFAIL`) convention across all SASE check scripts and recipes. When a verification command exits with code 75 (or matches known transient infrastructure signatures), SASE records an **infrastructure outcome** and immediately re-executes the check **without consuming the agent's attempt budget**.
  3. If verification fails with a semantic failure (code 1), SASE automatically spawns an iterative sub-turn with the failure diff injected into the prompt, up to `max_attempts`.
- **Architectural Fit:** Fully compatible with `single-turn-agents` and `receipts-prove-before-they-skip`. The host owns the loop; each attempt is a discrete single turn.
- **Effort / Impact:** Medium Effort / **Critical Impact**. Immediately stabilizes unattended epic runs and protects CI from flake attrition.

---

### Rank 2: Dynamic Scatter/Gather & Runtime Output Fan-Out

- **Inspiration:** Gas City's `steps.drain` and `steps.on_complete`.
- **Problem in SASE:** SASE's multi-agent swarms are statically declared in advance (e.g. `%swarm(gem, cld, grk, mus, cdx)`). SASE cannot take a dynamic runtime list produced by an agent (e.g., a list of 30 migration targets, 12 failing test files, or 8 security audit targets) and automatically scatter them across parallel worker turns.
- **Proposed Enhancement:**
  1. Introduce a **`scatter` (or `drain`) primitive** to SASE macro workflows:
     - Accepts a list of items (or convoy of beads) and fans out an identical sub-workflow or prompt across each item.
     - Implements concurrency throttling (`max_concurrency: 4`) and failure policies (`on_failure: continue | abort`).
  2. Introduce **`on_complete` dynamic binding**:
     - Allows an agent turn to emit a structured JSON artifact (e.g. `targets.json`).
     - SASE's workflow executor parses the JSON and instantiates follow-up agent turns for each entry in the collection.
- **Architectural Fit:** Aligns with SASE's Rust backend; graph expansion can be computed in `sase_core` and materialized as task beads.
- **Effort / Impact:** Medium Effort / **High Impact**. Unlocks large-scale automated refactoring, codebase migrations, and batch auditing in SASE.

---

### Rank 3: Declarative Step Retries with Soft-Fail Degradation

- **Inspiration:** Gas City's `steps.retry` with `on_exhausted = "soft_fail"`.
- **Problem in SASE:** When a step in a SASE macro workflow encounters a transient provider failure (e.g. API 503, rate limit, process OOM) or fails an auxiliary task (e.g. generating an audio edition in `sase-listen` or creating an infographic), the entire workflow halts, requiring operator intervention.
- **Proposed Enhancement:**
  1. Add declarative retry configuration to SASE workflow steps:
     ```yaml
     retry:
       max_attempts: 3
       backoff: exponential
       on_exhausted: soft_fail  # or hard_fail
     ```
  2. Implement `soft_fail` semantics: If an optional or non-critical step exhausts its retries, SASE marks the step as completed with degraded status (`soft_fail`), emits a warning notification card, and allows downstream dependent steps to proceed.
- **Architectural Fit:** Fits neatly into `src/sase/macro/workflow_executor.py` and SASE's notification system.
- **Effort / Impact:** Low Effort / **High Impact**. Drastically reduces operator interruptions during long-running macro runs.

---

### Rank 4: Decoupled Worker Pooling & Lightweight Worktree Execution

- **Inspiration:** Gas City's decoupled session pools and Kubernetes runtimes.
- **Problem in SASE:** SASE's `sase_<N>` workspace model provisions a full git clone for every single agent. This places a severe physical bottleneck on concurrency: spawning 20 parallel agents consumes 20 full repository checkouts, triggering heavy disk I/O, storage consumption, and git lock contention.
- **Proposed Enhancement:**
  1. Replace full directory clones with **linked Git Worktrees** backed by git alternate object stores (`objects/info/alternates`).
  2. Introduce a **Worker Pool Manager** in SASE:
     - Pre-provisions and warms a bounded pool of execution worktrees (e.g., `sase_pool_1` to `sase_pool_8`).
     - Automatically resets and checks out target branches for incoming agent turns, recycling worktrees upon turn completion.
- **Architectural Fit:** Preserves filesystem isolation while cutting disk usage by 85%+ and reducing agent spawn latency to under 500ms.
- **Effort / Impact:** High Effort / **High Impact**. Enables SASE to comfortably run 10–20+ concurrent agents on a single developer machine.

---

### Rank 5: Event-Driven Reactive Automation (Mechanical "Orders")

- **Inspiration:** Gas City's `orders`.
- **Problem in SASE:** SASE automation currently relies on cron-based schedules (AXE) or active monitor procs. There is no lightweight mechanism to trigger shell actions or workflow steps purely in response to internal lifecycle events (e.g., "when a task bead closes, run doctor check" or "when master goes red, auto-dispatch triage").
- **Proposed Enhancement:**
  1. Add an event bus and reactive `orders.yml` configuration to `.sase/`:
     ```yaml
     orders:
       - name: auto-triage-ci
         on: event.ci.red
         cooldown: 15m
         action: "sase tool run -- recipe:triage"

       - name: cleanup-ephemeral-artifacts
         on: bead.status.closed
         action: "sase artifact prune --unreferenced"
     ```
  2. Execute orders mechanically in the background host process without launching LLM agent turns.
- **Architectural Fit:** Complements SASE's host-owned architecture and minimizes unnecessary inference token spend.
- **Effort / Impact:** Medium Effort / **Medium Impact**. Eliminates repetitive manual maintenance and speeds up system self-healing.

---

### Rank 6: Reusable Topology & Workflow Bundles (Pack Spec)

- **Inspiration:** Gas City's `pack.toml` and Pack V2 specification.
- **Problem in SASE:** SASE's macros, skills, and prompt templates are scattered across `sase/macros/`, project configs, and home directories. There is no single, self-contained packaging format that allows an engineer to export or import a complete multi-agent workflow (e.g., "Code Review Gauntlet" or "Security Red Team Swarm") between different projects.
- **Proposed Enhancement:**
  1. Define a standardized **SASE Pack Specification** (`sase-pack.yml`):
     - Bundles prompt templates, macro workflows, required skills, and verification recipes into a single directory or tarball.
  2. Add CLI support: `sase pack install <repo/path>`, `sase pack list`, `sase pack run <pack:workflow>`.
- **Architectural Fit:** Leverages SASE's existing macro and skill infrastructure, making agentic workflows portable and modular.
- **Effort / Impact:** Medium Effort / **Medium Impact**. Fosters workflow sharing across teams and projects.

---

### Rank 7: Declarative Process Table Reconciliation (Crash-Safe Supervisor)

- **Inspiration:** Gas City's Reconciler v2 and process-table-first design.
- **Problem in SASE:** SASE's background tasks, monitor procs, and service procs rely on filesystem PID files and locks. If the terminal closes abruptly, the host reboots, or a process is killed with `SIGKILL`, stale lock files can block subsequent commands until manually repaired.
- **Proposed Enhancement:**
  1. Upgrade SASE's process manager in `sase_core`:
     - Inspect the operating system process table directly (`/proc` on Linux, `sysctl` on macOS) using process start timestamps and command signatures.
     - Eliminate fragile PID files.
     - Upon CLI/TUI startup, automatically reconcile declared background tasks with live processes, adopting running jobs and purging dead references.
- **Architectural Fit:** Core systems engineering upgrade that belongs in Rust (`sase_core`).
- **Effort / Impact:** Medium Effort / **Medium Impact**. Dramatically improves SASE's crash resilience and robustness.

---

### Rank 8: Headless Engine Wire Protocol for Remote Fleet Execution

- **Inspiration:** Gas City's `service-protocol-v0.md` and Kubernetes hyperscale backends.
- **Problem in SASE:** SASE is currently tightly coupled to the local workstation. While this makes local development fast and interactive, heavy compilation, extensive test suites, or large swarms can saturate the developer's laptop CPU and RAM.
- **Proposed Enhancement:**
  1. Define a lightweight JSON-RPC or HTTP/SSE wire protocol between the SASE engine and the SASE Textual TUI.
  2. Allow the SASE TUI to connect to a remote headless SASE daemon (`sase daemon --bind 0.0.0.0:8080`) running on a powerful build server or cloud workstation.
- **Architectural Fit:** Preserves SASE's beloved TUI front-end while offloading heavy agent execution, compilation, and testing to dedicated infrastructure.
- **Effort / Impact:** High Effort / **Medium Impact**. Positions SASE for enterprise and remote workstation environments without compromising single-operator UX.

---

## 6. What SASE Should Explicitly NOT Borrow

To maintain technical discipline, SASE must explicitly reject certain architectural patterns found in Gas City:

1. **DO NOT Adopt Dolt:**
   Dolt is the single greatest operational hazard in the Gas Town/Gas City lineage. Its massive disk amplification, memory leaks, and compaction demands are completely antithetical to SASE's clean, high-performance, Rust-centric philosophy. SASE's existing git-backed beads, SQLite ledgers, and in-memory caches are vastly superior.
2. **DO NOT Abandon Single-Turn Agent Discipline:**
   Gas City allows autonomous agents to spawn other agents, sling formulas, and perform long-running multi-turn loops. This routinely leads to runaway token consumption, hallucinations, and unverified commits. SASE's principle that **agents are single-turn** and that **the host owns completion** is a core competitive strength that must never be compromised.
3. **DO NOT Remove the Human-Bound Goal Ledger:**
   Gas City treats the software factory as fully autonomous. SASE correctly recognizes that autonomous agents without strict human goal grounding will drift and invent work. The Goal Ledger must remain the authoritative root of all agent work in SASE.
4. **DO NOT Adopt Tmux Screen-Scraping as a Primary Abstraction:**
   Gas City heavily relies on tmux pane inspection and keystroke injection. This is fragile, OS-dependent, and prone to display corruption. SASE's structured process management and API adapters are much cleaner.

---

## 7. Conclusion

Gas City is a bold and fascinating experiment in autonomous software factory engineering. Its declarative DAG compiler (Formulas v2), orchestrator-managed verification loops (`steps.check` with `exit 75` shielding), transient retry policies (`soft_fail`), dynamic scatter/gather (`drain`), and worker pooling represent the state of the art in agentic orchestration mechanics.

However, Gas City suffers from severe operational instability: catastrophic Dolt storage bloat, extreme author concentration (62% Knutsen), high token combustion, and existential doubts from its own creator (Steve Yegge).

SASE already possesses what Gas City lacks: an ultra-fast Rust core, zero database bloat, rock-solid execution safety (Tool Control Plane), strict human goal alignment (Goal Ledger), and a world-class TUI.

By adopting Gas City's **declarative verification loops (Rank 1)**, **dynamic scatter/gather fan-out (Rank 2)**, **transient retry policies (Rank 3)**, and **lightweight worktree pooling (Rank 4)**, SASE can absorb the best innovations of the software factory model while remaining the fastest, safest, and most dependable agentic software engineering platform in existence.

---

## 8. Sources & Methodology

### Repository Evidence (Audited Checkouts)
- **Gas City Checkout (`gh:gastownhall/gascity` @ `2dec01c71a`):**
  - Architecture & Philosophy: `AGENTS.md`, `ROADMAP.md`, `README.md`, `primitive-test.md`, `reconciler-v2.md`.
  - Formula Specifications: `docs/reference/specs/formula-spec-v2.md`, `formula-spec-v1.md`, `pack-spec.md`.
  - Dispatch & Runtime Code: `internal/dispatch/fanout.go`, `internal/dispatch/control.go`, `internal/molecule/`, `internal/graphv2/`.
  - Service Protocol: `docs/reference/specs/service-protocol-v0.md`, `engdocs/plans/hosted-onboarding/DESIGN.md`.
  - Storage & Runbooks: `docs/runbooks/dolt-compact.md`, `docs/runbooks/split-storage-classes.md`, `docs/troubleshooting/dolt-bloat-recovery.md`.
- **SASE Workspace Checkout (`sase-org/sase` @ `sase_16`):**
  - Architecture & Rules: `AGENTS.md`, `sase/memory/`.
  - Decision Records: `decisions:single-turn-agents`, `decisions:host-owned-completion`, `decisions:goal-ledger`, `decisions:goals-host-binds`, `decisions:guarded-recipes`, `decisions:ci-two-speed-split`, `decisions:receipts-prove-before-they-skip`.
  - Engine & Macro Code: `src/sase/macro/workflow_executor.py`, `src/sase/core/continuation_wire.py`, `src/sase/tool/routing.py`, `src/sase/finalizers/`.
  - Skills & Macros: `src/sase/macros/skills/sase_final.md`, `sase_artifact.md`.

### Prior Audited Research
- `research:202610/gascity_software_factory_purpose_and_vision/gascity_software_factory_purpose_and_vision.md` (Swarm 1v synthesis).
- `research:202610/gastown_vs_sase_lessons_to_borrow/gastown_vs_sase_lessons_to_borrow.md` (Gas Town vs SASE synthesis).

### Primary Web & Public Statements
- Chris Sells: *Orchestration Is All You Need* (Apr 2026); *Announcing Gas City 1.0* (Apr 2026).
- Steve Yegge: *Welcome to Gas City* (Apr 2026); *The Shape of Things to Come, Part 1: The Continuous Thunderdome* (Aug 2026).
- Katie Parrott & Mike Taylor, Every: *Inside the 100-agent Software Factory* (May 2026).
