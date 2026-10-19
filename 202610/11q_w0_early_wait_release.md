# Why `11q.w0` started before `11q` finished

**Short answer:** `11q.w0` waited on `11q` with `%w:11q`. The wait checker released it
during an 18-second gap after 11q's plan gate was approved and before the coder it
approved (`11q--code`) existed. In that gap the gate's metadata briefly said its
follow-up had **failed**. The wait resolver reads a failed follow-up as "no successor
coming", so the `11q` session looked finished: the plan was DONE and the gate was
settled. This is a bug: a value written *before* the launch is read as the launch's
final result.

## Timeline (2026-10-19, EDT)

| Time         | Event                                                                                  |
| ------------ | -------------------------------------------------------------------------------------- |
| 09:26:25     | `11q--plan` launched                                                                   |
| 09:41:18     | `11q.w0--plan` launched with `%w:11q` and parks                                        |
| 09:42:09     | `11q--plan` DONE (plan submitted); plan gate `11q--gate` opens                         |
| 09:43:55.12  | Gate answered (approve + commit); settlement's follow-up stage starts                  |
| 09:43:55.21  | Gate writes its first `done.json` (`gated`/`answered`, no follow-up fields)            |
| ~09:43:56    | Gate metadata gets `gate_followup_outcome: "failed"`; launch of `11q--code` begins     |
| 09:43:56–44:05 | `wait_checks` tick resolves `11q`; logs "Dependencies satisfied … waited on: 11q"    |
| 09:44:13     | `11q--code` artifact dir created; gate rewrites `done.json` with `launched → 11q--code` |
| 09:44:25     | **`11q.w0--plan` starts running**                                                      |
| 09:44:49     | `11q--code` starts running                                                             |
| 09:54 → now  | 11q goes on: `11q--mon` (failed tests) → `11q--1` queued. 11q is still not done        |

The waiter's own record shows when it was released: `wait_dependencies_satisfied_at` is
09:43:55.21. That is the `finished_at` of the gate's *first* `done.json`. The
`wait_release_source` is `ready_json`.

## Mechanism

1. **Gate settlement writes "failed" before it launches anything.** In
   `src/sase/gate_turn/settlement.py`, `_settle_gate_turn_locked` writes `done.json` and
   then calls `launch_or_record_followup` (`gate_turn/handoff_launch.py`). That function
   first runs the Rust classifier (`classify_gate_handoff`), then `apply_decision`, and
   only after that launches. On the normal settle input (gate `answered`, follow-up
   requested, nothing recorded yet) the classifier returns:
   `persist_outcome: "failed"`, `disposition: "interrupted"`, `launch_allowed: true`.
   `apply_decision` writes that `"failed"` to the gate's `agent_meta.json`. The real
   outcome (`launched`, agent `11q--code`) is only written about 18 s later. Most of that
   time goes to `wait_for_starter` and spawning the agent.
2. **The wait resolver treats "failed" as "no successor".** In
   `core/wait_dependency_resolution/_artifact_state.py`, `turn_followup_handoff_agent`
   returns the `<pending-turn-followup>` placeholder only when `followup_outcome is
   None`. A gate whose follow-up is still pending holds its session open because of that
   placeholder. Any other outcome that isn't a success returns `None`. So a gate marked
   `"failed"` has no expected successor, `handoffs_present` is true, and the
   `_agent_session_entity` aggregate for `11q` becomes resolved and done.
3. **The safety checks didn't catch it.** The confirmation re-scan only looks for *new
   member directories*. `11q--code`'s directory didn't exist until 09:44:13, which was
   after the release. A release is one-shot, so when 11q became unresolved again a few
   seconds later, nothing took the release back.

## Verification

I rebuilt the resolver's view from the real `~/.sase/projects` tree, rewound to the
window: gate `done.json` #1 and no `11q--code` directory. Then I ran
`dependency_resolution_status(index, ["11q"])`:

| Gate meta `gate_followup_outcome` | `11q` session aggregate | `%w:11q`   |
| --------------------------------- | ----------------------- | ---------- |
| absent (what the guard expects)   | `is_resolved=False`     | `waiting`  |
| `"failed"` (the settle-time value) | `is_resolved=True`      | `resolved` |

The classifier result above comes from calling `classify_gate_handoff(mode="settle", …)`
through the installed binding. The interim `"failed"` value can't be read on disk any
more because the later `launched` write replaced it. The code path that writes it is
deterministic, though.

## Impact

This is not a rare race. The gate's own `done.json` write is a watched-path change, so
it wakes `wait_checks`. That tick finishes well inside the ~18 s launch window. **Any
`%w:<session>` waiting on a session whose plan gate gets approved will probably be
released at approval time** instead of when the session's coder, monitor, and retry turns
are done.

## Fix directions

- Don't persist a terminal-looking `gate_followup_outcome` before the launch in settle
  mode. Record it only from the launch result. Alternatively, have the classifier use a
  non-terminal value such as `launching` there.
- Make the resolver's guard stricter: treat a gate with `gate_next_action` set as
  pending unless its outcome is *settled*. Settled means `launched` with the successor
  present, or a failure whose attempt is no longer live (`gate_followup_attempt_live`
  false). `persist_attempt` marks the attempt live (`preparing`, then `launching`)
  right after the `"failed"` write, so at release time the attempt was almost certainly
  still live.
- Add a regression test: an approved plan gate mid-launch (outcome `"failed"`, live
  `launching` attempt, no successor directory) must keep a `%w:<session>` waiter parked.
