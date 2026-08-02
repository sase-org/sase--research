---
create_time: 2026-08-02
updated_time: 2026-08-02
status: research
---

# A Zettelkasten-Inspired Method for Finishing SASE's First Blog Post

**Research question:** Bryan wants to write SASE's first blog post using a methodology inspired by Zettelkasten,
probably in Obsidian. What does Zettelkasten actually provide, how much of it transfers to this specific writing task,
what are the alternatives, and what is the smallest method that will actually produce the post?

**Relationship to prior work:** This report builds directly on
[`202607/first_post_authorship_gap/first_post_authorship_gap.md`](../202607/first_post_authorship_gap/first_post_authorship_gap.md)
(2026-07-28), which diagnosed the block as an ownership gap and prescribed R1: dictate three answers per outline section.
This report does **not** relitigate that diagnosis — it accepts it and asks a narrower question: *why did R1 not happen,
and does Zettelkasten fix that specific failure?* The answer is yes, but only one mechanism of it does, and adopting the
rest would be actively harmful.

---

## Bottom Line

1. **The Zettelkasten instinct is correct, and there is new evidence for it from the last four days.** On 2026-08-01 you
   created `bob:why_sase.md` with the description *"The contents of the first sase.sh blog post."* It is your own
   writing, not agent output — a genuine break from the replace-don't-own cycle. It is also 99 words long and stops
   mid-sentence on the word *"Maybe "*. Then it degrades: prose → bullets → single words (`claude`, `codex`). That decay
   curve is the whole problem in one file.

2. **The failure is note granularity, not willpower.** A note whose stated job is *"will contain full blog post"* is a
   blank page with a filename. Every sentence written into it is a commitment to a 2,500-word artifact, which is exactly
   the "352 decisions with no criterion" problem §2 of the prior report identified. The R1 prescription was right; it
   was written into the wrong container.

3. **Exactly one Zettelkasten primitive solves this: atomicity.** One idea per note, in your own words, titled with the
   claim. Eighteen notes that each answer one question you already know the answer to are eighteen *non-blank* pages.
   This is the mechanism behind Matuschak's "executable strategy": the task stops being *write the post* and becomes
   *find notes, write the missing ones, concatenate, rewrite* — steps that are individually doable.

4. **The rest of Zettelkasten does not transfer, and importing it is the main risk.** Classic Zettelkasten is built for
   *literature-derived* knowledge accumulating over *years* toward *unknown future* works. Your material is
   experiential, already in your head, aimed at one known work, overdue. That is close to the least Zettelkasten-shaped
   writing task there is. The fleeting→literature→permanent pipeline collapses to a single step. Emergent bottom-up
   structure is not just unnecessary — it would reopen the outline decision you closed on 2026-07-07 after 19 days.

5. **You are ~70% built already, which is why this can be scoped to one session rather than a system.** Your vault has
   5,322 notes, the transclusion habit (`![[note#^ref]]`), Dataview, a highlights pipeline, and — decisively — the
   **Note Refactor** plugin already installed, which splits one note into many. That is a dictation-blob-to-atoms
   converter you already own. Nothing needs to be installed.

6. **Recommended: a *directed* Zettelkasten, scoped to this one post, in your existing vault, seeded from quotes you
   have already written.** Details in §6. The scope guard matters as much as the method: this is one directory and
   ~20 notes, not a vault reorganization. A vault-wide PKM rebuild is cycle four wearing a cardigan.

---

## 1. Verified State, 2026-08-02

Re-derived against the workspace and vault today. Changes since the 2026-07-28 report:

| Item | State on 2026-07-28 | State on 2026-08-02 |
| --- | --- | --- |
| Published post | `structured-agentic-software-engineering.md`, 2,762 words, 6 sections | unchanged (2,759 words; no commits touching `docs/blog/` since) |
| Ten `[00]`–`[09]` drafts | present, `draft: true` | unchanged, still 11 files in `docs/blog/posts/` |
| Diagram briefs | 3 briefs, 0 rendered PNGs | unchanged |
| Proofread task `^proof-draft` | stalled, 1 annotation | still stalled |
| Authorship-gap research | delivered | ingested as `bob:ref/chat/first_post_authorship_gap.md`, task `^writers-block-research` marked in-progress, **1 highlight** (and it is a frontmatter fragment, not content) |
| **New** | — | `bob:why_sase.md` created 2026-08-01; task `^why-sase` added to `sase_blog_0.md` |

### 1a. The decisive new artifact

`bob:why_sase.md` in full (body, 60 words):

```markdown
I've always been proud to call myself a Software Engineer. It's always been an easy thing to take pride in
([insert dolla dolla bills]). Maybe

- It started with Claude Code.
- Software engineer changing. Crazy 12 months. Something big is happening.
- Let's look back at the last 12 months:
	- claude
	- codex
```

Read the shape, not the content. Two complete sentences. Then a trailing *"Maybe "* — the sentence where the commitment
got too expensive to finish. Then a fallback to bullets. Then the bullets themselves collapse to bare nouns. The note
loses resolution monotonically as it goes, because each successive line is being asked to carry more of a 2,500-word
obligation than the last.

This is not writer's block in the romantic sense. It is a container problem. The prior report prescribed eighteen
four-minute answers; what got created was one note scoped to the entire post. **The prescription was correct and the
container silently overrode it.**

### 1b. What this changes about the diagnosis

The 2026-07-28 report predicted "absent a change of method, cycle four is another generated draft." That prediction was
wrong in an encouraging way. Cycle four was *not* generated — you sat down and wrote it yourself. The ownership problem
is further along than the report thought. What remains is a mechanical problem about where the words go, and that is a
much cheaper problem.

---

## 2. What Zettelkasten Actually Is

Stripped of the mystique, there are five claims, of which only the first three matter here.

1. **Atomicity.** One idea per note. [zettelkasten.de](https://zettelkasten.de/atomicity/guide/) is explicit that this
   is *"a guiding compass that needs to be contextualised,"* not a law — and that treating it as a rigid rule
   *"is hindering the progress of many people."* Digital practitioners routinely run to ~500 words per note. Matuschak's
   framing is the most useful one for you: it is
   [separation of concerns](https://notes.andymatuschak.org/Evergreen_notes_should_be_atomic) — *"put things which
   belong together in a Zettel, but try to separate concerns from one another."*

2. **Own words.** A note is not a quote or a link; it is you having restated the idea. Ahrens' line — *"writing is not
   what happens after you've done your thinking, writing is the process of thinking"* — is the entire justification.
   For your case this is load-bearing for a second reason: notes in your own words are, by construction, the layer §4b
   of the prior report showed agents structurally cannot produce.

3. **Titles as claims.** [Evergreen note titles are like APIs](https://notes.andymatuschak.org/Evergreen_notes_should_be_atomic):
   the title states the assertion, not the topic. `the_agents_tab_is_the_buggiest_part_of_the_tui` is a note title;
   `agents_tab` is a folder name. This is a small discipline with an outsized effect — a titled claim is already the
   topic sentence of a paragraph, so the note is one-third written before you start.

4. **Dense linking / emergent structure.** Notes link to notes; over years, structure emerges bottom-up that you did not
   plan. **This is the part that does not apply.** See §3.

5. **Structure notes / MOCs.** A higher-order note that arranges links into a reading order. In orthodox Zettelkasten
   these are *records of connections already apparent*; in Nick Milo's LYT they are
   [active work stations](https://writing.bobdoto.computer/zettelkasten-linking-your-thinking-and-nick-milos-search-for-ground/)
   where you challenge and rearrange notes. For a directed writing project, the LYT reading is the useful one — and your
   outline is already exactly this object.

### 2a. The two modes, and which one you are in

Matuschak's [Executable strategy for writing](https://notes.andymatuschak.org/Executable_strategy_for_writing) names
both modes explicitly. This distinction is the single most important finding in this report:

> **Undirected:** Write notes continuously while reading; organically develop outlines; flesh them out when inspired.
>
> **Directed:** Review topic-related notes, create an outline, attach/write notes for each point, then concatenate and
> rewrite.

Almost everything written about Zettelkasten online describes the **undirected** mode — because that is the interesting,
philosophical, Luhmann-produced-70,000-cards mode. It is also the mode that takes years and produces work you did not
plan.

**You are unambiguously in the directed mode.** The outline exists. The topic is fixed. The deadline is real. The
material is in your head rather than in books. Directed mode is a legitimate, first-class part of the method, and it
reduces to four mechanical steps: *outline → attach a note per point → write the missing notes → concatenate and
rewrite.*

Everything in §6 is that loop and nothing else.

---

## 3. The Fit Test: What Transfers and What Doesn't

Honest scoring against your actual situation.

| Zettelkasten property | Transfers? | Why |
| --- | --- | --- |
| Atomicity | ✅ **The whole reason to do this** | Directly fixes the `why_sase.md` container failure (§1a). 18 small non-blank pages instead of 1 big blank one. |
| Own words | ✅ Essential | It *is* the missing layer. Also enforces R4 (agents as fact-checkers, not writers). |
| Titles as claims | ✅ Cheap and high-yield | A titled claim is a pre-written topic sentence; and a title you can't state is a section you don't have an opinion about — useful early signal. |
| Structure note / MOC | ✅ Already exists | `sase_blog_0#^outline` is a structure note that hasn't been told it's one. |
| Fleeting → literature → permanent pipeline | ⚠️ Collapses to one step | Your sources are your own memory, git history, and your vault — not books. There is no literature-note stage. Trying to run all three tiers adds two folders and zero value. |
| Emergent bottom-up structure | ❌ **Reject** | You already spent 19 days closing the outline decision (2026-06-18 → 2026-07-07). Letting structure "emerge" reopens it. The prior report's §3 is right: keep the structure, fill the layer. |
| Dense inter-note linking | ❌ Not now | Links pay off across hundreds of notes over years. Across 18 notes for one post, the structure note *is* the linking. |
| Permanence / vault-wide adoption | ❌ Out of scope | See §3a. |
| Unique IDs / Folgezettel numbering | ❌ Skip | Pure ceremony at this scale. Obsidian resolves `[[wikilinks]]` by filename. |

### 3a. The honest risk: methodology as cycle four

The prior report's most important warning was that *"more research is the failure mode, not the fix,"* and that both
source reports' seductive recommendation — *start over with a better structure* — was cycle four in better clothes.

**Adopting a note-taking methodology is a textbook instance of that same failure mode**, and it deserves to be named
before recommending it. The specific hazard is the **collector's fallacy**: the substitution of collecting-and-organizing
for thinking-and-shipping, which the Zettelkasten community itself identifies as the method's characteristic pathology
(*"I collect these with the idea that I will apply them, some day, but they just collect dust"*).

Your variant is unusually well-documented, because you have the numbers: **6,003 plan documents and 292 research
reports against 2,230 beads.** You have a demonstrated, industrial-scale capacity for producing high-quality
preparatory artifacts about work instead of the work. A blank Zettelkasten is the most appealing preparatory artifact
ever invented. Note also that this very report is itself a preparatory artifact, and the fourth one about this blog post.

Three concrete guards, all of which are part of the recommendation and not optional caveats:

- **Scope is one directory and ~20 notes.** Not the vault. Your 5,322 existing notes stay exactly as they are. Any
  sentence beginning "first I should reorganize" is the fallacy talking.
- **Admission criterion.** A note is allowed to exist only if you can name the section of the post it will be
  transcluded into. No orphans, no "interesting, might use later." This single rule is what makes it a writing tool
  rather than a collection.
- **One-session timebox.** If the first session does not produce notes, the method failed — fall back to dictating
  straight into `sase_blog_0#^outline` as R1 originally said. The method is a means; do not defend it.

### 3b. Why it is nevertheless worth doing

Given all of §3a — why not just do R1 as written? Because R1 was already tried and produced `why_sase.md`. The delta
between "dictate 18 answers" and this recommendation is *18 files instead of 1*, which is a one-line change to the
prescription that addresses the observed failure mode. That is a small enough intervention to be worth it, and it is
small enough that it cannot become a project.

---

## 4. Your Vault Is Already Most of the Way There

Verified in `~/bob` today. This is the argument for Obsidian over any alternative: you are not adopting a system, you
are naming one you already run.

| Zettelkasten requirement | What you already have |
| --- | --- |
| Plain-text linked notes | 5,322 markdown notes, `[[wikilinks]]`, git-versioned, Obsidian Sync via `ob` |
| Literature notes | `lit/` (81 notes) and `ref/` (341) with a real PDF→highlights→note pipeline (`bob highlights`) |
| Transclusion / assembly | You already embed block refs: `![[ref/chat/first_post_authorship_gap#^ref]]` |
| Structure notes | Every project note is one; `sase_blog_0#^outline` is the one that matters |
| Query layer | Dataview + `bob query` |
| Capture | `bob capture` (routes, sections, clipboard, scheduling) + WisprFlow dictation |
| **Blob → atomic notes** | **`note-refactor-obsidian` v1.8.2, already installed** — *"Extract note content into new notes and split notes"* |
| Templating | `templater-obsidian`, `quickadd`, `_templates/` |

That last row is the one that makes this practical. The dictation-shaped hole in the method — *"how do I get from a
40-minute voice dump to 18 separate notes without 18 acts of manual filing?"* — is already plugged by a plugin you
installed for other reasons. Dictate one blob, select each chunk, split it into its own note.

### 4a. You already have starting stock

A Zettelkasten's cold-start problem is that it is empty. Yours would not be. §6 of the prior report inventoried eight
quotable lines already in your vault, none of which appear in any post. Every one of them is an atomic note that has
already been written and merely lacks a file:

- *"I'm bad at naming things but I worry that indicates a deeper problem with the design."*
- *"...but the truth is ..."* (`sase_blog_0_legacy_notes.md`, the unfinished origin sentence)
- *"sase does not claim optimal performance, but optimal experience."*
- *"Alternations allow for 'vibe evals'."*
- *"Accumulated degradation in alignment ... AKA **prompt debt**."*
- *"Plan mode is the canonical or best example of some deeper primitive. I know it. Interrupts?"*
- *"make the prompt input widget so fucking awesome that using any other editor for agent prompts is unthinkable."*
- *"no weasels; just work."*

Plus the dropped requirements from §4b of the prior report — the Gas Town comparison, the four AI-slop categories, the
limitations list, the naming jokes — each of which is one note.

**That is roughly 15 notes of starting stock before you write a new word.** Harvesting them is a mechanical, 20-minute,
zero-judgment task, and it means the first genuinely new note you write goes into a populated system rather than an
empty one. Do this first; it is the cheapest possible on-ramp and it is not preparation, it is content.

---

## 5. Alternatives Considered

You said you are open to suggestions, so all of these were evaluated seriously.

| Option | Verdict | Reasoning |
| --- | --- | --- |
| **Obsidian vault, plain notes + structure note** | ✅ **Recommended** | Material is already there. Zero installs. Note Refactor handles the dictation split. Sync means phone capture works. Git-versioned. |
| Obsidian + **Longform** plugin | ⚠️ Rejected, but reconsider for post 1+ | Genuinely good at exactly this — scenes compiled into a manuscript via configurable workflows. But it means a new plugin, project scaffolding, and a compile config, for one 2,500-word post. That is tool-building at the exact moment tool-building is the enemy. Revisit if the ~10-post series continues. |
| Obsidian + Templater compile scripts | ❌ Rejected | Same objection, more DIY. For 18 notes, manual paste is faster than writing the compiler. |
| **SASE-native** (beads / plans / artifacts) | ❌ Rejected, and this one is a trap | It is the most tempting option — you own the tool, it has structure, and there is a plausible "dogfooding" story. But the repo's `plans/` and `research/` trees are *agent* territory: 6,003 plans and 292 reports produced by delegation. Putting the one artifact that must be unfakeably yours into the delegation pipeline is how it becomes agent prose again. The vault/repo split is a useful boundary — keep it. |
| **Logseq / Tana / Roam** | ❌ Rejected | Outliner-first tools are arguably a better fit for a claim-per-bullet workflow, and Tana's supertags would model the 3-question grid elegantly. Irrelevant: migrating 5,322 notes, or running two systems, costs more than the post. |
| Write directly in the repo markdown | ❌ Already tried, three times | This is what produced the replace-don't-own cycle. The post file is where *editing* happens, not where thinking happens. |
| Physical index cards | ⚠️ Not crazy | Luhmann's actual medium, and the friction genuinely helps atomicity. But it breaks dictation, the one capture method your ledger says completes. |
| Do nothing new; just execute R1 as written | ⚠️ The honest baseline | Already attempted 2026-08-01, produced `why_sase.md`, stalled in one day. The recommendation is R1 plus one structural change. |

### 5a. On the vault/repo boundary

Worth stating explicitly because it generalizes: **agents work in the repo; you work in the vault; the compile step is
the boundary.** This makes R4 of the prior report ("demote agents from writer to fact-checker") architectural rather
than aspirational — an agent cannot ghost-write a note it cannot see, and the vault is not in any agent's workspace.
It is the same isolation argument SASE makes about workspaces, applied to prose.

---

## 6. Recommended Solution

**A directed Zettelkasten, scoped to one post, in `~/bob`, seeded from quotes you already wrote.**

Name it by its directory: `~/bob/zk/blog0/`. One folder, flat, no subfolders, no ID scheme.

### Step 0 — Reframe `why_sase.md` (2 minutes)

It is currently the manuscript. Make it the **structure note**: the six section headings from the published post, each
followed by an empty bullet list that will hold `![[...]]` embeds. Move its 60 words of existing prose into
`zk/blog0/proud_to_call_myself_a_software_engineer.md` — that is a real note, and it is the first one.

Reconcile the section list once, in one line, and never again: your `^outline` says *Introduction, Overview, XPrompts,
ACE, AXE, Future Blog Posts*; the published post ships *Intro, SASE Wraps Agent CLIs, XPrompts, The Agents Tab In ACE,
Install, What's Next*. Anchor on the **published** six, since that is the artifact being edited, and fold AXE into
What's Next. This is a reconciliation, not a restructuring — do not spend a second session on it.

### Step 1 — Harvest existing stock (20 minutes, zero judgment)

One file per line from §4a, plus one per dropped requirement from the prior report's §4b table. Title = the claim.
Body = the quote plus one sentence of context. Then add the embed to the right section of the structure note.

This is deliberately mindless. It ends with ~15 notes on disk and the structure note visibly populated. The point is
that Step 2 begins in a non-empty system.

### Step 2 — Dictate the grid (one 45-minute session)

R1 from the prior report, unchanged in content, changed in destination. For each of the six sections, three questions:

> **High value** — what did this actually buy me?
> **High untapped opportunity** — what could it do that it doesn't yet?
> **Lesson learned** — what did it cost me to figure this out? What broke first?

Rules, carried forward because they are correct: dictate (WisprFlow — the only method in your ledger that ever completed
on time); do not open any existing draft; do not look up commands, dates, or names; mark uncertainty rather than
stopping to check it; transcribe verbatim.

**The one change:** dictate into a single scratch note, then use **Note Refactor** to split it into one file per answer.
Do not try to dictate into 18 files — that is filing, and filing during dictation kills dictation.

If you can only start one thing, start with **ACE**, because you already know the punchline: *the agents tab is the
buggiest part of the TUI.*

### Step 3 — Title the notes as claims (10 minutes)

Note Refactor will name files from first lines. Rename each to state its claim. This is fast, it is editing rather than
composing, and it surfaces the gaps: any note you cannot title is a cell where you don't yet have an opinion. That is
useful information, not failure — mark it and move on.

### Step 4 — Arrange, don't write (15 minutes)

In the structure note, order the embeds within each section into a reading order. Matuschak: *"your task is more like
editing than composition. You can make an outline by shuffling the note titles."* You are shuffling titles. No prose is
produced in this step, on purpose.

### Step 5 — Compile and rewrite (the actual writing session)

Paste the note bodies under their headings in the repo post file, in structure-note order, and rewrite for flow:
transitions, cut duplicates, fix seams. Manual paste — do not build a compiler for 18 notes. The prior report's R6 voice
checklist runs here, on paragraphs, not during note-writing.

The published post is 2,759 words and the target is 2,000–2,500, so this session **cuts as much as it adds**: thin the
Install section to a link, and thin XPrompts (the longest and most reference-dense section). Your new notes buy their
space from the tour.

### Step 6 — Hand agents the fact-check pass

R4 of the prior report, unchanged: verify every command/flag/keymap against source, re-derive every statistic, find
`file:line` citations, flag terminology drift, render the three diagram briefs to PNG. Agents do not write sentences.

### Definition of done, per note

- One paragraph, ≤150 words.
- Title states a claim.
- Contains at least one date, number, or name (prior report R6 #2 — specificity is the cheapest humanity signal, and
  §5's ledger means you have more of it available than nearly anyone writing in this space).
- Names the section it belongs to.
- You would say it out loud.

### Effort

| Step | Time | Output |
| --- | --- | --- |
| 0. Reframe | 2 min | Structure note + 1 note |
| 1. Harvest | 20 min | ~15 notes |
| 2. Dictate | 45 min | ~18 notes |
| 3. Title | 10 min | Named claims + a gap list |
| 4. Arrange | 15 min | Ordered structure note |
| 5. Compile & rewrite | 1 real session | Publishable draft |
| 6. Agent fact-check | delegated | Verified draft |

Roughly **90 minutes of your time before the writing session**, and none of those 90 minutes involves facing a blank
page.

---

## 7. What Not To Do

- **Do not build the vault-wide Zettelkasten.** Not now. If the method works, post 1 can extend it. 5,322 notes are not
  a migration project you take on while blocked on a deadline.
- **Do not install anything.** Not Longform, not a ZK prefixer, not an ID scheme. Everything above uses plugins already
  in `~/bob/.obsidian/plugins/`.
- **Do not build the compile pipeline.** Copy-paste. Eighteen notes.
- **Do not restructure the post.** The outline is yours, it cost 19 days, and the prior report's §3 settles it.
- **Do not let agents write notes.** They can fact-check, cite, and render diagrams. The notes are the deliverable and
  the deliverable must be yours — that is the entire point of §5a's boundary.
- **Do not read more about Zettelkasten.** The method is §2, in full, and you have now read it. The literature is large,
  self-referential, and optimized for the undirected mode you are not in. This report is the fourth preparatory
  artifact about this post; it should be the last.

---

## 8. Answering the Original Question Directly

> *Is Zettelkasten the right approach, and should it be Obsidian?*

**Yes to Obsidian**, decisively and for unglamorous reasons: the raw material, the quotes, the outline, the task ledger,
the highlights pipeline, and the blob-splitting plugin are already there, and moving is pure cost.

**Yes to Zettelkasten, but only its directed mode, and really only its atomicity principle.** The evidence is specific
rather than ideological: your last four attempts to write this post used a container scoped to the whole post, and all
four decayed in the same way — most recently and most legibly in `why_sase.md`, which visibly loses resolution from
prose to bullets to bare words over 60 words. Atomic notes change the unit of commitment from *a post* to *a paragraph
you already know the answer to*. That is the only thing that needs to change, and it is a one-line amendment to a
prescription you already have.

The rest of the method — emergence, dense linking, three-tier pipelines, permanent IDs — is real, valuable, and aimed at
a different problem than yours. Skip it. **No weasels; just work.**

---

## Appendix A: Verification

```bash
# Vault state
wc -w ~/bob/why_sase.md                                     # 99 (60 body)
find ~/bob -name '*.md' -not -path '*/.obsidian/*' | wc -l  # 5322
ls ~/bob/.obsidian/plugins/                                 # note-refactor-obsidian present
git -C ~/bob log --oneline --since=2026-07-25                # why_sase.md landed 2026-08-01

# Repo state
wc -w docs/blog/posts/structured-agentic-software-engineering.md   # 2759
grep -n '^## ' docs/blog/posts/structured-agentic-software-engineering.md
git log --since=2026-07-20 --oneline -- docs/blog/          # no post edits since
ls docs/images/blog/*.prompt.md                             # 3 briefs, still 0 PNGs
```

## Appendix B: Source Locations

| What | Where |
| --- | --- |
| Structure note (to be) | `bob:why_sase.md` |
| Your outline | `bob:sase_blog_0.md` → `## Outline` / `^outline` |
| Requirements, quotes, screenshots | `bob:sase_blog.md` |
| Origin sentence, "no weasels" | `bob:sase_blog_0_legacy_notes.md` |
| Stalled proofread annotations | `bob:ref/docs/sase_blog_260708.md` |
| Prior diagnosis | `sase/repos/research/202607/first_post_authorship_gap/first_post_authorship_gap.md` |
| Launch-readiness audit | `sase/repos/research/202607/blog_launch_readiness_audit.md` |
| Post being edited | `docs/blog/posts/structured-agentic-software-engineering.md` |
| Unrendered diagram briefs | `docs/images/blog/*.prompt.md` |

## Sources

**Method** — [Andy Matuschak: Executable strategy for writing](https://notes.andymatuschak.org/Executable_strategy_for_writing)
(the directed/undirected distinction — the key source for this report) ·
[Andy Matuschak: Evergreen notes should be atomic](https://notes.andymatuschak.org/Evergreen_notes_should_be_atomic) ·
[Andy Matuschak: Create speculative outlines while you write](https://notes.andymatuschak.org/Create_speculative_outlines_while_you_write) ·
[zettelkasten.de: The Complete Guide to Atomic Note-Taking](https://zettelkasten.de/atomicity/guide/) ·
[zettelkasten.de: The Principle of Atomicity — Principle vs. Implementation](https://zettelkasten.de/posts/principle-of-atomicity-difference-between-principle-and-implementation/) ·
[zettelkasten.de: Create Zettel from Reading Notes](https://zettelkasten.de/posts/create-zettel-from-reading-notes/) ·
[Bob Doto: Zettelkasten, Linking Your Thinking, and Nick Milo's Search for Ground](https://writing.bobdoto.computer/zettelkasten-linking-your-thinking-and-nick-milos-search-for-ground/)
(structure notes vs. MOCs)

**Practitioner accounts** — [David Kadavy: My Zettelkasten — An Author's Digital Slip-Box Method Example](https://kadavy.net/blog/posts/zettelkasten-method-slip-box-digital-example/)
(a working author's end-to-end pipeline, and his warning against over-applying it) ·
[Fatih Arslan: The Zettelkasten note-taking methodology](https://arslan.io/2025/01/30/the-zettelkasten-note-taking-methodology/) ·
[Zettelkasten Forum: collector's fallacy discussion](https://forum.zettelkasten.de/discussion/909/how-to-take-smart-notes-structure-note) ·
[Ali Abdaal: How to Take Smart Notes — summary](https://aliabdaal.com/book-notes/how-to-take-smart-notes/)

**Tooling** — [Longform plugin (kevboh)](https://github.com/kevboh/longform) ·
[Longform compile docs](https://github.com/kevboh/longform/blob/main/docs/COMPILE.md) ·
[Nosy Science: Longform-style compiling with Templater instead](https://nosy.science/2025/09/30/longformstemplater/)

**Internal** — `~/bob` (vault, git log, plugin manifests, `bob --help`, `bob capture --help`) ·
`docs/blog/posts/` · `sase/repos/research/202607/` · git history through 2026-08-02
