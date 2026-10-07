# First SASE Blog Post: Outline Recommendation

**Researcher:** `research.0i.grk`  
**Date:** 2026-10-07  
**Question:** What outline should the first public SASE blog post use?

This report reviews Bryan's Obsidian notes and tasks first, then the live post and prior SASE research, then independent external sources. It ends with a recommended outline. It does not draft post prose.

---

## Bottom line

The first post already exists on disk and on the live site. Bryan's vault still treats it as unpublished work. Those two facts decide the job: this is a **rewrite outline for the canonical first essay**, not a plan for a second post, and not a plan to generate a fourth agent draft.

Use a **problem-first origin essay with a short product proof**. Keep seven H2 sections. Target 2,200–2,800 words. Keep the current page title. Cut the install tour. Keep Macros and the Agents tab as proof of the thesis, not as documentation. Leave AXE, Telegram, Beads, Patches, and Memory as teasers.

Do not restore the June vault tour (Introduction / Overview / XPrompts / ACE / AXE / Future). Do not keep the July six-section product walkthrough as the spine. Do not replace the post with a statistics ledger or a pure memoir.

The missing layer is still the one named in July: for each remaining product section, one high-value win, one still-open gap, and one lesson that cost something. That is a writing constraint on the outline, not extra headings.

---

## 1. Vault and task review

Queried `~/bob` with Dataview (`bob query`) and `sase bead search` before any outline judgment. Canonical notes:

| Note | Role |
| --- | --- |
| `sase_blog.md` | Series parent. Still WIP: "Publish the full sase.sh blog series." Requirements dump (limitations, AI slop / prompt debt, naming jokes, PIW quotes, Gas Town contrast). |
| `sase_blog_0.md` | First-post project. Status **wip**. Parent task still open: "Post first blog post to https://sase.sh." Scheduled 2026-08-24 as "Today is the day." |
| `sase_blog_0.md` `^outline` | Bryan's own outline, marked done 2026-07-07 after 19 days: Introduction → Overview → XPrompts → ACE → AXE → Future Blog Posts. |
| `why_sase.md` | Intended assembly file for the owned draft. Opens on identity/pride, then a 12-month timeline, then "Motion isn't progress." |
| `sase_blog_0_legacy_notes.md` | Older ten-part tour, including "no weasels; just work" and Gas Town's inability to interweave agent calls with deterministic code. |
| `ref/docs/sase_blog_260708.md` | The stalled proofread. One comment: add devil/halo bullets for `%wait` and `#fork`. |

### Open first-post tasks (as of 2026-10-07)

From `sase_blog_0.md`:

- `[ ]` Launch an agent to create `~/bob/zk/` notes for the post (`^zk`, refreshed 2026-10-06).
- `[?]` Gather references. Points at `[[lib/blogs/harness_for_rsi]]`. Scheduled 2026-10-08.
- `[?]` Read zettelkasten research (`directed_zettelkasten_first_post`, cancelled as a ref task on 2026-10-03, still scheduled on the project note for 2026-10-09).
- `[?]` Describe a demo video and infographic for each `^outline` section. Scheduled 2026-10-09.

The "high value / high untapped opportunity / lesson learned" grid was cancelled 2026-10-06 as a duplicate of `^zk`. The need remains. Prior authorship research already showed that grid is the human layer the July post never received.

### Requirements that must shape the outline (not become extra H2s)

From `sase_blog.md` and `sase_blog_0.md` Requirements:

- Devil/halo bullets, citations, TUI screenshots, three funny diagrams, `tmux_ai_window` in the intro.
- "Sase does not claim optimal performance, but optimal experience."
- "The term 'sub-agent' doesn't cut it."
- "Why a TUI?" as a real beat.
- A brief software-engineering timeline at the start.
- Stats with the Codex-podcast line "Motion isn't progress."
- Limitations list and a definition of AI slop / prompt debt.
- Stick-figure / angel-devil art (media, not a section).
- Optional closer: GitHub `type:poll` issues.
- Newer Keep-backed item `^0`: "Add AI broccoli section" (2026-09-10). The Keep body is not in the vault, so this report reserves a slot and does not invent the claim.

Seasoning that belongs inside existing sections, not as headings: token types, stash examples, Vim-mode joke, loop vs graph engineering, skills-as-procedural-memory, `reads`/`snips` as future sidecars, `sase artifact read` as an example of durable plans.

### Beads

Epic `sase-5k` **First SASE Blog Post** is closed (plan `plan:202607/first_blog_post.md`). Phases 1–4 closed in July 2026. There is **no open bead** for a rewrite. The live work lives in the vault project, not in beads. Treat the July epic as "an agent-written draft shipped," not "the first post is done."

---

## 2. What is already on the public site

Live URL: `https://sase.sh/blog/posts/structured-agentic-software-engineering/` (HTTP 200).

Current published H2s:

1. *(untitled intro)* — Boris Cherny method, `tmux_ai_window`, 😈/😇, thesis
2. SASE Wraps Agent CLIs, Not Models
3. Macros
4. The Agents Tab In sase's TUI
5. Install, Configure, Initialize
6. What's Next

Local word count: **2,882**. The July plan targeted 2,500–3,500 words and at most ~9 H2s. Length is inside the old band. The problem is genre, freshness, and ownership.

Hard freshness problems on the live page:

- A top-of-post note that "xprompts have been renamed to macros." Essays do not wear rename banners.
- Provider list omits **Grok Build**, which the current README documents as a supported CLI (explicit-only, like Muse).
- Install still documents a six-CLI world. README is already on seven.
- Diagram briefs still exist as `docs/images/blog/*.prompt.md` with HTML-comment placeholders. GIFs and one still are embedded.
- `docs/getting_started.md` already exists. The install H2 duplicates it.

`docs/blog/index.md` still calls this file "the launch post." Ten sibling drafts remain `draft: true` with `[0N]` titles.

The July post follows Bryan's `^outline` with two deliberate cuts from `plan:202607/first_blog_post.md`: AXE is a teaser only, and the 15-minute walkthrough moved to Getting Started. Those cuts were right. The remaining failure is that sections 2–5 read as docs narration. The one sentence in the corpus that still sounds like Bryan is the intro line the proofread highlighted: *"That got me a long way. It also made the missing layer painfully obvious."*

---

## 3. Prior SASE research (independent of this swarm)

Read via `sase artifact read`. These are earlier reports, not peer files from this swarm.

### Launch-post review (`research:202606/blog00_launch_post_review_consolidated.md`)

Reviewed the **May `[00]` essay** (~5,400 words, 20 H2s), not the July post. Criteria still apply:

- Problem-first spine in the first 600–900 words.
- Drop visible `[00]` numbering.
- Visual proof near the top.
- Move install and reference tables out of the essay.
- Name limits plainly.
- Compare Codex app and Gas Town with current, narrow claims.

Bryan's annotation on that review accepted the title **"SASE: Structured Agentic Software Engineering."** Keep that as the page title.

### Series structure (`research:202606/sase_blog_series_structure_consolidated.md`)

Promote six public posts, not ten. Post 1 is the **why** essay. Post 2 is the quickstart, already relocated to Getting Started. ChangeSpecs/Patches is the differentiator showpiece, **later**. Optional surfaces (Telegram, nvim) are not launch pillars.

A promoted post must: move the reader to a new state, stand alone when shared, carry a proof artifact, and avoid being reference docs in essay form.

### Launch strategy (`research:202606/sase_blog_launch_strategy_consolidated.md`)

Canonical `sase.sh` first. Submit the essay to HN as a **regular link**, not Show HN. Save Show HN for a tryable repo/quickstart. Positioning: durable operating layer, not "parallel agents."

### Authorship gap (`research:202607/first_post_authorship_gap/first_post_authorship_gap.md`)

The block is ownership, not a blank page. Agent-produced text completes; judgment tasks stall. The July tour structure is Bryan's, executed by agents. Reports that wanted a different *kind* of post (origin story only, or a stats ledger as post 1) were wrong to overturn `^outline`. The right move is to **fill the human layer inside the decided spine**, then cut docs prose.

That 2026-07-28 conclusion is still the writing method. It is not, in 2026-10, a reason to freeze the July H2 list. Product nouns, provider set, and the competitive frame have all moved.

### Directed zettelkasten (`research:202608/directed_zettelkasten_first_post/directed_zettelkasten_first_post.md`)

Use a **directed**, project-scoped ZK in `~/bob`: atomic notes, attach to an outline, concatenate, rewrite. Do not build a second brain. `why_sase.md` is the assembly note. The `^zk` task still open in the vault is this method. The outline below is compatible with it: six content sections that can each receive "high value / gap / lesson" notes.

### Harness engineering vs SASE (`research:202610/openai_harness_engineering_vs_sase`)

Useful for positioning, dangerous as first-post content. The first post should claim the control plane (workspaces, durable state, gates, provider adapters). It should not dump landing-path metrics, ToolRun pass rates, or unowned failure signatures. Those belong in a later "how I actually run this" / ledger post.

---

## 4. Independent external research

### Genre: this post is explanation

[Diátaxis, Explanation](https://diataxis.fr/explanation/) is the right slot. Explanation is understanding-oriented, admits opinion, makes connections, and stays bounded. It is the documentation you can read away from the product. Tutorials, how-tos, and reference already exist (`docs/getting_started.md`, `docs/macros.md`, `docs/ace.md`). A first post that re-narrates those files will lose to them.

The language Diátaxis wants is the language the vault already has and the live post mostly lacks: *why it is this way*, *what the alternatives were*, *what it cost*.

### Models that work for a first public essay

Three public essays share a spine that fits SASE better than a feature tour:

1. **Charlie Marsh, [Python tooling could be much, much faster](https://notes.crmarsh.com/python-tooling-could-be-much-much-faster)** (2022). Claim in the first screen, one proof artifact (Ruff + numbers), a short "how it works," explicit **limits** ("What Ruff is missing"), tradeoffs, implications. Not a toolchain catalog.
2. **David Crawshaw, [Remembering the LAN](https://tailscale.com/blog/remembering-the-lan)** (2020). Memory → what was lost → dream → product as the bet. Almost no feature list. The product is the last third. This is the shape `why_sase.md` is reaching for.
3. **OpenAI, [An open-source spec for Codex orchestration: Symphony](https://openai.com/index/open-source-codex-orchestration-symphony/)** (2026-04-27). Problem (context switching after harness engineering) → one design claim (the issue tracker is the control plane) → how the loop works → honest limit (not a maintained product). Bryan has **finished** this piece (`ref/blogs/open_source_codex_orchestration_symphony.md`).

Marsh is the structural template. Crawshaw is the voice template. Symphony is the adjacent-work template: name the bottleneck, name the control plane, stop.

### The market the first post enters in October 2026

"Parallel coding agents in worktrees" is no longer a differentiator.

- Anthropic documents [parallel Claude Code sessions with worktrees](https://code.claude.com/docs/en/worktrees). The live post already cites this.
- OpenAI's Codex app covers worktrees, automations, Git review, and background runs. The June review already called Codex app the real competitor on overlap.
- OpenAI's February [Harness engineering](https://openai.com/index/harness-engineering/) piece (Bryan has **finished** it) frames the job as "humans steer, agents execute," with the repo as system of record. Symphony is the next bottleneck: managing work, not managing tabs.
- Gas Town has moved to **Gas City** ([docs.gascity.com](https://docs.gascity.com/), updated 2026-10-06): a "software factory" of Agent / Bead / Formula / Rig / Pack / Event, aimed at work that runs *outside* an interactive session.

SASE's first-post claim has to be narrower than "I also orchestrate agents." The defensible claim, matching README and the live intro, is:

> SASE is a local, provider-neutral **operating layer around the agent CLIs you already run**. Runs become durable records. Prompts become files. The human stays on the gates. The TUI is the control surface.

That is distinct from Codex-only Symphony, from Gas City's factory-outside-the-session bet, and from "just tmux." It is also distinct from calling model APIs directly.

Name the SASE paper as the source of the name and of ACE-as-command-environment. Do not retell the paper. It is in the library as **queued**: `ref/papers/agentic_software_engineering.md` ([arXiv:2509.06216](https://arxiv.org/abs/2509.06216)).

### HN mechanics (outline implications only)

[Show HN guidelines](https://news.ycombinator.com/showhn.html): blog posts are off-topic for Show HN. Submit the essay as a regular link. Suggested HN title (not the page title): **Why coding agents need an operating layer**.

YC's [Launch HN instructions](https://news.ycombinator.com/yli.html) still describe the comment shape that works: what it is, the problem, the backstory, the technical difference, an invitation for feedback. That is also a decent check on the post's own first screen.

---

## 5. Competing outlines, and why they lose

| Outline | Source | Verdict |
| --- | --- | --- |
| Intro → Overview → XPrompts (deep) → ACE (wide) → AXE+Telegram → Future | Vault `^outline` | Too wide. Recreates the May `[00]` failure. AXE and Telegram fail the series-structure "launch pillar" test. Macros-in-depth duplicates the draft `[02]` post. |
| Intro → Wraps CLIs → Macros → Agents tab → Install → What's Next | July live post / `sase-5k` | Right *width*, wrong *genre*. Install duplicates Getting Started. Macros and Agents tab are reference-dense. No identity beat, no timeline, no limits block, no wait/fork halo callback. Stale providers. |
| Pure "why orchestration" essay, almost no product | June series research, taken literally | Leaves the reader with no proof the cockpit exists. The live GIFs are the cheapest proof SASE has. Use them. |
| Stats ledger as post 1 | Authorship-gap report B | Strong second post. Weak first post. Numbers belong in Overview as one table, caveated. |
| Ten-part numbered serial | May drafts | Already rejected by series research and by Bryan's title note. Keep drafts as salvage; do not relaunch them as homework. |

---

## 6. Design constraints for the rewrite

1. **Page title stays** `SASE: Structured Agentic Software Engineering`. Bryan accepted it. The slug can stay.
2. **HN title is the problem**, not the brand: `Why coding agents need an operating layer`.
3. **2,200–2,800 words, seven H2s.** Under the old 3,500/9 cap. The July post is 2,882 and still needs human layer *and* cuts; plan to cut install and the Macros reference density to make room.
4. **Explanation first, proof second, tutorial never.** One boxed "Try it" with three commands plus a link to Getting Started. No config-layering lecture.
5. **Current nouns only.** Macros, agent sessions, Patches, Goals, ToolRuns, scheduler. No "xprompt," no "agent family," no rename banners. Provider set matches README: Claude, Codex, Antigravity, Qwen, OpenCode, Muse, Grok — with Muse/Grok called out as explicit-only.
6. **One proof surface.** The Agents tab replaces the window farm. Artifacts / Patches / Services get a pointing sentence, not a tour.
7. **Per remaining product section, three dictated beats** (from the authorship grid, not as H3s): what it bought, what it still cannot do, what it cost to learn. ACE's known punchline stays available: the Agents tab is the buggiest part of the TUI.
8. **Devil/halo stays**, including the wait/fork callback the proofread asked for.
9. **Three diagram slots**, mapped to existing briefs: window farm vs control tower; one prompt / many CLIs; prompt burrito. Plus Bryan's requested timeline infographic in the intro.
10. **Adjacent work in one short block**, not a literature review: SASE paper (name + ACE), OpenAI harness/Symphony (control plane vs factory), Gas City (factory outside the session). Respectful, present-tense, no "I did not find an equivalent."
11. **Close with** "no weasels; just work." It is Bryan's line.
12. **Agents fact-check; they do not write sentences.** Same rule as the authorship-gap R4, still correct.

Park for later posts (name in §7, do not outline here): Beads & SDD, Patches / mentors / comments, Memory, scheduler / AXE / chops, Telegram / mobile, plugin architecture, the ledger post ("five months of agent-attributed commits"), evals.

---

## 7. Recommended outline

Recommended public title: **SASE: Structured Agentic Software Engineering**  
Recommended HN title: **Why coding agents need an operating layer**  
Target: **2,200–2,800 words · 7 H2s · `<!-- more -->` after the thesis paragraph**

Each H2 lists allowed H3s. No body prose.

### H2 1. Twelve months, then a tmux full of agents

*Untitled in the July post; give it a heading this time.*

- A short timeline of the last year of software engineering (funny infographic; Bryan's `^outline` + `why_sase.md` both ask for this).
- The identity beat from `why_sase.md` (pride, control, "something coming for the job").
- Boris Cherny method, cited; then `tmux_ai_window`.
- "That got me a long way. It also made the missing layer painfully obvious."
- 😈 list (keep; tighten).
- Name, pronunciation ("sassy"), one-sentence definition.
- 😇 list (keep; one line each).
- One-sentence map of the rest of the post.

Media: timeline infographic; window-farm vs control-tower diagram placeholder.

### H2 2. What SASE is, and what it is not

This is the vault "Overview," rewritten as explanation.

- Who it is for: people already running coding-agent CLIs in real repos, hitting coordination overhead.
- The design bet in one paragraph: wrap agent CLIs, do not call models directly; optimal **experience**, not claimed optimal performance.
- What it generalizes, as a short list, not a tour: gates → plans → epics; beads → sidecars; provider CLIs; VCS/workspaces; agent presentation; macros / control flow; project/artifact records; scheduled automations. (From the 2026-08-07 "Things that sase generalizes" note.)
- Limits block: not a model provider, not a hostile-code sandbox, not a hosted team platform, POSIX/alpha, budget visibility incomplete, Agents tab still the buggiest surface.
- Adjacent work: SASE paper; OpenAI harness engineering / Symphony; Gas City. One paragraph each at most, or one combined paragraph plus links.
- Optional one-table "Motion isn't progress" stats (commits, agent share, repos), with the caveat that motion is not the pitch.
- Reserved slot: **AI broccoli** (Keep note 2026-09-10). Place here if it is a worldview/limits claim; drop the heading if the Keep text is a joke that fits inside Limits. Do not invent the claim.

Suggested H3s:

- Who this is for
- The bet
- Limits
- Related work *(or fold related work into The bet)*

### H2 3. Wrap the CLIs you already trust

Proof of the design bet. Salvage the live "Wraps Agent CLIs" section; cut routing trivia.

- Thin providers: SASE launches the CLI you authenticated.
- Inherit auth, sandbox, tools, and provider improvements.
- One prompt, several runtimes (current seven; Muse/Grok explicit-only).
- Write-once skills / instruction shims / commit finalization.
- The trade-off (less direct token accounting; inherit provider policy). Do not announce "the trade-off is honest"; show it.

Suggested H3s:

- The boundary
- What you keep
- What SASE adds around the run

Media: `sase_ace_multi_model_fanout.gif`; one-prompt / many-CLIs diagram.

### H2 4. Prompts that survive the window

Macros as the smallest load-bearing idea. Not the language reference.

- A Markdown file you can `#run`.
- Directives live in the prompt (`%model`, `%id`, `%wait`); link `docs/macros.md` for the rest.
- Alternations as the answer to "one prompt = one agent."
- 😈/😇 callback for `%wait` and `#fork` (the stalled proofread's only request).
- One paragraph on where you type it: TUI prompt widget, `sase-nvim` / LSP. No PIW feature tour.
- One sentence: "sub-agent" is the wrong word for agents that launch agents.
- Token-types beat: at most one short paragraph, or cut.

Suggested H3s:

- A file you can run
- Controls in the prompt
- Fan-out, waits, forks
- The same language in the TUI and in the editor

Media: `sase_ace_prompt_input.gif`; optional history/stash GIF if it earns a lesson; prompt-burrito diagram.

### H2 5. One screen instead of seven

Why a TUI, then the Agents tab as the replacement for the window farm.

- Why a TUI (local, keyboard-dense, works when the browser is the wrong object). Vim-mode joke lives here if it lives anywhere.
- Observability: status, waits, plans, unread, provider glyphs.
- Sessions as the unit of a chain of work (current term; not "families").
- Steering: plan gate, launch-approval gate, fork / retry / wait / kill. This is the "human stays in the loop" proof against factory-only tools.
- Honest gap: Agents tab is the buggiest part.
- One pointing sentence at Artifacts (Patches, beads) and Services (scheduler). No second tour.

Suggested H3s:

- Why a TUI
- Seeing the farm
- Gates and steering

Media: `sase_ace_agents_observability.gif` plus the existing still. Do not embed the Patches GIF.

### H2 6. Try it

A door, not a setup guide. About 120–180 words.

- Prerequisites in one sentence (POSIX, uv, one authenticated CLI).
- Three commands: `uv tool install sase` → `sase doctor` → one read-only `sase run`, then `sase tui`.
- Link Getting Started for the rest.
- Success criterion: a durable agent record that survives the window.

No H3s. No `sase.yml` lecture. No plugin `--with` lecture.

### H2 7. What's next

- One paragraph: this post was the front door.
- Teaser list (reader language, then the noun): Beads & SDD; Patches (review state outside chat); Memory; background execution (scheduler / AXE); Telegram / mobile; plugin architecture. Optional: the later ledger post.
- Optional: two or three GitHub `type:poll` questions.
- Close: "no weasels; just work."
- CTA: install one-liner, sase.sh, GitHub.

No series-navigation footer.

---

## 8. Mapping vault `^outline` → this outline

| Vault `^outline` | Disposition |
| --- | --- |
| Introduction (Boris → tmux → wait/fork; timeline) | Keep as H2 1, with identity + timeline added |
| Overview | Keep as H2 2 + H2 3 (split "what it is" from "wraps CLIs") |
| XPrompts (editor, directives, alternations, workflows, specials) | Compress to H2 4; send depth to the existing Macros draft / `docs/macros.md` |
| ACE (Agents / families / hoods, plus PRs, notifications, AXE tab) | Compress to H2 5; sessions not families; PRs/AXE become pointers |
| AXE + Telegram | Tease in H2 7. Not a first-post pillar |
| Future Blog Posts | Keep as H2 7 |
| Move 15-minute post to Getting Started | Already done; H2 6 is a stub that links there |
| Install as a full H2 | Drop |

---

## 9. What not to do next

- Do not generate another agent-authored full draft against this outline. Fill `why_sase.md` / `zk/` notes first (`^zk` + the three-question grid).
- Do not reopen the ten May drafts as a numbered launch series.
- Do not put AXE, Telegram, Beads, or Patches above the fold.
- Do not leave the xprompt rename banner in the rewritten post.
- Do not treat the closed bead `sase-5k` as "the first post is finished." The vault project is still wip.

---

## Sources

**Vault (read first)**  
`sase_blog.md` · `sase_blog_0.md` (`^outline`, Requirements, open tasks) · `sase_blog_0_legacy_notes.md` · `why_sase.md` · `sase.md` (series still a sub-project of the 1000-star goal) · `ref/docs/sase_blog_260708.md` · `ref/chat/blog00_launch_post_review_consolidated.md` (Bryan title annotation)

**Repo / live**  
`docs/blog/posts/structured-agentic-software-engineering.md` (2,882 words, live) · `docs/blog/index.md` · `docs/getting_started.md` · `README.md` (seven CLIs including Grok) · `https://sase.sh/blog/posts/structured-agentic-software-engineering/`

**Prior SASE research**  
`research:202606/blog00_launch_post_review_consolidated.md` · `research:202606/sase_blog_series_structure_consolidated.md` · `research:202606/sase_blog_launch_strategy_consolidated.md` · `research:202607/first_post_authorship_gap/first_post_authorship_gap.md` · `research:202608/directed_zettelkasten_first_post/directed_zettelkasten_first_post.md` · `research:202610/openai_harness_engineering_vs_sase` · `plan:202607/first_blog_post.md`

**External**  
[Diátaxis: Explanation](https://diataxis.fr/explanation/) · [Charlie Marsh: Python tooling could be much, much faster](https://notes.crmarsh.com/python-tooling-could-be-much-much-faster) · [Crawshaw: Remembering the LAN](https://tailscale.com/blog/remembering-the-lan) · [OpenAI: Harness engineering](https://openai.com/index/harness-engineering/) · [OpenAI: Symphony](https://openai.com/index/open-source-codex-orchestration-symphony/) · [Hassan et al.: Agentic Software Engineering](https://arxiv.org/abs/2509.06216) · [Show HN guidelines](https://news.ycombinator.com/showhn.html) · [Launch HN instructions](https://news.ycombinator.com/yli.html) · [Gas City overview](https://docs.gascity.com/) · [Claude Code worktrees](https://code.claude.com/docs/en/worktrees)

Library check: 4 of 15 candidates already in your library (2 finished: OpenAI harness engineering, Symphony). The SASE paper is already in your library (queued). The Hugo Bowne harness-engineering piece is already in your library (queued since 2026-03-29, legacy backlog). Recommend only the structural models not in `ref/`: Marsh, Crawshaw, Diátaxis Explanation. Cite harness engineering, Symphony, and the SASE paper as already captured.
