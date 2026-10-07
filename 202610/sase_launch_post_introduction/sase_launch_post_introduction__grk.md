# First SASE Blog Post: Opening Paragraphs

**Researcher:** `research.0j.grk`  
**Date:** 2026-10-07  
**Question:** What should the first 2–3 paragraphs of the first public SASE blog post say, as the introduction for the rest of the post?

This report reviews Bryan's Obsidian notes and tasks first, then the live post and prior SASE research, then independent external sources. It ends with a fully written introduction. It does not rewrite the rest of the post.

---

## Bottom line

Keep the live opening's two owned sentences. Add the two beats the vault asked for and the live post never shipped: a short software-engineering timeline, and the identity line from `why_sase.md`. Do not replace the tmux scene. Do not lead with pride-as-joke. Do not turn paragraph three into a product tour or an install promise.

The introduction is three paragraphs, then `<!-- more -->`. The existing 😈/😇 lists stay immediately after the fold. They are the rest of the untitled intro section, not extra paragraphs.

The job of these three paragraphs is to put a cold HN reader in a new state: *coding-agent CLIs already work; the missing layer is durable operation around them; this post is the front door to that layer.* Everything else in the post has to earn its space against that claim.

---

## 1. Vault and task review

Queried `~/bob` with `bob query` (Dataview and Tasks) before any prose judgment. Canonical notes:

| Note | Role for the opening |
| --- | --- |
| `sase_blog.md` | Series parent. Requirements: `tmux_ai_window` in the introduction, limitations, naming jokes, AI slop / prompt debt, Gas Town contrast. Those last items belong later, not in paragraph one. |
| `sase_blog_0.md` | First-post project, still **wip**. Parent task still open: "Post first blog post to https://sase.sh." |
| `sase_blog_0.md` `^outline` | Bryan's own intro brief, marked done 2026-07-07 after 19 days: **Boris method → `tmux_ai_window` → auto-approve / wait / fork**, and **"Start the blog post off with a brief timeline of software engineering transformation."** |
| `why_sase.md` | Assembly file for the owned draft. Opens on identity/pride, then "It started with Claude Code," then "Crazy 12 months," then a look-back at Claude and Codex. The finished identity sentence is the one human layer the live post still lacks. |
| `sase_blog_0_legacy_notes.md` | Older intro: who I am, SASE paper, Gas Town, the unfinished "I could say it was Google… but the truth is …". The paper and Gas Town belong in Overview. The unfinished sentence was completed in `why_sase.md` as pride and control. |
| `ref/docs/sase_blog_260708.md` | Stalled proofread. One comment, attached to the missing-layer sentence: add devil/halo bullets for `%wait` and `#fork`. That is a callback *after* the three paragraphs, not a rewrite of them. |

### Open first-post tasks (as of 2026-10-07)

From `sase_blog_0.md`:

- `[ ]` Launch an agent to create `~/bob/zk/` notes (`^zk`, refreshed 2026-10-06).
- `[?]` Gather references. Points at `[[lib/blogs/harness_for_rsi]]`. Scheduled 2026-10-08.
- `[?]` Read zettelkasten research. Scheduled 2026-10-09.
- `[?]` Describe a demo video and infographic for each `^outline` section. Scheduled 2026-10-09.

The "high value / high untapped opportunity / lesson learned" grid was cancelled 2026-10-06 as a duplicate of `^zk`. It still describes the missing human layer for *later sections*. The introduction's human layer is already specified: timeline, identity, `tmux_ai_window`.

### Vault lines that must survive into the opening

Already on the live page, and still the right sentences:

- "The status quo is useful enough to be dangerous."
- "That got me a long way. It also made the missing layer painfully obvious."

In the vault, and still missing from the live page:

- The 12-month (now ~20-month) transformation timeline.
- "I've always been proud to call myself a Software Engineer… My attempt to take back some control from this thing that seemed like it was coming for a core part of my identity."
- `tmux_ai_window` named in the introduction (this one *is* on the live page; keep it).

Seasoning that must **not** enter these three paragraphs: "dolla dolla bills," stats with "Motion isn't progress," AI slop / prompt debt, the Vim-mode joke, Gas Town, the SASE paper retelling, an install walkthrough, a provider roster.

---

## 2. What the live introduction currently does

Live URL: `https://sase.sh/blog/posts/structured-agentic-software-engineering/` (HTTP 200, verified 2026-10-07).

The published first screen is three short paragraphs, then `<!-- more -->`, then the 😈 list:

1. Status quo + Boris Cherny method + Anthropic worktrees.
2. `tmux_ai_window` in enough mechanical detail to be a scene.
3. "That got me a long way. It also made the missing layer painfully obvious."

After the fold: devil list, one-sentence "the menu can stay," the SASE definition, angel list, and a map that promises CLI wrapping, Macros, the Agents tab, **and install**.

Prior authorship research (2026-07-28) graded this opening as the one part of the corpus that sounds like Bryan, and said to keep it nearly verbatim. That diagnosis still holds for the two owned sentences and the tmux scene. It does not hold for the first screen as a *launch* screen.

Gaps against the vault and against a cold reader:

- No timeline, though `^outline` and `why_sase.md` both asked for one.
- No identity beat. The pride/control sentence exists only in `why_sase.md`.
- `<!-- more -->` currently hides the definition. A Hacker News snippet of this page ends on "the missing layer" without saying what SASE is.
- Paragraph two enumerates five CLIs (`claude`, `codex`, `agy`, `qwen`, `opencode`). The current README documents seven, with Muse and Grok Build explicit-only. An origin scene that lists five as if they were the present menu goes stale in the first screen.
- The map still promises an install section. Getting Started already exists. The introduction should not re-commit to a setup tour.
- The live page still opens with a rename banner ("xprompts have been renamed to macros"). Essays do not wear changelog notes. Delete it; the introduction should say **Macros** on first mention of reusable prompts.

Keep the scene. Move the thesis above the fold. Stop enumerating CLIs in the origin paragraph.

---

## 3. Prior SASE research (independent of this swarm)

Read from vault copies of earlier consolidated reports and from the live tree. These are earlier reports, not peer files from this swarm.

### Launch-post review (`blog00_launch_post_review_consolidated`)

Reviewed the May `[00]` essay, not the July post. The criteria still bind the opening:

- Problem-first spine in the first 600–900 words.
- Drop visible `[00]` numbering. Bryan later accepted the title **SASE: Structured Agentic Software Engineering**.
- Suggested HN title: **Why coding agents need orchestration** (this report prefers **operating layer**, which matches the live thesis).
- Add pronunciation and acronym near first mention.
- Do not spend the first screen on command tables or plugin install.

### Series structure

Post 1 is the **why** essay. Post 2 is the quickstart, already relocated to Getting Started. A promoted post must move the reader to a new state, stand alone when shared, carry a proof artifact, and avoid being reference docs in essay form. The introduction's proof artifact is the named, linked `tmux_ai_window` scene plus the later Agents-tab GIF. The introduction itself should not try to be the GIF.

### Launch strategy

Canonical `sase.sh` first. Submit the essay to HN as a regular link, not Show HN. Positioning: durable operating layer around coding-agent work. Avoid "a better AI coding agent," "the future of software engineering," and "an 11-part blog series."

Best one-line positioning from that note, still usable as a north star for paragraph three:

> Coding agents can produce patches. SASE coordinates the durable engineering system around them.

### Authorship gap (2026-07-28)

The block is ownership, not a blank page. Agent-produced text completes; judgment tasks stall. The July tour structure is Bryan's. Reports that wanted a different *kind* of post (origin story only, or a stats ledger as post 1) were wrong to overturn `^outline`. Fill the human layer inside the decided spine.

For *these three paragraphs*, that means: keep the tmux scene, add the identity sentence, add the timeline, stop generating a fourth unrelated opening.

### Directed zettelkasten (2026-08-02)

`why_sase.md` is the assembly note. The identity paragraph in it is "unfakeable, first-person." Use it. Do not demolish that file. Do not put stats in the opening; the ledger is a later beat.

### Outline recommendation (2026-10-07, prior swarm, this researcher's earlier report)

Recommended H2 1: "Twelve months, then a tmux full of agents." The three paragraphs below are that H2's prose, compressed so they can stand as the first screen. Devil/halo, pronunciation, and the post map were already assigned to this H2; pronunciation and the map move *into* paragraph three so they sit above the fold.

---

## 4. Independent external research

### Genre

[Diátaxis, Explanation](https://diataxis.fr/explanation/) is the right slot. Explanation admits opinion, makes connections, and stays bounded. The opening should sound like a person who already ran the experiment, not like a README.

### Openings that work

Three public essays share a first-screen spine that fits this post:

1. **Charlie Marsh, [Python tooling could be much, much faster](https://notes.crmarsh.com/python-tooling-could-be-much-much-faster)** (2022). Claim in the first screen, one lived observation (JS tools got fast), then the product as proof. Limits come later. The SASE analogue is: agents got good; the window farm is the status quo; SASE is the layer around it.
2. **David Crawshaw, [Remembering the LAN](https://tailscale.com/blog/remembering-the-lan)** (2020). Memory → what was lost → the product as the bet. This is the shape `why_sase.md` is reaching for. The identity beat belongs in paragraph one; it should not *be* paragraph one by itself.
3. **OpenAI, [Harness engineering](https://openai.com/index/harness-engineering/)** (2026-02-11). Bryan has **finished** this piece (`ref/blogs/harness_engineering.md`). The adjacent claim is "humans steer, agents execute," with the repo as system of record. Useful later as related work. Too corporate for sentence one of *this* post.

Marsh is the structural template for the first screen. Crawshaw is the voice template for the identity clause. The live SASE opener already has a better first sentence than either: "The status quo is useful enough to be dangerous." Keep it. Relocate it to the end of paragraph one, after the timeline, so the first screen still lands on a claim.

### Timeline facts the opening may rely on

Keep the timeline *short*. A funny infographic can carry dates; the prose should not become a press roundup.

| Event | Date | Source |
| --- | --- | --- |
| Claude Code research preview | 2025-02-24 | Anthropic launch; PCMag interview with Boris Cherny (2025-10-27) |
| Codex CLI | 2025-04-16 | [TechCrunch](https://techcrunch.com/2025/04/16/openai-debuts-codex-cli-an-open-source-coding-tool-for-terminals/) |
| Claude Code GA | 2025-05-22 | Anthropic |
| Boris Cherny setup thread (5 local Claudes, 5–10 in browser) | 2026-01-02 | [X status 2007179832300581177](https://x.com/bcherny/status/2007179832300581177) |
| Anthropic documents parallel sessions with worktrees | current | [code.claude.com/docs/en/worktrees](https://code.claude.com/docs/en/worktrees) (verified 2026-10-07) |
| Hassan et al., "Agentic Software Engineering…" (the SASE paper) | 2025-09-07, v3 2026-06-24 | [arXiv:2509.06216](https://arxiv.org/abs/2509.06216) |

`why_sase.md` said "last 12 months" in August 2026. From October 2026, "the last year and a half" or "since early 2025" is the honest phrase. Do not write "12 months."

Name Boris's five local sessions if you name a number; that is what the thread says. Do not flatten it to "multiple Claude sessions" after the live post already cited the thread.

The worktrees URL in the live post still resolves. Anthropic now also has a broader [Run agents in parallel](https://code.claude.com/docs/en/agents) page. Keep the worktrees link in the opening; it is the collision-isolation claim, which is the part SASE later generalizes.

### Market the first screen enters in October 2026

"Parallel coding agents in worktrees" is no longer a differentiator. Anthropic documents it. Codex app covers worktrees, automations, and background runs. Gas Town has moved toward a factory-outside-the-session bet. The opening therefore cannot climax on "I also run agents in parallel." The climax is: **the window farm is the status quo, and the missing layer is durable operation around the CLIs you already run.**

### The SASE paper, in the opening

The paper's abstract still supports the name and the ACE-as-command-environment idea. Bryan's library copy (`ref/papers/agentic_software_engineering.md`) is **queued** (captured 2026-10-07), with two comments that are about plan frontmatter and gates, not about the intro. Name the paper in Overview. Do not retell it in paragraph one. Do not spend a sentence of the first screen on "borrowing the name."

### HN mechanics

[Show HN guidelines](https://news.ycombinator.com/showhn.html): blog posts are off-topic for Show HN. Submit as a regular link. The first paragraph is the snippet. It has to work if the reader never expands the fold.

Suggested HN title: **Why coding agents need an operating layer.**  
Page title stays: **SASE: Structured Agentic Software Engineering.**

---

## 5. Design constraints for these three paragraphs

1. **Three paragraphs, then `<!-- more -->`.** Devil/halo lists follow the fold. `%wait` / `#fork` halo bullets are a later callback, not paragraph four.
2. **Paragraph one** carries timeline + identity + the status-quo sentence. That is the HN snippet.
3. **Paragraph two** is the Boris → `tmux_ai_window` scene. Named, linked, specific. No current-provider roster.
4. **Paragraph three** is the missing-layer sentence, the one-sentence definition with pronunciation, and a map of the rest of *this* post. The map names wrap-the-CLIs, Macros, and the Agents tab. It does not promise install, AXE, Telegram, Beads, or Patches as sections of this post.
5. **Current nouns only.** Macros, sase's TUI, Agents tab. No "xprompt," no rename banner, no "ACE" as the product name in the first screen (the live docs and README say "sase's TUI").
6. **Pronunciation "sassy"** on first expansion of the acronym.
7. **No contrastive "not a better model" opener.** The May `[00]` post led with that. The wrap-vs-replace distinction is real; it belongs in the next H2, stated as what SASE does.
8. **No stats.** "Motion isn't progress" is an Overview table, caveated.
9. **No networking-SASE lecture** unless it fits in a clause. "Structured Agentic Software Engineering, pronounced sassy" is enough disambiguation for the first screen.
10. **Agents fact-check; they do not invent the voice.** The sentences below reuse Bryan's owned lines and fill only the gaps the vault already named.

---

## 6. Rejected openings

| Opening | Why it loses |
| --- | --- |
| Lead with "I've always been proud…" and the dolla joke | Memoir as sentence one. Weak HN snippet. The joke is in `why_sase.md` as a placeholder and should never ship. |
| Keep the live three paragraphs unchanged | Missing timeline and identity. Fold hides the definition. Five-CLI roster is stale. Map still promises install. |
| May `[00]` "SASE is not a better model…" | Contrastive, abstract, no scene. Already retired once. |
| Stats / "Motion isn't progress" as paragraph one | Ledger-post energy. Wrong genre for the front door. |
| SASE paper + Gas Town as paragraph one | Literature review. The paper is queued; Gas Town is a later contrast. |
| Feature tour ("Macros, Beads, Patches, AXE…") | Recreates the May failure. The first screen has to win the *problem*, then point. |
| Two paragraphs that skip the timeline | Violates `^outline` and `why_sase.md`. The infographic can carry dates; the prose still needs one sentence of transformation. |

---

## 7. How these paragraphs hand off

After `<!-- more -->`:

1. The existing 😈 list (tighten; do not add CLI counts that will rot).
2. One sentence: the menu can stay local; everything around it grows up.
3. The existing 😇 list, with Macros and sase's TUI, plus the `%wait` / `#fork` halo the proofread asked for.
4. The window-farm vs control-tower diagram placeholder.
5. Then H2 **What SASE is, and what it is not** (Overview): limits, related work (SASE paper, harness engineering / Symphony, Gas City), optional stats table.

The three paragraphs below already say what the post will cover. Later H2s should not re-introduce SASE.

---

## 8. Fully written introduction

Use this as the untitled opening of `docs/blog/posts/structured-agentic-software-engineering.md`, replacing the current first screen through the definition paragraph. Leave the 😈/😇 lists in place after the fold, with the install promise removed from any leftover map sentence.

---

The last year and a half turned coding agents from a terminal novelty into daily infrastructure. Parallel sessions in git worktrees are now a [documented workflow](https://code.claude.com/docs/en/worktrees). I have always been proud to call myself a software engineer, and watching the job rewrite itself in public is what made me start this project: an attempt to take back some control from a thing that seemed like it was coming for a core part of my identity. The status quo that produced is useful enough to be dangerous.

Open a handful of terminal or tmux windows, run one coding-agent CLI in each, hand each one a scoped task, and hop between them as they finish. I think of this as the Boris Cherny method because [Boris Cherny's Claude Code setup thread](https://x.com/bcherny/status/2007179832300581177) described running five Claudes in the terminal and another five to ten in the browser, and Anthropic now documents that shape as normal. I automated my version with [`tmux_ai_window`](https://github.com/bbugyi200/dotfiles/blob/master/home/bin/executable_tmux_ai_window), a small script in my public dotfiles. One tmux binding opens a menu of the agent CLIs I actually use. Choosing one opens a new window named `ai`, `ai2`, `ai3`, and so on, in the current pane's directory, with the "yes, go do the work" flags already wired. When the CLI exits, the window closes and the remaining `ai*` windows are renumbered.

That got me a long way. It also made the missing layer painfully obvious. **SASE** (Structured Agentic Software Engineering, pronounced "sassy") is the open-source operating layer I built around those CLIs: durable records for every run, reusable prompts, approval gates, and a TUI where the whole mess becomes a screen you can read. This post is the front door. It explains why that layer exists, how SASE wraps the agent CLIs you already run, how Macros turn a prompt into a file you can rerun, and how one Agents tab replaces a farm of windows. The rest of the engineering system gets its own posts.

<!-- more -->

---

Word count of the three paragraphs: ~340. That is the whole first screen. A timeline infographic, if drawn, sits after the fold with the devil list, or as a figure under paragraph one if it is ready before publish. Do not delay the prose on the infographic.

---

## 9. Sources

**Vault**

- `~/bob/sase_blog.md`
- `~/bob/sase_blog_0.md` (`^outline`, Requirements, Contents)
- `~/bob/why_sase.md`
- `~/bob/sase_blog_0_legacy_notes.md`
- `~/bob/sase.md` (project frame)
- `~/bob/lib/docs/sase_blog_260708.md` and PDF (July draft / stalled proofread)
- `~/bob/lib/chat/blog00_launch_post_review_consolidated.pdf`
- `~/bob/lib/chat/sase_blog_launch_strategy_consolidated.pdf`
- `~/bob/lib/chat/sase_blog_series_structure_consolidated.pdf`
- `~/bob/lib/chat/first_post_authorship_gap.pdf`
- `~/bob/lib/chat/directed_zettelkasten_first_post.pdf`

**Product**

- Live post: https://sase.sh/blog/posts/structured-agentic-software-engineering/
- `docs/blog/posts/structured-agentic-software-engineering.md`
- `docs/blog/posts/why-coding-agents-need-orchestration.md` (retired `[00]` opener)
- `README.md` (seven CLIs; Muse and Grok Build explicit-only)

**External**

- Boris Cherny, Claude Code setup thread, 2026-01-02: https://x.com/bcherny/status/2007179832300581177
- Anthropic, parallel sessions with worktrees: https://code.claude.com/docs/en/worktrees
- Anthropic, run agents in parallel: https://code.claude.com/docs/en/agents
- Hassan et al., *Agentic Software Engineering: Foundational Pillars and a Research Roadmap*, arXiv:2509.06216
- OpenAI, *Harness engineering*, 2026-02-11: https://openai.com/index/harness-engineering/
- Charlie Marsh, *Python tooling could be much, much faster*, 2022
- Diátaxis, Explanation: https://diataxis.fr/explanation/
- Hacker News Show HN guidelines: https://news.ycombinator.com/showhn.html
- TechCrunch, Codex CLI launch, 2025-04-16
- PCMag, Boris Cherny interview, 2025-10-27 (Claude Code as February 2025 launch)

Library check: 4 of 10 candidates already in your library (2 finished: harness engineering, Symphony; 1 queued: SASE paper; 1 dropped: `harness_for_rsi`). The Boris thread, Marsh, Crawshaw, and the Anthropic worktrees/agents docs are not in `ref/`.
