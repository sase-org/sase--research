---
create_time: 2026-09-03
updated_time: 2026-09-03
status: research
---

# `,X` — Kill And Edit The Agent You Just Launched

**Research question:** add a `,X` leader keymap to the Agents tab that behaves like `,x`
(kill & edit) but targets *the most recently launched agent* rather than the focused row —
including an agent whose launch proc has not finished yet, so the user can undo a premature
`<enter>` immediately. What should "most recently launched" mean, how do we act on an agent
that does not exist yet, and what is the smallest correct implementation?

**Scope:** `sase` at master `9e2d95bb0`. Read paths: the whole `,x` implementation
(`agent_workflow/_entry_relaunch.py`, `agents/_marking_kill.py`, `_relaunch_barrier.py`),
the ACE launch pipeline (`_launch_start.py`, `_launch_procs.py`, `agent_durable.py`,
`_proc_action_submission.py`, `proc_observer.py`, `_launch_delta.py`), the durable proc
service and its operation-request sidecars (`sase/procs/`), the `sase run` child entry
(`main/query_handler/_launch.py`, `agent/launch_cwd*.py`), agent status/identity models,
and the full keymap registration surface (config, registry, dispatcher, command catalog,
footer, help modal, docs). Prior design context read from
`plans/202608/kill_and_edit_prompt_latency.md` and `plans/202606/remove_leader_x_bulk_kill_edit.md`.
No runtime instrumentation was collected; every structural claim is cited to source.

---

## Executive summary

The feature decomposes into two genuinely different problems, and conflating them is the
main way this gets built wrong:

1. **Targeting.** "The last launched agent" needs a definition that is stable, cheap, and
   matches user intent. The right one is *session-scoped*: the last launch **this ACE
   session submitted**, not the newest row on disk. ACE already has the exact handle for
   this — `_submit_launch_proc` gets a synchronous placeholder `ObservedProc` back from
   `register_pending` and already keys the submitted prompt off it
   (`_launch_procs.py:55`, `proc_observer.py:114`). Recording one more field there is the
   whole targeting mechanism.

2. **Acting before the agent exists.** During the launch window there is no `Agent` row to
   kill. The correct answer is **not** to cancel the launch — it is to *defer the kill* and
   *not defer the edit*. The prompt is already in memory
   (`_launch_submitted_prompts`, `_launch_procs.py:82-90`) and durably on disk in the proc's
   operation-request sidecar (`procs/service.py:428`), so the prompt bar can mount
   instantly. The kill then runs from the launch proc's existing completion callback, which
   hands back `AgentLaunchResult` objects carrying `artifacts_dir`, `agent_name`, `pid` and
   `timestamp` (`agent/launch_types.py`) — an exact handle on what to kill.

The relaunch cleanup barrier built for `,x`'s latency fix (`_relaunch_barrier.py`) is
*exactly* the primitive needed to make the deferred kill safe: it already exists to hold a
replacement launch until an old agent's cleanup settles. `,X` reuses it unchanged, with one
adjustment to its 30s timeout.

Recommended shape: **`,X` = "resolve the last launch → reveal it → run the `,x` flow on it",
with a deferred-kill branch when the launch proc is still in flight.** Details and phasing
in [Recommended solution](#recommended-solution).

---

## 1. What `,x` does today

### 1.1 Registration surface

`,x` is a leader-mode action named `kill_and_edit`, and it is wired in **eight** places.
Any new leader action must touch the same set:

| Concern | File | Note |
| --- | --- | --- |
| Shipped default | `src/sase/default_config.yml:738` | `kill_and_edit: "x"` |
| Typed default | `src/sase/ace/tui/keymaps/mode_keymaps.py:174` | `LeaderModeKeymaps.keys` |
| Dispatcher | `src/sase/ace/tui/actions/agent_workflow/_leader_mode.py:204` | key → method |
| Command label | `src/sase/ace/tui/commands/_mode_commands.py:66` | palette title |
| Command tab scope | `src/sase/ace/tui/commands/_mode_commands.py:106` | `AGENTS_ONLY` |
| Command availability | `src/sase/ace/tui/commands/_availability_agents.py:222` | greys out when unrunnable |
| Footer hint | `src/sase/ace/tui/widgets/_keybinding_modes.py:403` | leader footer row |
| Help modal | `src/sase/ace/tui/modals/help_modal/agents_bindings.py:283` | `?` bindings table |

Plus user-facing docs at `docs/ace.md:2251` (the `,`-table) and the prose that follows it.

`X` is free: no default leader subkey uses it (`mode_keymaps.py:154-186`), and
`tests/test_keymaps_defaults.py:375` enforces subkey uniqueness, so a collision would fail
CI immediately. The registry also drops retired action ids
(`keymaps/registry.py:112-135`) — `kill_and_edit_last` is new, so nothing to reconcile there.

### 1.2 The `,x` flow

The dispatcher branches on marks first (`_leader_mode.py:204-216`):

```
,x  →  marks exist?  →  yes: _bulk_kill_marked_agents_and_edit()   (_marking_kill.py:51)
                       →  no:  _kill_and_edit_agent()               (_entry_relaunch.py:215)
```

The single-row path is five steps:

1. **Resolve the target.** `self._get_selected_agent()` (`agents/_selection.py:236`).
   Clan containers are refused with a "mark its members" warning
   (`_entry_relaunch.py:220-232`).
2. **Resolve the prompt off the event loop.** `schedule_relaunch_prompt_resolution`
   (`_entry_relaunch.py:74`) runs `prepare_kill_edit_agent_prompt` in a thread; that reads
   the stored raw xprompt and rewrites its identity for forced name reuse via
   `prepare_kill_and_edit_prompt` (`sase/agent/relaunch_prompt.py:101`), producing
   `%id(!name)` / `%id:!name` forms.
3. **Re-resolve the row** after the async hop (`resolve_agent_identity`,
   `_entry_relaunch.py:134`) — the row may have moved or vanished.
4. **Kill or dismiss** (`_finish_kill_and_edit_agent`, `_entry_relaunch.py:271`):
   - `agent.status in DISMISSABLE_STATUSES or agent.pid is None` → optimistic dismiss, no
     confirmation (`models/agent_status.py:16`);
   - otherwise → `ConfirmKillModal`, then `_do_kill_agent` (`agents/_kill_flow.py:32`).
5. **Mount the prompt bar immediately**, and hold the *eventual relaunch* behind a
   `_RelaunchCleanupBarrier` until the kill/dismiss persistence proc settles
   (`_relaunch_barrier.py`). `_submit_resolved_launch` calls
   `hold_launch_for_relaunch_cleanup` first and parks itself if any barrier is open
   (`_launch_start.py:230-240`).

That barrier exists because `apply_force_reuse_launch` wipes the old owner's name state,
and a late dismissed-bundle write from the old cleanup would re-register the name the
replacement just claimed — see `plans/202608/kill_and_edit_prompt_latency.md`. **This is the
single most important invariant to preserve in `,X`.** The barrier times out after 30s
(`_relaunch_barrier.py:20`) and then releases held launches with a warning toast.

### 1.3 Fan-out shape

`_edit_and_relaunch_agents_bulk` (`_entry_relaunch.py:392`) seeds one verbatim prompt pane
per killed agent, deliberately *without* `---` splitting, so N killed agents map to N panes.
`,X` needs this whenever one launch produced more than one agent.

---

## 2. The launch pipeline, and what exists at each instant

This is the part that decides the design. Walking `<enter>` → visible row:

| T | Event | Code | State that exists |
| --- | --- | --- | --- |
| T0 | User submits | `_submit_resolved_launch` (`_launch_start.py:216`) | `ctx` (display name, project file, cl name), a reserved launch timestamp, the resolved prompt text |
| T0+ε | Placeholder proc registered **synchronously** | `_submit_durable_proc` → `observer.register_pending` (`_proc_action_submission.py:120`, `proc_observer.py:114`) | `ObservedProc(proc_id="pending-<uuid>", proc_type="launch", …)` returned to the caller |
| T0+ε | Prompt stashed in memory | `_submit_launch_proc` (`_launch_procs.py:82-90`) | `self._launch_submitted_prompts[placeholder_id] = prompt` |
| T1 | Durable submit completes on a thread worker | `submit_durable_proc_request` | Real durable proc row; operation request sidecar written to `proc_operation_request_path(proc_id)` containing the full `{"prompt": …}` payload (`procs/service.py:409-439`) |
| T2 | Supervisor spawns `python -m sase run` | `procs/spawn.py` | Fresh interpreter (~0.4s of pure startup, per the latency plan) |
| T3 | Child expands the prompt, allocates names, reserves its **own** timestamp, spawns agent process(es) | `main/query_handler/_launch.py:23` → `launch_agents_from_cwd` (`agent/launch_cwd.py:24`) | Artifact dir + `agent_meta.json` on disk; detached agent PID |
| T4 | Proc terminal; observer notices within `POLL_SECONDS = 0.5` (`proc_observer.py:55`) | `_on_launch_proc_complete` (`_launch_procs.py:94`) | `AgentLaunchResult[]` with `pid`, `artifacts_dir`, `agent_name`, `timestamp`, `cl_name` (`agent/launch_types.py`) |
| T5 | Bounded artifact-dir delta refresh | `_handle_launch_results_delta` (`_launch_delta.py:56`) | The `Agent` row finally appears in the Agents tab |

Four things follow directly:

- **ACE never knows the agent's identity before T4.** The child reserves its own timestamp
  (`launch_agents_from_cwd(query, …)` is called with `timestamp=None`,
  `_launch.py:139-146`), so ACE's `ctx.timestamp` is *not* the agent's artifact timestamp.
  It is drawn from the same global monotonic reservation
  (`core/agent_launch_facade.py:104`), so it orders correctly, but it cannot be used as an
  identity.
- **The prompt, however, is known at T0.** Both in memory and — from T1 — durably on disk.
  So the *edit* half of kill-and-edit never needs to wait for anything.
- **`AgentLaunchResult` is the join key.** `_artifact_dir_from_launch_result`
  (`_launch_delta.py:34`) already turns one into the exact artifact directory the row will
  carry, which is how `,X` will match proc → row.
- **The window is not short.** T2→T4 covers interpreter startup, xprompt expansion,
  workspace preparation and provider spawn; `launch_timing.py:16` sets its *slow stage*
  threshold at 30s, and `SASE_AGENT_LAUNCH_TIMING=1` exists precisely to profile it. This
  window is exactly where the user's "I hit enter too fast" reflex lands, and it can exceed
  the barrier's 30s timeout.

### 2.1 In-flight launches are already observable

`self._proc_projection.active_rows()` (`_proc_observer_models.py:137`) returns every active
proc, including `proc_type == "launch"` rows, ordered by `started_at`. Combined with the
placeholder-id → prompt map, ACE can already answer "is a launch in flight, and what prompt
did it carry?" with no new plumbing. This is also the crash-recovery story: after an ACE
restart the in-memory map is gone, but the proc row and its request sidecar survive, so a
fallback read of `proc_operation_request_path(proc_id)` recovers the prompt (the same read
`main/query_handler/special_cases.py:89` already performs).

---

## 3. What should "most recently launched" mean?

Four candidate definitions, all implementable:

**A. Newest agent row by artifact timestamp.** Scan `_agents_with_children`, take max
`raw_suffix`. *Rejected.* It cannot see the in-flight window at all — the exact case the
feature exists for — and it silently retargets onto agents the user did not launch: family
members, clan members, monitor shells, gate shells, and agents spawned *by* the agent they
just launched. Pressing `,X` and killing your agent's child is a bad surprise.

**B. Newest agent by name registry.** `get_most_recent_agent_name`
(`agent/names/_lookup_named.py:226`) already exists and scans every project's
`agent_meta.json`. *Rejected for this purpose.* Same blindness to the in-flight window,
plus it is an O(all artifact dirs) disk scan on a key that must feel instant, and it is
name-scoped (unnamed agents are invisible to it).

**C. Last launch submitted by this ACE session.** Recorded at T0 in `_submit_resolved_launch`
/ `_submit_one_bulk_patch`, upgraded at T4 with the resolved `AgentLaunchResult[]`.
*Recommended.* It is exactly "the thing you just pressed enter on", covers the in-flight
window by construction, costs one dict assignment on the launch path, and is immune to
children, monitors and background arrivals.

**D. C, with a disk-backed fallback to the newest ACE-origin launch proc.** Same as C but
when the session record is empty (ACE restarted, or the launch came from another session),
fall back to the newest terminal `origin="ace"` launch proc in the store and use its
`AgentLaunchResult`/request sidecar. *Recommended as a later phase only* — see
[§7](#7-phasing-and-what-to-defer).

A worthwhile refinement on C: keep a small **stack** (say the last 8 launches) rather than a
single slot. Cost is trivial, and it makes `,X` composable — pressing it twice in a row after
launching two agents does the obviously-right thing instead of failing on the second press.
It also gives a clean answer when the top entry is stale (already killed, already dismissed):
pop and try the next.

---

## 4. Acting on an agent that has not started

Three strategies for the T0–T4 window.

### 4.1 Cancel the launch proc (rejected)

Stop the `sase run` proc before it spawns anything. Problems:

- **No API for it.** `stop_proc_shell` (`procs/service.py:162`) is guarded to
  `PROC_LIFECYCLE_PROC_SHELL` rows (`procs/settlement.py:150`); an operation proc like
  `run.launch` is a different lifecycle. Stopping one is new plumbing in the durable proc
  layer — and by `rust-core-required` / `host-owned-completion` that plumbing is core
  backend surface, not a TUI-local change.
- **It is inherently racy and usually loses.** By the time a human reacts (≥1s) the child is
  typically past `launch_agents_from_cwd`, which has already reserved a timestamp, claimed a
  name, created the artifact dir, possibly prepared a workspace, and spawned a detached
  provider process. Killing the parent then orphans all of it.
- **Partial-kill damage.** A half-executed launch is precisely the state
  `launch_admission_runtime.stop_proc_identity` and the orphan-reaping chops exist to clean
  up. Manufacturing more of it from a hot keybinding is the wrong trade.

Even if built, it would still need 4.2 as the fallback for "too late". That makes it pure
additional surface.

### 4.2 Deferred kill (recommended)

`,X` during flight does two independent things:

- **Now:** mount the prompt bar seeded from `_launch_submitted_prompts[placeholder_id]`,
  open a relaunch cleanup barrier, and toast `Will kill "<display name>" when its launch
  finishes`.
- **Later, at T4:** in `_on_launch_proc_complete`, before/alongside
  `_handle_launch_results_delta`, notice the pending kill intent for that proc id and kill
  every returned `AgentLaunchResult`. Settle the barrier when the kill's persistence proc
  settles.

Why this is the right one:

- **It reuses every existing seam.** The completion callback, the submitted-prompt map, the
  barrier, `_do_kill_agent`'s `on_settled`, and the bulk pane mount are all already there
  and already tested.
- **It is correct by construction.** At T4 the agent is fully materialized: real PID, real
  artifact dir, real name. Killing it uses the ordinary, well-tested kill path rather than a
  novel abort path.
- **The user's latency is zero.** They get their prompt back immediately; the kill happens
  behind them. This matches the deliberate design of the `,x` latency fix
  (`plans/202608/kill_and_edit_prompt_latency.md`) rather than fighting it.

The cost is honest and worth stating: the agent *does* briefly start and burn a little
provider work before being killed. For the stated use case (an agent that has been alive for
under a few seconds) that is negligible, and it is strictly better than the alternative of
making the user wait.

**Two wrinkles that must be handled:**

- **Barrier timeout.** 30s (`_relaunch_barrier.py:20`) is tuned for a cleanup round trip, not
  for "wait out a whole launch and then a cleanup". If the launch takes 40s, the barrier
  times out, releases the parked relaunch, and the forced-name-reuse race the barrier exists
  to prevent comes back. Fix: give the pending-launch barrier its own longer budget (a
  parameter on `open_relaunch_cleanup_barrier`), or start the barrier only when the deferred
  kill is actually submitted at T4, keeping a separate lightweight "pending kill" gate for
  the T0–T4 stretch. The second is cleaner: the relaunch is held by *pending kill intent
  exists* until T4, then by the ordinary cleanup barrier.
- **Failed launches.** If the launch proc fails (no results, or a payloadless worker death,
  `_launch_procs.py:104-125`), there is nothing to kill. The intent must be discarded, the
  gate released, and the user told — and note that the failure path already stashes the
  prompt (`_schedule_failed_launch_prompt_recovery`), so `,X` must not double-stash.

### 4.3 Wait-then-kill with a blocked UI (rejected)

Mount nothing until T4, then run the normal `,x` flow. Simple, but it reintroduces exactly
the multi-second dead pause that `plans/202608/kill_and_edit_prompt_latency.md` was written
to remove, on the one keybinding whose entire justification is speed.

---

## 5. Design decisions worth making explicitly

**Reveal the target before acting.** Unlike `,x`, `,X` acts on a row the user may not be
looking at. Focusing it first makes the action legible and costs nothing: the machinery
already exists as `prepare_agent_navigation_target` / `reveal_agent_navigation_target`
(used by `_focus_agent_neighbor_by_identity`, `agents/_neighbors.py:336`), which also
handles revealing a collapsed clan/panel. This reframes the whole feature as
**"jump to the last launch, then `,x` it"** — a much smaller thing to build and explain.

**Confirmation.** Reuse `,x`'s rule (`ConfirmKillModal` iff there is a live PID) rather than
inventing a new one. It is tempting to skip confirmation for speed, but `,X` can also land
on an agent launched twenty minutes ago, and dismissing that silently is a real footgun.
Keeping the rule identical means one behavior to document and one code path to test. If a
fast path is wanted later, gate it on *recency* (target launched by this session within N
seconds), not on the key.

**Marks are irrelevant.** `,x` is mark-contextual; `,X` is defined by "the last launch" and
must ignore `_marked_agents` entirely. Say so in the help text, since the two keys sit next
to each other.

**Fan-out.** One submit can yield N agents — a multi-prompt (`---`) launch returns a list
from `launch_agents_from_cwd`, and `_handle_launch_results_delta` already handles the list
form. `,X` on such a launch should kill all of them and mount one pane each via
`_edit_and_relaunch_agents_bulk` (`_entry_relaunch.py:392`). Note the bulk-Patch launch
(`_submit_bulk_resolved_launch`, `_launch_start.py:313`) is the opposite shape: N *procs*
from one submit. Treat that whole fan-out as one logical launch record so `,X` undoes the
bulk launch as a unit, not just its last Patch.

**Clan containers.** `_kill_and_edit_agent` refuses them (`_entry_relaunch.py:220`). Since
`,X` resolves concrete `AgentLaunchResult`s rather than a focused row, it should target the
concrete members directly and never hand a container to the kill path.

**Availability.** `leader.kill_and_edit_last` should be reported runnable when a session
launch record exists (in-flight or resolved), independent of the focused row — parallel to
how `leader.kill_and_edit` is reported runnable when marks exist
(`_availability_agents.py:222`). The footer hint should be conditional too, so `,X` only
advertises itself when there is something to act on.

**Naming.** `kill_and_edit_last` reads well next to `kill_and_edit` and sorts adjacently in
the command palette. Label: `Kill last launched agent and edit`.

---

## 6. Failure modes to design against

| Scenario | Required behavior |
| --- | --- |
| No launch this session | Warn `No recent launch to kill`; do nothing. (With the disk fallback of §3-D, try that first.) |
| Launch in flight, then it fails | Discard the intent, release the gate, warn; do not double-stash the prompt (the failure path already stashes it, `_launch_procs.py:118-124`). |
| `,X` pressed twice while one launch is in flight | Idempotent: second press re-focuses/re-mounts, does not register a second kill intent. |
| Target already killed/dismissed by hand | Pop the launch stack entry, fall through to the next, or warn cleanly — never kill an unrelated row. |
| Target is a clan/family container | Act on concrete members; never pass a container to `_do_kill_agent`. |
| Target went `WAITING`/`QUEUED` via launch admission | Ordinary row with `pid is None` → dismiss path, no confirmation. Verify the admission coordinator is actually torn down by the existing cleanup, or the agent will still launch later. **This one deserves a dedicated test.** |
| ACE restarted between launch and `,X` | Phase 1: warn (no session record). Phase 2: recover from the durable proc row + request sidecar. |
| Launch exceeds the barrier timeout | See §4.2 — do not let a plain 30s timeout release the relaunch while the kill is still pending. |
| Prompt bar already mounted with a draft | Same policy as `,x`: `_mount_edit_relaunch_prompt_bar` unmounts the existing bar (`_entry_relaunch.py:418-448`), and the discarded draft goes to prompt history/stash. Worth confirming this is acceptable for a key the user may hit reflexively. |

---

## 7. Phasing, and what to defer

**Phase 1 — the 90% case.** Session-scoped launch record (a small stack), `,X` resolves it,
reveals the row, and runs the existing `,x` flow on it. No deferred kill yet: if the launch
is still in flight, warn `Launch still starting; try again in a moment`. This alone is
useful, is a genuinely small diff, and gets the whole keymap registration surface landed and
tested.

**Phase 2 — the in-flight window.** Deferred kill intent keyed on the launch proc id,
resolved in `_on_launch_proc_complete`, prompt bar seeded from
`_launch_submitted_prompts`, plus the barrier/timeout adjustment from §4.2. This is where
the real value is, and where the real risk is.

**Phase 3 (optional) — durability.** Disk fallback via the launch proc's operation-request
sidecar so `,X` survives an ACE restart.

**Explicitly do not build:** launch-proc cancellation (§4.1); a `sase agent restart`-style
CLI equivalent (`sase agent restart NAME` already covers the scripted case,
`docs/ace.md:2262`); any new definition of "recent" that scans disk on the hot path.

---

## 8. Test surface

Existing suites give the shape to copy: `tests/ace/tui/test_kill_and_edit_launch_barrier.py`,
`test_agent_bulk_kill_edit.py`, `test_kill_and_edit_agent_name.py`,
`test_launch_delta_handler.py`, `test_leader_keymap_dispatch.py` (with
`_leader_keymap_helpers.py`), `test_leader_keybinding_footer.py`, and the keymap/command
catalog suites (`tests/test_keymaps_defaults.py`, `test_command_catalog.py`,
`test_command_availability_agents.py`).

Minimum new coverage:

1. `,X` is `X`, is unique, survives a user override, and is not in `_RETIRED_LEADER_KEYS`.
2. Dispatch: `,X` on Agents calls the new method; on other tabs it is a no-op.
3. Availability + footer: advertised iff a launch record exists; ignores marks.
4. Targeting: after two launches, `,X` targets the second; a child agent launched by the
   target does not steal the slot.
5. Resolved-row path: reveals the row, then kills/dismisses under `,x`'s existing rules and
   mounts the rewritten prompt (forced name reuse preserved).
6. In-flight path: prompt bar mounts before the launch proc completes; the kill fires from
   the completion callback; the relaunch stays parked until the kill settles.
7. Failed in-flight launch: intent discarded, gate released, prompt stashed exactly once.
8. Fan-out: a `---` launch produces N killed agents and N prompt panes in launch order.
9. `WAITING`/`QUEUED` (admission-gated) target is fully torn down, not merely dismissed.

Per `sase/memory/lint_and_test.md`, `just check` is the agent default; anything touching the
footer or help modal also needs the PNG snapshot suite refreshed, since `,X` adds a footer
hint and a help-table row.

---

## Recommended solution

Build `,X` as **"resolve the last launch, reveal it, then run the existing `,x` flow on
it"** — reusing every seam `,x` already has, and adding exactly one new concept (a pending
kill intent) for the in-flight window.

**1. Record the launch (targeting).**
In `_submit_resolved_launch` (`_launch_start.py:216`) and `_submit_one_bulk_patch`
(`_launch_start.py:377`), have `_submit_launch_proc` return the placeholder `ObservedProc`
instead of a bool, and push a `LaunchRecord` onto a bounded session stack
(`_recent_launches`, max ~8):

```
LaunchRecord(
    proc_ids: list[str],        # >1 only for a bulk-Patch fan-out
    prompt: str,
    display_name: str,
    project_file: str, cl_name: str, is_project_agent: bool,
    results: list[AgentLaunchResult] | None,   # filled at T4
    state: IN_FLIGHT | RESOLVED | FAILED,
)
```

In `_on_launch_proc_complete` (`_launch_procs.py:94`), stamp the matching record with
`outcome.results` (or mark it `FAILED`). This is a handful of lines on a path that already
tracks per-proc launch state.

**2. `,X` resolves the top live record.**
- `RESOLVED` → map each `AgentLaunchResult` to a row via `_artifact_dir_from_launch_result`
  (`_launch_delta.py:34`) matched against `agent.get_artifacts_dir()`. Reveal the first
  target with the existing navigation machinery, then call the *same* code `,x` calls —
  refactor `_kill_and_edit_agent` to take an optional explicit target agent (defaulting to
  `_get_selected_agent()`), and route multi-result launches through
  `_edit_and_relaunch_agents_bulk`. No behavioral fork: same prompt rewriting, same
  confirmation rule, same barrier.
- `IN_FLIGHT` → mount the prompt bar immediately from
  `_launch_submitted_prompts[proc_id]`, register the pending kill intent against that proc
  id, and open the relaunch gate. Toast the target's display name.
- Empty / all-stale → `No recent launch to kill`.

**3. Deferred kill (the in-flight branch).**
Keep a `_pending_launch_kills: dict[proc_id, PendingKill]`. In `_on_launch_proc_complete`,
after the record is stamped and before `_handle_launch_results_delta`, if a pending kill
exists for that proc, kill every produced agent through the ordinary kill path and settle
the gate from `_do_kill_agent(..., on_settled=…)`. On launch failure, discard the intent,
release the gate, and let the existing failure handling own the prompt stash.

**4. Protect the name-reuse invariant.**
Hold the relaunch for the whole T0→kill-settled span, not just the cleanup span. Cleanest:
treat "a pending launch kill exists" as an additional condition inside
`_relaunch_cleanup_is_pending` (`_relaunch_barrier.py:79`), so `hold_launch_for_relaunch_cleanup`
parks the submit through the launch window and hands off to the ordinary cleanup barrier at
T4 — with the existing 30s timeout still governing only the cleanup leg it was tuned for.

**5. Register and document.**
Add `kill_and_edit_last: "X"` to `default_config.yml` and `LeaderModeKeymaps`; dispatch in
`_leader_mode.py`; label + `AGENTS_ONLY` scope in `_mode_commands.py`; availability in
`_availability_agents.py`; a conditional footer hint in `_keybinding_modes.py`; a help row
in `agents_bindings.py`; and a `docs/ace.md` table row plus a short paragraph stating the
three things a user must know — *it ignores marks*, *it works before the agent appears*, and
*it confirms exactly when `,x` would*.

**Ship Phase 1 and Phase 2 together if the appetite allows** — Phase 1 alone does not
actually solve the stated problem, since the "I hit enter too fast" reflex lands squarely
inside the in-flight window. Phase 3 (ACE-restart durability) is genuinely optional and can
wait for evidence anyone wants it.

**First thing to measure before building:** put `SASE_AGENT_LAUNCH_TIMING=1` on a few real
launches and record the actual T0→T4 distribution. If that window is reliably under ~1.5s,
Phase 2's complexity is arguably not worth it and Phase 1 plus a "still starting, try again"
toast may be the whole feature. If it is commonly 3–10s — which the 30s slow-stage threshold
in `launch_timing.py:16` suggests is expected — Phase 2 is the feature.
