# Simplifying sase.sh with Diátaxis: documentation structure, site UX, and process

Researcher: mus (independent swarm report, suffix `__mus`)
Date: 2026-10-15
Sources inspected directly: `mkdocs.yml` nav + theme config, `docs/index.md`,
`docs/getting_started.md`, headers/word counts of all 55 `docs/*.md` files,
`docs/configuration.md`, `docs/architecture.md`, `docs/ace.md`, `docs/beads.md`,
`docs/macros.md`, `docs/notifications.md`, `docs/llms.md`, `docs/axe.md`,
`docs/cli.md`, `wrangler.jsonc`, `docs/_redirects`, `requirements-docs.txt`,
`docs/blog/posts/`, `docs/images/`; https://diataxis.fr and its
Tutorials / How-to guides / Reference / Explanation / Applying Diátaxis /
Workflow (`how-to-use-diataxis`) pages.

## 1. Executive summary

The plan — radically simplify sase.sh while adding structure, using Diátaxis for
inspiration — is a good idea and targets the real problem. The evidence supports it:

- sase.sh is a 55-page, ~516,000-word MkDocs Material site where **5 files hold
  roughly half the words** (`ace.md` ~103k, `configuration.md` ~71k,
  `macros.md` ~32k, `beads.md` ~28k, `llms.md` ~27k). This is not a
  too-many-pages problem; it is a **mega-page + mixing problem**.
- The current nav buckets — Getting Started / The Basics / Beyond the Basics /
  The Nitty Gritty / Integrations / Reference — describe the *author's* sense of
  difficulty, not the *reader's* goal. A newcomer asking "how do I retry a failed
  agent?" has no reliable bucket to open.
- Nearly every large page mixes all four Diátaxis modes on one page: tutorial
  prose ("What you just did"), how-to steps, exhaustive reference tables, and
  conceptual explanation. That mixing is exactly what Diátaxis diagnoses, and it
  is why search-and-scroll feels heavy even though the content is genuinely good.

Recommendation in one paragraph: **keep MkDocs Material, keep the content, change
the information architecture.** Adopt Diátaxis as the top-level structure
(Tutorials / How-to guides / Reference / Explanation, plus a thin Concepts layer
only if needed), split the five mega-pages along mode boundaries rather than
rewriting them, rewrite the homepage around four jobs-to-be-done entries plus one
guided path, cap reference pages with generated content where possible, and govern
all of it with a lightweight per-page contract (one Diátaxis type, one audience,
one tested entry point). Migrate iteratively page-by-page per the Diátaxis
workflow — never as a big-bang "four empty folders" restructure. Details in §7.

## 2. What Diátaxis actually says (and what it does not say)

Diátaxis (https://diataxis.fr) identifies four user needs and four matching
documentation forms, arranged on two axes (study vs. work, theory vs. practice):

| Form | Orientation | Answers | Shape |
|---|---|---|---|
| Tutorial | learning, practical | "Can you teach me?" | A guided lesson with guaranteed success; learner does, teacher takes responsibility |
| How-to guide | working, practical | "How do I …?" | Steps toward one named user goal; assumes competence, skips teaching |
| Reference | working, theoretical | "What is … / what are the flags?" | Austere, complete, consistently patterned description ordered by the machinery |
| Explanation | learning, theoretical | "Why / tell me about …?" | Discursive context that joins things together; readable away from the product |

Three properties matter most for sase, and all three are directly supported by the
fetched Diátaxis pages:

1. **Mode purity beats folder purity.** Each page should serve one need. A page
   that teaches *and* lists every flag *and* explains the design fails all three
   readers. The fix is usually splitting, not relocating.
2. **Adopt it as a guide, not a plan.** The Diátaxis workflow page is explicit:
   do not create four empty sections and backfill them ("it's horrible"). Work
   one page at a time with the compass ("is this teaching, tasking, describing,
   or explaining?"), let the top-level structure emerge from improved pages.
3. **How-to guides are framed by user goals, not tool operations.** "How to use
   fixtures in pytest" qualifies; a tour of every knob does not. sase's current
   pages are overwhelmingly machinery-framed (`ace.md` has ~209 `#` headings
   walking the TUI widget-by-widget). Diátaxis would reframe them as
   goal-framed guides ("retry a failed run", "hand off a patch between agents").

What Diátaxis does *not* give you: audience segmentation (new user vs. contributor
vs. agent consumer of docs), landing-page UX, search/versioning policy, or
governance. sase needs all four, so the recommendation below is
"Diátaxis-at-the-core plus a thin surrounding system," not "Diátaxis everywhere."

## 3. Current-state audit: where sase.sh actually hurts

Counts below are measured from this checkout (word counts via `wc -w`).

### 3.1 The corpus is top-heavy

- 55 `docs/*.md` files, ~516k words total.
- Top 5 files ≈ 261k words (~51%): `ace.md` 103k, `configuration.md` 71k,
  `macros.md` 32k, `beads.md` 28k, `llms.md` 27k. Next: `notifications.md` 19k,
  `axe.md` 17k, `cli.md` 15k.
- `ace.md` alone carries 209 headings; `macros.md` 139; `llms.md` 170. These are
  books, not pages. No nav affordance (sections, indexes features are on, but
  they only mitigate) fixes a 100k-word page.
- Consequence for the "simplify" goal: deleting or merging small pages barely
  moves the needle. The project is splitting 5 pages into ~25, not rearranging 55.

### 3.2 Every large page mixes modes

Spot-checked headers confirm the mixing pattern:

- `ace.md`: Overview (explanation) → Launching (tutorial-ish) → CLI Options
  table (reference) → Examples (how-to) → per-tab keymaps (reference) → recovery
  runbooks (how-to) → profiling paths (reference). One page, all four quadrants.
- `beads.md`: Quick Start (tutorial) → Data Model / Storage / Sealed Segments
  (explanation + reference) → CLI Commands (reference) → TUI Integration
  (how-to-ish). Same mixing.
- `macros.md`, `llms.md`, `notifications.md`, `axe.md`: identical shape —
  tutorial intro, then reference tables, then conceptual asides, then runbook
  steps, with hand-maintained Tables of Contents papering over the seams.
- `getting_started.md` (~4.1k words) is a good tutorial draft but violates the
  tutorial contract in two Diátaxis senses: it explains too much inline
  (provider alias routing, workspace normalization theory) instead of keeping the
  learner moving, and its success is not self-verifying at each step.

### 3.3 The nav encodes insider difficulty, not reader intent

`Getting Started / The Basics / Beyond the Basics / The Nitty Gritty /
Integrations / Reference` fails three ways:

- **Unpredictable membership.** Why is Memory "basic" but Beads "beyond"? Why is
  Performance a "runbook" but Agent Revival "troubleshooting"? A new user cannot
  predict where their question lives.
- **Jargon labels.** Ace, Axe, Beads, SDD, Patches-as-changespecs are product
  terms a pre-user does not have yet. Labels should carry a plain-language
  gloss until the vocabulary lands (Diátaxis explanation pages are where the
  vocabulary *is* taught — the nav should not assume it upfront).
- **Reference is a junk drawer.** `cli.md` (a routing index, genuinely useful),
  `development.md` (contributor guide), `configuration.md` (71k-word
  everything-manual), and `acknowledgements.md` share one section. Reference
  should be ordered by the machinery and be exhaustive; today it is neither.

### 3.4 The homepage tries to do four jobs at once

`docs/index.md` (~921 words plus a 4→6 role-card grid, hero, PDF/launch-post
buttons) simultaneously pitches the product ("One prompt is not an engineering
system"), onboards by role ("I am setting up a repo…"), and indexes the docs.
The role cards are the right instinct but they point at mega-pages ("Open sase's
TUI guide" → 103k words), so the click after the promising card is where users
drown. The "Download PDF / Launch Post / View on GitHub" button row competes
with the single most important action (start the 15-minute tutorial).

### 3.5 Process gaps that recreated the problem

- No per-page contract: no frontmatter declaring type/audience/owner, so every
  edit appends to the nearest mega-page.
- `mkdocs.yml` uses `strict: true` (good) but no link checker, no heading/word
  budget, no Vale/markdownlint gate is visible in the inspected config — so
  bloat has no friction.
- Reference content (`configuration.md`, CLI flags, provider matrices) is
  hand-maintained prose, which drifts from the CLI it documents. Diátaxis
  reference wants to be generated or generated-checked wherever possible.

## 4. Critique of the plan

**Is this a good idea? Yes — with three adjustments (called out explicitly).**

Strengths of the plan as stated:

- "Simpler *and* more structured" sounds contradictory but is exactly right for
  this corpus: fewer words per page, more predictable places to put them.
- Reaching for Diátaxis rather than a bespoke taxonomy avoids inventing new
  jargon for a docs system that already suffers from jargon.
- De-prioritizing agentic management as the focus is correct sequencing (see
  adjustment 3 below).

Weaknesses / risks:

1. **"Drastically simplify" is the wrong verb; "split and sharpen" is the goal.**
   A mandate to cut can destroy the long-tail reference content that power users
   and agents rely on (`llms.md` provider quirks, `configuration.md`
   completeness). The audit shows the problem is density-per-page, not total
   coverage. Measure words-per-page and task-success, not total words.
2. **Diátaxis-as-four-folders is the most likely failure mode.** If the project
   creates `tutorials/ how-to/ reference/ explanation/` and bulk-moves files,
   every existing link, bookmark, `sase.sh` SEO entry, and agent prompt that
   cites a docs URL breaks for zero reader benefit, because the pages inside are
   still mixed. The Diátaxis authors warn against exactly this.
3. **Two audiences are being conflated.** sase.sh serves (a) humans learning and
   operating sase and (b) contributors/agents needing exact contracts. Diátaxis
   organizes (a) beautifully; (b) needs generated reference + ADRs/changelog
   discipline that Diátaxis does not specify. Both ship on the same site but
   should be visually and contractually separated.

### Adjustments I am making to the requirements (explicit)

- **A1 — Keep MkDocs Material; do not replatform.** The request implies site
  changes but does not mandate a stack change. Material already provides the
  needed primitives (sections, indexes, search suggestions/highlight, social
  cards, redirects, blog, RSS). A replatform (Docusaurus/Astro/custom) would
  burn the budget that should go to content surgery. All recommendations below
  assume `mkdocs.yml` + Material + Cloudflare (`wrangler.jsonc` → `site/`).
- **A2 — Add a fifth visible bucket ("Concepts") only as Explanation's front
  door, not as a new Diátaxis quadrant.** Pure Diátaxis has four sections. sase
  newcomers need one guided conceptual spine (orchestration → work units →
  memory → providers → Rust core) before the quadrant grid makes sense. I
  recommend labeling it "Concepts" in the nav while contracting it as
  Diátaxis Explanation in frontmatter, rather than pretending sase has no
  conceptual on-ramp problem.
- **A3 — Treat agent-consumable docs as a derived artifact, not a fifth
  quadrant.** Long-term agentic management stays out of focus per instructions,
  but one decision should be locked now: agents consume `llms.txt`-style
  distillations and generated reference, never a parallel docs tree. Proposal in
  §7.9 is minimal and non-blocking on purpose.

## 5. What good looks like: precedents worth copying

- **Diátaxis's own site** (the fetched pages): each page declares its contract
  in the first lines ("Tutorials … learning-oriented"), keeps pages short, and
  cross-links quadrants instead of inlining them. Copy the habit of a
  one-sentence contract header per page.
- **Kubernetes / Django / Stripe-style docs** (general knowledge, not
  re-verified here): task-index landing ("I want to …"), strict
  tutorial-vs-how-to separation, generated CLI/API reference kept out of guides.
  sase's `cli.md` already gestures at the routing-index pattern ("This page is a
  discovery index, not a dump of every flag") — promote that pattern
  site-wide rather than inventing a new one.
- **Docs-as-code governance**: `strict: true` builds plus link checking,
  per-page frontmatter (`type`, `audience`, `tested`), and word/heading budgets
  on guides. sase has the first; needs the rest.

## 6. Proposed sase.sh information architecture

Top-level nav after migration (names are deliberate — plain language first,
product term second where unavoidable):

1. **Start here** (2 pages): landing + "Your first 15 minutes" (true tutorial,
   rewritten to the tutorial contract).
2. **Tutorials** (4–5 total, each a guaranteed-success lesson): first agent run;
   first TUI session; first durable work unit (patch + bead); first reusable
   automation (macro → workflow). Each ends with "you now have X and can find
   it at Y."
3. **How-to guides** (~25–35, one user goal each, extracted from mega-pages):
   e.g. install a provider; retry/resume a failed run; hand a patch between
   agents; schedule a routine; triage a notification gate; configure one section
   of `sase.yml`; dispatch to a remote machine; capture agent screenshots. No
   guide over ~1,500 words; anything longer is two guides.
4. **Reference** (generated or tightly patterned): CLI index (`cli.md`, kept),
   per-command flag pages (generated from `--help` where feasible),
   configuration schema (split `configuration.md` by section, generated-checked
   in CI), query language, keymaps, environment variables, Rust-core boundary
   contract. Austere tone, no teaching, no storytelling.
5. **Concepts / Explanation** (~10): why orchestration; Patches vs. Beads vs.
   Goals; workspaces and isolation; memory model; providers and model tiers;
   service host (Axe) mental model; Rust-core boundary; SDD storage. This is
   where "Ace / Axe / Beads / SDD" vocabulary is taught — once, with diagrams
   reused from `docs/images/`.
6. **Contribute** (split out of Reference): development setup, commit workflows,
   architecture-for-contributors, docs process itself. Keeps user reference
   clean and signals "you can stop reading here" to non-contributors.
7. **Blog/Changelog** (kept, de-emphasized in nav): launch post, release notes
   surface; no how-to content lives only in a blog post.

Mapping of today's worst offenders (illustrative, not exhaustive):

| Today | Becomes |
|---|---|
| `ace.md` (103k) | 1 tutorial (first TUI session) + ~6 how-tos (query, palette, launch control, screenshots, …) + 1 keymap/command reference + 1 "TUI mental model" concept |
| `configuration.md` (71k) | Per-section reference pages (generated-checked) + ~4 how-tos ("configure X") + admin-center guide |
| `macros.md` (32k) | 1 tutorial + syntax/format reference + directives reference + ~4 how-tos |
| `beads.md` (28k) | 1 concept (issue model) + lifecycle/storage reference + ~4 how-tos |
| `llms.md` (27k) | 1 concept (provider architecture) + per-provider reference cards + ~3 how-tos |
| `getting_started.md` | Rewritten as the flagship tutorial; current explanatory asides move to Concepts or How-tos |

## 7. Recommended solution (phased, iterative)

### 7.1 Phase 0 — Lock the contract (small, first)

- Adopt per-page frontmatter for every docs page: `type:` (one of
  `tutorial|how-to|reference|explanation`), `audience:` (`new|user|contributor`),
  `tested:` (how the page's claims are verified), `owner:` ( rotation or team).
- Add three CI gates to the existing `strict` build: internal/external link
  check, guide word budget (warn >1,500 words for how-tos/tutorials), and a
  "mega-page ratchet" (any edit that grows `ace.md`/`configuration.md` beyond
  current bytes fails with a pointer to this plan). These gates *are* the
  "documentation process structure" the request asks for, at minimal ceremony.
- Freeze URL policy: all moves go through `docs/_redirects`-style redirect maps
  (already in use for `/xprompt/ → /macros/`); no link breaks without a 301.

### 7.2 Phase 1 — Homepage + Start-here (highest UX leverage, lowest risk)

- One hero action: "Get started in 15 minutes." Demote PDF/GitHub/launch-post
  to secondary links.
- Replace the 6+ role cards with two elements: (a) the four-quadrant entry
  ("Learn / Do / Look up / Understand"), each one line; (b) a task index of the
  top ~12 "I want to …" links backed by real how-tos. Cards must land on pages
  under ~2k words — fix the landing pages before advertising them.
- Add per-section contract sentences ("Tutorials teach by doing…") so users learn
  the system by using it.

### 7.3 Phase 2 — Split the five mega-pages in place (the core work)

Follow the Diátaxis workflow per page: run the compass on each `##` section,
extract reference tables into reference pages, extract goal-directed steps into
how-tos, move teaching narratives into tutorials, move "why" into Concepts —
*before* changing the nav. Ship each split as its own reviewable change with
redirects. Order by read frequency and pain: `ace.md` → `configuration.md` →
`macros.md` → `llms.md` → `beads.md` (front-door order, not alphabetical).

### 7.4 Phase 3 — Reference generation (kills drift)

- Generate CLI flag tables from the CLI (`--help`/schema) or verify prose
  against them in CI; same for config schema sections and env vars.
- Keep `cli.md`'s routing-index role and extend the pattern: every subsystem
  header gets a 3-line "where to go" block instead of duplicating content.

### 7.5 Phase 4 — Search, discovery, and trust UX

- Keep Material search but tune it: index-boost tutorials/how-tos over
  reference, verify `search.suggest`/`search.highlight` behavior on the top 20
  queries, add a curated "no results → try…" fallback is out of scope; instead
  ensure the task index covers those queries.
- Add "Was this helpful?" affordance per guide (even a link to file an issue
  with the page prefilled) and surface last-verified version on tutorials.
- Ship `llms.txt` (and per-section variants) as a build artifact from the same
  source — this is the entire agent-consumable-docs story for now (per A3).

### 7.6 What explicitly not to do

- No replatform, no new CSS design system, no versioned-docs sprawl yet (one
  version + changelog until a release demands versions).
- No four-empty-folders restructure; no total-word-count goal; no migration of
  blog how-tos into guides without an owner per moved post.
- No agent-owned docs pipeline in this phase beyond `llms.txt` + frontmatter.

### 7.7 Effort sketch

Phase 0 (~days), Phase 1 (~1 week incl. homepage), Phase 2 (the bulk: ~1–2 weeks
per mega-page if done with care, parallelizable per page), Phase 3 (~1–2 weeks
tooling), Phase 4 (ongoing tuning). A thin vertical slice — homepage + one fully
split page (`macros.md` is the best first candidate: mid-size, high-value,
self-contained) — should land first as proof of the pattern before committing to
all five.

### 7.8 How success is measured

- Task success: can a new user complete the 15-minute tutorial without leaving
  it? (instrument via docs feedback + success checklist, not surveillance).
- Findability: top-20 support questions each resolve to exactly one guide.
- Page health: zero pages over budget except enumerated reference; zero
  mixed-mode pages among tutorials/how-tos (compass spot-checks).
- Freshness: every tutorial re-verified per release; reference generation green.

### 7.9 Agentic management (deliberately minimal, per scope)

Record, do not build: frontmatter `type:` is machine-readable by construction;
`llms.txt` derivation keeps agents on the same source as humans; per-page
`owner:` + `tested:` fields are the hooks a future agent-maintainer flow will
need (stale-page detection, fix proposals). No agent write-access to docs,
no docs-generation pipeline, and no memory-web coupling until the human-facing
 restructure has landed and held for one release cycle.

## 8. Verdict restated

Yes, do this. The Diátaxis-inspired simplification addresses the documented
failure (dense mixed-mode mega-pages behind insider-labeled buckets), the fix
preserves what is good (deep, accurate content; Material; strict builds;
redirect discipline), and the iterative method de-risks it. The adjustments
above — split-don't-delete, guide-not-plan migration, Concepts gloss, agents as
derived consumers, no replatform — are the difference between a docs project
that lands and one that churns URLs for a quarter.
