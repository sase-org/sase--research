# Redesigning sase.sh: A Small, Diátaxis-Typed Guide in Front of a Generated Reference

> **Research question:** Drastically simplify SASE's documentation on sase.sh, making it
> simpler and more intuitive, while adding more structure to the documentation process.
> Use [Diátaxis](https://diataxis.fr) for inspiration. Consider long-term agentic
> maintenance, but focus on the best documentation solution and structure, and on how
> sase.sh's UX helps people learning about SASE. Critique the plan, call out any
> requirement adjustments, and end with a recommended solution.

This report consolidates five independent reports (`cdx`, `cld`, `grk`, `mus`, `gem`)
and adds the lead's own checks. The checks ran on 2026-10-15 against sase `bc4bc3e183`,
the live site, GitHub Actions logs for the docs deploy, and PyPI. The raw reports sit
next to this file as `sase_sh_docs_redesign__<suffix>.md`.

---

## Bottom line

**Yes, do it.** The site is hard to learn from, and today's documentation process
guarantees it will get worse. Diátaxis is the right inspiration. All five researchers
agree on the diagnosis. The corpus is a **518K-word behavior spec published as a user
manual**, under a navigation that sorts by the author's sense of difficulty ("The
Basics", "The Nitty Gritty") rather than by what the reader needs. It is growing about
**37% a month**, mostly as a side effect of feature commits.

The lead's checks add one finding that outranks every structural question:

> **Today, a newcomer who follows step 1 of the sase.sh tutorial (`uv tool install sase`)
> silently gets sase 0.1.0 from February 2026.** Every release from 0.2 through 0.17.1
> fails to resolve on PyPI (tracked as bug `sase-16p`). sase.sh describes `master`, which
> is 2,559 commits past the newest release. Even the newest release's own tutorial says
> `sase ace`, while the site says `sase tui`.

No information architecture fixes a front door whose first command installs the wrong
product. So the first adjusted requirement (R0 below) is a working install that matches
the docs. The rest of the recommendation is about structure.

**Recommended solution, in brief:**

1. **Split the site into two tiers, each sized for its readers.**
   - **The Guide** (*Get started*, *Guides*, *Concepts*) is small, typed, budgeted, and
     human-curated.
   - **The Reference** is mostly generated from the code that owns each fact and is
     split into lookup-sized pages. It keeps the full spec that agents and power users
     rely on.
   - Contributor material moves to a separate **Contribute** tab.
2. **Use Diátaxis as the editorial model, with plain user labels.** The tabs are
   *Get started · Guides · Concepts · Reference · Contribute · Blog*. The directory a
   page lives in decides its type.
3. **Rebuild the front door top-down and decompose the reference bottom-up.**
   - Write the homepage, two tested tutorials, about seven concept pages, and the first
     ~12–15 goal-titled guides as **new files**.
   - Split the monolith pages one at a time, using move-only commits plus redirects.
4. **Make the process enforceable, not aspirational.**
   - Directory-typed pages, templates, and word budgets with a ratchet.
   - Guide-tier hygiene lint, generated registries, and a URL and anchor contract test.
   - A "where does my change go?" routing rule for feature agents.
   - Without these, 37% monthly growth buries any reorganization within weeks.
5. **Stay on MkDocs Material for the restructure, but keep it Zensical-portable.**
   Material's critical fixes end **May 5, 2027**. Trial Zensical after its 0.1.0 release
   (planned for **Nov 5, 2026**) and decide by about February 2027.
6. **Decide the PDF's scope now.** The full-corpus handbook is 1,151 pages and already
   breached its size gate once. It takes about 8 of every deploy's ~9 minutes, and it is
   the only part of the stack Zensical can't build. Curating it down to a Guide-tier
   handbook is recommended, but this is Bryan's call.

---

## 1. Verified facts

The lead re-checked every row against the repo, the live site, CI logs, or PyPI. Rows
marked **new** appear in none of the five reports.

### Size, shape, and growth

| Fact | Value |
| --- | --- |
| Docs pages (excluding blog, image briefs, templates) | 57 pages, **518,106 words** |
| Concentration | `ace.md` 103K words and `configuration.md` 71K words are 34% of the corpus. The top 5 pages hold 50%. |
| Growth (words at each date) | 117K (Jun 15) → 152K (Jul 15) → 287K (Aug 15) → 379K (Sep 15) → 518K (Oct 15). That is 4.4× in four months, and +37% in the last month. |
| Who writes the docs (last 30 days) | 617 commits touched `docs/`: 452 `feat`, 83 `fix`, 68 `docs`. `ace.md` got 259 commits and `configuration.md` got 202. 335 of the 350 commits to those two pages have no plan reference (**new**). |
| The tutorial | `getting_started.md` grew from 1.5K words (July) to 4.1K (October), with 40 commits in 30 days. Step 3 alone explains provider auto-detection exceptions and size-alias routing. |
| Homepage | 4 equal hero buttons, 8 role cards, a primitives list, and 8 "next click" cards. The lede leads with "a Python CLI and TUI backed by a required Rust core". |
| Nav | About 60 always-expanded sidebar links, using `navigation.sections` without `navigation.tabs`. "Getting Started" includes *Content Layout Migration* and the historical *Instruction Inventory*. "The Basics" includes two internal TUI design contracts. |
| History and internals in user text (`cld`) | 741 history phrases ("formerly", "legacy", "no longer"…), 148 bead-ID mentions, 382 `src/` paths |
| Page frontmatter | Only `index.md` and `getting_started.md` have any, outside the blog |

### Installability and applicability (all new)

| Fact | Value |
| --- | --- |
| Newest PyPI release | `sase` **0.17.1**, published 2026-08-29. `master` is **2,559 commits** ahead. |
| What `uv tool install sase` installs today | **`sase==0.1.0`** (2026-02-23). Every version ≥ 0.2 has no solution, because 0.17.1 needs `sase-core-rs<0.33` and PyPI only has ≥ 0.34.23 (bead `sase-16p`, READY since 2026-09-22). |
| Blocker for 0.18.0 | Release PR #299 has been waiting since 2026-08-30 on a green Full CI (epic `sase-1jz`) |
| Docs vs. installable product | sase.sh deploys from every `master` push. The 0.17.1 tutorial says `sase ace`, and `sase tui` only arrived on 2026-09-15. The xprompt→macro rename (2026-10-03) is also unreleased. |

### Site, links, and search

| Fact | Value |
| --- | --- |
| Live `/ace/` page | 953 KB of HTML, 266 KB compressed |
| Search index | 1.31 MB, 1,888 entries. Material indexes **sections**: 207 of 208 `ace` entries carry an anchor (**new**). This refutes `gem`'s claim that search lands readers at the top of a mega-page. The real problem is a 950 KB destination page with jargon headings. |
| Broken in-product doc links (**new**) | The TUI onboarding widgets link to `https://sase.sh/macro/` (`agent_onboarding.py:27`) and `https://sase.sh/patch/` (`patch_onboarding.py:29`). **Both return 404.** Nothing validates sase.sh URLs that appear in code. |
| Fragment links in the README | The README (also the PyPI long description) deep-links `/ace/#prompt-history-modal`, `/macros/#auto-directive`, `/sdd/#plan-decisions`, and more. Released READMEs freeze these links forever. |
| `llms.txt` | 404 |
| Docs build in the gate | Master Gate runs only `fmt-docs-check`. `mkdocs build --strict` runs in Full CI and in the post-push deploy, so a broken docs build is first seen after it lands. |
| Readership | GitHub shows 5 stars and 10 unique visitors in 14 days. sase.sh referred 3 unique visitors to GitHub. PyPI recorded 344 downloads last month. Earlier research found that about 38% of recent Codex sessions in sase workspaces shell-read a `docs/` page. **Today the main readers are Bryan and agents.** |

### The PDF handbook (mostly new)

| Fact | Value |
| --- | --- |
| Size | **1,151 pages, 13.9 MiB** on 2026-10-15. It was 891 pages and 20.0 MiB on 2026-09-17. |
| Gate | `tools/validate_docs_pdf` fails the deploy above **22 MiB**, because Cloudflare caps a static asset at 25 MiB. It **already breached the gate once**. Commit `c87c9d1aa9` (2026-09-23) squeezed the PDF back under it by rendering code chips square. |
| Projection (lead's extrapolation, not a measurement) | Page count grew 29% in the last month. If size tracks pages from here, the PDF reaches about 18 MiB by mid-November and crosses 22 MiB around December 2026. |
| Deploy cost | In the 2026-10-15 deploy, the PDF step took **7 min 53 s**. The HTML site took **8 s**. The deploy runs on every `master` push. |
| Intent | The original 2026-05 request was "all SASE documentation **and blog articles** as one polished PDF". A docs-only shrink was **reverted** 5 minutes after it landed (`3bb3cb9e26`). |

### Platform

| Fact | Value |
| --- | --- |
| Material for MkDocs | In its "final maintenance period". Critical bug and security fixes are **extended through May 5, 2027**, and "minor issues may not receive a fix" (issue #8523, retitled 2026-09-15). |
| Zensical | 0.0.70 (2026-10-12), PyPI status **Alpha**. "On November 5, 2026, Zensical 0.1.0 will begin a dependable release line." It reads `mkdocs.yml`. |
| Zensical plugin support | Supports `blog`, `rss`, `redirects` (anchor-based too), `search`, `social`, `tags`, and `llmstxt` (llms.txt plus "Copy as Markdown"). Does not support `gen-files`. **PDF export is roadmap-only.** Unlisted plugins such as `mkdocs-exporter` are "silently ignored". |
| Existing generation sources | `tools/render_model_docs` (the `BEGIN GENERATED` / `--check` pattern) and `tools/sync_completion_spec` (an argparse snapshot). `src/sase/config/sase.schema.json` has 65 top-level keys and 1,239 nodes, 883 of them (71%) with descriptions (**new**). The keymaps live in `default_config.yml`. |
| Tutorial-testing building blocks | The deterministic `fakey` provider, about 500 tests that already isolate `HOME`, and VHS demo tapes in `demos/` with ready GIFs (for example `sase_ace_multi_model_fanout.gif`) |
| `refresh_docs` prompts | Ask for docs that are "accurate, complete, and clear to someone new". There is no page type, budget, or canonical-owner constraint. |

---

## 2. Diagnosis

Navigation and the homepage are symptoms. The causes, in order of leverage:

1. **Nothing types the docs.** No rule says what a page is for (its Diátaxis type) or who
   it is for (user or contributor). Pages therefore drift toward exhaustive reference,
   which is the easiest text for a feature agent to write. A typical `ace.md` sentence:
   "`Ctrl+J` and `Ctrl+K` move to the next / previous card in the focused deck panel…".
   It is precise and valuable to an agent editing the deck, and useless to someone
   deciding whether SASE is for them. Both kinds of text sit on one page labeled "The
   Basics".
2. **Accretion is the default path.** Feature agents document by appending to the page
   nearest their code, and the refresh agents optimize for completeness. Even the
   tutorial absorbed 40 commits in a month.
3. **Registries are written as prose.** CLI flags, config keys, keymaps, directives, and
   the glossary are maintained by hand, so every feature adds rows by hand and the rows
   drift. Earlier research found `docs/macros.md` wrong about macro discovery order.
4. **Docs aren't tied to an installable version.** The site describes `master`, users
   install from PyPI, and nothing checks that the two agree. **(new)**
5. **Links into the docs are an unvalidated interface.** That covers code, README, and
   PyPI links, as the two 404 TUI links show. **(new)**

---

## 3. Critique of the plan

### Is it a good idea?

**Yes, and the timing is unusually good.** Inbound links are almost nonexistent (10
unique GitHub visitors in two weeks), so restructuring costs very little now. The launch
is meant to attract outside readers. And Material's end of life forces a platform
decision regardless.

Four cautions turn a good idea into a workable plan:

1. **"Drastically simplify the documentation" will be read as "delete the spec."** That
   would trade a UX problem for an agent-accuracy problem. Agents read `docs/` constantly,
   and Bryan uses that detail to trust agent-written behavior. Simplify what readers
   **meet**. Shrink what is **hand-written** by generating registries and removing
   history. Keep the rest as Reference, out of the learning path.
2. **A restructure alone decays.** At about 20 docs commits a day, a tidy tree drifts
   back to accreted pages unless budgets are enforced and feature work goes to the
   Reference tier by default. The "more structure" half of the request is what makes the
   "simpler" half last.
3. **A big-bang move collides with live agents.** With about 9 commits a day on `ace.md`
   and no PRs, a sweeping reflow conflicts with whatever agents are doing. Write new Guide
   pages as new files. Move reference content mechanically, one page at a time.
4. **The best site can't rescue a broken first command.** Fix installability and declare
   which version the docs describe before launching the new front door.

### What Diátaxis gives SASE, and what it doesn't

**What it gives:**

- **The four types match SASE's gaps exactly.** Tutorials are overloaded, how-tos are
  buried in reference pages, explanation is scattered, and reference is over-supplied.
- **"How-to guides are about goals… not about tools"** fixes a nav made of internal nouns
  ("Mentors", "Beads", "SDD Storage").
- **"Reference should mirror the structure of the product"** gives the Reference tab a
  rule: command groups, config key families, TUI tabs, and file formats. These are
  exactly the things that can be generated.
- **"Aspire to perfect reliability"** for tutorials becomes an engineering requirement:
  test them.
- **The compass** (action/cognition × study/work) is a cheap placement rule for humans
  and agents alike.

**What it doesn't give:**

- **No audience axis.** Diátaxis has no place for internals, contributor guides, or the
  agent-as-reader. SASE needs a contributor area (Django and Kubernetes both have one).
- **No guidance on landing pages, site UX, versioning, or governance.** Those are this
  report's additions.
- **No stance on generated reference**, which is SASE's main lever on size and drift.
- **It is deliberately anti-plan.** It warns against creating "empty structures… Don't
  do that. It's horrible" and against tearing everything down. That fits the 500K-word
  Reference, which should be improved bottom-up. It fits the front door poorly, because
  usable front-door content barely exists. Building the front door top-down **with real
  pages** avoids the empty-structure trap Diátaxis warns about.
- **"Diátaxis cannot address functional quality."** Accuracy has to come from
  generation, tests, and review.

### What I would do differently from a straight Diátaxis adoption

- **Use familiar labels instead of framework labels.** *Get started / Guides / Concepts /
  Reference*, as uv and Claude Code use, rather than *Tutorials / How-to / Explanation*.
  Readers never need to learn the word "Diátaxis". Make the system visible once, in a
  "How these docs are organized" strip, as Django does.
- **Treat it as a two-tier product, not a four-quadrant tree.** The curated Guide and the
  generated Reference have different authors, budgets, and editing rules. That
  difference is the real structural insight.
- **Lead with a tutorial, not with "How SASE works".** Sequin rewrote its "How Sequin
  works" first page into a three-minute quickstart because readers didn't get the model
  until they used the product.
- **Put a working install ahead of all of it.**

---

## 4. Requirement adjustments (explicit)

| # | Original requirement (as read) | Adjusted requirement | Why |
| --- | --- | --- | --- |
| **R0** | *(new)* | **A working install that matches the docs is a launch prerequisite.** Publish 0.18.0 (`sase-16p`). Add a scheduled smoke that installs `sase` from PyPI into a clean environment and runs the tutorial's first commands. | `uv tool install sase` installs 0.1.0 today. No IA change survives a broken step 1. |
| **R1** | Drastically simplify the documentation | **Drastically simplify what readers meet.** Keep the Guide tier small and budgeted (launch at about 30K words, cap at 60K). Shrink the hand-written Reference through generation and history removal. **Don't delete the spec.** | The problem is where detail sits and how it is arranged, not that it exists. Agents and power users depend on it. |
| **R2** | Use Diátaxis as inspiration | **Diátaxis types plus an audience split (Contribute), with user-facing labels.** Top-down for the front door, bottom-up for the Reference. | Diátaxis has no audience axis. Its anti-plan advice fits the reference corpus but not a front door that barely exists. |
| **R3** | Add more structure to the docs process | **A lint-enforced contract:** directory-typed pages, templates, word budgets with a ratchet, Guide hygiene, generated registries, URL/anchor checks, and a change→docs routing rule. | Unenforced rules lose to +37% monthly growth written by agents. |
| **R4** | Agentic management is secondary | **Agreed, with one non-optional exception:** the accretion guard (budgets plus routing feature work into the Reference). Everything else agentic waits. | Without the guard, the simplification doesn't survive a month. |
| **R5** | *(new)* | **URL and fragment compatibility is part of the contract.** That covers redirects for moved pages, fragment-aware redirects or anchor stubs for README and PyPI deep links, and a test that every sase.sh URL in `src/`, the README, and `_redirects` resolves. | Two in-product links already 404. Released READMEs freeze deep links. |
| **R6** | *(new)* | **Declare docs applicability.** The site states which version it describes and how to get that version. | sase.sh describes `master`, while users install from PyPI. |
| **R7** | *(new)* | **Decide the PDF's scope now.** The recommendation is a curated Guide-tier handbook, but Bryan decides. | It already breached its size gate, takes ~8 min per deploy, and has no Zensical path. |
| **R8** | *(new)* | **Platform checkpoint:** restructure on Material, stay Zensical-portable, and decide before May 2027. | Material is in its final maintenance period. MkDocs 2.0 drops plugins. |
| **R9** | *(new)* | **Validate with readers.** Run a 3–5 person observed round on the new front door, and add cookie-less Cloudflare Web Analytics. | Nobody knows which pages visitors read. Label choices need observation, not opinion. |

---

## 5. Where the researchers disagreed, and how each question was resolved

| Question | Positions | Resolution |
| --- | --- | --- |
| **Top-level labels** | Pure Diátaxis labels (`gem`). Diátaxis labels plus Concepts (`mus`). User labels (`cdx`, `cld`, `grk`). | **User labels:** Get started · Guides · Concepts · Reference. Diátaxis governs the writing, not the vocabulary. |
| **Where contributor material lives** | Under Reference → Internals (`cld`). A utility or footer link (`cdx`). Its own tab (`grk`, `mus`). | **Its own "Contribute" tab.** Today's heaviest readers are contributors (Bryan and agents). A separate tab keeps Reference lookups clean and signals to newcomers that they can stop. Six tabs is still under the ~8 that comparable sites use. |
| **Homepage model** | A three-persona triage including a "Systems architect" path (`gem`). One primary CTA plus doors (`cdx`, `cld`, `grk`, `mus`). | **One primary CTA** ("Run your first agent"), one secondary ("How SASE works"), and four doors. Persona paths route newcomers into internals and multiply decisions. Sequin's evidence favors quickstart-first. |
| **Subsystem hubs** | Hub-and-spoke portal per subsystem with a compass card (`gem`). Only where real content exists (`cdx`). | **Concept pages are the hubs.** Each ends with "Do it" (guides) and "Look it up" (reference) links. That keeps subsystem cohesion without a fifth page type or empty portals. |
| **How a page declares its type** | A `type:`/`audience:` frontmatter field (`grk`, `mus`, `gem`, `cdx`). Directory = type (`cld`). | **Directory = type.** It can't be mis-declared, a lint can check it, and a wrong placement shows in the diff. Frontmatter holds only `title`, `description`, and optionally `covers:` for reference pages. |
| **Size budgets** | Lines (`gem`). Words (`cld`, `grk`, `mus`). | **Words.** Lines mis-measure: `cli.md` is only 1,026 lines but about 26K tokens, because Prettier pads its tables. |
| **What ships first** | Process contract first (`grk`). Front door first (`cld`, `cdx`). Contract first (`mus`). | **Both, in Phase 0.** Each is small and independent, measured in days. |
| **Rewrite, rescue, or split in place** | New Guide files (`cld`). Rescue the existing tutorial (`grk`, `cdx`). Split mega-pages in place (`mus`). | **New files for the Guide, sourced from old pages. Move-only splits for the Reference.** New files avoid colliding with ~20 docs commits a day. |
| **Platform** | Keep Material with no replatform (`grk`, `mus`, `gem`, none of whom mention Material's end of life). Zensical as successor (`cdx`, `cld`). Starlight fallback (`cdx`). | **Material now, portable. Zensical trial after 0.1.0. Starlight only if that trial fails.** "Keep Material indefinitely" ignores the May 2027 end of life. |
| **The PDF** | Retire it (`cld`). Curate it (`grk`). Keep a full four-book manifest (`gem`). Keep it and decide separately (`cdx`). | **Curate to a Guide-tier handbook.** The full corpus is about to outgrow the asset cap, dominates deploy time, and blocks Zensical. It is flagged as Bryan's decision because he explicitly asked for the full PDF and reverted a shrink. |
| **Guide-tier size** | About 60K words and ~40 pages (`cld`). Unspecified elsewhere. | **Launch at about 30K words. 60K is a ceiling, not a target.** There is one human editor. |
| **Number of tutorials** | 2 (`cdx`) to 5 (`mus`, `gem`) | **Ship 2 tested tutorials.** Add a third (plan → epic) only after observing readers on the first two. |

Errors not carried forward:

- `gem`'s search claim (see §1).
- `gem`'s illustrative commands with invented model IDs (`claude-3-5-sonnet`).
- `gem`'s line-based budgets.
- `mus`'s "Concepts as a fifth bucket only if needed". Concepts is essential, because the
  vocabulary problem is real (the glossary has about 70 terms).

---

## 6. Recommended solution

### 6.1 The model: two tiers, six tabs

```text
sase.sh
├─ Home                          one screen: what · who for · install · demo · four doors
├─ Get started   (tutorials)     ┐
├─ Guides        (how-to)        ├─ THE GUIDE: curated, typed, budgeted, human-reviewed
├─ Concepts      (explanation)   ┘
├─ Reference     (reference)     ── THE REFERENCE: generated where it's a registry, split where it's prose
├─ Contribute    (contributor)   ── development, internals, contracts, runbooks, docs process
└─ Blog          (essays)        ── dated; links to maintained docs, never the only home of an instruction
```

- **The directory is the type:**
  - `docs/start/`, `docs/guides/`, `docs/concepts/`
  - `docs/reference/`
  - `docs/contribute/`
  - `docs/blog/`
- **Reader promises:**
  - The Guide never sends a newcomer into the Reference to finish a task.
  - The Reference never re-teaches. It links back to Guides and Concepts.

### 6.2 Target navigation

```yaml
nav:
  - Home: index.md
  - Get started:
      - start/index.md                  # Is SASE for you? alpha status, requirements, the two lessons
      - Install and set up a provider: start/install.md
      - Run your first agent: start/first-run.md        # tutorial 1, read-only, +home
      - Make and review a change: start/first-change.md # tutorial 2: edit → inspect diff → land
  - Guides:
      - guides/index.md                 # goal list: "an encouraging suggestion of capabilities"
      - Set up: [add an existing repository, choose providers and models, configure essentials, completion & editor]
      - Daily work: [run agents in parallel, review and land a change, hand a result to another agent,
                     reuse a prompt (macros), find and replay an old prompt]
      - Plan and automate: [plan a multi-agent change, schedule recurring work, get automated review]
      - Fix problems: [start with sase doctor, an agent is stuck QUEUED, recover an interrupted agent]
  - Concepts:
      - How SASE works: concepts/index.md   # one diagram, seven nouns, ~two screens
      - Agents, sessions, and workspaces: concepts/agents.md
      - Work units — Patches, beads, plans, goals: concepts/work-units.md
      - How changes land: concepts/landing.md
      - Prompts, macros, and workflows: concepts/prompts.md
      - Memory and agent instructions: concepts/memory.md
      - Automation and human checkpoints: concepts/automation.md
      - Providers and models: concepts/providers.md
  - Reference:
      - reference/index.md              # a routing index in the style of today's cli.md
      - CLI: reference/cli/             # generated, one page per command group
      - Configuration: reference/config/  # generated from sase.schema.json, one page per key family
      - TUI: reference/tui/             # one page per tab + generated keymap
      - Macro language: reference/macros/ # syntax; directives generated from the Rust contract
      - Workflow YAML, Query language, File formats, Environment variables
      - Providers and models: reference/providers.md   # existing generated tables
      - Glossary: reference/glossary.md               # generated from the glossary web
      - Upgrading and deprecations: reference/upgrading.md  # the ONLY home for history in the docs
  - Contribute:
      - contribute/index.md             # development, docs contract, architecture internals,
                                        # Rust boundary, pane contracts, perf/telemetry, fakey, runbooks
  - Blog: blog/index.md
```

The Guides list above is the **first wave** (about 15 pages), chosen because the
homepage and tutorials link to them. More guides arrive only when a real user goal
appears. The test is whether the title can start with a verb and name an outcome.

### 6.3 Homepage and site UX

**The homepage is one screen with one primary action.** Hide the sidebar and TOC on it
(`hide: [navigation, toc]`).

1. **Hero** (copy is a draft for Bryan's review):
   - Headline: **Run a team of coding agents. Keep every change reviewable.**
   - Subhead: SASE runs Claude Code, Codex, and other agent CLIs in parallel, isolated
     workspaces, and lets you track, review, and land their work from one terminal UI.
   - Status pill: *Alpha · Linux & macOS · needs one authenticated agent CLI*.
   - A copyable three-line install block (`uv tool install sase` · `sase doctor` ·
     `sase tui`). Ship this **only once R0 holds**.
   - **Primary CTA:** *Run your first agent (15 min)*. **Secondary:** *How SASE works*.
     GitHub moves to the header icon.
2. **One demo:** the existing, reproducible 25-second multi-model fan-out GIF from
   `demos/out/`. Provide a still and alt text, and don't force autoplay.
3. **Four capability cards:** parallel isolated runs · supervise from one TUI ·
   durable, reviewable work · reusable prompts and automation. Each card links to a
   **Concept** page, never to a 100K-word reference.
4. **"How these docs are organized": four doors,** each one line. Learn → Get started.
   Do → Guides. Understand → Concepts. Look up → Reference.
5. **Footer row:** launch essay · blog · handbook PDF · acknowledgements. PDF and
   launch-post links keep their URLs but stop competing with the first run.

**Site-wide** (all of this is available in Material 9.7):

- Turn on `navigation.tabs` plus `.sticky`, `navigation.path` (breadcrumbs),
  `navigation.footer` (previous/next, so tutorials read in sequence), `toc.follow`,
  `content.code.copy`, and `search.suggest` and `search.highlight` (already on).
- Keep `navigation.sections` *within* tabs. Each sidebar then shows only its own tab:
  about 15 items in Guides, about 8 in Concepts, instead of about 60.
- Check the mobile drawer separately. Desktop tabs don't redesign it.
- **Glossary tooltips:** generate an abbreviations include from the `glossary` web for
  about 15 core terms. Hovering "Patch" or "bead" in Guide text then shows the one-line
  definition. It is the cheapest fix for jargon load.
- **Page openings follow the template:**
  - one sentence saying what the page is for;
  - a "Before you start" line for tutorials and guides;
  - a closing "Next" link.
- **Title conventions:**
  - Guide titles are goals ("Get automated code review", not "Mentors").
  - Reference titles name the thing.
- **Search tuning:**
  - Boost `start/` and `concepts/` in search.
  - Measure the top ~20 queries before excluding anything.
  - Don't add a chat widget as a substitute for information architecture.

**How this makes the site more intuitive, by visitor:**

- **Evaluator:**
  - Reads one sentence, sees one demo, and knows the requirements and alpha status.
  - Clicks one button.
- **New user:**
  - Finishes a tested 15-minute lesson in `+home` with a run they can see.
  - Is offered one next lesson, not a 20-term component map.
  - With a real repository, opens *Guides → Add an existing repository*.
- **Daily user:**
  - Lives in the Guides and Reference tabs.
  - A config key is one generated section page, not a 7,768-line scroll.
  - Keymaps are one generated table.
- **Contributor or agent:**
  - Contributor material and contracts sit under Contribute.
  - The full spec stays in Reference, plus a generated docs map (§6.10).

The general rule: the label in front of you matches the need you have, and the page you
open doesn't change mode halfway through.

### 6.4 Tutorials and concepts

**Tutorial 1, Run your first agent:**

- **Budget:** about 900–1,500 words, capped at 2,500.
- **Steps:**
  1. Confirm the install and one authenticated provider, with recovery links.
  2. Launch a read-only run in the managed `+home` project, saying explicitly that this
     is SASE's demo workspace, not your current directory.
  3. Find the run in the TUI and identify its prompt, status, and result.
- **Finish:** "You have launched and inspected a SASE run." Offer two next choices.
- **Out of scope:** macro syntax, the glossary, artifact digest forms, dependency
  scheduling, autonomy policy, and provider-selection internals. Those belong in a guide
  or the reference, linked at the point of need.

**Tutorial 2, Make and review a change:**

- A small edit in the demo project, then inspect the diff.
- Explain what landing will commit or push **before** the step that triggers it.
- Describe workspace isolation accurately. A prompt asking an agent not to edit files is
  not an enforceable guarantee.

**Both tutorials are tested.**

- Marked shell blocks run in a temporary `HOME` against `fakey` in the scheduled
  Full-CI lane.
- Screenshots and GIFs regenerate from `demos/` tapes, never by hand.
- An occasional real-provider walkthrough covers what `fakey` can't: authentication and
  routing.
- This needs a short feasibility spike. The pieces exist (`fakey`, ~500 HOME-isolated
  tests, VHS tapes), but no tutorial runner exists yet.

**Concepts teach a small model first.** The glossary has about 70 terms. The Guide
teaches **seven nouns** before using any other: *project → workspace → agent →
prompt/macro → Patch → bead/plan → TUI*.

- Every other term (clan, tribe, hood, deck, stitch, chop, gate, monitor, ToolRun…)
  appears only on the page that needs it, linked to the generated glossary.
- `concepts/index.md` ("How SASE works") has exactly one diagram and fits on about two
  screens. The homepage's secondary CTA and every "why?" link point to it.

### 6.5 Where today's pages go

"→ G" means a new Guide page written using the old page as source. "→ R" means
Reference, split or generated. "→ C" means Contribute.

| Current page (words) | Disposition |
| --- | --- |
| `getting_started` (4.1K) | → G: `start/install`, `start/first-run`, `start/first-change`. Artifact handoff and macros → guides. Component map → `concepts/index`. **Delete the duplicate draft blog post** (it already redirects). |
| `index` | Rewritten (§6.3) |
| `ace` (103K) | → G: a TUI tour inside tutorial 1, plus daily-work guides. → R: one page per TUI tab plus a **generated** keymap. Pane contract and visual grammar → C. |
| `configuration` (71K) | → G: `guides/configure` (about 1.5K words). → R: **generated** from the schema, one page per key family. Prose only where the schema can't say it. Environment variables and CLI flags get their own reference pages. |
| `cli` (14.6K) | → R: keep its routing-index role. Add per-command-group pages generated from argparse. |
| `macros` (32K), `workflow_spec` | → G: `concepts/prompts` and `guides/reuse-a-prompt`. → R: syntax, **generated** directives, discovery order, workflow YAML. |
| `beads`, `sdd`, `goals`, `change_spec`, `project_spec` | → G: `concepts/work-units` and `guides/plan-a-change`. → R: lifecycles, formats, CLI. `sdd_storage` → C. |
| `llms` (27K), `agent_providers` | → G: `start/install`, `guides/providers`, `concepts/providers`. → R: the existing generated tables. Instruction-delivery internals → C. |
| `axe`, `monitors`, `tool`, `mentors`, `sudo`, `notifications` | → G: one goal-titled guide each, where a real goal exists. → R: the details. Epic-labeled sections → C. |
| `memory`, `memory_history`, `instruction_bundles` | → G: `concepts/memory` and a guide. → R: formats. Manifest internals → C. |
| `agent_sessions`, `workspace`, `vcs`, `commit_workflows`, `agents_sidecar` | → G: `concepts/agents` and `concepts/landing`. → C: provider APIs, orchestrator, sync. |
| `init`, `content_layout` | → G: `guides/add-a-repository`. Migration → `reference/upgrading`. |
| `instruction_inventory` | **Remove from the site.** It is a historical epic artifact, so move it to the repo's `sdd/` area. |
| `troubleshooting/*`, `agent_auto_restart` | → G "Fix problems". `agent_auto_restart` is linked from the homepage but missing from the nav today. |
| `development`, `rust_backend`, `fakey`, `telemetry`, `perf_runbook`, `mobile_mvp_runbook`, `integrations`, `artifacts_pane_*` | → C |
| `mobile_gateway`, `remote_dispatch`, `editor`, `completion`, `plugins` | → G: one goal-titled guide each. API details → C. |
| `query_language`, `agent_images`, `pager`, `prompt`, `artifact_references`, `artifact_links` | → R, plus a guide where there is a real task |

Don't split every heading into a page. A good boundary is a complete task, a coherent
concept, or one reference family. Keep a working page intact if splitting would make its
task harder to follow.

### 6.6 The documentation process contract

This is the "more structure" half of the request. All of it is mechanical, runs as a
fast `tools/check_docs` in `just check`, and is documented in a short
*Contribute → Writing docs* page.

1. **Typing.** The directory decides the type. Every page needs a one-line
   `description:` in its frontmatter, which also feeds meta tags, `llms.txt`, and the
   docs map. Reference pages may declare `covers:` (code globs) for the gardener later.
2. **Templates** in `docs/_templates/` (excluded from the build):

   | Template | Shape |
   | --- | --- |
   | Tutorial | Goal sentence · prerequisites · numbered steps, each ending in a visible result · "What you did" · Next. No options, no alternatives, no "why". |
   | How-to | Goal title · "Before you start" · steps · verification · at most 3 variations · related links |
   | Concept | "About X" · the problem · the model (one diagram allowed) · trade-offs · "Do it / Look it up" links (this makes it the subsystem hub) |
   | Reference | Mirrors the product unit · scope and version · consistent tables · defaults · examples · no narrative |
   | Hub | One orientation sentence · grouped links · stop |

3. **Word budgets with a ratchet.** A page over budget may not grow, and new pages must
   fit. Pre-existing monoliths sit on an allowlist that only shrinks.

   | Tier | Per page | Notes |
   | --- | --- | --- |
   | `start/` | ≤ 2,500 | Tier total ≤ 10K |
   | `guides/` | target ≤ 1,500, hard 2,500 | Anything longer is two guides |
   | `concepts/` | ≤ 3,000 | Tier total ≤ 25K |
   | Hubs | ≤ 400 | |
   | `reference/` (hand-written) | ≤ 6,000 | Generated pages are exempt |
   | `contribute/` | ≤ 8,000 | Warn only |

4. **Guide hygiene lint** (`start/`, `guides/`, `concepts/` only):
   - no bead IDs, `src/` paths, or epic or phase labels;
   - no history phrases ("formerly", "no longer", "legacy", "renamed", "still
     mentions"). History goes to the CHANGELOG, decision records, and the single
     `reference/upgrading.md`.
5. **Validation:**
   - Add MkDocs `validation:` (`omitted_files`, `anchors`, `unrecognized_links`,
     `absolute_links` set to `warn`, which `strict` turns into failures) and
     `exclude_docs` for templates and includes.
   - Run `just docs-check` in Master Gate whenever `docs/` or `mkdocs.yml` changes. It
     takes about 8 seconds.
6. **URL contract test (new).** Every `https://sase.sh/...` URL in `src/`, the README,
   and `_redirects` must resolve in the built site, including anchors. This would have
   caught the two 404 TUI links. When content moves:
   - record each source path and anchor before extracting it;
   - use anchor-aware redirects or keep small compatibility stubs, because the fragment
     never reaches the server;
   - never redirect a deep link to a generic section index and call it compatible.
7. **Generated registries.** Extend the `render_model_docs` `BEGIN GENERATED` /
   `--check` pattern into one renderer. Generate **tables, not chapters**: hand-written
   reference prose stays where a schema can't say it.

   | Registry | Source | Replaces |
   | --- | --- | --- |
   | CLI | The argparse tree (already snapshotted by `tools/sync_completion_spec`) | `cli.md`'s hand tables and stale caveats |
   | Config | `sase.schema.json` (1,239 nodes, 71% described) | Most of `configuration.md` |
   | TUI keymap | `default_config.yml` `keymaps:` | About 475 hand-written rows in `ace.md` |
   | Directives and macro discovery order | The Rust `directive_contract` and the macro-source resolver | Drifted hand tables |
   | Glossary and design principles | The `glossary` and `decisions` memory webs | New, read-only pages |
   | Models and providers | `tools/render_model_docs` (existing) | — |

8. **Change → docs routing rule**, delivered to agents as a reference-memory trigger. The
   memory change goes through `/sase_memory_write`.

   | You changed… | Docs action |
   | --- | --- |
   | A CLI flag, config key, keybinding, directive, or model | Regenerate. Write no prose unless the generated description is insufficient. |
   | The behavior of an existing feature | Update its `reference/` page. If a tutorial or guide step is now wrong, fix that step and nothing more. |
   | A new user-visible capability | Add a reference entry. If it serves a new user goal, file a "guide candidate" follow-up. **Never append narrative to a Guide page.** |
   | A design decision | Write a decision record. It appears on the generated principles page. |
   | Internals, contracts, or runbooks | `contribute/` |

9. **Prose pins.** About 30 test files read `docs/*.md` prose (`macros.md` alone is
   pinned 25 times). Move those pins to generated blocks or reference pages. New tests
   may not pin Guide-tier prose.
10. **Constrain `refresh_docs`.** Its prompts name the page type and forbid adding a
    second mode. It may propose splits when a page is over budget. It may not edit the
    Guide tier beyond fixing a broken step, and it may never move pages between tabs.
    Information architecture is a human decision.

### 6.7 Applicability and release alignment

- **Now:**
  - Publish 0.18.0 (`sase-16p`, PR #299).
  - Add a small version line to the site header, for example "Docs track `master`.
    Latest release: vX.Y". Make sure the tutorial's install step installs a version
    that has the commands it uses.
- **Process:** the scheduled lane runs a clean PyPI install and the first tutorial
  commands. It fails when the installable product and the docs disagree.
- **Later, when external users exist and releases are regular:** consider building
  sase.sh from release tags and putting `master` docs on a preview URL.
  - Agents read `docs/` from the checkout, not the site, so this wouldn't hurt them.
  - It isn't recommended now: releases are blocked on Full CI, and the redesign would
    stay invisible until the next release.
- **Don't** build a multi-version docs archive yet.

### 6.8 The PDF handbook: decide now

| Option | Verdict |
| --- | --- |
| Keep the full-corpus PDF | **Not sustainable.** It is already at 1,151 pages, breached the gate in September, likely re-breaches by about December, takes ~8 min of every deploy, and has no Zensical path. |
| Retire it (`cld`) | Clean, but it contradicts the explicit May request and the reverted shrink. |
| **Curate a Guide-tier handbook** (`grk`) | **Recommended.** Get started, Concepts, Guides, and the launch essay, roughly 150–250 pages. Same URL. The Reference stays web-only. Builds in a fraction of today's time. |
| Four-book manifest including the full Reference (`gem`) | Keeps the size problem. Rejected. |

At the Zensical decision, either produce the curated PDF with a standalone step (a
headless-browser print over the built HTML, which is what `mkdocs-exporter` does
internally) or retire it then. This is **flagged for Bryan's decision**.

### 6.9 Platform

- **Now:** restructure on Material 9.7.
  - Add **no** new Python `hooks:`, `gen-files`, or custom plugins (Zensical doesn't
    support `gen-files`).
  - Do generation in `tools/` **before** the build, as `render_model_docs` already does.
  - Keep `overrides/main.html` simple.
- **After Zensical 0.1.0 (planned Nov 5, 2026), and decided by about February 2027:**
  1. Trial `zensical build` against the restructured repo.
  2. Verify blog, RSS, redirects (including anchor redirects), the `custom_dir` override,
     search quality, and mobile navigation.
  3. Turn on the built-in `llmstxt` and "Copy as Markdown".
  4. Switch once priority journeys and URLs behave the same.
- **Fallback:** if the trial finds durable blockers, evaluate Astro Starlight against
  the same acceptance cases. Don't start there. A JS stack adds Node ownership and
  conversion work, and nothing in this plan needs it.
- **Reject:** hosted docs platforms and a custom docs engine. Neither solves the actual
  problem, which is page purpose and accretion.

### 6.10 Agents as readers, and long-term agentic maintenance (brief, by request)

Agents are the heaviest readers today. Serve them cheaply, without building a second
docs tree.

- **A generated docs map** (`docs/README.md`, and `llms.txt` on the site) lists every
  page by tab with its `description`. Ship it via the `mkdocs-llmstxt` plugin now, or
  Zensical's built-in plugin later.
- **When files move,** update the plain-text `docs/…` pointers in memory notes and the
  in-product links through `/sase_memory_write` and the URL contract test. Agents that
  grep `docs/` keep working.
- **Two editing regimes:**
  - Feature agents own the **Reference**: they regenerate and update `covers`-matched
    pages.
  - The **Guide** is curated. New Guide content arrives through an explicit docs task
    or plan.
  - The budget lint enforces this mechanically.
- **Later:**
  - A weekly docs-editor routine reads the CHANGELOG, tutorial-test results, and the
    guide-candidate backlog, then **proposes a plan for human approval**.
  - Code/docs disagreements found while writing become `bug` beads, not sentences in the
    docs.
  - Build nothing more (no docs knowledge graph, retrieval layer, or support bot) until
    the corpus and routes work.

### 6.11 Migration plan

Each phase ships on its own and pays off independently.

| Phase | Scope | Collision risk | Exit criteria |
| --- | --- | --- | --- |
| **0. Prerequisites and quick wins** (days) | **R0:** publish 0.18.0, PyPI install smoke, version line. **Front door:** tabs, breadcrumbs, copy buttons; regroup the **existing** pages into the six tabs **without moving files** (legacy pages under Reference, internals under Contribute); rewrite the homepage; drop *Instruction Inventory* from the nav. **Contract:** validation block, docs-check in Master Gate, URL contract test (fix `/macro/` and `/patch/`), templates, budget lint with a legacy allowlist, Web Analytics. **Decide** the PDF scope. | Low: only `mkdocs.yml`, `index.md`, and tooling change | `uv tool install sase` installs the documented version. No sidebar shows more than ~30 items. Install and demo are above the fold. Strict build validates anchors and omitted files. |
| **1. Write the Guide** (new files) | `start/` (install plus 2 tutorials), `concepts/` (~8), the first ~15 guides, glossary tooltips, tutorial tests on `fakey`. Observe 3–5 newcomers and tune the labels. | None: new files | Guide ≈ 30K words and every page within budget. Tutorial tests green. At least 4 of 5 observed readers pick the right route for a named task. |
| **2. Generate registries** | CLI, config, keymap, directives, glossary, principles. Delete the hand tables they replace. Re-point prose pins. Install the agent routing rule. | Medium: these touch hot pages, so land one registry per quick commit | No hand-maintained registry tables remain. |
| **3. Decompose the monoliths** | Largest and most-read first: `ace` → `configuration` → `macros` → `beads` → `llms` → `notifications` → `axe`. Move-only commit, then redirects and anchor stubs, then content commits, scheduled in a low-agent window. Strip history into `upgrading.md` and the CHANGELOG. | Medium, mitigated by move-only commits and the routing rule | No `reference/` page over budget. Zero history phrases in the Guide. The legacy allowlist is empty. |
| **4. Platform** | Zensical trial after 0.1.0. Execute the PDF decision. `llms.txt`. | Low | Site builds on Zensical with blog, RSS, and redirects intact, before 2027-05-05 |
| **5. Maintenance loop** | Constrained `refresh_docs`, guide-candidate backlog, periodic docs-editor plan | — | Hand-written monthly growth ≤ 5% |

**Phase 0 fixes most of the first impression. Phases 0 and 1 together deliver the
"simple and intuitive" site. Phases 2 and 3 shrink and stabilize what's behind it.**

### 6.12 Success metrics

| Metric | Today | Target |
| --- | --- | --- |
| `uv tool install sase` installs the documented version | **No (installs 0.1.0)** | Yes, checked on a schedule |
| Homepage primary choices | 4 buttons + 16 cards | 1 primary CTA + 1 secondary + 4 doors |
| Sidebar items on any page | ~60 | ≤ 30 in Guides, ≤ 10 elsewhere |
| Guide-tier words | ~4K of real tutorial | ~30K at launch, ≤ 60K ceiling, every page within budget |
| Hand-written monthly growth | +37% | ≤ +5% |
| Tutorial reliability | Untested | Green in Full CI, plus a periodic real-provider walkthrough |
| History phrases, bead IDs, `src/` paths in the Guide | 741 / 148 / 382 across the corpus | 0 in the Guide |
| Hand-maintained registry tables | CLI, config, keymaps, directives | 0 |
| Broken sase.sh URLs in code and README | 2 known | 0, enforced |
| PDF | 1,151 pp, 13.9 MiB, ~8 min per deploy | Curated (or retired), well under the gate |
| Reader evidence | None | Observed-round results, plus analytics for entry pages, tutorial completion, and search terms |

### 6.13 What not to do

- Don't rewrite the 518K-word corpus top-down, and don't create empty Diátaxis folders.
- Don't delete reference detail agents rely on. Move it, generate it, or split it.
- Don't let feature agents append narrative to Guide pages. That is the accretion engine.
- Don't keep history in user-facing pages.
- Don't launch the new front door while `uv tool install sase` installs 0.1.0.
- Don't add Material-only hooks or plugins during the restructure. Don't switch to a JS
  framework, and don't add an AI answer box in place of information architecture.
- Don't put a docs map into always-loaded agent instructions without measuring its token
  cost.

### 6.14 Risks, and what would change this recommendation

- **Tabs feel abstract to users.** Keep the editorial types but test plainer door labels.
  The observed round decides.
- **Too many tiny pages.** Merge pages that readers keep flipping between. Split by
  complete task, concept, or reference family, never by individual flag.
- **Duplicate truth during migration.** When a Guide page is written from a legacy
  passage, replace that passage with a link in the same change. Extract; don't copy.
- **One human editor.** That is the reason for the 30K-word launch size and plan-gated
  Guide edits. Grow the Guide only as reviewing capacity allows.
- **The Reference still dominates search after generation.** Then reconsider a separate
  reference site, an option deferred today.
- **The Zensical trial fails.** Stay on Material until close to May 2027, then evaluate
  Starlight against the same acceptance cases.

---

## Recommended solution

**Make sase.sh a small, Diátaxis-typed Guide in front of a generated, split Reference,
and put a working install ahead of both.**

1. **First, make step 1 true.** Publish 0.18.0 so `uv tool install sase` installs the
   product the docs describe. Add a version line and a scheduled PyPI install smoke.
2. **Adopt the two-tier model with six user-labelled tabs:** Get started · Guides ·
   Concepts · Reference · Contribute · Blog. The directory is the type. Concept pages act
   as subsystem hubs.
3. **Ship Phase 0 this week:**
   - tabs, plus the existing pages regrouped without file moves;
   - a one-screen homepage with one primary CTA, install, a demo, and four doors;
   - validation and the URL contract test (fixing the two 404 links);
   - docs-check in Master Gate, templates, and budget lint;
   - a decision on the PDF scope (curation recommended; Bryan's call).
4. **Write the Guide as new files:** two tested tutorials, about eight concepts, and
   about 15 goal-titled guides, launching near 30K words. Tune the labels with 3–5
   observed newcomers.
5. **Generate the registries, then decompose the monoliths one page at a time,** using
   move-only commits, redirects, and anchor stubs.
6. **Enforce the contract in `just check`.** Budgets with a ratchet, Guide hygiene,
   present-tense Guide text, and the change→docs routing rule keep the site from
   regrowing at +37% a month.
7. **Move to Zensical after 0.1.0 and before Material's May 2027 end of life,** picking
   up `llms.txt` and Copy-as-Markdown. Use Starlight only if the trial fails.

This uses Diátaxis the way Diátaxis asks to be used: as a compass applied to real pages,
with a destination those pages can grow into. It gives newcomers one walked path, gives
daily users scoped lookups, and keeps the full spec that agents and Bryan rely on, now
generated instead of hand-accreted.

---

## Sources

**Diátaxis:** <https://diataxis.fr/> ·
[Start here](https://diataxis.fr/start-here/) · [Compass](https://diataxis.fr/compass/) ·
[Workflow](https://diataxis.fr/how-to-use-diataxis/) ·
[Tutorials](https://diataxis.fr/tutorials/) ·
[How-to guides](https://diataxis.fr/how-to-guides/) ·
[Reference](https://diataxis.fr/reference/) ·
[Explanation](https://diataxis.fr/explanation/) ·
[Quality](https://diataxis.fr/quality/)

**Case studies and precedents:**

- [Sequin: We fixed our documentation with Diátaxis](https://blog.sequinstream.com/we-fixed-our-documentation-with-the-diataxis-framework/)
- [Canonical: Diátaxis, a new foundation](https://ubuntu.com/blog/diataxis-a-new-foundation-for-canonical-documentation)
- [uv docs](https://docs.astral.sh/uv/) · [Django docs](https://docs.djangoproject.com/en/stable/) · [Kubernetes docs home](https://kubernetes.io/docs/home/) · [Click](https://click.palletsprojects.com/en/stable/)
- [Azion: navigation hubs](https://www.azion.com/en/documentation/style-guide/content/navigation-hubs/)
- [NN/g: progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/)
- [Google Technical Writing: audience](https://developers.google.com/tech-writing/one/audience)
- [llmstxt.org](https://llmstxt.org/)

**Platform** (verified 2026-10-15):

- [Material issue #8523 (end of life May 5, 2027)](https://github.com/squidfunk/mkdocs-material/issues/8523)
- [Material navigation setup](https://squidfunk.github.io/mkdocs-material/setup/setting-up-navigation/)
- [What MkDocs 2.0 means](https://squidfunk.github.io/mkdocs-material/blog/2026/02/18/mkdocs-2.0/)
- [Zensical upcoming changes](https://zensical.org/upcoming-changes/) · [Zensical plugin compatibility](https://zensical.org/docs/compatibility/mkdocs/plugins/) · [Zensical migration guide](https://zensical.org/docs/compatibility/mkdocs/migration/) · [Zensical roadmap](https://zensical.org/roadmap/) · [zensical on PyPI](https://pypi.org/project/zensical/)
- [Astro Starlight](https://starlight.astro.build/)

**Local evidence** (sase `bc4bc3e183`):

- `mkdocs.yml`, `mkdocs-pdf.yml`, `docs/**`, `docs/_redirects`
- `.github/workflows/{docs-deploy,master-gate}.yml`, `Justfile`
- `tools/{render_model_docs,sync_completion_spec,validate_docs_pdf,postprocess_docs_pdf}`
- `src/sase/scripts/sase_chop_refresh_docs.py`, `src/sase/config/sase.schema.json`, `src/sase/default_config.yml`
- `src/sase/ace/tui/widgets/{agent_onboarding,patch_onboarding}.py`
- `README.md`, `demos/`
- Git history (word counts at seven dates; commit-type and per-page churn over 30 days)
- Commits `c87c9d1aa9`, `3bb3cb9e26`, `883f31afc4`, `4fc9e7ae49`

**Live and remote checks** (2026-10-15):

- `curl` of `sase.sh` pages, the search index, `/llms.txt` (404), `/macro/` and `/patch/` (404), and the handbook PDF (`pdfinfo`: 1,151 pages)
- Docs-deploy run logs 38765248774 and 35164543094 (PDF size and step timings)
- `gh api` repository stats and traffic
- PyPI JSON for `sase` and `sase-core-rs`, and `uv pip compile` resolution of `sase`
- Bead `sase-16p`

**Earlier SASE research:**

- `research:202605/sase_sh_site_design_research.md`
- `research:202605/sase_sh_single_pdf_download.md`
- `research:202610/docs_backed_memory_and_agent_maintained_docs/docs_backed_memory_and_agent_maintained_docs__final.md`
- `research:202610/sase_v0_18_0_pypi_release_status.md`
