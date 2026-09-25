# `%tool` should be a ToolRun launch unit, not a renamed proc

**Independent research report (cdx)** · 2026-09-25  
**SASE snapshot:** `982209db994c2c9b9c45025e0e1c0b9ac3275b49`  
**Published core pin:** `c31b8cf4bad8ea8c5b058a959bb69270ee2d5b30`  
**Linked core inspected:** `96e42d944689412c45a39035764f3422acf261bb`

## Executive conclusion

Adding `%tool` is a good idea. Mechanically renaming `%proc` to `%tool` is not.

The names describe different layers:

- A **ToolRun** is the durable semantic record of work: named tool identity,
  definition digest, fingerprints, stages, outcome, and evidence.
- A **Proc** is one durable execution owner. A handed-off ToolRun may be owned by a
  proc, but it is not thereby a proc.

The current `%proc` directive accepts arbitrary Bash/Python, proc-specific workspace
and cwd choices, total and idle timeouts, a proc shell name, and launch-level
wait/queue/hold policy. Calling that unchanged surface `%tool` would make “tool” mean
“detached script,” while `sase tool` deliberately gives “tool” the narrower and more
valuable meaning of a project-owned catalog entry plus its ToolRun history.

I recommend adding `%tool` as a **new first-class typed launch unit for named catalog
tools**, implemented over the existing proc supervisor and existing ToolRun handoff.
Keep `%proc` as the low-level raw-code escape hatch. Do not make `%proc` an alias for
`%tool`, and do not add fenced arbitrary code to `%tool` in its first version.

The minimal public contract should be:

```text
+sase %tool:check

+sase %tool(test, tests/test_tool.py, "-k=smoke")

+sase %tool(check, timeout=20m, idle_timeout=5m, label=Preflight)
---
%wait
%id:reviewer
Review the result.
```

`%tool` is implicitly durable/handed off. It resolves the named tool through the same
catalog and argv resolver as `sase tool run`, creates exactly one ToolRun, uses exactly
one proc as its owner, and exposes the existing `sase tool show -F`, `wait`, and `stop`
controls. The directive should reject ad-hoc code, output-mode flags, cwd overrides,
and remote dispatch initially.

This should be a focused integration epic (roughly four or five phases), not a spelling
refactor and not a vehicle for receipts, prediction, or automatic admission.

## What I inspected

I read the consolidated roadmap at
`research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md` through the audited
artifact interface, then independently traced the current SASE and sase-core trees. I
did not inspect any report or transcript from the other researchers in this swarm.

The most relevant implementation surfaces are:

- directive parsing and Python mirrors:
  `src/sase/xprompt/_directive_types.py`, `_directive_collect.py`,
  `_directive_extract.py`, and `code_value.py`;
- typed launch wires and adapters:
  `src/sase/core/agent_launch_wire_records.py`,
  `agent_launch_wire_conversion.py`, `agent_launch_wire_from_dict.py`, and
  `agent_launch_facade.py`;
- proc dispatch and admission:
  `src/sase/agent/launch_proc_runtime.py`, `launch_admission_engine.py`, and
  `proc_capacity_admission.py`;
- ToolRun resolution and execution:
  `src/sase/config/tools.py`, `src/sase/tool/argv.py`, `executor.py`, `handoff.py`,
  `handoff_launch.py`, `ownership.py`, and the monitor handoff adapters;
- Rust planner and shared contracts:
  `crates/sase_core/src/agent_launch/typed_units.rs`, `wires.rs`,
  `plan_resolution.rs`, and the Rust editor directive catalog;
- ToolRun core:
  `crates/sase_core/src/tool_run/wire.rs`, `handoff_wire.rs`, and the store lifecycle;
- completion surfaces in the Rust editor catalog, `sase_xprompt_lsp`, ACE, and the
  Python/Rust completion-parity tests.

The linked core is ahead of the published pin only for the relevant queue-capacity
multiplier work. That difference does not change the `%proc`/ToolRun boundary described
here.

## Current state has moved beyond the roadmap snapshot

The roadmap was written on 2026-09-17, before the principal `sase tool` seams existed.
By the current tree:

- the project-owned catalog and `sase tool list` landed in `423316a051`;
- foreground ToolRun execution plus `run`/`runs`/`show` landed in `91b67672b4`;
- stage recording, fingerprints, load samples, bounded logs, and wrapper fidelity have
  landed;
- standalone `sase tool run -H` now reserves a ToolRun and delegates it to a plain
  durable proc (`c0591adf20`);
- `show -F`, `wait`, and `stop` landed in `df8ed51341`;
- owner settlement, notification delivery, end-to-end handoff acceptance, and removal
  of the handoff beta flag landed through `c91690efcb` and `cae16be3ca`;
- failure triage and opt-in stage continuation have started landing.

This validates the roadmap's core choices: record before admission, reuse existing
executors, and keep one ToolRun ID across handoff. It also means `%tool` no longer needs
to invent a control plane. It can be a thin typed-launch integration over a working
one.

The existing `%proc` path remains separate. Rust classifies a prompt slot as a
`ProcUnitWire` when it sees `%proc`; the Python coordinator waits for dependencies and
conditions, admits queue/hold policy, then starts an `xprompt-proc` proc. The supervisor
may acquire a fresh operational workspace and materializes a private 0600 Bash or
Python script. Unless that script itself invokes `sase tool run`, no ToolRun is made.

That difference is the key design fact.

## Critique of the proposed rename

### What is good about the idea

The motivation is sound:

1. **It makes the recorded path easy to author.** `%tool:check` is a much better prompt
   surface than spelling a proc containing `sase tool run check`.
2. **It gives the catalog a launch-graph role.** A named tool can participate in
   `%wait`, `%if`, `%hold`, fan-out, and approval without pretending to be an agent.
3. **It improves adoption structurally.** Heavy work authored through `%tool` cannot
   accidentally bypass the ToolRun ledger.
4. **It reuses mature machinery.** The existing ToolRun handoff already proves the
   one-run/one-owner relationship and the proc supervisor already owns durability,
   timeouts, logs, stop, and crash settlement.
5. **It is user-verifiable immediately.** A user can launch `%tool:check`, see one
   ToolRun and one owning proc, follow it, stop it, and wait on the next launch unit.

### What is wrong with a literal rename

1. **It collapses semantic work into an executor.** The roadmap and glossary are
   explicit that a ToolRun may be owned by a monitor or proc. Renaming a raw proc
   directive makes the abstraction point in the opposite direction.
2. **Arbitrary code has no stable tool identity.** `%proc::` fences and
   `%proc(python=...)` would become ad-hoc ToolRuns at best. Ad-hoc runs cannot support
   the same triage, receipts, or calibrated history as named tools; the current triage
   store explicitly refuses ad-hoc runs.
3. **The inherited options are misleading.** `cwd=` and `workspace=` belong to proc
   preparation. Named tools already have a contract: their argv comes from the
   project-owned `sase/sase.yml` and they run at the project root. Letting `%tool`
   override cwd weakens that identity.
4. **A string rewrite creates double-recording and ownership traps.** Lowering
   `%tool:check` to a shell body containing `sase tool run -H check` would ask for a
   second handoff from inside an already detached owner; current `-H` correctly refuses
   that. Lowering to foreground `sase tool run check` avoids the second handoff but
   hides the ToolRun ID until after the proc starts and leaves approval/digest semantics
   expressed as raw script text.
5. **The catalog can change between approval and execution.** `%proc` approves a code
   digest. `%tool` needs to approve a tool name, normalized definition digest, redacted
   argv, project, and execution policy, then verify the catalog again in the claimed
   workspace before starting it.
6. **The change is wider than its syntax suggests.** A rough reference count in the
   current trees finds `%proc`/`ProcUnitWire`/`xprompt-proc` concerns in 33 primary
   source files, 17 test files, 8 documentation files, and 19 relevant sase-core/PyO3/
   LSP files. A bulk rename would be both risky and architecturally incomplete.

### Critique of the broader roadmap

The roadmap's general direction is strong and subsequent implementation has validated
it. E1 and E2 were correctly separated: the ledger and foreground wrapper could land
before durable handoff, and the handoff reused monitors/procs instead of creating a new
supervisor. The record-first decision and explicit log ownership are exactly what make
this directive feasible now.

I would change the roadmap in one respect: add a small **typed tool launch/adoption
epic** after handoff and before receipts or prediction. The roadmap treated adoption
mainly as instructions plus wrapper recognition. `%tool` is a better authored adoption
surface for launch graphs and scheduled batches. It should not be folded into the much
larger forecast/admission epics.

I would also resist using `%tool` as a shortcut to pull E4/E6/E7 features forward.
Receipts, ETA/routing, and automatic admission each need their own evidence and policy.
An explicit authored `%queue` on a `%tool` unit may continue to act as launch-level
capacity policy, but that is not the future ToolRun cost model and should not be
presented as such.

## Recommended public contract

### Named tools only in v1

Support two forms:

```text
%tool:check
%tool(check)
```

The colon form is the common zero-argument shorthand. In the parenthesized form, the
first positional argument is the catalog tool name and later positional arguments are
extra argv. The ordinary catalog `args: allow|deny` rule remains authoritative:

```text
%tool(test, tests/test_tool.py, "-k=smoke")
```

Arguments containing commas, equals signs, whitespace, or directive punctuation must
use the existing quoting/text-block grammar. Resolution must call the same shared
resolver used by `sase tool run`; the directive must not grow a second argv policy.

Do not support these in v1:

- `%tool::` fenced code;
- `bash=` or `python=`;
- ad-hoc argv after `--`;
- `cwd=` or `workspace=`;
- `-q`, `-v`, or tail controls;
- `%dispatch`/remote execution;
- automatic ETA, routing, receipts, caching, joining, or capacity pricing.

Raw Bash/Python remains `%proc`. Ad-hoc recorded commands remain
`sase tool run -- ARGV...` when invoked directly. This keeps `%tool` synonymous with a
stable named identity.

### Execution-policy options

The useful initial options are owner policy, not alternate tool definitions:

```text
%tool(check, timeout=20m, idle_timeout=5m, label=Preflight)
```

- `timeout=` and `idle_timeout=` are enforced by the proc owner and settle the ToolRun
  with the existing typed timeout cause.
- `label=` changes owner presentation only; it never changes tool identity.
- Handoff is implicit. A `%tool` launch unit is durable by definition, so there is no
  `hand_off=` option.
- Output mode is implicit. The proc owns the sole log, and ToolRun `show -l/-F` follows
  that owner log.

Stage continuation can be added after the basic handoff works. Prefer one directive
field such as `continuation=default|always|never` rather than copying CLI spellings
`-k`/`-x` into prompt syntax. It must flow through the handoff envelope; the current
handoff intentionally rejects continuation flags, so pretending they already work
would be a contract bug.

### Composition with existing launch directives

The following should compose exactly as they do with proc units:

- `%wait` and in-plan logical dependencies;
- `%if::` admission conditions;
- `%queue` as explicitly authored launch capacity policy;
- `%hold`;
- `%id` only as an optional owner/shell display identity, subject to the existing
  stand-alone naming rules.

Within one plan, a bare `%wait` already binds to the preceding logical unit, so a new
`%wait(tool=...)` spelling is unnecessary for v1. Waiting on an external ToolRun ID may
be useful later, but it needs a real ToolRun liveness/outcome wait target in Rust rather
than tunneling through `%wait(proc=...)`.

### Approval and result semantics

Approval should show, without secrets:

- logical unit ID;
- selected project;
- tool name;
- redacted display argv and extra args;
- normalized definition digest;
- timeout/idle-timeout/label;
- waits, condition digest, hold, and explicit queue policy.

The launch result should expose both identities:

- ToolRun ID as the semantic locator;
- proc ID as the execution owner.

The ToolRun should be the primary user-facing locator. The proc remains available for
owner diagnostics, but ordinary follow/wait/stop instructions should use `sase tool`.

## Recommended internal design

### 1. Add `ToolUnitWire`; do not overload `ProcUnitWire`

Add a third Rust launch payload variant alongside `Agent` and `Proc`:

```text
LaunchUnitPayloadWire::Tool(ToolUnitWire)
```

Conceptually, `ToolUnitWire` contains:

- `tool_name` and ordered `extra_args`;
- normalized definition/digest snapshot;
- redacted display argv plus protected execution argv where needed;
- selected project;
- label and timeout policy;
- queue and hold fields.

This is more work than adding `tool_name: Option<_>` to `ProcUnitWire`, but it preserves
the domain boundary, produces honest approval output, and prevents illegal “code plus
tool” combinations. Shared queue/hold structs keep duplication small.

Because this adds a Rust enum variant and changes the launch wire understood by Python,
update the wire schema/version fixtures and move `sase-core-revision.txt` in the same
epic after the core change lands. The core contract should be born canonical rather
than carrying a Python-only translation.

### 2. Give Rust a normalized catalog snapshot during planning

The current planner is pure and receives prompt text, launch kind, selected project,
and flags. `%tool` needs early unknown-name/args-policy validation and a definition
digest in its approval plan.

Load the selected project's catalog in the Python adapter, normalize it through the
existing Rust ToolDefinition contract, and pass a versioned catalog snapshot into the
Rust typed-plan request. Rust should parse `%tool`, resolve the entry, validate extra
args, create `ToolUnitWire`, render the approval preview, and include the tool snapshot
in the plan content digest.

Do not read the catalog independently in both the Python and Rust parsers, and do not
store only a name in the approval plan.

### 3. Reuse the ToolRun handoff and proc supervisor

After waits, conditions, holds, and explicit queue policy pass:

1. allocate the proc owner ID;
2. reserve one `created` ToolRun owned by that proc, using the approved normalized
   definition and protected launch envelope;
3. submit an `xprompt-tool` proc whose argv is the existing ToolRun adopting worker;
4. let the proc supervisor acquire the operational workspace, set the worker cwd to
   that workspace, and verify the live catalog digest against the approved digest;
5. if the digest matches, release the barrier and let the existing worker claim and
   execute the ToolRun;
6. if workspace acquisition or digest verification fails, settle the reserved ToolRun
   as `launch_failed`; the tool command never starts.

The handoff envelope can deliberately leave cwd unresolved and run in the proc
supervisor's claimed workspace. The ToolRun's project identity comes from the approved
catalog snapshot; fingerprint observation uses the worker's actual cwd.

Generalize the workspace-acquisition portion of `launch_proc_runtime.py` so
`xprompt-proc` and `xprompt-tool` share it. Do not create another supervisor. Avoid a
private shell script for named tools; execute the existing Python adopting worker
directly with argv.

This preserves all important invariants:

- one semantic invocation, one ToolRun ID;
- one execution owner, the proc;
- one log owner, the proc log;
- one workspace lease;
- one continuation/settlement path;
- no command start before durable reservation;
- no catalog TOCTOU after approval.

The reservation path should be fail-closed, matching current handoff behavior. That
does not contradict fail-open foreground recording: a `%tool` launch promises a
durable locator and returns immediately, so starting without the promised record would
make its contract impossible to fulfill.

### 4. Make reverse ownership visible

Reuse the existing `tool-run` proc tags, request fingerprint, owner log locator, and
settlement reconciliation. Add the ToolRun ID to proc metadata so ACE and diagnostics
can jump from the owner to the semantic run without scanning the entire ledger.

The launch admission journal/receipt should record both IDs. A replay must recognize
the already reserved owner/run pair rather than allocate a second ToolRun after a
coordinator crash.

## Alternatives considered

### Mechanical rename of `%proc`

Reject. It is easy to explain but wrong in the model, preserves an overly broad raw
code surface, and still does not integrate the ToolRun ledger.

### Lower `%tool` to a `%proc` shell string

Useful only as a throwaway prototype. It can prove UX quickly, but it should not land
as the durable contract because approval sees code rather than a tool definition,
catalog drift is unchecked, quoting/redaction becomes shell-dependent, and the run ID
arrives too late for an authoritative launch receipt.

### Extend `ProcUnitWire` with optional tool fields

Possible as a transitional implementation, but not recommended. Every consumer would
need to enforce the code/tool one-of invariant, proc previews would grow tool branches,
and the public semantic distinction would remain absent from the core wire.

### Remove `%proc` and make `%tool` support named plus ad-hoc code

Reject for the first release. This preserves feature count at the cost of destroying
the strongest reason to add `%tool`: stable catalog identity. It also makes future
triage/receipts behavior vary invisibly by which `%tool` form was used.

## Compatibility and rollout

1. Add `%tool` behind the existing `typed_launch_units` beta flag. Do not add a second
   permanent choice or a second beta flag merely for the spelling.
2. Keep `%proc` working unchanged. Update the flag description, docs, directive
   contract, ACE completions, LSP snippets/actions, highlighting, and completion-parity
   tests in the same phases as the parser surface.
3. Document `%tool` as the preferred form for project verification and any command that
   needs ToolRun evidence. Document `%proc` as raw, durable, non-catalog code.
4. Optionally emit a targeted suggestion when a `%proc` body is exactly a simple
   `sase tool run TOOL ...` invocation. Do not silently rewrite it and do not warn on
   arbitrary proc bodies.
5. Gather real `%tool` use before deciding whether raw `%proc` remains a supported
   launch surface. If it is later deprecated, follow the project's sunset-flag policy
   and provide a targeted migration diagnostic. Do not alias arbitrary `%proc` code to
   `%tool`.
6. Do not graduate or remove `typed_launch_units` merely because `%tool` works; that
   flag also covers `%if::`, raw proc units, and typed launch machinery.

Since `%proc` is beta and default-off, this is the cheapest point to improve the model.
That is an argument for acting now, not an argument for a silent semantic rename.

## Suggested implementation phases and acceptance

### Phase 1 — Core grammar and wire

- Add `%tool:<name>` and `%tool(...)` to the shared Rust directive contract.
- Add `ToolUnitWire`, plan digest/preview, forbidden-combination diagnostics, and
  catalog-snapshot input.
- Validate missing project/catalog, unknown tool, args policy, duplicate tool
  directives, residual prose, raw-code forms, and secret-safe preview.
- Add PyO3 round-trip tests and ratchet the core pin.

**Acceptance:** planning `%tool:check` produces a Tool payload with the normalized
`check` definition digest; no process or store mutation occurs.

### Phase 2 — Durable dispatch

- Reserve ToolRun plus proc owner atomically enough for replay.
- Add `xprompt-tool` preparation reusing operational workspace acquisition.
- Verify the catalog digest in the leased workspace.
- Execute the existing adopting worker directly and settle all pre-start failures.

**Acceptance:** `%tool:check` creates exactly one ToolRun and one proc; ToolRun owner is
that proc; both settle consistently; the proc log is the only output of record.

### Phase 3 — Graph policy and control

- Prove waits, conditions, holds, explicit queue fields, total timeout, idle timeout,
  stop, cancellation, coordinator replay, and supervisor loss.
- Return both run/proc locators in launch results and receipts.

**Acceptance:** a two-unit `%tool` then `%wait`/agent plan stays blocked until the tool
settles, and `sase tool stop RUN` suppresses command continuation through the existing
owner path.

### Phase 4 — Authoring surfaces

- Update ACE, LSP, docs, examples, syntax highlighting, and completion parity.
- Add named-tool completion from the selected project's catalog if that can be done
  without per-render filesystem reads; otherwise ship directive completion first and
  catalog values in a follow-up cached snapshot.
- Update generated instruction sources only through their normal generated-skill
  workflow if guidance changes.

**Acceptance:** flag-on ACE and LSP advertise identical `%tool` forms and options;
flag-off behavior remains explicit and tested.

### Phase 5 — Continuation and migration polish (optional)

- Carry `continuation=default|always|never` through the handoff envelope.
- Add the exact-simple-wrapper `%proc` suggestion.
- Measure usage and decide, separately, whether `%proc` should remain.

## High-risk test cases

The implementation should have explicit tests for:

- quoted commas/equal signs and `args: allow|deny`;
- tool names such as `check-full`;
- literal zones, disabled xprompt regions, fences, fan-out, alternates, and repeats;
- flag off/on behavior and Rust/Python/ACE/LSP catalog parity;
- selected-project mismatch and no selected project;
- catalog digest changing between approval and acquired workspace;
- secret-like extra args appearing only in protected argv, never preview/log metadata;
- reservation failure, proc submission failure, workspace failure, exec failure,
  timeout, stop-before-claim, proc loss, and reboot reconciliation;
- coordinator replay after reservation but before proc submission and after proc ack;
- exactly one ToolRun for a named tool, with no nested child ToolRun;
- owner log replay/follow and reverse proc-to-ToolRun navigation;
- zero raw command execution when durable reservation cannot be made;
- older core rejection with an actionable floor diagnostic after the wire change.

## Final recommendation

Proceed with `%tool`, but change the plan from “rename `%proc`” to “add a first-class
named ToolRun launch unit.” Keep `%proc` for raw durable code. Use a new Rust
`ToolUnitWire`, validate against an approved catalog snapshot, recheck the definition
inside the claimed workspace, reserve exactly one ToolRun owned by exactly one existing
proc, and expose the ToolRun ID as the primary result.

Ship only named-tool execution, owner timeouts/label, and composition with the existing
launch graph at first. Defer ad-hoc code, external ToolRun waits, continuation modes,
receipts, prediction, and admission until each has its own evidence and contract.

That solution delivers the intended ergonomic and adoption benefit without confusing
the durable work record with the process that happens to execute it.
