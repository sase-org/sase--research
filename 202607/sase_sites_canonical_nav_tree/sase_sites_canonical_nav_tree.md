---
create_time: 2026-07-30
updated_time: 2026-07-30
status: research
---

# SASE Sites: A Canonical Navigation Tree Over the Existing Link Graph

## Research question

Should SASE formalize "few sites, many pages, arbitrary linkage" with a Zettelkasten-inspired rule in which **every page
has exactly one parent** and **every page's ancestry terminates at a single root**, which the user adopts as their main
(index) SASE site? Is it worth pursuing, and if so, what exactly gets built?

## Provenance and method

Consolidates two independent reports written concurrently without knowledge of each other, plus this verification pass:

- `sase_sites_canonical_nav_tree__a.md` (agent `research.s.cdx`, codex/gpt-5.6-sol) — the rooted-spanning-tree
  formulation, the `nav_parent`-is-not-semantics discipline, privacy projection of breadcrumbs, validation and
  reparenting operations, external standards grounding (SKOS, RFC 8288, W3C breadcrumb/multiple-ways).
- `sase_sites_canonical_nav_tree__b.md` (agent `research.s.cld`, claude/opus) — corpus measurement, the DITA map/topic
  split, the total rank-decreasing parent resolver, and the observation that `subtree()` is what finally makes
  publication scope writable.
- This report — re-measured **every** load-bearing figure in `__b` (all reproduce), resolved the single real conflict
  between the two, and adds four things neither found: **Phase 0 is already shipped**, the authored-link count is
  effectively **zero** rather than 22, the proposed tree is **five levels of 250–1,213-wide fan-out** (so it does not
  deliver browsing), and the decisive precedent is **Sphinx `toctree`**, which supplies a third option for edge
  ownership that beats both reports' proposals.

Both extend the two 2026-07-29 notes, whose decisions survive unchanged except where noted:

- `202607/sase_sites_platform/sase_sites_platform.md` — extend `sase_gateway`, index first, commit-pinned versions,
  privacy as a first-order constraint.
- `202607/sase_sites_hub_and_pages/sase_sites_hub_and_pages.md` — one site type; **sites are few, pages are many**;
  ref-as-identity; the four-edge vocabulary; and the invariant *published set = explicit scope ∩ audience ceiling, never
  reachability*.

Measured 2026-07-30 at `c135dcbd6` against live sidecar checkouts. Nothing below is estimated.

## Executive summary

**Pursue it. Keep the single root — it is the best idea in the proposal and its real payoff is not the one you pitched.
Reject "one parent per *page*" as a field on pages, but also reject the alternative of a parent per *site*. Drop the
Zettelkasten name.**

Three findings drive the recommendation.

**1. The root's payoff is auditable publication scope, not navigation.** Both reports sell the tree on wayfinding;
`__b` alone spotted the stronger argument. The prior notes' central safety invariant left "explicit scope" as an
unspecified pile of widget queries. A single-parent acyclic tree gives scope a syntax a human can read in one line —
`scope: subtree(bead:sase-3a)` — and it is safe *precisely because* the nav tree is single-parent while the link graph
is not. Re-measured: **175,654 markdown links across 21,641 documents, 8.1 per document.** Reachability over that graph
means "everything." A subtree is bounded and auditable. That is the argument that justifies the work.

**2. The tree will not be browsable, and both reports over-claim that it will.** Neither computed the fan-out. Under
`__b`'s own resolver, the widest plan shard has **946 children** (202607) and four more sit between 249 and 823 — and
`__b` explicitly claimed `shard:` nodes "absorb … the 6 plan months," which absorbs the *count of shards*, not the
~900 children inside each. Add the 1,213-hood level and the 354-root bead level and the result is depth ~5 with five
separate levels wider than 250. Ship breadcrumbs and `subtree()`; render wide levels as filterable index pages; let
search do browsing. Do not invest in sharding rules to make a 946-wide level navigable.

**3. The single real conflict resolves to "both, layered," and `__b`'s own signature already admits it.** `__a` puts the
parent on the page (one canonical global tree); `__b` puts it on the site (a DITA map per site). But `__b` defines
`parent(page, site)` over a fallback table that is entirely **global and site-independent**, with site overrides as
perturbations. So both reports specify the same derived resolver and differ only on where *authored* placement lives.
A canonical global tree must exist anyway — otherwise a page reached by search has no breadcrumb and `subtree()` has no
well-defined tree to range over (§3.4 shows this is an outright circularity in `__b`'s model). Per-site trees are then a
thin overlay for the handful of curated framings that genuinely differ.

**The mechanism both reports missed:** let the **parent declare its children**, not the child declare its parent and not
the site declare the whole tree. That is Sphinx's `toctree` — single `root_doc`, every document must appear in some
toctree, a warning when one does not, `:orphan:` to opt out, and `:glob:` to derive whole subtrees by rule. It has run
for ~18 years over corpora the size of the Linux kernel's docs. It gives `__a` the canonical root and orphan diagnostic,
gives `__b` "author the top, derive the bottom," and adds **no field to 21,641 pages** — the exact objection `__b`
raised against `__a`. It also answers `__b`'s open question 5 better than either of `__b`'s two options: overrides live
in the ~50 structure pages where curation actually happens.

And SASE already runs both layers, at the two scales each suits: `mkdocs.yml`'s `nav:` is an authored site-scoped tree
(42 targets, rooted at `index.md`) whose *generated* corpus — the blog — is attached by a plugin supplying its own tree
rather than by 11 nav entries; the agents sidecar is a derived global containment tree with real breadcrumbs over
12,843 documents. Neither report noticed the pairing. It is in-repo evidence for exactly the layered answer.

---

## 1. Where the two reports agree (settled, not re-litigated)

Both reports independently reach these, and both are right:

- **Pursue the single root.** SASE has no front door: of four sidecars, only `agents` has a root README. Plans, beads
  and research have no entry point at all.
- **Ancestry must never bear scope or authorization.** Publishing the root must not publish descendants; a public page's
  private ancestor must degrade to a stub, never be pulled into the bundle to complete a breadcrumb. Notion's
  publish-subpages-by-default is the anti-pattern; the prior notes' invariant already inverts it.
- **The tree must never own identity or URLs.** Source identity stays the artifact ref; published identity is a slug
  minted at publication. Re-parenting must be a cheap, reversible edit — which is the only thing that makes an authored
  top-of-tree practical.
- **`nav_parent` is not semantics.** It is canonical placement for wayfinding — not "broader concept," not owner, not
  security parent, not `dcterms:isPartOf`. Every native relation (plan lineage, bead dependency, agent kinship, commit
  provenance, mentions) stays a separate typed edge even when one happens to coincide.
- **Arbitrary linkage is unchanged.** `relation` / `mention` / `link` stay non-scope-bearing with cycles allowed. Nothing
  about the tree constrains what may link to what.
- **Drop the Zettelkasten name** (§5), while building the structure.
- **Generalize the pattern already shipped in the agents sidecar** rather than inventing a stricter one.

---

## 2. Evidence

### 2.1 Every one of `__b`'s figures reproduces

`__a` cites no local measurements; `__b`'s are load-bearing, so all were re-measured independently. All reproduce within
live churn:

| Claim | `__b` | Re-measured | |
| --- | --- | --- | --- |
| Plan documents (excl. prompt snapshots) | 3,310 | **3,312** | ✓ |
| Plans with `PROMPT` / `COMMITS` / `AGENTS` / `BEAD` / `PARENT` | 2,792 / 1,066 / 764 / 544 / 67 | **2,793 / 1,069 / 764 / 544 / 67** | ✓ |
| Plans with **no** parent candidate | 2,126 (64.2%) | **2,128 (64.3%)** | ✓ |
| Plans with **2+** parent candidates | 129 (3.9%) | **129 (3.9%)** | ✓ |
| Beads: records / roots / parented / max depth / dangling | 2,369 / 354 / 2,015 / 3 / 0 | **2,369 / 354 / 2,015 / 3 / 0** | ✓ |
| Agents: hoods / runs / documents | 1,213 / 5,103 / 12,824 | **1,213 / 5,103 / 12,843** | ✓ |
| Markdown links / documents / per doc | 175,554 / 21,615 / 8.1 | **175,654 / 21,641 / 8.1** | ✓ |
| Enabled projects | 3 | **3** (`actstat`, `bob-cli`, `sase`) | ✓ |

`__b`'s example plan is also accurate: `202607/ace_commit_diff_render_freeze.md` carries `PROMPT`, `AGENTS` and
`COMMITS` but no `BEAD` and no `PARENT`. Also confirmed: the widest bead root is `sase-3a` with **88** direct children,
and `_root_id` in `src/sase/bead_pages/associations/_lineage.py` is exactly the cycle-safe walk `__b` describes.

**Treat `__b`'s evidence base as sound.** Where the two reports disagree on fact, `__b` wins on measurement.

### 2.2 Phase 0 is already shipped — both reports have this wrong

Both of today's reports, and yesterday's hub-and-pages note, treat the missing `bead:` / `agent:` artifact ref kinds as
a hard prerequisite. `__b` states it flatly: *"`Bead` and `Agent` ref kinds are a hard prerequisite: without them the
parent chain cannot be expressed as refs."*

It landed. `src/sase/artifact_ref_models.py:12` now reads:

```python
BUILTIN_ARTIFACT_REF_KINDS = ("commit", "chat", "bug", "file", "bead", "agent")
```

in `85b5b6421 feat(artifact-refs): add bead and agent resolution context`. Both resolve `status: exact` today —
`sase artifact path bead:sase-9z` returns the bead page, and `sase artifact show agent:bbugyi200.athena.9w` resolves.

**Consequence:** the parent chain *can* be expressed as refs now. The tree work is unblocked immediately and Phase 0
should be struck from the plan rather than scheduled. `sase site` remains greenfield (no such subcommand), so the
sequencing in §8 starts one phase later than either report assumed.

### 2.3 Authored associative links: not 22, effectively zero

`__b`'s Zettelkasten critique rests on there being only 22 authored `@refs`. The real number is lower in the way that
matters. A broader sweep across all six ref kinds over `plans/` + `research/` finds 38 ref-shaped strings in **9 files**
— and every one of those nine is a plan or research note *about the artifact-ref feature itself*:

```
plans/202607/fuzzy_artifact_ref_completion.md          plans/202607/artifact_ref_lsp_completion.md
plans/202607/artifact_ref_completion_target_project…   plans/202607/artifact_refs_and_prompt_bar.md
plans/202607/bead_and_agent_artifact_refs.md           plans/202607/artifact_ref_project_ref.md
plans/202607/artifact_ref_project_ref.md               research/202607/sase_sites_hub_and_pages/*.md
```

Several are deliberate non-examples (`@plans:202607/foo.md`, `@bead:sase-does-not-exist`, `@research:x.md`).

**There are zero authored refs used as genuine knowledge cross-links in the corpus.** The associative-linking practice
Zettelkasten depends on is not weak here — it is absent. This strengthens `__b`'s conclusion and sharpens it: adding a
parent pointer cannot import a practice that has never once occurred. The 175,654 links that *do* exist are machine-
derived — hood rosters, kinship sections, lineage graphs, header blocks, commit trailers, breadcrumbs.

### 2.4 Fan-out: the tree is not browsable, and that is acceptable

Neither report computed the shape of the tree it proposed. `__b` flagged the 1,213-hood level as "the widest node in the
corpus" and asserted that `corpus:` and `shard:` nodes "exist specifically to absorb the 354 bead roots and the 6 plan
months." The 6 months are absorbed; their contents are not. Measured children per plan shard:

| Shard | 202511 | 202602 | 202603 | 202604 | 202605 | 202606 | 202607 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Plan children | 1 | 56 | 249 | 670 | 823 | 566 | **946** |

So the proposed tree is **depth ~5 with five separate levels wider than 250**: one 1,213-wide hood level, one 354-wide
bead-root level, and three plan shards at 566–946. `__b`'s "wide trees are not navigable" critique is correct and applies
to five times more of its own design than it claimed. `__a` does not address fan-out at all.

This does not defeat the proposal — it corrects what the proposal is *for*:

> The tree's deliverables are **breadcrumbs** (orientation on arrival) and **`subtree()`** (auditable scope). Browsing a
> 21,641-document corpus is search's job, and the prior notes already fund search.

Two design consequences. **Do not** chase sharding rules to make a 946-wide level browsable — prefix and time sharding
are both arbitrary at that width and add depth without adding meaning. **Do** render wide levels as the filterable,
paginated corpus-index pages the prior note already specifies, and report the `… and N more` convention there.

---

## 3. The one real conflict: one canonical tree, or one tree per site?

Everything else between the two reports is complementary. This is the decision.

### 3.1 Both models already contain the same resolver

`__a` §4.2 proposes `nav.parent` on the page with `parent_source: authored | derived | fallback` and a table of
conservative generated defaults (project → corpus → artifact). `__b` §4.2 proposes `parent(page, site)` as a total
function with an ordered fallback chain per page kind.

`__b`'s fallback table is keyed **entirely on page kind** — `Bead` → `parent_id` → `corpus:beads@<project>`, `Plan` →
`BEAD` → `PARENT` → `shard:<YYYYMM>@plans` → `corpus:plans@<project>`, and so on. Not one row consults the site. The
`site` parameter exists only to admit authored overrides. So:

```text
parent(page, site) = site_override(page)  if present
                     global_derived_parent(page)  otherwise
```

**A global canonical tree is already present in `__b`'s design.** The reports differ only on where authored placement is
recorded, and on whether the global tree is a first-class user-facing object or an implementation detail.

`__b`'s strongest empirical argument — 64.3% of plans have no parent candidate — is therefore aimed at the wrong target.
It defeats a *semantic* parent field, which `__a` also explicitly rejects (`nav_parent` is not `broader`, not
`is_part_of`). It does not touch a *total* parent function with deterministic fallbacks, which is what both reports
build.

### 3.2 Three things only a canonical tree can do

**Breadcrumb on arrival.** With 21,641 documents and 175,654 mostly-derived links, the dominant arrival path is search,
and a search result is context-free. `__a`'s W3C grounding is right that a breadcrumb is what makes a hit interpretable
— but the breadcrumb has to exist *before* the reader picks a site. Under a strictly per-site tree, `sase site nav <ref>`
prints ancestry "in each site that contains it," which is a multi-answer: it relocates the ambiguity `__b` set out to
remove from "which parent?" to "which site?", and gives a page reached from search zero breadcrumbs until it is adopted
by some site. Neither report makes this argument; it is the strongest case for the canonical layer.

**A single front door.** The user's stated requirement is a root "the user should be able to use as their main (i.e.
index) sase site." That is a global object by construction.

**Corpus-quality measurement.** The fallback-parent count (2,128 plans, 64.3%) is only a coherent metric against one
tree. Per-site, it is 2,128 × *n*.

### 3.3 Two things only a per-site tree can do

`__b`'s framing case is real and `__a` has no answer to it: a release-readiness site wants plans under their **bead**; a
retrospective wants them under their **month**; an agent-performance review wants them under their **authoring agent**.
All three are legitimate. Measured, this matters for **129 plans (3.9%)** with 2+ candidates — small, but exactly the
pages a curated site is most likely to feature.

Second, per-site placement keeps pages context-free, which is the DITA property that makes reuse safe.

### 3.4 The `subtree()` circularity forces the answer

`__b`'s best contribution is `scope: subtree(<ref>)` as the primary publication-scope syntax. But under a strictly
per-site tree it is circular:

1. `publication.scope: subtree(X)` decides which pages the site contains.
2. `nav` is a facet of that site, ranging over the pages it contains.
3. `subtree(X)` is evaluated against `nav`.

Scope depends on nav, nav ranges over scope. Neither report addresses this. The resolution is a hard constraint that
also settles the conflict:

> **Evaluate `subtree()` against the canonical derived tree. Apply site-local nav overrides only to pages already in
> scope.** Overrides re-shape presentation; they never re-shape membership.

This keeps `subtree()` deterministic and reviewable, and it means the canonical tree must be a real, always-present
object — not a per-site artifact.

### 3.5 Resolution

**Two layers, and the canonical one is primary.**

| | Canonical tree | Site nav overlay |
| --- | --- | --- |
| Cardinality | Exactly one, always present | Zero or one per site |
| Origin | Derived by the rank-decreasing resolver | Authored |
| Covers | All 21,641 pages | A curated handful (~50) |
| Supplies | Breadcrumbs, orphan diagnostics, `subtree()` domain, the root site | Presentation order and framing for one site |
| May affect membership | Yes (via `subtree()`) | **No** |
| May affect identity or URLs | **No** | **No** |

---

## 4. The precedent neither report cited

### 4.1 Sphinx `toctree`: parent-declares-children

`__a` grounds itself in SKOS, RFC 8288 and W3C breadcrumbs; `__b` in Luhmann, Ranganathan, DITA and Wikipedia's category
graph. The closest working analogue to what SASE needs is none of these: it is **Sphinx**, which has shipped this exact
model for ~18 years over a large fraction of the world's technical documentation.

Sphinx has a single **`root_doc`** — *"the 'root' of the TOC tree hierarchy."* Every document *must* appear in some
`toctree`; Sphinx *"will emit a warning if it finds a file that is not included."* A document can opt out with the
file-wide **`:orphan:`** field, which lets it build while declaring it unreachable by navigation. And `toctree` accepts
**`:glob:`**, so a parent can enumerate a whole subtree by rule instead of by hand.

That is `__a`'s canonical root and orphan diagnostic, plus `__b`'s "author the top, derive the bottom," in one
battle-tested mechanism. The Linux kernel's documentation tree even went through an explicit *"mark orphan documents as
such"* pass — `__b`'s fallback-parent metric, performed by a real project at real scale.

Its most useful property is the one neither report considered: **the edge is declared by the parent.** There are three
possible owners of a nav edge, not two:

| Owner | Cost | Assessment |
| --- | --- | --- |
| **Child declares parent** (`__a`'s `nav_parent` field) | A field on 21,641 pages; a migration; per-page authoring burden | `__b`'s objection is fair |
| **Site declares whole tree** (`__b`'s `nav` facet) | Overrides scatter across sites; no breadcrumb outside a site; `subtree()` circularity | `__b`'s own open question 5 flags the scatter |
| **Parent declares children** (Sphinx `toctree`) | Edits confined to ~50 index/structure pages; globs derive the rest | **Recommended** |

Parent-declares-children wins because placement is a *curation* act and curation happens at the index page, which is
where a human is already looking when they decide a page's home. It adds nothing to leaf pages, keeps one canonical
tree, and makes the authored/derived split syntactic (`children: [explicit]` vs `children: {glob: …}`) rather than a
`parent_source` enum the renderer must interpret.

### 4.2 SASE already runs both layers, at the two scales each suits

Neither report noticed that the repo contains both proposals in production:

**`mkdocs.yml` is `__b`'s design.** A `nav:` block in the site config — an authored, ordered, site-scoped tree over
flat-addressed markdown, rooted at `index.md`. Measured: **42 markdown targets** listed for a **77-file** corpus. The
gap is instructive, not a defect:

| Not in `nav:` | Count | Why |
| --- | --- | --- |
| `blog/posts/*.md` | 11 | A **generated corpus attached by a plugin that supplies its own tree** — not 11 nav entries |
| `images/**.md` | 23 | Prompt/critique sidecars — **content, not pages** (exactly the prior note's artifact-files rule) |
| `agents_sidecar.md` | **1** | A genuine orphan: a real doc page reachable by URL only |

**The agents sidecar is `__a`'s design.** A derived global containment tree over 12,843 documents with real breadcrumbs:

```text
# Hood: 96
[Agent Hoods](../../../../../../README.md) / [bbugyi200](../../../../README.md) / [athena](../../README.md) / 96
```

rooted at a README reporting *Owners: 1 · Machines: 1 · Hoods: 1213 · Runs: 5103*, with **5,126** agent pages addressed
flat at `agents/<name>/README.md`.

The pairing is the empirical case for §3.5: **authored tree on top for the curated corpus; derived tree below for the
generated corpus; generated corpora attached by rule, not enumeration; media as content, not pages.** And `docs/`
already demonstrates the failure mode the orphan diagnostic prevents — one real page silently unreachable, because
MkDocs is not run with a strictness that would flag it.

One refinement the sidecar forces on both reports: hood, machine and user pages **are** path-addressed by tree position
(`users/<u>/machines/<m>/hoods/<h>/README.md`, with relative-path breadcrumbs). Only leaves are flat. That is safe
because derived containment never reparents. The sharper rule:

> **Derived spines may be path-addressed. Authored placements must not be.** Anything a human can move must be addressed
> independently of where it sits.

---

## 5. The Zettelkasten framing: build it, drop the name

Both reports say drop the name; `__b` argues it in most depth (Luhmann's archive was two slip-boxes with a ~3,200-entry
flat keyword register as its deliberate many-rooted entry point; Folgezettel is the part the Zettelkasten community
concluded was a paper artifact; Luhmann himself filed "Anpassungsfähigkeit" at two addresses). `__a` adds the sharpest
citation: Luhmann explicitly rejected systematic ordering by topic and later described the whole as *"not hierarchy, and
most certainly no linear structure like a book."*

The crispest statement of the problem is in neither report:

> **In Luhmann's system the branching number *was* the address.** Single-parenthood was load-bearing precisely because
> tree position was identity — the constraint paid for itself by making every card findable and citable forever. Both
> reports correctly insist SASE must **never** derive identity or URLs from tree position (§1). That deletes the only
> thing that made Folgezettel worth its cost. SASE would be importing the constraint after removing its benefit.

Combined with §2.3 — zero authored associative links, ever — the honest position is that Zettelkasten is neither the
authority for the structure nor an available practice. `__b`'s Ranganathan framing is the right substitute: hierarchy
asks *"where do I put this?"*, facets ask *"how do I describe this?"*, and faceted systems may use hierarchy **within
one facet**. The tree is one facet, not the model.

**Call it the canonical navigation tree.** Naming it Zettelkasten will make future contributors expect associative
note-taking semantics the system does not have and does not need.

---

## 6. Recommended model

### 6.1 Two structures over the same page nodes

Let `V` be page nodes and `r` the reserved root. Define a **total** navigation-parent function
`nav_parent: V \ {r} → V` such that repeatedly following it from any page reaches `r`. Separately define
`links ⊆ V × RelationType × (V ∪ SiteRef ∪ ExternalRef)`. Link cycles are allowed; parent cycles are not. The knowledge
structure is the union: a rooted spanning tree for orientation over a multigraph for meaning.

The root is a distinguished **authored site** whose `nav.children` is hand-written (a few dozen entries mounting the
generated project hubs alongside topic notes). This is the one place the Zettelkasten instinct genuinely belongs, and it
works there because it is small, curated and manual. Everything below it is derived and stays correct with no
maintenance.

A correction to `__b` on placement: the system-managed `home` **project** is a hidden workspace/claim construct, and the
`sase/` **home content namespace** in `docs/content_layout.md` is chezmoi-managed source for xprompts and memory. They
are different things, and neither is a project index. Host the root as a reserved authored site in the home content
namespace (`~/sase/sites/index/`), not as a project.

### 6.2 Derive parenthood with a rank-decreasing resolver

Adopt `__b`'s §4.2 table essentially verbatim — it is the most concrete artifact either report produced:

| Page kind | Parent resolution order (first hit wins; last always resolves) |
| --- | --- |
| Bead | `parent_id` → `corpus:beads@<project>` |
| Plan | `BEAD` → `PARENT` → `shard:<YYYYMM>@plans` → `corpus:plans@<project>` |
| Agent | family → hood → machine → user → `corpus:agents@<project>` |
| Family | hood → machine → user → `corpus:agents@<project>` |
| Document note | `shard:<YYYYMM>@<role>` → `corpus:<role>@<project>` |
| ChangeSpec | `corpus:changespecs@<project>` |
| Corpus / shard | `project:<key>` |
| Project | `root` |
| Root | ⊥ |

Rank nodes `page < shard < corpus < project < root`. Every step either follows a validated same-rank pointer
(`parent_id`, measured cycle-free) or strictly increases rank, so the relation is well-founded and **cycles and orphans
are unrepresentable in the derived tree** — a single index pass with no cycle check.

`__b` cites `_lineage.py` as precedent for this being a theorem rather than a lint. Read precisely, that code is the
*opposite* pattern: `_root_id` returns `None` on a cycle or dangling chain and the caller degrades to direct-only. That
is the better engineering answer for the part of the tree a human can edit, so keep both: **the derived tree is a
theorem; authored overrides get `__a`'s validation plus graceful degradation.** This reconciles `__a` §5 with `__b` §4.2
rather than choosing between them.

### 6.3 Authored placement lives in the parent

Per §4.1, structure and index pages declare their children:

```yaml
# A reserved authored site: the root. ~50 authored entries against 21,641 derived.
ref: sites:index/site.yml
source: authored
nav:
  root: true
  children:
    - page: sites:sase/index.md          # explicit
    - page: docs:topics/tui_perf.md      # a hand-written topic note
    - glob: corpus:plans@sase            # derived subtree, by rule
```

Rules:

- A page listed by exactly one parent gets that parent. Listed by two authored parents → build error with both traces.
- Listed by none → the resolver's derived fallback applies. So there is no orphan *state* in the canonical tree, only a
  **fallback-parent** state, which is a measurable quality signal rather than an error.
- A site may re-shape its own presentation tree, but only over pages already in scope (§3.4).

### 6.4 What ancestry must never do

Take these from `__a` unchanged; they are its strongest contribution and `__b` states them only in passing:

```text
published set = explicit site scope ∩ audience ceiling
```

- Publishing the root does **not** publish descendants absent an explicit, reviewed `descendants_of(root)` rule.
- A public page's private or out-of-scope ancestor renders as an authorized external link or a non-linking stub — it is
  never pulled into the publication to complete a breadcrumb. Extend `src/sase/sdd/hosted_links.py`'s existing
  degrade-to-unlinked-label discipline from "no remote" to "out of scope."
- Ancestry confers no permission, no semantics, no `dcterms:isPartOf`, and no identity.
- `nav_parent` joins the prior note's edge vocabulary as a **non-scope-bearing structural layer**, distinct from
  `mount`/`embed`, which bear scope and must form a DAG.

Emit `rel="up"` and `rel="index"` per RFC 8288 / the IANA registry, filtered through audience checks, plus backlinks, an
"appears in" list, and the stable ref-based canonical URL.

### 6.5 Validation

Per saved version: resolve the ref; resolve exactly one parent (root excepted); walk ancestors recording visited refs;
reject repeats with a human-readable cycle trace; require termination at `r`; verify sibling order; evaluate visibility
and site scope **separately**. Diagnostics: `duplicate_parent`, `missing_parent`, `cycle`, `wrong_root`,
`hidden_ancestor` (informational), and `fallback_parent` (a count and trend, never a gate — it would fail on 2,128
historical plans).

---

## 7. Example use cases

**Publish an epic without publishing the archive.** `sase-3a` is the widest bead root, with 88 direct children. Today,
scoping that for publication means hand-writing widget queries and hoping nothing links outward into the ~3,000 chat
transcripts. With the canonical tree: `scope: subtree(bead:sase-3a)`. One reviewable line. The reviewer verifies it by
walking a tree instead of reasoning about 175,654 edges; the privacy cut keeps chats as tabs of agents so a stray link
cannot pull them in; the audience ceiling independently vetoes anything from a private corpus.

**A breadcrumb that survives search.** A reader searches "commit diff freeze," lands on
`202607/ace_commit_diff_render_freeze.md`, and sees `SASE · sase · Plans · 202607 · …`. That plan has `PROMPT`, `AGENTS`
and `COMMITS` but no `BEAD` and no `PARENT` — the resolver's month-shard fallback supplies the crumb, so the 64.3% of
plans with nothing to say still orient the reader. This is the case a per-site tree cannot serve, because at the moment
of arrival there is no site.

**One plan, two framings.** In a *TUI performance* site, an authored override in a hand-written performance topic page
parents that same plan beside the other stall investigations. In a *July retrospective* site it keeps the month
fallback. Same page, same ref, same URL, two presentations — and because overrides apply only within scope, neither site
can silently enlarge the other. A page-scoped parent field would have forced a choice between two correct answers, for
the 129 plans where it actually comes up.

**A front door that is yours.** Three enabled projects; only `agents` has a root README today. The root site's
`nav.children` mounts the generated project hubs alongside a few dozen authored topic notes. Adding a project adds one
child branch, not a new top-level product concept.

**Corpus quality as a number.** `sase doctor` reports 2,128 plans (64.3%) parented by fallback. Setting `BEAD` on plans
during normal work drives it down and the tree deepens on its own — the same cleanup the Linux kernel docs performed
with `:orphan:`. Report the trend; never gate on it.

---

## 8. Sequencing

This is an **amendment to `sase_sites_hub_and_pages.md` §5, not a new phase list** — with one deletion.

| Phase | Change |
| --- | --- |
| ~~0 — Addressing~~ | **Strike it. Already shipped** (§2.2): `bead:` and `agent:` ref kinds resolve `exact` at `85b5b6421`. The parent chain is expressible as refs today. |
| **1 — Renderer spike** | Unchanged, and now the first bead. Generalize `sase xprompt catalog`; render xprompts/skills; add a hand-authored root page with breadcrumbs over ~20 pages. Cheapest possible test of whether breadcrumbs and a root index feel right before any index work. |
| **2 — Index** | Add a `nav_parent` column to the nodes table, populated by §6.2's resolver at build time. Rank makes it one pass, no cycle check. Index both directions for recursive queries. |
| **3 — Pages and the hub** | Breadcrumbs from the resolver; the root site becomes `sase site` with no argument. Report `fallback_parent` counts in the build summary per the `… and N more` convention. **Render wide levels as filterable index pages, not outlines** (§2.4). |
| **4 — Composition** | `nav` as a constrained `mount` with a distinct validator (tree, not DAG). Authored `children:` in structure pages; duplicate-parent detection. |
| **7 — Publication** | `scope: subtree(<ref>)` becomes the primary scope syntax, evaluated against the **canonical** tree (§3.4). The audience ceiling still applies on top — subtree selects, the ceiling vetoes. |

Two small additions elsewhere: a `sase doctor` fallback-parent trend check, and `sase site nav <ref>` to print canonical
ancestry (plus per-site overrides where they exist). No new CLI group.

---

## 9. Open questions

1. **Is the root above projects, or per project?** A personal index implies above, which pulls the deferred
   cross-project decision forward. Recommend above, hosted as a reserved authored site in the `sase/` home content
   namespace — not on the hidden `home` project (§6.1). Decide before Phase 3; it sets the URL scheme.
2. **Do authored `children:` lists live in page front matter or in the site spec?** §4.1 recommends the parent page,
   which is neither of `__b`'s two options. Worth a deliberate call, since it is the one place this report departs from
   both inputs.
3. **How wide is too wide before pagination becomes sharding?** §2.4 recommends filterable index pages over new tree
   levels. If a 946-child index page tests badly, the fallback is time-then-prefix sharding for plans and prefix
   sharding for the 1,213 hoods — but do not build it speculatively.
4. **Does `nav` supersede `mount` or sit beside it?** `nav` is a tree, `mount` a DAG, both bear scope. Leaning toward
   `nav` as a constrained `mount` with its own validator (`__b`'s answer; no reason to overturn it).
5. **Should MkDocs be run with strict nav checking?** `docs/agents_sidecar.md` is unreachable today (§4.2). Independent
   of sites, and a one-line fix that validates the orphan-diagnostic idea for free.

---

## Sources

**Prior SASE research:** `202607/sase_sites_platform/sase_sites_platform.md` ·
`202607/sase_sites_hub_and_pages/sase_sites_hub_and_pages.md` ·
`202607/artifact_refs_and_inspector/artifact_refs_and_inspector.md` ·
`sase_sites_canonical_nav_tree__a.md` · `sase_sites_canonical_nav_tree__b.md`

**Documentation-tree precedent (new to this pass):**
[Sphinx `toctree` directive](https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html) ·
[Sphinx: document isn't included in any toctree](https://documatt.com/sphinx-errors/1-document-isnt-included-in-any/) ·
[Linux kernel: mark orphan documents as such](https://lkml.iu.edu/hypermail/linux/kernel/1906.0/03680.html) ·
[Sphinx issue 9596 (orphan warning typing)](https://github.com/sphinx-doc/sphinx/issues/9596)

**Zettelkasten, hierarchy and facets:**
[Luhmann, *Communicating with Slip Boxes*](https://luhmann.surge.sh/communicating-with-slip-boxes) ·
[Niklas Luhmann Archive](https://niklas-luhmann-archiv.de/bestand/zettelkasten/tutorial) ·
[No, Luhmann Was Not About Folgezettel](https://zettelkasten.de/posts/luhmann-folgezettel-truth/) ·
[Folgezettel](https://zettelkasten.de/folgezettel/) ·
[Ranganathan / faceted classification](https://berkeley.pressbooks.pub/tdo4p/chapter/faceted-classification/) ·
[DITA: topicref hierarchies](https://dita-lang.org/dita/archspec/base/topicref-creating-hierarchies) ·
[Maps of Content](https://www.dsebastien.net/2022-05-15-maps-of-content/)

**Standards and web representation:**
[W3C SKOS Reference](https://www.w3.org/TR/skos-reference/) ·
[W3C WAI Breadcrumb Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/breadcrumb/) ·
[W3C WAI Multiple Ways](https://www.w3.org/WAI/tutorials/menus/multiple-ways/) ·
[RFC 8288 Web Linking](https://www.rfc-editor.org/rfc/rfc8288) ·
[IANA Link Relations](https://www.iana.org/assignments/link-relations/link-relations.xhtml) ·
[`dcterms:isPartOf`](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/terms/isPartOf/)

**Cautionary precedent:**
[Evolution of Wikipedia's Category Structure (arXiv 1203.0788)](https://arxiv.org/pdf/1203.0788) ·
[Notion: public pages and web publishing](https://www.notion.com/help/public-pages-and-web-publishing) ·
[Notion Page object](https://developers.notion.com/reference/page) ·
[Google Drive shortcuts](https://developers.google.com/workspace/drive/api/guides/shortcuts)

**SASE (`c135dcbd6`, re-measured 2026-07-30):** `src/sase/artifact_ref_models.py:12` (now includes `bead`, `agent`;
`85b5b6421`) · `src/sase/bead_pages/associations/_lineage.py` · `src/sase/sdd/plan_header_block.py` ·
`src/sase/sdd/hosted_links.py` · `src/sase/project_alias_mutations.py:53` · `mkdocs.yml:12-42` ·
`docs/content_layout.md` · `docs/` (77 md, 42 in nav) · `sase/repos/plans/` (3,312 plans, 2,813 prompt snapshots) ·
`sase/repos/beads/issues.jsonl` (2,369 beads, 354 roots, depth 3) · `sase/repos/research/` (309 notes) ·
`~/.sase/projects/gh_sase-org__sase/repos/agents/` (12,843 docs, 1,213 hoods, 5,126 agent pages, 712 families)

---

## Recommended solution

**Pursue the idea, as a single canonical navigation tree that is derived by default, authored at the top, and never
touches identity, permissions or publication.** Concretely:

1. **Keep the single root; make it a reserved authored site** in the `sase/` home content namespace, above the three
   enabled projects. Its `nav.children` is a hand-written few dozen entries mounting the generated project hubs
   alongside topic notes. This is the front door SASE lacks.

2. **Make the parent function total and rank-decreasing** (§6.2), so single-rootedness is a theorem in the derived tree
   rather than a lint. There is then no orphan state — only a `fallback_parent` state, which is a corpus-quality metric
   (2,128 plans today) and never a gate.

3. **Let the parent declare its children, not the child its parent, and not the site the whole tree.** Explicit
   `children:` for the ~50 curated placements; `glob:` rules for the derived remainder. This is Sphinx's `toctree`, it
   adds no field to 21,641 pages, and it keeps overrides where curation actually happens.

4. **Add a thin per-site nav overlay for framing only.** It re-shapes presentation for pages already in scope; it never
   changes membership, identity or the canonical breadcrumb. This buys `__b`'s release-vs-retrospective case for the 129
   genuinely ambiguous plans without giving up a canonical answer for the other 3,183.

5. **Make `scope: subtree(<ref>)` the primary publication-scope syntax, evaluated against the canonical tree.** This is
   the real payoff: it turns "publish this much and no more" into one auditable line, and it is safe only because the nav
   tree is single-parent while the 175,654-edge link graph is not.

6. **Keep ancestry inert.** `published set = explicit scope ∩ audience ceiling`. No permission inheritance, no
   descendant publication, no tree-derived URLs; out-of-scope ancestors degrade to stubs. Derived spines may be
   path-addressed because they never reparent — authored placements may not.

7. **Set expectations honestly: the tree delivers breadcrumbs and auditable scope, not browsing.** Five levels are
   wider than 250 nodes and the widest is 946. Render those as filterable index pages and let search do discovery.
   Do not build sharding rules speculatively.

8. **Sequence: strike Phase 0 (already shipped), start with the renderer spike**, then `nav_parent` in the Rust index,
   then breadcrumbs and the root, then `subtree()` scope at publication.

9. **Call it the canonical navigation tree, not Zettelkasten.** Luhmann's single-parent addressing paid for itself only
   because tree position *was* identity — which SASE must not replicate — and the associative-linking practice that made
   his system work has never once occurred in this corpus (zero authored cross-reference `@refs`). Build the structure;
   borrow the name from nobody.
