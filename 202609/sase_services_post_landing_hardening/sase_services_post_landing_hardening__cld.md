# SASE services after landing: bugs, fixes, and extensions (sase-11y review)

**Researcher:** cld (swarm research.27) · **Date:** 2026-09-22 · **Scope:** the service host,
service procs, oneshots, platform units, env contract, and the Services tab shipped by epic
`sase-11y` (and child epic `sase-11y.11`).

**Code examined:** sase `3844ed83d` (master), sase-core `c5186cc` (v0.34.71, the version
installed in the venv), sase-telegram `76431fc`. I also checked the live host on athena
(systemd unit, proc store, per-proc logs, journal, and `/proc/<pid>/environ`) on the morning
of 2026-09-22. That was about 6 hours after a reboot at 06:30 EDT.

**Evidence labels used below:**

- **LIVE**: observed on athena today.
- **CODE**: I confirmed it by reading the code at the lines cited.
- **PROBE**: reproduced by a throwaway script or temporary test. These were run by
  read-only helper agents I delegated to; the scripts live outside the repo.
- **READ**: traced by reading code but not reproduced.

---

## 0. Executive summary

The architecture shipped as designed: one platform unit, one foreground host, a file control
plane, durable proc rows, a Rust-owned config, state, status and restart core, and the
Services tab. The live unit matches the plan exactly (`Type=exec`, a stable ExecStart,
`KillMode=mixed`, linger on). It survived today's reboot, and detached work really does escape
the host cgroup: the host cgroup holds only the host, gateway, scheduler, receiver, routines and
short-lived chops.

However, the **supervision semantics have one critical hole, and several failure paths are
silent**:

1. **The host ignores its own "give up" decisions.** When the Rust restart function says
   `give_up` (for `restart: never`, or a clean exit under `restart: on-failure`), the next 1 s
   reconcile relaunches the proc anyway, with no backoff. This happened live today. After the
   reboot, `telegram_receiver` exited 0 about 30 times, roughly every 2 s, because
   `pass`/gpg could not produce the bot token yet. It recovered only *because* of this bug.
   Fixing the host alone would therefore leave the receiver **down after every reboot**. The
   host fix and a receiver exit-code fix must ship together (§2, H1+H2).
2. **Crash loops are invisible outside an open TUI.** The Rust decision's `notify` flag is
   never acted on. The crash-loop flag switches itself off once backoff reaches its cap. The
   TUI treats only `failed`/`error` as failures, but Rust never emits either of those states.
   It emits `backoff`, `crash_loop` and `exited`.
3. **A broken config blinds the host.** A fatal `service:` config stops exit observation and
   status writes, and the TUI shows a healthy `SVC 0/0`. A config layer that failed to parse
   is silently ignored, so saving a machine overlay with a YAML error mid-edit makes the host
   *stop* the gateway and receiver within 1 s.
4. **The environment contract is leaky in production.**
   - The captured, now-dead `SSH_AUTH_SOCK` overrides the working one in the scheduler and
     gateway right now (LIVE).
   - `init --check` can never settle (LIVE).
   - `SASE_TMPDIR` never reaches the host (open bead `sase-15q`).
   - Boot-time secrets that go through `pass`/gpg are unavailable until login (LIVE).
5. **Stops are not graceful for the scheduler's chops.** systemd SIGKILLed chops, including
   `git` and `ssh` children, on 2 of the 3 host stops since the reboot (LIVE journal). Also,
   `sase update` restarts only the scheduler, so the host and gateway keep running pre-update
   code.

None of these requires rethinking the design. Most fixes are small and local. §8 has the
recommended "definitely do" list in priority order, followed by the larger extensions worth
considering.

---

## 1. Live observations on athena (2026-09-22)

| Item | Observation | Label |
|---|---|---|
| Unit | `sase.service` active since 07:42:36, enabled, `NRestarts=0`, linger on. ExecStart is the uv tool path, not an ephemeral workspace. Came back by itself after the 06:30 reboot. | LIVE |
| Processes | Exactly 1 `sase service run` and 1 `sase scheduler run`, plus 10 routines. `sase-14x` (39 duplicate hosts on 2026-09-20) does **not** reproduce right now. | LIVE |
| Host cost | Host pid used 28 s of CPU in 42 min (~1%). The unit as a whole averaged ~1.15 cores over the previous 12 h (13 h 50 m of CPU), almost all from scheduler chops; memory peaks 4–7 GB per run. | LIVE |
| Receiver flapping | `procs.jsonl` holds 17 `service:telegram_receiver` rows with `success/exit 0`, about 2 s apart, from 10:35:23Z to 10:36:06Z. The receiver log has ~30 matching "Telegram credentials unavailable; receiver exiting … `pass show telegram_sase_bot_token` failed: gpg: public key decryption failed". Retention (20 rows per service) already pushed out the earliest rows. | LIVE |
| Dead SSH agent | `~/.sase/service/env` captured `SSH_AUTH_SOCK=/tmp/ssh-bd1YBG80VDga/agent.13572` on 09-20. That path is **not a socket** now. The gateway (pid 1523548) and scheduler (pid 1964543) both run with it, so every agent the scheduler launches inherits a dead agent socket. Git still works only through the IdentityFile fallback. | LIVE |
| `init --check` | `needs_attention` → "write …/service/env" (drift in PATH and the SSH vars between shells). | LIVE |
| Stop kills | Journal: `Killing process … (sase_job_artifa) with signal SIGKILL` (06:38:43); `sase_job_commen`, `git`, `ssh` SIGKILLed (07:17:18). The 06:38 and 07:17 stops took 10–11 s. | LIVE |
| Logs | `sase service logs` prints nothing (`host.log` only exists in detached mode). `procs/gateway/output.log` is 0 bytes. `procs/scheduler/output.log` holds two stale "Axe orchestrator is already running (pid …)" lines from 09-20. Per-proc logs have no timestamps or run separators. | LIVE |
| Scheduler restarts | Six scheduler rows since boot, all `killed … stopped`. These were requested restarts; none were crashes. | LIVE |

---

## 2. Critical and high-severity bugs

### H1. The host relaunches procs it decided not to restart (critical) — CODE, PROBE, LIVE

- **Where:** `src/sase/service/host.py`.
  - `_settle_exit` (lines 202–213) queues a `_PendingRestart` only when `decision.action ==
    "restart"`.
  - For `give_up`, the name is left in neither `_children` nor `_pending`.
  - The third loop of `_reconcile_desired` (lines 252–256) then relaunches every entry that is
    in neither map and is `_desired_running`:

  ```python
  for entry in config.procs:
      if entry.name in self._children or entry.name in self._pending:
          continue
      if self._desired_running(entry, state):
          self._launch(entry, history=self._restart_history.get(entry.name))
  ```

  - `_desired_running` (lines 258–265) never consults `_restart_decisions`.
- **Effect:**
  - `restart: never` behaves like `always` with a 1 s delay.
  - `restart: on-failure` plus a clean exit behaves the same way. This is exactly the "a
    disabled receiver exiting 0 must not flap" case the plan called out.
  - Each relaunch passes `restarts=0`, so the restart counter and last-exit chip reset.
  - The status snapshot reads `running, restarts=0` most of the time, so the pill stays green
    while the proc spins.
  - Flapping also flushes the per-service 20-row history within ~40 s.
- **Fix:**
  - Keep a per-name `given_up` record keyed by the entry signature, and skip those names in
    loop 3.
  - Clear the record on a signature change, an explicit `proc start`/`restart`/`enable`, or a
    stop marker being cleared. A per-proc "start generation" in `state.json` makes "explicit
    start" observable to the host; see M6.
  - Add scenario tests for `on-failure` + exit 0 and `never` + exit 1.

### H2. The Telegram receiver reports "not ready yet" as a clean exit — LIVE, CODE (sase-telegram)

- **Where:** `sase-telegram/src/sase_telegram/scripts/sase_tg_inbound.py`, `_run_receiver`.
  - It returns `0` for "Telegram disabled" and also for "credentials unavailable".
  - `default_config.yml` declares `restart: on-failure` and `success_exit_codes: [0]`.
- **Why it matters now:** at boot, `pass`/gpg cannot decrypt the token until the user
  session's gpg-agent is usable. The receiver exits 0, and only H1's bug brings it back.
  **If H1 is fixed alone, the receiver stays down after every reboot until someone runs
  `sase service proc start telegram_receiver`.**
- **Fix (ship together with H1):**
  - Exit 0 only for "disabled".
  - Exit with a distinct retryable code for "credentials unavailable", so on-failure backoff
    (capped at 60 s) retries it. EX_TEMPFAIL = 75 is one option.
  - Separately, put the bot token somewhere readable at boot. Options: a 0600 token file, or
    adding `SASE_TELEGRAM_BOT_TOKEN` to the captured secret names on athena only. Otherwise
    Telegram is silent after an unattended reboot.
  - Ordering: release sase-telegram first, or gate the host change on the receiver release.

### H3. Service failures are not loud anywhere durable — CODE, PROBE

Three independent defects add up to "hidden from the gear means invisible failure", which the
plan explicitly forbade.

1. **`notify` is dropped.**
   - `decide_service_restart` sets `notify=True` once per crash-loop episode. It is copied into
     the status wire (`src/sase/service/status.py:603`), and nothing else reads it.
   - The old orchestrator's `_surface_crash_loop` (`src/sase/axe/orchestrator.py:197–259`)
     persisted an error and sent a notification. The host has no equivalent, and nothing
     notifies on `give_up` either.
2. **The crash-loop flag turns off in steady state.**
   - In `sase-core/crates/sase_core/src/service/restart.rs:271–276`, `crash_loop =
     recent_failures(within 60 s) >= 3`. But backoff caps at 60 s (`restart.py`
     `ServiceRestartTuning`), so once backoff is capped, failures land more than 60 s apart.
   - A proc that crashes forever therefore reads `crash_loop` for failures 3–7 and plain
     `backoff` afterwards (PROBE).
   - `alert_sent` stays true, so a later episode is not re-announced until a 300 s healthy run.
3. **The TUI's failure vocabulary doesn't match the wire.**
   - The TUI treats `{"failed","error"}` as failure in `src/sase/ace/tui/_service_health.py:14`,
     `widgets/bgcmd_list.py:557,602`, `widgets/axe_info_panel.py:240`,
     `widgets/_axe_dashboard_status.py:300` and `widgets/_axe_dashboard_output.py:60`.
   - `derive_proc_state` in `status.rs:566–595` emits only `running`, `unavailable`,
     `disabled`, `stopped`, `crash_loop`, `backoff` and `exited`.
   - Result: a crash-looping proc renders dim, with the "coming up" glyph. Only the generic
     `desired==running && state!=running` rule turns the pill to `!`, and only between runs.
   - `proc.summary` ("exited with code 1; retrying in 4s"), `proc.restart` and `proc.stop`
     provenance are never rendered.
   - The tests use a made-up `state="failed"` (`test_services_phase_closure.py:83`), so they
     pass while real states render quietly.

**Fix:**

- The host emits a durable notification for `decision.notify` and for `give_up` on a proc
  that is desired running. Reuse the orchestrator's error-file plus `notify_workflow_complete`
  path, tagged `service`/`crash-loop`.
- Make crash-loop sticky until a healthy run: `crash_loop = recent >= threshold || (alert_sent
  && consecutive_failures >= threshold)`.
- Map `backoff`, `crash_loop`, and `exited` with `desired==running`, to the red failure style.
- Render `summary` as a chip.
- Fix the test fixtures to use real wire states.

### H4. A bad config blinds the host and misleads the TUI — CODE, PROBE

1. **The host goes blind on a fatal config.** `_reconcile_once` (host.py:108–124) calls
   `load_service_config()` first. On `ServiceConfigError`:
   - **nothing** after it runs: `_observe_exits` doesn't reap or restart crashed children, and
     `_reconcile_desired` doesn't apply stops.
   - The fallback `write_current_host_status(self)` (`host_reporting.py:36`) calls
     `load_service_config()` again, fails, and swallows the error, so `status.json` goes stale.
2. **The TUI reports health instead of an error.**
   - After 15 s, `persisted_or_current_status()` rebuilds the snapshot, which raises. The TUI
     swallows that into a trace event (`actions/axe_display/_data.py:343–351`), leaving
     `service_status=None`.
   - `derive_service_health(None)` then returns a **healthy `SVC 0/0`**. The chrome says
     "stopped · press !x", and `!x` answers "already running".
   - `test_health_no_snapshot_is_healthy_empty` locks this behavior in.
3. **Layer parse errors are silently ignored.**
   - `service_config_compose` (`sase-core/.../service/config.rs:168–256`) never reads
     `layer.error`, and it filters only `kind == "local"`. Other unknown kinds are classified
     as "user".
   - So a machine overlay saved with a YAML syntax error composes as if the overlay didn't
     exist: `gateway` and `telegram_receiver` fall back to `enabled: false`, and the host
     **stops them** on the next reconcile (PROBE).
4. **`_stop_child` reloads config.** It calls `load_service_config()` just to settle
   (host.py:501–503). A fatal config during shutdown therefore aborts `_stop_all_children`
   after the first child.

**Fix:**

- Keep a **last-known-good composition** in the host. On a fatal or errored-layer compose,
  keep reconciling against it and publish the diagnostic in the status snapshot and heartbeat
  `error`. This is systemd's "old unit until daemon-reload succeeds" model.
- Observe exits independently of config: `_settle_exit` has `running.entry`.
- In Rust, treat a present-but-errored machine layer as fatal, which then triggers
  last-known-good.
- In the TUI, return a degraded marker instead of `None` and render `SVC ?` with the reason.

### H5. Proc-store rewrites destroy fields they don't understand (root cause of the 09-21 stripping) — CODE, PROBE

- **Where:** `sase-core/crates/sase_core/src/procs/wire.rs:19–92`. `ProcWire`,
  `ProcServiceWire` and `XpromptProcMetaWire` are closed structs with no `#[serde(flatten)]`
  catch-all.
- **Why that matters:** every writer rewrites `procs.jsonl` in full: append, reserve,
  `mutate_proc`, `prune_procs`, and even `update_proc` with a non-matching id.
  - Any process holding an older `sase_core_rs` therefore strips additive fields from
    *every* row. That includes long-lived TUIs, plugins, the gateway, and a stale wheel.
  - Rows with an unsupported `schema_version` are dropped entirely.
  - The test `unknown_fields_are_tolerated_and_malformed_rows_are_dropped_on_rewrite` asserts
    that stripping happens.
- **What landing did:** the fix at sase-11y landing (a Python fallback via
  origin + `service:<name>` tag) treats the symptom only on the read side.
  - **Rust retention** (`store.rs:593–604`) still identifies service rows only by
    `proc.service`. Stripped host rows fall back under the generic 100-row cap, where
    per-service last-N should apply (PROBE).
  - `ProcUpdateWire` has no `service` field, so a stripped block can never be re-attached.
- **Fix:**
  - Add a flatten `extra` map to the proc wires (and to the `state.json` wires) and flip the
    test.
  - Preserve unparseable and newer-schema lines verbatim on rewrite.
  - Give Rust retention the same origin/tag fallback.
  - Consider a store-level writer-version marker so an old writer can refuse to downgrade the
    file.
- **Scope:** this is a general store-hygiene fix. It protects every future additive field,
  not just `service`.

### H6. The environment contract leaks in production — LIVE, CODE

1. **A dead captured `SSH_AUTH_SOCK` wins (LIVE).**
   - `_capture_ssh_agent` (`src/sase/service/env.py:235–246`) checks liveness only at capture
     time. `load_service_environment(override_existing=True)` (`env.py:171–173`, called from
     `host_lifecycle.py:25`) applies the value with no check.
   - The module's own docstring says "a stale socket path is worse than none".
   - Per-login `/tmp/ssh-*/agent.*` sockets are always dead after a reboot, while the user
     manager's `/run/user/1000/openssh_agent` is live.
   - `docs/init.md:212–219` claims the host falls back to the manager's agent, and it doesn't.
   - **Fix:** at load time, drop `SSH_AUTH_SOCK`/`SSH_AGENT_PID` unless the path is a live
     socket. Better still, never capture session-scoped `/tmp/ssh-*` sockets and never
     override an inherited live one.
2. **`init --check` never settles (LIVE).**
   - `environment_files_match` (env.py:178–183) requires exact equality, including PATH and
     the per-shell SSH vars. So `init --check` and `sase doctor -C service.platform` report
     drift permanently.
   - A casual `init --yes` from an agent shell would capture that shell's socket and its
     `SASE_FEATURE_FLAGS`.
   - **Fix:** exclude volatile keys from the currency check, normalize PATH, and warn when
     capturing from a non-login context (for example `SASE_AGENT*` set, or `VIRTUAL_ENV` or a
     workspace path on PATH).
3. **Profile-exported SASE settings are missing.** `SASE_TMPDIR` and other SASE path
   overrides are never captured, so housekeeping reaps the wrong root (open bead `sase-15q`,
   67 GiB unreaped on apollo).
   - **Fix:** capture an allow-list of `SASE_*` path overrides. Have `doctor` compare the
     host's `SASE_*` against a login shell's.
4. **Boot-before-login secrets** (H2): document which secrets need a file or captured value
   for unattended boots, and have `init --check` flag secrets that only resolve through
   agent-backed tools (`pass`/gpg).

### H7. Host stops SIGKILL scheduler chops, and restarts report false failures — LIVE, CODE

1. **Chops outlive the routine and get SIGKILLed.**
   - Chops start with `start_new_session=True` (`src/sase/axe/chop_script_runner.py:198–210`),
     and routines only set `_running=False` on SIGTERM (`src/sase/axe/lumberjack.py:497–499`).
   - So the host's `killpg` of the scheduler never reaches in-flight chops. When the host
     exits, `KillMode=mixed` SIGKILLs them, including `git` and `ssh` mid-operation (LIVE
     journal).
   - This contradicts `docs/axe.md:1573–1576`, which says the orchestrator "forwards it to all
     children".
2. **`sase service restart` often reports failure.**
   - The host stops children **sequentially**, each with up to `stop_timeout` (default 10 s)
     plus a 5 s kill wait (`host.py:467–509`).
   - `platform_runner.default_runner` runs `systemctl` with `timeout=10`
     (`platform_runner.py:33–39`), and `systemctl --user restart` blocks until the stop
     finishes.
   - Stops of 10–11 s (LIVE) therefore make `sase service restart` report a timeout failure
     while the restart actually succeeds.
   - The heartbeat also freezes during a long stop, which can make the TUI show the host as
     `stale`.

**Fix:**

- Routines forward SIGTERM to running chop process groups and wait a bounded time.
- The host stops children in parallel (signal all, then wait up to the max `stop_timeout`).
- Set `TimeoutStopSec` above the total stop budget.
- Run `systemctl` with `--no-block`, then poll `is-active` or the heartbeat, or use a timeout
  larger than the stop budget.

### H8. `sase update` leaves the host and gateway on old code — CODE

- **CLI path:** `src/sase/main/update_restart.py:37–77` restarts only the `scheduler` proc.
- **What stays stale:**
  - The host process and gateway keep pre-update code.
  - With the editable install on athena, the long-lived host lazily imports *new* modules into
    an *old* process, a mixed-version hazard.
  - The receiver refreshes itself through its generation digest, so it is fine.
- **Inconsistency:** the TUI update path restarts the whole host (`ace_handler.py:91–96` →
  `restart_service_host`), so the two update paths disagree.
- **Detection gap:** the heartbeat's `sase_version` comes from dist-info, so staleness can't
  be detected after a git fast-forward.
- **Fix:**
  - Make the CLI restart the host (matching the TUI), or at least the gateway too.
  - Record a code fingerprint in the heartbeat and render a "stale code" chip: editable git
    SHAs plus the `sase_core_rs` version.

---

## 3. Medium-severity bugs

- **M1. `!x` stops the whole host from any tab, with no confirmation (CODE).**
  - `_toggle_axe_global` (`src/sase/ace/tui/actions/axe.py:121–150`): off the Services tab,
    with the host running and no oneshot active, `!x` calls `_stop_service_host()` directly.
  - Under the old AXE model this stopped the scheduler. Now it takes down the gateway (the
    phone loses its API) and the Telegram receiver, until the next boot or TUI start.
  - **Fix:** confirm before a host stop, or make off-tab `!x` target the scheduler proc.
- **M2. `!e` works on every tab against a stale selection (CODE, PROBE).**
  - `_handle_bang_key` (axe.py:184–188) has no tab check, and `_axe_service_selection` keeps
    its value after you leave the tab.
  - It writes **persistent machine policy** with no confirmation. A harness disabled `gateway`
    from the Agents tab.
  - Related: `_refresh_axe_display` runs off-tab (`axe.py:365`, `axe_bgcmd.py:414–418`),
    re-deriving the Services selection from the *active* tab's index and replacing the footer.
- **M3. `!x` on a oneshot row kills or dismisses it instead of toggling the host (CODE).**
  - axe.py:135–139. This contradicts the plan and the help text. A *finished* oneshot is
    dismissed with no confirmation.
- **M4. `x` on a crash-looping or exited proc does nothing (READ).**
  - The code is `action = "stop" if proc.state == "running" else "start"` (axe.py:391), so for
    `backoff`/`crash_loop` it "starts" a proc that has no stop marker.
  - The only way to quiet a loop from the tab is `!e`, which is a persistent disable.
  - **Fix:** choose stop whenever `desired == "running"`.
- **M5. State-store robustness in Rust.**
  1. **Missing boot id wipes all stops (CODE, PROBE).** `prune_expired_stops`
     (`state.rs:371–386`) runs on every mutation, including the 1 s heartbeat.
     - If the host's `current_boot_id()` is `None`, it deletes every stop recorded under a
       real boot id and saves the deletion.
     - `current_boot_id()` is `@cache`d, so one transient failure lasts the host's lifetime.
       On macOS the probe is a `sysctl` call with a 0.5 s timeout, run at login.
     - **Fix:** never prune when the current boot id is unknown, and don't cache `None`.
  2. **Wrong-shape `state.json` wedges everything (PROBE).** Valid JSON of the wrong shape
     (`[]`, `null`, `{}` with no `schema_version`) makes every read and mutation raise, with no
     quarantine.
  3. **The GIL is held during state and status lock waits and fsyncs (READ).**
     `sase_core_py/src/config/mod.rs`; the procs bindings use `allow_threads`.
- **M6. Restart via a 0.5 s stop marker can be lost (READ).**
  - `restart_service_proc` (`src/sase/service/actions.py:82–104`) writes a stop, sleeps
    0.5 s, and clears it.
  - If the host is inside a blocking `_stop_child` (up to 15 s) or `handover_scheduler` (up to
    20 s), it never sees the marker, and the restart silently does nothing.
  - **Fix:** a per-proc restart generation in `state.json` that the host consumes. This also
    gives H1 its "explicit start" signal, and lets the CLI wait for and confirm the new pid.
- **M7. Signals go to a PID without verifying ownership (CODE).**
  - `nudge_service_host` and `stop_service_host` (`control.py:147–156, 236–259`) signal
    `record.pid` whenever that PID is alive. They don't check `lock_held` or the boot id.
  - If the host died uncleanly and its PID was reused, `SIGUSR1` (default action: terminate)
    or `SIGTERM` hits an unrelated user process. `start_service_host` would also report
    "already running".
  - **Fix:** require `lock_held` and a matching `record.boot_id` before signaling.
- **M8. Orphaned daemon children after an unclean host death (READ).**
  - Children use `start_new_session=True`. In detached mode, or on macOS where there is no
    cgroup kill, a SIGKILLed or OOM-killed host leaves them running.
  - Only the scheduler has a single-owner handover. A new host starts a second gateway (which
    crash-loops on port 7629 while the orphan serves old code) and a second Telegram
    `getUpdates` consumer.
  - Daemon rows left `running` by a dead host are never settled; only oneshots are
    (`host_lifecycle.py:52–57`).
  - **Fix:** at startup, settle stale daemon rows, and kill (or adopt; see E3) live orphan
    pgids recorded in them.
- **M9. Platform lifecycle gaps (CODE, READ).**
  - **`init --yes` never restarts an active unit after its definition or env changes**
    (`platform.py:173–195`). It passes `start=not already_active`, so a new ExecStart or a
    rotated key does nothing until the next restart.
  - If a *detached* host holds the lock, `sase service run` under the unit exits 1. Under
    `Restart=on-failure` / `RestartSec=5` that repeats forever, and init still reports
    success.
  - **Fix:**
    - Stop or hand over a detached host during apply.
    - Give "already running" its own exit code, listed in `RestartPreventExitStatus=` and in
      launchd `SuccessfulExit`.
    - `try-restart` on change, or print "restart required".
- **M10. The detached host inherits the caller's cwd and env (CODE).**
  - `start_service_host` passes `cwd=Path.cwd()` and the TUI's full environment
    (`control.py:209–218`), and it picks the executable from `sys.argv[0]`.
  - Procs without `cwd` then run in that directory (host.py:298). That may be an ephemeral
    workspace that later disappears (compare the `$HOME` anchoring comment in
    `lumberjack.py:507–510`), and the host may run workspace code.
  - **Fix:** host cwd = `$HOME`, proc default cwd = `$HOME`, and the canonical executable (as
    the unit writer already does).
- **M11. TUI performance and refresh correctness (CODE, PROBE).**
  1. **Blocking refresh after every action.** After every `x`, `r`, `!e` and `!x`, the UI
     thread runs a full synchronous `collect_axe_status_data(include_full_snapshots=True)`
     (`axe.py:523`): ~39–53 ms warm, 280–350 ms cold. The async refresh scheduler already
     exists.
  2. **The stat-token optimization never fires.** The host rewrites `state.json` and
     `status.json` every second, so the TUI's refresh token always changes and the collector
     is never skipped. **Fix:** key the token on `change_token`, which heartbeat-only writes
     don't move.
  3. **Missed host death.** When the host dies, the files stop changing, so the TUI keeps
     showing "running" until unrelated churn happens, up to the 300 s sanity tick.
  4. **Heavy live tick.** It re-reads the whole proc log every second and isn't paused during
     navigation.

---

## 4. Low-severity bugs, doc drift, and polish

- **`sase service logs` is empty under a native unit.** It reads only the detached `host.log`
  (`service_handler.py:171–177`). **Fix:** read `journalctl --user -u sase.service` on Linux
  and `host.std{out,err}.log` on macOS.
  - The help text still says "Restart the detached service host" and "Show the detached
    service-host log".
  - There is no `-f/--follow` on `logs` or `proc logs`, and `NAME` has no help text.
- **`sase service status -j` always exits 0** (`service_handler.py:89–92`). `cli.md` and
  `configuration.md` document a non-zero exit when the host isn't running.
- **Docs promise env and shell semantics the code doesn't implement:**
  - `$$` → literal `$` is promised (schema, `configuration.md:4032`), but the host uses
    `os.path.expandvars`.
  - String commands are documented as `sh -c` but run through `/bin/sh -lc`
    (`host_support.py:51`). A login shell re-sources `~/.profile`, which can override the
    captured PATH or start an `ssh-agent` on every start.
- **`after:` is validated but never enforced by the host.**
  - Cycles still make procs unavailable, and cycle detection misses members reached through
    an already-finished node (PROBE).
  - Editing `after` restarts the proc, because it is part of `entry_signature`.
  - **Fix:** remove it from v1, or implement start ordering.
- **`restart: always` counts clean exits as failures.** It doubles backoff and alerts "crash-looping … exited
  with code 0" (PROBE). Either document it as systemd-like rate limiting, or give clean exits a
  flat delay.
- **Clock skew is unhandled.** Failures timestamped in the future stay in the crash-loop
  window. `persisted_or_current_status` compares wall clocks.
- **Per-proc log handling:**
  - `append_bounded_log` rewrites the whole file on every chunk once it is over the cap
    (`host_support.py:124–140`). Readers can see an empty file mid-rewrite.
  - Logs carry no timestamps and no "started pid N at T / exited code C" separators, which
    makes restart history unreadable.
  - The gateway writes nothing to its service log.
- **Quit & Stop Scheduler keeps it off until reboot.** The option writes a boot-scoped stop,
  and relaunching `ace` doesn't clear it. The modal doesn't say "until next boot", and the
  pill stays green.
- **Vocabulary leftovers:** "Add to AXE", "AXE config saved…", "axe config invalid:", "Axe
  Output" (the clipboard copies the legacy orchestrator log, not the selected service log),
  "Axe Agents", and the `bgcmd` wording in help. `axe_running` means "host running" in the app
  but "scheduler running" in `AxeAppliedConfigOutcome`.
- **`proc show` / `status` omit useful fields:** uptime, restart count, last exit and when,
  the current restart decision ("retrying in 12s"), and stop provenance (who stopped it, and
  until when). The data is already in the snapshot.

---

## 5. Plan conformance

| Plan requirement | Status |
|---|---|
| "a disabled receiver exiting 0 must not flap" | **Violated** (H1). Masked today by H2. |
| Crash-loop → "mark failed + notify once" | Notify never happens (H3). Nothing is marked failed. |
| "A failed service proc stays loud here and in notifications" | Not met (H3). |
| Host tests before default-on (concurrent start, stale lock, crash loop, …) | Present (sase-11y.11.4). But no test covers a `give_up` decision, which is how H1 escaped. |
| Consume status off-thread; nav p95 < 16 ms under restart storm | Status is read off-thread on the tick, but post-action loads are synchronous (M11). I found no evidence the p95 was measured under a storm. |
| Proc wire schema bump | Correctly *not* done (a bump would make old readers delete rows), but no unknown-field preservation replaced it (H5). |
| `service`/`svc:` query fields in core | Implemented in Python (`_proc_query.py`), not sase-core. Minor boundary deviation. |
| `after` ordering | Validated only (§4). |
| Env contract resolves provider CLIs and credentials | PATH works. SSH agent, `SASE_TMPDIR` and boot-time `pass` secrets do not (H6). |
| Unit design (Type=exec, KillMode=mixed, stable ExecStart, linger) | Matches exactly (LIVE). |
| Detach-scope escape | Works (LIVE: no agents in the host cgroup). The cost: ~18.8 k transient `sase-checks-*` scopes since 09-21 (~800/h) for checks that are ≤90 s. It's worth deciding whether short checks need a scope at all. |

---

## 6. Related open beads (so fixes don't duplicate)

- **`sase-14x`**: 39 duplicate `service run`/`scheduler run` copies on 2026-09-20. Root cause
  not diagnosed; not reproducing now. The only single-owner guarantee is the `host.lock` flock.
  A cheap guard would be for `sase service status`/`doctor` to warn when more than one
  `service run` exists for this `SASE_HOME`. M8 and M9 describe two real paths to a second
  owner of a child, though not of the host.
- **`sase-15q`**: `SASE_TMPDIR` missing from the host env (part of H6).
- **`sase-11w`**: Telegram inbound hardening (stale code, offsets, false success). This is
  where H2 belongs if it isn't done alongside H1.
- **`sase-153`**: bring back the full scheduler status view (`sase scheduler status --full`).
- **`sase-13x`**: four duplicate console-script resolvers, including the service host's.
- **`sase-13w`**: retire `bgcmd_legacy_slots`. There are also oneshot index edge cases: a CLI
  `proc run` can take an index the TUI reserved, and one overflow case drops an active row from
  the display (PROBE). These are low severity; fold them in when retiring the flag.

---

## 7. Larger extensions worth considering

These go beyond fixes. Each one is tied to evidence from this review, in line with the
corpus-before-mechanism decision.

- **E1. Last-known-good config plus a validation gate.** H4 already needs last-known-good in
  the host. Extend it so every config write path runs the Rust compose first and refuses (or
  warns) on a result that would stop running procs. Those write paths are the TUI scope-rail
  editor, `sase config` edits, and chezmoi-applied overlays via `sase doctor`. **Corpus:** H4's
  YAML-mid-edit scenario, which stops the gateway and receiver fleet-wide on athena.
- **E2. A durable service event stream.**
  - One append-only `~/.sase/service/events.jsonl` recording host start/stop, proc
    start/exit/restart/give-up, crash-loop begin/end, config reload, and last-known-good use.
  - It would back the H3 notifications, a "recent events" pane under each Services-tab node,
    `sase service proc show --events`, and fleet views.
  - Today this history lives only in 20 retained proc rows, which H1-style flapping flushes in
    40 s.
- **E3. An adoption-capable host (and in-place upgrade).**
  - At startup, adopt live daemon children from their proc rows (pid, pgid, argv match), then
    wait on and supervise them instead of relaunching.
  - This fixes M8 properly: no duplicate gateway or receiver after an unclean death, and it
    matters most on macOS.
  - It also enables `sase update` to re-exec the host in place (`execv` keeps the PID and
    children) without restarting the scheduler, gateway or receiver.
  - Combined with the H8 code fingerprint, the TUI could offer "restart stale procs" per proc.
- **E4. Per-proc cgroups and resource accounting.**
  - Run each daemon service proc in its own sub-cgroup: `Delegate=yes` on the unit plus a leaf
    per proc, or a `systemd-run --scope` per child.
  - **Stop semantics:** stopping the scheduler could SIGTERM its *whole* tree, including
    chops in their own sessions, with a grace period (the principled fix for H7). The
    alternative is instant SIGKILL at unit teardown.
  - **Accounting:** per-proc CPU and memory in the Services tab and `status`. The unit burns
    ~1.15 cores and peaks at 7 GB, and nobody can see which proc is responsible (compare
    `sase-14x`).
  - **Caps:** optional `MemoryHigh`/`CPUWeight` per proc.
- **E5. A heartbeat watchdog using the existing per-proc `status.json` contract.**
  - Add an optional `watchdog_seconds` per entry. If a proc that has reported `updated_at`
    goes silent longer than that, the host restarts it with the normal restart decision.
  - This is the cheapest "running but wedged" detection: no declarative healthcheck DSL, and
    it reuses a contract procs already have.
  - **Corpus:** `sase-11w`'s dead-for-a-day receiver and the scheduler's routine hangs. Worth
    doing only if one more wedge incident appears.
- **E6. Read-only service health off the box.**
  - The status wire was designed for "later the gateway's mobile API". Expose it as a
    read-only endpoint (`/api/v1/services`), a Telegram `/services` command, and a column in
    `sase machine status` for athena, apollo and the mac.
  - Together with H3's notifications, this closes the "athena rebooted, Telegram silently
    down" loop without sitting at a TUI. Keep mutation off the phone for now, as the plan
    decided.
- **E7 (not yet). Cross-machine singleton leases** for `telegram_receiver`, since Telegram
  allows one `getUpdates` consumer per bot. Today config discipline enforces it (athena overlay
  only). Only build a lease if a second consumer actually shows up.

---

## 8. Recommendations

### 8.1 Definitely make (priority order)

**P0: supervision correctness and visibility.** These are small, and together they form a
natural single epic.

1. **H1 + H2 together.**
   - The host honors `give_up`: a per-name given-up record, cleared on signature change or an
     explicit start/restart/enable.
   - The receiver exits non-zero (retryable) on missing credentials and 0 only when disabled.
   - Scenario tests: `on-failure` + exit 0 stays down; `never` stays down; `proc start`
     revives both; the receiver's missing-credentials exit backs off and recovers.
2. **H3: make failures loud.**
   - The host notifies on `decision.notify` and on `give_up` while desired running (reuse the
     orchestrator's `_surface_crash_loop` pattern).
   - Make the Rust crash-loop flag sticky until a healthy run.
   - The TUI treats `backoff`, `crash_loop`, and `exited` while desired running as failures,
     and renders `summary` ("retrying in Ns").
   - Replace the fake `failed` fixtures with real wire states.
3. **H4: last-known-good config.**
   - Exit observation no longer depends on config, and `_stop_child` no longer reloads it.
   - Rust treats errored layers as fatal and allow-lists layer kinds.
   - The TUI shows `SVC ?` with the diagnostic instead of `SVC 0/0`.
4. **H6.1 + H6.2: env hygiene.**
   - Drop dead `SSH_AUTH_SOCK`/`SSH_AGENT_PID` at load, and don't capture `/tmp/ssh-*`
     session sockets.
   - Exclude volatile keys from `init --check`.
   - Fix `docs/init.md`.
   - Then re-run `sase service init --yes` on athena from a login shell (owner action).

**P1: data safety and graceful lifecycle.**

5. **H5: preserve unknown fields.** Flatten `extra` in proc (and state) wires. Keep
   newer-schema rows verbatim. Add the Rust retention fallback via origin/tag.
6. **H7: graceful stops.**
   - Routines forward SIGTERM to chop process groups with a bounded wait.
   - The host stops children in parallel.
   - Set `TimeoutStopSec` above the stop budget.
   - Run `systemctl` with `--no-block` plus polling, or a larger timeout.
7. **H8: consistent updates.** `sase update` restarts the host (as the TUI does), and the
   heartbeat carries a code fingerprint that `status` and the TUI show as "stale code".
8. **M1–M4: TUI safety.**
   - Confirm a host stop from `!x`.
   - `!e` only on the Services tab, and confirmed.
   - On the Services tab, `!x` always toggles the host.
   - `x` stops any proc whose desired state is running.
   - Guard off-tab `_refresh_axe_display`.
9. **M5–M7: control-plane hardening.**
   - Never prune stops with an unknown boot id, and don't cache `None`.
   - Quarantine wrong-shape `state.json`.
   - A restart generation instead of the 0.5 s stop/clear dance, with CLI wait-and-confirm.
   - Signal only when the lock is held and the boot id matches.
10. **M8–M10: startup and lifecycle.**
    - Settle stale daemon rows and kill orphan pgids at startup.
    - `init --yes` restarts a changed active unit and hands over a detached host.
    - A distinct "already running" exit code in `RestartPreventExitStatus`.
    - Detached host cwd and proc default cwd = `$HOME`.

**P2: polish.** These are cheap; batch them into a small phase.

11. **M11 perf:**
    - Run post-action refreshes async.
    - Key the refresh token on `change_token`.
    - Schedule a refresh when the snapshot's freshness window expires.
    - Don't re-read the whole log every second.
12. **§4 items:**
    - `service logs` reads the journal or launchd logs.
    - `status -j` exit code.
    - `-f/--follow` on logs.
    - Timestamped per-proc logs with run separators.
    - Align the `$$` and `sh -c` docs with the code (or the code with the docs).
    - Drop or implement `after`.
    - Help text wording ("detached").
    - Richer `proc show` (uptime, restarts, last exit, restart decision, stop provenance).
    - Vocabulary cleanup.
    - The "until next boot" wording in the quit modal.
13. **`sase-15q`:** capture the `SASE_*` path overrides (H6.3).

### 8.2 Larger extensions to consider

- **E1, last-known-good plus a config validation gate:** strongest candidate; H4 already pays
  for half of it.
- **E3, adoption-capable host:** fixes macOS and detached duplicates properly and unlocks
  zero-downtime updates.
- **E2, service event stream:** the substrate for notifications, history, and the fleet view.
- **E6, read-only service health over gateway, Telegram, and `sase machine status`:** closes
  the "silently down after reboot" loop.
- **E4, per-proc cgroups and accounting:** consider once H7's routine-level fix lands and if
  the load questions (`sase-14x`) persist.
- **E5, heartbeat watchdog:** only after one more wedge incident (corpus-before-mechanism).
