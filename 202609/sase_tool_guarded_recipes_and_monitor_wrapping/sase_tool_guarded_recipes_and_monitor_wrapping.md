# Guarded recipes and monitor wrapping: the next step after `sase tool` E1

**Consolidated report** · 2026-09-22 · host athena · sase master `7f019258b`
**Sources:**

- researcher **cld** (`…__cld.md`): env-only recipe guard, default-on monitor wrap, and two
  wrapper bugs it reproduced and filed;
- researcher **mus** (`…__mus.md`): soft enforcement gated on a metric, verify-only monitor
  assist, a single-log-owner analysis;
- researcher **gem** (`…__gem.md`): a two-tier guard, catalog-aware monitor normalization,
  and the named-vs-ad-hoc cost;
- the lead researcher's own checks against today's tree, the ToolRun ledger, the monitor
  store, and agent `tool_calls.jsonl` (§9).

Context: `research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md`, the closed E1
epic `sase-135`, and `decisions:record-before-admit`.

**Question.** How should SASE (1) make sure agents run certain commands (such as
`just check`) through `sase tool`, with an override for when `sase tool` is broken, and
(2) make `sase monitor` wrap the commands it runs in `sase tool run`? Is the plan sound,
what would I change, and what do I recommend?

---

## 1. Answer up front

**Both steps are worth doing, but neither should be built as written, and three wrapper
defects have to be fixed first.**

1. **Enforcement: build a dependency-free guard inside the recipe, not a
   `sase tool ensure-not-agent` subcommand.**
   - **The rule.** An agent may run a guarded recipe only inside `sase tool run <that
     tool>`, or with an explicit bypass. The rule is not "the caller is not an agent":
     inside `sase tool run check` the child is still an agent process running
     `just check`.
   - **The inputs.** The decision needs three environment variables: `SASE_AGENT`
     (already set), `SASE_TOOL_NAME` (new, always exported by `sase tool run`) and
     `SASE_TOOL_BYPASS` (new, the override).
   - **The implementation.** A roughly 20-line POSIX script, wired as the first `just`
     dependency of `check` and `check-full`. It costs about 1 ms and never starts `sase`,
     so the override still works when `sase` itself is broken.
2. **Monitor wrapping: yes, but only in the argv the proc runs, never in the recorded
   monitor command.**
   - **Named upgrade.** A command that exactly matches a catalog tool (`just check`) runs
     as that named tool (`sase tool run check`), not as an ad-hoc run.
   - **Never wrapped.** Host-owned `execution_argv` launches (epic launches) and commands
     that already are `sase tool run …`.
   - **v1 scope.** Verify-profile monitors plus exact catalog matches. This is my call
     between cld's "default-on" and mus/gem's "verify only". A config field can widen it
     later.
   - **Already done.** Running arbitrary commands is already built: `sase tool run --
     ARGV…` shipped in E1.
3. **Fix three wrapper defects first.** Both steps push more work through the wrapper, and
   today the wrapper is less faithful than a raw command in three ways. Each one is filed:
   - **`sase-16c`: epic phase agents are misowned.** They inherit the live epic-launch
     monitor's id, so their `sase tool run check` runs get no compact output and no
     retained logs. A guard would *force* every phase agent onto this path.
   - **`sase-16b`: the wrapper orphans its child.** The child runs in a new session, so
     when a monitor timeout/stop or a provider tool timeout SIGKILLs the caller's process
     group, the `just check` tree survives unowned. cld reproduced it 5/5 and I reproduced
     it 2/2.
   - **`sase-16d` (new, found here): stdout/stderr order is lost.** In any merged view
     (monitor logs, agents' `2>&1 | tail`), output is regrouped: all stdout, then all
     stderr. I reproduced it 3/3.
4. **Be honest about the payoff.**
   - **Current adoption.** Since E1's guidance landed (2026-09-20), inline agent
     `just check` calls in the sase repo already go through `sase tool run` about 90% of
     the time. gem's "1.96% adoption crisis" number comes from a window dominated by calls
     made before that guidance existed.
   - **Where the gap is.** About 80% of the remaining raw heavy calls are in linked repos
     (mostly sase-core). Those repos have no tool catalog, so a guard in sase's `Justfile`
     can't reach them.
   - **Why build it anyway.** It is cheap. And E4 (receipts), E6 (forecasting corpus) and
     especially E7 (fail-closed admission) all need "every heavy agent run is a ToolRun"
     to hold by construction, not by habit.
5. **This changes an accepted decision.** `decisions:record-before-admit` says adoption is
   "instruction-led … so bypass is measured, not enforced." A guard reverses that clause,
   so it needs a new decision record that partly supersedes the old one.

**Recommended delivery:** one small epic, **"E1.5: enforced adoption"**, with four phases,
landing before E2:

1. fix the ownership roots;
2. fix the wrapper's process-group and output-stream fidelity;
3. add the recipe guard;
4. add monitor wrapping.

E2's `sase tool run -H check` then becomes "start a verify monitor whose command is
`check`" (§7).

---

## 2. Where the reports disagreed, and how I resolved it

| Topic | cld | mus | gem | Resolution (evidence) |
| --- | --- | --- | --- | --- |
| How bad is adoption? | about 90% in-repo after guidance; the residual is in linked repos | improving; wait for a stall | 1.96%, a "crisis" | **cld.** My own count since the E1 landing: 18 wrapped vs 1–2 raw in the sase repo, and 9 raw in linked repos (§4.1). gem's 7-day window is mostly pre-guidance. The report also selects files by modification time, so it pulls in older calls. |
| Build the guard now or later? | now: cheap, and needed structurally | only if the metric stalls for about 2 weeks | now: "prose fails" | **Now, but small**, and framed as a prerequisite for E4/E7, not as an adoption rescue. |
| Guard layer | POSIX script, env-only | Python helper plus `sase tool require-wrapped` | shell fast-path, then `sase tool guard` to print the error | **POSIX, env-only.** Any `sase` process on the refusal path fails exactly when `sase` is broken. gem's tier 2 would print a traceback instead of the bypass instructions (§5.3). |
| Proof that a run is wrapped | new, always-exported `SASE_TOOL_NAME` | `SASE_TOOL_RUN_ID` | `SASE_TOOL_RUN_ID` | **cld.** `executor_process.child_env` *removes* `SASE_TOOL_RUN_ID` when recording failed. A guard keyed on it would refuse the child of a fail-open `sase tool run check` (verified in code). |
| Refuse or redirect? | refuse | prefer redirect (`exec sase tool run`) | refuse | **Refuse** (§5.9). A `just` dependency can't replace the running recipe, so redirecting would require splitting each recipe into a stub and a private body. It also hides the contract. A refusal costs one call of a few milliseconds. |
| Override shape | `SASE_TOOL_BYPASS='<why>'` | `SASE_TOOL_ALLOW_DIRECT=1`, no reason | `SASE_TOOL_BYPASS=1` | **`SASE_TOOL_BYPASS`.** Any non-empty value bypasses. Guidance asks for a short reason, which is echoed to stderr and not validated. |
| Which recipes are guarded | `check` and `check-full` | `check` and `check-full` | also `test` | **`check` and `check-full` only.** Guarding `just test` mostly pushes agents to call pytest directly, which can't be guarded. |
| Monitor wrap scope | default-on with exclusions (fallback: verify-only) | verify profile, catalog commands only | catalog match anywhere; verify profile gets an ad-hoc wrap | **Verify profile plus exact catalog matches**, controlled by a config field (§7.4). Since E1, this covers 6 of the 9 monitors that need wrapping; the other three are a CI watch and two ad-hoc scripts. |
| Where the wrap is applied | proc argv only; `monitor_command` untouched | "rewrite" (unspecified) | rewrite `command` and set `execution_argv` | **cld.** Host completion reads `monitor_execution_argv` or `monitor_command` (`host_completion_state._command_argv`). Rewriting either one breaks every `-f` binding. |
| Named vs ad-hoc | named upgrade on exact match | named rewrite | named rewrite; says ad-hoc "loses stages" | **Named upgrade.** But gem overstated the cost: stage events are ingested for *any* recorded run (`executor.py` builds the `StageIngestor` whenever `recorded`). What ad-hoc loses is catalog identity, declared inputs, the toolchain fingerprint, LAST/TYPICAL, and later receipt eligibility. |
| Prerequisite bugs | `sase-16b`, `sase-16c` | none | env leak (hypothetical) | **cld's two, plus `sase-16d`**, which I found (§5.6). |
| Where the env scrub goes | at agent launch (new scrub set) | — | inside `scrub_agent_identity_env` | **At agent launch**, as a separate helper. `scrub_agent_identity_env` also runs in monitor and proc supervisors, where the owner variables are set on purpose. |
| Guard CLI latency | measured 0.25–0.43 s | — | estimated 80–120 ms | **Measured.** Either way, it's a cost every human and every CI run would pay. |
| Rust core impact | — | none | — | **Mostly none.** The guard and monitor policy live in Python/shell. The spawn-time pgid record for `sase-16b` probably touches the sase-core ToolRun wire and reconcile, which means a pin bump (§7.3). |

---

## 3. Verified facts that constrain the design

| Fact | Where / how verified | Consequence |
| --- | --- | --- |
| Ad-hoc `sase tool run -- ARGV…` exists, with no implicit shell | `tool/argv.py`; `docs/tool.md` | Monitor wrapping needs no new execution mode. A shell string becomes `-- /bin/sh -c CMD`. |
| Agents carry `SASE_AGENT=1` (plus `SASE_AGENT_NAME` and others) | this agent's env; `finalizers/prepare.py`, `artifact_cli/create.py` key on it | A cheap, established agent signal. |
| Monitor and proc supervisors scrub `SASE_AGENT*`, then set `SASE_MONITOR_ID` / `SASE_PROC_ID` | `monitor/supervise.py`, `procs/supervisor.py::_child_environment`, `procs/spawn.py` | A guard keyed on `SASE_AGENT` can't see monitors *or* `sase proc run -- just check`. By design. |
| Finalizer subprocesses get an allowlisted env with no `SASE_AGENT` | `finalizers/executor_support.py::sanitized_env` | Host-owned verification is unaffected by the guard. |
| `child_env(recorded=False)` removes `SASE_TOOL_RUN_ID` and `SASE_TOOL_RUN_EVENTS` | `tool/executor_process.py` | A new always-exported marker is needed. |
| Child is spawned with `start_new_session=True`; wrapper escalates after 5.0 s, supervisor SIGKILLs after 5.0 s | `executor_process.py`, `procs/supervisor.py` | The kill race (`sase-16b`). **I reproduced it 2/2**: wrapper got SIGKILL at 5.01 s, `sh` and `sleep` survived, and the run went `lost`. |
| Child stdout and stderr use separate pipes and two pump threads; monitors merge with `stderr=STDOUT` | `executor_process.py`, `monitor/supervise.py:308` | Order is lost (`sase-16d`). **Reproduced 3/3**: `out1…out6 err1…err6` wrapped vs `out1 err1 out2 err2…` direct. |
| Agent launch scrubs only `SASE_AGENT*` and the chop/job env | `agent/launch_spawn.py`, `agent/env_hygiene.py` | Phase agents inherit `SASE_MONITOR_ID`. `ownership._monitor_has_settled` only drops it once `done.json` exists (`sase-16c`). |
| Host completion reads `monitor_execution_argv` or else `monitor_command` | `monitor/host_completion_state.py::_command_argv` | The wrap must leave both fields alone. The proc wire already separates `argv` from `command`. |
| `check-full` doesn't invoke `just check` | `Justfile` | A strict per-tool name match has no nested-recipe conflict. |
| Linked repos have no catalog | `sase tool list` in the sase-core checkout says "no named tools in this project" | The guard and the named upgrade can't reach them until they get catalogs. |
| Ledger (athena): 204 runs; `check` 145 failed / 34 succeeded / 13 lost / 2 signaled; 17 monitor-owned, 13 of them with `agent: null` and 4 misowned by `sase-135.7` | `sase tool runs -a -j` | Attribution and ownership bugs are live. A 76% `check` failure rate (red master) means acceptance can't depend on a green check. |

---

## 4. Evidence: what enforcement and wrapping buy right now

### 4.1 Inline agent calls since the E1 landing (2026-09-20 16:25Z, heavy means ≥20 s)

I reused `tools/tool_adoption_report`'s own `classify()`, filtered by each call's timestamp
rather than the file's modification time, and split the "ambiguous" bucket by hand:

| Bucket | Count | Notes |
| --- | --- | --- |
| Wrapped, simple | 4 | |
| Wrapped inside a compound | 14 | `just fix …; timeout 3000 sase tool run check 2>&1 \| tail -60` and similar |
| Raw, sase repo | 1–2 | `just check 2>&1 \| tail -60` (cwd unknown), `(just install) && just check` |
| Raw, **linked repos** | 9 | 4 with an explicit `cd` into sase-core, sase-telegram, or sase-research-artifacts; 5 inferred as sase-core from Rust-only output patterns (`cargo fmt`, `^test … ok$`) |
| False positives (prose) | 4 | "just check" inside `sase bead note`/`+1` text or heredocs |

**In the sase repo, about 90% of calls are wrapped (18 of about 20). Across all repos it's
about 62% (18 of 29).** cld independently found the same split. Caveat: `tool_calls.jsonl`
summaries don't record cwd, so 5 of the 9 linked-repo attributions are inferred.

### 4.2 Monitors since the E1 landing (41 total)

| Class | Count | Wrap decision (§7.4) |
| --- | --- | --- |
| Epic launches (`sase bead work`, host-owned) | 19 | never wrap |
| Already `sase tool run …` (all verify profile) | 13 | leave unchanged |
| Verify profile: raw `just check`, `just test-scoped` ×2, pytest, `just install`, `just fix-tui-screenshots` | 6 | wrap: `just check` becomes named `check`, the rest ad-hoc |
| No profile: 2 `/tmp` scripts, 1 CI watch | 3 | v1 leaves them unwrapped |

Since 2026-09-15, **0 of 251 monitors used prepared completion (`-f`)**, and 17 timed out
and 1 was stopped (the `sase-16b` path). Verify-profile adoption is now very high:
cld counted 172 of 176 verification-like monitors. So the roadmap's old worry that
"opt-in profiles go unused" (1/69) no longer applies to the verify profile.

### 4.3 What this means

In the sase repo, the guard closes a residual of roughly one or two calls every two days
and protects against regression. **Its real value is structural**, and it grows with each
epic:

- **E4 receipts** reuse and mint only through the wrapper, so a raw `just check` neither
  benefits from a receipt nor creates one.
- **E6's corpus** is biased when the raw remainder differs systematically from the wrapped
  runs, and it does: linked repos and compound commands.
- **E7's fail-closed admission** is meaningless if the admitted path is optional.

Monitor wrapping has a similarly small marginal effect on `check` right now, since agents
already type `-- sase tool run check`. Its value is:

- recording the non-catalog verification commands (`test-scoped`, pytest, scripts);
- removing something agents must remember;
- giving E2 its bridge.

---

## 5. Critique of the plan

### 5.1 The direction is right

Guidance has worked unusually well: about 90% wrapped within two days. But every
downstream epic needs coverage that is guaranteed, not just high, and a cheap guard plus
monitor wrapping is the right pair of mechanisms. The user's instinct to require an
override is also correct. Without one, a broken `sase` would block all verification.

### 5.2 "ensure-not-agent" states the wrong rule

All three researchers agree. Agents are *supposed* to end up running `just check`; they
just have to do it through `sase tool run check`, whose child still has `SASE_AGENT=1`. So
the recipe has to tell apart:

- an agent running it raw;
- an agent running it wrapped for this tool;
- a human;
- CI;
- a finalizer;
- a monitor.

A command named `ensure-not-agent` that *passes* for agents would be misleading. Name the
guard after the rule instead: `require_tool_run check`.

### 5.3 A `sase` subcommand can't be the gate

- **The override would be circular.** The override exists for the case where `sase` is
  broken: a stale `sase_core_rs` wheel, an import error, a bad install. A guard that is
  itself a `sase` process crashes in exactly those states. gem's two-tier variant and
  mus's Python helper both still invoke `sase` on the refusal path. The refusal then
  shows a traceback instead of the bypass instructions, just when the agent needs them.
- **Every run would pay for it.** Every human and CI `just check` would take on about
  0.3 s and a dependency on `sase` being on PATH, for logic that needs three environment
  variables.
- **It adds CLI surface.** A new subcommand needs help text, an alias, and ordering under
  `cli_rules.md`. A `sase tool` verb is still useful later as a *read* surface, such as
  `sase tool list` marking which tools are guarded.

### 5.4 The guard must not key on `SASE_TOOL_RUN_ID`

E1 is deliberately fail-open. When recording fails, the command still runs, but
`SASE_TOOL_RUN_ID` is cleared. A guard keyed on that variable would refuse the child of
`sase tool run check` and tell the agent to run the command it just ran. The fix is a
one-line change in `child_env`: always export `SASE_TOOL_NAME=<tool>` (or `ad-hoc`),
whether or not recording succeeded.

### 5.5 The guard can't see monitors or procs, which is why the two steps belong together

Supervisors scrub agent identity on purpose. That makes `sase monitor start -- just check`
and `sase proc run -- just check` invisible to an `SASE_AGENT` guard. Refusing inside
monitors would be wrong: the refusal fires after the starting agent's turn has ended, so
it wastes a monitor run and a follow-up agent. The monitor half has to be **wrapping**, so
step 2 is the detached half of step 1. `sase proc run` is left to E2's standalone leg.

### 5.6 Enforcement first makes three wrapper defects universal

This is the strongest ordering argument, and the reason my phase order differs from
cld's. Today a raw `just check` is more robust than the wrapped form in three ways:

- **`sase-16c`: misowned phase agents.** Epic phase agents inherit the live epic-launch
  monitor's `SASE_MONITOR_ID`. Their `sase tool run check` is recorded as monitor-owned,
  so they get no compact output and no retained logs. With a guard in place, *every* phase
  agent is forced onto this path.
- **`sase-16b`: orphaned child trees.** The child lives in its own session. A SIGKILL of
  the caller's process group, whether from the supervisor's 5.0 s escalation or a provider
  tool timeout, kills only the wrapper. The `just check` tree keeps burning the capacity
  the roadmap is trying to measure, and the run settles `lost` with no recorded pgid. 13
  of 195 `check` runs are already `lost`. A guard makes the wrapper mandatory for every
  heavy inline run, and default wrapping sends every verify monitor's timeout through the
  race.
- **`sase-16d` (new): stream order is lost.** Two pipes pumped by two threads regroup
  interleaved output whenever stdout and stderr share a target. That covers the monitor
  log, which is the *only* log for monitor-owned runs, and agents' common
  `sase tool run check 2>&1 | tail -60`. Failure evidence handed to follow-up agents gets
  worse. The fix: when an owner holds the output, or when fds 1 and 2 are the same file,
  give the child one merged pipe.

### 5.7 "Wrap every monitor" is wrong in five ways

1. **Epic launches.** Wrapping `sase bead work` makes every phase agent's runs children of
   a long-lived ad-hoc run. That is `sase-16c` one level up.
2. **Double records.** `-- sase tool run check` is the documented idiom. Wrapping it again
   makes two ToolRuns for one semantic run, which breaks the roadmap invariant.
3. **Host completion.** Rewriting `monitor_command` or `monitor_execution_argv` breaks
   every `-f` binding (verified).
4. **The kill race** (`sase-16b`).
5. **Noise with no identity.** Sleeps, CI watches and ad-hoc scripts produce ToolRuns with
   no stable identity. They add little to E6 and add retention cost.

### 5.8 Two more design gaps

- **Attribution regresses.** 13 of 17 monitor-owned runs have `agent: null` because the
  supervisor scrubbed identity. The monitor already knows its starter (`reserved_by`), so
  it should pass that in a tool-specific variable rather than by restoring `SASE_AGENT*`.
- **The largest residual is out of reach.** The linked-repo raw calls need catalogs in
  those repos first. That deserves its own decision, because a `sase/sase.yml` in a
  linked repo may make other code treat it as a SASE project root.

### 5.9 Refuse, don't redirect (for now)

mus's redirect has real appeal: no friction, and no need to retrain callers. But:

- **It doesn't fit `just`.** A dependency can't replace its recipe. Redirecting means a
  public `check` stub plus a private `_check` body that the catalog points at, and
  double-run hazards if the stub is written carelessly.
- **It hides a behavior change.** Once E4 receipts or E6 auto-routing exist, a plain
  `just check` could silently return a cached receipt or hand off to a monitor, which
  ends the agent's turn.

A refusal costs one few-millisecond call and prints the exact remedy. Revisit after E6.

### 5.10 Governance

`decisions:record-before-admit` lists "bypass is measured, not enforced" as an accepted
cost. Its reopen condition (a measured concurrent-duplicate or queue-starvation rate)
hasn't been met, so this is a deliberate change of course, not a reopening.

The new record, "Agents run guarded recipes only through `sase tool run`", should:

- partly supersede that cost clause and back-link to it;
- note that *recording* stays fail-open, since a guard enforces routing, not
  recording-success;
- state its own reopen condition: sustained bypass above X%, or false refusals.

Write it through `/sase_memory_write`.

---

## 6. Adjusted requirements (my changes, flagged)

- **ADJ-1: Reshape step 1.** Replace `sase tool ensure-not-agent` with an env-only POSIX
  recipe guard, `tools/require_tool_run TOOL`. Its rule: an agent must be inside
  `sase tool run TOOL`, or have set a bypass. *Why:* §5.2–5.4.
- **ADJ-2: New always-exported marker.** `sase tool run` exports `SASE_TOOL_NAME` whether
  or not recording succeeded. *Why:* §5.4.
- **ADJ-3: One override concept.** `SASE_TOOL_BYPASS='<why>'`, honored by both the guard
  and monitor wrapping, echoed to stderr, and counted by the adoption report. The guard
  also fails open when `sase` isn't on PATH. *Why:* the user required an override, and
  giving a reason makes it auditable without a new store.
- **ADJ-4: Narrow guard scope.** v1 guards only `check` and `check-full` in the sase repo.
  `test` and `install` are never guarded. Linked repos come later, after they get
  catalogs. *Why:* §4.1, §5.8.
- **ADJ-5: Wrap only the proc argv.** Monitor wrapping never changes `monitor_command` or
  `monitor_execution_argv`. It never wraps host-owned launches or already-wrapped
  commands, and it upgrades exact catalog commands to named runs. *Why:* §5.7.
- **ADJ-6: Scope wrapping by config.** v1 wraps verify-profile monitors plus exact catalog
  matches. Use a config field (`off | verify | all`, default `verify`), not a flag, because
  scope is a durable user choice. *Why:* §4.2, §2.
- **ADJ-7: Prerequisites are in scope.** `sase-16c`, `sase-16b` and `sase-16d` land
  **before** the guard and the default wrap. *Why:* §5.6.
- **ADJ-8: Carry attribution.** Monitor-wrapped runs record the agent that started the
  monitor. *Why:* §5.8.
- **ADJ-9: Governance.** Write a new decision record that partly supersedes
  `record-before-admit`'s bypass clause. *Why:* §5.10.
- **ADJ-10: Sequencing.** Ship this as a small epic before E2. E2's `-H` is then built on
  monitor wrapping. *Why:* the guard is independent and low-risk, so it shouldn't wait on
  E2's larger scope.

---

## 7. Recommended solution

### 7.1 The environment contract (document it in `docs/tool.md`)

Any repo, whether a Justfile, a Makefile or an npm script, can implement the guard from
this contract in a few lines.

| Variable | Set by | Meaning |
| --- | --- | --- |
| `SASE_AGENT` | agent runner (already) | this process tree is a SASE agent's own shell |
| `SASE_TOOL_NAME` | **new:** `sase tool run`, always | the tree is inside `sase tool run <name>` (or `ad-hoc`) |
| `SASE_TOOL_BYPASS` | **new:** an agent or human, per command | run raw on purpose; the value is the reason |

### 7.2 The recipe guard (cld's prototype, verified by cld with just 1.58)

```sh
#!/bin/sh
# Refuse a raw agent invocation of a guarded named-tool recipe.
# Env-only by design: it must work when `sase` itself is broken.
tool=${1:?usage: require_tool_run TOOL}
[ -n "${SASE_AGENT:-}" ] || exit 0                    # humans, CI, finalizers, monitors
[ "${SASE_TOOL_NAME:-}" = "$tool" ] && exit 0          # inside `sase tool run $tool`
if [ -n "${SASE_TOOL_BYPASS:-}" ]; then
    printf 'sase: running `just %s` raw (SASE_TOOL_BYPASS: %s)\n' "$tool" "$SASE_TOOL_BYPASS" >&2
    exit 0
fi
command -v sase >/dev/null 2>&1 || {                    # no sase at all: fail open
    printf 'sase: `sase` not on PATH; running `just %s` raw\n' "$tool" >&2; exit 0; }
printf 'sase: agents run this recipe as `sase tool run %s` (it records a ToolRun).\n' "$tool" >&2
printf "  if sase tool is broken: SASE_TOOL_BYPASS='<why>' just %s\n" "$tool" >&2
exit 2
```

```just
# Agents must run guarded tools through `sase tool run` (docs/tool.md).
_require-tool-run name:
    @tools/require_tool_run {{ name }}

check: (_require-tool-run "check") _setup
check-full: (_require-tool-run "check-full") _setup
```

The guard runs before `_setup`, so a refusal costs milliseconds, not a dependency sync.
The name match is strict (`SASE_TOOL_NAME` must equal the tool):
`sase tool run -- sh -c 'just install && just check'` is refused and steered toward
`just install && sase tool run check`, which keeps the named identity. The guard is a
guardrail against habit, not a security boundary: `env -u SASE_AGENT` defeats it. The
bypass is deliberately easier and more visible than that.

**Measurement.** Extend `tools/tool_adoption_report` with two things:

- a `bypassed` class (`SASE_TOOL_BYPASS=… just check`);
- a refusal count (an exit-2 raw call followed by a wrapped one).

While there, filter by each call's timestamp, not the file's modification time, so
windows can't mix in older calls.

**Optional follow-on.** Add `guard: agents` on catalog entries, rendered by
`sase tool list`, and have `just validate` check that each guarded tool's recipe starts
with the guard. This keeps the catalog as the source of truth without the gate depending
on `sase`.

### 7.3 Executor and ownership changes (the prerequisites)

- **Always export `SASE_TOOL_NAME`** in `child_env`.
- **Scrub at agent launch.** A new `scrub_executor_ownership_env` helper, called where
  agents are launched (`agent/launch_spawn.py` and the admission/launch-condition paths),
  removes `SASE_TOOL_*`, `SASE_MONITOR_*` and `SASE_PROC_*`. An agent is a new root for
  ownership and enforcement. As a second safeguard, ownership resolution can ignore an
  inherited monitor/proc id when `SASE_AGENT` is set. This fixes `sase-16c`.
- **Process groups (`sase-16b`).**
  - Under a live monitor/proc owner, spawn the child in the wrapper's own process group
    and skip the wrapper's own SIGKILL escalation. The owner's `killpg` then reaches the
    whole tree, and the owner remains the single process owner.
  - For inline runs, the plan must choose a way for the child tree to die with the
    wrapper when the caller's group is SIGKILLed: same process group, or a death signal
    plus a reap.
  - Record `child_pid`, `child_pgid` and the process identity **right after spawn**, for
    example as an appended event, so reconcile can reap a `lost` run's surviving group.
    This part likely needs a small sase-core wire/reconcile change and a
    `sase-core-revision.txt` bump.
- **Stream fidelity (`sase-16d`).** When output is owned by an enclosing owner, or fds 1
  and 2 are the same file, give the child a single merged pipe.
- **Attribution.** The monitor passes its starter in `SASE_TOOL_RUN_AGENT`, which
  `begin_tool_run` uses when `SASE_AGENT_NAME` is absent.

### 7.4 Monitor wrapping

The wrap goes into the argv built in `monitor/start.py`, where
`compile_monitor_argv`/`monitor_proc_argv` are called. `monitor_command` stays exactly as
the agent wrote it, and `monitor_execution_argv` stays unset for ordinary monitors.

| Monitor | Proc argv |
| --- | --- |
| Host-owned `execution_argv` launch (epic `sase bead work`) | unchanged, **never** wrapped |
| Exactly one `sase tool run …` (any path to `sase`) | unchanged |
| A simple command equal to a catalog tool's argv (extra args only if the tool allows them), with cwd at that catalog's project root, **any profile** | `<sase> tool run <name>` (**named**) |
| Anything else under `-p verify`: compound commands, scripts, `just test-scoped`, pytest | `<sase> tool run -- /bin/sh -c CMD` (ad-hoc; an inner `sase tool run check` becomes its child) |
| Anything else without the verify profile | unchanged in v1 (`monitor.tool_wrap: all` widens this) |
| `SASE_TOOL_BYPASS` in the starter's env, `monitor.tool_wrap: off`, or tool bindings unavailable | unchanged, plus one `sase: running unwrapped (<reason>)` line in the monitor log |

- **`<sase>` must match the supervisor's installation**, i.e. `sys.executable -m sase`,
  not whatever `sase` is first on PATH.
- **The monitor log stays the output of record.** Owner-mode runs retain no duplicate
  stdout/stderr (one log owner), so `sase tool show -l` is empty for them by design.
- **Test the evidence extraction.** Check that `--next-output auto` tolerates the
  wrapper's `sase tool run <id>` and completion lines.
- **New config field.** `monitor.tool_wrap` must be added to `src/sase/default_config.yml`
  (repo gotcha).

**Guidance updates** (through `/sase_memory_write` and the `sase_monitor` skill source):

- plain `-- just check` becomes equivalent to `-- sase tool run check`;
- the "prepared-completion `-f` monitors still use raw `just check`" caveat is dropped,
  because they are now recorded too;
- the stale-install fallback becomes `SASE_TOOL_BYPASS='<why>' just check` plus a
  recorded `sase update`.

### 7.5 Delivery: "E1.5: enforced adoption" (4 medium phases, no beta flag)

1. **`ownership-roots`:** fix `sase-16c` (agent-launch scrub plus the ownership
   safeguard), export `SASE_TOOL_NAME`, and record the pgid and identity at spawn.
   *Verifiable:* a phase agent's `sase tool run check` produces compact output again, and
   `show -l` replays it.
2. **`wrapper-fidelity`:** owner-mode process group, inline death-with-wrapper, reconcile
   reaping (`sase-16b`), and the merged-stream mode (`sase-16d`). Both repros become
   regression tests. *Verifiable:* a timed-out monitor running a TERM-ignoring child leaves
   nothing behind; a wrapped `2>&1` shows interleaved order.
3. **`recipe-guard`:** the script and Justfile wiring, the decision record,
   `lint_and_test.md`, `docs/tool.md`, and the adoption report's `bypassed` and refusal
   classes. *Verifiable:* inside an agent, `just check` exits 2 with the three-line
   message, while `sase tool run check` and `SASE_TOOL_BYPASS=why just check` both run.
   Run the full test matrix: human, CI, finalizer, agent-raw, agent-wrapped,
   agent-wrapped-as-other-tool, recording-failure-wrapped, bypass, and no-`sase`-on-PATH.
4. **`monitor-wrap`:** the §7.4 policy, the `monitor.tool_wrap` config, attribution, the
   bypass, and the skill update. *Verifiable:* `sase monitor start -p verify -- just check`
   produces exactly one named `check` run with `owner_kind=monitor` and the starter
   agent; an `-f` monitor's host completion still succeeds; an epic launch creates no
   ToolRun.

Phases 1 and 2 are independent and can run in parallel. The guard (phase 3) must follow
both.

**No beta flag.** Per `sase_flags.md`, a beta flag is only for landed phases that would
expose an unfinished feature. Here each user-visible piece ships complete in its own
phase. `SASE_TOOL_BYPASS` is a permanent interface, and `monitor.tool_wrap` is a config
field.

**Acceptance must not depend on a green master.** `check` currently fails 76% of the
time in the ledger, so every exit criterion above is stated as observable behavior, not
"check passes".

### 7.6 Explicitly out of scope

- guards and named upgrades for linked repos (they need catalogs first);
- wrapping `sase proc run` (E2's standalone leg);
- redirect mode (revisit after E6);
- guarding `test` or `install`;
- any fail-closed admission (E7).

---

## 8. Open questions for Bryan

1. **Monitor wrap default.** `verify` (my recommendation: it covers all local verification
   seen since E1 and skips CI watches and scripts), or `all` (cld: one uniform rule)? The
   config field makes this cheap to change later.
2. **Strict vs lenient guard match.** Strict (`SASE_TOOL_NAME` must equal the recipe's
   tool; recommended) or "any `sase tool run`"? Lenient is friendlier but gives up named
   identity.
3. **Linked-repo catalogs.** Should sase-core, sase-telegram and the others get `tools:`
   catalogs so the guard and named upgrades reach the biggest remaining raw residual? This
   first needs a check that a `sase/sase.yml` in a linked repo doesn't make it look like a
   SASE project root.
4. **Epic placement.** E1.5 as its own small epic before E2 (recommended), or folded into
   E2 as its first phases?

---

## 9. Lead verification appendix (athena, 2026-09-22, tree `7f019258b`)

- **Code read:**
  - `tool/executor_process.py`: `child_env`, `spawn_child`, `wait_child`;
  - `tool/executor.py`: recording, `StageIngestor` on any recorded run, pgid sent only at
    finish;
  - `tool/ownership.py`: settled-only monitor staleness, existence-only parent check;
  - `agent/env_hygiene.py` and its callers;
  - `monitor/proc_adapter.py`, `monitor/start.py`, `monitor/supervise.py`,
    `monitor/host_completion_state.py`, `procs/supervisor.py`;
  - `finalizers/executor_support.py`, `Justfile` (`check`/`check-full`),
    `sase/sase.yml` `tools:` (check, check-full, install, test, test-visual).
- **Kill race, 2/2.**
  - Setup: isolated `SASE_HOME`, `SASE_MONITOR_ID` set, running
    `sase tool run -- sh -c "trap '' TERM; sleep 31.4159"`; after 3 s, SIGTERM to the
    wrapper's pgid, then SIGKILL at 5.0 s.
  - Result: the wrapper exited -9 at 5.01 s, `sh` and `sleep` survived, and the run showed
    "exit time was not observed".
  - Survivors were killed and the temporary homes removed.
- **Stream order, 3/3.**
  - Setup: isolated `SASE_HOME`, `SASE_MONITOR_ID=fakemon`, agent identity unset,
    `2>&1`.
  - Result: wrapped output grouped all stdout before all stderr; the direct run
    interleaved.
  - Filed as **`sase-16d`** (task(bug), medium, ready), linked `related` to `sase-16b` and
    `sase-16c`. Duplicate search and the one-week task sweep found no match, and no
    in-progress epic has a causal link.
- **Adoption.**
  - `tools/tool_adoption_report -d 1/2/3 -j`: 2/0/10, 5/1/37 and 10/5/83
    (wrapped/raw/ambiguous).
  - The §4.1 split used the report's `classify()` over `~/.sase/projects/*/artifacts/**/tool_calls.jsonl`,
    filtered by call timestamp ≥ 2026-09-20T16:25Z.
- **Monitors.** `sase monitor list -a -j` (1,318 rows), classified since 09-15 and since
  09-20; `completion_ref` was empty for all 251 since 09-15.
- **Ledger.** `sase tool runs -a -j`: 204 runs, with the state, owner and agent breakdown
  in §3.
- **Decision text.** Checked with
  `sase memory read decisions:record-before-admit decisions:check-full-is-explicit`.
- **Beads read.** `sase-135` (E1 landing note), plus `sase-16b` and `sase-16c` (filed by
  cld today; both are ready and linked `related`).
- **Side effects.**
  - The repro runs used isolated `SASE_HOME`s, so they added no rows to athena's ledger.
  - One task bead was created (`sase-16d`).
  - The three researcher reports were moved into this directory. The `sase-16b` and
    `sase-16c` descriptions still cite the cld report's old path,
    `research:202609/sase_tool_guard_and_monitor_wrap__cld.md`, which now lives at
    `research:202609/sase_tool_guarded_recipes_and_monitor_wrapping/sase_tool_guarded_recipes_and_monitor_wrapping__cld.md`.
