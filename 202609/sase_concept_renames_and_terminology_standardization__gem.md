# SASE Concept Terminology: Critique of Recent Renames and Recommendations for Industry Standardization

**Author:** Researcher `gem` (Independent Research Swarm)  
**Date:** September 2026  
**Context:** SASE Architecture & Terminology Evolution (Referenced in Epic `sase-17m`, Agent `0qi`, and System Memory)

---

## 1. Executive Summary

Historically, SASE (Structured Agentic Software Engineering) developed a rich tapestry of bespoke, colloquial, and whimsical metaphors to describe its operational and agentic primitives. These included:
- **Forestry / Woodcutting:** `axe` (scheduler), `lumberjacks` (scheduled loops), `chops` (scheduled jobs).
- **Kinship / Anthropology:** `agent family` (sequential agent session), `agent clan` (parallel agent group), `agent tribe` (cross-cutting tag/label), `agent hood` (dotted prefix namespace), `agent neighbor` (co-namespaced agent).
- **Textiles / Sewing:** `patch` (unit of change / PR), `stitch` (incremental commit / revision).
- **Arachnid / Biology:** `memory web` (keyed note collection), `memory strand` (individual topic note).
- **Unix Overloading:** `sase shell` (agent / gate / monitor execution turn), `sase pipe` (turn handoff to successor agent), `task` (durable OS process, colliding with task beads).

Recently, the SASE project has embarked on a systematic campaign to retire these esoteric metaphors in favor of terminology standard across modern artificial intelligence, cloud systems, and software engineering. Notable completions include:
- `axe` → **`scheduler`**
- `lumberjacks` → **`routines`**
- `chops` → **`jobs`**
- `ace` → **`tui`**

Currently underway are two pivotal renames:
- `agent families` → **`agent sessions`** (Epic `sase-17m`)
- `sase shells` → **`sase turns`** (Agent `0qi`)

This research provides an independent critique of both the completed and in-flight renames, analyzes their impact on developer cognitive load and LLM prompt grounding, and performs a comprehensive audit of the remaining SASE taxonomy. We show that while the current renames are outstanding improvements, the departure from the "kinship" metaphor has left concepts like `agent tribe`, `agent clan`, and `agent hood` as orphaned, confusing remnants. Furthermore, metaphors like `sase pipe`, `stitch`, and `memory strand` continue to impose unnecessary translation penalties. We conclude with a detailed critique and a prioritized roadmap of recommended new renames.

---

## 2. In-Depth Critique of Implemented Renames

### 2.1 `axe` → `scheduler`
- **Former Metaphor:** "AXE" served both as a loose acronym (Automated eXecution Engine) and as the central tool in the forestry metaphor (the axe that chops wood).
- **Industry Norm:** Operating systems, distributed task systems, and batch frameworks (Unix `cron`, APScheduler, Airflow Scheduler, Kubernetes CronJob controller) universally use **scheduler** to denote a long-running supervisor that periodically evaluates and executes automation.
- **Evaluation:**
  - **Strengths:** Eliminates a completely opaque proper noun. When an operator observes `sase scheduler status` or sees the process in `systemd`/`launchd`, its responsibility is immediately obvious without consulting a domain glossary.
  - **Nuances & Edge Cases:** In SASE, the scheduler lives as a supervised service proc under the `sase service` host process. A slight point of cognitive disambiguation is required between the *background automation scheduler* (which runs jobs on fixed intervals) and the *agent runner admission queue* (`%queue`, which manages worker capacity and concurrency limits for agent launches). SASE documentation and TUI have cleanly addressed this by placing background automation under the Services tab and reserving the term "admission queue" for agent capacity.
  - **Verdict:** Highly successful, unambiguous, and overdue.

### 2.2 `lumberjacks` → `routines`
- **Former Metaphor:** "Lumberjack" represented the independent worker process that executed chops on a schedule.
- **Industry Norm:** Periodic process supervisors typically speak of **loops**, **workers**, **daemons**, **schedules**, or **cron runners**.
- **Evaluation:**
  - **Strengths:** "Routine" successfully discards the folksy folklore and conveys recurring, predictable maintenance ("scheduled routines", "health routine").
  - **Critique & Lingering Weaknesses:** In computer science, "routine" is historically overloaded as a synonym for subroutine/function (e.g., Fortran subroutines, Go goroutines). Furthermore, as noted in prior SASE research (`scheduler_loop_naming_reassessment.md`), what SASE calls a routine is literally an *independently supervised operating system process* running a periodic loop. Calling a separate OS process a "routine" can mildly understate its isolation boundary. However, in user-facing configuration (`sase.yml`) and TUI displays ("Scheduled Routines"), the phrase "routine" functions well enough as a high-level grouping of jobs.
  - **Verdict:** Strong improvement over "lumberjack", though "scheduler loop" or "runner" would have been marginally more technically precise for a supervised process.

### 2.3 `chops` → `jobs`
- **Former Metaphor:** "Chop" was the atomic unit of work cut by a lumberjack, also reflecting personal historical repository branding (`bugyi-chops`).
- **Industry Norm:** Discrete executable units of automated or batch work are universally called **jobs** (Unix cron jobs, Slurm jobs, CI/CD jobs, Kubernetes Jobs).
- **Evaluation:**
  - **Strengths:** "Job" is the absolute standard. Terms like `job timeout`, `job cadence`, `job status`, and `job run` are universally understood by any software engineer or DevOps practitioner without explanation.
  - **Nuances:** The only minor friction is ensuring developers distinguish between a *scheduler job* (a short, script-only maintenance automation) and a *task bead* (an issue/ticket tracking human or agent development work). SASE handles this well by prefixing references as `job:<routine>/<name>`.
  - **Verdict:** Flawless rename. Completely removes esoteric jargon.

### 2.4 `ace` → `tui`
- **Former Metaphor:** "ACE" stood for Autonomous / Agent Coding Environment or Agent Control Environment.
- **Industry Norm:** Terminal-based user interfaces built with libraries like Textual, Ratatui, or Blessings are universally designated as **TUIs** (e.g., `lazygit`, `tig`, `gh dash`, `bottom`).
- **Evaluation:**
  - **Strengths:** Previously, `sase ace` was a confusing command: did it start an agent? Did it launch a daemon? Did it enter an IDE? Renaming the command to `sase tui` and referring to the visual interface as the "TUI" makes its exact scope and technology obvious. It also allowed internal components to decouple the Textual presentation layer from backend agent orchestration.
  - **Verdict:** Excellent, grounded, and eliminates false grandiosity.

---

## 3. In-Depth Critique of In-Progress Renames

### 3.1 `agent families` → `agent sessions` (Epic `sase-17m`)
- **Former Metaphor:** Anthropological kinship. An "agent family" represented a container owning a sequential chain of agent executions that share state, identity, and a workspace.
- **Why "Family" Failed:**
  1. *Structural Misalignment:* In standard English and mathematics, a "family" is an unordered set or collection of related entities (e.g., "family of fonts", "family of curves", "system of equations"). This led developers and LLMs to assume an "agent family" was a parallel group or team of agents running concurrently. In reality, SASE agent families are **strictly sequential** chains where each agent hands off to the next.
  2. *Metaphor Creep:* "Family" spawned a whole vocabulary of anthropomorphic terms ("children", "kinship", "clans", "tribes", "hoods") that obscured the underlying computational mechanics.
- **Industry Norm:** Across contemporary agentic frameworks and LLM interfaces:
  - **Claude Code / Anthropic API:** A multi-turn interaction in an ongoing workspace context is a **session**.
  - **OpenAI Assistant API:** A stateful conversation container is a **thread**; interactions within it form a **session**.
  - **Cursor / Aider / Cline / Roo Code:** An ongoing, stateful prompt-and-response loop with history retention is universally called an **agent session** or **chat session**.
- **Evaluation:**
  - **Strengths:** "Agent session" communicates precisely what the construct is: a long-lived, stateful container of sequential interactions sharing an overarching workspace and goal. It makes syntax like `%id(session=...)` and CLI commands like `sase agent session` completely natural. It also clarifies why gate turns and monitor turns can belong to a session: they are non-LLM phases within that session.
  - **Verdict:** Outstanding architectural and cognitive alignment. One of the highest-value renames in SASE.

### 3.2 `sase shells` → `sase turns` (Agent `0qi`)
- **Former Metaphor:** Borrowed computing jargon: "shell" (outer wrapper / executing member). In SASE, an agent was defined as a sequence of "shells": an `agent shell` (concrete LLM run), a `gate shell` (human decision point), or a `proc shell` (supervised command).
- **Why "Shell" Failed:**
  1. *Catastrophic Domain Collision:* In Unix/Linux systems, "shell" means `/bin/bash`, `/bin/sh`, `zsh`, a subshell, or a terminal session. Speaking of "agent shells" caused endless confusion when agents executed shell commands inside workspace directories.
  2. *Contradicted SASE's Own Architectural Decisions:* SASE's foundational Decision 3 (`single-turn-agents`) literally declares: *"A SASE agent run is one provider turn; continuation is always mechanical, never a promise to resume."* The architecture was already conceived around **turns**, yet persisted in calling the concrete execution units "shells".
- **Industry Norm:** In conversational AI, dialogue systems, multi-agent frameworks, and game theory, a single discrete execution phase where an entity takes action, emits messages/tool calls, and yields control is universally called a **turn** (e.g., user turn, assistant turn, agent turn).
- **Evaluation of Sub-Variants:**
  - **`agent turn`:** 100% standard. One LLM prompt-completion-tool execution lifecycle.
  - **`gate turn`:** Highly intuitive. In human-in-the-loop systems, the conversational/execution turn yields to the human gatekeeper; the gate is the decision turn.
  - **`monitor turn` / `proc turn`:** A minor semantic stretch from conversational dialogue, but in the context of an agent session, a long-running supervised command is a distinct execution turn.
  - **Verdict:** Essential rename that eliminates severe terminology collisions with Unix shells and harmonizes code with SASE's core architectural principle of single-turn agents.

---

## 4. Comprehensive Audit & Recommendations for New Renames

While the renames above have removed the most glaring pain points, a systematic audit of the remaining SASE concepts reveals several major areas where residual metaphors, colloquialisms, or domain collisions still create significant friction.

Below are 5 concrete areas requiring standardization, with detailed technical justifications.

---

### 4.1 Area 1: The Orphaned Kinship / Tribal Metaphor (`clan`, `tribe`, `hood`, `neighbor`)

Now that `agent family` has been renamed to `agent session`, the kinship metaphor has been formally dismantled. However, its satellite terms remain stranded in the codebase, creating a fragmented, inconsistent taxonomy.

#### Proposal 1.1: Rename `agent tribe` → `agent tag` (or `agent label`)
- **Current Definition:** *"An agent tribe is a user-facing label for related agents across clans and families. Assign a tribe at launch with `%id(tribe=<tribe>)` or `#tribe:<tribe>`... displayed with an `@` prefix."*
- **Crucial Historical Finding:** In earlier SASE history, this concept **was literally called `agent tag`**! The test file `tests/test_agent_tribe_terminology.py` exists specifically to prevent regression to tag terminology (`_TAG_IDENTIFIER_RE = re.compile(r"(?<![A-Za-z0-9])(?:agent_tags?|AgentTag...)"`). It was renamed from `tag` to `tribe` solely to align with the `family`/`clan` kinship metaphor.
- **Industry Norm:** Across tech, an arbitrary user-defined metadata label applied across entities is called a **tag** (Git tags, AWS tags, Datadog tags) or a **label** (Kubernetes labels, GitHub labels, Prometheus labels). Furthermore, in professional software engineering, anthropological tribal metaphors are increasingly discouraged in favor of clear, inclusive technical terms.
- **Justification:**
  1. The sole rationale for adopting "tribe" (kinship harmony) is now dead.
  2. Displayed with an `@` prefix (e.g., `@research`, `@frontend`), it operates identically to a tag or category label.
  3. Reverting/renaming to `agent tag` (or `agent label`) aligns with universal industry convention and simplifies the mental model.

#### Proposal 1.2: Rename `agent clan` → `agent swarm` (or `agent pool` / `agent team`)
- **Current Definition:** *"An agent clan is a named, rootless container for agents that run in parallel. Every member is named inside the clan's hood (`<clan>.<suffix>`) and declares `%clan:<clan>`; the clan name is reserved and is never itself an agent."*
- **Industry Norm:** In multi-agent AI systems, a set of agents operating concurrently in parallel toward a common objective is called an **Agent Swarm** (OpenAI Swarm, Swarm Intelligence), an **Agent Team** (CrewAI, AutoGen, ChatDev), or an **Agent Pool**.
- **Justification:**
  1. SASE already uses the word **swarm**! The user prompt itself notes: *"You are researcher gem in a 3-researcher swarm"*. The prompt directives feature `#swarm`, and xprompt has `xprompt swarm`.
  2. "Clan" has zero precedent in computer science or AI. It suggests Scottish medieval history or gaming guilds.
  3. Renaming `agent clan` to **`agent swarm`** (or **`agent team`**) would consolidate SASE's multi-agent terminology around an established AI industry term that SASE already uses colloquially.

#### Proposal 1.3: Rename `agent hood` → `agent namespace` and `agent neighbor` → `peer agent`
- **Current Definition:** *"An agent hood is a group of agents that are all named with the same `<name>.` prefix. For example, agents named `foo.bar`, `foo.baz`, and `foo.bar.1` are all apart of the same `foo` agent hood."* *"An agent neighbor is any agent that is in the same agent hood as another agent."*
- **Industry Norm:** In computer science, a hierarchical dotted prefix (`foo.bar`, `foo.baz`) defining a boundary of uniqueness and scoping is universally called a **namespace** (Kubernetes namespaces, C++ namespaces, XML/DNS namespaces, Python packages). Agents sharing a scope are **peer agents** or **co-namespaced agents**.
- **Justification:**
  1. "Hood" (colloquial shorthand for neighborhood) is jarringly informal and non-technical.
  2. A dotted prefix is the textbook definition of a namespace. Calling it an `agent namespace` immediately conveys its scoping, isolation, and hierarchical properties.
  3. "Neighbor" becomes simply a `peer agent` within the same namespace.

---

### 4.2 Area 2: The Unix Pipe Misnomer (`sase pipe` → `sase handoff`)

- **Current Definition:** `sase pipe`: *"Hand this agent's turn to the next family member and end this turn."*
- **Why "Pipe" is a Misnomer:**
  - In Unix and POSIX operating systems, a `pipe` (`|`) connects the output stream (`stdout`) of one process directly into the input stream (`stdin`) of another process running *concurrently*.
  - In SASE, `sase pipe` does NOT stream bytes between concurrent processes. Instead, it terminates the currently running agent, writes handoff metadata (`agent_meta.json`), and triggers the *next* agent turn in the sequential session chain with a successor prompt.
- **Crucial Codebase Finding:** Inside `src/sase/main/pipe_handler.py`, the core payload serialization function is literally named:
  ```python
  def _pipe_handoff_json(payload: dict[str, Any], *, agent_name: str | None, max_chain: int) -> dict[str, Any]:
  ```
  Furthermore, SASE's core instructions state: *"Only a successfully executed plan, monitor, pipe, or questions handoff is exempt..."*
- **Industry Norm:** In modern multi-agent frameworks (OpenAI Swarm, LangGraph, AutoGen, CrewAI), the mechanism where an active agent delegates execution or passes control to the next agent is universally called a **Handoff** (e.g., `agent.handoff()`).
- **Justification:**
  - `pipe` sets up false expectations of Unix streaming I/O.
  - SASE's internal code and documentation already repeatedly use the word "handoff" to describe what `pipe` does.
  - Renaming `sase pipe` → **`sase handoff`** (or `sase turn next`) aligns perfectly with contemporary multi-agent engineering standards.

---

### 4.3 Area 3: The Sewing Metaphor in VCS (`stitch` → `revision` or `commit`)

- **Current Definition:** *"A stitch is the lightweight ordered change record inside a Patch's `STITCHES:` section. Every VCS commit made through the tracked workflow has an associated numeric stitch, but a stitch need not have a commit... The `sase stitch create` command and real Git/Mercurial commits are still called commits."*
- **Industry Norm:** Stacked-diff workflows and modern VCS tools (Jujutsu `jj`, Graphite, Gerrit, Phabricator Differential, StGit) organize work into changesets/patches, where individual units are called **revisions**, **commits**, or **changes**.
- **Justification:**
  1. SASE inherited a sewing metaphor: a `Patch` is sewn together with `Stitches`. While `patch` is a standard Unix/Git term (`diff`, `patch`, `git format-patch`), `stitch` is completely idiosyncratic.
  2. SASE's own glossary strand acknowledges the confusion and tension: *"The `sase stitch create` command and real Git/Mercurial commits are still called commits."*
  3. `sase stitch` is already aliased to `sase vcs` in the CLI (`sase stitch (vcs)`).
  4. Renaming `stitch` → **`revision`** (or **`commit`**) aligns SASE with stacked-diff tooling standards (e.g., Revision 1, Revision 2a) and eliminates the need for apologies in documentation.

---

### 4.4 Area 4: The Arachnid Memory Metaphor (`memory web` & `memory strand` → `memory collection` & `memory entry`)

- **Current Definition:**
  - `memory web`: *"A memory web is a keyed note collection: one flat descriptor note plus a sibling directory of strand files."*
  - `memory strand`: *"One note inside a Memory Web, stored at `sase/memory/<web>/<slug>.md`."*
- **Industry Norm:** In knowledge management, documentation engines, and LLM agent memory architectures (MemGPT/Letta, Zep, LangChain, Notion, Obsidian):
  - A grouped set of topic documents is a **collection**, **category**, or **section**.
  - An individual topic file is an **entry**, **document**, **topic**, or **page**.
- **Justification:**
  1. The spiderweb metaphor ("web" and "strand") is poetic but unintuitive.
  2. Notice that SASE's own definitions immediately translate the metaphor into standard terms: *"A memory web is a keyed note collection"* and *"One note inside a Memory Web"*.
  3. When an architecture's own canonical documentation must immediately explain its metaphors using standard computer science terms, the metaphor is creating friction rather than clarity.
  4. Renaming `memory web` → **`memory collection`** and `memory strand` → **`memory entry`** (or `memory document`) would make SASE's memory architecture instantly self-explanatory.

---

### 4.5 Area 5: CLI Subcommand Collision (`sase proc (task)` vs `task beads`)

- **Current Issue:** In `sase --full-help`, the command inventory shows:
  ```text
  proc (task)         List, inspect, run, and kill durable procs
  bead                Lightweight git-native issue tracking (plan, phase, task)
  ```
  `task` is an active alias for `sase proc` (durable operating system processes). Meanwhile, in SASE's issue tracking system (`sase bead`), the primary unit of executable work is a **task bead** (`sase bead create -T "task(bug)"`, `sase bead ready`).
- **Confusion Caused:** A developer or agent wanting to manage tasks naturally types `sase task`, expecting to interact with work tracking, but is unexpectedly dropped into operating system background processes.
- **Recommendation:**
  1. **Deprecate the `task` alias on `sase proc`.** Reserve `proc` (or `process`) exclusively for operating system background processes.
  2. Reserve the noun **`task`** exclusively for units of software work (task beads and agent task assignments).

---

### 4.6 Area 6: Evaluative Analysis of `bead`

- **Current Status:** `sase bead` is SASE's git-backed issue tracking system, derived from Steve Yegge's `beads` project. It tracks `plan`, `phase`, and `task` tiers.
- **Analysis:**
  - Is `bead` standard in tech? No. Industry uses **issues**, **tickets**, **work items**, or **tasks**.
  - *However*, unlike `chop` or `axe` (which were shallow renames of jobs and schedulers), `bead` in SASE represents a deeply integrated, highly distinctive distributed git-native architecture (event streams in `beads/events/**`, projection to `issues.jsonl`, `SASE_BEAD` commit footers).
  - Renaming `bead` to `issue` or `ticket` would carry a massive cutover cost across hundreds of CLI surfaces, commit hooks, schema versions, and repositories, with relatively modest cognitive gain since "bead" functions effectively as a distinct proper product noun (like "Docker container" or "Git commit").
  - **Verdict:** Keep `bead` as a signature primitive of SASE, but clean up surrounding collisions (such as the `proc (task)` alias collision described above).

---

## 5. Comparative Overview: Current vs. Proposed Taxonomy

| Domain | Former / Legacy Term | Current / In-Progress Term | Status | Recommended New Term | Justification Summary |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Scheduler** | `axe` | `scheduler` | Implemented | *Retain `scheduler`* | Universal industry standard for background evaluation. |
| **Scheduler** | `lumberjacks` | `routines` | Implemented | *Retain `routines`* | Clear grouping of scheduled maintenance tasks. |
| **Scheduler** | `chops` | `jobs` | Implemented | *Retain `jobs`* | Universal standard for discrete scheduled/batch executions. |
| **Interface** | `ace` | `tui` | Implemented | *Retain `tui`* | Accurately describes the Textual terminal interface. |
| **Execution** | `agent family` | `agent session` | In Progress (`sase-17m`) | *Adopt `agent session`* | Ideal fit; represents stateful multi-turn workflow. |
| **Execution** | `sase shell` | `sase turn` | In Progress (`0qi`) | *Adopt `sase turn`* | Eliminates bash shell confusion; matches single-turn architecture. |
| **Grouping** | `agent tribe` | `agent tribe` | Stale Metaphor | **`agent tag`** (or **`agent label`**) | Restores pre-kinship term; standard for `@` user-facing labels. |
| **Grouping** | `agent clan` | `agent clan` | Stale Metaphor | **`agent swarm`** (or **`agent team`**) | Matches AI multi-agent standard and SASE's existing "swarm" usage. |
| **Scoping** | `agent hood` | `agent hood` | Stale Metaphor | **`agent namespace`** | Standard CS term for dotted prefix grouping (`foo.*`). |
| **Scoping** | `agent neighbor` | `agent neighbor` | Stale Metaphor | **`peer agent`** | Clearer technical relationship within a namespace. |
| **Control Flow** | `sase pipe` | `sase pipe` | Misnomer | **`sase handoff`** | Not a Unix byte stream; it is an agent turn handoff. |
| **VCS** | `stitch` | `stitch` | Metaphor | **`revision`** (or **`commit`**) | Standard stacked-diff term; removes awkward sewing metaphor. |
| **Memory** | `memory web` | `memory web` | Metaphor | **`memory collection`** | Matches standard knowledge base / RAG taxonomy. |
| **Memory** | `memory strand` | `memory strand` | Metaphor | **`memory entry`** (or **`doc`**) | Eliminates spiderweb jargon; self-explanatory. |
| **CLI** | `proc (task)` | `proc (task)` | Collision | **Deprecate `task` alias** | Eliminates collision between OS processes and task beads. |

---

## 6. Concluding Critique & Prioritized Recommendations

### 6.1 Brief Critique of Implemented and In-Progress Renames
1. **The Completed Renames (`axe` → `scheduler`, `chops` → `jobs`, `ace` → `tui`) were uniformly successful.** They immediately resolved ambiguity, aligned SASE with universal UNIX/systems standards, and made SASE's background architecture intuitive to any systems engineer. `lumberjacks` → `routines` was a strong improvement, effectively shedding the woodsman theme even if "routine" has slight historical overloading in CS.
2. **The In-Progress Renames (`agent families` → `agent sessions`, `sase shells` → `sase turns`) are brilliant and essential.**
   - Replacing "family" with "session" fixes the single most misleading concept in SASE: an agent family was never an unordered collection of kin, but a strictly sequential, stateful execution session.
   - Replacing "shell" with "turn" ends the constant, severe confusion between LLM provider execution cycles and Unix command-line shells (`bash`), directly aligning SASE with AI dialogue theory and SASE's own `single-turn-agents` core decision.

### 6.2 Prioritized List of New Recommended Renames

To complete the transition to a professional, industry-standard taxonomy, we recommend implementing the following new renames, prioritized by return on investment (cognitive clarity gained vs. implementation cost):

#### Tier 1: Immediate High-ROI Standardizations (Minimal code churn, high clarity)
1. **Rename `agent tribe` → `agent tag` (or `agent label`):**
   - *Why:* With `family` gone, `tribe` is an orphaned kinship relic. The concept is an `@`-prefixed label across agents. SASE previously called it `agent tag`. Restoring this terminology eliminates awkward jargon and matches GitHub/Kubernetes standards.
2. **Rename `sase pipe` → `sase handoff`:**
   - *Why:* `sase pipe` does not stream bytes between processes; it performs a sequential control-flow handoff to the next agent turn. Modern multi-agent frameworks universally call this a **handoff**, and SASE's internal code (`_pipe_handoff_json`) already uses this name.
3. **Deprecate the `task` alias on `sase proc`:**
   - *Why:* Eliminates the dangerous CLI collision where `sase task` launches process controls instead of task bead workflows.

#### Tier 2: Structural Alignment with AI & Systems Standards (Moderate scope)
4. **Rename `agent hood` → `agent namespace` (and `agent neighbor` → `peer agent`):**
   - *Why:* Replaces colloquial slang ("hood") with the universal computer science term for hierarchical dotted prefixes (`foo.*`).
5. **Rename `agent clan` → `agent swarm` (or `agent team`):**
   - *Why:* A parallel, coordinated group of agents is an agent swarm or team. SASE already uses the word "swarm" across multiple surfaces (including researcher swarms and xprompts).

#### Tier 3: Secondary Metaphor Refinements (Documentation & polish)
6. **Rename `memory web` → `memory collection` and `memory strand` → `memory entry`:**
   - *Why:* The spiderweb metaphor adds unnecessary conceptual baggage. Calling them collections and entries matches modern knowledge bases, vector stores, and memory systems.
7. **Rename `stitch` → `revision` (or `commit`):**
   - *Why:* Replaces the bespoke sewing metaphor with standard stacked-diff terminology, resolving the awkward contradiction where documentation must explain that stitches are commits.
