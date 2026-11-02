# Agent Hijack: Preserve the Work, Replace the Turn

Independent research by **cdx**, 2026-11-02.

**Recommendation:** Build this feature, but treat it as an operator-controlled recovery transaction. A successful hijack stops the current execution, retains exclusive workspace custody, and leaves a visible HIJACKED agent awaiting a decision. Recovery either starts a new turn with the existing work or deliberately starts fresh. Those are different operations and should look different in the interface.

This report independently examines the local SASE and sase-core checkouts and relevant primary documentation. It does not consult other reports or researchers in this swarm. It proposes a design; it does not implement the feature, modify the glossary, or test termination against live agents.

The source baseline is SASE commit **84e22d98be6b6ab289730573cb2525b11b7d7ea0** and sase-core commit **89a5bd8b810ab20fee5c223bb4b1e40cb2c3ab68**. Repository links below identify code inspected locally at those revisions. Shipped model defaults are examples of current behavior, not a claim about the operator's effective merged configuration.

**This is a good idea because it separates stopping execution from abandoning work.** A stalled provider, runaway tool, or unproductive reasoning loop should not force the user to choose between waiting indefinitely and losing access to a useful checkout. SASE already has much of the infrastructure needed: verified process termination, pinned workspace claims, successor delivery, and inheritance of commit responsibility.

The feature is less useful if it becomes an automatic stall detector or a shortcut to replaying the same failure at a higher price. Silence is not proof of a stall. A smarter model cannot repair an unavailable provider, a blocked credential prompt, or a broken host. Keep the first version manual. Show the last activity and tool state as evidence, and let the operator decide.

**The requirements should change in these specific ways.**

| Requested behavior | Recommended adjustment | Reason |
| --- | --- | --- |
| Kill without release or dismissal | Keep this contract, with an intermediate HIJACKING state until termination is verified | Sending a signal does not establish that tools have stopped writing |
| Restart using the exact same prompt | Preserve the original authored prompt and launch provenance; distinguish prompt replay from identical execution | Aliases, macro expansion, attachments, repository HEAD, and external effects can change |
| Dismiss and release, then edit | Open a recovery draft first; dismiss/release only when the user submits the replacement | Cancelling the editor should leave the held work and node intact |
| Escalate to @large unless the previous alias was @large | Use @large → @xlarge; do not automatically send @xlarge back to @large | The literal rule can downgrade and oscillate |
| Escalation preserves the workspace | Preserve the whole custody chain, including linked repositories and finalizer baselines | Merely reusing a directory can cause inherited changes to be treated as pre-existing foreign work |
| Three recovery choices | Add Continue with same model, Inspect work, Dismiss, and Escape to leave held | Provider failure does not always warrant a model change or a fresh checkout |
| Implicit release semantics | Save a verified recovery snapshot before fresh restart or dismissal of dirty work | Releasing a claim makes the checkout available for later reuse; it is not durable preservation |
| No stated expiration policy | Explicit hijacks remain held until recovery or deliberate dismissal | The current generic held-claim TTL is incompatible with an indefinite preservation promise |

These are proposed changes for the implementation decision, not silent reinterpretations of the request.

**“Agent Hijack” is a useful glossary term if its definition states the lifecycle boundary.** Proposed wording:

> An Agent Hijack, or hijack, is a user-requested takeover of recovery control that stops a sase agent's current agent turn while retaining exclusive custody of its workspace and preserving its agent node and recovery evidence. Once termination is verified, the node displays HIJACKED until the user starts a successor or dismisses it. A hijack does not complete the work, resume the killed process, or release the workspace.

Use **Hijack** for the command and **Recover agent** for the panel title. Use “Continue” for a new turn with preserved work, rather than “Resume,” which suggests the killed process or provider conversation can be restored. Publish the glossary strand through the memory-writing workflow when implementing the accepted design. No live memory change is part of this research.

**The existing code makes this a lifecycle feature, not a new color and keybinding.**

| Finding from inspected code | Consequence for implementation |
| --- | --- |
| The runner's SIGTERM handler normally calls release_workspace and clears the occupant record; staged handoffs are exceptions | Establish durable hijack intent and release protection before signalling. [Signal handler](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/axe/run_agent_runner_signals.py#L32) |
| Shutdown policy explicitly declines to hold when was_killed is true, and kill persistence also releases claims | Both graceful cleanup and external cleanup must understand hijack; changing only the signal handler is insufficient. [Runner shutdown](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/axe/run_agent_runner_lifecycle.py#L108), [kill persistence](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/ace/tui/actions/agents/_kill_persistence.py#L152) |
| Pinning rewrites an existing claim under a lock without making the slot available | Reuse this mechanism, but add a distinct explicit-recovery retention reason and stronger lifecycle checks. [Claim hold](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/running_field/_hold.py#L11) |
| Generic stale cleanup can release a pinned dead-PID claim if its artifacts or done marker are missing; otherwise age-based release defaults to 14 days | A PINNED bit alone cannot implement hijack. Recovery intent must independently protect allocation and cleanup, including after abrupt death. [Stale cleanup](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/ace/scheduler/stale_running_cleanup.py#L181), [TTL configuration](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/default_config.yml#L2176) |
| Termination already verifies process identity, discovers descendants and registered supervisors, escalates, and returns survivors | Reuse the verified terminator, separately from destructive kill/dismiss side effects. [Terminator](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/agent/_user_kill_tree.py) |
| Existing restart preflights the prompt, then stops/dismisses, wipes name ownership, and launches; its recovery bundle primarily saves prompts and metadata | Useful for fresh replay, unsuitable as the implementation of preserve-work escalation. Its bundle is not a complete checkout snapshot. [Restart planning](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/agent/_restart_planning.py), [execution](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/agent/_restart_execute.py), [bundle](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/agent/_restart_recovery.py) |
| Workspace transfer updates the claim in place; detached successor delivery persists identities and refuses ambiguous duplicate launches | Adapt these seams for recovery instead of release-then-reclaim or an ad hoc detached spawn. [Transfer](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/running_field/_transfer.py#L12), [successor delivery](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/axe/run_agent_successor_delivery.py#L164) |
| Continuations inherit baselines and opened-repository responsibility, but some call sites are best-effort | Hijack recovery needs a required, verified inheritance result before starting the provider. [Inheritance](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/llm_provider/commit_finalizer_inheritance.py#L33), [bootstrap rationale](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/axe/run_agent_runner_bootstrap.py#L154) |

The existing Rust retention policy is particularly relevant: it distinguishes retained work, release, and ownership that has moved, and requires a successor to be active in the same workspace with inherited obligations. That is the right foundation. An operator-requested hold should remain held even when the checkout happens to be clean; the user explicitly requested custody. [Core retention policy](https://github.com/sase-org/sase-core/blob/89a5bd8b810ab20fee5c223bb4b1e40cb2c3ab68/crates/sase_core/src/workspace_retention/policy.rs)

**The core invariant is exclusive recovery custody.** From acceptance of hijack until explicit release or confirmed successor ownership, no allocator, stale cleanup, auto-restart job, old runner, finalizer, or second recovery request may make the workspace available or create a competing writer. Keep the workspace and its materialized linked/sidecar checkouts in place; do not run checkout preparation, pull, reset, clean, or reclone as part of preserve-work recovery.

A claim record controls SASE, not arbitrary external programs. It cannot stop an unrelated editor from changing files or reverse an API call already accepted by a remote service. Verify the agent's known execution tree, reconcile source fingerprints when capturing or transferring work, and report uncertainty honestly. Do not promise that terminating a local tool rolls back its remote effect.

**Model execution state separately from the unresolved recovery decision.** The old provider turn is terminal once it is dead. The user-facing agent remains unresolved because it still holds work. I recommend a structured stop reason and recovery record, with core-derived public status HIJACKED, rather than making every consumer infer it from a file or a Python render override.

The current published run-state resolver accepts only active/waiting and completed/failed/stopped/dismissed. Extend its wire contract deliberately, along with indexing and publication. One reasonable representation preserves execution state “stopped,” adds stop_reason “hijacked” and recovery identity, and derives HIJACKED for the public agent node. Do not equate this with today's display STOPPED: the TUI currently describes STOPPED as a repeat slot that never ran. [Run-state resolver](https://github.com/sase-org/sase-core/blob/89a5bd8b810ab20fee5c223bb4b1e40cb2c3ab68/crates/sase_core/src/agent_run_state/resolve.rs#L5), [TUI status predicates](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/ace/tui/models/agent_status.py)

| State visible to the user | Execution/custody meaning | Permitted next actions |
| --- | --- | --- |
| RUNNING | Current turn owns and uses the workspace | Hijack, existing actions |
| HIJACKING | Durable intent exists; termination is being verified | Inspect progress; leave panel |
| HIJACKING · attention needed | Some process survives or identity/custody cannot be established | Retry termination or inspect evidence; no successor |
| HIJACKED | Execution stopped; workspace held; recovery unresolved | Continue, change model, restart fresh, edit, inspect, dismiss |
| RECOVERING | One durable recovery choice owns a reserved successor identity | Observe; repeated input attaches to this operation |
| RUNNING on successor | Successor owns workspace and inherited obligations | Normal actions; predecessor remains in history |
| Dismissed | Hold released through an ownership-checked operation | Normal archive/recovery-snapshot access |

If the target completed before hijack won the lifecycle race, return “Already completed” and preserve that result. Do not rewrite success into HIJACKED. If death is known but workspace custody is lost, show the failure explicitly and disable preserve-work recovery; never claim “workspace held.”

HIJACKED belongs in the existing stopped/attention presentation bucket, not in running capacity or successful completion counts. Show a held-workspace count separately if needed. A selected session node targets its one current concrete turn. A clan or group must not silently hijack every member. Multiple eligible targets should require choosing a concrete member; bulk hijack can wait.

A hijacked turn is not a successful dependency. Session-target waits stay unresolved while recovery is pending and follow the session's successor. Turn-target waits observe the old turn's stopped outcome according to their existing completion policy; success-dependent downstream work must not be released as successful. Dismissal without replacement explicitly cancels the unresolved work. Preserve goal/task identity on a continuation, and transfer or hold associated ownership consistently so schedulers cannot launch a competing worker.

**A reliable hijack is a durable operation outside the target process.**

1. Resolve an exact run identity, owning machine, current turn, process identity, claim, and lifecycle phase. Check capabilities and reject unsupported targets before mutation.
2. Serialize against terminal finalization and other recovery actions. Persist a request ID, source identity, expected claim owner/generation, and requested disposition. Pin the claim under the ownership lock. Only signal after durable protection is established.
3. Stop the provider, runner, and owned tool processes through the existing verified termination machinery. Reuse its grace policy: the current six-second grace intentionally outlasts the tool wrapper's five-second escalation. An unconditional immediate SIGKILL would skip useful cleanup. [Termination policy](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/agent/_user_kill_types.py#L14)
4. Record the verified outcome and remaining processes. Publish HIJACKED only after successful quiescence and confirmed retained custody. Capture available prompt, transcript, tool, repository, and finalizer evidence; do not require the stalled model to generate a handoff summary.
5. Reconcile incomplete operations after a host/TUI restart. Missing or corrupt recovery evidence must preserve the hold and surface an error, rather than make the checkout look free.

Use a journal with explicit phases because a process signal and multiple file writes cannot form one ordinary database transaction. Each boundary must be idempotent. A crash after recording intent but before pinning should be repairable without any signal having been sent. A crash after signalling must leave enough evidence to finish verification. Claim policy must recognize the pending operation, so missing done.json cannot turn that crash window into a free workspace.

The systemd lifecycle model supports the same general principle: terminating only the main process can leave service-owned processes running, and the documented stop sequence escalates after a grace period. This is corroboration, not a recommendation to rewrite SASE around systemd. [systemd kill procedure](https://www.freedesktop.org/software/systemd/man/latest/systemd.kill.html)

Retain SASE's process-identity checks. On Linux, pidfds can strengthen signalling by avoiding PID-reuse races; this is an implementation option for the shared termination layer, not a prerequisite for a new platform-specific feature branch. [Linux pidfd_send_signal documentation](https://man7.org/linux/man-pages/man2/pidfd_send_signal.2.html)

**The new operation must win against every old cleanup route.** Specifically audit SIGTERM handling, normal shutdown, cleanup persistence, staged-handoff reconciliation, stale workspace cleanup, automatic restart, dismissal, agent artifact pruning, and finalizer settlement. A late callback from the old run must not release the successor's claim or overwrite its status. Use exact run/claim identities and an operation generation, rather than workspace number or PID alone.

SASE already excludes killed/stopped/cancelled work from auto-restart. Add explicit hijack exclusion using authoritative intent, including the interval before a stopped marker is published. Cancelling or superseding a pending staged handoff must use its own lifecycle API; leaving it armed could launch a second successor. Never fabricate a successful pipe marker just to borrow its workspace-release exception. [Auto-restart classification](https://github.com/sase-org/sase-core/blob/89a5bd8b810ab20fee5c223bb4b1e40cb2c3ab68/crates/sase_core/src/agent_auto_restart/classify.rs#L306)

Finalization requires a clear boundary. If a host finalizer has acquired authority to commit or publish, reject hijack as temporarily unavailable and show that phase. Do not SIGKILL through an irreversible operation and call the result safe. Later support for stalled finalizers needs a dedicated repair protocol. If hijack acquires authority first, fence subsequent declarations and finalizer starts from that source turn.

**The recovery panel should make consequences legible before the keypress.** Propose a configurable leader binding **,z** for Hijack; that key is unused in the inspected default leader map. Keep x as existing kill/dismiss and ,x as existing kill-and-edit. Add Hijack to the cleanup/action panel for discovery, with the description “Stop and keep workspace.” This preserves familiar behavior while giving users a safer explicit choice.

On a HIJACKED concrete agent node, Enter should open recovery directly. Do not send the user through a generic chooser merely because the agent also has a Patch. Preserve a route to the Patch and evidence inside the panel or normal detail view. Current Enter handling already has a resolver, chooser, and identity revalidation; extend that seam. [Enter resolution](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/ace/tui/actions/agents/_agent_enter_resolver.py#L128), [choice dispatch](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/ace/tui/actions/agents/_agent_enter_action.py#L349)

Illustrative layout; the model and counts are supplied by a read-only preview:

~~~text
╭─ Recover agent · fix-parser ───────────────────────────────────╮
│ HIJACKED       Workspace held       Stopped 2 minutes ago     │
│ 3 changed files · 2 repositories · last tool: pytest          │
│                                                              │
│ Keep this work                                               │
│   c  Continue              Same model, new turn              │
│   s  Change model          @large → @xlarge                   │
│                            Resolved model and effort shown    │
│                                                              │
│ Start fresh                                                  │
│   r  Restart original      Same prompt, fresh workspace      │
│   e  Edit and restart      Opens a draft; keeps hold for now  │
│                                                              │
│   d  Inspect work          Changes, prompt, last output       │
│   x  Dismiss               Save recovery copy, release        │
│                                                              │
│ esc  Leave held             No action selected by Enter      │
╰──────────────────────────────────────────────────────────────╯
~~~

Use a quiet violet accent for HIJACKED, a static status badge, and a short “Workspace held” explanation. Reserve red for errors and destructive discard. Do not rely on color or a new icon alone. Keep the node in place and preserve selection, scroll, folds, and tab placement. A single progress line can change from “Stopping tools…” to “Workspace held”; do not leave a spinner running after death is verified.

Size the panel to available terminal width, wrap explanations, and allow scrolling in a short terminal. Check at 80×24 and with long names, multiple repositories, missing prompts, model unavailability, and a failed stop. Show disabled actions with their reason. Escape closes the panel and leaves the hold; it never resumes or dismisses.

The six letter keys select actions directly. Opening with Enter must not also trigger a default action, including through key-repeat. For c/s/r, one key launches the durable operation after preflight; e opens a draft. No redundant “Are you sure?” is needed when preservation and preflight succeed. Explicit discard without a complete recovery copy should be a separately labelled destructive action, with deliberate confirmation.

Textual's ModalScreen provides scoped keybindings and a dimmed backdrop, and typed dismissal results keep UI choice separate from execution. These support the proposed panel without a custom interaction framework. [Textual modal API](https://textual.textualize.io/api/screen/), [screen result handling](https://textual.textualize.io/guide/screens/)

Follow the project's TUI performance rules: cached facts for rendering, bounded background preview loads, durable procs for kill/recovery work, and identity revalidation after asynchronous boundaries. The UI can immediately show HIJACKING, but must not optimistically claim successful termination. Update the conditional footer, help popup, default keymap, and config schema together.

**Continue with preserved work is the default recovery path.** Both c and s create a fresh provider turn in the same SASE agent session. Preserve the old turn's transcript, artifacts, run identity, and hijack reason. If necessary, promote a one-turn agent into a session using the established naming mechanism; allocate a new suffix rather than wiping the source identity.

Before the successor may invoke a provider:

- Revalidate that the source is stopped and the recovery operation still owns the held claim.
- Reserve a unique successor identity under the recovery operation.
- Assemble its prompt and launch settings, checking provider availability and normal admission rules.
- Inherit primary and opened-repository baselines, responsibility for predecessor changes, task/goal linkage, relevant permissions, and current workspace paths. Failure to establish this is a recovery error, not permission to capture the dirty checkout as a fresh baseline.
- Transfer the existing claim atomically and update the occupant record. There must be no release/reclaim interval.
- Persist launch evidence and require successor acknowledgement before declaring recovery successful.

If admission is queued, keep custody while waiting and retain the same reservation. If launch clearly fails before starting, return to a recoverable held state. If it may have started, reconcile the reserved identity; do not blindly spawn again. Existing detached successor delivery already treats ambiguous submitted launches conservatively. Do not claim “exactly once” execution of arbitrary external tools.

The new turn gets the original task, an explicit statement that it inherits partial work, the relevant user recovery instruction, repository/diff summary, known tool outcomes, and links to original evidence. Keep this packet bounded. Offer the full transcript on demand; do not depend on a dead provider's native resume token, copy every stale intermediate thought into a different model, or claim unknown external actions did not occur. Preserve permission scope, but issue fresh turn-bound finalizer context; old declarations or verification receipts are not automatically valid for the successor.

**Fresh restart is a separate transaction.** It deliberately gives up the current checkout after preserving recoverable work. The panel should say so. A good sequence is: validate stored prompt and launch context; capture a verified recovery snapshot of affected repositories; persist the fresh launch intent and prompt; release the old claim and dismiss its visible node through checked APIs; then launch or queue the replacement. If launching fails after release, retain a visible recovery operation with the saved prompt and snapshot location.

SASE has a strict snapshot API separate from its best-effort rescue API. Reuse that distinction. A printed diff is not enough: preserve staged and unstaged changes, untracked files, binaries, unpublished commits, and operation state to the extent the snapshot format supports them. Include linked and sidecar repos and verify their manifests. Report unsupported or excluded material, especially meaningful ignored files or non-Git state, before claiming preservation. [Snapshot API and limits](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/workspace_provider/snapshot.py), [snapshot model](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/workspace_provider/_snapshot_model.py)

A strict snapshot can still have dependencies: the current published-base format relies on recorded remote history retaining its boundary commits. State that limit in recovery details. For a promise of self-contained durable recovery, capture those required objects or prove a retained base; do not relabel the existing format as a complete independent backup.

A snapshot failure leaves the workspace held. The user can retry, continue in place, or deliberately discard. Avoid snapshotting the entire workspace on the initial hijack critical path: stopping the agent is urgent, keeping the directory already preserves its state, and snapshots become required before releasing it.

The edit option uses the existing prompt bar/editor behavior and stash support, but keeps the source hold until submit. A cancelled draft leaves HIJACKED unchanged. On submit, run the same validated fresh-restart transaction. This is a deliberate improvement over ,x ordering, whose current implementation dismisses optimistically and uses a cleanup barrier to defer the replacement launch. Reuse its prompt reconstruction and barrier ideas without inheriting its release timing. [Kill-and-edit flow](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/ace/tui/actions/agent_workflow/_entry_relaunch.py#L246)

**“Exact same prompt” needs a precise contract.** Preserve the original raw prompt bytes as evidence and as the restart draft. Also retain the expanded task prompt and effective launch metadata. Identity and recovery provenance should be managed structurally; do not silently overwrite the source prompt to make name reuse work.

The practical restart contract is “the same authored request, launched again through normal current launch rules.” It cannot promise the same repository state, dynamic macro result, alias candidate, or provider response. Show material drift in the preview. If true resolved-input replay is desired, treat it as a separate explicit mode; it needs frozen inputs and cannot safely be approximated by replaying an old rendered string that still contains source-run identity or paths.

Validate that recovery refers to one concrete launch unit. The existing restart planner correctly rejects multi-segment/fan-out and container restarts; preserve that protection. A captured swarm prompt must not relaunch every sibling when the user selects one failed member. Replaying a prompt can also repeat side effects in its surrounding workflow. Keep recovery launch metadata separate and do not rerun completed setup/approval stages as if they were new task text.

**Model selection should be based on launch provenance, not text search.** SASE records model_alias, model_alias_trail, model_alias_origin, resolved provider/model, and effort. Use those facts from the hijacked turn; a literal occurrence of “@large” in a code block or discussion is not an authored model selection. Older runs with incomplete metadata require a guarded fallback through the directive parser and an explicit “previous tier unknown” label. [Alias metadata](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/axe/run_agent_successor_model.py#L31)

| Previous effective size | Suggested next selection | Label |
| --- | --- | --- |
| @xsmall, @small, @medium | @large | Escalate to @large |
| @large | @xlarge | Escalate to @xlarge |
| @xlarge | Stay at @xlarge; offer explicit alternate model choice | Change model; already at highest size |
| Explicit model/custom alias/unknown provenance | Suggest @large, show actual source and destination | Change model; capability increase unverified |

For a nested custom alias, use the effective built-in tier in the recorded resolution trail when unambiguous. Never infer the original alias from the resolved model alone. Defaults and fallback can produce the same model from several sizes.

The shipped @large pool currently includes codex/gpt-6.1-sol@xhigh, and @xlarge can fall back to that same candidate and effort. Thus moving up a size does not always change the concrete model. Show both alias and concrete result; if identical, say so and offer Continue or model selection instead of advertising “smarter.” Do not introduce a speculative universal intelligence ranking. [Shipped alias definitions](https://github.com/sase-org/sase/blob/84e22d98be6b6ab289730573cb2525b11b7d7ea0/src/sase/llm_provider/models.yml#L259)

Preview through a read-only alias resolver. Reserve the chosen resolution once on submission and persist its provenance, rather than rotating a pool on every render or resolving independently for the label and launch. Respect provider disables, capacity, fallback policy, effort semantics, and existing admission. A material change after preview should be surfaced, not silently represented as the originally shown upgrade.

**Keep configuration small.** The first version needs the hijack keymap entry in the established config and help surfaces. It does not need a user-configurable state machine, automatic stall timeout, action DSL, or arbitrary escalation ladder.

Reuse existing model alias configuration. Reuse the existing termination grace instead of adding a competing timeout. Represent “explicit operator hold” in the domain with no automatic expiration; do not disable TTL globally for ordinary failed agents. If operational experience shows abandoned hijacks are common, add reminder timing later, with explicit release as the action. Expiration that silently frees the held workspace would undermine the feature's main promise.

Provide a CLI entry such as **sase agent hijack NAME** and a shared recovery command/service, so the feature works when the TUI itself is unavailable. Extend the current restart surface for fresh replay and expose a clear preserve-work recovery path; finalize exact CLI grammar during implementation. All frontends must call the same core operation. Follow the repository's CLI help, alphabetization, and short-option conventions.

**Implementation belongs across the Rust boundary and the existing adapters.** Put transition validation, eligibility, status derivation, recovery action planning, escalation policy, and ownership decisions in sase-core. Python should gather observations, execute process/filesystem effects, and call the binding. Textual owns presentation, focus, keybindings, and cached display. Update the Python/Rust wire contracts and sase-core-revision.txt together.

Use the existing workspace retention, claim transfer, successor delivery, and baseline inheritance seams, but make their required guarantees explicit for this operation. Add a durable recovery record rather than distributing semantics among unrelated boolean markers. At minimum it records:

| Record area | Essential facts |
| --- | --- |
| Identity | Operation ID, source run/session, owner host, process identity |
| Custody | Workspace identity, expected claim generation/owner, retention reason |
| Progress | Requested/stopping/held/recovering/transferred/released phase, error evidence |
| Recovery choice | Selected action, original prompt reference/digest, resolved launch settings |
| Successor | Reserved name/run ID, delivery state, acknowledgement |
| Evidence | Repository obligations, snapshot references, stop result and survivors |

Store only necessary evidence, preserve source artifacts, and avoid duplicating an entire unrelated ledger. State changes and checked ownership transitions must be replayable after crashes. The Rust retention module can supply policy, while the established durable-proc machinery hosts effects and reconciliation.

Rollout must account for already-running code. An old runner can still execute a release-on-SIGTERM handler after disk code is upgraded. Advertise a hijack protocol capability at launch and refuse unsupported old runners with a clear explanation, unless an independently verified compatibility path provides the same protections. A stale TUI/backend must not reinterpret a new held state as ordinary dead work. Gate the feature until the participating controller, runner, and cleanup paths support it.

Start with local, concrete agent turns owning managed workspaces. Queued rows should retain their existing stop/edit semantics. Gate turns, monitor turns, and workflows with separate supervisors need their own cancellation/ownership rules. Home-mode agents lack the managed checkout guarantee; remote agents must be acted on by their owning host, not by signalling a local PID with the same number. For the first release, disable unsupported categories visibly rather than pretending success. This is an explicit scope reduction; broad session and fleet support should follow the same protocol once verified.

**The test plan should attack failure windows, not only menu callbacks.**

| Scenario | Required result |
| --- | --- |
| Repeated hijack or two TUI/CLI clients | One durable stop operation and one held source |
| TERM ignored; late descendant; escaped registered supervisor | Escalate and verify; report survivors; no competing successor |
| PID reused or owner machine mismatched | No signal to an unrelated process |
| Crash after intent, pin, signal, or death, before done.json | Reconciler preserves custody and finishes or exposes recovery |
| Stale cleanup and 14-day TTL sweep while hijacked | Explicit hold survives regardless of dead PID or missing completion marker |
| Normal completion races hijack | One terminal authority wins; no forged successful completion or stale release |
| Finalizer already committing/publishing | Hijack refuses the unsafe transition; no partial operation disguised as success |
| Old runner cleanup after successor claim transfer | Exact owner check prevents release of the successor's workspace |
| Repeated recovery key, lost spawn acknowledgement, controller restart | One reserved destination; ambiguous launch stays held for reconciliation |
| Primary plus linked/sidecar changes | Successor sees files and inherits their finalizer responsibility |
| Inheritance unavailable or malformed | No provider start; source remains recoverable |
| Edited prompt cancelled or provider disabled | Hold remains, source node remains, draft is recoverable |
| Fresh restart with staged/untracked/binary/unpublished work | Snapshot verified before release; failure prevents automatic discard |
| @large, @xlarge, nested alias, default alias, same concrete result | Deterministic policy with accurate labels and provenance |
| Fan-out source prompt or session/clan selection | Only the intended concrete turn can be recovered |
| Auto-restart, pending handoff, task claim, and dependency races | No second worker and no false success notification |
| Narrow terminal, long names, asynchronous refresh, Enter repeat | Usable panel, stable focus, no accidental action |

Extend existing termination, restart, workspace-retention, successor, and Enter-resolution test families. Add process integration tests in disposable workspaces and fault injection at transaction boundaries, plus TUI snapshots for the proposed states. Do not make the test suite terminate real user agents. The essential end-to-end proof is: modify primary and linked repositories, hijack, restart the controller, continue with a different model, and verify the successor both sees and owns those changes through finalization.

**The alternatives are weaker for this particular request.** SIGSTOP/SIGCONT preserves process memory but leaves a suspended process and its resources in the system, does not establish a clean single-turn replacement boundary, and does not help when the provider or tool is irrecoverably wedged. Killing and later re-pinning has a workspace-allocation race. A generic restart loses the preserved-work contract. A normal agent-authored pipe assumes cooperation from the agent being rescued. Automatic idle-triggered escalation adds uncertainty and cost before the manual recovery path is proven.

The largest remaining uncertainties are implementation integration, not whether the feature is useful: the exact shared lock/generation boundary across finalizers and claims, complete compatibility with old runners, snapshot coverage for unusual repositories, and how much recovery context users actually need. The inspected source supports the proposed seams, but this report does not establish their behavior under live fault injection. Validate those boundaries before treating the panel as ready.

**Recommended solution:** Ship a manual Agent Hijack operation backed by a Rust-owned recovery state machine and a durable host executor. Establish an explicit non-expiring workspace hold before terminating the verified execution tree; publish HIJACKED only when death and custody are confirmed. Enter opens a compact, keyboard-driven recovery panel whose primary choices continue with preserved work, either on the same model or a transparently resolved larger alias. Keep original restart and edit-and-restart as clearly labelled fresh-workspace alternatives, with verified preservation before release and no dismissal on editor cancellation. Preserve the old turn as history, inherit repository and finalizer responsibility into one successor, prevent @xlarge downgrades, and make failed or ambiguous recovery stay held. This keeps the useful idea while making preservation, ownership, and user choice the feature's actual guarantees.
