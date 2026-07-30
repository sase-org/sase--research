---
create_time: 2026-07-30
updated_time: 2026-07-30
status: research
---

# SASE Sites: Should Pages Form a Single-Rooted Zettelkasten Tree?

## Research question

The sites design has converged on "few sites, many pages, arbitrary linkage." Should that be formalized further with a
Zettelkasten-inspired structure in which **every page has exactly one parent** and **every page's ancestry terminates at
a single root node**, which the user adopts as their main (index) SASE site? Is this worth pursuing, and if so, what
exactly should be built?

## Provenance and method

This note extends, and does not re-litigate, the two prior reports:

- `202607/sase_sites_platform/sase_sites_platform.md` — index-first, extend `sase_gateway`, commit-pinned versions,
  privacy ceiling, `/sase_repo`-style skill contract.
- `202607/sase_sites_hub_and_pages/sase_sites_hub_and_pages.md` — one site type, `source: generated | authored`, **sites
  are few and pages are many**, ref-as-identity, the four-edge vocabulary, and the invariant *published set = explicit
  scope ∩ audience ceiling, never reachability*.

Everything in those notes survives this one. What is new here is a measurement pass over the actual corpus to test
whether a single-parent tree is *derivable*, plus an assessment of whether "Zettelkasten" is the right authority to
borrow from.

All figures were measured on 2026-07-30 at `c135dcbd6` (sase) against the live sidecar checkouts. Nothing below is
estimated.

## Executive summary

**Pursue it — but not as stated, and not under that name.**

The proposal contains one genuinely load-bearing idea, one framing that will mislead you, and one detail that will cause
real damage if implemented literally.

- **Load-bearing and correct: the single root.** SASE has no front door. A guaranteed root is cheap, and — the part that
  is easy to miss — it is what finally makes *publication scope* expressible as a subtree instead of a hand-maintained
  list of queries. That is the hardest unsolved problem in the prior two notes, and the tree solves it. This alone
  justifies the work.
- **Misleading: "Zettelkasten."** Zettelkasten's engine is *dense human-authored associative links*. Measured: the
  corpus contains **22 authored `@refs`** across 3,615 plans and research notes. Its ~175,554 links are **derived**, not
  authored. Meanwhile the one part of Luhmann's system that *was* single-parent — the Folgezettel branching address — is
  precisely the part the Zettelkasten community concluded was an artifact of paper and should not be ported to digital
  systems. You would be importing the discarded half and skipping the engine.
- **Damaging if literal: "every *page* has one parent."** Measured: **64% of plans (2,126 / 3,310) have no semantic
  parent candidate at all**, and where candidates exist they frequently conflict. Making parenthood a property of the
  *page* forces a canonical choice that the data cannot supply and that different sites legitimately want to answer
  differently.

The fix is a one-word change with large consequences: **the parent belongs to the site, not to the page.** This is
DITA's map/topic split — topics are context-free and reusable; the *map* imposes the hierarchy, and one topic may sit in
many maps. It preserves your single root, preserves arbitrary linkage, and removes the forced-choice problem entirely.

The strongest finding of this pass: **you have already built this, twice, and the version you shipped is better than the
one you are proposing.** The agents sidecar publishes a single-rooted containment tree with real breadcrumbs
(`Agent Hoods / bbugyi200 / athena / 96`) *while addressing every agent page by a flat, tree-independent name*. The bead
store maintains a cycle-safe `parent_id` forest with a `_root_id` walk while addressing every bead page flatly. Both
separate the navigation tree from page identity. Generalize that pattern; do not replace it with a stricter one.

---

## 1. Evidence base (all measured 2026-07-30, `c135dcbd6`)

### 1.1 Is a single parent derivable? Only for two corpora out of four

| Corpus | Documents | Single semantic parent derivable? | Measured |
| --- | --- | --- | --- |
| **Beads** | 2,369 | **Yes** | 2,015 (85%) carry `parent_id`; **354 roots**; **0 cycles**; **0 dangling chains**; max depth **3** |
| **Agents** | 5,464 agent pages + 712 families | **Yes, to hood level** | Containment tree `users(1)/machines(1)/hoods(1,213)`, depth 5; agent pages themselves live *flat* |
| **Plans** | 3,310 (excl. 2,815 prompt snapshots) | **Mostly no** | See below |
| **Research / document roles** | 305 | **No** | Month shard only (`202602`–`202607`) |

The plan corpus is where the rule breaks. Header-block section presence across 3,310 plans:

| Section | Count | Usable as a parent? |
| --- | --- | --- |
| `PROMPT` | 2,792 | No — 1:1 child, already a tab per the prior note |
| `COMMITS` | 1,066 | No — outbound, plural |
| `AGENTS` | 764 | Weak — authorship, and **plural** |
| `BEAD` | 544 | Yes |
| `PARENT` | 67 | Yes — but only **2.0%** of plans |

Resolving those into parent candidates:

| Candidates present | Plans | Share |
| --- | --- | --- |
| **None** | **2,126** | **64.2%** |
| `AGENTS` only | 640 | 19.3% |
| `BEAD` only | 415 | 12.5% |
| `AGENTS` + `BEAD` | 62 | 1.9% |
| `AGENTS` + `BEAD` + `PARENT` | 62 | 1.9% |
| `BEAD` + `PARENT` | 5 | 0.2% |

Two conclusions, both important:

1. **For ~64% of plans the tree has nothing to say.** Any single-parent rule falls back to the month shard —
   a filing convention, not a semantic relationship. A tree that is 64% "filed under 202607" is a filesystem with
   breadcrumbs. That is *useful*, but it is not a knowledge structure and should not be marketed as one.
2. **Where the data is rich, it is ambiguous.** 129 plans (3.9%) carry two or more legitimate parents. The bead that
   motivated the plan, the plan it descends from, and the agents that wrote it are all real relationships; picking one
   as "the" parent discards the others as navigation.

### 1.2 The link graph is dense — and almost entirely machine-derived

| Corpus | Documents | Markdown links | Links / doc |
| --- | --- | --- | --- |
| Agents sidecar | 12,824 | 142,963 | **11.1** |
| Beads | 2,361 | 22,601 | **9.6** |
| Research | 305 | 1,131 | 3.7 |
| Plans (incl. prompts) | 6,125 | 8,859 | 1.4 |
| **Total** | **21,615** | **175,554** | **8.1** |

Against that: **inline authored artifact references across the entire plans + research corpus total 22** (14
`@research:`, 8 `@plans:`).

So the hypertext already exists and is dense — hood rosters, kinship sections, lineage graphs, header blocks, commit
trailers, breadcrumbs. It is generated. The "arbitrary linkage between pages" the proposal asks to allow is
**already there and already arbitrary**; what is missing is not permission to link, it is retrieval and a front door.

### 1.3 You already shipped the proposed structure — as a hybrid

`~/.sase/projects/gh_sase-org__sase/repos/agents/README.md` is a root node:

```
# SASE Agent Hoods
**Owners:** 1 · **Machines:** 1 · **Hoods:** 1213 · **Runs:** 5103
| User | Machines | Hoods | Runs |
| [bbugyi200](users/bbugyi200/README.md) | 1 | 1213 | 5103 |
```

and every hood page carries an ancestry chain back to it:

```
# Hood: 96
[Agent Hoods](../../../../../../README.md) / [bbugyi200](../../../../README.md) / [athena](../../README.md) / 96
```

This is the proposal, in production, today. Note carefully what it does **not** do: the agent rows inside that hood page
link *out of the tree* to flat addresses — `agents/bbugyi200.athena.96/README.md` and
`families/bbugyi200.athena.96.md#member-code`. The tree supplies orientation and roll-up; a flat namespace supplies
identity.

`src/sase/bead_pages/associations/_lineage.py` is the same shape on the other side: a cycle-safe `_root_id` walk whose
docstring already anticipates both failure modes — *"Cycles and dangling parent chains have no root and therefore remain
direct-only."* Empirically neither occurs (0 and 0), because `parent_id` is written through a validating CLI rather than
authored freely.

Two independent subsystems, same conclusion: **single-rooted tree for navigation, flat refs for identity.**

---

## 2. Critique

### 2.1 Zettelkasten is the wrong authority, and specifically the wrong half of it

The proposal reads Zettelkasten as "notes in a parent/child tree with links." That is close to inverted.

- **Luhmann's archive was not single-rooted.** It was two slip-boxes; the second alone had eleven top-level sections.
  The entry points were a *flat* keyword index (Schlagwortregister) of ~3,200 entries pointing into the middle of the
  structure — a many-rooted index, deliberately.
- **The branching address (Folgezettel) is the contested part.** The Zettelkasten community's long-running conclusion is
  that Folgezettel solved a *paper* problem — a card has to be physically somewhere — and that
  ["with links alone you can do what Luhmann had to achieve with the Folgezettel technique."](https://zettelkasten.de/posts/luhmann-folgezettel-truth/)
  Luhmann himself is quoted as saying it is *"not important where you store a Zettel as long as you can reference it
  from every other point."* The same source documents "Anpassungsfähigkeit" appearing at **two** addresses (21/3a7 and
  54/14z/1) — i.e. Luhmann broke single-parenthood when the content demanded it.
- **The known failure mode of Folgezettel is exactly your corpus's situation.** It "allows a note to be part of only one
  sequence with one incoming link" — which breaks "when you want to continue two disparate trains of thought that
  contain the same note." That is the 129 plans with competing parents, and it is the general case for a corpus whose
  entities participate in several orthogonal relationships at once.
- **The engine is missing.** Zettelkasten produces insight because a human authors a link at the moment of connection.
  SASE has 22 such links. Adding a parent pointer does not add the practice; it adds the skeleton of the part that was
  never the point.

Ranganathan framed the underlying choice precisely: hierarchy asks *"Where do I put this?"*, facets ask *"How can I
describe this?"* — and faceted systems
[may still use hierarchy *within one facet*](https://berkeley.pressbooks.pub/tdo4p/chapter/faceted-classification/).
That is the correct role for your tree: **one facet, not the model.**

**Recommendation: build the structure, drop the name.** Call it the *navigation tree* or *page tree*. Naming it
Zettelkasten will invite future contributors to expect associative note-taking semantics that the system does not have
and does not need.

### 2.2 "One parent per page" forces a choice the data cannot make

§1.1 quantifies this: 64% of plans have no candidate, 3.9% have several. Under a page-scoped parent you must pick one
canonical answer per kind, forever, for all consumers. But the right answer is consumer-dependent:

- A release-readiness site wants plans parented by **bead**.
- A retrospective wants plans parented by **month**.
- An agent-performance review wants plans parented by **authoring agent**.

All three are legitimate; none is "the" parent. A page-scoped parent field makes two of them second-class and pushes
them into ad-hoc queries.

### 2.3 A single root over a 354-root forest relocates the problem rather than solving it

Beads form a forest of **354 roots**, max depth **3**. Agents form a tree whose widest level is **1,213 hoods under one
machine**. Adding a synthetic root above these is one node and zero difficulty — but the result is a very shallow, very
wide tree, and wide trees are not navigable. The root's value comes entirely from the *intermediate* nodes you introduce
to absorb fan-out (project → corpus → shard). Those intermediates are the actual design work; the root is the trivial
part. Budget accordingly, and expect to shard the 1,213-hood level explicitly.

### 2.4 The invariant only holds if parenthood is derived, not authored

Wikipedia is the cautionary case. It nominally has a root (`Category:Contents`) and a category hierarchy, but
[in practice the categories "compose a densely-connected graph"](https://arxiv.org/pdf/1203.0788) with multiple parents,
cycles up to length 22, and early path convergence that causes spurious inheritance across unrelated branches. It got
there by letting humans author parenthood freely.

SASE's beads have zero cycles because `parent_id` goes through validation. The lesson is direct: **make the single-root
property a theorem, not a lint.** If the parent function is total and strictly decreasing over a well-founded ranking,
cycles and orphans become unrepresentable rather than merely reported. §4.2 specifies that function.

### 2.5 Do not let the tree own the URL space

If routes are derived from tree position, re-parenting a page breaks every URL already handed to someone. The prior note
already settled the alternative and it should be restated here as a hard constraint: **source identity is the artifact
ref; published identity is a slug minted at publication.** The tree determines *navigation, breadcrumbs and scope* — never
addresses. This also means re-parenting is a cheap, safe, reversible edit, which is what makes an authored top-of-tree
practical at all.

### 2.6 It forces the cross-project decision early

Both prior notes recommended deferring cross-project sites (only 3 projects are enabled; `sase` dominates). A single
global root *is* a cross-project construct. This is not a defect — a personal index above all projects is plainly what
you want — but it should be a deliberate call rather than a side effect. The system-managed `home` project
(`src/sase/project_alias_mutations.py:53`) and the `~/sase/` home namespace in `docs/content_layout.md` are the natural
place for it, and both already exist.

---

## 3. What the idea gets right — and why it is worth doing anyway

Stripped of the Zettelkasten framing, three real wins remain, and the second is bigger than the proposal claims.

**1. There is no front door.** 21,615 documents across four sidecars with no entry point. The agents sidecar has a root
README; plans, beads and research do not. That is a genuine product gap and the root fixes it.

**2. A tree makes publication scope expressible.** This is the strongest argument and it is not in the proposal. The
prior note's central safety invariant is *published set = explicit scope ∩ audience ceiling, never reachability* — and
it left "explicit scope" as an unspecified list of widget queries. A single-parent acyclic tree gives scope a syntax
that a human can read and audit in one line:

```
scope: subtree(bead:sase-26)     # 57 descendants, deterministic, auditable
```

Crucially this stays safe **because** the tree is single-parent: `subtree()` over the nav tree is *not* reachability
over the link graph. A subtree is bounded and computable; the link graph at ~8 edges per node is fully connected and
means "everything." The tree is what lets you write scope down without accidentally writing down the whole corpus. It
directly addresses the report's sharpest risk — 2,984 chat transcripts and 5,464 agent prompts.

**3. Orientation and quality signal.** Breadcrumbs on every page, already proven on hood pages. And with a total parent
function, a doctor check no longer reports *orphans* (impossible by construction) but **fallback parents** — pages that
landed on a month shard because no semantic parent existed. Today that check would report 2,126 plans, which is an
actionable corpus-quality metric: link plans to beads and the number falls.

---

## 4. Recommended solution

### 4.1 The one-word change: the tree is a facet of a site, not a field on a page

Adopt DITA's split, which is the mature version of this exact problem:
[a topic is context-free and reusable; the *map* establishes the hierarchy](https://dita-lang.org/dita/archspec/base/topicref-creating-hierarchies),
and one topic may appear in many maps while having exactly one parent *within each*.

```yaml
# Extends the single site record from sase_sites_hub_and_pages.md §4.1 — one new facet.
ref: sites:index/site.yml
source: authored
title: SASE
nav:                              # NEW. The navigation tree for this site.
  root: true                      # at most one site per scope declares this
  strategy: derived               # | authored | derived+overlay
  children:                       # authored top-of-tree
    - mount: sites:sase/site.yml
    - mount: sites:home/site.yml
    - mount: docs:topics/tui_perf.md      # a hand-written MOC-style topic note
```

What this buys:

- **Your single root, exactly as proposed** — the root site is the index site.
- **Multi-parenthood without ambiguity** — a plan sits under its bead in the release site and under its month in the
  retrospective site. Both are single-parent trees; neither wins globally.
- **No new field on 21,615 pages**, no migration, no per-page authoring burden.
- **`relation` / `mention` / `link` are unchanged** and remain non-scope-bearing, per the prior note. `nav` is simply
  the strictest member of the existing scope-bearing `mount`/`embed` family: a tree instead of a DAG.

### 4.2 Make single-rootedness a theorem

Define `parent(page, site)` as a **total** function with an ordered fallback chain per page kind. First hit wins;
the last entry always resolves.

| Page kind | Parent resolution order |
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

Assign each node a rank — `page < shard < corpus < project < root`. Every fallback step either follows a validated
same-rank pointer (`parent_id`, already cycle-free) or strictly increases rank. The relation is therefore well-founded:
**cycles and orphans are unrepresentable, not merely detected.** Rank is what turns §2.4's lint into a proof.

Two rules complete it:

- **Authored override, tree-local.** A site may set `nav.parent:` on any page it includes. This changes that site's tree
  only — never identity, never another site's tree. Expect ~50 such overrides against 21,615 pages: **author the top of
  the tree, derive the bottom.** (Luhmann's own ratio was ~3,200 index entries to ~67,000 notes.)
- **Fan-out is bounded by intermediates, not by the root.** The `corpus:` and `shard:` nodes exist specifically to absorb
  the 354 bead roots and the 6 plan months. The 1,213-hood level needs its own sharding rule — flag it explicitly rather
  than discovering it at render time.

### 4.3 Where this lands in the existing plan

This is an **amendment to `sase_sites_hub_and_pages.md` §4, not a new phase list.** Its phases stand as written; `nav`
attaches to three of them:

| Existing phase | Amendment |
| --- | --- |
| **0 — Addressing** | Unchanged, and still the right first bead. `Bead` and `Agent` ref kinds are a hard prerequisite: without them the parent chain cannot be expressed as refs. |
| **2 — Index** | Add a `nav_parent` column to the nodes table, populated by §4.2's resolver at build time. Rank makes it a single pass with no cycle check needed. |
| **3 — Pages and the hub** | Breadcrumbs from the resolver; the root site becomes `sase site` with no argument. Report fallback-parent counts in the build summary, per the `… and N more` convention. |
| **7 — Publication** | `scope: subtree(<ref>)` becomes the primary scope syntax, replacing enumerated widget queries. The audience ceiling still applies on top — subtree selects, the ceiling vetoes. |

Two small additions elsewhere: a `sase doctor` fallback-parent check, and `sase site nav <ref>` to print a page's
ancestry in each site that contains it. No new CLI group; no change to the record's other facets.

### 4.4 Example use cases

**Publishing an epic without publishing the archive.** `sase-26` has 57 descendants. Today, scoping that for
publication means hand-writing widget queries and hoping nothing links outward into 2,984 chat transcripts. With the
nav tree: `scope: subtree(bead:sase-26)`. It selects the 57 beads, their plans and their commits; the privacy cut keeps
chats as tabs of agents rather than independent pages, so they cannot be pulled in by a stray link; the audience ceiling
independently vetoes anything from a private corpus. One reviewable line, and the reviewer can verify it by walking a
tree instead of reasoning about a graph with 175,554 edges.

**One plan, two homes.** `ace_commit_diff_render_freeze.md` has `PROMPT`, `AGENTS` and `COMMITS` but no `BEAD` and no
`PARENT`. In the *TUI performance* site an authored override parents it under a hand-written performance topic note,
beside the other stall investigations. In the *July retrospective* site it falls back to `shard:202607@plans`. Same
page, same ref, same URL, two trees. A page-scoped parent field would have forced you to choose, and neither answer is
wrong.

**A front door that is yours.** The root site's `nav.children` is authored — a few dozen entries — mounting the
generated project hubs alongside topic notes you write by hand. That is the only place the Zettelkasten instinct really
belongs, and it works there precisely because it is small, curated, and manual. Everything below it is derived and stays
correct without maintenance.

**Corpus quality as a number.** The fallback-parent check reports 2,126 plans with no semantic parent (64%). Setting
`BEAD` on plans during normal work drives it down, and the tree deepens on its own. The metric is real work made
visible, not a lint to suppress.

---

## 5. Recommended solution (summary)

**Pursue the single root. Reject the page-scoped single parent. Drop the Zettelkasten framing.**

1. **Add a `nav` facet to the existing site record** — an ordered tree over pages, with at most one site per scope
   declaring `root: true`. The parent belongs to the site (a DITA map), not to the page (a topic). Keep every other
   decision from the two prior notes.
2. **Derive parenthood with a total, rank-decreasing function** (§4.2) so single-rootedness is guaranteed by
   construction. Allow tree-local authored overrides; expect ~50 of them. Author the top, derive the bottom.
3. **Do not let the tree own identity or URLs.** Refs remain identity; publication mints a slug. Re-parenting must stay
   free.
4. **Make `subtree()` the primary publication scope syntax.** This is the real payoff: it gives the prior note's safety
   invariant a syntax a human can audit, and it is safe precisely because the nav tree is single-parent while the link
   graph is not.
5. **Keep arbitrary linkage exactly as designed** — `relation`, `mention` and `link` stay non-scope-bearing. Nothing
   about the tree constrains what may link to what.
6. **Generalize the pattern already shipped in the agents sidecar** rather than inventing a stricter one. Hood
   breadcrumbs plus flat page addresses is the target design; it is already in production and already correct.

The corpus does not need a new organizing principle. It has 175,554 derived links, a validated bead forest, and a
working single-rooted containment tree. What it lacks is a front door, retrieval, and a way to write down "publish this
much and no more." The nav tree delivers the first and the third; the index from the prior notes delivers the second.

---

## 6. Open questions

1. **Is the root above projects or per project?** A personal index implies above, which pulls the deferred cross-project
   decision forward. The `home` project and `~/sase/` namespace are the natural host. Decide before Phase 3 — it sets
   the URL scheme.
2. **How is the 1,213-hood level sharded?** The widest node in the corpus. Prefix sharding, time sharding, and
   pagination are all viable; none is free.
3. **Does `nav` supersede `mount`, or sit beside it?** `nav` is a tree, `mount` a DAG, and both bear scope. One
   mechanism is simpler; two is more honest about the difference between navigation and composition. Leaning toward
   `nav` as a constrained `mount` with a distinct validator.
4. **Should the fallback-parent count be a `just check` gate?** It is a good metric and a bad gate — it would fail on
   3,310 historical plans. Recommend reporting only, with a trend in `sase doctor`.
5. **Do authored overrides live in the site spec or beside the page?** Site spec keeps pages context-free (the DITA
   answer) but scatters overrides across sites. Beside-the-page centralizes them but reintroduces the page-scoped field
   this note argues against. Recommend the site spec.

---

## Sources

**Zettelkasten and its structure:**
[No, Luhmann Was Not About Folgezettel](https://zettelkasten.de/posts/luhmann-folgezettel-truth/) ·
[Folgezettel](https://zettelkasten.de/folgezettel/) ·
[The Folgezettel Conundrum](https://medium.com/@ethomasv/the-folgezettel-conundrum-20b14dc986ec) ·
[Linking many notes | Hierarchy in index cards/hubs](https://forum.zettelkasten.de/discussion/1661/linking-many-notes-hierarchy-in-index-cards-hubs-islands-of-knowledge) ·
[Indexed references vs. tags (Andy Matuschak)](https://notes.andymatuschak.org/z6ztEgzqZichYTJgabhYQLn4UY4FbC1JMH394)

**Hierarchy, facets, and maps:**
[Ranganathan / faceted classification](https://berkeley.pressbooks.pub/tdo4p/chapter/faceted-classification/) ·
[Faceted classification (Wikipedia)](https://en.wikipedia.org/wiki/Faceted_classification) ·
[DITA: how topicref elements establish hierarchies](https://dita-lang.org/dita/archspec/base/topicref-creating-hierarchies) ·
[DITA linking](https://docs.oasis-open.org/dita/v1.2/os/spec/archSpec/ditalinking.html) ·
[Maps of Content for better knowledge graphs](https://www.dsebastien.net/2022-05-15-maps-of-content/) ·
[Org-roam manual](https://www.orgroam.com/manual.html)

**Cautionary precedent:**
[Evolution of Wikipedia's Category Structure (arXiv 1203.0788)](https://arxiv.org/pdf/1203.0788)

**Prior SASE research:** `202607/sase_sites_platform/sase_sites_platform.md` ·
`202607/sase_sites_hub_and_pages/sase_sites_hub_and_pages.md` ·
`202607/artifact_refs_and_inspector/artifact_refs_and_inspector.md`

**SASE (`c135dcbd6`, measured 2026-07-30):** `src/sase/bead_pages/associations/_lineage.py` ·
`src/sase/bead/model.py:55,78-83` · `src/sase/sdd/plan_header_block.py:28-33` · `src/sase/sdd/plan_header_writes.py` ·
`src/sase/agents_sync/rendering_kinship.py` · `src/sase/project_alias_mutations.py:53` ·
`docs/content_layout.md` · `sase/repos/beads/issues.jsonl` (2,369 beads) · `sase/repos/plans/` (3,310 plans) ·
`sase/repos/research/` (305 notes) · `~/.sase/projects/gh_sase-org__sase/repos/agents/` (12,824 docs, 1,213 hoods)
