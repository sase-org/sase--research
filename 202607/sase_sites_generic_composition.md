---
create_time: 2026-07-29
updated_time: 2026-07-29
status: research
---

# SASE Sites as a Generic Composition Graph

## Research question

Should SASE replace the proposed `project` and `custom` site kinds with one generic Site that can link to zero or more
other Sites and SASE artifacts? In that model, can the site for an enabled project be a structural hub that arranges
generated artifact-oriented Sites into tabs and other layout regions?

This report extends `202607/sase_sites_platform/sase_sites_platform.md`. It concentrates on the product ontology,
composition and API contract rather than re-evaluating that report's server, indexing, static-export, rendering and
deployment research from scratch.

## Executive conclusion

**Yes: SASE should have one Site primitive, not `project` and `custom` kinds.** The original report already says that
the project site is effectively “site zero” built with the same renderer and widget vocabulary as a custom site. The
kind field therefore records provenance—generated versus directly authored—not a meaningful difference in behavior.
Provenance belongs in an optional generator record, not in the site's type.

The stronger version of the proposal needs one important qualification:

> Make every meaningful artifact *presentable through the Site contract*, but do not create a durable Site record,
> version history and deployment lifecycle for every artifact instance.

The `sase` project alone has roughly 21,000 Markdown documents. Turning each plan, prompt, bead, agent and chat into a
persistent Site would reproduce the exhaustive artifact registry that SASE recently built and removed, multiply
version and access-policy state, and blur the boundary between content identity and presentation identity. Artifacts
already have the kind-tagged `ArtifactRef` grammar; a Site should reference those identities rather than replace them.

Use a hybrid model:

- Persist a Site when it has independent layout, curation, sharing, versioning or ownership.
- Generate ordinary, schema-conforming Site manifests for project hubs and artifact collections.
- Generate an artifact's standalone Site *view* on demand from its `ArtifactRef`; promote it to a persistent Site only
  when someone customizes, saves or deploys it.
- Let a hub structurally **mount** child Sites into ordered layout slots. Keep ordinary **links** and inline **embeds**
  separate because they have different rebuild, cycle and access-control semantics.

This produces one engine and one API without producing one stored object per document.

---

## 1. What changes from the original proposal

The original report's architecture remains largely sound:

- a Site is a projection, not a new source of truth;
- saved versions are immutable and source-locked;
- deployment selects a saved version and never builds;
- static export and the live gateway are two render targets for the same model;
- the existing gateway, artifact-reference grammar, query language and privacy controls should be reused;
- generated output is never hand-edited;
- agent prompts, chats and variables are excluded by default.

The change is smaller than it first appears. Replace:

```yaml
kind: project
```

or:

```yaml
kind: custom
```

with orthogonal facts:

```yaml
generator:                    # optional; absence means the spec is directly authored
  name: project-hub
  version: 1
subjects:
  - project: sase
renderer:
  mode: standard
```

A generated Site can have an authored overlay. An authored Site can later be captured as a template. A project hub can
contain a hand-authored introduction. None of those transitions should require changing the Site's kind or moving it
between product paths.

### Why the kinds are misleading

| Supposed distinction | Is it actually different? |
| --- | --- |
| Identity | No. Both need durable IDs, names and URLs. |
| Layout | No. Both need pages, tabs, grids, navigation and responsive rendering. |
| Content | No. Both project SASE artifacts, queries, Markdown and media. |
| Versioning | No. Both need immutable versions and source locks. |
| Access | No. Both must obey the most restrictive included source. |
| Serving/export | No. Both need live and static render targets. |
| API | No. Readers and writers should not branch on site kind. |
| Origin | Yes. One begins from a generator; one begins from an authored spec. |

Origin is metadata. It should not become a sum type that every CLI command, API endpoint, renderer and deployment
adapter must branch over.

---

## 2. A tighter ontology

The generic model becomes easier to reason about if five nouns are kept distinct.

| Noun | Meaning | Source of truth? |
| --- | --- | --- |
| **Artifact** | A plan, bead, agent, chat, commit, document or explicit file, identified by the existing kind-tagged artifact-reference grammar. | Yes, in its owning repository/store. |
| **Site** | A durable identity for a presentation and composition surface. | Its small `SiteSpec` is source; rendered output is derived. |
| **Site view** | A route/page within a Site, possibly generated on demand for one artifact. | No; a projection. |
| **Saved version** | An immutable resolution of a SiteSpec, artifact source locks and composed child Site versions. | Yes, for what was built. |
| **Deployment** | A pointer from an audience/URL to one saved version. | Yes, for what is published. |

A Site is therefore:

> A versionable presentation manifest over zero or more artifact resources and zero or more other Sites, with an
> ordered layout, an access policy and a declared capability surface.

It is specifically **not**:

- a synonym for an artifact;
- a container that takes ownership of linked artifacts or child Sites;
- a second knowledge graph;
- a database for copied SASE state;
- necessarily a whole web origin or independently deployed bundle.

### One Site, several independent axes

Instead of kinds, describe Sites along independent axes:

| Axis | Examples |
| --- | --- |
| Subject | none, `project:sase`, one `plans:…` ref, one bead, a set of refs |
| Generator | none, `project-hub@1`, `artifact-collection@1`, `artifact-detail@1` |
| Renderer | `standard`, later `bundle` |
| Persistence | virtual, persisted |
| Resolution | live draft, saved/pinned |
| Visibility | local, restricted bundle, public |
| Role | hub, section, dashboard, report, detail—descriptive labels or templates, not kinds |

This avoids false exclusivity. A Site can simultaneously be generated from a project, customized by a human, rendered
with the standard component library, mounted inside a larger organization hub and deployed publicly.

---

## 3. Do not persist one Site per artifact

There are three plausible granularities.

| Model | Benefits | Costs | Verdict |
| --- | --- | --- | --- |
| Persistent Site for every artifact instance | Perfect uniformity; every object gets a Site ID and history | More than 21,000 Site records for one project; duplicated identity; version fan-out; ACL drift; deletion/orphan questions; recreates an exhaustive registry | Reject |
| Persistent Site per artifact corpus | Small graph; Plans/Beads/Agents become independently reusable sections | Individual artifacts still need standalone links; corpus boundaries can be coarse | Adopt |
| Virtual Site view for each artifact, promoted on demand | Every artifact is renderable/shareable through the same contract without stored lifecycle state | Requires deterministic view generation and a promotion rule | Adopt |

The combined model is:

```text
Persistent project hub Site
├── mounts persistent/generated Plans collection Site
│   └── serves virtual view for each plans:<ref>
├── mounts persistent/generated Beads collection Site
│   └── serves virtual view for each bead ref
├── mounts persistent/generated Agents collection Site
│   └── serves virtual view for each agent ref
└── mounts one Site per configured document role
    └── serves virtual view for each document ArtifactRef
```

“Virtual” does not mean unstable. Its route and output are deterministic functions of:

```text
(generator version, canonical ArtifactRef, source lock, renderer version)
```

It simply means SASE does not allocate a second mutable identity and lifecycle record until one is needed.

### Promotion

An artifact view becomes a persisted Site when a user or agent:

- adds narrative or custom layout;
- links additional artifacts not derived by the standard generator;
- saves a version intended to outlive the containing collection;
- assigns independent access or ownership;
- deploys it independently.

Promotion copies the fully resolved generated spec into a new Site source plus a reference to its generator provenance.
It does not copy the artifact content. The artifact remains linked by its canonical `ArtifactRef`.

### Why this matches SASE's existing direction

The adjacent artifact-reference research found that SASE already built and deleted a unified artifact graph in a
24-hour experiment, then succeeded with a much smaller kind-tagged reference and resolver. Current Python wire models
already distinguish `commit`, `chat`, `bug`, `file` and role-parameterized `document` references, with fragments for
lines, pages and time. Sites should spend that identity system rather than create `site_<id>` wrappers for every
artifact.

Backstage's catalog guidance reaches the same boundary from a mature portal product: model the human mental model and
attach views to meaningful nodes, rather than trying to inventory every possible thing. It explicitly warns against
going too granular and treats the catalog as a projection/cache rather than the ultimate source of truth.

---

## 4. Separate relations, composition and layout

“Sites can link to Sites” is underspecified. A hyperlink, a tab mount and an inline embed have materially different
semantics.

### 4.1 Three operations

| Operation | User experience | Build dependency? | Pins target version? | Target contributes to parent access ceiling? | Cycles? |
| --- | --- | ---: | ---: | ---: | ---: |
| **Link** | Navigate to the target | No | No by default | No; target enforces its own access | Allowed |
| **Mount** | Child routes/views appear inside parent navigation or a layout region | Yes | Yes in a saved version | Yes | Rejected |
| **Embed** | A selected target view/resource renders inline | Yes | Yes in a saved version | Yes | Rejected |

This distinction should exist in the schema and validation rules, not just in the renderer.

RFC 8288's Web Linking model is useful discipline here: a link is a typed relationship between a context and a target;
the relationship does not determine the target's media type or presentation. SASE should likewise keep semantic
relations such as `related`, `subject`, `parent` and `source` separate from presentation choices such as “put this in a
tab.”

### 4.2 Semantic graph versus ordered layout tree

Use two structures:

1. **Relations** are an unordered graph and explain why resources are connected.
2. **Layout** is an ordered tree and explains where/how selected resources are presented.

The distinction prevents several mistakes:

- `rel: related` does not silently make a target a build dependency.
- Tab order is not smuggled into graph edge order.
- The same child can be linked semantically but mounted only once.
- A mobile renderer can turn desktop tabs into a navigation list without changing the SiteSpec.
- Machine readers can ignore layout and still understand relationships.

IIIF's Presentation API is a useful precedent: much of its composition model is an explicitly ordered `items` array,
while separate properties such as `partOf` and `seeAlso` carry containment and related-resource semantics. SASE does not
need JSON-LD, but it should copy that separation.

### 4.3 Hub behavior

A hub is not a Site kind. It is an ordinary Site whose layout mostly references mounted children.

```yaml
# Explanatory, not a final wire schema.
schema_version: 1
site_id: site_01K...
name: sase
title: SASE

subjects:
  - type: project
    project: sase

generator:
  name: project-hub
  version: 1

resources:
  plans:
    target:
      type: site
      site_id: site_plans_01K...
    relation: section
    resolution: active
  beads:
    target:
      type: site
      site_id: site_beads_01K...
    relation: section
    resolution: active
  architecture:
    target:
      type: artifact
      ref: research:202607/sase_sites_platform/sase_sites_platform.md
    relation: featured

layout:
  type: tabs
  items:
    - id: overview
      label: Overview
      view:
        type: local
        source: overview.md
    - id: plans
      label: Plans
      view:
        type: mount
        resource: plans
    - id: beads
      label: Beads
      view:
        type: mount
        resource: beads
    - id: architecture
      label: Architecture
      view:
        type: artifact
        resource: architecture

renderer:
  mode: standard

access:
  mode: owner_only
```

The generated Plans child is the same primitive:

```yaml
schema_version: 1
site_id: site_plans_01K...
name: sase-plans
title: Plans
subjects:
  - type: artifact_collection
    project: sase
    artifact_kind: plans
generator:
  name: artifact-collection
  version: 1
  options:
    group_by: month
    detail_generator: artifact-detail
renderer:
  mode: standard
```

Nothing in either manifest says `kind: project` or `kind: custom`.

### 4.4 Cycle and deletion rules

- The link graph may contain cycles; backlinks, `partOf` links and “return to project” naturally do.
- The mount/embed graph must be a DAG. Validate the transitive closure before save.
- Deleting a Site never deletes linked Sites or artifacts.
- A broken ordinary link yields a diagnostic and a disabled link.
- A broken mount/embed is a build error because the parent cannot be reproduced.
- Mounting one child twice is allowed only with distinct mount IDs and routes; otherwise reject ambiguous route
  ownership.

---

## 5. Generated bases plus authored overlays

The original “generated output is never hand-edited” rule should remain, but generic Sites need a supported way to
customize generated hubs.

Model each draft as:

```text
resolved draft = generator output + validated authored overlay
```

The overlay may:

- change labels, ordering and layout;
- hide generated sections;
- add narrative pages, links, mounts and embeds;
- change presentation options;
- narrow access.

The overlay may not:

- mutate an artifact's source data;
- replace the generated Site's durable ID;
- widen access beyond included content;
- inject executable HTML into the standard renderer;
- alter generator-owned resource identities in a way that makes future regeneration ambiguous.

This resolves an awkward gap in the original proposal. A fully generated project Site that cannot be curated will be
too rigid; a copied project template that stops receiving generator improvements will drift. Base-plus-overlay keeps
both determinism and customization.

The saved version stores:

- generator name and version;
- generator input/source lock;
- authored overlay digest;
- fully resolved manifest digest;
- renderer version;
- child Site version locks;
- artifact source locks and content digests.

That is enough to reproduce the output and explain every input.

---

## 6. Standard and custom HTML are renderer modes, not Site kinds

The original report recommends a declarative standard renderer and defers arbitrary static assets. That remains the
right default, but the generic model gives the escape hatch a cleaner home:

| Renderer | Meaning | Recommendation |
| --- | --- | --- |
| `standard` | SASE renders a fixed vocabulary of Markdown, tables, boards, timelines, graphs, galleries and artifact readers from the SiteSpec. | v1 |
| `bundle` | The Site supplies a custom HTML/CSS/JS bundle that consumes only declared resources and typed actions through a host bridge. | Later, sandboxed |

`bundle` is not a “custom Site.” A generated plan visualizer could use it, while a bespoke report could use the
standard renderer. The renderer and origin are independent.

### Custom bundle security contract

MCP Apps is now the strongest adjacent standard to learn from. Its official pattern is a predeclared `ui://` HTML
resource rendered in a sandboxed iframe, with bidirectional JSON-RPC over `postMessage`; UI-initiated actions are routed
through the host's tool/consent path. It is framework-neutral and supports bundled HTML/JavaScript plus explicit CSP and
permissions.

SASE should align with that shape instead of inventing an unrestricted mini hosting platform:

- predeclare the bundle and digest before rendering;
- render custom bundles in a sandbox when embedded in another Site;
- give the bundle no gateway bearer token, filesystem path or parent DOM access;
- expose reads and actions through a narrow message bridge;
- require every action to name a typed, schema-validated gateway operation;
- let the host enforce authorization, audit and confirmation;
- use an explicit CSP allowlist; default to no outbound network;
- keep public custom bundles disabled until the standard renderer, access closure and audit path are mature.

An eventual MCP Apps adapter could reuse the same bundle and bridge when a Site is rendered inside ChatGPT, Claude,
VS Code or another compatible host. The standalone SASE Site must remain usable without MCP, so MCP Apps should be an
adapter—not the Site's identity or only runtime.

---

## 7. Reader and writer contracts

The HTML is for humans. Agents should never have to scrape it, infer tab names or edit generated files. The Site
contract needs a machine surface from the first release.

### 7.1 Discovery

Every served or exported Site should expose:

- a fixed `manifest.json` with a versioned media type/schema;
- an HTTP `Link` relation and HTML `<link>` pointing to that manifest;
- the Site ID, selected version ID and canonical URL in both HTML and JSON;
- a capabilities document describing supported reads and actions;
- typed links to child Sites and artifact resources.

Use a SASE-defined extension relation for the manifest and document it. Do not overload a semantic relation such as
`related` with discovery behavior.

### 7.2 Minimum read API

The canonical gateway surface can be REST-shaped:

```text
GET  /api/v1/sites
GET  /api/v1/sites/{site_id}
GET  /api/v1/sites/{site_id}/manifest
GET  /api/v1/sites/{site_id}/versions/{version_id}/manifest
GET  /api/v1/sites/{site_id}/resources
GET  /api/v1/sites/{site_id}/resources/{resource_id}
POST /api/v1/sites/{site_id}/query
GET  /api/v1/sites/{site_id}/actions
```

Responses should carry canonical artifact refs, not host paths. Pagination, scope/exclusion diagnostics, source
provenance and access-derived omissions must be explicit.

### 7.3 Site-spec writes

Site authoring is different from mutating an artifact. The safe remote authoring loop is:

1. fetch the current draft spec and strong `ETag`;
2. submit a complete validated replacement or narrowly typed edit with `If-Match`;
3. receive a new draft revision and diagnostics;
4. explicitly save an immutable version;
5. separately request deployment.

RFC 9110 specifies `If-Match` precisely for preventing lost updates on state-changing requests. This matters because
several agents and a human may edit one hub concurrently. A failed precondition should return `412`; SASE should never
silently apply a stale patch.

Local agents can continue to use `sase site open` to edit the small source spec through the repository workflow. The
gateway authoring API must operate on the same logical spec and validation path, not on generated HTML.

### 7.4 Artifact writes and actions

A Site is not a generic write-through filesystem. Later interactive Sites may offer actions such as:

- update a bead status;
- add a bead note;
- approve a review item;
- create a plan or Site draft;
- start a typed SASE workflow.

Each action should be an existing or new **typed domain operation** with:

- a stable name;
- JSON Schema input and output;
- read-only/destructive/idempotent metadata;
- required authorization scope;
- confirmation policy;
- audit record;
- returned artifact refs.

The Site manifest only selects which permitted actions are exposed in that presentation. It does not define arbitrary
shell commands or file writes.

### 7.5 MCP adapter

The 2026-07-28 MCP specification maps cleanly onto this contract:

- Sites and artifacts become MCP **resources**, with URI identity, list/read, templates, caching and optional update
  subscriptions.
- Typed Site actions become MCP **tools**, with JSON Schema inputs/outputs and host-controlled consent.
- A custom HTML renderer can become an MCP Apps UI resource.

This is a valuable adapter for agent portability, but the Rust gateway/API remains canonical so all SASE runtimes and
non-MCP clients receive identical behavior. Avoid building a separate per-Site MCP server; one SASE server can expose
resources and actions across authorized Sites.

---

## 8. Composition-aware versioning

The original save/deploy split becomes even more important once Sites compose.

### Draft references can float; saved versions cannot

A source SiteSpec may say:

```yaml
resolution: active
```

for a child Site so a project hub follows the newest approved Plans Site during authoring. When saving a version, SASE
must resolve the complete mount/embed closure to:

```yaml
site_id: site_plans_01K...
version_id: version_01K...
manifest_digest: sha256:...
```

Similarly, artifact refs resolve to exact repository commits and content digests. The saved version records the
resolved dependency closure, not just the floating source expression.

OCI's image-index/descriptor model is a strong precedent: higher-level manifests point to nested manifests through
media type, byte size and content digest, allowing independent retrieval and verification. SASE does not need to adopt
the OCI wire format, but it should adopt the invariant: **composed immutable output names immutable child content.**

### Rebuild propagation

| Change | Ordinary linking parent rebuild? | Mounting/embedding parent rebuild? |
| --- | ---: | ---: |
| Child metadata/title | No; link can resolve live | Yes, if parent renders it |
| New child saved version | No | Draft becomes stale; no automatic deployment |
| Artifact content changes | No, unless link label is derived | Yes, new parent version required |
| Child access narrows | Link remains, target may deny | Parent deployment becomes invalid and must be diagnosed |
| Child deletion | Broken-link warning | Build/deployment error |

Never auto-deploy a parent because a child changed. Generate a draft version, show the dependency diff and notify the
owner—the same review boundary recommended in the original report.

### Search

A mounted child may contribute its search shard to the saved parent bundle. An ordinary linked Site does not.
Cross-project hubs can therefore ship initially as navigation-only composition without requiring a global index.
Federated search across independently authorized linked Sites can come later.

---

## 9. Access and trust across the graph

The original report identifies privacy as the sharpest risk. Composition introduces a precise place to enforce it.

### Access closure

For mount/embed dependencies:

```text
maximum parent audience ≤ intersection of all transitively included source audiences
```

For ordinary links, the target remains responsible for authorization and does not lower the parent's ceiling. This is
another reason link and mount cannot be one ambiguous operation.

Requirements:

- Evaluate the access ceiling over the fully resolved transitive mount/embed closure at save and deploy time.
- Record which dependency caused a ceiling reduction.
- Refuse a public parent that mounts a private child; offer “link instead,” “exclude,” or an explicit redacted
  projection.
- Do not leak a private child's title, thumbnail, counts or existence through a public parent unless that metadata is
  independently authorized.
- Re-check active deployments when a child or source access policy narrows.
- Preserve the original exclusion of agent prompts, chats and variables by default.
- Apply custom-bundle permissions and CSP per mounted bundle, not only at the root.
- Never transitively inherit actions. A parent explicitly re-exports each action it wants to expose.

### Trust boundaries

A linked Site may be local, another SASE project, an exported bundle or eventually remote. Treat its manifest and
annotations as untrusted until:

- schema validation succeeds;
- the declared digest matches;
- the signer/source policy is acceptable;
- access is authorized;
- custom UI requirements fit the host sandbox policy.

Navigation to an untrusted external Site is much cheaper than mounting it. The product should make that difference
visible.

---

## 10. Implications for the CLI and generated skill

The generic model simplifies the user-facing surface.

```text
sase site new <name>                      # blank or --template; no kind
sase site generate --subject <ref>        # preview a generated/virtual Site
sase site persist --subject <ref>         # promote a generated view
sase site link <site> <target>             # ordinary semantic link
sase site mount <site> <child>             # structural dependency + layout placement
sase site unmount <site> <mount-id>
sase site check [site]                     # schema, refs, cycles, access closure, drift
sase site build [site]
sase site save [site]
sase site deploy [site]
sase site open [site]
sase site show [site]
```

The final verbs should still be checked against the SASE CLI rules before implementation. The conceptual changes are:

- no `--kind project|custom`;
- templates such as `project-hub`, `dashboard`, `report` and `gallery` are starting points, not types;
- `--subject` accepts a project or canonical artifact ref;
- `show --json` reports origin/generator, subjects, mounted closure and access ceiling;
- `check` detects mount cycles and unresolved/policy-incompatible dependencies;
- deployment remains a separately confirmed action.

The `/sase_sites` skill should teach the difference between `link`, `mount` and `embed` before it teaches layout
widgets. That distinction is the most consequential authoring choice in the generic model.

---

## 11. What to retain, revise and drop

| Original proposal | Decision |
| --- | --- |
| `Site`, saved version and deployment as separate records | Retain |
| One rendering engine and widget vocabulary | Retain |
| Existing gateway, live/static render targets | Retain |
| Declarative standard renderer first | Retain |
| Exact source locks and content-addressed bundles | Retain |
| Project site generated for each enabled project | Retain, as a generic Site with `project-hub` generator |
| Project/custom kinds | Drop |
| Project site never hand-edited | Revise to generated base plus validated authored overlay |
| One tab per corpus | Revise to mounted generated collection Sites arranged by the hub layout |
| Detail page per artifact | Retain as a virtual Site view, not a persistent Site record |
| Custom raw/static kind | Replace with later `renderer.mode: bundle` |
| Per-project index | Retain; cross-project linking does not require a global index |
| Multi-project Sites deferred because URL scheme changes | Revise: navigation composition can work early; mounted/federated search can remain deferred |
| Site index as a new unified graph | Narrow: use indexes for search/projection, but do not make the Site catalog an exhaustive artifact registry |

---

## 12. Risks and tests that follow from the generic model

| Risk | Required test/control |
| --- | --- |
| Mount cycle | Graph validation with a human-readable cycle trace |
| Artifact mistakenly persisted as thousands of Sites | Corpus-scale fixture asserting virtual generation does not allocate Site records |
| Floating child makes saved output irreproducible | Saved manifest must contain only pinned mount/embed versions |
| Parent exposes private child metadata | Transitive access-closure and negative disclosure tests |
| Child policy narrows after parent deployment | Drift detector marks deployment invalid and notifies owner |
| Generator update destroys authored customization | Overlay conflict diagnostics; never silently discard fields |
| Duplicate child routes | Route ownership validation |
| Arbitrary UI bypasses gateway controls | Sandbox, CSP, bridge-only actions, no bearer token in iframe |
| Concurrent agent edits overwrite each other | Strong ETag + `If-Match` integration tests |
| Linked external Site disappears | Link diagnostic only; no cascade deletion |
| Mounted external Site disappears | Build/deployment failure with pinned last-good version still available |
| Search leaks linked-but-not-mounted content | Only mounted, authorized shards enter parent search |

---

## 13. Primary external evidence

- [Backstage: Creating the Catalog Graph](https://backstage.io/docs/features/software-catalog/creating-the-catalog-graph/)
  — capture meaningful mental models rather than an exhaustive inventory; keep source metadata in Git and treat the
  portal/catalog as a projection rather than the ultimate source of truth.
- [Backstage: Entity References](https://backstage.io/docs/features/software-catalog/references/) — use explicit,
  transportable references between independently owned entities.
- [RFC 8288: Web Linking](https://www.rfc-editor.org/rfc/rfc8288.html) — distinguish a typed relationship from the
  target representation and from serialization/presentation.
- [IIIF Presentation API 3.0](https://iiif.io/api/presentation/3.0/) — use an ordered structural collection for
  presentation while retaining separate linking properties.
- [OCI Image Index](https://specs.opencontainers.org/image-spec/image-index/) and
  [OCI Descriptor](https://specs.opencontainers.org/image-spec/descriptor/) — immutable higher-level manifests refer to
  independently retrievable child manifests through content digests and sizes.
- [RFC 9110: HTTP Semantics, `If-Match`](https://www.rfc-editor.org/rfc/rfc9110.html#name-if-match) — prevent lost
  updates during concurrent state-changing writes.
- [MCP 2026-07-28 Resources](https://modelcontextprotocol.io/specification/2026-07-28/server/resources) and
  [Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) — separate readable URI-addressed
  resources from schema-described executable actions.
- [MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview) — predeclared HTML UI resources, sandboxed
  iframe rendering and auditable JSON-RPC/tool calls through the host.

Relevant local evidence:

- `202607/sase_sites_platform/sase_sites_platform.md`
- `202607/artifact_refs_and_inspector/artifact_refs_and_inspector.md`
- `src/sase/artifact_ref_models.py`
- `src/sase/artifact_refs.py`
- `docs/query_language.md`
- `docs/mobile_gateway.md`
- `docs/agents_sidecar.md`

## Recommended approach

Adopt **one generic, versioned Site primitive** and remove `project`/`custom` from the core model. Represent origin with
an optional versioned generator and support a generated base plus authored overlay. Keep renderer choice independent:
ship the declarative `standard` renderer first and reserve a sandboxed, bridge-only `bundle` renderer for later.

Implement the project experience as composition:

1. Create one persistent generic hub Site for each enabled project.
2. Generate ordinary child Sites for meaningful artifact **collections**—Plans, Beads, Agents, configured document
   roles and other top-level corpora—and mount them into the hub's ordered layout.
3. Render individual artifacts as deterministic virtual Site views addressed by their existing `ArtifactRef`; persist
   one only when it gains independent curation, access, versioning or deployment.
4. Encode `link`, `mount` and `embed` as distinct operations. Permit cycles only for links; require the mount/embed graph
   to be a DAG.
5. Resolve every mount/embed and artifact input to immutable versions, commits and digests when saving. Deploy only a
   saved version, and never auto-deploy parents after child changes.
6. Make the Rust gateway/CLI contract canonical for human and agent readers/writers: manifests and resources for reads,
   typed schema-validated actions for mutations, ETag-guarded draft edits, and no generic file/shell write surface.
   Add MCP Resources/Tools/Apps as adapters over that contract.
7. Prototype the smallest vertical slice before the broader search/index program: a generated project hub mounting
   Plans and Beads collection Sites, one virtual artifact view, static export, source/child locks, cycle validation and
   transitive access-ceiling tests.

This preserves the user's central insight—project hubs, artifact surfaces and bespoke dashboards are all the same kind
of thing—while keeping artifact identity, Site identity and deployment identity cleanly separate.
