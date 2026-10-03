# Why apollo keeps killing all of its SASE agents (OOM): root cause and fix

**Researcher:** cld · **Date:** 2026-10-03 · **Host investigated:** `apollo` (DigitalOcean droplet,
Ubuntu 24.04.3, kernel 6.8.0-138, systemd 255.4, 16 vCPU, 31 GiB RAM, **no swap**)

## TL;DR

There are two separate defects, and every wipe-out needs both of them:

1. **What triggers it: `bob query` blows up memory (bob-cli).** Agents that work on the Bob
   vault run Dataview queries such as `FLATTEN file.tasks AS t … GROUP BY t.status` across
   the whole vault. bob's native Dataview engine **deep-clones the entire page object once
   per flattened task**, so a page with N tasks costs N × (a page that itself contains N
   tasks). That is O(N²) memory per page. `GROUP BY` then clones every row two more times.
   The vault has pages with 2,413, 2,012, 819 and 509 tasks. One 509-task page alone adds
   4.1 GiB, and one 819-task page goes past 8 GiB. A whole-vault FLATTEN needs tens of GiB,
   so the 31 GiB box hits a global OOM in 7–49 s. **All 3 real OOM kills since boot line up
   with an unscoped `bob query … FLATTEN file.tasks` that was running at that moment and
   died in the same second.** Every unscoped FLATTEN query in the agent history caused an
   OOM, and every OOM had one running. Scoped queries (`FROM "2026"`) succeeded.
2. **Why it kills *every* agent: shared tmux-pane cgroup plus `OOMPolicy=stop` (sase).**
   The ACE TUI runs in a tmux pane, and tmux puts each pane in its own transient
   `tmux-spawn-<uuid>.scope`. `sase.detach_scope` only moves launched work into its own
   scope when the parent is a SASE-owned unit (`sase.service` / `sase-*.scope`). Under tmux
   it does nothing, so **every agent the TUI launches lives in the TUI's tmux scope**. The
   user manager's `DefaultOOMPolicy=stop` applies to that scope. When the kernel OOM-kills
   one process in it (the runaway `bob query`), systemd **stops the whole scope**: SIGTERM,
   then SIGKILL 90 s later, to the TUI and every agent and child. I reproduced both halves
   on apollo.

**Recommended solution (details in §8):**

- **(A) Today, no code:** on apollo, set `DefaultOOMPolicy=continue` in
  `~/.config/systemd/user.conf`, re-exec the user manager, and restart the TUI inside a
  `sase-tui-*` scope.
- **(B)** Tell agents not to run whole-vault `FLATTEN file.tasks`; use `TASK` queries
  instead. A `TASK` query answers the same question in 1.6 GiB.
- **(C)** Fix the clone-heavy row model in bob-cli's Dataview engine and add a memory
  guardrail.
- **(D)** Land the in-flight sase `detach_scope` change, after fixing its systemd version
  gate (it needs 253, not 243). Then put agent scopes in a memory-capped slice.

---

## 1. Symptom, as recorded by systemd

I don't have sudo or `adm` on apollo, so the kernel ring buffer and `/var/log/kern.log` are
unreadable. The **user** journal (`journalctl --user`) still records what the user manager
did with each OOM kill. All times are UTC. Agent artifact directory names are in EDT
(UTC−4).

| OOM kill (UTC) | Unit (TUI tmux pane) | What systemd did | Agents that died at that moment |
| --- | --- | --- | --- |
| 2026-10-01 21:15:46 | `tmux-spawn-a291e399….scope` (alive since 09-30 11:53, 5d17h CPU) | "A process of this unit has been killed by the OOM killer" → 21:16:09 "Failed with result 'oom-kill'" | 6: a 5-agent bob-cli swarm (agy/gemini-3.8-flash-high, grok-4.6, claude/opus, muse, codex/gpt-6.1-sol) + 1 sase muse agent. All `failed` within 2–9 s of the kill |
| 2026-10-03 16:24:28 | `tmux-spawn-1a05ddb8….scope` (alive since 10-01 21:15, **29.0G memory peak**) | Stop → "Stopping timed out. Killing." → SIGKILL to the surviving `zsh`, `python3`, `claude` at 16:25:58 → "Failed with result 'oom-kill'" | 3: bob-cli claude/opus (24 min in), bob-cli codex, sase codex |
| 2026-10-03 17:32:39 | `tmux-spawn-d263949a….scope` (TUI restarted 16:26) | Stop → 17:33:03 "Failed with result 'oom-kill'" | 2: sase muse `sase-1fs.1--1` (outcome `killed`), bob-cli codex `4r.f1.f0` |

Each time, the user opened a new tmux pane and restarted `sase -p tui` a few seconds
later. You can see this as a new `tmux-spawn-*` scope starting right after each kill.

Kernel and cgroup counters confirm these were **global** OOMs, not hits on a cgroup limit:

- `/proc/vmstat oom_kill` was **3** before my experiments. It reads 9 now, because six of my
  deliberately capped probes were killed.
- Every one of the 3 real kills is inside `user@1000.service`. `system.slice` shows
  `oom_kill 0`.
- `memory.max` is `max` (unlimited) on `user.slice`, `user-1000.slice` and
  `user@1000.service`. Their `memory.events.local` all show `oom 0`.
- `systemd-oomd` is inactive, so the kernel OOM killer is the actor.

## 2. Trigger: an unscoped `bob query … FLATTEN file.tasks` was running at every OOM

I replayed every agent's `tool_calls.jsonl` under `~/.sase/projects/*/artifacts/ace-run/` on
apollo. Exactly **8** agent tool calls ever ran `bob query` with `FLATTEN file.tasks|lists`:

| Started (UTC) | Scoped with `FROM`? | Ended | Outcome |
| --- | --- | --- | --- |
| 09-30 11:50:13 | yes | 11:50:13 | success |
| 09-30 19:12:39 | yes (`FROM "2026"`) | 19:12:47 | success |
| 09-30 19:12:53 | yes (`FROM "2026"`) | 19:13:28 | success |
| **10-01 21:15:35** | **no** (`GROUP BY t.status`) | **21:15:46 interrupted** | **OOM #1** |
| **10-01 21:15:35** | **no** (`GROUP BY t.fresh`) | **21:15:46 interrupted** | **OOM #1** (the same codex agent ran 3 queries in parallel) |
| **10-01 21:15:39** | **no** (`GROUP BY t.refresh`) | **21:15:46 interrupted** | **OOM #1** |
| **10-03 16:23:44** | **no** (`WHERE t.blockId = "ref" GROUP BY t.status`) | **16:24:28 interrupted** | **OOM #2** |
| **10-03 17:31:50** | **no** (`WHERE t.blockId = "ref" GROUP BY status`) | **17:32:39 interrupted** | **OOM #3** |

The correlation is complete in both directions. Every unscoped whole-vault FLATTEN query was
killed at the exact second of an OOM, 7–49 s after it started, and every OOM had one in
flight. The queries came from codex agents in the `bob-cli` project doing a `^ref` task
census or a task-lane census. This is the textbook Obsidian Dataview idiom: it is cheap in
real Dataview, which shares JS object references, but catastrophic in bob's native engine.

Other candidates I checked and ruled out:

- **The TUI process.** Its `tui_memory_heartbeat` log shows RSS swinging between 0.6 and
  2.6 GiB over hours (GC "rss_backstop" pauses keep it bounded). That is large, but it is
  not the 25+ GiB consumer, and it is not the OOM victim either (see §4).
- **`sase tool run` jobs (`just check` etc.).** `~/.sase/tools/runs.sqlite` shows **no**
  tool run active at 21:15:46 or 16:24:28. At 17:32 the only one had settled 31 s earlier.
- **`sase-checks-*` scopes.** There are about 10k of these in 5 days, which is journal
  noise. They are tiny `gh` PR-status and comment checks (`checks_runner.py`).
- **tmpfs, `/dev/shm` and `/run/user` growth.** All are empty, and `free` shows 4 MiB shared.
- **A cgroup memory limit.** None is configured anywhere (see above).

## 3. Why `bob query` needs tens of GiB: the engine's row model (bob-cli)

I opened the code via `sase repo open bob-cli`. It is the same `src/native/dataview/` that the
deployed `~/.cargo/bin/bob` on apollo was built from. The last change to `vault.rs` is the
2026-09-28 module split. The engine lives in `src/native/dataview/vault.rs` and `eval.rs`.
`DataviewValue` is a fully owned tree (`Array(Vec<…>)`, `Object(BTreeMap<String, …>)`, no
`Rc`/`Arc`), so **every `.clone()` is a deep copy**.

1. **`NativeRow::page` deep-copies the whole page.** `page_rows()` builds one row per page with
   `value: vault.page_value(page_index)`. `page_value` clones every field of the page,
   including `file.tasks`, `file.lists`, links and frontmatter.
2. **`flatten_rows` clones that whole page once per element:**
   ```rust
   for value in values {                       // values = this page's file.tasks
       flattened.push(row.clone().with_field(field, value));   // deep copy of the page
   }
   ```
   `with_field` then inserts the task into both `variables` and the cloned page object.
   A page with N tasks therefore materializes N copies of a value that itself holds N tasks
   (plus `file.lists`, which repeats them, and nested `children`). Memory is
   **Σ_pages N_p × size(page_p) ≈ Σ N_p² × (bytes per task)**.
3. **`NativeRow::group` (GROUP BY) clones every row twice more.** It builds `rows_value` from
   `row.value.clone()` for every row, then inserts `rows_value.clone()` into the group object
   and `rows_value` into `variables`.
4. **`NativeRow::context()` clones `variables` on every expression evaluation**
   (`variables: self.variables.clone()`). After GROUP BY, `variables["rows"]` is the group's
   whole row array. So each `length(rows)` cell and each SORT comparison makes yet another
   deep copy of a group.
5. `group_rows` looks up groups with a linear `iter_mut().find(...)`. That only costs CPU
   (O(rows × groups)), not memory.

The vault (`~/bob` on apollo: 5,795 notes, 21,049 checkbox lines) has a few very large task
pages: `_generated/queries/query/links/inbox_links.md` (2,413 tasks),
`_generated/queries/zoq/all_read.md` (2,012), `done/gtd_daily_done.md` (819),
`done/sase_done.md` (509), `sase.md` (285). Those generated pages have existed since June.
What changed recently is that agents started running unscoped FLATTEN queries.

### Measurements on apollo

Each probe ran in a throwaway `systemd-run --user --scope -p MemoryMax=… -p MemorySwapMax=0`
scope under `/usr/bin/time`, so it could not hurt live agents:

| Query (Max RSS / outcome) | Tasks flattened from one page | Result |
| --- | --- | --- |
| `TABLE … FROM "done/bob_done"` (no FLATTEN), the index baseline | – | **2.85 GiB**, 8.9 s. *Every* `bob query` pays this |
| `… FROM "done/bob_done" FLATTEN file.tasks AS t` | 170 | 2.85 GiB (no visible growth) |
| `… FROM "done/sase_done" FLATTEN file.tasks AS t` | 509 | **6.96 GiB** (+4.1 GiB), 15.8 s |
| same + `GROUP BY t.status` | 509 | **> 8 GiB, OOM-killed in its scope** |
| `… FROM "done/gtd_daily_done" FLATTEN file.tasks AS t` | 819 | **> 8 GiB, OOM-killed** |
| `… FROM "done" FLATTEN file.tasks AS t GROUP BY t.status` | whole folder | **> 6 GiB within 12 s, OOM-killed** |
| `TASK WHERE blockId = "ref" GROUP BY status` (same census, safe form) | – | **1.62 GiB**, 8.8 s, correct output |

From the 509-task page, one copy of that page costs about 8 MiB, roughly 16 KiB per task once
the page's tasks, lists and children are expanded into `BTreeMap`s. Extrapolating:
`inbox_links.md` alone, at 2,413², needs somewhere around 25–90 GiB, depending on how heavy
its generated link-tasks are. A whole-vault `FLATTEN file.tasks` **cannot finish on a
31 GiB host**, and the kill times (7–49 s) match the measured growth rate. The Oct 1
incident ran three of these in parallel (codex parallel tool calls), on top of three
2.85 GiB index baselines.

## 4. Why one runaway query takes down the TUI and every agent (sase)

### 4.1 Agents share the TUI's tmux-pane scope

tmux on Ubuntu 24.04 is built with systemd support. Every new pane process is moved into a
transient `tmux-spawn-<uuid>.scope` ("tmux child pane N launched by process 2210" in the
journal). The TUI runs in one of those. Its agents are launched through
`sase.agent.launch_spawn` → `sase.detach_scope.detach_scope(..., unit_prefix="sase-agent")`:

```python
parent_unit = _current_systemd_unit(proc_root=proc_root)
if not _is_sase_owned_systemd_unit(parent_unit):      # tmux-spawn-*.scope → False
    return _DetachScopeCommand(command, ...)            # no escape
```

`_is_sase_owned_systemd_unit` only accepts `sase.service`, `sase-axe*.scope` and other
`sase-*.scope`/`sase-*.service` units. The journal confirms the consequence: in five days
apollo **never started a single `sase-agent-*` scope**. Right now, the running agent runner
and its `muse` CLI sit in the TUI's scope:

```
runner 3000293  cgroup=…/user@1000.service/tmux-spawn-c5a838fd-….scope
cli    3004812  muse-bin … exec --json  cgroup=…/user@1000.service/tmux-spawn-c5a838fd-….scope
```

So `bob query`, every LLM CLI, every runner and the TUI are all members of one systemd unit.

### 4.2 `OOMPolicy=stop` turns one kill into a scope-wide teardown

`systemctl --user show -p DefaultOOMPolicy` returns `stop`, and every live `tmux-spawn-*`
scope (and `sase.service`) has `OOMPolicy=stop`. Scopes honour `OOMPolicy=` since systemd 253
(apollo's own `/usr/share/doc/systemd/NEWS.gz`: *"Scope units now support OOMPolicy=. Login
session scopes default to OOMPolicy=continue"*). tmux creates its scopes without setting
it, so they inherit `stop`.

I reproduced this on apollo with a 300 MiB-capped scope containing a background `sleep`, a
child that allocates 900 MiB, and the wrapper shell:

| `OOMPolicy` | Result |
| --- | --- |
| `stop` (the default) | The child is OOM-killed, **then systemd SIGTERMs the whole scope**: the sibling and wrapper die and `systemd-run` exits 143. Journal: "A process of this unit has been killed by the OOM killer" → "Failed with result 'oom-kill'". This is the production signature |
| `continue` | Only the child dies (exit 137). The `sibling_alive` check passes, the wrapper finishes, and the scope exits 0 |

In production, the 16:24 event even shows systemd waiting out the default 90 s stop timeout
and then SIGKILLing the leftover `zsh`, `python3` and `claude` processes.

### 4.3 Who the kernel actually killed

The kernel picks the task with the highest `rss + swap + pagetables + oom_score_adj ×
totalpages/1000`. On apollo the `sase.service` daemons (`sase service run`, scheduler,
gateway, axe routines) run with **`oom_score_adj=200`**, which is worth about 6.3 GiB of
RSS. Their `/proc/*/oom_score` is about 800, while the TUI at 1.36 GiB (adj 0) scores 694.
So **an adj-0 process in the TUI scope only beats those daemons once its RSS is above
~6.3 GiB.** The TUI, the LLM CLIs and the runners never get that big. The `bob query` does.

That makes the victims the runaway queries, and the TUI and agents were collateral of
`OOMPolicy=stop`. It also explains why the TUI always died together with the agents: the
TUI is in the same scope.

### 4.4 Open question

The 17:32 teardown logged "4.3G memory peak" for the TUI scope. That doesn't fit a
>6.3 GiB victim inside the same scope; the 16:24 event logged 29.0G. I could not confirm
the exact victim without kernel logs, but the argument in §4.3 shows the victim must have
been a >6 GiB adj-0 process. The `bob query` started at 17:31:50 is the only candidate, and
it was interrupted at 17:32:39.98. Treat the 4.3G number as unreliable. Note that
`memory.peak` also counts page cache, which is why earlier TUI panes reported 22–27 GiB
peaks without any OOM. To close this definitively, run with sudo:

```bash
sudo journalctl -k --since "2026-10-03 17:31" --until "2026-10-03 17:34" | grep -A45 "invoked oom-killer"
sudo journalctl -k --since "2026-10-01" | grep -E "Out of memory: Killed process|oom-kill:"
```

The `Killed process … (bob)` lines and their `anon-rss` values should match.

## 5. Contributing factors

- **No swap and no memory limits.** Any anon spike goes straight to a global OOM, and nothing
  contains a single agent's tool.
- **A 2.85 GiB baseline per `bob query`.** Indexing 5.8k notes plus `page_rows()`
  deep-copying every page makes even harmless queries heavy. Parallel tool calls multiply
  this.
- **The `bob_query` skill encourages `bob query` for vault-wide questions** ("Use `bob query`
  instead of manually parsing large parts of the vault") and says nothing about FLATTEN's
  cost or `TASK` queries.
- **Long-lived TUI panes accumulate the blast radius.** Every agent launched from the TUI
  in the last ~1–2 days (forks, swarms, follow-ups) sits in the same doomed scope.

## 6. Work already in flight

There is an **uncommitted** change in apollo's `sase_10` sase workspace. It has no bead and
isn't on `origin/master`. The `sase-detach-oom-test-*` "SASE detach-scope OOMPolicy
regression" scopes that ran in the journal at 16:43–17:22 today came from its tests. It:

- adds an escape path when the caller's user manager is reachable (`escape_reason="user_manager"`),
  so tmux-pane launches get their own scope;
- appends `--property=OOMPolicy=continue` to every detached scope;
- adds `runner_kill_provenance.py`, which records why a runner died.

This is the right shape for half of the fix, but it has one bug. It gates `OOMPolicy` on
**systemd ≥ 243** (`_OOM_POLICY_MIN_SYSTEMD_VERSION = 243`). Scope support only arrived in
**253**; 243 added `OOMPolicy=` for *services*. On systemd 243–252 hosts (e.g. Ubuntu 22.04
= 249, Debian 12 = 252), `systemd-run --scope --property=OOMPolicy=continue` should be
rejected, and every detached launch would fail. The gate needs to be 253.

## 7. Why it started now

Nothing on apollo's kernel or systemd side changed. The engine's FLATTEN/GROUP BY code dates
from July (bob-cli-9.x), and the 2k-task generated pages date from June. What is new
(09-30 onward) is agents, mostly codex in `bob-cli`, doing vault-wide task censuses with
idiomatic Dataview `FLATTEN file.tasks … GROUP BY`. Combined with the pre-existing
"all agents in the TUI's scope + `OOMPolicy=stop`" design, each such query became a
fleet-wide wipe-out.

## 8. Recommended solution

Apply the layers in order. (A) and (B) stop the bleeding today; (C) and (D) are the durable
fixes.

### (A) Today, on apollo, no code: contain the blast radius

1. Make OOM kills stop tearing down whole units, for the user manager only (no sudo):
   ```bash
   mkdir -p ~/.config/systemd
   printf '[Manager]\nDefaultOOMPolicy=continue\n' >> ~/.config/systemd/user.conf
   systemctl --user daemon-reexec          # re-reads user.conf; running units survive
   systemctl --user show -p DefaultOOMPolicy   # expect: DefaultOOMPolicy=continue
   ```
   Existing scopes keep `stop`, because `systemctl --user set-property … OOMPolicy=` is
   refused on a live scope (I tested this). The setting only applies to **new** tmux panes
   and scopes.
2. Restart the TUI **inside its own `sase-tui-*` scope** (in a fresh tmux window):
   ```bash
   systemd-run --user --scope -p OOMPolicy=continue --unit="sase-tui-$(date +%s)" sase -p tui
   ```
   Because the unit name matches `sase-*.scope`, the **currently deployed** `detach_scope`
   treats the TUI as SASE-owned and puts every agent it launches into its own
   `sase-agent-*.scope`. I verified this on apollo: inside such a scope, `detach_scope`
   returns `escaped=True` with a `systemd-run --user --scope … --unit=sase-agent-…`
   command, and in a plain pane `escaped=False`. Together with step 1, an OOM now kills
   only the runaway process (e.g. `bob query`). Its agent sees the command exit with 137
   and carries on, and the TUI and other agents are untouched. A shell alias such as
   `alias ace='systemd-run --user --scope -p OOMPolicy=continue --unit="sase-tui-$(date +%s)" sase -p tui'`
   makes this the default.

### (B) Today: stop agents from firing the trigger

Add a rule and an example to the `bob_query` skill source, which is deployed as
`~/.claude/skills/bob_query/SKILL.md`. The rule: *never `FLATTEN file.tasks` or
`file.lists` over the whole vault. Scope with `FROM "<folder or note>"` first, or use a
`TASK` query, e.g. `TASK WHERE blockId = "ref" GROUP BY status` (1.6 GiB, 9 s).* Until (C)
lands, also tell agents not to run `bob query` calls in parallel. bob-cli's own agent docs
or memory should say the same, because those agents are the ones writing these queries.

### (C) Root-cause fix in bob-cli: make FLATTEN and GROUP BY linear

Pick one of the two designs in the first bullet; the rest apply either way.

- **Stop deep-copying page values into rows.** Option 1: make `NativeRow` hold
  `page_index` plus a small overlay (`variables`) and resolve page fields lazily through
  `vault.page_field_value(…)` by reference. Option 2: switch `DataviewValue::Array` and
  `Object` to `Arc`-backed storage, with `Arc::make_mut` for copy-on-write in
  `with_field`. Either way, `flatten_rows` should add only the flattened binding (one
  task) per row, not a page copy. Memory then becomes O(total tasks) instead of
  O(Σ N_p²).
- **GROUP BY:** build `rows` from shared references once and store it once; don't keep
  separate copies in the object and in `variables`.
- **`EvalContext`:** borrow `variables` (`&'a BTreeMap` or `Cow`) instead of
  `self.variables.clone()` on every evaluation.
- **`group_rows`:** use a `HashMap` key index instead of a linear `find`.
- **Guardrail:** give the engine a row and memory budget. For example, refuse with "this
  FLATTEN would materialize N rows; add FROM/WHERE" above a threshold, and/or self-apply
  `RLIMIT_AS`/`--max-memory` with a sane default (e.g. 4 GiB). A bad query should then fail
  fast with an actionable error instead of OOMing the host.
- **Regression test:** add a synthetic vault with one 2,000-task note, and require
  `TABLE … FLATTEN file.tasks AS t GROUP BY t.status` to stay under a few hundred MiB.
- **Later:** trim the 2.85 GiB baseline. `page_rows()` clones every page up front, and the
  index stores tasks in both `file.tasks` and `file.lists`.

### (D) Durable containment in sase

- **Land the in-flight `detach_scope` change** (§6), with the `OOMPolicy` gate fixed to
  **systemd ≥ 253**. That gives every TUI- or CLI-launched agent, monitor and proc its own
  scope with `OOMPolicy=continue`, without the alias in (A).
- **Cap agent memory collectively.** Launch agent scopes with `--slice=sase-agents.slice`,
  and ship a `sase-agents.slice` with e.g. `MemoryHigh=22G` and `MemoryMax=26G` (tune to
  host RAM, leaving room for the TUI, `sase.service` and the OS). A runaway tool then
  triggers a **cgroup** OOM inside the slice instead of a global one. The kernel picks the
  largest process in the slice, which is the runaway, and `OOMPolicy=continue` keeps its
  agent alive. An optional per-agent `MemoryMax` gives finer isolation.
- **Surface the cause.** Finish `runner_kill_provenance`, so a killed agent shows
  "OOM-killed child `bob` (N GiB)" instead of a bare `failed`/`killed`.

### (E) Optional host hardening

Add a modest swapfile (8–16 GiB; the droplet has 51 GiB of free disk) or more RAM, to
absorb legitimate spikes. This is **not** a fix: a whole-vault FLATTEN needs more memory
than any reasonable swap. Keep `systemd-oomd` off until agents live in separate scopes,
because oomd kills whole cgroups and would recreate today's blast radius.

### Verification after the fix

- `journalctl --user -g "oom" --since today` should show at most single-process kills, and
  no `Failed with result 'oom-kill'` on `tmux-spawn-*` or `sase-tui-*` units.
- `grep oom_kill /proc/vmstat` (the baseline today is 9).
- Re-run the unsafe census under a cap:
  `systemd-run --user --scope -p MemoryMax=6G bob query --format markdown --query-file q.dql`
  with the 10-03 query. Before (C) only `bob` should die, and after (C) it should complete
  in well under 1 GiB above baseline.
- `cat /proc/$(pgrep -f 'sase -p tui')/cgroup` should show `sase-tui-*.scope`, and running
  agents' cgroups should show `sase-agent-*.scope`.

## Appendix: evidence sources

- **apollo user journal:** `journalctl --user` (scope starts and stops, OOM lines,
  "Consumed … memory peak").
- **cgroup and kernel counters:** `/sys/fs/cgroup/user.slice/**/memory.{max,events,events.local,stat}`,
  `/proc/vmstat`, `/proc/<pid>/{cgroup,oom_score,oom_score_adj}`.
- **SASE logs on apollo:**
  - `~/.sase/logs/runs.jsonl` (agent outcomes and durations)
  - `~/.sase/logs/tui_stalls.jsonl` (`tui_memory_heartbeat` RSS)
  - `~/.sase/logs/workspace_claims.jsonl`
  - `~/.sase/tools/runs.sqlite` (tool runs)
  - `~/.sase/projects/*/artifacts/ace-run/**/tool_calls.jsonl` (the exact commands that were
    in flight)
- **Code:**
  - sase `src/sase/detach_scope.py`, `src/sase/agent/launch_spawn.py`
  - bob-cli `src/native/dataview/vault.rs` (`flatten_rows`, `group_rows`, `NativeRow::{page,
    group, context, with_field}`, `page_value`), `eval.rs` (`EvalContext`), `value.rs`
    (`DataviewValue`)
- **Experiments run on apollo:** the capped `bob query` probes in §3, the `OOMPolicy`
  stop/continue reproduction in §4.2, the `set-property` refusal, and the `sase-tui-*`
  scope escape check. All probe scopes and temp files were cleaned up.
