---
create_time: 2026-08-13
updated_time: 2026-08-13
status: research
---

# Migrating ACE-Attached Procs to Detached, Command-Backed Procs

**Research question:** after the `sase-lh` terminology migration renames SASE Background
Tasks to Procs, what would it take to eliminate procs owned and executed by an ACE TUI,
make every real proc supervisor-owned and detached, and remove
`sase proc run -d|--detached`?

**Scope:** the `sase` repository at `3085a0d287ad` on 2026-08-13, plus epic bead
`sase-lh` and `plans:202608/background_tasks_to_procs.md`. Source names in this report
use the post-epic vocabulary, but paths and symbols quote the pre-rename tree when that
is the code inspected. Task beads, Textual workers that are not durable Procs, and the
Muse `task.lifecycle.*` protocol remain out of scope, exactly as specified by `sase-lh`.

## Bottom line

The migration is feasible, and the premise is true: a detached proc requires a real,
non-empty command, while an ACE-owned proc does not necessarily have one.

There are two different meanings hidden behind today's attached/detached distinction:

1. `sase task run` always starts an OS-detached supervisor. Without `--detached`, the
   row is merely _attributed and scoped to an ACE session_ (`kind="command"`); with the
   flag it is global (`kind="detached"`). Converting these command procs is mostly a
   data-model and CLI simplification.
2. ACE's `kind="tui"` rows are genuinely attached. Their Python callable runs in a
   Textual worker thread inside ACE, ACE owns cancellation and completion, and the row
   may contain `command=[]`. Converting these requires turning callable closures into
   command-line operations and recreating several services that the in-process proc
   runtime currently provides implicitly.

The source inventory found **54 calls** to `_submit_tracked_task`,
`_submit_background_task`, or their local alias across **37 ACE files**. One call is the
generic `_submit_background_task` adapter itself, leaving **53 producer or producer
wrapper sites**. Several wrappers fan out further: the launch wrapper serves five launch
variants, the cleanup wrapper serves five kill/dismiss/save variants, and the Beads
wrappers serve status, edit, note, snooze, create, close/open, launch, and
external-issue operations.

This should be a follow-on epic after `sase-lh`, not an expansion of that rename epic.
The rename is intentionally behavior-preserving; this work changes execution, ownership,
persistence, CLI shape, deduplication, cancellation, and recovery.

The most important design decision is where the new commands live:

> `sase proc` should remain the proc **control plane** (`list`, `show`, `run`, `kill`).
> A proc's executable operation should live under the domain that owns the behavior:
> `sase patch sync`, `sase gate answer`, `sase agent revert`, `sase plugin install`, and
> so on. ACE then submits that argv as a detached proc.

Do not add dozens of operation-specific children under `sase proc`, and do not add a
generic `sase ace run-callable` command that serializes Python closures. Either an
operation has useful headless semantics and deserves a domain command, or it is merely
short-lived UI work and should stop being represented as a Proc.

## What is true today

### The three current kinds encode two unrelated concepts

| Current kind | Execution owner                      | Session ownership and visibility         | Command requirement |
| ------------ | ------------------------------------ | ---------------------------------------- | ------------------- |
| `command`    | Detached supervisor                  | Attributed to a session, or unattributed | Required            |
| `tui`        | The ACE process and a Textual worker | Attributed to the ACE session            | Optional            |
| `detached`   | Detached supervisor                  | Global; no session owner                 | Required            |

The `command` versus `detached` distinction is not process detachment. Both flow through
`_submit_supervised_task()`, which launches `sase.tasks.supervisor` with
`start_new_session=True`, and the supervisor launches the command in another new
session. `--detached` selects `submit_detached_task()` instead of `submit_task()`, which
changes `kind` and prevents a `session_id`; it does not change how the command is
spawned.

### Detached procs really do require commands

`src/sase/tasks/runner.py::_validated_argv()` rejects an empty argv with
`"task command must contain a non-empty argv"`. Both `submit_task()` and
`submit_detached_task()` call that validator before appending a row. The supervisor then
passes `task.command` directly to `subprocess.Popen`. Tests explicitly cover both APIs
rejecting `[]` (`tests/test_tasks_runner.py`).

The record model itself is looser: `BackgroundTask.command` is a `list[str]`, and
deserialization maps a missing or null value to `[]`. That is necessary for TUI rows
today, but it is not sufficient input for the detached supervisor.

### ACE-owned procs can and commonly do lack commands

The path is unambiguous:

1. `TaskQueue.submit()` creates `TaskInfo` with `command=None`.
2. `_submit_tracked_task()` accepts a Python callable, not argv, calls
   `TaskMirror.track()`, and only then starts the Textual worker.
3. `TaskMirror._handle_track()` writes `command=list(info.command or [])`, so the
   durable row can contain `[]`.
4. Only `TaskReporter.set_command()` mutates `TaskInfo.command`. It runs from inside the
   worker after submission. The mirror's progress path updates only `status` and
   `phase`, not `command`, so later discovery of an argv is not reliably reflected in
   the durable row.

Only nine of the 37 producer files use `TaskReporter.set_command()`, `.run()`,
`.subprocess_run_fn()`, or `.uv_runner()`. The rest run Python domain functions and
closures directly. Even in those nine files, the durable command is timing-dependent
because mirroring and worker startup race.

This is stronger than “some procs have no command”: the current interface is designed
around callables, and its command field is only best-effort display metadata.

### What the TUI runtime currently supplies besides execution

Replacing a callable with argv does not by itself preserve behavior. The current
`TaskQueue`/`TaskMirror`/`TaskReporter` stack also supplies:

- per-Patch `dedup_key` exclusion and multi-domain `exclusive_scopes`;
- typed Python result payloads delivered to `on_complete` callbacks;
- live `phase` updates and structured log sections;
- optimistic-UI rollback on failure;
- chained actions, such as accept-then-mail and ordered post-write actions;
- in-process process registration and cancellation;
- TUI refresh, notification refresh, toasts, and in-place row updates;
- update completion behavior that may restart ACE;
- a session owner used for default visibility and kill routing.

Detached submission currently supplies none of the first five. It validates argv and
cwd, appends a row, spawns a supervisor, captures combined output, records exit status,
and supports process-group kill. A successful migration therefore needs a detached proc
client contract, not just a mechanical replacement with `submit_detached_proc(argv)`.

## Recommended target model

### One execution kind

All real procs should be supervisor-owned and globally visible. In the steady state:

- remove `command` and `tui` as writable kinds;
- either remove the `kind` field entirely or retain it only as legacy-read metadata;
- remove ownership-based session filtering;
- keep origin/provenance independently from ownership, for example `origin="ace"` and an
  optional `source_session_id` that never controls visibility or kill rights;
- make `command` immutable, required, and non-empty for every new proc;
- let `sase proc kill` kill every active proc uniformly.

Legacy terminal rows should remain readable without rewriting their logs. During a
mixed-version window, active legacy `command` rows can be treated as detached because
they already have supervisors. Active legacy `tui` rows should continue to be owned by
their old ACE process until they finish; once that process is gone, reconciliation
should terminalize them as errors. Only after the compatibility window should new code
stop recognizing `tui` ownership.

### CLI consequences

If every proc is detached, more than the run flag becomes redundant:

- `sase proc run -d|--detached` goes away; `run -- COMMAND` always creates a global
  detached proc. (The current spelling is `detached`, not `detatched`.)
- `sase proc run --session` goes away because attribution is no longer ownership.
- `sase proc list -d|--detached`, `--kind`, `--session`, and `--all` no longer select
  meaningful visibility sets and should be removed or reduced to legacy-history filters.
- JSON scope envelopes and TUI “this session/all sessions” controls disappear.
- `submit_task()` and `submit_detached_task()` collapse to one canonical `submit_proc()`
  API; legacy names can remain thin compatibility aliases during the rename/migration
  window.

For CLI compatibility, a hidden one-release no-op `--detached` that prints a warning
would be less disruptive than silently changing behavior, but it delays literal option
removal. If removal is the priority, reject it with the actionable message “all procs
are detached; remove `--detached`” rather than a generic argparse error.

### Proc command versus active child command

The durable `command` should always remain the top-level identity of the proc, such as
`["sase", "patch", "sync", "sase-abc"]`. Some commands run nested git, uv, or provider
commands. Those should update a separate mutable `active_command` field and `phase`;
they should not replace the immutable launch command. This fixes the current ambiguity
where `TaskReporter.set_command()` attempts to use one field for both roles.

## Runtime capabilities that must be added first

### 1. Durable, atomic deduplication

Move `dedup_key` and `exclusive_scopes` into the Proc wire/store. Submission must
atomically test active rows and append under the same Rust-core store lock; a Python
“read, then append” check would race two ACE instances. This is required before making
session-owned operations global, or two TUIs can launch the same Patch mutation or
package update concurrently.

The core API should return either the created proc or the conflicting active proc so ACE
can preserve today's useful duplicate message.

### 2. Versioned request and result sidecars

Many current callables capture rich dataclasses, lists, feedback text, or edited
content. Do not encode those in argv (which leaks them into process listings and the
proc record), and do not pickle Python closures.

Add supervisor-managed, mode-`0600` files alongside proc logs:

- a versioned request JSON file for large or sensitive command input;
- a versioned result JSON envelope with `success`, `message`, optional `payload`, and
  optional `error`—the cross-process equivalent of `TrackedTaskResult`;
- `request_path` and `result_path` metadata, retained/pruned with the proc;
- `SASE_PROC_ID`, `SASE_PROC_REQUEST_PATH`, `SASE_PROC_RESULT_PATH`, and
  `SASE_PROC_LOG_PATH` in the child environment.

Command-specific `--request` schemas should contain stable identifiers and user input,
not serialized TUI model objects or ephemeral closures. Commands should re-resolve live
project, Patch, agent, notification, or bead state when execution begins.

Do not parse JSON back out of the combined stdout/stderr log. Progress output, nested
tools, and warnings make that channel unsuitable for a completion protocol.

### 3. A cross-process `ProcReporter`

Refactor the useful parts of `TaskReporter` out of the TUI. When running under a proc,
the reporter can use `SASE_PROC_ID` to update `phase`, `active_command`, and `message`
in the durable store. Stdout/stderr remain ordinary captured logs. Foreground CLI use
should still work when the environment variables are absent.

Cancellation no longer needs each callable to register child `Popen` objects with ACE:
the supervisor owns the top-level command process group, and descendants stay in that
group unless they deliberately detach again. Commands that deliberately spawn another
daemon need to document that handoff instead of pretending the launcher proc owns the
daemon forever.

### 4. A non-owning ACE completion watcher

ACE still needs ephemeral UI reactions. Add a small watcher that maps a submitted
`proc_id` to an in-memory completion callback, polls or subscribes to terminal store
updates, loads the result envelope, and calls back on the Textual event loop. The
watcher is not the execution owner and may vanish without affecting the proc.

Callbacks may refresh panes, update badges, show toasts, or restart ACE, but all durable
mutation must occur inside the command. If ACE exits before completion, reopening ACE
must be sufficient to reconstruct correct state from disk. This rule eliminates hidden
correctness dependencies on an `on_complete` callback.

Chained durable operations should move into one domain command rather than relying on an
in-memory callback. Examples: ordered post-write actions should be one command with a
request list, and accept-with-mail should be one `sase patch accept --mail` command.

### 5. A detached submission facade for ACE

Replace callable submission with an argv-first API along these lines:

```text
submit_proc_command(
    argv,
    label,
    cwd,
    origin="ace",
    project=...,
    workspace_num=...,
    patch=...,
    tags=...,
    dedup_key=...,
    exclusive_scopes=...,
    request=...,
    on_complete=...,       # optional UI-only observer
)
```

There should be no `Callable` execution parameter. A static test can then enforce that
every ACE Proc producer supplies non-empty argv before the proc row is written.

## Where each command should live

The following inventory groups all 53 producer/wrapper sites. “Existing” means the
command already owns substantially the same domain operation, though it may need JSON,
batch, or result-envelope support. Proposed spellings are intentionally concrete enough
to plan against; exact flag names can be finalized in implementation planning.

### Patch lifecycle and VCS work (12 producer sites)

Current producers are in `actions/base.py`, `actions/status.py`, `actions/sync.py`,
`actions/proposal_rebase.py`, and `actions/hints/_rewind.py`.

| Current proc                | Recommended command                                                          | Status                                                                                                              |
| --------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| reword                      | `sase patch reword NAME --description-file FILE`                             | New `patch` child; ACE keeps the editor/modal phase local, command owns workspace claim and mutation                |
| add tag                     | `sase patch tag NAME KEY=VALUE`                                              | New `patch` child                                                                                                   |
| mail                        | `sase patch mail NAME --yes`                                                 | New `patch` child; command must own claim/release rather than inherit a TUI claim                                   |
| revert                      | `sase revert NAME`                                                           | Existing; optionally expose the same parser as `sase patch revert` later                                            |
| submit                      | `sase patch submit NAME`                                                     | New `patch` child                                                                                                   |
| archive                     | `sase patch archive NAME`                                                    | New `patch` child                                                                                                   |
| restore to WIP/Draft/Ready  | `sase restore NAME --status STATUS`                                          | Extend existing restore command                                                                                     |
| sibling-aware status change | `sase patch transition NAME STATUS`                                          | New `patch` child; ordinary fast transitions may stay synchronous and should not become procs merely for uniformity |
| sync                        | `sase patch sync NAME`                                                       | New `patch` child                                                                                                   |
| accept proposal(s)          | `sase patch accept NAME PROPOSAL... [--ready] [--bookkeeping-only] [--mail]` | New `patch` child; fold accept-then-mail into one command                                                           |
| rebase                      | `sase patch rebase NAME --onto PARENT`                                       | New `patch` child                                                                                                   |
| rewind                      | `sase patch rewind NAME ENTRY [--bookkeeping-only]`                          | New `patch` child                                                                                                   |

These domain functions currently live under `sase.ace.handlers` or
`sase.ace.tui.actions`. They must move to a surface-neutral Patch service (and into the
Rust core where the repository's backend-boundary rule applies) before both CLI and ACE
call them. A CLI handler must not import a TUI action module.

### Agent launches (one wrapper, five leaf variants)

`agent_workflow/_launch_tasks.py` serves single, repeat, multi-prompt, model/alternative
fanout, and bulk-Patch launches.

Use `sase run` rather than creating `sase proc launch`. The ordinary single, repeat,
multi-prompt, and directive-driven fanouts should be expressible by the canonical prompt
supplied to `sase run`. Add a versioned `sase run --request FILE` form for
already-resolved local xprompts, per-slot environment, immutable launch context, and
bulk Patch selectors that cannot safely be reconstructed from one prompt string.

The command must return launch result identities in the proc result envelope. ACE uses
them for exact artifact-delta reconciliation while it remains open; after a restart the
ordinary Agents loader must discover the same agents from durable artifacts.

### Agent management (14 producer/wrapper sites plus wrapper fanout)

| Current family                             | Recommended command                                                                         | Notes                                                                                       |
| ------------------------------------------ | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| kill persistence (single/bulk)             | extend `sase agent kill` to accept selectors, batches, and the complete cleanup transaction | The current CLI sends SIGTERM only; ACE persists substantially more cleanup state           |
| dismiss persistence (single/bulk)          | `sase agent dismiss NAME...`                                                                | New user-facing lifecycle command                                                           |
| save marked group                          | `sase agent group save --name GROUP NAME...`                                                | New; belongs with agent archive/group state, not Procs                                      |
| auto-approve directive                     | `sase agent auto NAME --mode MODE`                                                          | New surface over shared directive persistence                                               |
| wait / runner wait / run-now               | `sase agent wait NAME ...`; `sase agent wait NAME --clear`                                  | New; one command should handle dependency, bead, runner-cap, and priority fields atomically |
| rename                                     | `sase agent rename NAME NEW_NAME`                                                           | New                                                                                         |
| tribe assignment                           | `sase agent tribe set` or `sase agent tribe unset`                                          | Existing; extend batch/JSON support and make ACE invoke it                                  |
| revert preview/execute, single/bulk        | `sase agent revert NAME... [--preview] --json`                                              | New; preview returns a result envelope used by the confirmation modal                       |
| full agents sync                           | `sase agent sync --json`                                                                    | Existing                                                                                    |
| integrate exactly the badge's cached hoods | `sase agent sync --integrate-cached --hood ID... --json`                                    | Extend existing sync; do not smuggle captured Python objects into argv                      |
| stop monitor                               | `sase monitor stop ID --json`                                                               | Existing                                                                                    |

The auto/wait/rename commands may share a private surface-neutral directive service, but
a public `sase agent directive apply <opaque-json>` should not be the primary UX.
Specific commands give validation, help, auditability, and headless parity. Request JSON
is still appropriate internally for atomic bulk updates.

### Gates, plans, launch approvals, questions, and notifications (seven producer sites)

| Current proc                       | Recommended command                                                | Status                                                                                         |
| ---------------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| repeatable gate action             | `sase gate act ... --json`                                         | Existing and already command-backed                                                            |
| neutral gate response              | `sase gate answer ... --json`                                      | Existing                                                                                       |
| LaunchApproval accept/reject       | `sase launch approve SELECTOR` or `sase launch reject SELECTOR`    | Existing                                                                                       |
| neutral plan response              | `sase gate answer ...`, `sase plan approve`, or `sase plan reject` | Existing; use the gate command when the TUI has complete typed option input                    |
| legacy epic approval               | `sase plan approve SELECTOR --kind epic` or `sase bead work EPIC`  | Existing; keep only for legacy in-flight notifications                                         |
| UserQuestion response              | `sase gate answer --kind question ...`                             | Existing neutral gate path; retain the legacy response command only for old in-flight requests |
| mute/unmute and single/bulk snooze | `sase notify mute ID...`, `unmute ID...`, or `snooze ID...`        | New `notify` children over the existing atomic mutation functions                              |

These are the easiest migrations because the gate redesign already made the core work
command-backed. ACE currently bypasses those commands and calls the shared executor
directly so it can receive typed Python payloads and stream phases. The result sidecar
and cross-process reporter close that gap.

### Beads and external issues (three wrappers, many leaf actions)

Status cycle/edit, note, snooze/wake, create, close/open, and task/epic launch already
have corresponding `sase bead update`, `note`, `snooze`, `create`, `close`, `open`, and
`work` commands. ACE should build those argv directly instead of reproducing the bead
store transaction in closures. This also prevents the TUI and CLI implementations from
drifting on auto-commit messages and TaskTriage settlement.

External-issue edit, open/close, attach, create-and-link, and browser-open need a small
new subtree such as:

```text
sase bead issue open BEAD
sase bead issue attach BEAD ISSUE
sase bead issue create BEAD --request FILE
sase bead issue edit BEAD ISSUE --request FILE
sase bead issue set-state BEAD ISSUE open|closed
```

This belongs under `bead`, because the operation is selected from and may atomically
update a bead's external reference. Provider-neutral issue mutation remains behind the
VCS provider boundary.

Opening a browser is the clearest candidate to stop being a Proc: it is a local UI
effect, not durable work. If strict one-for-one migration is required,
`sase bead issue open` can resolve and open the URL as a detached proc, but doing so
adds a noisy durable row with little recovery value.

### Updates and plugin management (ten producer sites)

| Current proc                                       | Recommended command                                                     | Status                                                                            |
| -------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| install one plugin                                 | `sase plugin install NAME --json`                                       | Existing                                                                          |
| install marked plugins                             | `sase plugin install NAME... --json`                                    | Extend existing command to accept multiple names atomically                       |
| update plugin                                      | `sase plugin update NAME --json`                                        | Existing                                                                          |
| uninstall plugin                                   | `sase plugin uninstall NAME --json`                                     | Existing                                                                          |
| update agent CLIs                                  | `sase agent-cli update NAME...` or `--all`                              | Existing; add JSON result parity where needed                                     |
| managed SASE update                                | `sase update --json`                                                    | Existing                                                                          |
| editable checkout update                           | `sase update --to dev --yes --json` or a dedicated `--refresh-dev` mode | Mostly existing; preserve the dev journal                                         |
| combined editable + managed update                 | `sase update --to dev --yes --json` with one planned request            | Extend so one command owns both legs and one receipt                              |
| install-mode switch                                | `sase update --to MODE --yes --json` (`MODE` is `dev` or `pypi`)        | Existing                                                                          |
| comprehensive SASE + agent CLI + agent-repo update | `sase update --comprehensive --json`                                    | New high-level mode, internally invoking the three domain services in one command |

ACE's completion watcher may restart ACE after a successful changed result. The command
itself must write the pending update receipt before returning, so losing the TUI
callback cannot lose durable completion state.

### Prompt/config post-write work and commit fetching (five producer sites)

| Current proc                                   | Recommended command                                                            | Notes                                                                                                                   |
| ---------------------------------------------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| xprompt/config single-file commit-pull-push    | `sase repo publish --repo REF --path PATH --message-file FILE`                 | New shared sidecar/linked-repo operation; do not misuse Patch/stitch creation for a simple already-prepared config file |
| ordered commit/apply/custom post-write actions | `sase repo publish --request FILE` or a domain-specific xprompt/config wrapper | One detached command owns the full ordered sequence; arbitrary existing argv may be submitted directly                  |
| append prompt stash entry                      | `sase prompt stash append --request FILE`                                      | New; accepts the versioned stash wire and returns the new snapshot/counts                                               |
| force-fetch Commit timeline                    | `sase stitch list --fetch --format json ...`                                   | Existing and already returns the surface-neutral `VcsLogResult` data                                                    |

`sase repo publish` is preferable to `sase proc commit-file`: the behavior is a
repository mutation and should be independently usable. It is also preferable to raw
`sh -c 'git add && git commit && ...'`, because the current implementation has git
index-lock recovery, non-interactive environment handling, and structured failures.

Prompt stash persistence is another candidate for declassification if it is only a fast
local append. If it remains visible in Proc history, it needs the command above;
otherwise use an ordinary non-durable `asyncio.to_thread`/Textual worker and remove it
from the Procs pane.

### Axe background command launch (one producer site)

The current proc cleans/checks out a workspace and then starts a _second_ legacy
background-command daemon in one of nine slots. Keeping both layers after the Proc
migration would be redundant.

Add `sase workspace exec --project NAME --workspace N [--patch NAME] -- COMMAND...`. ACE
can submit that argv as the detached proc; the command claims/cleans/checks out the
workspace and then `exec`s or waits for the requested command in the proc's supervised
process group. The Procs pane becomes the durable command UI, and the separate bgcmd
slot store can be retired in a later compatibility phase. If immediate retirement is too
broad, use `sase workspace bgcmd-start ...` as a transitional command, but do not make
`sase proc bgcmd` the long-term domain home.

## Operations worth reconsidering as Procs

The strict migration can command-back every current row, but it would preserve some
historical over-classification. The current tracked runtime is also a convenient way to
avoid blocking the Textual event loop, which does not mean every use deserves durable
global execution.

Review these before adding commands solely for parity:

- open external issue in the local browser;
- append a prompt stash entry;
- small agent directive writes (auto, wait, rename, tribe);
- notification mute/snooze mutations;
- fast bead mutations that already complete under a locked local transaction.

The rule should be: use a Proc when work is materially long-running, must survive ACE,
benefits from global inspection/kill, or launches subprocess/network/VCS work. Use a
plain Textual/async worker for short UI-support I/O. This still achieves “no attached
Procs”: the remaining workers are explicitly not entered into the Proc store or Procs
pane.

## Migration sequence

1. **Land `sase-lh` first.** Base this work on canonical Proc names and schema 2; do not
   collide with its package/module/CLI renames.
2. **Add detached runtime primitives.** Implement atomic dedup/exclusive scopes,
   immutable `command`, mutable `active_command`, request/result sidecars, the
   cross-process reporter, and the ACE completion watcher. Keep old TUI procs working.
3. **Make existing commands proc-ready.** Standardize noninteractive/JSON/result
   behavior for gate, launch, plan, bead, monitor, plugin, update, agent-cli, agent
   sync, stitch list, revert, and restore commands.
4. **Add missing domain commands.** Patch lifecycle first, then agent
   lifecycle/directives, notification mutations, bead issue operations, repo publish,
   prompt stash, and workspace exec.
5. **Migrate ACE by domain.** Replace closures with argv and request payloads. Migrate
   low-callback operations first; migrate typed-preview and restart flows after the
   result watcher is proven. Preserve durable effects inside commands and leave only UI
   refresh/toast behavior in callbacks.
6. **Collapse ownership and CLI scope.** Make `sase proc run` always detached, remove
   session ownership/filtering and the redundant flags, stop writing `command`/`tui`
   kinds, and retain legacy-read rendering.
7. **Retire the attached runtime.** Delete `ProcQueue`/`ProcMirror` callable execution,
   TUI-only kill routing, and the `tui` kind after the overlap window. Keep ordinary
   Textual workers clearly named as workers, not Procs.
8. **Consider retiring bgcmd slots.** Once workspace commands are ordinary procs, merge
   their UI into the Procs surface and remove duplicate lifecycle state.

Patch commands and other shared domain behavior must respect the repository's Rust-core
backend boundary. Presentation-only callback/watch state stays in Python/Textual.

## Verification and acceptance criteria

The migration is complete when all of the following are true:

- every newly created Proc has a non-empty immutable command before its store append;
- no ACE Proc execution path accepts a Python callable;
- quitting or crashing ACE does not stop an ACE-submitted proc;
- every active proc can be killed through `sase proc kill` from any surface;
- two ACE instances cannot race past the same `dedup_key` or overlapping exclusive
  scope;
- command phase, active child command, logs, exit status, and structured result remain
  inspectable without the submitting ACE;
- losing the completion callback loses only ephemeral UI feedback, never a durable
  mutation, receipt, notification response, chained action, or workspace release;
- `sase proc run -- COMMAND` is global and detached without a flag;
- canonical help has no run `--detached` or `--session`, and no visibility control
  implies session ownership;
- legacy `command`, `tui`, and `detached` rows remain readable, with orphaned active TUI
  rows reconciled deterministically;
- a static inventory test rejects any new `_submit_tracked_proc(callable)`-style API;
- integration tests cover ACE-exit survival, cross-TUI dedup, result delivery, preview
  flows, accept-with-mail chaining, updater restart/receipt behavior, and workspace
  claim release after success, failure, kill, and supervisor crash.

Run the exhaustive repository verification lane and visual snapshots because the change
crosses core wire/store behavior, CLI parsers, ACE navigation and indicators, the Admin
Center Procs pane, update restart behavior, and many TUI snapshots.

## Main risks

1. **Duplicated mutations across TUIs.** This is why atomic core-backed dedup must land
   before globalizing producers.
2. **Lost typed results.** Parsing logs or relying on callbacks will fail on restarts;
   use result sidecars.
3. **Stale serialized state.** Request files should carry identifiers and user input;
   commands re-resolve live state and validate preconditions.
4. **Leaked sensitive input.** Descriptions, feedback, prompts, and gate inputs should
   not be argv or labels.
5. **Workspace leaks.** Commands—not ACE—must claim and release workspaces in `finally`
   paths, including kill handling.
6. **Update self-replacement.** The updater must durably write its receipt before the
   old process exits, while the watcher treats ACE restart as optional presentation.
7. **Proc history noise.** Blind one-for-one migration makes browser opens and tiny
   local writes global durable rows. Declassify work that does not meet the Proc bar.
8. **Mixed-version behavior.** Old ACE processes can still emit TUI rows during rollout;
   keep legacy reads and reconciliation until they are no longer live.

## Recommendation

Proceed with a separate detached-procs epic after `sase-lh`. Start with the proc runtime
contract and result/dedup primitives, then migrate command families. Do not begin by
removing `--detached`: that is the final visible simplification after every producer is
safe to run globally.

The architecture should make this invariant mechanically obvious:

```text
ACE interaction -> domain command argv + optional request JSON
                -> detached Proc supervisor
                -> domain operation + durable result
                -> optional, non-owning ACE completion observer
```

That gives SASE one coherent Proc concept: durable, command-backed, globally visible,
supervisor-owned work that survives every submitting surface.
