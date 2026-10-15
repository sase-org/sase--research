# sase.sh documentation: Diátaxis structure, site UX, and process

> **Research query:** How should SASE drastically simplify the public documentation on sase.sh, make it more intuitive for people trying to learn the product, and add structure to the documentation process? Use [Diátaxis](https://diataxis.fr) for inspiration. Long-term agentic management of the docs should be considered, but the report should decide the best documentation solution, structure, and sase.sh UX. Critique the plan. Call out justified requirement changes. End with a recommended solution.

**Researcher:** grk (independent swarm member)
**Date:** 2026-10-15
**Scope:** public docs site (`docs/`, `mkdocs.yml`, sase.sh), documentation process, and the UX of learning SASE. Agentic maintenance is a constraint on that process, not the design center.

---

## Bottom line

The goal is right. The current public site is hard to learn from, and the documentation process is too weak to stop it from getting worse. Diátaxis is the right inspiration.

The method implied by “drastically simplify by imposing Diátaxis” is the wrong method. Diátaxis itself says not to create four empty Tutorials / How-to / Reference / Explanation sections and pour the existing corpus into them. That is how you get a prettier mess.

**Do this instead:**

1. Treat Diátaxis as a **page-type taxonomy and writing standard**, not as a four-folder rewrite.
2. Present the site in **user language that maps onto those types**: Start, Guides, Concepts, Reference, Contribute, Blog.
3. **Rescue the on-ramp and split the mega-pages** before rewriting everything else.
4. Add **process structure first** (type, size, generated-vs-authored, templates, CI). Without that, the existing `refresh_docs` job will keep growing mixed-mode encyclopedias.
5. Keep MkDocs Material. Do not change the site generator.
6. Serve **two corpora**: a human site on sase.sh, and a machine-readable `/llms.txt` (plus a generated full dump) for agents. Stop writing every public page as if it must be complete for an agent that might see only that page.

The plan is a good idea once those adjustments are accepted. A big-bang content rewrite is not.

---

## 1. Critique of the plan

### What the plan gets right

Simplifying sase.sh and adding process structure belong together. The site is already a MkDocs Material project with a custom home, a PDF handbook pipeline, Cloudflare deploy, and a blog. The failure is information architecture and page mode, not tooling.

Diátaxis is the correct inspiration. SASE’s current nav is a **difficulty ladder** (`Getting Started` → `The Basics` → `Beyond the Basics` → `The Nitty Gritty` → `Integrations` → `Reference`). Diátaxis exists to replace that kind of ladder. Users do not arrive “ready for the nitty gritty.” They arrive with a need: learn, do a job, look up a fact, or understand why.

The home page already gropes toward a better model with “Start by role” cards. The sidebar then dumps the learner into a 57-leaf encyclopedia. Home and nav disagree.

### Where the plan is dangerous

**“Drastically simplify” and “add Diátaxis structure” pull in opposite directions if you treat structure as a rewrite.** The live docs tree is about 540,000 words of Markdown. Eight pages hold 58% of that. `docs/ace.md` alone is about 103,000 words; `docs/configuration.md` is about 71,000. You cannot simplify that corpus by rearranging nav titles. You simplify the **entry**, the **nav**, and the **page contract**, then split and retarget content.

**Diátaxis forbids the most tempting implementation.** From [Diátaxis as a guide to work](https://diataxis.fr/how-to-use-diataxis/):

- Use it as a guide, not a plan you must complete.
- Do not spend energy getting the top-level structure “correct” first.
- Do **not** create empty tutorials / how-to / reference / explanation structures. “Don’t do that. It’s horrible.”
- Structure should emerge from well-formed pages. Work one step at a time. Publish each improvement.
- Documentation can always be complete without being finished.

A SASE-shaped exception applies: some pages are so large that sentence-level iteration never finishes. Those pages need **planned splits**. That is still not a four-section greenfield.

**The public site has two audiences, and the current corpus optimizes for the wrong one.** SASE is a human product and an agent-facing coordination layer. Many pages read as if an agent might be handed a single URL and must find every flag, keymap, and caveat there. That produces functional completeness and destroys deep quality: flow, fit to a human need, a feeling of being anticipated ([Diátaxis on quality](https://diataxis.fr/quality/)). Humans bounce. Agents still cannot use a 9,700-line TUI dump well.

**Agentic management must not be the author of information architecture.** SASE already has `sase_job_refresh_docs`: an update proposal plus a polish proposal, scoped to documentation files, triggered by commit drift. The default prompts ask for accuracy, completeness, and clarity for someone new. They do **not** ask which user need a page serves. Unconstrained, that job will keep stuffing explanation into tutorials and flags into how-tos. Process structure has to bind the agents, not the other way around.

**The PDF handbook is not a user product in its current form.** The hero offers “Download PDF” as a peer of Getting Started. The PDF is a strict build of the whole site. Shipping the encyclopedia as a book does not make the encyclopedia easier.

### Is this a good idea?

Yes, with a method change.

I would take a different approach than a Diátaxis-labeled site rebuild. I would:

- keep the generator and the URL space;
- introduce page types and budgets immediately;
- retitle and tab the nav around user needs;
- make Getting Started a real lesson;
- split the five or six mega-pages;
- generate the true reference surfaces from source of truth;
- rewrite the home as a hub with one primary action.

That is still a large program. It is a sequenced one, and every phase can ship.

---

## 2. Adjustments to the requirements

These are justified changes to the request. Each is a requirement change, not a restatement.

1. **Do not require a four-section Diátaxis nav labeled Tutorials / How-to / Reference / Explanation.** Use user-facing labels that map onto those types. Click, Django, and Kubernetes all do this. Learners do not think in quadrants.

2. **Do not require a rewrite of the site generator.** Stay on MkDocs Material. The custom home CSS, PDF exporter, redirects, RSS, and Cloudflare deploy already work. Changing SSG is a year of work with no learning benefit.

3. **Treat “simplify” as simplify the path, not delete the knowledge.** Archive internal epic pages out of the public on-ramp. Split mega-pages. Keep the facts in reference. Do not start by deleting `configuration.md`.

4. **Put process structure ahead of the visible IA change, by a small amount.** Taxonomy, templates, size budgets, and generated-block rules can land without moving files. They make every later split and every `refresh_docs` run safer.

5. **Split the human site from the agent corpus.** sase.sh is for people. Add `/llms.txt` (and a generated full dump) for agents. Stop requiring every human page to be a complete agent briefing.

6. **Do not make long-term agentic management the keystone.** Keep `refresh_docs`. Constrain it by page type. Use agents for drift, classification, split proposals, and generated reference. Humans own IA, tutorial narrative, explanation, and home copy.

7. **Cap the first user-visible milestone.** The first public win is: a true 15-minute tutorial, a tabbed nav that no longer puts Instruction Inventory under Getting Started, and a home with one primary CTA. Mega-page splits can follow immediately; they should not block that win.

8. **Retire or curate the whole-site PDF as a hero action.** A handbook of Start + selected Concepts is useful. A 540,000-word PDF is a build artifact.

---

## 3. What sase.sh is today

Evidence is from the in-repo `docs/` tree, `mkdocs.yml`, `Justfile`, `tools/render_model_docs`, `src/sase/scripts/sase_chop_refresh_docs.py`, and the live home at [https://sase.sh](https://sase.sh).

### Generator and process that already exist

| Piece | What it does |
| --- | --- |
| MkDocs Material | Strict build, sections (not tabs), search suggest, blog + RSS |
| `just docs-check` | `mkdocs build --strict` |
| `just docs-pdf-check` | Whole-site PDF handbook via mkdocs-exporter |
| `just fmt-docs` | Regenerates model-catalog blocks in `docs/llms.md` from `models.yml` |
| GitHub `docs-deploy.yml` | Prebuilds `site/` and deploys through Wrangler |
| `refresh_docs` chop | Update + polish agent proposals, docs-files only |
| Redirects | `/xprompt/` → `/macros/`, draft 15-minute blog → `/getting_started/` |

This is a serious docs-as-code setup. The missing piece is a **content contract**. There is no page-type frontmatter, no size budget, no style guide for mode, and almost no generated reference beyond the model tables in `llms.md`. `docs/configuration.md` is a 7,768-line hand-maintained mirror of `src/sase/default_config.yml` (2,344 lines of YAML) plus CLI flags and env vars.

### The nav is a difficulty ladder with category errors

Current top-level groups from `mkdocs.yml`:

- **Getting Started** includes Your First 15 Minutes, Initialization, Content Layout Migration, Agent Providers, **Instruction Inventory**, and Instruction Bundles.
- **The Basics** includes Memory, Memory History, the entire TUI guide, Artifacts Pane Contract, Artifacts Visual Grammar, Axe, SDD, SDD Storage, Macros, Artifact References, Artifact Links, Pager, Prompt History.
- **Beyond the Basics** includes Architecture, Patches, Beads, Goals, Workflows, Agent Sessions, Agent Hood Synchronization, Monitors, Named Tools, Workspaces, Mentors.
- **The Nitty Gritty** is a junk drawer: commit workflows, notifications, sudo, mobile, remote dispatch, perf runbook, telemetry, revival log.
- **Integrations** mixes editor UX with fakey, rust backend, and the 27,000-word LLM provider page.
- **Reference** mixes CLI, configuration, query language, ProjectSpec, agent attachments, development, and acknowledgements.

Instruction Inventory is a historical epic artifact (“begun on 2026-10-06… E3 acceptance”). It tells a new user about `migrate` / `projection` dispositions and E1–E5. It does not belong on the public on-ramp. Artifacts Pane Contract and Visual Grammar are TUI implementation contracts. Fakey is a testing provider. Content Layout Migration is a compatibility how-to. All of these currently sit where a learner looks first.

That is a process failure visible in the IA: internal work was published into the nearest nav slot.

### Page size is the UX

Approximate word counts (in-repo `wc -w`):

| Page | Words | Lines |
| --- | ---: | ---: |
| `ace.md` (TUI) | 103,267 | 9,771 |
| `configuration.md` | 70,562 | 7,768 |
| `macros.md` | 32,179 | 4,083 |
| `beads.md` | 27,951 | 3,046 |
| `llms.md` | 26,773 | 3,582 |
| `notifications.md` | 18,523 | 2,037 |
| `axe.md` | 16,923 | 1,884 |
| `cli.md` | 14,614 | 1,026 |
| `development.md` | 12,868 | 1,407 |
| `getting_started.md` | 4,145 | 488 |
| `goals.md` | 731 | 96 |
| `architecture.md` | 3,031 | 298 |

`ace.md` plus `configuration.md` are one third of the public Markdown. The top eight pages are 58%. The right-hand TOC on those pages is longer than the left nav on a healthy site.

`goals.md` shows the opposite: a short, focused page a person can finish. That is the length target for how-to and concept pages.

### Getting Started is a tutorial that lost its nerve

`docs/getting_started.md` is titled “Your First 15 Minutes” and has the right bones: install, doctor, a read-only `sase run`, open the TUI, a tiny edit, artifact handoff, reuse a prompt as a macro, a taste of SDD. That is a lesson.

Then the lesson is interrupted:

- Step 4 is a TUI keybinding and prompt-overlay reference (Stash, Trash, `[` / `]`, `,.`, `Ctrl+K`, current-project chip).
- Step 5 explains stitches, Patches, `#propose`, project tags, `sase project add/create`, Admin Center.
- Step 8 walks autonomy profiles and nested epic workers.
- “The Component Map” is a 20-item glossary.
- “What To Read Next” leads with Instruction Bundles.

A tutorial’s job is a successful learning experience in a safe setting ([Diátaxis tutorials](https://diataxis.fr/tutorials/); [tutorials vs how-to](https://diataxis.fr/tutorials-how-to/)). The instructor is absent, so the path must stay on rails. The current page asks the student to also study the machinery. Sequin’s Diátaxis rewrite found the same failure: their first page used to be “How Sequin works,” and users did not get it until they used the product ([Sequin, 2024](https://blog.sequinstream.com/we-fixed-our-documentation-with-the-diataxis-framework/)).

There is also a **draft blog post** (`docs/blog/posts/hello-sase-your-first-15-minutes.md`) that duplicates the tutorial. `_redirects` already sends the blog URL to `/getting_started/`. Two sources for one lesson is how they drift.

### Home UX: a directory, not an on-ramp

The live home ([https://sase.sh](https://sase.sh)) is a custom Material landing page with:

- a four-button hero: Getting Started, Download PDF, View on GitHub, Launch Post;
- eight “Start by role” cards (init, TUI, SDD, Goals, memory, macros, architecture, editor);
- a primitives list;
- a component diagram;
- nine “Next clicks” cards, several of which repeat the role cards (TUI, architecture) or jump to recovery (`agent_auto_restart`).

That is 17 destinations before the person has a mental model. The README already states alpha status, POSIX-only, and “coordination layer, not a standalone agent.” The home does not. The first human question — “what do I do in the next 15 minutes?” — competes with PDF, GitHub, the launch essay, and eight role cards.

Role cards are a good **Guides hub** pattern. They are a weak **home** pattern. Kubernetes’s docs home does the better version: six buckets (Understand, Try, Set up, Tasks, Reference, Contribute), each with a handful of links and one “view all” ([kubernetes.io/docs/home](https://kubernetes.io/docs/home/)).

Material is currently using `navigation.sections` and `navigation.indexes` **without** `navigation.tabs`. Every group is visible in one sidebar. Tabs would scope the sidebar to one mode. The theme already supports this; it is a config change plus hub `index.md` pages.

### Dual writing modes on almost every large page

Using the Diátaxis compass (action vs cognition × study vs work):

| Page | Dominant need | What leaked in |
| --- | --- | --- |
| `getting_started.md` | Tutorial (action + study) | TUI reference, glossary, SDD policy |
| `init.md` (7,608 words) | How-to | Flag tables and compatibility |
| `ace.md` | How-to + reference mashed | Launch options, every tab, every keymap |
| `architecture.md` | Explanation | A 10-step launch implementation walkthrough |
| `cli.md` | Reference index (good intent) | Workflow advice in table cells |
| `macros.md` | Mixed how-to and reference | A 32k-word “one page” |
| `instruction_inventory.md` | Internal epic note | Published as Getting Started |

The CLI page is one of the few that already knows what it is: “a command index… discovery and routing… not a dump of every flag.” That sentence should be the model for reference hubs.

---

## 4. What Diátaxis actually recommends

The four types, from [Start here](https://diataxis.fr/start-here/) and [the map](https://diataxis.fr/map/):

| Type | User question | User is | Form |
| --- | --- | --- | --- |
| Tutorial | “Can you teach me to…?” | At study, doing | A lesson on rails |
| How-to | “How do I…?” | At work, doing | Directions to a real goal |
| Reference | “What is…?” | At work, looking up | Dry description of the machinery |
| Explanation | “Why…?” | At study, thinking | Discussion, context, opinion |

The compass:

- action + acquisition → tutorial
- action + application → how-to
- cognition + application → reference
- cognition + acquisition → explanation

Important consequences for SASE:

- A tutorial can be advanced (an experienced user learning monitors). A how-to can be basic (`sase completion install`). The split is study vs work, not beginner vs expert.
- Reference architecture should follow the machinery: commands, config keys, TUI tabs, query syntax. Gaps become visible.
- Explanation is allowed to have a point of view. The launch essay already does this well. Architecture should too, without the launch-path pseudocode.
- Crossing the boundaries is “at the heart of a vast number of problems in documentation.” SASE’s mega-pages are that crossing, scaled up.

Workflow consequences, again: do not plan the cathedral. Improve the page in front of you. For SASE, “the page in front of you” is often 9,000 lines, so the first improvement on those pages is **split until a page can be judged**.

Canonical adopted Diátaxis as direction, not as a one-shot rebuild, and noted that the first effect is that problems look worse because they become visible ([Ubuntu blog, 2021](https://ubuntu.com/blog/diataxis-a-new-foundation-for-canonical-documentation)). That is a feature. SASE should expect the audit table in §6 to look unkind.

---

## 5. What comparable sites do

These are the patterns worth copying. None require a new SSG.

**Click** ([click.palletsprojects.com](https://click.palletsprojects.com/en/stable/)) is the closest cousin: a Python CLI, Diátaxis-structured, with user-facing labels: Tutorials, How to Guides, Conceptual Guides, General Reference, API Reference. The home is a short “what it is,” a tiny worked example, then the typed index. It states the Diátaxis debt in the footer. SASE should do the same in Contribute, not on the home hero.

**Django** keeps a **thematic** table of contents (models, views, forms) and an **underlying type hierarchy** (tutorial, topic guides, how-to, reference). The index says so in plain language ([docs.djangoproject.com](https://docs.djangoproject.com/en/dev/)). New users get a multi-part tutorial that creates a poll app. Topic guides are explanation. How-tos are recipes. API details live in reference. This hybrid is the right long-term shape for SASE: type-first tabs, job-grouped pages inside Guides.

**Kubernetes** docs home is a hub of hubs: Understand (concepts), Try (tutorials), Set up, Tasks (how-to), Reference, Contribute. Each bucket has four to eight links. The sidebar is scoped. This is the home UX sase.sh should steal.

**Sequin** rewrote from “How Sequin works” first to a three-minute quickstart with one aha (changes flowing from Postgres to a sink). How-to writing exposed product gaps. They used “phantom links” to not-yet-written reference pages as a backlog. They used a model loaded with the Diátaxis site as a reviewer, not as the author. Highest ROI was tutorials, how-tos, and complete reference; explanation came last.

**Cloudflare** used Diátaxis as a north star while redesigning developer docs (quoted on diataxis.fr). Gatsby reorganized around the four quadrants for discovery. Both treated the framework as author guidance plus IA, not as a marketing label.

**Azion** adds a fifth form that Diátaxis does not name and SASE needs: the **navigation hub**. A hub routes. It does not teach, instruct, describe, or explain. Home, Start, Guides, Concepts, and Reference should each have a hub page of that shape.

**llms.txt** ([llmstxt.org](https://llmstxt.org/)) is a small Markdown file at `/llms.txt` that lists the docs an LLM should read, with optional `/llms-full.txt`. SASE should ship this as the agent corpus, rather than hoping agents ingest `ace.md`.

What not to copy: empty four-column marketing sites; “everything is a guide”; putting contributor runbooks in Getting Started; using page length as a proxy for completeness.

---

## 6. Recommended solution

### 6.1 Destination IA (user-facing)

Keep MkDocs Material. Enable `navigation.tabs` and `navigation.tabs.sticky`, keep `navigation.sections` for level-two groups, add hub `index.md` pages (`navigation.indexes` is already on). Add `navigation.path` breadcrumbs. Consider `navigation.prune` after the tree grows.

**Top tabs:**

| Tab | Diátaxis type | Job |
| --- | --- | --- |
| **Start** | Tutorials | Lessons. Safe, on rails, one aha each. |
| **Guides** | How-to | Real jobs. “How do I…?” grouped by work, not by subsystem. |
| **Concepts** | Explanation | Why the pieces exist and how they relate. |
| **Reference** | Reference | Machinery: CLI, config, TUI keys, query language, schemas. |
| **Contribute** | Mixed, but labeled | Local setup, docs workflow, Rust boundary, testing provider. |
| **Blog** | Essays | Launch posts and long-form. Already a plugin. |

Do not use “The Basics” or “Nitty Gritty.” Those encode author anxiety, not user need.

**Start (tutorials), suggested set:**

1. Your first 15 minutes (rescued current tutorial: install, doctor, read-only run, find the record, tiny edit, one artifact handoff). Stop. No keymap encyclopedia. No SDD.
2. Supervise a run in the TUI (open `sase tui`, find the agent, open the transcript, quit). One lesson.
3. Turn a prompt into a macro (today’s step 7, as its own lesson).
4. Optional later: a Patch from a small change; a Goal you cite; a two-agent handoff.

Each tutorial is concrete, particular, and restartable. `+home` is the right sandbox. Link out to Guides and Concepts; do not inline them.

**Guides (how-to), grouped by job:**

- Set up: install a provider, `sase init`, add an existing repo, shell completion.
- Daily work: launch agents, use the TUI, review a Patch, cite an artifact, save a prompt.
- Automation: write a macro, run a workflow, schedule a job, set autonomy.
- Recover: interrupted agent, runner slots, update-skew restart.
- Operate: mobile gateway, remote dispatch, sudo, notifications.

Titles should be verbs: “Add an existing GitHub repo,” “Hand a file to another agent,” “Recover an interrupted run.”

**Concepts (explanation):**

- Why a coordination layer (link the launch essay; do not duplicate it).
- Architecture map (today’s `architecture.md`, with the launch-path steps moved to reference).
- Work units: Goals vs beads vs Patches vs stitches vs artifacts.
- Memory and instructions (what agents see, what humans edit).
- Workspaces and isolation.
- Provider and plugin boundary, at a conceptual level.

**Reference:**

- CLI hub (keep `cli.md` as an index; add per-command pages generated from `--help` over time).
- Configuration hub, split by `sase.yml` section, generated from schema/default_config where possible.
- TUI keymap and CLI options for `sase tui`.
- Query language.
- ProjectSpec, workflow spec, macro syntax.
- LLM provider catalog (the generated tables already in `llms.md`).

**Contribute:** development, docs workflow, rust backend, fakey, instruction inventory, artifacts pane contracts, perf runbook, telemetry. These pages can stay public. They must leave Start and Guides.

**Hub pages:** Start, Guides, Concepts, and Reference each get an `index.md` that is only orientation plus grouped links (Azion’s hub form). Home is the top hub.

### 6.2 Home UX

Hide the left nav on `index.md` (`hide: [navigation]` is a Material feature). The home is a page, not a second sidebar.

**Hero**

- One sentence of what SASE is (coordination layer above coding-agent CLIs).
- Alpha + POSIX note, currently buried in the README.
- **One primary button:** Start — Your first 15 minutes.
- **One secondary button:** Why SASE exists (launch essay) *or* GitHub, not both in the hero.
- Move PDF and GitHub to the footer of the home, or to a “Also” row.

**Body, Kubernetes-style buckets, four to six links each:**

1. Start here (the tutorials).
2. Do a job (four Guides: init a repo, open the TUI, make a Patch, cite a Goal).
3. Understand the model (architecture, work units, memory).
4. Look it up (CLI, config, query language).

Drop the eight-plus-nine card fields. Role cards that survive become the Guides hub.

The component diagram can stay, but as a Concepts teaser, not as the thing a first-time visitor must decode.

This is how the proposed changes make the site more intuitive: the person who wants to learn is not asked to choose among seventeen peers of “Getting Started.” They are walked. The person who already knows the job they have goes to Guides. The person debugging a flag uses search and Reference. Those are different visits. The current home pretends they are the same visit.

### 6.3 Page contract (the process structure)

This is the high-leverage half. Land it even if the tabbed nav slips a week.

**Frontmatter on every docs page:**

```yaml
---
title: ...
description: ...
type: tutorial | howto | reference | explanation | hub | blog
audience: user | contributor | operator
status: current | internal | deprecated
---
```

`type` is the Diátaxis (plus hub) label. `audience` keeps contributor pages out of Start. `status: internal` is how Instruction Inventory stays in the repo without appearing in Start.

**Size budgets (soft, CI-warn, then CI-fail on new pages):**

| Type | Target | Hard cap |
| --- | --- | --- |
| Tutorial | 1,500–2,500 words | 4,000 |
| How-to | 800–2,000 | 4,000 |
| Explanation | 1,500–3,500 | 5,000 |
| Hub | < 400 | 800 |
| Reference | whatever the machinery needs, but one topic per page | 8,000 per file; split by command/section |

`goals.md` already sits in the how-to/explanation band. `getting_started.md` at 4,145 words is at the tutorial cap because of leaked reference; after a rescue it should land near 2,000.

**Templates** in `docs/templates/` (or `docs/_templates/`):

- Tutorial: goal of the lesson, time, prerequisites, numbered steps, “what you just did,” what not to do yet, one next lesson.
- How-to: goal, assumptions, steps, branches (`if this, then that`), failure notes, links to reference.
- Reference: structure mirrors the object; no tutorial voice; no “why we built this.”
- Explanation: claim, context, alternatives, links to how-to and reference.
- Hub: one orientation sentence, grouped links, stop.

**Compass checklist** in `docs/development.md` (docs workflow section) and a short `docs/README.md`:

- Is this action or cognition?
- Is the user at study or at work?
- What would have to move to another page for this page to serve one need?

**Generated vs authored:**

- Generated: model catalogs (already), CLI flag tables, config key tables, TUI keymap tables.
- Authored: tutorials, how-tos, explanations, hub copy.
- Marker convention already exists (`<!-- BEGIN GENERATED: name -->`). Extend it. `just fmt-docs` grows from one script to a small family, still YAML/help-driven, still import-light.

**`refresh_docs` constraints:**

- The update prompt must name the page `type` and forbid adding a second mode.
- Polish must check the compass, not only “clarity for someone new.” “Someone new” is a tutorial criterion; applying it to reference produces the current `ace.md`.
- The job may propose splits when a page exceeds the cap. It may not silently absorb the overflow into the same file.
- The job must not move pages between tabs. IA is human.

**CI additions** (all cheap, all fail-closed on new violations):

- `just docs-check` already strict-builds.
- Lint: every page has `type` and `audience`.
- Lint: new files respect the hard cap; existing mega-pages are listed in a temporary allowlist that only shrinks.
- `fmt-docs-check` covers every generated block.
- Optional later: `sase --full-help` command names must appear in the CLI hub.

**Authoring rule for mixed pages:** when a page wants a second mode, it links. Sequin’s phantom-link trick is the right backlog tool: write `[How autonomy profiles are chosen](../reference/autonomy.md)` before the target exists, then fill reference from the phantom list.

### 6.4 Mega-page splits (planned, not organic)

Sentence-level Diátaxis cannot chew these. Split them on purpose, with redirects.

**`ace.md` → TUI family**

- `guides/tui.md` — how to work in the TUI (daily).
- `start/tui-lesson.md` — the second tutorial.
- `reference/tui-cli.md` — `sase tui` options.
- `reference/tui-keys.md` — keymaps, generated from `ace.keymaps` if possible.
- Per-tab how-tos only where a tab is a real job (Agents, Artifacts, Services, Admin).
- Contracts (`artifacts_pane_contract.md`, visual grammar) → Contribute.

**`configuration.md` → generated section pages**

One page per top-level `sase.yml` key (`ace`, `axe`, `llm_provider`, …), plus env-var index and CLI-flag index. Hub page lists them. This is the reference architecture matching the machinery.

**`macros.md` → concept + how-to + reference**

- Concept: what a macro is.
- How-to: write one, add inputs, fan out.
- Reference: directives, discovery order, skill field.

**`beads.md` / `sdd.md`**

- Concept: beads vs epics vs phases vs Goals vs Patches.
- How-to: file a task, run an epic.
- Reference: bead CLI and storage.

**`llms.md`**

Keep generated tables. Move “how to install and authenticate a provider” to Guides (`agent_providers.md` already exists). Move “why providers are plugins” to Concepts.

**`cli.md`**

Keep as the discovery index it already claims to be. Do not let it become another dump. Per-command pages can land incrementally.

Preserve old URLs with `mkdocs-redirects` (already in the stack). The existing `_redirects` file is the Cloudflare layer for a few aliases; keep using both.

### 6.5 Dual corpus for humans and agents

sase.sh pages get shorter and more modal. Agents still need a complete map.

Ship:

- `docs/llms.md` is already a **provider** page. Do not overload that URL. Add `docs/llms.txt` (or `docs/llms/index.md` published at `/llms.txt` via extra files) listing the canonical human pages an agent should read, by type.
- `llms-full.txt` (or a generated “agent handbook”) concatenates reference hubs and concept pages, not the tutorials. Tutorials are for humans with a terminal.
- Instruction bundles remain the runtime instruction channel. Public docs are not a substitute for `sase/memory/` and per-invocation bundles. Instruction Inventory belongs in Contribute, as history, until the epic is gone.

This is the requirement change that lets the human site simplify without lying to agents.

### 6.6 What to do with the PDF

Options, in order of preference:

1. **Curated handbook:** Start tutorials + Concepts + CLI hub. That is a book a person might read.
2. **Per-tab PDFs** if someone still wants Reference on a plane.
3. Keep the whole-site PDF as a CI artifact, unlinked from the hero.

Do not advertise the current whole-site PDF as “the handbook.”

### 6.7 Migration sequence

This sequence respects Diátaxis’s “always complete, never finished” rule while admitting that mega-pages need a plan.

**Phase A — Process, no user-visible IA change**

- Add `type` / `audience` frontmatter to every page (mechanical).
- Add templates and the compass note to the development docs workflow.
- Add size allowlist + lint.
- Classify the existing tree in a table in Contribute (the unkind audit). That table is the backlog.

**Phase B — First public win**

- Rescue Getting Started: eight steps become six short ones; strip keymap/SDD/component-map dumps; “what to read next” points at the second tutorial and the Guides hub, not Instruction Bundles.
- Enable tabs + hub index pages; **move files in nav without rewriting them**.
- Relocate Instruction Inventory, pane contracts, fakey, rust backend, development, telemetry, layout migration into Contribute.
- Home: one primary CTA, four buckets, alpha note. Hide home sidebar.

Ship. The site is already more intuitive, even if `ace.md` is still huge, because the learner is no longer asked to find it under “The Basics” next to Memory History.

**Phase C — Splits and generated reference**

- Split `ace.md`, `configuration.md`, `macros.md` in that order.
- Extend `render_model_docs`-style generation to config sections and keymaps.
- CLI hub hygiene.

**Phase D — More lessons and how-tos**

- TUI lesson, macro lesson.
- Verb-titled Guides for the ten jobs new users actually have.
- Phantom links from those Guides become reference pages.

**Phase E — Agent corpus and constrained refresh_docs**

- `/llms.txt` + generated full dump.
- Type-aware `refresh_docs` prompts.
- Agents may propose splits and drift fixes; they may not retitle tabs.

Each phase is shippable. That is the Diátaxis workflow with a destination sketch, which SASE needs because the corpus is already large.

### 6.8 Agentic management (kept in its place)

Use agents for:

- classifying pages with the compass (human reviews the table);
- proposing splits when a file exceeds the cap;
- refreshing generated reference after CLI or schema changes;
- link checks, screenshot freshness, `fmt-docs`;
- polish passes that are type-aware.

Do not use agents for:

- choosing the top-level IA;
- writing the first-15-minutes narrative as a completeness dump;
- “document everything that changed since the last 25 commits” without a type constraint.

The existing two-agent update/polish pair is a good skeleton. Change the prompts and add the lints. That is enough agentic process for this problem. A docs-memory web or a dedicated docs bead type can wait until the taxonomy exists; otherwise agents will file beads against a pile.

---

## 7. Alternatives considered

| Alternative | Why it loses |
| --- | --- |
| Four empty Diátaxis folders, then move everything | Explicitly rejected by Diátaxis; URL churn; mixed pages stay mixed under new titles |
| Thematic nav only (TUI, Beads, Macros, …) | Matches the code, not the visit. Django uses theme *inside* type. SASE already over-indexes on subsystems |
| Difficulty ladder, cleaned up | The current model. Cleaning “Nitty Gritty” does not tell a user where to look up a flag vs how to recover a run |
| Switch to Docusaurus / Starlight | Months of migration; no evidence the generator is the bottleneck |
| Delete until the site is “small” | Destroys reference completeness; agents and operators still need the facts |
| Make `refresh_docs` the docs team | Unconstrained completeness prompts created this corpus |
| Explanation-first home (“how SASE works”) | Sequin measured this and it failed. SASE’s home already has a why-section plus 17 CTAs |
| One page per primitive, mixing modes on purpose | “Everything about Beads in one URL” is how you get 28,000-word pages |

The winning alternative is **type-first tabs, job-grouped Guides, generated Reference, hub home**, migrated in phases, with process lints that make regression obvious.

---

## 8. How this makes sase.sh more intuitive

A person who has never used SASE:

1. Hits sase.sh. Reads one sentence. Clicks Start.
2. Spends fifteen minutes in `+home`. Ends with a run they can see and a file they handed off. Feels competent.
3. Is offered one next lesson (the TUI), not a component map.
4. When they have a real repo, they open Guides: “Add an existing GitHub repo.”

A person who already uses SASE:

- Tabs scope the sidebar. They live in Guides and Reference.
- Search (already on) plus a CLI hub that is actually an index.
- Config lookup is a section page, not a 7,700-line scroll.

A contributor:

- Contribute tab exists. They are not editing Getting Started to document an epic inventory.
- A PR that adds a 12,000-word “basics” page fails a budget lint.

An agent:

- Reads `/llms.txt` and reference hubs.
- `refresh_docs` will not enlarge `getting_started.md` with the new flag it found; it will patch the generated reference page.

Intuition here is information scent: the label in front of you matches the need you have, and the page you open does not change mode halfway through. That is Diátaxis’s deep quality (flow, fit, anticipation). Functional quality (accuracy, completeness) moves into Reference and the agent corpus, where completeness belongs.

---

## 9. Success criteria

The work is succeeding when:

1. A new user can finish Start 1 without reading a keymap table or an epic disposition list.
2. The home has one primary CTA, and Instruction Inventory is not in Start.
3. No user-facing how-to or tutorial exceeds 4,000 words, except a shrinking allowlist of pre-existing mega-pages.
4. `ace.md` and `configuration.md` no longer exist as single files.
5. Every docs page declares `type` and `audience`.
6. `refresh_docs` cannot merge a second Diátaxis mode into a page without failing polish or CI.
7. `/llms.txt` exists and is what you hand an agent that needs to learn SASE from the web.
8. The PDF, if still offered, is a curated handbook.

The work is failing if the nav says Start / Guides / Concepts / Reference but Getting Started is still 4,000 words of mixed mode, or if `ace.md` is merely moved under Reference unchanged.

---

## 10. Recommendation

**Adopt Diátaxis as the documentation system: page types, writing mode, and a type-first site, implemented iteratively on MkDocs Material.**

Do not do a drastic four-folder rewrite. Do not switch generators. Do not center the program on agent-authored docs.

**Ship in this order:** process contract → rescued tutorial + tabbed nav + hub home → mega-page splits and generated reference → more lessons and verb-titled Guides → constrained `refresh_docs` and `/llms.txt`.

That is the best documentation solution for sase.sh. It is simpler for learners because it stops asking them to read the machinery in order to take a lesson. It is more structured for authors and agents because every page has one need, one budget, and one place it can live. It uses Diátaxis the way Diátaxis asks to be used: as a compass on real pages, with a destination IA that those pages are allowed to grow into.

---

## Sources

### Primary (this repo and the live site)

- [https://sase.sh](https://sase.sh) home
- `mkdocs.yml` navigation and theme flags
- `docs/index.md`, `docs/getting_started.md`, `docs/ace.md`, `docs/configuration.md`, `docs/cli.md`, `docs/architecture.md`, `docs/instruction_inventory.md`, `docs/development.md` (Documentation Workflow, Docs Deployment)
- `docs/blog/posts/hello-sase-your-first-15-minutes.md` (draft duplicate)
- `docs/_redirects`, `mkdocs-pdf.yml`, `docs/overrides/main.html`
- `Justfile` (`docs-check`, `docs-pdf-check`, `fmt-docs`)
- `tools/render_model_docs`
- `src/sase/scripts/sase_chop_refresh_docs.py` and `docs/axe.md` builtin `refresh_docs`
- `README.md` (alpha, POSIX, coordination-layer positioning)
- Word counts via `wc` on `docs/**/*.md` (2026-10-15 checkout)

### Diátaxis

- [https://diataxis.fr](https://diataxis.fr)
- [Start here](https://diataxis.fr/start-here/)
- [Applying Diátaxis](https://diataxis.fr/application/)
- [The compass](https://diataxis.fr/compass/)
- [The map](https://diataxis.fr/map/)
- [Workflow](https://diataxis.fr/how-to-use-diataxis/)
- [Quality](https://diataxis.fr/quality/)
- [Tutorials vs how-to guides](https://diataxis.fr/tutorials-how-to/)

### Comparable systems and case studies

- [Click documentation](https://click.palletsprojects.com/en/stable/) (explicit Diátaxis structure for a Python CLI)
- [Django documentation](https://docs.djangoproject.com/en/dev/) and [What to read next](https://docs.djangoproject.com/en/dev/intro/whatsnext/)
- [Kubernetes docs home](https://kubernetes.io/docs/home/)
- [Sequin: We fixed our documentation with the Diátaxis framework](https://blog.sequinstream.com/we-fixed-our-documentation-with-the-diataxis-framework/) (2024)
- [Canonical: Diátaxis, a new foundation for Canonical documentation](https://ubuntu.com/blog/diataxis-a-new-foundation-for-canonical-documentation) (2021)
- [Material for MkDocs: navigation](https://squidfunk.github.io/mkdocs-material/setup/setting-up-navigation/) (tabs, indexes, path, prune, hide)
- [llms.txt](https://llmstxt.org/)
- [Azion: Navigation hubs](https://www.azion.com/en/documentation/style-guide/content/navigation-hubs/)
