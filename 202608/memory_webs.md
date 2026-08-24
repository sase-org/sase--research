---
create_time: 2026-08-24
updated_time: 2026-08-24
status: research
tags: [memory, glossary, zettelkasten, adr, agent-context, architecture]
---

# Memory Webs and Strands

**Research question:** Should SASE generalize its glossary into file-backed memory webs
composed of small memory strands, and if so, what model, command contract, migration,
and implementation boundary will preserve the glossary's current strengths without
overfitting every future web to glossary semantics?

**Scope:** Architecture research only; no SASE, `sase-core`, or `bob-cli` behavior was
changed. Repository evidence was inspected at `sase@6ca6e798ed22`,
`sase-core@590478df02e4`, and `bob-cli@ef90f4f9d04f` on 2026-08-24.

---

## Bottom line

Proceed with the idea. The proposed filesystem shape is a materially better canonical
representation for the glossary, and the same substrate can support ADRs and several
other kinds of agent-readable knowledge. It removes glossary content from
`sase/sase.yml`, makes each entry independently reviewable and addressable, and turns
the generated glossary note into an ordinary hub rather than a special build product.

I recommend five adjustments:

1. Treat **core/reference** as a delivery axis and **note/web/strand** as a
   content-shape axis. A web is core or reference; a strand inherits its web's delivery
   class. These are orthogonal concepts, not four tiers.
2. Adopt **core memory** in place of short-term memory, but use **reference memory**
   rather than structured memory in place of long-term memory. “Structured” describes
   representation, while the actual distinction is always loaded versus retrieved on
   demand. If `structured` is already a firm product decision, the architecture below
   still works; substitute that label mechanically.
3. Make the filename stem the strand's immutable identity and frontmatter `title` its
   mutable display name. Titles and aliases may resolve as conveniences, but durable
   links and audit records should use `<web>:<strand-slug>`.
4. Define actual links. A directory of entries is a collection, not a web. Support a
   small generic explicit-reference field, and let a web opt into phrase-mention
   discovery to preserve glossary closure behavior.
5. Generalize storage, discovery, selection, rendering, and auditing first. Keep
   glossary-specific editor highlighting and its ACE experience as a specialization
   backed by the `glossary` web until another web proves those affordances are generic.

The most important implementation principle is to avoid a flag-day rewrite. The word
`glossary` currently appears in 134 files under `src/` and 121 files under `tests/` in
the SASE checkout. The behavior spans Rust validation and phrase matching, Python
resolution and audit logs, generated instructions, XPrompt/LSP hover and definition, ACE
browsing/editing, and visual snapshots. Introduce the generic domain underneath those
surfaces, migrate the two catalogs, switch consumers, then retire compatibility
adapters.

## 1. What exists today

### 1.1 The current memory tiers describe loading, not time

SASE currently discovers flat Markdown files directly under `sase/memory/`:

- `type: short` notes are copied into every managed agent instruction file.
- `type: long` notes contribute a description to Tier 2 and are fetched with an audited
  `sase memory read <file>.md` call.
- Project files resolve before same-named home files.
- Long notes can form a parent/child presentation tree, but reads remain file-addressed.

Both kinds are durable and versioned. Nothing about a short note is intrinsically
recent, and nothing about a long note is intrinsically old. Renaming `short` to `core`
therefore corrects a genuine category error. The useful distinction is residency in the
agent's initial context.

This matches the broader direction of agent-memory systems. MemGPT models memory as a
hierarchy that moves information between limited in-context storage and external
storage, while current context-engineering guidance recommends a hybrid of compact
up-front identifiers and just-in-time retrieval. Anthropic's Claude Code documentation
likewise distinguishes concise files loaded at startup from topic files read on demand.
The common engineering concern is context residency, not the age of the information.

### 1.2 The glossary is already a proto-web, but with split storage

The current glossary has the essential parts of a memory web:

- canonical entries with aliases;
- stable validation and phrase matching in `sase-core`;
- exact, alias, and unambiguous-prefix lookup;
- recursive breadth-first closure over terms mentioned by definitions;
- inbound references and read provenance;
- a compact always-loaded roster that tells agents how to fetch detail;
- interactive browsing and source navigation.

The mismatch is storage. Definitions live in a large `memory.glossary` map in
`sase/sase.yml`, while `sase memory init` generates `sase/memory/glossary.md` containing
only the compact Tier 1 roster. Consequently, the semantic source, generated agent
memory, and ordinary memory-note system are three related but different paths.

The two requested migrations are small enough to be excellent fixtures:

- SASE currently has 19 glossary terms with richer cross-references.
- `bob-cli` currently has four terms (`Pomodoro`, `Schedule Log`, `Task Link`, and
  `Work Log`) and simpler relations.

Together they exercise multiword names, aliases, definitions containing Markdown,
implicit reference closure, and project-local source navigation without making the first
migration operationally large.

### 1.3 The external analogies support the model, not every name

The Zettelkasten analogy is useful in three precise ways:

1. An individual note needs an address independent of its prose.
2. Small notes should be linkable and independently retrievable.
3. A hub or structure note is an entry point into relationships among notes, not merely
   a folder label.

Practical Zettelkasten guidance explicitly treats the unique identifier as the minimum
needed to address a note, and describes hub/structure notes as fast paths or
topic-specific tables of contents into a cross-linked body of notes. It also recommends
stable IDs that survive title changes. Those properties map cleanly to a filename slug,
a strand body, and a web descriptor.

The analogy should not be taken too literally. A SASE web is a curated context interface
for agents, not a general personal knowledge-management system. It needs deterministic
rendering, strict validation, scope precedence, security checks, audit events, and a
small grammar. It does not need arbitrary backlinks, tags, graph visualization, or
Obsidian-compatible wiki syntax in v1.

ADRs are a particularly strong second case. Michael Nygard's original proposal calls for
small, modular, sequentially identified text files stored with the project; each
captures one decision, its context, status, and consequences, and superseded records
remain available. AWS's current ADR guidance describes the collection as a decision log:
people skim headlines for orientation, read individual records for detail, and create a
new record rather than rewriting an accepted decision. That is almost exactly a
reference web with a compact hub and one stable strand per decision.

## 2. Critique and resolved design questions

### 2.1 “Core memory” is good; “structured memory” is ambiguous

`core` says what the runtime does: the content is part of every agent's starting
context. It is also an established term in tiered agent-memory work.

`structured` does not say what the runtime does. Core notes are structured Markdown;
memory webs are structured whether they are loaded up front or on demand; and an
ordinary long note can be free-form prose. The phrase “a structured web presented as
core rather than structured memory” will be technically correct but cognitively awkward.

Recommended terminology:

| Existing                   | Recommended               | Meaning                                    |
| -------------------------- | ------------------------- | ------------------------------------------ |
| Tier 1 (short-term) Memory | Tier 1 (core) Memory      | Always included in agent instructions      |
| Tier 2 (long-term) Memory  | Tier 2 (reference) Memory | Indexed in instructions, fetched on demand |
| `type: short`              | `type: core`              | Delivery class, not content shape          |
| `type: long`               | `type: reference`         | Delivery class, not content shape          |

If “structured memory” is preferred as a brand term, use `type: structured` and
`Tier 2 (structured) Memory`, but explicitly define it as “structured for selective
retrieval.” Do not let code infer that a `structured` item has a different Markdown or
frontmatter format from a `core` item.

### 2.2 A web and a tier are independent axes

The clean model is:

| Shape              | Canonical path                       | Delivery class | Agent-instruction representation         |
| ------------------ | ------------------------------------ | -------------- | ---------------------------------------- |
| Plain note         | `sase/memory/<name>.md`              | Own `type`     | Whole core body, or one reference entry  |
| Web descriptor/hub | `sase/memory/webs/<web>.md`          | Own `type`     | One core section, or one reference entry |
| Strand             | `sase/memory/webs/<web>/<strand>.md` | Inherited      | Never a top-level tier entry by itself   |

This preserves exactly two H2 sections. It also prevents the model from becoming a
matrix of special cases such as “core strand,” “Tier 3 web,” or “long web note.” A web
is the unit of instruction presentation and policy; a strand is the unit of detailed
retrieval.

### 2.3 Identity must not depend on a title or alias

The proposed `<name>.md` needs a sharper contract. Use the filename stem as the durable
identifier:

```text
glossary:agent-clan
decisions:0007-memory-webs
```

The strand's `title` is display text. `aliases` are lookup conveniences. Exact slugs
should win over exact titles, which should win over exact aliases, which should win over
a unique normalized prefix. Durable links, source maps, and audit events should record
the slug even when the user typed a title or alias.

This avoids breaking links and historical audit queries when `Agent Clan` is renamed,
and it gives ADRs monotonically sortable IDs without forcing their title to remain
frozen. Normalize web and strand slugs with a deliberately narrow grammar such as
`[a-z][a-z0-9_-]*`; reserve `:`, `/`, `.`, and whitespace for selector parsing and
paths. Unicode remains available in titles and aliases.

### 2.4 A directory does not create web semantics

The existing glossary is a graph because definitions mention other known terms and the
reader computes a closure. The proposed filesystem layout alone would lose that
property. A real memory web needs a relation policy.

Do not force implicit phrase matching on every web. It is ideal for domain terminology,
but dangerous for ADR titles or a web whose aliases are common words. Conversely, do not
require every glossary definition to carry a hand-maintained link list; that would
discard one of the current implementation's best features.

Use one small policy on the web descriptor:

```yaml
linking: mentions # mentions | explicit | none
```

- `mentions` compiles strand titles and aliases and derives same-web references by
  scanning bodies, preserving the glossary's current behavior.
- `explicit` follows a validated, same-web `references` list in strand frontmatter.
- `none` provides indexed selection with no automatic closure.

Keep typed domain relations such as ADR `supersedes` inside web-specific `metadata` in
v1. They matter to presentation and validation, but they should not silently determine
how much text a read injects. Cross-web links can use SASE artifact relations or a later
explicit design; v1 closure should remain within one web.

### 2.5 Project/home precedence should shadow a whole web

There are two plausible overlay rules:

1. merge project and home strands by slug, or
2. let a project web shadow a same-named home web as one atomic unit.

Choose whole-web shadowing for v1. If the project contains either
`sase/memory/webs/<web>.md` or its companion strand directory, resolve that web entirely
from the project; otherwise fall back to `~/sase/memory/webs/<web>.md` and its
directory.

Strand-level union sounds flexible but produces a hybrid catalog whose descriptor and
policies come from one scope while some content silently comes from another. It also
reintroduces the global-glossary leakage that the current config intentionally forbids.
An explicit `extends: home` can be designed later if real use cases justify composition.

### 2.6 A descriptor must be valid without a physical empty directory

Git does not preserve empty directories, so requiring every `<web>.md` to have an
existing `<web>/` directory makes an empty but valid web awkward to version. Define the
descriptor as the web's existence marker. A missing companion directory means zero
strands; a directory without its descriptor is invalid. Once a strand exists, normal
filesystem behavior materializes the directory.

Only direct `*.md` children are strands in v1. Reject nested directories, duplicate
normalized titles/aliases, symlinks escaping the selected memory root, malformed
frontmatter, and reserved names. Ignore editor backup files rather than interpreting
them as strands.

### 2.7 “Read the whole web” should be literal but observable

Honor the requested contract: `sase memory read <web>` prints the web preamble and every
strand. Do not silently summarize or truncate, because an audited read should mean what
its selector says. The JSON form should report the selected strand count and byte count,
and rich output may warn before a very large result. Agents should normally use a
keyword selector; the generated instruction text should say so.

For targeted reads, web policy determines reference closure. A glossary web should
default to full mention closure to preserve today's behavior. An ADR web should default
to depth zero even if it has explicit references. Keep `-d/--depth` as an override. The
effective depth and every transitively included strand belong in the audit event.

### 2.8 The generic substrate should not erase useful specialization

The current glossary has behaviors that are not implied by “a collection of Markdown
files”:

- Unicode-aware, code-aware phrase matching and conservative plural aliases;
- prompt semantic tokens, hover cards, and go-to-definition;
- an ACE glossary panel with a term rail, relation trail, and mutation actions;
- glossary-specific reports and read metadata.

The storage and catalog model can become generic while those surfaces continue to say
“Glossary.” An ADR browser will probably want status/date filters and supersession
edges, not prompt-wide highlighting of every decision title. Generalize a surface only
after a second web demonstrates shared interaction, not merely because both read files.

## 3. Recommended file contract

### 3.1 Web descriptor

```markdown
---
type: core
description: Project vocabulary needed to interpret SASE prompts and artifacts.
keyword: term
linking: mentions
default_depth: all
---

# Glossary

Run `sase memory read glossary:<keyword> [...] -r "<why>"` before relying on these
terms. Batch related terms into one read.
```

Recommended fields:

| Field           | Requirement | Meaning                                                            |
| --------------- | ----------- | ------------------------------------------------------------------ |
| `type`          | required    | `core` or `reference` (or `structured` if that naming is retained) |
| `description`   | required    | Compact Tier 2 text and list/help summary                          |
| `keyword`       | optional    | Singular display noun, default `strand`                            |
| `linking`       | optional    | `none` by default; `mentions` or `explicit` when needed            |
| `default_depth` | optional    | `0` by default; `all` for glossary-like closure                    |

The H1 is the web's display title and the remaining body is its preamble. For a core
web, memory initialization includes the preamble plus a generated deterministic roster
of strand titles and aliases in one Tier 1 section. For a reference web, Tier 2 includes
one entry using `description`; the preamble is returned by reads.

Do not write the generated roster back into the descriptor. Generated output belongs in
agent instruction files, not mixed into canonical user content. This eliminates the
current generated `sase/memory/glossary.md` artifact and its marker/conflict rules.

### 3.2 Strand

```markdown
---
title: Agent Clan
aliases: [clan]
---

An agent clan is a named, rootless container for agents that run in parallel.
```

For an explicitly linked web:

```markdown
---
title: Keep memory webs file-backed
aliases: [file-backed memory webs]
references: [0003-audited-memory-reads]
metadata:
  status: accepted
  date: 2026-08-24
  supersedes: []
---

## Context

...

## Decision

...

## Consequences

...
```

`title` is required and single-line. `aliases` is an optional list of unique single-line
strings. `references` is allowed only when the web uses `linking: explicit` and contains
same-web stable slugs. `metadata` is an opaque mapping preserved for web-specific
adapters; generic memory code must not assign semantics to arbitrary keys.

The body is the content returned to an agent. It should not need a duplicate H1 because
the renderer supplies a heading from `title`.

### 3.3 Glossary migration

The SASE migration should produce:

```text
sase/memory/webs/glossary.md
sase/memory/webs/glossary/agent-clan.md
sase/memory/webs/glossary/agent-family.md
...
sase/memory/webs/glossary/xprompt-workflow.md
```

`bob-cli` gets the same descriptor plus four strands. A deterministic migration command
or one-off script should:

1. parse and validate the existing catalog through the current Rust validator;
2. derive a stable slug for each canonical term, stopping on collisions;
3. write one strand with `title`, configured aliases, and the exact definition body;
4. reload the new web and compare normalized catalog entries and relation closure;
5. remove `memory.glossary` only after parity succeeds;
6. run `sase memory init` and verify generated instructions.

During transition, declaring both `memory.glossary` and a `glossary` web should be a
hard error. Precedence would hide drift and leave editors unsure which source to open.

## 4. Command and audit contract

### 4.1 One repeatable selector grammar

Extend both `read` and `show` to accept one or more selectors:

```text
TARGET := NOTE_PATH | WEB | WEB:KEYWORD
```

Examples:

```bash
sase memory read cli_rules.md -r "Need CLI rules"
sase memory read glossary:stitch glossary:patch -r "Need change-unit terms"
sase memory read 'glossary:Agent Hood' -r "Need hood semantics"
sase memory read decisions:0007-memory-webs -r "Need the governing decision"
sase memory read decisions -r "Audit the complete decision log"
```

Plain paths retain their current `.md` grammar. A bare non-path token names a web. Split
the first `:` only, but forbid colons in stable slugs. Resolve an entire batch before
writing an audit event or printing output; one unknown/ambiguous selector makes the
whole request fail, matching current glossary batch safety.

`show` must remain behaviorally identical without the audit side effect. `list` should
show plain notes and webs; a `--web <name>` filter can list strands without adding a new
command group. Avoid inventing generic create/delete commands in v1. Users can author
files, the Memory panel can grow a nested editor, and the old glossary mutation wrappers
can temporarily write strand files.

### 4.2 Preserve compatibility deliberately

For at least one deprecation window:

- `sase glossary read A B` translates to `sase memory read glossary:A glossary:B`.
- `show`, `all`, `list`, and `log` become thin compatibility adapters over generic web
  operations.
- `add` and `del` keep their current UX but write/remove glossary strand files and run
  memory initialization.
- `#memory/glossary` continues to expand the rendered glossary hub through a virtual
  compatibility alias even though the canonical descriptor is
  `sase/memory/webs/glossary.md`.

Do not dual-write the YAML catalog and strand files. Compatibility must have one
canonical source.

### 4.3 Unify the audit event, not just the command spelling

Today glossary reads and ordinary memory reads have separate JSONL schemas and log
views. Introduce a versioned memory-read event that can represent both:

- original selectors;
- canonical plain-note path or web name;
- requested strand slugs;
- transitively included strand slugs;
- effective depth and linking policy;
- project/home origin and resolved source paths;
- bytes returned, reason, agent identity, timestamp, and artifacts directory.

`sase memory log --web glossary`, `--keyword stitch`, and `--path cli_rules.md` can then
share one report engine. Keep old-event readers so historical logs remain visible; there
is no need to rewrite immutable JSONL history.

## 5. Rendering, resolution, and implementation boundary

### 5.1 Instruction rendering

Memory initialization should construct one effective catalog for the selected scope,
then render:

- every core plain note as it does today;
- every core web as one Tier 1 section: descriptor preamble plus compact strand roster;
- every top-level reference plain note as one Tier 2 entry;
- every reference web as one Tier 2 entry with a targeted-read instruction.

Strands must not each become Tier 1/Tier 2 headings. That would make the size of the
agent instruction file proportional to the entire corpus and defeat progressive
disclosure. Current context-engineering guidance explicitly favors lightweight
identifiers and filesystem metadata that let agents retrieve detail just in time.

The Tier anchors should change in one preparatory migration:

```markdown
## 1. Tier 1 (core) Memory

## 2. Tier 2 (reference) Memory
```

Parsers should accept both old and new headings during a compatibility period while
renderers emit only the new form. Likewise, accept legacy `short`/`long` frontmatter
with a deprecation diagnostic, but make `sase memory init` migrate owned files and
`--check` reject lingering project drift after the transition window.

### 5.2 Shared core versus Python

The existing Rust boundary is directionally correct. Shared web/strand behavior would be
needed by the CLI, ACE, the XPrompt LSP, and future frontends, so it belongs in
`sase-core`:

- wire types for web descriptors, strand entries, source locations, diagnostics, and
  resolved catalogs;
- stable slug/title/alias normalization and collision validation;
- selector resolution;
- compiled phrase matching for `linking: mentions`;
- deterministic reference closure and reverse relations.

Python should continue to own:

- project/home root discovery and whole-web shadowing;
- source-preserving YAML/Markdown reads and writes;
- filesystem containment and symlink checks;
- CLI orchestration, rich/Markdown/JSON rendering, and audit-log persistence;
- `sase memory init` planning and generated document synchronization;
- compatibility adapters and ACE integration.

Do not delete the Rust glossary module first. Introduce a generic strand-catalog API,
port the glossary facade onto it, compare old/new catalog payloads in tests, then rename
or retire glossary-specific Rust types once all consumers have moved. The Python package
can follow the same adapter-first sequence.

### 5.3 LSP and ACE

The file migration improves source navigation: hover and go-to-definition should point
directly at the strand file instead of a YAML mapping range. The launcher-generated LSP
catalog should become a versioned “phrase-enabled memory webs” catalog; the glossary is
its first member.

Keep the Glossary panel's name and specialized controls initially, but make its data
adapter read the generic catalog. Extend the Memory panel to display web descriptors and
nested strands. Only after an ADR pilot should SASE decide whether a generic Web panel
is useful or whether glossary and decisions deserve distinct domain panels.

## 6. Delivery plan and test strategy

### Phase 1: terminology compatibility

- Add `core`/`reference` enum values and new Tier headings.
- Read legacy `short`/`long` values and headings; render the new names.
- Update templates, docs, skills, generated README text, diagnostics, tests, and
  provider shims in one coherent change.
- If the product name remains `structured`, substitute it here; do not otherwise alter
  the design.

### Phase 2: generic read-only web substrate

- Add descriptor/strand discovery, validation, whole-web scope resolution, and
  rendering.
- Add `NOTE_PATH | WEB | WEB:KEYWORD` selectors to `memory show/read`.
- Add generic audit schema v2 and legacy log readers.
- Render one instruction entry per web.
- Put user-visible routing behind the required temporary feature flag until both paths
  pass parity tests.

### Phase 3: glossary parity and data migration

- Back the current glossary facade, LSP payload, ACE adapter, and mutation engine with a
  `glossary` web.
- Add old-versus-new golden tests for all SASE and `bob-cli` terms: normalization,
  aliases, derived plurals, spans, reference closure, reverse links, Markdown output,
  and source locations.
- Migrate both repositories and regenerate agent instructions.
- Reject dual definitions.

### Phase 4: compatibility retirement and ADR pilot

- Deprecate then remove `memory.glossary` and `sase glossary` after the advertised
  window.
- Create a small `decisions` reference web using stable numbered slugs,
  `linking: explicit`, `default_depth: 0`, and status/supersession metadata.
- Use the pilot to decide which listing, filtering, mutation, and ACE behaviors truly
  belong to all webs.

The test matrix must include:

- valid descriptor-only empty webs and invalid orphan strand directories;
- slug, title, alias, and normalization collisions;
- project whole-web shadowing and home fallback;
- deterministic ordering and byte-stable Markdown/JSON output;
- mixed note/web batches, all-or-nothing failures, cycles, and depth limits;
- symlink escape, traversal, malformed frontmatter, and non-Markdown files;
- audit-before-output guarantees and historical log compatibility;
- exactly one generated Tier section per web;
- old/new glossary closure parity and source navigation;
- ACE/LSP catalog cache invalidation and visual snapshots;
- `sase memory init --check`, repository validation, and both migrated projects.

## 7. Risks and non-goals

### Main risks

- **Context blow-up:** a core web roster or whole-web read can become large. Keep core
  web bodies compact, expose byte/strand counts, and make targeted reads the documented
  default.
- **Semantic over-generalization:** glossary phrase matching is not a universal memory
  behavior. Keep it opt-in.
- **Migration breadth:** changing storage and naming touches many independently useful
  surfaces. Adapters and golden parity are cheaper than a synchronized rewrite.
- **Identity drift:** titles are human-facing and will change. Stable slugs must own
  links and logs.
- **Scope surprise:** implicit home/project merges make a catalog irreproducible. Shadow
  whole webs.
- **Duplicate truth:** accepting YAML and files simultaneously will inevitably drift.
  Fail closed.
- **ADR mutation:** accepted ADRs should not be casually edited by generic memory tools.
  A decisions adapter should validate lifecycle rules and prefer superseding records.

### Non-goals for v1

- global full-text or embedding search;
- arbitrary graph queries or visualization;
- nested webs or nested strand directories;
- cross-web recursive closure;
- a plugin schema for every possible strand metadata field;
- automatic agent writes into canonical webs;
- replacing domain-specific UIs merely to obtain consistent naming.

## 8. Sources

Repository evidence:

- SASE: `docs/memory.md`, `docs/configuration.md`, `src/sase/memory/`,
  `src/sase/glossary/`, `src/sase/main/init_memory/glossary.py`,
  `src/sase/main/init_memory/root_rendering_notes.py`, `src/sase/amd/_memory.py`,
  `src/sase/xprompt/glossary_catalog.py`, the ACE glossary/memory panels, and related
  parser, audit, LSP, and test files.
- `sase-core`: `crates/sase_core/src/glossary.rs`, config provenance validation, PyO3
  glossary bindings, and XPrompt LSP glossary consumers.
- `bob-cli`: `sase/sase.yml`, its generated glossary memory, and generated agent
  instruction files.

External sources:

- Niklas Luhmann Archive: bibliographic record for
  [“Communicating with Slip Boxes”](https://niklas-luhmann-archiv.de/bestand/bibliographie/item/luhmann_2015_T-AW01).
- Zettelkasten Method:
  [Introduction to the Zettelkasten Method](https://zettelkasten.de/introduction/)
  (stable note addresses, hub/structure notes, and cross-links).
- Michael Nygard:
  [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
  (the original small-file ADR proposal).
- AWS Prescriptive Guidance:
  [Architectural decision record process](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html)
  (decision-log overview/detail use, lifecycle, immutability, and supersession).
- Packer et al.:
  [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560)
  (hierarchical in-context/external memory management).
- Sumers et al.:
  [Cognitive Architectures for Language Agents](https://arxiv.org/abs/2309.02427)
  (modular memory and structured internal actions).
- Anthropic:
  [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  and [How Claude remembers your project](https://code.claude.com/docs/en/memory)
  (hybrid up-front/on-demand context, progressive disclosure, and concise startup
  memory).

## 9. Recommended solution and future uses

Implement **file-backed, project-or-home memory webs** as an orthogonal extension of
plain memory notes:

- `sase/memory/webs/<web>.md` is the hub, policy, and instruction entry;
- `sase/memory/webs/<web>/<strand>.md` contains one independently addressable idea or
  record;
- the hub declares `core` or `reference`, while strands inherit it;
- stable filename slugs own identity, and titles/aliases own presentation and friendly
  lookup;
- project webs shadow same-named home webs atomically;
- generic explicit references make a collection into a web, while opt-in phrase matching
  preserves glossary behavior;
- `sase memory read` and `show` accept repeatable file, web, and web-strand selectors;
- one versioned audit model records both ordinary and web reads;
- Rust owns shared catalog/validation/matching/closure behavior, while Python owns
  filesystem scope, rendering, logging, initialization, and compatibility;
- old glossary commands remain adapters until SASE and `bob-cli` have passed full
  catalog, LSP, ACE, generated-instruction, and audit parity.

Use **core memory** as the Tier 1 name. Prefer **reference memory** for Tier 2; if the
chosen product term remains **structured memory**, define it strictly as the on-demand
delivery class and otherwise implement the same model.

After the glossary, pilot a `decisions` reference web. Good later candidates are:

- **runbooks** — one operational procedure or recovery scenario per strand;
- **failure modes** — recognizable symptoms, diagnosis, remediation, and prevention;
- **invariants** — one system invariant with rationale and known enforcement points;
- **policies** — review, security, release, or compatibility policies too detailed for
  core instructions;
- **domain concepts** — product or organization vocabulary beyond a single glossary;
- **integration contracts** — one external service's assumptions, limits, and failure
  behavior per strand;
- **design patterns and anti-patterns** — locally accepted patterns with examples and
  counterexamples;
- **experiments and lessons** — durable findings whose evidence and conclusion can be
  read independently;
- **threats and mitigations** — one threat model claim, trust boundary, or mitigation
  decision per strand;
- **data semantics** — one event, metric, field family, or lifecycle definition per
  strand.

The selection test is simple: create a web when the knowledge has a stable collection
identity, multiple independently useful members, and meaningful links or lookup keys.
Keep a plain note when the content must be understood as one document. Keep volatile
tasks, chronological chatter, generated API documentation, and facts derivable from the
code out of both.
