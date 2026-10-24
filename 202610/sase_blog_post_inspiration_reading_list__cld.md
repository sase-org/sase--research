# Reading for the SASE Post: The Critique, the Debts, the Neighbors, and Your Own Voice

> **Research query:** Review the references in `~/bob/ref/blogs/` and `~/bob/ref/papers/` read over the last six
> months, then find new reading that will steer SASE, and the launch blog post in particular, in the right direction.
> End with a ranked reading list.

**Researcher:** cld · **Date:** 2026-10-24 · **Library window reviewed:** 2026-04-24 → 2026-10-24 · **Web window:**
mostly 2026-01 → 2026-10, plus three older classics that the post needs

## Bottom line

1. **Your recent reading builds SASE. It doesn't yet support the post.** Thirty-eight non-CV notes in `blogs/` and
   `papers/` fall in the window. All but one finished item were finished between 2026-10-03 and 2026-10-23. The heavy
   reads are institutional or architectural:
   - Anthropic's code-review, source-control, and CI posts
   - OpenAI's harness and Symphony posts
   - five memory papers
   - the goals paper

   Your highlights show you read for **primitives**: "Changesets are what 'patches' should be!", "This is a LOT like
   gates!", "'at any altitude'!". Those reads are about scale SASE doesn't have. The draft opens with pride and
   identity, and it admits to "~1 user." Its open slots have almost no support in your library:
   - the opening
   - the AI-slop and prompt-debt section
   - the neighbors paragraph
   - naming
   - "mention loop engineering and graph engineering"

2. **Read the critique before you write the honesty section.** Armin Ronacher's *Agent Psychosis* (2026-01-18) names
   Gas Town and Beads as examples of a dopamine-driven "slop loop." A 16,381-commit meta-harness with about one user
   will be read through that lens. Your "What it cost" section is the answer, so write it knowing the question.

3. **Borrow the debt vocabulary readers already have.** Margaret-Anne Storey's *cognitive debt* and Addy Osmani's
   *intent debt* give "prompt debt" a family. They also let you claim, with proof artifacts, that decision records,
   memory webs, plan artifacts, and goals are how SASE pays intent debt down.

4. **Gas Town has moved, and partly toward you.** Steve Yegge's *Fences, not Sandboxes* (2026-08-24) promotes rules
   in steps: custom, then advisory, then written law, then mechanical enforcement. Gas City's *Extending Beads* (2026-10-01)
   splits "memory" from "issue." Both match choices SASE already made: decision records plus guarded recipes, and
   memory webs kept separate from beads. Ronacher's *Latent Powers* explains the convergence without either side
   claiming credit. Check your Gas Town comparison against these, not against January's manual.

5. **Protect your voice.** In *Interpreting Pangram* (2026-09-14), Ronacher rewrote an LLM-drafted text fully by hand
   and it still scored as AI, because the structure came from the model. Your outline, intro proposals, and
   writer's-block plan all came from agent swarms. Use agents for facts. Write the claim sentences and the section order
   yourself.

6. **Some of these keep coming back.** *Agent Psychosis*, Storey's debt model, and the agent-diversity paper each
   appeared in an earlier SASE reading list, but none was ever captured. This list ranks them for a specific job in the
   post.

**If you read only three:** *Agent Psychosis* (#1), Storey + *Intent Debt* (#2), *Fences, not Sandboxes* (#3).
**Before the introduction:** Lawson (#7), Sloan (#8), and the autonomy-ladder pair (#13).

## What you read in the last six months

`bob ref list -t blogs,papers -S 6m` returns 43 notes. Five are your own CV drafts, which leaves 38: 21 finished,
2 started, 11 queued, and 4 dropped.

| Cluster | Finished | Queued / started | What your annotations show |
| --- | --- | --- | --- |
| **How Anthropic works** | Code review (23 highlights), *Redesigning source control* (18), CI test-impact analysis (5) | *The AI-native SDLC playbook* (started) | These carry the heaviest highlighting. Reactions: "Changesets are what 'patches' should be!", "Investigate these for use with sase!", "This feels like the problem I was having with mentors." Several are dependencies of your *Write introduction* task. |
| **Harness and orchestration** | OpenAI *Harness engineering*, *Symphony*, the 11-system *Harness Engineering* paper, *Gas Town Emergency User Manual* (12), *Levels, Ticks and Cascaded Intelligence*, *The Coming Loop*, *The Dot and the Swarm*, *Reminders app*, netclode | Omnigent (8 highlights), Stripe Minions ×2, *Astra*, *Reality Is the Final Verifier*, Hassan et al. | You push back when a source puts agents ahead of goals. On Gas Town's "read what it has to say," you wrote: "This feels wrong! You need to check on goals, not individual agents!" |
| **Memory** | *The Log is the Agent*, *Memory OS*, *Human-Inspired Memory*, *Filesystem-Based Memory*, *EA-Graph*, Steve Kinney (28 highlights), Karpathy's *llm-wiki*, Diátaxis | *Agent-Friendly Documentation* | Kinney's "flat is probably right" and Karpathy's index-first wiki match the SASE decision "No Retrieval Mechanism Before Its Corpus." |
| **Goals** | *Goals as First-Class Abstractions* (22 highlights, many turned into `#task`) | *AI Evals FAQ* | "no tool supports goal-guided agent orchestration" → "sase will!" |
| **Dropped** | — | Databricks benchmark, *What Does a Harness Buy?*, muse code, harness-for-RSI | You drop measurement papers that don't change a decision. |

Three patterns matter for the post:

- **Reading feeds the roadmap more than the prose.** Most comments become `#task` items: beads `goal` field, planners
  running `sase goals list`, PR Merge Master. Almost none become sentences for the post. The *SASE Blog · 2026-10-19*
  notes are the exception, and they are about the post's own requirements.
- **Few personal-voice essays.** *The Coming Loop* and *The Dot and the Swarm* are finished but have no highlights.
  Mitchell Hashimoto's personal-ladder post, the genre model the outline report pointed to, is still queued for
  2026-11-07. Yegge's launch post *Welcome to Gas Town* has been queued since February, even though you read its
  emergency manual.
- **The post's own requirements are unread territory.** The requirements list asks for:
  - a definition of AI slop and its four categories, including prompt debt
  - a limitations list
  - naming jokes
  - "Why a TUI?"
  - "loop engineering and graph engineering"
  - the "sub-agent doesn't cut it" point
  - "SASE's purpose: to build the next SASE from scratch"

  Nothing in the window speaks to these.

## What the post needs, and where each pick lands

| Post slot (from `sase_blog.md` and `sase_blog_contents.md`) | What's missing | Picks |
| --- | --- | --- |
| Opening: pride, identity, "~1 user" | A grief/agency frame and a defense of software for one | #7 Lawson, #8 Sloan, Ronacher's *Anger, Anxiety and Agency* |
| Overview: "meta-harness" and timeline infographic | The vocabulary readers have had since June (loops, factories, graphs) and a ladder to place yours on | #6 *Loop Engineering* + Macedo, #13 autonomy levels, the Graph Engineering survey |
| "Things that sase generalizes" (§1.1–1.7) | Outside evidence that your generalizations are the right ones | #3 Yegge, #12 *Extending Beads*, 12-Factor Agents (in library), #14 Trustworthy Change |
| Neighbors paragraph (Gas Town, Omnigent, Symphony) | A generous, current, non-competitive frame | #5 *Latent Powers*, #3 Yegge, Maggie Appleton on Gas Town |
| Honesty: AI slop, prompt debt, limitations | The critique, plus a debt vocabulary | #1 *Agent Psychosis*, #2 Storey + Osmani, #10 *The Tower Keeps Rising*, #15 Answer.AI/Naur |
| ACE / TUI / "optimal experience" | A research framing for human-centered agents | #9 *Humans are Missing* |
| The multi-lab-swarm quote | Evidence, and its limits | #11 diversity + cross-model review |
| Memory section ("every wrong way possible") | Another team discovering the same split | #12 *Extending Beads* |
| Your own voice | A concrete warning about borrowed structure | #4 *Interpreting Pangram* |

## Ranked reading list

Every entry has been checked against `bob ref find`. "Not in library" means only that it is absent from `ref/`.

### 1. Agent Psychosis: Are We Going Insane?

- **Armin Ronacher** · 2026-01-18 · short essay ·
  <https://lucumr.pocoo.org/2026/1/18/agent-psychosis/>
- **What it says:** Heavy agentic coding produces a dopamine-driven "slop loop." People grow dependent on their AI
  companions and file low-quality issues and PRs, and the review cost lands on maintainers. Ronacher cites Gas Town
  and Beads as insular communities that reinforce this. He contrasts wasteful hands-off loops such as Ralph with a
  prepared session (his MiniJinja Go port used 2.2M tokens). He includes himself in the critique. *"Their dæmon told
  them it was good."*
- **Why for SASE:** This is the frame an HN reader brings to "~17K commits, ~2.9M lines, ~1 user." The post can't
  avoid that frame, so it should answer it. Your four slop categories, the limitations list, and "Motion isn't
  progress" are the answer. Read it first and decide whether to name it.
- **Use in:** the honesty H2; the caveat on the stats strip in the opening.
- **Library:** not in library. It surfaced unranked in the 2026-10-10 agentic-SE reading list and was never captured.

### 2. Cognitive debt, with The Intent Debt (read as a pair)

- **Margaret-Anne Storey**, *How Generative and Agentic AI Shift Concern from Technical Debt to Cognitive Debt* ·
  2026-02-09 · <https://margaretstorey.com/blog/2026/02/09/cognitive-debt/>
- **Addy Osmani**, *The Intent Debt* · 2026-06-05 · <https://addyosmani.com/blog/intent-debt/>
- **What they say:**
  - **Storey:** technical debt lives in code, and cognitive debt lives in people. A student team could not make simple
    changes by week 7 or 8 because no one could explain the design. Her fixes: a human who understands each AI
    change, writing down *why*, and regular checkpoints.
  - **Osmani:** adds intent debt, which lives in artifacts (goals, constraints, rationale). *"An agent can't generate
    intent, because intent is the one input that has to come from you."*
- **Why for SASE:** "Prompt debt" is your best original term. Defined against this triple-debt model, it becomes debt
  that accumulates in the *instructions* themselves. That is new, and SASE has the receipts:
  - memory notes that are republished, not hand-edited
  - immutable decision records with `superseded_by`
  - plans stored as artifacts and read by later agents (your four-plans screenshot)
  - goals that "always link back to a user prompt"

  Those are intent-debt payments, and the post can show them.
- **Use in:** the honesty H2; the memory paragraph.
- **Library:** neither is in the library. Storey's paper version (arXiv 2603.22106) was ranked #18 in the 2026-10-10
  list and was not captured. The blog post is the easier read.

### 3. Fences, not Sandboxes

- **Steve Yegge** · 2026-08-24 · essay · <https://yegge.ai/essays/fences-not-sandboxes/>
- **What it says:** Yegge reports on ten weeks inside a 50–60-agent factory. The agents grew a *legal system*: a
  constitution, case law, courts, registries, and about 450 legal artifacts. Rules move up a ladder: custom, then
  advisory, then written constitutional law, then mechanical enforcement. New law comes from clarifying questions and
  daily postmortems. A fence is "any mechanism that turns you away if you aren't supposed to be there": a polite
  refusal, not a wall. The figures are his own and unverified.
- **Why for SASE:**
  - It is the most current statement of where Gas Town's author has gone. Your requirement "Break down gastown
    differences" and your high-priority task "link to the analogous crazy term used by GasTown" both depend on
    comparing against him.
  - His rule ladder closely matches SASE: memory notes, then immutable **decision records**, then **guarded recipes**
    and Symvision lint that refuse.
  - The match is a "what SASE generalizes" proof point and a friendly hook for the neighbors paragraph.
- **Use in:** the neighbors paragraph; §1.1 Gates → Plans → Epics; memory.
- **Library:** not in library.

### 4. Interpreting Pangram

- **Armin Ronacher** · 2026-09-14 · short essay · <https://lucumr.pocoo.org/2026/9/14/interpreting-pangram/>
- **What it says:** Ronacher had Opus 5 write a tweet-style text and then rewrote it by hand, keeping only the
  structure and ideas. Pangram still rated it AI. His conclusion: structure supplied by an LLM survives heavy editing.
- **Why for SASE:** The project task reads "My SASE post, in my own voice." The 2026-10-07 outline report noted that
  HN moderators reject generated text. Your outline, intro drafts, and wave plan all came from research swarms. The
  practical lesson is to let agents verify facts and render assets, and to write the claim sentences and the order of
  sections yourself. Your wave plan already says "write intro last," so own its structure too.
- **Companion:** *Content for Content's Sake* (2026-05-04,
  <https://lucumr.pocoo.org/2026/5/4/content-for-contents-sake/>): *"The fact that it was cheap for you to produce
  does not make it cheap for someone else to receive."*
- **Library:** not in library.

### 5. Latent Powers

- **Armin Ronacher** · 2026-09-05 · short essay · <https://lucumr.pocoo.org/2026/9/5/latent-powers/>
- **What it says:** People having separate conversations with the same models end up pursuing similar projects,
  because the models nudge everyone toward the same defaults. *"In this case I did not find or decide on CatPlay, the
  model did."*
- **Why for SASE:** It explains why SASE, Gas Town, Omnigent, Symphony, and Stripe's Minions converge on worktrees,
  work trackers, and orchestrators, without "I invented it" or "they copied it." It also poses the question the post
  should answer: which SASE abstractions were *your* decisions, and which were model defaults? Your 2026-10-19
  annotation already has an answer: SASE "started at a lower level of abstraction than gastown," and that let you get
  closer to the right names.
- **Use in:** the neighbors paragraph; the naming jokes.
- **Library:** not in library.

### 6. Loop Engineering, with Stop Hand-Holding Your Coding Agent

- **Addy Osmani**, *Loop Engineering* · 2026-06-07 · <https://addyosmani.com/blog/loop-engineering/>
- **Sandeco Macedo**, *Stop Hand-Holding Your Coding Agent: Engineering the Loops that Replace Step-by-Step
  Prompting* · arXiv 2607.00038 · 2026-06-28 · <https://arxiv.org/abs/2607.00038>
- **What they say:**
  - **Osmani:** names the June 2026 shift from prompting agents to designing the loops that prompt them. His building
    blocks are automations, worktrees, skills, plugins and connectors, and sub-agents, plus a state file. *"Build the
    loop. Stay the engineer."*
  - **Macedo:** defines a loop spec as trigger, goal, verification step, stopping rule, and memory. In a coded sample
    of 50 public loops, 70% verify autonomously and 74% name their terminal states. Automated triggering and durable
    memory are the least developed parts.
- **Why for SASE:** Your requirement says "Mention loop engineering and graph engineering at some point!" Readers have
  had this vocabulary since June. SASE maps onto it in one table:

  | Loop part | SASE |
  | --- | --- |
  | Automations and triggers | routines and jobs |
  | Worktrees | workspaces |
  | Skills | macros and skills |
  | Verification and stopping | monitors, gates, and `just check` |
  | Goal | goals |
  | Memory | memory |

  Macedo's weakest areas, durable memory and automated triggers, are where SASE is strongest. For the "graph" half,
  the *Graph Engineering* survey (arXiv 2608.21156, 2026-08-21) orders the stages prompt → context → harness → loop →
  graph. That is a ready-made spine for your timeline infographic.
- **Use in:** the overview; the timeline infographic; the series map.
- **Library:** not in library.

### 7. We mourn our craft

- **Nolan Lawson** · 2026-02-07 · essay · <https://nolanlawson.com/2026/02/07/we-mourn-our-craft/>
- **What it says:** Programmers will look back on being "the last generation to code by hand." Lawson neither
  celebrates nor resists. He invites readers to grieve a craft that will become "a curio for future generations."
- **Why for SASE:** Your first paragraph is about pride, and about "my attempt to take back some control." Lawson
  states the grief half more clearly than anyone. Your post is the *agency* half. Read it so your opening says what
  his doesn't: that your response was to build structure.
- **Companion:** Ronacher, *Anger, Anxiety and Agency* (2026-08-24,
  <https://lucumr.pocoo.org/2026/8/24/anger-anxiety-agency/>). He moves from uncertainty to curiosity to excitement.
  *"anger can feel more actionable because, instead of saying 'I don't know,' you already have someone to blame."*
- **Use in:** the opening.
- **Library:** not in library.

### 8. An app can be a home-cooked meal

- **Robin Sloan** · February 2020 · essay · <https://www.robinsloan.com/notes/home-cooked-app/>
- **What it says:** Sloan built a messaging app for his family. Software for a handful of people doesn't have to be a
  product, and "it won't change unless we want it to change." *"I am the programming equivalent of a home cook."*
- **Why for SASE:** "~1 user" is a joke in your draft right now. Sloan turns it into a position: SASE is a
  home-cooked meta-harness, tuned for one engineer's experience. That fits your requirement "Sase does not claim
  optimal performance, but optimal experience!", and it is why the TUI, the PIW obsession, and the Vim-mode joke make
  sense. It also gives *Agent Psychosis* an honest answer: SASE isn't pretending to be a platform yet.
- **Companion:** Ink & Switch, *Malleable Software* (2025, <https://www.inkandswitch.com/essay/malleable-software/>),
  co-written by Geoffrey Litt, whose *Understanding is the new bottleneck* you have queued.
- **Use in:** the opening stats; "Why a TUI?"; limitations.
- **Library:** not in `ref/`. It is a 2020 classic, so you may have read it elsewhere.

### 9. Humans are Missing from AI Coding Agent Research

- **Zora Z. Wang, John Yang, Kilian Lieret, et al.** · arXiv 2608.12355 · 2026-07-04 · position paper ·
  <https://arxiv.org/abs/2608.12355>
- **What it says:** As agents improve, the bottleneck moves to how people communicate with, supervise, and trust them.
  The paper names four dimensions of the human-agent loop: task alignment, verifiability, steerability, and
  adaptability.
- **Why for SASE:** This is SASE's thesis in a research voice, from authors of SWE-bench and SWE-agent. The four
  dimensions give the ACE section a neutral rubric:
  - alignment → goals, plans
  - verifiability → gates, receipts, `just check`
  - steerability → `%wait`, `#fork`, questions, stashes
  - adaptability → memory

  Citing it makes "optimal experience" a stated design priority with a research basis, not just taste.
- **Use in:** the overview; the ACE/TUI section.
- **Library:** not in library.

### 10. The Tower Keeps Rising

- **Armin Ronacher** · 2026-07-13 · essay · <https://lucumr.pocoo.org/2026/7/13/the-tower-keeps-rising/>
- **What it says:** Ronacher uses Bruegel's *Tower of Babel*. Agents remove the friction that kept people's mental
  models in sync: reading code, asking colleagues. Each change looks reasonable while shared understanding erodes.
  *"The tower does not fall, it just keeps rising."*
- **Why for SASE:** It is the best single image for your fourth slop category ("accumulated degradation in alignment")
  and for "the agents tab is the buggiest part of the TUI." It pairs with the Anthropic code-review diagram you
  highlighted ("If machines do most of the reading, how does anyone learn the code?") and with Litt's queued essay.
- **Use in:** the honesty H2.
- **Library:** not in library.

### 11. Understanding Agent Scaling via Diversity, with When Does a Second Model Help?

- **Yingxuan Yang, Chengrui Qu, Muning Wen, et al.**, *Understanding Agent Scaling in LLM-Based Multi-Agent Systems
  via Diversity* · arXiv 2602.03794 · 2026-02-03 · <https://arxiv.org/abs/2602.03794>
- **Tae-Eun Song**, *When Does a Second Model Help? Cross-Model Review in LLM Verification* · arXiv 2610.01471 · v2
  2026-10-06 · <https://arxiv.org/abs/2610.01471>
- **What they say:**
  - **Yang et al.:** homogeneous agents show sharply diminishing returns. Two diverse agents can match or beat
    sixteen identical ones.
  - **Song:** one same-model review plus one cross-model review caught more planted errors than two same-model
    reviews (56.7% vs 42.7%), but not more than two strong cross-model reviews. The design can't separate "different
    model" from "stronger reviewer."
- **Why for SASE:** Your quote reads: "The ability to have different frontier models from competing labs swarm a
  difficult task together is something even those working at those labs don't have access to." The first paper backs
  it. The second bounds it: diversity helps when each reviewer is strong. That supports the decision that every size
  alias should span more than one provider, and it warns against claiming that a cheap second model is enough.
- **Use in:** wherever the swarm quote lands; the research-swarm anecdote.
- **Library:** neither is in the library. The diversity paper was Tier 3 in the 2026-10-07 next-direction list and
  was not captured.

### 12. Extending Beads: Memories, Versions and the Wire Protocol

- **Donna Box et al.** (Gas City blog) · 2026-10-01 ·
  <https://blog.gascity.com/posts/extending-beads-memories-versions-and-the-wire-protocol/>
- **What it says:** Beads' issue model (claim, block, close) suits work, not durable project knowledge. The post
  proposes:
  - Memory Beads
  - a generic graph of beads and typed links
  - an HTTP wire protocol
  - versioning, so a PR can cite the exact policy version it followed

  *"Unlike an Issue, a Memory doesn't become ready or blocked, and we don't close it when we've finished reading it."*
  It is a preview that "may corrupt your Beads data."
- **Why for SASE:** Another team found the split SASE already made: beads for work, memory notes and webs for
  knowledge, and decision records that are superseded rather than edited. That supports your "implemented project
  memory every wrong way possible… converging" line and the §1.2 *Beads → Sidecar repos* argument.
- **Use in:** §1.2; the memory paragraph; the neighbors paragraph.
- **Library:** not in library.

### 13. Agentic Autonomy Levels, with The Five Levels

- **Addy Osmani**, *Agentic Autonomy Levels* · 2026-07-02 · <https://addyosmani.com/blog/agentic-autonomy-levels/>
- **Dan Shapiro**, *The Five Levels: from Spicy Autocomplete to the Dark Factory* · 2026-01-23 ·
  <https://www.danshapiro.com/blog/2026/01/the-five-levels-from-spicy-autocomplete-to-the-software-factory/>
- **What they say:**
  - **Shapiro:** "almost everyone tops out" at level 3, reviewing diffs all day. Level 5 is a dark factory where no
    one reviews code.
  - **Osmani:** splits autonomy into two axes, *agency* (how far one agent goes) and *orchestration* (how many agents
    and who coordinates). He argues the level should follow the verification available. He names an anti-pattern,
    "summary substitution," where an agent's summary stands in for review.
- **Why for SASE:** Your intro is a personal ladder: Boris method → `tmux_ai_window` → auto-approved plans →
  `%wait`/`#fork`. Industry ladders already exist (Yegge's eight stages, Shapiro's five levels). Osmani's two axes fit
  SASE best: you climbed the orchestration axis (forks, waits, tribes, clans) while gates kept per-agent agency
  bounded. One sentence placing your ladder on those axes would sharpen the intro. "Summary substitution" also names
  what you objected to in Gas Town's "read what it has to say."
- **Use in:** the introduction; the timeline infographic.
- **Library:** neither is in the library. The queued Swarmia "Five Levels" post is a different article.

### 14. Software Engineering in the Agent Era: From Trustworthy Change to Human-Agent Software Organizations

- **Zhongjie Wang, Mingyi Liu** · arXiv 2609.04630 · 2026-09-04 · conceptual paper ·
  <https://arxiv.org/abs/2609.04630>
- **What it says:** Agents can scale execution without adding headcount. Framing, verification, integration, and
  accepting residual risk stay bounded by human capacity. The paper proposes three ideas:
  - *Trustworthy Change* as the engineering object
  - a *Responsibility Topology*
  - a *Human-Agent Cell* that produces candidates and evidence but **holds no acceptance authority**

  It reports no empirical results.
- **Why for SASE:** It formally states your decision "Completion Is Host-Owned": agents submit declarations, and
  host-owned finalizers act. Cite it if the post explains why SASE agents never commit or open PRs themselves, or in a
  future section on finalizers.
- **Use in:** §1.4 VCS and workspace operations; Future Work.
- **Library:** not in library.

### 15. Why LLMs can't make your code simpler

- **Pol Alvarez Vecino** (Answer.AI) · 2026-08-19 · essay ·
  <https://answer.ai/posts/2026-08-19-llms-code-simpler.html>
- **What it says:** Building on Naur's *Programming as Theory Building*, the essay argues that the complexity that
  matters lives in the team's theory, not the code. LLMs can't judge when an abstraction's hidden cost isn't worth
  paying. The case study is Answer.AI declining an LLM's suggestion to restore Stripe subscriptions.
- **Why for SASE:** Two of your slop categories, "unnecessary backward compatibility" and "duplication of
  functionality," are exactly what the essay says agents won't fix unprompted. The theory-building frame also backs
  your claim that names matter.
- **Companions:**
  - Naur's 1985 original (not in `ref/`; about 10 pages)
  - Sean Goedecke, *Programming (with AI agents) as theory building* (2026-04-03,
    <https://www.seangoedecke.com/programming-with-ai-agents-as-theory-building>): agents build theories they can't
    keep, so they rebuild each session. That is the case for SASE memory in one line.
- **Use in:** the honesty H2; memory.
- **Library:** not in library.

## Also worth knowing (unranked)

**Voice and naming**

- Ronacher, [*Clanker: A Word For The Machine*](https://lucumr.pocoo.org/2026/5/26/clankers/) (2026-05-26). He argues
  "agent" implies agency and responsibility that belong to people: *"the machine cannot be responsible, whoever is
  wielding it is."* Useful for your "the term sub-agent doesn't cut it" requirement and the naming jokes.
- Julia Evans, [*Some tactics for writing in public*](https://jvns.ca/blog/2023/08/07/tactics-for-writing-in-public/)
  (2023). Ask readers for experiences, not opinions. That fits your plan to end with `type:poll` GitHub issues.

**Evidence for each slop category**

- Ronacher, [*Building Pi With Pi*](https://lucumr.pocoo.org/2026/5/24/pi-oss/) (2026-05-24). AI code adds local
  defenses (tolerant readers, fallbacks) instead of global invariants. *"Almost always, the correct fix is not to
  handle the bad state, but to make the bad state impossible."* It also gives auto-close numbers for an AI-flooded
  tracker.
- Osmani, [*Agentic Code Quality*](https://addyosmani.com/blog/agentic-code-quality/) (2026-08-08). Quality gates move
  into the harness.

**The cost of orchestration**

- Osmani, [*The Orchestration Tax*](https://addyosmani.com/blog/orchestration-tax/) (2026-05-24): *"You are the GIL of
  your AI agents."*
- Osmani, [*Software Factories, Light and Dark*](https://addyosmani.com/blog/software-factories/) (2026-07-20): *"It is
  not a bigger agent; it is an org chart made of loops."*
- Osmani, [*Human judgment doesn't leave the software factory. It
  relocates.*](https://addyosmani.com/blog/human-judgment-doesnt-leave-the-software/) (2026-08-21).

**Counterpoints to steel-man**

- Martin Monperrus, [*The End of Code Review*](https://arxiv.org/abs/2606.13175) (2026-06-11): mandatory human review
  of agent code is "a dead end." Read it against Anthropic's code-review post, which you finished.
- Simon Willison, [*Vibe coding and agentic engineering are getting closer than I'd
  like*](https://simonwillison.net/2026/May/6/vibe-coding-and-agentic-engineering/) (2026-05-06).
- Willison on Mario Zechner, [*Thoughts on slowing the fuck
  down*](https://simonwillison.net/2026/Mar/25/thoughts-on-slowing-the-fuck-down/) (2026-03-25).
- Ronacher, [*The Final Bottleneck*](https://lucumr.pocoo.org/2026/2/13/the-final-bottleneck/) (2026-02-13).

**The Gas Town neighborhood**

- Maggie Appleton, [*Gas Town's Agent Patterns, Design Bottlenecks, and Vibecoding at
  Scale*](https://maggieappleton.com/gastown) (January 2026). The outline report flagged this as the critique readers
  will carry.
- Julian Knutsen, [*Rush Hour in Gas City*](https://blog.gascity.com/posts/rush-hour-in-gas-city/) (2026-10-21). They
  split the PR gate from post-merge runs and cut the PR gate from 25 to about 4.5 minutes. Bazel then runs only 2–6% of
  tests per PR. This mirrors your two-speed CI decision and the Anthropic test-impact post.

**Large swarms**

- Nicholas Carlini, [*Building a C compiler with a team of parallel
  Claudes*](https://www.anthropic.com/engineering/building-c-compiler) (2026-02-05).
- Cursor, [*Scaling long-running autonomous coding*](https://cursor.com/blog/scaling-agents) (January 2026). Flat peer
  coordination failed, and planners plus workers worked.

**"The first myth"** (from your requirement "SASE's purpose: To build the next SASE from scratch")

- Fred Brooks, *Plan to Throw One Away* and *The Second-System Effect*, chapters 11 and 5 of *The Mythical Man-Month*.
  Neither is in `ref/`. Both are a warning and a blessing for a project that plans its own rewrite.
- Ronacher, [*AI And The Ship of Theseus*](https://lucumr.pocoo.org/2026/3/5/theseus/) (2026-03-05): *"if you throw
  away all code and start from scratch, even if the end result behaves the same, it's a new ship."* It touches the
  rename question too.

**Why a TUI**

- [*Why are coding agents all going to the
  terminal?*](https://arnorhs.dev/posts/2025-10-11/why-are-coding-agents-all-going-to-the-terminal/) (2025-10-11). It
  is thin. Your own experience will make a better section than any source found.

## Already in your library: move these up

- **Hassan et al., *Agentic Software Engineering*** (arXiv 2509.06216). Queued at high priority, scheduled for
  2026-10-19, so it is now overdue. It is the source of SASE's name, and you planned to read the appendix. Version 3 is
  dated 2026-06-24, so check which version your PDF is.
- ***12 Factor Agents*** (HumanLayer). Queued since 2026-04-27 (legacy backlog). Three factors line up with SASE:
  - Factor 6 (launch, pause, resume) and Factor 7 (contact humans with tool calls) are close to gates.
  - Factor 12 ("make your agent a stateless reducer") is close to "Agents Are Single-Turn."

  It is the best outside citation for your "plan mode is a special case of some deeper primitive" note.
- ***Welcome to Gas Town*** (Yegge, 2026-01-01). Queued since 2026-02-11 (legacy backlog). It is the genre model for
  a launch post. You read the manual but not the launch.
- ***My AI Adoption Journey*** (Hashimoto). Queued for 2026-11-07. It is the model for a personal ladder, so read it
  *before* the introduction rather than after.
- ***Understanding is the new bottleneck*** (Litt). Queued for 2026-10-25. Pair it with #10.
- ***Introducing Omnigent*** is still "ready" with 8 highlights. Footnote [2] in your draft depends on it, so finish it
  or mark it read.

## Considered and dropped

- **Vendor "meta-harness" and "graph engineering" explainers** (MindStudio, TerminalBlog, TrueFoundry, Analytics
  Vidhya): marketing, with claims I couldn't verify. Osmani, Macedo, and the Feng survey cover the ideas.
- **Peter Steinberger's June loop post** and the reported July "graphs" follow-up: tweets, widely retold, and their
  content is captured by #6.
- **Yegge's Medium posts** (*Welcome to Gas City*, *Vibe Maintainer*, *Software Survival 3.0*): Medium blocked
  automated fetches (HTTP 403), so I had listing blurbs only. *Welcome to Gas City* is probably worth reading, but I
  can't vouch for its contents.
- ***Terminal Is All You Need*** (CHI 2026 workshop): only a vendor-hosted summary was available.
- **"Welcome to Glass Town" (AAIF) and Every's "Inside the 100 agent software factory"**: these appeared in results
  but I couldn't confirm them.
- **Re-ranking items from earlier SASE reading lists that serve the roadmap, not the post:** ParallelPilot, *The Work
  Behind Delegation*, *Mo' Models, Mo' Problems*, the receipts and approvals papers. They remain good. This report is
  about the post.

## Capture commands (proposed, not run)

```bash
bob ref create https://lucumr.pocoo.org/2026/1/18/agent-psychosis/ -L
bob ref create https://margaretstorey.com/blog/2026/02/09/cognitive-debt/ -L
bob ref create https://addyosmani.com/blog/intent-debt/ -L
bob ref create https://yegge.ai/essays/fences-not-sandboxes/ -L
bob ref create https://lucumr.pocoo.org/2026/9/14/interpreting-pangram/
bob ref create https://lucumr.pocoo.org/2026/9/5/latent-powers/
bob ref create https://addyosmani.com/blog/loop-engineering/
bob ref create https://arxiv.org/abs/2607.00038
bob ref create https://nolanlawson.com/2026/02/07/we-mourn-our-craft/ -L
bob ref create https://www.robinsloan.com/notes/home-cooked-app/
bob ref create https://arxiv.org/abs/2608.12355
bob ref create https://lucumr.pocoo.org/2026/7/13/the-tower-keeps-rising/ -L
bob ref create https://arxiv.org/abs/2602.03794
bob ref create https://arxiv.org/abs/2610.01471
bob ref create https://blog.gascity.com/posts/extending-beads-memories-versions-and-the-wire-protocol/
bob ref create https://addyosmani.com/blog/agentic-autonomy-levels/
bob ref create https://www.danshapiro.com/blog/2026/01/the-five-levels-from-spicy-autocomplete-to-the-software-factory/
bob ref create https://arxiv.org/abs/2609.04630
bob ref create https://answer.ai/posts/2026-08-19-llms-code-simpler.html
```

## Method and limits

- **Library review:**
  - Read every note returned by `bob ref list -t blogs,papers -S 6m -g`: 43 notes, including highlights and comments.
    The five CV drafts were excluded from the analysis.
  - Read the blog project materials: `sase_blog.md`, `sase_blog_contents.md`, `why_sase.md`, the annotated *SASE Blog
    · 2026-10-19* notes, and the writer's-block task plan.
  - Used the finished-external list for taste.
- **Prior research:** read through `sase artifact read`, to avoid repeats and to stay aligned with decisions already
  made:
  - the 2026-10-07 outline report
  - the reading lists from 2026-10-07 (next-direction), 2026-10-10 (agentic SE), and 2026-10-17 (merge discipline)
- **Web:**
  - Searched on 2026-10-24.
  - Every ranked item was opened by a fetch agent, and the summaries and quotes come from those fetched pages. The
    exceptions are Medium-hosted Yegge posts, which returned 403, and the HN thread for Zechner's essay.
  - arXiv abstracts were fetched directly. Numbers are as the authors report them. Yegge's factory figures are
    self-reported.
- **Independence:** I didn't open, search for, or ask about any other researcher's report from this swarm.
- **Limits:**
  - My web search is US-only.
  - Several 2026 blogs (Ronacher, Osmani) are prolific, so I chose among dozens of posts by fit to the post's slots,
    not by popularity.
  - Library "not found" covers `ref/` only.

Library check: 5 of 75 candidates already in your library (0 finished).
