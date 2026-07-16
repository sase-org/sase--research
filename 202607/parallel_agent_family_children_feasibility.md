# Parallel Agent Children in One Family: Feasibility and Design Research

Date: 2026-07-16

## Executive summary

Supporting multiple concurrently runnable agent children under one family is feasible. The two motivating cases do not
need a new general-purpose workflow scheduler: both already launch separate subprocesses, already describe their
ordering with explicit waits, and already allocate independent workspaces where needed. The missing capability is an
execution-neutral way to say, "these launch slots are members of one displayed family."

The change is nevertheless broader than adding a `parallel` flag. Today `%n(parent, suffix)` bundles four separate
behaviors:

1. it assigns family membership and a family-derived name;
2. it records parent/child lineage through `parent_timestamp`;
3. when the parent is active, it adds an exact success dependency on that parent; and
4. it defers the child into the parent's workspace.

Those semantics are correct for a serial plan-chain handoff. They are wrong for parallel peers. Reusing that path would
either serialize the peers, make them share a workspace, exempt them from normal runner-slot accounting, or all three.

The Agents-tab side is also only partly ready. A family root currently aggregates replies, tool calls, SASE context
events, output variables, and selected plan-chain timestamps, but commits, deltas, artifacts, errors, model/workspace
identity, arbitrary child timestamps, and group operations do not consistently use the same member set. Root status is
chosen mainly by "newest active child," which works for a serial chain but is not a meaningful aggregate for concurrent
siblings.

The recommended direction is a persisted, static **run-group manifest** with a unique group instance, stable local
member IDs, explicit membership and root presentation, and dependency/workspace policies kept separate. ACE should
project that manifest as an agent family and use one shared family-members projection for status, metadata, tools,
files, and actions. Existing `%wait` edges and workspace allocation can continue to execute the two target graphs.

This is a medium-to-large cross-cutting change, but not a high-risk concurrency rewrite. Most of the execution machinery
already exists. The difficult work is defining the data model and aggregation contracts so presentation does not alter
scheduling.

## Scope and source note

This research inspected:

- the current SASE workspace;
- the sibling `sase-core` repository opened through `sase repo`;
- the `chezmoi` linked repository opened through `sase repo`; and
- prior July research in the `sase--research` sidecar, especially
  `agent_family_unification_consolidated/agent_family_unification_consolidated.md` and
  `dynamic_agent_families_v1_v2_design.md`.

There is no literal `research_swarm_kiss` definition in the opened chezmoi revision. I treated
`home/sase/xprompts/research_swarm.md` as the intended workflow because it is the current four-agent KISS-style swarm:
two independent researchers, a lead that waits for both, and an image agent that waits for/forks the lead. If a
different uncommitted or renamed definition was intended, its member graph should be compared with the assumptions in
the use-case section below.

## What exists today

### Family attachment is a serial handoff primitive

The public family extension syntax is `%n(parent, suffix)`. The relevant path is:

- `src/sase/agent/_family_attach_resolution.py` resolves the newest visible root in the current project, allocates the
  suffix, and composes `<family-base>--<suffix>`.
- `crates/sase_core/src/agent_family.rs` deliberately ignores candidates with `parent_timestamp`, so attachment selects
  a root rather than an intermediate child.
- `src/sase/agent/_family_attach_launch.py` inherits ChangeSpec/model/workspace context. If the parent is active it sets
  `deferred_workspace=True` and records the parent's target workspace.
- `src/sase/axe/run_agent_directives.py` adds both the parent name and an exact artifact identity to the child's wait
  metadata, then persists `workflow_name`, `agent_family`, `agent_family_role`, `role_suffix`, and `parent_timestamp`.

Multiple children attached to the same active root can become runnable together after that root succeeds. The existing
`test_queued_family_siblings_do_not_mutually_block_parent_dependency` test confirms this. What is not supported is
running those children alongside the root or treating membership as independent from the parent-success edge.

The in-batch path has an additional constraint: `src/sase/agent/launch_executor.py` permits attachment to an earlier
statically named root, but marks attached children `can_attach_parent=False`. Template-named roots are excluded from
the pending-parent shortcut even though the multi-prompt launcher often already knows their concrete planned names.

### Epic work already has the desired parallel execution graph

The epic path is already structurally close to the target:

- `crates/sase_core/src/bead/work.rs` validates the epic DAG, partitions open phases into waves, assigns deterministic
  agent names, and makes the land agent wait for every launched phase.
- `src/sase/bead/work.py` renders one multi-prompt segment per phase and one final land segment. Each phase has only its
  actual DAG waits; phases in the same wave therefore run independently.
- `epic_work_segment_env()` supplies `epic_bead_id`, `phase_bead_id`, the plan reference, and commit attribution per
  segment.
- `src/sase/agent/launch_cwd_bead_work.py` sends the preplanned single-slot segments through the normal launcher, so
  each real worker retains normal process and workspace behavior.

Today the phase agent name is its phase bead ID and the land agent name is the epic ID. `%group:<epic-id>` is only a
user tag; it does not create a family or a lifecycle relationship.

Therefore, the epic work planner does not need a new DAG algorithm. It needs a group/family description attached to
the launch it already computes.

### The research swarm already has the desired dependency graph

The chezmoi `research_swarm.md` has four segments:

| Local role | Current name template | Dependencies |
| --- | --- | --- |
| Researcher A | `research.@.cdx` | none |
| Researcher B | `research.@.cld` | none |
| Lead/consolidator | `research.@.final` | A and B |
| Image agent | `research.@.image` | lead; forks lead |

The two researchers already run in parallel. The template allocator correlates their `@` token and rewrites later
wait/fork references to concrete names. As with epic work, only explicit membership and a root presentation are
missing.

The lead is the natural displayed root member: it owns the consolidated result and is the node users are most likely to
inspect. That root executes after two of its children, so a design that requires the concrete root process to be the
first segment is unnecessarily restrictive.

### ACE family rendering assumes lineage and mostly serial activity

ACE currently identifies a family child from `parent_timestamp`. Important consequences include:

- `Agent.child_linkage` treats any `parent_timestamp` row as a family member.
- `_agent_ordering.py` folds those rows under the artifact with the matching root timestamp.
- `_agent_status_apply.py` builds `followup_agents` and `runtime_children` from those direct timestamp links.
- `_agent_status_apply.py` mirrors the newest active child onto a root; plan-chain-specific recency rules also interpret
  later siblings as superseding earlier planner rounds.
- `src/sase/core/runner_slots/_admission.py` treats rows with `parent_timestamp` as non-root and therefore excludes
  them from countable root-agent admission.

That last point is critical: using `parent_timestamp` merely to fold parallel peer agents would let those peers bypass
the normal `max_running_agents` accounting. Display parenting must be separated from slot eligibility.

Current root metadata aggregation is uneven:

| Surface | Current family behavior | Gap for parallel peers |
| --- | --- | --- |
| Replies | Root plus direct `followup_agents`, with phase dividers | Suitable shape, but labels/order assume plan phases |
| Tools / slow calls | Uses `runtime_children`, attributed per child | Good basis if all members come from one projection |
| Memory / skills / opened workspaces | Uses `build_context_members()` | Good basis; currently follows direct children |
| Output variables | Root plus direct children, role attributed | Good basis; needs stable member IDs/collision policy |
| Timestamps | Selected plan feedback/question/code/epic fields copied | No generic per-member timeline or concurrency view |
| Model/provider/workspace | Mostly one root value; missing values copied from a mirrored child | "Newest/missing wins" is misleading with mixed peers |
| Commits | Reads the selected agent's `step_output` | Does not union all member commits |
| Deltas | Resolves one selected/live source plus its commit metadata | Does not present independent member workspaces as a group |
| Artifacts | Root artifacts plus child follow-up prompt artifacts | Does not union arbitrary member artifacts |
| Errors | Selected/root error fields | Multiple simultaneous failures are not consolidated |
| Status | Mirrors one newest active/waiting child | No defined group aggregate or member counts |
| Kill/dismiss/revive/revert | Several paths special-case workflow children or direct follow-ups | Root action semantics for peer members are incomplete |

The right refactor is a central family projection consumed by all these surfaces, not another set of child-to-root copy
rules.

### Wait failures are an existing weakness exposed by both use cases

Named waits resolve only on successful completion. `WaitDependencyStatus` currently exposes only `waiting` and
`resolved`; failed/killed/stopped producers remain unresolved, usually until a newer successful agent with that name
appears. As a result:

- an epic land agent can remain parked forever after a phase failure; and
- the research lead can remain parked forever after either researcher fails.

This is not caused by family grouping, but a family root will make the incomplete aggregate much more visible. A v1
family design needs an explicit position on failure propagation rather than silently inheriting an eternal WAITING
state.

## Feasibility by subsystem

| Subsystem | Feasibility | Expected shape |
| --- | --- | --- |
| Epic DAG planning | High | Keep the existing Rust wave plan; add group/member descriptors |
| Research swarm planning | High | Compile static `%family` metadata alongside existing name/wait planning |
| Parallel execution | Already present | Preserve each segment's current wait and workspace policy |
| Persistence/indexing | Medium | Add group instance/member/root fields and index them in `sase-core` |
| Agents-tab folding | Medium | Project group members independently from `parent_timestamp` |
| Root status | Medium | Replace newest-child mirroring with a defined group aggregate |
| Metadata consolidation | Medium-high | Migrate every detail source to one member projection with attribution |
| Group actions | Medium-high | Define and implement kill/dismiss/revive/revert/wait scope |
| Backward compatibility | High | Continue projecting legacy plan chains from existing family fields/timestamps |
| Full workflow scheduler | Not required for these cases | Existing static `%wait` graphs are sufficient |

The cross-repository part is unavoidable. Group identity, aggregate status, completion, and cleanup scope are shared
domain behavior under the Rust core boundary. Implementing only the Textual grouping would make ACE disagree with wait
resolution, CLI/mobile listings, and cleanup planning.

## Approaches considered

### 1. Add `wait=false` or `parallel=true` to `%n(parent, suffix)`

This is superficially the smallest change but is not recommended.

`%n` currently means more than "wait for parent." Disabling its implicit wait would still leave questions about
workspace inheritance, ChangeSpec inheritance, `parent_timestamp`, runner-slot admission, root resolution, and failure
semantics. A boolean cannot describe joins, after-terminal cleanup, on-failure branches, or independent workspace
policy. It would make the grouping directive a second scheduling language while retaining hidden coupling.

At most, such syntax could later be sugar that compiles into independent membership and dependency records. It should
not be the durable model.

### 2. Add a membership-only directive but keep a concrete first-member root

For example, a new `%family(parent, role)` could record membership without adding a wait or inheriting a workspace.
The first researcher or first epic phase could become the root.

This is workable for a narrow prototype, but root choice becomes arbitrary and leaks into names and metadata:

- the first epic phase is not the conceptual owner of the epic;
- the research lead and epic lander are more useful roots but run later;
- reruns can choose a different first open phase;
- root status/details conflate the chosen worker's own state with the aggregate; and
- a future root cannot be referenced by today's one-pass in-batch attachment path.

This option is acceptable only if the product explicitly wants "the first launched agent is the family root" as a
long-term rule.

### 3. Compile a static run-group/family manifest

This is the recommended option.

Before spawning any segment, the launcher persists a group instance containing:

- a user-facing family ID;
- a globally unique group instance/generation ID;
- a stable local member ID and role for every slot;
- the selected root member ID;
- the preallocated artifact identity for every member;
- the required member set for completion; and
- dependency/failure policies, either copied from the existing waits or referenced from the normalized launch plan.

Membership has no execution effect. `%wait`/identity edges decide readiness; the existing launch context decides
workspace and VCS behavior; each real agent continues to count toward runner capacity. ACE can render the selected root
member as the family container even if it is a later segment because root presentation comes from the manifest rather
than launch order.

A durable group record should own aggregate state. The concrete root member is only the row through which ACE presents
that state. If the root member's artifact is unavailable, ACE can render a synthetic group placeholder rather than
losing the family.

## Design decisions to make before implementation

### 1. Is family membership execution-neutral?

Recommended decision: **yes**. Joining a family must not add a wait, choose a workspace, inherit a branch, change slot
accounting, or imply failure propagation. Those are separate policies.

Keep `%n(parent, suffix)` as the serial plan-chain convenience with its current handoff semantics. Add a different
declarative path for static peer groups rather than changing `%n` underneath existing users.

### 2. What is authoritative: names, timestamps, or explicit group identity?

Recommended decision: explicit identity. Persist fields conceptually equivalent to:

```text
group_kind: agent_family
group_id: <user-facing stable label>
group_instance_id: <unique launch generation>
node_id: <stable local member id>
node_role: <display/semantic role>
root_node_id: <member presented as the root>
```

The exact field names should be chosen in the Rust wire design. Existing `agent_family`, `agent_family_role`,
`role_suffix`, `workflow_name`, and `parent_timestamp` remain compatibility projections for plan chains. A `--` name
prefix should not be required for new peer groups, and `parent_timestamp` should not be the authoritative membership
edge.

### 3. Is the root a process or a group?

Recommended decision: the aggregate belongs to a durable group record, while ACE projects a designated real member as
the visible root. Use the land agent for an epic and the lead/consolidator for the research swarm. This preserves useful
current names and avoids an arbitrary first-worker root.

The row must show aggregate state, but the panel should still distinguish "root member" metadata from "whole family"
metadata. A small MEMBERS summary near the top would make that distinction explicit.

### 4. What constitutes one family generation?

Recommended decision: one static multi-agent launch is one `group_instance_id`. The user-facing `group_id` may recur.

For `sase bead work` retries, do not silently merge old failed workers into a new active generation. Persist a
`supersedes_group_instance_id`/attempt relationship and show prior attempts from the root panel. Otherwise an old
failure can permanently poison current group status, and a completed phase omitted from a retry can make member-set
completion ambiguous.

If "every agent ever associated with this epic" is a hard requirement, expose that as an epic-history view layered
over generation records, not as the completion set for the active family.

### 5. How are names and references handled?

Recommended v1 decisions:

- Preserve existing global agent names for both workflows. Epic phase bead IDs and the epic land name are already
  useful external references; the research templates already work.
- Use local `node_id` values for group aggregation and attribution.
- Continue using existing global names in `%wait` and `#fork` for v1.
- Allow a group root to be a later segment because all member timestamps/names are preplanned before spawning.
- Later add group-local references such as `nodes.<id>` only if broader workflow convergence needs them.

This avoids a breaking rename of bead assignees, cleanup targets, wait references, and history keys.

### 6. What is the failure policy?

Recommended minimum policy:

- `after_success` is the default dependency edge.
- If a required predecessor fails, is killed, or is stopped, undispatched dependents become `STOPPED`/`CANCELLED`
  with a recorded cause instead of waiting forever.
- Group status becomes failed when a required member fails, even if independent siblings are allowed to finish.
- Cleanup/finally edges are out of scope unless one of the target workflows needs them.

The exact terminal label should be reconciled with existing `STOPPED` semantics and mobile/status wires. The key
requirement is a persisted terminal outcome that does not satisfy success dependencies.

### 7. What workspace and VCS policy do parallel members use?

Recommended decision: preserve the current per-segment policy. Family membership does not share workspaces.

- Epic phases keep their existing independent/deferred workspace allocation and ChangeSpec targeting.
- The land agent keeps its current explicit waits and claims its workspace only when ready.
- Home-mode research agents keep their current directory behavior. Their file protocol already gives A and B distinct
  report names before the lead consolidates them.

Parallel writers against one ChangeSpec can still race semantically; this is an existing epic-work risk rather than a
new family risk. The family panel should attribute commits/deltas by member so conflicts are diagnosable.

### 8. How does runner capacity work?

Recommended decision: every real agent process counts exactly as it does before grouping; the family container consumes
no slot. Do not derive admission from visual child/root status.

This requires decoupling `is_root_user_agent_record()` from display parenting for new group members. Legacy
`parent_timestamp` plan-chain continuations can keep their current semantics behind a compatibility classifier.

### 9. How is group status computed?

Define this before touching the TUI. A recommended priority is:

1. needs user input (`QUESTION`/`PLAN`) if any required member is blocked on the user;
2. failed if any required member has terminally failed and no recovery supersedes it;
3. running if any member is running;
4. waiting if at least one member is queued and none is running;
5. done only when every required member reached an accepted successful/terminal outcome.

The row should include counts such as `2 running · 1 waiting · 1 done`, because one scalar cannot fully describe a
parallel family. The scalar remains useful for filtering and notification priority; counts provide the truth.

### 10. What exactly does "consolidate all metadata" mean?

Recommended contract for the selected root:

- Show a MEMBERS table with local role, global name, status, model/provider, workspace, and elapsed time.
- Present timestamps as attributed member timelines; do not flatten concurrent events into plan-chain phase semantics.
- Concatenate replies with member/role dividers and deterministic ordering.
- Union tool calls, memory reads, skill uses, and opened workspaces by artifact directory with member attribution.
- Union output variables by `(node_id, key)`; never let last writer silently win at root scope.
- Union commits by repository and member, deduplicating by full commit identity.
- Union deltas/artifacts by repository/path and member. Preserve per-member views when two workers touch the same path.
- Show every member error and make the first/highest-priority failure a summary, not the only error.
- Show the epic plan once at group scope; keep a phase's bead/phase detail on its individual child row.
- Keep individual child panels available. Consolidation should not erase provenance.

Implement this through one `FamilyProjection`/`RunGroupProjection` abstraction. All panel loaders, cache keys, tool
sources, and actions should consume it. Avoid propagating more child values into mutable root fields.

### 11. What do root actions do?

Recommended defaults:

- expand/collapse: presentation only;
- kill root: confirm and kill every active member in the group instance;
- dismiss/save root: include all members and the group manifest;
- revive root: restore the manifest plus all selected generation members;
- revert root: preview the union of revertable member commits, grouped by repository/member;
- wait on root: wait for the manifest's required completion set, not whichever children happen to be discoverable;
- copy/reference root: copy the user-facing group/root reference; child rows copy their global agent name.

Partial member actions should remain available from expanded child rows. Notifications must be deduplicated so a group
completion does not make N child completions unusably noisy without hiding actionable member failures.

### 12. What authoring surface does the research swarm use?

Recommended v1 surface: introduce a membership-only `%family` directive (name subject to design review) that compiles
into the shared manifest and has no scheduling side effects. For example:

```text
%family(id=research.@, member=a, role=researcher)
%name:research.@.cdx ...
---
%family(id=research.@, member=b, role=researcher)
%name:research.@.cld ...
---
%family(id=research.@, member=lead, role=lead, root=true)
%name:research.@.final %wait:research.@.cdx %wait:research.@.cld ...
---
%family(id=research.@, member=image, role=image)
%name:research.@.image %wait:research.@.final #fork:research.@.final ...
```

This is illustrative syntax, not a finalized grammar. The important contract is that `%family` only declares the
group/member projection. Name templates, waits, model choice, VCS, and workspace behavior remain orthogonal.

The compiler must collect all family declarations before spawning, correlate the `@` token through the existing
template group, reject duplicate member IDs/multiple roots/missing roots, and persist the resolved manifest in the
LaunchApproval preview and launch artifacts.

The epic launcher can produce the same manifest directly from its typed `EpicWorkPlan`; it should not round-trip
internal family metadata through user prompt text.

## Concrete target shapes

### Epic work

Conceptual manifest:

```yaml
group_id: <epic bead id>
root_node_id: land
members:
  - node_id: phase:<phase bead id>
    role: phase
    agent_name: <phase bead id>
    waits_on: [<actual blocker phase agent names>]
  - node_id: land
    role: land
    agent_name: <epic bead id>
    waits_on: [<all launched phase agent names>]
```

The root entry displays the epic ID and uses the land member as its concrete root. All phase agents and the land agent
count normally, keep their existing names/workspaces, and appear as children when expanded. The root detail shows the
plan, per-phase/member status, replies, commits, deltas, artifacts, tools, and errors in one attributed panel.

### Research swarm

Conceptual manifest:

```yaml
group_id: research.<resolved token>
root_node_id: lead
members:
  - {node_id: a, role: researcher, agent_name: research.<token>.cdx}
  - {node_id: b, role: researcher, agent_name: research.<token>.cld}
  - {node_id: lead, role: lead, agent_name: research.<token>.final, waits_on: [a, b]}
  - {node_id: image, role: image, agent_name: research.<token>.image, waits_on: [lead]}
```

The lead is the displayed root even though A and B execute first. The root panel consolidates all four agents. The image
node remains a peer member with a dependency on the lead, not a nested family generation.

## Suggested implementation sequence

### Phase 1: Freeze the contracts with tests

- Add golden fixtures for a family with two simultaneous runners, one waiter, and a later root member.
- Define status priority/counts, failure cancellation, generation boundaries, action scope, and metadata attribution.
- Add regression coverage proving group membership does not alter wait dependencies, workspace allocation, or runner
  admission.
- Preserve legacy `%n` and plan-chain behavior byte-for-byte where the new group fields are absent.

### Phase 2: Add the core group model

- Define versioned Rust wire records for group manifests, members, root selection, and group projection.
- Persist/index group instance and member identity in `sase-core`.
- Add a presentation-neutral aggregate status/completion function.
- Extend cleanup/archive/revive planning to operate on a group instance.
- Keep legacy family discovery as a compatibility adapter that projects current plan-chain metadata into the new view.

### Phase 3: Compile and persist static family launches

- Preallocate all relevant slot identities before any member is spawned.
- Add manifest validation: one root, unique local member IDs, one project per v1 group, all referenced members known.
- Expose the manifest in LaunchApproval previews and partial-launch failure records.
- Add membership-only `%family` compilation for static multi-agent prompts.
- Let typed callers such as epic work pass a manifest directly.

### Phase 4: Move ACE to one group projection

- Fold rows by group instance without setting `parent_timestamp` on parallel peers.
- Separate display parenting from `is_root_user_agent_record()` admission.
- Replace newest-child status mirroring for new groups with the Rust aggregate and member counts.
- Route replies, tools, SASE context, variables, timestamps, commits, deltas, artifacts, errors, runtime, and cache keys
  through the same member list.
- Implement root and partial-member action semantics.
- Keep child detail panels and legacy plan-chain rendering.

### Phase 5: Migrate the two use cases

- Extend `EpicWorkPlanWire` or a sibling launch wire with the group manifest; make land the root node and phases members.
- Update the chezmoi `research_swarm.md` source with the membership-only declarations after the public grammar is stable.
- Verify repeated epic work, partial launch rollback, failed phases/researchers, kill/dismiss/revive, mixed models, and
  same-path deltas.

### Phase 6: Follow-ups, not blockers for the target cases

- Group-local output/reference namespaces (`nodes.<id>.<key>`).
- Dynamic membership after launch.
- General conditional/on-failure/finally edges.
- Bash/python group nodes and YAML/Markdown workflow convergence.
- Cross-project groups and per-group concurrency caps.

These broader items matter to the long-term run-graph architecture described by prior research, but they do not need to
block static epic and research families.

## Acceptance criteria for the first implementation

1. Two independent phase/research members in the same family can hold runner slots and execute concurrently.
2. Adding/removing family metadata does not change their waits, workspace numbers/directories, VCS refs, or model
   resolution.
3. The root row can correspond to a later member (land/lead) and appears as soon as the launch manifest is visible.
4. Collapsed view shows one family row; expanded view shows every member exactly once.
5. Root status/counts remain correct for simultaneous RUNNING, WAITING, QUESTION, DONE, FAILED, and cancelled members.
6. A failed required dependency terminally cancels its dependent instead of leaving it parked forever.
7. Every real member counts toward global runner admission; the family container does not.
8. Root details include every member's reply, tools, context events, variables, timestamps, commits, deltas, artifacts,
   and errors with stable attribution and no duplicate artifact reads.
9. Killing/dismissing/reviving/reverting the root operates on the agreed group scope; child actions remain available.
10. Legacy plan chains and `%n(parent, suffix)` retain their current serial handoff behavior.
11. A rerun creates a new group instance and cannot be poisoned by a failed prior generation.
12. Epic phase/land names and existing research wait/fork references continue to work.

## Recommended solution

Implement a versioned, persisted **static run-group manifest** shared by `sase-core`, launch planning, and ACE. Give
each invocation a unique `group_instance_id`, each member a stable local `node_id`/role, and select a `root_node_id` for
presentation. Keep group membership execution-neutral: existing `%wait` edges control readiness, existing launch
contexts control workspaces/VCS, and every real agent continues to count toward runner capacity. Do not use
`parent_timestamp` as the membership mechanism for parallel peers and do not overload `%n(parent, suffix)` with a
parallel boolean.

Project the designated land agent as the epic root and the lead agent as the research-swarm root, while storing the
aggregate independently of either process. Build one Rust-backed group/member projection and make every Agents-tab
metadata source and root action consume it. Add a membership-only `%family` authoring primitive for static swarms, and
let typed launchers such as epic work supply the same manifest directly. Preserve the current names, DAG waits,
workspace allocation, and serial `%n` compatibility. Include terminal dependency-failure propagation in the first
milestone so failed phases/researchers cannot leave the root land/lead agent waiting forever.

**In short: model the family as an explicit static group, not as a wait-bearing parent pointer; reuse the scheduler that
already runs these agents in parallel, and make ACE aggregate from the group manifest.**
