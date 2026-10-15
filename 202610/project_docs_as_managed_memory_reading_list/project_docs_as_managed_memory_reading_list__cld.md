# Docs as First-Class Memory: Reading List for Restructuring sase's `docs/`

- **Researcher:** cld (one of four independent researchers in this swarm)
- **Date:** 2026-10-15
- **Question:** Bryan is considering three related moves:
  1. Migrating some sase memory notes, such as `sase/memory/macros.md`, into `docs/`.
  2. Treating project documentation as a first-class kind of memory, managed the same way.
  3. Structuring the docs so that maintaining them is intuitive and scriptable by agents.

  Which articles and papers should inspire that work?
- **Companion research:** the 2026-10-06 swarm's *memory and instruction file* reading
  list already covers the instruction-file side: what belongs in always-loaded text,
  wording, and how rules go stale. This report covers the **documentation** side and
  avoids repeating that list except where a source matters for both.

---

## Bottom line

**Read these first:**

1. **Karpathy, *LLM Wiki*** (gist, 2026-04-04). The clearest model of an
   agent-maintained Markdown knowledge base:
   - three layers: raw sources, the wiki, and a schema file
   - three operations: ingest, query, lint
   - two special files: `index.md` and `log.md`
2. **Gao & Chen, *From Agent Behaviour to Agent-Friendly Documentation*** (arXiv, 2026-08-20).
   Agents mostly read instruction files and their own notes. Classical docs are 10.6% of
   documentation interactions, and agents never checked docs against code. Docs only work
   as memory if something routes agents into them.
3. ***Software Engineering at Google*, Ch. 10 "Documentation",** read with Google's
   **docguide best practices.** "Documentation is like code" as a checklist: owners,
   review, freshness dates with reminders, a single purpose per document, canonical docs,
   and deleting dead docs.
4. **Diátaxis**: the compass, plus "Diátaxis as a guide to work." It gives a type system
   for pages, and a way to migrate one page at a time instead of reorganizing everything
   at once.
5. **Cochran, *Progressive Disclosure for LLM-Maintained Wiki Knowledge Bases*** (arXiv,
   2026-07-06, v2 2026-10-07). A preregistered ablation on a 709-page LLM-maintained
   Markdown wiki:
   - Per-page `summary:` frontmatter cut cost modestly.
   - Adding a gist-returning lookup tool cut answer cost 30–58%, with pooled quality
     non-inferior.
   - Forcing the routing catalog into the prompt was the costliest setup.

**What these sources suggest for sase:**

- **Give each fact one canonical home, and make every other copy a projection.**
  `sase/memory/macros.md` (167 lines, about 3.7k tokens) is a hand-written digest of
  `docs/macros.md` (4,082 lines). It even says "Full contract: `docs/macros.md`." The
  sources do not argue for deleting the digest. Write the Docs' ARID principle ("Accept
  (some) Repetition In Documentation") and Mintlify's generated `skill.md` both defend
  agent-facing digests. They do argue for **binding** the digest to its source sections,
  so drift is detected mechanically and not discovered by accident.
- **Docs become first-class memory by adopting memory's machinery, not by moving files
  around.** sase memory already has:
  - typed frontmatter
  - trigger-style `description:` lines
  - authored `[[links]]`
  - audited reads
  - `init --check` drift detection

  Only 2 of the 65 top-level `docs/*.md` pages have any frontmatter. Bringing these
  mechanisms to docs pages is the change that matters: a `type`, a `description`, an
  owner, `covers:` code paths, a `reviewed:` date, and section-addressable audited reads.
- **For scriptable maintenance, lint findings should feed small tasks, and a
  whole-corpus prompt should not be the main tool.** Today `refresh_docs` asks an agent
  to "Refresh the documentation" after commit drift. The literature points to cheap
  mechanical checks first:
  - outdated code references (Tan et al.)
  - schema-validated content (Markdoc)
  - freshness metadata (Google)
  - executable procedures (Docs as Tests)

  An agent then fixes one finding at a time. That matches Diátaxis's "do one thing" and
  Google's "update docs in the same change as the code."

The full ranked list is [at the end](#ranked-reading-list).

---

## Method

- **Local grounding:**
  - measured `docs/` (pages, lines, frontmatter, nav) and the memory corpus
    (`sase memory list`)
  - read `macros.md` through `sase memory read`
  - inspected the `refresh_docs` chop
  - consulted two earlier, unrelated swarm reports through `sase artifact read`: the
    2026-10-06 memory reading list and the 2026-10-01 OpenAI harness-engineering
    critique
- **Discovery:** about 30 web searches, both standard and extended.
- **Verification:** six fetch passes against primary pages:
  - the arXiv abstract and HTML pages
  - Karpathy's gist
  - diataxis.fr
  - writethedocs.org
  - Google's docguide and SWE-book chapter
  - stripe.dev
  - martinfowler.com
  - Cline docs
  - llmstxt.org
  - Mintlify docs

  Failures:
  - Medium refused the Beads post (HTTP 403).
  - diataxis.fr/complex-hierarchies returned 404.
  - The HTML version of arXiv 2604.11243 returned 404.

  Claims from those three sources are marked as secondhand below.
- **Library check:** every candidate went through `bob ref find` in one batch. The
  results are summarized at the end.

---

## Where sase stands today (measured 2026-10-15, master `c2c2ffd4df`)

| Surface | Measurement |
|---|---|
| `docs/` corpus | 90 Markdown files, 65,178 lines, about 561k words. The 65 top-level pages total 59,507 lines. |
| Largest pages | `ace.md` 9,771 lines; `configuration.md` 7,768; `macros.md` 4,082; `llms.md` 3,582; `beads.md` 3,046 |
| Page metadata | 2 of 65 top-level pages have YAML frontmatter (`index.md`, `getting_started.md`), both only title and description for the site |
| Navigation | MkDocs Material in `strict: true` mode. The sections are "Getting Started / The Basics / Beyond the Basics / The Nitty Gritty / Integrations / Reference". These group by difficulty, not by kind of document. Runbooks, contracts and references are spread across sections. |
| Reference docs vs code | `configuration.md` (7.8k lines) and `cli.md` (1k lines) are hand-maintained, although `src/sase/config/sase.schema.json` and the CLI parser exist and could drive or check them. |
| Memory | 10 project and 2 home reference notes, plus 3 child notes, and the `decisions`, `glossary` and `task_types` webs. `macros.md` is the largest reference note, at about 3.7k tokens. The always-loaded context is about 5.75k tokens across 9 files. |
| Gardening | Builtin `refresh_docs` chop: an `update` agent, then a `polish` agent, triggered by `git.commits_since`. Both are told to touch only documentation and to "document the actual current behavior." There is no structured finding list. Each pass judges the whole corpus. |

The 2026-10-01 harness report reached a related conclusion: "Docs total 54.9k lines with
no agent-facing map," and gardening "covers docs only." The corpus has grown about 10%
since then.

---

## A framing: Diátaxis types mapped to sase memory kinds

This mapping is my own synthesis, not a claim made by any single source. It is the
easiest way to decide where a fact should live.

| Knowledge | Diátaxis type ([compass](https://diataxis.fr/compass/)) | Canonical home in sase | Projections that should be generated or hash-checked |
|---|---|---|---|
| Hazards, prohibitions, routing triggers for agents | none (agent-only) | core memory | none |
| Why the project chose X | explanation (cognition + acquisition) | `decisions` web | a rendered `docs/decisions/` page for humans |
| Vocabulary | explanation / reference | `glossary` web | a rendered `docs/glossary.md`, in the spirit of Martraire's "living glossary" |
| Contracts, syntax, config keys, CLI | reference (cognition + application) | `docs/` reference pages, single-sourced from schema or parser where possible | a memory **digest** bound to doc sections, such as today's `macros.md` |
| Human procedures | how-to / tutorial | `docs/` | none |
| Agent procedures | how-to | generated skills | a docs page listing skills, generated |
| Plans, progress, chats | none (episodic) | beads, plans, sidecars; **never** `docs/` | decisions graduate into the `decisions` web when work ships |

The rows mean two things:

- **Both directions of projection exist.** Some docs should be rendered *from* memory
  (decisions, glossary). Some memory should be digested *from* docs (macros, beads,
  artifacts).
- **What the user calls "migrating macros.md to docs"** is really three moves:
  1. The policy lines it contains (e.g. "Agents never create git commits…") already live
     in core and `decisions:host-owned-completion`. They should be removed from the
     digest.
  2. The syntax cheat sheet stays as a digest, but bound to sections of the canonical doc.
  3. The full contract stays only in `docs/macros.md`, which needs splitting by type.

---

## Themes, evidence, and what each suggests for sase

Each theme lists its strongest sources, then sase-specific ideas. These are
inspirations, not a plan. Memory-file changes go through `/sase_memory_write`, and
anything larger goes through `/sase_plan`.

### 1. One canonical home per fact; repetition is allowed but bound

**Evidence**

- **Google *SWE at Google*, Ch. 10:**
  - When documents conflict, "designate *canonical* documentation."
  - "Reference documentation should be single-sourced as much as possible."
- **Google docguide, "Duplication is Evil":** "Do not write your own guide to a common
  Google technology or process. Link to it instead."
- **Write the Docs principles:**
  - ARID, "Accept (some) Repetition In Documentation," but "ARID does not mean WET."
  - "Nearby": "Store sources as close as possible to the code which they document."
- **OpenAI, *Harness engineering*** (already in your library, finished): `AGENTS.md`
  acts as a roughly 100-line map into a structured `docs/` system of record. CI checks
  freshness, cross-links and structure, and a recurring doc-gardening agent runs over it
  (verified via mirrors in the 2026-10-01 report).
- **Codified Context** (Vasilopoulos, 2026-02-24) has three tiers:
  - a roughly 660-line "constitution" loaded every session
  - 19 specialist agent specs
  - a cold tier of 34 subsystem Markdown documents (about 16,250 lines, including the
    retrieval service), reached through an MCP service with `find_relevant_context` and
    `search_context_documents`. Its matching is plain keyword substring.

  Context totaled about 26k lines, 24% of the 108k-line codebase. The author says
  "Agent creation was typically driven by observed failure patterns rather than upfront
  design." It is an experience report from one developer.
- **Mintlify `skill.md`:** Mintlify "automatically generates a skill.md file … by
  analyzing your documentation with an agentic loop."
  - It distinguishes "llms.txt is a directory" from "skill.md is a capability summary."
  - A hand-written `skill.md` at the root overrides the generated one.

  This is a shipped example of an agent-facing projection derived from canonical docs,
  with a human override.
- **llms.txt v2** (Howard; modified 2026-08-10):
  - An H1 is the only required part.
  - The rest is H2 "file lists" of `[name](url): notes`.
  - Each page has a `.md` twin.
  - The "Optional" section marks "links an agent can skip when a shorter context is
    needed."

**For sase**

- **Declare the binding in the digest's frontmatter**, for example
  `sources: [docs/macros.md#directives, docs/macros.md#define]`. Then
  `sase memory init --check`, or a new `sase memory verify`, can store a hash of each
  source section and warn when the section changes after the digest was last reviewed.
  The warning should print **inside `sase memory read` output**. Agents are single-turn,
  so a separate report would never reach them. This is the cheapest mechanical form of
  "memory as a projection of docs."
- **Keep the digest human-curated, with a generated draft as an aid.** The prior
  memory list's evidence, SkillsBench v4 (self-generated skills scored below baseline),
  argues against Mintlify-style fully generated digests becoming the canonical copy. A
  regeneration agent can *propose* a digest diff when the hash check fires.
- **Render `decisions` and `glossary` into the docs site as generated pages.** This is
  the reverse projection. It gives humans the "explanation" layer that `docs/` lacks,
  without a second source of truth.

### 2. Typed, self-contained, addressable pages

**Evidence**

- **Diátaxis compass:** "action or cognition?" × "acquisition or application?" yields
  tutorial / how-to / reference / explanation. The site calls it "a truth-table or
  decision-tree of documentation" and says it works on existing docs.
- ***SWE at Google*:**
  - "A document should have, in general, a singular purpose, and stick to it."
  - "It is important to know the different types, and to *not mix types*."
  - Landing pages "include *only* links to other pages."
- **Mark Baker, *Every Page is Page One*** (XML Press, 2013): any page may be the
  reader's first. Each topic must stand alone at one level of abstraction. Agents arrive
  through `grep` and path guesses, so they read like Baker's web reader.
- **Gao & Chen:** recommend self-contained docs whose structure can be retrieved locally.
  The doc-to-doc read transition is only 0.27, meaning agents rarely move from one doc to
  another.
- **Cochran:** the agents "infer the likely page path" from the question and read the
  page directly. This suggests that file and path naming carries more of the load than
  index pages do.
- **Write the Docs, "Addressable":** "Provide addresses to readers that link directly to
  content at a granular level."

**For sase**

- **Add a `type:` field** to docs frontmatter. Use Diátaxis's four types plus `runbook`
  and `contract`, which sase already uses informally. Generate the MkDocs nav, or at least
  lint it, from `type`. Today "The Nitty Gritty" mixes runbooks with contracts.
- **Split the giants one page at a time.** `ace.md` (9.8k lines) and `configuration.md`
  (7.8k lines) are where agents pay most for mixed types. They cannot read the page
  whole, and `grep` hits land in the middle of tutorial prose.
- **Make sections addressable as stable selectors** (see Theme 5): `docs:macros#hold-directive`.

### 3. Metadata and mechanical checks (the scriptable part)

**Evidence**

- **Google freshness metadata:** "At Google, we often attach 'freshness dates' to
  documentation … metadata in the documentation set will send email reminders when the
  document hasn't been touched in, for example, three months." The example block is
  `freshness: { owner: 'username' reviewed: '2019-02-27' }`. When GooWiki was deprecated,
  "around 90% of the documents had no views or updates in the previous few months."
- **Google docguide:**
  - "Change your documentation in the same CL as the code change."
  - "Dead docs are bad … Default to delete or leave behind if migrating."
  - "A small set of fresh and accurate docs is better than a large assembly of
    'documentation' in various states of disrepair."
- **GitLab docs metadata** (mirrors of GitLab's docs):
  - Every page carries `stage`, `group` and `info` frontmatter, plus `title` and
    `description`.
  - CODEOWNERS maps pages to technical writers.
  - A `docs-lint` CI job runs markdownlint and Vale.

  It is the largest public example of docs-as-code with ownership metadata.
- **Stripe Markdoc** (Ryan Paul, 2022-09-13):
  - Stripe's old docs mixed "HTML, Markdown, Ruby, and ERB," so "content authoring
    effectively became software development."
  - Markdoc "parses to an Abstract Syntax Tree," with per-tag schemas.
  - CI validates "that every link between pages … points to a valid route."
  - Stripe is "building automated refactoring tools that use the AST."
- **Tan, Wagner & Treude** (*Empirical Software Engineering*, 2024; arXiv 2212.01479):
  - The method flags a code element named in docs when its count in source drops to
    zero after the doc's last update.
  - Prevalence: 28.9% of the top-1000 GitHub projects had outdated references at
    analysis time, and 82.3% had at least one at some point in their history.
  - The companion DOCER GitHub Action (arXiv 2307.04291) comments on PRs that "may result
    in outdated documentation."
- **Docs as Tests** (Manny Silva, 2025) and the open-source **Doc Detective**: execute
  documented procedures as tests. A 2026 follow-up, *Docs as Tests & AI: A Strategy for
  Self-Healing Technical Documentation*, is listed by booksellers. I could not see its
  table of contents.
- **Executable Code Knowledge** (Xueping Gao, 2026-08-17): knowledge units carry AST-span
  fingerprints. In a synthetic test, these flagged 50 of 50 stale cases that a snapshot of
  the rules missed. This is low-strength evidence from a single-author workshop
  submission.
- **Aghajani et al., *Software Documentation Issues Unveiled*** (ICSE 2019): a taxonomy
  built from 878 real documentation-issue artifacts. Under information content it lists
  correctness, completeness and up-to-dateness. It is useful for naming lint categories.

**For sase**, a sketch of a `sase docs lint` (or an extension of `sase validate`):

| Check | Source of idea | Cost |
|---|---|---|
| Required frontmatter (`type`, `description`, `owner`, `reviewed`), with `type` from an enum | GitLab; Google | trivial |
| Every backticked `sase …` command resolves in the CLI parser, and every parser command appears in `cli.md` | Tan et al.; SWE-book single-sourcing | small |
| Every config key in `sase.schema.json` appears in `configuration.md`, and every documented key exists | Tan et al.; single-sourcing | small |
| Code paths, `[[memory]]` links and `docs:` anchors that a page mentions all exist | Markdoc link validation; Tan et al. | small |
| `covers:` globs: warn when covered paths changed after `reviewed:`, and warn (never block) when a commit touches covered paths without touching the page | Google "same CL"; Codified Context drift | small–medium |
| Size budget per `type`, so oversized reference pages get split | Diátaxis; Cochran | trivial |
| Prose style rules in Vale | Datadog, Elastic and GitLab practice | medium |

The non-blocking commit warning matters most. The agent that changed the code is the
cheapest agent to update the doc. Everyone after it has to reconstruct the context.

### 4. Agent-maintained documentation: what the wiki literature has learned

**Evidence**

- **Karpathy, *LLM Wiki*** (2026-04-04):
  - The wiki is LLM-owned ("You read it; the LLM writes it").
  - Raw sources are immutable.
  - A schema file (`CLAUDE.md` or `AGENTS.md`) "makes the LLM a disciplined wiki
    maintainer rather than a generic chatbot."
  - Ingest touches "10-15 wiki pages" per source.
  - Lint looks for contradictions, stale claims, orphan pages, concepts without pages,
    missing cross-references, and data gaps.
  - `index.md` is "a catalog of everything in the wiki." `log.md` is append-only, with
    grep-able `## [date] ingest | Title` prefixes.
  - It scales to "~100 sources, ~hundreds of pages."
- **Moreira & Sweet, *Beyond Memory: A Templated Substrate*** (Notre Dame, 2026-05-29):
  - Pages declare a type, an `up:` parent, and typed edges (`extends`, `supports`,
    `criticizes`).
  - Log lines record `by: <human> via <agent>`.
  - A pre-commit verification gate checks reciprocal edges, resolving links, required
    frontmatter, and "honest reporting of negative results."

  The evidence is case studies only, but it is the most complete schema-plus-lint design
  in this space.
- **Cochran** (see above):
  - Adding a one-line `summary:` per page alone cut enforced-condition cost from $0.711 to
    $0.599 per answer.
  - Answer quality was non-inferior when pooled (+0.01). Correctness plus completeness
    alone dipped −0.18.
  - The human-judge reliability gate failed (κ 0.23).
  - It is a single-author study of a single corpus.
- **Google Code Wiki** (2025-11) and **Cognition's DeepWiki** are the fully generated end
  of the spectrum. Code Wiki "regenerates the documentation after each change" and
  carries a "Gemini can make mistakes" disclaimer. They are useful as a contrast: when
  generation is cheap, the hard part is trust.
- **Diátaxis, "a guide to work":**
  - "Don't try to work on the big picture."
  - Choose a piece, "nothing bigger than a page," and ask "What single next action will
    produce an immediate improvement here?"
  - Do it, then repeat.
  - Avoid tearing everything down.

**For sase**

- **Turn `refresh_docs` from a whole-corpus refresh into a consumer of a work queue.**
  The lint from Theme 3 produces findings, and the update agent takes one finding, or one
  page, per run. The polish agent then checks only that diff. This is Diátaxis's cycle,
  with the scheduling handled by machinery.
- **Copy Karpathy's `log.md` with care.** A docs changelog keyed by page could give
  `reviewed:` dates provenance. In sase, git history plus `SASE_AGENT=` trailers may
  already do this.
- **Keep the verification gate in front of agent writes.** The Templated Substrate's
  pre-commit gate is the docs version of the prior list's warning that memory written by
  agents needs a human or mechanical gate.

### 5. What agents actually read and write, and why routing matters

**Evidence**

- **Gao & Chen** (557 sessions from SWE-chat and 33,097 agent PRs from AIDev):
  - **Reads:** instruction files plus agent working notes make up 60.5% of documentation
    interactions. Classical docs are 10.6% and API references 1.3%.
  - **Validation:** "zero validation events," meaning no agent checked a doc against
    code.
  - **Writes:** the "production lobe" (1,401 events) is largely independent of code edits.
    41.5% of agent PRs touch docs, most often `AGENTS.md` (692 PRs), `CLAUDE.md` (362)
    and `copilot-instructions.md` (287).
  - **Unsupported claims:** "actionability" and "verifiability," the usual
    agent-friendly-docs claims, "lack consistent behavioural support."
  - **Recommendation:** agent working notes need their own maintenance category.
- **Mintlify traffic data (2026):** agents made up 66.85% of requests to Mintlify-hosted
  docs in August 2026, against 15.2% at the start of the year. Agent requests are counted
  server-side and human page loads browser-side, so treat the trend as directional.
- **Agent READMEs** (Chatlatanagulchai et al., 2025-11; in your library, queued): 2,303
  context files from 1,925 repos "evolve like configuration code" through frequent small
  additions.

**For sase**

- **Docs only become memory if the memory layer routes into them.** Gao & Chen's agents
  barely read classical docs on their own. sase's own read log showed that agents follow
  *imperative* authored links: the prior list found `sase_sizes.md` read heavily even
  though it is reachable only through a link.
- **Let `sase memory read` accept `docs:<page>#<anchor>` selectors.** The reads are then
  audited, and memory notes can link with `[[docs:macros#hold-directive]]`, checked by
  the Theme 3 lint. sase would also be able to measure what Gao & Chen could only infer:
  which docs agents actually use.
- **Do not inline a docs catalog into core.** Cochran's forced-preload condition was the
  most expensive. The prior list found that the inline `decisions` index costs 885 words
  per agent but is rarely followed. A compact, on-demand `sase docs list` (an
  llms.txt-style index with per-page `description:`) is the better pattern.
- **Check `corpus-before-mechanism` before building this.** That decision says sase does
  not build retrieval or linking machinery "ahead of a corpus that demonstrably needs
  it." A 65k-line docs corpus exists. What is missing is evidence that agents need it.
  The audited `docs:` selector is the cheap way to get that evidence before anything
  heavier.

### 6. Durable versus transient: what must never become docs

**Evidence**

- **Garg, *Context Anchoring*** (martinfowler.com, 2026-03-17):
  - It separates a project-level "priming document" ("updated quarterly") from a
    feature-level living document of decisions, rejected alternatives and open
    questions.
  - "When the feature ships, significant decisions graduate to formal ADRs."
  - It also notes that tool memory features "operate at the project level, not the
    feature level."
- **Böckeler, *Understanding Spec-Driven Development*** (2025-10-15; in your library,
  started):
  - It distinguishes spec-first, spec-anchored and spec-as-source.
  - It separates a "memory bank" (Kiro "steering", spec-kit "constitution") from
    per-feature specs.
  - On spec-kit's output: "I'd rather review code than all these markdown files."
- **Yegge, *Introducing Beads*** (in your library, queued; Medium blocked my fetch, so
  these quotes come from secondary summaries): he calls markdown plans "a colossal design
  mistake," with 605 plan files "in varying stages of decay."
- **Cline Memory Bank:**
  - Six files: `projectbrief`, `productContext`, `systemPatterns`, `techContext`,
    `progress`, `activeContext`.
  - `activeContext.md` "changes most frequently."
  - "update memory bank" makes the agent "review ALL files."

  It is a cautionary example of mixing durable and volatile knowledge in one doc set.

**For sase:** the existing split is already correct:

- durable knowledge in `docs/` and memory
- transient work in beads and plans
- graduated rationale in the `decisions` web

Make it enforceable: the docs lint could reject `type: plan` and date-stamped progress
sections. The `sdd.md` and `sdd_storage.md` pages show where the boundary is.

---

## Worked example: what "migrating `macros.md`" would look like

1. **Remove duplicated policy.** The memory note's "**Rule:** Agents never create git
   commits…" paragraph repeats core `sase.md` and `decisions:host-owned-completion`. Per
   the prior list (Chakrabarti; Nakayashiki), duplicated rules drift apart. Keep one
   copy.
2. **Bind the digest.** Add `sources:` frontmatter pointing at the `docs/macros.md`
   sections it summarizes:
   - Invoke
   - Directives table
   - Hold Directive
   - Define
   - Project-Task Launches

   Hash those sections in `init --check`.
3. **Type-split the canonical doc,** one Diátaxis step at a time:
   - `macros/` landing page (explanation plus links)
   - `macros/syntax` (reference)
   - `macros/directives` (reference, one section per directive)
   - `macros/launching-project-tasks` (how-to)
   - `macros/defining` (reference)
4. **Keep the selectors stable.** `#memory/macros` and `sase memory read macros.md` keep
   working, because the digest stays a memory note. What changes is that it now has
   provenance and a drift check.
5. **Measure.** If `docs:` selectors exist, compare digest reads with doc-section reads
   over 30 days. If agents almost always need the doc anyway, the digest can shrink to a
   trigger plus links.

---

## Ranked reading list

The ranking is by how likely each item is to change how sase structures, links and
maintains `docs/` and memory, weighted by evidence quality and how much it adds beyond
the 2026-10-06 memory list.

Effort:

- **S:** 15 minutes or less
- **M:** 30–60 minutes
- **L:** paper- or book-length (read the abstract and key sections)

Library status comes from `bob ref find`.

### Tier 1: read first

1. **[LLM Wiki (idea file)](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)**
   (Andrej Karpathy; gist, 2026-04-04). **S.** Not in library.
   - The conceptual template for "docs as agent-maintained memory":
     - layers: raw sources, the wiki, a schema file
     - operations: ingest, query, lint
     - files: `index.md`, `log.md`
   - Read it against sase's `memory` and `docs` split. The difference is that sase's
     "raw source" is code, which is not immutable.
2. **[From Agent Behaviour to Agent-Friendly Documentation](https://arxiv.org/abs/2608.20195)**
   (Zhijun Gao & Jing Chen, Peking University; 2026-08-20). **L.** Not in library. It was
   also #15 on the 2026-10-06 memory list.
   - The only large behavioral study of how coding agents discover, read and write docs.
   - Its null result on actionability and verifiability should temper any "agent-friendly
     docs" checklist.
3. **[Software Engineering at Google, Ch. 10 "Documentation"](https://abseil.io/resources/swe-book/html/ch10.html)**
   (Tom Manshreck, ed. Riona MacNamara; O'Reilly 2020; free online) together with
   **[Google docguide best practices](https://google.github.io/styleguide/docguide/best_practices.html)**
   and **[philosophy](https://google.github.io/styleguide/docguide/philosophy.html)**.
   **M.** Not in library.
   - Covers "documentation is like code" (owners, review, issues, freshness), doc types
     and "do not mix types," canonical docs, and deprecation.
   - The freshness-metadata block is a ready design for `reviewed:` and `owner:`.
4. **[Diátaxis](https://diataxis.fr/)** (Daniele Procida), especially
   **[the compass](https://diataxis.fr/compass/)** and
   **[Diátaxis as a guide to work](https://diataxis.fr/how-to-use-diataxis/)**. **S–M.**
   Not in library.
   - The page-type system for a `type:` field.
   - A migration method (one page, one next action, publish) that avoids a big-bang
     restructure of 65k lines.
5. **[Progressive Disclosure for LLM-Maintained Wiki Knowledge Bases: a Preregistered Ablation](https://arxiv.org/abs/2607.04576)**
   (Theodore O. Cochran; 2026-07-06, v2 2026-10-07). **M–L.** Not in library.
   - The only controlled evidence on how page summaries, catalogs and gist retrieval
     change cost and quality in an LLM-maintained Markdown corpus.
   - Caveats: single author, one corpus, and a failed human-judge reliability gate.
6. **[Detecting Outdated Code Element References in Software Repository Documentation](https://arxiv.org/abs/2212.01479)**
   (Wen Siang Tan, Markus Wagner, Christoph Treude; *EMSE* 2024) plus the
   **[DOCER GitHub Action paper](https://arxiv.org/abs/2307.04291)** (2023). **M.** Not in
   library.
   - The most directly scriptable drift check, with prevalence numbers that justify
     building it.
   - It maps onto sase's CLI and config references.

### Tier 2: strong, specific inspiration

7. **[How Stripe builds interactive docs with Markdoc](https://stripe.dev/blog/markdoc)**
   (Ryan Paul, Stripe; 2022-09-13). **S.** Not in library.
   - Docs as parseable, schema-validated data: link validation in CI, AST-based
     refactoring, and no code mixed into content.
   - Use it as the model for making `docs/` something scripts can safely edit.
8. **[Codified Context: Infrastructure for AI Agents in a Complex Codebase](https://arxiv.org/abs/2602.20478)**
   (Aristidis Vasilopoulos; 2026-02-24). **M–L.** Already in your library (queued since
   2026-03-21, legacy backlog).
   - The closest real system to "docs as cold memory": 34 subsystem docs behind a
     retrieval service, and specs created in response to observed failures.
   - It is an experience report, not a controlled study.
9. **[Beyond Memory: A Templated Substrate for Heterogeneous Collaborative Knowledge Work with LLM Agents](https://arxiv.org/abs/2607.24759)**
   (Priscila Saboia Moreira & Christopher R. Sweet, Notre Dame; 2026-05-29). **M.** Not
   in library.
   - A concrete frontmatter schema (type, `up:` parent, typed edges) and a pre-commit
     verification gate for an agent-maintained wiki.
   - Evidence is case studies only.
10. **[Documentation principles](https://www.writethedocs.org/guide/writing/docs-principles/)**
    (Write the Docs). **S.** Not in library.
    - ARID versus DRY is the exact tension behind memory digests.
    - "Current" ("incorrect documentation [is] worse than missing documentation"),
      "Nearby", and "Addressable".
11. **[Living Documentation: Continuous Knowledge Sharing by Design](https://www.pearson.com/en-us/subject-catalog/p/living-documentation-continuous-knowledge-sharing-by-design/P200000009531/9780134689364)**
    (Cyrille Martraire; Addison-Wesley, 2019). **L** (book; skim the chapters on knowledge
    augmentation, the living glossary, and automating docs). Not in library.
    - The book-length case for deriving documentation from the system and curating only
      what cannot be derived.
    - The intellectual root of "render glossary and decisions into docs, and digest docs
      into memory."
12. **[Context Anchoring](https://martinfowler.com/articles/reduce-friction-ai/context-anchoring.html)**
    (Rahul Garg, Thoughtworks; 2026-03-17). **S.** Not in library.
    - The priming-doc versus feature-doc split.
    - A graduation rule ("significant decisions graduate to formal ADRs") that fits
      sase's plan, bead and `decisions` lifecycle.
13. **[Mintlify `skill.md`](https://www.mintlify.com/docs/ai/skillmd)** together with
    **[the llms.txt spec, v2](https://llmstxt.org/)** (Mintlify, 2026; Jeremy Howard,
    2024, modified 2026-08-10). **S.** Not in library.
    - Two shipped formats for agent-facing projections of canonical docs: a capability
      digest generated from docs with a human override, and a link-list index with an
      "Optional" tier.
14. **[GitLab documentation metadata](https://docs.gitlab.com/ee/development/documentation/metadata.html)**
    (GitLab). **S.** Not in library.
    - Ownership frontmatter plus CODEOWNERS plus a `docs-lint` job (markdownlint, Vale)
      at large scale.
    - Read it for the metadata fields. Verify against the live page, since my search hits
      were archived mirrors.

### Tier 3: skim for specific angles

15. **[Understanding Spec-Driven Development: Kiro, spec-kit, and Tessl](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)**
    (Birgitta Böckeler; 2025-10-15). Already in your library (started). Memory bank versus
    spec, and the warning about review burden and markdown sprawl. Relevant to `sdd.md`.
16. **[Every Page is Page One](https://xmlpress.net/publications/eppo/)** (Mark Baker;
    XML Press, 2013). **L** (book). Not in library. The argument for standalone topics,
    which applies directly to agents that land on a page through `grep`.
17. ***Docs as Tests: A Strategy for Resilient Technical Documentation*** (Manny Silva,
    2025), and its 2026 AI follow-up. See the
    [IEEE ProComm review](https://procomm.ieee.org/?p=11483) and the
    [idratherbewriting podcast](https://idratherbewriting.com/blog/podcast-silva-guardians-of-knowledge).
    **L.** Not in library. Treats executable how-tos and runbooks as tests, which suits
    `perf_runbook.md` and `mobile_mvp_runbook.md`.
18. **[Software Documentation Issues Unveiled](https://2019.icse-conferences.org/details/icse-2019-Technical-Papers/49/Software-Documentation-Issues-Unveiled)**
    (Aghajani et al.; ICSE 2019), plus the
    [Never Work in Theory summary](https://neverworkintheory.org/2021/10/06/software-documentation-issues-unveiled.html).
    **M.** Not in library. A taxonomy for naming lint and finding categories.
19. **[Executable Code Knowledge](https://arxiv.org/abs/2608.16295)** (Xueping Gao,
    Alibaba Cloud; 2026-08-17). **M.** Not in library. AST-fingerprint freshness, and the
    design line "retrieval for coverage, ECK for … governance, and projections for
    delivery." Evidence is weak.
20. **Mintlify agent-traffic data:**
    [state of docs traffic](https://www.mintlify.com/blog/state-of-docs-traffic) and the
    [2026 State of Knowledge report](https://www.mintlify.com/state-of-knowledge/2026).
    **S.** Not in library. The case that docs now have two audiences. Methodology caveats
    apply.
21. **[Introducing Code Wiki](https://developers.googleblog.com/en/introducing-code-wiki-accelerating-your-code-understanding/)**
    (Google; 2025-11), plus
    [The Register's skeptical take](https://www.theregister.com/2025/11/17/google_previews_code_wiki/).
    **S.** Not in library. The fully generated end of the spectrum, and the trust problem
    that comes with it.
22. **[Agent READMEs: An Empirical Study of Context Files for Agentic Coding](https://arxiv.org/abs/2511.12884)**
    (Chatlatanagulchai et al.; 2025-11-17). Already in your library (queued). Context
    files evolve like configuration code.
23. **[Introducing Beads](https://steve-yegge.medium.com/introducing-beads-a-coding-agent-memory-system-637d7d92514a)**
    (Steve Yegge; 2025). Already in your library (queued). Why plans must never become
    docs. You know the conclusion from building sase beads, so read it only for the
    argument.
24. **[Cline Memory Bank](https://docs.cline.bot/prompting/cline-memory-bank)** (Cline
    docs). **S.** A widely copied structured doc-set-as-memory convention. Useful as a
    contrast because it mixes durable and volatile files.

### Already read, or covered by the 2026-10-06 memory list

- **[Harness engineering](https://openai.com/index/harness-engineering/)** (Lopopolo,
  OpenAI; 2026-02-11). **Already finished.** Re-read only the knowledge-base section,
  "a map, not a manual", which is the strongest single argument for `docs/` as the system
  of record.
- **Already in your library and adjacent, but about memory files rather than docs:**
  - [Letta Context Repositories](https://www.letta.com/blog/context-repositories/) (queued)
  - [ACE](https://arxiv.org/abs/2510.04618) (queued)
  - [Anthropic Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) (started)
  - [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (started)
- **Deliberately left out:**
  - *Knowledge Compounding* (arXiv 2604.11243): four queries and model-based projections.
  - Andy Matuschak's evergreen notes: your finished Zettelkasten reading already covers
    that ground.
  - Nygard's 2011 ADR post: sase's `decisions` web already goes beyond it.
  - The five-smells API-documentation paper (arXiv 2102.08486): targets Javadoc-style API
    documentation.

### Suggested captures

Lines for you to run if you want them; nothing was written to the vault:

```bash
bob ref create https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
bob ref create https://arxiv.org/abs/2608.20195
bob ref create https://abseil.io/resources/swe-book/html/ch10.html
bob ref create https://diataxis.fr/how-to-use-diataxis/
bob ref create https://arxiv.org/abs/2607.04576
bob ref create https://arxiv.org/abs/2212.01479
bob ref create https://stripe.dev/blog/markdoc
bob ref create https://arxiv.org/abs/2607.24759
```

---

## Idea backlog these readings point to

The ideas are ordered roughly by leverage per unit of effort. They are inspirations, not
a plan.

| # | Idea | Main sources |
|---|---|---|
| 1 | Add docs frontmatter (`type`, `description` written as a trigger, `owner`, `reviewed`, optional `covers`) and a `sase docs lint` that requires it. Start with the pages that memory notes summarize or link to. | Google SWE ch. 10; GitLab; Diátaxis |
| 2 | Bind memory digests to doc sections (`sources:` plus hashes in `init --check`), with the drift warning printed inside `sase memory read` | ARID; Mintlify skill.md; Tan et al. |
| 3 | Check CLI and config references against the parser and `sase.schema.json`, in both directions | Tan et al.; SWE-book single-sourcing |
| 4 | Add `docs:<page>#<anchor>` selectors to `sase memory read`, audited, with `[[docs:…]]` links checked by the lint | Gao & Chen; Write the Docs "Addressable"; sase read log |
| 5 | A non-blocking warning when a commit touches `covers:` paths without touching the page | Google "same CL"; Codified Context |
| 6 | Make `refresh_docs` consume lint findings, one finding or one page per run | Diátaxis "guide to work"; OpenAI doc-gardening; Karpathy lint |
| 7 | Split `ace.md`, `configuration.md` and `macros.md` by Diátaxis type, one page per cycle | Diátaxis; *Every Page is Page One*; Cochran |
| 8 | Render the `decisions` and `glossary` webs into generated docs pages | Martraire; SWE book "canonical docs" |
| 9 | Generate the docs nav, and an on-demand `sase docs list` (llms.txt-style), from frontmatter, without inlining it into core | llms.txt; Cochran; prior list's decisions-index cost |
| 10 | Run documented runbook steps as tests where feasible | Docs as Tests; Markdoc |

---

## Caveats

- **Evidence quality is uneven.** The best quantitative sources are:
  - Gao & Chen: observational.
  - Tan et al.: mining study.
  - Cochran: preregistered, but one author and one corpus.

  Most of the rest are practitioner essays and experience reports, including Codified
  Context, Karpathy, and the Templated Substrate case studies.
- **Code is not an immutable source.** Karpathy's model assumes immutable raw sources.
  sase's source of truth is code, which changes thousands of times a month. That is why
  this report leans on mechanical drift checks over LLM-judged "refresh" passes.
- **Some claims are secondhand:**
  - The Yegge quotes and the GitLab metadata details come from secondary or archived
    pages.
  - The Diátaxis "complex hierarchies" page returned 404, so nothing here relies on it.
- **Interpretation versus evidence.** The Diátaxis-to-memory mapping and the
  "projection binding" design are my synthesis, not findings from any one source.

Library check: 9 of 42 candidates already in your library (1 finished).
