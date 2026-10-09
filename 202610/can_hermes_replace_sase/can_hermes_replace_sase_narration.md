---
narration: 1
title: Can Hermes Replace SASE?
source: research:202610/can_hermes_replace_sase/can_hermes_replace_sase__final.md
source_blob: 071fa0b18c819072bcb299363897f2368ccd6a9d
date: 2026-10-09
kind: research
edition: full
producer: agent
---

## The question and the verdict

Can Hermes do everything SASE can? And should almost everyone choose Hermes instead of bothering with SASE?

Those questions get different answers. The feature equality claim fails. The practical advice largely holds.

All five independent researchers found capabilities Hermes does not match. The lead checked disputed findings in both codebases.

But most people, including most professional developers, do not need those capabilities together. Hermes, or a single vendor coding agent, is the better default.

The exception is a workflow, rather than a particular person. SASE fits someone managing several coding agents across vendors, on trusted repositories, under asynchronous supervision.

This report compares features only. It excludes popularity, adoption, and community size. Nobody ran matched workloads. It cannot establish differences in speed, reliability, or code quality.

Here, Hermes means Nous Research's Hermes Agent, the self-hosted agent harness. It does not mean the Hermes model family.

The comparison reflects October 2026. SASE's last released version is 0.17.1. Its development branch is about 2,260 commits beyond that release.

We also need a useful definition of capability. An agent with a shell could theoretically run almost anything, including SASE itself. That does not establish product equality.

The report distinguishes shipped core features, supported opt-in features, community approximations, and capabilities with no equivalent found.

## Two different kinds of product

Hermes is the agent. It runs its own model and tool loop across about 40 providers, including local models.

The same agent core serves a command-line interface, messaging gateway, terminal interface, and desktop application. It remembers users, writes skills, delegates, and schedules work.

SASE wraps agents. Its name means Structured Agentic Software Engineering. It coordinates seven vendor coding command-line interfaces as single-turn workers.

Those workers include Claude Code, Codex, Antigravity, Qwen Code, OpenCode, Muse Code, and Grok Build.

SASE keeps each vendor's harness as the execution engine. It provides shared launching, workspaces, human decisions, completion, and provenance around those engines.

Hermes instead offers migration into its own agent. Importing another agent's setup is different from supervising that agent as an independent worker.

The products overlap when several agents perform repository work under durable supervision. That is where the feature comparison matters.

The audit examined 19 SASE capabilities. Hermes matched 6 in core. Another 4 were opt-in, experimental, or official-plugin features.

For 4 more, only community plugins or unenforced approximations existed. The remaining 5 had no equivalent found.

Together, 9 capabilities lacked a Hermes core or official equivalent. But the weights matter more than that count.

Someone who needs ordinary parallel coding, scheduling, and chat control may lose nothing by choosing Hermes.

## The strongest case for just using Hermes

Hermes's Kanban board is a credible coding pipeline. It has task dependencies, durable claims, retries, attempt history, and an isolated git worktree per task.

It can decompose work automatically. Its review column launches a reviewer. Its swarms include an independent verifier and synthesizer.

Its pull request contract checks GitHub's required continuous integration checks at the current commit before closing the task.

Continuous integration, or CI, means automated checks run against proposed changes. Hermes's completion transaction also rechecks dependencies and worker ownership.

On review and checks before completion, Hermes is ahead of SASE. SASE lacks both a per-task review lane and an equivalent required-checks gate.

Scheduling is broader in Hermes. Scheduled jobs can deliver results across about 20 or more messaging platforms.

It also offers voice, browsing, computer use, vision, image generation, a desktop application, and a web dashboard.

Hermes learns across sessions. It writes memory and skills, prunes them, and searches previous conversations.

It offers seven terminal backends, including containers and remote execution. Other controls include an egress proxy, command blocking, approval modes, and prompt-injection scanning.

SASE normally runs vendor agents with permission checks bypassed. Its only opt-in sandbox is Muse's. Workspace clones do not constitute a security boundary.

Hermes supports native Windows, Windows Subsystem for Linux, macOS, Linux, Android through Termux, Docker, and Nix. SASE supports Linux and macOS.

Community plugins narrow further gaps. They offer persistent workflow gates, plan approval, multi-model deliberation, proof-based coordination, and automatic commits.

But an automatic-commit plugin does not reproduce SASE's host-owned completion policy. Similar outcomes can conceal opposite rules about who controls the work.

Subscriptions are another correction to an overly simple comparison. Hermes is not limited to metered application programming interfaces, or APIs.

An experimental official plugin can use a Claude subscription. Codex can use ChatGPT authentication. Community plugins reach Antigravity and Grok subscriptions.

One caveat concerns Hermes's native Anthropic authentication path. That path uses Max extra-usage credits rather than the base allowance.

Hermes also tracks account and model usage windows, rotates credentials on usage limits, and supports fallback providers.

SASE reacts to usage-limit errors too. Claims that it proactively reroutes before hitting limits were overstated.

For a few background coding tasks within one model family, delivered as pull requests, the case for Hermes is strong.

## Where feature equality breaks

The first decisive difference is the worker itself. SASE supervises the vendor's whole coding harness, including its tools and context management.

Hermes generally uses its own loop. It can swap to an opt-in Codex runtime, but that runtime loses several Hermes tools.

Other integrations expose vendor subscriptions as model providers. That is different from running their complete coding harnesses as workers.

Hermes's own documentation says external command-line workers are not yet a paved path for Kanban.

This matters when someone deliberately wants Claude Code, Codex, and Grok Build working under one shared board and policy.

It does not establish a measured quality advantage for those harnesses. Nobody benchmarked that hypothesis.

The second difference is who owns the commit. In SASE, the agent declares its changes and the host commits them.

The host rejects stale declarations and treats changes after acceptance as protocol violations. Commits record the agent, task, and plan.

Hermes's worker runs git and GitHub commands itself. Its pull request acceptance gate reads evidence; it does not perform remote writes.

SASE's rule is a workflow and provenance contract. It is not physical prevention. Agents have enough permissions to run git.

The system detects an unauthorized commit and refuses to accept it as completed work. That distinction limits the governance claim.

The third difference is a durable human decision. SASE ends the agent's turn when it asks for a gate.

Plans, questions, launch approvals, privileged commands, and failure triage each have typed records. A later answer launches a new turn with a receipt.

No model process or worker slot remains occupied while the human considers the request.

Hermes does have a durable pause. A Kanban task can block for input indefinitely. The dispatcher reaps its worker, and a human later unblocks it.

What Hermes lacks is SASE's typed decision system across any agent turn, with receipts.

Hermes's per-command approvals instead hold a live thread. Their default timeout is 300 seconds. That limit does not apply to blocked Kanban tasks.

Hermes merged durable command approvals and reverted them the same day. The report treats that as unfinished work, rather than an existing capability.

## The work record and verification evidence

SASE stores tasks, plans, and project memory in git-backed repositories. Its artifact graph connects research, plans, phases, and commits.

That supports questions about which agent followed which approved plan using which evidence. A clone can carry the work record.

Hermes keeps its Kanban board in a local database on one host. Its documentation explicitly describes that board as single-host.

Hermes's memory primarily describes the user. SASE's memory describes the project and renders into instruction files across vendors, with audited reads.

Hermes loads one project context type by priority. That is a different memory model rather than a direct substitute.

SASE also offers approved epics split into sized phases. Phase size chooses a model, and large phases must plan before implementing.

An automatic land agent waits mechanically for every phase agent and phase task. Closing the epic refuses incomplete phases or stale symbol entries.

But the land agent's integration work is still a language model following instructions. It is not a deterministic full-suite integration gate.

Hermes documents a comparable reconciliation-task pattern. The user assembles that pattern manually.

The real difference is SASE's automatic tail and mechanical waits, rather than inherently stronger integration testing.

SASE's ToolRuns record command identity, repository fingerprints before and after execution, and failure evidence.

Failures can be classified as new, known, flaky, or unknown. A known failure needs an independent witness.

Verdict receipts can authorize explicitly configured completion policies. They never skip test execution. A thin evidence ledger may produce many unknown classifications.

An ordinary SASE final declaration runs no tests by itself. Verification depends on what the agent ran or a prepared completion path.

Hermes has deterministic pass-or-fail gates, but no equivalent project-level failure ledger.

SASE's evidence story is distinctive. Hermes's review and required-checks story remains stronger in the ordinary coding pipeline.

## Costs, caveats, and who fits

SASE's benefits fall on a narrow group, while its costs fall on every user.

It is alpha software. It requires a Rust extension, supports only Linux and macOS, and normally bypasses agent permission checks.

Its vocabulary adds concepts for tasks, patches, commits, macros, gates, sessions, artifacts, and verification records.

Many differentiating features exist only on the development branch. A new release is needed to make them readily available.

Some safeguards are instructions rather than enforcement. Memory-write gating largely tells the agent what to do. Guarded recipes are guardrails, not security boundaries.

For a personal assistant, choose Hermes. SASE adds little to voice, browsing, scheduled automation, or memory about the user.

For one coding agent at a time, use that vendor's interface directly, or Hermes as an all-in-one agent.

For a few parallel tasks with chat supervision and pull requests, choose Hermes Kanban. It already provides worktrees, dependencies, review, and CI acceptance.

For users needing containment against untrusted input, or native Windows support, the report favors Hermes over SASE.

The SASE profile combines several recurring needs. It runs multiple native vendor harnesses, often using subscriptions, on long-lived trusted repositories.

Its operator supervises asynchronously, coordinates multi-phase work, and wants attributable landing plus durable decisions and verification evidence.

Professional seriousness is not the dividing line. Managing a heterogeneous agent fleet is.

The researchers disagreed about how broadly to recommend SASE. The lead rejected the claim that all serious software engineering needs it.

A repeatable operator profile exists beyond SASE's author. That establishes a plausible role, not a measured market size.

## SASE's realistic role and what could change

SASE's role is a vendor-neutral control layer above frontier coding agents. It should make several agents behave like a supervised engineering team.

That layer answers recurring operator questions. What plan was approved? What is blocked? Which worker changed which repository, using what evidence?

What verified the result? Who may land it? How does an ambiguous or failed landing recover?

The role gains value when vendors offer different harnesses. SASE can coordinate those harnesses without rebuilding their inner agent loops.

Its deterministic coordination handles dispatch, waits, gates, and commits without model tokens. Language models still perform reasoning and integration work.

To make this role reachable, the report recommends a release and an opt-in sandbox.

It also recommends a small starting path: launch an agent, review its declaration, handle a gate, and inspect the result.

SASE should add a review lane, required CI acceptance, and rollback during a run. Hermes exposes these product gaps clearly.

Useful coordinator additions include transcript search, webhook input, an external control API, and staged memory proposals.

The report discourages importing autonomous self-editing memory and skills into SASE's authored, versioned memory model.

The most promising relationship is complementary. Hermes has a headless mode suitable for a provider integration.

Making Hermes the eighth SASE provider could bring its flexible model loop under SASE's workspaces, gates, and finalizers.

A user could keep Hermes as a personal front door and SASE as the engineering coordinator. That maintained integration does not exist today.

The verdict would shift if Hermes shipped native external-worker lanes, typed durable approvals, and host-side commits.

A portable work record and verification ledger would narrow the remaining gap.

A practical trial should compare small coding tasks, dependency-ordered recovery, stale verification across repositories, and research consumed by later implementation.

Judge surviving records, recovery, verification policy, and custom integration. Nobody has run that trial.

## Recommendation

Make the practical argument and drop the feature equality claim. Most people, including most developers, should use Hermes or a single vendor coding agent.

Hermes cannot do everything SASE does. Its missing capabilities reflect architectural choices as well as unfinished features.

Do not add SASE merely for parallel agents, worktrees, task tracking, scheduling, memory, review, or chat control. Hermes already covers those needs.

Recommend SASE only when several distinctive needs recur together: native workers across vendors, host-owned landing, typed asynchronous decisions, portable project records, and verification evidence.

That is a real specialist role beyond its author. It is not a reason to recommend SASE to agent users generally.

Position SASE above coding agents. Make its distinctive contracts easy to adopt, improve containment and verification, and build the Hermes provider bridge.

If those contracts cannot justify a separate installation compared with Hermes and existing CI, contributing them to Hermes is the better strategy.
