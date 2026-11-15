---
title: "Agent Hijack reliability: why `,k` never works, and how to make hijack dependable across turn kinds"
researcher: cld
date: 2026-11-15
host: apollo
inputs:
  - ~/tmp/screenshots/20261115_164112.png
  - plan:202611/agent_hijack.md (epic sase-1qz, closed 2026-11-07)
---

# Agent Hijack reliability — research report (cld)

## TL;DR

- **Hijack does not work on any agent today, not just the one in the screenshot.** I
  found five independent defects stacked on the same path. Any one of them is enough to
  block every hijack on apollo. Two of them were checked against live agents on apollo
  with read-only probes (the [appendix](#appendix-a--read-only-probes-used) has the
  scripts). The probes:
  1. ran the TUI predicate on every live row: **0 of 7** running named agents passed;
  2. ran the backend's target resolution and Rust eligibility on the same agents: **every
     one refused**, including two agents booted minutes earlier from v0.19.0+45, with
     `missing_capability: "launched before hijack support; use x"`.
- **No hijack has ever succeeded on apollo.** `~/.sase/agent_hijacks/` holds only a lock
  file, and `~/.sase/procs/procs.jsonl` has no `persist-hijack` proc. The only hijack
  entry in `tui_toasts.jsonl` is the refusal in your screenshot (21:41:08Z).
- **The tests passed because each one fakes the very input that is broken in
  production.**
  - The TUI tests build `Agent(agent_type=AgentType.RUNNING)` rows by hand.
  - The e2e test writes `agent_meta.json` itself, including `runner_capabilities` and the
    `agent_llm_provider` / `agent_model` / `agent_effort` keys. Real runs never write
    those three keys.
- **Your screenshot hit the hardest case.** Session `tailnet-t.10` was crossing a turn
  boundary: agent turn `--5` was in host completion and had just handed off to monitor
  `--mon-3`. Hijack v1 refuses both of those states by design.
- **My recommendation has three steps:**
  1. **Make v1 actually work.** A small, high-value fix plus a canary test that drives
     the real launch path, not hand-built inputs.
  2. **Make hijack an agent-level ("session-level") action with a durable latch.** If a
     turn can't be stopped safely right now, the hijack is recorded and applied at the
     next safe hand-off point. Every turn hand-off in a session already goes through the
     workspace-claim transfer, so the latch can live there.
  3. **Add a monitor adapter** (stop the command, suppress `--next`, hold the workspace,
     continue with instructions). A gate adapter comes later.
- **Do not start by adding more turn kinds.** Widening coverage before the basic path is
  proven would multiply the untested surface. The hijack subsystem is already about 11k
  lines of Python and has never completed one real hijack.

---

## 1. What the screenshot shows

| Evidence in the screenshot                                                                | Meaning                                                                                                                              |
| ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Selected row: `6 — ⚡ tailnet ▱7 (RUNNING) ×15 … ◆ tailnet-t.10` in the `@epic` clan      | The **session container row** for agent session `tailnet-t.10` (epic phase 10 of clan `tailnet-t`)                                  |
| JUMP roster: `10 --5 ▶`, `11 --mon-3 ▶`                                                   | Agent turn `--5` had just staged a monitor handoff, and monitor turn `--mon-3` was live                                              |
| Detail footer: `final running`                                                            | `--5`'s host-completion finalizer was still running                                                                                 |
| Toast: `Selected agent is not eligible for hijacking`                                     | Generic refusal text from `src/sase/ace/tui/actions/agents/_hijack_action.py:64`                                                    |

`sase monitor show tailnet-t.10--mon-3` confirms the timing. Starter `tailnet-t.10--5`
handed off to the monitor at about 16:40. The monitor ran
`/bin/bash /tmp/tailnet-t10-postcommit-acceptance.sh` for 1m45s and failed with exit 1.
Its follow-up, `tailnet-t.10--6`, booted at 16:43:43. You pressed `,k` at 16:41:08,
while the monitor was running.

## 2. Root cause: five stacked defects

These are listed in the order a `,k` press runs into them. Fixing only the first one
would just expose the next.

### D1 — The TUI predicate rejects every real agent row (this is what you hit)

`agent_can_offer_hijack()` (`src/sase/ace/tui/actions/agents/_hijack_action.py:23`)
requires `agent.agent_type is AgentType.RUNNING`.

- Every raw-prompt launch is wrapped as an anonymous single-step workflow, `tmp_<ts>`
  (`create_anonymous_workflow`, `src/sase/macro/models.py:374`).
- So every named live agent loads as `AgentType.WORKFLOW`.
- Probe 2 ran the real `load_all_agents()` on apollo. All 7 named running agents are
  `WORKFLOW`, and all 7 fail the predicate: `tailnet-t.10--6`, `tailnet-t.10--plan`, and
  the five `research.4u.*` agents.

The same predicate gates every entry point to hijack:

- the `,k` leader action;
- the `,k` hint in the leader footer (`_leader_mode.py` → `agent_hijack_ingress_available`);
- the kill modal's **h Hijack instead** option (`_kill_action_flow.py:160`).

So the hint and the modal choice never appear either. The predicate dates from the first
TUI commit (`81808e9ba0`), and its only test builds an `AgentType.RUNNING` row
(`tests/ace/tui/test_agent_hijack_action.py:20`).

### D2 — A session row resolves to the wrong member

The session container row's `Agent` object is the session's **first** member, not its
live one. In probe 1, the container row for `tailnet-t.10` is `tailnet-t.10--plan`:

- `WORKFLOW`, aggregated status `RUNNING`, `is_agent_session_container_row=True`;
- carrying `pid 3399892`, a process that no longer exists.

So with D1 fixed, `,k` on this row would submit a hijack for `tailnet-t.10--plan`, which
is done. The backend would then refuse with "already completed".

On the CLI side, `sase agent hijack tailnet-t.10` goes through `find_named_agent`, which
picked the **latest** member. In probe 3 that member was `--mon-3`. Two problems follow:

- `_stop_target.py:75` decides whether a member is a monitor from a *live row matched by
  exact name*. `--mon-3` resolved with `is_monitor_turn=False`.
- Whether a member is a gate turn comes from meta keys (`gate_turn`/`is_gate_turn`,
  line 78).
- `_check_eligibility` also hard-codes `is_llm_agent: True`, `is_named_proc: False`, and
  `is_clan_container: False` (`_stop_orchestrator.py:304-310`).

As a result, a session name can resolve to a monitor or gate member that the backend
then treats as an LLM agent turn.

### D3 — The hijack capability stamp is erased on every run, so the backend refuses everything

The design depends on a capability stamp: `"runner_capabilities": ["hijack"]` in
`agent_meta.json`. It prevents hijacking runners whose SIGTERM handler would release the
workspace claim anyway.

1. Bootstrap writes the stamp correctly (`src/sase/axe/run_agent_runner_bootstrap.py:150-160`).
2. Moments later, directive extraction rebuilds `agent_meta.json`
   (`run_agent_directives_extract.py:65` → `run_agent_directive_metadata_build.py`).
3. That rebuild keeps only the keys on the allow-list in `preserved_agent_metadata()`
   (`run_agent_directive_metadata_preserved.py:31`).
4. `runner_capabilities` is not on that list, so it is dropped.

Evidence:

- Neither `research.4u.cld` (this run) nor `tailnet-t.10--6` has the key in its
  `agent_meta.json`.
- Both do have the other keys written by the same bootstrap function: `prompt_origin`
  (it is on the allow-list) and `launch_scratch_key`.
- `launch_scratch_key` survives because `run_agent_markers.write_agent_meta` (around line
  266) re-adds it whenever a runner rewrites its own meta. That is a fix for the same
  class of bug, applied to a different key.

Result: Rust eligibility refuses every agent with `missing_capability` (probe 3).

### D4 — Model facts are read from keys runners never write, so recovery would fail after a successful stop

`_stop_target.py` reads these keys:

- `provider` from `agent_llm_provider` / `provider` (line 86);
- `effort` from `agent_effort` / `effort` (line 88).

Real runners write `llm_provider`, `exec_llm_provider`, and `reasoning_effort`, as the
meta dump for `tailnet-t.10--6` shows. Here is what would happen with D1–D3 fixed:

1. The hijack record stores `provider=None` and `effort=None`.
2. `predecessor_concrete_target()` (`recover_common.py:121`) therefore produces a bare
   `"gpt-6-luna"`.
3. Rust `require_concrete_target` (`sase-core …/agent_hijack/execution.rs:786`) rejects
   that with "expected concrete provider/model".

So the stop would succeed and leave the workspace held, but **Continue and Escalate, the
main keep-work actions, would fail**. Restart and Dismiss would still work.

### D5 — The refusal reason is hidden, and the TUI and backend use different rules

The original plan says `,k` should toast the refusal reason when an agent is ineligible
(`plan:202611/agent_hijack.md`, "Way in"). Instead:

- the TUI toasts a fixed, generic string;
- the TUI never calls the Rust `agent_hijack_eligibility` at all, and keeps its own
  narrower rules.

There are therefore two eligibility rule sets that can drift apart, and they already
have. The user never learns which rule fired.

### D6 — The screenshot's states are refused by design

Rust eligibility (`eligibility.rs:30`) refuses these, in order:

- finalizer phases `declaring | executing | finalizing`;
- monitor turns, gate turns, named procs, home mode, remote rows, clan containers, and
  bulk-marked rows.

At 16:41 the `tailnet-t.10` session had nothing hijack v1 could act on: `--5` was
finalizing, and `--mon-3` was a monitor.

### Why the tests missed all of this

| Seam that is broken in production                      | How the test covers it                                                                            |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| Row type and session row → TUI predicate               | Builds an `AgentType.RUNNING` row by hand                                                         |
| Bootstrap meta → directive rebuild → capability        | `test_runner_launch_scratch_key_meta.py` checks the stamp only after bootstrap                     |
| Runner meta keys → hijack record model facts           | The e2e test hand-writes `agent_llm_provider` / `agent_model` / `agent_effort` / `runner_capabilities` |
| Live session in mid-transition                         | Not covered                                                                                       |

No test runs the chain end to end: **real launch pipeline → real loader → predicate → stop
→ recover**. That missing canary is the single most important fix after D1–D4.

---

## 3. Critique of the request

> "Agent hijacks should work on as many types of sase turns (in as many states) as
> possible … make agent hijacks much more resilient / dependable."

**The direction is right. I would change the order and how the goal is framed.**

1. **The first problem is not coverage; it is that the basic path is broken.** Adding
   monitor and gate hijack to a pipeline that has never completed one real hijack would
   multiply untested surface. The first deliverable should be "`,k` on an ordinary
   running agent turn works, and Continue succeeds", guarded by a canary that cannot be
   faked.

2. **The unit of hijack should be the agent (session), not a turn row.** When you press
   `,k`, you mean "take the wheel of this agent". You do not mean "kill the process
   behind this row". The screenshot shows why the row-level model fails: you selected the
   session, and the live member changed underneath you three times in about four minutes
   (`--5` → `--mon-3` → `--6`). The backend should resolve the live member at the moment
   it executes. It should then pick a stop method for that turn kind, so that every
   hijack ends the same way: the session is parked, the workspace is held, and the
   recovery panel opens.

3. **"Works in as many states as possible" should not mean "can kill at any instant".**
   Some states should never be interrupted halfway:
   - a host-completion finalizer committing or pushing;
   - a staged handoff being adopted;
   - a gate running the commands for the option you selected.
   Interrupting these could leave a half-landed commit or an orphaned successor. The way
   to reach "as many states as possible" safely is a **durable latch**: accept the
   hijack, show `⏏ HIJACK PENDING`, and apply it at the next safe hand-off point. Users
   then see one dependable behavior instead of a sequence of race-window refusals.

4. **Some states should hand off to another operation, not be hijacked.** Hijack means
   "stop, but keep the workspace and evidence". Where there is nothing to keep, a
   different operation fits better:

   | State                                  | Better operation        |
   | -------------------------------------- | ----------------------- |
   | Queued agent with no workspace claim   | `,x` kill & edit        |
   | Finished agent                         | `F` fork or `R` retry   |
   | Named proc                             | Stop the proc           |
   | Clan container                         | Pick a member           |

   Each of these should be an explicit redirect with a clear message, not a generic
   refusal.

5. **A note on scale.** The v1 subsystem is about 11.3k Python lines under
   `src/sase/agent/hijack/`, plus Rust and TUI code. It has rich exactly-once recovery
   transactions, and zero successful real-world uses. I would not rewrite it now; the
   design is sound and most of the defects are integration glue. I would freeze its scope
   until the canary and real use show it is worth extending.

### Adjusted requirements (my changes are flagged)

| #   | Requirement                                                                                                                                                                                                       | Status vs. the request                                         |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| R1  | `,k` on an ordinary running agent turn launched today hijacks it, and **Continue** succeeds. A canary test that drives a real runner launch (fakey provider, no hand-written meta) guards this.                    | **NEW, P0**                                                    |
| R2  | Hijack targets the **agent/session**. The backend resolves the live member when the hijack executes, atomically with respect to turn hand-offs.                                                                   | **CHANGED** (from row-level)                                   |
| R3  | Every (turn kind × state) pair has exactly one defined decision: `immediate`, `latched` (deferred to the next safe point), `redirect` (another operation), or `refused` with a specific reason. Generic refusals are not allowed. | **CHANGED** (replaces "as many states as possible")            |
| R4  | **One source of truth for eligibility.** Rust decides. The TUI calls the same function, with facts gathered by the same Python code the backend uses, both to show the `,k` hint and to word its messages.         | **NEW**                                                        |
| R5  | `sase agent hijack --explain NAME` prints, read-only, the resolved member, the facts, and the decision.                                                                                                            | **NEW** (would have caught D1–D4 in a minute)                  |
| R6  | Monitor turns are hijackable (stop the command, suppress `--next`, hold the workspace, continue with instructions).                                                                                               | Kept from the request, phase 3                                 |
| R7  | Gate turns are hijackable (cancel the decision, hold the workspace, continue).                                                                                                                                    | **DEFERRED.** A gate already waits for a human, so this adds the least value |
| R8  | Remote rows hijack through the fleet gateway; home-mode turns become hijackable.                                                                                                                                 | **DEFERRED / out of scope.** Keep the copy-command and reason   |
| R9  | Never resume a killed provider process, and never interrupt a finalizer while it is applying effects.                                                                                                              | Kept non-goal, now explicit                                    |

---

## 4. Approaches considered

| Option                                                         | What it is                                                                                         | Pros                                                                                                                               | Cons                                                                                                                                                                                                                | Verdict                         |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| **A. Patch v1 only**                                           | Fix D1–D5 and add the canary                                                                       | Small; makes hijack real for running agent turns                                                                                   | The screenshot case is still refused, though now with an accurate reason. Hand-off moments stay racy.                                                                                                             | Necessary, not sufficient       |
| **B. Add per-kind immediate stops**                            | Add monitor and gate stop paths to v1 without a latch                                              | Covers more kinds                                                                                                                  | A session's hand-offs are a series of short windows (finalize → stage → adopt → claim transfer → admit). Each would need its own special case, and `,k` would still land in a refused window.                     | Not recommended alone           |
| **C. Agent-level hijack with a durable latch + per-kind adapters** | Resolve the live member, stop it now when that is safe, otherwise latch and apply at the next hand-off point | One mechanism covers every hand-off state. Atomicity comes from an existing lock (see §6.2). The UX is the same everywhere.     | Needs a Rust wire change (v2 eligibility) and checkpoints at the hand-off points                                                                                                                                    | **Recommended** (after A)       |
| **D. Replace hijack with "kill with hold + fork"**             | Delete most of the v1 recovery machinery; reuse the held-workspace and readopt machinery           | Much less code                                                                                                                     | Rewrites an epic that closed 8 days ago; loses exactly-once escalate and continue; churn                                                                                                                            | Not now; revisit if v1 stays unused |

---

## 5. Proposed behavior for every state (R3)

`immediate` = stop now. `latched` = record the hijack and apply it at the next safe hand-off
point. `redirect` = hand the user to another operation, with a message.

| What is live in the selected agent                                                           | Decision                            | Mechanism                                                                                                                                                                                                                                     |
| -------------------------------------------------------------------------------------------- | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Agent turn `STARTING` / `RUNNING` / `RETRYING` (provider running)                            | immediate                           | Existing v1 stop orchestrator (after the D1–D5 fixes)                                                                                                                                                                                         |
| Agent turn booting or waiting for a runner slot, while the session holds the workspace        | immediate                           | Stop the runner and hold the claim. There is no transcript, so Continue relaunches the stored prompt plus your instructions.                                                                                                                 |
| Agent turn finalizing (`declaring` / `executing` / `finalizing`)                             | **latched**                         | The finalizer finishes, so commits land. The runner then settles as `hijacked` instead of adopting its staged handoff. The staged handoff is kept as evidence and is visible in the recovery panel.                                          |
| Between turns: handoff staged, not yet adopted                                               | **latched**                         | The host adopter sees the latch at the claim-transfer point and launches nothing. The session settles as held.                                                                                                                                |
| Monitor turn running *(the screenshot)*                                                       | immediate (monitor adapter)         | `stop_monitor()`, suppress `--next`, record `hijacked`, hold the workspace. Recovery **Continue** launches the recorded follow-up now, with the partial output and optional instructions (similar to `sase monitor resume`, but allowed for hijacked monitors). |
| Monitor staged, supervisor not started                                                        | latched                             | Applied when the monitor would be adopted                                                                                                                                                                                                     |
| Monitor settled, follow-up admitted or starting                                               | immediate on the follow-up, or latched at admission | The follow-up is an ordinary agent turn                                                                                                                                                                                                       |
| Gate turn waiting for a human                                                                 | immediate (gate adapter, deferred to R7) | Settle the gate with a `hijacked` response that runs no option commands, then hold the workspace                                                                                                                                              |
| Gate turn running the selected option's commands                                              | latched                             | Applied after the commands settle, before the follow-up launches                                                                                                                                                                              |
| Session member waiting on `%wait` while the session holds the workspace                       | immediate                           | Cancel the waiting member and hold the workspace                                                                                                                                                                                              |
| Stand-alone `WAITING` / `QUEUED` with no claim                                                | redirect                            | "Nothing to keep. Use `,x` kill & edit."                                                                                                                                                                                                      |
| Already `HIJACKED`                                                                            | redirect                            | Open the recovery panel                                                                                                                                                                                                                       |
| Terminal (DONE, FAILED, …)                                                                    | redirect                            | Fork (`F`) or retry (`R`)                                                                                                                                                                                                                     |
| Named proc                                                                                    | redirect                            | Stop the proc                                                                                                                                                                                                                                 |
| Clan container                                                                                | redirect                            | Pick the running member; auto-select it if there is exactly one                                                                                                                                                                               |
| Step of a multi-step named workflow                                                           | refused (for now), with reason      | Hand-off semantics for workflow steps need their own design                                                                                                                                                                                   |
| Home mode                                                                                     | refused (for now), with reason      | R8                                                                                                                                                                                                                                            |
| Remote row                                                                                    | redirect                            | Copy the command, as today (later: gateway, R8)                                                                                                                                                                                               |

---

## 6. Recommended solution

### Phase 1 — Make v1 real (sase only; no wire change; one medium phase)

1. **Keep the capability stamp (D3).**
   - Add `runner_capabilities` to `preserved_agent_metadata()`.
   - Also re-stamp it in `run_agent_markers.write_agent_meta` for writes the runner makes
     about itself (`pid == os.getpid()`), the same way `launch_scratch_key` is re-added.
   - Better still, define one `RUNNER_BOOT_META_KEYS` tuple shared by the bootstrap
     writer and the preserver. Add an invariant test: every key that
     `_write_bootstrap_agent_meta` writes must survive
     `extract_directives_and_write_meta`. This removes the bug class, not just this
     instance.
   - *Optional fallback for agents already running:* infer the capability from
     `code_identity`. Treat a runner as capable when its host root's commit contains
     `01a28287c8`, or when its version is ≥ 0.19.0 and the checkout isn't available.
     Otherwise, agents running today only become hijackable as they turn over.
2. **Fix the model-fact keys (D4).** Read `llm_provider` / `exec_llm_provider` and
   `reasoning_effort`. Add a test fed by an `agent_meta.json` fixture captured from a
   real runner, not written by hand.
3. **Resolve the live member (D2).**
   - The TUI resolves a session container row to its live member, and sends the session
     name when no member is live.
   - The CLI and backend, given a session name, pick the member from the session roster's
     **active** member, not `find_named_agent`'s latest.
   - Classify a member as monitor, gate, or proc from durable records (monitor marker,
     gate record, proc row), never from whether a live row exists.
   - Stop hard-coding `is_llm_agent`, `is_named_proc`, and `is_clan_container`.
4. **One eligibility authority (D1, D5).** Replace `agent_can_offer_hijack` with a facts
   builder shared with `_stop_target` that calls Rust `agent_hijack_eligibility`.
   - Accept `WORKFLOW` rows that are anonymous or `appears_as_agent`.
   - Show the decision's `message` in the toast and in the footer hint, for example
     `,k hijack (monitor: not yet)`.
   - Log refusal codes to `tui_toasts.jsonl` so they can be measured.
5. **`sase agent hijack --explain NAME`** (read-only). Probe 3 in the appendix is
   essentially this command.
6. **Canary test (R1).** The fakey real-runner test should:
   - launch through the normal pipeline (anonymous workflow, real bootstrap, real
     directive extraction);
   - wait for `RUNNING`;
   - check that the real TUI loader row passes the predicate;
   - call the hijack path the TUI uses (`submit_agent_hijack` core);
   - assert `HIJACKED` with the workspace held;
   - run **Continue**;
   - assert the successor runs in the same workspace and settles.

   Add a parity test: for rows loaded from the canary's artifacts, the TUI decision must
   equal the backend decision.

### Phase 2 — Agent-level hijack with a durable latch (sase-core + sase; large)

**The key design point is where the latch lives.** Every in-session hand-off I traced
goes through a **workspace-claim transfer or hold** under the RUNNING-field claim lock:

- monitor start and host completion (`src/sase/monitor/start_claim.py`,
  `host_completion_complete.py`, `host_completion_settle.py`);
- gate follow-ups (`src/sase/gate_turn/followup.py`);
- turn follow-ups (`src/sase/turns/followup_launch.py`);
- successor delivery and retries (`src/sase/axe/run_agent_successor_delivery.py`,
  `run_agent_retry_spawn.py`);
- launch-spawn `transfer_from_pid`.

Put the latch **on the claim** (`hijack_latch: {hijack_id, requested_at}`) and give
`transfer_workspace_claim` a rule: a latched claim is pinned and transfers to nobody.

That makes latch application atomic for every kind of hand-off with no extra lock. The
first transition attempt that observes the latch applies it, through a compare-and-swap
on the ledger record, so it is applied exactly once. I recommend verifying the "every
hand-off goes through claim transfer" assumption early in phase 2, for example by
grepping for adoption paths that launch a successor without a claim operation.

- **Rust (`sase_core::agent_hijack`)**:
  - Eligibility wire v2:
    - facts add `turn_kind` (`agent|monitor|gate|proc`), `turn_phase` (`booting`,
      `provider_running`, `finalizing`, `staged_handoff`, `awaiting_human`,
      `executing_options`, `admission_wait`), and `holds_workspace`;
    - the decision adds `mode` (`immediate|latched|redirect|refused`) and `redirect_op`.
  - Ledger record adds `scope` (`turn|session`), `latched_at`, `applied_at`,
    `applied_boundary`, and `stopped_turn_kind`, plus a `latched → stopping → held`
    transition.
  - Bump the wire versions and update the Python mirror constants as sase-core's
    `AGENTS.md` describes.
- **Python checkpoints** where the latch is applied:
  - runner after finalization, before adoption;
  - the staged adopters (`run_agent_exec_staged_adopters.py`, `…_staged_monitor.py`,
    `…_staged_gate.py`);
  - monitor supervisor launching its follow-up;
  - gate follow-up launch;
  - runner-slot admission for session successors.
- **The latch must never wait on a dead process.** The hijack operation itself should:
  1. write the latch;
  2. stop the live member right away if it is stoppable;
  3. otherwise wait, with a bound, for a checkpoint to apply the latch;
  4. if the process that owns the hand-off is dead or stuck, apply the latch itself
     (reconcile).

  Incidental evidence that stuck hand-offs happen: monitor `bob-cli-gh.1--mon` has sat in
  `staged` since 2026-11-03.
- **TUI.** Show a `⏏ HIJACK PENDING · after finalizer` overlay. Pressing `,k` again
  cancels the latch. A latch that becomes moot (the session ends cleanly first) settles
  as `moot` with a toast.

### Phase 3 — Monitor adapter (medium)

Hijacking a monitor fills a real gap. Today, `x` on a monitor stops it, no follow-up
runs, and the session is stuck: stopped monitors can only be inspected or dismissed. The
adapter would:

1. stop the monitor through `stop_monitor`;
2. mark its settlement `hijacked`, so it is no longer `stopped`;
3. suppress `--next` and hold the workspace;
4. offer recovery actions:

| Action      | Result                                                                                                                                             |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Continue    | Launch the recorded follow-up now, at its recorded model, injecting the partial output (labeled untrusted, as monitor forks do) and your instructions |
| Escalate    | The same, at a larger model                                                                                                                        |
| Re-run      | Restart the monitor command                                                                                                                        |
| Dismiss     | Dismiss after a verified recovery snapshot                                                                                                         |

### Phase 4 — Hardening (small)

- **`sase doctor` check:** "N running agents lack the hijack capability."
- **Boundary chaos test.** Run a scripted fakey session `agent → sleep-monitor → agent`
  and fire hijack at each checkpoint. Every attempt must end `HIJACKED` or `latched`;
  `refused` is a failure.
- **Gate adapter (R7)**, only if real use shows demand.

### Sequencing and sizing

1. **Phase 1** is the fix for your report. It is small enough for one medium epic phase
   or two small ones. It makes `,k` work for ordinary running agent turns, and it gives
   precise reasons for everything else, including the screenshot's monitor state.
2. **Phase 2** turns those reasons into successes at hand-off points.
3. **Phase 3** covers the screenshot case directly.

Ship phase 1 on its own. Real use will show whether phases 2 and 3 are worth their cost.

### Risks and open questions

- **Inferring the capability from `code_identity`.** An editable checkout at a commit
  before the hijack feature could report version `0.19.0`. Prefer the commit-ancestry
  check, and fall back to the version only when the checkout is missing.
- **Finalizing → latched trade-off.** If a finalizer hangs, for example on a push, the
  latch waits too. Bound the wait, and after a timeout give the user an explicit
  "hijack now (finalizer interrupted, see snapshot)" option, with a warning.
- **Workflow steps of non-anonymous, multi-step workflows.** Hand-off semantics for these
  need their own design, so they stay refused with a reason for now.
- **Exactly-once across Phase 2's new checkpoints.** Every checkpoint must go through the
  same ledger CAS. The chaos test in phase 4 exists to prove this.

---

## Appendix A — Read-only probes used

Probes 1–3 ran with the installed sase interpreter
(`~/.local/share/uv/tools/sase/bin/python3`) from a scratch directory. Probe 4's metadata
dump ran with the system `python3 -I`. **None of them signalled or mutated anything.**

- **Probe 1 — `load_all_agents()` on `tailnet-t.10` rows.**
  - The container row is `'tailnet-t.10--plan' WORKFLOW RUNNING pid 3399892 ws 10 cont True offer False`.
  - Every member, including `'tailnet-t.10--6' WORKFLOW RUNNING pid 2295354`, has
    `offer False`.
  - The monitors `--mon…--mon-3` are `AgentType.RUNNING` with `is_monitor=True` and
    `pid None`.
- **Probe 2 — every live `RUNNING` / `STARTING` / `RETRYING` row:** all named agents are
  `WORKFLOW` with `tmp_*` workflows, and all have `offer False`.
- **Probe 3 — `resolve_target` + `_check_eligibility`** (the same calls the orchestrator
  makes before it signals anything). `tailnet-t.10--6`, `tailnet-t.10`,
  `tailnet-t.10--mon-3`, `tailnet-t.10--5`, `research.4u.cld`, and `tailnet-t.land` all
  return `eligible:false, code:missing_capability`. `tailnet-t.10` resolved to the
  `--mon-3` artifacts with `is_monitor_turn=False`.
- **Probe 4 — `agent_meta.json`** of `tailnet-t.10--6` and `research.4u.cld`:
  - `runner_capabilities` is absent from both;
  - `tailnet-t.10--6` has `llm_provider="codex"`, `reasoning_effort="xhigh"`,
    `model_alias_trail=["medium"]`, and `code_identity.roots[sase].commit=9793a95a5c…`
    (version 0.19.0);
  - neither has `agent_llm_provider` or `agent_effort`.

## Appendix B — Key code references

| Concern                                                         | Location                                                                                       |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| TUI predicate and generic toast                                 | `src/sase/ace/tui/actions/agents/_hijack_action.py:12-36`, `:64`                               |
| Kill-modal hijack choice uses the same predicate                | `src/sase/ace/tui/actions/agents/_kill_action_flow.py:158-171`                                 |
| Anonymous `tmp_*` workflow wrapping                             | `src/sase/macro/models.py:374`                                                                 |
| Capability stamp written                                        | `src/sase/axe/run_agent_runner_bootstrap.py:150-160`                                           |
| Capability dropped (allow-list)                                 | `src/sase/axe/run_agent_directive_metadata_preserved.py:31-173`                                |
| Earlier fix for the same bug class (`launch_scratch_key`)       | `src/sase/axe/run_agent_markers.py:262-278`                                                    |
| Target resolution: monitor and gate classification, mis-keyed model facts | `src/sase/agent/hijack/_stop_target.py:75-88`                                         |
| Hard-coded eligibility facts                                    | `src/sase/agent/hijack/_stop_orchestrator.py:298-318`                                          |
| Rust eligibility order                                          | `sase-core crates/sase_core/src/agent_hijack/eligibility.rs`                                   |
| Rust concrete-target validation                                 | `sase-core crates/sase_core/src/agent_hijack/execution.rs:786-808`                             |
| Seeded e2e metadata                                             | `tests/fakey/test_agent_hijack_e2e.py:203-210`                                                 |
| Monitor stop (no follow-up)                                     | `src/sase/monitor/store.py:52`                                                                 |
| Claim-transfer hand-off points (latch home)                     | `src/sase/monitor/start_claim.py`, `src/sase/gate_turn/followup.py`, `src/sase/turns/followup_launch.py`, `src/sase/axe/run_agent_successor_delivery.py` |
