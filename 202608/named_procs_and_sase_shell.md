---
create_time: 2026-08-13
updated_time: 2026-08-13
status: research
---

# Named Procs and `sase shell`: merging monitors into the proc substrate

**Research question.** How should SASE merge `sase monitor` (epic `sase-kp`) into `sase
proc` (epic `sase-lh`) by introducing a new kind of detached proc — a **named proc**,
a.k.a. a **sase shell** — exposed through a new `sase shell` command that replaces and
removes `sase monitor`?

**Scope and snapshot.** Verified against the `sase` repo at `d9c685e86` (master, clean
tree) and `../sase-core` at `5b8ba44` on 2026-08-13. Both epics are live: every
`sase-kp` phase is closed with the epic in its land step; `sase-lh` phase 1 (Rust core)
is closed and phases 2–8 are in progress. This note says **proc** for the durable
background-execution unit and quotes current identifiers (`sase task`, `sase.tasks`,
`BackgroundTask`) when citing Python code that `sase-lh` has not renamed yet.

**Related work.** This extends
[`detached_proc_convergence`](detached_proc_convergence/detached_proc_convergence.md),
whose §5 raised exactly this question and deferred it as "the highest-leverage decision"
(its open decision #1), and
[`monitor_command_substrate`](monitor_command_substrate/monitor_command_substrate.md),
whose ranked item #15 was "extract the shared supervisor kernel between `tasks` and
`monitor` *once items 1-4 have settled the correct shape*." **Items 1–4 have since
landed** — the shape is settled, so the extraction is now well-founded rather than
speculative. Both prior reports predate the hardening work; several defects they treat
as open are fixed at this HEAD, and the recommendation below depends on that.

---

## Bottom line

Merge, but do not merge the two things the word "monitor" currently fuses.

A monitor is **a supervised named command** *and* **an agent-lane attachment**, welded
into one object. The first is generic infrastructure that duplicates procs. The second
is the genuinely valuable, genuinely monitor-specific part — family membership,
workspace-claim transfer, the `#fork` follow-up agent — and it is why the merge cannot
simply be "delete `sase.monitor`, call `sase proc run`".

`sase shell` is the right lever precisely because it lets you split them:

- **A named proc** is a proc with a `name`. Nothing else. It needs no lane, so — unlike
  a monitor today — **a human can start one from a plain shell**, ACE can start one, and
  cron can start one. `resolve_lane()` (`src/sase/monitor/store.py:69-81`) raises unless
  the lane already has agent artifacts, which is the reason `sase monitor start` is
  effectively agent-only today.
- **Lane attachment is an optional flag on a named proc**, not a precondition for
  existing. `--lane` (implicit inside an agent) turns a named proc into today's monitor;
  omitting it gives you the thing SASE currently has no way to express.

Four things follow, and they are the substance of this report:

1. **The supervisor is the real duplication, and the winner is already decided.**
   `sase.monitor.supervise` is a strictly stronger implementation than
   `sase.tasks.supervisor` on every axis that has ever caused an incident. Keep it, point
   it at the proc store, delete the other. The bounded-log layer is *already* shared
   (`sase.logs.pipe.BoundedLogPipe`), so this is less work than it looks.
2. **`name` should be the store-wide dedup key** that `detached_proc_convergence` §3.2
   named as a blocking prerequisite for the TUI-proc migration. One field buys both
   features. This work therefore *unblocks* that epic instead of competing with it.
3. **Do not add a proc `kind`.** Named-ness and lane-attachment are two independent
   nullable fields (`name`, `artifacts_dir`). `kind` already wrongly conflates ownership
   with attribution; adding a third meaning to it repeats the mistake the sibling
   research diagnosed.
4. **Keep the agent-artifact record for lane-attached shells.** It is not redundant with
   the proc row — it is what makes a shell a family member. Two records, one writer, one
   ordering rule (§6.2). This is the only genuinely hard part of the design.

Recommended architecture is **Option C** in §5, detailed in §6.

---

## 1. What the two systems are today

### 1.1 Side by side

| | **Procs** (`sase.tasks` → `sase.procs`) | **Monitors** (`sase.monitor`) |
| --- | --- | --- |
| Source size | 8 modules, 1,390 lines | 17 modules, **3,747 lines** |
| Test size | 2 files, 781 lines | 19 files, **4,169 lines** |
| Durable record | Rust JSONL store, `~/.sase/tasks/tasks.jsonl` | the member's `agent_meta.json` + `done.json` — **no store** |
| Identity | random id, unique ≥3-char prefix | monitor id, member agent name, **or lane name** |
| Command form | `argv` list, `Popen(argv)` | shell string, `Popen(cmd, shell=True)` |
| Supervisor | `python -m sase.tasks.supervisor --task-id X` | `sase.monitor.supervisor_bootstrap` → double-fork → `run_supervisor` |
| Scoping | session attribution (`--session`, `--detached`) | agent lane (**one active monitor per lane**) |
| Required at start | nothing but argv + cwd | `--reason` **and** `--timeout` |
| Timeouts | none | total + `--idle-timeout`, checked every 50 ms tick |
| On completion | status flip only | claim settle → follow-up agent → `done.json` → chat history → notification |
| Startable by a human | yes | **no** — `resolve_lane()` needs existing agent artifacts |
| Surface | ACE Procs pane, `sase task list/show/run/kill` | ACE Agents tab (family member), `sase monitor list/show/start/stop` |
| External callers | 3 (`bead/task_launch.py`, `bead/epic_launch.py`, `main/task_handler.py`) | 2 (`bead/epic_launch.py`, `main/monitor_handler.py`) |

The CLI shapes are already near-isomorphic — `list` / `show` / `start`\|`run` /
`stop`\|`kill` / a `SUPPRESS`'d supervise entry point — which is itself evidence that one
substrate is being written twice.

### 1.2 What is already shared

More than the prior research assumed, because the `sase-kp` hardening landed:

- **`BoundedLogPipe`** (`src/sase/logs/pipe.py`) is imported by both
  `sase/tasks/logs.py:16` and `sase/monitor/supervise.py:30`. The log transport, byte
  cap, rotation, and drain thread are one implementation already. This was the single
  biggest item on `monitor_command_substrate`'s ranked list and it is done.
- **`sase.logs._bounded`** (`log_file_lock`, `append_bytes_locked`) backs both.
- **Naming and id primitives** were deliberately mirrored: `sase/monitor/naming.py`
  copies `sase.tasks.ids`'s alphabet and length; `sase/monitor/store.py` mirrors
  `MIN_TASK_REF_LENGTH`. The module docstrings say so in the source.
- **`sase/monitor/supervise.py:1-8`** opens by declaring itself a mirror of
  `sase.tasks.supervisor`.

The duplication is therefore *acknowledged in the code* and already half-resolved. What
remains unshared is the process lifecycle and the record layer.

### 1.3 Where the supervisors actually differ

This determines which one survives. Every row was checked against both files at HEAD.

| Capability | `tasks/supervisor.py` | `monitor/supervise.py` |
| --- | --- | --- |
| Survives a caller's process-tree teardown | `start_new_session` only | **double-fork bootstrap, reparented to PID 1 before `start_monitor` returns** |
| Proves it is alive before the caller acts on it | no | **`.monitor_started` ack, polled with liveness, 20 s budget** |
| Cannot exec before the workspace claim is held | n/a | **launch barrier marker** |
| Total timeout | no | yes, evaluated every tick |
| Idle (no-output) timeout | no | yes |
| TERM→KILL escalation | yes | yes |
| `SIGHUP` ignored, handlers installed pre-import | no | yes |
| Guaranteed terminal marker on internal failure | `try/except BaseException/finally` | `try/except BaseException/finally` |
| Records child pgid | yes (`pgid=child.pid`) | yes (`monitor_pgid`) |
| Stronger-than-pid supervisor identity | `/proc/<pid>/cmdline` match | **`process_identity()`, boot-aware** |
| Child env identity scrubbed | no | **`scrub_agent_identity_env()` + `SASE_ARTIFACTS_DIR` drop** |
| Reconciliation of a dead supervisor | status flip to `error` | **kill pgid, finalize log, dispose claim, run/record follow-up; pre-boot → `lost`** |

There is no axis on which the proc supervisor is better. It is smaller because it does
less. **The merged kernel should be the monitor's, retargeted at the proc store.**

Two of those rows matter more than the rest for the merge:

- **The double-fork bootstrap is not optional once procs are agent-startable.** A
  `sase proc run` issued from inside an agent that is later torn down by a PPID-walking
  kill can be collected as collateral; the monitor added reparenting specifically to
  survive its own starter's `kill_agent_runner_group()`.
- **Identity beats pid.** `_supervisor_process_matches()`
  (`tasks/runner.py:299-324`) parses `/proc/<pid>/cmdline` and returns `True`
  unconditionally on any platform without `/proc`. `process_identity()` is the stronger
  primitive and should become the proc store's too.

---

## 2. The conflation `sase shell` gets to undo

`sase monitor start` does five separable things:

1. spawn a detached, supervised, bounded-logged, timed command;
2. give it a durable, addressable record;
3. **make it a member of an agent lane** (family promotion, artifacts dir, roster,
   runtime aggregation, `sase chats`, `%wait`/`#fork` visibility);
4. **transfer the starter's workspace claim to it** and settle that claim afterwards;
5. **kill the calling agent** and later launch a follow-up agent that inherits the
   starter's conversation, model, provider, and effort.

Items 1–2 are procs. Items 3–5 are the monitor's reason to exist. Today you cannot have
1–2 from this substrate without 3–5, and the costs of that fusion are concrete:

- **A human cannot start one.** `resolve_lane()` raises `MonitorLaneError` when a lane
  has no artifacts, so `sase monitor start --lane whatever` from a terminal fails. Host
  starts work only because epic launch *borrows the planner's lane*
  (`bead/epic_launch.py:145-165`).
- **Epic launch carries a whole fallback path because of it.**
  `bead/epic_launch.py:120-190` tries `start_monitor(...)` and, on `MonitorLaneError`,
  falls back to `submit_detached_task(...)` — two execution models, two record shapes,
  and two sets of downstream behavior for one user-visible action. Under the merge this
  becomes one call with an optional `--lane`, and the fallback disappears.
- **"One monitor per lane" is a constraint about lanes, not about commands.** It is the
  right rule for a lane attachment (a lane is sequential by definition) and the wrong
  rule for a named background command, which should be constrained by *what it is*
  (`name`), not by *who started it*.
- **`--next` is why the lane is mandatory,** since a follow-up agent needs a lane to be
  launched into. But most monitors in practice — sleeps, diagnostics collection, epic
  launches — set no follow-up at all. Epic launch explicitly passes `next_action=None`.

The clean statement of the merge is therefore:

> A **named proc** is a supervised command with a stable name. A **sase shell** is a
> named proc, optionally attached to an agent lane. `sase monitor` was the only-ever
> lane-attached case, with the attachment hard-coded as mandatory.

---

## 3. What "named" should mean

This is the part of the design most likely to be got wrong cheaply and regretted, so it
deserves precision.

### 3.1 A name is an identity *and* a mutual-exclusion key

Give `name` one job too few and it is cosmetic; give it one too many and it becomes a
generic label. The right pair:

- **Addressing.** `sase shell show deploy`, `sase proc kill nightly-docs` — no id
  prefixes, no copying hashes out of a table. This is what makes "sase shells" feel like
  tmux sessions rather than rows.
- **Mutual exclusion.** At most one **active** proc may hold a given name in a given
  project. A second start with the same name and the same request is an idempotent
  replay that returns the existing record; with a *different* request it is an error
  naming the running one. This is exactly today's monitor semantics, re-keyed from lane
  to name — `_monitor_request_fingerprint()` (`monitor/start.py:417-445`) already
  implements the fingerprint comparison, so the logic is a move, not a build.

That second job is the one `detached_proc_convergence` §3.2 called a blocking
prerequisite for migrating TUI procs: *"Store-wide dedup is required before globalizing
producers, or two ACE instances race the same Patch mutation or package update."* The
name **is** that dedup key. `plugin-install:pyright`, `comprehensive-update`,
`bgcmd-slot-3` are all natural names.

### 3.2 Uniqueness scope: per project, among active rows only

Host-wide is too strong (two projects legitimately run `check-full` at once); per-lane is
too weak (it is the constraint we are trying to escape). **Per project, active rows
only.** Terminal rows keep their names as history, so `sase proc list --name deploy` is a
run history and `sase proc show deploy` is the newest run.

### 3.3 Do not auto-derive the name from the command

This is the trap. Today, two agents in different lanes running `just check-full`
concurrently is normal and correct. If the default name were derived from the command
they would collide and the second would be rejected. Therefore:

- `sase proc run` without `--name` creates an **unnamed** proc (today's behavior,
  unchanged, no dedup).
- `sase shell start` **defaults the name to the lane name** when attaching to a lane.
  That reproduces "one monitor per lane" exactly, as a special case of the general rule,
  with no new failure mode.
- An explicit name is an explicit opt-in to cross-lane mutual exclusion.

### 3.4 Reference resolution order

Introducing names into a namespace that already resolves id prefixes creates ambiguity.
Resolve in strict precedence, first match wins: **exact name → exact id → unique id
prefix (≥3 chars) → member agent name → lane name.** Reject names that are valid proc
ids (same alphabet and length) at creation time so the first two rules can never fight.
`sase/monitor/store.py`'s `resolve_monitor_ref` already implements a four-tier precedence
of this shape and is the model to follow.

### 3.5 Character set

Lowercase alphanumerics, `-`, `_`, `.`, `:`; 1–64 chars; no leading `-`; no whitespace.
`:` is worth allowing because it gives producers a natural namespace
(`plugin-install:pyright`, `patch-sync:sase-abc`) without inventing a second field.

---

## 4. What a shell needs that a proc row lacks

Working from `ProcWire` (`sase-core/crates/sase_core/src/procs/wire.rs`) against
`MonitorRecord` (`src/sase/monitor/models.py:54-91`):

| Shell needs | Where it goes |
| --- | --- |
| `command`, `cwd`, `label`, `status`, `exit_code`, `pid`, `pgid`, `created/started/finished_at`, `log_path`, `project`, `workspace_num`, `cl_name`, `tags` | **already on `ProcWire`** |
| shell-vs-argv execution | **no new field** — store `["/bin/sh","-c","<string>"]` as the argv (see below) |
| "settling, not yet terminal" | **`phase`, already on `ProcWire`** |
| timeout reason text | **`message`, already on `ProcWire`** |
| `name` | new nullable `String` |
| `artifacts_dir` (lane attachment link) | new nullable `String` |
| `reason` | new nullable `String` |
| `supervisor_identity` | new nullable `String` |
| `timeout_seconds`, `idle_timeout_seconds` | new nullable numerics |
| `start_status` / `stop_status` labels | **stay in `agent_meta.json`** — they are agent status labels, meaningless without a lane |
| `next_action`, `next_output`, `tail_lines`, follow-up disposition (4 fields) | **stay in `agent_meta.json`** — lane-only |
| `starter_agent`, `followup_agent` | **stay in `agent_meta.json`** — lane lineage |
| `request_fingerprint` | either; prefer the proc row, since name-keyed idempotency is now a proc-level rule |

Two consequences worth stating plainly:

**Representing a shell command as `["/bin/sh","-c","<string>"]` needs no wire change and
is strictly more honest.** It shows the truth in `ps`, in the Procs pane, and in
`sase proc list`; it makes "shells run under `sh -c`" a visible property instead of a
documented footnote; and it lets `sase shell` and `sase proc run` share one execution
path. `label` already exists for the pretty display string.

**The Rust `agent_scan` wire shrinks.** It currently carries **31 `pub monitor_*`
fields** across the meta and done structs. Under this design roughly half of them —
command, cwd, state, exit code, pgid, supervisor identity, output path, timeouts —
become proc-row fields and leave the scan wire. That is a real reduction in the Rust
surface, not merely a relocation.

**Schema version.** `PROC_WIRE_SCHEMA_VERSION` is `2`; Python's `_require_schema()`
(`tasks/models.py:254-260`) checks **exact equality**, so even additive fields force a
coordinated Rust + Python bump. `detached_proc_convergence` open decision #7 asked
whether new fields could ride `sase-lh`'s migration: **that window has closed** — the
core phase landed at v2 on `c69a2f8`. Plan a v3 bump here, and while bumping, relax the
Python check to "≥ minimum known version" so this question never has to be asked again.

---

## 5. Four architectures

| | **A** Rename only | **B** Shared kernel, artifacts-only record | **C** Proc row + optional lane attachment | **D** Proc row only |
| --- | --- | --- | --- | --- |
| `sase monitor` removed | ✓ | ✓ | ✓ | ✓ |
| One supervisor | ✗ (two) | ✓ | ✓ | ✓ |
| Named procs | index only | index only | ✓ store-keyed | ✓ store-keyed |
| Store-wide dedup for the TUI migration | ✗ | ✗ | ✓ | ✓ |
| One list of everything running | ✗ | ✗ | ✓ | ✓ |
| Shells in the ACE Procs pane | ✗ | ✗ | ✓ | ✓ |
| Human-startable shells | needs a fix | ✓ | ✓ | ✓ |
| Family membership / `#fork` / `%wait` preserved | ✓ | ✓ | ✓ | **✗** |
| Rust wire change | none | none | additive + v3 | large |
| Dual-record consistency risk | n/a | n/a | **yes, managed** | n/a |
| Rough size | small | medium | **medium–large** | large |

**A — rename only.** Rename the command, add a name index, leave both engines. Cheapest,
and it does satisfy the literal request. It is not a merge: two supervisors keep
diverging, `sase proc list` still cannot answer "what is running on this host", and the
dedup mechanism the TUI-proc migration needs still has to be built later.

**B — shared kernel, artifacts-only record.** Extract the supervision kernel; keep
shells recorded solely in agent artifacts. No Rust change, no dual write, no pruning
question. But shells stay invisible to `sase proc list` and the Procs pane, names need a
separate index, and the TUI-proc migration gains nothing. B is the right answer *if and
only if* one unified list is not worth a Rust wire change.

**C — proc row primary, lane attachment optional. Recommended.** Every supervised
command is a proc row. `name` and `artifacts_dir` are independent nullable fields. A
lane-attached shell additionally owns an artifacts member, written by the same
supervisor under a strict ordering rule.

**D — proc row only.** Drop the artifacts member. Rejected: it deletes family roster
membership, runtime aggregation, `sase chats`, `%wait` resolution, `#fork` conversation
inheritance for the follow-up, and the workspace-claim transfer — all of which read the
agent artifact index, and all of which the `sase-kp` research called the epic's best
work. D also collapses into C the moment you re-add family membership, because a family
member *is* an artifacts directory.

---

## 6. Recommended solution

### 6.1 The layering

```
┌─ sase shell start [NAME] -c '…' -r '…' -t 45m [--lane L] [--next '…']
│    named proc + optional lane attachment + optional follow-up agent
├─ sase proc run [-n NAME] -- argv…
│    named or anonymous proc, no lane
└─ sase.procs kernel
     one supervisor (the monitor's), one Rust store, one bounded log,
     one reconciler, one identity check
```

Four concrete moves:

1. **Promote `sase/monitor/supervise.py` + `supervisor_bootstrap.py` to the proc
   kernel.** Retarget config reads from `agent_meta.json` to the proc row; retarget state
   writes from meta fields to `update_proc(...)`. Delete `sase/tasks/supervisor.py`.
   Everything in §1.3's right-hand column becomes true for *every* proc — including the
   `sase proc run` a user types in a terminal.
2. **Add the six additive fields from §4 to `ProcWire`**, bump to schema v3, relax the
   Python equality check to a minimum-version check.
3. **Move the lane-specific machinery into an attachment module** —
   `member.py`, `claims.py`, `followup*.py`, `settlement.py`, `transaction.py` — invoked
   by the kernel only when `artifacts_dir` is set. This is a move, not a rewrite: those
   modules total ~1,100 lines and already have 4,169 lines of tests behind them.
4. **`sase shell` is a thin CLI over `sase proc` plus the attachment**, exactly as
   requested. `sase monitor` and `src/sase/main/{parser_monitor,monitor_handler,
   monitor_render}.py` are deleted.

### 6.2 The one hard part: two records, one writer, one ordering rule

A lane-attached shell has a proc row *and* an artifacts member. That is a consistency
hazard and must be governed by explicit rules rather than convention:

- **Ownership is split by concern, not duplicated.**
  - *Proc row owns execution:* `status`, `phase`, `exit_code`, `pid`, `pgid`,
    `started_at`, `finished_at`, `log_path`, `supervisor_identity`.
  - *Artifacts markers own lane presentation and lineage:* status label, family
    membership, `done.json` outcome, chat history, follow-up disposition.
  - Nothing meaningful is written to both. The cross-link is one immutable field each
    way (`proc.artifacts_dir`, `agent_meta.proc_id`), written at creation, never mutated.
- **One writer.** The supervisor writes both. No other process mutates either after
  creation, except the reconciler acting on behalf of a dead supervisor.
- **One ordering rule, which also fixes a known monitor defect.** At settlement:

  ```
  proc.phase = "settling"          →  release/transfer claim
                                   →  launch or dispose the follow-up
                                   →  write agent_meta terminal + done.json
                                   →  proc.status = terminal
  ```

  So **`proc.status` terminal ⇒ fully settled**, and `%wait`, `--follow`, and the
  ACE indicator can all watch exactly one field. Today `agent_meta.monitor_state` still
  goes terminal *before* settlement runs (`monitor/supervise.py:379-433`), and the
  `monitor_settled` boolean plus `MonitorRecord.is_terminal`'s two-field check are the
  fix for that — `monitor_command_substrate` traced the ordering to a flaky test recorded
  in `sase-kp.6`. Ordering the write correctly makes the extra field unnecessary.
- **Pruning is safe and must be documented.** `prune_procs`
  (`sase-core/.../procs/store.rs:275-296`) only ever drops **terminal** rows beyond
  `history_limit` (default 100), so a running shell can never be pruned. A *finished*
  shell's row can age out while its artifacts survive — which is correct and worth
  stating: the proc row is the live index, the artifacts directory is the durable
  history. `sase shell list --all` must therefore read the artifact index, not the proc
  store.

### 6.3 CLI surface

```bash
# Named procs — the generic layer
sase proc run -n deploy -- ./deploy.sh          # named, no lane
sase proc show deploy                            # by name
sase proc kill deploy
sase proc list --name deploy                     # run history for one name

# Shells — named proc + lane attachment + follow-up
sase shell start [NAME] -c 'just check-full' -r '…' -t 45m -n '…'
sase shell list   [-a] [-l LANE] [-p PROJECT] [-s STATE] [-f FORMAT]
sase shell show   <REF> [-F/--follow] [-A/--all-lines] [-o/--output-only]
sase shell attach <REF>                          # alias for `show --follow`
sase shell stop   [<REF>]
```

Notes on the surface, against `sase/memory/cli_rules.md`:

- **`NAME` is a positional on `start`, defaulting to the lane**, not a `--name` flag.
  Rule "every public long option gets a short alias" collides otherwise: `-n` is already
  `--next` on monitor `start` and `--limit` on `list`. A positional dodges the collision
  and reads better (`sase shell start deploy -c './deploy.sh'`). On `sase proc run`,
  `-n/--name` is free and should be used.
- `sase shell` bare delegates to `sase shell list` via the central
  `_default_list_subcommands()` mechanism; do not re-implement it.
- **`attach` is worth adding even though it is an alias.** It makes the "shell" metaphor
  pay off, and it is the verb a user reaches for after `sase shell list`. It is
  `sase proc run --wait`'s streaming path applied to an existing row.

**On the name `shell`.** The one real objection: `sase shell` reads like "open an
interactive shell here" (`docker exec -it`, `kubectl exec`), and these are explicitly
*non*-interactive, TTY-forbidden batch commands. Two cheap mitigations make the name
honest rather than misleading: ship `attach` (so a shell is something you can detach from
and return to, which is what the word promises), and have `start` fail with an
actionable message when handed something that requires a TTY rather than hanging. With
those, `shell` is a good name — it is accurate about `sh -c` and about the tmux-like
mental model. Without them it will generate bug reports.

### 6.4 What `--lane` does, and what happens without it

| Started from | `--lane` | Behavior |
| --- | --- | --- |
| inside an agent | defaults to the agent's lane | today's monitor: family member, claim transfer, starter killed, `--next` allowed |
| inside an agent | `--lane none` | plain named proc; **the agent is not killed** and keeps working |
| a terminal / ACE / cron | omitted | plain named proc; no artifacts member; `--next` rejected with a clear error |
| a terminal | `--lane <existing>` | attaches to that lane if it resolves; today's error otherwise |

The third row is the new capability. `--lane none` in the second row is also new and
useful: an agent that wants to kick off a background command *without* ending its own
turn currently has no way to say so.

### 6.5 Compatibility

- **In-flight monitors must settle across the cut-over.** The reader path must keep
  understanding legacy `monitor_*` `agent_meta.json` fields indefinitely (serde aliases
  in Rust, as `sase-lh` already did for `task_id`), and the reconciler must be able to
  settle a member that has no proc row. This is the one non-negotiable compatibility
  requirement; everything else can be a hard cut.
- **`sase monitor` should be a one-release hidden alias that errors with a pointer**
  (`"sase monitor was replaced by sase shell; see sase shell start --help"`), not a
  silent removal — agents carry the old invocation in memory files and chat history.
- **`/sase_monitor` becomes `/sase_shell`.** The skill is generated and deployed to
  managed locations, so removing the old one goes through the skills manifest
  (`sase/memory/generated_skills.md`), not a file delete.
- **`sase/memory/build_and_run.md:39-41`** instructs every agent to run `just check-full`
  through `/sase_monitor`. It must change in the same commit that changes the skill, or
  agents will follow a memory pointing at a deleted command.

### 6.6 Sequence

Start **after `sase-lh` closes.** Every module this touches is being renamed by phases
2–8 right now; starting earlier means rebasing the work through the rename. This matches
`detached_proc_convergence` §8's sequencing conclusion.

| Phase | Work | Size |
| --- | --- | --- |
| 0 | Decide §6.7. Nothing else starts until the record model is chosen. | — |
| 1 | Rust: additive `ProcWire` fields, schema v3, min-version check in Python. | medium |
| 2 | Kernel: promote the monitor supervisor to the proc kernel; delete `tasks/supervisor.py`; every proc gains reparenting, ack, identity, dual timeouts. **Ship this alone and let it soak** — it changes execution for existing procs. | large |
| 3 | Named procs: `name` field, per-project active uniqueness, fingerprint replay, `sase proc run -n` / resolution order. | medium |
| 4 | Attachment: move `member`/`claims`/`followup*`/`settlement`/`transaction` behind an `artifacts_dir`-conditional path; implement the §6.2 ordering. | medium |
| 5 | `sase shell` CLI + `attach`; `sase monitor` becomes the erroring alias. | medium |
| 6 | Collapse epic launch's monitor/detached-task fork into one call. | small |
| 7 | ACE: shells in the Procs pane; keep the Agents-tab monitor row rendering, re-keyed on the proc row. | medium |
| 8 | Docs (`monitors.md` → `shells.md`, `cli.md`, `ace.md`, `sdd.md`), memory, glossary entry, `/sase_shell` skill, `sase memory init`. | medium |
| 9 | Delete `sase monitor`; land. | small |

Phase 2 is the one that carries risk and the one that delivers most of the value; it is
worth landing and living with before phases 3–5 build on it.

### 6.7 Decisions I need from you

1. **B or C** — is one unified "what is running" list worth an additive Rust wire change
   and the dual-record rule in §6.2? This is the whole decision; everything else follows.
2. **Name uniqueness scope** — per project (recommended) or host-wide?
3. **`--next` without a lane** — hard error (recommended), or should a host-started shell
   be able to *create* a fresh lane for its follow-up? The second is a genuinely useful
   new capability (scheduled agent kickoff) and genuine scope creep.
4. **Does `sase proc run` inherit the heavier kernel unconditionally?** Recommended yes,
   for uniformity; the cost is one extra fork and a sub-second bounded ack poll.
5. **Do the 31 `monitor_*` scan-wire fields get renamed to `shell_*`,** or kept with
   serde aliases? Recommended: rename only the ~15 that survive on the artifacts side,
   with aliases, in phase 8 — not in phase 1.
6. **`sase monitor` alias window** — one release (recommended), or a hard cut at phase 9?

---

## 7. Risks

1. **Dual-record divergence** for lane-attached shells. Mitigated by §6.2's
   single-writer + ordering rule, and it must be tested directly: kill the supervisor
   between each pair of steps and assert both records agree afterwards.
2. **Phase 2 changes execution for existing procs.** Every `sase task run`, every epic
   launch, and every bead-work launch starts going through a different supervisor. Land
   it alone, behind the full `just check-full` lane, and keep the old module importable
   for one release to make bisecting cheap.
3. **A name is a lock.** Per-project active uniqueness means a wedged shell blocks the
   next start under that name. `sase shell stop` and the reconciler must be reliable
   enough to clear it, and the collision error must name the blocking row and the exact
   command to inspect it — the way `_active_monitor_message()` already does.
4. **Naming confusion.** `shell` implying interactivity (§6.3); and SASE will briefly
   have had three names — task, proc, monitor, shell — for adjacent concepts within one
   month. The glossary entry is not optional.
5. **Schema v3 across mixed versions.** An old `sase` writing v2 rows while a new one
   expects v3. The min-version relaxation makes new-reads-old safe; old-reads-new needs
   the Rust side to keep tolerating unknown fields (it does, via `serde`).
6. **The `sase-kp` hardening must not be lost in the move.** The launch barrier, start
   ack, identity check, claim-undo path, and reconciliation ordering were each written
   against a specific reproduced failure. The move should be mechanical, and
   `tests/monitor/` should be migrated rather than rewritten — 4,169 lines of tests are
   the record of what those defects were.
7. **In-flight monitors at cut-over** (§6.5). A monitor started before the upgrade and
   still running after it must settle. This is the highest-probability real-world break.

---

## Appendix: verified facts and where they came from

| Claim | Evidence |
| --- | --- |
| Monitor is 17 modules / 3,747 lines; procs 8 / 1,390 | `wc -l src/sase/monitor/*.py src/sase/tasks/*.py` |
| Monitor tests 19 files / 4,169 lines | `wc -l tests/monitor/*.py` |
| `PROC_WIRE_SCHEMA_VERSION = 2`; kinds are `command`/`tui`/`detached`; unknown kinds rejected on write | `sase-core/crates/sase_core/src/procs/{wire,store}.rs` |
| Pruning only removes terminal rows | `procs/store.rs:275-296` |
| 31 `pub monitor_*` fields in the agent-scan wire | `grep -c "pub monitor_" crates/sase_core/src/agent_scan/*.rs` |
| Python proc schema check is exact-equality | `src/sase/tasks/models.py:254-260` |
| `resolve_lane()` requires existing agent artifacts | `src/sase/monitor/store.py:69-81` |
| Epic launch falls back from monitor to detached task | `src/sase/bead/epic_launch.py:120-190` |
| `start_monitor` has exactly 2 callers outside its package | `grep -rn "start_monitor" src/` |
| `BoundedLogPipe` already shared by both substrates | `src/sase/tasks/logs.py:16`, `src/sase/monitor/supervise.py:30` |
| Monitor supervisor capabilities in §1.3 | `src/sase/monitor/{supervise,start,supervisor_bootstrap,identity}.py` vs `src/sase/tasks/{supervisor,runner}.py` |
| Memory instructs agents to use `/sase_monitor` for `check-full` | `sase/memory/build_and_run.md:39-41` |
| CLI conventions (alphabetical, short aliases, bare-group `list`) | `sase/memory/cli_rules.md` |

Files that change, by area: `src/sase/monitor/**` (17), `src/sase/tasks/**` (8),
`src/sase/main/{parser,handler,render}_{monitor,task}.py` (6),
`src/sase/bead/{epic_launch,task_launch}.py`, `src/sase/ace/tui/{task_mirror,task_queue,
task_subprocess}.py` and `modals/tasks_pane*.py`, `src/sase/monitor_state.py`,
`sase-core/crates/sase_core/src/{procs,agent_scan}/**`, `tests/monitor/**` (19),
`tests/test_tasks_*.py` (2), `docs/{monitors,cli,ace,sdd,agent_families}.md`,
`sase/memory/build_and_run.md`, `src/sase/xprompts/skills/sase_monitor.md`, and the
project glossary.

Verification for this work is `just check-full` plus the PNG snapshot suite: it crosses
Rust wire and store behavior, CLI parsers, ACE navigation, the Procs pane, the Agents
tab, and agent-family lifecycle.
