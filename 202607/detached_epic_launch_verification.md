# Verification: detached epic launch, with and without a TUI

Phase `verify` of epic `sase-9s` (plan `202607/detached_epic_launch.md`), bead `sase-9s.8`, run 2026-07-26.

This records what was actually observed when an epic plan is approved end to end after phases `import_cycle`,
`core_kind`, `cwd`, `runner`, `launch`, `callers`, and `surfaces` landed. It is a hands-on record, not a test suite —
the durable regression coverage lives in the earlier phases' tests.

## How the runs were driven

Everything ran against an isolated SASE state root so no real project, bead store, or task store was touched:

- `SASE_HOME`, `XDG_CONFIG_HOME`, `XDG_STATE_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME` all redirected to a scratch tree.
- A scratch git project `verify` registered with a `WORKSPACE_DIR` project spec, so `resolve_epic_launch_cwd()` had a
  real primary checkout to resolve, and SDD storage adopted `local` (`<repo>/.sase/sdd`).
- Plan gates created through the real `create_plan_approval_gate()` with the same agent env vars a planner agent
  exports.
- Approvals applied through real, non-TUI code paths (see below). No `sase ace` process was running against the
  scratch state root when the first approval was applied.
- `sase` on `PATH` was a shim that imports the real CLI and replaces exactly one seam —
  `sase.bead.cli_work_handler.launch_bead_work_agents` — so no provider agents were actually spawned. Everything else
  in `sase bead work` ran for real: plan validation, SDD archive + commit, bead DAG creation, graph publication, the
  bead-state commit, planner-metadata backfill, and the completion notification. The shim can also sleep before the
  stubbed launch, which is how the long-running cases below were produced.

The only behavior therefore *not* exercised is the provider-agent spawn itself, which this epic does not touch.

## 1. No TUI — PASS

Gate created for `artifacts/epic_plan.md`, then approved through
`sase.integrations._mobile_notification_actions.execute_mobile_gate_action(prefix, ["approve"])` — the same executor the
Telegram/mobile inbound job uses — from a plain shell.

The gate response carried `epic_launch_task_id` and the transitional `epic_launch_owner: "host"`.

Observed:

| Claim | Result |
| --- | --- |
| A `detached` row appears in `sase task list` from a plain shell with no `--all` | yes — panel title `Tasks · global (detached + unattributed) (1)`, JSON scope `all: false` |
| `kind == "detached"`, `session_id is None`, `session_label is None` | yes; JSON also carries the additive `detached: true` |
| Command is the literal launch argv | `sase bead work /tmp/.../epic_plan.md --yes-to-all --artifacts-dir /tmp/.../artifacts` |
| It reaches `success` | yes — `exit_code: 0`, `message: "completed successfully"` |
| `sase task show <id>` shows the real launch output | yes — `✓ Validated`, `✓ Store`, `✓ Archived (committed)`, `✓ Epic bead`, `✓ Phase beads`, `✓ Dependencies`, `✓ Plan linked`, `✓ Graph committed`, `✓ Graph published`, wave summary, `Epic: verify-1` |
| The epic bead and its phase beads exist | yes — `verify-1`, `verify-1.1`, `verify-1.2` |
| `agent_meta.json` gained the host fields | yes — `epic_bead_id: verify-1`, `epic_started_at`, `plan_committed: true`, `sdd_plan_path` |
| The completion notification arrived | yes — sender `epic-launch`, tags `epic,launch`, `Epic verify-1 launched from epic_plan.md` |

Exactly one task row existed in the store afterwards.

`sase task show` also renders `Kind ◆ detached (global; no session owns this task)` and `Session —`, and the empty-store
panel hint mentions `sase task run --detached`.

### Defect 2 confirmed fixed at the source

The gate's `action_data` carried `project_dir: /tmp/.../repo` with **no** `CLAUDE_PROJECT_DIR` set anywhere — it was
resolved from `SASE_ACTIVE_PROJECT_DIR` through the runtime-neutral contract. `agent_project_file` was present too, so
either signal alone would have claimed the launch.

## 2. From the TUI — PASS (with one scope note)

A real Agents-tab keypress needs a live planner agent row, which the harness has no way to produce without launching a
provider agent. Instead the exact function the Agents tab calls was invoked:
`execute_plan_approval_response(..., "epic", epic_launch_mode="detached")`.

- Exactly **one** row was created, `kind == "detached"`. Across every run in this session, all six store rows were
  `detached`; no `tui`-kind row ever represented a launch. `_notification_epic_launch.py` no longer exists and
  `epic_launch_mode` no longer has a `foreground` member, so there is structurally one launch path.
- The Tasks tab shows the detached marker. The real `AceApp`, opened headless in a **fresh** session that had submitted
  nothing, rendered each row as `● ◆ detached Epic launch · <plan>` / `✓ ◆ detached …` / `⊘ ◆ detached …` in default
  scope.
- The top-bar indicator counts them. With two detached launches running, a brand-new TUI session reported
  `detached_running_count == 2` and the indicator rendered ` ⚙ 2 `.
- The planner agent launches nothing itself: the axe epic branch in `run_agent_exec_plan_accept.py` returns
  `"epic_approved"` unconditionally, and `_run_epic_launch_subprocess` / `_EpicLaunchResult` / `_EPIC_ID_LINE` are gone
  from the tree.

Scope note, not a defect: a real Agents-tab approval still wraps the *approval response* in a TUI-mirrored tracked task
(`_submit_tracked_task` in `submit_neutral_plan_response`). That is the pre-existing "Plan response: epic" row, not a
second launch — the plan's phase `callers` only removed the tracked-task *launch*.

## 3. Survives the TUI — PASS

Two epic approvals were made with a deliberately slow launch, then the headless TUI that observed them was closed.
Immediately after the TUI exited, both rows were still `running` with their `sase bead work` processes alive; both later
reached `success` with `exit_code: 0`. A later CLI read (and the earlier fresh-session TUI read) still showed the
finished rows in default scope.

## 4. Loud failure — PASS

A gate was built with neither `agent_project_file` nor `project_dir` in its action data (every provider `*_PROJECT_DIR`
env var and `SASE_AGENT_PROJECT_FILE` unset at gate creation). Approving it raised, through the neutral executor:

```
GateError: could not resolve the primary workspace for the approved epic;
resume with `sase bead work /tmp/.../epic_plan.md --yes-to-all`
```

surfacing to the caller as `MobileGateActionError` with the same message and code `epic_launch_failed`. No task row was
created and no in-agent fallback ran.

## 5. Kill path — PASS

A slow launch was killed with `sase task kill <prefix> --json`: `changed: true`, `status: "killed"`,
`message: "task killed"`, `exit_code: -15`. No `sase bead work` process survived. Re-killing the terminal row reported
`changed: false` and exited `0`, i.e. a no-op rather than an error.

## Bonus: concurrent-launch dedup — PASS

Two independent gates for the *same* plan path were approved back to back while the first launch was still running.
Both approvals returned the same `epic_launch_task_id` (`15dgdjgnwsfh`), and the store held one active detached row.

## Gap found

**Every epic-launch row records `origin: "api"`.** `submit_epic_launch_task()` accepts `origin` and defaults it to
`"api"`, but no caller threads one through: `prepare_epic_launch()` does not take an origin, and its three call sites
(`plan_approval_actions.py`, `_notification_modals.py`, `notification_gates/adapters.py`) do not pass one. The plan's
design section makes `origin` the field that records *where the work came from* now that a detached row has no session
(`ace`, `telegram`, `cli`, `axe`), and phase `launch` shows `origin=origin` with exactly that comment. Observed
`origin: "api"` for launches applied through the mobile/Telegram executor and through the TUI's own approval function
alike, so the surfaces cannot distinguish them today.

Everything else the plan asked this phase to prove held.
