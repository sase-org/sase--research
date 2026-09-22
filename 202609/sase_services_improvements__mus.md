# SASE services: bugs, improvements, and extensions

Researcher: mus · 2026-09-22 · epic context: `sase-11y` (Service host and
Services tab, closed 2026-09-21; leftover child epic `sase-11y.11` also closed).

Method: independent source review of the shipped tree — `src/sase/service/`,
`src/sase/main/service_handler.py`, `src/sase/main/scheduler_handler.py`,
`src/sase/main/proc_handler.py`, `src/sase/procs/` (models, oneshot,
supervisor), the TUI Services surfaces (`ace/tui/actions/axe.py`,
`axe_display/`, `_proc_observer_models.py`, `_proc_query.py`), and the
`sase-11y` bead notes (#1–#9, including the note-#7 status blind spot and its
landing fix). No peer reports consulted.

## Background: what shipped

One per-machine `sase service` host (started at boot/login by a systemd user
unit or launchd LaunchAgent via `sase service init`) owns every background
process: the scheduler, the mobile gateway builtin, plugin daemons (e.g. the
Telegram receiver), user daemons, and `!` background commands (transient
oneshot service procs). Control from one CLI (`sase service ...`,
`... proc ...`) and one TUI Services tab; legacy supervision paths retired.
The note-#7 blind spot (proc-store readers ignoring rows whose additive
`service` wire block was stripped by an older `sase_core_rs`) was fixed at
landing via origin/tag fallbacks (`Proc.service_name`,
`is_service_row`/`service_row_name`).

## Bugs

### 1. `sase proc kill` still takes the direct-kill path on stripped daemon rows
(`src/sase/main/proc_handler.py:309-317`, `_request_service_proc_stop:353-383`)

The generic-kill router only diverts to a service stop marker when
`proc.service is not None and proc.service.name and mode == daemon`.
On a stripped row (`service=None`, `origin == "service-host"`,
`service:<name>` tag) it falls through to `kill_proc`, and the host restarts
the proc under its restart policy — the kill looks like a no-op or flaps.
This is the exact "residual, benign" case the `sase-11y.11` landing note
admitted. `_request_service_proc_stop` additionally `assert`s the wire block,
so the fix must touch both the predicate and the helper (derive the name via
the same fallback `Proc.service_name` uses, and treat host-origin rows as
daemons the way `is_service_daemon_row` does).

### 2. `Proc.is_service` disagrees with `Proc.service_name` on the same class
(`src/sase/procs/models/proc.py:153-170`)

`service_name` falls back to origin + `service:<name>` tag; `is_service`
returns `self.service is not None`. A stripped daemon row therefore reports a
name but `is_service == False`. Only test code consumes `.is_service` today
(`tests/test_procs_facade_models.py:42`), so impact is latent — but it is a
public-model trap for the next consumer. Make `is_service` true whenever
`service_name` is non-None (or deprecate it in favor of the TUI's
origin-aware helpers).

### 3. TUI `service_row_name` reads only `row.label`; core `Proc.service_name` reads tags
(`src/sase/ace/tui/_proc_observer_models.py:126-136` vs `models/proc.py:154-166`)

The host writes both (`label=f"service:{name}"`, `tags=["service",
"service:<name>"]` at `service/host.py:311-327`), so the two readers agree
today — but they depend on different fields surviving a store rewrite, and an
older core build is already known to drop additive fields. One side normalizes
away and the rows go dark on that surface only. Unify both on
`host_service_tag_name` over tags *and* label (also note `ObservedProc` has no
tags field in the excerpt reviewed — confirm what the observer retains).

### 4. Status surfaces can disagree with each other
(`service_handler.py:88`, `:208`, `:241`; `control.py:295-326`)

- `sase service status` uses `persisted_or_current_status()` (the host's
  `status.json` when fresh ≤ 15 s).
- `sase service proc list`, `proc show`, and therefore `sase scheduler status`
  (via `scheduler_handler.py:64-66` → `handle_service_proc_show`) use
  `current_service_status()` (derived from the proc store).
- Only the host-built snapshot carries restart decisions / pending-restart
  detail (`host_reporting.py:100-117`); `_proc_observations`
  (`control.py:340-371`) synthesizes observations with no restart decision.

  Consequences: during crash-loop backoff windows, or whenever `status.json`
  is stale/missing, `service status` and `scheduler status` / `proc show`
  tell different stories (one shows pending restart, the other plain
  "stopped"). The note-#7 fix closed the stopped-while-running case but not
  this source-of-truth split. Either prefer the fresh host snapshot in
  show/list (with a "derived" annotation when falling back), or document which
  command is authoritative for what.

### 5. Crash-loop `notify` is computed and then ignored

The Rust restart decision carries `notify`/`crash_loop`/`alert_sent`
(`service/restart.py:86-116`, `status.py:602-603`; `host.py:371` threads
`alert_sent` through), but no Python code consumes `.notify`: no status
diagnostic, no TUI badge, no log line, no notification. Crash loops are
visible only if the operator happens to inspect per-proc state. (Snapshot
`diagnostics` come solely from config diagnostics — `status.py:476-486` —
so nothing host-observed reaches them.)

### 6. Host log is unbounded; tails read whole files into memory

Per-proc output is bounded (`pump_service_output`/`append_bounded_log` with
`log_max_bytes`, `host_support.py:120-141`). The host's own log is opened
`"ab"` in the detached-start path (`control.py:207-219`) with no rotation,
and `latest_service_log_lines` (`control.py:329-337`) reads the entire file
before slicing the tail — used by both the CLI and the TUI's per-refresh
service-log tails (`axe_display/_data.py:360-377`). Slow growth today, real
cost on long-lived machines.

### 7. `restart_service_proc` is sleep-and-hope
(`service/actions.py:82-104`)

Stop → `sleep(delay)` (default 0.5 s; `sase scheduler restart` passes
`delay=0.0` at `scheduler_handler.py:71-77`) → clear → double-nudge, with no
verification the host observed the stop inside its 1 s reconcile window. A
missed window makes restart a no-op or a flap, yet the CLI prints "requested
... restart" unconditionally. Either poll for the expected transition or say
what actually happened (including "host not running — desired state recorded"
when `nudge_service_host()` returns False, which callers currently discard).

### 8. Action feedback overclaims when the host is down
(`service/actions.py:41-104`, `control.py:147-156`)

`start/stop/restart/enable/disable` print success-style "requested ..."
messages even when `nudge_service_host()` is False (no live host PID). For
desired-state markers that is semantically fine, but the CLI never says the
host will only honor the marker later. One clarifying sentence when
`nudged is False` fixes real confusion ("I stopped the scheduler but it says
running" — no: nothing was running and nothing will act until the host
starts).

### 9. Small CLI contract warts

- `_handle_proc_enablement` (`service_handler.py:265-270`) returns
  `0 if outcome.changed else 0` — a dead branch; exit status cannot
  distinguish no-op from change. Decide the contract (probably: always 0, drop
  the ternary) instead of leaving a condition that suggests otherwise.
- Bare `sase service` defaults to `status`, whose handler exits 1 when the
  host is not running (`service_handler.py:110`). "Harmless and shows status"
  (CLI help) but nonzero — health checks and scripts will misread it.
  Consider exit 0 for successful status rendering regardless of host state
  (or document the 1 contract in `--help`).
- `sase service status` prints init blockers/warnings; `proc list` does not
  (`service_handler.py:107-109` vs `:207-236`). An operator debugging a proc
  via `proc show` never sees "linger disabled" or "unit user-disabled".

### 10. Marker-dropped warning is stderr-only
(`service/host.py:387-399`)

`_warn_if_service_marker_dropped` warns once per host process to stderr —
under systemd/launchd that lands in the journal, where no CLI operator looks.
The condition it describes (older `sase_core_rs` stripping the `service`
block) is exactly what caused the note-#7 incident. Promote it to a snapshot
diagnostic so `sase service status` shows it.

## Objective improvements (small, high-confidence)

1. Fix kill routing (bug 1) with one shared helper for "daemon service name
   of a row, wire block or fallback" used by `proc_handler.py`,
   `Proc.service_name`, and the TUI helpers.
2. Align `Proc.is_service` with `service_name`; align `service_row_name`
   with tags + label (bugs 2–3).
3. Converge show/list onto the fresh host snapshot when available, annotated
   with source; or document authority per command (bug 4).
4. Surface crash-loop state: at minimum a `service status` diagnostic and a
   Services-tab indicator when `crash_loop`/`notify` is set; decide what
   `alert_sent` means operationally (bug 5).
5. Bound the host log (reuse `append_bounded_log` semantics or platform
   journal) and make tail reads not load whole files (bug 6).
6. Verify-or-report in `restart_service_proc`; report "host not running,
   desired state recorded" for all actions when the nudge misses (bugs 7–8).
7. Clean the CLI contracts: enablement exit code, bare-status exit code,
   `proc list/show` init warnings (bug 9).
8. Add the marker-dropped condition as a status diagnostic (bug 10).
9. `service init`: linger is currently warning-only
   (`platform.py:103-107`) although the host cannot survive logout without
   it. Offer to enable linger as a plan action (or a `--with-linger` apply
   path) rather than a line operators scroll past; same for the
   user-disabled-unit warning.
10. Regression tests for each fixed inconsistency (stripped-row kill routing,
    snapshot-source divergence, restart verification, host-log bound) in
    `tests/service/` alongside the note-#7 tests
    (`test_service_status.py`, `test_procs_facade_models.py`,
    `test_proc_query.py`).

## Larger extensions to consider

- **Readiness, not just aliveness.** Per-proc health checks (scheduler
  heartbeat freshness, gateway listen-port check, receiver liveness) with a
  readiness column in `service status` and the Services tab. Process-alive
  today can still mean a wedged daemon.
- **Crash-loop alerting.** A real consumer for the `notify` decision:
  notification-inbox entry, `sase service status` warning block, and/or a
  configured hook command. Ties into the contributors' notification work.
- **Log UX.** `sase service logs -f`, `sase service proc logs -f`, and
  bounded per-proc history with retention policy; the TUI already tails
  service logs per refresh, so follow-mode has a natural home.
- **Restart policy surfacing.** Per-proc restart tuning (backoff, thresholds)
  is decided in Rust; expose effective policy + recent-failure timeline in
  `proc show --json` and the Services detail view for post-mortems.
- **`service status --explain`.** Lock holder, heartbeat age, snapshot source
  (fresh host vs derived), platform unit state — one screen answering "why
  does it say starting?" without reading three files.
- **Resource guardrails.** Optional per-proc memory/CPU limits expressed in
  the platform units (systemd directives / launchd limits) plus a lightweight
  `service top` view. Long-lived daemons on shared boxes need this
  eventually; not urgent.
- **Fleet status.** `service status` across machines (athena/apollo migration
  already proved multi-host reality) via the tailnet/dispatch work — a
  read-only aggregated view, not control.
- **Oneshot history UX.** Post-reboot orphans settle "unknown"
  (`procs/oneshot.py:179-190`); consider a distinct "host restarted" outcome
  and a retention/GC policy for finished `!` rows. Nine slots
  (`MAX_ONESHOT_SLOTS = 9`) with a clear exhaustion message
  (`oneshot.py:237`) is fine, but `proc run --follow` would close the loop
  for long commands.

## Recommended set (definitely make)

1. Stripped-row kill routing fix (bug 1) — it re-opens the exact incident
   class `sase-11y` just closed, via the most natural operator command.
2. Status-source convergence or documented authority (bug 4) — two commands
   disagreeing about "running" destroys trust in the whole surface.
3. Crash-loop visibility (bug 5) — silent restart loops are the failure mode
   most likely to burn an operator next.
4. Restart verification + host-down honesty (bugs 7–8) — small, removes a
   whole class of "I thought I restarted it" confusion.
5. Model/reader consistency (`is_service`, label-vs-tags) + regression tests
   (bugs 2–3, item 10) — cheap, prevents the next fallback-reader incident.
6. Host-log bound + marker-dropped diagnostic + CLI contract cleanup
   (bugs 6, 9, 10) — operational hygiene while the code is fresh.

## Larger extensions worth mentioning

Worth scoping next: readiness checks, crash-loop alerting, `-f` log follow,
and `status --explain`. Fleet status and resource guardrails are real but
later; oneshot history polish is nice-to-have.
