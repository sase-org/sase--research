# Improving SASE artifact-link adoption and quality

Date: 2026-08-24

## Executive summary

SASE already has most of the machinery needed for a useful artifact graph: a closed,
typed relation registry; durable sidecar storage; local materialization; automatic
`cites` and `read` provenance; audited reads; managed Markdown projections; and a
generic finalizer framework. The main problem is not storage. It is that the act of
creating an artifact and the act of declaring its semantic lineage are separate,
easy-to-forget operations.

The live graph confirms the resulting skew. Immediately before this report's own two
`derives-from` edges were added, it contained 142 edges, but only 58 were curated
semantic links. Of those 58, 41 were the generic
`related` relation and 17 were `derives-from`; there were no live `implements` or
`supersedes` links. The strongest adoption appears exactly where a scoped workflow
already suggests links. Generic plan and research creation do not provide comparable
support.

The best solution is therefore not a global instruction telling every agent to look for
links. It is a workflow-owned lineage system with three paths:

1. create deterministic links automatically when the workflow already knows the
   relationship;
2. finish the existing compact `links:` frontmatter inlet so an artifact-producing agent
   can declare semantic links next to the output it is writing; and
3. at the artifact's lifecycle boundary, show a small, ranked set of candidates from
   that run's prompt references and audited reads, asking for confirmation only when
   semantic judgment is required.

This gives ordinary agents zero additional prompt context. Only agents producing a
linkable artifact see a bounded, just-in-time linking prompt, and deterministic cases
need no model judgment at all.

## Scope and method

This research examined:

- the artifact registry, durable row format, sidecar indexes, local aggregation,
  projection refresh, CLI, ACE relation adapter, and Rust/Python boundary;
- the plan, research, task, and finalization workflows that create or consume artifacts;
- the live artifact-link graph and August 2026 plan/research inventories;
- the original artifact-link design research and the plans that implemented and later
  simplified the feature; and
- external provenance and catalog systems whose design pressures resemble SASE's.

Counts are a 2026-08-24 snapshot taken before this report's two curated source links were
added. Audited reads performed during this research increased the automatic `read` count
from 78 to 83, so the total edge count is intentionally less important than the curated
baseline. Inventory counts are also a rough denominator: not every Markdown artifact
needs a semantic link.

## What SASE has today

### A sound two-layer persistence model

Durable truth lives with the artifact provider: sidecar `links/**/*.json` files for file
artifacts and bead events for beads. A local aggregate under the SASE state directory is
a rebuildable cache. This is the right ownership boundary: a cloned artifact repository
brings its links with it, while queries do not need to scan every sidecar on every use.

Markdown projections expose the graph without making Markdown the database. Curated
links are rendered into a managed `## Links` block and automatic references into a
managed `## Referenced By` block. `sase artifact read` strips managed metadata before
returning content, so richer projections do not inherently increase model context.

### A deliberately small relation vocabulary

The closed registry currently has two automatic provenance relations and four curated
semantic relations:

| Relation | Current producer | Recommended meaning |
|---|---|---|
| `cites` | prompt-reference machinery | A prompt/run explicitly cited the target. |
| `read` | audited artifact reads | An agent/run read the target for a stated reason. |
| `derives-from` | CLI/manual | The source materially transforms, synthesizes, or is generated from the target. |
| `implements` | CLI/manual | The source is the concrete realization of the target requirement or design. |
| `supersedes` | CLI/manual | The source is the newer authoritative replacement for the target. |
| `related` | CLI/manual | A meaningful association exists and no more specific registered relation applies. |

`blocks` and `depends-on` correctly remain bead scheduling concepts rather than artifact
relations.

The vocabulary is sufficient for the immediate problem. The missing piece is a semantic
contract visible in CLI help and artifact-producing workflows: direction, examples,
recommended endpoint kinds, and when *not* to use each relation. In particular,
`implements` has no live examples and the existing plan-to-bead example is easy to read
in either direction. The registry should make the direction explicit: implementation
artifact → requirement/design artifact. A plan may implement a bead's requirement, but
a patch or stitch implementing a plan is the more intuitive example.

### Automatic provenance is not semantic lineage

Prompt references write `cites`; audited reads write `read`. These rows are valuable
evidence, but a read does not imply derivation. An agent can inspect a plan to compare,
reject, debug, or merely understand it. Automatically converting all reads into
`derives-from` would create a dense and misleading graph.

This distinction matches the W3C PROV model: an activity can *use* an entity without the
output entity necessarily being a derivation of every used entity; derivation denotes an
actual transformation or contribution to the new entity. PROV also treats revision as a
specialized form of derivation. See the [W3C PROV-O recommendation](https://www.w3.org/TR/prov-o/).

SASE should therefore keep an observational plane (`read`, `cites`) separate from a
semantic plane (`derives-from`, `implements`, `supersedes`, `related`). The former is
captured automatically; the latter is deterministic when a workflow knows it and
otherwise requires a small amount of explicit judgment.

## Evidence from the live graph

### Shape of the graph

The live aggregate contained:

| Measure | Count |
|---|---:|
| Total edges after this study's audited reads | 142 |
| Automatic `read` | 83 |
| Automatic `cites` | 1 |
| Curated/manual | 58 |
| Curated `related` | 41 |
| Curated `derives-from` | 17 |
| Curated `implements` | 0 |
| Curated `supersedes` | 0 |

Thus 70.7% of curated edges use the least specific semantic relation. The endpoint mix
shows two existing adoption channels:

| Curated edge shape | Count |
|---|---:|
| bead → bead, `related` | 23 |
| research → research, `derives-from` | 13 |
| research → bead, `related` | 7 |
| research → plan, `related` | 4 |
| research → research, `related` | 4 |
| bead → plan, `related` | 3 |
| file → research, `derives-from` | 2 |
| file → file, `derives-from` | 1 |
| file → plan, `derives-from` | 1 |

The task-creation skill explicitly teaches agents to add `related` links, which plausibly
explains the bead-heavy `related` cluster. Research consolidation naturally creates
obvious source/output pairs, which explains the `derives-from` cluster. By contrast,
the plan skill and core research xprompts contain no artifact-link step.

This is useful evidence that local workflow instructions work, while absence of a
workflow hook produces absence of links. It is also evidence against adding a broad
instruction to core memory: the same effect can be achieved only where relevant.

### Coverage is sparse and uneven

The August sidecars contained 603 plan Markdown files and 103 research Markdown files.
Only 32 distinct plans and 26 distinct research artifacts appeared anywhere in the live
graph, including automatic reads. Most linked documents had degree one.

Using the first live artifact-link CLI commit on 2026-08-20 as a rough feature-availability
boundary:

| Newly added artifact | Added after availability | Any link | Curated link |
|---|---:|---:|---:|
| Plans | 114 | 14 | 2 (1.8%) |
| Research Markdown | 26 | 12 | 10 (38.5%) |

This is not a claim that every plan should have a link. It does show that automatic reads
account for most plan visibility and that plan creation rarely results in an intentional
semantic edge. Research does better, but still depends on the particular workflow.

### Several implemented pieces are not connected end to end

The codebase already contains a tolerant Rust parser for a compact artifact-link
frontmatter inlet:

```yaml
links:
  - ref: bead:sase-js
    relation: implements
    description: Implements the accepted lifecycle design
```

It distinguishes absent, recognized, and unrecognized `links` shapes so it does not
mistake unrelated MkDocs-style metadata for artifact declarations. The function is
exported through the Python binding and checked by binding validation, but there is no
production caller. The original artifact-link research described this exact pattern:
consume the inlet during refresh, persist canonical rows, and normalize the declaration
away so source Markdown does not become a competing database or create digest feedback.

Two integration gaps prevent it from working today:

- strict plan frontmatter validation rejects the unrecognized `links` field; and
- no plan/research lifecycle command consumes the parsed rows and persists them.

There is a similar half-finished path for generated links. `derived` is a valid row
origin in the Rust/Python schema, but no live row uses it, and the projection classifier
renders only `manual`/`migrated` as curated and `prompt_ref`/`read` as automatic. A
`derived` row is currently neither class.

Finally, ACE's relation adapter flattens every artifact link to generic `links` or
`linked_by` relations. It drops the registered relation slug, inverse label,
description, origin, and use count. The Markdown projection preserves more semantic
information than the interactive relation UI.

## External design lessons

### Capture lineage at execution boundaries

[OpenLineage](https://openlineage.io/docs/) pushes collection into schedulers and
frameworks rather than relying on every job author to remember a separate lineage step.
Its core model records jobs, runs, and input/output datasets. The
[object model](https://openlineage.io/docs/spec/object-model/) distinguishes design-time
job identity from runtime run events, which is analogous to SASE separating artifact
meaning from an agent's observed reads.

An especially relevant OpenLineage refinement is explicit output-to-input attribution.
When a job has multiple inputs and outputs, treating every input as the source of every
output creates false Cartesian-product lineage. The emerging
[lineage job facet](https://openlineage.io/docs/next/spec/facets/job-facets/lineage/)
instead records the sources for each output. SASE should apply the same rule: a run's
read set is a candidate pool, not a set of automatic `derives-from` edges.

### Keep authoritative input compact; derive the graph

Backstage treats catalog relations as read-only output derived by processors from
authoritative descriptors and their surroundings. It commonly emits inverse pairs, but
users author the underlying fact rather than both graph directions. See the
[Backstage descriptor format](https://backstage.io/docs/next/features/software-catalog/descriptor-format/)
and its [model-extension guidance](https://backstage.io/docs/features/software-catalog/extending-the-model/).

Backstage also warns that a graph should capture the human mental model rather than
becoming an exhaustive inventory, and that the catalog is a cache over sources of truth.
That maps closely to SASE's durable sidecars plus local aggregate. See
[Creating the catalog graph](https://backstage.io/docs/features/software-catalog/creating-the-catalog-graph/).

GitHub follows the same lifecycle-boundary pattern for issue/PR links: a compact keyword
in a pull-request description or commit is interpreted by the host, which creates the
relationship and applies merge-time behavior. See
[Linking a pull request to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue?apiVersion=2022-11-28).

Together these systems suggest four principles:

1. collect facts where the workflow already knows them;
2. let authors declare compact intent, then normalize it into managed storage;
3. do not infer semantic lineage from mere co-occurrence or access; and
4. expose typed relationships that match a useful mental model, not every possible edge.

## Design goals

An improved system should satisfy the following constraints:

- **Zero steady-state context cost.** An agent that is not creating or replacing an
  artifact receives no artifact-link reminder.
- **Near-zero deterministic cost.** If a workflow already knows the relation, the host
  writes it without asking a model.
- **Bounded semantic cost.** An artifact-producing agent sees at most a small number of
  current-run candidates at the moment it can act on them.
- **Typed, directional meaning.** Specific relations are preferred over `related`, with
  examples and endpoint guidance available on demand.
- **One durable truth.** Markdown is an authoring inlet and projection; provider-owned
  indexes/events remain authoritative.
- **Explainable provenance.** The system distinguishes observed, declared, migrated,
  and host-derived assertions.
- **No false completeness.** Coverage metrics identify opportunities but never require
  every artifact to be linked.
- **Provider ownership.** A research plugin can define research-specific rules without
  expanding every SASE agent's core instructions.

## Options considered

| Option | Context cost | Link quality | Reliability | Assessment |
|---|---:|---:|---:|---|
| Put “always look for links” in global agent instructions | Every turn | Variable | Easy to forget; encourages `related` | Reject |
| Convert every `read`/`cites` edge into `derives-from` | None | Poor | Consistent but produces false lineage | Reject |
| Require explicit `sase artifact link add` after every output | Artifact turns only | Good when done | Separate step is frequently omitted | Useful fallback, insufficient alone |
| Infer all links from filenames, timestamps, or co-modification | None | Poor to moderate | Brittle and hard to explain | Use only for suggestions |
| Workflow instrumentation + compact declarations + bounded suggestions | Zero for unrelated turns | High | Deterministic where possible; confirmed otherwise | Recommend |

## Proposed architecture

### 1. Classify links by meaning, not merely by origin

Treat the graph as two planes:

- **Observed provenance:** `read`, `cites`. These answer “what did this run inspect or
  cite?” and remain automatic.
- **Semantic lineage:** `derives-from`, `implements`, `supersedes`, `related`. These
  answer “how are the artifacts meaningfully connected?” and may be manual or
  deterministically derived.

Projection routing should follow the relation class. A host-derived `implements` edge is
still a semantic link and belongs in the managed `## Links` view; a `read` edge remains
observational even if repeated many times. This also gives the currently unused
`derived` origin a coherent purpose: a semantic fact produced from authoritative
workflow state rather than model judgment.

Add relation metadata to the registry rather than to core agent instructions:

- concise definition and inverse label;
- direction with one positive and one negative example;
- allowed or recommended source/target artifact kinds;
- whether a workflow may derive it automatically; and
- whether it participates in retention, context expansion, or impact analysis.

Expose this through `sase artifact link relation list/show`, completions, and ACE's
relation picker. Prefer a specific relation whenever it applies; reserve `related` for
genuinely peer-like associations.

### 2. Finish the existing frontmatter authoring inlet

Integrate the existing Rust `links:` parser at provider lifecycle boundaries:

1. allow and strictly validate the recognized inlet in plan frontmatter;
2. resolve the final canonical source reference after the file is archived;
3. validate each target, relation, direction, and 240-character description;
4. upsert the durable provider-owned row;
5. remove the consumed inlet; and
6. refresh the managed projection.

Agent-declared inlet entries should be persisted as `manual` (or a future, explicitly
defined `declared`) origin. `derived` should be reserved for host facts. The inlet is not
durable truth and must not remain as a second editable representation.

Plan processing must happen inside `sase plan propose` or its archive operation. A plan
handoff terminates the runner mechanically and intentionally skips normal finalizers, so
an end-of-turn finalizer alone cannot make plan ingestion reliable. Research artifacts
can be consumed by the research provider's write/finalize boundary or a conditional
repository finalizer.

### 3. Instrument deterministic workflow relationships

The host should create edges whenever it already has authoritative structure:

- consolidated research report `derives-from` each selected draft;
- generated research infographic `derives-from` its source report;
- a `#research/more` continuation `derives-from` the earlier report it extends;
- a replacement document `supersedes` the old document when the workflow explicitly
  performs replacement; and
- plan/bead traceability derived from the existing plan `bead_id` and bead design
  reference, rather than storing a second independently editable association.

The last case needs an explicit relation decision. If the plan is treated as the
realization of a bead requirement, expose plan `implements` bead. If the native record
means only “this bead was created from this plan,” introduce or choose a relation whose
definition says that, rather than overloading `implements`. The important rule is to
materialize from the native association, not duplicate it.

Provider plugins should own these rules. The research-artifact plugin knows the draft,
consolidated-report, continuation, and image conventions; core SASE should provide the
link API and lifecycle hook but should not hard-code plugin filename patterns.

### 4. Add a conditional, bounded curation step

For relationships the host cannot know, use evidence already collected during the run:

1. track which linkable artifacts the run created or replaced;
2. assemble candidates from explicit prompt references, audited reads, assigned beads,
   and provider-native structure;
3. rank direct, current-run evidence above incidental or transitive evidence;
4. present at most five candidates per output with a suggested relation and short reason;
5. let the artifact-producing agent accept, edit, or decline them; and
6. persist only accepted semantic links.

Do not store suggestions as real link rows. The current upsert key is
`(source, relation, target)` and retains the row's original origin, creator, and creation
time while only updating the description (and automatic-use count). Persisting a
speculative `derived` row and later “confirming” the same edge would therefore fail to
record clean promotion to a human/model-declared assertion. Keeping candidates ephemeral
avoids this bug and keeps the graph trustworthy. If multiple independent assertions
become important later, evolve the model to store assertion provenance separately from
the materialized edge.

The generic finalizer framework is suitable for non-plan outputs: select an
`artifact-links` finalizer only when the run produced a linkable artifact and has
plausible candidates. Its context payload can contain only the output reference and the
bounded candidates. Unrelated turns do not select it and incur no tokens. Plan creation
uses the command-local step described above because its handoff bypasses finalizers.

### 5. Make links useful at retrieval time

Creation will improve only if links pay rent later. Add focused consumers:

- preserve relation slug, inverse, description, origin, and use count in ACE instead of
  flattening all edges to `links`/`linked_by`;
- offer a one-keystroke “link marked artifact to current artifact” action with a typed
  relation chooser and required reason;
- provide a budgeted one-hop context command that prefers `implements`,
  `derives-from`, and `supersedes`, with explicit filters for observational `read` and
  `cites` edges;
- show `supersedes` warnings when an agent opens an obsolete artifact;
- use incoming `implements`/`derives-from` edges for impact analysis and continuation
  context; and
- never expand transitively by default. A one-hop typed neighborhood is predictable;
  unconstrained graph traversal is a context explosion.

### 6. Add observability without turning coverage into a quota

Add `sase artifact link audit` (or extend `doctor`) with machine-readable measures:

- created artifacts with current-run candidates but no accepted semantic link;
- link counts by relation, origin, provider, and artifact kind;
- percentage of curated links using `related` when a more specific type may fit;
- dangling targets, unrendered origins, and projection drift;
- degree distribution and unusually dense nodes; and
- suggestion acceptance, edit, and decline rates.

The primary success denominator should be “new artifacts for which the workflow had a
credible candidate,” not all Markdown files. Useful initial targets would be:

- at least 80% of deterministic research relationships captured automatically;
- at least 60% of artifact outputs with credible candidates ending with a semantic link
  or an explicit decline;
- a declining share of `related` among newly curated links; and
- no measurable increase in base instruction tokens for runs that create no artifacts.

Run the audit in CI or periodic maintenance as a report, not a hard completeness gate,
until false-positive rates are well understood.

## Implementation sequence

1. **Semantics and visibility:** enrich the relation registry, define semantic versus
   observational projection classes, render `derived`, preserve typed fields in ACE,
   and add graph/audit statistics.
2. **Complete the authoring path:** permit validated `links:` frontmatter, consume it in
   plan and research lifecycle commands, normalize it away, and test canonical source
   resolution and duplicate handling.
3. **Instrument deterministic research paths:** drafts → consolidated report,
   report → infographic, and continuation → prior report. Materialize plan/bead links
   from native lifecycle state after settling their exact semantics.
4. **Add bounded suggestions:** use current-run prompt/read evidence in a conditional
   finalizer for ordinary artifacts and inside `sase plan propose` for plans. Persist
   only confirmed semantic links.
5. **Improve graph consumption:** typed ACE navigation, replacement warnings, one-hop
   context bundles, and impact queries.

Each phase is independently useful. The first two should precede model-generated
suggestions so agents are choosing from a clear vocabulary and the system has a reliable
place to persist their answer.

## Recommended solution

Implement **workflow-owned artifact lineage with a normalized authoring inlet and
conditional curation**.

Concretely, finish the already-built `links:` frontmatter parser and consume declarations
inside `sase plan propose` and research-provider finalization; automatically emit
`derived` semantic edges for relationships the workflow knows with certainty; and use a
selected artifact-link finalizer only when a non-plan run produced an artifact and has a
small candidate set from that run's prompt references and audited reads. Present no more
than five candidates per output and persist only those the agent confirms. Keep
`read`/`cites` as observational evidence rather than silently promoting them to semantic
lineage.

At the same time, make the graph worth maintaining: define relation direction and
endpoint guidance in the registry, route projections by semantic versus observational
relation class, surface full typed edges in ACE, and add an audit command whose coverage
denominator is artifacts with credible candidates. Put research-specific rules in the
research-artifact plugin and plan-specific ingestion in the plan command. Do not add a
global agent-memory reminder.

This design addresses the observed adoption gap while keeping average context unchanged:
most agents see nothing new, deterministic workflows incur no model work, and only an
agent that has just created a relevant artifact receives a short, actionable linking
decision at the point where it has the necessary context.
