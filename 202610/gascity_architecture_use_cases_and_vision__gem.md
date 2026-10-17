# Gas City: Architecture, Use Cases, and Long-Term Vision

> **Author:** researcher gem (`research.1v.gem`)  
> **Date:** October 2026  
> **Target Repository:** `gastownhall/gascity` (GitHub: [https://github.com/gastownhall/gascity](https://github.com/gastownhall/gascity))  
> **Scope:** Independent research investigation into project origins, architecture, use cases, and strategic vision.

---

## Executive Summary

**Gas City (`gc`)** is an open-source, composable orchestration-builder Software Development Kit (SDK) and runtime written in Go, specifically designed for multi-agent software engineering workflows. Created and maintained primarily by Julian Knutsen alongside the `gastownhall` community, Gas City emerged as a clean-room architectural extraction and generalization of Steve Yegge's seminal **Gas Town** (`steveyegge/gastown`) project.

While Gas Town demonstrated the viability of running multi-agent swarms over real-world codebases, its operational roles (such as Mayor, Deacon, Polecat, Crew, Witness, and Refinery) were tightly coupled and hardwired into application code. Gas City fundamentally re-architects that foundation around a single non-negotiable principle: **ZERO hardcoded roles**. In Gas City:
- Every agent role is pure configuration (defined via TOML declarations and prompt templates within modular **Packs**).
- The Go runtime acts strictly as transport, lifecycle manager, persistence layer, and supervisor—enforcing **Zero Framework Cognition (ZFC)** by keeping all heuristic judgment calls out of Go source code.
- The platform is designed around **The Bitter Lesson**: primitives must become more useful as frontier models advance, rather than hardcoding fragile decision trees that newer models render obsolete.

At its operational core, Gas City elevates multi-agent coding from ephemeral, single-session chat interactions into a durable, fleet-scale engineering environment. It executes declarative workflows (**Formulas**) as directed acyclic graphs of persistent work units (**Beads**), fanning work out across heterogeneous agent pools, enforcing dependencies, retrying transient failures, and reconciling desired vs. actual system states through a supervisor loop.

---

## 1. Project Origins: The Transition from Gas Town to Gas City

To understand Gas City, one must understand its predecessor, Gas Town:

```
+-------------------------------------------------------------------------+
| Steve Yegge's Gas Town (github.com/steveyegge/gastown)                  |
| - Proved multi-agent orchestration on real engineering tasks            |
| - Roles hardcoded in Go: Mayor (coordinator), Deacon (watchdog), etc.   |
| - Directory-derived identity (~/gt/mayor/, ~/gt/polecat/)               |
+-------------------------------------------------------------------------+
                                    │
                                    │ Architectural Extraction & Generalization
                                    ▼
+-------------------------------------------------------------------------+
| Gas City (github.com/gastownhall/gascity)                               |
| - Clean-room Go SDK and runtime (`gc` CLI + supervisor daemon)          |
| - ZERO hardcoded roles ("If a line of Go references a role, it's a bug")|
| - Composable Six Primitives: Agent, Bead, Formula, Rig, Pack, Event     |
| - Decoupled execution: out-of-session parallel graph execution (v2)     |
+-------------------------------------------------------------------------+
```

### The Gas Town Heritage
In 2025, Steve Yegge built Gas Town to coordinate swarms of AI coding agents working on large software repositories. Gas Town introduced concepts that revolutionized agentic workflows:
- Tracking work as persistent issue-like units (**Beads**), guaranteeing that tasks survive process crashes.
- Workflow recipes (**Formulas**) that decompose complex software tasks into sequenced steps.
- Role-based specialization (e.g., the Mayor planning and delegating, the Deacon monitoring agent stalls, ephemeral Polecats executing in isolated git worktrees).

### The Inherent Friction of Gas Town
Despite its power, Gas Town suffered from architectural rigidity:
1. **Hardcoded Role Types:** Role names and behaviors were baked directly into Go structs and control loops. Adapting the system to a different organizational topology required modifying and recompiling the Go codebase.
2. **Path-Derived Identity:** Agent identities and privileges were inferred from specific filesystem directory paths (e.g., `~/gt/mayor/`).
3. **In-Session Orchestration (v1):** Orchestration was tightly coupled to single interactive sessions, limiting parallel throughput and automated unattended fleet operations.

### The Gas City Insight
Steve Yegge and Julian Knutsen realized that the underlying mechanisms—Beads, Formulas, Convoys, and Supervision—were role-agnostic. Gas City was built from scratch to separate the **infrastructure substrate** from the **behavioral configuration**:
- Gas Town itself becomes merely one configuration **Pack** among many.
- The Go core provides generic primitives; prompt templates and TOML configuration define what agents do.
- Workflows run independently of user terminal sessions, managed by an Erlang/OTP-inspired controller.

---

## 2. Core Architecture: The Six Primitives

Gas City models all multi-agent software engineering through **six user-facing primitives**, supported by a three-layer code substrate:

| Primitive | Role | Definition | Underlying Code Substrate |
| :--- | :--- | :--- | :--- |
| **Agent** | **WHO** | A configured worker defined by name, provider, prompt template, and scope. | `internal/session/` + `internal/runtime/` + `internal/agent/` |
| **Bead** | **WHAT** | The universal unit of work and domain persistence (tasks, mail, convoys, waits). | `internal/beads/` (Dolt `bd` store, SQLite, FileStore) |
| **Formula** | **HOW** | A reusable, written-down workflow method compiled into an executable dependency graph. | `internal/formula/` + `internal/dispatch/` + `internal/orders/` |
| **Rig** | **WHERE** | An external project directory (typically a Git repository) registered with the city. | `internal/config/` (Rig scopes, bead namespace isolation) |
| **Pack** | **CONFIGURES** | The portable unit of configuration packaging agents, formulas, orders, and prompts. | `internal/config/` (`pack.toml`, `city.toml`) |
| **Event** | **OBSERVE** | An immutable, monotonically sequenced outbound notification stream. | `internal/events/` (`.gc/events.jsonl`, SSE, HTTP API) |

```
                              ┌─────────────────────────┐
                              │          PACK           │
                              │ (Declares configuration)│
                              └───────────┬─────────────┘
                                          │
                  ┌───────────────────────┼───────────────────────┐
                  ▼                       ▼                       ▼
         ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
         │      AGENT      │    │     FORMULA      │    │      ORDER      │
         │   (Prompt/WHO)  │    │   (Workflow/HOW) │    │  (Schedule/WHEN)│
         └────────┬────────┘    └─────────┬────────┘    └────────┬────────┘
                  │                       │                      │
                  │ fans out              │ compiles into        │ triggers
                  ▼                       ▼                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                           BEAD STORE (WHAT)                               │
│  - Convoys (batch tracking)       - Tasks & Epics (work units)            │
│  - Control Beads (gate/drain)     - Inter-agent Mail & Session Waits      │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │ executes within
                                      ▼
                        ┌───────────────────────────┐
                        │        RIG (WHERE)        │
                        │ (Git Repo / Bead Prefix)  │
                        └─────────────┬─────────────┘
                                      │ emits activity
                                      ▼
                        ┌───────────────────────────┐
                        │      EVENT BUS (OBSERVE)  │
                        │  (Append-only JSONL / SSE)│
                        └───────────────────────────┘
```

### Detailed Breakdown of Primitives

### 1. Agent (WHO)
An Agent in Gas City is pure configuration: an `agent.toml` file plus a Markdown-based prompt template (`prompt.template.md`).
- **Sessions & Disposable Runtimes:** When an agent executes, it runs as a **Session**. Sessions are disposable processes that the supervisor can start, stop, restart, or adopt after crashes.
- **Worker Pools:** Agents can be scaled dynamically into elastic pools (`[agent.pool]`) based on demand queries (`scale_check`), maintaining a floor (`min_active_sessions`) and a ceiling (`max_active_sessions`).
- **Pluggable Providers:** Gas City abstracts runtime execution via `runtime.Provider`. Supported backends include:
  - `tmux`: Default local production session manager providing interactive terminal attachment.
  - `subprocess`: Headless local or remote execution.
  - `exec`: Scripted command runner for non-interactive jobs.
  - `acp`: Agent Client Protocol integration.
  - `k8s`: Containerized Kubernetes pods for cloud/fleet execution.
  - `herdr`: Alternative session management backend.

### 2. Bead (WHAT)
The **Bead** is the universal persistence substrate. Everything in Gas City is represented as a bead:
- Tasks, epics, bug fixes, and feature requests.
- Inter-agent mail messages (`type: "message"`).
- Ephemeral workflow instances (**Wisps**).
- Running session registrations and wait/gate markers.
- Batch containers (**Convoys**).

Because state lives in the Bead Store rather than in memory or ephemeral session transcripts, Gas City satisfies the **Non-Destructive Interaction (NDI)** principle: *if an agent session dies or crashes, all work survives intact in the store*.

### 3. Formula (HOW)
A Formula (`*.formula.toml`) defines a repeatable engineering methodology.
- **Formula v1:** Executes linearly inside a single agent session (a "molecule").
- **Formula v2 (Fleet Orchestration):** The compiler decomposes the formula into a flat dependency graph containing:
  - **Work beads:** Steps assigned to specific agents or pools.
  - **Control beads:** Orchestrator-owned primitives (check, retry, fan-out, tally, drain, scope-check, workflow-finalize).
- The controller's control dispatcher (`internal/dispatch`) executes the graph outside any user session, fanning out ready steps in parallel, holding blocked steps until dependencies close, and automatically retrying failures.

### 4. Rig (WHERE)
A Rig represents an external project directory or Git repository registered with `gc rig add <path>`.
- Rigs provide logical isolation via bead-ID prefixing (all rigs share the underlying database cluster without cross-contamination).
- Agents can be scoped globally (city-level) or instantiated per-rig (rig-level).

### 5. Pack (CONFIGURES)
Packs are modular directories containing `pack.toml`, agent definitions, formulas, orders, commands, and health checks.
- A **City** is simply the local root pack combined with a `city.toml` deployment file.
- Shared packs can be imported from remote Git repositories or a pack registry, enabling teams to share standard agent workflows.

### 6. Event (OBSERVE)
Events are immutable, append-only records with monotonically increasing sequence numbers.
- Fired whenever state changes occur (e.g., `bead.created`, `bead.closed`, `session.woke`, `session.crashed`, `order.fired`).
- Consumed reactively via HTTP Server-Sent Events (SSE) or the CLI (`gc events --follow`).
- Events close the loop: an **Order** can listen to specific event streams and trigger automated formulas in response.

---

## 3. What is Gas City Used For?

Gas City addresses the fundamental limitations of single-agent, interactive AI coding tools (e.g., Claude Code, Cursor, Aider) by enabling autonomous, asynchronous, fleet-scale software engineering.

### Primary Use Cases

#### 1. Autonomous Multi-Agent Engineering Fleets
In standard workflows, a software engineer sits in a single terminal or IDE prompt, typing instructions, waiting for output, reviewing diffs, and manually triggering the next prompt. Gas City shifts this to an unattended factory model:
- Complex engineering jobs (e.g., "Migrate API from v1 to v2 across 50 endpoints") are defined as Formulas.
- The job is slung (`gc sling`) into a Convoy.
- The orchestrator fans out parallel work items across an elastic pool of coding agents, each operating in an isolated git worktree.
- Reviewer agents audit branches; convergence loops test and retry failing builds; finalizer agents merge code once quality gates pass.

#### 2. Cross-Repository and Multi-Project Coordination
Many enterprise workflows span multiple repositories. Because a City can host multiple **Rigs**, agents can coordinate cross-cutting changes:
- An upstream SDK update in Rig A can automatically trigger an Order that runs integration tests and opens downstream PRs in Rig B and Rig C.

#### 3. Scheduled Maintenance, Health Patrol, and Housekeeping
Through **Orders** (which support cron, cooldown, event, and condition triggers), Gas City acts as an autonomous site reliability engineer (SRE) and maintainer for codebases:
- **Flaky Test Patrol:** Automatically detect failing CI tests, isolate them, and sling remediation formulas to coding agents.
- **Dependency Drift & Security Patching:** Periodically audit dependencies, bump versions, and test builds without human prompting.
- **Agent Self-Healing:** The built-in **Health Patrol** monitors agent sessions for deadlocks, silent hangs, or crashes, executing backoff restarts and publishing alerts.

#### 4. Meta-Orchestration (Custom Agent Framework Emulation)
Because Gas City provides raw infrastructure without opinionated roles, it is used to build and host other agent paradigms:
- Emulating Steve Yegge's original Gas Town topology (Mayor overseer, Deacon watchdog, Dog messaging relay).
- Running Ralph-style iterative software development loops.
- Emulating Anthropic-style Agent Teams with specialized planners, code writers, and testers.

---

## 4. Key Architectural Invariants and Philosophy

The implementation of Gas City strictly enforces several architectural invariants:

### 1. ZERO Hardcoded Roles
In `AGENTS.md`, the rule is absolute: *"If a line of Go references a specific role name, it's a bug."* No hardcoded string checks (`if role == "mayor"`) exist in the Go runtime. Role behavior exists exclusively in user-authored configuration and prompt templates.

### 2. Zero Framework Cognition (ZFC) & Keep Judgment Out of Go
Gas City maintains that Go source code must handle transport, process supervision, and persistence, but **never reasoning**:
- Heuristics like "if an agent is stuck, decide what to do next based on output text" are strictly forbidden in Go.
- Go probes liveness, checks explicit thresholds, and restarts processes. Cognitive decisions (how to fix a bug, how to decompose a plan) are delegated to the model via prompt templates.

### 3. The Primitive Test & The Bitter Lesson
Before any new primitive is accepted into the SDK, it must pass three gates:
1. **Atomicity:** Can it be decomposed into existing primitives? (If yes, it must not be a new primitive).
2. **More useful as models improve:** Does the abstraction gain value as LLMs become more capable? If an abstraction encodes heuristics that a smarter model will bypass, it is rejected.
3. **Judgment out of Go:** Does Go handle transport only, leaving judgment to the LLM?

### 4. What Gas City Deliberately Excludes
To preserve architectural purity, Gas City explicitly omits features common in other frameworks:
- **No internal skills framework:** The LLM's own context and standard CLI tools serve as the skills system.
- **No hardcoded MCP registry in Go:** If a tool has a CLI or endpoint, the agent uses it directly.
- **No capability flags:** Expressed directly via natural language prompt templates.

### 5. Object Model at the Center, Typed Wire End-to-End
All core domain logic lives in `internal/*`. Both the `gc` CLI and the HTTP/SSE API (built with Huma and OpenAPI 3.1) are strict projections over the internal object model:
- Spec is strictly generated, never hand-written.
- Wire data is fully typed; arbitrary `map[string]any` is prohibited.
- The web dashboard is a decoupled TypeScript SPA communicating with the supervisor via typed OpenAPI endpoints.

---

## 5. Long-Term Vision and Strategic Direction

Based on repository documentation, design proposals, architecture records, and roadmaps, the long-term vision for Gas City encompasses several transformative initiatives:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      GAS CITY STRATEGIC HORIZON                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. CLOUD & HOSTED PLATFORM ("Crucible" / gascity.com)                      │
│     - Flow 0: Zero-install Web Playground (live instant demo runs)          │
│     - Flow 1: CLI-driven cloud provisioning (`gc init --at gascity.com`)    │
│     - Flow 2: Anonymous & on-demand cloud execution (`gc run --at`)         │
├─────────────────────────────────────────────────────────────────────────────┤
│  2. RECONCILER V2 & EVENT-DRIVEN SCALE                                      │
│     - Replace legacy periodic tick reconciler with keyed session reconciler │
│     - Erlang/OTP-grade autonomous state convergence                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  3. DUAL-TIER STORAGE ARCHITECTURE                                          │
│     - Dolt (`bd`) for versioned, auditable work domain beads                │
│     - SQLite for ultra-high-throughput ephemeral infra beads (wisps/waits)  │
├─────────────────────────────────────────────────────────────────────────────┤
│  4. PACK ECOSYSTEM & REGISTRY                                               │
│     - `registry.gascity.com` for sharing, importing, and composing packs    │
│     - Open standard for shareable multi-agent engineering workflows         │
├─────────────────────────────────────────────────────────────────────────────┤
│  5. FLEET & CLOUD RUNTIME BACKENDS                                          │
│     - Kubernetes (`k8s`) provider for massive multi-node containerized runs │
│     - Agent Client Protocol (ACP) standardization across model vendors     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1. Hosted Gas City ("Crucible" / `gascity.com`)
A major strategic focus outlined in `engdocs/plans/hosted-onboarding/DESIGN.md` is the development of a hosted cloud platform operated alongside the open-source CLI:
- **The "Git/GitHub" Analogy:** In the same way `git` is an open-source tool with commercial hosting in GitHub, `gc` is a commercial-free open-source CLI that natively interfaces with `gascity.com`.
- **Three-Tier Onboarding Vision:**
  - **Flow 0 (Web Playground):** Zero-install entry point. Users click "Run this" on `gascity.com` to see a multi-agent formula execute in real-time on an ephemeral cloud runner.
  - **Flow 1 (`gc init --at`):** Developers provision a remote hosted city in the cloud directly from their local terminal, complete with web dashboards and managed storage.
  - **Flow 2 (`gc run --at`):** Serverless, on-demand formula execution in cloud sandboxes with managed inference.
- **Architectural Cleanliness:** The OSS `gc` binary contains zero commercial code, pricing calculations, or plan enforcement. All hosted messaging arrives as opaque server-authored strings and links, preserving open-source neutrality.

### 2. High-Performance Reconciler (Reconciler v2)
The ongoing 1.6 priority roadmap targets total session and reconciler reliability:
- Deleting the legacy periodic "tick" loop in favor of a keyed, event-driven state reconciler (`engdocs/architecture/reconciler-v2.md`).
- Ensuring that after machine reboots, daemon crashes, or network disconnects, an entire city fleet automatically reconverges to its declared configuration without human triage.

### 3. Tiered Storage Classes (Dolt + SQLite Split)
Early versions of Gas City used Dolt (`bd`) for all bead types. While Dolt provides version control, branching, and auditability, running high-frequency infrastructure bookkeeping (ephemeral wisps, session heartbeats, wait conditions, and order tracking) over Dolt created performance bottlenecks and lock contention.
- **Strategic Fix:** Gas City is transitioning to a split-tier storage model:
  - **Dolt (`bd`):** Retained for durable, versioned work beads that humans and audit trails inspect.
  - **Local SQLite:** High-throughput, low-latency engine for transient infrastructure beads.

### 4. Pack Registry & Shared Ecosystem (`packman`)
Gas City aims to become the package manager for agentic workflows:
- Establishing `registry.gascity.com` to discover, publish, and version-pin shareable Packs (`engdocs/design/packv2/doc-packman.md`).
- Enabling organizations to distribute standard company engineering procedures (e.g., standard security review packs, deployment migration packs, code generation topologies) across teams.

### 5. Multi-Node Enterprise Infrastructure (Kubernetes & ACP)
While local developers run Gas City via `tmux`, enterprise adoption demands cloud-native execution:
- Expanding the Kubernetes runtime provider (`internal/runtime/k8s`) to spawn agent sessions in isolated cloud containers.
- Deepening support for the **Agent Client Protocol (ACP)** to enable standardized communication across disparate agent harnesses and LLM providers.

---

## 6. Competitive Positioning & Comparative Analysis

An internal survey (`engdocs/research/w-gc-004-orchestration-framework-survey.md`) benchmarks Gas City against prominent multi-agent frameworks:

| Feature / Dimension | Gas City (`gc`) | AutoGen (Microsoft) | CrewAI | LangGraph | Claude Agent SDK |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Primary Language** | Go | Python | Python | Python | TypeScript / Python |
| **Role Definition** | Pure Config (TOML + Prompts) | Python Subclasses | YAML / Python strings | Python Node Functions | Config objects / Skills |
| **Hardcoded Roles** | **ZERO** (Strictly forbidden) | Yes (Code-based) | Partial | Yes (Code-based) | None |
| **Persistence Model** | **Durable Beads** (Survives crash) | In-Memory / Distributed | In-Memory | Checkpointers (Thread-level) | Local JSONL Session files |
| **Work Execution** | Out-of-session Graph Dispatch | Actor Message Exchange | Sequential / Hierarchical | Pregel State Graph | Parent-Subagent Recursion |
| **Supervision / Health** | Independent Controller Patrol | Application code | Retry limit | Resumption on checkpoint | None |
| **Framework Judgment** | **None (ZFC)** | Yes | Yes | Yes (Conditional edges) | None |

### What Gas City Uniquely Gets Right
1. **Durable Work vs. Disposable Sessions:** Most frameworks treat conversation history as the work. If an agent dies or runs out of context, the task state is endangered. Gas City separates the worker (Session) from the work (Bead). If a session crashes, the bead stays open and a fresh worker resumes it.
2. **True Role Agnosticism:** Unlike frameworks that hardcode coordinator patterns or manager-worker hierarchies in code, Gas City makes orchestration topology entirely substitutable via Packs.
3. **Decoupled Autonomous Execution:** Orchestration happens outside the user's terminal session, enabling unattended fleet automation.

### Current Trade-offs and Open Challenges
1. **Intra-Step Checkpointing:** Unlike LangGraph, which can checkpoint and resume an agent mid-tool-call, Gas City currently resumes at bead boundaries. If a session fails halfway through a tool invocation, the step bead is restarted from scratch.
2. **Infrastructure Complexity:** Running the full stack (tmux, Dolt/bd, Go daemon) requires more local system dependencies than lightweight single-package Python libraries.

---

## 7. Strategic Implications for SASE

For the SASE ecosystem, Gas City offers vital architectural lessons and potential synergies:

1. **Bead Integration:** Both SASE and Gas City leverage beads for persistent, crash-resilient task tracking. Gas City demonstrates how formulas and convoys can be built on top of beads to coordinate autonomous agent swarms.
2. **Substrate Separation:** Gas City validates the power of keeping judgment out of runtime code (ZFC) and allowing model intelligence to evolve independently of the infrastructure kernel.
3. **Packs as Standard Workflows:** SASE's skills and macro system parallel Gas City's Pack concept; establishing cross-compatibility or adopting Gas City's clean pack-composition model could enhance workflow portability.

---

## 8. Conclusion

Gas City is not just another agent coding tool; it is a **foundational multi-agent operating system and orchestration engine**. By decomposing multi-agent engineering into six atomic primitives, strictly banning hardcoded roles, enforcing zero framework cognition, and persisting all state in durable beads, Gas City provides the robust, industrial-grade plumbing needed to transition AI software development from interactive chat prompts to autonomous, scalable software factories.
