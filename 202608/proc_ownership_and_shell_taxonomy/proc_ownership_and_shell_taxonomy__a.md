---
create_time: 2026-08-14
updated_time: 2026-08-14
status: research
---

# Proc-shell convergence: one supervisor, a monitor facade, and a clearer agent taxonomy

**Research question.** What is the best architecture for making every Proc
supervisor-owned and process-detached, removing `-d|--detached` from `sase proc run`,
merging monitors into the Proc service through `--shell <name>`, and replacing the
confusing **agent lane** term with a taxonomy built around **SASE agents** and **SASE
shells**?

**Snapshot.** Verified on 2026-08-14 against `sase` at `191e9f219`, `sase-core` at
`41701509f` (`v0.27.2`), and the live Proc store. This report revisits and supersedes the
obsolete parts of:

- [`detached_proc_convergence`](../detached_proc_convergence/detached_proc_convergence.md),
- [`sase_shell_named_procs`](../sase_shell_named_procs/sase_shell_named_procs.md), and
- [`monitor_command_substrate`](../monitor_command_substrate/monitor_command_substrate.md).

The Proc rename has now landed, but the behavioral convergence has not. The current
repository still has an ACE-owned callable Proc runtime, three Proc kinds, and a wholly
separate monitor execution/store projection.

## Bottom line

The four requested changes fit one coherent model, with one important refinement:

> A Proc is the durable execution record. A **proc shell** is a Proc with a SASE-shell
> identity. A **monitor** is the family-attached proc-shell workflow. `sase monitor`
> should remain a user-facing compatibility/policy facade, but it should call the Proc
> service directly and should not own a second supervisor or execution record.

That model leads to eight conclusions.

1. **Every newly-written Proc should have one non-empty immutable argv and one detached
   supervisor.** ACE may retain ordinary Textual workers for short UI-support work, but
   those workers must stop being called, stored, counted, or displayed as Procs.
2. **Delete `tui` as an execution kind and stop writing both `command` and `detached`
   kinds.** They encode two orthogonal facts—execution ownership and session
   attribution—neither of which needs a kind after convergence. Keep `session_id` only
   as optional attribution.
3. **Add `-S|--shell NAME` to `sase proc run`.** The wire field should be named
   `shell_name`, not merely `name`, and its presence should make the row a proc shell.
   Do not add a `shell` Proc kind.
4. **Do not use `shell_name` as the general deduplication mechanism.** A shell name is
   identity/addressability. Store-wide concurrency keys are a separate concern and must
   be reserved atomically in Rust before ACE-owned work moves out of process.
5. **Extract the hardened monitor supervisor into a neutral Proc supervisor kernel.** It
   already has the double-fork, startup acknowledgement, launch barrier, process
   identity, environment scrubbing, timeouts, TERM-to-KILL escalation, and recovery
   behavior the Proc supervisor lacks.
6. **Preserve the agent-artifacts projection for a family-attached proc shell.** The Proc
   row owns execution; the artifacts member owns family lineage, `%wait`/`#fork`, chat
   history, workspace-claim policy, follow-up policy, and durable family presentation.
7. **Make terminal Proc status mean settlement is finished.** Today monitor state becomes
   terminal before claim/follow-up settlement, and `monitor_settled` compensates for that
   ordering. The unified supervisor should enter `phase="settling"`, settle exactly once,
   and only then write the terminal Proc outcome.
8. **Do not add a top-level `sase shell` command.** That was the largest obsolete
   assumption in the prior named-Proc report. `shell` is the cross-cutting taxonomy and
   an option on `sase proc`; `sase monitor` remains the specialized facade.

## 1. Recommended taxonomy

The proposed terms work well if aggregate identity and execution-leaf identity are kept
strictly separate.

```text
SASE agent                         SASE shell
├─ standalone agent shell         ├─ agent shell (an LLM/provider run)
└─ agent family                   └─ proc shell  (a supervised command Proc)
   ├─ agent shell
   ├─ proc shell / monitor
   └─ agent shell
```

### 1.1 Precise definitions

| Term | Recommended definition |
| --- | --- |
| **SASE agent** (or **agent**) | Either an agent family or one standalone agent shell. This replaces **agent lane**. It is the durable/user-facing identity used for provenance, association, family-level display, and resumption. |
| **Agent shell** | One concrete LLM/provider execution member. It may stand alone or belong to an agent family. A family member such as `foo--code` is an agent shell; the family container `foo` is a SASE agent but is not itself a shell. |
| **Proc shell** | One named, supervisor-owned command Proc. It may be attached to an agent family; future work may give an unattached proc shell full standalone orchestration semantics. |
| **SASE shell** (or **shell**) | The leaf union: either an agent shell or a proc shell. A shell is something that actually executes; a family, clan, hood, and tribe are not shells. |
| **Monitor** | The workflow/presentation name for a proc shell attached to an agent family. It adds claim transfer, family membership, optional agent follow-up, and family history around the ordinary Proc service. It is not a Proc kind or a second execution primitive. |
| **Supervisor** | The detached OS process that owns a Proc command and its process group. It is infrastructure, not the proc shell itself. |

This resolves the original ambiguity cleanly:

- `foo` can be a standalone SASE agent whose only member is agent shell `foo`.
- After family promotion, `foo` is a family SASE agent containing shells such as
  `foo--plan`, `foo--mon`, and `foo--code`.
- `foo--plan` and `foo--code` are agent shells.
- `foo--mon` is a proc shell and, because it belongs to the family, a monitor.

### 1.2 A necessary adjustment to “agent family”

Current documentation calls a monitor “a real agent-family member whose work is one
supervised OS command instead of an LLM turn.” Once **agent shell** means the LLM leaf,
that wording becomes contradictory. An agent family should be defined as a strictly
sequential chain of **SASE shells**, not a chain containing only agent shells. The family
remains an *agent* because it is the aggregate unit of agentic work, lineage, provenance,
and resumption.

This is a glossary-level change, not merely prose polish. Code currently encodes
`agent_family_role="monitor"`; new records should separately encode:

- the member's execution kind (`shell_kind="agent"|"proc"`), and
- its family role/suffix (`plan`, `code`, `mon`, `review`, and so on).

`agent_family_role` and “which kind of shell executes this member?” are orthogonal.
Legacy `agent_family_role="monitor"` must remain readable.

### 1.3 Where “agent lane” is embedded today

The exact phrases “agent lane”, “family lane”, and “solo lane” occur 76 times across 33
current source, test, documentation, and memory files. The semantic abstraction is also
centralized in `src/sase/agent_lanes.py` as `AgentLaneRef`, `lane_ref_for_agent()`,
`lane_ref_for_lane_name()`, and `lane_name()`. It feeds commit provenance, agent-sidecar
publication, hosted links, artifact references, and ACE kinship rendering.

That module already implements almost exactly the proposed SASE-agent projection:

- a concrete family member projects to its bare family name;
- a standalone shell projects to itself; and
- a bare name consults the family-name reservation registry to disambiguate family from
  singleton.

Therefore the taxonomy migration should preserve behavior and rename the abstraction,
not redesign it. Introduce `SaseAgentRef`/`sase_agent_ref_for_shell()` and retain
`AgentLaneRef`/`lane_*` compatibility aliases for a deprecation window. Do not mix a
repository-wide internal rename into the supervisor convergence's highest-risk phase.

### 1.4 Surface consequences

The new vocabulary also clarifies several currently overloaded surfaces:

- `sase agent list` should primarily list SASE-agent aggregates, not pretend every
  family member is another peer agent.
- `sase agent show foo` may show the standalone SASE agent or family aggregate named
  `foo`; `sase agent show foo--code` explicitly selects one agent shell.
- `sase agent kill` can only kill a live agent shell, never a family container, so its
  help should say exactly that.
- `SASE_AGENT_NAME` currently carries the concrete member name and is therefore an
  **agent-shell name** under the new taxonomy. Family/provenance projection should use a
  separately named SASE-agent field or helper.
- Commit footer `SASE_AGENT=...` already carries today's lane projection; under the new
  terms it carries the SASE-agent identity. That behavior does not need to change.

The storage and CLI strings do not all need to rename in the supervisor epic, but new
APIs should stop adding ambiguous uses of bare “agent.”

### 1.5 Naming cautions

“Shell” has an unavoidable OS-shell meaning. CLI help must consistently say “named Proc
shell” and must not imply that `--shell NAME` selects `/bin/bash` or another command
interpreter. The monitor's shell command should be compiled explicitly to argv (for
example `[/bin/sh, -c, COMMAND]`) at the facade boundary rather than using
`Popen(..., shell=True)` in the supervisor.

Likewise, use `shell_name` in the wire and Python model. A bare `name` would be confused
with Proc label, agent name, family name, provider name, or project name.

## 2. What the current architecture proves

### 2.1 Proc `kind` still conflates two axes

Current `Proc` rows have three kinds (`src/sase/procs/models.py:18-23`):

| Current kind | Execution owner | Session attribution | Command requirement |
| --- | --- | --- | --- |
| `command` | Proc supervisor | optional/current session | Python submit path requires argv |
| `detached` | Proc supervisor | none/global | Python submit path requires argv |
| `tui` | ACE process and Textual worker thread | ACE session | command usually absent |

`submit_proc()` and `submit_detached_proc()` both call `_submit_supervised_proc()` and
spawn `sase.procs.supervisor` with `start_new_session=True`
(`src/sase/procs/runner.py:52-184`). The only behavioral difference at submission is the
kind and whether `session_id` is forced to `None`.

Thus `-d|--detached` does **not** currently choose whether the command is detached from
its caller. Both paths are already process-detached. It chooses the legacy “global,
unattributed” projection. `--session none` already expresses that fact directly.

The clean model is:

- execution ownership: invariant—always the Proc supervisor;
- process detachment: invariant—always detached;
- session attribution: `session_id: Optional[str]`;
- shell identity: `shell_name: Optional[str]`;
- family attachment: `artifacts_dir: Optional[str]` plus a reciprocal `proc_id` link.

No `kind` is needed for any of those facts.

### 2.2 The ACE-owned Proc runtime remains intact

The Proc rename was behavior-preserving. `ProcActionsMixin._submit_tracked_proc()` still:

1. accepts a Python callable and captures its closure;
2. reserves deduplication only in the current `ProcQueue`;
3. runs the callable via `run_worker(..., thread=True)` inside ACE;
4. stores typed payloads and completion callbacks only in memory; and
5. asks `ProcMirror` to write a `kind="tui"` row whose `pid` is ACE's pid.

The current call-site count is unchanged from the prior detached-Proc report:

- 29 real direct calls,
- 24 duck-typed `getattr(..., "_submit_tracked_proc", None)` calls,
- **53 real producers across 37 files**.

The 24 dynamic lookups matter. Merely changing typed call sites or deleting a public
method will not prove the old execution path is gone; a static regression test must also
reject those string lookups.

The live store reinforces the model mismatch. At the snapshot it had 101 rows, all
`kind="tui"`; 99 of 101 had an empty command. None was active. The earlier sample had
the same shape at larger scale (274 of 278 TUI rows commandless). Empty command is the
designed default, not a rare data defect.

### 2.3 The command requirement is not enforced in Rust

`_validated_argv()` rejects an empty argv in the Python supervisor submit path
(`src/sase/procs/runner.py:337-341`). The Rust store validates non-empty id, label, cwd,
origin, creation timestamp, and log path, but not `command`
(`sase-core/crates/sase_core/src/procs/store.rs:391-419`). That is why commandless TUI
rows are valid durable records.

After convergence, command validity is a domain invariant and belongs in Rust as well as
Python. Read compatibility needs care: the store's current validator is used while
loading old rows, so blindly adding `command must not be empty` would make historical
TUI rows disappear as invalid. Split read compatibility from new-write validation:

- tolerate an empty command only when reading a legacy `kind="tui"` row;
- reject every new append/reservation with an empty argv; and
- never allow update to erase an existing command.

### 2.4 Monitor is the stronger supervisor

The current monitor package is 4,147 lines with 4,843 lines of monitor tests; the Proc
package is 1,621 lines. Size alone is not the argument—the capability comparison is:

| Capability | Current Proc supervisor | Current monitor supervisor |
| --- | --- | --- |
| Detachment | `start_new_session=True` | double-fork and reparent before return |
| Startup proof | none | startup marker plus bounded acknowledgement wait |
| Command launch barrier | none | command cannot exec until claim transaction releases barrier |
| Supervisor identity | `/proc/<pid>/cmdline`, liveness-only fallback | boot-aware pid/start identity |
| Total and idle timeout | none | both, checked independently of output |
| Output | shared bounded byte pipe | same pipe plus head/tail capture |
| Agent identity scrubbing | no | yes |
| Reconciliation | terminal status flip | kill child group, settle claim/follow-up, handle reboot/lost state |
| Idempotency | none | full request fingerprint under a per-family lock |

The monitor hardening described by the prior research has landed. Recent changes also
made the monitor claim the command's actual workspace before launch. The recommendation
is therefore not “make Procs call monitor.” Extract the proven process-owning pieces into
a neutral Proc kernel, then make both ordinary Procs and monitor policy call that kernel.

### 2.5 Monitor's artifacts record is valuable, not duplication to delete

A monitor currently has no Proc row. It is represented by `agent_meta.json` plus
`done.json` in a family-member artifacts directory. This is why it automatically works
with:

- family order and roster rendering,
- workspace-claim transfer,
- `%wait` and `#fork`,
- `sase chats` and response history,
- model/provider inheritance for the follow-up, and
- family runtime/status projection in ACE and integrations.

Removing the artifacts record would force every family, wait, chat, mobile, editor, and
artifact-index consumer to join the Proc store. That is a much larger migration and
would make the future shell taxonomy less clear, not more.

The duplication to remove is **execution state and supervision**, not family lineage.

### 2.6 The current Rust Proc store needs transactional operations

The Rust store already holds an exclusive lock around append/update/prune, but the
Python producers perform read-then-submit dedup outside it. The live ACE queue similarly
deduplicates only within one TUI process. Once every TUI action submits a global Proc,
two ACE instances can race the same Patch update, plugin install, agent cleanup, or AXE
slot.

The store needs purpose-built atomic operations, not more conventions around
`read_procs()` plus `append_proc()`:

- `reserve_proc`: check active concurrency-key overlap and shell-name collision, then
  append one pending row under the same lock;
- `request_proc_stop`: record stop intent without prematurely terminalizing;
- `finish_proc`: compare active state, write outcome once, and refuse a second terminal
  owner; and
- optionally a narrow compare-and-set update for supervisor pid/identity and launch
  barrier state.

## 3. The `--shell` contract

### 3.1 Exact CLI shape

The option belongs to `run`, not to the `proc` group itself; bare `sase proc` defaults to
`sase proc list`, and list flags conventionally follow the explicit `list` token.

```bash
sase proc run -S check-full -- just check-full
sase proc run --shell check-full -- /bin/sh -c 'just check-full'
sase proc list --shell check-full
sase proc show check-full
sase proc kill check-full
```

The long option needs a short alias under the project CLI rules. `-s` is currently
`--session`, so use **`-S|--shell`** on Proc subcommands. Subcommand-local reuse does not
conflict with monitor's existing `-S|--stop-status`.

`show` and `kill` should continue accepting ids and id prefixes, then also accept an
exact shell name. `list --shell NAME` is a history filter. A Proc id remains the canonical
unambiguous execution identity.

### 3.2 Meaning of a shell name

`shell_name` is:

- immutable for one Proc row;
- unique among **active** proc shells in a project;
- reusable after terminal settlement, so `list --shell NAME` is run history; and
- compatible with the SASE shell-name grammar owned by core.

Resolution should prefer exact shell name, then exact Proc id, then a unique id prefix.
Names that are lexically valid Proc ids should be rejected to avoid precedence
ambiguity. A shell Proc must have a resolved project; a named global-namespace fallback
would create collisions that cannot later participate safely in project-scoped
xprompts.

The same active shell name with the same `request_fingerprint` is an idempotent replay.
The same active name with a different fingerprint is a visible conflict naming the
blocking Proc. This is a narrow identity invariant; it is **not** a substitute for the
general concurrency keys required by ACE actions.

### 3.3 Family attachment is separate

A proc shell's name must not imply that it is attached to a family. Persist attachment
explicitly through `artifacts_dir` and a reciprocal `proc_id` in the member metadata.

For a monitor start, the monitor service:

1. resolves/promotes the target SASE agent;
2. allocates the exact family-member shell name (`foo--mon`, `foo--mon-0`, ...);
3. creates/reserves the Proc with that `shell_name` and family attachment; and
4. delegates launch to the Proc service.

For direct `sase proc run --shell NAME`, the first release can create an unattached named
Proc row but should not claim that `%wait`, `#fork`, or family scheduling understands it.
This exposes the requested CLI without pulling the future standalone-shell orchestration
work into this change. Put differently: standalone proc-shell **identity and control**
can exist now; standalone proc-shell **participation in the agent topology** remains the
future direction.

If even identity-only standalone shells are considered out of scope, then a public
`--shell` option and that scope are in tension: without a family-attachment argument,
the direct CLI necessarily creates an unattached shell. The identity-only interpretation
is the smallest coherent resolution.

### 3.4 `shell_name` is not a Proc kind

Namedness, session attribution, family attachment, and execution ownership are four
independent axes. Encoding any combination as `kind="shell"` would immediately recreate
today's `command`/`detached`/`tui` problem and make standalone proc shells a schema
special case.

Use nullable fields and invariants instead:

```text
shell_name is None, artifacts_dir is None  -> ordinary Proc
shell_name is set,  artifacts_dir is None  -> unattached proc shell
shell_name is set,  artifacts_dir is set   -> family-attached proc shell / monitor
shell_name is None, artifacts_dir is set   -> invalid
```

## 4. Recommended record split

### 4.1 Proc row owns execution

The existing Proc row should retain argv, cwd, project/workspace attribution, session
attribution, label, tags, pid/pgid, timestamps, phase, status, exit code, message, and log
path. Add these nullable/additive fields in the next wire version:

| Field | Purpose |
| --- | --- |
| `shell_name` | Proc-shell identity; null for an ordinary unnamed Proc |
| `artifacts_dir` | Immutable cross-link for a family-attached proc shell |
| `reason` | Human/agent explanation; required by monitor policy, optional for ordinary Procs |
| `supervisor_identity` | Boot-aware protection against stale/reused pids |
| `timeout_ms`, `idle_timeout_ms` | Neutral supervision policy; integer milliseconds preserve the Rust wire's `Eq` model and avoid floats |
| `request_fingerprint` | Idempotency comparison for named starts |
| `concurrency_keys` | Atomic store-wide exclusion for actions that must not overlap |
| `result_path` | Durable structured result envelope for non-UI completion/recovery |
| `termination_reason` | Distinguish normal exit, stop, total timeout, idle timeout, supervisor loss, and start failure without multiplying kinds |
| `stop_requested_at` | Durable stop intent; the supervisor/reconciler remains the terminal writer |

The earlier named-Proc report proposed floating-point timeout fields. Current Rust
`ProcWire` derives `Eq`, so integer milliseconds are a cleaner wire contract.

Do **not** persist a Python callback, import path, arbitrary settlement command, or hook
path. Family-shell settlement is a closed built-in capability triggered by
`artifacts_dir is not None`. Persisted arbitrary code references would become a durable
mixed-version remote-code-execution contract.

### 4.2 Family artifacts own lineage and policy

The artifacts member should own only facts that make sense because the Proc belongs to
an agent family:

- exact family/member identity and role;
- `shell_kind="proc"`;
- reciprocal `proc_id`;
- start/stop display labels;
- starter and optional follow-up agent-shell identities;
- next action/output policy and follow-up disposition;
- chat response path and terminal family snapshot; and
- workspace-claim lineage needed for transfer/recovery.

Execution fields currently duplicated among the 31 Rust `monitor_*` scan-wire fields—
command, cwd, pid, pgid, supervisor identity, timeout, exit code, output path—should
project from the Proc row for new records. Legacy fields remain readable indefinitely.

### 4.3 Two records, one writer, one ordering rule

A family-attached proc shell necessarily has two records. Make consistency explicit:

- Proc row is the source of truth for execution and control.
- Artifacts are the source of truth for family topology and history.
- Each contains one immutable cross-link to the other.
- The Proc supervisor is the only normal writer after launch.
- The reconciler acts as that writer only after proving the supervisor is dead.

The finish order should be:

```text
child exits / timeout / stop request
  -> proc.phase = "settling" (still active)
  -> retain/finalize output
  -> release or transfer workspace claim
  -> launch, degrade, suppress, or durably reject follow-up
  -> write family member metadata + done.json + chat history
  -> proc.status = terminal, with termination_reason
```

Invariant: **terminal Proc status implies the command is gone and every required
settlement side effect is durable.** This lets `sase proc show --follow`, `sase monitor
show --follow`, `%wait`, ACE's indicator, and future standalone-shell waits observe one
authoritative completion condition. New records no longer need `monitor_settled`.

### 4.4 Log ownership must follow the durable history

Proc retention currently keeps only a configured number of terminal rows and deletes
logs by recomputing `procs/logs/<id>.log`; Proc log readers also recompute from the id
instead of honoring the row's `log_path`. A family member can outlive Proc history
retention indefinitely.

Therefore:

- ordinary and unattached proc-shell logs stay in the Proc log directory;
- family-attached proc-shell logs stay inside the member artifacts directory;
- every reader follows `Proc.log_path`; and
- pruning deletes only logs actually owned by the pruned Proc lifecycle, never an
  artifacts-owned log.

An integration test must append more than the history limit after a monitor settles and
then prove that its family history and output remain readable.

### 4.5 Wire compatibility

Current Python explicitly supports Proc wire schemas 1 and 2. Add schema 3 to that
supported set; do not replace the explicit set with “any version greater than or equal
to 2,” because a future version may change semantics rather than merely add fields.

Every new Rust field must use serde defaults so v1/v2 rows remain readable. Legacy
`kind` values should remain accepted on read but never be emitted for new rows after the
cut-over. A one-time rewrite is optional; compatibility should not depend on rewriting
historical evidence.

## 5. One service and one supervisor

### 5.1 Service boundary

Introduce one typed Proc start service, conceptually:

```python
StartProcRequest(
    argv=...,
    cwd=...,
    label=...,
    project=...,
    session_id=...,
    shell_name=...,
    timeout_ms=...,
    idle_timeout_ms=...,
    concurrency_keys=...,
    request_fingerprint=...,
    family_attachment=...,
)
```

`sase proc run`, ACE, bead launches, epic launches, and the monitor facade should all
call this service. The service validates, atomically reserves the row, spawns the neutral
supervisor, waits for its startup acknowledgement, completes any claim transaction, and
releases the launch barrier.

“Monitor wraps Proc at the service level” specifically means:

- no spawning `sase proc run` and parsing its JSON;
- no `proc supervisor -> sase monitor _run -> user command` wrapper process; and
- no second monitor store that must be reconciled with the Proc store.

A wrapper child is particularly unsafe: `sase proc kill` would kill the process that
must release the claim and decide the follow-up before it could settle.

### 5.2 Neutral supervisor kernel

Move the monitor's proven mechanics into `sase.procs` (or a neutral shared module owned
by that package):

- double-fork/reparent bootstrap;
- startup acknowledgement;
- launch barrier;
- boot-aware supervisor identity;
- byte-oriented bounded output;
- total/idle timeout loop;
- process-group TERM then KILL;
- agent-identity environment scrubbing;
- stop-intent observation; and
- crash/reboot reconciliation.

The supervisor should execute `Proc.command` directly as argv. Monitor's command-string
facade translates its shell string to explicit `sh -c` argv before submission.

Then add one closed family-attachment settlement path when `artifacts_dir` is present.
The generic kernel must not import CLI handlers, TUI actions, or dynamically named
callbacks.

### 5.3 Start transaction

For a family-attached proc shell, the safe ordering is:

```text
acquire family lifecycle lock
  -> reserve pending Proc and concurrency keys atomically
  -> create family-member artifacts with reciprocal proc_id
  -> spawn/reparent supervisor and obtain identity
  -> supervisor opens log and acknowledges while blocked at launch barrier
  -> acquire/transfer workspace claim to verified supervisor
  -> release barrier
  -> supervisor starts argv and marks Proc running
  -> monitor facade performs starter handoff only after acknowledgement
```

Every failure before the barrier needs a compensating transition that prevents the
command from running and restores/releases any claim. A dead pre-reboot active Proc is
`lost`; it must never be automatically replayed because the prior command outcome is
unknowable.

### 5.4 Stop semantics

Current `kill_proc()` signals and immediately writes `status="killed"`, while the
supervisor also writes terminal state. That race becomes unacceptable when settlement
must run exactly once.

`sase proc kill` and `sase monitor stop` should both:

1. atomically record stop intent;
2. verify supervisor identity and signal the supervisor;
3. wait or return while the supervisor kills the child group and settles; and
4. let only the supervisor—or dead-supervisor reconciler—write terminal outcome.

Monitor presentation can map `termination_reason="stop"` to `stopped`; the Proc surface
can continue rendering `killed` if that compatibility is valuable. The stored fact
should be one neutral reason.

## 6. Eliminating ACE-owned Procs

### 6.1 Do not turn every Textual worker into a Proc

The goal should be **no work classified as a Proc executes inside ACE**, not “ACE may no
longer have worker threads.” Short cache reads, prompt stash writes, and purely
presentation-support I/O still need to stay off the Textual event loop, but making a new
Python supervisor and `sase` child for a 90 ms operation is a major latency and history
noise regression.

Use this boundary:

- Proc: durable, long-running, cross-surface, independently inspectable/killable,
  subprocess/network/VCS work, or work that must survive ACE.
- Plain Textual/pump-free worker: short UI-support computation or I/O whose result is
  meaningless after the current UI interaction disappears.

Those workers must not enter the Proc store, Procs pane, quit warning, or Proc indicator.

### 6.2 Replace callable submission with argv submission

The current `ProcActionsMixin` should become an argv-first facade with no `Callable`
parameter. ACE submits a Proc service request and records only ephemeral observer policy:

- which Proc id it is watching;
- whether to notify on completion;
- whether to schedule an ordinary refresh; and
- an optional UI-only callback that may improve the current screen but is never required
  for correctness.

The existing `ProcMirror` writer becomes a **Proc observer**. It no longer creates
`kind="tui"` rows or flushes in-memory logs; it polls watched Proc ids and the global
active count off the event loop, then marshals terminal notifications through
`call_from_thread`.

Losing ACE must lose only ephemeral presentation. It must never lose a mutation, claim
release, receipt, next action, or result.

### 6.3 Durable request and result contracts

TUI callables currently close over live `Agent`, modal, plan, and bound-method objects and
return typed Python payloads directly to callbacks. A detached process cannot—and should
not—serialize those object graphs.

For each migrated operation:

- reduce input to durable identifiers and re-resolve current state in the command;
- put large or sensitive input in a mode-0600 versioned request sidecar rather than argv;
- write a mode-0600 versioned result envelope to `result_path` before exiting; and
- make completion/restart behavior derive from durable domain state plus that envelope.

Do not parse structured results from combined stdout/stderr. Logs are presentation and
diagnostics, not a protocol.

### 6.4 Put commands in domain services and CLI groups

The prior inventory remains valid. Migrate in this order:

1. notification/gate/launch and bead operations that already have headless commands;
2. Patch actions, extracting surface-neutral domain services and command handlers;
3. plugin/environment orchestration already composed from subprocesses;
4. agent cleanup/revert/dismiss flows after their live-object closures become
   identifier-keyed transactions; and
5. AXE workspace execution after its slot reservation becomes a store-wide concurrency
   key.

Declassify sub-second UI-support work instead of inventing commands for it.

Commands belong under their domains (`sase patch`, `sase agent`, `sase bead`, `sase
gate`, `sase plugin`, `sase workspace`, and so on), because those services are useful to
every frontend. A generic hidden `sase proc exec --payload ...` merely freezes TUI
implementation details into a private versioned protocol and should not be the primary
migration strategy.

### 6.5 Store-wide concurrency is a prerequisite

Current `dedup_key` and `exclusive_scopes` exist only in one ACE process. Persist a
single normalized `concurrency_keys` set instead. Examples:

- `patch:<project>:<patch>` for mutually exclusive Patch mutations;
- `plugin:<name>` for one package operation;
- `workspace:<project>:<num>` or `axe-slot:<n>` for a workspace execution slot; and
- `agent-meta:<artifacts-dir>` for directive persistence.

Two active requests with overlapping keys conflict atomically. If both the concurrency
keys and request fingerprint match, returning the already-active Proc is an idempotent
replay. This design covers the current exact dedup key and overlapping exclusive scopes
without coupling either to `shell_name`.

## 7. `sase monitor` after convergence

`sase monitor` should remain visible and useful. It expresses policy that generic Procs
do not:

- target/default the calling SASE agent;
- promote a singleton to an agent family;
- allocate a proc-shell member name;
- require a reason and bounded timeout;
- transfer the workspace claim;
- kill/handoff the starter agent shell; and
- optionally launch the next agent shell with inherited history/model/effort.

### 7.1 Start

`sase monitor start` parses its current flags into a monitor-policy request, prepares the
family attachment, and calls `start_proc()` directly. It returns both the Proc id and the
proc-shell member name. The command itself is owned directly by the Proc supervisor.

### 7.2 List/show/stop

For new records:

- `monitor list` queries family-attached proc shells and enriches them with family data;
- `monitor show` delegates execution/output reading to the Proc service and adds family
  and follow-up detail; and
- `monitor stop` resolves the family member then calls the same Proc stop service as
  `proc kill`.

All new monitors therefore appear in the unified Procs pane/list and under their family
in the Agents tab, with the same Proc id, status, and output.

### 7.3 Compatibility

Existing artifacts-only monitors must remain readable and stoppable during the migration.
Do not attempt to adopt an already-running monitor process group into a new Proc row; its
claim, pid identity, and settlement ownership cannot be transferred safely after launch.
Let the loaded legacy supervisor finish, and keep the legacy reconciler until no active
legacy record can remain.

Historical `monitor_*` fields and `agent_family_role="monitor"` are evidence, not data to
rewrite destructively. New readers should project both formats.

## 8. Removing `-d|--detached` and legacy kinds

### 8.1 Run behavior

After the cut-over, every `sase proc run` is detached by invariant. Remove
`-d|--detached`; retain `-s|--session REF` only as optional attribution, with `--session
none` for an unattributed Proc. Session attribution must not change ownership,
visibility, killability, or survival.

Keeping `--session` is useful because ACE can highlight work initiated for its session
without pretending the session owns the process. If that UI grouping is no longer
valuable, removing it is a later orthogonal simplification.

For one release, a suppressed compatibility parser for `-d|--detached` should reject it
with an actionable message:

```text
all Procs are detached; remove --detached (use --session none for no attribution)
```

This is safer than a generic argparse failure, especially because the command itself is
captured through a remainder positional. Apply the same behavior through the legacy
`sase task` alias. Remove the sentinel after the compatibility window.

### 8.2 List behavior

Stop exposing `--kind` and the list-side `--detached` filter for new semantics. During a
compatibility window they may remain hidden legacy-history filters. Replace meaningful
queries with orthogonal filters such as `--shell`, `--session`, `--project`, `--status`,
and `--tag`.

### 8.3 Old rows and mixed versions

- New code never writes `kind="tui"`.
- Old ACE instances may still write TUI rows during a rolling upgrade; readers tolerate
  them, and only their owning old ACE can finish them.
- A dead active legacy TUI row reconciles deterministically to error/lost after its ACE
  pid disappears.
- Legacy `command` and `detached` rows remain readable as equivalent supervised Proc
  history.
- Once the compatibility window closes, remove `TUI_PROC_KIND`,
  `DETACHED_PROC_KIND`, `_SUPERVISOR_OWNED_KINDS`, `MIRROR_KIND`, kind filters, and the
  TUI kill refusal.

## 9. Options considered

| Option | Result | Assessment |
| --- | --- | --- |
| Rename monitor to a new top-level `sase shell` CLI | Two execution substrates remain or monitor policy disappears into a generic command | Reject; obsolete assumption from prior research |
| Make `shell` a fourth Proc kind | Namedness, attachment, and execution get conflated again | Reject |
| Use shell name as every dedup/exclusion key | Identity changes whenever concurrency policy changes; unrelated operations collide | Reject |
| Make monitor spawn `sase proc run` | Adds CLI-to-CLI parsing and a second interpreter boundary | Reject |
| Put a monitor wrapper process under the Proc supervisor | Kill destroys the process responsible for settlement | Reject |
| Store a monitor only as a Proc row | Loses family/wait/fork/chat/claim semantics or forces joins into every consumer | Reject |
| Keep monitor artifacts only but share the supervisor | Smaller, but monitor stays absent from the unified Proc list and cannot provide the TUI migration's store-wide identity/concurrency substrate | Valid fallback, not recommended |
| Proc row plus optional family artifacts projection | One execution/control plane and preserved agent topology | **Recommend** |
| Convert every ACE worker into a detached command | Meets a literal reading but regresses sub-second UI work and pollutes history | Reject |

## 10. Recommended implementation sequence

### Phase 0 — freeze terminology and invariants

- Approve the glossary definitions in §1.
- Define `shell_name` as exact leaf identity and `artifacts_dir` as attachment.
- Decide the short compatibility windows for `--detached`, legacy monitor reads, and
  `AgentLaneRef` aliases.
- Add architecture tests that forbid new callable Proc producers.

This phase should update the canonical glossary only when implementation begins and the
user explicitly authorizes that memory edit; it must then run `sase memory init` as the
repository instructions require.

### Phase 1 — Rust Proc wire/store v3

- Add the fields in §4.1 with serde defaults and Python schema-3 support.
- Add atomic reserve, stop-intent, and finish operations.
- Validate non-empty command on every new reservation while tolerating legacy
  commandless TUI reads.
- Add active per-project shell-name uniqueness and concurrency-key overlap tests.
- Keep legacy kinds read-compatible but stop requiring them for new records.

### Phase 2 — neutral supervisor kernel

- Extract the hardened monitor bootstrap, acknowledgement, barrier, identity, timeout,
  byte-log, env-scrub, and reconciliation mechanics.
- Switch existing supervisor-owned Procs to it first, with no monitor merge yet.
- Make control APIs write stop intent and let the supervisor own terminal state.
- Let this phase soak independently; it changes every existing command Proc.

### Phase 3 — proc shells and monitor service facade

- Add `-S|--shell` and shell-name resolution/filtering.
- Add the optional family attachment and dual-record ordering.
- Make log access path-driven and protect artifacts-owned logs from Proc retention.
- Move monitor start/list/show/stop onto Proc services while retaining legacy monitor
  projection and reconciliation.
- Collapse epic launch's monitor/Proc fallback into one Proc service call.

### Phase 4 — ACE submission and observation infrastructure

- Add argv/request/result based Proc submission.
- Turn `ProcMirror` into a store-backed observer.
- Move dedup/exclusion to Rust concurrency keys.
- Ensure UI callbacks are optional presentation only.

### Phase 5 — migrate the 53 producers

- Migrate existing headless command paths first.
- Add/extract domain commands for Patch, plugin, workspace, and agent transactions.
- Declassify short UI-support operations to ordinary workers.
- Delete callable Proc submission and its dynamic `getattr` escape hatches.

### Phase 6 — collapse legacy axes and update surfaces

- Stop writing Proc kinds; remove run-side `--detached` and later its rejection sentinel.
- Remove TUI-owned kill/reconcile/render branches and the in-memory Proc queue/log.
- Render proc shells consistently in both Procs and Agents surfaces.
- Update docs, the monitor skill, glossary, generated instruction shims, and terminology.
- Add `SaseAgentRef` aliases first; perform deeper internal `lane_*` cleanup separately.

### Phase 7 — exhaustive verification and landing

Run `just check-full` through the SASE monitor mechanism available at that phase and run
the ACE PNG snapshot suite. This crosses the Rust/Python wire, shared store, process
ownership, CLI parsers, ACE Procs and Agents surfaces, family wait resolution, workspace
claims, follow-up launch, and docs/memory.

## 11. Acceptance and failure-injection matrix

### Ownership and execution

- Every newly-created Proc has non-empty immutable argv before reservation succeeds.
- No Proc execution path accepts a Python callable.
- Quitting/crashing ACE does not interrupt an ACE-submitted Proc.
- Killing the starter agent shell immediately after start does not kill the reparented
  Proc supervisor.
- No active Proc is owned by the ACE pid.

### Identity and concurrency

- Same `(project, shell_name, fingerprint)` concurrent starts execute once and both
  callers receive the same Proc.
- Same active shell name with a different fingerprint conflicts visibly.
- Overlapping concurrency keys across two ACE instances execute once.
- Same shell name in two projects is allowed.
- Terminal shell-name reuse creates a new Proc id and history remains queryable.

### Process safety

- Bootstrap death before acknowledgement never starts the command.
- Claim-transfer failure leaves the launch barrier closed.
- A stale/reused supervisor pid is never signalled.
- Pre-reboot active work becomes lost and is never replayed.
- Partial lines, invalid UTF-8, chatty output, closed output, background grandchildren,
  quiet commands, and TERM-ignoring process groups all settle correctly.

### Settlement and durability

- Proc terminal status is not visible before claim/follow-up/artifact settlement.
- Stop from either CLI suppresses `--next` and disposes the claim exactly once.
- Crash between every pair of settlement steps resumes without duplicate follow-up or
  double claim release.
- `%wait` advances only after terminal Proc settlement.
- Family-attached output survives more than one full Proc retention window.
- ACE restart reconstructs correct state without the original UI callback.

### Compatibility and UX

- New monitors have one Proc id visible through `sase proc`, `sase monitor`, the Procs
  pane, and the family member in Agents.
- Legacy monitor records remain readable/stoppable through the compatibility window.
- Legacy `command`/`detached`/`tui` history remains readable.
- `sase proc run --help` no longer advertises `--detached`.
- During the transition, passing it produces the actionable rejection above.
- `--shell` help says “named Proc shell” and cannot be mistaken for a shell executable.

## 12. Decisions that remain product choices

The architecture does not depend on these, but they should be explicit before planning:

1. **Identity-only standalone proc shells now?** Recommended yes: allow direct
   `proc run --shell`, while deferring xprompt/wait/fork integration. Otherwise the new
   public option needs an additional family-only constraint that makes it much less
   useful.
2. **Session attribution default.** Recommended keep current/latest session attribution
   as metadata, with `--session none`; make all Proc visibility/control global.
3. **Compatibility duration.** Recommended one release for the hidden, erroring
   `--detached` sentinel and at least one release for legacy monitor control.
4. **Internal lane rename depth.** Recommended update the glossary and user-facing text
   with this feature, add compatibility aliases in code, and defer the broad mechanical
   symbol/file rename until the lifecycle work has settled.

## Recommended solution

Adopt one supervisor-owned Proc control plane with an optional `shell_name` and an
optional family-artifacts attachment.

Concretely: add `-S|--shell NAME` to `sase proc run`; treat it as Proc-shell identity,
not as a kind, command interpreter, or general dedup key. Keep `session_id` as optional
attribution, replace ACE's in-process Proc callables with command-backed Proc submissions,
and leave short UI-support work as untracked Textual workers. Add atomic store-wide
concurrency keys and structured request/result sidecars before migrating those ACE
producers.

Promote the hardened monitor supervisor into the neutral Proc kernel. Let the Proc row
own command execution, process identity, timeout, output, control, and terminal outcome;
let an attached artifacts member own family lineage, `%wait`/`#fork`, claim and follow-up
policy, and history. Cross-link the two immutably, keep family-attached logs on the
artifacts lifecycle, and write terminal Proc state only after settlement is complete.

Make `sase monitor` a thin service-level facade over this path and define a monitor as a
family-attached proc shell. Do not create a top-level `sase shell` command and do not add
a shell Proc kind. Retain legacy monitor and kind readers during migration, then remove
the TUI Proc runtime, `-d|--detached`, kind filters, and ownership branches once all 53
ACE producers have either become command Procs or ordinary non-Proc workers.

Finally, replace **agent lane** in the public taxonomy with **SASE agent**, define
**agent shell**, **proc shell**, and **SASE shell** as above, and stage the deeper internal
`lane_*` rename separately from the supervisor cut-over. This gives the feature a clear
model now and leaves the future standalone proc-shell/xprompt work additive rather than
requiring another storage or terminology reversal.
