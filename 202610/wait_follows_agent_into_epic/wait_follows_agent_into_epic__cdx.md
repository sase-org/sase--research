# Waiting for work an agent creates: `%wait(for_epic=...)`

Researcher: **cdx**  
Research date: **2026-10-06**  
Scope: independent implementation research and design critique; no product changes.

Evidence baseline: `sase` commit `620e5310d48952dc5994d0eca91d750fd9789785`; linked `sase-core` commit `fa390362a556fe156701ee6bdf505411d4f0f7c5`. Repository observations below refer to these checkouts, not a claim about a future release. I did not consult the other reports or researchers in this swarm. External sources are primary documentation, consulted on the research date.

## Judgment

**This is a good feature. Implement it as a dependency on an agent's durably recorded epic outputs, with an explicit end to output discovery.** The proposed keyword is a reasonable public interface. The implementation should not discover epics by searching an agent's reply, following arbitrary artifact links, or periodically asking whether a bead happens to have the same creator name.

The user benefit is substantial: a person can submit a dependent prompt while the upstream agent is still deciding how to implement its work. The downstream runner starts after the upstream work is ready. This moves dependency bookkeeping into the host, where SASE already knows the producer and plan-approval lifecycle.

The difficult part is not adding a boolean. It is proving the difference between these three states:

1. The producer has not finished deciding or publishing its epic outputs.
2. The producer has finished and created no epic.
3. The producer has finished and created one or more epics whose closure must be awaited.

A polling implementation that treats an empty link query as state 2 will occasionally start too soon. One that waits indefinitely for the first epic will strand perfectly valid producers that create none. The recommended design records that distinction explicitly.

The largest caveat is the default. Making ordinary named `%wait` follow epics changes existing behavior, particularly the documented ability to wait for a submitted planner row before approval. I support the requested default for newly authored, explicitly named agent waits, provided existing stored waits and generated sequencing dependencies retain their previous behavior and the TUI advertises the effective scope.

## What exists today

### Agent and bead waits already compose

`%wait` accepts positional agent names and `agent=`, `bead=`, `hood=`, `proc=`, `unit=`, and `time=`. Python collection validates these keywords, then flattens agent targets into one list. Bead and hood targets have their own lists. There is no `for_epic` field. [S1]

The dependency evaluator requires all unresolved agent, identity, fork-source, hood, and bead conditions to resolve. It already accepts exact artifact dependencies with project and launch timestamp information. Therefore, a new epic-output condition can compose with the existing AND semantics rather than introducing a different scheduler. [S2]

Ordinary named agent waits generally require successful completion of the newest matching run. Failures stay parked, and the wait checker reports terminal blockers. There are important special cases: aggregate sessions/clans, retried monitor/gate turns, tribe selection, and submitted planner rows. A submitted `<base>--plan` row is considered resolved while the plan is still awaiting approval; the bare session name is not. This behavior has explicit regression tests. [S3]

Existing `%wait(bead=...)` means **closed**, not necessarily resolved as `done`. The project memory documents `done`, `canceled`, and `superseded` bead resolutions. Closing an epic normally requires all descendants to be closed, and its land agent owns the parent close. Waiting for the parent epic therefore reuses a useful completion boundary instead of tracking every worker ourselves.

Documentation describes local bead waits, but the implementation is more capable: full IDs can route through enabled-project store snapshots; shorthand and future IDs keep local scope. Cross-project derived epics should use the actual owner store rather than assume the waiting agent's project. [S4]

### There are two execution paths to update

The runner first checks whether dependencies are already resolved. If it must park, it writes `waiting.json`, watches for `ready.json`, and periodically resolves dependencies itself as a fallback. The fallback interval is currently 60 seconds. AXE's wait checker independently evaluates parked runners and publishes readiness. Both use the shared Python dependency functions. [S5]

The checker also performs a fresh membership confirmation before releasing an aggregate dependency: a successor can appear near the predecessor's terminal marker. This is an existing acknowledgement of precisely the kind of handoff race this proposal must handle. Confirmation currently reuses the supplied closed-bead snapshot; it is not an epic-output publication barrier. [S6]

Adding the behavior only to the checker would leave the initial fast path and outage fallback able to start too soon. Adding it only to TUI state would change appearances without changing admission.

### Creator attribution exists; the necessary scheduling link does not yet

Plan proposal stamps `proposed_by` using the acting agent's durable global name. Approved epic creation passes that proposer into bead creation. Rust persists `created_by`, makes phases inherit their parent epic's creator when appropriate, and otherwise can fall back to the store owner. These are strong foundations for attribution. [S7]

However, they identify an agent **name**, not the precise execution attempt that produced the epic. A reused name can create several historical epics; phase inheritance also means several non-epic beads can share the same creator.

The artifact graph currently projects:

- An agent's `bead_id`, `epic_bead_id`, or `phase_bead_id` into `implements` edges.
- Its published `wait_for_beads` into `awaits` edges.
- Stitch trailers into `stitch produced-by agent` edges.

The inspected projection entry point has no bead-creator rule. Moreover, the Rust `produced-by` relation currently advertises stitch sources and agent targets. Using `bead:<id> produced-by agent:<name>` requires extending that contract and its projection inputs. Infrastructure exists, but consistent creator-to-epic links are not already sufficient for this feature. `implements` is not evidence that an agent created the bead. [S8]

### Epic launch is asynchronous and recoverable

Plan approval starts an epic launch in a host-owned leased workspace, normally through a monitor and sometimes through a proc fallback. Epic construction creates the bead graph, links the plan, and launches workers. Some failures roll back the new graph; publication/spawn failures can preserve it for recovery. Relocation can change the epic ID. [S9]

There is already an epic-completion handoff keyed by project and planner artifact timestamp, with pending/settled records, atomic writes, saved resume argv, and notification recovery. That is a promising integration point. It is currently a **notification** protocol: it can fail open, uses a grace period, and reaps settled state. It must not be treated as permanent proof that no epic exists. Scheduling needs retained output evidence with stricter semantics. [S10]

A further wrinkle: bead relocation remaps IDs **and re-mints event IDs**. A create event's current `event_id` is therefore not a safe immutable output handle across relocation. [S11]

### The TUI already has an appropriate visual vocabulary

The list renders `WAITING` in amethyst, keeps agent and bead status counts separate, and can show a single bead token. The detail panel has aligned tagged lanes for agents, beads, hoods, and time. Its renderer already shows per-target status badges. [S12]

Bead statuses are enriched through a bounded cache, with separate handling for cold/unknown entries. Wait maps and row rendering are also cached. New output-state revisions must participate in invalidation; merely adding a field to metadata would risk stale rows. The project's performance contract requires worker-based I/O, incremental row updates, and no synchronous store reads during rendering. [S13]

## Proposed public contract

### Syntax and defaults

```text
%wait(builder)                         # builder plus any epic outputs
%wait(agent=builder, for_epic=true)     # explicit equivalent
%w(builder, for_epic=false)            # existing completion-only behavior
%wait(a, b, for_epic=true)              # apply to both targets in this occurrence
%wait(a, for_epic=false) %wait(b)       # independent policies
%wait(builder, bead=sase-87, time=5m)   # all dependencies, then the duration
```

`for_epic` belongs to each **directive occurrence's agent targets**, not to the whole prompt. A prompt-wide boolean cannot represent the last-but-one example and will eventually cause confusing edits.

Parse only `true` and `false` as the documented boolean tokens. Reject empty values, malformed values, duplicate keyword arguments, and contradictory policies for the same canonical agent target. Identical repeated conditions can be deduplicated. Source spans should let the editor mark the offending input.

Both `%wait(for_epic=true)` and `%wait(time=5m, for_epic=false)` should be hard errors because that occurrence has no explicit agent argument. An agent in another `%wait` occurrence does not supply the missing scope. Runtime errors should match editor diagnostics, for example:

> `for_epic= requires an agent target in the same %wait(...), e.g. %wait(builder, for_epic=true).`

**Scope recommendation for the first release:** support exact agents, exact turns, and named serial agent sessions. For a session, include epic outputs attributable to its own member turns within the selected session generation. Do not follow every agent it launched or every artifact reachable from it.

Explicit `for_epic=true` on a clan, tribe selector, proc, hood-only target, or generic logical unit should fail with a targeted diagnostic in this first release. These entities have different selection boundaries. Ordinary existing aggregate waits keep their present semantics. A named agent in the same submitted batch is supported even when the launch planner rewrites it into a logical-unit reference: preserve the fact that it was an agent target and preserve its epic policy. [S14]

Bare `%wait` keeps its existing preceding-unit/previous-agent sequencing meaning. It does not silently acquire epic-following behavior. Users who want the new scope name the producer explicitly. This is a deliberate narrowing of the default requested in the prompt; see the adjustments section.

### Which epics count?

An eligible output is a bead with `issue_type=plan` and `tier=epic` whose creation or approved-plan launch is attributed to the selected producer execution, including a host operation that materializes a plan submitted by that execution.

Include all such **direct epic outputs**, not just the first. Exclude:

- Phase beads, tale/ordinary plan beads, tasks, and goals.
- The existing epic the producer was assigned to implement.
- Epics it merely cited, read, edited, or manually linked as related.
- Epics from a different historical execution using the same name.
- Arbitrary epics made by independently launched helper agents.

A nested epic directly produced by the selected scope counts. The parent's existing descendant-close rule can account for nested work below a discovered epic; there is no need for recursive artifact-graph traversal.

The operation is “follow this producer's outputs,” not “follow all work somehow related to this producer.” That boundary prevents accidental waits on unrelated backlog items and keeps the feature understandable.

### Completion and zero outputs

Release only when:

```text
existing agent completion condition is satisfied
AND epic-output discovery for the selected producer scope is sealed
AND every published epic output is closed
AND all other authored dependencies are satisfied
```

For a sealed, empty output set, the epic condition succeeds immediately. Before sealing, emptiness means unknown. A known epic can be displayed before sealing, but it does not prove that it is the last one.

Preserve existing bead closure semantics: a closed `canceled` or `superseded` epic satisfies this wait, and its resolution is displayed. This feature should not silently redefine all bead waits as successful implementation. A future success-only policy would be a separate, deliberate addition if users need it. Missing beads, unreadable stores, corrupt output state, and launch errors do not count as zero outputs.

A rejected plan can close its output-discovery reservation with no epic. Whether the complete dependency releases still depends on the existing agent completion predicate. Do not turn a failed producer into a successful dependency merely because no epic remains.

The duration starts after the full dependency predicate, including epics, succeeds; an absolute time remains a floor. Capacity admission follows dependencies and time. Waiting reserves no running-model capacity. Once released, reopening a bead does not re-park the launch, matching present bead waits.

## The reliability design

### 1. Bind the epic set to the producer that satisfied the agent condition

Keep the normal named resolver until it yields the successful/resolved entity that satisfies the agent part. Persist that entity's exact generation and member identity before accepting its epic outputs. Existing retry/name-selection behavior remains available **before** this binding.

After binding, a later run of the same name must not replace the selected producer or supply a different epic set. If its epic is stuck, starting another unrelated `builder` run should not silently release the waiter. Recovery should repair the selected epic/launch, or the user can deliberately edit the dependency.

Use existing durable identity components where possible: canonical owner-qualified agent name, project key, launch timestamp, and session root/generation when needed. Current artifact paths are useful local locators, not the durable identity to preserve in portable records. Normalize legacy aliases and session promotion through the existing identity layer.

For an exact planner-row target, submission may satisfy the ordinary agent condition; **its output discovery remains open** while its epic proposal is awaiting review. A `for_epic=false` consumer can continue to analyze that submitted plan immediately. A default epic-following consumer waits for the approval outcome, materialization, and eventual epic closure.

For a session, seal only after the selected session generation has finished its own eligible member chain and all output reservations belonging to those members have settled. Do not seal on one predecessor's `done.json` or on the absence of currently visible successors. Reuse the existing membership-confirmation principle.

### 2. Record producer provenance during creation, not after agent completion

Add a narrow structured provenance record to bead creation and approved-plan launch:

```text
producer execution identity
producer session generation, when applicable
source plan/gate launch request identity, when applicable
stable output correlation identity
owner project/store identity
```

These are proposed logical fields, not existing wire names. Keep `created_by` for human attribution. Stamp precise provenance from host metadata at proposal/launch time; do not ask the model to remember to emit a link or call `sase var set`.

For direct `sase bead create` in an agent, supply the same producer metadata through the ordinary creation path. For host-approved plans, carry the originating producer through the gate and monitor/proc rather than attributing the epic to the monitor process or store owner.

Persist provenance in the bead's canonical creation transaction, so a crash cannot leave a created epic whose origin exists only in an uncommitted agent workspace. Creation without scheduling provenance must leave the output reservation unresolved and diagnostically repairable rather than authorize a false no-epic result.

Make output correlation survive bead renumbering. It can be tied to an idempotent launch request plus output ordinal, or minted once for a direct creation operation and preserved during relocation. Do not key it solely by mutable bead ID, current event ID, title, or wall-clock ordering. Retries of the same launch should not create duplicate output obligations.

### 3. Make the end of discovery an explicit host fact

A compact producer-output record is enough; a new general workflow engine is unnecessary. Conceptually:

```json
{
  "schema_version": 1,
  "producer": {
    "project": "sase",
    "global_name": "owner.machine.builder--plan",
    "launch_timestamp": "..."
  },
  "revision": 7,
  "discovery": "sealed",
  "pending_launches": [],
  "epic_outputs": [
    {"output_key": "...", "owner_project": "sase", "bead_id": "sase-87"}
  ]
}
```

This illustrates the contract, not a prescribed file layout. Store durable facts through the existing host-owned lane, with local marker/index projections for fast reads. Extend the current epic handoff correlation and portable agent publication where useful. Do not use its notification TTL as scheduling retention.

The critical ordering invariant is:

> An operation that may create an epic is durably registered against its producer before that producer scope can be sealed.

A producer can seal when its own relevant work is finished and every registered proposal/creation operation has published either an output or an explicit no-output result. A pending epic approval is an operation. A deferred host monitor/proc is an operation. A launch that retained an unpublished graph after failure is unresolved, not an empty success.

Normal producers that create no epic must also acquire a sealed empty result through host finalization. Otherwise “none” cannot be distinguished from missing metadata. Late delivery is handled by versioned durable publication: a consumer does not accept a seal until the referenced output facts are readable. No guessed sleep or “two quiet scans” can substitute for this ordering contract.

Reuse existing stores and atomic publication paths. Where producer state and bead state cannot be committed atomically across stores, persist an idempotent output/reservation fact first and leave sealing dependent on acknowledgement/replay. Do not pretend separate file writes form a transaction. The bead creation provenance remains the recoverable source for reconstructing a missed output publication.

### 4. Use one backend transition function everywhere

Define a Rust-owned reducer over explicit snapshots, with structured outcomes such as:

| State | Meaning | Display |
| --- | --- | --- |
| `agent` | Agent completion condition is unsatisfied | Waiting for builder |
| `discovering` | Agent part satisfied; output discovery remains open | Waiting for epic approval/publication |
| `epics` | Scope sealed; at least one epic is not closed | Waiting for epic sase-87 |
| `resolved` | Scope sealed; every required output is closed, or none exist | Dependency satisfied |
| `blocked` | Missing evidence or a terminal failure needs recovery | Epic launch failed / output unavailable |

These are dependency-stage values, not new top-level runner statuses. Output can include the producer binding, effective bead targets with owner identities, explanations, observation revisions, and notification/recovery facts.

Python collects filesystem/process/store inputs and persists approved transitions. Rust owns canonicalization, validation, provenance selection, set membership, sealing rules, and the release predicate. Python and Textual render the result. Existing dependency orchestration is still partly Python; that is a fact of this checkout, not permission to implement this new domain policy twice.

The initial already-resolved check, AXE checker, runner fallback, typed launch admission, and UI status query must use this same contract. Carry it through Rust/Python bindings and update `sase-core-revision.txt` before callers depend on new bindings.

### 5. Persist transitions without destroying authored intent

Keep the original agent wait and its policy. Persist bound producer and derived epic outputs separately. Do not replace `%wait(builder)` with `%wait(bead=sase-87)` and discard the reason that bead was selected.

This matters for reload, explanation, editing, and multiple epics. One target can have a completed agent condition plus open epic conditions while another is still running.

Use a wait-spec revision and compare-and-set/locked transition writes. Readiness must name the specification revision and binding/output observation it satisfied. A TUI edit that changes a target or disables epic following invalidates earlier readiness and derived state for that target. A stale checker cannot re-add removed epics afterward.

For this new contract, malformed or stale readiness is insufficient to start. The current `read_ready_result` accepts some unreadable/malformed markers; blindly reusing that permissive branch would undermine the stronger guarantee. Tighten the new versioned-marker path and preserve deliberate user “unwait” as an explicit operation. [S5]

No shared `resolved_deps` shortcut may bypass the new epic subcondition just because the original agent name was memoized.

## TUI design: make the handoff visible and calm

Retain the existing `WAITING` status and amethyst wait color. Add a short stage reason to the list row and use the existing detail lanes for a two-step story.

Before producer completion:

```text
reviewer  (WAITING · agent builder)

Wait: [agents] builder ▶ running
      [epics]  follow builder's epic outputs
```

While the producer's submitted epic plan is awaiting review:

```text
reviewer  (WAITING · epic approval)

Wait: [agents] builder--plan ✓ submitted
      [epics]  awaiting approval of builder's epic plan
```

After the producer part is satisfied and output discovery is sealed:

```text
reviewer  (WAITING · epic sase-87 ◐)

Wait: [agents] builder ✓ complete
      [epics]  sase-87 ◐ in progress — produced by builder
```

For more than one epic, show the first identifier plus `+N`, or a completed/total epic count at narrow widths. The detail view lists all outputs, titles, status, owner when foreign, and their producer. If a producer is still running but an epic is already known, show both facts; do not imply the agent requirement has disappeared.

Use existing bead tokens and existing artifact/agent jump affordances. The bead ID opens the bead context; the producer opens its context. Keep the completed agent lane dimmed, preserving an obvious explanation for why the dependency changed. A cold cache says “loading” or shows a neutral pending token; it must not claim a bead is missing.

A one-time selected-row toast such as “builder finished; now waiting for epic sase-87” is useful reinforcement. Persisted stage and detail are the essential feedback. Do not generate inbox notifications for routine handoffs, and do not make a toast the only explanation a returning user receives.

Reserve a red warning for a problem: “Epic launch failed; waiting for recovery,” “Epic output unavailable,” or “Waiting dependency forms a cycle.” Reuse terminal wait notification deduplication and include the actual recovery command supplied by the host when available. A mere approval delay is ordinary waiting.

The wait editor should expose a per-agent choice **Agent and its epics** / **Agent only**, with the former selected for supported new named targets. Mixed policies need a per-target model, not a single checkbox for the whole prompt. Preserve policies on edits, revive, prompt rewrites, and portable publication. If the existing modal cannot yet express mixed policies, show them accurately and keep a raw prompt edit route rather than silently flattening them.

No new keymap is necessary. If one is introduced later, update `src/sase/default_config.yml`, conditional footer behavior, and help. All enrichment stays off the event loop. Stage/output revision changes should invalidate the wait cache and patch the affected row rather than rebuild the entire list. A cosmetic transition can run after model refresh; it never determines scheduling.

## Edge cases that determine whether this is reliable

| Situation | Required result |
| --- | --- |
| Producer succeeds with no epic | Seal empty outputs; satisfy epic condition. |
| Producer creates two epics | Await both; never pick the first arbitrarily. |
| Producer creates only tasks/tales/phases | No eligible epic outputs; seal normally. |
| Producer implements an existing epic | Do not adopt its assigned epic as a produced output. |
| Plan submitted before approval | Show discovery/approval stage; do not infer no epic. |
| Approval chooses no launch | Settle that reservation explicitly; preserve other outputs and the existing agent predicate. |
| Host materializes an epic later | Attribute it to the original producer; await closure. |
| Producer/launch crashes | Stay parked with a recovery reason; never convert unknown to empty. |
| Failed launch rolls back its graph | Record that outcome; no dangling output from a transient graph, but a terminal failed reservation remains blocked pending recovery. |
| Failed launch preserves its graph | Keep a recoverable output/reservation; bind it once publication confirms the canonical identity. |
| Retry before producer binding | Follow existing named wait selection rules. |
| Same name rerun after binding | Preserve the original selected producer and epic set. |
| Epic renamed/renumbered on publication | Follow stable output correlation to the current full bead ID; never attach to an unrelated bead now occupying the old ID. |
| Epic closed as canceled/superseded | Satisfy closure and display its resolution. |
| Epic disappears or owner store is unavailable | Stay parked and explain missing/unavailable evidence. |
| Epic reopens after release | Do not re-park a released launch. |
| Agent is dismissed or artifacts are pruned | Retained producer/output evidence still supports the bound dependency; needed live waits protect that evidence. |
| AXE checker is unavailable | Runner fallback evaluates the same output contract. |
| Wait edited during a checker pass | Reject stale transition/readiness by spec revision. |
| Mixed agent, explicit bead, hood, and time waits | AND all dimensions; duration follows the full dependency stage. |
| Waiter is a phase/land worker of the epic it would follow | Reject/report the cycle; never release by timeout. |
| Output state comes from an older host without a seal | Explicitly show unsupported/unverified provenance, not “no epic.” |

For legacy runs, first attempt exact reconstruction from plan/gate/launch and bead provenance when sufficient. Ambiguous creator-name matching is diagnostic evidence, not automatic scheduling truth. If reconstruction cannot prove the scope, block the new epic-following condition with an actionable explanation; a user can select Agent only or an explicit bead. Already-stored legacy waits remain completion-only and need no new proof.

Cross-machine support needs coherent evidence from the producer's actual host/store. Reuse existing supported wait transport and enabled-project routing; do not broaden remote-dispatch combinations in this feature. A partition may delay a waiter, but it cannot authorize readiness from a partially synchronized output list.

## Requirements I would adjust explicitly

1. **“Any epic” becomes every direct epic output of the selected execution scope.** This clarifies multiple outputs, historical names, and assignment versus creation. Arbitrary transitive artifact links do not define scope.
2. **Zero outputs require an explicit end to discovery.** Agent completion alone is not enough when an epic approval or host launch remains pending.
3. **Invalid context is a hard error.** Either boolean without an explicit agent in the same occurrence is rejected, not merely warned about and ignored.
4. **Apply the default to newly authored explicit agent targets; preserve sequencing waits.** Bare preceding-unit waits, synthetic `%repeat` chains, implicit fork waits, and session attachment dependencies remain completion-only. Generated named waits should emit/persist an explicit `for_epic=false` policy where necessary. Otherwise a land/phase continuation can wait on the very epic it must help close.
5. **Initially exclude aggregate selectors from epic following.** Exact agents, turns, and serial sessions cover the motivating case. Clan/tribe support can follow once producer-set boundaries are designed. Existing aggregate wait behavior is preserved.
6. **Closure is the first-release completion policy.** Display canceled/superseded outcomes; do not add a silent success-only rule to this keyword.
7. **The transition is presentation, not replacement.** The agent condition remains satisfied provenance; the epic condition becomes the active blocker. Do not erase original intent or report that the system stopped requiring the agent.
8. **Normal waiting is persistent and quiet; recovery is conspicuous.** Use a stage badge and connected detail lanes. Avoid a new top-level status or noisy routine notifications.

The requested default remains a compatibility decision, not an incidental parser default. Parse omissions as “unspecified” until origin/target type and migration policy are known, then persist the effective policy. Old markers without the new schema retain old semantics. Audit submitted-planner consumers and all synthesized waits before switching new named prompts to the default.

If a compatibility branch must remain temporarily available, use the project's sunset-flag process, test both states, and make the enabled branch the intended new default. This report proposes no flag or bead creation. A permanent user preference would be ordinary configuration instead of a temporary feature flag.

## Alternatives and critique

| Approach | Strength | Problem | Judgment |
| --- | --- | --- | --- |
| Search `created_by` after agent success | Very small patch | Name reuse, no-output ambiguity, async approval, phase inheritance | Reject as authority. Useful only for controlled repair. |
| Traverse the artifact graph | Reuses visible relationships | Eventual projection and ambiguous semantic relations; absence proves nothing | Use for explanation, not admission. |
| Wait only on the bare session | No new syntax | Current session completion need not represent independent epic workers; changes every session's meaning | Insufficient for this request. |
| Preallocate an epic before planning | ID available immediately | Empty/abandoned draft epics; changes the planner workflow | Consider only if early epic identity has independent value. |
| Require a `sase var` epic ID | Reuses producer outputs | Agent must remember; a value supplies neither absence proof nor output-set closure | Optional convenience, not correctness. |
| Explicit `for_epic=true`, existing default false | Least disruption | Misses the requested convenient default | Good migration stage, not my preferred finished behavior. |
| Replace boolean with `scope=agent\|epics\|...` | More extensible | More concepts before demand; still needs provenance and sealing | Defer until a second output kind needs following. |
| Recorded epic outputs plus sealed producer scope | Clear zero/many behavior, restart safety, explains transitions | Requires host integration and coordinated Rust/Python changes | Recommend. |

A general “wait for everything this agent ever causes” feature would be much harder and less predictable. Jobs, tasks, follow-up researchers, and deliberately detached procs do not all have the same completion meaning. Keeping this feature about direct epic outputs is a good restraint.

There is also a real workflow hazard: people who wait on a planner to **review or refine its plan** need Agent only. The new default can otherwise wait for implementation before the reviewer begins. Completion text and preview should explain “Wait for builder and its epics” before launch, and `for_epic=false` must be easy to discover.

## Lessons from other orchestration systems

Temporal distinguishes confirmation that a child workflow started from waiting for its result. Its Go documentation requires the child's start event to be recorded before a parent completes if that child is to outlive the parent. **Design inference for SASE:** registering a possible epic output before producer sealing is a lifecycle guarantee, not an eventual-link search. This does not require adopting Temporal. [Temporal child workflow documentation](https://docs.temporal.io/develop/go/workflows/child-workflows)

Airflow supports tasks created from an upstream runtime result and explicitly defines the zero-length case, including how downstream trigger rules handle it. **Design inference for SASE:** represent a final empty output set deliberately; do not treat a missing record as an empty set. SASE should satisfy its optional epic condition for a proven empty set rather than copy Airflow's task-skip mechanics. [Airflow dynamic task mapping](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/dynamic-task-mapping.html#automatically-skipping-zero-length-maps)

## Implementation boundaries and acceptance evidence

This is a moderate cross-layer change, not a one-file directive addition. A practical sequence is:

1. Implement precise creation/launch provenance and sealed output evidence, including direct creation, plan approval, monitor/proc launch, rollback, relocation, retries, and no-output finalization. Add the bead-source `produced-by` relation/projection from this evidence.
2. Implement Rust occurrence-scoped wait policy and the producer-output reducer. Integrate both Python runtime paths and typed same-batch launch waits; version marker/readiness state and preserve legacy reads.
3. Carry the projection through agent metadata, the Rust scanner, Python wire mirrors, portable publication whitelists, revive/edit paths, and relevant cache keys. Extend `awaits` to include bound derived epic targets while keeping authored and derived conditions distinguishable.
4. Present the stage badge, connected detail lanes, editor completion/diagnostics, per-target wait editing, and launch preview. Finish the default migration after generated waits and submitted-plan workflows have explicit policies.

These are implementation suggestions, not a submitted SASE plan. No repository code was changed during this research.

Tests should establish behavior and failure boundaries, particularly:

- Parser parity and source diagnostics for aliases, multiple occurrences, mixed policies, malformed booleans, no-agent inputs, and same-batch named-agent rewrites.
- A successful empty producer releases; an unsealed empty producer never releases.
- Producer success observed before delayed epic publication does not release.
- Exact planner submission plus pending epic approval remains parked under the new policy, while `false` retains current behavior.
- Two epics, unrelated assigned epics, phase inheritance, name reuse, session membership confirmation, and legacy aliases select the right outputs.
- Crash between canonical bead creation and output publication recovers from recorded provenance.
- Rollback, retained graphs, relocation, duplicate/retried launch, canceled closure, and unavailable owner stores produce the stated results.
- AXE, initial fast path, runner fallback, and typed admission agree on identical snapshots.
- A stale ready marker or concurrent TUI edit cannot start a runner against an obsolete specification.
- Synthetic land/phase/fork/repeat dependencies do not acquire accidental epic cycles.
- Reloaded, dismissed/archived, and portable agent records retain necessary bindings and explain the wait.
- TUI snapshots cover agent, approval, epic, multiple-epic, narrow-width, loading, foreign-owner, and blocked states. Rendering performs no disk I/O; a stage change invalidates cached row/detail state.

Useful existing regression homes include `tests/test_directives_wait.py`, `tests/test_run_agent_wait_deps_initial.py`, `tests/test_run_agent_wait_fallback.py`, `tests/test_wait_dependency_release_confirmation.py`, `tests/test_axe_chop_wait_checks_submitted_planners.py`, `tests/test_bead/test_attribution.py`, `tests/artifact_links/test_agent_wait_bead_projection.py`, and the wait-section/list/modal tests under `tests/ace/tui/`. Use the documented checks for each modified repository and coordinate the Rust revision pin. A research-only report does not justify running the product test suite.

## Source ledger

All repository source links below are permalinks corresponding to locally inspected, audited checkouts. The files were not web-fetched. Project reference memories for macros, artifacts, beads, flags, and TUI performance were consulted through `sase memory read`.

- **S1 — Current directive collection and parsed payload:** [Python wait keyword collection](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/macro/_directive_collect.py#L130), [PromptDirectives](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/macro/_directive_types.py#L145), [prompt wait editing model](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/macro/_directive_edit_wait.py#L21).
- **S2 — AND resolution and exact dependency identities:** [dependency_resolution_status](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/core/wait_dependency_resolution/_resolution.py#L14), [artifact candidates](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/core/wait_dependency_resolution/_types.py#L34).
- **S3 — Existing dependency and planner semantics:** [macro documentation](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/docs/macros.md#L2709), [submitted plan classification](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/core/wait_dependency_resolution/_submitted_plans.py#L21), [planner-row release regressions](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/tests/test_axe_chop_wait_checks_submitted_planners.py#L19).
- **S4 — Owner-aware bead lookup:** [closed_bead_ids_for_waits](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/bead/wait_status.py#L36).
- **S5 — Initial resolution, parking, fallback, and permissive readiness:** [runner barrier](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/axe/run_agent_wait.py#L70), [direct dependency check/readiness](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/axe/run_agent_wait_deps.py#L48).
- **S6 — Checker release confirmation:** [checker](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/scripts/_chop_wait_checks_run.py#L153), [fresh dependency confirmation](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/core/wait_dependency_resolution/_confirmation.py#L23).
- **S7 — Actual proposer and creator attribution:** [proposal stamp](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/main/plan_propose_handler.py#L163), [attribution adapter](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/bead/attribution.py#L64), [epic creation](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/bead/epic_from_plan.py#L139), [Rust creation policy](https://github.com/sase-org/sase-core/blob/fa390362a556fe156701ee6bdf505411d4f0f7c5/crates/sase_core/src/bead/mutation/create.rs#L73).
- **S8 — Current link projections and relation restrictions:** [projection fan-out](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/artifact_links/projection/_entry.py#L26), [agent implements projection](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/artifact_links/projection/_agent_bead.py#L29), [awaits projection](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/artifact_links/projection/_agent_wait_bead.py#L14), [Rust relation registry](https://github.com/sase-org/sase-core/blob/fa390362a556fe156701ee6bdf505411d4f0f7c5/crates/sase_core/src/artifact_link/relation.rs#L145).
- **S9 — Approval/launch/rollback lifecycle:** [host approval bridge](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/_plan_approval_epic.py#L22), [leased launch monitor/proc](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/bead/epic_launch.py#L154), [epic graph construction and rollback](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/bead/epic_from_plan.py#L237).
- **S10 — Existing notification handoff and identity:** [handoff model](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/bead/epic_launch_handoff_model.py#L11), [project/timestamp key](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/bead/epic_launch_handoff_io.py#L23), [deferred notification persistence](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/bead/epic_launch_handoff.py#L57).
- **S11 — Relocation re-mints event IDs:** [remapped_event](https://github.com/sase-org/sase-core/blob/fa390362a556fe156701ee6bdf505411d4f0f7c5/crates/sase_core/src/bead/events/merge.rs#L371).
- **S12 — Existing wait presentation:** [list row status](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/ace/tui/widgets/_agent_list_render_agent_status.py#L194), [detail wait lanes](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/ace/tui/widgets/prompt_panel/_agent_wait_section.py#L119), [documented visual grammar](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/docs/ace.md#L6126).
- **S13 — Presentation/scanner/publication seams:** [wait map cache](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/ace/tui/_agent_wait_cache.py#L26), [bead status cache](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/ace/tui/models/agent_wait_beads.py#L16), [portable inventory metadata](https://github.com/sase-org/sase/blob/620e5310d48952dc5994d0eca91d750fd9789785/src/sase/agents_sync/inventory_io.py#L29), [Rust waiting marker wire](https://github.com/sase-org/sase-core/blob/fa390362a556fe156701ee6bdf505411d4f0f7c5/crates/sase_core/src/agent_scan/wire.rs#L980).
- **S14 — Rust typed launch and editor surfaces:** [typed wait parser](https://github.com/sase-org/sase-core/blob/fa390362a556fe156701ee6bdf505411d4f0f7c5/crates/sase_core/src/agent_launch/typed_units.rs#L1038), [agent-to-logical resolution](https://github.com/sase-org/sase-core/blob/fa390362a556fe156701ee6bdf505411d4f0f7c5/crates/sase_core/src/agent_launch/plan_resolution.rs#L91), [wait wire variants](https://github.com/sase-org/sase-core/blob/fa390362a556fe156701ee6bdf505411d4f0f7c5/crates/sase_core/src/agent_launch/wires.rs#L512), [editor directive metadata](https://github.com/sase-org/sase-core/blob/fa390362a556fe156701ee6bdf505411d4f0f7c5/crates/sase_core/src/editor/directive/metadata.rs#L680).

## Recommended solution

Implement `%wait(agent, for_epic=true|false)` as an occurrence-scoped dependency policy. Default newly authored explicit agent targets to `true`, while preserving old stored waits and generated sequencing dependencies as completion-only. Bind the epic condition to the exact producer generation that satisfies the agent condition; record its direct epic outputs at creation/host launch and explicitly seal discovery, including a proven empty result. Require all discovered epics to close, using existing closure semantics and owner-aware routing. Put the predicate and state transition in Rust and use it in every admission path. Project creator and waiter artifact links from those facts, and show a persistent, readable `WAITING · agent` → `WAITING · epic approval` → `WAITING · epic <id>` progression in the existing TUI vocabulary.

The boolean is worth adding. The output-publication boundary is the part that makes it dependable.
