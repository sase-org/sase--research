# Turning the SASE blog draft into actionable Obsidian work

Independent research by cdx · 2026-10-23

**Recommendation:** Run a bounded editorial spike, then write one concrete SASE story from beginning to end. Use that story to decide which abstractions need explaining. Keep a small queue of tasks that produce passages, evidence, or decisions in your existing `sase_blog` project. The present draft gives enough material to begin; another broad reading or outline project would add little until a body passage exists.

This report investigates task design and writing workflow. It does not rewrite the post, change the vault, or implement the proposed tasks. No other researcher's report or findings from this swarm were consulted.

**What the current material tells us.**

I read `/home/bryan/bob/sase_blog_contents.md`, then used read-only Bob queries to inspect the directly related project and its tasks. The draft contains two prose paragraphs: a personal account of engineering identity and control, followed by a product introduction and the self-deprecating observation about a prototype growing dramatically. The remainder is a seven-part taxonomy under “The Abstractions,” with two additional subsections under Agent CLIs. Those sections currently contain `TODO`. Four footnote placeholders cover naming, a meta-harness example, links, and statistics.

The opening already supplies a reason to care. The proposed body asks the author to explain nearly the whole system. My working hypothesis is that the missing connection between those two jobs creates avoidable difficulty: every `TODO` requires you to decide what the reader needs, choose evidence, choose scope, and compose prose at once. This is an editorial inference, not a psychological diagnosis.

Your existing project makes the intended outcome especially clear: the post should be live on `sase.sh` **in your own voice**. Its present task graph also matters:

| Observed item | Consequence for the recommendation |
| --- | --- |
| `sase_blog_contents` already has `parent: "[[sase_blog]]"`; `sase_blog` is a project under `sase`. | Reuse the two notes. A new project hierarchy is unnecessary. |
| `^write-introduction` is the current Next task; `^v1-draft` depends on it. | The body can be drafted before polishing the opening. Reconsider that sequencing explicitly. |
| `^v1-draft` blocks the existing `sase_pre_blog` project. | Preserve this outgoing dependency when decomposing the milestone. |
| Tasks already exist for future work, GasTown analogies, listening to an audio version, and release. | Refine and sequence these tasks rather than duplicating them. |
| Release has an explicit prerequisite outside this writing project. | Preserve that prerequisite. A finished manuscript and permission/readiness to publish are separate milestones. |
| `bob ready sase_blog --format json` reports a Ready cap of five, with one Ready reading task; `bob capture-tasks` identifies one Next task. | There is no need for a new task plugin or a large imported queue. Start with one writing decision task. |

The inspected task format uses `#task`, block IDs, and indented `DEPENDS ON`/`BLOCKS` links. Bob identifies `[*]` as Next and `[?]` as Blocked. These symbols should retain their current meanings. I did not inspect unrelated projects, prior research reports, or the referenced reading contents. Dependency links alone do not prove whether every upstream requirement is still necessary.

**What the research supports.**

The following principles are relevant; their application to this particular post is my synthesis.

| Finding and source | Application here | Evidence limit |
| --- | --- | --- |
| David Allen distinguishes a multi-action outcome from the concrete action available now, and warns that sequentially unavailable steps make action lists harder to use. [Managing Projects](https://gettingthingsdone.com/2010/02/managing-projects-tips-from-david-allen/) | Keep “publish my post” as the project outcome. Give the Next lane an action with a visible output. Store the rest of the proposed route in project support material. | Practitioner guidance, not an experiment comparing writing workflows. |
| Google's technical-writing course recommends defining audience, scope, and the questions a document should answer. [Documents](https://developers.google.com/tech-writing/one/documents) | Decide what an unfamiliar reader should understand before converting the feature outline into assignments. | Guidance for technical documents; the personal narrative still needs your judgment. |
| George Mason's Writing Center recommends freewriting, beginning in the middle, and speaking ideas aloud. [Writer's Block](https://writingcenter.gmu.edu/writing-resources/writing-as-process/writers-block) | Start with the concrete case you can explain most readily. A short voice memo can preserve your phrasing when prose feels difficult. | These are techniques to try, not guaranteed remedies. |
| Reverse outlining identifies each paragraph's main point and tests the resulting sequence. [Reverse Outlining](https://writingcenter.gmu.edu/writing-resources/writing-as-process/reverse-outlining) | Use it after there is a continuous draft. The current placeholder headings offer little prose to reverse-outline. | A revision method; it cannot decide your central claim for you. |
| Masicampo and Baumeister's experiments found that specific plans reduced cognitive interference associated with unfinished goals. [Study abstract, 2011](https://pubmed.ncbi.nlm.nih.gov/21688924/) | Record a concrete next action and a restart cue at session end, so returning requires less reconstruction. | I reviewed the abstract, not the full paper. This does not establish that a particular Obsidian setup or session length cures writer's block. |
| Gregory Engel argues for time-boxed research spikes and separates learning from delivered product value. [Agile Alliance community article](https://agilealliance.org/the-practice-of-sizing-spikes-with-story-points/) | The spike ends with a decision and executable tasks. Its completion is not equivalent to progress on the manuscript itself. | An author's practitioner position, not an Agile Alliance policy or a controlled writing study. |

The time limits, task counts, word ranges, and proposed outline below are practical defaults. They are not scientifically established thresholds. No additional reading assignment is needed to use this report. A batched `bob ref find` lookup returned `not_found` for these six sources; that means absent from the indexed `ref/` library, not that you have never read them. Library check: 0 of 6 candidates already in your library (0 finished).

**Which decomposition strategy fits this draft?**

| Approach | Benefit | Cost in this situation | Judgment |
| --- | --- | --- | --- |
| Make one task for every existing heading. | Easy to create; preserves coverage. | “Write about Agent CLIs” still hides audience, evidence, and scope decisions. Every topic looks mandatory. | Useful only after a scope decision. |
| Commission a comprehensive outline and extensive supporting research. | Can expose gaps. | You already have an outline and completed reading/outline tasks. It can postpone producing the missing body indefinitely. | Reserve further research for named factual gaps. |
| Freewrite the entire post. | Produces raw material in your voice quickly. | Does not itself supply dependencies, stopping conditions, or an executable queue. | Use inside a specific passage task. |
| Choose a reader and one real case, write that case, then explain the concepts it needs. | Produces a readable portion early and gives feature selection a purpose. | Requires accepting that some interesting features will remain outside this post. | Best default for the present draft. |

If the intended deliverable is actually an exhaustive architecture reference, the recommendation changes: retain the taxonomy and decompose each section using the same evidence-and-output rubric. The current personal opening and project outcome make an introductory, experience-led post the stronger assumption.

**The editorial spike: two work sessions, with a decision at the end.**

Give the spike one question: **What is the smallest complete post that connects my reason for building SASE to something a reader can see it do?** Budget two 25-minute work sessions with a break. Keep its output within the existing project note, followed by a provisional outline in the draft.

During the first session, write a short brief with these decisions:

1. **Reader:** provisionally, a software engineer who already uses a coding-agent CLI but knows nothing about SASE. Choose one primary reader for this version.
2. **Promise:** after reading, that person can explain why you built SASE, follow one real piece of work, and judge whether to investigate it further.
3. **Central claim:** write one sentence in your own words. A starting prompt is: “I wanted a way to steer and inspect work even as coding agents did more of it.” This is proposed framing, not a quotation from you or a verified product claim.
4. **Example:** select one real completed or well-documented piece of work that you can recount. Prefer a small change with a visible human decision, an observable result, and an available record.
5. **Boundary:** choose at most three concepts that the example needs. Put the remaining draft headings into a parking list.

During the second session, arrange five or six reader questions into an outline. Give each section one intended point and the evidence or anecdote that supports it. Create only the first three executable follow-up tasks, each with input, output, completion condition, and budget. Record remaining work as provisional bullets.

The spike is finished when those decisions and tasks exist. It does not require confidence that you chose the optimal outline. If a factual uncertainty remains, either remove the dependent claim for now or create one narrowly scoped verification task. If no suitable recorded example is available, draft a clearly labeled recollection and mark details to verify. Do not make building a new feature or recording a polished demo a prerequisite for writing.

A useful provisional structure is:

| Reader question | Material to produce | Rough allowance |
| --- | --- | --- |
| Why did you build this? | Retain the personal opening; connect the feeling of lost control to one practical frustration. | 200–300 words |
| What is SASE, and who might want it? | A plain-language explanation and a clear reader promise. | 150–250 words |
| What does using it look like? | One real episode: starting need, decisions, work, inspection, outcome. | 450–650 words |
| Which ideas made that possible? | Two or three explanations grounded in the same episode. | 450–650 words total |
| What remains awkward or uncertain? | Actual limitations, costs, and a short future direction. | 200–300 words |
| What should I do next? | One verified route to learn more or try it. | 100–150 words |

This suggests roughly 1,550–2,300 words, as an editing constraint rather than a quota. Choose a different range in the spike if necessary. The episode should identify what actually happened; avoid turning the sequence into a fictional “typical” success story.

**How the existing headings contribute.**

These are proposed placements, not instructions to delete material. Keep the original outline available in the project note or a parking section.

| Current heading or placeholder | Reader question worth answering | Default treatment in the first post |
| --- | --- | --- |
| Gates → Plans → Epics | Where do I make a decision, and what happens after it? | Candidate for a core explanation if the episode demonstrates it. Do not imply that every job must traverse the whole chain. |
| Beads → Sidecar repos | How do I find the work and its record later? | Explain the visible benefit with one actual record. Keep storage details brief. |
| Agent CLIs | What does SASE contribute around the agent I already use? | Keep a concise explanation; verify current support before listing providers. |
| Skills, memory, provider interface, NOT hooks | What information and instructions reach an agent? | Include only what the selected example requires; move internals to existing documentation links. |
| Tribes, clans, families, hoods, panels | How do I keep track of several pieces of work? | At most one annotated view if it advances the story. Avoid requiring a glossary tour. |
| VCS and workspace operations | How can I inspect changes and understand where they were made? | Strong candidate if a concrete change supplies evidence. |
| Xprompts / control flow | How do I reuse or coordinate a workflow? | Use one short example if needed; check terminology and current semantics. |
| Project management / agents sidecar / artifacts | What remains available when the run is over? | Combine with the durable-record explanation where they answer the same question. |
| Routines and Jobs | What can run repeatedly? | Park unless repetition is central to the chosen episode. |
| Pronunciation, name collision, meta-harness link, other links, counts | Which small facts help orientation or credibility? | One later verification sweep; do not make these the next writing session. |

There is a concrete reason for a terminology pass: the current audited SASE glossary calls an xprompt a **macro**, and says an agent family was renamed an **agent session**. The draft still contains both older labels. That observation warrants a focused check, not a complete architecture investigation. Other capability claims and numbers in the draft were not verified during this research.

For the large commit/line counts, record the date, repository scope, counting method, and treatment of generated or vendored files if you retain them. Consider dropping a figure if explaining its meaning costs more than it contributes. A size statistic can support the “prototype grew” anecdote; it does not establish quality or user benefit.

**A practical route from the spike to publication.**

Treat the following as a proposed route to refine after the spike, not a batch to place in Ready. Budgets represent work blocks, not promises of completion. If a passage task repeatedly overruns its block, split its remaining output explicitly.

| Step | Action and visible completion condition | Prerequisite | Suggested budget |
| --- | --- | --- | --- |
| S | Choose the reader, promise, case, and scope; record the first three follow-up tasks. | Current draft | 2 blocks |
| E | Collect the selected episode's starting need, key decision, result, and source pointers into a small evidence packet. Include one limitation or complication. | S | 1–2 blocks |
| W | Write the episode as a continuous rough passage. Separate observed facts from interpretation; mark uncertain details inline. | E | 1–2 blocks |
| C1–C3 | For each selected concept, write its problem, plain explanation, example from the episode, and tradeoff in about 150–220 words. Each concept is its own task. | E and selected concepts | 1 block each |
| I | Revise the existing opening to introduce the actual body and reader promise. Preserve the phrases you still mean. | W; clearer body direction | 1 block |
| L | Write limitations, one short future-work paragraph, and the reader's next step. Reuse the existing future-work task. | E and scope | 1 block |
| V | Assemble a continuous v1: opening, episode, explanations, limits, ending. Every selected section contains prose; uncertainties are explicitly marked. | W, C tasks, I, L | 1 block |
| F | Resolve retained factual markers, naming, provider list, counts, comparisons, and links. Remove unsupported claims. | V | 1–2 blocks |
| R | Summarize each paragraph's point, repair the sequence, and listen to the draft once using the existing audio-review task. | V | 1–2 blocks |
| Q | Apply review findings and inspect the rendered post: links, captions, code, footnotes, and mobile layout if relevant. | F and R; existing publication preparation | 1–2 blocks |
| P | Complete the existing release task and verify the public page. | Q and all existing release prerequisites | Follow existing release process |

There is no need to draft in reading order. W and the C tasks can supply useful prose while the opening remains provisional. F and R can start from the same v1; they do not need to block one another. A first draft may contain factual markers; publication may not.

Each task should satisfy this test: **Can I begin without deciding what the task means, and will I know what artifact or passage proves it is finished?** “Work on abstractions” fails. “Write 180 words explaining why I used this workspace for this change, with one example and one cost” passes once the episode is chosen.

Do not measure progress primarily by completed checkboxes. Better evidence is a complete episode, a continuous manuscript, resolved claims, and a rendered page. Leave one sentence at the end of each session: “Next, open [location] and produce [specific output].”

**How to put this into the existing Obsidian project.**

Start by adding the spike, then select it into Next using your usual workflow. Keep only one writing task in Next. Maintain no more than two or three genuinely executable writing tasks in Ready, within the existing total cap of five. Leave later possibilities as ordinary project bullets until the spike makes them concrete.

Preserve the existing project outcome and block IDs. Refine `^write-introduction` into the later opening-revision task, and retain `^v1-draft` as the assembly milestone with concrete completion criteria. Review its incoming dependencies to reflect the selected body tasks while preserving its outgoing link to `sase_pre_blog`. Do not automatically erase reading dependencies or mark them satisfied: decide which claims actually require them. The canceled earlier reference and completed replacement visible in the project are reasons to inspect links, not proof that every dependency is stale.

Reuse the audio task for the listen-and-revise pass. For GasTown analogies, choose only comparisons that help this reader understand a retained concept, and verify those comparisons. Keep the release task and its existing external prerequisite. These changes are recommendations; none were applied to the vault.

This first task is ready to adapt into `sase_blog.md`:

```markdown
- [ ] #task Choose the reader, promise, and real example for the SASE post ^blog-story-spike
  - **INPUT:** [[sase_blog_contents]] and the existing project tasks.
  - **TIMEBOX:** Two 25-minute work sessions, with a break.
  - **OUTPUT:** A short brief, a 5–6-part outline, and the first three executable writing tasks.
  - **DONE:** One reader, one promise, one example, and at most three core concepts are chosen; every follow-up task names its input and finished output.
  - **STOP:** Park unresolved nonessential topics; give any essential factual gap one targeted task.
```

After the spike chooses the example, the next cards can use this shape. Replace “chosen example” with the actual episode before admitting them to the action queue:

```markdown
- [ ] #task Collect the evidence for the chosen SASE example ^blog-example-evidence
  - ⛓️ **DEPENDS ON:** [[#^blog-story-spike]]
  - **INPUT:** The example selected in the brief.
  - **OUTPUT:** Bullets covering the starting need, human decision, work, inspection, result, and one limitation, with source pointers.
  - **DONE:** Each retained factual assertion has evidence or an explicit verification marker.
  - **BUDGET:** One or two work blocks; use an existing record if creating a demo would expand scope.

- [?] #task Draft the chosen SASE example as one continuous passage ^blog-example-prose
  - ⛓️ **DEPENDS ON:** [[#^blog-example-evidence]]
  - **INPUT:** The evidence packet.
  - **OUTPUT:** Approximately 450–650 rough words in [[sase_blog_contents]].
  - **DONE:** A reader can follow the need, decisions, work, and outcome; uncertain details are marked.
  - **BUDGET:** One or two work blocks. A spoken explanation is an acceptable starting input.
```

The spike's third follow-up should be the first concept passage, with the concept named, a link to its evidence, and the four-part completion rule from C1–C3. Its exact wording should follow the choice made in the spike. Once prerequisites are complete, use the existing task workflow to promote dependent cards; `[?]` is for an actual dependency, not merely for something you intend to do later. These are ordinary Obsidian tasks, not SASE task beads.

Keeping the brief in `sase_blog` avoids a new note. If you later create a separate evidence note, the vault convention requires a `parent` link, naturally `parent: "[[sase_blog]]"` here. No new automation is necessary to make this workflow useful.

**Preserving voice and avoiding another planning loop.**

Your opening is distinctive because it admits an uncomfortable motive and uses humor about the project's scale. The project explicitly asks for your voice. Retain authorship of the personal account, opinions, example selection, and tradeoffs. An assistant can gather source pointers, flag unsupported claims, suggest cuts, or identify confusing terms; it should not invent your experience or substitute polished generic positioning for it.

If the next passage stalls, spend ten minutes speaking or writing an answer to one concrete question: “What happened the last time I used this?” Then extract usable sentences into the draft. This adapts the freewriting and talking-aloud techniques cited above. If you cannot answer because evidence is missing, create one factual question with a source and a stop rule. If you can answer but keep expanding scope, cut back to the selected episode.

A reader check can also remain small: after v1, ask one suitable reader what they think SASE is, why you built it, and where they became confused. Turn those observations into at most three priority revisions. If no reader is available, use the paragraph-summary and audio passes as a fallback. The first draft should not wait for someone else's calendar.

Define completion of the manuscript separately from the surrounding launch work. The text is ready for release preparation when it has a coherent promise, one supported episode, necessary explanations, candid limitations, no unresolved publication-critical markers, and a verified next link. Existing launch prerequisites still apply. Future features and follow-up essays remain outside that completion condition unless the post makes a specific claim that depends on them.

**Evidence and limits of this investigation.**

The primary inputs were the supplied draft and targeted read-only results for `sase_blog.md`: a Dataview task query, `bob capture-tasks --route sase_blog --format json`, and `bob ready sase_blog --format json`. I also consulted the audited Obsidian memory and selected SASE glossary entries to check vault structure and terminology. The six external sources are linked beside the claims they support above. I did not verify all product features, locate a publishable example, recount source lines or commits, audit the full launch dependency graph, or assess the prior reading contents. Those limits are why the plan includes a small evidence step and a later claim-verification pass.

**Recommended strategy.**

Use your existing `sase_blog` project to run one two-session editorial spike, then immediately write one real episode in your own voice. Let that episode select the two or three abstractions that deserve space. Convert only the next few concrete outputs into action tasks; keep the broader route as project support material. Revise the opening after the body exists, retain the current v1 and release milestones, and reuse the future-work and audio-review tasks. Your next work session should end with a chosen reader, promise, and example; the first session after the spike should produce evidence or prose for that example. That gives the post a path to completion without requiring the whole of SASE to be explained first.
