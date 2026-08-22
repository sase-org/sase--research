---
create_time: 2026-08-22
updated_time: 2026-08-22
status: research
---

# Stand-alone proc launch units and the `%proc` directive

## Research question

How should SASE add stand-alone proc shells—proc shells that are not members of an
agent family—so they can run Bash or Python from an xprompt swarm, participate in
`%wait`, and safely claim and release project workspaces?

This report consolidates two independent reports and a third inspection of the current
tree at `a22ca4d61b`, plus audited reads of the earlier proc taxonomy, named-proc, and
monitor-substrate research. It is architecture research, not an implementation plan.

## Executive recommendation

Make `%proc` a **first-class proc launch unit**, not an agent modifier, synthetic agent,
or monitor wrapper. A mixed xprompt submission should expand into typed launch units
(`Agent` or `Proc`); a proc unit should be reserved in the existing durable proc store,
wait without consuming an LLM slot or workspace, acquire an operational workspace lease
only when ready to execute, run through the existing detached supervisor, and settle the
lease before becoming terminal.

The recommended surface is:

````text
%proc("just check")
%proc(bash="just check")
%proc(python="from sase.procs import read_procs; print(read_procs())")

#git:sase
%proc::
```bash
just install
just check
```
````

An omitted fence language means Bash. Python runs with SASE's `sys.executable`, which
provides the installed SASE package and dependencies without activation scripts or
`PYTHONPATH` manipulation.

Use the proc ID as the canonical execution identity in v1. If human-readable naming is
included, it should be an optional bare stand-alone `shell_name`, with no `--` family
qualification and no agent artifacts record. Generalize launch dependencies so bare
`%wait` in a mixed swarm points to the preceding typed unit and explicit proc waits use
`%wait(proc=...)`. Do not manufacture `done.json` merely to fit an agent-only resolver.

For project-scoped proc units, workspace leasing should be the default execution mode,
with an explicit `workspace=false` escape hatch for commands that only inspect global
state or wait. Crucially, the supervisor waits first and leases second. A proc with no
project context can run in an explicitly validated ordinary `cwd` without a lease.

## 1. Findings established by all three investigations

### 1.1 Execution machinery already exists

`src/sase/procs/` already supplies nearly everything `%proc` needs:

- durable reservation and proc IDs;
- detached, acknowledged supervision and a launch barrier;
- process-group signals, combined logs, and total/idle timeouts;
- persisted requests and result publication;
- idempotent settlement and reconciliation; and
- optional workspace-claim settlement policy.

`src/sase/workspace_provider/lease.py` is explicitly for non-agent host work. It claims
only machine-owned workspaces, materializes and prepares the checkout, transfers or
binds ownership to the proc supervisor, and releases through settlement. Failures never
fall back to workspace 0. `%proc` should compose these facilities, not shell out to
`sase proc run`, reuse `sase monitor start`, or create another supervisor.

### 1.2 The launch pipeline is agent-shaped today

The current swarm pipeline splits on top-level `---`, expands xprompt swarms, validates
agent names and providers, plans agent fan-out, rewrites bare `%wait` to the previous
agent name, creates agent artifacts, and calls the provider executor for every segment.
Therefore, merely adding `proc` to `_KNOWN_DIRECTIVES` is unsafe: extraction could strip
the executable payload while the remaining segment still follows the LLM path.

Classification must occur after swarm/template expansion exposes `%proc`, but before
agent-only normalization, model/provider checks, name allocation, runner admission, VCS
rollover injection, or artifacts creation.

### 1.3 `%proc::` needs a real fenced-code parser

Today's directive `::` support is the `%clan` summary shorthand. It expects `:: `,
captures prose until another line-boundary directive, and treats fences as protected
content. That grammar cannot correctly parse:

````text
%proc::
```python
print("%wait and #refs are literal here")
```
````

The existing `fenced_block_details` scanner should be reused to capture exactly one
closed CommonMark fence after `::`, permitting horizontal whitespace and blank lines
before the opening fence. Script contents become a literal zone: no directive,
xprompt, separator, command substitution, artifact reference, file inclusion, or Jinja
pass may reinterpret them.

### 1.4 Python should use SASE's interpreter

Both reports correctly converge on `sys.executable`. It is more reliable than system
`python3`, virtualenv activation, or `PYTHONPATH` injection and is the useful reason to
offer `python=`. It should not inject SASE objects or an implicit import prelude; normal
`import sase` is explicit and unsurprising.

### 1.5 Scripts should be files, not argv payloads

Materialize source with mode `0600` under the proc's private runtime directory and run:

```text
[/bin/bash, --noprofile, --norc, script.sh]
[sys.executable, script.py]
```

This avoids process-list exposure, argv-size limits, nested quoting, and poor Python
tracebacks. Do not inject `set -euo pipefail`; the user owns script semantics. Store a
source hash in the request fingerprint and show a safe preview in the public proc row.

## 2. Resolving the reports' disagreements

### 2.1 Identity: proc-native wins over a one-shell synthetic agent

Report A proposes a one-shell SASE agent, with an agent artifacts directory and
`done.json`, because today's `%wait` indexes agents. Report B proposes a proc-only row
and a typed wait backend.

The proc-native design is better supported by the domain model and earlier research:

- prior consolidated taxonomy explicitly records
  `shell_name set, artifacts_dir None -> standalone proc shell` and
  `shell_name set, artifacts_dir set -> family-attached proc shell == monitor`;
- the named-proc report says the artifacts projection preserves family roster, chat,
  `#fork`, claim-transfer, and monitor history—features a stand-alone command does not
  inherently possess;
- the Procs pane already presents non-monitor procs; and
- creating agent artifacts would pull a non-LLM command into agent counts, history,
  variables, finalizers, completion notifications, and runner invariants unless every
  consumer learned an exception.

The current glossary says every SASE shell belongs to a SASE agent, so implementation
will require an explicitly approved memory/glossary update. That wording should follow
the persisted model rather than force an unnecessary runtime projection.

Recommendation: reserve a normal `lifecycle="proc-shell"` row with origin
`xprompt-proc`. The proc ID is canonical. An optional `shell_name` is a user-facing
address, not an encoded owner. A bare name outside an agent should remain bare; inside
an agent, existing `agent--role` qualification remains monitor/family behavior.

### 2.2 Waiting: generalize dependencies instead of duplicating artifacts

Report A reuses `waiting.json`, `ready.json`, and `done.json`; report B introduces typed
wait targets. The latter is the cleaner boundary.

Bare `%wait` in a swarm means “the preceding launch unit,” not intrinsically “the
preceding agent.” Allocate stable identities during preflight and compile it directly:

```text
WaitTarget = Agent(agent identity) | Proc(proc id) | Bead(project, bead id)
```

Keep positional `%wait:<name>` agent-compatible. Add repeatable
`%wait(proc=<id-or-unique-name>)` for explicit proc dependencies. Proc supervisors
persist their wait spec in the request sidecar, expose `phase="waiting"`, and use a
shared pure dependency resolver. Agents may retain their existing marker files and
queue adapter.

V1 proc units should accept agent/proc/bead/time dependencies and reject
`runners=`/`priority=`, which control scarce LLM admission rather than proc execution.
A dependency becomes resolved when the target is terminal; whether downstream work
requires success should be a separate condition. This avoids the surprising Report A
proposal in which a failed proc leaves all dependents apparently hung.

The proc supervisor must remain kill-responsive while waiting. Execution timeouts begin
when the child starts, not while waiting for dependencies or a workspace.

### 2.3 Workspace policy: default by execution context, acquire after waiting

Report A defaults to no lease and requires `workspace=true`; Report B always leases a
project workspace. Neither rule alone fits all proc uses.

Use this contract:

| Proc context | Default |
| --- | --- |
| explicit/inherited `#git:` or `#gh:` project ref | lease that project |
| current registered project selected by the launch surface | lease that project |
| no project context + explicit ordinary `cwd` | run there without a lease |
| `workspace=false` | validated opt-out; no lease |

This makes the motivating case—run work in a claimed SASE workspace—safe by default,
while preserving lightweight global commands. An inherited VCS ref is not accidental:
it deliberately gives every swarm segment project context. It must not inject
`#commit`, `#pr`, or `#propose` into proc units.

Do not call today's `submit_via_lease` before `%wait`; that occupies a workspace while
idle. Persist admission intent, reserve/start the supervisor, resolve waits, then let
the supervisor acquire the operational lease with its own PID immediately before child
spawn. Bind the settlement policy durably before opening the execution barrier.

Command-owned lease acquisition from Python is unsafe unless the lease is attached to
the current proc's settlement record: SIGKILL bypasses the script's `finally`. Prefer
directive-owned leasing and provide an `attach_operational_lease_to_current_proc`
helper only if nested/dynamic acquisition is a real use case.

### 2.4 General-purpose `code` type: ship a complete slice

The request explicitly asks for fenced code as a future xprompt input type. Add a
structured value now, but expose `type: code` only when every relevant surface supports
it in the same slice:

```text
CodeValue { source: str, language: str | null, info_string: str | null }
```

The parser preserves the raw language; the `%proc` consumer maps it to an interpreter.
String interpolation renders `source`, while templates may access `.source` and
`.language`. Update Python input parsing/binding, Rust catalog/frontmatter schema,
completion, diagnostics, show/preview models, and type-directed `#xprompt::` binding
together. An enum entry without type-directed fence binding would advertise a feature
that does not work.

## 3. Recommended surface contract

### 3.1 Syntax

Accept in v1:

```text
%proc("just check")
%proc(bash="just check")
%proc(python="print('hello')")
%proc:: + exactly one following fenced block
```

Reject duplicate bodies, positional-plus-keyword bodies, `bash=` plus `python=`, empty
source, unknown kwargs, unclosed fences, unsupported languages, residual prompt prose,
and multiple `%proc` directives in one unit.

Do not add colon shorthand (`%proc:just check`) initially: unlike `%id:value`, an
unquoted command commonly contains spaces and directive-like text, so its boundary is
hard to explain consistently. Parentheses are excellent single-line syntax and `::`
is the excellent multi-line syntax. An alias can wait; `%p` is not necessary for v1.

For fences, accept no language (Bash), `bash`, and `python`. Reject aliases such as
`sh`, `shell`, `py`, and `python3` until each has a deliberate runtime contract.

Reasonable v1 kwargs are `timeout=`, `idle_timeout=`, `cwd=`, `workspace=`, and
`label=`. All are optional; none should repeat monitor's required-reason policy.

### 3.2 Directive compatibility

| Surface | Proc behavior |
| --- | --- |
| project refs and xprompt swarm expansion | support |
| `%wait` agent/proc/bead/time targets | support |
| `%id` | optional display name only; never family identity |
| `%hide` | support only if Procs history already has an equivalent bit |
| `%model`, `%effort`, `%auto`, `%final` | reject: LLM/finalizer-only |
| `%clan`, family attachment, tribe | reject in v1 |
| `%wait(runners=...)`, `%wait(priority=...)` | reject: LLM-admission-only |
| `%repeat`, `%alt` | defer until typed-unit fan-out has stable IDs and previews |

Use an allowlist and precise errors. Silently ignoring agent-only directives would make
mixed swarms difficult to audit.

## 4. Internal architecture

### 4.1 Typed mixed launch plan

Introduce a cross-frontend plan in `sase-core`, because parsing/classification and wait
semantics must match CLI, ACE, editor, mobile, and future web surfaces:

```text
LaunchPlan { units: Vec<LaunchUnit> }
LaunchUnit { kind: Agent | Proc, source_index, wait, project, payload }
ProcUnit { reserved_proc_id, script: CodeValue, interpreter, workspace_policy }
```

Planning order:

1. split only on top-level swarm separators;
2. expand xprompt swarms/templates while preserving existing literal zones;
3. recognize and protect `%proc` script spans on every expansion iteration;
4. classify each final segment as agent or proc;
5. reserve stable identities and compile bare waits to typed targets;
6. resolve projects and validate the entire mixed plan;
7. show an authorization preview; then
8. dispatch agents to the existing fan-out executor and procs to the proc supervisor.

The result type should also be tagged (`AgentLaunchResult | ProcLaunchResult`). Provider
guards, model fan-out, agent naming, artifacts allocation, and runner capacity operate
only on agent units. Approval limits and previews count both.

### 4.2 Proc admission and lifecycle

Persist wait, workspace, and script intent in a versioned request sidecar. Suggested
phases are `waiting`, `acquiring-workspace`, `preparing-script`, `running`, and
`settling`. The safe sequence is:

```text
reserve proc -> start/ack supervisor -> wait -> claim workspace -> persist claim policy
-> write script -> spawn child -> collect result -> settle/release -> terminal status
```

The proc must be stoppable in every phase. Terminal status is published only after
claim settlement; otherwise a dependent can start while the upstream workspace remains
occupied. Crash recovery cannot atomically update the proc store and project RUNNING
field, so persist enough intent and workflow/PID identity for stale-claim reconciliation
and add crash-injection tests around every boundary.

### 4.3 Environment

Start from the supervisor's sanitized environment, removing parent-agent, chop, and
artifacts identity. Add explicit `SASE_PROC_ID`, `SASE_PROJECT`, `SASE_PROJECT_FILE`,
`SASE_WORKSPACE_NUM`, and `SASE_WORKSPACE_DIR` where applicable. Prepend
`dirname(sys.executable)` to `PATH` so Bash finds the same `sase` executable. Do not set
`SASE_AGENT=1` or fabricate `SASE_ARTIFACTS_DIR`.

## 5. Important risks and tests

- **Known directive before classifier:** may strip code and accidentally launch an LLM.
- **Literal-zone recursion:** generated `%proc` must be recognized, but its script must
  never be expanded again.
- **Partial mixed launch:** validate the full plan before spawning any unit.
- **Waiting resource leak:** no runner slot or workspace while a proc waits.
- **Claim race:** child cannot exec before durable claim binding; terminal cannot publish
  before release.
- **Primary-checkout fallback:** never use workspace 0 after allocation failure.
- **Name collision:** active optional names must resolve through existing proc uniqueness
  and produce actionable `show`/`kill` guidance.
- **Authorization:** previews must show expanded executable source, interpreter, project,
  waits, and workspace policy, especially when an xprompt introduced `%proc`.

Required integration tests include agent→proc and proc→agent waits, proc→proc bare
waits, bead/time waits, upstream failure semantics, kill while waiting, kill while
running, timeout, allocation failure, crash between claim and policy persistence,
settlement replay, mixed-plan preflight failure, fenced literal `%`/`#`/`---`, and
Python `import sase` under `sys.executable`.

## 6. Delivery sequence

1. Land the structured fenced-code parser and a complete `code` input-type slice.
2. Add the Rust directive contract and proc classifier behind one disabled feature flag;
   do not expose a known-but-unlaunchable directive.
3. Introduce typed mixed launch plans/results and stable proc identity allocation.
4. Generalize wait targets/resolution and implement supervisor-side waiting.
5. Add deferred operational leasing and durable claim settlement.
6. Add execution, previews, Procs-pane presentation, docs, and lifecycle tests.
7. With explicit user approval, update glossary/memory to define stand-alone proc shells
   independently of agent-family attachment and regenerate derived instructions.

## Recommended solution

Implement `%proc` as a **proc-native typed launch unit** in the xprompt launch planner.
Parse parenthesized Bash/Python strings or exactly one fenced block after `::`; default
an unlabelled fence to Bash; execute private script files through `/bin/bash` or SASE's
`sys.executable`; and preserve script text as a literal zone.

Reserve the proc before dispatch so mixed-swarm waits have a stable typed target. Keep
the stand-alone proc out of agent artifacts and LLM runner accounting, generalize
`%wait` to address agents, procs, beads, and time, and let the proc supervisor wait
without resources. When ready, acquire a machine-owned operational lease for its target
project, bind the claim durably, execute, and release through existing idempotent
settlement before publishing the terminal state.

This design follows SASE's existing persisted taxonomy—stand-alone named proc versus
family-attached monitor—while solving the actual cross-cutting gaps: mixed launch-unit
planning, literal fenced code, typed dependency resolution, and deferred workspace
admission. It is more work than fabricating an agent artifacts directory, but it avoids
building a permanent second-class proc feature on agent-only assumptions.
