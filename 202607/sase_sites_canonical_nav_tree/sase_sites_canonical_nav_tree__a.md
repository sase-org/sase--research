---
create_time: 2026-07-30
updated_time: 2026-07-30
status: research
---

# SASE Sites: A Rooted Page Tree Over a Linked Knowledge Graph

## Research question

Should SASE formalize “few sites, many pages” with a Zettelkasten-inspired rule that every page except one root has
exactly one parent, every parent chain reaches that root, and the root can serve as the user's main SASE index site?
Can pages and sites still link to one another arbitrarily, and what should ancestry mean for composition, publication,
and access?

## Prior research reviewed

This report starts from, rather than repeats, the two consolidated SASE Sites reports produced on 2026-07-29:

- `sase_sites_platform/sase_sites_platform.md` established the platform direction: extend `sase_gateway`, build
  retrieval in the Rust core, use deterministic rendering and commit-pinned versions, keep explicit publication scope,
  and treat privacy as a first-order constraint.
- `sase_sites_hub_and_pages/sase_sites_hub_and_pages.md` refined the ontology: one site type; sites are few and pages
  are many; source identity is an artifact reference; a site is a layout and publication envelope; and links must not
  silently enlarge publication scope.

The second report already separated semantic relations from the ordered layout tree inside one site. The new question
is broader: whether *all* pages should also participate in one canonical navigation tree whose root is a generated
personal index site.

Research focused on four points that the prior reports did not settle:

1. what Luhmann's Zettelkasten did and did not make hierarchical;
2. whether a single-parent path materially improves web navigation;
3. how to retain polyhierarchical and cross-cutting knowledge without multiple canonical parents; and
4. whether one global root conflicts with explicit site scope, privacy, and independent publication.

## Executive conclusion

**Pursue the idea, but formalize it as a canonical navigation tree over an arbitrary relationship graph—not as a
semantic taxonomy and not as the publication model.**

The useful Zettelkasten analogy is that each note has one stable place while references connect it to as many other
contexts as necessary. Luhmann deliberately rejected a subject outline for the whole collection. He used fixed
addresses, arbitrary branching, a keyword register, and extensive cross-references; he described the resulting whole as
neither hierarchical nor linear. The SASE equivalent should therefore be:

- one **canonical navigation parent** per page, except for one distinguished root;
- stable page identity independent of the parent and URL path;
- any number of typed semantic, authored, and mention links;
- one generated root page that is the landing page of the user's main SASE site;
- secondary sites anchored at ordinary landing pages within that tree; and
- site membership and access computed from explicit scope and audience rules, never from parentage or arbitrary link
  reachability.

In graph terms, SASE should maintain a rooted spanning tree for orientation and a richer directed multigraph for
meaning. This is a strong fit for “few sites, many pages.” It gives every page a home and every user a dependable way
back to the main index without pretending that knowledge itself has only one hierarchy.

## 1. What “Zettelkasten-inspired” should mean

### 1.1 The part worth borrowing: one placement, many references

In *Communicating with Slip Boxes*, Luhmann distinguishes fixed placement from content classification. Every slip gets
a permanent number and therefore a stable address. The numbering permits arbitrary branches at any insertion point,
while fixed addresses permit any number of references and backlinks. When several placements seem plausible, Luhmann's
answer is pragmatic: choose one and record the other connections as references.

That maps unusually well to SASE:

| Luhmann's slip box | SASE Sites |
| --- | --- |
| Permanent slip number | Stable artifact/page reference |
| One physical filing position | One canonical `nav_parent` |
| Branching slip sequence | Parent/child navigation tree |
| References and backlinks | Typed links and derived relations |
| Keyword register | Root index, search, and structure pages |
| Preferred centers and regions | Topic pages and secondary sites |

This model removes the pressure to decide that a plan, bead, research note, or agent “really belongs” to every relevant
place. It belongs canonically in one navigation location and can participate in unlimited other contexts by reference.

### 1.2 The part not worth borrowing—or misrepresenting

Luhmann explicitly rejected systematic ordering by topics and subtopics because it would bind the collection to a
premature outline. He later described the whole as “not hierarchy, and most certainly no linear structure like a
book.” The network of links and backlinks, not the filing sequence alone, gave notes their value.

Therefore:

- `nav_parent` must mean **canonical placement for wayfinding**, not “broader concept,” “owner,” “security parent,”
  “only relevant topic,” or “the page that caused this page to exist.”
- Existing native relations—plan lineage, bead dependency, agent kinship, commit provenance, document mentions—must
  remain separate typed edges even when one happens to match `nav_parent`.
- The root must be an index and entry point, not a privileged note that claims to contain or validate all knowledge.
- Structure pages can collect links selectively. They need not duplicate a complete taxonomy.

Calling a strict topic tree “Zettelkasten” would be backwards. Calling a stable placement tree plus a dense reference
network “Zettelkasten-inspired” is accurate.

## 2. Why a canonical parent is valuable

### 2.1 Deterministic orientation

A page graph alone answers “what is related?” but not “where am I?” A unique parent chain gives every page one
deterministic breadcrumb. W3C's breadcrumb pattern is explicitly a list of parent pages in hierarchical order and is
intended to help users locate themselves within a site or application.

This matters at SASE scale. The prior reports measured more than 21,000 Markdown documents in the `sase` project alone.
Search and backlinks are essential, but neither substitutes for a predictable route:

```text
SASE Home → Projects → sase → Plans → Mobile MVP
```

The route is useful even when the user arrived through a cross-link from a bead, agent, or research page.

### 2.2 A real main site rather than a directory of unrelated sites

“Few sites, many pages” needs a default experience. A distinguished root page can be the landing page of a generated
main site that:

- lists enabled projects;
- exposes project, corpus, topic, and secondary-site children;
- provides global search and recent activity;
- surfaces orphan and broken-parent diagnostics to the owner; and
- offers one stable index link from every authorized page.

Without a root, “few sites” can still degrade into several unrelated hubs. With a root, secondary sites are deliberate
views within one larger information space.

### 2.3 Simple invariants and tooling

One canonical parent permits cheap, deterministic operations:

- compute breadcrumbs and ancestors;
- list children without ambiguity;
- render a navigation outline or site map;
- detect cycles and orphans;
- reparent one subtree;
- answer “where is the canonical home for this page?”;
- offer an `up` link and an `index` link in HTML; and
- provide a default subtree selection when an author explicitly asks for one.

The IANA Web Linking registry already distinguishes `up` (a parent document in a hierarchy), `index`, `collection`, and
`item`. SASE can serialize its navigation semantics using those standard relations while keeping its richer internal
edge vocabulary.

### 2.4 Clearer lifecycle ownership

A canonical parent provides an operational home for curation without becoming semantic ownership. If a generated
artifact has no authored placement, a deterministic collection page can own its navigation:

```text
project page → corpus index → artifact page
```

An authored overlay can later reparent it beneath a topic or structure page. The page reference does not change. This is
similar to systems that preserve stable object identity while letting users move the object between parents; Notion,
for example, gives every page a parent object and a separate stable UUID.

Google Drive shows the complementary alias pattern: it has a primary root hierarchy and stable opaque file IDs, while
shortcut objects point to files or folders from other locations. SASE does not need shortcut *pages*—an ordinary typed
link is enough—but the separation of identity, canonical placement, and alternate access paths is the right one.

## 3. Critique and failure modes

The idea is good only with the following qualifications.

### 3.1 A page often has several legitimate semantic parents

Knowledge organization is naturally polyhierarchical. The W3C SKOS model explicitly permits alternate hierarchical
paths and also separates hierarchical relations (`broader`/`narrower`) from associative relations (`related`). A SASE
research note might simultaneously be:

- part of a SASE Sites design thread;
- evidence for a web-client plan;
- relevant to a privacy bead; and
- produced by a particular agent.

Forcing all of those meanings into one `parent` field makes three relations disappear and makes the remaining one
arbitrary.

**Mitigation:** name the field `nav_parent`, not `parent`, `broader`, or `is_part_of`. Preserve every semantic relation
as its own typed edge. The navigation parent answers only “where is the canonical breadcrumb home?”

### 3.2 Parent-derived URLs would make reorganization dangerous

If page identity or canonical URLs contain the entire ancestor path, moving one branch breaks inbound links, saved
bookmarks, site specs, and source locks. This would reverse the prior report's correct decision that page identity is an
artifact reference.

**Mitigation:** page identity and routes remain ref-based and parent-independent. Reparenting changes breadcrumbs and
child listings, not the page ref. Human-readable slugs remain presentation aliases; publication slugs remain a separate
facet. If SASE emits path-shaped convenience URLs, it should also emit canonical ref-based URLs and redirects.

### 3.3 A global root can become a privacy coupling point

The user's local root may index private agents, chats, plans, and sidecars. A public secondary site cannot safely
include or expose that private ancestry. Conversely, publishing a root must not publish all descendants.

Notion is a useful warning: publishing a page publishes its subpages by default unless permissions are restricted. That
is convenient, but it is the wrong default for SASE's corpus, which includes thousands of prompts and chat transcripts.

**Mitigation:** ancestry is non-scope-bearing and non-authorizing.

```text
published set = explicit site scope ∩ audience ceiling
```

A public page's private or out-of-scope ancestor is rendered as an external authorized link when possible, or as a
non-linking reference stub. It is never pulled into the publication merely to complete the breadcrumb. Likewise,
publishing the root does not recursively publish descendants unless the site has an explicit, reviewed
`descendants_of(root)` scope rule.

The root is guaranteed to resolve in the owner's local graph; it is not guaranteed to be visible in every exported
projection.

### 3.4 A root can become a junk drawer

If missing parents silently fall back to the root, the tree technically remains valid while the index becomes useless.
This is especially likely for agent-created pages.

**Mitigation:** allow an orphan state during drafting and ingestion, but make it visible:

- generated pages receive deterministic collection parents;
- authored pages without a valid parent appear in an owner-only “Unplaced pages” diagnostic;
- local preview may render them;
- a version intended for deployment fails validation if any in-scope page lacks a valid ancestry chain; and
- no validator “fixes” an orphan by silently attaching it to the root.

This interprets “expected to have one parent” productively: temporary incompleteness is allowed, but a saved publishable
version is structurally complete.

### 3.5 One tree is not enough navigation

A deep hierarchy can be slow to browse, and different users approach the same information differently. W3C guidance
recommends multiple ways to reach content; search, site maps, navigation, and cross-links complement one another.

**Mitigation:** the parent tree supplies orientation, not the only discovery mechanism. Every page should also support:

- full-text search;
- backlinks;
- typed related links;
- “appears in these sites” links;
- corpus and type filters; and
- topic/structure pages.

The tree and graph should be rendered together, not as competing modes.

### 3.6 A single root changes the prior per-project assumption

The platform report recommended a per-project index and deferred cross-project hubs. A literal single root for every
page is user-scoped and necessarily federates enabled projects.

**Mitigation:** make the root a lightweight generated federation page, not a new global content database. Project roots
remain backed by project-local indexes and become children of the personal root. Global search can fan out across those
indexes. This preserves project isolation while making the navigation model globally coherent.

The root's identity should be deterministic and reserved, not a mutable title and not a row in a new registry.

## 4. Recommended data model

### 4.1 Two structures over the same page nodes

Let `V` be the set of page nodes and `r` the distinguished root page.

Define a navigation-parent function:

```text
nav_parent: V \ {r} → V
```

with these invariants:

1. `r` is the only node without a parent.
2. Every other publishable page has exactly one parent.
3. Repeatedly following `nav_parent` from any page reaches `r`.
4. Therefore, navigation-parent edges contain no cycles and form one rooted tree.

Separately define a typed link multigraph:

```text
links ⊆ V × RelationType × (V ∪ SiteRef ∪ ExternalRef)
```

The total knowledge structure is the union of the tree and the link graph. Arbitrary link cycles are allowed; parent
cycles are not.

This is a rooted spanning tree for navigation over a richer graph of meaning.

### 4.2 Page record

Illustrative logical shape:

```yaml
ref: research:202607/sase_sites_rooted_page_graph.md
nav:
  parent: sites:design/index.md
  parent_source: authored       # authored | derived | fallback
  order: 30                     # optional; deterministic default otherwise
relations:                      # derived and/or authored, not ancestry
  - type: supports
    target: plans:sase_sites.md
  - type: mentions
    target: bead:sase-123
```

The exact wire schema can differ, but four rules should not:

- `ref` is stable when `nav.parent` changes;
- the parent edge is stored or derived once, not inferred differently by each renderer;
- sibling order is explicit or deterministically derived; and
- semantic relations do not masquerade as navigation ancestry.

Generated defaults should be conservative and shallow:

| Page | Default navigation parent |
| --- | --- |
| Personal root | none |
| Project landing page | `Projects` structure page under the root |
| Corpus index (`Plans`, `Beads`, `Agents`, document role) | project landing page |
| Generated artifact page | its corpus index |
| Authored topic/structure page | explicitly selected parent |
| Authored content page | explicit parent, otherwise orphan diagnostic |
| Secondary-site landing page | explicit project, topic, or `Sites` structure page |

Native lineage can be offered as a one-click placement suggestion, but should remain a semantic relation by default.
For example, a plan's `PARENT` relation is not automatically its navigation parent; doing so would make navigation depth
and stability depend on workflow history.

### 4.3 Site record

A site is still a view and publication envelope, not a container that owns copies of pages:

```yaml
ref: sites:mobile_launch/site.yml
landing: sites:mobile_launch/index.md
scope:
  include:
    - pages: [...]
    - query: {...}
    # descendants_of is allowed only when explicitly requested.
layout: {...}
audience: local
publication: null
```

Formally:

```text
Site = (ref, landing_page, explicit_scope, layout, audience, publication)
```

The main site is the ordinary site whose `landing_page = r`. A secondary site's landing page is an ordinary page whose
own ancestry reaches `r`. Consequently:

- every site has a page-level home in the main information space;
- linking to a site can resolve to its landing page;
- a page can appear in many sites without acquiring multiple parents;
- sites can link to or mount one another without changing canonical ancestry; and
- deleting a site never deletes its referenced pages.

### 4.4 Relation vocabulary

The prior hub-and-pages report proposed `relation`, `mention`, `link`, `mount`, and `embed`. Add `nav_parent` as a
separate structural layer:

| Edge | Purpose | Stored? | Scope-bearing? | Cycle policy |
| --- | --- | --- | --- | --- |
| `nav_parent` | Canonical breadcrumb and child outline | Derived or authored | **No** | Must form one rooted tree |
| `relation` | Derived domain meaning: lineage, dependency, kinship, provenance | Recomputed | No | Allowed |
| `mention` | Inline artifact reference | Resolved at render | No | Allowed |
| `link` | Authored navigation to a page/site/external resource | Yes | No | Allowed |
| `mount` | Contribute a site's routes/layout | Yes | **Yes** | Site composition DAG |
| `embed` | Render a selected view inline | Yes | **Yes** | Site composition DAG |

This makes two distinct invariants easy to explain:

1. `nav_parent` answers **where is this page's canonical home?**
2. `scope` and `mount`/`embed` answer **what is included in this site?**

A normal hyperlink answers neither.

### 4.5 Web representation

For each rendered page SASE should emit:

- a visible breadcrumb from the current page toward the root, filtered through audience checks;
- `rel="up"` for the immediate accessible navigation parent;
- `rel="index"` for the accessible main root;
- `collection`/`item` relations for collection pages and direct children where appropriate;
- the stable canonical page URL based on the artifact ref;
- backlinks and typed related links; and
- an “Appears in” list for secondary sites whose accessible scope includes the page.

Use Dublin Core `isPartOf` only when a page is genuinely logically included in another resource. A navigation parent is
not automatically a semantic `isPartOf` relationship.

## 5. Validation and operations

The model is attractive partly because its correctness can be checked mechanically.

### 5.1 Save/build validation

For every page in a saved version:

1. resolve the page ref;
2. resolve exactly one `nav_parent`, except for the reserved root;
3. walk ancestors while recording visited refs;
4. reject a repeated ref with a human-readable cycle trace;
5. require the walk to terminate at the reserved root;
6. verify stable sibling ordering;
7. evaluate page visibility separately; and
8. compute site scope separately.

Suggested diagnostics:

```text
orphan: research:foo.md has no navigation parent
missing_parent: plan:bar points to missing page sites:plans/index.md
cycle: A → B → C → A
wrong_root: page reaches project:x but not the personal root
hidden_ancestor: breadcrumb segment B is outside this audience (informational)
```

### 5.2 Reparenting

`sase site page move <ref> --parent <ref>`—or its eventual equivalent—should:

- validate the proposed ancestor chain before writing;
- change navigation metadata only;
- preserve the page ref and canonical URL;
- leave semantic relations untouched;
- show affected descendants; and
- produce a normal reviewable source diff when the placement is authored.

Generated placement overrides belong in the authored site/navigation overlay, not in generated HTML and not in the
original artifact if that artifact's format does not own presentation.

### 5.3 Deleting a parent

Deleting or excluding a structure page with children must require one of:

- reparent the children;
- exclude the entire set from the current version; or
- leave authored children as diagnosed orphans in a draft.

It must not recursively delete underlying SASE artifacts.

### 5.4 Root behavior

The personal root should:

- always exist locally as a generated page;
- have a deterministic reserved identity and customizable title/layout;
- list project roots, topic/structure pages, and secondary-site landing pages;
- federate project-local indexes rather than replace them;
- remain non-public by default; and
- never imply that all descendants share its audience.

The generated base plus authored-overlay pattern from the prior report fits well: SASE owns the root's required
structure and the user can add ordering, prose, links, and widgets without ejecting from future generator improvements.

## 6. Example use cases

### 6.1 The main SASE home site

```text
SASE Home
├── Projects
│   ├── sase
│   │   ├── Plans
│   │   ├── Beads
│   │   ├── Agents
│   │   ├── Research
│   │   └── Docs
│   ├── sase-github
│   └── sase-telegram
├── Topics
│   ├── Sites design
│   ├── Mobile
│   └── Artifact UX
└── Sites
    ├── Mobile launch
    └── Release review
```

A plan remains canonically under `Projects → sase → Plans`. Its page links to its bead, implementing agents, commits,
and relevant research. The “Sites design” topic page links to this report and the two July 29 reports without
reparenting them. The main root provides consistent orientation, while search and cross-links expose the actual
knowledge network.

Why this is better than several project sites with no common root:

- there is one index URL to remember;
- cross-project pages have a coherent local home;
- project sites remain independently indexed and deployable; and
- adding a project adds one child branch rather than a new top-level product concept.

### 6.2 A cross-cutting SASE Sites design page

Suppose the design topic depends on:

- the platform research report;
- the hub-and-pages report;
- this rooted-graph report;
- a renderer implementation page;
- a privacy bead; and
- a future deployment plan.

Those pages belong to different corpora and possibly different projects. A topic landing page under
`SASE Home → Topics → Sites design` links to all of them. It may later become the landing page of a secondary authored
site for design review.

The single-parent rule helps because each source retains one canonical home and one breadcrumb. The arbitrary link
graph helps because the topic page can assemble the exact design context without copying, moving, or multiplying site
records.

### 6.3 A release or launch site assembled from existing pages

The “Mobile launch” site can include:

- an authored overview page;
- selected plan and bead pages;
- an agent roster view;
- a commit timeline; and
- a redacted research summary.

Its landing page has a canonical parent such as `SASE Home → Sites → Mobile launch`. The included plan pages stay under
their project/corpus parents. The site merely renders them in another layout and records that they “appear in” the
launch site.

When this site is shared:

- explicit scope decides which pages ship;
- audience ceilings exclude private agent details;
- out-of-scope ancestors do not get pulled into the bundle;
- canonical page refs keep links stable; and
- the local SASE home still provides full ancestry to an authorized owner.

This is precisely the “few sites, many pages” payoff: one launch site can reuse dozens of pages without creating dozens
of sites or duplicate content.

### 6.4 Agent work viewed from several contexts

An agent page is canonically located under its project and hood/family navigation. Its prompt and chat remain tabs of
that agent page, preserving the privacy-boundary page cut from the prior report.

The same agent page can be linked from a plan, bead, release site, and topic page. Those inbound contexts are visible as
backlinks. There is no need to make the agent page a child of multiple plans or to create one agent site per task.

## 7. Impact on the prior implementation plan

This proposal changes the data model modestly, not the platform direction.

Keep from the July 29 reports:

- one site type;
- sites are few and pages are many;
- artifact-ref page identity;
- a shared project-local retrieval index in Rust;
- deterministic Jinja2/Markdown rendering;
- explicit site scope and audience ceilings;
- `relation`/`mention`/`link`/`mount`/`embed`;
- static export plus `sase_gateway` serving; and
- save/deploy separation with commit-pinned source locks.

Add or revise:

1. **Add `nav_parent` to the shared page model and index.** Enforce uniqueness per child and index both parent and
   child for recursive navigation queries.
2. **Reserve a generated personal root page.** It federates enabled project roots and is the landing page of the main
   SASE site.
3. **Give every site a landing page.** A secondary site's landing page participates in the tree; the site's scope does
   not.
4. **Generate conservative default parents.** Project → corpus → artifact is the stable fallback. Authored overlays can
   place pages under topic and structure pages.
5. **Add tree diagnostics before publication.** Orphans may exist in drafts; in-scope publishable pages must reach the
   root.
6. **Render breadcrumbs and child outlines before graph visualization.** This provides immediate product value and
   tests whether the hierarchy is useful.
7. **Keep ancestry out of authorization and default publication.** This should be a named invariant in the wire
   contract and tests.

A small prototype can precede the full FTS index:

- use the existing xprompt/skill renderer;
- create a generated root, project page, corpus page, and several leaf pages;
- add two authored topic pages and a secondary site;
- render canonical breadcrumbs, backlinks, and “appears in” links; and
- test reparenting, an orphan, a cycle, and a public projection with a private ancestor.

That spike would validate the product semantics without committing to the full 21,000-page build.

## 8. Decision

### Pursue

- A distinguished root page as the main local SASE site.
- Exactly one canonical `nav_parent` for each publishable page except the root.
- Stable ref-based identity independent of ancestry.
- Unlimited typed cross-links, relations, mentions, and backlinks.
- Secondary sites as explicit views anchored at landing pages in the tree.
- Deterministic collection parents for generated pages and explicit placement for authored pages.
- Mechanical validation of root reachability, uniqueness, cycles, and orphans.

### Do not pursue

- A strict semantic taxonomy in which `parent` means “broader topic.”
- Page or URL identity derived from the ancestor path.
- Automatic publication or authorization inheritance from ancestry.
- Automatic inclusion of everything reachable by parent or ordinary link edges.
- A site record per page.
- Silent attachment of unplaced pages to the root.

## Sources

### Prior SASE research

- `202607/sase_sites_platform/sase_sites_platform.md`
- `202607/sase_sites_hub_and_pages/sase_sites_hub_and_pages.md`
- `202607/artifact_refs_and_inspector/artifact_refs_and_inspector.md`

### External primary and official sources

- Niklas Luhmann, [Communicating with Slip Boxes](https://luhmann.surge.sh/communicating-with-slip-boxes), translated
  by Manfred Kuehn; bibliographic record at the
  [Niklas Luhmann Archive](https://niklas-luhmann-archiv.de/bestand/bibliographie/item/luhmann_2015_T-AW01).
- Niklas Luhmann Archive,
  [Digital Zettelkasten tutorial](https://niklas-luhmann-archiv.de/bestand/zettelkasten/tutorial).
- W3C, [SKOS Simple Knowledge Organization System Reference](https://www.w3.org/TR/skos-reference/), especially
  hierarchical versus associative relations and alternate hierarchical paths.
- W3C WAI, [Breadcrumb Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/breadcrumb/) and
  [Multiple Ways](https://www.w3.org/WAI/tutorials/menus/multiple-ways/).
- IETF, [RFC 8288: Web Linking](https://www.rfc-editor.org/rfc/rfc8288), and the IANA
  [Link Relations registry](https://www.iana.org/assignments/link-relations/link-relations.xhtml).
- Dublin Core Metadata Initiative,
  [`dcterms:isPartOf`](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/terms/isPartOf/).
- Notion API, [Page object](https://developers.notion.com/reference/page),
  [Parent object](https://developers.notion.com/reference/parent-object), and Notion Help,
  [Publish a website with Notion Sites](https://www.notion.com/en-gb/help/public-pages-and-web-publishing).
- Google Drive API, [Files and folders overview](https://developers.google.com/workspace/drive/api/guides/about-files)
  and [Create a shortcut](https://developers.google.com/workspace/drive/api/guides/shortcuts).

## Recommended solution

Adopt a **rooted navigation tree plus typed link graph** as the SASE Sites page model.

Create one deterministic, generated personal root page and use it as the landing page of the main SASE site. Require
every publishable page except that root to have exactly one `nav_parent`, with validated, acyclic ancestry that reaches
the root. Keep page identity artifact-ref-based and independent of ancestry. Treat `nav_parent` only as canonical
placement for breadcrumbs, child outlines, and curation—not as semantic classification, site membership, permission
inheritance, or publication scope.

Keep arbitrary typed relations between pages and sites. Give every secondary site a landing page in the navigation tree,
but define the site's actual contents through explicit scope rules and audience ceilings. A page may appear in any
number of secondary sites without changing its canonical parent. Ancestors outside a deployed site's scope remain
external links or non-leaking stubs; they are never auto-published.

Implement this first as a small renderer and validation spike over xprompts/skills and a few authored topic pages. If
the breadcrumbs, root index, reparenting behavior, and privacy projection all hold up, add `nav_parent` to the shared
Rust page index before scaling to the full corpus.
