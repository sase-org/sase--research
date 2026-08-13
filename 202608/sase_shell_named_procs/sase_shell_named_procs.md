---
create_time: 2026-08-13
updated_time: 2026-08-13
status: research
---

# Named Procs and `sase shell`: merging the monitor substrate into procs

**Research question.** How should SASE merge `sase monitor` (epic `sase-kp`) into
`sase proc` (epic `sase-lh`) by adding a new kind of detached proc — a **named proc**,
a.k.a. a **sase shell** — exposed through a new `sase shell` command that replaces and
removes `sase monitor`?

**Snapshot.** Consolidated 2026-08-13 against `sase` at `ffa63b5ed` and linked
`sase-core` (schema-2 procs wire). `sase-kp`: all 12 phases closed, epic sitting on
`sase-kp.land`. `sase-lh`: phase 1 (Rust core) closed and released at
`PROC_WIRE_SCHEMA_VERSION = 2`; phases 2–8 in progress. Python still spells the package
`sase.tasks`; this note says **proc** for the concept and quotes current identifiers when
citing code.

**Related work.** Extends
[`detached_proc_convergence`](../detached_proc_convergence/detached_proc_convergence.md)
— this report answers its open decisions #1 (substrate convergence, "the
highest-leverage decision"), #7 (schema-bump timing), and #8 (sequencing) — and
[`monitor_command_substrate`](../monitor_command_substrate/monitor_command_substrate.md),
whose ranked item #15 ("extract the shared supervisor kernel *once items 1–4 have settled
the correct shape*") is now unblocked because items 1–4 landed.

**Sources.** Merges [`__a`](sase_shell_named_procs__a.md) and
[`__b`](sase_shell_named_procs__b.md) plus independent verification. Where the two
disagreed, §5 and §9 record the resolution.

---

## Bottom line

The merge is right, and both prior reports converge on the same architecture. Stated
once:

> A **named proc** is a supervised command with a stable `name`. A **sase shell** is a
> named proc, *optionally* attached to an agent lane. `sase monitor` was the
> only-ever-lane-attached case, with the attachment hard-coded as mandatory.

Five load-bearing conclusions:

1. **"Powered by `sase proc` under the hood" must mean the service layer, not the CLI,
   and not a wrapper process.** `sase shell` calls `sase.procs` functions directly.
   Spawning `sase proc run` and parsing its JSON, or running `sase shell _run` *as* a
   proc child, both break in specific ways (§6.2). This is the most important warning in
   either source report given the phrasing of the request.
2. **The supervisor is the real duplication, and the winner is already decided.**
   `sase.monitor.supervise` is strictly stronger than `sase.tasks.supervisor` on every
   axis. Promote it to the proc kernel and delete the other. `BoundedLogPipe` is
   *already* shared, so this is less work than either prior report's ancestors assumed.
3. **`name` is an identity *and* a mutual-exclusion key** — the store-wide dedup key
   `detached_proc_convergence` §3.2 called a blocking prerequisite for the TUI-proc
   migration. One field, two features: this epic *unblocks* that one rather than
   competing with it.
4. **Do not add a proc `kind`.** Namedness and lane-attachment are orthogonal nullable
   fields. `kind` already conflates ownership with attribution; a third meaning repeats
   the mistake.
5. **Keep the artifacts record for lane-attached shells** — dropping it deletes `%wait`,
   `#fork`, family roster, claim transfer, and `sase chats`. Two records, one writer, one
   ordering rule (§7). And **the shell's log must keep the artifacts lifecycle, not the
   proc-row lifecycle** (§5) — the one place where following the obvious design silently
   destroys user data.

---

## 1. The two systems today

All figures verified at `ffa63b5ed`.

| | **Procs** (`sase.tasks` → `sase.procs`) | **Monitors** (`sase.monitor`) |
| --- | --- | --- |
| Source | 8 modules, 1,390 lines | 17 modules, **3,747 lines** |
| Tests | 2 files, 781 lines | 19 files, **4,169 lines** |
| Durable record | Rust JSONL store `~/.sase/tasks/tasks.jsonl` | member `agent_meta.json` + `done.json` — **no store** |
| Command form | `argv` list, `Popen(argv)` | shell string, `Popen(cmd, shell=True)` (`supervise.py:196`) |
| Log location | global `task_logs_dir()/<id>.log` | **inside the artifacts dir** (`monitor_log_path(artifacts_dir)`) |
| Scoping | session attribution | agent lane — one active monitor per lane |
| Required at start | argv + cwd | `--reason` **and** `--timeout` |
| Timeouts | none | total + idle, checked on a 50 ms tick |
| On completion | status flip only | claim settle → follow-up agent → `done.json` → chat history → notification |
| Human-startable | yes | **no** — `resolve_lane()` (`monitor/store.py:69-81`) raises without pre-existing agent artifacts |
| External callers | 3 | 2 |

The CLI shapes are already near-isomorphic (`list` / `show` / `start`\|`run` /
`stop`\|`kill` / a suppressed supervise entry point) — itself evidence that one substrate
is being written twice. The duplication is acknowledged *in the source*:
`monitor/supervise.py:1-8` declares itself a mirror of `sase.tasks.supervisor`, and
`monitor/naming.py` copies `sase.tasks.ids`'s alphabet and length.

### 1.1 Which supervisor survives

Every row checked against both files at HEAD.

| Capability | `tasks/supervisor.py` | `monitor/supervise.py` |
| --- | --- | --- |
| Survives the caller's process-tree teardown | `start_new_session` only | **double-fork, reparented to PID 1 before `start_monitor` returns** |
| Proves liveness before the caller acts | no | **`.monitor_started` ack, polled, 20 s budget** |
| Cannot exec before the workspace claim is held | n/a | **launch barrier marker** |
| Total timeout / idle timeout | no / no | yes / yes |
| Supervisor identity | `/proc/<pid>/cmdline` match | **`process_identity()`, boot-aware** |
| Child env identity scrubbed | no | **`scrub_agent_identity_env()` + `SASE_ARTIFACTS_DIR` drop** |
| Dead-supervisor reconciliation | status flip to `error` | **kill pgid, finalize log, dispose claim, run/record follow-up; pre-boot → `lost`** |
| Request idempotency | none | full-request fingerprint under a lane lock |
| Shared bounded byte log | yes (`BoundedLogPipe`) | yes (same class) |

**There is no axis on which the proc supervisor is better. It is smaller because it does
less.** Two rows matter most for the merge:

- **Double-forking is not optional once procs are agent-startable.** A `sase proc run`
  issued inside an agent that is later torn down by a PPID-walking kill can be collected
  as collateral; the monitor added reparenting specifically to survive its own starter's
  `kill_agent_runner_group()`.
- **Identity beats pid.** `_supervisor_process_matches()` (`tasks/runner.py:299-324`)
  parses `/proc/<pid>/cmdline` and returns `True` unconditionally on any platform without
  `/proc`.

### 1.2 A correction to carry into planning

Report `__b`'s phase-2 framing ("every proc gains reparenting, ack, identity, dual
timeouts") is slightly too broad. `kind="tui"` rows are **ACE-owned mirror rows, not
supervised subprocesses** — `kill_task()` refuses them outright
(`tasks/runner.py:226-229`). The kernel change affects `command` and `detached` kinds
only. That narrows the blast radius of the riskiest phase and should be said explicitly
in the plan.

---

## 2. The conflation `sase shell` gets to undo

`sase monitor start` does five separable things:

1. spawn a detached, supervised, bounded-logged, timed command;
2. give it a durable, addressable record;
3. **make it a member of an agent lane** (family promotion, roster, runtime aggregation,
   `sase chats`, `%wait`/`#fork` visibility);
4. **transfer the starter's workspace claim to it** and settle that claim afterwards;
5. **kill the calling agent** and later launch a follow-up that inherits the starter's
   conversation, model, provider, and effort.

Items 1–2 are procs. Items 3–5 are the monitor's reason to exist. Today you cannot get
1–2 from this substrate without 3–5, and the cost is concrete:

- **A human cannot start one.** `resolve_lane()` raises `MonitorLaneError` when a lane has
  no artifacts, so `sase monitor start` from a terminal fails. Host starts work only
  because approved-epic launch *borrows the planner's lane*.
- **Epic launch carries a fallback path solely because of it.**
  `bead/epic_launch.py:120-190` tries `start_monitor(...)` and on `MonitorLaneError` falls
  back to `submit_detached_task(...)` — two execution models and two record shapes for one
  user-visible action. Under the merge this becomes one call with an optional `--lane`,
  and the fallback disappears.
- **"One monitor per lane" is a constraint about lanes, not commands.** It is right for a
  lane attachment (a lane is sequential by definition) and wrong for a named background
  command, which should be constrained by *what it is* (`name`), not *who started it*.
- **`--next` is why the lane is mandatory** — a follow-up agent needs a lane to launch
  into. But most monitors in practice (sleeps, diagnostics, epic launches) set no
  follow-up; epic launch explicitly passes `next_action=None`.

---

## 3. What "named" should mean

Both reports agree on the shape; this is the merged, tightened version.

### 3.1 Two jobs, exactly

- **Addressing.** `sase shell show deploy`, `sase proc kill nightly-docs` — no id
  prefixes, no copying hashes out of a table. This is what makes shells feel like tmux
  sessions rather than rows.
- **Mutual exclusion.** At most one **active** proc may hold a given name in a given
  project. A second start with the same name and same request is an idempotent replay
  returning the existing record; a *different* request is a visible error naming the
  running row. This is today's monitor semantics re-keyed from lane to name —
  `_monitor_request_fingerprint()` (`monitor/start.py:417-445`) already implements the
  comparison, so it is a move, not a build.

### 3.2 Scope, defaults, resolution

- **Per project, active rows only.** Host-wide is too strong (two projects legitimately
  run `check-full` at once); per-lane is the constraint we are escaping. Terminal rows keep
  their names as history, so `sase proc list --name deploy` is a run history.
- **Do not auto-derive the name from the command.** Two lanes running `just check-full`
  concurrently is normal today and would collide. Instead: `sase proc run` without
  `--name` stays **unnamed** (today's behavior, no dedup); `sase shell start` **defaults
  the name to the lane**, reproducing "one monitor per lane" exactly as a special case of
  the general rule; an explicit name is an explicit opt-in to cross-lane exclusion.
- **Resolution order, first match wins:** exact name → exact id → unique id prefix (≥3
  chars) → member agent name → lane name. **Reject names that are valid proc ids** (same
  alphabet and length) at creation, so the first two rules can never fight.
  `resolve_monitor_ref` already implements a four-tier precedence of this shape.
- **Character set:** lowercase alphanumerics, `-`, `_`, `.`, `:`; 1–64 chars; no leading
  `-`; no whitespace. Allowing `:` gives producers a free namespace
  (`plugin-install:pyright`, `patch-sync:sase-abc`) without a second field.
- **Reservation must happen under the Rust store lock.** A Python read-then-append is
  racy across two ACE instances or two agents; the store needs an atomic
  reserve-or-return-existing operation, not a check followed by `append_proc`.

---

## 4. Wire changes

Working from `ProcWire` against `MonitorRecord` (`monitor/models.py:54-91`):

| Shell needs | Where it goes |
| --- | --- |
| `command`, `cwd`, `label`, `status`, `exit_code`, `pid`, `pgid`, timestamps, `log_path`, `project`, `workspace_num`, `cl_name`, `tags` | **already on `ProcWire`** |
| shell-vs-argv execution | **no new field** — store `["/bin/sh","-c","<string>"]` as the argv |
| "settling, not yet terminal" | **`phase`, already on `ProcWire`** |
| timeout reason text | **`message`, already on `ProcWire`** |
| `name`, `artifacts_dir`, `reason`, `supervisor_identity`, `timeout_seconds`, `idle_timeout_seconds` | six new nullable fields |
| `request_fingerprint` | proc row (name-keyed idempotency is now a proc-level rule) |
| `start_status`/`stop_status`, `next_action`/`next_output`/`tail_lines`, follow-up disposition, `starter_agent`/`followup_agent` | **stay in `agent_meta.json`** — lane-only, meaningless without a lane |

Two consequences worth stating plainly:

**Compiling the shell string to `["/bin/sh","-c","<string>"]` needs no wire field and is
strictly more honest.** It shows the truth in `ps`, in the Procs pane, and in
`sase proc list`; it makes "shells run under `sh -c`" a visible property instead of a
documented footnote; it lets `sase shell` and `sase proc run` share one execution path;
and it keeps shell interpretation at the facade boundary instead of `shell=True` inside
the supervisor. `label` already exists for the pretty display string.

**The Rust `agent_scan` wire shrinks.** It carries **31 `pub monitor_*` fields**
(verified: `agent_scan/wire.rs`). Roughly half — command, cwd, state, exit code, pgid,
supervisor identity, output path, timeouts — become proc-row fields and leave the scan
wire. That is a real reduction in the Rust surface, not a relocation.

**Schema version.** `PROC_WIRE_SCHEMA_VERSION` is `2` and Python's `_require_schema()`
(`tasks/models.py:254-260`) checks **exact equality**, so even additive fields force a
coordinated Rust + Python bump. `detached_proc_convergence` open decision #7 asked whether
new fields could ride `sase-lh`'s migration: **that window has closed** — phase 1 landed
at v2. Plan a v3 bump here, and while bumping, **relax the Python check to a
minimum-known-version check** so the question never has to be asked again.

---

## 5. The retention trap (where the two reports disagreed)

This is the one substantive conflict, and it resolves in favor of `__a`'s instinct with a
cheaper fix than `__a` proposed.

`__b` states that pruning "only ever drops terminal rows … a finished shell's row can age
out while its artifacts survive — which is correct." The first half is true; the second
half is not, under `__b`'s own ownership split. Verified:

- `prune_tasks()` (`tasks/store.py:111-125`) calls **`delete_task_logs(...)` on every
  pruned id** — pruning a row **deletes its log files**.
- `apply_retention` runs **inside `append_proc`** (`procs/store.rs:99-104`), not only on
  an explicit prune. Every new proc append enforces retention.
- `DEFAULT_TASK_HISTORY_LIMIT = 100`. A busy host churns 100 terminal rows quickly.
- Today the monitor's log lives at `monitor_log_path(artifacts_dir)` — **inside the
  artifacts dir**, on the artifacts lifecycle. Proc logs live at
  `task_logs_dir()/<id>.log`, on the row lifecycle.

So the obvious design — "the proc row owns `log_path`" — would silently delete the output
behind a still-visible family member, a `sase chats` entry, and a `done.json` that points
at it. `__a` saw the hazard and proposed materializing a bounded head+tail snapshot into
the member artifacts at settlement.

**Cheaper resolution: for lane-attached shells, put `log_path` inside the artifacts dir.**
`delete_task_logs()` always recomputes `task_logs_dir()/<id>.log` from the id and ignores
the row's recorded `log_path`, so a log written into the artifacts dir is *already*
untouchable by pruning — the unlink is a no-op `FileNotFoundError`. This preserves exactly
today's monitor behavior with no duplicated bytes.

It has one prerequisite: the log module is **id-driven, not path-driven**.
`open_task_log()`, `read_task_log_tail()`, and `delete_task_logs()` all recompute from
`task_id`, while `runner.py:203` honors the stored `task.log_path`. Make the readers honor
the row's `log_path` (small, well-scoped) and both `sase proc show` and `sase shell show`
read the same bytes wherever they live.

Net rule: **the proc row is the live index; the artifacts directory is the durable
history.** `sase shell list --all` must therefore read the artifact index, not the proc
store — and unnamed/unattached procs keep today's global log location and lifecycle.

---

## 6. One supervisor, and the two ways to get "powered by `sase proc`" wrong

### 6.1 Not the CLI

Spawning `sase proc run --json` from `sase shell` and parsing the response adds
interpreter startup latency, error translation, output-ownership problems, and a fragile
CLI-to-CLI protocol. "Powered by `sase proc`" must mean **shared models, store,
supervisor, and service functions** — one Python import boundary, two CLI facades.

### 6.2 Not a wrapper process

The tempting shape is:

```text
proc supervisor -> sase shell _run -> user command
```

**Reject it.** `sase proc kill` signals the child *group*, so it kills `_run` and the user
command together — the process responsible for releasing the workspace claim and
launching or suppressing the follow-up dies before it can settle. Putting a second watcher
beside it just recreates the monitor supervisor under a new name. The proc supervisor must
own the user command **directly**.

### 6.3 What triggers shell settlement

`__a` proposes an explicit `profile="shell"` enum plus a versioned, mode-0600 request
sidecar, dispatched by a closed built-in handler. `__b` proposes that the presence of
`artifacts_dir` is the trigger.

**Take `__b`'s trigger and `__a`'s constraint.** Today the two are exactly equivalent —
every shell-settlement action (claim transfer, follow-up launch, member terminal write)
requires a lane, so `artifacts_dir is not None` *is* `profile == "shell"`, and a separate
enum buys nothing but a second thing to keep in sync. `__a`'s underlying constraint is the
part that must survive into the plan and is worth restating as a hard rule:

> The proc row must never persist an arbitrary Python import path, hook path, or
> completion command. Settlement dispatch is a closed set compiled into the supervisor.
> Anything else creates a durable code-execution contract across mixed versions.

If a second lifecycle profile ever appears with no lane, add the enum then — it is an
additive nullable field either way.

---

## 7. Two records, one writer, one ordering rule

A lane-attached shell has a proc row *and* an artifacts member. This is the only genuinely
hard part of the design and needs explicit rules, not convention.

**Ownership is split by concern, never duplicated.**

- *Proc row owns execution:* `status`, `phase`, `exit_code`, `pid`, `pgid`, `started_at`,
  `finished_at`, `log_path`, `supervisor_identity`, `name`, argv, cwd.
- *Artifacts markers own lane presentation and lineage:* custom status labels, family
  membership, `done.json` outcome, chat history, follow-up disposition, terminal snapshot.
- The cross-link is one immutable field each way (`proc.artifacts_dir`,
  `agent_meta.proc_id`), written at creation, never mutated.

**One writer.** The supervisor writes both. Nothing else mutates either after creation,
except the reconciler acting on behalf of a dead supervisor.

**One ordering rule — which also fixes a known defect:**

```text
proc.phase = "settling"
  → release/transfer the workspace claim
  → launch, degrade, or suppress the follow-up
  → write agent_meta terminal + done.json
  → proc.status = terminal
```

So **`proc.status` terminal ⇒ fully settled**, and `%wait`, `--follow`, and the ACE
indicator all watch exactly one field. Today `MonitorRecord.is_terminal` is a *two*-field
check (`monitor_state in TERMINAL_MONITOR_STATES and self.settled`, `models.py:100-102`)
precisely because the state goes terminal before settlement runs — the `settled` boolean
is a patch over the ordering. Ordering the writes correctly makes the extra field
unnecessary. `monitor_command_substrate` traced this ordering to a flaky test, and a
claim-release race is still recorded live on `sase-kp` as of 2026-08-13, so this is not a
theoretical cleanup.

**Full start-side transaction**, for completeness (from `__a`, which specified it best):

```text
reserve named proc (pending, command blocked)
  → create optional shell family member pointing at proc_id
  → spawn/reparent supervisor, wait for startup ack
  → record verified supervisor identity
  → transfer/acquire the workspace claim to that supervisor
  → release the launch barrier  →  running
```

Invariants: no user command executes before its claim is held; `start` cannot return a
live proc before the reparented supervisor acknowledges; failure before the barrier
reverses the claim to the still-live starter; a crash during `settling` is resumable and
idempotent; a pre-reboot active row becomes `supervisor_lost` and is **never** replayed.

**Kill semantics need one owner.** Today `kill_task()` signals and *immediately* writes
`status="killed"` (`runner.py:252-257`) while the supervisor also writes a terminal
result. A shell makes that race visible, because `killed` must suppress `--next` and
dispose of the claim exactly once. Correct behavior: control APIs record stop *intent*
atomically and signal the verified supervisor identity; the supervisor kills the group,
settles with reason `stop`, and writes the terminal state; if the supervisor is dead, the
reconciler does the same under the store lock. `sase proc kill` and `sase shell stop` are
then the same operation and cannot disagree.

---

## 8. CLI contract

```bash
# Named procs — the generic layer
sase proc run -n deploy -- ./deploy.sh    # named, no lane
sase proc show deploy                      # by name
sase proc kill deploy
sase proc list --name deploy               # run history for one name

# Shells — named proc + optional lane attachment + optional follow-up
sase shell start [NAME] -c 'just check-full' -r '…' -t 45m [-l LANE] [-n '…']
sase shell list   [-a] [-l LANE] [-p PROJECT] [-s STATE] [-f FORMAT]
sase shell show   <REF> [-F/--follow] [-A/--all-lines] [-o/--output-only]
sase shell attach <REF>                    # alias for `show --follow`
sase shell stop   [<REF>]
```

Checked against `sase/memory/cli_rules.md` and the live parsers:

- **`NAME` is a positional on `start`, defaulting to the lane** — not `--name`. The rule
  "every public long option gets a short alias" collides otherwise: `-n` is `--next` on
  `monitor start` and `--limit` on `task list` (both verified). A positional dodges it and
  reads better. On `sase proc run`, `-n/--name` is free and should be used.
- Keep the monitor's flags on `shell start`: required `-c/--command`, `-r/--reason`,
  `-t/--timeout`; optional `-C/--cwd`, `-i/--idle-timeout`, `-l/--lane`, `-L/--label`,
  `-n/--next`, `--next-output`, `-s/--start-status`, `-S/--stop-status`,
  `-T/--tail-lines`, `-j/--json`. Required reason/timeout is **shell-facade policy**;
  `sase proc run -n` must not inherit it.
- Bare `sase shell` delegates to `sase shell list` via the central
  `_default_list_subcommands()`; do not re-implement it per command.
- **Every shell is visible and controllable through both surfaces:** `sase proc list`
  shows a NAME indicator, `sase proc show <id-or-name>` shows the same status and bytes,
  and `sase proc kill` is exactly the operation behind `sase shell stop`. `sase shell`
  adds lane, custom status, and follow-up presentation.

### What `--lane` does

| Started from | `--lane` | Behavior |
| --- | --- | --- |
| inside an agent | defaults to the agent's lane | today's monitor: family member, claim transfer, starter killed, `--next` allowed |
| inside an agent | `--lane none` | plain named proc; **the agent is not killed** and keeps working |
| terminal / ACE / cron | omitted | plain named proc; no artifacts member; `--next` rejected with a clear error |
| terminal | `--lane <existing>` | attaches if it resolves; today's error otherwise |

Rows 2 and 3 are new capability. Row 2 in particular: an agent that wants to kick off a
background command *without* ending its own turn has no way to say so today.

### On the name `shell`

The one real objection: `sase shell` reads like "open an interactive shell"
(`docker exec -it`, `kubectl exec`), and these are explicitly non-interactive,
TTY-forbidden batch commands. Both reports flagged it independently and reached the same
mitigation, which is cheap and worth doing:

- ship **`attach`** (so a shell is something you detach from and return to — what the word
  promises); and
- have `start` **fail with an actionable message** when handed something that needs a TTY,
  rather than hanging.

With those, `shell` is a good name: accurate about `sh -c` and about the tmux-like mental
model. Without them it will generate bug reports. Documentation should define a **SASE
Shell** as *a named, non-interactive, run-to-completion proc*.

---

## 9. Alternatives

| | **A** Rename only | **B** Shared kernel, artifacts-only record | **C** Proc row + optional lane attachment | **D** Proc row only |
| --- | --- | --- | --- | --- |
| `sase monitor` removed | ✓ | ✓ | ✓ | ✓ |
| One supervisor | ✗ (two) | ✓ | ✓ | ✓ |
| Store-keyed names | index only | index only | ✓ | ✓ |
| Store-wide dedup for the TUI migration | ✗ | ✗ | ✓ | ✓ |
| One list of everything running | ✗ | ✗ | ✓ | ✓ |
| Shells in the ACE Procs pane | ✗ | ✗ | ✓ | ✓ |
| Human-startable shells | needs a fix | ✓ | ✓ | ✓ |
| Family / `#fork` / `%wait` preserved | ✓ | ✓ | ✓ | **✗** |
| Rust wire change | none | none | additive + v3 | large |
| Dual-record consistency risk | n/a | n/a | **yes, managed (§7)** | n/a |
| Size | small | medium | **medium–large** | large |

- **A** satisfies the literal request and is not a merge: two supervisors keep diverging
  and the dedup mechanism still has to be built later.
- **B** is a legitimate cheaper answer, and both reports say so. It is right **if and only
  if** one unified "what is running" list is not worth an additive wire change. Its cost:
  shells stay invisible to `sase proc list` and the Procs pane, names need a separate
  index, and the TUI-proc migration gains nothing.
- **C** is recommended.
- **D** is rejected: it deletes family roster membership, runtime aggregation,
  `sase chats`, `%wait` resolution, `#fork` conversation inheritance, and claim transfer —
  and it collapses back into C the moment family membership is re-added, because a family
  member *is* an artifacts directory. Eliminating the projection would require teaching
  every agent-artifact query, roster, wait resolver, chat lookup, mobile summary, and
  runtime aggregator to join the global proc store — a much larger migration with no user
  benefit.

A systemd/transient-unit backend was also considered and is not portable to macOS;
possible later as an optional backend only.

---

## 10. Sequencing

**Start after `sase-lh` closes.** Every module this touches is being renamed by phases 2–8
right now; starting earlier means rebasing through the rename. This matches
`detached_proc_convergence` §8 and both source reports. Do not fold behavioral change into
the terminology epic.

| Phase | Work | Size |
| --- | --- | --- |
| 0 | Decide §12. Nothing starts until the record model is chosen. | — |
| 1 | Rust: six additive `ProcWire` fields, schema v3, **atomic reserve-or-return** under the store lock, min-version check in Python. | medium |
| 2 | Kernel: promote `monitor/supervise.py` + `supervisor_bootstrap.py` to the proc kernel; retarget config reads from `agent_meta.json` to the proc row and state writes to `update_proc(...)`; delete `tasks/supervisor.py`. **Ship alone and let it soak** — it changes execution for `command`/`detached` procs (not `tui`). | large |
| 3 | Named procs: `name`, per-project active uniqueness, fingerprint replay, `sase proc run -n`, resolution order. | medium |
| 4 | Attachment: move `member`/`claims`/`followup*`/`settlement`/`transaction` (~1,100 lines, with 4,169 lines of tests) behind an `artifacts_dir`-conditional path; implement §7's ordering; make the log module path-driven and place lane-attached logs in the artifacts dir (§5). | medium |
| 5 | `sase shell` CLI + `attach` + TTY refusal; `sase monitor` becomes the erroring alias. | medium |
| 6 | Collapse epic launch's monitor/detached-task fork into one call. | small |
| 7 | ACE: shells in the Procs pane; keep the Agents-tab row rendering, re-keyed on the proc row. | medium |
| 8 | Docs (`monitors.md` → `shells.md`, `cli.md`, `ace.md`, `sdd.md`), memory, glossary entry, `/sase_shell` skill, `sase memory init`. | medium |
| 9 | Delete `sase monitor`; land. | small |

Phase 2 carries the risk and delivers most of the value; land it and live with it before
3–5 build on top.

**Follow-on, not in this epic:** migrating ACE's ~54 attached callable proc producers to
command-backed procs (`detached_proc_convergence`). The schema-3 dedup, settlement, and
completion machinery built here are its prerequisites, but converting those call sites is
separate work.

---

## 11. Compatibility

- **In-flight monitors must settle across the cut-over.** This is the one non-negotiable
  requirement and the highest-probability real-world break. Never try to adopt a live
  monitor's process group into a new proc record — the recorded pid, claim, barrier, and
  settlement ownership cannot be transferred after the fact. Let already-running
  supervisors finish under the code they loaded, and keep the reconciler able to settle a
  member with no proc row.
- **Legacy `monitor_*` fields stay readable indefinitely** (serde aliases in Rust, as
  `sase-lh` already did for `task_id`). Historical families, chats, and done markers are
  immutable evidence, not migration input. `sase shell list/show/stop` should recognize
  legacy monitor artifacts during the compatibility window so an upgrade does not strand
  them.
- **`sase monitor` should be a one-release hidden alias that errors with a pointer**, not
  a silent removal — agents carry the old invocation in memory files and chat history.
  `sase-lh`'s own decision to keep `task` as a legacy CLI alias is the local precedent.
- **`/sase_monitor` → `/sase_shell`** goes through the skills manifest
  (`sase/memory/generated_skills.md`), not a file delete.
- **`sase/memory/build_and_run.md` instructs every agent to run `just check-full` through
  `/sase_monitor`.** It must change in the same commit as the skill, or agents will follow
  a memory pointing at a deleted command.
- **Internal outcome spelling.** Prefer a neutral `proc` / `proc_handoff` vocabulary for
  the member and starter markers over continuing to emit `outcome="monitored"`, with
  `agent_family_role="shell"` controlling presentation. Choose once, apply everywhere.

Blast radius, measured: 69 files under `src/` match monitor-specific identifiers or
imports; 191 files across `src/`, `tests/`, `docs/`, and `sase/memory/` mention monitor at
all.

---

## 12. Decisions needed before planning

1. **B or C** — is one unified "what is running" list worth an additive Rust wire change
   plus the dual-record rule in §7? *This is the whole decision; everything else follows.*
   Recommended: **C**.
2. **Name uniqueness scope** — per project (recommended) or host-wide?
3. **`--next` without a lane** — hard error (recommended), or may a host-started shell
   *create* a fresh lane for its follow-up? The latter is a genuinely useful new capability
   (scheduled agent kickoff) and genuine scope creep.
4. **Does `sase proc run` inherit the heavier kernel unconditionally?** Recommended yes,
   for uniformity; the cost is one extra fork and a sub-second bounded ack poll.
5. **The 31 `monitor_*` scan-wire fields** — rename to `shell_*` or keep with serde
   aliases? Recommended: rename only the ~15 that survive on the artifacts side, with
   aliases, in phase 8 — not phase 1.
6. **`sase monitor` alias window** — one release (recommended) or a hard cut at phase 9?
7. **Shell executable** — keep `/bin/sh -c` semantics initially; add an explicit shell
   selector only on concrete demand.

None of these changes the architecture.

---

## 13. Risks

1. **Dual-record divergence** for lane-attached shells. Mitigated by §7's single-writer +
   ordering rule, and it must be tested directly: kill the supervisor between each pair of
   steps and assert both records agree afterwards.
2. **Log destruction on prune** (§5) if `log_path` for lane-attached shells is left in the
   global proc log dir. Silent, data-losing, and easy to miss in review.
3. **Phase 2 changes execution for existing `command`/`detached` procs.** Every
   `sase task run`, epic launch, and bead-work launch starts going through a different
   supervisor. Land it alone behind the full `just check-full` lane and keep the old module
   importable for one release to make bisecting cheap.
4. **A name is a lock.** Per-project active uniqueness means a wedged shell blocks the next
   start under that name. `sase shell stop` and the reconciler must be reliable enough to
   clear it, and the collision error must name the blocking row and the exact command to
   inspect it — as `_active_monitor_message()` already does.
5. **The `sase-kp` hardening must not be lost in the move.** The launch barrier, start ack,
   identity check, claim-undo path, and reconciliation ordering were each written against a
   specific reproduced failure. Make the move mechanical and **migrate `tests/monitor/`
   rather than rewriting it** — those 4,169 lines are the record of what the defects were.
   Note that a claim-release flake is still recorded live on `sase-kp` as of 2026-08-13;
   confirm it is cleared *before* the move, so a pre-existing race is not mistaken for a
   migration regression.
6. **Schema v3 across mixed versions.** The min-version relaxation makes new-reads-old
   safe; old-reads-new relies on the Rust side tolerating unknown fields (it does, via
   `serde`).
7. **Naming confusion.** `shell` implying interactivity (§8); and SASE will briefly have
   had four names — task, proc, monitor, shell — for adjacent concepts within one month.
   The glossary entry is not optional.

---

## 14. Verification

Beyond `just check-full` plus the PNG snapshot suite (this crosses the Rust wire and
store, CLI parsers, ACE navigation, the Procs pane, the Agents tab, and agent-family
lifecycle), the following cases are the ones that distinguish a correct implementation:

**Identity and concurrency** — simultaneous identical starts on one `(project, name)`
yield exactly one execution and both callers resolve it; a differing fingerprint on the
same active name produces one start and one visible conflict; the same name in different
projects both run; terminal-name reuse yields a new id while the name resolves to the
newest; a name that looks like a proc id is rejected at creation.

**Process ownership** — the starter kills itself immediately after start and the proc
survives; the bootstrap dies before ack and the command never starts, with the claim
returned to the starter; a claim transfer failure leaves the launch barrier closed; a
stale or recycled supervisor pid is never signaled; a pre-reboot active row becomes lost
and is never replayed.

**Output and timeout** — output continuing past the total timeout; a partial line with no
newline; invalid UTF-8; stdout closed while the process lives; a background grandchild
holding stdout; idle timeout versus an intentionally quiet command; a TERM-ignoring tree
requiring KILL escalation; rotation while both `proc show --follow` and
`shell show --follow` read.

**Settlement and retention** — stop through *either* CLI suppresses `--next` and disposes
the claim exactly once; a crash at each `settling` step resumes without a duplicate
follow-up or double claim release; `%wait` does not advance before settlement completes;
**and a lane-attached shell's output is still readable after 100+ newer procs have been
appended** (the §5 regression test).

**Surfaces** — the same id, name, status, and bytes appear in `sase proc`, `sase shell`,
the Procs pane, and the linked Agents row; approved epic launch uses one call with no
detached-task fallback; no new runtime path imports `sase.monitor` or writes `monitor_*`
data; legacy monitor records remain readable and stoppable during the window.

---

## Recommended solution

Adopt **Option C**. Concretely:

1. **Model namedness as an optional immutable `name` on the ordinary detached Proc
   record — not a fourth `kind`.** Add six additive nullable `ProcWire` fields (`name`,
   `artifacts_dir`, `reason`, `supervisor_identity`, `timeout_seconds`,
   `idle_timeout_seconds`), bump to schema v3, add an **atomic reserve-or-return**
   operation under the Rust store lock, and relax Python's exact-equality schema check to
   a minimum-version check.
2. **Promote the monitor supervisor to the proc kernel and delete
   `tasks/supervisor.py`.** Double-fork bootstrap, start ack, launch barrier, process
   identity, dual timeouts, env scrubbing, and full reconciliation become properties of
   *every* supervised proc. Ship this phase alone and let it soak.
3. **Make `sase shell` a direct service-level facade over `sase.procs`** — not a CLI
   wrapper, and not a wrapper process between the supervisor and the user command.
   Compile `-c '…'` to `["/bin/sh","-c","…"]` and persist that argv.
4. **Keep a thin lane attachment for agent-started shells**, triggered by
   `artifacts_dir`, owning only lane lineage, custom status labels, claim policy,
   follow-up policy, and the terminal history snapshot — with settlement dispatch a closed
   set compiled into the supervisor, never a persisted code path. Execution and control
   live exclusively in the proc store.
5. **Enforce one writer and one ordering rule** so `proc.status` terminal ⇒ fully settled,
   which retires the `settled` boolean and fixes the known claim-release race.
6. **Keep lane-attached shell logs inside the artifacts dir** and make the log module
   path-driven, so proc retention can never delete output a family member still points at.
7. **Sequence after `sase-lh` closes**, then remove the public `sase monitor` command
   behind a one-release erroring alias, migrating `/sase_monitor` → `/sase_shell` and
   `sase/memory/build_and_run.md` in the same commit as the skill.

The single decision that gates everything is #1 in §12: whether one unified "what is
running" list justifies the wire change and the dual-record rule. If the answer is no,
Option B — shared kernel, artifacts-only record — is a legitimately cheaper answer that
still deletes the duplicate supervisor and still gives you `sase shell`.
