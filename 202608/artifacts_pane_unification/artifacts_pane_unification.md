---
create_time: 2026-08-14
updated_time: 2026-08-14
status: research
tags: [ace, artifacts, patches, queries, relations, contract, tui]
---

# Unifying ACE Artifacts: Query, Relationship, and Pane Contracts

**Research question:** how should ACE unify every Artifacts sub-tab—including Patches—
behind a contract that lets an artifact/sidecar repository describe its tab without
shipping ACE code, while preserving and generalizing Patch's query language, saved
queries, ancestry/children navigation, and other high-value behavior?

**Scope and evidence.** This is a follow-up to
[`artifacts_pane_contract.md`](../artifacts_pane_contract/artifacts_pane_contract.md).
That report was correct about the missing host/provider boundary but deliberately left
Patches outside the common browser; this report revises that conclusion. The source was
re-read at `sase` `e4baf07717`, `sase-core` `41701509f`, and
`sase-research-artifacts` `a7d9e0499`. The query grammar, Rust evaluator and graph
index, saved-query/history stores, all current Artifacts panes, provider schema, and the
research provider were inspected directly.

---

## Bottom line

Build **one behavioral contract with multiple adapters**, not one generic widget and
not a plugin callback API.

1. **Patches must be in the contract from the first migration.** It should be the
   richest built-in adapter and the conformance oracle for querying, relations, saved
   views, navigation, and details. It should not be forced through the generic document
   renderer, and its mutation workflow does not have to become available to arbitrary
   providers.
2. **Put data semantics in `sase-core`; keep presentation in ACE.** Stable artifact
   identity, typed values, query parsing/validation/evaluation, and relation indexing
   are cross-frontend behavior. Textual layout, keybindings, rows, detail renderers, and
   conditional hints are not.
3. **Let sidecars declare facts, not UI code.** A provider describes fields, identity,
   inventory, query facets, relationships, and small presentation hints. The host
   derives capabilities. No provider callback should run during rendering, navigation,
   completion, or query evaluation.
4. **Generalize Patch's query engine as a typed query profile.** Preserve Boolean
   expressions, parentheses, quoting, implicit `AND`, and typed field predicates. Move
   Patch-only field names and shorthands out of the parser and into a compiled profile.
   Replace the other panes' four small, incompatible token parsers with the same engine.
5. **Represent ancestry, children, families, and links as typed directed relations.**
   Providers declare how stored properties produce edges; the core derives inverse
   edges and indexes them. A host-owned relations panel and reveal operation then work
   everywhere.
6. **Namespace persisted query state by pane and query-profile digest.** Migrate the
   current Patch-only slots, history, and query-to-selection memory into the Patch
   namespace without deleting the legacy files until the new store is known good.

The durable abstraction is therefore three nested layers:

```text
sidecar provider declaration
        │ fields, relations, safe presentation hints
        ▼
sase-core browse contract
        │ typed snapshot + query profile + relation graph
        ▼
ACE ArtifactsPaneContract
        │ common shell + capabilities + pane session
        ▼
built-in or declarative adapter
        └─ Patch is rich; document providers get useful defaults for free
```

This design makes a new host feature broadly rewarding: add grouping, saved views,
relation breadcrumbs, or a new typed operator to the shared shell/core once, and every
compatible provider receives it without understanding Textual.

---

## 1. What changed since the prior report

The earlier report captured a moving target. Several visible defects have since been
fixed, while the architectural gap remains.

| Earlier finding | Current state | Consequence for this design |
| --- | --- | --- |
| Provider labels were mechanically pluralized (`Researchs`) | Fixed; labels are singular/humanized | Label is still a provider hint, not an identity |
| Dynamic tabs could disturb expected digit order | Fixed; Files is last and gets the highest positional digit | Digits should remain host-assigned, never provider-assigned |
| Some tabs lacked icons | Fixed | Icon remains a safe presentation hint |
| Split mode was pane-specific | Fixed; the Artifacts view now applies shared split modes | This is the first real piece of the common shell |
| Provider specs were carried but unused | Still true | The next contract must actually compile and consume them |
| Patches used a separate navigation model | Still explicit in code | This is now the central migration target |
| Patches should remain an exception | Superseded by the present requirement | Contract inclusion does not require identical rendering |

The current registry in `src/sase/ace/tui/artifact_tabs.py` can discover and describe a
tab. The view still switches on pane identity to construct separate classes, and
`ArtifactsView.entry_navigator()` explicitly rejects Patches with “Patches use the
existing Patch navigation model.” `ArtifactsPatchesPane` describes itself as the
existing Patch surface “hosted unchanged.” Twelve TUI files still contain explicit
`ref:` dispatch. The architecture is dynamic at registration and static everywhere
interesting.

The provider spec reaches `ArtifactsDocumentsPane`, but the pane merely stores it. No
query, list, detail, footer, action, or navigation behavior is derived from it. This is
the seam the new design should turn into a real contract.

---

## 2. Current models and the useful parts to preserve

### 2.1 There are five browser implementations, not one

The current Artifacts widget package is over 13,000 lines. Most behavior is concentrated
in four parallel implementations—Beads, document/Plan-like entries, Files, and
Stitches—plus a separate Patch action/query stack. Each has its own filter model, row
identity assumptions, detail scheduling, action availability, and footer wiring.

The non-Patch panes do share an `ArtifactEntryNavigator` protocol, but it is too narrow
to be the final contract: its targets are pane-specific, it does not model queries or
relationships, and Patch is intentionally excluded. It is a useful compatibility
surface while migrating, not the domain boundary.

### 2.2 Patch search is a language; the others are token filters

Patch search currently has the strongest semantics:

- bare and quoted full-text terms, including case-sensitive quoted terms;
- `AND`, `OR`, `NOT`/`!`, parentheses, and implicit `AND`;
- named fields such as `status:`, `project:`, `ancestor:`, `name:`, `sibling:`, and
  `origin:`;
- compact aliases such as `+`, `^`, `~`, `&`, and `%` status forms;
- operational predicates for errors and running agents/procs;
- a real AST and a Rust-backed evaluator.

By contrast, Beads, Plans/documents, Stitches, and Files each wrap the generic
`filter_tokens.py` tokenizer with a pane-local field list and matcher. Those languages
support useful quoting, negation, and `key:value` tokens, but not Boolean grouping, and
their field definitions/completions are repeated in Python.

The Patch implementation already has the right *shape*—tokenize, parse to AST, validate,
evaluate against a corpus—but not the right domain boundary. In `sase-core`, the valid
field list, status forms, shorthand tokens, corpus, searchable text, and matchers all
know about Patches. Generalization should preserve the grammar architecture while
replacing those Patch assumptions with a compiled query profile and generic typed rows.

### 2.3 Patch relations are excellent UX over Patch-specific graph data

`PatchGraphIndex` builds parent/child and family indexes. The
`AncestorsChildrenPanel` renders those indexes, while `<`, `>`, and `~` navigate
ancestors, descendants/children, and the Patch “sibling” family. If a target is hidden
by the current filter, Patch navigation rewrites the query to reveal it.

Two details matter for a general contract:

1. Patch “siblings” are not graph siblings. They are a family based on a normalized
   Patch base name, including reverted variants. This is an equivalence relation, while
   parent/child is a directed hierarchy.
2. The visible panel is presentation. The reusable domain objects are stable artifact
   identities and typed edges. Other providers may have parents, versions, generated-by
   links, related research, owning Beads, or cross-kind references.

The generic model therefore needs both **hierarchies** and **families**, plus ordinary
typed links. Treating every relationship as a parent pointer would lose Patch semantics
and make future cross-pane navigation awkward.

### 2.4 Saved queries are useful but globally Patch-shaped

The current stores are independent global JSON files:

- ten numeric saved-query slots;
- previous/next query history (bounded to 50);
- canonical-query → selected Patch memory (bounded to 200).

The UI reinforces that ownership: invoking a saved slot from another Artifacts tab
switches to Patches, and the saved-query picker is Patch-only. This behavior should be
migrated, not reproduced. Persistence needs pane, profile, and stable selection identity
so two providers can use slot `1` without colliding and so a provider schema update can
be diagnosed.

### 2.5 Current provider values are not typed enough

The provider schema declares property types (`string`, `enum`, `boolean`, `integer`,
`number`, `date`, `datetime`, and `string_list`), but `ArtifactEntryWire.properties` and
the Python `ArtifactEntry.properties` flatten every value to `string`. The research
provider already declares useful `status`, `tags`, `create_time`, and `updated_time`
properties, but their types are lost before a general query/sort/facet engine could use
them.

Stable identity is in better shape. A resolved Patch already receives a stable id like
`patch:{project}/{name}`, a ref kind, canonical argument, display label, project, and
properties. The contract should extract and reuse that identity rather than inventing a
second row id.

---

## 3. Recommended contract boundaries

### 3.1 Core: a typed browse snapshot

Add a reusable wire model in `sase-core`, shared by built-ins and declarative providers:

```rust
struct ArtifactIdentityWire {
    stable_id: String,
    ref_kind: String,
    canonical_argument: String,
    display_label: String,
    project: Option<String>,
    repository: Option<String>,
    path: Option<String>,
    revision: Option<String>,
}

enum ArtifactValueWire {
    String(String),
    Enum(String),
    Boolean(bool),
    Integer(i64),
    Number(f64),
    Date(String),
    DateTime(String),
    StringList(Vec<String>),
    ArtifactRef(ArtifactTargetWire),
    ArtifactRefList(Vec<ArtifactTargetWire>),
}

struct ArtifactTargetWire {
    stable_id: Option<String>,
    ref_kind: String,
    canonical_argument: String,
    display_label: Option<String>,
}

struct ArtifactBrowseEntryWire {
    identity: ArtifactIdentityWire,
    values: BTreeMap<String, ArtifactValueWire>,
    relations: Vec<ArtifactRelationWire>,
    diagnostics: Vec<ArtifactDiagnosticWire>,
}

struct ArtifactBrowseSnapshotWire {
    generation: String,
    entries: Vec<ArtifactBrowseEntryWire>,
    query_profile: ArtifactQueryProfileWire,
    relation_profile: ArtifactRelationProfileWire,
}
```

The exact serialization is an implementation detail; the important decisions are:

- `stable_id` is the selection/mark/navigation key;
- display labels are never identity;
- typed values remain typed through the wire;
- a snapshot has a generation token, so caches and async results can be rejected after
  data changes;
- provider-originated diagnostics travel with the snapshot rather than causing a tab to
  silently disappear.

`origin` in today's `ArtifactEntryWire` means prompt-ref/agent-artifact provenance. It
should remain optional provenance, not become the universal discriminator for browser
rows.

### 3.2 Core: a compiled query profile, not provider executable code

Refactor the Patch parser into three stages:

1. **Syntax parser:** produces a domain-neutral Boolean AST.
2. **Profile validator/coercer:** resolves field names and aliases, checks operators,
   converts literals to typed values, and reports source-span diagnostics.
3. **Generic evaluator:** evaluates the typed AST against an
   `ArtifactBrowseSnapshotWire` and optional host enrichments.

Conceptually:

```text
Expr := And(Expr...) | Or(Expr...) | Not(Expr) | Predicate
Predicate := Text(value, case_sensitive)
           | Field(field_id, operator, typed_value)
           | HostPredicate(predicate_id)
```

Every profile gets host fields such as `id`/`ref`, `name`/`title`, `kind`, `project`,
`repo`, and `path` when those values exist. Provider properties extend the profile.
Types determine the safe default operators:

| Type | Default operators |
| --- | --- |
| string / enum / artifact ref | equality, inequality, contains where sensible |
| boolean | equality and existence |
| integer / number | equality and ordered comparisons |
| date / datetime | equality and ordered comparisons |
| list | contains-any initially; contains-all can be added without syntax changes |

Keep Patch's user-facing language compatible, while accepting the useful forms from
the current token-filter panes during their migration:

- whitespace remains implicit `AND`;
- `AND`, `OR`, `NOT`, `!`, and parentheses keep their current meaning;
- quoted and case-sensitive text remain available;
- `field:value1,value2` is accepted as compatibility sugar for
  `field:value1 OR field:value2` where an existing pane supports comma lists;
- `-field:value` is accepted as compatibility sugar for `NOT field:value` where an
  existing pane supports token negation;
- typed comparisons such as `updated>=2026-08-01` become possible.

Shorthands should be a **closed, host-validated vocabulary**, not arbitrary punctuation
owned by providers. `&` can mean exact identity, `+` project, `^` the pane's declared
hierarchy, and `~` its declared family. Patch's `%` status aliases and operational
tokens can start as a legacy Patch macro set. If error/agent/proc state is later exposed
as standard host enrichment, those predicates become useful across every pane without
provider changes.

This resembles Kubernetes field selectors in one valuable respect: fields supported by
a resource kind are explicit, and an unsupported field is an error rather than a
silent no-op. Kubernetes also allows custom resource definitions to declare selectable
fields. See the official [field selector documentation](https://kubernetes.io/docs/concepts/overview/working-with-objects/field-selectors/)
and [CRD API](https://kubernetes.io/docs/reference/kubernetes-api/apiextensions/custom-resource-definition-v1/).
Typed field mappings are also the foundation of Elasticsearch's query behavior; see
its [field data types](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/field-data-types)
and [Boolean query](https://www.elastic.co/docs/reference/query-languages/query-dsl/query-dsl-bool-query).

### 3.3 Core: normalized directed relations

Use one edge shape and a small closed topology vocabulary:

```rust
struct ArtifactRelationWire {
    relation_id: String,
    source: ArtifactIdentityWire,
    target: ArtifactTargetWire,
}

enum RelationTopology {
    Hierarchy,
    Family,
    Link,
}
```

A relation profile supplies labels, source property, target kind, directionality, and
whether transitive traversal is meaningful. The core validates targets, builds forward
and inverse indexes once per snapshot, and detects hierarchy cycles. Missing targets
remain representable as dangling links with a diagnostic; they should not invalidate
the entire pane.

The three useful primitives are:

- **Hierarchy:** one or more parent refs; the host derives children and supports
  ancestors/descendants.
- **Family:** an explicit grouping key; Patch's adapter supplies its normalized base
  name. Declarative providers must store or extract a field—no arbitrary normalization
  callback runs in ACE.
- **Link:** a typed edge to the same or another artifact kind, such as “produced by,”
  “owns,” “documents,” or “related to.”

This follows a proven catalog pattern: Backstage models relations as directed,
typed source/target edges, commonly with inverse pairs such as parent/child, and treats
relations as deduced output rather than author-written UI state. See its
[well-known relations](https://backstage.io/docs/features/software-catalog/well-known-relations/),
[descriptor format](https://backstage.io/docs/next/features/software-catalog/descriptor-format/),
and [custom relation guidance](https://backstage.io/docs/features/software-catalog/extending-the-model/).

### 3.4 ACE: one pane contract and common shell

The Python presentation boundary should be a host-owned immutable contract. Names are
illustrative:

```python
@dataclass(frozen=True)
class ArtifactsPaneContract:
    pane_id: str
    label: str
    icon: str
    accent_token: str
    source: ArtifactBrowseSource
    query_profile: ArtifactQueryProfile
    relation_profile: ArtifactRelationProfile
    capabilities: frozenset[PaneCapability]
    row_renderer: ArtifactRowRenderer
    detail_renderer: ArtifactDetailRenderer
    action_provider: ArtifactActionProvider | None
```

The shared shell owns:

- loading, empty, stale, and diagnostic states;
- query input, validation, completion, history, and saved views;
- list selection, marks, copy reference, and stable reveal;
- split modes and detail scheduling;
- optional relation rail/panel and relation breadcrumbs;
- grouping/folding/sorting when enabled;
- conditional footer, help, and command-palette contributions.

Adapters own only what genuinely varies:

- acquiring/building the snapshot;
- row and detail presentation;
- built-in trusted mutation actions;
- optional domain-specific status summaries.

This is analogous to VS Code's Tree View boundary: the host owns the view while a data
provider supplies items and children, and commands are contributed separately. See the
official [Tree View API guide](https://code.visualstudio.com/api/extension-guides/tree-view).
SASE should be more declarative than that API for repository-provided panes, because a
repo configuration is portable data rather than trusted installed extension code.

### 3.5 Capabilities are mostly derived, not requested

Use a closed `PaneCapability` enum so every downstream surface asks the contract instead
of testing pane ids. Likely values include:

```text
FILTER  SAVED_VIEWS  QUERY_HISTORY  MARK  COPY_REFERENCE
OPEN_SOURCE  OPEN_EXTERNAL  OPEN_AGENT  VERSIONS
RELATIONS  HIERARCHY  FAMILY  GROUP  FOLD  SORT
TRUSTED_MUTATION
```

Providers should declare data facts; the host derives most capabilities:

- an inventory plus fields implies filter/history/saved views;
- a hierarchy relation implies hierarchy navigation and its `<`/`>` hints;
- a family relation implies `~` navigation;
- stable refs imply copy-reference;
- revision metadata implies versions;
- only built-in/trusted adapters can expose mutation.

This avoids “boolean soup” in provider YAML and prevents a provider from claiming a
feature its data cannot support. It also means a new host capability can activate for
all old providers when their existing data satisfies it.

### 3.6 Stable reveal is the universal navigation primitive

Replace index/name tuples with a target containing pane and stable identity:

```python
ArtifactEntryTarget(pane_id: str, stable_id: str)
```

The shell operation `reveal(target)` should:

1. select it immediately if it is visible;
2. if hidden, preserve the current saved/view state and apply a temporary identity lens;
3. switch panes and request/load the target for a cross-pane relation;
4. render a missing-target diagnostic rather than losing the current selection.

Patch currently changes the user's query to reveal a filtered relation target. Preserve
that behavior behind a compatibility adapter initially, then move to the temporary lens
so jumping through a graph does not destructively rewrite a carefully composed query.

---

## 4. The declarative provider surface

Extend the existing ref provider schema rather than inventing a second sidecar config.
The existing `ref` block already owns kind, icon, identity, inventory, properties,
detail, and publication. Add query, relation, and pane hints to that same compiled spec.

A future research provider could look like this (illustrative, not final syntax):

```yaml
schema_version: 2
provider: research

ref:
  kind: research
  icon: "∴"
  identity:
    path_template: "{path}"

  inventory:
    globs: ["20*/**/*.md"]

  properties:
    status:
      type: enum
      values: [draft, research, final]
      source: markdown_frontmatter
      query:
        facet: true
    tags:
      type: string_list
      source: markdown_frontmatter
      query:
        searchable: true
        facet: true
    updated_time:
      type: datetime
      source: markdown_frontmatter
    parent:
      type: artifact_ref
      source: markdown_frontmatter
    series:
      type: string
      source: markdown_frontmatter
    related:
      type: artifact_ref_list
      source: markdown_frontmatter

  query:
    default_search: [title, tags, body]
    primary_time: updated_time
    default: ""

  relationships:
    - id: lineage
      topology: hierarchy
      from_property: parent
      target_kind: research
      outbound_label: Ancestors
      inbound_label: Children
    - id: variants
      topology: family
      group_by_property: series
      label: Related versions
    - id: related
      topology: link
      from_property: related
      outbound_label: Related

  pane:
    label: Research
    description: Research reports
    default_sort: [updated_time, desc]
    row:
      title: title
      badges: [status]
      secondary: [updated_time, tags]
    detail:
      fields: [status, create_time, updated_time, tags]
```

Important constraints:

- Properties and relations refer only to validated extractors and fields.
- `pane` contains semantic roles, never Textual selectors, arbitrary colors, raw Rich
  markup, keybindings, shell commands, Python entry points, or callbacks.
- Providers do not allocate digit shortcuts; the host assigns them from visual order.
- Unknown optional hints fall back to host defaults. Unknown required schema constructs
  produce a visible disabled/diagnostic pane instead of disappearing.
- A provider with only today's v1 fields still gets a standard query over identity and
  declared properties, saved views, stable navigation, marks, copy, and common chrome.

The final point is the leverage goal: most new shared behavior should require no provider
schema change at all.

---

## 5. Saved queries should become pane-scoped saved views

Keep “saved query” as the initial UI language, but use a slightly broader versioned
record so sorting/grouping can be saved later without another migration:

```json
{
  "version": 1,
  "pane_id": "patches",
  "profile_id": "builtin.patch.v1",
  "profile_digest": "...",
  "slot": 1,
  "query_source": "status:ready OR status:wip",
  "query_canonical": "...",
  "sort": null,
  "group": null,
  "scope": null
}
```

Rules:

- Numeric slots are local to the active pane. `01` on Research must not jump to
  Patches. A global picker can expose all panes' saved views.
- History is keyed by `pane_id`; query-to-selection memory is keyed by
  `(pane_id, query_canonical)` and stores `stable_id`, not a Patch name or row index.
- Store both source text and canonical form. Source preserves user intent/editability;
  canonical form supports deduplication and selection memory.
- Record the query profile id and digest. On mismatch, recompile from source. If it no
  longer validates, keep it visible with a diagnostic and an edit/delete path—never
  silently discard it.
- Use atomic replace and a schema version for the new store.

Migration should import every current saved query, history entry, and selection mapping
under `pane_id="patches"` and the legacy Patch profile. Do not delete or overwrite the
legacy files until the new store has been successfully written and re-read. A rollback
release should still be able to use the old data.

---

## 6. How Patch fits without losing its personality

Unification means shared contracts and interaction grammar, not identical rows.

| Patch feature today | General contract form | Patch adapter behavior |
| --- | --- | --- |
| Boolean query language | Typed query profile + generic AST/evaluator | Exact syntax/semantic compatibility fixture |
| `%`, `!!!`, `@@@`, `$$$` shorthands | Host-validated macro/profile entries | Keep as legacy profile macros initially |
| saved slots/history | Pane-scoped saved views/history | Import existing stores into Patch namespace |
| query remembers selection | Stable-id selection memory | Store existing `patch:{project}/{name}` id |
| Ancestors/Children panel | Generic relation panel | Hierarchy from Patch parent edges |
| sibling jumper | Family relation | Family key from Patch base-name normalizer |
| `<`, `>`, `~` | Capability-derived relation actions | Same keys and adaptive hints |
| Patch list and rich detail | Adapter row/detail renderers | Preserve information density and actions |
| lifecycle mutations | Trusted action provider | Remains Patch-only/built-in |
| global app state/mixins | Pane session/controller | Compatibility forwards during migration |

The common shell should make Patch *look* like the other tabs in framing, header/query
placement, split behavior, selection, status/diagnostics, footer grammar, help, and
empty/loading states. Its row renderer, detail content, relation richness, and mutation
commands may remain specialized.

Patch must be the first adapter exercised against the query and relation contracts.
Migrating generic document panes first would allow an abstraction that handles only easy
lists and then breaks when Patch arrives. Patch is the design stress test.

---

## 7. Performance and responsiveness requirements

The contract must make the fast path obvious and the slow path impossible to invoke by
accident.

- Build typed values, searchable text, completions, and relation indexes once per
  snapshot, off the Textual event loop.
- Cache compiled query profiles by provider/profile digest.
- Cache query results by `(pane_id, snapshot_generation, profile_digest,
  canonical_query)`.
- Query edits and completion may inspect only bounded in-memory data. They must never
  resolve providers, glob files, call Git, parse Markdown, or stat the filesystem per
  keystroke.
- Selection movement is O(1) against the visible result vector. Detail loading remains
  debounced/cancellable, and async completion rechecks pane, generation, and stable id
  before applying results.
- Cached snapshots render immediately; refresh is coalesced in the background. A stale
  badge is preferable to a frozen UI.
- The existing TUI performance target—ordinary `j`/`k` p95 under 16 ms—should become a
  conformance benchmark for every adapter.

Provider declarations also improve performance predictability: they can be validated
and compiled at discovery, whereas arbitrary callbacks make it impossible for the host
to know which UI path may block.

---

## 8. Failure, security, and compatibility policy

### Failure isolation

One invalid provider must not prevent built-in tabs or other providers from loading.
However, broad exception handling should not make it vanish without explanation. Keep
its descriptor and render a disabled pane or diagnostics row containing the provider
kind, config source, and validation problem. Log the full exception separately.

During refresh, keep the last valid snapshot with a visible stale/error state. Replace
it only after a complete new snapshot validates. Relation errors should degrade the
affected relation, not the entire collection.

### Trust boundary

A repository-controlled spec is data, not trusted code. The portable contract must not
allow:

- command strings or shell interpolation;
- importable callbacks or widget classes;
- network requests on query/navigation paths;
- arbitrary Rich/Textual markup or CSS selectors;
- provider-selected keybindings;
- unbounded filesystem traversal outside declared roots.

If a future installed plugin needs executable actions, expose those through a separate,
explicitly trusted registration interface that returns host-validated action
descriptors. Do not put that power in sidecar YAML.

### Schema rollout

Use a coordinated provider schema v2. The current Rust validator owns the authoritative
provider digest, and fields unknown to that core cannot safely participate in cache
identity. A presentation-only digest computed in Python would be acceptable for pane
hints, but query types and relations affect cross-frontend semantics and belong in the
core digest.

Recommended rollout:

1. Release `sase-core` support for the typed browse wire and v2 query/relation schema,
   temporarily accepting v1 and v2.
2. Raise SASE's minimum core version and add Python adapters.
3. Keep compiling v1 providers to a default profile; enable v2 declarations where
   present.
4. Upgrade `sase-research-artifacts` to v2 as the first third-party-style conformance
   fixture.
5. Deprecate—not immediately remove—the pane-local token parsers and legacy saved-query
   files.

---

## 9. Implementation sequence

### Phase 0 — Specify behavior and lock compatibility

- Write the versioned wire/profile types and `PaneCapability` vocabulary.
- Create golden query fixtures from the Patch documentation and current evaluator,
  including precedence, quoting, shorthands, invalid queries, and selection results.
- Create relation fixtures for parent chains, cycles, missing parents, families, and
  cross-kind links.
- Capture existing saved-query/history files as migration fixtures.
- Add an Artifacts conformance harness that any pane adapter can run.

**Exit condition:** the contract is executable in tests, not only a protocol sketch.

### Phase 1 — Generalize the Rust domain engine

- Extract stable artifact identity from the existing `ArtifactEntryWire`.
- Add typed values and generic browse snapshots.
- Split Patch query syntax from Patch field/profile semantics.
- Implement profile validation, typed coercion, generic evaluation, and relation index.
- Adapt the Patch corpus/graph to the new engine while keeping the current UI.

**Exit condition:** current Patch query and graph fixtures pass through the generic core
with no user-visible change.

### Phase 2 — Introduce pane session and persistence

- Add a pane-owned controller/session for snapshot, query, selection, marks, split,
  relation focus, and history.
- Add pane-scoped saved views/history/selection memory and legacy Patch migration.
- Implement stable `reveal()` and the compatibility form of current Patch navigation.
- Temporarily forward old `AceApp` Patch properties/actions to the pane session.

**Exit condition:** Patch no longer requires globally unique query state, and saved
queries are losslessly migrated.

### Phase 3 — Put Patch inside the common shell

- Make `PatchBrowseAdapter` provide the generic snapshot/profile/relations.
- Move header, query/status, loading/empty/error, split, selection, marks, copy, footer,
  help, and relation framing to the shell.
- Keep Patch row/detail renderers and trusted lifecycle actions.
- Replace query-destructive relation jumps with the temporary reveal lens after parity
  is proven.

**Exit condition:** there is no Patch exclusion in `entry_navigator()` and no
“existing Patch surface hosted unchanged” wrapper, while all Patch interaction fixtures
remain green.

### Phase 4 — Migrate remaining built-ins

- Add adapters for Stitches, Beads, Files, and the built-in document/Plan provider.
- Delete pane-local filter languages only after their old syntax is accepted by the
  generic profile or explicitly migrated.
- Replace `ref:`/pane-id switches in actions, help, footer, marks, clipboard, and command
  availability with contract/capability lookups.

**Exit condition:** adding a built-in pane requires an adapter, not edits across the TUI.

### Phase 5 — Activate provider schema v2

- Compile declarative providers into the same document adapter.
- Upgrade the research provider and prove typed status/tag/time queries plus any real
  research relations.
- Test an unknown synthetic provider with no SASE-specific Python code.
- Document compatibility, defaults, diagnostics, and schema evolution.

**Exit condition:** a sidecar author can add a useful tab with YAML alone, and a new
shared shell feature appears in that tab without a provider release.

### Phase 6 — Remove compatibility scaffolding

- Remove legacy Patch globals/mixins and saved-query readers after a measured deprecation
  window.
- Remove old pane-specific navigation/filter protocols and residual pane-id dispatch.
- Keep permanent query syntax aliases where user-authored saved data depends on them.

---

## 10. Decisions to make before implementation

The architecture above narrows the remaining choices. These should be decided in the
Phase 0 design record:

1. **Saved slot UX:** pane-local digits are recommended. Decide whether the global picker
   shows all panes by default or opens scoped to the active pane.
2. **Reveal UX:** a temporary identity lens with an obvious “return to query” affordance
   is recommended over rewriting the query.
3. **List matching semantics:** begin with contains-any for list fields; defer an
   explicit contains-all operator until a real use case appears.
4. **Cross-pane relations:** allow them in the wire immediately, even if the first UI
   only opens them. Retrofitting pane identity into relation targets later is expensive.
5. **Provider macros:** do not allow arbitrary punctuation. Start with host-defined
   aliases and Patch compatibility macros; expand only with collision rules and a clear
   discoverability story.
6. **Trusted custom actions:** keep them out of portable repository config. Revisit only
   as a separate installed-plugin contract.

None of these choices changes the main recommendation: typed core semantics,
declarative provider facts, one ACE shell, adapter-specific rendering, and Patch as the
first full-fidelity client.

---

## 11. Rejected alternatives

### Keep Patch permanently exempt

This preserves today's features cheaply but guarantees two navigation, query,
persistence, footer, help, and action-availability systems. Every future cross-pane
feature would either exclude the most capable pane or be implemented twice. It also
removes the best stress test from the contract.

### Force every pane through the current document/Plan widget

This optimizes for class-count rather than behavior. Patch mutation and graph UX, File
versions, Bead hierarchy, and Stitch-specific detail would turn the generic widget into
a set of pane-id conditionals. Shared shell plus specialized renderers is the smaller
abstraction over time.

### Let providers ship Textual widgets or Python callbacks

This gives maximum flexibility but forfeits portability, security, performance
guarantees, compatibility, and the “one implementation benefits everyone” goal. It
also makes host keymap/help consistency unenforceable.

### Keep provider values as strings and let each pane interpret them

That recreates today's duplicated matchers and makes numeric/date sorting and validation
inconsistent. Types must survive the wire if the query engine is truly shared.

### Save raw query strings without profile identity

This works until a provider renames a field or changes a type. Silent reinterpretation
is worse than a visible invalid saved view. Source + canonical form + profile digest is
the minimum durable record.

---

## 12. Recommended end state

The most useful test of the design is what happens when a new shared feature lands.
Suppose ACE adds “group results by any facet, remember folded groups in a saved view.”
In the recommended architecture:

1. `sase-core` exposes which typed fields are facets and groups a result set.
2. The common shell renders groups and persists fold state.
3. Patch can group by status/project; Research can group by status/tag; an unknown
   user's sidecar can group by its declared enum/list fields.
4. No provider code changes, no new pane-id branches, and no duplicated keybinding/help
   work are required.

That is the contract worth building. Patches belongs inside it precisely because its
query and relation features define the bar the other tabs should inherit—not because
all panes must look identical internally.
