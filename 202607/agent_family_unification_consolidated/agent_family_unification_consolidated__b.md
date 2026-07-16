# Unifying Agent Families as a Grouping, and Migrating YAML Workflows to Swarms

**Date:** 2026-07-16
**Status:** Research — no code changed
**Question:** What conceptual barriers must be designed around to (a) make agent families "just another way
of grouping agents on the Agents tab", and (b) migrate as much xprompt-workflow (YAML) capability as
possible into xprompt swarms (markdown)?

---

## TL;DR — the headline finding

**An agent family is not a group of agents today. It is one OS process.**

`foo--plan`, `foo--q`, `foo--code`, `foo--commit` are not four launched agents — they are four sequential
iterations of a single `while True` loop inside a single process
(`src/sase/axe/run_agent_exec.py:312-342`, `run_execution_loop`). Each iteration writes a new artifacts
directory, and the ACE Agents tab renders one row per directory. The "grouping" you see is a **rendering
artifact of a linked list** (`parent_timestamp`), not a scheduling structure.

`spawn_custom_role_followup` is named misleadingly — it spawns nothing
(`src/sase/axe/run_agent_exec_custom_roles.py:80-83`):

```python
"""Mutate *state* so the next loop iteration runs a custom role."""
role = transition.role
state.current_role_suffix = role.suffix
```

This inverts the framing of the initiative. The goal is not "add a `wait=false` flag so family members can
run in parallel." The goal is **to invert the model from _one process → N rows_ into _N processes → one
group_**. Parallelism is a downstream consequence of that inversion, not the change itself.

Everything below is a consequence. The three hardest barriers are:

1. **The family holds exactly one workspace, one ChangeSpec, and one git branch** — all three are
   per-process and structurally unshareable by concurrent members.
2. **Family members cannot be `%wait` targets** (`src/sase/ace/tui/agent_completion.py:254` excludes every
   child row) — so today there is no way to order them once they *are* separate agents.
3. **A swarm has no runtime.** It is a pure text→N-prompts transform evaluated once, before anything runs.
   Roughly half the YAML capability gap follows from that single fact.

---

## Part 1 — How the three concepts actually work today

### 1.1 Families

| Aspect | Reality | Evidence |
|---|---|---|
| Separator | `AGENT_FAMILY_SEPARATOR = "--"` | `src/sase/plan_chain.py:9` |
| User may type `--`? | **No — reserved.** `validate_user_agent_name` raises `AgentNameSyntaxError` | `src/sase/agent/launch_validation.py:84-91` |
| Sequencing | Event-driven state machine; roles `root → plan → q/feedback → code → commit` | `src/sase/agent_family/standard_plan_chain_definition.py:129-211` |
| Ordering driver | The **user's plan-review choice**, not name order or launch order | `standard_plan_chain_definition.py:101-108` (`_choice_target_role`) |
| Runtime | One process, `while True`, scalar `current_role_suffix: str` | `src/sase/axe/run_agent_exec_types.py:60` |
| Linkage | `parent_timestamp` — a **linked list**, each member pointing at its immediate predecessor | `src/sase/axe/run_agent_helpers_artifacts.py:163-165` |
| Is there an `AgentFamily` class? | **No.** A family is a string key plus the artifact rows carrying it, aggregated on demand | — |

Family membership is metadata-first, name-derived as fallback (`family_base_from_meta`,
`src/sase/core/wait_dependency_resolution/_artifact_state.py:115-131`).

Note the read/write mismatch already present: `create_followup_artifacts` writes a **linked list**
(`parent_timestamp` = immediate predecessor), but `family_candidate` reads a **star** — it picks the newest
root and collects children whose `parent_timestamp == root.timestamp`
(`src/sase/core/wait_dependency_resolution/_index.py:145-194`). This works today only because the standard
chain is shallow and re-points to the root at the plan-accept seam.

### 1.2 Swarms

| Aspect | Reality | Evidence |
|---|---|---|
| Split rule | `---` at line start, outside fenced blocks, after frontmatter | `sase-core/crates/sase_core/src/agent_launch/mod.rs:412-436` |
| Default scheduling | **Parallel.** `_spawn_segments_into` never awaits completion | `src/sase/agent/multi_prompt_launcher.py:253` |
| Sequencing | **Opt-in via `%wait`**, enforced *inside* the spawned child, not by the launcher | `src/sase/axe/run_agent_directives.py:175,324-329` |
| Ordering topology | A real **DAG** — `%wait` is the only multi-value directive | `src/sase/xprompt/_directive_types.py:36` |
| Cross-segment data | `sase var set k=v` → `{{ agents["key"].k }}`, file-mediated, loaded **once** at consumer start | `src/sase/agent/output_variable_context.py:80` |
| Relation to families | **None intrinsic.** Opt-in only via `%n(parent, suffix)` | `src/sase/agent/_family_attach_directives.py:14-45` |
| Runtime | **None.** One text transform, evaluated at dispatch, before anything runs | `src/sase/agent/xprompt_swarm.py:490` |

The docs state the default plainly (`docs/xprompt.md:1868`): *"The `%wait` directives chain them
sequentially; without `%wait` they would run in parallel."*

### 1.3 YAML workflows

Steps: `agent:` / `bash:` / `python:` / `prompt_part:` / `parallel:` / `use:`
(`src/sase/xprompt/workflow_loader_parse.py:96-108`). Control flow: `if:`, `for:`, `repeat:{until,max}`,
`while:`, `parallel:`, `join:`, `on_error:`, `finally:`, `hitl:`. Data flow: an **in-process Python dict**
(`self.context`) rendered through Jinja2 with `StrictUndefined`
(`src/sase/xprompt/workflow_executor_utils.py:47`).

The critical asymmetry, and the reason these two systems are **complementary rather than ordered**:

> YAML `agent:` steps call `invoke_agent()` **synchronously in-process**
> (`src/sase/xprompt/workflow_executor_steps_prompt.py:331`). They are not independently scheduled, cannot
> be `%wait`-ed on individually, and get no workspace allocation.

That is precisely why `xprompts/refresh_docs.yml:85` and `xprompts/fix_just.yml:43` use **python steps that
shell out to launch scripts** when they need real background agents. YAML has control flow but fake agents;
swarms have real agents but no control flow. Unification must resolve that, not paper over it.

**The dominant real-world YAML idiom is `deterministic gate → conditional agent`** — visible in
`refresh_docs.yml`, `audit_recent_bugs.yml`, `audit_recent_improvements.yml`, and most clearly in
`fix_just.yml`: four hidden bash gates → a python `decide_fixers` step → three mutually-exclusive
`if:`-gated fixers. Any swarm that cannot express this cannot absorb the existing corpus.

---

## Part 2 — The conceptual barriers

### Barrier 1 — "Family" currently means two incompatible things

This is the root ambiguity, and I think it is the decision everything else hangs from.

- **Family-as-phases** (the standard plan chain): `plan` and `code` are *phases of one CL*. They share a
  ChangeSpec, a branch, and a workspace **on purpose**. They are sequential by definition. Parallelism here
  is meaningless — you cannot review a plan concurrently with implementing it.
- **Family-as-group** (what you are asking for): peers that happen to be rendered together. Parallelism is
  the *point*. They should have their own workspaces and probably their own ChangeSpecs.

These want opposite defaults on every axis: tree sharing, CL identity, ordering, failure propagation. A
single `wait=<bool>` flag cannot straddle them, because the flag's real meaning silently changes depending
on which kind of family you are in.

**Recommendation:** name the two things separately before writing code. "Family" should probably keep
meaning phases-of-one-CL, and the grouping concept you want is closer to a promoted, first-class version of
**agent hoods** (`.`), which are already display-only and already parallel-safe
(`src/sase/ace/tui/models/agent_hoods.py:37-57`). Hoods are the existing "just a grouping" concept, and they
carry zero runtime baggage. The unification may be *hoods absorbing families' rendering*, not *families
absorbing swarms' parallelism*.

### Barrier 2 — Workspace exclusivity (the sharpest hazard)

The workspace claim is a line in the ChangeSpec `RUNNING:` field, keyed by PID
(`src/sase/running_field/_model.py:44-56`), and exclusivity is enforced in Rust
(`sase-core/crates/sase_core/src/agent_launch/mod.rs:1737-1753`):

```rust
if request.workspace_num != 0 {
    for line in running_claim_lines(&lines) {
        if let Some(existing) = WorkspaceClaimLine::parse(line) {
            if existing.workspace_num == request.workspace_num {
                return claim_plan(..., Some(format!("workspace #{} is already claimed", ...)), false);
```

`run_execution_loop` never touches the workspace — `ctx.workspace_dir` is a frozen field
(`src/sase/axe/run_agent_exec_types.py:18-19`). So every role in a family inherits one claim, and
`create_followup_artifacts` bakes the assumption into a comment: *"follow-up agents run in the same
workspace"* (`src/sase/axe/run_agent_helpers_artifacts.py:118-141`).

Three concrete ways parallel members break this:

1. **`run_sase_hg_clean` wipes uncommitted work at startup** (`runner_workspace.py:118`). A second member
   entering `prepare_workspace` destroys the first member's work-in-progress into a backup diff.
2. **`clear_stale_git_index_lock` deletes a *live* sibling's lock** once it is >15s old
   (`runner_workspace.py:48-83`). Its docstring states the assumption outright: *"This runs against a
   workspace we have exclusively claimed."*
3. **`release_workspace` has no PID predicate** — it matches on `(workspace_num, workflow, cl_name)` and
   removes **every** matching line (`sase-core/crates/sase_core/src/agent_cleanup/execution.rs:207-222`).

Point 3 deserves emphasis because it is a **trap laid directly on the obvious implementation**. It is masked
today only because `workflow_name = slot.workflow_name or f"ace(run)-{timestamp}"`
(`src/sase/agent/launch_executor.py:103`) embeds a per-slot unique timestamp. If you model "one family = one
workflow" and give parallel members a shared `workflow_name`, **the first member to finish silently releases
every sibling's claim.** That is the single most likely way this initiative produces a baffling
intermittent bug.

Related: the `#0` placeholder is exempt from the exclusivity check, so deferred members already pile up on
it, and `claim_deferred_workspace` opens by calling the unfiltered `release_workspace(project_file, 0, ...)`
(`src/sase/axe/run_agent_phases.py:53-54`). Safe today, unsafe the moment `workflow_name` is shared.

### Barrier 3 — One ChangeSpec, one branch, one tree

The branch is a **pure function of the ChangeSpec name**
(`src/sase/core/changespec.py:55-65`), and family members inherit `cl_name` from the parent by construction
(`src/sase/agent/_family_attach_launch.py:61-63`). Therefore: same family ⇒ same `cl_name` ⇒ same branch ⇒
same working tree. No worktrees are used anywhere.

Under concurrent members the file won't corrupt (everything goes through `changespec_lock` +
`write_changespec_atomic`), but the semantics do:

- `STATUS:` is a single line rewritten wholesale (`commit_utils/modifiers.py:44-92`) — last-writer-wins on a
  field that is supposed to be a state machine.
- `COMMITS:` numbering is positional (`commit_utils/entries.py:117-176`); concurrent appends interleave, and
  renumbering operates on a list neither member authored.
- The commit checkpoint keys off process-global env (`workflows/commit/checkpoint.py:45-50`).

**This is where `wait=false` stops being a flag and becomes an architecture.** Giving a member its own
workspace implies its own branch implies its own ChangeSpec — at which point it is not obviously "in the
family" in any sense the ChangeSpec layer recognizes.

### Barrier 4 — Family members are not `%wait`-referenceable

`src/sase/ace/tui/agent_completion.py:254` requires `not agent.is_workflow_child`, and `is_workflow_child`
is a historical alias that is **true for both child kinds** (`src/sase/ace/tui/models/agent.py:283-291`).
Family members are therefore excluded from `%wait` targets.

This is a hard blocker. The moment family members are separate processes, `%wait` is the only ordering
primitive available — and it currently cannot name them. Fixing it collides with Barrier 5.

### Barrier 5 — `--` is reserved, so members have no user-typeable names

`%wait:foo--code` cannot be authored, because `validate_user_agent_name` rejects any name containing `--`
(`src/sase/agent/launch_validation.py:84-91`). The family-attach path works around this with an env bypass
(`INTERNAL_AGENT_NAME_BYPASS_ENV`, `src/sase/agent/_family_attach_launch.py:44-86`).

So a swarm cannot today express "segment B is in segment A's family **and** waits for it" — the grouping
form (`%n(parent, suffix)`) produces a name the ordering form (`%wait:X`) is forbidden to mention. Either
`--` becomes typeable in `%wait` targets specifically, or grouping must stop being encoded in the name.

That second option is worth serious consideration: **the name is a bad place to store group membership.**
`agent_family` is already a metadata field (`plan_chain.py:17`), and membership resolution already prefers
metadata over the name (`_artifact_state.py:115-131`). The `--` convention is vestigial.

### Barrier 6 — `wait=<bool>` on `%name` conflates three orthogonal axes

Your stated plan is `%name(wait=<bool>)`. Four problems, in ascending order of importance:

1. **`%name` blanket-rejects all kwargs** (`_family_attach_directives.py:22-28`):
   ```python
   if named_args:
       raise ValueError(
           f"Unsupported keyword on {source}: {keys}. "
           "Use %n(parent, suffix) for family attach; keyword arguments "
           "are not supported.")
   ```
   Mechanical, but note the contrast: `%wait` already has a kwarg allowlist (`_directive_collect.py:85-99`),
   so adding one there is a one-line change while adding one to `%name` reverses a deliberate decision.

2. **There is no boolean-kwarg precedent anywhere in directive parsing.** Booleans are presence-based
   (`%hide` → `hide="hide" in expanded_args`, `_directive_extract.py:115`) or use the `+` suffix that
   synthesizes a throwaway `"true"` (`_directive_collect.py:130-131`). The only near-miss is `%auto`, which
   exact-matches `"true"` to absorb that synthesized value (`_directive_values.py:345-347`). Permissive bool
   coercion exists (`xprompt/models.py:138-140`) but only for step-output schemas.

3. **It inverts the swarm default.** Swarm segments are **parallel by default**, and `%wait` opts into
   sequencing. Family members are **sequential by definition**. If `%name(..., wait=true)` is the default for
   family members, then adding a segment to a family silently flips it from parallel to sequential — the
   grouping directive would have scheduling side effects. That is the exact conceptual confusion the
   initiative is meant to remove.

4. **`wait=false` does not mean "don't wait."** Look at what actually forces sequencing today
   (`_family_attach_launch.py:64-74`): when `parent_is_running`, the launcher forces
   `deferred_workspace=True`, parking the child on `#0` until the parent's `done.json` lands. It waits
   **because it shares a workspace**, not because a flag says to. So `wait=false` is really
   *"give me my own workspace"* — with all of Barrier 3's ChangeSpec/branch consequences riding along
   invisibly.

**Recommendation:** keep grouping (`%name`) and scheduling (`%wait`) orthogonal. `%wait` already gives you a
DAG, already accepts kwargs, and already defaults the right way for parallel work. The change you actually
need is Barrier 4 (make members nameable as `%wait` targets), not a new flag.

### Barrier 7 — Failure does not propagate through `%wait`

YAML has a real failure model: a failed step marks the workflow failed, downstream steps become `SKIPPED`
with `context[name] = {}`, `finally:` steps still run, and `on_error: continue` tolerates per-iteration
failures (`workflow_executor.py:379-397`, `workflow_executor_loops.py:190`).

Swarms have **none of it**. A failed segment never satisfies a dependency — `done.json` outcome must be
`"completed"` — so **dependents wait indefinitely** for a run that will never come
(`docs/workflow_spec.md:849`). There is no skip, no cancel, no `finally`, no `on_error`.

This is, I think, the most underrated gap on your list. "Just as robust as YAML" is unreachable without a
failure story: today a robust swarm workflow degrades into a hung one. Minimum viable set:

- dependency-failed ⇒ dependent is **cancelled/skipped**, not left `WAITING` forever
- a `SKIPPED` render state distinct from `WAITING`
- an opt-out (`%wait(..., on_error=continue)`-shaped) for independent work
- some `finally`-equivalent for cleanup segments

### Barrier 8 — A swarm has no runtime, so `if:` and dynamic `for:` are unrepresentable

Swarm fan-out is **fixed at authoring time by the number of `---` separators**. There is no place to put a
runtime decision. This blocks the dominant YAML idiom (Barrier/§1.3: `count → if threshold → launch →
mark`), and it blocks `for:` over a computed list, `repeat:/until:`, `while:`, and `join:`.

The good news: **output passing is already solved and does not need a runtime.** A bash segment can
`sase var set path=...`; a downstream segment does `%wait:setup` and reads `{{ agents["setup"].path }}`
(`docs/xprompt.md:1808-1815`). That is file-mediated and PID-agnostic. Two caveats: the `agents` context is
loaded **once** at consumer start (no polling/refresh), and the upstream snapshot is taken *before* the
segment launches (`multi_prompt_launcher.py:261`), so a segment only ever sees strictly-earlier segments.

So the boundary is sharper than "swarms need a runtime": swarms need **conditional and computed fan-out**
specifically. Three ways out, and this is a genuine fork:

- **(A) Give swarms a runtime** — `%if`, `%for`. Risk: reinventing YAML in markdown with weaker validation
  and no schema. The `%`-directive layer is a line-oriented regex scanner
  (`_directive_types.py:15-19`), not an expression language; growing it into one is a large, permanent
  commitment.
- **(B) Make YAML steps real dispatched agents** — the executor becomes a scheduler rather than an
  in-process interpreter. This fixes the "fake agents" asymmetry and gets bash/python roots almost for free,
  but it is the larger refactor and it keeps YAML as the authoring surface, which is the opposite of your
  stated goal.
- **(C) Let swarms call YAML** — a segment references `#some_workflow`, keeping control flow in YAML while
  swarms own agent orchestration. Cheapest, preserves both systems' strengths, but does not reduce the
  surface area you want to shrink.

My read: **(C) then (A) incrementally** — start by making the swarm the default authoring surface for
*agent* orchestration and let it delegate deterministic control flow, then pull specific YAML features
(`if:`-equivalent first, since it unblocks the gate→agent idiom) into swarms once the dispatch model is
stable. Doing (A) up front means designing an expression language before you know which constructs the
migrated corpus actually needs.

### Barrier 9 — Python/bash as root rows is deeper than the two `appears_as_agent` filters

You identified `running_listing.py:163/:248`. The real situation:

1. **`appears_as_agent` is structurally unreachable for a script step**
   (`xprompt/workflow_models.py:232-239`) — it requires `visible_steps[0].is_agent_step()`, which is
   `self.agent is not None`. It is computed once and frozen into `workflow_state.json`
   (`workflow_executor.py:171`).
2. **Script steps have none of the four things a root row is assumed to have.** They run in-process via
   `subprocess.run(..., cwd=os.getcwd())` (`workflow_executor_steps_script.py:106-113`) — no workspace
   claim, no `cl_name` (child rows reuse the display slot: `cl_name=step_name`,
   `_workflow_step_loaders.py:161`), no `agent_meta.json`, no name registration. Artifacts are a single
   `{step.name}.stdout` in the **parent's** dir (`workflow_executor_steps_script.py:131`).
3. **`AgentType` has only two values** — `RUNNING` and `WORKFLOW`
   (`src/sase/ace/tui/models/agent_types.py:7-11`). There is no `BASH`/`PYTHON`. Step kind rides on a
   free-form `step_type: str` set **only on child rows**. "Root" and "is an agent" are conflated by
   construction: `is_agent_entry` consults `step_type` only under `is_workflow_child`
   (`models/agent.py:294-308`), so a root row *cannot express* "I am not an agent".
4. **The listing predicate doubles as the runner-slot admission counter.** This is the finding that most
   changes the shape of the work — `src/sase/core/runner_slots/_admission.py:24-32`:

   ```python
   def is_root_user_agent_record(record: AgentArtifactRecordWire) -> bool:
       """Return whether *record* represents a countable root user agent."""
       if record.workflow_dir_name != "ace-run" or record.has_done_marker:
           return False
       meta = record.agent_meta
       if meta is None or meta.parent_timestamp:
           return False
       state = record.workflow_state
       return state is None or state.appears_as_agent
   ```

   The same function backs `running_root_agent_count` (`_admission.py:35-54`). Making bash/python roots
   listable, done naively, makes them **consume runner slots** — throttling real LLM agents behind
   `echo hello`. Listability and capacity accounting must be decoupled first.

5. **Several UI gates check `is_child_row` / `is_workflow_child` instead of `is_agent_entry`**, i.e. they
   treat "not a child" as a synonym for "is an agent". A bash root passes all of them: the provider badge
   (`_agent_list_render_agent.py:62-63`), the model/effort detail header (`prompt_panel/_helpers.py:177-179`),
   the file-panel-vs-prompt-panel carve-out (`agent_detail.py:229-232` — the *explicit* bash/python
   special-case, `is_workflow_child`-gated), and the tools panel (`_tools_panel_fetching.py:20`, which
   short-circuits on `row is agent` before checking `is_agent_entry`). Note `tools/sources.py:42-44` gates
   correctly — so the codebase already disagrees with itself here.

### Barrier 10 — The TUI cannot represent two running members

Parallel family members are not a rendering gap; they are **unrepresentable**. In severity order:

- **Root status mirroring picks exactly one child**: `newest_active = max(active, key=child_launch_time)`
  (`_agent_status_apply.py:353`). With N running members the root shows one status and silently hides the
  rest. There is no "2 running" affordance on an agent root, and group banners skip `is_workflow_child`
  (= all child rows), so members never reach the banner counts either
  (`agent_groups/_tree.py:396-424`).
- **Recency is used as a proxy for supersession** — every one of these breaks under parallelism, because
  each infers *logical* progression from *wall-clock launch time*:
  `feedback_child_progressed_past_review` (`_agent_status_family.py:345-374`),
  `has_later_family_continuation` (`:377-391`), `is_answered_continuation_asker` (`:394-407`, which also
  overwrites `stop_time`), `superseded_by_feedback_round` (`:325-342`).
- **"A child exists" ⇒ "the planner is done"**: `planner_child_status:436-437` returns `"DONE"` outright.
- **Kill does not cascade to family members at all.** `_immediate_kill_identities`
  (`actions/agents/_kill_identity.py:44-59`) collects only steps with `step.parent_workflow == agent.workflow`;
  family members carry `parent_workflow is None` by definition, so they never match. Survivable today
  (one process); with N parallel members it means **N orphans**. The dismissal gate
  (`_agent_list_build.py:443-451`) *does* check `is_family_member_child` — so the two paths already
  disagree about whether family children are dependents.

### Barrier 11 — Per-process state that must be re-homed

Four things are genuinely process-local and block the split:

1. **`LoopState`** — `saved_chat_paths`, `feedback_bullets`, `qa_rounds`, `custom_role_visit_counts` are
   **routing inputs to the evaluator** (`standard_plan_chain_evaluator.py:53,145`), not bookkeeping, and they
   live only in RAM. `FamilyStateSnapshot.current_role` is scalar
   (`standard_plan_chain_models.py:23-24`), so the persisted state cannot name two in-flight roles.
2. **`os.environ`** — `SASE_ARTIFACTS_DIR` / `SASE_AGENT_TIMESTAMP` are re-published on **every loop
   iteration** (`run_agent_exec_markers.py:14-25`, called from `run_agent_exec.py:314`) and read by unrelated
   subsystems (e.g. the commit checkpoint).
3. **Artifacts timestamps are 1-second resolution with `mkdir(exist_ok=True)`** (`artifacts.py:81`). Two
   members minted in the same second **silently share a directory**. Sequential launch makes this rare;
   parallel launch makes it likely.
4. **`promote_to_workflow`** retroactively rewrites the *root's* meta from the *successor's* process at
   `agent_step == 2` (`run_agent_helpers_artifacts.py:73-94`) — a cross-sibling write conflict.

Two things are **already cross-process safe** and can be leaned on: `#fork:` chat inheritance resolves by
agent name → `done.json["response_path"]` (`src/sase/history/chat.py:120-154`), and `parent_timestamp`
linkage is file-mediated. Notably, role-to-role context handoff is *already* file-based and opt-in — the
coder starts with a fresh context and the plan file is the handoff artifact
(`run_agent_exec_plan_accept.py:617-623`). **No live agent-CLI session is shared between roles**, which is
better news than it could have been.

### Barrier 12 — Name planning silently degrades

`planned_name_for_prompt` returns `(None, None)` when a prompt contains any `#` and has no explicit `%name`
(`multi_prompt_reference_allocator.py:96-97`) — a blunt substring test, because the parent has not expanded
xprompts yet and an xprompt body may itself contain `%name:`.

The reassuring part: an explicit `%name` is checked **first** (`:64-75`), so `%name:foo` + `#bar` plans fine.
Since `agents["..."]` requires a literal key anyway, the realistic reference case always carries a `%name`.

The genuinely broken case: **`%name` supplied inside the xprompt body.** `#foo` expanding to `%name:bar`
means the segment is unplannable, no upstream record is created (`multi_prompt_launcher.py:511-533` requires
an explicit name), and `agents["bar"]` in a later segment cannot resolve. There is no fallback — the 30s
naming poll (`multi_prompt_reference_naming.py:11-27`) covers only bare `%wait` / bare `#fork` in the
*immediately next* segment, and on timeout degrades silently to the global, racy
`get_most_recent_agent_name()`.

If swarms become the primary workflow surface this needs a rule — *any segment others reference must carry a
literal `%name`* — enforced at load, not discovered at runtime.

---

## Part 3 — Requirements you have not mentioned

Ordered by how likely they are to derail the work.

1. **Failure propagation through `%wait`** (Barrier 7). Robust ⇒ a failed dependency cancels dependents.
   Today it hangs them forever. Nothing else on this list changes "robust as YAML" as much.
2. **Runner-slot accounting must be decoupled from root listing** (Barrier 9.4) before script roots exist.
3. **`release_workspace` must become PID-scoped** (Barrier 2.3) before any two members share a
   `workflow_name`. This is a latent trap on the obvious implementation.
4. **Artifacts timestamps need sub-second resolution or a collision guard** (Barrier 11.3).
5. **Kill/cleanup must cascade to family members** (Barrier 10), or parallel members orphan on kill.
6. **`prompt_part` wrap-around and `tags: vcs|rollover|commit` have no swarm equivalent.** This is how
   `#git:foo #commit do X` layers workspace setup → user agent → commit around one prompt
   (`workflow_loader.py:191`, `xprompts/git.yml`, `xprompts/commit.yml`). It is the most load-bearing YAML
   feature in daily use and the least obviously portable, because a swarm segment *is* a whole agent — it has
   nowhere to inject text *into* a sibling.
7. **`use:` step imports** (`workflow_loader.py:99`, used by `commit.yml:15`, `pr.yml`) — swarms have no
   composition primitive below the segment level.
8. **Compile-time validation.** `workflow_validator.py:27` cross-checks step field types and unused
   inputs/outputs. Swarms validate essentially nothing; `%wait` targets are resolved at runtime, and an
   unknown `%foo` is silently left in the prompt (`_directive_collect.py:47-48`).
9. **HITL gates** (`workflow_executor_steps_script.py:170`) — no swarm equivalent.
10. **The `hidden:`/`appears_as_agent` collapsing trick.** `#git:foo do X` renders as *one* agent row despite
    being a 6-step workflow. Swarms have `%hide` (presence-based, `_directive_extract.py:115`), which may
    suffice — but `appears_as_agent` also gates root listing and slot admission, so the two are not
    equivalent.
11. **The `family_candidate` star-read vs. `parent_timestamp` linked-list-write mismatch**
    (`_index.py:145-194`) will need reconciling if members become a DAG rather than a chain.

### Live bugs found (independent of this initiative)

- **Only the first custom role at a placement ever runs.** `_select_custom_role_after`
  (`standard_plan_chain_evaluator.py:120-152`) `return`s on the first `placement_after` match, while
  `active_roles_after` (`discovery.py:84-92`) deliberately gathers roles from **all** definitions and sorts
  them. Install a `tester` and a `linter` both at `after: code` → only the alphabetically-first by
  `(source_path, id)` runs, **silently**. Reachable today with two YAML files and no parallelism.
- **`on_done` is dead.** Validated, stored, snapshotted, listed by `sase xprompt list` — and read by nothing.
  `re_review` / `continue` / `terminate` have zero behavioral difference; `docs/agent_families.md:105`
  admits it. Likewise `on_failure`: both `notify_and_continue` and `notify_and_stop` force `terminal=True`
  (`standard_plan_chain_evaluator.py:198`), so they too are indistinguishable in effect.
- **The `~~~` fence bug.** The swarm *classifier* (`segment_separators.py:13-17`) is CommonMark-ish and
  honors `~~~` fences; the Rust *splitter* (`agent_launch/mod.rs:1331-1358`) is a naive backtick-only run
  scanner. A `---` inside a `~~~` block splits anyway, tearing the fence in half and launching a garbage
  agent whose entire prompt is the fence tail. Contradicts the documented rule at `docs/xprompt.md:1831`.
  Low impact today; a correctness issue the moment swarms are the primary workflow surface.
- **Swarm expansion silently discards prose.** With multiple embedded references, inter-reference and
  trailing prose is dropped (`xprompt_swarm.py:446-451`) — silent data loss in an authoring surface.
- **`workflow.schema.json` never declares `on_error`**, and `additionalProperties: false` on step objects
  means a step using the documented `on_error:` field fails JSON-Schema validation while parsing fine at
  runtime.

---

## Part 4 — Assessment of your two stated plans

### "Allow agents in the same family to run in parallel via `%name(wait=<bool>)`"

**The requirement is right; the mechanism is, I think, the wrong shape.** Three reasons (detail in Barrier 6):

- Parallelism is not gated by a missing flag. It is gated by the workspace/ChangeSpec/branch triple
  (Barriers 2–3) and by `LoopState` being in RAM (Barrier 11). `wait=false` does not grant those — it
  *exposes* their absence, and the first symptom will be `run_sase_hg_clean` eating a sibling's work.
- It conflates grouping with scheduling. `%wait` already owns scheduling, already has kwargs, already is a
  DAG, and already defaults to parallel. Putting a scheduling flag on `%name` means the grouping directive
  acquires side effects — the exact confusion the initiative exists to eliminate.
- The prerequisite is Barrier 4: family members must become `%wait`-referenceable, which collides with `--`
  being unspeakable (Barrier 5).

**Suggested reframe:** members become independently launched agents ordered by `%wait` (parallel by default,
as swarms already are), and `%name` only ever answers *"who am I and what group am I in?"* Then `wait=` is
unnecessary — its absence *is* the parallelism.

### "Python and Bash steps as root agent rows"

**Correct and necessary, and roughly 3× larger than it looks** (Barrier 9). It is not two filters. It
requires: script steps becoming independently dispatched units with their own artifacts dir and
`agent_meta.json`; `AgentType` (or `is_agent_entry`) learning that a root can be a non-agent; decoupling
`is_root_user_agent_record` from `running_root_agent_count`; and fixing ~5 UI gates that use
`is_child_row` as a synonym for `is_agent_entry`.

There is a real prize buried here, though. Today YAML `agent:` steps are **fake agents** (in-process
`invoke_agent()`, no workspace, not `%wait`-able). If script steps become real dispatched units, the two
systems converge on **one dispatch model** — and that, not the `wait=` flag, is what would actually make
families "just a grouping."

---

## Part 5 — Recommendation

1. **Separate the two meanings of "family"** (Barrier 1) before anything else. Consider promoting **hoods**
   (`.`) as the grouping concept — they are already display-only, already parallel-safe, already have a
   neighbor index — and leaving `--` families as phases-of-one-CL.
2. **Do not add `wait=` to `%name`.** Make family members `%wait`-referenceable instead (Barrier 4), and let
   the existing parallel-by-default swarm semantics stand.
3. **Fix the traps before the feature**, in this order: PID-scope `release_workspace`; sub-second artifacts
   timestamps; decouple slot accounting from root listing; cascade kill to family members.
4. **Ship failure propagation through `%wait`** early (Barrier 7). It is the largest single gap between
   "swarms can express this" and "swarms are robust."
5. **Prefer path (C)→(A) on the runtime question** (Barrier 8): let swarms delegate deterministic control
   flow to YAML first, migrate agent orchestration to swarms, and only then pull specific constructs
   (`if:`-equivalent first) into the swarm layer — once the migrated corpus tells you which ones you
   actually need.
6. **Fix the first-match-wins custom-role bug** independently — it is a live silent-drop reachable today.

---

## Part 6 — The seven questions

1. **Does "family" keep meaning _phases of one CL_ (shared workspace, shared ChangeSpec, shared branch,
   inherently sequential), or does it become _a group of peers_ (own workspaces, own ChangeSpecs, inherently
   parallel)?** If both, they need different names — every axis (tree sharing, CL identity, default
   ordering, failure propagation) wants the opposite answer for each, and no single `wait=` flag can
   straddle them. If it becomes peers: **what happens to the ChangeSpec?** Branch is a pure function of
   `cl_name`, so parallel members either share a branch (and race `STATUS:`/`COMMITS:`) or stop being one CL.

2. **Should grouping and scheduling stay orthogonal — `%name` = "who am I / what group", `%wait` = "when do I
   start"?** I believe `wait=` on `%name` is the wrong knob (it means "give me my own workspace", not "don't
   wait"), but you may be optimizing for authoring ergonomics I am not seeing. If `%name(wait=)` is
   load-bearing for you, what does it mean for a *non-family* swarm segment?

3. **Are `--` names becoming user-typeable, or is group membership moving out of the name entirely?** Family
   members are excluded from `%wait` targets today (`agent_completion.py:254`) and `--` is rejected in
   user-supplied names (`launch_validation.py:84-91`), so a swarm cannot currently say "in A's family **and**
   waits for A". `agent_family` is already a metadata field and membership already resolves metadata-first —
   the `--` convention may be vestigial.

4. **What are swarm failure semantics?** Today a failed segment leaves every dependent `WAITING` forever.
   YAML has skip-on-prior-failure, `on_error: continue|stop`, and `finally:`. Which of those must swarms
   reach for "as robust as YAML" — and specifically, should a failed dependency **cancel** dependents, and do
   you want a `finally`-equivalent for cleanup segments?

5. **Where is the permanent boundary on swarm control flow?** Swarm fan-out is fixed at parse time by the
   `---` count, which makes the dominant YAML idiom (`deterministic gate → conditional agent`, per
   `fix_just.yml` / `refresh_docs.yml` / both audits) inexpressible. Do swarms grow `%if` and computed
   `%for` (a real expression language on top of a line-oriented regex scanner), or do they delegate control
   flow to YAML and own only agent orchestration?

6. **Should bash/python root rows consume runner slots?** `is_root_user_agent_record`
   (`runner_slots/_admission.py:24-32`) is simultaneously the ACE root-listing filter and the runner-slot
   admission counter. Making script roots listable without splitting these throttles real LLM agents behind
   `echo`. Splitting them means deciding what capacity a script row consumes — and whether an "agent root"
   and a "script root" are the same type at all (`AgentType` has only `RUNNING` and `WORKFLOW`).

7. **What is the fate of the `kind: agent_family` YAML schema, and of `prompt_part` wrap-around?** The
   family schema advertises more than it delivers — `on_done` has zero control-flow readers, `on_failure`'s
   two values are behaviorally identical, and only the first role at a placement ever runs. Is the swarm
   meant to replace it? And `prompt_part` + `tags: vcs|rollover|commit` (how `#git:foo #commit do X` layers
   setup → agent → commit) has **no swarm equivalent**, because a swarm segment is a whole agent with nowhere
   to inject text into a sibling — is that composition staying in YAML permanently?
