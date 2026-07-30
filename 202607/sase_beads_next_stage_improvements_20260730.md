# SASE Beads: Next-Stage Improvements

Date: 2026-07-30

## Executive conclusion

SASE beads have crossed an important maturity threshold. They are no longer merely an epic launcher with a thin issue
record behind it. In the last several days alone, SASE added durable event history, append-oriented notes, typed close
resolutions, guarded parent closure, dependency inspection/removal, JSON list/show output, generated bead pages, a
dedicated beads sidecar, stronger claim recovery, and much better documentation.

That changes the improvement agenda.

The largest remaining opportunity is not more CRUD and not copying upstream Beads' growing workflow vocabulary. It is
to make the existing system:

1. **lossless under concurrent agent writes;**
2. **decisive about which agent owns work;**
3. **cheap to merge and synchronize;**
4. **queryable enough to select the right work; and**
5. **analytical enough to learn from 2,400 completed work records.**

The highest-value recommendation is to replace the mutable `notes` snapshot with first-class append-only journal
events. The current command appends safely inside one local store lock, but the canonical event still contains the
whole accumulated notes string. Two independent workspace clones can therefore append from the same base and later
reduce to last-writer-wins text. The live audit still finds **301 beads with dropped historical note revisions**.
That is a direct contradiction between the event-sourced design and the memory it is meant to preserve.

Second, add a real `ready --claim` transaction with compare-and-set semantics and a publication barrier. The documented
manual loop is still `ready` followed by a blind `update --status in_progress`; it can launch two agents against the
same bead. Runner-managed claims are much stronger than they were, but they are explicitly best-effort before work
starts, and an `in_progress` owner that dies after promotion is intentionally permanent.

Third, remove the canonical storage hotspot in which every agent working on one epic appends to the same
`events/streams/<root-epic>.jsonl` file. The semantic conflict resolver has become impressively robust, but it is
solving a collision pattern the storage layout creates by construction.

Everything else in this report builds on those three changes.

## Scope and method

This report is a fresh successor to:

- [SASE Beads: Getting To Full Potential (2026-07-14)](sase_beads_full_potential_consolidated/sase_beads_full_potential_consolidated.md)
- [Getting More Leverage Out Of SASE Beads (2026-07-25)](sase_beads_leverage_20260725/sase_beads_leverage_20260725.md)

Those reports remain useful, but repeating their ranking would be misleading because much of it has already shipped.
This analysis therefore:

- inspected the live SASE bead store through the public CLI and canonical event streams;
- inspected the current SASE and Rust-core bead implementations and recent Git history;
- checked current command contracts rather than relying on the earlier reports;
- reviewed the current upstream Beads repository at commit `0e069115a231c537a83bb77a5106fe7c0efb47f2`;
- compared selected practices from GitHub Projects, Linear, Taskwarrior, Temporal, and upstream Beads; and
- ranked improvements by observed SASE impact, not by competitor feature count.

Code and data snapshots used:

| Repository     | Commit                                     |
| -------------- | ------------------------------------------ |
| `sase`         | `a4880ce321df4a9afdf1a2be5ce86eed8a5860fe` |
| `sase-core`    | `1355649d6bc2306ca5b8ab386772237c05f1f07a` |
| `sase--beads`  | `8499ede6e542736116bb62a668c79ce25088f0f1` |
| `sase--plans`  | `ca4c91b75aa0cb257640fdd0649dd898b15e5bc7` |
| upstream Beads | `0e069115a231c537a83bb77a5106fe7c0efb47f2` |

The live store was read but not mutated.

## Current state

### Store shape and activity

As of the snapshot:

| Measure                                                     |       Value |
| ----------------------------------------------------------- | ----------: |
| Total beads                                                 |       2,417 |
| Closed                                                      |       2,401 |
| In progress                                                 |          16 |
| Open / claimed                                              |       0 / 0 |
| Plan / phase beads                                          | 377 / 2,040 |
| Root event streams                                          |         421 |
| Canonical events                                            |      10,729 |
| Dependency edges in the current projection                  |       1,913 |
| Beads with at least one dependency                          |       1,494 |
| Beads closed in the last 7 days                             |         391 |
| Live-store checkout size, including Git and generated pages |       31 MB |
| Git pack size                                               |    7.01 MiB |

The store is not large enough to justify urgent compaction. It is large and active enough that discovery, selection,
integrity, and flow analysis can no longer be treated as future concerns.

For the 1,758 closed beads with parseable create and close timestamps:

| Create-to-close percentile |                     Duration |
| -------------------------- | ---------------------------: |
| p50                        |   3,906 seconds (65 minutes) |
| p90                        |   14,628 seconds (4.1 hours) |
| p95                        |  52,813 seconds (14.7 hours) |
| p99                        | 103,552 seconds (28.8 hours) |

These are not true execution-time measurements because creation can precede the first work transition. That limitation
is itself evidence for a flow-metrics improvement: the event store can derive queue time, first-start time, retry time,
and completion time separately.

### Current strengths

The system already has an unusually strong base:

- Rust-owned validation, mutation, reduction, history, and search behavior.
- Append-only canonical event streams with deterministic semantic merge.
- A generated JSONL compatibility projection and rebuildable SQLite cache.
- Hierarchical plans/phases and executable epic tiers.
- Dependency-aware wave scheduling and bead-gated agent waits.
- Batch epic preassignment before launch.
- Runner-aware `claimed` and `in_progress` transitions.
- Typed `done`, `canceled`, and `superseded` closure resolutions.
- Descendant-aware close guards and explicit forced closure.
- Attributed notes, history, lost-note detection, and opt-in restoration.
- Generated public pages associated with plans, agents, and commits.
- Readable and JSON forms for the most important inspection commands.

This is why a broad rewrite would be wasteful. The recommendations below extend the current event model and reuse the
existing SASE agent registry, query machinery, statistics surfaces, artifact references, and Rust boundary.

### Current weak points

Five facts dominate the next-stage design.

#### 1. Notes are append-shaped in the CLI but snapshot-shaped in storage

`append_issue_note` reads the current `notes` text, concatenates an attributed entry, and emits an `issue_updated`
event containing the entire new string. The local mutation lock prevents two writers in one clone from clobbering each
other. It does not make two independently based Git clones commutative.

The live command:

```text
sase bead history --lost-notes --format json
```

currently reports **301 findings**. Many contain exactly the information beads should retain: verification commands,
blocked-state explanations, decisions, and handoffs that were later replaced by commit bookkeeping.

The July 27 repair added visibility and a recovery path, which was the correct immediate move. The next move should
remove the representation that makes lost text possible.

#### 2. Ready-work acquisition remains check-then-act

`sase bead ready` still accepts no filters and has no claim option. `sase bead update` has no
`--if-status`, `--if-assignee`, or version precondition. A generic agent therefore:

1. reads the ready set;
2. chooses a bead;
3. blindly changes it to `in_progress`; and
4. starts work.

Two agents can make the same choice from different clones. Upstream Beads addresses this with an atomic
`ready --claim`, filters, and a clear losing claimant; its current command also supports an explanation of why work is
ready or blocked ([upstream `bd ready`](https://beads.gascity.com/cli-reference/ready)).

SASE's runner-managed lifecycle reduces this risk for launched agents, and `sase bead work` avoids it by preassigning
the whole epic. It does not eliminate the ad-hoc race, and it deliberately leaves post-promotion `in_progress` work
permanent after an owner dies.

#### 3. Parallel phase agents share one canonical Git file

The Rust event model assigns every issue and edge in a lineage to the root issue's stream:

```text
phase A ─┐
phase B ─┼──> events/streams/<epic-id>.jsonl ──> issues.jsonl ──> pages
phase C ─┘
```

This is compact and makes lineage replay convenient. It also ensures that the workload SASE optimizes for—parallel
phase agents—is the workload most likely to modify the same file in diverged clones.

The merge machinery now semantically unions append-only branches and validates reduction before accepting the result.
That is excellent defensive engineering. It has also required repeated fixes around rebase/merge convergence,
publication races, local write locks, no-op commits, claim persistence, and generated-page conflicts. As a rough
maintenance signal, from July 20 through the snapshot there were 110 commits touching bead code/docs, 41 with `fix`
subjects, and 34 whose subjects referenced synchronization, claims, conflicts, rebases, locks, sidecars, or commit
coordination. These counts measure a period of rapid development, not defect rates, but they identify the subsystem
absorbing attention.

#### 4. Querying and statistics lag behind the data

The current surfaces are asymmetric:

- `list` filters by status/type/tier and supports JSON.
- `search` is one case-insensitive literal substring plus status/type/tier filters.
- `show` supports full graph detail and JSON.
- `ready`, `blocked`, and `stats` accept no substantive options.
- `stats` prints six counts.

SASE already owns a Rust query parser/evaluator and saved-query infrastructure for ChangeSpecs. A bead query corpus
would be a reuse/generalization problem, not a greenfield parser.

Mature trackers consistently couple typed fields with compound filters, reusable views, sorting, and charts.
GitHub issue fields can drive grouping, filtering, sorting, and charts
([GitHub issue fields](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields/about-issue-fields));
Linear supports nested AND/OR filters and reusable views
([Linear filters](https://linear.app/docs/filters)); and upstream Beads exposes field/date comparisons with Boolean
operators ([upstream `bd query`](https://beads.gascity.com/cli-reference/query)).

SASE does not need all of their metadata. It does need comparable expressive power over the fields it already stores.

#### 5. Completion evidence is still prose

The close guard and typed resolution fixed the largest truthfulness problems identified by earlier research. The
remaining completion contract is informal:

- an agent is prompted to close with a verification note;
- `close --note` appends text and closes atomically;
- the note is not structurally distinguished from a progress or handoff note;
- commands, exit status, commits, artifacts, and waivers are not a typed completion record; and
- the CLI does not require evidence for a `done` phase or epic.

Of the 391 beads closed in the last seven days, 242 have non-empty notes. This interval spans the rollout of the new
close-note and resolution features, so the ratio should not be treated as current-agent compliance. It does show why
historical analysis cannot equate “closed” with a uniform evidence standard.

## Progress since the July reports

The earlier reports were productive. Their recommendations should be retired or narrowed where they have landed.

| Earlier concern                                       | Status on 2026-07-30                                                                                                                                                             |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Test fixtures leaking into the production store       | Fixed in code history; the current active set contains real running epics rather than fixture-ready work.                                                                        |
| Generated beads skill covered only a small CLI subset | Fixed. The current skill documents lifecycle, claims, sizes, close semantics, history, notes, formats, dependencies, and work.                                                   |
| Design links were unchecked                           | Substantially improved. `doctor` now checks design references and can preview repairs, although the live store still reports 14 malformed/missing links and 14 owner mismatches. |
| History was invisible                                 | Fixed with compact/full/JSON history and field filters.                                                                                                                          |
| Notes only replaced prior text                        | Improved with attributed append and lost-note restoration, but the canonical event still stores a whole-text snapshot.                                                           |
| Parent close could manufacture completion             | Fixed with descendant guards, explicit forced sweeps, and typed resolutions.                                                                                                     |
| Dependency edges could not be inspected or removed    | Fixed with `dep list`, `dep tree`, and atomic `dep rm`.                                                                                                                          |
| Machine-readable reads were sparse                    | Partially fixed: `list`, `show`, and `search` support JSON; `ready`, `blocked`, and `stats` do not.                                                                              |
| Beads were hard to browse outside running-agent rows  | Improved through the ACE Plans surfaces and generated bead pages.                                                                                                                |
| Atomic ad-hoc ready-work acquisition                  | Not fixed.                                                                                                                                                                       |
| Flow/size/model analytics                             | Not fixed.                                                                                                                                                                       |

This implementation velocity is another reason to prefer focused next steps over a new tracker architecture.

## Design principles for the next stage

1. **Keep Git-native canonical state.** Do not adopt Dolt, a required daemon, or a server as the source of truth.
2. **Make concurrent mutations commute whenever the domain allows it.** Notes and relation additions should union,
   not compete as snapshots.
3. **Put shared behavior in `sase-core`.** Query, claim preconditions, event identity, relations, reduction, and flow
   calculations are cross-frontend domain behavior.
4. **Use the existing agent registry for liveness.** A bead should reference an agent run/lease token; it should not
   produce a Git commit for every heartbeat.
5. **Prefer derived states to a custom-status explosion.** “Blocked,” “stale,” “needs evidence,” and “claim lost” can
   be computed.
6. **Add typed events before generic metadata.** A small number of meaningful event kinds is more valuable than a
   free-form field bag no tool understands.
7. **Make every new read usable from CLI, ACE, and mobile through one wire contract.**
8. **Migrate incrementally.** The current store has useful history and should remain readable throughout any event
   schema or layout transition.

## Detailed recommendations

### 1. Make notes a first-class, append-only journal

**Why this ranks first:** It fixes an observed integrity problem, aligns the implementation with the event-sourced
design, improves agent handoffs immediately, and provides the substrate for structured completion evidence.

Add journal operations such as:

```text
journal_entry_added
journal_entry_corrected
journal_entry_redacted
```

An added entry should carry:

- a content-derived `entry_id`;
- bead ID;
- author and timestamp;
- entry kind: `progress`, `handoff`, `decision`, `blocker`, `verification`, or `system`;
- body;
- artifact/bead/agent references;
- originating agent run ID when available; and
- optional superseded entry ID for corrections.

Reduction should build the human-readable notes projection from the set of journal events in deterministic order.
Concurrent additions from two clones then survive as two entries. Corrections and redactions should add new events;
they should not rewrite old events.

CLI shape:

```text
sase bead note <id> "..." --kind handoff
sase bead note <id> "..." --kind verification --ref artifact:...
sase bead notes <id> --kind blocker --since 7d --format json
```

Keep `notes` in the compatibility projection, but make it derived. Deprecate `update --notes` or redefine it as a
legacy summary field that cannot erase the journal. The lost-note restoration tool can migrate recoverable prior
revisions into provenance-tagged journal entries after one explicit confirmation.

**Success criteria**

- Two clones append different notes from the same base, merge, and retain both exactly once.
- No new post-migration lost-note finding can be produced by ordinary note commands.
- Appending a short note does not store the entire prior notes corpus in the new event.
- `show`, pages, ACE, mobile, and JSON all consume the same reduced journal model.

**Effort/risk:** Medium to high. It crosses the Rust wire/event/reducer/mutation/read boundary and projection formats,
but it is conceptually narrow. Coordinate its reference field with the artifact-reference work already in flight.

### 2. Add atomic ready-work claiming and run-bound ownership

**Why this ranks second:** Work selection is only useful if exactly one worker wins. A check-then-act loop is the wrong
primitive for autonomous agents.

Add:

```text
sase bead ready --claim [filters...] --format json
sase bead claim <id> --if-status open
sase bead reclaim <id> --if-owner-dead
```

A claim should contain:

- assignee;
- stable agent global name;
- exact agent run/artifact identity;
- claim token or generation;
- expected prior status/version; and
- acquisition timestamp.

The local mutation must be compare-and-set. For a sidecar-backed store, the agent must not begin work until the claim is
published and verified against the remote head. If publication loses a race, it should integrate, observe the winner,
and either claim the next matching bead or return a distinct machine-readable conflict result. Offline mode may expose
an explicit weaker local-only claim, but it should not pretend to be globally exclusive.

After promotion, liveness should be derived from SASE's agent metadata. Do not append heartbeat events to the bead
store. Instead:

- retain the claim/run token on the bead;
- read the agent registry's existing heartbeat/lifecycle data;
- expose `sase bead stale --status in_progress`;
- let `doctor` report owner-dead work;
- allow a guarded `reclaim --if-owner-dead`; and
- let epic reruns use the same operation rather than bespoke reassignment rules.

Temporal's activity model is useful precedent here: a heartbeat indicates both progress and worker liveness, and a
timeout allows timely recovery after a crash
([Temporal failure detection](https://docs.temporal.io/encyclopedia/detecting-activity-failures)). SASE already has
the liveness source; it only needs to bind bead ownership to the exact run that source describes.

**Success criteria**

- Two agents claiming the same ready bead from separate clones produce one winner and one loser before model work
  begins.
- Repeating a claim held by the same run is idempotent.
- A stale previous run cannot close or update work owned by a newer claim generation.
- Dead promoted owners are visible and recoverable without blind reopening.

**Effort/risk:** Medium to high. True cross-host exclusion requires a publication/verification barrier, not only a Rust
mutex or local compare-and-set.

### 3. Shard or objectize canonical events to remove the per-epic Git hotspot

**Why this ranks third:** The current resolver is strong, but parallel epic execution should not make semantic conflict
resolution the normal synchronization path.

The preferred long-term shape is immutable event objects:

```text
events/
  objects/
    ab/
      <content-derived-event-id>.json
  snapshots/
    <issue-or-lineage>.json
```

Each mutation adds uniquely named immutable files. Independent additions merge as a set at the Git tree level. A
deterministic snapshot/index accelerates reads but is derived and repairable. Atomic multi-bead operations still land
as one Git commit containing multiple objects.

A lower-cost transitional option is one stream per issue rather than one stream per root lineage. That removes most
phase-to-phase collisions but still conflicts when two agents legitimately append to the same bead. It is therefore a
useful migration step, not the ideal endpoint.

The implementation should also reconsider which generated files belong on the hot writer path:

- `issues.jsonl` can remain tracked for compatibility if the resolver always regenerates it.
- `manifest.json` should be derived from actual objects/streams rather than an independently contended counter.
- public pages could be generated by one publisher after canonical state lands, instead of every worker updating page
  projections in its own commit.

Use a versioned loader that can read v1 root streams and v2 objects simultaneously. New writes can move to v2 while a
background/explicit compactor snapshots closed v1 lineages. Avoid a flag-day rewrite.

Upstream Beads moved to Dolt partly to gain row/cell-level merging. SASE should take the useful lesson—independent
records should merge independently—without taking the required database/server architecture.

**Success criteria**

- A synthetic 20-phase epic can record progress and close phases from 20 clones without a canonical content conflict.
- Independent event additions never need ordinal renumbering.
- Generated projections can be deleted and rebuilt from canonical objects.
- Read latency stays sub-second at current store size.
- Git object/file-count growth is measured and bounded by deterministic snapshots or packing.

**Effort/risk:** High. This deserves an architecture spike and fixture migration before implementation. It should be
designed alongside recommendation 1 so journal entry identity is not reinvented twice.

### 4. Add a bead query corpus, saved views, and a real ready-work policy

**Why this ranks fourth:** The store has enough records and fields to support useful selection now, while the current
literal search and optionless `ready` force users and agents into `jq` or arbitrary first-row selection.

Generalize the existing Rust query infrastructure so different entity corpora can declare their fields and matchers.
A bead corpus should initially expose existing facts:

- `id`, `title`, `description`, journal text;
- `status`, `type`, `tier`, `resolution`;
- `owner`, `assignee`, exact run;
- `parent`, `ancestor`, `descendant`;
- `created`, `updated`, `started`, `closed`;
- `size`, `model`;
- `ready`, `blocked`, `blocks_count`, `depends_on`;
- `has:design`, `has:refs`, `has:verification`;
- `changespec`, `bug`; and
- `agent_alive`.

Example:

```text
sase bead query 'status:in_progress updated<2h !agent_alive'
sase bead query 'type:phase size:small closed>7d'
sase bead query 'resolution:superseded !has:replacement'
```

Then make `ready` a query-backed view:

```text
sase bead ready --type phase --parent sase-xy --sort criticality --explain
sase bead ready --query 'size:small !has:changespec' --claim --format json
```

Useful default sort policies are:

1. explicit dependency criticality / number of downstream beads unblocked;
2. age;
3. size or estimated cost; and
4. stable ID as the final tie-breaker.

Taskwarrior's urgency model demonstrates that readiness ordering can combine due date, blocking impact, age, active
state, and user preference without turning any one field into truth
([Taskwarrior urgency](https://taskwarrior.org/docs/urgency/)). SASE should start simpler and make `--explain` show
every factor.

Do **not** start by adding a large label taxonomy or custom statuses. Add a priority/due/defer field only when a live
saved view needs it. The immediate value comes from querying facts SASE already owns.

Saved bead views should reuse the existing SASE saved-query experience and be available in CLI, ACE Plans, and mobile.

**Success criteria**

- Common “stale,” “ready phase,” “blocked critical path,” and “missing evidence” views require no `jq`.
- The same canonical query produces the same result across CLI, ACE, and mobile.
- `ready --explain` tells an agent why an item was selected.
- Query parsing/evaluation remains a Rust-core capability with bounded corpus reuse.

**Effort/risk:** Medium. Reusing the current query engine is attractive, but its parser currently hard-codes
ChangeSpec-oriented property keys and lacks typed comparison semantics.

### 5. Record typed completion certificates

**Why this ranks fifth:** Close status now has honest structural guards, but “done” still lacks a machine-checkable
statement of what was verified.

Add a `completion_recorded` event or typed journal entry containing:

- summary;
- verification command(s);
- exit status and timestamp;
- repository and commit/ChangeSpec references;
- artifact references;
- agent run;
- acceptance criteria satisfied;
- known residual risks; and
- an explicit waiver with reason when a check could not run.

An approved epic plan can optionally declare phase acceptance criteria. `sase bead work` should compile those criteria
into the phase bead so the worker and land agent see the same contract. A normal `resolution=done` close for an
epic-launched phase should require a completion certificate or an explicit policy waiver. Canceled and superseded
closures should require a reason; superseded should eventually require a replacement relation.

The land agent should receive a compact evidence matrix:

| Phase | Resolution | Verification | Commits | Artifacts | Waivers |
| ----- | ---------- | ------------ | ------- | --------- | ------- |

This is not a new review workflow or status. It is structured evidence attached to the close transition.

**Success criteria**

- Every newly completed epic phase is either evidenced or explicitly waived.
- Land agents no longer parse arbitrary note prose to decide whether verification happened.
- Verification commands and results survive rebases and note updates.
- Pages and JSON show a concise certificate while history preserves the complete record.

**Effort/risk:** Medium after recommendation 1 and the current artifact-reference work. Enforcing it should be phased:
record first, warn second, require only for configured epic flows after adoption is measured.

### 6. Turn event history into flow, graph, and routing analytics

**Why this ranks sixth:** SASE now produces enough volume to learn from its own execution system, but `stats` still
reports only counts.

Add:

```text
sase bead stats --flow --since 30d --format json
sase bead stats --epic sase-xy --critical-path
sase bead stats --group-by size --measure cycle-time
```

Derive:

- queue time: create to first work start;
- active time: in-progress intervals;
- blocked time and blocker attribution;
- claim wait and runner-capacity wait;
- time to first useful journal entry;
- reopen/retry/reclaim/delegation rate;
- forced/canceled/superseded closure rate;
- throughput and WIP age;
- planned waves versus realized concurrency;
- critical-path delay and fan-in idle time;
- phase duration and completion-evidence rate by size;
- routing outcomes by model role/provider; and
- sync operation latency/conflict/recovery counts.

The live sample already shows why calibration matters. Among currently measurable sized closed phases:

| Size     | Count | Median create-to-close |       p90 |
| -------- | ----: | ---------------------: | --------: |
| `small`  |   141 |                3,906 s |  16,719 s |
| `medium` |   189 |                3,320 s |   9,856 s |
| `large`  |    10 |                7,891 s | 101,260 s |

This does **not** prove the size model is wrong: cohorts differ, create-to-close is not active time, and the large
sample is small. It does prove that the current `stats` output cannot answer whether the size ladder predicts effort
or whether model routing improves outcomes.

Linear's Insights product explicitly uses cycle time and estimate accuracy as issue-tracker questions
([Linear Insights](https://linear.app/docs/insights)); GitHub offers current and historical project charts for trends
and bottlenecks
([GitHub project insights](https://docs.github.com/en/issues/planning-and-tracking-with-projects/viewing-insights-from-your-project/about-insights-for-projects)).
SASE can do better for agent work because it also knows model, run, wait, commit, and verification provenance.

Expose summary views in the existing Statistics experience and optional operational metrics through SASE's telemetry.
If OpenTelemetry is used, keep metric names and attributes consistent and bounded; the upstream Beads implementation
already instruments storage operation counts, latency, errors, and lock waits
([upstream observability](https://beads.gascity.com/reference/observability)).

**Success criteria**

- A weekly retrospective is answerable without reading raw event JSONL.
- Size/model routing changes can be evaluated against before/after cohorts.
- A delayed epic identifies its actual critical path and time spent waiting.
- Analytics distinguish queue time from execution time.

**Effort/risk:** Medium. Most data already exists, but started/stopped intervals and retry identities must be normalized
before metrics are trustworthy.

### 7. Add a small typed relation graph and duplicate/supersession targets

**Why this ranks seventh:** Blocking dependencies and hierarchy answer execution order. They do not answer why two
beads are related, which record is canonical, what replaced a superseded bead, or where work was discovered.

Use one relation event/table with a deliberately small enum:

- `related_to`;
- `duplicate_of`;
- `supersedes`;
- `discovered_from`; and
- `validates`.

Only blocking dependencies affect readiness. Relation direction and cardinality should be defined in the Rust core.
`related_to` is symmetric; `duplicate_of` and `supersedes` are directed and should resolve to one canonical target.
Closing with `resolution=superseded` should require or strongly warn on a missing replacement.

Upstream Beads distinguishes blocking edges from replies, related items, duplicates, and supersession chains
([upstream graph links](https://beads.gascity.com/core-concepts/graph-links)). Linear similarly treats blocked,
blocking, related, and duplicate as distinct semantics
([Linear issue relations](https://linear.app/docs/issue-relations)).

SASE should not import conversation threading or generic graph types. The five relations above directly support
capture provenance, archive trust, evidence, and deduplication.

Start duplicate discovery mechanically using normalized titles/descriptions and shared refs. An optional semantic
review can propose pairs, but no LLM should automatically close one.

**Success criteria**

- Every superseded closure can navigate to its replacement.
- Captured follow-up work retains its source without blocking either bead.
- Duplicate marking is atomic, reversible through history, and preserves the canonical bead.
- `doctor` catches dangling or cyclic relation forms where they are invalid.

**Effort/risk:** Medium. A generic relation wire is more migration-friendly than adding a field for each relation.

### 8. Bind bead graphs to plan revisions and add reconciliation

**Why this ranks eighth:** Logical plan references and doctor checks improved path durability, but the relationship is
still mostly a pointer. SASE cannot explain whether the current bead graph still represents the plan revision that
created it.

Store on an epic and each compiled phase:

- canonical logical plan reference;
- plan content digest or durable revision ID;
- phase slug from frontmatter;
- authored dependency set;
- authored size/model;
- compiler/schema version; and
- creation transaction ID.

Add:

```text
sase bead reconcile <epic-id>
sase bead reconcile <epic-id> --format json
```

The command should compare the current plan against the bead graph and classify drift:

- path-only relocation;
- prose-only change;
- phase added/removed;
- dependency change;
- size/model change;
- bead link mismatch; and
- plan status inconsistent with bead resolution.

Automatic application should be conservative. Before execution, safe graph changes can be previewed and applied
atomically. After execution starts, topology changes should normally create a follow-up/child plan rather than rewrite
history.

The current doctor output still reports 28 design-reference/ownership warnings. Reconciliation would move the system
from repairing paths to understanding provenance and semantic drift.

**Success criteria**

- Every new epic can name the exact plan revision it compiled.
- Plan relocation does not look like semantic drift.
- A phase dependency or size change is visible before launch/resume.
- Re-running `work` is idempotent against the recorded plan revision.

**Effort/risk:** Medium. The plan compiler already has most authored metadata at launch time; the main work is defining
stable provenance and update policy.

### 9. Add qualified cross-project bead references, then cross-project dependencies

**Why this ranks ninth:** SASE manages multiple projects and linked repositories, but bead resolution and waits are
currently project-scoped. Cross-project work is therefore tracked in the wrong project's store or coordinated through
prose.

Do this in two stages:

1. **Read/reference stage:** define a globally unambiguous spelling such as `<project>#<bead-id>`, support it in
   `show`, queries, artifact refs, pages, ACE, and mobile, and add `--all-projects` aggregate reads.
2. **Dependency stage:** allow a local bead to depend on a qualified external bead, fail closed when the external store
   is missing/unreadable, and detect cycles across the resolved multi-store graph.

Do not add a federation server. Resolution can use SASE's enabled-project inventory and existing repository
materialization policy. Cache read snapshots and keep mutations owned by the bead's home project.

GitHub now supports issue hierarchies and dependencies, including selecting sub-issues from other repositories
([GitHub sub-issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues)).
The transferable lesson is the qualified reference and aggregate view, not GitHub's service architecture.

**Success criteria**

- A user can navigate and query a foreign-project bead without moving it into the local store.
- An external dependency remains visibly blocked when its store cannot be resolved.
- Cross-project cycles are diagnosed before launch.
- Project-local commands remain fast and unchanged by default.

**Effort/risk:** High and lower urgency than the prior items. Cross-store freshness and failure semantics must be
specified before mutations are added.

## What not to build

### No Dolt or required daemon

The current event source, Rust reducer, and Git sidecar are good strategic choices. The right response to merge
pressure is to make independent events independently mergeable, not to replace the source of truth with a server.

### No second workflow engine inside beads

Do not import molecules, formulas, wisps, gates, agent mail, or custom workflow states. SASE already has plans,
xprompts, agent families/clans, waits, gates, notifications, tasks, and ChangeSpecs. Beads should record and schedule
work, not duplicate those control planes.

### No broad label/custom-field system yet

First expose the fields and graph predicates already present. Add a new typed field only when a concrete saved query or
scheduling policy needs it. Free-form metadata without product semantics would make queries and migrations harder.

### No aggressive compaction yet

The sidecar is 31 MB including Git and generated pages, with a 7 MiB pack. Add health thresholds and measure read/token
cost, but spend current effort on lossless events and reduced contention. Immutable event objects will eventually need
packing/snapshots; design that with the storage v2 work rather than shipping an unrelated semantic “memory decay”
feature.

### No automatic semantic deduplication or autonomous priority rewriting

Agents may propose duplicates, relations, priorities, or size corrections. Canonicalization and scheduling policy are
high-impact decisions and should stay explainable and reviewable.

## Suggested implementation sequence

### Tranche A: trust and ownership

1. Design journal-entry and claim/run-token wire records together.
2. Ship first-class journal events and migrate new `note` writes.
3. Add local compare-and-set update guards and machine-readable conflict exit codes.
4. Add report-only stale/dead-owner views.
5. Add remote-verified `ready --claim`.

### Tranche B: convergence and selection

1. Prototype immutable event objects versus per-issue streams on a cloned production fixture.
2. Measure Git file/object growth, reduction time, merge behavior, and generated projection cost.
3. Land a dual-format reader and v2 writer incrementally.
4. Generalize the Rust query corpus and add bead queries/saved views.
5. Make filtered/explained `ready` use the same query path.

### Tranche C: evidence and learning

1. Record completion certificates without requiring them.
2. Add evidence coverage warnings and the land-agent evidence matrix.
3. Derive flow intervals and ship JSON analytics.
4. Calibrate phase sizes and model routing from observed cohorts.
5. Enforce evidence only for configured epic flows after adoption is healthy.

### Tranche D: graph reach

1. Add the small typed relation set.
2. Add plan revision provenance and reconciliation.
3. Add read-only qualified cross-project references.
4. Add cross-project dependencies only after freshness/failure semantics are proven.

## Low-cost improvements worth doing alongside the larger work

- Add `--format json` to `ready`, `blocked`, and `stats`.
- Add `--type`, `--tier`, `--parent`, and `--assignee` to `ready`.
- Add `--explain` to `ready` and `blocked`.
- Add `--if-status` and `--if-assignee` to `update` as an immediate local compare-and-set guard.
- Add `sase bead stale --days N` as report-only functionality.
- Downgrade or clarify `doctor`'s `beads.db missing` warning when the cache is optional and Rust reads do not require
  it.
- Expose a stable exit-code contract for validation failure, claim conflict, missing store, and sync failure.
- Add `stats --format json --since ...` before the full flow dashboard.

## Sources

Internal:

- Current SASE documentation: `docs/beads.md`, `docs/sdd.md`, `docs/ace.md`, and `docs/query_language.md`.
- Current Python implementation under `src/sase/bead/` and tests under `tests/test_bead/`.
- Current Rust implementation under `crates/sase_core/src/bead/` and `crates/sase_core/src/query/`.
- Live `sase--beads` event streams, projection, Git history, `sase bead stats`, `doctor`, `history --lost-notes`,
  list/search/show JSON, and command help.
- July plans covering fast reads/mutations, merge convergence, commit consolidation, history/truthful close,
  dependency tooling, claim hardening, pages, sidecar storage, and artifact references.
- The two earlier research packages linked in the scope section.

External primary documentation:

- [Upstream Beads: ready work and atomic claim](https://beads.gascity.com/cli-reference/ready)
- [Upstream Beads: query language](https://beads.gascity.com/cli-reference/query)
- [Upstream Beads: graph links](https://beads.gascity.com/core-concepts/graph-links)
- [Upstream Beads: OpenTelemetry observability](https://beads.gascity.com/reference/observability)
- [GitHub: typed issue fields in Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields/about-issue-fields)
- [GitHub: current and historical Project insights](https://docs.github.com/en/issues/planning-and-tracking-with-projects/viewing-insights-from-your-project/about-insights-for-projects)
- [GitHub: sub-issues and cross-repository selection](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues)
- [Linear: advanced filters and custom views](https://linear.app/docs/filters)
- [Linear: issue relations](https://linear.app/docs/issue-relations)
- [Linear: issue analytics](https://linear.app/docs/insights)
- [Taskwarrior: configurable urgency scoring](https://taskwarrior.org/docs/urgency/)
- [Temporal: activity heartbeats, timeouts, and crash detection](https://docs.temporal.io/encyclopedia/detecting-activity-failures)

## Final ranked recommended improvements

1. **Replace mutable notes snapshots with first-class append-only journal events** so concurrent progress, handoff,
   decision, blocker, and verification entries merge without loss.
2. **Add remote-verified atomic `ready --claim`, compare-and-set updates, and run-bound reclaim semantics** so exactly
   one agent owns work and dead owners are safely recoverable.
3. **Move canonical storage away from one root JSONL stream per epic**, preferably to immutable content-addressed
   event objects with derived snapshots, eliminating the normal parallel-write hotspot.
4. **Build a reusable bead query corpus, saved views, filtered/explained ready queues, and deterministic scheduling
   policies** over facts SASE already stores.
5. **Record typed completion certificates tied to plan acceptance criteria, commits, commands, artifacts, and
   waivers**, then phase in evidence requirements for executable epics.
6. **Derive flow, critical-path, size, model-routing, retry, and synchronization analytics from event history** and
   expose them through JSON, CLI, and the existing Statistics experience.
7. **Add a deliberately small typed relation graph** for `related_to`, `duplicate_of`, `supersedes`,
   `discovered_from`, and `validates`, with replacement targets for superseded work.
8. **Bind compiled bead graphs to exact plan revisions and add a reconciliation command** for topology, dependency,
   size/model, link, and lifecycle drift.
9. **Add qualified cross-project bead references and aggregate reads first, then carefully add cross-project
   dependencies** without introducing a federation server.
