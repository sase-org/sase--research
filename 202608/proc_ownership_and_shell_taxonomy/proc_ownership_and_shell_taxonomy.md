---
create_time: 2026-08-14
updated_time: 2026-08-14
status: research
---

# Proc ownership and the sase shell taxonomy

**Research question.** What is the best way to (a) eliminate procs that run inside the
ACE TUI process, make every proc supervisor-owned and detached, and remove
`-d|--detached` from `sase proc run`; (b) merge sase monitors into sase procs via a new
`--shell <name>` option, with `sase monitor` wrapping that at the service level; and (c)
adopt the taxonomy **agent lane → sase agent**, plus **agent shell**, **proc shell**, and
**sase shell**?

**Snapshot.** Consolidated on 2026-08-14. Every claim below was re-verified against
`sase` at `5601920c9`, the linked `sase-core` checkout, and the live stores
(`~/.sase/procs/procs.jsonl`, `sase agent list -a -j`). Numbers taken from live stores
drift; the shapes do not.

**Sources.** This report merges two independent research reports and a third
verification pass:

- [`__a`](proc_ownership_and_shell_taxonomy__a.md) — `research.0k.cdx`, verified at
  `191e9f219`.
- [`__b`](proc_ownership_and_shell_taxonomy__b.md) — `research.0k.cld`, verified at
  `191e9f219`.

Both extend [`detached_proc_convergence`](../detached_proc_convergence/detached_proc_convergence.md),
[`sase_shell_named_procs`](../sase_shell_named_procs/sase_shell_named_procs.md), and
[`monitor_command_substrate`](../monitor_command_substrate/monitor_command_substrate.md),
all written 2026-08-13 against the pre-`sase.procs` tree.

---

## 0. Bottom line

1. **The taxonomy is a documentation-and-identifier change, not an architectural one.**
   `sase agent list -a` already returns a mixed list of agent shells and proc shells —
   41% of its rows carry `agent_family_role="monitor"`. The model exists; it has no
   name. Land it first, alone, so every surface the other two asks add is named once.

2. **Identity and exclusion are two different fields, and conflating them is the one
   decision that would repeat today's `kind` mistake.** `__b` argues the shell name *is*
   the store-wide dedup key ("one field, two features"). That is not expressible:
   ACE's current exclusion is a **set with overlap semantics**
   (`requested & info.exclusive_scopes`), with a live call site claiming three scopes at
   once. `__a` is right — `shell_name` is identity, `concurrency_keys` is exclusion. §3.

3. **Consequence: standalone proc shells are *not* on the critical path.** `__b`'s chain
   ("dedup is the name → a name makes a proc a shell → a shell belongs to an agent → so
   ACE's procs need agent-less shells") breaks at the first link. ACE's migrated procs
   need concurrency keys, not names. Standalone shells stay a cheap, desirable *option*
   in the merge epic rather than a blocker for the TUI work. §3.4.

4. **The producer inventory in both reports is wrong.** `__a` says 53 sites / 37 files
   (carried forward without recounting); `__b` recounts to 41 / 30 but greps only
   `_submit_tracked_proc` and a method that **does not exist**
   (`_submit_background_proc`, 0 references). Both miss `_submit_proc` — a second public
   producer surface with 17 call sites across 7 files. The true figure is **56 call
   sites across 36 files**. §6.1.

5. **`-N/--shell`, not `-S/--shell`.** `__a` recommends `-S` after checking it against
   `sase monitor`'s `-S|--stop-status`. The collision it missed is in its own command
   group: **`-S` is already `--status` on `sase proc list`**. `-N` is free on `proc run`
   and `proc list`. §4.1.

6. **Timeouts must be integer milliseconds.** `ProcWire` derives `Eq`. `__b`'s proposed
   `timeout_seconds: Option<f64>` / `idle_timeout_seconds: Option<f64>` will not
   compile without dropping that derive — which is exactly why `AgentMetaWire`, which
   already holds those f64 fields, derives only `PartialEq`. `__a` is right. §5.3.

7. **Removing `tui` from `PROC_KINDS` silently destroys visible history.** Neither
   report states this precisely. `normalize_and_validate_proc` runs on **read** as well
   as append (`procs/store.rs:224`), and invalid rows are *skipped*. Every one of the
   101 live rows is `kind="tui"`. Delete the kind from the validator and the store reads
   as empty. §6.4.

8. **`sase monitor` stays.** Both reports independently reject the prior note's
   `sase shell` top-level command, for the same reason: under this taxonomy that name
   belongs to the *concept*, so the command would be either wrong (listing only proc
   shells) or redundant (duplicating `sase agent list`). Keeping `sase monitor` also
   avoids renaming the `/sase_monitor` skill and rewriting `build_and_run.md`.

---

## 1. Corrections to both source reports

Verified at `5601920c9`. Only claims that changed are listed; everything else in both
reports held up.

| Claim | Source | Verdict | Evidence |
| --- | --- | --- | --- |
| 53 producers / 37 files | `__a` | **Wrong composition, right magnitude.** Not recounted; asserted "unchanged" | §6.1 |
| 41 refs / 30 files, "16 direct + 24 getattr + 1 def" | `__b` | **Undercount.** Misses `_submit_proc` entirely | §6.1 |
| `_submit_background_proc` is a producer | both | **Does not exist.** 0 references in `src/` | `grep -rn '_submit_background_proc' src/` |
| Use `-S\|--shell` | `__a` | **Rejected.** `-S` is `--status` on `sase proc list` | `parser_proc.py:146` |
| `-N\|--shell` free on `run` and `list` | `__b` | **Confirmed** | `parser_proc.py` |
| `timeout_seconds: Option<f64>` on `ProcWire` | `__b` | **Will not compile.** `ProcWire` derives `Eq` | `procs/wire.rs:6` |
| Integer-ms timeouts preserve the `Eq` model | `__a` | **Confirmed and load-bearing** | same |
| `-l/--lane` → `-a/--agent`, "`-a` is free" | `__b` | **Half right.** Free on `monitor start`; **`-a` is `--all` on `monitor list`** | `parser_monitor.py:61,80` |
| `shell_name` is the store-wide dedup key | `__b` | **Rejected.** Exclusion is set-overlap; a scalar name cannot express it | §3.1 |
| Standalone proc shells are a prerequisite for the TUI migration | `__b` | **False**, given the above | §3.4 |
| `shell_name` ≠ dedup key; add `concurrency_keys` | `__a` | **Confirmed and adopted** | §3 |
| Store rejects unknown kinds *on write* | `__b` open decision 7 | **Understated — also on read**, and invalid rows are dropped | `procs/store.rs:224` |
| 101 rows, all `kind=tui`, 99 commandless | `__b` | **Confirmed exactly** | live store |
| `sase agent list -a` = 75 rows / 33 monitors | `__b` | **Confirmed in shape** (73 / 30 today; live index drifts) | live index |
| `SUPPORTED_PROC_WIRE_SCHEMA_VERSIONS = {1, 2}`; v3 is a set entry | `__b` §0 | **Confirmed** | `procs/models.py:11-12` |
| `_ListScope.matches()`; `include_unattributed` must become unconditional | `__b` | **Confirmed, with the exact trigger**: `include_unattributed = ref is None or session_id is None` | `proc_handler.py:88,396` |
| `_supervisor_process_matches()` returns `True` on any host without `/proc` | `__b` | **Confirmed** | `procs/runner.py:311` |
| `delete_proc_logs` recomputes from id, so artifacts logs are prune-proof | `__b` | **Confirmed — and it is a trap, not just a convenience.** §5.5 | `procs/logs.py:71-82` |
| monitor 4,147 LOC / 21 modules vs procs 1,621 / 9 | both | **Confirmed** | `wc -l` |
| Exactly 31 `pub monitor_*` fields on the scan wire | both | **Confirmed**, split across two structs (6 summary + 25 detail) | `agent_scan/wire.rs` |
| CLI cold start ~0.5 s for a real subcommand | `__b` | **Confirmed: 0.58 s** (0.34 s bare parse) | measured 2026-08-14 |

Two facts neither report recorded, both of which change a recommendation:

- **`cli_rules.md` forbids required options**: *"Options must not be required. A value
  that is required for the command to execute belongs in a positional argument."*
  `sase monitor start` has **three** `required=True` options (`-c/--command`,
  `-r/--reason`, `-t/--timeout`). Both reports plan to keep "required reason and timeout
  as facade policy". That is fine as *policy*, but the facade should not carry the
  violation forward untouched — see §9.
- **The `Proc` glossary entry itself has to change.** It reads: *"Procs … come in
  `command`, `tui`, and `detached` kinds."* That sentence dies with this work, and
  neither report lists it among the memory-file edits.

---

## 2. The taxonomy

### 2.1 The four terms and the anchor sentence

| Term | Means | Today's spelling |
| --- | --- | --- |
| **Sase Agent** (agent) | An agent family, or a single agent that belongs to no family | "agent lane" |
| **Agent Shell** | One concrete agent run, whether or not it belongs to a family | *(no term)* |
| **Proc Shell** | One named, supervised proc that is a member of a sase agent | "sase monitor" |
| **Sase Shell** (shell) | An agent shell or a proc shell | *(no term)* |

`__b`'s anchor sentence is the best single line either report produced and should head
the glossary entry:

> **A sase agent is a sequence of sase shells.**

```text
sase agent                         sase shell
├─ solo agent (one shell)          ├─ agent shell   (an LLM/provider run)
└─ agent family (>= 2 shells)      └─ proc shell    (a supervised command proc)
   ├─ agent shell
   ├─ proc shell  == monitor
   └─ agent shell
```

Note the asymmetry that makes the model work: a family container (`pc`) is a sase agent
but is **not** a shell. A shell is the thing that actually executes. Clans, hoods, and
tribes are not shells either.

### 2.2 The code already implements it

Three independent confirmations, all measured today:

```
$ sase agent list -a -j | ...
rows: 73   roles: {'monitor': 30, None: 24, 'root': 19}
```

1. **`sase agent list` already lists sase shells**, not sase agents — 41% of its rows are
   proc shells, and the bare family name (`pc`) never appears, only `pc--code`, `pc--mon`.
2. **A proc shell already has a name in the agent namespace.** `sase-m4.6--mon-0` is
   resolvable by `sase agent show`.
3. **The monitor CLI already resolves all three levels** — *"Monitor id (or unique
   prefix), member agent name, or lane name"* (`parser_monitor.py:136`): id, shell, sase
   agent.

Suffix allocation also already exists and is locked:
`allocate_agent_family_child_suffix()` (`plan_chain.py:466`) mints `--mon`, `--mon-0`,
`--mon-1` via `monitor/naming.py:38-48`. Naming a proc shell needs no new allocator.

**Sizing consequence:** this epic is small. It is renames, glossary, help text, and one
CLI option swap.

### 2.3 Proposed glossary entries

Replacing **Agent Lane** and adding three (adapted from `__b`, which mirrors the
existing entry's structure most closely):

> **Sase Agent** — ALIASES: agent. A sase agent is either an agent family or a single
> agent that does not belong to a family; it is the identity that owns a sequence of
> sase shells. Sase agent names never end with `--<suffix>`, since that suffix belongs
> to the shells. When an agent is alone, the sase agent and its one agent shell share a
> name. When a second shell joins — which can only happen once the previous shell
> completes, because shells within a sase agent run sequentially — the original agent is
> renamed with its own `--<suffix>` and the bare name becomes a pure container.
>
> **Sase Shell** — ALIASES: shell. A sase shell is one member of a sase agent: either an
> agent shell or a proc shell. A sase agent is a sequence of sase shells.
>
> **Agent Shell** — An agent shell is a single agent, which may or may not belong to an
> agent family. It is the concrete thing that runs, holds a workspace claim, and appears
> in `sase agent list`.
>
> **Proc Shell** — A proc shell is a named, supervised [[Proc]] that is a member of a
> sase agent, with streaming output, a timeout, and an optional follow-up agent shell. A
> proc shell that belongs to an agent family is also called a **sase monitor** and is
> managed with `sase monitor`.

Retire the "agent's house" metaphor with the word it explains. Under the new terms the
sase agent is the identity and the shell is the body it wears for one run — one agent,
many shells over time.

Two further edits neither report listed:

- **`Agent Family`** currently reads *"a strictly sequential chain whose members use
  `<family>--<suffix>` names"*. Reword to *a chain of sase shells* — otherwise "agent
  shell" (the LLM leaf) contradicts a family that also contains proc shells. `__a` is
  right that this is a semantic change, not prose polish.
- **`Proc`** must drop *"come in `command`, `tui`, and `detached` kinds"*.

All of the above requires explicit user authorization before touching `sase/memory/`,
followed by a mandatory `sase memory init`.

### 2.4 Rename scope: only one of five senses of "lane"

`lane` appears ~1,397 times across 146 files in `src/`, but carries at least five
unrelated meanings. Only the first is renamed:

| Sense | Example | Rename? |
| --- | --- | --- |
| **Agent lane** | `agent_lanes.py`, `--lane`, `MonitorLaneError`, `lane_neighbors` | **yes** |
| AXE / lumberjack chop lane | `LANE_CHOP_TIMEOUT_SECONDS` | no |
| Scoped-test lane | `build_and_run.md`: "a diff-scoped test lane" | no |
| ACE detail-panel display lane | `SASE CONTEXT`, `COMMITS`, `PLAN` lanes | no |
| Launch-override lane | `_override_pill.py`: "the `default` launch lane" | no |

`docs/ace.md` contains senses 1 and 4 about 190 lines apart. The rename therefore
*improves* the four surviving senses: once agent lanes are gone, "lane" unambiguously
means a row or a scheduling track. **Rust is nearly untouched** — 33 occurrences in the
whole crate. This is a Python-and-docs change.

`agent_lanes.py` already implements the projection the taxonomy needs (member → family
name; solo → itself; bare name → consult the family-name reservation registry). So
**rename the abstraction, do not redesign it**: introduce `SaseAgentRef` /
`sase_agent_ref_for_shell()`, keep `AgentLaneRef` / `lane_*` as deprecation aliases, and
stage the mechanical symbol sweep separately from the supervisor work (`__a` §1.3).

Surface consequences worth deciding up front (`__a` §1.4):

- `SASE_AGENT_NAME` carries the concrete member name — under the new terms it is an
  **agent-shell name**. Family projection needs a separately named field or helper.
  `default_lane()` already does exactly this projection
  (`agent_family_base(name) or name`, `monitor/store.py:60-67`).
- Commit footer `SASE_AGENT=` already carries the lane projection; it becomes the
  sase-agent identity with no behavior change.
- `sase agent kill` can only kill a live agent shell, never a container. Say so in help.

### 2.5 The `-l/--lane` → `-a/--agent` swap has one collision

`-a/--agent` is the established repo convention (`parser_skills.py:78`,
`parser_repo.py:125`, `parser_artifact.py:131`). But `-a/--all` is an equally
established convention on `list` subcommands (`proc list`, `agent list`, `workspace`,
`stitch`, `repo`, `prompt`).

Measured shorts:

| Subcommand | Has `--lane`? | `-a` taken by |
| --- | --- | --- |
| `sase monitor start` | `-l/--lane` | *free* |
| `sase monitor list` | `-l/--lane` | **`--all`** |
| `sase monitor show` | no (`-l` is `--log-lines`) | — |

So `__b`'s "the only public CLI break, and `-a` is free" holds for `start` and fails for
`list`. Options, in preference order:

- **(a) `-a/--agent` on `start`; on `list`, keep `-l` as the short and rename only the
  long option to `--agent`.** Recommended. One character of inconsistency, zero breakage
  of `-a/--all`, and `-l` survives as a familiar short during the transition.
- (b) Move `--all` to `-A` on `monitor list` to free `-a`. Breaks a repo-wide convention
  for one subcommand.
- (c) Pick a neutral short (`-A/--agent`) uniformly. Collides conceptually with
  `-A/--all-lines` on the `show` subcommands.

### 2.6 "Shell" has one liability; pre-empt it

"Shell" also means a command interpreter, and proc shells run their commands under one
(`["/bin/sh", "-c", ...]`). Three cheap mitigations, from `__b` §1.4 and `__a` §1.5:

- Reserve `--interpreter` in the docs *now* for the future selector, so `--shell` can
  never mean it.
- Have `--shell` **reject values containing `/`** with an actionable error. A path is
  the only way a user can express the wrong mental model.
- Write help as "named proc shell" and define the glossary entry in terms of identity,
  not execution.

Use `shell_name` in the wire and Python model, never a bare `name` — which would collide
with proc label, agent name, family name, provider name, and project name.

---

## 3. The central decision: identity is not exclusion

This is the one place the two reports genuinely conflict, and it determines the shape of
everything downstream.

- **`__a` §3.2, §6.5:** `shell_name` is identity/addressability. Store-wide exclusion is
  a separate `concurrency_keys` set.
- **`__b` §3.4:** "the name *is* the dedup key. One field, two features."

### 3.1 The evidence

`_submit_tracked_proc` has **three** exclusion mechanisms today
(`ace/tui/actions/proc_actions.py:151-200`):

```python
existing = (self._proc_queue.get_running_for_key(dedup_key)
            if dedup_key is not None
            else self._proc_queue.get_running_for_cl(cl_name))
if existing is None:
    existing = self._proc_queue.get_running_for_scopes(exclusive_scopes)
```

and `get_running_for_scopes` is **set-overlap**, not equality
(`ace/tui/proc_queue.py:320-331`):

```python
if info.status == "running" and requested & info.exclusive_scopes:
```

with a live call site claiming three scopes at once:

```python
exclusive_scopes=("sase-update", "agent-cli-update", "agents-sync")
# plugins_browser_comprehensive_update.py:349
```

A single scalar `shell_name` cannot express "this proc blocks anything claiming any of
these three scopes." **`__a` is right.** Collapsing the two would force either a
combinatorial explosion of names or a silent loss of the exclusion ACE relies on today
— and it would recreate the exact failure mode of `kind`: one field encoding two
orthogonal facts.

### 3.2 The resolution

Keep both, and make the relationship one-directional:

| Field | Type | Meaning | Cardinality |
| --- | --- | --- | --- |
| `shell_name` | `Option<String>` | Proc-shell identity; addressable by `show` / `kill` / `list` | at most one per row |
| `concurrency_keys` | `Vec<String>` | Store-wide exclusion; overlap conflicts | zero or more per row |

**A shell name implies exactly one concurrency key** (`shell:<project>:<qualified
name>`), so there is one *enforcement* mechanism with two *authoring* surfaces. That
satisfies `__b`'s legitimate objection to two parallel mechanisms without pretending the
scalar can do the set's job. Migrate ACE's current keys directly:

- `patch:<project>:<cl_name>` — replaces `get_running_for_cl`
- `plugin:<name>`, `sase-update`, `agent-cli-update`, `agents-sync` — replace
  `exclusive_scopes` verbatim
- `workspace:<project>:<num>` / `axe-slot:<n>` — for the AXE slot
- `agent-meta:<artifacts-dir>` — for directive persistence

Reservation must be atomic in Rust (§5.3); read-then-append in Python is exactly the
race that globalizing ACE producers would expose across two ACE instances.

### 3.3 What a name is for

`shell_name` earns its place on identity alone:

- `sase proc show deploy` / `sase proc kill deploy` without copying an id;
- `sase proc list -N deploy` as run history for one name;
- the join key between a proc row and its family member;
- the addressable target for future `%wait` / `#fork` directives.

Its uniqueness rule is a *consequence* of the taxonomy, not a dedup policy: one active
shell per sase agent, because a sase agent is sequential by definition. See §4.3.

### 3.4 This un-blocks the sequence

`__b`'s most consequential structural claim is that standalone proc shells are a
prerequisite for eliminating TUI procs, because ACE's procs need store-wide dedup, dedup
is the name, and ACE is not an agent. With §3.1 the chain breaks at the first link:
**ACE's migrated procs need concurrency keys, and most of them need no name at all.**

That is also the right outcome on its own terms. Under `__b`'s model every migrated ACE
proc would mint a sase agent with an artifacts directory — adding hundreds of rows to an
agent index that holds 73 today, for background work that is not agentic in any sense.

Standalone proc shells remain worth building, and cheaply: `resolve_lane()` raises
`MonitorLaneError` when a name has no pre-existing artifacts (`monitor/store.py:69-81`),
so the only new capability is minting a sase agent from nothing. But they become an
*enabler for the future direction* rather than a *blocker for the TUI migration* —
which changes the sequencing risk materially.

---

## 4. The `--shell` contract

### 4.1 CLI shape and the short alias

The option belongs on `run` and `list`, not on the group: `cli_rules.md` establishes that
bare `sase proc` delegates to `sase proc list` and that list flags follow the explicit
`list` token.

```bash
sase proc run  -N check-full -- just check-full   # create a proc shell
sase proc list -N check-full                      # run history for one shell name
sase proc show check-full                         # already takes a ref; add name resolution
sase proc kill check-full                         # same operation as `sase monitor stop`
sase proc list                                    # shells and unnamed procs, one table
```

That last line is the point of the merge: today there is **no single list of what is
running**. Proc shells live in `agent_meta.json` + `done.json` with no store row; procs
live in the JSONL store with no family. After the merge, `sase proc list` shows
everything and `sase agent list` shows every shell — two complete projections instead of
two partial ones.

**Short alias — decided.** Measured shorts in `parser_proc.py`:

| Subcommand | Taken | `-S` | `-N` |
| --- | --- | --- | --- |
| `proc run` | `-c -d -j -l -p -q -s -t -w` | free | free |
| `proc list` | `-a -d -j -k -n -p -q -r -s -S -t` | **`--status`** | free |

`__a`'s `-S|--shell` collides with `sase proc list --status`. `__a` checked the wrong
neighbour (`sase monitor -S|--stop-status`, a different group). Use **`-N/--shell`
uniformly**; a per-subcommand divergence would be far worse than the weak mnemonic, and
`-s` must be rejected outright since it is `--session` on both subcommands — making it
`--shell` on `run` only would let `sase proc list -s deploy` silently filter by session.

Do **not** make `--shell` valueless-with-auto-allocation. `nargs="?"` immediately before
a `--`-introduced remainder is an argparse edge case for no benefit; `--mon`-suffix
auto-allocation belongs to `sase monitor start`, where it already lives.

### 4.2 The resolution rule

`__b`'s rule is the design's best idea and should be adopted verbatim: **the family
separator carries the qualification.**

| Value | Resolves to | Notes |
| --- | --- | --- |
| `pc--check` (contains `--`) | shell `check` of sase agent `pc` | fully qualified; no ambient agent needed |
| `check` (bare), inside agent `pc` | shell `check` of sase agent `pc` | today's implicit-lane behavior |
| `check` (bare), no calling agent | **today:** error. **future:** mint a sase agent whose only shell is `check` | one syntax, two eras |

The future direction becomes a capability addition with no syntax change.

### 4.3 Uniqueness — the two reports are reconcilable

`__a` says "unique among active proc shells in a project"; `__b` says "one active shell
per sase agent, not per project". These are the same rule stated at two levels, and the
merged form is:

> The unique key is **(project, fully-qualified shell name)**. Because a sase agent is
> sequential by definition, that also yields at most one active shell per sase agent.
> Agent names are project-scoped (`_project_records` filters by project), so the project
> scope comes for free rather than being an extra rule.

This preserves `__b`'s requirement that two agents — or two projects — can both run
`just check-full` under the suffix `check`, while giving `__a`'s per-project active
uniqueness.

Further constraints, merged from both:

- A shell name must be a valid **agent-name component**, because it *is* one. That means
  `:` (proposed in `sase_shell_named_procs` §3.2) is **not** available; use `-`.
- Reject values that are lexically valid proc ids, so name resolution and id-prefix
  resolution can never fight. Resolution order: exact shell name → exact proc id →
  unique id prefix.
- Reject values containing `/` (§2.6).
- `shell_name` is immutable for a row and reusable after terminal settlement, so
  `list -N NAME` is run history.
- Same active name + same `request_fingerprint` = idempotent replay. Same name +
  different fingerprint = a visible conflict that **names the blocking row and the
  command to inspect it**, as `_active_monitor_message()` already does.

### 4.4 `shell_name` is not a kind

Namedness, session attribution, family attachment, and execution ownership are four
independent axes. A `kind="shell"` would immediately recreate the
`command`/`detached`/`tui` problem. Use nullable fields and one invariant:

```text
shell_name None, artifacts_dir None  -> ordinary proc
shell_name set,  artifacts_dir None  -> standalone proc shell
shell_name set,  artifacts_dir set   -> family-attached proc shell == monitor
shell_name None, artifacts_dir set   -> invalid
```

---

## 5. One supervisor, one service

### 5.1 Promote the monitor kernel; delete `procs/supervisor.py`

Both reports agree, and it is verified: monitor is 21 modules / 4,147 LOC (with 4,843
LOC of tests) against procs' 9 modules / 1,621 LOC, and there is **no axis on which the
proc supervisor is better** — it is smaller because it does less.

| Capability | proc supervisor | monitor supervisor |
| --- | --- | --- |
| Detachment | `start_new_session=True` | double-fork + reparent before return |
| Startup proof | none | startup marker + bounded ack wait |
| Launch barrier | none | command cannot exec until the claim transaction releases it |
| Supervisor identity | `/proc/<pid>/cmdline`, **`return True` on any host without `/proc`** | boot-aware pid/start identity |
| Total + idle timeout | none | both, checked independently of output |
| Env scrubbing of agent identity | no | yes |
| Reconciliation | flips status | kills child group, settles claim/follow-up, handles reboot/lost |
| Idempotency | none | request fingerprint under a per-family lock |

Two of these become **mandatory** the moment procs are agent-startable: reparenting (so
a PPID-walking `kill_agent_runner_group()` cannot collect the proc as collateral) and
identity-over-pid (`procs/runner.py:311` returns `True` unconditionally when `/proc` is
unreadable).

Migrate `tests/monitor/` rather than rewriting it — those 4,843 lines are the record of
which defects the `sase-kp` / `sase-ku` hardening was written against.

**One caveat on `__b`'s "ship it alone and let it soak":** there is nothing to soak with.
All 101 live rows are `kind=tui`; there is not a single `command` or `detached` row on
this host. The kernel swap has near-zero production blast radius *and* near-zero
real-world validation, so the tests carry all the weight. Ship it alone anyway — for
bisectability, not for soak signal.

### 5.2 The two wrong wrappers

"Wrap this functionality at the service level" is the exact phrasing that produces both
mistakes. Both reports warn about them; the warning is worth restating:

- **Not a CLI wrapper.** `sase monitor start` must not `Popen(["sase", "proc", "run",
  "--json", ...])` and parse the envelope. That buys a second interpreter start
  (**measured 0.58 s**), an error-translation layer, output-ownership problems, and a
  CLI-to-CLI protocol that can skew across versions.
- **Not a wrapper process.** The shape `proc supervisor → sase monitor _run → user
  command` must be rejected. `sase proc kill` signals the child *group*, so it kills the
  wrapper and the user command together — and the wrapper is precisely the process
  responsible for releasing the workspace claim and launching or suppressing `--next`.
  It would die before it could settle.

"Powered by procs" means shared models, store, supervisor, and service functions:
**one Python import boundary, two CLI facades.** The supervisor executes `Proc.command`
as argv directly; the monitor facade compiles `-c 'string'` into `["/bin/sh", "-c",
"string"]` *before* submission and persists that argv — honest in `ps`, in the Procs
pane, and in `sase proc list`.

Introduce one typed request as the single entry point for `sase proc run`, ACE, bead
launches, epic launches, and the monitor facade:

```python
StartProcRequest(argv, cwd, label, project, session_id, shell_name,
                 timeout_ms, idle_timeout_ms, concurrency_keys,
                 request_fingerprint, family_attachment)
```

### 5.3 Wire v3

`ProcWire` has 22 fields and derives `Debug, Clone, PartialEq, Eq, Serialize,
Deserialize` (`procs/wire.rs:6`). Add these, all nullable with serde defaults:

| Field | Type | Purpose |
| --- | --- | --- |
| `shell_name` | `Option<String>` | proc-shell identity |
| `artifacts_dir` | `Option<String>` | immutable cross-link for a family-attached shell |
| `reason` | `Option<String>` | required by monitor policy, optional otherwise |
| `supervisor_identity` | `Option<String>` | boot-aware protection against reused pids |
| `timeout_ms`, `idle_timeout_ms` | `Option<u64>` | **integer ms — see below** |
| `request_fingerprint` | `Option<String>` | idempotent replay |
| `concurrency_keys` | `Vec<String>` | store-wide exclusion (§3.2) |
| `result_path` | `Option<String>` | durable structured result envelope (§6.2) |
| `termination_reason` | `Option<String>` | normal / stop / total timeout / idle timeout / supervisor loss / start failure |
| `stop_requested_at` | `Option<String>` | durable stop intent |

**Integer milliseconds, not `f64` seconds.** `ProcWire` derives `Eq`; `f64` is not `Eq`.
This is not theoretical — `AgentMetaWire`, which holds `monitor_timeout_seconds: f64`,
derives only `PartialEq` for exactly this reason (`agent_scan/wire.rs:204`). `__b`'s
`timeout_seconds: Option<f64>` would force dropping `Eq` from `ProcWire` and silently
weaken every equality assertion in the Rust and Python test suites.

Schema **v3** is a *set entry* — `SUPPORTED_PROC_WIRE_SCHEMA_VERSIONS = frozenset({1,
2})` — not a coordinated cutover. Keep it an explicit set; do not relax it to `>= 2`,
since a future version may change semantics rather than add fields.

Add three atomic store operations. Read-then-append in Python is not sufficient once
two ACE instances can submit:

- `reserve_proc` — check concurrency-key overlap **and** shell-name collision, then
  append one pending row, all under the existing exclusive lock;
- `request_proc_stop` — record intent without terminalizing;
- `finish_proc` — compare active state, write the outcome once, refuse a second terminal
  owner.

Roughly half of the 31 `pub monitor_*` scan-wire fields (command, cwd, state, exit code,
pgid, supervisor identity, output path, timeouts) become proc-row fields and **leave**
the scan wire — a real reduction. Rename the survivors `shell_*` with serde aliases in
the documentation phase, not the wire phase. Never persist a Python callback, import
path, or hook path: settlement is a closed built-in triggered by `artifacts_dir is not
None`, and a persisted code reference would be a durable mixed-version RCE contract.

Do **not** persist policy that is meaningless without a sase agent —
`start_status`/`stop_status`, `next_action`/`next_output`/`tail_lines`, follow-up
disposition, starter and follow-up agent — those stay in `agent_meta.json`.

### 5.4 Two records, one writer, one ordering rule

A family-attached proc shell necessarily has two records. Both reports converge on the
same split and the same fix; adopt it:

- **Proc row** owns execution and control: argv, cwd, status, phase, exit code, pid,
  pgid, timestamps, `log_path`, `supervisor_identity`, `shell_name`.
- **Artifacts member** owns lineage and presentation: family membership and role,
  `shell_kind="proc"`, custom status labels, `done.json`, chat history, follow-up
  disposition, workspace-claim lineage.
- One **immutable cross-link each way**.
- The **supervisor is the only normal writer** after launch; the reconciler writes only
  after proving the supervisor is dead.

`__a`'s point about `agent_family_role` is worth adopting: today the role is *derived
from the suffix* (`agent_family_role_for_suffix`, `plan_chain.py`), which fuses "what
kind of thing executes this member" with "what job it does". Record `shell_kind` as a
separate field and keep legacy `agent_family_role="monitor"` readable.

**One ordering rule**, so terminal proc status means fully settled:

```text
child exits / timeout / stop request
  -> proc.phase = "settling"   (still active)
  -> retain/finalize output
  -> release or transfer the workspace claim
  -> launch, degrade, suppress, or durably reject the follow-up
  -> write member metadata + done.json + chat history
  -> proc.status = terminal, with termination_reason
```

Invariant: **terminal proc status implies the command is gone and every required
settlement side effect is durable.** This retires `monitor_settled` and
`MonitorRecord.is_terminal`'s two-field check, and gives `sase proc show --follow`,
`sase monitor show --follow`, `%wait`, ACE's indicator, and future standalone waits one
authoritative completion condition.

Today's `kill_proc()` signals and *immediately* writes `status="killed"` while the
supervisor also writes terminal state. That race becomes unacceptable once settlement
must run exactly once. Both `sase proc kill` and `sase monitor stop` must: record stop
intent atomically → verify supervisor identity and signal it → let only the supervisor
(or the dead-supervisor reconciler) write the terminal outcome. The stored fact is one
neutral `termination_reason`; presentation may still render `killed` or `stopped`.

The claim-release race is still recorded live on `sase-kp`. **Confirm it is cleared
before the move**, so a pre-existing flake is not mistaken for a migration regression.

### 5.5 The log-retention trap, stated precisely

`append_proc` calls `delete_proc_logs(pruned)` on **every append**
(`procs/store.py:85`), with `procs.history_limit: 100` and the live store sitting at
exactly 101 rows — so this fires constantly. Today `delete_proc_logs` recomputes
`proc_logs_dir()/<id>.log` from the id and **ignores the row's `log_path`**
(`procs/logs.py:71-82`), which is why a log written into an artifacts dir is
accidentally prune-proof.

`__a` recommends "every reader follows `Proc.log_path`". Taken literally and applied to
the pruner, **that change would start deleting artifacts-owned logs on nearly every
append** — silent, data-losing, and easy to miss in review. Split the rule:

- **Readers become path-driven.** `runner.py:203` already honors `proc.log_path`;
  `open_proc_log()` and `read_proc_log_tail()` (`logs.py:29,59`) still recompute from
  the id and must be fixed.
- **The pruner stays confined.** It may delete only files inside `proc_logs_dir()`, and
  must refuse any path outside it regardless of what `log_path` says.

Keep attached proc-shell logs at `monitor_log_path(artifacts_dir)`, as they are today. A
family member can outlive proc history retention indefinitely; add an integration test
that appends past the history limit after a monitor settles, then proves the family's
history and output are still readable.

---

## 6. Removing procs from ACE, and removing `-d|--detached`

### 6.1 The real producer inventory

Both reports undercount or mis-compose this. Measured at `5601920c9`:

| Entry point | Call sites | Files | Duck-typed |
| --- | --- | --- | --- |
| `_submit_tracked_proc` | 39 | 30 | **24** (`getattr(app, "_submit_tracked_proc", None)`) |
| `_submit_proc` | 17 | 7 | 0 |
| `_submit_background_proc` | **0 — does not exist** | 0 | 0 |
| **Total (excl. definitions)** | **56** | **36** | 24 |

`_submit_proc` (`proc_actions.py:114`) is a thin adapter over `_submit_tracked_proc`
with a `(bool, str)` callable signature — *"Existing Patch actions keep using
`_submit_proc`"* — so it is not a second runtime, but it *is* a second public producer
surface, and it is the one used by `status.py`, `base.py`, `axe_bgcmd.py`, `sync.py`,
`proposal_rebase.py`, `hints/_rewind.py`, and `agents/_monitor_stop_flow.py`. A
migration plan scoped to 41 sites would miss all of them.

Two enforcement consequences:

- The static regression test must match **string patterns**, not resolved call targets:
  24 sites are `getattr` lookups, and the mixin's absence makes them silently no-op.
- It must cover **both** entry points plus the seven named wrappers
  (`_submit_cleanup_proc`, `_submit_kill_persistence_proc`,
  `_submit_bulk_kill_persistence_proc`, `_submit_launch_proc`, `_submit_sase_update_proc`,
  `_submit_dev_update_proc`, `_submit_combined_update_proc`). A `_submit_*_proc` glob
  catches all of them, which is the right shape for the test.

Only one code path writes a TUI row: `proc_mirror.py:258`. That is the single choke
point to delete last.

### 6.2 What should stop being a proc at all

The goal is **"no work classified as a proc executes inside ACE"**, not "ACE may no
longer have worker threads". Measured durations from the live store against a measured
**~1.0–1.2 s** of detached-proc startup (0.58 s supervisor + 0.58 s `sase` child):

| Proc type | n | Median | Max | Verdict |
| --- | --- | --- | --- | --- |
| `kill <patch>` | 10 | 152.1 s | **1679.3 s** | migrate — strongest case |
| `kill/dismiss N agents` | 3 | 146.2 s | 177.8 s | migrate |
| `comprehensive update` | 11 | 4.7 s | 95.7 s | migrate |
| `Plan response: tale` | 16 | 4.3 s | 6.2 s | migrate |
| `launch <project>` | 13 | 1.7 s | 71.1 s | migrate |
| `Stash prompt` | 3 | **0.09 s** | 0.11 s | **declassify** |

The 28-minute `kill` proc is the strongest argument for the migration: highest volume,
holds a half-applied transaction, dies with the TUI, and `sase proc kill` refuses to
touch it (`runner.py:226-229`). `Stash prompt` at 90 ms is a **>10× latency
regression** for no benefit and should become a plain `run_worker(thread=True)` with no
store row — which still satisfies "no procs run inside ACE", because the remaining
workers are simply never procs.

The boundary:

- **Proc**: durable, long-running, cross-surface, independently inspectable/killable,
  subprocess/network/VCS work, or work that must survive ACE.
- **Plain Textual worker**: short UI-support computation or I/O whose result is
  meaningless once the current UI interaction disappears. These must not enter the proc
  store, the Procs pane, the quit warning, or the proc indicator.

**Durable request/result contracts.** TUI callables close over live `Agent`, modal, plan,
and bound-method objects. A detached process cannot and should not serialize those. For
each migrated operation: reduce input to durable identifiers and re-resolve state in the
command; put large or sensitive input in a mode-0600 versioned request sidecar rather
than argv; write a mode-0600 versioned result envelope to `result_path` before exiting.
**Do not parse structured results from combined stdout/stderr** — logs are presentation,
not a protocol. Losing ACE must lose only ephemeral presentation, never a mutation,
claim release, receipt, next action, or result.

**Commands belong in existing domain groups** — `sase patch`, `sase agent`, `sase bead`,
`sase notify`, `sase plugin`, `sase workspace`, `sase run` — not a `sase ace` namespace
and not a generic `sase proc exec --payload` dispatcher, which would freeze TUI
implementation details into a private versioned protocol. Domain functions must move out
of `ace/handlers` and `ace/tui/actions` into surface-neutral services, and into
`sase-core` where the backend-boundary rule applies: a CLI handler must never import a
TUI action module.

`ProcMirror` becomes a **proc observer**: it stops creating rows and flushing in-memory
logs, and instead polls watched proc ids and the global active count off the event loop,
marshalling terminal notifications through `call_from_thread`.

### 6.3 Removing `-d|--detached`

The flag is already a misnomer, and the command's **own help says so**:

> *"Run a command as a detached, durable proc … start it under a detached supervisor …
> the proc survives this shell and any TUI."*

— while the epilog still advertises `sase proc run --detached -- ./overnight.sh`.
`submit_proc` and `submit_detached_proc` both call `_submit_supervised_proc` with
`start_new_session=True` (`runner.py:52-184`) and differ in exactly two ways: `kind`,
and whether `origin` is required. So `--detached` chooses *attribution*, not detachment,
and `--session none` already expresses that.

Two consequences to decide on purpose:

1. **One forced behavior change.** `_ListScope.matches()` returns `True` for every
   `kind == detached` row unconditionally, while a session-less non-detached row appears
   only when `include_unattributed` is set — and that is
   `ref is None or session_id is None` (`proc_handler.py:88,396`), i.e. **False whenever
   the user passes an explicit `--session <other>`**. After the collapse, "detached" and
   "unattributed" are the same thing, so `include_unattributed` must become
   unconditional or `sase proc list --session <other>` silently stops showing global
   procs.
2. **`-d/--detached` should leave `sase proc list` too**, where it is documented as
   shorthand for `--kind detached`. Keep `--kind` as a hidden legacy-history filter
   during the compatibility window; drop the shorthand.

**Keep `--session` on `run`.** `detached_proc_convergence` §9 recommended dropping it as
well; that is a second, unrequested removal that also changes the default from
`current → latest → none` to unattributed. Attribution still decides which ACE session's
Procs tab shows and counts the row, and keeping it costs nothing. Session attribution
must never affect ownership, visibility, killability, or survival.

For one release, keep a **suppressed compatibility parser** that rejects `-d|--detached`
with an actionable message rather than a bare argparse error — agents carry the old
invocation in memory files and chat history, and the command itself arrives through a
`--` remainder positional:

```text
all procs are detached; remove --detached (use --session none for no attribution)
```

Apply the same behavior through the legacy `sase task` alias.

### 6.4 The kind-removal trap

**Highest-severity migration hazard in this whole plan, and neither report states it
precisely.**

`normalize_and_validate_proc` calls `validate_kind`, which rejects anything not in
`PROC_KINDS` — and it runs on **read** (`procs/store.rs:224`) as well as on append
(`:92`). On read, an invalid row is **silently skipped**. Every one of the 101 live rows
is `kind="tui"`.

Therefore: **removing `"tui"` from `PROC_KINDS` makes the entire visible proc store
disappear.** The same applies to `"command"` and `"detached"`.

The rule for the whole cut-over is *split read compatibility from new-write validation*:

- **Read**: keep every legacy kind accepted forever, or make `kind` a free-form
  `Option<String>` with no validation on read. Never rely on rewriting historical
  evidence.
- **New writes**: never emit a kind after the cut-over; reject empty argv on every new
  reservation (today `_validated_argv` enforces this in Python only —
  `runner.py:337-341` — while the Rust store validates `proc_id`, `label`, `cwd`,
  `origin`, `created_at`, and `log_path`, but **not `command`**); never allow an update
  to erase an existing command.
- Tolerate an empty command **only** when reading a legacy `kind="tui"` row.

During a rolling upgrade an old ACE may still write TUI rows; readers tolerate them, and
only their owning old ACE can finish them. A dead active legacy TUI row must reconcile
deterministically to `error`/`lost` once its ACE pid disappears. Only after the window
closes should `TUI_PROC_KIND`, `DETACHED_PROC_KIND`, `_SUPERVISOR_OWNED_KINDS`,
`MIRROR_KIND`, `PROC_KIND_CHOICES`, the kind filters, and the TUI kill refusal be
deleted.

Likewise: **never adopt an already-running monitor's process group into a new proc row.**
Its pid identity, claim, launch barrier, and settlement ownership cannot be transferred
after launch. Let loaded legacy supervisors finish under the code they started with, and
keep the legacy reconciler until no active legacy record can remain.

---

## 7. Sequencing

Three epics. Both reports agree the taxonomy goes first; the difference is what rides
along with it.

**Epic A — Taxonomy (small).** Behavior-preserving. Rename agent lane → sase agent;
introduce sase shell / agent shell / proc shell; `-l/--lane` → `--agent` (§2.5); update
the `Agent Family` and `Proc` glossary entries; `docs/agent_families.md`,
`docs/monitors.md`, `docs/ace.md` (agent-lane hits only); `sase_monitor` skill; then
`sase memory init`. Add `SaseAgentRef` aliases; defer the mechanical `lane_*` symbol
sweep. Land immediately after `sase-lh` and `sase-kp` close, so all terminology churn
lands in one window.

**Epic B — Proc shells (large).**

| Phase | Work |
| --- | --- |
| 1 | Rust wire v3: additive nullable fields (§5.3), integer-ms timeouts, atomic `reserve_proc` / `request_proc_stop` / `finish_proc`, per-project active shell-name uniqueness, concurrency-key overlap |
| 2 | **Kernel:** promote `monitor/supervise.py` + `supervisor_bootstrap.py`; delete `procs/supervisor.py`. **Ship alone** for bisectability |
| 3 | Named shells: `shell_name`, the §4.2 resolution rule, fingerprint replay, `sase proc run -N` |
| 4 | Attachment: `member`/`claims`/`followup*`/`settlement`/`transaction` behind an `artifacts_dir`-conditional path; §5.4 ordering; path-driven readers + confined pruner (§5.5) |
| 5 | `sase monitor` becomes the service-level facade |
| 6 | Collapse epic launch's monitor/detached-proc fork (`bead/epic_launch.py:150,249`) and `bead/task_launch.py:90` into one service call |
| 7 | *(recommended, not required)* standalone proc shells: mint a sase agent with no starter |
| 8 | ACE: proc shells in the Procs pane; Agents-tab rows re-keyed on the proc row |
| 9 | Docs, memory, `shell_*` scan-wire rename with serde aliases |

**Epic C — No procs inside ACE (large).** Store-wide `concurrency_keys` first (§3.2),
then migrate the 56 producer sites in bucket order: free wins (gate / launch / bead) →
Patch workflow → plugins and environment → agent lifecycle → AXE workspace execution.
Declassify sub-second work. Then remove `-d|--detached` from `run` *and* `list`, make
`include_unattributed` unconditional, keep `--session`, reject `--detached` for one
release, and delete the callable runtime.

**Dependency, corrected.** `__b` puts Epic C behind Epic B phase 7 (standalone shells).
Per §3.4 that is not required: **Epic C depends on Epic B phases 1–4** (the wire fields,
the kernel, and atomic `concurrency_keys` reservation) and on nothing else. Phases 5 and
7 are independent. This is the single largest sequencing difference between the two
reports, and it removes a hard serialization from the plan.

**Landing.** `just check-full` through `/sase_monitor`, plus the ACE PNG snapshot suite.
This work crosses the Rust/Python wire, the shared store, process ownership, CLI parsers,
both ACE surfaces, family wait resolution, workspace claims, follow-up launch, and
docs/memory.

---

## 8. Acceptance criteria worth writing down

**Ownership.** Every new proc has non-empty immutable argv before reservation succeeds ·
no proc execution path accepts a Python callable (static test, string-pattern based, §6.1)
· quitting or crashing ACE never interrupts an ACE-submitted proc · killing the starter
agent shell does not kill the reparented supervisor · no active proc is owned by the ACE
pid.

**Identity and concurrency.** Same `(project, shell_name, fingerprint)` concurrent starts
execute once and both callers get the same proc · same active name + different
fingerprint conflicts visibly, naming the blocking row · overlapping concurrency keys
across two ACE instances execute once · the same suffix under two different sase agents
is allowed · terminal name reuse creates a new proc id and history stays queryable.

**Process safety.** Bootstrap death before acknowledgement never starts the command ·
claim-transfer failure leaves the barrier closed · a stale or reused supervisor pid is
never signalled · pre-reboot active work becomes `lost` and is never replayed · partial
lines, invalid UTF-8, closed output, background grandchildren, quiet commands, and
TERM-ignoring process groups all settle.

**Settlement.** Terminal proc status is never visible before claim/follow-up/artifact
settlement · stop from either CLI suppresses `--next` and disposes the claim exactly once
· a crash between **every pair** of §5.4 ordering steps resumes without duplicate
follow-up or double claim release · `%wait` advances only after terminal settlement ·
family-attached output survives more than one full retention window · ACE restart
reconstructs correct state without the original UI callback.

**Compatibility.** The live 101-row store still reads after the kind collapse (§6.4) ·
legacy monitor records remain readable and stoppable · new monitors show one proc id
through `sase proc`, `sase monitor`, the Procs pane, and the family member in Agents ·
`sase proc run --help` no longer advertises `--detached`, and passing it produces the
actionable rejection · `--shell` help says "named proc shell" and rejects `/`.

---

## 9. Open decisions

1. **`-N/--shell`?** §4.1 says yes; `-s` and `-S` are both rejected on evidence. *(The
   only decision here that changes what a user types daily.)*
2. **Does Epic B phase 7 (standalone proc shells) ride along?** Recommended yes — it is
   cheap and it unlocks the `%wait`/`#fork` future direction — but per §3.4 it is
   **no longer a blocker for Epic C**, which is the material change from `__b`.
3. **Does `sase agent list` keep listing shells?** Recommended yes, documented. An agent
   name may name a sase agent (`pc`) or one of its shells (`pc--code`), and
   `resolve_monitor_ref` already resolves both.
4. **`--agent` short on `monitor list`.** §2.5 option (a): `-a` on `start`, keep `-l` on
   `list`, rename only the long option.
5. **`sase monitor start`'s three `required=True` options** violate `cli_rules.md`. The
   facade rewrite is the natural moment to fix it — most likely by making the command a
   positional (`sase monitor start [-a AGENT] -- CMD...`, matching `sase proc run`) and
   giving `--reason` / `--timeout` defaults. Out of scope for the merge itself, but it
   should be a deliberate "not now" rather than an oversight.
6. **`sase agent kill` collision.** Today it SIGTERMs a running agent shell; Epic C's
   migrated `kill` proc persists a kill/dismiss *transaction*. Distinct verb
   (`sase agent cleanup`) or a deliberate flag-based merge?
7. **Escape-hatch budget** for a hidden `sase proc exec --payload` dispatcher in Epic C —
   approve at most N proc types, or forbid it outright?
8. **Compatibility windows.** Recommended: one release for the erroring `--detached`
   sentinel, at least one release for legacy monitor control, and legacy `kind` reads
   kept **indefinitely** (§6.4).

---

## 10. Risks

1. **Naming fatigue.** Within ~six weeks SASE will have had *task → proc*, *monitor →
   proc shell*, and *lane → sase agent*. The glossary entries are not optional, and
   `sase monitor` must keep working throughout. Keeping the command — rather than the
   prior note's `sase shell` — is the single biggest mitigation available.
2. **`--shell` read as an interpreter selector.** §2.6. Cheap to mitigate, embarrassing
   to skip.
3. **Silent history loss at kind removal.** §6.4. The failure is invisible: the store
   reads as empty rather than erroring.
4. **Silent log loss at prune.** §5.5. Fires on essentially every append at the current
   100-row limit; trivially introduced by a well-intentioned "make readers path-driven"
   change applied one function too far.
5. **A name is a lock.** Per-agent active uniqueness means a wedged shell blocks the next
   start under that name. Stop and reconcile paths must be reliable enough to clear it,
   and the collision error must name the blocking row and the command to inspect it.
6. **Dual-record divergence.** Test it directly: kill the supervisor between each pair of
   §5.4 ordering steps and assert both records agree afterwards.
7. **Epic B phase 2 changes execution for every existing supervised proc** — with no
   production traffic to soak against (§5.1). Keep the old module importable for one
   release so bisecting is cheap.
8. **Losing a completion callback must lose only ephemeral UI feedback.** If ACE exits
   before completion, reopening must reconstruct correct state from disk.
9. **Blind migration of sub-second work** turns 90 ms writes into durable global rows and
   a Procs pane nobody can read.

---

## Recommended solution

**Land three epics, in this order, and keep identity separate from exclusion.**

**1. Adopt the taxonomy first, alone, as a behavior-preserving epic.** Rename agent lane
→ **sase agent**; add **sase shell** = **agent shell** | **proc shell**; anchor the
glossary on *a sase agent is a sequence of sase shells*; define a **monitor** as a
family-attached proc shell — the narrowing that becomes true by construction the day
standalone shells ship. Rewrite the `Agent Family` entry as a chain of *shells* and drop
the three kinds from the `Proc` entry. Rename only the agent-lane sense of "lane"; the
AXE, test, display, and launch senses stay and become less ambiguous. Rust is 33
occurrences. Add `SaseAgentRef` aliases and defer the mechanical symbol sweep. Doing this
first means every surface below is named once. **Do not add a top-level `sase shell`
command** — that name belongs to the concept.

**2. Merge monitors into procs by making a proc shell a named proc with an optional
family attachment.**

- Add **`-N/--shell NAME`** to `sase proc run` and `sase proc list`, with name resolution
  on `show`/`kill`. `-S` collides with `proc list --status`; `-s` is `--session`.
- Use `__b`'s resolution rule: a value containing `--` fully qualifies the sase agent, a
  bare value is a suffix under the calling agent. One syntax spells today's behavior and
  the future direction identically.
- Uniqueness is **(project, fully-qualified shell name)**, which — because a sase agent
  is sequential by definition — also yields one active shell per agent.
- **Keep `shell_name` (identity) and `concurrency_keys` (exclusion) as separate fields**,
  with a name implying exactly one key. ACE's exclusion is set-overlap and cannot be
  expressed by a scalar name; fusing them would repeat the `kind` mistake and would force
  every migrated ACE proc to mint a sase agent it has no business owning.
- Add ten nullable `ProcWire` fields at schema **v3** (a set entry, not a cutover), with
  **integer-millisecond** timeouts to preserve the `Eq` derive, plus atomic
  `reserve_proc` / `request_proc_stop` / `finish_proc` under the store lock.
- **Promote `monitor/supervise.py` + `supervisor_bootstrap.py` to the proc kernel and
  delete `procs/supervisor.py`.** Ship that phase alone. Reparenting and
  identity-over-pid become mandatory once procs are agent-startable.
- Keep `sase monitor` as a **direct service-level facade over `sase.procs`** — one Python
  import boundary, two CLI facades. Not a CLI wrapper (0.58 s and a version-skewing
  protocol), not a wrapper process (kill would destroy the process that must settle).
  Compile `-c '…'` to `["/bin/sh","-c","…"]` and persist that argv.
- Enforce one writer and one ordering rule so **terminal proc status ⇒ fully settled**,
  retiring `monitor_settled` and the claim-release race with it.
- Keep attached-shell logs in the artifacts dir: make **readers** path-driven, keep the
  **pruner** confined to `proc_logs_dir()`.
- Include standalone proc shells if convenient — they are cheap and they unlock
  `%wait`/`#fork` over procs — but do not gate anything on them.

**3. Then eliminate procs inside ACE and remove `--detached`.** Migrate **56 call sites
across 36 files** — via *both* `_submit_tracked_proc` (39, of which 24 are duck-typed
`getattr`) and `_submit_proc` (17), a surface both prior reports missed — putting each
command in its existing domain group rather than a `sase ace` namespace or a generic
payload dispatcher, and pushing shared behavior into `sase-core` per the backend-boundary
rule. Replace ACE's in-memory `dedup_key` / `exclusive_scopes` with store-wide
`concurrency_keys`. Demote sub-second work (`Stash prompt`, 90 ms against ~1.0–1.2 s of
startup) to plain Textual workers with no store row. Turn `ProcMirror` into a read-only
observer. Then remove `-d|--detached` from `run` *and* `list`, make
`include_unattributed` unconditional, keep `--session`, and reject `--detached` for one
release with an actionable message.

**Above all, when the kinds collapse: keep reading them.** `validate_kind` runs on read
and silently drops invalid rows, and every proc in the live store is `kind="tui"` — so
deleting the kind from `PROC_KINDS` erases the visible history of the very system this
work is meant to unify.
