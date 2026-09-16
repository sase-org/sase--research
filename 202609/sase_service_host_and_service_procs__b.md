# `sase service`: running AXE, the gateway, and plugin services as service procs

_Researcher B · 2026-09-16 · sase `491daa988`, sase-core `f822ebd` (v0.34.37),
sase-telegram `bedb649`. I also inspected the live user units and processes on athena
and apollo, read-only._

This report uses the names from the request. **Supervisor** / `sase supervisor` is
today's AXE / `sase axe`, and **Service tab** is today's AXE tab. §4 recommends changing
both names, and explains why.

---

## 0. Verdict

**It is worth doing.** The idea fixes real problems that the code already works around
in fragile ways:

- **AXE does not start at boot.** A TUI starts it (`sase tui --restart-axe`), inside a
  `systemd-run --scope`. The only recovery path is an optional 5-minute `ensure` timer.
- **The gateway is a hand-written systemd unit.** The unit is copied onto each machine
  and runs outside SASE's control.
- **The Telegram receiver has no real supervisor.** It is kept alive only because a
  5-second job tick keeps re-submitting it. Core code also hardcodes the plugin's origin
  string so the receiver doesn't block TUI restarts.
- **macOS has no service support.**
- **Background commands are a separate mechanism.** They are not durable and do not
  record exit codes.

The request needs some changes, though:

- **Several requirements need to be sharper.** Otherwise they conflict with each other
  or break running agents. §3 lists them.
- **Two names are worth reconsidering:** "Supervisor" and "Service" (§4).
- **One design constraint is critical and not obvious.** On Linux, processes launched by
  jobs, including **agent runners**, currently live inside the AXE systemd scope's
  cgroup. If the service host becomes a systemd unit with the default kill behaviour,
  every `sase update` or `sase service restart` would kill in-flight agents (§2.6).

**Recommended shape (details in §9):**

- **One per-machine host process**, `sase service run`, registered once as a systemd user
  unit or a launchd LaunchAgent.
- **The host runs service procs**, declared in a new `service.procs` config map. Entries
  come from core builtins (`supervisor`, `gateway`), from plugin `sase_config` layers
  (Telegram), or from the user.
- **Daemons run as the host's children**, with supervisord-style restart policies.
- **Oneshots, including today's `!!` background commands, run as detached procs.** They
  run outside the host's process tree so host restarts don't kill them.
- **Every run is recorded in the existing proc store.** Each row carries a first-class
  `service` marker.
- **The Service tab** shows one node per service proc, including disabled ones (dimmed).
  Routine and job nodes nest under the supervisor node, and oneshots appear in their own
  section.

---

## 1. Method

- **Code:** I read the `sase axe` CLI, orchestrator, routines, ensure and systemd-scope
  code; the AXE TUI tab, background commands, the gear indicator, and the Admin Center
  Procs pane; the proc subsystem and its Rust store; `sase init` onboarding; and config
  layering.
- **Other repos:** I opened sase-telegram and sase-core through `sase repo open`.
- **Live machines:** I inspected `~/.config/systemd/user`, running processes, and cgroup
  membership on athena and on apollo (over SSH).
- **Prior research:** I read the earlier naming research
  (`research:202609/scheduler_loop_naming_reassessment.md` and
  `research:202609/scheduler_tui_naming/scheduler_tui_naming.md`) through
  `sase artifact read`.
- **External precedents** (primary sources, accessed 2026-09-16):
  - systemd `systemd.kill(5)` and `loginctl(1)` (systemd 257 man pages on athena);
  - launchd [`launchd.plist(5)`](https://keith.github.io/xcode-man-pages/launchd.plist.5.html);
  - [supervisord configuration](https://supervisord.org/configuration.html);
  - [process-compose](https://f1bonacc1.github.io/process-compose/launcher/);
  - [Homebrew `service do` blocks](https://docs.brew.sh/Formula-Cookbook).

---

## 2. What exists today (verified)

### 2.1 AXE ("Supervisor")

- **Process tree.** `sase axe start` runs an `Orchestrator`
  (`src/sase/axe/orchestrator.py`). It spawns one `sase axe routine run <name>` child
  per configured routine.
  - Restart: exponential backoff capped at 60s, reset after 5 minutes of uptime.
  - Crash loops (3 failures in 60s) are surfaced as notifications.
  - Shutdown sends SIGTERM, then SIGKILL.
  - Output is captured into bounded per-routine logs.
- **This is already a small process supervisor**, the same kind of program `sase service`
  would be.
- **Lifecycle machinery built around the lack of a real service manager:**
  - a lifetime flock;
  - `orchestrator.pid`;
  - `desired_state.json`;
  - a lifecycle journal;
  - wedged-lock recovery after 90s;
  - `ensure` with restart-storm damping (`src/sase/axe/ensure.py`);
  - an optional `sase-axe-ensure.timer` (`src/sase/axe/_ensure_timer.py`).
- **The systemd scope.** On Linux the TUI's start path wraps the orchestrator in
  `systemd-run --user --scope` (`src/sase/axe/systemd_scope.py`). This keeps it alive
  when the tmux pane closes. **No persistent unit exists for AXE, and no launchd code
  exists anywhere.**
- **What restarts AXE.** The TUI starts or restarts AXE at startup. AXE is also
  restarted by:
  - `sase update`;
  - plugin install, update, and uninstall;
  - feature-flag changes;
  - every AXE config save made in the TUI.

  **AXE restarts are frequent.** This matters for §6.

### 2.2 The AXE tab

- **Rows** (`src/sase/ace/tui/widgets/bgcmd_list.py`) come in three kinds, in two
  sections:
  - `LumberjackItem` (routine) rows, with `ChopItem` (job) rows nested under them;
  - `BgCmdItem` rows, below a `── commands ──` divider.
- **No orchestrator row exists.** The synthetic parent row was removed
  (`actions/axe.py:332`).
- **Keys:**
  - `x` starts or stops AXE, or kills a background command;
  - `r` runs a job or re-runs a command;
  - `e` / `a` edit or add config entries through a scope-aware transaction editor;
  - `Q` offers "quit + stop AXE";
  - bang mode: `!!` starts a background command and `!x` toggles AXE.
- **The label** is presentation-only (`_TAB_DISPLAY_NAMES["axe"] = "AXE"`,
  `widgets/tab_bar.py:22`). About 20 other user-visible "AXE" strings exist, for example
  the footer ` AXE ` pill and the help and palette categories.

### 2.3 Background commands (`!!`)

- **Storage:** 9 fixed slots under `~/.sase/axe/bgcmd/<slot>/`
  (`src/sase/ace/tui/bgcmd.py`).
- **Launch:**
  1. A durable proc runs `sase axe bgcmd-launch`.
  2. That proc optionally cleans the workspace and checks out a Patch.
  3. It then starts the command with a raw `Popen(shell=True, start_new_session=True)`.
- **Gaps:**
  - **No exit code is recorded.** `mark_slot_finished` writes only `finished_at`
    (`bgcmd.py:196`).
  - **Re-run (`r`) bypasses the durable path** and calls `start_background_command`
    directly.
- **Visibility:** the commands appear only on the AXE tab and in footer badges.

### 2.4 Procs

- **Model.** A proc is one command under one detached supervisor process (a
  double-forked `supervisor_bootstrap.py`).
- **No restart policy exists.** A lost supervisor or a reboot settles the row as `error`.
- **Kinds are validated in Rust.** `PROC_KINDS = ["command", "tui", "detached"]` is at
  sase-core `crates/sase_core/src/procs/store.rs:24`. `submit_proc_request` forces
  `kind="command"` (`src/sase/procs/service.py:88`). The glossary calls kinds
  "compatibility labels rather than permanent semantic categories", **so a new `service`
  kind is the wrong marker.**
- **Name collisions:**
  - `src/sase/procs/service.py` is already named "service" (a typed proc-shell service
    layer).
  - "supervisor" appears on about 218 Python lines across 81 files, almost all meaning
    the **per-proc detached supervisor**. That includes the wire fields `supervisor_id`
    and `supervisor_claimed_at` and the Rust call `claim_proc_supervisor`.
  - The glossary's *Sase Monitor* strand says a monitor runs "under a detached
    supervisor."
- **The Procs pane query language** (`ace/query_profile/profiles/_procs.py`):
  - supports `-field:value` negation and a derived boolean `monitor`
    (`origin == "monitor"`);
  - **has no `service` field.** A bare `-service` today is a *free-text* exclusion: it
    would hide any proc whose label or command merely contains the word "service" and
    would not hide actual service procs;
  - **has no default value.** It starts empty and lasts only for the life of the TUI
    process (`config_center_session.py:72`).
- **The gear indicator** counts every proc for which `proc_is_relevant` is true
  (`ace/tui/_proc_observer_store.py:126`). **Any row with `session_id is None` counts.**
  The live Telegram receiver row (`mnqrkm88fdgq`, origin `telegram-receiver`,
  `session_id: null`) therefore shows as a gear chip in every TUI session today.

### 2.5 Gateway and Telegram receiver

- **`sase_gateway`** is a Rust HTTP server shipped as a console script by the
  `sase-core-rs` wheel. It binds `127.0.0.1:7629` and serves the mobile and fleet APIs.
  - Python only runs it in the foreground (`sase mobile gateway start`).
  - `docs/remote_dispatch.md:62-119` gives manual `systemd-run` and launchd plist
    recipes.
- **The installed gateway units** on athena and apollo are the same hand-written
  `~/.config/systemd/user/sase-gateway.service`: `Type=simple`, `Restart=on-failure`,
  `Wants/After=network-online.target`. Two defects:
  - **The unit omits the `--agent-bridge-command` and PATH environment** that
    `remote_dispatch.md` recommends.
  - **`network-online.target` does not exist in the user manager.**
    `systemctl --user status network-online.target` reports "could not be found", so
    that dependency does nothing.

  Apollo also has a stray `sase-gateway.service.bak-sase-xe.16.11.5`. Both machines have
  `Linger=yes`.
- **The Telegram receiver.** A user-config routine `telegram` (5s interval) runs
  `sase_job_tg_inbound`. Each tick calls `ensure_receiver_running()`
  (sase-telegram `src/sase_telegram/receiver.py`), which does the following:
  1. It submits a proc with `origin="telegram-receiver"`.
  2. It sets both `concurrency_keys` and `request_fingerprint` to
     `telegram-receiver:<chat_id>`, so repeat calls replay the same row.
  3. It uses **no timeout**.

  The module docstring explains why: "SASE's proc supervisor does not auto-relaunch a
  crashed supervised proc, so this per-tick re-arm … is what gives the receiver its
  restart resilience."
- **The receiver exits 0 by design** when `~/.sase/telegram_is_enabled` is missing or
  credentials fail (`sase_tg_inbound.py:4826-4833`). A naive "always restart" policy
  would make it flap.
- **Core hardcodes the plugin's origin.** `src/sase/ace/tui/update_restart.py:91-106`
  excludes `origin == "telegram-receiver"` from blocking TUI self-update restarts, under
  the comment "durable services that outlive ACE by design". This is exactly the service
  concept, currently implemented as a string match on a plugin's private origin.

### 2.6 The cgroup finding (critical for the design)

athena currently has **four active** `sase-axe-*.scope` transient units, although only
one orchestrator is running. Their cgroups contain:

| Scope | Members |
| --- | --- |
| `sase-axe-3848459-….scope` (an old AXE instance) | the Telegram receiver's proc supervisor and receiver (up 1d20h), plus a `run_agent_runner.py` agent |
| two other old scopes | only `run_agent_runner.py` agent processes |
| the current scope | the orchestrator and its 11 routines |

Every process an AXE job launches, **agents included**, inherits the launching scope's
cgroup. systemd's documented default for services is `KillMode=control-group`: "all
remaining processes in the control group of this unit will be killed on unit stop". The
docs also say `process` and `none` are "not recommended" because processes "escape the
service manager's lifecycle" (`systemd.kill(5)`).

**Consequence.** If `sase service` becomes a systemd unit and job-launched agents,
detached procs, and background commands keep spawning inside it, then
`systemctl --user restart sase.service` (or `sase update`) kills all of them. **The design
must place long-lived detached work in its own transient scopes** (§9.4). The existing
`systemd_scope.py` is the seed of that helper.

### 2.7 `sase init` and config layering

- **`sase init` onboarding** is a registry of `InitCommandSpec(name, label, plan, run)`
  steps: `config`, `machine`, `memory`, `repo`, `skills`
  (`src/sase/main/init_registry.py`).
  - Each step plans first and supports `-c/--check`, `-d/--diff`, and `-y/--yes`.
  - The prompt is `Run \`sase init <cmd>\` now? [y/N/d]`
    (`_init_onboarding_apply.py:18-43`).
- **"Offer once" under `--all` already exists, but only for `machine`.** It is a
  `machine_offer_handled` flag (`_init_onboarding_batch.py:20-25`) plus two
  `plan.command == "machine"` special cases (`_init_onboarding_apply.py:24,101-108`).
- **Config layers, in order:**
  1. package defaults;
  2. **plugin `sase_config` layers** (a plugin ships its own `default_config.yml`);
  3. `~/.config/sase/sase.yml`;
  4. **selected `sase_*.yml` overlays**, including the machine overlay matched by
     `id.machine_name` (chezmoi-guarded per host);
  5. project-local `sase.yml` in the cwd.

  Plugins can therefore contribute config, and per-machine overrides already have a home.
- **The AXE entry editor** already writes config through a scope rail (user, overlays,
  local) with chezmoi apply.

---

## 3. Requirement adjustments I consider objective improvements

Each item below changes or sharpens a stated requirement. **They are clearly flagged
because they alter what was asked.**

| # | Requirement as stated | Adjustment | Why it's objectively better |
| --- | --- | --- | --- |
| **O1** | "Each active/enabled service proc should have a node" | **Also show disabled (and stopped) service procs, dimmed.** They can be hidden with the existing `.` hide toggle. | You can't select a node that isn't rendered, so "enable from the Service tab" is impossible if disabled procs have no node. |
| **O2** | start/stop/enable/disable | **Define persistence explicitly.** `stop` holds until `start` or the next boot (keyed to boot id, like systemd). `disable` persists on *this machine* until `enable`. | Without this, "I stopped the gateway" becomes ambiguous after `sase update` restarts the host. systemd users already expect stop ≠ disable. |
| **O3** | `sase service` runs inside a systemd/launchd service | **Long-lived detached work must escape the unit.** On Linux that is a transient scope per agent, detached proc, or oneshot; on macOS, `AbandonProcessGroup=true` plus `setsid`. The unit uses `KillMode=mixed`. | §2.6: otherwise every host restart or `sase update` kills running agents and background commands. |
| **O4** | host reads service config | **The host resolves config from machine-level layers only:** defaults, plugins, user, and overlays, but **not** a project-local `sase.yml`. | The host runs from `$HOME` at boot. Its behaviour must not depend on the cwd it was started from. |
| **O5** | (implicit) | **The unit's `ExecStart` must be the stable install**, never a numbered `sase_N` workspace. This reuses `should_reexec_axe_start_from_canonical`. | Workspace checkouts are ephemeral. AXE already enforces this for `axe start`. |
| **O6** | supervisor becomes a service proc | **Retire the parallel watchdogs** behind sunset flags: the `sase axe ensure` timer, the TUI's direct `start_axe_daemon` start, and the scope wrapper around `axe start`. | Two independent restarters for one process race each other. These are the duplicate-start and lock-contention races that the existing wedged-lock recovery and ensure storm damping already defend against. |
| **O7** | `sase service init` installs the service | **Build it as a plan/apply init step** with `--check/--diff`. It should also **detect legacy units** (`sase-gateway.service`, `sase-axe-ensure.*`, the `sh.sase.gateway` plist), **check lingering** on Linux, and **remember a decline**. | Legacy units hold port 7629, so the builtin gateway would fail to bind. Without linger, user units don't start at boot. Without a decline marker, `sase init --check` nags forever on machines where the user said no. |
| **O8** | "prompt only once with `-a`" | **Generalize the existing machine-only special case** into an `InitCommandSpec.scope = "machine"` attribute and a `prompt_command` field. Both `machine` and `service` then use it. | Adding a second `plan.command == "service"` branch copies an ad-hoc pattern. The underlying rule is "machine-scoped steps run once per invocation". |
| **O9** | service procs "run and managed" | **Service procs need a restart policy with a clean-exit rule, plus start conditions.** Examples: `restart: on-failure`, `when: {path_exists: ~/.sase/telegram_is_enabled}`. | The Telegram receiver exits 0 on purpose when disabled (§2.5). An always-restart policy would make it flap. |
| **O10** | hide from Procs tab via `-service`; no gear | **Add a first-class `service` marker to the proc wire**, a `service` boolean to the procs query dialect, and make the gear filter use that marker. Delete the core `telegram-receiver` origin check. | Today `-service` is a free-text match (§2.4) and the gear counts every session-less row. Core must not depend on a plugin's private origin string. |
| **O11** | `sase supervisor` becomes a builtin service proc | **`sase supervisor start/stop/restart/status` must delegate to the host** (`sase service proc <verb> supervisor`). The foreground entry point becomes `sase supervisor run`. | One process with two control paths (lifetime lock vs. host desired state) produces fights. The host must be the only thing that starts the supervisor. |
| **O12** | Procs tab prefilled with `-service` | **Make the default query a config value**, `tui.procs.default_query: "-service"`, so users and tests can change it. | A hardcoded prefill is a hidden policy. The Procs pane already has a session-state field to seed. |

---

## 4. Critique: naming and scope (judgment calls, flagged)

### 4.1 "Supervisor" is the wrong name for AXE once `sase service` exists

- **In industry usage, the *supervisor* is the program that runs and restarts
  services.** supervisord's `[program:x]` and runit's `runsv` both work this way. In the
  new architecture, that program is **`sase service`**. AXE's defining job is
  *scheduling jobs*. Its routine supervision is an implementation detail, and an optional
  later phase (§5, option D) moves it into the host.
- **The name also collides internally.** It overlaps with the per-proc "detached
  supervisor" in about 218 code lines, in Rust wire fields, and in the *Sase Monitor*
  glossary strand. "The supervisor restarted the supervisor's proc supervisor" is a
  realistic support sentence under this naming.
- **Recommendation:** name the builtin **`scheduler`** (`sase scheduler`, "Scheduler"
  node). The prior naming research reached the same conclusion for the CLI noun.
- **If you keep "Supervisor":** reword the proc-level concept in prose and glossary
  ("proc keeper" or "detached runner") so that SASE has exactly one thing called a
  supervisor.

### 4.2 "Service" vs "Services" for the tab

The sibling tabs are plural (**Agents**, **Artifacts**), and the tab lists many service
procs. **"Services" is the consistent label.** The CLI noun should stay singular
(`sase service`), matching `sase proc`, `sase agent`, and `sase bead`.

### 4.3 "Service" is overloaded three ways, so fix the vocabulary up front

"Restart the service" could mean the platform unit, the host, or one service proc. Adopt
and enforce three terms:

- **platform unit** — the systemd unit or launchd LaunchAgent (`sase.service`,
  `sh.sase.service`);
- **sase service** (the host) — the process that unit runs;
- **service proc** — the things the host runs. **Never use bare "service" for these.**

Also rename the internal `src/sase/procs/service.py`, for example to `lifecycle.py`.
It is cheap and internal.

### 4.4 Are background commands really "service procs"?

- **Where the fit is weak.** They are ad-hoc, user-typed, project/workspace-scoped shell
  commands. Service procs are machine-scoped, configured, long-lived programs.
- **The honest precedent** is systemd's split between **oneshot** (a unit that runs to
  completion) and **transient** (a unit created at runtime by `systemd-run`, not from a
  file).
- **The unification pays off if the model has two orthogonal attributes:**
  - `mode: daemon | oneshot`;
  - `source: builtin | plugin | config | transient`.

  Background commands are then **transient oneshots**. Configured oneshots are useful in
  their own right, for example "at host start, prune tmp" or "warm caches after boot".
- **Keep the user-facing word "command"** for `!!` in the TUI so muscle memory and docs
  still read naturally. Rows are "oneshot nodes"; the concept is a transient oneshot
  service proc.

### 4.5 Gateway enabled-by-default?

- **The argument for off by default.** A builtin gateway that starts on every install
  opens a loopback HTTP API on machines that never pair a phone or join a fleet.
- **Recommendation:** ship `gateway` **disabled by default** in core defaults. Enable it
  in the machine overlay, or have `sase machine init` / mobile pairing flip it on.
  athena and apollo enable it explicitly.

### 4.6 Don't build a plugin Python API yet

- **Config already covers the known plugin case.** Plugins can already contribute
  `service.procs` entries through `sase_config`, and the one known plugin case
  (Telegram) needs nothing more.
- **Per the decision `corpus-before-mechanism`,** defer a `sase_service_procs`
  entry-point group until a plugin needs *dynamic* expansion, for example one receiver
  per configured bot.
- **Design the internal builtin-launcher interface so it can become that API later.**

---

## 5. Architecture options

| Option | Summary | Pros | Cons | Verdict |
| --- | --- | --- | --- | --- |
| **A. One platform unit per service proc** (the `brew services` / `foreman export` model) | `sase service init` writes `sase-supervisor.service`, `sase-gateway.service`, a Telegram unit, and so on; systemd/launchd does all supervision. | Native restart and logging; no custom daemon. | Every per-proc action from the TUI becomes a platform-specific `systemctl`/`launchctl` call. Plugin-added procs require re-running init. There is no fallback on hosts without a service manager, and transient oneshots have no macOS story. Platform differences leak into every feature. | Reject |
| **B. One host process owning service procs** (the supervisord / process-compose model) | One platform unit runs `sase service run`, which spawns and restarts service procs as its children and mirrors each run into the proc store. | One platform integration point. Same semantics on Linux, macOS, and "no service manager" (detached fallback). Config reload without re-init. Reuses the orchestrator's proven backoff and crash-loop code. Stopping the unit stops all daemons, which is correct. | Adds a Python process. Needs escape scopes for work that must outlive it (§2.6). | **Adopt for daemons** |
| **C. Reconciler over detached procs** (generalize Telegram's `ensure_receiver_running`) | The host only ensures each enabled service proc has an active proc-store row, launched through the existing detached per-proc supervisor. | Service procs survive host restarts. Reuses the proc lifecycle entirely. | One extra supervisor process per daemon. Restart latency is bounded by polling. The platform unit no longer stops what it started. After upgrades you *want* daemons restarted anyway. | **Adopt only for oneshots**, which *should* survive host restarts |
| **D. Flatten: the host replaces the orchestrator** | Each routine becomes its own service proc, and "supervisor" becomes a node group. | Removes one supervision layer and the duplicated lifecycle code. | AXE restarts are frequent (config saves, flags, plugin changes, §2.1). If routines are host children, those restarts become per-routine churn, and `sase supervisor restart` semantics (heartbeat verification across routines) must be rebuilt. Larger blast radius. | **Defer.** Revisit once B is stable and if the two lifecycle layers prove costly. |
| **E. Do less** | Keep AXE as-is. Only add `sase service init`, which installs two fixed units (AXE and gateway), and filter the receiver out of the gear. | About 20% of the effort for the boot-start win. | No plugin services, no per-proc UI, no background-command unification. Each new daemon needs new platform code. | Fallback if the epic is too large right now |

**Why B keeps the host separate from the supervisor** rather than making the orchestrator
the host: the supervisor restarts often. Every AXE config save, flag flip, or plugin
change restarts it. The gateway and Telegram receiver should not bounce each time.

---

## 6. Proposed glossary terms

Glossary strands must describe shipped behaviour. **Land these in the epic's final
phase**, after checking each sentence against the implementation, through
`/sase_memory_write` with the plan as authorization. The text below is the proposed
wording. It uses the recommended names; substitute "Supervisor" if you keep it.

**New strand: `Sase Service`** (aliases: `service host`, `sase service`)

> The sase service is the per-machine host process (`sase service run`) that starts,
> restarts, and stops that machine's service procs, with at most one per SASE home.
> `sase service init` registers it as a platform unit — a systemd user unit on Linux, a
> launchd LaunchAgent on macOS — so it starts at boot or login; without one,
> `sase service start` runs it detached. Say "service proc" for what it runs and
> "platform unit" for its systemd/launchd registration; bare "service" is ambiguous.

**New strand: `Service Proc`** (aliases: `service procs`)

> A service proc is a named proc the sase service owns, declared under `service.procs`
> by core (builtin), a plugin's config layer, or the user, or created at runtime as a
> transient oneshot. Its mode is `daemon` — kept running under its restart policy — or
> `oneshot` — run once to completion. Start, stop, enable, or disable one with
> `sase service proc` or from its Services-tab node; `enabled: false` in a machine
> overlay keeps it off that machine. Service proc runs are recorded in the proc store
> but hidden from the Procs tab and the proc gear by default.

**New strand: `Oneshot Service Proc`** (aliases: `oneshot`, `background command`)

> A oneshot service proc runs once to completion and is never restarted. Configured
> oneshots run when the sase service starts; transient oneshots are created at runtime,
> by the TUI's `!!` background commands or `sase service proc run`. Oneshots run outside
> the sase service's process tree, so restarting the sase service does not kill them.
> Distinct from a job, which a routine runs on a schedule.

**New strand: `Scheduler`** (aliases: `AXE`, `axe`, `Supervisor` if renamed otherwise)

> The scheduler is the builtin service proc that runs SASE's background automation: it
> starts one process per routine and restarts crashed routines, and routines run jobs.
> Control it with `sase scheduler` or from its Services-tab node, under which its
> routine and job nodes nest. AXE is its former name and remains an accepted alias for
> older commands, config, and state paths.

**New strand: `Service Node`**

> A service node is one row of the Services tab: a service proc node, a oneshot node,
> or — nested only under the scheduler's node — a routine node and its job nodes.
> Section dividers and the host status line are chrome, not nodes.

**Edits to existing strands**

- **`Sase Node`:** generalize it from "one row of the Agents tab's agent tree" to "one
  selectable row of a TUI tree". The Agents-tab node kinds stay as listed, plus "on the
  Services tab, a service node". Keep "banners, dividers and panel titles are chrome".
- **`Routine`:** replace "An AXE routine … The AXE orchestrator starts it" with "A
  scheduler routine … The scheduler starts it". Keep the Lumberjack alias sentence.
- **`Job`:** replace "unit of AXE automation. AXE supplies" with "unit of scheduler
  automation. The scheduler supplies".
- **`Proc`:** append "Runs of service procs are procs marked with a `service` block;
  the Procs tab hides them by default." Also consider dropping the aliases
  `background task(s)`, which now read as a near-synonym of "background command" (a
  oneshot).
- **`Sase Monitor`:** if "Supervisor" is kept for AXE, change "under a detached
  supervisor" to the new name for the per-proc runner.

That is five new terms and five edited ones. Only term names reach the always-loaded
roster, so the per-turn cost is small.

---

## 7. Config design: simple is easy, complex is possible

### 7.1 Schema (composed and validated in sase-core, like `axe_config_compose`)

```yaml
service:
  restart_backoff_max_seconds: 60          # host-wide defaults
  crash_loop: {starts: 3, window: "60s"}   # then state=failed + one notification
  condition_poll: "30s"                     # re-evaluate `when:` for stopped-by-condition procs
  procs:
    <name>:                                 # map keyed by name → merges by name across layers
      description: "…"
      enabled: true                         # default true
      mode: daemon                          # daemon | oneshot
      command: "autossh -N tunnel"          # string → sh -c; list → argv; exactly one of command/builtin
      builtin: gateway                      # core-provided launcher (plugins may not use)
      cwd: "~"                              # default $HOME
      env: {KEY: value}
      restart: on-failure                   # daemon: on-failure (default) | always | never
      success_exit_codes: [0]               # "clean" exits for on-failure
      when:                                 # all must hold to start; re-checked every condition_poll
        path_exists: "~/.sase/telegram_is_enabled"
        env_set: [TELEGRAM_BOT_TOKEN]
        executable: sase_job_tg_inbound
        platform: [linux, macos]
      after: [gateway]                      # start ordering only (not a health dependency)
      stop_signal: TERM
      stop_timeout: "10s"
      log_max_bytes: 2097152
```

Design notes:

- **Map form merges by name** across layers, like job maps
  (`docs/axe.md:699`). This is what makes disabling a one-liner.
- **`builtin:` maps to an internal launcher.** The launcher computes argv from existing
  config sections, so the gateway reads `mobile_gateway.*` and the scheduler reads
  `axe.*`/`scheduler.*` and nothing is duplicated. The launcher interface is the future
  plugin API (§4.6).
- **`command:` is resolved like job scripts:** first the venv `bin`, then `PATH`. A
  plugin can therefore name its own console script without an absolute path.
- **`when:` stays deliberately small.** It is evaluated by the host, and a proc whose
  condition fails shows as "waiting: condition", not "failed".
- **Every child gets a small environment contract:**
  - `SASE_SERVICE_PROC=<name>`;
  - `SASE_SERVICE_STATE_DIR=~/.sase/service/procs/<name>/`;
  - `SASE_SERVICE_STATUS_FILE`.

  A proc *may* write `status.json` with `{summary, state: ok|degraded, updated_at}`. The
  Services tab shows the summary on the node. This is the whole "complex service"
  protocol for v1: a complex service is any program, and the host needs no knowledge of
  its internals.

### 7.2 Examples

**Simplest user service (three lines):**

```yaml
service:
  procs:
    tunnel: {command: "autossh -M 0 -N buildbox"}
```

**Core defaults (`src/sase/default_config.yml`).** From here on, `scheduler` is the builtin the
request calls `supervisor` (see §4.1); substitute that name if it is kept.

```yaml
service:
  procs:
    scheduler:    {builtin: scheduler, description: "Background automation: routines and jobs"}
    gateway:      {builtin: gateway, enabled: false, description: "Mobile and fleet HTTP gateway"}
```

**sase-telegram ships a `sase_config` layer.** This is new for the plugin, which today
declares no entry points:

```yaml
service:
  procs:
    telegram_receiver:
      description: "Telegram inbound long-poll receiver"
      command: [sase_job_tg_inbound, --receiver]
      restart: on-failure            # exits 0 when disabled → stays down, no flapping
      when:
        path_exists: "~/.sase/telegram_is_enabled"
```

`ensure_receiver_running()` becomes a no-op when the service proc is configured. Keep it
behind a sase-telegram sunset flag for older sase versions.

**Disabling a proc on one machine** (`~/.config/sase/sase_apollo.yml`, a machine
overlay):

```yaml
service:
  procs:
    telegram_receiver: {enabled: false}
```

---

## 8. CLI surface

This follows the CLI rules memory: alphabetical order, a short alias for every long
option, no required options, and bare groups delegating to `list`.

```
sase service init       [-c/--check] [-d/--diff] [-f/--force] [-j/--json] [-y/--yes]
sase service logs       [-f/--follow] [-n/--lines N]              # host log
sase service proc       → `sase service proc list` (central default-list convention)
  disable NAME          [-j/--json]                              # machine-local, persistent; also stops
  enable NAME           [-j/--json] [-r/--reset]                 # --reset: drop local override, follow config
  list                  [-a/--all] [-j/--json]                   # -a: include disabled + finished oneshots
  logs NAME             [-f/--follow] [-n/--lines N]
  restart NAME          [-j/--json]
  run -- CMD...         [-c/--cwd DIR] [-l/--label L] [-p/--project P] [-w/--workspace N] [-W/--wait]
  show NAME             [-j/--json]
  start NAME            [-j/--json]
  stop NAME             [-j/--json]                              # holds until start or reboot
sase service restart    [-j/--json] [-t/--verify-timeout S]
sase service run                                                 # the host, foreground (unit ExecStart)
sase service start      [-j/--json]
sase service status     [-j/--json]
sase service stop       [-j/--json]
sase service uninstall  [-j/--json] [-y/--yes]
```

Semantics:

- **`start` / `stop` / `restart`:**
  - When a platform unit is installed, they drive it: `systemctl --user` on Linux;
    `launchctl bootstrap|bootout|kickstart gui/$UID/sh.sase.service` on macOS.
  - When no unit is installed, they spawn or stop a detached host guarded by a lifetime
    lock. This preserves today's "TUI starts it" UX on machines without a unit.
  - `restart` verifies a fresh host heartbeat, reusing AXE's `_verify_startup` approach.
- **Enable/disable (machine-local) vs. config `enabled`.**
  - `enable` and `disable` write a machine-local override in `~/.sase/service/state.json`.
    Like `systemctl enable`, the override is not synced by chezmoi.
  - `enabled:` in config is the declarative default.
  - **The effective value is the override if present, otherwise the config value.**
    `show` and the TUI display provenance, for example "disabled here" vs. "disabled by
    sase_apollo.yml".
  - Editing the config value stays in the existing entry editor (`e`), with its scope
    rail.
- **Two `run` commands.** `sase service run` is the host;
  `sase service proc run -- CMD` creates a transient oneshot. Help text must contrast
  them. If that proves confusing, rename the host entry point to `sase service host`.
- **The supervisor/scheduler command delegates (O11).**
  - `sase scheduler start|stop|restart|status` becomes a thin alias for
    `sase service proc … scheduler`.
  - `sase scheduler run` is the foreground orchestrator.
  - `job`, `routine`, and `maintenance` are unchanged.
  - `ensure` is retired (O6).
- **The TUI flags rename:**
  - `--no-axe` → `--no-service` (don't start the host);
  - `--restart-axe` → `--restart-service`;
  - the old spellings are kept as sunset-flag aliases.

---

## 9. Recommended design, in detail

### 9.1 Host runtime (`src/sase/service/`, Python)

- **Startup:**
  1. Take a lifetime flock at `~/.sase/service/host.lock`.
  2. Write `host.json`: pid, boot id, start time, version, heartbeat.
  3. Load config through the machine-level layers (O4) and compose it in Rust.
- **The reconcile loop runs once per second.** It can be nudged sooner by a SIGUSR1 sent
  from the CLI or TUI after they write desired state. For each service proc, compute
  `desired` (effective enabled, runtime stop, `when:`) against `actual`, then
  start, stop, or restart.
  - **Why a state file and not a socket:** control uses a file-based desired-state store
    written under a lock, like `desired_state.json` and the proc store today. A Unix
    socket would be nicer but adds a server. A file store also lets the Rust gateway and
    mobile clients read the same state.
- **Config reload is a stat-token check on every tick,** reusing `config/core.py`'s
  stat-token caching:
  - added procs start;
  - removed procs stop;
  - procs whose resolved spec changed restart;
  - the host itself does not restart.
- **Daemons are direct children** in their own process group.
  - **Extract the orchestrator's child-supervision code** (backoff, crash loop,
    bounded-log pump, TERM→KILL) into a shared module used by both the host and the
    scheduler's routine supervision. This replaces duplication rather than adding it.
  - **Each run is mirrored into the proc store** as `kind="command"` with a new
    optional `service` block (`{name, mode, source}`), the host's identity as its
    supervisor identity, and a stable `shell_name` `service:<name>`. `sase proc show`
    and the Procs pane (with `-service` removed) keep working, and reconciliation marks
    runs `error` when the host dies. The mirror follows the existing `tui`-kind
    "runs it itself and mirrors it" precedent.
  - **Logs** go to a *stable* per-proc file, `~/.sase/service/procs/<name>/output.log`,
    bounded, with a `.1` backup. Restarts don't scatter logs, and each proc-store row
    points at that file. Restarts must not churn the 100-row terminal proc retention
    either, so exclude `service` rows from the generic history limit and keep a
    per-service last-N instead.
- **Oneshots** are submitted through the existing detached proc path
  (`submit_proc_request`) with a `service` block and `mode: oneshot`. They get durable
  rows, exit codes, `sase proc kill`, streaming, and settlement for free, and they
  survive host restarts.
- **`sase proc kill` on a daemon row** routes to the host by writing desired state
  `stopped`. It must not signal the child directly, which would just trigger a restart.
- **Updates.** `sase update` restarts the host instead of AXE. This also fixes today's
  "restart the gateway after upgrading" manual step (`docs/remote_dispatch.md:298`).
  `source_skew` detection can trigger a self-restart.

### 9.2 Linux platform unit (`~/.config/systemd/user/sase.service`)

```ini
[Unit]
Description=SASE service host (sase service)
Documentation=https://sase.sh/service/

[Service]
Type=exec
ExecStart=<stable-install>/bin/sase service run
Environment=PATH=<stable-install>/bin:%h/.local/bin:/usr/local/bin:/usr/bin:/bin
# Environment=SASE_HOME=… only when set at init time
Restart=on-failure
RestartSec=5
KillMode=mixed
TimeoutStopSec=30

[Install]
WantedBy=default.target
```

Notes on this unit:

- **No `network-online.target`.** It does not exist in the user manager (§2.5); services
  that need the network rely on `restart: on-failure`.
- **Why `KillMode=mixed`:** the host gets SIGTERM and stops daemons in reverse `after:`
  order, and anything left in the cgroup is then SIGKILLed. That is correct *only
  because* detached work escapes (§9.4).
- **Lingering.** `init` checks `loginctl show-user $USER -p Linger`. If it is off,
  `init` offers `loginctl enable-linger`. `loginctl(1)`: with linger, "a user manager is
  spawned for the user at boot and kept around after logouts". If the command needs
  privilege, route it through `/sase_sudo`-style review rather than raw sudo.

### 9.3 macOS platform unit (`~/Library/LaunchAgents/sh.sase.service.plist`)

- **Plist keys:**
  - `ProgramArguments = [<stable>/bin/sase, service, run]`;
  - `RunAtLoad = true`;
  - `KeepAlive = {SuccessfulExit = false}`. Per `launchd.plist(5)`, this restarts the
    host after a crash but not after a clean exit.
  - `AbandonProcessGroup = true`. By default launchd "kills any remaining processes with
    the same process group ID as the job".
  - `EnvironmentVariables.PATH`;
  - stdout and stderr to `~/.sase/service/logs/launchd.log`;
  - `ThrottleInterval = 10`.
- **Loading:** `launchctl bootstrap gui/$UID <plist>`, then `launchctl enable`. The label
  follows the existing doc's `sh.sase.gateway` convention.
- **Limitation.** A LaunchAgent starts at *login*, not at boot. Starting before login
  needs a root LaunchDaemon, which is out of scope. `init` and the docs should say so.
- **Test risk.** The `mac` tailnet host is often offline, so launchd paths need
  unit-level tests with a fake `launchctl` plus a manual smoke checklist.

### 9.4 Escape scopes (the critical cross-cutting change)

- **Add one helper,** `detach_scope(argv, name)`, generalized from `systemd_scope.py`.
- **When it applies:** only when the current process runs inside the sase service unit
  (detected via `INVOCATION_ID` or `/proc/self/cgroup`).
- **What it does:** it wraps detached launches in
  `systemd-run --user --scope --collect --unit=sase-<kind>-<id>`.
- **Every detach point uses it:**
  - the proc supervisor spawn (`procs/spawn.py`);
  - agent runner launches (`agent/launch_admission_coordinator.py` and the job-proposal
    launch path);
  - monitor and gate-shell spawns;
  - the gateway's agent-bridge launches.
- **Verification test:** assert that a job-launched agent's `/proc/<pid>/cgroup` is not
  under `sase.service`.
- **Side benefit:** per-agent memory and CPU accounting in systemd.
- **Cost:** tens of milliseconds per launch.

### 9.5 `sase init` integration

- **Register the step.** Add `InitCommandSpec(name="service", scope="machine",
  prompt_command="sase service init")` after `machine`.
  - The plan compares the rendered unit or plist with what is on disk and lists legacy
    units to disable (`sase-gateway.service`, `sase-axe-ensure.{service,timer}`,
    `sh.sase.gateway.plist`), each with a reason ("holds port 7629").
  - The prompt reads: ``Run `sase service init` now? This installs a login/boot service
    and disables N legacy units. [y/N/d]``.
- **Declines.** A "no" writes `~/.sase/service/init_declined`, so `--check` reports
  "declined" instead of "pending". `sase service init` always ignores the marker.
- **Once per `--all` run.** Replace `machine_offer_handled` with a
  `handled_machine_steps: set[str]` on `InitOnboardingBatchContext` (O8).
- **Tests.** Keep the pytest process guard (`_process_guard.py`) so tests never touch
  real units.

### 9.6 Services tab

Mockup (glyphs illustrative):

```
 Services · host ● running 4d · sase.service
▌ ● scheduler          running · 11 routines · up 26m
│  ▌ * hooks  3c/0e
│  │  └─ ● hook_checks
│  ▌ * waits
│  …
▌ ● gateway            running · 127.0.0.1:7629 · up 4d
▌ ● telegram_receiver  running · sase-telegram · up 1d
▌ ◌ tunnel             disabled here
▌ ◔ nightly_digest     waiting: condition (path missing)
── oneshots ──
▷ #1 just test                       running · ws 3 · 1m
✓ #2 pytest -k foo                   exit 0 · 4m ago
✗ #3 make lint                       exit 2 · 9m ago
```

- **Nodes.** Service proc nodes, routine nodes, and job nodes all use the `▌` rail.
  Oneshot nodes use a distinct left glyph (`▷`, `✓`, `✗`) and a muted colour, sit below a
  divider, and carry an exit-code chip. The **host status line is chrome**; it shows when
  the host is down and what to press.
- **Nesting.** Routine and job nodes keep today's folding (`h`/`l`/`H`/`L`, fold keys
  `lumberjack:<name>`) under the scheduler node. The scheduler node gets its own
  `service:scheduler` fold key.
- **Details pane.**
  - A service proc node shows its spec, provenance, restart history, the `status.json`
    summary, and a log tail.
  - Routine and job views are unchanged.
  - A oneshot node shows its output, like today.
- **Keys.** Keep existing muscle memory and grow bang mode into a "service" prefix:

  | Key | Action |
  | --- | --- |
  | `x` | Start/stop the selected service proc; kill a running oneshot |
  | `r` | Restart a daemon, re-run a oneshot (**now durable**), or run a job now |
  | `!!` | New oneshot (unchanged flow: project → workspace → command history) |
  | `!e` | Toggle enable/disable (machine-local) |
  | `!x` | Start/stop the host |
  | `e` / `a` | Edit/add config entries. The editor learns `service.procs` entries alongside routines and jobs. |

  Record every new binding in `default_config.yml` keymaps, per the gotchas memory.
- **Footer.** The ` AXE ` pill becomes a service-health pill, for example ` SVC 3/3 ` or
  ` SVC ! `, showing a crash-looping or failed daemon.
- **Gear indicator.** `_update_proc_indicator` / `proc_is_relevant` exclude rows with a
  `service` block (O10). The Telegram receiver stops appearing as a gear chip.
- **Procs pane.** Add `service` (boolean) and `svc:<name>` to the procs query profile,
  and seed `ProcsSessionState.query` from `tui.procs.default_query` (default
  `"-service"`, O12). Pressing `m` still cycles the monitor filter; an optional key (any
  letter still unbound in the pane) could cycle `service` → `-service` → off.
- **Quit modal.** `Q` offers "stop scheduler", not "stop host". Stopping the host would
  also take down the gateway and the receiver.
- **Label change.** Keep the internal tab id `axe` (and `--tab axe`) for now and change
  only `_TAB_DISPLAY_NAMES`. Accept `--tab services` later. The prior naming research counted about 667
  visual-snapshot PNGs that regenerate when labels change (not re-counted here).

### 9.7 Background commands → transient oneshots

- **What stays the same:** the project → workspace → history prompt, optional Patch
  checkout, `#N` display index (1–9 retained, since existing slot-numbered UI such as
  `ProcessSelectModal` and the footer badges depends on it), and output view.
- **What changes:**
  - Storage moves from `~/.sase/axe/bgcmd/<slot>/` to the proc store, with a `service`
    block of `{mode: oneshot, source: transient}`.
  - The slot becomes a display index held in a `bgcmd-slot:<n>` concurrency key; that
    key already exists.
  - **Exit codes are recorded.**
  - **Re-run is durable.**
  - `sase service proc run` gives agents and CLI users the same capability.
- **Migration.** A sunset flag keeps the old slot directories readable, so finished
  commands still show, until they age out.

### 9.8 Rust core boundary (sase-core)

These items follow the *Rust Core Is Required* decision:

- `config/service.rs`: composes and validates `service.procs` (names, exactly one of
  `command`/`builtin`, enum values, `when:` shape, `after:` cycles) and emits
  diagnostics. Python fails closed, as `axe_config_compose` does.
- The `procs/wire.rs` / `store.rs` optional `service` block: validation, the query
  field, and a retention exemption with per-service last-N.
- `service_state`: a locked store for `~/.sase/service/state.json`, holding the
  machine-local enable overrides, boot-scoped stops, and host heartbeat.
- `service_status`: a schema-versioned status wire containing the host, each proc's
  desired, effective, and actual state, provenance, restart/backoff state, and the
  status summary. The CLI `--json`, the TUI, and the gateway's mobile API all consume it.
- A pure restart-decision function (policy, history, now → start, backoff until T, or
  failed). The TUI and mobile clients can then explain "retrying in 12s" consistently.

**Process spawning, platform-unit writing, and the TUI stay in Python.** They are the
process side effects and presentation that the boundary decision explicitly keeps out of
the core.

---

## 10. Migration and rollout

Suggested epic phases. Phases 1–2 hide behind a `service_host` **beta** flag, which is
epic scaffolding removed before the epic lands. Old paths get **sunset** flags, per the
flags memory.

1. **Names and prerequisites.**
   - Decide Scheduler vs. Supervisor and Services vs. Service.
   - Rename `procs/service.py`.
   - Add the `detach_scope` helper and cgroup tests (§9.4). This phase ships value on its
     own: it fixes today's leaked `sase-axe-*.scope` units, which stay alive only because
     they still hold agents.
2. **sase-core.** Config schema, `service` proc block, state store, status wire.
3. **Host.**
   - Implement `sase service run/start/stop/restart/status/logs` and
     `service proc …`.
   - Extract the child-supervision library from the orchestrator.
   - Add the `scheduler` builtin: argv `sase axe start …` initially.
   - Hand over from a running AXE: if the orchestrator lock is held by a non-host
     process, `sase service start` stops it once and starts it under the host.
4. **Platform units.** `sase service init/uninstall`, systemd and launchd writers, linger
   check, legacy detection, the `sase init` machine-scoped step, and `sase doctor`
   checks (unit enabled, linger, heartbeat fresh, crash loops, legacy units present).
5. **Gateway and Telegram.**
   - Add the `gateway` builtin (reads `mobile_gateway.*`, adds
     `--agent-bridge-command <stable sase>`).
   - Add the sase-telegram `sase_config` layer and the `ensure_receiver_running`
     no-op-when-configured change.
   - Delete core's `telegram-receiver` origin check.
6. **TUI.** Services tab nodes, keys, footer pill, gear exclusion, and Procs query field
   with the configurable default.
7. **Oneshots.** Move background commands onto the proc store.
8. **Sunset and docs.**
   - Retire `axe ensure` and its timer (`init` uninstalls it), the axe-start scope
     wrapper, and TUI direct-start.
   - Make `sase axe`/`sase supervisor` aliases.
   - Update docs (`axe.md`, `remote_dispatch.md` supervision sections, `ace.md`,
     `cli.md`, `plugins.md`).
   - Land the glossary strands (§6) and remove the beta flag.

**Live machine runbook (athena, apollo)**, run once phase 5 has landed and been
installed:

1. `sase service init --diff`. Confirm it plans `sase.service` and disabling
   `sase-gateway.service`.
2. Apply. `init` runs `systemctl --user disable --now sase-gateway.service`, writes and
   enables `sase.service`, then waits for the host heartbeat.
3. Enable the gateway in each machine's overlay (`service.procs.gateway.enabled: true`).
   Verify with `curl -s 127.0.0.1:7629/api/v1/health` and, from the controller,
   `sase machine status <target>`.
4. **athena, Telegram receiver.** Kill the legacy receiver row with
   `sase proc kill mnqrkm88fdgq`; it is still running the old `sase_chop_tg_inbound`
   name inside an old AXE scope. Then confirm `telegram_receiver` is running under the
   host. Its concurrency key is the same, so the two cannot overlap.
5. **athena, user config.** Remove the `tg_inbound` job from the `telegram` routine in
   the chezmoi `sase.yml`. `tg_outbound` stays a job.
6. **apollo, Telegram.** Its `telegram` routine runs but no receiver is active, so either
   set `telegram_receiver: {enabled: false}` in its overlay or rely on the `when:`
   condition.
7. Optionally remove apollo's stray `sase-gateway.service.bak-sase-xe.16.11.5`. Old
   `sase-axe-*.scope` units clear themselves once their agent processes exit.

---

## 11. Risks and open questions

- **Boot-time failure hurts silently.** If the host fails at boot, the scheduler never
  runs and hooks and waits stall.
  - Mitigations: `Restart=on-failure` / `KeepAlive`; a TUI banner when the host is down
    with a one-key start; a `sase doctor` check.
  - A host that crash-loops at the platform level should still leave a readable
    `host.json` error.
- **Supervision depth.** The chain is platform → host → scheduler → routines → jobs →
  agents. It is acceptable because each layer uses the same extracted library.
  Option D (§5) is the documented way to collapse a layer if it proves costly.
- **Secrets in the environment.** Unit files must not embed tokens. Service procs should
  read credentials the way they do today (sase-telegram's `credentials` module), and
  `env:` values in config should support `${VAR}` references rather than literals.
- **SASE_HOME multiplicity.** There is one host per SASE home. Test and dev homes must
  not install platform units; `init` refuses unless `SASE_HOME` is unset or `--force` is
  given.
- **Open: remote control.** Should the gateway expose service control (start/stop from
  mobile)? The status wire makes it cheap, but it is a security surface, so defer it.
- **Open: dependencies.** Is `after:` enough, or is a readiness probe needed? The known
  procs don't need one yet, so defer (corpus before mechanism).
- **Open: fallback without a unit.** Should the TUI keep starting the host on machines
  that declined `init`? Recommendation: yes, matching today's TUI-starts-AXE behaviour,
  unless `--no-service` is passed.

---

## 12. Recommended solution (summary)

1. **Pursue it, as an epic, with the adjustments in §3** (O1–O12). The most important
   are:
   - escape scopes, so restarts never kill agents (O3);
   - disabled nodes stay visible (O1);
   - a restart policy with a clean-exit rule plus `when:` conditions (O9);
   - a first-class `service` proc marker replacing origin-string hacks (O10);
   - a single control path for the scheduler (O11).
2. **Architecture: option B for daemons and option C for oneshots.**
   - One Python host (`sase service run`) runs daemon service procs as supervised
     children, using code extracted from the AXE orchestrator.
   - Oneshots, including `!!` background commands, go through the existing detached
     proc path.
   - Every run is mirrored into the proc store with a `service` block.
   - Config, state, status wire, and restart decisions live in sase-core.
3. **Platform: one unit only.** A systemd user unit (`sase.service`, `KillMode=mixed`,
   linger check) or a launchd LaunchAgent (`sh.sase.service`,
   `KeepAlive.SuccessfulExit=false`, `AbandonProcessGroup=true`). `sase service init` is a
   machine-scoped, plan/apply `sase init` step that migrates the legacy gateway and
   ensure units and is offered once per `--all` run.
4. **Configuration.**
   - A `service.procs` map, merged by name.
   - A simple proc is `command:`; core builtins use `builtin:`; plugins contribute
     entries through their existing `sase_config` layer.
   - Complex procs are arbitrary programs with a tiny env and `status.json` contract.
   - Disable per machine with `enabled: false` in a machine overlay, or with
     `sase service proc disable` / `!e`, a machine-local override that shows its
     provenance.
   - Defer a Python plugin API.
5. **Builtins and plugins:**
   - `scheduler`, enabled;
   - `gateway`, disabled by default and enabled on athena and apollo;
   - sase-telegram contributes `telegram_receiver` with
     `restart: on-failure` + `when: path_exists`.
6. **Services tab** (plural label recommended):
   - one node per service proc, disabled ones dimmed;
   - routine and job nodes nested under the scheduler node;
   - a distinct oneshot section with exit-code chips;
   - `x`/`r`/`!!`/`!e`/`!x` controls;
   - a service-health footer pill;
   - service procs excluded from the gear and hidden in the Procs pane by a
     configurable `-service` default backed by a real query field.
7. **Naming.**
   - **Prefer "Scheduler" over "Supervisor" for AXE** (§4.1).
   - Adopt the three-term vocabulary: platform unit / sase service / service proc.
   - Land five new glossary strands (Sase Service, Service Proc, Oneshot Service Proc,
     Scheduler/Supervisor, Service Node) and five strand edits (§6), written against
     shipped behaviour in the epic's last phase.
8. **If the full epic is too large right now,** ship option E first: install fixed units
   for AXE and the gateway, and filter the receiver out of the gear. Ship the §9.4
   escape-scope fix regardless, because it is independently valuable.
