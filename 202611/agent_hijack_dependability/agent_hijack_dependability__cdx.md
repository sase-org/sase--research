# Dependable agent hijacks across SASE turn lifecycles

Independent research by **cdx**, 2026-11-15. This report evaluates the proposal to make hijacks work across more turn kinds and lifecycle states. No detailed implementation plan was supplied; the critique therefore concerns that goal and the implementation approaches it suggests. I did not consult this swarm's other researchers, reports, or transcripts. This is research, not an implementation change.

The proposal is worthwhile. The screenshot exposes a mismatch between the unit the user sees—a continuing agent session—and the much narrower unit the hijack implementation accepts—a local, live LLM runner with a numbered workspace and particular status. Fixing that mismatch will improve everyday control. However, merely relaxing eligibility checks would expose unsupported settlement paths and could weaken work preservation. The better approach is to extend the existing durable hijack protocol into a host-owned intervention that stops session progression, preserves custody, and delegates interruption to the owner of each turn kind.

The most consequential findings are broader than the screenshot: there are reproducible gaps in request deduplication, intent persistence, pin rollback, and linked-repository snapshot discovery. These should be repaired before widening the action's availability.

The evidence baseline is SASE commit `082f2bc7054de7d71a86646105c863b4dd85849d` and linked `sase-core` commit `2159438daaad1b2925acde6a9a6dabfd3e79bca5`, which also matches `sase-core-revision.txt`. The screenshot identifies `v0.19.0+45.g9793a95a5`. Comparing that commit with the inspected checkout showed no differences in the hijack directory, TUI hijack action, or session-status projection file. I read the supplied image at `~/tmp/screenshots/20261115_164112.png`, inspected source and tests, ran isolated Python probes against the checkout and installed Rust binding, and consulted primary process-control documentation. I did not exercise hijack against live work or run the full test suite.

The screenshot shows session `tailnet-t.10`, a `RUNNING` row, a session header with 12 turns, and the warning “Selected agent is not eligible for hijacking.” Its turn strip includes `--5` and the newer `--mon-3`; the header also shows a shell/starting indicator. That establishes a session with monitor-related activity, but it does not preserve the complete selected Python object or prove which member owned the workspace at that instant.

The exact warning has a precise source: `_start_hijack_agent` returns before submitting the durable operation when `agent_can_offer_hijack` is false. That predicate requires `AgentType.RUNNING`, status `RUNNING`, `STARTING`, or `RETRYING`, a positive workspace number, and a PID. It excludes monitors, gates, named procs, clans, remote rows, and imported rows. The screenshot is therefore evidence of an ingress refusal, not evidence that SIGTERM or SIGKILL failed. [TUI ingress][s1]

There is a separate session-targeting problem. `_get_selected_agent` returns the selected navigation object. `_mirror_root_from_child` can copy a child's visible `RUNNING` status onto its session root without copying its execution type or PID. Hijack does not first resolve that root to a concrete active turn. An isolated probe constructed a workflow root and an eligible LLM child, invoked the real mirroring function, and obtained:

```text
parent_status=RUNNING, parent_type=workflow, parent_pid=None,
parent_workspace=4, parent_eligible=False, child_eligible=True
```

This reproduces the misleading presentation independently of the screenshot. It is the strongest code-level explanation of why a visibly running session can fail immediately. It does not prove that these were the screenshot object's exact field values. Selecting its monitor member would still encounter the explicit monitor exclusion. [Selection][s2], [session mirroring][s3]

The backend imposes the same narrow product boundary even if the TUI is bypassed. Rust eligibility rejects monitor, gate, home-mode, remote, clan, and bulk targets; finalizer phases `declaring`, `executing`, and `finalizing`; missing capability, workspace, or PID; and all statuses outside the three live-runner statuses. These are intentional, tested restrictions, not just forgotten keybindings. [Rust eligibility][r1], [eligibility tests][r2]

The core-binding probe returned:

| Synthetic target, otherwise eligible | Result |
| --- | --- |
| Running LLM turn | Eligible |
| Waiting or queued turn | `ineligible_status` |
| Starting turn without PID | `missing_pid` |
| Monitor turn | `monitor_turn` |
| Gate turn | `gate_turn` |
| Finalizer executing | `finalizing` |
| Home-mode turn | `home_mode` |

A later read-only `sase agent show tailnet-t.10--mon-3` returned `DONE (monitored)`. That is later state, not a reconstruction of the screenshot. The screenshot and inspected code support the diagnosis above; they do not establish that a particular monitored command hung or that any work was lost.

There is a good foundation to retain. Hijack already has Rust policy, a revisioned ledger, exclusive record creation, durable TUI proc submission, workspace pinning, intent markers, process-tree termination with identity checks, snapshots, and several recovery choices. Recovery reserves a successor and validates launch identity, admission identity, workspace inheritance, and acknowledgement. Its reconciliation logic deliberately refuses to infer successful launch from a name alone. Wait resolution parks unresolved hijacks and follows their resolved successor. These are valuable guarantees, and replacing the subsystem wholesale would discard considerable work. [Ledger][s4], [recovery preparation][s5], [recovery reconciliation][s6], [wait following][s7]

The following defects and gaps deserve attention before broader eligibility. “Probe” below means temporary filesystem records and mocked external effects; no real processes were signalled or real workspace claims changed.

| Finding | Evidence and confidence | Practical consequence |
| --- | --- | --- |
| Uniqueness is per hijack ID, not per target execution | `create_record` locks/exclusively creates a filename derived from `hijack_id`. The orchestrator generates a new random ID for each ordinary call. A probe created two active records with the same agent, artifacts directory, PID, and workspace but different IDs. | Two callers can race through independent records and overwrite the same intent marker. The TUI's proc concurrency key is helpful, but direct CLI calls do not enter that submission path. Add backend target-level deduplication. |
| Intent-marker persistence is unchecked | `write_user_kill_intent` returns `None` on `OSError`; the orchestrator ignores the return value. Injecting `None` still reached the mocked terminator. | The runner may fail to recognize the stop as a hijack. Claim protection elsewhere reduces some exposure but does not make this a sound transaction prerequisite. |
| Pre-stop failure can orphan a pin | After `pin_claim`, failure of `begin_stop` calls `abort_before_stop`, which deletes the intent and ledger record without undoing the newly acquired pin. The injected-failure probe confirmed pin acquisition, no unpin, no termination, and no remaining record. | Capacity can remain held with no hijack recovery record explaining it. Restore the prior pin under identity checks or retain a repairable operation. |
| Partial stop is treated as terminal failure with custody removed | On surviving processes the orchestrator advances to `stop_failed`, removes the intent, and unpins a pin it acquired. The ledger treats `stop_failed` as terminal. The probe confirmed that path. | A dead runner plus a surviving child is possible; the message asserting the agent is “still RUNNING” is stronger than the evidence. Preserve quarantine/custody until writers are proven gone. |
| Abandoned stop operations lack the recovery treatment already available to launches | The stale sweep explicitly retains `requested` and `stopping` records without reconciliation. Recovery reconciliation handles `resolving`, plus projection repair for resolved records. | Crashing the CLI or worker during stop can leave an indefinite hold or incomplete presentation. Retention avoids immediate loss, but it is not dependable recovery. |
| Snapshot discovery does not match current linked-repo metadata | The launcher produces `linked_repos` as a list of dictionaries with `workspace_dir`; stop and release discovery accept only string entries. A probe using the real `LinkedRepoResolution.to_jsonable()` output omitted the linked repo in both readers. The end-to-end fixture supplies string paths instead. | “Snapshot all work before release” is not proved for current metadata. Opened repositories are also recorded in a separate marker file that these readers do not consult. |
| A standalone run can pass stop eligibility without an available keep-work successor path | `session_base_for({'agent_name': 'standalone-demo'}, {})` returns `None`; preparation raises `no_session` when no parent can be derived. Stop eligibility has no corresponding session requirement. | A supported stop does not necessarily imply that Continue can work. Prepare a standalone-to-session promotion or another supported successor identity. |

The first four findings follow directly from the [stop orchestrator][s8], [intent writer][s9], [abort helper][s10], and [ledger terminal-state rules][s4]. The abandonment gap is explicit in the [stale sweep][s11]. Snapshot findings are supported by the [metadata producer][s12], [stop discovery][s13], [release discovery][s14], [opened-repo markers][s15], and [end-to-end fixture][s16]. The standalone limitation is visible in [session derivation][s17] and [preparation][s5]. The probes establish these branch behaviors, not the incidence of production races or observed data loss.

Two further areas need adversarial tests. First, the orchestrator checks for a competing non-hijack `done.json` before termination, but `ensure_hijacked_settlement` preserves an existing marker afterward. The orchestration path can still attempt `confirmed_stop`; a terminal outcome appearing in the intervening window needs one shared settlement decision, not independent file writes. Second, staged-handoff adoption, monitor continuation, gate decision execution, and hijack are protected by different local mechanisms. The staged dispatcher revalidates adoption receipts under its adoption lock, but the hijack path does not acquire that lock or establish a common continuation fence. These are code-derived race risks, not incidents reproduced here. [Stop settlement][s10], [staged adoption][s18]

I would adjust the requirements explicitly as follows:

1. **Make every relevant state addressable, rather than promising immediate termination in every state.** The host should accept a durable intervention request or return a specific, actionable refusal. Some states require a safe boundary before control can transfer.
2. **Define hijack as stopping autonomous progression while preserving recoverable work.** It remains a new continuation after interruption, not a promise to resume the killed provider process. For a gate with no process, hijack means retaining or withdrawing its decision under the gate protocol.
3. **Make session scope and exact-turn scope explicit.** Selecting a session controls that session generation's current continuation. Selecting an exact historical turn does not silently redirect to a different execution. A clan is a set of independent agents and needs a separate bulk operation with per-target results.
4. **Require an honest outcome for uncertainty.** “Requested,” “waiting for safe boundary,” “stopping,” “held,” and “blocked by surviving writer” are different outcomes. A timeout or failed observation must never become a successful hold by convention.
5. **Preserve local work and record external effects; do not promise rollback.** Killing a local SSH client, publishing process, or gate option does not undo actions already performed elsewhere. Recovery must show whether those actions are completed, not started, or uncertain.
6. **Separate stop support from recovery support.** Before accepting a stop, expose whether continuation can retain the workspace, whether a fresh workspace is required, and whether model escalation is meaningful. Missing provider history should degrade to an evidence-based fresh continuation when possible.
7. **Treat remote and shared-workspace support as explicit capabilities.** A remote request executes on its owner host. A home-mode run can gain cancellation and evidence capture without pretending that its shared directory is an exclusively held numbered workspace.

These are proposed requirement changes, not claims that the current glossary already permits every behavior. In particular, queued, gate, and terminal recovery semantics extend the present running-LLM definition of hijack.

A useful support contract would look like this:

| Target or phase | Intended behavior | Recovery constraints |
| --- | --- | --- |
| Standalone or session LLM turn, running/retrying | Fence continuation, retain custody, stop its verified execution set, then hold | Start a new successor; promote a standalone run to a session if needed |
| Queued / dependency-waiting / quota-waiting | Suspend its admission request and automatic dispatch; no PID required | Resume the same pending work or edit it while held; retain original dependencies unless explicitly changed |
| Starting before/after process spawn | Persist cancellation before launch; bootstrap must observe it before work begins | Close the spawn/acknowledgement race; do not invent a workspace if none exists |
| Session container | Resolve current ownership under the session-generation lock/fence | Show the actual member controlled; ambiguous ownership gets a diagnostic |
| Monitor running | Fence normal follow-up, retain its custody, stop through proc/monitor ownership, verify all writers stopped | Continue with original task, command, output, ToolRun identity and partial effects; do not automatically rerun the command |
| Monitor settled, continuation pending | Block continuation admission/delivery; keep the real command result | Resume the retained continuation or start a recovery turn exactly once |
| Gate awaiting decision | Atomically hold/withdraw the pending decision and suppress its continuation | Preserve the review bundle; re-present or replace it according to an explicit recovery choice |
| Gate answer accepted, option command executing | Record request; preserve accepted choice and execution receipt; wait for a supported boundary or use a verified command-stop path | Never reinterpret cancellation as rejection or blindly replay the selected command |
| Provider completed, finalizer executing | Record request and prevent further autonomous continuation; let an in-flight irreversible step settle if possible | Recover from existing finalizer receipts; an emergency interruption must retain an “effect uncertain” condition |
| Handoff staged but not adopted | Fence adoption under the existing handoff lock and retain staged payload/custody | Reuse or supersede the stage intentionally; do not launch both it and a recovery successor |
| Handoff already adopted | Session-scoped intervention resolves the new current owner | Exact-turn requests return a superseded/finished result and identify the successor |
| Crashed, lost, failed or already held | Reconcile authoritative state; repair custody if still owned; expose recovery directly | No signal required; never seize a workspace now occupied by another generation |
| Successfully completed historical run | Offer Continue/Fork/Restart, preserving the real outcome | Do not relabel completed work “hijacked” |
| Remote owner | Route a generation-pinned request through owner-host control | Offline means pending/unreachable, not locally successful |
| Home-mode/shared directory | Stop verified execution and capture available evidence | No shared-directory reset or exclusive-workspace claim without an actual ownership mechanism |

Monitor support cannot be implemented by just calling `stop_monitor` after deleting the eligibility rejection. Current monitor stop intentionally settles a user-stopped turn and suppresses its normal follow-up; shared turn settlement then releases its claim. A hijack adapter needs a disposition that retains custody and parks continuation instead. It must support both proc-backed monitors and the legacy supervisor path. [Monitor stop][s19], [shared settlement][s20]

Likewise, `cancel_gate_turn` deliberately distinguishes unanswered gates from accepted decisions whose execution has not yet published a response. It can return an executing gate unchanged. A hijack must participate in that decision race and report its actual state, not assume that invoking cancellation removed the execution. [Gate cancellation][s21]

The architectural change should stay small enough to review: extend the existing hijack ledger and introduce one common control decision used by all frontends and continuation paths. Do not build a second workflow engine. The new logical control record should identify the owning host, stable session/run generation, exact turn identity and kind, operation/request ID, workspace generation and claim owner, current phase, stop-worker identity, continuation fence revision, and effect acknowledgements. Reuse existing run and launch identities where possible; names and PIDs remain labels/observations rather than ownership proofs.

A monotonic fence is a stored control revision checked when SASE admits new work, transfers custody, adopts a staged handoff, or launches a follow-up. Once an intervention has fenced a session generation, those paths must either stay parked or present the recovery authorization that supersedes that fence. Revalidation must happen at the launch/claim boundary, not only when a queue item was first read. The fence does not prevent arbitrary shell writes; process termination and custody verification remain necessary.

For concurrency, reserve the operation under a target-generation lock or equivalent atomic index. Repeated requests for that same target return the existing active operation. Serializing only by a newly generated operation ID cannot provide that property. Publish lock ordering relative to the project claim lock, handoff adoption lock, and gate execution lock. Keep broad locks short: reserve or compare state while locked, perform slow termination outside it, then verify and record effects. Executor identity or a lease is needed so recovery does not run concurrently with a living worker; an elapsed timeout alone is not proof that a worker is dead.

Use a small, shared capability result rather than copying more boolean allowlists into the UI. It should contain resolved scope and target, supported action, current phase, reason code, recovery modes, and expected revision. The UI can cache it with the roster and refresh asynchronously. Authoritative execution rechecks it. This both improves messages and avoids blocking Textual rendering on filesystem scans or process inspection. A session could say “Hijack monitor tailnet-t.10--mon-3; command will stop, workspace will remain held,” or “Intervention queued; commit is settling.” Missing support should name the owner/type and available action.

The stop transaction needs a clear order:

1. Resolve and reserve the target generation; coalesce duplicate requests.
2. Persist the intervention and fence future progression; establish and verify custody for any owned workspace.
3. Persist and verify the turn-specific stop intent. If a prerequisite fails before signalling, restore only this operation's changes or leave an explicit repairable record.
4. Quiesce through the appropriate owner: admission queue, LLM runner, monitor/proc service, gate executor, or finalizer boundary.
5. Verify that old writers and continuation dispatch are stopped. If uncertain, retain custody in a blocked state and identify the evidence needed.
6. Publish held state and durable recovery evidence. Expensive snapshots can continue after a proven hold, but release/reuse must wait for verified, current coverage.
7. On recovery, reserve one successor, transfer custody with acknowledgement, and settle the predecessor/fence only after identity and inheritance match.

This is a resumable sequence of recorded effects, not a claim that one filesystem rename makes every external action atomic. A reconciler should be able to resume after any step, including initial request, intent publication, pin acquisition, stop, snapshot, successor reservation, and final projection. Preserve completed outcomes when completion wins. Never overwrite an accepted gate decision or a proven successor merely because the UI still shows an older state.

Snapshot enumeration should share one canonical repository inventory with finalization: primary repository, opened linked and external repositories, relevant sidecars, baseline entries, and inherited custody. The finalizer already observes opened markers and baseline repositories. Share that inventory, not necessarily every finalizer effect or its full scanning implementation. Capture content and repository state sufficiently to restore staged, unstaged, untracked, binary, and newly opened work. Missing inventory, inaccessible repositories, or unverifiable fingerprints must block release unless the user explicitly invokes a destructive escape hatch. [Finalizer repository observation][s22]

For finalizing turns, I would keep a bounded cooperative phase and a separate emergency path. The normal action records intent immediately and holds the next continuation while the current commit/publish operation reaches its recorded boundary. If it cannot settle, show the reason and allow an explicitly selected forced stop of verified local execution. That path preserves work, receipts, and uncertainty; it cannot guarantee rollback of a push or external deployment. Simply removing the `finalizing` check would bypass the reason that restriction exists.

The process-control layer is already more capable than a bare `kill(pid)`: it records identities, discovers groups/descendants and registered supervisors, shields unrelated processes, rediscoveries late children, escalates, and verifies survivors. Retain this. The stop ledger should also receive the origin process-identity token it already has a field for; the current orchestrator does not populate that argument. Missing or malformed identity is currently handled permissively by the general identity helper, so new hijack capabilities should explicitly distinguish verified, legacy, gone, and uncertain execution. [Verified terminator][s23], [identity policy][s24], [stop orchestration][s8]

On Linux, pidfds can close the check-then-signal PID-reuse race for individual processes. A pidfd refers to a specific process and signalling it fails after that process is gone. This is a useful implementation hardening option, not a replacement for run identity or continuation fencing. [Linux pidfd manual](https://man7.org/linux/man-pages/man2/pidfd_send_signal.2.html)

For stronger descendant containment, evaluate launching each owned execution scope in a dedicated cgroup or systemd user scope. The kernel documents `cgroup.kill` as covering descendants while handling concurrent forks and migrations. This helps with processes that escape ordinary parent/group discovery, provided the execution was placed in its own scope before it could spawn children. Scope the command/provider workload separately from the supervisor responsible for durable settlement. Keep unrelated services outside it. This is a Linux optimization, not a prerequisite for the initial cross-platform design. [Kernel cgroup v2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html)

Systemd's documented stop model is a useful precedent: bounded graceful termination followed by forcible termination of the control group, rather than stopping only the main PID. SASE still needs its own application-level acknowledgements and custody checks. A delivered signal is not proof that all work is safely stopped. [systemd.kill](https://www.freedesktop.org/software/systemd/man/latest/systemd.kill.html)

Temporal likewise distinguishes a cancellation request that allows application cleanup from termination that application code cannot handle. The relevant lesson is to separate the request from its completion and to specify the cleanup contract. I am not recommending adopting Temporal as a dependency for this feature. [Temporal workflow control](https://docs.temporal.io/cli/command-reference/workflow#terminate)

The credible alternatives are:

| Approach | Assessment |
| --- | --- |
| Remove UI/core exclusions and reuse the LLM stop path | Small apparent patch, but incorrect for PID-less waits, gates, monitor custody, and finalizers. Reject. |
| Only resolve session containers to an LLM member | Good immediate usability fix where ownership is unambiguous. It cannot satisfy the monitor/gate and transition requirements alone. |
| Separate independently implemented hijack flows for each turn kind | Can widen support quickly but multiplies races and inconsistent semantics. Use adapters under one protocol instead. |
| Freeze/SIGSTOP the process and later SIGCONT | Retains locks, resources, and fragile provider/network state, and does not handle PID-less turns. It conflicts with the existing fresh-successor model. Reject as the normal contract. |
| Replace the entire lifecycle subsystem with a new orchestrator | Excessive scope given the existing ledger, custody, admission, and reconciliation machinery. Reconsider only if concrete integration limits emerge. |
| Extend the current ledger, common targeting/fencing, and typed executors | Best balance of coverage, safety, compatibility, and reviewable rollout. |

An implementation sequence should start with the proven defects, then add coverage in vertical slices. First, correct intent persistence, target-level idempotency, pre-signal rollback, partial-stop custody, and structured repository discovery. Add stop-phase reconciliation. Next, introduce shared target resolution and capability reporting, including standalone recovery. Then add queued/starting states and monitors end to end, including their follow-up races. Follow with unanswered gates, accepted gate execution, staged handoff boundaries, and finalizers. Add owner-host routing and shared-directory support once the local protocol is stable. Each slice should include recovery and crash repair before its capability is advertised.

Core policy, wire types, transition legality, action availability, and reconciliation decisions belong in `sase_core`. Python should observe processes/files and execute effects through existing owners; Textual should render the resulting capability/state. Update PyO3 bindings and schema fixtures alongside the Rust changes, then ratchet SASE's core revision pin before Python callers depend on them. Version new fields/capabilities deliberately: old runners must not be declared safe merely because their current status string looks supported.

The acceptance tests should measure guarantees rather than the number of permitted statuses:

- The screenshot-shaped session fixture has a workflow root, an active monitor, a staged transition, and historical members. The action resolves current ownership and gives a precise result. An ordinary active LLM child is also reachable from its session container.
- TUI and CLI issue concurrent requests with different request IDs for the same run. Exactly one active stop operation owns custody; all callers observe its progress. Repeating after a response is lost does not create another stop or successor.
- Fail every persistent write and kill the worker between every transaction step. Restart/reconciliation must converge to a justified hold, completed outcome, restored prior state, or explicit blocked condition.
- Let the runner die while a child survives, test permission-denied signals and PID reuse, and let children escape into new sessions. No surviving writer permits workspace reuse, and no unrelated process is signalled.
- Race hijack with admission, retry, finalizer completion, staged adoption, monitor completion, gate response acceptance, and recovery dispatch. At most one successor may become the owner for the same session progression point.
- Exercise real launcher metadata and opened-repo markers, not only handmade string lists. Verify restore of dirty primary, linked, external and sidecar work before release; test snapshot failure and post-snapshot changes.
- Verify held and expired states keep waiters parked; resolution follows the proven successor. Do not treat dismissal, expiry, or a stopped gate as success for dependents.
- Cover standalone runs, missing metadata, unavailable history, pre-capability runners, restart of the host service, Linux and macOS behavior, and remote/offline ownership. Read-only previews must remain nonmutating.

Retain existing recovery, CAS, release-transaction, and fakey tests as regression coverage. Extend them with realistic producers and concurrency boundaries. This research's probes are narrower than that acceptance suite; they demonstrate current defects without certifying the proposed architecture.

Operationally, show the operation ID, target generation, resolved turn kind, custody owner, current step, time in step, last error, and next recovery action. Track time to acknowledge, time to verified hold, frequency of blocked stops, duplicate suppression, reconciliation repairs, and snapshot coverage failures. A useful initial latency target is immediate acknowledgement after durable reservation and a bounded stop attempt with visible progress; choose service-level thresholds from measurements rather than promising a universal stop deadline. Long external critical sections and uninterruptible local I/O need explicit uncertainty.

For source navigation, the links below point to the exact inspected commits; repository contents were read from authorized local checkouts. The externally linked manuals support only the specific process-control comparisons above. The design and priorities are this report's conclusions.

[s1]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/ace/tui/actions/agents/_hijack_action.py
[s2]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/ace/tui/actions/agents/_selection.py#L283
[s3]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/ace/tui/models/_agent_status_apply.py#L49
[s4]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/agent/hijack/ledger.py
[s5]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/agent/hijack/_recover_prepare.py#L112
[s6]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/agent/hijack/recover_reconcile.py
[s7]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/core/wait_dependency_resolution/_hijack_follow.py
[s8]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/agent/hijack/_stop_orchestrator.py
[s9]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/agent/_user_kill_intent.py#L48
[s10]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/agent/hijack/_stop_claim.py
[s11]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/ace/scheduler/stale_running_sweep.py#L372
[s12]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/_linked_repo_env.py#L61
[s13]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/agent/hijack/_stop_evidence.py#L70
[s14]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/agent/hijack/_release_snapshot.py#L181
[s15]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/_linked_repo_markers.py
[s16]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/tests/fakey/test_agent_hijack_e2e.py#L217
[s17]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/agent/hijack/recover_subject.py#L151
[s18]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/axe/run_agent_exec_staged_dispatch.py#L475
[s19]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/monitor/store.py#L49
[s20]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/turns/settlement.py#L49
[s21]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/gate_turn/cancel.py
[s22]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/finalizers/_prepare_observe.py
[s23]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/agent/_user_kill_tree.py
[s24]: https://github.com/sase-org/sase/blob/082f2bc7054de7d71a86646105c863b4dd85849d/src/sase/core/process_identity.py
[r1]: https://github.com/sase-org/sase-core/blob/2159438daaad1b2925acde6a9a6dabfd3e79bca5/crates/sase_core/src/agent_hijack/eligibility.rs
[r2]: https://github.com/sase-org/sase-core/blob/2159438daaad1b2925acde6a9a6dabfd3e79bca5/crates/sase_core/src/agent_hijack/tests.rs

**Recommended solution:** extend the existing Rust-owned hijack/recovery state machine with generation-aware session targeting, a durable continuation fence, and turn-specific executors. First fix the demonstrated custody, persistence, deduplication, reconciliation, and snapshot-inventory gaps. Then add queued/starting turns and monitors end to end, followed by gates and finalizer/handoff boundaries. Preserve the existing successor identity and workspace-inheritance checks. The goal should be a dependable, recoverable intervention from every meaningful state, with honest limits on when safe control transfer can finish—not a larger list of rows that can be killed.
