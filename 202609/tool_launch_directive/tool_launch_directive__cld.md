# `%proc` → `%tool`: make xprompt process units first-class ToolRuns

**Researcher cld** · 2026-09-25 · host apollo · sase master `982209db99` · sase-core pin
`c31b8cf4ba` (linked checkout at `96e42d9`)

**Question.** Bryan wants to rename the `%proc` directive to `%tool` and add features so
it better supports `sase tool`. Is that a good idea? Would I do it differently? What
exactly should be built?

**Inputs.** The roadmap (`research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md`),
the E3/E4 landing-criteria consolidation, the E1 and E3 plans, `docs/xprompt.md` (typed
launch units), `docs/tool.md`, `docs/monitors.md` (tool-run wrapping), code on both sides
of the Rust boundary, the bead store, and local usage evidence on apollo. Appendix A
lists what I checked and how. Appendix B is a disclosure about my method.

---

## 1. Answer up front

**Yes, rename it, but only if the behavior changes too. A rename with no behavior change
would be worse than leaving `%proc` alone.**

- **A rename with no behavior change makes the name wrong.** Since E1, "tool" in SASE
  means one thing: a recorded **ToolRun**. The `sase tool` CLI, the `tools:` catalog,
  the `SASE_TOOL_*` environment contract, and the glossary's *Tool Run* strand all use
  it that way. A `%tool("just check")` that creates no ToolRun would contradict all of
  them.
- **Changing the behavior is worth doing, and now is the cheapest time.** Three facts
  make the case:
  1. **Today an xprompt `just check` leaves no trace.** `%proc("just check")` creates
     no ToolRun. The guarded-recipe check lets it through silently, because a proc
     never has `SASE_AGENT` set. Nobody is notified when it finishes. That breaks the
     rule that every heavy run is recorded as a ToolRun automatically. The
     `guarded-recipes` decision adopted that rule, and E4, E6, and E7 all depend on it.
  2. **E2 already built the execution path `%tool` needs.** It reserves a ToolRun for a
     proc, lets `sase tool _adopt` claim it, settles it from the proc's outcome, and
     sends exactly one notification. That is exactly what a `%tool` unit needs, so
     almost all of the execution work is reuse.
  3. **Nobody uses `%proc` yet, so the rename breaks nothing.** I found zero real
     `%proc` invocations anywhere I could look (§2.4). The directive is behind the beta
     `typed_launch_units` flag, which is due for a keep, extend, or remove decision on
     2026-11-20. Rename it before that flag's On branch becomes permanent.
- **Caveat: `%proc` has not been used at all in the 33 days since it landed.** Renaming
  it will not change that on its own. `%tool` earns its place only through three
  pipelines that nothing else in SASE can express (§3.3). Ship a thin slice that makes
  those work, then measure before adding anything else.

**Recommendation in one paragraph.**
- **Replace `%proc` with `%tool` in one step.** `%proc` becomes a migration error. There
  is no alias and no sunset flag, and the work stays under `typed_launch_units`.
- **Use a name-first grammar.** `%tool:check` and `%tool(test, tests/tool)` run catalog
  tools. Code bodies need an explicit `bash=`, `python=`, or `%tool::` fence, and they
  become ad-hoc ToolRuns.
- **Make every unit a ToolRun, owned by its proc, through the E2 hand-off contract.**
  Reserve the run in the supervisor's prepare step, after the workspace lease. If the
  reservation fails, fall back to running the command wrapped, the same way monitors
  do.
- **Fix the wait bug in the same epic.** `sase-11k` makes a same-plan `%wait` resolve
  when the proc is submitted, not when it finishes. Fix it, and expose the waited
  ToolRun to `%if::`. The context wire already has an unused `outputs` map for this.
- **Defer everything else until usage justifies it.** That covers capacity, receipts,
  remote dispatch, `%wait(tool=)`, and declarative failure predicates.
- **Size and timing:** one epic of five phases, after E3 lands.

---

## 2. What exists today

### 2.1 `%proc`: typed launch units (epic `sase-s6`, landed 2026-08-23)

**Authoring.** `%proc("cmd")` takes a Bash body positionally. `%proc(bash=…|python=…)`
names the language, and `%proc(opts)::` takes a fenced body. The options are
`timeout=`, `idle_timeout=`, `cwd=`, `workspace=`, and `label=`. A segment holding
`%proc` is a *proc unit*. It cannot contain prompt prose. It composes with `%id`,
`%wait`, `%if::`, `%q`, and `%hold`, and it rejects `%dispatch`. All of this is gated by
the `typed_launch_units` beta flag.

**Wire.** The payload is `ProcUnitWire { code, shell_name, label, timeout, idle_timeout,
cwd, workspace, workspace_explicit, selected_project, queue_*, hold }`, and the unit
variant is `LaunchUnitPayloadWire::Proc` (`sase-core/crates/sase_core/src/agent_launch/wires.rs:458`).
`code` is required.

**Dispatch** (`src/sase/agent/launch_proc_runtime.py`):
- `dispatch_proc_unit` submits a proc with origin `xprompt-proc` and lifecycle
  `proc-shell`. Its argv is `/bin/bash --noprofile --norc <script>` or the SASE Python
  plus the script.
- The supervisor's `prepare_xprompt_proc_supervisor` then:
  - acquires an operational lease when `workspace` is set, preparing the checkout from
    the primary remote (`workspace_provider/lease.py`);
  - materializes the private `0600` script through Rust `prepare_proc_script`;
  - refuses to run if the prepared argv differs from the reserved one;
  - sets a sanitized environment with `SASE_PROC_ID` and never `SASE_AGENT`.

**No completion notification.** Settlement only cleans up the private inputs
(`procs/settlement.py:99`). The proc carries no `followup`, so a finished `%proc` unit
is visible only as an Agents-tab `▣` row.

**Two parsers.** Rust `agent_launch/typed_units.rs` and Python
`src/sase/xprompt/_directive_collect.py` (13 `%proc` references) both parse the
directive. Parity tests keep them in step.

### 2.2 `sase tool` today

**Epic status:**

| Epic | Bead | Status |
| --- | --- | --- |
| E1 | `sase-135` | Closed |
| E1.5 (guarded recipes, monitor wrapping) | `sase-16h` | Closed |
| E2 (hand-off, stop/follow/wait, `terminal_cause`, one notification) | `sase-17p` | Closed |
| E3 (failure triage) | `sase-18j` | In progress: 5 of 9 phases closed; `.6`–`.9` open |
| E4 | — | Re-scoped or deferred by the 2026-09-24 consolidation |
| E5–E8 | — | Not planned |

**How hand-off works** (`src/sase/tool/handoff.py`, `adopt.py`):
1. `reserve_handoff_run` creates a `created` run with a frozen launch envelope (argv,
   cwd, definition, digest).
2. The owning proc runs `python -m sase tool _adopt <run>`. The worker claims the run,
   executes it, and calls `_deliver_settlement`.
3. Timeouts and stops are read from the owner's recorded termination intent
   (`_timeout_probe`, `_stop_probe`).
4. If something crashes, owner-fact reconciliation settles the run. It only applies to
   `launch_mode: handoff` runs (`tool/owner.py`).

**The monitor rule** (`docs/monitors.md` §"Tool-run wrapping"):
- Reserve the run up front.
- If the reservation fails, fall back to the wrapped argv and write one reason line.
  This is fail-open.
- A simple command equal to a catalog argv, run from the catalog's project root, is
  upgraded to a named tool run.

### 2.3 The gap: what "run `just check` from an xprompt" does today

| Prompt | ToolRun? | Guarded recipe | A timeout is recorded as | Completion notification | E3 triage |
| --- | --- | --- | --- | --- | --- |
| `%proc("just check")` | **none** | allowed silently (no `SASE_AGENT` in the proc) | n/a | **none** | **none** |
| `%proc(bash="sh -c '…just check…'")` | **none** | allowed silently | n/a | none | none |
| `%proc("sase tool run check")` | yes: foreground, owner = the proc (code reading) | satisfied | `signal`, not `timeout`: the foreground path has no timeout probe (`executor.py:225`) | none: foreground runs are not eligible for hand-off delivery | yes (named) |
| **proposed** `%tool:check` | yes: hand-off, owner = the proc | satisfied | `timeout` (`adopt.py` `_timeout_probe`) | once, through the existing E2 path | yes |

The third row shows an author can get a ToolRun today by typing the wrapper by hand. But
that run is a second-class citizen. Nobody writes it that way, which is the same
adoption gap that the guarded-recipes decision measured for agents.

### 2.4 Usage, footprint, and flag state

**Usage: zero.**
- Chat transcripts: `~/.sase/chats` holds about 1,600 transcripts from 2026-07 to
  2026-09. It contains zero `%proc(` or `%proc::` invocations. The only other hits are
  prose mentions and this swarm's own prompt.
- Prompt history: September's 331 KB `prompt_history/2609.json` has no hits.
- Authored xprompts: there are no hits in `~/sase`, `~/.config/sase`, or packaged
  `src/sase/xprompts/`.
- Proc store: none of the 143 retained procs has origin `xprompt-proc`. This is weak
  evidence, because the store keeps only a bounded history.
- `~/.sase/typed_launches/` does not exist on apollo, so no direct typed launch has
  ever run here.
- The flag *is* enabled on apollo (`~/.sase/feature_flags.json`), so this is not an
  opt-in effect: the feature is available and still unused.

**Footprint:**

| Repo | `%proc` references | `xprompt-proc` / `xprompt_proc` references | Other |
| --- | --- | --- | --- |
| sase | 146 in 37 files (a third are docs and tests) | 107 in 26 files | — |
| sase-core | 102 in 14 files (most in `editor/wire.rs`, `agent_launch/typed_units.rs`, `fenced_code.rs`, and tests) | 22 | 18 `ProcUnit` references |

I could not check sase-nvim, which is not checked out on apollo.

**Flag.**
- `typed_launch_units` is beta and default off. Its removal bead is `sase-s7`, due
  2026-11-20 or at v0.18.0.
- Its remove-when gate reads: *"Mixed Agent/Proc launches, skipped admission, recovery,
  and both editor surfaces have operational evidence."* With zero usage, that gate
  cannot be met today.

**Related open beads:**
- `sase-11k`: a same-plan proc wait resolves when the proc is submitted, not when it
  finishes.
- `sase-16s`: `dispatch_proc_unit` checks terminal state against a stale proc row.
- `sase-wk`: `,X` cannot abort un-admitted units.
- `sase-166`: typed-admission error presentation.
- `sase-sa`: the glossary's "Proc Shell" strand is stale about stand-alone procs.
- `sase-189`: the tool-run notification has no real action.
- `sase-17e` and `sase-17g`: ToolRun routing and escalation.

---

## 3. Critique

### 3.1 Is the rename a good idea?

It is a good idea under three conditions:

1. **`%tool` must mean "creates a ToolRun", by construction, for every unit.** Otherwise
   don't rename it.
2. **Reuse E2's executor contract rather than inventing a "tool unit" executor.** The
   roadmap's cross-epic invariants say one run has one ToolRun id and one process owner.
   The `record-before-admit` decision says recording adds no new supervisor. `%tool`
   should be the third client of the hand-off contract, after `-H` and monitors.
3. **Do it inside the beta window.** While the flag is beta, a grammar break, a wire
   schema change, and a hard cutover cost almost nothing. After `sase-s7` retires the
   flag, each needs a sunset flag and a migration.

### 3.2 The name itself

**For `%tool`.**
- It matches `sase tool`, `tools:`, `SASE_TOOL_*`, and ToolRun.
- There is precedent for naming a directive after its role rather than its executor. A
  *monitor* is also a proc shell underneath, yet nobody calls it `sase proc --watch`.

**Against `%tool`.**
- An xprompt is an LLM prompt, and in LLM vocabulary "tool" means function calling. A
  reader may take `%tool:check` to mean "give the agent a `check` tool".
- That risk is concrete: there is already a proposal about agent toolsets (`sase-17i`,
  a Muse `run.toolset` allowlist).
- The LLM Calls rename fixed this collision in the TUI, not in prompts.
- **Mitigations:**
  - Pick a different name for any future provider-permission directive now, such as
    `%toolset` or `%allow`.
  - Make the directive description say "Run a project tool as a stand-alone, recorded
    unit (ToolRun)".

**Alternatives, and why each loses:**

| Name | Problem |
| --- | --- |
| `%run` | Collides with `sase run`, which launches agents. This is the worst option. |
| `%exec`, `%sh` | They name the mechanism, not the record. |
| `%cmd` | The roadmap already rejected `cmd`. |
| `%check` | Too narrow for `test`, `install`, or ad-hoc bodies. |

Keep `%tool`.

**The executor is still a proc, and that is fine.** The Agents-tab row stays a `▣` proc
shell, `sase proc kill` still works, and `%wait(proc=…)` stays valid. The docs need one
sentence: "a tool unit runs as a proc shell and records a ToolRun". This is the same
relationship monitors already have.

### 3.3 Will `%tool` actually get used?

`%proc` has had 33 days and no users. My reading of why:
- Running an ad-hoc command in the background already has three better-known entry
  points: the TUI `!` command, `sase proc run`, and `sase tool run -H`.
- Agents cannot use typed launches without a LaunchApproval gate.
- So `%proc` competes on "run a command in the background" and loses.

`%tool` has to win on *composition* instead: on things only a launch unit inside a
multi-segment plan can do. I see three:

1. **Post-land verification.**
   ```text
   +sase %id:impl #pr:thing …task…
   ---
   +sase %wait:impl
   %tool:check
   ```
   `check` runs in a fresh leased checkout, so it verifies what actually landed, not
   the agent's workspace. The result is recorded, triaged by E3 once E3 lands, and
   notified.
2. **Scheduled clean-checkout witness runs.** AXE job proposals already accept typed
   directives (`docs/axe.md`, typed directives in job proposals). A routine that proposes `%tool:check` on a
   freshly prepared checkout produces clean-tree runs. Those are exactly what E3's
   KNOWN rule is short of: the E3/E4 consolidation found that all 15 clean-tree runs
   failed and that runs rarely sit at the merge base.
   - These are named runs, not ad-hoc ones, so in principle they are eligible as
     witnesses. E3 never treats ad-hoc runs as witnesses.
   - Whether they satisfy the final distinct-workspace and ancestry rule has to be
     checked against `sase-18j`'s landed rule.
3. **Gate an agent on a tool result.** Run `%tool:check`, then launch a fixer agent
   only if it failed:
   ````text
   +sase %id:chk
   %tool:check
   ---
   +sase %wait:chk
   %if::
   ```python
   import json, os, sys
   ctx = json.load(open(os.environ["SASE_CONDITION_CONTEXT"]))
   run = ctx["waited_outcomes"][0]["outputs"]["tool_run"]
   sys.exit(0 if run["exit_code"] != 0 else 1)
   ```
   Fix what `sase tool show {run id}` reports …
   ````
   Today this is broken twice: the wait resolves at submission (`sase-11k`), and the
   context carries no ToolRun.

Anything beyond these three should wait for evidence. This follows the spirit of the
`corpus-before-mechanism` decision: `%proc` is the counterexample, a full feature built
with no measured demand.

### 3.4 What the rename does *not* do

Do not sell `%tool` as any of these:
- **Not an agent verification path.** Agent-initiated typed launches still need
  LaunchApproval. Agents keep using inline `sase tool run` or `sase monitor start`.
  Agent guidance must not offer `%tool` as an alternative to monitors, because that
  would reintroduce the "which one do I use" problem the roadmap warned about. `sase
  tool` is already the fourth way to run a command; `%tool` must not become a fifth
  supervisor.
- **Not capacity admission.** `%q` on a tool unit stays a check, not a claim. E7 owns
  claims.
- **Not receipts or skip-if-passed.** E4's reuse leg measured zero opportunity: no
  passing fingerprint was ever re-run.
- **Not remote.** A tool unit combined with `%dispatch` stays rejected; E8 ruled out
  remote dispatch.

### 3.5 Risks and sharp edges the plan must handle

1. **When the catalog is resolved.** The unit runs in a leased checkout prepared from
   the remote. The catalog must be resolved *there*, at execution time, not from the
   source checkout at admission. Admission may check the name early for a better
   error, but the leased checkout is authoritative.
2. **When the run is reserved, versus E2's frozen envelope.** The cwd is unknown until
   the lease is acquired, so reserve in the supervisor's prepare step.
   - Pre-allocate the run id when the proc is submitted. That fixes the proc argv
     (`_adopt <id>`) at submission, and the prepare step already refuses argv drift.
   - Reservation must be idempotent by run id, so coordinator or supervisor replay
     never reserves twice.
3. **Identity of ad-hoc bodies.** `_adhoc_definition(argv)` keys on argv
   (`tool/argv.py`). The materialized script path is unique per proc, so each ad-hoc
   unit would become its own definition, with no LAST or TYPICAL. Key ad-hoc tool units
   on language plus code digest instead: a display or identity argv like
   `bash sha256:<digest>`, with the real path kept only in the private argv.
4. **Same-plan wait semantics (`sase-11k`).** All three pipelines in §3.3 break without
   this fix. For tool units, a wait must resolve at terminal settlement only. Choosing
   between the bead's two remediation options is unnecessary here.
5. **The default `workspace=true`.** `%tool:check` in a project context verifies a
   fresh leased checkout, not your working tree.
   - That is right for pipelines 1 and 2, and it is what E3 evidence wants.
   - It surprises anyone who wants to check their current dirty tree. For that, use
     `workspace="false"` plus a cwd, or plain `sase tool run check`.
   - Show which checkout will be used in the approval preview and on the row.
6. **Two parsers.** The rename touches both. The name-first grammar is *new* logic, so
   under `rust_core_backend_boundary` it belongs in Rust only. Recommendation: make the
   Python `_directive_collect.py` path delegate to Rust for `%tool` rather than growing
   a second implementation.
7. **Changing a beta wire.** `ProcUnitWire.code` is required today, and a named unit
   has no code. Either make `code` optional and add `tool: Option<ToolTargetWire>`,
   validated as exactly one of the two, with a schema bump; or add a new payload
   variant. A bump is cheap now: there are no persisted typed plans on apollo, and the
   feature is beta.
8. **Collisions with E3.** E3's open phases change `src/sase/tool/` and move the
   sase-core pin. `%tool` mostly touches core's `agent_launch` and `editor` modules,
   plus sase's `launch_proc_runtime` and `tool/handoff`. Rules:
   - Serialize the pin moves.
   - Make no ToolRun *store* wire change. E2's decision 6 (additive only) still binds.
9. **The flag's remove-when gate.** `sase-s7` needs operational evidence that zero
   usage cannot provide. Either `%tool` produces that evidence, or the due date forces
   a decision about an unused feature (§7 Q5).

---

## 4. Options considered

| Option | What it is | Verdict |
| --- | --- | --- |
| **A. Rename only** | `%tool` = today's `%proc`, same behavior | **Reject.** The name would be wrong (§1); it adds churn and gains nothing. |
| **B. Keep `%proc`, auto-wrap bodies** | Apply the monitor `tool_wrap` policy to proc bodies; add `%proc(tool=check)` | **Viable fallback, not the primary choice.** Least churn, and the name matches the executor. But you get two names for one concept: `sase tool run check` on the CLI and `%proc(tool=check)` in prompts, which reads backwards. |
| **C. Add `%tool` beside `%proc`** | `%tool` for catalog tools; `%proc` stays for raw, unrecorded scripts | **Reject.** Two directives would overlap. An unrecorded escape hatch contradicts `record-before-admit` and `guarded-recipes`. And zero `%proc` users means there is nothing to protect. |
| **D. Replace `%proc` with `%tool`; ToolRun for every unit via E2** | §5 | **Recommend.** |
| **D′. D, but wrap in the foreground** | Materialize `exec sase tool run …` as the proc script, with no hand-off reservation | **Reject as the default; keep it as the fallback.** Timeouts and stops would be recorded wrongly, crashes would not be reconciled from the owner, no notification would be sent, and the run id would be unknown until the command starts. Use it only when reservation fails. |

---

## 5. Recommended design

### 5.1 Grammar (name-first)

```text
%tool:check                                  # named catalog tool
%tool(check)                                 # same
%tool(test, tests/tool, -x)                  # extra argv, only where the entry has args: allow
%tool(check, timeout=45m, label="Nightly")   # %proc's options carry over unchanged
%tool(bash="just docs-check", cwd=docs)      # ad-hoc ToolRun from a Bash body
%tool(python="print('ready')")               # ad-hoc ToolRun from a Python body
%tool(timeout=20m)::                         # fenced ad-hoc body (one closed bash/python fence)
```

**Rules.**
- **The first positional or colon value is a catalog tool name.** A positional that
  contains whitespace or shell metacharacters is an error with a fix:
  `%tool expects a tool name; for a shell command use %tool(bash="just check")`. That
  message catches every old `%proc("…")` form.
- **Later positionals are extra argv tokens.** They are passed verbatim with no shell
  parsing. The catalog's `args:` policy accepts or refuses them at execution; the
  parser does not.
- **`bash=`, `python=`, and a `::` fence make an ad-hoc run.** They cannot be combined
  with a name.
- **Keywords are unchanged:** `timeout=`, `idle_timeout=`, `cwd=`, `workspace=`, and
  `label=`. Slice 1 adds no new keywords.
- **Composition rules carry over from `%proc`:**
  - one `%tool` per unit, and no prose in a tool unit;
  - `%id:<name>` sets the shell name;
  - `%q`, `%hold`, `%wait`, and `%if::` compose as they do with `%proc`;
  - `%dispatch` is rejected.
- **Any `%proc` form is a migration error:** `%proc was renamed to %tool;
  %proc("cmd") is now %tool(bash="cmd")`.
- **Completion needs a new value role.** Add a `DirectiveValueRole` for catalog names,
  read from the current project's `tools:`. It is new: the CLI `TOOL_RUN` completion
  kind covers run ids, not catalog names.

### 5.2 Execution: the monitor model applied to tool units

1. **At admission dispatch** (`dispatch_proc_unit`), pre-allocate `run_id` and submit
   the proc with:
   - `argv = worker_argv(run_id)`;
   - `tags = owner_tags(run_id)`;
   - `followup = {"kind": "tool-run", "run_id": run_id}`;
   - origin `xprompt-proc`, with the tool target (or the code) and its options in the
     `xprompt_proc` metadata.

   Record `tool_run_id` in the admission journal and receipt.
2. **In the supervisor's prepare step** (`prepare_xprompt_proc_supervisor`):
   1. Take the lease, if `workspace` is set.
   2. Resolve the invocation:
      - **named:** `resolve_run_argv([name, *extra], cwd=<lease root or cwd>)`, which
        reads the catalog from the leased checkout;
      - **ad-hoc:** materialize the script as today, then resolve an ad-hoc argv whose
        identity is the code digest (§3.5.3).
   3. Call `reserve_handoff_run(resolved, owner_kind="proc", owner_id=proc_id,
      run_id=run_id)`. This needs a new optional `run_id` parameter and must be
      idempotent.
   4. The proc then execs `_adopt`, exactly like a `-H` proc.
3. **Fail open on reservation failure.** Exec the wrapped foreground form instead and
   write one `sase: tool run not reserved (…)` line to the proc log. This matches the
   monitor rule: the proc id is already durable, so a handle always exists. Catalog
   errors are different. An unknown name or refused extra args fails the proc with a
   clear message; never fall back to running the command ad-hoc.
4. **Settlement reuses E2 unchanged.** The worker claims and settles. `_deliver_settlement`
   publishes once, and the proc-settlement follow-up covers the rest. Owner-fact
   reconciliation covers crashes. Lease release and private-input cleanup are
   unchanged.
5. **Upgrade simple bodies to named runs.** A `bash=` body that is one simple command
   equal to a catalog argv, run at that catalog's root, becomes the named run. Call the
   monitor's matcher; do not write a second one.

Guarded recipes pass for the right reason. The `_adopt` child environment carries
`SASE_TOOL_NAME` and `SASE_TOOL_PROJECT_ROOT` for the correct root, whether or not
`SASE_AGENT` is set.

Fold `sase-16s` (a stale proc row in `dispatch_proc_unit`) into this work, since that
function is being rewritten anyway.

### 5.3 Waits, conditions, and results

- **Fix `sase-11k` for tool units.** A same-plan wait on a tool unit is satisfied at
  terminal proc settlement, never at submission.
- **Populate the condition context.** Fill
  `waited_outcomes[i].outputs.tool_run = {run_id, tool, state, exit_code,
  terminal_cause}`, and add `verdict` once `sase-18j` lands.
  - `outputs` already exists on `ConditionWaitedOutcomeWire`
    (`agent_launch/condition.rs:51`) and nothing in production populates it, so this is
    additive with no schema bump.
  - Fill the same field on the external `%wait(proc=<tool unit>)` path in
    `launch_admission_runtime.py:_resolve_proc_wait`. Today that path maps success to
    `launched` and every other status to `launch_error`, and it drops the exit code.
- **Deferred, reopened only on measured use of the `%if::` form above:**
  - `%wait(tool=<run-id>)`;
  - a static failure shorthand for `%if`;
  - injecting the run id into the dependent agent's prompt.

### 5.4 Surfaces (keep them thin; the rest belongs to E5)

- **Approval and direct-launch preview:** show the resolved tool and checkout, e.g.
  `tool check → just check (sase/sase.yml, definition 12b1…) in a leased checkout`.
- **PROC SHELL detail:** add a "Tool run" row with the id, state, exit code, and verdict
  once available, plus a `sase tool show <id>` hint. Look the run up through the
  `tool-run:<id>` proc tag now, and through E3's owner selector once it lands.
- **Agents-tab label:** `tool:check`, matching `-H` procs.

### 5.5 Names that stay "proc"

- `LaunchUnitPayloadWire::Proc` and `ProcUnitWire`: keep the variant, because the unit
  *is* a proc, and add the tool target. Renaming the variant during the same schema
  bump is possible but buys little.
- Origin `xprompt-proc`, lifecycle `proc-shell`, the `▣` rows, and `%wait(proc=…)`:
  keep them all. They name the executor.
- User-facing text says **tool unit**.

### 5.6 Migration, flags, and documentation

- **Switch over in one step, under `typed_launch_units`.** No alias and no sunset flag.
  The `sase_flags` rule requires a flag for backward-compatible branches "while callers
  migrate", and there are no callers (§2.4). The migration error, modeled on `%name` and
  `%tribe`, is the only compatibility code.
- **Land it before `sase-s7`'s retirement decision** (2026-11-20 or v0.18.0), or extend
  `sase-s7` so the flag cannot retire in the middle of the rename.
- **Update these docs and memory notes:**
  - `docs/xprompt.md`, `docs/tool.md` (a new "From an xprompt" section),
    `docs/axe.md`, `docs/architecture.md`, and `docs/configuration.md`;
  - the glossary: fix the stale "Proc Shell" strand (`sase-sa`) and consider a "Tool
    Unit" strand;
  - the `xprompts.md` memory's directive table, which lists neither `%proc` nor `%if`
    today.

  Make every memory change through `/sase_memory_write`.

---

## 6. Implementation plan sketch

One epic of five phases. Plan it after `sase-18j` lands. The alternative is running it
concurrently under an explicit rule: no ToolRun store changes, and pin moves serialized.

| # | Phase | Repos | Size | User-verifiable result |
| --- | --- | --- | --- | --- |
| 1 | Grammar and contract | sase-core (+pin), sase delegates parsing | large | `%tool:check`, `%tool(test, tests/x)`, and `%tool(bash=…)` parse and complete in the TUI and LSP. `%proc` produces the migration error. |
| 2 | Execution through the E2 hand-off | sase (only a tiny core change, if any) | large | `sase run '+sase %tool:check'` creates a `▣` row plus a ToolRun owned by that proc. `sase tool show/wait/stop` work on it. Exactly one notification arrives on settle. Timeout and stop record the right `terminal_cause`. |
| 3 | Terminal waits and condition outputs | sase-core (+pin), sase | medium | The §3.3 fixer-on-failure pipeline works end to end. `sase-11k` is closed. |
| 4 | Surfaces | sase | medium | The approval preview shows the tool and checkout. PROC SHELL detail shows the Tool run row. Visual snapshots are refreshed. |
| 5 | Docs, glossary, and proof | sase + memory | small–medium | Docs and memory are updated. `smoke_sase_tool_runs` gains a live `%tool` case. The flag decision (Q5) is recorded. |

Phases 1–2 alone would be a large tale. The cross-repo pin ratchet in phases 1 and 3
argues for an epic, so each moves the pin once.

---

## 7. Open questions for Bryan

1. **Name-first grammar?** It breaks the `%proc("cmd")` positional-Bash form, which
   becomes `%tool(bash="cmd")`. I recommend yes. The error message carries the fix, and
   no one uses the old form.
2. **Keep ad-hoc code bodies in `%tool`?** I recommend yes; they are ad-hoc ToolRuns.
   Dropping them means either losing arbitrary-script units or keeping `%proc`
   alongside `%tool` (option C).
3. **Keep `workspace=true` as the default for tool units**, which verifies a fresh
   leased checkout? I recommend keeping it and showing it clearly in the preview.
4. **Reserve a different name now for any future provider tool-permission directive**,
   such as `%toolset`?
5. **What if `%tool` is not used either?** If it records no organic use within about
   three weeks of landing, should `typed_launch_units` as a whole be reconsidered
   rather than retired to permanently on?
6. **Timing:** after `sase-18j` lands (my recommendation), or concurrently under the
   no-store-change rule?

---

## Appendix A: verification (apollo, 2026-09-25)

**Code read at `982209db99`:**
- `src/sase/agent/launch_proc_runtime.py`
- `src/sase/tool/{handoff,handoff_launch,adopt,ownership,owner,executor,argv}.py`
- `src/sase/procs/settlement.py`
- `src/sase/agent/launch_admission_runtime.py:_resolve_proc_wait`
- `src/sase/xprompt/_directive_collect.py`
- `src/sase/workspace_provider/lease.py`

**sase-core read at `96e42d9`:**
- `agent_launch/{wires,typed_units,admission,condition}.rs`
- `editor/directive/metadata.rs`
- `fenced_code.rs`

**The table in §2.3.** It comes from reading that code, not from launching units. I did
not start real `%proc` units in Bryan's environment:
- Foreground runs under a proc owner get only `_foreground_stop_probe` (`executor.py:225`).
- `_timeout_probe` exists only on the `_adopt` path.
- `observe_owner_fact` returns `None` unless `launch_mode == "handoff"`.
- `deliver_handoff_settlement` skips anything that is not a proc-owned hand-off.

**Usage (§2.4).**
- The earliest grep over `~/.sase/chats` for `%proc(` and `%proc::` returned 0 files.
  That grep ran before this swarm's peers had written any transcripts.
- Two older September transcripts mention `%proc` only in prose ("`%proc` still is
  [feature-flagged]").
- `prompt_history/2609.json`, user xprompt directories, and `sase proc list -a -j`
  (143 rows: `axe` 55, `service-host` 42, `ace` 38, `monitor` 8) have no `%proc` use.

**Beads, read with an audit reason:** `sase-s6`, `sase-s7`, `sase-11k`, `sase-16s`,
`sase-wk`, `sase-17e`, `sase-17g`, `sase-17x`, and `sase-18j`. Epic status comes from
`sase bead list -r epic -s all`.

**Memory**, read through `sase memory read`: `decisions:guarded-recipes`,
`decisions:record-before-admit`, `decisions:single-turn-agents`, and the glossary
strands Proc, Proc Shell, Tool Catalog, and Tool Run, plus `sase_flags.md` and
`xprompts.md`.

**Flags:** `sase flag list` and `~/.sase/feature_flags.json`, where
`typed_launch_units: true`.

## Appendix B: method disclosure

While counting real `%proc` invocations, I ran a broad `grep -rhF '%proc'` over
`~/.sase/chats`. By then it matched transcripts this swarm's peer researchers had just
created (the `research.9.gem` and `research.9.mus` runs). The output included one
peer's one-line summary sentence, which favored adding `%tool` alongside `%proc`.

I did not open those files, and I did not use that line. Option C was already on my
list, and I reject it on this report's own evidence: the `record-before-admit` and
`guarded-recipes` decisions, and zero `%proc` usage. The lead should weigh my §4
verdict on option C knowing I saw that line.
