---
create_time: 2026-07-16
updated_time: 2026-07-16
status: research
---

# Unifying Agent Families with Xprompt Swarms

## Executive conclusion

The initiative is feasible, but it is larger than making family children parallel and allowing Bash/Python rows at the
top level. Those two changes expose the real architectural issue: SASE currently uses the same fields and naming
conventions for several different concepts.

Today a plan-chain "family" can mean all of the following at once:

- a visual fold under one Agents-tab row;
- a `--`-delimited naming namespace;
- a parent/child process relationship;
- an implicit success dependency;
- a shared workspace handoff;
- a lifecycle state machine with plan/question gates;
- a completion, wait, dismissal, revert, and output-aggregation scope.

Those meanings happen to align for the mostly serial standard plan chain. They stop aligning as soon as two family
members run concurrently, a command is the first visible row, dependencies form a DAG, or a family is defined by a
reusable Markdown swarm.

The most important prerequisite is therefore to separate **group membership**, **display hierarchy**, **execution
dependencies**, **workspace/resource ownership**, and **lifecycle control** in the persisted model. An agent family can
then become what the user should conceptualize it as: one kind of run group on the Agents tab. The standard plan chain
would be a group with an optional lifecycle controller, not the definition of what all groups are.

For the xprompt goal, the strongest design is not to grow a second workflow executor out of `%` directives. Compile
both YAML workflows and executable Markdown swarms into one normalized run-graph representation. Markdown can become
the preferred authoring surface for the common agent/command DAG, while YAML remains a compatibility syntax and, at
least initially, a reasonable home for the less-Markdown-like constructs that do not migrate cleanly.

## Scope and evidence

This report was checked against the current implementation and documentation on 2026-07-16, especially:

- family attachment and naming: `src/sase/agent/_family_attach_*.py`, `src/sase/axe/run_agent_directives.py`,
  `src/sase/plan_chain.py`;
- family lifecycle evaluation: `src/sase/agent_family/`, `src/sase/axe/run_agent_exec_*.py`;
- swarm planning and launch: `src/sase/agent/xprompt_swarm.py`, `src/sase/agent/multi_prompt_launcher.py`,
  `src/sase/agent/launch_executor.py`;
- workflow capabilities: `src/sase/xprompt/workflow_*.py`, `docs/workflow_spec.md`;
- Agents-tab row and child models: `src/sase/ace/tui/models/agent.py`, `_agent_ordering.py`, `_agent_status_family.py`,
  and `agent_groups/`;
- wait, capacity, and action scopes: `src/sase/core/wait_dependency_resolution/`,
  `src/sase/core/runner_slots/_admission.py`, and `src/sase/core/agent_cleanup_facade.py`;
- prior research in `sase--research`, particularly the June family/workflow report, the July v1/v2 family design, and
  the standalone-xprompt analysis.

One prior decision is explicitly superseded by this initiative. The 2026-07-05 family design declared root
Bash/Python rows a non-goal. Making them roots now is not a small omitted v1 item; it changes the execution, resource,
security, artifact, and action models discussed below.

## The conceptual model to aim for

The product vocabulary becomes much easier if a run is modeled along five independent axes:

| Concept | Meaning | Examples |
| --- | --- | --- |
| Run group | Rows that belong to one user-recognizable unit | a research swarm, plan chain, verification pipeline |
| Node | One executable or interactive member | agent, Bash, Python, human gate, synthetic summary |
| Dependency edge | When a node may run | after success, after any terminal result, conditional |
| Display relation | Where a node is folded/rendered | under group root, under a phase, flattened |
| Controller | Who may add or transition nodes dynamically | none, static DAG scheduler, standard plan-chain evaluator |

This gives a useful definition:

> An agent family is a run group whose members usually have named roles and which may have a lifecycle controller.

That definition makes plan families, parallel reviewer families, and Markdown swarms visually coherent without
pretending they have identical execution semantics.

A minimal normalized record would need concepts resembling these (names are illustrative):

| Record | Important fields |
| --- | --- |
| `RunGroup` | invocation id, display name, definition id/hash/snapshot, controller kind, aggregate policy |
| `RunNode` | group id, group-scoped node id, node kind, role, display-parent id, concrete artifact identity |
| `RunEdge` | upstream/downstream ids, trigger (`success`, `terminal`, expression), failure/skip policy |
| `ResourcePolicy` | workspace mode, runner-slot class, concurrency budget, environment scope |
| `GroupState` | scheduled/active/terminal nodes, gate state, outputs, final outcome, dynamic expansion state |

The existing names and fields can remain compatibility projections. For example, `foo--tester` can still be a useful
display/public name, but it should not be the authoritative proof that the row belongs to group `foo`.

ACE's dotted-name hoods and its project/ChangeSpec/name-root banners should remain view and navigation groupings, not
silently become execution groups. They can render the same rows through different lenses, while explicit run-group
membership answers lifecycle questions such as completion, cancellation, and output aggregation. Treating every shared
name prefix as an execution family would recreate the same name-inference problem under a different delimiter.

## Requirements that are easy to miss

### 1. Family membership and waiting must become separate operations

The proposed `wait=<bool>` keyword on `%name` is useful backward-compatible syntax, but it should compile into two
independent facts:

1. attach this node to a group;
2. optionally create a dependency on the named parent.

Currently `%n(parent, suffix)` automatically adds both a name-derived family relationship and an exact identity wait
when the parent is running. It also records the parent's timestamp as the child's UI parent. A Boolean can disable the
implicit edge, but it cannot express the workflow cases SASE already supports:

- wait only on success;
- run after either success or failure (`finally` cleanup);
- run only on failure;
- wait for two or more upstream nodes;
- skip or cancel rather than wait forever after an upstream failure;
- branch on a typed upstream output.

Recommendation: retain `wait=true|false` as ergonomic sugar on family attachment, but make explicit edges the durable
model. Do not make the `%name` parser the general workflow scheduler.

### 2. `parent_timestamp` is too overloaded for parallel or non-tree families

`parent_timestamp` currently affects UI folding, family root detection, wait aggregation, child capacity exemption,
cleanup cascading, listing visibility, output attribution, and workspace handoff. The wait index generally recognizes a
family generation as one root plus children whose `parent_timestamp` points directly to that root.

That representation cannot safely describe all of these at once:

- a flat visual family with dependencies between siblings;
- a diamond dependency graph;
- a child attached to a prior child but displayed under the group root;
- an independent parallel member that must count against capacity;
- a synthetic group container with no process;
- a family that spans multiple dynamic plan/question rounds.

Persist separate `group_id`, `display_parent_id`, and dependency-edge fields. Keep `parent_timestamp` as a legacy/direct
process-link projection until old consumers have migrated.

### 3. A reusable swarm needs group-scoped node identities

The current Markdown examples use globally stable names such as `%name:plan` and `%name:code`. A second concurrent
invocation collides with the first. Auto/template names do not solve the whole problem because same-batch family
attachment currently resolves only earlier static names, and an in-batch attached child is deliberately not eligible to
be another in-batch parent.

A robust swarm definition needs two identity levels:

- an automatically unique invocation/group id;
- stable, group-scoped node ids such as `update`, `verify`, and `review`.

Dependencies and templates should normally use local ids. Public agent names can then be derived (for example,
`<invocation>--verify`) without authors hard-coding globally unique names. Manual `%n(existing, reviewer)` can remain
the user-facing way to extend an already-running group.

### 4. A concrete root process cannot also be the group container

The present family root row is both a real run and the visual/aggregate container. Status is mirrored from planner,
question, and coder children onto it. With parallel members, the concrete root may finish while siblings continue; with
a Bash root it may finish in seconds while agents run for hours; with a failing root, cleanup nodes may still be active.

The durable model should have a group lifetime independent of any one process. ACE may still render the first concrete
node as the apparent root to preserve the compact current UI, but group status and completion should come from a group
record/aggregate, not by overwriting that node's own outcome.

This also answers what “Python/Bash as a root row” should mean: the command can be the first visible member, while an
underlying synthetic group record owns scheduling and aggregate state.

### 5. Parallel family members need a workspace policy

This is the most important operational consequence of `wait=false`.

A child of a running parent currently inherits the parent's exact workspace safely only because it is deferred until
the parent succeeds. If that child starts immediately, two processes can edit, install, checkout, stash, or commit in
the same checkout concurrently.

The system needs an explicit policy for at least:

- shared workspace versus isolated workspace per node;
- read-only/review nodes versus writing nodes;
- which snapshot/commit an isolated node starts from;
- how results from parallel writers are merged or handed to a convergence node;
- whether a setup command mutates one node's environment, every later node's environment, or a group-owned shared
  environment;
- release/cleanup ownership when several nodes refer to one ChangeSpec.

The motivating “update SASE, then verify it” case makes this concrete. Running `just install` in one workspace or
virtual environment is ineffective if the verifier launches in another isolated workspace. Conversely, forcing both
into one mutable workspace is unsafe if they are parallel. The definition must be able to state the intended scope.

### 6. Parallel family children currently bypass the global runner limit

Runner-slot admission defines a countable root as an active `ace-run` record without `parent_timestamp`; tests
explicitly guarantee child exemption. A `wait=false` family member that still carries parent metadata would therefore
run immediately without consuming a normal root slot.

Capacity must be modeled independently from display/group membership. At minimum define:

- which node kinds consume LLM runner slots;
- whether parallel family agents count globally (recommended: yes by default);
- whether groups have their own concurrency cap;
- whether Bash/Python nodes use a separate command pool or no cap;
- how queued group members are ordered relative to unrelated roots.

Without this, a large swarm can unintentionally bypass `max_running_agents` simply by calling every member a child.

### 7. Static fan-out is not a workflow scheduler

An xprompt swarm currently expands all Markdown segments and dispatches them up front. `%wait` can park a downstream
agent, and `agents[...]` variables can be rendered once its dependency succeeds. That is enough for a static agent DAG,
but YAML workflows additionally render each step against accumulated state and can decide at runtime whether or how
many nodes exist.

Full workflow parity requires a durable scheduler (a persistent process is not necessarily required, but durable host
state is). It must be able to:

- release nodes only after their edge conditions are known;
- create loop iterations or dynamic fan-out;
- mark unreachable/downstream nodes skipped or cancelled;
- survive SASE/ACE restarts and definition edits;
- keep running cleanup after ordinary failure;
- know when no more dynamic nodes can be added and the group is terminal.

Pre-launching everything as indefinite `%wait` rows is not sufficient: success-only waits deliberately do not resolve
after failure, conditionals may not be decidable until typed output exists, and loops do not have a known node count at
launch time.

### 8. Failure semantics must be designed before happy-path sequencing

YAML has fail-fast sequence/parallel behavior, per-loop `on_error`, HITL rejection, and `finally` steps. Ordinary swarm
waits are success barriers: a failed producer can leave dependents parked until a newer successful run with the same
name appears.

A grouped workflow needs deterministic answers to:

- Does an upstream failure fail the group immediately or only after cleanup?
- Are downstream nodes cancelled, skipped, left pending, or offered for manual override?
- Does “wait for group” require every required node to succeed, or just a designated terminal node?
- How do optional, skipped, and user-rejected nodes affect the aggregate outcome?
- Can a failed node be retried in place, and which descendants become stale?
- Does killing the visible root kill all active siblings and queued descendants?

These policies must be persisted so CLI, ACE, mobile, wait resolution, and revival agree.

### 9. Bash/Python roots need first-class node artifacts and actions

Allowing command roots is more than displaying `[bash]` or `[python]`. A root command needs the same lifecycle-quality
record as an agent:

- start/stop/outcome, PID/process-group, stdout/stderr, traceback/error;
- prompt/source snapshot and definition provenance;
- typed output and artifact files;
- workspace and environment identity;
- retry, kill, dismiss, revive, mark, and reproduction behavior;
- notification and unread semantics;
- resource/capacity classification.

The current TUI treats root workflow rows, workflow-step children, family-member children, and agent entries
differently. `Agent.is_agent_entry`, tool availability, cleanup classification, running-agent listings, and row type
rendering all need a node-kind model that does not infer “agentness” from `AgentType.WORKFLOW` plus child position.

### 10. Unify typed outputs, not just row placement

YAML steps have declared output schemas, JSON/key-value parsing, field-reference validation, artifact capture, joins,
and an accumulated template context. Swarm agents expose string output variables through `sase var`, keyed by globally
stable agent names.

Command-to-agent and agent-to-command workflows need one group-scoped data plane. A reasonable direction is:

- `nodes.<local_id>.<field>` as the canonical group namespace;
- persisted output schemas and values on each node;
- an `agents[...]` compatibility alias for agent-produced string variables;
- explicit artifact references rather than putting large data in metadata;
- deferred template rendering only after required upstream values exist;
- static validation of known fields and runtime validation of values.

Without this, command roots can sequence work but cannot robustly communicate with later agents.

### 11. Human gates and dynamic plan/question handoffs are not ordinary rows

The standard plan chain is already a typed lifecycle evaluator. It can insert roles after plan approval or role
completion, preserve question/feedback state, snapshot definitions, and use specialized PlanApproval/UserQuestion
protocols. That behavior is not reducible to a static list of pre-launched swarm segments.

Unification should preserve a controller seam:

- a plain swarm has a static graph controller;
- a plan family has the standard plan-chain controller, which may add nodes and gates;
- a future custom family may combine a declared static graph with lifecycle events.

The UI grouping can be unified while the controller implementations remain deliberately different. Trying to make
`%wait` alone replace the family evaluator would regress plan/question behavior.

### 12. Markdown execution changes the trust model

Today a `.md` xprompt is reasonably understood as prompt text, even when separators cause agent fan-out. YAML workflow
files visibly contain executable Bash/Python steps. If Markdown gains executable segments, merely invoking or embedding
what looks like prompt prose may run local code from a workspace, plugin, or user xprompt directory.

Executable Markdown therefore needs:

- unmistakable syntax and catalog/preview labeling;
- a definition-level marker or capability declaration, not accidental code-fence interpretation;
- validation that executable fences cannot be produced accidentally by template substitution;
- LaunchApproval previews that include commands and node counts, not only agent slots;
- a policy for inline Python versus references to installed, reviewable helpers;
- clear behavior for workspace-local/untrusted definitions.

This is also an argument for compiling definitions before launch and snapshotting the compiled graph.

### 13. Embeddable workflow composition is different from swarm composition

Many important YAML workflows are not standalone pipelines. `#git`/plugin VCS refs bracket a caller's agent with
setup/checkout and `finally` release/diff steps. `#commit`, `#propose`, and `#pr` inject intent and run post-agent
adapters. `#json`, `#file`, and screenshot helpers run pre/post work around an explicit `prompt_part` boundary.

A Markdown swarm contains agent segments; it does not currently have an explicit “the caller's host agent runs here”
boundary. Attaching surrounding prose to the first agent is not equivalent to wrapping the caller, especially when the
first node is conditional, repeated, a command, or absent.

If these workflows are to migrate, executable Markdown needs an explicit host-prompt anchor plus well-defined wrapper
ordering. Otherwise retain them as workflow/intent adapters. “Move as much as possible” should not require eliminating
a semantic category that Markdown does not naturally express.

### 14. Nesting and mixed project scope need a policy

Swarms can be embedded recursively and individual prompt segments can carry different VCS refs. Family attachment,
however, resolves within one project and normally inherits the parent's ChangeSpec/workspace.

Define whether:

- invoking a swarm creates a nested group or flattens its nodes into the caller's group;
- a plan-chain subfamily is a subgroup or the same group with a controller transition;
- one group may span projects/repositories;
- workspace refs on child definitions override or conflict with group inheritance;
- group actions and completion cross project panels.

A conservative first version should probably keep a run group project-local and flatten statically embedded swarms,
while retaining provenance for each source definition.

### 15. Every family-scoped user action needs an aggregate contract

Current behavior already has special family scope for waiting, output variables, replies, revert, dismissal, status
mirroring, and completion. Parallel heterogeneous nodes add more cases:

- fold/expand and group banners;
- kill one node versus kill group;
- retry one node versus replay invalidated descendants;
- dismiss/revive a partially completed group;
- mark/bulk-action behavior;
- revert commits from all writers or one branch;
- which reply/log is shown on the root;
- one completion notification versus per-node notifications;
- unread acknowledgement and group failure summaries;
- linked chats and cross-node provenance.

These should consume the same group/node projection used by non-TUI integrations, not remain ACE-only inference.

### 16. Cross-surface and Rust-core changes are part of the feature

Group identity, node kinds, aggregate status, wait semantics, cleanup planning, pending actions, and catalog validation
are shared domain behavior under the project's Rust-core boundary. The integration-facing `AgentListEntry` currently
exposes family role, parent, and direct-child counts, but lightweight running-agent listings deliberately omit child
records.

The implementation must update or version:

- Python and Rust scan wires and artifact indexes;
- CLI agent lists and wait/name lookup;
- ACE row models, actions, metadata, and visual snapshots;
- mobile/editor/helper bridge projections;
- Telegram/notification summaries and gate actions;
- LaunchApproval preview and capacity accounting.

A TUI-only grouping rewrite would make the conceptual model less consistent, not more.

### 17. Definitions and active runs must be snapshotted

Static swarm text is saved today, and plan families snapshot custom role configuration. A general run graph needs the
same durability: definition id/source, version/hash, rendered inputs, compiled nodes/edges/policies, and dynamic state.

Otherwise editing a Markdown swarm while a node is waiting can change what later nodes mean, old rows cannot explain
their topology, and crash recovery has no authoritative graph to resume.

## YAML-to-Markdown parity matrix

The table below separates features that fit Markdown swarms naturally from those requiring a real common executor.

| Capability | YAML workflow today | Markdown swarm today | Requirement for migration |
| --- | --- | --- | --- |
| Typed inputs/Jinja | yes | yes | Preserve once-per-invocation values |
| Multiple agents | ordered/parallel constructs | yes, all dispatched | Add group-scoped ids and graph snapshot |
| Agent dependencies | implicit sequence/control flow | `%wait` | Persist explicit edges and failure policy |
| Bash/Python | yes | no native segment kind | First-class executable node syntax/runtime |
| Typed step output | yes | string agent vars only | Unified node output namespace/schema |
| `if` branching | yes | no | Scheduler-evaluated conditional edges/nodes |
| `for`/`while`/`repeat` | yes | agent `%repeat` is narrower | Dynamic graph expansion with visit caps |
| Nested parallel/join | yes | flat fan-out | Graph fan-out plus typed joins/aggregation |
| HITL | yes | plan/questions are separate | Durable gate nodes/protocol selection |
| `finally` cleanup | yes | no terminal dependency mode | `terminal` edges and cleanup outcome policy |
| Hidden steps | yes | `%hide` hides a row | Distinguish hidden node from hidden group |
| Environment | workflow-wide | per spawned process/directives | Group/node environment scopes and snapshot |
| Artifact capture | script stdout | per-agent artifacts | Per-node stdout/stderr/artifact contract |
| Shared step import | `use:` | inline xprompt refs are prompt-oriented | Typed reusable node/subgraph references |
| Compile-time field checks | yes | limited to prompt/frontmatter | Validate graph ids, fields, cycles, policies |
| Host prompt wrapper | explicit `prompt_part` | implicit first segment only | Explicit host anchor or keep adapter format |
| VCS outer wrapping | tag/order semantics | VCS ref inherited to segments | Pre/post/finally wrapper semantics |
| Workflow `done.json` | aggregate root marker | independent agent markers | Durable group completion record |
| Runtime loops/gates | executor owns state | no swarm owner after dispatch | Durable static/dynamic group controller |

## What can realistically migrate first

### Good first migrations

These fit a static executable swarm once command nodes, local ids, explicit edges, typed outputs, and group completion
exist:

- setup command -> one or more verification agents;
- independent parallel reviewers -> synthesizer;
- command checks -> conditional fixer agents, if simple conditional edges are included;
- the agent portions of `refresh_docs`, replacing Python's imperative nested `launch_agent_from_cwd` call with declared
  nodes;
- simple standalone workflows whose shape is commands followed by agents and no embedding boundary.

### Later migrations

These require a durable scheduler and richer policies:

- `sync`, whose agent step is conditional and repeated until conflicts are resolved;
- `fix_just`, once conditional branches, mixed node kinds, and failure behavior are fully modeled;
- evaluation workflows that exercise `for`/`while`/`repeat`, nested parallelism, joins, and per-iteration errors;
- user-authored HITL pipelines;
- dynamic plan/question families that combine runtime events with declared nodes.

### Likely retain as adapters, at least initially

These are xprompt-composition wrappers or typed intents rather than ordinary swarms:

- VCS workspace wrappers (`#git`, `#gh`, etc.) with outer pre/post/finally behavior;
- commit/propose/PR intent front doors;
- `#json`, `#file`, screenshots, and similar helpers with an explicit host-agent prompt boundary;
- curated privileged lifecycle side effects for plan approval and SDD mutation.

They can still compile into the same lower-level IR eventually, but forcing them into “a list of swarm members” is not
a useful product goal.

## Recommended implementation shape

### Phase 1: decouple grouping from lineage

Add explicit, additive group/node metadata and a presentation-neutral group projection. Adapt old plan-family and YAML
workflow artifacts into it. Keep existing `--`, `workflow_name`, and `parent_timestamp` behavior as compatibility
projections.

This phase should define group completion and action scope before changing launch syntax.

### Phase 2: normalize static agent swarms

Give every swarm invocation a unique group id and every segment a stable local node id. Compile `%wait` and
`%n(..., wait=...)` into graph edges and membership. Make capacity accounting use node resource class rather than child
status.

At this point parallel agent families become safe at the metadata/scheduler level, but writing nodes should remain
blocked until workspace policy is implemented.

### Phase 3: add first-class command nodes

Choose explicit executable-Markdown syntax and trust rules. Run Bash/Python as independently recorded nodes with typed
outputs, artifacts, kill/retry behavior, workspace policy, and group-scoped template context.

This phase enables the motivating update-then-verify workflow and the first useful YAML migrations.

### Phase 4: introduce a durable graph scheduler

Add conditional/terminal edges, deterministic skip/cancel behavior, group completion, crash recovery, and cleanup.
Then add dynamic fan-out/loops, joins, and generic HITL in separately testable increments.

YAML and Markdown should both compile into this scheduler; do not preserve two subtly different definitions of
success, cleanup, and output rendering.

### Phase 5: bridge the standard plan-chain controller

Have the existing family evaluator emit/transition nodes in the common group model while retaining its specialized
events and gate protocols. This is where the Agents tab can finally treat a plan family as simply a grouped run while
the backend still knows it is dynamically controlled.

### Phase 6: migrate definitions by semantic class

Migrate simple standalone DAGs first, then conditional pipelines, then selected wrappers only after an explicit host
anchor exists. Keep a YAML compatibility loader indefinitely if it is inexpensive; the goal is one runtime model and a
preferred authoring experience, not a risky flag day.

## Validation requirements

Before calling the concepts unified, tests should cover at least:

- two concurrent invocations of the same swarm without name collisions;
- parallel family members under global and per-group capacity limits;
- writing parallel members with each supported workspace policy;
- command root -> agent handoff using typed output and the intended installed/built environment;
- upstream failure causing deterministic skip/cancel, plus `finally` cleanup;
- group wait resolution for success, failure, optional/skipped nodes, and gates;
- kill/retry/dismiss/revive at node and group scopes;
- restart recovery while nodes are queued, commands are active, or a gate is pending;
- plan/question/custom-role parity on the common group projection;
- old `--`, dotted, single-dash, and YAML workflow artifacts;
- CLI/ACE/mobile/Telegram projections from the same group state;
- LaunchApproval previews that expose executable commands and accurate agent capacity;
- executable Markdown trust and template-injection boundaries;
- visual snapshots for agent, Bash, Python, gate, synthetic group, and mixed parallel states.

## Highest-value design questions

1. **Is the visible root a member or a container?** Should every group have a synthetic durable group record, with ACE
   optionally rendering its first concrete agent/Bash/Python node as the apparent root, or must the concrete root row
   itself remain the authoritative group record?

2. **Will membership become explicit metadata?** May `group_id`/`node_id` become authoritative while `--` names,
   `workflow_name`, and `parent_timestamp` become compatibility/display projections, or do you want family identity to
   remain name-derived?

3. **What workspace semantics should `wait=false` have?** Should a parallel family member share the parent's mutable
   checkout, receive an isolated workspace at a defined snapshot, or require an explicit read/write workspace policy;
   and how should parallel writers converge?

4. **What is the required v1 failure model?** Is it enough to support `after success` plus `after terminal`/`finally`,
   with downstream nodes deterministically skipped or cancelled, or must v1 also support on-failure branches, manual
   overrides, retries, and conditional expressions?

5. **How much YAML parity is actually a launch requirement?** Which concrete existing workflows must be expressible in
   Markdown for the first milestone: update-then-verify, `fix_just`, `refresh_docs`, `sync`, VCS wrappers, commit
   intents, HITL, loops, and/or nested parallel joins?

6. **What executable-Markdown syntax and trust boundary do you want?** Should `.md` files opt into an explicit workflow
   kind/capability before Bash/Python fences can execute, and are arbitrary inline Python bodies acceptable from
   workspace/plugin definitions or should Markdown normally call registered helpers?

7. **Is a durable host-side graph scheduler acceptable?** Can SASE persist a compiled graph and release/create nodes in
   response to outputs, failures, gates, and restarts, or must swarm-defined workflows remain coordinator-free and
   expressible entirely as processes pre-launched with wait metadata?
