---
create_time: 2026-08-13
updated_time: 2026-08-13
status: research
---

# Migrating TUI-Attached Procs to Detached, Command-Backed Procs

**Research question:** what would it take to eliminate procs that run inside the ACE TUI
process, make every proc supervisor-owned and detached, and remove the
`-d|--detached` option — given that a detached proc requires a command and a TUI proc
does not?

**Scope:** the `sase` repo at `c1b2724a1`/`3085a0d28` on 2026-08-13, the live proc store
at `~/.sase/tasks/tasks.jsonl`, epic `sase-lh`, and `plans:202608/background_tasks_to_procs.md`.
This note says **proc** for the durable background-execution unit and quotes current
identifiers (`sase task`, `sase.tasks`, `kind="tui"`) when citing code.

This is a consolidation of two independent research reports
([`__a`](detached_proc_convergence__a.md), [`__b`](detached_proc_convergence__b.md))
plus verification of every load-bearing claim in both. Where they disagreed, the
adjudication and its evidence are given inline.

---

## Bottom line

**Your premise is correct**, and the enforcement is in exactly one place. It is stronger
than "some procs lack a command": the TUI proc interface is *designed around Python
callables*, and its `command` field is best-effort display metadata. **274 of 278 TUI
rows in the live store (98.6%) have `command: []`.**

Six findings shape the work:

1. **`--detached` is a misnomer.** `sase task run` already starts an OS-detached
   supervisor with or without the flag. `--detached` only decides whether the row is
   *attributed* to a session. Its own help text says so: *"Make the task global instead
   of attributing it to a session."*

2. **Two axes are being collapsed, not one.** `kind` conflates **ownership** (supervisor
   vs. the TUI's own worker thread) with **attribution** (which session scopes the row).
   Migrating TUI procs collapses ownership; removing `-d|--detached` collapses
   attribution. The second is nearly free once the first lands — `--detached` becomes
   exactly `--session none`, which already exists.

3. **54 producer sites across 37 ACE files**, reducing to ~24 distinct proc types in
   three buckets: ~13 that deserve real domain commands, ~6 that already have a CLI
   equivalent, and ~5 that should stop being procs entirely.

4. **The command is the easy half.** Four capabilities a TUI proc gets for free have no
   detached equivalent: per-row completion callbacks (30+ sites), store-wide dedup,
   closure capture over live TUI objects, and the typed in-memory log.

5. **Those capabilities are not green-field — and this is the finding both source
   reports missed.** `src/sase/monitor/` is an explicit, documented *mirror* of the task
   supervisor that already implements follow-up dispatch, result handoff, workspace
   claims, settlement, and orphan reconciliation. See §5. The real architectural question
   is whether to build a third supervised-command substrate or converge two.

6. **Commands belong in the existing domain groups** (`sase patch`, `sase agent`,
   `sase bead`, …), not in a `sase ace` sub-namespace and not behind a generic
   dispatcher. This follows from the repo's own Rust-core boundary rule.

**Sequence this as a separate epic starting after `sase-lh` closes.** The rename is
deliberately behavior-preserving; this work changes execution, ownership, persistence,
CLI shape, dedup, cancellation, and recovery.

---

## 1. What is true today

### 1.1 Three kinds encode two unrelated concepts

| Kind | Execution owner | Session ownership | Command |
| --- | --- | --- | --- |
| `command` | detached supervisor subprocess | attributed to a session | **required** |
| `tui` | the ACE process's own Textual worker thread | attributed to the ACE session | optional |
| `detached` | detached supervisor subprocess | global, none | **required** |

`command` and `detached` are the *same execution model*: `_SUPERVISOR_OWNED_KINDS`
(`src/sase/tasks/runner.py:41`) contains both and both flow through
`_submit_supervised_task()`, which launches `sase.tasks.supervisor` with
`start_new_session=True`. `tui` is the genuinely different one — no supervisor, no child
process, the row's `pid` is *the TUI's own pid* (`ace/tui/task_mirror.py:271`), and the
work is a Python callable on a worker thread.

The asymmetry leaks into user-facing behavior:

- `kill_task()` refuses TUI rows outright — *"TUI-owned tasks can only be killed from
  their owning ACE session"* (`runner.py:226-229`). **`sase task kill` is therefore a lie
  for ~99% of rows in the store.**
- Orphan reconciliation branches on kind: supervisor rows verify `/proc/<pid>/cmdline`,
  TUI rows only check pid liveness, and the 60 s unclaimed grace applies to supervisor
  kinds only (`runner.py:283-296`).
- `_ListScope.matches()` treats `kind == detached` as *always in scope*, while a
  session-less non-detached row depends on `include_unattributed`
  (`main/task_handler.py:80-87`). **Verified.**
- The proc indicator counts two populations: the in-memory queue plus a polled store
  count of "detached + this session's command rows" (`task_mirror.py:350-368`).

Every one of those special cases disappears with `tui`.

### 1.2 The premise, verified

**Yes — enforced in the Python submit path only.**

```python
# src/sase/tasks/runner.py:337-341
def _validated_argv(argv: Sequence[str]) -> list[str]:
    command = [str(part) for part in argv]
    if not command or not command[0]:
        raise TaskSubmitError("task command must contain a non-empty argv")
    return command
```

`_submit_supervised_task()` calls it first thing (`runner.py:129`), for both
`submit_task()` and `submit_detached_task()`. It is not incidental — the supervisor's
whole job is to `Popen` that argv and own its process group, so a commandless supervised
proc has nothing to supervise. `submit_detached_task()` additionally requires a non-empty
`origin` and a `cwd` that resolves to an existing directory.

**The store does not enforce it.** `validate_task()`
(`sase-core/crates/sase_core/src/tasks/store.rs:397-411`) requires non-empty `task_id`,
`label`, `cwd`, `origin`, `created_at`, and `log_path` — `command` is deliberately
absent. So TUI rows land commandless *legally*.

**And in practice they do.** Independently reproduced against the live store on
2026-08-13:

```
~/.sase/tasks/tasks.jsonl — 279 rows
  kind=tui        278 rows  →  274 with command: []   (98.6%)
  kind=detached     1 row   →    0 with command: []
```

The store had rolled by three rows between the two reads; **the 98.6% ratio was
identical both times.** The handful of exceptions are rows whose body happened to call
`TaskReporter.run()` / `.set_command()` — the only writer of `TaskInfo.command`
(`ace/tui/task_subprocess.py:118-120`), which otherwise defaults to `None`
(`task_queue.py:157`) and is mirrored as `command=list(info.command or [])`
(`task_mirror.py:260`).

Worse, `set_command()` runs *from inside the worker, after submission*, and the mirror's
progress path updates only `status` and `phase` — never `command`. So even the four
"successes" are timing-dependent.

**Conclusion:** a command must be invented for ~99% of today's procs. There is nothing to
reuse.

---

## 2. Inventory

The two source reports gave 54 and 57 call sites. **54 is correct**, and the discrepancy
is itself informative:

| Reference kind | Count |
| --- | --- |
| Direct `_submit_tracked_task(` / `_submit_background_task(` calls | 30 |
| **Indirect `getattr(app, "_submit_tracked_task", None)` submitters** | **24** |
| Method definitions | 2 |
| Docstring / comment mentions | 4 |
| **Total producer sites** | **54 across 37 files** |

One of the 30 is the internal `_submit_background_task` → `_submit_tracked_task` adapter,
leaving **53 real producers**. Several are wrappers that fan out further (the launch
wrapper serves five variants; the cleanup wrapper five; the bead wrappers eight).

> **Consequence for enforcement.** 24 of 54 producers submit through a *duck-typed string
> lookup*, not a typed call. A static test that "no proc execution path accepts a
> callable" must therefore match `getattr(..., "_submit_*")` by name, not just resolve
> call targets. This pattern also means the TUI silently no-ops if the mixin is absent.

### Bucket 1 — Patch workflow (11 types, 15 sites), `ace/tui/actions/`

`sync`, `mail`, `reword`, `add_tag`, `accept`, `rebase`, `revert`, `submit`, `archive`,
`restore`, `status` (sibling-aware transition), `rewind`.

**Cleanest candidates.** Every body is already a module-level function whose arguments
are `(project_file, cl_name, project_basename, …)` — all strings, all serializable.
`reword` and `add_tag` collect input interactively *before* submitting, so the collected
value is just another argv element (or a `--*-file` for large text).

### Bucket 2 — Agent lifecycle (7 types, 15 sites), `ace/tui/actions/agents/`

| Type | Live count | Median | Note |
| --- | --- | --- | --- |
| `kill` | 89 | 144 s (max 1232 s) | kill **persistence**, not signalling |
| `dismiss` | 32 | 23 s | dismissal transaction |
| `agent-directive` (approve/wait/rename/tribe) | 3 | 2.3 s | persists to `agent_meta.json` |
| `save`, `revert_preview`/`revert_agent`, `monitor-stop`, `agents-sync` | — | — | `agents-sync` uses `exclusive_scopes` |

**The hard bucket.** `kill` is the highest-volume proc *and* the hardest to command: its
body (`_kill_tasks.py:27-95`) closes over `list[BulkKillItem]` of live `Agent` objects, a
`dismissed_snapshot` set, an `agents_with_children_snapshot`, an `AgentCleanupPlanWire`,
a `SavedAgentGroupWire`, **and a bound TUI method used as a callback**. None of that is
expressible as argv today. A 1232 s proc that dies with the TUI and leaves a half-applied
transaction is also the strongest argument *for* the migration.

### Bucket 3 — Notification / gate / launch (6 types, 7 sites)

| Type | Existing CLI |
| --- | --- |
| `notification-gate` | **`sase gate answer`** ✓ |
| `gate-action` | **`sase gate act`** ✓ |
| `launch` (approval) | **`sase launch approve` / `reject`** ✓ |
| `plan-gate`, `launch` (agent), `question`, `notification` | partial |

**Most migration-ready.** The gate path *already builds an argv* and feeds it to
`reporter.set_command()` (`_notification_gate_execution.py:125`), which is exactly the
shape a detached proc needs, and `execute_gate_selection()` is already called with
`source="tui"` — so the headless path exists and is exercised.

### Bucket 4 — Bead operations (3 types, 3 sites)

`bead-<operation>`, `bead-issue-open`, and issue mutations. All keyed by
`(project, bead_id)` with direct `sase bead <verb> <id>` equivalents already.

> **The exemplar for this entire migration already exists.** Standalone task-bead *launch*
> bypasses the TUI queue and submits a detached proc directly
> (`sase/bead/task_launch.py:83-95`), argv `["sase", "bead", "work", …]`, under a
> `log_file_lock` that scans active rows for a matching argv prefix + tags before
> submitting. That is the target shape, working in production today.

### Bucket 5 — Plugin / environment maintenance (8 types, 9 sites)

`plugin-install` (×2), `plugin-uninstall`, `plugin-update`, `comprehensive-update` (56
rows, median 5.9 s, max 455 s), `sase-update` (×2), `dev-update`, `mode-switch`,
`agent-cli-update`. **Every one already shells out** through `reporter.uv_runner()` or
`reporter.subprocess_run_fn()` — they are already subprocess pipelines with an in-process
orchestrator, and `sase plugin install/uninstall/update` and `sase update` already exist.

### Bucket 6 — Should not be procs at all (5 types)

| Type | Live count | Median | Why |
| --- | --- | --- | --- |
| `prompt-stash` | 5 | **0.09 s** | append one JSON entry, update a badge |
| `snippet-chezmoi-apply` | 3 | 0.51 s | |
| `<noun>-commit` | 3 | 2.0 s | save an xprompt to git |
| `commit-fetch` | — | — | pane cache refresh, `reload_on_complete=False` |
| `config-commit` | — | — | `notify_on_complete=False`, `reload_on_complete=False` |

These exist to keep work off the Textual event loop, not because anyone wants to find
them in a proc list or resume them after a restart. See §4 for the cost argument.

---

## 3. What a TUI proc gets that a detached proc does not

Inventing a command is necessary but not sufficient.

### 3.1 Per-row completion callbacks — the biggest gap

`_submit_tracked_task(..., on_complete=…)` runs a UI-thread callback carrying a typed
payload (`task_actions.py:306-319`). **30+ sites use it**, with rich in-process payloads:
`LaunchTaskOutcome` requests agent + notification refreshes, `CleanupTaskOutcome`
schedules a refresh with a named source, `_GateTaskOutcome` carries a `_PartialAttempt`.

A detached proc's TUI has **no mechanism to observe a specific row reaching a terminal
state.** Verified: `_refresh_detached_count` (`task_mirror.py:350-368`) does
`read_tasks(status=ACTIVE)` and returns a `sum(1 for …)` — an *aggregate count*. Nothing
dispatches per-row completion.

### 3.2 Dedup and exclusion

`dedup_key`, per-Patch dedup, and `exclusive_scopes` are all in-memory and scoped to one
TUI process (`task_queue.py:295-331`). Store-wide dedup is required *before* globalizing
producers, or two ACE instances race the same Patch mutation or package update.

The wire change is not free: `TASK_WIRE_SCHEMA_VERSION` is currently `1` and checked for
**exact equality** (`models.py:254-260`), so adding `dedup_key` is a coordinated Rust +
Python bump, not a silently additive field.

> **Time-sensitive:** `sase-lh` phase 2 migrates on-disk state and may bump the schema
> anyway. If so, adding `dedup_key` during that bump avoids a second coordinated
> migration. Phase 1 (Rust core) has **already closed**, so confirm quickly whether the
> window is still open — this is worth a five-minute check before planning.

### 3.3 Closure capture

Bucket 2's `kill` is the worst case, but `_launch_tasks.py`, `_notification_*`, and the
plugins-browser flows all close over parsed plans, wire objects, and bound methods. Each
migrated proc needs a *serialization contract*: reduce the closure to durable identifiers
the command re-resolves, or write a payload file and pass its path. Per the repo's
Rust-core boundary rule, the transaction logic extracted this way is exactly the "shared
backend and domain behavior" that belongs in `sase-core`.

### 3.4 Live typed in-memory log

TUI procs own a bounded `_TaskLog` with typed streams (`stdout`, `stderr`, `progress`,
`header`, `result`) and `redirect_print_to()` capturing bare `print()`. Detached procs get
combined stdout/stderr and nothing else. **A presentation regression, not a blocker**, but
visible in the Procs pane.

### 3.5 What gets better

- `sase task kill` starts working for every proc instead of refusing ~99% of rows.
- Procs survive a TUI crash or restart — critical for the 1232 s `kill` proc.
- Every proc becomes reproducible from a shell, Telegram, a mobile gateway, or an agent.
- Orphan reconciliation, list scoping, and the indicator all lose their kind branches.
- Killing becomes a process-group SIGTERM through the supervisor rather than
  `worker.cancel()` plus best-effort `terminate_processes()`, which **cannot interrupt a
  Python body that is not in a subprocess**.

---

## 4. Cost, and why bucket 6 exists

Measured on `athena`, 2026-08-13, warm cache:

| Operation | Min | Max |
| --- | --- | --- |
| `sase --version` (bare CLI cold start) | 0.308 s | 0.428 s |
| `sase task list -n 1` (real subcommand) | 0.624 s | 0.643 s |

A detached proc pays this **twice** — once for the supervisor interpreter, once for the
`sase …` child it execs. Budget **~0.6–1.0 s of dead time before any work starts**,
against ~0 for a thread in the already-warm TUI process.

Against observed lifetimes, overhead is negligible above `agent-directive` (~2.3 s) and
dominant below it. Converting `prompt-stash` (median **0.09 s**) is a ~10× latency
regression for no benefit.

**Decision rule.** Use a proc when work is materially long-running, must survive ACE,
benefits from global inspection/kill, or launches subprocess/network/VCS work. Use a plain
Textual worker for short UI-support I/O. This still achieves "no attached procs" — the
remaining workers are simply never entered into the proc store or pane.

---

## 5. The finding neither report made: a second substrate already exists

Both source reports specify the missing mechanisms (§3) as new construction. They are
not. `src/sase/monitor/` — the `sase monitor` feature, epic `sase-kp` — is an explicit
mirror of the proc supervisor, and its module list is a near-exact inventory of what this
migration needs:

```
supervise.py  """... :mod:`sase.tasks.supervisor`. Owns the monitored command
                  from spawn through the ..."""
store.py      "#: Mirrors :data:`sase.tasks.ids.MIN_TASK_REF_LENGTH` ..."
naming.py     "#: Same alphabet/length as :data:`sase.tasks.ids.TASK_ID_ALPHABET` ..."

followup.py  settlement.py  claims.py  reconcile.py  output.py  transaction.py
```

`sase monitor start` already offers, on a detached supervisor:

- `-n|--next TEXT` — **a follow-up action dispatched on completion** (§3.1's gap);
- `--next-output {none,tail,file}` — **structured result handoff**, the `file` mode being
  essentially the "result sidecar" both reports propose;
- `-j|--json`, `-t|--timeout`, `-i|--idle-timeout` — supervision policy;
- a `SUPPRESS`'d `_supervise` subcommand — the same hidden-dispatcher pattern report `__b`
  weighed as its "Option C".

Two caveats keep this from being a drop-in. Monitor's follow-up dispatches an **agent**,
not an in-process UI callback, so ACE's `on_complete` still needs a watcher. And monitors
are deliberately *not* a second task database — they are agent-family members backed by
`agent_meta.json` + `done.json`, so the storage models genuinely differ.

But the sibling research in this directory
([`monitor_command_substrate`](../monitor_command_substrate/monitor_command_substrate.md))
reports that *this* supervisor has non-authoritative timeouts, orphaned commands on
supervisor crash, leaked workspace claims, and check-then-create races on start — **the
same failure modes listed as risks for the proc migration.** Building a third copy would
reproduce them a third time.

> **Recommendation.** Add an explicit Phase 0 decision: does the proc migration build its
> own supervisor mechanisms, or does SASE converge procs and monitors onto one supervised
> command substrate with two projections? SASE currently has three overlapping supervision
> stacks — procs, monitors, and AXE bgcmd slots. This migration is the moment that becomes
> a deliberate choice instead of an accident.

---

## 6. Where the command should live

### Rejected: a `sase ace <verb>` namespace

`sase ace` is a **leaf command, not a group**: it takes an optional `query` positional
whose default is *computed at registration time* from saved queries
(`main/parser_ace.py:10-24`). Adding subcommands means a breaking change to that
positional or an awkward two-mode parser. It also misfiles the work — these are Patch,
agent, bead, and plugin operations that are merely *reachable* from the TUI.

### Rejected as primary: a generic dispatcher

`sase proc exec <type> --payload <file>`, hidden via `argparse.SUPPRESS`. It does not
remove the work, it relocates it — the payload schema for `kill` is exactly as hard to
design as the argv for `sase agent cleanup` — and it adds a versioned *private* contract
between two `sase` versions that can now differ (the TUI writes a payload; a later `sase`
on `PATH` reads it). It forfeits every §3.5 benefit except durability.

**Keep as a ≤2-proc escape hatch** for cases where a public command would be nonsense
(`plan-gate`, bulk `revert_preview`), gated behind a schema version and a writer/reader
agreement test.

### Recommended: distribute into the existing domain groups

Verified command surface as of `c1b2724a1`:

| Group | Exists today | Needed |
| --- | --- | --- |
| `sase patch` | `current`, `ref`, `search`, `set-origin`, `sync-deltas`, `sync-external`, `migrate` | `sync`, `mail`, `reword`, `tag`, `accept`, `rebase`, `revert`, `submit`, `archive`, `restore`, `transition`, `rewind` |
| `sase agent` | `list`, `kill`, `show`, `sync`, `tribe`, `archive`, `artifacts`, `index` | `dismiss`, `cleanup`, `revert`, directive verbs, group `save` |
| `sase gate` | `act`, `answer`, `create`, `show`, `wait` | **none** |
| `sase launch` | `approve`, `reject`, `request` | **none** |
| `sase bead` | `update`, `note`, `snooze`, `create`, `close`, `open`, `work` | `bead issue` subtree |
| `sase plugin` / `sase update` | full verbs | at most flags |
| `sase notify` | `create`, `list`, `show` | `mute`, `unmute`, `snooze` |
| `sase workspace` | `list`, `path`, `open`, `cleanup`, `repair`, `migrate` | `exec` (see §7) |
| `sase run` | **exists** — "Launch or resume a coding-agent run from a prompt, xprompt, workflow, or history" | `--request FILE` for resolved launch context |

Three arguments make this right:

1. **It is the repo's own stated test.** `CLAUDE.md`'s Rust-core boundary rule — *"if a
   web app, CLI, editor integration, or another frontend would need the behavior to match
   the TUI, treat it as core backend logic."* Every proc in buckets 1–5 passes. The proc
   migration is just the forcing function.
2. **The commands are independently valuable.** `sase patch mail my-feature` is useful
   whether or not procs exist. A dispatcher argv is useful to nothing.
3. **It is honest in the UI.** The Procs pane shows `command`. A user reading
   `sase agent dismiss foo bar` learns something; `sase proc exec --payload /tmp/x.json`
   teaches nothing.

Cost: roughly **16–20 new public subcommands**, each owing alphabetical ordering, a short
alias, good `-h` output, and tests per `sase/memory/cli_rules.md`.

`sase patch` is missing exactly the *mutating workflow* verbs — a gap worth closing on its
own merits. Note the **`sase agent kill` naming collision**: the existing verb means
"SIGTERM a running agent by name"; the TUI's `kill` proc persists a kill/dismiss
*transaction*. A distinct verb (`sase agent cleanup`) or a deliberate flag-based merge is
required.

---

## 7. Conflicts between the two reports, resolved

**Agent launches — `sase run`, not a new command.** Report `__a` recommended routing
launches through `sase run`; `__b` marked the CLI equivalent "partial" without
identifying a home. **`__a` is right:** `sase run` exists and is the documented launch
surface. Add a versioned `--request FILE` form for already-resolved xprompts, per-slot
environment, and bulk Patch selectors that cannot be reconstructed from one prompt string.
The command must return launch identities in the result envelope.

**AXE bgcmd — a command, not a demotion.** `__a` proposed `sase workspace exec`; `__b`
filed `bgcmd-launch` under "should not be procs" because it already spawns its own
detached process. **`__a` is right, and `__b`'s observation is the reason why.** Reading
`actions/axe_bgcmd.py:205-275`, the proc does workspace resolution, clean, VCS checkout,
and subprocess spawn — *and* writes a durable on-disk slot reservation via
`mark_slot_pending(slot)`, cleared in the dedup-rejection path. The code's own comment
notes that a missed cleanup leaves the slot "reserved until the TUI restarts." That is
durable state leaking on TUI death — an argument *for* supervisor ownership, not for
demotion. Its dedup key is also synthetic and per-slot (`bgcmd-slot-N`) and in-memory, so
two ACE instances can race the same slot today.

The right fix collapses the two layers: `sase workspace exec --project NAME --workspace N
[--patch NAME] -- COMMAND...`, submitted as the detached proc, claiming and checking out
the workspace and then `exec`ing the command inside the supervised process group. The
`sase workspace` group already exists. The separate bgcmd slot store can retire later.

**Call-site count — 54, not 57.** `__a`'s figure is exact (§2). `__b`'s 57 counted
docstring mentions and definitions.

**Notification mute/snooze — `__a` is precise.** `sase notify` exists as a group
(`create`, `list`, `show`); the mutation verbs do not. "New `notify` children" is the
correct characterization.

**Declassification list — merge both.** `__a` additionally nominated browser-open, small
agent-directive writes, and notification mutations. `__b` provided the empirical basis
(§4) and drew the line at ~2 s. Use `__b`'s measurements with `__a`'s decision rule;
agent-directive at 2.3 s median sits on the boundary and should be decided by whether a
directive write ever needs to survive ACE, not by latency alone.

---

## 8. Recommended sequence

**Phase 0 — decide and de-scope.**
- Confirm bucket 6 leaves the proc store entirely (plain `run_worker(thread=True)`, no
  mirror row). Removes 5 proc types and all sub-second rows.
- **Decide the substrate question in §5** before building anything.
- Confirm whether `command` kind collapses too, or only `tui` (§9).

**Phase 1 — build (or converge onto) the mechanisms.**
- Per-row completion watcher. The natural home is the existing `TaskMirror` writer thread:
  it already runs off the event loop, already polls the store, and already has a
  `call_from_thread` path back to the UI (`task_actions.py:89-99`).
- Store-wide `dedup_key` / `exclusive_scopes` with an atomic test-and-append under the
  Rust-core store lock, returning either the created proc or the conflicting one.
- Versioned request/result sidecars, mode `0600`, alongside proc logs, with
  `SASE_PROC_{ID,REQUEST_PATH,RESULT_PATH,LOG_PATH}` in the child environment. **Do not
  parse JSON back out of the combined stdout/stderr log** — progress output and nested
  tools make that channel unusable as a completion protocol.
- Split `command` (immutable launch identity, e.g. `["sase","patch","sync","sase-abc"]`)
  from `active_command` (mutable, for nested git/uv/provider calls). This resolves the
  current ambiguity where `set_command()` serves both roles.
- An argv-first `submit_proc_command(...)` facade with **no `Callable` parameter**.

**Phase 2 — migrate the free wins (buckets 3, 4).** ~10 sites that already have commands
and already build argv. Validates Phase 1 at low risk.

**Phase 3 — Patch workflow (bucket 1).** ~15 sites. Largest CLI surface, lowest
conceptual difficulty. Domain functions must move out of `ace/handlers` / `ace/tui/actions`
into a surface-neutral service (and into `sase-core` where the boundary rule applies) —
**a CLI handler must not import a TUI action module.**

**Phase 4 — plugins and environment (bucket 5).** ~9 sites, mostly re-pointing. Watch the
orchestration in `plugins_browser_comprehensive_update_execution.py` — it must *move*
into the command, not be duplicated. The updater must durably write its receipt before
returning, so a lost callback cannot lose completion state.

**Phase 5 — agent lifecycle (bucket 2).** ~15 sites, the hard one. Extract kill / dismiss
/ mark transactions into identifier-keyed functions, replace the
`register_expected_deletion` callback, resolve the `sase agent kill` collision.

**Phase 6 — collapse ownership and CLI scope.** `sase proc run` always detached; remove
`--detached` and `--session` from run; stop writing `command`/`tui` kinds; retain
legacy-read rendering.

**Phase 7 — retire the attached runtime.** Delete callable execution, `TUI_TASK_KIND`, the
`kill_task` refusal, the `_ListScope` special case, `MIRROR_KIND`, and the `tui` entries in
`TASK_KIND_CHOICES` / Rust `TASK_KINDS`.

**Sequencing against `sase-lh`.** Verified: 8 phases, phase 1 (Rust core) **closed**,
phases 2–8 **in progress**. It renames the CLI tree (phase 3) and the TUI tracked-task
runtime (phase 4) — every file this migration touches. Start after it closes so this work
is written against `sase proc` / `sase.procs` once rather than rebased through a rename.
Note also that `sase-lh` keeps **`task` as a legacy CLI alias**, so `--detached` must be
removed from both spellings, and the store moves to `~/.sase/procs/procs.jsonl`.

---

## 9. The `-d|--detached` flag

Today the flag selects `submit_detached_task` over `submit_task`
(`main/task_handler.py:181`) — `kind=detached` + `session_id=None` instead of
`kind=command` + a resolved session. Once every proc is supervisor-owned, `kind` carries
no information and the flag equals the already-supported `--session none`.

One deliberate behavior change to accept:

> `_ListScope.matches()` keeps `kind == detached` rows in scope for *every* query, while a
> session-less non-detached row appears only when `include_unattributed` is set — which is
> false when the user passes an explicit `--session <other>`. After the collapse,
> "detached" and "unattributed" are the same thing, so `sase proc list --session <other>`
> would stop showing global procs unless `include_unattributed` becomes unconditional.

**Recommendation:** keep `session_id` as an optional *attribution* field, drop `kind`
entirely (or freeze it to one value for wire compatibility), make `include_unattributed`
unconditional, and keep `--session none` as the way to submit an unattributed proc. Also
drop `-d|--detached` from `sase proc list`, where it is documented as "shorthand for
`--kind detached`". For the run flag, prefer a one-release rejection with an actionable
message ("all procs are detached; remove `--detached`") over a bare argparse error.

---

## 10. Risks

1. **Duplicated mutations across TUIs** — why atomic core-backed dedup must land before
   globalizing producers.
2. **Lost typed results** — parsing logs or relying on callbacks fails across restarts.
3. **Stale serialized state** — request files carry identifiers and user input; commands
   re-resolve live state and validate preconditions at execution time.
4. **Leaked sensitive input** — descriptions, feedback, prompts, and gate inputs must not
   appear in argv or labels; they leak into process listings and the proc record.
5. **Workspace leaks** — commands, not ACE, must claim and release in `finally` paths,
   including kill handling. Note the sibling monitor research reports this exact bug in
   the parallel supervisor.
6. **Update self-replacement** — the updater must write its receipt durably before the old
   process exits; ACE restart is presentation only.
7. **Proc history noise** — blind one-for-one migration turns browser opens and 90 ms
   writes into durable global rows.
8. **Mixed-version behavior** — old ACE processes still emit `tui` rows during rollout. The
   Rust store rejects unknown kinds **on write**, so read-side behavior for pre-existing
   rows needs an explicit decision; doing nothing yields a one-way read-only tail.

---

## 11. Acceptance criteria

- Every new proc has a non-empty immutable command before its store append.
- No proc execution path accepts a Python callable — enforced by a static test that also
  matches the `getattr(app, "_submit_*")` pattern (§2).
- Quitting or crashing ACE does not stop an ACE-submitted proc.
- Every active proc is killable via `sase proc kill` from any surface.
- Two ACE instances cannot race past the same `dedup_key` or overlapping exclusive scope.
- Phase, active child command, logs, exit status, and structured result stay inspectable
  without the submitting ACE.
- **Losing the completion callback loses only ephemeral UI feedback** — never a durable
  mutation, receipt, gate response, chained action, or workspace release. If ACE exits
  before completion, reopening it must reconstruct correct state from disk.
- `sase proc run -- COMMAND` is global and detached with no flag; help shows no
  `--detached` or `--session` on run.
- Legacy `command`/`tui`/`detached` rows remain readable, with orphaned active TUI rows
  reconciled deterministically.
- Integration tests cover ACE-exit survival, cross-TUI dedup, result delivery, preview
  flows, accept-with-mail chaining, updater restart/receipt behavior, and workspace claim
  release after success, failure, kill, and supervisor crash.

Run `just check-full` and the visual snapshot suite — this crosses core wire/store
behavior, CLI parsers, ACE navigation, the Procs pane, and update restart behavior.

---

## 12. Open decisions for the project owner

1. **Substrate convergence (§5).** Build proc-specific completion/result/claim mechanisms,
   or converge procs and monitors onto one supervised-command substrate? This is the
   highest-leverage decision and should be made first.
2. **Does bucket 6 leave the proc store?** If yes, the migration is meaningfully smaller.
   If no, accept a ~10× latency regression on `prompt-stash` and a pane full of 90 ms rows.
3. **Does `command` kind collapse too, or only `tui`?** §9 recommends both; collapsing only
   `tui` leaves `--detached` meaningful and is a smaller change.
4. **`sase agent kill` naming.** Rename the new one (`sase agent cleanup`), or subsume both
   under `kill` with a flag?
5. **Escape-hatch budget.** Approve at most N procs for the hidden dispatcher, or forbid it.
6. **Existing `tui` rows.** Migrate in place, leave readable-but-unwritable, or drop at kind
   removal?
7. **Schema-bump timing (§3.2).** Can `dedup_key` ride `sase-lh`'s state migration, or has
   that window closed with phase 1?
8. **Epic sequencing.** Confirm this waits for `sase-lh` to close.

---

## Appendix: files that change

**Python core** — `src/sase/tasks/{models,runner,store,supervisor}.py`,
`src/sase/main/{parser_task,task_handler,task_render}.py`

**TUI runtime** — `src/sase/ace/tui/{task_mirror,task_queue,task_subprocess}.py`,
`actions/task_actions.py`, `modals/tasks_pane*.py`, `tasks_store_rows.py`,
`widgets/task_indicator.py`

**Call sites** — 54 across 37 files under `src/sase/ace/tui/actions/**` and
`src/sase/ace/tui/modals/**` (§2)

**New CLI** — `src/sase/main/parser_patch.py`, `parser_agent.py`, `parser_notify.py`,
`parser_workspace.py` (+ handlers), plus flags on `parser_plugin.py`, `parser_update.py`,
`parser_run*.py`

**Rust core** (`../sase-core`, via `/sase_repo`) — `crates/sase_core/src/tasks/store.rs`
(`TASK_KINDS`, `validate_task`), `crates/sase_core/src/tasks/wire.rs` (`dedup_key`)

**Possibly shared** — `src/sase/monitor/{supervise,followup,settlement,claims,reconcile,output}.py`
if the §5 convergence is adopted

**Tests** — `tests/test_tasks_runner.py`, `tests/test_tasks_facade.py`,
`tests/ace/tui/test_task_mirror.py`, `tests/main/test_task_handler_list.py`,
`tests/main/test_parser_task.py`, `tests/test_bead/`

**Docs / config** — `docs/cli.md`, `docs/ace.md`, `docs/configuration.md`,
`src/sase/default_config.yml`
