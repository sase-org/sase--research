# Why the SASE fleet never makes it through a night: 2026-09-17 → 09-18 on apollo and athena

_Researcher B · written 2026-09-18 ~08:00 EDT. All times are EDT unless marked `Z`.
"Overnight" means 2026-09-17 18:00 → 2026-09-18 07:00._

## TL;DR

- **What ran.** athena started 157 agent shells overnight (42 of them monitors). apollo
  started 30 (4 monitors). Only two agent runs failed outright (03:10 and 06:18, both on
  athena). Five epic chains still stalled or needed you to step in by hand, and three
  older epics that stalled on earlier nights are still stuck.
- **Four failure mechanisms caused every stall.** Two of them are **silent**: the run is
  reported as a normal success, so nothing alerts you.
  1. **Completed, but the bead was left open (silent).** A phase agent finishes
     successfully, but one of its acceptance criteria depends on something it can't
     control (a PyPI release, or a host-wide gate that is red). It adds a
     `PROPOSED FOLLOW-UP` note, keeps the bead open, and exits green. The dependent
     phases then wait on that bead forever. `wait_checks` only raises an alert when the
     dependency _failed_, so nobody is told.
  2. **Lost monitor handoff (silent).** On athena, `sase monitor start` takes 23–68 s
     (apollo: 2.5–5 s). Codex hands control back to the model while that command is
     still starting. The skill tells the model not to wait, so it ends its turn. Codex
     then exits, killing the half-started command. No monitor is ever created, and the
     host reports the run as successful after a "declaration recovery" turn. The
     continuation was the step that would close the parent epic, and it silently
     disappears.
  3. **A loud failure with no recovery.** An agent passed `--model codex/gpt-5` to
     `sase monitor start`, copying an example from the `sase_monitor` skill doc. That
     model isn't allowed on the ChatGPT-account codex. The follow-up agent failed with a
     400 error at 03:10, and a "can never self-resolve" notification went out at 03:12.
     Nothing acted on it, and the epic is still stuck.
  4. **Landing recursion.** Land agents keep spawning child epics under themselves.
     Three new levels appeared in a single night on athena. Closing a child epic
     automatically closes a parent _phase_, but never a parent _epic_. That step is left
     to an LLM, running inside the same monitor handoff that mechanism 2 loses.
- **Things that made it worse:**
  - Host-wide gates are red: `just check-full` (sase-j0, +38), visual snapshots
    (sase-x5), and pyscripts lint (sase-12n).
  - athena is overloaded. Its runner slots are full, `check-full` takes 30–153 minutes
    and two 90-minute monitors timed out, and one phase ran 15 monitor→fix cycles.
  - sase updated itself six times on athena overnight while agents were running.
  - 29 epic beads are in progress even though every child is closed. Nobody will ever
    close them, and they bury the real stalls.
- **Recommended solution.** Make "is this epic still moving?" a deterministic,
  host-owned check instead of something an LLM reports.
  1. **No-silent-success.** If a run finishes and its assigned bead is still open,
     record it as `completed_blocked`, not success.
  2. **Handoff intent markers for `sase monitor start`.** Extend the existing sase-11t
     gate-intent guard so the runner replays or fails a handoff that never landed.
  3. **An epic-liveness watchdog job.** Every open bead in a launched epic must have a
     live owner. If it doesn't, the job relaunches or escalates once, loudly.
  4. **Small fixes.** Validate `--model` when a monitor starts, retry with the inherited
     model, fix the skill doc, and cap landing recursion.

  Section 7 walks through last night and shows each stall would have been caught within
  minutes, not by you at 3 AM.

## 1. Method and sources

- **Agent list and artifacts.** `sase agent list -a -j` on both hosts, plus every
  artifact directory under `~/.sase/projects/*/artifacts/ace-run/202609/{17,18}`. From
  each I read `agent_meta.json`, `done.json`, `workflow_state.json`, `error_report.md`,
  `tool_calls.jsonl`, and `live_reply_timestamps.jsonl`.
- **Notifications, monitors, updates.** `~/.sase/notifications/*.jsonl` on both hosts.
  `sase monitor list -a -j`. `~/.sase/logs/dev_update.jsonl`.
- **Beads.** `sase bead show` / `history` / `list`, and a read-only pass over the
  generated `issues.jsonl` projection to get chain statistics.
- **Chat transcripts** in `~/.sase/chats/202609/`, and the agent output logs in
  `~/.sase/workflows/202609/`.
- **Source code.**
  - `bd/land_epic` and `bd/work_phase_bead` in `src/sase/default_config.yml`
  - `src/sase/monitor/start.py`
  - `src/sase/llm_provider/gate_intent_guard.py`
  - `src/sase/llm_provider/_subprocess_codex.py`
  - `src/sase/scripts/sase_chop_wait_checks.py`
  - sase-core `crates/sase_core/src/bead/mutation.rs` (`close_one_and_delegated_parent`)
- **Prior research.** `research:202609/sase_11e_nested_landing_loop.md` (09-16) covers
  the landing-recursion problem. I build on it here rather than repeat it.

## 2. What happened, host by host

### 2.1 apollo (30 overnight shells; idle from about 23:53 to 03:07)

| Time        | Event                                                                                                                                                                                                                                                                                                                            |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 19:55       | `sase-zr.7.1.1.land` finds gaps and launches child epic `sase-zr.7.1.1.5` (3 phases). This is recursion level 3 below `sase-zr.7.1`.                                                                                                                                                                                             |
| 19:55–23:10 | Phases `.5.1`, `.5.2`, `.5.3` run one after another and all close.                                                                                                                                                                                                                                                               |
| 23:22       | `sase-zr.7.1.1.5.land` finds more gaps and launches `sase-zr.7.1.1.5.4` (2 phases), recursion level 4.                                                                                                                                                                                                                           |
| 23:53       | **`sase-zr.7.1.1.5.4.1` completes but deliberately leaves its bead open.** Its reason: "PyPI currently has no files for 0.34.50 … preventing a coherent pyproject.toml/uv.lock ratchet." It submits `bead_action: keep`. The notification says `completed`.                                                                      |
| 23:53–05:42 | `.4.2` and `.4.land` wait on the open bead. **No alert fires.** apollo sits idle.                                                                                                                                                                                                                                                |
| 03:07       | You approve two tale gates (`0a.f0.f0`, `0e.w0`) that had been waiting since 17:07 and 18:23.                                                                                                                                                                                                                                    |
| 05:42       | The epic is rerun with a standard `sase bead work` phase launch (`%id(1, clan=sase-zr.7.1.1.5.4, …)`), most likely by you. The new `.4.1` run hits the same blocker, but this time it **closes** the bead and records the blocker as an existing follow-up. The two runs applied different close criteria to identical evidence. |
| 06:13–07:43 | `.4.2`'s monitored `just check-full` **times out at its 90-minute budget**, and a follow-up launches.                                                                                                                                                                                                                            |

The top-level `sase-zr.7` epic has been stuck since 09-16. Its phases `.2`, `.3`, `.5`
and its land agent all wait on phase `sase-zr.7.1`, which turned into four levels of
nested epics (`7.1 → 7.1.1 → 7.1.1.5 → 7.1.1.5.4`).

Evidence: the transcript
`~/.sase/chats/202609/gh_sase_org__sase-ace_run-sase_zr_7_1_1_5_4_1-260917_232232.md`,
and the notes on bead `sase-zr.7.1.1.5.4.1` (#1 at 23:50, #3 at 05:51).

### 2.2 athena (157 overnight shells, 42 monitors)

| Time        | Event                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 17:45       | `sase-124.land` spawns child epic `sase-124.8`. A misleading "Epic launch outcome is unknown" alert fires, then the launch succeeds 26 s later.                                                                                                                                                                                                                                                                                                                                                                            |
| 19:40       | `sase-11y.2.1.land` spawns `sase-11y.2.1.5`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| 21:16       | `sase-123.land` spawns `sase-123.7`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| 22:36       | `sase-124.8.land` spawns `sase-124.8.4`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 23:26       | **Lost handoff #1.** `sase-11y.2.1.5.land` closes its own epic and starts auditing parent epic `sase-11y.2.1`. It runs `sase monitor start … -- just check-full` (ToolUse at 03:25:53Z). The model writes "Full verification is running under the required SASE monitor" at 03:26:17Z, 24 s after the call, and codex exits. **No monitor record exists.** The host runs a declaration-recovery turn and reports `completed` at 23:30. `sase-11y.2.1` and `sase-11y.2` stay open, which blocks `sase-11y.4` through `.10`. |
| 00:05       | `sase-123.7.land` → `sase-123.7.6`, again preceded by an "outcome is unknown" alert.                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| 01:15       | `sase-124.8.4.land` → `sase-124.8.4.3`. That is three nested levels created by the `sase-124` chain in one night.                                                                                                                                                                                                                                                                                                                                                                                                          |
| 01:38–03:08 | `sase-124.8.4.3.2`'s monitored `just check-full` **times out at 90 minutes**.                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| 03:10       | **Loud failure.** The follow-up `sase-124.8.4.3.2--1` launches with `%model:codex/gpt-5`. The starter had passed `--model 'codex/gpt-5'` to `sase monitor start`. The provider returns: `400 … The 'gpt-5' model is not supported when using Codex with a ChatGPT account`.                                                                                                                                                                                                                                                |
| 03:12       | `wait_checks` sends "Wait dependency can never self-resolve". Nothing acts on it. `sase-124.8.4.3`, `.8.4`, `.8`, and `sase-124` are still open. The `.land` waiter is no longer running and doesn't appear in `sase agent list`.                                                                                                                                                                                                                                                                                          |
| 03:16       | **You step in.** You launch `0mm`: "…close the sase-11y.2.1 epic bead and its parent sase-11y.2 bead." It closes them at 04:19, and `sase-11y.4`/`.5`/`.6`/`.7` start at 04:28–05:48.                                                                                                                                                                                                                                                                                                                                      |
| 03:19       | **Lost handoff #2.** `sase-11l.5.1.land--1` runs `sase monitor start` (ToolUse at 07:19:31Z). Codex logs `failed to record rollout items: thread … not found` at 07:19:50Z and exits. No monitor record exists, and the run is reported `completed` at 03:20.                                                                                                                                                                                                                                                              |
| 03:34       | `sase-123.7.6.5.land--1` does walk up the chain, closing `sase-123.7.6`, `sase-123.7`, and `sase-123`. So the ancestor-close step works when the LLM happens to do it.                                                                                                                                                                                                                                                                                                                                                     |
| 06:18       | **You step in again** and close `sase-11l.5.1` ("I'm pretty sure this epic's work is done at this point."). The `sase-11l.6` waiter, which had been waiting **41 h**, wakes and immediately fails: `NameCollisionError: agent name 'sase-11l.6' is already taken`. You relaunch the epic at 06:21.                                                                                                                                                                                                                         |

Also running on athena through the night:

- `sase-126.4` ran 15 monitor→fix cycles (20:15–06:22) of
  `just install && just fix && just check && just test-visual …`.
- `0mi` ran 8 cycles, 5 of them `check-full`, lasting 30–153 minutes each.

Epics that stalled on earlier nights and are **still silently stuck**:

| Epic         | Waiting since | Open phase     | Why the phase was left open                                                                        |
| ------------ | ------------- | -------------- | -------------------------------------------------------------------------------------------------- |
| `sase-11h`   | 09-15 19:36   | `sase-11h.4`   | The selection-health gate is red on 11 unrelated nodes.                                            |
| `sase-11i.6` | 09-16 00:38   | `sase-11i.6.4` | The TUI benchmark is over budget on the loaded host, and there are 602 visual-snapshot mismatches. |
| `sase-11o`   | 09-16 09:18   | `sase-11o.2`   | Agents-sync reconcile is blocked, and there is lock contention.                                    |

## 3. The four failure mechanisms, with root causes

### 3.1 Completed, but the bead was left open (silent stall)

- **What happens.** `bd/work_phase_bead` tells the worker to close its bead only when
  the work is done, and to record anything else as `PROPOSED FOLLOW-UP`. When a success
  criterion depends on something outside the agent's control, a conscientious agent
  leaves the bead `in_progress` and exits normally. Examples of such criteria:
  - a PyPI publication of `sase-core-rs`
  - a green `check-full` or `test-visual` on a host whose master is red
  - a latency benchmark on an overloaded host
- **Why it is silent.**
  - A run's result depends only on the provider run and the finalizer. Nothing checks
    whether the assigned bead is closed.
  - Dependents wait on the _bead_ (`%w(bead=…)`). The `wait_checks` terminal-blocker
    detector (`_identity_terminal_blocker` in `sase_chop_wait_checks.py`) only fires
    when the dependency's done marker shows a non-success outcome. A successful run that
    left its bead open never triggers it.
- **Why it isn't deterministic.** On identical evidence, the 23:22 run of
  `sase-zr.7.1.1.5.4.1` kept the bead open and the 05:42 rerun closed it. Close criteria
  are left to the model's judgement.
- **How common it is.** 1 new case overnight on apollo, plus 3 older epics on athena
  (above) that are still stalled 2–3 days later. Every example I found is an _acceptance
  or verification_ phase.

### 3.2 Lost monitor handoff (silent stall)

- **Designed behaviour.** `sase monitor start` detaches a supervisor. Once that
  supervisor acknowledges, the command kills the calling agent. The follow-up agent then
  continues the work.
- **The race on athena:**
  - **Monitor start is slow on athena.** Time from the `sase monitor start` ToolUse to
    the monitor member's artifact directory appearing: **23–68 s on athena**, measured
    on about 40 overnight starts. **apollo: 2.5–5 s.** athena has a 64-core CPU at load
    19–28 and about 10.5k artifact directories; apollo has a 16-core CPU at load about
    19 and about 440 directories. That points to archive-size-dependent work, not raw
    CPU. This is the same class of problem as sase-zu and sase-124.
  - **Codex doesn't wait for it.** Codex's exec tool hands control back to the model
    while the command is still running.
  - **The model ends its turn.** The `sase_monitor` skill says "Do not poll, sleep, or
    wait … after starting it", so the model writes a final message and ends the turn.
  - **Codex exit kills the command.** The in-flight `sase monitor start` dies before it
    creates the member or acknowledges the supervisor.
  - Timestamps for `sase-11y.2.1.5.land`: call at 03:25:53Z, final text at 03:26:17Z,
    codex done at about 03:26:21Z. On athena, a successful start creates its member
    about 25–30 s after the call.
- **Why the host misses it.**
  - sase-11t built exactly this protection for gates and sudo: `begin_gate_intent` plus
    `raise_if_gate_intent_lost`. `sase monitor start` doesn't use it. It only writes
    `.sase_monitor_pending` _after_ the supervisor acknowledges.
  - The codex turn-integrity check (`_CodexTurnIntegrityState.integrity_error`) only
    fires when the final agent message is **empty**. In both overnight losses the model
    had written a confident "handing off" message.
  - The host then runs a declaration-recovery turn, which is told not to do anything
    else, and records success.
- **How common it is.** 2 of about 40 overnight athena monitor starts. Both were land
  continuations whose job was to close a parent epic. Together they cost about 4 h and
  about 3 h of epic progress, and both needed you to intervene by hand.

### 3.3 Loud failure with no recovery

- **`sase-124.8.4.3.2--1`: invalid model.**
  - The `sase_monitor` skill's `--model` help lists `codex/gpt-5` as an example, and the
    agent copied it.
  - `sase monitor start` accepted it without checking. The failure only surfaced in the
    follow-up, after the starter was already dead.
  - A 400 error from a bad model name can't be fixed by retrying the same request. It
    _can_ be fixed by retrying with the starter's inherited model (`gpt-5.5@xhigh`). No
    such retry exists, and the 03:12 "never self-resolve" notification is passive.
- **`sase-11l.6`: name collision.** It failed with a `NameCollisionError` after waiting
  41 h. The same class of failure shows up in the notification history on 08-03 and
  08-14. A long wait makes a failure at wake time more likely, and nothing retries it.
- **Other failures in the week's notification history** (09-11 → 09-18):
  - `_WorkspaceBeadEvictionRefused` (about 12 across both hosts)
  - `stitch create` timeouts / not retried
  - a missing or stale finalizer declaration once the recovery budget was exhausted
  - "gate shell marked lost"
  - `%id bead association … does not match SASE_BEAD_ID`
  - `ImportError` / "wire schema mismatch" after self-updates
  - usage-credit exhaustion

  The failure _classes_ change every night. That is why fixing them one at a time never
  gets you to a clean night. You need a generic recovery layer.

### 3.4 Landing recursion and the missing plan→plan close

- **Growth.** Follow-up epics (a plan bead whose parent is a plan bead) have
  accelerated:

  | Month                   | Follow-up epics | Top-level plans |
  | ----------------------- | --------------- | --------------- |
  | 2026-07                 | 10              | 182             |
  | 2026-08                 | 39              | 185             |
  | 2026-09 (first 18 days) | 56              | 73              |

  Last night alone created 8 between 18:00 and 07:00 (9 counting `sase-124.8` at 17:45).
  The deepest chains are 6 levels (`sase-xe.16.11.7.14.6.7`), and several more are 5
  levels.

- **Why they grow.** Land agents run with `%auto`, so a child plan is approved about a
  second after it is proposed. The 09-16 research documents this.
- **The close gap.** `close_one_and_delegated_parent` in sase-core cascades a close from
  a plan to its parent only when that parent is a **phase**. When the parent is a
  **plan** (the epic that spawned the follow-up), it doesn't cascade. Closing that
  parent is left to the child land agent, via the `bd/land_epic` instruction "repeat
  through directly parented plan ancestors."
  - When the land agent does it, as `sase-123.7.6.5.land--1` did, it works.
  - When the landing continuation runs through a monitor handoff that is lost, the
    parent epic is never closed.
- **Zombie epics.** 29 plan beads are `in_progress` even though every child is closed. 6
  of them have a closed follow-up epic, and 23 had a land step that never finished. With
  154 beads in progress, the real stalls can't be seen.

## 4. Amplifiers (why _some_ failure happens every single night)

1. **Red global gates turn verification phases into coin flips.** `check-full` is red on
   master (sase-j0, +38). Visual snapshots have drifted (sase-x5). pyscripts lint is red
   (sase-12n, filed at 05:57). Every phase that must "pass `just check`/`check-full`"
   either loops (15 cycles for `sase-126.4`), leaves its bead open (3.1), or closes with
   caveats (apollo's 05:42 rerun).
2. **athena contention.**
   - All 8 runner slots were occupied this morning.
   - `check-full` takes 30–153 minutes, and two 90-minute budgets timed out
     (`sase-124.8.4.3.2`; apollo's `sase-zr.7.1.1.5.4.2`).
   - `sase monitor start` takes 23–68 s, which is what opens the window for the race in
     3.2.
   - Many agents run `check-full` at the same time. Under the two-speed-verification
     decision, that is supposed to be a landing gate, not a routine phase check.
3. **Self-hosting skew.**
   - sase runs as an editable install of the primary checkout. On athena it updated
     itself 6 times overnight (03:08, 03:43, 05:02, 05:55, 07:06, 07:12), including
     `sase-core-rs` 0.34.47 → 0.34.50 → 0.34.51.
   - apollo updated 4 times.
   - None of these caused a failure last night, but the week's history includes several
     that did: `cannot import name …` errors and
     `agent scan wire schema mismatch: got 9, expected 8`.
4. **Alert noise.**
   - "Epic launch outcome is unknown" fired 17 times since 09-11. Both of last night's
     were followed by a successful launch 16–26 s later.
   - `TaskTriage` notifications repeat (sase-10y is at +13).
   - The one alert that mattered, "can never self-resolve" at 03:12, arrived looking
     exactly like the noise, and there is no single "your epics are stuck" signal.

## 5. What already exists, and why it didn't help

| Mechanism                                                                      | What it covers                                                                   | Gap that bit last night                                                                    |
| ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `wait_checks` terminal-blocker notification                                    | Waiting on a dependency agent that **failed**                                    | Doesn't notice a _successful_ run that left its bead open. Only notifies; takes no action. |
| sase-11t gate-intent guard (`begin_gate_intent` / `raise_if_gate_intent_lost`) | Gate and sudo creation that dies mid-flight                                      | Not used by `sase monitor start`.                                                          |
| Codex turn-integrity check                                                     | A turn that ends with an **empty** final message and a killed or pending command | Misses a non-empty "I'm handing off" message with a pending handoff command.               |
| Declaration-recovery turn                                                      | Missing finalizer declaration                                                    | Turns a lost handoff into a clean success.                                                 |
| Delegated-parent cascade in sase-core                                          | Plan → parent **phase**                                                          | Doesn't cover plan → parent **plan**. Relies on the LLM's ancestor walk.                   |
| `sase bead work <epic>` rerun                                                  | Recovering an epic by hand                                                       | You have to notice the stall first, which is what happened at 03:16 and 06:21.             |

## 6. Recommended solution

**The idea.** Treat "the epic is still moving" as a host-owned invariant, the way
completion already is (decisions `host-owned-completion` and `gates-never-block`).
Agents may _claim_ progress, but the host checks it and recovers, deterministically,
without asking an LLM. Components are listed in priority order. P0 plus P1 would have
caught every stall last night.

### P0-a: No silent success (runner post-condition)

- **Check.** When a run that has an assigned phase or land bead ends `completed`, the
  runner re-reads that bead. It is a stall if all of these hold:
  - the bead is not closed,
  - no handoff is live for the family (monitor, gate, pipe, or an open plan or questions
    request),
  - and the bead is not explicitly marked blocked (see P2-b).
- **Response.** Record a new outcome, `completed_blocked`, not success. Raise **one**
  high-priority `EpicStalled` notification, sent through Telegram, with three actions:
  - **Relaunch phase**
  - **Close anyway** (a human override)
  - **Cancel phase**
- **Would have caught:** `sase-zr.7.1.1.5.4.1` at 23:53, and `sase-11h.4`,
  `sase-11i.6.4`, `sase-11o.2`.
- **Cost:** one bead read per run.

### P0-b: Handoff intent markers for `sase monitor start`

- **Write the intent first.** Make writing a `.sase_handoff_intent.monitor` file (with
  the full request argv) the **first** thing `sase monitor start` does, before heavy
  imports, the lane lock, and preflight. The monitor pending marker then consumes it.
- **The runner replays or fails.** After the provider exits, if an intent was never
  consumed and no monitor record matches it, the runner **replays the start itself**
  from the recorded argv. The runner is still alive and still holds the workspace claim.
  If the replay fails, the runner fails the run with a `HandoffLost` error, reusing the
  sase-11t guard machinery.
- **Tighten the codex integrity check.** A `sase monitor start`, `gate`, `pipe`,
  `plan propose`, `questions`, or `sudo` command still pending when the turn completes
  is a failure, whatever the final message says.
- **Change the `sase_monitor` skill wording.** "If the tool call yields while still
  running, keep polling that same session until it exits. Never end the turn while
  `sase monitor start` is in flight."
- **Would have caught:** both lost land continuations (23:26 and 03:19).

### P0-c: Fail fast on bad follow-up models and retry with the inherited model

- **Validate at start.** `sase monitor start --model` (and gate `--model` flags) should
  check the model against the provider's live catalog and account restrictions _while
  the starter is still alive_.
- **Retry with the inherited model.** When a follow-up fails at launch with a
  model-rejection or other non-retryable request error, relaunch it once with the
  starter's inherited route, and note that in the prompt.
- **Fix the skill doc.** Remove `codex/gpt-5` from the example list. Use `@small`, as
  the canonical invocation already does.
- **Would have caught:** `sase-124.8.4.3.2--1`, which would have continued at 03:08.

### P1: Epic-liveness watchdog (an AXE job, every ~10 min)

- **The invariant.** For every launched epic, every open descendant bead must have a
  **live owner**. A live owner is any of:
  - a running, queued, or waiting agent shell
  - a running monitor
  - a gate waiting on a human
  - an explicit `blocked` mark
- **What it does with an orphan**, following a fixed policy:
  1. **Failed phase, retryable cause:** relaunch once with `sase bead work <epic>`,
     which reassigns non-closed beads and never touches closed ones.
  2. **Plan bead with all children closed and no live land agent:** relaunch that plan's
     land agent. This closes the plan→plan gap in 3.4 deterministically. It also triages
     the 29 zombie epics: run it once in report-only mode, and let you bulk-close or
     relaunch.
  3. **Waiter process gone** (like `sase-124.8.4.3.land` today): relaunch the waiter.
  4. **Otherwise, or on a second orphaning:** escalate with `EpicStalled`, once per
     epic. Don't send one alert per waiter.
- **Where it lives.** The liveness computation takes a bead graph plus a snapshot of
  agent, monitor, and gate liveness, and returns an orphan list. The TUI, CLI, and
  Telegram all need the same answer, so per the rust-core-boundary rule it belongs in
  `sase-core`. The AXE job and a `sase bead liveness` command become thin adapters.
- **Morning digest.** The same data powers one daily summary: stalled epics, why each is
  stalled, and one-key fixes.

### P2: Stop generating stalls

- **P2-a: Cap landing recursion.** This implements the 09-16 research recommendation.
  - A land agent at nesting depth 2 or more cannot `%auto`-approve a child epic. That
    needs a human `EpicApproval`.
  - Items that depend only on a release or a global gate become typed task beads with
    `/sase_new_task`, not another nested epic.
  - Add a sanctioned "land-with-residuals" exit: close the epic, attach residual task
    beads, and leave the parent chain unblocked.
- **P2-b: Make "blocked on an external dependency" a first-class state.**
  - A lifecycle-owned command, for example
    `sase bead block <id> --on release|global-gate|human --reason …`. Agents don't
    hand-edit status, so this has to be a command.
  - It marks the phase blocked and raises a single triage gate right away. The watchdog
    counts it as owned by a human, not orphaned.
  - Change `bd/work_phase_bead` to say: "if the only unmet criterion is a release or a
    red global gate, run `sase bead block`, never just keep the bead open."
- **P2-c: Protect verification capacity.**
  - Allow at most 1–2 concurrent `check-full` runs per host, queued through the existing
    runner capacity weights.
  - Set `check-full` monitor timeouts from observed runtimes. On athena that means at
    least 3 h; 90 minutes timed out twice last night.
  - Keep `check-full` a land-only gate, per `two-speed-verification`.
- **P2-d: Freeze self-updates while epics are in flight.** `dev_update` should defer, or
  apply only at quiescent points, while any launched epic has live agents.
- **P2-e: Cut alert noise.** Suppress "Epic launch outcome is unknown" when a launch
  success arrives within 60 s. Route `EpicStalled` above `TaskTriage`.

### Bedtime checklist (no code needed)

1. `just check` is green on master. Fix or waive sase-12n, and park sase-j0 and sase-x5
   gates away from phase criteria.
2. `sase bead list --status in_progress` has no epic whose open beads lack a live agent.
   Until P1 ships, eyeball `sase agent list` for WAITING rows whose dependency is
   `DONE`.
3. No active phase has a criterion that needs a PyPI publication or a live cross-host
   drill.
4. Pause `dev_update` on athena.

### Recover right now

- `sase-124.8.4.3`: run `sase bead work sase-124.8.4.3`. Its land waiter is gone and
  `.2` failed.
- `sase-11h`, `sase-11i.6`, `sase-11o`: decide whether to override-close, block, or
  cancel `sase-11h.4`, `sase-11i.6.4`, and `sase-11o.2`.
- `sase-zr.7`: decide whether `sase-zr.7.1`'s four-level chain should be collapsed so
  `.2`, `.3`, `.5`, and the land agent can run.
- The 29 zombie epics listed in 3.4.

## 7. Counterfactual: last night with P0 + P1

| Incident                        | What happened                                          | With P0 + P1                                                                                                                                                         |
| ------------------------------- | ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sase-zr.7.1.1.5.4.1` (apollo)  | Silent 6 h stall; you reran it at 05:42                | `completed_blocked` plus `EpicStalled` at 23:53. With P2-b, `sase bead block --on release` gates you once. You pick "Close anyway" and `.4.2` starts at about 23:55. |
| `sase-11y.2.1.5.land` (athena)  | Lost handoff; parent open 4 h; you intervened at 03:16 | The runner replays the monitor start at about 23:27. The parent audit closes `sase-11y.2.1`/`.2`, and `sase-11y.4` starts about 3 h earlier.                         |
| `sase-11l.5.1.land--1` (athena) | Lost handoff; you closed it at 06:18                   | Same replay at about 03:20. The later `NameCollisionError` gets caught by the watchdog, which relaunches once, and doesn't wait for you at 06:21.                    |
| `sase-124.8.4.3.2--1` (athena)  | Invalid model; epic still stuck                        | `--model codex/gpt-5` is rejected at start, so the starter picks its inherited model. Or the launch retries with the inherited route at 03:10.                       |
| Zombie epics / older stalls     | Invisible                                              | The first watchdog pass lists all 29 plus the 3 stalled epics, each with one-key actions.                                                                            |

## 8. Proposed task beads

I didn't file these. Researcher A is working the same data in parallel, so the lead
should decide which to file and avoid duplicates.

- **bug:** `sase monitor start` handoff is lost when codex ends its turn mid-start. It
  needs an intent marker plus runner replay, and the codex integrity check must cover a
  non-empty final message with a pending handoff command.
- **bug:** `sase monitor start --model` accepts models the provider rejects, and the
  skill doc example `codex/gpt-5` is invalid on ChatGPT-account codex.
- **bug:** a successful run whose assigned bead is still open is reported as plain
  success, and `wait_checks` never flags bead waits on it.
- **bug:** closing a follow-up epic doesn't cascade to, or re-launch, its parent _plan_.
  This is the plan→plan case in `close_one_and_delegated_parent`.
- **feature:** the epic-liveness watchdog and a `sase bead liveness` report, in
  sase-core.
- **feature:** `sase bead block` as a lifecycle-owned blocked state with a single triage
  gate.
- **bug:** `sase monitor start` takes 23–68 s on athena vs 3 s on apollo, and the cost
  likely scales with archive size (related: sase-zu).
- **bug:** a waiter fails with `NameCollisionError` at wake after a long wait
  (`sase-11l.6`, 41 h).
