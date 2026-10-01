# SASE through the lens of OpenAI's “Harness engineering”

## Executive assessment

SASE is already a serious agent harness, not a thin launcher. Against the practices in
OpenAI's February 2026 [“Harness engineering: leveraging Codex in an agent-first
world”](https://openai.com/index/harness-engineering/), its strongest areas are isolated
workspaces, durable state outside chat, explicit human gates, long-running work,
recorded verification, automated review primitives, and high-throughput test
infrastructure. In several of these areas—especially auditable handoffs, multi-provider
coordination, and host-owned completion—SASE is more rigorous than the case study.

The main gap is that SASE has optimized the **control plane around agents** more than the
**environment in which an agent understands and validates the product**. OpenAI's core
lesson was not merely “run more agents”; it was to make the application, architecture,
documentation, UI, logs, metrics, and feedback loops directly legible and operable by
agents. SASE does this well for SASE's own orchestration state, but does not yet make the
same contract easy or mandatory for every repository it manages.

My bottom line: SASE is strong harness infrastructure with a growing legibility tax. It
would benefit more from consolidation, explicit application-harness contracts, and
outcome measurement than from additional orchestration concepts.

## Scope and method

This critique compares the article's reported practices with the SASE repository at
commit `ebf070e16ae0b24bf889d582c574d01752bb6d54` (2026-10-01). I inspected the root
agent instructions, architecture and development documentation, project configuration,
workspace/provider boundaries, scheduler, mentors, ToolRuns, telemetry/statistics,
finalizers, CI workflows, visual testing, and relevant repository-scale indicators.

The article is an experience report from one product team, not a universal standard.
Two of its choices should not be cargo-culted:

- “No manually-written code” was an experimental constraint, not evidence that human
  edits are intrinsically harmful.
- Minimal blocking merge gates make sense only when correction is cheap, rollback is
  reliable, and production risk permits it.

The useful comparison is therefore whether SASE embodies the underlying principles:
agent legibility, progressive disclosure, executable constraints, fast feedback,
autonomy with bounded escalation, and continuous entropy control.

## Scorecard

| Article-derived criterion | Assessment of SASE | Short rationale |
| --- | --- | --- |
| Isolated, reproducible agent environments | **Strong** | Numbered workspace clones, atomic claims, linked-repo handling, provider abstractions, and durable recovery are first-class. |
| Durable knowledge and progressive disclosure | **Mixed–strong** | Memory notes, reference reads, artifacts, plans, beads, and architecture docs are excellent primitives, but the always-loaded instruction/catalog surface is already large and duplicated across scopes. |
| Application/UI/log/metric legibility | **Mixed** | SASE's own TUI has screenshots, visual goldens, traces, telemetry, and run logs; managed target applications have no standard boot/readiness/browser/observability contract. |
| Mechanically enforced architecture and taste | **Mixed–strong** | Ruff, mypy, Symvision, feature-flag checks, terminology checks, plan validation, file-size limits, visual tests, and the Rust-core pin are real enforcement. Python package dependency direction and domain layering are not similarly encoded. |
| Fast, trustworthy feedback loops | **Strong** | ToolRun fingerprints, stage evidence, triage, receipts, diff-scoped selection, backtests, visual lanes, and two-speed CI are unusually mature. |
| End-to-end autonomy with human escalation | **Strong** | Sessions, monitors, gates, workflows, mentors, scheduler jobs, notifications, and host-owned finalizers cover most lifecycle transitions durably. |
| Review and feedback absorption | **Mixed–strong** | Mentor agents and comment polling exist, but a standard self-driving “review until satisfied, repair CI, then land” loop is not the default project contract. |
| Entropy control / recurring gardening | **Mixed** | Storage cleanup and maintenance are strong; code/document quality gardening is available but less systematic and is not configured in this repository as a recurring quality program. |
| Human-attention and throughput optimization | **Mixed** | Parallelism, dashboards, compact ToolRun output, scoped checks, and automated handoffs help. Vocabulary, ceremony, very large manuals, and heavyweight PR CI consume attention. |
| Outcome measurement | **Mixed** | SASE records run volume, success, commits, wall time, provider usage, ToolRun cost, and pressure. It does not yet close the loop on prompt-to-merge time, human intervention, review yield, rework, or escaped defects. |

## Where SASE aligns well

### 1. It treats the harness as a product

OpenAI describes engineering effort moving from typing code to designing scaffolding,
tools, abstractions, and feedback loops. SASE clearly shares that orientation. Its
architecture is explicitly an orchestration layer whose durable state lets work be
launched, tracked, resumed, reviewed, retried, and handed off independently of one chat
(`docs/architecture.md`). The README accurately describes SASE as a coordination layer,
not a replacement for coding agents.

This is important: failures are not addressed only with a bigger prompt. SASE has
purpose-built mechanisms for missing capabilities—skills, XPrompts, workflows, gates,
monitors, tools, mentors, artifacts, and scheduler jobs. That is exactly the kind of
harness investment the article advocates.

### 2. Workspace isolation and durable continuation are excellent

The article highlights one runnable application instance per worktree. SASE provides a
strong lower-level foundation: numbered clone-per-agent workspaces, atomic claims,
deferred claims for waiting work, linked-repository materialization, cleanup of dead
claims, and persisted workflow/session state (`docs/architecture.md`,
`docs/workspace.md`).

SASE also addresses a problem the article largely elides: provider turns and human
decisions do not live forever. Monitor turns hand long commands to a supervisor; gate
turns persist a human decision without holding a provider process; successor turns can
consume the prior evidence. Host-owned finalizers inspect every repository an agent
opened and prevent successful completion from silently losing dirty work
(`docs/monitors.md`, `docs/configuration.md`, `docs/commit_workflows.md`). This is
excellent reliability engineering for autonomous work.

### 3. Verification evidence is unusually rigorous

SASE's ToolRun system is one of its best matches to the article's emphasis on feedback
loops. A named tool records stages, output, duration, host pressure, worker grants,
before/after fingerprints, toolchain versions, and typed incompleteness rather than
inventing zeroes. Failure triage distinguishes new, known, flaky, and unknown failures;
known failures require independent evidence. Receipts prove what ran without silently
skipping future execution (`docs/tool.md`).

The repository's test infrastructure is also sophisticated:

- `just check` combines whole-repository lint/validation with a measured diff-scoped
  test lane and broadening rules.
- Selection recall is backtested against coverage data.
- The fast master gate is sharded and bounded; exhaustive work is scheduled
  separately.
- Visual regressions use pinned renderers, deterministic PNG goldens, a dedicated CI
  lane, and diagnostic HTML reports.
- Timing flakes have a reproducible contention harness and a gated baseline.

This is not just “run tests.” It is a harness that observes the reliability and cost of
its own tests.

### 4. SASE makes its own UI and operations legible

The article stresses that an agent needs direct access to UI state and observability.
SASE has invested substantially in this for itself:

- `sase screenshot` captures the real TUI state an agent would see
  (`docs/ace.md`).
- The repository maintains visual snapshots and can emit replay bundles.
- TUI trace spans, startup measurements, responsiveness floors, stall logs, and heap
  diagnostics are documented (`docs/perf_runbook.md`).
- The Agents tab exposes chats, diffs, files, ToolRuns, LLM calls, finalizers, and
  failures.
- Local telemetry covers lifecycle, providers, finalizers, the scheduler, reviews,
  VCS/workspaces, gates, and ToolRuns (`docs/telemetry.md`).

The Admin Center already reports run counts, success, commits, wall time, concurrency,
provider/model use, XPrompt use, plans, and questions. That is a good base for measuring
the harness rather than relying on anecdotes.

### 5. Architecture and taste are partly encoded, not merely documented

SASE's `just lint` runs formatting, Ruff, mypy, feature-flag integrity, script
structure, test-wait policy, changelog structure, Patch/stitch terminology, unused
symbol analysis, file-size checks, and keep-sorted checks. CI validates committed plans,
generated model documentation, package builds, and the required Rust binding revision.
The Rust-core boundary has a clear litmus test in `AGENTS.md`, a pinned revision, and
binding checks with remediation text.

That is strongly aligned with the article's recommendation to enforce invariants and
give errors instructions an agent can act on. SASE is particularly good at turning
process policy—feature-flag retirement, plan validity, terminology, finalization,
repository ownership—into executable checks.

### 6. Human escalation is explicit and durable

OpenAI's target is to escalate only when judgment is required. SASE's gates are an
excellent implementation of that principle: a decision is hashed, stored, presented
through multiple clients, answered once, and connected to an exact follow-up. The agent
does not burn context or a runner slot while waiting. Typed sudo gates, plan review,
questions, launch approval, and task triage all reuse this mechanism.

Mentors similarly turn agent review into structured comments with focus, severity,
file, and line information. The scheduler waits for prerequisite hooks, kills stale
reviews when a newer commit appears, and lets a human accept only the comments worth
applying (`docs/mentors.md`).

## Where SASE falls short or is at risk

### 1. The target application is not a first-class harness capability

This is the most important gap.

SASE guarantees a code workspace, but it does not define a portable contract for:

- booting one application stack per workspace;
- allocating isolated ports, databases, queues, and credentials;
- waiting for readiness and tearing the stack down;
- navigating a UI through a browser/DOM interface;
- querying application logs, metrics, and traces;
- capturing before/after screenshots or video as completion evidence;
- expressing user journeys and service-level acceptance criteria.

Projects can assemble these pieces with named tools, `%proc`, workflows, plugins, and
custom skills, but discoverability and semantics are project-specific. By the article's
standard, anything the agent cannot inspect and drive effectively does not exist. SASE
currently makes **agent work** observable more consistently than it makes **the software
being changed** observable.

The distinction matters because most meaningful verification occurs above unit tests.
An agent can pass `just check` and still fail to prove that a user journey works, that a
service starts within its latency budget, or that a trace has no pathological span.

### 2. Progressive disclosure is being undermined by catalog growth

SASE understands the principle: core memory is always loaded, reference memory is read
on demand, and memory webs expose keyed strands. Yet the generated root `AGENTS.md` is
already 283 lines / 17,285 bytes. It includes a 24-entry decision catalog and an
always-loaded glossary catalog containing dozens of product-specific terms. In an
actual run, home-level and project-level instructions can both be injected, adding
repeated repository and finalization policy.

This is still far better than inlining every memory body, but it is drifting from a map
toward a compact encyclopedia. The cost is not only tokens. With every concept marked
important, the agent must decide among Patches, stitches, beads, plans, artifacts,
memory, webs, strands, turns, sessions, clans, tribes, hoods, gates, monitors, procs,
jobs, routines, receipts, and goals before solving the user's problem.

The documentation has the same shape. There is a good MkDocs navigation tree and a
useful `docs/architecture.md`, but the top-level documentation alone is roughly 54,900
lines. `docs/ace.md` is 9,159 lines and `docs/configuration.md` is 7,545 lines. These are
excellent references for maintainers and poor entry points for an agent deciding what
matters to one task. The root instructions route memory reads, but do not serve as a
short task-oriented map of the architecture and documentation.

### 3. Mechanical architecture enforcement is broad but not deep enough

SASE enforces many local properties, but the article's strongest architectural lesson
is about fixed layers and allowed dependency edges. I found a documented top-level
system boundary and a strongly policed Python/Rust boundary, but no comparable
machine-readable dependency model for Python domains or TUI layers.

This is consequential at current scale. The repository contains about 5,400 tracked
Python source files, with more than 2,100 under `src/sase/ace`. The `toobig` line-count
gate keeps individual files small, but file size is not cohesion or architecture. A
hard maximum can even encourage fragmentation into many narrowly named modules while
leaving dependency direction implicit. Ruff, mypy, Symvision, and unused-symbol checks
cannot answer whether `ace`, `main`, `sdd`, `finalizers`, and provider adapters depend
in the intended direction.

SASE therefore has strong **policy linting** and only partial **architecture linting**.
Its Rust boundary is the model to generalize: declare ownership and permitted edges,
then fail with a remediation path.

### 4. Documentation freshness is possible, but not yet a closed loop

The article describes indexed design knowledge, verification status, quality grades,
mechanical cross-link/freshness checks, and a recurring documentation gardener. SASE
has several ingredients:

- strict MkDocs builds;
- generated model docs;
- committed plan validation;
- immutable decision records and reference memory;
- an AXE `refresh_docs` job that can launch an update agent followed by a polish agent.

However, strict MkDocs proves that documentation builds and links resolve, not that a
claim still matches code. The `refresh_docs` job is documented as an optional routine
and is not configured in this repository's `sase/sase.yml`. There is no visible
domain-by-domain quality score, ownership/freshness metadata, or systematic check that a
doc's asserted commands, config keys, or architecture edges remain current.

The recent history shows frequent documentation work, so the problem is not neglect.
The problem is that freshness still depends heavily on remembering to update very large
manuals.

### 5. Entropy collection focuses more on runtime state than code quality

The scheduler has excellent housekeeping for stale processes, claims, temporary files,
notifications, artifact links, sidecar sync, and retention previews. It also supports
mentors, task triage, and optional documentation refresh. What is less visible is a
default recurring program that:

- grades each domain's architecture, tests, docs, and observability;
- detects duplicated helpers or parallel abstractions;
- finds obsolete compatibility paths and vocabulary;
- opens small, automatically reviewable refactors;
- measures whether the same failure pattern recurs after a harness fix.

The repository does run a file-size linter and has a `toobig_split` routine, but
splitting files is not the same as garbage-collecting concepts. The growing glossary and
large number of compatibility aliases are themselves entropy signals.

### 6. PR CI remains expensive relative to the stated throughput philosophy

SASE has explicitly adopted two-speed CI for master: a bounded per-SHA fast gate and a
scheduled exhaustive lane. That is a strong response to scarce runner capacity. Local
agents also use a scoped `just check` rather than `just check-full`.

But pull-request CI remains heavy: it builds the Rust core, runs lint and docs builds, a
three-version test matrix (with coverage), visual tests, page-group isolation,
performance floors, and a release-core-floor smoke test; the test matrix allows up to
120 minutes. This is defensible for an alpha release, but it is not the article's
minimal-blocking model. The key question is empirical: which of these jobs prevent
escapes often enough to justify their lead-time and queue cost?

SASE has the ToolRun/telemetry machinery to answer that question, but required-gate
policy is not yet visibly derived from defect yield, time-to-signal, or rollback cost.

### 7. Review automation is a capability, not yet a default closure loop

Mentors, hooks, PR comment polling, fix workflows, and finalizers are strong building
blocks. The article's operating loop is more opinionated: the implementation agent
reviews locally, requests focused peer-agent reviews, incorporates feedback, observes
CI, repairs failures, and repeats until reviewers are satisfied.

SASE can express such a workflow, but the base project configuration does not define one
canonical “definition of done” state machine for ordinary changes. Mentor profiles are
not configured in `sase/sase.yml`; user-level configuration may add them, but that means
the repository itself does not fully declare its review policy. Host-owned finalization
prevents lost edits, but it does not by itself prove product behavior or review closure.

### 8. SASE measures activity better than leverage

The Admin Center answers useful operational questions: how many runs, which providers,
success rate, commits, wall time, concurrency, skills, projects, plans, and questions.
Tool stats add stage latency, repeats, duplicate work, pressure, and failure categories.

Those metrics do not yet establish the product claim that one developer gets a better
engineering team. Missing or underemphasized measures include:

- median prompt-to-merged-change time;
- human minutes and number of interventions per accepted change;
- first-pass acceptance and reviewer defect yield;
- rework and revert rate within 1/7/30 days;
- escaped defects attributable to insufficient harness coverage;
- time lost to instructions, gates, setup, and finalizer recovery;
- harness improvements linked to before/after recurrence of a failure signature.

Without these, SASE can optimize run throughput while accidentally increasing
coordination overhead or low-value change volume.

## Actionable takeaways

### Highest priority: make the application legible, not only the agent fleet

1. **Define a repository-level application harness contract.** Add a small,
   machine-readable manifest (for example `sase/harness.yml`) with standard capabilities:
   `bootstrap`, `start`, `ready`, `stop`, `test`, `ui`, `logs`, `metrics`, `traces`, and
   `capture`. Let projects omit unsupported capabilities, but make discovery uniform.

2. **Namespace runtime resources by workspace.** Standardize port allocation, service
   names, databases, temp roots, and teardown so every numbered workspace can run a
   complete isolated stack. Expose the resolved endpoints in launch metadata.

3. **Make user journeys executable evidence.** Add a standard way to declare journeys
   and assertions that can drive a browser/TUI/API, capture before/after screenshots or
   video, and attach logs/traces to the agent result. A completion workflow should be
   able to require these artifacts for UI- or behavior-sensitive changes.

4. **Add observability adapters.** Provide capability interfaces for structured logs,
   metrics, and traces rather than prescribing one backend. The important contract is
   that the agent can query them locally and by workspace identity.

### Next: reduce context and conceptual load

5. **Set a hard budget for always-loaded instructions.** Aim for a root `AGENTS.md` of
   roughly 100–150 lines. Keep only invariants, safety rules, the architecture map, and
   routing instructions. Move the full decision list, glossary term list, task-type
   catalog, and repository inventory behind on-demand commands that can search and show
   only relevant entries.

6. **Deduplicate home/project policy at render time.** If both scopes contain identical
   memory, repository, or finalization rules, inject one canonical block with scope
   annotations rather than repeating it.

7. **Turn giant manuals into indexed domain guides.** Split `ace.md`,
   `configuration.md`, `xprompt.md`, and `llms.md` around stable task/domain boundaries.
   Give each domain an `index.md` containing purpose, public API, architecture edges,
   tests, runbooks, and “read next” links. Preserve generated reference pages for
   exhaustive field/command tables.

8. **Adopt a vocabulary budget.** Before adding a new durable noun, require evidence
   that an existing concept cannot carry the behavior. Track deprecated aliases and
   remove them on a stated horizon. Agent legibility improves when concepts shrink, not
   only when definitions become more precise.

### Encode architecture and documentation quality

9. **Create a machine-readable package dependency policy.** Declare allowed Python
   domain edges and enforce them in `just lint`, starting with high-value boundaries
   such as UI → adapter → core. Reuse the clarity of the Rust-core boundary. Every
   violation should name the forbidden edge and the intended facade.

10. **Replace file size as the primary modularity proxy.** Keep `toobig` as a warning or
    backstop, but add checks for public facade ownership, import cycles, duplicated
    helpers, and package cohesion. Review whether aggressive splitting is contributing
    to the 5,400-file source tree.

11. **Add documentation verification metadata.** For each domain guide, record owner,
    code anchors, commands/examples that can be tested, last verified revision, and
    review cadence. CI should execute snippets and validate code/config references where
    possible.

12. **Dogfood recurring doc gardening.** Configure `refresh_docs` for SASE itself, but
    make it targeted: use changed-domain ownership and code anchors, produce a stale
    claim report, and open small updates. “Polish everything” should not substitute for
    semantic verification.

13. **Publish a versioned quality scorecard.** Grade each major domain on architecture,
    test strength, docs freshness, observability, performance, and known debt. Have AXE
    update evidence and propose focused repairs. This supplies the map that a future
    agent needs more effectively than another global rule.

### Close the autonomous engineering loop

14. **Ship one canonical change lifecycle workflow.** It should reproduce the issue,
    collect baseline evidence, implement, run risk-appropriate checks, exercise declared
    journeys, request focused mentor reviews, apply accepted feedback, observe CI,
    retry/remediate bounded failures, and escalate only ambiguous judgments.

15. **Put review policy in the repository.** Configure baseline mentor profiles for
    architecture, correctness, security-sensitive diffs, and user-facing behavior in
    `sase/sase.yml`, with project-specific focus and bounded cost. User-level profiles
    can extend them but should not be the only source of review policy.

16. **Draft final declarations mechanically.** Preserve host-owned finalization, but
    reduce agent ceremony by generating a proposed manifest from the observed diff,
    opened repositories, assigned bead, and latest verification. Ask the model only for
    judgments the host cannot infer, such as the commit message or whether scope is
    genuinely complete.

17. **Link repeated failures to harness repairs.** When a failure signature crosses a
    recurrence threshold, AXE should propose a typed task: improve a tool, doc, fixture,
    architecture rule, or environment capability. Link the task to the ToolRuns and
    measure recurrence after it lands.

### Make throughput policy evidence-based

18. **Measure prompt-to-merge and human intervention.** Add first-class metrics for
    accepted changes, intervention count/time, review iterations, CI repair loops,
    reverts, and escaped bugs. Report them by project, workflow, model, and risk class.

19. **Classify gates by observed value.** For every PR job, measure time-to-signal,
    queue cost, unique defects caught, and whether the same defect would have appeared
    in the scheduled/release lane. Keep fast high-yield checks blocking; move slow
    low-yield checks to merge-queue, scheduled, or release policy only when rollback and
    risk justify it.

20. **Treat harness changes as experiments.** State a target before adding another
    mechanism—for example, “reduce median human interventions per merged change from X
    to Y”—and compare before/after cohorts. This will keep SASE focused on leverage
    rather than accumulating features that merely make orchestration more expressive.

## Final conclusion

The article's most valuable standard is that agent autonomy is an environment property,
not a model property. SASE strongly embodies this for orchestration: it gives agents
workspaces, durable state, safe continuation, evidence, review machinery, and controlled
completion. Its next step should be to extend the same rigor downward into the
application-under-change and inward into its own information architecture.

If Bryan does only three things, I would choose these:

1. establish the standard per-workspace application/observability contract;
2. cut always-loaded instructions and reorganize giant docs into verified domain maps;
3. measure human intervention and prompt-to-merge outcomes, then use those measurements
   to prune concepts and gates that do not earn their cost.

Those changes would move SASE from a powerful agent control tower toward the more
important goal described by the article: a complete engineering environment in which
agents can understand, change, validate, review, and land software with scarce human
attention spent only where judgment is genuinely needed.
