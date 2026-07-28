---
create_time: 2026-07-28
updated_time: 2026-07-28
status: research
---

# The Authorship Gap: Finishing SASE's First Blog Post

Consolidated from two independent research reports ([`__a`](first_post_authorship_gap__a.md) by `research.@.cdx`,
[`__b`](first_post_authorship_gap__b.md) by `research.@.cld`) plus a third verification pass. All figures re-derived
against this workspace on 2026-07-28.

## Research Question

Bryan is stuck writing SASE's first blog post. Every piece of blog content in the repo is agent-generated. What is
actually blocking it, and what is the smallest set of actions that produces a publishable post?

## Bottom Line

1. **The block is an ownership gap, not a blank page.** Both reports reached this independently, and the evidence
   holds up under direct verification: in your Obsidian ledger, *every* task where an agent produces text completed
   (usually in a day); *every* task where you must judge or own text was cancelled or stalled. Four cancelled/stalled
   since June 5. The one blog task that finished on time without an agent was the WisprFlow brain-dump.

2. **But both reports want to overturn a decision you already made — and they shouldn't.** Report A says write an
   origin story instead of a tour. Report B says write a statistics "ledger post" instead of a tour. Neither noticed
   that **the tour structure is yours**: `sase_blog_0.md` has an `## Outline` section — Introduction → Overview →
   XPrompts → ACE → AXE → Future Blog Posts — attached to a task you deliberated on for 19 days and marked done on
   2026-07-07. The July post follows it faithfully. The agents did not impose the structure; they executed it.

3. **You are not starting from zero. You are ~470 words in, and those are the hard words.** Lines 19–64 of the July
   post contain the `tmux_ai_window` scene, the 😈/😇 bullets you asked for, and the one sentence in the corpus that is
   unmistakably yours. Report A grades this opening as "promising"; Report B says keep it "nearly verbatim." They
   agree. The failure is everything *after* line 64 — 83% of the post is product tour with no human layer.

4. **What is actually missing is a layer you specified and never delivered.** Two subtasks under your own completed
   outline task are still unchecked: *"Flesh out 'high value, high untapped opportunity, and an associated lesson
   learned' for each section"* and *"Describe demo video and infographic for each main section."* Add the
   `sase_blog.md` Requirements the agents dropped (limitations list, AI slop, the naming jokes, the Gas Town
   comparison) and you have the complete gap. It is bounded and fill-in-the-blank — not another essay.

5. **This is the third launch cycle, not the first.** The `[00]` essay was published live on 2026-05-09, rewritten
   2026-06-14, then retracted on 2026-07-08 by the same commit that shipped the current post. The recurring failure
   mode is *replace rather than own*: when the proofread stalls, the resolution has been to generate a new post and
   retire the old one. Absent intervention, the next thing that happens is a fourth draft. **More research is the
   failure mode, not the fix.**

6. **Everything except the writing is done.** Every launch blocker that prior audits flagged has since been fixed —
   including the `#cd` isolation bug Report B lists as its one blocking item (fixed 2026-07-09). Details in §7.

---

## 1. Verified Inventory

`docs/blog/posts/` holds eleven files, 2,417 lines, 20,501 words.

| Date       | Draft | Lines | Words | Title                                                       |
| ---------- | ----- | ----: | ----: | ----------------------------------------------------------- |
| 2026-05-08 | ✔     |   626 | 5,353 | [00] The Missing Operating Layer for Coding Agents           |
| 2026-05-10 | ✔     |   205 | 1,610 | [01] Hello, SASE — Your First 15 Minutes                     |
| 2026-05-12 | ✔     |   178 | 1,377 | [02] XPrompts in Depth                                       |
| 2026-05-14 | ✔     |   123 | 1,075 | [03] AXE — The Background Daemon                             |
| 2026-05-16 | ✔     |   133 | 1,201 | [04] Beads and SDD                                           |
| 2026-05-18 | ✔     |   164 | 1,393 | [05] Commit Workflows                                        |
| 2026-05-20 | ✔     |   188 | 1,328 | [06] ChangeSpecs in Practice                                 |
| 2026-05-21 | ✔     |   172 | 1,719 | [07] Driving SASE From Your Phone                            |
| 2026-05-22 | ✔     |   167 | 1,760 | [08] Where You Type                                          |
| 2026-05-23 | ✔     |   109 |   923 | [09] What's Next                                             |
| 2026-07-08 | —     |   352 | 2,762 | **SASE: Structured Agentic Software Engineering** (published) |

Two corrections to the source reports: Report A's "ten drafted blog posts totaling about 20,500 words" is actually all
*eleven* files; the ten drafts are 17,739 words. Report B attributes a "5,400 words / 20 sections" review to the July
draft — that review (`202606/blog00_launch_post_review_consolidated.md`) covered the **`[00]` draft** (5,353 words,
20 sections). The July post is 2,762 words in 6 sections.

**The ten drafts are already invisible to readers.** All carry `draft: true`, so the mkdocs-material blog plugin
excludes them; `site/blog/posts/` contains only `structured-agentic-software-engineering`. This matters for weighing
Report B's "delete them" recommendation (§8, R3).

### Provenance confirms the corpus is docs re-narrated

Report B's provenance finding is correct and is the single most useful piece of forensics in either report. The
`[00]`–`[09]` series was not written across sixteen days in May — it was written across four, with six posts landing in
one commit (`26a2aeb23`). Its generating plan, `sase/repos/plans/202605/new_blog_posts.md`, says so in its own words:

> "Section skeleton fleshed out with on-topic prose **pulled from the relevant product doc**."
>
> "Dates step every other day so the archive page reads as **a deliberate series rather than a same-week dump**."

A May 10 commit is literally `chore: warm up tone of "Hello, SASE" first-15-minutes post` — voice applied as a lint
pass. Two drafts now carry terminology patch notes ("companion repos are now called sidecar repos"): they are being
maintained like source files, which is the tell that they are documentation, not writing.

Worth noting the staggered dates were staged for an archive page that `mkdocs.yml` now disables (`archive: false`).

---

## 2. The Diagnosis, Verified

Report B's central claim is the strongest finding across all three passes. I re-ran it against the vault directly:

| Task                                             | Created    | Outcome                        |
| ------------------------------------------------ | ---------- | ------------------------------ |
| Plan first blog post                              | 2026-06-05 | **cancelled** 2026-06-13       |
| Move sase tasks to sase_blog                      | 2026-06-07 | done same day                  |
| WisprFlow brain-dump on what the post should contain | 2026-06-11 | **done** 2026-06-14 (by hand) |
| Migrate note in pocket to Obsidian tasks          | 2026-06-15 | **cancelled** 2026-06-29       |
| Decide on the blog posts' outline                 | 2026-06-18 | done 2026-07-07 (19 days late) |
| Proofread blog post                               | 2026-06-19 | **cancelled** 2026-06-29       |
| Convert sase_blog_0 into a project                | 2026-06-24 | done 2026-06-25                |
| Use Fable to generate first draft                 | 2026-07-07 | done 2026-07-08 (**1 day**)    |
| Proofread blog post                               | 2026-07-08 | **stalled**, scheduled 07-26   |

Agent-produces-text → completes. You-must-own-text → cancelled or slips. The current proofread has physical evidence of
stalling: `ref/docs/sase_blog_260708.md` holds two highlights and exactly one comment — *"Add bullets (devil + angel)
that describe why `%wait` and `#fork` are needed!"* — attached to the one sentence in the post that is actually yours
(*"That got me a long way. It also made the missing layer painfully obvious."*). Then it stops. Twenty days, one
comment.

Both reports draw the right conclusion: editing prose into your voice requires the voice to already be on the page.
When it isn't, every sentence is a decision with no criterion, and there are 352 of them.

**Note what that single comment asks for, though.** It does not ask to restructure. It asks to *extend the 😈/😇
pattern to `%wait` and `#fork`*. Your one editorial instinct in twenty days was additive and local. That is a strong
signal about the shape of the work you can actually finish — and an argument against both reports' "start over
differently" framing.

---

## 3. The Correction Both Reports Need: The Outline Is Yours

Neither prior report read `sase_blog_0.md`'s `## Outline` block. It is the decisive artifact.

```text
- Introduction
    - Boris method -> tmux_ai_window -> auto-approve plans -> wait / fork -> ...
- Overview
- XPrompts
    - Editor Tooling ... Directives ... Alternations ... Argument Types ... Workflows ... "Special" XPrompts
- ACE
    - Focuses mainly on Agent (Tab / Families / Hoods), but also touches on PRs tab, notification panel ... AXE tab
- AXE
    - Sub-section that focuses on sase-telegram!
- Future Blog Posts
    - Beads and SDD / Memory / Mobile / Evals / ChangeSpec / SASE's Architecture
```

The July post's actual sections: Intro → SASE Wraps Agent CLIs (Overview) → XPrompts → The Agents Tab in ACE →
Install → What's Next. **That is your outline.** You decided it on 2026-07-07 after 19 days, then generated a draft
against it the next day.

This reframes both source reports:

- **Report A** recommends replacing the tour with a personal origin story, on the grounds that the tour is "a
  compressed manual." The critique of the *execution* is sound. The prescription overturns your structural decision.
- **Report B** recommends replacing the tour with a "ledger post" built on repo statistics. The statistics are real and
  genuinely uncontested ground (§5) — but nothing in your notes asks for that post. It is Report B's idea, argued well
  enough to be persuasive, and it would restart the outline decision you already spent 19 days closing.

The post is also explicitly **post 0 of a series** (`sase_blog.md`: "Publish the full sase.sh blog series",
sub-project `sase_blog_0`). A broad front-door overview that forward-references later posts is the *correct* shape for
post 0. The tour is not a mistake; it is the assignment.

**Keep the structure. Fill the layer that's missing from it.**

---

## 4. What Is Actually Missing

### 4a. Your own unchecked subtasks

Under the completed outline task, two subtasks remain open:

1. *"Flesh out 'high value, high untapped opportunity, and an associated lesson learned' for each
   `[[sase_blog_0#^outline]]` section."*
2. *"Describe demo video and infographic for each main section."*

Item 1 **is the missing human layer**, specified by you, in your own framing, per section. Six sections × three fields
= eighteen short answers. That is the whole job. It converts each tour section from "here is a feature" into "here is
what this cost me to learn," which is precisely what both reports are groping toward — without discarding your outline.

### 4b. Requirements the agents dropped

Report B's dropped-requirements table is accurate; I verified every row against `sase_blog.md` and
`sase_blog_0_legacy_notes.md`.

| Requirement                                                                  | In any post? |
| ---------------------------------------------------------------------------- | ------------ |
| Break down Gas Town differences (beads, rigs, no mayor)                       | ✗            |
| "Mention that the agents tab is the buggiest part of the TUI!"                | ✗            |
| "Create list of limitations!"                                                 | ✗            |
| "Make jokes about why sase and xprompts are named the way they are."          | ✗            |
| "Add a definition of what I consider to be AI slop and how it shows up in sase's codebase." | ✗ |
| Categories of AI slop (backcompat, dead features, duplication, prompt debt)   | ✗            |
| "Alternations allow for *vibe evals*"                                         | ✗            |
| "sase does not claim optimal performance, but optimal experience"             | ✗            |
| Devil/halo emoji bullets · `tmux_ai_window` in intro · citations · TUI media  | ✓            |

Everything kept is a feature explanation. Everything dropped is an admission, a joke, an opinion, or a scar. As Report
B correctly argues, this follows mechanically from the method: when the instruction is "flesh out these sections with
prose pulled from the relevant product doc," documentation is the only source, and documentation has no record of what
is broken, regretted, or funny. Re-prompting cannot fix it. The material is in your head.

### 4c. Assets: scaffolded, unrendered

Your requirement *"Use multiple (3?) funny AI-generated diagrams"* is further along than either report noticed — and
also stalled in the same way:

- Three diagram briefs exist: `docs/images/blog/{window_farm_vs_control_tower,one_prompt_five_clis,prompt_burrito}.prompt.md`
- Three matching `<!-- DIAGRAM: ... -->` placeholders sit at exact insertion points in the post (lines 63, 105, 221)
- **Zero rendered PNGs.** Each brief says "Current status: prompt brief only; raster generation is a follow-up."

This is the cleanest delegatable task in the whole project.

⚠️ **Correction to Report B's Appendix B:** the four screenshots you flagged in your notes
(`~/tmp/screenshots/20260616_140429.png` and three others) **no longer exist** — `~/tmp` has been cleaned. If you want
the Claude-outage retry, `%wait`, questions/retries/tales, or alternations examples, they must be re-captured. The
"Include TUI screenshots" requirement is otherwise substantially met: the July post already embeds five GIFs/stills,
and `demos/out/` holds five regenerable GIF/MP4 pairs (`just demos`).

---

## 5. The Ledger: Material Only You Have

Report B's strongest constructive contribution. Re-verified 2026-07-28; commands in Appendix A.

| Fact                        | Value                                                    |
| --------------------------- | -------------------------------------------------------- |
| First commit                | 2026-02-14 (`7559fe4f5`, "chore: Init beads")             |
| Commits                     | **11,193** in ~5.5 months                                 |
| Commits by month (Feb→Jul)  | 769 / 1,659 / 1,642 / **3,428** / 1,812 / 1,883           |
| Python source               | 430,694 lines across 2,463 files                          |
| Python tests                | 464,659 lines across 2,408 files                          |
| Test-to-source ratio        | **1.08 : 1**                                              |
| Beads                       | 2,230                                                     |
| Plan documents              | 6,003                                                     |
| Research reports            | 292                                                       |
| Commits signed `SASE_AGENT=`| 1,954 — all since June 2026                               |
| Agent runs, 23-day window   | 5,282 total; ~226/day; peak **496 on 2026-07-18**         |
| Supported provider CLIs     | 5 (`claude`, `codex`, `agy`, `qwen`, `opencode`)          |

🔴 **Fix before publishing any of these:** Report B's headline "891,646 lines of code" does not reconcile with its own
table (which sums to 903,285), and neither figure matches a clean re-derivation. The discrepancy is a `tokei` reading
error — it pairs the all-language **Total** row with the **Python** file count. Use one of these, labelled:

- **895,353** — Python code lines (src 430,694 + tests 464,659)
- **903,680** — all-language code lines (src 436,388 + tests 467,292)

This is exactly the number a Hacker News reader will recompute. Both reports are right that publishing the caveats
buys more credibility than the number: run counts include hook runs and workflow steps; `~/.sase` prunes, so 5,282 is a
23-day window and not a total; line counts include generated and test code.

### The five questions the numbers raise

Each is a question only you can answer, and each is section-4a material:

1. **What happened in May?** 3,428 commits — 87% above your median month — then it drops back.
2. **Why did attribution appear in June?** `SASE_AGENT=` starts in June and covers 1,720 commits in a month. Something
   made "which agent wrote this?" urgent. That is the whole argument for durable agent records, told as an incident.
3. **Why is there more test code than source code?** 1.08:1 from a solo developer is not normal. How much of 464k lines
   is coverage versus slop? You already have a word for the answer.
4. **6,003 plans for 2,230 beads** — 2.7 plans per unit of tracked work. What is SDD's actual yield?
5. **What does 226 agent runs a day cost** — in dollars, attention, and review capacity? Nobody in this space has
   published that with real data.

---

## 6. You Already Wrote the Good Lines

All verified present in the vault; none appear in any post. This is the clearest evidence the problem is not "can't
write" — it is that the writing never got connected to the artifact.

> *"I'm bad at naming things but I worry that indicates a deeper problem with the design."*
>
> *"I could say that it was the obvious need for structure I saw while working at Google or that I saw an opportunity
> to add some value but the truth is ..."*
>
> *"Goal number two: make the prompt input widget so fucking awesome that using any other editor for agent prompts is
> unthinkable."*
>
> *"Plan mode is the canonical or best example of some deeper primitive. I know it. Interrupts?"*
>
> *"sase does not claim optimal performance, but optimal experience."*
>
> *"Alternations allow for 'vibe evals'."*
>
> *"Accumulated degradation in alignment due to bad prompting and/or bad code review practices. AKA **prompt debt**."*
>
> *"End with 'no weasels; just work'."*

**Prompt debt** and **vibe evals** are original coinages in a space starved for vocabulary. Prompt debt — a name for
the decay that happens when agents build on prior agent output under drifting instructions — is the most valuable thing
in your notes and could outlive the tool.

And the unfinished sentence, *"...but the truth is ..."*, is filed under `sase_blog_0_legacy_notes.md`. Report B is
right that it isn't obsolete: it is the only sentence in the corpus that makes a reader need the next one.

---

## 7. The Landscape

Both reports researched this independently and their findings compose rather than conflict.

**The category filled in during 2026.** Report A documents the incumbents: the OpenAI Codex app (parallel agents,
isolated-worktree diff review, reusable skills, scheduled automations — its announcement explicitly says the challenge
has shifted from what agents can do to how people supervise them at scale), Claude Code (agent view for background
sessions, parallel worktrees, subagents, experimental agent teams), and GitHub's Agents tab. Report B adds the
independents: Conductor, Composio's Agent Orchestrator, Emdash, Baton, and OpenClaw.

**Consequence, on which both agree:** do not build the post on parallel agents, isolated workspaces, one-pane
observability, reusable instructions, or background execution. Those are now category expectations, and a feature-tour
framing invites "how is this different from Conductor?" as the first comment.

**The wedge.** Report B's is sharper: Addy Osmani's *The Code Agent Orchestra* is the canonical published spec for what
multi-agent coding needs — dependency-tracked shared task lists, quality gates, persistent memory via `AGENTS.md`,
worktree isolation — with the thesis that the bottleneck moved from generation to verification. SASE has shipped
essentially that entire list. *The industry is publishing the specification; you have the implementation and five
months of operating data.* Report A's complementary framing: the durable, harder-to-commoditize claim is
independence — local, provider-neutral, git-native, owner-controlled workflow state — which also invites honest
trade-off discussion (you inherit the rough edges of the CLIs you wrap).

**The AI-slop hazard.** Report B's argument here is the most launch-critical thing in either document and Report A does
not cover it. July 2026 is a bad month to publish machine prose: Substack shipped AI detection on 2026-07-21, and
research on HN and Reddit found pejorative "AI slop" accusations rose more than tenfold, with contempt attaching to the
*writer*, not the writing. For a generic product that is a reputational cost. For SASE it is self-refuting: a tool
selling *reviewable, trustworthy agent output*, launching with unreviewed agent output, loses the argument in the first
comment. The inverse is the opportunity — **a post that openly catalogues the AI slop in its own agent-generated
codebase is unfakeable**, and is the strongest available proof that you review what your agents produce.

**Show HN mechanics** (Report B): literal title, no superlatives, link the repo, go deep on technical detail rather
than pitch, post Tue–Thu 9am–12pm ET, be present in comments for the first 60 minutes.

---

## 8. Launch Mechanics: Already Clean

Prior audits flagged several blockers. **All are fixed.** Do not spend time on these.

| Item                                            | Status                                                        |
| ----------------------------------------------- | ------------------------------------------------------------- |
| `#cd` promises a sandbox, edits the real checkout | ✅ **Fixed 2026-07-09** — `f150306ce feat!: remove directory workspace xprompt` removed the plugin entirely; the quickstart now uses the genuine `#git:home` sandbox |
| Quickstart should fold into Getting Started      | ✅ Done — `docs/getting_started.md` exists; `_redirects` 301s the old post URL |
| No `LICENSE` file while PyPI claims MIT          | ✅ Fixed — `LICENSE` present, `pyproject.toml` declares MIT     |
| No Open Graph / Twitter-card metadata            | ✅ Fixed — `docs/overrides/main.html` emits full `og:` tags     |
| `[00]` post renders no images                    | ✅ Moot — the July post embeds five GIFs/stills                 |
| Retracted `[00]` URL will 404                    | ✅ Handled — `docs/_redirects` 301s to the new post             |

🔴 **This is a correction to Report B's R6**, which presents the `#cd` issue as "blocking" and "the one item here that
can't wait." It cites `blog_launch_readiness_audit.md` (2026-07-02); the fix landed a week later. Report B also
references `just docs-check` — no such recipe exists, and the justfile has no docs targets at all. The strictness is
real, though: `mkdocs.yml` sets `strict: true`, so broken cross-links fail the build.

**The takeaway is motivating: the only thing standing between you and a published post is your own text.**

---

## 9. The Replace-Don't-Own Cycle

Neither source report surfaced this, and it is the reason to be careful about what happens next.

| Date       | Event                                                                                  |
| ---------- | -------------------------------------------------------------------------------------- |
| 2026-05-09 | `2bb581fcb chore: publish coding agent orchestration essay` — **`[00]` goes live**       |
| 2026-06-06 | `b1d537da4 chore: hide unpublished blog posts` — the other nine hidden                   |
| 2026-06-14 | `e96510106 docs: rewrite SASE launch essay` — rewritten in place, after the June review  |
| 2026-06-19 | Proofread task **cancelled**                                                             |
| 2026-07-08 | `a280878c3 docs: publish SASE launch post` — sets `draft: true` on `[00]`, **retracting it**, and ships the new post |
| 2026-07-28 | Proofread task open 20 days, one annotation                                              |

SASE's "first blog post" has already been published once and retracted, and rewritten once more. Each time the
proofread stalls, the resolution has been to *generate a replacement* rather than finish the existing text. Three
cycles in three months.

This predicts the next event precisely: absent a change of method, cycle four is another generated draft. It is also
the strongest argument against acting on the most seductive recommendation in either source report — **both A and B
propose a new post with a new structure, which is cycle four wearing better clothes.**

---

## 10. Recommendations

### R1. Finish your own outline task, by dictation — one 45-minute session

The single highest-value action. Do not open the post. Open `sase_blog_0#^outline` and dictate three answers for each
of the six sections:

> **High value** — what does this section's feature actually buy me?
> **High untapped opportunity** — what could it do that it doesn't yet?
> **Lesson learned** — what did it cost me to figure this out? What broke first?

Eighteen short answers, ~4 minutes each. Dictation is non-negotiable: it is the only blog method in your ledger that
ever completed on time (the WisprFlow brain-dump, 2026-06-11 → 06-14). Evidence it is your real register — your own
launch-post prompt reads *"Reference the tmux_ai_window script in my Cheetos repo,"* a dictation artifact for
"chezmoi." That sentence is unmistakably a person; nothing in 2,417 lines of drafts sounds like it.

Rules, merged from both reports: do not open any existing draft; do not look up commands, dates, or names; do not
polish; mark uncertainty instead of stopping to research it; include details that seem too small. **Transcribe
verbatim — the transcript is the source, not an input to a draft.**

Report A's ten origin-story questions remain excellent, but use them as *warm-up* for the Introduction section only.
The per-section grid is the deliverable, because it is the artifact you already committed to producing.

### R2. Then do the two additive passes your own comment asked for

Your single annotation in twenty days asked to extend the 😈/😇 bullets to `%wait` and `#fork`. Do exactly that, plus:

- **A limitations section.** You have asked for this three times since June 7 and never received it. Seed list, all
  from your notes and the July 2 audit: the Agents tab is the buggiest part of the TUI; XPrompt authoring fails
  silently in every common mistake mode (unknown `#name` passes through to the model, malformed YAML makes a definition
  vanish from `sase xprompt list`, name shadowing is silent); config YAML errors are swallowed at debug level with no
  `sase config validate`; alpha software, POSIX only; no custom crash screen — unhandled TUI exceptions surface as a
  raw Textual traceback; you inherit provider pricing and policy changes; and the naming is a genuine open problem you
  suspect points at a design problem. *A limitations section is the cheapest credibility purchase available, and it is
  the section agents will never write for you.*
- **"AI slop in my own codebase."** Your four categories — unnecessary backcompat, features you never use, duplicated
  logic, and **prompt debt** — with one real example of each from the SASE tree. This is the section people will quote,
  and per §7 it is the single most effective inoculation against the slop critique.
- **The dropped one-liners.** "Optimal experience, not optimal performance." The naming jokes. Vibe evals. The Gas Town
  comparison. Each is one or two sentences.

### R3. Do not restructure. Do not delete the ten drafts yet.

Keep your outline (§3). Keep the opening — lines 19–64 are already the strongest prose in the corpus and satisfy three
of your six active requirements.

On Report B's "delete the ten drafts first": the *psychological* argument is sound — while they sit there, "write the
post" feels like "edit ten posts," which is the task you keep cancelling. But the *urgency* is overstated: they are
`draft: true` and already excluded from the built site, so no reader can see them. Treat this as optional workspace
hygiene, and if you do it, do it **after** R1, not before — reorganizing the repo is another way to not write. If you
do delete, `git rm` is safe (history keeps every word) but fix `docs/blog/index.md` and cross-links in the same commit
or `strict: true` fails the build.

### R4. Demote the agents from writer to fact-checker

Both reports converge here and it is right.

| Give the agents                                                    | Keep for yourself      |
| ------------------------------------------------------------------ | ---------------------- |
| Verify every command, flag, and keymap against current source       | Every sentence         |
| Re-derive every statistic; flag any that don't reproduce            | Which stats to include |
| Find `file:line` citations for claims you make from memory          | The claims             |
| Check that no example in the post fails when run                    | The examples' point    |
| Flag terminology drift (companion→sidecar, provider names)          | The terminology        |
| **Render the three diagram briefs to PNG** (§4c)                    | Whether they're funny  |

Agents must not generate the opening scene, decide what you believe, or "make the voice more engaging." Hard
constraint from the July plan, still correct: never present `gemini` as a supported CLI — the five are `claude`,
`codex`, `agy`, `qwen`, `opencode`.

### R5. Use the ledger inside the post, not as the post

Report B's ledger post is a genuinely good idea aimed at the wrong slot. Do not let it restart your outline decision —
but do use the numbers, because they are your only uncontested ground (§5) and they make the tour concrete. Put the
table in the Overview section, with the caveats printed alongside. Fix the LOC figure first.

Then **write the ledger post second.** "Five months, 11,193 commits, and what 226 agent runs a day actually cost" is
the post that cannot be generated, and it belongs in your `Future Blog Posts` list beside Beads/SDD and Memory. It is a
better post 1 than any of the nine remaining drafts.

### R6. Voice checklist — run on any paragraph before it ships

Report B's checklist is the best structure-agnostic tool in either report. A paragraph failing two or more is agent
prose regardless of who typed it:

1. Could this sentence appear in the docs? If yes, cut or move it.
2. Is there a date, a number, or a name in it? Specificity is the cheapest humanity signal, and you have more of it
   available than almost anyone writing in this space.
3. Does it admit anything? A paragraph with no cost, failure, or doubt was written by something that never had a bad
   week.
4. Does it end on an aphorism? ("That boundary is the whole trick." / "The row already knows." — three in the current
   post.) Delete them; they are transitions pretending to be insights.
5. Is the humor load-bearing? A joke about something that happened works; a joke in a joke-shaped slot reads worse than
   no joke.
6. Does it use "honest," "boring," or "the trade-off is" as a credibility move? Both the July post
   (`structured-agentic-software-engineering.md:95`) and the `[00]` draft
   (`why-coding-agents-need-orchestration.md:131`) contain "The trade-off is honest/real" in the same structural slot —
   rhetorical humility as a template field. Show the trade-off; don't announce it.
7. Would you say this out loud?

### R7. Scope and framing

- **Target 2,000–2,500 words.** The current post is 2,762 and the additions in R2 will push it up, so plan to cut the
  Install section down to a link (Getting Started already does it better) and thin the XPrompts section, which is the
  longest at 686 words and the most reference-dense.
- **Write for one reader** (Report A, and it's the right call): an experienced solo developer or tech lead already
  running coding-agent CLIs in real git repos, who has tried more than one concurrent session and is starting to feel
  the coordination overhead. Not AI newcomers.
- **Lead with your choices, not commodity features** (§7). Independence, locality, provider neutrality, and durable
  git-native work state are defensible; parallel agents and worktrees are not.
- **Keep the title literal and unsuperlative** for the Show HN. The current title is fine.
- **End with "no weasels; just work."** It's yours, it's the last line of your own legacy outline, and it is a better
  closing than anything in the corpus.

### R8. The first ten minutes, if you're still stuck

Do not start with the post. Start with one section of the R1 grid — pick **ACE**, since you already know the punchline
("the agents tab is the buggiest part of the TUI"). Say three sentences out loud:

> The thing the Agents tab actually bought me was [ ___ ].
> What it still can't do that I want is [ ___ ].
> I learned that when [ ___ ] happened, and it cost me [ ___ ].

One section done is 1/6 of the missing layer and roughly 200 words of unfakeable text. Then stop. The goal of the first
session is not a finished post — it is to make the next session an editing task on *your* words, which is the one kind
of blog task your ledger says you finish.

---

## Appendix A: Re-Deriving the Numbers

```bash
git rev-list --count HEAD                                     # commits
git log --format='%ad' --date=format:'%Y-%m' | sort | uniq -c  # by month
git log --format='%B' | grep -c '^SASE_AGENT='                 # agent-attributed
tokei src  | grep -E '^ (Python|Total)'                        # use the Python row, not Total
tokei tests | grep -E '^ (Python|Total)'
wc -l sase/repos/beads/issues.jsonl                            # beads
find sase/repos/plans/2026* -name '*.md' | wc -l               # plans
find sase/repos/research -name '*.md' | wc -l                  # research

# Agent runs — NOTE: ~/.sase prunes; this is a ~23-day window, not a total
find ~/.sase/projects/*/artifacts -maxdepth 5 -type d \
  -regextype posix-extended -regex '.*/[0-9]{14}$' \
  | grep -oE '[0-9]{14}$' | cut -c1-8 | sort | uniq -c

git log --diff-filter=A --format='%ad %h %s' --date=short -- docs/blog/posts/   # corpus provenance
```

## Appendix B: Source Locations

| What                                          | Where                                                        |
| --------------------------------------------- | ------------------------------------------------------------ |
| **Your outline (the decisive artifact)**      | `bob:sase_blog_0.md` → `## Outline` / `^outline`              |
| Your requirements, quotes, screenshot notes   | `bob:sase_blog.md`                                            |
| "...but the truth is", "no weasels; just work"| `bob:sase_blog_0_legacy_notes.md`                             |
| Stalled proofread annotations (2 highlights)  | `bob:ref/docs/sase_blog_260708.md`                            |
| Plan that generated the May series            | `sase/repos/plans/202605/new_blog_posts.md`                   |
| Plan that generated the July post             | `sase/repos/plans/202607/first_blog_post.md`                  |
| June review of the `[00]` draft               | `sase/repos/research/202606/blog00_launch_post_review_consolidated.md` |
| Launch-readiness audit (`#cd` item now stale) | `sase/repos/research/202607/blog_launch_readiness_audit.md`   |
| Unrendered diagram briefs                     | `docs/images/blog/*.prompt.md` (3 files)                      |
| Existing demo media                           | `demos/out/` — 5 GIF/MP4 pairs, `just demos` regenerates      |
| ⚠️ Flagged screenshots                        | `~/tmp/screenshots/*.png` — **gone, `~/tmp` was cleaned**     |

## Sources

**External, from Report A** — [Tailscale: Remembering the LAN](https://tailscale.com/blog/remembering-the-lan) ·
[Charlie Marsh: Python tooling could be much, much faster](https://notes.crmarsh.com/python-tooling-could-be-much-much-faster) ·
[Astral: uv](https://astral.sh/blog/uv) · [Diátaxis: Explanation](https://diataxis.fr/explanation/) ·
[Google Technical Writing: Audience](https://developers.google.com/tech-writing/one/audience) ·
[Paul Graham: Write Simply](https://paulgraham.com/simply.html?viewfullsite=1) ·
[OpenAI: Introducing the Codex app](https://openai.com/index/introducing-the-codex-app/) ·
[Claude Code: Run agents in parallel](https://code.claude.com/docs/en/agents) ·
[Claude Code: Agent teams](https://code.claude.com/docs/en/agent-teams) ·
[GitHub: About third-party coding agents](https://docs.github.com/en/copilot/concepts/agents/about-third-party-coding-agents)

**External, from Report B** — [Addy Osmani: The Code Agent Orchestra](https://addyosmani.com/blog/code-agent-orchestra/) ·
[Augment Code: 9 Open-Source Agent Orchestrators (2026)](https://www.augmentcode.com/tools/open-source-agent-orchestrators) ·
[Nimbalyst: Best Multi-Agent Coding Tools (2026)](https://nimbalyst.com/blog/best-multi-agent-coding-tools-2026/) ·
[Tembo: AI Agent Orchestration Tools](https://www.tembo.io/blog/ai-agent-orchestration-tools) ·
[Superframeworks: The AI Slop Backlash Is Here](https://superframeworks.com/articles/ai-slop-backlash-judgment-moat) ·
[The Register: AI slop writing has taken over the internet](https://www.theregister.com/ai-and-ml/2026/07/09/ai-slop-writing-has-taken-over-the-internet/5269525) ·
[daily.dev: Hacker News Marketing for Developer Tools](https://business.daily.dev/resources/hacker-news-marketing-developer-tools-show-hn-launch-day-sustained-coverage/) ·
[markepear: How to launch a dev tool on Hacker News](https://www.markepear.dev/blog/dev-tool-hacker-news-launch)

**Internal, this pass** — `docs/blog/posts/*` · `docs/blog/index.md` · `docs/getting_started.md` · `docs/_redirects` ·
`mkdocs.yml` · `docs/overrides/main.html` · `docs/images/blog/` · `justfile` · `pyproject.toml` · git history through
`v0.12.0` · `bob:sase_blog{,_0,_0_legacy_notes}.md` via `bob query`
