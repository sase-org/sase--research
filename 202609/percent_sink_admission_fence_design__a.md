# `%sink` as a durable admission fence

## Research scope

This report independently evaluates how to add a `%sink` prompt directive to SASE. The
requested intuition is “`%wait`, but with the edge reversed”: selected agents or
stand-alone procs should wait for the agent or proc whose prompt contains `%sink`.
Selection must cover all currently waiting agents, an agent hood, exact SASE Agent
names, and optionally future matching launches. A target that has already begun running
must never be stopped or made to wait retroactively.

The investigation used these repository revisions:

- `sase`: `53ba46064937d53c3c3c9902542aadf5fe3831bb`
- `sase-core`: `7e56423b74107c418845d9681d13b10ff72317cf`

The main paths inspected were the Python prompt parser and legacy runner, the Rust typed
launch planner and admission state machine, proc submission, wait resolution, agent
status bucketing, TUI completion, and the xprompt LSP completion contract.

## Executive conclusion

The sound implementation is not to edit the selected targets' prompts or their existing
`waiting.json` dependency lists. `%sink` should register a host-local, durable admission
fence in `sase-core`. That fence creates reverse completion edges:

```text
ordinary %wait:  launching unit  ----waits for----> dependency
%sink:           selected target ----waits for----> sink source
```

The fence must be consulted atomically at the last transition from a pre-run state to a
running/dispatching state. That is the only design that can uphold the key invariant:

> Whichever happens first wins. If the sink is registered first, a matching pre-run
> target is blocked. If the target commits its running transition first, the sink does
> not affect it.

This requires a small global constraint journal and lock, immutable completion
identities for both agents and procs, cycle detection, and an admission check shared by
the agent and proc launch paths. Completion metadata should remain defined once in the
Rust editor contract so the prompt widget and external LSP clients stay in parity.

I also recommend one explicit extension to the proposal: `drain=true`. `%sink` by itself
cannot make a stand-alone proc wait until *no matching agents are running*, because the
requirements correctly prohibit affecting already-running agents. With `drain=true`,
existing running matches remain untouched but become prerequisites of the sink source;
pre-run and future matches wait on the source. This creates a race-free maintenance
window without ever pausing or killing a running target.

## What the current implementation implies

### `%wait` is split across two launch architectures

The legacy Python runner parses `%wait` into prompt directives and calls
`wait_for_dependencies` before it enters the runner-slot queue. In
`src/sase/axe/run_agent_runner.py`, dependency waiting occurs around lines 110–130,
while runner-slot admission occurs later around lines 173–194. The transition that
records the run start is a callback of the slot queue.

This ordering matters. A `QUEUED` agent has already passed its dependency phase. Merely
adding the sink source to that agent's `waiting.json` would not make the queue loop go
back and wait on the new dependency. Existing TUI code in
`src/sase/ace/tui/actions/agents/_directive_persistence.py` can atomically rewrite a
waiting marker, but that marker is not an admission authority once the runner has moved
to slot waiting. The TUI's separate edit/relaunch behavior in `_wait_actions.py` is more
evidence that dependency mutation is not a general cross-state mechanism.

The newer typed path is closer to the right substrate. In
`crates/sase_core/src/agent_launch/mod.rs`, a `LaunchPlanWire` contains agent and proc
units with `WaitTargetWire` edges. `admission.rs` journals phases such as Reserved,
Waiting, Checking, Eligible, Dispatching, and Launched. Python's
`launch_admission_runtime.py` resolves external waits and asks the Rust state machine
for the next action.

However, the typed journal is scoped to one submitted launch plan. A future `%sink`
match can arrive from another prompt, so per-plan state alone cannot enforce the new
cross-launch relationship.

### A logical proc dependency currently means “submitted,” not “finished”

The typed planner rewrites same-plan agent and proc names to logical wait targets.
`resolved_wait_outcome` in `agent_launch/admission.rs` treats a logical target as
resolved once that unit has an outcome. A proc unit gets a Launched outcome after its
supervisor submission succeeds. It does not wait for the process to reach a terminal
proc status.

External proc waits are different: Python's `_resolve_proc_wait` polls the proc record
until terminal state. Thus the current `Logical` edge and an external `Proc` edge do not
have equivalent completion semantics. `%sink` must not inherit this ambiguity. All
reverse edges should be explicit terminal-completion edges. Ideally the same work should
make ordinary same-plan proc waits terminal-completion edges as well, or distinguish
`started` and `completed` edge satisfaction in the wire type.

### Waiting procs do not yet have durable identities

`src/sase/agent/launch_proc_runtime.py` allocates a new proc ID only immediately before
supervisor dispatch. A typed `ProcUnit` waiting in admission has only a logical unit ID;
it is not yet a durable proc visible to other launches. This prevents robust cross-plan
selection of a waiting stand-alone proc and makes “future procs” impossible to attach to
by stable identity.

The implementation should reserve a completion identity before dependency admission.
This can be a preallocated proc record in a pending state or a generalized launch-node
completion handle that is later bound to the supervisor proc. Reusing mutable display
names is unsafe because names can be recycled after completion.

### `WAITING` and `QUEUED` are presentation buckets, not one wait mechanism

`src/sase/agent/status_buckets.py` classifies `WAITING` and `QUEUED` as pre-run wait
statuses. The distinction is useful in the UI but exposes two different physical wait
points. `%sink` therefore needs to target a semantic property—“has not crossed the run
boundary”—rather than injecting itself into either legacy wait representation.

### Completion already has a shared contract, but lacks two needed roles

`crates/sase_core/src/editor/directive.rs` defines directive metadata shared by ACE and
the xprompt LSP. `%wait` currently offers `agent`, `bead`, `proc`, `time`, and `unit`
keywords. `agent` has a catalog-backed value role, but `proc` and `unit` are free text.
The Rust completion engine and LSP host catalog know agent/group roles; they do not yet
have first-class Hood and Proc roles.

ACE already derives proc completion candidates with an immutable proc ID plus friendly
shell aliases in `_agent_completion_candidates.py`. That is a good interaction model:
show a useful label, but insert and persist the immutable ID. The current wait completion
code explicitly omits proc rows for ordinary positional values, so `%sink` should get a
purpose-built selector schema rather than copying that behavior.

## Critique of the proposal

The reverse-wait concept is useful, but it is more powerful and more global than its
simple description suggests.

First, `%sink` is not merely prompt syntax. A normal wait declares a dependency owned by
the launching unit. A sink reaches into other launches, including launches submitted
later. That makes it a scheduler/admission constraint with lifecycle, concurrency,
auditing, crash recovery, and cycle concerns.

Second, “launched after this agent” is ambiguous. It might mean prompt submission,
process spawn, transition to RUNNING, or time order as perceived in the UI. I recommend
defining it as **registered after the sink rule's monotonically ordered registration**.
That moment is controllable under a lock. Wall-clock comparisons are not.

Third, the motivating maintenance-proc example needs stronger semantics than the base
proposal provides. Suppose agent A is already running and a stand-alone proc P declares
`%sink(all=agents, future=true)`. The rule must not affect A, so P may run concurrently
with A. If P is supposed to run only after all agents finish, the base directive is
insufficient. This is why an explicit drain mode is objectively beneficial.

Fourth, a broad future sink can accidentally stall an entire host. The syntax and UI
should make scope and lifetime conspicuous, report how many targets were captured, and
avoid a terse alias initially. A typo in an exact selector must not silently turn a
one-time rule into a no-op.

Finally, selector names and dependency identities are different things. Names and hoods
are appropriate query inputs; immutable agent-family generations and proc IDs are the
only safe persisted edge endpoints.

## Recommended directive contract

Use a repeatable parenthesized directive:

```text
%sink(builder, reviewer)
%sink(hood=research)
%sink(all=agents, scope=host)
%sink(proc=proc-01K..., future=true)
%sink(all=both, scope=host, future=true, drain=true)
```

Recommended fields:

| Input | Meaning |
|---|---|
| positional value | Exact SASE Agent name |
| `hood=<name>` | Agent name equal to the hood or beneath `hood.` |
| `proc=<id-or-label>` | Exact stand-alone proc, resolved immediately to an immutable proc ID |
| `all=agents\|procs\|both` | Select every matching pre-run entity of the requested kind |
| `scope=project\|host` | Search current project by default; opt in to the local host |
| `future=true\|false` | Also match entities registered after the rule; default `false` |
| `drain=true\|false` | Wait for existing running matches before starting the source; default `false` |

Selectors are unioned. At least one positional, `hood`, `proc`, or `all` selector is
required. Repeating `%sink` adds selectors. Scalar options must either appear once or
repeat with identical values; conflicting scalar values are an error.

I do not recommend glob or regular-expression selectors in the first version. Hood
membership is sufficient for hierarchy and must use a component boundary:
`name == hood || name.startswith(hood + ".")`. A hood selector applies only to agents,
not procs.

I also do not recommend a `%s` short alias initially. Broad, persistent scheduling
effects benefit from being visible in prompts and review surfaces.

### Exact semantics

1. The directive source is the whole SASE Agent generation when used in an agent
   prompt, not merely its current shell. Handoffs and family continuation should not
   release the targets prematurely. In a `%proc` prompt, the source is that proc's
   terminal completion.
2. At rule registration, capture matching entities that are durably in a pre-run state.
   This includes dependency-WAITING, resource-QUEUED, and typed units in Waiting. Exclude
   entities that have atomically crossed the run/dispatch boundary.
3. Every captured target gains a terminal-completion blocker on the sink source.
4. If `future=true`, every later registered target matching the saved selector gains the
   same blocker before it can run.
5. The source releases targets on every terminal outcome: success, failure, killed,
   skipped, lost, or reconciled orphan. The outcome is retained for display and audit;
   `%sink` is ordering, not success gating.
6. Multiple matching sink rules accumulate; the target waits for all distinct source
   completion references.
7. The source is always excluded from its own target selection.
8. A finished source causes its future rule to expire. Entities registered afterward do
   not need a vacuous blocker, though the journal retains the rule and terminal outcome
   for audit.

For `drain=true`, add one complementary operation at registration:

- Current matching running entities become prerequisites of the source.
- They continue running unchanged.
- Current pre-run and later matching entities wait for the source as above.

The resulting cut is:

```text
already running matches  ---> sink source ---> queued/future matches
```

This is the behavior needed for a command that must run after existing work drains but
before queued or newly submitted work begins. It should remain opt-in because it delays
the sink source and creates additional cycle opportunities.

## Recommended architecture

### 1. Make the Rust core authoritative

Add wire types along these lines (names illustrative):

```rust
struct SinkSpecWire {
    selectors: Vec<SinkSelectorWire>,
    scope: SinkScopeWire,
    include_future: bool,
    drain_running: bool,
}

enum SinkSelectorWire {
    AgentName(String),
    AgentHood(String),
    Proc(ProcSelectorWire),
    All(EntityKindSetWire),
}

enum CompletionRefWire {
    AgentGeneration { project: String, artifact_id: String },
    Proc { project: String, proc_id: String },
}
```

Names select; `CompletionRefWire` blocks. The existing wait resolver's ability to bind
an agent to project/timestamp/artifact identity is a useful precedent.

The sink spec belongs on each `LaunchUnitWire`. It must participate in plan digesting,
approval previews, journal serialization, diagnostics, and schema versioning. `%sink`
must also make `has_typed_launch_directive` true so no prompt carrying it falls through
to the legacy runner-only path. Python can recognize the name for compatibility, but it
must not independently implement the scheduling rule.

Allow `%sink` on ordinary agent units and `%proc` units. Initially reject it in remote
`%dispatch` V1, just as that protocol rejects other unsupported launch-graph features.
A host-local rule cannot safely claim to fence a remote scheduler.

### 2. Add a host-local constraint journal

Create a durable journal under SASE host state with one lock and monotonically ordered
events. It needs to record:

- completion-node reservation and entity kind/project;
- sink-rule registration and selector snapshot;
- materialized target-to-source blockers;
- source and target admission-boundary transitions;
- terminal outcomes, expiration, cancellation, and reconciliation.

The rule store must be host-global even when a rule's selector scope is one project.
Per-plan journals cannot see later launches. Use append/update semantics and atomic file
replacement consistent with existing SASE state practices; do not use prompt text or
`waiting.json` as the source of truth.

The decisive operation is a compare-and-transition under this lock:

```text
register sink rule / materialize blockers
                  versus
check blockers / commit target as running
```

This linearization point supplies the requested guarantee without attempting to freeze
an already-running process. It also makes future matching deterministic.

The journal needs startup reconciliation. A source that disappeared after registration
must eventually receive a terminal Lost/Orphaned result and release its targets. A
stale live rule must never block launches forever merely because a process crashed
between status writes.

### 3. Unify completion semantics

Do not encode sink edges as today's same-plan `Logical` waits, because those resolve at
launch outcome. Introduce a terminal completion edge or add an explicit satisfaction
mode such as `Terminal` versus `Launched`. Both agent and proc endpoints must settle the
same way whether they are in the same plan or another plan.

Reserve completion identity early:

- Reserve an agent generation/artifact identity before dependency waiting.
- Reserve a proc ID or generalized completion node before typed admission, not at
  supervisor dispatch.
- Expose pending procs to selector/completion inventories.
- Have the supervisor settlement path publish proc terminal outcome to the journal.

### 4. Enforce at both final admission boundaries

For agents, insert the shared constraint check immediately before the operation that
records `run_started_at` and consumes a runner slot. A target blocked after reaching the
slot queue returns to a scheduler-visible waiting state without holding the scarce
runner resource.

For procs, check immediately before supervisor dispatch. A blocked proc consumes no LLM
runner slot and should not spawn a supervisor process. It remains a durable pending proc
so it can itself be selected or cancelled.

Status projection may continue to show WAITING/QUEUED, ideally with a reason such as
“sink: research.2” and the immutable source reference. Internally, admission blockers
must be composable with ordinary waits and capacity constraints rather than rewriting
one into another.

### 5. Detect cycles before committing rules

A reverse edge can immediately create a cycle—for example, source A already waits for B
and `%sink(B)` would make B wait for A. `drain=true` can create similar cycles with a
running prerequisite. Under the same constraint lock, build the completion graph from
ordinary terminal waits, materialized sink blockers, and proposed drain prerequisites.
Reject a rule that introduces a cycle and return a diagnostic showing the shortest
useful path.

Future matching also needs cycle handling. When a later entity registers, materialize
all matching future rules as one transaction, check the combined graph, and reject or
hold that launch with an actionable condition error. Do not silently discard one edge.

### 6. Extend one completion contract for ACE and LSP

In the Rust editor directive metadata, add `%sink` arguments and first-class
`DirectiveValueRole::Hood` and `DirectiveValueRole::Proc`. Extend the host catalog
protocol to include:

- exact agent name, hood path, project, immutable generation reference, and state;
- proc ID, friendly shell/name aliases, project, and state;
- whether an entity is pre-run, running, or terminal.

Use the full host inventory for sink completion, subject to `scope`, rather than only
the rows currently visible in ACE. Both ACE and the LSP should consume the same metadata
and catalog schema. Display aliases are fine; insertion should prefer exact agent names,
hood names, and immutable proc IDs.

The editor should show a concise live summary for broad forms, for example:

```text
all=both, scope=host, future=true
captures 4 waiting + 2 queued; skips 3 running; remains active until source completes
```

This preview is especially important for `future=true` and `drain=true`. An unmatched
exact selector with `future=false` should be an error. With `future=true`, zero current
matches is valid but should be stated explicitly.

## Delivery sequence

1. **Core model and parser.** Add sink syntax, selector validation, completion roles,
   wire types, digests, and approval summaries in `sase-core`. Route any sink prompt
   through typed launch.
2. **Constraint service.** Implement the durable host journal, lock, immutable refs,
   selector materialization, cycle checks, terminal release, expiration, and crash
   reconciliation.
3. **Agent integration.** Register agent completion nodes early and put the constraint
   check at the final pre-run boundary. Project blocker reasons into statuses and
   cancellation paths.
4. **Proc integration.** Reserve proc completion identity before admission, make pending
   procs discoverable, check the fence before dispatch, and publish actual terminal
   settlement. Fix or explicitly separate same-plan logical-launch waits from terminal
   completion waits.
5. **ACE and LSP.** Extend the shared editor contract and catalog helper, add exact/hood/
   proc/all completion, previews, and parity tests.
6. **Operational hardening.** Add journal inspection, stale-rule reconciliation,
   cancellation behavior, and concise diagnostics before enabling host-wide future
   fences by default.

The feature can initially live under the existing typed-launch rollout boundary; a
second independent implementation flag would add more state combinations without
reducing the core risk.

## Verification matrix

At minimum, tests should cover:

- all four source/target combinations: agent→agent, agent→proc, proc→agent, proc→proc;
- dependency-WAITING, capacity-QUEUED, typed Waiting, and pending proc targets;
- STARTING/RUNNING targets being excluded and never interrupted;
- a sink-registration versus run-transition race in both lock orderings;
- exact name, hood boundary, proc ID, all-agents, all-procs, and both selectors;
- current-project default and explicit host scope;
- future targets registered before and after source terminal completion;
- `drain=true` with running work, queued work, and continuous new submissions;
- source success, failure, kill, skip, loss, cancellation, and process crash recovery;
- multiple sinks on one target and deduplication of the same immutable source;
- direct and future-induced cycle rejection;
- SASE Agent family/handoff completion, name reuse, and immutable binding;
- no runner slot or proc supervisor held while a sink blocker is unresolved;
- ACE/LSP argument and candidate parity, including pending proc completion;
- clear rejection of unsupported remote dispatch.

Property-based state-machine tests are worthwhile here. The central safety property is:
no entity with a run-boundary sequence lower than a sink rule is retroactively blocked,
and every matching entity with a registration sequence higher than an active future
rule receives its blocker before crossing that boundary.

## Recommended solution

Implement `%sink` as declarative syntax over a durable, host-local completion graph in
the Rust core. Persist selector rules globally, resolve current matches to immutable
agent-generation or proc references, and atomically consult those rules at the final
agent/proc run boundary. Route every sink prompt through typed admission, give pending
procs early completion identities, use terminal rather than launch acknowledgement as
the edge condition, and reject dependency cycles.

Expose exact agent, hood, proc, and `all=agents|procs|both` selectors through the shared
Rust completion metadata so ACE and LSP clients remain identical. Default selection to
the current project, require explicit `scope=host`, and make future matching opt-in.

Finally, add the explicitly named `drain=true` mode. It is the cleanest way to satisfy
the important stand-alone maintenance-proc scenario while preserving the non-negotiable
rule that already-running agents and procs are never paused, stopped, or made to wait.
