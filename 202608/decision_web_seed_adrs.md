---
create_time: 2026-08-24
updated_time: 2026-08-24
status: research
tags: [architecture, adr, decisions, memory-webs, artifacts, sase-core]
---

# Which Decisions Should Seed SASE's Decision Web?

**Research question:** Which architectural decisions would be most useful as the first
strands in the `decisions` memory web proposed by
[`glossary_to_memory_webs.md`](glossary_to_memory_webs/glossary_to_memory_webs.md)?

**Scope:** Retrospective decision recovery and authoring priority, not implementation of
the memory-web substrate. Repository evidence was checked at `sase@4041c17e4` and the
research sidecar at `bf8f505` on 2026-08-24.

---

## Bottom line

Seed the web with **ten accepted decisions**, then add three follow-ons. The first ten
are enough to prove the proposed web with a real, heterogeneous corpus: context
management, backend boundaries, workspace isolation, durable state, change tracking,
storage topology, completion safety, artifact identity, extensibility, and verification.

The highest-value ADR is not the broadest architectural principle. It is the decision
whose rationale is easiest to lose and most likely to be accidentally reversed:
**SASE uses explicit, audited memory retrieval instead of inferred runtime recall.** The
repository first built keyword-selected dynamic memory, then removed it while retaining
episodes, then removed episodes too. That history is recoverable from commits today but
is almost absent from current documentation. It should be written as a small
supersession chain, making it an ideal first demonstration of why ADRs exist.

The Rust-core boundary and numbered-workspace isolation come next. Both affect a large
part of the system, carry expensive alternatives, and are already enforced as project
instructions. Their current documentation says *what* the boundary is; an ADR would
preserve *why* it exists, which tradeoffs were accepted, and what evidence should cause
it to be revisited.

Three operating rules follow from the research:

1. **Rank is authoring priority, not ADR identity.** Allocate monotonically increasing
   decision IDs in authoring order. Keep the historical decision date in metadata; do
   not pretend a retrospective record was written on that date.
2. **Backfill decisions, not documentation topics.** A glossary term, command reference,
   wire version, UI layout, or migration recipe is not an ADR unless it captures a
   choice among meaningful alternatives with durable consequences.
3. **Use immutable accepted records.** If the project changes course, add a new record
   and mark the old one superseded. Do not rewrite history to make the old choice look
   obvious in retrospect.

## 1. What makes a decision ADR-worthy here

Michael Nygard's original criterion is a useful filter: record decisions that affect
structure, non-functional characteristics, dependencies, interfaces, or construction
techniques. An ADR should describe one response to competing forces, not summarize a
subsystem. AWS's current guidance adds two important operational properties: the
decision log should work as a skimmable overview and as a detailed reference, and an
accepted record should be immutable and superseded by a new record when the decision
changes.

Those properties align unusually well with the proposed memory web:

- The `decisions.md` web note is the skimmable log.
- One strand is one decision and can be read on demand.
- Stable slugs keep identity independent of mutable titles.
- `supersedes` / `superseded-by` is the one typed relationship ADRs inherently need.
- Reference rendering keeps decision bodies out of every agent's startup context.

I ranked candidates using four qualitative tests:

| Test | Question |
| --- | --- |
| Architectural reach | Would reversing this alter several components, public contracts, or operational guarantees? |
| Rationale-loss risk | Is the reasoning missing from current docs, scattered across history, or contradicted by plausible alternatives? |
| Web value | Does the record connect several glossary terms and provide context for later, narrower decisions? |
| Decision maturity | Is there enough landed behavior and evidence to state an accepted decision without inventing rationale? |

The ranking is deliberately qualitative. Source-file counts are a useful signal of
reach, but they would create false precision: terms such as `Patch`, `plugin`, and
`workspace` appear in generated files and compatibility layers as well as in owning
code.

## 2. The current documentation gap

The primary repository has a strong architecture guide and detailed subsystem
references, but no ADR corpus or ADR-shaped Markdown by name. The guides mostly describe
the current state:

- `docs/architecture.md` says that durable state is outside chat transcripts, defines
  the project/repo/workspace taxonomy, and states the Python/Rust ownership boundary.
- `docs/workspace.md` documents numbered workspaces, claims, registries, and the managed
  XDG-state default.
- `docs/sdd_storage.md` documents provider-owned, role-based sidecars and transactional
  materialization.
- `docs/commit_workflows.md` documents provider-neutral commit orchestration, Patch and
  Stitch tracking, conflict resume, and the host finalizer.
- `docs/artifact_references.md` and `docs/artifact_links.md` document typed identities,
  provider resolution, audited reads, and the relation registry.
- `docs/plugins.md` documents many extension groups and the distinction between
  discovery, availability, and activation.

These are valuable references, but they are poor substitutes for a decision record.
They are expected to track current behavior, so obsolete alternatives and the reasons
for rejecting them disappear during normal maintenance. The memory history proves the
point: current docs correctly omit dynamic memory and episodes, but that makes it easy
for a future contributor to rediscover the attractive idea without seeing the failure
history.

The git history and existing research contain enough evidence to recover a high-quality
initial corpus. The most useful anchors are:

| Decision area | Evidence |
| --- | --- |
| Automatic versus explicit memory | `c421c12c4` added keyword-selected dynamic memory; `e8c2f14bb` removed it; `37973b8b3` removed episodes |
| Rust/Python boundary | `b83199d6e` documented the boundary; `docs/architecture.md`; `docs/rust_backend.md` |
| Managed workspaces | `2147ba8c7` documented stable numeric workspace identity; `22f8924c9` made XDG state the default |
| Durable state outside chats | `docs/architecture.md`, especially the state model and cross-frontend motivation |
| Patch and Stitch model | `2634fb475` adopted Patch terminology; `b4a868893` made `stitch create` the only tracked VCS path |
| Provider-owned sidecars | `747d9be32` made provider storage authoritative; `3cf8ea2bf` adopted sidecars; `107904b6b` generalized document roles |
| Host-owned finalization | `2f9c4ae29` made pluggable finalizers the sole completion path |
| Typed artifacts | `f53e43ab1` added the artifact-provider registry; `4687d3795` published the closed relation registry |
| Required plugins | `1e59c50e7` added project declarations and fail-closed enforcement |
| Two-speed verification | `515ef3a48` split `just check` from `just check-full` |
| Supervisor-owned procs | `8b4635ad1` routed monitors through the shared proc service |

## 3. Recommended record shape

Use the ordinary web-strand frontmatter proposed by the source research and keep ADR
fields under opaque metadata until the generic web substrate has a reason to interpret
them:

```yaml
keyword: Prefer explicit audited memory retrieval
aliases: [explicit memory, audited memory]
metadata:
  status: accepted
  decision_date: 2026-06-15
  recorded_date: 2026-08-24
  evidence:
    - commit:e8c2f14bb
    - commit:37973b8b3
```

The body should remain short and use the same stable sections for every record:

1. **Context** — the forces and constraints, including the prior state.
2. **Decision** — one active-voice statement of what SASE will do.
3. **Alternatives considered** — only credible alternatives that were available.
4. **Consequences** — positive, negative, and neutral consequences.
5. **Revisit when** — observable conditions that should trigger a new ADR.
6. **Evidence** — commits, plans/research, and current enforcement points.

For retrospective records, separate `decision_date` from `recorded_date`. Use
`status: accepted-retrospective` only if the web wants to distinguish provenance; do not
use it as a different lifecycle state. The architectural status is still Accepted.

The initial implementation should follow the source report's restraint and use prose
references between ADRs. Once decision strands are artifacts, record actual replacement
with the existing `supersedes` relation. Do not add a parallel `references:` syntax or
infer closure from title mentions.

## 4. Candidate analysis

### 4.1 Prefer explicit, audited memory retrieval over automatic runtime recall

**Recommended status:** Accepted, represented by two records: an older
`automatic-runtime-memory-recall` record marked Superseded, and the current
`explicit-audited-memory-retrieval` record.

This has the highest rationale-loss risk. SASE implemented keyword-triggered prompt
rewriting in April (`c421c12c4`), removed that runtime in May while retaining a smaller
episode-recall path (`e8c2f14bb`), and removed episodes in June (`37973b8b3`). Current
memory instead uses bounded always-loaded notes, explicit inclusion, audited reads, and
human-reviewed write proposals.

The ADR should state the decision at the level of policy: SASE will not infer durable
context and silently inject it into an agent turn. Context with material provenance or
cost is selected explicitly and, where appropriate, audited. Credible alternatives are
keyword matching, embedding/vector retrieval, episode recall, and provider-native
memory. Consequences include more deliberate reads and occasional missed context in
exchange for inspectability, bounded startup context, fewer false-positive injections,
and less runtime-specific prompt mutation.

**Web neighbors:** Memory Web, Memory Strand, Xprompt, Artifact, audited read, and the
future glossary-web migration.

### 4.2 Put deterministic cross-frontend behavior in Rust; keep orchestration in Python

**Recommended status:** Accepted, decision date 2026-05-01 or the earliest verified
boundary adoption date.

The current rule is already precise: reusable deterministic backend/domain behavior
belongs in `sase-core` behind stable wire records and a Python facade; Python owns
plugin dispatch, process and filesystem side effects, TUI presentation, and workflow
orchestration. The ADR should preserve the forces behind the split: cross-frontend
consistency, performance on large stores, stable contracts, incremental migration, PyO3
deployment cost, version skew, and the need to keep app-context side effects out of the
core.

The rejected extremes are “keep everything in Python” and “move the application into
Rust.” The accepted boundary is more useful than a language-choice ADR because it tells
contributors where new behavior belongs. Its revisit condition should be boundary
friction measured in duplicated adapters or wire churn, not a general preference for
one language.

**Web neighbors:** Rust Core Backend, Patch, Bead, Artifact, Project, Query, wire schema,
and every frontend.

### 4.3 Isolate agents in exclusively claimed numbered workspace clones

**Recommended status:** Accepted.

This decision should combine the stable architectural choice, not every path-policy
detail: one agent claims one numbered clone; the primary checkout is workspace `#0`;
workspace identity is managed by a per-project store; execution clones default under an
XDG state root rather than polluting the source tree. The core forces are parallel-agent
isolation, protection from cross-agent working-tree interference, deterministic cleanup,
discoverability, backup/container tradeoffs, and allocation races.

Alternatives include shared working trees with branches, Git worktrees, adjacent clones
derived by string convention, and ad hoc caller-selected directories. The ADR should
explain why a workspace is not a repo and why linked/sidecar checkouts inside a workspace
do not become additional workspaces. Exact reserved ranges and migration commands are
reference-doc consequences, not the decision itself.

**Web neighbors:** Sase Workspace, Sase Repo, Sase Project, Agent Shell, workspace claim,
sidecars, and finalization.

### 4.4 Persist orchestration state outside chat transcripts and UI processes

**Recommended status:** Accepted.

This is SASE's foundational state-model decision: chats and TUIs are views over durable,
inspectable records rather than authorities. ProjectSpecs, agents, beads, plans,
research, prompts, notifications, workspace claims, finalizer evidence, and audit logs
outlive a provider invocation. That enables retry, resume, review, handoff, multiple
frontends, and failure recovery.

The credible alternative is a chat/session-centered orchestrator in which the provider
conversation and live process own progress. The cost of the accepted choice is a large
set of schemas, stores, indexes, reconciliation paths, and compatibility obligations.
The benefit is provider independence and recoverability. Keep this ADR narrow: it
decides where authority lives, not which store owns every record.

**Web neighbors:** Artifact, Agent, Patch, Bead, ProjectSpec, finalizer, ACE, AXE, and
mobile/editor integrations.

### 4.5 Model tracked change as a Patch containing ordered Stitches

**Recommended status:** Accepted.

The important decision is not the Patch rename by itself. It is that SASE has a stable,
PR-sized review record whose identity survives commit rewrites, and an ordered Stitch
record for each tracked change operation. All tracked VCS mutation flows through the
provider-neutral `sase stitch create` workflow, which owns hooks, attribution,
Patch/Stitch bookkeeping, conflict checkpoints, and resume behavior.

The alternatives are raw commits as the only identity, provider-native PRs as the
source of truth, a specification-only ChangeSpec, and separate commit engines per VCS or
agent runtime. The earlier naming research recommended `rivet`, while the landed product
chose Patch/Stitch; that disagreement makes the rationale particularly worth recording.
Compatibility aliases belong in consequences, not in the decision statement.

**Web neighbors:** Patch, Stitch, ProjectSpec, VCS provider, finalizer, bead autoclose,
and artifact provenance.

### 4.6 Let workspace providers own SDD placement in role-based sidecar repositories

**Recommended status:** Accepted.

This ADR should record two coupled choices that form one storage authority decision:
workspace providers determine the storage policy, and durable corpora may materialize
as role-based sidecars (`plans`, `research`, `beads`, hidden `agents`, and generic
document roles). A positive store record is authoritative; clone existence is not.
Materialization is transactional and record-last.

Alternatives are putting every artifact in the primary code repo, keeping one monolithic
companion repo, allowing user config to select arbitrary layouts, or treating whichever
clone happens to exist as truth. Consequences include extra repositories and publication
coordination, but lower contention, independent retention, portable artifact links, and
clear ownership. Transport requirements and schema-2/3 migration steps belong in
reference docs.

**Web neighbors:** Sase Repo, workspace provider, Artifact Reference, Project, plans,
research, beads, agents, and repository publication.

### 4.7 Use a host-owned sealed finalizer protocol as the sole completion path

**Recommended status:** Accepted, with an explicit note that the decision is recent and
should be revisited after operational soak.

The host resolves a finalizer plan before the model turn, publishes immutable context,
accepts a turn-bound declaration, executes deterministic providers, and independently
verifies postconditions. Runtime-native stop hooks and prompt-controlled commands do not
own completion. Plugins may contribute finalizer providers, but installation does not
activate them and the host retains repository inventory, ordering, retries, evidence,
and failure authority.

The alternatives are provider-specific hooks, a hard-coded commit finalizer, arbitrary
prompt-selected executors, and trusting an executor's success claim. The consequences
are protocol and evidence complexity in exchange for uniform agent runtimes, bounded
recovery, discarded-work detection, and extensibility without surrendering the safety
boundary.

**Web neighbors:** Required Plugin, Stitch, Agent Shell, Artifact, workspace claim,
provider, and publication verification.

### 4.8 Address durable records with typed artifact references and provider resolution

**Recommended status:** Accepted.

Every durable record has a canonical `<kind>:<argument>` identity. Builtin and
plugin-provided reference kinds resolve, expand into prompts, publish as portable prose,
and record consumption. This separates artifact identity from a local path, a hosted
URL, a particular sidecar layout, or a UI row.

Alternatives include raw paths, URLs embedded in prompts, one xprompt per document
kind, and hard-coded research/plan branches. Consequences include a registry and
provider contract, canonicalization rules, and collision constraints; benefits include
portable prompts, lazy sidecar materialization, one audit model, and future-compatible
memory-strand addressing.

**Web neighbors:** Artifact, Artifact Reference, Required Plugin, Sase Repo, research,
plan, bead, agent, Patch, Stitch, and indexed file.

### 4.9 Extend capabilities through typed plugins with declared availability

**Recommended status:** Accepted.

SASE uses typed extension boundaries for LLM, VCS, workspace, config, xprompt, artifact,
file-hook, task-type, and finalizer capabilities. Project config names providers with a
qualified `distribution@provider` form. A project must declare required plugin
distributions and validation fails closed when a selected provider is absent or its
version is unsatisfied. Installation makes a provider available; it does not necessarily
activate it.

Alternatives are optional imports, runtime-specific conditionals, a single untyped hook
bag, silent capability degradation, and environment-dependent catalogs. Consequences
include install and version-management friction, but also reproducible project behavior,
uniform provider boundaries, and actionable doctor diagnostics. Committed snapshots for
plugin-derived catalogs are a consequence of deterministic generation, not a separate
top-level ADR unless that pattern expands further.

**Web neighbors:** Required Plugin, provider, task type, finalizer, Artifact Reference,
VCS, workspace, and Xprompt.

### 4.10 Use two-speed verification at agent scale

**Recommended status:** Accepted.

Agent work runs every whole-repo lint gate plus a diff-scoped test selection; landing
and CI run the exhaustive suite. Selection health and an always-run contract set backstop
the heuristic. The decision is a construction technique with architectural consequences
because SASE's ephemeral parallel agents make full-suite verification on every turn an
unsustainable shared-resource policy.

The supporting research measured roughly a 15-fold reduction in host demand for a real
scoped check and rejected splitting the repo or immediately adopting Pants/Bazel as
solutions to the same problem. Consequences include a nonzero false-negative risk and
more selection infrastructure, balanced by shorter feedback and less contention. The
ADR should say when `check-full` is mandatory and what evidence would invalidate the
selector strategy.

**Web neighbors:** Agent, Sase Workspace, Rust Core Backend, CI, suite gate, selection
health, and landing workflow.

### 4.11 Supervise long-running commands outside ACE through one proc service

**Recommended status:** Accepted, next-wave priority.

The architectural decision is not the shell vocabulary. It is that all long-lived OS
commands are detached, supervisor-owned procs with durable output and lifecycle state;
ACE observes them but does not own their execution. A monitor is a family-attached proc
shell projected through the same service, while stand-alone proc shells use the same
substrate without pretending to be LLM agents.

Alternatives include in-TUI background tasks, a separate monitor supervisor, and one
process model per producer. The chosen model survives UI teardown and supports shared
status, stopping, timeouts, and follow-up semantics. Keep identity (`shell_name`) separate
from concurrency exclusion keys; that is an important consequence but too narrow for a
separate ADR.

**Web neighbors:** Proc, Proc Shell, Sase Monitor, Agent Family, Agent Shell, ACE, and
runner slots.

### 4.12 Use a closed typed artifact relation registry; keep scheduling in beads

**Recommended status:** Accepted, next-wave priority.

Artifact links answer why durable records are connected using a closed relation set
with defined inverses and directionality. Committed per-artifact indexes are truth, a
project aggregate is a rebuildable read model, and Markdown tables are projections.
`blocks` and `depends-on` are deliberately excluded because bead dependencies already
own scheduling.

The alternatives are free-text `RELATED:` notes, arbitrary relation slugs, prompt
citations as the only link type, and overloading the graph with readiness semantics.
This deserves its own ADR apart from typed artifact identity because the decisive forces
are vocabulary governance, source-of-truth placement, and separation from scheduling.

**Web neighbors:** Artifact, Artifact Markdown File, Bead, read, cites, related,
supersedes, implements, and derives-from.

### 4.13 Represent keyed memory collections as flat web descriptors with nested strands

**Recommended status:** Proposed only after the project owner accepts the source
research; first native (non-retrospective) ADR.

This is the decision that would create the decision web itself: a flat
`sase/memory/<web>.md` descriptor owns a managed roster, while independently addressable
strands live under `sase/memory/<web>/` and are fetched on demand. The descriptor's body,
not strand bodies, participates in core/reference rendering. This should remain one ADR
about the storage/addressing shape. Tier vocabulary, scope merge, closure, and glossary
migration can be consequences or later ADRs if they become independently reversible
choices.

The alternatives are config-backed keyed stores, `sase/memory/webs/`, one large note,
and a generic artifact database. Do not mark this Accepted merely because the research
recommended it. Acceptance belongs to the implementation decision, and any later change
should supersede this record rather than editing it in place.

**Web neighbors:** Memory Web, Memory Strand, glossary, decisions, Artifact Reference,
core memory, and reference memory.

## 5. What not to seed as ADRs

The following are valuable documentation but weak initial decision strands:

- **Glossary-only taxonomy changes.** “Agent lane” to “Sase Agent,” shell definitions,
  and Patch naming need rationale in their owning ADRs or glossary history, not one ADR
  per noun. The proc-ownership research explicitly found the shell taxonomy itself was
  not architectural.
- **Individual schema and wire versions.** A schema bump implements a decision; it is
  not usually the decision. Record a compatibility-window ADR only if version-window
  policy becomes independently contested.
- **Feature-flag instances.** A beta or sunset flag is temporary rollout state. The
  durable decision is the user-facing behavior being rolled out; flag lifecycle belongs
  in governance memory and its removal bead.
- **UI pane contracts and keymaps.** These are presentation contracts unless a choice
  changes the backend ownership boundary or a published integration interface.
- **One provider's quirks.** Grok, Muse, GitHub, and Telegram details belong in provider
  docs unless they force a project-wide trust, privacy, or execution-boundary decision.
- **Generated catalogs by themselves.** Task types and artifact relations are already
  web-shaped, but their snapshots are consequences of deterministic plugin assembly.
  Promote the snapshot pattern to an ADR only if several catalogs adopt one shared
  architecture and alternatives become costly.

## 6. Authoring and rollout recommendation

Write ranks 1–3 first and review their shape before mass backfilling. Rank 1 should
produce the current explicit-memory record and one superseded predecessor, proving
lifecycle and traversal. Ranks 2 and 3 prove that the template works for a boundary and
an operational topology, not only for feature reversals.

Then add ranks 4–10 as one seed batch. Each should fit in roughly one to two pages,
include at least one credible rejected alternative, name a revisit condition, and cite
current enforcement points. If a draft becomes a subsystem overview, split or delete
it; the ordinary docs already do that job better.

Add ranks 11–12 after the seed review because both are recent and detailed supporting
research already exists. Add rank 13 only when the web substrate itself is accepted.
That sequencing yields a useful decision log even if the glossary migration described
by the source report never happens.

## 7. Sources

Internal evidence:

- [`glossary_to_memory_webs.md`](glossary_to_memory_webs/glossary_to_memory_webs.md)
- [`test_suite_verification_architecture.md`](test_suite_verification_architecture/test_suite_verification_architecture.md)
- [`naming_the_change_unit.md`](naming_the_change_unit/naming_the_change_unit.md)
- [`proc_ownership_and_shell_taxonomy.md`](proc_ownership_and_shell_taxonomy/proc_ownership_and_shell_taxonomy.md)
- [`finalizer_protocol_and_extensibility.md`](finalizer_protocol_and_extensibility/finalizer_protocol_and_extensibility.md)
- [`artifact_link_graph.md`](artifact_link_graph/artifact_link_graph.md)
- `sase:docs/architecture.md`, `docs/rust_backend.md`, `docs/workspace.md`,
  `docs/sdd_storage.md`, `docs/commit_workflows.md`, `docs/artifact_references.md`,
  `docs/artifact_links.md`, `docs/plugins.md`, and the commits cited in §2.

External guidance:

- Michael Nygard,
  [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
  — architecturally significant scope, one decision per short record, status, and
  supersession.
- AWS Prescriptive Guidance,
  [Architectural decision record process](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html)
  — decision-log overview/detail roles, context/decision/consequences minimum, review,
  immutability, and supersession.

## 8. Final ranked recommendations

1. **Prefer explicit, audited memory retrieval over automatic runtime recall** — Accepted; author it with one Superseded automatic-recall predecessor.
2. **Put deterministic cross-frontend behavior in Rust and keep orchestration/presentation in Python** — Accepted.
3. **Isolate agents in exclusively claimed numbered workspace clones** — Accepted.
4. **Persist orchestration state outside chat transcripts and UI processes** — Accepted.
5. **Model tracked change as a Patch containing ordered Stitches and use one provider-neutral mutation path** — Accepted.
6. **Let workspace providers own SDD placement in role-based sidecar repositories** — Accepted.
7. **Use a host-owned sealed finalizer protocol as the sole completion path** — Accepted, recent.
8. **Address durable records with typed artifact references and provider resolution** — Accepted.
9. **Extend capabilities through typed plugins with project-declared, fail-closed availability** — Accepted.
10. **Use two-speed verification: diff-scoped agent checks and exhaustive landing/CI checks** — Accepted.
11. **Supervise long-running commands outside ACE through one durable proc service** — Accepted, next wave.
12. **Use a closed typed artifact relation registry and keep scheduling dependencies in beads** — Accepted, next wave.
13. **Represent keyed memory collections as flat web descriptors with nested on-demand strands** — Proposed; accept only with the memory-web implementation decision.
