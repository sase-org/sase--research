---
create_time: 2026-07-16
updated_time: 2026-07-16
status: research
---

# Parallel Agent-Family Children for Epics and Research Swarms (Consolidated)

Consolidates two independent research reports (`__a`: codex, `__b`: claude, both 2026-07-16) plus the lead
researcher's own verification pass. Both source reports are preserved alongside this file. Line references were
checked against the working tree on 2026-07-16; claims marked **[lead-verified]** were independently re-confirmed by
the lead researcher, including several that resolve open questions left by the source reports.

## The Question

Can multiple agent children in one family run in parallel, so that (1) an epic's phase agents plus its land agent and
(2) the chezmoi `research_swarm` each collapse to one root row on the Agents tab, with the root panel consolidating
the metadata of every member?

## Headline

**Feasible, and parallel execution is not the blocker — both use cases already run their members in parallel in
production.** Both reports independently converged on this. `sase bead work` renders one `---`-separated multi-prompt
(every phase segment plus a final land segment, `src/sase/bead/work.py:212-282`) and launches it in a single call;
each agent is spawned detached and self-gates inside its own process via `%w` waits
(`src/sase/axe/run_agent_wait.py:303`). The chezmoi `research_swarm.md` has the same shape: two researchers in
parallel, a lead that waits on both, an image agent that waits on/forks the lead. No new scheduler, no change to the
axe loop, and no change to `%n(parent, suffix)` is needed.

The real work splits into three parts:

1. **Membership** — give the already-parallel members family membership without inheriting the serial plan-chain
   baggage (a metadata/identity design problem, mostly cheap);
2. **Aggregation** — make the root row and root panel a true aggregate instead of a mirror of one child (the
   substantive TUI + core work); and
3. **Pre-existing hazards that membership activates** — slot-accounting exemption, kill cascade, and wait-failure
   parking (two of these are latent capacity/orphan bugs, not features).

Feasibility: high for the epic (use case 1), medium for the research swarm (use case 2). The epic needs **no naming
change at all** (see §3); the swarm forces the "rootless group" decision and needs a new authoring primitive.

**Naming caveat:** `research_swarm_kiss` does not exist in the chezmoi repo — both researchers confirmed
independently (grep + history). Only `home/sase/xprompts/research_swarm.md` and `old_research_swarm.md` exist. Both
reports assumed the current `research_swarm.md` (the simplified "KISS" rewrite) is the intended target. **Confirm
before implementing.**

## 1. What Exists Today

### 1.1 Three uncoordinated grouping mechanisms — and both use cases picked the wrong two

| Mechanism | Spelling | Produces | Metadata rollup |
| --- | --- | --- | --- |
| **Family** | `foo--code` + `agent_family`/`parent_timestamp` metadata | Root row + folded child rows | Partial (elapsed time, model backfill) |
| **Hood** | `foo.bar` | Navigation only (`~` modal, neighbor count); no rows, no grouping | None |
| **Tag** | `%g:foo` | A whole side panel per tag | Banner counts only |

Both use cases currently use tag + hood. Tags make the space problem worse: `%group:<epic_id>`
(`src/sase/bead/work.py:341-342`) gives every epic its own panel containing N+1 rows.

### 1.2 The family data model is already a flat star — parallel-ready

The persisted model has no chain and no ordering metadata. Every member points at the root via
`parent_timestamp == root.raw_suffix` (`_agent_status_family.py:195-200`; `names/_lookup.py:193-231`). The
plan → feedback → coder reading order is an emergent artifact of a chronological sort
(`_agent_ordering.py:44-46`). Family completion already uses set semantics
(`is_agent_family_complete`, `_lookup.py:234-241`: all members succeeded) — exactly right for parallel members.

What is *not* parallel-ready is everything layered on top: `%n(parent, suffix)` bundles four behaviors — membership +
name, lineage (`parent_timestamp`), an implicit success dependency on the parent, and workspace inheritance/deferral
when the parent is running (`_family_attach_launch.py:64-74`). Correct for a serial handoff; wrong for peers. Both
reports agree: **route around `%n`, don't extend it** (no `wait=false` boolean — grouping must not carry scheduling
side effects, per the prior unification report).

### 1.3 The epic already parses as a family, by accident — and it is inert today

Report `__b`'s best find, verified by executing the parser: child bead IDs are `{parent}.{n}`
(`sase-core .../bead/mutation.rs:891-898`) and the feedback-suffix regex accepts a dot, so:

```text
'sase-6e.4'  member=True   base='sase-6e'  suffix='--4'  role='feedback'
'sase-6e'    member=False  (the land agent is the family base, not a member)
```

`agent_family_base('sase-6e.4')` returns exactly the land agent's name. The epic needs no rename, no `--` migration,
no `INTERNAL_AGENT_NAME_BYPASS` change.

**[lead-verified] This accidental classification is fully inert today** — resolving `__b`'s top open question:

- `agent_family` metadata is written in exactly two places, both plan-chain/attach paths
  (`run_agent_directives.py:380`, `run_agent_helpers_artifacts.py:87`) — never for epic agents.
- Every behavioral consumer keys off metadata or `parent_timestamp` (both unset for epic agents): row linkage
  (`agent.py:251-262`), grouping, supersession heuristics (all gated on `parent_timestamp` + planner roles),
  slot admission, wait resolution (`_iter_family_members` matches on metadata only, `_lookup.py:152-190`).
- `find_agent_family()` refuses member-shaped names outright (`_lookup.py:193-201` returns `None` when
  `is_agent_family_member(name)`), so a phase's `%w:sase-6e.1` stays an exact-name lookup.
- The single name-parse fallback in the TUI (`agent_family_name`, `_agent_status_family.py:168-180`) has one caller,
  gated to plan workflows.
- `workflow_name` for multi-prompt slots is `ace(run)-<timestamp>` (`launch_executor.py:103`), so the
  `_family_base_from_meta` workflow-name path cannot accidentally match either.

So Phase "grant membership" is a clean state change, not a bug fix — but the moment metadata is written, dormant
machinery wakes up, for better and worse (§2).

### 1.4 The structural asymmetry between the two use cases

- **The epic has a natural root**: the land agent is named the epic bead ID (`sase-6e`), the exact family base of
  every phase. A real process already exists to be the root row.
- **The research swarm has no root**: members are `research.<N>.{cdx,cld,final,image}`; no agent is named
  `research.<N>`, and dotted swarm names do not parse as family members (`.cdx`/`.final` are not recognized
  suffixes). The root must be either a designated member (`final`, the consolidator) or a synthetic group record.

This asymmetry is why both reports sequence the epic first. Use case 2 also has an authoring gap use case 1 doesn't:
the swarm is user-authored xprompt text, and **no directive exists today that declares membership without `%n`'s
attach semantics** — so the swarm needs a new membership-only directive regardless of which persistence model wins
(§4).

**[lead-verified] A later segment can be the root.** All slot timestamps are preallocated before any spawn
(`launch_executor.py:87-94`, `LaunchTimestampBatchAllocator.allocate`), so phase segments can carry
`parent_timestamp` (or manifest references) pointing at the land/lead slot even though it launches last and runs
last.

## 2. What Breaks: Blockers by Severity

### 2.1 Slot accounting: family children are slot-exempt (HIGH — capacity bug)

`is_root_user_agent_record` (`src/sase/core/runner_slots/_admission.py:24-31`) excludes any record with
`parent_timestamp` set, and backs both the running listing and `running_root_agent_count`. Correct when a family is
one sequential process; catastrophic when it is 8 concurrent ones — membership would let an epic bypass
`max_running_agents` entirely. **Decouple listing/admission from display parenting before granting membership.**
Consensus: every real member counts toward the global cap; the family container consumes no slot.

### 2.2 Root status is a mirror, not an aggregate (HIGH — the substantive work)

`_mirror_root_from_child` (`_agent_status_apply.py:44-48`) is literally `parent.status = child.status`. With N
parallel phases "which child wins" has no answer, and `_agent_status_family.py` is ~664 lines of
recency-as-supersession heuristics that assume sequence. Aggravating: the land agent (the root) is `WAITING` while
every phase runs — a naive mirror shows the epic as WAITING for its entire active life.

Needs a defined aggregate. Consensus priority: needs-user-input (QUESTION/PLAN) → failed (any required member) →
running (any) → waiting → done (all required members succeeded). Both reports also agree a scalar is insufficient:
show member counts (`2 running · 1 waiting · 1 done`) on the row. The one existing true aggregate is the pattern to
copy: `_aggregate_runtime` (`agent_time.py:332-359`) — recursive over `runtime_children`, cycle-guarded,
aggregate-over-leaf precedence.

### 2.3 Tokens/cost do not exist as fields at all (HIGH — scope risk)

"Consolidate all metadata" most naturally implies cost/tokens. There is no `tokens` or `cost` field on `Agent`
(**[lead-verified]** against `_agent_state.py`); tokens exist only per-tool-call, parsed ad hoc from artifact JSON
(`tui/tools/_entry.py:181`). A consolidated epic cost is a **new metric subsystem** (field + loader + artifact
source of truth + sase-core scan wire), not a rollup. Easiest item to under-scope; keep it out of the v1 panel.

### 2.4 Kill/cleanup does not cascade to family members (MEDIUM — N orphans)

**[lead-verified]** `_immediate_kill_identities` (`actions/agents/_kill_identity.py:44-59`) cascades only to
workflow-step children (`AgentType.WORKFLOW` parent + `parent_workflow` match); family members never match. The
dismissal gate does check family membership, so the two paths already disagree. Survivable with one sequential
process; N orphaned processes with N members. Check whether the newer planner-backed path
(`AgentCleanupPlanWire.cascaded_workflow_children`) covers family members in Rust; extend whichever is authoritative.

### 2.5 Wait failures park dependents indefinitely (MEDIUM — made visible, not caused, by this feature)

**[lead-verified, refining both reports]:** the wait-resolution module does detect failure
(`FAILURE_OUTCOMES = {failed, killed, stopped}`, `is_failed` on candidates), but `WaitDependencyStatus` has exactly
two states — `resolved`/`waiting` — and a failed producer only triggers a fallback search for a *newer* same-name
artifact (`_index.py:350-390`). So a waiter parks until a retry launches a successful replacement; there is no
terminal cancellation. Consequence: a failed phase leaves the land agent WAITING forever; a failed researcher leaves
the lead WAITING forever. This is a pre-existing `sase bead work` gap that a family root makes prominently visible —
an argument for the feature, not against it.

Design note: the park-until-retry behavior is partly a feature (relaunching the failed phase under the same name
unblocks the waiter). Terminal cancellation should therefore key off "the group generation is terminally failed /
superseded," not "first member failure," or it breaks the retry story.

### 2.6 The metadata panel is strictly single-agent (MEDIUM)

`build_header_text` (`prompt_panel/_agent_display_header.py:149-569`) reads only `agent.*` fields; selection is a
plain index lookup; selecting a collapsed banner shows the first agent's metadata. The consolidated panel is a
genuinely new render branch. Current aggregation coverage is uneven (report `__a`'s inventory): replies, tool calls,
SASE context events, output variables, and selected plan-chain timestamps already aggregate over direct children;
**commits, deltas, artifacts, errors, model/workspace identity, and arbitrary timestamps do not union across
members**. The fix both reports endorse: one shared family/group member projection consumed by every panel loader,
tool source, cache key, and action — not more one-off child-to-root copy rules. Watch cache invalidation
(`_agent_list_render_cache.py:104`, `tools/cache.py:120` key on `runtime_children`) and `tui_perf.md` (no new
synchronous I/O in loaders).

### 2.7 Sharp edges to leave alone

- `release_workspace` matches `(workspace_num, workflow, cl_name)` with no PID predicate; it is masked today only
  because each slot's `workflow_name` embeds a per-slot timestamp. Do not refactor toward "one family = one
  `workflow_name`" without PID-scoping the release first.
- Same-tick agent launches can race on one workspace (`lumberjack.py:216-227` deliberately serializes agent chops).
  Neither use case spawns concurrently — don't "optimize" the launch loop.
- Epic phases already share one ChangeSpec; parallel writers racing `STATUS:`/`COMMITS:` is a pre-existing
  `sase bead work` condition, not something this change introduces. Attribute commits/deltas per member so conflicts
  are diagnosable.

## 3. Where the Reports Disagreed, and the Resolution

Both reports agree on the principles: membership must be execution-neutral (no waits, no workspace inheritance, no
slot exemption, no failure propagation implied); explicit identity must be authoritative over name parsing;
`parent_timestamp` demoted to a display projection; the land agent / lead agent are the displayed roots; don't touch
`%n`, the axe loop, or the scheduler. They disagree on the **persistence vehicle**:

- **`__a` (codex): a new persisted run-group manifest** in sase-core — `group_id`, unique `group_instance_id`,
  per-member `node_id`/role, `root_node_id`, required-member completion set — projected by ACE; a `%family`
  membership-only directive for swarms; epic launcher passes the manifest typed, not via prompt text.
- **`__b` (claude): reuse the existing metadata fields** — write `agent_family`/`parent_timestamp`/a new
  `agent_family_role` onto the already-parallel members from `epic_work_segment_env`; no new wire records; defer the
  synthetic-root question by designating `final` as the swarm root.

**Resolution: `__b`'s staged path as the v1 vehicle, `__a`'s manifest as the destination — with three `__a`
principles pulled forward into v1:**

1. **Generation identity comes free in the metadata model**: `parent_timestamp` pointing at a specific land/lead
   artifact timestamp *is* a generation instance ID — `find_agent_family` already selects the newest root
   generation, so a `sase bead work` retry (new land timestamp) naturally starts a fresh generation and old failures
   cannot poison it. This defuses `__a`'s main correctness objection to reusing the star model.
2. **Aggregate status and membership semantics belong in sase-core** (Rust core boundary litmus test: CLI, mobile,
   and web listings need the same group status the TUI shows). Define the aggregate function and any new
   role/membership fields in `sase-core` from the start, even in v1.
3. **Execution-neutrality is enforced, not assumed**: regression tests that adding membership metadata changes no
   waits, workspace numbers, VCS refs, or admission counts (`__a`'s acceptance criteria 1-2, 7).

Two lead-verified findings sharpen the trade-off:

- **[lead-verified] Writing `agent_family` metadata changes `%wait`/`#fork` base-name semantics.** Once members carry
  `agent_family: sase-6e`, `resolve_wait_dependency('sase-6e')` resolves via `is_agent_family_complete` — i.e., a
  wait on the land agent's name becomes "wait for the entire family," and `#fork:sase-6e` resolves to the newest
  *successful member* rather than the land agent. For the epic root this is arguably the desired semantics (`__a`
  recommends exactly this for root waits), but it is a behavior change to document and test, not a free ride.
- **[lead-verified] A first-class `phase` role is a code change, not a metadata write.** Role resolution is
  suffix-centric: `_parse_plan_chain_suffix` (`plan_chain.py:152` ff.) classifies numeric tokens as `feedback` via
  legacy fallbacks *before* consulting stored `agent_family_role`, and returns `None` when `role_suffix` is unset.
  Silver lining: with `role_suffix` unset, the planner-role supersession heuristics (`PLANNER_FAMILY_ROLES =
  {plan, feedback}`) cannot fire on phase members. Adding `phase`/`land` (and later `researcher`/`lead`/`image`)
  roles means touching `plan_chain.py` and its Rust counterpart.

## 4. Design Decisions to Make Before Implementing

Ordered by how badly getting them wrong hurts.

1. **Aggregate status semantics + counts** (§2.2). Decide the priority order and the member-count row treatment.
   Failure must be visible at the root or folding actively hides problems.
2. **Slot policy** (§2.1). Confirm parallel members count against `max_running_agents`; decide whether groups get a
   per-group concurrency cap (defer unless needed).
3. **Scope of "consolidated metadata."** Member table (role, name, status, model, workspace, elapsed) + unions of
   replies/tools/variables/commits/deltas/artifacts/errors with per-member attribution is the v1 contract
   (`__a` §10 has the full field-by-field contract). Tokens/cost is a separately-scoped subsystem (§2.3).
4. **Root identity for the swarm** (§1.4): designated member (`final`) vs synthetic group record. Recommendation:
   designate `final` — it already waits on every sibling, and it makes use case 2 structurally identical to use
   case 1 (lander = root). A synthetic group record is architecturally purer (prior unification report, requirement
   7) but should be justified by a third use case.
5. **Does the root double as a member?** The land agent is both. Decide whether `sase-6e` renders once (root only)
   or twice (root + synthesized `--0` child, cf. `assign_bare_family_root_zero_suffix`,
   `_agent_status_family.py:627-660`). Recommendation: once.
6. **Roles**: add first-class `phase`/`land` roles (code change, §3) rather than inheriting `feedback`; define their
   status rules.
7. **Failure policy** (§2.5): v1 = failure visible in aggregate root status; terminal cancellation of undispatched
   dependents keyed off generation-terminal failure is its own follow-up item (preserve retry-unblocks-waiter).
8. **Does `%group:<epic_id>` survive?** Once the epic is one family row, the per-epic tag panel is redundant.
   Recommendation: drop the tag in the same change so two grouping mechanisms don't fight over the same agents.
9. **Base-name wait/fork semantics** (§3): document and test that `%wait:<root-name>` means whole-family completion
   after membership lands.
10. **Authoring surface for the swarm**: a membership-only directive (`%family(id=…, member=…, role=…, root=…)` —
    grammar TBD) that compiles to membership metadata/manifest and has zero scheduling side effects. Must correlate
    the `@` template token through the existing template group, validate one root + unique members, and surface in
    LaunchApproval previews. The epic launcher does *not* use it — it writes membership typed, from
    `epic_work_segment_env`.
11. **Hood-derived roots — rejected.** `sase-6e.4`'s hood ancestor is already `sase-6e`, but hoods are deliberately
    metadata-free display concepts; deriving rollup from name prefixes recreates name-inference under a new
    delimiter.

## 5. Recommended Solution

**Grant family membership via explicit metadata to agents that already run in parallel; make the root a real
aggregate backed by a sase-core group projection; don't touch `%n`, the axe loop, or the scheduler. Epic first, swarm
second; full run-group manifest only when a use case forces it.**

Staged so each phase is independently shippable (phases 0-2 are worth doing even if the grouping feature is
dropped):

- **Phase 0 — decouple listing from admission** (§2.1). Make parallel family members count against
  `max_running_agents`. The one blocker that becomes a capacity incident rather than a cosmetic bug.
- **Phase 1 — real aggregate root status** (§2.2), defined in sase-core, with member counts. Keep the mirror for
  single-child sequential chains so existing behavior is bit-for-bit unchanged; guard with a golden-equivalence
  harness over current plan/question flows before touching `_agent_status_family.py`.
- **Phase 2 — cascade kill to family members** (§2.4). Cheap; must land before N-way membership.
- **Phase 3 — epic membership (use case 1).** `epic_work_segment_env` writes `agent_family: <epic_id>`,
  `parent_timestamp: <land slot timestamp>` (preallocated, §1.4), and a new first-class `phase` role
  (plan_chain + Rust role change, §3) on every phase; the land agent carries the family base. No naming change.
  Drop `%group:<epic_id>` in the same change. Add the execution-neutrality regression tests and the base-name
  wait-semantics tests (§3).
- **Phase 4 — the consolidated root panel** (§2.6). One shared family-member projection consumed by the panel,
  tools/commits/deltas/artifacts/errors sources, cache keys, and root actions (kill/dismiss/revive/revert scope =
  the member set). Ship with existing fields; tokens/cost is a separate effort (§2.3).
- **Phase 5 — research swarm (use case 2).** Introduce the membership-only `%family` directive (decision 10),
  designate `research.@.final` as root, update chezmoi `research_swarm.md` once the grammar is stable. This is the
  point to revisit whether the accumulated metadata should graduate into `__a`'s full manifest
  (`group_instance_id`/`node_id` wire records) — it becomes worthwhile when synthetic roots, group-scoped actions
  beyond kill/dismiss, or cross-project groups arrive.
- **Follow-ups, not blockers:** terminal cancellation of dependents on generation-terminal failure (§2.5),
  token/cost metrics, group-local reference namespaces, dynamic membership, conditional edges.

### Acceptance criteria for v1 (merged)

1. Two phase/research members hold runner slots and execute concurrently while folded under one root row.
2. Adding/removing membership metadata changes no waits, workspace assignments, VCS refs, or model resolution.
3. The root row is the later-launching land/lead member and appears from launch time.
4. Root status/counts are correct for simultaneous RUNNING/WAITING/QUESTION/DONE/FAILED members; a phase failure is
   visible at the root.
5. Every real member counts toward runner admission; killing the root kills all active members.
6. Root details show every member's replies, tools, variables, commits, deltas, artifacts, and errors with stable
   per-member attribution; child panels remain available.
7. Legacy plan chains and `%n(parent, suffix)` behavior are byte-for-byte unchanged; a `sase bead work` rerun starts
   a fresh generation that old failures cannot poison.

## 6. Open Questions for the User

1. Is `research_swarm.md` the intended "`research_swarm_kiss`"? Nothing by that name exists.
2. Does "consolidate the metadata" require tokens/cost? If yes, that is the long pole and deserves its own epic
   (§2.3).
3. Should the epic root show progress counts ("3/8 phases done") in the row, or only in the panel?
4. Is TUI-only acceptable for v1, or should aggregate group status reach CLI/mobile/Telegram listings immediately?
   (The Rust-core boundary rule pulls sase-core into Phases 1 and 3 either way; exposing it to other frontends is
   then incremental.)
5. Land agent rendered once or twice (decision 5)?

## Appendix: Verification Log (lead researcher, 2026-07-16)

- `_admission.py:24-31` — `parent_timestamp` ⇒ excluded from root admission (also gates on
  `workflow_dir_name == "ace-run"`, no done marker). Confirms §2.1.
- `WaitDependencyStatus` (`wait_dependency_resolution/_types.py:49`) has exactly two states; `is_failed` candidates
  trigger `newer_than` fallback searches (`_index.py:350-390`), never terminal cancellation. Refines §2.5.
- `agent_family` metadata writers: only `run_agent_directives.py:380` (family attach) and
  `run_agent_helpers_artifacts.py:87` (plan chain). `find_agent_family` early-returns for member-shaped names
  (`_lookup.py:193-201`). One TUI name-parse fallback caller, plan-workflow-gated
  (`_agent_status_family.py:555`). ⇒ accidental bead-ID family classification is inert today (§1.3).
- `resolve_wait_dependency`/`resolve_resume_agent_name` (`_lookup.py:264-292`) resolve base names against family
  metadata ⇒ membership metadata changes base-name wait/fork semantics (§3).
- `launch_executor.py:87-103` — batch timestamp preallocation before the spawn loop; slot `workflow_name` defaults
  to `ace(run)-<timestamp>` (§1.4, §1.3).
- `_kill_identity.py:44-59` — immediate kill cascade requires `AgentType.WORKFLOW` + `parent_workflow` match;
  family members excluded (§2.4).
- `_parse_plan_chain_suffix` (`plan_chain.py:152` ff.) — numeric suffixes classify as `feedback` before stored-role
  consultation; unset `role_suffix` ⇒ role `None`; `PLANNER_FAMILY_ROLES = {plan, feedback}`
  (`_agent_status_family.py:28`) (§3).
- No `token`/`cost` fields in `_agent_state.py` (§2.3).
- Report `__b`'s executed-parser log (`sase-6e.4` → base `sase-6e`, role `feedback`; `research.3.*` not members) is
  reproduced in `parallel_family_children_consolidated__b.md` § Verification Log.

## Key References

- Source reports: `parallel_family_children_consolidated__a.md` (codex — run-group manifest design, metadata
  contract §10, acceptance criteria), `parallel_family_children_consolidated__b.md` (claude — grouping-mechanism
  survey, accidental-family find, blocker severity analysis, staged plan).
- Prior art: `202607/agent_family_unification_consolidated/agent_family_unification_consolidated.md` (five-axis run
  model; membership/scheduling orthogonality; both source reports build on it),
  `202607/dynamic_agent_families_v1_v2_design.md`.
- Epic orchestration: `src/sase/bead/work.py:212-341`, `src/sase/bead/cli_work_handler.py:217`,
  `sase-core .../bead/work.rs:125-205`.
- Family model: `src/sase/plan_chain.py`, `src/sase/agent/names/_lookup.py:140-292`,
  `src/sase/agent/_family_attach_launch.py:64-74`, `docs/agent_families.md`.
- ACE rollup/rendering: `_agent_status_apply.py:44-48`, `agent_time.py:332-381`, `_agent_status_family.py`,
  `fold_state.py:47`, `prompt_panel/_agent_display_header.py:149-569`.
- Capacity/launch/wait: `src/sase/core/runner_slots/_admission.py`, `src/sase/axe/lumberjack.py:216-227`,
  `src/sase/agent/launch_executor.py:80-130`, `src/sase/axe/run_agent_wait.py:303`,
  `src/sase/core/wait_dependency_resolution/`.
- Swarm source: chezmoi `home/sase/xprompts/research_swarm.md`.
