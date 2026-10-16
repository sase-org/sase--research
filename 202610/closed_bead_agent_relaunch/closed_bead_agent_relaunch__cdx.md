# Closed-bead agent launches: preserve completion, audit the new attempt

Independent research by **cdx**, 2026-10-16.

## Finding

Allow `%id(..., bead=<id>)` to launch against an existing closed bead, and record a host-written audit note before provider execution. My recommendation is to **leave the bead closed**, retaining its resolution, close time, reason, and assignee. Treat this as a new execution associated with completed work. Reopen the bead explicitly when the work itself needs to resume.

This is a good change for the reported finalizer/error recovery case. A completed bead and a failed execution can coexist legitimately. The dangerous version of the proposal is silently treating every retry as proof that the completion was wrong, or merely deleting the current rejection without deciding what happens to the bead's status.

The main tradeoff of preserving closure is equally important: this launch does not reclaim the bead as unfinished work or make its dependents wait again. That needs an explicit, documented contract.

## Scope and evidence

I independently inspected the current SASE checkout and its audited `sase-core` checkout, read the applicable bead/artifact/macro memories through `sase memory read`, and ran small isolated probes through the Python facade and installed Rust extension. No product code or real bead was changed. No other report from this swarm was consulted.

Source revisions inspected:

- SASE: `e297cefb8ec146cce6cc83e2f56abe43c44572c6`.
- sase-core: `1c6d5299a65fb3612e8075abed866cad024c9a2b`.

The runtime probes used the installed extension, not a newly built extension from the inspected core checkout. They corroborate the source findings, but are not a substitute for implementation tests against the updated binding.

## What currently happens

### The restart preserves the bead intentionally

The default configuration maps comma followed by `x` to `kill_and_edit`. The action recovers and rewrites the prompt, handles the old execution's cleanup, and presents the prompt for relaunch. Its cleanup barrier prevents old persistence work from resurrecting the replaced agent. Closed-bead support should preserve that barrier. [Keymap][keymap], [kill-and-edit flow][relaunch-flow].

The prompt helpers preserve orthogonal `%id` metadata, including `bead=`. The ordinary retry helper explicitly drops an obsolete `session=` attachment while retaining the bead. The kill-and-edit session rewrite also accepts a phase bead fallback. Thus removing `bead=` during retry would lose a deliberate association rather than fix the underlying lifecycle mismatch. [Retry rewriting][retry], [identity rewriting][identity-edit].

### The hard failure is at execution admission

The parser validates that `bead=` is a nonempty, whitespace-free identifier. The generic runner later calls `_promote_bead_claim`, after dependency/runner admission and workspace preparation. That calls `claim_bead_for_agent_launch`, which materializes the bead store, holds the store write lock around mutation and sidecar commit, and delegates through `BeadProject` to Rust. [Directive validation][directive], [promotion][promotion], [runner checkpoint][runner].

In Rust, `run_claim_launch` immediately returns `kind="closed"` with `cannot claim closed bead for agent launch: <id>`. Nonclosed beads are normally moved to `in_progress` and assigned to the launching agent; an already matching `in_progress` assignment is a no-op. The Python runner separately rejects an `in_progress` bead owned by another agent, except for its established replacement rules. [Core claim algorithm][core-claims], [ownership predicates][force-reuse].

This distinction matters: Rust's present claim function does not itself provide all the runner's ownership protections. A patch must preserve the runner checks, and any new closed-bead policy must live in the shared core rather than only in a Textual action.

Waiting claims are separate. They reserve an `open` bead; closed beads decline without mutation. Bootstrap simply continues when it cannot acquire that waiting claim. Therefore there is no need to reopen or annotate a bead merely because a queued/waiting prompt mentions it. The useful audit point is the existing post-preparation launch checkpoint. [Wait claim][core-wait], [bootstrap][bootstrap].

### The audit primitive already exists

`BeadNoteWire` has an ID, timestamp, author, and text. `NoteAppended` records the text in the canonical event stream and projects it into the bead's visible note list. The existing append operation imposes no requirement that the bead be open. [Note wire][note-wire], [note mutation][notes].

A note is enough for the requested recognizable, timestamped annotation. A new status, label, tag system, or event kind is not justified for the first implementation. The underlying event history preserves edits/removals too; visible notes themselves can be edited or retracted, so this should not be described as a tamper-proof audit system.

### Finalization already tolerates closed assignments

The shared bead-action policy accepts `keep` without changing status. A `close` decision against a closed bead becomes `CloseIdempotent`, and the commit hook does not close it again. This means preserving a close at launch is compatible with existing completion behavior; there is already a distinction between committing execution output and changing bead completion. [Action policy][actions], [commit hooks][hooks].

The agent-to-bead `implements` relation is projected from published metadata, independently of the bead's assignee/status. Keeping the original assignee therefore need not lose the later execution's provenance. [Association projection][association].

## The decision that must be explicit

There are two different operations hiding inside “restart”:

1. **Retry execution or finish finalization.** The original work may already be landed and verified. A new execution can inspect state, recover output, or repair a finalizer failure without invalidating the completion.
2. **Resume unfinished or newly broken work.** The close is no longer an accurate statement about the work. The bead should become active again, with the associated scheduling consequences.

A launch against a closed bead does not tell the host which situation applies. In particular, an error after a successful close is not evidence that the task is incomplete.

As a limited external analogy, GitHub Actions allows rerunning completed executions and preserves access to separate run attempts. It also keeps the original triggering SHA/ref, which SASE prompt replay should not be assumed to do. The useful lesson is explicit attempt identity, not copying GitHub's retry semantics wholesale. [GitHub's rerun documentation](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs?tool=webui).

| Approach | Benefit | Cost / risk | Assessment |
| --- | --- | --- | --- |
| Preserve the close; append an admission note | Matches finalizer recovery; keeps historical completion and dependency meaning | A real repair must explicitly reopen; closed association grants no exclusive work claim | Recommended default |
| Automatically reopen and claim | Makes actual resumed work visible as `in_progress`; restores ordinary claim ownership | Reopens ancestors, changes scheduling, can undo canceled/superseded completion, and may leave reopened parents without a land worker | Use only for an explicit resume-work operation |
| Drop `bead=` on retry | Small UI workaround | Loses commit/finalizer association and provenance; other launch paths still fail | Reject |
| Make a new bead for every retry | Separates distinct work cleanly | Routine error recovery creates tracking noise and divides one task's history | Appropriate only for genuinely new scope |
| Add `allow_closed=true`, a new confirmation, or a feature flag | Makes an exception explicit | Restores the interaction friction the request aims to remove | Unnecessary for the recommended default |

### Why automatic reopening is a larger change than it appears

The existing `open_issue` archives the prior close into `close_history`, clears current close metadata, and reopens every closed ancestor. This is meaningful domain behavior, not a harmless assignment reset. [Open implementation][reopen], [close archival][archive].

A closed phase can belong to a closed epic whose land agent already finished. Automatically reopening both does not automatically arrange a new land execution. Conversely, a dependent that already passed a bead wait is not parked again if that bead later reopens; the documented wait contract is explicitly one-way. Automatic reopening cannot undo downstream work that already started. [Wait contract][wait-doc].

Simply removing the Rust guard is also incorrect. The remaining claim algorithm writes `status=in_progress` but does not archive/clear the old close. Validation disallows a resolution on a nonclosed issue, and mutation/replay must agree on close history. A proper reopen implementation would need the same archival, ancestor, and reducer semantics as explicit `open`. [Claim algorithm][core-claims], [resolution validation][resolution].

Those costs can be justified when deliberately resuming work. They are not justified by every failed provider/finalizer run.

## Proposed behavior and requirement adjustments

These are deliberate clarifications/additions to the request, not assumptions about its current wording:

- **Preserve closure by default.** Launching is permitted; it does not itself reopen the bead or change its assignee, resolution, close time, close reason, or ancestors. Updating the note log and `updated_at` is expected.
- **Apply to every closed resolution.** A `done`, `canceled`, or `superseded` bead can be associated with an execution. Its recorded resolution must remain intact. Do not silently revive canceled work.
- **Make the note a host responsibility.** It must not depend on the LLM remembering to write it after startup.
- **Record an admitted attempt, not successful execution.** Provider startup can fail after the note is stored. The note must describe the pre-execution checkpoint accurately and link to the attempt outcome through its identity.
- **One note per actual attempt, not per internal retry.** Repeated checkpoint calls for the same launch must not append duplicates. A later relaunch, including forced name reuse, gets a new note.
- **Use the shared launch path.** Typed `%id`, comma-x, ordinary retry, session replacements, and automatic relaunches should receive the same closed-bead behavior when they reach that path. Keep bulk `sase bead work` scheduling and its skip-closed-phase policy separate.
- **A failed audit write remains a real launch error.** Remove the closed-status rejection; do not swallow missing-bead, integrity, I/O, ownership, or required local-commit errors.
- **Do not claim exclusive ownership of a closed bead.** This operation records association rather than taking an `in_progress` claim. Multiple launches can therefore associate with the same completed bead. Actual implementation work should explicitly reopen and use the existing claim rules.

The last point is a substantive tradeoff. If exclusive closed-bead recovery execution is a hard requirement, it needs a separate attempt lease keyed by project and bead, with cleanup and liveness semantics. Overwriting `assignee` while retaining `closed` would neither enforce exclusivity through the current predicates nor preserve the original completion ownership. I would not build a second claim subsystem just for this request.

The new agent should receive a short host context line stating that its bead was already closed, showing the current close details, and directing it to inspect existing work before repeating implementation. If unfinished work remains, explicitly reopen using the existing bead operation. This is useful recovery context, but prompt wording is not a substitute for the host's audit write or an ownership mechanism.

## Audit record design

Use the existing note timestamp and author fields, with a versioned, recognizable body prefix. For example, the rendered note could be:

```text
2026-10-16T14:03:27Z · <resolved-agent-name>
CLOSED_BEAD_LAUNCH v1: attempt=<stable-launch-id>; stage=pre-execution;
state=preserved; previous_closed_at=<close-time>; resolution=done.
```

The timestamp above is illustrative. Capture the actual checkpoint time in UTC. Use the resolved launching agent as the event actor/note author, not the original bead creator. Include the stable attempt ID even when the agent name is also a clickable reference: names can be forcibly reused.

Required content is small: a fixed marker/version, attempt ID, resolved agent identity, and an explicit statement that closure was preserved. Prior close time and resolution make the note self-contained. Original/source-agent identity or launch origin may be included when already available, but should not require a new user input. Avoid copying prompts, transcripts, or ephemeral absolute checkout paths into the note.

Keep ordinary notes as the storage primitive. For a first implementation, an exact versioned marker plus attempt token can support duplicate detection under the core mutation lock. Centralize its formatting/matching and do not infer execution state from arbitrary prose. An additive structured operation ID would be cleaner if an existing suitable mechanism is available, but a whole new event family is unnecessary.

The launch ID must exist before the checkpoint and survive internal retry/replay. `RunnerRunState` already exposes launch artifact identity, including an artifact timestamp and launch root. Reuse an existing stable per-attempt identifier if its uniqueness is guaranteed; otherwise allocate a host ID once and persist it. Do not deduplicate by timestamp alone, by the agent name, or by `(agent, closed_at)`: each can collapse legitimate later launches. [Run identity][run-state].

## Implementation surface

The domain change belongs in `sase_core::bead::mutation::claims`, exposed through `sase_core_py` and the thin Python facade/project adapter. Extend the launch admission request with stable attempt identity; the closed branch should, under the same mutation lock:

```text
load the authoritative bead
if closed:
    if this attempt's audit entry already exists:
        return unchanged closed bead
    stage NoteAppended using the launching agent and checkpoint time
    update the visible note projection and updated_at
    commit through MutationView
    return changed=true, with the bead still closed
otherwise:
    retain the existing claim behavior
```

This is a sketch of responsibilities, not a requirement to introduce these exact API names. Reuse the note-event/projection machinery so cached mutation and event replay produce identical state. Avoid invoking the public append-note mutation from inside another mutation lock; factor shared staging if necessary. The closed outcome must report `changed=true` when a note is created, or the runner will skip its persistence path. [Mutation outcome][outcome], [note staging][notes].

In Python, pass the attempt identity through `run_agent_runner_bead.py`, `BeadProject`, and `bead_mutation_facade.py`. Continue holding the existing store lock around mutation plus the standalone sidecar commit. Do not bolt a `project.show()` / `append_note()` / ignore-closed sequence onto just the TUI: that splits policy, races status changes, and makes audit creation unreliable across entry points.

The core binding currently takes `(beads_dir, bead_id, agent_name, now=None)`. Prefer an additive, compatible extension rather than breaking old positional callers, and update binding round-trip coverage. A compatibility policy is needed for a legacy caller that supplies no attempt ID: it must not silently skip the audit or deduplicate all later launches under one name. The SASE call path should always supply the ID. Move `sase-core-revision.txt` past the landed core implementation before SASE calls an updated binding. [Binding][binding].

`_promote_bead_claim` currently sets `bead_claim_promoted=true`. Audit its consumers before changing this flag's meaning. For the closed path, an additive disposition such as `closed_association` can make the distinction explicit in metadata/context while preserving existing cleanup expectations. Do not have claim reconciliation reopen a closed bead to make a running row appear consistent. Existing doctor code already restricts its missing-waiting-claim check to open beads. [Promotion][promotion], [doctor predicate][doctor].

### Persistence detail that should not be missed

The runner requires a successful local SDD commit for changed standalone stores. It then calls `publish_bead_claim`. Despite wording about synchronous publication in some comments, that helper **prints a warning and returns an error outcome when push fails**; the runner currently ignores that outcome. In-tree stores leave the event as a workspace change for ordinary finalization. [Checkpoint][runner], [publication helper][publication].

For this change, I recommend retaining those existing storage policies: the audit append must succeed, and the required standalone local checkpoint must commit before execution. Reuse the publication attempt and its diagnostic. Do not promise that remote publication is guaranteed before execution.

**Requirement clarification:** a visible canonical audit note persisted under existing claim policies is the proposed guarantee. If “audit trail” is intended to mean “already published remotely before any provider starts,” that is a stricter policy and should be specified and tested separately, including network failure/retry behavior. It should not be introduced accidentally through this small lifecycle change.

## Checks that would establish the implementation

| Case | Required result |
| --- | --- |
| Closed task, plan, or phase | Launch admitted; exactly one host note; all close/assignee fields retained |
| Closed `done`, `canceled`, `superseded` | Recorded resolution and reason unchanged; note identifies the attempt |
| Closed phase under closed ancestors | Ancestors stay byte-for-byte unchanged |
| Same attempt enters checkpoint twice / replay fallback | One note and one logical mutation |
| Distinct attempts, including same forced agent name | Separate timestamped notes; earlier notes retained |
| Waiting/queued launch canceled before admission | No closed-launch note and no reopening |
| Bead closes while launch waits | Decision uses the authoritative status at launch; closed branch records it |
| Bead explicitly reopened before admission | Normal active-bead claiming rules apply |
| Missing/ambiguous ID, bad actor/attempt, mutation or local-commit failure | Specific error preserved; provider does not run on failed mandatory checkpoint |
| Another agent owns an `in_progress` bead | Existing refusal/replacement behavior retained |
| Closed association finalizes with `keep` / `close` | Close remains intact; idempotent close does not overwrite the original reason/resolution |
| Event replay and cached backing | Same note, actor, timestamps, outcome, and issue projection |
| Sidecar publication fails | Existing policy/diagnostic remains explicit; no claim of remote durability |
| Comma-x, ordinary retry, session/forced reuse, CLI launch | Bead association survives rewriting; common admission behavior exercised |

Also verify that `%wait(bead=...)` still follows closure, not retry liveness, and that `sase bead work <epic>` still skips completed phases. Keep the current kill-and-edit cleanup barrier intact. These checks concern behavior, rather than tests that merely mirror helper implementations.

For implementation verification, use focused Rust mutation/binding tests and Python runner/relaunch/finalizer integration tests, then the repository-required `just check` gate through the guarded tool workflow. No implementation test suite was run for this research-only deliverable.

## Isolated observations

I initialized a temporary bead store inside the workspace, created a parent and phase, claimed/closed the phase, and closed the parent. All probe files were removed afterward. Explicit test timestamps were supplied so the results were deterministic.

The Python facade plus installed Rust extension produced:

```text
claim_for_agent_launch(closed_phase, retry.worker)
  ValueError: closed: cannot claim closed bead for agent launch: probe-1.1

append_note(closed_phase, marker, author=retry.worker)
  status, closed_at, close_reason, resolution, assignee: all preserved
  note timestamp: 2026-10-16T10:03:00Z
  note author: retry.worker

append the identical marker again at the identical time
  note count: 2

open_issue(closed_phase)
  phase status: open
  reopened ancestors: [probe-1]
  current resolution: null
  close_history count: 1
```

This demonstrates both that the existing note primitive is suitable and that it does **not** provide exactly-once attempt recording automatically. The parent reopening is observed behavior, not a speculative concern.

## Recommended solution

**Accept the requested relaxation in the shared Rust launch-admission operation, preserve the bead's closed state and completion metadata, and append one host-authored `CLOSED_BEAD_LAUNCH` note per stable launch attempt at the existing pre-execution checkpoint.** Retain missing-bead/ownership/persistence errors, reuse existing sidecar persistence, supply explicit closed-bead context to the agent, and verify finalizer idempotence. Do not add a new required directive input or confirmation.

Use explicit `sase bead open` when the work actually needs to resume, accepting its ancestor and scheduling effects deliberately. This gives comma-x recovery the desired low friction while keeping “a new execution happened” separate from “the previous completion is being undone.”

[keymap]: https://github.com/sase-org/sase/blob/e297cefb8ec146cce6cc83e2f56abe43c44572c6/src/sase/default_config.yml#L1165-L1183
[relaunch-flow]: https://github.com/sase-org/sase/blob/e297cefb8ec146cce6cc83e2f56abe43c44572c6/src/sase/ace/tui/actions/agent_workflow/_entry_relaunch.py#L350-L414
[retry]: https://github.com/sase-org/sase/blob/e297cefb8ec146cce6cc83e2f56abe43c44572c6/src/sase/agent/retry_prompt.py#L10-L31
[identity-edit]: https://github.com/sase-org/sase/blob/e297cefb8ec146cce6cc83e2f56abe43c44572c6/src/sase/macro/_directive_edit_identity.py#L153-L179
[directive]: https://github.com/sase-org/sase/blob/e297cefb8ec146cce6cc83e2f56abe43c44572c6/src/sase/macro/_directive_values.py#L104-L113
[promotion]: https://github.com/sase-org/sase/blob/e297cefb8ec146cce6cc83e2f56abe43c44572c6/src/sase/axe/run_agent_runner_launch.py#L208-L245
[runner]: https://github.com/sase-org/sase/blob/e297cefb8ec146cce6cc83e2f56abe43c44572c6/src/sase/axe/run_agent_runner_bead.py#L43-L143
[core-claims]: https://github.com/sase-org/sase-core/blob/1c6d5299a65fb3612e8075abed866cad024c9a2b/crates/sase_core/src/bead/mutation/claims.rs#L101-L159
[force-reuse]: https://github.com/sase-org/sase/blob/e297cefb8ec146cce6cc83e2f56abe43c44572c6/src/sase/bead/force_reuse.py#L20-L44
[core-wait]: https://github.com/sase-org/sase-core/blob/1c6d5299a65fb3612e8075abed866cad024c9a2b/crates/sase_core/src/bead/mutation/claims.rs#L167-L204
[bootstrap]: https://github.com/sase-org/sase/blob/e297cefb8ec146cce6cc83e2f56abe43c44572c6/src/sase/axe/run_agent_runner_bootstrap.py#L282-L319
[note-wire]: https://github.com/sase-org/sase-core/blob/1c6d5299a65fb3612e8075abed866cad024c9a2b/crates/sase_core/src/bead/wire.rs#L326-L346
[notes]: https://github.com/sase-org/sase-core/blob/1c6d5299a65fb3612e8075abed866cad024c9a2b/crates/sase_core/src/bead/mutation/notes_update.rs#L409-L458
[actions]: https://github.com/sase-org/sase-core/blob/1c6d5299a65fb3612e8075abed866cad024c9a2b/crates/sase_core/src/bead_action/policy.rs#L62-L152
[hooks]: https://github.com/sase-org/sase/blob/e297cefb8ec146cce6cc83e2f56abe43c44572c6/src/sase/workflows/commit/bead_hooks.py#L125-L151
[association]: https://github.com/sase-org/sase/blob/e297cefb8ec146cce6cc83e2f56abe43c44572c6/src/sase/artifact_links/projection/_agent_bead.py#L13-L44
[reopen]: https://github.com/sase-org/sase-core/blob/1c6d5299a65fb3612e8075abed866cad024c9a2b/crates/sase_core/src/bead/mutation/close_remove.rs#L41-L121
[archive]: https://github.com/sase-org/sase-core/blob/1c6d5299a65fb3612e8075abed866cad024c9a2b/crates/sase_core/src/bead/events/reduction.rs#L693-L722
[wait-doc]: https://github.com/sase-org/sase/blob/e297cefb8ec146cce6cc83e2f56abe43c44572c6/docs/macros.md#L2720-L2730
[resolution]: https://github.com/sase-org/sase-core/blob/1c6d5299a65fb3612e8075abed866cad024c9a2b/crates/sase_core/src/bead/wire.rs#L1224-L1234
[run-state]: https://github.com/sase-org/sase/blob/e297cefb8ec146cce6cc83e2f56abe43c44572c6/src/sase/axe/run_agent_runner_state.py#L17-L51
[outcome]: https://github.com/sase-org/sase-core/blob/1c6d5299a65fb3612e8075abed866cad024c9a2b/crates/sase_core/src/bead/mutation/mutation_wire.rs#L158-L183
[binding]: https://github.com/sase-org/sase-core/blob/1c6d5299a65fb3612e8075abed866cad024c9a2b/crates/sase_core_py/src/beads/mod.rs#L891-L910
[doctor]: https://github.com/sase-org/sase/blob/e297cefb8ec146cce6cc83e2f56abe43c44572c6/src/sase/doctor/checks_beads.py#L508-L526
[publication]: https://github.com/sase-org/sase/blob/e297cefb8ec146cce6cc83e2f56abe43c44572c6/src/sase/bead/_sync_publication.py#L109-L139
