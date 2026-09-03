# Research: Agents-tab `,X` for kill-last-launch-and-edit

Date: 2026-09-03

## Question

What is the safest and simplest way to add an Agents-tab `,X` command that behaves
like `,x`, but targets the most recent agent launch even when the durable proc that
performs the launch has not finished yet?

The important product scenario is an undo gesture: a user presses Enter, immediately
notices a prompt mistake, presses `,X`, edits the restored prompt, and submits it again.

## Executive finding

The command cannot be implemented robustly by finding the newest visible `Agent`, and
it should not be implemented by merely killing the newest `launch` proc. The former is
too late for the required pending-launch window. The latter has a real orphan race:
the outer `sase run` command is supervised in one process group, but each agent runner
is deliberately started in a new session. Once the child has spawned, killing the
outer proc does not kill that child, and the outer proc may die before publishing its
final `AgentLaunchResult` payload back to ACE.

The best design is to model each accepted launch as an explicit launch attempt, make
launch cancellation cooperative and idempotent at the backend boundary, and let `,X`
operate on the newest accepted attempt. ACE can restore the saved prompt immediately
while a cleanup barrier prevents resubmission until the cancellation/cleanup attempt
has settled.

## Desired semantics

The target should be defined as the **most recently accepted launch submission from
this ACE session**, not:

- the currently focused Agents row;
- the most recently sorted Agents row;
- the most recently completed launch proc; or
- the most recently submitted proc of any kind.

“Accepted” matters because `_submit_durable_proc()` can reject a submission on a
concurrency collision. A rejected Enter must not replace the previous valid target.
“Submission” matters because the identity exists before either the durable proc ID or
an `Agent` row exists.

For a normal one-prompt launch, one submission and one agent are the same thing. A
multi-prompt submission is inherently different: it is one `sase run` proc that
sequentially creates several detached children, and there is no stable singular “last
agent” before that sequence completes. The least surprising undo behavior is therefore
transactional: `,X` cancels/cleans every child created by the latest submission and
restores that submission's full prompt/pane stack. The UI label should say “kill last
launch & edit” so this edge case is honest. Bulk-Patch launch already creates one
submission per Patch; the final accepted slot is the newest launch attempt.

This command should be session-local initially. Recovering “the last launch” across an
ACE restart is a separate product decision, and the ordinary row-based `,x` remains
available once an agent is visible.

## Current implementation

### `,x` is row/mark based

The existing command is dispatched in
`src/sase/ace/tui/actions/agent_workflow/_leader_mode.py`:

- marked Agents take precedence and enter the bulk kill-and-edit path;
- otherwise `_kill_and_edit_agent()` uses the focused Agent row;
- prompt content is resolved off the Textual event loop;
- the Agent identity is re-resolved after that asynchronous read; and
- `_finish_kill_and_edit_agent()` optimistically kills/dismisses, mounts the prompt
  immediately, and opens a relaunch cleanup barrier.

The barrier in `agent_workflow/_relaunch_barrier.py` is a particularly useful piece to
reuse. It separates “let the user start editing now” from “allow the replacement launch
only after cleanup persistence has settled.” The new command needs the same UX
property, but its initial target is a launch attempt rather than an Agent row.

### The launch path already creates an early placeholder

The relevant path is:

```text
Enter
  -> _submit_resolved_launch(prompt)
  -> _submit_launch_proc(..., submitted_prompt=prompt)
  -> submit_agent_launch()
  -> _submit_durable_proc()
  -> ProcObserver.register_pending()       # pending-<uuid>, returned immediately
  -> background supervisor submission
  -> ProcObserver.register_submitted()     # real durable proc ID
  -> sase run
  -> detached Agent child/children
  -> final typed launch result
  -> _on_launch_proc_complete()
  -> _handle_launch_results_delta()
```

This is good infrastructure for a responsive TUI. The pending `ObservedProc` proves
that ACE can record a launch target synchronously without doing disk work on the
keystroke path. However, `_submit_launch_proc()` currently reduces the returned
`ObservedProc` to a Boolean, and `_on_durable_submit_worker_completed()` does not expose
a launch-specific callback when the placeholder is replaced by the durable proc ID.

`_launch_submitted_prompts` is also close to the required state, but it is only
failure-recovery metadata. It is keyed by proc ID, deleted on completion, and does not
hold the launch context or cancellation phase. It should be replaced or complemented
by a typed attempt record rather than stretched into the feature's state machine.

### Why killing the launch proc is insufficient

Proc cancellation currently calls `kill_proc()`/`stop_proc_shell()`. The supervisor
records stop intent, signals its child process group with SIGTERM, and eventually
escalates to SIGKILL. The supervised `sase run` command itself is created with
`start_new_session=True`, so cancellation correctly owns that outer process group.

The actual agent is outside it:

- `src/sase/agent/launch_spawn.py` explicitly describes the runner as a detached
  subprocess.
- `spawn_prepared_agent_process()` is Rust-backed.
- `crates/sase_core_py/src/lib.rs` calls `configure_detached_process()` before spawn.
- On Unix, that function calls `setsid()`; on Windows it uses
  `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`.

The outer `sase run` process emits `AgentLaunchResult` values only after
`launch_agents_from_cwd()` has returned. Its existing partial-launch rollback handles
ordinary Python exceptions, but process termination by SIGTERM does not travel through
that exception handler. The dangerous timeline is therefore:

```text
sase run spawns detached child
  -> child claims workspace
  -> user presses ,X
  -> ACE kills outer launch proc
  -> outer proc dies before final result payload
  -> detached child survives; ACE has no completion result identifying it
```

There is an even narrower interruption window around spawn/claim/result construction.
A design that discovers the child only after killing the outer process cannot prove it
has found every child. Reserved timestamp/workflow metadata is useful for reconciliation
but does not close that ownership gap by itself.

One attractive shortcut is to avoid killing the outer proc: mark the attempt
“kill when ready,” restore the prompt immediately, let `sase run` finish normally, and
then kill the exact `AgentLaunchResult` values from its completion callback. This is a
reasonable low-risk prototype and avoids the detached-child orphan race for ordinary
launches. It is not a complete implementation, however. A slow or stuck launch holds
the relaunch barrier indefinitely; ACE exit loses the session-local callback; and typed
admission may hand work to a background coordinator and return without direct Agent
results for every unit. The durable cancellation protocol below generalizes this good
“do not kill what you cannot yet identify” property without making completion of the
outer command the only recovery path.

### Keymap history matters

Uppercase `,X` was previously `kill_marked_and_edit`. Commit `fae3c9e11` retired that
action when marked behavior was folded into contextual `,x`. The loader still filters
the old `kill_marked_and_edit` action ID in `_RETIRED_LEADER_KEYS`, and tests explicitly
assert that standalone `,X` is absent.

The new feature should use a new action ID such as `kill_last_launch_and_edit`. It must
not revive `kill_marked_and_edit`; retaining that retired-ID filter preserves the old
configuration migration while allowing uppercase X to be assigned to the new action.

## Options considered

| Approach | Handles pre-start | Exact target | Survives detached-child race | Complexity | Assessment |
|---|---:|---:|---:|---:|---|
| Select newest visible Agent row | No | Sometimes | No | Low | Fails the core requirement and can select an external or differently ordered agent. |
| Scan agent artifacts/RUNNING fields by timestamp | Only after metadata exists | Usually | Not provably | Medium | Useful as reconciliation, not as ownership or primary targeting. It also puts disk work near a hot keypath unless carefully offloaded. |
| Find and kill newest `launch` proc | Yes, after a real proc ID exists | Usually | No | Low | Unsafe because the spawned agent is detached; also races the local pending placeholder. |
| Arm “kill when ready,” then use the final launch result | Yes | Yes for ordinary launches | Yes while ACE remains alive and the proc completes | Medium | Good prototype/fallback, but can wait forever, loses intent on ACE exit, and does not fully cover background typed admission. |
| ACE-only attempt state plus deferred proc kill | Yes | Yes within session | No | Medium | Solves target selection but not child ownership. Suitable scaffolding, insufficient final behavior. |
| Durable launch-attempt protocol with cooperative cancel and cleanup | Yes | Yes | Yes | Higher | The only approach that covers every phase without guessing. |

## Proposed design

### 1. Add a typed launch-attempt record in ACE

Create a small immutable-identity/mutable-phase record, conceptually:

```python
LastLaunchAttempt(
    generation: int,
    attempt_id: str,
    submitted_prompt: str,
    prompt_context: PromptContextSnapshot,
    placeholder_proc_id: str,
    durable_proc_id: str | None,
    phase: Literal[
        "submitting", "running", "completed", "cancel_requested",
        "cleaning", "settled", "failed"
    ],
    results: tuple[AgentLaunchResult, ...],
)
```

The exact storage type can vary, but the invariants should not:

- Install it only after `_submit_durable_proc()` accepts the submission.
- Store the exact resolved prompt and a copy of the launch `PromptContext` before the
  prompt bar releases that context.
- Give every attempt a monotonic generation/UUID independent of proc IDs.
- Keep both placeholder and durable proc IDs; never ask `kill_proc()` to kill a
  `pending-*` placeholder.
- Let completion callbacks update only the matching generation. Completion of an older
  concurrent launch must never overwrite the newer `,X` target.
- Once `,X` consumes an attempt, repeated `,X` is idempotent against that same attempt;
  it must not fall through and unexpectedly kill the preceding launch.

The cleanest API adjustment is for `_submit_launch_proc()` to return the accepted
`ObservedProc | None` rather than `bool`, and for generic durable submission to accept
an `on_submitted(placeholder_id, handle)` callback. If cancellation was requested while
the submit worker was still obtaining the durable handle, that callback starts the
backend cancel operation as soon as the real ID is known.

### 2. Introduce backend-owned launch cancellation

This behavior crosses frontend boundaries and belongs in `sase-core` plus its Python
binding, with thin CLI/ACE adapters. The backend contract should be keyed by an
`attempt_id` carried in the `run.launch` payload and should persist:

- cancellation intent;
- each spawned child's PID and exact launch identity (`artifacts_dir`, project file,
  workspace, workflow, timestamp, and agent name when known); and
- terminal cancellation/cleanup status.

The critical rule is **publish ownership before the launcher can lose the child**. A
plain “kill, then scan” implementation does not satisfy this. Two reasonable protocol
shapes are possible:

1. A cooperative cancellation record that `sase run` checks before each spawn and
   immediately after each spawn is durably receipted. The launcher finishes by rolling
   back every receipt when cancellation is present.
2. A dedicated idempotent `cancel launch attempt` operation that records intent, stops
   the outer proc, waits for it to become terminal, and repeatedly reconciles/cleans
   the durable receipts.

These can share one journal and operation. Avoid relying solely on a Python SIGTERM
handler: asynchronous termination can land between detached spawn and Python result
construction. The spawn/receipt boundary must be atomic with respect to cancellation,
or the launcher must defer hard termination through that critical section. A bounded
hard-kill fallback is still appropriate after cooperative cancellation times out, but
cleanup then reads the durable receipts and is retryable.

The operation should be idempotent: “no child spawned,” “child already exited,” and
“cleanup already completed” are all successful settled outcomes. Releasing workspace
claims and persisting agent dismissal should use the same backend/domain behavior as
normal agent cleanup, not duplicate it in Textual code.

### 3. Make `,X` an immediate UI undo backed by a cleanup barrier

When the key is pressed on the Agents tab:

1. Snapshot the current attempt generation. If none is actionable, show “No recent
   launch to kill and edit.”
2. Mark that attempt `cancel_requested` synchronously so a second press cannot retarget
   an older attempt.
3. Mount the saved prompt or prompt panes immediately using the saved context. No disk
   read should occur on this keystroke path.
4. Open a relaunch cleanup barrier.
5. In a worker/durable operation, cancel the attempt. If submission still has only a
   placeholder ID, defer the operation until the real handle arrives.
6. On settlement, merge any launch receipts/results into the Agents projection, apply
   normal kill/dismiss persistence to spawned agents as needed, settle the barrier, and
   refresh only the affected Agents state.

For the immediate “I hit Enter too soon” window, confirmation adds little safety and
undermines the undo gesture; the attempt should cancel without a modal. If `,X` targets
an already completed, stable running Agent long after launch, reusing the existing
`ConfirmKillModal` policy is reasonable. A simple cutoff is phase-based rather than
time-based: an in-flight launch is an unconfirmed undo, while a completed attempt
delegates to the existing `,x` kill-and-edit path for its exact result.

The saved context is better than `_mount_edit_relaunch_prompt_bar()`'s generic home
context for an in-flight attempt: it preserves the launch target and pane behavior the
user just submitted. Factor the low-level prompt-bar mounting so both paths can share
rendering without forcing the new action through row-derived metadata.

If a child claimed a named identity before cancellation, the replacement launch must
not race or conflict with that identity. The cleanup barrier should carry the cleanup
result into final launch preparation, either by applying the existing forced-name-reuse
rewrite to the final edited text or by passing a narrowly scoped backend relaunch
authorization. Applying this at submit time is safer than mutating a prompt the user is
actively editing.

### 4. Wire all keymap surfaces

Add `kill_last_launch_and_edit: "X"` in both:

- `LeaderModeKeymaps` in `src/sase/ace/tui/keymaps/mode_keymaps.py`; and
- `ace.keymaps.leader_mode.keys` in `src/sase/default_config.yml`.

Then update:

- the leader dispatcher in `_leader_mode.py`;
- `_LEADER_LABELS` and `_LEADER_TABS` in `commands/_mode_commands.py`;
- `CommandContext` and its extractor with a cheap Boolean such as
  `has_actionable_last_launch`;
- Agents availability in `commands/_availability_agents.py`;
- the conditional leader footer in `widgets/_keybinding_modes.py`; and
- the Agents help modal.

The footer should show `,X kill last launch & edit` only while an attempt is actionable,
matching the repository's conditional-footer convention. Help can always document it.
The command palette should use the same availability predicate. Keep
`kill_marked_and_edit` in `_RETIRED_LEADER_KEYS`; the new action ID makes migration
unambiguous.

## Failure handling and edge cases

- **Submission rejected:** do not replace the prior target and do not record VCS replay
  usage beyond current accepted-submission behavior.
- **Pressed before durable proc ID exists:** remember cancellation; act when the handle
  callback arrives. Never pass the placeholder ID to `kill_proc()`.
- **Pressed just as completion arrives:** generation + idempotent backend cancellation
  makes either ordering converge on the same cleanup result.
- **Older launch finishes later:** update its own record/results, but do not make it the
  latest target again.
- **Launch fails with no child:** restore the prompt, settle successfully, and avoid a
  second failure-stash copy.
- **One or more children spawned:** clean all receipts from that submission and hold
  relaunch until their claims/dismissal persistence settles.
- **Typed `%if`/`%proc` launch:** the current admission code intentionally preserves
  already launched units on cancellation. `,X` needs stronger transaction-undo
  semantics, so the new attempt cleanup must explicitly include those launched unit
  identities rather than inheriting admission cancellation behavior unchanged.
- **ACE exits during cleanup:** the backend attempt and cancellation record must remain
  retryable/reconcilable; UI callback state alone cannot own correctness.
- **Repeated keypress:** report “Last launch cancellation already in progress” or focus
  the already restored prompt; never advance to the previous attempt.

## Test strategy

The most valuable tests are phase-boundary tests, not just keymap assertions.

1. **Keymap/catalog:** default uppercase X, unique subkeys, stale
   `kill_marked_and_edit` override still filtered, Agents-only catalog entry, conditional
   footer, help text, and leader dispatch/repeat behavior.
2. **Accepted-target ordering:** rejected submissions do not become latest; two
   accepted launches followed by reverse-order completion still target the second.
3. **Pending-placeholder race:** block durable submission, press `,X`, release the
   submit worker, and assert cancellation uses the real proc ID exactly once.
4. **Pre-spawn cancellation:** assert zero agent children and immediate prompt mount.
5. **Spawn/cancel race:** pause immediately after detached spawn, request cancellation,
   and assert the journaled PID is terminated and its workspace claim is released.
6. **Post-completion path:** resolve the exact Agent by `artifacts_dir`/launch result,
   reuse normal kill-and-edit behavior, and preserve forced name reuse.
7. **Multi-prompt transaction:** all children from the newest submission are cleaned
   and all original prompt panes are restored in order.
8. **Idempotency/recovery:** kill twice, child already exited, ACE closes during
   cleanup, and cancellation resumes from persisted state.
9. **Responsiveness:** the `,X` handler performs no synchronous filesystem/proc-store
   access and mounts the editor before cleanup settles.

Existing suites provide useful homes and fixtures:
`test_agent_launch_non_blocking.py`, `test_durable_submit.py`,
`test_kill_and_edit_launch_barrier.py`, `test_partial_launch_cleanup.py`,
`test_leader_keymap_dispatch.py`, `test_keymaps_defaults.py`, and
`test_command_availability_agents.py`. The detached-child race deserves at least one
real-process integration test in addition to mocked unit tests.

## Recommended implementation sequence

1. Define the launch-attempt wire/state and idempotent cancellation/receipt behavior in
   `sase-core`; expose it through `sase_core_rs` and thin Python adapters.
2. Add `attempt_id` to `run.launch`, journal child receipts at the spawn boundary, and
   make cancellation settle only after child/workspace cleanup is reconciled.
3. Evolve ACE's launch submission seam to retain the returned placeholder and receive
   the later durable handle; add the generation-safe `LastLaunchAttempt` state.
4. Implement the `,X` action with immediate prompt restoration and a relaunch cleanup
   barrier, delegating completed single-agent attempts to the existing `,x` machinery
   where possible.
5. Add the config, dispatcher, command-palette, footer, help, migration, and phase-race
   tests, then run the repository's required verification lanes.

## Recommended solution

Implement `,X` as **kill last launch & edit**, backed by a durable launch-attempt
protocol rather than by Agents-row ordering or a raw proc kill. Record the newest
accepted ACE launch synchronously with its exact prompt/context and pending proc ID;
bridge that placeholder to the durable proc handle; restore the prompt immediately on
`,X`; and hold resubmission behind the existing cleanup barrier. In the backend, record
cancellation intent and atomically receipt every detached child so an idempotent cancel
operation can stop the outer launch, kill/dismiss every child it produced, and release
all workspace claims without an orphan window. Treat a multi-prompt submission as one
undo transaction, use the new action ID `kill_last_launch_and_edit` on uppercase X, and
leave the retired `kill_marked_and_edit` ID filtered for configuration compatibility.
