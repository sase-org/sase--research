---
create_time: 2026-08-02
updated_time: 2026-08-02
status: research
---

# From Notes to Post: A Zettelkasten-Inspired Workflow for SASE's First Blog Post

## Research Question

What parts of the Zettelkasten method would actually help Bryan finish SASE's first blog post, which tool should hold
the work, and how can the method be kept small enough that building a note system does not replace writing the post?

## Bottom Line

Use **a project-seeded, Zettelkasten-inspired workflow inside the existing Bob Obsidian vault**. Do not build a
general-purpose “second brain,” migrate the vault, switch tools, or restart the post. Create one writing inbox, one
control/structure note based on the existing outline, and at most 12–18 short notes containing Bryan's own claims,
scenes, admissions, jokes, and lessons. Capture those by dictation, develop them in writing, arrange links to them under
the existing section headings, and then assemble them into the repository draft.

This is a better fit than a strict reproduction of Luhmann's paper system. It preserves the useful mechanisms—writing
in one's own words, atomicity, contextual linking, and bottom-up synthesis—while omitting numeric addresses, a deep
taxonomy, a global graph workflow, and a plugin project. Obsidian is the right tool because it is already Bryan's note
environment, stores ordinary local Markdown, supports links/backlinks, properties, and templates natively, and already
syncs headlessly on this machine.

The success criterion is not “a healthy Zettelkasten.” It is a publishable post with at least one unmistakably
Bryan-authored claim, story, or limitation in every substantive section.

## 1. What Zettelkasten Contributes—and What It Does Not

“Zettelkasten” is used online to mean several different things: linked notes, personal knowledge management, a folder
scheme, a graph visualization, or a faithful digital copy of Niklas Luhmann's card index. For this project, the most
useful definition is narrower:

> A writing practice in which small, independently understandable notes are written in the author's own words,
> explicitly related to other notes, and later selected and ordered into a larger argument.

Four mechanisms matter.

### 1.1 Rewriting is thinking, not clerical capture

Luhmann's 1968 description says excerpts should be exceptional rather than page-length copies, stresses trying one's
own formulations, and separates one's own thought from a source's thought. He also says that critical restatement is
itself thought-work and a way to develop one's language. This is particularly relevant to SASE: the missing material is
not more feature documentation but Bryan's judgment about the features.
([Niklas Luhmann Archive: “Technik des Zettelkastens”](https://niklas-luhmann-archiv.de/bestand/manuskripte/manuskript/MS_2906_0001))

A 2020 meta-analysis of 56 writing-to-learn experiments found a modest positive learning effect from writing about
content. That research concerned school learning, not Zettelkasten or professional blogging, so it is supporting
evidence for generative writing—not proof that this particular method beats alternatives.
([Graham, Kiuhara, and MacKay, 2020](https://doi.org/10.3102/0034654320914744))

### 1.2 “Atomic” means one reusable idea, not one sentence

A useful note is about one claim, scene, question, or tension and contains enough context to make sense later. It may be
one paragraph or several. Splitting every sentence creates fragments with no meaning; keeping an entire book or project
in one note makes linking imprecise. Andy Matuschak's formulation is a good practical test: make a note about one thing
while capturing enough of that thing to be useful.
([Evergreen notes should be atomic](https://notes.andymatuschak.org/Evergreen_notes_should_be_atomic))

For this post, good note titles are assertions or vivid handles:

- `The scrollback buffer became my first agent database`
- `Provider independence is a UX choice, not an abstraction exercise`
- `The ACE Agents tab is both SASE's value proposition and its buggiest surface`
- `Prompt debt grows when reusable instructions remain trapped in chat history`

Bad titles merely name buckets: `ACE`, `Thoughts`, `Blog research`, or `Agents`.

### 1.3 Links should state a relationship

Luhmann regarded references—not topical filing—as the mechanism that solved organizational problems. A digital link is
most valuable when the surrounding sentence explains why two ideas belong together. “This failure led to
[[Durable agent records are more important than durable terminals]]” is useful; a context-free `Related: [[ACE]]` is
usually not.

Backlinks then make the reverse relationship discoverable. Obsidian's core Backlinks plugin exposes linked and
unlinked mentions without requiring a community plugin.
([Obsidian Backlinks](https://obsidian.md/help/plugins/backlinks))

### 1.4 Structure notes turn a network into an argument

Atomic notes do not magically become a post. A structure note—also called an outline note, hub, or map of
content—selects a small “hand” of notes and orders them for a particular output. The same idea can later appear in a
different structure note for another post.

For this project, the existing blog outline is already the structure note. The method should enrich that decision, not
reopen it. This is the crucial adaptation from an open-ended research Zettelkasten to a post with a known purpose.

## 2. The SASE-Specific Problem to Solve

The July research report, [The Authorship Gap](../202607/first_post_authorship_gap/first_post_authorship_gap.md),
established several facts that were rechecked against the repository on 2026-08-02:

- The current front-door post still exists at `docs/blog/posts/structured-agentic-software-engineering.md` with the
  same broad structure: introduction, provider boundary, XPrompts, ACE, installation, and future posts.
- Its opening has a concrete `tmux_ai_window` scene and the strongest Bryan-authored material in the draft.
- Most of the remainder explains product behavior in documentation-like prose.
- The previously chosen outline asked for “high value,” “high untapped opportunity,” and a “lesson learned” for each
  main section, but those answers were not supplied.
- The repeated failure pattern has been to replace an unowned draft with another generated draft.

This changes how Zettelkasten should be used. A conventional literature-first workflow would deepen the wrong side of
the post: more externally sourced information and more competent product explanation. The first notes should instead
be **experience notes** and **claim notes**. External source notes are only needed when a factual assertion requires
support.

The method is valuable here because it changes the unit of work from “proofread a 2,700-word agent draft” to “write one
true paragraph about what XPrompts cost me to learn.” It allows authorship to accumulate without demanding a complete
essay-shaped performance in one sitting.

## 3. Tool Options

| Option | Strengths | Costs and risks | Fit for this post |
| --- | --- | --- | --- |
| **Existing Obsidian vault** | Local Markdown; internal links and backlinks; native properties and templates; current Bob workflow and headless sync | Easy to overbuild with plugins, metadata, and graph aesthetics | **Best fit** |
| Plain Markdown plus Git/editor search | Minimal, portable, excellent for final prose and review | Capture and backlink discovery require more manual work; duplicates the existing vault | Good fallback, but no benefit over current Obsidian setup |
| Logseq | Block-first capture, journals, backlinks, and queries; attractive for rapid bullet-based thinking | A second store and different block/document model; migration and export friction add no value to this post | Worth considering only if daily block journaling is already preferred |
| Org-roam | Plain text, strong linking/query capabilities, deep Emacs integration | Its own manual warns of the investment for people not already fluent in Emacs and Org-mode | Excellent for an existing Org-mode user; poor reason to switch now ([manual](https://www.orgroam.com/manual)) |
| Zotero | Excellent source library, PDF annotations, and citation provenance | Does not solve first-person synthesis or long-form structure; adds another inbox | Optional companion for future research-heavy posts, not the writing home ([docs](https://www.zotero.org/support/quick_start_guide)) |

Obsidian itself is both a Markdown editor and a linked knowledge base, and its data lives as local plain-text files.
That makes it compatible with shell tools, Git, and other editors rather than turning the notes into an application-only
database. ([About Obsidian](https://obsidian.md/help/obsidian)) Sönke Ahrens now describes his own refined digital
workflow as Obsidian-based, though that is practitioner preference rather than comparative evidence.
([Take Smart Notes](https://www.soenkeahrens.de/en/takesmartnotes))

The best tool decision is therefore the uneventful one: remain in Bob. A tool switch would introduce novelty exactly
where this project needs continuity.

## 4. The Minimal Obsidian Design

Use only three core capabilities for the first post:

1. **Properties** for a small amount of machine-readable state. Obsidian stores these as YAML in the Markdown file and
   supports links, lists, dates, checkboxes, and other simple types.
   ([Properties](https://obsidian.md/help/properties))
2. **Templates** for consistent capture without repeated setup.
   ([Templates](https://obsidian.md/help/plugins/templates))
3. **Links and backlinks** for contextual connections and retrieval.

Do not install a plugin for this pilot. Do not use the global graph as a dashboard. Obsidian Bases can later provide a
table of notes filtered by project and status while leaving the data in Markdown, but with fewer than 20 notes even
that is optional. ([Obsidian Bases](https://obsidian.md/help/bases))

### 4.1 The four artifacts

1. **One writing inbox** — a low-friction place for dictation transcripts, fragments, questions, and copied excerpts.
   It is temporary and must be drained. Matuschak's writing-inbox practice is useful here because it explicitly pairs
   frictionless capture with regular development or deletion.
   ([A writing inbox for transient and incomplete notes](https://notes.andymatuschak.org/zUP4GuzPF33dWkZPiu9N6V5))
2. **One control/structure note** — the existing outline, reader definition, coverage matrix, and ordered links to
   developed notes.
3. **12–18 atomic notes** — predominantly Bryan's claims and experiences, plus a few source notes where evidence is
   actually necessary.
4. **The repository draft** — the source of truth for publishable prose. Obsidian is for thinking and assembly; the
   blog Markdown file is for the manuscript. Do not build two-way synchronization between them.

Every new Bob note must include the vault's required `parent` property linking to another Bob Markdown note. A minimal
idea-note template is:

```markdown
---
parent: "[[SASE blog 0 — control]]"
type: idea
status: seed
project: "[[SASE blog 0 — control]]"
sections:
  - ace
source_kind: experience
created: "{{date}}"
---

# {{title}}

## What I mean

Write the claim in your own words. Two to five sentences is enough.

## Evidence or scene

What happened? Include a concrete date, command, failure, cost, or decision if one exists.

## Tension

What is the limitation, objection, tradeoff, or thing that is still broken?

## Reader consequence

Why should an experienced developer care?

## Connections

- This follows from [[...]] because ...
- This complicates [[...]] because ...
```

Use `type: story` when the scene is primary and `type: source` for an external work. Keep the same property names and
types. For source notes, add a `source_url` property and distinguish paraphrase from any short quotation. Status needs
only four values: `seed`, `developed`, `placed`, and `published`.

### 4.2 The control note

The control note should not become another long manuscript. It is the small project cockpit:

```markdown
---
parent: "[[sase_blog]]"
type: writing-project
status: active
created: "{{date}}"
---

# SASE blog 0 — control

## Reader and promise

Experienced solo developer or tech lead running several coding-agent CLIs.
After reading, they should understand why a durable operating layer became necessary.

## Constraints

- Keep the existing outline and opening.
- Target 2,000–2,500 words.
- No agent-written first-person experience or belief.
- Every substantive section gets one Bryan-owned claim, scene, or admission.

## Coverage matrix

| Section | High value | Untapped opportunity | Lesson/scar | Limitation | Concrete asset |
| --- | --- | --- | --- | --- | --- |
| Introduction | | | | | |
| Provider boundary | | | | | |
| XPrompts | | | | | |
| ACE | | | | | |
| Install | | | | | |
| What's next | | | | | |

## Working outline

1. Introduction
   - [[The scrollback buffer became my first agent database]]
2. Provider boundary
   - [[...]]
```

Here `[[sase_blog]]` means the existing parent blog-project note documented in the July audit; if that note has since
been renamed, use its current link rather than creating a dangling parent solely to preserve the example.

The matrix is deliberately redundant with the outline. It reveals whether a section contains lived judgment before
draft assembly begins.

## 5. A Bounded Workflow for the First Post

### Step 0: Freeze the target

Declare the current post and existing outline to be the target for this cycle. No alternate angle, replacement draft,
new series architecture, or vault reorganization is allowed until the post is published or explicitly abandoned.

### Step 1: Capture by voice without looking at the draft (45 minutes)

Dictate answers to these three prompts for each of the six sections:

1. What does this feature or choice actually buy me?
2. What could it become, or what opportunity is still unused?
3. What broke, cost time, embarrassed me, or changed my mind while I learned this?

Add two optional prompts: “What remains bad?” and “What is funny only because it really happened?” Do not fact-check or
polish during capture. Mark uncertainty aloud. Dictation is especially appropriate because the prior blog ledger shows
that Bryan completed the earlier voice brain-dump while prose-ownership tasks stalled.

### Step 2: Drain the inbox into 12–18 notes (two or three 30-minute sessions)

For each useful fragment:

- Write a claim-like title.
- Restate it in writing rather than preserving only the transcript.
- Add one concrete detail and one cost, limitation, or counterpoint.
- Link it to one existing note or another new note and explain the relationship.
- Delete or archive fragments that do not become interesting after two passes.

Cap the pilot at 18 developed notes. Scarcity forces selection and blocks the system from becoming a collecting hobby.

### Step 3: Fill the coverage matrix before opening the manuscript

Place links to developed notes in the matrix. A cell may reuse a note, and some sections do not need all five cells,
but each substantive section must have one of `High value`, `Lesson/scar`, or `Limitation` filled. If a row is empty,
ask another question; do not ask an agent to manufacture an answer.

### Step 4: Build the argument in the control note

Under each existing heading, arrange 2–4 linked notes in reader order:

1. scene or problem;
2. claim;
3. product mechanism;
4. cost, limitation, or unresolved question.

This is where bottom-up notes meet the already chosen top-down outline. Obsidian's backlinks can suggest relevant
material, but the control note—not the global graph—owns sequence.

### Step 5: Assemble, then rewrite (one 90-minute session)

Copy the useful note bodies into the repository post under their selected headings. Write transitions in the
manuscript. The note is a component, not sacred prose: merge repetition, cut setup, and change ordering as needed. The
goal is to preserve the thought's provenance, not its exact wording.

Do an additive pass first: insert Bryan-owned material. Do a subtractive pass second: remove documentation prose that
the new material makes unnecessary. This reduces the risk that editing turns back into wholesale replacement.

### Step 6: Use agents as reviewers, not autobiographers

Agents are well suited to:

- verify commands, names, keybindings, dates, and statistics against source;
- identify claims that need citations;
- flag terminology drift and duplicated explanations;
- test examples and links;
- ask adversarial questions or point to empty matrix cells;
- suggest possible links between notes for Bryan to accept or reject.

Agents should not invent first-person scenes, decide what Bryan believes, generate humor, or rewrite the post “in
Bryan's voice.” A useful rule is: **the agent may ask the question and verify the answer, but it may not supply the
experience.**

### Step 7: Publish and compost

After publication, change used notes to `status: published` and add the post link. Keep claims that could serve future
posts. Archive the control note and clear the inbox. Only then decide whether the pilot revealed a stable workflow
worth generalizing across the whole SASE series.

## 6. Guardrails Against Zettelkasten Procrastination

The method's largest practical risk is not bad note-taking. It is productive-feeling system construction.

- **No vault migration.** Start with new work; do not retrofit every old note. Ahrens explicitly advises that a new
  workflow does not require reorganizing prior material.
  ([2022 preview, pp. 8–10](https://www.soenkeahrens.de/s/2022-HTTSN-Preview.pdf))
- **No numeric Luhmann IDs.** File-level Markdown links already provide sufficient addressability and human-readable
  handles for this use case.
- **No folder debate.** Use the vault's existing placement conventions and required `parent` field. Semantic structure
  lives in links; project state lives in a few properties.
- **No graph gardening.** The graph is an exploration aid, not a completion metric.
- **No plugin installation before publication.** Core Obsidian features are sufficient.
- **No source collection without a question.** The first post needs experience and judgment more than a larger reading
  list. The official Web Clipper is useful later for source-driven posts, but clipping is capture, not synthesis.
  ([Web Clipper](https://obsidian.md/help/web-clipper))
- **No permanent inbox.** Drain it on the next writing session; archive or delete weak fragments.
- **No “number of notes” goal.** Track covered sections and placed Bryan-owned ideas instead.

## 7. Evidence Quality and Open Questions

The strongest evidence for this recommendation is project-local: a selected outline and good opening already exist;
agent-produced prose accumulates quickly; authorial judgment is the recurring bottleneck; and voice dictation is the
one demonstrated capture method that completed. The Zettelkasten literature supplies a mechanism that fits those facts.

The external evidence is less definitive than the method's popularity suggests. Luhmann's archive documents his own
practice. Ahrens and Matuschak offer thoughtful, influential practitioner systems. Obsidian's documentation establishes
tool capabilities. The writing-to-learn meta-analysis supports generative writing in an adjacent setting. None is a
controlled comparison showing that a digital Zettelkasten produces better professional blog posts than a plain outline
or commonplace book.

That uncertainty argues for a pilot with a stop condition, not a lifestyle conversion. After the post ships, evaluate:

- Did atomic notes make it easier to resume writing?
- Did links surface a non-obvious connection that survived into the post?
- How many notes were actually reused?
- Did the inbox get drained, or become another backlog?
- Did the system shorten the path to Bryan-owned prose?

If the answer is mostly no, retain the useful dictation and coverage-matrix steps and drop the rest.

## Sources

- [Niklas Luhmann Archive: *Technik des Zettelkastens* (1968)](https://niklas-luhmann-archiv.de/bestand/manuskripte/manuskript/MS_2906_0001)
- [Sönke Ahrens: *Take Smart Notes*](https://www.soenkeahrens.de/en/takesmartnotes)
- [Sönke Ahrens: 2022 book preview](https://www.soenkeahrens.de/s/2022-HTTSN-Preview.pdf)
- [Andy Matuschak: Evergreen notes](https://notes.andymatuschak.org/Evergreen_notes)
- [Andy Matuschak: A writing inbox for transient and incomplete notes](https://notes.andymatuschak.org/zUP4GuzPF33dWkZPiu9N6V5)
- [Obsidian Help: About Obsidian](https://obsidian.md/help/obsidian)
- [Obsidian Help: Properties](https://obsidian.md/help/properties)
- [Obsidian Help: Templates](https://obsidian.md/help/plugins/templates)
- [Obsidian Help: Backlinks](https://obsidian.md/help/plugins/backlinks)
- [Obsidian Help: Bases](https://obsidian.md/help/bases)
- [Graham, Kiuhara, and MacKay: “The Effects of Writing on Learning...” (2020)](https://doi.org/10.3102/0034654320914744)
- [Org-roam User Manual](https://www.orgroam.com/manual)
- [Zotero Quick Start Guide](https://www.zotero.org/support/quick_start_guide)
- Internal: [The Authorship Gap: Finishing SASE's First Blog Post](../202607/first_post_authorship_gap/first_post_authorship_gap.md)
- Internal: `docs/blog/posts/structured-agentic-software-engineering.md`, checked 2026-08-02

## Recommended Solution

Run a **one-post Obsidian pilot in Bob for no more than one week**:

1. Create `SASE blog 0 — inbox` and `SASE blog 0 — control`, each with the required `parent` property.
2. Copy the existing outline into the control note and add the six-row coverage matrix above.
3. Do one 45-minute voice session answering “high value, untapped opportunity, lesson/scar, limitation, and funny true
   detail” for each section without opening the current draft.
4. Convert only the best material into 12–18 atomic, claim-titled notes using core Obsidian Properties, Templates, and
   Backlinks. Install nothing and reorganize nothing.
5. Arrange those note links beneath the existing outline, assemble them into the current repository post, then cut the
   agent-documentation prose they replace.
6. Let agents fact-check, test, and challenge the result, while keeping all first-person experience, belief, humor, and
   final wording under Bryan's authorship.
7. Publish, mark the used notes, archive the project control note, and only then decide whether to expand the workflow
   to later SASE posts.

This solution uses Zettelkasten where it is strongest—as an incremental thinking and synthesis practice—without letting
the note system become a fourth attempt to avoid owning the post.
