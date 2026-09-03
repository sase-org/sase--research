---
create_time: 2026-09-03
updated_time: 2026-09-03
status: research
---

# `,X` — Kill And Edit The Last Launched Agent (Consolidated)

**Research question:** add a `,X` leader keymap to the Agents tab that behaves like `,x`
(kill & edit) but targets *the most recently launched agent* — including one whose launch
proc has not finished yet — so a user can instantly undo a premature `<enter>`, edit the
prompt, and resubmit.

**Provenance:** consolidates two independent reports (`__a` from research.3.cdx, `__b`
from research.3.cld) plus a third verification pass by the lead researcher. Every
load-bearing citation below was re-verified against master `9e2d95bb0`; where the two
reports disagreed, the disagreement and its resolution are stated explicitly.

---

## Executive summary

Both researchers independently converged on the two hardest calls, and verification
confirms both:

1. **Targeting must be session-scoped, not disk-derived.** "Most recently launched"
   means *the last launch this ACE session accepted*, recorded synchronously at submit
   time. Disk-scan alternatives (newest row, `get_most_recent_agent_name`) are blind to
   the in-flight window — the exact case the feature exists for — and will happily
   retarget onto clan members, monitors, or agents *spawned by* the agent you launched.

2. **Never kill the launch proc.** Agent runners are spawned as detached processes in
   their own session (Rust-owned spawn, `setsid()` on Unix), so killing the outer
   `sase run` proc after spawn orphans the child while destroying the only channel
   (`AgentLaunchResult`) that identifies it. There is also no stop API for operation
   procs today (`stop_proc_shell` is guarded to proc-shell lifecycle rows,
   `procs/service.py:340`, `procs/settlement.py:151`), and SIGTERM bypasses the
   partial-launch rollback, which only catches in-process Python exceptions
   (`main/query_handler/_launch.py:144-159`).

The reports diverged on what to do during the in-flight window. Report A recommended a
durable backend cancellation protocol in `sase-core` (attempt records, cooperative
cancel, spawn receipts). Report B recommended a session-local **deferred kill**: restore
the prompt immediately, record kill intent, and kill the concrete `AgentLaunchResult`s
when the launch proc completes, via the ordinary kill path.

**Resolution: build the deferred kill (B), adopting A's state-discipline guardrails, and
scope the one real hole — typed `%if`/`%proc` admission launches — explicitly.** A's
protocol solves problems this undo gesture does not have (cross-restart durability,
kill-before-spawn), at the cost of new wire/API surface in `sase-core` per the
rust-core-backend-boundary rule. The deferred kill needs zero new backend behavior: it
waits for the launch to finish and reuses the existing, well-tested kill/dismiss and
relaunch-barrier machinery. Its acknowledged costs (the agent briefly starts; intent dies
with the ACE session) are acceptable for an interactive undo and are strictly better than
making the user wait.

---

## Verified ground truth

### The launch timeline

Walking `<enter>` → visible row (all verified):

| T | Event | Code | What exists |
| --- | --- | --- | --- |
| T0 | Submit | `_submit_resolved_launch` (`_launch_start.py:216`) | resolved prompt text, launch ctx |
| T0+ε | Placeholder registered **synchronously** | `_submit_durable_proc` → `register_pending` (`_proc_action_submission.py:121-137`, `proc_observer.py:114`) | `ObservedProc(proc_id="pending-<uuid>")` returned to the caller; completion callback keyed by this placeholder ID |
| T0+ε | Prompt stashed | `_submit_launch_proc` (`_launch_procs.py:86-91`) | `_launch_submitted_prompts[placeholder_id] = prompt` |
| T1 | Durable submit on a worker thread | `register_submitted` (`proc_observer.py:143`) | real proc row; `ProcWatch` maps durable ID → placeholder ID; request sidecar holds the full prompt |
| T2–T3 | Supervisor spawns `sase run`; child expands prompt, claims name, creates artifact dir, spawns **detached** agent | `procs/spawn.py:135` (`start_new_session=True`), `agent/launch_spawn.py` | detached agent PID; ACE knows nothing yet |
| T4 | Proc terminal | `_on_launch_proc_complete` (`_launch_procs.py:94`) | `AgentLaunchResult[]` with `pid`, `artifacts_dir`, `agent_name`, `timestamp` (`agent/launch_types.py:7-20`) |
| T5 | Bounded delta refresh | `_handle_launch_results_delta` (`_launch_delta.py`) | the `Agent` row appears |

Three consequences:

- **ACE cannot identify the agent before T4.** The child reserves its own timestamp and
  name; nothing session-side names the agent earlier.
- **The prompt is fully known at T0** (in memory; durably from T1 in the proc's
  operation-request sidecar). The *edit* half of kill-and-edit never needs to wait.
- **The completion callback already bridges placeholder → durable ID.** Callbacks are
  registered under the placeholder ID and delivered through `ProcWatch.placeholder_id`,
  so a kill intent keyed by placeholder ID needs no new plumbing to be found at T4.
  (This dissolves report A's "bridge the placeholder to the durable handle" work item
  for the deferred-kill design; the bridge already exists.)

The T0→T4 window is real, not theoretical: it covers a fresh interpreter start, xprompt
expansion, workspace preparation, and provider spawn. `launch_timing.py:16` sets its
*slow-stage* threshold at 30s, and `SASE_AGENT_LAUNCH_TIMING=1` exists to profile it.
The "I hit enter too fast" reflex lands squarely inside this window, so the in-flight
branch is a requirement of the feature, not an optional phase.

### The `,x` machinery to reuse

- Dispatch: marks take precedence, else `_kill_and_edit_agent()` on the focused row
  (`_leader_mode.py:204-216`, `_entry_relaunch.py:215`); clan containers are refused.
- Prompt resolution runs off the event loop; identity is re-resolved after the hop;
  dismissable/pid-less rows dismiss without confirmation, live-PID rows get
  `ConfirmKillModal` (`_entry_relaunch.py:271`, `agents/_kill_flow.py`).
- The prompt bar mounts immediately; the *replacement launch* is parked behind a
  `_RelaunchCleanupBarrier` until kill/dismiss persistence settles
  (`_relaunch_barrier.py`; `_submit_resolved_launch` parks itself at
  `_launch_start.py:231-235`). The barrier exists because `apply_force_reuse_launch`
  wipes old name state and a late cleanup write could resurrect the name the replacement
  claims — **the single most important invariant to preserve**. It times out after 30s
  and then releases held launches with a warning (`_relaunch_barrier.py:20,123-138`).
- `_edit_and_relaunch_agents_bulk` (`_entry_relaunch.py:392`) mounts one verbatim pane
  per killed agent — the fan-out shape `,X` needs for multi-prompt launches.

### The keymap surface (and the retired-`,X` history)

The reports half-disagreed here; both halves are true:

- **Key `X` is free** — no default leader subkey uses it, and subkey uniqueness is
  CI-enforced (`tests/test_keymaps_defaults.py`).
- **But `,X` has history**: it was `kill_marked_and_edit` until that action was folded
  into contextual `,x`. The action ID sits in `_RETIRED_LEADER_KEYS`
  (`keymaps/registry.py:121-124`), and `test_stale_kill_marked_and_edit_override_is_dropped`
  (`tests/test_keymaps_registry_loading_legacy.py:154`) proves a lingering user override
  `kill_marked_and_edit: "X"` is dropped at load. So: use a **new action ID**, keep the
  retired filter untouched, and the migration story is automatic — a stale override
  cannot revive the old action or collide with the new binding.

A new leader action touches eight registration points plus docs: `default_config.yml`
(per the gotchas core memory), `LeaderModeKeymaps` (`keymaps/mode_keymaps.py`), the
dispatcher (`_leader_mode.py`), command label + `AGENTS_ONLY` scope
(`commands/_mode_commands.py`), availability (`commands/_availability_agents.py`),
the conditional footer (`widgets/_keybinding_modes.py`), the help modal
(`modals/help_modal/agents_bindings.py`), and `docs/ace.md`.

---

## Targeting: the session launch record

Record the launch at the moment it is accepted. `_submit_durable_proc` already returns
the placeholder `ObservedProc` (or `None` on a duplicate/scope rejection); today
`_submit_launch_proc` reduces it to a bool (`_launch_procs.py:92`). Change it to return
the `ObservedProc` and push a record onto a small bounded session stack (~8 entries):

```
LaunchRecord(
    proc_ids: list[str],          # placeholder IDs; >1 only for bulk-Patch fan-out
    prompt: str,                  # the resolved submitted prompt
    display_name / project_file / cl_name / launch context snapshot,
    results: list[AgentLaunchResult] | None,   # stamped at T4
    state: IN_FLIGHT | RESOLVED | FAILED | KILL_PENDING | CONSUMED,
)
```

Record in both `_submit_resolved_launch` and `_submit_one_bulk_patch`
(`_launch_start.py:216,377`); stamp results or `FAILED` in `_on_launch_proc_complete`.

Discipline rules (report A's contribution, all cheap to honor):

- **Only accepted submissions become the target.** A rejected Enter (`None` return)
  must not clobber the previous valid target.
- **Completion updates only its own record.** An older concurrent launch finishing late
  must not steal or overwrite the newest target.
- **`,X` consumes a record idempotently.** A second press re-focuses/re-mounts the same
  attempt; it must never fall through and kill the *previous* launch.
- The stack (report B's contribution) makes `,X` composable: launch two agents, press
  `,X` twice, get the obviously-right behavior; stale entries (already killed/dismissed)
  are popped and skipped.

Treat a bulk-Patch submission (N procs from one gesture) as one logical record so `,X`
undoes it as a unit; a multi-prompt `---` launch (N agents from one proc) is likewise
one record with N results.

Rejected alternatives (both reports, verified): newest visible row and
`get_most_recent_agent_name` (`agent/names/_lookup_named.py:226`) are blind to the
in-flight window, retarget onto agents the user didn't launch, and the latter is an
O(all-artifact-dirs) disk scan on a hot key.

---

## Acting during the in-flight window

### Rejected: cancel the launch proc

Verified reasons, in increasing severity:

1. No API: operation procs have no stop path (`stop_proc_shell` guard, above); building
   one is core-backend surface (`rust-core-required`), not a TUI change.
2. Usually too late: by human reaction time the child has typically claimed a name,
   created the artifact dir, and spawned the detached provider process.
3. **The orphan race.** The agent child is `setsid()`-detached (Rust
   `configure_detached_process`; `launch_spawn.py` "detached subprocess"). Killing the
   outer proc post-spawn leaves the child alive while destroying the pending
   `AgentLaunchResult` — ACE never learns what it launched. The multi-prompt rollback
   (`rollback_partial_launch_results`) only runs for in-process exceptions; SIGTERM does
   not travel through it.

Even if built, the completion-time kill would still be needed as the "too late"
fallback — cancellation is pure additional surface for v1.

### Recommended: deferred kill

`,X` while the record is `IN_FLIGHT` does two independent things:

- **Now:** mount the prompt bar seeded from the record's prompt (equivalently
  `_launch_submitted_prompts[placeholder_id]`), mark the record `KILL_PENDING`, hold
  the replacement launch (below), and toast
  `Will kill "<display name>" when its launch finishes`.
- **At T4:** in `_on_launch_proc_complete` — after the record is stamped, before/alongside
  `_handle_launch_results_delta` — see the pending intent, kill every returned
  `AgentLaunchResult` through the ordinary kill path (`_do_kill_agent`), and settle the
  gate from its `on_settled`. Join results to rows via `_artifact_dir_from_launch_result`
  (`_launch_delta.py:35`).

Why this wins: it reuses every existing seam (completion callback, prompt map, barrier,
kill flow, bulk pane mount), it acts only on fully-materialized agents so it is correct
by construction, and the user's perceived latency is zero — matching the deliberate
design of the `,x` latency work rather than fighting it. The honest cost — the agent
briefly starts and burns a few seconds of provider work — is negligible for the stated
use case.

Report A's objections to this approach, adjudicated:

- *"A stuck launch holds the barrier indefinitely."* True but bounded: give the pending
  window its own generous budget with a warn-and-release fallback (same philosophy as
  the existing barrier timeout). The prompt is already restored either way; worst case
  the auto-kill is abandoned with a toast and the user `,x`es the row when it appears.
- *"ACE exit loses the intent."* Accepted for v1 and documented. The launch simply
  completes; the agent appears; ordinary `,x` applies. Cross-restart durability is
  report B's Phase 3 (recover from the proc row + request sidecar) and should wait for
  evidence anyone wants it.
- *"Typed admission may return without direct results for every unit."* **Verified
  real** — see the next section. Scope it; don't let it drag in the full protocol.

### The typed-admission gap (verified this pass)

A prompt containing `%if`/`%proc` cannot use the plain cwd-launch path
(`launch_cwd_agents.py:590` guards this); `sase run` dispatches it through typed
admission (`_launch.py:109`). The completion payload then carries
`admission_complete: bool` (`direct_typed_launch.py:224-231`), and when it is false a
**detached coordinator** (`start_new_session=True` grandchild,
`launch_admission_coordinator.py:33-66`) keeps launching the remaining units *after the
launch proc has exited*. Killing the returned `AgentLaunchResult`s therefore under-kills
a gated launch. Relatedly, admission-deferred agents can surface as `WAITING`/`QUEUED`
rows whose dismissal must actually tear down the coordinator's claim on them, or they
launch anyway later.

v1 scoping: when the deferred kill fires on a payload with `admission_complete: false`,
kill the returned results and toast that gated units continue in the background
(pointing at the ordinary admission surfaces). A true "abort launch bundle" operation is
follow-up work — and per the core-backend boundary it belongs in `sase-core`, which is
where report A's cancellation protocol becomes the right tool *if* that follow-up is
ever prioritized. File it as a task bead; do not block `,X` on it. The
`WAITING`/`QUEUED` teardown question deserves a dedicated test regardless, because
plain `,x` on such a row has the same question today.

### Protecting the name-reuse invariant

Hold the replacement launch for the whole T0→kill-settled span, not just the cleanup
leg. Cleanest shape (report B): treat "a pending launch kill exists" as an additional
condition in `_relaunch_cleanup_is_pending` (`_relaunch_barrier.py:79`), so
`hold_launch_for_relaunch_cleanup` parks the submit through the launch window and hands
off to the ordinary cleanup barrier at T4 — leaving the existing 30s timeout governing
only the cleanup leg it was tuned for. Give the pending-kill leg its own longer,
warn-and-release budget.

### Confirmation policy (merged from both reports)

- **In-flight / deferred branch: no modal.** There is no row yet, and by T4 the user
  has moved on; a modal firing minutes later would be absurd. The `,X` press *is* the
  confirmation — the target is seconds old by definition of this branch.
- **Resolved branch (row exists): reuse `,x`'s exact rule** (`ConfirmKillModal` iff
  live PID; dismiss silently otherwise). `,X` can land on an agent launched twenty
  minutes ago, and silently killing that is a real footgun. One rule to document, one
  path to test.

---

## The `,X` action, end to end

1. Pop the newest live `LaunchRecord` (skipping stale entries). None → toast
   `No recent launch to kill and edit`.
2. `RESOLVED` → map results to rows, reveal the first target with the existing
   navigation machinery (`prepare_agent_navigation_target` /
   `reveal_agent_navigation_target`, `agents/_neighbors.py`) so the action is legible,
   then run the *same* code `,x` runs: refactor `_kill_and_edit_agent` to accept an
   explicit target (defaulting to `_get_selected_agent()`), routing multi-result
   records through `_edit_and_relaunch_agents_bulk`. Same prompt rewriting (forced name
   reuse), same confirmation rule, same barrier — no behavioral fork.
3. `IN_FLIGHT` → deferred-kill branch as above.
4. `KILL_PENDING` (repeat press) → re-focus the restored prompt; register nothing new.

Explicitly: **`,X` ignores marks** (say so in help — the two keys are adjacent);
**never hand a clan container to the kill path** (records hold concrete results, so
this falls out naturally); a launch that *failed* discards the intent, releases the
gate, and must **not** double-stash the prompt — the failure path already stashes it
(`_launch_procs.py:115-120`).

Naming: action ID `kill_and_edit_last` (sorts next to `kill_and_edit` in the palette;
report A's `kill_last_launch_and_edit` is equivalent — pick one and keep the retired
`kill_marked_and_edit` filter untouched). Label: `Kill last launched agent and edit`.
Availability: runnable iff a live record exists, independent of the focused row;
conditional footer hint per the footer convention (it is sometimes-true state).

---

## Failure modes (merged)

| Scenario | Required behavior |
| --- | --- |
| No launch this session | Toast, do nothing. |
| Submission rejected (dup/scope) | Prior target unchanged. |
| Launch fails while intent pending | Discard intent, release gate, warn; prompt stashed exactly once by the existing failure path. |
| `,X` twice during one flight | Idempotent; never advances to the previous launch. |
| Older launch completes after newer target set | Updates its own record only. |
| Target already killed/dismissed by hand | Pop, try next record, or warn — never kill an unrelated row. |
| Multi-prompt / bulk-Patch record | Kill all children of the record; one pane each, in order. |
| Typed launch, `admission_complete: false` | Kill returned results; warn that gated units continue (v1). |
| `WAITING`/`QUEUED` target | Dismiss path; verify coordinator teardown — dedicated test. |
| Launch outlives barrier budget | Warn-and-release; prompt already restored; no silent relaunch race. |
| ACE restart mid-flight | v1: no record, toast; agent appears and `,x` applies. Phase 3 if wanted. |
| Prompt bar already holds a draft | Same as `,x`: unmount, draft goes to history/stash. |

---

## Tests

Homes to copy: `test_kill_and_edit_launch_barrier.py`, `test_agent_bulk_kill_edit.py`,
`test_launch_delta_handler.py`, `test_leader_keymap_dispatch.py`,
`test_keymaps_defaults.py`, `test_keymaps_registry_loading_legacy.py`,
`test_command_catalog.py`, `test_command_availability_agents.py`,
`test_agent_launch_non_blocking.py`, `test_durable_submit.py`.

Highest-value coverage, beyond the obvious keymap/dispatch/availability assertions:
(1) accepted-target ordering — a rejected submit and a late-finishing older launch
never steal the slot; (2) the pending-placeholder race — press `,X` before the durable
ID exists, release the submit worker, assert the kill intent is found via the existing
callback bridge exactly once; (3) in-flight branch — prompt bar mounts before proc
completion, kill fires from the completion callback, relaunch stays parked until the
kill settles, forced name reuse preserved; (4) failed launch — intent discarded, prompt
stashed exactly once; (5) fan-out — N results → N kills → N panes in order; (6)
`WAITING`/`QUEUED` teardown; (7) `,X` handler does no synchronous disk/proc-store work.
Footer + help changes require the PNG snapshot suite per `lint_and_test.md`; `just
check` is the agent lane.

---

## Recommended solution

Build `,X` as **"resolve this session's last accepted launch, reveal it, and run the
existing `,x` flow on it — with a deferred kill when the launch is still in flight."**
Concretely:

1. Have `_submit_launch_proc` return the placeholder `ObservedProc`; push a
   `LaunchRecord` (bounded stack, ~8) in `_submit_resolved_launch` /
   `_submit_one_bulk_patch`; stamp results/failure in `_on_launch_proc_complete`.
2. `,X` = new action `kill_and_edit_last` on key `X` (retired `kill_marked_and_edit`
   filter untouched), registered across all eight keymap surfaces plus docs, available
   iff a live record exists, marks ignored.
3. Resolved records delegate to the refactored `,x` machinery (explicit-target
   `_kill_and_edit_agent`, bulk path for fan-out) — same confirmation rule, same
   forced-name-reuse rewrite, same cleanup barrier.
4. In-flight records restore the prompt instantly and register a pending kill executed
   from the launch-completion callback via the ordinary kill path — no confirmation on
   this branch, no launch-proc cancellation ever.
5. Extend `_relaunch_cleanup_is_pending` so the replacement launch is parked from
   T0 to kill-settled, with a generous warn-and-release budget for the launch leg and
   the existing 30s timeout for the cleanup leg.
6. Scope typed admission: kill returned results, toast when `admission_complete` is
   false; file the "abort launch bundle" backend operation (sase-core, where report A's
   cancellation protocol applies) as follow-up rather than blocking on it.

Ship the record/keymap work and the in-flight branch **together** — the stated use case
lands inside the T0→T4 window, so the in-flight branch is the feature, not an
enhancement. Before tuning the pending-window budget, run a few real launches with
`SASE_AGENT_LAUNCH_TIMING=1` to see the actual T0→T4 distribution. Defer ACE-restart
durability until someone asks for it; drop launch-proc cancellation entirely.
