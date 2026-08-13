---
create_time: 2026-08-13
updated_time: 2026-08-13
status: research
---

# Improving `sase monitor`: The Supervisor Is The Weak Link

**Question.** The `sase-kp` epic is mid-flight — 8 of 12 phases closed, `tui-detail`,
`epic-launch`, `memory-docs`, and `smoke` still open. What should be improved before the
epic lands, and what is worth building after it?

**Method.** Read every module in `src/sase/monitor/`, the CLI trio
(`parser_monitor.py` / `monitor_handler.py` / `monitor_render.py`), the runner adoption
path (`run_agent_exec_monitor.py`), the TUI integration points, and the plan
(`plans:202608/sase_monitor.md`). Compared the implementation against the sibling
supervision primitive that already exists in this repo (`src/sase/tasks/`). Three
findings were confirmed by executing the real code against real subprocesses rather than
by reading; the reproductions are inline below.

**Verified against** `sase@22319c52d` (master, clean tree), 2026-08-13.

**Companion report.** `202608/sase_monitor_improvements.md` was researched independently
against the same snapshot and reaches compatible conclusions from a different angle
(durability, control surfaces, and agent handoff). Read both; where they overlap, the
reproductions below are the empirical half.

## Executive Summary

**The design is right and the plumbing is right. The command supervisor is where the
value leaks.** Modeling a monitor as an ordinary agent-family member was the correct
call and it paid off exactly as the plan predicted: the artifact scanner, family roster,
runtime aggregation, chat history, workspace claims, and `#fork` handoff all work on
monitors with almost no monitor-specific code. `store.py` is 289 lines and there is no
new store at all. That part of the epic should be considered done and good.

The problem is concentrated in one function. `supervise._stream_output()` drives *both*
output streaming *and* timeout enforcement from a blocking, line-oriented
`readline()` loop. That single choice produces three independent failures, all
reproduced against the shipped code:

| Command shape | What happens | Verified |
| --- | --- | --- |
| Emits output continuously | **Timeout never fires.** Ran 12s into a 2s budget, still streaming. | ✅ |
| Emits a partial line (`\r` progress bars) | **Supervisor blocks for the whole partial line.** 8s into a 2s budget, `timed_out=False`, and nothing reached `live_reply.md` until the line completed — so "live output" is not live. | ✅ |
| Backgrounds a grandchild that inherits stdout | **Monitor stays `running` after the command exits.** Parent exited at t≈0; the supervisor blocked 10s on the orphan's pipe, 3s budget never fired. | ✅ |

The fix is not a patch to the loop — it is to delete the loop. `sase.tasks.supervisor`
already solves this correctly by handing the child's stdout **directly to the log file
descriptor** (`stdout=output`) and polling `child.poll()` on a 50 ms tick. No reader
thread, no partial-line stall, no timeout starvation, and materially less code. The
monitor supervisor should adopt that shape.

Three further gaps compound it. Monitors persist the supervisor pid but **never persist
the monitored command's pgid** — tasks do (`tasks/models.py:45`). So when a supervisor
dies hard, nothing on the system can kill the command tree it left behind, and the lane
wedges: `active_monitor_for_lane()` keeps returning a `running` monitor that no longer
exists, so every subsequent `sase monitor start` in that lane fails until a human runs
`sase monitor stop`. Separately, the monitored command **inherits the starter agent's
`SASE_AGENT` / `SASE_AGENT_NAME` / `SASE_ARTIFACTS_DIR`**, which every other
subprocess boundary in this repo scrubs (`chop_script_runner.py:26`,
`axe/_process_start.py:58`). And `live_reply.md` is **uncapped on disk** — the 2 MiB
budget applies only to the in-memory retained view, so the plan's stated goal
("unbounded capture of a chatty command must not fill the artifacts store") is not
actually enforced.

Finally, one small thing that is invisible in tests and very visible in use: inside an
agent, **`sase monitor start` prints nothing at all**. `kill_agent_runner_group()` is
`NoReturn`, so every line after `maybe_handoff_monitor_from_agent()` in
`monitor_handler.py:236` is unreachable — including `-j/--json`.

---

## Part 1 — What Actually Shipped

The lifecycle is worth stating plainly because most of it is correct and should not be
disturbed.

```
agent runs `sase monitor start`
  └─ start_monitor()                       src/sase/monitor/start.py:68
       ├─ resolve lane, reject duplicates, promote single agent → family
       ├─ create_monitor_member()          member.py:16      ← artifacts dir + monitor_* meta
       ├─ Popen(sase monitor _supervise)   detached, setsid
       └─ transfer_workspace_claim()       workflow="ace-monitor" so the dying
                                            starter's cleanup can't release it
  └─ maybe_handoff_monitor_from_agent()    writes .sase_monitor_pending, kills runner
                                            (NoReturn — see Finding 6)

runner SIGTERM
  └─ handle_monitor_marker()               axe/run_agent_exec_monitor.py:25
       └─ starter lands DONE with a synthetic chat that `#fork` will resume

supervisor
  └─ run_supervisor()                      supervise.py:84
       ├─ _stream_output()                 ← every Part 2 finding lives here
       ├─ _finish_monitor()                terminal marker, chat history, refresh pulse
       └─ launch_followup_agent()          followup.py:43   → %id(@, family=lane) attach
            or _release_claim_and_notify()
```

**What is genuinely good:** the "no new store" decision; the `ace-monitor` claim-workflow
trick that makes the slot un-releasable by the dying starter; reusing
`resolve_family_attach_plan()` so the follow-up attaches exactly as a user-typed
`%id(@, family=…)` would; `_widen_fence()` in the follow-up prompt (fenced code is an
xprompt literal zone, so widening the fence is a *correct* injection defense, not just a
cosmetic one); and the JSON schema version constant on the CLI surface from day one.

**Test coverage is strong for a mid-flight epic** — 2,985 lines across `tests/monitor/`,
`tests/main/`, `tests/ace/tui/`, and `tests/test_axe_run_agent_exec_monitor.py`. The gaps
in Part 2 survived *because* every one of them is a real-subprocess timing behavior that
the current fixtures (short, newline-terminated, quiet commands) cannot express.

---

## Part 2 — Correctness Findings

### Finding 1 — A chatty command never times out (high)

`_stream_output()` (`supervise.py:159`) checks the deadline only in the branch where
`select()` *times out*. When data is ready the loop `continue`s straight past it:

```python
ready, _, _ = select.select([stdout], [], [], _POLL_SECONDS)
if ready:
    line = stdout.readline()
    if line:
        capture.append(line)
        continue                      # ← deadline never evaluated
    break
if child.poll() is not None:
    break
if deadline is not None and not timed_out and time.monotonic() >= deadline:
    ...
```

A command that keeps the pipe hot never yields to the deadline check.
`termination.maybe_escalate()` sits in the same starved branch, so even *after* a timeout
SIGTERM, escalation to SIGKILL never happens while output continues.

```bash
# reproduction (run from the workspace root)
.venv/bin/python - <<'PY'
import subprocess, time, os, tempfile
from sase.monitor.supervise import _stream_output, _Termination
from sase.monitor.output import OutputCapture
d = tempfile.mkdtemp(); cap = OutputCapture(os.path.join(d,'out.md')); term = _Termination()
child = subprocess.Popen("while true; do echo chatty; done", shell=True, cwd=d,
    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    start_new_session=True, text=True)
term.attach(child); t0=time.monotonic()
_stream_output(child, cap, term, 2.0)      # 2-second budget
PY
# observed: still streaming 12.0s into a 2s budget (killed externally)
```

This is the failure mode that matters most for the epic's headline use case: a runaway
`just check-full` or a wedged CI poll that logs while it spins is exactly the thing the
timeout exists to bound.

### Finding 2 — Partial lines stall the supervisor and defeat "live" output (high)

`readline()` blocks until a newline arrives. Any command that renders progress with `\r`
— `cargo`, `npm`, `docker`, `pip`, `rsync`, most spinners — holds the supervisor inside
that call. Two consequences: the deadline is not evaluated for the duration, and
`capture.append()` is not called, so `live_reply.md` stays empty and the TUI shows a
monitor producing nothing.

```
partial-line-then-sleep      budget=2.0s  elapsed=8.0s  timed_out=False  file_bytes=24
```

(`printf 'progress-no-newline'; sleep 8; echo done` — 24 bytes appeared only at the end.)

The whole selling point of a monitor over a `bash` workflow step is that you can watch
it. For a large class of real commands, you currently cannot.

### Finding 3 — An orphaned grandchild keeps the monitor `running` (high)

`_stream_output()` treats pipe EOF as completion, but the pipe stays open as long as
*any* descendant holds it. A command that backgrounds a daemon (`(sleep 10 &); echo
done`) exits immediately while the supervisor blocks in the final `for line in stdout`
drain — which has no deadline at all:

```
orphan-holds-stdout-pipe     budget=3.0s  elapsed=10.0s  timed_out=False  file_bytes=12
```

Worse, `sase monitor stop` cannot rescue it: `_Termination._signal_child()` guards on
`self.child.poll() is None`, and the child has already exited, so the stop request is
silently dropped and the supervisor stays blocked. The lane is stuck until the orphan
releases the pipe — possibly never.

**Findings 1–3 have one fix.** Follow `tasks/supervisor.py:99`: pass the log file
descriptor as the child's `stdout` and poll `child.poll()` on a short tick. The child
writes to disk directly (kernel-buffered, no partial-line problem, genuinely live), the
supervisor never blocks on a read, the deadline is evaluated every tick, and the
completion signal becomes process exit rather than pipe EOF. The retained/capped view
that `_finish_monitor()` and the follow-up prompt need can then be read back from the
tail of the file at terminal time — which is what `read_tail_seek()` already does for the
CLI.

### Finding 4 — No `monitor_pgid`, so orphaned command trees are unkillable (high)

`sase.tasks` persists `pgid=child.pid` (`tasks/supervisor.py:119`, `tasks/models.py:45`)
precisely so a dead supervisor does not strand a live process tree. Monitors persist only
the supervisor's own pid, and `_reconcile_dead_supervisor()` (`store.py:135`) marks the
record `failed` **without killing anything**. If a supervisor is `SIGKILL`ed or the
machine loses it, `just check-full` keeps running forever, holding the workspace tree,
with no SASE surface able to reach it.

### Finding 5 — A hard-killed supervisor wedges the lane (high)

`cleanup_stale_running_entries()` (`ace/scheduler/stale_running_cleanup.py`) reclaims the
*workspace claim* for a dead pid, but nothing reconciles `monitor_state`. The member's
`agent_meta.json` still says `running` and no `done.json` exists, so:

- the Agents tab shows `MONITORING` forever with a ticking runtime;
- `sase monitor list` reports it active;
- `active_monitor_for_lane()` returns it, and `start_monitor()` raises
  `MonitorAlreadyRunningError` for every subsequent monitor in that lane — **or, if the
  command string matches, silently returns the dead record as though the monitor were
  live** (`start.py:76-84`), which is the more dangerous half: the caller believes a
  monitor is running, the agent is killed, and nothing ever happens.

Recovery today requires a human to run `sase monitor stop <id>`. The scheduler already
walks dead pids for claims; a monitor reconciliation pass belongs beside it.

### Finding 6 — Inside an agent, `sase monitor start` prints nothing (medium)

`kill_agent_runner_group()` is annotated `NoReturn` and ends in `sys.exit(0)`
(`main/utils.py:60-90`). `maybe_handoff_monitor_from_agent()` calls it, so in
`_handle_monitor_start()` everything after line 236 is unreachable when `SASE_AGENT` is
set:

```python
handed_off = maybe_handoff_monitor_from_agent(record)   # never returns in an agent
if bool(getattr(args, "json", False)): ...              # dead in an agent
print(f"Started monitor {short_id} ({record.monitor_id})")   # dead in an agent
if handed_off:
    print("\nThis is the last output before the agent runner is killed; …")  # dead
```

The plan required the opposite ("*When run inside an agent, this is the last output the
agent produces before it is killed — say so explicitly*"). The only test touching this
asserts `handed_off is False` (`tests/main/test_monitor_handler_start.py:256`), so the
agent path is untested. Fix: emit the summary *before* the handoff call. The information
does survive in the synthesized chat via `handle_monitor_marker()`, so this is a UX and
`--json`-contract bug rather than data loss.

### Finding 7 — The monitored command inherits the starter's agent identity (medium)

`start.py:162` spawns the supervisor with `env=os.environ.copy()`, and `supervise.py:106`
passes no `env=` at all — so the monitored command runs with the starter's `SASE_AGENT=1`,
`SASE_AGENT_NAME`, and `SASE_ARTIFACTS_DIR`, pointing at an agent that is already dead.
Every comparable boundary in this repo scrubs these (`scrub_agent_identity_env()` in
`chop_script_runner.py:26` and `axe/_process_start.py:58`).

Concretely, inside a monitored command:

- `sase artifact create` and `sase var` pass their `SASE_AGENT == "1"` guards and write
  into the dead starter's artifacts directory;
- `sase plan propose` / `sase questions` write handoff markers into a runner that no
  longer exists;
- a nested `sase monitor start` resolves `default_lane()` to the starter and then calls
  `kill_agent_runner_group()` on a stale pid.

This is a latent footgun rather than an observed failure, but it is cheap to close and
the repo has an established helper for it. Note the epic-launch path (`kp.9`) makes it
concrete: `sase bead work` is exactly the kind of command that reads agent identity.

### Finding 8 — `live_reply.md` is uncapped on disk (medium)

`MONITOR_MAX_OUTPUT_BYTES` (2 MiB) bounds only `OutputCapture`'s in-memory head+tail
view; `append()` writes every byte to the file unconditionally, and the docstring says so
("the file on disk is never truncated"). The plan's requirement — *"unbounded capture of a
chatty command must not fill the artifacts store"* — is therefore unmet. A monitor on a
verbose command for hours writes a multi-GB file into `~/.sase/projects/…/artifacts/`.
The rotation/cap belongs in the same poll loop as the deadline check.

### Finding 9 — Smaller correctness and fidelity gaps (low)

- **`monitor_output_path` is declared everywhere and written nowhere.** It exists on the
  Rust wire (`agent_scan_wire_markers.py:206`) and is read by
  `MonitorRecord.from_record()` (`models.py:134`), so `record.output_path` is always
  `None` and every consumer re-derives the path itself. Either write it in `member.py` or
  drop the field.
- **The follow-up does not inherit the starter's model or effort.** The plan required it
  ("*the starter's model/provider/effort so the follow-up is the same kind of agent*").
  `spawn_agent_subprocess()` takes no model parameter and `followup.py:107` passes no
  `SASE_MODEL_OVERRIDE` and no `%model`/`%effort` prefix, so an Opus planner's monitor
  hands off to a default-model agent. Cleanest fix: prefix the composed prompt with
  `%model:`/`%effort:` from the member's inherited meta — directives are stripped before
  the model sees the prompt, so this is idiomatic and invisible.
- **`_release_claim_and_notify()` releases without a workflow filter**
  (`supervise.py:301`). The claim was deliberately given the distinct
  `MONITOR_WORKSPACE_CLAIM_WORKFLOW`; releasing with `workflow=None` matches on
  `(workspace_num, cl_name)` only and can remove a claim the monitor does not own — most
  plausibly on the shared workspace `0` used by host-started monitors and `%wait` agents.
  Pass the workflow.
- **Running elapsed derives from the artifacts timestamp, not `run_started_at`**
  (`monitor_render.py:58-68`), so a monitor's displayed runtime includes member-creation
  and supervisor-spawn latency. Small, but it is the number the user watches.
- **Inline code spans in the follow-up prompt are not literal zones.** The tail is fenced
  and safe; `command` and `cwd` are rendered as `` `…` `` in the table. A command
  containing something like `#commit` or `%model:x` would expand in the follow-up's
  prompt. Narrow, but free to close by fencing or escaping those two cells.
- **`start_monitor()` has no lock around check-then-create.** The plan required keeping
  the `epic-launch-submit` file lock at the *caller*; the generic path relies on that
  caller-side discipline, so any future second caller reintroduces double-start.

---

## Part 3 — Design Opportunities

### 3.1 Converge the two supervisors

SASE now has two detached command supervisors with overlapping responsibilities:
`sase.tasks.supervisor` (durable task store, `pgid` tracking, dead-supervisor
reconciliation, no timeout) and `sase.monitor.supervise` (agent-family membership,
timeout, streaming, follow-up handoff). Each has something the other needs. The monitor's
bugs in Part 2 are all things `tasks` already got right; the task runner's missing timeout
is something the monitor tried to add.

The recommendation is *not* to merge the user-facing surfaces — an agent-family monitor
and a background task are genuinely different products. It is to extract the shared
mechanism: spawn detached with a new session, stream to a file, enforce a deadline,
escalate SIGTERM→SIGKILL on the pgid, persist `(pid, pgid)`, reconcile a dead supervisor.
One implementation, two thin policy layers on top.

### 3.2 Idle timeout, not just wall-clock timeout

`--timeout` bounds total runtime, which forces a bad trade: set it tight and a legitimately
slow `check-full` gets killed; set it generous (the epic launch uses 4h) and a wedged
command burns the whole budget before anyone notices. Once output goes to a file with a
polled loop (§Finding 1–3 fix), an `--idle-timeout 10m` — "no bytes written for N" — is
nearly free to add and is the check that actually catches hangs. This is the single
highest-value *new* feature the subsystem could gain.

### 3.3 Retry policy for flaky commands

`--next` is free text, so "re-run it if it fails" costs a whole follow-up agent turn. A
declarative `--retries N [--retry-on nonzero|timeout]` handled inside the supervisor would
convert the most common flaky-CI pattern from an LLM turn into a loop. Given that
`sase-j7` and `sase-j0` are both open flake-class beads, this is not hypothetical for this
repo.

### 3.4 The Rust core boundary is worth revisiting, deliberately

`CLAUDE.md`'s litmus test — *"if a web app, CLI, editor integration, or another frontend
would need the behavior to match the TUI, treat it as core backend logic"* — points at the
monitor state machine and record projection. The plan explicitly non-goaled a Rust monitor
store, and the reasoning given (agent-family semantics live in Python next to the runner)
is sound for the *lifecycle*. But `MonitorRecord.from_record()`, `monitor_state_bucket()`,
and the `done.json` precedence rules are pure projection over a wire the Rust side already
parses, and the Telegram/mobile/`/sase_agents_status` surfaces already need them to agree
with the TUI. Moving just that projection across would be a small, contained change that
honors the boundary rule without fragmenting the lifecycle. Worth a conscious decision
rather than inheriting the non-goal by default.

### 3.5 Parallel monitors and fan-in

"One active monitor per lane" is a correct simplification of a sequential lane, but it
blocks a real pattern: run `just check-full` *and* poll CI concurrently, then hand both
results to one follow-up. The generalization is a monitor group with a barrier follow-up
that fires when all members reach terminal state. Not for this epic — but the current
`MonitorAlreadyRunningError` should say so explicitly rather than reading as a bug.

### 3.6 Observability

The retry-spawn path emits `RETRY_SPAWNS_TOTAL` (`telemetry/metrics.py:32`). Monitors emit
nothing. Starts, terminal-state distribution, elapsed-vs-budget, timeout rate, and
follow-up launch failures are exactly the numbers that answer "is this feature earning its
keep?" — which is the question behind this research.

---

## Part 4 — Surfaces And Docs

- **`sase monitor list` / `show` do a full-history scan of every project on every call.**
  `_project_records()` (`store.py:248`) queries with `include_full_history=True`,
  `active_limit=None`, `recent_completed_limit=None`, `include_hidden=True`, and
  `_resolve_ref()` always passes `project=None`. `--follow` then repeats that scan every
  0.5s (`monitor_handler.py:305`), as does `stop_monitor()`'s wait loop and
  `_wait_for_monitor()`. Once the artifacts store has real history this becomes the most
  expensive idle loop in the CLI. Both loops already know the member's `artifacts_dir` —
  they should read that member's two marker files directly and reserve the index query for
  the initial resolution.
- **The `/sase_monitor` skill is good but under-specifies the hazards.** It should say:
  the command runs under `sh -c` (quote accordingly); a lane may have only one active
  monitor; do not monitor interactive or TTY-requiring commands; background daemons will
  hold the monitor open (until Finding 3 is fixed); and — once fixed — that
  `--json`/summary output is the last thing the agent sees. `--cwd`, `--lane`, `--label`,
  and `--tail-lines` are undocumented in the skill entirely.
- **A human cannot start a monitor.** `resolve_lane()` requires existing agent artifacts,
  so `sase monitor start --lane whatever` from a plain shell fails with
  `MonitorLaneError`. Host-started monitors work only because the epic launch borrows the
  planner's lane. Allowing a standalone lane would make `sase monitor` a genuinely useful
  interactive tool, not only an agent-facing one.
- **Still open in the epic:** `kp.8` (TUI detail panel, live-output rendering as a
  non-markdown log block, stop keybinding), `kp.9` (epic launch still calls
  `submit_epic_launch_task()` — the monitor path is not wired), `kp.11` (`docs/monitors.md`
  does not exist; `sase/memory/build_and_run.md` still does not tell agents to run
  `just check-full` through a monitor, which is the behavior change that makes the whole
  epic pay off), `kp.12` (smoke). Two `PROPOSED FOLLOW-UP:` notes are already parked on
  `kp.9` (patch/stitch terminology audit) and `kp.11` (glossary entry for **Monitor
  Member**).

---

## Ranked Recommendations

Ordered by (impact × confidence) ÷ cost. The first four are pre-land work on `kp.8`/`kp.12`
or a new phase; the rest are follow-on.

1. **Replace `_stream_output()` with the `tasks.supervisor` shape — child stdout straight
   to the log fd, `child.poll()` on a short tick.** One change fixes Findings 1, 2, and 3:
   timeouts fire under continuous output, `\r`-style progress renders live, and completion
   is process exit rather than pipe EOF so orphaned grandchildren stop wedging the lane.
   It also *removes* code. Nothing else on this list matters as much.

2. **Persist `monitor_pgid` and use it for stop, timeout escalation, and reconciliation.**
   Mirrors `tasks/models.py:45`. Without it, a hard-killed supervisor strands a live
   command tree that no SASE surface can reach (Finding 4).

3. **Reconcile orphaned monitors in the axe scheduler.** A dead supervisor pid with
   `monitor_state == "running"` and no `done.json` should be marked `failed` beside the
   existing `cleanup_stale_running_entries()` claim sweep — including the same-command
   early-return in `start_monitor()`, which today silently reports a dead monitor as live
   (Finding 5).

4. **Print the start summary before the handoff kill, and cover the `handed_off=True`
   path in tests.** Two lines moved; restores the plan's explicit requirement and makes
   `-j/--json` work in the only context that uses it (Finding 6).

5. **Scrub agent identity from the monitored command's environment** with the existing
   `scrub_agent_identity_env()`, and drop `SASE_ARTIFACTS_DIR`. Do this before `kp.9`
   lands, since `sase bead work` is exactly the kind of command that reads it (Finding 7).

6. **Cap `live_reply.md` on disk.** Enforce `MONITOR_MAX_OUTPUT_BYTES` against the file,
   not only the in-memory view — the plan's stated requirement, currently unmet
   (Finding 8).

7. **Stop polling the artifact index in tight loops.** `--follow`, `_wait_for_monitor()`,
   and `stop_monitor()` should read the member's own `agent_meta.json`/`done.json`; scope
   `_resolve_ref()` to the inferred project. Cheap now, increasingly expensive later.

8. **Add `--idle-timeout`.** The check that actually catches hangs, nearly free once
   recommendation 1 lands, and it lets `--timeout` be generous without being useless
   (§3.2).

9. **Carry the starter's model and effort to the follow-up** via a `%model`/`%effort`
   prefix on the composed prompt. Restores a plan requirement and prevents an Opus lane
   from silently continuing on the default model (Finding 9).

10. **Close the small fidelity gaps as one commit:** write or delete
    `monitor_output_path`; pass `MONITOR_WORKSPACE_CLAIM_WORKFLOW` to `release_workspace()`;
    compute running elapsed from `run_started_at`; fence the `command`/`cwd` cells in the
    follow-up prompt (Finding 9).

11. **Tighten the `/sase_monitor` skill** with the hazard list and the undocumented flags,
    and finish `kp.11`'s `build_and_run.md` edit — that memory change is what actually
    converts the feature into agent behavior (§Part 4).

12. **Extract the shared supervisor mechanism between `tasks` and `monitor`** once
    recommendations 1–3 have settled the correct shape. Do it as consolidation of proven
    code, not as speculative abstraction (§3.1).

13. **Add monitor telemetry counters** alongside `RETRY_SPAWNS_TOTAL` (§3.6).

14. **Allow standalone/host lanes so a human can start a monitor** without an existing
    agent lane (§Part 4).

15. **Revisit the Rust boundary for the state/projection layer only**, as a deliberate
    decision rather than an inherited non-goal (§3.4).

16. **Design monitor groups with a barrier follow-up** for parallel monitors, and make the
    current one-per-lane error message state the constraint as intentional (§3.5).

17. **Consider `--retries` for flaky commands** (§3.3).
</content>
</invoke>
