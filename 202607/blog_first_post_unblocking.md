---
create_time: 2026-07-28
updated_time: 2026-07-28
status: research
---

# Unblocking SASE's First Blog Post

## Research Question

Bryan is stuck writing SASE's first blog post. Every piece of blog content currently in the repo is agent-generated.
What is actually causing the block, what raw material exists that nobody else could write, and what should the first
post be?

## Bottom Line

1. **The block is not a blank page — it's an ownership gap.** There are 2,417 lines of finished-looking blog prose in
   `docs/blog/posts/`. The task that keeps failing is not "write" but "proofread," and it has failed four times across
   two months. You are being asked to approve someone else's voice, which is harder than writing your own.
2. **The existing corpus is documentation wearing a blog's clothes.** Its own generating plan says the prose was
   "pulled from the relevant product doc" and that the publication dates were staggered "so the archive page reads as a
   deliberate series rather than a same-week dump." Nine of the ten drafts were written in four days in May.
3. **The agents dropped every requirement you cared about most.** Your notes in `sase_blog.md` ask for a limitations
   list, an admission that the Agents tab is the buggiest part of the TUI, jokes about the naming, and a definition of
   AI slop and where it lives in SASE's own codebase. Zero of those appear in any post. Everything the agents kept was
   a feature explanation; everything they dropped was negative, personal, or funny.
4. **You already have the only story nobody else can tell, and it's numeric.** 11,192 commits in 5.5 months, 891,646
   lines of code, a 1.07:1 test-to-source ratio, 2,230 beads, 6,002 plan documents, and ~4,855 agent runs against this
   repo in the last 23 days alone. No competing project in this category has a ledger like that.
5. **Recommendation: write the ledger post, not the tour post.** "Here is what five months and ~200 agent runs a day
   actually produced, cost, and broke" covers what SASE is *as a side effect* of explaining why each piece exists — and
   it is the one post that cannot be generated, because the facts live in your head and your `~/.sase` directory.
6. **There is a launch-specific hazard in shipping agent prose.** In July 2026 the "AI slop" backlash reached the exact
   audience you're launching into. An agent-orchestration tool whose launch post reads as agent-written is a
   self-refuting artifact, and it is the first thing a Hacker News comment will say.

---

## 1. Inventory: What Exists Today

`docs/blog/posts/` contains eleven files, 2,417 lines total.

| Date (frontmatter) | Draft | Lines | Title                                                            |
| ------------------ | ----- | ----- | ---------------------------------------------------------------- |
| 2026-05-08         | true  | 626   | [00] The Missing Operating Layer for Coding Agents               |
| 2026-05-10         | true  | 205   | [01] Hello, SASE — Your First 15 Minutes Orchestrating Coding Agents |
| 2026-05-12         | true  | 178   | [02] XPrompts in Depth — From One File to Full Workflows          |
| 2026-05-14         | true  | 123   | [03] AXE — The Background Daemon That Keeps Agent Work Moving     |
| 2026-05-16         | true  | 133   | [04] Beads and SDD — Planning Multi-Agent Work That Actually Lands |
| 2026-05-18         | true  | 164   | [05] Commit Workflows — The Pluggable Path From Diff to PR        |
| 2026-05-20         | true  | 188   | [06] ChangeSpecs in Practice — Review State Outside the Chat      |
| 2026-05-21         | true  | 172   | [07] Driving SASE From Your Phone — Telegram as Mobile Control    |
| 2026-05-22         | true  | 167   | [08] Where You Type — The Prompt Input Widget and sase-nvim        |
| 2026-05-23         | true  | 109   | [09] What's Next — Shared Memory, Mobile, and the Web Surface      |
| 2026-07-08         | false | 352   | SASE: Structured Agentic Software Engineering                     |

Only the last one is published; it is the only post in the built site (`site/blog/posts/`).

### The provenance matters more than the content

Git says the `[00]`–`[09]` series was not written across sixteen days in May. It was written across **four**:

| Created    | Commit                                              | Posts               |
| ---------- | --------------------------------------------------- | ------------------- |
| 2026-05-08 | `7fb11b800` chore: add MkDocs blog scaffold          | [00]                |
| 2026-05-10 | `3249942db` feat: add hands-on "Hello, SASE" post    | [01]                |
| 2026-05-11 | `3412b2278` feat(blog): add Post 0 origin story      | [00] rework         |
| 2026-05-11 | `26a2aeb23` feat(blog): add Posts 3–8                | **six posts, one commit** |
| 2026-05-11 | `3d3a5120b`, `0995c6909`                             | [07], [08]          |

The generating plan (`sase/repos/plans/202605/new_blog_posts.md`) states the method in its own words:

> "Section skeleton fleshed out with on-topic prose **pulled from the relevant product doc** (linked, not duplicated
> wholesale)."

> "Dates step every other day so the archive page reads as **a deliberate series rather than a same-week dump**."

> "Each skeleton lists the H2s I'll write... **the notes are the contract**."

That is a complete diagnosis in three lines. The posts are (a) docs re-narrated, (b) with a fabricated publishing
cadence, (c) structured before there was anything to say. There is nothing to salvage at the paragraph level because
there was never a paragraph-level idea.

The July 8 launch post is better — it has a real opening (the `tmux_ai_window` story) — but your own task ledger
records it as `Use Fable to generate first draft of blog post!` created 2026-07-07, completed 2026-07-08. One day.

### Symptomatic details

- Both the July post and the `[00]` draft contain the same rhetorical tic in the same structural slot: "The trade-off is
  honest." (`structured-agentic-software-engineering.md:95`) and "The trade-off is real:"
  (`why-coding-agents-need-orchestration.md:131`). Rhetorical humility as a template field.
- The drafts are already rotting. Two carry a patch note: *"Terminology note (July 2026): the 'companion repos' named
  in this historical post are now called sidecar repos."* They are being maintained like source files, which is a sign
  they are documentation, not writing.
- A May 10 commit is literally `chore: warm up tone of "Hello, SASE" first-15-minutes post`. Voice was applied as a
  lint pass.

---

## 2. The Block Is an Ownership Gap, Not a Blank Page

Your Obsidian task ledger (`sase_blog.md`, `sase_blog_0.md`) is the clearest evidence in this entire investigation.

| Task                                                     | Created    | Outcome                        |
| -------------------------------------------------------- | ---------- | ------------------------------ |
| Plan first blog post                                      | 2026-06-05 | **cancelled** 2026-06-13       |
| Move sase tasks to sase_blog                              | 2026-06-07 | done 2026-06-07                |
| Do a WisprFlow brain-dump on what the first post should contain | 2026-06-11 | **done** 2026-06-14      |
| Migrate note in pocket to Obsidian tasks                  | 2026-06-15 | **cancelled** 2026-06-29       |
| Decide on the blog post's outline                         | 2026-06-18 | done 2026-07-07 (19 days late) |
| Proofread blog post                                       | 2026-06-19 | **cancelled** 2026-06-29       |
| Convert sase_blog_0 into a project                        | 2026-06-24 | done 2026-06-25                |
| Use Fable to generate first draft                         | 2026-07-07 | done 2026-07-08 (1 day)        |
| Proofread blog post                                       | 2026-07-08 | **open**, scheduled 2026-07-26 |

The pattern is unambiguous:

- Every task where **an agent produces text** completes, usually within a day.
- Every task where **you must judge or own text** is cancelled or slips.
- The one exception — the task that completed on time, by hand, with no agent — is the **WisprFlow brain-dump**. You
  dictated what the post should contain and finished it in three days.

The current proofread pass has physical evidence of stalling: `ref/docs/sase_blog_260708.md` (the PDF annotation
sidecar for the July 8 draft) contains **two highlights and exactly one comment** — *"Add bullets (devil + angel) that
describe why `%wait` and `#fork` are needed!"* — attached to the one sentence in the post that is actually yours
("That got me a long way. It also made the missing layer painfully obvious."). Then it stops. Twenty days, one comment.

This is not procrastination. Editing prose into your voice requires the voice to already be on the page; when it isn't,
every sentence is a decision with no criterion, and there are 352 of them. Generating more drafts makes this strictly
worse — it adds material to judge without adding anything to judge it against.

---

## 3. What the Agents Systematically Dropped

Your notes contain explicit content requirements. Here is what happened to each.

| Requirement (from `sase_blog.md` / `sase_blog_0.md`)                          | In any post? |
| ------------------------------------------------------------------------------ | ------------ |
| Break down differences vs. gastown (beads, rigs, no mayor)                      | ✗            |
| **"Mention that the agents tab is the buggiest part of the TUI!"**              | ✗            |
| **"Create list of limitations!"**                                              | ✗            |
| **"Make jokes about why sase and xprompts are named the way they are."**       | ✗            |
| **"Add a definition of what I consider to be AI slop and how it shows up in sase's codebase."** | ✗ |
| Categories of AI slop (backcompat, dead features, duplication, "prompt debt")   | ✗            |
| "Alternations allow for *vibe evals*"                                          | ✗            |
| "sase does not claim optimal performance, but optimal experience"               | ✗            |
| Real screenshots (Claude outage retry, `%wait`, questions/retries/tales)         | ✗            |
| Devil/halo emoji bullets                                                        | ✓            |
| tmux_ai_window in the introduction                                              | ✓            |
| XPrompts / Agents tab / install sections                                        | ✓            |
| Citations                                                                       | ✓            |

Everything preserved is a feature explanation. Everything dropped is an admission, a joke, an opinion, or a scar.

That is not a coincidence and not a model failure — it follows directly from the method. When the instruction is "flesh
out these sections with on-topic prose pulled from the relevant product doc," the agent's only source is documentation,
and documentation has no record of what's broken, what you regret, or what's funny. **The corpus is missing exactly the
content that a corpus generated from docs cannot contain.** No amount of re-prompting fixes that, because the source
material doesn't have it. It's in your head, your screenshots directory, and your git history.

---

## 4. The Material Only You Have

All figures verified against this workspace on 2026-07-28. Re-derivation commands in Appendix A.

### The build

| Fact                            | Value                                                    |
| -------------------------------- | -------------------------------------------------------- |
| First commit                     | 2026-02-14 (`7559fe4f5`, "chore: Init beads")             |
| Commits to date                  | **11,192** in ~5.5 months                                 |
| Commits by month                 | 769 / 1,659 / 1,642 / **3,428** / 1,812 / 1,882 (Feb→Jul) |
| Source code                      | 436,230 lines across 2,462 Python files                   |
| Test code                        | 467,055 lines across 2,407 Python files                   |
| Test-to-source ratio             | **1.07 : 1**                                              |
| Beads                            | 2,230                                                     |
| Plan documents                   | 6,002 (`202603`: 438, `202604`: 1,161, `202605`: 1,539, `202606`: 1,084, `202607`: 1,723) |
| Research reports                 | 290                                                       |
| Commits signed `SASE_AGENT=`     | 1,953 — all since June 2026 (229 in June, 1,720 in July)  |

### The operation

`~/.sase` retains roughly three weeks of run artifacts, so these are a **window, not a total** — the real figure since
February is much larger and unrecoverable.

| Fact                                     | Value                              |
| ----------------------------------------- | ---------------------------------- |
| Agent runs, all projects, 2026-07 window  | 5,205 (Jul 6 – Jul 28, 23 days)    |
| Agent runs against `sase` itself          | 4,855 `ace-run` + 57 `fix-hook` + 66 `summarize-hook` |
| Daily average                             | ~226 runs/day                      |
| Peak day                                  | **496 runs on 2026-07-18**         |
| Quietest day                              | 103 on 2026-07-24                  |
| Supported provider CLIs                   | 5 (`claude`, `codex`, `agy`, `qwen`, `opencode`) |
| Repos in the system                       | 5 (`sase`, `sase-core`, `sase-github`, `sase-telegram`, `sase-nvim`) |

⚠️ Caveats to state honestly if you publish these: run counts include hook runs and workflow steps, not just top-level
agents; `~/.sase` prunes, so the window is not a total; and line counts include generated and test code. Publishing the
caveat alongside the number is worth more than the number, especially to a Hacker News audience that will look for the
inflation.

### The five stories these numbers imply

Every one of these is a question only you can answer, and each is a post's worth of material:

1. **What happened in May?** 3,428 commits — 87% above your median month, then it drops back. What changed, and did the
   output survive?
2. **Why did attribution appear in June?** The `SASE_AGENT=` trailer starts in June 2026 and now covers 1,720 commits in
   a month. Something went wrong that made "which agent wrote this?" an urgent question. That story is the whole
   argument for durable agent records, told as an incident instead of a feature.
3. **Why is there more test code than source code?** 1.07:1 from a solo developer is not normal. Did agents write tests
   to make checks pass, and how much of that 467k lines is real coverage versus slop? You already have a word for the
   answer.
4. **6,002 plans for 2,230 beads.** Roughly 2.7 plan documents per unit of tracked work. What is the actual yield of
   SDD, and what fraction of those plans were never executed?
5. **What does 226 agent runs a day cost?** In dollars, in attention, in review capacity. Nobody publishing in this
   space has answered that with real data.

---

## 5. You Already Wrote the Good Lines

These are all yours, already on disk, and none of them appear in any post. This is the strongest evidence that the
problem is not "can't write" — it's that the writing never got connected to the artifact.

> *"I'm bad at naming things but I worry that indicates a deeper problem with the design."*

> *"I could say that it was the obvious need for structure I saw while working at Google or that I saw an opportunity
> to add some value but the truth is ..."*

> *"Goal number two: make the prompt input widget so fucking awesome that using any other editor for agent prompts is
> unthinkable."*

> *"Plan mode is the canonical or best example of some deeper primitive. I know it. Interrupts?"*

> *"sase does not claim optimal performance, but optimal experience."*

> *"Alternations allow for 'vibe evals'."*

> *"Accumulated degradation in alignment due to bad prompting and/or bad code review practices. AKA **prompt debt**."*

> *"End with 'no weasels; just work'."*

Two of these — **prompt debt** and **vibe evals** — are original coinages in a space that is starved for vocabulary.
The first is the single most valuable thing in your notes: a name for the specific decay that happens when agents build
on prior agent output under drifting instructions. That term could outlive the tool.

Also note that the unfinished sentence — *"but the truth is ..."* — is your opening line. You wrote it, trailed off, and
filed it under "obsolete notes." It is not obsolete. It is the only sentence in the entire corpus that makes a reader
need the next one.

---

## 6. The Landscape You're Launching Into

### Competitors

The category filled in during 2026 and is now crowded with worktree-per-agent tools plus a UI: Conductor (Melty Labs,
free Mac app for parallel Claude Code sessions), Composio's open-source Agent Orchestrator, Emdash, Baton, and OpenClaw
as the giant by adoption. Cursor, OpenAI, Windsurf, and GitHub all shipped parallel-agent workflows.

**Implication:** a feature-tour launch post competes directly on features with better-funded projects, and loses. It
also invites the wrong comparison ("how is this different from Conductor?") in the first comment.

**What none of them have:** five months of continuous single-operator use at ~200 agent runs a day, with the plans,
beads, and commit trail preserved. Duration and volume are your only uncontested ground.

### The conventional wisdom you can answer

Addy Osmani's *The Code Agent Orchestra* is the canonical statement of what multi-agent coding needs: shared task lists
with dependency tracking and automatic unblocking, peer-to-peer agent messaging, file locking, quality gates (plan
approval, hooks, human review), persistent memory via `AGENTS.md`, and worktree isolation — with the thesis that **the
bottleneck has moved from generation to verification**.

SASE has shipped essentially that entire list: beads with dependency-aware readiness, plan approval and launch approval
gates, `sase init`-managed `AGENTS.md` and provider shims, workspace isolation, fix hooks and mentors for verification.

That is the wedge, and it's a good one: **the industry is publishing the specification; you have the implementation and
five months of operating data.** "Here is the orchestration checklist everyone agrees on — here is what happened when
one person actually built all of it and lived inside it" is a post that only you can write, and it positions SASE
against the discourse rather than against Conductor's feature list.

### The AI-slop hazard (the reason this post specifically must be yours)

July 2026 is a bad month to publish machine prose. Substack shipped AI detection on 2026-07-21. Research on HN and
Reddit found the share of accusations using pejorative "AI slop" labels rose more than tenfold. The consistent finding
is that **the contempt attaches to the writer, not the writing** — readers don't conclude "clever tool use," they
conclude the author couldn't be bothered.

For a generic product this is a reputational cost. For SASE it is an existential argument: a tool that claims to make
agent output *reviewable and trustworthy*, launching with unreviewed agent output, refutes its own thesis in public. The
first comment writes itself.

The inverse is also true, and it's an opportunity: **a post that openly catalogues the AI slop in its own
agent-generated codebase is unfakeable.** It's the strongest possible proof that you actually review what your agents
produce — which is precisely what you're selling.

### Launch mechanics

For the Show HN, the consistent guidance: clear literal title with no superlatives (no "fastest," "first," "best"),
link the GitHub repo, go deep on technical detail rather than pitch, post Tue–Thu 9am–12pm ET, and be present in the
comments for the first 60 minutes. Modest language outperforms confident language with this audience.

---

## 7. Recommendations

### R1. Write the ledger post, not the tour post — and let the tour become docs

**Working title:** something literal and unsuperlative. Candidates:

- *"Five months, 11,192 commits, and a tool for supervising the agents that wrote them"*
- *"What 200 agent runs a day actually looks like"*
- *"I let coding agents write 890,000 lines. Here's the part nobody shows you."*

**Thesis:** The hard problem stopped being "can the model write the patch" months ago. It's "where did the patch go,
what was it trying to do, and how do I know it isn't slop." SASE is what one person built after five months of that
problem at ~200 agent runs a day — and here is the evidence, including what it cost and what's still broken.

**Why this beats the feature tour:**

- It explains the features *as consequences*, which is the only structure where a reader retains them. `%wait` isn't a
  directive, it's what you built the night ordering broke. ChangeSpecs aren't a data model, they're what you added when
  you lost a diff.
- It cannot be generated. The facts are in your head and `~/.sase`.
- It inoculates against the slop critique instead of inviting it.
- It puts you on ground no competitor can contest.

**Section beats:**

1. **The truth is...** — Finish that sentence. Boris's method → `tmux_ai_window` → the moment it stopped scaling. (You
   already have the strongest paragraph in the corpus here; keep it nearly verbatim.)
2. **The ledger** — The numbers from §4, with the caveats stated. One table, no commentary needed; the table is the
   argument.
3. **What broke, in order** — 4–6 concrete failures, each introducing the piece of SASE that exists because of it. This
   is the whole feature tour, smuggled in as narrative. Use the screenshots you've already flagged: the Claude outage
   where retries saved you (2026-06-16), the `%wait` example, the questions/retries/tales example.
4. **Prompt debt, and the slop in my own codebase** — Your four categories, with a real example of each from the SASE
   tree. This is the section people will quote.
5. **What's still bad** — The limitations list you asked for and never got. Start with "the Agents tab is the buggiest
   part of the TUI," which you already wrote.
6. **What it is, concretely** — The shortest possible "here's what SASE actually does," then `uv tool install sase` and
   links to docs. Fewer than 400 words. The docs already do this well.
7. **No weasels; just work.** — Your ending. Use it.

**Target: 2,000–2,500 words.** The July draft's own review dinged 5,400 words / 20 sections; don't rebuild that.

### R2. Quarantine the ten drafts before you write anything

As long as `[00]`–`[09]` sit in `docs/blog/posts/`, "write the post" feels like "edit ten posts," and you will keep
cancelling the task. They are not drafts of your blog; they are a simulation of one, and they were built to a contract
that no longer applies.

Simplest correct move: delete them from the working tree. Git history keeps every word, and `git log --diff-filter=D`
plus `git show` recovers any of them in seconds if you ever want a paragraph back.

```bash
cd docs/blog/posts
git rm why-coding-agents-need-orchestration.md hello-sase-your-first-15-minutes.md \
       xprompts-in-depth.md axe-background-daemon.md beads-and-sdd.md \
       commit-workflows-plugins.md changespecs-in-practice.md \
       telegram-mobile-agents.md prompt-widget-and-nvim.md whats-next-memory-mobile-web.md
```

If deleting feels too final, move them to a non-`docs/` path in this same repo (they can't be `git mv`'d into
`sase/repos/research/`, which is a separate sidecar clone). Either way, `just docs-check` runs mkdocs `--strict`, so
fix `docs/blog/index.md` and any cross-links in the same commit or the build fails. Keep `[01] Hello, SASE` content alive only by folding the
accurate parts into `docs/getting_started.md`, which your own note already asked for
(*"Move 15-minute install post to 'Getting Started' section and remove blog series page!"*).

### R3. Reuse the one method that worked: dictate it

Your ledger contains exactly one blog task that completed on schedule with no agent involvement: *"Do a WisprFlow
brain-dump on what the first blog post should contain"* — created 2026-06-11, done 2026-06-14. Every subsequent
approach has been generate-then-approve, and every one has stalled.

**Protocol:**

1. Close the editor. Open the ledger table from §4 and your quotes from §5 on screen. Nothing else.
2. Dictate for 20–30 minutes, answering only the five questions in §4 and the six section beats in R1. Do not stop to
   fix anything. Rambling is the point — your prompt files show your natural register is direct, run-on, and concrete,
   which is exactly the register that reads as human.
3. Transcribe verbatim. **That transcript is the draft**, not an input to a draft.
4. Cut it down yourself. Cutting your own words is a task you can actually finish; approving someone else's is the one
   you've cancelled four times.

Evidence this is your real voice: your own launch-post prompt reads *"Reference the tmux_ai_window script in my Cheetos
repo"* — a dictation artifact for "chezmoi." That sentence is unmistakably a person. Nothing in 2,417 lines of drafts
sounds like it.

### R4. Change the agents' job from writer to fact-checker

Agents are genuinely good at the parts you'll get wrong, and that's where to spend them:

| Give the agents                                                            | Keep for yourself      |
| --------------------------------------------------------------------------- | ---------------------- |
| Verify every command, flag, and keymap against current source                | Every sentence         |
| Re-derive every statistic and flag the ones that don't reproduce             | Which stats to include |
| Find `file:line` citations for claims you make from memory                   | The claims             |
| Check that no example in the post fails when run                             | The examples' point    |
| Flag terminology drift (companion→sidecar, provider names, `gemini`)          | The terminology        |

The hard constraint from the July plan is still right and worth re-stating: never present `gemini` as a supported CLI;
the five are `claude`, `codex`, `agy`, `qwen`, `opencode`.

### R5. Ship the limitations section — here's the seed

You've asked for this list three times since June 7 and never received it. Starting set, all from your own notes and
the July 2 audit:

- The Agents tab is the buggiest part of the TUI. *(your note, 2026-06-18)*
- XPrompt authoring fails silently in every common mistake mode: unknown `#name` passes through to the model, malformed
  YAML makes a definition vanish from `sase xprompt list`, name shadowing is silent. *(`blog_launch_readiness_audit.md`)*
- Config YAML errors are swallowed at debug level; unknown keys are dropped with no diagnostic and there is no
  `sase config validate`.
- Alpha software: interfaces and workflows still change. POSIX only.
- No custom crash screen; unhandled TUI exceptions surface as a raw Textual traceback.
- You inherit provider pricing and policy changes you don't control.
- The naming is a genuine open problem, and you suspect it points at a design problem. *(your quote — publish it)*

A limitations section is the cheapest credibility purchase available, and it's the section agents will never write for
you.

### R6. Fix the `#cd` isolation claim before the post ships (blocking)

From `blog_launch_readiness_audit.md` (2026-07-02): `docs/blog/posts/hello-sase-your-first-15-minutes.md` tells readers
that `sase run` gives them an isolated workspace clone, while its examples use `#cd:$(pwd)`, which deliberately skips
workspace allocation and edits the reader's real checkout
(`src/sase/workspace_provider/plugins/cd_workspace.py:61-71`; `docs/workspace.md:130-133`).

Any launch drives traffic to the quickstart. Shipping a post that funnels new users into a page that promises a sandbox
and doesn't provide one is the one item here that can't wait. If R2 removes that post from `docs/blog/`, confirm the
same claim isn't carried into `docs/getting_started.md`.

### R7. Keep the July 8 post — as documentation

`structured-agentic-software-engineering.md` is genuinely good reference material and shouldn't be deleted. It is
accurate, well-organized, and covers the four topics you scoped. It just isn't a blog post; it's an overview page with a
date on it.

Retitle it "SASE Overview," move it into `docs/` beside `architecture.md`, and let the new ledger post link to it as
"if you want the full tour." You lose nothing and you stop trying to make one artifact do two incompatible jobs.

### R8. Voice checklist — run this on any paragraph before it ships

If a paragraph fails two or more, it's agent prose regardless of who typed it:

1. **Could this sentence appear in the docs?** If yes, cut or move it.
2. **Is there a date, a number, or a name in this paragraph?** Specificity is the cheapest humanity signal you have —
   and you have more of it available than almost anyone writing in this space.
3. **Does it admit anything?** A paragraph with no cost, no failure, and no doubt was written by something that has
   never had a bad week.
4. **Does it end on an aphorism?** "That boundary is the whole trick." / "The row already knows." / "Small is often the
   point." Three in the current post. Delete every one; they're transitions pretending to be insights.
5. **Is the humor load-bearing?** A joke about something that actually happened works. A joke in a joke-shaped slot
   ("Technically it is not haunted. Usually.") reads worse than no joke.
6. **Does it use "honest," "boring," or "the trade-off is" as a credibility move?** Show the trade-off; don't announce
   that you're about to be honest about one.
7. **Would you say this out loud?** The dictation test. If not, rewrite it as what you'd actually say.

---

## Appendix A: Re-Deriving the Numbers

```bash
# Commits, timeline, monthly distribution
git rev-list --count HEAD
git log --reverse --format='%h %ad %s' --date=short | head -1
git log --format='%ad' --date=format:'%Y-%m' | sort | uniq -c

# Agent-attributed commits
git log --format='%B' | grep -c '^SASE_AGENT='

# Lines of code
tokei src | tail -3
tokei tests | tail -3

# SDD corpus
wc -l sase/repos/beads/issues.jsonl                     # beads
find sase/repos/plans/2026* -name '*.md' | wc -l         # plans
find sase/repos/research -name '*.md' | wc -l            # research

# Agent runs (note: ~/.sase prunes; this is a ~23-day window, not a total)
find ~/.sase/projects/*/artifacts -maxdepth 5 -type d \
  -regextype posix-extended -regex '.*/[0-9]{14}$' \
  | grep -oE '[0-9]{14}$' | cut -c1-8 | sort | uniq -c

# Blog corpus provenance
git log --diff-filter=A --format='%ad %h %s' --date=short -- docs/blog/posts/
```

## Appendix B: Source Material Locations

| What                                        | Where                                                          |
| -------------------------------------------- | -------------------------------------------------------------- |
| Your outline, requirements, and quotes       | `bob:sase_blog.md`, `bob:sase_blog_0.md`                        |
| Your abandoned opening line, "no weasels"    | `bob:sase_blog_0_legacy_notes.md`                               |
| Stalled proofread annotations (2 highlights) | `bob:ref/docs/sase_blog_260708.md`                              |
| Screenshots you flagged as good examples     | `~/tmp/screenshots/20260616_140429.png` (Claude outage retry), `20260616_115015.png` (`%wait`), `20260624_074728.png` (questions/retries/tales), `20260619_214831.png` (alternations) |
| The plan that generated the May series       | `sase/repos/plans/202605/new_blog_posts.md`                     |
| The plan that generated the July post        | `sase/repos/plans/202607/first_blog_post.md`                    |
| Prior launch-readiness audit (still valid)   | `sase/repos/research/202607/blog_launch_readiness_audit.md`     |
| Existing demo media                          | `demos/out/` (5 GIF/MP4 pairs, regenerable via `just demos`)    |

## Sources

- [The Code Agent Orchestra — Addy Osmani](https://addyosmani.com/blog/code-agent-orchestra/)
- [9 Open-Source Agent Orchestrators for AI Coding (2026) — Augment Code](https://www.augmentcode.com/tools/open-source-agent-orchestrators)
- [Best Multi-Agent Coding Tools for Claude Code and Codex Users (2026) — Nimbalyst](https://nimbalyst.com/blog/best-multi-agent-coding-tools-2026/)
- [AI Agent Orchestration Tools for Coding (2026) — Tembo](https://www.tembo.io/blog/ai-agent-orchestration-tools)
- [The AI Slop Backlash Is Here — Superframeworks](https://superframeworks.com/articles/ai-slop-backlash-judgment-moat)
- ["That's AI Slop, You Bot!" — accusations, evidence, and credibility in online discourse](https://www.researchgate.net/publication/406909613_That's_AI_Slop_You_Bot_Studying_Accusations_Evidence_and_Credibility_in_Online_Discourse_Towards_LLM-Generated_Comments)
- [AI slop writing has taken over the internet — The Register](https://www.theregister.com/ai-and-ml/2026/07/09/ai-slop-writing-has-taken-over-the-internet/5269525)
- [Hacker News Marketing for Developer Tools — daily.dev](https://business.daily.dev/resources/hacker-news-marketing-developer-tools-show-hn-launch-day-sustained-coverage/)
- [How to launch a dev tool on Hacker News — markepear](https://www.markepear.dev/blog/dev-tool-hacker-news-launch)
