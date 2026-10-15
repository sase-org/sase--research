# Simplifying sase.sh: documentation architecture, reader experience, and a sustainable publishing process

Independent research by **cdx**, 2026-10-15. This report was developed without consulting the other reports or researchers in this swarm.

## Decision in brief

The simplification is justified. SASE already has extensive documentation; its immediate problem is that newcomers encounter too much of it, too early, while experienced users must consult enormous mixed-purpose pages.

Adopt **Diátaxis as the editorial model**, with reader-facing areas called **Start here, Guides, Concepts, and Reference**. Give sase.sh a short product landing page and one reliable first-run journey. Preserve detailed material, but split large references and move implementation contracts out of the beginner navigation. Keep Markdown and review beside the code.

Deliver the content improvements on the existing site first. In parallel, evaluate **Zensical as the preferred renderer successor**, with a concrete compatibility gate. Material for MkDocs is in its final maintenance period; an indefinite “keep the current stack” recommendation would overlook that constraint. Do not make a renderer migration a prerequisite for improving the learning experience.

## 1. Scope, evidence, and limits

I examined the live site, its desktop and mobile presentation, the local documentation corpus, navigation and deployment configuration, documentation-refresh prompts, selected documentation tests, and the official Diátaxis and renderer documentation. The local checkout was at `bc4bc3e183db0b97b00f9eea9ec6b5bb57e29b8e` when audited. I did not establish that production was built from exactly that revision.

Browser observations used Chromium at **1440 × 1000** and **390 × 844**. I inspected the homepage and mobile navigation. There was no horizontal overflow in those homepage captures. This was a limited expert audit, not an accessibility certification, a performance benchmark, or research with actual SASE users. Search suggestions below are design recommendations; I did not establish a reliable search-quality baseline. I did not install SASE afresh or launch a paid provider to validate the tutorial end to end.

Counts below are reproducible from `mkdocs.yml` and the Markdown tree. “Words” means whitespace-separated tokens, including code, tables, frontmatter, and markup. It is a source-volume indicator, not a measurement of prose reading time.

| Source measure | Observation |
| --- | ---: |
| Top-level navigation entries, including Home and Blog | 8 |
| Markdown destinations explicitly listed in navigation | 57 |
| Markdown files anywhere under `docs/` | 90 |
| Documentation pages excluding `blog`, `plans`, `images`, and `overrides` directories | 57 |
| Words across that last group | 518,106 |
| `docs/getting_started.md` | 4,145 words; 488 lines |
| `docs/ace.md` | 103,267 words |
| `docs/configuration.md` | 70,562 words |
| `docs/macros.md` | 32,179 words |
| `docs/beads.md` | 27,951 words |
| `docs/llms.md` | 26,773 words |

The TUI and configuration pages alone contain about one third of the measured corpus. This is a strong reason to improve page boundaries, not a reason to remove one third of the documentation.

Local evidence anchors: `mkdocs.yml`; `docs/index.md`; `docs/getting_started.md`; `docs/ace.md`; `docs/configuration.md`; `docs/agent_providers.md`; `docs/development.md`; `mkdocs-pdf.yml`; `.github/workflows/docs-deploy.yml`; `src/sase/scripts/sase_chop_refresh_docs.py`; `tools/render_model_docs`; `tests/test_docs_getting_started_providers.py`. SASE vocabulary was checked through audited memory reads.

## 2. What is making the current site difficult

### The navigation asks readers to classify difficulty before they understand the product

The present groups include “The Basics,” “Beyond the Basics,” and “The Nitty Gritty.” These labels do not predict where to find a particular task. “The Basics” contains both the TUI and developer-facing artifact-pane contracts. “Getting Started” includes content-layout migration and instruction-delivery inventories. These are useful subjects, but their placement implies that a new user should understand them early. The [live homepage](https://sase.sh/) exposes this organization.

The desktop sidebar presents many links at once; the mobile drawer does collapse the top-level groups, which is useful. Neither behavior resolves the ambiguity of the labels. Changing visual grouping alone would leave that ambiguity intact.

### The introductory journey accumulates unrelated responsibilities

The [current first-15-minutes guide](https://sase.sh/getting_started/) starts with installation and a simple run, then introduces prompt-history edge cases, draft recovery, commit and push behavior, artifact reference forms, reusable macros, executable plans, dependency checkpoints, autonomy policy, and a substantial component glossary.

This material is often accurate and valuable. Its collective effect is that a first successful run feels like the start of a large curriculum rather than a complete achievement. A learner needs a clear stopping point and a choice of next task.

The [provider installation page](https://sase.sh/agent_providers/) similarly introduces instruction-delivery channels and verification internals near the beginning. A person resolving authentication should reach the relevant provider instructions before that material.

### Large topic manuals combine distinct reading modes

The TUI page mixes orientation, daily tasks, exhaustive keybindings, edge cases, and behavioral contracts. The configuration page covers configuration, environment variables, CLI flags, interactive administration, and migration details. The CLI index routes readers into these large owners, so merely finding the right command does not necessarily produce a focused answer.

A subsystem name is a reasonable reference category. It is a poor sole organizing principle for every kind of documentation. “Macros,” for example, can mean a first lesson, a reuse recipe, syntax reference, or an explanation of prompt composition.

### The homepage leads with implementation and gives four actions equal emphasis

The hero opens with Python, TUI, and a required Rust core before demonstrating the user's outcome. Getting Started, Download PDF, View on GitHub, and Launch Post share the same button treatment. On the 390-pixel capture, these occupy four full-width rows. Lower down, eight role/task cards and another collection of next-click cards create repeated routing decisions.

The existing page has a coherent visual treatment and responsive layout. The opportunity is to reduce the number of decisions, strengthen the primary action, and show what a supervised run actually looks like. The existing README already contains product demonstration assets that can inform this work.

### Accuracy controls exist, but they do not enforce useful scope

The project has a strict MkDocs build, generated model-catalog blocks, PDF validation, and documentation-related tests. This is a valuable starting point.

The refresh workflow proposes an update agent followed by a polish agent. Its prompts emphasize current behavior, completeness, clarity, and documentation-only edits. They do not establish a reader task, documentation type, canonical owner for a fact, or a rule against expanding the beginner path. Broad refreshes can therefore remain accurate while making navigation and page scope worse. This is a plausible failure mode, not evidence that automation caused the existing volume.

## 3. Critique of the proposed direction and explicit requirement adjustments

**Yes, simplify the experience. Do not make “fewer pages” or “fewer total words” the objective.** Splitting two huge references may increase page count while making answers far easier to find. Judge the result by learning success, task completion, and accurate lookup.

**Use Diátaxis to distinguish reader needs, not to fill a four-quadrant checklist.** Its own workflow guidance recommends incremental improvement and warns against erecting empty structures or tearing down the existing corpus wholesale. A complete set of four documents for every feature would multiply maintenance without proving demand. [Diátaxis workflow guidance](https://diataxis.fr/how-to-use-diataxis/)

**Treat public-site UX and document maintenance as related but separate design problems.** Navigation and progressive disclosure improve discovery; clear content ownership and verification improve durability. Neither substitutes for the other.

The following are deliberate adjustments to the original requirements:

1. **Replace “drastically simplify documentation” with “drastically simplify the first experience and routine discovery.”** Keep comprehensive technical coverage accessible.
2. **Make audience separation explicit.** The primary reader is a developer who already understands Git and at least one coding-agent CLI, but is new to SASE. Operators, plugin authors, and contributors need dedicated routes, not extra prerequisite reading for everyone. This follows the principle of writing to the gap between existing knowledge and the task at hand. [Google Technical Writing: Audience](https://developers.google.com/tech-writing/one/audience)
3. **Add a small user-validation requirement.** This report can propose a strong architecture; it cannot establish which labels actual users find intuitive without observation.
4. **Add URL and fragment compatibility as migration requirements.** Existing links from prompts, issues, skills, search engines, and external articles are part of the documentation interface.
5. **Add explicit documentation applicability.** State whether production docs describe the latest released SASE or development head. Do not leave a rapidly changing alpha product's readers to infer this from a GitHub tag badge.
6. **Add a renderer transition checkpoint.** The current theme's support horizon is an implementation constraint, even though choosing a new generator is not the central UX solution.

I would not start with a new CMS, an AI answer interface, a complete prose rewrite, or a comprehensive agentic documentation platform. Each adds another project before the reader's immediate problem has been solved.

## 4. Applying Diátaxis without making readers learn Diátaxis

Diátaxis separates four needs: learning through a guided experience, completing a task, consulting precise facts, and developing understanding. That distinction is the useful foundation. [Diátaxis overview](https://diataxis.fr/)

| Reader need | SASE navigation label | Editorial contract | Example |
| --- | --- | --- | --- |
| Learn by doing | Start here / Tutorials | A controlled example, visible results, limited choices, a definite finish | Run an agent and inspect its result |
| Complete real work | Guides | Task-specific prerequisites, actions, verification, and recovery | Add an existing repository; recover a saved draft |
| Understand the model | Concepts | Explain relationships, reasons, and tradeoffs | How projects, repositories, and workspaces relate |
| Look up exact behavior | Reference | Precise, consistent descriptions of commands, settings, syntax, and constraints | `sase agent` options; configuration precedence |

The beginner tutorial should provide an experience whose success the author can check. It should show expected observations as the reader progresses and defer detailed explanation to links. [Diátaxis tutorials](https://diataxis.fr/tutorials/)

Guides should be framed by a user's problem, including problems spanning multiple subsystems. “Reuse a successful prompt” is a better guide title than “Macro operations.” [Diátaxis how-to guides](https://diataxis.fr/how-to-guides/)

Reference can retain product-shaped organization and necessary detail. Standard layouts, scope, defaults, and examples matter more than reducing it to short summaries. [Diátaxis reference](https://diataxis.fr/reference/)

“Concepts” is a reader-friendly label for explanation: relationships, reasons, constraints, and alternatives belong there. [Diátaxis explanation](https://diataxis.fr/explanation/)

A page should have one dominant purpose. That does not require removing every sentence of context from instructions. One sentence explaining a surprising action can prevent a mistake; a detour through backend design usually belongs elsewhere. Landing pages are routing devices and need not be forced into a content quadrant.

## 5. Proposed information architecture

Use one site and one content repository. Keep the main navigation compact:

```text
SASE logo → Home
Start here | Guides | Concepts | Reference | Blog
Search and GitHub as utilities; Contribute and Support as clear utility/footer links
```

Start here is a small curated entry, not a second “everything introductory” category. Its landing page can distinguish “I want to see a first run” from “I already use SASE and need a task guide.” Tutorials remain explicitly labeled within it.

```text
Start here
  Is SASE right for me?               [short overview]
  Run your first agent               [tutorial]
  Make and review a small change      [second tutorial]
  Installation and provider setup    [links to focused guides]

Guides
  Set up a project
  Run and supervise agents
  Review and deliver changes
  Reuse prompts and workflows
  Share context and results
  Plan larger work
  Operate and troubleshoot

Concepts
  How SASE coordinates agent work
  Projects, repositories, and workspaces
  Runs, sessions, and handoffs
  Plans, task tracking, Patches, and Goals
  Memory and durable context
  Automation and human checkpoints

Reference
  CLI commands
  Configuration and environment
  TUI controls and keybindings
  Prompt and workflow syntax
  Artifact references and queries
  Providers and integrations
  Glossary
  Developer reference → contributor area
```

These are proposed groupings, not an instruction to publish empty pages. Begin with real content for the highest-priority journeys and retain useful existing pages elsewhere until they can be extracted properly.

The contributor area should contain development setup, architecture internals, Rust boundaries, plugin and integration contracts, UI component contracts, performance instrumentation, and documentation contribution guidance. It can live under the same generator and domain with its own landing page and sidebar. Operator guides such as service setup and recovery remain visible to users through Guides; “advanced” does not mean “internal.”

For occasional subject-based discovery, section landing pages can route a subject such as Memory to its guide, concept, and reference. Add such a hub only when the subject actually has those resources. Do not recreate the complete navigation beneath every mode.

A useful precedent is [uv's documentation](https://docs.astral.sh/uv/), which distinguishes Getting started, Guides, Concepts, Reference, Troubleshooting, and Internals. [Docker Docs](https://docs.docker.com/) also separates entry routes from detailed reference. These are examples of navigational vocabulary, not proof that SASE should copy their scale or layouts.

## 6. The sase.sh experience

### Homepage: establish value and offer one next action

Proposed hero copy, subject to product review:

> **Run coding agents together. Keep their work reviewable.**
>
> SASE helps you launch agents in separate workspaces, follow their progress, and carry results between runs from one terminal interface.
>
> **Run your first agent** · Watch the demo

Add a compact suitability line: alpha status; Linux/macOS; one supported authenticated agent CLI. Put detailed compatibility and installation requirements on the linked setup page. The Rust core is an installation/architecture fact, not the first benefit to explain.

Follow the hero with:

1. One legible TUI screenshot or short, captioned recording showing launch → progress → result. Reuse current accurate assets when possible; provide a still and text alternative, and avoid compulsory autoplay.
2. Three concrete capabilities: supervise parallel work, reuse context, review changes.
3. Three clearly named routes: Start learning, Complete a task, Look up a command.
4. A compact supported-provider summary and links to Concepts, contribution, support, and the blog.

Move Download PDF and the launch essay to secondary locations. Preserve their URLs. They serve useful readers, but neither should compete visually with the first run.

Progressive disclosure supports this approach: make common needs immediately visible and link clearly to specialized detail. Hiding important prerequisites or making the route to advanced material obscure would defeat it. [Nielsen Norman Group: Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/)

### The first tutorial: finish after one observable result

Use an editorial starting budget of roughly **900–1,400 words**, then adjust based on observed completion. This is a design target, not a universal limit or a proven SASE reading-time estimate.

Keep the story to:

1. Confirm installation and one authenticated provider, with focused recovery links.
2. Launch the explicit managed demo project with `+home`, explaining that this is SASE's demo workspace rather than the reader's current directory.
3. Find the run in the TUI and identify its prompt, status, and result.
4. Finish with “You have launched and inspected a SASE run,” followed by two next choices: make a small change or connect a real repository.

The first meaningful result should not require understanding macro syntax, the complete glossary, artifact digest forms, dependency scheduling, or automation policy. Provider-specific selection exceptions must remain easy to discover at the relevant step; move their implementation details into provider setup/reference rather than pretending every provider behaves identically.

The next tutorial can make a small change and review its diff. Explain commit and push effects **before** the step that triggers them. Use the managed demo repository to establish that behavior before asking users to target their own remote. Workspace isolation should be described accurately; a prompt asking an agent not to edit files is not an enforceable security guarantee.

### Document pages: orient, answer, then connect

Each page should say what it helps with and who it assumes the reader is. Procedural pages should identify prerequisites, show expected results, and offer a recovery link. Reference should expose exact syntax and defaults without requiring a tutorial to be read first.

Keep the current location visible with a section title and breadcrumbs. Use explicit next-step links in tutorials, a local table of contents for substantial reference pages, and normal copyable code blocks. Use expandable details for exceptional branches, not for essential instructions or core answers.

The current Material stack already supports section indexes, navigation tabs, and breadcrumbs. Its documentation also makes clear that desktop tabs do not automatically redesign the mobile drawer; both must be checked. [Material navigation options](https://squidfunk.github.io/mkdocs-material/setup/setting-up-navigation/)

For search, prioritize current public documentation over historical blog posts and internal design pages where the chosen renderer permits. Make titles and descriptions match likely queries: “agent authentication,” “add a repository,” “saved prompt,” “review a diff.” Add legacy names and SASE-specific synonyms where useful. Validate these decisions with a small fixed query set; do not assume that adding a chat box solves information architecture.

## 7. What to do with the existing documents

| Existing content | Recommended treatment |
| --- | --- |
| `getting_started.md` | Keep the first-run lesson; extract reuse, artifact handoff, planning, and glossary material into their appropriate destinations |
| `init.md`, `content_layout.md` | Separate installation/project setup tasks from migration; migration belongs under Operations/Upgrade |
| `agent_providers.md` | Put provider installation/authentication first; move instruction-delivery diagnostics and adapter internals to focused guides/developer reference |
| `ace.md` | Create a short TUI orientation; extract task guides; split controls/reference by meaningful surface such as Agents, Artifacts, prompts, and administration |
| `configuration.md` | Separate configuration files and precedence, setting families, environment variables, and command flags; stop treating configuration as the owner of every CLI flag |
| `cli.md` | Retain its discovery role, but route each command family to focused, consistently structured command reference |
| `macros.md`, `workflow_spec.md` | Separate a first reusable-prompt lesson, real task recipes, and syntax/reference; maintain one authoritative definition of each directive |
| `beads.md`, `sdd.md`, `goals.md`, `change_spec.md` | Add a concise relationship explanation; retain each object's exact lifecycle and commands in reference |
| Artifact-pane contracts and visual grammar | Contributor/developer area, linked from relevant public integration reference |
| Service, remote dispatch, and recovery runbooks | Operations and troubleshooting guides, organized by task or symptom |
| Blog posts | Dated essays and announcements; link to maintained docs and mark obsolete instructions when discovered |
| `agent_auto_restart.md` | Give recovery material a predictable troubleshooting route; it currently exists outside explicit main navigation |

Do not split every heading into a page. A useful boundary is a complete task, a coherent concept, or one reference family. Splitting a command's individual flags across separate pages would make lookup worse. Keep a working page intact if extraction would make its task harder to follow.

Maintain a migration inventory with **keep / extract / merge / move / archive** decisions and a canonical destination for each extracted section. Large manuals can temporarily remain available through a reference hub. A smaller sidebar must not make still-needed content disappear.

## 8. Publishing technology: staged change with an explicit successor decision

The current implementation is more than Markdown plus a theme: it includes blog and RSS behavior, redirects, custom social metadata, styles, a PDF exporter with browser processing, PDF post-processing/validation, and a Cloudflare deployment pipeline. A replatform has to preserve or intentionally replace those dependencies.

The Material maintainers currently state that critical maintenance runs through **May 5, 2027**, with new work focused on Zensical. The official announcement describes the forthcoming Zensical 0.1.0 release on November 5, 2026; this report does not treat that future milestone as already shipped. Recheck support dates during implementation. [Official transition announcement](https://zensical.org/upcoming-changes/)

| Option | Fit for SASE | Decision |
| --- | --- | --- |
| Improve content and navigation on current Material/MkDocs | Lowest disruption; preserves the existing checks and publishing outputs | Use for the first content releases, with a dated transition plan |
| Zensical using existing Markdown and configuration | Preferred successor candidate; minimizes content translation and permits parallel evaluation | Adopt after compatibility is demonstrated |
| Astro Starlight | Credible alternative for a more deliberate site rebuild; adds Astro/Node ownership and content/template conversion work | Fallback if the compatibility trial exposes durable blockers |
| Hosted documentation service | Could replace infrastructure, but introduces a separate publishing and content-governance decision | No demonstrated need to choose it for this project |
| Custom application or documentation engine | Maximum control, accompanied by substantial ongoing ownership | Reject for the present goals |

Zensical's official migration guide supports evaluating the same `mkdocs.yml` alongside the existing builder and specifically recommends keeping production unchanged until representative pages, search, and dependencies have been checked. It notes template-engine and CLI differences, including lack of the current `--site-dir` CLI option. This matters to SASE's isolated PDF build script. [Zensical migration guide](https://zensical.org/docs/compatibility/mkdocs/migration/)

Its compatibility documentation lists blog, redirects, RSS, and search support, with behavioral differences. I did not find `mkdocs-exporter` in that supported-plugin page. That is **an unverified dependency**, not proof that a PDF solution is impossible. [Zensical plugin compatibility](https://zensical.org/docs/compatibility/mkdocs/plugins/)

A bounded compatibility trial should compare:

- Normal pages, tables, code, admonitions, raw homepage HTML, and metadata overrides.
- Existing blog paths, RSS contents, redirects, and representative fragment links.
- Desktop and mobile navigation, keyboard access, dark/light themes, and search queries.
- Strict link validation, Cloudflare static output, and the deployment smoke checks.
- The full PDF path: temporary output configuration, exporter behavior, numbering, covers, post-processing, and validation.

Prefer plain Markdown and small presentation overrides during the redesign. Do not build more custom Material-specific components while preparing to leave it.

[Starlight](https://starlight.astro.build/) supplies a documentation-oriented baseline with navigation and search. It remains a legitimate fallback, but a new theme cannot decide page purpose or shorten the learning journey. A hosted service or paid authoring product is not required to apply the proposed editorial model.

The handbook deserves a separate product decision. A selected learning handbook plus web reference may eventually serve readers better than binding the entire evolving corpus and blog into one PDF. Preserve the current download route during this work; changing handbook scope or separating its release cadence should be explicit, rather than an accidental consequence of a renderer migration.

## 9. Enough process to keep the result coherent

Keep documentation in the SASE repository, reviewed with the behavior it describes. Start with one short contributor policy and four templates, rather than a new documentation database.

For each authored page, record a title, useful description, dominant type, and audience. A small frontmatter convention is sufficient, for example:

```yaml
title: Add an existing repository
description: Register a repository and verify that SASE can launch work against it.
kind: how-to
audience: user
```

These are proposed metadata fields, not current renderer features. Do not add fields without a concrete use. Review dates should mean that somebody actually checked the page; automated edits must not masquerade as verification. Track owners by broad area in the contributor policy instead of building a comprehensive per-fact graph.

Templates should enforce different contracts:

- Tutorial: starting state, concrete result, prescribed steps, expected observations, finish, next lesson.
- Guide: user problem, prerequisites, solution, verification, relevant recovery branch.
- Concept: question, mental model, relationships, reasons/tradeoffs, related tasks.
- Reference: scope/version, syntax or schema, defaults, constraints, examples, related guides.

Use one canonical location for volatile facts. Generate mechanical inventories from real command/configuration/model definitions where the source supports reliable generation. Existing model-table generation is a useful precedent. Author the learning narrative and explanations; generated command help is insufficient for those jobs.

Add a small change-review checklist: What user-visible behavior changed? Which document owns it? Does a tutorial or guide need updating? If no documentation changes are necessary, why? A feature should not acquire a permanent homepage card simply because it is new.

Retain strict site builds and existing generated-content validation. During migration, add meaningful checks for moved links, preserved anchors, and a few important complete journeys. For the priority tutorial, deterministic CLI/UI fixtures can check stable behavior; separately run occasional real-provider walkthroughs because a simulated provider cannot establish authentication and production routing correctness. Do not make every documentation build spend provider tokens.

Some current tests assert exact tutorial wording about provider selection. When content moves, move those behavioral requirements to their canonical reference and update the tests deliberately. Leaving prose tests attached to the old tutorial can force implementation detail back into the beginner path.

Make page purpose and correctness review separate questions. A technically correct paragraph can still belong on a different page.

## 10. Long-term SASE-agent maintenance, kept proportionate

Build on the existing update → polish workflow rather than introducing a new orchestration system. Change its unit of work from “refresh all documentation” to a scoped change with a named audience, type, affected behavior, and canonical destination.

The updating agent should provide evidence for changed commands and outputs, identify duplicates it removed, and explain whether a beginner page actually needs touching. The reviewing agent should check both correctness and whether the edit preserves the page's contract. Repeated runs with no relevant change should produce no content change.

Agents can efficiently find broken links, drift in generated reference, stale provider instructions, and oversized mixed-purpose sections. Keep primary navigation, homepage positioning, and core learning-path changes subject to an editorial decision. Automation should maintain that architecture rather than repeatedly inventing a new one.

Do not prioritize a documentation knowledge graph, retrieval system, autonomous taxonomy management, or AI support widget before the human-readable corpus and task routes work well. The initial agent-maintenance improvement is a narrower assignment and a better review rubric.

## 11. Rollout and evidence of improvement

### First increment: prove one better journey

Rewrite the homepage routing and first-run tutorial. Remove migration and internal contracts from beginner navigation while keeping them reachable through their proper sections. Add a compact documentation landing/index and a task-oriented Guides entry. Preserve existing URLs wherever possible.

Test this against a handful of developers unfamiliar with SASE. Observe whether they can explain what SASE adds, choose the first action, locate the result, and describe where the run happened. Use those observations to tune labels before reorganizing the entire corpus.

### Second increment: repair high-value discovery and reference

Split the TUI and configuration manuals along meaningful boundaries. Extract guides for connecting a repository, choosing/authenticating a provider, reusing a prompt, handing off a result, inspecting changes, and diagnosing a failed run. Publish Concepts only where a relationship needs explaining.

Move contributor contracts and internal details into the contributor area. Make configuration and command reference ownership explicit. Update README and support links to the new canonical destinations.

### Third increment: switch renderer after the compatibility gate

Run the Zensical trial alongside the content changes. Switch once the existing outputs and priority journeys have equivalent behavior. If there is a durable blocking dependency, choose a documented replacement or evaluate Starlight against the same acceptance cases. Set the decision early enough to allow implementation before Material's announced maintenance end.

### Continuous maintenance: small changes with visible outcomes

Apply the templates and review checklist to subsequent feature work and refresh agents. Do not block ordinary maintenance waiting for all 518,000 source words to be classified.

For moved content, create a source-path and anchor inventory before extraction. A whole-page redirect cannot, by itself, determine which of several new pages an old URL fragment should reach: the fragment is not sent in the HTTP request. Use tested fragment-aware redirects or compatibility pages retaining the important old anchors and linking directly to their replacements. Do not redirect a detailed configuration link to a generic section index and count that as compatibility.

Use these acceptance measures as initial targets to validate, not as claims already achieved:

| Test | Initial target |
| --- | --- |
| New reader chooses the correct route for a named task | At least 4 of 5 in a small observed round; investigate every failure |
| First-run tutorial | Complete one run and identify its result without visiting advanced reference; time installation/authentication and provider latency separately |
| Common task discovery | Correct landing page within roughly 30 seconds in the observed round |
| Expert lookup | Find a named command flag or setting without a long manual scan |
| Compatibility | Priority old URLs and fragments reach their specific replacements; canonical links resolve |
| Accessibility/responsiveness | Keyboard operation and focus, readable content at narrow widths/zoom, useful image alternatives, both color schemes |
| Maintenance | No duplicated volatile fact introduced; examples and generated references match their declared version |

A small round is formative feedback, not statistical proof. Compare old and proposed routes for the same tasks. Add aggregate search/no-result and feedback information only if it will drive decisions; page views alone cannot distinguish a useful page from a confusing one.

## 12. Risks and the conditions that would change this recommendation

- **Four-mode navigation feels abstract to users.** Keep the editorial distinctions, but test plainer task routes on landing pages. Users do not need to know the framework's name.
- **Too many tiny pages create navigation overhead.** Keep complete tasks and reference families together; merge pages when readers repeatedly need to alternate between them.
- **Expert users lose trusted bookmarks.** Preserve specific URL/anchor paths and provide an explicit command/settings index during transition.
- **The simple first experience conceals real product complexity.** State prerequisites and side effects at the point of action. If real-repository onboarding still demands excessive decisions, identify that as a product-onboarding issue rather than writing an ever-longer tutorial.
- **Version drift undermines otherwise good content.** Choose and display an applicability policy before building a multi-version archive. Add versioned docs only when supporting distinct versions creates an actual need.
- **Renderer work consumes the content effort.** Time-box compatibility assessment and publish the first journey on the working stack. Keep renderer acceptance separate from editorial acceptance.
- **Agents keep expanding documentation.** Give them explicit scope, canonical destinations, and permission to remove or relocate duplication. Review usefulness as well as correctness.

If SASE discovers several genuinely separate product audiences or a requirement for non-Git editorial authors, the one-repository approach may need reconsideration. Neither requirement is established by this audit.

## Recommended solution

**Simplify sase.sh around a first successful run and task-based discovery, using Diátaxis to keep tutorials, guides, concepts, and reference distinct.** Keep detailed documentation, split the oversized manuals, and give contributors and operators clear destinations. Retain Markdown beside the code, add a small editorial contract and targeted verification, and narrow the existing agent-refresh workflow to maintain those decisions.

**Ship the first content improvements on the current stack, then move to Zensical once a representative compatibility trial passes, with Starlight as the fallback.** Treat Material as a short-term bridge because its announced maintenance horizon is finite. This gives SASE a simpler learning experience and a maintainable documentation process without turning documentation reform into a custom-platform project.
