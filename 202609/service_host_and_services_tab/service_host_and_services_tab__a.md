# SASE Service Runtime and Service Tab Architecture

**Researcher:** A  
**Date:** 2026-09-16  
**Scope:** Independent implementation research for generalizing AXE/Supervisor into a
cross-platform SASE Service and Service tab. I did not consult the other swarm
researcher's report, transcript, or findings.

## Executive summary

This idea is worth pursuing, but only as a consolidation project. Today SASE has three
different supervision arrangements for the processes in scope: the AXE orchestrator
and its routines, a standalone systemd unit for `sase_gateway`, and a periodic Telegram
job that re-establishes an indefinite receiver Proc. A SASE-owned service runtime can
replace those arrangements with one coherent lifecycle, one CLI, one TUI, and one
cross-platform installation path.

The strongest design is a two-level supervisor:

1. The operating system's per-user service manager owns exactly one foreground process,
   `sase service run`.
2. That SASE Service owns all configured service procs, including the builtin
   Supervisor and gateway, plugin-provided Telegram receiver, user-defined persistent
   processes, and transient oneshots.

The OS manager should **not** receive one unit per service proc. That would expose
platform differences throughout SASE, make plugin installation mutate native service
configuration, and deprive the Service tab of a single portable control plane.
Conversely, `sase service run` must not daemonize: systemd or launchd already owns its
lifetime.

Each configured service proc needs a stable service ID and desired state. Each actual
launch or restart should remain a distinct durable SASE Proc execution. This division
is important: the stable service node is what users control, while individual Proc
records provide execution identity, output, status, and history. It also avoids
misusing the existing Proc `kind`, which the current glossary deliberately treats as a
compatibility label rather than a complete semantic taxonomy.

I recommend the following requirements changes:

- Define startup as **per-user service-manager startup**, not universally as machine
  boot. A Linux user service can start at boot when lingering is enabled. A normal
  macOS LaunchAgent starts at user login. Pre-login macOS startup requires a privileged
  LaunchDaemon and should be a later, explicit mode rather than the default.
- Show disabled and unavailable configured service procs in the Service tab. Otherwise
  users cannot enable them from the tab, contrary to the requested interaction.
- Make plugin service procs opt-in by default. Installing a plugin must not silently
  grant it an always-running background process.
- Exclude project-local configuration from the service catalog. A boot/login service's
  working directory must not decide which long-lived processes run on a machine.
- Interpret enable/disable as persistent machine policy, and start/stop as runtime
  control. An enabled-but-stopped proc starts again when the SASE Service next starts;
  a disabled proc does not.
- Add an idempotent `sase service uninstall` operation alongside `init`. Native service
  installation needs a supported recovery and removal path.
- Treat `!` commands as transient oneshot service procs, but replace the current fixed
  nine-slot history with a limit on concurrently active oneshots. Completed history
  should never prevent a new command from running.

The project should be rejected or deferred if it merely adds this runtime on top of the
old AXE desired-state/watchdog mechanism, standalone gateway units, and Telegram rearm
loop. Two supervisors claiming the same child is worse than the present fragmentation.

## What exists now

### AXE/Supervisor

The current AXE architecture is already a small service manager. Its orchestrator
starts one subprocess per routine, monitors those routine processes, and restarts them
after failure. Routine processes schedule short jobs and persist status under
`~/.sase/axe`. The public lifecycle is exposed through `sase axe
start|stop|restart|ensure|status`, and the TUI normally ensures AXE is running.

`sase axe ensure install` is Linux-specific. It installs a user systemd timer/watchdog
that periodically restores AXE's desired state; it is not a portable service host.
Several update and TUI paths also have AXE-specific restart behavior. Those callers
will need to restart the new SASE Service or its Supervisor child, depending on what
changed.

A live inspection on athena found a detached, healthy AXE orchestrator managing ten
routines: `checks`, `ci_watch`, `comments`, `external_mirror`, `hooks`,
`housekeeping`, `refresh_docs`, `run_every`, `telegram`, and `waits`. The Telegram
routine currently contains `tg_inbound` and `tg_outbound` jobs. Neither athena nor
apollo currently had an installed `sase-axe-ensure.timer`, so the current detached AXE
process and the native gateway service are already separate lifetime domains.

Relevant implementation areas include `src/sase/axe/orchestrator.py`,
`src/sase/main/parser_ace.py`, `src/sase/ace/tui/actions/axe_display/`, and
`docs/axe.md`.

### Background commands

The `!` workflow currently uses `sase axe bgcmd-launch`, ultimately starting a detached
shell command with `start_new_session=True`. State and output live beneath
`~/.sase/axe/bgcmd`. The implementation has nine persistent slots, and a completed
entry continues to consume its slot until dismissed.

The TUI already gives these entries a distinct cyan presentation and supports launch,
kill, rerun, selection, output inspection, and dismissal. Those interactions are worth
preserving. The storage and process ownership should change: the command becomes a
transient service definition with restart policy `never`, and its execution becomes a
normal durable Proc. The concurrency limit may remain nine initially, but completed
history must not consume concurrency.

The current shell behavior should also become explicit. Interactive `!` input can be
translated deliberately to `$SHELL -lc <text>`. Declarative service configuration
should use an argument vector by default and should require an explicit setting to opt
into shell interpretation.

Relevant implementation areas include `src/sase/ace/tui/bgcmd.py` and
`src/sase/ace/tui/widgets/bgcmd_list.py`.

### Durable Procs and the Procs tab

SASE already has most of the execution substrate needed for service children:

- durable Proc records and retained output;
- process-group ownership and signal handling;
- status reconciliation for live and stale processes;
- a Proc observer used by the TUI;
- queryable fields and a cached, off-thread Procs presentation.

The current Proc wire schema has `command`, `tui`, and `detached` kinds, plus `legacy`
and `proc-shell` lifecycles. It also demonstrates that additive, domain-specific
metadata can coexist with the common wire shape. The Rust core is the correct place to
extend the schema, state transitions, and query semantics; the Python CLI and TUI
should consume those bindings rather than recreate service rules.

The Procs query dialect currently exposes booleans for `monitor`, `running`, and
`failed`. The default Procs query is empty. The top-right active-proc indicator removes
monitor rows from its count but has no service concept. This makes the requested
behavior a natural additive change: add a `service` boolean derived from service-proc
metadata, initialize the Procs pane query to `-service`, and exclude service rows from
the global gear count. Removing `-service` should reveal the actual executions and
their logs; hiding them must remain a presentation default, not deletion from the Proc
store.

Relevant implementation areas include `crates/sase_core/src/procs/wire.rs` and
`crates/sase_core/src/procs/store.rs` in `sase-core`, plus
`src/sase/procs/models.py`, `src/sase/ace/tui/_proc_query.py`,
`src/sase/ace/query_profile/profiles/_procs.py`, and
`src/sase/ace/tui/actions/lifecycle.py` in `sase`.

### Gateway native services

The chezmoi repository currently installs `sase-gateway.service` on athena and apollo.
It is a user systemd unit with `Type=simple`, an absolute `ExecStart`, localhost port
7629, `Restart=on-failure`, and `RestartSec=5`. Live inspection on 2026-09-16 found the
unit enabled and active on both machines. Both machines also had user lingering
enabled. Athena was running systemd 257 and apollo systemd 255.

Migration must therefore be transactional. The old unit and new builtin gateway
service proc cannot both bind the port. On each machine the cutover should validate
the new definition first, stop and disable the legacy unit, start the gateway under the
SASE Service, verify its Proc and listening endpoint, and restore the legacy unit if
verification fails. Only after both machines have migrated should the unit be removed
from chezmoi.

The builtin gateway should default to disabled globally and be enabled in the athena
and apollo machine overlays.

### Telegram receiver

The `sase-telegram` plugin currently exposes console scripts for inbound and outbound
jobs but no plugin `sase_config` entry point. Every five seconds, the inbound job
cleans up state and idempotently ensures that an indefinite receiver Proc exists. That
periodic rearm is necessary because an ordinary detached Proc is not automatically
restarted.

The new architecture should separate the responsibilities:

- the plugin contributes a disabled-by-default service-proc definition for the
  receiver through its config resource;
- the SASE Service owns starting, stopping, restarting, and backing off that receiver;
- any periodic inbound cleanup that remains useful stays a Supervisor job, but it no
  longer launches or repairs the receiver;
- the legacy `~/.sase/telegram_is_enabled` switch migrates to machine-config
  enablement.

Missing credentials must not create a rapid clean-exit loop. Disabled means no launch.
If an enabled receiver lacks credentials, it should report an actionable nonzero
failure and enter bounded exponential backoff, or remain alive while retrying. The
first option is simpler and makes the unavailable state visible to the common manager.

Relevant plugin areas include `src/sase_telegram/receiver.py`,
`docs/inbound.md`, and the plugin's `pyproject.toml`.

## Critique of the idea

### Why it is valuable

The proposal creates a stable boundary between process policy and process execution.
It removes three bespoke repair mechanisms, makes native startup portable, gives
plugins a safe way to contribute background capabilities, and lets the TUI present
desired and observed state together. It also gives headless users the same controls as
TUI users.

The architecture is particularly suitable for SASE because its services are
user-scoped, share SASE configuration and Proc storage, and need domain-aware
presentation. Installing every plugin process as a systemd or launchd unit would be
more native, but would duplicate configuration and behavior across platforms and make
the Service tab little more than a lossy wrapper over two different APIs.

### Main design risks

**It can grow into a poor reimplementation of systemd.** The SASE Service should own
only a constrained contract: command, environment, working directory, stop timeout,
restart policy, backoff, and optional simple health checks. Scheduling remains a
Supervisor responsibility. Dependencies, sockets, secret management, resource
sandboxing, container orchestration, and arbitrary lifecycle callback systems are out
of scope until concrete use cases justify them.

**Double supervision can cause process fights.** AXE's detached lifetime, its desired
state/watchdog, the gateway unit, and Telegram's repair job must be explicitly retired
as their replacements land. Compatibility commands should delegate to the new owner;
they must not preserve an independent fallback daemon.

**“Service” is overloaded.** The glossary and UI must distinguish the SASE Service
(one manager), a native user service (systemd/launchd ownership), a service proc
(managed child definition plus desired state), and a Proc (one execution record).

**Plugin installation could become implicit persistence.** Loading a plugin definition
must not enable it. The effective machine configuration must opt in, and status should
make a missing required plugin or invalid definition visible rather than silently
dismissing it.

**Boot behavior differs by platform.** A per-user Linux manager can start at boot when
linger is enabled. A LaunchAgent starts at GUI login, while a system LaunchDaemon is
root-managed and has a different trust and configuration model. Calling both “start on
boot” would promise behavior the safe default cannot deliver.

**Self-update introduces executable skew.** A native unit contains an absolute command
path. `sase service init --check` and `status` should detect a missing or stale path,
and SASE/plugin update flows should restart the service after the installation has
completed. Updating a child in place and immediately restarting it from code being
replaced is less reliable than a host-level restart request.

### Objective requirement adjustments

The following are changes to the stated requirements, not just implementation detail:

1. **Display all configured service proc nodes, including disabled and unavailable
   ones.** “Each active/enabled service proc” is too narrow for an enable action.
2. **Use per-user startup semantics.** Linux boot startup is conditional on linger;
   macOS defaults to login startup. A privileged system-wide installation can be
   evaluated separately.
3. **Add `uninstall`, `status`, and `--check` behavior to native installation.** An
   installer without an idempotent diagnostic/removal path is difficult to recover.
4. **Default plugin definitions to disabled.** Installation is not consent to persistent
   execution.
5. **Keep project configuration out of the service catalog.** Only builtin defaults,
   plugin defaults, user configuration, and the selected machine overlay should
   participate.
6. **Limit active oneshots, not historical oneshots.** Completed commands must not
   consume execution capacity.
7. **Do not make `service` a Proc kind.** Add semantic service metadata and a
   `service-proc` lifecycle, preserving kind compatibility.

## Recommended domain model

### SASE Service

`sase service run` is a foreground, single-instance host process. It acquires a lock
within `SASE_HOME`, loads the host-only effective service catalog, validates it before
launching children, and exposes a local control channel. It reconciles desired state to
observed process state and writes an atomic versioned snapshot for read-mostly clients.

A practical local layout is:

```text
~/.sase/service/
  service.lock
  control.sock
  status.json
  logs/
```

The exact paths can change, but the properties matter:

- only one service host can own a SASE home;
- mutations go through an authenticated local control socket rather than racing state
  files;
- TUI/status reads have an atomic snapshot and change token;
- service-host and child logs have a predictable location even when no TUI is open.

On SIGTERM, the host marks itself stopping, sends the configured stop signal to all
child process groups, waits up to their stop timeout, escalates remaining children,
writes final state, and exits. Native stop/restart actions do not race child repair.

### Service definition and stable identity

A persistent service definition has a stable, namespaced ID:

- `builtin@supervisor`
- `builtin@gateway`
- `sase-telegram@inbound`
- `user@dev-proxy`

Short names may be accepted by the CLI only when unambiguous. Namespacing prevents a
plugin or user definition from accidentally shadowing a builtin. A definition carries
provenance so diagnostics can identify the source layer and conflicting override.

The minimal persistent definition should contain:

```yaml
service:
  procs:
    user@dev-proxy:
      description: Local development proxy
      command: [python, -m, my_proxy, --port, "8080"]
      enabled: true
      cwd: /home/me
      env:
        LOG_LEVEL: info
      restart: on-failure       # always | on-failure | never
      stop_timeout: 15s
      healthcheck:              # optional; omit for ordinary process liveness
        tcp: 127.0.0.1:8080
        interval: 30s
        timeout: 2s
```

Simple services are therefore entirely declarative. Complex services remain possible
because `command` can point to an arbitrarily sophisticated executable supplied by a
plugin. The manager should resist exposing Python callbacks for start/stop/health:
executable boundaries are testable, portable, and isolate plugin failures from the
manager. An explicit `shell: true` can be supported for user definitions, but it
should not be the default.

Plugin defaults should use the config plugin mechanism already present in SASE. For
example, `sase-telegram` can add a `sase_config` entry point whose packaged
`default_config.yml` contributes `sase-telegram@inbound` with `enabled: false`.
Machine configuration then enables it. If the definition prefix refers to a plugin
that is missing or disabled, the catalog retains an unavailable entry and an
actionable reason.

Configuration precedence should remain familiar, with one deliberate restriction:

```text
builtin defaults
  < plugin defaults
  < user config
  < selected machine overlay
```

Project-local configuration is excluded even if `sase service` is invoked from a
project. This makes native startup deterministic and avoids granting an arbitrary
checkout persistent execution authority merely by becoming the current directory.

### Desired and observed state

The manager should keep persistent enablement separate from a runtime override:

- **enable**: persistently set enabled and start it now;
- **disable**: persistently set disabled and stop it now;
- **start**: run it for this service-host generation without changing configuration;
- **stop**: stop it for this service-host generation without changing configuration;
- **restart**: stop and start now, preserving enablement.

An enabled proc stopped at runtime starts again when the outer SASE Service is next
started. A disabled proc stays disabled across restarts. The CLI and TUI should state
this distinction in help and action labels; otherwise users will reasonably assume
that Stop is durable.

The effective state for each stable service ID should include:

- definition provenance and effective enabled state;
- runtime desired override;
- phase: `disabled`, `stopped`, `starting`, `running`, `backoff`, `failed`, or
  `unavailable`;
- current Proc ID and PID, if any;
- restart attempt count and next attempt time;
- last exit, last error, and latest health result;
- service-host generation.

Restart policy should use capped exponential backoff with jitter and expose a
crash-loop/degraded state. Ordinary process liveness is the default health signal.
Declarative TCP or exec health checks are useful for gateway-like processes, but they
should not expand into dependency scheduling.

### Relationship to durable Procs

A stable service proc is not itself a process execution. Every launch creates a new
durable Proc record with:

- existing compatible kind (`command` or `detached`, as appropriate);
- new lifecycle `service-proc`;
- additive service metadata: stable service ID, mode (`persistent` or `oneshot`),
  manager generation, and attempt number.

The stable Service tab node aggregates the current and latest execution. The Procs tab
can reveal every attempt and its retained output by removing `-service`. This gives
restart history without mutating one Proc record into several lifetimes.

Generic Proc actions must respect ownership. Killing a service-owned Proc directly
without changing desired state would make the manager restart it. `sase proc kill`
should either route the action to the service host as a service-proc stop or reject it
with the correct `sase service proc stop` command.

The shared schema, validation, state classification, and restart-transition rules
belong in `sase-core`. Python should handle platform integration, plugin discovery,
thin command adapters, and Textual presentation. This follows the repository's Rust
core boundary: CLI, TUI, and future clients must agree on service semantics.

## Recommended CLI

The command tree should follow SASE's exact-child default and option conventions:

```text
sase service                         # exact alias for `sase service list`
sase service init [--check]
sase service list [--json]
sase service restart
sase service run                    # foreground native-service entrypoint
sase service start
sase service status [--json]
sase service stop
sase service uninstall

sase service proc                   # exact alias for `... proc list`
sase service proc disable ID
sase service proc enable ID
sase service proc list [--json]
sase service proc restart ID
sase service proc run [OPTIONS] -- COMMAND...
sase service proc start ID
sase service proc status ID [--json]
sase service proc stop ID
```

Public long options should receive short aliases under the project's CLI rules, and
service IDs should be positional. JSON output must be versioned and include desired
and observed state rather than only a PID.

The root lifecycle commands control the native unit. They should not secretly create a
second detached service host when native installation is absent; instead they should
return an actionable `sase service init` instruction. `sase service run` is the sole
foreground manager entrypoint used by systemd/launchd and by integration tests.

`sase supervisor` remains the domain command for routines, jobs, maintenance, and
Supervisor-specific status. Its lifecycle aliases delegate to
`sase service proc ... builtin@supervisor`. A hidden/deprecated `sase axe` alias can
preserve scripts for a release window. AXE's independent desired-state files and
watchdog must not remain active after migration.

### `sase init` integration

`sase service init` is idempotent and noninteractive. It renders the platform artifact,
validates its executable path and permissions, installs or updates it, reloads the
native service manager, enables startup, and starts the SASE Service. `--check` reports
drift without mutation. `uninstall` stops and removes the native artifact but does not
delete Proc history, configuration, or logs unless a separate purge is explicitly
requested.

`sase init` should treat service installation as a **host-scoped initializer**, not a
per-project initializer. The current `--all` flow loops projects, so merely adding the
question inside that loop risks repeated prompts. The clean implementation extends
the init registry with host/project scope and runs host initializers once outside the
project loop. A batch sentinel such as `service_offer_handled` is an acceptable
transitional patch, but scope is the durable model.

Expected behavior:

- interactive `sase init`: prompt once, “Install and start the SASE Service?”;
- `sase init --all`: the same prompt exactly once for the host;
- `sase init --all --yes`: install once without a prompt;
- check/dry-run modes: report the host plan once;
- an explicit init target may invoke the same implementation directly.

## Native integration

### Linux/systemd

Install a user unit at `~/.config/systemd/user/sase.service` with approximately:

```ini
[Unit]
Description=SASE Service

[Service]
Type=simple
ExecStart=/absolute/path/to/sase service run
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

The absolute executable should be captured and checked for drift. The foreground host
must not fork. The outer restart policy protects against service-host failure; the
inner manager independently applies per-child policy. An explicit `systemctl --user
stop` does not cause `Restart=on-failure` to bring the unit back, which matches the
desired root lifecycle.

Enabling the unit attaches it to the user manager's default target. Starting at machine
boot without a login additionally requires lingering. `sase service init` should detect
linger. It should explain that login-start works without it and give the exact
`loginctl enable-linger` remediation, but it should not silently elevate privileges.
Athena and apollo already have lingering enabled.

Use only systemd features available on both observed hosts. In particular, do not
depend initially on newer `RestartSteps` behavior when apollo runs systemd 255; the
SASE Service itself can implement portable child backoff.

Authoritative references:

- [systemd.service](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [systemd.unit](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html)
- [loginctl](https://www.freedesktop.org/software/systemd/man/latest/loginctl.html)

### macOS/launchd

Install a per-user LaunchAgent at
`~/Library/LaunchAgents/org.sase.service.plist`. Its essential properties are a unique
`Label`, an absolute `ProgramArguments` array ending in `service run`, `RunAtLoad`, a
failure-oriented `KeepAlive` policy, and explicit stdout/stderr log paths. Bootstrap it
in the user's GUI domain and use launchd lifecycle commands for start/stop/restart.
The file must not be group- or world-writable.

Apple's launchd guidance explicitly says launchd-managed processes must not daemonize,
should catch SIGTERM, should use plist keys for working directory and standard output,
and should tolerate changing network availability. It also distinguishes per-user
LaunchAgents, which start at login and stop at logout, from system LaunchDaemons.
Those constraints support the same foreground host design as systemd and require the
startup-semantics adjustment above.

Authoritative reference:

- [Apple: Creating Launch Daemons and Agents](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html)

A privileged LaunchDaemon mode could later support true pre-login startup, but it
introduces root installation, user/home discovery, permissions, and config ownership.
It should not block the safe LaunchAgent implementation.

## Service tab design

The canonical tab identifier should become `service`, with persisted/CLI values `axe`
and `supervisor` normalized as compatibility aliases during migration. The visible
label is **Service**. It is cleaner to migrate directly from AXE to Service than to
ship a short-lived public Supervisor tab name.

The tree should have this shape:

```text
Service
├─ Supervisor                         running
│  ├─ checks                          running
│  │  ├─ job-a                        idle
│  │  └─ job-b                        failed
│  ├─ telegram                        running
│  │  └─ tg-outbound                  idle
│  └─ ...
├─ Gateway                            running
├─ Telegram inbound receiver          disabled
├─ Personal beta proc                 unavailable: plugin missing
└─ Oneshots
   ├─ ◆ pytest tests/unit/...          running
   └─ ◇ rg TODO src/                   exited 0
```

Top-level persistent nodes correspond to configured service procs. The Supervisor is
special only in presentation: its existing routine nodes and job grandchildren remain
beneath it. The routine/job actions, output, edit behavior, and status should be
retained. Other persistent services are normally leaves. Disabled and unavailable
nodes are visible but visually subdued, with the reason close to the label.

Oneshots belong in a visually distinct section with a compact glyph/color treatment.
They remain service proc nodes semantically, but they have no persistent enablement and
always use restart policy `never`. Rerun creates a new oneshot; dismiss removes it from
visible history according to retention rules. A configurable active-oneshot limit can
default to nine while history remains unbounded by slots and is eventually pruned by a
documented retention policy.

When a service proc node is selected, the action model offers Start, Stop, Restart,
Enable, and Disable when those actions are meaningful. Enable/Disable must clearly say
that machine configuration is being changed. The edit must preserve configuration
provenance: an override should be written to the selected machine overlay, not back
into builtin/plugin packaged defaults. Runtime action requests should be durable Proc
operations or control-socket requests so a TUI restart does not lose intent.

The TUI implementation must preserve existing performance constraints:

- no filesystem, socket, process, or config work on the Textual event loop;
- consume the atomic service snapshot/change token off-thread;
- cache parsed/display state and update only affected nodes;
- make refresh tasks pump-free and generation-aware;
- maintain the navigation/refresh p95 target below 16 ms.

The existing AXE display adapter can initially be nested beneath a synthetic
Supervisor service node while the backend is migrated. That reduces UI risk, provided
the synthetic node is replaced by real service state before the old AXE lifetime owner
is removed.

### Procs tab and global indicator

Add a negatable `service` boolean to the Procs query profile and adapter. Initialize
the pane's query state to `-service`, so service executions are hidden by default but
the filter is explicit and removable. The filtering cache key must include any new
service metadata/version that can change the boolean classification.

The top-right gear/active-proc count should exclude `service:true` rows as well as
monitor rows. The Service tab itself is the visibility and control surface for these
long-lived processes. Failed service state still needs prominent presentation inside
that tab and, where appropriate, a notification; hiding it from the gear cannot mean
hiding its failure altogether.

## Glossary recommendations

These definitions are deliberately concise and preserve the boundary between stable
services and individual executions.

### New terms

**Sase Service**

> The Sase Service is the single foreground manager for one SASE home, installed under
> the user's native service manager. It reconciles the enabled service-proc catalog,
> owns child process and restart policy, and publishes state for `sase service` and the
> Service tab; systemd or launchd supervises the Sase Service itself, not each service
> proc.

**Service Proc**

> A service proc is a managed unit whose executions are launched and reconciled by the
> Sase Service rather than by a submitting session. A persistent definition gets its
> stable ID and enablement from builtin, plugin, or user configuration; every launch or
> restart is a distinct durable Proc execution under that ID.

**Oneshot Service Proc**

> A oneshot service proc is a transient Service Proc for one command, with restart
> policy `never` and no persistent enablement. The `!` background-command flow creates
> these, and completed output remains available until dismissed or retained history
> expires.

**Service Node**

> A service node is a selectable semantic row in the Service tab: a service-proc node,
> a Supervisor routine or job descendant, or a oneshot service-proc node. A
> service-proc node is stable across process restarts; section labels and dividers are
> chrome, not nodes.

**Sase Supervisor** (alias: **Supervisor**)

> The Sase Supervisor is the builtin Service Proc behind `sase supervisor` that
> schedules routines and runs their jobs. The Sase Service owns the Supervisor process
> lifetime; the Supervisor owns only its routine/job tree.

### Existing terms to revise

**Sase Node** currently describes only Agents-tab rows, so using “node” in the Service
tab without revising it would create a contradiction. Replace its scope sentence with:

> A sase node is a selectable semantic row in a hierarchical SASE view. In Agents this
> includes clan, agent/member shell, workflow-step, and proc-shell rows; in Service it
> includes Service Nodes. Headers, dividers, and panel titles are chrome, not nodes.

Keep the existing Agents-specific taxonomy and aliases after that umbrella sentence.

**Routine** (alias: **Lumberjack**) should stop assigning ownership to AXE:

> A routine is an independently supervised scheduler process owned by the Sase
> Supervisor. It runs configured jobs concurrently on a fixed interval and records
> state and metrics; the Supervisor restarts it after crashes.

**Job** (alias: **Chop**) should likewise name the new owner:

> A job is one short, script-only unit of Supervisor automation. Its routine supplies
> cadence, context, guards, timeout, and deduplication; a structured result may request
> launches, which only the runner performs.

**Proc** should gain one final sentence without redefining its existing execution
semantics:

> A Service Proc is a managed subtype whose stable service identity may span multiple
> Proc executions.

I would not add “Service Proc Definition” or expose “native unit” as glossary terms
yet. They are implementation concepts rather than vocabulary users and agents must
reliably distinguish in normal work.

## Migration plan

Migration should be incremental in code but exclusive in ownership at every cutover.

### Phase 1: vocabulary, schema, and compatibility

- Add the glossary terms and revisions.
- Add service definition/state types, stable IDs, provenance, `service-proc` lifecycle,
  service metadata, and wire-version compatibility in Rust core and bindings.
- Add default config and schema entries; exclude project-local config in the service
  loader.
- Add `service` to the Procs query model while leaving the default query unchanged
  until real service Proc rows exist.
- Normalize `axe`/`supervisor` tab aliases to canonical `service`.

### Phase 2: service host and native lifecycle

- Implement the foreground host, lock, control protocol, atomic snapshot, graceful
  shutdown, restart/backoff state machine, and logs.
- Implement `sase service` and `sase service proc` commands.
- Implement idempotent systemd and launchd init/check/uninstall adapters.
- Add host-scoped `sase init` integration and the single-prompt `--all` behavior.
- Exercise concurrent-start, stale-lock, socket, crash-loop, signal, and config-reload
  cases before it owns production children.

### Phase 3: Service tab and presentation

- Replace the public tab label/ID and add stable service nodes.
- Temporarily mount the existing routine/job collector under the Supervisor node.
- Add service actions, disabled/unavailable state, and the distinct oneshot section.
- Default the Procs query to `-service` and remove service rows from the gear count.
- Measure responsiveness under many restarts/log updates before broad rollout.

### Phase 4: Supervisor ownership cutover

- Give the Supervisor a foreground entrypoint suitable for service management.
- Start it as `builtin@supervisor` and make compatibility lifecycle commands delegate.
- Move existing TUI routine/job data beneath the real Supervisor node.
- Retire AXE's detached start path, desired-state repair, ensure timer, and
  TUI-auto-ensure only after successful migration detection.

### Phase 5: oneshot migration

- Route `!` through `sase service proc run` with `restart: never`.
- Preserve output/rerun/kill/dismiss behavior and import or read legacy bgcmd history
  during a bounded compatibility period.
- Replace fixed slots with an active concurrency limit and retention policy.

### Phase 6: gateway and Telegram

- Enable builtin gateway definitions only on athena/apollo.
- Cut over one machine at a time with a port/status verification and rollback path.
- Remove the old gateway unit from chezmoi only after both machines pass.
- Add `sase-telegram` config registration, explicitly enable its receiver where wanted,
  remove periodic receiver rearm, and migrate the legacy enable flag.
- Verify there is exactly one Telegram `getUpdates` consumer before and after cutover.

### Phase 7: compatibility removal

- Remove dead AXE state and hidden aliases only after telemetry/manual inspection shows
  no active legacy installation.
- Document repair for stale native units, missing plugins, invalid machine overlays,
  and failed child shutdown.

## Verification strategy

The highest-value tests exercise ownership boundaries, not just command parsing.

**Core and config**

- deterministic merge/provenance and collision errors;
- machine override enabling a disabled plugin default;
- exclusion of project-local definitions;
- stable ID and short-name ambiguity handling;
- restart/backoff transitions, clean exit semantics, and crash-loop state;
- Rust/Python wire parity and older wire-version reads;
- `service` query classification and cache invalidation.

**Service host**

- one host per SASE home under simultaneous starts;
- graceful process-group stop and forced timeout escalation;
- new Proc record for each restart under one stable service ID;
- runtime stop versus persistent disable across host restart;
- atomic snapshot and control-socket behavior during host failure;
- missing executable, missing plugin, bad credentials, and invalid health checks;
- no restart after an explicit outer stop.

**Native installation**

- idempotent install/check/update/uninstall;
- executable-path drift reporting;
- systemd startup with and without linger and behavior on versions 255 and 257;
- launchd plist validation, bootstrap, kickstart, bootout, login startup, permissions,
  signals, and log paths.

**TUI**

- Supervisor routine/job hierarchy and all retained actions;
- persistent, disabled, unavailable, restarting, failed, and oneshot visual states;
- Start/Stop/Restart/Enable/Disable routing and failure feedback;
- default `-service` filter, user removal of the filter, and no service gear count;
- `!` concurrency, completion, rerun, dismissal, and retained output;
- no event-loop I/O and navigation/refresh p95 below 16 ms.

**Machine migration**

- no simultaneous legacy/new gateway owners;
- port 7629 responds from the new Proc and rollback restores the old unit;
- no legacy gateway unit remains enabled after verified cutover;
- one Telegram receiver only, with visible backoff on credential failure;
- Supervisor routines survive service-host restart and do not retain an orphaned AXE
  orchestrator.

## Recommended solution

Proceed with the project as a replacement architecture, using these decisions:

1. Install one per-user native service whose foreground command is
   `sase service run`.
2. Put portable service-proc reconciliation in SASE, with the shared domain and wire
   model in `sase-core` and platform/TUI adapters in Python.
3. Model a stable Service Proc separately from its durable Proc executions; every
   restart creates a new Proc record with `service-proc` lifecycle metadata.
4. Define services declaratively in host-only config. Let plugins contribute
   disabled-by-default definitions via their existing config entry-point mechanism;
   complex behavior lives behind an executable boundary.
5. Use machine overlays for persistent enablement, runtime overrides for Start/Stop,
   and bounded exponential backoff for recovery.
6. Make `sase service` default to list, provide explicit host and nested proc lifecycle
   commands, add idempotent init/check/uninstall, and make `sase init --all` run the
   host-scoped prompt once.
7. Rename the canonical tab directly to Service, show all configured states, nest
   routines/jobs beneath the builtin Supervisor node, and show transient oneshots in a
   distinct section.
8. Hide execution rows from Procs with an explicit default `-service` query and exclude
   them from the gear indicator, while retaining full history when the filter is
   removed.
9. Migrate Supervisor, background commands, gateway, and Telegram one owner at a time;
   delete each old supervision path as its replacement becomes authoritative.
10. Keep the scope intentionally smaller than a general init system. If a need is
    better served by systemd/launchd, a Supervisor routine, or the plugin executable
    itself, leave it there.

This approach gives SASE a coherent cross-platform service UX without obscuring native
lifecycle guarantees or sacrificing the durable Proc model that already works well.
