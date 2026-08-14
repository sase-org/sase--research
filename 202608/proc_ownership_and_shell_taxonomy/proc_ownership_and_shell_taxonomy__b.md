---
create_time: 2026-08-14
updated_time: 2026-08-14
status: research
---

# Sase Shells: one taxonomy, one substrate, and no procs inside ACE

**Research question.** How should SASE (a) eliminate procs that run inside the ACE TUI
process, make every proc supervisor-owned and detached, and remove `-d|--detached` from
`sase proc run`; (b) merge monitors into procs via a new `--shell <name>` option on
`sase proc`, with `sase monitor` wrapping that functionality at the service level; and
(c) adopt the proposed taxonomy — **agent lane → sase agent**, plus the new terms
**agent shell**, **proc shell**, and **sase shell**?

**Snapshot.** Verified against `sase` at `191e9f219` on 2026-08-14, the linked
`sase-core` checkout, the live proc store at `~/.sase/procs/procs.jsonl` (101 rows), and
the live agent index (`sase agent list -a`, 75 rows). Both prerequisite epics have every
phase closed and sit on their land bead: `sase-lh` (task → proc rename) and `sase-kp`
(`sase monitor`).

**Related work.** Extends
[`detached_proc_convergence`](../detached_proc_convergence/detached_proc_convergence.md)
and [`sase_shell_named_procs`](../sase_shell_named_procs/sase_shell_named_procs.md).
Both were written on 2026-08-13, before the `sase.procs` package landed; §0 records
every claim of theirs that is now stale, wrong, or newly confirmed. Also relevant:
[`monitor_command_substrate`](../monitor_command_substrate/monitor_command_substrate.md).

---

## Bottom line

1. **The three asks are one change, and the taxonomy is the enabling piece — land it
   first.** Every CLI surface the other two asks add (`--shell`, the agent-attachment
   option, the `sase monitor` facade) is named in the new vocabulary. Naming it first
   means writing it once.

2. **The taxonomy is not aspirational — the code already implements it.**
   `sase agent list -a` returns 75 rows, of which **33 carry
   `agent_family_role="monitor"`**. That command already lists *sase shells* (agent
   shells and proc shells together); it just has no word for what it is listing. Nothing
   in the taxonomy has to be built. It has to be *named*.

3. **Keeping `sase monitor` is better than the prior notes' plan to replace it with a
   `sase shell` command.** `sase_shell_named_procs` §8 proposed `sase shell` as the
   command. Under this taxonomy that name is taken by the *concept* — a sase shell is an
   agent shell **or** a proc shell — so a `sase shell` command that listed only proc
   shells would be actively wrong, and one that listed both would duplicate
   `sase agent list`. The user's plan (option on `sase proc`, `sase monitor` retained as
   a facade) avoids the collision, and it costs nothing to migrate: no `/sase_monitor`
   skill rename, no `sase/memory/build_and_run.md` rewrite, no stranded agent memories.

4. **`--shell NAME` should carry one resolution rule: the family separator qualifies
   it.** `--shell pc--check` names the shell `check` under sase agent `pc`;
   `--shell check` means "suffix `check` under the calling agent". That single rule
   spells today's behavior and the out-of-scope future direction identically, so the
   future change adds capability without changing syntax.

5. **A standalone proc shell is not a new record type — it is a sase agent whose only
   shell is a proc shell**, exactly as a solo agent is a sase agent whose only shell is
   an agent shell. That symmetry makes the future direction far cheaper than it looks.
   It also puts it **on the critical path**: §3.4 shows the TUI-proc migration needs
   store-wide dedup, dedup is the shell name, and ACE is not an agent — so ACE's procs
   must be able to be shells without a starting agent. Out of scope for this note, but
   not out of scope for the sequence.

6. **"Wrap this functionality at the service level" is the exact phrase that invites the
   two wrong implementations.** Both prior notes warned about them and the warning is
   worth restating verbatim: `sase monitor` must not spawn `sase proc run` and parse its
   JSON, and the proc supervisor must not run `sase monitor _run` as its child. §2.4.

7. **Removing `-d|--detached` is nearly free once `tui` collapses, and it forces one
   deliberate behavior change** in list scoping that must be made on purpose. §3.2.

---

## 0. What changed since the 2026-08-13 notes

The user flagged that the prior notes contain obsolete assumptions. They do. Here is
every load-bearing claim, re-checked at `191e9f219`.

| Prior claim | Status today | Evidence |
| --- | --- | --- |
| Python package is `sase.tasks`; store at `~/.sase/tasks/tasks.jsonl` | **Stale.** `src/sase/tasks/` no longer exists; `src/sase/procs/` (9 modules, 1,621 lines) and `~/.sase/procs/procs.jsonl` are live | `ls src/sase/procs`, `sase proc list` |
| `PROC_WIRE_SCHEMA_VERSION` is checked for **exact equality**, so any field addition is a hard coordinated bump | **Wrong now.** Python checks membership in `SUPPORTED_PROC_WIRE_SCHEMA_VERSIONS = {1, 2}` | `src/sase/procs/models.py:11-12,274` |
| "Plan a v3 bump and *while bumping*, relax the exact-equality check" | **Already done.** The relaxation landed with `sase-lh.2`; a v3 addition is now a set entry, not a cutover | same |
| `sase-lh` phases 2–8 in progress | **Stale.** All 8 phases closed; epic on `sase-lh.land` | `sase bead show sase-lh` |
| `sase-kp` all 12 phases closed, sitting on land | **Still true** | `sase bead show sase-kp` |
| 274/278 (98.6%) of TUI rows have `command: []` | **Confirmed, tighter.** 101 rows, **all** `kind=tui`, **99 with empty command (98.0%)**. There is not one `command` or `detached` row in the live store | §3.1 |
| ~54 producer sites across 37 files | **Recount: 41 references across 30 files** — 16 direct calls, 24 duck-typed `getattr` submitters, 1 definition. The `sase-lh.4` rename consolidated several wrappers | §3.3 |
| `kill` proc: median 144 s, max 1232 s | **Worse.** median **152 s**, max **1679 s** (28 minutes) | §3.5 |
| `_ListScope.matches()` returns `True` for every `kind == detached` row; unattributed rows depend on `include_unattributed` | **Confirmed verbatim** | `src/sase/main/proc_handler.py:82-89` |
| `_validated_argv` enforces non-empty argv on the submit path only; the Rust store does not require `command` | **Confirmed** | `src/sase/procs/runner.py:337-341` |
| `kill_proc()` refuses TUI rows | **Confirmed** | `src/sase/procs/runner.py:226-229` |
| Retention runs inside `append_proc` and `prune` deletes logs | **Confirmed** | `src/sase/procs/store.py:85`; `procs.history_limit: 100` in `default_config.yml:52` |
| `delete_proc_logs` recomputes the path from the id and ignores the row's `log_path`, so an artifacts-dir log is already prune-proof | **Confirmed** — the §5 "cheap resolution" still works | `src/sase/procs/logs.py:71-82` |
| Log module is id-driven, so readers need to become path-driven | **Half done.** `runner.py:203` already reads `proc.log_path`; `open_proc_log()` and `read_proc_log_tail()` still recompute from the id | `src/sase/procs/logs.py:29,59` |
| `monitor/supervise.py` is strictly stronger than the proc supervisor on every axis | **Still true**; monitor is 21 modules / 4,147 lines with 4,843 lines of tests, procs is 9 modules / 1,621 lines | `wc -l` |
| 31 `pub monitor_*` fields on the Rust `agent_scan` wire | **Confirmed exactly 31** | `sase-core/crates/sase_core/src/agent_scan/wire.rs` |
| CLI cold start ≈0.31–0.43 s bare, 0.62–0.64 s for a real subcommand | **Faster now:** 0.29 s bare parse, 0.51 s for `sase proc list -n 1`. Budget ~0.5–1.0 s of dead time per detached proc | measured 2026-08-14 |

Two further facts neither note recorded, both of which matter here:

- **`--shell` is completely free.** There is no `--shell` option anywhere in the CLI and
  no code reads `$SHELL`. Zero collisions.
- **Family child-suffix allocation already exists and is locked.**
  `allocate_agent_family_child_suffix(base_name, template)`
  (`src/sase/plan_chain.py:466`) is what mints `--mon`, `--mon-0`, `--mon-1`
  (`src/sase/monitor/naming.py:38-48`). Naming a proc shell does not need a new
  allocator.

---

## Part I — The taxonomy

### 1.1 The four terms, and the sentence that makes them work

| Term | Means | Today's spelling |
| --- | --- | --- |
| **Sase Agent** (agent) | An agent family, or a single agent that does not belong to one | "agent lane" |
| **Agent Shell** | One concrete agent, whether or not it belongs to a family | *(no term)* |
| **Proc Shell** | One named, supervised proc that belongs to a sase agent | "sase monitor" |
| **Sase Shell** (shell) | An agent shell or a proc shell | *(no term)* |

The sentence that ties them together, and the one worth putting at the top of the
glossary entry:

> **A sase agent is a sequence of sase shells.**

That is not a new model. It is a literal description of `src/sase/monitor/member.py` +
`src/sase/plan_chain.py`: a family container holds strictly sequential members, and a
monitor is a member with `agent_family_role="monitor"`. The taxonomy's whole contribution
is that it lets you *say* this.

It also resolves the metaphor problem in the current glossary. Today's entry says "we
think of an agent lane like an agent's house" — but the thing being renamed to *agent*
is the house, which leaves the occupant unnamed. Under the new terms the sase agent is
the identity and the shell is the body it wears for one run: **one agent, many shells
over time**, hermit-crab style. The old house metaphor should be retired with the old
word.

### 1.2 The code already agrees

Three independent confirmations, all measured today:

```
$ sase agent list -a -j | …
total 75  monitors 33
roles: {'monitor': 33, None: 23, 'root': 19}
  sase-m4.6_1--mon   failed     MONITORED     monitor
  01u--mon           completed  EPIC CREATED  monitor
  sase-m4.6--mon-0   failed     MONITORED     monitor
```

1. **`sase agent list` already lists sase shells.** 44% of its rows are proc shells. It
   does not list sase agents at all — `pc` never appears, only `pc--code`, `pc--mon`.
2. **A proc shell already has an agent name.** `sase-m4.6--mon-0` is a shell name in the
   existing agent-name namespace, resolvable by `sase agent show`.
3. **The monitor CLI already resolves all three levels.** `sase monitor show` accepts a
   "Monitor id (or unique prefix), member agent name, or lane name"
   (`src/sase/main/parser_monitor.py:136`) — id, shell, sase agent.

The taxonomy is therefore a **documentation-and-identifier** change, not an
architectural one. That is the single most important thing to know when sizing it.

### 1.3 "Lane" has five meanings in this repo — that is the real bug

`lane` appears **1,397 times across 146 files** in `src/`, 227 test files, and 27 doc
files. But a rename cannot be mechanical, because the word carries at least five
unrelated senses:

| Sense | Example | Rename? |
| --- | --- | --- |
| **Agent lane** | `agent_lanes.py`, `--lane`, `MonitorLaneError`, `lane_neighbors` | **yes** |
| AXE / lumberjack chop lane | `LANE_CHOP_TIMEOUT_SECONDS`, "Create a new scheduled lane" | no |
| Scoped-test lane | `sase/memory/build_and_run.md`: "a diff-scoped test lane" | no |
| ACE detail-panel display lane | `SASE CONTEXT / BEAD` lane, `COMMITS` lane, `PLAN` lane | no |
| Launch-override / mutation lane | `_override_pill.py` "the `default` launch lane" | no |

`docs/ace.md` alone contains both sense 1 and sense 4 — line 871 ("keyed on the name a
row presents as its **lane** name") and line 1061 ("a `PLAN` lane beside its task `BEAD`
lane") are 190 lines apart and mean unrelated things. This is precisely the confusion the
user identified, and it argues the rename *improves* the other four senses too: once
agent lanes are gone, "lane" unambiguously means a row or a scheduling track.

**Rust is nearly untouched:** only 33 occurrences of `lane` in the whole
`sase_core` crate. This rename is a Python + docs change.

### 1.4 "Shell" is the right word, with one liability

In its favor: one syllable; composes cleanly (`agent shell` / `proc shell` /
`sase shell`); completely unused in the codebase; and it inherits an accurate
connotation — a shell is a container for one occupant's run.

Alternatives considered and rejected: *agent instance* / *agent run* (`sase run` already
exists; "run" is overloaded), *family member* (meaningless for a solo agent — which is
the exact gap being closed), *incarnation* / *avatar* (too cute for a CLI).

**The liability is real and worth pre-empting:** "shell" also means a command
interpreter, and proc shells will run their commands under one.
`sase_shell_named_procs` §4 recommends compiling a monitor's `-c 'string'` into
`["/bin/sh", "-c", "string"]` and persisting that argv — which is right — so the
question "which shell does the proc shell use?" *will* be asked. Three cheap mitigations:

- Name the future interpreter selector now, in docs, as `--interpreter` (never
  `--shell`), so the word is reserved.
- Have `--shell` **reject values containing `/`** with an actionable error
  (`--shell names a sase shell, not an interpreter; did you mean the command?`). A path
  is the only way a user can express the wrong mental model.
- Define the glossary entry in terms of identity, not execution: *a sase shell is one
  member of a sase agent*.

### 1.5 What the rename costs

Scoped to the agent-lane sense only:

| Surface | Work |
| --- | --- |
| `src/sase/agent_lanes.py` (151 lines) | Module + `AgentLaneRef` + `lane_ref_for_agent` / `lane_ref_for_lane_name` rename |
| `sase monitor` CLI | `-l/--lane` → `-a/--agent` on `start`, plus help text on `list`/`show`/`stop` (`parser_monitor.py:84,136,210,240,320`) |
| `src/sase/monitor/` | `MonitorLaneError`, `resolve_lane`, `default_lane`, `monitor_lane_lock_path`, `_resolve_lane_start` |
| ACE | `models/agent_lane_neighbors.py`, `actions/agents/_folding_lanes.py`, `lane_fold_level`, `lane_neighbors`, `lane_keys`, `lane_scale` |
| `agents_sync` | `lane_commits`, publication/inventory lane keys |
| Docs | `docs/agent_families.md` (27 hits), `docs/ace.md` (agent-lane hits only), `docs/monitors.md` (14) |
| Memory / skills | `sase/memory/glossary.md`, `src/sase/xprompts/skills/sase_monitor.md` (3 hits), then `sase memory init` |
| Rust | 33 occurrences total |

The `-l/--lane` → `-a/--agent` swap is the only public CLI break, and `-a` is free on
`sase monitor start` today.

### 1.6 Proposed glossary entries

Replacing **Agent Lane**, and adding three:

> **Sase Agent** — ALIASES: agent. A sase agent is either an agent family or a single
> agent that does not belong to a family; it is the identity that owns a sequence of
> sase shells. Sase agent names never end with `--<suffix>`, since that suffix belongs to
> the shells. When an agent is alone, the sase agent and its one agent shell share a
> name. When a second shell joins — which can only happen once the previous shell
> completes, because shells within a sase agent run sequentially — the original agent is
> renamed with its own `--<suffix>` and the bare name becomes the pure family container.
>
> **Sase Shell** — ALIASES: shell. A sase shell is one member of a sase agent: either an
> agent shell or a proc shell. A sase agent is a sequence of sase shells.
>
> **Agent Shell** — An agent shell is a single agent, which may or may not belong to an
> agent family. It is the concrete thing that runs, holds a workspace claim, and appears
> in `sase agent list`.
>
> **Proc Shell** — A proc shell is a named, supervised proc that is a member of a sase
> agent, with streaming output, a timeout, and an optional follow-up agent. A proc shell
> that belongs to an agent family is also called a **sase monitor** and is managed with
> `sase monitor`. See also [[Proc]].

`sase monitor` keeps its own entry, defined as *a lane-attached proc shell* — exactly
the narrowing the user anticipated, and it becomes true by construction the day
standalone proc shells ship.

### 1.7 The one tension: `sase agent list` lists shells

After the rename, "agent" means the container but `sase agent list` returns shells
(§1.2). Three options:

- **(a) Accept and document it.** An agent name may name a sase agent (`pc`) or one of
  its shells (`pc--code`), and commands resolve both — which `resolve_monitor_ref`
  already does. **Recommended:** zero churn, and it matches how people speak.
- (b) Add a grouping flag (`sase agent list --agents` vs the shell default). Cheap, but
  it invents a distinction users have not asked for.
- (c) Add a `sase shell` command later. **Do not** — §3 of the bottom line: that name is
  the concept's, and the command would either be wrong or redundant.

---

## Part II — `--shell <name>` on `sase proc`, and `sase monitor` as a facade

### 2.1 What `--shell NAME` means

Interpreting "a new `--shell <name>` option on the `sase proc` command" as: `--shell` on
`run` (create), `--shell` on `list` (filter), and name resolution on `show`/`kill`
(which already take a ref).

**One resolution rule, which is the design's load-bearing idea:**

| Value | Resolves to | Notes |
| --- | --- | --- |
| `pc--check` (contains `--`) | shell `check` of sase agent `pc` | fully qualified; needs no ambient agent |
| `check` (bare), called inside agent `pc` | shell `check` of sase agent `pc` | today's implicit-lane behavior |
| `check` (bare), no calling agent | **today:** error. **future:** a new sase agent whose only shell is `check` | one syntax, two eras |

This is what makes the future direction a capability addition rather than a syntax
change — and it is why the future direction is cheap: a standalone proc shell is not a
new record, it is a sase agent with one proc shell, structurally identical to a solo
agent with one agent shell.

**Constraints:**

- A shell name must be a valid agent-name component, because it *is* one. That gives
  namespace, uniqueness, and resolution for free from the existing registry and
  `allocate_agent_family_child_suffix`. It also means `:` (proposed in
  `sase_shell_named_procs` §3.2 as a free namespace) is **not** available — use `-`.
- Reject values containing `/` (§1.4).
- Reject values that are valid proc ids, so name-resolution and id-prefix resolution can
  never fight (`sase_shell_named_procs` §3.2, still correct).
- **Mutual exclusion is per sase agent, not per project.** `sase_shell_named_procs`
  recommended per-project name uniqueness; under this taxonomy the constraint falls out
  of the model instead — one active shell per sase agent, because a sase agent is
  sequential by definition. That is today's "one monitor per lane", derived rather than
  special-cased, and it is strictly better than a per-project rule (two projects, or two
  agents, running `just check-full` under the name `check` is normal and must work).

### 2.2 Short alias — the one wart

`cli_rules.md` requires a short alias for every public long option. `--shell` has no
good letter left:

| Candidate | Verdict |
| --- | --- |
| `-s` | **No.** `-s` is `--session` on both `sase proc run` and `sase proc list` today. Making it `--shell` on `run` only means `sase proc list -s deploy` silently filters by session. Worst possible outcome |
| `-H` | **No.** `-H` is `--full-help` at the top level (`parser.py:576`); reusing it subcommand-locally reads as help |
| `-N` | **Recommended.** Free on both `run` and `list`; mnemonic is "name of the shell"; uppercase shorts are established here (`-S/--status`, `-T/--tail-lines`, `-C/--cwd`, `-L/--label`) |

Note `-d` is freed on both subcommands by this work (§3.2) but has no mnemonic value for
`--shell`. Use `-N/--shell` uniformly and take the small mnemonic hit; a per-subcommand
divergence would be much worse.

Do **not** make `--shell` valueless-with-auto-allocation (`sase proc run --shell -- cmd`)
— `nargs="?"` immediately before a `--`-introduced remainder is an argparse edge case for
no benefit. Auto-allocation of the `--mon`-style suffix belongs to `sase monitor start`,
which is where it already lives.

### 2.3 What the proc surfaces gain

```bash
sase proc run -N deploy -- ./deploy.sh   # create a proc shell
sase proc show deploy                     # already takes a ref; add name resolution
sase proc kill deploy                     # same operation as `sase monitor stop`
sase proc list -N deploy                  # run history for one shell name
sase proc list                            # shells and unnamed procs in one table
```

The last line is the whole point of the merge: today there is **no single list of what is
running**. Proc shells (monitors) live in `agent_meta.json` + `done.json` with no store
row; procs live in the JSONL store with no lane. After the merge, `sase proc list` shows
everything and `sase agent list` shows every shell — two complete projections instead of
two partial ones.

### 2.4 `sase monitor` as a service-level facade — and the two wrong wrappers

`sase monitor` keeps its full surface (`-c/--command`, required `-r/--reason`, required
`-t/--timeout`, `-i/--idle-timeout`, `-n/--next`, `--next-output`, `-s/--start-status`,
`-S/--stop-status`, `-T/--tail-lines`, plus `-a/--agent` renamed from `-l/--lane`) and
implements it by **calling `sase.procs` functions directly**. Required reason and timeout
stay monitor-facade policy; `sase proc run -N` must not inherit them.

Restating both prior notes' warnings, because "wrap this functionality" is exactly the
phrasing that produces them:

- **Not a CLI wrapper.** `sase monitor start` must not `Popen(["sase", "proc", "run",
  "--json", …])` and parse the envelope. That buys a second interpreter start
  (~0.5 s measured), an error-translation layer, output-ownership problems, and a
  CLI-to-CLI protocol that can skew across versions. "Powered by procs" means shared
  models, store, supervisor, and service functions — **one Python import boundary, two
  CLI facades.**
- **Not a wrapper process.** The shape `proc supervisor → sase monitor _run → user
  command` must be rejected. `sase proc kill` signals the child *group*, so it kills the
  wrapper and the user command together — and the wrapper is precisely the process
  responsible for releasing the workspace claim and launching or suppressing `--next`. It
  would die before it could settle. The proc supervisor owns the user command
  **directly**, and settlement is a closed set compiled into the supervisor, never a
  persisted code path.

And the substrate decision from `sase_shell_named_procs` §1.1 still holds and should be
re-affirmed rather than re-litigated: **promote `monitor/supervise.py` +
`supervisor_bootstrap.py` to the proc kernel and delete `procs/supervisor.py`.** There is
no axis on which the proc supervisor is better; it is smaller because it does less
(no double-fork reparenting, no start ack, no launch barrier, no dual timeouts, no
boot-aware process identity, no env scrubbing, and a reconciler that only flips status).
Two of those become mandatory the moment procs are agent-startable: reparenting (so a
PPID-walking `kill_agent_runner_group()` cannot collect the proc as collateral) and
identity-over-pid (`_supervisor_process_matches()` at `procs/runner.py:299` returns
`True` unconditionally on any platform without `/proc`).

### 2.5 Wire changes

Working from `ProcWire` (22 fields, `sase-core/crates/sase_core/src/procs/wire.rs:7-31`):

| Needed | Where |
| --- | --- |
| `command`, `cwd`, `label`, `status`, `phase`, `message`, `exit_code`, `pid`, `pgid`, timestamps, `log_path`, `project`, `workspace_num`, `cl_name`, `tags` | already present |
| shell-string execution | **no field** — persist `["/bin/sh","-c","…"]` as the argv; honest in `ps`, in the Procs pane, and in `sase proc list` |
| "settling, not yet terminal" | `phase`, already present |
| `shell_name`, `artifacts_dir`, `reason`, `supervisor_identity`, `timeout_seconds`, `idle_timeout_seconds` | **six new nullable fields** |
| `request_fingerprint` | proc row (idempotent replay is now a proc-level rule) |
| `start_status`/`stop_status`, `next_action`/`next_output`/`tail_lines`, follow-up disposition, starter/follow-up agent | **stay in `agent_meta.json`** — meaningless without a sase agent |

Schema **v3**, added to `SUPPORTED_PROC_WIRE_SCHEMA_VERSIONS` rather than swapped in
(§0). Roughly half of the Rust `agent_scan` wire's **31 `pub monitor_*` fields** —
command, cwd, state, exit code, pgid, supervisor identity, output path, timeouts — become
proc-row fields and leave the scan wire: a real reduction, not a relocation. Rename the
survivors `shell_*` with serde aliases, in the documentation phase, not the wire phase.

### 2.6 Two records, one writer, one ordering rule (carried forward, re-verified)

A proc shell has a proc row *and* an artifacts member. `sase_shell_named_procs` §5 and §7
specify this correctly and both of their key mechanics still verify at HEAD:

- **Ownership split, never duplicated.** Proc row owns execution (`status`, `phase`,
  `exit_code`, `pid`, `pgid`, timestamps, `log_path`, `supervisor_identity`,
  `shell_name`, argv, cwd). Artifacts markers own lineage and presentation (custom status
  labels, family membership, `done.json`, chat history, follow-up disposition). One
  immutable cross-link each way.
- **One ordering rule**, so `proc.status` terminal ⇒ fully settled:
  `phase="settling"` → release/transfer the claim → launch/degrade/suppress the follow-up
  → write `agent_meta` terminal + `done.json` → `status` terminal. This retires
  `MonitorRecord.is_terminal`'s two-field check and fixes the known claim-release race —
  which is still recorded live on `sase-kp` and should be confirmed cleared *before* the
  move, so a pre-existing flake is not mistaken for a migration regression.
- **The retention trap is real and the cheap fix still works.** `append_proc` calls
  `delete_proc_logs(pruned)` on every append (`store.py:85`) with
  `procs.history_limit: 100` (`default_config.yml:52`) — and the live store is sitting at
  exactly 101 rows, so this fires constantly. But `delete_proc_logs` recomputes
  `proc_logs_dir()/<id>.log` from the id and ignores the row's `log_path`
  (`logs.py:71-82`), so a log written into the artifacts dir is already prune-proof.
  Keep attached proc-shell logs at `monitor_log_path(artifacts_dir)` as they are today,
  and finish making the readers path-driven: `runner.py:203` already honors
  `proc.log_path`; `open_proc_log()` and `read_proc_log_tail()` (`logs.py:29,59`) still
  recompute from the id.

---

## Part III — No procs inside ACE, and no `--detached`

### 3.1 The premise, re-verified today

```
~/.sase/procs/procs.jsonl — 101 rows
  kind=tui       101 rows  →  99 with command: []   (98.0%)
  kind=command     0 rows
  kind=detached    0 rows
```

Stronger than the prior note's finding: **every proc on this host right now is a TUI
proc.** The interface is designed around Python callables — `_submit_tracked_proc` takes
a `Callable[..., TrackedProcResult[T]]` (`ace/tui/actions/proc_actions.py:151-163`) — and
`command` is best-effort display metadata written from inside the worker *after*
submission. A command must be invented for ~98% of procs; there is nothing to reuse.

### 3.2 Removing `-d|--detached`

`--detached` is already a misnomer: `sase proc run` starts an OS-detached supervisor with
or without it (`_SUPERVISOR_OWNED_KINDS` contains both `command` and `detached`,
`runner.py:41`), and the flag only decides *attribution* — its own help says "Make the
proc global instead of attributing it to a session". `submit_proc` and
`submit_detached_proc` differ in exactly two ways: `kind`, and whether `origin` is
required (`runner.py:52-111`).

So the removal is: `-d` becomes exactly `--session none`, which already exists and stays.
Two consequences to decide deliberately:

1. **One behavior change is forced.** `_ListScope.matches()` keeps every
   `kind == detached` row in scope for every query, while a session-less non-detached row
   appears only when `include_unattributed` is set — which is false when the user passes
   an explicit `--session <other>` (`proc_handler.py:82-89`). After the collapse
   "detached" and "unattributed" are the same thing, so **`include_unattributed` must
   become unconditional**, or `sase proc list --session <other>` stops showing global
   procs.
2. **`-d/--detached` should leave `sase proc list` too**, where it is documented as
   "shorthand for `--kind detached`". Once `tui` is gone and `command`/`detached`
   collapse, `kind` carries no information. Keep `--kind` readable for legacy rows during
   a compatibility window; drop the shorthand.

Prefer a one-release rejection with an actionable message ("all procs are detached;
remove `--detached`") over a bare argparse error — agents carry the old invocation in
memory files and chat history.

**Keep `--session` on `run`.** `detached_proc_convergence` §9 recommended dropping it
too; that is a second, unrequested removal that also changes the default from
`current → latest → none` to unattributed. Attribution is still meaningful (it decides
which ACE session's Procs tab shows and counts the row), and keeping it costs nothing.

### 3.3 The producer inventory, recounted

41 references across 30 files under `src/sase/ace/`:

| Reference kind | Count |
| --- | --- |
| Direct `_submit_tracked_proc(` / `_submit_background_proc(` calls | 16 |
| Duck-typed `getattr(app, "_submit_*", None)` submitters | 24 |
| Definition | 1 |

The 24 duck-typed submitters matter for enforcement: a static test asserting "no proc
execution path accepts a callable" must match the `getattr` string pattern, not just
resolve call targets. This pattern also means the TUI silently no-ops if the mixin is
absent.

The buckets from `detached_proc_convergence` §2 survive the rename intact (patch
workflow, agent lifecycle, notification/gate/launch, bead operations, plugin/environment
maintenance, and the should-not-be-procs group), as does its conclusion that the commands
belong in the existing domain groups (`sase patch`, `sase agent`, `sase bead`,
`sase notify`, `sase workspace`, `sase run`) rather than a `sase ace` namespace or a
generic payload dispatcher. Nothing found today changes that analysis; it is not repeated
here.

### 3.4 The dependency the taxonomy exposes

`detached_proc_convergence` §3.2 identifies store-wide dedup as a hard prerequisite:
ACE's `dedup_key` and `exclusive_scopes` are in-memory and scoped to one TUI process
(`proc_actions.py:151-163`), so globalizing producers without store-wide exclusion lets
two ACE instances race the same Patch mutation or package update.
`sase_shell_named_procs` §3.1 answers it: the name *is* the dedup key. One field, two
features.

Under this taxonomy that answer has a consequence worth stating plainly:

> **A name makes a proc a shell. A shell belongs to a sase agent. ACE is not an agent.**

So ACE's migrated procs need to be shells with no starting agent — i.e. the FUTURE
DIRECTION. It is out of scope for this note, as requested, but it is **not** out of the
sequence: it is a prerequisite for eliminating TUI procs safely. Three ways forward:

- **(a) Pull the no-agent case of standalone proc shells into the shell-merge epic.**
  Recommended. §2.1 makes it nearly free: `sase proc run -N patch-sync-sase-abc` mints a
  sase agent whose only shell is that proc shell. The only genuinely new capability is
  creating a sase agent from nothing — `resolve_lane()` (`monitor/store.py:69-81`) raises
  today when a lane has no pre-existing artifacts. That is mint a name, create the
  artifacts dir, write `agent_meta` with the proc-shell role: no starter to kill, no
  claim to transfer, no follow-up.
- (b) Defer it and give ACE procs a plain `dedup_key` field separate from `shell_name`.
  Two mechanisms for one job — precisely what `sase_shell_named_procs` §3.1 argued
  against.
- (c) Defer both, and accept that cross-TUI races remain until standalone shells land.
  Acceptable only if the TUI migration is explicitly sequenced after them.

This also unlocks the payoff the user already anticipated: once a proc shell is a sase
agent's member, `%wait` and `#fork` see it, so xprompt directives that make procs wait on
agents (or vice versa) need no new machinery.

### 3.5 What should stop being a proc at all

Fresh timings from the live store (n = completed rows with both timestamps):

| Type | n | Median | Max |
| --- | --- | --- | --- |
| `kill <patch>` | 10 | **152.1 s** | **1679.3 s** |
| `kill/dismiss N agents` | 3 | 146.2 s | 177.8 s |
| `comprehensive update` | 11 | 4.7 s | 95.7 s |
| `Plan response: tale` | 16 | 4.3 s | 6.2 s |
| `launch <project>` | 13 | 1.7 s | 71.1 s |
| `Stash prompt` | 3 | **0.09 s** | 0.11 s |

Against ~0.5–1.0 s of detached-proc startup (supervisor interpreter + `sase …` child,
measured 2026-08-14), the decision rule from `detached_proc_convergence` §4 holds and the
data sharpens both ends of it:

- The 28-minute `kill` proc is the strongest possible argument *for* the migration: it is
  the highest-volume type, it holds a half-applied transaction, and today it dies with the
  TUI and `sase proc kill` refuses to touch it (`runner.py:226-229`).
- `Stash prompt` at 90 ms is a ~10× latency regression for no benefit. It should become a
  plain `run_worker(thread=True)` with no store row — which still satisfies "no procs run
  inside ACE", because the remaining workers are simply never procs.

`Plan response: tale` (16 rows, 4.3 s median) is a type neither prior note inventoried;
it sits above the threshold and should migrate.

---

## Sequencing

Three epics, in this order. The ordering differs from both prior notes in one respect:
**the taxonomy goes first and alone.**

**Epic A — Taxonomy (small–medium).** Rename agent lane → sase agent; introduce sase
shell / agent shell / proc shell; `-l/--lane` → `-a/--agent`; glossary, docs,
`sase_monitor` skill, `sase memory init`. Behavior-preserving. Land it fast, immediately
after `sase-lh` and `sase-kp` close, so all terminology churn lands in one window rather
than being spread across three epics — and so every surface Epics B and C add is named
correctly from birth.

**Epic B — Proc shells (large).** Roughly `sase_shell_named_procs` §10, re-keyed:

| Phase | Work |
| --- | --- |
| 1 | Rust: six additive `ProcWire` fields, schema v3 (set addition), **atomic reserve-or-return** under the store lock |
| 2 | **Kernel:** promote `monitor/supervise.py` + `supervisor_bootstrap.py`; delete `procs/supervisor.py`. **Ship alone and let it soak** — it changes execution for `command`/`detached` procs only, not `tui` |
| 3 | Named shells: `shell_name`, the §2.1 resolution rule, per-sase-agent active uniqueness, fingerprint replay, `sase proc run -N` |
| 4 | Attachment: move `member`/`claims`/`followup*`/`settlement`/`transaction` behind an `artifacts_dir`-conditional path; §2.6 ordering; path-driven logs |
| 5 | `sase monitor` becomes the service-level facade; TTY refusal with an actionable message |
| 6 | Collapse epic launch's monitor/detached-proc fork (`bead/epic_launch.py:120-190`) into one call |
| 7 | *(recommended, §3.4a)* standalone proc shells: mint a sase agent with no starter |
| 8 | ACE: proc shells in the Procs pane; Agents-tab rows re-keyed on the proc row |
| 9 | Docs, memory, glossary follow-through; `shell_*` scan-wire rename with serde aliases |

Migrate `tests/monitor/` (4,843 lines) rather than rewriting it — those tests are the
record of which defects the `sase-kp` and `sase-ku` hardening was written against.

**Epic C — No attached procs (large).** `detached_proc_convergence` §8 phases 2–7,
unchanged in substance: free wins (gate/launch/bead) → Patch workflow → plugins and
environment → agent lifecycle → collapse ownership and remove `-d` → retire the callable
runtime (`TUI_PROC_KIND`, the `kill_proc` refusal, the `_ListScope` special case,
`PROC_KIND_CHOICES`, Rust `PROC_KINDS`). Domain functions must move out of `ace/handlers`
and `ace/tui/actions` into surface-neutral services — a CLI handler must never import a
TUI action module — and into `sase-core` where the boundary rule applies.

Epic C depends on Epic B phases 1–4 and 7. Epic B phase 5 does not block it.

---

## Risks

1. **Naming fatigue.** Within about six weeks SASE will have had *task → proc*,
   *monitor → proc shell*, and *lane → sase agent*. The glossary entries are not
   optional, and `sase monitor` must stay working the whole time. Keeping the command
   (rather than the prior notes' `sase shell`) is the single biggest mitigation
   available.
2. **`--shell` read as an interpreter selector.** §1.4. Cheap to mitigate, embarrassing
   to skip.
3. **Epic B phase 2 changes execution for existing procs.** Every `sase proc run`, epic
   launch, and bead-work launch starts going through a different supervisor. Land it
   alone behind `just check-full`; keep the old module importable for one release so
   bisecting is cheap.
4. **A name is a lock.** Per-sase-agent active uniqueness means a wedged shell blocks the
   next start under that name. `sase monitor stop` / `sase proc kill` and the reconciler
   must be reliable enough to clear it, and the collision error must name the blocking
   row and the exact command to inspect it — as `_active_monitor_message()` already does.
5. **Dual-record divergence** for attached shells. Test it directly: kill the supervisor
   between each pair of §2.6 ordering steps and assert both records agree afterwards.
6. **Log destruction on prune** (§2.6) if attached-shell logs move to the global proc log
   dir. Silent, data-losing, easy to miss in review. The live store sitting at exactly the
   100-row limit means this fires on essentially every append.
7. **In-flight monitors across the cut-over.** Never adopt a live monitor's process group
   into a new proc record — pid, claim, barrier, and settlement ownership cannot be
   transferred after the fact. Let running supervisors finish under the code they loaded,
   and keep the reconciler able to settle a member with no proc row.
8. **Losing a completion callback must lose only ephemeral UI feedback** — never a durable
   mutation, receipt, gate response, chained action, or workspace release. If ACE exits
   before completion, reopening must reconstruct correct state from disk.
9. **Blind bucket-6 migration** turns 90 ms writes into durable global rows and a Procs
   pane nobody can read.

---

## Open decisions

1. **Does `sase agent list` keep listing shells under the new names?** §1.7 recommends
   yes, documented. *(This is the only decision that changes what a user types daily.)*
2. **Does the standalone-proc-shell case get pulled into Epic B phase 7, or does Epic C
   wait for a fourth epic?** §3.4 recommends pulling it in.
3. **`-N/--shell`, or a different short alias?** §2.2. `-s` must be rejected regardless.
4. **Does `sase monitor` narrow to "attached proc shells" immediately, or only once
   standalone shells exist?** Recommend: define it narrowly in the glossary from day one,
   since it is true today by construction.
5. **`sase agent kill` collision.** Existing verb = SIGTERM a running agent shell; Epic
   C's migrated `kill` proc persists a kill/dismiss *transaction*. Distinct verb
   (`sase agent cleanup`) or a deliberate flag-based merge?
6. **Escape-hatch budget for a hidden `sase proc exec --payload` dispatcher** in Epic C —
   approve at most N proc types, or forbid it?
7. **Legacy `tui` rows** — migrate in place, leave readable-but-unwritable, or drop at
   kind removal? The Rust store rejects unknown kinds on write, so read-side behavior for
   pre-existing rows needs an explicit decision.

---

## Recommended solution

**Land three epics in this order, and do not merge the first into the second.**

1. **Adopt the taxonomy first, as a standalone behavior-preserving epic.** Rename agent
   lane → **sase agent**; add **sase shell** = **agent shell** | **proc shell**; anchor
   the glossary on *a sase agent is a sequence of sase shells*; rename `-l/--lane` to
   `-a/--agent`; retire the "house" metaphor. Rename only the agent-lane sense of
   "lane" — the AXE, test, display, and launch senses stay and become *less* ambiguous.
   Rust is 33 occurrences; this is a Python-and-docs change. Doing this first means every
   surface below is named once.

2. **Merge monitors into procs by making a proc shell a named proc that is a member of a
   sase agent.** Concretely:
   - Add `--shell NAME` (short `-N`) to `sase proc run` and `sase proc list`, with the
     §2.1 rule: a value containing `--` fully qualifies the sase agent, a bare value is a
     suffix under the calling agent. A shell name must be a valid agent-name component,
     must not look like a proc id, and must not contain `/`.
   - Derive mutual exclusion from the model — one active shell per sase agent — rather
     than inventing a per-project name lock.
   - Add six nullable `ProcWire` fields (`shell_name`, `artifacts_dir`, `reason`,
     `supervisor_identity`, `timeout_seconds`, `idle_timeout_seconds`) at schema **v3**,
     which is now a set addition, plus an atomic reserve-or-return under the store lock.
   - **Promote `monitor/supervise.py` to the proc kernel and delete
     `procs/supervisor.py`.** Ship that phase alone. Double-fork reparenting, start ack,
     launch barrier, boot-aware identity, dual timeouts, env scrubbing, and full
     reconciliation become properties of every supervised proc.
   - Keep `sase monitor` as a **direct service-level facade over `sase.procs`** — not a
     CLI wrapper, not a wrapper process between the supervisor and the user command.
     Compile `-c '…'` to `["/bin/sh","-c","…"]` and persist that argv. Required
     reason/timeout stay facade policy.
   - Enforce one writer and one ordering rule so `proc.status` terminal ⇒ fully settled,
     retiring the `settled` boolean and the claim-release race with it.
   - Keep attached-shell logs inside the artifacts dir and finish making
     `open_proc_log()` / `read_proc_log_tail()` path-driven.
   - **Include the no-agent case of standalone proc shells** (§3.4a). It is nearly free
     under this taxonomy — a standalone proc shell is a sase agent with one proc shell —
     and it is what unblocks step 3.

3. **Then eliminate procs inside ACE and remove `--detached`.** Migrate the 41 producer
   sites in `detached_proc_convergence`'s bucket order, putting each command in its
   existing domain group (`sase patch`, `sase agent`, `sase bead`, `sase notify`,
   `sase workspace`, `sase run`) rather than a `sase ace` namespace or a generic payload
   dispatcher. Demote sub-second work (`Stash prompt`, 90 ms) to plain Textual workers
   with no store row. Use shell names as the store-wide dedup key. Then remove
   `-d|--detached` from `sase proc run` *and* `sase proc list`, make
   `include_unattributed` unconditional, keep `--session` on run, reject `--detached` for
   one release with an actionable message, and delete the callable runtime.

**The single decision that gates the sequence** is open decision #2: whether standalone
proc shells ride along in step 2. If yes, step 3 is unblocked and the whole plan is three
epics. If no, step 3 needs either a separate dedup mechanism it should not have, or a
fourth epic before it.

---

## Appendix — verification commands

```bash
# Store composition and command emptiness
python3 -c "import json,collections,os; rows=[json.loads(l) for l in open(os.path.expanduser('~/.sase/procs/procs.jsonl')) if l.strip()]; c=collections.Counter(r['kind'] for r in rows); print(len(rows), c, sum(1 for r in rows if not r.get('command')))"

# Shells already in the agent index
sase agent list -a -j | python3 -c "import json,sys,collections; d=json.load(sys.stdin); print(len(d), collections.Counter(r.get('agent_family_role') for r in d))"

# Producer inventory
grep -rn '_submit_tracked_proc\|_submit_background_proc' src/sase/ace/ | wc -l
grep -rn 'getattr(.*_submit_tracked_proc\|getattr(.*_submit_background_proc' src/sase/ace/ | wc -l

# The five senses of "lane"
grep -rIn '\blane\b' src/ --include='*.py' | grep -viE 'agent|monitor|family|member'

# Schema support set (no longer exact equality)
grep -n 'SUPPORTED_PROC_WIRE_SCHEMA_VERSIONS' src/sase/procs/models.py

# Retention deletes logs by recomputed id, not by row log_path
grep -n 'delete_proc_logs' src/sase/procs/store.py src/sase/procs/logs.py

# --shell is free
grep -rn '\-\-shell' src/sase/main/ ; grep -rn 'getenv("SHELL"' src/
```
