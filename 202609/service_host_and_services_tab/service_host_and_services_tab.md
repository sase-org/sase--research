# Generalizing AXE into `sase service`: consolidated research

_Lead researcher · 2026-09-16 · consolidates
[report A](service_host_and_services_tab__a.md) and
[report B](service_host_and_services_tab__b.md) plus independent verification at sase
`491daa988` and live inspection of athena (re-verified today: four leaked
`sase-axe-*.scope` units, `sase-gateway.service` enabled+active, `Linger=yes`). Revised
the same day after cross-checking an independent third report (GPT Astra, not committed)
at sase `7636fe03b` and on athena and apollo; §12 lists what changed and why._

This report uses the request's names — **Supervisor** for today's AXE, **Service tab**
for today's AXE tab — except where §3 flags a naming recommendation.

## 1. Verdict

**Worth pursuing — but only as a replacement architecture, not an addition.** Both
researchers independently reached the same verdict for the same reasons. SASE today has
four bespoke supervision arrangements that a single service runtime would subsume:

- **AXE self-supervises badly.** A TUI start path wraps the orchestrator in
  `systemd-run --scope`; recovery is an optional 5-minute ensure timer (installed on
  neither machine); nothing starts it at boot. macOS has no story at all.
- **The gateway is a hand-written unit** copied onto athena and apollo outside SASE's
  control. B found two live defects: it omits the `--agent-bridge-command`/PATH setup
  that `docs/remote_dispatch.md` recommends, and its `network-online.target` dependency
  does not exist in the user manager (verified: "could not be found").
- **The Telegram receiver has no supervisor.** A 5-second job tick re-arms it, and core
  hardcodes the plugin's private `telegram-receiver` origin string
  (`src/sase/ace/tui/update_restart.py:10`) to keep it from blocking TUI restarts. This
  is exactly the "durable service" concept, implemented as a string hack.
- **Background commands are a parallel mechanism** with nine fixed slots, no recorded
  exit code (`bgcmd.py` writes only `finished_at`; verified), and a non-durable rerun.

Both reports also agree on the failure mode: **if the new runtime lands on top of the
old AXE desired-state/watchdog, the standalone gateway unit, and the Telegram rearm
loop, the result is two supervisors fighting over the same children — worse than
today's fragmentation.** Every migration phase must retire the old owner as the new one
becomes authoritative.

## 2. The one critical finding: cgroup capture (B §2.6, verified live)

This is the most important thing either researcher found, and it constrains the whole
design. On athena, **four** `sase-axe-*.scope` transient units are active though only
one orchestrator runs. The stale scopes stay alive because they still contain
processes: the Telegram receiver and — critically — `run_agent_runner.py` agent
processes launched by jobs. Everything a job launches inherits the launching scope's
cgroup, and systemd's default for services is `KillMode=control-group`: stopping the
unit kills everything in it.

**Consequence:** if `sase service run` becomes a systemd unit and agents, detached
procs, and oneshots keep spawning inside its cgroup, then every
`systemctl --user restart sase.service` — which `sase update`, flag changes, and config
saves will trigger — **kills all in-flight agents**. The design must therefore include
an escape helper: when running inside the service unit, every detach point (proc
supervisor spawn, agent runner launches, monitor/gate shells, gateway agent-bridge)
wraps itself in `systemd-run --user --scope --collect` (macOS:
`AbandonProcessGroup=true` + `setsid`). `systemd_scope.py` is the seed. The unit itself
uses `KillMode=mixed`.

This helper is independently valuable (it also fixes today's leaked scopes) and should
ship first regardless of the rest of the epic. Report A missed this entirely; its
"children of the host" design is only safe with this fix in place.

## 3. Naming (flagged: recommends against part of the request)

- **"Supervisor" for AXE collides badly.** The per-proc detached supervisor already
  owns the word: ~445 Python lines mention `supervisor` outside any AXE context
  (re-counted; B counted 218 with a narrower net), including the wire fields
  `supervisor_id`/`supervisor_claimed_at` and the *Sase Monitor* glossary strand
  ("under a detached supervisor"). In industry usage (supervisord, runit) the
  *supervisor* is the program that restarts services — which in this architecture is
  `sase service`, not AXE. The prior naming research
  (`research:202609/scheduler_loop_naming_reassessment.md`) independently recommended
  **`sase scheduler`** for this component. **Recommendation: name the builtin
  `scheduler`.** If "Supervisor" is kept anyway, rename the per-proc supervisor concept
  in prose and glossary so SASE has exactly one supervisor, and update *Sase Monitor*.
- **Tab label: "Services" (plural).** Verified: the sibling tabs render as "Artifacts"
  and "Agents". The tab lists many service procs; plural is the consistent label. The
  CLI noun stays singular (`sase service`), matching `sase proc`/`sase agent`.
- **Three-term vocabulary, enforced in docs and glossary:** *platform unit* (the
  systemd unit / launchd LaunchAgent) ≠ *sase service* (the host process the unit runs)
  ≠ *service proc* (what the host runs). Bare "service" is ambiguous; never use it for
  a service proc. Also rename the unrelated `src/sase/procs/service.py` (cheap,
  internal).

## 4. Requirement adjustments (all flagged; both researchers or lead concur)

1. **Show disabled and unavailable service procs, dimmed** (A+B). "Each active/enabled
   service proc has a node" makes enable-from-the-tab impossible — you cannot select a
   node that isn't rendered. Unavailable nodes (plugin missing, invalid definition)
   carry the reason inline.
2. **Define stop vs. disable persistence explicitly** (A+B). `stop` is a runtime
   override that survives host restarts and crashes and clears only on `start` or the
   next machine boot (keyed to the boot id, as B specified); `disable` is persistent
   machine policy. systemd users already expect stop ≠ disable; without this, "I
   stopped the gateway" is ambiguous after `sase update` restarts the host. (An
   earlier draft said "next host start/boot". That is wrong: host restarts are routine,
   so the stop would be undone by the very `sase update` this rule exists for.)
3. **Long-lived detached work must escape the unit cgroup** (B; §2). Non-negotiable.
4. **The host resolves config from machine-level layers only** — defaults, plugin
   layers, user config, machine overlay — **never project-local `sase.yml`** (A+B). A
   boot service's behavior must not depend on the cwd it was started from, and a
   checkout must not gain persistent execution authority by being the current
   directory.
5. **`ExecStart` must be the stable install**, never an ephemeral `sase_N` workspace
   (B); reuse `should_reexec_axe_start_from_canonical`. Detect executable-path drift in
   `init --check`/`status` (A).
6. **Retire the parallel watchdogs behind sunset flags** (A+B): the ensure timer, the
   TUI direct-start, the axe-start scope wrapper, and Telegram's rearm tick. Two
   restarters for one process race each other.
7. **`sase service init` is a plan/apply step with `--check`/`--diff`, plus
   `uninstall`** (A+B). It must detect legacy units (`sase-gateway.service`,
   `sase-axe-ensure.*`, `sh.sase.gateway` plist — the gateway unit holds port 7629),
   check lingering on Linux, and remember a decline so `--check` doesn't nag forever.
8. **Generalize the once-per-`--all` prompt** (A+B). `sase init` already special-cases
   `machine_offer_handled` (verified in `_init_onboarding_batch.py` /
   `_init_onboarding_apply.py`); replace it with an `InitCommandSpec.scope = "machine"`
   attribute so `machine` and `service` share one rule: machine-scoped steps run once
   per invocation, outside the project loop.
9. **Restart policy needs a clean-exit rule** (B). The Telegram receiver exits 0 by
   design when disabled; a naive always-restart flaps. `restart: on-failure` with
   `success_exit_codes` covers it.
10. **A first-class `service` marker on the proc wire, not free text** (B). Today a
    bare `-service` in the Procs query is a *free-text* exclusion (no `service` field
    exists; verified), and the gear indicator counts every `session_id is None` row —
    the live Telegram receiver shows as a gear chip in every session. Add an optional
    `service` block to the wire, a derived `service` boolean to the query dialect, make
    the gear use it, and delete the core origin-string check. Do **not** add a new proc
    `kind` — the glossary deliberately calls kinds compatibility labels (A+B agree).
11. **One control path for the Supervisor** (A+B). `sase supervisor
    start/stop/restart/status` delegates to `sase service proc <verb> supervisor`; the
    foreground entrypoint becomes `sase supervisor run`. The host is the only thing
    that starts it.
12. **The Procs-pane default query is a config value**, `tui.procs.default_query:
    "-service"` (B), not a hardcoded prefill — users and tests can change it, and
    removing the filter reveals full execution history (hiding is presentation, never
    deletion).
13. **Plugin service procs default to disabled** (A). Installing a plugin is not
    consent to a persistent background process. Same for the **gateway builtin**:
    disabled in core defaults, enabled in the athena/apollo machine overlays (A+B). A
    default-on loopback HTTP API on machines that never pair a phone is wrong.
14. **Limit *active* oneshots, not history** (A). Today a completed `!` command
    consumes its slot until dismissed; completed history must never block a new
    command.
15. **The host needs an explicit environment contract** (B's unit had a static `PATH`;
    lead, verified live). Today AXE inherits the launching TUI's interactive shell
    environment, and every agent a job launches inherits it in turn. A platform unit
    gets only the service manager's environment. On athena, the running orchestrator's
    environment includes `GEMINI_API_KEY`, `SASE_FEATURE_FLAGS`, and the nvm bin
    directory. `systemctl --user show-environment` has none of them, so `codex`,
    `gemini`, and `opencode` do not resolve there. On apollo the user manager's `PATH`
    lacks `~/.local/bin`, so even `sase` does not resolve. B's static
    `<install>/bin:%h/.local/bin:/usr/local/bin:/usr/bin:/bin` would still miss the nvm
    CLIs on athena, and launchd's default `PATH` omits Homebrew. So:
    `sase service init` captures the invoking shell's `PATH` into a 0600
    `~/.sase/service/env` file. The host loads that file itself, so Linux and macOS
    share one mechanism and no unit or plist carries secrets. Secrets that providers
    read from the environment (`GEMINI_API_KEY`, `mobile_gateway.fcm_credential_env`)
    are added to it explicitly; the file never holds a snapshot of the whole shell
    environment. `init --check`, `sase doctor`, and `status` resolve every configured
    agent-provider CLI and the gateway binary against the host's effective `PATH`, and
    they report flags that are set only in the interactive shell. Without this, the
    migration silently breaks agent launches for every provider that lives outside the
    service manager's `PATH`.
16. **Oneshots run only on request, never on replay** (Astra; lead-verified gap). The
    host auto-starts enabled *daemons* only. A oneshot runs because a request (`!`,
    `sase service proc run`) asked for it. It never runs because a config entry or an
    old row exists. After a crash, an unsettled oneshot is settled as unknown and never
    retried. B's glossary text said "configured oneshots run when the sase service
    starts", and its examples conflated host start with boot ("at host start, prune
    tmp" / "warm caches after boot"). Host starts happen on every update, flag flip,
    and config save, so that rule would re-run side effects routinely. v1 therefore
    accepts only `mode: daemon` in `service.procs`; `oneshot` is transient-only. This is
    the same corpus-before-mechanism call as `when:` in §5, since no configured oneshot
    has a consumer. If one is added later, it runs at most once per machine boot (keyed
    to the boot id) and never on a host restart or config reload.

## 5. Where the reports disagreed, and the resolutions

- **Control plane: Unix socket (A) vs. file-based desired state + SIGUSR1 nudge (B).**
  → **File-based** (B). It matches SASE's existing patterns (`desired_state.json`,
  locked proc store), needs no server, and lets the Rust gateway and mobile clients
  read the same state. Keep A's requirements that survive the change: reads come from
  an **atomic, versioned status snapshot** with a change token, and mutations go
  through a locked store, never racing ad-hoc writes. Revisit a socket only if latency
  or auth demands it (corpus-before-mechanism).
- **Oneshot placement: transient service definition under the host (A) vs. detached
  proc path outside the host tree (B).** → **Detached** (B). Host restarts are
  frequent (updates, flag flips, config saves); a `!` command must survive them.
  Daemons are host children (stopping the unit *should* stop them); oneshots go
  through the existing `submit_proc_request` detached path with a `service` block, and
  gain durable rows, exit codes, kill, and streaming for free.
- **Enable/disable storage: write machine overlay config (A) vs. machine-local
  override file with config as default (B).** → **Both layers, B's semantics.**
  `enabled:` in config is the declarative default (plugins ship `false`); `sase
  service proc enable/disable` and the tab's toggle write a fast machine-local
  override (like `systemctl enable`, not chezmoi-synced); the existing scope-rail
  entry editor (`e`) remains the way to change the declarative value. `show` and the
  tab must display provenance ("disabled here" vs. "disabled by sase_apollo.yml") —
  A's provenance requirement stands, and packaged defaults are never written to.
- **Service IDs: namespaced `builtin@supervisor` (A) vs. flat names in a
  layer-merged map (B).** → **Flat names** (B). A `service.procs` map merged by name
  across config layers is how job maps already work and is what makes disabling a
  one-liner in an overlay. Reserve builtin names, validate collisions with provenance
  diagnostics, and record each entry's source layer. Namespacing can come later if
  plugin collisions materialize.
- **Detached-host fallback without a platform unit: forbid (A) vs. keep (B).** →
  **Keep** (B). Machines that decline `init` must not lose automation entirely —
  today's TUI-starts-AXE UX is the baseline. A single lifetime lock prevents A's
  "secret second host" concern, and `status` must plainly say "running detached (no
  platform unit installed)".
- **Tab ID migration: canonicalize to `service` now (A) vs. display-label-only first
  (B).** → **B's sequencing, A's end state.** Change `_TAB_DISPLAY_NAMES` and accept
  `--tab services` as an alias first (the label is presentation-only; verified);
  canonicalize the internal id in the sunset phase. The prior naming research counted
  ~667 visual snapshots that regenerate on label changes — don't pay that twice.
- **Health: declarative TCP/exec healthchecks (A) vs. `when:` start conditions +
  `status.json` self-reporting (B).** → **Defer both probes and `when:` (lead
  adjustment, flagged).** The only `when:` consumer B identified is
  `~/.sase/telegram_is_enabled`, and A's migration already replaces that file with
  config enablement — after which the known corpus (scheduler, gateway, receiver)
  needs neither declarative probes nor conditions. Keep the pieces with immediate
  consumers: process liveness as the default health signal, `success_exit_codes`, and
  B's tiny env contract (`SASE_SERVICE_PROC`, a state dir, an optional `status.json`
  `{summary, state, updated_at}` the tab surfaces). That contract is the whole
  "complex service" protocol for v1 — a complex service proc is just an arbitrary
  program — and the corpus-before-mechanism decision says to stop there.

## 6. Recommended architecture

**Two-level supervision, one platform integration point** (both reports' option B):

1. The OS per-user service manager owns exactly one foreground process:
   `sase service run`. One unit per service proc (the `brew services` model) is
   rejected: platform differences would leak into every feature, plugin install would
   mutate native config, and the tab would become a lossy wrapper over two APIs.
2. The host owns all service procs: builtins (`supervisor`/`scheduler`, `gateway`),
   plugin-contributed (`telegram_receiver`), user-defined daemons, and transient
   oneshots. It must not daemonize — systemd/launchd owns its lifetime.

**Host runtime** (`src/sase/service/`): lifetime flock + `host.json` heartbeat under
`~/.sase/service/`; a ~1 s reconcile loop (nudgeable via SIGUSR1) comparing desired
state (effective enabled, runtime overrides) to actual children; config reload via the
existing stat-token check (added procs start, removed stop, changed restart — the host
itself does not restart); stable bounded per-proc logs at
`~/.sase/service/procs/<name>/output.log`. **Extract the orchestrator's proven
child-supervision code** (capped exponential backoff, crash-loop detection → `failed` +
one notification, TERM→KILL, bounded log pump) into a shared module used by both the
host and the Supervisor's routine supervision — this replaces duplication rather than
adding a fourth copy. `sase update` restarts the host (fixing today's manual
"restart the gateway after upgrading" step); `sase proc kill` on a daemon row routes to
the host as desired-state `stopped` rather than signaling a child the host would
immediately resurrect.

**Every run is a durable Proc.** The stable service-proc node is what users control;
each launch/restart is a distinct proc-store row carrying the additive `service` block
(`{name, mode, source}`) — restart history without mutating one record into several
lifetimes. Exempt *named* service-proc rows from the generic 100-row retention and keep
per-service last-N instead, so restarts don't churn unrelated history. Transient
oneshots have no stable name (B's block is `{mode: oneshot, source: transient}`), so
they stay under the generic retention. Otherwise every `!` command would become its own
bucket that is never pruned.

**Config** (composed and validated in sase-core; Python fails closed, like
`axe_config_compose`):

```yaml
service:
  procs:
    <name>:
      description: "…"
      enabled: true               # default true; plugins ship false
      mode: daemon                # only daemon in v1; oneshot is transient-only (§4.16)
      command: "autossh -N box"   # string → sh -c; list → argv; XOR with builtin:
      builtin: gateway            # core launcher reading existing config sections
      cwd: "~"                    # env:, restart:, success_exit_codes:,
      restart: on-failure         # stop_signal/-timeout, after: (ordering only),
      log_max_bytes: 2097152      # log_max_bytes
```

The simplest user service is one line
(`tunnel: {command: "autossh -M 0 -N buildbox"}`). Builtin launchers compute argv from
existing config (`mobile_gateway.*`, `axe.*`) so nothing is duplicated, and their
interface is the future plugin API — **defer a Python entry-point API** until a plugin
needs dynamic expansion; the known case (Telegram) is covered by the plugin shipping a
`sase_config` layer, a mechanism that already exists. Disabling on one machine is a
one-line overlay entry. Complex services live behind an executable boundary — testable,
portable, and isolating plugin failures from the host (A's argument, adopted).

**Compose list-valued fields atomically.** The generic layer merge concatenates lists in
the default, plugin, overlay, and local layers. Only the base user layer replaces them
(`merge_config_sources` in `src/sase/config/loading.py`; verified). As a result, a
machine overlay that overrides a plugin's `command: [argv…]` would *append* to the
plugin's argv, and `success_exit_codes` and `after` would accumulate the same way. The
sase-core `service.procs` composer must merge each entry field by field and replace
list values whole in every layer. It must also treat an explicit `enabled: false` as a
value, never as a missing key.

**Rust core boundary** (per rust-core-required): config compose/validation, the wire
`service` block + query field + retention exemption, the locked
`~/.sase/service/state.json` store (overrides, boot-scoped stops, heartbeat), a
schema-versioned status wire consumed by CLI `--json`, TUI, and the gateway's mobile
API, and a pure restart-decision function so every client explains "retrying in 12s"
identically. Process spawning, platform-unit writers, and Textual stay in Python.

**Platform units.** Linux: `~/.config/systemd/user/sase.service` — `Type=exec`, stable
`ExecStart`, `Restart=on-failure`, `RestartSec=5`, **`KillMode=mixed`**,
`WantedBy=default.target`, no `network-online.target` (it doesn't exist in the user
manager), no features beyond systemd 255 (apollo). The environment comes from the
host-loaded env file (§4.15), not from `Environment=` lines. `init` checks linger and
offers the exact `loginctl enable-linger` remediation without silently elevating. macOS:
`~/Library/LaunchAgents/sh.sase.service.plist` — `RunAtLoad`,
`KeepAlive={SuccessfulExit: false}`, `AbandonProcessGroup=true`, explicit log paths,
`ThrottleInterval=10`; `launchctl bootstrap gui/$UID`. macOS 13+ lists LaunchAgents
under Login Items, and the user can switch them off there. `init --check` and `status`
must report a user-disabled background item as such and must not re-bootstrap it in a
loop. **Startup means per-user
service-manager startup**: boot on Linux only with linger (both machines already have
it), login on macOS; a pre-login root LaunchDaemon is an explicit later mode, not the
default. The `mac` host is often offline, so launchd paths need unit tests against a
fake `launchctl` plus a manual smoke checklist.

**CLI** (per the CLI-rules memory: alphabetical, short aliases, bare groups → `list`):

```text
sase service init|uninstall [--check/--diff/--yes]   # platform unit lifecycle
sase service start|stop|restart|status|logs|run      # host lifecycle (run = unit ExecStart)
sase service proc list|show|start|stop|restart|enable|disable|logs NAME
sase service proc run [--cwd/--label/--project/--workspace] -- CMD...   # transient oneshot
```

Root start/stop drive the platform unit when installed, else the lock-guarded detached
fallback. `sase service` has no `list` child, so the central bare-group → `list` rule
does not cover it. Bare `sase service` must print help or act as `status`. It must never
act as `run`, because someone exploring the CLI must not start a foreground host.
`sase service proc run` vs. `sase service run` needs contrasting help text; rename the
host entrypoint to `sase service host` if it confuses. TUI flags:
`--no-axe`/`--restart-axe` → `--no-service`/`--restart-service` with sunset aliases.

## 7. Services tab

```text
 Services · host ● running 4d · sase.service
 ● Supervisor          running · 11 routines
 │  ▌ hooks …            (routine and job nodes, unchanged folding/actions)
 ● gateway             running · 127.0.0.1:7629
 ● telegram_receiver   running · sase-telegram
 ◌ tunnel              disabled here
 ✕ beta_thing          unavailable: plugin missing
── oneshots ──
 ▷ #1 pytest -k foo    running · 1m
 ✓ #2 make lint        exit 0 · 4m ago
```

- One node per configured service proc, disabled dimmed, unavailable with reason. The
  Supervisor node is special only in presentation: existing routine/job nodes nest
  under it with today's folding, actions, output, and scope-rail editing retained. The
  host status line is chrome (and shows what to press when the host is down).
- Oneshots sit below a divider with distinct glyphs (`▷`/`✓`/`✗`), muted color, and an
  exit-code chip. `!` flow (project → workspace → command history), `#1–#9` display
  indices, output view, kill/rerun/dismiss all survive — but storage moves to the proc
  store (slot → `bgcmd-slot:<n>` concurrency key, which already exists), **exit codes
  are recorded, and rerun becomes durable**.
- Keys: `x` start/stop proc (kill oneshot), `r` restart daemon / rerun oneshot / run
  job, `!!` new oneshot, `!e` enable/disable toggle (says it edits machine policy),
  `!x` host start/stop. New bindings go into `default_config.yml` keymaps (gotchas
  memory). The `Q` quit modal offers "stop Supervisor", not "stop host" — stopping the
  host would take the gateway and receiver down too.
- The ` AXE ` footer pill becomes a service-health pill (` SVC 3/3 ` / ` SVC ! `). A
  failed service proc must stay loud here and in notifications — hidden from the gear
  cannot mean invisible failure.
- Procs pane: add the `service` boolean (+ `svc:<name>`), seed the query from
  `tui.procs.default_query` (default `-service`), include service metadata in the
  filter cache key; gear excludes `service` rows and monitor rows. The pane already
  restores its committed query from session state, so the seed applies only when no
  query has been persisted. A query the user cleared persists as empty and is never
  re-seeded.
- Preserve the TUI perf constraints: no I/O on the event loop, consume the atomic
  snapshot off-thread, generation-aware refresh, navigation p95 < 16 ms — measure under
  restart storms before rollout.

## 8. Glossary additions (land in the epic's final phase, against shipped behavior, via `/sase_memory_write`)

Five new strands, merged from both proposals (substitute "Scheduler" per §3 if
adopted):

- **Sase Service** (aliases: service host) — The sase service is the per-machine host
  process (`sase service run`) that starts, restarts, and stops that machine's service
  procs, with at most one per SASE home. `sase service init` registers it as a platform
  unit — a systemd user unit on Linux, a launchd LaunchAgent on macOS — so it starts at
  boot or login; without one, `sase service start` runs it detached. systemd/launchd
  supervises the sase service itself, never each service proc. Say "service proc" for
  what it runs and "platform unit" for its registration; bare "service" is ambiguous.
- **Service Proc** — A service proc is a named proc the sase service owns, declared
  under `service.procs` by core (builtin), a plugin's config layer, or the user, or
  created at runtime as a transient oneshot. Its mode is `daemon` — kept running under
  its restart policy — or `oneshot` — run once to completion. Control one with
  `sase service proc` or its Services-tab node; `enabled: false` in a machine overlay
  keeps it off that machine. Every launch is a distinct durable Proc carrying a
  `service` marker, hidden from the Procs tab and proc gear by default.
- **Oneshot Service Proc** (aliases: oneshot, background command) — A oneshot service
  proc runs once to completion and is never restarted. Transient oneshots are created
  at runtime by the TUI's `!` background commands or `sase service proc run`; they run
  outside the sase service's process tree, so restarting the sase service does not kill
  them. Distinct from a job, which a routine runs on a schedule.
- **Service Node** — A service node is one selectable row of the Services tab: a
  service-proc node, a oneshot node, or — nested only under the Supervisor's node — a
  routine node and its job nodes. A service-proc node is stable across process
  restarts; section dividers and the host status line are chrome, not nodes.
- **Sase Supervisor** *(or Scheduler)* — The builtin service proc behind
  `sase supervisor` that runs SASE's background automation: it starts one process per
  routine and restarts crashed routines, and routines run jobs. The sase service owns
  the Supervisor's process lifetime; the Supervisor owns only its routine/job tree. AXE
  is its former name and remains an accepted alias.

Strand edits: **Sase Node** generalizes from "one row of the Agents tab's agent tree"
to one selectable row of a hierarchical TUI view, keeping the Agents taxonomy and
adding "on the Services tab, a service node"; **Routine**/**Job** replace AXE with the
new owner's name, keeping Lumberjack/Chop aliases; **Proc** gains one sentence ("Runs
of service procs carry a `service` marker; the Procs tab hides them by default") and
should drop the `background task(s)` aliases, which now read as oneshot synonyms;
**Sase Monitor** drops or renames "detached supervisor" if the Supervisor name is kept.
Only term names hit the always-loaded roster, so per-turn cost is small. Don't add
"platform unit" or "service proc definition" as strands — implementation vocabulary,
not terms agents must distinguish (A's judgment, adopted).

## 9. Migration (each phase retires the owner it replaces)

1. **Escape scopes + names.** Ship `detach_scope` and cgroup tests first — it fixes the
   leaked-scope bug today and unblocks everything else. Decide
   Supervisor-vs-Scheduler and Services; rename `procs/service.py`.
2. **sase-core:** config schema, wire `service` block + query field, state store,
   status wire, restart-decision function.
3. **Host:** `sase service` + `service proc` commands, extracted supervision library,
   `supervisor` builtin (argv `sase axe start` initially), handover that stops a
   running orchestrator lock-holder and restarts it under the host. Behind a
   `service_host` beta flag; exercise concurrent-start, stale-lock, crash-loop,
   signal, reload, stop-vs-restart race, and no-oneshot-replay cases before it owns
   production children. **Release gate:** under a real unit, restart the host while
   three things are live: a job-launched agent, a running `!` oneshot, and a
   gateway-launched agent. All three must survive. An agent launched for each
   configured provider must also resolve its CLI and credentials (§4.15). Mock-only
   tests cannot establish either property.
4. **Platform units:** init/uninstall with `--check`/`--diff`, systemd + launchd
   writers, the env-file capture and provider-CLI resolution check (§4.15), linger
   check, legacy-unit detection, decline marker, the machine-scoped
   `sase init` step (once per `--all`), `sase doctor` checks.
5. **Gateway + Telegram:** `gateway` builtin (reads `mobile_gateway.*`, adds the
   agent-/helper-bridge args the hand unit is missing). Its launcher must reuse
   `_prepare_mobile_gateway_launch`'s argv and exec the gateway binary directly —
   **not** `sase mobile gateway start`, which POSTs `/api/v1/session/pair/start` after every
   successful health check. Under restart policy, that would create a fresh pairing
   challenge on every restart and write the code into the persistent service log.
   Today `start` is the only `sase mobile gateway` subcommand and the only CLI path
   that mints a pairing code, so add a `pair` subcommand that asks the running gateway
   for a challenge. When a host-owned gateway is enabled, `start` should point there
   rather than fight the host for port 7629. sase-telegram ships its `sase_config`
   layer, `ensure_receiver_running` no-ops when configured (sunset flag for old sase),
   delete core's origin check, migrate `telegram_is_enabled` to config enablement. The
   marker is machine-local and exists only on athena (verified; apollo has none).
   Telegram allows one `getUpdates` consumer per bot, and SASE has no cross-machine
   lock. The migrated `enabled: true` must therefore land in the athena machine
   overlay, never in the chezmoi-synced base config, which would start a second
   receiver on apollo. The offset file (`~/.sase/telegram/update_offset.txt`) is
   unchanged because the receiver code is unchanged.
6. **TUI:** Services tab nodes/keys/pill, gear exclusion, Procs query field +
   configurable default. Display-label rename only; tab-id canonicalization waits.
7. **Oneshots:** `!` onto the proc store; legacy slot dirs readable behind a sunset
   flag until they age out.
8. **Sunset + docs + glossary:** retire ensure/timer/TUI-direct-start/scope-wrapper,
   alias `sase axe`, canonicalize the tab id, update docs, land glossary strands,
   remove the beta flag.

**Live runbook (athena, apollo), after phase 5:** `sase service init --diff` (plans the
unit + disabling `sase-gateway.service`) → apply → enable gateway in each machine
overlay → verify `curl 127.0.0.1:7629/api/v1/health` and controller
`sase machine status`, with rollback restoring the legacy unit on failure → on athena
kill the legacy receiver row (`sase proc kill mnqrkm88fdgq`; same concurrency key, so
old and new cannot overlap) and drop the `tg_inbound` job from the `telegram` routine
in chezmoi config (`tg_outbound` stays) → remove the chezmoi gateway unit only after
both machines pass → verify exactly one Telegram `getUpdates` consumer before and
after. Old `sase-axe-*.scope` units clear as their agents exit.

## 10. Risks and open questions

- **Silent boot failure:** a host that fails at boot stalls hooks/waits invisibly.
  Mitigations: outer `Restart=on-failure`/`KeepAlive`, a TUI banner with a one-key
  start when the host is down, `sase doctor`, and a readable `host.json` error even
  when crash-looping.
- **Supervision depth** (platform → host → Supervisor → routines → jobs → agents) is
  acceptable because every layer shares the extracted library. Flattening routines
  into host children (B's option D) is deliberately deferred: Supervisor restarts are
  frequent, and per-routine churn plus rebuilt heartbeat semantics is a larger blast
  radius for no current pain.
- **Secrets:** unit files must not embed tokens; `env:` should support `${VAR}`
  references; procs keep reading credentials as they do today.
- **Test/dev homes:** one host per SASE home; `init` refuses under a nonstandard
  `SASE_HOME` without `--force`, and under `--force` the unit and plist names carry a
  home-derived suffix so they cannot overwrite the default home's `sase.service`; keep
  the pytest process guard so tests never touch real units.
- **Open:** expose service control through the gateway's mobile API (cheap via the
  status wire, but a security surface — defer); `after:` ordering vs. readiness
  probes (defer; no current consumer).
- **Fallback scope (E):** if the epic is too large now, the 20% version is fixed units
  for AXE + gateway plus the gear fix — but ship the escape-scope helper regardless.

## 11. Recommended solution

Pursue it as an epic. One platform unit per machine runs `sase service run`; the host
supervises daemon service procs as children (code extracted from the AXE orchestrator)
and launches oneshots — including migrated `!` commands — through the detached proc
path so they survive host restarts, and they run only on request, never on replay.
Detached work escapes the unit cgroup via a scope helper, shipped first. The host loads
an explicit, init-captured environment, so agents it launches keep resolving their CLIs
and credentials once they no longer inherit a TUI shell. Service procs are declared in a
flat, layer-merged
`service.procs` map (one line for simple cases; `builtin:` launchers for core;
plugin `sase_config` layers for Telegram; arbitrary executables plus a tiny
env/`status.json` contract for complex cases; no Python plugin API yet). Enablement is
declarative config plus a provenance-visible machine-local override; stop is runtime,
disable is policy; the gateway and all plugin procs default off. Config, wire `service`
block, state store, status wire, and restart decisions live in sase-core. `sase
service init` is an idempotent plan/apply machine-scoped `sase init` step (offered once
under `--all`, decline remembered) with `uninstall` and legacy-unit migration for the
hand-written gateway units on athena and apollo. The tab becomes **Services**
(display-label first), with all configured procs as nodes (disabled dimmed), routines
and jobs nested under the Supervisor node, a visually distinct oneshot section with
recorded exit codes, start/stop/enable/disable actions, a config-backed `-service`
Procs default, and gear exclusion via a first-class wire marker. Prefer **Scheduler**
over **Supervisor** for the builtin's name (flagged; the collision evidence is strong
and the prior naming research agrees), and land the five new glossary strands and five
edits in the final phase against shipped behavior. Every migration phase deletes the
supervision path it replaces — the project's one disqualifying outcome is two
supervisors owning the same child.

## 12. Cross-check against a third report (GPT Astra)

A third, independently generated report reached the same verdict and the same
architecture: one foreground runtime under the OS service manager, the Proc store for
executions, the Supervisor kept for routines, and a cgroup escape for agents as the
release gate. Its value was in pointing at places where this consolidation was wrong or
silent. Each point below was checked against the code or the live machines before it
was adopted.

**Adopted:**

- The stop override is boot-scoped, not host-start-scoped (§4.2). This fixes an
  internal contradiction with the "boot-scoped stops" store in §6.
- The host needs an explicit environment contract (§4.15). Verified on both machines,
  this is the largest finding the cross-check produced.
- Oneshots run only on request, and configured oneshots are out of v1 (§4.16).
- Transient oneshots stay under the generic retention (§6).
- List-valued `service.procs` fields replace whole in every layer (§6).
- A user-disabled macOS background item is reported, not retried (§6).
- The behavior of bare `sase service` is defined (§6).
- The Procs default query is a seed only, not re-applied (§7).
- The gateway builtin never mints pairing codes, and a `pair` subcommand is added
  (§9.5).
- Telegram is enabled in exactly one machine overlay (§9.5).
- The restart-with-live-work release gate is explicit (§9.3).
- Suffixed unit names under `--force` (§10).
- The verdict now counts four bespoke arrangements, matching its own list (§1).

**Not adopted.** On each of these, Astra took the side this report had already
rejected, and it added no new evidence:

- A Unix-socket control API (§5 keeps file-based state).
- Namespaced service IDs (§5 keeps flat names).
- Enablement written only into YAML, with no machine-local override (§5 keeps B's
  override with visible provenance).
- Argv-only `command:` (a string is still `sh -c`, which is fine for user-authored
  config).
- Requiring a service-specific opt-in beyond `sase init --yes`. That is a policy
  choice, and today every init step applies under `--yes`.
- Astra's glossary drafts, including a separate *Service Definition* strand. §8 already
  rejects implementation-vocabulary strands.
