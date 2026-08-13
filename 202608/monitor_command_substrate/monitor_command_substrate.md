---
create_time: 2026-08-13
updated_time: 2026-08-13
status: research
---

# `sase monitor`: the family model is right, the command substrate is not

**Research question.** The `sase-kp` epic is mid-flight. What would most improve the
correctness, durability, and usefulness of SASE monitors?

**Consolidated from three independent investigations.**

| Source | Author | Angle |
| --- | --- | --- |
| [`monitor_command_substrate__a.md`](monitor_command_substrate__a.md) | `research.0e.cdx` (codex/gpt-5.6-sol) | Durability, control surfaces, agent handoff; external systems comparison |
| [`monitor_command_substrate__b.md`](monitor_command_substrate__b.md) | `research.0e.cld` (claude/opus) | Line-level code audit against the sibling `sase.tasks` primitive |
| this report | lead | Re-verification at current `HEAD`, adjudication of conflicts, newly-landed surface |

**Snapshot.** Both source reports were verified against `22319c52d`. This report is
verified against **`73ec160bb`** (master, clean tree), which is two monitor commits
later — `44796037a` (kp.9, epic launch) and `73ec160bb` (kp.11, docs/memory) both landed
in between. Every defect below was **re-reproduced at `73ec160bb`**; line references are
to that commit.

**Epic status (authoritative, `sase bead show sase-kp`).** 10 of 12 phases closed. Only
`sase-kp.8` (TUI detail panel, live output, keybindings) and `sase-kp.12` (end-to-end
monitor exercises, sized `xsmall`) remain in progress. Both source reports list four open
phases; that is stale.

## Bottom line

Both independent investigations reached the same conclusion, and this one confirms it:
**modeling a monitor as an ordinary agent-family member was the right call, and the
command supervisor is where the value leaks.** There is no new store — `store.py` is 289
lines, and the artifact index, family roster, runtime aggregation, chat history,
workspace claims, and `#fork` handoff all work on monitors with almost no
monitor-specific code. That part of the epic should be considered done and good.

The defects concentrate in one function, `supervise._stream_output()`
(`supervise.py:159-188`), which drives output streaming *and* timeout enforcement from a
single blocking, line-oriented, text-decoding `readline()` loop. That one choice produces
six distinct failures, all reproduced. The most severe is not in either source report's
top tier: **a single invalid UTF-8 byte kills the supervisor outright at t≈0**, orphaning
a live process group that nothing in SASE can reach.

The timing matters. `kp.11` landed a `sase/memory/build_and_run.md` instruction directing
every agent to run `just check-full` through a monitor — and a continuously-chatty
command like `just check-full` is precisely the shape whose timeout never fires. The
documentation that makes the feature pay off also maximizes the blast radius of the bug
underneath it.

## Verified defect matrix

All probes drive the **shipped** `_stream_output()` against real subprocesses at
`73ec160bb`. "stuck" means the loop had not returned when the probe's own cutoff
(budget + 6s) expired.

| # | Command shape | Budget | Elapsed | `timed_out` | Result |
| --- | --- | --- | --- | --- | --- |
| A | continuous output (`while true; do echo chatty; done`) | 2.0s | 8.0s stuck | `None` | **timeout never fires**; 19,741,134 bytes written |
| B | partial line (`printf` no newline, then sleep) | 2.0s | 8.0s stuck | `None` | **blocks in `readline()`**; 0 bytes on disk |
| C | backgrounded grandchild holding stdout | 3.0s | 9.0s stuck | `None` | **pipe EOF never arrives**; stays `running` |
| D | quiet (`sleep 8`) — **control** | 2.0s | 2.0s | `True` | correct |
| E | stdout **and** stderr closed, process alive | 2.0s | 8.0s stuck | `None` | blocks in unbounded `child.wait()` |
| F | invalid UTF-8 byte, then sleep | 2.0s | **0.01s** | — | **`UnicodeDecodeError` escapes the supervisor** |
| G | TERM-ignoring **and** chatty | 2.0s | 12.0s stuck | `None` | SIGTERM sent, **SIGKILL escalation starved** |

Control D matters for calibration: the timeout *does* work for quiet commands, which is
why the shipped tests pass. Every supervisor test uses a short, quiet,
newline-terminated command (`echo hello world`, `sh -c 'echo boom >&2; exit 3'`, `true`,
`sleep 30` — `tests/monitor/test_monitor_supervise.py`). No test emits continuous output,
a partial line, or a non-UTF-8 byte. The gaps survived because the fixtures cannot
express them, not because the code was unreviewed.

### Why the loop fails

```python
ready, _, _ = select.select([stdout], [], [], _POLL_SECONDS)   # supervise.py:171
if ready:
    line = stdout.readline()      # blocks on a partial line (B); decodes strictly (F)
    if line:
        capture.append(line)
        continue                  # ← deadline and escalation never evaluated (A, G)
    break                         # ← EOF, not process exit (C)
if child.poll() is not None:
    break
if deadline is not None and not timed_out and time.monotonic() >= deadline:
    ...                           # only reachable when select() times out
termination.maybe_escalate()      # ← same starved branch (G)
...
for line in stdout:               # unbounded drain
    capture.append(line)
child.wait()                      # ← no timeout (E)
```

`select()` guarantees one readable *byte*, not a newline, so `readline()` can block
arbitrarily. `text=True` gives a `TextIOWrapper` with `errors='strict'`, so any invalid
byte raises. And `run_supervisor()` wraps only the `Popen` call in `try` — the
`_stream_output()` call at `supervise.py:134` has no guard at all.

### Finding F is the one to fix first

Neither source report ranked this correctly. Report A mentioned non-UTF-8 output as a
sub-bullet ("decoding can raise from the text wrapper") and the missing `try`/`finally`
as a separate finding, but never connected them or probed either. Report B did not
mention decoding at all. Verified consequence chain, end to end:

```text
one invalid byte
  → UnicodeDecodeError escapes _stream_output()      (t = 0.01s)
  → no try/finally in run_supervisor()               (supervise.py:133-155)
  → supervisor dies; stdout/stderr are DEVNULL       (start.py:161-163) → traceback invisible
  → child process GROUP still alive                  (verified: killpg(pid, 0) succeeds)
  → no monitor_pgid persisted anywhere               → nothing in SASE can kill it
  → agent_meta.monitor_state stays "running", no done.json
  → lane wedged; workspace claim held; --next follow-up never launches
```

Triggers are ordinary: a compiler emitting latin-1 diagnostics, a test printing binary, a
`grep` that hits a binary file, a tool running under a non-UTF-8 locale. It is a
one-byte, permanent, silent lane wedge.

## The central disagreement, resolved

The two reports agree on the diagnosis and **disagree on the fix**. Resolving it requires
a fact both got partly wrong.

- **Report B** recommends adopting `tasks.supervisor`'s shape, described as handing "the
  child's stdout **directly to the log file descriptor** (`stdout=output`)… No reader
  thread."
- **Report A** recommends a nonblocking, byte-oriented `os.read()` pump with an
  incremental UTF-8 decoder, evaluating the deadline every iteration, and separately
  describes tasks' logs as "a pipe drain plus shared bounded-log rotation."

**Report A's characterization is the correct one; Report B's is not.**
`tasks.logs.open_task_log()` does not return a file. It returns `_BoundedTaskLogPipe`
(`tasks/logs.py:103-168`), whose `fileno()` is the **write end of an `os.pipe()`**,
drained by a daemon thread that reads 64 KiB chunks and appends through
`append_bytes_locked(..., truncate_oversized=True)` — which rotates at a byte cap
(`logs/_bounded.py:94-142`). There *is* a reader thread, and the supervisor *does* stay in
the data path.

This matters, because B's simplified description would, if implemented literally, remove
the supervisor from the data path and make B's own recommendation #6 (cap `live_reply.md`
on disk) and A's Findings 4 and 6 (bounded logs, secrets redaction) impossible. The
apparent conflict between the two reports dissolves once the real mechanism is used.

### Recommended shape

Reuse the existing, tested primitive rather than writing either new loop:

1. **Transport** — spawn with `stdout=<pipe-backed bounded writer>`, `stderr=STDOUT`, as
   `tasks/supervisor.py:99-109` does. Partial lines stop mattering (`os.read` returns
   whatever is available), decoding stops mattering (bytes, not text), and a full pipe
   applies natural backpressure to a runaway command.
2. **Wait loop** — poll `child.poll()` on a short tick like `tasks/supervisor.py:42-55`,
   and add the deadline check tasks lacks. Completion becomes **process exit**, not pipe
   EOF, which is what fixes C. Drop `_POLL_SECONDS` from 0.5s to tasks' 0.05s so timeout
   and kill escalation have sub-second granularity.
3. **Bounding** — the drain thread already enforces a byte cap, which closes A-4/B-8 for
   free.
4. **Do not adopt tasks' retention verbatim.** `append_bytes_locked` keeps only `path`
   plus one rotated `path.1`, so a long run **loses the head**. `OutputCapture`'s
   head + tail elision (`output.py:38-79`) is genuinely better for a follow-up LLM — you
   want the start of the build *and* the failure at the end. Keep that accumulator and
   feed it from the drain thread, taking `bytes` chunks instead of `str` lines.
5. **Guard everything** — wrap the whole lifecycle in `try`/`finally` that TERM→KILLs the
   child tree and writes a terminal marker, as `tasks/supervisor.py:137-152` does.

This one change resolves A-1, A-4, B-1, B-2, B-3, B-8, and probes A/B/C/E/F/G, and it
*removes* code. Two independent reproductions plus this one make the diagnosis
high-confidence; nothing else on the list is close in value.

A secondary benefit neither report noted: `OutputCapture` currently opens the log with
`buffering=0` (`output.py:36`) and writes **once per line**. Probe A wrote 19.7 MB as
~2.8M unbuffered write syscalls in 8 seconds — the supervisor burns a core streaming a
chatty command. The drain thread batches into 64 KiB appends.

## Crash safety and process ownership

Confirmed by both reports and re-verified:

- **No child pgid is persisted.** `sase.tasks` records `pgid=child.pid`
  (`tasks/supervisor.py:119`, `tasks/models.py:45`) precisely so a dead supervisor cannot
  strand a live tree. Monitors persist only the supervisor's own pid
  (`start.py:174`), and that write happens *after* `Popen`, leaving a window with no pid
  at all.
- **Reconciliation does not reconcile.** `_reconcile_dead_supervisor()`
  (`store.py:135-163`) marks the record `failed` but **kills nothing, releases no claim,
  and — noted by neither report — silently drops the `--next` follow-up.** For the
  headline use case (`just check-full --next "fix what failed"`), a dead supervisor means
  the follow-up agent never runs and the lane simply goes quiet.
- **Reconciliation is only reachable through `stop`.** `list`, the TUI, and the scheduler
  never call it, so a wedged lane requires a human to run `sase monitor stop <id>`.
- **A dead monitor can be reported as live.** `start_monitor()` returns the existing
  record unchanged when the command string matches (`start.py:78-79`), with no liveness
  check — the caller believes a monitor is running, the agent is killed, and nothing
  happens.
- **`stop` can signal a recycled pid.** It checks only that the numeric pid is alive
  (`store.py:112`). SASE already has stronger patterns to reuse: task reconciliation
  validates the supervisor command line, and `axe/maintenance.py` records `/proc` start
  ticks plus boot ID.

## Lifecycle ordering

Report A's transactional analysis is correct and confirmed in the code:

- **The command can start before the workspace claim is secured.** `start.py` spawns the
  supervisor at line 151 and only transfers/acquires the claim at lines 177-195. The
  supervisor reads `monitor_state="running"` and may `exec` immediately. On claim failure
  the code sends a best-effort SIGTERM to the supervisor (`_kill_supervisor`, line 197) —
  which, per probe G, may be starved if the command is chatty. A mutating command can
  therefore run without ever holding the claim.
- **Terminal state precedes settlement.** `_finish_monitor()` writes `done.json` before
  launching the follow-up or releasing the claim, so observers see `completed` while
  settlement is still running. Phase `kp.6` already recorded the resulting flaky test.
  Kubernetes makes exactly this distinction for Jobs (terminating vs. the final
  `Complete`/`Failed` condition); the invariant is worth borrowing, the infrastructure is
  not.
- **Check-then-create is unlocked.** `start.py:75` → `130` has no per-lane lock. The
  caller holds one today — `epic_launch.py:146` wraps the whole resolve-and-start in
  `log_file_lock(tasks_dir() / "epic-launch-submit")` — but the generic primitive should
  enforce its own invariant rather than depend on every future caller's discipline.
- **Idempotency is command-string equality.** The same command returns the existing
  monitor even when cwd, timeout, `--next`, statuses, or reason differ. A request
  fingerprint or explicit idempotency key would make a changed request conflict visibly.

## The newly-landed surface (kp.9 / kp.11)

Neither source report could see these; both landed after their snapshot.

**`kp.9` promotes a low-priority finding into a routine one.** The epic-launch path calls
`start_monitor(... inherit_lane_workspace_claim=False)` (`epic_launch.py:164`), which
routes to `claim_workspace(project_file, 0, ...)` — the **shared workspace 0**. Report B
filed the unfiltered claim release as sub-item #10 of a "small fidelity gaps" bundle,
correctly guessing it was "most plausibly on the shared workspace 0." It is now the
default path for **every approved epic launch**. `_release_claim_and_notify()` calls
`release_workspace(..., cl_name=cl_name)` with no `workflow` argument
(`supervise.py:301-305`), and `workflow` is an optional matcher
(`running_field/_operations.py:160-164`), so the release matches on `(workspace_num,
cl_name)` alone and can remove a claim the monitor does not own — on the slot shared with
`%wait` agents. Passing `MONITOR_WORKSPACE_CLAIM_WORKFLOW` is a one-line fix that should
be reclassified as pre-land.

Also worth noting on that path: the epic-launch monitor sets `next_action=None` and a
4-hour timeout. The absent follow-up is a deliberate and reasonable choice (the launched
epic spawns its own agents), but it means a supervisor crash during an epic launch
produces no signal at all beyond a stuck row.

**`kp.11` is done, and it is what raises the stakes.** `docs/monitors.md` exists (9.1 KB),
and `sase/memory/build_and_run.md:39-41` now instructs agents to run `just check-full`
through `/sase_monitor` and never inline. Report B lists both as outstanding; that is
stale. The consequence is the framing above: the memory change that converts the feature
into agent behavior is live, pointed at a continuously-chatty command, on top of a
supervisor whose timeout cannot fire for continuously-chatty commands.

**`kp.12` is the natural home for the fix, and is mis-sized.** It is the one remaining
non-TUI phase, currently `xsmall`. It should carry the regression matrix below and be
resized accordingly, or a dedicated hardening phase should be added.

## Trust boundary, secrets, and identity

- **Command output crosses an LLM trust boundary.** The follow-up prompt embeds the
  retained tail verbatim. Report B is right that `_widen_fence()` is a real defense, not a
  cosmetic one — a fenced block is an xprompt literal zone, so widening the fence
  genuinely prevents directive expansion. But a code fence does not stop a *model* from
  treating "ignore prior instructions and run …" as an instruction, and build output
  routinely contains attacker-influenced text (test names, dependency output, fetched
  content). Add an explicit untrusted-data notice immediately before the tail, prefer a
  deterministic outcome summary plus an artifact reference over a large inline tail
  (`--next-output none|tail|file`), and add adversarial smoke tests.
- **Two prompt cells are not literal zones.** `command` and `cwd` render as inline code
  spans, not fenced blocks, so a command containing `#commit` or `%model:x` would expand
  in the follow-up's prompt. Free to close.
- **Secrets are durable.** The exact shell command is persisted in `agent_meta.json`,
  saved to chat history, and echoed in notifications. A shared redaction pipeline over
  task and monitor logs, plus an argv form (`sase monitor start -- cmd arg...`) alongside
  an explicitly-named shell mode, is the right long-term shape. Redaction must be tested
  for secrets split across chunk boundaries.
- **The monitored command inherits the dead starter's agent identity.** `start.py:166`
  passes `env=os.environ.copy()` and `supervise.py:106` passes no `env=` at all, so the
  command runs with `SASE_AGENT=1`, `SASE_AGENT_NAME`, and `SASE_ARTIFACTS_DIR` pointing
  at an agent that no longer exists. Every comparable boundary in this repo scrubs these
  (`scrub_agent_identity_env()` in `chop_script_runner.py:26`, `axe/_process_start.py:58`).
  Inside a monitored command, `sase artifact create` and `sase var` would pass their
  `SASE_AGENT == "1"` guards and write into the dead starter's directory; a nested `sase
  monitor start` would call `kill_agent_runner_group()` on a stale pid. With `kp.9`
  landed, `sase bead work` runs on this path routinely.

## Smaller confirmed gaps

- **Inside an agent, `sase monitor start` prints nothing.** `kill_agent_runner_group()` is
  `NoReturn` (`main/utils.py:60`), so every line after
  `maybe_handoff_monitor_from_agent()` in `_handle_monitor_start()` is unreachable when
  `SASE_AGENT` is set — including `-j/--json`. The plan required the opposite ("*this is
  the last output the agent produces before it is killed — say so explicitly*"). The only
  test asserts `handed_off is False`. Fix: emit the summary before the handoff call.
- **The follow-up does not inherit the starter's model or effort.** `followup.py` contains
  no model, effort, or `SASE_MODEL_OVERRIDE` handling, so an Opus lane's monitor hands off
  to a default-model agent, against the plan. Prefixing the composed prompt with
  `%model:`/`%effort:` is idiomatic and invisible — directives are stripped before the
  model sees the prompt.
- **`monitor_output_path` is declared everywhere and written nowhere**, so
  `record.output_path` is always `None` and every consumer re-derives it. Write it or drop
  it.
- **Displayed runtime includes member-creation and supervisor-spawn latency**, because
  elapsed derives from the artifacts timestamp rather than `run_started_at`. Small, but it
  is the number the user watches.
- **Index polling in tight loops.** `--follow` (0.5s), `stop_monitor()`'s wait loop, and
  `_wait_for_monitor()` each re-query the artifact index with `include_full_history=True`,
  `active_limit=None`, `include_hidden=True` (`store.py:248-275`). Report B overstates this
  slightly — `_monitor_records()` does push `only_monitors=True` into the query wire, so
  Rust does the filtering; the genuinely unfiltered full-history scan is `resolve_lane()`'s
  call, which runs once at start. The loops still know the member's `artifacts_dir` and
  should read its two marker files directly.
- **A human cannot start a monitor.** `resolve_lane()` requires existing agent artifacts,
  so `sase monitor start --lane whatever` from a plain shell fails. Host-started monitors
  work only because epic launch borrows the planner's lane.

## Highest-value new capability

**`--idle-timeout`.** `--timeout` bounds total runtime, forcing a bad trade: set it tight
and a legitimately slow `check-full` is killed; set it generous (epic launch uses 4h) and
a wedged command burns the whole budget before anyone notices. Once output goes through a
polled loop, "no bytes written for N minutes" is nearly free to add and is the check that
actually catches hangs. A quiet command is not automatically unhealthy, so this must be
opt-in per monitor rather than a global default.

Beyond that, the useful additions in rough order are outcome-aware follow-ups
(`--next-on success|failure|timeout`), declarative `--retries N --retry-on nonzero|timeout`
for flaky commands, host-wide admission control via concurrency groups, and monitor
telemetry counters alongside the existing `RETRY_SPAWNS_TOTAL`. Kubernetes and Temporal
are worth borrowing invariants from — bounded attempts, heartbeats, terminal settlement —
not infrastructure.

## What not to build

- Do not replace agent artifacts with a monitor database. The no-new-store decision is the
  epic's best call; add lifecycle fields to the existing member record.
- Do not add cron or recurring monitors. AXE already owns recurring execution.
- Do not make automatic restart the default. Most shell commands are not proven idempotent,
  and a monitor can be a deploy or a bead launch.
- Do not make systemd mandatory. Report A's optional Linux backend (transient user
  services, `KillMode=control-group`, `cgroup.kill`, resource accounting) is well-evidenced
  and this host supports it (systemd 257, cgroup v2, `Linger=yes`), but SASE also supports
  macOS. It is a P2 hardening backend behind a corrected portable supervisor, not a
  replacement for one — and after a boot-ID change an unfinished monitor must become
  `lost`, never silently re-run.
- Do not add detailed telemetry before the supervision and settlement invariants are
  correct.
- Do not move the monitor *lifecycle* into Rust. Report B's narrower suggestion —
  relocating only `MonitorRecord.from_record()`, `monitor_state_bucket()`, and the
  `done.json` precedence rules, which are pure projection over a wire Rust already parses —
  is a legitimate reading of the repo's boundary rule and worth a deliberate decision, but
  it is not urgent and should not be bundled with the supervisor fix.

## Regression matrix for `sase-kp.12`

The planned smoke phase covers normal completion, nonzero exit, timeout, stop, CLI
formats, and epic approval. Every row below is a currently-failing or unexercised
boundary; the first seven correspond to probes A-G.

| Boundary | Exercise | Required invariant |
| --- | --- | --- |
| stream | continuous output past the deadline | timeout wins; tree is dead |
| stream | partial line, no newline | output is live; deadline still evaluated |
| stream | backgrounded grandchild holds stdout | completion is process exit, not pipe EOF |
| stream | stdout **and** stderr closed, process alive | supervisor stays responsive |
| stream | invalid UTF-8 byte | supervisor survives; output is replaced, not fatal |
| stop | child ignores TERM and prints continuously | SIGKILL after grace |
| crash | SIGKILL the supervisor with a live grandchild | tree killed, claim released, follow-up dispositioned |
| identity | stale or recycled supervisor pid | unrelated process is never signaled |
| start | two simultaneous starts in one lane | exactly one command executes |
| claim | forced claim-transfer failure | command never executes |
| settle | follow-up launch delayed or failing | no premature terminal state; no leaked claim |
| logs | output beyond the cap while `show --follow` runs | disk bounded; follower survives rotation |
| trust | output contains injected directives and secrets | neither reaches an action nor durable plaintext |
| reboot | active marker from a previous boot | monitor becomes `lost`; no implicit rerun |

## Ranked recommended improvements

Ranked by (impact × confidence) ÷ cost. Items 1-7 are pre-land work on `kp.12` or a new
hardening phase; the rest are follow-on.

1. **Rebuild `_stream_output()` on the `tasks` pipe-and-drain-thread shape, with the
   deadline in a `child.poll()` loop.** Spawn with a pipe-backed bounded writer
   (`_BoundedTaskLogPipe`), poll on a 50 ms tick, treat process exit as completion, and
   keep `OutputCapture`'s head + tail retention by feeding it byte chunks from the drain
   thread. Fixes probes A, B, C, E, F, G and closes A-1, A-4, B-1, B-2, B-3, B-8 in one
   change that *removes* code. Nothing else matters as much.
2. **Wrap the whole supervisor lifecycle in `try`/`finally`.** On any internal failure,
   TERM→KILL the child tree, finalize the log, and write a terminal marker. Today a single
   invalid byte silently orphans a live process group forever (probe F). Even after item
   1 removes the decode path, the guard is what makes every *other* unexpected failure
   survivable.
3. **Persist the child pgid — and a stronger identity than a pid.** Mirror
   `tasks/models.py:45`, and record `/proc` start ticks plus boot ID as `axe/maintenance.py`
   already does, so `stop`, escalation, and reconciliation can never signal a recycled pid.
4. **Make reconciliation active and complete.** Run it from `list`, the TUI, and the axe
   scheduler beside the existing stale-claim sweep — not only from `stop`. It must kill the
   surviving tree, release the claim, and surface the dropped `--next` follow-up. Add a
   liveness check to `start_monitor()`'s same-command early return, which today can report a
   dead monitor as live.
5. **Pass `MONITOR_WORKSPACE_CLAIM_WORKFLOW` to `release_workspace()`.** One line.
   Reclassified from "small fidelity gap" to pre-land because `kp.9` made shared workspace 0
   the default for every approved epic launch.
6. **Scrub agent identity from the monitored command's environment** with the existing
   `scrub_agent_identity_env()`, and drop `SASE_ARTIFACTS_DIR`. `sase bead work` now runs on
   this path.
7. **Print the start summary before the handoff kill**, and cover the `handed_off=True`
   path in tests. Two lines moved; restores a plan requirement and makes `-j/--json` work in
   the only context that uses it.
8. **Make lane start and settlement transactional.** Per-lane lock inside the generic
   primitive; a launch barrier so the child cannot `exec` before the claim is held; a request
   fingerprint or idempotency key; and terminal state written only after child, log, claim,
   and follow-up disposition are settled.
9. **Add `--idle-timeout`.** The check that actually catches hangs, nearly free after item 1,
   and it lets `--timeout` be generous without being useless.
10. **Harden the follow-up prompt boundary.** An explicit untrusted-data notice before the
    tail, `--next-output none|tail|file`, fenced `command`/`cwd` cells, and adversarial smoke
    tests. Deterministic separation first; no guardrail LLM.
11. **Carry the starter's model and effort to the follow-up** via a `%model:`/`%effort:`
    prefix on the composed prompt.
12. **Close the remaining fidelity gaps as one commit:** write or delete
    `monitor_output_path`; compute running elapsed from `run_started_at`; stop re-querying the
    artifact index in `--follow`, `stop_monitor()`, and `_wait_for_monitor()`, reading the
    member's own marker files instead.
13. **Add a secrets redaction pipeline** shared by task and monitor logs, applied before
    disk, TUI, notification, chat, and follow-up writes, plus an argv mode alongside an
    explicitly-named shell mode.
14. **Add monitor telemetry and a bounded lifecycle journal** — starts, terminal-state
    distribution, elapsed-vs-budget, timeout rate, follow-up launch failures — alongside the
    existing `RETRY_SPAWNS_TOTAL`.
15. **Extract the shared supervisor kernel between `tasks` and `monitor`** once items 1-4
    have settled the correct shape. Consolidation of proven code, not speculative abstraction.
16. **Add host-wide admission control** — bounded concurrency groups with an explicit
    reject/queue/replace policy and a visible `QUEUED` state. Replacement must never be the
    silent default, because monitored commands mutate workspaces and deployment targets.
17. **Outcome-aware continuation and bounded retries** — `--next-on`, linked manual
    `sase monitor retry`, and strictly opt-in `--retries` for commands declared idempotent.
18. **Allow standalone/host lanes** so a human can start a monitor without an existing agent
    lane, and state the one-per-lane constraint as intentional in
    `MonitorAlreadyRunningError`.
19. **Tighten the `/sase_monitor` skill** with the hazard list (runs under `sh -c`; one
    active monitor per lane; no interactive or TTY-requiring commands) and the undocumented
    `--cwd`, `--lane`, `--label`, `--tail-lines` flags.
20. **Optional Linux systemd/cgroup backend** — transient user services, `Type=exec`,
    `KillMode=control-group`, resource accounting — behind the corrected portable supervisor,
    with macOS retained as a tested fallback.
21. **Revisit the Rust boundary for the projection layer only**, and design monitor groups
    with a barrier follow-up for parallel monitors. Both are deliberate future decisions, not
    epic work.
