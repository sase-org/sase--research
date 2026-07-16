---
create_time: 2026-07-16
updated_time: 2026-07-16
status: research
---

# Parallel Agent-Family Children for Epics and Research Swarms

## The Question

Can multiple agent children in the same `--` family run in parallel, so that (1) an epic's phase agents plus its land
agent, and (2) the chezmoi `research_swarm`, each collapse to **one root row** on the Agents tab whose panel
**consolidates the metadata of every member**?

Every file:line reference below was read directly against the working tree on 2026-07-16, and the naming claims in
§3.1 were verified by executing the parser (see § Verification Log).

## Headline

**Parallelism is not the blocker. It already works — both motivating use cases run in parallel in production today.**

The real gap is that SASE has **three uncoordinated grouping mechanisms** and the two use cases picked the two that
*don't* produce a root row:

| Mechanism | Spelling | What it produces | Parallel-safe? | Metadata rollup? |
| --- | --- | --- | --- | --- |
| **Family** | `foo--code` | **Root row + folded child rows** | Data model: yes. Attach path: no. | Partial (time, model) |
| **Hood** | `foo.bar` | Navigation index only (`~` modal, neighbor count) | Yes (no runtime baggage) | None |
| **Tag** | `%g:foo` | A whole side **panel** per tag | Yes (no runtime baggage) | Banner counts only |

Both use cases currently use **tag + hood**. Tags make the space problem *worse*: `%group:<epic_id>`
(`src/sase/bead/work.py:341-342`) gives every epic its own panel with N+1 rows in it. The user wants that panel to be
one row.

So the work is **not** "let family members run in parallel." It is:

1. **Give the already-parallel members family membership** (a metadata write, not a scheduler change), and
2. **Make the root row a real aggregate** rather than a mirror of one child (this is the substantive work), and
3. **Add the metadata that "consolidate" implies but that does not currently exist at all** (tokens/cost — see §4.4).

Feasibility: **high for use case 1, medium for use case 2**, on the order of a focused epic — *provided* the four
blockers in §4 are addressed. Two of them are latent-bug territory, not features.

## 1. Relationship to Prior Research

This report is a **narrow, implementation-focused follow-up** to
`202607/agent_family_unification_consolidated/agent_family_unification_consolidated.md` (2026-07-16), which asked the
broad question "what should a family *be*?" and answered with a five-axis run model (run group / node / dependency
edge / display relation / controller).

This report does **not** relitigate that. It accepts the consolidated report's core conclusion — *grouping and
scheduling must be orthogonal; `group_id`/`node_id` metadata should be authoritative; `--` names and
`parent_timestamp` demoted to projections* — and asks a smaller question: **given two concrete, already-parallel
workloads, what is the shortest correct path to one root row with consolidated metadata?**

The most important delta: the consolidated report frames this as "inverting one-process → N-rows into N-processes →
one-group," and warns that the obvious implementation path hits a `release_workspace` race. Both are correct. But it
somewhat **understates the good news** for these two specific use cases, because both already sidestep the plan-chain
process model entirely — they never touch `spawn_custom_role_followup`, `%n(parent, suffix)`, or the axe `while True`
loop. See §3.

Also relevant, and explicitly superseded on the point it covers: `202607/dynamic_agent_families_v1_v2_design.md:38,137`
records "root bash/python rows" as a v1 non-goal. That cut does not constrain this initiative — neither use case needs
script roots.

## 2. What the Two Use Cases Actually Are Today

### 2.1 Epic phase agents + land agent (`sase bead work`)

`render_multi_prompt` (`src/sase/bead/work.py:212-282`) emits **one `---`-separated multi-prompt** containing every
phase segment plus a final land segment, and hands it to **a single launch call**
(`src/sase/agent/launch_cwd_bead_work.py:29`, `launch_planned_bead_work_agents`). Per phase (`work.py:249-265`):

```python
lines.append(f"%name:!{assignment.agent_name}")
lines.append(_group_directive(plan.launch_tag_id))   # -> %group:<epic_id>
lines.append("%auto:tale")
if assignment.waits_on:
    lines.append(f"%w:{','.join(assignment.waits_on)}")
lines.append(f"#{work_phase_xprompt.name}:{assignment.bead_id}")
```

The land segment (`work.py:267-280`) carries `%w:` on **every** phase agent (`land_waits_on`, computed in Rust at
`sase-core/crates/sase_core/src/bead/work.rs:182-187`).

**Execution model: spawn-all-at-once, self-gate at runtime.** Every agent is spawned back-to-back as a detached
process; each then blocks *inside its own process* in `wait_for_dependencies` (`src/sase/axe/run_agent_wait.py:303`)
until its named upstream agents finish. Wave partitioning is Kahn-style layering in Rust (`work.rs:125-153`), but the
waves are advisory — `waits_on` is per-phase, so phases within a wave run genuinely concurrently.

**This is the critical fact: N phase agents already run in parallel, each in its own workspace, today.**

### 2.2 `research_swarm` (chezmoi)

Note on naming: **`research_swarm_kiss` does not exist** in the chezmoi repo (or anywhere — `grep -ri kiss` returns
nothing in either repo). The xprompts present are `home/sase/xprompts/research_swarm.md` and
`home/sase/xprompts/old_research_swarm.md`. This report assumes the current `research_swarm.md` is the intended target
(it is the simplified rewrite that replaced the legacy three-agent chain; "KISS" is presumably shorthand for that
rewrite). **Confirm this before implementing.**

Its four segments:

```text
%name:research.@.cdx  %model:@research_a  %g:research  {{ prompt }} #research
---
%name:research.@.cld  %m:@research_b      %g:research  {{ prompt }} #research
---
%name:research.@.final %m:@research_lead  %wait:research.@.cdx %wait:research.@.cld %g:research
---
%name:research.@.image %model:codex/gpt-5.6-sol %wait:research.@.final %g:research #fork:research.@.final
```

Same shape: `cdx` and `cld` run concurrently, `final` waits on both, `image` waits on `final`. Same `%g:` tag. Same
already-parallel execution.

### 2.3 The structural asymmetry between the two

This matters more than anything else in the design, and is the main reason use case 2 is harder:

- **Epic has a natural root.** Phase agents are named `sase-6e.1 … sase-6e.N`; the land agent is named **`sase-6e`** —
  the exact hood ancestor of every phase. A root row already exists as a real process.
- **`research_swarm` has no root.** Members are `research.3.{cdx,cld,final,image}`; **no agent is named
  `research.3`**. The root would have to be either synthetic (a group record with no process) or a designated member
  (`final` is the natural candidate — it is the consolidator — but it starts last and is `WAITING` for most of the
  run).

This is exactly requirement 7 of the consolidated report ("a group record independent of any one process"), and use
case 2 forces the decision that use case 1 lets you dodge.

## 3. Feasibility: What Already Works

### 3.1 The family data model is already a flat star, not a chain — and epic names already parse as families

The glossary's "phases of one CL" framing implies a linear chain. **The persisted model has no chain and no ordering
metadata.** Every member points at the *root*, not at its predecessor: despite the parameter being named
`prev_artifacts_timestamp` (`src/sase/axe/run_agent_helpers_artifacts.py:101`), both call sites pass the root run's
constant timestamp. Grouping is purely `agent.parent_timestamp == parent.raw_suffix`
(`src/sase/ace/tui/models/_agent_status_family.py:195-200`). `find_agent_family()`
(`src/sase/agent/names/_lookup.py:193-231`) defines a family as root + everything whose `parent_timestamp` matches —
flat. The plan → feedback → coder reading order is an **emergent artifact of a chronological sort**
(`src/sase/ace/tui/models/_agent_ordering.py:44-46`), not a declared sequence.

Better still, `is_agent_family_complete()` (`_lookup.py:234-241`) already uses **set semantics** —
`all(member.outcome == _SUCCESS_OUTCOME ...)` — which is exactly right for parallel members.

**And the naming already works for use case 1, by accident.** Child bead IDs are `{parent_id}.{n}`
(`sase-core/crates/sase_core/src/bead/mutation.rs:891-898`), and `_FEEDBACK_SUFFIX_RE`
(`src/sase/plan_chain.py:21`) is `^(?:--|[-.])(\d+)$` — it accepts a **dot**. Executed against the live parser:

```text
'sase-6e.4'   member=True   base='sase-6e'   suffix='--4'    role='feedback'
'sase-6e'     member=False  base=None        suffix=None     role=None
```

**Epic phase agents already classify as family members of the land agent.** `agent_family_base('sase-6e.4')` returns
`'sase-6e'` — the land agent's exact name. This is a genuine head start: the family base needs no new naming scheme,
no `--` migration, and no `INTERNAL_AGENT_NAME_BYPASS` change.

Two caveats, both important:

- **The role is wrong.** They classify as `feedback` rounds, which carries built-in round status rules
  (`docs/agent_families.md:17`) meant for replan iterations. A phase is not a feedback round.
- **This is currently inert but inconsistent.** Rendering linkage is `parent_timestamp`-based
  (`src/sase/ace/tui/models/agent.py:251-262`), and phase agents have `parent_timestamp = None` → they render as
  `AgentChildLinkage.ROOT`. So *the name says family, the linkage says root, and they disagree today.* Membership
  resolution elsewhere prefers metadata but **falls back to name parsing** (`_agent_status_family.py:168-180`;
  `names/_lookup.py:153-168`), so some code paths already see `sase-6e.4` as family. **Whether this causes live
  misbehavior today was not established and should be checked before building on it** — it is either free
  infrastructure or a latent bug, and which one matters.

`research.3.cdx` does **not** parse as a family member (`.cdx` is not a recognized suffix) — use case 2 needs an
explicit decision either way.

### 3.2 Parallel execution is proven; only concurrent *spawning* is serialized

Segments are spawned in a plain `for` loop (`src/sase/agent/multi_prompt_launcher.py:251`;
`src/sase/agent/launch_executor.py:101`) and each `spawn_agent_subprocess()`
(`src/sase/agent/launch_spawn.py:117`) is detached — so they start back-to-back and then run at once. Nothing needs to
change here.

The one hard constraint worth knowing, `src/sase/axe/lumberjack.py:216-227`:

```python
# Run script chops concurrently. Agent launches are sequentialized below
# because launch preparation allocates workspaces before the eventual
# RUNNING-field claim, so same-tick launches can race on one workspace.
```

This is about *concurrent spawning*, which neither use case does. It is a warning against "optimizing" the launch loop,
not a blocker.

### 3.3 Recursive metadata aggregation already exists — for exactly one field

`_aggregate_runtime()` (`src/sase/ace/tui/models/agent_time.py:332-359`) is a real recursive sum over
`runtime_children`, cycle-guarded via a `seen` set of `id()`s, and `_runtime_interval` (`:363-381`) already implements
*aggregate-over-leaf precedence* — a parent with children **ignores its own leaf interval entirely**. This is the
pattern to copy for every other rolled-up field, and it means the traversal edge (`runtime_children`, populated in
`_agent_ordering.py:164-186`) already exists.

### 3.4 Children are hidden by default — the space goal is nearly free

`FoldStateManager` defaults to `FoldLevel.COLLAPSED` (`src/sase/ace/tui/models/fold_state.py:47`), and `_fold_filter.py:52-72`
suppresses children until the user presses `l`. **Once members are family children, the "saves space on the Agents tab"
benefit lands automatically** — no new folding UI required.

## 4. Blockers, by Severity

### 4.1 Root status is a *mirror*, not an aggregate — breaks immediately under parallelism (HIGH)

`_mirror_root_from_child()` (`src/sase/ace/tui/models/_agent_status_apply.py:44-48`) is literally:

```python
parent.status = child.status
copy_missing_display_metadata(parent, child)
```

The root shows **one selected child's status verbatim**. With 8 parallel phases, "which child wins" has no correct
answer, and the recency-as-supersession heuristics throughout `_agent_status_family.py` (`superseded_by_feedback_round`,
`latest_non_workflow_child_launch_by_parent`) assume later-launched = supersedes-earlier, which is false for peers.

This is the single largest piece of real work. It requires a genuine aggregate status (e.g. *any failed → FAILED; any
running → RUNNING; all terminal → DONE*), not a selection.

**Aggravating factor for use case 1:** the land agent *is* the root and *is* a member, and it is `WAITING` while every
phase runs. A naive mirror would show the epic as `WAITING` for its entire active life.

### 4.2 Tokens and cost **do not exist as fields at all** (HIGH — scope risk)

"Consolidate the metadata from all of them" most naturally means cost/tokens. **There is no `tokens` or `cost` field on
`Agent`.** Verified against the full field list in `src/sase/ace/tui/models/_agent_state.py` — nothing. Tokens exist
only per-tool-call, parsed ad hoc from artifact JSON summaries (`src/sase/ace/tui/tools/_entry.py:181`,
`src/sase/ace/tui/widgets/_tools_panel_details.py:239` read `total_tokens` off a tool-response summary).

So "consolidated cost for an epic" is **not a rollup feature — it is a new metric feature**: add the field to
`_agent_state.py`, thread it through `agent_loader.py`, decide the artifact source of truth, cross the `sase-core` scan
wire, *and then* roll it up. This is very likely the largest single line item and it is easy to miss when scoping.

Related trap: `runtime_children` holds only *direct* children and only `step_type == "agent"` main steps plus
follow-ups (`_agent_ordering.py:177-184`) — hidden/bash/python steps are excluded, so a cost rollup over that edge
would **silently undercount**. And `_agent_list_render_cache.py:104` / `tools/cache.py:120` already key on
`runtime_children`; a new aggregate field must join cache invalidation or roots show stale totals.

### 4.3 Slot accounting: family children are slot-exempt (HIGH — capacity bug)

`is_root_user_agent_record` (`src/sase/core/runner_slots/_admission.py:24-32`) backs **both** the running listing
(`src/sase/agent/running_listing.py:219`) and `running_root_agent_count` (`_admission.py:35-54`). `parent_timestamp`
children are exempt from slot accounting — which is correct when a family is one sequential process, and **catastrophic
when it is 8 concurrent ones**. Converting epic phases to family children would make an 8-phase epic bypass
`max_running_agents` entirely.

Listing and admission must be decoupled **before** membership is granted, not after. Recommended answer: parallel family
members **do** count against the global cap.

### 4.4 Kill/cleanup does not cascade to family members (MEDIUM — becomes N orphans)

`_immediate_kill_identities` collects only workflow steps; family members carry `parent_workflow=None` and never match.
Survivable with one process; **N orphaned processes with N**. The dismissal gate *does* check family membership, so the
two paths already disagree today.

### 4.5 Workspace/ChangeSpec — mostly a non-issue here, with one sharp edge (MEDIUM)

The consolidated report's biggest warning is that `%n(parent, suffix)` forces workspace sharing on a running parent
(`src/sase/agent/_family_attach_launch.py:64-74`: `parent_is_running` → `deferred_workspace=True`), and that
`release_workspace` matches on `(workspace_num, workflow, cl_name)` with **no PID predicate**.

**Neither use case goes through that path.** Both are launched by the multi-prompt launcher with independent
workspaces. This report's recommendation (§6) therefore deliberately **does not touch `%n`** — granting membership via
metadata avoids the entire family-attach serialization mechanism.

The sharp edge that remains: if a future refactor ever models "one family = one `workflow_name`," the PID-less
`release_workspace` match means **the first member to finish silently releases every sibling's workspace claim**. It is
masked today only because `workflow_name` embeds a per-slot timestamp (`src/sase/agent/launch_executor.py:103`). Leave
that masking in place, or PID-scope the release first.

Worth noting for use case 1: epic phases **already share one ChangeSpec** (`work.py:236-237` — the first phase creates
it via `#pr`, later phases and the land agent target it directly). So `cl_name` inheritance — the thing family attach
forces — is already true here. Parallel writers racing `STATUS:` (last-writer-wins) and `COMMITS:` (positional
numbering) is a **pre-existing** condition of `sase bead work`, not something this change introduces.

### 4.6 The metadata panel is strictly single-agent (MEDIUM)

`build_header_text()` (`src/sase/ace/tui/widgets/prompt_panel/_agent_display_header.py:149-569`) reads only `agent.*`
fields, and selection is a plain `self._agents[self.current_idx]` lookup
(`src/sase/ace/tui/actions/agents/_selection.py:17-25`). There is no root-specific panel — root vs child differences are
just conditional rows. Selecting a *collapsed banner* doesn't aggregate either; it shows the **first** agent's metadata
(`_agent_list_build.py:132-163`).

"See all the metadata for the Epic on a single panel" therefore needs a genuinely new render branch.

## 5. Design Decisions Required

Ordered by how badly getting them wrong hurts.

1. **Aggregate status semantics.** What does the root show when 3 phases run, 1 failed, and the lander waits? Proposed:
   *any failed → FAILED; else any running → RUNNING; else any waiting → WAITING; else DONE*. Failure must be visible at
   the root or folding actively hides problems — the opposite of the goal.
2. **Root identity for rootless groups (use case 2).** Synthetic group record, or designate a member? These diverge
   permanently; §6 recommends deferring by not converting use case 2 in phase 1.
3. **Does the root double as a member?** For epics the land agent is both. Today a bare-named root that gains a sibling
   renders as `foo--0` in memory only (`_agent_status_family.py:627-660`). Does `sase-6e` appear once (as root) or
   twice (root + `sase-6e--0` child)?
4. **What "consolidated metadata" means concretely.** Cost/tokens (new field, §4.2), elapsed (exists), model set
   (union exists), status (needs aggregation), ChangeSpec/branch, bead IDs, per-member links? Scope this explicitly —
   it silently ranges from ~1 to ~5 beads.
5. **Phase role vs feedback role.** `sase-6e.4` currently classifies as `role='feedback'`. Add a `phase` role, or
   overload? A new role means new status rules and a `sase-core` wire change.
6. **Slot policy.** Confirm parallel members count against `max_running_agents` (§4.3), and decide whether groups get
   their own concurrency cap.
7. **Do tags survive?** If an epic becomes one family root row, `%group:<epic_id>` becomes redundant — a panel
   containing one row. Drop the tag, or keep both? Keeping both means two grouping mechanisms fighting over the same
   agents.
8. **Rollup vs. hood.** `sase-6e.4`'s hood ancestor already *is* `sase-6e` (`agent_hoods.py:37-57`). Should the root
   row be derived from the hood tree instead of family metadata? (§6 says no — but it is a legitimate alternative and
   the consolidated report's conflict resolution 2 explicitly reconciles the two by separating display from execution.)

## 6. Recommended Solution

**Grant family membership via metadata to agents that already run in parallel; make the root a real aggregate; do not
touch `%n`, the axe loop, or the scheduler.**

The insight that makes this cheap: **the family data model is already a flat star (§3.1) and the agents already run in
parallel (§3.2).** The only thing standing between today and the desired UI is that nobody sets `parent_timestamp` /
`agent_family` on these members, plus a root that aggregates instead of mirrors.

Concretely, staged so each phase is independently shippable:

**Phase 0 — decouple listing from admission (§4.3).** Split `is_root_user_agent_record` into its two callers and make
parallel family members count against `max_running_agents`. **Do this first**; it is the one blocker that turns into a
capacity incident rather than a cosmetic bug. Independently correct regardless of what follows.

**Phase 1 — real aggregate root status (§4.1).** Replace `_mirror_root_from_child` with an aggregate for roots that
have ≥2 concurrently-active children, following the `_aggregate_runtime` precedent (`agent_time.py:332-359`) — including
its cycle guard and aggregate-over-leaf rule. Keep the mirror for the single-child sequential plan chain so existing
behavior is bit-for-bit unchanged. **Guard this with a golden-equivalence harness over the current plan/question flows
before touching it** (the consolidated report's stage 1, and `_agent_status_family.py` is 664 lines of accumulated
heuristics — this is the file most likely to produce a subtle regression).

**Phase 2 — cascade kill to family members (§4.4).** Make `_immediate_kill_identities` match family members. Cheap, and
must land before N-way membership or a killed epic leaks N processes.

**Phase 3 — epic membership (use case 1).** Have `epic_work_segment_env` (`src/sase/bead/work.py:285`) write
`agent_family` / `parent_timestamp` / `agent_family_role` metadata pointing every phase at the land agent, alongside the
bead env it already writes. Add a `phase` role rather than inheriting `feedback` (§5.5). **Resolve the §3.1 caveat
first** — determine whether `sase-6e.4`'s existing accidental family classification is inert or already causing
misbehavior. Drop `%group:<epic_id>` in the same change (§5.7) so two mechanisms don't fight.

Note this needs **no naming change** — the bead-ID names already produce the right family base.

**Phase 4 — the consolidated panel (§4.6).** Add an aggregate render branch to `build_header_text` for roots with
parallel members. Ship it with *existing* fields (elapsed, model union, status, per-member list) and **treat cost/tokens
as a separate, explicitly-scoped effort** (§4.2) rather than letting a new metric subsystem ride in on a UI change.

**Phase 5 — `research_swarm` (use case 2), only if phases 0-4 prove out.** This forces the rootless-group decision
(§5.2). Recommended when you get there: **designate `research.@.final` as the root** via explicit family metadata
rather than building a synthetic group record — `final` already `%wait`s on every sibling, so it is the natural
aggregation point, and it makes use case 2 structurally identical to use case 1 (lander = root). A synthetic group
record is the architecturally purer answer and the consolidated report's requirement 7 argues for it, but it is a much
larger change and should be justified by a third use case, not this one.

**What this deliberately does not do**, and why:

- **No `%name(wait=...)`.** The consolidated report resolved this: `%name` blanket-rejects kwargs
  (`_family_attach_directives.py:22-28`), and grouping should not carry scheduling side effects. `%wait` already
  expresses the ordering both use cases need.
- **No durable graph scheduler.** Both use cases already self-gate correctly via `%wait`. Building a scheduler here
  would be solving a problem neither has.
- **No touching `%n` / family attach.** That path's workspace-sharing and `release_workspace` hazards (§4.5) are real,
  and this recommendation routes around them entirely rather than fixing them.
- **No hood-derived roots.** Hoods are display-only and deliberately carry no metadata; deriving execution-relevant
  rollup from a name prefix recreates name-inference under a new delimiter (consolidated report, conflict resolution 2).

**Honest assessment of the risk.** The pitch "it's just metadata" is true for membership and false for the whole
initiative. The cost sits in three places: `_agent_status_family.py` is 664 lines of recency heuristics that all assume
sequence and will fight an aggregate (§4.1); tokens/cost is an entire missing subsystem masquerading as a rollup
(§4.2); and the slot exemption is a live capacity bug that membership would activate (§4.3). Phases 0-2 are worth doing
**even if the grouping feature is dropped** — which is a good sign about the sequencing.

## 7. Open Questions

1. Is `research_swarm.md` the intended "research_swarm_kiss"? Nothing by that name exists in either repo.
2. Does `sase-6e.4`'s existing accidental `role='feedback'` family classification (§3.1) cause any live misbehavior
   today, or is it fully inert? This changes Phase 3 from "grant membership" to "fix a latent bug, then grant
   membership."
3. Does "consolidate the metadata" require cost/tokens (§4.2)? If yes, that is the long pole and deserves its own bead.
4. For an epic, should the land agent render once (root only) or twice (root + `--0` child)?
5. Should the aggregate root status distinguish "3/8 phases done" (progress) from a single status token? A count is far
   more useful for an 8-phase epic than `RUNNING`, but it is a new render concept.
6. When a phase fails, should the root show FAILED even though the lander may still be `WAITING` forever? (Related: the
   consolidated report's requirement 1 — failed dependencies currently never satisfy a wait, so the lander waits
   indefinitely rather than being cancelled. That is a pre-existing `sase bead work` gap this change would make
   *visible*, which is an argument for doing it.)
7. Does this need to reach mobile/Telegram/CLI listings, or is a TUI-only rollup acceptable for v1? The Rust-core
   litmus test says group identity and aggregate status are shared domain behavior (`../sase-core`), which would pull
   `sase-core` into Phases 1 and 3.

## Verification Log

Executed against the working tree, 2026-07-16 (`.venv/bin/python`):

```text
'sase-6e.4'          member=True  base='sase-6e'   suffix='--4'    role='feedback'
'sase-6e.3'          member=True  base='sase-6e'   suffix='--3'    role='feedback'
'sase-6e'            member=False base=None        suffix=None     role=None
'research.3.cdx'     member=False base=None        suffix=None     role=None
'research.3.final'   member=False base=None        suffix=None     role=None
'sase-6e--4'         member=True  base='sase-6e'   suffix='--4'    role='feedback'
'foo--code'          member=True  base='foo'       suffix='--code' role='code'
'sase-6e.4.2'        member=True  base='sase-6e.4' suffix='--2'    role='feedback'
```

Confirms: dot-separated child bead IDs already canonicalize to `--`-family membership; the land agent's bare name is
not itself a member; `research_swarm`'s dotted names are not members.

## Key References

- **Prior research:** `202607/agent_family_unification_consolidated/agent_family_unification_consolidated.md` (the
  broad model question); `202607/dynamic_agent_families_v1_v2_design.md` (v1/v2 scope; its root-script non-goal does
  not constrain this work); `202606/dynamic_agent_families_xprompt_workflows_consolidated.md` (family state machine).
- **Epic orchestration:** `src/sase/bead/work.py:212-282` (render), `:285` (segment env), `:341` (`%group`);
  `src/sase/bead/cli_work_handler.py:217` (the spine); `src/sase/agent/launch_cwd_bead_work.py:29` (launch adapter);
  `sase-core/crates/sase_core/src/bead/work.rs:125-205` (waves + naming), `bead/mutation.rs:891-898` (dotted child IDs).
- **Family model:** `src/sase/plan_chain.py:9,21,308-323`; `src/sase/agent/names/_lookup.py:193-241`;
  `src/sase/agent/_family_attach_launch.py:64-74`; `docs/agent_families.md`.
- **ACE rows/rollup:** `src/sase/ace/tui/models/agent.py:251-262` (linkage);
  `src/sase/ace/tui/models/_agent_status_apply.py:44-48` (mirror); `src/sase/ace/tui/models/agent_time.py:332-381`
  (the aggregation precedent); `src/sase/ace/tui/models/_agent_status_family.py` (664 lines of heuristics);
  `src/sase/ace/tui/models/fold_state.py:47`; `src/sase/ace/tui/models/_agent_state.py` (no cost/token fields);
  `src/sase/ace/tui/widgets/prompt_panel/_agent_display_header.py:149-569` (single-agent panel).
- **Grouping mechanisms:** `src/sase/ace/tui/models/agent_hoods.py:37-57` (hoods);
  `src/sase/ace/tui/models/agent_panels.py` (tag panels); `src/sase/xprompt/_directive_types.py:68,117-120`
  (`%g` → `tag`).
- **Capacity/launch:** `src/sase/core/runner_slots/_admission.py:24-54`; `src/sase/axe/lumberjack.py:216-227`;
  `src/sase/agent/multi_prompt_launcher.py:251`; `src/sase/agent/launch_spawn.py:117`;
  `src/sase/axe/run_agent_wait.py:303`.
- **Swarm source:** chezmoi `home/sase/xprompts/research_swarm.md` (and `old_research_swarm.md`).
- **Perf constraint:** `sase/memory/tui_perf.md` — read before touching loaders; no added synchronous I/O.
