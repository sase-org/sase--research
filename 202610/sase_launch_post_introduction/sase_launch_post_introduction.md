---
audio:
  edition: brief
  duration_s: 256.44
  chapter_count: 3
  episode_id: the-first-paragraphs-of-the-first-sase-blog-post-1260c4
---

# The First Paragraphs of the First SASE Blog Post

> **Research query:** Help write the first two to three paragraphs of the first sase blog
> post, the introduction for the rest of the post, drawing first on the related notes and
> tasks in my Obsidian vault (`~/bob/`) before any outside research.

<div class="listen">

♫ **Brief audio edition** · 4 min · 3 chapters · [Narration
script](sase_launch_post_introduction_narration.md)

</div>

![Infographic of the sase launch-post opening in three beats: identity ("I've always been proud to call myself a Software Engineer"), motion (gai's 98-line start, 15,756 commits, 2.74M tracked Python lines, 53% tests, 95% agent-attributed commits since July, and "Motion isn't progress"), and promise (sase defined and pronounced "sassy", with one developer supervising Claude Code and Codex in isolated workspaces that produce durable work records)](sase_launch_post_introduction_infographic.png)

## Bottom line

1. **Write the opening that today's outline already specified.** Your Keep note from
   2026-10-07 queued two swarms in order: *"Decide on the outline of the blog. Write the
   first paragraph of the blog."* The outline consolidation
   (`research:202610/sase_launch_post_outline/sase_launch_post_outline__final.md`) landed a
   few hours before this one. It defines an unheaded opening with three beats: **identity →
   motion → promise**. After the `<!-- more -->` fold, the outline's §1 "How I Got Here"
   carries the timeline and your ladder (Boris method → `tmux_ai_window` → auto-approved
   plans → `%wait`/`#fork`). None of the five reports wrote to that spec. Four of them spent
   a paragraph on Boris and `tmux_ai_window`, which §1.2 retells right after the fold.
   [The introduction below](#the-introduction) follows the outline.
2. **Open with your own sentence.** Four of the five reports and the outline lead with the
   pride line from `why_sase.md`. grk argued it makes a weak Hacker News snippet. HN shows
   only the title and domain, though. The surfaces that do show a snippet are the blog
   index, which shows everything above `<!-- more -->`, and social cards, which use the
   front-matter `description`. Paragraph 3 defines sase above the fold, and the dek covers
   social cards.
3. **Most of the words are already yours.** Paragraph 1 is `why_sase.md` joined to the
   unfinished line in `sase_blog_0_legacy_notes.md` (*"…but the truth is …"*). The pride
   sentence answers the question that line leaves open. Paragraph 2 closes with your
   *"Motion isn't progress"* note and your *"I've tried a lot"* passage from
   `sase_blog_0.md` Contents. The agent-written parts are connective sentences and
   checkable facts. The [provenance table](#sentence-provenance) marks them so you can
   rewrite them in your own voice. Paragraph 3 needs that most.
4. **The "Motion isn't progress" quote probably has a source.** cld searched four Codex
   podcasts and found nothing. I found the idea in Latent Space's *"Codex from 0 to 10M
   Users: Building ChatGPT Work"*, published 2026-07-28. At 01:08:18, OpenAI's Akshay Nathan
   says: *"I think maybe the trap is like conflating motion and progress… motion is much
   easier now than ever before because of the tooling that we have."* You created
   `why_sase.md`, with its note "*Motion isn't progress* quote from codex podcast," four
   days later, on 2026-08-01. The exact phrase "motion isn't progress" does not appear in
   the transcript, so the introduction paraphrases him and credits him. Confirm this is the
   episode you heard. If it isn't, drop the credit and keep the line as your own.
5. **The numbers check out, and they set up the joke.** I re-derived everything today (see
   [Facts verified today](#facts-verified-today)). The sase repo has 15,756 commits since
   2026-02-14 and about 2.74M lines of tracked Python, 53% of it tests. One new figure: the
   `SASE_AGENT=` trailer began on 2026-06-27, and since July **95% of commits** (6,143 of
   6,446) carry one. `gai`, sase's ancestor, was born on **2025-10-20**. If you publish
   around 2026-10-20, "a year ago" is exact, and your "crazy 12 months" bullet becomes
   literally true.
6. **Four calls are yours alone:** whether to keep "dolla dolla bills," whether to name
   Google, which name you use (the rename decision is due around 10-18), and lowercase
   "sase" versus "SASE" in prose. The README now uses lowercase **sase**. The live post uses
   "SASE".

*In this report, § numbers (§1, §1.2, §2.1, …) refer to sections of the post outline, and
¶1–¶3 refer to the paragraphs of [the introduction](#the-introduction).*

## What the vault asks the opening to do

The vault was read on 2026-10-07.

| Source | What it says | Where it lands |
| --- | --- | --- |
| `gkeep_inbox.md` (Keep, 2026-10-07 15:58) | "Decide on the outline of the blog. Write the first paragraph of the blog." | This report follows the outline decided earlier today. |
| `why_sase.md` (created 2026-08-01) | Pride/identity paragraph, plus bullets: stats with *"Motion isn't progress"*, "It started with Claude Code", "Crazy 12 months. Something big is happening", "look back at the last 12 months: claude, codex". | ¶1 (paragraph near-verbatim), ¶2 (stats + motion). "It started with Claude Code" opens §1, after the fold. |
| `sase_blog_0_legacy_notes.md` | *"I could say that it was the obvious need for structure I saw while working at Google or that I saw an opportunity to add some value but the truth is ..."* | ¶1, as the setup for "maybe it was my pride". |
| `sase_blog_0.md` Contents (2026-08-14) | "Blog quote for motivation behind sase: … Well I've tried... I've tried a lot. I've kept trying because even after all this time I'm still not quite sure what I want, which frustrates me." | ¶2, near-verbatim, as the answer to "motion isn't progress". |
| `sase_blog_0.md` `^outline` + Requirements | Introduction = Boris → `tmux_ai_window` → auto-approve → wait/fork, plus a funny timeline infographic. "Mention `tmux_ai_window` in introduction?!" "Optimal experience, not optimal performance." Humor, stick figures. | The ladder and infographic go to §1.1–1.2, right after the fold, which keeps them inside "the introduction" in the broad sense. "Optimal experience" goes to §2.1. |
| `sase_blog_0.md` tasks | `^prj` "Post first blog post to https://sase.sh!" is still open. `^zk` is open. *Gather references* (10-08), *Read zettelkasten research* (10-09), and *Describe demo video and infographic* (10-09) are blocked. Both proofread tasks are cancelled. | The intro must stand on its own, with no figure or citation hunt needed before publishing. |
| Prior research in the vault | `first_post_authorship_gap` (07-28): the block is ownership, and agents must not "decide what you believe." `directed_zettelkasten_first_post` (08-02): the identity sentence is "unfakeable, first-person." Your comment on the blog00 review fixed the title, *"SASE: Structured Agentic Software Engineering."* | Every opinion and feeling in the intro is a sentence you wrote. |

## Facts verified today

| Claim used | Evidence (2026-10-07) |
| --- | --- |
| `gai` born 2025-10-20 as a 98-line LangGraph script whose only tools were a mocked `get_weather` and a `calculate` | dotfiles `22fed806` "feat: Add 'gai' script": `home/lib/gai/main.py`, 98 lines, `StateGraph`, `tools = [get_weather, calculate]`. An hour later, `fb7276ce` "Attempt to wrap gemini CLI with gai". So sase's very first job was wrapping an agent CLI. |
| 15,756 commits on sase `master` | `git rev-list --count HEAD`. The first commits are `7559fe4f5e` "chore: Init beads" and `a325ec2d40` "chore: Add gai -> sase migration beads", both 2026-02-14. |
| "Over two million lines of Python, more than half of it tests" | Tracked `src/` + `tests/` `*.py` files: 2,736,065 physical lines. cld measured ≈2.3M non-blank, non-comment lines, with tests at 52–53%. The claim holds under either count. |
| "Since July, 19 out of every 20 commits have been signed by the coding agent that wrote them" | The first `SASE_AGENT=` trailer is dated 2026-06-27. Per month, signed/total: Jul 2,046/2,191 · Aug 2,009/2,095 · Sep 1,819/1,890 · Oct 269/270, which totals 6,143/6,446 = **95.3%**. All-time, 6,349 distinct commits are signed. cld's 6,367 counted trailer lines, not commits. |
| Motion vs. progress | Latent Space, 2026-07-28, Akshay Nathan (OpenAI core product engineering lead), 01:08:18: "I think maybe the trap is like conflating motion and progress." Co-host Vibhu: "I like the discussion between motion and progress." |
| Claude Code and Codex as example CLIs; isolated workspaces; one developer supervising from a TUI | README: sase "turns Claude Code, Codex, Antigravity, Qwen Code, OpenCode, Meta's Muse Code, and xAI's Grok Build into a coordinated engineering team. One developer supervises parallel agents in isolated workspaces." Tagline: "Tracked, reviewable, repeatable work." |
| Getting Started exists at `../../getting_started.md` | `docs/getting_started.md` exists. The live post already links docs with `../../` paths. |

### Verified but kept out of the introduction

These are verified but kept out of the intro, because §1 tells them. The first
`tmux_ai_window` (dotfiles `5242ea0d`, 2026-01-14 23:27) was 19 lines, bound to
`prefix + A`, and opened a window running `claude --dangerously-skip-permissions`. That was
twelve days after Boris Cherny's thread, which coverage dates to 2026-01-02. The thread says
"I run 5 Claudes in parallel in my terminal" with tabs numbered 1–5, plus 5–10 more on
claude.ai
([VentureBeat](https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are),
[Slashdot](https://developers.slashdot.org/story/26/01/06/2239243/creator-of-claude-code-reveals-his-workflow)).
Your first dotfiles commit that credits Claude Code is `c43e0a8d` (2025-04-30). The
dotfiles hold 543 `gai` commits from October 2025 through February 2026. cld's industry
timeline (Claude Code preview 2025-02-24, Codex CLI 2025-04-16, Hassan et al. 2025-09-07,
Gas Town 2026-01-01, Shumer in February 2026) is the right raw material for the §1.1
infographic.

## Where the reports disagreed

| Question | Positions | Resolution |
| --- | --- | --- |
| First sentence | cdx, cld, mus, gem: the pride line. grk: an industry claim first, with identity mid-paragraph. | **Pride line.** It's your sentence, and the outline puts it first. The HN-snippet objection doesn't apply ([Bottom Line 2](#bottom-line)). |
| Boris / `tmux_ai_window` in the intro | cdx, grk, gem: a full paragraph. cld: the `gai` → tmux → Valentine's Day chain. mus: one clause. | **Not in the intro.** §1.2 tells the ladder right after the fold. The intro's "a year ago" uses `gai` instead, the one origin fact §1 doesn't need. |
| Stats | cld: yes (current). gem: yes (stale). grk, cdx: none. mus: none. | **Yes, three numbers plus the 95% figure,** undercut by "motion isn't progress." The outline decided this, and §4 "What It Cost" pays it off. |
| "Motion isn't progress" | cld: unattributed. gem: "someone on the Codex podcast" (no source). grk: not in the opening. | **Paraphrase, credited to Akshay Nathan with a link.** Confirm the episode. |
| "Dolla dolla bills" | cld: "(the dolla dolla bills didn't hurt)". gem: paraphrased as "lucrative". grk: never ship it. cdx, mus: omitted. | **Keep cld's version as the default,** because it's your placeholder resolved in your own phrase. Swap in "(the paychecks didn't hurt)" if it reads wrong out loud. |
| Google | cld, gem: keep. grk, cdx: omit. | **Keep, as your call.** Without it: "…the obvious need for structure I saw at work…". |
| Defining sase above the fold | cdx, grk, mus, gem: yes. cld: defer. | **Yes, one sentence plus pronunciation,** because the blog index shows only the text above `<!-- more -->`. Credit the paper in §2.2. |
| Length | ~200 (outline) to ~520 words (gem). | **~300 words.** Trims for ~220 are in [Before publishing](#before-publishing). |
| Em dashes | cld: avoid them, as a machine-prose tell. gem, mus: use them heavily. | **None in the intro.** Your notes rarely use them, and HN moderators are actively hostile to generated text. |

## Corrections to individual reports

- **gem** fabricates biography and experience: "for over fifteen years," "like thousands of
  other developers," "for about forty-eight hours, it felt like having superpowers," agents
  that "stomped over each other's worktrees," failures that "burned through API quotas."
  None of this appears in the vault or the repo, which is exactly what the authorship
  research warned against. Its figures are stale: 11,000 commits, 900,000 lines, and 5,000
  runs, against 15,756 commits and 2.7M lines. Its lead variant reopens with the
  contrastive "SASE is not a wrapper… nor…" move that the launch review retired. It also
  attributes the quote to "the Codex podcast" without a source. A plausible source now
  exists ([Bottom Line 4](#bottom-line)), but the speaker's actual words differ.
- **mus** dates the shift "about a year ago." Your first Claude Code commit is 17 months
  old, and `gai` is the one-year mark. Its closing map tours product nouns (prompt
  language, TUI and scheduler, tracking machinery), which the outline replaced with idea
  headings. It compresses the ladder until it loses its specifics, and it uses em dashes
  throughout.
- **grk** diagnoses the live post well: the rename banner, a stale five-CLI roster when the
  README lists seven, an install promise in the map and blog index, and a fold that hides
  the definition. Its draft, though, garbles the July line into "The status quo that
  produced is useful enough to be dangerous." Its "no stats" and "never ship the dolla
  joke" positions predate the outline decided today. Its separate HN title conflicts with
  HN's original-title rule, as the outline consolidation found.
- **cld** has the strongest evidence, and every git fact in it re-verified. Its ¶2 industry
  timeline (Gas Town, Shumer) belongs in §1.1, and its ¶3 retells §1.2's tmux scene. Its
  trailer count was a line count (see [Facts verified today](#facts-verified-today)). It
  couldn't source "Motion isn't progress"; that gap is now closed.
- **cdx** is accurate and careful, and it was right not to imply SASE invented parallel
  agents or worktrees. But its draft gives you feelings you never wrote down ("exciting,
  and a little disorienting"). It also skips the stats and the motion line, both of which
  the outline asks for. Its joke, *"My engineering workflow was starting to look
  suspiciously like terminal-window management,"* is good, and it fits §1.2.

## Seam with the rest of the post

### What comes right after the fold

1. §1.1 opens on your bullet *"It started with Claude Code."* Don't repeat `gai` there.
2. §1.2 salvages the July `tmux_ai_window` scene. Replace its five-CLI list, since the
   README now lists seven, and consider adding cdx's terminal-window joke.
3. §1.3 keeps the 😈 list, *"That got me a long way. It also made the missing layer
   painfully obvious,"* and the plan-mode question. The outline also placed "…but the truth
   is…" and the trying quote in §1.3. Both now live in the intro, so §1.3 should use only
   the first half of the Contents quote (*"Sometimes tinkering is the most efficient way to
   understand…"*) or nothing from it.
4. "Optimal experience, not optimal performance" stays in §2.1. The paper credit and the
   naming jokes stay in §2.2.

### Before publishing

1. **Re-derive the numbers** on publish day. The repo adds about 65–70 commits a day.
   `git rev-list --count HEAD` ·
   `git ls-files 'src/*.py' 'tests/*.py' | xargs cat | wc -l` ·
   per-month `git log --grep='^SASE_AGENT=' --format=%cd --date=short | cut -c1-7 | sort | uniq -c`
   against `git log --format=%cd --date=short | cut -c1-7 | sort | uniq -c`.
2. **Publish date.** On or near 2026-10-20, "A year ago" is exact. After about December,
   switch to "Last October."
3. **Confirm the podcast** ([Bottom Line 4](#bottom-line)).
4. **Name.** If the rename lands (around 10-18), change every "sase", the expansion, and the
   pronunciation in ¶3. Write that clause last.
5. **Remove the July banner** ("xprompts have been renamed to macros"). Rewrite the
   front-matter `description`, which still promises "a practical install path"; it's the
   social-card snippet. Also fix `docs/blog/index.md`, which says the launch post covers
   installation.
6. **Read it out loud,** then rewrite the agent-written sentences in
   [Sentence provenance](#sentence-provenance) in your own words. Paragraph 3 is mostly
   agent-written.
7. **Trim to ~220 words if you want the outline's length.** Drop the Google clause, drop the
   19-of-20 sentence, and cut ¶3's "who it's for" sentence.

## About this report

**Date:** 2026-10-07 · **Type:** lead consolidation of five independent reports
([cdx](sase_launch_post_introduction__cdx.md), [cld](sase_launch_post_introduction__cld.md),
[grk](sase_launch_post_introduction__grk.md), [mus](sase_launch_post_introduction__mus.md),
[gem](sase_launch_post_introduction__gem.md)), plus my own checks against the `~/bob` vault,
this repo, the dotfiles repo, and the web.

**Question:** Write the first 2–3 paragraphs of the first sase.sh blog post, the
introduction for the rest of the post. Review the related vault notes and tasks first, then
research.

## Sources

**Vault (read first):** `why_sase.md` · `sase_blog_0.md` (tasks, Requirements, Contents,
`^outline`) · `sase_blog.md` · `sase_blog_0_legacy_notes.md` · `gkeep_inbox.md` ·
`2026/20261007.md`.

**Prior research (via `sase artifact read`):**
`research:202610/sase_launch_post_outline/sase_launch_post_outline__final.md` and the five
reports consolidated here.

**Repos:** sase (`README.md`, `docs/blog/posts/structured-agentic-software-engineering.md`,
`docs/blog/index.md`, `git log`) · dotfiles via `sase repo open chezmoi` (`22fed806`,
`fb7276ce`, `5242ea0d`, `c43e0a8d`).

**Web:**

- [Latent Space: Codex from 0 to 10M Users, Building ChatGPT Work (Akshay Nathan, OpenAI), 2026-07-28](https://www.latent.space/p/chatgpt-work)
- [VentureBeat: The creator of Claude Code just revealed his workflow](https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are)
- [Slashdot: Creator of Claude Code Reveals His Workflow](https://developers.slashdot.org/story/26/01/06/2239243/creator-of-claude-code-reveals-his-workflow)
- [Boris Cherny's setup thread](https://x.com/bcherny/status/2007179832300581177)
- [Hassan et al., Agentic Software Engineering (arXiv:2509.06216)](https://arxiv.org/abs/2509.06216)
  (for §2.2, not the intro)
- [Hacker News Show HN guidelines](https://news.ycombinator.com/showhn.html)

## Sentence provenance

Where each sentence of [the final version below](#the-introduction) comes from:

| ¶ | Sentence (abbrev.) | Origin |
| --- | --- | --- |
| 1 | "I've always been proud…" / "easy thing to take pride in" | `why_sase.md`, verbatim |
| 1 | "(the dolla dolla bills didn't hurt)" | your placeholder "[insert dolla dolla bills]", resolved (cld) |
| 1 | "I could tell you … Google … add some value, but the truth is" | `sase_blog_0_legacy_notes.md`, lightly edited |
| 1 | "maybe it was just my pride" / "take back some control … core part of my identity" | `why_sase.md`, near-verbatim |
| 2 | "A year ago, sase was `gai`, a 98-line LangGraph script…" | **agent-written**, from dotfiles `22fed806` |
| 2 | "15,756 commits … over two million lines of Python…" | **agent-written**, from your bullet "List sase's stats" |
| 2 | "19 out of every 20 … signed by the coding agent that wrote them" | **agent-written**, from the trailer counts in [Facts verified today](#facts-verified-today) |
| 2 | "That's a lot of motion. But, to paraphrase … motion isn't progress." | your bullet, with credit added |
| 2 | "Well, I've tried. I've tried a lot. I've kept trying because…" | `sase_blog_0.md` Contents, near-verbatim |
| 3 | "This post is about the parts that stuck." | **agent-written** (cld), the hand-off |
| 3 | Definition, pronunciation, and what sase does | **agent-written**, from the README. Rewrite in your voice. |
| 3 | "If you already juggle more than one coding agent…" / map / Getting Started | **agent-written**, from the outline's "promise" beat and section names |

## The introduction

Place it directly under the H1 `SASE: Structured Agentic Software Engineering`, followed by
`<!-- more -->`, then §1 "How I Got Here." It runs about 300 words. It is given below as
Markdown source, ready to paste; its Getting Started link resolves from the post's location
in `docs/blog/posts/`.

```markdown
I've always been proud to call myself a Software Engineer. It's always been an
easy thing to take pride in (the dolla dolla bills didn't hurt). I could tell
you that I started working on sase because of the obvious need for structure I
saw while working at Google, or because I saw an opportunity to add some value,
but the truth is, maybe it was just my pride. Building sase is my attempt to
take back some control from this thing that seemed like it was coming for a
core part of my identity.

A year ago, sase was `gai`, a 98-line LangGraph script in my dotfiles whose
only tools were a fake weather lookup and a calculator. Today its repo holds
15,756 commits and over two million lines of Python, more than half of it
tests. Since July, 19 out of every 20 of those commits have been signed by the
coding agent that wrote them. That's a lot of motion. But, to paraphrase
OpenAI's [Akshay Nathan](https://www.latent.space/p/chatgpt-work), motion isn't
progress. Well, I've tried. I've tried a lot. I've kept trying because, even
after all this time, I'm still not quite sure what I want, which frustrates me.

This post is about the parts that stuck. Together they make up sase (Structured
Agentic Software Engineering, pronounced "sassy"), an open-source layer around
the coding-agent CLIs you may already use, like Claude Code and Codex. It runs
them in isolated workspaces, keeps a durable record of what each one did, and
lets one developer supervise all of it from a single keyboard-driven terminal
UI. If you already juggle more than one coding agent at a time, this post is
for you. It covers how I got here, what sase generalizes, and what all that
motion cost. If you'd rather just try it, start with
[Getting Started](../../getting_started.md).

<!-- more -->
```
