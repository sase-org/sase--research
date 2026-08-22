---
create_time: 2026-08-22
updated_time: 2026-08-22
status: research
---

# Stand-alone Proc Shells and the `%proc` Xprompt Directive

**Research question:** What design should SASE use for stand-alone proc shells that
claim project workspaces, participate in xprompt swarms, execute Bash or Python source,
and honor useful standard directives such as `%wait` without pretending to be agents?

**Scope:** SASE at `a22ca4d61b` and `sase-core` at `fc9e98c570`, inspected on
2026-08-22. This is implementation-oriented architecture research, not an implementation;
no SASE runtime behavior was changed.

## Bottom line

`%proc` should be a **first-class launch-unit kind** backed by the existing durable proc
service and operational workspace lease machinery. It should not be implemented as a
special agent, a monitor, or a Bash wrapper around `sase proc run`.

The launch path should expand xprompt swarms and remaining launch-visible xprompt
references, classify every resulting segment as either an agent or a proc, validate the
entire mixed batch, and then dispatch each typed unit.
A proc should be reserved immediately so it has a durable ID and can be waited on, but
its detached supervisor should satisfy `%wait` first and acquire a machine-owned project
workspace only immediately before executing the script. Normal completion, error, kill,
timeout, or launch failure should all enter the existing idempotent settlement path,
which releases the workspace exactly once.

The source syntax should be:

````sase
#git:sase %proc("just check")
#git:sase %proc(bash="just check")
#git:sase %proc(python="from sase.procs import read_procs; print(len(read_procs()))")

#git:sase
%proc::
```bash
just check
```
````

An omitted fence language means Bash. Version 1 should accept only `bash` and `python`
when a language is present and should reject every ambiguous combination rather than
guess. Python should run with the exact `sys.executable` that is running SASE, inside the
leased checkout and the sanitized proc environment; that supplies SASE's installed
Python environment without activation scripts, `PYTHONPATH` mutation, or injected
Python globals.

The difficult part is not starting a subprocess. It is preserving SASE's launch,
literal-zone, dependency, workspace, and settlement invariants across a unit that has no
agent artifacts directory and no agent family owner.

## 1. Findings from the current implementation

### 1.1 The proc subsystem already owns almost all execution mechanics

`src/sase/procs/` is a durable proc-shell service, not merely a CLI convenience:

- `ProcSubmitRequest` persists argv, cwd, environment, attribution, timeouts, a workspace
  claim policy, result paths, artifacts, and follow-up policy in a request sidecar;
- `submit_proc_request` atomically reserves a proc row, writes the request, starts a
  detached supervisor, waits for its acknowledgement, and then opens a launch barrier;
- `supervisor.py` owns signals, process groups, bounded combined logs, total and idle
  timeouts, sanitized child environments, and terminal result selection;
- `settlement.py` runs resumable checkpoints for output, workspace claims, artifacts,
  follow-ups, and result publication before the proc becomes terminal;
- the Rust proc store provides atomic reserve, claim, update, stop, settling, finish,
  concurrency, retention, and reconciliation operations; and
- `wait_for_proc` and proc ID/name resolution already provide observation and control.

This is the correct execution substrate. A `%proc` implementation should submit an
ordinary `lifecycle="proc-shell"` row with an origin such as `xprompt-proc`. Its
`proc_id` is the canonical stand-alone identity. It does not need a fake agent name or a
synthetic agent artifacts directory.

### 1.2 Operational leases are explicitly designed for non-agent work

`src/sase/workspace_provider/lease.py` describes its abstraction as “durable operational
workspace leases for non-agent host work.” It already:

1. claims from the unified machine-owned workspace pool;
2. refuses the user-owned primary checkout;
3. materializes and prepares the leased checkout from its primary remote;
4. produces a durable settlement policy;
5. can transfer a caller-owned claim to an acknowledged proc supervisor; and
6. releases the claim idempotently during proc settlement.

`submit_via_lease` is therefore close to the required no-wait path. It is not sufficient
for `%wait`, however: callers must acquire the lease before submission. Using it as-is
would make a proc occupy a workspace for its entire wait, which is both wasteful and
inconsistent with deferred agent launches.

The missing primitive is **supervisor-owned admission**: persist the desired project and
wait policy when the proc is reserved, let the detached supervisor wait without a claim,
then let that same supervisor acquire and durably bind the operational lease immediately
before child spawn.

### 1.3 The current launch pipeline assumes every expanded segment is an agent

The high-level flow in `src/sase/agent/launch_cwd_agents.py` currently:

1. splits the submitted text on top-level `---` separators;
2. expands xprompt swarms into more segments;
3. guards every segment against disabled LLM providers;
4. validates agent names and agent-only fan-out directives; and
5. sends every segment to the single- or multi-agent launch machinery.

The preview, launch guard, result types, multi-prompt planner, bare `%wait` rewriting,
timestamp/name allocation, and Rust `LaunchFanoutSlotWire` all encode the same
assumption. Adding `%proc` only to `PromptDirectives` would allow it to reach agent model
selection and workspace planning before anybody knew it was not an agent.

The correct boundary is earlier: after segment expansion and all launch-visible xprompt
expansion, but before provider guards, agent naming, default home normalization, or agent
fan-out planning. This needs one proc-aware literal-protection pass around the ordinary
xprompt expansion that remains after swarm expansion. Each resulting segment should
become a typed `LaunchUnitWire`.

### 1.4 Existing fence scanning is strong enough, but it is not yet a reusable value

`src/sase/xprompt/_fenced_blocks.py` already has a structured scanner that returns:

- the complete block range;
- opening and optional closing fence ranges;
- an optional info string; and
- the exact content range.

It handles backtick and tilde fences, longer closing fences, up to three leading spaces,
trailing whitespace, and live unclosed blocks. The multi-prompt splitter is fence-aware,
so a `---` inside a `%proc` script will not create another swarm segment.

Today fences are protected as opaque strings. There is no typed value that retains
source and language, and the Rust launch planner contains a separate, narrower fence
scanner. `%proc` should not add a third regex. The structured behavior should become a
shared core contract returning a value such as:

```text
CodeBlockValue {
    source: String,
    language: Option<String>,
}
```

The generic value must preserve `None` for an omitted language. Bash is a `%proc`
consumer default, not an intrinsic property of every code block. This distinction is
what makes the type suitable for a future `input: code` xprompt argument.

### 1.5 Single-line script strings create a literal-zone problem

Fenced source is already protected from xprompt expansion, Jinja rendering, command
substitution, artifact references, file references, directive extraction, `%alt`, and
multi-prompt splitting. A string inside `%proc("...")` is not.

Without a new literal range, source such as the following could be rewritten before it
is executed:

```sase
%proc(bash="printf '%s\n' '#review' '$(date)' '@literal'")
```

That is a correctness and security issue. The proc-script scanner must expose the source
span of all three single-line forms, and those spans must join the existing literal-zone
protection on every xprompt-expansion iteration. Template expansion may produce a new
`%proc`, so a one-time pre-scan is not enough.

The contract should be: xprompt/template machinery may produce a proc directive, but
once text is recognized as its script payload, that text is literal. It does not undergo
another pass of xprompt expansion, `$(...)`, `@path`, artifact-ref, Jinja, directive,
alternative, or separator processing.

### 1.6 `%wait` has reusable resolution logic but agent-specific persistence

The `%wait` surface currently supports:

- positional agent dependencies;
- `bead=` dependencies;
- `time=` duration or absolute-time floors;
- `runners=` participating-agent slot thresholds; and
- `priority=` within the agent runner queue.

Agent runners persist `waiting.json` and `ready.json` under an agent artifacts directory.
They use a shared dependency index for agent/artifact/bead resolution, but the barrier,
markers, slot admission, and completion stamp are agent-specific.

A stand-alone proc has no legitimate agent artifacts directory. Creating one solely to
reuse `run_agent_wait.py` would corrupt the domain model and make the proc appear to be
an agent. The reusable dependency predicates should instead sit behind a generic typed
wait target, while the proc supervisor persists its wait request and progress in its
existing runtime sidecar and `Proc.phase`.

`runners=` and `priority=` are specifically controls for scarce LLM runner slots. They
are neither possible nor useful for a proc, so v1 should reject them on a `%proc` unit
with a precise error. Agent, proc, bead, duration, and absolute-time dependencies are
useful and should be supported.

### 1.7 The current terminology assumes proc shells have agent owners

The current glossary defines a Sase Shell as a member of a Sase Agent, and
`qualify_proc_shell_name` requires a bare named proc shell to be qualified beneath the
calling agent as `<agent>--<shell>`. The persisted proc model itself is less restrictive:
`shell_name` is optional, and all command procs already use the proc-shell lifecycle.

Version 1 does not need to redesign names. Leave `shell_name=None`, use the proc ID as
the stand-alone identity, and show the row through the existing Procs pane and proc
indicator. Do not render it as an Agents-tab node. The glossary should eventually be
updated to say that proc shells may be family-attached or stand-alone; if user-assigned
stand-alone names are added later, ownership should become an explicit nullable field
rather than continuing to encode ownership in a `--`-qualified string.

## 2. Recommended surface contract

### 2.1 Single-line forms

Accept exactly these parenthesized shapes:

```sase
%proc("just check")
%proc(bash="just check")
%proc(python="from sase import __version__; print(__version__)")
```

Rules:

- one positional string means Bash;
- `bash=` and `python=` are mutually exclusive;
- a positional value cannot be combined with either keyword;
- there must be exactly one script value;
- unknown keywords, extra positional arguments, empty source, missing `)`, and duplicate
  keywords are errors;
- colon and plus shorthands are not accepted for `%proc`; and
- no short alias should be introduced initially—`%p` is too valuable a namespace to
  consume before usage proves it worthwhile.

Quoted, text-block, and escape behavior should come from the existing xprompt argument
parser, but the parsed source must remain marked literal rather than being sent through
ordinary directive-argument expansion.

### 2.2 Multi-line form

Use a line-oriented `::` introducer followed by exactly one fenced code block:

````sase
%proc::
```python
from sase.procs import read_procs
print([proc.proc_id for proc in read_procs()])
```
````

Allow horizontal whitespace after `::` and blank lines before the opening fence. Require
the opening fence to begin on its own Markdown line. This keeps the syntax compatible
with the existing scanner; supporting `%proc:: ```bash` on one line would be a bespoke
non-Markdown fence grammar with no compensating benefit.

The content is the exact scanner `content_range`. Preserve its newlines and indentation;
do not `.strip()` the program. Require a closing fence at launch time even though the
editor scanner represents live unclosed fences. A longer fence naturally permits fence
text inside a script.

Language rules for v1:

| Fence info string | Interpreter |
| --- | --- |
| absent | Bash |
| `bash` | Bash |
| `python` | SASE's Python interpreter |
| anything else, multiple tokens, or attributes | explicit validation error |

Aliases such as `sh`, `shell`, `py`, and `python3` look friendly but obscure the exact
runtime contract. They can be added compatibly if real prompts demand them. Arbitrary
fence languages must not be converted into executable names.

The segment may also contain a project reference and supported control directives, but
no residual prompt prose. A mixed agent/proc segment is almost certainly a mistake and
should fail rather than silently discard the prose.

### 2.3 Swarm example

An xprompt swarm can contain agent and proc units together:

````sase
#git:sase
%id:builder
Implement the parser change and run focused tests.
---
#git:sase
%wait
%proc::
```bash
just check
```
---
#git:sase
%wait
Review the implementation and verification output.
````

Bare `%wait` should retain its current “previous launch slot” meaning, but the planner
must stop rewriting it to an agent-name string. It should attach a typed dependency on
the previous unit:

```text
WaitTargetWire::Agent(planned agent identity)
WaitTargetWire::Proc(preallocated proc_id)
```

That lets a proc wait for an agent and an agent wait for a proc. It also eliminates the
current naming poll when the previous unit already has a typed launch identity.

For explicit dependencies, add repeatable `%wait(proc=<proc-ref>)` alongside the existing
positional-agent and `bead=` forms. A proc ref may use the same exact/unique ID resolution
as `sase proc show`. Existing positional arguments remain agent names for compatibility.

### 2.4 Directive compatibility in v1

| Surface | Proc behavior |
| --- | --- |
| project VCS reference | required unless the current project is unambiguous |
| xprompt expansion / xprompt swarms | supported around the proc payload |
| `%wait:<agent>` / `%wait(bead=...)` / `%wait(time=...)` | supported |
| `%wait(proc=...)` | add and support for both proc and agent units |
| bare `%wait` in a multi-unit launch | typed dependency on the previous unit |
| `%wait(runners=...)`, `%wait(priority=...)` | reject on proc units; agent-only |
| `%model`, `%effort`, `%auto`, `%final` | reject; LLM/finalizer-only |
| `%id`, `%clan`, family attachment | reject; agent identity-only |
| `%repeat` and `%alt` | reject for proc units in v1; add only with typed proc fan-out semantics |
| `%hide` | reject until proc history/notification semantics are deliberately defined |

This allowlist is better than silently ignoring directives. A standard directive can be
added later without breaking valid prompts; assigning accidental meanings now is much
harder to unwind.

### 2.5 Project and workspace behavior

`%proc` should mean “run a script in a leased SASE project workspace,” not “run arbitrary
code in whichever directory launched SASE.” Resolve the project as follows:

1. an explicit known-project VCS reference wins;
2. otherwise use the current SASE project when it is unambiguous; and
3. otherwise fail with an actionable request for a project reference.

Never fall back to workspace 0, the user's current checkout, or generic home mode. The
existing `sase proc run` remains the appropriate interface for a proc intentionally
running in an explicitly supplied ordinary cwd.

The leased checkout is ephemeral operational state. Logs and the proc result survive;
uncommitted files in the released checkout do not constitute a durable output and may be
reset on its next lease. If a later workflow needs the same dirty workspace, that should
be a future explicit atomic handoff policy, not an implicit consequence of adjacency in
a swarm.

## 3. Proposed internal architecture

### 3.1 A generic launch plan above the agent planner

Add a cross-frontend wire owned by `sase-core`:

```text
LaunchPlanWire {
    units: Vec<LaunchUnitWire>,
}

LaunchUnitWire {
    execution_kind: Agent | Proc,
    source_index: u32,
    template_group: Option<String>,
    swarm_xprompts: Vec<String>,
    wait: WaitSpecWire,
    agent: Option<AgentUnitWire>,
    proc: Option<ProcUnitWire>,
}

ProcUnitWire {
    proc_id: String,
    project_ref: ProjectRefWire,
    script: CodeBlockValue,
    interpreter: Bash | Python,
}
```

Keep `LaunchFanoutPlanWire` inside `AgentUnitWire`; do not add proc fields to every agent
fan-out slot. The current Rust `agent_launch` module can continue to plan model,
alternative, and repeat fan-out for agent units only.

Preallocate every proc ID during pure preflight. That makes previews stable, lets a later
unit depend on a proc before it has spawned, gives the runtime script a stable private
directory, and permits all syntax/project/dependency validation before any unit launches.

The new planning order should be:

```text
submitted text
  -> split on top-level segment separators
  -> expand xprompt swarms
  -> expand remaining launch-visible xprompts with proc-aware literal protection
  -> classify and parse each segment as Agent or Proc
  -> resolve typed dependencies and projects
  -> validate the complete mixed plan / render approval preview
  -> dispatch each typed unit
       Agent -> existing provider guard, fan-out, artifacts, agent executor
       Proc  -> durable proc reservation and supervisor admission
```

Provider-disable guards, model resolution, agent-name validation, agent timestamps, and
agent artifact allocation must see only `Agent` units. Slot budgets and approval previews
must see both kinds so a remote or agent-originated launch cannot hide executable proc
work inside an apparently smaller request.

The generic result should likewise be a tagged union (`AgentLaunchResult` or
`ProcLaunchResult`) rather than forcing a proc ID into an agent result record. This will
require versioning the launch request/preview payloads used by ACE and mobile surfaces.

### 3.2 `%proc` is a launch selector, not a normal prompt modifier

Do not add a `proc: bool` plus script fields to `PromptDirectives`. That class describes
modifiers consumed by an agent runner. Instead add a dedicated top-level proc-directive
scanner/parser used by launch classification and literal-zone protection.

The parser should return:

- the complete directive/source block span to remove from launch-control text;
- the script source span, for literal protection and diagnostics;
- the typed `CodeBlockValue`;
- the selected interpreter; and
- precise validation errors with source ranges.

Add `proc` to the Rust editor directive registry so completion, hover, and diagnostics
agree with runtime behavior. The actual classifier and code-fence rules also belong in
`sase-core`: they are domain behavior every CLI, TUI, editor, web frontend, or plugin host
must share. Python should consume the returned spans and wires while continuing to own
xprompt file loading and rendering.

### 3.3 Introduce a real code-block value, but do not publish a nominal input type

Create `CodeBlockValue` and its structured scanner now. Use it for `%proc` and expose it
through the Python/Rust wire boundary. Do not merely add `CODE` to `InputType` while the
invocation parser still treats its value as an ordinary scalar; that would advertise a
contract the parser cannot honor.

A complete future `input: code` slice should:

- add `CODE` to Python `InputType`, loader parsing, binding, show/render models, and tests;
- add it to Rust frontmatter diagnostics, schema enumeration, catalog/mobile projections,
  completion, and hover;
- teach type-directed `#xprompt::` parsing to capture exactly one fenced block;
- bind a JSON-shaped `{source, language}` value into Jinja (`arg.source` and
  `arg.language`), while legacy string interpolation renders `source`; and
- apply the same literal and closed-fence rules as `%proc`.

This preserves the requested general-purpose direction without expanding `%proc` work
into a half-supported public xprompt input surface.

### 3.4 Add durable proc admission before child spawn

Extend the proc request sidecar with a versioned admission request:

```text
admission: {
    wait: WaitSpecWire,
    workspace: {
        project: String,
        project_file: String,
        workflow: "proc:<proc_id>",
    },
    script: {
        language: Option<String>,
        interpreter: "bash" | "python",
        source: String,
        sha256: String,
    },
}
```

The proc row can use its existing active statuses and `phase` field:

| Proc phase | Workspace state |
| --- | --- |
| `waiting` | no claim |
| `acquiring-workspace` | claim protocol in progress |
| `preparing-script` | lease held |
| `running` | lease held by supervisor/child lifecycle |
| `settling` | lease held until the claim checkpoint completes |
| terminal | no claim |

After the existing start barrier opens, the supervisor should:

1. directly poll the generic wait resolver while remaining kill-responsive;
2. acquire an operational lease with its own PID, so no claim transfer is needed;
3. atomically write the settlement policy to the request sidecar and update the proc
   row's `cwd`, project, workspace number, phase, and message;
4. materialize a private script file; and
5. spawn the interpreter in the leased cwd.

Persist the workspace intent before taking the claim and include the proc ID in the lease
workflow. If the supervisor dies in the narrow claim-to-sidecar-write interval, stale
claim reconciliation can then identify the dead PID and proc workflow. The bind helper
should release synchronously on every ordinary exception. Add crash-injection tests at
each boundary; two separate durable stores cannot provide a single filesystem
transaction, so recovery—not an imaginary atomic write—is the guarantee.

Timeout accounting should begin when the child starts, as it does today. Time spent
waiting for a dependency or for workspace admission must not consume the script's
execution timeout. A future admission timeout can be a separate policy.

### 3.5 Generalize wait targets without fabricating agent artifacts

Define a shared wait wire such as:

```text
WaitSpecWire {
    targets: Vec<WaitTargetWire>,
    duration_seconds: Option<f64>,
    until: Option<String>,
}

WaitTargetWire = Agent(identity) | Proc(proc_id) | Bead(project, bead_id)
```

Keep current `%wait` spelling compatible and translate it into this representation.
Agent runners may continue to write `waiting.json` for presentation and lumberjack
coordination. Proc supervisors should store the same logical spec in their request
sidecar, publish `phase="waiting"`, and resolve directly against agent artifact indexes,
the proc store, and bead state. They should not write `ready.json` or create an artifacts
directory.

The dependency resolver should remain pure and shared; each execution kind owns its own
durable presentation and polling adapter. Terminal proc statuses resolve a proc target
regardless of success, matching current agent completion-style dependency behavior;
whether a downstream unit requires upstream success should be a separate future
condition rather than an implicit change to `%wait`.

### 3.6 Materialize scripts instead of putting source in argv

Do not use `bash -c <source>` or `python -c <source>`. Long/multiline source makes argv,
process listings, quoting, fingerprinting, and diagnostics worse.

The supervisor should write the source with mode `0600` beneath its existing private
runtime directory, for example:

```text
~/.sase/procs/runtime/<proc_id>/script.sh
~/.sase/procs/runtime/<proc_id>/script.py
```

Then execute:

```text
[bash, --noprofile, --norc, script.sh]
[sys.executable, script.py]
```

Do not inject `set -euo pipefail`; that silently changes ordinary Bash script semantics.
Users can request strict mode in their script. Store a content hash in the request
fingerprint and use a redacted logical command in the public proc row rather than copying
the full program into argv. The source remains available in the private request/runtime
sidecar for exact execution and diagnostics, subject to normal proc retention.

The existing supervisor environment is the right base: copy SASE's process environment,
scrub agent and chop identity, remove `SASE_ARTIFACTS_DIR`, and add `SASE_PROC_*` values.
For leased procs also add explicit `SASE_PROJECT`, `SASE_PROJECT_FILE`,
`SASE_WORKSPACE_NUM`, and `SASE_WORKSPACE_DIR` values. Python must use `sys.executable`;
that is the reliable way to provide the same installed SASE package and dependencies.
Do not source an activation script or inject SASE objects into script globals.

### 3.7 Presentation and authorization

The Procs pane already observes non-monitor proc rows, and the proc indicator explicitly
distinguishes them from monitor shells. Add the new origin/phase labels there and keep
stand-alone procs out of agent counts, family trees, agent completion notifications, and
provider capacity.

Mixed launch previews must label each unit as `AGENT` or `PROC`. A proc preview should
show its interpreter, exact target project, wait dependencies, and script (plus hash),
without executing any preprocessing or acquiring a workspace. Direct interactive
submission is user-authored execution; remote, mobile, plugin-mediated, or agent-originated
launches must retain the existing launch approval boundary and count proc units against
the request's declared slot limit.

This matters because an xprompt may introduce `%proc` even when the call site does not
spell it. Classification and full expansion must happen before approval, and approval
must show the expanded executable source.

## 4. Lifecycle and failure contract

| Event | Required behavior |
| --- | --- |
| syntax/project/wait validation failure | fail the mixed plan before any spawn or claim |
| waiting | durable proc row exists; supervisor is killable; no workspace is claimed |
| wait target resolves | acquire and prepare one machine-owned workspace |
| allocation/preparation failure | settle proc as error; never use primary checkout |
| script-file or child-spawn failure | settle as error and release the lease |
| exit 0 | settle success, retain log/result, release lease |
| nonzero exit | settle error with exit code, retain log/result, release lease |
| total/idle timeout | terminate process group, settle error, release lease |
| user kill during wait | settle killed; there is no lease to release |
| user kill while running | terminate process group, settle killed, release lease |
| supervisor loss/reboot | reconcile to explicit unknown/error outcome and release/recover any dead-PID lease |
| future workspace handoff | transfer claim atomically to the named consumer; do not also release it |

The existing settlement checkpoints provide the required “exactly once in effect”
cleanup after a workspace policy is bound. The new work is ensuring that every admission
crash boundary either binds that policy or leaves enough persisted intent for stale-lease
reconciliation.

## 5. Alternatives considered

### Implement `%proc` as a special prompt handled by the agent runner

This would create artifacts, names, provider selection, workspace admission, runner-slot
accounting, finalizers, and notifications for something that does not run an LLM. It
would also make agent-family ownership appear mandatory. Rejected.

### Reuse `sase monitor start`

A monitor is a family-attached proc shell with agent-specific metadata and follow-up
semantics. A stand-alone command has no family member to monitor and must not synthesize
one. Rejected.

### Expand `%proc` to `sase proc run -- bash -c ...`

This bypasses typed mixed-plan validation, literal protection, deferred workspace
admission, typed wait dependencies, approval previews, and durable script-source
handling. It also either runs in the caller's cwd or forces a wrapper to reimplement the
lease protocol. Rejected.

### Acquire the operational lease in the launch host, then let the proc wait

This can reuse `submit_via_lease` unchanged, but a long dependency wait monopolizes a
prepared checkout and reduces pool capacity. It also makes killed-before-start cleanup
more complicated than necessary. Rejected for `%proc`; the existing helper remains
correct for callers that intentionally already hold a lease.

### Wait synchronously in the launch host, then submit the proc

The launch call would block, cancellation would depend on the foreground session, there
would be no durable proc identity while waiting, and a mixed swarm could not refer to the
pending unit. Rejected.

### Put source directly in `bash -c` / `python -c`

This exposes programs in argv/process listings, magnifies quoting errors, and gives
multiline source a different execution path from fenced source. Rejected.

### Treat any fence info string as an executable language

This turns Markdown metadata into command discovery, produces platform-dependent
behavior, and greatly enlarges the authorization surface. Reject in v1; use an explicit
interpreter registry if more languages are later justified.

### Add `InputType.CODE` without changing xprompt invocation parsing

This would be a renamed string type, not a code-block type, and would drift across Python
loaders, Rust diagnostics, editor completion, and mobile catalogs. Rejected. Build the
value and scanner now; expose the public input type only as a complete vertical slice.

## 6. Suggested implementation slices

1. **Core syntax and wires.** Add `CodeBlockValue`, structured fence/proc span scanning,
   proc directive diagnostics/editor metadata, `WaitTargetWire`, and generic mixed
   `LaunchPlanWire` in `sase-core`; expose typed Python adapters and parity tests.
2. **Literal and surface parsing.** Add single-line proc payloads to literal-zone
   protection, parse the three parenthesized forms and fenced `::` form, enforce the
   directive allowlist, and add editor/highlighter/completion support.
3. **Mixed launch planning.** Expand swarms and remaining launch-visible xprompts, then
   classify; preallocate proc IDs, generalize bare `%wait`, version launch
   preview/request/result payloads, exclude proc units from provider/name/fan-out
   planning, and validate the complete plan before dispatch.
4. **Proc admission and scripts.** Add the versioned admission sidecar, generic proc wait
   adapter, supervisor-owned just-in-time operational lease acquisition, row/sidecar
   binding, private script materialization, Bash/Python argv, environment attribution,
   and settlement integration.
5. **Presentation and recovery.** Render phases and mixed previews, add typed proc wait
   completion to agent waiters, cover kill/reconciliation/crash boundaries, document
   ephemeral workspace output, and update the Proc Shell/Sase Shell glossary definitions
   with explicit user approval through the normal memory workflow.
6. **Future code input.** Only after `%proc` proves the primitive, add a complete
   `input: code` frontmatter/binding/editor/mobile slice using the same value and scanner.

Because `%proc` is user-reaching behavior before the complete path is ready, the
implementation should be developed behind a disabled SASE feature flag created through
the project's normal flag workflow. The parser may recognize the syntax for diagnostics
while execution remains unavailable until admission, cleanup, and approval behavior are
complete.

## 7. Verification matrix

### Parser and literal behavior

- each accepted single-line form and every mutual-exclusion/arity failure;
- quoted strings containing `#xprompt`, `%directive`, `%{alt}`, `$(command)`, `@path`,
  `{{ jinja }}`, `---`, commas, parentheses, escapes, and newlines;
- backtick and tilde fences, longer fences, indentation, CRLF, blank lines before the
  fence, missing close, empty body, absent language, valid languages, and invalid info;
- `%proc` text inside an ordinary fence/inline-code/disabled region remains inert;
- a fence containing `---` remains one swarm segment;
- an xprompt expansion that introduces a proc is rescanned and classified; and
- proc script bytes round-trip unchanged from parse through the runtime file.

### Mixed planning and directives

- agent-only, proc-only, and alternating mixed swarms;
- embedded and top-level xprompt swarm expansion metadata remains attached;
- all unit validation happens before the first spawn;
- provider guards and model/name allocation see only agent units;
- explicit agent/proc/bead/time waits and bare previous-unit waits in both directions;
- agent-only directives fail precisely on proc units; and
- previews show type, source, interpreter, dependency, project, and stable proc ID.

### Workspace and lifecycle

- no workspace is claimed while a proc is waiting;
- acquisition uses only machine-owned workspaces and never falls back to primary;
- cwd/project/workspace/env attribution matches the acquired lease;
- success, nonzero exit, signal, kill during wait, kill during run, total timeout, idle
  timeout, script-write failure, spawn failure, and preparation failure all settle;
- the lease is released exactly once for every terminal outcome;
- crash injection before claim, after claim, after policy bind, after child exit, and at
  every settlement checkpoint leaves no permanent live claim; and
- released checkout changes are treated as ephemeral unless an explicit handoff exists.

### Interpreter environment

- Bash receives exact source and ordinary Bash semantics without an implicit strict mode;
- Python's executable equals the launching SASE `sys.executable`;
- Python can import the installed `sase` package;
- agent/chop/artifacts identity is scrubbed; and
- proc/project/workspace environment variables are correct.

## Sources

SASE repository evidence:

- `src/sase/agent/launch_cwd_agents.py`
- `src/sase/agent/xprompt_swarm.py`
- `src/sase/agent/multi_prompt.py`
- `src/sase/agent/multi_prompt_launch_plan.py`
- `src/sase/agent/multi_prompt_launch_execution.py`
- `src/sase/agent/multi_prompt_reference_directives.py`
- `src/sase/agent/launch_guard.py`, `launch_request_planning.py`, and
  `launch_preview.py`
- `src/sase/xprompt/_directive_types.py`, `_directive_collect.py`,
  `_directive_extract.py`, and `_directive_shorthand.py`
- `src/sase/xprompt/_fenced_blocks.py`, `_literal_zones.py`, `processor.py`,
  `_jinja.py`, `models.py`, `input_binding.py`, and `loader_parsing.py`
- `src/sase/llm_provider/preprocessing.py`
- `src/sase/axe/run_agent_wait.py` and `run_agent_wait_deps.py`
- `src/sase/core/wait_dependency_resolution/`
- `src/sase/procs/models.py`, `request.py`, `service.py`, `supervisor.py`,
  `settlement.py`, `runner.py`, `runtime.py`, and `names.py`
- `src/sase/workspace_provider/lease.py`
- `src/sase/ace/tui/_proc_observer_models.py` and
  `src/sase/ace/tui/models/agent_nodes.py`

`sase-core` repository evidence:

- `crates/sase_core/src/agent_launch/mod.rs`
- `crates/sase_core/src/procs/wire.rs` and `procs/store.rs`
- `crates/sase_core/src/workspace_lease.rs`
- `crates/sase_core/src/editor/directive.rs` and `editor/frontmatter.rs`
- `crates/sase_core/src/xprompt_catalog.rs`
- `crates/sase_core/src/prompt_literals.rs`

## Recommended solution

Implement `%proc` as a **typed stand-alone proc launch unit with supervisor-owned,
just-in-time workspace admission**.

- Parse the three strict parenthesized forms and the line-oriented fenced `::` form into
  a reusable `{source, language}` code-block value; default an omitted language to Bash
  only at the `%proc` consumer.
- Treat all proc source spans as literal through every xprompt and prompt-processing
  pass. Accept only Bash and Python in v1 and reject ambiguous arguments, residual prose,
  unsupported languages, and agent-only directives.
- Add a generic mixed `LaunchPlanWire` above the existing agent fan-out planner. Expand
  xprompt swarms and remaining launch-visible references first, classify every segment,
  preallocate proc IDs, resolve bare `%wait` to typed previous-unit dependencies,
  validate the whole batch, and show proc scripts and projects in approval previews.
- Reuse the durable proc row, detached supervisor, logs, kill/timeouts, reconciliation,
  and settlement checkpoints. Do not create an agent, monitor, fake artifacts directory,
  or family-qualified shell name; the proc ID is the stand-alone identity and the Procs
  pane is its presentation surface.
- Persist `%wait` and project intent in a versioned proc admission sidecar. Wait without a
  workspace, then acquire an operational lease under the supervisor PID, durably bind
  its settlement policy, execute in the leased checkout, and release on every terminal
  outcome. Add `%wait(proc=...)`; support agent, proc, bead, duration, and absolute-time
  targets, while rejecting runner-slot priority/threshold controls for procs.
- Materialize mode-`0600` script files in the proc runtime directory. Execute Bash
  without implicit strict mode and Python with SASE's `sys.executable`; inherit SASE's
  sanitized environment and add explicit proc/project/workspace attribution.
- Build the shared scanner, code-block value, launch classification, editor contract,
  and wait wires in `sase-core`; keep project discovery, filesystem leasing, script
  materialization, and subprocess supervision in Python. Expose `input: code` later only
  as a complete type-directed xprompt slice using the same primitive.

This design makes proc shells genuinely stand-alone, keeps waiting cheap, preserves
workspace safety and crash cleanup, and extends xprompt swarms without weakening the
agent/proc boundary.
