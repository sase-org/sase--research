# The First SASE Blog Post: A Recommended Outline

**Date:** 2026-10-07 · **Type:** lead consolidation of five independent reports
([cdx](sase_launch_post_outline__cdx.md), [cld](sase_launch_post_outline__cld.md),
[grk](sase_launch_post_outline__grk.md), [mus](sase_launch_post_outline__mus.md),
[gem](sase_launch_post_outline__gem.md)), plus lead verification against the `~/bob` vault, this repo, the live site,
and external sources.

**Question:** Which outline should the first sase.sh blog post use? Review related vault notes and tasks first, then
research. End with a recommended outline: structure and sub-sections only, no drafted content.

---

## Bottom Line

1. **This is an in-place rewrite of a live post, not a new post.** The July post has been live since 2026-07-08:
   `structured-agentic-software-engineering`, HTTP 200 today, 2,882 words. The vault's `^prj` task *"Post first blog
   post to https://sase.sh!"* is still open, though. The job is to replace an agent-written product tour with a post
   you own, at the same URL. Keep the slug. Salvage the July opening: the `tmux_ai_window` scene, the 😈/😇 bullets,
   and *"That got me a long way. It also made the missing layer painfully obvious,"* which you highlighted. Everything
   after the opening becomes proof, not tour.

2. **Keep the July `^outline` order, but change what its headings name.** Introduction → overview → core ideas →
   future still works. The headings, however, are product nouns, and almost all of them have been renamed since
   2026-07-07. XPrompts are now Macros, ACE is `sase tui`, AXE is the scheduler, ChangeSpecs are Patches, and agent
   families are agent sessions. The product name itself may change too (§1). Headings should name ideas; product
   nouns belong in body text.

3. **Build the body on your 2026-08-07 list, "Things that sase generalizes."** It is the strongest framing in the
   vault and no draft uses it. Each section becomes a small argument: a narrow special case, the general version, and
   what the general version buys. That gives every section the 😈 → 😇 shape you asked for, and the headings survive
   renames. Cover **four of the eight items**, ordered by the rungs of your own ladder (Boris method →
   `tmux_ai_window` → auto-approved plans → `%wait`/`#fork`). The intro sets up each rung, and the body pays it off.
   The other four items become the series map, and they line up almost exactly with the "Future Blog Posts" list
   already in `^outline`.

4. **Make the honesty section a full H2.** It combines AI slop and prompt debt, the reserved AI-broccoli slot, and the
   limitations list. Opening with 15,755 commits and *"Motion isn't progress"* raises a question this section
   answers. Readers will also arrive with an existing critique of agent-built orchestrators in mind (Maggie Appleton's
   "vibecoded" essay on Gas Town).

5. **No install section.** Use a single "Try it" sub-section in the closing that links to Getting Started.

6. **Title: keep the one you accepted.** Use *"SASE: Structured Agentic Software Engineering"*, or
   *"&lt;NewName&gt;: Structured Agentic Software Engineering"* after a rename. HN's guidelines say to submit with the
   original title and not to editorialize. That rules out the separate problem-led HN title that grk and gem
   proposed. Put the problem in the dek instead.

7. **Shape:** five H2 sections plus an unheaded opening, about 2,800 words (hard cap 3,000).

8. **Then write; don't regenerate.** The July authorship-gap research found that the block is ownership, not
   structure, and that its recurring failure mode is "replace rather than own." This outline is meant to end the
   outline question. Its slots are for your words, and agents only verify facts and render assets.

---

## 1. What the Vault Says (verified 2026-10-07)

| Source | State | What it means for the outline |
| --- | --- | --- |
| `gkeep_inbox.md`, Keep note 2026-10-07 15:58 | *"Launch research swarms… Decide on the outline of the blog. Write the first paragraph of the blog."* | The outline must state the first paragraph's job explicitly. A draft of it already exists in `why_sase.md`. |
| `sase_blog_0.md` | **wip**. `^prj` is open. `^zk` (create `~/bob/zk/` notes plus architecture-principle zettels) is open, fresh 2026-10-06. Blocked: *Gather references* (next 10-08; its REF `harness_for_rsi` is dropped), *Read zettelkasten research* (10-09), and *Describe demo video and infographic for each main section* (10-09). | The outline doubles as the `^zk` structure note: each H3 maps to 1–3 zettels. The media slots below answer the demo/infographic task. |
| Grid task | *"Flesh out high value / high untapped opportunity / lesson learned for each section"*, cancelled 2026-10-06 as *"the same as the ^zk task."* | The grid survives as a **writing prompt** inside each body section, not as visible headings. |
| `^outline` (done 2026-07-07) | Introduction (ladder, timeline infographic) → Overview → XPrompts → ACE → AXE (+Telegram) → Future Blog Posts. | Keep the order and the ladder. Retire the product-noun headings. |
| Requirements added after `^outline` (Jul–Oct) | Devil/halo bullets, citations, three funny diagrams, TUI screenshots, "optimal experience, not optimal performance," "sub-agent doesn't cut it," token types, stash examples, stick figures, *Things that sase generalizes*, "I'm out of tokens," `type:poll` issues, the Vim-mode joke, **"Why a TUI?"**, AI Daily Brief, loop/graph engineering, skills as procedural memory, `reads`/`snips` sidecars, the `sase artifact read` four-plans example, the hub-note quote, **AI broccoli**. | Every item has a slot below or appears on the parked list (§5). |
| `why_sase.md` | The pride/identity paragraph is drafted. Order: pride → stats + *"Motion isn't progress"* → "it started with Claude Code" → the last 12 months. | This is your own assembly order for the opening and §1, so follow it. |
| `sase_blog.md` (series requirements) | Gas Town differences, *"agents tab is the buggiest part of the TUI,"* a limitations list (asked three times), naming jokes, the AI slop definition and its four categories including **prompt debt**, "vibe evals," the PIW goal quotes, and *"Plan mode is the canonical or best example of some deeper primitive… Interrupts?"* | The plan-mode quote now has an answer, **gates**, which gives the post a thread to plant early and pay off later. |
| Your annotations | On the blog00 review: *"…fine. PROPOSED TITLE: 'SASE: Structured Agentic Software Engineering'."* On the dropped proofread: *"Add bullets (devil + angel) that describe why `%wait` and `#fork` are needed!"* On the HN-strategy report: 16 highlights (lead with the reader's problem, durable state rather than "parallel agents," name an honest limitation, end with a feedback ask). | Title and devil/halo are decided. The HN "comments" are mostly highlight text split off by PDF extraction, so treat them as interest signals, not decisions. |
| AI broccoli | The body lives only in Google Keep. A web search found no established public term. | Reserve a slot that only you can fill. Do not infer the meaning. |
| Naming | The rename-shortlist research (2026-10-04) recommends deciding **within two weeks** (about 10-18). `sase.md` also has *"Sase rename idea: 'sal'"* (10-26), and terminology renames are pending: `s/shell/turn/` (10-12), pipe → loop (10-08), Main → IO (10-10). | Rename-proof headings. Write the name slot last. Freeze terminology on the draft date. |

---

## 2. Where the Reports Disagreed, and How This Report Resolves It

| Question | Positions | Resolution |
| --- | --- | --- |
| Spine | Vault tour (mus, gem keep it, lightly modified); work problems in three groups (cdx); "what SASE generalizes" (cld); problem-first origin + proof (grk) | **Generalizes, ordered by the ladder.** This keeps cdx's three problem groups (prompts, supervision, durable work) and grk's "proof, not docs." |
| H2 count | 5 + opening (cld, gem) to 8 (cdx, mus) | **5 + opening.** cdx's 8 H2s and ~27 H3s leave about 90 words per H3. |
| Title | cdx: *Why I Built SASE…*; gem: *The Missing Operating Layer…* (the retracted `[00]` title); grk: keep the page title but use a separate HN title; cld: keep the pattern and wait for the rename | **Your accepted title, also used on HN** (HN requires the original title). |
| Slug | gem: switch to `why-coding-agents-need-orchestration` (the retracted `[00]` slug) | **Keep the live slug.** |
| Install | mus: full section; grk: 120–180-word H2; cdx, cld, gem: link only | **One "Try it" sub-section in the closing**, linking to Getting Started. |
| AI slop / prompt debt | mus: defer; cdx: sub-section; cld, gem: H2 | **H2, combined with limitations and AI broccoli.** It is a series requirement, and it answers the stats. |
| Stats | gem: a whole "ledger" section; cld: opening strip; cdx: don't lean on activity metrics | **One caveated strip in the opening, paid off in §4.** The ledger stays a later post. |
| The grid | gem: visible H3s with agent-written answers; cld, grk: a writing constraint | **A writing prompt, never a heading, answered only by you.** |
| Durable work | cdx: make plans and artifacts visible in post one; others: defer | **Fold it into §3.3** through the `sase artifact read` four-plans example. |
| Neighbors | cld: compare against Gas Town; cdx: don't publish the "fatal flaw"; grk: one respectful block | **One short, dated, descriptive paragraph in §2.3.** No "fatal flaw." Recheck any Gas Town claim against Gas City. |

### Corrections to individual reports

- **gem:** The figures are stale. It cites 11,000+ commits; `git rev-list` shows **15,755** since 2026-02-14, with 6,349
  carrying `SASE_AGENT=` trailers. It lists six providers, but the README lists **seven**, including Grok Build. It
  also proposes the retracted `[00]` title and slug, uses old nouns (ChangeSpecs, AXE), and plans a "Post 1: Hello
  SASE" even though the quickstart already moved to Getting Started. Its grid answers were written by an agent (for
  example, the claim that "vendor CLI updates can alter exit codes"), which fills the very slots only you can fill.
- **mus:** It keeps old terms (ChangeSpec, families), defers AI slop despite the series requirement, keeps a full
  install section, and refers to a "Tamanaco gap" it never explains.
- **grk:** "Gas Town has moved to Gas City" overstates the link. Gas City is an April 2026 ground-up rewrite of Gas
  Town as an SDK, run by a company that lists Yegge as an advisor. Its separate HN title conflicts with HN's
  original-title rule.
- **cld:** It calls the HN-strategy annotations "your comments." Most of them are highlight continuations, so they are
  interest signals.
- **All five:** Every report treats "different types of tokens" and "AI broccoli" correctly as unknown. Keep it that
  way.

---

## 3. External Context That Shapes the Outline

- **"Parallel agents in worktrees" is table stakes.** Several tools already ship it: OpenAI's Symphony spec
  (2026-04-27; you finished it), the Codex app, Claude Code worktrees and agent teams, Gas City, and Databricks'
  Omnigent. Lead with what SASE *generalizes*, not with parallelism. Your HN-strategy highlights say the same thing.
- **Personal ladder posts work, and one famous ladder already exists.** Mitchell Hashimoto's *My AI Adoption Journey*
  (2026-02-05) is a step-by-step personal ladder. Steve Yegge's *Welcome to Gas Town* built its launch on an
  eight-stage industry ladder. Keep the industry timeline to one infographic, and make **your** ladder the prose.
- **Genre.** This post is a Diátaxis *explanation*: why things are the way they are, what the alternatives were, and
  what they cost. A post that re-narrates `docs/macros.md` or `docs/ace.md` loses to those pages. For structure,
  Charlie Marsh's Ruff launch essay is a good model (claim → proof → how it works → explicit limits). For voice,
  David Crawshaw's *Remembering the LAN* is a good model (memory → what was lost → the product as a bet).
- **HN.** Submit with the original title. Moderators have said generated text isn't allowed on HN, and a flag for
  AI-written articles is under debate. That makes your own voice in the human-only slots a requirement, not a nicety.
- **Claims discipline.** Name Hassan et al. (arXiv:2509.06216) as the source of the name, without implying that the
  paper validates this tool. METR's February 2026 update shows how uncertain agent speedup measurements still are, so
  present "optimal experience" as a design priority, not a measured result. Present Symphony's and OpenAI's harness
  metrics as their results, not as transferable SASE results.
- **Positioning tone.** The Keep note that launched this research also lists a Databricks job search, and Omnigent is
  a Databricks project. Keep the neighbors paragraph descriptive and generous. That is the right tone for HN anyway.

---

## 4. Gates Before Drafting

1. **Rename decision (about 2026-10-18).** It decides the H1, §2.2, and every noun. Write §2.2 last either way.
2. **Terminology freeze** on the draft date: macro, `sase tui`, scheduler/jobs/routines, agent session, Patch, gate.
   Remove the July "xprompts renamed" banner.
3. **Recapture the June screenshots.** `20260616_140429`, `20260616_115015`, `20260619_214831`, and `20260624_074728`
   are still in `~/tmp/screenshots/` (verified), but they predate the xprompt → macro, `ace` → `tui`, and family →
   session renames.
4. **Your model-alias config task** (scheduled 2026-10-10), so the screenshots show the config you actually use.
5. **Inputs only you can supply:** the AI-broccoli meaning, the token-types experience, one real slop example per
   category, and the grid answers for §3.1–3.4.
6. **Publish chores:** update `docs/blog/index.md`, which still says the launch post covers installation, and
   re-derive every number on publish day.

---

## 5. Parked for Later Posts (pointer at most)

Macro argument types; multi-prompt vs YAML workflows; project macros (`#gh:sase`); the PRs/Patches tab and the
notification panel; scheduler, AXE, and Telegram depth; Beads and SDD; Patch hooks, mentors, and comments; the memory
architecture and the zettelkasten hub-note quote (it fits the memory post, because memory-web descriptors are hub
notes); `reads`/`snips` sidecars; plugin and pluggable-VCS architecture; evals; the architecture principles (they
seed the `^zk` zettels and a later post); the commit/run "ledger" post; a detailed Gas Town breakdown; and emailing
the `agent_swe` paper authors (a launch-checklist item, not content).

---

## 6. Recommended Outline

**Title:** `SASE: Structured Agentic Software Engineering` (or `<NewName>: Structured Agentic Software Engineering`).
Use the same title on HN.
**Dek:** one line naming the problem: an operating layer around the agent CLIs you already use. You write it.
**Shape:** about 2,800 words · 5 H2s plus an unheaded opening · `<!-- more -->` after the opening · headings name
ideas, and product nouns stay in body text.
**Template for every §3 sub-section:** 😈 the special case → 😇 what SASE generalizes it to → one proof artifact →
your grid answers (high value / untapped opportunity / lesson learned), written as prose, never as headings.

### Opening (no heading, ~200 words)

- **The first paragraph.** Identity and pride, then "take back some control" (drafted in `why_sase.md`).
- **Motion.** A 3–4-number stats strip (commits, agent-attributed share, months), re-derived on publish day and
  undercut by *"Motion isn't progress."*
- **The promise.** One sentence on what SASE is and who the post is for, plus a Getting Started link for readers who
  only want to try it.
- *Media:* none. Keep the first screen fast.

### 1. How I Got Here (~500 words)

- **1.1 Twelve Months.** "It started with Claude Code." The industry timeline goes into one funny infographic
  (angel/devil stick figures), with at most about 100 words of prose. Cite the AI Daily Brief here.
- **1.2 My Ladder.** Boris method → `tmux_ai_window` → auto-approved plans → `%wait`/`#fork`. Each rung names what
  broke, and §3 returns to each one. Salvage the July opening here.
- **1.3 The Missing Layer.** The 😈 list and the "missing layer" line, followed by the "…but the truth is…" beat with
  the tinkering-vs-trying quote. Plant the question: *plan mode is a special case of what?*
- *Media:* timeline infographic; `window_farm_vs_control_tower` diagram (brief exists).

### 2. What SASE Is, and Isn't (~350 words)

- **2.1 The Bet.** Wrap agent CLIs, not models; "optimal experience, not optimal performance"; the 😇 list.
  *Media:* multi-model fan-out GIF (exists), so the first product proof lands within about 700 words.
- **2.2 The Name.** Where it comes from (the SASE paper: an inspiration, not a validation), the pronunciation, and the
  naming jokes ("I'm bad at naming things…", xprompts → macros). Write this last, after the rename decision.
- **2.3 Who It's For, and Its Neighbors.** The reader already runs several agent CLIs in real repos. Add one dated,
  descriptive paragraph on Symphony and the Codex app, Claude Code agent teams, Gas Town/Gas City, and Omnigent, with
  narrow claims only.

### 3. What SASE Generalizes (~1,150 words)

- *Lead-in (unheaded):* the eight-item list as one visual. Four are covered here and four in later posts.
- **3.1 One CLI → Every CLI.** *(The Boris rung.)* The provider interface; skills and memory written once, and why
  hooks are not; the different types of tokens (your meaning, moved to §4.3 if it turns out to be about cost); retries
  through a provider outage. *Lesson-slot candidate:* skills as procedural memory. *Media:* `one_prompt_provider_clis`
  diagram (brief exists) or the outage-retry screenshot.
- **3.2 A Wall of Terminals → One Screen.** *(The `tmux_ai_window` rung.)* "Why a TUI?"; agent sessions, clans, hoods,
  and tribes, and why "sub-agent" doesn't cut it; a forward pointer to the Agents-tab limitation in §4.3. *Media:*
  agents observability GIF and still (both exist).
- **3.3 Plan Mode → Gates.** *(The auto-approved-plans rung, and the payoff for §1.3's question.)* Gates → plans →
  epics; questions and launch approvals as the same primitive; plans that outlive the chat (the `sase artifact read`
  four-plans example). *Lesson-slot candidate:* "a gate never blocks an agent," or single-turn agents. *Media:* a plan
  or question gate clip (to record); the questions/retries screenshot; `img/20260824_141701.png`.
- **3.4 One Prompt → Programs.** *(The `%wait`/`#fork` rung.)* Macros as a prompt language; the `%wait`/`#fork`
  devil/halo bullets (your proofread request); alternations → "vibe evals"; stashes; the PIW/LSP "goal number one /
  goal number two" quote. *Lesson-slot candidate:* loop vs graph engineering. *Media:* prompt-input GIF (exists); the
  `%wait` and alternations screenshots; `img/20260802_*` stashes; `prompt_burrito` diagram (brief exists).

### 4. What It Cost (~400 words)

- **4.1 The Slop I Shipped.** Your definition, then the four categories (unneeded backward compatibility, unused
  features, duplicated logic, prompt debt) with one real SASE example each. Tie it back to the opening stats.
- **4.2 AI Broccoli.** Reserved for the Keep note's meaning. Merge into 4.1 or drop it if it does not stand alone.
- **4.3 Limitations.** One bulleted list: the Agents tab is the buggiest part of the TUI; alpha and POSIX-only;
  inherits provider pricing, policy, and CLI churn; vocabulary still moving; attention and token cost. No media.

### 5. What's Next, and I Need Your Help (~250 words)

- **5.1 The Other Four.** The remaining generalizations become the series map: Beads → sidecar repos (Beads & SDD);
  VCS and workspace operations (Patches, pluggable VCS); agent project management (artifacts, memory); conditional
  automations (scheduler and jobs, Telegram/mobile). Add evals and the ledger post.
- **5.2 "I Need Your Help. I'm Out of Tokens."** The ask, plus the `type:poll` GitHub issues.
- **5.3 Try It.** One link to Getting Started, with at most one command. Candidate spot for the Vim-mode joke.
- **Closing line:** *"No weasels; just work."*

---

## Sources

**Vault (reviewed first):** `sase_blog_0.md` (tasks, Requirements, Contents, `^outline`) · `sase_blog.md` ·
`why_sase.md` · `gkeep_inbox.md` (2026-10-07 Keep task) · `sase.md` (rename ideas, terminology renames, model-alias
task) · `2026/20261007.md` · `bob ref show` annotations on `ref/chat/blog00_launch_post_review_consolidated`,
`ref/docs/sase_blog_260708`, `ref/chat/sase_hacker_news_popularity_strategy_consolidated`.

**Repo and site:** `docs/blog/posts/structured-agentic-software-engineering.md` (H2s, word count, `git log` rename
history) · `docs/blog/index.md` · `README.md` (seven providers) · `git rev-list` and `git log` counts · sase.sh live
check · `~/tmp/screenshots/` and `~/bob/img/` file checks.

**Prior research (via `sase artifact read`):** `research:202610/sase_rename_new_name_shortlist/sase_rename_new_name_shortlist__final.md`
· `research:202607/first_post_authorship_gap/first_post_authorship_gap.md`.

**External:**
[OpenAI: Symphony](https://openai.com/index/open-source-codex-orchestration-symphony/) ·
[OpenAI: Harness engineering](https://openai.com/index/harness-engineering/) ·
[Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) ·
[Hassan et al.: Agentic Software Engineering](https://arxiv.org/abs/2509.06216) ·
[Mitchell Hashimoto: My AI Adoption Journey](https://mitchellh.com/writing/my-ai-adoption-journey) ·
[Steve Yegge: Welcome to Gas Town](https://steve-yegge.medium.com/welcome-to-gas-town-4f25ee16dd04) ·
[Maggie Appleton: Gas Town](https://maggieappleton.com/gastown) ·
[Gas City: About](https://gascity.com/about/) ·
[Hacker News Guidelines](https://news.ycombinator.com/newsguidelines.html) ·
[AI Weekly: HN debates a flag for AI-generated articles](https://aiweekly.co/alerts/hacker-news-debates-user-facing-flag-for-ai-generated-articles) ·
[Diátaxis: Explanation](https://diataxis.fr/explanation/) ·
[Charlie Marsh: Python tooling could be much, much faster](https://notes.crmarsh.com/python-tooling-could-be-much-much-faster) ·
[David Crawshaw: Remembering the LAN](https://tailscale.com/blog/remembering-the-lan) ·
[METR: Developer productivity experiment update](https://metr.org/blog/2026-02-24-uplift-update/).

Already in your library: Harness engineering and Symphony (finished); Welcome to Gas Town, the Hassan et al. paper,
and Effective harnesses (queued). The only new reading worth adding for this post is the two structural models
(Marsh, Crawshaw); the rest are citations, not homework.

Library check: 5 of 10 candidates already in your library (2 finished).
