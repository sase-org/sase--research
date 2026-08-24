---
create_time: 2026-08-24
updated_time: 2026-08-24
status: research
tags:
  - ace
  - artifacts
  - agents
  - query-language
  - artifact-links
  - revival
  - tui
  - sase-core
---

# The Artifacts Agents Sub-tab: One Catalog, Two Levels of Identity, One Shared Query Engine

**Research question.** What is the best way to implement an **Agents** sub-tab under
ACE's **Artifacts** tab so it is an excellent historical/queryable agent catalog,
participates correctly in artifact-link navigation, and can revive archived agents,
without replacing the live operational purpose of the main **Agents** tab?

**Scope.** This report designs the Agents sub-tab. The artifact-link storage and
projection defects catalogued in
`artifact_link_derivation/artifact_link_derivation.md`, and the later project to make
every TUI tab link-aware, remain separate phases. This design deliberately leaves the
right seams for those phases and includes only the minimum link work required for the
new pane to be a valid destination.

**Method and snapshot.** Code and live-index inspection on 2026-08-24 at `sase`
`9abe1967b`, `sase-core` `b5d7f3c`, the research sidecar `d65fd9d`, and the agent
artifact sidecar `2de122bf3`. I reviewed the shipped Artifacts pane contract, shared
query profiles and Rust evaluator, the main Agents query dialect and loader, agent
identity/publication code, dismissed-bundle index, revival flow, and artifact-link
relation adapter. I also verified the live configured pane inventory and index sizes.

---

## Bottom line

Build the new pane as a **historical agent catalog adapter inside the existing
Artifacts contract**, not as a second copy of the main Agents widget and not on the
standalone Python agent-query parser.

The two tabs have different primary jobs:

| Surface | Primary job | Default corpus | Interaction model |
| --- | --- | --- | --- |
| Main **Agents** tab | Operate the live agent inbox | Active and recent agents | Live tree, attention state, orchestration actions |
| **Artifacts → Agents** | Find and inspect durable agent history | Complete indexed metadata, including dismissed history | Query-first catalog, stable rows, detail/relations, revival |

They should share three backend services—catalog snapshots, query profiles, and
revival—but they should not share a large stateful Textual widget.

The central modelling choice is a **two-level inventory**:

1. a selectable family/solo banner represents the durable **Sase Agent** artifact; and
2. concrete agent-shell rows beneath it carry run-specific status, timing, model,
   content locations, and revival identity.

That reconciles three truths the current code keeps separate:

- `@agent:<solo>` names a solo Sase Agent;
- `@agent:<family>--<role>` resolves to the family page's `#member-<role>` anchor; and
- revival restores a concrete dismissed run and, where applicable, its workflow
  children.

Use the existing profile-driven Rust query engine with `boolean=True`. Extend that
shared engine once with a typed `duration` field and comparison syntax so useful agent
queries such as `age>2h` and `runtime>=5m` do not require a permanent agent-only parser.
Keep default free-text search metadata-only; do not read tens of thousands of prompt and
chat files while building the pane. Full-content search should be an explicit later FTS
capability.

The new pane should query the persistent agent artifact index and dismissed-bundle
summary index off-thread. It must never use the main tab's Tier-2 source scan. On this
machine the relevant scale is already approximately 8,054 indexed artifact rows plus
26,657 valid dismissed bundle summaries, so cached snapshots, capped/virtualized result
rendering, and lazy detail hydration are requirements, not polish.

Finally, extract revival from the `AceApp` Agents-tab mixins into a backend operation
that returns a typed delta. Keep the existing `R` modal on the main Agents tab, but make
both it and the new pane call that operation. On the new pane, `R` revives the selected
or marked concrete rows; a family banner with multiple revivable members opens a
prefiltered chooser.

---

## 1. What has already landed

The prior Artifacts contract research is no longer merely aspirational. Most of its
foundation is present and should be extended rather than bypassed.

### 1.1 The Artifacts host already has the correct extension point

`src/sase/ace/tui/_artifact_tab_model.py:26-37` currently defines four fixed panes:

```text
stitches → patches → beads → files
```

`sase artifact pane show agents -j` confirms that `agents` is not configured; the live
inventory is `stitches`, `patches`, `beads`, `ref:plan`, `ref:research`, and `files`.

Each existing built-in is declared in
`src/sase/ace/tui/_artifact_tab_contract_adapters.py`, compiled through
`compile_builtin_contract()`, assigned a `CompiledQueryProfile`, and automatically
enriched with artifact-link relations by `with_artifact_link_relations()`
(`_artifact_tab_contract.py:69-126`). The closed capability vocabulary already includes
the features the new pane needs:

- entry navigation and opening;
- filter sessions, query history, and saved queries;
- refresh and project scope;
- stable marks and stable-reference copy;
- detail scrolling;
- relations, grouping, status counters, and mutation.

Therefore Agents should be a fifth built-in adapter. Adding a bespoke screen outside
this contract would immediately forfeit the very shared behavior the user wants.

### 1.2 The shared query infrastructure is real and production-ready

`src/sase/ace/query_profile/` defines pane-authored schemas that compile to immutable,
digested profiles. A field can be typed as string, enum, bool, date, or int and can be
independently searchable, filterable, repeatable, negatable, and exact-matching.

`ArtifactQuerySession` provides:

- off-thread Rust evaluation;
- a bounded result cache keyed by pane, snapshot generation, profile digest, and
  canonical query;
- one live worker per pane with pending-query coalescing; and
- stale-result rejection by generation.

The corpus itself is compiled into a Rust handle by
`compile_artifact_query_index()`. Beads, files, plans, stitches, patches, and procs
already have profile adapters. What is missing is simply an `agents_query_schema()` and
an agent catalog row adapter.

The engine already supports Boolean profiles. Patches uses `boolean=True`, so AND, OR,
NOT, implicit conjunction, and parentheses do not require another parser.

### 1.3 There is also a separate Agents-only query language

The main Agents tab currently uses
`src/sase/ace/agent_query/{tokenizer,parser,evaluator,highlighting}.py`. It supports:

- Boolean expressions and parentheses;
- substring fields `status`, `cl`, `project`, `name`, `model`, `provider`, `tribe`, and
  `text`;
- enums `type`, `source`, and `needs`;
- booleans `pinned`, `hidden`, and `attention`; and
- `age` comparisons such as `age>2h`.

This dialect predates the now-shipped shared profile machinery. Reusing it for the new
pane would institutionalize two parsers and two completion/canonicalization systems. It
would also exclude the new pane from shared saved-query profile digests and Rust corpus
evaluation.

The correct migration direction is the reverse: make the shared profile expressive
enough for Agents, build the new pane on it, then optionally rewire the main Agents tab
to the same profile in a later cleanup. The existing main tab does not need to be
rewritten before this pane can ship.

### 1.4 The link graph already tries to navigate to a pane that does not exist

`src/sase/ace/tui/relations/artifact_links.py:182-183` maps an `agent:` reference to:

```python
ArtifactEntryTarget("agents", (payload,))
```

There is no Agents pane and `_known_target_for_ref()` has no Agents branch. This is the
specific missing destination identified by the artifact-link derivation report. Adding
the pane will not by itself make all links correct—the relation adapter currently
collapses typed link rows into generic `links`/`linked_by` edges, and the aggregate has
known loss/retention defects—but it will stop agent endpoints from being structurally
unnavigable.

---

## 2. The product boundary: catalog, not duplicate control room

The main Agents tab is a live control room. Its loader intentionally paints a small
Tier-1 inbox from the persistent index—up to 1,000 active and 200 recently completed
records—and only later reconciles broader history. Its row tree carries live workflow
children, folds, attention state, provider/runtime state, agent controls, and display
cache behavior.

The new pane should instead optimize for questions such as:

- Which agent read this research report?
- Find failed Codex agents in project `sase` from the last week.
- Which members of this family ran under which models?
- Find dismissed agents associated with a patch and revive the right one.
- Show agents with questions, retries, output variables, commits, or linked artifacts.
- Jump from an artifact-link edge to a stable agent result even when it is not in the
  live inbox.

Embedding the existing `AgentList` would bring the wrong defaults and tight coupling:

- it is centred on live `AceApp` state rather than an immutable pane snapshot;
- its historical Tier 2 deliberately performs a source scan;
- its query evaluation assumes the standalone Python dialect and optional content-file
  cache; and
- revival callbacks directly refresh/select rows only when `current_tab == "agents"`.

The two surfaces can still converge over time. The shared layer should be deliberately
below both widgets:

```text
agent artifact index + dismissed summary index + sidecar publication
                              │
                    AgentCatalogSnapshot
                              │
          ┌───────────────────┴───────────────────┐
          │                                       │
  main Agents adapter                    Artifacts Agents adapter
  live tree / operations                 catalog / query / relations
          │                                       │
          └──────────── shared revival service ───┘
```

This preserves the custom revival panel while making it possible to retire that panel
later without making retirement part of the current project.

---

## 3. Identity and row model

### 3.1 Why one flat notion of “agent” is insufficient

The project's glossary and `src/sase/sase_agent.py` define a **Sase Agent** as either a
family or a solo agent. It owns an ordered sequence of concrete agent shells. A family
member spelling such as `foo--code` projects to Sase Agent `foo`.

The sidecar reflects both levels:

- `families/<global-family>.md` is the family artifact, with a lineage table and
  `#member-<role>` anchors; and
- `agents/<global-shell>/README.md` is the concrete shell page with chat, files,
  commits, model/provider, state, and timing.

The core resolver makes the distinction explicit:

- a solo name maps to `agents/<global-name>/README.md`; and
- a member name maps to `families/<global-family>.md#member-<role>`.

Meanwhile, the persistent agent artifact index and dismissed archive are run-oriented,
and revival needs a concrete `raw_suffix`/bundle identity. A single family row loses
revival precision; a flat shell-only list loses the durable family artifact and makes a
family-level link ambiguous.

### 3.2 Recommended model: selectable group banner plus concrete rows

Use two immutable records in one snapshot:

```text
AgentArtifactGroup
  stable target: agents / ("agent", <global family-or-solo name>)
  kind: family | solo
  aggregate fields: projects, states, members, models, providers, timing

AgentCatalogRow
  stable target: agents / ("shell", <global concrete name>)
  group id: global family-or-solo name
  run identity: artifact_dir + raw_suffix/source_run_id
  source flags: live-index | dismissed-archive | published-sidecar
```

The visible hierarchy is shallow and stable:

```text
▾ research.12                         family/solo artifact banner
    research.12--plan    completed    concrete shell row
    research.12--code    dismissed    concrete shell row
```

For a solo agent, the banner and sole shell may be visually collapsed into one row, but
the data model should retain both concepts. That avoids later special cases when a solo
gains family-like relations or multiple archived attempts.

Query matching happens on concrete rows. A group banner remains visible when at least
one child matches, and can show `1 of 4 members`. Family-level fields may be copied onto
child query rows so `family:research.12` and free text behave naturally.

### 3.3 Stable target and alias rules

The pane must accept all durable spellings that can appear in a link:

1. canonical global family/solo name;
2. canonical global member name;
3. local names owned by the current machine;
4. historical aliases already known to the agent artifact index/name registry; and
5. member references that resolve to a family page anchor even if the concrete shell
   row is unavailable.

Recommended resolution order:

1. canonicalize with the Rust agent-identity functions;
2. prefer an exact concrete member row;
3. otherwise project a member to its family banner;
4. match an exact solo/family banner; and
5. retain a pending target while an exact indexed lookup hydrates an older row.

Add an Agents branch to `_known_target_for_ref()`; do not compare raw payload strings in
the widget. The same pure resolver should be used by artifact-link navigation, pending
entry requests, copy-reference lookup, and tests.

The copied reference should always be globally durable:

- concrete row: `@agent:<global-member-or-solo>`;
- family banner: `@agent:<global-family>`.

### 3.4 Project scope is a view, not identity

Agent global names are durable across projects, while the index also records a project.
The pane should declare `project_scoped=True` and honor the Artifacts project's shared
scope selector. “All projects” remains available. Project must never be embedded into
the stable target merely to disambiguate a row; use the globally qualified agent name
and run identity.

---

## 4. Catalog data source and performance contract

### 4.1 Use indexes, never the historical source scanner

The live agent artifact index already contains fields useful to the catalog: project,
workflow, clan/tribe, family, timestamp, status, type, patch, agent name, model,
provider, start/finish times, parent/step lineage, retry chain, hidden state, marker
state, and the full compact scanner record JSON.

It supports a full-history query, but the current main TUI loader explicitly returns
`None` for `full_history=True` and then calls `scan_artifacts()`
(`_agent_loader_artifacts.py:108-109,171-182`). That is appropriate legacy behavior to
remove from the main tab eventually, not behavior to copy into a catalog.

The dismissed-bundle summary index adds exactly the archive fields needed for initial
display and filtering: agent name/type, patch, status, start/stop, project, model,
provider, VCS provider, workflow, parent/step identity, and retry lineage. Full bundle
JSON should only be read after selecting a row for detail or revival.

Live measurements on this machine:

| Index | Rows / state |
| --- | ---: |
| Agent artifact index | 8,054 indexed |
| Visible inbox projection | 684 visible |
| Hidden terminal rows retained | 4,583 |
| Dismissed identities projected into artifact index | 35,923 |
| Valid dismissed bundle summaries | 26,657 |
| Corrupt/stale/missing dismissed summaries | 0 / 0 / 0 |

The exact values will drift, but the order of magnitude is the design input.

### 4.2 Introduce a catalog snapshot boundary

Define a widget-free `AgentCatalogSnapshot` with:

- deduplicated group and shell records;
- stable-id maps and alias maps;
- a compiled `ArtifactQueryIndex`;
- observed facets;
- artifact-link snapshot/generation;
- source/index signatures and completeness diagnostics; and
- lazy locators for sidecar pages and dismissed bundles.

The long-term backend/domain contract belongs in `sase-core`: a CLI, editor, or web
frontend will need the same identity reduction, archive deduplication, and query fields.
Python should remain a thin adapter from core wires to Textual row/detail models.

It is reasonable to stage this without first migrating the entire Python
dismissed-bundle SQLite implementation. A first core wire can accept/project the
existing compact summary rows, while the durable ownership of catalog identity and
deduplication lands in Rust. Do not let that staging decision leak dismissed bundle
objects into the pane.

### 4.3 Snapshot and rendering rules

The pane should follow these rules:

- **Cached first, revalidate explicitly.** Pane activation consumes the last snapshot
  immediately if present and schedules refresh off-thread. The shared refresh action
  may request revalidation.
- **Generation keyed.** Index signatures, project scope, and catalog generation are
  part of cache invalidation. Query results already include the query-profile digest.
- **Full corpus, bounded presentation.** A query evaluates across complete indexed
  metadata, including dismissed history, but the option list renders a bounded page or
  virtualized window. Empty-query display should default to newest results and clearly
  show `showing N of M`; it must not create 30,000 Textual options.
- **Exact navigation bypasses the display cap.** A link target or stable pending target
  requests one indexed identity even if it is older than the current result window.
- **Lazy detail.** Prompt, chat, response, commits, diffs, variables, and bundle JSON
  are loaded for the selected stable id after the normal detail debounce.
- **Thin pump callback.** Worker completion swaps immutable state and refreshes only
  affected rows/panels. No filesystem reads, subprocesses, or index rebuilds occur in
  render/watch/callback paths.
- **Stable marks.** Mark concrete stable targets, not row positions. A group mark
  expands to its currently matching concrete children at action time and previews the
  count.

Suggested acceptance budgets—not existing project guarantees—are no synchronous I/O on
pane activation or keystrokes, a cached first paint within one event-loop frame, and
interactive query evaluation/render update below 150 ms at the measured 30k-row scale.
The implementation should add a representative performance fixture rather than rely on
the exact numbers as a brittle test.

### 4.4 Do not eagerly port content search

The main Agents tab's `AgentContentSearchCache` searches prompts, replies, chat fallback,
and attempt replies. It reads up to 512 KiB per file and caches by mtime. That is useful
for a 200-row inbox built on a worker. Applying it to the complete archive would turn a
metadata query into tens of thousands of file stats and reads.

For the catalog:

- default free text searches indexed metadata, names, patch/workflow/step, compact
  summary/error text already present, and published sidecar summary fields;
- an explicit future `content:` field should use a persistent full-text index over
  prompt/chat/response content; and
- until that FTS index exists, omit `content:` rather than silently perform a source
  scan.

The main tab can retain its existing content behavior during the migration.

---

## 5. Recommended query language

### 5.1 Use one Boolean compiled profile

Add `agents_query_schema()` to `src/sase/ace/query_profile/profiles.py` and register it
for pane id `agents` in `pane_registry.py`. Set `boolean=True` so all of these work:

```text
project:sase AND (status:failed OR needs:input)
family:research.12 AND NOT role:plan
dismissed:true AND revivable:true AND provider:codex
patch:sase-42 AND (retry:true OR attention:true)
```

The profile then automatically participates in shared parsing, canonicalization,
completion, facets, saved-query digests, history, and off-thread Rust batch evaluation.

### 5.2 Field set

The first profile should be broad enough to answer actual operational and provenance
questions, but every field must be cheap to populate from indexes.

| Field | Type / matching | Meaning and recommended values |
| --- | --- | --- |
| `name` | string, searchable | Global/local concrete name plus display aliases |
| `family` | string, exact-capable | Global/local Sase Agent family/solo identity |
| `role` | string/enum | `plan`, `code`, `review`, `monitor`, or observed role |
| `kind` | enum | `solo`, `family-member`, `workflow`, `monitor` as non-overlapping row facts |
| `project` | string, repeatable | Display name plus accepted aliases; never project-spec keys in UI |
| `patch` | string, repeatable | Patch name; do not perpetuate the legacy user-facing `cl` term |
| `bead` | string, repeatable | Associated bead ids from indexed metadata |
| `workflow` | string | Workflow/xprompt identity |
| `step` | string | Step name/index |
| `parent` | string | Parent agent name/identity |
| `clan` | string | Agent clan |
| `tribe` | string, exact-capable | User-defined tribe |
| `status` | enum/observed values | Canonical runtime state |
| `active` | bool | Derived live-state bucket |
| `attention` | bool | Stopped/error/needs-input state requiring attention |
| `needs` | enum | At least `input`; extend from normalized state facts |
| `dismissed` | bool | Present in dismissed projection/archive |
| `revivable` | bool | A valid bundle can be restored now |
| `hidden` | bool | Hidden from the live inbox |
| `pinned` | bool | Pinned agent identity |
| `retry` | bool | Any retry-chain participation |
| `attempt` | int | Retry attempt number |
| `source` | enum | `axe`, `manual`, and other canonical launch sources |
| `model` | string, repeatable | Model name |
| `provider` | string, repeatable | LLM provider |
| `effort` | string/enum | Reasoning effort when known |
| `since` / `until` | date bounds | Started/created timestamp, using shared relative dates |
| `runtime` | duration | Finished-started or indexed active elapsed duration |
| `age` | relative-date alias | Time since start; canonicalized to an absolute date bound |
| `has` | enum, repeatable | `prompt`, `chat`, `reply`, `commit`, `diff`, `question`, `error`, `plan`, `bead`, `output`, `vars`, `links` |

`status`, `role`, `model`, `provider`, `project`, and `tribe` completions should merge
static canonical values with observed snapshot facets. An unknown observed model or
provider must remain queryable without a release.

### 5.3 Extend typed comparisons in the shared engine once

The shared profile's current `FieldValueKind` lacks `duration`. Duration bounds work
only through host-reserved int keys `min` and `max`, while the main Agents dialect has
the much clearer `age>2h` form.

Recommended change:

1. add `duration` to the compiled field vocabulary;
2. allow generic `<`, `<=`, `=`, `>=`, and `>` comparison operators for typed int,
   duration, and date fields in the Rust profile parser/evaluator;
3. normalize whole-unit literals (`30s`, `5m`, `2h`, `1d`) to canonical seconds;
4. canonicalize `age>2h` to the corresponding absolute start-time bound using the
   configured clock/timezone; and
5. include the resolved time anchor or normalized bound in the query cache key so a
   relative query cannot remain valid forever.

This is query-infrastructure work, but it is justified by this pane and useful to Procs
and other timed artifacts. It avoids a permanent special parser while preserving the
best syntax users already know.

If implementation sequencing requires the pane before generic comparisons land, use
the existing shared forms (`since:2d`, `until:2026-08-01`, `min:5m`, `max:2h`) as a
temporary beta syntax and normalize legacy `age...` input at the Agents profile
boundary. Do not expose a second AST/evaluator to the new pane.

### 5.4 Link-aware query fields should follow lossless link data

Ultimately the profile should support:

```text
has:links
relation:read
artifact:"@research:202608/..."
linked:true
```

However, the artifact-link derivation report proves the aggregate is currently lossy,
and the TUI relation adapter discards relation, description, origin, and uses while
projecting rows. Shipping negative filters such as `linked:false` on incomplete data
would provide confidently wrong answers.

Recommended staging:

- first version: show the existing relation rail and make agent targets navigable;
- reserve a link-enrichment field seam on `AgentCatalogRow`; and
- enable `relation`, `artifact`, and `linked` query fields only after the separate
  artifact-link index/projection fixes make the snapshot complete and typed.

This keeps step 2 out of scope without forcing a later pane rewrite.

### 5.5 Example high-value saved queries

Seed examples in help/documentation, not hard-coded user slots:

```text
# Needs attention in the current project
active:true AND (attention:true OR needs:input)

# Recent failed Codex work
provider:codex AND status:failed AND age<7d

# Revivable implementation agents for one patch
patch:sase-42 AND role:code AND dismissed:true AND revivable:true

# Retry chains using a particular model
retry:true AND model:gpt-5.6-sol

# Family lineage excluding monitors
family:research.12 AND NOT kind:monitor
```

---

## 6. Pane contract and interaction design

### 6.1 Built-in adapter declaration

Add `agents` to the fixed sub-tab order **after Files**. This preserves the order and
digit shortcuts of the existing four built-ins; Agents becomes the next fixed digit
before provider panes are assigned remaining slots.

Recommended adapter facts:

| Fact | Value |
| --- | --- |
| `pane_id` / adapter | `agents` |
| ref kind / target prefix | `agent` / `agent` |
| inventory, fields, stable identity | true |
| revisions | false in v1; shell lineage is a relation/group, not document versions |
| can mutate | true, because revival is a host-owned mutation |
| project scoped | true |
| detail | true |
| query profile | compiled `agents_query_schema()` |
| default grouping | by Sase Agent/family |
| status counters | active, attention, failed, dismissed, revivable |
| empty state | “No agents match the current project scope and query.” |

Suggested icon/accent can follow design review; the architecture should not depend on
them. Add the pane id, icon, accent, descriptor, adapter, profile registry entry, and
`ArtifactsView._compose_pane()` branch together so no half-configured target exists.

Because this is user-reaching behavior landed before completion, create a disabled beta
only through `sase flag new <key>`. A reasonable key is `artifacts_agents_pane`. The Off
branch should omit the descriptor and preserve current behavior; the removal condition
should require query, exact link navigation, revival, performance, and both-tab
regression tests to pass. No flag was created as part of this research task.

### 6.2 Layout

Use the shared Artifacts shell and split modes:

- **list:** compact query results and family banners;
- **detail:** selected group/shell metadata and lazy content links;
- **relations:** family/parent/retry/artifact-link edges using the host relation rail.

Recommended compact shell row:

```text
● research.12--code   completed   sase   gpt-5.6-sol/codex   18m   3h ago
```

Responsive priority should be name → status → project/patch → timing → model/provider.
Narrow layouts elide from the right; they must not shorten the stable identity used by
navigation.

The detail panel should contain, when available:

1. canonical/local name, Sase Agent family/solo identity, role, project, patch, tribe;
2. state, start/finish/runtime, retry and parent/step lineage;
3. model/provider/effort and launch source/workflow;
4. prompt/chat/reply and published artifact paths;
5. commits, changed files/diff summary, plans, beads, output variables;
6. error/question/wait state; and
7. family, retry, parent/child, and artifact-link relations.

The family banner detail shows an ordered member timeline rather than pretending the
family has one model or one status.

### 6.3 Grouping

Recommended modes:

- **By agent** (default): family/solo banner with concrete children;
- **By date:** started day/week;
- **By project:** configured project display name;
- **By status:** active/attention/completed/failed/dismissed;
- **By patch:** patch association; and
- **By tribe:** user grouping.

Grouping must be a presentation of the query result, never a second filtering system.
Stable marks and pending targets survive regrouping.

### 6.4 Actions and copy targets

The pane should inherit normal Artifacts navigation, filter, history, saved query,
refresh, grouping, marking, detail scroll, relation jump, and project-scope actions.

Agents-specific actions:

- `R`: revive selected/marked revivable shell rows;
- open the published agent/family Markdown page;
- open prompt/chat/reply where present;
- copy globally durable reference, name, family, chat/reply path, JSON summary, or
  handoff text; and
- later, invoke generic artifact-link creation once that becomes a shared host action.

The current global `R` dispatcher checks only `current_tab == "agents"`; on Artifacts it
falls through to Patch rewind. Route `R` through the active Artifacts pane/capability
first so `Artifacts → Agents` invokes revival while other panes retain their existing
meaning. Keep `R` unchanged on the main Agents tab.

---

## 7. Revival architecture

### 7.1 Current coupling

The existing flow is capable but UI-bound:

- `R` on the main Agents tab opens recent and saved dismissal groups, then custom
  archive search;
- custom search pages top-level dismissed bundles from the summary index and hydrates
  selected bundles;
- `_do_revive_agent()` / `_do_revive_agents()` restore artifact files, update the
  dismissed set, purge bundle summaries, rebuild/sync index projections, upsert restored
  artifact rows, update epochs, refilter the main list, and select the revived row; and
- the completion callback explicitly exits unless `current_tab == "agents"`.

Calling these mixin methods from the new pane would couple it to main-tab in-memory
state and make cross-tab refresh brittle. The mutation also performs substantial disk
work in a UI callback.

### 7.2 Extract one backend operation

Introduce a widget-free request/result boundary, conceptually:

```text
ReviveAgentsRequest
  concrete identities / raw suffixes
  include workflow children
  optional saved/recent group provenance

ReviveAgentsResult
  revived identities and artifact dirs
  skipped/missing/failed identities with stages
  dismissed/index generation deltas
  notifications/log payloads
```

The operation owns the transaction-like ordering already encoded in the mixins:

1. resolve and validate bundle summaries;
2. hydrate only requested bundles;
3. plan parent/child removals;
4. restore artifacts;
5. persist the dismissed set;
6. purge/mark revived bundles before rebuilding the dismissed projection;
7. upsert restored artifact rows; and
8. return a delta for interested views.

Run it off the event loop as a tracked user operation. The main Agents adapter consumes
the delta to refilter/select; the Artifacts adapter invalidates its catalog generation,
re-runs the current query, preserves marks for failures, and selects the revived row.
Both can publish the same success/failure notifications and logs.

### 7.3 Selection semantics

Recommended defaults:

- a concrete dismissed shell row revives that row and its workflow children using the
  existing parent rule;
- marked concrete rows revive as one batch;
- a family banner with exactly one revivable concrete child revives it;
- a family banner with multiple revivable children opens the existing custom selection
  UI already prefiltered to the family;
- an active/completed non-dismissed row reports “not revivable” without mutation; and
- a row whose summary exists but bundle is missing remains visible with a diagnostic
  and cannot be marked revivable.

Single-row revival can proceed after the user presses `R`; batch/family revival should
show the concrete count and names before applying because the visible group may contain
more rows than fit on screen.

### 7.4 Preserve the custom main-tab panel

Do not deprecate or remove the existing group-first revival panel in this project. It
has capabilities the new pane will not immediately reproduce—saved/recent dismissal
groups and archive-specific selection. Refactor it to call the shared operation, then
let real usage determine whether the panel is still valuable after the catalog ships.

---

## 8. Relations and future artifact-link integration

### 8.1 Relations available independently of artifact links

The Agents adapter can declare useful native relations immediately:

| Relation | Kind | Direction / target |
| --- | --- | --- |
| family / members | family | banner ↔ concrete shell |
| parent / children | hierarchy | concrete shell ↔ concrete shell |
| retry-of / retried-as | hierarchy or link | concrete shell ↔ concrete shell |
| workflow steps | family | parent ↔ ordered step shells |
| patch | link | agent → Patches pane |
| beads/plans | link | agent → Beads/provider pane when indexed association exists |

These should be built from the immutable catalog snapshot and known stable targets, not
by reading metadata during relation rendering.

### 8.2 Minimum artifact-link work in this phase

Although general link improvement is out of scope, the Agents pane cannot be considered
complete without:

1. canonical known-target resolution for family, member, solo, local, and global
   `agent:` spellings;
2. `entry_targets()` containing both visible concrete rows and selectable group banners;
3. pending exact lookup for filtered/capped history;
4. artifact-link edges appearing in the existing relation rail; and
5. cross-pane tests from another artifact to an agent and back.

Do **not** fix the aggregate retention, read-link persistence, typed edge projection,
bead endpoints, or global TUI link actions opportunistically inside this pane change.
Those have wider ownership and are already sequenced in the derivation report.

### 8.3 Seams for the later all-tab integration

Every catalog row/group should expose these host-neutral facts:

- stable `ArtifactEntryTarget`;
- canonical artifact reference;
- source project(s);
- available artifact relations;
- open/copy locators; and
- mutation capability facts separate from relation facts.

That is enough for a later generic “link selected artifact to …” action to include Agents
without importing an Agents widget. Chops can then point at the canonical agent/family
targets of launches through the same relation layer.

---

## 9. Open questions and recommended defaults

These are the decisions worth making explicitly before implementation. Each has a
recommended default so work need not stop for every choice.

### Q1. Is the new pane a replacement for the main Agents tab?

**Recommended: no.** Treat the main tab as the live operational inbox and the new pane
as the durable queryable catalog. Share backend services. Revisit deprecation only
after usage data shows the catalog covers the group-first revival workflow and live
tree operations.

### Q2. Is one row a Sase Agent, a shell, or a historical run?

**Recommended: concrete shell/run rows grouped beneath a selectable family/solo Sase
Agent banner.** This preserves query/revival precision and exact member links while
retaining the durable artifact identity. Do not aggregate all runtime state into one
family row.

### Q3. Does the corpus include dismissed and hidden history by default?

**Recommended: the query corpus includes all indexed metadata, including dismissed
history; the empty-query presentation is capped and excludes explicitly hidden noise
unless requested.** Queries search the full corpus, and exact navigation bypasses the
cap. This is how old link endpoints remain reachable without rendering 30k rows.

### Q4. Should it reuse the current Agents Python query parser?

**Recommended: no.** Add a Boolean Agents profile to the shared Rust-backed query
contract. Preserve familiar syntax via shared typed-duration comparisons or a narrow
normalization adapter, then migrate the main tab later.

### Q5. Is `age>2h` worth extending shared query infrastructure?

**Recommended: yes.** Add generic typed comparison and duration support once in Rust.
It is materially clearer than pane-relative `min`/`max`, benefits Procs too, and removes
the only strong reason to retain the standalone parser. If it cannot land first, use
shared date bounds temporarily behind the beta flag.

### Q6. Should free text search complete prompt/chat/reply content?

**Recommended: not in v1.** Search indexed metadata by default. Later add explicit
`content:` backed by persistent FTS. Never walk the archive on each filter session.

### Q7. Should the pane be current-project-only?

**Recommended: honor the shared project selector and support All projects.** Start in
the same scope as other Artifacts panes. Always copy globally qualified references.

### Q8. What does `R` do on a family row?

**Recommended: revive directly only when one concrete child is revivable; otherwise
open a prefiltered chooser.** Concrete-row `R` remains direct, and marks provide batch
revival.

### Q9. Should the existing revival modal be retired now?

**Recommended: no.** Refactor its mutation backend, keep its UX, and evaluate later.
The new pane adds a better discovery route without forcing a premature removal.

### Q10. Should artifact-link fields be queryable in v1?

**Recommended: relation navigation yes; negative/completeness-sensitive link filtering
no.** Enable link query fields after the separate aggregate and typed-projection defects
are fixed.

### Q11. Should Agents be a document provider instead of a built-in?

**Recommended: built-in adapter.** Agent inventory, live/archive reconciliation, and
revival are host-owned domain behavior, not a declarative sidecar document inventory.
The published sidecar remains the openable durable representation.

### Q12. Where should catalog reconciliation live?

**Recommended: Rust core wire/domain service with thin Python presentation adapters.**
Identity reduction, deduplication, query fields, and revival semantics are useful to
frontends beyond Textual. It is acceptable to stage over the current Python archive
index, but not to make the pane itself the domain boundary.

### Q13. What is the default grouping and ordering?

**Recommended: group by family/solo Sase Agent, order groups and children by newest
activity descending, and preserve alternative date/project/status/patch/tribe modes.**
An exact relation jump expands and selects its target regardless of current grouping.

### Q14. Does this need a feature flag?

**Recommended: yes, a disabled beta created with `sase flag new`.** Test both Off and On
states. Remove the Off branch only after exact link navigation, query correctness,
revival from both tabs, and measured large-corpus responsiveness are demonstrated.

---

## 10. Dependency-ordered implementation plan

### Phase 0 — Flag and executable contracts

1. Create the disabled beta flag through `sase flag new`.
2. Add contract tests for the descriptor, capabilities, query profile, stable target
   shapes, and Off/On behavior.
3. Add identity fixtures covering global/local solo, family, concrete member, alias,
   retry, workflow child, and missing member.

### Phase 1 — Core catalog and query profile

1. Define core catalog group/row wires and deterministic deduplication from artifact
   records plus dismissed summaries.
2. Expose cached full-history index queries without using source scans.
3. Add `agents_query_schema()` and the query-row adapter.
4. Add shared duration/comparison support, or the temporary shared-bound syntax plus
   legacy normalization.
5. Benchmark query index compilation/evaluation at representative 10k/30k+ corpora.

### Phase 2 — Read-only Artifacts pane

1. Register the fifth built-in descriptor/adapter/profile and compose the pane.
2. Implement cached/off-thread snapshots, bounded/virtualized rows, exact pending
   lookup, stable marks, grouping, status counters, and lazy details.
3. Implement global/local/member/family target resolution and native family/lineage
   relations.
4. Add query history, saved query, completion/facets, copy/open actions, and project
   scope through the shared host APIs.

At this point the pane is valuable even before revival, but remains beta.

### Phase 3 — Shared revival service

1. Extract the existing disk/index mutation order into a widget-free operation with a
   typed result delta.
2. Rewire the main Agents modal to it without changing the existing UX.
3. Add `R` routing, concrete and marked revival, family chooser rules, progress/error
   state, and catalog refresh to the new pane.
4. Test partial batch failure and cross-tab cache invalidation.

### Phase 4 — Artifact-link destination completion

1. Add the Agents known-target resolver to the artifact-link adapter.
2. Test inbound/outbound navigation for solo, family, member anchor, filtered old row,
   and cross-project global name.
3. Show current generic artifact-link relations in the rail with completeness
   diagnostics as appropriate.

This phase does not absorb the separate lossless/typed link-index project.

### Phase 5 — Rollout

1. Run unit, integration, TUI pilot, visual snapshot, and both-flag-state tests.
2. Measure cached activation, snapshot compile, interactive filtering, exact history
   lookup, and revival on the real corpus.
3. Opt in during beta, fix discovered identity/performance issues, then remove the flag
   through its removal bead when the qualitative gate is met.

---

## 11. Verification matrix

| Area | Required evidence |
| --- | --- |
| Contract | CLI pane inspection shows correct capabilities/profile; Off state has the old inventory |
| Query | Rust/Python profile parity corpus; Boolean precedence; typed duration/date; facets and canonicalization |
| Identity | local/global, solo/family/member, aliases, exact/pending target, stable marks across refresh |
| Catalog | active + completed + hidden + dismissed dedupe; no source scan; corrupt/missing archive diagnostics |
| Scale | representative 30k+ metadata corpus; bounded option count; stale query worker rejection |
| Detail | lazy hydration/cancellation; selection generation prevents late overwrite |
| Revival | single, marked batch, family chooser, workflow children, partial failure, index/bundle ordering |
| Regression | existing main Agents `R` modal and selection behavior remain intact |
| Relations | family/parent/retry edges; inbound/outbound artifact link; filtered/capped exact jump |
| Visual | narrow/wide layouts, group banners, status counters, empty/error/loading states |

Because this changes the TUI, implementation should run the project's normal `just
check` lane and the dedicated visual snapshot suite for intentional visual changes. A
full landing gate should follow the project's monitored `just check-full` policy.

---

## 12. Main risks and guardrails

| Risk | Guardrail |
| --- | --- |
| A family/member ref selects the wrong abstraction | Two-level model plus one canonical core resolver and explicit alias tests |
| New pane becomes a fork of main Agents | Share services and immutable records, not widgets or `AceApp` fields |
| Query dialects diverge permanently | New pane uses only compiled profile/Rust evaluation; main parser is compatibility debt |
| Complete history freezes the TUI | Index-only snapshot, worker compilation, bounded/virtualized presentation, lazy detail |
| Content search causes archive-wide I/O | Metadata-only v1; explicit FTS later |
| Revival mutates disk on the event loop | Shared tracked operation returning a typed delta |
| A filtered/capped row is not a valid link target | Exact indexed pending lookup independent of visible page |
| Link filters report false negatives | Defer completeness-sensitive fields until the link store/projection is fixed |
| Main `R` changes accidentally | Pane-aware routing plus regression tests on both tabs |
| Beta becomes permanent dead code | `sase flag new` removal bead and qualitative removal gate |

---

## Recommended solution

Implement **Artifacts → Agents** as the fifth built-in `ArtifactsPaneContract` adapter,
behind a disabled `artifacts_agents_pane` beta flag. Keep the main Agents tab as the live
control room and make the new pane the complete, query-first historical catalog.

Represent the catalog at two levels: selectable family/solo Sase Agent banners with
queryable concrete shell/run rows beneath them. Use globally qualified names as durable
artifact identities, retain run/bundle identity for revival, and resolve local names,
member names, and aliases through one Rust-owned canonical target resolver. An exact
artifact-link jump must be able to hydrate and select an old row even when normal
results are filtered or capped.

Build catalog snapshots only from the persistent agent artifact index, dismissed-bundle
summary index, and published sidecar metadata—never from a full source scan. Compile the
complete compact metadata corpus off-thread into the existing Rust query handle, render
only a bounded/virtualized result window, and lazy-load prompt/chat/reply/bundle detail.

Add a Boolean `agents_query_schema()` to the shared query-profile registry. Extend the
shared Rust query grammar with typed duration/comparison support so `age>2h` and
`runtime>=5m` become profile features rather than reasons to reuse the standalone
Python agent parser. Search metadata by default; add full content only when a persistent
FTS index exists. Reserve link-aware fields now but enable completeness-sensitive link
queries only after the separate artifact-link fixes.

Extract revival into one widget-free, off-thread operation that owns bundle restoration,
dismissed-state persistence, bundle cleanup, and artifact-index updates, and returns a
typed delta. Keep the existing main-tab `R` modal as a caller. In the new pane, `R`
revives selected or marked concrete rows; ambiguous family banners open the existing
chooser prefiltered to their revivable members.

Land in this order: **flag/contracts → core catalog and shared query profile → read-only
pane → shared revival → exact agent-link navigation → measured beta rollout**. This
delivers the missing artifact destination now, preserves the later artifact-link and
all-tab integration plans, and avoids creating a second Agents architecture that would
have to be dismantled as soon as those plans begin.
