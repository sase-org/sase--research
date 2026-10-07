# First SASE Blog Post: Outline Recommendation

Researcher: mus (5-researcher swarm, independent report).
Question: decide on an outline for the first sase blog post.
Method: reviewed related Obsidian vault notes and tasks via `bob query`, checked
Bryan's reference library via `bob ref`, and read the existing repo draft and blog
index. No peer swarm reports were consulted.

## 1. What the vault already decided

The first-post project note (`sase_blog_0.md`, parent `sase_blog.md`, status wip)
carries a decided outline (`^outline`, task completed 2026-07-07):

- Introduction — personal timeline (Boris method → `tmux_ai_window` →
  auto-approve plans → wait/fork), opening with a brief software-engineering
  transformation timeline plus a funny infographic.
- Overview
- XPrompts — editor tooling (sase-nvim / xprompt LSP vs prompt input widget),
  directives, alternations, argument types/usage, workflows (multi-prompt vs YAML,
  when to use each), "special" xprompts (`#fork`, project xprompts like `#gh:sase`).
- ACE — Agent tab (families/hoods), PRs tab, notification panel, AXE tab teaser.
- AXE — with a sase-telegram sub-section.
- Future Blog Posts — Beads/SDD, Memory, Mobile/Web, Evals, ChangeSpec
  (hooks, mentors, reviewer comments), architecture (pluggable CLI/VCS).

Supporting material in the vault:

- `why_sase.md` — the draft intro voice: pride in calling oneself a Software
  Engineer, sase as an attempt to "take back some control" from something coming
  for that identity; planned beats include repo stats with a "Motion isn't
  progress" quote, "it started with Claude Code," and a 12-month lookback.
- `sase_blog_0_legacy_notes.md` — superseded 10-section outline (caveman diagram,
  gastown comparison and its fatal flaw, xprompts, AXE/Lumberjacks/Chops, Beads/SDD,
  ChangeSpecs, pluggable VCS/providers/LSP, Neovim/PIW, telegram, future work,
  "no weasels; just work" conclusion). Useful as a spare-parts list, not current.
- `sase_blog.md` (series, ~10 posts planned) — extra requirements: AI-slop
  definition and categories (incl. "prompt debt"), alternations as "vibe evals,"
  PIW advocacy quotes, candidate pull quotes about naming.
- `sase_blog_0.md` Requirements — accumulated after the outline decision: funny
  devil/halo bullets, citations, 3 AI diagrams, TUI screenshots, `tmux_ai_window`
  in the intro, "optimal experience, not optimal performance," "sub-agent"
  terminology dissatisfaction, token types, stashed-prompt examples, stick figures,
  the generalizations list (Gates→Plans→Epics, Beads→sidecars, agent CLIs,
  VCS/workspace ops, presentation tribes/clans/families/hoods, control-flow
  forks/waits/queues, project mgmt, chops), "out of tokens" line, `type:poll`
  GitHub issues as reader questions, Vim-mode joke, a "Why a TUI?" section, loop
  vs graph engineering, skills-as-(procedural-)memory, `reads`/`snips` sidecars,
  `sase artifact read` anecdote, zettelkasten hub-note quote, AI-broccoli section.

Open/blocked vault tasks that constrain the outline: gather references
(high priority), read zettelkasten research, describe a demo video and infographic
per main outline section (high priority), and create `zk/` zettel notes per section.

## 2. What the repo already contains

`docs/blog/posts/` holds 11 drafts and `docs/blog/index.md` names
`structured-agentic-software-engineering.md` (dated 2026-07-08, ~2.9k words) as
the launch post and front door. That draft already implements much of the vault
outline: Boris-method/`tmux_ai_window` intro with devil/halo bullets, "wraps agent
CLIs, not models," Macros, the Agents tab, and install/initialize. It carries a
rename note (xprompts → macros) and a diagram placeholder. Sibling drafts cover
orchestration-why, 15-minute start, macros-in-depth, prompt-widget/nvim, AXE
daemon, beads/SDD, changespecs, commit-workflows/plugins, telegram-mobile, and
whats-next.

## 3. Reference library check (via `bob ref`)

Blog-post-adjacent references from the vault tasks, all already in the library:

- Finished: OpenAI "Harness engineering" (Lopopolo); Steve Kinney "Agent memory
  systems" (29 highlights, 2 comments, one comment linking `sase_memory`);
  "Symphony" Codex-orchestration spec; netclode.
- Queued: Databricks "Omnigent" meta-harness (Zaharia); Mollick "The Dot and the
  Swarm"; Litt "Understanding is the new bottleneck"; Barbaste et al. harness
  survey (arxiv:2609.00006, queued 2026-10-07).
- Agent-report notes (`ref/chat`: launch-strategy, launch-readiness-audit,
  series-structure, blog00-review) are finished topic signals, not reading history.

Library check: 7 of 7 candidates already in the library (4 finished).

## 4. Analysis and tensions

1. The outline decision is done but stale. The `^outline` was frozen 2026-07-07;
   the draft post was generated 7/07–7/08 and has since drifted from the vault
   (terminology: xprompts→macros, ACE→sase's TUI; new requirements unaddressed).
2. The draft under-serves the vault's distinctive beats. Missing or thin:
   identity/motivation hook (`why_sase`), "Why a TUI?", generalizations list,
   token types, skills-as-memory, loop/graph engineering, AI slop/prompt debt,
   polls-as-CTA, Vim joke. These are exactly what would differentiate the post
   from the queued external references (Omnigent, Symphony, harness survey).
3. Scope risk: the vault outline tries to cover XPrompts/Macros, ACE, and AXE in
   one post while sibling drafts (macros-in-depth, axe-background-daemon,
   telegram-mobile) already own the depth. The first post should stay a front
   door and defer.
4. Media is planned but unassigned: one demo/infographic per main section is an
   open high-priority task; the draft has one diagram placeholder and one GIF
   reference in the README. The outline should pin media slots per section.

## 5. Recommended outline for the first blog post

Recommendation: revise (do not restart) the existing launch draft
(`structured-agentic-software-engineering.md`) to the outline below. Section
order follows the reader's journey (pain → thesis → proof → try it → what's
next). Per the request, headings and sub-sections only — no prose.

1. Hook: why this exists
   - Identity and control (software-engineer pride; taking back control)
   - Tinkering as understanding; "it started with Claude Code"
   - Sase by the numbers (LoC, commits, repos) with the motion-isn't-progress beat
2. How we got here: the timeline
   - Boris method → `tmux_ai_window` → auto-approve plans → wait/fork
   - Timeline infographic slot (funny but informative)
   - The missing layer: scrollback-is-database, no notifications, prompts in
     shell history, one prompt launches one agent (devil bullets)
3. Thesis: what sase is
   - Wraps agent CLIs, not models (provider-independent coordination layer)
   - Optimal experience, not optimal performance
   - What sase generalizes (Gates→Plans→Epics; Beads→sidecars; agent CLIs;
     VCS/workspace ops; presentation tribes/clans/families/hoods; control-flow
     forks/waits/queues; project mgmt; chops) (halo bullets)
   - Positioning vs adjacent work (gastown flaw: LLM calls interwoven with
     deterministic code; one-line nods to Omnigent/Symphony/harness-engineering
     with citations, depth deferred to later posts)
4. Macros: the deterministic prompt language (front-door depth only)
   - Directives, alternations (incl. "vibe evals" nod), argument types
   - Multi-prompt vs YAML workflows and when to use each
   - Special macros (`#fork`, project macros); pointer to macros-in-depth
   - Stashed-prompt example slot (screenshot)
5. Supervision: the Agents tab
   - One control surface for many agents; live status, diffs, chats, artifacts
   - Notifications and plan/launch approval gates (human still matters)
   - Fan-out demo slot (single prompt → parallel agents GIF)
   - `sase artifact read` anecdote slot (agent reading 4 related plans)
6. Why a TUI?
   - Keyboard-driven supervision; terminal as the control tower, not the farm
   - TUI screenshot slot; control-tower diagram slot
7. Try it: install and first run
   - 15-minute path (install → provider readiness → init → first agent record)
   - Pointer to Getting Started; what "done" looks like
8. What's next and how to participate
   - Series map (Beads/SDD, Memory, Mobile/Web, Evals, ChangeSpec, architecture)
   - Open questions as `type:poll` GitHub issues (reader CTA)
   - Vim-mode joke and sign-off (no-weasels tone)

Explicitly deferred (pointer only, owned by sibling drafts): AXE/scheduler depth,
sase-telegram, beads/SDD, ChangeSpecs, memory/skills-as-memory essay, AI slop and
prompt debt, token-types tour, loop vs graph engineering, `reads`/`snips`.

## 6. Suggested next actions (not part of the outline)

- Close the Tamanaco gap first: decide macro vs xprompt and ACE vs sase's-TUI
  naming in the draft before adding sections.
- Fulfil the per-section media task against sections 2–7 above (one
  demo/infographic each); current known-good assets: fanout GIF, retry/outage
  and `%wait` screenshots, alternations screenshot, stashed-prompt screenshots.
- Fold only the finished references into post 1 citations (harness-engineering,
  Kinney memory, Symphony, netclode); keep the queued three plus the arxiv
  survey for the follow-up posts they belong to.
- The cancelled "high value / untapped opportunity / lesson per section" task
  duplicates the `zk/` notes task — keep it cancelled and let the zettel notes
  carry that structure.
