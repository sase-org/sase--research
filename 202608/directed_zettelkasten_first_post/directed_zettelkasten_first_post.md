---
create_time: 2026-08-02
updated_time: 2026-08-02
status: research
---

# A Directed Zettelkasten for SASE's First Blog Post

**Research question:** Bryan wants to write SASE's first blog post using a Zettelkasten-inspired methodology, probably
in Obsidian. What actually transfers, which tool should hold the work, and what is the smallest method that produces the
post rather than a system for producing the post?

**Sources merged:** `directed_zettelkasten_first_post__a.md` (research.x.cdx) and
`directed_zettelkasten_first_post__b.md` (research.x.cld), plus independent verification performed 2026-08-02 07:38–07:45
EDT. Both source reports are preserved beside this one.

**Prior work:** [`202607/first_post_authorship_gap/`](../../202607/first_post_authorship_gap/first_post_authorship_gap.md)
(2026-07-28) diagnosed the block as an *ownership gap*, not a blank page, and prescribed **R1**: dictate three answers
per outline section. This report accepts that diagnosis and asks the narrower question both source reports converged on:
*why didn't R1 happen, and does Zettelkasten fix that specific failure?*

---

## Bottom Line

1. **Both reports reach the same recommendation, and it is the right one:** a *directed*, project-scoped Zettelkasten in
   the existing `~/bob` Obsidian vault. Not a second brain, not a vault migration, not a tool switch, not a new draft.
   Their disagreements are about containers and ceremony, and are resolved in §4.

2. **The single mechanism that transfers is atomicity.** One idea per note, in your own words, titled with the claim.
   The unit of commitment changes from *a 2,500-word post* to *a paragraph you already know the answer to*. Everything
   else — emergent structure, dense linking, Folgezettel IDs, the fleeting→literature→permanent pipeline — is built for
   a different problem and importing it is the main risk.

3. **Report B's central citation checks out and should anchor the method.** Matuschak's *Executable strategy for
   writing* does explicitly name two modes; the directed one reads verbatim: *"Review notes related to your topic…
   Write an outline… Attach existing notes to each point in the outline; write new notes as needed,"* then *"Concatenate
   all the note texts together to get an initial manuscript"* and rewrite. You are unambiguously in that mode. Nearly
   all popular Zettelkasten writing describes the undirected mode, which takes years and produces work you did not plan.

4. **⚠️ Report B's headline evidence went stale three minutes after it was written.** B built its argument on
   `why_sase.md` decaying into a trailing *"Maybe "*. As of **07:37:44 today** that sentence is finished, and finished
   well (§1a). B was accurate at 07:34 and is superseded now. The diagnosis survives — the container is still scoped to
   the whole post — but the recommendation must not demolish a file you are actively writing in.

5. **Obsidian, decisively, for unglamorous reasons.** Verified today: 5,322 notes, and `note-refactor-obsidian` v1.8.2
   is *already installed* — a dictation-blob-to-atoms splitter you own for other reasons. Longform is not installed and
   should stay that way. Nothing needs to be installed, migrated, or configured.

6. **You have ~18 notes of starting stock before writing a word**, all verified in the vault today (§1c). The
   cold-start problem that kills most Zettelkasten attempts does not apply to you.

7. **Total cost: ~90 minutes of focused time before the writing session**, none of it facing a blank page — inside a
   one-week stop condition.

---

## 1. Verified State, 2026-08-02 ~07:40 EDT

Re-derived independently; commands in Appendix A. Where the source reports differ on a number, the verified value is
given here and used throughout.

| Item | Verified value | Notes |
| --- | --- | --- |
| Published post | `docs/blog/posts/structured-agentic-software-engineering.md`, **2,759 words** | A said "~2,700"; B said 2,759 ✅ |
| Post sections | intro (untitled) + *SASE Wraps Agent CLIs* · *XPrompts* · *The Agents Tab In ACE* · *Install, Configure, Initialize* · *What's Next* | B's list ✅ |
| `^outline` sections | *Introduction · Overview · XPrompts · ACE · AXE · Future Blog Posts* | **Mismatched with the published six** — B caught this; A did not |
| Sibling drafts | 10 files, all `draft: true`, **~18,100 words total** | Excluded from the built site |
| Diagram briefs | 3 `*.prompt.md`, still **0 rendered PNGs** | Unchanged since 2026-07-28 |
| Vault size | **5,322** notes | B ✅ exact |
| `note-refactor-obsidian` | **v1.8.2, installed** | B ✅ exact |
| Longform | **not installed** | Confirms B's "would require an install" |
| Other relevant plugins | `dataview`, `templater-obsidian`, `quickadd`, `obsidian-tasks-plugin`, `metadata-menu`, `obsidian-linter`, `block-id-prompt`, `bob-*` | |
| `why_sase.md` | created 2026-08-01 13:20, **modified 2026-08-02 07:37:44, uncommitted** | See §1a |

### 1a. The state change that postdates both reports

Report B quoted `why_sase.md` as breaking off mid-sentence on *"Maybe "* and called that decay curve "the whole problem
in one file." That was true of the version committed to the vault at `6ecb00a` (2026-08-02 03:30). The working file has
since been edited — mtime **07:37:44**, after both researchers had finished writing — and now reads:

> I've always been proud to call myself a Software Engineer. It's always been an easy thing to take pride in ([insert
> dolla dolla bills]). **Maybe it was my pride that made me start working on [sase](todo). My attempt to take back some
> control from this thing that seemed like it was coming for a core part of my identity.**
>
> - **List sase's stats (e.g. LoC, commits, repos, etc..) with _"Motion isn't progress"_ quote from codex podcast.**
> - It started with Claude Code.
> - Software engineer changing. Crazy 12 months. Something big is happening.
> - […]

Three things follow, and they matter more than the correction:

- **The completed sentence is exactly the missing layer.** *"My attempt to take back some control from this thing that
  seemed like it was coming for a core part of my identity"* is unfakeable, first-person, and passes every item on the
  prior report's R6 voice checklist. Nothing in 18,000 words of drafts sounds like it. The capability was never in doubt;
  what this shows is the *unit* in which it arrives — one or two sentences at a time. That is the atomic-note argument,
  observed rather than argued.
- **B's structural diagnosis survives intact.** The note grew by one sentence and one bullet, then reverted to bullets
  and bare nouns. Prose → bullets → single words is still the shape. A container whose stated job is *"will contain full
  blog post"* still charges every sentence against a 2,500-word obligation.
- **Do not gut this file.** B's Step 0 says to move its prose out into `zk/blog0/` and convert it to a structure note.
  Executing that this morning would clobber live work. §4 resolves this differently.

### 1b. The three-question grid is mechanically invisible

The prior report identified the grid — *"Flesh out 'high value, high untapped opportunity, and an associated lesson
learned' for each section"* — as the missing human layer, specified by Bryan, in his own framing. Verified detail neither
new report noticed: in `sase_blog_0.md` it is a **plain sub-bullet under a task already marked `[x]` complete**
(`^outline`, `completion:: 2026-07-07`), not a `#task` of its own. The note's own frontmatter counts
`task_count: 8, open_task_count: 4` — the grid is in neither number.

So the highest-value action in the project is invisible to the task system that governs everything else you do. That is
a 30-second fix and it belongs in Step 0.

### 1c. Starting stock — verified present, none published

Report B's claim of ~15 notes of stock is well-founded; every line below was confirmed in the vault today. Three items
are *newer* than B's list.

From `sase_blog.md`: *"I'm bad at naming things but I worry that indicates a deeper problem with the design"* · *"make
the prompt input widget so fucking awesome that using any other editor for agent prompts is unthinkable"* · *"Plan mode
is the canonical or best example of some deeper primitive. I know it. Interrupts?"* · *"Alternations allow for 'vibe
evals'"* · the four AI-slop categories incl. **prompt debt** · the Gas Town breakdown · *"the agents tab is the buggiest
part of the TUI"* · the limitations list · the naming jokes.

From `sase_blog_0_legacy_notes.md`: the unfinished origin sentence *"…but the truth is …"* · *"no weasels; just work"* ·
Gas Town's fatal flaw (can't interweave agent calls with deterministic code) · the Codex-parity / unified-CLI goals.

From `sase_blog_0.md`: *"sase does not claim optimal performance, but optimal experience"* · **new 2026-08-01:** *"The
term 'sub-agent' doesn't cut it when referring to agents that other agents run."*

From `why_sase.md`: **new today:** the *"Motion isn't progress"* stats framing, and the identity paragraph itself.

That is **~18 notes that are already written and merely lack a file.**

### 1d. Carried forward: the assets are still gone

Re-verified: all four screenshots referenced in `sase_blog.md` (`20260616_140429`, `20260616_115015`, `20260619_214831`,
`20260624_074728`) are **absent from the entire home directory**, though 294 other screenshots spanning 2026-06-15 →
2026-08-02 survive. The prior report flagged this on 2026-07-28; five days later nothing has been re-captured. The
Claude-outage retry, `%wait`, alternations, and questions/retries/tales examples must be re-shot or dropped. Neither new
report mentions it.

---

## 2. What Transfers, and What Doesn't

The two reports' analyses of the method agree almost completely; this is the merged version, with B's directed/undirected
frame as the organizing principle because it is the one externally verified claim that carries real weight.

| Property | Transfers? | Why |
| --- | --- | --- |
| **Atomicity** | ✅ The whole reason to do this | Fixes the container failure directly: 18 small non-blank pages instead of one big blank one. Note that zettelkasten.de itself calls atomicity *"a guiding compass that needs to be contextualised,"* not a rule — a note is one *idea*, not one sentence. |
| **Own words** | ✅ Essential | It *is* the missing layer, and it is structurally the thing agents cannot supply. Ahrens: *"writing is the process of thinking."* |
| **Titles as claims** | ✅ Cheap, high yield | `the_agents_tab_is_the_buggiest_part_of_the_tui` is a title; `agents_tab` is a folder. A titled claim is a pre-written topic sentence — the note is a third done before you start. A title you *can't* state marks a section you don't yet have an opinion about, which is useful early signal. |
| **Structure note / MOC** | ✅ Already exists | `sase_blog_0.md#^outline` is a structure note that hasn't been told it's one. |
| Fleeting → literature → permanent | ⚠️ Collapses to one step | Your sources are memory, git history, and your own vault — not books. Running three tiers adds two folders and zero value. |
| Emergent bottom-up structure | ❌ Reject | You spent 19 days closing the outline decision (2026-06-18 → 07-07). Letting structure "emerge" reopens it. |
| Dense inter-note linking | ❌ Not now | Links pay off across hundreds of notes over years. Across ~30 notes for one post, the structure note *is* the linking. |
| Unique IDs / Folgezettel | ❌ Skip | Ceremony at this scale. Obsidian resolves `[[wikilinks]]` by filename. |
| Vault-wide adoption | ❌ Out of scope | See §5. |

**On evidence quality.** Report A was commendably honest that the external literature is thin: Luhmann's archive
documents his own practice, Ahrens and Matuschak are influential practitioner systems, and no controlled study shows a
digital Zettelkasten beats a plain outline for professional blogging. One qualification — A's supporting citation, the
Graham/Kiuhara/MacKay 2020 writing-to-learn meta-analysis, is about K–12 content learning and should not be carried into
the recommendation; it is too distant to bear weight. The honest position is that the *project-local* evidence (§1) is
strong and the *general* evidence is weak, which is precisely why this is a one-week pilot with a stop condition rather
than a conversion.

---

## 3. Tool Decision: Obsidian, in `~/bob`

Both reports agree; the merged case is short because it is uncontested.

You are not adopting a system, you are naming one you already run: 5,322 plain-text linked notes, git-versioned, synced
via `ob`; `[[wikilinks]]` and block transclusion (`![[note#^ref]]`) already habitual; Dataview and `bob query`;
WisprFlow dictation; `bob capture`; and **Note Refactor already installed**, which plugs the one hole in the method —
*how do I get from a 40-minute voice dump to 18 files without 18 acts of manual filing?*

Alternatives, merged from both reports' tables:

| Option | Verdict |
| --- | --- |
| **Obsidian, existing vault, plain notes + structure note** | ✅ **Recommended.** Zero installs, material already present, sync means phone capture works. |
| Obsidian + **Longform** | ⚠️ Rejected now; reconsider for the series. Genuinely built for this, but it is a plugin install plus project scaffolding plus a compile config for one 2,500-word post — tool-building at the moment tool-building is the enemy. Verified not installed. |
| Obsidian + Templater compile scripts | ❌ Same objection, more DIY. For ~30 notes, manual paste beats writing the compiler. |
| **SASE-native** (beads / plans / artifacts) | ❌ **Rejected, and this one is a trap.** The most tempting option — you own the tool, there is a dogfooding story. But `plans/` and `research/` are *agent* territory (6,003 plans, 292 reports by delegation). Putting the one artifact that must be unfakeably yours into the delegation pipeline is how it becomes agent prose again. Only B considered this; it is the most valuable rejection in either report. |
| Logseq / Tana / Roam | ❌ Arguably better fits for claim-per-bullet work; irrelevant against migrating 5,322 notes or running two systems. |
| Org-roam | ❌ Excellent for an existing Emacs/Org user; its own manual warns of the investment otherwise. |
| Zotero | ❌ Not the writing home. Optional companion for a future source-heavy post. |
| Plain Markdown + git/editor search | ❌ No benefit over the vault you already have. |
| Write directly in the repo post file | ❌ Already tried three times — this *is* the replace-don't-own cycle. |
| Physical index cards | ⚠️ Not crazy (Luhmann's medium, friction genuinely aids atomicity) but it breaks dictation, the one capture method your ledger says completes. |
| Just execute R1 as written | ⚠️ The honest baseline — attempted 2026-08-01, produced `why_sase.md`, stalled in a day. |

### 3a. The vault/repo boundary is the real architecture

Worth stating because it generalizes (B's insight, and the sharpest structural idea in either report): **agents work in
the repo; you work in the vault; the compile step is the boundary.** This makes the prior report's R4 — demote agents
from writer to fact-checker — architectural rather than aspirational. An agent cannot ghost-write a note it cannot see,
and the vault is in no agent's workspace. It is SASE's own workspace-isolation argument applied to prose.

---

## 4. Where the Two Reports Conflict — and How It Resolves

| Conflict | Report A (cdx) | Report B (cld) | Resolution |
| --- | --- | --- | --- |
| **Where the structure note lives** | Create a new `SASE blog 0 — control` note | Reframe `why_sase.md` into it, move its prose out | **Neither.** `sase_blog_0.md#^outline` already *is* the structure note. A adds a fourth container to a project that already has too many; B's move would clobber a file edited at 07:37 today. Use what exists (§6 Step 0). |
| **`parent` frontmatter** | Required, with a worked template | Never mentioned | **A is right, decisively.** The obsidian memory states new `~/bob` notes must carry a `parent` link, and the vault follows it universally (`parent: "[[sase_blog_0.md\|sase_blog_0]]"`). B's `zk/blog0/` notes would violate the convention and fall out of `bob`'s parent-based navigation and project-task rollups. |
| **Note count** | 12–18 total | "~20" as the guard, but ~15 harvested **+** ~18 dictated | **~18 harvested + 18 dictated ≈ 36.** B is internally inconsistent; A's cap is too tight to hold both the stock and the grid. Cap the *dictated* notes at 18 (it is 6 sections × 3 questions — your own committed grid). Harvest is mechanical and needs no cap. |
| **Note template weight** | 5 headings: What I mean / Evidence / Tension / Reader consequence / Connections | One paragraph, ≤150 words | **B's body, A's frontmatter.** Five headings × 36 notes is 180 form fields — the collector's fallacy in template form. A's headings are excellent as *dictation prompts*, not as stored structure. |
| **`why_sase.md` evidence** | Not used | Decay curve, trailing *"Maybe "* | **Superseded 07:37:44** (§1a). B was accurate when written; the sentence is now finished. |
| **Post word count** | "~2,700" | 2,759 | 2,759 verified. |
| **Outline vs. published sections** | Assumes the published six | Flags the mismatch, anchors on published | **B.** Reconcile once, in one line: anchor on the **published** six (that is the artifact being edited) and fold *AXE* into *What's Next*. This is a reconciliation, not a restructuring — do not spend a session on it. |
| **Calendar** | One-week pilot with a stop condition | ~90 minutes of focused time | **Both, nested.** ~90 focused minutes (B's table is more actionable) inside A's one-week stop condition. |

---

## 5. Risks

### 5a. The methodology *is* the failure mode it treats

Both reports name this and neither flinches, correctly. The prior report's warning was *"more research is the failure
mode, not the fix."* Adopting a note-taking methodology is a textbook instance of that, and Zettelkasten's characteristic
pathology has a name — the **collector's fallacy**, substituting collecting-and-organizing for thinking-and-shipping.
Your variant is unusually well documented: **6,003 plan documents and 292 research reports against 2,230 beads.** A blank
Zettelkasten is the most appealing preparatory artifact ever invented. This report is the *fifth* preparatory artifact
about this post and should be the last.

Three non-optional guards:

- **Scope is one folder and ~36 notes.** Not the vault. Your 5,322 existing notes stay exactly as they are. Any sentence
  beginning *"first I should reorganize"* is the fallacy talking.
- **Admission criterion.** A note may exist only if you can name the section of the post it goes into. No orphans, no
  "interesting, might use later." This single rule is what makes it a writing tool rather than a collection.
- **One-session timebox.** If the first session does not produce notes, the method failed — fall back to dictating
  straight into the outline as R1 said. The method is a means; do not defend it.

**Why do it at all, given the above?** Because R1 *was* tried and produced `why_sase.md`. The delta between "dictate 18
answers" and this recommendation is **18 files instead of 1** — a one-line amendment to a prescription you already have,
targeted at the observed failure. Small enough to be worth it; small enough that it cannot become a project.

### 5b. The risk neither report named: atoms make choppy prose

A post assembled from atomic notes can read as *an artifact of note-taking* — the documented critique of Matt Gemmell's
"Atomic Thoughts" essay in the Zettelkasten forum is exactly this, an essay whose style contradicted its own thesis by
reading as reassembled fragments. The failure mode is real and it is specific to your case: this post's whole job is
**voice**. Thirty-six well-formed atoms concatenated under six headings is a listicle with paragraphs.

Both reports have a "rewrite for flow" step; neither names the hazard or gives a test. Add one. At assembly, run the
prior report's R6 voice checklist **plus an eighth item**:

> **8. Does this paragraph connect to the one before it, or merely sit next to it?** If you can swap two adjacent
> paragraphs without noticing, you have a list, not an argument. Write the seam.

Budget for the seams. The concatenated manuscript is the *input* to the writing session, not its output — Matuschak says
"concatenate… then rewrite," and the rewrite is not a formality.

---

## 6. Recommended Solution

**A directed Zettelkasten, scoped to one post, in `~/bob`, using containers that already exist, seeded from quotes you
already wrote.**

Notes live in one new flat folder, `~/bob/zk/blog0/`. No subfolders, no ID scheme. Every note carries
`parent: "[[sase_blog_0.md|sase_blog_0]]"`.

### Step 0 — Assign roles to existing containers (5 minutes)

Do not create a new control note, and **do not gut `why_sase.md`** — you were writing in it at 07:37 this morning.

| Container | Role |
| --- | --- |
| `sase_blog_0.md#^outline` | **Structure note.** Already is one. Reconcile to the published six sections in one line; fold *AXE* into *What's Next*. |
| `why_sase.md` | **Assembly note.** Leave the identity paragraph exactly where it is — it is note #1 and it is already in the right place. Its bullets become the section slots that will hold `![[…]]` embeds. |
| `~/bob/zk/blog0/` | **The notes.** New, flat, one post only. |

Then make the grid visible: promote the buried sub-bullet under `^outline` into its own top-level `#task` in
`sase_blog_0.md` (§1b). Right now the highest-value action in the project is not counted in `open_task_count`.

### Step 1 — Harvest existing stock (20 minutes, zero judgment)

One file per item in §1c. Title = the claim. Body = the quote plus one sentence of context. Frontmatter =
`parent`, plus `section:` naming where it goes. Add the embed to the matching bullet in `why_sase.md`.

This is deliberately mindless. It ends with ~18 notes on disk and the assembly note visibly populated — so Step 2 begins
in a non-empty system. It is not preparation; it is content.

### Step 2 — Dictate the grid (one 45-minute session)

R1 unchanged in content, changed in destination. For each of the six published sections, three questions:

> **High value** — what did this actually buy me?
> **High untapped opportunity** — what could it do that it doesn't yet?
> **Lesson learned** — what did it cost me to figure this out? What broke first?

Report A's two extra prompts are worth adding: *"What is still bad?"* and *"What is funny only because it really
happened?"*

Rules, carried forward because they are correct: dictate (WisprFlow — the only blog method in your ledger that ever
completed on time); do not open any existing draft; do not look up commands, dates, or names; mark uncertainty rather
than stopping to check it; transcribe verbatim.

**The one change:** dictate into a *single* scratch note, then use **Note Refactor** to split it into one file per
answer. Do not try to dictate into 18 files — that is filing, and filing during dictation kills dictation.

If you can only start one thing, start with **ACE**: you already know the punchline.

### Step 3 — Title the notes as claims (10 minutes)

Note Refactor names files from first lines; rename each to state its claim. This is editing, not composing. Any note you
cannot title marks a cell where you have no opinion yet — record it as a gap and move on.

### Step 4 — Arrange, don't write (15 minutes)

In `why_sase.md`, order the embeds within each section: scene or problem → claim → mechanism → cost or open question.
Matuschak: *"your task is more like editing than composition. You can make an outline by shuffling the note titles."*
No prose is produced in this step, on purpose. Any section with no `Lesson learned` or `Limitation` note is a section
that will read like documentation — ask another question rather than letting an agent manufacture an answer.

### Step 5 — Compile and rewrite (the real writing session)

Paste note bodies under their headings in `docs/blog/posts/structured-agentic-software-engineering.md`, in assembly
order, then rewrite for flow. Manual paste — do not build a compiler for 36 notes.

Two passes, in order: **additive** (insert your material), then **subtractive** (cut the documentation prose it makes
redundant). This is where the post is won or lost — run the R6 voice checklist plus the connective-tissue test from
§5b on every paragraph.

The post is 2,759 words against a 2,000–2,500 target, so this session **cuts as much as it adds**: thin Install to a
link (Getting Started does it better, and your own outline already has a task to move it) and thin XPrompts, the
longest and most reference-dense section. Your new notes buy their space from the tour.

### Step 6 — Hand agents the verification pass

Unchanged from R4, plus one addition: verify commands/flags/keymaps against source, re-derive every statistic, find
`file:line` citations, flag terminology drift, **render the three diagram briefs to PNG**, and **re-capture the four
lost screenshots** (§1d). Agents do not write sentences. Never present `gemini` as a supported CLI — the five are
`claude`, `codex`, `agy`, `qwen`, `opencode`.

### Definition of done, per note

One paragraph, ≤150 words · title states a claim · contains at least one date, number, or name · names its section ·
you would say it out loud.

### Effort

| Step | Time | Output |
| --- | --- | --- |
| 0. Assign roles + surface the task | 5 min | Structure/assembly roles fixed, grid visible |
| 1. Harvest | 20 min | ~18 notes |
| 2. Dictate | 45 min | ~18 more |
| 3. Title | 10 min | Named claims + gap list |
| 4. Arrange | 15 min | Ordered assembly note |
| 5. Compile & rewrite | 1 real session | Publishable draft |
| 6. Agent verification | delegated | Verified draft, rendered diagrams, re-shot screenshots |

**~95 minutes before the writing session, none of it facing a blank page** — inside a one-week stop condition.

### After publication

Mark used notes `status: published` with a link to the post. Keep claims that could serve later posts — with ten drafts
queued, reuse is the one Zettelkasten benefit you can actually bank. Then evaluate honestly: did atomic notes make it
easier to *resume*? Did any note get reused? Did the folder get drained or become another backlog? If the answer is
mostly no, keep dictation and the grid, drop the rest.

---

## 7. What Not To Do

- **Do not build the vault-wide Zettelkasten.** If the method works, post 1 can extend it. 5,322 notes are not a
  migration you take on while blocked on a deadline.
- **Do not install anything.** Not Longform, not an ID scheme. Everything above uses plugins already in
  `~/bob/.obsidian/plugins/`.
- **Do not build the compile pipeline.** Copy-paste.
- **Do not restructure the post.** The outline is yours and it cost 19 days.
- **Do not create another control note.** Three containers already exist; a fourth is the fallacy.
- **Do not let agents write notes.** They fact-check, cite, and render. The notes are the deliverable and the deliverable
  must be yours.
- **Do not read more about Zettelkasten.** §2 is the method in full. The literature is large, self-referential, and
  optimized for the undirected mode you are not in.

---

## Appendix A: Verification Commands

```bash
# Vault (2026-08-02 ~07:40 EDT)
stat -c '%y' ~/bob/why_sase.md                                  # 2026-08-02 07:37:44 -0400
git -C ~/bob status --short why_sase.md                         # M (uncommitted)
git -C ~/bob log -p --since=2026-08-01 -- why_sase.md           # 6ecb00a @ 03:30 holds the pre-edit text
find ~/bob -name '*.md' -not -path '*/.obsidian/*' | wc -l      # 5322
ls ~/bob/.obsidian/plugins/                                     # note-refactor-obsidian present; no longform
bob query --format markdown --query-file <(echo 'TABLE parent WHERE startswith(file.name,"sase_blog")')

# Repo
wc -w docs/blog/posts/structured-agentic-software-engineering.md   # 2759
grep -c '^draft: true' docs/blog/posts/*.md                        # 10 of 11
ls docs/images/blog/*.prompt.md                                    # 3 briefs, 0 matching PNGs

# Lost assets
find ~ -name '20260616_140429*' -o -name '20260616_115015*' \
       -o -name '20260619_214831*' -o -name '20260624_074728*'     # no results
```

## Appendix B: Source Locations

| What | Where |
| --- | --- |
| Structure note | `bob:sase_blog_0.md` → `## Outline` / `^outline` |
| Assembly note | `bob:why_sase.md` |
| Requirements, quotes | `bob:sase_blog.md` |
| Origin sentence, "no weasels" | `bob:sase_blog_0_legacy_notes.md` |
| Stalled proofread annotations | `bob:ref/docs/sase_blog_260708.md` |
| Prior diagnosis | `202607/first_post_authorship_gap/first_post_authorship_gap.md` |
| Launch-readiness audit | `202607/blog_launch_readiness_audit.md` |
| Post being edited | `docs/blog/posts/structured-agentic-software-engineering.md` |
| Unrendered diagram briefs | `docs/images/blog/*.prompt.md` |

## Sources

**Method (verified)** — [Matuschak: Executable strategy for writing](https://notes.andymatuschak.org/Executable_strategy_for_writing)
(directed vs. undirected — quoted verbatim in §Bottom Line, fetched and confirmed 2026-08-02) ·
[Matuschak: Evergreen notes should be atomic](https://notes.andymatuschak.org/Evergreen_notes_should_be_atomic) ·
[Matuschak: A writing inbox for transient and incomplete notes](https://notes.andymatuschak.org/zUP4GuzPF33dWkZPiu9N6V5) ·
[zettelkasten.de: The Complete Guide to Atomic Note-Taking](https://zettelkasten.de/atomicity/guide/) ·
[zettelkasten.de: Principle vs. Implementation](https://zettelkasten.de/posts/principle-of-atomicity-difference-between-principle-and-implementation/) ·
[Luhmann Archive: *Technik des Zettelkastens* (1968)](https://niklas-luhmann-archiv.de/bestand/manuskripte/manuskript/MS_2906_0001) ·
[Ahrens: *How to Take Smart Notes*](https://www.soenkeahrens.de/en/takesmartnotes) ·
[Bob Doto: Zettelkasten, LYT, and Nick Milo's search for ground](https://writing.bobdoto.computer/zettelkasten-linking-your-thinking-and-nick-milos-search-for-ground/)

**Risks** — [Zettelkasten Forum: "Atomic Thoughts" by Matt Gemmell](https://forum.zettelkasten.de/discussion/comment/17108/)
(essay reading as an artifact of note-taking — the §5b hazard) ·
[Zettelkasten Forum: collector's fallacy](https://forum.zettelkasten.de/discussion/909/how-to-take-smart-notes-structure-note) ·
[Kadavy: My Zettelkasten — a working author's pipeline, and his warning against over-applying it](https://kadavy.net/blog/posts/zettelkasten-method-slip-box-digital-example/)

**Tooling** — [Obsidian Help: Properties](https://obsidian.md/help/properties) ·
[Backlinks](https://obsidian.md/help/plugins/backlinks) · [Bases](https://obsidian.md/help/bases) ·
[Longform plugin](https://github.com/kevboh/longform) (evaluated, rejected, not installed) ·
[Org-roam manual](https://www.orgroam.com/manual)

**Not carried forward** — Graham, Kiuhara & MacKay (2020) writing-to-learn meta-analysis, cited by report A: real, but
about K–12 content learning rather than professional writing, and too distant to support this recommendation.

**Internal** — `~/bob` (git log, plugin manifests, `bob query`) · `docs/blog/posts/` ·
`sase/repos/research/202607/` · source reports `__a` (research.x.cdx) and `__b` (research.x.cld), 2026-08-02.
