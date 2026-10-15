# Project Docs as Managed Memory: Consolidated Reading List

> **Research query:** Find articles and papers to inspire three possible moves for sase:
> migrating some memories (such as `sase/memory/macros.md`) into Markdown docs under
> `docs/`, making project documentation a first-class representation of memory that is
> managed the same way, and structuring the docs so agents can maintain them intuitively
> and scriptably. Finish with a ranked list of what to read.

![Infographic summarizing the report: give docs memory-style management (stable identity, owner and review date, audited reads, reviewed writes and drift checks); route agents from an always-loaded trigger through a short memory digest to the canonical docs section; untangle macros.md into existing core rules, a bound digest and docs/macros.md; give every page one Diátaxis job; turn maintenance into small, reviewable work; and the report's top five reads](project_docs_as_managed_memory_reading_list_infographic.png)

## Bottom line

**Making docs first-class memory is mostly about governance, not file location.** All
four reports agree. `docs/` needs the machinery that memory already has:

- a stable identity (path plus anchor)
- a typed purpose
- a discovery description written as a trigger
- an owner and a review date
- audited reads
- authored links
- a reviewed write path
- mechanical drift checks

Moving files into a different directory accomplishes none of this.

**"Migrate `macros.md` to docs" is really
[three different moves](#worked-example-of-migrating-the-macros-note):**

1. The **policy lines** in the note already live in core memory and in
   `decisions:host-owned-completion`. Delete those copies.
2. The **syntax cheat sheet** stays as a short agent-facing digest, but it becomes
   *bound* to the sections of `docs/macros.md` it summarizes, so drift is detected
   mechanically.
3. The **full contract** lives only in `docs/macros.md`. That page should be split by
   Diátaxis type, one page at a time.

**[Routing is the crux](#routing-decides-whether-docs-ever-act-as-memory), and the
evidence warns against retiring the digest.** The strongest warnings in the literature
are about routing, not structure:

- Coding agents rarely open classical documentation on their own. It makes up 10.6% of
  their documentation interactions; instruction files and agent notes make up 60.5%
  ([Gao & Chen](https://arxiv.org/abs/2608.20195)).
- In Vercel's evals, an on-demand docs skill was never invoked in 56% of cases
  ([Vercel](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)).

A docs corpus becomes memory only if something in always-loaded text sends agents into
it. The `macros.md` digest is that router today. Retiring it outright,
[as gem proposes](#retire-the-macros-digest-or-keep-it), would remove the router.

**For scriptable maintenance, build
[cheap mechanical checks](#scriptable-maintenance-through-mechanical-findings-and-small-agent-tasks)
first.** Turn their findings into small, single-page agent tasks. Avoid whole-corpus
"refresh the documentation" passes, which is what the `refresh_docs` chop does today.
[Keep a human review gate](#govern-agent-written-docs-the-way-memory-writes-are-governed)
on agent-written docs: in A-SAW's industrial study, 11 of 13 practitioners rejected agent
output that no human had reviewed.

**Read these five first:**

1. **Diátaxis** (the compass, plus "Diátaxis as a guide to work"): a type system and a
   one-page-at-a-time migration method
2. ***Software Engineering at Google*, ch. 10 "Documentation"**, with Google's docguide:
   owners, canonical docs, freshness metadata, "same change as the code," and deleting
   dead docs
3. **Gao & Chen, *From Agent Behaviour to Agent-Friendly Documentation*** (2026): what
   coding agents actually read and write
4. **Karpathy, *LLM Wiki***: the operating model for an agent-maintained Markdown
   knowledge base (ingest, query, lint, `index.md`, `log.md`)
5. **Tan, Wagner & Treude, *Detecting Outdated Code Element References***, plus the DOCER
   action: the most directly scriptable drift check, with prevalence data

Then read **KCS "Reuse is Review"** (a read is not a use, and a use is not a check) and
**A-SAW** (quality and trust come apart). The full ranked list is
[at the end](#ranked-reading-list).

## What sase has today

Verified on master `c2c2ffd4df`, 2026-10-15.

- **`docs/` corpus:** 90 Markdown files, 65,178 lines. 55 top-level pages, totaling
  59,507 lines.
- **Largest pages:** `ace.md` 9,771 lines; `configuration.md` 7,768; `macros.md` 4,082;
  `llms.md` 3,582. `llms.md` is the LLM-provider integration page.
- **Page metadata:** Only `index.md` and `getting_started.md` have YAML frontmatter.
- **Navigation:** Getting Started, The Basics, Beyond the Basics, The Nitty Gritty,
  Integrations, Reference. These sections group pages by depth, not by document type.
- **Reference pages:** `cli.md` and `configuration.md` are hand-maintained tables with no
  generation markers. `src/sase/config/sase.schema.json` and the CLI parser exist and
  could drive or check them.
- **`sase/memory/macros.md`:** 167 lines, 14.8 KB. A hand-written digest of
  `docs/macros.md`, already ending sections with "Full contract: `docs/macros.md` …"
  pointers. It also restates policy that lives in core memory and the `decisions` web.
- **Memory machinery:** `core`/`reference` types, trigger-style descriptions, authored
  `[[links]]`, webs, and audited `sase memory read` backed by a read log
  (`src/sase/memory/read_log.py`). Some memory is already generated, such as the
  `task_types` web.
- **Doc gardening:** The builtin `refresh_docs` chop runs an `update` agent ("Refresh the
  documentation for {project} …") and then a `polish` agent. Both prompts cover the
  whole repository, and there is no structured list of findings.
- **Governing decision:** `decisions:corpus-before-mechanism`: do not build retrieval or
  linking machinery ahead of a corpus that demonstrably needs it.

## Where the four reports agree

- **Use Diátaxis as the page type system.** All four reports recommend it. cdx, cld and
  grk adopt it incrementally; gem's restructure is
  [discussed below](#a-physical-directory-restructure-or-type-metadata).
- **"First-class" means shared governance, not shared location.** All four reports say
  this in different words. Docs should gain types, descriptions, audited reads, typed
  links, and a reviewed write path.
- **Generate what the code already knows, and author only the rest.** This is Martraire's
  *Living Documentation* argument, and cld, grk and gem all make it. cdx adds a caveat
  from DScribe: generation is reliable only for repeatable reference facts.
- **Run mechanical drift checks before LLM "refresh" passes.** cld, grk and gem cite Tan
  et al., DOCER and Markdoc; cdx cites AdDoc.
- **Decisions and glossary stay memory webs.** Render them into docs pages; do not
  flatten them into docs chapters. cld, grk and gem agree.
- **Write topics that work as page one.** Agents arrive through `grep`, path guesses and
  memory reads, so every topic must stand alone (Baker; cdx, cld, grk).
- **Transient work never becomes docs.** Plans, progress and current focus belong in
  beads, plans and goals (cld, grk).

## Disagreements and how I resolved them

### A physical directory restructure or type metadata

The question is whether to restructure `docs/` into Diátaxis directories.

- **gem:** move everything into `docs/reference/`, `docs/how-to/`, `docs/explanation/`
  and `docs/tutorials/`.
- **cdx, cld, grk:** add a `type:` field and improve one page at a time.

**Resolution: metadata first, page at a time.** Three reasons:

- Diátaxis's own ["guide to work"](https://diataxis.fr/how-to-use-diataxis/) warns
  against imposing an empty four-part structure before improving actual content.
- Every move breaks inbound links that agents and memory notes rely on.
- Navigation can later be *generated* from `type:`, which recovers the benefit of the
  folders without the churn.

### Retire the macros digest or keep it

The note in question is `sase/memory/macros.md`.

- **gem:** retire it, or replace it with a pointer.
- **cld:** keep it as a digest bound to doc sections through hashes.
- **grk:** keep a short how-to and point it at the docs.
- **cdx:** treat authority and delivery as separate properties.

**Resolution: keep a smaller digest, make `docs/` canonical, and bind the two.** The
routing evidence decides this:

- Gao & Chen show agents rarely open classical docs unprompted.
- Vercel's skill was never invoked in 56% of eval cases.
- The prior sase list found that agents *do* follow imperative authored links.

Once the digest is bound,
[measure it](#worked-example-of-migrating-the-macros-note). If the read log shows agents
almost always go on to the doc section, shrink the digest to triggers plus links.

### An always-on docs index or on-demand lookup

**Two results seem to conflict.**

- **Vercel:** an 8 KB compressed docs index in `AGENTS.md` reached a 100% pass rate. The
  equivalent skill reached 79%, and only with explicit instructions; without them it
  matched no docs at all.
- **Cochran:** forcing a catalog preload was the *costliest* condition. Agents inferred
  page paths directly from the question. A lookup tool that returns page gists cut cost,
  with quality non-inferior.
- **cld** therefore says: do not inline a docs catalog into core.

**They measure different things.**

- Vercel measures whether an agent *knows to look* for knowledge missing from its
  training data. Next.js 16 APIs were the test case; sase's macro grammar is the same
  kind of knowledge.
- Cochran measures cost once an agent is already working inside a corpus whose paths
  are predictable.

**Resolution:**

- Keep a trigger-level pointer in always-loaded text. sase's one-line reference-memory
  descriptions are already this design.
- Make page paths and anchors predictable.
- Do not inline a full docs catalog.

### Which automation papers matter

gem ranked RepoAgent first and DocAgent sixth; no other report used them. Both generate
docstring- and API-level documentation for code objects, bottom-up through a dependency
graph. sase's problem is prose user documentation. These papers are closer fits:

- AdDoc: traceability-driven change recommendations
- Tan et al. and DOCER: stale code references
- RepoDoc: incremental updates for repository-level docs
- CASCADE: checking documented claims against behavior

**Resolution:** RepoAgent and DocAgent are moved to
["skip unless"](#ranked-reading-list).

### Which theoretical frame

The reports offer different frames:

- gem: CoALA's "docs are semantic memory"
- cdx: Hipikat and the Extended Mind
- grk: transactive memory and cognitive dimensions

**Resolution:** Hipikat ranks highest because it is an actual project-memory system
built over existing artifacts. CoALA's procedural/semantic split is a poor fit:
`macros.md` mixes grammar (semantic) with launch rules (procedural) by design. The others
are optional vocabulary.

### Do agents own the wiki or do humans review it

- **Karpathy:** "You read it; the LLM writes it."
- **A-SAW:** trust requires mandatory human review.

**Resolution:** adopt Karpathy's operations (ingest, query, lint, an index and a log)
together with A-SAW's gate. The deciding difference is cld's point that Karpathy's raw
sources are immutable while sase's source of truth, its code, changes constantly. sase
already gates memory writes and completions, and docs should not get a looser regime.

## Themes and what they suggest for sase

These are directions to explore, not a plan. Any memory-file change goes through
`/sase_memory_write`, and larger changes go through `/sase_plan`.

### Classify knowledge by its job before choosing where it lives

This list merges cdx's job table, cld's Diátaxis-to-memory mapping and grk's migration
heuristic.

- **Hazards and prohibitions needed on every turn**
  - *Diátaxis type:* none (agent instruction)
  - *Canonical home:* core memory
  - *How it reaches an agent:* always inlined
  - *Maintained by:* human; kept tiny
- **Routing and gotchas for one subsystem (the `macros.md` digest)**
  - *Diátaxis type:* digest of reference/how-to
  - *Canonical home:* reference memory, **bound to doc sections**
  - *How it reaches an agent:* description always shown; body on read
  - *Maintained by:* human-curated, with drift flagged
- **Contracts, syntax, config keys, CLI**
  - *Diátaxis type:* reference
  - *Canonical home:* `docs/`, generated from or checked against the schema and parser
  - *How it reaches an agent:* audited section read or `grep`
  - *Maintained by:* generated where the code knows the facts; checked elsewhere
- **Human procedures and runbooks**
  - *Diátaxis type:* how-to
  - *Canonical home:* `docs/`
  - *How it reaches an agent:* on demand
  - *Maintained by:* human; executable where feasible
- **Why the project chose X**
  - *Diátaxis type:* explanation
  - *Canonical home:* `decisions` web, immutable
  - *How it reaches an agent:* descriptor inlined, strand on demand; rendered into a docs
    page
  - *Maintained by:* human; superseded, never edited
- **Vocabulary**
  - *Diátaxis type:* explanation / reference
  - *Canonical home:* `glossary` web
  - *How it reaches an agent:* the same; rendered into a docs glossary
  - *Maintained by:* human
- **Plans, progress, investigations**
  - *Diátaxis type:* none (episodic)
  - *Canonical home:* beads, plans, the research sidecar; **never `docs/`**
  - *How it reaches an agent:* read through their own tools
  - *Maintained by:* decisions graduate into the web when work ships

Diátaxis covers the human entries. The agent-instruction, decision and evidence entries
are a sase extension, which is cdx's point. A general documentation taxonomy should not
erase the difference between describing behavior and constraining an agent.

### Authority, delivery and maintenance contract are separate properties

cdx's three dimensions are the clearest way to think about "first-class":

- **Purpose:** what the reader should get from the page (reference, procedure,
  explanation, instruction).
- **Maintenance contract:** a living description, a generated projection, or a superseded
  record.
- **Delivery:** always loaded, listed for discovery, or retrieved for a task.

A page can be the canonical reference and still load only on demand. "First-class"
then means a shared management interface:

- a stable path plus anchor
- a `description:` written as a trigger
- `type`
- `owner`
- `reviewed`
- optional `covers:` code globs
- an explicit supersession or retirement path

Precedents for this metadata:

- **Google's freshness block:** `owner`, `reviewed`, plus reminders.
- **GitLab's ownership frontmatter plus CODEOWNERS.** Check the live page; cld saw it
  only through mirrors.
- **Baker's topic rules:** self-contained, one purpose, establishes its own context.

### Routing decides whether docs ever act as memory

The evidence, and what each source shows:

- **[Gao & Chen 2026](https://arxiv.org/abs/2608.20195):** 557 SWE-chat sessions and
  33,097 agent PRs. Instruction files plus agent notes are 60.5% of documentation
  interactions; classical docs 10.6%; API references 1.3%. Consultation is
  self-initiated 70.2% of the time and failure-driven 7.5%. No explicit
  documentation-based validation sequence was observed. The common "actionability" and
  "verifiability" claims lack consistent behavioral support.
- **[Vercel 2026](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals):**
  The always-present compressed index scored 100%; the skill, which was never invoked in
  56% of cases, scored 79%. These are first-party evals, and the post was #12 on the
  2026-10-06 list.
- **[Cochran 2026](https://arxiv.org/abs/2607.04576):** In a 709-page LLM-maintained
  wiki, agents skipped the index and inferred page paths. Gist lookup cut cost and kept
  quality non-inferior. Catalog preload was the costliest condition. Single author, one
  corpus.
- **[Gloaguen et al. v3](https://arxiv.org/abs/2602.11988):** Context files do not
  generally improve task success and raise cost by more than 20%. Instructions are
  followed; overviews do not help.
- **[DocPrompting](https://arxiv.org/abs/2207.05987) (ICLR 2023):** Retrieving
  documentation measurably helps code generation for functions absent from training
  data. sase's macro grammar is exactly such knowledge.
- **[Ahrefs llms.txt study](https://ahrefs.com/blog/llmstxt-study/) (vendor data, June
  2026):** Of 137K sites, 97% of `llms.txt` files received no requests in May 2026. A
  public index is not the lever; an internal pointer is.

**For sase:** documentation acts as memory when three things hold:

1. A trigger-level pointer sits in always-loaded text.
2. Paths and anchors are predictable.
3. Reads are audited, so usage can be measured.

The cheapest probe is to let `sase memory read` accept `docs:<page>#<anchor>` selectors.
The reads are then logged, and memory can link `[[docs:macros#hold-directive]]` with a
lint check. This respects `corpus-before-mechanism`: the corpus exists (65k lines), and
what is missing is *evidence of need*, which the read log would supply before anything
heavier such as embeddings or a retrieval service gets built.

### Scriptable maintenance through mechanical findings and small agent tasks

Mechanical findings feed small agent tasks. The checks below are ordered from cheapest to
most expensive.

- **Required frontmatter (`type` from an enum, `description`, `owner`, `reviewed`); links
  and anchors resolve. MkDocs `strict` already covers part of this.**
  - *Inspiration:* Google; GitLab; [Markdoc](https://stripe.dev/blog/markdoc)
  - *Cost:* trivial
- **Every backticked `sase …` command resolves in the parser and vice versa; every
  `sase.schema.json` key is documented and every documented key exists**
  - *Inspiration:* [Tan et al.](https://arxiv.org/abs/2212.01479), DOCER
  - *Cost:* small
- **Generated regions inside hand-written pages, with a CI freshness check, for example
  the directive table in both `docs/macros.md` and the digest, rendered from the
  directive registry**
  - *Inspiration:* [cog](https://nedbatchelder.com/code/cog/) `--check` (added in cog
    3.3.0); [Willison's TIL](https://til.simonwillison.net/python/cog-to-update-help-in-readme)
  - *Cost:* small
- **`covers:` globs: warn, never block, when covered code changes without the page**
  - *Inspiration:* [AdDoc](https://infobart.com/static/documents/tse2014.pdf);
    [Swimm](https://docs.swimm.io/new-to-swimm/continuous-documentation)'s up-to-date /
    out-of-sync / outdated states; Google's "same change as the code"
  - *Cost:* small to medium
- **Behavioral claims: executable how-tos, shared doc and test templates, and
  doc-derived tests**
  - *Inspiration:* Docs as Tests; [DScribe](https://arxiv.org/abs/2005.08750);
    [CASCADE](https://arxiv.org/abs/2604.19400)
  - *Cost:* medium to large

The generated-regions check is my addition. It is the lightest way to "generate the
catalog" without converting a whole page into a template.

**Then the agents.** `refresh_docs` should consume *one finding or one page per run*:

- This matches Diátaxis's "what single next action will produce an immediate
  improvement?"
- It also matches Karpathy's lint operation, which looks for contradictions, stale
  claims, orphan pages and missing cross-references.
- The polish agent then verifies only that diff.
- The cheapest agent to update a doc is the one that just changed the code. The
  `covers:` warning should reach that agent inside its own turn, because a separate
  report would never reach a single-turn agent.

**KCS's distinction matters here.** A *read* proves the page was accessed. A *successful
use* is task-level evidence. A *check against the code* is evidence of correctness. A
recorded read should never refresh `reviewed:`. Usage is one signal for prioritizing
review; dependency changes and consequences are others, so a rarely read recovery
runbook can still need review.

### Govern agent-written docs the way memory writes are governed

Evidence:

- [A-SAW](https://arxiv.org/abs/2610.13647): agent drafts against a typed catalog and
  templates raised median quality by 19 points and made quality predictable. Trust
  stayed conditional: 11 of 13 practitioners rejected unreviewed output. Its
  anti-hallucination measures transfer directly:
  - catalog-grounded identifiers
  - explicit `[TODO: …]` markers in place of plausible filler
  - automated phantom-identifier checks
  - two-role approval
- [Lethbridge et al. 2003](https://doi.org/10.1109/MS.2003.1241364): engineers keep
  *highly structured, easy to maintain* documentation current, and let the rest go stale.
  High-level explanation can lag and still be useful; reference and how-to cannot.
- [Moreira & Sweet](https://arxiv.org/abs/2607.24759): a pre-commit verification gate
  (reciprocal links, required frontmatter) in front of agent-written wiki pages.
- Agent READMEs (in your library, queued): unconstrained agent-facing Markdown grows by
  small additions and almost no deletions.

**For sase:** docs edits already flow through host-owned completion. The gap is a
docs-specific lint gate plus A-SAW's TODO-not-filler rule in the docs-writing prompts,
not a new approval mechanism.

### Keep durable and transient knowledge apart

- Garg's [Context Anchoring](https://martinfowler.com/articles/reduce-friction-ai/context-anchoring.html)
  separates a project-level priming document from feature-level living documents. When a
  feature ships, significant decisions graduate to ADRs.
- [Cline's Memory Bank](https://docs.cline.bot/prompting/cline-memory-bank) is the
  cautionary contrast. It mixes `activeContext`/`progress` with durable files and tells
  the agent to "read ALL memory bank files at the start of EVERY task."

sase's split is already right: durable knowledge in docs and memory, transient work in
beads and plans, rationale graduating into `decisions`. A docs lint could enforce it by
rejecting `type: plan` and dated progress sections.

## Worked example of migrating the macros note

The note being migrated is `sase/memory/macros.md`. This merges cld's steps, grk's
heuristic, cdx's authority/delivery split, and the
[generated-region idea](#scriptable-maintenance-through-mechanical-findings-and-small-agent-tasks).

1. **Remove duplicated policy.** The "Agents never create git commits …" rule already
   lives in core memory and `decisions:host-owned-completion`. Keep one copy.
2. **Make `docs/macros.md` canonical and give it metadata:** `type`, a trigger-style
   `description`, `owner`, `reviewed`, and `covers: src/sase/macros/**`.
3. **Generate the catalog parts.** Render the directive and alias table from the
   directive registry into *both* the doc and the digest as generated regions, and check
   their freshness in `just check`. If the registry cannot produce the descriptions, that
   suggests the descriptions belong in code.
4. **Bind the remaining digest prose.** Add frontmatter such as
   `sources: [docs/macros.md#directives, …]` and store section hashes. Print the drift
   warning *inside* `sase memory read` output.
5. **Split the doc by type, one page per cycle:**

   - a syntax reference
   - a directives reference with one section per directive
   - a defining-macros reference
   - a how-to for launching project tasks
   - explanation pages that link to `decisions` strands

   Keep anchors stable, and use MkDocs redirects for anything that moves.
6. **Measure.** Over about 30 days, compare digest reads with doc-section reads in the
   read log. Then shrink the digest to triggers plus links, or keep it as it is.

The same pattern fits `sase_beads.md` against `docs/beads.md` and `sase_artifacts.md`
against `docs/artifact_references.md` and `docs/artifact_links.md`. Core gotchas, such
as the keymap config and the Rust-core boundary, stay core. The decision and glossary
webs stay webs.

## Idea backlog, ordered by leverage per unit of effort

1. **Docs frontmatter (`type`, `description`, `owner`, `reviewed`, optional `covers`)
   plus a `sase docs lint` that requires it. Start with pages that memory notes digest or
   link to.**
   - *Main sources:* Google SWE ch. 10; GitLab; Diátaxis
2. **Two-way CLI and config reference checks against the parser and `sase.schema.json`**
   - *Main sources:* Tan et al.; single-sourcing
3. **Generated regions (cog-style) for directive, CLI and config tables, with `--check` in
   CI**
   - *Main sources:* Martraire; cog
4. **Bind memory digests to doc sections (`sources:` plus hashes), with the warning shown
   inside `sase memory read`**
   - *Main sources:* Write the Docs ARID; AdDoc
5. **Audited `docs:<page>#<anchor>` selectors, and lint-checked `[[docs:…]]` links**
   - *Main sources:* Gao & Chen; Write the Docs "Addressable"; the read log
6. **Make `refresh_docs` consume one lint finding or one page per run**
   - *Main sources:* Diátaxis; Karpathy's lint; OpenAI's doc-gardening
7. **A non-blocking `covers:` warning delivered inside the turn that changed the code**
   - *Main sources:* Google "same change"; Swimm; AdDoc
8. **Split `ace.md`, `configuration.md` and `macros.md` by type, one page per cycle**
   - *Main sources:* Diátaxis; Baker; Cochran
9. **Render the `decisions` and `glossary` webs into generated docs pages**
   - *Main sources:* Martraire; Google "canonical docs"
10. **Generate the docs nav from `type:`, and an on-demand `sase docs list` that is never
    inlined into core**
    - *Main sources:* Cochran; Vercel (pointer, not catalog)

Constraints to respect:

- `corpus-before-mechanism`: gather evidence before building retrieval.
- `/sase_memory_write` for any memory change.
- The Rust-core boundary, if selector resolution must match across frontends.

## Ranked reading list

The ranking reflects how likely each item is to change how sase structures, links and
maintains `docs/` and memory, weighted by evidence quality and by how much it adds beyond
the 2026-10-06 memory and instruction-file list.

Effort:

- **S:** 15 minutes or less
- **M:** 30–60 minutes
- **L:** paper or book length; read the abstract and the named sections

Library status comes from one batched `bob ref find`. "Not in library" means only that
the item is absent from `ref/`, not that you have never read it. Library check: 5 of 49
candidates already in your library (1 finished).

### Tier 1: read first

1. **[Diátaxis](https://diataxis.fr/)** (Daniele Procida; living site). Read
   [the compass](https://diataxis.fr/compass/) and
   [Diátaxis as a guide to work](https://diataxis.fr/how-to-use-diataxis/). **S–M.** Not
   in library. All four researchers ranked it.
   - Gives the `type:` vocabulary.
   - Gives a migration cadence that avoids a big-bang restructure.
   - Read it with a few `macros.md` passages beside you, asking what each one helps its
     reader *do*.

2. **[*Software Engineering at Google*, ch. 10 "Documentation"](https://abseil.io/resources/swe-book/html/ch10.html)**
   (Tom Manshreck, ed. Riona MacNamara; O'Reilly, 2020; free online), together with
   **[Google docguide best practices](https://google.github.io/styleguide/docguide/best_practices.html)**.
   **M.** Not in library.
   - "Documentation is like code": owners, review, freshness dates with reminders.
   - Canonical documents, a single purpose per document, deprecation.
   - "Change your documentation in the same CL as the code change."
   - Borrow the principles, not Google's process overhead.

3. **[From Agent Behaviour to Agent-Friendly Documentation](https://arxiv.org/abs/2608.20195)**
   (Zhijun Gao & Jing Chen; 2026-08-20). **L.** Not in library.
   - The only large behavioral study of how coding agents discover, read and write docs.
   - Its null result on actionability and verifiability should temper any
     "agent-friendly docs" checklist.
   - It was #15 on the 2026-10-06 list. If you read it then, reread only the
     recommendations.

4. **[LLM Wiki (idea file)](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)**
   (Andrej Karpathy; gist, April 2026). **S.** Not in library.
   - Three layers: raw sources, the wiki, a schema file.
   - Three operations: ingest, query, lint.
   - Two special files: `index.md` and `log.md`.
   - Read it against sase's split, keeping in mind that sase's "raw source" is code,
     which is not immutable.

5. **[Detecting Outdated Code Element References in Software Repository Documentation](https://arxiv.org/abs/2212.01479)**
   (Wen Siang Tan, Markus Wagner, Christoph Treude; *Empirical Software Engineering*,
   2024), plus the **[DOCER GitHub Action paper](https://arxiv.org/abs/2307.04291)**.
   **M.** Not in library.
   - 28.9% of the top-1000 GitHub projects had outdated references at analysis time;
     82.3% had one at some point.
   - Maps directly onto sase's CLI and config references.

### Tier 2: strong, specific inspiration

6. **Knowledge-Centered Service v6:
   [Reuse is Review](https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/030/040/020),
   [Article Structure](https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/040/010/020),
   and [Article State](https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/040/010/030)**
   (Consortium for Service Innovation). **S.** Not in library.
   - Maintenance done as part of use, with confidence tracked separately from
     visibility.
   - The source of the "read ≠ used ≠ checked" distinction for sase's audited reads.
   - Only cdx found it, and it is the best fit for sase's existing read log.

7. **[A-SAW: The Agentic Software Architecture Workflow](https://arxiv.org/abs/2610.13647)**
   (Finn Klatt, Luca Di Grazia, Johannes Schneider; 2026-10-09). **M.** Not in library.
   - The only industrial evaluation found of agents maintaining structured documentation
     under mandatory review.
   - Covers typed catalogs, TODO markers in place of filler, and the split between
     quality and trust.
   - Very new (v1), from one organization.

8. **[Every Page is Page One](https://mbakeranalecta.github.io/spfe-open-toolkit/spfe-docs-essays/every-page-is-page-one.html)**
   (Mark Baker; essay; the book is XML Press, 2013). **S** for the essay. Not in library.
   - Self-contained, single-purpose topics that establish their own context.
   - The page-level complement to Diátaxis. Agents land in the middle the way search
     readers do.

9. **[Progressive Disclosure for LLM-Maintained Wiki Knowledge Bases: a Preregistered Ablation](https://arxiv.org/abs/2607.04576)**
   (Theodore O. Cochran; 2026-07-06, v2 2026-10-07). **M–L.** Not in library.
   - The only controlled evidence on summaries, catalogs and gist retrieval in an
     LLM-maintained Markdown corpus.
   - Read it together with the
     [Vercel post](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)
     (not in library; #12 on the 2026-10-06 list). The pair explains "pointer, not
     catalog."
   - Caveats: one author, one corpus, and a failed human-judge reliability gate.

10. **[Using Traceability Links to Recommend Adaptive Changes for Documentation Evolution](https://infobart.com/static/documents/tse2014.pdf)**
    (Barthélémy Dagenais & Martin P. Robillard; IEEE TSE 40(11), 2014). **M.** Not in
    library.
    - Research grounding for `covers:` warnings: recommend *where* docs need attention
      after a change instead of rereading everything.
    - Read the worked examples and limitations first.

11. **[cog](https://nedbatchelder.com/code/cog/)** (Ned Batchelder) with
    **[Using cog to update `--help` in a Markdown README](https://til.simonwillison.net/python/cog-to-update-help-in-readme)**
    (Simon Willison). **S.** Not in library. *Added by the lead.*
    - The lightest practical pattern for generated regions inside hand-written Markdown,
      with `cog --check` in CI.
    - Lets sase generate the directive, CLI and config tables without converting whole
      pages into templates.

12. **[How Stripe builds interactive docs with Markdoc](https://stripe.dev/blog/markdoc)**
    (Ryan Paul; 2022-09-13). **S.** Not in library.
    - Docs as a parseable, schema-validated AST: link validation in CI, AST-based
      refactoring, and no code mixed into content.
    - The model for making `docs/` safely editable by scripts.

13. **[Hipikat: A Project Memory for Software Development](https://www.cs.ubc.ca/~murphy/papers/hipikat/hipikat-tse.pdf)**
    (Čubranić, Murphy, Singer, Booth; IEEE TSE 31(6), 2005). **M.** Not in library.
    - The closest conceptual precedent: project memory built from artifacts that
      already exist, with typed relationships and task-driven recommendation.
    - Read §3 (the model) and §7 (discussion). The evidence concerns human newcomers,
      not LLMs.

14. **[*Living Documentation: Continuous Knowledge Sharing by Design*](https://www.pearson.com/en-us/subject-catalog/p/living-documentation-continuous-knowledge-sharing-by-design/P200000009531/9780134689364)**
    (Cyrille Martraire; Addison-Wesley, 2019). **L.** Skim the chapters on knowledge
    extraction, the living glossary, and automation. Not in library.
    - The book-length case for "generate what the system knows; curate only the
      insight."

15. **[How Software Engineers Use Documentation: The State of the Practice](https://doi.org/10.1109/MS.2003.1241364)**
    (Lethbridge, Singer, Forward; IEEE Software 20(6), 2003). **S–M.** Not in library.
    - Structured, easy-to-maintain docs are the ones that get maintained.
    - Explanation may lag; reference and how-to may not.

### Tier 3: skim for specific angles

16. **[CASCADE: Detecting Inconsistencies between Code and Documentation with Automatic Test Generation](https://arxiv.org/abs/2604.19400)**
    (Kiecker et al.; FSE 2026). **M.** Not in library. Checks documented claims against
    behavior through doc-derived tests, and reports a mismatch only when doc-derived code
    passes the test while the existing code fails. Evaluated on Java; relevant for the
    reference facts in how-tos.
17. **[Documentation principles](https://www.writethedocs.org/guide/writing/docs-principles/)**
    (Write the Docs). **S.** Not in library. ARID ("Accept (some) Repetition In
    Documentation") versus DRY is the exact tension behind memory digests; also covers
    "Current," "Nearby" and "Addressable."
18. **[Context Anchoring](https://martinfowler.com/articles/reduce-friction-ai/context-anchoring.html)**
    (Rahul Garg; 2026-03-17). **S.** Not in library. Priming documents versus feature
    documents, and how decisions graduate into ADRs.
19. **[Beyond Memory: A Templated Substrate for Heterogeneous Collaborative Knowledge Work with LLM Agents](https://arxiv.org/abs/2607.24759)**
    (Moreira & Sweet; 2026-05-29). **M.** Not in library. A frontmatter schema, typed
    edges and a pre-commit gate for an agent-maintained wiki. Evidence is case studies
    only.
20. **[Swimm: Continuous Documentation](https://docs.swimm.io/new-to-swimm/continuous-documentation)**
    (vendor docs). **S.** Not in library. *Added by the lead.* A shipped code-coupled
    documentation system that checks docs on every commit, with up-to-date / out-of-sync
    / outdated states. A product precedent for `covers:`.
21. **[Generating Unit Tests for Documentation](https://arxiv.org/abs/2005.08750)** (DScribe;
    Nassif, Hernandez, Sridharan, Robillard; IEEE TSE). **M.** Not in library. Generates
    tests and documentation from one shared template. Applies to repeatable reference
    facts only.
22. **[Software Documentation Issues Unveiled](https://www.inf.usi.ch/lanza/PUBS/P/Agha2019a.pdf)**
    (Aghajani et al.; ICSE 2019). **M.** Not in library. An issue taxonomy built from
    878 artifacts, useful for naming lint and finding categories.
23. **[RepoDoc](https://arxiv.org/abs/2604.26523)** (Xu et al.; 2026-04-29). **M.** Not
    in library. A repository knowledge graph with incremental "semantic impact
    propagation" updates. Read it only if the generated-reference track becomes real
    work.
24. **[How does OASIS DITA support content reuse?](https://acm-sigdoc-structured.org/postings/How-Does-OASIS-DITA-Support-Content-Reuse.pdf)**
    (Stanley Doherty; ACM SIGDOC). **S–M.** Not in library. Reuse by key rather than by
    copy, and the governance costs of transclusion chains. No XML needed.

### Already in your library or on the 2026-10-06 list

- **[Harness engineering](https://openai.com/index/harness-engineering/)** (OpenAI).
  **Finished.** Reread only the knowledge-base section ("a map, not a manual").
- **[Codified Context](https://arxiv.org/abs/2602.20478)** (Vasilopoulos). In your
  library, queued (legacy backlog). The closest real system to "docs as cold memory":
  34 subsystem docs behind a retrieval service.
- **[Agent READMEs](https://arxiv.org/abs/2511.12884)** (Chatlatanagulchai et al.). In
  your library, queued (legacy). Shows how agent-facing Markdown grows without types.
- **[Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)**
  (Anthropic). In your library, started (legacy). grk's progressive-disclosure model for
  docs pages.
- **[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)**
  (Anthropic). In your library, started (legacy). Background.
- **[Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988)** (Gloaguen et al.). Not in
  library; #2 on the 2026-10-06 list. Only the v3 nuance is new: instructions are
  followed, overviews do not help. Its companions are
  [Lulla et al.](https://arxiv.org/abs/2601.20404) (efficiency gains) and
  [Khatri](https://arxiv.org/abs/2607.27250) (no measurable correctness effect from the
  injection strategy).

### Contrast, vocabulary, or skip unless needed

- **[Cline Memory Bank](https://docs.cline.bot/prompting/cline-memory-bank).** Useful as a
  taxonomy. Its loading design (read all files on every task) is the one to avoid.
- **[llms.txt](https://llmstxt.org/)**, together with the
  [Ahrefs 137K-site study](https://ahrefs.com/blog/llmstxt-study/), and
  **[Mintlify `skill.md`](https://www.mintlify.com/docs/ai/skillmd).** Shipped formats
  for agent-facing projections. Public `llms.txt` files go almost entirely unread, so
  borrow the format for an internal index, not as a lever.
- **[CoALA](https://arxiv.org/abs/2309.02427).** Vocabulary only. Its procedural/semantic
  split does not map cleanly onto sase's notes.
- **[RepoAgent](https://arxiv.org/abs/2402.16667) and DocAgent.** Docstring- and
  API-level generation through dependency graphs. Not sase's prose problem.
- **[ReadMe.LLM](https://arxiv.org/abs/2504.09798).** LLM-oriented library docs, backed
  by case studies. Its "up to 100%" figure is a success rate, not an improvement.
- **[DocPrompting](https://arxiv.org/abs/2207.05987).** Classic evidence that retrieved
  docs help with APIs absent from training. Background for the
  [routing theme](#routing-decides-whether-docs-ever-act-as-memory).
- **[Documenting Architecture Decisions](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions)**
  (Nygard). You already practice this through the `decisions` web.
- **[The Extended Mind](https://consc.net/papers/extended.html)**, Cognitive Dimensions of
  Notations, and Transactive Memory. Optional philosophy and vocabulary.
- **[Executable Code Knowledge](https://arxiv.org/abs/2608.16295).** AST-span
  fingerprints for freshness. Single author, synthetic evaluation.
- **CODESYNC.** Dropped as off-topic (see
  [Corrections](#corrections-to-claims-in-the-reports)).

### Suggested captures

These are for you to run if you want them. Nothing was written to the vault.

```bash
bob ref create https://diataxis.fr/how-to-use-diataxis/ -L
bob ref create https://abseil.io/resources/swe-book/html/ch10.html -L
bob ref create https://arxiv.org/abs/2608.20195 -L
bob ref create https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
bob ref create https://arxiv.org/abs/2212.01479 -L
bob ref create https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/030/030/040/020
bob ref create https://arxiv.org/abs/2610.13647 -L
bob ref create https://arxiv.org/abs/2607.04576 -L
```

## Caveats

- **Evidence quality is uneven.**
  - Quantitative but limited:
    - Gao & Chen: observational.
    - Tan et al.: a mining study.
    - Cochran: preregistered, but one author and one corpus.
    - A-SAW: one organization, v1 only six days old.
    - Vercel: first-party.
  - Practitioner guidance rather than experiments: Diátaxis, Google, KCS, Baker, Martraire
    and Karpathy.
- **Interpretation versus evidence.** The
  [job-based mapping](#classify-knowledge-by-its-job-before-choosing-where-it-lives), the
  bound-digest design and the
  [resolution of the Vercel/Cochran tension](#an-always-on-docs-index-or-on-demand-lookup)
  are my synthesis, not findings from any single source.
- **Secondhand items.**
  - GitLab's metadata details came through mirrors (cld).
  - Karpathy's gist date comes from cld's fetch.
  - My verification of the 2026 arXiv papers covered their abstract pages, not the full
    texts.
- **Library coverage.** `bob ref find` indexes only `ref/`, and intake was not checked
  separately. The Google docguide "possible" match was a false positive (a LangGraph
  note).

## Corrections to claims in the reports

I checked these against arXiv abstract pages, the local tree, and web sources.

- **CODESYNC is about detecting doc–code drift**
  - *Report:* gem
  - *What is actually true:* CODESYNC (Wang et al., ICML 2025) updates LLMs' knowledge of
    evolving Python APIs. Its abstract never mentions documentation. **Dropped.**
- **ReadMe.LLM boosts accuracy "by up to 100%"**
  - *Report:* gem
  - *What is actually true:* The abstract reports "up to 100% success" in *one case
    study*. That is a success rate, not an improvement.
- **"Cascade (2026), Academic Software Engineering Group", no URL**
  - *Report:* gem
  - *What is actually true:* The paper is CASCADE by Kiecker, Sparka, Reuter, Ziegler and
    Grunske, [arXiv 2604.19400](https://arxiv.org/abs/2604.19400), to appear at FSE 2026.
    Evaluation: 71 inconsistent and 814 consistent Java pairs; 13 new inconsistencies
    found, 10 since fixed.
- **Reads are logged to `.sase/state/audit/`; `sase memory read docs:…`**
  - *Report:* gem
  - *What is actually true:* Neither the path nor the `docs:` selector exists. Both are
    proposals.
- **`docs/llms.md` is an `llms-full.txt`**
  - *Report:* grk
  - *What is actually true:* It is the LLM-provider integration page.
- **`cli.md`, `configuration.md` and `ace.md` are generated dumps**
  - *Report:* grk
  - *What is actually true:* They carry no generation markers and are hand-maintained, as
    cld says. That they are *not* generated is part of the problem.
- **65 top-level docs pages**
  - *Report:* cld
  - *What is actually true:* There are **55**. The 59,507-line total is correct.
- **Gloaguen v3 shows no general benefit**
  - *Report:* cdx
  - *What is actually true:* Confirmed. The v3 abstract (2026-09-29) adds a nuance:
    instructions in context files *are* well followed, but repository overviews "are not
    helpful." Pointers and rules belong in always-loaded text; overviews do not.
- **A-SAW (arXiv 2610.13647)**
  - *Report:* grk
  - *What is actually true:* Verified: Klatt, Di Grazia and Schneider, v1 dated
    2026-10-09. One sentence of the abstract is garbled, so treat any figure not restated
    in the body with caution.

Also verified as real and accurately summarized:

- Gao & Chen (2608.20195)
- Cochran (2607.04576)
- Moreira & Sweet (2607.24759)
- Khatri (2607.27250)
- RepoDoc (2604.26523)
- Executable Code Knowledge (2608.16295)

## About this report

- **Date:** 2026-10-15
- **Role:** lead researcher. This report merges four independent reports with my own
  verification and gap research.
- **Inputs** (all in this directory):
  - [`__cdx`](project_docs_as_managed_memory_reading_list__cdx.md): authority vs delivery,
    KCS, AdDoc, Hipikat, and evidence on agent context files
  - [`__cld`](project_docs_as_managed_memory_reading_list__cld.md): measured `docs/`,
    Karpathy's LLM Wiki, Gao & Chen, Cochran, drift checks, and a `macros.md` worked
    example
  - [`__grk`](project_docs_as_managed_memory_reading_list__grk.md): progressive
    disclosure, A-SAW, Lethbridge, and a migration heuristic
  - [`__gem`](project_docs_as_managed_memory_reading_list__gem.md): CoALA framing,
    RepoAgent and DocAgent, and a Diátaxis directory restructure
- **Question:** Bryan is considering three moves:
  1. Migrate some sase memories (for example `sase/memory/macros.md`) into `docs/`.
  2. Treat project documentation as a first-class kind of memory and manage it the same
     way.
  3. Structure the docs so that maintaining them is intuitive and scriptable by agents.

  Which articles and papers should inspire that work?

A note on scope: four other reports on an adjacent question landed in `202610/` in the
same hour:

- `docs_as_first_class_memory__cld.md`
- `docs_as_memory_migration_and_structure__gem.md`
- `docs_memory_split_diataxis_projections__grk.md`
- `documentation_as_memory_source_backed_references__cdx.md`

They belong to a different dispatch. This consolidation neither read nor moved them.
