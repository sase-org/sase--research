# SASE services after sase-11y: bugs, fixes, and extensions (consolidated)

**Lead researcher:** consolidation of swarm `research.27` · **Date:** 2026-09-22 ·
**Scope:** the service host, service procs, oneshots, platform units, the captured
environment contract, and the Services tab shipped by epic `sase-11y` and its child epic
`sase-11y.11`.

**Inputs:**

- [`__cld`](sase_services_post_landing_hardening__cld.md): the deepest code review, with
  live observations on athena.
- [`__mus`](sase_services_post_landing_hardening__mus.md): CLI and UX gaps, with timings.
- [`__gem`](sase_services_post_landing_hardening__gem.md): defect list and a roadmap of
  larger extensions.

**Lead verification:** I re-checked every claim this report relies on against sase master
`d6a64c6b6`, sase-core `c5186cc` (v0.34.71) and sase-telegram `76431fc`. I also checked
the live host on athena at about 08:45 EDT and did a read-only check of apollo.

**Evidence labels:**

- **LIVE**: observed on a running machine today.
- **CODE**: confirmed by reading the cited lines.
- **PROBE**: reproduced by a researcher's throwaway script. I did not re-run these, but
  the code I read agrees with each one.

---

## 0. Bottom line

The architecture shipped as designed, and nothing below needs a redesign. The live
systemd unit matches the plan: `Type=exec`, a stable ExecStart, `KillMode=mixed`, and
linger on. It survived today's reboot. The host costs about 1% CPU, and detached agents
really do leave the host cgroup. Apollo is healthy: one host, gateway and scheduler
running, and the receiver correctly disabled.

The problems are in **supervision semantics, failure visibility, and the environment
contract**. Four of them need attention first:

1. **The host overrides its own "give up" decisions.** Procs the restart policy says to
   leave down get relaunched every ~2 s, with no backoff. That is the only reason the
   Telegram receiver comes back after a reboot.
2. **Restarts are unreliable.** `sase scheduler restart` is effectively a no-op, and
   every other restart path is a timing-dependent stop/sleep/clear sequence.
3. **Failures are silent.** The crash-loop `notify` bit is never read. The crash-loop
   flag turns itself off in steady state. The TUI's list of failure states doesn't match
   the states the Rust core actually emits.
4. **The captured environment is not reboot-safe or context-safe.** The running host
   still hands every child a dead SSH agent socket. `sase service init --yes` run from an
   agent or ACE shell would freeze that shell's feature flags into the 24/7 host.

Most fixes are small and local. §6 lists what to do, in order.

---

## 1. What changed since the researchers looked (read this first)

- **`ba71aa524` (08:23 today) fixed the dead `SSH_AUTH_SOCK` in code, but not on the
  running host.**
  - `load_service_environment` now drops a captured socket that isn't live.
  - The host has been running since 07:42, before that commit. At 08:44 the gateway
    (pid 1523548), the scheduler (pid 2018178) and the receiver (pid 1523656) still had
    `SSH_AUTH_SOCK=/tmp/ssh-bd1YBG80VDga/agent.13572`, and that path no longer exists.
    The host's own inherited socket (`/run/user/1000/openssh_agent`) is live. (LIVE)
  - **So the host needs one restart to pick the fix up.** That restart is itself exposed
    to §3.7: chops get SIGKILLed, and `sase service restart` can report a false timeout.
    Do it at a quiet moment.
- **sase-telegram already supports a boot-safe token file** (`~/.sase/telegram_bot_token`,
  mode 600). The receiver's own error message names it. Athena doesn't have one, which is
  why the receiver can't start until gpg is usable after login. The receiver log holds
  101 "credentials unavailable" exits. (LIVE)
- **The proc store's service-marker stripping is gone for now.** All 21 retained
  `service:telegram_receiver` rows carry the `service` block again (LIVE). The root cause
  (§3.9) is still there for the next additive field.

---

## 2. Where the reports disagreed, and how I resolved it

| Question | Reports said | Resolution |
|---|---|---|
| Is `sase scheduler restart` broken? | gem: yes, a live-verified no-op. cld and mus missed it. | **Confirmed (CODE).** `scheduler_handler.py:72–77` passes `delay=0.0`, so the stop marker is cleared microseconds after it is written, before the nudged host reads state. |
| Does the 0.5 s stop/clear restart "frequently" fail? | mus: yes, because the host reconciles only every ~1 s. | **Overstated.** SIGUSR1 wakes the loop immediately, and a warm `load_service_config` takes about 4 ms (LIVE timing). The restart usually works: cld saw six requested scheduler restarts today. It fails when the host is blocked in `_stop_child` (up to `stop_timeout` + 5 s) or in `handover_scheduler` (cld M6). Both the 0.0 s case and the blocked-host case point to the same fix: a restart generation (§3.4). |
| How bad is `append_bounded_log`? | gem: "catastrophic", about 100 MB/s. cld: low. | **Latent, medium.** Once a log reaches the cap, every `read1()` chunk rewrites the whole 2 MiB file, and readers can briefly see an empty file. Today's logs are far below the cap: receiver 120 KB, gateway 0 B, scheduler 100 B (LIVE). Cheap to fix; not urgent. |
| Stale per-proc `status.json` | gem: medium bug. mus: write-only infrastructure. | **Latent.** Nothing writes `status.json`: no file exists on athena or apollo, and there is no writer in sase or sase-telegram. Fix the staleness when the first producer lands (E6), or remove the read path. |
| Does anything honor `after:`? | mus: unsure whether the composer sorts. gem and cld: unenforced. | **Unenforced (CODE).** The Rust composer keys entries in a `BTreeMap` (alphabetical), and `host.py` never reads `after`. No builtin, plugin or athena proc sets it. Fix the docs now and implement ordering only when a consumer appears. |
| Should `enable` clear a boot stop? | gem: a bug; `enable` must clear it. | **Not a behavior bug.** This matches systemd, where enable is not start. The defect is that the CLI says "enabled" and exits 0 without mentioning the stop that still applies. Handled under honest outcomes (§4.1). |
| Stuck child launches a duplicate | gem: high. | **Real but rare (CODE).** A SIGKILLed process group has to survive 5 s, which in practice means D-state. The parallel-stop rewrite (§3.7) fixes it: keep tracking a child until it is reaped. |
| Restart transport | gem: a Unix-socket RPC control plane. cld: a restart generation in `state.json`. | **Use the generation.** It fixes the edge-trigger problem inside the existing file control plane, and it gives the host an "explicit start" signal that §3.1 needs anyway. A socket control plane has no corpus yet (see `corpus-before-mechanism`). |
| Health checks | mus and gem: a declarative `healthcheck` DSL, "the biggest reliability upgrade". cld: a heartbeat watchdog, only after another wedge. | **Take cld's position** (E6). Reuse the per-proc status contract before adding a DSL. |

---

## 3. Critical and high-severity findings

### 3.1 The host relaunches procs it decided to give up on (critical) — CODE, LIVE, PROBE

- **What happens:**
  - `_settle_exit` (`src/sase/service/host.py:202–213`) queues a pending restart only
    when `decision.action == "restart"`.
  - On `give_up` (`restart: never`, or a clean exit under `on-failure`), the name ends up
    in neither `_children` nor `_pending`.
  - Loop 3 of `_reconcile_desired` (`host.py:252–256`) then relaunches it on the next 1 s
    tick. `_desired_running` (`:258–265`) never consults the restart decision.
  - Spawn failures under `never` go through the same path (`_record_spawn_failure`,
    `:442–465`).
- **Live proof:** 17 consecutive `service:telegram_receiver` rows, all `success/exit 0`,
  about 2 s apart, from 10:35:23Z to 10:36:06Z. (LIVE, `~/.sase/procs/procs.jsonl`)
- **Why the tests missed it:** the host scenario tests
  (`tests/service/test_service_host_scenarios.py`) use only a failing child. No host test
  covers `give_up`.
- **Side effects:**
  - Each relaunch resets `restarts` to 0, so the Services pill stays mostly green.
  - The retained 20-row history is flushed within about 40 s.
- **Fix:**
  - Keep a per-name given-up record, keyed by the entry signature, and skip those names in
    loop 3.
  - Clear the record on a signature change or an explicit start/restart/enable (§3.4).
  - Add scenario tests for `on-failure` + exit 0 and for `never` + exit 1.

### 3.2 The Telegram receiver reports "not ready yet" as success — CODE, LIVE

- **Where:** `sase_tg_inbound.py:5008–5014` returns `0` both for "Telegram disabled" and
  for "credentials unavailable". The plugin declares `restart: on-failure` with
  `success_exit_codes: [0]`.
- **Why the receiver works today:** at boot, `pass`/gpg can't decrypt until the user
  session is usable, so the receiver exits 0. Only the §3.1 bug brings it back.
- **The trap:** fixing §3.1 alone leaves Telegram down after every reboot.
- **Fix:**
  - Exit 0 only for "disabled".
  - Exit with a retryable non-zero code for missing credentials, for example `75`
    (EX_TEMPFAIL), so the capped backoff retries it.
  - Release sase-telegram before, or together with, the host change.
  - **Owner action:** create `~/.sase/telegram_bot_token` (mode 600) on athena, so an
    unattended reboot doesn't depend on gpg-agent at all.

### 3.3 Service failures are not loud anywhere — CODE, PROBE

Four defects add up to the invisible failure the plan explicitly forbade ("a failed
service proc stays loud"):

1. **`notify` is a dead letter.** Rust sets `notify=true` once per crash-loop episode.
   Python copies it into `status.json` (`src/sase/service/status.py:603`), and nothing
   reads it. The old orchestrator's `_surface_crash_loop` persisted an error and sent a
   notification; the host has no equivalent. Nothing notifies on `give_up` of a
   desired-running proc either.
2. **The crash-loop flag switches itself off.**
   - `crash_loop = failures in the last 60 s >= 3` (`sase-core …/service/restart.rs:271–279`).
   - Backoff caps at 60 s (`restart.rs:7–11`), so once it is capped, failures land more
     than 60 s apart.
   - A proc that fails forever therefore reads `crash_loop` only for failures 3–7, then
     plain `backoff` from then on.
3. **The TUI's failure vocabulary doesn't match the wire.**
   - The TUI treats only `{"failed","error"}` as failure (`_service_health.py:14` and
     four widgets).
   - Rust emits `running`, `unavailable`, `disabled`, `stopped`, `crash_loop`, `backoff`
     and `exited`.
   - Test fixtures use a made-up `state="failed"`, so the tests pass while the real
     states render dim.
4. **The CLI tables hide the evidence.** `status`, `proc list` and `proc show` never
   render `restarts`, `last_exit`, the restart decision ("retrying in 12s"), or stop
   provenance, although all of it is already in the snapshot. (mus B5, gem 4.2)

**Fix:**

- The host raises a durable notification on `decision.notify` and on `give_up` while the
  proc is desired running. Reuse the orchestrator's error-file plus
  `notify_workflow_complete` path.
- Make crash-loop sticky until a healthy run, for example
  `recent >= threshold || (alert_sent && consecutive_failures >= threshold)`.
- Treat `backoff`, `crash_loop`, and `exited`-while-desired-running as failure styles,
  and render `summary` as a chip.
- Switch the fixtures to real wire states.

### 3.4 Restarts are edge-triggered commands built on level-triggered state — CODE, LIVE (gem)

- **What happens:**
  - `restart_service_proc` (`src/sase/service/actions.py:82–104`) writes a stop marker,
    nudges, sleeps `delay`, clears the marker, and nudges again.
  - `sase scheduler restart` passes `delay=0.0`. That delay was carried over unchanged
    from the pre-service record/clear code. gem ran it live and the PID did not change.
  - Even at 0.5 s, the restart is silently lost whenever the host is blocked (§2).
  - No caller waits for or reports the new PID.
  - `sase update` reports `status="restarted"` although it only *requested* a restart
    (`src/sase/main/update_restart.py:37–77`).
- **Fix:**
  - Add a per-proc **restart generation** (or token) to `state.json` in sase-core. The
    host consumes it by stopping the old child, launching a new one, and recording the
    generation it completed.
  - The CLI polls for that generation and prints `old pid → new pid`. It reports a
    timeout honestly and exits non-zero.
  - The same generation doubles as the "explicit start" signal that clears §3.1's
    given-up record.
  - Delete the `delay` knobs.

### 3.5 A bad config blinds the host and misleads the TUI — CODE, PROBE (cld H4)

- **The host stops working:** `_reconcile_once` (`host.py:108–124`) loads the config
  first. When that raises, nothing after it runs: no exit observation, no restarts, no
  stops. The fallback status write reloads the config, fails again, and swallows the
  error, so `status.json` goes stale.
- **The TUI shows health:** the snapshot error becomes `service_status=None`, and
  `derive_service_health(None)` returns a **healthy `SVC 0/0`**
  (`_service_health.py:43–46`). A test locks that behavior in.
- **Broken overlays are silently ignored:** the layer wire has an `error` field
  (`sase-core …/config/wire.rs:153–154`), but `compose_service_config` never reads it
  (`…/service/config.rs:160–260`).
  - A machine overlay saved with a YAML error mid-edit composes as if the overlay didn't
    exist.
  - `gateway` and `telegram_receiver` then fall back to `enabled: false`, and the host
    **stops them** within 1 s (cld PROBE).
- **Shutdown can abort early:** `_stop_child` reloads the config just to settle the exit
  (`host.py:501–503`). A fatal config during shutdown aborts `_stop_all_children` after
  the first child.
- **Fix:**
  - Keep a **last-known-good composition** in the host, and publish the diagnostic in the
    heartbeat and snapshot. This is systemd's "old unit until daemon-reload succeeds"
    model.
  - Observe exits without needing the config (`running.entry` already has what
    `_settle_exit` needs).
  - In Rust, treat an errored layer as fatal, and allow-list the layer kinds.
  - The TUI renders `SVC ?` with the reason.

### 3.6 The environment contract is neither reboot-safe nor context-safe — LIVE, CODE

1. **Dead SSH agent socket.** Fixed in code by `ba71aa524` but still live on athena
   (§1).
   - Remaining work: stop capturing session-scoped `/tmp/ssh-*` sockets at all.
   - Correct the claim in `docs/init.md` that the host falls back to the manager's agent;
     that is only true after the fix, and only once the host restarts.
2. **`init --check` never settles.**
   - `environment_files_match` (`env.py:191–196`) requires exact equality, including
     `PATH` and the per-shell SSH variables.
   - So `sase service init --check` reports `needs_attention` from every shell (LIVE: it
     wants to rewrite `~/.sase/service/env`).
   - Its advice, "run `sase service init --yes`", then leads straight to item 3.
3. **New: the service env can pin feature flags for the host's lifetime.**
   - `capture_service_environment` deliberately includes `SASE_FEATURE_FLAGS`
     (`env.py:54`), and the host applies captured values with `override_existing=True`
     (`host_lifecycle.py:25`).
   - Agent and ACE shells export a resolved flag snapshot. This agent shell has one
     (352 chars), and the host has none today (LIVE).
   - So a single `init --yes` from an agent or ACE context would freeze those flags into
     the scheduler and every agent it launches, overriding later `sase flag
     enable/disable` until the next `init`.
   - This is `sase-11c`'s pinning bug, moved into the longest-lived process on the
     machine. Only a drift *warning* exists (`platform.py:496–501`).
   - **Fix:** don't capture `SASE_FEATURE_FLAGS`, since the host should resolve flags
     from saved state. Record the host as an affected surface on `sase-11c`.
4. **Profile-exported SASE settings never reach the host.** `SASE_TMPDIR` and the other
   `SASE_*` path overrides are missing, so housekeeping reaps the wrong root (`sase-15q`:
   67 GiB unreaped on apollo). gem's configurable passthrough
   (`service.capture_env_names`, plus proxies, CA bundles, and locale) is the general
   form of this fix. It needs a schema change, because `service:` currently accepts only
   `procs` (`config.rs`).
5. **Boot-before-login secrets.** Have `init --check` and `doctor` flag secrets that
   resolve only through agent-backed tools (`pass`/gpg), and point to the file-based
   alternatives (§3.2).

**Fix, together:**

- Exclude volatile keys (the SSH variables and `SASE_FEATURE_FLAGS`) from the currency
  check and normalize `PATH`.
- Warn, or refuse without `--force`, when `init --yes` runs from an agent or ACE context
  (`SASE_AGENT*` is set, or a workspace venv is on `PATH`).
- Capture an allow-list of `SASE_*` path overrides.

### 3.7 Stops are neither graceful nor bounded — LIVE, CODE (cld H7, mus B4, gem 9 and 11)

- **Chops get SIGKILLed.**
  - Chops start in their own session (`chop_script_runner.py:209`), and routines only set
    `_running=False` on SIGTERM. So the host's `killpg` of the scheduler never reaches
    in-flight chops.
  - When the host exits, `KillMode=mixed` SIGKILLs them. The journal shows
    `sase_job_artifa` at 06:38:43, and `sase_job_commen`, `git` and `ssh` at 07:17:18.
    (LIVE)
- **Stops are sequential and can block for an hour.**
  - `_stop_all_children` stops children one at a time, each for up to `stop_timeout`
    (the schema allows up to 3600 s) plus a 5 s kill wait.
  - During an inline stop in `_reconcile_desired`, the host doesn't heartbeat (the TUI
    marks it stale after 15 s) and can't honor SIGTERM.
  - The unit sets no `TimeoutStopSec`.
- **`sase service restart` reports false failures.** `systemctl` runs with `timeout=10`
  (`platform_runner.py`), and `systemctl --user restart` blocks through a stop that takes
  10–11 s (LIVE journal). So the command can report a timeout even when the restart
  succeeds.
- **A stuck child gets a duplicate.** If a child survives SIGKILL, the host drops it from
  `_children` and launches a second instance in the same pass (gem Bug 9).
- **Fix:**
  - Routines forward SIGTERM to chop process groups and wait a bounded time.
  - The host signals all children first, then waits up to the largest `stop_timeout`,
    heartbeating while it waits.
  - Keep a child tracked (`terminating`) until it is reaped.
  - Cap the effective stop wait, and set `TimeoutStopSec` above the total budget.
  - Run `systemctl` with `--no-block` and poll the heartbeat, or use a timeout above the
    stop budget.

### 3.8 `sase update` leaves the host and gateway on old code — CODE (cld H8)

- **CLI path:** `update_restart.py` restarts only the `scheduler` proc (and only
  "requests" it; §3.4). The host and gateway keep pre-update code.
- **Mixed versions:** with athena's editable install, the long-lived host lazily imports
  new modules into an old process.
- **The two update paths disagree:** the TUI's update path restarts the whole host
  (`axe_display/_refresh_full.py:125`).
- **Staleness is invisible:** the heartbeat's `sase_version` comes from dist-info, which
  reads `0.17.1` for every git SHA.
- **Fix:**
  - The CLI restarts the host, matching the TUI.
  - The heartbeat records a code fingerprint (editable git SHAs plus the `sase_core_rs`
    version), and `status` and the TUI show a "stale code" chip.
  - Coordinate with the in-progress `sase-158.6.3` ("Fix the update handlers, managed
    rows, and docs"), which touches the same handlers.

### 3.9 Proc-store rewrites delete fields they don't understand — CODE, PROBE (cld H5)

- **The cause:** `ProcWire`, `ProcServiceWire` and `XpromptProcMetaWire`
  (`sase-core …/procs/wire.rs`) have no `#[serde(flatten)]` catch-all, and every writer
  rewrites `procs.jsonl` in full.
  - So any process running an older `sase_core_rs` strips additive fields from *every*
    row.
  - Rows with a newer `schema_version` are dropped.
  - A test asserts the stripping.
- **What landing did:** the fix treated the read side only. Rust retention still
  identifies service rows by `proc.service` alone, and `ProcUpdateWire` can't re-attach a
  stripped block.
- **Why it still matters:** the symptom is gone today (§1), but this is the general
  hazard for every future additive field.
- **Fix:**
  - Add a flatten `extra` map to the proc and service-state wires.
  - Keep newer-schema lines verbatim on rewrite.
  - Give retention the same origin/tag fallback.

---

## 4. Medium-severity findings

### 4.1 CLI outcomes aren't honest (mus B2 and B3, gem Bugs 4 and 5, cld §4)

- **`proc start` on a disabled proc reports success.** `_require_startable` checks only
  `available` (`actions.py:153–160`), so the CLI prints "requested … start" and nothing
  runs. The TUI does refuse. **Fix:** error with "run `sase service proc enable` first",
  or add `--enable`.
- **`proc enable` leaves a boot stop in place without saying so.** **Fix:** keep the
  systemd-like behavior, but print "enabled; still stopped until next boot — run
  `proc start`", or add `--now`.
- **Start, stop and enable ignore `outcome.nudged` and `outcome.changed`.**
  - When the host is down, the CLI still says "requested" and exits 0.
  - A no-op repeat looks the same as a real transition.
  - The enable handler returns `0 if outcome.changed else 0` (`service_handler.py`).
- **`sase service status` takes 4.3 s** (LIVE; `proc list` takes 0.68 s), because it runs
  a full `service_init_plan(force=True)` on every call (`service_handler.py:107`).
  **Fix:** move that audit to `init` and `doctor`.
- **`status -j` always exits 0,** and so does `proc list`. Text `status` exits 1 when the
  host is down. **Fix:** document one exit-code contract in `cli.md` and follow it.

### 4.2 Operators can't see what they need (all three reports)

- **`sase service logs` prints nothing and exits 0 under the systemd unit** (LIVE). It
  reads only the detached-mode `host.log`, which doesn't exist here. **Fix:** fall back to
  `journalctl --user -u sase.service` on Linux and `host.std{out,err}.log` on macOS.
  - The help text still says "detached".
  - `logs` and `proc logs` have no `-f/--follow`.
- **Orphan procs are invisible.** `snapshot.orphans` is built, but only
  `_scheduler_desired_state.py` reads it. The CLI tables and the Services tab never
  render orphans, so a renamed or removed proc that is still running can't be seen or
  stopped. (mus B7, gem 3)
- **`proc show` is missing fields:** uptime, restart count, last exit and when, the
  current restart decision, stop provenance, and the description.
- **Per-proc logs have no timestamps and no "started pid N / exited code C"
  separators,** so restart history can't be read from the log.

### 4.3 TUI safety (cld M1–M4, mus B8 and B9, gem 4.7)

- **`!x` off the Services tab stops the whole host with no confirmation**
  (`actions/axe.py:141–150`). That takes down the gateway (the phone loses its API) and
  the receiver.
- **`!e` has no tab check** (`axe.py:183–187`). It writes persistent machine policy
  against `_axe_service_selection`, which is stale once you leave the tab. A harness
  disabled `gateway` from the Agents tab (cld PROBE).
- **`x` on a `backoff` or `crash_loop` proc does nothing.** The code runs "start"
  whenever `state != "running"` (`axe.py:391`). The only way to quiet a loop is `!e`,
  which is a persistent disable. **Fix:** stop whenever `desired == "running"`.
- **Actions are dropped silently while a worker is busy** (`axe.py:419–421`). **Fix:**
  show a toast.
- **The Services help section doesn't document `r`** (restart). `r` is overloaded in
  `actions/base.py:47–61`.
- **`!x` on a finished oneshot dismisses it without confirmation** (cld M3).

### 4.4 Control-plane and lifecycle hardening (cld M5–M10, gem Bug 10)

- **An unknown boot id deletes every stop.** `prune_expired_stops`
  (`sase-core …/service/state.rs:367–386`) runs on every mutation, including the 1 s
  heartbeat. `current_boot_id()` is `@cache`d, so a single `None` lasts the host's
  lifetime; on macOS the probe is a 0.5 s-timeout `sysctl` run at login. **Fix:** never
  prune with an unknown boot id, and don't cache `None`.
- **A wrong-shape `state.json`** (`[]`, `null`, or `{}` with no `schema_version`) wedges
  every read and write, with no quarantine.
- **Signals go to the PID without an ownership check.** `nudge_service_host` and
  `stop_service_host` signal `record.pid` whenever that PID is alive
  (`control.py:147–156`), without checking `lock_held` or the boot id. After an unclean
  death and PID reuse, SIGUSR1 (whose default action is terminate) hits an unrelated
  process.
- **An unclean host death orphans daemon children.** In detached mode, and always on
  macOS, the next host starts a second gateway (which crash-loops on port 7629) and a
  second `getUpdates` consumer. Stale daemon rows are never settled.
- **`init --yes` never restarts an active unit** after its definition or env changes
  (`platform.py:229–250`), yet reports success.
- **A detached host inherits the caller's `cwd` and environment.** Procs without a `cwd`
  run from `Path.cwd()` (`host.py:298`), possibly an ephemeral workspace. **Fix:** use
  `$HOME` and the canonical executable.
- **A detached lock holder makes the unit loop.** If a detached host holds the lock, the
  unit's `sase service run` exits 1 every 5 s. **Fix:** give "already running" its own
  exit code, and list it in `RestartPreventExitStatus` and in launchd `SuccessfulExit`.

### 4.5 Performance (cld M11, verified)

- **The host rewrites `state.json` and `status.json` about once a second** (LIVE: both
  mtimes advance every second). So the TUI's stat-token optimization never skips a
  collection. **Fix:** key the TUI on `change_token`, and write `status.json` only when
  it changes.
- **Every `x`, `r`, `!e` and `!x` runs a synchronous full status collection** on the UI
  thread: 40–50 ms warm and 280–350 ms cold (cld PROBE). **Fix:** use the existing async
  refresh scheduler.
- **The live tick re-reads the whole proc log every second.**
- **A dead host is noticed only by the 300 s sanity tick.**

---

## 5. Low-severity findings and polish

- **Bounded logs rewrite the whole file at the cap** (§2). **Fix:** rotate `.log` →
  `.log.1`, or use high/low-water truncation aligned to a newline.
- **`after:` is validated but not enforced.** Change `configuration.md` from "Start
  ordering only" to "validated; not yet enforced". Editing `after` still restarts the
  proc, because it is part of the signature.
- **Docs promise shell semantics the code doesn't have:**
  - `$$` → literal `$` is promised, but the host uses `os.path.expandvars`.
  - String commands are documented as `sh -c` but run through `/bin/sh -lc`, which
    re-sources the profile.
- **`restart: always` counts clean exits as failures:** backoff doubles and it alerts
  "crash-looping … exit 0". Document this, or give clean exits a flat delay.
- **The per-proc `status.json` contract has no producer.** Either wire one up (E6) with
  staleness filtering (`updated_at < started_at` → ignore; unlink on launch), or remove
  it.
- **Quit & Stop Scheduler writes a boot-scoped stop,** but the modal doesn't say "until
  next boot".
- **Vocabulary leftovers:** "Add to AXE", "axe config invalid:", "Axe Output" (which
  copies the legacy orchestrator log), and `axe_running` meaning "host running".
- **Transient scopes:** about 800 `sase-checks-*` scopes per hour for checks that take
  90 s or less. Decide whether short checks need a scope at all.

**Related open beads, so fixes don't duplicate:**

- `sase-11w`: receiver hardening. §3.2 belongs there if it isn't done with §3.1.
- `sase-15q`: `SASE_TMPDIR` (§3.6.4).
- `sase-11c`: pinned feature flags (§3.6.3).
- `sase-14x`: 39 duplicate hosts on 09-20. Undiagnosed, and not reproducing on athena or
  apollo today. A cheap guard would be for `status`/`doctor` to warn when more than one
  `service run` exists for this `SASE_HOME`.
- `sase-158.6.3`: update handlers (§3.8).
- `sase-13x`: console-script resolvers.
- `sase-13w`: retire the legacy bgcmd slots.
- `sase-153`: `scheduler status --full`.

---

## 6. Recommendations

### 6.1 Definitely make (priority order)

**P0: supervision correctness and visibility.** These are small and fit naturally in one
epic.

1. **§3.1 + §3.2 together.**
   - The host honors `give_up`.
   - The receiver exits non-zero and retryable on missing credentials.
   - Host scenario tests: `on-failure`+0 stays down, `never` stays down, an explicit start
     revives both, and a credential outage backs off and then recovers.
2. **§3.4: a restart generation in sase-core state.**
   - Fixes `sase scheduler restart` and the busy-host loss.
   - Gives §3.1 its explicit-start signal.
   - The CLI waits for and prints the new PID.
3. **§3.3: loud failures.**
   - The host notifies on `notify` and on `give_up`.
   - Crash-loop is sticky until a healthy run.
   - The TUI uses the real wire states and shows `summary`.
   - The CLI shows restarts and last exit.
4. **§3.5: a last-known-good config.**
   - Exit observation no longer depends on the config.
   - Errored layers are fatal in Rust.
   - The TUI shows `SVC ?` instead of `SVC 0/0`.
5. **§3.6: environment hygiene.**
   - Stop capturing `SASE_FEATURE_FLAGS`.
   - Exclude volatile keys from `--check`.
   - Warn on (or refuse) agent/ACE-context `init --yes`.
   - Capture an allow-list of `SASE_*` path overrides (closes `sase-15q`).

**P1: graceful lifecycle and honest operations.**

6. **§3.7 graceful, bounded, parallel stops:**
   - SIGTERM forwarding to chops.
   - Tracking until reaped.
   - `TimeoutStopSec`.
   - Non-blocking `systemctl`.
7. **§3.8 consistent updates:** host restart, a code fingerprint, and a stale-code chip,
   coordinated with `sase-158.6.3`.
8. **§4.1 honest CLI outcomes,** including taking the init audit out of `status`
   (4.3 s → under 1 s).
9. **§4.2 observability:**
   - `service logs` falls back to the journal or launchd logs.
   - Orphans rendered in the CLI and the tab.
   - A fuller `proc show`.
   - `--follow`.
   - Timestamped run separators.
10. **§4.3 TUI safety:**
    - Confirm a host stop from `!x`.
    - `!e` only on the Services tab, and confirmed.
    - `x` stops any desired-running proc.
    - A busy toast.
    - Help documents `r`.
11. **§4.4 hardening:**
    - The boot-id prune guard.
    - `state.json` quarantine.
    - A lock-held check before signaling.
    - Settle and kill orphans at startup.
    - `init --yes` restarts a changed unit.
    - A distinct exit code for "already running".
    - `$HOME` as the detached cwd.

**P2: hygiene.**

12. **§3.9** proc-wire `extra` preservation.
13. **§4.5** performance.
14. **§5** polish, as one small batch.

**Owner actions today (no code needed):**

- Create `~/.sase/telegram_bot_token` (mode 600) on athena.
- Restart the host once, at a quiet moment, to load `ba71aa524`. Until §3.7 lands, expect
  in-flight chops to be killed.
- Run `sase service init --yes` only from a login shell, never from an agent or ACE
  shell.

### 6.2 Larger extensions worth considering

- **E1. Last-known-good config plus a validation gate** (cld). §3.5 already pays for half
  of it.
  - Every config write path runs the Rust compose first. Those paths are the TUI config
    editor, `sase config` edits, and chezmoi-applied overlays via `doctor`.
  - It refuses or warns when the result would stop running procs.
  - This is the strongest candidate.
- **E2. A durable service event stream,** `~/.sase/service/events.jsonl` (cld).
  - Records host start/stop, proc start/exit/restart/give-up, crash-loop begin/end,
    config reload, and last-known-good use.
  - It becomes the substrate for §3.3 notifications, a per-node "recent events" pane,
    `proc show --events`, and fleet views.
  - Today this history lives in 20 retained rows that §3.1-style flapping flushes in
    40 s.
- **E3. An adoption-capable host with in-place re-exec** (cld E3, mus E4).
  - At startup, adopt live daemon children from their proc rows (matching pid, pgid and
    argv) instead of relaunching them. This fixes macOS and detached-mode duplicates
    properly.
  - `sase update` can then `execv` the host without restarting the scheduler, gateway or
    receiver.
  - Combined with §3.8's fingerprint, this gives per-proc "restart stale code".
- **E4. Read-only service health off the box** (cld E6, gem 5.4, mus E5).
  - Expose it through a gateway endpoint (`/api/v1/services`), a Telegram `/services`
    command, and a column in `sase machine status` for athena, apollo and the mac.
  - Together with §3.3, this closes the "rebooted, Telegram silently down" loop without a
    TUI.
  - Keep mutation off the phone for now.
- **E5. Per-proc cgroups, accounting and limits** (cld E4, gem 5.3, mus E3).
  - Use `Delegate=yes` with a leaf per proc, or a `systemd-run --scope` per child.
  - Stopping the scheduler could then terminate its whole tree gracefully.
  - The Services tab could show per-proc CPU and memory. The unit averages about 1.15
    cores with 4–7 GB peaks, and nobody can see which proc is responsible.
  - Optional `MemoryHigh`/`CPUWeight`.
  - Worth it once §3.7's routine-level fix lands, if load questions (`sase-14x`) persist.
- **E6. Wedge detection via a heartbeat watchdog, not a healthcheck DSL** (cld E5 over
  mus E1 and gem 5.1).
  - Add an optional `watchdog_seconds` that restarts a proc whose reported `updated_at`
    goes stale, using the existing `status.json` contract (and fixing its staleness at
    the same time).
  - Build it after one more wedge incident.
  - Readiness-gated `after:` and HTTP probes come later, only if something needs them.

**Not recommended now:**

- **A Unix-socket RPC control plane** (gem 5.5). The restart generation fixes the actual
  race inside the file control plane.
- **Configured boot-time oneshots** (gem 5.2). No proc needs them.
- **`sase service proc kill`** (gem 4.4). A reliable restart with stop escalation covers
  the use case.
- **Cross-machine singleton leases for the receiver** (cld E7). Config discipline works;
  revisit only if a second `getUpdates` consumer ever appears.
