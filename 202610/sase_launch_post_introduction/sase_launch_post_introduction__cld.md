# The Opening Paragraphs of SASE's First Blog Post

Researcher: `cld` (Claude Opus 5.5). Date: 2026-10-07. All repo and vault facts were
derived on this date; the commands are in Appendix A.

## Research Question

Write the first 2–3 paragraphs of the first sase.sh blog post, the introduction the rest
of the post hangs off. Start by reviewing the related Bob vault notes and tasks, then do
independent research.

## Bottom Line

1. **You've already written the hardest sentences.** The opening of `why_sase.md`
   (2026-08-01) and the unfinished line in `sase_blog_0_legacy_notes.md` ("I could say
   that it was the obvious need for structure I saw while working at Google … but the
   truth is …") are halves of the same paragraph. The legacy line asks a question and
   the `why_sase.md` line answers it ("Maybe it was my pride…"). Joining them gives
   paragraph 1 with almost no new words.
2. **Your notes describe paragraphs 2 and 3; they just never got written.**
   `why_sase.md` has three bullets under the opening: _"It started with Claude Code"_,
   _"Crazy 12 months. Something big is happening"_, and _"List sase's stats … with
   'Motion isn't progress'"_. The `sase_blog_0` outline says the introduction should go
   _"Boris method → tmux_ai_window → …"_ and _"start … with a brief timeline of software
   engineering transformation"_. The "Contents" quote ("Sometimes tinkering… Well I've
   tried… I've tried a lot…") is the emotional turn. Paragraph 2 is the industry
   timeline, and paragraph 3 is your response to it.
3. **Your own git history makes the timeline specific.** This is what none of the
   earlier blog research found. sase did not start in February 2026. It started on
   **2025-10-20** as `gai`, a **98-line LangGraph script** in your dotfiles whose only
   tools were a mock weather lookup and a calculator. The first `tmux_ai_window`
   (**2026-01-14**) was a **19-line script** that bound `prefix + A` to a new tmux window
   running `claude --dangerously-skip-permissions`. That was **12 days** after Boris
   Cherny's setup thread (2026-01-02), which is the tweet the published post already
   links. Specific dates and sizes like these are what make a paragraph read as written
   by a person, and they are all public in the dotfiles history.
4. **The intro stops where the published post's tmux scene starts.** The last sentence
   of paragraph 3 hands off to the `tmux_ai_window` scene, the 😈 bullets, and the SASE
   definition. Your outline's next beats ("auto-approve plans → wait / fork") belong
   there, and so does the one annotation you left on the July draft (add 😈/😇 bullets
   for `%wait` and `#fork`).
5. **Fix three things before it ships.** The stats are a snapshot from 2026-10-07, so
   re-derive them on publish day. The "Motion isn't progress" quote has no source yet: I
   couldn't trace it to a Codex podcast episode, so it runs unattributed. Whether to
   mention Google is your decision. Details are in §6.

## 1. What the Vault Says the Introduction Must Do

Every row below comes from notes in `~/bob/`. Status shows whether the final intro (§9)
covers it.

| Requirement / material | Source note | In final intro? |
| --- | --- | --- |
| Identity/pride opening, verbatim | `why_sase.md` (2026-08-01) | ✅ ¶1, near-verbatim |
| "[insert dolla dolla bills]" placeholder | `why_sase.md` | ✅ ¶1, resolved as a joke in your own phrase |
| "I could say … Google … but the truth is …" | `sase_blog_0_legacy_notes.md` (brain-dump, 2026-06-14) | ✅ ¶1, the hinge into "pride" |
| "It started with Claude Code." | `why_sase.md` | ✅ ¶2, as a dated commit |
| "Crazy 12 months. Something big is happening." | `why_sase.md` | ✅ ¶2, the Shumer essay plus timeline |
| "Let's look back at the last 12 months: claude, codex" | `why_sase.md` | ✅ ¶2 names both, plus an infographic brief (§5) |
| "Start the blog post off with a brief timeline of SWE transformation … funny but informative timeline infographic" | `sase_blog_0.md` Outline + Requirements (2026-08-01) | ✅ ¶2, with an infographic slot after it |
| "Boris method → tmux_ai_window → auto-approve plans → wait / fork → …" | `sase_blog_0.md` Outline | ✅ ¶2–¶3 cover Boris → `tmux_ai_window`; the rest goes to the next section |
| "Mention `tmux_ai_window` in introduction?!" | `sase_blog_0.md` Requirements | ✅ ¶3 |
| "Mention the SASE paper that inspired it all." | `sase_blog_0_legacy_notes.md` | ✅ ¶3, one clause |
| "List sase's stats … with 'Motion isn't progress'" | `why_sase.md` | ✅ ¶3 |
| "Sometimes tinkering … Maybe trying is better? … I've tried a lot. I've kept trying because … I'm still not quite sure what I want, which frustrates me." | `sase_blog_0.md` Contents (2026-08-14) | ✅ ¶3, near-verbatim |
| "Introduction on who I am … with a funny caveman diagram!" | `sase_blog_0_legacy_notes.md` | ➖ who you are is covered by ¶1; the caveman diagram fits the infographic slot (§5) |
| "Make jokes about why sase and xprompts are named the way they are" | `sase_blog.md` | ➖ not in the intro; see §6.4 for a ready-made joke |
| "sase does not claim optimal performance, but optimal experience!" | `sase_blog_0.md` | ➖ better used right after the SASE definition |
| Proposed title: _"SASE: Structured Agentic Software Engineering"_ | your comment on `blog00_launch_post_review_consolidated` | n/a; the intro is written to sit under that title |

Earlier research in the vault still applies to the intro:

- **`first_post_authorship_gap` (2026-07-28)** called the problem an ownership gap, not
  a blank page. It gave a voice checklist (R6) for any paragraph before it ships: Could
  it appear in the docs? Does it have a date, number, or name? Does it admit anything?
  Does it end on an aphorism? Is the humor load-bearing? Does it use
  "honest/boring/the trade-off is" as a credibility move? Would you say it out loud? It
  also said agents should not "generate the opening scene" or "decide what you believe."
  I followed that literally. Every opinion and feeling in the final intro is a sentence
  you already wrote. My additions are connective tissue plus checkable facts.
- **`directed_zettelkasten_first_post` (2026-08-02)** said the identity sentence _"is
  unfakeable, first-person, and passes every item on the … voice checklist"_, and that
  `why_sase.md` should not be gutted. The final intro keeps it in place.
- **`blog00_launch_post_review_consolidated` (June)** found the earlier opening named
  too many products too fast (XPrompts, SDD, Beads, ACE, AXE…). The intro below names
  exactly one sase concept: sase itself.

## 2. What I Found That the Notes Don't Say: sase's Real Timeline

Everything here comes from git history in the public dotfiles repo (opened as the
linked `chezmoi` repo) and the sase repo.

| Date | Event | Evidence |
| --- | --- | --- |
| 2025-04-30 | First dotfiles commit that credits Claude Code: it moved Neovim Lua files from `util/` to `bb_utils/` | `c43e0a8d` "ref: Had 'claude code' migrate util/*.lua files to bb_utils/*.lua files" |
| 2025-10-20 | **`gai` is born**: `home/lib/gai/main.py`, 98 lines, a LangGraph `StateGraph` with two example tools, a mocked `get_weather` and a `calculate`. Same day: "Attempt to wrap gemini CLI with gai", "Attempt to create MVP of gai", "Remove unused example tool support from gai" | `22fed806`, `fb7276ce`, `fa1b3530`, `f77d010e` |
| Oct 2025 → Feb 2026 | 543 dotfiles commits mention `gai` (27 / 88 / 93 / 231 / 103 per month, Oct→Feb) | `git log -i --grep='\bgai\b'` |
| 2026-01-14 23:27 | **First `tmux_ai_window`**: 19 lines; `prefix + A` opens a window named `ai`/`ai<N>` running `claude --dangerously-skip-permissions` | `5242ea0d` "feat: Add tmux keybinding for creating AI windows" |
| 2026-02-14 | **sase repo's first commit** (`chore: Init beads`), then `chore: Add gai -> sase migration beads`. So the first thing sase ever tracked was its own migration | sase `7559fe4f5e`, `a325ec2d40` |
| 2026-03-14 | `sase-org/sase` GitHub repo created (with `sase-github`, `sase-nvim`, `sase-telegram`) | `gh repo list sase-org` |
| 2026-07-08 | Launch post published (the Fable draft) | sase `a280878c3` per prior research |
| 2026-10-03 | "xprompt" renamed to "macro" across docs, memory, and skills | sase `fe53ae4fc4` |
| 2026-10-07 | 15,755 commits on sase `master`; 6,367 carry a `SASE_AGENT=` trailer; 16 repos under `sase-org` (12 public) | Appendix A |

Size of the sase repo on 2026-10-07 (tracked `*.py` only):

| | Files | Physical lines | Non-blank, non-comment lines |
| --- | --- | --- | --- |
| `src/` | 5,649 | 1,288,490 | ≈1,101,000 |
| `tests/` | 5,912 | 1,446,249 | ≈1,202,000 |
| **Total** | 11,561 | **2,734,739** | **≈2,303,000** (tokei: 2,312,209 code lines) |

So "over two million lines of Python, more than half of it tests" holds under either
counting method (tests are 52–53%). One more data point: `src/` had 2,473 `.py` files on
2026-07-28 and 3,990 on 2026-09-01. It has more than doubled in ten weeks. That belongs
in the AI-slop / "prompt debt" section, not the intro. It does make "Motion isn't
progress" literally true, though, and an HN reader will notice the growth whether or not
you mention it.

## 3. Industry Timeline (Verified)

These are the outside facts the intro uses, plus extras for the infographic.

| Date | Event | Source |
| --- | --- | --- |
| 2025-02-24 | Claude Code research preview | [Anthropic Claude Code release notes](https://docs.anthropic.com/en/release-notes/claude-code) |
| 2025-04-16 | OpenAI releases Codex CLI (open source) | [Gigazine](https://www.gigazine.net/gsc_news/en/20250417-openai-codex-cli), [Visual Studio Magazine](https://visualstudiomagazine.com/articles/2025/04/17/mapping-openais-full-ai-suite-after-codex-cli-debut.aspx) |
| 2025-05-22 | Claude Code generally available | [Anthropic release notes](https://docs.anthropic.com/en/release-notes/claude-code) |
| 2025-09-07 | Hassan et al., _Agentic Software Engineering: Foundational Pillars and a Research Roadmap_, proposes **Structured Agentic Software Engineering (SASE)**, including an "Agent Command Environment (ACE)" | [arXiv 2509.06216](https://arxiv.org/abs/2509.06216v1) |
| 2026-01-01 | Steve Yegge releases Gas Town (multi-agent orchestrator) | [heise](https://heise.de/-11178824), [ascii.co.uk](https://ascii.co.uk/news/article/news-20260102-190a5f9f/steve-yegge-releases-gas-town-multi-agent-orchestrator-for-c) |
| 2026-01-02 | Boris Cherny's Claude Code setup thread: five Claudes in parallel, terminal tabs numbered 1–5, system notifications. The date comes from decoding the status ID of the link already in the published post (`x.com/bcherny/status/2007179832300581177`) | [VentureBeat](https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are) |
| Feb 2026 | Matt Shumer's "Something Big Is Happening" (~5,000 words on X); compares the moment to February 2020; 70–80M+ views reported | [Wikipedia](https://en.wikipedia.org/wiki/Something_Big_Is_Happening), [Fortune](https://www.fortune.com/2026/02/20/something-big-is-happening-in-ai-but-thats-the-only-thing-matt-shumer-got-right) |

Two cautions:

- The Shumer essay drew heavy criticism (Fortune, Cato, Forbes), so the intro cites it
  only as a cultural marker ("comparing the moment to February 2020"). It does not
  endorse the essay's predictions. The intro also says "tens of millions of views," not
  "readers."
- I couldn't find a source for **"Motion isn't progress"** in any Codex-related podcast
  I could search: Lenny's Podcast with Alexander Embiricos, The OpenAI Podcast episode
  with Brockman and Sottiaux, The Pragmatic Engineer with Sottiaux, and the AI Daily
  Brief's "9 Codex Tips." The intro uses the phrase unattributed, as your own
  conclusion. If you find the episode, an attribution fits naturally ("As someone on
  the Codex team put it…"). Don't attribute it from memory, because an HN reader will
  check.

## 4. Design Decisions

- **¶1 is yours, rearranged.** I joined the legacy "I could say … but the truth is …"
  sentence to the `why_sase.md` pride sentence, because that is exactly the question
  that line was waiting to have answered. Your "Maybe" survives ("the truth is, maybe it
  was just my pride"). The hedge sounds spoken, and taking it out would make the line
  sound like a press release. "[insert dolla dolla bills]" becomes "(the dolla dolla
  bills didn't hurt)", which keeps your phrase and turns the placeholder into the joke.
- **¶2 is the "crazy 12 months" section, with checkable facts only.** It opens with "And
  it was coming fast," which picks up "coming for" from ¶1. The first Claude Code commit
  sits next to Codex CLI ("claude, codex"). Gas Town and Boris put the agent-wrangling
  problem in public view in the first week of 2026. Shumer's title is your own bullet,
  "Something big is happening." The paragraph ends on a fact and invents no feeling for
  you. That respects "agents must not decide what you believe."
- **¶3 is your response, told through your own artifacts.** It runs `gai` → the 19-line
  `tmux_ai_window` → Valentine's Day → stats → "Motion isn't progress" → your "I've
  tried a lot" passage → hand-off. Each fact is a small, slightly funny, true detail: a
  fake weather tool, `--dangerously-skip-permissions`, Valentine's Day. That puts the
  humor in the material instead of in slots shaped for jokes (checklist item 5).
- **The last sentence hands off; it isn't an aphorism.** "This post is about the parts
  that stuck, starting with that tmux keybinding" leads straight into the existing
  `tmux_ai_window` scene.
- **No em dashes in the intro prose.** They are the most recognizable tell of machine
  prose in mid-2026, and your own notes rarely use them.
- **Casing.** Your drafts write lowercase "sase" and capitalize "Software Engineer."
  I kept both. The published post uses "SASE" in prose. Pick one before publishing;
  the intro reads fine either way.

## 5. Infographic Brief (Slot After ¶2)

For the "funny but informative timeline infographic." This also fits the funny-stick-figure
and angel/devil art requirements, and could host the caveman diagram from the legacy
brain-dump.

> Horizontal timeline, stick-figure style. Top lane: **the industry** (Claude Code
> preview 2025-02-24 · Codex CLI 2025-04-16 · Claude Code GA 2025-05-22 · SASE paper
> 2025-09-07 · Gas Town 2026-01-01 · Boris's five tabs 2026-01-02 · "Something Big Is
> Happening" Feb 2026). Bottom lane: **me** (Claude Code moves some Lua files 2025-04-30
> · `gai` = LangGraph + fake weather tool 2025-10-20 · 19-line `tmux_ai_window` with
> `--dangerously-skip-permissions` 2026-01-14 · sase's first commit, Valentine's Day
> 2026 · 15,755 commits later, still renaming things: xprompts → macros 2026-10-03).
> The stick figure moves from caveman (left) to a person surrounded by many tiny agent
> stick figures with halos and devil horns (right).

## 6. Before Publishing

1. **Re-derive the stats on publish day** (Appendix A). The commit count grows by
   roughly 60–70 a day, and the line count is rising fast.
2. **Google.** ¶1 keeps your phrase "while working at Google." It's in the past tense and
   works as written, but naming an employer is your call. If you drop it, the sentence
   still works: "because of the obvious need for structure I saw at work."
3. **Seam with the published post.** If this intro replaces the opening of
   `structured-agentic-software-engineering.md`, the existing first paragraph ("The
   status quo is useful enough to be dangerous… the Boris Cherny method…") now repeats
   Boris. Cut it, and start the next section with something like: _"That keybinding
   grew. Today one tmux binding opens a `display-menu` with every agent CLI I use…"_
   Then continue into "That got me a long way. It also made the missing layer painfully
   obvious," which the vault notes call the one sentence in the July post that is
   clearly yours. The CLI list in that scene (`claude`, `codex`, `agy`, `qwen`,
   `opencode`) is from July, so check it against what the menu offers today.
4. **A ready-made naming joke for later in the post.** On 2026-10-03, four days before
   this report, xprompts were renamed to macros, after ACE became `sase tui` (2026-09-15)
   and agent families became agent sessions (2026-09-25). Your own line, _"I'm bad at
   naming things but I worry that indicates a deeper problem with the design,"_ needs no
   setup beyond that list. It belongs where the post first says "macro," not in the
   intro.
5. **Optional insert for ¶3**, if you want to say plainly that agents wrote most of
   this: after "15,755 commits," add ", 6,367 of them signed by the agent that made
   them,". The trailer only exists since June 2026, so don't call it "most."

## 7. Alternate: a Two-Paragraph Version

If you'd rather the timeline live entirely in the infographic:

> I've always been proud to call myself a Software Engineer. It's always been an easy
> thing to take pride in (the dolla dolla bills didn't hurt). I could tell you that I
> started working on sase because of the obvious need for structure I saw while working
> at Google, or because I saw an opportunity to add some value, but the truth is, maybe
> it was just my pride. sase is my attempt to take back some control from this thing
> that seemed like it was coming for a core part of my identity.
>
> And it was coming fast. In April 2025, I had Claude Code move some Lua files around
> my dotfiles. In October, I started `gai`, a 98-line LangGraph script whose only tools
> were a fake weather lookup and a calculator. In January, Boris Cherny shared his
> five-Claudes-in-five-tabs setup, and twelve days later I had a tmux keybinding that
> opened a new window running `claude --dangerously-skip-permissions`. On Valentine's
> Day 2026, `gai` became sase. Its repo now holds 15,755 commits and over two million
> lines of Python, but motion isn't progress. I've tried a lot. I've kept trying
> because, even after all this time, I'm still not quite sure what I want, which
> frustrates me. This post is about the parts that stuck.

## 8. Sentence Provenance (Final Version)

| ¶ | Sentence (abbrev.) | Origin |
| --- | --- | --- |
| 1 | "I've always been proud…" / "easy thing to take pride in" | `why_sase.md`, verbatim |
| 1 | "(the dolla dolla bills didn't hurt)" | your placeholder, resolved |
| 1 | "I could tell you … Google … add some value, but the truth is" | `sase_blog_0_legacy_notes.md`, lightly edited |
| 1 | "maybe it was just my pride" / "sase is my attempt … core part of my identity" | `why_sase.md`, near-verbatim |
| 2 | "And it was coming fast." | new connective |
| 2 | Claude Code commit 2025-04-30; Codex CLI 2025-04-16 | dotfiles `c43e0a8d`; Gigazine/VSM |
| 2 | Gas Town 2026-01-01; Boris's thread 2026-01-02 | heise; tweet-ID decode + VentureBeat |
| 2 | Shumer, February 2020 comparison, tens of millions of views | Wikipedia / Fortune; your bullet "Something big is happening" |
| 3 | "I responded the only way I know how: I started trying things." | your "Maybe trying is better?" (`sase_blog_0.md` Contents) |
| 3 | `gai`, 98 lines, fake weather + calculator, 2025-10-20 | dotfiles `22fed806` |
| 3 | 12 days later, 19-line script, `prefix + A`, `--dangerously-skip-permissions` | dotfiles `5242ea0d` |
| 3 | Valentine's Day 2026; name from Hassan et al. | sase `7559fe4f5e`/`a325ec2d40`; arXiv 2509.06216; legacy note "the SASE paper that inspired it all" |
| 3 | 15,755 commits; >2M lines of Python, >half tests | Appendix A (2026-10-07) |
| 3 | "Motion isn't progress, though." | `why_sase.md` bullet (unattributed, see §3) |
| 3 | "I've tried a lot. I've kept trying because … which frustrates me." | `sase_blog_0.md` Contents, verbatim |
| 3 | "This post is about the parts that stuck, starting with that tmux keybinding." | new hand-off sentence |

## Appendix A: Re-Deriving the Numbers

```bash
# sase repo (run from a sase checkout)
git rev-list --count HEAD                                          # commits (15,755)
git log --reverse --format='%h %ad %s' --date=short | head -2      # first commits (2026-02-14)
git log --format='%B' | grep -c '^SASE_AGENT='                     # agent-signed (6,367)
git ls-files 'src/*.py'   | xargs cat | wc -l                      # 1,288,490
git ls-files 'tests/*.py' | xargs cat | wc -l                      # 1,446,249
tokei src tests -t Python                                          # 2,312,209 code lines
gh repo list sase-org --limit 50                                   # 16 repos (12 public)

# dotfiles (chezmoi) repo
git log --reverse --format='%h %ad %s' --date=short -i --grep='\bgai\b' | head
git show 22fed806 --stat                                           # gai: 98-line main.py
git show 5242ea0d                                                  # tmux_ai_window v1: 19 lines
git log --format='%h %ad %s' --date=short -i --grep='claude code' | tail -1   # 2025-04-30

# Tweet-ID → timestamp (Twitter snowflake)
python3 -c "import datetime as d;i=2007179832300581177;print(d.datetime.fromtimestamp(((i>>22)+1288834974657)/1000,d.UTC))"
```

## Sources

Vault (read 2026-10-07): `sase_blog.md`, `sase_blog_0.md`, `why_sase.md`,
`sase_blog_0_legacy_notes.md`, `sase_blog_blockers.md`, `sase_research.md`,
`ref/docs/sase_blog_260708.md` + `lib/docs/sase_blog_260708.pdf` (the July draft),
`lib/chat/first_post_authorship_gap.pdf`, `lib/chat/directed_zettelkasten_first_post.pdf`,
`lib/chat/blog00_launch_post_review_consolidated.pdf`,
`lib/chat/sase_blog_launch_strategy_consolidated.pdf`,
`lib/chat/sase_blog_series_structure_consolidated.pdf`, and the vault's git history for
the 2026-06-20 "Initial Brain-dump" version of `sase_blog_0.md`.

Repos: sase (this checkout, including `docs/blog/posts/structured-agentic-software-engineering.md`),
the dotfiles repo via `sase repo open chezmoi`.

Web:

- [Anthropic — Claude Code release notes](https://docs.anthropic.com/en/release-notes/claude-code)
- [Gigazine — OpenAI releases Codex CLI](https://www.gigazine.net/gsc_news/en/20250417-openai-codex-cli)
- [Visual Studio Magazine — Mapping OpenAI's suite after Codex CLI debut](https://visualstudiomagazine.com/articles/2025/04/17/mapping-openais-full-ai-suite-after-codex-cli-debut.aspx)
- [arXiv 2509.06216 — Agentic Software Engineering: Foundational Pillars and a Research Roadmap](https://arxiv.org/abs/2509.06216v1)
- [heise — Gas Town orchestrates ten or more coding agents](https://heise.de/-11178824)
- [ascii.co.uk — Steve Yegge releases Gas Town](https://ascii.co.uk/news/article/news-20260102-190a5f9f/steve-yegge-releases-gas-town-multi-agent-orchestrator-for-c)
- [VentureBeat — The creator of Claude Code just revealed his workflow](https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are)
- [Wikipedia — Something Big Is Happening](https://en.wikipedia.org/wiki/Something_Big_Is_Happening)
- [Fortune — Something big is happening in AI, but that's the only thing Matt Shumer got right](https://www.fortune.com/2026/02/20/something-big-is-happening-in-ai-but-thats-the-only-thing-matt-shumer-got-right)
- Searched without finding "Motion isn't progress": [Lenny's Podcast w/ Alexander Embiricos](https://poderato.com/shows/lenny-s-podcast-product-career-growth/why-humans-are-ai-s-biggest-bottleneck-and-what-s-coming-in-2026-alexander-embiricos-openai-codex-product-lead-), [The Pragmatic Engineer w/ Tibo Sottiaux](https://newsletter.pragmaticengineer.com/p/building-codex-with-tibo-sottiaux), [AI Daily Brief — 9 Codex Tips](https://metacast.app/podcast/the-ai-daily-brief-artificial-intelligence-news/Br2I36uH/9-codex-tips-from-the-codex-team/pp9GxKBd)

## 9. The Introduction

> I've always been proud to call myself a Software Engineer. It's always been an easy
> thing to take pride in (the dolla dolla bills didn't hurt). I could tell you that I
> started working on sase because of the obvious need for structure I saw while working
> at Google, or because I saw an opportunity to add some value, but the truth is, maybe
> it was just my pride. sase is my attempt to take back some control from this thing
> that seemed like it was coming for a core part of my identity.
>
> And it was coming fast. The first commit in my dotfiles that credits Claude Code is
> from April 30, 2025, two weeks after OpenAI released Codex CLI, and all it did was move
> some Lua files from one directory to another. Eight months later, Steve Yegge released
> Gas Town to run a whole town of coding agents at once, and the next day Boris Cherny,
> the creator of Claude Code, shared a setup that kept five Claudes busy in five numbered
> terminal tabs. By February, Matt Shumer's "Something Big Is Happening" was comparing
> the moment to February 2020 and racking up tens of millions of views.
>
> I responded the only way I know how: I started trying things. sase began on October
> 20, 2025 as `gai`, a 98-line LangGraph script in my dotfiles whose only tools were a
> fake weather lookup and a calculator. Twelve days after Boris's post, I bound
> `prefix + A` to a 19-line script that opened a new tmux window running
> `claude --dangerously-skip-permissions`. On Valentine's Day 2026, `gai` got its own
> repo and a new name, borrowed from a paper by Ahmed E. Hassan and colleagues that
> proposed something called Structured Agentic Software Engineering. That repo now holds
> 15,755 commits and over two million lines of Python, more than half of it tests.
> Motion isn't progress, though. I've tried a lot. I've kept trying because, even after
> all this time, I'm still not quite sure what I want, which frustrates me. This post is
> about the parts that stuck, starting with that tmux keybinding.
