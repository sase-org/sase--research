# Docs as First-Class Memory: Should SASE Move Memory Into `docs/`, and How?

**Date:** 2026-10-15 · **Researcher:** `cld` · **Subject:** `sase` at `c2c2ffd4df` (master)

> **Research query (paraphrased):** Some SASE memories (for example
> `sase/memory/macros.md`) should probably move into Markdown docs under `docs/`.
> Project documentation might become a first-class kind of memory, managed in a similar
> way. Docs should also be structured so agents can maintain them more intuitively and
> more mechanically. Research the best way to do this, critique the plan, adjust the
> requirements where justified, and recommend a solution.

---

## Bottom line

**The direction is right, but two of the three ideas need changing before you build
them.** Recommended principle: **read docs like memory, write docs like code.**

1. **"Migrate some memories to docs": yes, but only for descriptive content, and only if
   the trigger moves with it.** `macros.md` is a good first candidate. It is a 3.7k-token
   hand-written digest of `docs/macros.md` (about 61k tokens), and the two have already
   drifted apart: [both are wrong about macro discovery order, in different ways](#f2-hand-maintained-digests-drift-and-the-two-copies-are-wrong-differently).
   What makes memory useful is not where the file lives. It is the **one-line trigger**
   in agent instructions, the **token budget**, and the **audited read**. A plain move to
   `docs/` drops all three. Pointing agents at the full docs section instead costs about
   **7× the tokens** (the Directives section alone is about 26k tokens).
2. **"Make docs a first-class representation of memory, managed in a similar way": half
   right.** Docs should become a first-class **read target** of memory: addressable
   sections, `[[docs:...]]` links, triggers, audited reads, and validation. Docs should
   **not** take on memory's **write governance**. Memory writes need explicit user
   authorization because memory is normative and always paid for. Docs changed in **36%
   of the 1,493 commits that touched `src/` in the last 30 days**, and that co-change
   with code is what keeps them accurate. Gating it would make drift worse. Governance
   should depend on the **kind of content** (rules versus facts), not on the directory.
3. **"Structure docs so agents can maintain them more easily": strongly yes, and it's
   the biggest win available.** Docs maintenance is already mostly done by agents (625
   commits touched `docs/` in 30 days), but it has no structure to work from:
   - Only 2 of 55 pages have frontmatter.
   - There is no map from code to docs.
   - Two pages, `ace.md` (about 185k tokens) and `configuration.md` (about 167k tokens),
     are each larger than many context windows and took 466 commits between them in 30
     days.
   - The docs gardener's prompt amounts to "refresh the docs". It
     [writes known bugs into the docs as caveats](#f5-the-docs-gardener-is-unscoped-and-writes-defects-into-the-docs)
     instead of routing them to beads.

**Recommendation in one paragraph:** Keep `sase/memory/` as the home for rules,
rationale (decisions), vocabulary (glossary), and private home context. Make `docs/` the
single canonical home for facts about product behavior. Give every doc page a small,
lint-checked frontmatter contract: `description`, `kind`, `covers`, and an optional
`memory:` trigger. Teach `sase memory read` and `[[...]]` links to address
`docs:<page>#<anchor>` sections, with audit records. Generate tables that are really
registries (directives, discovery order, glossary, decisions index) from their sources
of truth. Split the two giant pages along the `covers` boundaries. Rebuild the docs
gardener around a diff → affected-pages map. Pilot with `macros.md` and `dispatch.md`.
Details are in [Recommended solution](#recommended-solution).

---

## 1. What exists today

### Memory (`sase/memory/`)

- **19 flat notes:** 3 core, 13 reference, and 3 memory-web descriptors (`decisions`,
  `glossary`, `task_types`). Flat notes total about 22k tokens. With strands, the tree
  is 4,225 lines.
- **Core** notes are inlined into every instruction bundle. **Reference** notes show up
  as one-line triggers ("Read before…") and are fetched with audited
  `sase memory read`. Strands are addressed as `web:keyword`.
- **Writes are governed.** `/sase_memory_write` allows an edit only when the user asked
  for it, an accepted plan decision covers it, or a bead describes it. Otherwise the
  agent files a `memory` task bead. A finalizer warns (`memory_change_uncovered`) on
  uncovered changes.
- **Links are authored** as `[[target]]` / `![[target]]` and validated by `sase doctor`.
  History is browsable through Memory History. Usage is logged: 2,080 audited reads by
  886 agents across 125 paths.
- **Memory already points into docs, but only as plain text.** There are 7 `docs/…`
  path mentions, for example "Full contract: `docs/remote_dispatch.md`". Nothing
  validates them.

### Docs (`docs/`, MkDocs Material, published at sase.sh)

- **55 top-level pages, 59,507 lines,** about 1.0M tokens. That estimate is bytes/4,
  which overstates the count because Prettier pads tables.
- **The biggest pages:**

  | Page | Lines | Approx. tokens | Commits in last 30 days |
  | --- | ---: | ---: | ---: |
  | `ace.md` | 9,771 | ~185k | 260 |
  | `configuration.md` | 7,768 | ~167k | 206 |
  | `macros.md` | 4,082 | ~61k | 75 (28 as `macros.md` + 47 as `xprompt.md` before the 10-03 rename; 473 all-time) |
  | `llms.md` | 3,582 | — | 65 |
  | `beads.md` | 3,046 | — | 51 |

- **Existing quality gates:**
  - `mkdocs build --strict` (`just docs-check`).
  - Prettier formatting.
  - One generated-block renderer: `tools/render_model_docs` keeps the `docs/llms.md`
    model tables in sync with `models.yml`, and `fmt-docs-check` runs in `just check`.
    **This is the precedent to generalize.**
- **Frontmatter:** only `index.md` and `getting_started.md` have any. Blog posts already
  carry `description:` frontmatter.
- **Gardener:** the builtin `refresh_docs` chop proposes an "update" agent and then a
  "polish" agent once enough commits have landed. Their prompts are unscoped. See
  [F5](#f5-the-docs-gardener-is-unscoped-and-writes-defects-into-the-docs).

### Change and usage numbers (last 30 days unless noted)

| Measure | Value |
| --- | ---: |
| Commits | 1,890 |
| …touching `src/` | 1,493 |
| …touching `src/` **and** `docs/` | 542 (36%) |
| Commits touching `docs/` | 625 |
| …gardener-style (`docs: refresh/verify/correct …`) | 26 |
| Commits touching `sase/memory/` | 77 (63 of them touched the generated README) |
| `sase/memory/macros.md` commits, all-time (following renames) | 27 (7 touched no docs) |
| `docs/macros.md` commits, all-time | 473 |

**Audited memory reads (all-time log):**

- **Rules and procedures dominate:** `lint_and_test.md` 664, `sase_sizes.md` 326,
  `sase_beads.md` 313, `sase_artifacts.md` 221, `tui.md` 217, `tui_perf.md` 211,
  `symvision.md` 210.
- **Descriptive notes are rarely read:** `macros.md` 36, plus 48 under its legacy name
  `xprompts.md`. `dispatch.md` has 4.
- **Strands:** `glossary` 1,203, `decisions` 366.

---

## 2. Findings

### F1. Docs are already the de facto agent reference, and those reads are unaudited

I sampled Claude session transcripts from `sase_<N>` workspaces over the last 7 days:
109 sessions.

- **48 sessions (44%)** ran shell reads (`grep`, `sed`, `cat`, `head`, `rg`, `wc`)
  against `docs/`.
- **33 sessions** ran `sase memory read`.
- **Most-hit pages:** `docs/llms.md` 69 times, `docs/ace.md` 63, `docs/macros.md` 52,
  `docs/notifications.md` 42, `docs/plugins.md` 38.

`docs/macros.md` was grepped or sliced **52 times in one week**. The `macros.md` memory
note has been read **84 times in its whole life**, counting both names.

Caveats:
- Some of those shell reads came from agents editing the docs, not just consulting them.
- Claude is only one of several providers.

Either way, the docs are already part of the agent loop. They just have **no trigger,
no section addressing, and no audit trail**.

### F2. Hand-maintained digests drift, and the two copies are wrong differently

I spot-checked one fact that appears in both places: macro discovery order. I compared
both against the resolver
(`sase.content_layout.resolve_macro_file_sources(project='sase')`, whose docstring calls
its order "the Rust-owned first-wins order").

| Source | Legacy directories it names | Order |
| --- | --- | --- |
| **Resolver (truth)** | `sase/xprompts`, `.xprompts`, `xprompts` (project and home), `~/sase/xprompts/<project>`, `~/.config/sase/xprompts/<project>` | All canonical sources first (project → home → project-specific home), then all legacy sources |
| **`docs/macros.md` table** | `.macros/`, `macros/`, `~/.macros/`, `~/macros/`, `~/.config/sase/macros/{project}/` (**none of these is read**) | Legacy project dirs before canonical home |
| **`sase/memory/macros.md`** | `.xprompts/`, `xprompts/`, `~/.xprompts/`, … (right names, but omits `sase/xprompts`) | Legacy project dirs before canonical home |

- `git log -S` traces the wrong docs names to the bulk rename `fe53ae4fc4` ("rename
  xprompt concept to macro across docs, memory, and skills", 2026-10-03). It rewrote
  `.xprompts/` to `.macros/` in docs but left memory alone.
- Twelve days and many gardener runs later, the docs are still wrong.
- I did not trace ranking end to end through every loader, so treat the "order" column
  as the resolver's view.

What this shows:
1. Two hand-maintained copies of one fact will diverge.
2. Neither copy was generated from the contract that owns the fact.
3. The gardener, which compares prose against behavior, did not catch it.

Registry-shaped facts like this one should be **generated**, not copied.

### F3. What memory adds over docs is the trigger, budget, audit, and governance, not the storage

| Read path | Approx. tokens |
| --- | ---: |
| `sase memory read macros.md` (digest) | ~3.7k |
| `docs/macros.md`, whole page | ~61k |
| `docs/macros.md` Directives section only | ~26k |
| `docs/macros.md` Hold Directive section only | ~1.7k |
| `sase memory read dispatch.md` vs `docs/remote_dispatch.md` | ~0.7k vs ~5.2k |

**Two consequences:**

- Deleting the digest and telling agents to "read the docs" is a 7–16× cost increase per
  triggered read.
- Section-addressed reads (`#hold-directive`) can be *cheaper* than the digest when the
  agent needs one topic.

The digest has a real job (a dense cheat sheet), and so do section reads (deep detail).
The fix is to keep both and make them share one source of truth. Keeping two unrelated
copies is the current problem.

### F4. Docs and memory have opposite write regimes, and both are correct for their content

- **Memory content is mostly normative**: rules, conventions, procedures. It is paid for
  on every turn (core) or every trigger (reference). Gating it behind user authorization
  is right: an agent should not quietly rewrite the rules other agents follow.
- **Docs content is mostly descriptive**: what the product does. It has to change in the
  same commit as the code, and it already does in 36% of `src/` commits.
- Since all commits land straight on master with no review (per the earlier
  harness-engineering research in this repo), the only thing keeping docs accurate is
  that agents co-edit them freely.

**So "manage docs the same way as memory" would break one side or the other:**
- **Docs inherit memory's gating:** docs updates slow down and drift grows.
- **Memory's normative rules move into ungated docs:** any agent can silently rewrite a
  rule.

**Governance has to follow content kind, not location.**

### F5. The docs gardener is unscoped and writes defects into the docs

The `refresh_docs` builtin (`src/sase/scripts/sase_chop_refresh_docs.py`) tells its
update agent to "Refresh the documentation for {project}". It may edit only docs. When
docs and code disagree, it must "document the actual current behavior; never change the
code".

**The result is docs that describe bugs.** Examples:
- `docs/memory.md:257`: "…that help text is stale."
- `docs/cli.md:22`: "Compact help's `memory` blurb still mentions reviewing proposals,
  but that CLI workflow has been removed."
- Both lines trace to the gardener commit "docs: refresh current behavior reference".
- A grep finds 13 lines of this "help text is stale / still mentions" shape.

**The docs also accumulate history:**
- Raw counts across `docs/`: "legacy" 497, "retired" 146, "no longer" 94,
  "deprecated" 51. Some are legitimate, such as migration guides.
- Memory, by contrast, has a written norm against this: "prefer deleting a stale line
  over appending a caveat."

**The gardener has no way to scope its work.** It cannot tell which pages a diff
affects, because nothing maps code to pages.

### F6. Outside practice agrees on a map plus a corpus, progressive disclosure, and mechanical freshness

- **OpenAI, "Harness engineering" (Feb 2026):**
  - Treat `AGENTS.md` as a short table of contents (about 100 lines), not an
    encyclopedia.
  - The repository's structured `docs/` is the system of record.
  - Linters and CI check freshness and cross-links, and recurring agents fight entropy.
  - Our earlier critique scored SASE's map mechanism as excellent and noted that
    "`docs/` has no map".
- **Anthropic, context engineering and Agent Skills:**
  - Keep lightweight identifiers in context and load content just in time.
  - Skills use three levels: name and description always loaded, body loaded on trigger,
    bundled resources loaded on demand.
  - The description is what drives selection. That is exactly what SASE's reference
    triggers already do.
- **Claude Code memory docs:**
  - Path-scoped rules (`.claude/rules/*.md` with `paths:` globs) load only when a
    matching file is read or edited.
  - `@imports` load at launch and "don't reduce its context cost."
  - Keep each `CLAUDE.md` "under 200 lines."
  - **GitHub Copilot** has the same idea: `*.instructions.md` files with `applyTo` globs.
  - Both are "covers"-style triggers keyed on the code being touched.
- **Gloaguen et al., "Evaluating AGENTS.md" (ETH Zurich / LogicStar, arXiv 2602.11988,
  ICLR 2026):**
  - Context files "do not generally improve task success rates" and increase inference
    cost "by over 20%".
  - "Repository overviews… are not helpful", but agents do follow the instructions.
  - **Implication:** do *not* answer "docs as memory" by inlining a docs map or doc
    content into always-loaded context. Keep triggers few and specific.
- **Diátaxis (Procida):**
  - Four doc kinds: tutorial, how-to, reference, explanation.
  - Mixing them is the most common structural failure.
  - A memory cheat sheet is a legitimate *reference* artifact, useful to humans too.
- **Swimm (code-coupled docs) and Doc Detective (docs as tests):**
  - Docs declare which code they depend on.
  - CI flags a doc when that code changes, and runs the procedures the doc describes.
- **Martraire, *Living Documentation*:** generate docs from authoritative artifacts
  wherever possible, and curate the rest.
- **llms.txt (Howard):**
  - An H1, a summary blockquote, and H2 sections of annotated links, plus `.md` mirrors
    of pages.
  - A one-line description per page feeds it directly.
  - `mkdocs-llmstxt` is now in maintenance mode, so a small custom generator is the
    safer route.

---

## 3. Critique of the plan

### Idea 1: "Migrate some memories to docs"

**Mostly good, but phrased the wrong way round.**

- **The real problem is duplication.** Descriptive facts live in two hand-maintained
  copies (F2). "Moving" content fixes that only if the memory side keeps its trigger and
  points into the docs.
- **Without a section-addressable target, migration makes agents pay more** (F3) and
  read less precisely.
- **Most of today's reference memory is not a migration candidate.** The heavily read
  notes are rules and procedures (`lint_and_test`, `symvision`, `sase_flags`,
  `cli_rules`, `tui_perf`). The descriptive digests are the rarely read ones (`macros`,
  `dispatch`). So the migration is small and targeted, not a re-homing of memory.

### Idea 2: "Make docs a first-class representation of memory, managed similarly"

**Good for reads, harmful for writes.**

- **Share these:**
  - descriptions and triggers;
  - audited, section-addressed reads;
  - authored links and their validation;
  - history browsing;
  - token accounting;
  - visibility in `sase memory list` and the Memory panel.
- **Do not share:**
  - **write authorization** (F4);
  - **always-loaded budget:** docs cost nothing until read, so only their trigger lines
    count against the budget;
  - **audience:** docs are public, and home memory (`tailnet`, `obsidian`) must never be
    published.
- **Do not make docs a new memory *kind* with webs, strands, or closure.** That is
  mechanism without a corpus that needs it. The `corpus-before-mechanism` decision
  records three times this went wrong and had to be ripped out at real cost.
- **The corpus does justify a *small* mechanism:**
  - memory already cites docs as plain text;
  - two digests already duplicate docs;
  - agents already read docs, unaudited, every day (F1).

### Idea 3: "Structure docs so maintenance is intuitive and scriptable"

**The strongest of the three. Its success depends on making the structure
machine-checkable, not just tidier.**

- **"Scriptable" needs metadata a script can join:**
  - which code a page covers;
  - what kind of page it is;
  - a one-line description;
  - which blocks are generated.
- **Pages need to be small enough for an agent to own.** No agent can reason across a
  185k-token page.
- **The gardener needs a channel for defects** other than the docs themselves (F5).

### Overall verdict

**It's a good idea, and I would go about it differently.**

- **Your framing:** "move memory into docs and manage docs like memory."
- **Mine:** "memory is the index and the rulebook; docs are the corpus." Memory gains a
  first-class pointer into docs. Docs gain a contract that makes them maintainable by
  machine. Governance depends on content kind.

---

## 4. Requirement adjustments (explicit)

These change your stated requirements. Each one is justified above.

| # | Your requirement (as I read it) | Adjusted requirement | Why |
| --- | --- | --- | --- |
| **R1** | Migrate memories such as `macros.md` into `docs/`. | Make `docs/` the **single canonical home for descriptive facts**. Memory keeps **rules, rationale, vocabulary, and private context**. Migrate one note at a time by content kind. A migrated entry keeps its **trigger** and resolves into docs. | F2, F3, F4. Most heavily read memory is normative and should stay. |
| **R2** | Manage docs similarly to memory. | **Read docs like memory, write docs like code.** Share addressing, audit, links, validation, and visibility. Apply memory write governance only to (a) the always-loaded `memory:` trigger block on a doc page, and (b) pages declared `kind: policy`. | F4. 36% of `src/` commits co-edit docs, and gating them would increase drift. |
| **R3** | Structure docs better. | The structure must be a **lint-checked contract**: page frontmatter (`description`, `kind`, `covers`, optional `memory`), generated blocks for registry-shaped facts, a page-size budget, and validated anchors. | "Scriptable" needs joinable metadata (F5, F6). Taste-based reorganizations decay. |
| **R4** | *(new)* | **Project in both directions.** Memory webs that humans also need (`glossary`, the `decisions` index) render into **generated, read-only docs pages**. Their source stays in memory. | One source of truth, two audiences. The glossary has no docs page today. |
| **R5** | *(new)* | **The gardener must not encode defects in docs.** A disagreement between code and docs becomes a `bug` task bead (or a tracked admonition that a lint counts), never a "this is stale" sentence. | F5. |
| **R6** | *(new)* | **Measure before generalizing.** Pilot on `macros.md` and `dispatch.md` with explicit exit criteria and a reopen condition (see [§7](#metrics-and-reopen-conditions)). | `corpus-before-mechanism`; the ETH result on context cost. |
| **R7** | *(new, optional)* | **Make the read-target feature work for any SASE-managed project.** Add `memory.docs_roots` in `sase.yml`, defaulting to empty, with `sase` setting `["docs"]`. Selector resolution goes in **sase-core**. | The CLI, TUI Memory panel, and editor LSP must resolve `docs:` selectors identically, which is the rust-core boundary rule. |

---

## 5. Options considered

| Option | Description | Verdict |
| --- | --- | --- |
| **A. Status quo plus a drift lint** | Keep both copies and add a checker that compares memory claims against docs. | Treats the symptom. Claim comparison is fuzzy, and F2 shows *both* copies can be wrong. Reject as the end state; its lint ideas are absorbed into D. |
| **B. Wholesale move** | Delete descriptive notes and point agents at docs pages. | Loses triggers, raises read cost 7–16×, and puts rules into ungoverned docs. **Reject.** |
| **C. Docs as a full memory kind** | Doc pages become notes or webs with memory governance, closure, and so on. | Throttles docs co-change and is mechanism without a corpus. **Reject.** |
| **D. Docs as read targets plus a docs contract** | Memory keeps the index and the rules. Docs get frontmatter, `docs:` selectors and links, generated blocks, `covers`-driven gardening, and governance by kind. | **Recommended.** |
| **E. LLM-generated digests** | `sase memory init` summarizes doc sections into memory. | Non-deterministic, costly, and unreviewable at init time. Reject as a build step. Keep a narrower version: **provenance hashes** flag stale digests, and the gardener *proposes* a refresh. |

---

## 6. Disposition of today's memory notes

"Descriptive" means it states facts about behavior. "Normative" means it tells
agents or contributors what to do.

| Note | Reads | Content | Disposition |
| --- | ---: | --- | --- |
| `sase.md`, `gotchas.md`, `rust_core_backend_boundary.md` (core) | n/a | Runtime contract and hard rules | **Stay core.** Possible later step: turn `gotchas` (keymap ↔ `default_config.yml`) into a check. |
| `decisions` web | 366 | Rationale | **Stay memory.** Add a **generated** docs index page (title, claim, status) for humans. |
| `glossary` web | 1,203 | Vocabulary | **Stay memory** (keyword addressing, implicit closure). Add a **generated** `docs/glossary.md`. |
| `task_types` web, `sase_artifacts`, `sase_beads`, `sase_sizes` | 31–326 | Generated product guidance | **Stay generated memory.** |
| `lint_and_test.md` | 664 | Procedure (normative) | **Stay.** Move its descriptive "reading `sase tool run` triage" detail into `docs/tool.md` and link `[[docs:tool#…]]`. |
| `symvision.md`, `sase_flags.md`, `cli_rules.md`, `generated_skills.md`, `tui_perf.md` | 43–211 | Conventions and procedures | **Stay for now.** These are contributor policy. Revisit as `kind: policy` docs pages only after Phase 2 proves governance by kind. |
| `tui_screenshot.md` | 95 | Mixed: tool usage plus procedure | **Split.** Usage facts go to `docs/development.md#visual-snapshot-workflow`; the procedure stays in memory. Verify the overlap first. |
| **`macros.md`** | 84 | **Descriptive digest** of `docs/macros.md` | **Pilot migration.** Becomes the published page `docs/macros_quick_reference.md` with a `memory:` trigger and the alias `macros.md`. The one normative line ("agents never commit…") already lives in core `sase.md` and `decisions:host-owned-completion`, so drop it here. |
| **`dispatch.md`** | 4 | **Descriptive digest** of `docs/remote_dispatch.md` | **Pilot migration.** Becomes a "Quick reference" section of `docs/remote_dispatch.md`, addressed as `docs:remote_dispatch#quick-reference`. |
| `tailnet.md`, `obsidian.md` (home) | 12–36 | Private | **Never publish.** Stay home memory. |

---

## Recommended solution

### Principle and decision record

**Docs are read like memory and written like code.** Write this as a new decision
record before building anything. Suggested content:

- **Claim:** `docs/` is the canonical home of descriptive facts. Memory holds rules,
  rationale, vocabulary, private context, and *triggers*. A doc page or section can be
  the target of a reference trigger, a `[[docs:…]]` link, or an audited
  `sase memory read docs:…`. Write governance follows content kind: the `memory:`
  trigger block and `kind: policy` pages are memory-governed, and everything else is
  docs-as-code.
- **Why:**
  - Two hand-maintained copies drift (F2).
  - Agents already read docs, unaudited (F1).
  - Digests are worth keeping but need a single source (F3).
  - Docs must co-change with code (F4).
- **Rejected:** options B, C, and E (§5).
- **Cost:**
  - one selector and link kind in sase-core;
  - a frontmatter lint;
  - two giant pages to split, with redirects;
  - anchor stability now matters.
- **Reopens when:** docs-backed triggers measurably raise tokens per triggered read or
  lower read rates compared with the note baseline, *or* governance by kind produces
  uncovered rule changes. In that case, return the pilot notes to memory.

### Component 1: the docs page contract (frontmatter)

```yaml
---
description: >-
  One-page cheat sheet of macro invocation grammar, % directives, and launch VCS refs.
kind: reference            # tutorial | how-to | reference | explanation | runbook | policy
covers:                    # repo globs whose behavior this page documents
  - src/sase/macro/**
  - src/sase/agent/multi_prompt*.py
memory:                    # optional; governed by /sase_memory_write
  trigger: >-
    Read before writing macros, prompt directives, or launching agents with git/gh VCS
    workflow blocks.
  aliases: [macros.md]     # keeps #memory/macros and [[macros.md]] working
derived_from:              # optional; for digests of other pages
  - docs/macros.md#directives
---
```

**One `description` serves four consumers:**
1. Material's `<meta name="description">`;
2. `llms.txt`;
3. `sase docs list` and the gardener's routing;
4. the fallback trigger text.

**Lint**, as a fast Python tool next to `render_model_docs`, run in `just check`:
- `description` and `kind` are required.
- Every `covers` glob must match at least one path.
- A `memory.trigger` must be one paragraph.
- Pages over a size budget get a warning. Suggested budget: about 30k tokens. `ace.md`
  and `configuration.md` fail it today.

**MkDocs config:** turn on anchor validation (`validation: anchors: warn`, together
with `--strict`) so that broken `#anchor` links fail the build.

### Component 2: docs as memory read targets (the "first-class" piece)

- **Selector:** `sase memory read docs:<page>[#<anchor>] -r "<why>"` prints the page or
  section with frontmatter stripped.
  - Sections are cut by heading slug, using the same slugify as MkDocs' `toc`.
  - The read records an audit event with the doc's blob OID, like a note read.
  - It batches with notes and strands in a single call.
  - `show` gives the same output without an audit record.
- **Links:** `[[docs:<page>#<anchor>]]` works in notes, strands, and doc pages that opt
  in. `sase doctor` validates both page and anchor. The 7 existing plain-text `docs/…`
  mentions become links.
- **Triggers:** pages that declare `memory.trigger` are listed in the generated
  `## Reference Memory` section beside the notes, one line each. Triggers are opt-in
  only, and there is **no docs map in always-loaded context** (ETH result; Claude Code's
  under-200-lines guidance).
- **Governance:**
  - `/sase_memory_write` and the `memory_change_uncovered` finalizer guard treat a diff
    to a page's `memory:` block, or to a `kind: policy` page, as a memory change.
  - Body edits on other pages are ordinary docs edits.
  - Update the skill text to state the content-kind rule.
- **Surfaces:** the Memory panel lists docs-backed entries read-only (`o` opens
  `$EDITOR`). `sase memory list` counts their trigger-line tokens. `sase memory log`
  credits section reads.
- **Placement:** selector resolution and frontmatter parsing belong in **sase-core**
  next to the existing web selector and read-log code, because the CLI, TUI, and LSP
  must agree. The lint and renderers can stay Python tools.

### Component 3: generate registry-shaped facts

Generalize `tools/render_model_docs` into a generated-block framework: a marker,
`render`, and `--check` in `just check`. First blocks:

1. **Directive table rows** (name, aliases, accepted forms, keywords) from the Rust
   directive contract that the TUI and LSP already share. The *Effect* column stays
   hand-written, and a coverage check fails if a contract directive is missing from it.
   This applies to both `docs/macros.md` and the quick reference.
2. **Macro discovery order** from the content-layout contract. This fixes F2 for good.
3. **Glossary page** from the `glossary` web, and a **decisions index** from the
   `decisions` web, both read-only and marked "generated from memory".
4. Later: CLI flag tables from argparse and configuration keys from
   `sase.schema.json`. That covers much of `configuration.md`'s 167k tokens.

### Component 4: page structure for agent ownership

- **Split the two giant pages:**
  - `ace.md` becomes `docs/ace/` (one page per tab or panel).
  - `configuration.md` becomes `docs/configuration/` (one page per top-level key family).
  - Each new page gets tight `covers` globs.
  - `mkdocs-redirects` is already installed, so the old URLs keep working.
  - This also reduces edit collisions across concurrent workspaces. Those two pages took
    466 commits in 30 days.
- **Keep Diátaxis kinds separate:**
  - Quick references are `reference`.
  - Runbooks (`perf_runbook`, `mobile_mvp_runbook`, `troubleshooting/*`) are `runbook`.
  - Migration and history narrative goes to explicitly `explanation`/migration pages or
    to `CHANGELOG.md`.
- **History-language lint (warning only):** flag "no longer / formerly / renamed from /
  still mentions / is stale" outside migration pages, so the gardener can clean up.

### Component 5: a scriptable docs gardener

- **`sase docs affected [--since <rev>] [-f json]`** joins a diff against `covers` and
  lists the affected pages and sections. Suggested placement for this core-side join:
  sase-core or a thin Python adapter.
- **Rewrite `refresh_docs`** to emit **one proposal per affected page cluster**, each
  with:
  - the page path(s);
  - the diff hunks that touched its `covers`;
  - an instruction to edit only those pages and re-run the generated blocks;
  - an instruction to **file a `bug` task bead** for any disagreement between code and
    docs instead of writing a caveat.

  The polish agent then verifies just that cluster.
- **Digest provenance:** `derived_from` records the source section's content hash when
  the digest was last refreshed. `sase doctor` warns when the source has changed since
  then, and the gardener proposes the refresh. This is Swimm-style verification applied
  to cheat sheets.
- **Advisory co-change note:** when a commit touches covered code but not the covering
  page, the final declaration or `just check` output prints a one-line notice. It is
  **never blocking**, in the same spirit as triage that annotates rather than changing
  exit codes.

### Component 6 (optional): publish for outside agents

Generate `/llms.txt` from `description` and the nav, and publish `.md` mirrors of the
pages. This helps agents in *other* repos that use SASE learn it from sase.sh. It is
low cost once Component 1 exists.

### Phased plan

| Phase | Scope | Exit criteria |
| --- | --- | --- |
| **0. Hygiene** (days, no new mechanism) | Fix the discovery-order drift. Change the `refresh_docs` prompts to route defects to beads, and sweep the 13 stale-caveat lines into beads. Write the content-kind rule into `docs/development.md` "Documentation Workflow" and the `/sase_memory_write` skill. Turn on MkDocs anchor validation. | Zero "help text is stale"-style lines. Strict build passes with anchors checked. |
| **1. Docs contract** (small epic) | Frontmatter schema and lint. Add `description` and `kind` to all 55 pages (gardener-assisted). Generated-block framework with blocks 1–3 from Component 3. | Lint is green in `just check`. Discovery table and directive rows are generated. Glossary and decisions pages are published. |
| **2. Read targets plus pilot** (small epic, sase-core plus Python) | `docs:` selectors, links, triggers, governance hook, Memory panel and log support. Migrate `macros.md` to `docs/macros_quick_reference.md` (with alias) and `dispatch.md` to its quick-reference section. | Tokens per triggered read ≤ the note baseline (3.7k / 0.7k). Pilot entries show audited reads. Zero unresolved `docs:` links. `#memory/macros` and `[[macros.md]]` still resolve. |
| **3. Structure plus gardener** (epic) | Split `ace.md` and `configuration.md`. `covers` everywhere. `sase docs affected`. Scoped `refresh_docs`. `derived_from` provenance. Advisory co-change note. | No page over budget. Gardener proposals are scoped per cluster. The share of docs commits that are gardener catch-up goes down. |
| **4. Optional** | `llms.txt`/`.md` mirrors; `memory.docs_roots` for other managed projects; consider `kind: policy` homes for contributor conventions. | Driven by demand. |

### Metrics and reopen conditions

- **Read cost:** tokens per triggered read for the pilot entries against their note
  baselines. Section reads should be cheaper.
- **Discoverability:** audited reads of docs-backed entries compared with the old note
  read rate. Shell `grep`/`sed` access to `docs/` from transcripts should shift toward
  audited reads.
- **Freshness:** the count of digest-staleness warnings and how long they stay open. The
  count of hand-maintained registry tables, which should approach zero.
- **Gardener quality:** stale-caveat lines (target 0), `bug` beads filed by the
  gardener, and scoped proposals per run.
- **Reopen** if the pilot raises read cost or lowers read rates, or if governance by
  kind lets an unauthorized rule change through. In that case, return the pilot notes to
  memory and keep only Components 1, 3, and 5, which are worthwhile on their own.

### What not to do

- Don't move rules or procedures (`lint_and_test`, `sase_flags`, `cli_rules`, …) into
  ungoverned docs.
- Don't inline a docs map, or any doc content, into always-loaded instructions.
- Don't build doc embeddings, keyword auto-injection, or doc "webs". That is the
  retrieval-before-corpus pattern the decisions record as failing three times.
- Don't put all docs writes behind memory authorization.
- Don't generate digests with an LLM at `sase memory init` time.

---

## Method

- **Memory:** read `sase/memory/README.md` and `docs/memory.md`. Audited reads of
  `macros.md`, `cli_rules.md`, `dispatch.md`, `generated_skills.md`, `tui.md`,
  `sase_flags.md`, `lint_and_test.md`, `symvision.md`, and `tui_perf.md`, plus the
  decisions `corpus-before-mechanism`, `memory-webs`, `memory-links-are-authored`, and
  `instructions-per-invocation`. Read the source of the `sase_memory_write` skill.
- **Usage:** read counts from `sase memory log --json`. Change statistics from `git log`
  (last 30 days, plus `--follow` and `-S` traces).
- **Gardener and drift:** read `src/sase/scripts/sase_chop_refresh_docs.py` and
  `docs/axe.md`. Called the macro-source resolver directly from the repo venv.
- **Docs access:** grep counts over local Claude transcripts for `sase_<N>` workspaces
  (`~/.claude/projects`, files changed in the last 7 days).
- **Sizes:** token sizes are bytes/4 estimates.
- **Prior research (unrelated earlier swarms in this repo):**
  `202610/openai_harness_engineering_vs_sase/openai_harness_engineering_vs_sase.md` and
  `202610/instruction_bundles_vs_readable_agents_md/instruction_bundles_vs_readable_agents_md.md`,
  read through `sase artifact read`.

## Sources

- OpenAI, *Harness engineering: leveraging Codex in an agent-first world* (Feb 2026):
  <https://openai.com/index/harness-engineering/>. openai.com blocks direct fetches, so I
  relied on the earlier in-repo critique's reading and on secondary summaries, e.g.
  <https://concepts.dsebastien.net/concept/harness-engineering/> and
  <https://opensource.adobe.com/ai-repo-harness-guide/READING/>.
- Anthropic, *Effective context engineering for AI agents*:
  <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>.
  Summarized via secondary sources, e.g.
  <https://agentic-ai.readthedocs.io/en/latest/ContextEngineering/anthropic/>.
- Anthropic, *Equipping agents for the real world with Agent Skills*:
  <https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills>
- Claude Code memory documentation (path-scoped rules, `@imports`, size guidance):
  <https://code.claude.com/docs/en/memory>
- GitHub Copilot path-specific custom instructions (`applyTo`):
  <https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions>
  and
  <https://github.blog/changelog/2025-09-03-copilot-code-review-path-scoped-custom-instruction-file-support>
- Gloaguen, Mündler, Müller, Raychev, Vechev, *Evaluating AGENTS.md: Are
  Repository-Level Context Files Helpful for Coding Agents?* (arXiv 2602.11988, ICLR
  2026): <https://arxiv.org/abs/2602.11988>. Commentary:
  <https://developer.upsun.com/posts/ai/agents-md-less-is-more>,
  <https://codex.danielvaughan.com/2026/04/13/what-eth-zurich-paper-gets-wrong-right-about-agents-md/>
- Diátaxis: <https://diataxis.fr/>. Canonical's adoption:
  <https://ubuntu.com/blog/diataxis-a-new-foundation-for-canonical-documentation>
- llms.txt proposal: <https://llmstxt.org/>. `mkdocs-llmstxt`:
  <https://github.com/pawamoy/mkdocs-llmstxt>
- Swimm, code-coupled documentation:
  <https://docs.swimm.io/new-to-swimm/benefits-of-code-coupled-documentation>
- Doc Detective / docs as tests (FOSDEM 2025):
  <https://fosdem.org/schedule/event/fosdem-2025-4928-no-more-broken-docs-keep-docs-accurate-with-doc-detective>
- Cyrille Martraire, *Living Documentation* (Addison-Wesley, 2019):
  <https://eu.pearson.com/living-documentation-continuous-knowledge-sharing-by-design/9780134689364>
