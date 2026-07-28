---
create_time: 2026-07-28
updated_time: 2026-07-28
status: research
---

# Getting Bryan Started on SASE's First Blog Post

## Research Question

How can Bryan make genuine progress on SASE's first blog post when the codebase already contains a large amount of
polished, entirely agent-generated prose?

## Executive Finding

This is not a blank-page problem. It is an **authorship problem created by abundance**.

The repository already contains:

- 290 Markdown research files totaling about 802,000 words in the research sidecar;
- ten drafted blog posts totaling about 20,500 words;
- a 5,353-word draft called *The Missing Operating Layer for Coding Agents*; and
- a newer, public 2,762-word launch post called *SASE: Structured Agentic Software Engineering*.

More outlining, research, and agent-generated prose will probably make starting harder. Each new artifact increases the
feeling that Bryan must either approve a finished synthetic voice or compete with it.

The best route forward is to stop treating the existing launch article as Bryan's draft. Treat it as a **fact-checked
source packet**. Bryan should create a fresh human source by telling one concrete story: the progression from a useful
tmux window launcher to a workflow whose real bottleneck was no longer writing patches, but supervising, remembering,
sequencing, and landing agent work. The first post should be a founder's field note about that realization, not a tour
of SASE's nouns.

The current post already contains the seed of this story in its `tmux_ai_window` anecdote. What it lacks is the part no
agent can recover from the repository: what actually happened, what Bryan felt responsible for, which workaround failed
first, what trade-off he chose knowingly, and what he believes other developers are getting wrong.

## What I Examined

Internal evidence:

- `README.md`
- `docs/blog/index.md`
- all ten files under `docs/blog/posts/`
- the current launch article, `docs/blog/posts/structured-agentic-software-engineering.md`
- the earlier draft, `docs/blog/posts/why-coding-agents-need-orchestration.md`
- prior blog research under `sase/repos/research/202605/`, `202606/`, and `202607/`
- repository history, release tags, and the history of the current launch article

External evidence:

- strong first-person developer-tool essays and launch posts from Tailscale and Astral;
- current technical-writing guidance from Diátaxis, Google, and Paul Graham; and
- the current official product surfaces for Codex, Claude Code, and GitHub coding agents.

Measurements and market checks were made on 2026-07-28.

## Diagnosis: Why Starting Feels Difficult

### 1. There is already too much "finished" material

The ten blog files are not notes. They are polished articles with titles, frontmatter, cross-links, terminology,
commands, and conclusions. The two first-post candidates alone contain more than 8,000 words.

That creates three kinds of friction:

1. **Selection friction:** Which of the already coherent narratives is the real one?
2. **authority friction:** What can Bryan add when the draft already sounds certain about everything?
3. **voice friction:** Editing a fluent paragraph tends to preserve its rhythm and assumptions even when individual
   words change.

The solution is not to choose the least-wrong generated draft and begin line-editing it. The solution is to create a
small body of human source material that has higher authority than all existing prose.

### 2. The current article changes modes after a promising opening

The public launch post begins well. It names a recognizable workflow, describes the `tmux_ai_window` script, and says
that the workaround exposed a missing layer. Its first 46 lines contain 467 words.

After that, roughly 83% of the post is a product explainer:

| Section | Approximate words |
| --- | ---: |
| SASE Wraps Agent CLIs, Not Models | 472 |
| XPrompts | 686 |
| The Agents Tab in ACE | 549 |
| Install, Configure, Initialize | 430 |
| What's Next | 69 |

This material is technically useful, but it turns the post into a compressed manual. It introduces provider selection,
model aliases, skill deployment, XPrompt discovery, typed inputs, three invocation syntaxes, directives, alternations,
Cartesian products, multi-agent segment syntax, families, clans, hoods, tribes, approval keys, configuration layering,
sidecars, and initialization ordering.

A reader can finish with many facts about SASE but no vivid answer to:

> What happened to Bryan's work that made building this much machinery feel necessary?

### 3. The codebase knows the product, but it does not know the experience

Repository evidence can verify that SASE is a serious, rapidly evolving system. The current history contains more than
11,000 commits, almost all attributed to Bryan. The repo began as a GAI-to-SASE migration in February 2026, reached
public releases in June, and tagged v0.12.0 on July 27.

That history cannot answer the questions that make an origin story worth reading:

- What did the terminal look like on the day the old workflow stopped scaling?
- Which agent did Bryan forget about, and what did that cost?
- Was the first pain lost output, colliding edits, repeated prompts, lack of notification, or review overload?
- What was satisfying about the tmux workflow before it became painful?
- Which SASE feature felt obvious only in hindsight?
- What part of the current system is still awkward?
- Why build across multiple agent CLIs instead of committing to the favorite one?
- What did Bryan believe six months ago that he no longer believes?

These are not missing facts for an agent to research. They are the human source of the essay.

## The Market Has Moved: Avoid a Generic "Multi-Agent" Launch

The basic orchestration premise is timely, but it is no longer distinctive by itself.

OpenAI describes the Codex app as a command center for running multiple agents in parallel, reviewing diffs from
isolated worktrees, using reusable skills, and scheduling automations. Its announcement even says the challenge has
shifted from what agents can do to how people supervise them at scale.
([OpenAI, *Introducing the Codex app*](https://openai.com/index/introducing-the-codex-app/))

Claude Code now documents:

- an agent view for dispatching and monitoring background sessions;
- parallel worktree sessions;
- subagents; and
- experimental agent teams with a shared task list, dependencies, and inter-agent messages.

([Claude Code, *Run agents in parallel*](https://code.claude.com/docs/en/agents);
[Claude Code, *Orchestrate teams of Claude Code sessions*](https://code.claude.com/docs/en/agent-teams))

GitHub's Agents tab can dispatch Copilot and enabled third-party coding agents, follow their work, and route results
through pull-request review.
([GitHub, *About third-party coding agents*](https://docs.github.com/en/copilot/concepts/agents/about-third-party-coding-agents))

Therefore, the launch post should not rely on any of these claims:

- SASE lets you run agents in parallel.
- SASE gives agents isolated workspaces.
- SASE lets you see several agents in one interface.
- SASE supports reusable agent instructions.
- SASE can run work in the background.

Those are credible capabilities, but increasingly they are category expectations.

The more durable story is:

> I wanted the work around coding agents to belong to me and my repositories—not to one model vendor or one chat
> surface—so I built a local, git-native operating layer that makes prompts, work units, dependencies, approvals,
> reviews, and artifacts durable.

That claim is both more personal and harder for a fast-moving competitor feature list to invalidate. It also invites
honest discussion of trade-offs: SASE gains portability and owner-controlled workflow state, while inheriting the
rough edges and changes of the CLIs it wraps.

## What Strong Developer-Tool Essays Do

Three useful models suggest three compatible ingredients.

### Tailscale: begin with memory and a felt loss

David Crawshaw's *Remembering the LAN* begins with growing up around a small network above his parents' medical
practice. It spends substantial time on what that environment felt like before presenting the technical dream.
([Tailscale, *Remembering the LAN*](https://tailscale.com/blog/remembering-the-lan))

The transferable lesson is not "use nostalgia." It is: **begin with a world the author personally inhabited**. The
technical argument becomes credible because the desired future restores a quality the author can name from experience.

SASE's equivalent world is not an abstract "agentic future." It is Bryan's actual terminal: multiple `ai*` windows,
specific keys, repeated polling, and a homegrown script that was genuinely useful before its limitations became clear.

### Ruff: state a narrow theory and prove it

Charlie Marsh introduced Ruff with a blunt theory—Python tooling could be much faster—then supplied a working tool,
benchmarks, and an immediate installation path.
([Charlie Marsh, *Python tooling could be much, much faster*](https://notes.crmarsh.com/python-tooling-could-be-much-much-faster))

The lesson is: **one strong claim plus one proof is enough for a first post**. Ruff's launch did not need to explain
every future feature of an integrated Python toolchain.

SASE's narrow theory could be:

> Coding agents are becoming capable faster than our workflows for supervising their work.

The proof should be one real before/after workflow, not a component inventory.

### uv: make the promise, proof, adoption path, and limits visible

The uv launch starts with a one-sentence description, shows performance immediately, explains a few design principles,
gives installation commands early, and plainly names current limitations.
([Astral, *uv: Python packaging in Rust*](https://astral.sh/blog/uv))

The lesson is: **clarity and candor create confidence**. SASE can link to its quickstart rather than reproducing all
configuration, but the first post should say who can try it, who should wait, and what alpha software still means.

## Writing Guidance That Fits This Case

Diátaxis says good explanatory writing should provide historical context, discuss choices and alternatives, admit
opinion and perspective, and stay closely bounded so it does not absorb tutorials and reference material.
([Diátaxis, *Explanation*](https://diataxis.fr/explanation/))

That is almost an exact diagnosis of the current post. It contains explanation, tutorial, reference, and product tour
at once. The first post should retain history, choices, and opinions, while moving commands and exhaustive mechanics to
the quickstart and docs.

Google's technical-writing course recommends defining the reader's role and proximity to the subject, then providing
what that reader needs but does not already know. It specifically warns about the curse of knowledge and internal
vocabulary.
([Google, *Audience*](https://developers.google.com/tech-writing/one/audience))

For this post, the reader should be narrower than "software developers interested in AI":

> An experienced solo developer or tech lead who already runs coding-agent CLIs in real git repositories, has tried
> more than one concurrent session, and is beginning to feel coordination and review overhead.

That reader already understands git, terminals, pull requests, and coding agents. They do not know or need SASE's
internal taxonomy on first contact.

Paul Graham's advice is to use ordinary words and simple sentences, write the first draft quickly, then edit hard.
([Paul Graham, *Write Simply*](https://paulgraham.com/simply.html?viewfullsite=1))

In this case, "write the first draft quickly" matters because reading the polished generated drafts first will invite
imitation and self-editing. Bryan's first pass should be spoken or typed quickly from memory, with no attempt to sound
like the existing site.

## Recommended Reader Promise

After reading the first post, a new reader should be able to repeat only three ideas:

1. Running several capable coding agents moved Bryan's bottleneck from patch generation to coordination.
2. SASE wraps existing agent CLIs with owner-controlled, durable engineering workflow state.
3. SASE is for people who already feel this problem; it is alpha software and not a replacement for their agent CLI.

The reader does **not** need to learn the full meanings of ACE, AXE, XPrompts, ChangeSpecs, SDD, beads, sidecars,
families, clans, hoods, tribes, chops, lumberjacks, mentors, or model aliases.

## Recommended Article Shape

Target 1,200–1,800 words. That is not an SEO rule; it is a scope constraint intended to force one argument.

### Working title

**From a Tmux Full of Coding Agents to SASE**

This is clearer and more ownable than *The Missing Operating Layer for Coding Agents*. It promises an origin story,
not a universal category claim.

Other viable titles:

- **When My Coding Agents Became the New Bottleneck**
- **Why I Built an Operating Layer for Coding Agents**
- **The Scrollback Buffer Was My Agent Database**

### Outline

#### 1. One real scene (200–300 words)

Describe a particular day or repeated ritual. How many windows were open? What keys did Bryan press? What question was
he trying to answer? What went wrong or nearly went wrong?

Do not introduce SASE terminology yet.

#### 2. The workaround that almost worked (200–250 words)

Show `tmux_ai_window` and explain why it was good. Acknowledging that the old system worked prevents the post from
inventing a straw man.

Then name the limit: the script created processes, not durable work.

#### 3. The realization (200–250 words)

State the thesis in plain language:

> The agents were increasingly capable. My attention and the state between their sessions were not scaling with them.

Explain why more tmux automation or a single-provider UI was not the whole answer for Bryan.

#### 4. The principles behind SASE (350–500 words)

Use three principles, not a feature catalog:

1. **Wrap the agent CLIs; do not replace them.**
2. **Make prompts and work state durable and repository-aware.**
3. **Keep human gates at consequential transitions.**

Each principle gets one concrete example. Product names may appear in parentheses or links, but they should not drive
the paragraph.

#### 5. One proof (200–300 words)

Use a single GIF or still showing one prompt fan out to multiple isolated agents and the resulting work visible in ACE.
Walk through only what a cold reader can see:

- one request;
- separate workspaces;
- status in one view;
- an artifact or diff to review; and
- the human still able to stop, retry, or approve.

#### 6. Who it is for, current limits, and one next step (150–250 words)

Say explicitly:

- SASE is for developers already using agent CLIs heavily;
- one-off, single-agent users may not need it;
- it is alpha, POSIX-only software with an opinionated git/workspace model; and
- the smallest next step is the existing guided quickstart.

Link the install path. Do not reproduce full configuration in the essay.

## What to Reuse and What to Defer

### Reuse as source material

- The `tmux_ai_window` factual description.
- One ACE fan-out or observability GIF.
- The precise list of supported CLIs, probably in one sentence.
- The honest "wrap CLIs, not models" trade-off.
- The tested quickstart link and alpha/POSIX caveats.
- Existing documentation links for readers who want mechanics.

### Defer to later posts or docs

- model-selection syntax and alias configuration;
- XPrompt discovery precedence and all invocation forms;
- the directive catalog and Cartesian-product syntax;
- families, clans, hoods, and tribes;
- the plan-approval keymap;
- configuration-layer precedence;
- memory/repository/skill initialization order;
- ChangeSpecs, beads, SDD, AXE, chops, and lumberjacks as separate product tours; and
- the entire future roadmap.

The older 5,353-word post can remain an internal map of concepts. The newer 2,762-word post can become a product tour or
technical overview. Neither needs to be destroyed for Bryan to write the actual first-person launch essay.

## A 45-Minute Human-Source Session

The immediate goal is **not** to write the post. It is to generate 600–1,000 words of source material that only Bryan
could have produced.

### Rules

- Do not open either existing first-post draft.
- Use a voice memo if speaking is easier than facing a document.
- Do not look up commands, dates, or product names.
- Do not polish sentences.
- Mark uncertainty rather than stopping to research it.
- Include details that seem too small: key presses, window names, what time of day it was, what annoyed Bryan, and what
  he tried first.

### Questions

Answer these in order, spending about four minutes on each:

1. What did the best version of the old tmux workflow feel like?
2. Describe one specific moment when it failed to tell you what you needed to know.
3. What did you do manually, over and over, that eventually felt absurd?
4. What was the first piece of SASE you built to remove that pain?
5. When did the project stop feeling like a personal script and start feeling like a system?
6. Why was wrapping several agent CLIs important to you?
7. Which part of SASE reflects your strongest opinion about how software should be built?
8. What is still rough, and who should not use SASE yet?
9. If a skeptical friend said "tmux and git worktrees are enough," what would you agree with before disagreeing?
10. What do you hope your own workday feels like six months from now?

### Turn the source into a rough draft

After recording:

1. Transcribe it without smoothing the language.
2. Highlight five phrases that sound unmistakably like Bryan.
3. Circle one concrete incident and one opinion.
4. Delete everything unrelated to those two anchors.
5. Put the remaining fragments into the six-section outline above.
6. Write transitions only after the fragments are placed.

An agent can help after this point, but its role should be constrained:

- verify commands and product claims;
- identify unexplained terms;
- challenge overclaims against current competitors;
- suggest cuts and ordering;
- preserve Bryan's phrases; and
- flag invented or unsupported anecdotes.

The agent should not generate the first scene, choose what Bryan believes, or "make the voice more engaging."

## A Fill-in Skeleton for the First Ten Minutes

If a completely blank document is still blocking progress, begin with these prompts and leave the brackets visible:

> On [a real day or during a repeated ritual], I had [number] coding agents open in [terminal/tmux setup]. To find out
> [the thing you needed to know], I [specific manual action]. [Specific consequence or near miss.]
>
> This was not a bad workflow. I had built [the tmux helper] because [what it did well]. It let me [real benefit]. The
> problem was that it knew how to start processes, but it did not know [the durable work state you needed].
>
> That was when I realized [the thesis in Bryan's own words].

Stop after those three paragraphs. The goal is not to complete the post in one sitting; it is to replace the
agent-generated opening with a source that has authority.

## Sources

### Internal

- `README.md`
- `docs/blog/index.md`
- `docs/blog/posts/structured-agentic-software-engineering.md`
- `docs/blog/posts/why-coding-agents-need-orchestration.md`
- all other files under `docs/blog/posts/`
- `sase/repos/research/202605/blog_series_deep_research.md`
- `sase/repos/research/202606/blog00_launch_post_review_consolidated.md`
- `sase/repos/research/202606/sase_blog_launch_strategy_consolidated.md`
- `sase/repos/research/202606/sase_blog_series_structure_consolidated.md`
- `sase/repos/research/202607/blog_launch_readiness_audit.md`
- `sase/repos/research/202607/blog_launch_xprompts_agents_tui_consolidated.md`
- local git history through v0.12.0

### External

- [Tailscale: Remembering the LAN](https://tailscale.com/blog/remembering-the-lan)
- [Charlie Marsh: Python tooling could be much, much faster](https://notes.crmarsh.com/python-tooling-could-be-much-much-faster)
- [Astral: uv — Python packaging in Rust](https://astral.sh/blog/uv)
- [Diátaxis: Explanation](https://diataxis.fr/explanation/)
- [Google Technical Writing: Audience](https://developers.google.com/tech-writing/one/audience)
- [Paul Graham: Write Simply](https://paulgraham.com/simply.html?viewfullsite=1)
- [OpenAI: Introducing the Codex app](https://openai.com/index/introducing-the-codex-app/)
- [Claude Code: Run agents in parallel](https://code.claude.com/docs/en/agents)
- [Claude Code: Orchestrate teams of Claude Code sessions](https://code.claude.com/docs/en/agent-teams)
- [GitHub: About third-party coding agents](https://docs.github.com/en/copilot/concepts/agents/about-third-party-coding-agents)

## Final Recommendations

1. **Do not revise the generated launch post yet.** Start a blank document or voice memo without it visible. Use the
   existing article later as a fact source.
2. **Make the first post an origin story, not a SASE tour.** Center it on the progression from a useful tmux launcher
   to a coordination bottleneck that required durable work state.
3. **Write for one reader:** an experienced developer already running multiple coding-agent sessions in real git
   repositories. Do not write for AI newcomers or explain the entire project.
4. **Own one thesis:** agent capability is scaling faster than the operator workflow around it. Show one incident and
   one before/after proof.
5. **Lead with Bryan's choices, not commodity features.** Current vendor tools already offer parallel agents,
   worktrees, dashboards, skills, and automations. Explain why SASE is independent, local, provider-neutral,
   repository-aware, and opinionated about durable engineering state.
6. **Limit the first post to three principles and at most two product nouns beyond SASE.** Link the quickstart and docs
   for mechanics. Move taxonomies, command catalogs, and configuration details out.
7. **Be candid about fit and limits.** Saying that one-off users do not need SASE—and that alpha, POSIX-only,
   git/workspace-opinionated software has rough edges—will make the positive claims more credible.
8. **Do one 45-minute human-source session next.** Answer the ten questions above aloud, select one concrete incident
   and five phrases that sound like Bryan, and draft only the first three paragraphs. That is enough progress for the
   next session; it also creates the human source that every later agent-assisted edit should protect.
