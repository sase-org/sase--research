# Simplifying sase.sh: A Two-Tier, Diátaxis-Shaped Docs Site That Stops Re-Growing

> **Research question:** Drastically simplify SASE's documentation on sase.sh so it is
> simpler and more intuitive, and add more structure to the documentation process. Use
> [Diátaxis](https://diataxis.fr) as inspiration. Consider long-term agentic maintenance,
> but focus on the best documentation solution and structure, and on the sase.sh site's
> UX for people trying to learn about SASE. Critique the plan, adjust requirements where
> justified, and end with a recommendation.

Researcher: `cld`. Date: 2026-10-15. Measured against sase `bc4bc3e183` and the live
`https://sase.sh/`. I also read two earlier, unrelated research reports as background:
`202605/sase_sh_site_design_research.md` and
`202610/docs_backed_memory_and_agent_maintained_docs/…__final.md`. Where this report
agrees or disagrees with them, it says so.

---

## Bottom line

**Yes, do it. But the problem isn't that the docs are badly organized. They are a
behavior spec, written by feature agents, that gets published as a user manual. They are
also growing at about 37% a month.** No reorganization lasts unless it separates those two
things and puts a ceiling on growth.

- **Size.** The docs are **518K words across 57 pages**. That is roughly 36 hours of
  reading and a **1,151-page PDF**.
- **Growth.** Four months ago they were 119K words. `ace.md` alone went from 24K words
  to 103K words in three months. Even the 15-minute tutorial nearly tripled, from 1.5K to
  4.1K words.
- **Comparison.** uv, a mature tool with a famously clear MkDocs site, has **72K
  hand-written words across 81 pages**. It generates its CLI, settings, and
  environment-variable references from code.

**Recommended solution (details in §6):**

1. **Split the site into two tiers that users can see.**
   - **The Guide** is small, curated, and human-reviewed: *Get started*, *Guides*, and
     *Concepts*. It has hard word budgets and a target of about 60K words in total.
   - **The Reference** holds everything else: the CLI, configuration, TUI, file formats,
     and *Contributing & internals*. Most of it should be **generated**; the rest is
     split into small pages.
   - Agents keep everything they rely on today. New users only see the Guide.
2. **Rebuild the front door from the top down, and decompose the reference from the
   bottom up.** Diátaxis warns against big top-down reorganizations, and for a
   516K-word reference that warning is right. The front door is different: it barely
   exists. The tutorials are tangled, there are almost no concept pages, and the 25-card
   homepage teaches nothing. Write it fresh, as new files, so it doesn't collide with the
   ~20 docs commits a day landing on `master`.
3. **Use five top-level tabs:** Get started · Guides · Concepts · Reference · Blog.
   This replaces a 60-plus-item sidebar of internal nouns ("Mentors", "Beads",
   "Artifacts Pane Contract", "SDD Storage"). Each page lives in exactly one tab, and the
   directory decides its type.
4. **Give the docs process a small contract that lint enforces:** per-type templates,
   per-type word budgets with a ratchet, nav and anchor validation, generated registry
   pages, present-tense-only text in the Guide (history goes to the CHANGELOG), and a
   "where does my change go?" routing table for feature agents.
5. **Make tutorials executable.** Diátaxis requires tutorials to be perfectly reliable.
   On a product with about 450 feature commits a month, only a tested tutorial stays
   reliable. Run them against the bundled deterministic `fakey` provider, and regenerate
   screenshots from the existing VHS and demo-seeding tooling.
6. **Platform: stay on MkDocs Material for the restructure, but keep it portable to
   Zensical.** Material is in maintenance mode, with critical fixes through May 5, 2027.
   Its successor, Zensical, is still alpha and reads `mkdocs.yml`, but has no PDF export.
   **Retire the 1,151-page PDF handbook** (adjustment R4), and migrate to Zensical after
   its 0.1.0 release.

---

## 1. What sase.sh is today (measured)

### 1.1 Size, concentration, growth

| Metric | Value |
| --- | --- |
| Docs pages (excluding blog and image briefs) | 57 |
| Words | **518,106**. At about 238 wpm, that is roughly 36 hours of reading |
| Two largest pages | `ace.md` 103K words (about 7.2 hours), `configuration.md` 71K. **Together they are 34% of the corpus** |
| Top 5 pages | 50% of all words (`ace`, `configuration`, `macros`, `beads`, `llms`) |
| Published PDF handbook | **1,151 pages, 14.6 MB** |
| Live `/ace/` page | 259 KB compressed |
| Live search index | 1.28 MB compressed, downloaded by anyone who searches |
| `llms.txt` | none (404) |

**Growth** (`docs/*.md` words at each date):

| Date | Words | Pages |
| --- | --- | --- |
| 2026-06-15 | 119K | 34 |
| 2026-07-15 | 151K | 38 |
| 2026-08-15 | 286K | 43 |
| 2026-09-15 | 378K | 49 |
| 2026-10-15 | **518K** | 57 |

- In the last 30 days, 617 commits touched `docs/`. 450 of them are `feat:` commits and
  only 68 are `docs:`.
- `ace.md` got 259 commits and `configuration.md` got 202. That's about 15 commits a day
  on two files.
- **Docs are being written as a side effect of feature work.** Each feature agent
  appends a precise description of its behavior to the page nearest its code.

### 1.2 Comparison point: uv

I opened `astral-sh/uv` as an external repo and measured its docs.

| | uv | sase |
| --- | --- | --- |
| Hand-written docs words | 72K | 518K |
| Pages | 81 | 57 |
| Top-level nav | Introduction · Getting started · Guides · Concepts · Reference | Home · Getting Started · The Basics · Beyond the Basics · The Nitty Gritty · Integrations · Reference · Blog |
| Getting started | 5 pages, 2K words | 6 pages, mixed. Includes "Content Layout Migration" and a historical "Instruction Inventory" |
| CLI / settings / env reference | **Generated** at build time (`crates/uv-dev/src/generate_cli_reference.rs`, gitignored output) | Hand-written prose tables (`cli.md` is 14.6K words, `configuration.md` is 71K) |
| Internals and contributing | Nested at the end of Reference | Mixed into "The Basics" (`artifacts_pane_contract.md`, `artifacts_pane_visual_grammar.md`, `sdd_storage.md`) |
| `validation:` block in `mkdocs.yml` | Yes (`omitted_files`, `absolute_links`, `unrecognized_links`) | No. As a result, `agent_auto_restart.md` is unlisted but still linked from the homepage |

uv is roughly what sase's Guide tier could look like. Its five-tab shape is also the
closest real-world precedent for this exact stack (Python CLI, MkDocs Material,
Diátaxis-ish). Other sites I checked follow the same pattern: Django ("Tutorials / Topic
guides / Reference guides / How-to guides"), Claude Code ("Getting started … Reference"
plus a literal "Quickstart"), and Tailscale ("Get Started / Manage / Expand / Resources
and reference"). None of them puts more than about 8 items at the top level, and none
mixes contributor internals into the learning path.

### 1.3 Site UX findings

1. **The sidebar is a wall.** The live sidebar renders about 60 always-expanded links
   (`navigation.sections` without `navigation.tabs`), plus the current page's TOC. It
   is the same on every page, including the homepage.
2. **The nav is a list of internal nouns.** Labels like "Mentors", "Beads", "Monitors",
   "Named Tools", "Agent Hood Synchronization", "SDD Storage", and "Artifacts Visual
   Grammar" mean nothing to a newcomer. Diátaxis is explicit about this: how-to guides
   are "about goals, projects and problems, not about tools", and grouping by product
   feature "is rarely successful".
3. **The difficulty-ladder grouping mixes audiences and types.** "The Basics" contains
   the 103K-word TUI spec and two internal design contracts. "Getting Started" contains
   a migration note and a historical inventory. "The Nitty Gritty" holds both user
   how-tos (sudo, notifications) and private runbooks (Mobile MVP, performance).
4. **The homepage offers about 25 choices and teaches nothing.**
   - The cards come in three groups: 8 role cards, 8 primitives, and 9 "next clicks".
   - There is no install command and no demo media. The README has three demo GIFs and
     videos, and they are much better.
   - The lede leads with "a Python CLI and TUI backed by a required Rust core", which is
     an implementation detail.
   - Several cards use jargon, for example the memory card's "flat-note metadata…
     memory-web strands".
5. **The tutorial is overloaded.**
   - "Your First 15 Minutes" is 4,145 words in 8 steps and introduces workspace (33
     mentions), bead (31), plan (25), epic (21), Patch (18), macro (15), SDD, stitch,
     and artifact references.
   - Diátaxis' tutorial rules include "Ignore options and alternatives" and "A tutorial
     is not the place for explanation". Step 3 alone explains why Muse and Grok aren't
     auto-detected and how size aliases route.
6. **History and internals leak into user text.** I found:
   - 741 history phrases ("formerly", "renamed from", "legacy", "no longer", "still
     mentions", "retired", "cutover"), 134 of them in `configuration.md`;
   - 148 bead-ID mentions;
   - 382 `src/sase/...` paths;
   - epic labels in headings (for example `tool.md`'s "Verdict receipts … (E4
     receipt-execution-cli)");
   - stale caveats such as `cli.md:22`, "Compact help's `memory` blurb still mentions
     reviewing proposals…".
7. **Big pages make search and reading worse.** Search hits land somewhere inside a
   1 MB page. The homepage's 10 KB is followed by a 1.28 MB search index on first search.

### 1.4 Process findings

- **Rules for where docs content goes:** none, beyond "run `just docs-check`". The
  Development → Documentation Workflow section only covers build commands.
- **Tests that pin documentation prose:** about 31 test files read real `docs/*.md`
  content. `docs/macros.md` alone is pinned 25 times, mostly by terminology tests. A
  restructure has to move these pins to generated blocks or to the new paths.
- **Generated content:** only the model-tier tables in `llms.md`
  (`tools/render_model_docs`, checked by `fmt-docs-check`).
- **Gate gap** (from the earlier docs-memory report): `mkdocs build --strict` only runs
  on PR CI and the post-push deploy. With zero PRs, a broken docs build is first seen
  after it lands.
- **Audience reality:**
  - `sase-org/sase` has 5 stars, and GitHub shows 10 unique visitors in the last 14 days.
  - The launch post went out 2026-07-08, and 10 of 11 blog posts are still drafts.
  - Today the docs' main readers are Bryan and agents. The earlier report found that 38%
    of recent Codex sessions in sase workspaces shell-read a docs page.
  - **This is the cheapest moment the project will ever have for restructuring**, since
    there are almost no inbound links to break. It is also the moment to make the site
    ready for the readers the launch is meant to attract.

### 1.5 Platform findings

| Item | Status (verified 2026-10-15) |
| --- | --- |
| Material for MkDocs | 9.7.0 (Nov 2025) was "the final version" for features. Critical bug and security fixes were **extended to May 5, 2027** (pinned issue #8523, retitled 2026-09-15). "Minor issues may not receive a fix." |
| MkDocs 2.0 | Pre-release. "Won't have a plugin system"; "incompatible with Material"; "no migration path". Material caps `mkdocs<2`. |
| Zensical (successor) | 0.0.70 (2026-10-12), **Alpha**. 0.1.0 planned for 2026-11-05. Reads `mkdocs.yml`. Natively supports `blog`, `rss`, `redirects`, and search. Has built-in `llmstxt` plus a "Copy as Markdown" action. **No PDF export.** Unlisted plugins are "silently ignored". Templates use MiniJinja. |
| sase's plugin stack | `search`, `blog`, `rss`, `redirects`, plus `mkdocs-exporter` (PDF build only). Everything except the PDF has a Zensical path. |

---

## 2. Diagnosis

**The corpus is a behavior spec published as a user manual.** Here is a typical passage
from `ace.md` §Agents Tab Main Deck:

> "`Ctrl+J` and `Ctrl+K` move to the next / previous card in the focused deck panel
> (wrapping). In a paged Main deck this swaps the visible card; in a spread Main deck it
> scrolls the next / previous card's header to the top…"

That is a precise, valuable **reference** sentence for an agent changing the deck, or
for a power user. It does nothing for someone deciding whether SASE is for them. Today
both kinds of text sit on the same page, under a nav labeled "The Basics".

The three root causes, in order of how much they matter:

1. **Nothing types the docs.** No rule says what a page is for (Diátaxis type) or who it
   is for (user vs. contributor), so every page drifts toward exhaustive reference. That
   is the easiest kind of text for a feature agent to write.
2. **Accretion is the default path.** Feature agents document by appending, so the
   corpus grows with the code, at +37% a month. Even a perfect restructure would be
   buried within one or two months unless budgets and routing change what agents do.
3. **Registries are written as prose.** The CLI, config keys, keymaps, directives, model
   tables, and glossary are written by hand. Each feature adds a row by hand, and the
   rows drift (see the stale `memory` help caveat and the macro discovery-order drift
   found in the earlier report).

Navigation and the homepage are symptoms. Fix them in the same effort, but they are not
the cure.

---

## 3. Critique of the plan

### 3.1 Is this a good idea?

**Yes. It's overdue, and the timing is good:** almost no inbound links, the launch is
recent, and Material's end-of-support forces a platform decision anyway. Three cautions:

1. **"Drastically simplify" must not mean "delete the spec."** Agents use the detail. I
   would add that the TUI and config detail is also what lets *Bryan* trust agent-written
   behavior. Deleting it would trade a UX problem for an agent-accuracy problem.
   Simplify what readers *meet*. Shrink what's hand-written by **generating** registries
   and **removing history**. Keep the rest as reference, out of the learning path.
2. **Restructuring alone decays.** At 617 docs commits a month, a tidy tree drifts back
   into accreted pages within weeks unless (a) budgets are enforced and (b) feature work
   is routed into the reference tier by default. The process half of your request isn't
   optional polish. It's what makes the simplification last.
3. **A big-bang move collides with live agents.** With ~9 commits a day on `ace.md` and
   no PRs, a sweeping rename or reflow conflicts with whatever agents are doing. Build
   the new tier as **new files**. Move old ones **mechanically** (move-only commits plus
   redirects), one page at a time.

### 3.2 Where Diátaxis fits sase, and where it doesn't

**Where it fits:**

- **The four types match sase's gaps exactly.** Tutorials are overloaded, how-tos are
  buried inside reference pages, and explanation is nearly absent: "Why X exists"
  paragraphs are scattered across references. Reference is massively over-supplied.
- **"Reference should mirror the structure of the product"** gives a clean rule for the
  Reference tab: CLI command groups, config key families, TUI tabs, and file formats.
  Those are also the things that can be generated.
- **"How-to guides are about goals … not about tools"** directly fixes the nav-of-nouns
  problem. "Get automated code review" explains itself; "Mentors" doesn't.
- **"Aspire to perfect reliability" (tutorials)** turns into an engineering requirement:
  test the tutorials.
- **The compass** (action/cognition × study/work) is a cheap decision rule that agents
  can apply when placing content.

**Where it falls short:**

- **It types content, not audiences.** sase has at least three audiences: evaluators and
  new users, daily and power users, and contributors (including agents). Diátaxis has no
  "internals" quadrant. uv adds one by nesting *Internals* and *Contributing* under
  Reference, and sase needs the same.
- **It has no stance on generated reference**, beyond warning that generated reference
  "is not all the documentation required". For sase, generation is the main lever on
  size and drift.
- **It's anti-plan.** It says "Use Diátaxis as a guide, not a plan", "don't try to work
  on the big picture", and "the temptation is to tear it all down and start again …
  avoid it". That's sound advice for a *living reference* where most content is already
  serviceable. It fits sase's front door poorly: that content doesn't exist in usable
  form, and Diátaxis' own worst case, creating "empty structures … Don't do that. It's
  horrible", is avoided by launching each section with real pages. So I recommend
  **top-down for the Guide tier and bottom-up (Diátaxis-style) for the Reference tier**.
  The earlier docs-memory report said "don't build a four-folder Diátaxis tree from the
  top down". I agree for the reference corpus, and disagree for the front door.
- **It doesn't guarantee functional quality.** In its own words, "Diátaxis cannot
  address functional quality." Accuracy has to come from generation, tests, and the
  gardener, not from the taxonomy.

### 3.3 What I would do differently from a straight Diátaxis adoption

- **Use familiar labels instead of framework labels.** Use *Get started / Guides /
  Concepts / Reference*, as uv and Claude Code do, rather than *Tutorials / How-to /
  Explanation / Reference*. Diátaxis itself lists *Topics*, *Background*, and
  *Conceptual guides* as acceptable names for explanation.
- **Use directory = tier = type.** Putting the type in the path means agents don't need
  to remember a front-matter field. The lint can enforce it, and a wrong placement shows
  up in the diff.
- **Treat AI agents as a named audience, but a cheap one.** Add `llms.txt` and per-page
  Markdown copies, which come free with Zensical. Don't build an agent-specific docs
  tier.

---

## 4. Requirement adjustments (explicit)

| # | Your requirement, as I read it | Adjusted requirement | Why |
| --- | --- | --- | --- |
| **R1** | Drastically simplify sase's documentation. | **Drastically simplify the reader-facing Guide tier** (target ≤ 60K words, ≤ ~40 pages). **Shrink the hand-written Reference** through generation and history removal, and split it into budgeted pages. **Don't delete the spec.** | Agents depend on the detail, and power users need it too. The UX problem comes from where the detail sits and how it's arranged, not from the fact that it exists. |
| **R2** | Use Diátaxis as inspiration. | **Use Diátaxis types plus an audience split** (an *Internals* section). Apply it **top-down for the Guide**, and bottom-up with ratchets for the Reference. | Diátaxis has no audience axis, and its anti-plan advice fits the reference corpus but not a front door that barely exists (§3.2). |
| **R3** | Add more structure to the documentation process. | **A lint-enforced contract:** directory-typed pages, templates, per-type budgets with a ratchet, nav and anchor validation, present-tense-only text in the Guide, generated registries, and a change→docs routing table. | Without enforcement, +37% monthly growth undoes any reorganization (§2). |
| **R4** | *(new)* | **Retire the 1,151-page PDF handbook.** If Bryan wants an offline copy, at most publish a Guide-tier PDF (about 100 pages) while on Material. | No reader uses an 1,151-page PDF. It is a large build cost, and it is the only part of the stack that blocks Zensical. |
| **R5** | *(new)* | **Make the restructure Zensical-portable,** and migrate after 0.1.0, before May 2027. Don't migrate to another framework. | Material is in maintenance mode, and MkDocs 2.0 breaks plugins. |
| **R6** | *(new)* | **Tutorials are tested.** Shell blocks in `docs/start/` run in a sandbox against `fakey` in the scheduled full-CI lane. Screenshots and GIFs are regenerated from seeded demo state. | Diátaxis requires "perfect reliability". The current tutorial has nearly tripled in four months. |
| **R7** | *(new)* | **History lives in the CHANGELOG and decision records, never in Guide pages.** | 741 history phrases. Readers need current behavior. |
| **R8** | Agentic management is secondary. | Agreed, **with one exception that is not optional:** an accretion guard (budgets plus routing feature work into the Reference tier). | Without it, the simplification doesn't survive a month. |

---

## 5. Options considered

| Option | What it is | Verdict |
| --- | --- | --- |
| **A. Polish the status quo** | Rename nav groups, trim the homepage, turn on tabs | **Reject as the plan, but use it as Phase 0.** Cheap and visible, but it doesn't touch accretion, types, or the tutorial. |
| **B. Full top-down Diátaxis rewrite** | Four folders, rewrite all 518K words | **Reject.** Huge review load, conflicts with about 20 docs commits a day, and loses spec detail agents use. Diátaxis itself warns against it. |
| **C. Cut to uv size** | Delete or abridge everything that isn't Guide material | **Reject.** It moves the problem into agent accuracy, and users lose consultable reference. |
| **D. Two tiers: curated Guide plus generated, split Reference (with Internals)** | Top-down Guide, bottom-up Reference, a lint contract, and tested tutorials | **Recommended.** It fixes the reader's path immediately and leaves the spec in place for agents. Each phase pays off independently. |
| **E. Two sites** | sase.sh holds only the Guide. The exhaustive manual is repo-only or on a second site | **Defer.** Reconsider if the Reference tier is still dominating search after generation. With tabs and search boosts, one site is simpler. |
| **F. Switch frameworks** (Starlight, Docusaurus, Mintlify, Fumadocs) | Rebuild the site on a JS stack | **Reject.** It throws away a Python-native toolchain that agents already know, and the restructure doesn't need it. Zensical is the low-cost continuation. |

---

## 6. Recommended solution

### 6.1 The model: two tiers, five tabs

```text
sase.sh
├─ Home                         one screen: what, who for, install, demo, 3 doors
├─ Get started   (tutorials)    ┐
├─ Guides        (how-to)       ├─ THE GUIDE: curated, budgeted, human-reviewed, ≤ ~60K words
├─ Concepts      (explanation)  ┘
├─ Reference     (reference)    ── THE REFERENCE: generated where possible, split, budgeted
│   └─ Contributing & internals    design contracts, runbooks, provider APIs, Rust core
└─ Blog
```

- **The directory is the type:**
  - `docs/start/`, `docs/guides/`, and `docs/concepts/` hold the Guide.
  - `docs/reference/` holds the Reference.
  - `docs/reference/internals/` holds contributor material.
  - `docs/blog/` is unchanged.
- **Reader promise:** the Guide never sends a newcomer into the Reference to finish a
  task. The Reference never repeats teaching. It links back to Guides and Concepts, as
  Diátaxis prescribes ("link to how-to guides, explanation and introductory
  tutorials").

### 6.2 Proposed navigation (target state)

```yaml
nav:
  - Home: index.md
  - Get started:
      - start/index.md                     # Is sase for you? requirements, alpha status, the 3 tutorials
      - Install: start/install.md          # uv + one provider + `sase doctor`
      - Your first agent run: start/first-run.md          # tutorial 1, ~15 min, read-only, +home
      - Land your first change: start/first-change.md     # tutorial 2: edit → review diff → commit/propose
      - Plan and run a multi-agent change: start/first-epic.md  # tutorial 3: plan → approve → epic → land
  - Guides:
      - guides/index.md                    # a rich goal list (Diátaxis: "an encouraging suggestion of capabilities")
      - Daily work:
          - Run agents in parallel: guides/parallel-agents.md
          - Review and land agent changes: guides/land-changes.md
          - Hand work from one agent to another: guides/artifact-refs.md
          - Reuse prompts with macros: guides/macros.md
          - Track work with beads: guides/beads.md
          - Track an outcome with a goal: guides/goals.md
          - Find and replay old prompts: guides/prompt-history.md
      - Automate:
          - Schedule recurring agent work: guides/schedule.md
          - Build a multi-step workflow: guides/workflows.md
          - Get automated code review: guides/mentors.md
          - Run long commands without blocking: guides/monitors.md
          - Approve privileged commands safely: guides/sudo.md
      - Set up and customize:
          - Set up a project: guides/init.md
          - Choose providers and models: guides/providers.md
          - Give agents project memory: guides/memory.md
          - Configure sase: guides/configure.md
          - Customize keybindings: guides/keybindings.md
          - Editor and shell completion: guides/editor.md
          - Install plugins: guides/plugins.md
          - Run agents on another machine: guides/remote.md
          - Use sase from your phone: guides/mobile.md
      - Fix problems:
          - Start with sase doctor: guides/troubleshoot.md
          - An agent is stuck QUEUED: guides/queued-agents.md
          - Recover an interrupted agent: guides/recover-agents.md
  - Concepts:
      - How sase works: concepts/index.md  # the one-page mental model + one diagram
      - Agents, sessions, and workspaces: concepts/agents.md
      - Work units — Patches, beads, plans, goals: concepts/work-units.md
      - How changes land: concepts/landing.md
      - Prompts, macros, and workflows: concepts/prompts.md
      - Memory and agent instructions: concepts/memory.md
      - Background automation: concepts/automation.md
      - Providers and models: concepts/providers.md
      - Design principles: concepts/principles.md   # generated index of decision records
  - Reference:
      - reference/index.md
      - CLI: reference/cli/            # generated, one page per command group
      - Configuration: reference/config/   # generated from sase.schema.json, one page per key family
      - TUI: reference/tui/            # one page per tab + generated keymap
      - Macro language: reference/macros/  # grammar, directives (generated rows), discovery order (generated)
      - Workflow YAML: reference/workflow-yaml.md
      - Query language: reference/query-language.md
      - File formats: reference/formats/   # Patch, ProjectSpec, memory notes, plans
      - Providers and models: reference/providers.md  # generated tier/alias tables
      - Environment variables: reference/environment.md
      - Glossary: reference/glossary.md    # generated from the glossary memory web
      - Contributing & internals: reference/internals/
  - Blog: blog/index.md
```

**Budget:**

| Tab | Pages | Words |
| --- | --- | --- |
| Get started | 5 | about 8K |
| Guides | about 27 | about 30–35K |
| Concepts | 9 | about 20K |

That puts the Guide at about 60K words, comparable to uv's entire hand-written corpus.

### 6.3 Where every current page goes

"→ G" means a Guide page that has to be *written*, using the old page as source. "→ R"
means it moves into the Reference, split or generated. "→ I" means Internals.

| Current page (words) | Disposition |
| --- | --- |
| `getting_started` (4.1K) | → G: `start/install`, `start/first-run` (steps 1–4), `start/first-change` (step 5). Step 8 → `start/first-epic`. Steps 6–7 → guides `artifact-refs` and `macros`. "Component Map" → `concepts/index`. |
| `index` (0.9K) | Rewritten (§6.4) |
| `init` (7.6K) | → G `guides/init` (short). → R `reference/cli/init` (generated) and `reference/formats` (memory init). |
| `agent_providers` (5.2K) | → G `start/install` and `guides/providers`. → R `reference/providers` |
| `content_layout` (0.8K) | → R "Upgrading" note under internals, or CHANGELOG. Not in Get started. |
| `instruction_inventory` (0.7K) | **Remove from site.** It's a historical migration inventory, so move it to research or `sdd/`. |
| `instruction_bundles` (2.4K) | → G `concepts/memory` section. → I for manifest internals. |
| `memory` (3.6K), `memory_history` (2.7K) | → G `concepts/memory` and `guides/memory`. → R `reference/formats/memory`, `reference/tui/memory` |
| `ace` (103K) | → G: a TUI tour inside `start/first-run` and `concepts/index`, plus `guides/keybindings`. → R: `reference/tui/{agents,artifacts,services,projects,machines,tools,statistics,prompt-input,command-line,launch-control}.md` plus a **generated** `reference/tui/keymap.md` |
| `artifacts_pane_contract`, `artifacts_pane_visual_grammar` | → I |
| `axe` (16.9K) | → G `concepts/automation` and `guides/schedule`. → R `reference/scheduler.md` |
| `sdd` (7.8K), `sdd_storage` (3.5K) | → G `concepts/work-units` and `start/first-epic`. → R `reference/formats/plans`. → I (storage) |
| `macros` (32K) | → G `concepts/prompts` and `guides/macros`. → R `reference/macros/{syntax,directives,discovery,cli}` (directive rows and discovery order generated) |
| `artifact_references`, `artifact_links`, `pager`, `prompt` | → G `guides/artifact-refs` and `guides/prompt-history`. → R one page each |
| `architecture` (3K) | → G `concepts/index` (user-level picture). → I `internals/architecture` |
| `change_spec`, `project_spec` | → G `concepts/work-units`. → R `reference/formats/{patch,projectspec}` |
| `beads` (28K), `goals` (0.7K) | → G `guides/beads`, `guides/goals`, `concepts/work-units`. → R `reference/beads` (CLI generated) |
| `workflow_spec` (4.3K) | → G `guides/workflows`. → R `reference/workflow-yaml` |
| `agent_sessions` (8.1K), `agents_sidecar` (4.5K) | → G `concepts/agents`. → I (sidecar sync) |
| `monitors` (8.5K), `tool` (6.6K), `mentors` (1.7K), `sudo` (2.5K) | → G one goal-titled guide each. → R the detail. Epic-labeled `tool.md` sections → I |
| `workspace` (6.7K), `vcs` (6K) | → G `concepts/agents` (workspaces). → I (provider APIs and hooks) |
| `commit_workflows` (8.6K) | → G `concepts/landing` and `guides/land-changes`. → I (orchestrator, payloads) |
| `notifications` (18.5K) | → G `guides/notifications` (in Daily work). → R `reference/notifications` |
| `mobile_gateway` (4.2K), `remote_dispatch` (3K) | → G `guides/mobile` and `guides/remote`. → I (gateway API) |
| `mobile_mvp_runbook`, `perf_runbook`, `telemetry`, `fakey`, `rust_backend`, `integrations`, `development` | → I |
| `troubleshooting/*`, `agent_auto_restart` | → G "Fix problems" |
| `editor`, `completion` | → G `guides/editor` (one page). → R `reference/lsp` if needed |
| `plugins` (10.5K) | → G `guides/plugins`. → I "Write a plugin" |
| `llms` (26.8K) | → G `concepts/providers` and `guides/providers`. → R `reference/providers` (generated tables). → I (provider architecture) |
| `cli` (14.6K) | → R `reference/cli/*`, **generated** |
| `configuration` (71K) | → G `guides/configure` (about 1.5K). → R `reference/config/*`, **generated** from the schema. Hand-written notes only where the schema can't say it. |
| `query_language`, `agent_images` | → R |
| `acknowledgements` | Footer or About link |

### 6.4 Homepage and site UX spec

**Homepage: one screen and three doors.** Hide the sidebar and TOC with
`hide: [navigation, toc]`.

1. **Hero:**
   - One sentence, close to the README's: *"Run a team of coding agents (Claude Code,
     Codex, and more) in parallel, isolated workspaces, and track, review, and land
     their work from one terminal UI."*
   - A status pill: *Alpha · Linux & macOS*.
   - **A three-line install block with a copy button:** `uv tool install sase`,
     `sase doctor`, `sase tui`.
   - Primary CTA: **Start the 15-minute tutorial**. Secondary: **How sase works**. Third:
     GitHub.
2. **One demo:** the 25-second multi-model fan-out GIF from `demos/out/`. It's already
   produced, privacy-safe, and reproducible.
3. **"What sase adds to your agent CLI": four cards.** Parallel isolated runs ·
   Supervise from one TUI · Durable, reviewable work · Reusable prompts and automation.
   Each links to a Concept page, not to a reference page.
4. **"How these docs are organized": four doors,** each a one-line description of a
   tab: Learn (Get started), Do (Guides), Understand (Concepts), Look up (Reference).
   This makes Diátaxis visible the way Django's "How the documentation is organized"
   section does.
5. Footer row: launch post · blog · GitHub · acknowledgements. **Remove the PDF
   button.**

**Theme features** (all available in Material 9.7 and expected to carry over to
Zensical):

- **Turn on:**
  - `navigation.tabs`, `navigation.tabs.sticky`, `navigation.path` (breadcrumbs);
  - `navigation.footer` (previous/next, so tutorials read in sequence);
  - `navigation.indexes` (already on);
  - `toc.follow`, `content.code.copy`, `search.suggest`, `search.highlight`.
- **Keep `navigation.sections` within tabs.** With tabs on, each sidebar shows only its
  own tab, at most about 30 items for Guides and about 9 for Concepts, instead of 60+.
- **Search tuning:** set `search: boost: 2` in front matter for `start/` and
  `concepts/`. Set `search: exclude: true` on generated reference pages only if they
  crowd out results. Measure before excluding anything.

**Glossary tooltips.**

- Generate `docs/_includes/abbreviations.md` from the glossary memory web, limited to
  about 15 core terms (Patch, bead, epic, workspace, project, macro, stitch, goal, gate,
  monitor, and so on).
- Auto-append it with `pymdownx.snippets` and `abbr`, so hovering any of these terms in
  the Guide shows its one-line definition.
- This is the cheapest available fix for jargon load. It doesn't apply inside code.

**Page templates** (one per tab; see §6.6), so every page opens the same way:

- one sentence saying what the page is for;
- for tutorials and guides, a "Before you start" line;
- a closing "Next" line.
- How-to titles are goals ("Get automated code review"). Concept titles take an
  implicit "About …" (Diátaxis). Reference titles name the thing.

**Agents as readers:** add `llms.txt` and per-page Markdown copies. Defer this to the
Zensical migration, where it is built in. Before then, `mkdocs-llmstxt` works but is
itself in maintenance mode.

**Analytics:** turn on cookie-less Cloudflare Web Analytics for the site, which is
already on Cloudflare. Today nobody knows which pages visitors read. The success
metrics in §6.10 need that data.

### 6.5 Concepts: teach a small model first

The glossary has about 70 terms. The Guide should teach **seven nouns** before it uses
anything else:

**project → workspace → agent → prompt/macro → Patch → bead/plan → TUI**

Everything else (clan, tribe, hood, deck, card, stitch, chop, routine, gate, monitor,
ToolRun, and so on) is introduced only on the page that needs it, and linked to the
generated glossary.

`concepts/index.md` ("How sase works") should have exactly one diagram and fit on about
two screens. It should be the page the homepage's secondary CTA and every "why?"
question point to.

### 6.6 The documentation process contract

This is the "more structure" half of your request. Everything here is mechanical and
lint-checked by a fast `tools/check_docs` in `just check`, plus `mkdocs build --strict`
on the landing path.

**1. Typing.** The directory decides the type. Each page needs a one-line `description:`
in its front matter, which is also used for the meta description and `llms.txt`.
Reference and internals pages may also declare `covers:` (code globs), as the earlier
docs-memory report proposed. That report's `kind:` field becomes redundant with
directories; if kept, the lint just checks that it agrees with the path.

**2. Templates.** Keep them in `docs/_templates/` (excluded from the build):

| Template | Shape |
| --- | --- |
| Tutorial | Goal sentence · prerequisites · numbered steps, each ending in a visible result · "What you did" · Next. No options, no alternatives, no "why". |
| How-to | Goal-titled · "Before you start" · steps or recipe · variations (at most 3) · related links |
| Concept | "About X" · the problem it solves · the model (one diagram allowed) · trade-offs and alternatives · related guides |
| Reference | Mirrors the product unit (command group, config family, TUI tab) · consistent tables · **no narrative** · links out |

**3. Budgets (words, enforced by a ratchet).** A page over budget may not grow, and new
pages must fit.

| Tier | Budget per page | Tier total |
| --- | --- | --- |
| `start/` | ≤ 2,500 | ≤ 10K |
| `guides/` | ≤ 1,500 | none (count grows with goals) |
| `concepts/` | ≤ 3,000 | ≤ 25K |
| `reference/` (hand-written) | ≤ 6,000 | none |
| Generated pages | exempt | — |
| `internals/` | ≤ 8,000 (warn only) | — |

**4. Guide-tier hygiene lint.** This applies to `start/`, `guides/`, and `concepts/`
only.

- No bead IDs, no `src/` paths, and no epic or phase labels.
- No history phrases ("formerly", "no longer", "legacy", "renamed", "still mentions").
  An allowlist covers real migration guides.
- Every shell block in `start/` carries a test marker.

**5. MkDocs validation:**

```yaml
validation:
  omitted_files: warn
  anchors: warn
  absolute_links: warn
  unrecognized_links: warn
exclude_docs: |
  _templates/
  _includes/
  images/**/*.md
```

Combined with `--strict`, these warnings fail the build. That catches unlisted pages and
broken anchors. Run `just docs-check` in the master gate, or whenever `docs/` or
`mkdocs.yml` changes, so the gap the earlier report found (strict build only on PRs) is
closed.

**6. Generated registries.** Extend the existing `BEGIN GENERATED` / `--check` pattern
from `tools/render_model_docs` into one renderer with providers:

| Registry | Source | Replaces |
| --- | --- | --- |
| CLI reference | the argparse tree (already snapshotted for completion by `tools/sync_completion_spec`) | `cli.md`'s 14.6K hand-written words and its stale caveats |
| Config reference | `src/sase/config/sase.schema.json` (65 top-level keys, ~1,000 properties) | most of `configuration.md`'s 71K words |
| TUI keymap | `default_config.yml` `keymaps:` and the `KeymapRegistry` that already feeds the in-app footer and help | about 475 table rows in `ace.md`'s four Keybindings sections |
| Directives and macro discovery order | the Rust `directive_contract` and `resolve_macro_file_sources` (earlier report) | drifted hand tables |
| Glossary and design principles | the `glossary` and `decisions` memory webs | nothing today; these are new and read-only |
| Model and provider tables | `tools/render_model_docs` (existing) | — |

Generate **tables, not chapters**. The hand-written reference pages keep the prose that
a schema can't hold.

**7. Present tense only.** The docs describe current behavior. Changes go in the
CHANGELOG, rationale goes in decision records (shown on the generated "Design
principles" page), and deprecations go in a single `reference/upgrading.md`.

**8. Change → docs routing table.** This goes in Development → Documentation, and in a
reference-memory trigger for agents. That memory change has to go through
`/sase_memory_write`.

| You changed… | Docs action |
| --- | --- |
| A CLI flag or command, a config key, a keybinding, a directive, or a model | Regenerate. **Write no prose** unless the generated description is insufficient. |
| The behavior of an existing feature | Update its `reference/` page. If a tutorial or guide step is now wrong, fix that step and nothing more. |
| A new user-visible capability | Add a reference entry. If it serves a new user *goal*, write a guide **only if asked**. Otherwise file a "guide candidate" follow-up. **Never append narrative to a Guide page.** |
| A design decision or trade-off | Write a decision record. It appears on the generated Design principles page. |
| Internals, contracts, or runbooks | `reference/internals/` |

**9. Tested tutorials.**

- `tests/docs/` runs the marked shell blocks of `start/*.md` in a temporary
  `HOME`/`SASE_HOME` with the `fakey` provider.
- It asserts each step's "visible result".
- It runs in the scheduled full-CI lane, which matches `ci-two-speed-split`.
- Screenshots and GIFs come from `demos/` tapes and seeders, or from `sase screenshot`,
  regenerated by recipe, never by hand.

**10. Prose pins in tests.** Existing tests that pin `docs/*.md` prose get rewritten to
pin generated blocks or reference pages. New tests may not pin Guide-tier prose. Guide
text has to stay editable by a human editor.

### 6.7 Platform decision

- **Now:** restructure on MkDocs Material 9.7.
  - Use no new Python `hooks:`, no `gen-files`, and no custom Python plugins. Do
    generation in `tools/` *before* the build, as `render_model_docs` already does.
  - Keep templates MiniJinja-safe: no Python calls in `overrides/main.html`.
  - Then a Zensical migration is configuration-level work.
- **Retire `mkdocs-pdf.yml` and the handbook** (R4). Doing this removes the only plugin
  without a Zensical path, a Chromium/Playwright build step, and a 14.6 MB artifact.
- **After Zensical 0.1.0 (planned 2026-11-05), and before 2027-05-05:**
  - trial `zensical build` against the restructured repo;
  - verify the blog, RSS, redirects, the `custom_dir` override, and search;
  - turn on the built-in `llmstxt` and "Copy as Markdown".
- **Don't** move to Starlight, Docusaurus, or Mintlify. Nothing in this plan needs them,
  and the Python-native toolchain is part of what keeps agent maintenance cheap.

### 6.8 Long-term agentic maintenance (brief, by request)

- **Two editing regimes.** Feature agents own the **Reference** tier: they regenerate
  and update `covers`-matched pages, following the earlier report's
  `sase docs affected` and gardener design. The **Guide** tier is *curated*. Feature
  agents may correct a broken step, but new Guide content arrives through an explicit
  docs task. The budget lint enforces this mechanically.
- **A periodic docs-editor routine** (weekly, through the scheduler):
  - reads the CHANGELOG and `docs affected` since its last run;
  - checks tutorial-test results and the "guide candidate" backlog;
  - proposes Guide edits as a **plan for human approval**.
  - Diátaxis is clear that "deep quality" needs judgment, and the Guide is where that
    judgment pays off.
- **Defects found while writing docs become `bug` task beads,** not sentences in the
  docs. This repeats the earlier report's R4 and fixes the "help text still says…"
  pattern.

### 6.9 Migration plan

The order is designed to avoid collisions with concurrent agents.

| Phase | Scope | Conflict risk | Exit criteria |
| --- | --- | --- | --- |
| **0. Front-door quick wins** (1–2 days) | Add tabs, breadcrumbs, and copy buttons. Add the `validation:` block and `exclude_docs`. Add `docs-check` to the gate. Rewrite the homepage (§6.4). Drop the PDF button. Regroup the **existing** pages into the five tabs **without moving files**: legacy pages sit under Reference, and internals under Reference → Internals. Remove `instruction_inventory` from the nav. | Low: only `mkdocs.yml` and `index.md` change | Sidebar shows ≤ 30 items per tab. The homepage shows install and demo above the fold. The strict build validates anchors and omitted files. |
| **1. Write the Guide** (new files) | `start/` (3 tutorials plus install), `concepts/` (9), then about 25 goal-titled `guides/`, written from the old pages as source. Add templates, budgets, the hygiene lint, and the glossary tooltips. | None: these are new files | The Guide is ≤ 60K words, every Guide page is within budget, and tutorial tests pass on `fakey`. |
| **2. Generate the registries** | CLI, config, keymap, directives, glossary, and design principles. Delete the hand tables they replace. Re-point tests that pin prose. | Medium: these edits touch hot pages, so do each registry as one quick commit | No hand-maintained registry tables remain. `cli.md` and `configuration.md` are mostly generated. |
| **3. Decompose the monoliths** | One page at a time, largest first (`ace`, `configuration`, `macros`, `beads`, `llms`, `notifications`, `axe`). Use a **move-only** commit plus redirects, then content commits. Update the agent routing trigger so agents edit the new paths. Strip history phrases into the CHANGELOG. | Medium: mitigated by move-only commits and the routing trigger | No `reference/` page over budget. Zero history phrases in the Guide. The legacy-mixed page count reaches 0. |
| **4. Zensical** | After 0.1.0: trial build, then switch. Turn on `llmstxt` and Copy as Markdown. | Low | The site builds on Zensical with blog, RSS, and redirects intact, before 2027-05-05. |
| **5. Maintenance loop** | The docs-editor routine, the scoped gardener, and the guide-candidate backlog | — | Hand-written growth stays ≤ 5% a month. |

**Phase 0 alone fixes most of the first-impression problem.** Phases 0 and 1 together
deliver the "simple and intuitive" site. Phases 2 and 3 shrink and stabilize what's
behind it.

### 6.10 Success metrics

| Metric | Today | Target |
| --- | --- | --- |
| Guide-tier words (start, guides, concepts) | n/a (about 4K of real tutorial) | ≤ 60K, every page within budget |
| Hand-written words, month-over-month growth | +37% | ≤ +5% |
| Sidebar items visible on any page | about 60 | ≤ 30 (Guides), ≤ 10 elsewhere |
| Homepage primary choices | about 25 cards | 3 CTAs plus 4 doors |
| Install command and demo above the fold | no and no | yes and yes |
| Tutorial reliability | untested | tutorial tests green in full CI |
| History phrases, bead IDs, `src/` paths in the Guide | n/a (741, 148, and 382 corpus-wide) | 0 |
| Hand-maintained registry tables | CLI, config, keymaps, directives | 0 |
| Pages over budget | 12 pages over 15K tokens | 0, with the ratchet only going down |
| PDF | 1,151 pages | retired |
| Reader data | none | Cloudflare Web Analytics: entry pages, tutorial completion (whether readers reach the last tutorial page), search terms |

### 6.11 What not to do

- Don't rewrite the 518K-word corpus top-down, and don't create empty Diátaxis folders.
- Don't delete reference detail that agents rely on. Move it, generate it, or split it.
- Don't let feature agents append narrative to Guide pages. That's the accretion engine.
- Don't keep history in user-facing pages.
- Don't add Material-only Python hooks or plugins during the restructure, and don't
  switch to a JavaScript docs framework.
- Don't put a docs map or docs content into always-loaded agent instructions without
  measuring it (the earlier report's caution still applies).

---

## Recommendation (summary)

1. **Adopt the two-tier model.** The *Guide* (Get started, Guides, Concepts) is
   curated, Diátaxis-typed, about 60K words, and tested. The *Reference* (CLI, config,
   TUI, formats, and Contributing & internals) is generated where it's a registry,
   split where it's prose, and kept as the agents' spec.
2. **Ship Phase 0 this week:** tabs, a regrouped nav without file moves, a one-screen
   homepage with install plus demo, validation, and the docs build in the gate. Drop
   the PDF.
3. **Write the Guide as new files** (three tutorials, nine concepts, about 25
   goal-titled guides), with templates, budgets, and tutorial tests on `fakey`.
4. **Generate the registries, then decompose the monoliths one page at a time,**
   using move-only commits and redirects.
5. **Enforce the contract in `just check`** (directory types, budgets with a ratchet,
   Guide hygiene, present-tense-only text, the routing table) so the site doesn't
   regrow at +37% a month.
6. **Migrate to Zensical after 0.1.0, and before Material's May 2027 support end,**
   picking up `llms.txt` and Copy-as-Markdown for free.

---

## Sources

**Diátaxis**

- https://diataxis.fr/
- https://diataxis.fr/start-here/
- https://diataxis.fr/compass/
- https://diataxis.fr/how-to-use-diataxis/
- https://diataxis.fr/map/
- https://diataxis.fr/tutorials/
- https://diataxis.fr/how-to-guides/
- https://diataxis.fr/reference/
- https://diataxis.fr/explanation/
- https://diataxis.fr/quality/
- `/complex-hierarchies/` and `/adoption/` returned 404.

**Practitioner critiques of Diátaxis (informal)**

- https://hn.svelte.dev/item/49138188
- https://github.com/lark-parser/lark/discussions/1360
- https://discuss.ocaml.org/t/diataxis-documentation-structure/7750
- https://stevearrants.substack.com/p/documentation-frameworks-a-field

**Exemplar docs sites**

- https://docs.astral.sh/uv/
- https://docs.astral.sh/ruff/
- https://docs.djangoproject.com/en/stable/
- https://code.claude.com/docs/en/overview and https://code.claude.com/docs/llms.txt
- https://learn.chatgpt.com/docs (redirect target of developers.openai.com/codex)
- https://docs.gitlab.com/
- https://tailscale.com/kb

**uv repository** (opened via `sase repo open gh:astral-sh/uv`): `mkdocs.yml`,
`docs/`, `.gitignore`, `crates/uv-dev/src/generate_cli_reference.rs`

**Platform**

- https://squidfunk.github.io/mkdocs-material/blog/2025/11/11/insiders-now-free-for-everyone/
- https://github.com/squidfunk/mkdocs-material/issues/8523
- https://squidfunk.github.io/mkdocs-material/blog/2026/02/18/mkdocs-2.0/
- https://zensical.org/docs/compatibility/mkdocs/
- https://zensical.org/docs/compatibility/mkdocs/plugins/
- https://zensical.org/roadmap/
- https://zensical.org/upcoming-changes/
- https://pypi.org/project/zensical/
- https://github.com/pawamoy/mkdocs-llmstxt

**Live measurements** (2026-10-15)

- `curl` sizes for `https://sase.sh/`, `/ace/`, `/configuration/`,
  `/search/search_index.json`, `/downloads/sase-handbook.pdf` (1,151 pages via
  `pdfinfo`), and `/llms.txt` (404)
- sidebar link count on `/getting_started/`
- `gh api` repo stats and traffic for `sase-org/sase`

**Local:** sase `bc4bc3e183`, covering `mkdocs.yml`, `mkdocs-pdf.yml`, `docs/**`,
`Justfile`, `tools/render_model_docs`, `tools/sync_completion_spec`,
`src/sase/config/sase.schema.json`, `src/sase/default_config.yml`, `demos/`, git
history, and word counts at five dates.

**Earlier sase research (background):**

- `research:202605/sase_sh_site_design_research.md`
- `research:202610/docs_backed_memory_and_agent_maintained_docs/docs_backed_memory_and_agent_maintained_docs__final.md`
