# Docs as first-class memory: a reading list for migrating SASE notes into `docs/`

> **Research query.** Some SASE memories should move into markdown in `docs/`
> (`sase/memory/macros.md` is the motivating example). Project documentation
> should become a first-class representation of memory, managed the way memory
> is managed. Documentation should be structured so agents can maintain it
> intuitively and scriptably. Find articles and papers that inspire this, and
> end with a ranked reading list.

**Researcher:** grk (`research.1g.grk`) · 2026-10-15
**Kind:** independent reading-list research (docs × memory × agent-maintainable IA)
**Independence:** I did not locate, open, or read peer reports from this swarm
(`__cdx`, `__cld`, `__gem`). Shared external sources and unrelated prior
research only.

---

## Bottom line

Keep **one structured source of project knowledge** and **two projections** of
it: a human docs site (`docs/`, MkDocs, sase.sh) and an agent memory overlay
(`sase/memory/`, instruction bundles, `#memory/<stem>`). The migration is a
*re-homing of reference material* plus a *promotion of docs to the same
governance memory already has* (frontmatter types, descriptions, audited
reads, a write skill, lint, typed links). It is a split of audiences, not a
merge of files.

The smoking gun is already in the tree. `sase/memory/macros.md` is a 15 KB
reference note of how-to and gotchas that agents must load on demand.
`docs/macros.md` is a 238 KB dump of the same domain for humans. Core memory
is always inlined into `AGENTS.md`; several `docs/` pages (`ace.md` ~723 KB,
`configuration.md` ~652 KB, `cli.md` ~206 KB) would blow the instruction
budget if they were treated as memory. The two corpora already have different
jobs. The work is to make that split *intentional*, *typed*, and
*agent-scriptable*.

Four readings carry the whole argument:

1. **[Diátaxis](https://diataxis.fr)** — the information architecture. Tag
   every page as tutorial / how-to / reference / explanation. Grow the site
   from the inside out. Aim for *complete, not finished*.
2. **[Anthropic Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)** —
   the loading model SASE already uses (core metadata always on, body on
   trigger, bundled refs on demand). Apply it to *docs pages* the way it is
   already applied to skills and memory.
3. **[A-SAW (Klatt, Di Grazia, Schneider, 2026)](https://arxiv.org/abs/2610.13647)** —
   the maintenance workflow. Typed catalogs, instrumented templates, agent
   first draft, **mandatory human review**. Quality and trust come apart;
   11 of 13 practitioners rejected unreviewed agent output.
4. **[Lethbridge, Singer, and Forward (2003)](https://doi.org/10.1109/MS.2003.1241364)** —
   the maintenance law. Engineers update documentation that is *highly
   structured and easy to maintain*. Make docs structured, and agents (and
   you) will keep them.

If you read only those four, you can decide the shape of the migration. The
rest of the list supplies the topic-page pattern, the living-docs extraction
story, the empirical picture of agent context files, and the stale-ref
checks that make the structure scriptable.

---

## 1. What SASE already has, and what the literature is for

### Two audiences, two budgets

| Surface | Audience | Loading rule | Size pressure |
| --- | --- | --- | --- |
| Core memory (`type: core`) | Every agent, every turn | Always inlined into `AGENTS.md` | Must stay small |
| Reference memory (`type: reference`) | Agent, on demand | Audited `sase memory read`; listed by one-line description | Medium; read when the task names it |
| Memory webs / strands | Agent, on demand | Descriptor inlined; strand body via `web:keyword` | Small files, dense links |
| Skills (`SKILL.md`) | Agent, on trigger | Name/description always on; body then bundled files | Progressive disclosure |
| `docs/` (MkDocs Material, sase.sh) | Humans first; agents via `llms.txt` / fetch | Nav + search + page | Can be large |
| Generated dumps (`cli.md`, `configuration.md`, `ace.md`) | Humans / grep | Whole-file | Already 200–700 KB each |

The memory stack is already a progressive-disclosure system. Anthropic's
Agent Skills paper (October 2025; open standard at [agentskills.io](https://agentskills.io/))
names the three levels SASE already implements: L1 YAML name/description,
L2 `SKILL.md` body, L3 bundled references. Core / reference / webs are the
same pattern with different names. The open question is whether **project
documentation** joins that pattern as a first-class sibling, or stays a
human website that agents wander into with `grep`.

### The macros.md duplication is the migration prototype

`sase/memory/macros.md` (reference, parent `AGENTS.md`) is operational:
invoke `#name`, `%` directives, gotchas, links to `[[dispatch.md]]`. It is
the note an agent should read before touching macros. `docs/macros.md` is
the public reference for the same domain, more than 16× larger. That is
exactly the split Diátaxis and Skills both recommend: a **how-to** (or a
thin index into how-tos) for the practitioner in the loop, and a
**reference** generated or expanded for the human site.

A good migration of `macros.md` looks like:

- Keep a short agent-facing how-to / gotchas note in memory, or generate
  that note from the same structured source the docs page uses.
- Treat `docs/macros.md` as the canonical reference, with Diátaxis type
  `reference` in frontmatter.
- Point the memory note at the docs page (and at specific anchors) instead
  of restating the catalog.
- Generate the catalog portions from the live macro/CLI/config schema, in
  the living-documentation sense (Martraire): extract knowledge the system
  already has.

The same pattern applies to other reference notes that currently duplicate
docs (`sase_artifacts.md` vs `docs/artifact_references.md` /
`docs/artifact_links.md`; `sase_beads.md` vs `docs/beads.md`; CLI rules vs
`docs/cli.md`). Core memory stays core: gotchas that must fire on every
turn (keymap config, rust-core boundary, single-turn agents) do not belong
in `docs/` as their *only* home.

### Docs as first-class memory means governance, not location

"Manage documentation the way we manage memory" is a *process* claim:

- Typed frontmatter (`type:`, `description:`, Diátaxis mode, audience,
  generated-vs-authored).
- A write path with authorization (the analogue of `/sase_memory_write`).
- Audited reads when an agent consults a docs page as context.
- Lint: required fields, broken `[[links]]`, stale code-element references,
  page-type mismatches (tutorial text sitting in a reference page).
- An index of descriptions that can be always-loaded the way Reference
  Memory already is — a docs-side `llms.txt` / catalog, not the full
  2 MB tree.

Cline's Memory Bank is the naive version of this idea: six markdown files
the agent is told to **read in full at the start of every task**. SASE
already outgrew that. Steal the typed hierarchy and the update protocol.
Leave the "read ALL files every task" instruction on the table.

---

## 2. How I ranked

I ranked for *inspiration to change SASE's docs/memory split*, not for
general documentation excellence. A paper that generates READMEs from a
knowledge graph is useful as a *generation* technique. A four-quadrant
authoring framework that agents can tag and lint is useful as *structure*.
Structure outranks generation here, because Lethbridge's finding is that
only structured, easy-to-maintain documents get maintained.

Criteria, in order:

1. **Actionable on this tree.** Can it change how `docs/` and `sase/memory/`
   relate in the next few months?
2. **Dual audience.** Does it speak to humans *and* agents, or give a clean
   way to project one source to both?
3. **Scriptable.** Frontmatter, catalogs, templates, stale-ref checks,
   generation from code — things an agent can run.
4. **Evidence.** Industrial evaluation or a large corpus beats a blog
   manifesto, unless the manifesto is the best statement of a still-true
   claim (Diátaxis, Nygard, Baker).
5. **Humility about agents.** Mandatory review, quality–trust divergence,
   and "TODO markers instead of filler" outrank "the agent writes the docs."

---

## Ranked reading list

### 1. Daniele Procida — *Diátaxis* (living site)

- **URL:** <https://diataxis.fr>
- **Especially:** [Start here](https://diataxis.fr/start-here/),
  [Workflow](https://diataxis.fr/how-to-use-diataxis/),
  [Quality](https://diataxis.fr/quality/)
- **Library:** not in `ref/`

The four needs — tutorial, how-to, reference, explanation — are the
machine-checkable types SASE docs currently lack. Today's `mkdocs.yml` nav
is audience-journey shaped (*Getting Started*, *The Basics*, *Beyond the
Basics*, *The Nitty Gritty*, *Integrations*, *Reference*), which is a
reasonable human IA and a poor agent contract. An agent asked to "update
the macros documentation" cannot tell whether it is editing a how-to, a
reference dump, or an explanation, because the page does not say.

Three Diátaxis claims map directly:

- **One page, one mode.** Mixed pages are the maintenance hazard. Memory
  `macros.md` is a how-to. Docs `macros.md` wants to be reference. Mixing
  them in one file is why the memory note is already the wrong size for
  one of its jobs.
- **Inside-out, complete not finished.** Do not scaffold four empty
  sections. Pick a page, assess the user need, take one improvement, commit
  it. A plant is never finished and always complete. That is the right
  cadence for an agent-maintainable docs tree and for a migration of
  individual memory notes.
- **Functional vs deep quality.** Accuracy, completeness, consistency are
  measurable — and Diátaxis *exposes* lapses in them (a reference page that
  mirrors CLI structure makes missing flags obvious). Flow, fit, and
  "feeling good to use" stay human judgements. A-SAW later measures the
  same split as quality vs trust.

**What to steal:** a `diataxis:` frontmatter field (`tutorial` / `how-to` /
`reference` / `explanation`) on every `docs/` page and on every memory note
that is a candidate for migration; a lint that flags mode mixing; a
migration order that starts from pages already in front of you
(`macros.md`), not from a four-quadrant rewrite of `mkdocs.yml`.

---

### 2. Zhang, Lazuka, and Murag — *Equipping agents for the real world with Agent Skills* (Anthropic, 2025-10-16)

- **URL:** <https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills>
- **Standard:** <https://agentskills.io/> (progressive disclosure in three
  stages: discovery / activation / execution)
- **Library:** already in your library as [[ref/ai/claude_code_ref/claude_skills]]
  (started, legacy backlog, added 2025-10-17). Keep it on this list because
  the *docs* application is the new work; the skill format is already
  adopted.

This is the loading model to copy onto documentation. At startup the agent
sees only `name` + `description`. The body loads when the task matches.
Bundled files (`reference.md`, `forms.md`) load when the body points at
them. Context bundled into a skill is "effectively unbounded" because the
agent has a filesystem.

SASE memory is this pattern. SASE docs are not: an agent that needs CLI
help either greps a 206 KB page or hopes `docs/cli.md` was not the thing
it needed. The docs-as-memory move is to give every page the skill-like
envelope memory notes already have — description always available, body on
demand, extra files only when named — and to generate an index of those
descriptions (the Reference Memory list, or a project `llms.txt`).

The authoring advice is also the docs-authoring advice: start from
evaluation (where agents fail for lack of context), split when `SKILL.md`
gets unwieldy, write descriptions from the agent's point of view, put
deterministic work in code rather than prose. Generated CLI/config
reference belongs in code-backed pages; gotchas belong in short how-tos.

**What to steal:** treat `docs/` pages as skill-shaped resources. Description
index always on; page body via audited read; generated appendices split
out. Do not inline `docs/ace.md` into anyone's prompt.

---

### 3. Klatt, Di Grazia, and Schneider — *A-SAW: The Agentic Software Architecture Workflow* (arXiv:2610.13647, 2026-10-09)

- **URL:** <https://arxiv.org/abs/2610.13647>
- **Library:** not in `ref/`
- **Why this high:** it is the only industrial evaluation I found of
  *agents maintaining structured design documentation under mandatory
  human review*, which is the workflow you are reaching for.

Architecture as Code makes artifacts versionable and machine-readable; it
does not update them. A-SAW adds a persistent agent layer: a typed element
catalog, instrumented templates, a feature-scoped context folder, and a
human approval gate. Evaluation in a large product org: 45 architecture
documents, 13 matched source→regeneration pairs, 13 practitioner
interviews.

Headline numbers:

- Score SD 19.2 → 3.8 (quality becomes predictable across authors).
- Median +19 points on matched pairs.
- Completeness 100%, consistency 93%, machine-readability 99%,
  traceability 79%.
- **11 of 13 practitioners rejected unreviewed agent output.** Trust was
  conditional on how much the agent had to infer beyond the repository.
  Polished output is itself a hazard: reviewers may skip the review the
  workflow depends on.

Five structural anti-hallucination measures: catalog-grounded identifiers,
context-folder scoping, explicit `[TODO: …]` instead of plausible filler,
automated checks for phantom identifiers, two-role approval.

Five transferable design principles (their §5.2):

1. Ground the agent in a persistent, version-controlled context store.
2. Enforce a machine-verifiable naming contract (typed identifier catalog).
3. Separate artifact, agent-orchestration, and human-review layers.
4. Calibrate review to the agent's competence gradient (concentrate where
   it must infer).
5. Design for earned trust and progressive autonomy.

**What to steal for SASE docs:** a catalog of page ids / CLI flags / config
keys / bead types that docs and memory both reference by identifier; TODO
markers where context is missing; generated first drafts of reference
pages; **human review remains the gate** (this is already
`host-owned-completion` and `/sase_memory_write` for memory — docs need
the same). Traceability and rationale stay human. Completeness and
consistency are what the agent is for.

Propose: `bob ref create https://arxiv.org/abs/2610.13647 -L`

---

### 4. Michael Nygard — *Documenting Architecture Decisions* (Cognitect, 2011-11-15)

- **URL:** <https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions>
- **Library:** not in `ref/`

The original ADR: one short markdown file per architecturally significant
decision; Context / Decision / Status / Consequences; numbered; in the
repo; superseded rather than deleted. The post is itself an ADR.

SASE already has this as the **decisions memory web**: immutable once
accepted, superseded with `metadata.status` plus `superseded_by` and a
`[[...]]` back-link, never edited in place. That is the right kernel. The
inspiration for the docs migration is *placement*: decisions are
explanation (Diátaxis) and they are also agent-critical. They should
remain a structured corpus both surfaces can project — a human "why we
chose X" section in docs, and the always-on roster in agent instructions
(with the existing reopen condition that inlining every descriptor becomes
a token-budget problem).

**What to steal:** keep the web. When a memory note is really a decision,
it is already in the right shape; do not flatten it into a docs chapter.
When a docs page buries a decision in a narrative, lift it into a strand
and link both ways.

---

### 5. Chatlatanagulchai et al. — *Agent READMEs: An Empirical Study of Context Files for Agentic Coding* (arXiv:2511.12884v2)

- **URL:** <https://arxiv.org/abs/2511.12884>
- **Library:** already in your library as [[ref/ai/agent_ref/agent_readmes]]
  (queued since 2026-01-18, legacy unread). Worth keeping: it is the
  empirical picture of what happens when "docs for agents" grow without a
  type system.

2,303 agent context files (AGENTS.md, CLAUDE.md, …) across 1,925
repositories. They evolve like configuration: frequent small *additions*,
almost no deletions. They are long and hard to read. Heading depth is
shallow (H2/H3). Content priorities: tests 75.9%, implementation 70.8%,
architecture 68.1%. Security 14.8%, performance 14.5%.

This is the failure mode of "just put it in markdown for the agent."
Without types, budgets, and progressive disclosure, the file becomes a
append-only config blob. SASE's core/reference split, write skill, and
instruction-bundle rendering exist to prevent exactly this. A docs
migration that dumps reference notes into `AGENTS.md` would recreate the
corpus this paper measured.

**What to steal:** treat agent-facing docs as living configuration with an
explicit deletion/archive path; measure heading depth and file length;
keep NFRs (security, performance, single-turn, rust-core boundary) in
core memory because the empirical default is to omit them.

---

### 6. Lethbridge, Singer, and Forward — *How software engineers use documentation: the state of the practice* (IEEE Software 20(6), 2003)

- **DOI:** [10.1109/MS.2003.1241364](https://doi.org/10.1109/MS.2003.1241364)
- **Library:** not in `ref/`

Three industrial studies. Engineers do not update most documentation in a
timely way. The exception is documentation that is **highly structured and
easy to maintain** (test cases, inline comments). Out-of-date high-level
abstractions can remain useful.

This is the conservation law for the whole project. If docs-as-memory is
going to be maintained by you and by agents, the format has to be the
structured kind: small files, typed frontmatter, generated reference,
lintable identifiers. A 700 KB ACE page will rot. A catalog of widget
behaviors generated from the TUI, plus a short how-to, will not — or will
rot in a way a script can see.

The second finding is permission to keep high-level explanation slightly
stale. Diátaxis *explanation* and Nygard *context* can lag the code and
still orient a reader. Reference and how-to cannot.

Propose: `bob ref create https://doi.org/10.1109/MS.2003.1241364 -L`

---

### 7. Cyrille Martraire — *Living Documentation: Continuous Knowledge Sharing by Design* (Addison-Wesley, 2019)

- **ISBN:** 978-0-13-468932-6
- **Q&A:** <https://www.infoq.com/articles/book-review-living-documentation/>
- **Library:** not in `ref/`

Four principles: living documentation is **reliable**, **low-effort**,
**collaborative**, and **insightful**. The method is to *extract* knowledge
the system already has (types, tests, annotations, CLI schemas, config
models) and to automate the documents that can be automated, so humans
spend attention on the insight that cannot be extracted.

SASE already generates `sase/memory/sase.md`, `task_types.md`,
`sase_artifacts.md`, `sase_beads.md`, `sase_sizes.md`. The human site
already has generated-looking giants (`cli.md`, `configuration.md`,
`llms.md`). The living-docs move is to make that generation *the point*
for reference pages, and to stop hand-maintaining catalogs in memory
notes. Memory then holds the how-to and the gotchas that generation
cannot see (the rust-core litmus test; "don't forget `default_config.yml`
when changing keymaps").

**What to steal:** generate reference; author how-to and explanation;
never hand-duplicate a list the code already knows.

---

### 8. Mark Baker — *Every Page is Page One* (XML Press, 2013)

- **Site:** <https://everypageispageone.com/the-book/>
- **Essay:** <https://mbakeranalecta.github.io/spfe-open-toolkit/spfe-docs-essays/every-page-is-page-one.html>
- **Library:** not in `ref/`

Seven topic properties: self-contained; specific limited purpose;
establishes context; conforms to a type; assumes a qualified reader; stays
on one level; links richly. Readers arrive from search, from an agent
tool call, from a `#memory/` expansion. There is no "previous chapter."

This is the page-level complement to Diátaxis's site-level quadrants.
Agent `sase memory read` and `sase artifact read` *are* page-one arrivals:
the agent gets one note, not a book. A migrated docs page that only makes
sense if you read `getting_started.md` first will fail both humans landing
from Google and agents landing from a description index.

**What to steal:** one purpose per page; a context paragraph at the top
(the memory `description:` field is already this); typed links instead of
"see above"; qualified-reader statements ("read this before changing
macros") matching today's reference-memory blurbs.

---

### 9. Cline — *Memory Bank* (docs.cline.bot) — cautionary sibling

- **URL:** <https://docs.cline.bot/prompting/cline-memory-bank>
- **Library:** not in `ref/`

Six markdown files in a hierarchy: `projectbrief.md` →
`productContext.md` / `systemPatterns.md` / `techContext.md` →
`activeContext.md` → `progress.md`. The custom instruction is "I MUST
read ALL memory bank files at the start of EVERY task." Updates are
user-triggered. Checkpoints preserve code; the bank preserves knowledge.

This is the popular "markdown is the memory" design. It is a useful
*taxonomy* of project knowledge (brief, product why, architecture,
stack, current focus, progress). It is a poor *loading* design for SASE:
always-on full reads recreate the Agent READMEs failure mode and fight
the Skills progressive-disclosure model you already run. `activeContext.md`
and `progress.md` are also the wrong durability: SASE already has goals,
beads, stitches, and the Memory History panel for current work.

**What to steal:** the typed hierarchy as *optional docs templates* (a
product-why explanation page, a system-patterns explanation page). Leave
the mandatory full-read. Map "current focus" to goals/beads, not to a
docs file agents rewrite every turn.

---

### 10. Three small standards that already describe the dual projection

Read as a cluster; each is short.

**Jeremy Howard — `/llms.txt` v2** (<https://llmstxt.org/>). A curated
markdown index: H1, blockquote summary, H2 sections of
`[name](url): note` links. It is a description catalog for agents,
exactly analogous to SASE's Reference Memory list. SASE already ships
something in this spirit (`docs/llms.md` is 237 KB — that is a
`llms-full.txt`, not an index). The useful move is a *small* `llms.txt`
of page descriptions, with the giant file as optional.

**Agentic AI Foundation — `AGENTS.md`** (<https://agents.md/>). A README
for agents, kept *beside* the human README. This is the official
blessing of the dual-audience split. SASE's generated `AGENTS.md` is the
agent README; `docs/` is the human one. Migration should keep them
apart and generated from shared sources.

**Write the Docs — Docs as Code**
(<https://www.writethedocs.org/guide/docs-as-code/>; Holscher; Gentle's
*Docs Like Code*). Docs live in the repo, in plaintext, reviewed in PRs,
built in CI. SASE already does this (MkDocs in-tree). The missing piece
is the *agent* as a first-class docs contributor under the same PR/review
gate A-SAW insists on — which SASE already has for code (`host-owned-completion`)
and for memory (`/sase_memory_write`). Docs need that write path.

**Library:** none of the three are in `ref/`.

---

### 11. Andy Matuschak — *Evergreen notes*

- **URL:** <https://notes.andymatuschak.org/Evergreen_notes>
- **Library:** not in `ref/`

Atomic, concept-oriented, densely linked notes, written for yourself.
This is the design language of SASE **memory webs**: a descriptor plus
small strand files, `web:keyword`, authored `[[target]]` / `![[target]]`
links (decision `memory-links-are-authored`). When a memory note is
really a concept (glossary terms, decision claims, task types), it
should stay a strand, not become a docs chapter. Docs pages can
*transclude or link* strands; they should not replace them.

**What to steal:** migrate *reference catalogs* to docs; keep *concept
atoms* as webs. The glossary is already the existence proof.

---

### 12. Stale-docs detection (cluster)

**Tan, Wagner, and Treude — DOCER**, *Detecting Outdated Code Element
References in Software Repository Documentation*, Empirical Software
Engineering 29, 5 (2024). arXiv: [2212.01479](https://arxiv.org/abs/2212.01479).
28.9% of top GitHub projects have at least one stale code-element
reference *now*; 82.3% had one at some point. ICSME 2023 follow-up ships
a GitHub Action that scans PRs.

**Aghajani et al. — *Software Documentation Issues Unveiled*** (ICSE 2019).
878 artifacts; taxonomy of 162 issue types. Up-to-dateness is ~39% of
*content* issues. Follow-up survey (ICSE 2020, *The Practitioners'
Perspective*) ranks missing docs for new features as the up-to-dateness
issue practitioners care about most.

**What to steal:** a CI check that identifiers in `docs/` and
`sase/memory/` still exist in code, CLI, config schema, or the A-SAW-style
catalog. This is the cheapest scriptable maintenance win and the one
Lethbridge predicts people will actually run, because it is structured.

**Library:** not in `ref/`.

Propose: `bob ref create https://arxiv.org/abs/2212.01479 -L`

---

### 13. Two older theories that name the system you are building

**Thomas Green — *Cognitive Dimensions of Notations* (1989).** Viscosity
(resistance to local change) is the dimension of a 700 KB docs page.
Hidden dependencies are the dimension of a memory note that restates a
CLI flag. Premature commitment is scaffolding four empty Diátaxis
sections (Procida already warns against this). Use the vocabulary when
deciding what to split.

**Daniel Wegner — *Transactive Memory* (1985/1987).** Groups remember
more because they remember *who knows what*. SASE's description indexes
(Reference Memory list, skill name/description, a future docs `llms.txt`)
are a transactive-memory directory for agents. The directory has to stay
small and accurate; the holdings can be large.

**Library:** not in `ref/`. Read if you want vocabulary; skip if you want
mechanism. The mechanism is already in Skills and in `sase memory read`.

---

### 14. Xu, Liu, Wang, Zhong, and Zheng — *RepoDoc* (arXiv:2604.26523, 2026-04-29)

- **URL:** <https://arxiv.org/abs/2604.26523>
- **Code:** <https://github.com/SYSUSELab/RepoDoc>
- **Library:** not in `ref/`

RepoKG (Code / Concept / Doc entities, seven relations) → module
clustering → skillful agent generation with Mermaid diagrams; incremental
*Semantic Impact Propagation* for updates. 24 repos, 8 languages. +32.5%
API coverage, +10.4% completeness, 3× faster, 85% fewer tokens vs
flat-fragment baselines. Incremental: −73% time, −77% tokens, +10.2%
update recall.

Ranked last among the mechanism papers because SASE's problem is
*authored dual-audience structure*, and RepoDoc solves *generated
whole-repo docs from code*. Use it as the inspiration for generating
CLI/config/API reference and for incrementally regenerating those pages
when code changes. Do not use it as a replacement for Diátaxis how-tos,
Nygard decisions, or core gotchas.

Propose: `bob ref create https://arxiv.org/abs/2604.26523 -L` if the
generation track becomes real work.

---

## 3. A concrete shape the literature supports

Putting the readings against the current tree:

| Kind of knowledge | Home | Loading | Maintained by |
| --- | --- | --- | --- |
| Every-turn gotchas (keymaps, rust-core, single-turn) | Core memory | Always inlined | Human; tiny |
| Operational how-to for agents (`macros.md` gotchas) | Reference memory *or* generated projection of a docs how-to | Description always on; body on `sase memory read` | Human how-to; lint |
| Concept atoms (glossary, decisions) | Memory webs | Descriptor inlined; strand on demand | Human; supersede, don't edit |
| Public how-to / tutorial / explanation | `docs/`, Diátaxis-tagged | Nav + `llms.txt` description; audited page read | Human; agent drafts welcome |
| Catalogs (CLI, config, macros, flags, bead types) | Generated `docs/` reference + schema | Page read / grep / catalog id | **Generated** (Martraire, RepoDoc) |
| Architecture decisions | Decisions web *and* optional docs explanation that links to it | Already built | Human; Nygard rules |
| Current work | Goals, beads, stitches | Host-bound | Already built — not a docs file |

Migration heuristic for a given memory note:

1. If it is a gotcha that must fire every turn → stay core.
2. If it is a concept or a decision → stay a web strand.
3. If it is a catalog the code already knows → generate into `docs/`
   reference; replace the memory copy with a pointer.
4. If it is an operational how-to (`macros.md`) → keep a short agent
   how-to (memory or generated stub) and make `docs/` the canonical
   reference; Diátaxis-tag both.
5. If it is current work → it is a goal/bead, not documentation.

Scriptable maintenance, in the order I would actually build it:

1. Frontmatter schema (`diataxis`, `audience: human|agent|both`,
   `generated: true|false`, `description`).
2. Description index (Reference-Memory-like list and/or small `llms.txt`).
3. Identifier catalog (CLI flags, config keys, macro names, bead types)
   and a DOCER-style stale-ref check in CI.
4. `/sase_docs_write` analogue: agents draft, humans approve (A-SAW P3–P5).
5. Generate the giant reference pages from schema; stop hand-editing them.
6. Only then: optional RepoDoc-style impact propagation for those
   generated pages.

A-SAW's quality–trust finding is the governance constraint on all of the
above. Completeness and consistency will jump if an agent fills templates.
Trust will not, unless review stays mandatory and concentrates where the
agent inferred. TODO markers beat fluent filler. That is already how SASE
treats memory writes and host-owned completion; docs should join that
club rather than invent a looser one.

---

## 4. If you read only four

1. [Diátaxis](https://diataxis.fr) — structure and migration cadence.
2. [Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
   (already started in your library) — loading model for docs pages.
3. [A-SAW](https://arxiv.org/abs/2610.13647) — catalogs, templates,
   mandatory review, quality–trust split.
4. [Lethbridge et al. 2003](https://doi.org/10.1109/MS.2003.1241364) —
   why structure is what gets maintained.

Then Nygard (you already practice this), Agent READMEs (queued; the
failure mode), and Martraire (generate the catalogs).

---

## Library check

Library check: **2 of 18 unique candidates already in your library (0 finished).**

| Work | Verdict | Note |
| --- | --- | --- |
| Anthropic Agent Skills | in_library | [[ref/ai/claude_code_ref/claude_skills]] — started, legacy, added 2025-10-17 |
| Agent READMEs (arXiv:2511.12884) | in_library | [[ref/ai/agent_ref/agent_readmes]] — queued, legacy unread, added 2026-01-18 |
| Diátaxis, A-SAW, Nygard, Lethbridge, Martraire, Baker, Cline Memory Bank, llms.txt, AGENTS.md, Write the Docs, Matuschak, DOCER, Aghajani, RepoDoc, Green, Wegner | not_found | Absence from `ref/` is not proof unread |

Coverage note from `bob ref find`: only notes under `ref/` are indexed.

Suggested captures (add `-L` to also narrate):

```text
bob ref create https://diataxis.fr -L
bob ref create https://arxiv.org/abs/2610.13647 -L
bob ref create https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions -L
bob ref create https://doi.org/10.1109/MS.2003.1241364 -L
bob ref create https://arxiv.org/abs/2212.01479 -L
```

The Skills article and Agent READMEs paper are already captured; no
`bob ref create` for those two.
