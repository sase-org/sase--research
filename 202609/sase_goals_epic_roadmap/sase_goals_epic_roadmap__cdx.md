# Splitting SASE Goals into independently verifiable epics

_Independent research report · researcher cdx · 2026-09-27_

## Executive conclusion

Do **not** implement the Goals design as one epic. It contains at least four distinct
capabilities with different failure modes and different proof obligations:

1. a durable goal data plane;
2. automatic launch-time binding and provenance;
3. claim, review, and human settlement;
4. the Goals user experience.

The attention-policy cutover should be a fifth, separately approved delivery unit, but
it is probably a tale rather than an epic unless implementation uncovers materially
more migration work.

This is not merely a way to shorten the task list. The split makes each landing useful
and reversible, and it prevents one verification result from standing in for unrelated
properties. A storage concurrency test does not verify launch inheritance; a launch
matrix does not verify finalizer evidence; a visual snapshot does not verify
notification deduplication. A single epic would have to prove all of those at once.

The design's P0–P4 rollout is a good dependency sketch, but it is not yet a good epic
partition. In particular, P0 is a grab bag of prerequisites, P1 combines two large
capabilities, and P3 combines presentation with artifact-graph semantics. The proposed
split below turns those phases into outcome boundaries.

## Research basis

I treated `research:202609/sase_goals_design/sase_goals_design.md` as the shared design
input and checked its proposed seams against the current repositories:

- `sase` at `c8a7a5ed3c71`;
- `sase-core` at `297bc1e3364c`.

I did not inspect any other report from the current research swarm.

The current code confirms that Goals starts as a cross-cutting feature rather than an
extension of one existing module:

- There is no Goal domain/CLI today; occurrences of “goal” are primarily plan metadata
  and prose.
- `AgentUnitWire` has launch and finalizer fields but no structured goal binding.
- the Python finalizer registries recognize only `builtin@command` and
  `builtin@commit`, so `builtin@goal` is a real protocol/provider addition rather than
  configuration alone;
- ACE's `TabName` and `TAB_ORDER` are closed over `agents`, `artifacts`, and `services`;
- artifact relations are a closed Rust registry, so `pursues`, `evidences`, `defines`,
  and `follows` are schema changes;
- sidecar auto-sync is already role-generic and can be reused, but the proposed
  co-hosted `goals` role still needs an explicit ownership/resolution contract;
- `parent_agent_name` is consumed by several projections, but normal child launch does
  not yet persist the parent relationship needed by Goal inheritance;
- recent commits have actively refactored tabs, agent lists, deck views, and FINAL
  presentation. That makes an isolated, late UI epic safer than mixing UI changes into
  storage or launch work.

The relevant current seams include `crates/sase_core/src/agent_launch/wires.rs`,
`crates/sase_core/src/finalizer/`, `crates/sase_core/src/artifact_ref/`,
`crates/sase_core/src/artifact_link/relation.rs`, `src/sase/finalizers/`,
`src/sase/_sidecar_auto_sync.py`, `src/sase/agent/`, and
`src/sase/ace/tui/tab_order.py`.

## What makes an epic boundary good here

Each Goals epic should satisfy five tests:

1. **One primary invariant.** Its acceptance suite answers one main question.
2. **A black-box endpoint.** The result can be exercised without code from a future
   epic.
3. **A coherent intermediate product.** Master remains understandable and usable after
   the epic lands.
4. **A bounded rollback.** Reverting or disabling the capability does not corrupt
   another capability's data.
5. **Core-to-Python completeness.** If an epic changes shared behavior, it includes the
   Rust domain rule, PyO3 binding, `sase-core-revision.txt` ratchet, Python caller, and
   tests. Splitting by repository would create unshippable half-epics.

The last point is important. “Rust backend” and “Python integration” are implementation
phases inside an epic, not separate epics. The repository boundary is not a user- or
verification boundary.

## Proposed delivery graph

```text
Epic 1: Goal data plane
          |
          v
Epic 2: Automatic binding and provenance
          |
          v
Epic 3: Claim, review, and settlement
          |
          v
Epic 4: Goals experience and navigation
          |
          v
Cutover: Attention policy and hardening
```

The linear graph is intentional. Parallel implementation would increase merge risk in
the shared wire/config surfaces and make failures ambiguous. Research, fixtures, and
test-case enumeration can happen in parallel, but the product landings should follow
the dependency order.

### Capability matrix

| Delivery unit | New stable behavior after landing | Primary proof | Explicitly excluded |
| --- | --- | --- | --- |
| Epic 1 — data plane | Humans can create, inspect, edit, merge, drop, reopen, and list durable Goals from CLI/API | reducer, two-clone concurrency, repair, scale, artifact resolution | automatic agent binding, claims, TUI |
| Epic 2 — binding | Every LLM turn has exactly one host-selected Goal before spawn; agents can name/adopt drafts | exhaustive launch-shape matrix and provenance audit | claim authority, GoalVerify, notification changes |
| Epic 3 — review loop | Eligible owners can claim with evidence; humans can verify/reject/drop through one durable gate | finalizer ordering, evidence integrity, liveness/role policy, idempotent gate E2E | top-level Goals tab, success-ping suppression |
| Epic 4 — experience | Goals are discoverable and operable in ACE with reliable jumps and artifact relations | interaction tests, visual snapshots, event-loop/performance tests | attention-policy cutover |
| Cutover — attention | Claims replace success pings; answer acknowledgement and Idle notices behave as designed | notification truth table, migration, production-shape soak | new Goal schema or launch rules |

## Epic 1: Durable Goal data plane

**Outcome:** a Goal is a first-class, durable, locally readable object with a stable
`goal:` identity and a complete manual CLI/API. It works even if no agent is ever
launched.

This epic owns:

- Rust Goal ids, wire types, lifecycle reducer, event validation, and deterministic
  conflict rules;
- the append-only event ledger, unsettled markers, repair/doctor logic, and local hot
  projection;
- the storage-owner decision for the co-hosted goals namespace in the beads repository;
- role-generic sync integration, publish/outbox behavior for manual mutations, sync
  freshness, and local-only projects;
- `goal:` artifact parsing/resolution/rendering;
- the manual CLI needed to exercise the model: `new`, `list`, `show`, `edit`, `drop`,
  `reopen`, `merge`, and `doctor`;
- the Rust binding, Python facade, and core revision ratchet.

It should not implement automatic drafts, agent `name`/`adopt`, a finalizer, gates, or
ACE. Keeping those out gives the storage model a clean black-box test surface.

### Epic 1 acceptance

1. A fresh project can create a Goal, read it as `goal:<id>`, edit it, list it while
   unsettled, settle/drop it, and reopen it using only CLI commands.
2. Two independent clones can append concurrent events and converge without a textual
   merge conflict. The documented races (claim-like concurrent transition, drop versus
   mutation, reopen versus settlement) reduce deterministically in property tests even
   if the corresponding user actions are not exposed yet.
3. Killing a writer between event and marker updates is repaired deterministically;
   doctor is idempotent and reports what it changed.
4. Warm list latency meets the agreed p50/p95 targets at 1,000 unsettled Goals.
5. Adding 100,000 settled Goals changes hot-list p95 by no more than the agreed budget,
   and file-open tracing proves that settled item directories are not opened.
6. A project without a shared goals/beads store is clearly `local only` and never
   attempts publication.
7. Unsupported schema versions fail closed with a useful diagnostic; old readers do
   not silently misreduce newer events.

### Why this is one epic

The reducer, ledger layout, marker repair, and projection mutually define the data
contract. Separating them would force a later epic to invalidate the first epic's
performance and concurrency claims. Conversely, no launch or UI behavior is needed to
verify them.

## Epic 2: Automatic binding, lineage, and prompt provenance

**Outcome:** before a provider starts, every LLM turn has exactly one primary Goal
chosen by deterministic host policy; mechanical processes create none. The binding is
durable across every continuation path.

This epic owns:

- the pure Rust binding-resolution ladder and structured `goal_binding` launch wire;
- `goal_id` in agent metadata and `SASE_GOAL_ID` as a convenience only;
- `%goal:<id>` / `%goal:new`, completion, and directive preservation;
- draft creation, the injected intake block, agent `list`/`show`/`name`/`adopt`,
  compare-and-swap naming, and crash auto-naming;
- session, pipe, questions, monitor, gate, retry, plan-to-code, clan, parent, bead,
  routine, epic-phase, lander, and dispatch inheritance;
- actual persistence of parent lineage, not merely projection fields that can read it;
- plan `goal_id` stamping and plan outcome refinement;
- origin prompt/ref/digest capture, root-versus-unit provenance, and the publication
  trigger needed for a named Goal;
- the generated agent skill that teaches name/adopt behavior.

This epic does **not** decide whether an agent may claim, add a new finalizer, generate
a verification gate, or alter completion notifications.

### Epic 2 acceptance

1. The host writes exactly one `goal_id` before provider spawn for direct, plan, bead,
   swarm/clan, `%alt`, `%repeat`, session, child, retry, dispatch, gate, pipe, question,
   and monitor paths.
2. Mechanical procs inherit context where needed but create no new Goal and make no
   Goal decision.
3. A five-member swarm creates one draft, converges on one name, and attaches all five
   contributors to one Goal.
4. A child launched through LaunchApproval inherits the parent's Goal using persisted
   lineage; `%goal:new` is the explicit escape hatch.
5. Epic phase and land turns resolve the same plan-bound Goal without relying on
   `SASE_PLAN`.
6. An adopted draft never appears in the shared ledger, and its prompt excerpt never
   publishes.
7. The stored unit-prompt digest matches `submitted_xprompt.md`; the root prompt and
   “also asked” provenance remain separately reachable.
8. A killed unnamed turn yields one auto-named Idle Goal rather than a missing Goal or
   an unbounded machine-local draft.

### Coherent state after Epic 2

SASE still emits today's success notifications. Goals provide an intent inventory via
CLI, while completion remains agent-centric. This is a useful and understandable
intermediate state: users can inspect, merge, edit, or drop Goals, and no claim is
mistaken for human verification.

## Epic 3: Claim, review, and human settlement

**Outcome:** an eligible owner can turn an active Goal into one durable, evidence-backed
review request, and a human decision deterministically settles or reopens it.

This epic owns:

- `builtin@goal`, its required finalizer configuration, and ordering after
  `builtin@commit`;
- `keep_open` versus `claim`, draft fallback naming, finalizer context/recovery, and
  prepared-monitor completion;
- host-derived owner/contributor/standing-role policy and the “no other contributor is
  live” rule;
- host-collected evidence candidates, symbolic `@commit` and `@reply`, resolvability,
  provenance validation, criterion coverage, check steps, gaps, and receipt snapshots;
- human `verify`, `reject`, and `drop` transitions;
- a single idempotent `GoalVerify` gate per claim, usable from existing gate surfaces,
  CLI, mobile, and Telegram;
- `JumpToGoal` as a stable action contract. Before Epic 4, it may open the canonical
  Goal artifact/report rather than a dedicated tab;
- claim/reject/follow-up semantics and synchronous publication/outbox behavior for
  attention-critical mutations.

It intentionally runs alongside existing `done` notifications. That duplication is a
temporary observation mode, not an unfinished implementation.

### Epic 3 acceptance

1. `builtin@goal` cannot run before a configured predecessor and cannot claim when
   `builtin@commit` failed or deferred.
2. Phase workers and researchers under a pending lead can only `keep_open`; landers and
   unblocked owners can claim.
3. A claim is rejected if another contributor is live, its basis revision is stale, an
   evidence ref is missing/cross-project/unrelated, or a criterion is neither evidenced
   nor listed as a gap.
4. `@commit` and `@reply` resolve only after their durable artifacts exist. A remote
   machine can render an embedded receipt summary without access to the local receipt.
5. Repeated finalizer execution, push retry, or cross-machine observation creates
   exactly one claim event, one gate, and one notification for a claim id.
6. Verify settles; reject records required feedback and reopens; drop settles as
   dropped. Reading or dismissing the notification does none of these.
7. A follow-up during Review retracts the claim; a follow-up after Done creates a new
   Goal linked to the old one.
8. Green prepared-monitor completion can claim with its receipt; red completion keeps
   the Goal open and launches recovery without a false review request.

### Why the finalizer belongs with settlement

A finalizer that can write a claim but cannot create a durable human decision path is
not independently useful. Conversely, the gate is only transport; it should not own
Goal truth. Claim and settlement therefore form one transactional review loop and one
epic.

## Epic 4: Goals experience, relations, and navigation

**Outcome:** a user can discover, understand, and act on every unsettled Goal from ACE,
with reliable jumps between Goals, agents, prompts, plans, and evidence.

This epic owns:

- the top-level Goals tab and its Review, Running, Idle, Standing, and lazy history
  lanes;
- the 30-second review card: You asked, Outcome, Claim, Check it, Evidence, Gaps,
  Agents, Timeline;
- tab badge/inbox integration and stable row ordering;
- Goal chips in Agents, the FINAL Goal card, and grouping by Goal;
- numbered relation-rail jumps and archived-agent fallback;
- the `pursues`, `evidences`, `defines`, and `follows` relation schema/projections;
- repair of `JumpToAgent` to use the existing reveal path for collapsed, grouped, and
  filtered targets;
- all keymap/config/schema updates and visual/accessibility/performance tests.

This epic does not silence success notifications. Users can compare the new Goals
surface with the existing agent-centric signal before attention policy changes.

### Epic 4 acceptance

1. The top-level tab appears in the intended order, persists across restarts, cycles
   correctly, and has an empty state that explains automatic binding.
2. Review, Running, and Idle classification derives from Goal state plus live inventory
   and stays stable while refreshes arrive.
3. Verify/reject/drop/edit/merge/launch/prompt actions operate on the selected Goal and
   refuse stale revisions cleanly.
4. Every rendered agent/evidence/prompt/plan chip has a working numbered jump; a live
   agent hidden by grouping/filtering is revealed, while an archived agent falls back
   to its artifact view.
5. Goal chips and the FINAL Goal card show the same revision/status as the Goals tab.
6. The TUI never performs store reduction or network I/O on the event loop. Cached
   refresh meets the agreed paint budget at the target unsettled count.
7. Visual snapshots cover narrow/wide terminals, every status, gaps/warnings, long
   titles, missing evidence, sync staleness, unpublished state, and non-color status
   cues.

### Why relations land here rather than in Epic 1

`goal:` identity and resolution are data-plane concerns, so they land in Epic 1. The
four new relations exist to power cross-object discovery and navigation. Landing their
closed-registry schema changes with the consumer avoids adding graph vocabulary that
has no visible or testable use yet.

## Final delivery unit: Attention-policy cutover and hardening

**Outcome:** the unit of attention changes from “agent turn ended” to “Goal is ready for
review” without hiding failures or decisions.

This unit owns:

- suppression of successful `JumpToAgent(done)` notifications and their unread
  projection;
- migration/dismissal policy for existing unread success rows;
- answer-only acknowledgement-on-open, including undo, or explicit verify if that
  product decision changes;
- quiet Idle notices, aging nudges, and the final notification priority/chime policy;
- metrics needed to compare notification volume and detect duplicate/lost claims;
- final cleanup of temporary compatibility branches.

It should introduce no new Goal event schema, binding precedence, evidence rule, or TUI
architecture. If it grows any of those, the work belongs back in the owning epic.

### Cutover acceptance

1. The notification truth table is exact: success is silent; claim is loud; keep-open
   is silent; Idle is quiet; failure, questions, approvals, sudo, and triage are
   unchanged.
2. A representative direct answer, research swarm, epic land, prepared monitor,
   dispatch, crash, and rejection each produce exactly the expected attention events.
3. Opening an answer settles only answer-only claims and records `acknowledged`, never
   `verified`; undo is bounded and deterministic.
4. No unread success marker survives migration as a false Goal review, and no error
   marker is lost.
5. A production-shape soak covers all major work shapes and shows no duplicate gates,
   unbound turns, or silently stranded review Goals before the old signal is removed.

This is likely a tale because its domain prerequisites already exist. Treat it as an
epic only if unread migration, multi-client compatibility, or operational rollback
proves large enough to need independent phases.

## Work that should not become standalone epics

### Do not create a “P0 prerequisites” epic

The three proposed P0 items have different consumers:

- parent lineage and prompt publication belong to Epic 2;
- reliable reveal-path navigation belongs to Epic 4.

A prerequisite epic would have no single observable outcome and would be difficult to
close honestly.

### Do not split by repository or layer

Each capability that invokes Rust must include its Rust implementation, binding,
revision pin, Python integration, and end-to-end test. “Core backend,” “Python glue,”
and “CLI” are phases or tasks, not epics.

### Do not make each lifecycle verb an epic

Name, adopt, claim, verify, reject, merge, and reopen are too interdependent to verify
as isolated user outcomes. Group them by authority boundary: agent binding in Epic 2,
agent claim in Epic 3, and human review/settlement in Epic 3.

### Do not make performance a cleanup epic

The O(n unsettled) claim shapes the ledger layout. Its benchmark and file-open proof
must gate Epic 1. TUI paint latency gates Epic 4. Deferring either would allow the wrong
architecture to harden.

## Feature-flag and rollout implications

The design proposes one `goals` flag across P0–P4. That is appropriate only if all work
remains one epic. SASE's flag rules define a beta flag as epic scaffolding that the same
epic removes before it lands. A flag spanning several independently landed epics would
have ambiguous ownership and an indefinitely incomplete Off branch.

For the multi-epic split:

- do **not** create one umbrella `goals` beta flag;
- allow a scoped beta flag inside an individual epic only when that epic needs landed
  internal phases, and remove it before that epic lands;
- keep compatibility by behavior, not a cross-epic hidden branch:
  - after Epic 1, manual Goals work;
  - after Epic 2, automatic Goals work while existing success pings remain;
  - after Epic 3, claims and existing success pings coexist;
  - after Epic 4, the complete UI coexists with existing pings;
  - the cutover removes the old success signal only after observation.

Product choices should be made just before the epic that needs them. Storage
visibility/local-only semantics block Epic 1; standing routine Goals and cross-project
ownership block Epic 2; stale review policy blocks Epic 3; tab position and key choice
block Epic 4; answer acknowledgement blocks the cutover. The other open questions need
not stall earlier work.

## Integration verification across the whole program

Each epic needs its own acceptance suite, but the final program should rerun one small
end-to-end matrix after every landing:

| Scenario | Data plane | Binding | Review | UI | Attention |
| --- | --- | --- | --- | --- | --- |
| direct question | one Goal | draft → named | answer claim | answer card | one acknowledgement signal |
| five-agent research swarm | one Goal | five contributors | lead-only claim | contributor jumps | one claim signal |
| plan → epic → land | one Goal | plan/phase/land continuity | land-only claim | plan/evidence links | approval + one claim |
| monitor success/failure | same Goal | inherited | claim / keep-open | receipt/progress visible | claim / error only |
| crash then relaunch | active Idle Goal | explicit/inherited reuse | no false claim | Idle → Running | error, then eventual claim |
| two-machine race | one reduced state | same Goal | one winning claim/gate | freshness visible | no duplicate signal |

This matrix is an integration safety net, not a reason to reunify the epics. Failures
still point to an owning capability and proof suite.

## Recommended solution

Create **four dependency-ordered epics and one final cutover tale**:

1. **Goal data plane** — land the Rust-owned ledger, conflict/repair semantics, hot
   projection, sync/local-only behavior, manual CLI, and `goal:` artifact identity.
2. **Automatic binding and provenance** — land the host resolution ladder, drafts,
   name/adopt, lineage, plan/clan/session/child continuity, and prompt provenance.
3. **Claim, review, and settlement** — land `builtin@goal`, evidence policy, role and
   liveness authority, prepared-monitor behavior, one idempotent `GoalVerify` gate, and
   human settlement.
4. **Goals experience and navigation** — land the top-level tab, review card, Agents
   integration, relations, reliable jumps, visual coverage, and TUI performance proof.
5. **Attention-policy cutover** — after an observation soak, suppress successful agent
   pings, enable answer acknowledgement and Idle notices, migrate unread state, and
   confirm failures/decisions remain unchanged.

Do not use one cross-epic feature flag, do not create a prerequisite grab-bag epic, and
do not split Rust from Python. Treat the existing design as the program-level contract,
but give each epic its own stable intermediate behavior and its own falsifiable
acceptance suite. This is the smallest partition that materially reduces verification
risk without turning closely coupled lifecycle operations into artificial micro-epics.
