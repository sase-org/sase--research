# Unifying Agent Families as a Grouping, and Migrating YAML Workflows to Swarms (Consolidated)

Date: 2026-07-16

Consolidates two independent research reports plus lead-researcher verification:

- `agent_family_unification_consolidated__a.md` (codex researcher) — architecture-first analysis: the five-axis run
  model, the YAML↔Markdown parity matrix, and a six-phase implementation shape.
- `agent_family_unification_consolidated__b.md` (claude researcher) — implementation-first analysis: what a family
  actually is at the process level, the concrete traps in the workspace/ChangeSpec/slot machinery, and live bugs.

The lead researcher re-verified every load-bearing claim below against the working tree on 2026-07-16 (all cited
file:line references were read directly). Where the reports disagree, the resolution is stated explicitly
(§ Conflict Resolutions).

## Headline

**"Agent family" today names two different mechanisms, and neither is "a group of agents."**

1. **The standard plan chain is one OS process.** `foo--plan`, `foo--q`, `foo--code` are sequential iterations of a
   single `while True` loop (`src/sase/axe/run_agent_exec.py:312` ff., verified). `spawn_custom_role_followup` spawns
   nothing — it mutates `state.current_role_suffix` and lets the loop go around again
   (`src/sase/axe/run_agent_exec_custom_roles.py:80-90`, verified). Each iteration writes an artifacts directory; ACE
   renders one row per directory, linked by `parent_timestamp`. The visible grouping is a rendering artifact of a
   linked list.
2. **Manual family attach (`%n(parent, suffix)`) is a separate process that is serialized by workspace sharing, not by
   a scheduler.** When the parent is running, the launcher forces `deferred_workspace=True` and parks the child until
   the parent's workspace frees (`src/sase/agent/_family_attach_launch.py:64-74`, verified). The child also inherits
   the parent's `cl_name` (`:61-63`), hence its branch and working tree.

So the initiative is not "add a flag so members can run in parallel." It is **inverting one-process → N-rows into
N-processes → one-group**, while unbundling the ~7 meanings "family" currently carries at once: visual fold,
`--`-naming namespace, process lineage, implicit success dependency, workspace handoff, lifecycle state machine, and
the scope for wait/dismiss/revert/output-aggregation actions. Parallelism falls out of that inversion; it is not the
change itself.

## The target conceptual model

Both reports converge on separating five independent axes in the persisted model (report A's framing, which report B's
findings independently justify):

| Concept | Meaning | Today's overloaded carrier |
| --- | --- | --- |
| Run group | rows forming one user-recognizable unit | `--` name prefix, `workflow_name`, `parent_timestamp` |
| Node | one executable/interactive member (agent, bash, python, gate) | `AgentType` (only `RUNNING`/`WORKFLOW`) |
| Dependency edge | when a node may run (success/terminal/conditional) | implicit workspace deferral + `%wait` |
| Display relation | where a node folds in ACE | `parent_timestamp` again |
| Controller | who may add/transition nodes dynamically | the in-process plan-chain evaluator |

Useful product definition: *an agent family is a run group whose members usually have named roles and which may have a
lifecycle controller.* The standard plan chain becomes a group with a controller — not the definition of what all
groups are. `group_id`/`node_id` metadata should become authoritative, with `--` names, `workflow_name`, and
`parent_timestamp` retained as compatibility/display projections. (Membership resolution already prefers metadata over
the name — `family_base_from_meta`, `src/sase/core/wait_dependency_resolution/_artifact_state.py` — so the `--`
convention is arguably vestigial.)

## Verified mechanics that constrain the design

Facts both reports rely on, independently re-verified by the lead researcher:

- **Sequencing is a side effect of workspace exclusivity.** `wait=false` therefore really means "give me my own
  workspace," with ChangeSpec/branch consequences riding along invisibly (`_family_attach_launch.py:64-74`).
- **`--` is reserved in user-typed names** (`src/sase/agent/launch_validation.py:84-91`), bypassed internally via
  `INTERNAL_AGENT_NAME_BYPASS_ENV` for family attach. Note the docstring scopes this to *explicit user entry points*
  only — historical artifact names are read separately — so making members referenceable is a validation-policy
  change, not an artifact-format change.
- **Member referenceability is partial and inconsistent, not uniformly absent** (lead-researcher nuance refining
  report B). TUI autocomplete collapses family roots to the family base name
  (`src/sase/ace/tui/agent_completion.py:253-254` + `agent_prompt_name`), and child rows are hidden by default; but
  the runtime wait index *does* index planner rows individually under their canonical `<base>--plan` name
  (`src/sase/core/wait_dependency_resolution/_index.py:101-118`). The inconsistency itself is an argument for explicit
  edges over name-derived ordering.
- **Failure does not propagate.** Wait resolution requires `SUCCESS_OUTCOME = "completed"` (identity waits also accept
  `plan_rejected` — `_types.py:7-8`). A failed producer never satisfies a dependency; dependents wait forever. Swarms
  have no skip, no cancel, no `finally`, no `on_error`.
- **Listing and capacity share one predicate.** `is_root_user_agent_record`
  (`src/sase/core/runner_slots/_admission.py:24-32`) backs both the running listing
  (`src/sase/agent/running_listing.py:219`) and `running_root_agent_count` (`_admission.py:35-54`). Naively listable
  script roots would consume runner slots; conversely, `parent_timestamp` children are slot-exempt, so parallel
  "children" bypass `max_running_agents` entirely.
- **The workspace machinery assumes one exclusive owner.** `run_sase_hg_clean` wipes uncommitted work at member
  startup; stale git-index-lock removal assumes exclusive claim; and `release_workspace` matches on
  `(workspace_num, workflow, cl_name)` with **no PID predicate** — masked today only because `workflow_name` embeds a
  per-slot timestamp (`src/sase/agent/launch_executor.py:103`). Model "one family = one `workflow_name`" and the first
  member to finish silently releases every sibling's claim. This is the most likely source of a baffling intermittent
  bug on the obvious implementation path.
- **Branch is a pure function of `cl_name`** (`src/sase/core/changespec.py`), and family attach inherits `cl_name` —
  so same family ⇒ same branch ⇒ same tree. Concurrent members won't corrupt the ChangeSpec file (atomic writes) but
  will race its semantics: `STATUS:` is last-writer-wins; `COMMITS:` numbering is positional.
- **Swarms have no runtime.** Fan-out is fixed at parse time by the `---` count; segments dispatch in one loop with
  per-segment upstream snapshots encoded *before* launch (`src/sase/agent/multi_prompt_launcher.py:253-262`,
  verified), and the `agents[...]` context is loaded once at consumer start. Output passing is file-mediated and
  PID-agnostic (already cross-process safe); conditional/computed fan-out is inexpressible.
- **YAML `agent:` steps are not real agents.** They run `invoke_agent()` synchronously in-process, get no workspace,
  and cannot be `%wait`-ed — which is why `refresh_docs.yml` and `fix_just.yml` shell out to launch scripts for real
  background agents. YAML has control flow but fake agents; swarms have real agents but no control flow.
- **This initiative reverses a recorded scope cut.** The 2026-07-05 v1/v2 family design explicitly dropped root
  bash/python rows as a v1 non-goal (`202607/dynamic_agent_families_v1_v2_design.md:38,137,168-170`, verified). That
  doc should be explicitly superseded so future agents don't treat the cut as current policy.

## Requirements not in the original framing, by derail-likelihood

1. **A failure model for `%wait`** — the largest single gap between "swarms can express this" and "swarms are
   robust." Minimum viable: failed dependency ⇒ dependents deterministically **cancelled/skipped** (a render state
   distinct from `WAITING`), an opt-out for independent work, and a `finally`-equivalent (terminal edges) for cleanup
   nodes. Policies must be persisted so CLI, ACE, wait resolution, notifications, and revival agree.
2. **Workspace/ChangeSpec policy for parallel members** — shared vs. isolated checkout, snapshot base for isolated
   nodes, read-only vs. writing roles, convergence of parallel writers, and environment scope. The motivating
   update-then-verify case makes environment scope concrete: `just install` in one isolated workspace does nothing for
   a verifier launched into another. Until this exists, parallel *writing* members should stay blocked.
3. **Decouple slot accounting from root listing** before script roots exist, and decide capacity classes: do script
   nodes consume LLM runner slots (recommended: no, separate pool), do parallel family agents count globally
   (recommended: yes), per-group concurrency caps.
4. **PID-scope `release_workspace`** (or stop sharing `workflow_name`) before any two members share one.
5. **Kill/cleanup must cascade to group members.** `_immediate_kill_identities` collects only workflow steps; family
   members carry `parent_workflow=None` and never match — survivable with one process, N orphans with N. The dismissal
   gate *does* check family membership, so the two paths already disagree.
6. **Group-scoped node identity.** Reusable swarms need an auto-unique invocation/group id plus stable local node ids
   (`update`, `verify`); two concurrent invocations of a swarm using global `%name:plan` collide today. Add a
   load-time rule: any segment referenced by others must carry a literal `%name` (name planning silently degrades when
   `%name` arrives via xprompt expansion, falling back to a racy `get_most_recent_agent_name()`).
7. **A group record independent of any one process.** The visible root may finish while siblings run (or be a
   seconds-long bash node while agents run for hours); status mirroring currently picks exactly one newest-active
   child, and the recency-as-supersession heuristics in `_agent_status_family.py` all break under parallelism. Group
   status/completion should come from a durable group aggregate, with ACE free to render the first concrete node as
   the apparent root.
8. **First-class node records for bash/python** — own artifacts dir, meta, stdout/stderr, PID/process-group,
   kill/retry/dismiss/revive, typed output, provenance. Today `appears_as_agent` is structurally unreachable for
   script steps, `AgentType` has only two values, and ~5 UI gates use `is_child_row` as a synonym for
   `is_agent_entry`. Roughly 3× larger than the two listing filters suggest.
9. **A unified typed-output plane.** YAML steps have schemas, validation, joins, and accumulated context; swarm agents
   expose string vars keyed by global names. Direction: `nodes.<local_id>.<field>` as the canonical group namespace
   with an `agents[...]` compatibility alias, artifact references for large data, deferred rendering until upstream
   values exist.
10. **Per-process state that must be re-homed:** `LoopState` routing inputs (feedback bullets, QA rounds, visit
    counts) live only in RAM; `SASE_ARTIFACTS_DIR`/`SASE_AGENT_TIMESTAMP` are re-published per loop iteration and read
    by unrelated subsystems; artifacts timestamps are 1-second resolution with `mkdir(exist_ok=True)` — two members in
    the same second silently share a directory. (Good news, verified: role-to-role context handoff is already
    file-based and opt-in; no live agent-CLI session is shared between roles.)
11. **Trust model for executable Markdown.** Once `.md` can run bash/python, invoking prompt-looking text executes
    local code. Needs explicit opt-in syntax/kind, protection against fences produced by template substitution,
    LaunchApproval previews that show commands and node counts, and a policy for inline python vs. registered helpers.
12. **Definition/graph snapshotting.** Compile the definition at launch and persist the compiled nodes/edges/policies;
    otherwise editing a swarm while a node waits changes what later nodes mean, and crash recovery has no
    authoritative graph.
13. **Cross-surface scope.** Group identity, node kinds, aggregate status, wait semantics, and cleanup planning are
    shared domain behavior under the Rust-core boundary (`../sase-core`). CLI listings, ACE models, mobile/editor
    bridges, Telegram summaries, and LaunchApproval previews must consume the same group/node projection — a TUI-only
    grouping rewrite would make the model less consistent, not more.
14. **Composition semantics without a swarm equivalent, keep as adapters initially:** `prompt_part` wrap-around with
    `tags: vcs|rollover|commit` (how `#git:foo #commit do X` layers setup → caller's agent → commit — the most
    load-bearing daily YAML feature), `use:` step imports, HITL gates, and the `hidden:`/`appears_as_agent` collapsing
    trick. A swarm segment *is* a whole agent; it has no anchor meaning "the caller's prompt goes here." "Move as much
    as possible" should not require eliminating a semantic category Markdown doesn't express.
15. **Nesting/scope policy.** Whether an embedded swarm flattens into the caller's group or nests, whether a group may
    span projects, and how child VCS refs interact with group inheritance. Conservative v1: project-local groups,
    flatten static embeds, keep per-definition provenance.

## Assessment of the two stated plans

### `%name(..., wait=<bool>)`

**Right requirement, wrong knob as stated.** Verified specifics: `%name` deliberately blanket-rejects keyword args
(`_family_attach_directives.py:22-28`); there is no boolean-kwarg precedent in directive parsing; swarm segments are
parallel-by-default while family members are sequential-by-definition, so a `wait=true` default on family attach gives
the *grouping* directive scheduling side effects — the exact conflation the initiative exists to remove; and since
sequencing is enforced by workspace deferral, `wait=false` actually means "give me my own workspace" (with ChangeSpec
and branch consequences). A boolean also cannot express what YAML already supports: wait-on-terminal (`finally`),
run-on-failure, multi-parent joins, skip-vs-cancel, conditional edges.

**Consolidated recommendation:** keep grouping and scheduling orthogonal in the durable model — membership and
dependency edges are separate persisted facts. Make group members `%wait`-referenceable (the actual missing primitive)
and let parallel-by-default stand. If `wait=` ships on `%name` at all, it must be pure sugar that compiles into an
explicit edge, and the workspace question deserves its own explicit knob (e.g. `workspace=shared|isolated`) rather
than riding along silently.

### Python/bash as root rows

**Correct and necessary — and the convergence prize is bigger than the feature.** Beyond the ~3× scope in requirement
8, making script steps independently dispatched units with real records is the same change that would fix YAML's
fake-agent asymmetry: both systems converge on **one dispatch model**, which — more than any flag — is what makes
families "just a grouping."

## Conflict resolutions

1. **`wait=` on `%name`:** report A would keep `wait=true|false` as ergonomic sugar over explicit edges; report B
   would not add it at all. Both agree the durable model is explicit membership + explicit edges and that a boolean
   can't carry failure semantics. Resolution above: B's position for the syntax (don't overload the grouping
   directive; B's parser-level evidence is decisive), A's position for the model (edges are the durable form, sugar is
   negotiable later).
2. **Hoods vs. explicit group metadata:** report B suggests promoting hoods (`.`) as the "just a grouping" concept;
   report A warns that treating any shared name prefix as an execution family recreates name-inference under a new
   delimiter. These reconcile cleanly once display and execution are separated: hoods demonstrate the *display-side*
   UX (display-only, parallel-safe, zero runtime baggage) and can absorb family *rendering*; authoritative execution
   membership should be explicit `group_id` metadata, never prefix-derived. Neither hoods nor `--` names should answer
   lifecycle questions.
3. **Runtime strategy:** report A recommends compiling both YAML and Markdown into one durable run-graph scheduler;
   report B recommends starting with swarms delegating deterministic control flow to YAML (its option C) and pulling
   constructs into swarms incrementally (option A), noting that making YAML steps real dispatched agents (option B) is
   the convergence prize. These are compatible: A describes the **end state**, B the **sequencing**. Do not design a
   `%`-directive expression language up front — the directive layer is a line-oriented regex scanner, and the migrated
   corpus should reveal which constructs are needed (an `if`-equivalent first: the dominant real-world YAML idiom is
   *deterministic gate → conditional agent*, per `fix_just.yml`, `refresh_docs.yml`, and both audit workflows).
4. **Member wait-referenceability:** report B stated members "cannot be `%wait` targets" citing the TUI completion
   filter; lead verification shows the picture is subtler (planner rows are individually indexed as
   `<base>--plan`; the block is autocomplete visibility plus `--` name validation at user entry points). The practical
   conclusion is unchanged — you cannot today author "in A's group **and** waits for A" — but the fix is smaller than
   it looks and the existing inconsistency strengthens the explicit-edge design.

## Migration order (merged)

- **First (static graph + command nodes + local ids + typed outputs + group completion):** setup-command → verifier
  agents (the motivating case); parallel reviewers → synthesizer; the agent portions of `refresh_docs`.
- **Later (needs conditional edges / durable scheduler):** `fix_just` (gates → mutually exclusive fixers), `sync`
  (conditional, repeated-until-resolved agent step), loop/join-heavy evaluation workflows, user-authored HITL.
- **Retain as adapters, at least initially:** VCS wrappers (`#git`/`#gh`), commit/propose/PR intents, `#json`/`#file`/
  screenshot helpers, privileged plan-approval side effects. They can compile into the same IR eventually, but forcing
  them to be "a list of swarm members" is not a useful goal.

Sequenced implementation shape (report A, endorsed): (1) decouple grouping from lineage with additive group/node
metadata and a presentation-neutral projection; (2) normalize static swarms (invocation ids, local node ids, edges,
capacity classes); (3) first-class command nodes + trust rules; (4) durable graph scheduler with failure semantics and
crash recovery; (5) bridge the plan-chain evaluator as a controller emitting nodes into the common model; (6) migrate
definitions by semantic class, keeping a YAML compatibility loader.

## Live bugs found along the way (independent of this initiative)

- **Only the first custom role at a placement ever runs** — `_select_custom_role_after` returns on first
  `placement_after` match (`standard_plan_chain_evaluator.py:112-152`, verified) while discovery gathers and sorts all
  roles; a `tester` and a `linter` both at `after: code` silently drops one.
- **`on_done` is dead** (stored, listed, read by nothing); `on_failure`'s two values are behaviorally identical.
- **`~~~` fence bug:** the Python swarm classifier honors tilde fences; the Rust splitter is backtick-only, so a `---`
  inside a `~~~` block splits anyway and launches a garbage agent.
- **Swarm expansion silently discards inter-reference/trailing prose** with multiple embedded references.
- **`workflow.schema.json` omits `on_error`** while `additionalProperties: false` makes documented usage fail schema
  validation.

## The seven questions

1. **What does "family" mean going forward — phases of one CL, or a group of peers?** If both concepts survive, they
   need different names: every axis (workspace sharing, ChangeSpec identity, default ordering, failure propagation)
   wants opposite answers. And if peers: what happens to the ChangeSpec, given branch is a pure function of `cl_name`
   — do parallel writers share a branch (racing `STATUS:`/`COMMITS:`) or stop being one CL?
2. **May group membership become explicit metadata?** `group_id`/`node_id` authoritative; `--` names,
   `workflow_name`, and `parent_timestamp` demoted to compatibility/display projections; and a synthetic durable group
   record owning aggregate state, with ACE optionally rendering the first concrete node as the apparent root — or must
   the concrete root row itself remain the authoritative record?
3. **What workspace/environment semantics do parallel members get?** Shared mutable checkout, isolated workspace at a
   defined snapshot, or an explicit per-node read/write policy — and specifically for update-then-verify, what scope
   does a setup command's effect have (one node, all later nodes, a group-owned shared environment)?
4. **What is the v1 failure model?** Is `after success` + `after terminal`/`finally`, with failed dependencies
   deterministically skipping/cancelling dependents (rendered distinctly from `WAITING`), sufficient — or must v1 also
   include on-failure branches, retries, and manual overrides?
5. **Is a durable host-side graph scheduler acceptable, and where is the initial control-flow boundary?** Can SASE
   persist a compiled graph and release/create nodes on outputs, failures, gates, and restarts? Until then, do swarms
   delegate deterministic control flow to YAML (option C) — and which concrete workflows must be expressible in
   Markdown for milestone 1 (update-then-verify only, or also `fix_just`-class conditionals)?
6. **What executable-Markdown syntax and trust boundary do you want?** Explicit opt-in kind/capability before fences
   can execute; inline python vs. registered helpers; LaunchApproval previews showing commands — and do you accept
   dropping `wait=` from `%name` in favor of `%wait`-based edges plus a separate workspace knob, or is
   `%name(wait=)` load-bearing ergonomics for you (and if so, what does it mean on a non-family segment)?
7. **Should script roots and parallel members consume runner slots?** `is_root_user_agent_record` currently backs
   both listing and admission; splitting them forces the real decisions — what capacity a bash/python node consumes,
   whether parallel family agents count against `max_running_agents` (recommended: yes), and whether groups get their
   own concurrency cap.
