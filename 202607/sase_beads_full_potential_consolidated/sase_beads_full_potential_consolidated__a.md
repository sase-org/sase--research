# SASE Beads: Practical Improvement Research

**Date:** 2026-07-14  
**Goal:** Identify the most impactful practical improvements to SASE beads, informed—but not dictated—by the evolution
of Steve Yegge's Beads project.

## Executive conclusion

SASE beads is already successful at one job: compiling an approved epic plan into a dependency DAG, launching phase
agents, and retaining an execution record. It is not yet realizing the broader value of a persistent work graph.

The best next step is not to copy upstream Beads' expanding platform. It is to make SASE's smaller model trustworthy and
frictionless:

1. make plan references portable and self-healing;
2. enforce truthful completion instead of cascade-closing unfinished work;
3. compile a plan into its epic/phase graph atomically;
4. make claiming atomic and recover claims from actual SASE agent liveness;
5. expose the event history that SASE already stores; and
6. add a deliberately small follow-up queue with priority, deferral, and provenance.

Those changes reinforce SASE's existing architecture. Dolt, federation, arbitrary status/type systems, molecules,
wisps, mail, generic gates, and external tracker synchronization would add much more complexity than value here.

## Scope and method

This analysis used three evidence sets:

- The current SASE bead implementation and documentation, including `docs/beads.md`, the Rust-backed Python facades,
  `sase bead work`, the `bd/new_epic` workflow prompt, and the generated `sase_beads` skill source.
- The live SASE bead store as of 2026-07-14: the canonical event streams plus their generated `issues.jsonl`
  projection.
- The Git history, changelog, documentation, releases, and selected issue/PR history of the project formerly hosted at
  `steveyegge/beads`, now redirected to [`gastownhall/beads`](https://github.com/gastownhall/beads). The inspected
  upstream checkout was at `6e1b04c26` (2026-07-14).

The local measurements below describe actual SASE usage, not a synthetic fixture. They are more important to the
recommendations than feature parity with upstream.

## What SASE beads already does well

SASE has a coherent and unusually well-integrated core:

- A compact domain: plan beads, executable phase children, three statuses, and blocking dependencies.
- An append-only, Git-portable event store owned by the Rust core, with a generated JSONL projection.
- A strong plan-to-execution bridge: `sase bead work` validates an epic, derives Kahn waves from its DAG, preclaims
  phases, emits dependency-aware `%wait` relationships, launches one phase agent per bead, and launches a final land
  agent.
- Deterministic agent naming and safe retry behavior for failed or killed epic runs.
- Useful integration with model aliases, commits, SDD plan files, ChangeSpecs, telemetry, ACE, and sidecar repositories.
- Search, ready/blocked views, statistics, health checks, dry-run launch previews, and conflict repair.

The dependency graph is not decorative. It is the most heavily exercised part of the model. That is a strong signal to
invest in graph correctness and usability before introducing more kinds of graph edge.

## What the live store says about actual usage

### Inventory snapshot

| Measure | Observed value | Interpretation |
| --- | ---: | --- |
| Total beads | 1,479 | Substantial real usage in under four months |
| Plan beads | 214 | Almost every body of work has a plan container |
| Phase beads | 1,265 | Average 5.97 children per parent; maximum 88 |
| Epic-tier plans | 212 | The executable epic path is the product in practice |
| Ordinary plan-tier plans | 2 | The non-epic plan tier is effectively unused |
| Open / in progress / closed | 0 / 0 / 1,479 | Beads is an execution ledger, not a standing work queue |
| Parents with dependency edges | 212 of 213 | DAG scheduling is nearly universal |
| Dependency edges | 1,202 | 1,003 phase beads have at least one dependency |
| Epics marked `is_ready_to_work` | 176 | Most recent epics used automated work launch |
| Beads with descriptions | 612 | Phase context is improving but inconsistent |
| Beads with current notes | 1,149 | Notes are heavily used |
| Current notes containing `COMMIT:` | 1,043 | The notes field is primarily commit bookkeeping |
| Beads with assignees | 957 | Mostly an artifact of epic preclaiming |
| Beads with explicit model selection | 112 | Sparse overrides are appropriate because aliases supply defaults |
| Beads with ChangeSpec metadata | 0 | Implemented linkage has never been exercised in this store |

### The main diagnosis

SASE beads is used as a **short-lived epic execution ledger**:

1. approve a detailed plan;
2. create one epic and its phases;
3. launch all work;
4. close everything; and
5. move on.

That is useful, but it leaves value on the table. `sase bead ready` currently has no frontier to manage, old beads
cannot reliably lead back to their plans, and discovered follow-up work is more likely to remain in a note or report
than become claimable work.

### Plan links are mostly non-portable

Every plan bead has a `design` value, and 14 phases also have one: 228 links total. Under the current checkout's
resolution context:

- 138 links are absolute filesystem paths; 136 of those paths no longer exist.
- 90 are relative paths; 84 use legacy layouts that no longer resolve from the primary checkout.
- only 6 use the current `sase/repos/plans/...` form and resolve there.
- in total, only 8 of 228 stored design links resolve as written.

The plans themselves still exist and commonly carry `bead_id` frontmatter, so this is repairable. The current
`sase bead doctor` reports no issues because it does not validate design references. This is the sharpest mismatch
between the promise of persistent memory and the current reality.

### Completion can be factually wrong

`sase bead close <plan>` intentionally cascade-closes all phase children. That is convenient, but it permits a parent
to declare success without preserving unfinished child state.

The live store contains both resolution ambiguity and concrete contradictions:

- `sase-31.6` closed successfully after diagnosing that the target CI was still failing, then a new phase was added to
  address the residual. Plain `closed` cannot distinguish “the diagnostic phase completed” from “the target condition
  is now healthy”; that meaning lives only in prose.
- `sase-5t` and `sase-5t.5` are closed while their latest notes explicitly say to keep both open until uncommitted,
  unlanded recovery work is durably committed.

These are not merely stale prose. They show that the state transition can override the evidence it is supposed to
summarize. The plan frontmatter also says `status: done`, so the incorrect state has propagated into both systems.

### Useful event history exists but is hidden

The canonical streams retain each update, including notes that were later replaced. In the event history:

- 475 issues have at least one explicit note-update event;
- 246 have multiple note updates;
- there are 769 note-update events in total; and
- some issues have five successive notes.

The current projection exposes only the latest note. A commit hook can therefore replace a detailed verification or
blocked-state summary with `COMMIT: <sha>`. The evidence is still in the stream, but there is no normal
`sase bead history` surface for a person or agent to retrieve it.

### The agent-facing skill understates the product

The generated `sase_beads` skill is a good compact reference for create/update/list/search/ready/show/dep-add, but it
does not teach the complete implemented workflow. In particular, it omits the central `sase bead work` operation and
does not cover `blocked`, `stats`, `doctor`, `sync`, conflict repair, removal, or lifecycle shortcuts. Its typical
workflow describes manual phase claiming rather than the epic launcher that 176 epics have actually used.

This kind of contract drift matters because agents do not benefit from features they are not taught to invoke.

## What evolved in upstream Beads

Upstream's history is valuable because it reveals which ideas kept paying rent and which ideas created a complexity
cycle.

### The durable core appeared early

The initial development line already contained issue CRUD, SQLite storage, dependency tracking with cycle detection,
labels, an event audit trail, full-text search, statistics, and initialization. Agent onboarding arrived in v0.10.0;
ready-queue sorting and priorities followed soon after; hash IDs were added in v0.20.0 for concurrent-branch creation.
See the upstream [changelog](https://github.com/gastownhall/beads/blob/main/CHANGELOG.md) and
[v0.20.0 section](https://github.com/gastownhall/beads/blob/main/CHANGELOG.md#0200---2025-10-30).

The product's current documentation still reduces the essential loop to **create → dependency graph → ready → atomic
claim → close**. That loop is more useful to SASE than almost everything built around it. See
[How Beads Works](https://github.com/gastownhall/beads/blob/main/docs/core-concepts/index.md).

### Multi-agent pressure produced useful safety primitives

Several upstream improvements respond directly to agents racing or dying:

- Hash-based IDs avoid creation collisions across agents and branches.
- Atomic `bd update --claim` and `bd ready --claim` make work selection a single compare-and-set operation; repeated
  claims by the same owner are idempotent. See
  [Agent Coordination](https://github.com/gastownhall/beads/blob/main/docs/multi-agent/coordination.md).
- Transactions made multi-operation graph changes all-or-nothing.
- Epic close guards, added in v0.60.0, prevent accidental closure while children remain open. See the
  [v0.60.0 changelog](https://github.com/gastownhall/beads/blob/main/CHANGELOG.md#0600---2026-03-12).
- `bd ready --explain` and `bd graph check` made graph state diagnosable rather than magical; these shipped in the
  [v1.0.0 line](https://github.com/gastownhall/beads/releases/tag/v1.0.0).
- The current unreleased line adds claim leases, heartbeat, and reclaim because a dead worker could otherwise strand a
  task in progress forever. See [PR #4537](https://github.com/gastownhall/beads/pull/4537) and the
  [unreleased changelog](https://github.com/gastownhall/beads/blob/main/CHANGELOG.md#unreleased).

These are mature responses to real failure modes. SASE should adopt their invariants, but use SASE-native agent
liveness instead of copying a generic heartbeat system.

### Backlog management stayed simple at first

Priority, oldest-first/hybrid ready sorting, a deferred state, label filters, stale-work queries, comments, and
append-only audit history turned the dependency graph into a practical queue. Deferral was explicitly framed as an
icebox distinct from dependency blocking in
[v0.31.0](https://github.com/gastownhall/beads/blob/main/CHANGELOG.md#0310---2025-12-20).

For SASE, priority, deferral, and provenance are the useful subset. A large label taxonomy and arbitrary custom status
categories are not justified by a store with no open backlog.

### Complexity expanded, reversed, and expanded again

The same history is a warning:

- v0.30.2 added an agent mail system, message types, multiple knowledge-graph links, and event hooks.
- v0.32.0 removed the mail commands four days later on the stated principle that Beads should be a data store rather
  than a workflow engine. See the
  [v0.32.0 section](https://github.com/gastownhall/beads/blob/main/CHANGELOG.md#0320---2025-12-20).
- Molecules, formulas, wisps, gates, cross-project dependencies, agent/role/rig issue types, and worktree orchestration
  then broadened the model again.
- The SQLite/JSONL/daemon design accumulated concurrency, worktree, locking, and synchronization failure modes. v0.50
  removed the daemon and JSONL sync layers while making Dolt the default; later releases spent substantial effort on
  Dolt modes, locks, migrations, recovery, and replication. See
  [v0.50.0](https://github.com/gastownhall/beads/blob/main/CHANGELOG.md#0500---2026-02-14) and
  [v1.1.0](https://github.com/gastownhall/beads/blob/main/CHANGELOG.md#110---2026-07-04).
- A user report captured the cost clearly: multiple databases, worktree drift, locked storage, lost issues, and an
  architecture obscured by sprawling documentation. See
  [issue #376](https://github.com/gastownhall/beads/issues/376).

The lesson is not that upstream made the wrong choices for its audience. It is that SASE already owns planning,
orchestration, agents, waits, VCS workflows, ChangeSpecs, repositories, and UI. Rebuilding those concepts inside beads
would create two competing control planes.

## Recommended product direction

SASE beads should remain a **small persistent work graph and execution ledger** beneath SASE's existing orchestration.
It should not become a general project-management platform.

A useful boundary is:

- **Beads owns:** work identity, hierarchy, blocking edges, readiness, claims, evidence, resolution, and durable
  provenance.
- **Plans own:** the detailed design and phase specification.
- **Agent artifacts own:** runtime process state, questions, replies, outputs, and completion outcomes.
- **ChangeSpecs/VCS providers own:** commits, reviews, CI, mailing, merging, and submission state.
- **`sase bead work` owns:** compiling the work graph into concrete agent launches and waits.

The improvements below all respect that boundary.

## Detailed improvement opportunities

### 1. Replace stored filesystem paths with logical plan references

**Problem:** 220 of 228 design links do not resolve as stored. Paths capture a particular machine, numbered workspace,
or retired SDD layout.

**Recommendation:** store a logical SDD reference, not a filesystem path. A form such as
`plans:202607/external_repos.md` is enough; resolve it at read time through the active SDD store. Treat the plan's
`bead_id` frontmatter as the reverse index.

Practical pieces:

- Add a versioned `design_ref` wire field while continuing to read legacy `design` strings.
- On creation, canonicalize through the SDD store rather than relativizing against the current primary checkout.
- Add `sase bead doctor --fix-design-refs` that scans plans by `bead_id`, reports ambiguity, and emits repair events.
- Make normal `doctor` report missing, ambiguous, and bead/frontmatter-mismatched links.
- Have `show` render both the stable logical reference and the currently resolved path.

**Why first:** it repairs historical value immediately and is independent of any new workflow. It also makes every
later history, search, and handoff feature more useful.

### 2. Make completion an invariant, not a convenience

**Problem:** closing a plan cascades to children, and the store contains closed records whose own notes say the work
must remain open.

**Recommendation:** invert the default:

- `sase bead close <plan>` should fail when any child is non-closed.
- It should also fail when the linked plan cannot be resolved or when the plan frontmatter and bead state disagree.
- A phase with active blockers should require an explicit override to close.
- Forced closure should require `--force --reason` and record a non-success resolution.
- Reopening a child or adding follow-up work beneath a closed parent should reopen the parent automatically, or fail
  with a precise instruction to do so.
- Replace the ambiguous “closed means completed or abandoned” rule with a small resolution enum such as `done`,
  `canceled`, and `superseded`. Do not add arbitrary custom statuses.

The land agent can still perform rich verification, but the Rust mutation must enforce the minimum invariant. Upstream's
epic close guard is the relevant inspiration; SASE's own contradictory records are the stronger justification.

### 3. Compile plans into bead graphs atomically

**Problem:** `bd/new_epic` currently asks an LLM to create the parent, create children sequentially, infer phase models,
add dependencies one command at a time, edit frontmatter, commit, and launch. Each mutation can auto-commit. An
interrupted run can leave a partial graph, a wrong child order, or plan/bead drift.

**Recommendation:** add a SASE-specific compiler, for example:

```text
sase bead epic create --from-plan <plan> --dry-run
sase bead epic create --from-plan <plan> --launch --yes
```

It should:

1. parse the plan's structured phase headings, dependency declaration, and model annotations;
2. show the proposed IDs, edges, and execution waves;
3. create the epic, phases, dependencies, stable plan reference, and frontmatter linkage in one Rust-owned transaction;
4. validate cycles, missing phases, cross-epic edges, and phase count before committing anything; and
5. be idempotent by `bead_id`, producing a diff/reconcile preview instead of duplicate records.

Keep the agentic workflow as a fallback for unusual prose plans, but make `bd/new_epic` call the deterministic compiler
for normal SASE plans. This adapts upstream's batch graph creation idea without importing formulas or molecules.

### 4. Add atomic claims and SASE-native recovery

**Problem:** the documented `bd/next` path performs `ready` and then a separate status update. Two agents can select the
same ready bead. Conversely, an agent that dies after preclaim can leave a phase in progress until a human retries the
epic.

**Recommendation:** add:

```text
sase bead claim <id>
sase bead ready --claim
sase bead unclaim <id>
sase bead reconcile [<epic-id>]
```

Claim should be one atomic Rust mutation that verifies open status and satisfied dependencies, assigns the current SASE
agent identity, and transitions to in-progress. Reclaiming one's own claim should be idempotent; a competing claim
should fail clearly.

Do not copy upstream's generic five-minute heartbeat literally. SASE already knows agent name, PID/liveness, workspace,
terminal outcome, and retry identity. `reconcile` should compare claims with that source of truth:

- live or waiting agent: keep the claim;
- successful terminal agent with an open bead: flag incomplete lifecycle cleanup;
- failed/killed terminal agent: reopen or mark retryable according to policy;
- missing/ambiguous old agent evidence: warn and require an explicit reclaim.

Record a structured attempt for every launch/retry. This would make `is_ready_to_work`'s sticky Boolean unnecessary over
time; a derived `has_launched` fact and attempt history are clearer.

### 5. Expose append-only notes, evidence, and history

**Problem:** the event stream has the handoff history, but `show` presents only the latest mutable `notes` value. Commit
bookkeeping commonly overwrites richer summaries.

**Recommendation:** expose what already exists before inventing a second discussion database:

```text
sase bead history <id>
sase bead note <id> "..."          # append, never replace
sase bead show <id> --history
```

Also move common evidence out of prose:

- zero or more commit references, with repo attribution;
- agent attempt IDs and outcomes;
- ChangeSpec, bug, PR, and plan references where available;
- close resolution and reason; and
- verification summary as an append-only event.

Change the commit hook from replacing `notes` with `COMMIT: ...` to appending a commit-evidence event. Auto-populate
ChangeSpec/VCS context when `sase bead work` already knows it; the current store's zero attached ChangeSpecs indicates
that an optional manual flag is not enough.

This captures the useful part of upstream comments/audit history while reusing SASE's canonical event streams.

### 6. Add a deliberately small follow-up backlog

**Problem:** all 1,479 current records are closed. Follow-ups and defects discovered during work have no lightweight,
durable route into a future ready queue.

**Recommendation:** add one focused capture operation and only the fields it needs:

```text
sase bead capture "Fix flaky snapshot renderer" --kind bug --priority 1 --from sase-31.6
sase bead defer <id> --until 2026-08-01
```

The minimum model is:

- standalone `task` and `bug` kinds, or a single standalone `task` with an optional `kind=bug` field;
- priority with a modest fixed scale and a sensible default;
- optional `defer_until` so “not now” is distinct from dependency blocking;
- `discovered_from` provenance that does not affect readiness; and
- optional promotion into a later plan/epic.

Only the land agent—or an agent explicitly authorized by its prompt—should create follow-up beads automatically. Phase
agents should propose captures in their result rather than silently expanding scope. This preserves the existing “do
not create beads of your own” safety rule.

Start without labels, custom statuses, due dates, estimates, milestones, or a type zoo. Add a field only after the live
queue demonstrates a query that cannot be answered cleanly.

### 7. Finish the graph and agent-facing UX

The graph is heavily used but only partly editable and explainable. High-value, contained additions are:

- `sase bead dep rm <issue> <depends-on>` so a mistaken edge is repairable without manual storage surgery.
- `sase bead dep tree <id>` and `sase bead graph check` for local structure and cycle/integrity inspection.
- `sase bead ready --explain [<id>]` to state exactly which blocker, deferral, claim, or parent condition excludes work.
- JSON output for `list`, `ready`, `blocked`, `show`, `stats`, and history, with stable schemas for agents.
- A generated-skill contract test that compares documented subcommands/examples against the argparse surface.
- A rewritten `sase_beads` skill whose primary workflow is plan → atomic graph creation → dry-run → `work` → reconcile
  → land, with manual `ready --claim` as the secondary path.

These ideas borrow from upstream's best diagnostic surfaces without importing its general-purpose graph vocabulary.

## Improvements to current practice that require little or no product work

While the product changes are pending, the following practices would improve reliability now:

1. Run `sase bead work <epic> --dry-run` before launch for plans with parallel or fan-in dependencies.
2. Do not manually close a parent epic to clean up children. Close phases individually and let the land agent close the
   parent only after checking notes, commits, plan status, and actual repository state.
3. Use `--reason` whenever closure is not an ordinary successful completion.
4. Use `sase bead search` rather than full closed listings to recover historical context.
5. Pass ChangeSpec and bug metadata whenever an epic is expected to create or continue that ChangeSpec; the current
   data shows this path has never been used.
6. Treat `sase bead doctor` as a storage/sync check, not yet as proof that plan links or completion semantics are valid.
7. Update the generated `sase_beads` source template rather than any deployed skill copy.

## What not to adopt from upstream

The following upstream capabilities should remain out of scope unless a concrete SASE use case appears:

- **Dolt, server modes, federation, and pluggable SQL storage.** SASE's event streams and sidecar Git model are healthy
  at 1,479 issues. Changing storage would spend effort on migrations, locking, replication, and recovery instead of user
  value.
- **Molecules, formulas, protos, wisps, and generic gates.** SASE plans, xprompts, `%wait`, approval actions, and agent
  families already occupy this layer.
- **Agent mail or message issue types.** SASE questions, notifications, chat integrations, and agent artifacts are the
  communication plane.
- **Arbitrary custom types and statuses.** They weaken predictable ready/work/land semantics and increase every query
  and UI surface's state space.
- **A broad label taxonomy.** Priority, kind, provenance, owner, plan, and ChangeSpec answer the known queries. Labels
  can wait for evidence.
- **External tracker synchronization.** ChangeSpecs and VCS-provider plugins are the correct integration point.
- **AI duplicate detection, raw SQL, and generic dashboard ecosystems.** Search and a small TUI view are sufficient at
  current scale.

## Suggested implementation sequence

The shared behavior belongs in the Rust core under the documented backend boundary. Python should remain the CLI/TUI
adapter and orchestration layer.

| Sequence | Slice | Why this order |
| ---: | --- | --- |
| 1 | Stable plan refs, migration, doctor validation | Repairs historical value with minimal workflow risk |
| 2 | Close guards, resolution, state reconciliation checks | Stops new false completion records immediately |
| 3 | Dependency removal/tree/check and history surfaces | Makes the existing graph and event log operable |
| 4 | Atomic plan-to-epic compiler | Removes the largest multi-command creation failure window |
| 5 | Atomic claim and agent-liveness reconciliation | Makes manual and retry workflows concurrency-safe |
| 6 | Follow-up capture with priority/deferral/provenance | Creates a real persistent ready frontier |
| 7 | Skill rewrite, JSON contracts, optional ACE queue view | Teaches and surfaces the completed model |

Each slice should include event-schema compatibility and a migration/rollback story. Avoid adding new fields in advance
of the slice that consumes them.

## Most impactful improvements to make

In priority order, these are the changes most likely to improve day-to-day SASE work:

1. **Make plan linkage durable.** Replace filesystem `design` paths with logical SDD references, backfill them from
   `bead_id` frontmatter, and teach `doctor` to validate the relationship. Today 220 of 228 links fail as stored.
2. **Prevent false completion.** Remove default cascade close, require all children to be genuinely complete, add a
   small resolution enum, and require a reason for forced closure. The live store already contains closed beads that
   explicitly say they must remain open.
3. **Create epic graphs atomically from plans.** Replace LLM-driven sequences of create/dep/frontmatter operations with
   a dry-runnable, idempotent Rust transaction that compiles the normal SASE plan format.
4. **Add atomic claim plus liveness-based reconcile.** Eliminate the `ready`/`update` race and recover dead-agent claims
   using SASE's real agent metadata instead of importing a generic heartbeat subsystem.
5. **Turn the event store into usable handoff memory.** Add history and append-note surfaces, and record commits,
   attempts, ChangeSpecs, and verification as structured append-only evidence instead of overwriting `notes`.
6. **Create a small persistent follow-up queue.** Add `capture`, priority, deferral, and `discovered_from` provenance so
   work found during an epic survives into a later `ready` frontier without broadening the active phase's scope.
7. **Finish the narrow graph UX and teach it accurately.** Add dependency removal/tree/check, readiness explanations,
   stable JSON, and a generated `sase_beads` skill centered on `sase bead work` and recovery.

If only three improvements are funded, choose **durable plan references, truthful close semantics, and atomic
plan-to-epic creation**. Together they make the existing system substantially more trustworthy without making it much
larger.
