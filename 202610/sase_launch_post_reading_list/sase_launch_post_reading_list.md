# Reading for the SASE Launch Post: Answer the Critique, Join the Debt Vocabulary, Keep the Human at Goal Altitude

> **Research query:** Review the blogs and papers I've read over the last six months in `~/bob/ref/blogs/` and
> `~/bob/ref/papers/`, then find new reading material that will inspire my work on SASE, and the blog post in
> particular, in the right direction. End with a ranked list of articles and papers I should consider reading.

![Infographic "Reading toward a stronger SASE": the six-month reading audit (21 finished external reads, 13 blogs and 8 papers), the keep-the-human-at-goal-altitude model of human, SASE host, and agents, four takeaways (answer the critique, define the debt, protect understanding, bound the swarm claim), Engelbart's bootstrapping test, the top five reading priorities, and "Write first. Read to revise."](sase_launch_post_reading_list_infographic.png)

## Bottom line

1. **Your recent reading built SASE, but it hasn't yet given the post much support.**
   [Twenty-one external blogs and papers](#what-six-months-of-reading-show) were finished in the window, not counting
   CV drafts. Nearly all were finished between 10-03 and 10-23. The heavy reads were about factories and primitives:

   - Anthropic's code-review, source-control, and CI posts
   - OpenAI's harness and Symphony posts
   - the Gas Town manual
   - five memory papers
   - the goals paper

   The post's open slots have almost nothing behind them in the library. Those slots are:

   - the opening
   - AI slop and prompt debt
   - the Gas Town paragraph
   - "loop engineering and graph engineering"
   - "Why a TUI?"
   - "sub-agent doesn't cut it"
   - "the first myth"

   cld, cdx, and grk found this independently.
2. **The right direction is the one in your own margin note.** On Yegge's "stop everything and read what it has to
   say," you wrote: *"This feels wrong! You need to check on goals, not individual agents!"* All five reports converge
   on that note as the post's spine. The direction it sets: the human works at goal altitude, records outlive the
   model, and the host owns completion. The wrong direction is a shinier inner harness, bigger swarms, or more memory
   machinery for its own sake.
3. **One finding changes what the post can claim: "prompt debt" is not a new term.** Aljohani & Do published
   [*PromptDebt*](#the-problem-is-prompt-debt-and-promptdebt) at EASE 2025, and Drew Breunig's *The Problem is Prompt
   Debt* (2026-06-22) was republished on O'Reilly Radar. Your meaning is different from both: alignment that degrades
   in an agent-built codebase. So keep it, but define it against theirs rather than as a coinage. No report flagged
   this as prior art. cld called the term "new," and gem listed *PromptDebt* in a figure without ranking it.
4. **Read the critique before you write the honesty section.** Ronacher's [*Agent Psychosis*](#agent-psychosis) calls
   Gas Town and Beads "the complete celebration of slop loops." A launch post with roughly 16K commits and about one
   user will be read through that lens.
5. **Old human-factors papers give the cockpit argument a lineage, and they are short.** Klein et al.'s
   [*Ten Challenges*](#ten-challenges-for-making-automation-a-team-player) is 5 pages,
   [Bainbridge](#ironies-of-automation) is 5, and [Naur](#programming-as-theory-building) is about 9. Engelbart's
   [*bootstrapping* idea](#engelbart-abc-model-and-bootstrapping-strategy), which none of the reports found, gives
   "SASE's purpose: to build the next SASE" a 60-year-old frame.
6. **Bound the multi-lab swarm claim before you make it.**
   [Kim et al.](#capable-language-models-can-outgrow-the-benefits-of-collaboration) (*Nature Machine Intelligence*,
   2026, peer-reviewed) find that extra agents rarely help once a single agent is already strong. Errors compound
   17.2× with independent agents versus 4.4× with central coordination. Diversity helps (Yang et al.) when each
   reviewer is strong (Song).
7. **None of this should block writing.** Yesterday's writer's-block report counted 450 of 520 blog minutes going to
   reading, and it made the rule "writing never depends on reading." Every item [below](#ranked-reading-list) names
   the *revision* of the section it feeds. Don't wire any of them as a `dependsOn` of a zero-draft task.

**If you read only three (about 45 minutes):** [#1 *Agent Psychosis*](#agent-psychosis),
[#2 Breunig plus Aljohani & Do](#the-problem-is-prompt-debt-and-promptdebt), and
[#3 Klein et al.](#ten-challenges-for-making-automation-a-team-player) **Tomorrow's scheduled read**, Litt's
*Understanding is the new bottleneck*, pairs with [#4](#programming-as-theory-building).

---

## What six months of reading show

All five reports describe the same cohort. `bob ref list -o external -R finished -t blogs,papers -S 2026-04-24`
returns 25 finished records. Four are CV drafts, which leaves 21 external reads: 13 blogs and 8 papers.

The finished reads fall into four clusters:

- **How Anthropic works**
  - *Finished:* *How the Claude Code team does code review*, *Redesigning source control*, *Agentic coding is
    straining CI*
  - *Your annotations show:* You read them for primitives: "Changesets are what 'patches' should be!" and "This
    feels like the problem I was having with mentors." These are product notes, not post notes.
- **Harness and orchestration**
  - *Finished:* OpenAI *Harness engineering*, *Symphony*, the eleven-system *Harness Engineering* paper, *Gas Town
    Emergency User Manual*, *Levels, Ticks and Cascaded Intelligence*, *The Coming Loop*, *The Dot and the Swarm*,
    *Reminders*, netclode
  - *Your annotations show:* You push back wherever a source puts agents ahead of goals.
- **Memory**
  - *Finished:* *The Log is the Agent* ("Support sase tool call replay?"), *Memory OS*, *Human-Inspired Memory*,
    *Filesystem-Based Memory*, *EA-Graph*, Kinney, Karpathy's *llm-wiki*, Diátaxis
  - *Your annotations show:* Kinney's "flat is probably right" and Karpathy's index-first wiki match the decision "No
    Retrieval Mechanism Before Its Corpus."
- **Goals**
  - *Finished:* *Goals as First-Class Abstractions* (your most-annotated paper)
  - *Your annotations show:* "no tool supports goal-guided agent orchestration" → "sase will!", and "Goals should
    always link back to a user prompt!"

Three patterns matter for the post.

- **Comments turn into `#task` items, not sentences.** Your reading feeds the roadmap, not the prose.
- **Almost no personal-voice essays.** Hashimoto's personal ladder is queued for 11-07, and Yegge's *Welcome to Gas
  Town* has been queued since February.
- **Ignore the reading-history timeline in gem's report.** gem drew a "May–June memory phase." Eight of the
  completion dates, including most of the memory papers, were inferred from Git as 10-03. The only June completion is
  Kinney (06-11), so the trajectory gem drew is an artifact of how dates were recovered (cdx's caveat).

---

## Ranked reading list

Ranking criteria, in order:

- whether it changes what the post can honestly claim
- whether it fills an open slot from `sase_blog.md` Requirements
- whether it points SASE in a better direction
- how many researchers converged on it
- reading cost

Every item was opened in this pass or by the report that proposed it, and the claims were checked. Library status
comes from `bob ref find`; "not in library" means only "absent from `ref/`".

### Agent Psychosis

**Rank #1:** *Agent Psychosis: Are We Going Insane?*

- **Armin Ronacher**, 2026-01-18. <https://lucumr.pocoo.org/2026/1/18/agent-psychosis/>
- Not in library. It came up unranked in the 10-10 agentic-SE reading list and was never captured. About 10 minutes.
- **Feeds:** the honesty section (AI slop, prompt debt, limitations) and the stats caveat in the opening.
- **What it says:**
  - Heavy agentic coding becomes a dopamine-driven "slop loop," and maintainers pay the review cost.
  - Gas Town and Beads are "the complete celebration of slop loops."
  - He includes himself in the critique: "They *were* trying to help. Their dæmon told them it was good."
- **Why:** This is the frame an HN reader brings to "~17K commits, ~1 user." Your slop categories, the "What it cost"
  section, gates, and host-owned completion answer it, so write those knowing the question. Decide whether to name it.
- **Limit:** It is a polemic, not evidence about SASE.

### The Problem is Prompt Debt and PromptDebt

**Rank #2:** *The Problem is Prompt Debt*, with *PromptDebt*

- **Drew Breunig**, 2026-06-22, republished on O'Reilly Radar 2026-07-30.
  <https://www.dbreunig.com/2026/06/22/the-problem-is-prompt-debt.html>
- **Ahmed Aljohani & Hyunsook Do**, *PromptDebt: A Comprehensive Study of Technical Debt Across LLM Projects*, EASE
  2025. <https://arxiv.org/abs/2509.20497>
- Neither is in the library. About 15 minutes: Breunig in full, plus the abstract and definition table of Aljohani &
  Do.
- **Feeds:** the "Categories of AI slop" requirement, specifically its prompt-debt bullet.
- **What they say:**
  - **Breunig:** hand-written prompts that serve as a system's durable spec pile up patches and lock the app to one
    model.
  - **Aljohani & Do:** prompt debt is a category of self-admitted technical debt, "debt resulting from poorly
    structured, inefficient, or suboptimal prompts." It accounts for about 6.6% of LLM-specific debt comments across
    93K Python files.
  - **Related:** Sean Goedecke, *Prompts are technical debt too* (2026-05-20), treats `AGENTS.md`, `CLAUDE.md`, and
    skills as debt tied to one model, without using the phrase.
- **Why:** Your definition is "accumulated degradation in alignment due to bad prompting and/or bad code review
  practices." That describes debt in the *codebase the agents produced*, not in the prompt text, and it is distinct
  from both. The post gets stronger if it places your meaning next to theirs instead of claiming the term. SASE also
  answers Breunig's lock-in point directly with multi-provider size aliases and memory that is republished rather than
  hand-edited.
- **Limit:** Breunig is a practitioner essay. Aljohani & Do measured code comments in LLM-calling projects, not
  agent-built repositories.

### Ten Challenges for Making Automation a Team Player

**Rank #3:** *Ten Challenges for Making Automation a "Team Player" in Joint Human-Agent Activity*

- **Klein, Woods, Bradshaw, Hoffman, Feltovich**, *IEEE Intelligent Systems* 19(6), 2004.
  <https://doi.org/10.1109/MIS.2004.74>. cdx read it from a
  [coauthor-hosted PDF](https://www.researchgate.net/profile/David-Woods-19/publication/3454232_Ten_Challenges_for_Making_Automation_a_Team_Player_in_Joint_Human-Agent_Activity/links/0c96052164a74da6ab000000/Ten-Challenges-for-Making-Automation-a-Team-Player-in-Joint-Human-Agent-Activity.pdf).
- Not in library. About 20 minutes; challenges 5, 7, 9, and 10 matter most.
- **Feeds:** §1.1 Gates → Plans → Epics, §1.3.2 agent presentation, and the Gas Town paragraph.
- **What it says:** Joint human-agent work needs a basic compact, mutual predictability, directability, and maintained
  common ground. The challenges include making intentions visible, negotiating goals, and managing attention.
- **Why:** It turns your Gas Town note into design criteria. The test it gives SASE: can the person understand and
  redirect the work without watching each action? The "goals, not agents" stance then reads as twenty years of
  engineering lineage rather than taste. It is the strongest addition from cdx.
- **Limit:** A pre-LLM conceptual framework. It gives criteria, not evidence that SASE meets them.

### Programming as Theory Building

**Rank #4:** *Programming as Theory Building*, with *Programming (with AI agents) as theory building*

- **Peter Naur**, 1985, about 9 pages. <https://pages.cs.wisc.edu/~remzi/Naur.pdf>
  ([readable transcription](https://pablo.rauzy.name/dev/naur1985programming.pdf))
- **Sean Goedecke**, 2026-04-03. <https://www.seangoedecke.com/programming-with-ai-agents-as-theory-building>
- Neither is in the library. About 35 minutes.
- **Feeds:** §1.3.1 memory, plus two slop categories in the honesty section: unnecessary backward compatibility and
  duplicated functionality.
- **What they say:**
  - **Naur:** a program is a theory held by the people who can explain and change it. Text and documentation can't
    fully carry that theory, so reviving a program from them alone fails.
  - **Goedecke:** agents can build a working theory of a codebase but can't keep it between sessions.
- **Why:** This is the cleanest argument for *why* SASE has memory, goals, plans as artifacts, and decision records.
  It also states their limit: they help a successor (human or agent) rebuild the theory, but they don't store it for
  you. That keeps the post from implying SASE "remembers for you." Three researchers converged on Naur.
- **Companions:**
  - Litt, [queued for tomorrow](#pull-these-forward-from-your-library).
  - Ronacher, [*The Tower Keeps Rising*](https://lucumr.pocoo.org/2026/7/13/the-tower-keeps-rising/) (2026-07-13): agents
    remove the friction that kept people's mental models in sync.
  - Answer.AI, [*Why LLMs can't make your code simpler*](https://answer.ai/posts/2026-08-19-llms-code-simpler.html)
    (2026-08-19).
- **Limit:** Naur is philosophy. Don't cite him as proof that machines can't understand programs.

### Engelbart ABC Model and Bootstrapping Strategy

**Rank #5:** Engelbart's ABC model and bootstrapping strategy

- **Doug Engelbart Institute** pages:
  - [*ABC Model*](https://www.dougengelbart.org/about/abc-model.html)
  - [*Bootstrapping Strategy*](https://www.dougengelbart.org/about/bootstrapping-strategy.html)
- **Primary source:** Engelbart, *Toward High-Performance Organizations: A Strategic Role for Groupware* (GroupWare
  '92). Read §3, "The ABC Model of Organizational Improvement," and §10, "C Community: High-Payoff Bootstrapping
  Opportunity." The old `dougengelbart.org/pubs/augment-132811.html` URL now redirects to
  `dougengelbart.org/content/view/116/`.
- Not in library. About 25 minutes. **My addition; no researcher found it.**
- **Feeds:** the requirement "SASE's purpose: To build the next SASE from scratch (the first 'myth')." Possibly the
  closing too.
- **What it says:**
  - **A** is the core work, **B** is improving how A gets done, and **C** is "improving how B work is done, asking
    'How can we improve the way we improve?'"
  - Bootstrapping means "use what you build to boost your own effectiveness": getting better at getting better.
- **Why:** SASE is built by SASE agents. Agents improving SASE is B work. The memory, decision records, research
  swarms, and macros that make *the next* improvement cheaper are C work. That gives the myth a lineage and a
  falsifiable test: does a SASE improvement make the next one cheaper? It is also the strongest answer to
  [*Agent Psychosis*](#agent-psychosis). Bootstrapping is a deliberate strategy rather than a slop loop, *if* you can
  show the C-level payoff.
- **Tension to keep in view:** Brooks's second-system effect and "plan to throw one away" (*The Mythical Man-Month*,
  chapters 5 and 11, from cld). Bootstrapping is the blessing, Brooks is the warning, and both apply to a project that
  plans its own rewrite.
- **Limit:** Organizational theory from the groupware era, with no evidence about agents.

### Cognitive Debt and The Intent Debt

**Rank #6:** *Cognitive Debt*, with *The Intent Debt*

- **Margaret-Anne Storey**, *How Generative and Agentic AI Shift Concern from Technical Debt to Cognitive Debt*,
  2026-02-09. <https://margaretstorey.com/blog/2026/02/09/cognitive-debt/>
- **Addy Osmani**, *The Intent Debt*, 2026-06-05. <https://addyosmani.com/blog/intent-debt/>
- Neither is in the library. Storey's paper version appeared in the 10-10 list and was never captured. About 20
  minutes.
- **Feeds:** the honesty section and the memory paragraph.
- **What they say:**
  - **Storey:** technical debt lives in code, and cognitive debt lives in people.
  - **Osmani:** intent debt lives in missing artifacts such as goals, constraints, and rationale. "An agent can't
    generate intent, because intent is the one input that has to come from you."
- **Why:** With [#2](#the-problem-is-prompt-debt-and-promptdebt), these give your prompt debt a family that readers
  already know. SASE pays intent debt in ways the post can show:

  - goals that link back to the originating prompt
  - plans stored as artifacts and read by later agents
  - immutable decision records with `superseded_by`
  - gated memory writes
- **Limit:** These are essays, and Storey's evidence is a classroom anecdote.

### Fences not Sandboxes and Appleton on Gas Town

**Rank #7:** *Fences, not Sandboxes*, with Appleton on Gas Town

- **Steve Yegge**, 2026-08-24. <https://yegge.ai/essays/fences-not-sandboxes/>
- **Maggie Appleton**, *Gas Town's Agent Patterns, Design Bottlenecks, and Vibecoding at Scale*, January 2026.
  <https://maggieappleton.com/gastown>
- Neither is in the library. About 45 minutes.
- **Feeds:** the Gas Town paragraph, the high-priority "analogous crazy term" task, and §1.1.
- **What they say:**
  - **Yegge:** a factory of about 50–60 agents grew a legal system: a constitution, jurisprudence, and courts, with
    about 450 legal artifacts. Rules climb a ladder: custom, then advisories, then written law, then "mechanical
    enforcement: programs that refuse by policy."
  - **Appleton:** design becomes the bottleneck when agents write everything. She also extracts the orchestration
    patterns under the chaos and gives a guide to when you can stop looking at code.
- **Why:** Yegge's ladder now looks like SASE's: memory notes, then immutable decision records, then guarded recipes
  and Symvision refusals. That convergence makes the Gas Town paragraph generous and current rather than a critique of
  January's manual. Appleton is the critique readers will carry.
- **One-line companion:** Ronacher, [*Latent Powers*](https://lucumr.pocoo.org/2026/9/5/latent-powers/) (2026-09-05).
  He *wonders whether* models steer people toward the same projects, which could explain the convergence without
  "they copied me." cld stated this too strongly. Ronacher leaves it as an open question.
- **Limit:** Yegge's numbers are self-reported. Stop after these two
  ([grk's warning stands](#where-they-split-and-how-i-resolved-it)).

### Ironies of Automation

**Rank #8:** *Ironies of Automation*

- **Lisanne Bainbridge**, *Automatica* 19(6), 1983, 5 pages.
  <https://gwern.net/doc/sociology/technology/1983-bainbridge.pdf>
- Not in library. About 15 minutes.
- **Feeds:** the honesty section, "Why a TUI?", and gates.
- **What it says:** Automating the routine leaves the operator with the hardest leftover tasks, while monitoring
  wears away the skills those tasks need.
- **Why:** It names why "read every finished agent" is the wrong leftover job. It also names the risk SASE carries: if
  plan approval becomes a rubber stamp, you lose the competence the gate depends on. Your mentor-noise note on the
  code-review post is a Bainbridge observation.
- **2026 restatements:**
  - Mitchell, Ghosh, Passi, [*AI Agents Push Humans Out of the Loop*](https://arxiv.org/abs/2608.23642), a position
    paper.
  - Shen & Tamkin, [*How AI Impacts Skill Formation*](https://arxiv.org/abs/2601.20245), a randomized study finding
    weaker learning with AI help.
- **Limit:** Industrial-process examples, and it overlaps with [#3](#ten-challenges-for-making-automation-a-team-player).

### Capable language models can outgrow the benefits of collaboration

**Rank #9:** *Capable language models can outgrow the benefits of collaboration*, with the diversity pair

- **Yubin Kim et al.**, *Nature Machine Intelligence* 8, 1157–1172, 2026-07-24.
  <https://www.nature.com/articles/s42256-026-01268-y>. Preprint: *Towards a Science of Scaling Agent Systems*,
  <https://arxiv.org/abs/2512.08296>.
- **Yang et al.**, *Understanding Agent Scaling in LLM-Based Multi-Agent Systems via Diversity*,
  <https://arxiv.org/abs/2602.03794>.
- **Tae-Eun Song**, *When Does a Second Model Help? Cross-Model Review in LLM Verification*,
  <https://arxiv.org/abs/2610.01471>.
- None are in the library. About 50 minutes: Kim's results and limitations, plus the other two abstracts.
- **Feeds:** wherever the "different frontier models from competing labs" quote lands, the research-swarm anecdote,
  and §1.5 forks and waits.
- **What they say:**
  - **Kim et al.** tested 260 configurations. How well one agent does alone best predicts whether adding agents
    helps; above roughly 45% single-agent performance, extra agents rarely help. Errors compound 17.2× with
    independent agents versus 4.4× with centralized coordination. Results range from +80.8% to −70.0%, and
    cross-domain prediction is poor.
  - **Yang et al.:** two diverse agents can match or beat sixteen identical ones.
  - **Song:** one same-model review plus one cross-model review caught 56.7% of planted errors, versus 42.7% for two
    same-model reviews. It did not beat two strong cross-model reviews.
- **Why:** Your swarm quote holds up only with bounds. Diversity helps when each member is strong. Fan-out is a
  per-task choice, not a default. Central, host-owned coordination is what keeps errors from compounding. That
  supports the decision that every size alias spans more than one provider, and warns against claiming that a cheap
  second model is enough.
- **Limit:** These are benchmarks. Don't hard-code the thresholds.

### The Vocabulary Readers Already Have

**Rank #10:** The vocabulary readers already have: loops, harnesses, autonomy levels

- **Addy Osmani**, *Loop Engineering*, 2026-06-07. <https://addyosmani.com/blog/loop-engineering/>
- **Birgitta Böckeler**, *Harness engineering for coding agent users*, martinfowler.com, 2026-04-02.
  <https://martinfowler.com/articles/harness-engineering.html>
- **Addy Osmani**, *Agentic Autonomy Levels*, 2026-07-02. <https://addyosmani.com/blog/agentic-autonomy-levels/>
- **Optional evidence:**
  - Macedo, [arXiv 2607.00038](https://arxiv.org/abs/2607.00038)
  - Feng et al., [*Graph Engineering in the Era of LLM Agents*](https://arxiv.org/abs/2608.21156)
- None are in the library. About 40 minutes.
- **Feeds:** the requirement "Mention loop engineering and graph engineering," the overview, the timeline
  infographic, and the personal ladder in the intro.
- **What they say:**
  - **Osmani, *Loop Engineering*:** names the June 2026 shift from prompting agents to designing the loops that
    prompt them.
  - **Böckeler:** the user's harness is feedforward guides plus feedback sensors.
  - **Osmani, *Autonomy Levels*:** splits autonomy into *agency* and *orchestration*, and names the anti-pattern
    "summary substitution," where an agent's summary stands in for review. That is what you objected to in Gas Town.
  - **Macedo:** in 50 hand-coded public loops, 70% verify autonomously and 74% name their terminal states. Automated
    triggers and durable memory are the least developed parts.
  - **Feng et al.:** list prompt, context, harness, loop, and graph as successive areas of focus.
- **Why:** Readers have this vocabulary. SASE can be placed in it in one move:

  - routines and jobs are the triggers
  - gates, monitors, and `just check` are verification and stopping
  - goals and memory are the rest

  Macedo's weakest parts are SASE's strongest. Böckeler lets you say SASE sits *above* the harness, and Osmani's two
  axes describe your ladder: you climbed the orchestration axis while gates kept per-agent agency bounded.
- **Limit:** These pieces are independent of one another. Osmani doesn't cite Macedo, and Feng's ordering is implied
  by a list, not presented as a pipeline.

### Interpreting Pangram

**Rank #11:** *Interpreting Pangram*

- **Armin Ronacher**, 2026-09-14. <https://lucumr.pocoo.org/2026/9/14/interpreting-pangram/>
- Not in library. 5 minutes.
- **Feeds:** process, not a section.
- **What it says:** He rewrote text by hand on top of a structure an LLM produced, and it still scored "100% slop."
  The structure survived the edits.
- **Why:** Your outline, intro proposals, and wave plan all came from agent swarms, and so does this report. Use
  agents for facts and media. You own the claim sentences and the order of sections. That is why the "Feeds" lines
  here are an index, not an outline.
- **Limit:** One anecdote about one detector.

### Humans are Missing from AI Coding Agent Research

**Rank #12:** *Humans are Missing from AI Coding Agent Research*

- **Zora Z. Wang, John Yang, Kilian Lieret, … Graham Neubig, Daniel Fried, Diyi Yang**, arXiv 2608.12355, v1
  2026-07-04. <https://arxiv.org/abs/2608.12355>
- Not in library. About 20 minutes.
- **Feeds:** §1.3.2 agent presentation, and "SASE does not claim optimal performance, but optimal experience!"
- **What it says:** As agents improve, the bottleneck moves to how people work with them, along four dimensions: task
  alignment, verifiability, steerability, and adaptability.
- **Why:** The authors include SWE-bench and SWE-agent researchers, so it gives "optimal experience" a research basis
  rather than resting on taste. The four dimensions map cleanly onto SASE:

  - alignment: goals and plans
  - verifiability: gates and receipts
  - steerability: `%wait`, `#fork`, and questions
  - adaptability: memory
- **Limit:** A position paper.

### Two Terminal-First Essays

**Rank #13:** Two terminal-first essays: Zechner's pi post and *Just Talk To It*

- **Mario Zechner**, *What I learned building an opinionated and minimal coding agent*, 2025-11-30.
  <https://mariozechner.at/posts/2025-11-30-pi-coding-agent/>
- **Peter Steinberger**, *Just Talk To It – the no-bs Way of Agentic Engineering*, 2025-10-14.
  <https://steipete.me/posts/just-talk-to-it>
- Neither is in the library. About 30 minutes. **My addition.**
- **Feeds:** "Why a TUI?" and "The term 'sub-agent' doesn't cut it."
- **What they say:**
  - **Zechner:** coding agents are mostly linear chat, so a terminal UI "makes the most sense." Sub-agents are
    opaque and pass context poorly.
  - **Steinberger:** runs "3-8 in parallel in a 3x3 terminal grid," and says "What others do with subagents, I
    usually do with separate windows."
- **Why:** These are the only two non-vendor, terminal-first essays I found. Both doubt sub-agents, which opens room
  for SASE's named relations: forks, tribes, clans, and hoods. Steinberger's grid is the hand-built cockpit that SASE
  turns into a system. I found no serious essay proposing a better word than "sub-agent," so that argument would be
  your own. Ronacher's *Clanker* addresses the word "agent," not hierarchy.
- **Counterpoint to answer:** elianiva,
  [*TUI is the wrong abstraction for coding agents*](https://elianiva.com/posts/tui-is-the-wrong-abstraction-for-coding-agents/)
  (2026-10-03).
- **Limit:** Each describes one practitioner's setup.

### We mourn our craft and An app can be a home-cooked meal

**Rank #14:** *We mourn our craft*, with *An app can be a home-cooked meal*

- **Nolan Lawson**, 2026-02-07. <https://nolanlawson.com/2026/02/07/we-mourn-our-craft/>
- **Robin Sloan**, 2020. <https://www.robinsloan.com/notes/home-cooked-app/>
- Neither is in `ref/`, though you may have read Sloan elsewhere. About 15 minutes.
- **Feeds:** the opening (pride, "my attempt to take back some control," "~1 user").
- **Why:**
  - **Lawson** states the grief half of the moment, and your opening is the agency half.
  - **Sloan** turns "~1 user" from a joke into a position: a home-cooked meta-harness tuned for one engineer's
    experience. It also gives [*Agent Psychosis*](#agent-psychosis) an honest answer, since SASE isn't pretending to
    be a platform.
- **Limit:** Mood pieces. They earn a sentence, not a section.

### How a Cockpit Remembers Its Speeds

**Rank #15 (optional):** *How a Cockpit Remembers Its Speeds*

- **Edwin Hutchins**, *Cognitive Science* 19, 1995. <https://www.ida.liu.se/~729G12/mtrl/cockpit.pdf>
- Not in library. About 45 minutes.
- **Feeds:** the control-tower framing and "the scrollback buffer is the database."
- **What it says:** The unit of analysis is the cockpit as a system. Speed bugs, cards, and callouts hold memory that
  no single pilot holds.
- **Why:** The post already talks in cockpit language, and Hutchins supplies the vivid concrete case. It is grk's #1.
  I rank it last only because [#3](#ten-challenges-for-making-automation-a-team-player) and
  [#4](#programming-as-theory-building) carry the same argument in a third of the time.
- **Limit:** Aviation, not software.

---

## Pull these forward from your library

These items are already in your library:

- **Litt, _Understanding is the new bottleneck_**
  - *State:* Queued, high priority, scheduled 10-25
  - *Why now:* Pairs with [#4](#programming-as-theory-building). It gives SASE's artifacts a human purpose: you should
    come out of an agent-assisted change better able to propose the next one.
- **Hassan et al., _Agentic Software Engineering_ (arXiv 2509.06216)**
  - *State:* Queued, high priority, parent `sase_blog`, scheduled 10-19, **overdue**
  - *Why now:* The paper SASE takes its name from (ACE/AEE). It feeds footnote `[1]` (name). It is also the one ref
    already in the `sase_blog` Ready lane.
- **_Introducing Omnigent_ (Databricks)**
  - *State:* Queued, high priority, scheduled 10-25
  - *Why now:* Footnote `[2]` depends on it. Finish it or mark it read.
- **_Reality Is the Final Verifier_ (Krentsel … Zaharia, Stoica)**
  - *State:* Queued, scheduled 11-07
  - *Why now:* Separates a requirement gap from a model gap. Pull it forward only if "vibe evals" stays in the post.
- **Hashimoto, _My AI Adoption Journey_**
  - *State:* Queued, scheduled 11-07
  - *Why now:* The model for a personal-ladder post. Read it before Intro v1, which you write last.
- **Jesse Vincent, [_Superpowers_](https://blog.fsck.com/2025/10/09/superpowers/)**
  - *State:* Started (legacy)
  - *Why now:* The best genre model: an honest one-person framework launch told as "how I work now." **My addition.**
- **Anthropic, [_Scaling Managed Agents: Decoupling the brain from the hands_](https://www.anthropic.com/engineering/managed-agents)**
  - *State:* Queued (legacy, since 04-17)
  - *Why now:* The session is a durable event log outside the harness, and "the harness also became cattle." This is
    the closest vendor echo of "Agents Are Single-Turn" plus host-owned state. **My addition.**
- **_12 Factor Agents_ (HumanLayer)**
  - *State:* Queued (legacy, since 04-27)
  - *Why now:* Factor 12 ("stateless reducer") resembles single-turn agents, and factors 6–7 resemble gates. It backs
    your "plan mode is a special case of a deeper primitive" note.
- **Yegge, _Welcome to Gas Town_**
  - *State:* Queued (legacy, since 02-11)
  - *Why now:* Read only if you want Yegge's own launch-post genre. *Superpowers* matches your scale better.

---

## Capture commands (proposed, not run)

```bash
bob ref create https://lucumr.pocoo.org/2026/1/18/agent-psychosis/ -L
bob ref create https://www.dbreunig.com/2026/06/22/the-problem-is-prompt-debt.html -L
bob ref create https://arxiv.org/abs/2509.20497
bob ref create https://doi.org/10.1109/MIS.2004.74 -L
bob ref create https://pages.cs.wisc.edu/~remzi/Naur.pdf -L
bob ref create https://www.seangoedecke.com/programming-with-ai-agents-as-theory-building -L
bob ref create https://www.dougengelbart.org/about/abc-model.html
bob ref create https://www.dougengelbart.org/about/bootstrapping-strategy.html
bob ref create https://margaretstorey.com/blog/2026/02/09/cognitive-debt/ -L
bob ref create https://addyosmani.com/blog/intent-debt/ -L
bob ref create https://yegge.ai/essays/fences-not-sandboxes/ -L
bob ref create https://maggieappleton.com/gastown -L
bob ref create https://gwern.net/doc/sociology/technology/1983-bainbridge.pdf -L
bob ref create https://www.nature.com/articles/s42256-026-01268-y -L
bob ref create https://arxiv.org/abs/2602.03794
bob ref create https://arxiv.org/abs/2610.01471
bob ref create https://addyosmani.com/blog/loop-engineering/
bob ref create https://martinfowler.com/articles/harness-engineering.html
bob ref create https://addyosmani.com/blog/agentic-autonomy-levels/
bob ref create https://lucumr.pocoo.org/2026/9/14/interpreting-pangram/
bob ref create https://arxiv.org/abs/2608.12355
bob ref create https://mariozechner.at/posts/2025-11-30-pi-coding-agent/ -L
bob ref create https://steipete.me/posts/just-talk-to-it
bob ref create https://nolanlawson.com/2026/02/07/we-mourn-our-craft/ -L
bob ref create https://www.robinsloan.com/notes/home-cooked-app/
bob ref create https://www.ida.liu.se/~729G12/mtrl/cockpit.pdf
```

Attach these to `sase_blog` refs only as blockers of each section's **revise** task, never of a zero draft.

---

## Reading for SASE itself

These are worth reading while you build. They point SASE in a direction; they are not post material.

1. **[LongHorizon-Harness](https://arxiv.org/abs/2608.01964)** (Ma et al., 2026-08-03).

   - Task state lives outside execution and is updated only with facts the environment confirms.
   - A Manage–Execute–Audit loop uses a fresh-context executor and a read-only auditor.
   - `AgentAdapter` wraps native loops *without modifying them*.
   - Results: Qwen 3.7-Plus 51.8% → 80.7% on WeaveBench, and Terminal-Bench 2.1 69.7% → 77.2%.
   - This is empirical support for host-owned state and for wrapping CLIs rather than replacing them. Preprint.
2. **[*When Sub-Agents Work in Parallel*](https://arxiv.org/abs/2610.10263)** (Li et al., 2026-10-07).

   - Matched Codex, Claude Code, and Kimi runs: 354 tasks, 2,124 executions.
   - The model decides short tasks, and orchestration decides long ones.
   - It identifies 13 concurrency failure modes. Check them against clans, `%wait`, and launch approval.
3. **[MAST, *Why Do Multi-Agent LLM Systems Fail?*](https://arxiv.org/abs/2503.13657)** (Cemri et al., v3).

   - 14 failure modes in 3 groups: system design, inter-agent misalignment, and task verification.
   - Use it to classify real SASE incidents (from cdx).
4. **[Code-review agents in PRs](https://arxiv.org/abs/2604.03196)** (Chowdhury et al., MSR 2026).

   - PRs reviewed only by code-review agents merge 45.2% of the time, versus 68.4% for human-reviewed PRs.
   - 60.2% of *closed* agent-only PRs sit in the 0–30% signal band.
   - This is evidence for your mentor-noise note. gem misstated the 60.2% as a share of comments.
5. **[Wang & Liu, *Software Engineering in the Agent Era*](https://arxiv.org/abs/2609.04630)** (2026-09-04).

   - "Execution grants no acceptance authority."
   - This is "Completion Is Host-Owned" stated as SE theory (from cld).
6. **[Saltzer, Reed, Clark, *End-to-End Arguments*](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf)**
   (1984).

   - Explains where a postcondition has to be checked.
   - Use it to separate receipts from replay: replay reconstructs evidence, it doesn't prove a fresh action is safe
     (from cdx).
7. **[TDAD](https://arxiv.org/abs/2603.17973)** (Alonso et al., 2026-03).

   - A graph-based test map cut test-level regressions from 6.08% to 1.82% with the full tool.
   - Prompting for TDD alone made regressions worse (9.94%).
   - The lightweight skill version raised issue resolution from 24% to 32%. Samples were small.
   - A cheap idea for SASE skills and `just check`.
8. **Instruction-file evidence**, for `sase_memory_plan` and the later memory post:

   - Gao & Chen, *From Agent Behaviour to Agent-Friendly Documentation* (queued under `sase_memory_plan`). Instruction
     files and working notes make up 60.5% of doc interactions.
   - *Agent READMEs* (queued, legacy).
   - Koniukhova,
     [*When Coding Agent Guides Help, Hurt, or Do Nothing*](https://dev.to/yahhi/when-coding-agent-guides-help-hurt-or-do-nothing-28op).
     Anecdotal. A guide that retells the docs changed nothing; one undocumented fact flipped a single task.
   - Remy's [memory-layer survey](https://redreamality.com/blog/agent-memory-layer-survey-2026-decision-framework/).
     A personal blog: four memory jobs, files as source of truth.
9. **Supervision models:**

   - Sheridan, [*Automation*](https://www.hfes.org/Portals/0/Documents/Sheridan.pdf), 2 pages. Supervision is planning,
     programming, monitoring, diagnosing, intervening, and learning.
   - Park et al., [*The Work Behind Delegation*](https://arxiv.org/abs/2609.24234). Reworks Sheridan's model into seven
     stages for coding agents. It appeared in an earlier SASE list.
10. **Gas City, [*Extending Beads*](https://blog.gascity.com/posts/extending-beads-memories-versions-and-the-wire-protocol/)**
    (Donna Box, 2026-10-01).

    - Memory Beads separated from issues, plus versions so a PR can cite the exact policy version it followed.
    - Still a preview on an integration branch.

**Lower priority:**

- For the beads-and-SDD post: Díaz et al., [*Spec-Driven Development for Agentic Software
  Engineering*](https://arxiv.org/abs/2609.00252), with five human-agent interaction patterns. Pair it with
  Böckeler's SDD article, which you've already started.
- Panozzo,
  [*Avoid Losing Work with Jujutsu (jj) for AI Coding Agents*](https://www.panozzaj.com/blog/2025/11/22/avoid-losing-work-with-jujutsu-jj-for-ai-coding-agents/),
  for workspace safety. This is the corrected URL.
- Stripe, *Minions* Part 2 (queued). Blueprints mixing deterministic steps with agent loops.
- Temporal, [*Durable, flexible multi-agent systems*](https://temporal.io/blog/durable-flexible-multi-agent-systems).
  Vendor dev-rel, but its line "Temporal isn't replacing your framework. It's the layer underneath it" is exactly
  SASE's positioning.

**Research-inspired directions (suggestions, not existing features):**

- **Completion artifacts that explain.** A completion artifact should state the purpose and governing assumptions of a
  change, not only keep the transcript (Naur, Litt, Storey).
- **Notifications measured by decisions.** Measure the share of notifications that lead to a useful decision, and the
  minutes it takes to reconstruct a paused goal (Klein, Bainbridge; cdx's proposed metrics).
- **A C-level metric.** Does each SASE improvement make the next one cheaper? (Engelbart)
- **Fan-out as a per-task decision**, bounded by evidence (Kim et al.).

---

## Where the reports agreed and split

### Where they agreed

Agreement is unusually broad, considering the five reports were independent:

- **Naur, _Programming as Theory Building_**
  - *Who ranked it:* cdx #5, grk #3, cld (companion to #15)
  - *Status:* Not in library; [#4 in the ranked list](#programming-as-theory-building)
- **Bainbridge, _Ironies of Automation_**
  - *Who ranked it:* cdx #11, grk #2
  - *Status:* Not in library; [#8 in the ranked list](#ironies-of-automation)
- **_Reality Is the Final Verifier_**
  - *Who ranked it:* cdx #3, mus #2, grk (pull-forward)
  - *Status:* Queued for 11-07
- **Litt, _Understanding is the new bottleneck_**
  - *Who ranked it:* cdx #2, grk and cld (pull-forward)
  - *Status:* Queued for 10-25
- **Hassan et al., the paper SASE takes its name from**
  - *Who ranked it:* cld and grk (finish first)
  - *Status:* Queued and overdue since 10-19
- **Appleton on Gas Town**
  - *Who ranked it:* mus #3, cld (unranked)
  - *Status:* Not in library; companion to [#7](#fences-not-sandboxes-and-appleton-on-gas-town)
- **Model diversity for swarms**
  - *Who ranked it:* cld #11, gem #11
  - *Status:* Not in library; [#9 in the ranked list](#capable-language-models-can-outgrow-the-benefits-of-collaboration)
    (gem's version corrected)

### Where they split and how I resolved it

- **Read more Gas Town?**
  - *Positions:* grk: stop, since more Yegge pulls the post toward swarm ops. cld: *Fences, not Sandboxes* at #3 and
    *Extending Beads* at #12. mus: Appleton at #3.
  - *Resolution:* **Read exactly two pieces, then stop.** The post has a Gas Town paragraph and a high-priority task
    to "link to the analogous crazy term used by GasTown," scheduled for today. Your comparison is anchored on
    January's manual, and Yegge has moved since then. Read
    [*Fences* and Appleton](#fences-not-sandboxes-and-appleton-on-gas-town). *Extending Beads* goes to the SASE
    engineering tier ([Reading for SASE itself](#reading-for-sase-itself)).
- **Memory and instruction-file evidence**
  - *Positions:* mus: five of its ten picks. grk and cdx: the launch post shouldn't become a memory paper.
  - *Resolution:* **Memory gets one sub-heading in your outline (§1.3.1),** so one paragraph. mus's set feeds
    `sase_memory_plan` and the later memory post (`whats-next-memory-mobile-web.md`). It is in
    [Reading for SASE itself](#reading-for-sase-itself), not the main list.
- **VCS and review infrastructure**
  - *Positions:* gem: jj, Sapling, TDAD, code-review empirics. cdx: resist turning reading into infrastructure
    expansion.
  - *Resolution:* **Roadmap, not post.** The well-evidenced items are in
    [Reading for SASE itself](#reading-for-sase-itself) with corrections.
- **Is "prompt debt" original?**
  - *Positions:* cld: "your best original term… That is new." gem: listed *PromptDebt* in a taxonomy figure but
    didn't rank it.
  - *Resolution:* **Prior art exists** (verified). It is now
    [#2 in the ranked list](#the-problem-is-prompt-debt-and-promptdebt).
- **Which human-factors classics?**
  - *Positions:* grk: Hutchins, Bainbridge, Parasuraman, Endsley. cdx: Klein, Bainbridge, *Ironies of Generative AI*,
    End-to-End.
  - *Resolution:* **Klein + Naur + Bainbridge**, which together run about 20 pages and directly address goals,
    understanding, and leftover human work. Hutchins is optional ([#15](#how-a-cockpit-remembers-its-speeds)).
    Parasuraman, Endsley, and *Ironies of GenAI* drop to "if you want more."
- **Reopen _What Does a Harness Buy?_**
  - *Positions:* mus: yes, to get a cost number for "What it cost." You dropped it on 10-10.
  - *Resolution:* **Only if that section needs one number.** Not ranked.
- **How to use the reading**
  - *Positions:* cdx: one completed story plus one failure story. cld: a slot map. grk: finish the namesake paper
    first.
  - *Resolution:* **Use the reading after the zero drafts, not before them.** This follows yesterday's wave plan.
    Treat the "Feeds" lines in the [ranked list](#ranked-reading-list) as an index, not an outline (see
    [#11](#interpreting-pangram)).

---

## Considered and dropped

- **Karpathy, *Software 3.0*** (grk #7). Well known. Its autonomy slider is covered by Osmani's two axes
  ([#10](#the-vocabulary-readers-already-have)).
- **Parasuraman, Sheridan & Wickens (2000); Endsley (1995)** (grk #10–11). Good, but
  [#3](#ten-challenges-for-making-automation-a-team-player) and [#8](#ironies-of-automation) carry the argument for the
  post. Read them if a later "gates" post needs a taxonomy.
- **METR time horizons** (grk #12). Known. It is a "why now" sentence, not a read.
- **Cursor, *Continually improving our agent harness*** (grk #9). Context on a competitor. Know that its closing claim
  ("will live in the harness") is the bet SASE declines.
- **Willison, *Embracing the parallel coding agent lifestyle*** (grk #5). Steinberger
  ([#13](#two-terminal-first-essays)) covers the window farm more vividly.
- ***Ironies of Generative AI*** (cdx #7). Overlaps with Bainbridge plus Shen & Tamkin.
- ***What Does a Harness Buy?*** (mus #9). You dropped it. Reopen it only if "What it cost" needs one cost number.
- **Mergify, ToFu, the AlphaSignal Codex-CLI digest, *AI-to-AI Code Reviews*, *Scientific Agent Skills*, Sapling,
  Hydari's AgTD papers, SDAD, X-MAS.** Each is vendor data, secondary, unevaluated, roadmap-only, or (X-MAS)
  misdescribed.

---

## Corrections to the individual reports

My verification pass found these errors. Fix them before reusing any of this material.

- **gem #11**
  - *Claim:* X-MAS pairs "Claude for architectural synthesis, Codex for syntax, Gemini for multi-modal"
  - *Verified:* **Invented.** X-MAS (Ye et al., 2025) tests 27 *open-weight* models, and Claude and Codex never
    appear. Its authors were given only as a "research group."
- **gem #9**
  - *Claim:* SDAD authors are a "Software Engineering Research Group"
  - *Verified:* Vu Hung Nguyen and Thanh Nguyen. A conceptual paper with no evaluation.
- **gem #3**
  - *Claim:* "60.2% of CRA review comments" are low-signal
  - *Verified:* 60.2% of *closed CRA-only PRs* (n=98). 12 of 13 agents averaged below 60% signal.
- **gem #5**
  - *Claim:* The `test_map.txt` skill cut regressions 70%, to 1.82%
  - *Verified:* That figure is the full GraphRAG+TDD tool (Phase 1). The skill deployment raised resolution from 24%
    to 32%.
- **gem #4**
  - *Claim:* Panozzo URL
  - *Verified:* Returns 404; the corrected URL is in [Reading for SASE itself](#reading-for-sase-itself).
- **gem #1, #2, #6**
  - *Claim:* "productivity-reliability paradox"; "AgTD" credited to Hydari; a TechRxiv skills companion paper
  - *Verified:* The paper says "productivity paradox." "AgTD" comes from Tukur et al. The companion paper could not
    be found.
- **gem §2**
  - *Claim:* A "May–June memory phase" in the reading timeline
  - *Verified:* The completion dates were inferred from Git as 10-03; the only June completion is Kinney.
- **mus #6**
  - *Claim:* "State of Merge Queues 2026"; "~6% of PRs batched"
  - *Verified:* The post is titled *AI-assisted PRs break main half as often as human ones* (1.9% vs 4.4%). The ~6% is
    derived, and covers private merges only.
- **mus #5**
  - *Claim:* Yahhi, 2026-10-22; guides "flip hard tasks" 3/8 → 16/16
  - *Verified:* Author is Valentina Koniukhova, posted 10-21. The flip happened on *one* task, and guides also hurt
    (agents broke a working API).
- **grk #6**
  - *Claim:* Temporal quote
  - *Verified:* It continues: "…correctly, for as long as it takes." This is vendor dev-rel.
- **grk #9**
  - *Claim:* Cursor uses sub-agents to switch models
  - *Verified:* Sub-agents *sidestep* switching models mid-conversation.
- **grk #12**
  - *Claim:* METR "Long Tasks" v4
  - *Verified:* The title is now *…Long **Software** Tasks*. v4 only adds an author; the doubling time is still about
    7 months.
- **cld (bottom line)**
  - *Claim:* "Prompt debt" is new
  - *Verified:* Prior art exists: Aljohani & Do (2025) and Breunig (2026). See
    [#2](#the-problem-is-prompt-debt-and-promptdebt).
- **cld #5**
  - *Claim:* *Latent Powers*: "models nudge everyone"
  - *Verified:* Ronacher *wonders whether* they do and leaves it open.
- **cld #14**
  - *Claim:* The Human-Agent Cell "holds no acceptance authority"
  - *Verified:* The actual wording is "execution grants no acceptance authority."
- **cld #6**
  - *Claim:* Osmani → Macedo → graph survey as one lineage
  - *Verified:* They are independent pieces, and the graph ordering is implied.

Spot checks of cdx (Kim et al., *Reality Is the Final Verifier*, Klein) found no errors.

---

## Method and limits

**Lead researcher's consolidated report** · 2026-10-24 · merges five independent reports
([`__cdx`](sase_launch_post_reading_list__cdx.md), [`__cld`](sase_launch_post_reading_list__cld.md),
[`__grk`](sase_launch_post_reading_list__grk.md), [`__mus`](sase_launch_post_reading_list__mus.md),
[`__gem`](sase_launch_post_reading_list__gem.md)). I added four fact-check sweeps covering about 60 cited sources, two
batched library lookups (87 queries), a gap search, and a check of the post's current state.

> **Research question.** Review my references in `~/bob/ref/blogs/` and `~/bob/ref/papers/` from the last six
> months. Then find new reading that will inspire my work on SASE, and the blog post in particular, in the right
> direction. End with a ranked list of articles and papers.

- **Inputs.** I read the five reports through `sase artifact read` (not transcripts). For blog context I also read:

  - yesterday's writer's-block final report
  - the current `sase_blog_contents.md` (274 words, ten `TODO` headings)
  - the Requirements lines in `sase_blog.md`
- **Verification.** Four helper sweeps opened about 60 cited sources: gem's arXiv picks, the newer grk, mus, and cdx
  items, cld's top 15, and a gap search. Two sources could not be opened, the OpenAI Codex agent-loop post (403) and a
  dsebastien concept page. Most arXiv claims were checked against abstract and HTML pages, not full PDFs. Vendor and
  self-reported figures are labeled as such.
- **Library.** Two batched `bob ref find` calls, 87 queries in all. "Possible" title matches were resolved by URL
  identity: *Welcome to Gas Town*, *12 Factor Agents*, and Omnigent are queued; the Willison and Panozzo candidates
  were unrelated. Absence covers `ref/` only. Intake was not checked. I did not write to the vault.
- **Scope.** My additions are [#2](#the-problem-is-prompt-debt-and-promptdebt),
  [#5](#engelbart-abc-model-and-bootstrapping-strategy), [#13](#two-terminal-first-essays), *Superpowers*, *Managed
  Agents*, and the reading-budget rule. Everything else was found by at least one researcher and verified here.

Library check: 13 of 64 candidates already in your library (0 finished).
