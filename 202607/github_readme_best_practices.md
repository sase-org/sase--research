# GitHub README Best Practices — Research and Recommendations for the sase README

Date: 2026-07-17

## Recommendation

**Keep the current README's shape. Fix its omissions.**

The README was rewritten on 2026-07-17 (`ac92d6ade`, −301/+57), cutting it from ~353 lines to 109. That was the right
call, and this report does not argue for undoing it. At 109 lines sase sits in the **landing-page archetype** alongside
goose (63 lines), OpenHands (150), and aider (180) — the correct shape for a project whose docs site carries ~40 pages.
The temptation after research like this is to bolt on every section some spec recommends. Resist it. `makeareadme.com`
says "too long is better than too short"; GitHub's own docs say the opposite and GitHub is right for this project.

What the README is actually missing is not sections but **facts**: it never says sase is Alpha, never says it is
POSIX-only, never expands its own acronym, never links the `CONTRIBUTING.md` that already exists, and ships ~7 MB of
media that renders broken on PyPI. Every one of those is a small, high-confidence fix that preserves the current
minimalism.

The highest-value single change is unglamorous: **link `CONTRIBUTING.md` and state the project's Alpha status.** Those
two are the cheapest wins available and are the two best-evidenced findings in the entire literature (see §3).

---

## Method and scope

Four parallel research tracks: canonical/normative guidance, empirical and academic literature, a structural teardown of
eight peer project READMEs, and a factual audit of sase's own README and docs. Peer READMEs were read from local
checkouts opened via `sase repo open gh:<owner>/<repo>`, not web-fetched, so quotes come from source files.

Three premises I started with turned out to be **wrong** and are corrected in place below rather than quietly dropped.
This matters because all three circulate widely and look sourced when they aren't:

1. **Diátaxis says nothing about READMEs.** The "README as front door, per Diátaxis" framing is unattributable.
2. **Steinmacher does not find documentation is the top newcomer barrier.** Socialization barriers are.
3. **There is no eye-tracking study of READMEs.** "Above the fold" for READMEs is unmeasured.

---

## Ground truth: what the sase README is today

**109 lines · 552 words · 5.2 KB.** Outline: `# sase` → `## Why sase` → `## See it in action` → `## Quick start` →
`## Works with your agents` → `## Learn more` → `## Development` → `## Acknowledgements` → `## License`.

Verified facts:

- **Zero broken links.** All 7 relative paths resolve and are git-tracked; all 11 `sase.sh` URLs return HTTP 200 and map
  to real `mkdocs.yml` nav entries. This is in better shape than most projects.
- **Media payload: 7.03 MB** on every view — `sase_overview.png` (1.35 MB) + three GIFs (3.84 / 1.07 / 0.77 MB). All
  three GIFs are 1920×1080 sources displayed at `width="830"` (~2.3× oversized). No file breaches GitHub's ~10 MB limit.
- **Smaller variants already exist and are unused:** `docs/images/blog/` holds 1280×720 copies of the same demos
  (fan-out: 1.7 MB vs 3.84 MB), and every GIF has an `.mp4` twin 1.5–2.7× smaller.
- **`CONTRIBUTING.md` is a complete orphan** — referenced by zero files in the repo (verified by grep across
  `README.md`, `docs/*.md`, `mkdocs.yml`).
- **Absent:** `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE`, `.github/PULL_REQUEST_TEMPLATE.md`.
  `.github/` contains only workflows (`ci.yml`, `docs-deploy.yml`, `pr-title.yml`, `publish.yml`).
- **Claims match reality where stated.** The 5-agent table matches the 5 user-facing `sase_llm` entry points (`fakey`
  correctly omitted); "Python 3.12+" matches `requires-python`.
- **Facts omitted:** `Development Status :: 3 - Alpha`, `Operating System :: POSIX` (no Windows), the `git` and
  `$EDITOR` requirements from `INSTALL.md`, and the expansion of "SASE" (the README gives the pronunciation "sassy" but
  never says *Structured Agentic Software Engineering* — which is the package's own one-line description).
- **Surfaces 8 of ~40 doc pages.** The blog (10 posts) and the PDF handbook (`/downloads/sase-handbook.pdf`, built and
  smoke-tested in CI) are entirely unsurfaced.

---

## §1. Canonical guidance

### GitHub's own docs — the only normative source that matters for scope

[About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)
prescribes no section list. It prescribes five *questions*: what the project does, why it's useful, how to get started,
where to get help, who maintains it. Its one hard scope rule, verbatim:

> "A README should only contain information necessary for developers to get started using and contributing to your
> project. Longer documentation is best suited for wikis."

That sentence is the strongest named-source backing for the routing model, and it endorses sase's current minimalism.

The [community health file](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
taxonomy is also load-bearing: GitHub's own file layout says support, security, governance, and contribution mechanics
belong in *sibling files*, not in the README. The README links to them. sase does this correctly for `INSTALL.md` and
`LICENSE`, and fails to for `CONTRIBUTING.md`.

### standard-readme — prescriptive, but self-scoped to libraries

[spec.md](https://github.com/RichardLitt/standard-readme/blob/main/spec.md) is the only source with machine-checkable
MUSTs, mandating 16 sections in order: Title → Banner → Badges → Short Description → Long Description → TOC → Security →
Background → Install → Usage → Extra → API → Maintainers → Thanks → **Contributing (required)** → **License (must be
last)**.

**Do not adopt this wholesale.** It self-scopes: *"Standard Readme is designed for open source libraries."* Its Node/npm
heritage shows (title-must-match-package-name, description-must-match `package.json`). Several hard requirements are
inapplicable to a CLI application. Its TOC-required-above-100-lines rule also predates GitHub's auto-generated heading
TOC and is now largely obsolete.

Two rules worth borrowing anyway: **short description under 120 characters, matching the package manager's description
field**, and **Contributing is required**.

### Art of README — the best-argued ordering, and it contradicts standard-readme

[art-of-readme](https://github.com/hackergrrl/art-of-readme) prescribes Name → One-liner → **Usage** → API →
**Installation** → License, and gives the only real ordering rationale in any source:

> "The ordering presented here is lovingly referred to as 'cognitive funneling'... the ordering of these key elements
> should be decided by how quickly they let someone 'short circuit' and bail on your module."

**Order sections by disqualification speed, not workflow order.** Install is late because nobody installs before
deciding. This is a genuine disagreement with standard-readme/makeareadme (which order by workflow: install, then use),
and it's a disagreement about *reader model*. For a tool discovered via search or a link — sase's situation —
disqualification order is better calibrated.

Its other positions, both relevant to sase:

- **Brevity:** *"The ideal README is as short as it can be without being any shorter."*
- **Badges, skeptically:** *"They add visual noise... For each badge, consider: 'what real value is this badge providing
  to the typical viewer of this README?'"*
- **Images:** *"Doesn't rely on images to relay critical information"* — because *"your version control repository and
  its embedded README will outlive your repository host and any of the things you hyperlink to."*

### Other sources, briefly

- **JOSS review checklist** ([link](https://joss.readthedocs.io/en/latest/review_checklist.html)) — the only source
  making **"Statement of need"** a named, reviewable artifact: *"Do the authors clearly state what problems the software
  is designed to solve and who the target audience is?"* sase's `## Why sase` already serves this.
- **CNCF project-template** ([link](https://github.com/cncf/project-template/blob/main/README-template.md)) — uniquely
  prescribes an explicit **`Out of Scope`** section. No other source has this. sase's *"sase does not replace coding
  agents"* line is a compressed version of the same move.
- **makeareadme.com** — contributes **Visuals**, **Roadmap**, **Project status** as first-class sections. Project status
  is not in any other source and is genuinely useful signal.
- **awesome-readme** — *not guidance*. It's a gallery with a visual-maximalist bias (logos, emoji, avatar walls) that
  runs directly against GitHub's and Art of README's scope advice. Citing it as authority means citing a popularity
  aesthetic.

### Where the sources genuinely disagree

| Question | Position A | Position B |
|---|---|---|
| Install before Usage? | Install first — standard-readme, makeareadme, CNCF | Usage first, Install 5th — Art of README |
| License placement | "Must be last" — standard-readme | "might be better higher up" — Art of README |
| Length | "Too long is better than too short" — makeareadme | "as short as it can be" — Art of README; "only what's necessary" — GitHub |
| Badges | Unquestioned section #3 — makeareadme | "visual noise... easy to abuse" — Art of README |
| Images/GIFs | Visuals = section #4 — makeareadme | "Doesn't rely on images to relay critical information" — Art of README |
| Contributing | Required *section* — standard-readme | Separate file, README links it — GitHub, CNCF, opensource.guide |

---

## §2. Peer teardown — eight developer tools

| Repo | Lines | Words | Demo media |
|---|---|---|---|
| `block/goose` | 63 | 276 | **none** |
| `All-Hands-AI/OpenHands` | 150 | 903 | 2 PNG |
| `Aider-AI/aider` | 180 | 1,156 | 1 screencast SVG |
| **`sase`** | **109** | **552** | **3 GIF + 1 PNG** |
| `astral-sh/uv` | 326 | 1,080 | 1 benchmark SVG |
| `charmbracelet/bubbletea` | 402 | 1,910 | 2 GIF, 1 PNG |
| `BurntSushi/ripgrep` | 541 | 2,874 | 2 PNG |
| `astral-sh/ruff` | 563 | 2,021 | 1 benchmark SVG |
| `jesseduffield/lazygit` | 637 | 3,646 | **15 GIF** |

### Three archetypes

- **Landing page (60–200 lines):** goose, OpenHands, aider. Tagline + demo + minimal install + link list. Requires a
  docs site. **← sase is here, correctly.**
- **Funnel (300–560 lines):** uv, ruff. Tagline + chart + highlights + install + per-feature transcript, each ending in
  a docs link.
- **Manual (540–640 lines):** lazygit, ripgrep. Bloat is almost entirely the package-manager install matrix.

### Patterns common to ≥6 of 8

1. **Name + one-sentence tagline within the first 15 lines.** 8/8. Formula: `<superlative> <category>,
   <differentiator>` — uv's *"An extremely fast Python package and project manager, written in Rust."*; lazygit's *"A
   simple terminal UI for git commands."* Never a paragraph. sase complies.
2. **Badges immediately after title.** 8/8, 3–8 badges. Consistent set: version + license + CI + chat. **sase has no CI
   badge** despite four workflows.
3. **A visual within the first ~50 lines.** 7/8 — goose is the sole exception and it's conspicuous. Medium tracks value
   prop: speed → benchmark chart (uv, ruff); interaction → GIF (lazygit, bubbletea); UI → screenshot (OpenHands).
   sase complies.
4. **Install inline, minimal, then link out.** 6/8. Only lazygit and ripgrep inline the exhaustive matrix — both are old
   and both are worse for it. sase complies (4 commands, then links `INSTALL.md`).
5. **Features scannable and deep-linked.** 8/8.
6. **Docs site owns reference material; README is a funnel.** 6/8. **Nobody documents comprehensively in the README.**
7. **Social proof as a named section.** 6/8. Position varies wildly — ruff puts `## Testimonials` at #2, aider puts
   `## Kind Words From Users` last. **sase has none.**
8. **Terminal-native artifacts, never photos or mockups.** sase complies.

### Patterns worth stealing, ranked by fit

- **lazygit's feature-block triple** — heading / exact-keypress sentence / GIF. E.g. `### Cherry-pick`: *"Press
  `shift+c` on a commit to copy it and press `shift+v` to paste (cherry-pick) it."* → GIF. **This is the highest-value
  pattern in the set for a TUI**, and the one uv can't supply. It teaches the keymap and demos the feature at once.
  lazygit's GIFs are generated by an integration-test harness and all named `*-compressed.gif` — compression is a
  systematized step, not an afterthought. sase's demos are already VHS-tape-generated, so the harness exists.
- **ripgrep's `### Why shouldn't I use ripgrep?`** — the only explicit anti-sell in the set. Enormous credibility for
  near-zero cost.
- **uv's `## FAQ`** answering *identity* questions (*"How do you pronounce uv?"*, *"Is uv ready for production?"*)
  rather than troubleshooting. Directly relevant: sase has a pronunciation note and an unstated Alpha status.
- **OpenHands' sub-tagline naming interoperable competitors** — *"Run OpenHands, Claude Code, Codex, Gemini, or any
  ACP-compatible agent..."* For an orchestrator, "works with the agent you already use" is the positioning. sase already
  does this in its opening paragraph.
- **ruff's `<!-- Begin section: Overview -->` markers** — the README is the *source of truth* that gets sliced and
  embedded into the docs site. One copy, two renderings. The only *structural* solution to README/docs drift in the set.
- **aider's headings-as-links** — `### [Git integration](https://aider.chat/docs/git.html)`. The outline doubles as docs
  nav.
- **bubbletea's dependents-graph link** as self-updating, unfakeable social proof.
- **uv's `<picture>` with `prefers-color-scheme`** so visuals work in both GitHub themes.

**Anti-pattern observed:** lazygit's first 37 lines are paid sponsor banners before the project name.

---

## §3. Empirical evidence — and what it does *not* support

This is where most README advice overclaims. The honest summary is that **the evidence base is thin, correlational, and
in one case points the opposite way from the folklore.**

### The best-supported finding: the Why/status gap

**Prana, Treude et al., "Categorizing the Content of GitHub README Files,"** *Empirical Software Engineering* 24,
1296–1327 (2019). [arXiv:1802.06997](https://arxiv.org/abs/1802.06997). n=393 repos, 2 annotators, Cohen's κ=0.858.

Taxonomy: What, Why, How, When, Who, References, Contribution, **Other** (not "Status" — status content lives under
*When*).

| Category | % of files | % of sections |
|---|---|---|
| What | **97.0%** | 16.7% |
| How | 88.5% | **58.4%** |
| References | 60.8% | 20.3% |
| Who | 52.9% | 7.6% |
| Contribution | **27.8%** | 2.9% |
| **Why** | **25.7%** | 2.7% |
| **When** (status) | **21.4%** | 4.3% |

**Roughly 3 in 4 READMEs never answer "why should I care?" or "is this alive?"** Meanwhile *What* appears in 97% of
files but only 16.7% of sections — present but thin — while *How* sprawls to 58.4% of sections. A README that is 58%
install instructions and one line of "what" is the statistical norm.

**sase already wins on Why** (`## Why sase` + the positioning paragraph) — it's in the 25.7%. **It loses on status**,
sitting in the 78.6% that never say whether the project is alive or production-ready, despite `pyproject.toml` declaring
Alpha.

**Caveats:** the &lt;2KB filter deliberately excludes the most minimal READMEs, so the true "missing Why" rate is likely
worse. 2018 sample; GitHub has grown ~10× since. The paper's 20-professional survey measured *perceived* usefulness, not
task performance — the authors explicitly flag this. Any claim that Prana et al. showed better READMEs improve outcomes
is **not supported**.

### License and Contributing: rare, high-effect-size, two independent methods agree

**Liu, Noei & Lyons (2022), "How README Files are Structured in Open Source Java Projects,"** *Information and Software
Technology*. [PDF](https://enoei.github.io/papers/liu2022readme.pdf). n=11,594 English READMEs.

| Section | Present | Cliff's δ vs. stars |
|---|---|---|
| Contributing | **5%** | **0.415** |
| License | **13%** | **0.416** |
| Usage | 31% | 0.314 |
| Installation | 21% | 0.311 |
| Description | 41% | **0.039** |

**The striking result:** the sections with the *largest* effect sizes (License, Contributing) are the *rarest*. The most
common section (Description) has a negligible effect.

Independently, the [GitHub Open Source Survey 2017](https://opensourcesurvey.org/2017/) (n=5,500) found **64%** say a
license is very important in deciding whether to **use** a project and **67%** in deciding whether to **contribute** —
the top-rated document for both. Two different methods, same signal.

**This is the strongest available argument for the single cheapest fix on sase's list: link the orphaned
`CONTRIBUTING.md`.**

### ⚠️ Do not claim a good README drives adoption

**Gaughan, Champion, Hwang & Shaw (2025), "The Introduction of README and CONTRIBUTING Files in Open Source Software
Development,"** CHASE 2025. [arXiv:2502.18440](https://arxiv.org/abs/2502.18440). n=4,226 READMEs.

Measured: README median publication is the **same day as the initial commit**; CONTRIBUTING median is **1,806 days**
(~4.9 years) in. Docs get published around local maxima in contribution activity, and **weekly commit activity declines
afterward**. The authors state there is *"no evidence to support such causality"* — documentation **follows** activity
rather than causing it.

Every star correlation in §3 is confounded (Liu et al. raise this themselves: popular projects plausibly attract better
docs, not the reverse). The one study that tested temporal direction found the arrow pointing the wrong way. **Treat
"good README → more stars" as unproven.** The defensible claim is narrower: certain sections co-occur with popular
projects and are rare enough to be cheap differentiators.

Also measured by Gaughan: **median README reading time 14.79 seconds** (under 160 words). READMEs are short and are read
fast. sase's 552 words is ~3.5× the median — still firmly in "read in one sitting" territory.

### ⚠️ Three corrections to widely-repeated claims

**Documentation is not the top newcomer barrier.** Steinmacher et al.'s [systematic
review](https://www.ime.usp.br/~gerosa/papers/Steinmacher2014_Chapter_BarriersFacedByNewcomersToOpen.pdf) (OSS 2014, 21
studies; IST 2015, 20 primary studies) lists five barrier categories, and the most-evidenced are *"newcomers' previous
technical skills, receiving response from community, centrality of social contacts, and finding the appropriate way to
start contributing."* **Documentation is not among them**; socialization barriers appear in 75% (15/20) of studies. The
Documentation Problems category contains only *Outdated Documentation*, *Information Overload*, and *Code Comments not
Clear* — none about README first impressions. The information-overload finding actually cuts *against* comprehensive
docs: *"just providing a bunch of documentation leads to information overload."*

The real source of the folklore is the GitHub 2017 survey's *"incomplete or outdated documentation... observed by 93% of
respondents."* But 93% **observed** the problem — that measures pervasiveness, not severity ranking, and it's a
non-peer-reviewed self-report survey.

**"Above the fold" for READMEs is unmeasured.** No eye-tracking or attention study of READMEs or developer docs landing
pages appears to exist. [NN/g's scrolling research](https://www.nngroup.com/articles/scrolling-and-attention/) (57% of
viewing time above the fold, 130k+ fixations) studied **news, ecommerce, blogs, and FAQs — no developer
documentation.** Argue the fold from first principles if you like, but don't dress it in NN/g's numbers.

**Diátaxis says nothing about READMEs.** [diataxis.fr](https://diataxis.fr/) is a framework for organizing a
documentation *corpus* (tutorial / how-to / reference / explanation). It has no README prescription and no "front door"
framing. The README-as-minimal-slice-of-each-type mapping is a defensible inference, but it is **not attributable to
Diátaxis**. "README is the front door" appears only in blog and vendor content — rhetorically useful, not sourced.

### Agent-facing context files — early, unsettled, and mostly deflationary

Relevant because sase is itself an agent-orchestration tool that generates `AGENTS.md`/`CLAUDE.md` shims.

- **Chatlatanagulchai et al. (Nov 2025), "Agent READMEs: An Empirical Study of Context Files for Agentic Coding,"**
  [arXiv:2511.12884](https://arxiv.org/abs/2511.12884). n=2,303 context files / 1,925 repos. Content prevalence: Testing
  75.0%, Architecture 67.7%, Build and Run 62.3%, **Security 14.5%**, **Performance 14.5%**. Median 6–7 H2 sections — a
  near-exact match for Prana's median 7 README sections. Purely descriptive: measures what's *in* the files, never
  whether they work.
- **Gloaguen et al. (Feb 2026), "Evaluating AGENTS.md,"** [arXiv:2602.11988](https://arxiv.org/abs/2602.11988). ETH
  Zurich. Headline, authors' own words: *"providing context files does not generally improve task success rates, while
  increasing inference cost by over 20% on average."* Also: *"Repository overviews, although popular and recommended by
  model providers, are not helpful."* ⚠️ Several vendor blogs cherry-pick the one positive number (+4% for
  developer-written files on n=138) and invert the paper's conclusion. Don't repeat that.
- **Lulla, ... Treude et al. (Jan 2026)**, [arXiv:2601.20404](https://arxiv.org/html/2601.20404v2), found the opposite
  on different tasks: ~28.6% faster wall-clock, ~16.6% fewer output tokens — but on small scoped PRs (≤100 LOC) with
  **no correctness measure**. Plausible reconciliation: AGENTS.md narrows search on small scoped tasks but induces extra
  exploration on open-ended ones. Both are small studies. **The evidence is genuinely unsettled.**
- **McMillan, "Instruction Adherence in Coding Agent Configuration Files,"**
  [arXiv:2605.10039](https://arxiv.org/pdf/2605.10039) ⚠️ *preprint, single author, industry lab*. 16,050 observations.
  **None of four file-structure variables** (size, position, architecture, conflict) produced a detectable effect. The
  largest effect is **within-session decay** — each additional generated function ≈5.6% lower odds of compliance, median
  first omission at position 4. Task identity beat file structure by 26.2 percentage points.

**Implication if it holds:** tuning context-file length/position/structure is low-yield, and compliance decays
*within a session* regardless of the file. That argues for **enforcement over prose** — hooks, linters, CI — which is
precisely what sase's `just check` convention already does. Worth noting as a positioning asset, not a README change.

**llms.txt: no empirical efficacy study exists.** Treat as evidence-free.

---

## §4. Recommended changes to the sase README

Ordered by value-to-effort. Items 1–6 are high-confidence and cheap; 7–11 are judgment calls; 12–13 are explicitly
*not* recommended.

### 1. Link the orphaned `CONTRIBUTING.md`

`CONTRIBUTING.md` exists (59 lines, covers setup, `just` workflow, tests, tox, beads) and is referenced by **nothing in
the repo**. Contributing has the second-largest measured effect size on stars (δ=0.415) while appearing in only 5% of
Java READMEs, and GitHub's survey ranks contribution guidance a top decision factor (67%). It's also a standard-readme
**required** section and a GitHub community-profile checklist item.

Cheapest fix on this list: one line in the existing `## Development` section, or a two-line `## Contributing` section
before `## License`.

### 2. State the project's status — sase is Alpha and doesn't say so

`pyproject.toml` declares `Development Status :: 3 - Alpha`. The README never mentions it. 78.6% of READMEs omit status
(Prana's *When*, 21.4% present) — this is the single most common gap in the corpus, and sase currently has it.

Someone running `uv tool install sase` deserves to know. Follow uv's FAQ precedent (*"Is uv ready for production?"*) or
add one honest line near the top. This is a credibility purchase, not a liability.

### 3. Expand the acronym

The README says sase is pronounced "sassy" but **never says what SASE stands for** — *Structured Agentic Software
Engineering* — even though that string is the package's own `description` in `pyproject.toml` and the mkdocs
`site_description`. The project's name is its thesis; spend the four words.

### 4. State the platform constraint and the real prerequisites

`Operating System :: POSIX` — **no Windows support**. The README's Quick start lists only Python 3.12+, uv, and an agent
CLI. `INSTALL.md` additionally requires **`git`** and a **text editor** (`$EDITOR`→nvim→vim). A Windows user or a
git-less environment currently discovers this by failing.

uv's FAQ has an exact precedent: *"What platforms does uv support?"* One line in Quick start, or one FAQ entry.

### 5. Fix the PyPI rendering — relative paths are broken there

`pyproject.toml` sets `readme = "README.md"`, so this file **is** the PyPI long description. PyPI does not rewrite
relative URLs, and `[tool.hatch.build.targets.sdist] only-include = ["src/sase"]` excludes `demos/` and `docs/` from the
sdist. So all four images and the `INSTALL.md` / `LICENSE` / `docs/acknowledgements.md` links **render broken on the
PyPI page**.

This is a real defect, not a style question, and it's invisible from GitHub. Two options: use absolute
`raw.githubusercontent.com` URLs for images (costs the "inline essentials" principle Art of README argues for), or
maintain a separate short PyPI description. Recommend the former — it's a one-time edit and PyPI is a genuine discovery
surface.

### 6. Cut the media payload from ~7 MB

7.03 MB loads on every README view: `sase_overview.png` 1.35 MB + fan-out GIF 3.84 MB + PRs GIF 1.07 MB +
observability GIF 0.77 MB. The GIFs are 1920×1080 sources displayed at `width="830"` — ~2.3× oversized.

**The assets to fix this already exist in-repo and are unused:** `docs/images/blog/` holds 1280×720 variants of the same
demos (fan-out: 1.7 MB vs 3.84 MB — a 2.2× cut), and every GIF has an `.mp4` twin 1.5–2.7× smaller. lazygit
systematizes this — all 15 of its demo GIFs are named `*-compressed.gif`.

Point the README at the downscaled variants. Nothing needs regenerating. Optional follow-on: adopt uv's `<picture>` +
`prefers-color-scheme` pattern so the hero works in both GitHub themes.

### 7. Add a CI badge

Four workflows exist (`ci.yml`, `docs-deploy.yml`, `pr-title.yml`, `publish.yml`); the README has four badges (Docs,
PyPI, pyversions, License) and **no CI status**. Build status is in the consistent badge set across 8/8 peers, and it's
the one badge that answers a question the others don't: *does this currently work?*

Counter-consideration: Art of README's badge skepticism is real — *"what real value is this badge providing?"* A CI
badge passes that test; a fifth badge beyond it probably doesn't.

### 8. Surface the blog and the PDF handbook

`## Learn more` links 8 of ~40 doc pages. Entirely unsurfaced: the **blog (10 posts)** and the **PDF handbook** at
`/downloads/sase-handbook.pdf` — which CI builds *and* smoke-tests on every deploy, and which `docs/index.md` features
in its hero. Shipping a handbook and not linking it from the front page is pure waste. Two lines in `## Learn more`.

### 9. Consider "Why shouldn't I use sase?"

ripgrep's `### Why shouldn't I use ripgrep?` is the cheapest credibility purchase in the peer set, and CNCF's template
independently prescribes an explicit `Out of Scope` section. sase has a compressed version already — *"sase does not
replace coding agents; it makes agent-driven engineering dependable."* — but it reads as a positioning line, not an
honest limits statement.

Real candidates: it's Alpha; POSIX-only; it assumes you're already paying for an agent CLI; it's opinionated about
workspaces and git. Naming these disqualifies the wrong users fast, which is exactly what cognitive funneling asks for.

### 10. Consider the lazygit feature-triple for the TUI

The highest-value pattern in the peer set for a TUI: `### Feature` → one sentence naming the **exact keypress** → GIF.
lazygit generates its GIFs from an integration-test harness; **sase already has VHS tapes and a seed script**
(`demos/tapes/`, `demos/scripts/seed_sase_ace_demo`), so the machinery exists.

⚠️ **This one is in tension with everything else in this report.** It would push sase from landing-page toward
funnel/manual and undo today's slimming. Two unused GIFs already exist (`prompt_input`, `prompt_history_stash`), so the
temptation is real. **My recommendation: do this on the `sase.sh/ace/` docs page, not the README.** The README's job is
to route there.

### 11. Optional: adopt ruff's section markers to prevent drift

ruff wraps its README in `<!-- Begin section: Overview -->` / `<!-- End section: Overview -->` and slices it into the
docs site — one source, two renderings. sase has ~40 docs pages and a README that will drift from them. Worth
considering *if* README/docs duplication becomes a maintenance problem; not worth it preemptively.

### 12. NOT recommended: a Table of Contents

standard-readme requires one above 100 lines and sase is 109. **Ignore this.** The rule predates GitHub's
auto-generated heading TOC, which already provides it. Liu et al. found a TOC in only 2% of 11,594 Java READMEs. A
manual TOC on a 109-line file is pure maintenance burden.

### 13. NOT recommended: reordering Install after Usage, or adding social proof

- **Ordering:** Art of README's Usage-before-Install argument is the best-argued in the literature, but it targets
  *libraries* where usage is a code snippet. sase's "usage" *is* its demos, and `## See it in action` already sits above
  `## Quick start`. **sase is already effectively in funnel order.** Leave it.
- **Social proof:** 6/8 peers have a named section (`## Testimonials`, `## Kind Words From Users`, `## Bubble Tea in the
  Wild`). sase has none — but manufacturing testimonials for an Alpha project is worse than having none. Revisit at
  1.0. If you want the cheap version now, bubbletea's dependents-graph link is self-updating and unfakeable.

### Out of scope for the README, but adjacent

`SECURITY.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE`, and `.github/PULL_REQUEST_TEMPLATE.md` are all absent —
four of the seven GitHub community-profile checklist items. opensource.guide names license + README + contributing +
code of conduct as the universal four. These are **sibling files, not README sections** (per GitHub's own health-file
taxonomy), so they don't change the README — but `SECURITY.md` in particular is worth adding for a tool that executes
agent-generated code, and ripgrep's `### Vulnerability reporting` shows the README-side pointer costs one line.

---

## Sources

**Canonical**
- GitHub, [About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)
- GitHub, [Creating a default community health file](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
- RichardLitt, [standard-readme spec](https://github.com/RichardLitt/standard-readme/blob/main/spec.md)
- hackergrrl, [Art of README](https://github.com/hackergrrl/art-of-readme)
- [makeareadme.com](https://www.makeareadme.com/)
- [opensource.guide/starting-a-project](https://opensource.guide/starting-a-project/) (a **GitHub** property, not Mozilla)
- [JOSS review checklist](https://joss.readthedocs.io/en/latest/review_checklist.html)
- [CNCF project-template](https://github.com/cncf/project-template/blob/main/README-template.md), [CNCF techdocs criteria](https://github.com/cncf/techdocs/blob/main/docs/analysis/criteria.md)
- [diataxis.fr](https://diataxis.fr/) — *for documentation-corpus vocabulary only; says nothing about READMEs*

**Empirical**
- Prana, Treude, Thung, Atapattu, Lo (2019), *EMSE* 24:1296–1327 — [arXiv:1802.06997](https://arxiv.org/abs/1802.06997)
- Liu, Noei, Lyons (2022), *IST* — [PDF](https://enoei.github.io/papers/liu2022readme.pdf)
- Gaughan, Champion, Hwang, Shaw (2025), CHASE — [arXiv:2502.18440](https://arxiv.org/abs/2502.18440)
- Venigalla & Chimalakonda (2022) — [arXiv:2206.10772](https://arxiv.org/abs/2206.10772) ⚠️ peer review unconfirmed
- Steinmacher, Graciotto Silva, Gerosa (2014), OSS/IFIP AICT 427:153–163 — [PDF](https://www.ime.usp.br/~gerosa/papers/Steinmacher2014_Chapter_BarriersFacedByNewcomersToOpen.pdf); IST 59:67–85 (2015) ⚠️ paywalled, abstract only
- [GitHub Open Source Survey 2017](https://opensourcesurvey.org/2017/) ⚠️ industry survey, not peer-reviewed
- NN/g, [Scrolling and Attention](https://www.nngroup.com/articles/scrolling-and-attention/) ⚠️ *no developer docs in sample*

**Agent context files**
- Chatlatanagulchai et al. (2025) — [arXiv:2511.12884](https://arxiv.org/abs/2511.12884)
- Gloaguen, Mündler, Müller, Raychev, Vechev (2026) — [arXiv:2602.11988](https://arxiv.org/abs/2602.11988)
- Lulla, Mohsenimofidi, Galster, Zhang, Baltes, Treude (2026) — [arXiv:2601.20404](https://arxiv.org/html/2601.20404v2)
- McMillan — [arXiv:2605.10039](https://arxiv.org/pdf/2605.10039) ⚠️ preprint, single author, industry lab

**Peer READMEs** (read from local checkouts via `sase repo open`): astral-sh/uv, astral-sh/ruff, Aider-AI/aider,
jesseduffield/lazygit, charmbracelet/bubbletea, BurntSushi/ripgrep, All-Hands-AI/OpenHands, block/goose

**Could not obtain:** Springer (Prana published version), ScienceDirect (Steinmacher IST 2015 full text), ACM DL (Qiu et
al. 2019, "Signals that Potential Contributors Look For," CSCW — looks directly relevant to README-as-first-impression;
worth a library pull).
