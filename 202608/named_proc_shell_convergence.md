---
create_time: 2026-08-13
updated_time: 2026-08-13
status: research
---

# Named Procs and `sase shell`: Converging Monitors onto the Proc Substrate

**Research question:** how should SASE replace `sase monitor` with a new `sase shell`
surface whose executions are named, detached procs, while preserving the monitor
feature's agent-family handoff, workspace continuity, timeouts, output, and follow-up
behavior?

**Snapshot:** this report was researched on 2026-08-13 against `sase` commit
`d9c685e86`, `sase-core` commit `5b8ba44b5`, epic `sase-kp`, epic `sase-lh`, and the
plans behind both epics. At this snapshot all twelve `sase-kp` phases are closed but its
land bead is still in progress. `sase-lh` has landed and released the Rust rename
(`sase_core::procs`, wire schema 2), while its Python, CLI, TUI, copy, documentation, and
land phases are still in progress. The `sase` checkout therefore still spells current
Python identifiers as `sase.tasks`; this report uses their post-`sase-lh` names unless
quoting current code.

Related research:

- [`detached_proc_convergence`](detached_proc_convergence/detached_proc_convergence.md)
  establishes why all durable procs should eventually be supervisor-owned and identifies
  the monitor/proc duplication.
- [`monitor_command_substrate`](monitor_command_substrate/monitor_command_substrate.md)
  audits the original monitor supervisor. Most of its critical hardening recommendations
  have since landed, which materially changes which implementation should be preserved.

---

## Bottom line

The proposed convergence is the right direction, but **namedness should be an orthogonal
proc property, not a fourth `kind` value**, and **`sase shell` should call the proc service
API directly, not spawn and parse the `sase proc` CLI**.

The clean architecture has three layers:

1. **Proc engine — authoritative execution.** The proc store owns identity, immutable
   argv, name, process identity, pid/pgid, state, timeout policy, log, stop intent,
   reconciliation, and terminal outcome. There is one supervisor implementation.
2. **Shell policy — named-proc orchestration.** A trusted built-in `shell` lifecycle
   profile adds the required reason/budget, agent-lane association, workspace claim,
   optional follow-up action, and custom start/stop labels.
3. **Agent-family projection — lineage, not execution.** When a shell belongs to an agent
   lane, a thin family member points to the proc by `proc_id`. It preserves the excellent
   monitor family model without owning a second supervisor or runtime record.

This is not just a rename. Today's proc supervisor is simpler and weaker than the
hardened monitor supervisor. Convergence must move the monitor guarantees into
`sase.procs` first, then delete the monitor copy. Repointing `sase monitor` at today's
proc runner would regress startup safety, handoff survival, timeouts, process identity,
workspace ownership, reconciliation, and follow-up settlement.

---

## 1. Current architecture

### 1.1 Procs are the right execution authority, but not yet the stronger engine

The Rust schema-2 `ProcWire` currently records:

```text
proc_id, label, kind, status, command, cwd,
project, workspace_num, session_id/session_label,
origin, cl_name, tags,
pid, pgid, exit_code, phase, message,
created_at, started_at, finished_at, log_path
```

The store is a single locked JSONL database. `append_proc()` validates, appends, and
applies retention atomically, but it does not perform atomic name reservation,
idempotency, deduplication, or exclusive-scope checks
(`sase-core/crates/sase_core/src/procs/store.rs:85-114`).

The current Python proc runner (`src/sase/tasks/runner.py`, soon `sase.procs`) does the
following:

- appends a pending row;
- directly starts `python -m sase.tasks.supervisor` with `start_new_session=True`;
- records only the numeric supervisor pid after `Popen` returns;
- starts the requested argv under a second process group;
- writes combined output through the shared `BoundedLogPipe`;
- maps exit to `success`, `error`, or `killed`;
- reconciles a dead supervisor by checking pid/cmdline and marking the row `error`.

This is a good small durable-command engine. It is not yet sufficient for an agent that
starts a command and immediately kills its own runner.

### 1.2 Monitors now contain the stronger execution engine

The `sase-kp` implementation is much larger: the monitor package is 3,747 lines versus
1,390 lines in the current task/proc package, before their respective CLI parsers,
handlers, and renderers. Some of that is legitimate family/follow-up policy, but much is
now generic detached-process machinery:

| Capability | Current proc | Current monitor |
| --- | --- | --- |
| Detached supervisor | direct `Popen` child | double-forked, reparented supervisor |
| Startup proof | none | supervisor acknowledgement with liveness polling |
| Pre-exec barrier | none | command waits until the workspace claim is secured |
| Process identity | pid + Linux cmdline match | boot id + `/proc` start ticks |
| Child pgid | persisted | persisted |
| Combined bounded byte log | yes | yes, through the same `BoundedLogPipe` |
| Total timeout | none | authoritative, checked every 50 ms |
| Idle timeout | none | authoritative, byte-activity based |
| TERM-to-KILL escalation | yes | yes |
| Agent env scrubbing | no general guarantee | yes |
| Request idempotency | none | full-request fingerprint under a lane lock |
| Crash reconciliation | terminalizes row | kills group, settles claim/follow-up, marks lost across reboot |
| Settlement barrier | terminal status is immediate | terminal only after claim/follow-up disposition |

The important conclusion is not that monitor should remain independent. It is that its
generic guarantees should become proc guarantees.

### 1.3 The monitor family model remains worth preserving

The monitor's execution record currently lives in `agent_meta.json` and `done.json`, so
the same entity simultaneously acts as:

- a command execution;
- a sequential agent-family member;
- a workspace-claim owner;
- a saved chat-history entry;
- a `%wait` / `#fork` handoff point;
- an Agents-tab row and family-runtime interval.

That produced an excellent user model, but it also forced command state into 20-plus
`monitor_*` fields in the agent scan wire. There are now 138 source, test, and docs files
matching monitor-specific identifiers or imports, including Rust agent scanning, wait
resolution, mobile summaries, plan approval, runner finalization, the TUI, and the CLI.

The convergence should preserve the family projection but stop making it the process
authority.

---

## 2. The key modeling decision: a name is not a kind

Current proc `kind` values (`command`, `tui`, `detached`) already conflate two unrelated
axes:

- who owns execution (ACE worker versus detached supervisor); and
- how the row is attributed (session versus global).

Adding `kind="named"` would introduce a third axis—addressability—into the same field. A
named proc is still detached, may or may not belong to a session, and may use either a
direct argv or a shell command. Namedness is simply an optional, immutable identity.

Recommended model:

```text
Proc
├── proc_id              immutable generated identity
├── name?                immutable human identity
├── profile?             trusted lifecycle profile; "shell" for this feature
├── command              immutable exact argv
├── execution fields     pid/pgid/identity/status/phase/timestamps/log
├── policy fields        timeout, idle timeout, fingerprint, exclusion scopes
└── attribution fields   project/workspace/session/Patch as today
```

`kind` should be retained only for schema-2 compatibility while the attached-TUI-proc
migration is unfinished. New named shells should be supervisor-owned and unattributed
(`session_id=None`). A later convergence can retire the legacy kind distinctions once
all procs are detached, as recommended by `detached_proc_convergence`.

### Name semantics

The least surprising contract is:

- `name` uses a short validated identifier grammar (no path separators, control
  characters, or whitespace; bounded length);
- active-name uniqueness is scoped by project, with a separate global scope for
  project-less procs;
- only one active proc may hold `(project, name)`;
- a terminal name may be reused;
- exact active name wins during resolution; otherwise a name resolves to its newest
  retained generation;
- `proc_id` remains the permanent, unambiguous reference for history.

For an in-agent shell, default the proc name to the agent lane. This naturally retains
the monitor invariant of one active shell per lane. A host-started shell without a lane
must supply a name. If future functionality permits several named procs in one lane,
that should be an explicit parallel-group design rather than an accidental consequence
of choosing two names.

Name reservation must occur under the Rust proc-store lock. A Python
read-then-append—like the original monitor start check—is inherently racy across two ACE
instances or agents.

---

## 3. Recommended source-of-truth split

There should be one authoritative owner per field category.

| Data | Authority | Why |
| --- | --- | --- |
| proc id/name, argv, cwd | Proc record | every surface must execute and display the same launch |
| supervisor pid/identity, child pgid | Proc record | stop and reconciliation must use one control plane |
| status, phase, exit, timeout/stop reason | Proc record | no dual terminal-state machine |
| active/rotated output | Proc log | `sase proc` and `sase shell` must show the same bytes |
| lane, parent timestamp, model/provider, bead lineage | Agent member | these are agent-family concepts |
| reason, next action/output policy, custom labels | Shell request/member | shell policy, not generic process execution |
| workspace claim provenance | Shell request plus running-field store | needed to reverse or settle transfers safely |
| follow-up disposition | Agent member terminal snapshot | `%wait`, Agents tab, and history need it after proc retention |

The family member should contain a small pointer such as `proc_id`, `proc_name`, and
`agent_family_role="shell"`. While active, the Agents tab joins that pointer to the proc
store for live state and log output. At settlement it writes a bounded terminal snapshot
to `done.json` and the member artifacts, so agent history remains readable after proc
history retention prunes the underlying row.

### Retention is a load-bearing detail

Proc retention currently removes old terminal rows and their logs; agent artifacts have
a different and generally longer lifecycle. If shell rows merely point at
`~/.sase/procs/logs/<id>.log`, an ordinary `procs.history_limit` prune can silently erase
the output behind a still-visible family member.

Before launching the follow-up, shell settlement should therefore materialize:

- a bounded retained log or head-plus-tail summary in the member artifacts;
- the exact terminal status, exit code, elapsed time, and termination reason;
- the proc id and name;
- the follow-up outcome and any degraded/error detail.

The live proc remains canonical while running; the terminal member snapshot becomes the
durable family-history representation after the proc is pruned. Pinning every named proc
forever would defeat proc retention and is not recommended.

---

## 4. One supervisor, with a trusted lifecycle profile

The generic proc supervisor should adopt the hardened monitor lifecycle. Shell-specific
code should not supervise another child inside a proc child: that creates two process
groups and makes stop/crash settlement unreliable.

A tempting but incorrect implementation is:

```text
proc supervisor -> sase shell _run -> user command
```

If `sase proc kill` signals the child group, it kills both `_run` and the user command,
so the process responsible for releasing the claim and launching/suppressing the
follow-up dies before it can settle. Putting a second watcher beside it recreates the
monitor supervisor under another name.

Instead, the proc supervisor should own the user command directly and support a closed,
trusted lifecycle profile:

```text
profile = null       ordinary proc; settlement is a no-op
profile = "shell"    invoke SASE's built-in shell settlement handler
```

Do not persist arbitrary Python import paths or arbitrary completion commands. They
create a durable code-execution contract, make mixed-version upgrades unsafe, and expose
another injection surface. Store a versioned, mode-0600 shell request sidecar and let a
small built-in dispatcher understand only supported profile/schema pairs.

### Generic fields needed by schema 3

The exact wire names can be chosen during planning, but the behavior needs explicit
durable representation:

- optional immutable `name`;
- optional `profile` and versioned profile request path;
- stronger `supervisor_identity`;
- request fingerprint/idempotency key;
- atomic dedup/exclusive scopes;
- total and idle timeout budgets (prefer integer milliseconds on the wire);
- stop-requested state that the supervisor, not the caller, terminalizes;
- termination reason (`exit`, `stop`, `timeout`, `idle_timeout`, `supervisor_lost`);
- a `starting` / `running` / `settling` phase;
- settlement completion/failure detail.

The `sase-lh` core phase already released schema 2, so this is necessarily a separate,
deliberate schema-3 change. Reopening the terminology-only rename to squeeze in new
semantics would make that epic harder to land and test.

### Kill semantics need one owner

Today's `kill_task()` sends SIGTERM and immediately writes `status="killed"`, while the
supervisor also writes the eventual terminal result. A shell makes that race visible
because `killed` must suppress `--next` and dispose of a workspace claim exactly once.

Recommended behavior:

1. control APIs atomically record stop intent;
2. they signal the verified supervisor identity;
3. the supervisor kills the process group, runs settlement with `stop` as the reason,
   and writes the terminal state;
4. if the supervisor is dead, reconciliation performs those same steps under the proc
   lock;
5. `sase proc kill` and `sase shell stop` use the same operation and therefore cannot
   disagree.

---

## 5. Transaction and state machine

The shell start path crosses the proc store, agent artifacts, a supervisor process, and
the workspace-claim store. It cannot be one filesystem transaction, but it can have a
single recoverable order.

```text
reserve named proc (pending, command blocked)
          │
          ├─ create optional shell family member pointing to proc_id
          │
          ├─ spawn/reparent proc supervisor and wait for startup ack
          │
          ├─ record verified supervisor identity
          │
          ├─ transfer/acquire workspace claim to that supervisor
          │
          └─ release launch barrier
                    │
                  running
                    │ child exits / stop / timeout / reconciliation
                    ▼
                 settling
          ├─ finalize bounded member log snapshot
          ├─ launch, degrade, or suppress follow-up
          ├─ transfer or release workspace claim
          ├─ write member done marker
          └─ write proc terminal state
```

Important invariants:

- no user command can execute before its claim is held;
- `start` cannot return a live proc until the reparented supervisor has acknowledged;
- failure before the barrier reverses the original claim to the still-live starter;
- terminal proc status means process, log, claim, member, and continuation are settled;
- a crash during `settling` is resumable and idempotent;
- a pre-reboot active proc becomes `supervisor_lost` and is never automatically replayed;
- repeated identical starts return the active proc; a changed request with the same
  active name conflicts visibly.

The existing monitor bootstrap, process identity, launch barrier, request fingerprint,
bounded byte pipe, timeout loop, and reconciliation code are the reference
implementation. Move and generalize them; do not rewrite them from scratch.

---

## 6. `sase shell` CLI contract

`sase shell` should be a curated facade over named procs, following the repository's
default-list convention:

```text
sase shell                         -> sase shell list
sase shell list
sase shell show <name-or-id>
sase shell start [NAME] -c CMD -r REASON -t DURATION [options]
sase shell stop [name-or-id]
```

Preserve the valuable monitor flags:

- required `-c/--command`, `-r/--reason`, and `-t/--timeout`;
- optional `-C/--cwd`, `-i/--idle-timeout`, `-l/--lane`, `-L/--label`;
- optional `-n/--next`, `--next-output`, `-s/--start-status`,
  `-S/--stop-status`, and `-T/--tail-lines`;
- JSON and follow/output flags on list/show/stop.

Inside an agent, `NAME` and `--lane` default to the calling lane. Outside an agent, an
explicit name is required; `--lane` is optional, so the new feature also fixes the
current inability to start a monitor without existing agent artifacts.

The word “shell” can imply an interactive PTY. This feature is not one: stdin is null,
there is no attach protocol, and `show --follow` streams a log. Documentation and help
should define a **SASE Shell** as a named, noninteractive, run-to-completion proc.

### Command representation

`sase proc run -- COMMAND ...` should remain the argv-native generic surface.
`sase shell start -c '...'` is explicitly the shell-string surface. Compile it to an
explicit argv such as `[/bin/sh, -c, CMD]` and persist that argv; do not use
`shell=True` inside the supervisor. This gives the proc record an honest, replayable
launch identity and keeps shell interpretation at the facade boundary.

### Relationship to `sase proc`

Every shell must be visible and controllable through both surfaces:

- `sase proc list` shows a NAME/PROFILE indicator for named rows;
- `sase proc show <proc-id-or-name>` shows the same status and log;
- `sase proc kill <proc-id-or-name>` is exactly the operation behind
  `sase shell stop`;
- `sase shell list/show` add lane, custom status, and follow-up presentation from the
  family projection.

“Powered by `sase proc`” should mean shared models, store, supervisor, and service
functions. Spawning `sase proc run --json` and parsing its response would add startup
latency, error translation, output ownership problems, and a fragile CLI-to-CLI
protocol.

---

## 7. Agent-family bridge

For an agent-owned shell, keep the visible lane sequence:

```text
acme            family container
├─ acme--0      DONE       starter
├─ acme--shell  CHECKING   shell member -> proc 4k7m2...
└─ acme--1      RUNNING    follow-up
```

The family member should not duplicate the proc state machine. A minimal new artifact
shape is enough:

```text
agent_meta.json
  name, agent_family, role_suffix, parent_timestamp, inherited model/workspace lineage
  agent_family_role: "shell"
  proc_id, proc_name
  shell_reason, shell_next_action/output, custom labels

done.json
  outcome: a new neutral proc/shell-member outcome
  proc_id, proc_name
  terminal status/exit/termination/elapsed snapshot
  follow-up disposition
  response/log artifact paths
```

The precise outcome spelling should be chosen once and applied everywhere. Reusing
`"monitored"` would preserve less code but leave the removed concept embedded in new
records. Prefer a neutral internal outcome such as `"proc"` for the member and
`"proc_handoff"` for the starter runner, with `agent_family_role="shell"` controlling
presentation.

The starter handoff marker becomes a proc/shell marker and carries `proc_id`, name, and
member artifacts path. The runner continues to skip workspace release because the claim
already belongs to the proc supervisor. `%wait` should resolve a shell generation only
after the follow-up is launched or durably dispositioned, preserving the monitor
semantics that fixed premature family advancement.

This projection is intentionally thin, but it is not optional for agent-started shells.
Eliminating it would require teaching every agent-artifact query, family roster, wait
resolver, chat lookup, mobile summary, and runtime aggregator to join the global proc
store. That is a much larger migration with no user benefit.

---

## 8. Alternatives considered

| Option | One supervisor | Preserves family model | Future detached-proc migration | Cost/risk | Verdict |
| --- | ---: | ---: | ---: | --- | --- |
| Rename monitor to shell, keep its supervisor/store projection | no | yes | poor | low now, permanent duplication | reject |
| Run `sase shell _run` as an ordinary proc child | nominally | yes | poor | stop/crash kills the settler | reject |
| Proc authority plus thin shell family projection | yes | yes | excellent | medium, explicit cross-store transaction | **recommend** |
| Delete family artifacts and synthesize shell rows from procs | yes | requires broad rewrite | excellent | highest; breaks artifact-native consumers | reject for now |
| Make systemd/transient units the authority | one Linux backend | possible | mixed | not portable to macOS | optional future backend only |

The recommended option is the only one that removes supervision duplication without
throwing away the monitor feature's most successful product decision.

---

## 9. Sequencing

Do this as a new convergence epic after both `sase-kp` and `sase-lh` close. Do not fold
behavioral changes into the in-flight terminology epic.

### Phase 1 — proc schema and atomic reservation

- Add schema-3 named/profile/control fields in `sase-core` with schema-2 read
  compatibility.
- Add an atomic reserve/create operation that enforces active name, idempotency, dedup,
  and exclusive scopes under the Rust lock.
- Add name-aware ref resolution and filters.

### Phase 2 — converge the supervisor kernel

- Move the monitor double-fork bootstrap, process identity, startup ack, launch barrier,
  timeout/idle-timeout loop, env hygiene, and complete reconciliation into `sase.procs`.
- Keep `BoundedLogPipe` as the shared output transport.
- Make stop intent and final terminalization supervisor-owned.
- Add the trusted lifecycle-profile dispatcher and versioned request sidecar.

### Phase 3 — build `sase shell`

- Add the list/show/start/stop facade over proc service functions.
- Implement name defaults/scoping and explicit `/bin/sh -c` argv conversion.
- Add the shell request/result formats and terminal artifact snapshot.

### Phase 4 — bridge agent families

- Create the thin shell member projection and pending handoff adoption.
- Move monitor follow-up prompt/launch and claim settlement into a shell-policy package,
  generalized only where another proc profile truly needs it.
- Join live Agent rows to proc status/log by `proc_id`; keep terminal summaries in
  artifacts.

### Phase 5 — migrate integrations

- Change approved epic launch to start a shell/named proc and return its proc id/name.
- Update the Agents and Procs tabs, mobile summaries, wait resolution, notifications,
  docs, memory, and the agent skill (`/sase_monitor` -> `/sase_shell`).
- Ensure the Procs tab and Agents tab show one shared execution identity.

### Phase 6 — remove monitor creation and CLI

- Remove the public `sase monitor` parser, handler, renderer, supervisor, and docs.
- Stop writing new `monitor_*` fields and `outcome="monitored"`.
- Keep a read/reconcile compatibility adapter for historical monitor artifacts until a
  deliberate retirement point; do not rewrite immutable history.
- Optionally keep a one-release hidden tombstone that exits with an exact `sase shell`
  translation, but do not keep a functional legacy alias if the product decision is to
  remove `sase monitor`.

### Follow-on — migrate attached ACE procs

Only after the shared proc engine is stable should the separate
`detached_proc_convergence` work migrate the ~54 ACE producer sites from Python callables
to command-backed procs. The schema-3 dedup, result sidecar, settlement, and completion
watching built here are prerequisites, but converting all those call sites should not be
bundled into the shell convergence epic.

---

## 10. Compatibility and migration

### Existing proc records

- Schema 3 reads schema-2 `command` / `tui` / `detached` rows with no invented names.
- New fields default to absent/no-op.
- Old active procs retain their existing supervisor behavior; do not mutate ownership
  underneath a running process.

### Existing monitor records

- Never try to adopt a live monitor's process group into a new proc record. The recorded
  pid, claim, barrier, and settlement ownership cannot be transferred safely after the
  fact.
- Let already-running supervisors finish under the code they loaded.
- `sase shell list/show/stop` may recognize legacy monitor artifacts during the
  compatibility window so an upgrade does not strand them after the public monitor CLI
  disappears.
- Keep old `monitor_*` scan fields readable. Historical agent families, chats, and done
  markers are immutable evidence, not migration input.

### Failure during rollout

The feature is ready to switch only when both control paths agree:

- killing through `sase proc` suppresses the shell follow-up and releases the claim;
- stopping through `sase shell` produces the same proc terminal record;
- a proc-store row without a member can be reconciled or cleaned;
- a shell member whose proc row was pruned still renders its terminal snapshot;
- a shell member whose proc is stuck in `settling` is repairable idempotently.

---

## 11. Verification matrix

### Identity and concurrency

- same project/name, simultaneous identical starts -> exactly one proc executes and both
  callers resolve it;
- same project/name, different fingerprint -> one starts and one gets a visible
  conflict;
- same name in different projects -> both may run;
- terminal-name reuse -> new proc id, name resolves to active/newest, old id still exact;
- overlapping lane/exclusive scope under different names -> rejected atomically.

### Start and process ownership

- starter kills itself immediately after start -> proc survives;
- bootstrap dies before ack -> command never starts, claim returns to starter;
- claim transfer fails -> launch barrier remains closed and command never starts;
- stale/recycled supervisor pid -> unrelated process is never signaled;
- pre-reboot active row -> becomes lost, never replayed.

### Output and timeout

- continuous output past total timeout;
- partial line with no newline;
- invalid UTF-8;
- stdout/stderr closed while process remains alive;
- background grandchild holds stdout;
- idle timeout versus intentionally quiet command;
- TERM-ignoring process tree requires KILL escalation;
- rotation while `proc show --follow` and `shell show --follow` both read.

### Settlement and handoff

- success, nonzero, total timeout, idle timeout, explicit stop, supervisor crash;
- stop through either CLI suppresses `--next`;
- follow-up claim transfer succeeds, degrades to a fresh claim, or fails with a durable
  prompt and visible error;
- crash at every `settling` step resumes without duplicate follow-up or claim release;
- proc is not terminal and `%wait` does not advance before settlement completes;
- terminal member log remains readable after proc pruning.

### Surfaces and integrations

- the same proc id/name/status/log appears in `sase proc`, `sase shell`, Procs tab, and
  the linked Agents row;
- approved epic launch uses a named proc with no detached-task fallback;
- JSON envelopes expose the proc record as the canonical execution object;
- no new runtime path imports `sase.monitor` or writes `monitor_*` data;
- legacy monitor records remain readable and stoppable during the compatibility window.

Run `just check-full` through the long-command mechanism only after a bootstrap smoke
test proves the new shell survives starter teardown; also run the visual snapshot suite
because both the Agents and Procs presentations change.

---

## 12. Decisions to make before planning

Only a few product choices remain genuinely open:

1. **Name syntax and scope.** This report recommends project-scoped names, defaulting to
   the agent lane, with terminal reuse and proc ids for permanent history.
2. **Legacy CLI behavior.** Hard argparse removal immediately, or a one-release
   nonfunctional tombstone that prints the equivalent `sase shell` invocation.
3. **Host shell family membership.** This report recommends that host-started named
   procs need no artificial agent lane; `--lane` opts into a family projection.
4. **Internal outcome spelling.** Choose a neutral `proc` / `proc_handoff` vocabulary
   rather than continuing to emit `monitored`.
5. **Shell executable.** Preserve current `/bin/sh -c` semantics initially; a future
   explicit shell-selector option can be added if there is a concrete need.

None of these changes the architectural recommendation.

---

## Recommended solution

Implement **named procs as ordinary detached Proc records with an optional immutable
`name`, not as `kind="named"`**. Add a trusted `profile="shell"` lifecycle, and make
`sase shell` a direct service-level facade over `sase.procs` for
`list|show|start|stop`. Promote the hardened monitor bootstrap, launch barrier, process
identity, total/idle timeouts, bounded byte logging, stop semantics, and crash
reconciliation into the single proc supervisor before switching any callers.

For agent-started shells, retain a thin `agent_family_role="shell"` member that points
to the canonical `proc_id`; let it own only lane lineage, custom presentation, workspace
handoff policy, follow-up-agent policy, and a terminal history snapshot. Keep live
execution and control exclusively in the proc store. Finish `sase-kp` and `sase-lh`,
land this as a separate schema-3 convergence epic, migrate approved epic launches and
the agent skill, then remove the public `sase monitor` command while preserving a
read/reconcile adapter for historical monitor artifacts. After that foundation is
stable, use it for the separate migration of ACE's attached callable procs.
