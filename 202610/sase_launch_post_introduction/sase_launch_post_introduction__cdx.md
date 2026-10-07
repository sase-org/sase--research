---
title: "Opening SASE's first post: identity, tmux, and the cost of coordination"
researcher: cdx
researched: 2026-10-07
scope: "Independent research and a finished three-paragraph introduction"
---

# Opening SASE's first post: identity, tmux, and the cost of coordination

Open with Bryan's changing experience of engineering, connect it to the concrete tmux workflow that preceded SASE, and introduce SASE by the job it does. The strongest story in the notes is a developer trying to retain understanding and control while delegating more execution. The opening should make that problem recognizable before naming the product's components.

This report was researched independently. I did not locate, read, request, or indirectly obtain the findings of the other researchers in this swarm. The vault review preceded external research. No vault notes or tasks were changed, and the existing blog files were left untouched.

## What the vault says

I used `bob query` to discover related notes and tasks, then `bob ref show --ref-dir .` to read the four project notes below. I also read Bryan's annotations on the older draft and launch-post review through `bob ref show`, rather than treating those earlier reports as independent evidence about the product.

| Input | Evidence relevant to the opening | Editorial consequence |
| --- | --- | --- |
| [why_sase.md](/home/bryan/bob/why_sase.md) | Bryan begins with pride in being a software engineer and a desire to regain control as the work changes. He also proposes a retrospective on AI coding tools. | Keep a short personal opening. Make the change tangible through the developer's work rather than a prediction about the profession. |
| [sase_blog_0.md](/home/bryan/bob/sase_blog_0.md) | The introduction outline moves from Boris's workflow to `tmux_ai_window`, then plan automation and coordination. Another requirement asks for experience rather than optimal performance. | Use the script as the bridge from personal motivation to an engineering problem. Promise a clearer workflow without asserting a speedup. |
| [sase_blog.md](/home/bryan/bob/sase_blog.md) | The series calls for limitations, humor, and an account of the accumulated debt of agent-written work. | Keep the voice candid and allow one specific joke. Avoid a launch pitch that sounds certain the tool has solved engineering. |
| [sase_blog_blockers.md](/home/bryan/bob/sase_blog_blockers.md) | This project note was canceled; its individual tasks mix completed and canceled items. | Treat it as historical planning context, not a current release gate or a capability checklist. |

The current writing tasks in `sase_blog_0.md` include gathering references, describing section demos and infographics, and creating linked notes for the post. The outline task is completed, while the old draft-proofreading task is canceled. Those states suggest continuing from the existing direction with fresh prose, rather than assuming the July draft should merely be polished. Task states are evidence of Bryan's writing process; they do not prove which software features have shipped.

Two annotations sharpen the brief. Bryan's comment on the earlier July draft asks for concrete reasons behind waiting and forking. His comment on the prior launch-post review proposes the title **SASE: Structured Agentic Software Engineering**. That points toward a personal introduction followed quickly by coordination examples, with the acronym expanded once.

I also checked the current paper capture, [agentic_software_engineering.md](/home/bryan/bob/ref/papers/agentic_software_engineering.md). Bryan's two comments concern preserving the reason for a plan and recognizing the similarity between consultation requests and gates. These are useful signals: the product is concerned with intent and human decisions, not only starting more processes. The capture is marked queued even though it contains annotations; I do not infer a completed reading from those annotations.

The linked *Harness for RSI* reference is marked dropped. I checked its metadata and did not make it the argument for this opening. The notes' wish for a broad retrospective can be satisfied in one sentence about changing workflows. Exact launch dates, benchmark charts, and a twelve-month chronology would introduce work and claims that the introduction does not need.

## Checks against the actual project

I read the primary checkout's `README.md`, `docs/acknowledgements.md`, and the two existing blog files `docs/blog/posts/structured-agentic-software-engineering.md` and `docs/blog/posts/why-coding-agents-need-orchestration.md`. These establish the product's current description and the documented origin story. The proposed paragraphs below are newly written; they do not copy the older opening's sequence or jokes.

The current README describes a developer supervising coding agents, isolated workspaces, reusable prompts, and recorded work. It also labels the software alpha. The July blog file has already been updated to acknowledge that xprompts are now called macros. Its provider enumeration also differs from the current README. Accordingly, the introduction uses the durable phrase **reusable prompts**, names only two example CLIs, and leaves exhaustive terminology and provider lists for the body.

I opened the linked chezmoi repository through `sase repo open` and inspected `home/bin/executable_tmux_ai_window`. The script really does provide a provider menu and launch agents in numbered tmux windows. This supports the modest claim that it made agent launching easier. It does not establish that the script created isolated checkouts or supplied durable plans, review tracking, or SASE's wider coordination behavior. The proposed introduction assigns those capabilities to SASE.

The existing project materials attribute the parallel-session inspiration to Boris Cherny and link his setup thread. I attempted to read the original post, but the web reader could not retrieve it. I therefore preserve that attribution as Bryan's documented account, without independently claiming its exact session count, wording, date, or historical priority. The opening does not claim that Boris invented parallel agent work.

Source checkout revisions for reproducibility:

- SASE: `62604c10b7b01af1dd28cd43404d6728c2c3a375`.
- Chezmoi: `0cd5c177b879ce59d69bf4918c4c4dd9b8bf009a`.

## Independent external research

The sources support a framing around structured work and human judgment. They do not establish that SASE improves productivity or that coordination is the only bottleneck.

**The conceptual basis.** Hassan and colleagues' paper distinguishes goal-directed agentic engineering from simple code generation and describes human command and agent execution environments, with handovers and human consultation. It supplies a conceptual rationale for introducing SASE around understanding and directing work. The paper is a vision and research roadmap; it is not a controlled evaluation of this implementation. Its name should be credited in the body when the acronym's origin is discussed. [Paper, first submitted September 7, 2025; current version June 24, 2026](https://arxiv.org/abs/2509.06216).

**Why records and handoffs matter.** Anthropic's long-running-agent experiments describe incomplete work, poor continuity across context windows, and premature completion claims. Their intervention includes persistent progress information, incremental tasks, and verification. This supports making lasting work records part of the product explanation. It does not prove that a team of agents outperforms a single agent. [Anthropic engineering report, November 26, 2025](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents).

**Parallel work is already supported by agent tools.** Claude Code's current documentation describes separate worktrees for concurrent sessions. This makes isolation a familiar mechanism, while leaving room for SASE's broader coordination workflow. The introduction should explain what the author wants to manage around execution; it should not suggest that parallel launching or workspace isolation is exclusive to SASE. SASE's documented numbered workspaces are clones, so the draft calls them workspaces rather than worktrees. [Official parallel-session documentation, accessed October 7, 2026](https://code.claude.com/docs/en/worktrees).

**A reason to avoid performance promises.** METR's July 2025 randomized study found a 19% slowdown among 16 experienced contributors completing 246 tasks with the tested early-2025 tools. It is a specific setting and time period, not evidence that current agents generally slow developers down. [Original study report](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/).

The February 2026 follow-up reports suggestive changes but says selection effects and difficulties measuring concurrent agent work make the new estimates unreliable. This is particularly relevant to a tool for parallel work: session counts and subjective excitement are inadequate evidence for a productivity claim. I would keep both studies out of the opening and use them only to discipline its wording. [METR follow-up, February 24, 2026](https://metr.org/blog/2026-02-24-uplift-update/).

**Consistency with the public description.** SASE's public docs describe durable work state, provider-independent coordination, and a terminal interface for supervising agent activity. The proposed product definition aligns with that description. These are first-party capability claims, not independent evidence of user outcomes. [SASE documentation, accessed October 7, 2026](https://sase.sh/).

These findings support an editorial inference: explaining the cost of keeping delegated work understandable is a stronger introduction than announcing a productivity revolution. That is my recommendation, not a conclusion directly tested by any cited source.

## Recommended structure and boundaries

Use three paragraphs, each doing one job:

1. **The change in the author's work.** Start with the pride already present in `why_sase.md`, then describe the progression from suggestions to delegated tasks to concurrent agents. Keep the account personal. The engineering responsibility—deciding what should exist and judging the result—gives the paragraph its continuity.
2. **The concrete coordination problem.** Introduce tmux and `tmux_ai_window` briefly, then name the things that became hard to keep track of: prompts, plans, changes, dependencies, and requests for attention. One joke about window management gives the problem a human voice without mocking the work.
3. **SASE and the reader's promise.** Expand the name, state that it coordinates existing coding-agent CLIs, and describe a few visible benefits. End by promising an explanation of the workflow, which can lead into the overview and reusable-prompt sections.

Keep the heavier material for later: acronym lineage and formal research terminology; launch dates; `%wait` and fork syntax; provider selection; the scheduler; philosophical claims about the profession; feature comparisons; and detailed limitations. The final paragraphs leave room for all of those subjects without trying to compress the rest of the post into the opening.

The supplied outline wants a historical timeline. The first paragraph below honors that in miniature through a progression of capabilities. If the post still needs an infographic, place it after the introduction or in the overview and verify dates separately. The identity language is adapted from Bryan's own draft, while the light disorientation and window-management joke are proposed authorial phrasing, not reported quotations or invented biographical events.

There is no measured SASE speedup in the material reviewed here. The draft therefore states an aim—making the work easier to understand, steer, and review—and describes mechanisms. It leaves the reader free to judge the experience from the demonstrations that follow.

## Fully written introduction

I've always been proud to call myself a software engineer. Over the past few years, that job has started to feel different. AI tools went from suggesting the next line to taking on tasks, changing files, and running tests. Now I can have several agents working at once. That is exciting, and a little disorienting: I still have to decide what should be built and whether the result is any good, while learning how to direct work I am no longer doing entirely myself.

Inspired by [Boris Cherny's parallel-session workflow](https://x.com/bcherny/status/2007179832300581177), I started running coding agents in separate tmux windows and wrote a little script, `tmux_ai_window`, to make launching them easier. Each extra agent brought more bookkeeping: its prompt, its plan, what it had changed, what it was waiting for, and when it needed me. My engineering workflow was starting to look suspiciously like terminal-window management.

That experiment grew into **SASE** (Structured Agentic Software Engineering, pronounced “sassy”), an [open-source coordination layer for coding agents](https://sase.sh/). SASE runs tools such as Claude Code and Codex in isolated workspaces, keeps a record of their work, and gives me one terminal interface for reusable prompts, approvals, and results. The aim is to make working with agents easier to understand, steer, and review. This post explains how I got here and how those pieces fit together.
