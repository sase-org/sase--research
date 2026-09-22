# Guarding named tools and wrapping monitors in `sase tool run`

**Researcher cld** · 2026-09-22 · host athena · sase master `7c763a2e7b` · core pin
`c5186cc4af` · just 1.58.0

**Question.** What's the best way to (1) make sure SASE agents run certain commands
through `sase tool run`, with an override for when `sase tool` is broken, and (2) make
`sase monitor` wrap the commands it runs in `sase tool run`? The user also asked for a
general critique of the plan, justified requirement adjustments (clearly flagged), and a
recommended solution.

**Context read:** `research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md`, the
`sase-135` epic bead and its landing note, `plan:202609/tool_e1_named_tools.md`,
`decisions:record-before-admit`, `decisions:check-full-is-explicit`,
`decisions:single-turn-agents`, `decisions:host-owned-completion`, `lint_and_test.md`,
`sase_flags.md`, `cli_rules.md`, and the shipped code in `src/sase/tool/`,
`src/sase/monitor/`, `src/sase/procs/supervisor.py`, `src/sase/finalizers/`, the
`Justfile`, and `sase/sase.yml`.

---

## 1. Answer up front

**Both steps point the right way, but neither should be built exactly as written.** Each
one runs into a hidden defect, and each has a design detail that would otherwise break
something already shipped.

1. **Enforcement: yes, but put it in the recipe as a dependency-free shell guard, not in
   a `sase tool ensure-not-agent` subcommand.** The rule to enforce is not "the caller is
   not an agent". It is "an agent may run this recipe only inside `sase tool run` for this
   tool, or with a stated bypass." That decision needs only three environment variables,
   so it should be computed without starting `sase`. The override exists for the case
   where `sase` is broken, so a guard that depends on `sase` fails in exactly the situation
   it is meant to handle. A 20-line POSIX `tools/require_tool_run` wired as the first
   `just` dependency of `check` and `check-full` costs about 1 ms and is provider-neutral.
   It also catches compound commands, pipes, and scripts. I prototyped it (§9).
2. **Monitor wrapping: yes, default-on, but not literally every monitor, and only after
   two prerequisite bug fixes.** Wrap at the point where `sase monitor start` compiles the
   proc argv. Keep the semantic `monitor_command` unchanged so the prepared-completion
   exact-command contract still holds. Skip commands that are host-owned execution-argv
   launches (epic launches) or that are already a single `sase tool run …`. When the
   command is exactly a catalog tool (`just check`), run the named tool instead of an
   ad-hoc run. Ad-hoc `sase tool run -- ARGV` already exists, so the "you might need to
   implement arbitrary commands" part is already done.
3. **Two live defects must be fixed first.** I reproduced both on athena today and filed
   them:
   - **`sase-16b`:** `sase tool run` puts its child in a new session. When a monitor
     times out or is stopped, the proc supervisor SIGKILLs the wrapper at 5.0 s, before
     the wrapper's own 5.0 s escalation fires. The whole `just check` tree survives as an
     orphan and the run settles `lost`. This reproduced 5 out of 5 times, and there were
     17 verify-monitor timeouts on athena in the last week.
   - **`sase-16c`:** epic phase agents inherit the *live* epic-launch monitor's
     `SASE_MONITOR_ID`, so their `sase tool run check` runs are recorded as monitor-owned.
     They get no compact output and no retained logs. There are four such runs by
     `sase-135.7` in the ledger right now. Wrapping monitors, or relying on inherited env
     markers for enforcement, would spread this class of bug.
4. **This revises an accepted decision.** `decisions:record-before-admit` says adoption is
   "instruction-led … so bypass is measured, not enforced." A guard changes that stated
   cost, so it needs a new decision record that partly supersedes it (§4.7).
5. **Evidence check: instructions already work in this repo. The guard's value is mostly
   structural and comes later.** Two days after E1's guidance landed, heavy `just check`
   calls in the sase repo are about 90% wrapped. Most of the remaining raw calls are in
   **linked repos such as sase-core, which have no catalog**, so a guard in the sase
   `Justfile` can't reach them. The guard is still worth building now because it's cheap,
   and because E3, E4, E6 and especially E7 (fail-closed admission) all need "every agent
   heavy run is a ToolRun" to hold by construction, not by habit.

**Recommended delivery:** one small epic, "E1.5 — enforced adoption", of about four
phases:

- (1) fix the env boundary (`sase-16c`) and add the always-exported `SASE_TOOL_NAME`
  marker;
- (2) the recipe guard with the `SASE_TOOL_BYPASS` override;
- (3) fix owner-mode process groups (`sase-16b`);
- (4) default-on monitor wrapping, with the named-tool upgrade, the exclusions, and
  attribution.

E2 (durable hand-off) then builds on it: `sase tool run -H check` becomes "start a monitor
whose command is `check`." Details are in §7.

---

## 2. What exists today (verified on this tree)

| Fact | Where | Consequence for this work |
| --- | --- | --- |
| Ad-hoc runs exist: `sase tool run -- ARGV…`, with no implicit shell | `src/sase/tool/argv.py` `_parse_run_words` | Monitor wrapping needs no new execution mode. A monitor's shell string becomes `-- /bin/sh -c CMD`. |
| Agent processes carry `SASE_AGENT=1` (plus `SASE_AGENT_NAME` etc.) | env of this agent; `finalizers/prepare.py:635` | A cheap, reliable agent signal. |
| Monitor/proc supervisors **scrub `SASE_AGENT*`** from the monitored command and set `SASE_MONITOR_ID`, `SASE_PROC_ID` | `procs/supervisor.py::_child_environment`, `monitor/start.py` env overlay | An `SASE_AGENT`-based guard is blind inside monitors, by design. That's why step 2 is needed. |
| Finalizer subprocesses get a minimal allowlisted env (no `SASE_AGENT`) | `finalizers/executor_support.py::sanitized_env` | Host-owned verification is unaffected by a guard. |
| The executor exports `SASE_TOOL_RUN_ID` / `SASE_TOOL_RUN_EVENTS` **only when recording began**, and clears them otherwise | `tool/executor_process.py::child_env` | A guard keyed on `SASE_TOOL_RUN_ID` would refuse a fail-open run whose store is broken (§4.3). |
| The child is spawned with `start_new_session=True`. Wrapper escalation is `TERM_ESCALATE_SECONDS = 5.0`. | `tool/executor_process.py` | Races the supervisor's 5.0 s grace (`sase-16b`). |
| Proc supervisor: SIGTERM the child pgid, SIGKILL after `_KILL_GRACE_SECONDS = 5.0` | `procs/supervisor.py::_Termination` | Same. |
| Monitors run `/bin/sh -c COMMAND` through the proc supervisor. Epic launches pass `execution_argv` (code-swap bootstrap). | `monitor/proc_adapter.py`, `monitor/start.py` | The wrap goes into the proc argv. Exclude execution-argv launches. |
| Host completion binds the exact verification argv, and settlement observes `monitor_execution_argv` or `monitor_command` | `finalizers/prepare.py` bind; `monitor/host_completion_state.py::_command_argv` | The wrap must not alter either field. |
| Ownership treats an inherited monitor id as stale **only after the monitor settles** | `tool/ownership.py::_monitor_has_settled` | Live epic-launch monitors misown phase-agent runs (`sase-16c`). |
| `child_pid` / `child_pgid` are sent only in `finish_tool_run` | `tool/executor.py` | A `lost` run never records which group to reap. |
| sase-core has no `sase/sase.yml`; `sase tool list` there says "no named tools in this project" | ran it | A guard or wrapper for linked repos needs catalogs first. |

---

## 3. Evidence: how much does enforcement buy right now?

### 3.1 Inline agent calls (`tools/tool_adoption_report`, athena, run 2026-09-22)

| Window | wrapped | raw | ambiguous (pipelines / compound) | wrapped share of classifiable |
| --- | --- | --- | --- | --- |
| 7 days (mostly before guidance) | 10 | 500 | 205 | 2.0% |
| 2 days (after E1 phase 6 guidance) | 8 | 1 | 39 | 88.9% (wall share 96.6%) |

I split the 2-day "ambiguous" bucket by hand: **27 wrapped-in-compound**
(`timeout 3000 sase tool run check 2>&1 | tail -60`, `just fix && sase tool run check`, …)
and **20 raw-in-compound**. Of the 20, about 4 are false positives (prose mentioning
"just check" inside `sase bead note`, `sase memory read`, and similar). About 11–13 are in
**linked repos**, such as `cd sase/repos/linked/sase-core && just check`, `cargo fmt && just check`,
sase-telegram, and sase-research-artifacts. **Only about 3–5 are genuinely raw `just check` in
the sase repo.** Within the sase repo the instruction-led adoption rate is already about
90%, well above E1's ≥70% target.

### 3.2 Monitors (`sase monitor list -a -j`, 1,317 monitors since 2026-08-13)

- 22% of all monitors (290) are **epic launches** (`sase bead work …`). Since 09-15, 64 of 65
  use `execution_argv`, but one still ran as a plain shell command.
- Since 09-15, **172 of 176 verification-like monitors use `-p verify`**. The roadmap's
  "verify profile 1/69" figure is stale, so the profile is now a reliable signal. Zero use
  prepared completion (`-f`).
- Since 09-20, 13 monitored commands contain `sase tool run` and one is a raw `just check`.
  Before 09-20 it was hundreds raw (423 `check-full`, 317 `check` overall).
- 17 verify-ish monitors **timed out** and 1 was stopped in the last week. Each one went
  through the kill path in §4.5.

### 3.3 The ToolRun ledger (athena, 202 runs)

- 17 runs are monitor-owned. **13 of them have no agent attribution**, because the monitor
  scrubbed `SASE_AGENT_NAME`. **4 are misowned by the live epic-launch monitor**
  `136v0dbr3pv1` (`sase-16c`), and their `logs` contain only `events_path`.
- 13 inline `check` runs are `lost` (about 7%), all attributed to agents. Their child pgid
  was never recorded, so whether the trees were orphaned can't be determined after the
  fact (`sase-16b`).

### 3.4 What the evidence means

The guard's **marginal** value in the sase repo today is small: it closes a residual of
roughly 10% and guards against regression. Its **structural** value is large and grows
over time:

- E3's KNOWN/NEW classification and E4's receipts are only as good as their coverage.
- E6's corpus is biased if the raw remainder differs systematically. Compound commands in
  linked repos do.
- **E7 admission can't be meaningfully fail-closed if the guarded path is optional.** An
  admission controller that sees 90% of heavy runs misprices the other 10% as free.

The guard is cheap (§7.1), so building it now is justified. It should be framed as the
prerequisite for admission, not as an adoption fix.

---

## 4. Critique of the plan

### 4.1 "ensure-not-agent" names the wrong rule

Agents are *supposed* to run `just check`, through `sase tool run check`, whose child
really is `just check` with `SASE_AGENT=1` still set. The recipe has to distinguish
"agent, raw" from "agent, wrapped", "human", "CI", "finalizer" and "monitor". The rule is
**agent ⇒ wrapped-for-this-tool ∨ bypassed**. The name should say that, for example
`require_tool_run check`. A command called `ensure-not-agent` that passes for agents is
confusing to read in a Justfile.

### 4.2 A `sase` subcommand can't be the guard

- **The override is circular.** The override exists for "`sase tool` is broken". A guard
  implemented in `sase` crashes or refuses in exactly those states (stale `sase_core_rs`
  wheel, import error, bad install). To fail open it would need a shell pre-check anyway,
  and then the shell pre-check *is* the guard.
- **Cost and coupling for everyone.** `sase tool list` takes about 0.28 s and
  `sase tool run -- true` about 0.41 s on athena. Every human and CI `just check` would pay
  that and depend on `sase` being on PATH. The env-only shell guard measured **1.1 ms**.
- **CLI surface.** A new subcommand needs help text, a short alias, and alphabetical
  placement (`cli_rules.md`), all for logic that needs none of `sase`.

A `sase tool` verb is still useful later as a *read* surface, for example
`sase tool list` showing which tools are guarded. It shouldn't be the gate.

### 4.3 The guard must not key on `SASE_TOOL_RUN_ID`

E1 is deliberately fail-open. If `begin` fails (unwritable store, lock contention), the
command still runs, and `child_env(recorded=False)` **clears** `SASE_TOOL_RUN_ID`. A guard
keyed on that variable would refuse the child of `sase tool run check`, and tell the
agent to run the command it just ran. The executor needs a separate marker that it
**always** exports, independent of recording. I recommend `SASE_TOOL_NAME=<tool>`, or
`ad-hoc` for ad-hoc runs. It's a one-line change in `child_env` and it matches the
"recording stays fail-open" invariant.

### 4.4 The guard is blind in monitors, and that's why the two steps belong together

Monitor and proc supervisors scrub `SASE_AGENT*` on purpose. So `sase monitor start -- just check`
passes an `SASE_AGENT` guard. There are two ways to close the gap:

- **Refuse inside monitors** (the guard also keys on `SASE_MONITOR_ID`). This is bad. The
  refusal fires *after* the starting agent's turn has ended, so it wastes a whole monitor
  cycle plus a follow-up agent launch just to deliver "use `sase tool run`". It would also
  refuse prepared-completion `-f` monitors, which today must use raw `just check`.
- **Wrap at the monitor** (step 2). There's no friction, it covers compound commands and
  scripts, and it covers `-f` monitors because the semantic command is unchanged.

So step 2 isn't a separate nice-to-have. It's the monitor half of the enforcement story.
The guard covers inline calls and monitor wrapping covers detached calls.

### 4.5 "Wrap every monitor" is wrong in four specific ways

1. **Epic launches.** Wrapping `sase bead work …` would give every phase agent an
   inherited ToolRun marker. Their `sase tool run check` would record as a *child* of the
   epic-launch run, with no output ownership, no compact output, and no retained log. This
   is `sase-16c` again, one level up. `_parent_exists` checks existence, not liveness, and
   the parent would be live for hours anyway.
2. **Double records.** `sase monitor start -- sase tool run check` is now the documented
   idiom. Wrapping it again creates two ToolRuns for one semantic run, which violates the
   roadmap invariant "one semantic run = one ToolRun id".
3. **Host completion.** Prepared completion binds the exact verification argv, and
   settlement observes `monitor_execution_argv` or `monitor_command`. If wrapping is
   implemented by rewriting either field, every `-f` monitor fails its binding. The wrap
   has to live only in the proc argv, which the proc wire already separates from `command`.
4. **The kill race (`sase-16b`).** The supervisor sends SIGTERM to the wrapper's pgid,
   waits 5.0 s, then SIGKILLs it. The wrapper forwards SIGTERM to the child's *separate*
   session and arms its own 5.0 s escalation on its first 0.1 s tick, so it always loses.
   If the tree needs more than 5 s to exit on SIGTERM, the wrapper dies, the tree lives on
   unowned, and the ToolRun goes `lost`. This reproduced 5/5 (§9). Today it only affects
   monitors whose agent typed `sase tool run`. Wrapping by default would put **every**
   monitor timeout and stop through it, currently 17+ per week on athena.

### 4.6 Attribution regresses unless the wrap carries it

Because monitors scrub agent identity, 13 of 17 monitor-owned ToolRuns have
`agent: null`. If monitors become the main source of heavy ToolRuns, `sase tool runs -A`
and any per-agent triage (E3) go blind. The monitor knows its starter agent, so the wrap
should pass it as a tool-specific attribution variable, not by restoring `SASE_AGENT*`.

### 4.7 It changes an accepted decision

`decisions:record-before-admit` ("Cost") says: *"adoption is instruction-led (guidance
plus the wrapper — provider hooks are gone), so bypass is measured, not enforced."* A
recipe guard reverses that clause. Its stated reopen condition (a measured
concurrent-duplicate or queue-starvation rate) hasn't been met, so this is a genuine
change of course, not a reopening. Per the decisions web's rules, write a new record
("Agents run guarded recipes only through `sase tool run`") that partly supersedes the
old one's cost clause and back-links it. Do this through `/sase_memory_write`. The new
record should state the reopen condition for removing the guard: sustained bypass
>X% or guard false-refusals.

### 4.8 The largest raw residual is outside this repo

Most of the remaining raw heavy `just check` calls are `sase-core` and other linked
repos (§3.1). They have no catalog, and `sase tool run check` there fails with "no named
tools". A guard in sase's Justfile can't touch them. Extending enforcement means giving
those repos catalogs first. That's worth its own decision, because a `sase/sase.yml` in a
linked repo may make it look like a SASE project root to other code. It shouldn't be
bundled into v1.

### 4.9 Sequencing against the roadmap

The roadmap's next epic is E2 (durable hand-off: `sase tool run -H`). Monitor wrapping is
the same link seen from the other side: E2 goes tool → monitor, wrapping goes monitor →
tool. Doing wrapping first *simplifies* E2. With wrapping in place, `-H` is "start a
`-p verify` monitor whose command is the named tool". The monitor's wrap creates the one
ToolRun, and the link already lives on the tool side (`owner_kind=monitor`), which is the
roadmap's rule. I'd ship this work as a small epic just before E2, rather than as part of
E2, so the guard (independent, low-risk) isn't held behind E2's larger scope.

---

## 5. Options considered

### 5.1 Where enforcement lives

| Option | Verdict | Why |
| --- | --- | --- |
| **A. `sase tool ensure-not-agent` subcommand** (user's proposal) | Reject as the gate | Circular with the "sase is broken" override, about 0.3 s per call for everyone, CLI surface for env-only logic, and the name states the wrong rule (§4.1–4.2) |
| **B. POSIX recipe guard `tools/require_tool_run TOOL`** as the first `just` dependency | **Recommend** | About 1 ms, no `sase` dependency, provider-neutral, fires however the recipe was reached (compound commands, pipes, scripts), and the policy is visible in the Justfile next to the recipe |
| C. Provider pre-tool hooks (for example Claude Code `PreToolUse`) | Reject | Provider hooks are gone from the transport (roadmap §2.6). They would be per-provider and match command strings (`cd x && just check`, `bash -c`), and they miss scripts. |
| D. `just` PATH shim that rewrites `just check` → `sase tool run check` | Reject | Shadows a real binary, must parse `just`'s own flags (`-f`, `--justfile`, `-d`), sees every nested `just` call inside recipes, and redirects silently |
| E. Self-wrapping recipe: raw agent `just check` re-execs `sase tool run check` | Reject for now | Zero friction, but it hides the contract. Once E6 auto-routing or E4 receipts land, a "plain `just check`" could hand off to a monitor (ending the agent's turn) or return a cached receipt without the agent knowing. It would also split the recipe into a public stub plus a private `_check` body that the catalog points at. Refusal with an exact remedy costs one failed call of a few milliseconds and teaches the agent. |

### 5.2 How monitors relate to ToolRuns

| Option | Verdict | Why |
| --- | --- | --- |
| M1. Wrap every monitor ad-hoc | Reject | Epic-launch leak, double records, host-completion break, kill-race exposure (§4.5) |
| M2. Only rewrite exact catalog commands (`just check` → `sase tool run check`), leave the rest raw | Too narrow alone | Misses compound monitor commands (`just install && just fix && just check …` is common) |
| M3. Guard refuses raw recipes inside monitors | Reject | Refusal after the turn ended wastes a monitor plus a follow-up agent, and breaks `-f` monitors (§4.4) |
| M4. Default-on wrap with exclusions + named upgrade | **Recommend** | Covers compound commands and scripts, keeps named identity where it's exact, and leaves host completion and epic launches alone |
| M5. Wrap only `-p verify` monitors | Acceptable fallback | 172/176 verification monitors use it, so it's a strong signal. But it's opt-in and misses unprofiled script monitors. Use it if you want a narrower first cut. |

M2's exact-argv recognition doesn't conflict with the "recognition-by-profile" rejection
in `decisions:record-before-admit`. That rejection was about *inferring cost* from argv
patterns, which leaves no stable identity. Exact equality with a catalog entry *produces*
the stable named identity. It's the same identity the agent would get by typing
`sase tool run check`.

---

## 6. Adjusted requirements (my changes, flagged)

- **ADJ-1 (reshape step 1).** Replace `sase tool ensure-not-agent` with a recipe guard
  whose rule is "agent ⇒ running inside `sase tool run <this tool>`, or bypassed",
  implemented env-only in POSIX sh (`tools/require_tool_run`). *Why:* §4.1–4.3.
- **ADJ-2 (narrow scope).** v1 guards only `check` and `check-full` in the sase repo.
  `test` and `test-visual` come later, if data shows they're worth it. Guarding `just test`
  mostly pushes agents to call pytest directly. `install` is never guarded: it's cheap and
  ubiquitous, and has no value to record until E4 receipts exist. Linked repos come later,
  after they have catalogs. *Why:* §3.1, §4.8.
- **ADJ-3 (one override concept).** The override is a single *reasoned* env var,
  `SASE_TOOL_BYPASS='<why>'`, honored by both the recipe guard and monitor wrapping. It's
  echoed to stderr (so it lands in transcripts and monitor logs) and counted by the
  adoption report. The guard also fails open by itself when `sase` isn't on PATH, and
  monitor wrapping fails open by itself when the tool bindings are unavailable. *Why:* the
  user asked for an override. A reason makes it auditable without a new store.
- **ADJ-4 (reshape step 2).** Monitors wrap by default, **except** (a) host-owned
  execution-argv launches and (b) commands that already are a single `sase tool run …`.
  A command that exactly equals a catalog tool invocation at the project root runs the
  **named** tool, not an ad-hoc wrap. *Why:* §4.5, §5.2.
- **ADJ-5 (prerequisites in scope).** Fixing `sase-16c` (env boundary), adding the
  always-exported `SASE_TOOL_NAME` marker, and fixing `sase-16b` (owner-mode process
  groups plus a pgid recorded at spawn) are part of this work and land **before**
  default-on wrapping. *Why:* default-on wrapping and env-keyed enforcement both make
  these bugs more likely and more damaging.
- **ADJ-6 (carry attribution).** Monitor-wrapped ToolRuns record the starter agent.
  *Why:* §4.6.
- **ADJ-7 (governance).** Write a decision record that partly supersedes
  `record-before-admit`'s "bypass is measured, not enforced" clause. *Why:* §4.7.
- **ADJ-8 (sequencing).** Ship as a small epic before E2, with E2 then building `-H` on
  monitor wrapping. *Why:* §4.9.

---

## 7. Recommended solution

### 7.1 The recipe guard

**Env contract.** It's small, stable, and documented in `docs/tool.md` so other repos
can implement the same check:

| Variable | Set by | Meaning |
| --- | --- | --- |
| `SASE_AGENT` | agent runner (already) | This process tree is a SASE agent's own shell |
| `SASE_TOOL_NAME` | **new:** `sase tool run` exports it to every child, whether or not recording succeeded | The tree is inside `sase tool run <name>` (or `ad-hoc`) |
| `SASE_TOOL_BYPASS` | **new:** an agent or human, per command | Run raw on purpose; the value is the reason |

**Script** (`tools/require_tool_run`, prototyped and working, §9):

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

**Wiring.** The guard goes before `_setup` so a refusal costs milliseconds, not a
dependency sync. just runs dependencies in order; I verified this with 1.58.

```just
# Agents must run guarded tools through `sase tool run` (docs/tool.md).
_require-tool-run name:
    @tools/require_tool_run {{ name }}

check: (_require-tool-run "check") _setup
    ...
check-full: (_require-tool-run "check-full") _setup
    ...
```

**Design choices worth keeping:**

- **Strict name match** (`SASE_TOOL_NAME == tool`), not "any ToolRun". An agent typing
  `sase tool run -- sh -c 'just install && just check'` is refused and nudged toward
  `just install && sase tool run check`, which keeps named identity (TYPICAL, and later
  receipts). Inside monitors the guard never fires, so monitor ad-hoc wraps aren't
  affected. Nested recipes inside `check` (`just test-scoped`, `just fmt-py-check`) aren't
  guarded.
- **Exit 2 with a three-line message** that names the exact wrapped command and the exact
  bypass. No wall of text: the agent sees it inline.
- **The guard is not a security boundary.** Anything with a shell can
  `env -u SASE_AGENT`. It's a guardrail against habit. The bypass is deliberately
  *easier* than circumventing it, and it's visible.
- **Measurement without a new store.** Extend `tools/tool_adoption_report` to classify
  `SASE_TOOL_BYPASS=… just check` as `bypassed`, and to report guard refusals by pairing
  an exit-2 raw call with a following wrapped call. The guard's stderr line puts the
  reason in the transcript either way.
- **Agent-boundary hygiene.** Add `SASE_TOOL_NAME`, `SASE_TOOL_BYPASS`, `SASE_TOOL_RUN_*`,
  `SASE_MONITOR_ID`, `SASE_MONITOR_ARTIFACTS_DIR` and `SASE_PROC_*` to the set scrubbed
  when an **agent** is launched (`sase-16c`). An agent is a new ownership and enforcement
  root.
- **Tests:** human, CI, finalizer, agent-raw (refused), agent-wrapped (passes),
  agent-wrapped-other-tool (refused), recording-failure-wrapped (passes: this is the
  §4.3 regression), bypass, no-sase-on-PATH, and a Justfile regression asserting the guard
  is the first dependency of each guarded recipe. `tools/` layout rules
  (`_lint-pyscripts`) apply to the new script.

**Optional follow-on:** a catalog field such as `agents: guarded` on `check` and
`check-full`, rendered by `sase tool list`, plus a `just validate` check that every
guarded catalog tool's recipe starts with the guard dependency. That makes the catalog
the single source of truth without making the gate depend on `sase`. It isn't needed for
v1.

### 7.2 Monitor wrapping

**Where.** In `sase monitor start`, where the proc argv is compiled
(`compile_monitor_argv` / `monitor_proc_argv`). Pass the wrapped argv as the proc
`argv`. Leave `monitor_command` exactly as the agent wrote it and **don't** set
`monitor_execution_argv`. Prepared-completion binding and settlement observation then see
the unchanged semantic command. The proc wire already carries `argv` and `command`
separately, so this needs no new wire field. That matches the roadmap's "link on the tool
side only" rule.

**What gets wrapped.**

| Monitor command | Execution argv |
| --- | --- |
| Host-owned `execution_argv` launch (epic `sase bead work`) | unchanged, **not wrapped** |
| Exactly one `sase tool run …` (any path to `sase`) | unchanged, **not wrapped** (already one ToolRun) |
| A single simple command equal to a catalog tool's argv (+ allowed extra args), with cwd = project root, for example `just check` | `<sase> tool run check` (**named**) |
| Anything else: compound commands, scripts, `gh run watch`, sleeps, `just install && sase tool run check` | `<sase> tool run -- /bin/sh -c CMD` (ad-hoc; an inner `sase tool run check` becomes its child) |
| `SASE_TOOL_BYPASS` set in the starter's env, or tool bindings unavailable | unchanged, not wrapped. One `sase: running unwrapped (<reason>)` line goes into the monitor log |

`<sase>` must be **the same installation as the supervisor** (`sys.executable -m sase`;
`src/sase/__main__.py` exists), not whatever `sase` is first on PATH. Workspace `.venv`
installs and the global install can differ.

Sleeps are wrapped too, for simplicity. A `sleep 300` ToolRun is cheap noise
(owner-mode runs retain no stdout/stderr logs, only events and samples). If it bothers
you in `sase tool runs`, add a display filter rather than another exclusion rule.

**Owner-mode behavior.** This builds on the E1 ownership code and needs these changes:

- **Process group (`sase-16b`).** When a live monitor or proc owns the run, spawn the
  child *in the wrapper's own process group* and skip the wrapper's own SIGKILL
  escalation. The owner's `killpg` then reaches the whole tree, and the owner stays the
  single process owner (roadmap invariant). For inline runs, record `child_pid`,
  `child_pgid` and the process identity **right after spawn**, so `tool_run_reconcile` can
  reap a `lost` run's surviving group when the identity still matches.
- **Attribution.** The monitor passes its starter agent in a tool-specific variable
  (for example `SASE_TOOL_RUN_AGENT`), which `begin_tool_run` uses when `SASE_AGENT_NAME`
  is absent. This doesn't restore `SASE_AGENT*`: the monitored command must still not act
  as the agent.
- **Output.** It's already correct. Under an owner, the wrapper passes bytes through
  (idle-timeout still sees them), writes no duplicate logs, and adds a single
  `sase tool run <id>` stderr line to the monitor log. The follow-up agent can then run
  `sase tool show <id>`. Test that `--next-output auto` evidence extraction tolerates that
  line.

**Guidance changes** (through `/sase_memory_write` and the `sase_monitor` skill source):

- `-- sase tool run check` stops being something agents must type in monitors. Plain
  `-- just check` becomes equivalent.
- The "Prepared-completion `-f` monitors still use raw `just check`" caveat goes away,
  because those monitors are now recorded too.
- The stale-install fallback becomes "`SASE_TOOL_BYPASS='<why>'` + raw command + record
  `sase update`".

### 7.3 Delivery: "E1.5 — enforced adoption" (about 4 medium phases, no beta flag)

1. **`ownership-roots`:** fix `sase-16c`. Scrub executor-ownership variables at agent
   launch and ignore a monitor/proc id when `SASE_AGENT` is set. Add the always-exported
   `SASE_TOOL_NAME` marker, and add the child pgid/identity at spawn (the reconcile half
   of `sase-16b`). *Verifiable:* a phase agent's `sase tool run check` is compact again,
   and `show -l` replays its output.
2. **`recipe-guard`:** `tools/require_tool_run`, Justfile wiring for `check` and
   `check-full`, the new decision record, `lint_and_test.md`, `docs/tool.md`, and the
   adoption-report `bypassed` class. *Verifiable:* inside an agent, `just check` exits
   with the three-line message, and `sase tool run check` and
   `SASE_TOOL_BYPASS=why just check` both run.
3. **`owner-process-group`:** owner-mode child in the wrapper's group, no wrapper
   escalation under an owner. Add the §9 race as a regression test. *Verifiable:* a
   timed-out monitor running a TERM-ignoring child leaves nothing behind.
4. **`monitor-wrap`:** default-on wrapping with the table in §7.2, named upgrade,
   attribution, fallback, bypass, and the `sase_monitor` skill update. *Verifiable:*
   `sase monitor start -p verify -- just check` produces exactly one named `check`
   ToolRun with `owner_kind=monitor` and the starter agent attributed; a `-f` monitor's
   host completion still succeeds; an epic launch creates no ToolRun.

No beta flag is needed: phases 1 and 3 aren't visible to users, and phases 2 and 4 each
ship complete in one phase (`sase_flags.md`: flag only when a landed phase would expose
an unfinished feature). `SASE_TOOL_BYPASS` is the permanent per-invocation escape hatch.
It's an interface, not a flag.

**Acceptance must not depend on green master** (roadmap D7). `just check` is red on
symvision at present (`sase-13s`), so every exit criterion above is stated as behavior,
not "check passes".

### 7.4 Explicitly out of scope

- Guards for linked repos (they need catalogs first; see open question 3).
- Wrapping `sase proc run` (E2's standalone leg owns that).
- Making `just check` redirect instead of refuse (option E; revisit after E6 shows whether
  auto-routing makes a silent redirect dangerous).
- Any fail-closed admission (E7).

---

## 8. Open questions for Bryan

1. **Strict vs lenient guard match.** I recommend strict (`SASE_TOOL_NAME` must equal the
   recipe's tool), so ad-hoc inline wraps of `just check` are refused and pushed toward
   named runs. Lenient ("any `sase tool run`") is friendlier but gives up identity.
2. **Wrap scope.** Default-on with exclusions (my recommendation) or `-p verify` only
   (M5, narrower, already 98% of verification monitors)?
3. **Linked repos.** Should sase-core (and sase-telegram, etc.) get their own `tools:`
   catalogs so the guard can extend there? That's where most of the remaining raw heavy
   `just check` calls are. It needs a check that a `sase/sase.yml` in a linked repo
   doesn't make it look like a SASE project root elsewhere.
4. **Bypass variable name.** `SASE_TOOL_BYPASS` (my pick) vs `SASE_TOOL_RAW`. It should
   be non-`SASE_AGENT_*` so monitors don't scrub it, and explicitly scrubbed at agent
   launch so it never leaks into child agents.

---

## 9. Verification appendix (athena, 2026-09-22)

- **Guard prototype:** a scratch Justfile with `check: (_require-tool-run "check") _setup`.
  - Human: setup and body ran, exit 0.
  - `SASE_AGENT=1`: guard refused *before* `_setup`, exit 2, with
    ``error: recipe `_require-tool-run` failed … exit code 2``.
  - `SASE_AGENT=1 SASE_TOOL_NAME=check`: ran.
  - `SASE_AGENT=1 SASE_TOOL_BYPASS=…`: printed the reason and ran.
  - 20 calls averaged **1.1 ms**.
- **CLI timing:** `sase tool --help` 0.06 s, `sase tool list` 0.25–0.29 s,
  `sase tool run -- true` 0.41–0.43 s (load average 7–14 on 64 cores).
- **Kill race (`sase-16b`):**
  - Setup: a supervisor-like parent in an isolated `SASE_HOME` ran
    `sase tool run -- sh -c "trap '' TERM; sleep 37.4242"`, sent SIGTERM to the wrapper's
    pgid, and sent SIGKILL at 5.0 s (mirroring `procs/supervisor.py`).
  - Result, 5 of 5 runs: the wrapper died with -9, `sh` and `sleep` survived, and the
    ToolRun settled `lost`.
  - Separately, SIGKILLing the caller group of a plain `sase tool run -- sleep 23` left
    `sleep` running.
  - All survivors were killed afterwards.
- **Inherited ownership (`sase-16c`):**
  - `sase tool runs -a -j`: 4 `check` runs by agent `sase-135.7` have
    `owner_kind=monitor`, `owner_id=136v0dbr3pv1`.
  - `sase monitor list -a -j`: that monitor is `0nm--mon`, running
    `sase bead work …/tool_e1_named_tools.md`.
  - Those runs' `logs` hold only `events_path`.
- **Env scrubbing:** `procs/supervisor.py::_child_environment` calls
  `scrub_agent_identity_env` and sets `SASE_PROC_ID`; `monitor/start.py` overlays
  `SASE_MONITOR_ID`; `finalizers/executor_support.py::sanitized_env` allowlists env for
  finalizer subprocesses.
- **Epic launches:** of 290 `sase bead work` monitors, 190 have `monitor_execution_argv`
  and 100 ran as plain shell. Since 09-15 it's 64 vs 1.
- **Adoption numbers:** from `python3 tools/tool_adoption_report -d 7` and `-d 2 -j`. The
  compound-command split came from the report's own `classify()` over the same
  `tool_calls.jsonl` files.
- **Side effect disclosure:** the CLI timing step ran `sase tool run -- true` three
  times against athena's real ledger, adding three ad-hoc `succeeded` rows. The race
  experiments used isolated `SASE_HOME`s.
- **Beads filed:** `sase-16b` (orphaned child tree / lost run with no pgid) and
  `sase-16c` (inherited live monitor ownership), both `task(bug)`, size medium. I searched
  for duplicates first and swept the last week's task beads; no in-progress epic has a
  causal link. `sase-16b` was created locally as `sase-16a`, but its push lost a race
  with another agent's `sase-16a` (an unrelated stale-PNG-golden `ci` task), and the
  sync moved it to `sase-16b`.
