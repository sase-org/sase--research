**SASE and Gas Town: coordination advantages worth borrowing**

Independent research by **cdx**, 2026-10-16. Scope: the requested `gastownhall/gastown` repository versus the supplied SASE checkout and its linked backend and GitHub plugin. No other report, transcript, summary, or findings from this research swarm were consulted.

**Assessment.** Gas Town's clearest advantage is how explicitly it packages coordination around work that must keep moving: addressed agent communication, cross-project work collections, redispatch of stranded tasks, a dedicated integration role, and operational repair. SASE already has durable state, dependencies, parallel execution, automated review, recovery, and host-owned completion. Treating those as missing would produce the wrong roadmap. The best changes are extensions to SASE's existing domains, with measurable reductions in operator intervention.

The evidence supports several specific capability advantages. It does **not** establish that Gas Town is faster, cheaper, more reliable, or better at producing correct software overall. In particular, its README overstates what I could trace into the normal merge execution path.

**Evidence and revision boundaries.**

| Component | Inspected revision | Why it matters |
| --- | --- | --- |
| Gas Town | `649b832b7672bc7a2dbef26f5983aba6198b819b` | Repository HEAD and origin/main; independently matched against git ls-remote for HEAD and main. Commit date is July 23, 2026, despite this October investigation. |
| SASE | `f3087c86acbbd2e445a7a0054e3d596aafeeeb95` | The supplied working checkout, not a presumed release or a remotely fetched replacement. |
| sase-core | `594faf31d80af79a148cb67968318b2bfb1a5770` | Opened linked checkout matches SASE's sase-core-revision.txt exactly. |
| sase-github | `8712c153aa969eef55bccbabe2e0e94a50764a68` | Checked to avoid overlooking PR submission behavior implemented outside the main SASE repository. |

Repositories were opened through the audited SASE repository workflow. Repository evidence was read locally; source links below pin the inspected commits. Web browsing was used for upstream issue discussions, which are evidence of reported operational failures rather than independently reproduced defects. This was a source and documentation investigation: I did not install Gas Town, operate a live town, run either project's test suite, or benchmark equivalent workloads. Tests cited below were inspected as evidence of intended coverage, not reported as passing executions. Negative findings mean “not found in the inspected entry points, source, and documentation,” not a proof that no custom plugin can supply the behavior.

**A fair starting point: substantial overlap.**

SASE's architecture already includes immutable launch plans, journaled admission, dependency waits, capacity budgets, durable agent artifacts, supervised processes, gates that release the provider process, scheduler reconciliation, and reusable workflows. Epic work includes dependency waves, phase workers, nested delegation, a final land agent, dry-run previews, resumable launches, and cross-project target resolution. Gas Town should not receive an unqualified advantage merely for having persistent tasks, DAGs, isolated workspaces, or multiple agents. [SASE architecture][s-arch]; [bead work][s-work]; [workflow specification][s-workflows].

Likewise, SASE already has automated conflict repair and independent completion checks. Its finalizer can launch one repair turn, require verification before resuming the VCS operation, and check publication evidence afterward. Its GitHub plugin submits a tracked PR through the GitHub CLI. Gas Town's integration advantages must be assessed against those features. [SASE finalizer][s-final]; [GitHub submission implementation][s-gh].

A few terminology correspondences prevent false equivalences:

| Gas Town concept | Closest SASE concept | Material difference |
| --- | --- | --- |
| Rig | Registered project and its repositories | Both organize work by repository/project; names alone are not an advantage. |
| Polecat | Task or phase worker with a claimed workspace | Gas Town emphasizes replaceable workers attached to durable work. SASE also separates work records from run artifacts. |
| Convoy | An epic plus grouping/progress surfaces | A convoy can collect existing work across rigs without making it one authored epic. |
| Hook | Durable work assignment | Not equivalent to a SASE verification hook. Comparing the names directly is misleading. |
| Formula/molecule | Macro/workflow or executable epic | Different execution representations; SASE already has typed inputs and rich control flow. |
| Refinery | Finalizer, review hooks, land agent, and VCS provider | Gas Town presents integration as a standing per-rig responsibility with an explicit queue. |
| Mail | Shared artifacts, output variables, notifications, and follow-ups | Those SASE mechanisms do not expose an equivalent general addressed agent mailbox in the inspected surfaces. |

**Addressed communication is Gas Town's strongest distinctive primitive.**

Gas Town exposes agent identities as destinations: a coordinator, a rig's integration agent, a particular worker, a rig broadcast, or a mailing list. Messages carry a subject, type, priority, thread/reply information, and delivery metadata. Separate commands cover sending, reading, claiming queued messages, and checking for new mail. This enables coordination after a launch plan is already running: an API worker can inform its consumer of a changed contract, a reviewer can request clarification, or an integration worker can route rework to the responsible worker. [Mail CLI][g-mail-cli]; [message model][g-mail-types].

There is implementation substance beyond a prompt convention. Delivery bookkeeping distinguishes persisted messages from acknowledged receipt and orders acknowledgement writes for crash recovery. Mail read/check and queue-claim paths call that machinery. The nudge queue offers cooperative delivery at a natural runtime boundary, with expiry and queue limits; it explicitly avoids the disruption of blindly injecting terminal input. [Delivery implementation][g-delivery]; [mail check][g-mail-check]; [queue claiming][g-mail-queue]; [nudge queue][g-nudge].

The durability claim needs precision. Mail defaults to ephemeral database-backed wisps; the permanent option requests retention/sync beyond that mode. A normal message can outlive an agent session without being a permanent remote artifact. Nudges also expire. Receipt acknowledgement is not proof that the requested work was completed, and I found no basis for claiming universal exactly-once processing. [Mail CLI flags][g-mail-cli]; [delivery implementation][g-delivery].

SASE can coordinate well-defined pipelines through waits and structured outputs, and it has durable human notifications and follow-up turns. However, searches through its agent CLI, launch machinery, documentation, and Rust domains did not uncover a comparable general inter-agent mailbox. The missing convenience is ad hoc communication addressed to an ongoing responsibility, rather than reconstructing a new prompt or having the operator carry information between runs. This is a high-confidence capability gap within the inspected scope. [SASE agent CLI][s-agent-cli]; [architecture][s-arch]; [notification types][s-notifications].

For SASE, the compatible adaptation is a host-owned inbox consumed by the next session turn or an explicit supported delivery boundary. It need not keep providers alive, interrupt tools, or let messages bypass launch approval. Immutable artifact references should carry large payloads; message IDs, recipient generation, acknowledgement, and expiry should remain separate fields. For independent research swarms such as this one, delivery policy must preserve the deliberate isolation between researchers.

**Convoys make cross-project work and stranded work easier to operate.**

Gas Town's convoy is a persistent collection of related work items across rigs, independent of the particular workers currently executing them. Its staging command accepts an epic, existing tasks, or an existing convoy and produces a structured result with findings, waves, gated tasks, and a tree. This gives an operator a direct way to ask what a deliverable comprises and which work is blocked. [Convoy concept][g-convoy]; [stage implementation][g-stage].

More significantly, the daemon actually starts a convoy manager. It watches lifecycle events across stores and periodically scans for stranded convoys. When a convoy has ready work but no workers, it tries to dispatch a ready item. It skips unavailable/parked routes and tries another candidate if a dispatch fails. The implementation includes a startup sweep, serialized scans, recovery behavior after database polling failures, and tests for dispatch failure, parked rigs, and multi-store events. This is a concrete closed loop between persistent work state and execution, not just a dashboard. [Daemon startup][g-daemon]; [convoy manager][g-manager]; [manager tests][g-manager-tests].

SASE already supports cross-project targets and explicit waits on a bead belonging to another enabled project. It also has dependency-wave previews and scheduler reconciliation. The narrower difference is that its epic planner operates on the authored phases of an epic, and the inspected Rust planner rejects an open, known blocker outside that epic. Supplying multiple bead-work targets uses ordered command processing, rather than constructing one cross-project delivery graph. Thus “SASE has no cross-project work” would be false; “Gas Town offers a more direct cross-project collection and reconciliation model” is supported. [SASE bead work][s-work]; [Rust epic planner][s-core-work].

The practical example is a coordinated change spanning a Rust library, Python binding, editor plugin, and documentation. Those may remain separate projects and plans while still belonging to one deliverable. Gas Town provides a more obvious operational container for them. SASE could project such a view over existing goals, epics, waits, and artifacts instead of adding another synonymous work-item type. The invocation's goal policies should be preserved: machine task completion must not automatically settle a person's goal.

The autonomous part is less certain than the capability itself. The manager's normal stranded scan is 30 seconds, but that is a configured mechanism, not a measured recovery SLA. Redispatch can also be wrong if ownership evidence is stale. The useful lesson is the explicit invariant “ready authorized work should have an owner or an explained reason,” not aggressive restart behavior.

**The integration queue is valuable; advertised automatic batching is not established.**

Gas Town exposes ready, blocked, claimed, and anomalous merge requests separately from workers. Its refinery patrol specifies branch rehearsal against the effective target, configured quality checks, failure handling, merge/push, and completion feedback. It also handles integration branches and direct versus PR-based merging. This packages a recurring responsibility: ensuring concurrently produced changes become one working branch. [Refinery CLI][g-refinery-cli]; [refinery patrol][g-refinery-patrol].

For a busy SASE project, a persistent view of “coding finished, waiting to integrate,” blocked integration, and repair ownership could be more useful than looking across individual finalizer results and PRs. A queue also provides a natural home for admission and fairness at the integration stage. SASE's existing finalizers and land agents substantially reduce the size of this gap; the advantage is explicit queue ownership and operations, not the invention of verification or automated repair. [SASE finalizer][s-final]; [GitHub submission][s-gh].

There is an important source-level qualification. The README says the Refinery uses a Bors-style batching and bisection queue. The batch implementation contains AssembleBatch and ProcessBatch, and tests cover merging a good subset after a failing batch. But repository-wide searches found no production call sites for either function: only their definitions and tests. The shipped refinery patrol instead instructs processing branches one at a time. Therefore I would describe batching as implemented/tested library machinery whose normal runtime integration was not established—not a demonstrated user-facing performance advantage. [README][g-readme]; [batch implementation][g-batch]; [batch tests][g-batch-tests]; [patrol][g-refinery-patrol].

Verification also depends on configuration: empty check commands are skipped, and the patrol can disable tests. A role description does not itself guarantee an independently verified merge. SASE should preserve host-owned finalization and its existing receipt policy rather than substitute agent assertions or infer that a previous passing run authorizes skipping verification. Start any integration-queue experiment with serial, exact-candidate validation. Consider batching only after measuring integration contention and testing non-additive failures, moving targets, and flaky checks.

**Diagnosis-to-repair coverage is broader in Gas Town.**

Gas Town's doctor has a common check/fix contract and rechecks after a successful fix. Concrete checks include worktree metadata, hook attachment invariants, orphan processes/sessions, and dead workers with unpushed commits. The last is especially operationally useful: it recognizes valuable stranded output before cleanup, and its fix path attempts to push the branch. [Doctor framework][g-doctor]; [stalled-worker check][g-stalled]; [worktree check][g-worktree]; [hook checks][g-hook-check].

SASE's diagnostics are not missing or entirely read-only. Although a guide describes read-only modes, the current CLI also exposes duplicate-Patch-block and primary-sidecar-link repair options. Other domains have their own repair commands, including workspace and goal repair. SASE's auto-restart system also has eligibility classification, a retry bound, storm protection, and audit records. The advantage is Gas Town's breadth under a common operational repair entry point, not a binary “can repair/cannot repair” distinction. [SASE doctor CLI][s-doctor]; [workspace operations][s-workspaces]; [recovery guide][s-recovery]; [goal ledger][s-goals].

The appropriate improvement is a typed repair catalog connecting a failed invariant to a previewable action and a postcondition. Actions that publish work or terminate a process should expose those effects rather than hide behind an indiscriminate “fix everything.” This could reuse SASE's existing commands and gate machinery. It need not become an autonomous LLM doctor.

**Escalations make unresolved work a managed lifecycle.**

Gas Town supplies a dedicated escalation record with severity, acknowledgement, closure, routing, and stale re-escalation. The CLI implementation creates tracked state and dispatches notifications; the stale command consults configured thresholds and a maximum re-escalation count. It also records delivery failures, rather than treating creation of an escalation as proof every recipient was reached. Some richer category routing remains explicitly future work in its design document. [Escalation design][g-escalation]; [commands][g-escalation-cli]; [implementation][g-escalation-impl].

SASE already has durable gates, notification acknowledgement, deduplication, timeouts, error notifications, and transport integrations. What I did not find is a comparable general contract that promotes an unresolved incident through ownership and severity over time. This is a moderate-confidence gap, because existing scheduler jobs and notification plugins can approximate portions of it. The useful extension would be ownership and escalation policy on existing blocked-work notifications, with human consent still governing actions. Simply adding email/SMS channels would not address the core issue. [SASE gates][s-gates]; [notification types][s-notifications]; [scheduler routines][s-routines].

**External observability is a real but conditional advantage.**

Gas Town has an opt-in OpenTelemetry exporter for logs and metrics, a documented run identity, and instrumentation connecting agent creation, state changes, mail operations, and other events. Calls from session startup, the daemon, and mail handling show that this is wired into runtime paths. That is useful for operators who already aggregate telemetry across machines or want to correlate the orchestration layer with other infrastructure. [OTel data model][g-otel-model]; [exporter][g-otel]; [recorders][g-recorders]; [session instrumentation][g-session].

SASE already has local telemetry stored through Rust in SQLite, retention and rollups, health diagnostics, and historical usage views. Its documentation explicitly says the previous bundled external monitoring stack was removed. Thus Gas Town's advantage is optional compatibility with external observability systems, not basic visibility. SASE's local approach is likely the better default for a single operator. [SASE telemetry][s-telemetry].

Gas Town's costs command is also concrete, including role/rig breakdowns and daily digests, but the inspected command explicitly derives costs from Claude Code transcripts. I would not promote it into a general multi-provider accounting advantage. Nor did I establish complete OTel event coverage for every supported runtime. [Costs implementation][g-costs].

**Useful packaging, without a reason to copy the whole architecture.**

The Mayor, Witness, Refinery, and Deacon make coordination responsibilities visible, and the repository ships reusable role prompts and operational formulas. That can make an unattended workflow easier to describe and invoke. However, SASE already has macros, plugins, phase/land roles, configurable autonomy, and deterministic scheduler jobs. I see a packaging opportunity—curated workflows with clear progress and repair contracts—rather than evidence that SASE needs Gas Town's terminology, a second workflow language, or permanently running supervisory models. [Gas Town formula package][g-formula]; [SASE workflows][s-workflows]; [bead work][s-work].

I would not count federation/reputation, a formula marketplace, theoretical “20–30 agent” scale, or generalized self-healing as proven advantages on this evidence. Some are documented visions or depend on external systems; others need a workload and measurement. SASE already has fleet and mobile surfaces, so a web dashboard alone is also insufficient to establish superiority. [Gas Town README][g-readme]; [formula-marketplace design][g-marketplace]; [SASE mobile gateway][s-mobile].

**Counterevidence that should shape adoption.**

Recent upstream reports make the distinction between an attractive mechanism and a reliable system especially important:

- September 29 issue **#4890** reports a reused worker being killed immediately because an idle reaper reads its previous session's state. The report explicitly names HEAD-649b832, matching the revision inspected here. Treat this as a strong reason to require generation-aware liveness before automatic redispatch or cleanup. [Issue #4890](https://github.com/gastownhall/gastown/issues/4890).
- September 25 issue **#4887**, also naming HEAD-649b832, reports usage-limit waits being indistinguishable from hangs. A SASE reconciliation policy should distinguish provider throttling, legitimate long tools, human gates, and dead ownership. [Issue #4887](https://github.com/gastownhall/gastown/issues/4887).
- September 15 issue **#4870** reports failed hook persistence producing orphaned patrol state. It names a different development revision, so it is ecosystem risk evidence rather than a demonstrated bug in this checkout. [Issue #4870](https://github.com/gastownhall/gastown/issues/4870).

These were open reports when consulted, not independently reproduced findings. They do not cancel Gas Town's coordination advantages, but they rule out presenting watchdog breadth as proof of superior reliability. A useful SASE adaptation should put durable intent, execution generation, idempotency, and verified postconditions ahead of recovery aggressiveness.

**How I would evaluate the changes.** Use a small repeated workload containing independent tasks, one dependency chain across repositories, one conflicting change, one failed worker, and one deliberately gated decision. Record time from ready task to assignment, time from finished work to verified integration, human interventions, duplicate launches/messages, lost output, and supervision tokens. Compare improvements against the current SASE workflow on the same providers and capacity. The first target should be less operator coordination at unchanged correctness, not a larger count of simultaneous agents.

The following source references resolve to the exact inspected revisions; issue links above remain live discussions.

[s-arch]: https://github.com/sase-org/sase/blob/f3087c86acbbd2e445a7a0054e3d596aafeeeb95/docs/contribute/architecture.md
[s-work]: https://github.com/sase-org/sase/blob/f3087c86acbbd2e445a7a0054e3d596aafeeeb95/docs/reference/work-units/bead-work.md
[s-workflows]: https://github.com/sase-org/sase/blob/f3087c86acbbd2e445a7a0054e3d596aafeeeb95/docs/reference/workflows.md
[s-final]: https://github.com/sase-org/sase/blob/f3087c86acbbd2e445a7a0054e3d596aafeeeb95/docs/contribute/commit-workflow-orchestrator.md#commit-finalizer
[s-gh]: https://github.com/sase-org/sase-github/blob/8712c153aa969eef55bccbabe2e0e94a50764a68/src/sase_github/workspace/submit.py
[s-agent-cli]: https://github.com/sase-org/sase/blob/f3087c86acbbd2e445a7a0054e3d596aafeeeb95/docs/reference/cli/agent.md
[s-notifications]: https://github.com/sase-org/sase/blob/f3087c86acbbd2e445a7a0054e3d596aafeeeb95/docs/reference/automation/notification-types.md
[s-core-work]: https://github.com/sase-org/sase-core/blob/594faf31d80af79a148cb67968318b2bfb1a5770/crates/sase_core/src/bead/work.rs#L115
[s-doctor]: https://github.com/sase-org/sase/blob/f3087c86acbbd2e445a7a0054e3d596aafeeeb95/docs/reference/cli/doctor.md
[s-workspaces]: https://github.com/sase-org/sase/blob/f3087c86acbbd2e445a7a0054e3d596aafeeeb95/docs/reference/agents/workspaces.md
[s-recovery]: https://github.com/sase-org/sase/blob/f3087c86acbbd2e445a7a0054e3d596aafeeeb95/docs/guides/recover-interrupted-agent.md
[s-goals]: https://github.com/sase-org/sase/blob/f3087c86acbbd2e445a7a0054e3d596aafeeeb95/docs/reference/work-units/goals.md
[s-gates]: https://github.com/sase-org/sase/blob/f3087c86acbbd2e445a7a0054e3d596aafeeeb95/docs/reference/automation/notification-gates.md
[s-routines]: https://github.com/sase-org/sase/blob/f3087c86acbbd2e445a7a0054e3d596aafeeeb95/docs/reference/automation/scheduler-default-routines.md
[s-telemetry]: https://github.com/sase-org/sase/blob/f3087c86acbbd2e445a7a0054e3d596aafeeeb95/docs/contribute/telemetry.md
[s-mobile]: https://github.com/sase-org/sase/blob/f3087c86acbbd2e445a7a0054e3d596aafeeeb95/docs/reference/integrations/mobile-gateway.md
[g-mail-cli]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/cmd/mail.go
[g-mail-types]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/mail/types.go
[g-delivery]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/mail/delivery.go
[g-mail-check]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/cmd/mail_check.go
[g-mail-queue]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/cmd/mail_queue.go
[g-nudge]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/nudge/queue.go
[g-convoy]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/docs/concepts/convoy.md
[g-stage]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/cmd/convoy_stage.go
[g-daemon]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/daemon/daemon.go#L553
[g-manager]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/daemon/convoy_manager.go
[g-manager-tests]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/daemon/convoy_manager_test.go
[g-refinery-cli]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/cmd/refinery.go
[g-refinery-patrol]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/formula/formulas/mol-refinery-patrol.formula.toml
[g-readme]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/README.md
[g-batch]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/refinery/batch.go
[g-batch-tests]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/refinery/batch_test.go
[g-doctor]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/doctor/doctor.go
[g-stalled]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/doctor/stalled_polecat_check.go
[g-worktree]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/doctor/worktree_gitdir_check.go
[g-hook-check]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/doctor/hook_check.go
[g-escalation]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/docs/design/escalation.md
[g-escalation-cli]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/cmd/escalate.go
[g-escalation-impl]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/cmd/escalate_impl.go
[g-otel-model]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/docs/otel-data-model.md
[g-otel]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/telemetry/telemetry.go
[g-recorders]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/telemetry/recorder.go
[g-session]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/session/lifecycle.go
[g-costs]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/cmd/costs.go
[g-formula]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/internal/formula/README.md
[g-marketplace]: https://github.com/gastownhall/gastown/blob/649b832b7672bc7a2dbef26f5983aba6198b819b/docs/design/mol-mall-design.md

**Ranked ways Gas Town is superior to SASE in the inspected comparison.** Ranking reflects likely coordination value, breadth of applicability, and evidence confidence—not popularity or a benchmark result.

1. **General addressed agent communication — high confidence.** Mailboxes, routing, threads, delivery acknowledgement, queued work, and cooperative nudges provide a direct coordination primitive that the inspected SASE surfaces do not offer. Most valuable when plans change while several agents are already working.
2. **Cross-project work collections with active stranded-work reconciliation — high confidence in capability; medium in reliability.** Convoys preserve the deliverable independently of worker sessions and connect ready work back to dispatch. SASE has many ingredients but a less direct equivalent for mixed existing tasks spanning projects.
3. **Explicit integration responsibility and queue operations — medium-high confidence.** The Refinery makes ready, blocked, claimed, and anomalous integration work operationally visible. SASE already finalizes, verifies, repairs, and lands work; the extra benefit is queue ownership across completed workers. Automatic batch/bisect throughput is excluded from this ranking because production wiring was not found.
4. **A broader common diagnosis-and-repair surface — high confidence in breadth.** Gas Town puts more workspace, assignment, process, and stranded-output checks behind one repair framework. This is an operator-effort advantage, not evidence that its repair actions are safer.
5. **An explicit escalation lifecycle — medium confidence.** Tracked severity, acknowledgement, routing, and bounded stale re-escalation make persistent blockers harder to forget. SASE's gates and notifications provide a strong base but do not expose the same general lifecycle in the inspected scope.
6. **Native optional export to external observability systems — high confidence, conditional value.** OTLP logs/metrics and run correlation help multi-machine operators who already use that infrastructure. SASE's local telemetry remains a substantial capability and a sensible default.

**Ranked changes worth considering for SASE.** These are recommendations from this investigation, not filed tasks or an authorized implementation plan.

1. **Add a work-centered progress and reconciliation view over existing records.** Show each deliverable's ready, running, waiting, failed, awaiting-integration, and verified work with an accountable owner or explicit blocking reason. Support references across projects and epics without duplicating goals or beads. Begin with diagnosis and an operator-invoked resume; enable bounded redispatch only after generation-aware ownership checks are proven. Success criterion: a lost worker or unavailable project is visible without manually reconstructing several runs, and independent authorized work continues without duplicate execution. Expected scope: medium to large, mostly in sase-core with thin CLI/TUI adapters.
2. **Introduce durable session-addressed messages at safe turn boundaries.** Start with direct send/read/ack and artifact references, using stable session identity plus recipient generation. Preserve single-turn execution, independent-swarm isolation, and launch authorization; require an explicit continuation policy before a message starts another model turn. Add broadcast and work queues only after direct delivery is reliable. Success criterion: a message sent during a restart reaches the intended successor, acknowledgement is distinguishable from task completion, and a correction requires no operator copy/paste. Expected scope: medium to large.
3. **Unify existing repair mechanisms behind a typed catalog.** Each finding should name evidence, the proposed mutation, its scope, and a checkable postcondition. Connect current workspace, sidecar, claim, goal, and finalizer repairs before adding new ones. Keep preview and execution distinct where actions publish or terminate work. Success criterion: the most frequent support failures can be diagnosed and repaired from one surface with a durable result and a successful recheck. Expected scope: medium; likely an earlier payoff than a new merge engine.
4. **Pilot a host-owned integration queue for projects with measured contention.** Reuse finalizer declarations, VCS providers, ToolRun evidence, and existing repair turns. Begin with serial integration, explicit target/source revisions, visible ownership, and one bounded repair path; keep verification tied to the candidate actually being landed. Do not implement batching or receipt-based skipping merely because Gas Town advertises them. Success criterion: lower finished-to-landed latency and fewer operator conflict interventions, with no increase in invalidated or missing verification. Expected scope: large; validate the workload need first.
5. **Extend blocked-work notifications with ownership and bounded escalation.** Reuse gates and notification transports, adding responsible party, acknowledgement, next-review time, resolution, and a capped escalation policy. Prefer a consolidated blocker digest to repeated alerts. Success criterion: an unattended failure remains visible and reaches the right decision-maker without duplicate incidents or treating silence as consent. Expected scope: medium.
6. **Ship a small set of curated coordination workflows.** Package “implement a dependency graph,” “review and integrate completed work,” and “inspect/recover stranded work” using existing macros, scheduler jobs, and adapters. Explain input, output, authority, and recovery behavior in plain terms. Success criterion: an operator can run and recover the workflow without learning internal grouping syntax or installing a standing LLM bureaucracy. Expected scope: small to medium; can accompany recommendations 1–5.
7. **Offer external telemetry as an optional adapter, only for a demonstrated consumer.** Export selected existing lifecycle and tool events with stable correlation IDs, bounded cardinality, and content redaction; retain local SQLite telemetry as authoritative for local operation. Do not restore a mandatory monitoring stack or claim provider-neutral dollar accounting from Claude-only data. Success criterion: one concrete cross-machine diagnosis becomes easier without adding dependencies to the default path. Expected scope: medium; lower priority for a single-operator setup.
