# Docs as a Managed Corpus, Memory as the Agent Index

**Researcher:** grk (independent swarm report)
**Date:** 2026-10-15
**Question:** Should some SASE memories migrate into `docs/`, should project documentation become a first-class representation of memory, and how should documentation be structured so agents can maintain it?

This report does not consult peer swarm reports. It uses the current sase checkout, SASE memory and decisions, the research sidecar layout, and public sources on Diátaxis, `llms.txt`, `AGENTS.md`, and agent-docs evals.

---

## 1. Recommendation

Keep the two corpora. Do not merge them.

- **`sase/memory/`** stays the agent-facing operating layer: compact rules, when-to-read indexes, decision/glossary/task-type webs, and generated excerpts of facts that agents must not guess.
- **`docs/`** stays the human-facing product handbook: tutorials, how-tos, explanation, and exhaustive reference, published at sase.sh.
- **Instruction bundles / `AGENTS.md`** stay a compiled projection of memory, not of `docs/`.

The useful version of the user's plan is: give `docs/` memory-*like governance* (catalog, kind metadata, size gates, ownership, drift checks, a write convention) and give agents a **short docs map** the way reference memory already lists notes. The harmful version is: move memory notes into `docs/`, treat MkDocs pages as `type: core|reference` memory, or expect agents to `sase memory read` 4,000-line handbook pages.

`sase/memory/macros.md` is the wrong example to migrate. It is a 167-line agent grammar and launch contract. `docs/macros.md` is a 4,082-line human reference. The memory file already defers to the docs page for the full hold-directive contract. Deleting the memory note would either dump ~4k lines into every macros-related turn or leave agents with a one-line "go read the handbook" hint, which evals show they skip.

**Do this instead, in order:**

1. Classify every memory note and every docs page (keep / excerpt / point / split). Move almost nothing in the first pass.
2. Split the six monster docs pages and tag every page with a Diátaxis kind plus `related_memory`.
3. Generate a docs map (`docs/MAP.md` in-repo, `/llms.txt` on the site) from that metadata.
4. Put a compressed copy of that map into reference memory, in the Vercel "8 KB index" style, so agents know *which file to open*.
5. Add drift tests for the overlapping facts (macros directives, beads lifecycle, artifact identity, dispatch contract).
6. Add a thin `sase docs check` only after the map and splits exist. Do not build docs retrieval, docs-as-memory types, or a second instruction compiler.

That is a docs-as-code plus agent-index program. It is not a memory-migration program.

---

## 2. Critique of the plan

The plan mixes three problems that want three different treatments.

| User instinct | Verdict | Why |
| --- | --- | --- |
| Some memories belong in `docs/` | Mostly false for the current corpus; true for a few *facts* that are duplicated, not for the notes | Memory notes are already the compact remainder. The pain is drift, not location. |
| Documentation should be a first-class representation of memory | True for *governance*, false for *delivery* | Same catalog/check/write discipline. Different load path, audience, and size budget. |
| Docs should be structured so agents can maintain them | True, and the highest-leverage part | Current `docs/` is a 60k-line handbook with six pages over 2,000 lines and almost no page metadata. |

### 2.1 Migrating memory into `docs/` solves the wrong failure

The failure today is **two hand-maintained texts about the same subsystem**, not **memory living in the wrong directory**.

Measured on this checkout:

| Topic | Docs page | Memory note |
| --- | --- | --- |
| Macros | `docs/macros.md` 4,082 lines / 244 KB | `sase/memory/macros.md` 167 lines / 15 KB |
| TUI | `docs/ace.md` 9,771 lines / 740 KB | `sase/memory/tui.md` 17 lines |
| Configuration | `docs/configuration.md` 7,768 lines | `sase/memory/sase_flags.md` 77 lines (flags only) |
| Beads | `docs/beads.md` 3,046 lines | `sase/memory/sase_beads.md` 150 lines, **generated** |
| Artifacts | `docs/artifact_references.md` + `artifact_links.md` ~627 lines | `sase/memory/sase_artifacts.md` 108 lines, **generated** |
| Dispatch | `docs/remote_dispatch.md` 357 lines | `sase/memory/dispatch.md` 60 lines |
| CLI conventions | `docs/cli.md` 1,026 lines | `sase/memory/cli_rules.md` 42 lines |
| Lint/test | `docs/development.md` 1,407 lines | `sase/memory/lint_and_test.md` 160 lines |

Memory is already one to two orders of magnitude smaller. Several generated notes state the design out loud. The beads template says the note covers "only what that help output cannot tell you." The artifacts template says `sase artifact -h` owns exhaustive flags and the note owns "domain boundaries and safety rules agents must remember."

That is the correct split. Migrating `macros.md` into `docs/` would throw away the compact layer and keep the encyclopedia.

Notes that are *not* docs-shaped at all, and must stay in memory:

- `gotchas.md` (10 lines of agent-only landmines)
- `lint_and_test.md` (when an agent must run `just check`, the check-full prohibition)
- `generated_skills.md` (chezmoi deploy guards)
- `symvision.md`, `tui_screenshot.md`, `tui_perf.md` (agent operational runbooks)
- the `decisions`, `glossary`, and `task_types` webs (instruction-rendered catalogs with `sase memory read` addressing)

A memory task bead already exists as a type. Stale agent rules belong there. Stale handbook prose belongs in an ordinary docs edit.

### 2.2 "Docs as first-class memory" collapses two audiences

Memory is loaded into every SASE agent turn, or listed so the agent knows when to pay for a read. Docs are loaded by a human browser, a PDF handbook, and occasionally by an agent that already knows which path to open.

If docs pages became `type: core`, every turn would pay for a 60k-line handbook. Codex's explicit instruction slot is 32 KiB and Grok's is 120 KiB (`decisions:instructions-per-invocation`). `docs/ace.md` alone is ~740 KB. That cannot enter the bundle.

If docs pages became `type: reference`, agents would need `sase memory read` for handbook pages, audited reasons, and the memory-write skill before editing a getting-started tutorial. That is the wrong authorization model: product docs are ordinary repo files; memory is context every future agent pays for.

If docs were merely *aliased* into the memory catalog without new types, you would still inherit memory's fail-closed validators, web descriptors, parent trees, and `sase memory init` regeneration. That is a large mechanism in search of a corpus that already has MkDocs, `just docs-check`, and a deploy workflow.

SASE already rejected speculative retrieval three times (`decisions:corpus-before-mechanism`). Building "docs memory" as a fourth retrieval surface, before a classified corpus and a map, repeats that mistake.

### 2.3 Structuring docs for agents is the good idea, and it is independent

This part of the plan is right and should lead.

Current `mkdocs.yml` nav is a tour ("Getting Started", "The Basics", "Beyond the Basics", "The Nitty Gritty", "Integrations", "Reference", "Blog"). That is a human reading path, not a kind system. Individual pages mix kinds: `docs/macros.md` is tutorial motivation, how-to, CLI reference, and explanation in one file. `docs/ace.md` is a 9,771-line TUI encyclopedia. `docs/configuration.md` is 7,768 lines of reference.

Docs maintenance for agents is currently:

- `just docs-check` (`mkdocs build --strict`)
- a handful of lock tests (`test_docs_macro_bundled_skills_table_matches_packaged_sources`, macro-terminology tests, provider tables)
- no page frontmatter schema (except blog posts)
- no page size gate
- no "when to read this page" index
- no docs analog of `/sase_memory_write`
- `docs/agent_auto_restart.md` exists on disk and is **unlisted** in nav (57 nav entries, 57 non-blog pages, one orphan)

Agents can already `Read` a docs path. They cannot cheaply *choose* one. That is the Vercel result below: on-demand docs fail when the agent must decide to open them; a short always-loaded index succeeds.

### 2.4 The 2026-05 "zettel as canonical, memory as projection" idea is the ancestor — and docs can play that role without a third store

The draft blog post `docs/blog/posts/whats-next-memory-mobile-web.md` (May 2026) sketched canonical zettel plus generated memory projections, with inbox promotion and retrieval as later phases. It stayed on the shelf for poisoning, projection cost, and retrieval determinism. `corpus-before-mechanism` then forbade shipping retrieval ahead of a corpus.

Using **existing `docs/`** as the human-canonical layer, instead of inventing a zettel store, is the version of that idea that already has a corpus: ~60k lines, a public site, CI, and PDF. Memory already is the projection layer for beads, artifacts, sizes, task types, and `sase.md`. The missing piece is a **docs map plus excerpt/ownership rules**, not a new knowledge base.

---

## 3. What SASE already is

SASE is not a naive `AGENTS.md` dump. It already has the three-layer context stack the rest of the industry is still converging on.

### 3.1 Delivery stack

| Layer | Role | Load | Owner |
| --- | --- | --- | --- |
| Core memory | Always-true agent facts and landmines | Inlined into every instruction bundle | `type: core` notes; generated `sase.md` |
| Memory webs | Catalog of keyed records | Descriptor inlined; strand bodies on demand | `decisions`, `glossary`, `task_types` |
| Reference memory | Domain runbooks with a one-line trigger | Index always loaded; body via `sase memory read` | `type: reference` notes |
| Skills / macros | Procedures | On demand, by invocation | `sase/macros/`, generated `SKILL.md` |
| Docs | Human handbook | Never in the bundle; agent `Read` if they know the path | `docs/` + MkDocs |
| Instruction bundles | Per-invocation compiled view of the above memory layers | Adapter channel; native SASE files suppressed | `decisions:instructions-per-invocation` |

`sase memory init` already regenerates `AGENTS.md`, provider shims, `sase/memory/README.md`, and the generated notes. `/sase_memory_write` already forbids casual memory edits. Audited reads already exist. History already exists (`docs/memory_history.md`, `sase memory history`).

The architecture the user wants for docs — catalog, check, generated views, write discipline — **already exists for memory**. Cloning it onto `docs/` wholesale would duplicate it. Teaching docs to *feed* that architecture with a map and a few generated excerpts is the reuse.

### 3.2 Generated notes are the existence proof for projections

These files are not hand-maintained agent essays. They are templates under `src/sase/main/init_memory/templates/`:

- `memory-sase.template.md` → `sase/memory/sase.md`
- `memory-sase-artifacts.template.md` → `sase/memory/sase_artifacts.md`
- `memory-sase-beads.template.md` → `sase/memory/sase_beads.md`
- `memory-sase-sizes.template.md` → `sase/memory/sase_sizes.md`
- `memory-sase-task-types.template.md` → `sase/memory/task_types.md`

They already encode "CLI/docs own the encyclopedia; memory owns the agent remainder." Extending that pattern to macros *tables* (directive roster, discovery order) is a small generator change. Replacing the memory note with the handbook is not.

### 3.3 Cross-links already exist, as prose, not as a contract

Memory already points at docs in several places:

- `sase/memory/macros.md` → `docs/macros.md` Hold Directive and `docs/cli.md`
- `sase/memory/dispatch.md` → `docs/remote_dispatch.md`
- `sase/memory/cli_rules.md` → `docs/plugins.md`
- `sase/memory/tui_perf.md` → `docs/perf_runbook.md`
- `sase/memory/rust_core_backend_boundary.md` → `docs/rust_backend.md`

Docs already describe memory as a product feature (`docs/memory.md`, `docs/memory_history.md`, `docs/content_layout.md`, `docs/instruction_bundles.md`).

What does not exist: a machine-checkable `related_docs` / `related_memory` pair, a test that the two texts do not contradict, or a generated index that lists "if you are doing X, open Y."

### 3.4 Token budget of the current memory corpus

From `sase/memory/README.md` on this checkout:

- 19 flat notes (3 core, 13 reference, 3 web descriptors)
- 1,554 lines, ~22,182 tokens **for the whole memory tree including unread reference bodies**
- `AGENTS.md` itself is 305 lines (core + web descriptors + the reference *list*)

That is already near Anthropic's "keep CLAUDE.md under 200 lines" advice for the always-loaded file, and well inside Codex's 32 KiB slot only because reference *bodies* are not inlined. There is no headroom to ingest handbook pages.

---

## 4. External evidence

### 4.1 Diátaxis: kind before location

[Diátaxis](https://diataxis.fr/) (Daniele Procida) splits documentation into four needs: tutorials (learning), how-to guides (tasks), reference (information), explanation (understanding). Cloudflare, Gatsby, and many others used it as the north star for IA. The claim that matters here is not "make four directories." It is: **a page that tries to be two kinds is unmaintainable**, for humans and for agents.

SASE's current `docs/` fails that test at the page level. `macros.md`, `ace.md`, `configuration.md`, `llms.md`, and `beads.md` are mixed-kind dumps. An agent asked to "update the hold directive" cannot be told "edit the reference page"; it has to search a 4,000-line mixed file. A human trying to learn macros has to skip CLI tables.

Applying Diátaxis here means:

- required `kind:` frontmatter on every docs page (`tutorial` / `how-to` / `reference` / `explanation` / `runbook` / `blog`)
- split mixed pages until each file has one kind
- nav can stay tour-shaped for humans; the *files* become addressable

Do not block on a four-folder rename. Kind metadata plus splits is enough for agents. Folder moves can follow.

### 4.2 `llms.txt`: an index, not a dump

Jeremy Howard's [`llms.txt` v2](https://llmstxt.org/) (updated 2026-08-10) is a small Markdown file at `/llms.txt`: H1, summary blockquote, then H2 sections of links with one-line notes. It is a reading list. `llms-full.txt` (full concatenated docs) is a vendor convention, **not** in the spec. Google Search ignores `llms.txt`. Its remaining job is **coding agents and docs assistants**.

sase.sh today has `docs/robots.txt` and a sitemap. It has no `/llms.txt`. Confusingly, `docs/llms.md` is the LLM *providers* reference, not this file. A site-level `llms.txt` should be generated from nav + page summaries, not hand-written, and must not be named in a way that collides with `llms.md`.

For SASE *agents*, the in-repo analog is more important than the public file: a `docs/MAP.md` (or generated section of a reference memory note) with the same shape — title, one-line when-to-read, path. That is what Vercel found works.

### 4.3 Vercel (2026-01): a compressed docs index in `AGENTS.md` beat skills

Vercel taught agents Next.js 16 APIs that were absent from training data ([blog](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)):

| Configuration | Pass rate |
| --- | --- |
| No docs | 53% |
| Skill, agent decides | 53% (skill never invoked in 56% of cases) |
| Skill, explicit "use the skill" | 79% |
| **8 KB compressed docs index in `AGENTS.md`** | **100%** |

They started from a 40 KB dump, compressed 80% to an index of *paths*, and kept the 100% pass rate. The instruction that mattered was "prefer retrieval-led reasoning over pre-training-led reasoning." Skills remained the right shape for *vertical procedures* ("upgrade Next.js"), not for general framework knowledge.

SASE already has the skill/procedure layer (macros, generated skills) and the always-loaded index layer (reference memory descriptions). What it lacks is the **docs path index**. Adding that index is the empirically supported move. Putting handbook pages into memory, or hoping agents will open `docs/macros.md` because it exists, is the 53% cell.

### 4.4 ETH Zurich / LogicStar (arXiv:2602.11988): more `AGENTS.md` is not more success

Gloaguen et al., *Evaluating AGENTS.md* ([arXiv:2602.11988](https://arxiv.org/abs/2602.11988), v3 2026-09-29): context files do not generally improve SWE-bench / CTXbench success, and they raise inference cost by over 20%. Agents *follow* the instructions, which produces more exploration and testing, not more correct patches. Repository overviews do not help. Developer-written files beat LLM-generated ones (~7%). The authors' conclusion: context files should contain **non-standard practices and minimal extra requirements**, not project tours.

This is a direct warning against:

- inlining `docs/` into instruction bundles
- generating a "docs memory" dump with an LLM
- adding handbook overviews to core memory

It supports SASE's current core notes (`gotchas`, rust-core boundary, workspace rules) and argues for keeping them small.

A second study (Lulla et al., arXiv:2601.20404) found `AGENTS.md` *reduced* median runtime ~29% and output tokens ~17% on a 124-PR corpus, with comparable completion. Those two papers do not agree on cost, but they agree on the content rule: **short, specific, non-inferable**.

### 4.5 Industry consensus on where a line goes

Convergent advice from Anthropic's steering post, the `AGENTS.md` convention, and independent write-ups (Vorp, 5dive, Codeminer):

| Content | Home | SASE analog |
| --- | --- | --- |
| Always-true facts, don'ts, done-means | `AGENTS.md` / core | Core memory |
| Occasional procedures | Skill | Macro / generated skill |
| Exhaustive reference | Docs, linked from an index | `docs/` + reference memory index |
| Enforcement | Hooks, CI, permissions | `just check`, doctor, finalizers, `/sase_memory_write` |

Natural-language files are context, not a security boundary. SASE already puts "never commit yourself" in core and enforces it with host-owned finalizers. Docs will not make that stronger.

### 4.6 Agent-maintainable docs in the wild

The pattern that actually helps agents edit docs is boring:

1. One kind per file, with a template.
2. Frontmatter an agent can parse (`kind`, `audience`, `owner`, `when_to_read`, `related_*`).
3. Size limits so a page stays in one read.
4. Tests that lock tables generated from code (SASE already does this for bundled skills).
5. A map at the top of the tree.

The anivar `developer-docs-framework` skill (Diátaxis + 27 rules) is a procedure pack for writing docs, not a reason to store the handbook in memory. If SASE wants agents to *maintain* docs, a **docs-writing skill** plus page templates is the right shape. That is a skill, not a memory type.

---

## 5. Adjusted requirements

These replace or narrow the user's stated requirements. Each is an explicit delta.

**A. Do not migrate memory notes into `docs/` as the default action.**
Replace with a classify-first rule: keep, excerpt, point, or split. Migration of a whole note is allowed only when the note contains no agent-operational rules and is a worse copy of an existing docs page.

**B. Do not make `docs/` a memory kind, a `sase memory read` target, or part of `sase memory init`.**
Replace "first-class representation of memory" with "first-class managed corpus": catalog, metadata, check, ownership, write convention. Delivery stays `Read` of a path named by the docs map.

**C. Do not inline handbook pages into instruction bundles.**
Hard constraint from Codex 32 KiB / Grok 120 KiB and from arXiv:2602.11988. The always-loaded docs artifact is an *index*, budgeted like reference-memory descriptions (target: well under 8 KB compressed, Vercel-style).

**D. Require a Diátaxis `kind` (or SASE's slightly extended set) on every docs page, and split mixed pages before adding retrieval.**
This is the structure requirement, made testable. The six pages over 2,000 lines (`ace`, `configuration`, `macros`, `llms`, `beads`, `notifications`) are the first split set.

**E. Treat overlapping topics as one fact table with two renderings, not two essays.**
Canonical owner is whichever layer already generates: CLI help and init templates for beads/artifacts/sizes; docs for user narrative; memory for agent don'ts. Add drift tests. Optionally generate shared tables (macro directive roster, discovery order) from one source.

**F. Follow `corpus-before-mechanism`.**
No `sase docs read`, no docs web, no embedding index, no keyword trigger for docs, until (1) pages are split and tagged, (2) a map exists, and (3) there is a measured failure of agents finding the right page *given the map*. The map is the mechanism the current corpus already justifies, because the corpus is 60k lines of unindexed mixed pages.

**G. Add a docs write convention, thinner than `/sase_memory_write`.**
Agents may edit `docs/` as ordinary project files when the task is a docs change. They must not invent pages, grow a page past its size budget, or change `kind` without a plan. A short skill (`/sase_docs` or a section in `lint_and_test.md`) is enough at first. A fail-closed write skill like memory is not justified until docs edits become a measured source of handbook damage.

**H. Keep `macros.md` memory.**
Tighten it toward the beads/artifacts pattern: grammar and launch rules the agent must not skip; pointers with anchors into the split docs reference. Do not replace it with "read `docs/macros.md`."

**I. Publish `/llms.txt` for external agents; keep the in-repo map as the source of truth.**
One generator, two outputs. Do not hand-author a third copy. Do not name the generator output `docs/llms.md`.

---

## 6. Recommended solution

### 6.1 Architecture

```text
code, CLI help, config schema, init templates
        |                         |
        | generated               | generated
        v                         v
  sase/memory/* excerpts     docs/* handbook pages
  (agent remainder)          (human narrative + exhaustive reference)
        |                         |
        | sase memory init        | docs map generator
        v                         v
  instruction bundle         docs/MAP.md  +  /llms.txt
  (core + web descriptors    (when-to-read index)
   + reference LIST
   + compressed docs map)
```

Ground truth for *behavior* is code. Ground truth for *how a human learns it* is `docs/`. Ground truth for *what an agent must not get wrong this turn* is `sase/memory/`. Those three are allowed to share generated tables. They are not allowed to share identity.

### 6.2 Classification of the current memory corpus

| Note | Action | Reason |
| --- | --- | --- |
| `gotchas.md`, `rust_core_backend_boundary.md`, `sase.md` | Keep core | Non-inferable, cheap, always true |
| `lint_and_test.md`, `generated_skills.md`, `symvision.md`, `sase_flags.md`, `tui*.md` | Keep reference | Agent operational; docs are the human version of a *different* slice |
| `sase_artifacts.md`, `sase_beads.md`, `sase_sizes.md`, `task_types.md` | Keep generated | Already the projection pattern |
| `macros.md` | Keep; tighten; add drift tests and anchors | Agent grammar + VCS launch contract; docs own the encyclopedia |
| `dispatch.md`, `cli_rules.md` | Keep; add `related_docs` and a contradiction test | Already point at docs; size is fine |
| `decisions` / `glossary` / `task_types` webs | Keep in memory | Instruction-rendered catalogs; publishing a *human* glossary page later is a docs add, not a move |
| `README.md` | Keep generated | Memory catalog; do not replace with `docs/memory.md` |

No current memory note is a good first candidate for wholesale move into `docs/`. The first "migrations" are **facts inside notes** (directive tables, discovery-order rows) into a shared generated fragment, not file moves.

### 6.3 Docs structure (the actual IA change)

**Page metadata** (YAML, required for `just docs-check`):

```yaml
kind: reference          # tutorial | how-to | reference | explanation | runbook | blog
audience: human          # human | agent | both  (agent-only pages are rare; prefer memory)
when_to_read: "When adding or changing a % directive"
related_memory: [macros.md]
owner: docs              # docs | memory | generated
size_budget_lines: 800
```

`audience: both` is for pages an agent should open *after* the map points there (CLI reference, remote dispatch). `audience: human` is the default. Agent-only content stays in memory.

**First split set** (pages > 2,000 lines):

1. `ace.md` → TUI tutorial / how-to / reference / visual-grammar already partly split (`artifacts_pane_*`). Continue until no TUI file exceeds the budget.
2. `configuration.md` → per-domain reference pages; keep a short index.
3. `macros.md` → `macros/index.md` (explanation), `macros/howto.md`, `macros/reference.md` (the contract the memory note points at), maybe `macros/directives.md`.
4. `llms.md` → per-provider reference; keep an index. Rename nothing to `llms.txt`.
5. `beads.md` → concepts vs CLI/lifecycle reference vs SDD how-to.
6. `notifications.md` → how-to vs reference.

Redirects already exist (`xprompt.md` → `macros.md`). Use the same plugin for splits.

**Size budget.** Pick a number and enforce it in `just docs-check`. 800–1,000 lines is a reasonable first cap: large enough for real reference, small enough for one agent read. Grandfather the monsters only until their split epic closes.

**Nav.** Keep a human tour in `mkdocs.yml`. Add a second, generated "By kind" index if wanted. Agents use `docs/MAP.md`, not the tour.

### 6.4 The docs map (the Vercel piece)

Generate `docs/MAP.md` from frontmatter + nav:

```markdown
# SASE docs map

Prefer these files over training data when the task matches `when_to_read`.

## Reference
- [Macro template reference](macros/reference.md): when changing #macros, %directives, or launch VCS
- [CLI reference](cli.md): when adding sase subcommands
...

## How-to
- [Remote dispatch](remote_dispatch.md): when using %dispatch
...
```

`sase memory init` (or a sibling `sase docs map`) copies a **compressed** form of that map into a new reference note, e.g. `sase/memory/docs_map.md`, listed in the Reference Memory section with description "Read when you need a handbook page and do not already know the path." The compressed form can be the Vercel pipe style if tokens get tight; a bullet list of 57 one-liners is probably enough and more readable.

Budget: the always-loaded *description* stays one line; the map body is on-demand unless measured miss-rate says it must be core. Start on-demand. Promote to core only if agents still fail to open it (Vercel needed it in the always-loaded file because they had no SASE-style reference list). SASE's reference list may be enough: one line, "read `docs_map.md` when choosing a handbook page."

### 6.5 Drift tests (the maintenance analog)

Start with four lock tests, modeled on `test_docs_macro_bundled_skills_table_matches_packaged_sources`:

1. Every `%` directive named in `sase/memory/macros.md` appears in the macros *reference* docs page (after split: `macros/directives.md`).
2. Bundled skill names in docs match packaged sources (already exists).
3. `sase/memory/dispatch.md` and `docs/remote_dispatch.md` share the same required selector rule (extract a single sentence or a small fixture).
4. Generated beads/artifacts memory notes still say they do not replace `-h` / onboard.

Do not try to NLP-diff 4,000-line files. Test the **named facts** that have caused or will cause agent error.

### 6.6 Management analog (what "manage similarly" should mean)

| Memory today | Docs analog to add | Docs analog **not** to add |
| --- | --- | --- |
| `type:` core/reference | `kind:` Diátaxis | `type: core` on a docs page |
| `sase memory list` | `sase docs map` / generated `docs/MAP.md` | Loaded-into-bundle dashboard |
| `sase memory init --check` | `just docs-check` plus frontmatter/size | Regenerating `AGENTS.md` from docs |
| `sase memory read` (audited) | Ordinary `Read`; optional later audit if map miss-rate is high | Mandatory audited docs reads |
| `/sase_memory_write` | Short skill: templates, size, kind, no new pages without a plan | Fail-closed write skill on every docs edit |
| Memory history pager | Git history + MkDocs; optional later | Duplicate the memory-history product |
| `[[wiki]]` links | Markdown links + `related_memory` | A second wiki syntax |

`just docs-check` already runs in docs-deploy CI. Extend it: required frontmatter, size budget, map freshness, no unlisted pages (`agent_auto_restart.md` is the canary).

### 6.7 Phasing (corpus before mechanism)

**Phase 0 — Classify (days, no product change).**
A table in a plan, not a feature: every memory note and docs page with keep/excerpt/point/split. This report's §6.2 is the memory half.

**Phase 1 — Structure the handbook (the docs epic).**
Frontmatter schema, size gate, split the six monsters, fix the unlisted page, generate `docs/MAP.md` and `/llms.txt`. Success: an agent given "change the hold directive" is one map lookup + one file under 800 lines from the answer.

**Phase 2 — Cross-corpus ownership (the drift epic).**
`related_memory` / `related_docs`, four lock tests, tighten `macros.md` memory toward the beads "remainder" voice, generate any shared tables that the tests want.

**Phase 3 — Agent index (the Vercel epic).**
New reference note `docs_map.md` (or a section of an existing note). Measure: instruction readout already tracks memory reads; add a cheap counter for `docs/` opens on docs-changing agents if needed. Promote the map to core only if the miss rate stays high.

**Phase 4 — Optional thin CLI.**
`sase docs check` as a wrapper around the new gates, if `just docs-check` is no longer enough. Stop. Do not start a docs web, docs retrieval, or docs-in-the-compiler.

Each phase ships something usable. None requires the later ones.

### 6.8 What success looks like

- Agent changing macros: reads `sase/memory/macros.md` (still), follows an anchor into `docs/macros/reference.md` (or `directives.md`), edits one kind-pure file, `just docs-check` and the directive lock test pass.
- Agent changing TUI: still hits `sase/memory/tui.md` then `tui_perf.md` / `tui_screenshot.md`; `docs/ace.md` is no longer a 9,771-line search space.
- Human on sase.sh: same or better nav; shorter pages; `/llms.txt` for external coding agents.
- Instruction bundle size: unchanged or smaller. No handbook bytes in core.

---

## 7. Risks and non-goals

**Split-and-redirect cost.** Splitting `ace.md` and `configuration.md` is real work and will churn MkDocs nav, PDF, and inbound links. Do it as its own epic with redirects. Do not couple it to memory-init changes.

**Dual-audience pages.** `audience: both` will be overused. Default to `human`. If a paragraph is an agent don't, it belongs in memory; link to it from docs if a human should see it too.

**Generated-table temptation.** Generating the entire macros handbook from code will produce unreadably complete reference. Generate *tables*, not chapters.

**Map staleness.** The map must be generated in `just docs-check` / `sase memory init --check`, fail-closed, same as glossary roster drift.

**External `llms.txt` theater.** Shipping `/llms.txt` without the in-repo map helps outsiders and does little for SASE agents. Do both from one generator, or skip the public file until the map exists.

**Non-goals:** vector search over docs; treating blog posts as memory; moving decisions or glossary out of memory; deleting `AGENTS.md` in favor of MkDocs; a third zettel store.

---

## 8. Direct answers

**Is this a good idea?**
The structure-and-governance half is a good idea and overdue. The "memories should live in `docs/`" half is not. The "docs are memory" half is a category error: docs are a corpus, memory is a delivery system for a tiny, expensive slice of that corpus.

**Would I take a different approach?**
Yes. I would not open with migration. I would open with classification, Diátaxis splits, a generated map, and drift tests on the overlapping facts. I would steal the generated-template pattern that beads and artifacts already use, and steal Vercel's compressed index, and stop before inventing docs-as-memory types. That is a smaller epic with a clearer eval: "agent finds the right page in one hop" and "instruction bundle does not grow."

**`macros.md` specifically?**
Keep the memory file. Split the docs file. Point with anchors. Lock the directive roster. Optionally generate the roster from one list. That is the whole macros work item.

---

## 9. Sources

### In-repo (this checkout)

- `sase/memory/README.md`, `sase/memory/macros.md`, `sase/memory/sase_artifacts.md`, `sase/memory/sase_beads.md`
- `docs/memory.md`, `docs/macros.md`, `docs/content_layout.md`, `docs/instruction_bundles.md`, `docs/instruction_inventory.md`, `docs/development.md` (Documentation Workflow), `mkdocs.yml`
- `src/sase/main/init_memory/templates/` (generated note templates)
- `src/sase/main/init_memory/root_rendering_notes.py`
- `tests/main/test_init_skills_sources.py` (`test_docs_macro_bundled_skills_table_matches_packaged_sources`)
- Decisions (via `sase memory read`): `corpus-before-mechanism`, `memory-webs`, `memory-links-are-authored`, `webs-render-in-their-own-section`, `instructions-per-invocation`
- `docs/blog/posts/whats-next-memory-mobile-web.md` (May 2026 zettel/projection sketch)

### External

- Diátaxis: <https://diataxis.fr/>
- `llms.txt` v2: <https://llmstxt.org/> (Howard, 2024; v2 2026-08-10)
- Vercel, "AGENTS.md outperforms skills in our agent evals" (2026-01-27): <https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals>
- Gloaguen et al., "Evaluating AGENTS.md" (arXiv:2602.11988, v3 2026-09-29): <https://arxiv.org/abs/2602.11988>
- Lulla et al., "On the Impact of AGENTS.md Files on the Efficiency of AI Coding Agents" (arXiv:2601.20404)
- Anthropic, "Steering Claude Code" (2026-06-18): <https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more>
- Agent-instruction best-practices summary (Kehoe, 2026-10): <https://mac.install.guide/ai/agent-instructions/best-practices>
- Vorp Labs, instruction-placement matrix: <https://vorplabs.com/blog/agent-instruction-placement-matrix>
- 5dive, "pushed / indexed / pulled": <https://blog.5dive.ai/blog/claude-md-skills-or-memory/>
