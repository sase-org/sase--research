---
create_time: 2026-08-13
updated_time: 2026-08-13
status: research
---

# Migrating TUI-Attached Procs to Detached Procs

**Research question:** what would it take to eliminate the TUI-attached proc kind
entirely — migrating every proc that today runs inside the ACE TUI process to a
supervisor-owned detached proc — given that a detached proc requires an associated
command, and what should that command be?

**Scope:** the `sase` repo at master `3085a0d28` on 2026-08-13, the sibling
`sase-core` Rust crate at `origin/master`, and the live proc store at
`~/.sase/tasks/tasks.jsonl` (282 rows) as read on 2026-08-13. Terminology follows the
in-flight rename epic `sase-lh` (*Rename SASE Background Tasks to Procs*): this note
says **proc** for the durable background-execution unit and keeps the current
identifiers (`sase task`, `sase.tasks`, `kind="tui"`) when quoting code.

## Bottom line

1. **The premise is correct, and it is enforced in exactly one place.** A supervised
   proc — both `command` and `detached` kinds — must carry a non-empty argv;
   `_validated_argv()` rejects an empty one before the row is ever written. The Rust
   store does *not* enforce this, so TUI-kind rows land with `command: []` legally.
   Empirically **277 of 281 TUI rows in the live store (98.6%) have an empty command**.
   Only the four rows whose bodies happened to call `TaskReporter.run()` recorded one.

2. **There are two independent axes being collapsed, not one.** `kind` conflates
   *ownership* (who drives the row: a supervisor process vs. the TUI's own worker
   thread) with *attribution* (which session, if any, owns the row for scoping).
   Migrating TUI procs collapses the ownership axis; removing `-d|--detached` collapses
   the attribution axis. They are separable, and the second is nearly free once the
   first is done: `--detached` becomes exactly `--session none`, which already exists.

3. **57 call sites submit TUI procs**, but they are not 57 commands. They reduce to
   about **24 distinct proc types** in three buckets: ~13 that map onto domain
   operations another frontend would legitimately want (→ real CLI subcommands), ~6
   that already have a CLI equivalent and can be flipped almost immediately, and ~5
   that should not be procs at all and should be demoted to plain Textual workers with
   no durable row.

4. **The command is the easy half.** The hard half is the four capabilities a TUI proc
   gets for free and a detached proc does not have at all: **completion callbacks**
   (`on_complete`, 30+ sites), **store-wide dedup** (`dedup_key` / `exclusive_scopes`
   are in-memory and per-process today), **closure capture** of live TUI objects, and
   **live in-memory log ownership**. Each needs a new mechanism before any migration
   lands.

5. **The new command should live in the existing domain command groups**
   (`sase patch`, `sase agent`, `sase bead`, `sase plugin`, …), not in a new `sase ace`
   sub-namespace and not behind a generic internal dispatcher. This follows directly
   from the repo's own Rust-core boundary litmus test, and `sase ace` cannot host
   subcommands anyway without a breaking change — it is a leaf command with an optional
   `query` positional.

6. **Cost is real and should shape scope.** A detached proc pays ~0.6–1.0 s of process
   startup (a `sase` CLI cold start measured at 0.31 s minimum, 0.62 s for a real
   subcommand, plus a second interpreter for the supervisor) before any work begins.
   Several current TUI procs have a *median lifetime of 0.09 s*. Converting those is a
   10× latency regression for no benefit — which is why bucket three exists.

---

## 1. What "attached" and "detached" mean today

Three kinds are defined in `src/sase/tasks/models.py:17-22`:

| Kind | Meaning | Driven by | Session |
| --- | --- | --- | --- |
| `command` | Supervised proc submitted by a session | `sase.tasks.supervisor` subprocess | attributed |
| `tui` | Proc a TUI process runs itself and mirrors into the store | the ACE process's own Textual worker thread | attributed |
| `detached` | Supervised proc no session owns | `sase.tasks.supervisor` subprocess | none |

`command` and `detached` are the same execution model — `_SUPERVISOR_OWNED_KINDS`
(`src/sase/tasks/runner.py:41`) contains both, and both go through
`_submit_supervised_task()`. They differ only in whether a `session_id` is recorded.
`tui` is the genuinely different one: no supervisor, no child process, the row's `pid`
is the *TUI's own pid* (`src/sase/ace/tui/task_mirror.py:271`), and the work is a Python
callable on a Textual worker thread.

This asymmetry leaks into user-facing behavior in several places:

- `kill_task()` refuses TUI rows outright — *"TUI-owned tasks can only be killed from
  their owning ACE session"* (`src/sase/tasks/runner.py:226-229`). `sase task kill` is
  therefore a lie for 99% of the rows in the store.
- Orphan reconciliation branches on kind: supervisor-owned rows verify
  `/proc/<pid>/cmdline` matches the supervisor argv, TUI rows only check pid liveness,
  and unclaimed rows use a 60 s grace only for supervisor kinds
  (`src/sase/tasks/runner.py:283-296`).
- `_ListScope.matches()` treats `kind == detached` as *always in scope*, while a
  session-less non-detached row depends on `include_unattributed`
  (`src/sase/main/task_handler.py:80-87`).
- The TUI's own indicator has to count two populations separately: its in-memory queue
  plus a polled store count of "detached + this session's command rows"
  (`src/sase/ace/tui/task_mirror.py:350-368`).

Every one of those special cases disappears if `tui` does.

## 2. Verifying the premise: does a detached proc require a command?

**Yes — in the Python submit path only.**

```
src/sase/tasks/runner.py:337-341
def _validated_argv(argv: Sequence[str]) -> list[str]:
    command = [str(part) for part in argv]
    if not command or not command[0]:
        raise TaskSubmitError("task command must contain a non-empty argv")
    return command
```

`_submit_supervised_task()` calls it first thing (`runner.py:129`), for both
`submit_task()` and `submit_detached_task()`. The requirement is not incidental: the
supervisor's entire job is to `Popen` that argv and own its process group, so a
commandless supervised proc has nothing to supervise.

`submit_detached_task()` additionally requires a non-empty `origin` (it is a required
keyword, documented as *"the only record of where the work came from"*,
`runner.py:93-98`) and a `cwd` that resolves to an existing directory
(`_validated_cwd`, `runner.py:344-348`).

**The store does not enforce it.** `validate_task()` in
`sase-core/crates/sase_core/src/tasks/store.rs:397-411` requires non-empty `task_id`,
`label`, `cwd`, `origin`, `created_at`, and `log_path` — `command` is deliberately
absent from that list. `validate_kind()` (`store.rs:424-429`) accepts exactly
`["command", "tui", "detached"]` and rejects anything else.

**So TUI rows legally carry no command, and in practice they don't:**

```
$ # ~/.sase/tasks/tasks.jsonl, 282 rows, 2026-08-13
kind=tui       281 rows   →  277 with command: []   (98.6%)
kind=detached    1 row    →    0 with command: []
```

The four exceptions are rows whose body called `TaskReporter.run()` or
`reporter.set_command()`, which is the only writer of `TaskInfo.command`
(`src/sase/ace/tui/task_subprocess.py:118-120`); `TaskInfo.command` otherwise defaults
to `None` (`src/sase/ace/tui/task_queue.py:157`) and the mirror writes
`command=list(info.command or [])` (`task_mirror.py:260`).

**Conclusion:** creating a command for each migrated proc is genuinely required, and for
~99% of today's procs there is no command to reuse — it has to be invented.

## 3. Inventory of TUI procs

57 submission sites across `src/sase/ace/` route through `_submit_tracked_task()` /
`_submit_background_task()` in `src/sase/ace/tui/actions/task_actions.py`. Grouped by
proc type, with the live-store frequency and median lifetime where observed:

### 3a. Patch workflow (11 types, 15 sites) — `src/sase/ace/tui/actions/`

| Proc type | Site | Body |
| --- | --- | --- |
| `sync` | `sync.py:227` | claim workspace, sync, release |
| `mail` | `base.py:394` | mail the Patch |
| `reword` | `base.py:235` | `reword_execute_task()` after an interactive editor phase |
| `add_tag` | `base.py:308` | `add_tag_task()` after a modal |
| `accept` | `proposal_rebase.py:428` | accept proposal |
| `rebase` | `proposal_rebase.py:499` | rebase proposal |
| `revert` | `status.py:216` | `revert_patch()` |
| `submit` | `status.py:236` | `submit_patch()` |
| `archive` | `status.py:249` | `archive_patch()` |
| `restore` | `status.py:266` | restore from Reverted |
| `status` | `status.py:295` | transition with sibling reverts |
| `rewind` | `hints/_rewind.py:169` | rewind hint |

These are the cleanest migration candidates: every body is already a module-level
function whose arguments are `(project_file, cl_name, project_basename, …)` — all
strings, all serializable. `reword` and `add_tag` collect input interactively *before*
submitting, so the collected value is just another argv element.

### 3b. Agent lifecycle (7 types, 15 sites) — `src/sase/ace/tui/actions/agents/`

| Proc type | Sites | Live count | Median | Notes |
| --- | --- | --- | --- | --- |
| `kill` | `_kill_tasks.py:97,181` | 89 | 144 s | kill **persistence**, not signalling |
| `dismiss` | `_dismissing.py:251,379` | 32 | 23 s | dismissal transaction |
| `save` | `_marking.py:231` | — | — | mark persistence |
| `agent-directive` | `_approve.py:178`, `_wait_actions.py:219,286,388`, `rename.py:340`, `_tribe_assignment.py:259` | 3 | 2.3 s | persist a directive to `agent_meta.json` |
| `revert_preview` / `revert_agent` | `_revert.py:128,188,338,397` | — | — | single + bulk |
| `monitor-stop` | `_monitor_stop_flow.py:67` | — | — | |
| `agents-sync` / `agents-cached-integration` | `agents_sync.py:218,272` | — | — | uses `exclusive_scopes=("agents-sync",)` |

`kill` is the highest-volume proc in the store and the hardest to command. Its body
(`_kill_tasks.py:27-95`) closes over `list[BulkKillItem]` (live `Agent` objects), a
`dismissed_snapshot` set, an `agents_with_children_snapshot` list, an
`AgentCleanupPlanWire`, a `SavedAgentGroupWire`, *and* a bound method
`self._register_expected_agent_artifact_deletion` used as a callback into TUI state.
None of that is expressible as argv today.

### 3c. Notification / gate / launch (6 types, 7 sites)

| Proc type | Site | Existing CLI equivalent |
| --- | --- | --- |
| `notification-gate` | `agents/_notification_gate_execution.py:92` | **`sase gate answer`** |
| `gate-action` | `agents/_notification_gate_actions.py:165` | **`sase gate act`** |
| `plan-gate` | `agents/_notification_plan_gate.py:141` | partial |
| `launch` (approval) | `agents/_notification_launch_approval.py:126` | **`sase launch approve` / `reject`** |
| `launch` (agent) | `agent_workflow/_launch_tasks.py:87`, `agents/_notification_modals.py:457` | partial |
| `question` | `agents/_notification_question_modal.py:245` | partial |
| `notification` | `modals/notification_modal_action_support.py:85` | partial |

This bucket is the most migration-ready: the gate path already *builds an argv* and
feeds it to `reporter.set_command()` (`_notification_gate_execution.py:125`,
`_notification_gate_actions.py:213`), which is precisely the shape a detached proc
needs. `execute_gate_selection()` is already called with `source="tui"`, so the headless
CLI path exists and is exercised.

### 3d. Bead operations (3 types, 3 sites)

`bead-<operation>` (`_artifacts_beads_common.py:136`), `bead-issue-open`
(`_artifacts_beads_issue_actions.py:241`), and issue mutations
(`_artifacts_beads_issue_mutations.py:95`). All are keyed by `(project, bead_id)` and
have direct `sase bead <verb> <id>` equivalents already. Note that standalone task-bead
*launch* already bypasses the TUI queue and submits a detached proc
(`sase/bead/task_launch.py:83-95`, argv `["sase", "bead", "work", …]`) — the exemplar
for this whole migration.

### 3e. Plugin / environment maintenance (8 types, 9 sites) — `src/sase/ace/tui/modals/`

`plugin-install` (×2), `plugin-uninstall`, `plugin-update`, `comprehensive-update` (56
rows in the store, median 5.9 s, max 455 s), `sase-update` (×2), `dev-update`,
`mode-switch`, `agent-cli-update`. Every one of these already shells out through
`reporter.uv_runner()` or `reporter.subprocess_run_fn()` — i.e. they are *already*
subprocess pipelines with an in-process orchestrator. `sase plugin install/uninstall/
update` and `sase update` already exist as commands.

### 3f. UI-state maintenance (5 types, 5 sites) — **should not be procs**

| Proc type | Site | Live count | Median | Why |
| --- | --- | --- | --- | --- |
| `prompt-stash` | `agent_workflow/_prompt_bar_stash.py:149` | 5 | **0.09 s** | append one JSON entry, update a badge |
| `commit-fetch` | `widgets/artifacts/commits_pane.py:307` | — | — | pane cache refresh, `reload_on_complete=False` |
| `<noun>-commit` | `agent_workflow/_prompt_bar_save_xprompt_git.py:189,346` | 3 | 2.0 s | save an xprompt to git |
| `snippet-chezmoi-apply` | (same flow) | 3 | 0.51 s | |
| `config-commit` | `modals/config_commit.py:133` | — | — | `notify_on_complete=False`, `reload_on_complete=False` |
| `bgcmd-launch` | `actions/axe_bgcmd.py:256` | — | — | already spawns its own detached process |

These exist to keep work off the Textual event loop, not because a user ever wants to
find them in a proc list, resume them after a TUI restart, or run them from another
machine. A durable store row for a 90 ms operation is pure overhead.

## 4. What a TUI proc gets that a detached proc does not

Inventing a command is necessary but not sufficient. Four capabilities have no detached
equivalent today.

### 4.1 Completion callbacks (the biggest gap)

`_submit_tracked_task(..., on_complete=…)` runs a UI-thread callback carrying a typed
`payload` when the worker finishes (`task_actions.py:306-319`). Over 30 sites use it,
and the payloads are rich in-process objects: `LaunchTaskOutcome` requests agent
refreshes and notification refreshes; `CleanupTaskOutcome` schedules an agents refresh
with a named source; `_GateTaskOutcome` carries a `_PartialAttempt`.

A detached proc's TUI has **no mechanism at all** to observe a specific row reaching a
terminal state. The mirror's writer thread only polls an aggregate *count*
(`_refresh_detached_count`, `task_mirror.py:350-368`) and the Procs pane polls the
store for display (`tasks_store_rows.py`). Nothing dispatches per-row completion.

**Required:** a completion watcher. The natural home is the existing `TaskMirror`
writer thread — it already runs off the event loop, already polls the store on a
cadence, and already has a `call_from_thread` path back to the UI
(`task_actions.py:89-99`). It would track submitted ids, detect the terminal transition,
and post a message the app routes to a registered handler. Outcome payloads must then
travel through the store (a JSON blob written by the CLI and read back) instead of
through a Python object.

### 4.2 Dedup and exclusion

`dedup_key` (`get_running_for_key`), per-Patch dedup (`get_running_for_cl`), and
`exclusive_scopes` (`get_running_for_scopes`) are all in-memory and scoped to one TUI
process (`task_queue.py:295-331`). Detached procs need store-wide dedup.

Precedent exists but is hand-rolled per call site: `submit_task_launch_task()` takes a
`log_file_lock` and scans `read_tasks(status=ACTIVE)` for a matching argv prefix +
tags (`sase/bead/task_launch.py:87-95, 114-118`); `_active_epic_launch_for_plan()` does
the same for epics (`sase/bead/epic_launch.py:246-248, 264+`).

**Required:** promote that into `submit_detached_task(..., dedup_key=…,
exclusive_scopes=…)` with one store-level lock. That means a new `dedup_key` field on
the wire, which is a `sase-core` change: `BackgroundTaskWire` (`tasks/wire.rs:10`) plus
the Python `BackgroundTask` dataclass. Note that `TASK_WIRE_SCHEMA_VERSION` is checked
for **exact** equality (`models.py:254-260`), so this is a coordinated bump, not a
silently additive field.

### 4.3 Closure capture

TUI proc bodies are closures over live objects. Section 3b's `kill` flow is the worst
case, but `_launch_tasks.py`, `_notification_*`, and the plugins-browser flows all
close over parsed plans, wire objects, and bound methods.

**Required:** for each migrated proc, a *serialization contract* — reduce the closure to
durable identifiers (agent names, artifacts dirs, project keys, bead ids) that the CLI
can re-resolve, or write a payload file and pass its path. Per the repo's Rust-core
boundary rule, the transaction logic that gets extracted this way is exactly the kind of
"shared backend and domain behavior" that belongs in `sase-core` rather than being
re-implemented behind a CLI shim.

### 4.4 Live in-memory log

TUI procs own a bounded in-memory `_TaskLog` the pane reads directly, with typed
streams (`stdout`, `stderr`, `progress`, `header`, `result`) and `redirect_print_to()`
capturing bare `print()` calls. The mirror flushes it to the durable log incrementally.
Detached procs get combined stdout/stderr from the supervisor and nothing else.

**Impact:** the stream typing and `reporter.phase()` / `reporter.section()` markers are
lost unless the CLI emits them as text conventions the renderer re-parses. This is a
presentation regression, not a blocker, but it will be visible in the Procs pane.

### 4.5 What gets *better*

Worth stating for balance — migration is not all cost:

- `sase task kill` starts working for every proc instead of refusing 99% of rows.
- Procs survive a TUI crash or restart. A `kill` proc with a 1232 s observed maximum
  currently dies with the TUI and leaves a half-applied transaction.
- Every proc becomes reproducible and scriptable from the shell, from Telegram, from a
  mobile gateway, and from an agent — the same property that made
  `sase bead work` / epic launch work well as detached procs.
- Orphan reconciliation, list scoping, and the proc indicator all lose their kind
  branches.
- Killing a proc becomes a process-group SIGTERM through the supervisor rather than
  `worker.cancel()` plus best-effort `terminate_processes()`, which cannot interrupt a
  Python body that is not in a subprocess.

## 5. Where should the command live?

### Option A — a new `sase ace <verb>` namespace

**Rejected.** `sase ace` is a leaf command, not a group: it takes an optional `query`
positional whose default is computed from saved queries
(`src/sase/main/parser_ace.py:10-24`). Adding subcommands means either a breaking change
to that positional or an awkward two-mode parser. It also misfiles the work — these are
Patch, agent, bead, and plugin operations that happen to be *reachable* from the TUI,
not properties of the TUI.

### Option B — distribute into the existing domain command groups

**Recommended.** Each proc becomes a subcommand of the group that owns its domain:

| Bucket | Command group | New subcommands needed |
| --- | --- | --- |
| Patch workflow (3a) | `sase patch` | `sync`, `mail`, `reword`, `tag add`, `accept`, `rebase`, `revert`, `submit`, `archive`, `restore`, `rewind` |
| Agent lifecycle (3b) | `sase agent` | `dismiss`, `mark`, `revert`, `directive set`, `cleanup` (kill persistence) |
| Notification/gate (3c) | `sase gate`, `sase launch` | **none** — `gate answer`, `gate act`, `launch approve/reject` already exist |
| Beads (3d) | `sase bead` | **none** — verbs already exist |
| Plugins (3e) | `sase plugin`, `sase update` | at most flags on existing verbs |
| UI-state (3f) | — | **none** — demote out of the proc store |

`sase patch` already exists as a group with `current`, `ref`, `search`, `set-origin`,
`sync-deltas`, `sync-external`, and `migrate` — it is missing exactly the *mutating
workflow* verbs, which is a gap worth closing on its own merits. `sase agent` likewise
has `list`, `kill`, `show`, `sync`, `tribe`, `archive`, `artifacts`, `index` — `kill`
today means "SIGTERM a running agent by name", which is *not* what the TUI's `kill`
proc does (that one persists a kill/dismiss transaction), so a distinct verb is needed
and the naming collision should be resolved deliberately.

Three arguments make this the right choice:

1. **It is the repo's own stated test.** `CLAUDE.md`'s Rust-core boundary rule: *"if a
   web app, CLI, editor integration, or another frontend would need the behavior to
   match the TUI, treat it as core backend logic."* Every proc in buckets 3a–3e passes
   that test. Building real domain commands is the shape that rule already prescribes;
   the proc migration is just the forcing function.
2. **The commands are independently valuable.** `sase patch mail my-feature` is useful
   whether or not procs exist. A dispatcher argv is useful to nothing.
3. **It is honest in the UI.** The Procs pane shows `command`. A user reading
   `sase agent dismiss foo bar` learns something; a user reading
   `sase proc exec --payload /tmp/x.json` does not.

The cost is real: roughly **16–20 new public subcommands**, each owing alphabetical
ordering, a short alias, excellent `-h` output, and tests, per `sase/memory/cli_rules.md`.

### Option C — one generic internal dispatcher

`sase proc exec <type> --payload <file>`, hidden with `argparse.SUPPRESS` (precedent:
the SUPPRESS'd lifecycle aliases in `src/sase/main/parser_project.py:79-82`).

**Rejected as the primary path**, for a narrow reason: it does not remove the work, it
relocates it. The payload schema for `kill` is exactly as hard to design as the argv for
`sase agent cleanup`, and it additionally becomes a versioned private contract between
two `sase` versions that can now differ (the TUI writes a payload; a *later* `sase` on
`PATH` may read it). It also forfeits every benefit in §4.5 except durability.

**Keep it as a narrow escape hatch** for at most one or two procs where a genuinely
public command would be nonsense — `plan-gate` and the bulk `revert_preview` are the
plausible candidates. If used, gate it behind a payload schema version and a test that
the writer and reader agree.

### Recommendation

**Option B, with Option C available for ≤2 exceptions**, and bucket 3f explicitly
excluded from the migration rather than forced through it.

## 6. Recommended migration shape

Sequence matters: the mechanisms in §4 must exist before any high-traffic proc moves.

**Phase 0 — decide and de-scope.** Confirm bucket 3f leaves the proc store entirely
(plain `run_worker(thread=True)`, no mirror row). This alone removes 5 proc types and
all of the sub-second rows. Confirm whether `command` kind also collapses (see §7).

**Phase 1 — build the mechanisms.**
 - Completion watcher in `TaskMirror` + an app-level handler registry (§4.1).
 - Store-wide `dedup_key` / `exclusive_scopes` on `submit_detached_task()`, including
   the `sase-core` wire field and schema bump (§4.2).
 - A convention for structured outcome payloads a CLI writes and the TUI reads back.

**Phase 2 — migrate the free wins (bucket 3c, 3d).** Gate execution, gate actions,
launch approval, and bead operations already have commands and already build argv. This
phase validates the Phase 1 mechanisms against real flows at low risk. ~10 sites.

**Phase 3 — Patch workflow (bucket 3a).** Add the `sase patch` verbs. Bodies are already
string-argument functions; this is the largest *volume* of new CLI surface but the
lowest *conceptual* difficulty. ~15 sites.

**Phase 4 — plugins and environment (bucket 3e).** Mostly re-pointing at existing
`sase plugin` / `sase update` commands. Watch for the orchestration currently living in
the modal (`plugins_browser_comprehensive_update_execution.py`) — that logic must move
into the command, not be duplicated. ~9 sites.

**Phase 5 — agent lifecycle (bucket 3b).** The hard one. Requires extracting the kill /
dismiss / mark transactions into identifier-keyed functions (candidate for `sase-core`),
replacing the `register_expected_deletion` callback with something the CLI can express,
and resolving the `sase agent kill` naming collision. ~15 sites.

**Phase 6 — remove the kind.** Delete `TUI_TASK_KIND`, the `_SUPERVISOR_OWNED_KINDS`
branch in `_is_orphaned`, the `kill_task` refusal, the `_ListScope` detached special
case, `MIRROR_KIND`, and the `tui` entries in `TASK_KIND_CHOICES` (Python) and
`TASK_KINDS` (Rust). Migrate or accept the invalidation of existing `tui` rows — the
Rust store rejects unknown kinds on *write*, and read-side behavior for pre-existing
rows needs an explicit decision.

**Sequencing against `sase-lh`.** The procs rename epic is in progress (phases 2–8 open)
and touches every file this migration touches. This work should be a separate epic that
starts **after `sase-lh` closes**, so it is written against `sase proc` / `sase.procs`
naming once rather than rebased through a rename.

## 7. The `-d|--detached` flag

Today `-d|--detached` on `sase task run` selects `submit_detached_task` over
`submit_task` (`src/sase/main/task_handler.py:181`), i.e. it picks `kind=detached`
+ `session_id=None` instead of `kind=command` + a resolved session.

Once every proc is supervisor-owned, `kind` carries no information and the flag is
equivalent to the already-supported `--session none`. Removing it is safe, with one
deliberate behavior change to accept:

> `_ListScope.matches()` currently keeps `kind == detached` rows in scope for *every*
> query, while a session-less non-detached row is only shown when
> `include_unattributed` is set — which is false when the user passes an explicit
> `--session <other>` (`task_handler.py:80-87, 385-390`). After the collapse, "detached"
> and "unattributed" are the same thing, so `sase task list --session <other>` would
> stop showing global procs unless `include_unattributed` is changed to always-true.

Recommendation: keep `session_id` as an optional *attribution field*, drop `kind`
entirely (or freeze it to a single value for wire compatibility), make
`include_unattributed` unconditional, and keep `--session none` as the way to submit an
unattributed proc. Also drop `-d|--detached` from `sase task list`, where it is
documented as *"shorthand for --kind detached"*.

## 8. Cost measurement

Measured on `athena`, 2026-08-13, warm page cache:

| Operation | Min | Max |
| --- | --- | --- |
| `sase --version` (bare CLI cold start) | 0.308 s | 0.428 s |
| `sase task list -n 1` (real subcommand) | 0.624 s | 0.643 s |

A detached proc pays this **twice**: once for `python -m sase.tasks.supervisor` and once
for the `sase …` child it execs. Budget ~0.6–1.0 s of dead time before any work starts,
against ~0 for a thread in the already-warm TUI process.

Observed TUI proc lifetimes from the live store, by proc type:

| Proc type | n | Median | Max |
| --- | --- | --- | --- |
| `kill` | 20 | 144.35 s | 1232.72 s |
| `dismiss` | 9 | 23.11 s | 351.21 s |
| `plan-gate` | 13 | 7.02 s | 50.38 s |
| `comprehensive-update` | 13 | 5.90 s | 455.03 s |
| `launch` | 29 | 2.33 s | 188.60 s |
| `agent-directive` | 3 | 2.27 s | 4.57 s |
| `snippet-commit` | 3 | 2.01 s | 2.04 s |
| `plugin-uninstall` | 1 | 1.17 s | 1.17 s |
| `snippet-chezmoi-apply` | 3 | 0.51 s | 0.60 s |
| `prompt-stash` | 5 | **0.09 s** | 0.36 s |

The overhead is negligible for everything above `agent-directive` and dominant below
it. This is the empirical basis for bucket 3f.

## 9. Open decisions for the project owner

1. **Does bucket 3f leave the proc store?** If yes, the migration is meaningfully
   smaller and faster. If no, accept a 10× latency regression on `prompt-stash` and
   friends, and expect the Procs pane to fill with 90 ms rows.
2. **Does `command` kind collapse too, or only `tui`?** §7 recommends collapsing both.
   Collapsing only `tui` leaves `--detached` meaningful and is a smaller change.
3. **`sase agent kill` naming.** The existing verb signals a process; the TUI proc
   persists a transaction. Options: rename the new one (`sase agent cleanup`), or
   subsume both under `sase agent kill` with a flag.
4. **Escape-hatch budget.** Approve at most N procs for Option C, or forbid it outright.
5. **Existing `tui` rows.** Migrate in place, leave them readable but unwritable, or
   drop them at the kind removal. The Rust store rejects unknown kinds on write, so
   doing nothing means a one-way read-only tail.
6. **Epic sequencing.** Confirm this waits for `sase-lh` to close.

## Appendix: files that change

**Python core** — `src/sase/tasks/{models,runner,store,supervisor}.py`,
`src/sase/main/{parser_task,task_handler,task_render}.py`

**TUI runtime** — `src/sase/ace/tui/{task_mirror,task_queue,task_subprocess}.py`,
`src/sase/ace/tui/actions/task_actions.py`,
`src/sase/ace/tui/modals/tasks_pane*.py`, `tasks_store_rows.py`,
`src/sase/ace/tui/widgets/task_indicator.py`

**Call sites** — 57 across `src/sase/ace/tui/actions/**` and
`src/sase/ace/tui/modals/**` (enumerated in §3)

**New CLI** — `src/sase/main/parser_patch.py` + handler, `src/sase/main/parser_agent.py`
+ handler, plus flags on `parser_plugin.py` / `parser_update.py`

**Rust core** (`../sase-core`) — `crates/sase_core/src/tasks/store.rs` (`TASK_KINDS`,
`validate_task`), `crates/sase_core/src/tasks/wire.rs` (`dedup_key`)

**Tests** — `tests/test_tasks_runner.py`, `tests/test_tasks_facade.py`,
`tests/ace/tui/test_task_mirror.py`, `tests/main/test_task_handler_list.py`,
`tests/main/test_parser_task.py`, plus the bead launch/gate suites under
`tests/test_bead/`

**Docs / config** — `docs/cli.md`, `docs/ace.md`, `docs/configuration.md`,
`src/sase/default_config.yml` (`tasks.history_limit`)
