# Splitting the SASE Blog Post into Obsidian Tasks: Walking Skeleton, Rolling Waves

> **Research query:** Bryan has writer's block on the sase blog post (`~/bob/sase_blog_contents.md`). He wants to
> turn the post into actionable Obsidian tasks, possibly including a spike or planning task that produces more tasks.
> Research how to split it, and end with a recommended strategy.

**Researcher:** cld · **Date:** 2026-10-23 · **Inputs checked:** the draft, `sase_blog.md` and its sub-projects, the
`done/sase_blog_done.md` archive, the October daily notes (Pomodoro ledger), `bob ref` annotations on six blog refs,
prior research (`first_post_authorship_gap`, `sase_launch_post_outline`, read via `sase artifact read`), the sase repo
(`README.md`, `docs/`, `demos/tapes/`), the `bob` CLI, and the external sources listed at the end.

## Bottom line

1. **The block is in how the tasks are cut, not in your writing.** The two writing tasks you have are *Write
   introduction!* and *Finish full v1 draft of blog post!*. Both are projects, not next actions. *Write introduction!*
   was planned into a BLOG or WRITE Pomodoro on five of the last eight days.
2. **Reading has been eating the writing time.** Since *Write introduction!* was created (10-16), your completed BLOG
   and WRITE Pomodoros total **520 minutes**. **450** went to reading refs, **45** were linked to the writing task, and
   25 went to other work. And today's 10-minute WRITE Pomodoro went to launching this research. 265 of the reading
   minutes went to two refs from `sase_pypi_releases` that were wired in as `dependsOn` prerequisites of the intro.
   Your dependency graph made reading a precondition of writing.
3. **The draft's order is depth-first. Make it breadth-first.** The current chain is intro → whole v1 draft. Writing
   advice and the research on blocked writers both point the other way. Write one rough sentence under *every* heading
   first (a walking skeleton), and write the introduction **last**, once you know what it introduces.
4. **The habit that reliably finishes is reading and annotating. Use it for revision.** Every proofread task has been
   cancelled. Meanwhile your annotated snapshots of blog material get 17 comments each. So make "revise" look like
   "read": snapshot the draft, annotate it like a ref, and turn the annotations into the next tasks.
5. **Recommended strategy:** **one spike (S0, 2 Pomodoros, hard stop)**, then **rolling waves of at most 5 tasks**.
   The spike approves a requirement-to-section map (prepared in [Appendix A](#appendix-a-requirement--section-map)),
   writes a one-sentence claim under every heading, and creates Wave 1. Each wave is: write → snapshot → annotate →
   **wave review**. The wave review is the recurring planning task that produces the next wave's tasks. Agents run in
   a parallel lane for facts, stats, footnotes, Gas Town mapping, and media. They never write prose.
6. **Size:** about 40 Pomodoros in total, including about 20 to a full v1 draft (every section zero-drafted). Your
   recent pace is about 3.2 BLOG Pomodoros a day. At that pace, v1 is about a week away and a publishable post about
   2.5 weeks, *if* BLOG time goes to writing.

---

## 1. Where the post actually stands (verified 2026-10-23)

| Item | State | Why it matters for the split |
| --- | --- | --- |
| `sase_blog_contents.md` | 274 words: about 130 words of intro prose in your voice, 4 footnote TODOs (`[1]` name and pronunciation, `[2]` Omnigent link, `[a]` links, `[b]` counts), and 10 headings (`1.1`–`1.7`, plus `1.3.1` and `1.3.2`), every one `TODO` | The skeleton exists, and it is *your* structure: the 2026-08-07 "Things that sase generalizes" list. No outline decision is pending. |
| `^write-introduction` | `[/]` since 10-16. Its `dependsOn` lists 3 blog refs plus 2 `sase_pypi_releases` refs, all now done. Its WORK LOG says *"Research on how to split up into tasks."* | This is the only open writing task, and it blocks `^v1-draft`. |
| `^v1-draft` | `[?]`, depends only on the intro, and blocks `sase_pre_blog#^prj` (13 blocked engineering tasks) | This is a whole-post task: the kind that rolls. |
| `^sase-blog` (release) | `[?]`, depends on `job_2026_apply_29#^prj` | The release is deliberately gated on job applications. Writing isn't, and shouldn't be. |
| `sase_blog.md` backlog | 43 Requirements bullets, 3 Screenshots, 6 Later Posts topics, plus 34 annotation comments (17 on the outline ref, 17 on the 10-19 notes snapshot) | Rich material that no section claims yet. This is why every heading still feels like a blank page. |
| `bob ready sase_blog` | 1 of 5 ready, room for 4 | The per-note Ready cap of 5 is a ready-made WIP limit. The task plan should respect it. |
| Media | Five VHS tapes exist (`multi_model_fanout`, `agents_observability`, `prompt_input`, `prompt_history_stash`, `prs_pipeline`). The four June screenshots still exist in `~/tmp/screenshots/` but predate renames. `img/20260824_141701.png` (the four-plans example) and `img/20260802_*` (stashes) exist. | Sections 1.3, 1.3.2, 1.4, and 1.5 already have proof media. Sections 1.1, 1.2, 1.6, and 1.7 don't. |

### What the ledger says about which tasks finish

Most of this repeats the July authorship-gap research, re-checked against `done/sase_blog_done.md`, which has newer
rows.

- **Finished quickly:** agent-produced text ("Use Fable to generate first draft", 1 day), mechanical restructures
  (`^no-more-0-prj`, `^create-prj-0`), the WisprFlow brain-dump (3 days), and reading or annotating refs. The
  outline ref and the 10-19 notes snapshot drew 17 comments each.
- **Rolled or cancelled:** *Proofread blog post!* (cancelled twice), *Gather a list of references* (rolled 8 times,
  then cancelled), *Describe demo video and infographic for each main section* (rolled 6 times, then cancelled),
  *Flesh out "high value…" for each section* (cancelled), *Read research on how to get past writers block*
  (cancelled), and *Launch agent to create ~/bob/zk/ notes* (cancelled).

The pattern is not "Bryan can't write." Tasks with **a concrete artifact and a single sitting** finish. Tasks that
are **open-ended judgment over a whole document** ("proofread", "flesh out each section", "finish v1") roll. The split
has to turn the second kind into the first.

### Pomodoro tally method (10-16 → 10-23)

I parsed every completed (`- [x]`) BLOG or WRITE Pomodoro in `2026/202610{16..23}.md` and classified it by its first
linked task. Writing (`^write-introduction`) got 45 minutes: 35 on 10-16 and 10 today. Reading (`ref-*` or
`^read-blog-notes`) got 450: outline ref 100, Gas Town manual 50, blog notes 35, *Redesigning source control* 185,
*How the Claude Code team does code review* 80. Other work got 25 ("Testing task relations!"). Pomodoros that link
several tasks were counted once, under the first link.

---

## 2. Diagnosis: three task-design defects

### 2.1 The tasks are projects, not next actions

David Allen's test for a next action is *"the next physical, visible activity"*. His point is that things stall
because *"the doing of them has not been defined."* *Write introduction!* and *Finish full v1 draft* both fail that
test. Each hides dozens of decisions: what the promise sentence says, whether to mention leaving Google, which
provider list to use, and so on.

There is lab evidence that this matters. McCrea, Liberman, Trope & Sherman (2008, *Psychological Science*) found that
people were **less likely to procrastinate when the task was framed concretely**, and that the effect held regardless
of the task's attractiveness, importance, or difficulty. A task line that names the section, the verb, and the size of
the output is the cheapest concreteness you can buy.

### 2.2 Reading gates writing

`dependsOn` is finish-to-start: nothing downstream becomes ready until every upstream task is done. That suits
engineering prerequisites. It is harmful when the upstream tasks are reading and the downstream task is drafting.
Each new ref you add pushes the writing back, and reading always *feels* like progress on the post. Mike Rose's
study of blocked writers (1980) found that blockers were not less emotional or less able. They were following
**rigid rules and inflexible plans** that got in the way of composing. "Read everything relevant before writing the
intro" is exactly such a rule.

### 2.3 The order is depth-first

The current graph is: intro (must be finished) → everything else. But the introduction is the one part you can't
write well yet, because it is a promise about sections that don't exist. The advice to "write the introduction last"
is standard for this reason (Orzel; Principia; Davidson). The fix is the skeleton draft: rough bones across the whole
piece first, then flesh (novelists' "skeleton draft"; the Pyramid Principle's "prose follows the scaffold").

### 2.4 An asset, not a defect: annotation is your strongest habit

You reliably read, highlight, and comment on PDFs of agent reports and notes snapshots. You do not reliably
"proofread" a draft in place. Flower & Hayes's model separates *translating* (drafting) from *reviewing*. Your
ledger suggests you should separate them in **medium** too. Draft in Obsidian by dictation. Review as a snapshot,
the way you review refs, or as audio through the existing *transcribe… and listen to it* task.

---

## 3. What the research says, as task-design rules

| Principle | Source | What it means for the tasks |
| --- | --- | --- |
| Brief, regular sessions beat binges | Boice (summarized by Prolifiko and Writing Commons; check the primary source before quoting numbers) | One-Pomodoro writing tasks, ideally the first Pomodoro of the day. No "writing day". |
| Concrete construal reduces procrastination | McCrea et al. 2008 | Every task names a section, a verb, and an output size. |
| Next physical, visible action | Allen, *GTD* | Use verbs like *dictate*, *write 3 sentences*, *list*, *paste*. Avoid *work on*, *figure out*, *finish*. |
| Implementation intentions ("when X, I do Y") | Gollwitzer & Sheeran 2006 meta-analysis, 94 tests, d ≈ 0.65 | Tie the next writing task to a cue, e.g. "after morning GTD, the first Pomodoro is WRITE." |
| Rigid rules and plans cause blocking | Rose 1980 | Remove "intro first" and "read first" as hard dependencies. |
| Draft and review are different processes | Flower & Hayes 1981 | Use separate tasks, never in the same Pomodoro. |
| Small frame, bad first draft | Lamott, *Bird by Bird* | Zero-draft tasks have a word floor and a no-editing rule. |
| Poke small holes in big tasks | Lakein's Swiss-cheese method | Keep 5-minute tasks (footnotes, counts) for low-energy slots. |
| End each session knowing what's next | The "Hemingway Bridge" (Forte, *Building a Second Brain*) | Each writing Pomodoro ends with a `NEXT:` line in the task's WORK LOG. |
| Creative log per writing project | Bob Doto, *A System for Writing* (in your `system_for_writing` notes, ^9b) | The WORK LOG on the active blog task *is* your creative log. |
| Spike = time-boxed experiment whose output is knowledge | Jeffries (XP), Cohn | S0 is time-boxed, its output is tasks plus decisions, and don't overuse it. |
| Rolling-wave planning | PMBOK (progressive elaboration) | Detail only the next wave. Later waves stay one line each until their wave review. |
| LLM-written essays reduce ownership and recall | MIT Media Lab, *Your Brain on ChatGPT* (2025 preprint, preliminary) | Agents fact-check and render. They never draft your sentences. |

---

## 4. Options considered

| Option | Unit of work | Fits the Ready cap of 5? | Keeps your voice? | Rot risk | Verdict |
| --- | --- | --- | --- | --- | --- |
| **A. One task per section** ("Write §1.1") | Section, 2–4 Pomodoros each, with judgment hidden inside | No: 10+ ready at once | Yes | High: these are the "flesh out each section" tasks that already rolled | Reject as the only unit |
| **B. One task per phase** (draft → revise → edit → publish) | Whole document | Yes | Yes | Very high: this is `^v1-draft` and *Proofread blog post!* | Reject |
| **C. One task per Requirements bullet** | 43+ micro-tasks | No | Mixed | High, and it loses the narrative | Reject as tasks. Keep as a **map** (Appendix A) |
| **D. Walking skeleton + rolling waves + spike** (recommended) | One Pomodoro, one section, one visible output; at most 5 ready per wave | Yes, by design | Yes: dictated zero drafts | Low: only the next wave exists in detail | **Adopt** |
| **E. Agent drafts, Bryan edits** | Whole sections | Yes | No: this is the replace-don't-own cycle (`[00]` → July post → `why_sase` → now) | n/a | Reject: it contradicts `^prj` ("in my own voice") |
| **F. Cut scope or split into a series** | Moves 1–2 abstractions to Later Posts | n/a | Yes | n/a | Keep as a **pressure valve** at the Wave 2 review if the word budget breaks |

---

## 5. The recommended strategy in detail

### 5.1 Six rules for every blog task

1. **One Pomodoro, one verb, one visible output, one heading link.** Example: *"Zero-draft §1.5: dictate ≥150 words
   under [[sase_blog_contents#1.5 …]]"*. Never "Write §1.5".
2. **Writing never depends on reading.** A ref may block only the *revision* of the section it feeds, and only if
   you name that section in the ref task.
3. **Drafting and revising are separate tasks.** Zero drafts allow no deletions and no lookups. Mark gaps with `??`
   and keep going.
4. **There are two lanes.** The WRITE lane is yours: dictation, claims, jokes, admissions. The AGENT lane covers
   stats, footnote facts, Gas Town mapping, docs checks, media, and polls. Agents never produce post prose.
5. **At most 5 ready tasks.** Later waves are not created yet (rolling wave). `bob ready sase_blog` is the check.
6. **End every WRITE Pomodoro with a bridge.** Add a WORK LOG line on the task: `NEXT: <first words of the next
   sentence or the next question>`.

### 5.2 The spike: S0, "Cut the post into waves" (2 Pomodoros, hard stop)

**Purpose:** reduce uncertainty, then emit tasks. It produces decisions and tasks, not prose beyond one sentence per
heading.

**Inputs:** this report's [Appendix A](#appendix-a-requirement--section-map) (requirement → section map) and
[Appendix B](#appendix-b-per-section-sources-and-proof-media) (per-section facts and media), the draft, and nothing
else. No new reading.

**Pomodoro 1: decide (yours).**
1. Approve or strike Appendix A, one row at a time. Each row ends as a section number, `LATER`, or `CUT`.
2. Name the H2s after `1. The Abstractions`. The October 7 outline's candidates are *What it cost* (slop, AI broccoli,
   limitations) and *What's next / I need your help* (polls, out of tokens, series map). Decide whether "How I got
   here" (ladder, leaving Google, timeline) lives in the intro or gets its own H2.
3. Resolve the two overlaps: **hoods** appear under both 1.3.2 and 1.6, and **families** is the pre-rename term for
   agent sessions. Also decide whether **Xprompts** stays as a joke heading or becomes Macros.
4. Set a word budget per section. A baseline of 250 words × 10 abstraction headings + 400 intro + 400 cost + 250
   next ≈ 3,550 words. That is over the October 7 outline's 3,000 cap, so pick where to trim now, or note it for the
   Wave 2 review.

**Pomodoro 2: skeleton and tasks.**
1. Write **one claim sentence under every heading**, breadth-first, ugly allowed. This is the walking skeleton, and
   afterward no heading is blank.
2. Create Wave 1 from the [paste-ready block](#55-paste-ready-tasks-wave-0-and-wave-1) and attach each section's card
   (Appendix A/B rows) as sub-bullets.
3. Rewire the graph. Complete `^write-introduction` as **"Intro v0"**: the two paragraphs *are* an intro v0. Create
   "Intro v1 (last)" in Wave 5. Re-point `^v1-draft` to the Wave 3 review.
4. Add the bridge line.

**Exit criteria (all must hold):** every heading has a claim sentence · every Appendix A row is assigned · the H2
list is fixed · `bob ready sase_blog` shows ≤5 · `^v1-draft` no longer depends on the intro.

**Anti-goals:** no new research swarm about the blog's *shape* before v1. This one should be the last. No outline
rewrite. No reading.

### 5.3 The wave loop: the planning task that keeps producing tasks

```text
WRITE (3–4 zero-draft or revise tasks, 1 Pomodoro each, WRITE theme)
  → SNAPSHOT (agent or automation: draft → PDF ref for Highlights, and/or MP3 via the existing listen task)
  → ANNOTATE (1 READ Pomodoro: highlight and comment, as with any ref)
  → WAVE REVIEW (≤1 Pomodoro: turn annotations into the next ≤5 tasks, cancel what no longer matters, write the bridge)
```

The **wave review** is the task you asked for: a planning task that produces more tasks. It depends on the wave's
writing tasks, so it surfaces only when the wave is done, and it is always the last task created in its wave.

| Wave | Contents (suggested; S0 can re-order) | Pomodoros |
| --- | --- | --- |
| **0** | S0 spike (2) · launch the agent fact pack (A1–A4 below) and skim its output (≈2) | ~4 |
| **1** | Zero drafts where your notes already hold the punchline (Swiss-cheese the easy holes first): **§1.5** (😈/😇 `%wait`/`#fork` bullets, vibe evals, PIW quote), **§1.3.2** ("Why a TUI?", the Agents tab is the buggiest part), **§1.1** (plan mode as a special case of gates, the four-plans example), **§1.3** (outage retries, rival labs' models working one task) · snapshot + annotate · W1 review | ~6 |
| **2** | Zero drafts for **§1.3.1** (memory "every wrong way", skills as procedural memory, *why not hooks*), **§1.2** (beads → sidecars, the Gas Town difference), **§1.6** (artifacts, `sase artifact read` auditability), **§1.4** (VCS and workspaces) · snapshot + annotate · W2 review, which also applies the pressure valve if the budget breaks | ~6 |
| **3** | Zero drafts for **§1.7** (routines and jobs, the "types of tokens"), **What it cost** (slop categories with one real example each, AI broccoli, limitations), and **What's next / I need your help** · W3 review → **completes `^v1-draft`** | ~6 |
| **4** | Revise each section from annotations plus the agent fact sheet, about 2 sections per Pomodoro. Run the July voice checklist (R6 in `first_post_authorship_gap`). Freeze terminology. Salvage pass on the live July post (the `tmux_ai_window` scene). | ~8–10 |
| **5** | **Intro v1 (last):** the promise sentence, the "Well, I've tried" bridge, leaving Google, the full provider list. Then the closing line, title and dek, and footnotes `[1]` `[2]`. | ~3–4 |
| **6** | Publish prep: re-derive `[b]` on publish day, `[a]` link pass, embed media, listen pass, mkdocs build, then release when `job_2026_apply_29` clears | ~3–4 |

Total ≈ 36–40 Pomodoros. The v1 draft (end of Wave 3) is ≈ 22.

### 5.4 The agent lane (start today, in parallel with S0)

These are the task shapes your ledger says finish: a concrete artifact, and reviewing it costs at most one Pomodoro.
One "launch the blog fact-pack agent" task can cover A1–A4.

| ID | Output | Notes from this research |
| --- | --- | --- |
| **A1. Stats `[b]`** | Commit and LOC table with definitions, across sase, sase-core, and the plugins | The draft's "~17K commits, ~2.9M lines of Python and Rust" needs definitions. Today `sase` alone has **16,356 commits** (since 2026-02-14), and `src`+`tests` hold **2,909,932 Python lines (2,471,204 code lines)**. So "2.9M" is sase's *Python* line count alone, with no Rust. Re-derive on publish day. |
| **A2. Footnote facts `[1]` `[2]`** | Source list. You write the joke. | The README says sase is pronounced "sassy". Gartner's 2019 *Secure Access Service Edge* acronym, the name conflict, is *also* pronounced "sassy". Use Hassan et al. (arXiv:2509.06216) for the acronym's origin. For `[2]`, prior research `omnigent_meta_harness_lessons_for_sase` already has the Omnigent material. |
| **A3. Gas Town term map** | Table: each §1.x abstraction → its Gas Town or Gas City analog, with a link | This absorbs the existing *"link to the analogous crazy term used by GasTown"* task. It also prevents a clash: "NOT hooks" in §1.3.1 versus Gas Town's own use of *hooks*. |
| **A4. Per-section fact sheet** | For each section: the current command and term names and the docs page to check against ([Appendix B](#appendix-b-per-section-sources-and-proof-media)) | Includes the **"why not hooks?"** rationale hunt. You asked "Why is that again?" on the outline, and no docs page or design-decision entry records it. |
| **A5. Media** | Re-render the 5 existing tapes with current naming. Propose tapes for §1.1, §1.2, §1.6, and §1.7, which have no proof media. Render the diagram briefs. | Your annotation says to prefer GIFs over images. The June screenshots can stand in until then. |
| **A6. Snapshot each wave** | A draft PDF ref plus optional MP3 | Reuses the `SASE Blog · 2026-10-19` snapshot pattern and the existing *transcribe… and listen* task. |
| **A7. `type:poll` issues** | Draft GitHub issues. You approve the wording. | For *What's next / I need your help*. |

### 5.5 Paste-ready tasks (Wave 0 and Wave 1)

These use the vault's existing syntax. Ready count after pasting: S0, A-lane, plus the existing paper-appendix ref =
**3 of 5**. The Wave 1 tasks surface when S0 completes. `bob task reconcile` maintains `[?]` from `dependsOn`.

```markdown
- [ ] #task Spike S0: approve the requirement→section map, name the H2s, write one claim sentence under every heading, create Wave 1 (2 🍅, hard stop) [created::2026-10-23] [id:: sase_blog__s0-spike] ^s0-spike
	- Input: research:202610/sase_blog_post_task_split__cld.md (Appendices A and B). No other reading.
	- EXIT: every heading has a claim · every map row assigned · `bob ready sase_blog` ≤5 · ^v1-draft re-pointed
- [ ] #task Launch blog fact-pack agent (stats [b], footnote facts [1][2], Gas Town term map, per-section fact sheet incl. "why not hooks") and skim its output [created::2026-10-23] [id:: sase_blog__agent-fact-pack] ^agent-fact-pack
- [?] #task Zero-draft §1.5 Xprompts / control flow: dictate ≥150 words under [[sase_blog_contents#1.5 Xprompts / Agent control flow (forks/waits/queues)|§1.5]], no editing, end with NEXT line [created::2026-10-23] [id:: sase_blog__zd-1-5] [dependsOn:: sase_blog__s0-spike] ^zd-1-5
	- CARD: 😈/😇 bullets for %wait and #fork · vibe evals · PIW goal #1/#2 quote · stashes · loop vs graph engineering
- [?] #task Zero-draft §1.3.2 Agent presentation: dictate ≥150 words ("Why a TUI?" first), no editing, end with NEXT line [created::2026-10-23] [id:: sase_blog__zd-1-3-2] [dependsOn:: sase_blog__s0-spike] ^zd-1-3-2
	- CARD: Why a TUI? · Agents tab is the buggiest part · "sub-agent" doesn't cut it · agents_observability GIF
- [?] #task Zero-draft §1.1 Gates → Plans → Epics: dictate ≥150 words, no editing, end with NEXT line [created::2026-10-23] [id:: sase_blog__zd-1-1] [dependsOn:: sase_blog__s0-spike] ^zd-1-1
	- CARD: "Plan mode is the canonical example of some deeper primitive" → gates · four-plans `sase artifact read` example · tales/epics/legends/myths
- [?] #task Zero-draft §1.3 Agent CLIs: dictate ≥150 words, no editing, end with NEXT line [created::2026-10-23] [id:: sase_blog__zd-1-3] [dependsOn:: sase_blog__s0-spike] ^zd-1-3
	- CARD: retries through the Claude outage · competing labs' models swarming one task · usage-window indicators · optimal experience, not optimal performance
- [?] #task Wave 1 review: snapshot + annotate the draft (1 🍅 READ), then create ≤5 Wave 2 tasks and write the bridge [created::2026-10-23] [id:: sase_blog__w1-review] [dependsOn:: sase_blog__zd-1-5, sase_blog__zd-1-3-2, sase_blog__zd-1-1, sase_blog__zd-1-3] ^w1-review
```

**Dictation prompts for every zero draft.** These are prompts, not content. They fold your old "high value /
untapped opportunity / lesson learned" grid into the 😈/😇 shape you asked for.

1. 😈 What special case annoyed me before SASE existed for this? What did I actually do instead?
2. 😇 What did SASE generalize it into? Name one specific day it paid off.
3. 💸 What did it cost, what's still broken, or what would I do differently?

### 5.6 What to do with the existing tasks

| Task | Recommendation |
| --- | --- |
| `[/] Write introduction!` | Complete it as **Intro v0**. The two paragraphs are a real v0, and closing a task that's been open a week matters. Intro v1 moves to Wave 5. |
| `[?] Finish full v1 draft` | Keep it, and re-point `dependsOn` to `sase_blog__w3-review` once Wave 3 exists. Define it as "every heading has a zero draft." |
| *Link to the analogous GasTown term* | Fold it into A3. |
| *Review all post-blog tasks for Future Work* | Make it an input to the Wave 3 *What's next* zero draft. |
| *Transcribe into a podcast episode and listen* | Make it the A6 snapshot mechanism and run it every wave, not once at the end. |
| `ref` July live post (`structured_agentic_software_engineering`) | Remove its blocker and attach it to the Wave 4 salvage pass (the `tmux_ai_window` scene and 😈/😇 opening). It is not a writing input before then. |
| `ref` *Agentic Software Engineering* paper ("Read appendix!") | Attach it to footnote `[1]` and the Wave 5 work. It must not block any WRITE task. |
| `sase_pre_blog` (13 engineering tasks) | No change: it already waits on the draft, not the reverse. Write about what ships today. Anything unfinished (pi, hermes) becomes a *What's next* mention, and A1 re-derives the provider count on publish day. |

---

## 6. Risks and how the plan handles them

- **A fifth replace-don't-own cycle.** Zero drafts are dictated, agents never produce post prose, and the skeleton
  sentences come from you in S0.
- **Reading creep.** Reading lives in the READ theme and never blocks WRITE. Each wave gets exactly one annotate
  Pomodoro, and its output must become tasks the same day in the wave review.
- **Task rot.** Only the next wave exists in detail. The Ready cap of 5 is enforced by `bob ready`.
- **Scope creep.** Ten abstraction headings plus new H2s put the post over budget. The Wave 2 review is the
  designated moment to move one or two abstractions (§1.4 and §1.7 are the natural candidates) to Later Posts as
  one-paragraph pointers.
- **Terminology churn** (families → sessions, xprompts → macros, possible product rename). Freeze terminology at
  Wave 4. Headings name ideas.
- **The release gate.** The job-application gate on `^sase-blog` is fine. It gates *publishing*, not *writing*, so
  don't add more gates to the writing path.

---

## 7. Recommended strategy

**Use the walking-skeleton, rolling-wave plan with a single 2-Pomodoro spike up front.**

1. **Today (5 minutes):** complete *Write introduction!* as Intro v0, paste the [Wave 0–1 block](#55-paste-ready-tasks-wave-0-and-wave-1),
   and launch the fact-pack agent (A1–A4).
2. **Next WRITE Pomodoro: S0, part 1.** Approve the requirement map, fix the H2 list, resolve the hoods, families,
   and xprompts overlaps, and set word budgets.
3. **Following WRITE Pomodoro: S0, part 2.** Write one claim sentence under all ten-plus headings, wire Wave 1, and
   re-point `^v1-draft`. Stop when the time-box ends, even if it isn't perfect.
4. **Make the first Pomodoro of each day WRITE** (implementation intention) and spend it on the next zero-draft task.
   Dictate, add no edits, and end with a `NEXT:` line.
5. **After each wave:** snapshot, then one READ Pomodoro of annotation, then the wave review, which creates ≤5 tasks
   for the next wave.
6. **After Wave 3:** `^v1-draft` completes and every heading has your words under it. Only then revise (Wave 4),
   write the intro last (Wave 5), and do publish chores (Wave 6).
7. **Keep agents in the AGENT lane only:** facts, stats, footnote facts, Gas Town map, media, polls, snapshots.

If you do only one thing, do the **skeleton sentence under every heading**. It turns ten blank TODOs into ten things
to expand, and it is the input the introduction has been missing.

---

## Appendix A: Requirement → section map

This is the mechanical part of S0's work: one row per `sase_blog.md` Requirements, Screenshots, Outline, or
annotation item. S0 approves, moves, or strikes each row. "Bryan-only" marks material no agent can supply.

| Requirement / note | Proposed home | Bryan-only? |
| --- | --- | --- |
| Pride/identity opening; promise sentence + Getting Started link (outline annotation); "Well, I've tried" bridge (intro annotation); leaving Google (outline annotation) | Intro (Wave 5) | ✔ |
| List every supported provider (intro annotation) | Intro, with A1 checking the count | — |
| `tmux_ai_window` in intro; Boris → `tmux_ai_window` → auto-approve plans → wait/fork ladder; 12-month timeline infographic; AI Daily Brief | Intro, or a "How I got here" H2 (S0 decides) | ✔ ladder · agent for the infographic |
| Naming jokes (sase, xprompts); "I'm bad at naming things…" (annotation: sase started at a lower level of abstraction than Gas Town); SASE/Secure Access Service Edge | Footnote `[1]` and §1.5 | ✔ jokes · A2 facts |
| Omnigent as the meta-harness example | Footnote `[2]` | A2 |
| "Plan mode is the canonical example of some deeper primitive… Interrupts?"; questions/retries/tales screenshot; tales/epics/legends/myths and "SASE's purpose: build the next SASE (first myth)"; "a goal should outlive an epic"; legends instead of milestones | §1.1 (goals/legends may go to *What's next*) | ✔ |
| Gas Town differences (beads used less, rigs, no mayor) | §1.2 plus A3 links across sections | ✔ opinion · A3 facts |
| `reads`/`snips` as future sidecar repos | §1.2 or *What's next* | — |
| Competing labs' models swarming one task (QUOTE); retries through the Claude outage (screenshot `20260616_140429`); usage-window indicators (outline annotation); "optimal experience, not optimal performance" | §1.3 | ✔ |
| Skills as procedural memory; "implemented project memory every wrong way"; why NOT hooks; hub-note quote; FUTURE memory + docs (Diátaxis) | §1.3.1 (hub-note quote and memory+docs may go to LATER) | ✔ · A4 hooks rationale |
| "Why a TUI?"; Agents tab is the buggiest part; "sub-agent" doesn't cut it; tribes, clans, hoods; TUI screenshots/GIFs | §1.3.2 | ✔ |
| PRs/Patches pipeline GIF; ChangeSpec hooks, mentors, reviewer comments | §1.4 (depth goes to LATER) | — |
| `%wait`/`#fork` 😈/😇 bullets; alternations → "vibe evals" (screenshot `20260619_214831`); `%wait` screenshot `20260616_115015`; stashes (`img/20260802_*`); PIW goal #1/#2 quote; loop vs graph engineering; Vim-mode joke | §1.5 (Vim joke possibly in the closing) | ✔ |
| Artifact sidecar repos; `sase artifact read` auditability and the four-plans example (`img/20260824_141701.png`); future `sase artifact write/validate` | §1.6 (the example could instead anchor §1.1) | ✔ |
| "Different types of tokens" (annotation: cleanup routines, plan/code, size model aliases); `sase-telegram`; scheduler | §1.7 (size aliases may fit §1.3) | ✔ |
| AI slop definition and 4 categories (backcompat, unused features, duplication, prompt debt); AI broccoli (Keep note); limitations list; "agents tab buggiest" forward pointer; closet/hacker diagram | **What it cost** (new H2) | ✔ (an agent may *propose* candidate slop examples from git history) |
| "I need your help. I'm out of tokens."; `type:poll` issues; Later Posts series map; FUTURE goals scale; finalizer ideas; post-blog tasks review | **What's next / I need your help** (new H2) | ✔ · A7 issues |
| "No weasels; just work" (be kind to Steve Yegge) | Closing line | ✔ |
| Devil/halo bullets; angel/devil stick figures; 3 funny diagrams; citations | Cross-cutting style and media (A5) | ✔ taste · agent rendering |
| Email the `agent_swe` authors; HN timing; security audit | Launch checklist, not content | — |

## Appendix B: Per-section sources and proof media

| Section | Docs to fact-check against | Existing proof media | Gap |
| --- | --- | --- | --- |
| 1.1 Gates → Plans → Epics | `docs/sdd.md`, `docs/notifications.md`, `docs/concepts/automation.md`, `docs/guides/plan-multi-agent-change.md` | Screenshot `20260624_074728`; `img/20260824_141701.png` | No gate/plan GIF yet |
| 1.2 Beads → Sidecar repos | `docs/beads.md`, `docs/concepts/work-units.md`, `docs/agents_sidecar.md` | — | Needs media |
| 1.3 Agent CLIs | `docs/concepts/providers.md`, `docs/llms.md`, `README.md` (7 providers) | `sase_ace_multi_model_fanout` tape; screenshot `20260616_140429` | — |
| 1.3.1 Skills, memory, provider interface | `docs/concepts/memory.md`, `docs/instruction_bundles.md` | — | Hooks rationale is undocumented (A4) |
| 1.3.2 Agent presentation | `docs/agent_sessions.md`, `docs/ace.md`, `docs/concepts/agents.md` | `sase_ace_agents_observability` tape | Re-render with current names |
| 1.4 VCS and workspace ops | `docs/vcs.md`, `docs/workspace.md`, `docs/commit_workflows.md`, `docs/concepts/landing.md` | `sase_ace_prs_pipeline` tape | — |
| 1.5 Xprompts / control flow | `docs/macros.md`, `docs/concepts/prompts.md` | `sase_ace_prompt_input` and `sase_ace_prompt_history_stash` tapes; screenshots `20260616_115015`, `20260619_214831`; `img/20260802_*` | — |
| 1.6 Project management | `docs/agents_sidecar.md`, `docs/agent_sessions.md` (hoods) | `img/20260824_141701.png` (if not used in 1.1) | Needs media |
| 1.7 Routines and Jobs | `docs/axe.md`, `docs/monitors.md`, `docs/tool.md`, `docs/mobile_gateway.md` | — | Needs media |

---

## Sources

**Vault (read-only):** `sase_blog_contents.md`, `sase_blog.md`, `sase_pre_blog.md`, `sase_post_blog.md`,
`done/sase_blog_done.md`, `why_sase.md`, `sase_blog_0_legacy_notes.md`, `sase_blog_blockers.md`,
`system_for_writing.md`, `bob_gtd.md`, `gtd.md`, `job_2026.md`, `job_2026_apply_29.md`, and `2026/20261008–20261023.md`
(Pomodoro ledger). `bob ref show` annotations on `ref/notes/sase_blog_261019`, `ref/chat/sase_launch_post_outline`,
`ref/chat/sase_launch_post_introduction`, `ref/chat/blog00_launch_post_review_consolidated`, `ref/docs/sase_blog_260708`,
and `ref/blogs/structured_agentic_software_engineering`. Also `bob ready sase_blog`.

**Prior research (via `sase artifact read`):** `research:202607/first_post_authorship_gap/first_post_authorship_gap.md`
and `research:202610/sase_launch_post_outline/sase_launch_post_outline.md`.

**Repo:** `README.md` (providers, "sassy"), `docs/` page titles, `demos/tapes/`, `git rev-list --count HEAD`, and
`tokei src tests`.

**External:**

- [Prolifiko: Boice on binge vs. brief daily writing](https://prolifiko.com/?p=14245) ·
  [Writing Commons: The Writing Log & Daily Writing](https://writingcommons.org/article/the-writing-log/)
- [McCrea, Liberman, Trope & Sherman (2008), Construal Level and Procrastination](https://www.psychologicalscience.org/journals/psychological-science/j.1467-9280.2008.02240.x/) ·
  [KOPS record](https://kops.uni-konstanz.de/entities/publication/42507a45-e0af-45cf-a38e-51b39cb0e5f4)
- [Gollwitzer & Sheeran (2006), Implementation intentions meta-analysis (KOPS)](https://kops.uni-konstanz.de/entities/publication/2e749bfb-8533-437c-8203-7e788c910c5f)
- [Mike Rose, Writer's Block: The Cognitive Dimension](https://www.mikerosebooks.com/writer-s-block--the-cognitive-dimension.html)
- [Writing Commons: Problem-solving strategies for writers (Flower & Hayes)](https://writingcommons.org/section/writing-process/problem-solving-strategies/)
- [43 Folders on Allen's "next physical, visible activity"](https://www.43folders.com/node/47127/313823) ·
  [FacileThings: What is the next action](https://facilethings.com/blog/en/what-is-the-next-action)
- [Bird by Bird summary (one-inch picture frame, shitty first drafts)](https://www.supersummary.com/bird-by-bird/summary/)
- [Atlassian: Swiss cheese and salami methods](https://www.atlassian.com/blog/productivity/swiss-cheese-salami-methods)
- [Summary of Forte's Hemingway Bridge / archipelago of ideas](https://launchvic.notion.site/)
- [Mountain Goat Software: Agile spikes deliver knowledge](https://mountaingoatsoftware.com/blog/spikes) ·
  [Hackernoon: 6 common mistakes when using spikes](https://hackernoon.com/6-common-mistakes-when-using-spikes-9a4186c3cc29)
- [Rolling wave planning (progressive elaboration)](https://thedigitalprojectmanager.com/project-management/rolling-wave-planning/)
- [Chad Orzel: Always write the introduction last](https://chadorzel.com/principles/?p=6118) ·
  [Principia: Write the introduction last](https://content.principia.edu/teaching-excellence/write-the-introduction-last/) ·
  [Davidson: Planning and drafting](https://davidsonwriter.davidson.edu/planning-drafting/)
- [Skeleton draft vs. bulging draft](https://www.goodreads.com/author_blog_posts/21136279-the-first-draft-skeleton-draft-or-bulging-draft)
- [TechLearning: Your Brain on ChatGPT (MIT Media Lab, 2025 preprint)](https://www.techlearning.com/news/your-brain-on-chatgpt-everything-educators-need-to-know-about-mits-ai-study)
- [Obsidian Tasks: task dependencies (id / dependsOn)](https://publish.obsidian.md/tasks/Getting+Started/Task+Dependencies) ·
  [Longform plugin](https://community.obsidian.md/plugins/longform) (considered, not recommended: your Bob task
  system already covers what a scene-compiler would add)
- [Fierce Network: What is SASE? (Gartner, 2019)](https://www.fierce-network.com/tech/what-sase) ·
  [Palo Alto Networks on Gartner's SASE report](https://www.paloaltonetworks.com/blog/2019/11/cloud-next-generation-network-security)

**Caveats.** The Boice and Hemingway-Bridge claims come from secondary summaries. The MIT study is a preliminary,
non-peer-reviewed preprint. The Pomodoro tally classifies each Pomodoro by its first linked task. Line counts are
Python only, from the `sase` repo only.
