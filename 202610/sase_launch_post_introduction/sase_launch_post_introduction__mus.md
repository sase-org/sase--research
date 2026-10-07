# First SASE blog post: introduction draft — research (mus)

Question: write the very first 2–3 paragraphs of the first sase.sh blog post, to serve as the introduction for the rest of the post.

## Vault review (via `bob query` + targeted reads)

Used the `bob_query` skill first (logged skill use), then:

- Tasks query `description includes blog` (~37 tasks): the live project is `sase_blog_0.md` ("Post first blog post to https://sase.sh!"), child of `sase_blog.md` ("Publish the full sase.sh blog series!"). Open items: launch agent to create `~/bob/zk/` notes for the post, gather references, zettelkasten research, demo video/infographic per outline section. Decided/completed: outline frozen in `sase_blog_0#^outline`, Fable first draft, `why_sase.md` created as the container for the full post.
- Targeted reads: `sase_blog_0.md` (outline + Requirements), `sase_blog.md`, `why_sase.md`, `sase_blog_0_legacy_notes.md`, `sase.md` header (`SASE = Structured Agentic Software Engineering`).
- DQL path check confirmed `sase_blog.md` (5 tasks), `sase_blog_0.md` (13 tasks), `why_sase.md` (0 tasks), `sase.md` (~221 tasks).

What the vault says the intro must do:

1. **Outline (`sase_blog_0#^outline`)**: Introduction = personal origin story (Boris method → `tmux_ai_window` → auto-approve plans → wait/fork → …) plus a brief timeline of the software-engineering transformation, summarized with a funny but informative timeline infographic. What follows: Overview, XPrompts, ACE, AXE, Future posts.
2. **Existing draft seed (`why_sase.md`)**: opens in first person — "I've always been proud to call myself a Software Engineer… My attempt to take back some control from this thing that seemed like it was coming for a core part of my identity." Plus beats: it started with Claude Code; crazy 12 months; something big is happening; stats block with a "Motion isn't progress" quote.
3. **Requirements (`sase_blog_0.md`, `sase_blog.md`)**: funny and self-deprecating; optimal *experience*, not optimal performance; tinkering/trying as method ("Sometimes tinkering is the most efficient way to understand"); name jokes; stick-figure art; TUI screenshots later. Legacy notes add: the SASE paper that inspired it, the gastown contrast (interleaving LLM calls with deterministic code), deterministic prompt language (xprompts) as the magic.
4. **Tone constraints**: the vault wants pride and honesty, not a product announcement. The cancelled "proofread" and "writers block" tasks plus the open references/zettel tasks mean this intro must stand alone without depending on citations, diagrams, or screenshots — those come later in the post.

## Grounding in the repo (own research)

Checked the SASE checkout's `README.md` so the intro does not misdescribe the thing:

- sase = Structured Agentic Software Engineering, pronounced "sassy". Tagline: "One developer. A team of coding agents. Tracked, reviewable, repeatable work."
- It is a coordination layer over Claude Code, Codex, Antigravity, Qwen Code, OpenCode, Muse Code, Grok Build — not a replacement for them. One developer supervises parallel agents in isolated workspaces from a keyboard-driven TUI; Macros, Patches, Goals, ToolRuns, scheduler.
- Status is alpha, POSIX-only. That matches the vault's "optimal experience, not optimal performance" framing: the honest pitch is dependability and control, not benchmark wins.

## Conclusions / recommendations

- Write the intro in Bryan's first-person voice, continuing the `why_sase.md` seed rather than restarting it. First person + pride + tinkering is the established opening contract.
- Name the transformation (12 crazy months, started with Claude Code) in paragraph 1, define SASE and its thesis (one developer, a team of agents; tracked, reviewable, repeatable; experience over performance) in paragraph 2, and tee up the post's journey (timeline → xprompts → ACE/AXE → what's next) in paragraph 3. That hands off cleanly to the frozen outline.
- Keep it to 3 paragraphs, no citations or screenshots in the intro itself — the vault explicitly places stats, diagrams, and TUI shots *after* the opening.
- Do not promise performance, autonomy, or magic. The intro's honesty ("take back some control", "I'm still not quite sure what I want, which frustrates me" per the Contents braindump) is theDifferentiator the rest of the post pays off.

## Fully written introduction (deliverable)

I've always been proud to call myself a software engineer. It has always been an easy thing to take pride in — and, if I'm honest, it was pride that started this project. About a year ago the ground shifted under that identity: coding agents went from autocomplete curiosities to something that writes real code while you watch, and I started tinkering because tinkering is the most efficient way I know to understand something. It started with Claude Code, then a tmux window, then auto-approved plans and agents waiting on and forking other agents — and somewhere in that blur of "just one more experiment" I realized something big was happening and I wanted some control back over a core part of who I am.

That tinkering became sase (Structured Agentic Software Engineering, pronounced "sassy"). The idea is simple: one developer, a team of coding agents, doing tracked, reviewable, repeatable work. Sase doesn't replace your agents — it turns Claude, Codex, and friends into a coordinated engineering team, with parallel agents in isolated workspaces supervised from one keyboard-driven TUI. Sase makes no claim to optimal performance, only to optimal experience: every run is something you can watch, interrupt, review, and reproduce, because motion isn't progress and a pile of agent output you can't trust is just a faster mess.

This is the first of a series of posts about what I built and what it taught me. We'll start with a brief timeline of how software engineering changed in the last twelve months, then tour the pieces that fell out of all that trying: a deterministic prompt language for interweaving agents with real code, the TUI and scheduler I use to supervise them, and the tracking machinery that keeps the whole swarm honest. And yes, there are stick figures.
