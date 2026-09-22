# sase services: bugs, improvements, and extensions (`__mus`)

Swarm researcher report on the recently landed `sase services` feature
(epic `sase-11y`, closed 2026-09-21; child leftover epic `sase-11y.11` also
closed). Method: read the service-host runtime
(`src/sase/service/`), the CLI handler and parser
(`src/sase/main/service_handler.py`, `src/sase/main/parser_service.py`),
the Services-tab TUI actions (`src/sase/ace/tui/actions/axe.py`), the
installed unit on athena, and the user docs (`cli.md`, `configuration.md`,
`axe.md`); probed the live host on athena with the real CLI and timed it.

Overall assessment: the feature is in good shape. The landing notes show the
three significant known issues were all fixed at landing (Services-tab `x`
routing, stale PNG goldens, the service-marker blind spot in note #7), the
host-scenario tests the plan required now exist
(`tests/service/test_service_host_scenarios.py`: concurrent starts, stale
lock, signals, reload, stop-vs-restart race, crash backoff, oneshot settle),
and the quit-modal wording called out as leftover work now reads "Restart
TUI & service host". What remains is a layer of smaller real bugs, UX gaps,
and observability dead-ends — no architectural rework. Nothing below
contradicts the epic's closed status; these are follow-ups.

One live-machine note: while probing exit codes I ran
`sase service proc stop scheduler` on athena and immediately ran
`sase service proc start scheduler` to restore it. The scheduler relaunched
cleanly (new pid, `state: running`). No lasting effect, but the fact that a
read-only-looking investigation can bounce the scheduler that easily is
itself part of finding B2 below.

## Bugs (should fix)

### B1. `sase service logs` is silently empty under the native unit

`_handle_service_logs` tails `~/.sase/service/host.log`. That file only
exists on the detached-`Popen` path (`control.start_service_host` opens it in
append-binary mode). Under the installed systemd unit, the host's stdout
goes to the journal, `host.log` is never created (verified: no `*.log` in
`~/.sase/service/` on athena), and `sase service logs` prints nothing and
exits 0. An operator debugging a sick host gets silence with a success exit
code — the worst combination.

Fix: when `host.log` is absent/empty and a native unit is installed, fall
back to `journalctl --user -u sase.service -n N` (and the launchd equivalent
on macOS), or at minimum print "no host log; try `journalctl --user -u
sase.service`" to stderr. Companion fix: `sase service logs` and
`proc logs` deserve a `--follow` flag; today the only way to watch a proc
log live is `tail -F` on the path from `proc show`.

### B2. Proc actions report success when nothing honored them

`_handle_proc_enablement` returns exit 0 unconditionally
(`return 0 if outcome.changed else 0`), and start/stop/restart handlers
likewise always return 0 and print "requested …". Two failure modes are
masked:

- The host is down. `stop`/`start`/`enable` just write state rows and
  `nudge_service_host()` returns False, but the CLI never surfaces
  `nudged=False`. The message should say "service host is not running;
  takes effect on next start" and ideally exit nonzero (or at least the
  message must differ — scripts cannot distinguish "stopped" from
  "recorded a stop nobody will act on").
- Idempotent repeats are indistinguishable from real transitions
  ("requested service proc scheduler stop" printed both times).

Fix: thread `outcome.nudged` and `outcome.changed` into the message and
exit code. E.g. no-op repeat → "already stopped (no change)", host down →
warning + exit 1. The `ServiceProcActionOutcome` already carries both
fields; the handler just ignores them.

### B3. `sase service status` takes ~3.9 s; `proc list` takes ~0.7 s

Timed on athena (warm): `status` 3904 ms, `proc list` 690 ms. The delta is
`service_init_plan(force=True)` running inside `_handle_service_status` on
every invocation — provider-CLI readiness probes, executable resolution,
env capture — purely to append install warnings beneath the status table.
Status is the highest-frequency services command (humans, TUI-adjacent
scripts, agents); paying a 4-second init audit each time is wrong, and it
makes the "is the host up?" check feel broken.

Fix: drop the init-plan section from `status` (it belongs to
`service init` / `doctor`), or gate it behind `--init-check`, or cache it
with a TTL. Note the inconsistency this also resolves: `status` exits 1
when the host is down while `proc list` always exits 0 — pick one contract
for "host down" and document it (`cli.md` currently documents neither).

### B4. Synchronous `_stop_child` blocks the whole host loop

`_reconcile_desired` stops deselected/reconfigured children inline, and
`_stop_child` waits up to `entry.stop_timeout_seconds` — whose schema
allows up to **3600 s**. During that wait the host does no other
reconciliation, records no heartbeats (status goes stale after 15 s, the
TUI health pill flips red), and a SIGTERM cannot be honored until the wait
ends (systemd will SIGKILL after `TimeoutStopSec`, and the unit sets no
explicit `TimeoutStopSec`). One wedged proc can therefore wedge host
shutdown and orphan every sibling's supervision for up to an hour.

Fix (small): cap the effective stop wait (e.g. min(configured, 30 s)),
move SIGKILL escalation ahead of the full wait, and/or stop children
concurrently rather than sequentially in `_stop_all_children`. At minimum
keep heartbeating during a long stop so the host doesn't look dead while
it is working.

### B5. Crash-loop `notify` is a dead letter

The Rust restart decision returns `notify: true` on crash loops and the
host persists it in `status.json` (`ServiceStatusProc.restart`), but no
Python or TUI consumer reads `decision.notify` / `crash_loop` anywhere
(grepped: zero non-test consumers). A proc can be crash-looping with
backoff and the only evidence is buried in `status --json`. The CLI tables
(`status`, `proc list`, `proc show`) don't render `restart`, `restarts`,
or `last_exit` at all.

Fix: surface `crash_loop`/`restarts`/`last_exit` in `proc show` and add a
`state` qualifier (e.g. `backing off · 5 restarts`) in the tables; route
`notify` into the existing notification.Delete path or the Services-tab
health pill. This is the cheapest high-value observability win in the list.

### B6. `service.procs.<name>.after` is not honored at runtime

`host.py` contains zero references to `entry.after` — all configured
daemons launch in the same reconcile tick in config order, with no
dependency wait or readiness gate. If the Rust composer topologically
sorts by `after`, ordering is approximately right but readiness is still
unmodeled (a dependent can start before its dependency is listening);
if it doesn't sort, `after` is documentation. Docs (`configuration.md`)
promise "start ordering only", which overclaims either way.

Fix: verify what the composer guarantees; either implement true ordering
in `_reconcile_desired` (hold a proc in `pending` until its `after` set is
observed running, with a timeout that degrades to warn-and-launch) or
downgrade the docs to "advisory; the host may start entries in any order".
Also note cycles only make entries unavailable at compose time — good —
but an `after` name that is disabled/stopped probably blocks nothing,
which should be stated.

### B7. Orphan procs are invisible to humans

The snapshot schema carries `orphans` and `status --json` emits them, but
neither human table (`status`, `proc list`) renders them. Orphans are
exactly the rows an operator needs after un-installing a plugin or
renaming a proc (ex-`telegram_receiver` rows, stale scheduler rows).

Fix: print an "Orphaned procs" section (even one line each with pid/state)
when non-empty.

### B8. TUI silently drops proc actions while a worker is busy

`_run_service_proc_action`, `_start_service_host`, and friends return
without feedback when `self._axe_worker is not None`. Pressing `x`/`r`
during a slow action (host start waits up to 15 s) appears broken — no
toast, no queueing.

Fix: notify "service action already in progress" or serialize requests.
Trivial.

### B9. TUI toggle refuses disabled procs instead of offering enable+start

`_toggle_selected_service_proc` stops at "Service proc is disabled" for a
stopped-but-disabled proc. The operator's intent (start it) takes two
trips (enable key, then `x`). Minor; consider a confirm-to-enable-and-start
flow.

## Objective improvements (should make)

1. **Host-log rotation.** Proc output logs are bounded (`log_max_bytes`,
   default 2 MiB) but the detached-path `host.log` is opened `"ab"` with
   no bound, and `latest_service_log_lines` slurps the whole file to split
   lines. Reuse `append_bounded_log` for host stdout or document that the
   detached path is debug-only.
2. **`proc logs`/`service logs` `--follow`.** (See B1.)
3. **`sase service init` drift detection.** `start` from a shell uses the
   caller's live env; the unit uses the env captured at `init` time. There
   is a warning for `SASE_FEATURE_FLAGS` drift but nothing that says "unit
   env is N days old; re-run `init --yes`". A `captured_at` timestamp plus
   a staleness hint in `init` (not in `status` — see B3) would close the
   loop.
4. **Exit-code contract documentation.** `cli.md` should state which
   service commands exit nonzero when (host down, unknown proc, init
   not-current). Today only `init --check` semantics are discoverable.
5. **`restart` delay should be a poll, not a sleep.**
   `restart_service_proc` sleeps a fixed 0.5 s between stop-marker and
   clear; the host reconciles every ~1 s, so the stop is frequently never
   observed (harmless today only because the clear+nudge relaunches
   anyway — meaning "restart" often degrades to "ensure running" without
   actually bouncing the process). Poll for the child to actually exit
   (bounded, e.g. 10 s) before clearing the marker; fall back to the
   current behavior on timeout.
6. **Doctor coverage for services.** `sase doctor` should gain (or
   document) the service checks an operator needs: unit installed+active,
   linger on, env freshness, crash-looping procs, orphaned rows. Some of
   this exists piecemeal in `init_plan` warnings; doctor is where people
   look.
7. **Per-proc `reported` status is write-only infrastructure.** The host
   exposes `SASE_SERVICE_PROC_STATUS` and reads `status.json`, but the
   scheduler/orchestrator no longer writes the legacy file (see
   `axe/_process_status.py`: "not written by the new orchestrator
   architecture"). Either get one writer (scheduler heartbeat summary
   would make the Services tab much richer) or remove the read path
   before it confuses someone.

## Larger extensions (consider)

- **E1. Health checks per proc.** `restart: always` restarts dead
  processes, but a wedged-yet-alive proc (gateway bound but not
  responding, scheduler alive but not ticking) is "running" forever. An
  optional `health_check: {argv|http_get, interval, timeout}` entry with
  failures feeding the existing restart/crash-loop machinery would be the
  single biggest reliability upgrade, and the status/notify plumbing from
  B5 is the natural display surface.
- **E2. `sase service proc edit` / `config` visibility.** Today the path
  from "proc is CrashLooping because its command is wrong" to a fix is:
  discover which config layer owns the entry (`proc show` gives
  `declared_by` — good), hand-edit that file, `proc restart`. A
  `proc config NAME` that prints the effective entry plus provenance, and
  eventually `proc set NAME key=value` for machine overlays, would shorten
  the most common remediation loop.
- **E3. Resource limits and log-level controls per proc.** systemd-level
  `MemoryMax`/`CPUQuota` and per-proc log verbosity are the obvious next
  knobs once multiple user daemons share the host; the `service.procs`
  schema has room and the unit template is generated, so this is cheap.
- **E4. Host-initiated safe update.** `sase update` today restarts the
  scheduler/TUI; a `sase service stage-update` that drains oneshots,
  stops children gracefully, swaps the binary, and verifies heartbeats
  would remove the most failure-prone manual sequence on remote machines.
- **E5. Multi-host visibility (fleet).** Out of scope for one machine, but
  the status snapshot is already serializable — publishing it (or a digest)
  per machine would let the AXE/mobile surfaces show athena vs apollo
  health in one place. Don't build this until two machines actually hurt.

## Recommended set (definitely make)

If only a subset gets scheduled, make it these, in order:

1. B1 (empty `service logs` under systemd) — actively misleading today.
2. B5 (surface crash-loop/restarts/last_exit) + B7 (show orphans) — same
   small area, turns the CLI from "control plane" into "observable".
3. B2 (honest messages/exit codes when the host is down or nothing
   changed) — scripting safety.
4. B3 (take `init_plan` out of `status`) — 4 s → <1 s on the most-run
   command.
5. B4 (bound stop waits; heartbeat during stops) — the only item with a
   hang-the-host failure mode.
6. B8 (TUI busy feedback) — one-line fix.
7. B6 — at minimum the two-sentence docs correction; runtime ordering only
   if the composer doesn't already sort.

Verification performed: live `service status` / `proc list|show|stop|start`
on athena (all healthy; scheduler restored after the probe), `status`
3904 ms vs `proc list` 690 ms timings, `show`/`stop` unknown-proc exit 2,
`service logs` empty with exit 0 and no `host.log` on disk, unit file
contents (`KillMode=mixed`, `Restart=on-failure`, no `TimeoutStopSec`),
scenario-test inventory, zero-consumer grep for `notify`/`crash_loop`,
zero-reference grep for `after` in `host.py`. Rust-core composer internals
were not inspected (no checkout in this workspace); B6's composer half is
flagged accordingly rather than asserted.
