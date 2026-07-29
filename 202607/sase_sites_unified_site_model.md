---
create_time: 2026-07-29
updated_time: 2026-07-29
status: research
---

# SASE Sites: One Generic Site, Addressed By Artifact Reference

## Research question

The consolidated note `202607/sase_sites_platform/sase_sites_platform.md` recommends **two site kinds** — a generated
`project` portal and an agent-authored `custom` site. Should SASE instead support **one generic site** that links to zero
or more other sites and artifacts, where the project site is produced by emitting a site per meaningful artifact (plans,
beads, agents) and linking them under a hub site that specifies tabs and layout?

## Verdict up front

**Yes — collapse the two kinds.** The single generic model is not a simplification of the prior design; it is a more
accurate description of what SASE already builds. But it is only safe and buildable with three corrections the proposal
does not yet contain:

1. **Identity must be the artifact reference, not a new ID space.** Otherwise "a site per artifact" means 13,000+ new
   durable records that must be kept in sync with the corpus — a second source of truth the size of the corpus.
2. **Links must never confer visibility.** In a densely linked single-type graph, publication-by-reachability would let
   one shared plan transitively publish 3,011 chat transcripts. Scope must be an explicit rule; reachability must never
   be one. This is the single most important guardrail, and the two-kind design was accidentally hiding the risk.
3. **"A site exists for every artifact" is a logical claim, not a build claim.** Sites are addressed always and
   materialized by scope. Without this distinction the model reads as "render 21,452 HTML files," which the prior
   research correctly rejected.

With those three, `project` vs `custom` dissolves into a `source: generated | authored` field on one record, and the
whole feature becomes one addressing scheme, one index schema, one renderer, and one publication envelope.

Everything below marked *verified* was measured or read at `c40aa7f9f` (sase) and the current `sase-core` checkout.

---

## 1. What the two-kind split was actually encoding

The prior note's `project`/`custom` distinction bundles three independent axes into one enum. Separating them is what
makes the collapse work.

| Axis | Question it answers | Is a *type* the right tool? |
| --- | --- | --- |
| **Provenance** | Was this derived from the corpus, or written by hand? | **No** — a field (`source: generated \| authored`). Both render through the same pipeline. |
| **Structure** | Is this a leaf page or an index/hub over other pages? | **No** — composition. A leaf is a site with one tab; a hub is a site whose tabs are queries. |
| **Publication** | What is the unit you share, version, and grant access to? | **Yes** — but as an *optional facet on any site*, not as a second content kind. |

The prior design used one enum for all three, which is why it needed two renderers, two identity stories, and two privacy
stories. The user's proposal correctly identifies that provenance and structure do not deserve types. The correction it
still needs is that **publication does deserve its own machinery** — just not its own *kind*.

---

## 2. SASE already ships this model, in Markdown

This is the strongest argument for the proposal, and neither prior report made it: the per-artifact-page-plus-hub graph
is not a new architecture. It is running in production today, cross-repo, deterministic, and already hyperlinked.

**Verified counts (this machine, `sase` project, 2026-07-29):**

| Corpus | Count | Shape already generated |
| --- | --- | --- |
| Agent pages | **5,407** dirs | `agents/<global-name>/README.md` + `chat.md`, `prompt.md`, `meta.json`, `commits.json`, `state.json` |
| Family pages | **708** | `families/<name>.md` |
| Bead pages | **2,320** | `pages/<epic>/<bead>.md` with lineage Mermaid, phases, deps, commits, agents |
| Plan documents | **3,308** | `<YYYYMM>/<name>.md` |
| Prompt snapshots | **2,805** | `<YYYYMM>/prompts/<name>.md` (1:1 with a plan) |
| Chat transcripts | **3,011** | `agents/<name>/chat.md` (1:1 with an agent) |
| Research documents | **302** | document-role sidecar |
| Project docs | **77** | `docs/` |
| Agents sidecar total | 33,839 files | 12,639 `.md` |
| **Markdown total** | **~21,452** | |

**The hub node already exists.** `src/sase/agents_sync/rendering_index_pages.py` renders a five-level hub chain — root →
owner → machine → hood → family → agent — and every agent page opens with a breadcrumb across it:

```markdown
# Agent: 9w

[Agent Hoods](../../README.md) / [bbugyi200](../../users/bbugyi200/README.md) /
[athena](../../users/bbugyi200/machines/athena/README.md) / [9w](.../hoods/9w/README.md) /
[9w](../../families/bbugyi200.athena.9w.md) / 9w
```

**The cross-artifact edges are already written down as hyperlinks.** Verified:

- **2,784 plans** carry a header block linking to their prompt, agents, and commits — with agent links pointing at the
  hosted sidecar page and commit links at GitHub:

  ```markdown
  - **PROMPT:** [202607/prompts/…](prompts/….md)
  - **AGENTS:**
    - [bbugyi200.athena.9m](https://github.com/sase-org/sase--agents/blob/main/agents/bbugyi200.athena.9m/README.md)
    - [bbugyi200.athena.9m--code](https://github.com/…/families/bbugyi200.athena.9m.md#member-code)
  - **COMMITS:**
    - [cb9deb0](https://github.com/sase-org/sase/commit/cb9deb0…) — fix: guard remote SDD creation and plan routing
  ```

- **Commit trailers carry reference-style links into the sidecars.** Verified over 11,307 commits: **2,064**
  `SASE_AGENT=`, **742** `SASE_PLAN=`, **1,632** `SASE_MACHINE=`, **71** `SASE_BEAD=` (recent). Each renders as a
  markdown reference link to the bead page or agent page. *(Note: the trailers use `=`, not `:`; the prior note's
  `SASE_BEAD`/`SASE_AGENT` citation is correct in substance.)*

- **The TUI already has a per-artifact reader.** `docs/ace.md:195` — `Enter` on a plan, bead, phase, archived document,
  or chat opens the preview reader, and "when ACE knows a canonical artifact reference, the title shows that logical
  reference beside the resolved local path." The TUI's unit of viewing is *already* one artifact addressed by one ref.

**Conclusion:** SASE is already a cross-repo hypertext of per-artifact pages with hub indexes. What is missing is not a
second site kind. It is (a) an HTML rendering layer, (b) a retrieval index, and (c) a publication envelope. The user's
model names what exists; the two-kind model invents a distinction the corpus does not have.

---

## 3. External precedent

Four systems bear directly on "one generic node type with typed edges," and one is a cautionary tale.

**Backstage software catalog — validates the model, and validates *derived* edges.** Every entity kind shares one
envelope (`apiVersion`, `kind`, `metadata`, `spec`); only `kind` and the `spec` contents vary. Critically, the
`relations` field is **read-only and generated by catalog processors, never authored in YAML** — each relation is
`{targetRef, type}`, and relations are commonly emitted as bidirectional pairs. `System` and `Domain` are ordinary
entities that happen to act as grouping hubs. This is exactly the shape being proposed, from a system that has run it at
enterprise scale: one envelope, a kind discriminator, hub-ness as a property, and derived edges kept structurally
separate from authored spec.

**Datasette — validates per-record pages plus a JSON twin.** Datasette derives a page hierarchy from a SQLite database:
index → database → table → row, where "every row in every Datasette table has its own URL," foreign keys render as links
to related rows, and every page has a `.json` sibling. That is precisely the index-first, uniform-node, uniform-API
architecture the prior research recommended — and it demonstrates that a generic renderer over an index does not have to
feel generic.

**TiddlyWiki — the purest version.** "Everything is a tiddler: content, configuration, plugins, even the core code…
much like Unix's everything's-a-file philosophy, and it has the same benefits" — one set of tools works on everything.
The relevant lesson: uniformity pays off when the *tooling* is uniform (search, transclusion, linking), which is exactly
the case here (one index, one query surface, one reader).

**Notion — the cautionary tale.** Notion publishes a page to the web and "subpages are also published by default, along
with any of their subpages"; you must *opt out* per subpage to hide them. Notion's default is publish-by-reachability.
Applied to SASE's graph — where a plan links to its agents, agents link to their chats and prompts, commits link to beads,
beads link back to plans — that default publishes essentially the entire corpus from any starting point. **SASE must
invert it: default-closed, opt-in scope.**

**WordPress — the cost of generic-without-typed-columns.** All post types live in one `wp_posts` table discriminated by
`post_type`, with attributes in an EAV `wp_postmeta` table; the well-documented consequence is a query-performance cliff
past ~100,000 meta rows, with the standard fix being dedicated tables with real columns. The SASE edge count will land in
that range (§6.2), so the lesson is direct: **one generic node table is fine; a generic EAV attribute table is not.**

---

## 4. Correction 1 — identity is the artifact reference

### 4.1 The problem with "create a site per artifact"

If each per-artifact site is a durable record with its own opaque ID, version history, and deployment state, then the
site store becomes a ~13,000-row mirror of the corpus that must be created, renamed, garbage-collected, and reconciled
forever. That violates the principle both prior reports agreed on — *all truth stays in the sidecars; a site is a
projection.*

### 4.2 The fix

**The site's identity IS the artifact reference.** `plans:202607/sase_sites.md` is not a site that *points at* a plan; it
is that plan's site. Consequences:

- **No creation step** for generated sites. Every artifact has a site the moment it exists, for free.
- **No sync problem.** Delete the artifact, the site is gone. Rename it, the ref resolver already reports `drifted`.
- **No second namespace.** `sase site show plans:…`, `sase artifact show plans:…`, `@plans:…` in a prompt, and the LSP
  completion catalog all speak the same grammar.
- **Drift semantics are inherited, not invented.** `ArtifactRefResolutionStatus` already defines `exact`, `drifted`,
  `ambiguous`, `missing`, `unknown_kind`, `unknown_repo`, `unknown_project`.

This directly replaces the prior note's "durable opaque `id` + `slug`" (§5.2). Acknowledged tradeoff: path-derived IDs
are weaker than opaque IDs under rename. But the alternative is a permanently maintained 13k-row ref→ID mapping, and the
resolver's `drifted` status plus `sase artifact doctor` already cover the failure. Refs win on cost by a wide margin.

### 4.3 The prerequisite nobody has flagged: beads and agents are not addressable

**Verified gap.** `BUILTIN_ARTIFACT_REF_KINDS = ("commit", "chat", "bug", "file")` plus `Document { role }`
(`artifact_ref/wire.rs:41-45`). Document roles come from `document_sidecar_roles(store.split_sidecar_roles(),
include_plans=True)` — and `_store_types.py:44-48` **explicitly excludes `beads` and `agents`**: *"`beads` and `agents`
are never document roles."* `bug:` is `{project, number}` — a GitHub issue, **not** a bead.

So today there is **no way to write `@bead:sase-19.3` or `@agent:bbugyi200.athena.9w`.** The prior research's §5.1 node
list ("`bead`, `agent`, `family` …keyed by the existing `ArtifactRefKindWire` grammar") assumes an addressing scheme that
does not exist.

**Recommendation: extend `ArtifactRefKindWire` with `Bead { project, id }` and `Agent { name }` as a standalone,
pre-sites change.** It is small, it unblocks the entire model, and it is independently valuable *today* — artifact-ref
completion in ACE prompts, LSP semantic highlighting and diagnostics, `sase artifact show/path/open`, and prompt-launch
reference expansion all gain bead and agent addressing whether or not sites ever ship. This is the best first bead in the
epic.

### 4.4 Authored sites are artifacts too

Add a `sites` document role over `sase/sites/`, matching the canonical namespace in `docs/content_layout.md`
(`sase/xprompts/`, `sase/memory/`, `sase/repos/`). Then an authored hub is `sites:<name>/site.yml` and **every site —
generated or authored — is addressed by an artifact ref.** The addressing scheme has no special cases.

---

## 5. Correction 2 — a link is a reference, not a grant

### 5.1 Why the single-type model raises the stakes

The two-kind design contained the blast radius by accident: a `custom` site listed its widgets explicitly, and the
`project` site had per-corpus include flags. Collapse to one linked type and the natural reading becomes *"a site
includes what it links to"* — which, on this graph, means everything.

The graph is nearly fully connected. From any plan: → its prompt snapshot → its agents → each agent's chat, prompt, and
output variables → its commits → those commits' beads → those beads' other plans. Publishing by reachability from a
single plan would traverse into **3,011 chat transcripts and 2,654 agent prompt files**. `docs/agents_sidecar.md` is
explicit that the sidecar carries prompts, transcripts and sanitized output variables visible to anyone who can read it.

Notion's default (§3) is exactly this behavior. It is wrong here.

### 5.2 The invariant

> **A site's published set is `explicit scope rule ∩ audience ceiling`. Never graph reachability.**
>
> In-scope pages are published whether or not anything links to them. Out-of-scope pages are **not** published even when
> linked, and their inbound links render as **unresolved reference stubs** — a visible label, not a broken URL.

The stub behavior is not a new invention; it is the existing house style. `src/sase/sdd/hosted_links.py:1-8`: *"It is
local-only, never raises, and returns `None` instead of guessing, so a store without an authoritative hosted remote
degrades to an unlinked label instead of a broken URL."* Extend that discipline from "no remote" to "out of scope."

### 5.3 Three edge types, exactly one of them scope-bearing

| Edge | Origin | Stored? | Affects published set? |
| --- | --- | --- | --- |
| **`link`** | Derived from the corpus (plan header block, commit trailer, bead lineage, agent kinship, breadcrumb) | No — recomputed, like plan header blocks which are *"re-derived rather than accumulated"* | **No** |
| **`include`** | Authored in a site's layout: a widget sourcing a corpus/query, or embedding another site's tab | Yes, in the layout | **Yes — the only scope-bearing edge** |
| **`mention`** | An inline `@ref` in prose, found by `artifact_ref/scanner.rs` | No — resolved at render | **No** |

`link` is Backstage's read-only `relations` array (§3), and the separation is the same one Backstage found necessary:
derived relations must not be confused with authored spec.

This makes the single-type model **strictly safer than the two-kind model**, because the published set is one explicit
rule that `sase site check` can print, rather than an emergent property of which of two renderers ran.

---

## 6. Correction 3 — logical always, materialized by scope

### 6.1 Address every artifact; render what scope selects

"A site per artifact" is a statement about *addressing*, not about emitting files. Because the site ID is a ref (§4),
an unmaterialized site still resolves, still appears in search, and can be rendered on demand by the gateway. Static
export materializes only `scope ∩ audience`.

The prior research's build math survives unchanged: pre-render the ~6,600 high-value pages (plans + bead pages +
document-role notes + family pages), shard the long tail (prompt snapshots, agent READMEs, chats) into on-demand JSON,
shard the search index by corpus and month, and **report exclusions out loud** in the build summary per SASE's
`… and N more` convention.

### 6.2 Draw the site/tab boundary where the privacy boundary is

Not every artifact deserves its own URL. The right cut is the one that makes **"has a URL" coincide with "is a privacy
boundary"**:

| Artifact | Own site? | Rationale |
| --- | --- | --- |
| Plan (3,308) | **Yes** | Independently meaningful and shareable |
| Bead (2,320) | **Yes** | Already has a generated page with lineage |
| Agent (5,407) | **Yes** | Already has a generated page |
| Family (708) / hood / machine / owner | **Yes** | Existing hub pages |
| Document role, e.g. `research` (302) | **Yes** | Already a document corpus |
| xprompt / skill (41 / 17) | **Yes** | Small, high-value, genuinely shareable |
| ChangeSpec | **Yes** | PR-sized review records |
| Project | **Yes** | The hub |
| **Prompt snapshot (2,805)** | **No — a tab of its plan** | 1:1 with a plan |
| **Chat transcript (3,011)** | **No — a tab of its agent** | 1:1 with an agent, and the highest-risk corpus |
| **Commit (11,307)** | **No — a row/link** | Canonical home is already GitHub |

This removes ~17,000 nodes and — more importantly — means **you cannot link to a chat without linking to its agent.**
The sensitive corpora stop being independently addressable targets and become facets of a node whose audience is already
being decided. The agent-inclusion profiles from the prior research (`metadata` / `summaries` / `full`) then apply at
exactly one place: the agent site's tab set.

Node count lands near **13,000** — and the *published* count for a default project site is far smaller.

---

## 7. The unified model

### 7.1 One record

```yaml
# Identical shape whether generated or authored.
ref: plans:202607/sase_sites.md        # identity — an artifact reference, not a new ID
source: generated                       # | authored     (replaces kind: project | custom)
title: SASE Sites Platform
layout:                                 # resolved from a per-kind default; overridable
  tabs: [...]
links: [...]                            # DERIVED, read-only, never authored (Backstage `relations`)
publication:                            # OPTIONAL FACET — absent means "addressable, not shareable"
  scope: {...}                          # the only thing that decides what gets published
  audience: local
  version: ...                          # commit-pinned source lock
  target: ...
```

The `publication` block is the Notion insight (any page can be published) with the Notion default inverted (nothing is
published implicitly, and reachability grants nothing).

### 7.2 Layout is data; hub-ness is emergent

One renderer, one widget vocabulary, per-kind default layouts. The tabs are not invented — they are readable directly off
the existing Markdown renderers:

| Site kind | Default tabs | Source of the vocabulary |
| --- | --- | --- |
| Plan | Plan · Prompt · Agents · Commits · Beads | plan header block (`PROMPT`/`PARENT`/`AGENTS`/`COMMITS`) |
| Bead | Overview · Lineage · Phases · Dependencies · Commits · Agents | `bead_pages/rendering_tables.py`, `rendering_graph.py` |
| Agent | Summary · Prompt · Chat · Commits · Kinship | `agents_sync/rendering_agent_page.py`, `rendering_kinship.py` |
| Family | Members · Timeline · Commits | `rendering_family_page.py` |
| Document role | Document · Backlinks | `artifact_ref/scanner.rs` |
| **Project (hub)** | Overview · Plans · Beads · Agents · Artifacts · *one per document role* · Docs · Graph · Search | `ace/tui/artifact_tabs.py` (reuse `ARTIFACTS_SUBTAB_ORDER`, `ARTIFACTS_ACCENTS` verbatim) |

A leaf site has one tab with a `markdown` widget. A hub site has several tabs whose widgets are corpus queries. **Same
record, same renderer, same schema.** That is the entire content of "collapse the two kinds."

### 7.3 The project site

`sites:<project>/index` — a built-in default hub layout, materializable into `sase/sites/<project>/site.yml` via
`sase site init` when the user wants to customize it. This is precisely the user's *"structural/hub node that specifies
tabs and website layout,"* and it means the project portal is authored with the same machinery agents use, so it is
diffable, reviewable, and golden-testable rather than compiled into Python.

---

## 8. What changes in the prior research

| Prior decision | Status under the unified model |
| --- | --- |
| Do not build a new web server; extend `sase_gateway` | **Unchanged.** Four SASE research threads now agree. |
| Ship the search index first | **Unchanged, and simplified** — one `nodes` table + one `edges` table, no per-kind schema. |
| Markdown→HTML stays Python (`markdown-it-py` + `nh3`) per `202605/markdown_to_html_rich_artifacts.md` | **Unchanged.** |
| Save/deploy split with commit-pinned source locks | **Unchanged** — but attaches to the `publication` facet, not to a site kind. |
| Specify inside the shared `/api/v1` contract | **Unchanged, and easier** — `GET /sites/:project/node/:ref` is uniform across every node type. |
| Privacy ceiling, agent inclusion profiles, refuse-public-when-agents-private, consent prompts | **Unchanged, and better located** — they attach to the scope rule and the agent site's tab set (§6.2). |
| **Two kinds (`project` / `custom`)** | **Replaced** by `source: generated \| authored`. |
| **Durable opaque site ID + slug** | **Replaced** by the artifact ref (§4). |
| Node kinds "keyed by the existing `ArtifactRefKindWire` grammar" | **Blocked** — `bead:` and `agent:` do not exist. New prerequisite (§4.3). |
| SiteSpec widgets sourced via "the existing ACE query language" | **Needs correction** — see below. |

### The query-language correction

The prior note's §5.3 example uses `query: "bead:sase-26.*"` and claims data is *"sourced through the existing ACE query
language (`docs/query_language.md`, `sase_core::query`)."* **There is no such unified language.** Verified:

- `docs/query_language.md:1-11` — *"The ChangeSpec query language filters ChangeSpecs… This page documents ChangeSpec
  queries. **The Agents tab in ACE has a separate agent query language** with agent-specific property keys."* Its valid
  property keys are exactly `status`, `project`, `ancestor`, `name`, `sibling`.
- Bead search (`bead/search.rs:59,85`) and plan search are independent linear substring scans, not a shared query
  surface.

So `bead:sase-26.*` is not a valid query in any existing language. For v1, a widget must name its corpus explicitly:

```yaml
- kind: table
  corpus: beads
  filter: {epic: sase-26, status: open}
  columns: [id, title, status, size, agents, commits]
```

A genuinely unified query language over the site index is a fine Phase-N goal, but it must be scoped as new work rather
than assumed to exist. This is a real risk to the widget vocabulary as previously specified.

---

## 9. Costs and failure modes of the single-site model

Honest accounting of what the collapse costs.

1. **The word "site" gets overloaded.** If a plan has a site, "share this site" is ambiguous. *Mitigation:*
   `sase site list` defaults to sites **with a publication facet**, with `-a/--all` for the full ref-addressed universe —
   the same convention `sase agent list` already uses (running agents by default, `-a` includes DONE/FAILED).
   *Tripwire:* if you find yourself writing "the site's site," or adding a `--publishable` filter in more than two
   places, split the noun — `page` for the node, `site` for the publication envelope. Do not do it preemptively.
2. **Edge scale.** Rough order: ~14k plan-header edges + ~9k bead edges + ~43k agent kinship/breadcrumb edges + 2,877
   commit trailers + inline mentions ≈ **10⁵ edges over ~13k nodes.** Comfortable for SQLite, but past the point where
   WordPress's EAV pattern falls over (§3). *Mitigation:* typed columns, not an attribute table; indexes on
   `(src_kind, src_ref)` and `(dst_kind, dst_ref)`; FTS5 in separate virtual tables per
   `agent_archive/mod.rs:641`. Note the existing `~/.sase/agent_artifact_index.sqlite` is already **74 MB at schema
   version 19** — plan for the site index to be a peer of that, not a toy.
3. **Loss of a hand-curated portal.** *Mitigation:* ship the default hub layout as a built-in template (§7.3).
4. **Rename drift.** Path-derived IDs break on rename. *Mitigation:* existing `drifted` status + `sase artifact doctor`.
5. **Generic renderers tend toward bland.** *Mitigation:* per-kind default layouts (§7.2) plus reusing ACE's accents so
   web and TUI palettes cannot drift.
6. **`sase site` vs `sase artifact` must stay crisp.** State the rule in docs and in the skill:
   **`sase artifact` resolves the source; `sase site` renders and publishes the view.** Same refs, different verb space.

---

## 10. Revised phasing

**Phase 0 — Addressing (small, independently valuable).** Add `Bead` and `Agent` to `ArtifactRefKindWire`; add the
`sites` document role over `sase/sites/`. Ships value immediately in ACE completion, the LSP, prompt reference expansion,
and `sase artifact show/path/open` — with no sites, no HTML, no server. **Do this first regardless of whether sites
proceed.**

**Phase 1 — Index (medium).** `sase_core::site` — one nodes table, one edges table, FTS5, schema-versioned rebuild/upsert
/query following `agent_scan/index.rs`, incremental keying by Git blob SHA. `sase site index` + `sase site search`.
Delivers the genuinely missing capability (retrieval over 21k documents) with no renderer.

**Phase 2 — Renderer (medium).** Per-kind default layouts, one widget vocabulary, Python `markdown-it-py` + `nh3`
rendering. `sase site build <ref>` with an **explicit scope rule** and loud exclusion reporting. `local` audience only.
Prompts and chats are tabs, never nodes (§6.2).

**Phase 3 — Serve (medium).** `sites_http_enabled` on the daemon; `/sites` router; uniform `GET /sites/:project/node/:ref`
plus a `.json` twin per Datasette; SSE live-reload; specified in the shared `/api/v1` contract. ACE integration: open the
site for the selected row.

**Phase 4 — Authored hubs (medium).** `sase/sites/`, `sase site new/init/open/check`, the project hub template, and the
`/sase_sites` skill modeled on `/sase_repo`'s hard contract.

**Phase 5 — Publication facet (medium).** Commit-pinned source locks, `versions`/`export`/`deploy`, the audience ladder,
interactive-only consent per `docs/sdd_storage.md:118`, the refuse-public-when-agents-private rule, and a `sase doctor`
scope-vs-corpus drift check.

**Phase 6 — Freshness (small).** Post-commit incremental refresh following `bead_pages/publication.py`'s best-effort,
never-raises pattern and `agents_sync/publication_outbox.py`'s durable outbox.

---

## 11. Recommended approach

1. **Adopt the single generic site.** Drop `project`/`custom`. Replace with `source: generated | authored` on one record
   with one layout schema and one renderer. The corpus already has this shape (§2); the two-kind split describes a
   distinction SASE does not make.

2. **Make the artifact reference the site identity.** No opaque IDs, no slugs, no site registry for generated sites.
   `sase site show plans:202607/foo.md` and `@plans:202607/foo.md` name the same thing. Prerequisite: add `bead:` and
   `agent:` ref kinds and a `sites` document role — **ship this first, on its own** (§4.3).

3. **Enforce the containment invariant: a link is a reference, not a grant.** Published set = explicit scope ∩ audience
   ceiling, never reachability. Three edge types, only `include` is scope-bearing. Out-of-scope link targets degrade to
   unresolved stubs, reusing `hosted_links.py`'s never-guess discipline. Invert Notion's default.

4. **Address every artifact; materialize by scope.** "A site per artifact" is about addressing. Build emits ~6,600 pages
   by default and shards the tail, exactly as the prior research computed.

5. **Draw the node boundary at the privacy boundary.** Prompt snapshots are a tab of their plan; chat transcripts are a
   tab of their agent; commits are rows. This removes ~17,000 nodes *and* makes the 3,011 transcripts structurally
   unreachable as independent link targets.

6. **Make the project site an ordinary hub site with a shipped default layout** — `sites:<project>/index`,
   materializable into `sase/sites/<project>/site.yml` for customization. Same machinery agents use; therefore diffable,
   reviewable, and golden-testable.

7. **Keep everything else from the consolidated note.** Extend `sase_gateway`, index first, Python Markdown rendering,
   commit-pinned source locks, the privacy ceiling, and the `/sase_repo`-style skill contract all survive the collapse
   unchanged — several of them get simpler.

8. **Fix the query-language assumption before writing the widget spec.** There is no unified ACE query language today.
   For v1, widgets name their corpus explicitly; treat a unified index query language as separate, later, scoped work.

The unifying idea: **SASE already publishes a hypertext of per-artifact pages, hub indexes, and cross-repo links. Sites
should be the HTML rendering, the retrieval index, and the publication envelope for that existing graph — not a second
content model layered on top of it.** One generic site is the right call precisely because the corpus never had two
kinds.

---

## 12. Open questions

1. **Is `site` the right noun for a leaf node?** The tripwire in §9.1 defers the decision honestly, but it is worth
   deciding deliberately now rather than discovering it in the CLI. `page` (node) + `site` (publication) is the fallback.
2. **Should a generated site ever be writable?** v1 is read-only w.r.t. the corpus. But "an agent updates a bead from its
   site" is the natural next ask, and it should go through existing typed gateway operations, not a site mutation API.
3. **Multi-project hub.** A cross-project hub site is a straightforward composition once the node ID is a ref (the ref
   already carries `project`), but it changes the URL scheme. Defer — only 3 projects are enabled.
4. **Multi-machine truth.** The agents sidecar is owner/machine-sharded, so a site built on one machine reflects only
   synced state. The source lock makes this visible; the product answer ("whose view is this?") is still undecided. See
   `202605/multi_machine_sync.md`.
5. **Do xprompts and skills belong in the project site by default?** They are the most genuinely shareable artifacts in
   the corpus and the smallest; they may deserve to be the *first* corpus rendered rather than an afterthought.

---

## Sources

**External precedent:**
[Backstage system model](https://backstage.io/docs/features/software-catalog/system-model) ·
[Backstage descriptor format](https://backstage.io/docs/features/software-catalog/descriptor-format) ·
[Datasette pages and URLs](https://docs.datasette.io/en/stable/pages.html) ·
[Grok TiddlyWiki: Tiddlers](https://groktiddlywiki.com/static/Tiddlers.html) ·
[TiddlyWiki (Wikipedia)](https://en.wikipedia.org/wiki/TiddlyWiki) ·
[Notion: public pages and web publishing](https://www.notion.com/help/public-pages-and-web-publishing) ·
[WordPress post types](https://developer.wordpress.org/themes/classic-themes/basics/post-types/) ·
[Meta Box: custom post types in core](https://metabox.io/cpt-in-core/)

**Prior SASE research:** `202607/sase_sites_platform/sase_sites_platform.md` (and `__a`, `__b`) ·
`202607/sase_mobile_app_motivation.md` · `202605/markdown_to_html_rich_artifacts.md` ·
`202605/textual_serve_ace_web_access.md` · `202604/sase_web_client_research.md` · `202605/multi_machine_sync.md`

**SASE (`c40aa7f9f`):** `src/sase/artifact_ref_models.py` · `src/sase/artifact_refs.py` · `src/sase/artifact_cli/` ·
`src/sase/sdd/_store_types.py` · `src/sase/sdd/hosted_links.py` · `src/sase/agents_sync/rendering_index_pages.py` ·
`src/sase/agents_sync/rendering_agent_page.py` · `src/sase/bead_pages/rendering*.py` · `src/sase/ace/tui/artifact_tabs.py`
· `docs/ace.md` · `docs/cli.md` · `docs/configuration.md` · `docs/content_layout.md` · `docs/query_language.md` ·
`docs/agents_sidecar.md` · `docs/sdd_storage.md`

**`sase-core`:** `crates/sase_core/src/artifact_ref/{wire,scanner}.rs` · `crates/sase_core/src/agent_scan/index.rs` ·
`crates/sase_core/src/agent_archive/mod.rs` · `crates/sase_core/src/bead/search.rs` ·
`crates/sase_core/src/query/` · `crates/sase_core/src/commit_footer.rs`

**SASE long-term memory:** `memory/cli_rules.md` · `memory/rust_core_backend_boundary.md` ·
`memory/generated_skills.md`
