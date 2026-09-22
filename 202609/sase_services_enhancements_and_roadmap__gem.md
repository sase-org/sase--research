# SASE Services Feature: Defect Analysis, Operational Improvements, and Architectural Roadmap

- **Author**: Researcher `research.27.gem`
- **Date**: 2026-09-22
- **Context**: Epic `sase-11y` ("Introduce the SASE service host and Services tab") and `sase-11y.11` ("Finish the service-host epic leftovers found at landing")
- **Target Repository**: `sase` (primary) and `sase-core` (linked)

---

## 1. Executive Summary

Epic `sase-11y` introduced a major architectural milestone to SASE: replacing the legacy AXE ensure watchdog, ad-hoc daemon loops, and scattered background command slot directories with a unified, per-machine **SASE service host** (`sase service run`), a dedicated **Services tab** in the TUI, and a native supervisor integration (systemd user units on Linux, launchd LaunchAgents on macOS).

A deep independent inspection of the implementation across `src/sase/service/`, `src/sase/main/`, `src/sase/ace/tui/`, `src/sase/procs/`, and the sibling Rust backend `crates/sase_core/src/service/` reveals that while the foundation is well-structured, several **critical defects**, **racy control-plane patterns**, and **operational blind spots** exist in the shipped code.

### Key Findings Summary:
1. **Live, Confirmed Defect in `sase scheduler restart`**: The command is completely broken and operates as a silent no-op because `src/sase/main/scheduler_handler.py` explicitly passes `delay=0.0` to `restart_service_proc()`. The stop marker is created and erased in microseconds before the asynchronous host reconcile loop can observe it. Live verification on this machine confirmed that running `sase scheduler restart` leaves the running PID completely unchanged.
2. **Fundamentally Flawed Stop/Clear Restart Anti-Pattern**: The service host uses level-triggered desired state (`state.stops`), but `restart_service_proc()` attempts to implement an edge-triggered restart by writing a stop marker, sleeping an arbitrary duration (`delay=0.5`), and deleting the stop marker. This creates race conditions under load, causes early clear before slow-terminating children finish exiting, and provides no synchronization or verification.
3. **Complete Invisibility of Orphan Service Procs**: When a configured service proc is renamed or removed from configuration while running, the Rust status engine properly records it in `ServiceStatusSnapshot.orphans`. However, the CLI (`sase service status`, `sase service proc list`) and the TUI Services tab (`_build_axe_items`) iterate exclusively over `snapshot.procs`. Orphan processes are completely hidden from all management surfaces.
4. **`enable_service_proc` Fails to Clear Boot Stops**: Running `sase service proc enable <name>` updates machine enablement overrides but ignores `state.stops`. If a proc had been stopped via `sase service proc stop`, enabling it leaves it stopped, deceiving the operator.
5. **`start_service_proc` Reports False Success on Disabled Services**: The CLI start command checks only whether a proc is *available*, ignoring machine enablement. Running start on a disabled proc reports `"requested service proc <name> start"`, but the host's `_desired_running()` evaluates to false and never starts it.
6. **Stale `status.json` Persists Across Crashes and Restarts**: Child proc status reports (`status.json`) are never unlinked upon process termination or relaunch. When a service restarts, `read_reported_status()` immediately displays the previous run's reported status—even when `updated_at < started_at`—masking boot failures or showing bogus health.
7. **Unconsumed `after: [...]` Dependency Ordering**: Service proc dependencies (`after: [other_proc]`) are parsed and cycle-checked in Rust, stored in `ServiceProcConfig`, and hashed into signatures, but `_reconcile_desired()` in `src/sase/service/host.py` iterates over procs and launches them concurrently without checking whether dependencies are running or ready.
8. **Catastrophic O(N*M) Log Rewriting in `append_bounded_log`**: Once a service proc log reaches `log_max_bytes` (default 2 MB), every incoming chunk (<4 KB) triggers: write chunk -> seek -> read entire 2 MB into memory -> open in `"wb"` (truncating to 0 bytes) -> write entire 2 MB. This causes massive disk thrashing (gigabytes of I/O for modest logging), tears lines mid-boundary, and causes concurrent readers (such as TUI log viewers) to see file truncations.
9. **Duplicate Instance Spawn on Stuck Children**: If a child process ignores `SIGKILL` (e.g. stuck in kernel D-state or hung syscall) and times out during `_stop_child()`, the host drops it from `_children` and immediately launches a second instance in the same loop iteration.
10. **`apply_service_init` Leaves Active Services on Stale Definitions/Environment**: When `sase service init --yes` applies unit file or `service.env` changes, it reloads systemd but explicitly refuses to restart active units (`start=not already_active`), leaving running hosts with stale configurations without warning the user.

Below is the complete analysis, categorization, and prioritized implementation roadmap.

---

## 2. Architecture Review: The Shipped `sase-11y` Model

### 2.1 Process Supervision Hierarchy

The current supervision model follows a multi-tier hierarchy:
```
[Native Platform Supervisor] (systemd user unit: sase.service / launchd: sh.sase.service)
        │  (Supervises only the host process via Restart=on-failure, KillMode=mixed)
        ▼
[Service Host Process] (sase service run, holds flock on host.lock)
        │
        ├── [Supervised Daemon Service Procs] (direct children in separate process groups)
        │       ├── scheduler (builtin: sase scheduler run)
        │       │       └── [Routines] -> [Jobs] -> [Agents] (escaped via detach_scope)
        │       ├── gateway (builtin: mobile gateway server)
        │       ├── telegram_receiver (plugin: sase-telegram inbound daemon)
        │       └── [User/Plugin Configured Daemons]
        │
        └── [Transient Oneshot Procs] (!) (detached, unparented from host cgroup)
```

### 2.2 Boundary Separation: Rust Core vs. Python Runtime

Following the project's litmus test (`rust_core_backend_boundary`), the backend logic is divided cleanly:
- **`sase-core` (Rust)**: Owns ordered config layer merging (`service_config_compose`), dependency cycle detection, persistent state mutations (`service_state_mutate`), expired boot stop pruning, and derived status aggregation (`service_status_build`).
- **`sase` (Python)**: Owns OS-level process management (`subprocess.Popen`), stdout pumping, signal trapping (`SIGTERM`, `SIGINT`, `SIGUSR1`), systemd/launchd platform manager operations, CLI parsing, and Textual TUI rendering.
- **Coordination Seam**: The host and CLI communicate via locked JSON state files (`state.json`), heartbeat records (`host` in `state.json`), and inter-process nudges (`SIGUSR1` to the host PID).

---

## 3. Detailed Defect Analysis (Bugs That Must Be Fixed)

### 3.1 Bug 1: `sase scheduler restart` is a Broken No-Op (Zero-Delay Race Condition)

- **Affected File**: `src/sase/main/scheduler_handler.py:72-79`
- **Severity**: **High** (Core CLI management command fails silently)
- **Root Cause**:
  In `scheduler_handler.py`, the `restart` subcommand calls:
  ```python
  outcome = restart_service_proc(
      "scheduler",
      actor="cli",
      reason="scheduler restart",
      delay=0.0,
  )
  ```
  In `src/sase/service/actions.py`, `restart_service_proc()` does:
  ```python
  stop = record_service_stop(name, actor, reason=reason)
  first_nudge = nudge_service_host()
  if delay > 0:
      time.sleep(delay)
  start = clear_service_stop(name)
  second_nudge = nudge_service_host()
  ```
  Because `delay=0.0`, `clear_service_stop()` executes within microseconds of `record_service_stop()`. By the time the service host receives the `SIGUSR1` signal and executes its next `_reconcile_once()`, the stop marker is already gone. The host reads `state.stops`, finds it empty, observes that `_desired_running()` is true and the signature is unchanged, and does absolutely nothing.
- **Live Reproduction Verification**:
  ```bash
  $ sase scheduler status
  scheduler · running · pid 1964543
  $ sase scheduler restart
  requested service proc scheduler restart
  $ sase scheduler status
  scheduler · running · pid 1964543  # PID unchanged! Never restarted!
  ```
- **Remediation**:
  1. Remove `delay=0.0` from `scheduler_handler.py`.
  2. Implement an explicit restart request marker (see Bug 2).

---

### 3.2 Bug 2: Fundamentally Flawed Stop/Clear Pattern in `restart_service_proc`

- **Affected File**: `src/sase/service/actions.py:82-105`
- **Severity**: **High** (Architectural race condition across all service restarts)
- **Root Cause**:
  The service host state machine is purely level-triggered (`desired = running` if `enabled` and `not in stops`). A restart is an edge-triggered command. Attempting to simulate an edge-triggered restart by toggling a level-triggered stop marker with an arbitrary sleep (`delay=0.5`) is fundamentally unreliable:
  - If the host is performing heavy work or the system is under load, `_reconcile_once()` might not execute within the 500 ms window. The stop is cleared before the host ever sees it.
  - If the target service takes longer than 500 ms to terminate gracefully, `clear_service_stop()` clears the stop marker while the process is still running.
  - The CLI command returns immediately without verifying that the process actually stopped or restarted, or reporting the new PID.
- **Remediation**:
  Add an explicit `restarts: dict[str, ServiceRestartRequest]` map or `generation: int` counter to `ServiceState` in `sase-core`. When a restart is requested, increment the generation counter or record a restart token. The service host compares the running process's launch generation to the requested generation, stops the old process, launches the new one, and records the completed generation. Callers can poll or wait synchronously for the token to settle.

---

### 3.3 Bug 3: Complete Invisibility of Orphan Service Procs

- **Affected Files**:
  - `src/sase/main/service_handler.py:103-104, 227-234`
  - `src/sase/ace/tui/actions/axe_display/_loader_items.py:130-142`
- **Severity**: **Medium** (Operational leak / unmanageable background processes)
- **Root Cause**:
  When a service proc definition is removed from configuration (or renamed in `sase.yml`) while its process is running, the host continues to observe it, and `sase-core`'s `derive_orphan_proc()` places it in `snapshot.orphans`.
  However:
  - `_handle_service_status` in `service_handler.py` only iterates over `snapshot.procs`.
  - `_handle_proc_list` in `service_handler.py` only iterates over `snapshot.procs`.
  - `_build_axe_items` in `_loader_items.py` only appends items from `service_status.procs`.
  Orphan procs are completely omitted from the CLI tables and the TUI sidebar. Operators cannot see that an orphan is running, cannot see its PID or resource consumption, and cannot stop it from the service interface.
- **Remediation**:
  - In `service_handler.py`: Add an "Orphan procs" section or append orphan rows to `sase service status` and `sase service proc list` with state `orphan` or `unconfigured`.
  - In `_loader_items.py`: Append orphan service procs to the sidebar with an `[orphan]` badge so they can be selected, inspected, and stopped.

---

### 3.4 Bug 4: `enable_service_proc` Fails to Clear Boot Stop Markers

- **Affected File**: `src/sase/service/actions.py:107-123`
- **Severity**: **Medium** (Confusing state / broken operator expectations)
- **Root Cause**:
  If an operator stops a service proc using `sase service proc stop <name>` (which records a boot-scoped stop marker in `state.stops`), and later enables it using `sase service proc enable <name>`, `enable_service_proc()` calls `set_service_enablement(name, True, actor)` but does not call `clear_service_stop(name)`.
  When the host reconciles, `_desired_running()` evaluates:
  ```python
  return bool(entry.available and enabled and entry.name not in state.state.stops)
  ```
  Because `name in state.state.stops` is still true, the service proc remains stopped. The CLI outputs `"enabled service proc <name> for this machine"`, but `sase service status` continues to report `desired: stopped, state: stopped`.
- **Remediation**:
  In `enable_service_proc()`, automatically clear any existing boot stop marker (`clear_service_stop(name)`) so that enabling a service proc immediately permits it to run.

---

### 3.5 Bug 5: `start_service_proc` Reports False Success on Disabled Services

- **Affected File**: `src/sase/service/actions.py:41-61, 153-160`
- **Severity**: **Medium** (Silent failure / incorrect user feedback)
- **Root Cause**:
  `_require_startable(entry)` checks only `entry.available`:
  ```python
  def _require_startable(entry: ServiceProcConfig, *, command: str) -> None:
      if entry.available:
          return
      reason = "; ".join(entry.unavailable_reasons) or "proc is unavailable"
      raise ServiceProcActionError(...)
  ```
  It does not check `entry.enabled` or machine enablement overrides. If an operator runs `sase service proc start <name>` on a service proc that is disabled by default or disabled in the machine overlay (for example, `telegram_receiver` on a machine without it enabled):
  - `_require_startable()` passes without error.
  - `clear_service_stop(name)` runs.
  - The CLI outputs: `"requested service proc <name> start"`.
  - The host reconciles, checks `_desired_running()`, sees `enabled == False`, and does not start the process.
  The user is given the false impression that the service was started.
- **Remediation**:
  Check effective enablement in `_require_startable()` (or `start_service_proc()`). If the proc is disabled, either return an error informing the user to run `sase service proc enable <name>` first, or provide a `--force`/auto-enable option.

---

### 3.6 Bug 6: Stale `status.json` Reports Persist Across Crashes & Restarts

- **Affected Files**:
  - `src/sase/service/host_support.py:97-117`
  - `src/sase/service/host.py:168-187, 267-386`
  - `src/sase/ace/tui/widgets/_axe_dashboard_output.py:350-359`
- **Severity**: **Medium** (Misleading diagnostic data / false health reporting)
- **Root Cause**:
  Service procs can report internal state by writing a JSON payload to `SASE_SERVICE_PROC_STATUS` (`~/.sase/service/procs/<name>/status.json`).
  However, this file is never unlinked when a process exits, crashes, or is restarted.
  When the service host launches a new child instance:
  1. `read_reported_status(name)` in `host_support.py` reads the existing `status.json` from the previous run.
  2. It does not verify whether `reported.updated_at >= running.started_at`.
  3. The TUI and status snapshots immediately render the old `reported.state` and `reported.summary` (e.g. `"ready — Connected to Telegram"`) while the new process is still initializing or failing.
- **Remediation**:
  - When a process exits in `_settle_exit()`, and before spawning a new child in `_launch()`, unlink `status.json` or write a cleared marker.
  - In `read_reported_status()`, ignore any report whose `updated_at` timestamp is earlier than `running.started_at`.

---

### 3.7 Bug 7: `entry.after` Dependency Ordering is Completely Unconsumed

- **Affected Files**:
  - `src/sase/service/host.py:215-257`
  - `crates/sase_core/src/service/config.rs:727-805`
- **Severity**: **Medium** (Declared configuration contract is ignored at runtime)
- **Root Cause**:
  In `sase-core`, `after: ["proc_a"]` is thoroughly validated: self-dependencies and cycles are detected and rejected. The resolved `after` list is serialized and stored in `ServiceProcConfig.after`.
  However, in `src/sase/service/host.py`:
  ```python
  for entry in config.procs:
      if entry.name in self._children or entry.name in self._pending:
          continue
      if self._desired_running(entry, state):
          self._launch(entry, history=self._restart_history.get(entry.name))
  ```
  The host simply loops over `config.procs` in dictionary order. It never checks whether the dependencies listed in `entry.after` are currently running or ready. If service B specifies `after: ["service_a"]`, service B is launched simultaneously with A (or even before A if B appears first in the config).
- **Remediation**:
  In `_reconcile_desired()`:
  - Sort `config.procs` topologically according to `entry.after`.
  - For each candidate entry, check if all procs named in `entry.after` are active in `self._children` and have reached running state before calling `self._launch(entry)`.

---

### 3.8 Bug 8: Catastrophic O(N*M) Log Rewriting in `append_bounded_log`

- **Affected File**: `src/sase/service/host_support.py:124-141`
- **Severity**: **High** (Severe disk I/O amplification and log corruption risk)
- **Root Cause**:
  `append_bounded_log` is called by `pump_service_output` via `sase.supervision.pump_output` for *every chunk* read from the child process's stdout/stderr pipe (often chunks as small as a few bytes to 4 KB).
  Look at the implementation:
  ```python
  def append_bounded_log(path: Path, chunk: bytes, max_bytes: int) -> None:
      path.parent.mkdir(parents=True, exist_ok=True)
      with path.open("ab") as handle:
          handle.write(chunk)
      if max_bytes <= 0:
          return
      try:
          size = path.stat().st_size
      except OSError:
          return
      if size <= max_bytes:
          return
      with path.open("rb") as handle:
          handle.seek(max(0, size - max_bytes))
          data = handle.read()
      with path.open("wb") as handle:
          handle.write(data)
  ```
  Once the log reaches `max_bytes` (default 2 MB):
  - Every subsequent chunk triggers a full `open("rb")` of 2 MB, followed by `open("wb")` which truncates the file to 0 bytes and rewrites the entire 2 MB.
  - If a service outputs 50 log lines per second, the host reads and writes **100 MB/sec** of disk I/O continuously.
  - Opening the file in `"wb"` mode creates an atomic race window where concurrent readers (such as the TUI or `sase service proc logs`) observe an empty 0-byte file.
  - `handle.seek(size - max_bytes)` slices at an arbitrary byte offset, splitting UTF-8 multi-byte characters and leaving truncated lines at the top of the file.
- **Remediation**:
  - Adopt standard dual-file log rotation: write to `<name>.log`. When size exceeds `max_bytes`, rename `<name>.log` to `<name>.log.1` (or `<name>.log.old`) and start a fresh `<name>.log`.
  - Alternatively, use high-water / low-water truncation: only truncate when the file exceeds `1.25 * max_bytes`, truncate down to `max_bytes` aligned to the next newline (`\n`), and perform the rewrite via an atomic tempfile replace (`os.replace`).

---

### 3.9 Bug 9: Duplicate Instance Spawn on Stuck/Hung Child Process

- **Affected File**: `src/sase/service/host.py:467-509, 220-232, 252-257`
- **Severity**: **High** (Process leakage and supervisor desynchronization)
- **Root Cause**:
  In `_stop_child()`, the host sends `stop_signal`, waits for `stop_timeout_seconds`, and if the process hasn't exited, sends `SIGKILL` and waits for `_STOP_KILL_TIMEOUT_SECONDS` (5.0s).
  If the process is stuck in uninterruptible kernel sleep (D-state), a hung NFS/FUSE call, or a zombie state, `running.process.poll()` is still `None` after the timeout expires.
  In `_reconcile_desired()`:
  ```python
  self._stop_child(name, running)
  self._children.pop(name, None)
  self._pending.pop(name, None)
  ```
  The host unconditionally pops `name` from `self._children` even though the previous process is still alive. Later in the same reconcile pass:
  ```python
  for entry in config.procs:
      if entry.name in self._children or entry.name in self._pending:
          continue
      if self._desired_running(entry, state):
          self._launch(entry, ...)
  ```
  Because `entry.name` is no longer in `self._children`, the host immediately calls `_launch(entry)`, spawning a *second* process for the same service proc while the old stuck process continues to consume system resources.
- **Remediation**:
  Do not remove the child from `self._children` if `poll()` is still `None`. Keep tracking it as `status="stuck"` or `status="terminating"`, refuse to launch a replacement until the previous PID has truly exited, and flag the issue in the host status diagnostics.

---

### 3.10 Bug 10: `apply_service_init` Leaves Active Services on Stale Definitions/Environment

- **Affected File**: `src/sase/service/platform.py:171-216`
- **Severity**: **Medium** (Silent configuration drift after user intervention)
- **Root Cause**:
  When an operator runs `sase service init --yes` to apply changes (for example, updated SASE binary path, modified environment variables, or new systemd options):
  ```python
  linux_reload(runner)
  retire_linux_legacy(runner)
  linux_enable_start(
      definition,
      runner,
      enable=not already_enabled,
      start=not already_active,
  )
  ```
  Because `already_active` is true if the service was already running, `start=False`. The manager reloads the unit configuration (`systemctl --user daemon-reload`), but never restarts the service. The service host continues running the old executable with the old environment. The command reports `ok=True, message="installed sase.service"`, giving the operator the impression that changes were applied.
- **Remediation**:
  If `plan.actions` included updating the definition or environment file and the unit was active, either automatically restart the unit (`systemctl --user restart sase.service`), or emit a prominent notice: `"Configuration updated. Run 'sase service restart' to activate changes on the running service."`

---

### 3.11 Bug 11: Serial/Sequential Child Termination in `_stop_all_children`

- **Affected File**: `src/sase/service/host.py:467-510`
- **Severity**: **Low-to-Medium** (Slow shutdowns and risk of ungraceful SIGKILL from systemd)
- **Root Cause**:
  During service host shutdown (triggered by `SIGTERM`, `SIGINT`, or systemd stop), `_stop_all_children()` calls `_stop_child(name, running)` serially for each child.
  Each child can take up to `stop_timeout_seconds` (default 10s).
  With 4 configured services, total shutdown time can take up to 40 seconds. If systemd's unit timeout is reached (or user Ctrl-C is pressed again), systemd sends `SIGKILL` to the entire cgroup (`KillMode=mixed`), killing remaining children abruptly without graceful cleanup.
- **Remediation**:
  Send the stop signals (`SIGTERM`) to all children in parallel first. Then poll and wait concurrently until all children have exited or their respective deadlines expire.

---

## 4. Objective Improvements (Usability, Observability, and Robustness)

Beyond fixing bugs, several targeted improvements will significantly enhance the operational quality of SASE services:

### 4.1 CLI Log Streaming (`-f` / `--follow`)
- **Current Limitation**: Both `sase service logs` and `sase service proc logs <name>` only accept `-n / --lines`. There is no follow flag.
- **Improvement**: Add `-f / --follow` to both commands. In follow mode, after printing the initial tail lines, poll the log file for new bytes (or use `inotify` via a lightweight helper) until interrupted, matching standard `journalctl -f` and `docker logs -f` behavior.

### 4.2 Detailed Diagnostic Output in `sase service proc show`
- **Current Limitation**: `sase service proc show <name>` currently prints only: `name`, `summary`, `source`, `enabled`, `desired`, `state`, `launcher`, and `log`. It completely ignores:
  - `restarts`: Count of restarts since host start.
  - `last_exit`: Exit code, terminating signal, finished timestamp, spawn errors.
  - `restart`: Backoff delay, next restart timestamp (`restart_at`), and crash-loop flag.
  - `reported`: Detailed internal state and summary reported via `status.json`.
  - `started_at` / Uptime: Elapsed runtime of the active PID.
  - `description`: Docstring/description of the service proc.
- **Improvement**: Add these fields to `handle_service_proc_show()` so operators diagnosing a failing or crash-looping service have all relevant telemetry immediately in stdout without needing to parse JSON.

### 4.3 Enhanced CLI Status Tables (PIDs, Uptime, Restarts)
- **Current Limitation**: The tables printed by `sase service status` and `sase service proc list` contain columns: `Name`, `Enabled`, `Desired`, `State`, `Summary`.
- **Improvement**: Add `PID`, `Restarts`, and `Uptime` columns. For instance:
  ```
  ┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃ Name              ┃ Enabled ┃ Desired ┃ State   ┃ PID      ┃ Uptime  ┃ Summary               ┃
  ┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━┩
  │ gateway           │ yes     │ running │ running │ 1523548  │ 2d 4h   │ running · pid 1523548 │
  │ scheduler         │ yes     │ running │ running │ 2018178  │ 12m     │ running · pid 2018178 │
  │ telegram_receiver │ yes     │ running │ running │ 1523656  │ 2d 4h   │ running · pid 1523656 │
  └───────────────────┴─────────┴─────────┴─────────┴──────────┴─────────┴───────────────────────┘
  ```

### 4.4 Dedicated `sase service proc kill <name>` Subcommand
- **Current Limitation**: Currently, operators only have `sase service proc stop <name>`. This records a persistent stop marker and relies on the service host to send `SIGTERM`. If a process is hung or an operator wants to immediately terminate and let the host restart it (per its restart policy), there is no command to do so without manually running `sase proc list` and `sase proc kill <proc_id>`.
- **Improvement**: Add `sase service proc kill <name> [-s SIGNAL]`. This looks up the active PID of `<name>` and sends the signal directly, allowing the supervisor to immediately handle the exit according to its restart policy.

### 4.5 Service Runtime Health Checks in `sase doctor`
- **Current Limitation**: `check_service_platform()` in `src/sase/doctor/checks_service_platform.py` only checks whether the unit file and environment file on disk match the desired state. If the service host process is dead, crash-looping, or failing to start procs, `sase doctor` reports `Service platform unit: OK`.
- **Improvement**: Add a runtime doctor check (`service.host_runtime` and `service.procs_health`):
  - Is the service host process alive and holding the lock?
  - Is the heartbeat fresh (< 15 seconds)?
  - Are any enabled daemon procs in `crash_loop`, `backoff`, or unexpected `stopped` states?

### 4.6 Configurable Host Environment Passthrough (`service.env` / Proxies)
- **Current Limitation**: `capture_service_environment()` only captures LLM provider API keys, `PATH`, and `SSH_AUTH_SOCK`. In corporate or restricted network environments, services and child agents require proxy variables (`HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`), custom CA certificates (`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`), or locale settings (`LANG`, `LC_ALL`). Because `systemd --user` runs in an isolated environment without shell profiles, these variables are completely missing.
- **Improvement**: Allow configuring `service.capture_env_names: [...]` or a static `service.env: {...}` block in `sase.yml` that `capture_service_environment()` captures and persists to `service.env`.

### 4.7 TUI Services Tab Polish
- **Help Modal Keybinding Documentation**: Update `src/sase/ace/tui/modals/help_modal/axe_bindings.py` to explicitly document `r` as "Restart selected service proc" and `!e` as "Toggle service enablement".
- **Process Selector Modal Expansion**: Update `ProcessSelectModal` (`!x` from non-Services tabs) to list active service procs alongside background commands, so operators can quickly restart or stop the scheduler or gateway from any tab.

---

## 5. Architectural Extensions for Future Epics

Looking beyond immediate fixes, the following five extensions represent high-leverage architectural evolutions for SASE services:

### 5.1 Extension 1: Declarative Health Checks & Dependency Readiness Gating

- **Motivation**:
  Currently, the service host only knows whether a process PID is alive. A process that deadlocks, hangs in an infinite loop, or stops serving requests remains marked `running`. Furthermore, `entry.after` cannot function effectively without knowing when a dependency is *ready* (not just spawned).
- **Design Proposal**:
  Add an optional `healthcheck:` specification to `service.procs`:
  ```yaml
  service:
    procs:
      gateway:
        launcher: { kind: builtin, builtin: gateway }
        healthcheck:
          type: http
          url: http://127.0.0.1:7629/api/v1/health
          interval_seconds: 15
          timeout_seconds: 2
          retries: 3
          start_period_seconds: 10
      scheduler:
        launcher: { kind: builtin, builtin: scheduler }
        after: [gateway]
        healthcheck:
          type: heartbeat
          file: ~/.sase/axe/heartbeat.json
          max_age_seconds: 30
  ```
- **Benefits**:
  - Automatically restarts hung/deadlocked services.
  - True dependency gating: Service B waiting `after: [A]` starts only when A transitions from `starting` to `healthy`.
  - Richer TUI indicators: Render distinct pills for `starting`, `healthy`, `degraded`, and `unhealthy`.

---

### 5.2 Extension 2: Configured (Non-Transient) Oneshots & Lifecycle Hooks

- **Motivation**:
  Currently, `mode: oneshot` is only supported for runtime transient background commands (`!`). There is no mechanism to declare one-off initialization tasks that must run on service host boot before daemons start (e.g. database/state migrations, workspace cleanup, cache warming, dependency prebuilding).
- **Design Proposal**:
  Allow declaring `mode: oneshot` in `service.procs`:
  ```yaml
  service:
    procs:
      db_migrate:
        mode: oneshot
        command: "sase migrate apply"
        on_failure: abort_daemons  # or: continue
      gateway:
        after: [db_migrate]
        mode: daemon
        ...
  ```
- **Benefits**:
  - Guarantees prerequisites are met before daemons spin up.
  - Eliminates manual pre-start steps or ad-hoc wrappers in systemd units.

---

### 5.3 Extension 3: Resource Limits & Sandboxing via Transient Systemd Slices

- **Motivation**:
  A memory leak or CPU spin in the scheduler, gateway, or a plugin proc (like Telegram receiver) can exhaust system memory, triggering the Linux OOM killer to terminate arbitrary developer processes or the service host itself.
- **Design Proposal**:
  Allow service procs to declare resource limits in `sase.yml`:
  ```yaml
  service:
    procs:
      scheduler:
        resources:
          memory_max: 2G
          cpu_quota: 150%
          tasks_max: 500
  ```
  On Linux, when spawning the service proc, wrap it in `systemd-run --user --scope --slice=sase-service-<name>.slice -p MemoryMax=2G ...` (similar to how `detach_scope` already operates).
- **Benefits**:
  - Isolates resource hogs so one misbehaving daemon cannot destabilize the developer's workstation or other SASE services.

---

### 5.4 Extension 4: Cross-Machine Service Control & Tailnet Fleet Federation

- **Motivation**:
  SASE already features machine-to-machine dispatch (Apollo, Athena) over Tailscale SSH and mobile gateway pairs. However, checking service status or restarting services across machines requires SSHing into each machine manually.
- **Design Proposal**:
  Expose service status and control endpoints on the mobile gateway API:
  - `GET /api/v1/services/status`
  - `POST /api/v1/services/proc/<name>/restart`
  - `GET /api/v1/services/proc/<name>/logs?lines=100&follow=false`
  Integrate these with the CLI and TUI:
  - `sase machine service apollo status`
  - `sase machine service apollo restart scheduler`
  - In TUI Admin Center / Services tab: A remote machine switcher to inspect service health across the fleet.
- **Benefits**:
  - Centralized operational visibility across multi-machine development setups.

---

### 5.5 Extension 5: Dedicated Unix Domain Socket Control Plane (UDS / RPC)

- **Motivation**:
  File polling (`state.json`), file locking (`flock`), and Unix signals (`SIGUSR1`) are brittle:
  - Signals do not carry payloads.
  - Signal delivery can be lost or coalesced if multiple signals arrive rapidly.
  - File-based state mutations require sleep-based delays and non-atomic stop/clear patterns.
  - Callers cannot receive synchronous return values or streaming logs from the host.
- **Design Proposal**:
  The service host listens on a local Unix domain socket at `~/.sase/service/host.sock`.
  The CLI and TUI communicate with the host via a simple JSON-RPC or HTTP-over-UDS protocol:
  - `POST /restart {"proc": "scheduler"}` -> Blocks until the process is restarted, returns `{"new_pid": 2018178, "old_pid": 1964543}`.
  - `GET /status` -> Returns instant, in-memory host status snapshot without reading disk.
  - `GET /logs?proc=scheduler&stream=true` -> Streams live log chunks directly over the socket.
- **Benefits**:
  - Completely eliminates all stop/clear race conditions and file-polling delays.
  - Instant command execution and synchronous error propagation.
  - Real-time log streaming without touching filesystem buffers.

---

## 6. Recommended Action Plan & Prioritization

### Phase 1: Immediate Defect Remediation (Target: Next Patch/Minor Release)
These changes address confirmed bugs, race conditions, and data corruption risks:

| Item | Description | Files | Complexity |
|---|---|---|---|
| **1.1** | **Fix `sase scheduler restart` no-op**: Remove `delay=0.0` override in `scheduler_handler.py`. | `src/sase/main/scheduler_handler.py` | Low |
| **1.2** | **Replace stop/clear anti-pattern with explicit restart marker**: Add restart generation counter/token to `ServiceState` in Rust and Python; host checks generation change to trigger restart. | `crates/sase_core/src/service/state.rs`, `src/sase/service/actions.py`, `src/sase/service/host.py` | Medium |
| **1.3** | **Surface orphan service procs**: Render `snapshot.orphans` in CLI status/list and TUI sidebar items. | `src/sase/main/service_handler.py`, `src/sase/ace/tui/actions/axe_display/_loader_items.py` | Low |
| **1.4** | **Clear boot stop in `enable_service_proc`**: Automatically call `clear_service_stop` when enabling a proc. | `src/sase/service/actions.py` | Low |
| **1.5** | **Validate enablement in `start_service_proc`**: Reject start requests on disabled procs with clear error. | `src/sase/service/actions.py` | Low |
| **1.6** | **Invalidate stale `status.json`**: Unlink `status.json` on proc termination and filter out reports with `updated_at < started_at`. | `src/sase/service/host.py`, `src/sase/service/host_support.py` | Low |
| **1.7** | **Fix O(N*M) log rewriting in `append_bounded_log`**: Implement dual-file rotation (`.log` / `.log.1`) or high-water truncation with atomic tempfile replacement. | `src/sase/service/host_support.py` | Medium |
| **1.8** | **Prevent duplicate launch of hung children**: Retain stuck processes in `_children` until `poll()` is non-null. | `src/sase/service/host.py` | Low |
| **1.9** | **Parallelize shutdown in `_stop_all_children`**: Send SIGTERM to all children concurrently before waiting on timeouts. | `src/sase/service/host.py` | Low |
| **1.10** | **Enforce `entry.after` ordering at launch**: Sort procs topologically and delay launching dependent procs until dependencies are active. | `src/sase/service/host.py` | Medium |

### Phase 2: Operational Ergonomics & Observability
These changes provide developer-facing usability improvements:

| Item | Description | Files | Complexity |
|---|---|---|---|
| **2.1** | **Add `-f/--follow` log streaming**: Support real-time log following for `service logs` and `proc logs`. | `src/sase/main/parser_service.py`, `src/sase/main/service_handler.py` | Medium |
| **2.2** | **Enrich `sase service proc show`**: Display restarts, last exit status, crash-loop backoff, uptime, and description. | `src/sase/main/service_handler.py` | Low |
| **2.3** | **Enrich status tables**: Add PID, Uptime, and Restarts columns to CLI status/list tables. | `src/sase/main/service_handler.py` | Low |
| **2.4** | **Add `sase service proc kill <name>`**: Provide direct CLI signal delivery to running procs. | `src/sase/main/parser_service.py`, `src/sase/main/service_handler.py` | Low |
| **2.5** | **Add service health checks to `sase doctor`**: Check host running state, heartbeat freshness, and crash-looping procs. | `src/sase/doctor/checks_service_platform.py` | Low |
| **2.6** | **Configurable proxy & environment capture**: Support `service.capture_env_names` in `sase.yml`. | `src/sase/service/env.py`, `src/sase/config/sase.schema.json` | Medium |
| **2.7** | **TUI polish**: Document `r` (restart) in help modal; expose service procs in `ProcessSelectModal` (`!x`). | `src/sase/ace/tui/modals/help_modal/axe_bindings.py`, `src/sase/ace/tui/modals/process_select_modal.py` | Low |

### Phase 3: Architectural Extensions (Candidate Future Epics)
Larger extensions to be planned as standalone epics:
1. **Epic: Declarative Health Checks & Dependency Readiness**: Add `healthcheck` schema and runtime verification for daemon procs.
2. **Epic: Configured Oneshots & Boot Hooks**: Support pre-daemon one-time initialization tasks in `service.procs`.
3. **Epic: UDS Control Plane**: Upgrade host control communication from `state.json` + `SIGUSR1` to a Unix domain socket RPC server.
4. **Epic: Remote Machine Service Federation**: Expose service control through the mobile gateway API for multi-machine fleet management.
