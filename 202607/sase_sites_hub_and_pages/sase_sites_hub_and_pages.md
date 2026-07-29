---
create_time: 2026-07-29
updated_time: 2026-07-29
status: research
---

# SASE Sites: One Site Primitive, Hubs and Pages

## Research question

Should SASE drop the proposed `project` / `custom` site kinds in favor of **one generic site** that links to zero or more
other sites and artifacts — where each enabled project's site is produced by emitting a site per meaningful artifact
(plans, beads, agents) and linking them under a hub site that specifies tabs and layout?

## Provenance and method

Consolidates two independent reports written concurrently without knowledge of each other, plus this verification pass:

- `sase_sites_hub_and_pages__a.md` (agent `research.r.cdx`, codex/gpt-5.6-sol) — composition semantics: link/mount/embed,
  generated-base-plus-overlay, composition-aware versioning, access closure, reader/writer API, MCP alignment.
- `sase_sites_hub_and_pages__b.md` (agent `research.r.cld`, claude/opus) — corpus measurement, the
  identity-is-the-artifact-ref argument, the link-is-not-a-grant invariant, the privacy-boundary node cut.
- This report — re-measured both reports' load-bearing claims, resolved seven conflicts, and found **two things neither
  report found**: SASE already ships a working corpus→HTML site renderer, and the prior artifact-refs research already
  decided the identity question both reports argued from scratch.

Both extend `202607/sase_sites_platform/sase_sites_platform.md`. Its non-ontology decisions (extend `sase_gateway`, index
first, Python rendering, commit-pinned source locks, privacy ceiling, `/sase_repo`-style skill contract) are unchanged
here except where noted. Claims marked *verified* were re-measured at `af4295179` (sase) and the current `sase-core`
checkout.

## Executive summary

**Adopt one site primitive. But the primitive is "one kind of site," not "one site per artifact."**

Both reports converge on collapsing `project`/`custom`, and both are right: verified, every axis the enum was carrying —
identity, layout, content, versioning, access, render target, API — is identical across the two supposed kinds. Only
*origin* differs, and origin is a field.

Both reports then spend most of their length wrestling the same follow-on problem: if every artifact is a site, do you
create 13,000–21,000 site records? `__a` answers with virtual-views-plus-promotion; `__b` answers with
addressing-not-materialization. Both work. Both are also unnecessary, because the premise is avoidable:

> **Sites are few; pages are many.** A *site* is a layout plus a publication envelope. A *page* is a route within a site
> addressed by an artifact reference. There is one site type, one layout schema, one renderer, one index — and no site
> record for individual plans, beads, or agents, because those are pages.

This is `__b`'s own §9.1 fallback (`page` for the node, `site` for the publication), promoted to primary. It costs
nothing, dissolves the entire granularity debate, and keeps everything valuable from both reports: pages are still
addressed by artifact refs (`__b` §4), collections are still mountable when they earn it (`__a` §3), and "share this
site" is never ambiguous. Decide it now — the expensive thing to change later is the CLI surface, not the model.

The five decisions that follow:

1. **Identity is the artifact reference** — for pages and for site sources alike. Already-settled prior art, not a new
   judgment call (§2.2). Publication adds a durable slug; content adds no new ID space.
2. **A prerequisite blocks everything and is worth shipping alone**: there is no `bead:` or `agent:` artifact ref kind
   (verified in both Python and Rust). Fix it first; it pays off in ACE, the LSP and the artifact CLI whether sites ever
   ship (§2.1).
3. **A link is a reference, not a grant.** Published set = explicit scope ∩ audience ceiling, never reachability. This is
   the sharpest risk in the single-type model and `__b`'s most important contribution (§3.2).
4. **Composition needs four edge types, not "linking."** Derived relations and mentions never bear scope; authored
   mounts and embeds do, and must form a DAG (§3.1).
5. **A working renderer already exists in the tree.** `sase xprompt catalog` is a shipped corpus→document-model→
   self-contained-HTML+PDF pipeline. Generalizing it is a days-scale v0 that neither report considered (§2.3).

---

## 1. What both reports get right (settled; not re-litigated below)

- Collapse `project`/`custom` into one record with `source: generated | authored`. Origin is metadata, not a sum type
  that every CLI command, endpoint, renderer and deploy adapter branches over.
- Do not create a durable record per artifact instance. Both reports reject it independently, for the same reason: it
  rebuilds a corpus-sized second source of truth.
- Publication — versioning, access, deploy — is real machinery, but it is an **optional facet on any site**, not a second
  kind. Absent facet means "renderable, not shareable."
- Keep the save/deploy split with commit-pinned source locks. Never auto-deploy a parent because a child changed; produce
  a draft and notify.
- Hub-ness is emergent, not typed. A hub is an ordinary site whose tabs mostly reference other things.
- Agent prompts, chats and output variables stay excluded by default.
- `__b`'s corpus measurements reproduce. Verified independently today: **3,308** plan documents, **2,805** prompt
  snapshots, **~3,005** agent `chat.md`, **2,334** bead pages (small deltas are live churn). Both reports' scale
  arguments rest on sound numbers.

---

## 2. New evidence this pass adds

### 2.1 The blocker is real, at both layers — and it is the best first bead

`__b` found it; `__a` missed it; it is confirmed on both sides of the binding:

- `src/sase/artifact_ref_models.py:12` — `BUILTIN_ARTIFACT_REF_KINDS = ("commit", "chat", "bug", "file")`
- `crates/sase_core/src/artifact_ref/wire.rs` — `ArtifactRefKindWire` is exactly `Commit`, `Chat`, `Bug`, `File`,
  `Document { role }`
- `src/sase/sdd/_store_types.py:40-48` — *"`beads` and `agents` are never document roles"*, enforced by the filter below
  the docstring

So today you cannot write `@bead:sase-19.3` or `@agent:bbugyi200.athena.9w`. Both reports' node models assume an
addressing scheme that does not exist, and the original consolidated note's §5.1 node list assumes it too. `bug:` is a
GitHub issue, not a bead.

`__b`'s recommendation stands and should be emphasized: add `Bead` and `Agent` ref kinds as a **standalone pre-sites
change**. It is small, it unblocks the whole model, and it independently improves artifact-ref completion in ACE, LSP
highlighting/diagnostics, `sase artifact show/path/open`, and prompt reference expansion.

### 2.2 The identity dispute was already decided — in `__b`'s direction

This is the reports' sharpest conflict. `__a` §2 keeps a durable opaque `site_id` per persisted Site; `__b` §4 argues
identity *is* the artifact ref, with no new ID space. Neither cites the note that settles it.

`202607/artifact_refs_and_inspector/artifact_refs_and_inspector.md` ran exactly this argument to conclusion and found two
pieces of decisive local evidence:

- **SASE built the opaque-ID registry and deleted it.** The unified artifact graph — SQLite store, SQL-backed search,
  paged detail contracts, ingestion from agent artifacts / ChangeSpecs / commits / beads / thoughts, graph export —
  landed 2026-05-05 and was removed 2026-05-06 in `b455124`: **12,898 deletions across 11 files**, including 967 lines of
  PyO3 bindings. It lived ~24 hours and never reached a user.
- **SASE solved the durable-naming problem correctly, two days ago.** Epic `sase-9z` — *"Make bead plan linkage durable
  with logical `plans:` references"* — closed 2026-07-27 and **repaired 227 stored links that no longer resolved.** That
  is a proven five-phase playbook for making an artifact kind durably referenceable.

Its verdict: *"Do not build a new artifact store, registry, or second index."* Note that `__a` cites the deleted graph as
a reason not to persist a Site per artifact — and then reintroduces minted IDs for the Sites it does persist. That is
inconsistent, and the prior research resolves it.

**Resolution — with the piece neither report reached.** Ref-as-identity is right, but `__a`'s underlying worry is
legitimate and `__b` understates it: refs are path-derived, so renaming `sase/sites/foo/` renames the site and breaks any
URL already handed to a teammate. Split the two needs the enum was hiding:

- **Source identity = artifact ref.** `sites:<name>/site.yml` for authored sites; the page's own ref for every rendered
  page. No registry, no slugs, no creation step, and drift semantics inherited free (`exact`/`drifted`/`ambiguous`/
  `missing`/`unknown_*` already exist on the resolver, plus `sase artifact doctor`).
- **Published identity = a slug in the `publication` facet.** Durable across source renames, because that is the only
  string that ever appears in a URL a human keeps. It is minted once, when publication is first requested — not for
  13,000 pages nobody shares.

That satisfies `__a`'s real requirement ("sites outlive the run that created them; agents must never infer identity by
title matching") without a corpus-sized ID space.

### 2.3 A corpus→HTML site renderer already ships, and neither report found it

`sase xprompt catalog` (733 lines across `src/sase/xprompt/catalog.py`, `_catalog_render.py`,
`catalog_template.html.j2`, `catalog_style.css`) already does end to end what a site does:

| Site stage | Existing implementation |
| --- | --- |
| Gather a SASE corpus across all resolution sources | `_catalog_sources.gather_entries()` |
| Compute overview metrics | `compute_stats()` → `CatalogStats` (`total`, `by_project`, `by_source`) |
| Build a structured, renderer-agnostic document model | `build_document()` → `CatalogDocument` |
| Render self-contained HTML | `render_html()` — Jinja2, `autoescape=select_autoescape(["html","xml"])`, CSS inlined via `{{ css_text \| safe }}` |
| Export a portable artifact | `render_pdf()` — wkhtmltopdf, pandoc fallback |

`jinja2` is a runtime dependency (`pyproject.toml:37`). This is the smallest honest v0 for sites, and it also answers
`__b`'s open question 5 emphatically: **xprompts and skills should be the first corpus rendered**, because they are the
most genuinely shareable, the smallest, and the only corpus that already has a renderer.

**It also corrects the original note's rendering plan.** That note says Markdown→HTML should "reuse the artifact-HTML
pipeline" per `202605/markdown_to_html_rich_artifacts.md`. Verified: there is no such pipeline in this repo.
`markdown-it-py==4.0.0`, `mdit-py-plugins==0.5.0` and `linkify-it-py==2.1.0` are pinned in the **`visual` extra only**
(the PNG-snapshot stack) and imported by exactly one test; `nh3` is not a dependency at all. The `202605` note is a
*decision*, not an implementation.

The two decisions are complementary, not competing, and should be stated separately:

- **Page shell, layout, tabs, widgets → Jinja2 templates over a structured document model** (existing precedent,
  autoescaped).
- **Markdown document bodies → `markdown-it-py` + `nh3`** (existing decision; requires promoting the pins to runtime
  deps and adding `nh3`).

### 2.4 "One site per meaningful artifact" is ambiguous — SASE has two artifact vocabularies

Neither report addresses this, and the user's framing sits directly on the seam. Per
`artifact_refs_and_inspector.md` §1.1, two disjoint things are called artifacts:

| | **Artifacts tab entities** | **Artifact *files*** |
| --- | --- | --- |
| What | Commits, Plans, Chats, Bugs, PRs | Agent-produced images, markdown, PDFs, videos, explicit files |
| Model | 5 unrelated types | `ArtifactFile` (`src/sase/core/artifact_file_types.py:51`) |
| Storage | Repos, SDD sidecars, bead store, chats catalog | `~/.sase/artifacts/` + `index.jsonl` |
| Scale | see §1 | **3,985 rows / 622 MB**, 188 explicit, 533 producing agents |

`__b`'s node table covers the first vocabulary plus beads/agents/families/xprompts/skills/ChangeSpecs. Neither report
places the 3,985 agent-produced media files, which are the corpus most likely to make a site *look* good (3,775 images,
including the research infographics) and are already durably addressable as `file:` refs.

**Recommendation:** artifact files are page *content*, not pages. They render as galleries and inline media within a
producing agent's page or a document's page. Say so explicitly in the spec, because "a site per artifact" reads as a
promise about both vocabularies.

### 2.5 Smaller verified corrections

- **The ACE-reuse claim is overstated in both reports and in the original note.** `src/sase/ace/tui/tab_order.py`:
  ACE has exactly three top-level tabs — `agents`, `changespecs` (labeled "Artifacts"), `axe`. There is no Plans, Beads,
  Docs, Graph or Search tab to mirror. `artifact_tabs.py` supplies only the five *Artifacts sub-tabs*
  (`commits`, `plans`, `chats`, `bugs`, `prs`) and their accents. Those can be reused verbatim; the project-hub tab
  vocabulary is **new design**. "Mirror ACE so the surfaces teach each other" is a goal, not a constant to import.
- **The query-language correction is right, and there is a better in-tree model than either report names.** `__b` is
  correct that `docs/query_language.md:1-11` is ChangeSpec-only and explicitly notes the Agents tab has a separate
  language, so the original note's `query: "bead:sase-26.*"` is not valid anywhere. The constructive answer is already
  shipped: `query_artifact_files()` (`src/sase/core/artifact_file_query_facade.py`) executes in Rust over a
  **structured filter set** — `kinds`, `project`, `agent`, `since`, `explicit_only`, free-text `query`, `limit`. Widgets
  should adopt that shape (`corpus:` + typed `filter:` + optional free-text), not a new DSL string.
- **`tower-http` still lacks `fs`** (`Cargo.toml:30`, features `["trace"]`), and `mobile_http_enabled` is at
  `daemon.rs:37` — the per-feature-flag precedent both reports rely on is real.
- **`site/` remains taken**, now doubly: `mkdocs.yml` sets `site_dir: site`, wrangler claims it as `assets.directory`,
  and `mkdocs.yml:103-108` adds a **blog** plugin over `blog/posts/`. `sase site build` must not default there, and the
  docs/blog pipeline and `sase site` need an explicit documented boundary.
- No existing `site` bead or epic; `sase bead search "site"` returns only unrelated "call site" matches. Greenfield
  confirmed.

---

## 3. Conflicts between the two reports, resolved

| # | Conflict | `__a` (cdx) | `__b` (cld) | Resolution |
| --- | --- | --- | --- | --- |
| 1 | Site identity | Durable opaque `site_id` per persisted Site | Identity *is* the artifact ref; no new ID space | **`__b`, with `__a`'s concern honored as a split (§2.2).** Source identity = ref. Published identity = a slug minted only when publication is requested. Prior art (deleted registry + closed `sase-9z`) is decisive. |
| 2 | Per-artifact granularity | Virtual Site views, promoted on demand | Addressed always, materialized by scope | **Neither — reframe.** Per-artifact things are **pages**, not sites (§Executive). Both mechanisms then become one: a page is rendered on demand and exported when scope selects it. |
| 3 | Edge vocabulary | `link` / `mount` / `embed` | `link` (derived) / `include` / `mention` | **Merge into four (§3.1).** The reports are describing different cuts of the same space; both cuts are needed. |
| 4 | Collection sites | Persist a Plans/Beads/Agents collection Site and mount it into the hub | A hub tab whose widgets are corpus queries; no intermediate record | **`__b` by default, `__a`'s mechanism retained.** Eagerly creating collection Sites is the premature-registry mistake at 1/1000 scale, and it forces every hub version to carry child locks for children nobody shares separately. Keep `mount` as a primitive so a collection can be *promoted* when it needs independent access, versioning or sharing — which is `__a`'s own promotion rule. |
| 5 | Customizing a generated hub | Generated base + validated authored overlay, with conflict diagnostics | Materialize the default layout into `sase/sites/<project>/site.yml` and edit it | **`__a`, with `__b`'s as the escape hatch.** Eject-only guarantees drift. SASE's own convention argues for overlay: plan header blocks are deliberately *"re-derived rather than accumulated"* across 2,784 plans. Default layout stays built-in; customization is an overlay the generator re-applies every rebuild. Full materialization stays documented as a last resort. |
| 6 | Writes | Rich remote authoring: manifest discovery, ETag + `If-Match`, `412`, typed actions | v1 read-only w.r.t. the corpus | **Both, ordered by *what* is written.** v1 spec writes go through the repo workflow (`sase site open` → edit → `/sase_git_commit`) — SASE-native, uniform across runtimes, and it already satisfies the user's "written to by sase agents." `__a`'s ETag design is correct and belongs at Phase N, when concurrent remote editing is real. Corpus writes are never a site API in either phase: typed gateway operations only. |
| 7 | MCP | Align the `bundle` renderer with MCP Apps; add MCP Resources/Tools adapters | Not addressed | **Adopt `__a`'s sandbox contract; temper its position.** The **Uniform Agent Runtimes** rule means the canonical agent surface must be the CLI plus the generated skill — every runtime gets identical behavior. MCP is an adapter for MCP-capable hosts, never the identity or primary runtime. `__a`'s sandbox rules (predeclared digest, no bearer token in the iframe, CSP allowlist, bridge-only typed actions, host-enforced consent) are the right model for `bundle` regardless. |

`__b` is stronger on evidence, corpus scale, privacy and the addressing prerequisite. `__a` is stronger on composition
semantics, versioning under composition, and the machine contract. The merge below takes each where it is strongest.

### 3.1 The merged edge vocabulary

Two axes — derived vs authored, scope-bearing vs not — yield four types. `__a`'s three and `__b`'s three overlap
partially; neither set alone is sufficient.

| Edge | Origin | Stored? | Bears scope? | Cycles | Notes |
| --- | --- | --- | --- | --- | --- |
| **`relation`** | Derived from the corpus: plan header blocks, commit trailers, bead lineage, agent kinship, breadcrumbs | No — recomputed each build | **No** | Allowed | `__b`'s `link`. Backstage's read-only `relations`: derived edges must never be confused with authored spec. |
| **`mention`** | An inline `@ref` in prose, found by `artifact_ref/scanner.rs` | No — resolved at render | **No** | Allowed | `__b`'s. |
| **`link`** | Authored navigational hyperlink to another site or page | Yes | **No** | Allowed | `__a`'s. Target enforces its own access. |
| **`mount` / `embed`** | Authored layout: mount contributes child routes into the parent's navigation; embed renders a selected view inline | Yes | **Yes — the only scope-bearing edges** | **Rejected (DAG)** | `__a`'s. `__b`'s `include` is their union; splitting them is worth it because routes and inline rendering have different validation. |

Keep `__a`'s rules verbatim: validate the transitive mount/embed closure before save; a broken `link` is a diagnostic and
a disabled link, a broken `mount`/`embed` is a build error; mounting one child twice requires distinct mount IDs and
routes; deleting a site never deletes linked sites or artifacts.

### 3.2 The invariant that makes the single-type model safe

`__b`'s central guardrail, and the reason the collapse is *safer* than the two-kind design rather than riskier:

> **A site's published set is `explicit scope rule ∩ audience ceiling`. Never graph reachability.** In-scope pages are
> published whether or not anything links to them. Out-of-scope pages are not published even when linked, and inbound
> links degrade to **unresolved reference stubs** — a visible label, not a broken URL.

The two-kind design contained the blast radius by accident (custom sites listed widgets explicitly; the project site had
per-corpus flags). Collapse to one linked type and the natural reading becomes "a site includes what it links to" —
which, on a graph where plan → prompt → agents → chats → commits → beads → plans is fully connected, means everything.
Notion does exactly this: subpages publish by default, opt-out per page. **Invert it.**

The stub behavior is existing house style, not a new invention: `src/sase/sdd/hosted_links.py` is *"local-only, never
raises, and returns `None` instead of guessing, so a store without an authoritative hosted remote degrades to an unlinked
label instead of a broken URL."* Extend that discipline from "no remote" to "out of scope."

Layer `__a`'s access closure on top, for the scope-bearing edges only:

```text
max parent audience ≤ intersection of all transitively mounted/embedded source audiences
```

Record which dependency caused a ceiling reduction. Refuse a public parent mounting a private child, offering
"link instead," "exclude," or an explicit redacted projection. Do not leak a private child's title, count or existence
through a public parent. Re-check active deployments when any child or source policy narrows. Never transitively inherit
actions — a parent re-exports each one explicitly.

### 3.3 Draw the page boundary at the privacy boundary

`__b`'s best structural insight, and `__a` has no equivalent. Make "has a URL" coincide with "is a privacy boundary":

| Artifact | Own page? | Rationale |
| --- | --- | --- |
| Plan · Bead · Agent · Family/hood/machine · document-role note · xprompt · skill · ChangeSpec · Project | **Yes** | Independently meaningful; most already have a generated Markdown page |
| **Prompt snapshot (2,805)** | **No — a tab of its plan** | 1:1 with a plan |
| **Chat transcript (~3,005)** | **No — a tab of its agent** | 1:1 with an agent, and the highest-risk corpus |
| **Commit (11k+)** | **No — a row/link** | Canonical home is already GitHub |
| **Artifact file (3,985)** | **No — gallery/inline content** | §2.4; addressable as `file:` refs |

This removes ~17,000 would-be nodes *and* makes the sensitive corpora structurally unreachable as independent link
targets: you cannot link a chat without linking its agent, whose audience is already being decided. The agent inclusion
profiles from the original note (`metadata` / `summaries` / `full`) then apply at exactly one place — the agent page's
tab set.

---

## 4. The merged model

### 4.1 One record

```yaml
# Identical shape whether generated or authored.
ref: sites:mobile_launch/site.yml   # source identity — an artifact ref, not a new ID space
source: authored                     # | generated    (replaces kind: project | custom)
title: SASE Mobile MVP Launch Hub
subjects: [...]                      # project, artifact refs, or corpora this site is about
generator:                           # present iff source: generated
  name: project-hub
  version: 1
layout:                              # ordered tree: tabs -> widgets/mounts/embeds
  tabs: [...]
resources: {...}                     # named link / mount / embed targets
relations: [...]                     # DERIVED, read-only, never authored
renderer:
  mode: standard                     # | bundle (later, sandboxed)
publication:                         # OPTIONAL FACET; absent means "renderable, not shareable"
  slug: mobile-launch                # durable published identity (§2.2)
  scope: {...}                       # the only thing that decides what is published
  audience: local
  version: {...}                     # commit-pinned source + child locks
  target: {...}
```

Nothing says `kind: project` or `kind: custom`. Semantic relations (an unordered derived graph, explaining *why* things
connect) stay separate from layout (an ordered tree, explaining *where* things appear) — RFC 8288's discipline, and
IIIF's ordered-`items`-plus-`partOf` separation. That separation is what lets a mobile renderer turn tabs into a nav list
without touching the spec, and lets machine readers ignore layout entirely.

### 4.2 Layout is data; tabs come from the existing renderers

Per-kind default layouts, read off what SASE already generates in Markdown — not invented:

| Page kind | Default tabs | Vocabulary source |
| --- | --- | --- |
| Plan | Plan · Prompt · Agents · Commits · Beads | plan header block (`PROMPT`/`PARENT`/`AGENTS`/`COMMITS`) |
| Bead | Overview · Lineage · Phases · Dependencies · Commits · Agents | `bead_pages/rendering_tables.py`, `rendering_graph.py` |
| Agent | Summary · Prompt · Chat · Commits · Kinship · Artifacts | `agents_sync/rendering_agent_page.py`, `rendering_kinship.py` |
| Family | Members · Timeline · Commits | `rendering_family_page.py` |
| Document-role note | Document · Backlinks | `artifact_ref/scanner.rs` |
| **Project hub** | Overview · Plans · Beads · Agents · Artifacts · *one per document role* · Docs · Graph · Search | **New design** (§2.5); reuse `ARTIFACTS_SUBTAB_ORDER`/`ARTIFACTS_ACCENTS` for the Artifacts tab's sub-tabs only |

A leaf page has one tab with a markdown widget. A hub has several tabs whose widgets are corpus queries and mounts. Same
record, same renderer, same schema — that is the entire content of "collapse the two kinds."

**Corpus tabs must be derived from the resolved store record's role map**, never hardcoded to `research`. `Document
{ role }` is role-parameterized precisely so this works.

### 4.3 `sase site` vs `sase artifact` must stay crisp

`sase artifact` already ships `list`/`show`/`path`/`open`/`create`/`doctor` over the same refs. State the rule in the
docs and in the skill, or the two surfaces will grow duplicate resolution paths:

> **`sase artifact` resolves the source. `sase site` renders and publishes the view.** Same refs, different verb space.

Corollary from §2.2's prior art: **do not build a second index for sites.** One nodes table plus one edges table with
typed columns — `__b`'s WordPress lesson is apt here (one generic node table is fine; a generic EAV attribute table hits
a query cliff, and the edge count lands near 10⁵). Follow `agent_scan/index.rs`'s schema-versioned rebuild/upsert/query
shape and `agent_archive/mod.rs:641`'s FTS5 virtual tables. Size expectation: `~/.sase/agent_artifact_index.sqlite` is
**74 MB at schema version 19** today — plan for a peer of that, not a toy.

---

## 5. Recommended approach

Ordering differs deliberately from both reports and from the original note. All three say "index first." The index is
still the genuinely missing capability and still the big investment — but a **renderer spike over the smallest corpus
comes first**, because it costs days (§2.3 reuses shipped code), and it answers the product question ("is a generic site
actually good?") before the expensive phase. You cannot render a Plans tab over 3,308 documents without retrieval, so
the index still precedes the hub.

| Phase | Scope | Size |
| --- | --- | --- |
| **0 — Addressing** | Add `Bead { project, id }` and `Agent { name }` to `ArtifactRefKindWire`; add a `sites` document role over `sase/sites/` (fits the existing `sase/xprompts/`, `sase/memory/`, `sase/repos/` convention in `docs/content_layout.md`). Ships value in ACE completion, the LSP, prompt expansion and `sase artifact` with **no sites, no HTML, no server**. Do this regardless of whether sites proceed. | S |
| **1 — Renderer spike** | Generalize `sase xprompt catalog` into `SiteDocument` + a standard Jinja2 shell; render xprompts and skills as the first corpus; emit one self-contained HTML file. Locks the document model, the widget vocabulary and the layout schema against real output. Promote `markdown-it-py`/`mdit-py-plugins` to runtime deps and add `nh3` for document bodies. | S–M |
| **2 — Index** | `sase_core::site`: one nodes table, one edges table, typed columns, FTS5, schema-versioned rebuild, incremental keying by Git blob SHA. `sase site index` + `sase site search`. Delivers retrieval over ~21k documents with no renderer changes. | M |
| **3 — Pages and the hub** | Per-kind default layouts (§4.2); the project hub with an **explicit scope rule** and loud exclusion reporting per the `… and N more` convention; the privacy-boundary page cut (§3.3); `local` audience only. Pre-render the ~6,600 high-value pages, shard the tail to on-demand JSON, shard the search index by corpus and month. Output goes to an artifact store, **not `site/`**. | M |
| **4 — Composition** | `link` / `mount` / `embed` as distinct operations (§3.1); DAG validation with human-readable cycle traces; route-ownership validation; transitive access-closure checks; generated base + validated authored overlay with conflict diagnostics. | M |
| **5 — Serve** | `sites_http_enabled` beside `mobile_http_enabled`; the `/sites` router; uniform `GET /sites/:project/node/:ref` with a `.json` twin per Datasette; SSE live-reload; `tower-http` `fs`. Specified in the **shared `/api/v1` contract** that serves the Android app and the future web client — not a parallel surface. Inherit the non-loopback bind refusal, pairing→bearer auth, audit log, `contract.rs` snapshot discipline, and `Host`-header validation unchanged. | M |
| **6 — Authored sites and the skill** | `sase/sites/`, `sase site new/open/check`, the hub template, and `/sase_sites` modeled on `/sase_repo`'s hard contract — use the skill first, treat the printed path as the only path. Teach `link` vs `mount` vs `embed` **before** layout widgets; it is the most consequential authoring choice. Ship after the CLI is stable, per the CLI/skill contract-sync rule. | M |
| **7 — Publication facet** | Minted slug, commit-pinned source and child version locks, `versions`/`export`/`deploy`, the audience ladder, interactive-only consent per `docs/sdd_storage.md:118`, refuse-public-when-agents-private, `sase doctor` scope-vs-corpus drift check, a `sites-deploy` workflow modeled on `docs-deploy.yml` targeting a **separate** Cloudflare Worker. | M |
| **8 — Later** | HTTP spec writes with strong ETag + `If-Match` → `412`; typed site actions over existing gateway operations; sandboxed `renderer.mode: bundle` per `__a`'s MCP-Apps-shaped contract; MCP Resources/Tools adapters; cross-project hubs; retrieval chat over the index. | L |

### The seven decisions, stated plainly

1. **One site type.** Drop `project`/`custom`; replace with `source: generated | authored` on one record with one layout
   schema and one renderer. The corpus never had two kinds.
2. **Sites are few; pages are many.** Per-artifact things are pages addressed by artifact refs, not site records. This
   dissolves the 13k-vs-21k granularity question rather than answering it.
3. **Ref-as-identity for sources; a minted slug only for publication.** No opaque IDs for content, no site registry, no
   second index. Prior art already decided this.
4. **A link is a reference, not a grant.** Published set = explicit scope ∩ audience ceiling, never reachability. Four
   edge types; only `mount`/`embed` bear scope; only they must form a DAG.
5. **Draw the page boundary at the privacy boundary.** Prompts are tabs of plans, chats are tabs of agents, commits are
   rows, artifact files are gallery content.
6. **Ship the addressing prerequisite first, then a renderer spike over xprompts, then the index.** Phase 0 and Phase 1
   are each independently valuable and cheap.
7. **Keep the rest of the original note.** Extend `sase_gateway`, Python rendering, commit-pinned locks, the privacy
   ceiling and the `/sase_repo`-style skill contract all survive the collapse — several get simpler.

**The unifying idea:** SASE already publishes a cross-repo hypertext of per-artifact pages, hub indexes and derived
links, and it already ships one working corpus→HTML renderer. Sites should be the HTML rendering, the retrieval index
and the publication envelope for that existing graph — one kind of site, many pages, no second content model.

---

## 6. Open questions

1. **Which corpus proves the model?** This report recommends xprompts/skills (cheapest, most shareable, renderer already
   exists). Plans or beads would be more useful sooner but need the index first. Worth an explicit call.
2. **Should the `sase` project's own site be public?** A strong SASE-on-SASE demo, and much of the corpus is already in
   public sidecars — but it publishes ~3,005 transcripts unless explicitly excluded. §3.3 makes this a one-place
   decision rather than a diffuse risk.
3. **Multi-machine truth.** The agents sidecar is owner/machine-sharded, so a site built on one machine reflects only
   synced state. The source lock makes that visible; the product answer ("whose view is this?") is undecided. See
   `202605/multi_machine_sync.md`.
4. **How does a teammate actually receive a site?** Both reports specify the machinery (bundle, Worker, sidecar) but not
   the default. Phase 1's single self-contained HTML file is the cheapest real answer and worth pricing against a
   deployed Worker before Phase 7.
5. **Cross-project hubs.** Straightforward once page identity is a ref (the ref already carries `project`), but it
   changes the URL scheme. Defer — only 3 projects are enabled and `sase` dominates.
6. **`sase ace web`** (`202605/textual_serve_ace_web_access.md`) remains dramatically cheaper than any phase here if the
   real need is "read SASE in a browser" rather than "publish a shareable site." Decide it explicitly, not by omission.

---

## Sources

**External precedent:**
[Backstage software catalog](https://backstage.io/docs/features/software-catalog/system-model) ·
[Backstage descriptor format](https://backstage.io/docs/features/software-catalog/descriptor-format) ·
[Backstage: creating the catalog graph](https://backstage.io/docs/features/software-catalog/creating-the-catalog-graph/) ·
[Datasette pages and URLs](https://docs.datasette.io/en/stable/pages.html) ·
[Notion: public pages and web publishing](https://www.notion.com/help/public-pages-and-web-publishing) ·
[WordPress post types](https://developer.wordpress.org/themes/classic-themes/basics/post-types/) ·
[RFC 8288 Web Linking](https://www.rfc-editor.org/rfc/rfc8288.html) ·
[IIIF Presentation API 3.0](https://iiif.io/api/presentation/3.0/) ·
[OCI image index](https://specs.opencontainers.org/image-spec/image-index/) ·
[RFC 9110 `If-Match`](https://www.rfc-editor.org/rfc/rfc9110.html#name-if-match) ·
[MCP resources](https://modelcontextprotocol.io/specification/2026-07-28/server/resources) ·
[MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview) ·
[TiddlyWiki](https://en.wikipedia.org/wiki/TiddlyWiki)

**Prior SASE research:** `202607/sase_sites_platform/sase_sites_platform.md` ·
`202607/artifact_refs_and_inspector/artifact_refs_and_inspector.md` (decisive on identity) ·
`202607/sase_mobile_app_motivation.md` · `202605/markdown_to_html_rich_artifacts.md` ·
`202605/textual_serve_ace_web_access.md` · `202604/sase_web_client_research.md` · `202605/multi_machine_sync.md`

**SASE (`af4295179`):** `src/sase/artifact_ref_models.py:12` · `src/sase/artifact_refs.py` · `src/sase/artifact_cli/` ·
`src/sase/core/artifact_file_query_facade.py` · `src/sase/core/artifact_file_types.py` · `src/sase/sdd/_store_types.py` ·
`src/sase/sdd/hosted_links.py` · `src/sase/xprompt/{catalog,_catalog_render,_catalog_sources}.py` ·
`src/sase/xprompt/catalog_template.html.j2` · `src/sase/xprompt/catalog_style.css` ·
`src/sase/agents_sync/rendering_*.py` · `src/sase/bead_pages/rendering*.py` · `src/sase/ace/tui/tab_order.py` ·
`src/sase/ace/tui/artifact_tabs.py` · `pyproject.toml` · `mkdocs.yml` · `docs/{cli,content_layout,query_language,ace,agents_sidecar,sdd_storage}.md`

**`sase-core`:** `crates/sase_core/src/artifact_ref/{wire,scanner}.rs` · `crates/sase_core/src/agent_scan/index.rs` ·
`crates/sase_core/src/agent_archive/mod.rs` · `crates/sase_core/src/bead/search.rs` ·
`crates/sase_gateway/src/daemon.rs:37` · `Cargo.toml:30`

**SASE long-term memory:** `memory/cli_rules.md` · `memory/rust_core_backend_boundary.md` ·
`memory/generated_skills.md`
