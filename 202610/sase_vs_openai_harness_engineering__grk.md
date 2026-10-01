# SASE against OpenAI harness engineering

**Researcher:** grk
**Date:** 2026-10-01
**Primary source:** Ryan Lopopolo, [Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/), OpenAI, 2026-02-11
**Related source:** OpenAI Cookbook, [Using PLANS.md for multi-hour problem solving](https://developers.openai.com/cookbook/articles/codex_exec_plans) (the ExecPlan shape the article points at)
**Scope:** Critique SASE (the product *and* the operating layer it gives other projects) against the practices that post treats as harness-engineering discipline.

## Verdict

SASE is already a serious harness. It put durable state, numbered workspaces, audited memory, host-owned commits, mechanical continuation, and a human attention surface in place before OpenAI named the job “harness engineering.” Those pieces match the article’s scarce-resource thesis: human time and attention.

The gap is *compounding*. OpenAI’s team treated every agent failure as a missing, legible, enforceable capability in the repository, then encoded taste as lints, architecture as structural tests, docs as a mechanically checked system of record, and review as an agent-to-agent loop that can finish a change overnight. SASE’s own repo still asks agents to navigate a large generated instruction file, a huge human docs site, an acknowledged import cycle, a file-size gate they are told they cannot fix, and a mentor loop that stops for a human keypress. The operating layer is strong at *supervising* agents. It is weaker at *making the next agent run cheaper than the last*.

The highest-leverage work is to treat SASE-the-codebase the way that post treats its product repo: a short map, mechanical invariants, living plans, agent-legible QA, and a garbage collector for pattern drift.

## Method

This report is independent. It uses the public OpenAI post, the ExecPlan cookbook it cites, SASE’s generated `AGENTS.md`, `docs/` (architecture, development, memory, mentors, monitors, SDD, axe, telemetry, completion, commit workflows, TUI screenshots), `sase memory list` / audited `sase memory read` of `lint_and_test.md`, `tui.md`, and `sase_beads.md`, and live measurements in this workspace (`sase_19`).

It does not consult peer swarm reports from this turn.

Scores below use four labels:

| Label | Meaning |
| --- | --- |
| **Ahead** | SASE already exceeds the article’s bar, or solved a problem the post leaves open. |
| **Aligned** | SASE practices the same idea in a recognizable form. |
| **Partial** | The pieces exist; they do not yet compound the way the article describes. |
| **Behind** | The article’s lesson is under-applied in SASE, and applying it would raise agent leverage. |
| **Divergent** | SASE chose a different design on purpose. The score comments on whether that choice still pays. |

## What the article actually claims

The post is a field report from building an internal product with “0 lines of manually-written code”: about a million lines, ~1,500 PRs, a three-to-seven person team driving Codex, throughput rising as the team grew. The scarce resource is human attention. The engineering job is therefore:

1. **Humans steer. Agents execute.** Humans specify intent, design environments, and build feedback loops. When an agent fails, the human asks “what capability is missing, and how do we make it both legible and enforceable?” rather than “try harder.”
2. **Give the agent a map, not a manual.** A ~100-line `AGENTS.md` is a table of contents. The system of record is a structured `docs/` tree (design docs, architecture, product specs, exec plans, generated schemas, quality/reliability/security notes). Progressive disclosure is mandatory because context is scarce, a giant file rots, and a blob cannot be linted.
3. **What the agent cannot see does not exist.** Google Docs, Slack, and tacit knowledge are invisible. Repository-local, versioned artifacts are the only memory that compounds.
4. **Make the running application legible.** Per-worktree bootable apps, Chrome DevTools Protocol skills, ephemeral per-worktree logs/metrics/traces (LogQL, PromQL, TraceQL), and prompts that state SLOs (“startup under 800ms”) become tractable. Single runs last six hours, often overnight.
5. **Enforce architecture and taste mechanically.** Layered domains with one-way dependencies, custom linters whose error messages *teach the fix*, parse-at-the-boundary, file-size limits, structured logging. Constraints are early prerequisites for agent speed. Human taste is captured once, then applied everywhere.
6. **Throughput changes merge philosophy.** Short-lived PRs, minimal blocking merge gates, flakes as follow-ups. Corrections are cheap; waiting is expensive. Agent-to-agent review (a Ralph Wiggum loop) drives a PR until reviewers are satisfied. Humans may review; they are not required.
7. **Plans are first-class living artifacts.** ExecPlans are self-contained, novice-guiding, outcome-focused, and kept current with Progress, Surprises, Decision Log, and Retrospective sections. Active, completed, and tech-debt plans live in-repo.
8. **Entropy needs garbage collection.** Agents copy whatever patterns already exist. Friday “AI slop” cleanup does not scale. Golden principles plus recurring cleanup agents that open small, automergeable refactors are the substitute.
9. **Autonomy is the product of the harness.** Given one prompt, the agent can reproduce a bug, record a failure video, fix, re-validate, open a PR, handle feedback, remediate CI, and merge, escalating to a human only for judgment.

The post is explicit that this behavior depends on that repository’s investment and does not generalize for free.

## Two jobs, one critique

SASE and that Codex product are different machines.

| | OpenAI post | SASE |
| --- | --- | --- |
| Object | One product repo, generated by Codex | An operating layer around many agent CLIs, plus SASE’s own large Python/Rust codebase |
| Provider | Codex | Claude, Codex, Antigravity, Qwen, OpenCode, Muse, Grok, plugins |
| Time model | Multi-hour / overnight single agent | Single-turn agents; continuation is a monitor, gate, or session member |
| Commit | Agents open, squash, and merge PRs | Host-owned `builtin@commit` / `sase stitch create`; agents declare, they do not commit |
| Human role | Encode environments and taste; optional review | Steer through TUI, gates, plan approval, mentor accept/apply, notifications |
| Knowledge | `docs/` as system of record | Generated `AGENTS.md` from memory; SDD sidecars; MkDocs `docs/` for humans |

A fair critique therefore asks two questions:

1. **As a codebase agents work in**, does `sase` itself follow harness-engineering practice?
2. **As a harness SASE gives other projects**, does it *export* those practices (maps, mechanical invariants, living plans, agent-legible QA, GC)?

SASE is stronger on (2) for *control* (workspaces, beads, gates, stitches) and weaker on both for *compounding quality* (maps, structural architecture, taste-as-code, overnight autonomy, pattern GC).

## Scorecard

| # | Article practice | SASE score | One-line evidence |
| --- | --- | --- | --- |
| 1 | Humans steer, agents execute | **Partial** | Gates, plan approval, and host-owned commits put humans on intent. A lot of SASE engineering is still implementation and review labor. |
| 2 | Failure → missing capability, made legible and enforceable | **Partial** | Decisions, skills, and custom lints exist. The default recovery is still a follow-up prompt or a task bead, not a new invariant. |
| 3 | `AGENTS.md` as ~100-line map | **Behind** | Generated `AGENTS.md` is 283 lines / ~4.3k tokens; loaded instruction context is ~5.3k tokens including home. Glossary and 24 decision blurbs are inlined. |
| 4 | Progressive disclosure | **Aligned** | Core vs reference vs memory webs, audited `sase memory read`, token dashboard. This is a real system. |
| 5 | Repository knowledge as system of record | **Partial** | Memory, SDD, beads, patches are versioned. Agent navigation goes through memory, while `docs/` is a 9k-line TUI encyclopedia plus 7.5k-line config reference with no agent map and no freshness linter. |
| 6 | Mechanical doc hygiene (linters, CI, gardening agents) | **Partial** | `sase validate` checks generated memory/skills/repo drift and plan links. No QUALITY_SCORE, no stale-doc gardener, no cross-link coverage of `docs/`. |
| 7 | What the agent cannot see does not exist | **Aligned** | Work state lives in files (`~/.sase`, sidecars, memory). Audited reads. Telegram/TUI are surfaces over that store. |
| 8 | Per-worktree isolated app | **Ahead** | Numbered workspace clones, claims, Git alternates, per-launch `TMPDIR`/`CARGO_TARGET_DIR`. More productized than “boot the app in a worktree.” |
| 9 | Drive the UI to validate | **Partial** | `sase screenshot` plus PNG goldens are a TUI analogue of CDP. Visual tests are excluded from `just check`. No CDP/Playwright skill for *user* web apps SASE orchestrates. |
| 10 | Queryable logs/metrics/traces with SLO prompts | **Behind** | Local SQLite telemetry (`sase telemetry snapshot/health`) is host-level, not per-workspace, not PromQL/LogQL, and not how agents close TUI or product bugs. |
| 11 | Multi-hour / overnight single-run autonomy | **Divergent** | `Agents Are Single-Turn` is a core decision. Monitors and sessions reconstruct long work as a chain. Six-hour uninterrupted Codex runs are outside the contract. |
| 12 | Layered architecture, mechanically enforced | **Behind** | Rust-core boundary is a documented litmus test. `docs/development.md` still admits a large `src/sase` import cycle that forces test-selection to be a bounded heuristic. No layer linter. |
| 13 | Taste invariants as lints that teach the fix | **Partial** | ruff, mypy, symvision, keep-sorted, terminology audit, `toobig` (1000/850/700). `toobig` is explicitly *not* in `just check` because “an agent can rarely act on it.” |
| 14 | Parse at the boundary | **Partial** | Rust wire contracts and typed launch plans. No project-wide “parse don’t YOLO-json” golden principle or lint. |
| 15 | Agent-to-agent review until green | **Partial** | Mentors write structured JSON and sit in tribe `@review`. A human toggles accept and presses `a`/`A` to launch apply. |
| 16 | Minimal blocking merge; corrections cheap | **Partial** | Two-speed verification (`just check` vs `just check-full`) and CI two-speed match “waiting is expensive.” Host-owned completion, receipts, and mentor gates still serialize on human attention. |
| 17 | Living exec plans with progress and decision logs | **Partial** | Tales/epics are schema-validated, executable via `sase bead work`, archived in the plans sidecar. They are not living ExecPlans (no mandated Progress / Decision Log / Retrospective updated mid-flight). |
| 18 | Entropy garbage collection (golden principles + cleanup agents) | **Behind** | AXE housekeeping GCs *runtime* (tmp, notifications, disk, stale beads). Nothing regularly scans the codebase for copied-bad-patterns and opens automergeable cleanups. |
| 19 | Agents produce the whole system (CI, docs, dashboards, tools) | **Partial** | Agents write a large fraction of SASE. Humans still own taste, architecture, and a lot of the harness itself. The “0 manual lines” constraint is not SASE’s philosophy. |
| 20 | End-to-end: reproduce, record, fix, re-validate, PR, merge | **Partial** | Epic launch + prepared completion + monitors can chain a lot of this. Recording a failure, driving the app, merging without a human, and looping review to satisfaction are incomplete. |

## Detailed critique

### 1. The engineer’s job: environments, intent, feedback loops

The article redefines engineering as scaffolding. SASE’s public story is the same sentence in different clothes: it is “the missing operating layer for coding agents,” wrapping CLIs so humans stop being air-traffic control.

That match is real:

- **Intent** is a goal (`sase goal`), a plan (`sase plan propose`), a bead, or an xprompt — all durable, all outside the chat.
- **Environment** is a numbered workspace with a claim, isolated venv, managed temp, and linked/sidecar checkouts opened through `sase repo open`.
- **Feedback** is `just check` / `sase tool run`, visual goldens, mentors, hooks, notifications, and prepared host completion.

The article’s sharper rule is the *failure protocol*. When Codex could not do a thing, the team did not retry the prompt. They added a tool, a lint, a doc, or an abstraction, and they had Codex write that addition. SASE’s failure protocol is usually a recovery successor, a `PROPOSED FOLLOW-UP` note, or a task bead. Those are good audit trails. They do not automatically become the next agent’s environment.

Evidence: `lint_and_test.md` tells agents that a `just check` pass with a `just check-full` failure is “a test-infrastructure bug, out of scope” to be filed as a task. That is honest about scope. It is also the opposite of “make the missing capability enforceable.” The selector’s import-cycle caveat in `docs/development.md` has lived long enough to be documented as a reason the fast lane is a heuristic. An OpenAI-style team would have treated that cycle as the highest-priority architecture lint.

**Take for SASE:** keep the human gates. Change the default response to agent struggle from “file a bead” to “name the missing invariant or tool, then encode it.”

### 2. Knowledge: map vs manual

OpenAI tried one giant `AGENTS.md` and listed four failure modes: context crowding, everything-is-important, instant rot, unverifiable blob. Their replacement is a ~100-line map plus a structured `docs/` system of record with design-doc indexes, `ARCHITECTURE.md`, `QUALITY_SCORE.md`, `PRODUCT_SENSE.md`, `RELIABILITY.md`, `SECURITY.md`, generated schemas, and exec-plan directories.

SASE independently invented a *better* disclosure mechanism than a pile of markdown pointers:

- Core memory is inlined and paid for on every turn.
- Reference memory is listed by one-line description and read through `sase memory read` with a reason, producing an audit event.
- Memory webs (`glossary`, `decisions`, `task_types`) keep strand bodies out of the prompt until named.
- `sase memory list` prints loaded / referenced / available / missing with approximate token counts.

That is progressive disclosure with accountability. OpenAI’s `docs/` tree does not audit which files an agent actually opened.

The always-loaded map is still too fat.

Live measurement in this workspace:

| Surface | Size |
| --- | --- |
| Project `AGENTS.md` | 283 lines, ~4,316 tokens, 17,285 bytes |
| Loaded instruction context (project + home) | 357 lines, ~5,282 tokens |
| Reference memory listed but not loaded | 12 files, including `xprompts.md` (~2,969 tokens) and `lint_and_test.md` (~2,382) |
| `docs/ace.md` | 9,159 lines |
| `docs/configuration.md` | 7,545 lines |
| `docs/xprompt.md` | 3,796 lines |

The generated `AGENTS.md` currently inlines: workspace/repo/final-declaration rules, gotchas, rust-core boundary, a 10-item reference-memory catalog, 24 decision one-liners (including superseded ones), a 60+ term glossary *index*, and the task-type catalog. The glossary strands are correctly on-demand. The index of every term is always-on. Decision *records* are on-demand; the *blurb list* is always-on.

That is the article’s “too much guidance becomes non-guidance” failure, in a milder form. Agents pattern-match the nearest rule in a 5k-token preamble instead of following a 100-line map to the one file that matters.

`docs/` is the human system of record (MkDocs). It is not the agent map. Nothing in `AGENTS.md` says “start at `docs/architecture.md`, then `docs/DESIGN.md`.” There is no `QUALITY_SCORE.md`. There is no generated `docs/generated/` schema dump. `sase validate` mechanically checks *generated* agent docs (memory init, skills, repo, plan links, prompt archive). It does not check that `docs/ace.md` still matches the TUI, or that architecture claims still match imports.

**Net:** SASE’s memory system is the right *mechanism*. The always-loaded payload and the human docs corpus still look like the encyclopedia OpenAI abandoned.

### 3. Agent legibility of the running system

The article’s most operational lesson is: once code throughput exceeds human QA, the bottleneck is whether the agent can *see the app*. They made each worktree bootable, wired CDP, and stood up an ephemeral observability stack so SLO-shaped prompts work.

SASE’s product is a TUI, so the analogue is `sase screenshot`: launch `sase tui` in tmux at 120×40, send keys, export SVG, rasterize with the same font stack as the golden PNG suite, optionally `--keep` and recapture. Visual goldens live under `tests/ace/tui/visual/snapshots/png/` with exact pixel equality. `docs/ace.md` and `lint_and_test.md` document this path. That is real application legibility, and it is more carefully pinned (fonts, color, truecolor, animations off) than a typical Playwright screenshot.

Three gaps keep it from compounding:

1. **`just check` never runs visual snapshots.** TUI-changing agents can finish a turn green on the fast lane and leave goldens stale. `just check-full` updates them locally; CI’s `visual-test` job is check-only. The article’s loop is “change, drive, observe, repeat in the same run.” SASE’s loop is “change, hope you remembered `just fix-tui-screenshots`, maybe in a monitor.”
2. **Observability is host telemetry, not worktree telemetry.** `sase telemetry` writes to `~/.sase/telemetry/metrics.sqlite`, with health thresholds (error rate, retry rate, p95). Agents can `snapshot` and `health`. They cannot query *this workspace’s* TUI event log with a PromQL-like language, and they are not prompted with SLOs such as “Agents tab refresh p95 under N ms.” `docs/perf_runbook.md` is a human runbook.
3. **The harness does not export a CDP/app-boot skill for the products SASE orchestrates.** SASE wraps coding agents that work on *other* repos, including web apps. The article’s Chrome and observability investment is exactly what those agents need. SASE ships TUI screenshots for itself and Playwright in *docs CI*, not a first-class “boot this worktree’s app and drive it” workflow for arbitrary projects.

Workspace isolation itself is ahead of the article. Numbered clones, atomic claims, Git alternates, rescue bundles, per-launch Cargo targets, and `SASE_DETACH_SCOPE` so restarting the service host does not kill agents — that is a production worktree product. OpenAI describes the app-boot half. SASE built the clone/claim/lifecycle half.

### 4. Architecture and taste, enforced

The article’s architectural claim is the one most teams postpone: strict layers (Types → Config → Repo → Service → Runtime → UI), one Provider seam for cross-cutting concerns, custom linters, structural tests. With agents, that is an *early* prerequisite because agents copy local structure at high speed.

SASE has a real boundary: shared backend belongs in `sase-core`; Python/TUI call `sase_core_rs`; presentation stays in this repo. The litmus test is in core memory. `toobig` enforces 1000/850/700 line budgets on `src` and `tests`. Symvision catches unused and misused symbols. Keep-sorted, ruff, mypy, feature-flag checks, and a terminology audit run in `just lint`.

The enforcement story then breaks in two places the article would treat as P0.

**The import cycle.** `docs/development.md` says test selection is depth-bounded because “an unbounded closure would select the vast majority of the suite because of a large import cycle in `src/sase`.” That sentence is a confession that the dependency graph is not a DAG the harness can trust. OpenAI’s layered linter exists specifically so this sentence cannot be true.

**`toobig` is a taste invariant agents are forbidden to satisfy.** The Justfile and `lint_and_test.md` are explicit: `toobig` is omitted from `just check` / `just check-full` because agents can rarely act on it; the `toobig_split` routine owns splits; CI still runs it via `just lint`. That is the article’s anti-pattern in one recipe. A constraint that is not remediable in-band trains agents to ignore it. OpenAI writes lint error messages *to inject the remediation into context*. SASE’s most structural size gate is routed around the agent.

There is no import-linter, no allowed-edge matrix, no per-domain quality grade, no “parse don’t validate” lint on external JSON. The rust-core boundary is a documented social rule plus some tests; it is not a mechanically enumerated allowed-import graph.

**Net:** SASE has taste tools. It does not yet have the *architecture compiler* the article says agents need before they can go fast without decay.

### 5. Review, merge, and the cost of waiting

OpenAI’s merge philosophy follows from throughput: short-lived PRs, few blocking gates, flakes as follow-ups, agent reviewers in a loop, humans optional, agents squash and merge.

SASE’s merge philosophy follows from auditability:

- Agents never create commits, branches, or PRs. They submit a `/sase_final` declaration. The host runs `sase stitch create` (`docs/commit_workflows.md`, decision `host-owned-completion`).
- Mentors produce structured comments; a human accepts them in the TUI and launches `make_mentor_changes` with `a` (propose) or `A` (commit) (`docs/mentors.md`).
- `just check` is the agent default; `just check-full` is explicit-only (`decisions:check-full-is-explicit`). CI is two-speed: fast per-SHA gate, exhaustive matrix off the push path (`decisions:ci-two-speed-split`).
- Prepared completion can auto-finish a green `just check` monitor without another LLM turn.

The two-speed verification lane is aligned with “waiting is expensive.” Diff-scoped tests, no queueing behind other agents, and “do not run check-full to be careful” are harness engineering.

The review loop is where SASE spends human attention the article would spend on encoding taste. Mentor comments of severity `suggestion` still need a human `Space` then `a`. There is no “loop until all agent reviewers are satisfied, then host-complete” profile. That is a coherent safety choice for a system that commits to many projects. It is also why SASE will not hit 3.5 PRs/engineer/day of *unattended* landing on its own repo.

Flakes are already modeled (`FLAKY` triage, flake baseline on check-full, `flake` task type). The article’s “address flakes with follow-up runs rather than blocking indefinitely” is partly here (`sase tool run` continues past all-KNOWN/FLAKY by default). Receipts (`receipts-prove-before-they-skip`) are *stricter* than the article, on purpose: a covering verdict is proof for host completion, not a skip of execution. That is good harness discipline. It is also more blocking.

### 6. Time: single-turn vs six hours

This is the deepest divergence.

OpenAI’s leverage story includes “single Codex runs work on a single task for upwards of six hours (often while the humans are sleeping)” and ExecPlans that keep a stateless overnight agent oriented.

SASE’s core decision `single-turn-agents` says a run is one provider turn; continuation is always mechanical. `docs/monitors.md` explains why provider-native background tools do nothing here: the turn ends, the wake-up never fires. The replacements — monitors, gates, session members, epic phase chains, prepared completion — are *more reliable* than a six-hour chat. They survive process death, they record evidence, they release runner slots during human waits.

The cost is that SASE cannot, today, offer the article’s “one prompt, go until the PR is merged” shape without a human-visible chain of turns. Epic launch is the closest: planner → approval gate → phase agents → land agent. Each hop pays context reload, instruction preamble, and the risk of local-optima between phases. ExecPlans try to make that reload cheap by stuffing the whole world into one living document. SASE plans are *launchable* (beads, sizes, deps) and *not self-contained* in the ExecPlan sense: a phase worker is expected to read AGENTS.md, memory, and skills, not to restart from the plan file alone.

Neither model is free. SASE should keep mechanical continuation (it is the correct reliability answer). It should steal ExecPlan *living sections* so a successor turn can rehydrate from the plan instead of rediscovering the design.

### 7. Entropy and garbage collection

The article’s GC story is the one SASE is furthest from.

Codex copies existing patterns, including bad ones. Humans spent Fridays (20% of the week) cleaning “AI slop.” They replaced that with golden principles (shared utilities over hand-rolled helpers; no YOLO probing of data shapes) and recurring background agents that scan, update quality grades, and open tiny automergeable refactors.

SASE’s AXE `housekeeping` lumberjack (1h) is excellent *operational* GC: error digests, notification compact, managed-tmp reap, proc runtime sweep, disk pressure, stale-bead cleanup, gate-turn reclaim, artifact-link backfill, artifact-run prune. That is how you keep `~/.sase` from eating the disk. It does not walk `src/sase` looking for duplicated helpers, Python reimplementation of rust-core, unstructured `json.loads` of external payloads, or docs that no longer match code.

The `memory` task type (“a sase memory note or skill that is out of date”) and `sase validate`’s generated-file drift checks are the seed of doc GC. They are not a scheduled gardener that opens fix-up stitches.

Given SASE’s own admission of an import cycle and a toobig backlog owned by a split routine, pattern drift is already a measured problem. There is no daily quality-grade updater.

### 8. Plans

SASE plans are operationally stronger than a markdown ExecPlan in several ways:

- Schema validation (`sase plan validate`) before proposal.
- Human approval as a durable gate.
- Epic phases with sizes, dependency edges, and `sase bead work` launch.
- Prompt archive linkage in the agents sidecar.
- Monthly directories in a plans sidecar, queryable, statused.

They are weaker as *novice-guiding living documents*:

- No mandated Progress checklist with timestamps.
- No Surprises & Discoveries.
- No Decision Log inside the plan (project `decisions` web is the ADR store, immutable, separate).
- No Outcomes & Retrospective on close.
- Phase workers append `PROPOSED FOLLOW-UP` notes to beads; they do not rewrite the plan as they learn.
- Plans live in a sidecar, which agents *can* see after `sase repo open`, but which is a second repository with its own commit obligation.

The cookbook’s bar is: a complete novice (or a stateless overnight agent) can implement from the plan file alone. SASE’s bar is: a SASE agent with the generated instruction corpus can implement a sized phase. The second bar needs the first when you want overnight autonomy or cheap successor turns.

## Where SASE already leads the article

These are not consolation prizes. They are harness pieces OpenAI’s post barely has to build because it is one team, one repo, one provider.

1. **Durable state outside the transcript.** Agent artifacts, patches, stitches, beads, goals, gates, tool runs, memory audit logs. The article’s “repository is the system of record” is necessary; SASE also records *runs*.
2. **Workspace product.** Numbered clones, claims, alternates, rescue, occupancy checks. This is the mature form of “bootable per worktree.”
3. **Audited progressive disclosure.** `sase memory read` with reasons is stricter than “the agent might open `docs/`.”
4. **Mechanical continuation.** Monitors, gates, prepared completion. Human pauses do not pin a provider process. This is how you scale attention.
5. **Multi-provider adapters.** The article is Codex-shaped. SASE’s `adapters-normalize-harnesses` decision (each provider conforms to the single-turn contract) is the harder harness problem.
6. **Host-owned commits.** The article lets agents merge. SASE’s declaration/finalizer split makes provenance and bead footers reliable. Keep this; add autonomy *above* it (auto-accept mechanical review, auto-complete green monitors).
7. **ToolRun corpus.** Named tools, duration classes, triage, receipts. This is a feedback loop the article gestures at with “use gh and local scripts” and SASE actually records.
8. **Attention UI.** Notifications, tribes, clans, the Agents tab. The article still assumes engineers live in PRs. SASE assumes many parallel agents.

## Where the article should change SASE

### A. SASE-the-codebase

The sase repo is a large, mixed-authorship Python/Rust TUI. Agents already write much of it. It does not yet behave like an agent-first repo:

- Always-loaded instructions are a 5k-token preamble, not a 100-line map.
- Architecture is documented (rust-core, content layout) and not compiled (import cycle, no layer linter).
- The harshest size invariant is invisible to the agent default recipe.
- Visual QA is opt-in.
- There is no quality scorecard per domain.
- There is no pattern-GC job.
- Plans do not accumulate mid-flight learning in the plan file.

Until those change, every new agent pays a tax the last agent already paid.

### B. SASE-as-harness for other projects

SASE can launch, isolate, review, and commit work on arbitrary projects. It does not yet *install* an OpenAI-style harness into those projects:

- No generator for a short `AGENTS.md` map + `docs/` skeleton (`ARCHITECTURE.md`, `QUALITY_SCORE.md`, `PLANS.md`, `PRODUCT_SENSE.md`).
- No optional “agent-first merge profile” (mentor loop to satisfaction → host complete → short-lived patch).
- No bundled CDP / per-worktree app-boot / LogQL skillpack for web products.
- No golden-principles AXE job that projects can enable.

`sase memory init` and `sase init` already generate agent instruction files. That is the insertion point.

### C. Divergences to keep

Do not import “0 lines of manually-written code.” SASE’s value is a trustworthy operating layer. Humans should still own goals, settle goals, answer gates that require judgment, and encode taste. The article itself says humans remain in the loop at a different layer.

Do not abandon single-turn. Make successor turns cheaper (living plans, thinner maps, receipts) so a chain *feels* like six hours without becoming an unkillable chat.

Do not let agents raw-`git commit` / `gh merge`. Keep host-owned stitches. Autonomy should mean “the host completes because evidence is sufficient,” which prepared completion already sketches.

## Actionable takeaways

Priority is leverage for the next agent run, not completeness. Each item is small enough to become a tale or an epic phase.

### P0 — make the next run cheaper

1. **Shrink generated `AGENTS.md` to a true map (~100–150 lines, budget ~1.5k tokens).** Keep: workspace/repo/final rules, rust-core litmus, “read reference memory with this command,” pointers. Move: full decision blurb list (replace with “24 records in `decisions`; read `decisions:<keyword>`”), glossary term dump (replace with “66 terms; read `glossary:<term>`”), task-type bodies (keep names + “read `task_types:<slug>`”). Measure with `sase memory list` in CI and fail if loaded tokens exceed a ratchet.

2. **Point the map at `docs/`, not only at memory.** Add a ten-line “where to look” block: architecture, development/verification, TUI, xprompts, rust backend, SDD/beads, memory. Treat `docs/architecture.md` as `ARCHITECTURE.md`. Memory stays the operational contract; docs stay the product/domain contract.

3. **Compile the rust-core and layering rules.** Add a structural import linter (even a coarse allowlist: `sase.ace` may not be imported from `sase.core`, Python must not reimplement listed `sase_core_rs` facades). Break the `src/sase` import cycle enough that `just test-scoped` can trust an unbounded reverse-import walk. Put the cycle on a quality scorecard until it is gone.

4. **Make `toobig` remediable in-band.** Either restore an agent-runnable split path (`sase tool run toobig-split` that proposes file cuts with a patch) or teach `just check` to print the exact split command and accept a “split scheduled” receipt. A lint the default recipe ignores is not a taste invariant.

5. **Close mechanical mentor loops.** For comments at `suggestion` (and optionally `warning`) on a configured profile, auto-accept and launch `make_mentor_changes` until the mentor is silent or hits a round cap, then host-complete if `just check` is green. Keep `error` and security profiles on a human gate. This is the Ralph loop the article uses, sitting on SASE’s existing mentor JSON.

### P1 — make quality compound

6. **Add `docs/QUALITY_SCORE.md` (or a generated `sase/memory` web) with a grade per domain and layer.** Start with: TUI/ACE, xprompt, beads, rust-core boundary, test selection, docs freshness, visual QA. An AXE weekly job updates grades and opens task beads for anything that dropped.

7. **Doc-gardening job.** Recurring AXE chop: sample public APIs vs `docs/cli.md` / `docs/ace.md` headings, flag files whose last meaningful code-adjacent edit is much newer than the doc, open `memory` or `docs` task beads. Reuse `sase validate`’s drift idea for non-generated docs.

8. **Living plan sections.** Extend tale/epic schema with optional `progress`, `surprises`, `decision_log`, `retrospective` (or a sibling `*.log.md`). Phase workers and land agents must append, not only bead notes. Successor turns read the log before the code. Keep SASE sizes and bead launch; steal ExecPlan *liveness*.

9. **TUI QA as a first-class verify profile.** For turns that touch ACE/pager rendering, `sase screenshot` before/after (or targeted `just fix-tui-screenshots -- <nodes>`) should be the analogue of CDP, wired into a `verify-tui` monitor profile. Do not require `just check-full` to get visual signal.

10. **Golden-principles GC.** Write five mechanical rules as lints or semgrep/ruff plugins: no new Python facade that duplicates a rust-core binding; no `json.loads` of external bytes without a schema; prefer shared helpers over third copies; file size; structured log keys. Weekly AXE agent opens one-file refactors. Automerge or host-complete when `just check` is green and the diff is under a line cap.

11. **Taste promotion path.** When a mentor comment or review stitch repeats twice, the land agent’s default is to encode it as a lint with a remediation message, not to hope the next agent reads the comment archive.

### P2 — export the harness; grow autonomy without dropping the contract

12. **`sase init harness` (name TBD) for other projects.** Generate a 100-line `AGENTS.md` map, `docs/ARCHITECTURE.md` stub, `PLANS.md` / ExecPlan pointer, `QUALITY_SCORE.md`, and a `just check` recipe hook. This is how SASE *sells* harness engineering instead of only orchestrating CLIs.

13. **Agent-first merge profile** (opt-in per project): short-lived patches, mentor Ralph loop, `just check` as the only blocker, flakes → task bead, prepared completion on green. Keep the current profile as default for `sase` itself until quality GC exists.

14. **Worktree app-boot skillpack** for web/user projects: boot command per project config, CDP or Playwright drive, ephemeral log/metric endpoints if present. SASE does not need to become a browser company; it needs a skill + project config schema so Codex-in-SASE can do what Codex-at-OpenAI does.

15. **SLO-shaped telemetry for agents.** `sase telemetry snapshot -f json` is already there. Add a documented recipe: “Agents tab refresh p95,” “launch admission wait,” “just check duration class calibration,” and a skill that treats a breached threshold as a bug with a required screenshot or trace. Per-workspace traces can wait; queryable host SLOs should not.

16. **Overnight epic mode without multi-turn chats.** A session policy: phase agent → verify monitor → auto-continue to next unblocked phase while humans sleep, escalating only on `error` mentors, failed checks, or missing judgment. Single-turn stays the atom. The chain becomes the six-hour run.

17. **Parse-don’t-validate as a golden principle.** At every process/network/file boundary, typed parse (Pydantic/msgspec/rust types). Lint YOLO `dict` poking of untrusted JSON. This is both the article’s example and a rust-core-aligned rule.

18. **Land-agent retrospective.** Epic land already closes beads. Require a short “missing capability” section: what the agents could not see or enforce, and whether a lint, skill, or doc was added. That is the article’s failure protocol, installed in the one place SASE already has a summarizer.

19. **Ratchet loaded tokens and visual coverage in CI.** Token dashboard as a budget. Visual snapshot path coverage as a grade. Treat regressions like test-cost budgets (`just test-cost`).

20. **Do not copy the zero-manual-lines constraint.** Keep humans on goals, gates that need judgment, and taste encoding. Measure success as *human minutes per landed stitch* and *repeat-failure rate for the same missing capability*, not as “agents wrote 100% of the diff.”

## Suggested first epic

If this report becomes work, the smallest epic that would move the scorecard:

| Phase | Outcome |
| --- | --- |
| `map` | Generated `AGENTS.md` under a loaded-token ratchet; docs pointer block; glossary/decision catalogs no longer inlined. |
| `layers` | Import allowlist lint + cycle break plan that makes unbounded test selection sound. |
| `toobig` | Agent-remediable size gate. |
| `mentor-loop` | Opt-in auto-apply for suggestion-level mentor comments with a round cap. |
| `garden` | QUALITY_SCORE stub + weekly AXE gardener for docs/memory drift. |

That epic is harness engineering in SASE’s own vocabulary: mechanical, durable, and aimed at the scarce resource the article named.

## Sources

- Lopopolo, Ryan. [Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/). OpenAI, 2026-02-11.
- OpenAI Cookbook. [Using PLANS.md for multi-hour problem solving](https://developers.openai.com/cookbook/articles/codex_exec_plans).
- Huntley, Geoffrey. [The Ralph Wiggum Loop](https://ghuntley.com/loop/) (linked from the OpenAI post as the review-loop pattern).
- SASE in-tree: `AGENTS.md`; `docs/architecture.md`, `docs/development.md`, `docs/memory.md`, `docs/mentors.md`, `docs/monitors.md`, `docs/sdd.md`, `docs/axe.md`, `docs/telemetry.md`, `docs/commit_workflows.md`, `docs/ace.md` (agent screenshots), `docs/blog/posts/why-coding-agents-need-orchestration.md`, `docs/blog/posts/structured-agentic-software-engineering.md`; Justfile `toobig` / `check` recipes.
- Live: `sase memory list` (loaded ~5,282 tokens); `sase memory read lint_and_test.md tui.md sase_beads.md`; `wc` on `AGENTS.md` and large `docs/` files in workspace `sase_19` on 2026-10-01.
