# `%tool` should be a named ToolRun launch unit

**Consolidated report** · 2026-09-25 · host apollo · sase master `982209db994c2c9b9c45025e0e1c0b9ac3275b49` · published core pin `c31b8cf4bad8ea8c5b058a959bb69270ee2d5b30` · linked core `96e42d944689412c45a39035764f3422acf261bb`

**Sources:** Codex (`tool_launch_directive__cdx.md`), Claude (`tool_launch_directive__cld.md`), Muse (`tool_launch_directive__mus.md`), Gemini (`tool_launch_directive__gem.md`), the `sase tool` epic roadmap (`research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md`), and independent verification of the live sase / sase-core trees and bead store.

**Question.** Rename the `%proc` xprompt directive to `%tool` and add features so it better supports `sase tool`. Is that a good idea, and what should actually be built?

---

## 1. Answer up front

**Add `%tool`. Do not mechanically rename `%proc`.**

The instinct is right: project tools belong in the launch graph, and `%tool:check` is the prompt surface `sase tool run check` has been missing. The framing is wrong. `%proc` authors a raw durable process. `sase tool` records a **ToolRun** — a named catalog identity plus fingerprints, stages, and a followable id. Those are different layers. A ToolRun may be *owned by* a proc; it is not itself a proc. Calling today's `%proc` surface `%tool` would make "tool" mean "detached script" at the exact moment the rest of the product has given the word a narrower, more valuable meaning.

Four independent researchers reached that same architectural diagnosis. They split on how hard to cut over `%proc`, whether ad-hoc code belongs in `%tool`, and whether reservation should fail open. The live tree, the ToolRun hand-off contract, and the `typed_launch_units` beta window resolve those splits as follows.

**Recommendation in one paragraph.** Ship `%tool` as a **new first-class typed launch unit for named catalog tools**, implemented over the existing proc supervisor and the existing E2 hand-off path. Keep `%proc` as the raw-code unit in this epic. Grammar is name-first (`%tool:check`, `%tool(test, tests/tool.py, "-k=smoke")`). Every `%tool` unit reserves exactly one ToolRun owned by exactly one proc, fail-closed, with hand-off implicit. Approve against a catalog snapshot and re-check the definition digest in the leased workspace before the command starts. Compose with `%wait` / `%if::` / `%queue` / `%hold` / `%id` as proc units already do, and fix same-plan waits so they resolve at terminal proc settlement (`sase-11k`). Stay behind `typed_launch_units`. Leave receipts, continuation modes, remote dispatch, ad-hoc bodies, and `%wait(tool=<run-id>)` for later evidence.

This is a focused integration epic of about five phases, sequenced after E2 (already landed) and beside E3 (in progress), not a spelling refactor and not a vehicle for E4–E7.

---

## 2. What exists today (independently verified)

### 2.1 `%proc` is a beta process unit, not a tool

Gated by `typed_launch_units` (beta, default **off**; removal bead `sase-s7`, due 2026-11-20 / v0.18.0). Gemini's claim that the flag is enabled in default config is false: beta flags default off (`FeatureFlagDefinition.default` is true only for `sunset`). Claude reports it is enabled on apollo; that is a machine overlay, not the product default.

Forms (`docs/xprompt.md`, Rust `typed_units.rs`, Python `_directive_collect.py`):

```text
%proc("just check")
%proc(python="print('ready')", timeout="20m", label="Preflight")
%proc(timeout="20m", idle_timeout="5m", cwd="docs", workspace="true")::
```

Colon and plus forms are rejected. Options are `timeout=`, `idle_timeout=`, `cwd=`, `workspace=`, `label=`. One `%proc` per unit; residual prompt prose is an error. `%id:<name>` becomes `shell_name`. `%dispatch` is rejected on a proc unit (`validate_dispatch_combinations` pushes `%proc` into the forbidden list). Muse's claim that `%dispatch` composes with `%proc` is false.

Wire: `LaunchUnitPayloadWire::{Agent, Proc}` only. `ProcUnitWire.code` is required. Queue, hold, workspace, and timeout fields already live on the proc payload.

Dispatch: `dispatch_proc_unit` submits origin `xprompt-proc`, lifecycle `proc-shell`. The supervisor leases a workspace when `workspace` is true (default **true** in project context), materializes a private `0600` script, execs by argv, never sets `SASE_AGENT`. Settlement cleans private inputs. There is no ToolRun, no completion notification, and no E3 triage.

Epic `sase-s6` still shows `IN_PROGRESS` with all eight phases closed (land outstanding). Several discovered coordinator defects remain on that bead (`sase-11k`, `sase-16s`, time-wait respawn, PID sidecar). That is a reason to add `%tool` additively rather than rewrite `%proc` in place.

### 2.2 `sase tool` already has the control plane `%tool` would call

The 2026-09-17 roadmap is partly historical. By today's tree:

| Capability | Status |
| --- | --- |
| Project-owned `tools:` catalog + `sase tool list` | landed (E1) |
| Foreground `run` / `runs` / `show` | landed (E1) |
| Durable hand-off (`-H`), `show -F` / `wait` / `stop`, owner settlement, one notification | landed (E2) |
| Failure triage | `sase-18j` in progress (phases 1–5 closed; 6–9 open) |
| Receipts, forecasts, admission, fleet | not planned as live epics |

Catalog (`sase/sase.yml` `tools:`): `check`, `check-full`, `install`, `test`, `test-visual`. Named tools run at the catalog's project root. Extra argv follow `args: deny|allow`. Ad-hoc CLI is `sase tool run -- ARGV...`.

Hand-off contract (`docs/tool.md`): reserve a `created` run that already names its owner, start the owner on `python -m sase tool _adopt <run>`, settle from owner facts. **Explicit `-H` is fail-closed** (nothing starts if reservation fails). **Monitor wrapping is fail-open** (the monitor id is already durable). Nested `-H` inside a live owner is refused.

Roadmap invariants that still bind: one semantic run = one ToolRun id; one process owner; one log owner; zero new supervisors; record-first; the link lives on the tool side (`proc_id` on the ToolRun).

### 2.3 The gap a rename would have to close

| Prompt | ToolRun? | Timeout cause | Notification | E3 |
| --- | --- | --- | --- | --- |
| `%proc("just check")` | none | n/a | none | none |
| `%proc("sase tool run check")` | foreground, owner = the proc | `signal`, not `timeout` (no timeout probe on the foreground path) | none (foreground is ineligible for hand-off delivery) | named only |
| proposed `%tool:check` | hand-off, owner = the proc | `timeout` via `_adopt` | once, E2 path | named |

Guarded recipes let a `%proc("just check")` through silently because the proc never sets `SASE_AGENT`. That is a hole in "every heavy run is a ToolRun" (`decisions:guarded-recipes`, `decisions:record-before-admit`).

### 2.4 Usage of `%proc` is zero, and that cuts both ways

Claude grepped ~1,600 chat transcripts, September prompt history, authored xprompts, and 143 retained procs: **zero** `xprompt-proc` origin rows and zero real `%proc(` / `%proc::` invocations (apollo, flag enabled). Packaged `src/sase/xprompts/` also has none. That makes a spelling break cheap, and it also means a rename by itself will not create demand. `%proc` already loses to `!`, `sase proc run`, and `sase tool run -H` as "run a command in the background." `%tool` earns a place only through composition that those entry points cannot express.

### 2.5 Same-plan waits resolve at proc *submission*

Bead `sase-11k` (ready, bug, medium) is real. I re-read `admission.rs::resolved_wait_outcome`: a same-plan `WaitTargetWire::Logical` is satisfied when `state.phase.outcome()` is `Some`, and `LaunchUnitPhaseWire::Launched` is terminal. The coordinator journals `launched` as soon as `dispatch_proc_unit` returns success — i.e. supervisor submission. External `%wait(proc=<id>)` instead polls `TERMINAL_PROC_STATUSES`. Docs say a typed dependency is satisfied when the target "settles"; for a proc unit, admission currently treats submit as settled. Every post-land "run check, then launch a fixer" pipeline is racy until this is fixed.

`ConditionWaitedOutcomeWire.outputs` already exists and is empty in production. Filling `outputs.tool_run` is additive, no schema bump.

---

## 3. Critique of the proposed rename

### 3.1 What is good about the idea

1. **It makes the recorded path the easy path.** `%tool:check` is strictly better authoring than a proc whose body happens to call `sase tool run`.
2. **It gives the catalog a launch-graph role.** Named tools can participate in `%wait`, `%if::`, `%hold`, fan-out, and AXE job proposals without pretending to be agents.
3. **It closes a structural adoption hole.** Heavy work authored as `%tool` cannot bypass the ToolRun ledger the way `%proc("just check")` can.
4. **The execution path already exists.** E2's reserve / `_adopt` / owner-fact settlement / one notification is exactly what a tool unit needs. Codex is right that `%tool` no longer needs to invent a control plane.
5. **The beta window is the cheap moment.** `typed_launch_units` is still optional; `sase-s7`'s remove-when gate ("mixed Agent/Proc launches … have operational evidence") cannot be met on zero usage. Landing `%tool` *before* that decision is the point of the flag.

### 3.2 Why a literal rename is the wrong unit of work

1. **It collapses a semantic record into an executor.** Glossary: a ToolRun is not a proc; a proc may own a ToolRun. Renaming the process directive points the abstraction the wrong way. SASE already spent E1 renaming the TUI "Tools" pane to **LLM Calls** to free this word.
2. **Arbitrary code has no stable tool identity.** `%proc::` fences and `%proc(python=...)` becoming `%tool` would mint ad-hoc ToolRuns keyed on unique private script paths. Current triage already refuses ad-hoc runs as witnesses. That is ledger noise, not catalog history.
3. **Inherited proc options lie about named tools.** `cwd=` and `workspace=` are proc-preparation knobs. Named tools already have a contract: argv from `sase/sase.yml`, cwd = project root. Overriding cwd as a first-class `%tool` identity field weakens the thing fingerprints and receipts key on. (Workspace *lease* is a different question; see §5.2.)
4. **A string rewrite creates double-recording traps.** Lowering `%tool:check` to a proc body of `sase tool run -H check` asks for a second hand-off from inside an already detached owner; `-H` refuses that. Lowering to foreground `sase tool run check` hides the run id until after start and records timeouts as signals.
5. **Approval would freeze the wrong digest.** `%proc` approves a code digest. `%tool` has to approve a tool name, normalized definition digest, redacted argv, project, and owner policy, then re-verify the live catalog in the claimed workspace.
6. **The blast radius is a full contract change either way.** `%proc` / `ProcUnitWire` / `xprompt-proc` concerns span sase (parser, admission, proc runtime, ACE, docs, tests) and sase-core (typed units, wires, editor catalog, LSP). A bulk rename still leaves the ledger unintegrated; an additive `%tool` pays the same surfaces once, for the right payload.

### 3.3 Will `%tool` actually get used?

Only if it wins on **composition**. Claude's three pipelines are the right adoption test; nothing else in SASE expresses them:

1. **Post-land verification** — agent lands, then `%tool:check` in a fresh leased checkout of what actually merged.
2. **Scheduled clean-checkout witness runs** — AXE already accepts typed directives in job proposals. Named, clean-tree runs are exactly the witness class E3 is short of.
3. **Gate an agent on a tool result** — `%tool:check` then `%if::` on `waited_outcomes[].outputs.tool_run`. This is currently broken twice (`sase-11k`, empty `outputs`).

`%tool` is a user-authored launch unit. Agent-initiated typed launches still need LaunchApproval. Agent guidance should keep pointing at `sase tool run` and `sase monitor start`; `%tool` must not become a fifth "how do I run a command" story for agents (`sase tool` is already the fourth, after `proc run`, `monitor start`, and gates).

### 3.4 What this work must not become

- **Not capacity admission.** `%q` on a tool unit stays a check, not a claim. E7 owns claims.
- **Not receipts or skip-if-passed.** Gemini's `reuse=true` pulls E4 into a directive that should only record. The E3/E4 consolidation already measured zero receipt-reuse opportunity on apollo.
- **Not remote.** `%dispatch` + tool unit stays rejected; E8 ruled out remote dispatch of tool runs.
- **Not provider tool-calling.** Directives are stripped before the model sees the prompt, so `%tool:check` is not an LLM function-call instruction. Still reserve `%toolset` / `%allow` now for any future provider-permission directive (`sase-17i`), and write the `%tool` description as "Run a project tool as a stand-alone recorded ToolRun."

---

## 4. Where the four reports agree, disagree, and how this report resolves them

### 4.1 Agreement (all four, independently)

- A pure rename with unchanged `%proc` behavior is worse than leaving `%proc` alone.
- `%tool` has to mean "creates a ToolRun," by construction.
- Reuse the existing proc supervisor and E2 hand-off; do not add a supervisor, store, or queue.
- Stay under `typed_launch_units`; do not mint a second flag.
- Named catalog reference is the headline grammar.
- Do not fold E4/E6/E7 behavior into this epic.

### 4.2 Disagreements and resolutions

| Topic | Codex | Claude | Muse | Gemini | Resolution |
| --- | --- | --- | --- | --- | --- |
| Keep `%proc`? | Keep as raw escape hatch | Hard replace; `%proc` is a migration error | Additive, then retire after `sase-s7` | Keep forever as orthogonal primitive | **Additive now.** Zero callers make a hard cutover tempting, but `sase-s6` is still landing and the coordinator still has open bugs. Retiring `%proc` is a *later* flag-gated decision, and it has to happen **before** `sase-s7` deletes the Off branch — Muse's "after `sase-s7`" order is backwards. |
| Ad-hoc code on `%tool`? | No in v1 | Yes, as ad-hoc ToolRuns (`bash=` / `python=` / `::`) | Yes; that is the new home of `%proc` bodies | No; keep on `%proc` | **Named tools only in v1.** Ad-hoc CLI already exists. Unique-script-path identities would pollute LAST/TYPICAL. Add `bash=` later only if launch-graph ad-hoc ToolRuns show up as a real request. |
| Wire type | New `ToolUnitWire` | Keep `ProcUnitWire`, optional tool target | ToolRun-routed; less explicit | New `ToolUnitWire` | **New `LaunchUnitPayloadWire::Tool(ToolUnitWire)`.** A required `code` field cannot honestly represent a named tool. Schema bump is cheap while the feature is beta and persisted typed plans are scarce. |
| Reservation failure | Fail-closed | Fail-open like monitors | Record-first through the executor | Unspecified | **Fail-closed, matching `-H`.** The user asked for a ToolRun locator. Monitor wrapping is fail-open because the *monitor* id is the handle. Catalog errors (unknown name, `args: deny`) fail the unit; they never fall back to running the command ad-hoc. |
| Catalog when? | Snapshot at plan, re-verify in lease | Name-check early; lease is authoritative | Catalog-first at dispatch | Static validate at plan expansion | **Both.** Plan-time snapshot for approval, digest, and unknown-name errors. Execution-time re-check in the leased checkout. Mismatch settles the reserved run `launch_failed` and never starts the command. |
| `workspace=` | Reject cwd/workspace in v1 | Keep default `true` (fresh lease) | Carry proc options through | Unspecified | **Keep proc's project default: `workspace=true`.** That is the post-land / witness pipeline. Show the checkout in the approval preview. `workspace="false"` remains the dirty-tree escape; `sase tool run check` remains the interactive one. Reject `cwd=` on named tools in v1 (catalog cwd is the project root). |
| Extra features | Timeouts + label only | Same; defer continuation | Also `-H` / `-k` / `-x` as directive flags | `handoff=`, `keep_going=`, `reuse=` | **Owner timeouts + `label=` only.** Handoff is implicit (a `%tool` unit is durable by definition). Stage continuation can arrive later as `continuation=default\|always\|never` through the hand-off envelope — today's hand-off rejects continuation flags, so pretending they work would be a contract bug. |
| Wait bug | Mentions graph policy | Fold `sase-11k` into the epic | Untouched `%wait(proc=)` | Untouched | **In scope for tool units.** The three adoption pipelines require terminal settlement. |
| Timing | After hand-off, 4–5 phases | After E3 (`sase-18j`) lands | After `sase-s6` land + `sase-s7` | After E2 | **Now, beside E3.** E2 has landed (Gemini's gate is stale). Serialize sase-core pin moves with `sase-18j`; make no ToolRun *store* wire change. Do not wait for E3's remaining phases. Do not wait for `sase-s7`. |

Claude disclosed seeing one peer summary line while grepping chats and discarded it. The lead did not use peer transcripts; the option-C (siblings) rejection stands on `record-before-admit` and the live `%proc`/`ToolRun` boundary.

---

## 5. Recommended public contract

### 5.1 Grammar (name-first, named tools only)

```text
%tool:check
%tool(check)
%tool(test, tests/test_tool.py, "-k=smoke")
%tool(check, timeout=20m, idle_timeout=5m, label=Preflight)
```

Rules:

- First positional or colon value is a catalog tool name. A positional containing whitespace or shell metacharacters errors with a fix: `%tool expects a tool name; for a raw script use %proc(...)`.
- Later positionals are extra argv tokens, no shell parsing. The catalog `args:` policy is authoritative; the parser does not invent a second policy. Quote commas, equals, and whitespace with the existing directive grammar.
- Keywords in v1: `timeout=`, `idle_timeout=`, `label=`, `workspace=`. No `bash=`, `python=`, `::` fence, `cwd=`, `handoff=`, `-q`/`-v`, or continuation flags.
- One `%tool` per unit; no residual prose; `%id` sets owner/shell display name under the existing stand-alone naming rules.
- `%wait`, `%if::`, `%queue`, `%hold` compose as they do with proc units. `%dispatch` is rejected.
- `%proc` keeps working. Optionally, a targeted suggestion when a `%proc` body is exactly `sase tool run TOOL ...`. No silent rewrite.

`%tool:check` is a new colon form (`%proc` currently forbids colon). That is the right shorthand for a name, and it is why this is a new directive rather than an alias.

### 5.2 Execution and identity

A `%tool` unit is implicitly durable.

1. Admission waits, conditions, holds, and explicit `%queue` checks pass.
2. Allocate the proc owner id. Pre-allocate the ToolRun id so the `_adopt` argv is stable (prepare already refuses argv drift). Record both ids in the admission journal/receipt.
3. Submit an `xprompt-tool` (or equivalently tagged `xprompt-proc`) whose argv is the existing adopting worker, not a private shell script.
4. Supervisor acquires the operational lease when `workspace` is true, sets cwd to that checkout (or the selected project's root when `workspace` is false), and re-resolves the catalog.
5. If the live definition digest matches the approved snapshot, `reserve_handoff_run` is idempotent on the pre-allocated id and the worker claims and executes. If the digest mismatches, or reservation/lease fails, settle the reserved run `launch_failed` and do not start the tool command.

Invariants to keep: one invocation, one ToolRun id; one owner, the proc; one log, the proc log; one workspace lease; no command start before a durable reservation; no catalog TOCTOU after approval.

Origin / lifecycle / `▣` glyph / `%wait(proc=...)` stay executor names. User-facing copy says **tool unit**. Agents-tab label matches `-H`: `tool:check`. PROC SHELL detail gains a Tool run row (id, state, exit, later verdict) plus a `sase tool show` hint. The ToolRun id is the primary locator; `sase tool show/wait/stop` are the user controls.

### 5.3 Waits and `%if::`

- Same-plan wait on a **tool** unit is satisfied at terminal proc settlement only. Agent units may keep today's "launched" meaning (an agent being started is the historical wait). This is a deliberate split, not an accidental inheritance of `sase-11k`.
- Populate `waited_outcomes[i].outputs.tool_run = {run_id, tool, state, exit_code, terminal_cause}` (add `verdict` once `sase-18j` lands). The same fields belong on the external `%wait(proc=<tool-unit>)` path, which today maps success to `launched` and drops the exit code.
- Defer `%wait(tool=<run-id>)`, a static failure shorthand, and injecting the run id into a dependent agent's prompt until the `%if::` form above is actually used.

### 5.4 Approval preview

Show, without secrets: logical id, selected project, tool name, redacted display argv and extra args, definition digest, timeout/idle-timeout/label, workspace (leased vs current tree), waits, condition digest, hold, explicit queue policy.

---

## 6. Recommended internal design

1. **Rust owns the new grammar.** Add `%tool` to the shared directive contract, editor catalog, and LSP snippets. Python `_directive_collect.py` should delegate `%tool` to Rust rather than grow a second name-first parser. Parity tests (`test_xprompt_directive_completion_parity`) stay the gate. A catalog-name `DirectiveValueRole` is new (today's `TOOL_RUN` kind is run ids). If per-render filesystem reads are forbidden on the TUI path, ship directive completion first and catalog values from a cached snapshot.
2. **`ToolUnitWire` beside Agent and Proc.** Fields: `tool_name`, `extra_args`, normalized definition/digest snapshot, redacted display argv, selected project, label, timeout policy, `workspace`, queue/hold. Bump the launch-plan wire schema. Ratches `sase-core-revision.txt` in the same epic after the core change lands. Born canonical.
3. **Catalog snapshot in the typed-plan request.** The planner is pure today. Python loads the selected project's catalog, normalizes it through the existing Rust `ToolDefinition` contract, and passes a versioned snapshot in. Rust resolves the name, validates extra args, renders the preview, and includes the snapshot in the plan content digest.
4. **Reuse hand-off + generalize workspace acquisition.** Share lease logic between `xprompt-proc` and the tool unit. Execute the adopting worker directly. Reverse-link via existing `tool-run:` proc tags plus ToolRun id in proc metadata so ACE can jump owner → run. Coordinator replay must recognize the already-reserved owner/run pair.
5. **Fold `sase-16s` if `dispatch_proc_unit` is rewritten** (stale proc row before hold rebind). Fold `sase-11k` for tool units in the wait/condition phase.

---

## 7. Implementation sketch

One epic, five phases. Plan it as its own unit; name E3 as a concurrent pin-move constraint, not a predecessor. Green-master-independent acceptance (roadmap D7).

| # | Phase | Repos | Size | User-verifiable result |
| --- | --- | --- | --- | --- |
| 1 | Grammar and `ToolUnitWire` | sase-core (+pin), sase delegates parse | large | `%tool:check` and `%tool(test, tests/x)` parse, complete, and preview in TUI and LSP when the flag is on. Unknown names and `args: deny` fail at plan time. `%proc` still works. Flag-off still rejects both. |
| 2 | Durable dispatch | sase (tiny core if any) | large | `sase run '+sase %tool:check'` creates one `▣` proc and one ToolRun owned by that proc. `sase tool show/wait/stop` work. Exactly one notification. Timeout/stop record the typed `terminal_cause`. Catalog drift after approval settles `launch_failed` with no command start. |
| 3 | Terminal waits and condition outputs | sase-core (+pin), sase | medium | A `%tool` then `%wait` / `%if::` fixer pipeline blocks until the tool settles. `sase-11k` closed for tool units. Context carries `outputs.tool_run`. |
| 4 | Surfaces | sase | medium | Approval shows tool + checkout + digest. PROC SHELL detail shows the Tool run row. Visual snapshots refreshed. |
| 5 | Docs, glossary, suggestion | sase + memory | small–medium | `docs/xprompt.md`, `docs/tool.md` ("From an xprompt"), `docs/axe.md`, glossary (`tool-run`, `tool-catalog`, stale Proc Shell `sase-sa`), `xprompts.md` directive table. Optional exact-wrapper `%proc` suggestion. `smoke_sase_tool_runs` gains a live `%tool` case. |

Cross-cutting tests: quoting / `args:` policy; `check-full` as a name; literal zones and fan-out; flag on/off; selected-project mismatch; secret-like extra args only in protected argv; reservation / lease / digest / stop-before-claim / proc-loss / reboot reconciliation; coordinator replay after reserve-before-submit and after ack; exactly one ToolRun, no nested child; older-core floor diagnostic after the wire change.

---

## 8. Alternatives considered

| Option | Verdict |
| --- | --- |
| **A. Flag-day rename, same executor** | Reject. Wrong name, no ledger, large churn. |
| **B. Additive `%tool` named-only, keep `%proc` (this report)** | Recommend. Honest vocabulary, one recording path for the catalog, cheap while beta. |
| **C. Permanent siblings with different recording** | Reject as the end state. Two recording paths forever split the E6/E7 corpus. Acceptable only as the *temporary* shape of B. |
| **D. Hard replace `%proc` with `%tool` including ad-hoc bodies** | Viable later, not v1. Zero callers make it cheap, but it forces ad-hoc ledger identity design into the first epic and rewrites a still-landing coordinator. |
| **E. `%proc(tool=check)` keyword, no new directive** | Reject. The name still says mechanism; completion and discoverability stay wrong. |
| **F. Desugar `%tool` to a `%proc` shell string** | Prototype only. Approval sees code, digest is unchecked, run id arrives too late. |
| **G. Foreground wrap as the default** | Reject. Wrong `terminal_cause`, no owner reconciliation, no notification. Keep as nothing: `%tool` is durable. |

---

## 9. Open questions for Bryan

1. **Confirm named-only v1**, with `%proc` kept as the raw unit until `%tool` has organic use.
2. **Confirm fail-closed reservation** (the `-H` contract) rather than monitor-style fail-open.
3. **Confirm leased-checkout default** (`workspace=true`) for `%tool:check` in project context, with the checkout named in the approval preview.
4. **Confirm `%toolset` / `%allow` is reserved** for any future provider-permission directive.
5. **If `%tool` also records no organic use within ~three weeks of landing**, treat that as evidence for `sase-s7`'s keep/extend/remove decision on typed launch units as a whole, rather than graduating an unused feature to permanently on.

---

## 10. Recommended solution

Proceed with `%tool` as a **new named ToolRun launch unit**, not as a rename of `%proc`.

- Public spelling: `%tool:check` / `%tool(name, extra...)` with owner timeouts, label, and `workspace=`.
- Internal shape: `LaunchUnitPayloadWire::Tool(ToolUnitWire)`, catalog snapshot at plan, digest re-check in the leased workspace, one reserved ToolRun owned by one existing proc via E2 `_adopt`.
- Graph: compose with existing wait/condition/queue/hold; fix tool-unit waits to terminal settlement; fill `%if::` `outputs.tool_run`.
- Scope cut: no ad-hoc bodies, no receipts, no continuation flags, no remote, no new supervisor, no new feature flag.
- Timing: one five-phase epic now, pin-serialized with `sase-18j`, inside the `typed_launch_units` beta window, before `sase-s7` has to decide.

That delivers the ergonomic and adoption benefit the rename was aiming at, keeps "tool" aligned with `sase tool` and ToolRun, and leaves raw durable scripts on `%proc` until something actually uses them.
