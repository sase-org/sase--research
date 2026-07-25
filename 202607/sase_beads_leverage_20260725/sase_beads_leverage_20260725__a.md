# SASE Beads at Full Potential: A Reassessment

Date: 2026-07-25

## Executive conclusion

Bryan is already using SASE beads very effectively as a **parallel execution engine**. The live store shows real DAGs,
fan-out/fan-in, rapid throughput, deterministic phase agents, and increasingly sophisticated recovery behavior. The
main opportunity is no longer “use more dependencies.” It is to turn beads into three connected loops:

1. **Capture and triage:** retain work discovered during other work, then make the next useful action obvious.
2. **Budgeted execution:** use phase sizes, dependency waves, child epics, and ChangeSpec linkage deliberately.
3. **Learning and trust:** preserve evidence, measure flow, and enforce invariants so the archive is reliable.

The July 14 consolidated report was directionally right, but the implementation has moved quickly. Two of its lower
ranked product recommendations—atomic plan-to-epic compilation and runtime-managed claiming/reconciliation—are now
substantially implemented. Five phase sizes, recursive child epics, bead-gated waits, and rich plan surfaces also exist.

The strategic gap remains: beads still have no low-ceremony standalone task or `discovered-from` relationship. The
operational gap has become more urgent: the current `ready` output is polluted by test-created beads, most historical
plan references remain broken, and recursive close can still create records contradicted by their own notes.

My updated headline is:

> SASE beads are already a strong execution graph. Their next level is a trustworthy work inbox and an empirical
> feedback system—not a larger issue tracker.

## Scope and method

This reassessment used:

- the required prior report,
  [`sase_beads_full_potential_consolidated.md`](sase_beads_full_potential_consolidated/sase_beads_full_potential_consolidated.md),
  plus its two companion analyses;
- the live SASE bead projection and canonical event streams at a 2026-07-25 09:55 EDT snapshot;
- the current CLI, bead documentation, generated skill source, recent implementation history, and current plan archive;
- graph analysis of every plan's direct phase DAG;
- the current upstream `gastownhall/beads` checkout at commit
  `508d359211243a2ae903bb4237823ca2184e57e7`, particularly its lightweight TODO, dependency, history, note, and
  coordination documentation.

No bead records were created, edited, closed, reopened, or removed during this research.

The live store changes while agents work. Counts below are a timestamped observation, not a permanent audit fixture.
The plans-sidecar snapshot was commit `e25d06baa374269888d49048c03e94a1708cf996`.

## What changed since the July 14 report

The earlier report's most important contribution was separating the excellent execution engine from the missing living
memory. That distinction still holds, but several details need updating.

| July 14 finding or recommendation | July 25 state | Updated interpretation |
| --- | --- | --- |
| Store was 1,479 closed, zero active | 2,014 total: 19 open, 7 in progress, 1,988 closed | Beads now show live execution well, but all 26 active records were created today; there is still no standing backlog |
| Compile plans to epic graphs atomically | Implemented in `sase bead work <plan.md>` with validation, archive, rollback, idempotent `bead_id`, dry-run, and JSON | Remove this from the future roadmap; use it consistently |
| Add atomic claims and liveness reconciliation | Implemented through `claimed`, just-in-time promotion, release, reconciliation, and current follow-up hardening | Manual `ready → update in_progress` is no longer the primary workflow |
| Three coarse phase sizes | Five sizes now exist: `xsmall`, `small`, `medium`, `large`, `xlarge`, with role-based model routing | This creates a new opportunity: treat size as an execution budget and calibrate it empirically |
| Flat epic/phase hierarchy | Parented child epics and recursive lineage now exist; bead-gated waits hold dependents until delegated child epics land | Progressive decomposition is now a first-class workflow |
| Plan linkage mostly broken | New linkage is much better, but only 103 of 320 current plan refs resolve through the current resolver; 217 still fail | New writes improved; migration and validation remain necessary |
| Commit stamps overwrite useful notes | Still true in the snapshot; 1,449 of 1,590 non-empty notes begin with `COMMIT:` or `COMMITS:` | A WIP July 25 tale now proposes stopping new commit-note writes, but history/backfill remains unsolved |
| No trustworthy close semantics | Still true; recursive parent close remains documented behavior | The old contradictory examples remain closed and unchanged |
| Agent skill omits the main workflow | Still true, and the gap has widened as the product added sizes, claims, child epics, recovery, and plan-file launch | This is now one of the cheapest high-impact fixes |
| No living capture queue | Still true | Remains the largest strategic capability gap |

## What the live store says

### Inventory and flow

At the snapshot:

| Measure | Observed |
| --- | ---: |
| Total beads | 2,014 |
| Plan beads | 320 |
| Phase beads | 1,694 |
| Open / claimed / in progress / closed | 19 / 0 / 7 / 1,988 |
| Active beads created before July 25 | 0 |
| Beads created July 15–25 | 526 |
| Of those 526, already closed | 500 |
| Compatibility projection | 1.64 MB |
| Canonical event streams | 5.0 MB, 7,966 events |

The July 14 “completed-work ledger” diagnosis should therefore be refined:

- Beads are no longer invisible while execution is happening.
- They are still **ephemeral at the portfolio level**: every active bead is from the current day.
- They still retain almost no future work between execution cycles.

That is a healthy execution queue and an absent backlog, not one undifferentiated problem.

### The dependency scheduler is already being used well

Among 92 plan graphs created since July 15:

- 421 direct phases were created, averaging 4.58 per graph.
- 52 graphs have at least one parallel wave.
- 49 have fan-in.
- 33 are strictly linear.
- Only 4 have no dependency edges.
- The widest recent graph has 11 phases in one wave.

Across the full store, 125 of 305 graphs have parallel waves and 123 have fan-in. This is strong evidence that the
scheduler is not an unused feature.

The useful improvement is qualitative: make graphs express **uncertainty, independent ownership, and convergence
points**, not merely component boundaries. A phase graph should explain why work may proceed in parallel and what
evidence must exist before it converges.

### `ready` is not yet a human-ready queue

At the snapshot, `sase bead ready` printed 10 records:

- all 10 were plan beads;
- five were legitimate live epic containers;
- five were obvious test fixtures (`sase-97`, `sase-9a`, `sase-9b`, `sase-9c`, `sase-9d`);
- no ready phase appeared.

The five test records were created in a tight sequence, have fixture titles such as `Created Epic` and `Epic`, and
carry paths such as `.localtmp/pytest-of-bryan/...`, `.pytest_cache/...`, `plan.md`, and
`sdd/plans/202605/roadmap.md`. The source tests create exactly these titles, descriptions, ChangeSpec values, and paths.
Their helpers change directory and mock primary-workspace resolution but do not clear inherited `SASE_SDD_*`
variables, allowing a launched-agent test run to target the real sidecar.

This yields two conclusions:

1. Test isolation is currently a bead-store integrity issue, not ordinary test hygiene.
2. `ready` mixes “epic container can be launched” with “phase can be worked” and, eventually, “captured task needs
   triage.” Those need distinct action-oriented views.

### New plan references are better, but the archive is still mostly disconnected

Using the current plan resolver with the current workspace and plans sidecar:

- 103 of 320 plan-bead references resolve.
- 217 fail.
- Of 105 plan beads created since July 15, 94 resolve and 11 fail.

Most new production references use the correct sidecar-aware form. The failures are dominated by test artifacts, but
there is also at least one real recent regression: `sase-85` stores `202607/epic_clan_summary_rich.md`; the resolver
prefers the sidecar's surviving nested `plans/` directory and misses the actual root-level `202607/` file.

`sase bead doctor` did not report any of these broken references or temp-path records. It only warned that `beads.db`
was missing.

The earlier report's migration recommendation is therefore still valid, but its framing can improve:

- prevent new bad refs;
- repair legacy refs;
- validate the **same resolution algorithm used by the TUI and plan-opening surfaces**;
- treat temp-directory and numbered-workspace references as a separate high-confidence error class.

### Completion is still not a reliable fact

Recursive parent close remains documented behavior. The July 14 contradictory records remain:

- `sase-5t` and `sase-5t.5` are closed while their notes say to keep them open until recovery edits have a durable
  commit and ChangeSpec/PR;
- `sase-31.6` is closed while its notes say master CI still fails.

A useful archive needs more than a status enum. It needs a close invariant and a resolution:

- `done`: acceptance evidence exists;
- `canceled`: intentionally not completed;
- `superseded`: replaced by another bead or plan.

Closing a parent should fail while descendants are unresolved. Forced closure should require a reason and retain which
descendants were not done.

### The event store is an unused learning system

The canonical streams contain:

- 1,560 note-update events;
- 916 issues with a note update;
- 511 issues with multiple note revisions.

The projection exposes only the latest value. At the same time, 1,449 of 1,590 current non-empty notes begin with
commit bookkeeping, so the human-readable state is dominated by evidence that is often stale after amend or rebase.

A July 25 WIP tale, `202607/drop_bead_commit_note.md`, correctly proposes stopping the automated `COMMIT: <sha>`
overwrite. It also documents that no consumer relies on the field and that ChangeSpecs already carry the durable
post-rebase commit. That is a good immediate fix, but it does not:

- restore overwritten historical notes;
- expose event history;
- structure verification evidence;
- derive flow metrics from timestamps and transitions.

The event store already contains enough information to become a lightweight process-observability system without
changing backends.

### Phase size is implemented but not calibrated

Only 175 phases currently carry a stored size:

| Size | Count |
| --- | ---: |
| `xsmall` | 0 |
| `small` | 55 |
| `medium` | 110 |
| `large` | 10 |
| `xlarge` | 0 |

The absence of `xsmall` and `xlarge` is not yet evidence of failure—the five-size feature landed only recently—but it
means the new routing ladder has not accumulated real operating data.

The current semantics are well chosen:

- `xsmall`: trivial observation or exercise, almost no reasoning;
- `small`: focused direct implementation;
- `medium`: substantial direct implementation;
- `large`: separate planning handoff, possibly a child epic;
- `xlarge`: deliberately deferred or too large to plan effectively in isolation.

The opportunity is to measure whether these labels predict duration, retries, child-epic delegation, model cost, and
landing defects.

### Child epics are useful but still rare

There are 12 parented plan beads:

- seven are the older Mobile MVP program decomposition;
- two are explicit child-epic tests;
- three are recent production “finish and land” child epics.

The recent production examples reveal a promising pattern: a phase that becomes a meaningful graph of its own can
delegate to a child epic without losing lineage. Bead-gated waits keep the original phase and downstream work honest
until the child epic lands.

This should become an explicit escalation rule, not something agents discover ad hoc.

### ChangeSpec linkage is implemented but unused in production

Four beads carry ChangeSpec and bug metadata. All four are recognizable test fixtures. There is no live-store evidence
of production use.

That leaves a useful existing capability dormant. For PR-backed epics, ChangeSpec metadata gives the graph a durable
delivery spine:

`plan → epic → phases → ChangeSpec/bug → commits → landing`

It also provides a better home for commit provenance than mutable bead notes.

### The agent skill teaches an obsolete workflow

The CLI currently has 18 top-level verbs:

`blocked`, `close`, `create`, `dep`, `doctor`, `init`, `list`, `onboard`, `open`, `ready`,
`resolve-conflicts`, `rm`, `search`, `show`, `stats`, `sync`, `update`, and `work`.

The generated `sase_beads` skill meaningfully documents seven of them and still ends with:

`create manually → add phases manually → add deps manually → ready → update in_progress → close`

It omits or under-teaches:

- canonical `sase bead work <plan.md>`;
- `--dry-run`, JSON plan compilation, idempotent resume, and safe retry;
- phase size and size-derived model routing;
- child epics and bead-gated waits;
- runtime-managed `claimed` lifecycle in the actual execution flow;
- `close --reason`, `open`, `blocked`, `stats`, `doctor`, `sync`, `rm`, conflict recovery, and ChangeSpec metadata.

This matters because generated skills are the discoverability layer for agents. A capability absent from the skill may
as well be hidden.

## Useful ways to use beads now

These practices need no new data model.

### 1. Use a short execution-control ritual

Before approving or resuming expensive work:

```bash
sase bead work path/to/epic.md --dry-run
sase bead show <epic-id>
sase bead blocked
sase bead doctor
sase bead sync --status
```

During recovery:

```bash
sase bead list --status open --status claimed --status in_progress
sase bead show <phase-or-epic-id>
sase bead work <epic-id>
```

`sase bead work <epic-id>` is the primary retry mechanism. Do not manually set `claimed`; the runner owns that state.
Use `open` only for an intentional reopen and `close --reason` whenever completion is not an ordinary successful
delivery.

Do not treat today's unfiltered `ready` output as a personal task list. Inspect type and lineage with `show`.

### 2. Design graphs around convergence, not directories

Useful graph shapes include:

**Parallel investigation**

```text
reproduce ─┬─ hypothesis A ─┐
           ├─ hypothesis B ─┼─ synthesize ─ verify
           └─ hypothesis C ─┘
```

**Cross-cutting delivery**

```text
contract ─┬─ core implementation ─┐
          ├─ frontend/adapters ───┼─ integration ─ end-to-end evidence
          └─ migration/docs ──────┘
```

**Risk-first rollout**

```text
spike → decision → implementation → canary → rollout → cleanup
```

Make the final fan-in phase produce explicit evidence. The land agent should validate integration, but it should not be
the first place where cross-phase acceptance is exercised.

### 3. Treat phase size as a budget

Use the five sizes as policy, not prose:

| Size | Good use | Warning sign |
| --- | --- | --- |
| `xsmall` | Observation-only smoke, trivial fixture/update, narrow mechanical proof | The task changes consequential behavior |
| `small` | One focused change with obvious verification | The description contains multiple independent deliverables |
| `medium` | Substantial direct implementation from a precise description | The worker must first decide the architecture |
| `large` | Work needing an explicit planning handoff or likely child epic | The parent plan pretends the implementation is already known |
| `xlarge` | Intentional progressive elaboration after prerequisite evidence | Used merely to request a stronger model |

Explicit per-phase models should remain exceptional. Size-derived role aliases are a cleaner policy surface and make
later measurement possible.

### 4. Use child epics as controlled scope escalation

A phase should propose a child epic when:

- it discovers multiple independently schedulable deliverables;
- the architecture cannot be responsibly fixed in the original phase description;
- it needs a separate landing/reconciliation boundary;
- work should remain visibly subordinate to the original goal.

It should not create a child epic just because a phase is inconvenient. The escalation threshold should roughly match
`large` or `xlarge`. The parent phase remains open; bead-gated waits ensure its dependents do not proceed on the mere
completion of the original agent.

This gives SASE progressive elaboration without introducing upstream-style formulas or molecules.

### 5. Attach real PR-backed epics to ChangeSpecs

When an epic is expected to create or continue a ChangeSpec, put the ChangeSpec and bug metadata in the approved plan
instead of leaving them implicit. This lets `sase bead work` route the first phase through the project/PR context and
subsequent phases and the lander through the ChangeSpec context.

The goal is not duplicate tracking. The bead owns execution structure; the ChangeSpec owns delivery/commit lifecycle.

### 6. Use search as the current archive index

For recurring failures or architectural areas:

```bash
sase bead search "claim" --format full --limit 5
sase bead search "CI" --status closed --type phase --format full --limit 10
sase bead search "changespec" --type plan --format compact
```

Search includes closed beads and matches titles, descriptions, notes, plan refs, assignees, models, sizes, and
ChangeSpec metadata. It is more useful than dumping every closed record.

Treat results as leads, not proof, until plan-link repair and truthful close semantics land.

### 7. Run a weekly bead retrospective

A short review should ask:

- Which open or in-progress beads are older than expected?
- Which phases were reopened or retried?
- Which graphs had avoidable serial dependencies?
- Which “small” phases became plans, and which “large” phases finished directly?
- Which child epics represented healthy discovery versus poor initial decomposition?
- Which closed beads have cancellation/supersession semantics hidden inside notes?
- Which follow-ups were mentioned but never captured?

Today this review requires event analysis and judgment. A future metrics surface should make it routine.

## Product improvements that unlock new uses

### A. Add a capture inbox without building a second tracker

The minimal model remains:

- a standalone `task` bead with no required plan or parent;
- a non-blocking `discovered-from` relationship;
- `sase bead capture "..."`, defaulting provenance from ambient bead context;
- optional `defer_until`, distinct from dependency blocking;
- promotion from captured task to planned epic while retaining provenance;
- phase and land prompts that capture follow-up work worth more than a couple of minutes.

Upstream's current `bd todo` design reinforces the right product shape: TODO is a convenience layer over normal task
records, not a parallel store. SASE should borrow that narrow idea but omit priority and labels until a real backlog
demonstrates a query that needs them.

Captured content must remain untrusted agent-authored data. A bead is memory, not authorization.

### B. Make trust a product invariant

One integrity program should cover:

1. **Hermetic tests:** clear or replace inherited `SASE_SDD_PLANS_DIR`, `SASE_SDD_BEADS_DIR`, and related project
   routing in tests; refuse to let pytest fixture operations auto-commit into a real sidecar.
2. **Quarantine current debris:** review the five open fixture beads, then remove them through the supported command
   only after confirming exact targets.
3. **Plan-link doctor:** run the production resolver for every plan bead, flag temp/numbered-workspace refs, detect
   bead/frontmatter mismatches, and migrate repairable legacy paths.
4. **Truthful close:** reject parent close with unresolved descendants; require force plus reason for exceptional
   closure; add `done`, `canceled`, and `superseded` resolution.
5. **Reopen consistency:** reopening a child should reopen or explicitly invalidate the parent's successful resolution.

Until these hold, expanding the backlog magnifies noise.

### C. Replace state-oriented `ready` with action-oriented triage

Keep the raw query, but add views that answer different questions:

- **Inbox:** captured tasks requiring triage.
- **Launchable:** approved epic plans not already executing.
- **Ready phases:** unblocked phase work eligible for manual or automated scheduling.
- **Claimed/waiting:** reserved by live agents.
- **Blocked:** unresolved prerequisites, with explanation and age.
- **Needs attention:** stale, orphaned, invalid-ref, failed, canceled, or contradictory records.

Add stable JSON to `list`, `ready`, `show`, `blocked`, `stats`, and the new views. Then implement the already-researched
cross-project AXE open-bead tree as a read/triage surface, not full TUI CRUD.

### D. Turn event history into evidence and flow metrics

Add:

- `sase bead history <id>`;
- append-only evidence/comment events;
- structured commit, ChangeSpec, PR, verification, retry, and resolution references;
- historical-note recovery where event streams retain overwritten values;
- `sase bead stats --flow --since ...`.

High-value derived measures are:

- queue wait: create to first execution;
- execution time: first execution to resolution;
- blocked time and critical-path delay;
- reopen/retry/delegation rate;
- phase duration and defect rate by size and model role;
- authored wave plan versus realized concurrency;
- WIP age and throughput;
- false or forced closure count.

This is the most novel opportunity beyond the prior report. The event-sourced design and new size/model metadata make
beads a natural continuous-improvement instrument. No new database is required.

### E. Teach the real product

Rewrite the generated `sase_beads` source template around:

`approved plan → dry-run → atomic compile → launch → claimed/waiting → retry/delegate → evidence → land`

Include:

- five-size policy;
- plan-file and bead-ID `work`;
- child epic behavior;
- ChangeSpec metadata;
- active/blocked inspection;
- safe retry and reopen;
- close reasons and integrity rules;
- doctor, sync, and conflict recovery;
- destructive `rm` warnings.

Add a contract test comparing the parser's public verbs/options with the skill's documented surface. Update the source
template, regenerate, and deploy; do not hand-edit provider copies.

### F. Finish graph diagnostics, not graph vocabulary

The useful remaining commands are small:

- `dep list`;
- `dep rm`;
- `dep tree`;
- `ready --explain`;
- a wave/critical-path view reusing `work --dry-run`;
- stable JSON.

Do not import upstream's broad typed graph, gates, formulas, molecules, wisps, mail, server leases, or federation.
SASE already owns planning, orchestration, waits, agents, notifications, VCS delivery, and memory.

If a second non-blocking relationship proves necessary after `discovered-from`, `validates` is the best candidate
because it connects explicit evidence to delivery. Do not add a generic taxonomy in advance.

## Suggested success criteria

The following signals would show that beads are becoming more useful rather than merely larger:

| Objective | Useful signal |
| --- | --- |
| Trustworthy store | Zero pytest/temp-path beads; zero unresolved plan refs created by current code; zero contradictory normal closes |
| Living memory | Discovered follow-ups survive across days and retain source provenance |
| Useful triage | Most entries in the default human queue correspond to a clear next action |
| Calibrated routing | Size predicts execution time, delegation, retry, and model cost well enough to guide planning |
| Better decomposition | Parallelism is intentional; fan-in phases carry acceptance evidence; unnecessary linear epics decline |
| Durable delivery lineage | Real PR-backed epics carry ChangeSpec/bug metadata and structured landed evidence |
| Agent discoverability | Generated skill covers every supported primary workflow and passes CLI/skill parity checks |
| Learning loop | Weekly review can be answered from commands/TUI without manual event-stream analysis |

## Sources

- Prior consolidated analysis and its companions:
  `202607/sase_beads_full_potential_consolidated/`.
- Current SASE documentation and implementation:
  `docs/beads.md`, `docs/sdd.md`, `docs/llms.md`, `src/sase/main/parser_bead.py`,
  `src/sase/plan_documents.py`, `src/sase/xprompts/skills/sase_beads.md`, and recent bead-related history through
  primary commit `596521653e220b29c3155b53aa464226b99a99ba`.
- Live plans sidecar:
  `beads/issues.jsonl`, `beads/events/streams/*.jsonl`, active plans, and git history at the timestamped snapshot.
- Earlier SASE research:
  `202603/sase_beads.md`, `202605/axe_open_bead_tree.md`,
  `202605/greenfield_bead_storage_architecture.md`, and `202605/bead_jsonl_merge_conflicts.md`.
- Current upstream Beads checkout:
  `gastownhall/beads` at `508d359211243a2ae903bb4237823ca2184e57e7`, especially
  `docs/workflows/todo.md`, `docs/core-concepts/dependencies.md`, `docs/multi-agent/coordination.md`,
  `docs/cli-reference/history.md`, and `docs/cli-reference/note.md`.

## Ranked recommendations

1. **Make the bead store trustworthy before expanding it.** Fix inherited-`SASE_SDD_*` test leakage, review and remove
   the five current fixture beads, add production-resolver plan-link checks and migration to `doctor`, and enforce
   truthful close/reopen semantics. This is first because today's `ready` result is 50% test debris and historical
   completion records still contradict themselves.
2. **Add the standalone capture inbox.** Ship a normal `task` bead, `sase bead capture`, non-blocking
   `discovered-from`, optional deferral, promotion to a planned epic, and prompt-side capture discipline. This is the
   largest strategic unlock: it turns same-day execution state into durable cross-session memory.
3. **Rewrite the generated bead skill around the real execution lifecycle.** Teach plan-file dry-run/compile/work,
   five sizes, claims, child epics, ChangeSpecs, retry, evidence, landing, doctor, and recovery; enforce CLI/skill
   parity in tests. This is low effort and unlocks capabilities that already exist.
4. **Create action-oriented triage surfaces.** Separate inbox, launchable epics, ready phases, claimed/waiting,
   blocked, and needs-attention views; add JSON to every read command and build the cross-project AXE bead tree.
   The current raw `ready` semantics cannot serve humans or automation well.
5. **Expose history and turn bead events into flow metrics.** Finish the in-progress commit-note fix, add history and
   append-only structured evidence, recover useful old notes, and report wait time, cycle time, blocked time, retries,
   critical path, and size/model outcomes. This converts the archive into a continuous-improvement system.
6. **Adopt an explicit size and child-epic policy now.** Use `xsmall` for observation-only work, reserve
   `large`/`xlarge` for plan-first or progressively elaborated work, and require a clear escalation reason for child
   epics. Review the policy weekly until the five-size ladder is empirically calibrated.
7. **Use ChangeSpec and bug metadata on real PR-backed epics.** Let beads own execution topology and ChangeSpecs own
   delivery/commit lifecycle. The feature is implemented, but all four current examples are fixtures.
8. **Finish narrow graph ergonomics.** Add `dep list`, `dep rm`, `dep tree`, `ready --explain`, and a reusable
   wave/critical-path view. Stop there unless live usage proves the need for more link types or workflow machinery.
