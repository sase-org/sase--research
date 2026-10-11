# Pi and SASE: preserve the harness, add dependable orchestration

Independent research by **cdx**, 2026-10-11.

## Main conclusion

**SASE should make it easy for a pi user to keep pi and gain SASE's coordination, isolation, and completion guarantees.** Trying to replace pi's everyday conversation interface before supporting its harness would impose a large switching cost.

Pi and SASE overlap, but begin at different layers. Pi supplies a customizable agent harness: model access, tools, conversation context, session storage, and a terminal interface. SASE coordinates existing coding-agent harnesses: project workspaces, parallel launches, dependencies, durable review records, decisions, background commands, and host-owned completion. Pi's immediate appeal is control over one's agent; SASE's potential appeal is making that agent's engineering work easier to coordinate and land. [Pi overview][P1], [SASE overview][S1], [SASE architecture][S2].

The biggest qualification is recent: **pi now has native MCP and Codemode, and its repository includes experimental Pi Durable.** A comparison based on older descriptions of pi as four tools without MCP or durability would miss important developments. Earendil announced Pi 1.0 and Pi Durable on October 1, 2026; the inspected coding-agent changelog records 1.1.0 on October 7. The checkout also includes unreleased changes. [Pi 1.0 announcement](https://earendil.com/posts/pi-1-0/), [coding-agent changelog][P15].

My recommended order is pi integration, a simpler path to the first useful result, a better focused conversation experience, lightweight customization, and context efficiency. Improve recovery contracts alongside those changes; do not replace SASE's backend with the experimental Durable runtime.

## Scope, evidence, and limits

I opened the requested upstream repository through SASE's audited repository workflow and independently inspected its README, package metadata, coding-agent guides, RPC and print-mode implementation, Durable documentation and selected implementation, Chord documentation, and current first-party announcements. I compared these with this SASE checkout's documentation, provider registration and interface, integration contracts, and audited architectural decision notes.

Versions studied:

| Repository | Exact source snapshot | Qualification |
|---|---|---|
| earendil-works/pi | 96abe9a5ad45005cae34ed1c52d42f71fc88bedc | Main checkout; coding-agent package version 1.1.0; includes an Unreleased changelog section |
| sase-org/sase | e926d4100b1a6960682f632dce5c7a3882f39a77 | Current local checkout, not an assertion about the latest published SASE release |

Repository citations below use those immutable commits. Public announcements were checked separately. Where local source and older marketing differ, I use current source behavior and call out the difference.

This is a source and documentation review, **not a hands-on usability study, performance benchmark, paid-model evaluation, or extension compatibility certification**. No pi dependencies were installed, no pi model calls were made, and no implementation changes were made to SASE. Rankings are judgments about likely adoption value and implementation cost, not measured user preferences. I did not read or solicit any other report or researcher's findings from this swarm.

## What pi is today

### A useful default agent with unusually accessible customization

The normal CLI workflow is straightforward: install, start pi in a working directory, authenticate with /login, choose a model, and submit a task. Pi automatically saves sessions grouped by working directory. The transcript exposes tool activity; the footer exposes model, context usage, and accumulated usage and cost. The working directory influences resources and default tool paths, but is not an access restriction. [Quickstart][P2], [interactive usage][P3], [security][P10].

Customization has several levels:

- AGENTS.md for persistent instructions.
- Markdown prompt templates for reusable commands.
- Agent Skills directories for specialized instructions, scripts, and references, loaded on demand.
- TypeScript extensions for tools, commands, providers, event handlers, context transformations, and terminal UI.
- Packages distributing those resources through npm, git, or local paths.

A small local extension can be one TypeScript file, without a separate compilation step. /reload lets the user iterate within a session. This is a concrete product advantage: the user or agent can implement a small workflow without first creating a conventional Python distribution or contributing to the harness itself. [Extensions][P5], [packages][P6], [skills][P7], [prompt templates][P8].

The CLI still deliberately omits built-in subagent orchestration, plan mode, a general per-call permission system, and background bash. Those workflows can be supplied by extensions, packages, files, external process supervision, or another host. That is different from being incapable of those workflows. [Pi README][P1].

### Conversation control is a first-class part of the product

Pi persists entries as a parent-linked tree in JSONL. /tree selects another point in the same session, /fork creates a separate session from earlier history, and /clone duplicates the active branch. Abandoned branches survive. Compaction changes the context sent to the model while retaining original records. Branch summarization can preserve useful information from the path being left. [Sessions][P4], [compaction][P9].

Two kinds of busy-session input are distinct:

- **Steering:** guide the current work at a safe boundary after the current response/tool round.
- **Follow-up:** queue work after the current run finishes.

The inspected usage and SDK guides describe steering after the current response and its tool calls, so I would not promise instantaneous interruption of an arbitrary tool call. This is more precise than some website wording. [Interactive usage][P3], [SDK][P12].

**Conversation branching does not roll back filesystem changes.** Pi's history tree is a context-navigation mechanism. Returning to an old message can leave the checkout containing edits from the branch being abandoned. SASE's isolated workspaces and recorded changes are valuable companions to this feature, provided a combined interface makes the distinction explicit. This conclusion follows from the session-tree semantics and process-level file permissions; it is not a claim that pi supplies transactional filesystem branches. [Sessions][P4], [security][P10], [SASE workspaces][S3].

### Pi owns the model and tool loop

Pi calls models through its unified pi-ai layer, rather than selecting among separately implemented coding-agent CLIs. That makes it possible to switch models within the conversation while retaining the same harness and tools. It supports hosted, subscription, custom-endpoint, and local-model connections. Specific authentication and model capabilities vary. [Models][P11], [pi-ai][P16].

Current virtual models can route each request to a physical model and thinking level. The transcript distinguishes the selected router from the model that actually answered; routing state follows the session branch. The docs explicitly discuss cache misses and keeping continuations/retries on an appropriate model. This is a stronger and more inspectable concept than an opaque “automatic” model selector. [Virtual models][P17].

Pi exposes the same underlying agent/session mechanisms through interactive, print, JSON, RPC, and SDK interfaces. RPC is particularly relevant to SASE because it allows a Python host to control a pi subprocess without embedding a TypeScript application. [How pi works][P18], [CLI integration][P13], [RPC][P14].

### Native MCP and Codemode change the context-efficiency story

Current pi connects MCP servers over stdio or streamable HTTP, manages authentication, discovers tools and resources, and supports deferred exposure. Codemode lets the model write JavaScript that combines tool calls and reduces their results before sending output back to the model. Scripts run in QuickJS without ambient filesystem or network APIs; their external effects occur through the callable tools. The isolation of that interpreter is not a sandbox for the complete pi process. [MCP][P19], [Codemode][P20], [security][P10].

Codemode can call tools in parallel, inspect structured results, and retain small branch-local values between successful calls. Deferred tool declarations avoid putting every tool schema in every prompt. This offers SASE a lesson about context and orchestration efficiency, but does not imply SASE needs its own interpreter: harnesses already provide different tool-composition facilities. The useful common requirement is preserving tool provenance, output bounds, cancellation, and policy through nested calls.

Earendil's September 29 explanation frames the MCP change around discoverability, structured results, and tool composition. The relevant lesson is to evolve the small set of primitives when a feature demonstrably improves them, rather than treating an old exclusion as permanent identity. [“You Said No MCP!”](https://earendil.com/posts/you-said-no-mcp/).

### Pi Durable is an adjacent runtime, not the normal CLI

Pi Durable is a separate framework for durable agent applications. Its README explicitly warns that the API may change without notice. It shares pi-ai and uses Chord for state, but should not be described as a durability guarantee already possessed by every normal pi coding-agent session. [Durable README][P21], [Pi Durable announcement](https://earendil.com/posts/pi-durable/).

Its implemented/documented concepts include:

- Immutable conversation records plus typed application documents changed through atomic commits.
- Durable generation/tool/task checkpoints.
- Persistent submissions deduplicated by requestId.
- Replay policies distinguishing safe tools from tools that may already have caused effects.
- Per-conversation models, tools, instructions, and execution environments.
- Task ownership, cancellation, forks, queued steering/follow-ups, and bounded live-state watching.

The selected implementation confirms that tool intent is committed before execution. On recovery, both the recorded policy and the current tool policy must permit safe replay; otherwise an interrupted result tells the model the call may have partially run. Submission admission checks an existing requestId and returns the original submission. These are concrete mechanisms rather than merely roadmap intentions. [Tool recovery source][P22], [submission admission source][P23].

Durability has important limits. One process owns a storage; the README says there is no cross-process locking. SQLite's documented WAL/NORMAL configuration protects against process crashes while allowing loss of the newest commits on power/host failure. JSONL can fsync, but retains history in memory; the docs recommend SQLite for long runs. Deduplicating a submission or replaying a “safe” tool does not automatically make external effects exactly-once. Applications still need appropriate ownership and idempotency. [Durable storage][P21].

Chord separates plugin facets, services, replicated state, and transport adapters. Its stable service handles and validated replacement lifecycle are worth studying for future multi-surface SASE integrations. That is an architectural idea to borrow, not a reason to import Chord or rewrite Rust-owned SASE domains in TypeScript. Experimental server/client packages extend this direction, but are not evidence of a finished replacement for SASE's project and review workflows. [Chord][P24], [experimental server][P25], [SASE backend boundary][S12].

## How the products compare

| Dimension | Pi coding agent | SASE today | Implication for a pi user |
|---|---|---|---|
| Primary purpose | Personal, customizable coding harness | Coordination layer over existing harnesses | They can be complementary |
| First useful task | Start in a folder and chat | Install SASE plus an authenticated supported CLI; choose a project/workspace | SASE needs to explain the target and added value earlier |
| Model changes | Same tools/context mechanism across providers; virtual routing available | Chooses a harness/provider plus model/effort; supports aliases and cross-provider workflows | Preserve the user's pi harness instead of forcing a new one |
| Conversation history | In-file tree, branch navigation, fork, clone, compaction | Agent/session/clan forks and provider-specific continuation | Improve access to alternatives; do not pretend SASE lacks forks |
| Small customizations | Local TypeScript files and Markdown resources; reload | Rich macros, generated skills, config and installed plugin entry points | Narrow the gap for tiny executable customizations |
| Parallel engineering | Extensions and external hosts can launch agents | Native fan-out, isolation, queue/dependency handling and coordinated work | This is a reason to add SASE |
| Slow work | Ordinary CLI leaves process supervision to other tools | Detached commands, monitors and mechanical continuation | Show the user what survives closing the interface |
| Durable engineering state | Session records; custom extensions; separate Durable framework | Patches, stitches, goals, beads, artifacts, recorded commands and decisions | SASE supplies a finished engineering workflow around the harness |
| Completion | Harness settles; normal CLI does not supply SASE's landing contract | Selected host finalizers verify completion and own commits/branches/PRs | A defensible advantage if it works transparently |
| Safety boundary | Project trust and optional extension gates; OS/container boundary needed | Decision gates, workspace isolation and provider controls | Reviewability and isolated checkouts are not a universal security sandbox |
| Integration surface | CLI modes, documented RPC, TypeScript SDK | CLI plus public Python helpers, provider plugins and frontend bridges | Extend existing SASE APIs rather than claim they do not exist |
| Platform reach | Linux, macOS, native Windows; Termux guide | POSIX Linux/macOS; Windows explicitly unsupported | Important for some users, expensive and secondary to basic compatibility |

Sources for pi: [overview][P1], [sessions][P4], [interfaces][P13], [extensions][P5], [security][P10]. Sources for SASE: [overview][S1], [getting started][S4], [sessions][S5], [macros][S6], [plugins][S7], [integrations][S8], [monitors][S9], [workspace isolation][S3].

### Where SASE already has a stronger proposition

**Coordinated work across isolated repositories.** Pi extensions can launch workers, but a worker-launching extension does not by itself provide SASE's project registry, numbered workspace claims, launch admission, dependency handling, and consistent operational visibility. This is infrastructure the pi user need not assemble themselves. [Architecture][S2], [workspaces][S3], [sessions and clans][S5].

**Engineering outcomes beyond the transcript.** SASE tracks reviewable changes and their lifecycle, reusable workflows, dependency-aware work units, person-owned outcomes, immutable artifacts, and command evidence. The value is linking the result to how it was produced and reviewed, even when the model or harness changes. [Patches][S10], [goals][S13], [named tools][S14], [artifact references][S15].

**Host-owned waits and completion.** A monitor or gate can outlive the provider turn; a verified host finalizer can land work after the model exits. Keeping this machinery outside the agent's private session avoids relying on that session staying alive forever. The tradeoff is more infrastructure and more visible transition states. SASE should make that tradeoff understandable in the interface, rather than require a newcomer to memorize its internal vocabulary. [Monitors][S9], [completion configuration][S11].

Pi Durable narrows the architectural distance by offering durable tasks and state, but it is a toolkit. It does not demonstrate an out-of-the-box equivalent of SASE's complete engineering workflow. Conversely, SASE's stored records and supervised processes do not establish tool-level crash replay equivalent to Pi Durable's harness checkpoints.

### Where pi currently creates less friction

Pi centers the individual conversation: a coherent transcript, directly accessible queue/model/session controls, and a small customization ladder. SASE centers the coordinated work graph. That is a valuable distinction, but it can make a small edit or experiment feel like entry into an orchestration system.

SASE already has relevant foundations: a TUI starting on Agents, prompt completion/history, forks, public integration helpers, plugin discovery, initialization and doctor tooling, and instruction bundles with section-level token estimates. The opportunity is to present these around the immediate task and hide unnecessary choices until useful. [TUI][S16], [initialization][S17], [instruction bundles][S18].

A particularly concrete mismatch is location. Pi uses the folder where it starts. SASE's documented “current project” is independent of cwd, and the README says the +home quickstart runs in the built-in home sandbox rather than the caller's directory. Neither behavior is inherently wrong, but a pi user needs a clear target display and an easy way to choose the actual repository. [Getting started][S4], [SASE README][S1], [Pi quickstart][P2].

## An integration strategy that fits SASE

The upstream RPC interface is the practical starting point for a pi provider. SASE already discovers installed LLM-provider plugins; its base provider interface receives a preprocessed prompt and returns a result with optional usage. The inspected built-in registry names the supported coding CLIs and contains no pi provider. This establishes a shipped integration gap in this snapshot, not proof that no third party has written one. [SASE provider registration][S19], [provider interface][S20], [Pi RPC][P14].

A viable adapter should do more than invoke “pi --print”:

1. Start pi in the workspace SASE actually claimed, with a deliberate session storage location.
2. Load the user's selected pi resources and authentication through pi's normal mechanisms; retain provenance and trust decisions.
3. Deliver SASE's required instruction/completion contract without unnecessarily replacing the user's entire pi prompt.
4. Consume and normalize structured events, token/cost records, tool activity, errors, queues, and session identity.
5. Maintain the relation between SASE's run/session identity and pi's session/branch identity.
6. End the provider invocation and dispose the subprocess when the SASE turn settles or hands off. Do not leave a hidden daemon or native background extension masquerading as an active SASE turn.

There are two non-obvious compatibility hazards:

- **RPC acceptance and low-level end are not completion.** A successful prompt response can mean started, queued, or handled. Automatic retries, compaction recovery, or queued input can follow agent_end. The documented terminal boundary is agent_settled. Even that only settles the harness; SASE's own finalizer contract must still be satisfied. Pi JSON mode can report a model error while exiting zero, so a host must inspect events instead of trusting process status alone. [RPC lifecycle][P14], [CLI integration][P13], [print-mode implementation][P26].
- **Extension compatibility depends on the surface.** RPC transports basic dialogs and notifications, but custom terminal components and several UI methods are unavailable or no-ops. Do not advertise compatibility with every pi extension. Initially certify a subset, list unsupported UI/background behavior, and offer opening pi's own terminal UI for appropriate standalone work. [RPC extension UI][P27].

For dialogs, a raw RPC extension request normally waits for an in-process answer. SASE's existing gate contract instead ends the agent turn and resumes through host infrastructure. A first adapter should either limit such extensions to a tested synchronous path or deliberately translate them into durable handoffs with stored request identity and continuation evidence. “Forward every dialog into a gate” is not a free or already-solved mapping.

Shared queue, lineage, policy and artifact semantics belong in SASE's Rust core when they must agree across CLI, TUI and other frontends. Subprocess control and pi wire adaptation can remain thin Python/provider glue. This respects the existing boundary and prevents a pi-specific alternative SASE backend. [SASE architecture][S2], [Rust backend][S12].

## What to learn without copying pi wholesale

**Minimize the cost of customizing an existing workflow.** Pi makes a reusable prompt much cheaper than a tool, and a tool cheaper than a new application. SASE's rich macros should remain, but executable extensions should have an equally approachable smallest form.

**Treat context as an inspectable, scarce resource.** Pi's on-demand skills, bounded/deferred tool declarations, context hooks, and compaction are useful patterns. SASE already exposes instruction-bundle manifests and estimated token counts, so measure and simplify the actual delivered context before inventing a new memory-retrieval subsystem. Pi's minimal base prompt does not guarantee a small effective prompt after project instructions, skills, extensions, and tools load. [Skills][P7], [Codemode][P20], [compaction][P9], [SASE bundle inspection][S18].

**Make transitions explicit.** A user should distinguish queued steering from queued next work, an interrupted tool from a failed tool, and a settled agent from successfully finalized engineering work. Pi's interface and RPC make several of these distinctions accessible. SASE has additional distinctions worth preserving rather than flattening into “done.”

**Use declared replay and idempotency instead of optimistic restart.** Pi Durable's design offers useful reference patterns for work SASE actually owns. SASE's update-skew recovery currently documents conservative exclusions, including post-provider failures and OOM/timeouts. That caution is sensible; improve precision where evidence permits, rather than indiscriminately rerunning a whole engineering turn. [SASE auto-restart][S21], [Durable recovery][P22].

**Separate UI projection from authoritative state.** Pi Durable and Chord show how late-attaching clients can receive current committed state plus bounded updates. SASE already has integration-facing projections and a required shared core. Improve those contracts and their conformance tests; do not move business logic into terminal components or reimplement it independently for a future web client. [Chord][P24], [SASE integrations][S8].

## Choices I would defer

- Replacing SASE's Rust/Python architecture with pi-ai, Chord, or Pi Durable.
- Building a second full coding harness merely to match pi's conversation UI.
- Shipping native Windows before validating demand from pi users.
- Adding a generalized runtime interceptor ecosystem before identifying the useful hooks and preserving finalizer ownership.
- Promising lower cost, better coding accuracy, universal extension compatibility, or exactly-once external effects without measurements.
- Adding more orchestrator vocabulary to the first-run interface.

A useful adoption experiment would recruit existing pi users for three tasks: one local edit using their own resources, one pair of independent workers, and one change carried through verification to a reviewable result. Measure setup time, wrong-target incidents, resource-compatibility failures, interventions, and completion rate. Include a power user with executable extensions and one user who mainly uses templates/skills. This tests whether SASE preserves the part they like while improving the part they currently assemble themselves.

## Source index

Pi repository sources, all pinned to the inspected commit:

- [P1: repository overview][P1]; [P2: quickstart][P2]; [P3: interactive usage][P3].
- [P4: sessions][P4]; [P5: extension API and lifecycle][P5]; [P6: packages][P6].
- [P7: skills][P7]; [P8: prompt templates][P8]; [P9: compaction][P9].
- [P10: security and project trust][P10]; [P11: model access][P11]; [P12: SDK][P12].
- [P13: CLI modes][P13]; [P14: RPC][P14]; [P15: release history][P15].
- [P16: pi-ai][P16]; [P17: virtual models][P17]; [P18: harness structure][P18].
- [P19: MCP][P19]; [P20: Codemode][P20]; [P21: Pi Durable][P21].
- [P22: durable tool recovery implementation][P22]; [P23: submission deduplication implementation][P23].
- [P24: Chord][P24]; [P25: experimental server][P25]; [P26: print/JSON exit handling][P26]; [P27: RPC UI limitations][P27].

SASE repository sources, all pinned to the inspected commit:

- [S1: overview and quickstart][S1]; [S2: architecture][S2]; [S3: workspaces][S3].
- [S4: getting started and current-project semantics][S4]; [S5: agent groupings and sessions][S5].
- [S6: macros][S6]; [S7: plugins][S7]; [S8: public integration APIs][S8].
- [S9: monitors][S9]; [S10: Patches][S10]; [S11: host finalizer configuration][S11].
- [S12: Rust backend][S12]; [S13: goals][S13]; [S14: recorded tools][S14].
- [S15: artifact references][S15]; [S16: TUI][S16]; [S17: initialization][S17].
- [S18: instruction bundles][S18]; [S19: shipped provider entry points][S19].
- [S20: provider base interface][S20]; [S21: update-skew recovery][S21].

Additional first-party sources: [Pi 1.0 announcement, October 1](https://earendil.com/posts/pi-1-0/), [Pi Durable announcement, October 1](https://earendil.com/posts/pi-durable/), and [MCP/Codemode rationale, September 29](https://earendil.com/posts/you-said-no-mcp/). I also consulted [Mario Zechner's earlier account of pi's design](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/) for historical context; its old package names and feature exclusions are not used as current feature claims.

[P1]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/README.md
[P2]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/docs/quickstart.md
[P3]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/docs/usage.md
[P4]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/docs/sessions.md
[P5]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/docs/extensions.md
[P6]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/docs/packages.md
[P7]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/docs/skills.md
[P8]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/docs/prompt-templates.md
[P9]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/docs/compaction.md
[P10]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/docs/security.md
[P11]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/docs/models.md
[P12]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/docs/sdk.md
[P13]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/docs/cli-integration.md
[P14]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/docs/rpc.md
[P15]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/CHANGELOG.md
[P16]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/ai/README.md
[P17]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/docs/virtual-models.md
[P18]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/docs/how-pi-works.md
[P19]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/docs/mcp.md
[P20]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/docs/codemode.md
[P21]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/durable/README.md
[P22]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/durable/src/harness/tool.ts#L150
[P23]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/durable/src/harness/submissions.ts#L158
[P24]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/chord/README.md
[P25]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/server/README.md
[P26]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/src/modes/print-mode.ts#L135
[P27]: https://github.com/earendil-works/pi/blob/96abe9a5ad45005cae34ed1c52d42f71fc88bedc/packages/coding-agent/docs/rpc-extension-ui.md
[S1]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/README.md
[S2]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/docs/architecture.md
[S3]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/docs/workspace.md
[S4]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/docs/getting_started.md
[S5]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/docs/agent_sessions.md
[S6]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/docs/macros.md
[S7]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/docs/plugins.md
[S8]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/docs/integrations.md
[S9]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/docs/monitors.md
[S10]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/docs/change_spec.md
[S11]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/docs/configuration.md#llm_providerfinalizers
[S12]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/docs/rust_backend.md
[S13]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/docs/goals.md
[S14]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/docs/tool.md
[S15]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/docs/artifact_references.md
[S16]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/docs/ace.md
[S17]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/docs/init.md
[S18]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/docs/instruction_bundles.md
[S19]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/pyproject.toml#L212
[S20]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/src/sase/llm_provider/base.py
[S21]: https://github.com/sase-org/sase/blob/e926d4100b1a6960682f632dce5c7a3882f39a77/docs/agent_auto_restart.md

## Ranked improvements to make SASE appealing to existing pi users

Ranking favors preserving existing investment, fast visible benefit, and feasible changes over architectural novelty. Effort estimates are relative engineering judgments, not schedules.

1. **Ship a supported pi harness provider with an explicit compatibility contract.**  
   **Why first:** a user who already trusts pi should not have to switch coding agents to try SASE. This is the prerequisite for selling SASE as added coordination. **First slice:** a maintained provider using pi's structured interface, normal authentication, selected skills/templates/tools, SASE workspace cwd, session IDs, usage capture, errors, cancellation, and host finalization. Use agent_settled correctly; do not trust JSON process exit alone. Make unsupported terminal-only extensions and background behaviors visible. Basic print/JSON launching may prove the integration, but is not sufficient for full steering or extension compatibility. **Effort:** medium to large. **Success measure:** representative pi users complete a verified task with their existing model and portable resources, without editing those resources or installing a different coding harness. [Provider boundary][S20], [RPC lifecycle][P14], [UI limitations][P27].

2. **Offer a repository-focused first-run path with progressive disclosure.**  
   **Why:** pi users expect “start here, do this task.” SASE's project/workspace targeting and existing initialization can be simplified at the point of use. **First slice:** detect the invoking repository, show exactly which project and checkout will be used, reuse an existing project or offer a minimal registration, and launch one pi-backed task in an isolated workspace. Keep the richer orchestration views available. Defer optional sidecars, remote setup, and advanced workflow concepts until needed. Preserve existing project-selection semantics through an explicit entry path rather than silently changing all launches to cwd-based selection. **Effort:** medium. **Success measure:** a new pi user reaches a correct-repository result in one sitting and can explain where the edits landed. [Current-project semantics][S4], [initialization][S17].

3. **Add a focused conversation view with explicit steering and follow-up queues.**  
   **Why:** coordination is easier to adopt when a single task remains easy to control. **First slice:** a transcript, input editor, current model/context/cost display, Stop, Steer, Next task, Continue, and Fork actions for the selected worker. Expose pending messages and whether they were accepted or delivered. Use capability-aware controls: forward to pi's RPC where supported; show a host-owned successor path where live steering is unavailable. Present SASE's existing forks clearly before building a new history engine. Any future entry-level branch action must state whether it branches only context or also selects different repository state. **Effort:** medium to large. **Success measure:** users redirect or queue work without manually composing orchestration directives, and lose no queued text on stop/restart. [Pi usage][P3], [SASE existing forks][S16], [RPC commands][P14].

4. **Make a tiny customization as easy as a local file and reload.**  
   **Why:** pi's executable extension ecosystem is part of what users are invested in. **First slice:** documented examples for a one-file command/hook, explicit trusted discovery, validation, clear event ownership, disposal, and reload at safe boundaries. Keep Markdown/Jinja macros as the cheapest choice for prompts. Publish a small catalog of useful workflow bundles, with dependency and compatibility metadata, rather than attempting to mirror every pi extension. Let pi own pi extensions through the provider; add SASE extensions only for orchestration behavior the host must own. Plugins must not bypass required finalizers or mutate shared domain rules in presentation code. **Effort:** medium. **Success measure:** a user can create and test a simple host workflow without packaging a distribution or patching core. [Pi extensions][P5], [SASE plugin foundations][S7].

5. **Set a measured context budget and make the effective context inspectable.**  
   **Why:** pi users care about controlling their harness, and orchestration instructions can consume context before their task begins. **First slice:** put SASE's existing bundle section/token estimates into the task view, distinguish SASE additions from pi/project resources, identify duplicated instructions, and expose the provenance of loaded tools/skills. Measure launch-token overhead and time to first useful output on real tasks. Move appropriate long guidance to audited on-demand material while keeping the required completion and safety contract present. Preserve pi's deferred MCP/Codemode behavior rather than re-declaring all tools in SASE. **Effort:** small to medium initially. **Success measure:** lower measured instruction overhead with unchanged compliance and completion reliability; honest “unknown” values where the provider exposes no complete accounting. [Bundle tooling][S18], [skills][P7], [Codemode][P20].

6. **Provide an explicit “use SASE for this workflow” bridge from pi.**  
   **Why:** after integration, the user needs one compelling reason to invoke SASE instead of their current pi package/tmux setup. **First slice:** a thin pi command or package that requests a SASE run and displays its durable identity/status, plus three maintained recipes: independent implement/review workers, parallel investigations with a synthesis step, and verification followed by host-owned landing. Use existing SASE APIs and gates; do not let the extension invent its own scheduler or finalizer. Keep the first command understandable without learning clans, stitches, and queue grammar. **Effort:** small to medium after item 1. **Success measure:** pi users run a second coordinated task because supervision and results are useful, rather than merely because onboarding succeeded. [SASE workflows][S6], [integration APIs][S8], [pi extension commands][P5].

7. **Strengthen recovery with typed replay, idempotency, and cancellation contracts for host-owned work.**  
   **Why:** dependable automation becomes a reason to prefer SASE as runs grow longer, and Pi Durable is moving directly into this territory. **First slice:** inventory SASE's existing durable launches, monitors, gates and finalizers; declare which operations can retry, which require reconciliation, and which must report uncertain effects. Persist operation IDs before effects, reuse them during recovery, and add failure-injection tests around admission/execution/settlement boundaries. Scope the contract to operations SASE controls; opaque provider tool calls may only support conservative recovery. Do not equate submission deduplication with exactly-once external effects or automatically retry arbitrary shell commands. **Effort:** large, incremental. **Success measure:** crash tests preserve acknowledged work and never silently duplicate mutations or leave unmanaged child work. [Current recovery limits][S21], [Durable replay mechanism][P22], [deduplication][P23].

8. **Make model routing and cost explainable across harnesses and turns.**  
   **Why:** pi exposes selected versus dispatched models and physical-model cost; SASE's multi-provider advantage should be equally legible. **First slice:** show resolved harness, model, effort, selection reason, any fallback, observed usage, and whether figures are incomplete. Preserve pi virtual-router identity and per-response physical model attribution instead of flattening both into one label. Build on SASE's existing aliases and usage accounting; add cheaper review/summary routing only where it improves measured outcomes and avoids needless cache misses. **Effort:** medium. **Success measure:** a user can trace why each model ran and what cost is actually known, including retries and summarized context. [Pi virtual models][P17], [SASE providers][S19], [instruction provenance][S18].

9. **Make adoption reversible through portable resources and reviewable session exports.**  
   **Why:** lock-in is especially unattractive to a user who chose a customizable harness. **First slice:** validate/reuse standard skill directories and existing AGENTS.md without rewriting them; offer template migration previews; export a selected SASE session's prompts, results, lineage, diffs and artifact links in documented JSON plus readable HTML/Markdown. Allow explicitly attaching an existing pi session as preserved context, with provenance and clear limits on replay or branch fidelity. Distinguish read-only attachment from fully adopting that session into a SASE turn. Use review/redaction before sharing, since tool output can contain private data. **Effort:** medium. **Success measure:** the user can retain useful pi resources, explain imported history, and take results elsewhere without needing a running SASE installation. [Pi skills][P7], [session/export semantics][P4], [SASE integration projections][S8].
