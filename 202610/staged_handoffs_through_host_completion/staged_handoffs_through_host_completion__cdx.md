# Final declarations for gates and monitors: preserve work before handing off

Independent research by **cdx**, 2026-10-28.

**Recommendation.** Adopt the proposed lifecycle change: agents should prepare gates or monitors, submit one final declaration, and let the host perform the transition after the provider finishes. Reuse the existing declaration, commit executor, and completion controller. Put gate/monitor activation in a separate, mandatory terminal stage of that controller, rather than inside the commit executor. Explicitly preserve verification-before-commit and allow a clean turn to declare without requesting a commit.

This solves the concrete composition problem while retaining the valuable part of the current design: no model process waits for a human or long command. The mistake is the bypass of completion, not the eventual termination of the provider.

**Scope and evidence.** I independently inspected sase at commit **a2fbbc3b9db7100077fc0ba609bd49edd0b66416**, the opened sase-core checkout at **ed8328f91e46db4c824f4a41fc71bfa6507c9429**, current SASE skills and audited memory, the two requested agent histories, and the plan produced by sase-1ou.land. I did not consult any other researcher in this swarm or their reports. Findings below distinguish source behavior from transcript assertions and proposed design. I did not execute a gate, monitor, finalizer experiment, or production reproduction; those operations would change the running lifecycle. Code and test inspection support the mechanism; they do not establish the frequency or full extent of historical data loss.

**What the two examples establish**

The completed bob-cli-dw.land transcript reports that proposing the next backlog epic would bypass committing a sase test correction and nine plan-file edits. The agent chose normal finalization and left the successor unproposed. It also reports finding five older, closed backlog epics whose plans still said wip, and filing bob-cli-e0 for the stranding defect. That is strong evidence of a real workflow conflict, with reported historical corroboration. I have not independently reconstructed each older workspace to prove exactly which bytes were lost. The explicit finalizer bypass in current source independently supports the agent's diagnosis. [H1, S1]

The initial name lookup for sase-1ou.land resolved to its monitor member, so I also retrieved the original and plan-member transcripts by exact basename. The original history has no substantive final response; the plan member records submission of files_spread_ci_landing.md. Its audited plan says the reconciled tests/reproducible_flake_baseline.txt and two sase-core changes “commit after its turn and exist before this plan launches.” The later monitor transcript records the child epic being launched. This directly exposes the desired contract: preserve work in multiple repositories before starting its dependent successor. The reviewed records do not independently prove whether those particular edits eventually landed; they show an assumption the current plan handoff cannot guarantee. [H2, H3, S1, S2]

The right acceptance scenario is therefore stronger than “a plan command returns successfully”: a turn edits a primary and linked repository, prepares a plan, declares both commits and the continuation, and the approved successor sees the required committed revisions.

**How the current implementation works**

| Path | Current behavior | Consequence |
| --- | --- | --- |
| Ordinary completion | Provider returns; the host calls run_finalizers. | Accepted declarations drive bounded, verified completion. |
| Plan proposal | Validate and format; move the plan to the durable plan archive; write .sase_plan_pending; kill the runner group. | The proposal terminates the provider before ordinary completion. |
| Generic gate turn | Create member, transfer/release claim according to policy, create the decision bundle, potentially auto-resolve; pending gates then hand off by marker and kill. | The gate can already be actionable before the provider has finalized. |
| Monitor | Resolve lane, bind optional completion intent, create member, submit supervisor/proc and transfer claim; then write marker and kill. | Starting the monitor is already a substantive ownership transition. |
| Prepared verification | sase final prepare seals conditional completion; monitor start binds it; eligible success runs host finalizers without another model. | This intentionally keeps commit after verification. |

These are distinct paths, not one shared call site. Plan proposal directly kills the runner; generic gates and monitors use the shared turns/handoff helper. Both the finalizer controller and declaration recovery explicitly return early when a pending handoff exists. Changing only the shared kill helper would miss plans and would leave the skip paths intact. [S1–S4]

The existing completion system is already more general than a commit hook:

- The host seals selected finalizer instances and their configuration before the provider runs.
- The declaration is bound to run ID, agent ID, turn nonce, plan digest, and context digest.
- The controller executes a bounded fixed-point loop. A later finalizer can dirty a repository and reactivate commit.
- The commit provider executes repository decisions through sase stitch create and independently accounts for results.
- Missing or stale required declarations have a bounded recovery path. [S5–S7]

A clean commit-only turn currently does **not** need a submitted manifest. build_context_requirements gives commit a not_triggered requirement when no repository obligations exist; the skill returns after reading that context. Thus “every turn must declare” requires a change to the generic protocol/host policy, beyond removing handoff exemptions. It does not require empty Git commits. [S6]

Conversely, a dirty repository currently requires a commit decision. Its only legal repository action is commit; typed deferrals are separate and restricted to authorship/safety reasons. “I am handing off” is not one of those reasons. Merely making the message optional or adding a blanket skip action would weaken an existing protection against losing work. [S6]

**Critique of the proposal**

The proposal is a good direction for three reasons. It gives the model one explicit completion boundary. It allows independent accomplishments and a next step in the same turn. And it makes the host accountable for both preserving work and arranging continuation, instead of treating a signal and marker as successful completion.

The principal adjustment is architectural: reuse the **finalization framework**, not the **commit executor as the home for all terminal actions**.

| Approach | Benefit | Cost / weakness | Assessment |
| --- | --- | --- | --- |
| Add gates and monitors to builtin@commit | Small-looking API change; one familiar payload | Couples continuation to VCS selection and dirty-state triggering; conditional verification becomes awkward; commit retries risk repeating launch side effects | Avoid as the permanent architecture |
| Separate handoff finalizer placed after commit in the existing ordering | Reuses provider abstractions and keeps responsibilities separate | A simple after: [commit] edge is insufficient: another finalizer can still mutate the tree later in the same cycle | Viable only with terminal-stage semantics |
| Mandatory host terminal stage using a typed declaration intent | Independent of VCS, supports clean turns, runs after the fixed point, can own durable activation receipts | Requires an explicit lifecycle boundary and recovery state | Recommended |
| Keep kill-on-propose and silently finalize afterward | Limits agent-facing changes | Intent is already active, workspace may have moved, author has not declared commits, and recovery must guess | At most a legacy compatibility bridge |

The default configuration selects commit but does not require it. Therefore a handoff implemented solely inside builtin@commit can disappear when commit is deselected. The host lifecycle contract must survive a no-commit configuration. Existing selected finalizers should still retain their host-authenticated configuration; the model must not choose an arbitrary executor or repository path. [S5, S6]

A terminal stage can be presented as a built-in “handoff finalizer” in status and documentation. Internally, it should be a controller-owned epilogue that cannot run until ordinary finalizers have converged. This avoids creating a broadly programmable workflow engine or a general dependency language just to express the one terminal transition.

**Requirements I would change or clarify**

1. **Every orderly root-agent completion declares, including clean turns.** A valid empty-payload declaration is a real completion acknowledgment. Native helpers still return to their parent. A crash, forced stop, or provider failure cannot be required to produce an agent declaration; the host must record an explicit abnormal outcome and preserve recovery evidence.

2. **Every turn-ending handoff uses the same boundary.** Include questions and pipe in the finished contract, not just plan/gate/monitor. All five currently appear in the pending-handoff classifier. A phased rollout can support legacy turns, but retaining permanent exceptions would contradict “all turns.” [S1]

3. **Preparation is inert with respect to the next actor.** It can validate, format, snapshot, and reserve a stable intent ID. It must not publish an actionable gate, execute an auto-approved option, start a new monitored command, release/transfer the claim, or dispatch a successor.

4. **No commit is legal for specific reasons, not because a handoff exists.** Clean tree, conditional commit after verification, and explicit custody transfer of unfinished work are different states. They must remain distinguishable in declarations and receipts.

5. **Finalization must finish before normal successor activation.** “Commit finalizer ran once” is too weak. All required repository outcomes and other selected finalizers must be settled; then the terminal stage activates the continuation. Activation must preserve single-writer ownership.

6. **A handoff does not imply task completion.** A parent epic with remaining work stays open. A completed predecessor may close while proposing independent successor work. Preserve explicit bead keep/close choices; do not infer them from the existence of a plan or monitor.

7. **Finalizers arrange durable waiting; they do not wait themselves.** Their success condition is accepted ownership by the gate/monitor infrastructure, not a human response or completed long command.

These are justified extensions or restrictions of the request, rather than claims that the present protocol already supports them.

**Recommended declaration and command experience**

Keep the familiar preparation commands. In a root agent, plan propose, monitor start, and turn-producing gate creation should prepare an intent and return a clear descriptor: “Prepared; activates after final declaration.” Plan validation errors should remain repairable in the same turn. Preserve shell/host direct-start APIs; they have no provider declaration to wait for.

Expose the prepared intent in sase final context and include it in the host-generated manifest template. The agent should not have to copy a second large gate or monitor specification into the declaration.

Illustrative new envelope content, not an existing schema:

    {
      "completion": {
        "kind": "handoff",
        "intent_ref": "<host-issued reference>",
        "intent_digest": "<sealed digest>"
      },
      "payloads": [
        {
          "instance_id": "commit",
          "payload": {
            "repositories": [
              {
                "repo_id": "<host-issued repository ID>",
                "action": "commit",
                "message": "fix: preserve landing work",
                "bead_action": "keep"
              }
            ],
            "deferrals": []
          }
        }
      ]
    }

The usual schema version, run/agent identities, nonce, and plan/context digests still apply. A clean turn carries no commit payload when none is required. A normal completion uses completion.kind = complete. The host, not an untrusted manifest path, resolves the prepared intent.

Allow at most one terminal intent per root turn. Repeating the same preparation should return the same intent; incompatible second preparations should be rejected with a repairable error. Explicit replacement before submission may be supported, with the old intent recorded as superseded. After submission, no more workspace edits or intent replacement.

Preparation should freeze the plan bytes, decision definitions, request commands/argv, working directory binding, continuation prompt, model route, timeout, auto-approval policy, and workspace policy. Validate them when prepared and verify their relevant hashes again at activation. A prompt or plan repair that changes approved meaning must require a new intent rather than silently substituting content.

This has a small deliberate UX cost: an agent can continue after preparing, so it can also forget to declare. The host already has a declaration recovery path; extend it to include prepared continuation evidence and fail visibly when it cannot obtain a valid declaration. Do not silently activate an undeclared intent. The provider-completion watchdog already watches newly accepted declarations and can reap a stalled provider after a grace period; keep bounded teardown as a backstop. [S7, S8]

**Repository policy: the important split**

| Situation | Required repository treatment | Activation order |
| --- | --- | --- |
| Clean plan-only or gate-only turn | Host observes no work to commit | Declare → finish other finalizers → activate gate |
| Completed edits plus successor plan | Declare commits for all relevant repositories, including linked/sidecar repositories | Commit and verify all → activate gate → approval may launch successor |
| Monitor that waits for CI on this turn's new commit | Commit first; bind the resulting revision to the monitor's context | Commit/push as required by existing policy → monitor |
| Final verification monitor | Seal conditional commit decisions, command identity and tree evidence | Declare → transfer to verification → eligible success commits |
| Unfinished edits plus long diagnostic/build command | Explicit custody transfer to monitor and its continuation/recovery owner | Declare → preserve and transfer work → monitor → later declaration decides commit |
| Dirty gate whose decision is needed before committing | Explicit preserved custody, with rejection/timeout recovery ownership | Declare → preserve work → gate; no automatic commit contrary to the decision |

The first two rows deliver the named users' immediate benefit. The remaining rows prevent that fix from forcing premature commits.

For final verification, reuse the existing prepared completion mechanism rather than inventing a second representation. Its command binding, repository observations, result eligibility, no-model execution, and recovery routing already exist. Today preparation explicitly does not submit; the revised workflow must include acceptance of the verification handoff in the actual final declaration while keeping the commit contingent on verification. Failed checks, timeout, stale evidence, or new repository obligations must still withhold commits and route recovery. Preserve the pass/no-new acceptance distinction and its exact ToolRun evidence. [S9]

For ordinary unfinished work, introduce an explicit **transfer of repository custody**, separate from the existing safety deferrals. The host should require the exact repository set and fingerprints, an identified next owner, retained claims or a restorable checkpoint, and a defined outcome for failed/abandoned continuation. Carry attribution into the successor: inherited changes should not become “foreign work” merely because they were dirty when that successor began.

Do not confuse a hash or transcript with preserved file contents. The current monitor recovery helper is best-effort, runs for failed follow-up dispatch, and writes text Git diffs without requesting a binary patch. It is useful diagnostics, not a sufficient proof that arbitrary work is durably recoverable. Before permitting custody transfer to release a workspace, require either demonstrably retained worktrees/claims or a lossless snapshot that covers staged, unstaged, untracked, binary, executable, deletion, and linked-repository state. Existing retention/checkpoint facilities should be evaluated before adding another store. [S10]

A narrow first implementation can support commit-before-plan and the existing conditional verification path, but it must not claim migration is complete while ordinary dirty monitor handoffs still lack a defined preservation policy.

The plan gate's own commit option is also distinct from committing the author's unrelated code and sidecar changes. Its approval payload already separates commit_plan from run_coder. Preserve those review semantics; finalizing today's authorized work must not silently count as approving tomorrow's proposed implementation. [S11]

**Activation, failures, and recovery**

Recommended host progression:

    prepared → declaration accepted → provider finished
             → repository/other obligations settled
             → activation authorized → next owner acknowledged
             → creator handoff recorded

For verification/custody transfer, “obligations settled” means the host has accepted durable custody or conditional completion, not that a Git commit already exists.

The crucial boundary is between authorizing activation and starting the next actor. Store an intent ID, declaration digest, original owner, current state, required repository receipts, successor ID, and activation receipt durably. A retry must adopt the existing gate/monitor/successor rather than allocate a duplicate.

This resembles the dual-write problem described in AWS's transactional-outbox guidance: recording an outcome and notifying another system can fail independently, so durable intent plus idempotent delivery is necessary. Applying that principle here is a design inference, not evidence that Git commits and proc/gate creation share an atomic transaction. They do not. Use the existing journals, lane locks, replay fingerprints, supervisor acknowledgment and receipts where they fit, with explicit recovery across stores. Do not claim arbitrary commands execute exactly once. [E1, S3, S4]

| Failure boundary | Required behavior |
| --- | --- |
| Preparation rejected | No actionable gate, command, or claim transfer; agent can repair |
| Provider exits without declaration | Bounded declaration recovery or visible failure; no successor activation |
| One repository commits, another fails | Keep receipts and surviving work; hold dependent activation; resume remaining work |
| Commit succeeds, host crashes before activation | Reconciler resumes the recorded intent without recommitting or asking the model to reconstruct it |
| Launch succeeds, receipt write fails | Find/adopt the same launch ID; do not rerun a possibly destructive command |
| Later finalizer changes files | Revalidate/redeclare as required and reconverge before activation |
| Cancellation after commit | Report committed work and cancelled continuation; do not attempt a Git rollback |
| Monitor stops or loses its successor | Preserve transferred work and expose recovery ownership |
| Gate rejects or times out | Leave prior authorized commits intact; preserve any carried work under its declared recovery policy |

Avoid holding an OS process or executor slot for human-scale waits. Claims may need durable retention to protect uncommitted work; that is a distinct resource cost and should be visible. The old “gates never block” rationale remains valid even though the kill-on-create timing changes.

Auto-approval deserves an explicit compatibility decision. Current generic gates can auto-resolve while the creator remains alive; creation restores its claim in that branch. A staged terminal gate should run auto-resolution after finalization, avoiding an approved command racing commits. Audit internal callers that depend on an immediate auto-result. Non-turn internal/shell gate operations can retain a direct service API, but an agent-facing pending decision must not fall back to blocking. [S3]

Monitor joins are another special case. A -J join adopts a ToolRun that is already running; preparation cannot retroactively make that command inert. Reserve the existing run for host adoption before creator teardown, retain its exact run ID, and prohibit conflicting workspace mutation while it runs. Do not convert a join into a fresh execution. If adoption fails, preserve the established stop/recovery behavior instead of leaving an unmanaged process. [S12]

The host's finalizer-repair turns currently refuse handoffs because the old commands kill the outer runner. Keep that restriction for model-driven repair until an explicit suspend/resume design exists. A new trusted terminal executor should call lower-level host activation APIs using the accepted intent; it must not shell out to the existing self-killing commands or broadly disable the repair guard. [S13]

**Implementation surface and sequencing**

This is a cross-cutting lifecycle change, not a small optional field on a commit message. A useful implementation decomposition is:

- **Core contract:** add the typed completion intent, root-turn acknowledgment and repository custody/conditional disposition validation to sase-core. Keep accepted declaration identity, digests and exact obligation coverage. Rust wire types deny unknown fields, so coordinate schema compatibility, PyO3 bindings, Python mirrors and sase-core-revision.txt. [S14]
- **Preparation front doors:** separate pure validation/snapshot/reservation from activation for plan, gate and monitor. Retain plan tier validation, formatting validation, provenance and review content binding. Move pending-handoff semantics out of preparation.
- **Controller terminal stage:** require orderly root declarations independently of the selected commit provider; converge existing finalizers; execute one idempotent transition; persist activation evidence; then settle the creator's ownership.
- **Conditional/custody path:** integrate prepared verification and ordinary unfinished monitor work before turning off the legacy escape hatch. Preserve multi-repository attribution and no-model completion.
- **Runner and recovery integration:** replace unconditional handoff skips; distinguish prepared, accepted, activating, active and failed states; retain legacy marker handling for already-running old-protocol turns. Keep continuations, chat capture, notifications and workspace release tied to actual activation.
- **Instruction rollout:** update source skill templates, CLI guidance, generated instruction sources and tests together. Skills are generated from src/sase/macros/skills and should deploy only from a landed revision. Any eventual implementation plan must separately authorize memory changes through the memory-write rules. The existing decision records should be superseded as required, not silently rewritten; their no-blocking/host-ownership principles still apply.

Use an immutable per-run protocol version so the host does not change a running agent's meaning halfway through its turn. A bounded transition that can read both old and new records is safer than globally deleting marker readers. Stop producing old self-killing handoffs for new-protocol turns and later remove compatibility according to the project's retirement policy. This is not a recommendation for a permanent user-facing mode switch.

A commit-first plan path is the best initial vertical slice because it directly tests both named examples. Roll out the complete no-exemptions contract only after verification, dirty monitor joins, questions and pipe have defined behavior.

**Tests that would determine whether this is safe to ship**

No production mutation or test execution was needed for this research report. The implementation should prioritize behavior at failure boundaries:

1. A clean root submits successfully with no commit payload, including with commit deselected; an absent required acknowledgment is detected.
2. A primary-plus-linked-plus-sidecar edit followed by a plan commits every obligated repository before actionable publication or successor launch.
3. A later finalizer dirties a tree after the first commit pass; no gate/monitor activates until reconvergence.
4. Manual and auto plan approvals observe the same finalized predecessor state; rejecting the plan never undoes prior authorized work.
5. Prepared verification performs zero pre-check commits; green commits with no extra model; red, timeout, stale evidence and new obligations enter recovery.
6. Ordinary dirty-monitor transfer preserves binary and untracked content and attribution; stopping or losing follow-up cannot make the work disposable.
7. Repeated submission/preparation and concurrent reconciler retries produce one logical gate/monitor and one selected continuation.
8. Crash injection after each durable-state write and external side effect proves replay/adoption, especially commit-success/activation-missing and launch-success/receipt-missing.
9. A joined ToolRun finishes immediately during finalization; its evidence and run ID survive and its command is never rerun.
10. Parent bead state, plan associations, provider transcript capture and linked-repository revisions survive both successful and failed handoffs.
11. Helpers and finalizer repair turns cannot create independent terminal transitions; stale nonce/foreign intent/tampered plan bytes are rejected.
12. Old in-flight marker turns remain readable, while new protocol turns cannot silently use marker-based finalizer exemptions.

Existing useful suites include test_finalizer_declaration_channel_recovery.py, test_finalizer_owned_turn_handoffs.py, gate_turn/test_transaction_finalizer_owned_turn.py, monitor/test_monitor_host_completion.py, plan_chain_golden/test_marker_and_loop_golden.py, and test_plan_approval_launch_reliability_integration.py. Some assertions deliberately encode current exemptions and will need intentional changes. Continue using the project's normal guarded check workflow; research is not a reason to run check-full.

**Evidence index**

Source links below are pinned to the inspected revisions. They were read from the authorized local checkouts, not fetched from GitHub.

- **H1:** Completed bob-cli-dw.land history, obtained with sase chat show --agent bob-cli-dw.land and exact listing metadata: [gh_bobs_org__bob_cli-ace_run-bob_cli_dw_land-261028_153711.md](/home/bryan/.sase/chats/202610/gh_bobs_org__bob_cli-ace_run-bob_cli_dw_land-261028_153711.md).
- **H2:** Completed sase-1ou.land [original history](/home/bryan/.sase/chats/202610/gh_sase_org__sase-ace_run-sase_1ou_land-261027_092233.md), [plan history](/home/bryan/.sase/chats/202610/gh_sase_org__sase-ace_run-sase_1ou_land__plan-261027_092233.md), and [monitor history](/home/bryan/.sase/chats/202610/gh_sase_org__sase-ace_run-sase_1ou_land__mon-20261028170410.md), retrieved through sase chat show.
- **H3:** plan:202610/files_spread_ci_landing.md, read through sase artifact read with an audit reason. Its opening “Why this child epic exists” section contains the two-repository commit-before-launch assumption.
- **S1:** [Pending handoff kinds](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/agent/pending_handoff.py); [controller skip and pending-instance policy](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/finalizers/controller_context.py#L41); [recovery handoff skip](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/finalizers/declaration_recovery.py#L30).
- **S2:** [Plan proposal, archive, marker, kill](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/main/plan_propose_handler.py#L176); [shared turn handoff](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/turns/handoff.py#L32).
- **S3:** [Gate creation and claim/auto-resolution transaction](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/gate_turn/transaction.py#L94).
- **S4:** [Monitor start flow](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/monitor/start_flow.py#L109); [launch and proc submission](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/monitor/start_launch.py#L214); [launch barrier and acknowledgment constants](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/monitor/transaction.py).
- **S5:** [Sealed finalizer plan](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/finalizers/plan.py); [controller fixed-point loop](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/finalizers/controller_run.py#L196); [default finalizer selection](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/default_config.yml#L1994).
- **S6:** [Dirty-only commit requirement](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/finalizers/declaration_store.py#L210); [manifest and commit validation](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/finalizers/declaration_manifest_commit.py#L43).
- **S7:** [Declaration acceptance](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/finalizers/declaration.py#L181); [provider-to-finalizer boundary](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/llm_provider/_invoke.py#L439).
- **S8:** [Accepted-declaration/provider-end watchdog](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/llm_provider/_subprocess_plain.py#L137).
- **S9:** [Prepared completion contract in the final skill source](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/macros/skills/sase_final.md); [host no-model execution and drift checks](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/monitor/host_completion_execute.py#L58); [host completion tests](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/tests/monitor/test_monitor_host_completion.py).
- **S10:** [Best-effort worktree recovery diff](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/monitor/worktree_recovery.py); [monitor handoff transcript/continuation capture](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/axe/run_agent_exec_monitor.py#L25).
- **S11:** [Plan gate approval payload](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/plan_gate.py#L387); [plan branch continuation policies](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/plan_gate_turn/create.py).
- **S12:** [ToolRun joinability and escalation routing](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/tool/routing.py#L264); monitor launch source in S4.
- **S13:** [Finalizer-owned handoff prohibition and tests](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/tests/test_finalizer_owned_turn_handoffs.py); [guard implementation](https://github.com/sase-org/sase/blob/a2fbbc3b9db7100077fc0ba609bd49edd0b66416/src/sase/finalizers/owned_turn.py).
- **S14:** [Rust finalizer wire contract](https://github.com/sase-org/sase-core/blob/ed8328f91e46db4c824f4a41fc71bfa6507c9429/crates/sase_core/src/finalizer/wire.rs); [Rust declaration validation](https://github.com/sase-org/sase-core/blob/ed8328f91e46db4c824f4a41fc71bfa6507c9429/crates/sase_core/src/finalizer/submission.rs#L125).
- **E1:** [AWS transactional outbox guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html), consulted 2026-10-28. Used only for the durable-intent/idempotent-delivery analogy.
- **Audited SASE context:** decisions:gates-never-block, decisions:single-turn-agents, decisions:host-owned-completion, decisions:adapters-normalize-harnesses; glossary entries for gates, monitors, turns and stitches; sase_artifacts.md and generated_skills.md. Current memory-write and final skills were also reviewed for rollout/finalization constraints.

**Recommended solution**

Proceed with final-declaration-based handoffs. Make gate/plan/monitor commands prepare a sealed terminal intent, require an orderly root-turn declaration even when no commit is needed, run existing selected finalizers to completion, and activate exactly one continuation through a mandatory host terminal stage with replayable receipts. Reuse builtin@commit for commits and prepared completion for verification; add explicit, verified custody transfer for work that must remain uncommitted. Deliver the multi-repository commit-plus-plan case first, then complete the monitor/questions/pipe migration without permanent exemptions. This preserves the current single-turn and no-blocking guarantees while making “save this turn's work, then start the next step” a host-enforced contract.
